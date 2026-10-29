#!/bin/bash
# Put a file on the macOS clipboard as a real file reference («class furl») so that
# Cmd+V in Figma/FigJam imports it as media — exactly like a Finder copy-paste.
# (base64 / createVideoAsync do NOT work for FigJam video.)
# Usage: set_clipboard.sh /absolute/path/to/file.mp4
F="$1"
[ -f "$F" ] || { echo "no file: $F" >&2; exit 1; }
ABS="$(cd "$(dirname "$F")" && pwd)/$(basename "$F")"
osascript -e "set ff to POSIX file \"$ABS\"" -e 'tell application "Finder" to set the clipboard to ff'
echo "clipboard <- $ABS"
