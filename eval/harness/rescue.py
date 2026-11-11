"""Rescue Score (C5) ablation on top of the frozen CTAV (M7, QD-033).

    py -m eval rescue --config eval/configs/m7_rescue_plan_val.yaml   # stage 1: no LLM
    py -m eval rescue --config eval/configs/m7_rescue_val.yaml        # stage 2: replay

Stage 1 (`plan`, no `judged_run`): every (eta1, eta2, eta3, tau) of the grid (02 SS6.1) over
the precomputed components (scripts/build_rescue_features.py); a point is feasible if it adds
at most `max_call_increase` x CTAV's LLM calls (02 SS6.3). Writes the union of the windows the
feasible points rescue (`rescue_windows.csv`), which one runner config judges once on CTAV's
tier (C1 prompt, `rescue.windows`).

Stage 2 (`judged_run` + `anchor_features` given): each point's decisions = CTAV's decisions
(cached tiers, eval/harness/ctav.py) + the rescued windows' C1 answers under the same CTAV
policy (C3). Exact metrics for all points, no LLM call. Rules fixed before the judge run:
- selection: max F1 on the subset among feasible points *and* "off" (no rescue); ties -> fewer
  LLM calls, lower FPR, fewer non-zero eta. "off" selected => C5 dropped.
- reduction (02 SS6.4): the formula keeps exactly the components with eta > 0 at the selected
  point; the best point of each face (eta_k = 0) is reported with its paired dF1 CI.
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
import pandas as pd
import yaml

from eval.harness import ctav
from eval.harness.compare import compare_subset
from packages.schemas.models import JudgedAlert
from services.detector.rescue import COMPONENTS, RescueParams, eta_grid
from services.judge.backends import PRICES_PER_1M
from services.judge.policy import apply_policy


def load_rescue_config(path: Path) -> dict[str, Any]:
    config = _read(path, "rescue", ("run_id", "split", "features", "ctav", "grid", "max_call_increase"))
    if ("judged_run" in config) != ("anchor_features" in config):
        raise ValueError(f"{path}: stage 2 needs both `judged_run` and `anchor_features`")
    return config


def load_features_config(path: Path) -> dict[str, Any]:
    """scripts/build_rescue_features.py's config."""
    return _read(path, "rescue_features", ("run_id", "split", "windows_run", "alerts_run", "window_seconds", "log", "time"))


def _read(path: Path, kind: str, required: Sequence[str]) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        config = dict(yaml.safe_load(handle))
    if config.get("kind") != kind:
        raise ValueError(f"{path}: expected `kind: {kind}`")
    for key in required:
        if key not in config:
            raise ValueError(f"{path}: missing `{key}`")
    if config["split"] == "test" and not config.get("g_test", False):
        # Rule 2 (AGENTS.md): no `test` before M8 and the hypothesis registration of M7.
        raise ValueError(f"{path}: split test is only allowed at M8 (set g_test: true there)")
    return config


def grid_points(grid: Mapping[str, Any]) -> list[RescueParams]:
    return [RescueParams(*eta, tau=float(tau)) for eta in eta_grid(float(grid["eta_step"])) for tau in grid["tau"]]


def point_name(p: RescueParams) -> str:
    return f"eta=({p.eta1:g},{p.eta2:g},{p.eta3:g})|tau={p.tau:g}"


@dataclass
class Base:
    """The frozen CTAV without rescue, over every window of the split (replay order)."""

    replay: ctav.Replay
    variant: ctav.Variant
    outcome: ctav.Outcome
    mask: np.ndarray  # evaluation subset (telemetry)


def load_base(config: Mapping[str, Any], results: Path, repo: Path) -> Base:
    ctav_config = ctav.load_ctav_config(repo / config["ctav"])
    tiers = ctav_config["tiers"]
    replay = ctav.Replay(
        ctav.load_tier_run(results, tiers["local"]),
        ctav.load_tier_run(results, tiers["topology"]),
        ctav.load_facts(results, ctav_config["anchor_features"]),
    )
    variant = ctav.variant_from_config(ctav_config)
    subset = ctav_config.get("subset", "telemetry")
    mask = replay.telemetry if subset == "telemetry" else np.ones(len(replay.ids), dtype=bool)
    return Base(replay, variant, replay.run(variant), mask)


def load_features(results: Path, run_id: str, ids: Sequence[str]) -> pd.DataFrame:
    frame = pd.read_parquet(results / run_id / "rescue_features.parquet")
    if list(frame["window_id"]) != list(ids):
        raise ValueError(f"{run_id} does not cover the CTAV windows in replay order")
    return frame


def rescued_masks(frame: pd.DataFrame, points: Sequence[RescueParams]) -> dict[str, np.ndarray]:
    """Vectorised `is_rescued(y_IF, rescue_score(...), p)` for every grid point."""
    lam, phi, dt = (frame[c].to_numpy(dtype=float) for c in COMPONENTS)
    promoted = frame["is_candidate"].to_numpy(dtype=int) == 1
    return {point_name(p): ~promoted & (p.eta1 * lam + p.eta2 * phi + p.eta3 * dt >= p.tau) for p in points}


def plan(config: Mapping[str, Any], base: Base, frame: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    points = grid_points(config["grid"])
    masks = rescued_masks(frame, points)
    cap = float(config["max_call_increase"]) * base.outcome.llm_calls
    union = np.zeros(len(frame), dtype=bool)
    rows: list[dict[str, Any]] = []
    for p in points:
        r = masks[point_name(p)]
        feasible = int(r.sum()) <= cap
        union |= r & feasible
        rows.append({"name": point_name(p), "eta": [p.eta1, p.eta2, p.eta3], "tau": p.tau,
                     "rescued": int(r.sum()), "rescued_in_subset": int((r & base.mask).sum()), "feasible": feasible})
    report = {
        "ctav_llm_calls": base.outcome.llm_calls,
        "max_added_calls": cap,
        "points": rows,
        "feasible_points": sum(r["feasible"] for r in rows),
        "union_windows": int(union.sum()),
        "union_in_subset": int((union & base.mask).sum()),
    }
    return report, frame.loc[union, ["window_id", *COMPONENTS]]


def _rescued_alerts(
    run: ctav.TierRun, facts: Mapping[tuple[str, str, str], Mapping[str, Any]], variant: ctav.Variant
) -> dict[str, JudgedAlert]:
    """CTAV's tier-2 policy (theta, C3 anchoring) on each rescued window's C1 answer."""
    out = {}
    for window_id, raw in run.judged.items():
        cited = [
            ctav.evidence_fact(facts[(run.run_id, window_id, eid)], variant.baseline, variant.percentile)
            for eid in raw.evidence_event_ids
        ]
        out[window_id] = apply_policy(raw, cited, 2, variant.policy).model_copy(update={"routing_tier": 2})
    return out


def _select(points: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    return max(
        points,
        key=lambda p: (round(p["metrics"]["f1"], 9), -p["cost"]["llm_calls"], -p["metrics"]["fpr"], -p["nonzero_eta"]),
    )


def evaluate(config: Mapping[str, Any], base: Base, frame: pd.DataFrame, results: Path) -> dict[str, Any]:
    n_boot, seed = int(config.get("n_boot", 1000)), int(config.get("seed", 42))
    run = ctav.load_tier_run(results, config["judged_run"])
    alerts = _rescued_alerts(run, ctav.load_facts(results, config["anchor_features"]), base.variant)
    tokens = {r["window_id"]: (int(r["prompt_tokens"] or 0), int(r["completion_tokens"] or 0))
              for r in run.rows if r["window_id"] in alerts}
    ids = np.array(base.replay.ids)
    index = {w: i for i, w in enumerate(ids)}
    alert_rescued = np.zeros(len(ids), dtype=bool)
    for window_id, alert in alerts.items():
        alert_rescued[index[window_id]] = alert.verdict == "TRUE_ALERT"
    judged = np.zeros(len(ids), dtype=bool)
    judged[[index[w] for w in alerts]] = True

    label = base.replay.label[base.mask]
    price_in, price_out = PRICES_PER_1M.get(str(config.get("model", "gemini-2.5-flash")), (0.0, 0.0))
    cap = float(config["max_call_increase"]) * base.outcome.llm_calls
    points = grid_points(config["grid"])
    masks = rescued_masks(frame, points)

    def entry(name: str, rescued: np.ndarray, nonzero: int, extra: Mapping[str, Any]) -> dict[str, Any]:
        if (rescued & ~judged).any():
            raise ValueError(f"{name}: {int((rescued & ~judged).sum())} rescued windows were never judged")
        predicted = base.outcome.predicted | (rescued & alert_rescued)
        p_tok = base.outcome.prompt_tokens + sum(tokens[w][0] for w in ids[rescued])
        c_tok = base.outcome.completion_tokens + sum(tokens[w][1] for w in ids[rescued])
        calls = base.outcome.llm_calls + int(rescued.sum())
        return {
            "name": name,
            **extra,
            "nonzero_eta": nonzero,
            "rescued": int(rescued.sum()),
            "rescued_in_subset": int((rescued & base.mask).sum()),
            "rescued_alerts_in_subset": int((rescued & alert_rescued & base.mask).sum()),
            "feasible": int(rescued.sum()) <= cap,
            "metrics": ctav._metrics(label, predicted[base.mask], n_boot, seed),
            "cost": {"llm_calls": calls, "added_calls": int(rescued.sum()),
                     "estimated_cost_usd": p_tok / 1e6 * price_in + c_tok / 1e6 * price_out},
            "_predicted": predicted[base.mask],
        }

    off = entry("off", np.zeros(len(ids), dtype=bool), 0, {"eta": None, "tau": None})
    rows = [
        entry(point_name(p), masks[point_name(p)], sum(e > 0 for e in (p.eta1, p.eta2, p.eta3)),
              {"eta": [p.eta1, p.eta2, p.eta3], "tau": p.tau})
        for p in points
    ]
    feasible = [r for r in rows if r["feasible"]]
    selected = _select([off, *feasible])
    best_point = _select(feasible) if feasible else off

    faces = {}
    for k, component in enumerate(COMPONENTS):
        face = [r for r in feasible if r["eta"][k] == 0]
        if face:
            faces[f"without_{component}"] = _select(face)
    pair_inputs = {"best": best_point["_predicted"], "off": off["_predicted"],
                   **{k: v["_predicted"] for k, v in faces.items()}}
    face_pairs = compare_subset(label, pair_inputs, n_boot, seed)

    curve_eta = best_point["eta"]
    curve = [
        {"tau": r["tau"], "recall": r["metrics"]["recall"], "f1": r["metrics"]["f1"], "fpr": r["metrics"]["fpr"],
         "llm_calls": r["cost"]["llm_calls"], "rescued": r["rescued"]}
        for r in rows if r["eta"] == curve_eta
    ]

    def public(r: Mapping[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in r.items() if not k.startswith("_")}

    baselines: dict[str, np.ndarray] = {"ctav": off["_predicted"], "ctav_rescue": selected["_predicted"]}
    if best_point is not selected:
        baselines["ctav_rescue_best_point"] = best_point["_predicted"]
    for name, run_id in (config.get("baselines") or {}).items():
        baselines[name] = ctav.raw_run_predictions(ctav.load_tier_run(results, run_id))[base.mask]

    kept = [] if selected is off else [c for c, e in zip(COMPONENTS, selected["eta"], strict=True) if e > 0]
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "config": dict(config),
        "windows": int(base.mask.sum()),
        "fault_windows": int(label.sum()),
        "ctav_variant": ctav._describe(base.variant),
        "judged_rescue_windows": len(alerts),
        "judged_rescue_alerts": int(alert_rescued.sum()),
        "max_added_calls": cap,
        "off": public(off),
        "points": [public(r) for r in rows],
        "selected": public(selected),
        "best_point": public(best_point),
        "c5_kept": selected is not off,
        "formula_components": kept,
        "faces": {k: public(v) for k, v in faces.items()},
        "face_pairs": face_pairs,
        "tau_curve": {"eta": curve_eta, "points": curve},
        "comparison": compare_subset(label, baselines, n_boot, seed),
    }


def write(report: Mapping[str, Any], out_dir: Path, config_text: str, union: pd.DataFrame | None = None) -> None:
    if out_dir.exists():
        raise SystemExit(f"{out_dir} already exists: results are never overwritten, use a new run_id")
    out_dir.mkdir(parents=True)
    (out_dir / "rescue.json").write_text(json.dumps(report, indent=2, allow_nan=False, default=str), encoding="utf-8")
    (out_dir / "config.snapshot.yaml").write_text(config_text, encoding="utf-8")
    if union is not None:
        union.to_csv(out_dir / "rescue_windows.csv", index=False)
    if "points" in report and "metrics" in (report["points"] or [{}])[0]:
        with (out_dir / "points.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["name", "eta1", "eta2", "eta3", "tau", "feasible", "rescued", "rescued_in_subset",
                             "added_calls", "tp", "fp", "precision", "recall", "f1", "f1_lo", "f1_hi", "fpr"])
            for r in [report["off"], *report["points"]]:
                m = r["metrics"]
                eta = r["eta"] or ["", "", ""]
                writer.writerow([r["name"], *eta, r["tau"] if r["tau"] is not None else "", r["feasible"],
                                 r["rescued"], r["rescued_in_subset"], r["cost"]["added_calls"], m["tp"], m["fp"],
                                 f"{m['precision']:.4f}", f"{m['recall']:.4f}", f"{m['f1']:.4f}",
                                 f"{m['f1_ci95'][0]:.4f}", f"{m['f1_ci95'][1]:.4f}", f"{m['fpr']:.4f}"])


def table(report: Mapping[str, Any]) -> str:
    if "selected" not in report:
        return (f"[plan] feasible {report['feasible_points']}/{len(report['points'])}, union "
                f"{report['union_windows']} windows ({report['union_in_subset']} in subset), "
                f"cap {report['max_added_calls']:.0f} added calls")
    lines = [f"[rescue] judged {report['judged_rescue_windows']} rescue windows, "
             f"{report['judged_rescue_alerts']} alerts after CTAV policy"]
    for label_, r in (("off", report["off"]), ("selected", report["selected"]), ("best_point", report["best_point"])):
        m = r["metrics"]
        lines.append(f"  {label_:10s} {r['name']:28s} TP={m['tp']} FP={m['fp']} P={m['precision']:.4f} "
                     f"R={m['recall']:.4f} F1={m['f1']:.4f} [{m['f1_ci95'][0]:.4f}; {m['f1_ci95'][1]:.4f}] "
                     f"FPR={m['fpr']:.4f} +calls={r['cost']['added_calls']}")
    for pair, d in report["face_pairs"]["pairs"].items():
        lines.append(f"  {pair}: dF1={d['d_f1']:+.4f} [{d['d_f1_ci95'][0]:+.4f}; {d['d_f1_ci95'][1]:+.4f}] "
                     f"dR={d['d_recall']:+.4f} [{d['d_recall_ci95'][0]:+.4f}; {d['d_recall_ci95'][1]:+.4f}]")
    lines.append(f"  C5 kept: {report['c5_kept']}; formula components: {report['formula_components']}")
    return "\n".join(lines)
