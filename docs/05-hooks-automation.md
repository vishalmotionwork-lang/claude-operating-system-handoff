# 05 — Hooks and automation

Hooks run shell commands on Claude Code events. They're configured in `~/.claude/settings.json` (template: [`templates/settings.json`](../templates/settings.json)).

## Active hooks

| Event | Matcher | Hook | Does |
|---|---|---|---|
| SessionStart | — | `crg-auto-build.sh` | Builds a code-review graph for the repo if none exists |
| SessionStart | — | `gsd-check-update.js`, `gsd-session-state.sh` | GSD update check + loads `.planning/STATE.md` |
| PreToolUse | Read/Grep/Glob | `crg-remind.sh` | "Graph available — prefer graph queries" |
| PreToolUse | Write/Edit | `gsd-prompt-guard.js`, `gsd-read-guard.js`, `gsd-workflow-guard.js` | GSD guards (read before edit, stay in phase) |
| PreToolUse | Bash | `gsd-validate-commit.sh` | Conventional commit format |
| PreToolUse | figma-console FigJam tools | `figjam-skill-remind.sh` | Injects "use the /figjam-board kit" |
| PostToolUse | Bash | `transcript-meeting-report.sh` | After a ChatGPT transcription, ask whether to build a meeting report |
| PostToolUse | Edit/Write/Bash | `code-review-graph update --skip-flows` | Incremental graph update |
| PostToolUse | Read | `gsd-read-injection-scanner.js` | Flags prompt-injection text in files read |
| PostToolUse | Bash/Edit/Write/Agent | `gsd-context-monitor.js` | Warns as the context window fills |
| PostToolUse / Stop / PreCompact | — | `sync.py` | Token/cost stats pushed to a team dashboard (internal, not included) |
| statusLine | — | `gsd-statusline.js` | Model, context %, current phase |

Custom ones are in [`hooks/`](../hooks); GSD's come with GSD; ECC's with its plugin.

## Lessons about hooks

- **Measure latency.** An unmatched (`""`) PostToolUse hook fires on *every* tool call. Keep those tiny, or give them a matcher.
- **Timeouts are in seconds**, not milliseconds — `"timeout": 5000` means 83 minutes.
- A hook can **inject context** by printing `{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"…"}}` — the cleanest way to make Claude use the right skill at the right moment.
- "From now on, whenever X…" requests need a hook, not a memory — memory can't make the harness do anything.
- The user kept permission prompts on (declined auto mode as default) — don't re-propose it.

## Scheduled / background

- `backup_memory.sh` via cron at 03:00 — snapshots memory + Redis + Qdrant, verifies, keeps 7.
- `/loop` and `/schedule` for recurring checks inside Claude Code; `CronCreate` for routines.
