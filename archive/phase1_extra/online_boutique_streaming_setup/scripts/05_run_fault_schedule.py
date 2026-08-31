from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "sandbox.yaml"
DEFAULT_SCHEDULE = ROOT / "config" / "fault_schedule.yaml"
COMPOSE_FILE = ROOT / "compose" / "telemetry-store.yml"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: list[str], *, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, input=input_text, text=True, check=check)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def sanitize_name(value: str) -> str:
    clean = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    clean = re.sub(r"-+", "-", clean)
    return clean[:63].strip("-")


def make_fault_id(index: int, fault: dict[str, Any]) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return sanitize_name(f"{index:02d}-{fault['fault_type']}-{fault['target_service']}-{stamp}")


def docker_compose_base() -> list[str]:
    return ["docker", "compose", "-f", str(COMPOSE_FILE)]


def redis_xadd(stream: str, payload: dict[str, Any], maxlen: int) -> None:
    cmd = docker_compose_base() + [
        "exec",
        "-T",
        "redis",
        "redis-cli",
        "XADD",
        stream,
        "MAXLEN",
        "~",
        str(maxlen),
        "*",
    ]
    for key, value in payload.items():
        cmd.extend([key, "" if value is None else str(value)])
    run(cmd)


def sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def upsert_fault_event(config: dict[str, Any], event: dict[str, Any]) -> None:
    pg = config["telemetry_store"]["postgres"]
    selector = json.dumps(event.get("selector", {}), separators=(",", ":"), sort_keys=True)
    metadata = json.dumps(event.get("metadata", {}), separators=(",", ":"), sort_keys=True)
    started_at = event["event_time"] if event["status"] == "running" else event.get("started_at")
    ended_at = event["event_time"] if event["status"] == "completed" else None
    sql = f"""
INSERT INTO fault_events (
    fault_id, fault_type, service_id, namespace, target_kind, pod_id, severity,
    expected_symptom, status, planned_start_at, started_at, ended_at,
    duration_seconds, cooldown_seconds, selector, metadata, updated_at
) VALUES (
    {sql_literal(event['fault_id'])},
    {sql_literal(event['fault_type'])},
    {sql_literal(event['service_id'])},
    {sql_literal(event['namespace'])},
    {sql_literal(event.get('target_kind', 'service'))},
    {sql_literal(event.get('pod_id'))},
    {sql_literal(event.get('severity', 'ERROR'))},
    {sql_literal(event.get('expected_symptom'))},
    {sql_literal(event['status'])},
    {sql_literal(event.get('planned_start_at'))},
    {sql_literal(started_at)},
    {sql_literal(ended_at)},
    {int(event.get('duration_seconds') or 0)},
    {int(event.get('cooldown_seconds') or 0)},
    {sql_literal(selector)}::jsonb,
    {sql_literal(metadata)}::jsonb,
    now()
)
ON CONFLICT (fault_id) DO UPDATE SET
    status = EXCLUDED.status,
    started_at = COALESCE(fault_events.started_at, EXCLUDED.started_at),
    ended_at = COALESCE(EXCLUDED.ended_at, fault_events.ended_at),
    duration_seconds = EXCLUDED.duration_seconds,
    cooldown_seconds = EXCLUDED.cooldown_seconds,
    selector = EXCLUDED.selector,
    metadata = fault_events.metadata || EXCLUDED.metadata,
    updated_at = now();
"""
    cmd = docker_compose_base() + ["exec", "-T", "postgres", "psql", "-U", pg["user"], "-d", pg["database"]]
    run(cmd, input_text=sql)


def record_fault_event(config: dict[str, Any], event: dict[str, Any]) -> None:
    redis_cfg = config["telemetry_store"]["redis"]
    stream = redis_cfg["streams"]["faults"]
    payload = {
        "event_time": event["event_time"],
        "ingest_time": utc_now(),
        "fault_id": event["fault_id"],
        "fault_type": event["fault_type"],
        "service_id": event["service_id"],
        "namespace": event["namespace"],
        "status": event["status"],
        "severity": event.get("severity", "ERROR"),
        "expected_symptom": event.get("expected_symptom", ""),
        "duration_seconds": event.get("duration_seconds", 0),
        "cooldown_seconds": event.get("cooldown_seconds", 0),
        "selector": json.dumps(event.get("selector", {}), separators=(",", ":"), sort_keys=True),
    }
    redis_xadd(stream, payload, int(redis_cfg.get("maxlen", 500000)))
    upsert_fault_event(config, event)


def selector_for(namespace: str, service: str) -> dict[str, Any]:
    return {"namespaces": [namespace], "labelSelectors": {"app": service}}


def build_chaos_manifest(fault_id: str, namespace: str, fault: dict[str, Any], duration_seconds: int) -> dict[str, Any]:
    kind = fault["chaos_kind"]
    service = fault["target_service"]
    spec: dict[str, Any] = {
        "mode": fault.get("mode", "one"),
        "selector": selector_for(namespace, service),
    }
    if kind == "NetworkChaos":
        action = fault.get("action", "delay")
        spec["action"] = action
        spec["direction"] = fault.get("direction", "to")
        spec["duration"] = f"{duration_seconds}s"
        network = fault.get("network", {})
        if action == "delay":
            spec["delay"] = {
                "latency": network.get("latency", "500ms"),
                "jitter": network.get("jitter", "50ms"),
                "correlation": str(network.get("correlation", "25")),
            }
        elif action == "loss":
            spec["loss"] = {
                "loss": str(network.get("loss", "35")),
                "correlation": str(network.get("correlation", "25")),
            }
    elif kind == "StressChaos":
        spec["duration"] = f"{duration_seconds}s"
        stressors: dict[str, Any] = {}
        if "cpu" in fault:
            stressors["cpu"] = {
                "workers": int(fault["cpu"].get("workers", 1)),
                "load": int(fault["cpu"].get("load", 80)),
            }
        if "memory" in fault:
            stressors["memory"] = {
                "workers": int(fault["memory"].get("workers", 1)),
                "size": str(fault["memory"].get("size", "256MB")),
            }
        spec["stressors"] = stressors
    elif kind == "PodChaos":
        spec["action"] = fault.get("action", "pod-kill")
        spec["duration"] = f"{duration_seconds}s"
    else:
        raise ValueError(f"unsupported chaos_kind: {kind}")

    return {
        "apiVersion": "chaos-mesh.org/v1alpha1",
        "kind": kind,
        "metadata": {
            "name": fault_id,
            "namespace": namespace,
            "labels": {
                "managed-by": "online-boutique-streaming-sandbox",
                "fault-type": fault["fault_type"],
            },
        },
        "spec": spec,
    }


def kubectl_apply(manifest: dict[str, Any], dry_run: bool) -> None:
    rendered = yaml.safe_dump(manifest, sort_keys=False)
    if dry_run:
        print(rendered)
        return
    run(["kubectl", "apply", "-f", "-"], input_text=rendered)


def kubectl_delete(kind: str, name: str, namespace: str, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] kubectl -n {namespace} delete {kind} {name} --ignore-not-found=true")
        return
    run(["kubectl", "-n", namespace, "delete", kind, name, "--ignore-not-found=true"], check=False)


def sleep_or_skip(seconds: int, *, no_sleep: bool, reason: str) -> None:
    if seconds <= 0:
        return
    if no_sleep:
        print(f"[schedule] skip sleep {seconds}s for {reason}")
        return
    print(f"[schedule] sleeping {seconds}s for {reason}")
    time.sleep(seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Online Boutique fault schedule and record ground truth.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--schedule", type=Path, default=DEFAULT_SCHEDULE)
    parser.add_argument("--max-faults", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-sleep", action="store_true")
    parser.add_argument("--skip-warmup", action="store_true")
    parser.add_argument("--namespace", default=None)
    args = parser.parse_args()

    config = load_yaml(args.config)
    schedule = load_yaml(args.schedule)
    namespace = args.namespace or schedule["schedule"].get("namespace") or config["kubernetes"]["namespace"]
    warmup_seconds = int(schedule["schedule"].get("warmup_seconds", config["fault_defaults"]["warmup_seconds"]))
    default_duration = int(schedule["schedule"].get("default_duration_seconds", config["fault_defaults"]["duration_seconds"]))
    default_cooldown = int(schedule["schedule"].get("default_cooldown_seconds", config["fault_defaults"]["cooldown_seconds"]))
    faults = list(schedule.get("faults", []))
    if args.max_faults:
        faults = faults[: args.max_faults]

    if not faults:
        print("no faults selected", file=sys.stderr)
        return 1

    if not args.skip_warmup:
        sleep_or_skip(warmup_seconds, no_sleep=args.no_sleep, reason="baseline warmup")

    for index, fault in enumerate(faults, start=1):
        fault_id = make_fault_id(index, fault)
        duration = int(fault.get("duration_seconds", default_duration))
        cooldown = int(fault.get("cooldown_seconds", default_cooldown))
        selector = selector_for(namespace, fault["target_service"])
        manifest = build_chaos_manifest(fault_id, namespace, fault, duration)
        started_at = utc_now()
        event = {
            "event_time": started_at,
            "planned_start_at": started_at,
            "fault_id": fault_id,
            "fault_type": fault["fault_type"],
            "service_id": fault["target_service"],
            "namespace": namespace,
            "target_kind": fault["chaos_kind"],
            "severity": fault.get("severity", "ERROR"),
            "expected_symptom": fault.get("expected_symptom", ""),
            "status": "running",
            "duration_seconds": duration,
            "cooldown_seconds": cooldown,
            "selector": selector,
            "metadata": {"chaos_manifest": manifest},
        }

        print(f"[schedule] starting {fault_id}")
        if not args.dry_run:
            record_fault_event(config, event)
        kubectl_apply(manifest, dry_run=args.dry_run)

        sleep_or_skip(duration, no_sleep=args.no_sleep, reason=f"{fault_id} duration")

        print(f"[schedule] stopping {fault_id}")
        kubectl_delete(fault["chaos_kind"], fault_id, namespace, dry_run=args.dry_run)
        completed_event = {
            **event,
            "event_time": utc_now(),
            "started_at": started_at,
            "status": "completed",
        }
        if not args.dry_run:
            record_fault_event(config, completed_event)

        sleep_or_skip(cooldown, no_sleep=args.no_sleep, reason=f"{fault_id} cooldown")

    print("[schedule] completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
