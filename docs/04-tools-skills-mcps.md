# 04 — Tools, skills, plugins, MCP servers, CLIs

Numbers below are counted from the live machine's 201 session transcripts and 7,874-prompt history (29 Oct 2026). Transcripts get pruned, so treat them as relative, not absolute.

## Built-in tools by use

| Tool | Calls | Used for |
|---|---:|---|
| Bash | 3,347 | Python scripts, CLIs (`composio`, `cli-anything-*`, `yt-dlp`, `ffmpeg`), headless browser, zips |
| Read | 2,116 | Memory, code, images/screenshots for visual checks |
| Write | 324 | HTML boards, memory files, scripts |
| Agent | 119 | Parallel research / build agents (almost all `general-purpose`) |
| Edit | 100 | Targeted changes |
| ToolSearch | 63 | Loading deferred MCP tools |
| AskUserQuestion | 57 | Every question to the user goes through this (a saved rule) |
| SendMessage | 22 | Continuing a running agent |
| WebSearch / WebFetch | 22 | Light lookups (Firecrawl for heavy ones) |

## Slash commands by use (typed by the user)

| Command | Uses | |
|---|---:|---|
| `/clear` | 388 | Fresh context between tasks |
| `/chatgpt-transcript` | 31 | Hinglish-quality transcription |
| `/gsd:resume-work` | 25 | Resume a coded project |
| `/model` | 20 | Switch model |
| `/mcp` | 14 | Check / auth MCP servers |
| `/gsd:new-project` · `/gsd:plan-phase` | 11 · 10 | Start / plan code projects |
| `/compact` | 9 | |
| `/visualise` | 8 | Doc/transcript → systemised visual HTML |
| `/figma` | 7 | HTML → Figma |
| `/post-meeting-visual-report` · `/transcript` · `/creator-reverse-engineer` | 3 · 3 · 2 | |

## Skills — the ones that matter

**Home-built (included in [`skills/`](../skills), sanitized):**

| Skill | What it does |
|---|---|
| `post-meeting-visual-report` | Recording → transcript → repaired, attributed → visual HTML report filed by month/department |
| `visualise` | Any doc/transcript → systemised visual HTML + context doc |
| `figjam-board` | Reliable FigJam boards via a place-and-verify JS kit |
| `video-style-decoder` | Edited video → repeatable style system (rules, move library, timing, worksheet) |
| `video-inspo-extracter` | Video → classified b-roll clips on a FigJam grid, or a creator teardown board |
| `synced-captions` | Word-synced, phrase-aware SRT captions |
| `agent-handoff` | Protocol so big delegated work survives context overflow |

**Home-built, internal (not included — describe and rebuild for your own tools):**
`sprint-planner` (voice note → team planning tools via CLIs), `sprint-os`, `zeel-scripting-os` (companion skills for static HTML apps: the app produces a prompt, Claude replies with one JSON patch), `reel-insights` (reel + Insights → per-reel docs + master doc), `creator-reverse-engineer` (public separately as an MIT repo).

**Third-party, install from source:**

| Skill pack | Source | Why |
|---|---|---|
| GSD — Get Shit Done (~60 `gsd-*` skills + agents) | `npx get-shit-done-cc` | Phase-based project planning/execution for code |
| gstack (`browse`, `qa`, `ship`, `review`, `investigate`, `office-hours`…) | github.com/garrytan/gstack | ~100 ms headless browser for verifying every HTML/app before handoff |
| Firecrawl (`firecrawl-*`) | `npx skills add firecrawl/cli` | Search, scrape, crawl, map, cloud browser |
| agent-reach | its GitHub repo | Read X, Reddit, YouTube, LinkedIn, IG, Bilibili, RSS… |
| composio-cli | Composio plugin | 1,000+ app actions (Gmail, Slack, Drive, Notion…) from Bash |
| Anthropic skills (`docx`, `pdf`, `pptx`, `xlsx`, `skill-creator`, `dataviz`, `artifact-*`) | built in / claude.ai | Office files, charts |

## Plugins (`/plugin`)

| Plugin | Marketplace | Status |
|---|---|---|
| everything-claude-code | `affaan-m/everything-claude-code` | on — agents (planner, architect, code/security/language reviewers, tdd-guide), rules, commands |
| composio | `ComposioHQ/composio-plugin-cc` | on |
| cli-anything | `HKUDS/CLI-Anything` | on — wrap any app as a CLI |
| frontend-design, telegram, clangd-lsp | `anthropics/claude-plugins-official` | installed, off |

## MCP servers

| Server | Calls | Purpose |
|---|---:|---|
| Slack (via plugin) | 128 | Search users/channels, read EODs, post sprint pages, upload files |
| Google Drive (claude.ai connector) | 39 | Create/share briefs and docs |
| figma-direct (`cli-anything-figma`) | 15 | Drive Figma Desktop over its debug port — no plugin needed |
| figma-console | 9 | FigJam/Figma building via the Desktop Bridge plugin |
| Gmail, Google Calendar, Claude Docs (claude.ai connectors) | — | Mail, scheduling, living docs |
| computer-use | 5 | Native Mac apps when nothing else works |
| knowlens-mcp | — | Internal people/task/capacity data (company-specific) |
| Neon | — | Postgres (read only — verify writes through the app's own API) |
| Miro / rube (Composio) | — | Older board work, now mostly FigJam |
| pencil | — | `.pen` design files |
| code-review-graph | — | Code graph for large repos (hooks keep it updated; MCP itself now disabled) |

Example config in [`templates/mcp-servers.md`](../templates/mcp-servers.md).

## CLIs and system dependencies

| Install | Used for |
|---|---|
| `brew install yt-dlp ffmpeg jq gh redis uv` | Media download / cutting, JSON, GitHub, hot memory, Python envs |
| `npm i -g vercel @anthropic-ai/sdk` | Deploys (CLI, not Git integration) |
| `bun` | gstack browser |
| `pip install code-review-graph anthropic` | Code graph, SDK |
| `firecrawl` CLI | Web data |
| `composio` CLI | App actions; `composio search "<task>"` → `composio execute` |
| `supabase` CLI + Docker | Local-first backend dev |
| `cli-anything-<app>` | One CLI per internal web app (Ledger, ERP, Outline, Figma…) — dry-run first, no deletes |
| Groq API key (`GROQ_API_KEY`) | Fast Whisper transcription |
| macOS Vision OCR (small Swift tool) | Frame OCR in teardown light reads |

## Agents (subagent types)

`general-purpose` does ~90 % of delegated work. ECC adds specialists: `planner`, `architect`, `code-reviewer`, `security-reviewer`, `tdd-guide`, language reviewers and build resolvers. GSD adds ~30 `gsd-*` agents for its phases. `Explore` for wide read-only searches.
