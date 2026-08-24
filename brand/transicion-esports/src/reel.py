#!/usr/bin/env python3
"""
Estilo 4 — REEL (vertical 1080x1920).

Las mismas bandas de 18 grados, pero transpuestas: barren de abajo arriba, que
es lo que funciona en 9:16 —un barrido lateral cruza 1080 px en nada y se pierde
el gesto—. Solo la mascota, sin logotipo: el lockup oficial es horizontal y en
un frame estrecho quedaria diminuto.

    FORMAT=vertical python3 build.py reel
"""

from common import *

NAME = "reel"
TITLE = "Reel vertical (solo mascota)"
FORMAT = "vertical"
CUT_POINT = 0.50

YEL_IN, ORG_IN, DARK_IN = (0.00, 0.24), (0.05, 0.29), (0.10, 0.34)
DARK_OUT, ORG_OUT, YEL_OUT = (0.60, 0.86), (0.64, 0.90), (0.68, 0.96)
MASCOT_T, IMPACT = (0.24, 0.40), 0.385

MASCOT_W = 0.62          # ancho de la mascota, en anchos de frame

_rng = np.random.default_rng(11)
SHARDS = []
for _i in range(26):
    _diag = _i % 5 != 0                      # 4 de cada 5 siguen la diagonal
    SHARDS.append(dict(
        x=float(_rng.uniform(-0.06, 0.95)),
        w=float(_rng.uniform(0.14, 0.55) if _diag else _rng.uniform(0.008, 0.030)),
        h=float(_rng.uniform(0.0025, 0.013) if _diag else _rng.uniform(0.08, 0.32)),
        d=float(_rng.uniform(0.0, 0.28)),
        c=[YEL, ORG, WHITE, YEL, YEL, ORG][_i % 6],
        a=int(_rng.uniform(120, 255)),
    ))


def draw_shards(layer, t):
    """Esquirlas subiendo, alineadas con el angulo de las bandas."""
    d = ImageDraw.Draw(layer)
    tail = 1.0 - seg(t, 0.955, 1.0)          # nada queda colgado al final
    for sh in SHARDS:
        wins = ((sh["d"] * 0.40, 0.28 + sh["d"] * 0.40),
                (0.78 + sh["d"] * 0.14, 0.97 + sh["d"] * 0.14))
        for k, win in enumerate(wins):
            p = seg(t, *win)
            if p <= 0 or p >= 1:
                continue
            y = lerp(H * 1.20, -H * 0.60, out_cubic(p) if k == 0 else p)
            x0, x1 = sh["x"] * W, sh["x"] * W + sh["w"] * W
            bh = sh["h"] * H
            o0, o1 = -(x0 / W) * SKEWV, -(x1 / W) * SKEWV
            a = int(sh["a"] * min(1.0, (1 - p) * 3.2, p * 6.0) * (tail if k else 1.0))
            if a < 3:
                continue
            d.polygon([(x0, y + o0), (x1, y + o1),
                       (x1, y + o1 + bh), (x0, y + o0 + bh)], fill=sh["c"] + (a,))


def card(t, logo_dy=0.0):
    c = textured_bg(t)
    cx, cy = W / 2, H / 2 + logo_dy
    draw_shockwave(c, t, IMPACT, cx, cy, ring_scale=1.35, burst_scale=2.3)
    draw_mascot_hit(c, t, MASCOT_T, cx, cy, W * MASCOT_W)
    flash(c, t, IMPACT)
    return rgb_split(c, t, IMPACT)


def frame(f):
    t = (f + 0.5) / FPS
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_shards(canvas, t)

    for tin, tout, col, edge, ew in (
        (YEL_IN, YEL_OUT, YEL, WHITE, H * 0.0035),
        (ORG_IN, ORG_OUT, ORG, YEL, H * 0.0055),
    ):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_vslab(lay, vslab_y(t, tin, tout), col, edge, ew)
        canvas.alpha_composite(lay)

    yb = vslab_y(t, DARK_IN, DARK_OUT)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon(vslab_poly(yb), fill=255)
    # parallax: la mascota acompana la salida de la banda, pero mas lento
    c = card(t, logo_dy=(yb - YB_IN) * 0.34 if t > DARK_OUT[0] else 0.0)
    c.putalpha(ImageChops.multiply(c.getchannel("A"), mask))
    canvas.alpha_composite(c)

    edge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ew = H * 0.0042
    ImageDraw.Draw(edge).polygon(
        [(0, yb), (W, yb - SKEWV), (W, yb - SKEWV + ew), (0, yb + ew)],
        fill=YEL + (255,))
    canvas.alpha_composite(edge)
    return canvas
