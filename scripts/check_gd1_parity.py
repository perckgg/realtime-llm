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

This is the BM25 half of M3's G-paper gate run early (M1, QD-016).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from packages.schemas.evidence import load_gd1_corpus, parse_timestamp
from packages.schemas.models import AlertCandidate, RetrievalBudget
from services.judge.backends import GeminiBackend
from services.judge.cache import ResponseCache
from services.judge.llm_judge import LLMJudge
from services.judge.prompt import alert_payload, compose_prompt, context_payload
from services.retrieval.bm25_hybrid import Bm25HybridRetriever

GD1_CORPUS = REPO / "legacy/nezha_setup/processed/logs.jsonl"
GD1_CACHE = REPO / "legacy/outputs/phase2/step7_rerun/quality_full_budget/cache/paper_500/hybrid_bm25_top6.jsonl"
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dump", type=Path, default=DUMP)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--out", type=Path, default=REPO / "data/gd1_parity/parity_report.json")
    args = parser.parse_args()

    rows = [json.loads(line) for line in args.dump.open(encoding="utf-8") if line.strip()]
    if args.limit:
        rows = rows[: args.limit]
    gd1_alerts = {row["alert"]["alert_id"]: row["alert"] for row in rows}
    retriever = Bm25HybridRetriever(
        load_gd1_corpus(GD1_CORPUS),
        pool="global",
        extra_query_terms=lambda c: [gd1_alerts[c.candidate_id]["detector_label"], gd1_alerts[c.candidate_id]["fault_type"]],
    )
    backend = GeminiBackend(ResponseCache(None, [GD1_CACHE]), api_key="offline-parity-check")
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
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"rows": len(rows), **report["counts"], "mismatches": len(mismatches)}, indent=1))
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
