#!/usr/bin/env python3
"""
Learning loop: makes the memory system get smarter over time.

4 systems:
  1. Relevance tracking  — track which retrieved chunks were useful vs ignored
  2. Weight evolution     — boost useful chunks, decay ignored ones in Qdrant
  3. Pattern extraction   — find recurring patterns across projects
  4. Auto-consolidation   — merge related memories into higher-quality summaries

Usage:
    # Track that a chunk was useful (called by Claude during sessions)
    python3 learning_loop.py track-useful --source "projects/hireflow/DECISIONS.md" --query "auth approach"

    # Track that a chunk was retrieved but ignored
    python3 learning_loop.py track-ignored --source "conducting-ai-session.md" --query "auth approach"

    # Run the learning cycle (updates weights, extracts patterns, consolidates)
    python3 learning_loop.py evolve

    # Show learning stats
    python3 learning_loop.py stats

    # Extract cross-project patterns
    python3 learning_loop.py patterns
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from models import MEMORY_BASE, CONTEXT_DIR

REDIS_PREFIX = "claude:"
LEARNING_DIR = CONTEXT_DIR / "learning"
STATS_FILE = LEARNING_DIR / "retrieval-stats.json"
PATTERNS_FILE = LEARNING_DIR / "patterns.md"
WEIGHTS_FILE = LEARNING_DIR / "weights.json"


def get_redis():
    import redis
    return redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)


def ensure_dirs():
    LEARNING_DIR.mkdir(parents=True, exist_ok=True)


def load_stats() -> dict:
    """Load retrieval statistics."""
    if STATS_FILE.exists():
        return json.loads(STATS_FILE.read_text())
    return {"useful": {}, "ignored": {}, "queries": [], "sessions": 0}


def save_stats(stats: dict):
    ensure_dirs()
    STATS_FILE.write_text(json.dumps(stats, indent=2))


# ─── 1. RELEVANCE TRACKING ────────────────────────────────

def track_useful(source: str, query: str):
    """Record that a retrieved chunk was actually used by the agent/user."""
    stats = load_stats()
    if source not in stats["useful"]:
        stats["useful"][source] = {"count": 0, "queries": [], "last_used": ""}
    stats["useful"][source]["count"] += 1
    stats["useful"][source]["last_used"] = datetime.now().isoformat()
    if query and query not in stats["useful"][source]["queries"]:
        stats["useful"][source]["queries"].append(query)
        # Keep last 10 queries per source
        stats["useful"][source]["queries"] = stats["useful"][source]["queries"][-10:]
    save_stats(stats)
    print(f"[track] Marked '{source}' as useful (count: {stats['useful'][source]['count']})")


def track_ignored(source: str, query: str):
    """Record that a retrieved chunk was returned but not used."""
    stats = load_stats()
    if source not in stats["ignored"]:
        stats["ignored"][source] = {"count": 0, "queries": [], "last_seen": ""}
    stats["ignored"][source]["count"] += 1
    stats["ignored"][source]["last_seen"] = datetime.now().isoformat()
    if query and query not in stats["ignored"][source]["queries"]:
        stats["ignored"][source]["queries"].append(query)
        stats["ignored"][source]["queries"] = stats["ignored"][source]["queries"][-10:]
    save_stats(stats)
    print(f"[track] Marked '{source}' as ignored (count: {stats['ignored'][source]['count']})")


def track_session():
    """Increment session counter and append to daily log."""
    stats = load_stats()
    stats["sessions"] = stats.get("sessions", 0) + 1
    save_stats(stats)

    # Append to daily session log (YYYY-MM-DD.md)
    log_dir = CONTEXT_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"{today}.md"

    cwd = os.getcwd()
    project = os.path.basename(cwd) if cwd != str(Path.home()) else "home"
    timestamp = datetime.now().strftime("%H:%M")

    entry = f"- {timestamp} | {project} | session #{stats['sessions']}\n"

    with open(log_file, "a") as f:
        f.write(entry)


# ─── 2. WEIGHT EVOLUTION ──────────────────────────────────

def compute_weights(stats: dict) -> dict:
    """Compute retrieval weights from usage stats.

    Weight formula:
      useful_count / (useful_count + ignored_count + 1)

    Score 0.0 → always ignored (demote in results)
    Score 0.5 → neutral
    Score 1.0 → always useful (boost in results)
    """
    weights = {}
    all_sources = set(list(stats.get("useful", {}).keys()) + list(stats.get("ignored", {}).keys()))

    for source in all_sources:
        useful = stats.get("useful", {}).get(source, {}).get("count", 0)
        ignored = stats.get("ignored", {}).get(source, {}).get("count", 0)
        weight = useful / (useful + ignored + 1)
        weights[source] = {
            "weight": round(weight, 3),
            "useful": useful,
            "ignored": ignored,
            "verdict": "boost" if weight > 0.6 else "neutral" if weight > 0.3 else "demote",
        }

    return weights


def save_weights(weights: dict):
    ensure_dirs()
    WEIGHTS_FILE.write_text(json.dumps(weights, indent=2))
    print(f"[weights] Updated {len(weights)} source weights → {WEIGHTS_FILE}")


def get_weight(source: str) -> float:
    """Get the learned weight for a source file. Returns 0.5 if unknown."""
    if WEIGHTS_FILE.exists():
        weights = json.loads(WEIGHTS_FILE.read_text())
        return weights.get(source, {}).get("weight", 0.5)
    return 0.5


# ─── 3. PATTERN EXTRACTION ────────────────────────────────

def extract_patterns(stats: dict) -> list[dict]:
    """Find recurring patterns across projects from usage data.

    Patterns detected:
    - Same query matches useful chunks across multiple projects
    - Same source file useful for multiple different queries (hub knowledge)
    - Feedback rules that get loaded in every session (universal rules)
    """
    patterns = []

    # Pattern 1: Hub knowledge (one file useful for many queries)
    useful = stats.get("useful", {})
    for source, data in useful.items():
        if len(data.get("queries", [])) >= 3:
            patterns.append({
                "type": "hub_knowledge",
                "source": source,
                "query_count": len(data["queries"]),
                "queries": data["queries"][:5],
                "insight": f"'{source}' answers many different questions — high-value memory",
            })

    # Pattern 2: Frequently ignored (noise sources)
    ignored = stats.get("ignored", {})
    for source, data in ignored.items():
        useful_count = useful.get(source, {}).get("count", 0)
        if data["count"] >= 5 and useful_count == 0:
            patterns.append({
                "type": "noise_source",
                "source": source,
                "ignored_count": data["count"],
                "insight": f"'{source}' retrieved {data['count']} times but never used — consider removing or re-chunking",
            })

    # Pattern 3: Cross-project decisions (same decision type across projects)
    decision_queries = defaultdict(list)
    for source, data in useful.items():
        if "decisions" in source.lower() or "decision" in str(data.get("queries", [])).lower():
            project = source.split("/")[1] if "/" in source else "global"
            for q in data.get("queries", []):
                decision_queries[q].append(project)

    for query, projects in decision_queries.items():
        if len(set(projects)) >= 2:
            patterns.append({
                "type": "cross_project_pattern",
                "query": query,
                "projects": list(set(projects)),
                "insight": f"Decision pattern '{query}' spans {len(set(projects))} projects — consider a universal rule",
            })

    return patterns


def write_patterns(patterns: list[dict]):
    ensure_dirs()
    lines = [
        "# Learned Patterns",
        f"<!-- Generated: {datetime.now().isoformat()} -->",
        "",
    ]

    if not patterns:
        lines.append("No patterns detected yet. Use the system more to build learning data.")
    else:
        for p in patterns:
            ptype = p["type"].replace("_", " ").title()
            lines.append(f"## {ptype}")
            lines.append("")
            lines.append(f"**{p['insight']}**")
            if "source" in p:
                lines.append(f"- Source: `{p['source']}`")
            if "queries" in p:
                lines.append(f"- Queries: {', '.join(p['queries'][:5])}")
            if "projects" in p:
                lines.append(f"- Projects: {', '.join(p['projects'])}")
            lines.append("")

    content = "\n".join(lines)
    PATTERNS_FILE.write_text(content)
    print(f"[patterns] {len(patterns)} patterns → {PATTERNS_FILE}")


# ─── 4. AUTO-CONSOLIDATION ────────────────────────────────

def suggest_consolidations(stats: dict) -> list[dict]:
    """Suggest memories that should be merged or promoted.

    Rules:
    - If 3+ chunks from the same file are all useful → promote the whole file
    - If a feedback rule is useful in 5+ sessions → promote to CLAUDE.md
    - If a pattern appears in 3+ projects → create a universal rule
    """
    suggestions = []
    useful = stats.get("useful", {})

    # Group useful chunks by parent file
    by_file = defaultdict(int)
    for source, data in useful.items():
        base_file = source.split("#")[0] if "#" in source else source
        by_file[base_file] += data.get("count", 0)

    for source_file, total_uses in by_file.items():
        if total_uses >= 5:
            suggestions.append({
                "action": "promote",
                "source": source_file,
                "uses": total_uses,
                "reason": f"Used {total_uses} times — consider promoting key content to CONTEXT.md or CLAUDE.md",
            })

    # Feedback rules used across many sessions
    for source, data in useful.items():
        if "feedback" in source and data.get("count", 0) >= 5:
            suggestions.append({
                "action": "promote_to_claude_md",
                "source": source,
                "uses": data["count"],
                "reason": f"Feedback rule used {data['count']} times — stable enough for CLAUDE.md",
            })

    return suggestions


# ─── EVOLVE: RUN THE FULL LEARNING CYCLE ──────────────────

def evolve():
    """Run the complete learning cycle."""
    stats = load_stats()

    print(f"[evolve] Sessions tracked: {stats.get('sessions', 0)}")
    print(f"[evolve] Useful sources: {len(stats.get('useful', {}))}")
    print(f"[evolve] Ignored sources: {len(stats.get('ignored', {}))}")

    # Step 1: Compute and save weights
    weights = compute_weights(stats)
    save_weights(weights)

    boosted = sum(1 for w in weights.values() if w["verdict"] == "boost")
    demoted = sum(1 for w in weights.values() if w["verdict"] == "demote")
    print(f"[evolve] Weights: {boosted} boosted, {demoted} demoted, {len(weights) - boosted - demoted} neutral")

    # Step 2: Extract patterns
    patterns = extract_patterns(stats)
    write_patterns(patterns)

    # Step 3: Suggest consolidations
    suggestions = suggest_consolidations(stats)
    if suggestions:
        print(f"\n[consolidate] Suggestions:")
        for s in suggestions:
            print(f"  {s['action']}: {s['source']} ({s['reason']})")
    else:
        print(f"[consolidate] No consolidation suggestions yet (need more usage data)")

    print(f"\n[evolve] Learning cycle complete.")


def show_stats():
    """Display learning statistics."""
    stats = load_stats()

    print(f"Sessions: {stats.get('sessions', 0)}")
    print(f"Useful sources: {len(stats.get('useful', {}))}")
    print(f"Ignored sources: {len(stats.get('ignored', {}))}")

    if stats.get("useful"):
        print(f"\nTop useful (most retrieved & used):")
        sorted_useful = sorted(stats["useful"].items(), key=lambda x: x[1]["count"], reverse=True)
        for source, data in sorted_useful[:10]:
            print(f"  {data['count']}x | {source}")

    if stats.get("ignored"):
        print(f"\nTop ignored (retrieved but never used):")
        sorted_ignored = sorted(stats["ignored"].items(), key=lambda x: x[1]["count"], reverse=True)
        for source, data in sorted_ignored[:10]:
            # Check if also useful
            useful_count = stats.get("useful", {}).get(source, {}).get("count", 0)
            tag = f" (also useful {useful_count}x)" if useful_count else " ← noise"
            print(f"  {data['count']}x | {source}{tag}")

    if WEIGHTS_FILE.exists():
        weights = json.loads(WEIGHTS_FILE.read_text())
        demoted = {k: v for k, v in weights.items() if v["verdict"] == "demote"}
        if demoted:
            print(f"\nDemoted sources (consider re-chunking or removing):")
            for source, data in demoted.items():
                print(f"  weight={data['weight']} | {source}")


def main():
    if len(sys.argv) < 2:
        print("Usage: learning_loop.py <track-useful|track-ignored|evolve|stats|patterns>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "track-useful":
        source = query = ""
        if "--source" in sys.argv:
            idx = sys.argv.index("--source")
            source = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        if "--query" in sys.argv:
            idx = sys.argv.index("--query")
            query = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        if not source:
            print("[error] --source required", file=sys.stderr)
            sys.exit(1)
        track_useful(source, query)

    elif command == "track-ignored":
        source = query = ""
        if "--source" in sys.argv:
            idx = sys.argv.index("--source")
            source = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        if "--query" in sys.argv:
            idx = sys.argv.index("--query")
            query = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        if not source:
            print("[error] --source required", file=sys.stderr)
            sys.exit(1)
        track_ignored(source, query)

    elif command == "evolve":
        evolve()

    elif command == "stats":
        show_stats()

    elif command == "patterns":
        stats = load_stats()
        patterns = extract_patterns(stats)
        write_patterns(patterns)
        if patterns:
            for p in patterns:
                print(f"  [{p['type']}] {p['insight']}")
        else:
            print("No patterns yet. Track more usage first.")

    elif command == "session-start":
        track_session()

    else:
        print(f"[error] Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
