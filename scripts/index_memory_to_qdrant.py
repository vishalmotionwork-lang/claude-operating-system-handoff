#!/usr/bin/env python3
"""
Index all Claude Code memory files into Qdrant for semantic search.
Indexes into BOTH collections (fast + deep) for dual-model retrieval.

Run this OUTSIDE of Claude Code sessions.

Usage:
    uvx --with qdrant-client --with sentence-transformers \
        python3 ~/.claude/scripts/index_memory_to_qdrant.py

Options:
    --force       Recreate collections from scratch
    --dry-run     Show what would be indexed without writing
    --fast-only   Only index the fast (MiniLM) collection
    --deep-only   Only index the deep (BGE-large) collection
"""

import sys
import hashlib
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from models import QDRANT_PATH, MEMORY_BASE, MODELS, clear_stale_qdrant_lock

CHUNK_SIZE = 400
CHUNK_OVERLAP = 50


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by approximate token count."""
    words = text.split()
    words_per_chunk = int(chunk_size * 0.75)
    overlap_words = int(overlap * 0.75)

    if len(words) <= words_per_chunk:
        return [text] if text.strip() else []

    chunks = []
    start = 0
    while start < len(words):
        end = start + words_per_chunk
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap_words
        if start >= len(words):
            break

    return chunks


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and body from markdown."""
    metadata = {}
    body = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1].strip()
            body = parts[2].strip()
            for line in frontmatter.split("\n"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    metadata[key.strip()] = val.strip()

    return metadata, body


def generate_id(text: str, filepath: str) -> str:
    """Generate a deterministic ID for deduplication."""
    return hashlib.md5(f"{filepath}:{text[:100]}".encode()).hexdigest()


def collect_files() -> list[Path]:
    """Collect all markdown files from memory directories."""
    files = []

    for f in MEMORY_BASE.glob("*.md"):
        if f.name != "MEMORY.md":
            files.append(f)

    projects_dir = MEMORY_BASE / "projects"
    if projects_dir.exists():
        for f in projects_dir.rglob("*.md"):
            files.append(f)

    for subdir in ["sources", "templates"]:
        sub = MEMORY_BASE / subdir
        if sub.exists():
            for f in sub.rglob("*.md"):
                files.append(f)

    return files


def prepare_chunks(files: list[Path]) -> list[dict]:
    """Parse files into chunks with metadata (model-agnostic)."""
    all_chunks = []

    for filepath in files:
        try:
            text = filepath.read_text(encoding="utf-8")
        except Exception as e:
            print(f"  [skip] {filepath.name}: {e}")
            continue

        if not text.strip():
            continue

        metadata, body = parse_frontmatter(text)
        rel_path = str(filepath.relative_to(MEMORY_BASE))

        if rel_path.startswith("projects/"):
            parts = rel_path.split("/")
            project_name = parts[1] if len(parts) > 1 else "unknown"
            doc_type = parts[-1].replace(".md", "").lower()
            category = "project"
        elif "feedback" in filepath.name:
            project_name = "global"
            doc_type = "feedback"
            category = "feedback"
        else:
            project_name = "global"
            doc_type = filepath.stem.lower()
            category = metadata.get("type", "reference")

        chunks = chunk_text(body)
        if not chunks:
            chunks = [body] if body.strip() else []

        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "id": generate_id(chunk, rel_path),
                "text": chunk,
                "source_file": rel_path,
                "project": project_name,
                "doc_type": doc_type,
                "category": category,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "name": metadata.get("name", filepath.stem),
                "description": metadata.get("description", ""),
                "indexed_at": datetime.now().isoformat(),
            })

    return all_chunks


def index_collection(client, model_key: str, chunks: list[dict], force: bool):
    """Index chunks into a single Qdrant collection using the specified model."""
    from qdrant_client.models import Distance, VectorParams, PointStruct
    from sentence_transformers import SentenceTransformer

    config = MODELS[model_key]
    collection = config["collection"]
    model_name = config["name"]

    print(f"\n{'='*60}")
    print(f"[{model_key}] Model: {model_name}")
    print(f"[{model_key}] Collection: {collection} (dim={config['dimensions']})")
    print(f"{'='*60}")

    print(f"[{model_key}] Loading model...")
    model = SentenceTransformer(model_name)
    vector_size = model.get_sentence_embedding_dimension()

    collections = [c.name for c in client.get_collections().collections]
    if collection in collections and force:
        print(f"[{model_key}] Deleting existing collection")
        client.delete_collection(collection)
        collections.remove(collection)

    if collection not in collections:
        print(f"[{model_key}] Creating collection (dim={vector_size})")
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    print(f"[{model_key}] Encoding {len(chunks)} chunks...")
    points = []
    for chunk in chunks:
        embedding = model.encode(chunk["text"]).tolist()
        payload = {k: v for k, v in chunk.items() if k != "id"}
        points.append(PointStruct(
            id=chunk["id"],
            vector=embedding,
            payload=payload,
        ))

    if points:
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            client.upsert(collection_name=collection, points=batch)
            print(f"  [{model_key}] {min(i + batch_size, len(points))}/{len(points)} points")

    # Verify
    test_queries = [
        "HireFlow project stack and decisions",
        "KnowAI business context",
    ]
    for query in test_queries:
        embedding = model.encode(query).tolist()
        results = client.query_points(
            collection_name=collection,
            query=embedding,
            limit=2,
        )
        print(f"  [{model_key}] '{query}'")
        for r in results.points:
            print(f"    {r.score:.3f} | {r.payload.get('source_file', '?')[:40]}")

    print(f"[{model_key}] Done — {len(points)} chunks indexed")
    return len(points)


def main():
    force = "--force" in sys.argv
    dry_run = "--dry-run" in sys.argv
    fast_only = "--fast-only" in sys.argv
    deep_only = "--deep-only" in sys.argv

    from qdrant_client import QdrantClient

    files = collect_files()
    print(f"[scan] Found {len(files)} memory files")

    if dry_run:
        for f in files:
            print(f"  {f.relative_to(MEMORY_BASE)}")
        print(f"\n[dry-run] Would index {len(files)} files. No changes made.")
        return

    chunks = prepare_chunks(files)
    print(f"[chunks] {len(chunks)} chunks prepared from {len(files)} files")

    print(f"[init] Connecting to Qdrant at {QDRANT_PATH}")
    if clear_stale_qdrant_lock():
        print("[init] Cleared stale Qdrant lock")
    client = QdrantClient(path=str(QDRANT_PATH))

    models_to_index = []
    if fast_only:
        models_to_index = ["fast"]
    elif deep_only:
        models_to_index = ["deep"]
    else:
        models_to_index = ["fast", "deep"]

    total = 0
    for model_key in models_to_index:
        total += index_collection(client, model_key, chunks, force)

    client.close()
    print(f"\n[done] Total: {total} points across {len(models_to_index)} collection(s)")
    print("[closed] Qdrant connection released.")


if __name__ == "__main__":
    main()
