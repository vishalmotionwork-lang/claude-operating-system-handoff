# 01 — The memory system

Claude Code starts every session blank. This setup makes plain markdown files the long-term memory and forces Claude to read the right ones before it does anything.

## The tiers

```
Tier 0    MEMORY.md + REGISTRY.md     always loaded   index of everything + project list
Tier 0.5  context/hot.md (Redis)      instant         user profile + active project + recent decisions
Tier 1    projects/<name>/CONTEXT.md  on project pick stack, paths, URLs, commands
Tier 2    projects/<name>/SESSION.md  right after     last state, next steps, blockers
          .planning/STATE.md          if GSD active   execution truth (code projects)
Tier 3    DECISIONS.md, PLANS/, RESEARCH/  only when the task needs them
```

Loading little up front and the rest on demand keeps the context window for actual work.

## Where it lives

Claude Code's auto-memory folder is per working directory:

```
~/.claude/projects/<cwd-with-slashes-as-dashes>/memory/
├── MEMORY.md                ← the index (auto-loaded every session)
├── USER.md                  ← who the user is, stack, hard rules (priority 0)
├── feedback_<topic>.md      ← one lesson per file (158 of these)
├── reference_<topic>.md     ← how-to / gotcha / pointer files (143)
├── project_<topic>.md       ← small one-off project facts (20)
├── sources/                 ← loaded research sources + INDEX.md
│   ├── INDEX.md
│   └── yt-<id>.md · pdf-<slug>.md · ig-<id>.md · src-<slug>.md
└── projects/
    ├── REGISTRY.md          ← table of every project, sorted by last-touched
    └── <project-name>/
        ├── CONTEXT.md       ← stack, paths, URLs, commands, "say X to resume"
        ├── SESSION.md       ← what happened last, current state, next steps
        └── DECISIONS.md     ← why things are the way they are (optional)
```

Templates for every file are in [`templates/memory/`](../templates/memory).

## One memory = one file, with frontmatter

```markdown
---
name: feedback_never_glob_rm_cleanup
description: Never rm with a wildcard to "clean up" — delete only an explicit list of paths you just created
metadata:
  type: feedback
---

<the rule>

**Why:** <what went wrong, the incident>
**How to apply:** <the concrete behaviour next time>. Related: [[feedback_other_rule]].
```

- `description` is what Claude reads to decide whether the file is relevant — make it a full rule, not a title.
- `[[name]]` links connect related memories. A link to a file that doesn't exist yet is fine; it marks something worth writing.
- Four types: **user** (who), **feedback** (how to work — corrections *and* things that went well), **project** (ongoing work not derivable from code), **reference** (resources, recipes, gotchas).

## The index: `MEMORY.md`

One line per memory, grouped by theme, bold for the important ones:

```markdown
- [**Never glob rm**](feedback_never_glob_rm_cleanup.md) — delete only an explicit list of paths you created
```

**Keep it under ~24 KB.** Claude Code truncates the index past its limit — the live one hit 37 KB and lost its last 62 lines. Detail belongs in the topic file; the index line is a hook, ≤ ~200 chars. Group lesser entries inline with `·` separators.

## Projects: `REGISTRY.md` + one folder each

`REGISTRY.md` is a table: Project · Type · Path · One-liner · Last Touched. The one-liner ends with a trigger phrase — *Say **"sprint planner"*** — so saying that phrase loads the project.

Rules learned the hard way:
- **Never put project detail in `MEMORY.md`** — each project owns its folder.
- **Never store the project's real files in memory.** Memory holds pointers (CONTEXT/SESSION/DECISIONS); code and docs live in the project folder.
- Every plan and process is saved so any session can resume it.

## The startup protocol (`CLAUDE.md`)

The home `CLAUDE.md` ([template](../templates/CLAUDE.md)) makes these reads **blocking** before the first reply:

1. `~/.claude/context/hot.md` — hot memory
2. `MEMORY.md` — the index
3. every `feedback_*.md` listed in it
4. `projects/REGISTRY.md`

Then: ask which project (top 5 by date) unless the user already named one → load its `CONTEXT.md` → `SESSION.md` → confirm *"Last time we … Continue, or different task?"*. When a task resembles past work, check other projects' `CONTEXT.md` before starting from scratch.

## The self-learning rule

After **any** correction, pushback or stated preference:
1. Write `feedback_<topic>.md` immediately (what went wrong, the rule, why).
2. Add its line to `MEMORY.md`.
3. Tell the user: *"Saved as rule: …"*.

Also save what *worked* when the user confirms an unusual choice — otherwise Claude drifts away from approaches that were already validated. This is the single most valuable habit in the setup: [06-lessons-learned.md](06-lessons-learned.md) is the distilled result.

## Session end protocol

When wrapping up: update the project's `SESSION.md` (done / state / next / blockers), bump its date in `REGISTRY.md`, confirm *"Session saved. Next time I'll pick up from …"*. If GSD runs the project, `SESSION.md` only holds the human side (blockers on people, stakeholder decisions, the why) — execution state is in `.planning/STATE.md`.

## Hot memory (optional layer)

[`scripts/hot_memory.py`](../scripts/hot_memory.py) keeps a Redis cache of the user profile, active project and recent decisions, rendered into `~/.claude/context/hot.md` within a ~4,000-token budget. TTLs: session 4 h · project 7 d · decisions 30 d · feedback 90 d · user 180 d.

```bash
python3 ~/.claude/scripts/hot_memory.py load --project <name>
python3 ~/.claude/scripts/hot_memory.py store --key "auth-decision" --value "Using Supabase Auth"
python3 ~/.claude/scripts/hot_memory.py get
```

Qdrant semantic search ([`index_memory_to_qdrant.py`](../scripts/index_memory_to_qdrant.py)) was built too but **deprecated** — it was rarely used; direct file reads plus a good index won. Keep Redis only if you want the speed; the file tiers work without it.

Maintenance: [`memory_doctor.py`](../scripts/memory_doctor.py) (health checks — broken links, missing frontmatter, oversized index) and [`backup_memory.sh`](../scripts/backup_memory.sh) (daily cron, 7 rotating snapshots, verifies before rotating).

## Credentials

The live setup kept a few API keys in memory files. **Don't.** Use environment variables or the macOS Keychain (`security add-generic-password` / `find-generic-password`), and never commit memory to a public repo.
