#!/usr/bin/env python3
"""
grid_decode.py — turn a video into timecoded contact-grid sheets for STYLE decoding.

Why this and not scene-detect: motion-graphics / short-form grammar lives in the
ON-SCREEN TEXT and overlays that animate over continuous footage, NOT in hard cuts.
ContentDetector under-counts those (it sees gradual change). A fixed-cadence frame
grid with timecodes burned in lets you SEE exactly what's on screen at every beat and
map each script line to its visual treatment.

Usage:
  uvx --with pillow python3 grid_decode.py VIDEO [fps] [cols] [rows] [thumb_w]
  defaults: fps=2  cols=4  rows=5  thumb_w=240   (=> 20 frames/sheet, 0.5s step)

Outputs: frames/f_####.jpg  and  grids/grid_##.jpg  (each labeled `t=..s  #idx`).
Read the grids top-to-bottom; the label tells you the exact timestamp of each frame.
"""
import sys, os, glob, subprocess
from PIL import Image, ImageDraw, ImageFont

video = sys.argv[1]
fps   = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
cols  = int(sys.argv[3])   if len(sys.argv) > 3 else 4
rows  = int(sys.argv[4])   if len(sys.argv) > 4 else 5
tw    = int(sys.argv[5])   if len(sys.argv) > 5 else 240

os.makedirs("frames", exist_ok=True)
os.makedirs("grids",  exist_ok=True)
for f in glob.glob("frames/f_*.jpg"): os.remove(f)
for f in glob.glob("grids/grid_*.jpg"): os.remove(f)

subprocess.run(
    ["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", video,
     "-vf", f"fps={fps},scale={tw}:-1", "frames/f_%04d.jpg"], check=True)

frames = sorted(glob.glob("frames/f_*.jpg"))
if not frames:
    sys.exit("no frames extracted")
step = 1.0 / fps
per  = cols * rows
labelh = 24
th = Image.open(frames[0]).size[1]
cellw, cellh = tw, th + labelh
for fp in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
           "/Library/Fonts/Arial Bold.ttf"):
    try:
        font = ImageFont.truetype(fp, 18); break
    except Exception:
        font = ImageFont.load_default()

n_sheets = (len(frames) + per - 1) // per
for s in range(n_sheets):
    chunk = frames[s*per:(s+1)*per]
    sheet = Image.new("RGB", (cols*cellw, rows*cellh), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    for i, fpth in enumerate(chunk):
        idx = s*per + i
        t = idx * step
        cx, cy = (i % cols)*cellw, (i // cols)*cellh
        d.rectangle([cx, cy, cx+cellw, cy+labelh], fill=(0, 90, 160))
        d.text((cx+5, cy+3), f"t={t:0.1f}s  #{idx}", fill=(255, 255, 255), font=font)
        sheet.paste(Image.open(fpth), (cx, cy+labelh))
    out = f"grids/grid_{s:02d}.jpg"
    sheet.save(out, quality=88)
    print(out, f"covers t={s*per*step:.1f}-{((s+1)*per-1)*step:.1f}s")
print(f"{len(frames)} frames -> {n_sheets} grids @ {fps}fps")
