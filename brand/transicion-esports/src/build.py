#!/usr/bin/env python3
"""
Renderiza y codifica las transiciones.

    python3 build.py                 # todas
    python3 build.py replay          # solo una
    python3 build.py iris --preview 10,24,36

Salida: WebM VP9 con alpha en la carpeta padre, listo para OBS.
"""

import importlib
import os
import sys

import common as C

STYLES = ["sweep", "iris", "replay"]
DEST = os.path.dirname(C.ROOT)


def build(name, preview=None):
    style = importlib.import_module(name)
    if preview is not None:
        os.makedirs(os.path.join(C.OUT, style.NAME), exist_ok=True)
        for f in preview:
            C.finish(style.frame(f), f).save(
                os.path.join(C.OUT, style.NAME, "preview_%02d.png" % f))
        print("  preview %s: %s" % (style.NAME, preview))
        return

    print("[%s] %s" % (style.NAME, style.TITLE))
    C.render_sequence(style)

    a, b, n = C.coverage(style)
    if n == 0:
        print("  AVISO: ningun frame llega a opacidad total")
    else:
        print("  opaco 100%%: %.3f s -> %.3f s (%d frames)" % (a, b, n))
        if not a <= style.CUT_POINT <= b:
            print("  AVISO: el corte en %.2f s cae fuera de la ventana"
                  % style.CUT_POINT)

    out = os.path.join(DEST, "transicion-%s-1080p60.webm" % style.NAME)
    C.encode_webm(style, out)
    ok, got, ref = C.verify_alpha(style, out)
    print("  %-44s %5.2f MB  alpha %s"
          % (os.path.basename(out), os.path.getsize(out) / 1e6,
             "OK" if ok else "PERDIDO (%.1f%% vs %.1f%%)" % (got * 100, ref * 100)))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    preview = None
    if "--preview" in args:
        i = args.index("--preview")
        preview = [int(x) for x in args[i + 1].split(",")]
        args = args[:i]
    for name in (args or STYLES):
        build(name, preview)
