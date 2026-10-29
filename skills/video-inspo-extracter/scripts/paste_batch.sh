#!/bin/bash
# Auto-paste a batch of clips into the FRONT Figma window via scripted Cmd+V.
# No manual clicking. Pairs with the plugin positioning step (see reference/board-grid.md).
#
# Usage: paste_batch.sh <clipsdir> <start_index> <count> [sleep_per=2.2]
#
# Clips are taken in `ls | sort` order (so name them segNN_... for timeline order).
# Each paste lands at viewport center; the plugin repositions afterwards by id order.
#
# REQUIREMENT: the terminal/host running this must have macOS Accessibility permission
# (System Settings > Privacy & Security > Accessibility) or the keystroke is silently
# dropped. Test with one clip first and confirm a new MEDIA node appears via the plugin.
cd "$1" 2>/dev/null || { echo "bad clipsdir: $1" >&2; exit 1; }
CLIPS=( $(ls *.mp4 2>/dev/null | sort) )
START="$2"; COUNT="$3"; SLP="${4:-2.2}"
end=$((START+COUNT)); k=$START
while [ $k -lt $end ] && [ $k -lt ${#CLIPS[@]} ]; do
  f="$PWD/${CLIPS[$k]}"
  osascript -e "set ff to POSIX file \"$f\"" -e 'tell application "Finder" to set the clipboard to ff' >/dev/null 2>&1
  osascript -e 'tell application "Figma" to activate' >/dev/null 2>&1
  sleep 0.5
  osascript -e 'tell application "System Events" to keystroke "v" using command down' >/dev/null 2>&1
  sleep "$SLP"
  k=$((k+1))
done
echo "pasted clips $START..$((k-1)) of ${#CLIPS[@]}"
