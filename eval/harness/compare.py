"""Paired comparison of runs over the same windows (02 SS5.2; H0 in 08 SS4).

    py -m eval compare --runs bm25=h0_val_bm25_v1,c1=h0_val_c1_k0_v1 \
        --detector-only h0_val_bm25_v1 --out h0_val_compare_v1

For each subset (`telemetry` = main result, `all` = secondary, QD-017) and
each method: confusion matrix, P/R/F1/FPR with a 95% bootstrap CI. For each
method against the reference (the first one): the differences dR, dP, dF1,
dFPR with a **paired** 95% bootstrap CI and exact McNemar tests on per-window
correctness -- over all windows, fault windows only (the recall test) and
normal windows only (the FPR test).

The paired bootstrap resamples windows with replacement; a window is one of 8
cells (label, prediction A, prediction B), so a resample is a Multinomial(n,
cell shares) draw over those cells (same trick as `bootstrap_confusion_ci`).

Runs must cover the same windows with the same labels. Output goes to
eval/results/<out>/compare.json, which must not exist yet.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from eval.harness.metrics import scores
from eval.harness.stats import bootstrap_confusion_ci, mcnemar_exact

DETECTOR_ONLY = "detector_only"


@dataclass(frozen=True)
class Method:
    name: str
    run_id: str
    detector_only: bool = False


@dataclass(frozen=True)
class Windows:
    ids: list[str]
    label: np.ndarray  # bool, is fault
    telemetry: np.ndarray  # bool


def parse_methods(runs: str, detector_only: str | None = None) -> list[Method]:
    """`name=run_id,...` (or bare run ids, named after themselves)."""
    methods = []
    for spec in filter(None, (s.strip() for s in runs.split(","))):
        name, _, run_id = spec.partition("=")
        methods.append(Method(name, run_id) if run_id else Method(spec, spec))
    if detector_only:
        methods.append(Method(DETECTOR_ONLY, detector_only, detector_only=True))
    names = [m.name for m in methods]
    if len(set(names)) != len(names):
        raise ValueError(f"duplicate method names: {names}")
    if len(methods) < 2:
        raise ValueError("compare needs at least two methods")
    return methods


def _flag(value: str) -> bool:
    return value not in ("", "0", "False", "false")


def load_predictions(results: Path, method: Method) -> tuple[Windows, np.ndarray]:
    with (results / method.run_id / "per_window.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    ids = [r["window_id"] for r in rows]
    label = np.array([_flag(r["label_is_fault"]) for r in rows])
    telemetry = np.array([_flag(r["has_telemetry"]) for r in rows])
    if method.detector_only:
        predicted = np.array([_flag(r["is_candidate"]) for r in rows])
    else:
        predicted = np.array([r["decision"] == "alert" for r in rows])
    return Windows(ids, label, telemetry), predicted


def _cm(label: np.ndarray, predicted: np.ndarray) -> dict[str, int]:
    return {
        "tp": int(np.sum(label & predicted)),
        "fp": int(np.sum(~label & predicted)),
        "fn": int(np.sum(label & ~predicted)),
        "tn": int(np.sum(~label & ~predicted)),
    }


def _scores_batch(tp: np.ndarray, fp: np.ndarray, fn: np.ndarray, tn: np.ndarray) -> dict[str, np.ndarray]:
    def ratio(num: np.ndarray, den: np.ndarray) -> np.ndarray:
        return np.divide(num, den, out=np.zeros_like(num, dtype=float), where=den > 0)

    precision = ratio(tp, tp + fp)
    recall = ratio(tp, tp + fn)
    return {
        "precision": precision,
        "recall": recall,
        "f1": ratio(2 * precision * recall, precision + recall),
        "fpr": ratio(fp, fp + tn),
    }


def paired_delta_ci(
    label: np.ndarray, pred_a: np.ndarray, pred_b: np.ndarray, n_boot: int, seed: int, alpha: float = 0.05
) -> dict[str, tuple[float, float]]:
    """95% paired bootstrap CI of metric(B) - metric(A) for precision, recall, f1, fpr."""
    n = len(label)
    if n == 0:
        return {}
    cell = label.astype(int) * 4 + pred_a.astype(int) * 2 + pred_b.astype(int)
    counts = np.bincount(cell, minlength=8)
    draws = np.random.default_rng(seed).multinomial(n, counts / n, size=n_boot)  # (n_boot, 8)

    def confusion(pred_bit: int) -> tuple[np.ndarray, ...]:
        is_pred = np.array([(c >> pred_bit) & 1 for c in range(8)], dtype=bool)
        is_fault = np.array([c >= 4 for c in range(8)])
        cells = [(is_fault & is_pred), (~is_fault & is_pred), (is_fault & ~is_pred), (~is_fault & ~is_pred)]
        return tuple(draws[:, mask].sum(axis=1) for mask in cells)

    metrics_a = _scores_batch(*confusion(1))
    metrics_b = _scores_batch(*confusion(0))
    out = {}
    for name in metrics_a:
        delta = metrics_b[name] - metrics_a[name]
        out[name] = (float(np.quantile(delta, alpha / 2)), float(np.quantile(delta, 1 - alpha / 2)))
    return out


def _mcnemar(label: np.ndarray, pred_a: np.ndarray, pred_b: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    right_a = (pred_a == label)[mask]
    right_b = (pred_b == label)[mask]
    return {
        "n": int(mask.sum()),
        "a_right_b_wrong": int(np.sum(right_a & ~right_b)),
        "a_wrong_b_right": int(np.sum(~right_a & right_b)),
        "p_value": mcnemar_exact(right_a.tolist(), right_b.tolist()),
    }


def compare_subset(
    label: np.ndarray, predictions: Mapping[str, np.ndarray], n_boot: int, seed: int
) -> dict[str, Any]:
    names = list(predictions)
    reference = names[0]
    methods: dict[str, Any] = {}
    for name, predicted in predictions.items():
        cm = _cm(label, predicted)
        entry: dict[str, Any] = {**cm, **scores(cm)}
        for metric, (lo, hi) in bootstrap_confusion_ci(cm, scores, n_boot, seed).items():
            entry[f"{metric}_ci95"] = [lo, hi]
        methods[name] = entry
    pairs: dict[str, Any] = {}
    every = np.ones(len(label), dtype=bool)
    for name in names[1:]:
        a, b = predictions[reference], predictions[name]
        delta = {m: methods[name][m] - methods[reference][m] for m in ("precision", "recall", "f1", "fpr")}
        ci = paired_delta_ci(label, a, b, n_boot, seed)
        pairs[f"{name} - {reference}"] = {
            **{f"d_{m}": v for m, v in delta.items()},
            **{f"d_{m}_ci95": list(v) for m, v in ci.items()},
            "mcnemar_all": _mcnemar(label, a, b, every),
            "mcnemar_fault": _mcnemar(label, a, b, label),
            "mcnemar_normal": _mcnemar(label, a, b, ~label),
        }
    return {"windows": len(label), "fault_windows": int(label.sum()), "reference": reference,
            "methods": methods, "pairs": pairs}


def compare(
    methods: Sequence[Method], results: Path, n_boot: int = 1000, seed: int = 42
) -> dict[str, Any]:
    loaded = [(m, *load_predictions(results, m)) for m in methods]
    base = loaded[0][1]
    for method, windows, _ in loaded[1:]:
        if windows.ids != base.ids or not np.array_equal(windows.label, base.label) or not np.array_equal(
            windows.telemetry, base.telemetry
        ):
            raise ValueError(f"{method.run_id} does not cover the same windows/labels as {loaded[0][0].run_id}")
    subsets = {"telemetry": base.telemetry, "all": np.ones(len(base.ids), dtype=bool)}
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "methods": [{"name": m.name, "run_id": m.run_id, "detector_only": m.detector_only} for m in methods],
        "n_boot": n_boot,
        "seed": seed,
        **{
            name: compare_subset(base.label[mask], {m.name: pred[mask] for m, _, pred in loaded}, n_boot, seed)
            for name, mask in subsets.items()
        },
    }


def write(report: dict[str, Any], out_dir: Path) -> Path:
    if out_dir.exists():
        raise SystemExit(f"{out_dir} already exists: results are never overwritten, use a new name")
    out_dir.mkdir(parents=True)
    path = out_dir / "compare.json"
    path.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    return path


def table(report: Mapping[str, Any], subset: str = "telemetry") -> str:
    block = report[subset]
    lines = [f"[{subset}] windows={block['windows']} faults={block['fault_windows']}",
             f"{'method':16s} {'TP':>5s} {'FP':>6s} {'P':>7s} {'R':>7s} {'F1':>7s} {'FPR':>7s}"]
    for name, m in block["methods"].items():
        lines.append(f"{name:16s} {m['tp']:5d} {m['fp']:6d} {m['precision']:7.4f} {m['recall']:7.4f} "
                     f"{m['f1']:7.4f} {m['fpr']:7.4f}")
    for pair, d in block["pairs"].items():
        lines.append(
            f"{pair}: dR={d['d_recall']:+.4f} {_fmt(d.get('d_recall_ci95'))} "
            f"dFPR={d['d_fpr']:+.4f} {_fmt(d.get('d_fpr_ci95'))} "
            f"McNemar p(all/fault/normal)={d['mcnemar_all']['p_value']:.3g}/"
            f"{d['mcnemar_fault']['p_value']:.3g}/{d['mcnemar_normal']['p_value']:.3g}"
        )
    return "\n".join(lines)


def _fmt(ci: Sequence[float] | None) -> str:
    return f"[{ci[0]:+.4f}; {ci[1]:+.4f}]" if ci else ""
