"""Gate G-port (M2, QD-012), layers 1-2: retrieval and mock judge on GD1's inputs.

Each layer receives exactly GD1's input, so a mismatch points at that layer:

1. Retrieval -- for each of the 40 GD1 Phase 4 candidates (dump of
   `py scripts/dump_gd1_prompts.py --split phase4 --max-total-calls 40`), GD2's
   `bm25_hybrid` in parity mode (GD1 corpus, global pool, GD1's
   `detector_label` + `fault_type` query terms, Phase 4 weights and
   search_k 500) must return the same top-6 doc ids, in order, as GD1. The
   dump itself is checked against GD1's committed Phase 4 audit
   (`retrieved_context_ids`).
2. Judge -- GD2 `LLMJudge(MockBackend)` with Phase 4's decision settings
   (confidence 0.80, require_evidence off) on GD1's alert + contexts must give
   GD1's `final_decision` for the 30 windows GD1 actually judged
   (TRUE_ALERT = route_alert, FALSE_POSITIVE = suppress,
   UNCERTAIN = manual_review).

    py scripts/gport_layers.py   # -> eval/results/gport_layers_phase4.json (committed)

3a. Pipeline on GD1's candidates -- the harness's own gate, budget and
   decision code (eval/harness/runner.py `Gate`, `_decision`) over the 300
   Phase 4 windows in GD1 order, fed GD1's 40 candidates, with GD2 retrieval
   (parity) and GD2 mock judge: the confusion matrix must equal GD1's exactly.
   This isolates everything downstream of the detector.

Layers 3b (full GD2 pipeline, GD2 detector) and 4 (detector) run through the
harness with eval/configs/gd1_phase4_parity.yaml; `--run gd1_phase4_parity_v1`
then explains that run window by window against the GD1 audit (candidate
sets, retrieval on the shared candidates, decisions, detector score agreement).
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from eval.harness.metrics import confusion
from eval.harness.runner import Gate, _decision
from packages.schemas.evidence import load_gd1_corpus, parse_timestamp
from packages.schemas.models import ContextEvent, RetrievalBudget, RetrievalResult
from scripts.check_gd1_parity import gd1_candidate
from services.judge.backends import MockBackend
from services.judge.llm_judge import LLMJudge
from services.retrieval.bm25_hybrid import Bm25HybridRetriever

DUMP = REPO / "data/gd1_parity/phase4_hybrid_bm25_top6.jsonl"
AUDIT = REPO / "legacy/nezha_setup/outputs/phase4_benchmark/audit/hybrid_bm25_top6_audit.jsonl"
CORPUS = REPO / "legacy/nezha_setup/processed/logs.jsonl"
OUT = REPO / "eval/results/gport_layers_phase4.json"
VERDICT_TO_GD1 = {"TRUE_ALERT": "route_alert", "FALSE_POSITIVE": "suppress", "UNCERTAIN": "manual_review"}
# legacy/nezha_setup/config/experiment_phase4_benchmark.yaml `retrieval:`
PHASE4_RETRIEVAL = {
    "time_margin_minutes": 8,
    "search_k": 500,
    "semantic_weight": 0.35,
    "time_weight": 0.25,
    "metadata_weight": 0.25,
    "signal_weight": 0.15,
}


def gd1_events(contexts: list[dict[str, Any]]) -> RetrievalResult:
    """GD1's retrieved contexts as a GD2 RetrievalResult (judge layer input)."""
    events = [
        ContextEvent(
            event_id=c["doc_id"],
            modality="trace" if c["event_type"] == "trace_span" else "log",
            ts=parse_timestamp(c["timestamp"]),
            service=c["service_id"],
            content=c["message"],
            score=float(c["score"]),
            debug={"source": c["source"], "severity": c["severity"], "event_type": c["event_type"]},
        )
        for c in contexts
    ]
    return RetrievalResult(strategy="gd1_contexts", events=events, latency_ms=0.0, token_estimate=0)


def pipeline_on_gd1_candidates(
    rows: list[dict[str, Any]], retriever: Bm25HybridRetriever, judge: LLMJudge, budget: RetrievalBudget
) -> dict[str, Any]:
    """Layer 3a: GD1's 300 windows and 40 candidates through GD2's gate/budget/retrieval/judge."""
    candidates = {row["alert"]["window_id"]: row["alert"] for row in rows}
    audit = [json.loads(line) for line in AUDIT.open(encoding="utf-8")]
    gate = Gate(
        {
            "enabled": True,
            "low_threshold": 0.80,
            "high_threshold": 0.98,
            "high_score_action": "call_llm",
            "max_llm_calls": 30,
            "budget_exhausted_action": "route_alert",
        }
    )
    gd2_rows, gd1_rows, differ = [], [], []
    for record in audit:  # GD1 order = Phase 4 evaluation order
        alert = candidates.get(record["window_id"])
        action, judged = "not_candidate", None
        if alert is not None:
            action = gate.action(float(alert["anomaly_score"]))
            if action == "call_llm":
                candidate = gd1_candidate(alert)
                judged = judge.evaluate(candidate, retriever.retrieve(candidate, budget))
                gate.calls += 1
        decision = _decision(action, gate, judged)
        gd1_alert = record["final_decision"] == "route_alert"
        fault = record["ground_truth"] == "true_alert"
        gd2_rows.append({"label_is_fault": fault, "decision": decision})
        gd1_rows.append({"label_is_fault": fault, "decision": "alert" if gd1_alert else "other"})
        if (decision == "alert") != gd1_alert:
            differ.append(record["window_id"])

    def alert(row: dict[str, Any]) -> bool:
        return bool(row["decision"] == "alert")

    return {"gd1": confusion(gd1_rows, alert), "gd2": confusion(gd2_rows, alert), "windows_differing": differ}


def explain_run(run_id: str, dump_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Layers 3b/4: a GD2 harness run on the mapped Phase 4 windows vs the GD1 audit."""
    mapping = {
        r["gd2_window_id"]: r
        for r in csv.DictReader((REPO / "eval/configs/gd1_phase4_windows.csv").open(encoding="utf-8"))
        if "evaluated" in r["role"].split("+")
    }
    run_dir = REPO / "eval/results" / run_id
    gd2 = {r["window_id"]: r for r in csv.DictReader((run_dir / "per_window.csv").open(encoding="utf-8"))}
    gd2_retrieval = {
        rec["window_id"]: [e["event_id"] for e in rec["events"]]
        for rec in map(json.loads, (run_dir / "retrieval.jsonl").open(encoding="utf-8"))
    }
    audit = {r["window_id"]: r for r in map(json.loads, AUDIT.open(encoding="utf-8"))}
    gd1_contexts = {row["alert"]["window_id"]: [c["doc_id"] for c in row["contexts"]] for row in dump_rows}
    counts: Counter[str] = Counter()
    differing: list[dict[str, Any]] = []
    gd1_scores, gd2_scores = [], []
    for wid, row in gd2.items():
        gd1 = audit[mapping[wid]["gd1_window_id"]]
        gd1_cand, gd2_cand = bool(gd1["is_candidate"]), row["is_candidate"] == "1"
        counts[f"candidates_gd1_{int(gd1_cand)}_gd2_{int(gd2_cand)}"] += 1
        gd1_scores.append(float(gd1["anomaly_score"]))
        gd2_scores.append(float(row["anomaly_score"]))
        if gd1["gate_action"] == "call_llm" and row["gate_action"] == "call_llm":
            counts["judged_by_both"] += 1
            same = gd2_retrieval.get(wid) == gd1_contexts.get(gd1["window_id"])
            counts["judged_by_both_same_top6"] += same
        gd1_alert, gd2_alert = gd1["final_decision"] == "route_alert", row["decision"] == "alert"
        if gd1_alert != gd2_alert:
            differing.append(
                {
                    "gd1_index": int(mapping[wid]["gd1_index"]),
                    "label": gd1["ground_truth"],
                    "gd1": [gd1["gate_action"], gd1["final_decision"], gd1["anomaly_score"]],
                    "gd2": [row["gate_action"], row["decision"], float(row["anomaly_score"])],
                }
            )
    ranks1 = _ranks(gd1_scores)
    ranks2 = _ranks(gd2_scores)
    return {
        "counts": dict(counts),
        "decisions_differing": sorted(differing, key=lambda d: d["gd1_index"]),
        "detector_score_spearman": statistics.correlation(ranks1, ranks2),
        "detector_score_mean": {"gd1": statistics.fmean(gd1_scores), "gd2": statistics.fmean(gd2_scores)},
    }


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", help="also explain this harness run (layers 3b/4)")
    args = parser.parse_args()
    rows = [json.loads(line) for line in DUMP.open(encoding="utf-8") if line.strip()]
    # Keyed by window_id: the committed audit predates GD1's current alert_id scheme.
    audit = {r["window_id"]: r for r in map(json.loads, AUDIT.open(encoding="utf-8")) if r.get("is_candidate")}
    alerts = {row["alert"]["alert_id"]: row["alert"] for row in rows}
    retriever = Bm25HybridRetriever(
        load_gd1_corpus(CORPUS),
        pool="global",
        extra_query_terms=lambda c: [alerts[c.candidate_id]["detector_label"], alerts[c.candidate_id]["fault_type"]],
        **PHASE4_RETRIEVAL,
    )
    judge = LLMJudge(MockBackend(), require_evidence=False, confidence_threshold=0.80)
    budget = RetrievalBudget(top_k=6, max_tokens=10**9, timeout_ms=10**9)

    counts: Counter[str] = Counter()
    mismatches: list[dict[str, Any]] = []
    for row in rows:
        alert_id = row["alert"]["alert_id"]
        gd1 = audit.get(row["alert"]["window_id"])
        gd1_ids = [c["doc_id"] for c in row["contexts"]]
        counts["candidates"] += 1
        counts["dump_matches_audit"] += gd1 is not None and (
            gd1["gate_action"] != "call_llm" or gd1["retrieved_context_ids"] == gd1_ids
        )
        gd2_ids = [e.event_id for e in retriever.retrieve(gd1_candidate(row["alert"]), budget).events]
        same_retrieval = gd2_ids == gd1_ids
        counts["retrieval_top6_equal"] += same_retrieval
        counts["with_context"] += bool(gd1_ids)
        record: dict[str, Any] = {"alert_id": alert_id, "gd1_ids": gd1_ids, "gd2_ids": gd2_ids}
        if gd1 is not None and gd1["gate_action"] == "call_llm":
            counts["judged_by_gd1"] += 1
            verdict = judge.evaluate(gd1_candidate(row["alert"]), gd1_events(row["contexts"])).verdict
            same_verdict = VERDICT_TO_GD1[verdict] == gd1["final_decision"]
            counts["verdict_equal"] += same_verdict
            counts[f"gd1_{gd1['final_decision']}"] += 1
            record.update({"gd1_decision": gd1["final_decision"], "gd2_verdict": verdict})
            if not same_verdict:
                mismatches.append(record)
        if not same_retrieval:
            mismatches.append(record)
    layer_3a = pipeline_on_gd1_candidates(rows, retriever, judge, budget)
    report = {"counts": dict(counts), "mismatches": mismatches, "layer_3a": layer_3a}
    if args.run:
        report["layer_3b"] = explain_run(args.run, rows)
        print("layer 3b:", json.dumps(report["layer_3b"]["counts"]),
              "spearman", round(report["layer_3b"]["detector_score_spearman"], 4))
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["counts"], indent=1), f"\nmismatches: {len(mismatches)} -> {OUT}")
    print("layer 3a:", json.dumps(layer_3a))
    return 0 if not mismatches and not layer_3a["windows_differing"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
