---
name: agent-handoff
description: Handoff protocol for spawning agents on large tasks (multi-file refactors, full phase execution, long research) so work survives context overflow. Use when delegating work that may exhaust an agent's context, or when a returning agent may have left a handoff file.
---

# Agent Handoff Protocol

When spawning agents for large tasks (multi-file refactors, full phase execution, long research):

- Include in the agent prompt: "If you are running low on context, BEFORE finishing: write a handoff file to `~/.claude/context/handoff-<task>.md` with: what's done, what's left, current state, and any decisions made."
- After an agent returns, check whether a handoff file exists. If so, spawn a continuation agent with that file as context.
- This prevents work loss on context overflow — agents hand off instead of dying silently.

When context is getting heavy in the main session:

- Save critical state to Redis: `python3 ~/.claude/scripts/hot_memory.py store --key "<topic>" --value "<state>"`
- This survives compaction and session restarts.
