#!/usr/bin/env python3
"""
Estilo 2 — IRIS.

La silueta de la propia mascota crece desde el centro hasta tragarse la
pantalla, y despues se abre como un agujero con forma de trufa para revelar la
escena nueva. El mecanismo es radial, no un barrido: es lo que lo diferencia
del estilo 1 aunque comparta paleta y lockup.
"""

from common import *

NAME = "iris"
TITLE = "Iris de mascota"
CUT_POINT = 0.50

YEL_IN, ORG_IN, DARK_IN = (0.02, 0.27), (0.06, 0.31), (0.10, 0.35)
DARK_OUT, ORG_OUT, YEL_OUT = (0.60, 0.84), (0.65, 0.89), (0.70, 0.95)
MASCOT_T, WORD_T, IMPACT = (0.27, 0.43), (0.32, 0.48), 0.415

SEED = 0.012                 # la silueta arranca como un punto en el centro


def _cover():
    return assets()["sil_cover"] * 1.06


def layer_mask(t, tin, tout, spin_in, spin_out):
    """
    Cierra con la silueta creciendo; mantiene pantalla completa; abre con un
    agujero con la misma forma. Devuelve None si la capa no tapa nada.
    """
    cov = _cover()
    if t < tin[0]:
        return None
    if t < tin[1]:
        # in_out_cubic deja unos frames a tamano legible antes de tragarse todo
        p = in_out_cubic(seg(t, *tin))
        return sil_mask(lerp(SEED, cov, p), rot=lerp(spin_in, 0.0, p))
    if t < tout[0]:
        return Image.new("L", (W, H), 255)
    p = accel(seg(t, *tout))
    hole = sil_mask(lerp(SEED, cov * 1.10, p), rot=lerp(0.0, spin_out, p))
    return ImageChops.invert(hole)


def draw_sparks(layer, t):
    """Chispas radiales al abrir y al cerrar, para que no aparezca de la nada."""
    d = ImageDraw.Draw(layer)
    cx, cy = W / 2, H / 2
    for win, outward in (((0.00, 0.15), True), ((0.85, 1.00), False)):
        p = seg(t, *win)
        if p <= 0 or p >= 1:
            continue
        e = out_cubic(p) if outward else p
        al = int((1 - abs(p * 2 - 1)) ** 1.4 * 210)
        if al < 4:
            continue
        for i in range(14):
            ang = (i / 14) * math.tau + (0.2 if outward else 1.1)
            r0 = W * (0.10 + e * 0.52) if outward else W * (0.62 - e * 0.50)
            r1 = r0 + W * 0.075 * (1 - e if outward else e)
            d.line([cx + r0 * math.cos(ang), cy + r0 * math.sin(ang),
                    cx + r1 * math.cos(ang), cy + r1 * math.sin(ang)],
                   fill=(YEL if i % 3 else ORG) + (al,),
                   width=max(2, int(W * 0.0028)))


def card(t):
    c = textured_bg(t, speed1=0.16, speed2=0.42)
    cx, cy = W / 2, H / 2
    draw_shockwave(c, t, IMPACT, cx, cy)

    # el logo se va hacia el espectador antes de que el agujero lo perfore
    ex = out_cubic(seg(t, DARK_OUT[0], DARK_OUT[0] + 0.14))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_lockup(lay, t, MASCOT_T, WORD_T, cx, cy, W * 0.50 * (1 + 0.38 * ex))
    if ex > 0:
        k = int(255 * (1 - ex))
        lay.putalpha(lay.getchannel("A").point(lambda v: v * k // 255))
    c.alpha_composite(lay)

    flash(c, t, IMPACT)
    return rgb_split(c, t, IMPACT)


def frame(f):
    t = (f + 0.5) / FPS
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_sparks(canvas, t)

    # amarillo y naranja van por delante: dejan un reborde de color al crecer
    for tin, tout, col, si, so in ((YEL_IN, YEL_OUT, YEL, -34.0, 26.0),
                                   (ORG_IN, ORG_OUT, ORG, -28.0, 21.0)):
        m = layer_mask(t, tin, tout, si, so)
        if m is None:
            continue
        lay = Image.new("RGBA", (W, H), col + (255,))
        lay.putalpha(m)
        canvas.alpha_composite(lay)

    m = layer_mask(t, DARK_IN, DARK_OUT, -22.0, 16.0)
    if m is not None:
        c = card(t)
        c.putalpha(ImageChops.multiply(c.getchannel("A"), m))
        canvas.alpha_composite(c)
    return canvas
