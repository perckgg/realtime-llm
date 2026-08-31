#!/usr/bin/env bash
# Fetch the Nezha dataset into data/Nezha/.
#
# The dataset is not committed (.gitignore excludes data/*), so anyone
# reproducing the thesis results runs this first. Everything downstream —
# scripts/verify_labels.py, scripts/make_splits.py, the whole Phase 2 pipeline —
# reads from the directory this creates.
#
# Source: Yu et al., "Nezha: Interpretable Fine-Grained Root Causes Analysis for
# Microservices on Multi-modal Observability", FSE 2023.
# Artifact: https://github.com/IntelligentDDS/Nezha
#
# Usage:
#   bash scripts/download_nezha.sh            # clone into data/Nezha
#   NEZHA_DATA_DIR=/other/path bash scripts/download_nezha.sh

set -euo pipefail

REPO_URL="https://github.com/IntelligentDDS/Nezha.git"
# Pin the commit once the thesis numbers are final, so a later upstream change
# cannot silently move the ground truth. Leave empty to track the default branch.
PINNED_COMMIT="${NEZHA_COMMIT:-}"

TARGET="${NEZHA_DATA_DIR:-./data/Nezha}"

if [ -d "$TARGET/rca_data" ]; then
  echo "Nezha already present at $TARGET — nothing to do."
  echo "Delete the directory first if you want a clean re-download."
  exit 0
fi

echo "Cloning $REPO_URL into $TARGET ..."
mkdir -p "$(dirname "$TARGET")"
git clone --depth 1 "$REPO_URL" "$TARGET"

if [ -n "$PINNED_COMMIT" ]; then
  echo "Checking out pinned commit $PINNED_COMMIT ..."
  git -C "$TARGET" fetch --depth 1 origin "$PINNED_COMMIT"
  git -C "$TARGET" checkout "$PINNED_COMMIT"
fi

echo
echo "Recording the exact revision for the thesis appendix:"
git -C "$TARGET" rev-parse HEAD

cat <<'NOTE'

The clone keeps its own .git directory. That is deliberate: it records which
upstream revision the results came from. It is invisible to this repository
because data/ is gitignored.

Expected layout:
  data/Nezha/rca_data/<YYYY-MM-DD>/<YYYY-MM-DD>-fault_list.json   ground truth
  data/Nezha/rca_data/<YYYY-MM-DD>/{metric,log,trace,traceid}/    fault period
  data/Nezha/construct_data/root_cause_{hipster,ts}.json          service lists

Next step:
  python scripts/verify_labels.py     # writes docs/label-audit.md
  python scripts/make_splits.py       # writes data/splits/{dev,val,test}.json
NOTE
