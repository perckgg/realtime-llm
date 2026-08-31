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
MONITORING_NS="$(read_yaml kubernetes.monitoring_namespace)"
CHAOS_NS="$(read_yaml kubernetes.chaos_namespace)"

HOST_IP="${TELEMETRY_HOST_IP:-}"
if [[ -z "$HOST_IP" ]]; then
  HOST_IP="$(docker network inspect kind -f '{{(index .IPAM.Config 0).Gateway}}' 2>/dev/null || true)"
fi
if [[ -z "$HOST_IP" ]]; then
  HOST_IP="$(docker network inspect bridge -f '{{(index .IPAM.Config 0).Gateway}}' 2>/dev/null || true)"
fi
if [[ -z "$HOST_IP" ]]; then
  echo "could not determine Docker host gateway; set TELEMETRY_HOST_IP manually" >&2
  exit 1
fi

echo "[collectors] exposing host telemetry store to cluster via endpoint ${HOST_IP}"
kubectl -n "$NAMESPACE" apply -f - <<YAML
apiVersion: v1
kind: Service
metadata:
  name: telemetry-store-host
spec:
  ports:
    - name: redis
      port: 6379
      targetPort: 6379
    - name: postgres
      port: 5432
      targetPort: 5432
---
apiVersion: v1
kind: Endpoints
metadata:
  name: telemetry-store-host
subsets:
  - addresses:
      - ip: ${HOST_IP}
    ports:
      - name: redis
        port: 6379
      - name: postgres
        port: 5432
YAML

echo "[collectors] deploying telemetry bridge"
kubectl apply -f "${ROOT_DIR}/k8s/telemetry-bridge.yaml"
kubectl -n "$NAMESPACE" rollout status deployment/telemetry-bridge --timeout=5m

echo "[collectors] adding Helm repositories"
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null 2>&1 || true
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts >/dev/null 2>&1 || true
helm repo add chaos-mesh https://charts.chaos-mesh.org >/dev/null 2>&1 || true
helm repo update

echo "[collectors] installing Prometheus stack"
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace "$MONITORING_NS" \
  --create-namespace \
  -f "${ROOT_DIR}/config/prometheus-values.yaml"

echo "[collectors] installing OpenTelemetry Collector"
helm upgrade --install otel-collector open-telemetry/opentelemetry-collector \
  --namespace "$MONITORING_NS" \
  --create-namespace \
  -f "${ROOT_DIR}/config/otel-collector.yaml"

echo "[collectors] installing Chaos Mesh"
helm upgrade --install chaos-mesh chaos-mesh/chaos-mesh \
  --namespace "$CHAOS_NS" \
  --create-namespace \
  --set chaosDaemon.runtime=containerd \
  --set chaosDaemon.socketPath=/run/containerd/containerd.sock \
  --set dashboard.securityMode=false

kubectl -n "$MONITORING_NS" get pods
kubectl -n "$CHAOS_NS" get pods
echo "[collectors] collectors and fault backend deployed"
