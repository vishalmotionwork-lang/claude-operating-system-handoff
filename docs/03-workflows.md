# 03 — Workflows

The jobs that run every week, in the order they're done.

## 1. Start / resume a session

```
open terminal in ~  →  claude
→ CLAUDE.md protocol reads hot.md, MEMORY.md, feedback rules, REGISTRY.md
→ say the project's trigger phrase ("sprint planner")  →  CONTEXT.md + SESSION.md load
→ "Last time we … Continue?"
```
`/clear` between unrelated tasks (the most-used command: 388 times). `/compact` only at a natural break. For code projects with GSD: `/gsd:resume-work`.

## 2. Meeting → visual report  (`/post-meeting-visual-report`)

1. Transcribe: `/chatgpt-transcript <file>` (a PostToolUse hook then asks whether to file a report).
2. Repair the transcript with the **lexicon** (`assets/lexicon.md`: known mis-hearings of names and terms — append every new one).
3. Attribute speakers from vocatives, roll-calls and role asymmetry — never guess a name the call didn't say.
4. Check numbers against the canonical-numbers file and prior work in `memory/projects/`.
5. Build the HTML report from `assets/report-template.html` with numbered figures.
6. File at `meetings/YYYY-MM/<department>/YYYY-MM-DD-<topic>--<people>.html`, render-check, open it.

## 3. Voice note → sprint / tasks  (internal `sprint-planner` skill)

Voice note → `/chatgpt-transcript` → Claude maps each item to **existing** pieces first (link, don't duplicate) → writes projects, task groups and per-piece tasks into the team's planning tools through their CLIs (always `--dry-run` preview first, never delete) → publishes the weekly sprint page → posts in Slack. Friday: pull hours and stages back, close the sprint. Every artifact gets a timestamped copy in `sprint-planning/<team>/<Monday>_sprint/`.

The pattern generalises: **give every internal web app a CLI** (`cli-anything-<app>`) that can do everything the UI can, with dry-run + no deletes, and a skill that knows the workflow. Then Claude can run the whole loop from a voice note.

## 4. Research / teardown → interactive HTML board

1. Brief per angle → parallel `general-purpose` agents (narrow scope, disjoint files).
2. Pull data (yt-dlp, Firecrawl, agent-reach, Composio), transcribe, classify.
3. Build **one self-contained interactive HTML** (local assets, playable media, full-page detail views with breadcrumb/back/prev-next, reasoning shown on every label).
4. Verify in a headless browser (`/browse` / gstack) — screenshots are Claude's evidence; the user gets the HTML file opened in their browser.
5. YouTube embeds don't play from `file://` (Error 153) — ship a tiny localhost launcher.

## 5. Visual boards in FigJam / Figma

`/figjam-board` (place-and-verify engine `figjam-kit.js`) via the `figma-console` MCP, or `cli-anything-figma` / `figma-direct` MCP which drives Figma Desktop over its debug port with no plugin. A PreToolUse hook reminds Claude to use the kit instead of hand-rolled JS. Build in verified-empty space; screenshot after every build.

## 6. Building software  (GSD + ECC)

```
/gsd:new-project  →  /gsd:discuss-phase  →  /gsd:plan-phase  →  /gsd:execute-phase  →  /gsd:verify-work  →  /gsd:ship
```
- GSD (Get Shit Done) owns `.planning/` (ROADMAP, STATE, phase plans) and runs planner / executor / verifier agents.
- ECC (Everything Claude Code plugin) supplies reviewers (`code-reviewer`, `typescript-reviewer`, `security-reviewer`…), `/tdd`, `/verify`, `/code-review`.
- Rules: plan first, TDD with 80 % coverage, review right after writing, **boot the real app and click through it before calling it done**, local-first (Docker / local Supabase) before any hosting talk, deploy via Vercel CLI (not a GitHub connection).
- Large ports: split into named waves of 5–15 files per agent, foundation first.

## 7. Content: scripts and strategy

- Scripts are full word-for-word spoken voice of the on-camera person, never skeletons. Never invent clients, numbers or receipts — leave `[FILL]` markers.
- Reverse-engineering a viral piece = keep the **framework** (psychology, structure), apply it to a genuinely different topic.
- Platform strategy is built top-down: bandwidth → cadence (counts) → funnel → pillars → topics, each level summing to its parent.
- YouTube: ideas → framework check → wide research → packaging (title/thumbnail) alternatives → pick → *then* script.

## 8. Daily rhythm

`/bod` (beginning of day — log planned tasks to the team dashboard) and `/eod` (what got done, issues). These commands are internal (they write to the team database) and not included; write your own against your own store.

## 9. Delegating big work  (`agent-handoff` skill)

Give each agent a narrow, disjoint scope and an explicit file list; never brief a second agent on a file a running agent still owns; agents write a handoff file so the work survives context overflow. For 20–50-agent builds: waves of foundation → screens → audits → fixers.
