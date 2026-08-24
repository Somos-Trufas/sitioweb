#!/usr/bin/env python3
"""
Renderiza y codifica las transiciones.

    python3 build.py                          # todas las horizontales
    python3 build.py replay                   # solo una
    python3 build.py iris --preview 10,24,36
    FORMAT=vertical python3 build.py reel     # 1080x1920 para reels

Salida: WebM VP9 con alpha en la carpeta padre, listo para OBS.
"""

import importlib
import os
import sys

import common as C

STYLES = ["sweep", "iris", "replay", "reel"]
DEST = os.path.dirname(C.ROOT)
CUR = "vertical" if C.VERTICAL else "horizontal"
TAG = "1080x1920p60" if C.VERTICAL else "1080p60"


def style_format(name):
    return getattr(importlib.import_module(name), "FORMAT", "horizontal")


def build(name, preview=None):
    style = importlib.import_module(name)
    want = getattr(style, "FORMAT", "horizontal")
    if want != CUR:
        env = "FORMAT=vertical " if want == "vertical" else ""
        sys.exit("[%s] es %s; ejecuta:  %spython3 build.py %s"
                 % (name, want, env, name))

    if preview is not None:
        os.makedirs(os.path.join(C.OUT, style.NAME), exist_ok=True)
        for f in preview:
            C.finish(style.frame(f), f).save(
                os.path.join(C.OUT, style.NAME, "preview_%02d.png" % f))
        print("  preview %s: %s" % (style.NAME, preview))
        return

    print("[%s] %s%s" % (style.NAME, style.TITLE,
                         "  (%s)" % style.NOTE if hasattr(style, "NOTE") else ""))
    C.render_sequence(style)

    a, b, n = C.coverage(style)
    if n == 0:
        print("  AVISO: ningun frame llega a opacidad total")
    else:
        print("  opaco 100%%: %.3f s -> %.3f s (%d frames)" % (a, b, n))
        if not a <= style.CUT_POINT <= b:
            print("  AVISO: el corte en %.2f s cae fuera de la ventana"
                  % style.CUT_POINT)

    out = os.path.join(DEST, "transicion-%s-%s.webm" % (style.NAME, TAG))
    C.encode_webm(style, out)
    ok, got, ref = C.verify_alpha(style, out)
    print("  %-44s %5.2f MB  %dx%d  alpha %s"
          % (os.path.basename(out), os.path.getsize(out) / 1e6, C.W0, C.H0,
             "OK" if ok else "PERDIDO (%.1f%% vs %.1f%%)" % (got * 100, ref * 100)))


if __name__ == "__main__":
    args = list(sys.argv[1:])
    preview = None
    if "--preview" in args:
        i = args.index("--preview")
        preview = [int(x) for x in args[i + 1].split(",")]
        args = args[:i]
    for name in (args or [s for s in STYLES if style_format(s) == CUR]):
        build(name, preview)
