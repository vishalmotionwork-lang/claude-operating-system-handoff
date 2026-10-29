#!/usr/bin/env python3
"""
Prompt builder with optional sections for agent context injection.

Inspired by Mohini's PromptContext pattern: ~25 optional fields,
only includes non-empty sections. Keeps agent prompts lean.

Usage:
    # Build context for a specific agent task
    python3 ~/.claude/scripts/build_agent_context.py --project hireflow --task architecture

    # Build minimal context (just project + feedback)
    python3 ~/.claude/scripts/build_agent_context.py --project hireflow --minimal

    # Build full context (everything available)
    python3 ~/.claude/scripts/build_agent_context.py --project hireflow --full

    # Output as string (for embedding in agent prompts)
    python3 ~/.claude/scripts/build_agent_context.py --project hireflow --task coding --stdout

Output: ~/.claude/context/agent-context.md
"""

import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from models import MEMORY_BASE, CONTEXT_DIR

AGENT_CONTEXT_FILE = CONTEXT_DIR / "agent-context.md"

# Task-to-sections mapping: which sections each task type needs
TASK_SECTIONS = {
    "coding": ["project_context", "decisions", "feedback", "stack"],
    "architecture": ["project_context", "decisions", "feedback", "deep_search", "cross_project"],
    "research": ["project_context", "deep_search", "cross_project"],
    "debugging": ["project_context", "decisions", "session", "stack"],
    "planning": ["project_context", "decisions", "feedback", "deep_search", "session"],
    "review": ["project_context", "decisions", "feedback", "stack"],
    "minimal": ["project_context", "feedback"],
    "full": ["project_context", "decisions", "feedback", "session", "deep_search", "cross_project", "stack"],
}


def load_section(section: str, project: str) -> tuple[str, str]:
    """Load a single context section. Returns (title, content) or ("", "") if empty."""
    project_dir = MEMORY_BASE / "projects" / project

    if section == "project_context":
        path = project_dir / "CONTEXT.md"
        if path.exists():
            content = path.read_text(encoding="utf-8").strip()
            if content:
                return "Project Context", content
    elif section == "decisions":
        path = project_dir / "DECISIONS.md"
        if path.exists():
            content = path.read_text(encoding="utf-8").strip()
            if content:
                return "Key Decisions", content
    elif section == "session":
        path = project_dir / "SESSION.md"
        if path.exists():
            content = path.read_text(encoding="utf-8").strip()
            if content:
                return "Last Session State", content
    elif section == "feedback":
        chunks = []
        for f in sorted(MEMORY_BASE.glob("feedback_*.md")):
            text = f.read_text(encoding="utf-8").strip()
            if text:
                # Extract body only (skip frontmatter)
                if "---" in text:
                    parts = text.split("---", 2)
                    if len(parts) >= 3:
                        text = parts[2].strip()
                chunks.append(f"- {text[:150]}")
        if chunks:
            return "Feedback Rules", "\n".join(chunks)
    elif section == "deep_search":
        path = CONTEXT_DIR / "deep-search.md"
        if path.exists():
            content = path.read_text(encoding="utf-8").strip()
            if content:
                return "Deep Vector Context (BGE-large)", content[:3000]
    elif section == "cross_project":
        path = CONTEXT_DIR / "prefetched-deep.md"
        if not path.exists():
            path = CONTEXT_DIR / "prefetched.md"
        if path.exists():
            content = path.read_text(encoding="utf-8").strip()
            if content:
                return "Cross-Project Context (Vector Search)", content[:2000]
    elif section == "stack":
        path = project_dir / "CONTEXT.md"
        if path.exists():
            content = path.read_text(encoding="utf-8")
            # Extract just the stack/commands/URLs section
            lines = []
            in_section = False
            for line in content.split("\n"):
                if line.startswith("## ") and any(k in line.lower() for k in ["command", "url", "stack", "what"]):
                    in_section = True
                elif line.startswith("## "):
                    in_section = False
                if in_section:
                    lines.append(line)
            if lines:
                return "Stack & Commands", "\n".join(lines)

    return "", ""


def build_context(project: str, task: str = "coding") -> str:
    """Build agent context with only the sections needed for this task."""
    sections_needed = TASK_SECTIONS.get(task, TASK_SECTIONS["coding"])

    lines = [
        f"<!-- Agent Context | Project: {project} | Task: {task} | {datetime.now().isoformat()} -->",
        "",
    ]

    loaded = 0
    for section in sections_needed:
        title, content = load_section(section, project)
        if title and content:
            lines.append(f"## {title}")
            lines.append("")
            lines.append(content)
            lines.append("")
            loaded += 1

    if loaded == 0:
        lines.append(f"No context found for project '{project}'. Check memory/projects/{project}/")

    return "\n".join(lines)


def main():
    project = ""
    task = "coding"
    stdout = "--stdout" in sys.argv

    if "--project" in sys.argv:
        idx = sys.argv.index("--project")
        project = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""

    if "--task" in sys.argv:
        idx = sys.argv.index("--task")
        task = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "coding"

    if "--minimal" in sys.argv:
        task = "minimal"
    elif "--full" in sys.argv:
        task = "full"

    if not project:
        # Try to detect from cwd
        from hot_memory import detect_project
        project = detect_project()

    if not project:
        print("[error] No project specified. Use --project <name>", file=sys.stderr)
        sys.exit(1)

    context = build_context(project, task)

    if stdout:
        print(context)
    else:
        CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
        AGENT_CONTEXT_FILE.write_text(context, encoding="utf-8")
        section_count = context.count("## ")
        print(f"[build] {section_count} sections for '{project}' ({task}) → {AGENT_CONTEXT_FILE}")


if __name__ == "__main__":
    main()
