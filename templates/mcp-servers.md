# MCP servers — how to add them

Add with `claude mcp add` (user scope = every project) or connect in claude.ai → Settings → Connectors (those appear in Claude Code automatically when you're signed in).

```bash
# Figma / FigJam via the Desktop Bridge plugin
claude mcp add --scope user figma-console -- npx -y figma-console-mcp@latest

# Figma Desktop over its debug port, no plugin (ships with cli-anything-figma)
claude mcp add --scope user figma-direct -- cli-anything-figma mcp

# Neon Postgres (read-mostly)
claude mcp add --scope user --transport http Neon https://mcp.neon.tech/mcp

# Composio (1,000+ apps) — or just use the composio CLI from Bash
#   install the plugin from the composio marketplace, then: composio login
```

claude.ai connectors used: **Slack**, **Google Drive**, **Gmail**, **Google Calendar**, **Claude Docs**.
Built in: **computer-use** (native Mac apps — enable in Claude Code settings).

Check with `/mcp`. Exact package names change; confirm on each project's README before installing.
