#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
CONFIG="${ROOT_DIR}/config/sandbox.yaml"
KIND_CONFIG="${ROOT_DIR}/kind/kind-config.yaml"

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
NAMESPACE="$(read_yaml kubernetes.namespace)"

if kind get clusters 2>/dev/null | grep -qx "$CLUSTER_NAME"; then
  echo "[kind] cluster already exists: ${CLUSTER_NAME}"
else
  echo "[kind] creating cluster: ${CLUSTER_NAME}"
  kind create cluster --name "$CLUSTER_NAME" --config "$KIND_CONFIG" --wait 120s
fi

kubectl cluster-info --context "kind-${CLUSTER_NAME}"
kubectl apply -f "${ROOT_DIR}/k8s/namespace.yaml"
kubectl label namespace "$NAMESPACE" purpose=true-streaming-sandbox --overwrite

echo "[kind] cluster ready: ${CLUSTER_NAME}"
