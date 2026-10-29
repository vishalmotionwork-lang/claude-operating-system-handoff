# Project Rules

## Startup Protocol

⚠️ **CRITICAL: Steps 1-4 are BLOCKING. Do NOT respond to the user until ALL are complete.**
⚠️ **The session-start hook outputs reminders. If you see [hot] messages, you MUST follow them.**

**BEFORE your first response to the user — no exceptions:**

1. **Read `~/.claude/context/hot.md`** — Redis hot memory. Contains user profile, feedback rules, active project context, and key decisions. This is your brain loading. DO IT FIRST.

2. **Read `~/.claude/projects/-Users-YOUR-USER/memory/MEMORY.md`** — Memory index. Note all feedback files listed.

3. **Read ALL feedback memory files** listed in MEMORY.md (every `feedback_*.md`). These are corrections from past sessions. Apply them BEFORE doing any work. If you skip this, you WILL repeat mistakes the user already corrected.

4. **Read `~/.claude/projects/-Users-YOUR-USER/memory/projects/REGISTRY.md`** — Project list. Identify which project the user is working on.

**AFTER the mandatory reads — respond to the user:**

5. Ask: "Which project are you working on?" — show top 5 by last-touched date
6. If user already named a project in their message, skip the question — load it directly
7. Load that project's `CONTEXT.md` (Tier 1)
8. Load `SESSION.md` (Tier 2) if hot.md is stale/missing
9. Confirm: "Last time we [summary]. Continue, or different task?"
10. **Cross-project lookup**: when the task resembles past work, check other projects' `CONTEXT.md`/`SESSION.md` in `memory/projects/` and reference their implementations instead of starting from scratch. Skip for trivial tasks (typos, config changes).
11. Load `DECISIONS.md` and `PLANS/` or `RESEARCH/` only when the task requires it (Tier 3)

**DURING the session:**

12. **Store key decisions to Redis** (optional, only for critical decisions): `python3 ~/.claude/scripts/hot_memory.py store --key "<topic>" --value "<state>"`

If user says something new (not in REGISTRY), create a new project folder immediately:
```
memory/projects/<project-name>/
├── CONTEXT.md
├── SESSION.md
└── DECISIONS.md (if needed)
```
And add it to REGISTRY.md.

## Self-Learning Rule

After ANY correction, pushback, or preference expressed by the user:
1. Immediately save it as a feedback memory in `~/.claude/projects/-Users-YOUR-USER/memory/feedback_<topic>.md`
2. Use frontmatter: name, description, type: feedback
3. Include: what went wrong, the rule for next time, and why
4. Confirm to user: "Saved as rule: [one-liner]"

## GSD + Memory Integration

When a project has `.planning/` (GSD is active):
- **STATE.md ownership**: `.planning/STATE.md` is the source of truth for execution state
- **SESSION.md role**: Only tracks human-side context that GSD doesn't know:
  - Blockers waiting on people/approvals
  - Stakeholder decisions
  - "Why" context behind choices
  - Link to GSD state: "GSD active — see .planning/STATE.md for execution progress"
- **No duplication**: Don't repeat phase progress, task lists, or "what's next" in SESSION.md — that's in GSD
- **CONTEXT.md feeds GSD**: When spawning GSD agents, point them to CONTEXT.md for stack/URLs/commands so they skip discovery

When a project has NO `.planning/`:
- SESSION.md is the full source of truth (current behavior)

> Spawning agents for large tasks (multi-file refactors, long research)? See the `agent-handoff` skill.

## Session End Protocol

When a session is ending (user says goodbye, wrapping up, or context is getting long):
1. If GSD active: no need to duplicate state — just update SESSION.md with human-side context only
2. If no GSD: update SESSION.md with full state (what was done, current state, next steps, blockers)
3. Update `REGISTRY.md` last-touched date for that project
4. Confirm: "Session saved. Next time I'll pick up from [summary]."

## Project Memory Structure

```
Tier 0: REGISTRY.md              — always loaded (project list, dates)
Tier 0.5: hot.md (Redis)         — instant (<100ms), project context + feedback + session facts
Tier 1: CONTEXT.md               — loaded when project selected (stack, URLs, commands)
Tier 2: SESSION.md               — loaded right after (last state, next steps)
         .planning/STATE.md      — if GSD active, this is execution truth (not SESSION.md)
Tier 3: DECISIONS.md             — loaded only when task needs architecture/choices
         PLANS/                  — loaded only when planning new phases
         RESEARCH/               — loaded only when researching
```

Never put project-specific context in the main MEMORY.md. Each project owns its own folder.
