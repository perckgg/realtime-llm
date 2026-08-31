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

PG_DB="$(read_yaml telemetry_store.postgres.database)"
PG_USER="$(read_yaml telemetry_store.postgres.user)"
GROUP="$(read_yaml telemetry_store.redis.consumer_group)"

echo "[store] starting Redis and PostgreSQL/pgvector"
docker compose -f "$COMPOSE_FILE" up -d

echo "[store] waiting for PostgreSQL"
until docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1; do
  sleep 2
done

echo "[store] waiting for Redis"
until docker compose -f "$COMPOSE_FILE" exec -T redis redis-cli PING >/dev/null 2>&1; do
  sleep 2
done

echo "[store] verifying pgvector"
docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U "$PG_USER" -d "$PG_DB" -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';"

echo "[store] creating Redis streams and consumer groups"
for stream in ob:metrics ob:logs ob:traces ob:faults ob:windows; do
  docker compose -f "$COMPOSE_FILE" exec -T redis redis-cli XGROUP CREATE "$stream" "$GROUP" '$' MKSTREAM >/dev/null 2>&1 || true
done

docker compose -f "$COMPOSE_FILE" ps
echo "[store] telemetry store ready"
