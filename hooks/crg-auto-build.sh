#!/bin/bash
# Auto-build code-review-graph if repo has no graph yet, otherwise skip.
# Called on SessionStart. The PostToolUse hook handles incremental updates.

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_ROOT" ]; then
  exit 0
fi

GRAPH_DB="$REPO_ROOT/.code-review-graph/graph.db"

if [ ! -f "$GRAPH_DB" ]; then
  echo "[crg] No graph found — building for $(basename "$REPO_ROOT")..."
  python3 -m code_review_graph build --repo "$REPO_ROOT" --skip-flows 2>&1 | tail -1
  echo "[crg] Graph built. Full postprocess will run on first review."
else
  # Quick stats
  python3 -m code_review_graph status --repo "$REPO_ROOT" 2>&1 | head -5
fi
