#!/bin/bash
# Cut every passage in a merged plan into its own clip.
# Usage: extract_clips.sh <video> <plan_merged.csv> [outdir=clips] [height=720] [crf=23]
set -e
VIDEO="$1"; PLAN="$2"; OUT="${3:-clips}"; H="${4:-720}"; CRF="${5:-23}"
[ -f "$VIDEO" ] && [ -f "$PLAN" ] || { echo "usage: extract_clips.sh <video> <plan_merged.csv> [outdir] [height] [crf]" >&2; exit 1; }
mkdir -p "$OUT"
# -nostdin is MANDATORY: without it ffmpeg consumes the while-read loop's stdin and skips clips.
tail -n +2 "$PLAN" | while IFS=, read seg cls start end dur stc etc nshots shots; do
  name=$(printf "seg%02d_%s_%s-%s" "$seg" "$cls" "${stc//:/}" "${etc//:/}")
  ffmpeg -nostdin -y -ss "$start" -t "$dur" -i "$VIDEO" \
    -vf "scale=-2:$H" -c:v libx264 -preset veryfast -crf "$CRF" \
    -c:a aac -b:a 128k -movflags +faststart "$OUT/${name}.mp4" >/dev/null 2>&1
  echo "cut $name (${dur}s)"
done
echo "DONE: $(ls "$OUT"/*.mp4 | wc -l | tr -d ' ') clips in $OUT/ ($(du -sh "$OUT" | cut -f1))"
