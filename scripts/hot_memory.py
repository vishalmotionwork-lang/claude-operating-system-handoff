#!/usr/bin/env python3
"""
Hot memory layer using Redis for instant context retrieval.

Three-tier architecture:
  Redis (hot)   → <1ms  → active project, recent decisions, session state
  Qdrant (warm) → ~6s   → fast semantic search (MiniLM)
  Qdrant (deep) → ~15s  → high-quality semantic search (BGE-large)
  Files (cold)  → disk  → persistent source of truth

Usage:
    python3 ~/.claude/scripts/hot_memory.py hook
    python3 ~/.claude/scripts/hot_memory.py load --project hireflow
    python3 ~/.claude/scripts/hot_memory.py get
    python3 ~/.claude/scripts/hot_memory.py store --key "auth-decision" --value "Using Supabase Auth"
    python3 ~/.claude/scripts/hot_memory.py warm --project hireflow
    python3 ~/.claude/scripts/hot_memory.py deep-search --query "auth architecture patterns"
    python3 ~/.claude/scripts/hot_memory.py flush
"""

import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from models import MEMORY_BASE, CONTEXT_DIR, MODELS, clear_stale_qdrant_lock

REDIS_PREFIX = "claude:"
HOT_FILE = CONTEXT_DIR / "hot.md"

# Base TTLs in seconds (before access-count boosting)
# Aligned with actual knowledge lifetimes, not arbitrary short windows
BASE_TTLS = {
    "session": 4 * 3600,         # 4h — runtime decisions, current task context
    "project": 7 * 24 * 3600,    # 7d — project files (stack doesn't change daily)
    "decisions": 30 * 24 * 3600,  # 30d — architectural decisions (rarely change)
    "feedback": 90 * 24 * 3600,   # 90d — user preferences (almost permanent)
    "user": 180 * 24 * 3600,      # 180d — user profile (effectively permanent)
    "deep": 4 * 3600,             # 4h — deep search cache
}

# Access-count boost: each read extends TTL by this multiplier (capped at 3x base)
ACCESS_BOOST_FACTOR = 1.2
ACCESS_BOOST_CAP = 3.0

# Legacy aliases for backward compat
TTL_SESSION = BASE_TTLS["session"]
TTL_PROJECT = BASE_TTLS["project"]
TTL_FEEDBACK = BASE_TTLS["feedback"]
TTL_DEEP = BASE_TTLS["deep"]


def get_redis():
    """Connect to local Redis."""
    import redis
    return redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)


def track_access(r, key: str, category: str = "project"):
    """Track access count and boost TTL for frequently accessed keys.

    Every read increments the access counter. TTL extends by ACCESS_BOOST_FACTOR
    per access, capped at ACCESS_BOOST_CAP * base TTL.

    This implements the useful part of 'Ebbinghaus decay' —
    frequently used memories stay hot longer, rarely used ones expire naturally.
    """
    access_key = f"{REDIS_PREFIX}access:{key}"
    count = r.incr(access_key)
    r.expire(access_key, BASE_TTLS.get(category, BASE_TTLS["project"]))

    base_ttl = BASE_TTLS.get(category, BASE_TTLS["project"])
    boosted_ttl = int(min(
        base_ttl * (ACCESS_BOOST_FACTOR ** min(count, 20)),  # cap iterations
        base_ttl * ACCESS_BOOST_CAP,
    ))

    # Extend the actual key's TTL
    current_ttl = r.ttl(key)
    if current_ttl > 0 and boosted_ttl > current_ttl:
        r.expire(key, boosted_ttl)

    return count


def get_with_tracking(r, key: str, category: str = "project") -> str:
    """Get a value from Redis and track the access for TTL boosting."""
    value = r.get(key)
    if value is not None:
        track_access(r, key, category)
    return value


def detect_project() -> str:
    """Detect project from cwd."""
    cwd = os.getcwd().lower()
    hints = {
        # Order matters — more specific matches first
        "hireflow-gsd": "hireflow-gsd",
        "hireflow": "hireflow",
        "knowai-canvas": "knowai-canvas",
        "knowai-erp": "knowai-erp",
        "knowai-masterplan": "knowai-masterplan",
        "knowai-gameplan": "knowai-gameplan",
        "knowai development": "knowai-dashboard",
        "knowai": "knowai-dashboard",
        "meetingrecorder": "meeting-recorder",
        "weedio": "weedio-tool",
        "figma-to-website": "zeelai-website",
        "mind-buddy": "mind-buddy",
        "founders-house": "founders-house",
        "college-project": "college-project",
        "youtube": "youtube-plan",
        "meditation": "meditation-app",
        "ai-concepts": "ai-concepts-encyclopedia",
        "beacon": "beacon",
        "marqit": "marqit",
        "personal task": "personal-tasks",
    }
    for hint, project in hints.items():
        if hint in cwd:
            return project
    return ""


def load_project(r, project: str):
    """Load a project's file-based context into Redis hot memory."""
    project_dir = MEMORY_BASE / "projects" / project

    loaded = 0

    # Priority 0: USER.md (always loaded, longest TTL)
    user_file = MEMORY_BASE / "USER.md"
    if user_file.exists():
        content = user_file.read_text(encoding="utf-8")
        if content.strip():
            r.set(f"{REDIS_PREFIX}user:profile", content, ex=BASE_TTLS["user"])
            loaded += 1

    # Priority 1-3: Project files
    files_to_load = {
        "context": project_dir / "CONTEXT.md",
        "session": project_dir / "SESSION.md",
        "decisions": project_dir / "DECISIONS.md",
    }

    for doc_type, filepath in files_to_load.items():
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8")
            if content.strip():
                key = f"{REDIS_PREFIX}project:{project}:{doc_type}"
                ttl = BASE_TTLS.get(doc_type, BASE_TTLS["project"])
                r.set(key, content, ex=ttl)
                loaded += 1

    # Feedback rules (long TTL)
    for f in MEMORY_BASE.glob("feedback_*.md"):
        content = f.read_text(encoding="utf-8")
        if content.strip():
            key = f"{REDIS_PREFIX}feedback:{f.stem}"
            r.set(key, content, ex=BASE_TTLS["feedback"])
            loaded += 1

    r.set(f"{REDIS_PREFIX}active_project", project, ex=TTL_SESSION)
    r.set(f"{REDIS_PREFIX}session_start", datetime.now().isoformat(), ex=TTL_SESSION)

    return loaded


def warm_from_qdrant(r, project: str):
    """Load Qdrant prefetch results into Redis."""
    prefetch_file = CONTEXT_DIR / "prefetched.md"
    if prefetch_file.exists():
        content = prefetch_file.read_text(encoding="utf-8")
        if content.strip():
            r.set(f"{REDIS_PREFIX}prefetched:{project}", content, ex=TTL_PROJECT)
            return True
    return False


def store_fact(r, key: str, value: str):
    """Store a runtime decision or fact in hot memory."""
    r.set(f"{REDIS_PREFIX}runtime:{key}", value, ex=TTL_SESSION)


def task_search(r, query: str):
    """Fast cross-project search using MiniLM. 2-3s, no project filter.

    This is the USEFUL Qdrant query: "what have we done before that's
    relevant to what we're about to do?" Returns cross-project decisions,
    patterns, and past mistakes — things folder reads can't give you.

    Use when the user describes their task. Not at session start.
    """
    from models import QDRANT_PATH, MODELS, clear_stale_qdrant_lock

    cache_key = f"{REDIS_PREFIX}task:{query[:80]}"
    cached = r.get(cache_key)
    if cached:
        print(f"[task] Cache hit for '{query[:50]}...'")
        return cached

    config = MODELS["fast"]

    clear_stale_qdrant_lock()

    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(config["name"])
    except Exception as e:
        print(f"[warn] Model load failed: {e}", file=sys.stderr)
        return None

    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(path=str(QDRANT_PATH))
    except RuntimeError as e:
        if "already accessed" in str(e):
            print("[warn] Qdrant locked.", file=sys.stderr)
            return None
        raise

    # NO project filter — search EVERYTHING. That's the point.
    embedding = model.encode(query).tolist()
    results = client.query_points(
        collection_name=config["collection"],
        query=embedding,
        limit=10,
    )
    client.close()

    # Group by project to show cross-project knowledge
    lines = [
        f"## Cross-project context: {query}",
        f"<!-- Fast search ({config['name']}) | {datetime.now().isoformat()} -->",
        "",
    ]

    seen_projects = set()
    for res in results.points:
        if res.score < 0.30:
            continue
        source = res.payload.get("source_file", "?")
        project = res.payload.get("project", "?")
        text = res.payload.get("text", "")[:300]

        project_tag = f"**[{project}]**" if project not in seen_projects else f"[{project}]"
        seen_projects.add(project)

        lines.append(f"{project_tag} `{source}` (score: {res.score:.2f})")
        lines.append(text)
        lines.append("")

    if len(seen_projects) > 1:
        lines.insert(3, f"> Found relevant context across {len(seen_projects)} projects: {', '.join(sorted(seen_projects))}")
        lines.insert(4, "")

    content = "\n".join(lines)

    # Cache in Redis (2h TTL)
    r.set(cache_key, content, ex=2 * 3600)

    # Write to file for Claude to read
    task_file = CONTEXT_DIR / "task-context.md"
    task_file.write_text(content, encoding="utf-8")
    print(f"[task] {len(seen_projects)} projects, {sum(1 for r in results.points if r.score >= 0.30)} results → {task_file}")

    return content


def deep_search(r, query: str, project: str = ""):
    """Run a deep search using BGE-large and cache results in Redis."""
    from models import QDRANT_PATH

    cache_key = f"{REDIS_PREFIX}deep:{query[:80]}"
    cached = r.get(cache_key)
    if cached:
        print(f"[deep] Cache hit for '{query[:50]}...'")
        return cached

    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    import signal

    config = MODELS["deep"]
    print(f"[deep] Loading {config['name']}...")

    def _timeout_handler(signum, frame):
        raise TimeoutError(f"Deep model loading timed out after 60s")

    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(60)
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(config["name"])
    except (TimeoutError, Exception) as e:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
        print(f"[warn] Deep model failed to load: {e}", file=sys.stderr)
        return None
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

    # Clear stale locks before opening embedded Qdrant
    if clear_stale_qdrant_lock():
        print("[deep] Cleared stale Qdrant lock", file=sys.stderr)

    try:
        client = QdrantClient(path=str(QDRANT_PATH))
    except RuntimeError as e:
        if "already accessed" in str(e):
            print("[warn] Qdrant locked by active process. Cannot run deep search.", file=sys.stderr)
            return None
        raise

    collections = [c.name for c in client.get_collections().collections]
    if config["collection"] not in collections:
        print(f"[warn] Deep collection not indexed. Run indexer first.", file=sys.stderr)
        client.close()
        return None

    search_filter = None
    if project:
        search_filter = Filter(
            should=[
                FieldCondition(key="project", match=MatchValue(value=project)),
                FieldCondition(key="project", match=MatchValue(value="global")),
            ]
        )

    embedding = model.encode(query).tolist()
    results = client.query_points(
        collection_name=config["collection"],
        query=embedding,
        query_filter=search_filter,
        limit=20,
    )
    client.close()

    lines = [
        f"## Deep Search: {query}",
        f"<!-- Model: {config['name']} | Time: {datetime.now().isoformat()} -->",
        "",
    ]
    for res in results.points:
        if res.score >= 0.35:
            source = res.payload.get("source_file", "?")
            lines.append(f"**[{source}]** (score: {res.score:.3f})")
            lines.append(res.payload.get("text", ""))
            lines.append("")

    content = "\n".join(lines)

    # Cache in Redis
    r.set(cache_key, content, ex=TTL_DEEP)

    # Also write to file for Claude to read
    deep_file = CONTEXT_DIR / "deep-search.md"
    deep_file.write_text(content, encoding="utf-8")
    print(f"[deep] {len(results.points)} results → {deep_file}")

    return content


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~1.3 tokens per word."""
    return int(len(text.split()) * 1.3)


def get_all_hot_context(r, token_budget: int = 4000) -> str:
    """Retrieve hot context within a token budget.

    Prioritized sections (loaded in order, stops when budget exhausted):
      0. User profile (WHO you are — always first, ~400 tokens)
      1. Feedback rules (prevent repeat mistakes — 300 chars each for full reasoning)
      2. Project decisions (high value per token)
      3. Project context (stack, URLs, commands)
      4. Session state (what happened last)
      5. Runtime facts (current session decisions)
      6. Vector prefetch (semantic matches — trimmed to fit)

    Default budget: 4,000 tokens (~3,000 words / ~200 lines).
    """
    sections = []
    tokens_used = 0

    active_project = r.get(f"{REDIS_PREFIX}active_project") or "unknown"
    session_start = r.get(f"{REDIS_PREFIX}session_start") or "unknown"

    header = f"# Hot Memory (Redis)\n<!-- Budget: {token_budget} tokens | {datetime.now().isoformat()} -->\n\n**Active project**: {active_project} | **Session**: {session_start}\n"
    tokens_used += estimate_tokens(header)

    # Priority 0: User profile (who you are — always first)
    user_profile = get_with_tracking(r, f"{REDIS_PREFIX}user:profile", "user")
    if user_profile:
        body = user_profile
        if "---" in user_profile:
            parts = user_profile.split("---", 2)
            if len(parts) >= 3:
                body = parts[2].strip()
        section_text = f"## User Profile\n\n{body}\n"
        section_tokens = estimate_tokens(section_text)
        if tokens_used + section_tokens <= token_budget:
            sections.append(section_text)
            tokens_used += section_tokens

    # Priority 1: Feedback rules (prevent repeat mistakes)
    feedback_keys = r.keys(f"{REDIS_PREFIX}feedback:*")
    if feedback_keys:
        feedback_lines = ["## Feedback Rules", ""]
        for key in sorted(feedback_keys):
            content = r.get(key)
            if content:
                body = content
                if "---" in content:
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        body = parts[2].strip()
                feedback_lines.append(f"- {body[:300]}")
        feedback_lines.append("")
        section_text = "\n".join(feedback_lines)
        section_tokens = estimate_tokens(section_text)
        if tokens_used + section_tokens <= token_budget:
            sections.append(section_text)
            tokens_used += section_tokens

    # Priority 2: Decisions (high value — non-obvious choices)
    decisions_key = f"{REDIS_PREFIX}project:{active_project}:decisions"
    decisions = get_with_tracking(r, decisions_key, "decisions")
    if decisions:
        trimmed = decisions[:1500]
        section_text = f"## Decisions\n\n{trimmed}\n"
        section_tokens = estimate_tokens(section_text)
        if tokens_used + section_tokens <= token_budget:
            sections.append(section_text)
            tokens_used += section_tokens

    # Priority 3: Project context (stack, commands, URLs)
    context_key = f"{REDIS_PREFIX}project:{active_project}:context"
    ctx = get_with_tracking(r, context_key, "project")
    if ctx:
        trimmed = ctx[:1200]
        section_text = f"## Project Context\n\n{trimmed}\n"
        section_tokens = estimate_tokens(section_text)
        if tokens_used + section_tokens <= token_budget:
            sections.append(section_text)
            tokens_used += section_tokens

    # Priority 4: Session state
    session_key = f"{REDIS_PREFIX}project:{active_project}:session"
    session = get_with_tracking(r, session_key, "session")
    if session:
        trimmed = session[:800]
        section_text = f"## Last Session\n\n{trimmed}\n"
        section_tokens = estimate_tokens(section_text)
        if tokens_used + section_tokens <= token_budget:
            sections.append(section_text)
            tokens_used += section_tokens

    # Priority 5: Runtime facts (current session)
    runtime_keys = r.keys(f"{REDIS_PREFIX}runtime:*")
    if runtime_keys:
        runtime_lines = ["## Session Decisions", ""]
        for key in sorted(runtime_keys):
            fact_name = key.replace(f"{REDIS_PREFIX}runtime:", "")
            value = r.get(key)
            runtime_lines.append(f"- **{fact_name}**: {value}")
        runtime_lines.append("")
        section_text = "\n".join(runtime_lines)
        section_tokens = estimate_tokens(section_text)
        if tokens_used + section_tokens <= token_budget:
            sections.append(section_text)
            tokens_used += section_tokens

    # Priority 6: Vector prefetch (fill remaining budget)
    remaining = token_budget - tokens_used
    if remaining > 200:
        prefetch = r.get(f"{REDIS_PREFIX}prefetched:{active_project}")
        if prefetch:
            # Trim to remaining budget (~0.77 words per token)
            max_chars = int(remaining * 4)
            trimmed = prefetch[:max_chars]
            section_text = f"## Vector Context\n\n{trimmed}\n"
            sections.append(section_text)
            tokens_used += estimate_tokens(section_text)

    result = header + "\n".join(sections)
    result += f"\n<!-- Tokens: ~{tokens_used}/{token_budget} -->"
    return result

    return "\n".join(lines)


def write_hot_file(content: str):
    """Write hot context to file."""
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    HOT_FILE.write_text(content, encoding="utf-8")


def flush(r):
    """Clear all hot memory."""
    keys = r.keys(f"{REDIS_PREFIX}*")
    if keys:
        r.delete(*keys)
    for f in [HOT_FILE, CONTEXT_DIR / "deep-search.md"]:
        if f.exists():
            f.unlink()


def hook(r):
    """Session-start hook: load project context into Redis and write hot file."""
    project = detect_project()

    if project:
        loaded = load_project(r, project)
        warm_from_qdrant(r, project)
        content = get_all_hot_context(r)
        write_hot_file(content)
        print(f"[hot] Loaded {loaded} files for '{project}' into Redis → {HOT_FILE}")
    else:
        for f in MEMORY_BASE.glob("feedback_*.md"):
            fc = f.read_text(encoding="utf-8")
            if fc.strip():
                r.set(f"{REDIS_PREFIX}feedback:{f.stem}", fc, ex=TTL_FEEDBACK)
        content = get_all_hot_context(r)
        write_hot_file(content)
        print(f"[hot] No project detected. Loaded feedback rules → {HOT_FILE}")


def main():
    if len(sys.argv) < 2:
        print("Usage: hot_memory.py <hook|load|get|store|warm|deep-search|flush> [options]")
        sys.exit(1)

    command = sys.argv[1]

    try:
        r = get_redis()
        r.ping()
    except Exception as e:
        print(f"[error] Redis not available: {e}", file=sys.stderr)
        print("[hint] Run: brew services start redis", file=sys.stderr)
        sys.exit(1)

    if command == "hook":
        hook(r)

    elif command == "load":
        project = ""
        if "--project" in sys.argv:
            idx = sys.argv.index("--project")
            project = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        else:
            project = detect_project()
        if not project:
            print("[error] No project specified or detected", file=sys.stderr)
            sys.exit(1)
        loaded = load_project(r, project)
        print(f"[load] {loaded} files loaded for '{project}'")

    elif command == "get":
        content = get_all_hot_context(r)
        write_hot_file(content)
        print(f"[get] Hot context written to {HOT_FILE}")

    elif command == "store":
        key = value = ""
        if "--key" in sys.argv:
            idx = sys.argv.index("--key")
            key = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        if "--value" in sys.argv:
            idx = sys.argv.index("--value")
            value = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        if not key or not value:
            print("[error] --key and --value required", file=sys.stderr)
            sys.exit(1)
        store_fact(r, key, value)
        print(f"[store] Saved '{key}' to hot memory (TTL: {TTL_SESSION}s)")

    elif command == "warm":
        project = ""
        if "--project" in sys.argv:
            idx = sys.argv.index("--project")
            project = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        else:
            project = detect_project()
        if warm_from_qdrant(r, project or "auto"):
            print(f"[warm] Prefetch loaded into Redis for '{project}'")
        else:
            print("[warm] No prefetch file found")

    elif command == "task-search":
        query = ""
        if "--query" in sys.argv:
            idx = sys.argv.index("--query")
            query = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        if not query:
            print("[error] --query required", file=sys.stderr)
            sys.exit(1)
        task_search(r, query)

    elif command == "deep-search":
        query = ""
        if "--query" in sys.argv:
            idx = sys.argv.index("--query")
            query = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        if not query:
            print("[error] --query required", file=sys.stderr)
            sys.exit(1)
        project = ""
        if "--project" in sys.argv:
            idx = sys.argv.index("--project")
            project = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        else:
            project = r.get(f"{REDIS_PREFIX}active_project") or ""
        deep_search(r, query, project)

    elif command == "switch":
        # Called when user selects a project mid-session.
        # Re-loads Redis, re-runs Qdrant prefetch with project-specific queries,
        # and regenerates hot.md — so everything is project-aware, not generic.
        project = ""
        if "--project" in sys.argv:
            idx = sys.argv.index("--project")
            project = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        if not project:
            print("[error] --project required for switch", file=sys.stderr)
            sys.exit(1)

        # 1. Load project files into Redis
        loaded = load_project(r, project)
        print(f"[switch] Loaded {loaded} files for '{project}' into Redis")

        # 2. Re-run Qdrant prefetch with project-specific queries (inline, not background)
        #    Must use uvx to get qdrant-client + sentence-transformers deps
        import subprocess as _sp
        scripts_dir = Path(__file__).parent
        prefetch_cmd = [
            "uvx", "--with", "qdrant-client", "--with", "sentence-transformers",
            "python3", str(scripts_dir / "prefetch_context.py"),
            "--project", project,
        ]
        print(f"[switch] Re-prefetching Qdrant for '{project}'...")
        _sp.run(prefetch_cmd, timeout=60)

        # 3. Warm Redis from new prefetch + regenerate hot.md
        warm_from_qdrant(r, project)
        content = get_all_hot_context(r)
        write_hot_file(content)
        print(f"[switch] Project '{project}' fully loaded — hot.md + prefetched.md updated")

    elif command == "flush":
        flush(r)
        print("[flush] Hot memory cleared")

    else:
        print(f"[error] Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
