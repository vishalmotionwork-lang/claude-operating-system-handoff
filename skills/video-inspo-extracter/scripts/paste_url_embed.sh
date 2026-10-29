#!/bin/bash
# Paste a URL into the front Figma/FigJam window -> creates a clickable EMBED widget
# (e.g. a YouTube player card). Use for the "source video link on top" of a board.
# Usage: paste_url_embed.sh "https://www.youtube.com/watch?v=..."
printf "%s" "$1" | pbcopy
osascript -e 'tell application "Figma" to activate' >/dev/null 2>&1
sleep 1
osascript -e 'tell application "System Events" to keystroke "v" using command down' >/dev/null 2>&1
echo "url pasted as embed: $1"
