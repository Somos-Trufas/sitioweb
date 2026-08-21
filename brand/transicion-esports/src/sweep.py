#!/usr/bin/env python3
"""
Estilo 1 — BARRIDO.

Tres bandas a 18 grados cruzan de derecha a izquierda, la mascota golpea en el
centro y las bandas salen en cascada por la izquierda.
"""

from common import *          # toolkit interno: paleta, easing, geometria

NAME = "barrido"
TITLE = "Barrido diagonal"
CUT_POINT = 0.50

YEL_IN, ORG_IN, DARK_IN = (0.00, 0.24), (0.05, 0.29), (0.10, 0.34)
DARK_OUT, ORG_OUT, YEL_OUT = (0.60, 0.86), (0.64, 0.90), (0.68, 0.96)
MASCOT_T, WORD_T, IMPACT = (0.24, 0.40), (0.29, 0.45), 0.385

_rng = np.random.default_rng(11)
SHARDS = []
for _i in range(26):
    _diag = _i % 5 != 0                      # 4 de cada 5 siguen la diagonal
    SHARDS.append(dict(
        y=float(_rng.uniform(-0.06, 0.95)),
        h=float(_rng.uniform(0.14, 0.55) if _diag else _rng.uniform(0.008, 0.030)),
        w=float(_rng.uniform(0.0025, 0.013) if _diag else _rng.uniform(0.08, 0.32)),
        d=float(_rng.uniform(0.0, 0.28)),
        c=[YEL, ORG, WHITE, YEL, YEL, ORG][_i % 6],
        a=int(_rng.uniform(120, 255)),
    ))


def draw_shards(layer, t):
    d = ImageDraw.Draw(layer)
    tail = 1.0 - seg(t, 0.955, 1.0)          # nada queda colgado al final
    for sh in SHARDS:
        wins = ((sh["d"] * 0.40, 0.28 + sh["d"] * 0.40),
                (0.78 + sh["d"] * 0.14, 0.97 + sh["d"] * 0.14))
        for k, win in enumerate(wins):
            p = seg(t, *win)
            if p <= 0 or p >= 1:
                continue
            x = lerp(W * 1.20, -W * 0.60, out_cubic(p) if k == 0 else p)
            y0, y1 = sh["y"] * H, sh["y"] * H + sh["h"] * H
            bw = sh["w"] * W
            o0, o1 = (1 - y0 / H) * SKEW, (1 - y1 / H) * SKEW
            a = int(sh["a"] * min(1.0, (1 - p) * 3.2, p * 6.0) * (tail if k else 1.0))
            if a < 3:
                continue
            d.polygon([(x + o0, y0), (x + bw + o0, y0),
                       (x + bw + o1, y1), (x + o1, y1)], fill=sh["c"] + (a,))


def card(t, logo_dx=0.0):
    c = textured_bg(t)
    cx, cy = W / 2 + logo_dx, H / 2
    draw_shockwave(c, t, IMPACT, cx, cy)
    draw_lockup(c, t, MASCOT_T, WORD_T, cx, cy, W * 0.50)
    flash(c, t, IMPACT)
    return rgb_split(c, t, IMPACT)


def frame(f):
    t = (f + 0.5) / FPS
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_shards(canvas, t)

    for tin, tout, col, edge, ew in (
        (YEL_IN, YEL_OUT, YEL, WHITE, W * 0.0035),
        (ORG_IN, ORG_OUT, ORG, YEL, W * 0.0055),
    ):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_slab(lay, slab_x(t, tin, tout), col, edge, ew)
        canvas.alpha_composite(lay)

    xb = slab_x(t, DARK_IN, DARK_OUT)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon(slab_poly(xb), fill=255)
    # parallax: el logo acompana la salida de la banda, pero mas lento
    c = card(t, logo_dx=(xb - XB_IN) * 0.34 if t > DARK_OUT[0] else 0.0)
    c.putalpha(ImageChops.multiply(c.getchannel("A"), mask))
    canvas.alpha_composite(c)

    edge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ew, x2 = W * 0.0042, xb + SLABW
    ImageDraw.Draw(edge).polygon(
        [(x2 - ew, H), (x2, H), (x2 + SKEW, 0), (x2 - ew + SKEW, 0)], fill=YEL + (255,))
    canvas.alpha_composite(edge)
    return canvas
