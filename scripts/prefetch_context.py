#!/usr/bin/env python3
"""
Pre-fetch relevant context from Qdrant and write it to a file
that Claude Code loads automatically at session start.

Supports dual models:
  --fast (default for hooks): MiniLM, quick session context
  --deep: BGE-large, high-quality semantic search for research/architecture

Usage:
    python3 ~/.claude/scripts/prefetch_context.py --project hireflow
    python3 ~/.claude/scripts/prefetch_context.py --project hireflow --deep
    python3 ~/.claude/scripts/prefetch_context.py --query "authentication decisions" --deep
    python3 ~/.claude/scripts/prefetch_context.py --hook
"""

import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from models import QDRANT_PATH, CONTEXT_DIR, MODELS, get_model_for_task, clear_stale_qdrant_lock

OUTPUT_FILE_FAST = CONTEXT_DIR / "prefetched.md"
OUTPUT_FILE_DEEP = CONTEXT_DIR / "prefetched-deep.md"
MAX_CHUNKS_FAST = 15
MAX_CHUNKS_DEEP = 20
MIN_SCORE_FAST = 0.25
MIN_SCORE_DEEP = 0.35  # BGE scores higher, can afford stricter threshold


def detect_project_from_cwd() -> str:
    """Detect which project we're in based on cwd."""
    cwd = os.getcwd().lower()
    project_hints = {
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
    for hint, project in project_hints.items():
        if hint in cwd:
            return project
    return ""


def _fallback_file_search(queries: list[str], project_filter: str, max_chunks: int) -> list[dict]:
    """Graceful degradation: search memory files with substring matching when Qdrant is unavailable.

    This is the 'grep fallback' — worse than vector search but better than nothing.
    Inspired by Mohini's VectorStore trait pattern: try Qdrant → SQLite cosine → text LIKE.
    """
    from models import MEMORY_BASE

    results = []
    search_terms = []
    for q in queries:
        search_terms.extend(q.lower().split())

    # Remove common words
    stop_words = {"project", "context", "and", "the", "for", "current", "state", "stack", "decisions", "patterns"}
    search_terms = [t for t in search_terms if t not in stop_words and len(t) > 2]

    files_to_search = list(MEMORY_BASE.rglob("*.md"))
    if project_filter:
        # Prioritize project-specific files
        project_files = [f for f in files_to_search if project_filter in str(f)]
        other_files = [f for f in files_to_search if project_filter not in str(f)]
        files_to_search = project_files + other_files

    for filepath in files_to_search:
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception:
            continue

        if not content.strip():
            continue

        content_lower = content.lower()
        hits = sum(1 for term in search_terms if term in content_lower)
        if hits > 0:
            rel_path = str(filepath.relative_to(MEMORY_BASE)) if str(filepath).startswith(str(MEMORY_BASE)) else filepath.name
            score = hits / len(search_terms) if search_terms else 0
            results.append({
                "text": content[:500],
                "score": score,
                "source": rel_path,
                "project": project_filter or "global",
                "category": "fallback",
                "doc_type": filepath.stem.lower(),
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    # Tag results so the output file clearly shows fallback was used
    for r in results:
        r["category"] = "fallback (grep, NOT vector search)"
    print(f"[fallback] File search found {len(results[:max_chunks])} results (Qdrant unavailable)", file=sys.stderr)
    return results[:max_chunks]


def _load_model_with_timeout(model_name: str, timeout_sec: int = 30):
    """Load SentenceTransformer with a timeout to prevent hanging on model download."""
    import signal

    def _timeout_handler(signum, frame):
        raise TimeoutError(f"Model loading timed out after {timeout_sec}s: {model_name}")

    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(timeout_sec)
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(model_name)
        return model
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def fetch_context(queries: list[str], mode: str = "fast", project_filter: str = "") -> list[dict]:
    """Query Qdrant and return relevant chunks. Falls back to file search if Qdrant unavailable."""
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    if not QDRANT_PATH.exists():
        print("[warn] Qdrant storage not found. Falling back to file search.", file=sys.stderr)
        return _fallback_file_search(queries, project_filter, MAX_CHUNKS_FAST)

    config = MODELS[mode]
    collection = config["collection"]
    max_chunks = MAX_CHUNKS_DEEP if mode == "deep" else MAX_CHUNKS_FAST
    min_score = MIN_SCORE_DEEP if mode == "deep" else MIN_SCORE_FAST

    print(f"[{mode}] Model: {config['name']}")
    print(f"[{mode}] Collection: {collection}")

    timeout = 60 if mode == "deep" else 30  # BGE-large is bigger, needs more time
    try:
        model = _load_model_with_timeout(config["name"], timeout_sec=timeout)
    except (TimeoutError, Exception) as e:
        print(f"[warn] Model loading failed ({e}). Falling back to file search.", file=sys.stderr)
        return _fallback_file_search(queries, project_filter, max_chunks)

    # Clear stale locks before opening embedded Qdrant
    if clear_stale_qdrant_lock():
        print(f"[{mode}] Cleared stale Qdrant lock", file=sys.stderr)

    try:
        client = QdrantClient(path=str(QDRANT_PATH))
    except RuntimeError as e:
        if "already accessed" in str(e):
            print(f"[warn] Qdrant locked by active process. Falling back to file-based search.", file=sys.stderr)
            return _fallback_file_search(queries, project_filter, max_chunks)
        raise

    collections = [c.name for c in client.get_collections().collections]
    if collection not in collections:
        print(f"[warn] Collection '{collection}' not found. Falling back to file search.", file=sys.stderr)
        client.close()
        return _fallback_file_search(queries, project_filter, max_chunks)

    search_filter = None
    if project_filter:
        search_filter = Filter(
            should=[
                FieldCondition(key="project", match=MatchValue(value=project_filter)),
                FieldCondition(key="project", match=MatchValue(value="global")),
            ]
        )

    all_results = []
    seen_texts = set()

    for query in queries:
        embedding = model.encode(query).tolist()
        results = client.query_points(
            collection_name=collection,
            query=embedding,
            query_filter=search_filter,
            limit=max_chunks,
        )

        for r in results.points:
            text = r.payload.get("text", "")
            text_hash = hash(text[:100])
            if text_hash not in seen_texts and r.score >= min_score:
                seen_texts.add(text_hash)
                source = r.payload.get("source_file", "unknown")

                # Apply learned weight: boost useful sources, demote noisy ones
                from learning_loop import get_weight
                learned_weight = get_weight(source)  # 0.0-1.0, default 0.5
                # Blend: 70% vector score + 30% learned weight
                adjusted_score = (r.score * 0.7) + (learned_weight * 0.3)

                all_results.append({
                    "text": text,
                    "score": adjusted_score,
                    "raw_score": r.score,
                    "learned_weight": learned_weight,
                    "source": source,
                    "project": r.payload.get("project", "unknown"),
                    "category": r.payload.get("category", "unknown"),
                    "doc_type": r.payload.get("doc_type", "unknown"),
                })

    client.close()

    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results[:max_chunks]


def write_context_file(results: list[dict], project: str, queries: list[str], mode: str):
    """Write fetched context to a markdown file."""
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_FILE_DEEP if mode == "deep" else OUTPUT_FILE_FAST

    is_fallback = any(r.get("category", "").startswith("fallback") for r in results)
    source_label = "GREP FALLBACK — Qdrant was unavailable" if is_fallback else f"Vector Search ({MODELS[mode]['name']})"

    lines = [
        f"# Pre-fetched Context — {source_label}",
        f"<!-- Generated: {datetime.now().isoformat()} | Mode: {mode.upper()} | Source: {'fallback' if is_fallback else 'qdrant'} -->",
        f"<!-- Project: {project or 'auto'} | Queries: {'; '.join(queries)} -->",
        "",
    ]

    if is_fallback:
        lines.append("> **WARNING: These results are from keyword matching, NOT semantic vector search.**")
        lines.append("> Quality is degraded. Check Qdrant status: `curl -s localhost:6333/collections` or check `~/.qdrant-memory/.lock`")
        lines.append("")

    if not results:
        lines.append("No relevant context found in vector memory.")
        lines.append("Run `~/.claude/scripts/index_memory_to_qdrant.py` to populate.")
    else:
        by_category = {}
        for r in results:
            cat = r["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(r)

        for category, chunks in by_category.items():
            lines.append(f"## {category.title()}")
            lines.append("")
            for chunk in chunks:
                source = chunk["source"]
                score = chunk["score"]
                lines.append(f"**[{source}]** (relevance: {score:.2f})")
                lines.append(chunk["text"])
                lines.append("")

    content = "\n".join(lines)
    output_file.write_text(content, encoding="utf-8")
    print(f"[{mode}] Wrote {len(results)} chunks to {output_file}")


def main():
    project = ""
    queries = []
    mode = "deep" if "--deep" in sys.argv else "fast"

    if "--project" in sys.argv:
        idx = sys.argv.index("--project")
        if idx + 1 < len(sys.argv):
            project = sys.argv[idx + 1]
            if mode == "deep":
                queries = [
                    f"{project} architectural decisions and trade-offs",
                    f"{project} patterns, conventions, and lessons learned",
                    f"cross-project patterns related to {project}",
                    f"security and performance decisions for {project}",
                ]
            else:
                queries = [
                    f"{project} project context and stack",
                    f"{project} decisions and architecture",
                    f"{project} current state and blockers",
                ]

    elif "--query" in sys.argv:
        idx = sys.argv.index("--query")
        if idx + 1 < len(sys.argv):
            queries = [sys.argv[idx + 1]]

    elif "--hook" in sys.argv or "--auto" in sys.argv:
        mode = "fast"  # hooks always use fast model
        project = detect_project_from_cwd()

        # Fallback: if cwd doesn't match a project (e.g. started from ~/),
        # use the last active project from Redis — much better than generic queries
        if not project:
            try:
                import redis as _redis
                _r = _redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
                project = _r.get("claude:active_project") or ""
                if project:
                    print(f"[fast] No cwd match — using last active project from Redis: {project}", file=sys.stderr)
            except Exception:
                pass

        if project:
            queries = [
                f"{project} project context and stack",
                f"{project} decisions and patterns",
                f"feedback and preferences for {project}",
            ]
        else:
            queries = [
                "user preferences and feedback rules",
                "recent project context",
                "important decisions and patterns",
            ]

    else:
        print("Usage: prefetch_context.py --project <name> [--deep] | --query <text> [--deep] | --hook")
        sys.exit(1)

    results = fetch_context(queries, mode=mode, project_filter=project)
    write_context_file(results, project, queries, mode)


if __name__ == "__main__":
    main()
