# Claude Operating System — Handoff

How one small content + product team runs almost all of its work through **Claude Code**: the memory system that makes every session resumable, the research structure, the repeatable workflows, and the tools, skills, MCP servers and hooks behind them. Everything here is meant to be installed onto a new machine.

> Snapshot taken 29 Oct 2026 from a live setup: **7,874 prompts**, **201 session transcripts**, **378 memory files** (158 feedback rules, 143 references, 136 project folders), **191 skills**, **61 agents**, 6 plugins, ~12 MCP servers.

## What's inside

| Path | What it is |
|---|---|
| [`docs/01-memory-system.md`](docs/01-memory-system.md) | The tiered memory architecture — files, frontmatter, index, project folders, hot memory, the self-learning rule |
| [`docs/02-research-system.md`](docs/02-research-system.md) | How research is done and stored — source order, sources index, teardown pipelines, transcription |
| [`docs/03-workflows.md`](docs/03-workflows.md) | The workflows used every week, step by step |
| [`docs/04-tools-skills-mcps.md`](docs/04-tools-skills-mcps.md) | Every tool, skill, plugin, MCP server and CLI — ranked by real usage |
| [`docs/05-hooks-automation.md`](docs/05-hooks-automation.md) | Hooks, status line, scheduled jobs |
| [`docs/06-lessons-learned.md`](docs/06-lessons-learned.md) | The most useful of 158 feedback rules, made generic |
| [`docs/07-install.md`](docs/07-install.md) | Step-by-step install on a fresh Mac |
| [`templates/`](templates) | `CLAUDE.md`, global rules, memory skeleton, `settings.json` |
| [`skills/`](skills) | Seven home-built skills, sanitized and ready to drop in |
| [`scripts/`](scripts) | Memory (Redis/Qdrant), transcription, backup and doctor scripts |
| [`hooks/`](hooks) | The custom hook scripts |
| [`commands/`](commands) | Custom slash commands |
| [`install.sh`](install.sh) | Copies templates, skills, hooks and scripts into `~/.claude` without overwriting |

## Quick start

```bash
git clone https://github.com/vishalmotionwork-lang/claude-operating-system-handoff.git
cd claude-operating-system-handoff
./install.sh            # dry run: shows what it would copy
./install.sh --apply    # copies, never overwrites existing files
```

Then follow [`docs/07-install.md`](docs/07-install.md) for plugins, MCP servers and CLIs.

## The idea in one paragraph

Claude forgets everything between sessions. So the system makes **files the memory**: one index (`MEMORY.md`) that's always loaded, one folder per project (`CONTEXT.md` → `SESSION.md` → `DECISIONS.md`) loaded only when that project is picked, and one small file per **lesson** (`feedback_*.md`) written the moment the user corrects Claude. A `CLAUDE.md` startup protocol forces Claude to read those before answering. Skills package the repeatable jobs (transcribe a meeting → visual report; tear down a creator; plan a sprint), and hooks nudge Claude toward the right skill at the right moment.

## What is deliberately NOT in this repo

This repo is public. The live memory holds client names, team details, internal URLs, salaries and a few credential files, so none of the raw memory is published — only its **structure**, **templates** and **generic lessons**. Also left out: internal-only skills (sprint planner, Sprint OS, scripting OS — described in the docs), commands that hard-code a database connection, and third-party skills/plugins (installed from their own sources instead, see the install guide).

## License

MIT for the original material here. Third-party tools keep their own licenses.
