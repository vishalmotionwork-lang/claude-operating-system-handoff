#!/usr/bin/env python3
"""
Scene-detect a video and build labeled contact sheets for visual classification.

Usage (run via uvx so deps are isolated):
  uvx --with opencv-python-headless --with numpy --from scenedetect \
      python3 detect_and_sheet.py <video.mp4> [threshold]

Outputs:
  scenes.csv     -> idx,start,end,dur,start_tc,end_tc  (every detected shot)
  sheets/        -> sheet_NN.jpg contact sheets (4 cols x 5 rows), each tile a
                    mid-shot frame with "idx  mm:ss-mm:ss  Ns" burned in.

Lower threshold => more (finer) shots. 27 is a good default; drop to ~22 for very
fast-cut / graphics-heavy edits, raise to ~32 to merge.
"""
import cv2, csv, math, os, sys, numpy as np
from scenedetect import detect, ContentDetector

VIDEO = sys.argv[1] if len(sys.argv) > 1 else "video.mp4"
THRESH = float(sys.argv[2]) if len(sys.argv) > 2 else 27.0
OUT = "sheets"; os.makedirs(OUT, exist_ok=True)
TW, TH, COLS, ROWS = 480, 270, 4, 5
mmss = lambda s: f"{int(s//60):02d}:{int(s%60):02d}"

print(f"[1/3] detecting shots (ContentDetector thr={THRESH}) ...", flush=True)
scenes = detect(VIDEO, ContentDetector(threshold=THRESH, min_scene_len=12))
print(f"   -> {len(scenes)} shots", flush=True)

cap = cv2.VideoCapture(VIDEO); rows = []; thumbs = []
for i, (s, e) in enumerate(scenes):
    a, b = s.get_seconds(), e.get_seconds()
    cap.set(cv2.CAP_PROP_POS_MSEC, ((a + b) / 2.0) * 1000)
    ok, fr = cap.read()
    if not ok:
        cap.set(cv2.CAP_PROP_POS_MSEC, a * 1000); ok, fr = cap.read()
    fr = cv2.resize(fr, (TW, TH)) if ok else np.zeros((TH, TW, 3), "uint8")
    label = f"{i:03d}  {mmss(a)}-{mmss(b)}  {b-a:.1f}s"
    cv2.rectangle(fr, (0, 0), (TW, 22), (0, 0, 0), -1)
    cv2.putText(fr, label, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
    cv2.rectangle(fr, (0, 0), (TW-1, TH-1), (60, 60, 60), 1)
    thumbs.append(fr)
    rows.append({"idx": i, "start": round(a, 2), "end": round(b, 2), "dur": round(b-a, 2),
                 "start_tc": mmss(a), "end_tc": mmss(b)})
cap.release()

with open("scenes.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

print("[2/3] building contact sheets ...", flush=True)
PER = COLS * ROWS
for sh in range(math.ceil(len(thumbs) / PER)):
    chunk = thumbs[sh*PER:(sh+1)*PER]
    while len(chunk) < PER: chunk.append(np.zeros((TH, TW, 3), "uint8"))
    sheet = cv2.vconcat([cv2.hconcat(chunk[r*COLS:(r+1)*COLS]) for r in range(ROWS)])
    cv2.imwrite(f"{OUT}/sheet_{sh:02d}.jpg", sheet, [cv2.IMWRITE_JPEG_QUALITY, 80])
print(f"[3/3] done: {len(thumbs)} shots, {math.ceil(len(thumbs)/PER)} sheets, scenes.csv", flush=True)
