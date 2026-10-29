#!/usr/bin/env python3
"""
Turn a per-shot A/B/C classification (made by the agent after viewing the contact
sheets) into extraction plans.

Usage:
  python3 plan_from_classes.py scenes.csv classes.txt [merge_gap_seconds]

classes.txt may be either:
  - one continuous string of letters, one per shot in order, e.g.  AAABCCAB...
    (length MUST equal the number of shots in scenes.csv), OR
  - lines "idx,cls"  (e.g.  0,A / 1,A / 2,C ...); any shot not listed defaults A.

Classes:
  A = no talking head      (b-roll / animation / screen-rec / charts / external)  -> KEEP
  B = talking head+overlay (presenter on camera with graphics/text on top)        -> KEEP
  C = plain talking head    (skip)

Outputs:
  plan_per_shot.csv  -> every KEEP shot (A or B)
  plan_merged.csv    -> consecutive same-category KEEP shots merged into passages
                        (seg,cls,start,end,dur,start_tc,end_tc,nshots,shots)
"""
import csv, sys
from collections import Counter

scenes_path = sys.argv[1]
classes_path = sys.argv[2]
GAP = float(sys.argv[3]) if len(sys.argv) > 3 else 0.2
mmss = lambda s: f"{int(s//60):02d}:{int(s%60):02d}"

rows = list(csv.DictReader(open(scenes_path)))
for r in rows:
    r["start"], r["end"], r["dur"] = float(r["start"]), float(r["end"]), float(r["dur"])

raw = open(classes_path).read().strip()
cls_by_idx = {}
if "," in raw or "\n" in raw and all(("," in l) for l in raw.splitlines() if l.strip()):
    for line in raw.splitlines():
        if not line.strip(): continue
        i, c = line.split(","); cls_by_idx[int(i)] = c.strip().upper()
else:
    seq = "".join(ch for ch in raw if ch.upper() in "ABC").upper()
    assert len(seq) == len(rows), f"classes ({len(seq)}) != shots ({len(rows)})"
    cls_by_idx = {i: seq[i] for i in range(len(rows))}

for r in rows:
    r["cls"] = cls_by_idx.get(int(r["idx"]), "A")

cnt = Counter(r["cls"] for r in rows)
dur = {k: sum(r["dur"] for r in rows if r["cls"] == k) for k in "ABC"}
total = sum(r["dur"] for r in rows) or 1
print("=== PER-SHOT ===")
for k in "ABC":
    print(f"  {k}: {cnt[k]:3d} shots  {dur[k]:7.1f}s  ({dur[k]/total*100:4.1f}%)")
print(f"  KEEP (A+B): {cnt['A']+cnt['B']} shots, {dur['A']+dur['B']:.1f}s")

def merge(rows, same_cat=True):
    segs = []; cur = None
    for r in rows:
        if r["cls"] not in ("A", "B"): cur = None; continue
        if cur and (not same_cat or cur["cls"] == r["cls"]) and abs(r["start"]-cur["end"]) < GAP:
            cur["end"] = r["end"]; cur["shots"].append(int(r["idx"]))
        else:
            cur = {"cls": r["cls"], "start": r["start"], "end": r["end"], "shots": [int(r["idx"])]}
            segs.append(cur)
    return segs

seg_cat = merge(rows, True)
print(f"\nMERGED (same-category): {len(seg_cat)} passages")
print(f"MERGED (any keep run):  {len(merge(rows, False))} passages")

with open("plan_per_shot.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["idx","cls","start","end","dur","start_tc","end_tc"])
    for r in rows:
        if r["cls"] in ("A","B"):
            w.writerow([r["idx"],r["cls"],r["start"],r["end"],round(r["dur"],2),mmss(r["start"]),mmss(r["end"])])
with open("plan_merged.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["seg","cls","start","end","dur","start_tc","end_tc","nshots","shots"])
    for n, s in enumerate(seg_cat):
        w.writerow([n, s["cls"], round(s["start"],2), round(s["end"],2), round(s["end"]-s["start"],2),
                    mmss(s["start"]), mmss(s["end"]), len(s["shots"]),
                    f"{s['shots'][0]}-{s['shots'][-1]}"])
print("wrote plan_per_shot.csv + plan_merged.csv")
