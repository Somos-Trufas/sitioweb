#!/usr/bin/env python3
"""Compone la demo A->B y codifica las tres entregas finales."""

import os
import subprocess
import sys

os.environ["SS"] = "1"                      # solo necesitamos demo_scene
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image                        # noqa: E402
import render                                # noqa: E402

ROOT = render.ROOT
FRAMES = render.FRAMES
OUT = render.OUT
DEMO = os.path.join(OUT, "demo")
FPS, N = render.FPS, render.N
PRE, POST = 30, 30                           # 0.5 s antes y despues
CUT = int(render.CUT_POINT * FPS)            # frame de corte dentro del stinger

os.makedirs(DEMO, exist_ok=True)

A = render.demo_scene("A").convert("RGBA")
B = render.demo_scene("B").convert("RGBA")

k = 0
for _ in range(PRE):
    A.convert("RGB").save(os.path.join(DEMO, "d%03d.png" % k))
    k += 1
for f in range(N):
    st = Image.open(os.path.join(FRAMES, "f%03d.png" % f)).convert("RGBA")
    base = A if f < CUT else B
    Image.alpha_composite(base, st).convert("RGB").save(
        os.path.join(DEMO, "d%03d.png" % k)
    )
    k += 1
for _ in range(POST):
    B.convert("RGB").save(os.path.join(DEMO, "d%03d.png" % k))
    k += 1
print("demo: %d frames (%.2f s)" % (k, k / FPS))

BASE = "transicion-somos-trufas-1080p60"
jobs = [
    # stinger para OBS: VP9 con canal alpha
    (["ffmpeg", "-y", "-framerate", str(FPS), "-i", os.path.join(FRAMES, "f%03d.png"),
      "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "20",
      "-auto-alt-ref", "0", "-row-mt", "1",
      os.path.join(OUT, BASE + ".webm")], BASE + ".webm"),
    # master de edicion: ProRes 4444 con alpha
    (["ffmpeg", "-y", "-framerate", str(FPS), "-i", os.path.join(FRAMES, "f%03d.png"),
      "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
      "-alpha_bits", "16", "-vendor", "apl0",
      os.path.join(OUT, BASE + ".mov")], BASE + ".mov"),
    # vista previa del efecto
    (["ffmpeg", "-y", "-framerate", str(FPS), "-i", os.path.join(DEMO, "d%03d.png"),
      "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-preset", "slow",
      "-movflags", "+faststart",
      os.path.join(OUT, BASE.replace("1080p60", "DEMO-1080p60") + ".mp4")],
     BASE.replace("1080p60", "DEMO-1080p60") + ".mp4"),
]

for cmd, name in jobs:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FALLO", name)
        print(r.stderr[-1500:])
        sys.exit(1)
    p = cmd[-1]
    print("ok  %-46s %7.2f MB" % (name, os.path.getsize(p) / 1e6))


# --- verificacion: el alpha debe sobrevivir a la codificacion ---------------
# ffmpeg guarda el alpha de WebM en un stream aparte: el decoder nativo lo
# ignora, hay que pedir libvpx/libvpx-vp9 explicitamente para comprobarlo.
import numpy as np                            # noqa: E402

ref = np.asarray(Image.open(os.path.join(FRAMES, "f003.png")).getchannel("A"))
ref_t = float((ref == 0).mean())
for f, dec in ((BASE + ".webm", "libvpx-vp9"), (BASE + ".mov", None)):
    tmp = os.path.join(OUT, ".chk.png")
    cmd = ["ffmpeg", "-y", "-v", "error"]
    if dec:
        cmd += ["-c:v", dec]
    cmd += ["-i", os.path.join(OUT, f), "-vf", "select=eq(n\\,3)",
            "-vframes", "1", "-pix_fmt", "rgba", tmp]
    subprocess.run(cmd, capture_output=True)
    got = np.asarray(Image.open(tmp).convert("RGBA").getchannel("A"))
    got_t = float((got == 0).mean())
    ok = abs(got_t - ref_t) < 0.02
    print("    alpha %-42s %s (%.1f%% vs %.1f%% ref)"
          % (f, "OK" if ok else "PERDIDO", got_t * 100, ref_t * 100))
    os.remove(tmp)
