#!/usr/bin/env python3
"""
SOMOS TRUFAS — Transicion esports (stinger) 1 s / 1920x1080 / 60 fps.

Genera una secuencia PNG con canal alpha y la codifica en:
  · WebM VP9 con alpha  -> stinger para OBS
  · MOV ProRes 4444     -> edicion (Premiere / AE / Resolve)
  · MP4 demo A->B       -> vista previa del efecto

Paleta y tipografia tomadas del "Manual de Identidad TRUFAS":
  Mikado Yellow #FFC621 · Liver #583F37 · #FF9A21 · #452B22
"""

import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

Image.MAX_IMAGE_PIXELS = None

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "assets")
FONTS = os.path.join(ROOT, "fonts")
OUT = os.path.join(ROOT, "out")
FRAMES = os.path.join(OUT, "frames")

W0, H0 = 1920, 1080
S = int(os.environ.get("SS", "3"))          # supersampling
W, H = W0 * S, H0 * S
FPS, N = 60, 60                             # 60 frames = 1.000 s exacto

# ---------------------------------------------------------------- paleta ----
YEL = (255, 198, 33)      # Mikado Yellow
ORG = (255, 154, 33)
LIVER = (88, 63, 55)      # Liver
DEEP = (69, 43, 34)
NIGHT = (32, 19, 14)
WHITE = (255, 255, 255)

# ------------------------------------------------------------- timeline ----
YEL_IN, ORG_IN, DARK_IN = (0.00, 0.24), (0.05, 0.29), (0.10, 0.34)
DARK_OUT, ORG_OUT, YEL_OUT = (0.60, 0.86), (0.64, 0.90), (0.68, 0.96)
MASCOT_T = (0.24, 0.40)
WORD_T = (0.29, 0.45)
IMPACT = 0.385
CUT_POINT = 0.50          # punto de corte de escena recomendado

# ------------------------------------------------------------- geometria ----
SKEW = H * 0.325                              # 18 grados
SLABW = W * 1.42
XB_IN = -SKEW - W * 0.04
XB_RIGHT = W * 1.10
XB_LEFT = -(SLABW + SKEW + W * 0.08)


# --------------------------------------------------------------- easing ----
def clamp01(x):
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def seg(t, a, b):
    return clamp01((t - a) / (b - a)) if b > a else (1.0 if t >= b else 0.0)


def lerp(a, b, p):
    return a + (b - a) * p


def out_quint(p):
    return 1 - (1 - p) ** 5


def out_expo(p):
    return 1.0 if p >= 1 else 1 - 2 ** (-10 * p)


def out_cubic(p):
    return 1 - (1 - p) ** 3


def accel(p, k=1.9):
    return p ** k


# ------------------------------------------------------------ primitivas ----
def slab_poly(xb):
    return [(xb, H), (xb + SLABW, H), (xb + SLABW + SKEW, 0), (xb + SKEW, 0)]


def slab_x(t, tin, tout):
    """Posicion del borde inferior-izquierdo de una banda diagonal."""
    if t < tin[1]:
        return lerp(XB_RIGHT, XB_IN, out_cubic(seg(t, *tin)))
    if t < tout[0]:
        return XB_IN
    return lerp(XB_IN, XB_LEFT, accel(seg(t, *tout)))


def draw_slab(layer, xb, color, edge=None, edge_w=0.0):
    d = ImageDraw.Draw(layer)
    d.polygon(slab_poly(xb), fill=color + (255,))
    if edge and edge_w > 0:
        x2 = xb + SLABW
        d.polygon(
            [(x2 - edge_w, H), (x2, H), (x2 + SKEW, 0), (x2 - edge_w + SKEW, 0)],
            fill=edge + (255,),
        )


# ------------------------------------------------------ assets precargados ----
def _load():
    a = {}

    lock = Image.open(os.path.join(ASSETS, "lockup_yellow.png")).convert("RGBA")
    la = np.asarray(lock.getchannel("A"))
    cols = (la > 76).sum(axis=0)
    runs, s = [], None
    for i, v in enumerate(cols):
        if v == 0:
            s = i if s is None else s
        elif s is not None:
            runs.append((s, i - 1))
            s = None
    runs = [r for r in runs if r[1] - r[0] > 60 and lock.width * 0.1 < r[0] < lock.width * 0.9]
    gap = max(runs, key=lambda r: r[1] - r[0])

    # geometria relativa del lockup oficial (unidades = ancho total del lockup)
    def bbox(x0, x1):
        sub = la[:, x0:x1]
        ys, xs = np.where(sub > 76)
        return (x0 + xs.min(), ys.min(), x0 + xs.max(), ys.max())

    mb = bbox(0, gap[0])
    wb = bbox(gap[1], lock.width)
    LW = lock.width
    a["mascot_rel"] = (mb[0] / LW, mb[1] / LW, (mb[2] - mb[0]) / LW, (mb[3] - mb[1]) / LW)
    a["word_rel"] = (wb[0] / LW, wb[1] / LW, (wb[2] - wb[0]) / LW, (wb[3] - wb[1]) / LW)
    a["lock_h_rel"] = (max(mb[3], wb[3]) - min(mb[1], wb[1])) / LW
    a["lock_y0_rel"] = min(mb[1], wb[1]) / LW

    # mascota a todo color, recortada a su contenido
    m = Image.open(os.path.join(ASSETS, "mascot_full.png")).convert("RGBA")
    m = m.crop(m.getchannel("A").getbbox())
    LOCK_W = W * 0.50
    mw = LOCK_W * a["mascot_rel"][2]
    a["mascot"] = m.resize((int(mw * 2.3), int(mw * 2.3 * m.height / m.width)), Image.LANCZOS)

    w = Image.open(os.path.join(ASSETS, "wordmark_yellow.png")).convert("RGBA")
    w = w.crop(w.getchannel("A").getbbox())
    ww = LOCK_W * a["word_rel"][2]
    a["word"] = w.resize((int(ww * 1.25), int(ww * 1.25 * w.height / w.width)), Image.LANCZOS)
    a["LOCK_W"] = LOCK_W
    return a


A = _load()


def _bg():
    yy, xx = np.mgrid[0:H, 0:W]
    nx = (xx / W - 0.5) * 2.0
    ny = (yy / H - 0.5) * 2.0
    r = np.clip(np.sqrt(nx * nx + ny * ny) / 1.414, 0, 1).astype(np.float32) ** 1.3
    img = np.empty((H, W, 4), np.uint8)
    for i in range(3):
        img[..., i] = (DEEP[i] * (1 - r) + NIGHT[i] * r).astype(np.uint8)
    img[..., 3] = 255
    del yy, xx, nx, ny, r
    return Image.fromarray(img, "RGBA")


def _stripes(spacing, thick, color, alpha):
    lay = Image.new("RGBA", (int(W + spacing), H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x = -SKEW - spacing
    while x < W + spacing * 2:
        d.polygon(
            [(x, H), (x + thick, H), (x + thick + SKEW, 0), (x + SKEW, 0)],
            fill=color + (alpha,),
        )
        x += spacing
    return lay


BG = _bg()
SP1 = W * 0.030
ST1 = _stripes(SP1, W * 0.0045, LIVER, 150)
SP2 = W * 0.013
ST2 = _stripes(SP2, W * 0.0016, LIVER, 34)

# esquirlas de velocidad
_rng = np.random.default_rng(11)
SHARDS = []
for i in range(26):
    diag = i % 5 != 0                       # 4 de cada 5 siguen la diagonal
    SHARDS.append(
        dict(
            y=float(_rng.uniform(-0.06, 0.95)),
            h=float(_rng.uniform(0.14, 0.55) if diag else _rng.uniform(0.008, 0.030)),
            w=float(_rng.uniform(0.0025, 0.013) if diag else _rng.uniform(0.08, 0.32)),
            d=float(_rng.uniform(0.0, 0.28)),
            c=[YEL, ORG, WHITE, YEL, YEL, ORG][i % 6],
            a=int(_rng.uniform(120, 255)),
        )
    )


def draw_shards(layer, t):
    d = ImageDraw.Draw(layer)
    tail = 1.0 - seg(t, 0.955, 1.0)         # nada queda colgado al final
    for sh in SHARDS:
        wins = ((sh["d"] * 0.40, 0.28 + sh["d"] * 0.40),
                (0.78 + sh["d"] * 0.14, 0.97 + sh["d"] * 0.14))
        for k, win in enumerate(wins):
            p = seg(t, *win)
            if p <= 0 or p >= 1:
                continue
            x = lerp(W * 1.20, -W * 0.60, out_cubic(p) if k == 0 else p)
            y0 = sh["y"] * H
            y1 = y0 + sh["h"] * H
            bw = sh["w"] * W
            o0 = (1 - y0 / H) * SKEW
            o1 = (1 - y1 / H) * SKEW
            fade = min(1.0, (1 - p) * 3.2, p * 6.0) * (tail if k else 1.0)
            a = int(sh["a"] * fade)
            if a < 3:
                continue
            d.polygon(
                [(x + o0, y0), (x + bw + o0, y0), (x + bw + o1, y1), (x + o1, y1)],
                fill=sh["c"] + (a,),
            )


# ------------------------------------------------------------- el "card" ----
def build_card(t, logo_dx=0.0):
    """Fondo oscuro + textura + logo + impacto (sin recortar a la banda)."""
    card = BG.copy()

    # textura diagonal en movimiento
    dx1 = int((t * W * 0.38) % SP1)
    card.alpha_composite(ST1.crop((dx1, 0, dx1 + W, H)))
    dx2 = int((t * W * 0.90) % SP2)
    card.alpha_composite(ST2.crop((dx2, 0, dx2 + W, H)))

    cx, cy = W / 2 + logo_dx, H / 2
    LOCK_W = A["LOCK_W"]
    mrel, wrel = A["mascot_rel"], A["word_rel"]
    lock_cy = (A["lock_y0_rel"] + A["lock_h_rel"] / 2) * LOCK_W
    lx = cx - LOCK_W / 2
    ly = cy - lock_cy

    # --- impacto: onda de choque + rafaga radial (por DETRAS del logo) ---
    fx = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(fx)
    # el anillo arranca ya fuera del lockup para no cortar el logotipo
    for delay, mult, col, life in ((0.0, 1.00, YEL, 0.12), (0.03, 0.66, WHITE, 0.10)):
        rp = seg(t, IMPACT + delay, IMPACT + delay + life)
        if 0 < rp < 1:
            r = (W * 0.26 + out_expo(rp) * W * 0.80) * mult
            lw = max(2, int((1 - rp) ** 1.4 * W * 0.009 + 2))
            al = int(((1 - rp) ** 2.6) * 215)
            if al > 3 and r > 4:
                d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col + (al,), width=lw)

    # las lineas quedan pegadas al centro: el logo tapa las que lo cruzan
    bp = seg(t, IMPACT, IMPACT + 0.09)
    if 0 < bp < 1:
        e = out_expo(bp)
        al = int(((1 - bp) ** 2.0) * 245)
        r0 = W * 0.075 + e * W * 0.055
        r1 = r0 + (1 - bp) * W * 0.045 + W * 0.008
        for i in range(12):
            ang = (i / 12) * math.tau + 0.26
            lw = max(3, int((1 - bp) * W * 0.0075) + 2)
            d.line(
                [cx + r0 * math.cos(ang), cy + r0 * math.sin(ang),
                 cx + r1 * math.cos(ang), cy + r1 * math.sin(ang)],
                fill=YEL + (al,), width=lw,
            )
    card.alpha_composite(fx)

    # --- wordmark: sale de detras de la mascota con un barrido ---
    wp = seg(t, *WORD_T)
    if wp > 0:
        e = out_expo(wp)
        tw = LOCK_W * wrel[2]
        th = LOCK_W * wrel[3]
        wm = A["word"].resize((max(1, int(tw)), max(1, int(th))), Image.LANCZOS)
        wx = lx + LOCK_W * wrel[0] + (1 - e) * W * 0.018
        wy = ly + LOCK_W * wrel[1]
        reveal = int(tw * e)
        if reveal > 0:
            wm = wm.crop((0, 0, reveal, wm.height))
            if e < 1:
                wm.putalpha(wm.getchannel("A").point(lambda v: int(v * min(1.0, wp * 2.4))))
            card.alpha_composite(wm, (int(wx), int(wy)))

    # --- mascota: golpe con sobre-escala ---
    mp = seg(t, *MASCOT_T)
    if mp > 0:
        e = out_expo(mp)
        sc = 1.0 + 1.20 * (1 - e)
        if t > MASCOT_T[1]:                       # rebote corto al aterrizar
            q = seg(t, MASCOT_T[1], 0.56)
            sc = 1.0 + 0.030 * math.sin(q * math.pi * 2) * (1 - q)
        sc *= 1.0 + 0.014 * seg(t, MASCOT_T[1], 0.62)

        tw = LOCK_W * mrel[2] * sc
        m = A["mascot"]
        m = m.resize((max(1, int(tw)), max(1, int(tw * m.height / m.width))), Image.LANCZOS)
        rot = -15.0 * (1 - e)
        if abs(rot) > 0.15:
            m = m.rotate(rot, resample=Image.BICUBIC, expand=True)
        blur = (1 - e) ** 1.4 * W * 0.010
        if blur > 0.7:
            m = m.filter(ImageFilter.GaussianBlur(blur))
        op = min(1.0, seg(t, MASCOT_T[0], MASCOT_T[0] + 0.05))
        if op < 1:
            m.putalpha(m.getchannel("A").point(lambda v: int(v * op)))
        mcx = lx + LOCK_W * (mrel[0] + mrel[2] / 2)
        mcy = ly + LOCK_W * (mrel[1] + mrel[3] / 2)
        card.alpha_composite(m, (int(mcx - m.width / 2), int(mcy - m.height / 2)))

    # --- impacto: ondas de choque + rafaga radial ---
    # --- destello ---
    fp = seg(t, IMPACT - 0.02, IMPACT + 0.075)
    if 0 < fp < 1:
        k = (1 - fp) ** 2.6 if t >= IMPACT else seg(t, IMPACT - 0.02, IMPACT) * 0.55
        a = int(clamp01(k) * 150)
        if a > 2:
            card.alpha_composite(Image.new("RGBA", (W, H), (255, 238, 196, a)))

    # --- aberracion cromatica en el golpe ---
    sp = seg(t, IMPACT, IMPACT + 0.09)
    if 0 < sp < 1:
        off = int((1 - sp) ** 1.6 * W * 0.0026)
        if off >= 1:
            r, g, b, al = card.split()
            card = Image.merge(
                "RGBA",
                (ImageChops.offset(r, off, 0), g, ImageChops.offset(b, -off, 0), al),
            )
    return card


# ------------------------------------------------------------- un frame ----
def render_frame(f):
    t = (f + 0.5) / FPS
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    draw_shards(canvas, t)

    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_slab(lay, slab_x(t, YEL_IN, YEL_OUT), YEL, WHITE, W * 0.0035)
    canvas.alpha_composite(lay)

    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_slab(lay, slab_x(t, ORG_IN, ORG_OUT), ORG, YEL, W * 0.0055)
    canvas.alpha_composite(lay)

    xb = slab_x(t, DARK_IN, DARK_OUT)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon(slab_poly(xb), fill=255)
    # parallax: el logo acompana la salida de la banda, pero mas lento
    card = build_card(t, logo_dx=(xb - XB_IN) * 0.34 if t > DARK_OUT[0] else 0.0)
    card.putalpha(ImageChops.multiply(card.getchannel("A"), mask))
    canvas.alpha_composite(card)

    edge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ew = W * 0.0042
    x2 = xb + SLABW
    ImageDraw.Draw(edge).polygon(
        [(x2 - ew, H), (x2, H), (x2 + SKEW, 0), (x2 - ew + SKEW, 0)], fill=YEL + (255,)
    )
    canvas.alpha_composite(edge)

    out = canvas.resize((W0, H0), Image.LANCZOS)

    # grano sutil (bloques 2x2: parece grano de pelicula y comprime mucho mejor)
    arr = np.asarray(out).astype(np.int16)
    small = _rng.integers(-3, 4, (H0 // 2, W0 // 2, 1)).astype(np.int16)
    n = np.repeat(np.repeat(small, 2, axis=0), 2, axis=1)
    m = arr[..., 3:4] > 0
    arr[..., :3] = np.clip(arr[..., :3] + n * m, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


# ---------------------------------------------------------------- escenas ----
def demo_scene(kind):
    im = Image.new("RGB", (W0, H0), (16, 18, 24) if kind == "A" else (24, 16, 12))
    d = ImageDraw.Draw(im)
    if kind == "A":
        for y in range(0, H0, 3):
            k = int(16 + 26 * (y / H0))
            d.line([(0, y), (W0, y)], fill=(k, k + 4, k + 12))
        for x in range(-H0, W0, 64):
            d.line([(x, H0), (x + H0, 0)], fill=(30, 36, 50), width=2)
        base, label, sub = (120, 150, 210), "ESCENA A", "GAMEPLAY"
    else:
        for y in range(0, H0, 3):
            k = int(20 + 30 * (1 - y / H0))
            d.line([(0, y), (W0, y)], fill=(k + 14, k + 6, k))
        for x in range(-H0, W0, 64):
            d.line([(x, H0), (x + H0, 0)], fill=(58, 40, 28), width=2)
        base, label, sub = YEL, "ESCENA B", "CAMARA"
    try:
        f1 = ImageFont.truetype(os.path.join(FONTS, "BebasNeue-Regular.ttf"), 190)
        f2 = ImageFont.truetype(os.path.join(FONTS, "Poppins-Bold.ttf"), 42)
    except OSError:
        f1 = f2 = ImageFont.load_default()
    d.text((W0 / 2, H0 / 2 - 40), label, font=f1, fill=base, anchor="mm")
    d.text((W0 / 2, H0 / 2 + 90), sub, font=f2, fill=(150, 150, 150), anchor="mm")
    return im


# ------------------------------------------------------------------ main ----
def main():
    os.makedirs(FRAMES, exist_ok=True)
    args = sys.argv[1:]
    if args and args[0] == "--preview":
        for f in [int(x) for x in args[1].split(",")]:
            render_frame(f).save(os.path.join(OUT, f"preview_{f:02d}.png"))
            print("preview frame", f, "t=%.3f" % ((f + 0.5) / FPS))
        return

    import time

    t0 = time.time()
    for f in range(N):
        render_frame(f).save(os.path.join(FRAMES, "f%03d.png" % f))
        if f % 10 == 0:
            print("  frame %02d/%d  (%.1fs)" % (f, N, time.time() - t0), flush=True)
    print("frames listos en %.1fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
