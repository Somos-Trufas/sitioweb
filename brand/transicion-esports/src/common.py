#!/usr/bin/env python3
"""
Base compartida de las transiciones de Somos Trufas.

Cada estilo vive en su propio modulo y expone:
    NAME, TITLE, CUT_POINT y frame(f) -> RGBA supersampleado.

Paleta y tipografia del "Manual de Identidad TRUFAS":
  Mikado Yellow #FFC621 · Liver #583F37 · #FF9A21 · #452B22
"""

import math
import os
import subprocess
import time

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

Image.MAX_IMAGE_PIXELS = None

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "assets")
FONTS = os.path.join(ROOT, "fonts")
OUT = os.path.join(ROOT, "out")

W0, H0 = 1920, 1080
S = int(os.environ.get("SS", "3"))           # supersampling
W, H = W0 * S, H0 * S
FPS, N = 60, 60                              # 60 frames = 1.000 s exacto

# ---------------------------------------------------------------- paleta ----
YEL = (255, 198, 33)       # Mikado Yellow
ORG = (255, 154, 33)
LIVER = (88, 63, 55)       # Liver
DEEP = (69, 43, 34)
NIGHT = (32, 19, 14)
WHITE = (255, 255, 255)

SKEW = H * 0.325           # 18 grados: el angulo diagonal de la marca


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


def in_cubic(p):
    return p ** 3


def in_out_cubic(p):
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def accel(p, k=1.9):
    return p ** k


# ------------------------------------------------------- bandas diagonales ----
SLABW = W * 1.42
XB_IN = -SKEW - W * 0.04
XB_RIGHT = W * 1.10
XB_LEFT = -(SLABW + SKEW + W * 0.08)


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


# ------------------------------------------------------------------ assets ----
_A = {}


def _sil_pyramid(src):
    """Mipmaps de la silueta: evita el aliasing al escalarla muy pequena."""
    levels, cur = [], src
    while cur.width > 128:
        levels.append(cur)
        cur = cur.resize((cur.width // 2, max(1, cur.height // 2)), Image.LANCZOS)
    levels.append(cur)
    return levels


def _cover_scale(sil):
    """Ancho minimo (en multiplos del frame) para que la silueta tape todo."""
    small = sil.resize((256, max(1, int(256 * sil.height / sil.width))), Image.LANCZOS)
    lo, hi = 0.6, 6.0
    for _ in range(22):
        mid = (lo + hi) / 2
        w = max(2, int(240 * mid))
        h = max(2, int(w * small.height / small.width))
        s = small.resize((w, h), Image.BILINEAR).point(lambda v: 255 if v > 128 else 0)
        canvas = Image.new("L", (240, 135), 0)
        canvas.paste(s, (120 - w // 2, 67 - h // 2))
        if np.asarray(canvas).min() > 250:
            hi = mid
        else:
            lo = mid
    return hi


def assets():
    """Carga perezosa: los estilos solo pagan por lo que usan."""
    if _A:
        return _A

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
    runs = [r for r in runs
            if r[1] - r[0] > 60 and lock.width * 0.1 < r[0] < lock.width * 0.9]
    gap = max(runs, key=lambda r: r[1] - r[0])

    def bbox(x0, x1):
        ys, xs = np.where(la[:, x0:x1] > 76)
        return (x0 + xs.min(), ys.min(), x0 + xs.max(), ys.max())

    mb, wb, LW = bbox(0, gap[0]), bbox(gap[1], lock.width), lock.width
    _A["mascot_rel"] = (mb[0] / LW, mb[1] / LW,
                        (mb[2] - mb[0]) / LW, (mb[3] - mb[1]) / LW)
    _A["word_rel"] = (wb[0] / LW, wb[1] / LW,
                      (wb[2] - wb[0]) / LW, (wb[3] - wb[1]) / LW)
    _A["lock_h_rel"] = (max(mb[3], wb[3]) - min(mb[1], wb[1])) / LW
    _A["lock_y0_rel"] = min(mb[1], wb[1]) / LW

    m = Image.open(os.path.join(ASSETS, "mascot_full.png")).convert("RGBA")
    m = m.crop(m.getchannel("A").getbbox())
    _A["mascot"] = m.resize((int(W * 0.30),
                             int(W * 0.30 * m.height / m.width)), Image.LANCZOS)

    w = Image.open(os.path.join(ASSETS, "wordmark_yellow.png")).convert("RGBA")
    w = w.crop(w.getchannel("A").getbbox())
    _A["word"] = w.resize((int(W * 0.45),
                           int(W * 0.45 * w.height / w.width)), Image.LANCZOS)

    # silueta = el alfa de la mascota (su contorno amarillo es el borde real)
    sil = m.getchannel("A")
    _A["sil_levels"] = _sil_pyramid(sil)
    _A["sil_cover"] = _cover_scale(sil)
    return _A


def sil_mask(scale, rot=0.0, fcx=None, fcy=None):
    """
    Mascara (L, tamano de frame) con la silueta de la mascota escalada a
    `scale` anchos de frame. Usa una afin inversa, asi que cuesta lo mismo
    con la silueta diminuta que gigante.
    """
    lv = assets()["sil_levels"]
    tw = max(1.0, scale * W)
    src = next((l for l in reversed(lv) if l.width >= tw), lv[0])
    sw, sh = src.size
    k = tw / sw
    th = math.radians(rot)
    cos, sin = math.cos(th), math.sin(th)
    fcx = W / 2 if fcx is None else fcx
    fcy = H / 2 if fcy is None else fcy
    a, b = cos / k, sin / k
    d, e = -sin / k, cos / k
    c = sw / 2 - (a * fcx + b * fcy)
    f = sh / 2 - (d * fcx + e * fcy)
    return src.transform((W, H), Image.AFFINE, (a, b, c, d, e, f),
                         resample=Image.BILINEAR, fillcolor=0)


def font_path(name):
    """`name` puede ser una lista: devuelve el primero que exista, o None."""
    for n in ([name] if isinstance(name, str) else name):
        p = os.path.join(FONTS, n)
        if os.path.exists(p):
            return p
    return None


def font(name, size):
    p = font_path(name)
    try:
        return ImageFont.truetype(p, int(size))
    except (OSError, TypeError):
        return ImageFont.load_default()


# ------------------------------------------------------- fondo y texturas ----
_CACHE = {}


def bg():
    if "bg" not in _CACHE:
        yy, xx = np.mgrid[0:H, 0:W]
        nx, ny = (xx / W - 0.5) * 2.0, (yy / H - 0.5) * 2.0
        r = np.clip(np.sqrt(nx * nx + ny * ny) / 1.414, 0, 1).astype(np.float32) ** 1.3
        img = np.empty((H, W, 4), np.uint8)
        for i in range(3):
            img[..., i] = (DEEP[i] * (1 - r) + NIGHT[i] * r).astype(np.uint8)
        img[..., 3] = 255
        del yy, xx, nx, ny, r
        _CACHE["bg"] = Image.fromarray(img, "RGBA")
    return _CACHE["bg"]


def stripes(spacing, thick, color, alpha):
    key = ("st", spacing, thick, color, alpha)
    if key not in _CACHE:
        lay = Image.new("RGBA", (int(W + spacing), H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        x = -SKEW - spacing
        while x < W + spacing * 2:
            d.polygon([(x, H), (x + thick, H), (x + thick + SKEW, 0), (x + SKEW, 0)],
                      fill=color + (alpha,))
            x += spacing
        _CACHE[key] = lay
    return _CACHE[key]


def textured_bg(t, speed1=0.38, speed2=0.90):
    """Fondo oscuro con la trama diagonal en movimiento."""
    card = bg().copy()
    sp1, sp2 = W * 0.030, W * 0.013
    dx = int((t * W * speed1) % sp1)
    card.alpha_composite(stripes(sp1, W * 0.0045, LIVER, 150).crop((dx, 0, dx + W, H)))
    dx = int((t * W * speed2) % sp2)
    card.alpha_composite(stripes(sp2, W * 0.0016, LIVER, 34).crop((dx, 0, dx + W, H)))
    return card


# ----------------------------------------------------------- logo e impacto ----
def draw_shockwave(card, t, impact, cx, cy, rings=True, burst=True):
    """Onda de choque y rafaga radial. Se dibuja DETRAS del logo."""
    fx = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(fx)
    if rings:
        # arranca ya fuera del lockup para no cortar el logotipo
        for delay, mult, col, life in ((0.0, 1.00, YEL, 0.12), (0.03, 0.66, WHITE, 0.10)):
            rp = seg(t, impact + delay, impact + delay + life)
            if 0 < rp < 1:
                r = (W * 0.26 + out_expo(rp) * W * 0.80) * mult
                lw = max(2, int((1 - rp) ** 1.4 * W * 0.009 + 2))
                al = int(((1 - rp) ** 2.6) * 215)
                if al > 3 and r > 4:
                    d.ellipse([cx - r, cy - r, cx + r, cy + r],
                              outline=col + (al,), width=lw)
    if burst:
        bp = seg(t, impact, impact + 0.09)
        if 0 < bp < 1:
            e = out_expo(bp)
            al = int(((1 - bp) ** 2.0) * 245)
            r0 = W * 0.075 + e * W * 0.055
            r1 = r0 + (1 - bp) * W * 0.045 + W * 0.008
            for i in range(12):
                ang = (i / 12) * math.tau + 0.26
                lw = max(3, int((1 - bp) * W * 0.0075) + 2)
                d.line([cx + r0 * math.cos(ang), cy + r0 * math.sin(ang),
                        cx + r1 * math.cos(ang), cy + r1 * math.sin(ang)],
                       fill=YEL + (al,), width=lw)
    card.alpha_composite(fx)


def draw_lockup(card, t, mascot_t, word_t, cx, cy, lock_w):
    """El lockup oficial: la mascota golpea, el logotipo sale de detras."""
    a = assets()
    mrel, wrel = a["mascot_rel"], a["word_rel"]
    lx = cx - lock_w / 2
    ly = cy - (a["lock_y0_rel"] + a["lock_h_rel"] / 2) * lock_w

    wp = seg(t, *word_t)
    if wp > 0:
        e = out_expo(wp)
        tw, th = lock_w * wrel[2], lock_w * wrel[3]
        wm = a["word"].resize((max(1, int(tw)), max(1, int(th))), Image.LANCZOS)
        reveal = int(tw * e)
        if reveal > 0:
            wm = wm.crop((0, 0, reveal, wm.height))
            if e < 1:
                wm.putalpha(wm.getchannel("A").point(
                    lambda v: int(v * min(1.0, wp * 2.4))))
            card.alpha_composite(wm, (int(lx + lock_w * wrel[0] + (1 - e) * W * 0.018),
                                      int(ly + lock_w * wrel[1])))

    mp = seg(t, *mascot_t)
    if mp > 0:
        e = out_expo(mp)
        sc = 1.0 + 1.20 * (1 - e)
        if t > mascot_t[1]:                          # rebote corto al aterrizar
            q = seg(t, mascot_t[1], mascot_t[1] + 0.16)
            sc = 1.0 + 0.030 * math.sin(q * math.pi * 2) * (1 - q)
        sc *= 1.0 + 0.014 * seg(t, mascot_t[1], mascot_t[1] + 0.22)

        tw = lock_w * mrel[2] * sc
        m = a["mascot"]
        m = m.resize((max(1, int(tw)), max(1, int(tw * m.height / m.width))),
                     Image.LANCZOS)
        rot = -15.0 * (1 - e)
        if abs(rot) > 0.15:
            m = m.rotate(rot, resample=Image.BICUBIC, expand=True)
        blur = (1 - e) ** 1.4 * W * 0.010
        if blur > 0.7:
            m = m.filter(ImageFilter.GaussianBlur(blur))
        op = min(1.0, seg(t, mascot_t[0], mascot_t[0] + 0.05))
        if op < 1:
            m.putalpha(m.getchannel("A").point(lambda v: int(v * op)))
        mcx = lx + lock_w * (mrel[0] + mrel[2] / 2)
        mcy = ly + lock_w * (mrel[1] + mrel[3] / 2)
        card.alpha_composite(m, (int(mcx - m.width / 2), int(mcy - m.height / 2)))


def flash(card, t, impact, peak=150, lead=0.02, life=0.075):
    fp = seg(t, impact - lead, impact + life)
    if 0 < fp < 1:
        k = (1 - fp) ** 2.6 if t >= impact else seg(t, impact - lead, impact) * 0.55
        a = int(clamp01(k) * peak)
        if a > 2:
            card.alpha_composite(Image.new("RGBA", (W, H), (255, 238, 196, a)))


def rgb_split(card, t, impact, life=0.09, amount=0.0026):
    sp = seg(t, impact, impact + life)
    if 0 < sp < 1:
        off = int((1 - sp) ** 1.6 * W * amount)
        if off >= 1:
            r, g, b, al = card.split()
            return Image.merge("RGBA", (ImageChops.offset(r, off, 0), g,
                                        ImageChops.offset(b, -off, 0), al))
    return card


# ------------------------------------------------------------- pipeline ----
def finish(canvas, f):
    """Baja a 1080p y anade grano en bloques 2x2 (comprime mucho mejor)."""
    out = canvas.resize((W0, H0), Image.LANCZOS)
    arr = np.asarray(out).astype(np.int16)
    rng = np.random.default_rng(9000 + f)
    small = rng.integers(-3, 4, (H0 // 2, W0 // 2, 1)).astype(np.int16)
    n = np.repeat(np.repeat(small, 2, axis=0), 2, axis=1)
    arr[..., :3] = np.clip(arr[..., :3] + n * (arr[..., 3:4] > 0), 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def frames_dir(style):
    return os.path.join(OUT, style.NAME, "frames")


def render_sequence(style, only=None):
    d = frames_dir(style)
    os.makedirs(d, exist_ok=True)
    todo = only if only is not None else range(N)
    t0 = time.time()
    for f in todo:
        finish(style.frame(f), f).save(os.path.join(d, "f%03d.png" % f))
        if only is None and f % 15 == 0:
            print("  frame %02d/%d  (%.1fs)" % (f, N, time.time() - t0), flush=True)
    print("  %s: %d frames en %.1fs" % (style.NAME, len(list(todo)), time.time() - t0))


def coverage(style):
    """Ventana en la que el frame es 100 % opaco (donde puede caer el corte)."""
    d = frames_dir(style)
    full = [(i + 0.5) / FPS for i in range(N)
            if np.asarray(Image.open(os.path.join(d, "f%03d.png" % i))
                          .getchannel("A")).min() == 255]
    return (full[0], full[-1], len(full)) if full else (None, None, 0)


def encode_webm(style, dest, crf=20):
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS),
         "-i", os.path.join(frames_dir(style), "f%03d.png"),
         "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0",
         "-crf", str(crf), "-auto-alt-ref", "0", "-row-mt", "1", dest],
        check=True, capture_output=True)


def verify_alpha(style, dest):
    """
    ffmpeg guarda el alfa de WebM en un stream aparte y el decoder nativo lo
    ignora, asi que hay que pedir libvpx-vp9 explicitamente para comprobarlo.
    """
    ref = np.asarray(Image.open(os.path.join(frames_dir(style), "f003.png"))
                     .getchannel("A"))
    tmp = os.path.join(OUT, ".chk.png")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-c:v", "libvpx-vp9",
                    "-i", dest, "-vf", "select=eq(n\\,3)", "-vframes", "1",
                    "-pix_fmt", "rgba", tmp], capture_output=True)
    got = np.asarray(Image.open(tmp).convert("RGBA").getchannel("A"))
    os.remove(tmp)
    a, b = float((got == 0).mean()), float((ref == 0).mean())
    return abs(a - b) < 0.02, a, b
