"""
Shared model configuration for the memory system.

Two embedding models:
  - fast (MiniLM): 384d, 80MB, <1s load — session start, quick lookups
  - deep (BGE-large): 1024d, 1.3GB, ~5s load — research, architecture, cross-project
"""

import os
import subprocess
import time
from pathlib import Path

QDRANT_PATH = Path.home() / ".qdrant-memory"


def clear_stale_qdrant_lock() -> bool:
    """Remove Qdrant .lock file if no process holds it.

    Called before every Qdrant access to prevent the embedded client
    from failing with 'already accessed' errors after a crash.

    The ONLY check is whether a live process holds the lock (via lsof).
    No age threshold — if nobody holds it, it's stale. Period.
    Qdrant embedded mode creates the lock on open and should release on close.
    If the process died, the lock is orphaned regardless of age.

    Returns:
        True if a stale lock was removed, False otherwise.
    """
    lock_file = QDRANT_PATH / ".lock"
    if not lock_file.exists():
        return False

    # Check if any process actually holds the lock
    try:
        result = subprocess.run(
            ["lsof", str(lock_file)],
            capture_output=True, text=True, timeout=5,
        )
        # If lsof finds a holder (exit code 0 with output beyond header),
        # the lock is active — don't touch it
        lines = result.stdout.strip().split("\n")
        if result.returncode == 0 and len(lines) > 1:
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # No holder = orphaned lock. Remove it.
    try:
        lock_file.unlink()
        return True
    except FileNotFoundError:
        return False  # Race: already gone
MEMORY_BASE = Path.home() / ".claude" / "projects" / str(Path.home()).replace("/", "-").replace(".", "-") / "memory"
CONTEXT_DIR = Path.home() / ".claude" / "context"

MODELS = {
    "fast": {
        "name": "sentence-transformers/all-MiniLM-L6-v2",
        "collection": "claude-memory-fast",
        "dimensions": 384,
        "description": "Fast model for session start and quick lookups",
    },
    "deep": {
        "name": "BAAI/bge-large-en-v1.5",
        "collection": "claude-memory-deep",
        "dimensions": 1024,
        "description": "High-quality model for research and architecture decisions",
    },
}

# Task-to-model routing
TASK_MODEL_MAP = {
    # Fast model tasks
    "hook": "fast",
    "session-start": "fast",
    "quick-lookup": "fast",
    "project-context": "fast",

    # Deep model tasks
    "research": "deep",
    "architecture": "deep",
    "cross-project": "deep",
    "deep-search": "deep",
    "decisions": "deep",
}


def get_model_for_task(task: str) -> str:
    """Return 'fast' or 'deep' based on the task type."""
    return TASK_MODEL_MAP.get(task, "fast")


def get_model_config(mode: str) -> dict:
    """Return model config dict for the given mode."""
    return MODELS.get(mode, MODELS["fast"])
