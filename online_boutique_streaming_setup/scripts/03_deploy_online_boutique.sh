#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
CONFIG="${ROOT_DIR}/config/sandbox.yaml"

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

NAMESPACE="$(read_yaml kubernetes.namespace)"
REF="$(read_yaml kubernetes.online_boutique_ref)"
NODE_PORT="$(read_yaml kubernetes.frontend_node_port)"
HOST_PORT="$(read_yaml kubernetes.frontend_host_port)"
MANIFEST_URL="https://raw.githubusercontent.com/GoogleCloudPlatform/microservices-demo/${REF}/release/kubernetes-manifests.yaml"

kubectl apply -f "${ROOT_DIR}/k8s/namespace.yaml"

echo "[online-boutique] deploying ${REF}"
kubectl -n "$NAMESPACE" apply -f "$MANIFEST_URL"

echo "[online-boutique] exposing frontend-external as NodePort ${NODE_PORT}"
kubectl -n "$NAMESPACE" patch svc frontend-external --type merge -p "{\"spec\":{\"type\":\"NodePort\",\"ports\":[{\"name\":\"http\",\"port\":80,\"targetPort\":8080,\"nodePort\":${NODE_PORT}}]}}"

echo "[online-boutique] setting stable load generator rate"
kubectl -n "$NAMESPACE" set env deployment/loadgenerator USERS=20 RATE=2

echo "[online-boutique] waiting for deployments"
kubectl -n "$NAMESPACE" rollout status deployment --all --timeout=15m

kubectl -n "$NAMESPACE" get pods -o wide
echo "[online-boutique] frontend should be reachable at http://localhost:${HOST_PORT}"
