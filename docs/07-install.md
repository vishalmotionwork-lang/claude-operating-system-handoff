# 07 — Install on a new machine

Order matters: base tools → Claude Code → this repo → plugins → skills packs → MCP servers → personalise memory.

## 1. Base tools (macOS)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install node python git gh jq yt-dlp ffmpeg redis uv supabase/tap/supabase
brew install --cask docker
curl -fsSL https://bun.sh/install | bash
npm i -g vercel
pip3 install --break-system-packages anthropic redis code-review-graph requests
gh auth login
```

## 2. Claude Code

```bash
npm i -g @anthropic-ai/claude-code
claude   # sign in
```

## 3. This repo

```bash
git clone https://github.com/vishalmotionwork-lang/claude-operating-system-handoff.git
cd claude-operating-system-handoff
./install.sh           # dry run
./install.sh --apply   # copies into ~/.claude and ~, never overwrites
```

It installs:
- `~/CLAUDE.md` (startup protocol) and `~/.claude/rules/common/*.md`
- the memory skeleton into `~/.claude/projects/<home-slug>/memory/`
- the seven skills into `~/.claude/skills/`, hooks into `~/.claude/hooks/`, scripts into `~/.claude/scripts/`, commands into `~/.claude/commands/`
- `templates/settings.json` → `~/.claude/settings.json` **only if you have none** (otherwise merge by hand)

Start Claude from your home folder (`cd ~ && claude`) so the home `CLAUDE.md` and memory folder apply.

## 4. Plugins

Inside Claude Code:
```
/plugin marketplace add affaan-m/everything-claude-code
/plugin install everything-claude-code@everything-claude-code
/plugin marketplace add HKUDS/CLI-Anything
/plugin install cli-anything@cli-anything
/plugin marketplace add https://github.com/ComposioHQ/composio-plugin-cc.git
/plugin install composio@composio
```

## 5. Skill packs

```bash
# GSD — Get Shit Done (phase-based building)
npx get-shit-done-cc@latest

# gstack — fast headless browser + QA/ship skills
git clone https://github.com/garrytan/gstack.git ~/.claude/skills/gstack && cd ~/.claude/skills/gstack && ./setup
```
Firecrawl, agent-reach and Composio CLIs: follow each project's README (each needs an account / API key). Check every install command against the project's current README — they change.

## 6. MCP servers

See [`templates/mcp-servers.md`](../templates/mcp-servers.md). Connect Slack, Google Drive, Gmail, Calendar in claude.ai → Connectors.

## 7. Secrets (env vars, never memory files)

```bash
# ~/.zshrc
export GROQ_API_KEY=...        # /transcript, synced-captions, video-style-decoder
export FIRECRAWL_API_KEY=...
```
Or Keychain: `security add-generic-password -a "$USER" -s groq -w <key>`.

## 8. Optional: hot memory

```bash
brew services start redis
python3 ~/.claude/scripts/hot_memory.py hook   # renders ~/.claude/context/hot.md
# daily backup
(crontab -l; echo "0 3 * * * bash ~/.claude/scripts/backup_memory.sh") | crontab -
```

## 9. Personalise (the part that makes it yours)

1. Fill `memory/USER.md`.
2. Add your projects to `projects/REGISTRY.md`, one folder each.
3. Copy the rules you agree with from [06-lessons-learned.md](06-lessons-learned.md) into `feedback_*.md` files.
4. Fill `skills/post-meeting-visual-report/assets/lexicon.md` with your team's names and terms.
5. Work normally — every correction becomes a new feedback file. After a month the memory is the most valuable part of the setup.

## Verify

```bash
claude
> /mcp            # servers connected
> /plugin         # plugins enabled
> what do you remember about me?   # should quote USER.md
```
