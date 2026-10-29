#!/usr/bin/env bash
# cut_clips.sh — cut one evidence clip per visual move from a plan CSV.
#
# Usage:   bash cut_clips.sh WORKING.mp4 clips.csv [out_dir] [width]
#   clips.csv lines:  name,start_sec,dur_sec        (header line optional, skipped if it starts with 'name')
#   defaults: out_dir=clips  width=540
#
# Notes (hard-won):
#  - KEEP AUDIO. Many moves are "synced to the voice"; the editor must hear the VO under the clip.
#  - -nostdin is required or ffmpeg eats the while-loop's stdin and skips rows.
#  - Output is web-ready (yuv420p + faststart) so clips play inline in the HTML reader over file://.
set -euo pipefail
SRC="${1:?usage: cut_clips.sh WORKING.mp4 clips.csv [out_dir] [width]}"
CSV="${2:?need clips.csv (name,start,dur)}"
OUT="${3:-clips}"
W="${4:-540}"
mkdir -p "$OUT"
while IFS=, read -r name start dur _rest; do
  [ -z "${name:-}" ] && continue
  case "$name" in name|\#*) continue;; esac          # skip header / comments
  name="$(echo "$name" | tr -cd '[:alnum:]_-')"
  ffmpeg -nostdin -y -loglevel error -ss "$start" -i "$SRC" -t "$dur" \
    -vf "scale=${W}:-2" -c:v libx264 -preset veryfast -crf 30 -pix_fmt yuv420p \
    -c:a aac -b:a 96k -movflags +faststart "$OUT/${name}.mp4"
  printf "  %-34s %ss +%ss  %s\n" "$name" "$start" "$dur" "$(du -h "$OUT/${name}.mp4" | cut -f1)"
done < "$CSV"
echo "clips in: $OUT/  ($(du -sh "$OUT" | cut -f1))"
