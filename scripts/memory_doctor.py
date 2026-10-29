#!/usr/bin/env python3
"""
Memory Doctor — self-healing, dedup, pruning, and recovery for the memory system.

Commands:
    python3 memory_doctor.py health          # Full health report (services, index, files)
    python3 memory_doctor.py dedup-check     # Find duplicate/similar memory files
    python3 memory_doctor.py dedup-fix       # Interactively merge duplicates
    python3 memory_doctor.py prune           # Archive dormant projects (>90 days)
    python3 memory_doctor.py restore <date>  # Restore from backup (YYYY-MM-DD)
    python3 memory_doctor.py repair          # Auto-fix common issues
"""

import sys
import os
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from models import QDRANT_PATH, MEMORY_BASE, CONTEXT_DIR

BACKUP_DIR = Path.home() / ".claude" / "backups"
REGISTRY_FILE = MEMORY_BASE / "projects" / "REGISTRY.md"


# ─── HEALTH CHECK ───────────────────────────────────────

def check_health():
    """Full health report across all memory tiers."""
    issues = []
    warnings = []
    ok = []

    # 1. Redis
    try:
        result = subprocess.run(["redis-cli", "ping"], capture_output=True, text=True, timeout=5)
        if result.stdout.strip() == "PONG":
            key_result = subprocess.run(
                ["redis-cli", "keys", "claude:*"], capture_output=True, text=True, timeout=5
            )
            key_count = len([k for k in key_result.stdout.strip().split("\n") if k])
            ok.append(f"Redis: alive ({key_count} active keys)")
        else:
            issues.append("Redis: not responding to PING")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        issues.append("Redis: not available (brew services start redis)")

    # 2. Qdrant index
    if QDRANT_PATH.exists():
        meta = QDRANT_PATH / "meta.json"
        lock = QDRANT_PATH / ".lock"
        if meta.exists():
            age_sec = int(datetime.now().timestamp() - meta.stat().st_mtime)
            age_h = age_sec // 3600
            if age_h > 48:
                warnings.append(f"Qdrant index: {age_h}h old (re-index recommended)")
            else:
                ok.append(f"Qdrant index: {age_h}h old")
        else:
            issues.append("Qdrant: meta.json missing (needs re-index)")

        if lock.exists():
            lock_age = int(datetime.now().timestamp() - lock.stat().st_mtime)
            holder = _get_lock_holder(lock)
            if holder:
                ok.append(f"Qdrant lock: held by PID {holder} (active session)")
            elif lock_age > 300:
                warnings.append(f"Qdrant lock: stale ({lock_age}s old, no holder)")
            else:
                ok.append(f"Qdrant lock: recent ({lock_age}s old)")
    else:
        issues.append("Qdrant: storage directory not found")

    # 3. Memory files
    md_files = list(MEMORY_BASE.rglob("*.md"))
    feedback_files = [f for f in MEMORY_BASE.glob("feedback_*.md")]
    project_dirs = [d for d in (MEMORY_BASE / "projects").iterdir() if d.is_dir()] if (MEMORY_BASE / "projects").exists() else []
    ok.append(f"Memory files: {len(md_files)} total, {len(feedback_files)} feedback, {len(project_dirs)} projects")

    # 4. Context files
    hot_file = CONTEXT_DIR / "hot.md"
    prefetch_file = CONTEXT_DIR / "prefetched.md"
    if hot_file.exists():
        age = int(datetime.now().timestamp() - hot_file.stat().st_mtime)
        ok.append(f"hot.md: exists ({age}s old)")
    else:
        warnings.append("hot.md: not found (will be created on next session)")

    if prefetch_file.exists():
        age = int(datetime.now().timestamp() - prefetch_file.stat().st_mtime)
        ok.append(f"prefetched.md: exists ({age}s old)")
    else:
        warnings.append("prefetched.md: not found (background prefetch pending)")

    # 5. Backups
    if BACKUP_DIR.exists():
        backups = sorted([d for d in BACKUP_DIR.iterdir() if d.is_dir() and len(d.name) == 10])
        if backups:
            latest = backups[-1].name
            ok.append(f"Backups: {len(backups)} snapshots (latest: {latest})")
        else:
            warnings.append("Backups: directory exists but no snapshots")
    else:
        issues.append("Backups: directory not found (run backup_memory.sh)")

    # 6. Crons
    try:
        cron_result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
        cron_text = cron_result.stdout
        has_heartbeat = "heartbeat.sh" in cron_text
        has_backup = "backup_memory.sh" in cron_text
        if has_heartbeat and has_backup:
            ok.append("Crons: heartbeat + backup active")
        else:
            missing = []
            if not has_heartbeat:
                missing.append("heartbeat")
            if not has_backup:
                missing.append("backup")
            warnings.append(f"Crons: missing {', '.join(missing)}")
    except Exception:
        warnings.append("Crons: could not check crontab")

    # Print report
    print("\n═══ Memory Doctor Health Report ═══\n")
    if issues:
        print("CRITICAL:")
        for i in issues:
            print(f"  [X] {i}")
    if warnings:
        print("\nWARNINGS:")
        for w in warnings:
            print(f"  [!] {w}")
    print("\nOK:")
    for o in ok:
        print(f"  [+] {o}")

    print(f"\nVerdict: {len(issues)} critical, {len(warnings)} warnings, {len(ok)} ok")
    return len(issues) == 0


# ─── DEDUP CHECK ─────────────────────────────────────────

def _parse_memory_file(filepath: Path) -> dict:
    """Parse a memory file into metadata + body."""
    try:
        content = filepath.read_text(encoding="utf-8").strip()
    except Exception:
        return {"path": filepath, "raw": "", "body": "", "meta": {}, "words": set()}

    body = content
    meta = {}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            body = parts[2].strip()

    normalized = " ".join(body.lower().split())
    words = set(normalized.split())

    return {
        "path": filepath,
        "raw": content,
        "body": body,
        "meta": meta,
        "normalized": normalized,
        "words": words,
        "size": len(content),
        "mtime": filepath.stat().st_mtime,
    }


def _compute_similarity(a: dict, b: dict) -> float:
    """Jaccard similarity on word sets."""
    if not a["words"] or not b["words"]:
        return 0.0
    return len(a["words"] & b["words"]) / max(len(a["words"] | b["words"]), 1)


def _find_duplicate_pairs(files: list[Path], threshold: float = 0.75) -> list[tuple]:
    """Find all pairs of files above similarity threshold."""
    parsed = [_parse_memory_file(f) for f in files if f.exists()]
    parsed = [p for p in parsed if p["body"]]  # skip empty

    pairs = []
    for i in range(len(parsed)):
        for j in range(i + 1, len(parsed)):
            sim = _compute_similarity(parsed[i], parsed[j])
            if sim >= threshold:
                pairs.append((parsed[i], parsed[j], sim))

    # Sort by similarity descending (merge most similar first)
    pairs.sort(key=lambda x: x[2], reverse=True)
    return pairs


def dedup_check(verbose: bool = False) -> int:
    """Find duplicate or very similar memory files."""
    feedback_files = list(MEMORY_BASE.glob("feedback_*.md"))
    project_files = [f for f in MEMORY_BASE.rglob("*.md") if f.name == "CONTEXT.md"]

    dupes_found = 0

    # Strategy 1: Feedback files
    pairs = _find_duplicate_pairs(feedback_files, threshold=0.75)
    for a, b, sim in pairs:
        dupes_found += 1
        print(f"[dedup] Similar ({sim:.0%}): {a['path'].name} <-> {b['path'].name}")
        if verbose:
            print(f"  A: {a['normalized'][:80]}...")
            print(f"  B: {b['normalized'][:80]}...")

    # Strategy 2: Project CONTEXT.md files
    ctx_pairs = _find_duplicate_pairs(project_files, threshold=0.80)
    for a, b, sim in ctx_pairs:
        dupes_found += 1
        print(f"[dedup] Similar contexts ({sim:.0%}): {a['path'].parent.name} <-> {b['path'].parent.name}")

    if dupes_found == 0:
        print("[dedup] No duplicates found")
    else:
        print(f"\n[dedup] {dupes_found} potential duplicate(s) found")

    return dupes_found


# ─── DEDUP FIX (AUTO-MERGE) ──────────────────────────────

def _merge_feedback_pair(keep: dict, remove: dict) -> str:
    """Merge two similar feedback files. Keep the richer one, absorb unique content from the other.

    Strategy:
      - Keep the file with more content (larger body)
      - If the weaker file has unique sentences, append them under a '---' separator
      - Preserve the keeper's frontmatter
      - Return the merged content
    """
    keep_sentences = set(s.strip() for s in keep["body"].replace("\n", ". ").split(". ") if len(s.strip()) > 10)
    remove_sentences = set(s.strip() for s in remove["body"].replace("\n", ". ").split(". ") if len(s.strip()) > 10)

    unique_in_removed = remove_sentences - keep_sentences
    # Filter out sentences that are substrings of existing content
    truly_unique = []
    keep_lower = keep["body"].lower()
    for sentence in unique_in_removed:
        if sentence.lower() not in keep_lower:
            truly_unique.append(sentence)

    if not truly_unique:
        # Nothing unique in the weaker file — just keep the stronger one as-is
        return keep["raw"]

    # Append unique content
    merged = keep["raw"].rstrip()
    merged += "\n\n<!-- Merged from " + remove["path"].name + " -->\n"
    for sentence in truly_unique:
        merged += f"- {sentence}\n"

    return merged


def dedup_fix(dry_run: bool = True) -> int:
    """Auto-merge duplicate memory files.

    For feedback files:
      - Finds pairs with >75% word overlap
      - Keeps the larger/newer file, merges unique content from the other
      - Moves the weaker file to archive/
      - Updates MEMORY.md index if the removed file was listed

    For project CONTEXT.md:
      - Reports only (projects shouldn't be auto-merged — they may be intentional forks)

    Returns number of merges performed.
    """
    feedback_files = list(MEMORY_BASE.glob("feedback_*.md"))
    pairs = _find_duplicate_pairs(feedback_files, threshold=0.75)

    if not pairs:
        print("[dedup-fix] No duplicates found — nothing to merge")
        return 0

    archive_dir = MEMORY_BASE / "archive"
    merged_count = 0
    already_removed = set()

    for a, b, sim in pairs:
        # Skip if either file was already merged in this run
        if a["path"] in already_removed or b["path"] in already_removed:
            continue

        # Keep the larger file (more content = more complete)
        # Tie-break: keep the newer file
        if a["size"] > b["size"]:
            keep, remove = a, b
        elif b["size"] > a["size"]:
            keep, remove = b, a
        elif a["mtime"] >= b["mtime"]:
            keep, remove = a, b
        else:
            keep, remove = b, a

        print(f"[dedup-fix] Merge ({sim:.0%}): keep {keep['path'].name}, absorb {remove['path'].name}")

        if dry_run:
            print(f"  [dry-run] Would merge unique content and archive {remove['path'].name}")
            continue

        # Merge content
        merged_content = _merge_feedback_pair(keep, remove)
        keep["path"].write_text(merged_content, encoding="utf-8")
        print(f"  [write] Updated {keep['path'].name}")

        # Archive the removed file
        archive_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d")
        archive_name = f"{remove['path'].stem}-merged-{timestamp}.md"
        archive_path = archive_dir / archive_name
        shutil.move(str(remove["path"]), str(archive_path))
        print(f"  [archive] {remove['path'].name} → archive/{archive_name}")

        # Update MEMORY.md index — remove the line referencing the deleted file
        _remove_from_memory_index(remove["path"].name)

        already_removed.add(remove["path"])
        merged_count += 1

    # Also check project CONTEXT.md (report only — don't auto-merge projects)
    project_files = [f for f in MEMORY_BASE.rglob("*.md") if f.name == "CONTEXT.md"]
    ctx_pairs = _find_duplicate_pairs(project_files, threshold=0.80)
    for a, b, sim in ctx_pairs:
        print(f"[dedup-fix] WARN: Similar project contexts ({sim:.0%}): {a['path'].parent.name} <-> {b['path'].parent.name}")
        print(f"  Projects are NOT auto-merged — review manually if these should be consolidated")

    if dry_run and merged_count == 0 and pairs:
        print(f"\n[dedup-fix] Dry run: {len(pairs)} pair(s) would be merged. Use --apply to execute.")
    elif merged_count > 0:
        print(f"\n[dedup-fix] Merged {merged_count} duplicate(s). Originals archived in memory/archive/")
    else:
        print("[dedup-fix] No duplicates to merge")

    return merged_count


def _remove_from_memory_index(filename: str):
    """Remove a reference to a file from MEMORY.md index."""
    memory_index = MEMORY_BASE / "MEMORY.md"
    if not memory_index.exists():
        return

    content = memory_index.read_text(encoding="utf-8")
    lines = content.split("\n")

    # Remove lines that reference this filename (without extension)
    stem = filename.replace(".md", "")
    new_lines = [line for line in lines if stem not in line]

    if len(new_lines) < len(lines):
        memory_index.write_text("\n".join(new_lines), encoding="utf-8")
        print(f"  [index] Removed {stem} from MEMORY.md")


# ─── PRUNE DORMANT PROJECTS ─────────────────────────────

def prune_projects(days: int = 90, dry_run: bool = True):
    """Archive SESSION.md from projects untouched for >N days."""
    projects_dir = MEMORY_BASE / "projects"
    if not projects_dir.exists():
        print("[prune] No projects directory found")
        return

    cutoff = datetime.now().timestamp() - (days * 86400)
    pruned = []

    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir() or project_dir.name == "REGISTRY.md":
            continue

        session_file = project_dir / "SESSION.md"
        if not session_file.exists():
            continue

        mtime = session_file.stat().st_mtime
        age_days = int((datetime.now().timestamp() - mtime) / 86400)

        if mtime < cutoff:
            pruned.append((project_dir.name, age_days, session_file))

    if not pruned:
        print(f"[prune] No dormant projects (>{days} days)")
        return

    print(f"[prune] {len(pruned)} dormant project(s):")
    for name, age, path in pruned:
        action = "would archive" if dry_run else "archiving"
        print(f"  {action}: {name}/SESSION.md ({age} days old)")
        if not dry_run:
            archive_dir = path.parent / "archive"
            archive_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d")
            shutil.move(str(path), str(archive_dir / f"SESSION-{timestamp}.md"))

    if dry_run:
        print(f"\n[prune] Dry run. Use 'memory_doctor.py prune --apply' to execute.")


# ─── RESTORE FROM BACKUP ────────────────────────────────

def restore(date: str, target: str = "all"):
    """Restore memory from a backup snapshot.

    Args:
        date: Backup date (YYYY-MM-DD)
        target: What to restore — 'all', 'qdrant', 'redis', 'memory', 'context'
    """
    backup_path = BACKUP_DIR / date
    if not backup_path.exists():
        available = sorted([d.name for d in BACKUP_DIR.iterdir() if d.is_dir() and len(d.name) == 10])
        print(f"[restore] Backup '{date}' not found.")
        if available:
            print(f"[restore] Available: {', '.join(available)}")
        return False

    print(f"[restore] Restoring from {backup_path}")

    targets = [target] if target != "all" else ["qdrant", "memory", "context"]

    for t in targets:
        source = backup_path / t
        if t == "qdrant" and source.exists():
            print(f"  Qdrant: {source} → {QDRANT_PATH}")
            if QDRANT_PATH.exists():
                # Remove lock before restoring
                lock = QDRANT_PATH / ".lock"
                if lock.exists():
                    lock.unlink()
                shutil.rmtree(QDRANT_PATH)
            shutil.copytree(source, QDRANT_PATH)

        elif t == "memory" and source.exists():
            print(f"  Memory: {source} → {MEMORY_BASE}")
            # Don't delete existing — merge (backup wins for conflicts)
            for f in source.rglob("*"):
                if f.is_file():
                    rel = f.relative_to(source)
                    dest = MEMORY_BASE / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dest)

        elif t == "context" and source.exists():
            print(f"  Context: {source} → {CONTEXT_DIR}")
            for f in source.glob("*.md"):
                shutil.copy2(f, CONTEXT_DIR / f.name)

        elif not source.exists():
            print(f"  SKIP: {t} (not in backup)")

    print("[restore] Done. Run the indexer to rebuild Qdrant if restored.")
    return True


# ─── AUTO-REPAIR ─────────────────────────────────────────

def repair():
    """Auto-fix common issues without user interaction."""
    fixes = 0

    # 1. Remove stale Qdrant lock
    lock = QDRANT_PATH / ".lock"
    if lock.exists():
        holder = _get_lock_holder(lock)
        if not holder:
            lock_age = int(datetime.now().timestamp() - lock.stat().st_mtime)
            if lock_age > 300:
                lock.unlink()
                print(f"[repair] Removed stale Qdrant .lock ({lock_age}s old)")
                fixes += 1

    # 2. Ensure context directory exists
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)

    # 3. Ensure learning directory exists
    learning_dir = CONTEXT_DIR / "learning"
    learning_dir.mkdir(parents=True, exist_ok=True)

    # 4. Ensure logs directory exists
    log_dir = CONTEXT_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # 5. Try to restart Redis if down
    try:
        result = subprocess.run(["redis-cli", "ping"], capture_output=True, text=True, timeout=5)
        if result.stdout.strip() != "PONG":
            subprocess.run(["brew", "services", "start", "redis"], capture_output=True, timeout=10)
            print("[repair] Attempted Redis restart")
            fixes += 1
    except Exception:
        pass

    # 6. Fix MEMORY.md if it's missing
    memory_index = MEMORY_BASE / "MEMORY.md"
    if not memory_index.exists():
        print("[repair] MEMORY.md missing — cannot auto-create (needs manual review)")

    # 7. Ensure projects/REGISTRY.md exists
    if not REGISTRY_FILE.exists():
        print("[repair] REGISTRY.md missing — cannot auto-create (needs manual review)")

    print(f"[repair] {fixes} issue(s) fixed")
    return fixes


# ─── HELPERS ─────────────────────────────────────────────

def _get_lock_holder(lock_path: Path) -> str:
    """Check if a process holds the lock file. Returns PID or empty string."""
    try:
        result = subprocess.run(
            ["lsof", str(lock_path)], capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.strip().split("\n")
        if len(lines) > 1:
            return lines[-1].split()[1]
    except Exception:
        pass
    return ""


# ─── MAIN ────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "health":
        check_health()

    elif command == "dedup-check":
        dedup_check(verbose="--verbose" in sys.argv)

    elif command == "dedup-fix":
        dry_run = "--apply" not in sys.argv
        dedup_fix(dry_run=dry_run)

    elif command == "prune":
        days = 90
        if "--days" in sys.argv:
            idx = sys.argv.index("--days")
            if idx + 1 < len(sys.argv):
                days = int(sys.argv[idx + 1])
        dry_run = "--apply" not in sys.argv
        prune_projects(days=days, dry_run=dry_run)

    elif command == "restore":
        if len(sys.argv) < 3:
            print("[error] Usage: memory_doctor.py restore <YYYY-MM-DD> [qdrant|redis|memory|context|all]")
            sys.exit(1)
        date = sys.argv[2]
        target = sys.argv[3] if len(sys.argv) > 3 else "all"
        restore(date, target)

    elif command == "repair":
        repair()

    else:
        print(f"[error] Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
