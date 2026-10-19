"""Run one experiment config end to end (01 SS6.8, 02 SS3).

    py -m eval run --config eval/configs/<name>.yaml

Replays Nezha in time order through detector -> gate -> retrieval -> judge
and writes the six files of 02 SS3.3 (plus `judged.jsonl`) to
eval/results/<run_id>/, which must not exist yet (results are never
overwritten; a new parameter set = a new run_id). Optionally writes the same
rows to ClickHouse (`storage.clickhouse: true`, 03 SS3).

Config sections (see eval/configs/*.yaml for full examples):

- `run_id`, `seed`, `time_source` (wall | epoch), `n_windows` (optional cap)
- evaluated windows: `split` (dev | val | test) **or** `window_set`
  ({path, role, labels: gd1 | dataset}) -- the latter for GD1 parity
- `detector`: IsolationForestDetector arguments + `fit`
  ({strategy: split, split: dev} | {strategy: window_set, path, role})
- `gate` (optional, GD1's LLM gate): low/high thresholds, high_score_action,
  max_llm_calls, budget_exhausted_action
- `evidence`: {store: nezha} | {store: gd1_corpus, path} (parity only)
- `retrieval`: services/retrieval/registry.py block; `parity_query_terms: true`
  puts GD1's detector_label + fault_type back into the BM25 query -- this
  reads the label and exists **only** to reproduce GD1 (QD-016)
- `judge`: services/judge/registry.py block
- `storage`: {clickhouse: false}
- `stages`: `full` (default) | `detector` -- detector only, no retrieval or
  judge (counting candidates / cost estimates); `retrieval` and `judge` may
  then be omitted
"""

from __future__ import annotations

import csv
import json
import subprocess
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from eval.harness.metrics import summarize
from packages.schemas.evidence import InMemoryEvidenceStore, NezhaEvidenceStore, load_gd1_corpus
from packages.schemas.loaders import load_split_window_ids
from packages.schemas.models import AlertCandidate, JudgedAlert, RetrievalResult, TelemetryWindow
from services.detector.candidates import build_alert_candidate
from services.detector.isolation_forest import IsolationForestDetector
from services.judge.registry import build_judge
from services.replayer.nezha_source import NezhaReplaySource
from services.retrieval.bm25_hybrid import Bm25HybridRetriever
from services.retrieval.registry import build_budget, build_strategy

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "eval" / "results"

PER_WINDOW_FIELDS = [
    "window_id", "service", "pod", "window_ts", "label_is_fault", "label_fault_type",
    "label_root_cause", "has_telemetry", "anomaly_score", "is_candidate", "top_features",
    "gate_action", "retrieved", "context_events", "context_tokens", "retrieval_latency_ms",
    "judged", "verdict", "raw_verdict", "confidence", "evidence_events", "evidence_origin",
    "downgraded_by_evidence_rule", "judge_status", "cache_hit", "actual_api_call",
    "llm_latency_ms", "prompt_tokens", "completion_tokens", "decision",
]  # fmt: skip


@dataclass(frozen=True)
class Label:
    is_fault: bool
    fault_type: str
    root_cause: str


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    required = ["run_id", "detector"]
    if config.get("stages", "full") == "full":
        required += ["retrieval", "judge"]
    for key in required:
        if key not in config:
            raise ValueError(f"{path}: missing `{key}`")
    if ("split" in config) == ("window_set" in config):
        raise ValueError(f"{path}: give exactly one of `split` or `window_set`")
    return config


def _window_set(spec: dict[str, Any]) -> tuple[list[str], dict[str, Label]]:
    """Window ids (file order) whose `role` contains spec["role"], and GD1 labels if asked."""
    path = REPO / spec["path"]
    with path.open(encoding="utf-8", newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if spec["role"] in r["role"].split("+")]
    labels: dict[str, Label] = {}
    if spec.get("labels") == "gd1":
        for r in rows:
            fault = r["gd1_label"] == "true_alert"
            labels[r["gd2_window_id"]] = Label(fault, r["gd1_fault_type"] if fault else "none", "")
    return [r["gd2_window_id"] for r in rows], labels


def _evaluated(config: dict[str, Any]) -> tuple[set[str], dict[str, Label]]:
    if "split" in config:
        return load_split_window_ids(config["split"]), {}
    ids, labels = _window_set(config["window_set"])
    return set(ids), labels


def _train_ids(fit: dict[str, Any]) -> set[str]:
    if fit.get("strategy", "split") == "split":
        return load_split_window_ids(fit.get("split", "dev"))
    if fit["strategy"] == "window_set":
        return set(_window_set(fit)[0])
    raise ValueError(f"unknown detector.fit.strategy {fit['strategy']!r}")


def _detector(config: dict[str, Any]) -> tuple[IsolationForestDetector, dict[str, Any]]:
    params = {k: v for k, v in config["detector"].items() if k not in {"type", "fit"}}
    params.setdefault("random_state", config.get("seed", 42))
    return IsolationForestDetector(**params), dict(config["detector"].get("fit") or {})


def _evidence(config: dict[str, Any], nezha: NezhaEvidenceStore) -> NezhaEvidenceStore | InMemoryEvidenceStore:
    spec = config.get("evidence") or {"store": "nezha"}
    if spec["store"] == "nezha":
        return nezha
    if spec["store"] == "gd1_corpus":
        return load_gd1_corpus(REPO / spec["path"])
    raise ValueError(f"unknown evidence.store {spec['store']!r}")


def _git_commit() -> str:
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True)
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True, check=False)
        return sha.stdout.strip() + (" (dirty working tree)" if dirty.stdout.strip() else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


class Gate:
    """GD1's LLM gate (legacy/src/decision/policy.py `gate_alert`) + call budget.
    Disabled by default: every candidate goes to the judge, no budget."""

    def __init__(self, spec: dict[str, Any] | None) -> None:
        spec = spec or {}
        self.enabled = bool(spec.get("enabled", False))
        self.low = float(spec.get("low_threshold", 0.0))
        self.high = float(spec.get("high_threshold", 1.0))
        self.high_action = str(spec.get("high_score_action", "call_llm"))
        self.max_calls = spec.get("max_llm_calls")
        self.exhausted_action = str(spec.get("budget_exhausted_action", "manual_review"))
        self.calls = 0

    def action(self, score: float) -> str:
        if self.max_calls is not None and self.calls >= int(self.max_calls):
            return "llm_budget_exhausted"
        if self.enabled:
            if score < self.low:
                return "ignore"
            if score >= self.high and self.high_action == "direct_alert":
                return "direct_alert"
        return "call_llm"


def _decision(gate_action: str, gate: Gate, judged: JudgedAlert | None) -> str:
    if judged is not None:
        return {"TRUE_ALERT": "alert", "FALSE_POSITIVE": "suppress"}.get(judged.verdict, "manual_review")
    if gate_action == "direct_alert":
        return "alert"
    if gate_action == "ignore":
        return "suppress"
    if gate_action == "llm_budget_exhausted":
        return {"route_alert": "alert", "suppress": "suppress"}.get(gate.exhausted_action, "manual_review")
    return "none"


def run(config: dict[str, Any], results_root: Path = RESULTS) -> Path:
    run_id = str(config["run_id"])
    out_dir = results_root / run_id
    if out_dir.exists():
        raise SystemExit(f"{out_dir} already exists: results are never overwritten, use a new run_id")
    use_clickhouse = bool((config.get("storage") or {}).get("clickhouse", False))
    if use_clickhouse:
        from packages.storage.clickhouse import run_exists

        if run_exists(run_id):
            raise SystemExit(f"run_id {run_id!r} already has rows in ClickHouse")

    started = time.perf_counter()
    time_source = config.get("time_source", "wall")
    evaluated, label_override = _evaluated(config)
    detector, fit = _detector(config)
    train_ids = _train_ids(fit)
    detector.fit(
        NezhaReplaySource(window_ids=train_ids, include_history=True, time_source=time_source).stream(),
        train_ids=train_ids,
    )
    fit_seconds = time.perf_counter() - started

    nezha = NezhaEvidenceStore()
    full = config.get("stages", "full") == "full"
    retrieval_config = dict(config.get("retrieval") or {"type": "none"})
    parity_terms = bool(retrieval_config.pop("parity_query_terms", False))
    query_terms: dict[str, list[str]] = {}
    if full:
        strategy = build_strategy(retrieval_config, _evidence(config, nezha))
        if parity_terms:
            if not isinstance(strategy, Bm25HybridRetriever):
                raise ValueError("parity_query_terms only applies to bm25_hybrid")
            strategy.extra_query_terms = lambda c: query_terms[c.candidate_id]
        budget = build_budget(retrieval_config)
        judge = build_judge(config["judge"])
    gate = Gate(config.get("gate"))
    threshold = detector.threshold

    rows: list[dict[str, Any]] = []
    out_dir.mkdir(parents=True)
    replay = NezhaReplaySource(
        window_ids=evaluated, include_history=True, time_source=time_source, limit=config.get("n_windows")
    )
    with (out_dir / "retrieval.jsonl").open("w", encoding="utf-8") as retrieval_out, (
        out_dir / "judged.jsonl"
    ).open("w", encoding="utf-8") as judged_out:
        for window in replay.stream():
            if not replay.is_evaluated(window):
                detector.observe(window)
                continue
            label = label_override.get(window.window_id) or _dataset_label(window)
            score = detector.score(window)
            promoted = detector.is_candidate(window, score)
            candidate = build_alert_candidate(window, score, promoted, detector.top_features(window))
            row = _row(window, label, score, candidate, nezha)
            judged: JudgedAlert | None = None
            gate_action = "not_candidate"
            if candidate is not None and not full:
                gate_action = "detector_only"
            elif candidate is not None:
                gate_action = gate.action(score)
                if gate_action == "call_llm":
                    query_terms[candidate.candidate_id] = [
                        "anomaly" if score >= threshold else "normal",
                        label.fault_type if label.is_fault else "none",
                    ]
                    result = strategy.retrieve(candidate, budget)
                    judged = judge.evaluate(candidate, result)
                    gate.calls += 1
                    _fill_judged(row, result, judged)
                    retrieval_out.write(_jsonl({"window_id": window.window_id, **result.model_dump(mode="json")}))
                    judged_out.write(_jsonl(judged.model_dump(mode="json")))
            row["gate_action"] = gate_action
            row["decision"] = _decision(gate_action, gate, judged)
            rows.append(row)

    judge_config = config.get("judge") or {}
    metrics = summarize(
        rows,
        n_boot=int(config.get("n_boot", 1000)),
        seed=int(config.get("seed", 42)),
        price_in=float(judge_config.get("input_cost_per_1m_tokens", 0.10)),
        price_out=float(judge_config.get("output_cost_per_1m_tokens", 0.40)),
    )
    runtime = {
        "run_id": run_id,
        "finished_at": datetime.now(UTC).isoformat(),
        "wall_seconds": round(time.perf_counter() - started, 1),
        "detector_fit_seconds": round(fit_seconds, 1),
        "evaluated_windows": len(rows),
        "llm_calls": metrics["all"]["operations"]["llm_calls"],
        "api_calls": metrics["all"]["operations"]["api_calls"],
        "cache_hit_rate": metrics["all"]["operations"]["cache_hit_rate"],
        "judge_backend": judge.backend.name if full else "none",
    }
    _write_outputs(out_dir, config, rows, metrics, runtime)
    if use_clickhouse:
        _write_clickhouse(run_id, rows, retrieval_config["type"], judge.backend.name if full else "none", out_dir)
    return out_dir


def _dataset_label(window: TelemetryWindow) -> Label:
    lab = window.label
    if lab is None:
        return Label(False, "none", "")
    return Label(lab.is_fault, lab.fault_type or "none", lab.root_cause_service or "")


def _row(
    window: TelemetryWindow, label: Label, score: float, candidate: AlertCandidate | None, nezha: NezhaEvidenceStore
) -> dict[str, Any]:
    row: dict[str, Any] = dict.fromkeys(PER_WINDOW_FIELDS, "")
    row.update(
        {
            "window_id": window.window_id,
            "service": window.service,
            "pod": window.pod or "",
            "window_ts": window.start_ts.isoformat(),
            "label_is_fault": int(label.is_fault),
            "label_fault_type": label.fault_type,
            "label_root_cause": label.root_cause,
            "has_telemetry": int(nezha.has_telemetry(window.start_ts, window.end_ts)),
            "anomaly_score": score,
            "is_candidate": int(candidate is not None),
            "top_features": "|".join(candidate.top_features) if candidate else "",
            "retrieved": 0,
            "judged": 0,
            "context_events": 0,
            "context_tokens": 0,
            "cache_hit": 0,
            "actual_api_call": 0,
            "downgraded_by_evidence_rule": 0,
        }
    )
    return row


def _fill_judged(row: dict[str, Any], result: RetrievalResult, judged: JudgedAlert) -> None:
    row.update(
        {
            "retrieved": 1,
            "context_events": len(result.events),
            "context_tokens": result.token_estimate,
            "retrieval_latency_ms": round(result.latency_ms, 3),
            "judged": 1,
            "verdict": judged.verdict,
            "raw_verdict": judged.raw_verdict,
            "confidence": judged.confidence,
            "evidence_events": len(judged.evidence_event_ids),
            "evidence_origin": judged.evidence_origin,
            "downgraded_by_evidence_rule": int(judged.downgraded_by_evidence_rule),
            "judge_status": judged.debug.get("status", ""),
            "cache_hit": int(judged.cache_hit),
            "actual_api_call": int(bool(judged.debug.get("actual_api_call"))),
            "llm_latency_ms": round(judged.llm_latency_ms, 3),
            "prompt_tokens": judged.debug.get("prompt_tokens") or "",
            "completion_tokens": judged.debug.get("completion_tokens") or "",
        }
    )


def _jsonl(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False, default=str) + "\n"


def _write_outputs(
    out_dir: Path,
    config: dict[str, Any],
    rows: Iterable[dict[str, Any]],
    metrics: dict[str, Any],
    runtime: dict[str, Any],
) -> None:
    with (out_dir / "per_window.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PER_WINDOW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (out_dir / "runtime.json").write_text(json.dumps(runtime, indent=2), encoding="utf-8")
    (out_dir / "config.snapshot.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    (out_dir / "git_commit.txt").write_text(_git_commit() + "\n", encoding="utf-8")


def _write_clickhouse(run_id: str, rows: list[dict[str, Any]], strategy: str, backend: str, out_dir: Path) -> None:
    from packages.storage.clickhouse import insert_alert_evaluations, insert_retrieval_trace

    evaluations = []
    for r in rows:
        judged = bool(r["judged"])
        evaluations.append(
            {
                "run_id": run_id,
                "window_id": r["window_id"],
                "service": r["service"],
                "window_ts": datetime.fromisoformat(r["window_ts"]),
                "anomaly_score": float(r["anomaly_score"]),
                "candidate_source": "metric" if r["is_candidate"] else "none",
                "rescue_score": None,
                "rescue_lambda_log": None,
                "rescue_phi_topo": None,
                "rescue_delta_time": None,
                "retrieval_strategy": strategy if r["retrieved"] else "",
                "retrieval_latency_ms": float(r["retrieval_latency_ms"] or 0.0),
                "context_event_count": int(r["context_events"]),
                "context_tokens": int(r["context_tokens"]),
                "retrieval_truncated": 0,
                "verdict": r["verdict"] if judged else ("TRUE_ALERT" if r["decision"] == "alert" else "NONE"),
                "raw_verdict": r["raw_verdict"] if judged else "",
                "routing_tier": 1 if judged else 0,
                "evidence_origin": r["evidence_origin"] if judged else "none",
                "threshold_applied": None,
                "confidence": float(r["confidence"]) if judged else None,
                "judge_backend": backend if judged else "none",
                "llm_latency_ms": float(r["llm_latency_ms"]) if judged else None,
                "cache_hit": int(r["cache_hit"]),
                "downgraded": int(r["downgraded_by_evidence_rule"]),
                "downgraded_gating": 0,
                "downgraded_anchoring": 0,
                "label_is_fault": int(r["label_is_fault"]),
                "label_fault_type": r["label_fault_type"],
                "label_root_cause": r["label_root_cause"],
            }
        )
    insert_alert_evaluations(evaluations)
    traces = []
    with (out_dir / "retrieval.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            for event in record["events"]:
                traces.append(
                    {
                        "run_id": run_id,
                        "window_id": record["window_id"],
                        "event_id": event["event_id"],
                        "modality": event["modality"],
                        "service": event["service"],
                        "event_ts": datetime.fromisoformat(event["ts"]),
                        "score": float(event["score"]),
                        "rank": int(event["debug"].get("rank", 0)),
                        "origin": event["origin"],
                        "graph_distance": event["graph_distance"],
                        "debug_json": json.dumps(event["debug"], default=str),
                    }
                )
    insert_retrieval_trace(traces)

