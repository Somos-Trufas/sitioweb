#!/usr/bin/env python3
"""
Estilo 3 — REPLAY.

Dos mitades convergen sobre la diagonal de marca, se juntan sobre el rotulo
REPLAY con estetica de cinta (lineas de barrido, chevrones de rebobinado y
saltos de imagen) y se separan para dejar ver la repeticion.

El rotulo va en Bebas Neue, que es el sustituto libre habitual de Dharma
Gothic M, la display del manual: es comercial y no esta en el repo. Si la
licencian, basta con dejar el .ttf en fonts/ y cambiar FONT_DISPLAY.
"""

from common import *

NAME = "replay"
TITLE = "Replay"
CUT_POINT = 0.50

FONT_DISPLAY = "BebasNeue-Regular.ttf"

YEL_IN, ORG_IN, DARK_IN = (0.00, 0.24), (0.05, 0.29), (0.10, 0.34)
DARK_OUT, ORG_OUT, YEL_OUT = (0.60, 0.86), (0.64, 0.90), (0.68, 0.96)
MASCOT_T, WORD_START, IMPACT = (0.26, 0.40), 0.30, 0.38

# ---- geometria del corte diagonal -----------------------------------------
_L = math.hypot(SKEW, H)
UX, UY = SKEW / _L, -H / _L        # a lo largo de la diagonal
NX, NY = H / _L, SKEW / _L         # perpendicular
CX, CY = W / 2, H / 2
BIG = 3 * max(W, H)
DMAX = max(abs((x - CX) * NX + (y - CY) * NY)
           for x, y in ((0, 0), (W, 0), (0, H), (W, H)))
OVER = W * 0.003                   # solape que garantiza que no quede rendija
EDGE = W * 0.008


def half_poly(off, s):
    """Semiplano a un lado de la diagonal desplazada `off`. s=+1 arriba-dcha."""
    px, py = CX + NX * off, CY + NY * off
    ax, ay = px + UX * BIG, py + UY * BIG
    bx, by = px - UX * BIG, py - UY * BIG
    return [(ax, ay), (bx, by),
            (bx + NX * BIG * s, by + NY * BIG * s),
            (ax + NX * BIG * s, ay + NY * BIG * s)]


def band_poly(off, s, width):
    """Franja de `width` hacia el interior del semiplano: el filo brillante."""
    o2 = off + width * s
    p0 = (CX + NX * off, CY + NY * off)
    p1 = (CX + NX * o2, CY + NY * o2)
    return [(p0[0] + UX * BIG, p0[1] + UY * BIG), (p0[0] - UX * BIG, p0[1] - UY * BIG),
            (p1[0] - UX * BIG, p1[1] - UY * BIG), (p1[0] + UX * BIG, p1[1] + UY * BIG)]


def half_off(t, tin, tout, s):
    closed, opened = -OVER * s, DMAX * 1.06 * s
    if t < tin[1]:
        return lerp(opened, closed, out_cubic(seg(t, *tin)))
    if t < tout[0]:
        return closed
    return lerp(closed, opened, accel(seg(t, *tout)))


# ---- textura de cinta ------------------------------------------------------
_SCAN = None


def scanlines():
    global _SCAN
    if _SCAN is None:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        sp = max(3, int(H * 0.0055))
        for y in range(0, H, sp):
            d.rectangle([0, y, W, y + max(1, sp // 3)], fill=(0, 0, 0, 46))
        _SCAN = lay
    return _SCAN


def tape_glitch(card, t, f):
    """Saltos horizontales, solo mientras la pantalla esta tapada."""
    if not 0.34 < t < 0.62:
        return card
    rng = np.random.default_rng(500 + f)
    if rng.random() > 0.42:
        return card
    arr = np.array(card)
    for _ in range(int(rng.integers(2, 6))):
        y0 = int(rng.integers(0, H - H // 18))
        hh = int(rng.integers(H // 90, H // 24))
        arr[y0:y0 + hh] = np.roll(
            arr[y0:y0 + hh], int(rng.integers(-int(W * 0.022), int(W * 0.022))), axis=1)
    return Image.fromarray(arr, "RGBA")


def scan_sweep(card, t):
    """Barrido de luz cruzando el rotulo: el 'impacto' aqui es de cinta."""
    p = seg(t, 0.36, 0.58)
    if p <= 0 or p >= 1:
        return
    x = lerp(-W * 0.35, W * 1.15, out_cubic(p))
    al = int((1 - abs(p * 2 - 1)) ** 1.5 * 62)
    if al < 3:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bw = W * 0.14
    ImageDraw.Draw(lay).polygon(
        [(x, H), (x + bw, H), (x + bw + SKEW, 0), (x + SKEW, 0)],
        fill=(255, 240, 200, al))
    card.alpha_composite(lay)


# ---- rotulo ----------------------------------------------------------------
_MEASURE = ImageDraw.Draw(Image.new("L", (1, 1)))


def word_metrics(size):
    f = font(FONT_DISPLAY, size)
    track = size * 0.07
    widths = [_MEASURE.textlength(ch, font=f) for ch in "REPLAY"]
    return f, track, widths, sum(widths) + track * (len("REPLAY") - 1)


def draw_word(card, t, x, cy, size):
    """Las letras entran escalonadas desde abajo."""
    f, track, widths, _ = word_metrics(size)
    step, dur = 0.017, 0.13
    for i, ch in enumerate("REPLAY"):
        p = seg(t, WORD_START + i * step, WORD_START + i * step + dur)
        if p > 0:
            e = out_expo(p)
            pad = int(size * 0.45)
            wi, hi = int(widths[i]) + pad * 2, int(size * 1.8)
            lay = Image.new("RGBA", (wi, hi), (0, 0, 0, 0))
            ImageDraw.Draw(lay).text((pad, hi * 0.5), ch, font=f,
                                     fill=YEL + (int(clamp01(p * 3.5) * 255),),
                                     anchor="lm")
            blur = (1 - e) * size * 0.06
            if blur > 0.6:
                lay = lay.filter(ImageFilter.GaussianBlur(blur))
            card.alpha_composite(lay, (int(x - pad),
                                       int(cy - hi * 0.5 + (1 - e) * size * 0.36)))
        x += widths[i] + track


def draw_chevrons(card, t, x0, x1, ymid, h):
    """Chevrones de rebobinado desplazandose hacia la izquierda."""
    p = seg(t, 0.36, 0.44)
    if p <= 0:
        return
    w, hh = int(x1 - x0), int(h * 2.2)
    strip = Image.new("RGBA", (w, hh), (0, 0, 0, 0))
    d = ImageDraw.Draw(strip)
    step, cw = h * 1.7, h * 0.62
    off = (t * W * 0.62) % step
    tw = max(2, int(h * 0.20))
    k = -1
    while True:
        x = k * step - off
        if x > w + step:
            break
        d.line([(x + cw, hh * 0.5 - h * 0.5), (x, hh * 0.5)], fill=YEL + (255,), width=tw)
        d.line([(x, hh * 0.5), (x + cw, hh * 0.5 + h * 0.5)], fill=YEL + (255,), width=tw)
        k += 1
    # difuminado en los extremos para que no aparezcan cortados
    grad = np.linspace(0, 1, w, dtype=np.float32)
    grad = np.minimum(np.minimum(grad * 6, (1 - grad) * 6), 1.0) * clamp01(p)
    a = np.asarray(strip.getchannel("A")).astype(np.float32) * grad[None, :]
    strip.putalpha(Image.fromarray(a.astype(np.uint8), "L"))
    card.alpha_composite(strip, (int(x0), int(ymid - hh * 0.5)))


def draw_mascot(card, t, cx, cy, target_h):
    p = seg(t, *MASCOT_T)
    if p <= 0:
        return
    e = out_expo(p)
    m = assets()["mascot"]
    th = target_h * (1.0 + 0.55 * (1 - e))
    m = m.resize((max(1, int(th * m.width / m.height)), max(1, int(th))), Image.LANCZOS)
    rot = -12.0 * (1 - e)
    if abs(rot) > 0.15:
        m = m.rotate(rot, resample=Image.BICUBIC, expand=True)
    blur = (1 - e) ** 1.4 * W * 0.006
    if blur > 0.7:
        m = m.filter(ImageFilter.GaussianBlur(blur))
    op = min(1.0, seg(t, MASCOT_T[0], MASCOT_T[0] + 0.05))
    if op < 1:
        m.putalpha(m.getchannel("A").point(lambda v: int(v * op)))
    card.alpha_composite(m, (int(cx - m.width / 2), int(cy - m.height / 2)))


def card(t, f):
    c = textured_bg(t, speed1=0.10, speed2=0.26)
    c.alpha_composite(scanlines())

    size = H * 0.215
    _, _, _, tw = word_metrics(size)
    mh = H * 0.21
    m = assets()["mascot"]
    mw = mh * m.width / m.height
    gap = W * 0.028
    gx = CX - (mw + gap + tw) / 2
    ty = CY - H * 0.03

    draw_mascot(c, t, gx + mw / 2, ty, mh)
    draw_word(c, t, gx + mw + gap, ty, size)
    draw_chevrons(c, t, gx + mw + gap, gx + mw + gap + tw, ty + H * 0.145, H * 0.038)

    scan_sweep(c, t)
    flash(c, t, IMPACT, peak=110, life=0.06)
    c = rgb_split(c, t, IMPACT, life=0.10, amount=0.0032)
    return tape_glitch(c, t, f)


def frame(f):
    t = (f + 0.5) / FPS
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    offs = {}
    for key, tin, tout in (("yel", YEL_IN, YEL_OUT), ("org", ORG_IN, ORG_OUT),
                           ("dark", DARK_IN, DARK_OUT)):
        offs[key] = (half_off(t, tin, tout, +1), half_off(t, tin, tout, -1))

    for key, col in (("yel", YEL), ("org", ORG)):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for s, off in ((+1, offs[key][0]), (-1, offs[key][1])):
            d.polygon(half_poly(off, s), fill=col + (255,))
        canvas.alpha_composite(lay)

    mask = Image.new("L", (W, H), 0)
    dm = ImageDraw.Draw(mask)
    for s, off in ((+1, offs["dark"][0]), (-1, offs["dark"][1])):
        dm.polygon(half_poly(off, s), fill=255)
    c = card(t, f)
    c.putalpha(ImageChops.multiply(c.getchannel("A"), mask))
    canvas.alpha_composite(c)

    # Filo brillante del corte. Se apaga cuando las mitades estan juntas: si no,
    # la linea parte el rotulo REPLAY justo por la mitad.
    edge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    de = ImageDraw.Draw(edge)
    for s, off in ((+1, offs["dark"][0]), (-1, offs["dark"][1])):
        k = min(1.0, abs(off - (-OVER * s)) / (W * 0.10))
        if k > 0.01:
            de.polygon(band_poly(off, s, EDGE), fill=YEL + (int(255 * k),))
    canvas.alpha_composite(edge)
    return canvas
