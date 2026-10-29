#!/bin/bash
# PreToolUse reminder: use graph tools before Read/Grep/Glob on project code.
# Only fires if a graph exists for the current repo.

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_ROOT" ]; then
  exit 0
fi

if [ -f "$REPO_ROOT/.code-review-graph/graph.db" ]; then
  echo "[crg] Graph available — prefer: get_minimal_context, semantic_search_nodes, query_graph, get_impact_radius, detect_changes over raw file reads."
fi
