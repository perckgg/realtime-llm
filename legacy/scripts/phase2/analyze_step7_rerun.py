from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REGIMES = ["operational_budget_120", "quality_full_budget"]
VARIANTS = ["hybrid_bm25_top6", "topology_aware_fusion_top6"]
METRICS = ["precision", "recall", "f1", "false_positive_rate", "accuracy"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate paired uncertainty and McNemar analysis for the Step 7 rerun."
    )
    parser.add_argument("--rerun-root", default="outputs\\phase2\\step7_rerun")
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rerun_root = _abs_path(args.rerun_root)
    reports: list[dict[str, Any]] = []
    for regime in REGIMES:
        records_by_variant = {
            variant: _load_records(_result_path(rerun_root, regime, variant))
            for variant in VARIANTS
        }
        bm25_records, topology_records = _align_records(records_by_variant)
        report = _analyze_regime(
            regime,
            bm25_records,
            topology_records,
            bootstrap_samples=args.bootstrap_samples,
            seed=args.seed,
        )
        reports.append(report)

    payload = {
        "bootstrap_samples": args.bootstrap_samples,
        "seed": args.seed,
        "delta_direction": "topology_aware_fusion_top6 minus hybrid_bm25_top6",
        "regimes": reports,
    }
    output_base = rerun_root / "step7_rerun_analysis"
    output_base.with_suffix(".json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _write_csv(output_base.with_suffix(".csv"), reports)
    _write_markdown(output_base.with_suffix(".md"), payload)
    print(json.dumps({"analysis": str(output_base.with_suffix('.json'))}, indent=2))
    return 0


def _result_path(rerun_root: Path, regime: str, variant: str) -> Path:
    mode = f"step7_view_a_{regime}_paper_500_{variant}"
    return rerun_root / regime / "results" / f"{mode}_results.json"


def _load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records")
    if not isinstance(records, list):
        raise RuntimeError(f"Missing records list in {path}")
    return records


def _align_records(
    records_by_variant: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    indexed = {
        variant: {str(record.get("window_id")): record for record in records}
        for variant, records in records_by_variant.items()
    }
    bm25_ids = set(indexed[VARIANTS[0]])
    topology_ids = set(indexed[VARIANTS[1]])
    if bm25_ids != topology_ids:
        raise RuntimeError(
            f"Window mismatch: BM25={len(bm25_ids)}, topology={len(topology_ids)}, "
            f"symmetric_difference={len(bm25_ids ^ topology_ids)}"
        )
    ordered_ids = [str(record.get("window_id")) for record in records_by_variant[VARIANTS[0]]]
    bm25_records = [indexed[VARIANTS[0]][window_id] for window_id in ordered_ids]
    topology_records = [indexed[VARIANTS[1]][window_id] for window_id in ordered_ids]
    for bm25, topology in zip(bm25_records, topology_records):
        if bm25.get("ground_truth") != topology.get("ground_truth"):
            raise RuntimeError(f"Ground truth mismatch for window {bm25.get('window_id')}")
    return bm25_records, topology_records


def _analyze_regime(
    regime: str,
    bm25_records: list[dict[str, Any]],
    topology_records: list[dict[str, Any]],
    bootstrap_samples: int,
    seed: int,
) -> dict[str, Any]:
    bm25_metrics = _metrics(bm25_records)
    topology_metrics = _metrics(topology_records)
    deltas = {
        metric: round(topology_metrics[metric] - bm25_metrics[metric], 6)
        for metric in METRICS
    }
    confidence_intervals = _paired_bootstrap(
        bm25_records,
        topology_records,
        samples=bootstrap_samples,
        seed=seed,
    )
    return {
        "regime": regime,
        "windows": len(bm25_records),
        "bm25": {
            **bm25_metrics,
            **_decision_counts(bm25_records),
        },
        "topology": {
            **topology_metrics,
            **_decision_counts(topology_records),
        },
        "delta": deltas,
        "paired_bootstrap_95ci": confidence_intervals,
        "mcnemar_all_windows": _mcnemar(bm25_records, topology_records),
        "mcnemar_true_alert_windows": _mcnemar(
            bm25_records,
            topology_records,
            truth_filter="true_alert",
        ),
        "mcnemar_normal_windows": _mcnemar(
            bm25_records,
            topology_records,
            truth_filter="normal",
        ),
    }


def _metrics(records: list[dict[str, Any]]) -> dict[str, float]:
    tp = fp = tn = fn = 0
    for record in records:
        truth = record.get("ground_truth") == "true_alert"
        predicted = record.get("final_decision") == "route_alert"
        if truth and predicted:
            tp += 1
        elif not truth and predicted:
            fp += 1
        elif not truth:
            tn += 1
        else:
            fn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    false_positive_rate = fp / (fp + tn) if fp + tn else 0.0
    accuracy = (tp + tn) / len(records) if records else 0.0
    return {
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
        "false_positive_rate": round(false_positive_rate, 6),
        "accuracy": round(accuracy, 6),
    }


def _decision_counts(records: list[dict[str, Any]]) -> dict[str, Any]:
    manual_review_records = [
        record for record in records if record.get("final_decision") == "manual_review"
    ]
    manual_reviews = len(manual_review_records)
    route_alerts = sum(1 for record in records if record.get("final_decision") == "route_alert")
    return {
        "route_alerts": route_alerts,
        "manual_reviews": manual_reviews,
        "manual_review_rate": round(manual_reviews / len(records), 6) if records else 0.0,
        "manual_review_reasons": dict(
            sorted(
                Counter(
                    str(record.get("fallback_status") or record.get("gate_action") or "unknown")
                    for record in manual_review_records
                ).items()
            )
        ),
    }


def _paired_bootstrap(
    bm25_records: list[dict[str, Any]],
    topology_records: list[dict[str, Any]],
    samples: int,
    seed: int,
) -> dict[str, dict[str, float]]:
    if samples <= 0:
        raise ValueError("--bootstrap-samples must be positive")
    rng = random.Random(seed)
    count = len(bm25_records)
    distributions = {metric: [] for metric in METRICS}
    for _ in range(samples):
        indices = [rng.randrange(count) for _ in range(count)]
        bm25_sample = [bm25_records[index] for index in indices]
        topology_sample = [topology_records[index] for index in indices]
        bm25_metrics = _metrics(bm25_sample)
        topology_metrics = _metrics(topology_sample)
        for metric in METRICS:
            distributions[metric].append(topology_metrics[metric] - bm25_metrics[metric])
    return {
        metric: {
            "lower": round(_percentile(values, 0.025), 6),
            "upper": round(_percentile(values, 0.975), 6),
        }
        for metric, values in distributions.items()
    }


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _mcnemar(
    bm25_records: list[dict[str, Any]],
    topology_records: list[dict[str, Any]],
    truth_filter: str | None = None,
) -> dict[str, int | float]:
    bm25_correct_topology_wrong = 0
    bm25_wrong_topology_correct = 0
    windows = 0
    for bm25, topology in zip(bm25_records, topology_records):
        if truth_filter and bm25.get("ground_truth") != truth_filter:
            continue
        windows += 1
        truth = bm25.get("ground_truth") == "true_alert"
        bm25_correct = (bm25.get("final_decision") == "route_alert") == truth
        topology_correct = (topology.get("final_decision") == "route_alert") == truth
        if bm25_correct and not topology_correct:
            bm25_correct_topology_wrong += 1
        elif topology_correct and not bm25_correct:
            bm25_wrong_topology_correct += 1
    discordant = bm25_correct_topology_wrong + bm25_wrong_topology_correct
    p_value = _exact_binomial_two_sided(
        min(bm25_correct_topology_wrong, bm25_wrong_topology_correct),
        discordant,
    )
    return {
        "windows": windows,
        "bm25_correct_topology_wrong": bm25_correct_topology_wrong,
        "bm25_wrong_topology_correct": bm25_wrong_topology_correct,
        "discordant": discordant,
        "exact_p_value": p_value,
    }


def _exact_binomial_two_sided(smaller_count: int, trials: int) -> float:
    if trials == 0:
        return 1.0
    tail = sum(math.comb(trials, index) for index in range(smaller_count + 1)) / (2**trials)
    return min(1.0, 2 * tail)


def _write_csv(path: Path, reports: list[dict[str, Any]]) -> None:
    fieldnames = [
        "regime",
        "windows",
        "bm25_precision",
        "topology_precision",
        "precision_delta",
        "precision_ci_lower",
        "precision_ci_upper",
        "bm25_recall",
        "topology_recall",
        "recall_delta",
        "recall_ci_lower",
        "recall_ci_upper",
        "bm25_f1",
        "topology_f1",
        "f1_delta",
        "f1_ci_lower",
        "f1_ci_upper",
        "bm25_fpr",
        "topology_fpr",
        "fpr_delta",
        "fpr_ci_lower",
        "fpr_ci_upper",
        "bm25_manual_review_rate",
        "topology_manual_review_rate",
        "mcnemar_all_p",
        "mcnemar_alert_p",
        "mcnemar_normal_p",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for report in reports:
            ci = report["paired_bootstrap_95ci"]
            writer.writerow(
                {
                    "regime": report["regime"],
                    "windows": report["windows"],
                    "bm25_precision": report["bm25"]["precision"],
                    "topology_precision": report["topology"]["precision"],
                    "precision_delta": report["delta"]["precision"],
                    "precision_ci_lower": ci["precision"]["lower"],
                    "precision_ci_upper": ci["precision"]["upper"],
                    "bm25_recall": report["bm25"]["recall"],
                    "topology_recall": report["topology"]["recall"],
                    "recall_delta": report["delta"]["recall"],
                    "recall_ci_lower": ci["recall"]["lower"],
                    "recall_ci_upper": ci["recall"]["upper"],
                    "bm25_f1": report["bm25"]["f1"],
                    "topology_f1": report["topology"]["f1"],
                    "f1_delta": report["delta"]["f1"],
                    "f1_ci_lower": ci["f1"]["lower"],
                    "f1_ci_upper": ci["f1"]["upper"],
                    "bm25_fpr": report["bm25"]["false_positive_rate"],
                    "topology_fpr": report["topology"]["false_positive_rate"],
                    "fpr_delta": report["delta"]["false_positive_rate"],
                    "fpr_ci_lower": ci["false_positive_rate"]["lower"],
                    "fpr_ci_upper": ci["false_positive_rate"]["upper"],
                    "bm25_manual_review_rate": report["bm25"]["manual_review_rate"],
                    "topology_manual_review_rate": report["topology"]["manual_review_rate"],
                    "mcnemar_all_p": report["mcnemar_all_windows"]["exact_p_value"],
                    "mcnemar_alert_p": report["mcnemar_true_alert_windows"]["exact_p_value"],
                    "mcnemar_normal_p": report["mcnemar_normal_windows"]["exact_p_value"],
                }
            )


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Step 7 Rerun Paired Analysis",
        "",
        f"- Bootstrap samples: {payload['bootstrap_samples']}",
        f"- Seed: {payload['seed']}",
        f"- Delta direction: {payload['delta_direction']}",
        "",
        "| Regime | BM25 F1 | Topology F1 | Delta F1 [95% CI] | BM25 Recall | Topology Recall | Delta Recall [95% CI] | BM25 FPR | Topology FPR | McNemar all p |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for report in payload["regimes"]:
        ci = report["paired_bootstrap_95ci"]
        lines.append(
            "| {regime} | {bm25_f1:.4f} | {topology_f1:.4f} | {f1_delta:.4f} [{f1_low:.4f}, {f1_high:.4f}] | "
            "{bm25_recall:.4f} | {topology_recall:.4f} | {recall_delta:.4f} [{recall_low:.4f}, {recall_high:.4f}] | "
            "{bm25_fpr:.4f} | {topology_fpr:.4f} | {p:.3g} |".format(
                regime=report["regime"],
                bm25_f1=report["bm25"]["f1"],
                topology_f1=report["topology"]["f1"],
                f1_delta=report["delta"]["f1"],
                f1_low=ci["f1"]["lower"],
                f1_high=ci["f1"]["upper"],
                bm25_recall=report["bm25"]["recall"],
                topology_recall=report["topology"]["recall"],
                recall_delta=report["delta"]["recall"],
                recall_low=ci["recall"]["lower"],
                recall_high=ci["recall"]["upper"],
                bm25_fpr=report["bm25"]["false_positive_rate"],
                topology_fpr=report["topology"]["false_positive_rate"],
                p=report["mcnemar_all_windows"]["exact_p_value"],
            )
        )
    lines.extend(
        [
            "",
            "McNemar uses paired correctness on the same frozen windows. Manual review remains a non-routed end-to-end decision in this analysis; selective metrics are reported separately in the regime reports.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _abs_path(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


if __name__ == "__main__":
    raise SystemExit(main())
