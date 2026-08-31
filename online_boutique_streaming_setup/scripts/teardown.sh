#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
CONFIG="${ROOT_DIR}/config/sandbox.yaml"
COMPOSE_FILE="${ROOT_DIR}/compose/telemetry-store.yml"

read_yaml() {
  python3 - "$CONFIG" "$1" <<'PY'
import sys, yaml
path, key = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as fh:
    data = yaml.safe_load(fh)
node = data
for part in key.split("."):
    node = node[part]
print(node)
PY
}

CLUSTER_NAME="$(read_yaml kubernetes.cluster_name)"
DELETE_VOLUMES=0
if [[ "${1:-}" == "--volumes" ]]; then
  DELETE_VOLUMES=1
fi

if command -v kind >/dev/null 2>&1 && kind get clusters 2>/dev/null | grep -qx "$CLUSTER_NAME"; then
  echo "[teardown] deleting kind cluster: ${CLUSTER_NAME}"
  kind delete cluster --name "$CLUSTER_NAME"
else
  echo "[teardown] kind cluster not found: ${CLUSTER_NAME}"
fi

if [[ "$DELETE_VOLUMES" == "1" ]]; then
  echo "[teardown] stopping telemetry store and deleting volumes"
  docker compose -f "$COMPOSE_FILE" down -v
else
  echo "[teardown] stopping telemetry store but keeping volumes"
  docker compose -f "$COMPOSE_FILE" down
fi
