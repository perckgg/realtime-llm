"""Check GD2's ported BM25 + judge prompt against GD1, candidate by candidate.

Input: the dump of `scripts/dump_gd1_prompts.py` (GD1's alert, top-6 contexts,
prompt and Gemini cache key for every LLM call of a split). For each row, GD2
re-runs retrieval in parity mode (GD1's label-filtered corpus, global pool,
GD1's `detector_label` + `fault_type` query terms), composes the prompt with
services/judge/prompt.py and reports:

- retrieval: top-k doc ids identical to GD1, in order;
- prompt: identical string, hence identical cache key;
- cache: key present in GD1's Gemini cache;
- judge: GD2 LLMJudge verdict from that cached answer.

    py scripts/check_gd1_parity.py [--limit N]

Both variants together are M3's gate G-paper (QD-016 BM25 half, QD-021
topology half): with `--limit 0` the run also recomputes the paper's Table 1
row (full budget) from the cached answers -- positive = TRUE_ALERT; windows the
paper never sent to the LLM count as negatives -- and stores it under
eval/results/gpaper_viewA_paper500.json (committed).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from packages.graph.service_graph import load_gd1_graph
from packages.schemas.evidence import load_gd1_corpus, parse_timestamp
from packages.schemas.models import AlertCandidate, RetrievalBudget
from packages.schemas.protocols import RetrievalStrategy
from services.judge.backends import PAPER_MODEL, GeminiBackend
from services.judge.cache import ResponseCache
from services.judge.llm_judge import LLMJudge
from services.judge.prompt import alert_payload, compose_prompt, context_payload
from services.retrieval.bm25_hybrid import Bm25HybridRetriever
from services.retrieval.hybrid_bm25_graph import HybridBm25GraphRetriever

GD1_CORPUS = REPO / "legacy/nezha_setup/processed/logs.jsonl"
GD1_CACHE_DIR = REPO / "legacy/outputs/phase2/step7_rerun/quality_full_budget/cache/paper_500"
GD1_GRAPH = REPO / "legacy/outputs/phase2/service_graph_directed.json"
GD1_WINDOWS = REPO / "legacy/outputs/phase2/window_index.csv"
TABLE1 = REPO / "eval/results/gpaper_viewA_paper500.json"
PAPER_TABLE1 = {  # paper Table 1, full budget (08 SS2)
    "hybrid_bm25_top6": {"f1": 0.7030, "fp": 7},
    "topology_aware_fusion_top6": {"f1": 0.4759, "fp": 137},
}
VARIANTS = ("hybrid_bm25_top6", "topology_aware_fusion_top6")
DUMP = REPO / "data/gd1_parity/paper_500_hybrid_bm25_top6.jsonl"


def gd1_candidate(alert: dict[str, Any]) -> AlertCandidate:
    return AlertCandidate(
        candidate_id=alert["alert_id"],
        window_id=alert["window_id"],
        service=alert["service_id"],
        pod=alert["node_id"],
        ts=parse_timestamp(alert["time_window"]["start"]),
        end_ts=parse_timestamp(alert["time_window"]["end"]),
        anomaly_score=float(alert["anomaly_score"]),
        source="metric",
        metric_snapshot=alert["metric_snapshot"],
        top_features=alert["top_features"],
    )


def parity_retriever(variant: str, alerts: dict[str, dict[str, Any]]) -> RetrievalStrategy:
    """GD2 retriever in GD1-parity mode for one paper variant (Step 7 View A config)."""
    store = load_gd1_corpus(GD1_CORPUS)

    def terms(c: AlertCandidate) -> list[str]:
        return [alerts[c.candidate_id]["detector_label"], alerts[c.candidate_id]["fault_type"]]

    if variant == "hybrid_bm25_top6":
        return Bm25HybridRetriever(store, pool="global", extra_query_terms=terms)
    # legacy/nezha_setup/config/experiment_phase2_topology_fusion_500w.yaml `retrieval:`
    return HybridBm25GraphRetriever(
        store,
        graph=load_gd1_graph(GD1_GRAPH),
        alpha=0.35,
        beta=0.25,
        gamma=0.40,
        tau_seconds=300,
        bm25_k=60,
        graph_max_distance=2,
        graph_per_service_limit=20,
        time_margin_minutes=8,
        bm25_pool="global",
        extra_query_terms=terms,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", default="hybrid_bm25_top6", choices=VARIANTS)
    parser.add_argument("--dump", type=Path, default=None, help="default data/gd1_parity/paper_500_<variant>.jsonl")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    dump = args.dump or REPO / f"data/gd1_parity/paper_500_{args.variant}.jsonl"
    out = args.out or REPO / f"data/gd1_parity/parity_report_{args.variant}.json"

    rows = [json.loads(line) for line in dump.open(encoding="utf-8") if line.strip()]
    if args.limit:
        rows = rows[: args.limit]
    gd1_alerts = {row["alert"]["alert_id"]: row["alert"] for row in rows}
    retriever = parity_retriever(args.variant, gd1_alerts)
    cache = ResponseCache(None, [GD1_CACHE_DIR / f"{args.variant}.jsonl"])
    backend = GeminiBackend(cache, model=PAPER_MODEL, api_key="offline-parity-check")
    judge = LLMJudge(backend)
    budget = RetrievalBudget(top_k=6, max_tokens=10**9, timeout_ms=10**9)

    counts: Counter[str] = Counter()
    mismatches: list[dict[str, Any]] = []
    for row in rows:
        candidate = gd1_candidate(row["alert"])
        result = retriever.retrieve(candidate, budget)
        gd2_ids = [event.event_id for event in result.events]
        gd1_ids = [context["doc_id"] for context in row["contexts"]]
        prompt = compose_prompt(alert_payload(candidate), [context_payload(e) for e in result.events])
        key = backend.cache_key(prompt)
        checks = {
            "retrieval_ids_equal": gd2_ids == gd1_ids,
            "prompt_equal": prompt == row["prompt"],
            "key_equal": key == row["cache_key"],
            "gd1_cache_hit": backend.cache.get(key) is not None,
        }
        counts.update(name for name, ok in checks.items() if ok)
        judged = judge.evaluate(candidate, result) if checks["gd1_cache_hit"] else None
        if judged is not None:
            counts[f"verdict_{judged.verdict}"] += 1
            counts[f"verdict_{judged.verdict}_{row['alert']['ground_truth']}"] += 1
        if not all(checks.values()):
            mismatches.append({"alert_id": candidate.candidate_id, **checks, "gd1_ids": gd1_ids, "gd2_ids": gd2_ids})
    report = {"rows": len(rows), "counts": dict(sorted(counts.items())), "mismatches": mismatches[:20]}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"rows": len(rows), **report["counts"], "mismatches": len(mismatches)}, indent=1))
    if not args.limit:
        row = table1_row(counts, len(rows), len(mismatches))
        table = json.loads(TABLE1.read_text(encoding="utf-8")) if TABLE1.exists() else {}
        table[args.variant] = row
        TABLE1.write_text(json.dumps(table, indent=2) + "\n", encoding="utf-8")
        print(f"Table 1 ({args.variant}): {row}")
    return 0 if not mismatches else 1


def table1_row(counts: Counter[str], llm_calls: int, mismatches: int) -> dict[str, Any]:
    with GD1_WINDOWS.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    labels = {r["window_id"]: r["ground_truth"] for r in rows if r.get("split") == "paper_500"}
    faults = sum(1 for v in labels.values() if v == "true_alert")
    normals = len(labels) - faults
    tp, fp = counts["verdict_TRUE_ALERT_true_alert"], counts["verdict_TRUE_ALERT_normal"]
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / faults if faults else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "windows": len(labels), "fault_windows": faults, "normal_windows": normals, "llm_calls": llm_calls,
        "gd1_cache_hits": counts["gd1_cache_hit"], "retrieval_top6_equal": counts["retrieval_ids_equal"],
        "prompt_equal": counts["prompt_equal"], "mismatches": mismatches,
        "tp": tp, "fp": fp, "fn": faults - tp, "tn": normals - fp,
        "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4),
        "fpr": round(fp / normals, 4) if normals else 0.0,
    }


if __name__ == "__main__":
    raise SystemExit(main())
