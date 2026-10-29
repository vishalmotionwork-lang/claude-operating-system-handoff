#!/usr/bin/env bash
# Copy this handoff into ~/.claude and ~ without overwriting anything.
# Usage: ./install.sh          (dry run)
#        ./install.sh --apply  (copy)
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
HOME_SLUG="$(printf '%s' "$HOME" | tr '/.' '--')"
MEMORY_DIR="$CLAUDE_DIR/projects/$HOME_SLUG/memory"
APPLY=false
[ "${1:-}" = "--apply" ] && APPLY=true

copied=0; skipped=0

place() {  # place <src-file> <dest-file>
  local src="$1" dest="$2"
  if [ -e "$dest" ]; then
    echo "  skip (exists)  $dest"; skipped=$((skipped + 1)); return
  fi
  echo "  copy           $dest"; copied=$((copied + 1))
  if $APPLY; then mkdir -p "$(dirname "$dest")"; cp "$src" "$dest"; fi
}

place_tree() {  # place_tree <src-dir> <dest-dir>
  local src="$1" dest="$2" f
  while IFS= read -r -d '' f; do
    place "$f" "$dest/${f#"$src"/}"
  done < <(find "$src" -type f -print0)
}

echo "Memory folder: $MEMORY_DIR"
$APPLY || echo "(dry run — pass --apply to copy)"

place "$REPO/templates/CLAUDE.md"     "$HOME/CLAUDE.md"
place "$REPO/templates/settings.json" "$CLAUDE_DIR/settings.json"
place_tree "$REPO/templates/rules"    "$CLAUDE_DIR/rules"
place_tree "$REPO/templates/memory"   "$MEMORY_DIR"
place_tree "$REPO/skills"             "$CLAUDE_DIR/skills"
place_tree "$REPO/hooks"              "$CLAUDE_DIR/hooks"
place_tree "$REPO/scripts"            "$CLAUDE_DIR/scripts"
place_tree "$REPO/commands"           "$CLAUDE_DIR/commands"

if $APPLY; then
  chmod +x "$CLAUDE_DIR"/hooks/*.sh "$CLAUDE_DIR"/scripts/*.sh 2>/dev/null || true
  mkdir -p "$CLAUDE_DIR/context"
fi

echo "Done: $copied to copy, $skipped skipped. Next: docs/07-install.md steps 4-9."
