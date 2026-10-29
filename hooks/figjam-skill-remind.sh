#!/usr/bin/env bash
# Fires before figma-console FigJam creation/edit tools.
# Injects a reminder to use the /figjam-board place-and-verify engine
# instead of hand-rolling board JS. STOP-style: treat as required.
cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"STOP — FigJam board work detected. Use the /figjam-board skill, do NOT hand-roll board JS. Read ~/.claude/skills/figjam-board/figjam-kit.js and paste it in full at the top of your figma_execute call, then build with zone()/card()/kanban()/text(), call verify() and resolve warnings BEFORE screenshotting, and finish() to wrap in one movable section. This neutralizes FigJam's coordinate traps (section appendChild origin-add, stale absoluteBoundingBox, no createPage). See SKILL.md for the full flow."}}
JSON
exit 0
