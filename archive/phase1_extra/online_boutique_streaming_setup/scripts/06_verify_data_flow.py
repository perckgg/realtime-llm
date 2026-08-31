from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "sandbox.yaml"
COMPOSE_FILE = ROOT / "compose" / "telemetry-store.yml"


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=check)


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def compose_cmd(service: str, extra: list[str]) -> list[str]:
    return ["docker", "compose", "-f", str(COMPOSE_FILE), "exec", "-T", service, *extra]


def redis_scalar(args: list[str]) -> str:
    result = run(compose_cmd("redis", ["redis-cli", *args]))
    return result.stdout.strip()


def psql_scalar(config: dict[str, Any], sql: str) -> str:
    pg = config["telemetry_store"]["postgres"]
    result = run(compose_cmd("postgres", ["psql", "-U", pg["user"], "-d", pg["database"], "-At", "-c", sql]))
    return result.stdout.strip()


def stream_lengths(config: dict[str, Any]) -> dict[str, int]:
    streams = config["telemetry_store"]["redis"]["streams"]
    output: dict[str, int] = {}
    for label, stream in streams.items():
        output[label] = int(redis_scalar(["XLEN", stream]) or "0")
    return output


def table_counts(config: dict[str, Any]) -> dict[str, int]:
    tables = [
        "fault_events",
        "metric_samples",
        "log_events",
        "trace_spans",
        "context_documents",
        "metric_windows",
        "pipeline_audit",
    ]
    counts: dict[str, int] = {}
    for table in tables:
        counts[table] = int(psql_scalar(config, f"SELECT COUNT(*) FROM {table};") or "0")
    return counts


def print_map(title: str, values: dict[str, int | str]) -> None:
    print(f"\n{title}")
    for key, value in values.items():
        print(f"  {key}: {value}")


def verify_kubernetes(config: dict[str, Any]) -> None:
    namespace = config["kubernetes"]["namespace"]
    run(["kubectl", "-n", namespace, "get", "deploy"], check=True)
    run(["kubectl", "-n", namespace, "get", "pods"], check=True)


def verify_no_future_leakage(config: dict[str, Any]) -> int:
    margin = int(config["retrieval"]["time_margin_minutes"])
    sql = f"""
SELECT COUNT(*)
FROM metric_windows mw
JOIN context_documents cd
  ON cd.service_id = mw.service_id
 AND cd.event_time >= mw.window_start - interval '{margin} minutes'
 AND cd.event_time <= mw.window_end + interval '{margin} minutes'
WHERE cd.ingest_time > mw.watermark_time;
"""
    return int(psql_scalar(config, sql) or "0")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Online Boutique streaming sandbox data flow.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--wait-seconds", type=int, default=0)
    parser.add_argument("--allow-empty", action="store_true")
    parser.add_argument("--skip-k8s", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    failures: list[str] = []

    print("[verify] checking Redis")
    if redis_scalar(["PING"]) != "PONG":
        failures.append("Redis PING failed")

    print("[verify] checking PostgreSQL and pgvector")
    vector_version = psql_scalar(config, "SELECT extversion FROM pg_extension WHERE extname = 'vector';")
    if not vector_version:
        failures.append("pgvector extension is not enabled")

    before = stream_lengths(config)
    print_map("[verify] Redis stream lengths before wait", before)

    if args.wait_seconds > 0:
        print(f"[verify] waiting {args.wait_seconds}s for streaming growth")
        time.sleep(args.wait_seconds)

    after = stream_lengths(config)
    print_map("[verify] Redis stream lengths after wait", after)

    counts = table_counts(config)
    print_map("[verify] PostgreSQL table counts", counts)
    print_map("[verify] versions", {"pgvector": vector_version})

    if args.wait_seconds > 0 and after["metrics"] <= before["metrics"] and not args.allow_empty:
        failures.append("ob:metrics did not grow during wait window")
    if counts["metric_samples"] == 0 and not args.allow_empty:
        failures.append("metric_samples is empty")

    leakage_count = verify_no_future_leakage(config)
    print_map("[verify] streaming validity", {"no_future_leakage_violations": leakage_count})
    if leakage_count != 0:
        failures.append(f"future context leakage violations: {leakage_count}")

    if not args.skip_k8s:
        try:
            verify_kubernetes(config)
        except subprocess.CalledProcessError as exc:
            failures.append(f"Kubernetes verification failed: {exc.stderr.strip() or exc.stdout.strip()}")

    if failures:
        print("\n[verify] failed checks:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print("\n[verify] data flow checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
