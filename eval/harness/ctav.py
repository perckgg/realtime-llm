"""CTAV replay on cached tier runs: C2 + C3 + C4, theta sweep, H3 ablation, H4 budget curve (M6, QD-031).

    py -m eval ctav --config eval/configs/ctav_final.yaml

CTAV's decision is a pure function of the two tiers' judge answers (08 SS4,
01 SS6.4): tier 1 = a BM25 run, tier 2 = a C1 run of the same split, detector
and judge. Both runs judged every candidate, so every answer CTAV could ask for
is already cached; a tier-2 answer is only *counted* (calls, tokens) for the
candidates that C4 escalates. No LLM call is made.

Per variant (services/judge/policy.py + services/judge/routing.py):
- `two_tier`: C4 routing, tier-1 policy with theta_local, tier-2 with theta_topo;
- `topology_only`: no C4, every candidate judged on C1 context (tier 2);
- `local_only`: BM25 context only (tier 1).

Outputs in eval/results/<run_id>/ (must not exist): `ctav.json` (main variant,
H3 ablation with paired CI + McNemar against the full CTAV, comparison with the
baselines, theta sweep, budget curve, component verdicts by the criteria fixed
in the config), `per_window.csv` and `judged.jsonl` of the main variant (so
`py -m eval compare` and the RCA agent read it like any run).
"""

from __future__ import annotations

import csv
import gzip
import itertools
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
import yaml

from eval.harness.compare import compare_subset
from eval.harness.metrics import scores
from eval.harness.stats import bootstrap_confusion_ci
from packages.schemas.models import JudgedAlert
from services.judge.backends import PRICES_PER_1M
from services.judge.policy import EvidenceFact, PolicyConfig, Tier, apply_policy
from services.judge.routing import RoutingConfig, route

Mode = Literal["two_tier", "topology_only", "local_only"]
Baseline = Literal["rolling", "dev"]


def _read_yaml(path: Path, kind: str, required: Sequence[str]) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if config.get("kind") != kind:
        raise ValueError(f"{path}: expected `kind: {kind}`")
    for key in required:
        if key not in config:
            raise ValueError(f"{path}: missing `{key}`")
    return dict(config)


def load_anchor_config(path: Path) -> dict[str, Any]:
    return _read_yaml(path, "anchor_features", ["run_id", "runs", "rolling", "percentiles", "dev_baseline"])


def load_ctav_config(path: Path) -> dict[str, Any]:
    config = _read_yaml(path, "ctav", ["run_id", "split", "tiers", "anchor_features", "policy", "routing"])
    if config["split"] == "test" and not config.get("g_test", False):
        # Rule 2 (AGENTS.md): no `test` before M8 and the hypothesis registration of M7.
        raise ValueError(f"{path}: split test is only allowed at M8 (set g_test: true there)")
    if not {"local", "topology"} <= set(config["tiers"]):
        raise ValueError(f"{path}: tiers needs `local` and `topology`")
    return config


# --- inputs --------------------------------------------------------------------------------


def _flag(value: str) -> bool:
    return value not in ("", "0", "False", "false")


@dataclass
class TierRun:
    run_id: str
    rows: list[dict[str, str]]
    judged: dict[str, JudgedAlert]  # window_id -> raw judge answer (LLMJudge rules applied)
    context: dict[str, list[str]]  # window_id -> retrieved event ids


def load_tier_run(results: Path, run_id: str) -> TierRun:
    base = results / run_id
    with (base / "per_window.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    judged = {}
    with (base / "judged.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            alert = JudgedAlert.model_validate_json(line)
            judged[alert.window_id] = alert
    context = {}
    with (base / "retrieval.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            context[row["window_id"]] = [e["event_id"] for e in row["events"]]
    return TierRun(run_id, rows, judged, context)


def load_facts(results: Path, run_id: str) -> dict[tuple[str, str, str], dict[str, Any]]:
    """(tier run, window_id, event_id) -> anchoring record of scripts/build_anchor_features.py."""
    facts = {}
    with gzip.open(results / run_id / "events.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            facts[(record["run"], record["window_id"], record["event_id"])] = record
    return facts


def evidence_fact(record: Mapping[str, Any], baseline: Baseline, percentile: int) -> EvidenceFact:
    threshold = (record.get(baseline) or {}).get(str(percentile))
    return EvidenceFact(
        event_id=record["event_id"],
        service=record["service"],
        modality=record["modality"],
        severity=record.get("severity", "INFO"),
        duration_ms=record.get("duration_ms"),
        baseline_ms=threshold,
    )


# --- variants ------------------------------------------------------------------------------


@dataclass(frozen=True)
class Variant:
    name: str
    mode: Mode
    policy: PolicyConfig
    routing: RoutingConfig
    baseline: Baseline = "rolling"
    percentile: int = 95


def variant_from_config(config: Mapping[str, Any], name: str = "ctav") -> Variant:
    policy = config["policy"]
    anchor = policy.get("anchor") or {}
    routing = config["routing"]
    return Variant(
        name=name,
        mode="two_tier" if routing.get("enabled", True) else "topology_only",
        policy=PolicyConfig(
            theta_local=float(policy["theta_local"]),
            theta_topo=float(policy["theta_topo"]),
            gating=bool(policy.get("gating", True)),
            anchoring=bool(policy.get("anchoring", True)),
            require_evidence=bool(policy.get("require_evidence", True)),
            anchor_log_levels=frozenset(str(x).upper() for x in anchor.get("log_levels", ["ERROR", "WARN"])),
        ),
        routing=RoutingConfig(
            enabled=bool(routing.get("enabled", True)),
            escalate_on=frozenset(routing.get("escalate_on", ["no_context", "uncertain", "weak_fp"])),
            fp_confidence=float(routing["fp_confidence"]),
        ),
        baseline=anchor.get("baseline", "rolling"),
        percentile=int(anchor.get("percentile", 95)),
    )


@dataclass
class Outcome:
    """One variant over every window of the split, in replay order."""

    predicted: np.ndarray  # bool, decision == alert
    decisions: list[str]
    alerts: dict[str, JudgedAlert]  # window_id -> final alert (judged candidates only)
    escalations: dict[str, str | None]
    llm_calls: int
    tier2_calls: int
    prompt_tokens: int
    completion_tokens: int
    counts: Counter[str]


class Replay:
    def __init__(
        self,
        local: TierRun,
        topology: TierRun,
        facts: Mapping[tuple[str, str, str], Mapping[str, Any]],
    ) -> None:
        ids_local = [r["window_id"] for r in local.rows]
        ids_topo = [r["window_id"] for r in topology.rows]
        if ids_local != ids_topo:
            raise ValueError(f"{local.run_id} and {topology.run_id} do not cover the same windows")
        for a, b in zip(local.rows, topology.rows, strict=True):
            if (a["label_is_fault"], a["has_telemetry"], a["is_candidate"]) != (
                b["label_is_fault"],
                b["has_telemetry"],
                b["is_candidate"],
            ):
                raise ValueError(f"window {a['window_id']}: labels / candidates differ between tier runs")
        self.local = local
        self.topology = topology
        self.facts = facts
        self.rows = local.rows
        self.ids = ids_local
        self.label = np.array([_flag(r["label_is_fault"]) for r in self.rows])
        self.telemetry = np.array([_flag(r["has_telemetry"]) for r in self.rows])
        self.candidate = np.array([_flag(r["is_candidate"]) for r in self.rows])
        self._tokens = {
            run.run_id: {r["window_id"]: (int(r["prompt_tokens"] or 0), int(r["completion_tokens"] or 0)) for r in run.rows}
            for run in (local, topology)
        }

    def _cited(self, run: TierRun, alert: JudgedAlert, variant: Variant) -> list[EvidenceFact]:
        return [
            evidence_fact(self.facts[(run.run_id, alert.window_id, eid)], variant.baseline, variant.percentile)
            for eid in alert.evidence_event_ids
        ]

    def _judge(self, run: TierRun, window_id: str, tier: Tier, variant: Variant) -> JudgedAlert:
        raw = run.judged[window_id]
        return apply_policy(raw, self._cited(run, raw, variant), tier, variant.policy)

    def run(self, variant: Variant, budget: int | None = None) -> Outcome:
        predicted = np.zeros(len(self.ids), dtype=bool)
        decisions = ["none"] * len(self.ids)
        alerts: dict[str, JudgedAlert] = {}
        escalations: dict[str, str | None] = {}
        calls = tier2_calls = prompt = completion = 0
        counts: Counter[str] = Counter()
        for i, window_id in enumerate(self.ids):
            if not self.candidate[i]:
                continue
            left = None if budget is None else budget - calls
            if left is not None and left < 1:
                decisions[i] = "manual_review"  # llm_budget_exhausted (runner.Gate)
                counts["budget_exhausted"] += 1
                continue
            if variant.mode == "local_only":
                alert, used = self._judge(self.local, window_id, 1, variant), [self.local]
                reason = None
            elif variant.mode == "topology_only":
                alert = self._judge(self.topology, window_id, 2, variant).model_copy(update={"routing_tier": 2})
                used, reason = [self.topology], None
            else:
                w = window_id

                def tier1() -> tuple[JudgedAlert, int]:
                    return self._judge(self.local, w, 1, variant), len(self.local.context.get(w, []))

                def tier2() -> JudgedAlert | None:
                    return self._judge(self.topology, w, 2, variant) if self.topology.context.get(w) else None

                routed = route(tier1, tier2, variant.routing, left)
                alert, reason = routed.alert, routed.escalation
                used = [self.local] if routed.llm_calls == 1 else [self.local, self.topology]
                if reason:
                    counts[f"escalation_{reason}"] += 1
                if routed.tier2_skipped:
                    counts[f"tier2_skipped_{routed.tier2_skipped}"] += 1
            for run in used:
                p, c = self._tokens[run.run_id][window_id]
                prompt, completion = prompt + p, completion + c
            calls += len(used)
            tier2_calls += int(self.topology in used)
            escalations[window_id] = reason
            alerts[window_id] = alert
            decision = {"TRUE_ALERT": "alert", "FALSE_POSITIVE": "suppress"}.get(alert.verdict, "manual_review")
            decisions[i] = decision
            predicted[i] = decision == "alert"
            for flag in ("downgraded_by_evidence_rule", "downgraded_by_gating", "downgraded_by_anchoring"):
                counts[flag] += int(getattr(alert, flag))
            counts["downgraded_by_threshold"] += int(bool(alert.debug.get("downgraded_by_threshold")))
            counts[f"final_tier{alert.routing_tier}"] += 1
        return Outcome(predicted, decisions, alerts, escalations, calls, tier2_calls, prompt, completion, counts)


def raw_run_predictions(run: TierRun, budget: int | None = None) -> np.ndarray:
    """A plain run's decisions, under a chronological call budget like runner.Gate."""
    predicted = np.zeros(len(run.rows), dtype=bool)
    used = 0
    for i, row in enumerate(run.rows):
        if not _flag(row["is_candidate"]):
            continue
        if budget is not None and used >= budget:
            continue
        used += 1
        predicted[i] = row["decision"] == "alert"
    return predicted


# --- reporting -----------------------------------------------------------------------------


def _metrics(label: np.ndarray, predicted: np.ndarray, n_boot: int, seed: int) -> dict[str, Any]:
    cm = {
        "tp": int(np.sum(label & predicted)),
        "fp": int(np.sum(~label & predicted)),
        "fn": int(np.sum(label & ~predicted)),
        "tn": int(np.sum(~label & ~predicted)),
    }
    out: dict[str, Any] = {**cm, **scores(cm)}
    for name, (lo, hi) in bootstrap_confusion_ci(cm, scores, n_boot, seed).items():
        out[f"{name}_ci95"] = [lo, hi]
    return out


def _cost(outcome: Outcome, price_in: float, price_out: float) -> dict[str, Any]:
    return {
        "llm_calls": outcome.llm_calls,
        "tier2_calls": outcome.tier2_calls,
        "prompt_tokens": outcome.prompt_tokens,
        "completion_tokens": outcome.completion_tokens,
        "estimated_cost_usd": outcome.prompt_tokens / 1e6 * price_in + outcome.completion_tokens / 1e6 * price_out,
    }


def ablations(main: Variant) -> list[Variant]:
    """H3: one component at a time (08 SS5.1). C4 is either removed from a two-tier main
    (`no_c4`) or, when H3 already dropped it, added back to a topology-only main (`with_c4`)."""
    other: Baseline = "dev" if main.baseline == "rolling" else "rolling"
    if main.mode == "two_tier":
        c4 = replace(main, name="no_c4", mode="topology_only", routing=replace(main.routing, enabled=False))
    else:
        c4 = replace(main, name="with_c4", mode="two_tier", routing=replace(main.routing, enabled=True))
    return [
        main,
        replace(main, name="no_c2", policy=replace(main.policy, gating=False)),
        replace(main, name="no_c3", policy=replace(main.policy, anchoring=False)),
        c4,
        replace(main, name=f"c3_{other}_baseline", baseline=other),
    ]


def sweep_variants(main: Variant, grid: Mapping[str, Sequence[Any]]) -> list[Variant]:
    keys = list(grid)
    out = []
    for values in itertools.product(*(grid[k] for k in keys)):
        point = dict(zip(keys, values, strict=True))
        variant = main
        if "theta_topo" in point:
            variant = replace(variant, policy=replace(variant.policy, theta_topo=float(point["theta_topo"])))
        if "fp_confidence" in point:
            variant = replace(variant, routing=replace(variant.routing, fp_confidence=float(point["fp_confidence"])))
        if "percentile" in point:
            variant = replace(variant, percentile=int(point["percentile"]))
        if "baseline" in point:
            variant = replace(variant, baseline=point["baseline"])
        if "mode" in point:
            variant = replace(
                variant, mode=point["mode"], routing=replace(variant.routing, enabled=point["mode"] == "two_tier")
            )
        out.append(replace(variant, name="|".join(f"{k}={v}" for k, v in point.items())))
    return out


def _describe(variant: Variant) -> dict[str, Any]:
    return {
        "mode": variant.mode,
        "theta_local": variant.policy.theta_local,
        "theta_topo": variant.policy.theta_topo,
        "gating": variant.policy.gating,
        "anchoring": variant.policy.anchoring,
        "fp_confidence": variant.routing.fp_confidence,
        "escalate_on": sorted(variant.routing.escalate_on),
        "baseline": variant.baseline,
        "percentile": variant.percentile,
    }


def select(points: Sequence[Mapping[str, Any]], metric: str) -> Mapping[str, Any]:
    """Best `metric` on the main subset; ties -> fewer LLM calls, then lower FPR (fixed before the sweep)."""
    return max(points, key=lambda p: (round(p["metrics"][metric], 9), -p["cost"]["llm_calls"], -p["metrics"]["fpr"]))


def component_verdicts(pairs: Mapping[str, Any], costs: Mapping[str, Mapping[str, Any]], main: Variant) -> dict[str, Any]:
    """H3 criteria of 08 SS5.1, read off the ablation (pairs are `variant - ctav`)."""
    c2 = pairs["no_c2 - ctav"]
    c3 = pairs["no_c3 - ctav"]
    if "no_c4 - ctav" in pairs:
        with_c4, without_c4 = "ctav", "no_c4"
        c4 = pairs["no_c4 - ctav"]
    else:  # topology-only main: flip `with_c4 - ctav` to `without - with`
        with_c4, without_c4 = "with_c4", "ctav"
        flipped = pairs["with_c4 - ctav"]
        c4 = {"d_f1": -flipped["d_f1"], "d_f1_ci95": [-flipped["d_f1_ci95"][1], -flipped["d_f1_ci95"][0]]}
    return {
        "C2": {
            "rule": "removing C2 raises FPR: d_fpr CI95 lower bound > 0 (no-op if theta_topo == theta_local)",
            "theta_topo_above_local": main.policy.gating and main.policy.theta_topo > main.policy.theta_local,
            "d_fpr_ci95": c2.get("d_fpr_ci95"),
            "contributes": main.policy.gating
            and main.policy.theta_topo > main.policy.theta_local
            and c2["d_fpr_ci95"][0] > 0,
        },
        "C3": {
            "rule": "removing C3 lowers precision: d_precision CI95 upper bound < 0",
            "d_precision_ci95": c3.get("d_precision_ci95"),
            "contributes": c3["d_precision_ci95"][1] < 0,
        },
        "C4": {
            "rule": "removing C4 costs more (USD) and does not raise F1: "
            "cost(without) > cost(with) and d_f1(without - with) CI95 lower bound <= 0",
            "with": with_c4,
            "without": without_c4,
            "cost_usd": {k: costs[k]["estimated_cost_usd"] for k in (with_c4, without_c4)},
            "d_f1_without_minus_with": c4.get("d_f1"),
            "d_f1_ci95": c4.get("d_f1_ci95"),
            "contributes": costs[without_c4]["estimated_cost_usd"] > costs[with_c4]["estimated_cost_usd"]
            and c4["d_f1_ci95"][0] <= 0,
        },
    }


def evaluate(config: Mapping[str, Any], results: Path) -> tuple[dict[str, Any], Replay, Outcome, Variant]:
    n_boot, seed = int(config.get("n_boot", 1000)), int(config.get("seed", 42))
    tiers = config["tiers"]
    replay = Replay(
        load_tier_run(results, tiers["local"]),
        load_tier_run(results, tiers["topology"]),
        load_facts(results, config["anchor_features"]),
    )
    model = str(config.get("model", "gemini-2.5-flash"))
    price_in, price_out = PRICES_PER_1M.get(model, (0.0, 0.0))
    subset = config.get("subset", "telemetry")
    mask = replay.telemetry if subset == "telemetry" else np.ones(len(replay.ids), dtype=bool)
    label = replay.label[mask]
    main = variant_from_config(config)
    report: dict[str, Any] = {
        "created_at": datetime.now(UTC).isoformat(),
        "config": dict(config),
        "subset": subset,
        "windows": int(mask.sum()),
        "fault_windows": int(label.sum()),
        "candidates": int(replay.candidate[mask].sum()),
        "price_per_1m": [price_in, price_out],
    }

    sweep = config.get("sweep")
    if sweep:
        points: list[dict[str, Any]] = []
        for variant in sweep_variants(main, sweep["grid"]):
            outcome = replay.run(variant)
            points.append(
                {
                    "name": variant.name,
                    "variant": _describe(variant),
                    "metrics": _metrics(label, outcome.predicted[mask], n_boot, seed),
                    "cost": _cost(outcome, price_in, price_out),
                }
            )
        modes = set(sweep.get("select_modes", ["two_tier"]))
        best = select([p for p in points if p["variant"]["mode"] in modes], sweep.get("metric", "f1"))
        report["sweep"] = {"grid": sweep["grid"], "metric": sweep.get("metric", "f1"), "select_modes": sorted(modes),
                           "points": points, "selected": best["name"], "selected_variant": best["variant"]}
        if sweep.get("apply_selection", False):
            chosen = best["variant"]
            main = replace(
                main,
                mode=chosen["mode"],
                policy=replace(main.policy, theta_topo=chosen["theta_topo"]),
                routing=replace(main.routing, fp_confidence=chosen["fp_confidence"], enabled=chosen["mode"] == "two_tier"),
                baseline=chosen["baseline"],
                percentile=chosen["percentile"],
            )

    variants = ablations(main)
    outcomes = {v.name: replay.run(v) for v in variants}
    baselines = {name: load_tier_run(results, run_id) for name, run_id in (config.get("baselines") or {}).items()}
    predictions: dict[str, np.ndarray] = {v.name: outcomes[v.name].predicted[mask] for v in variants}
    for name, run in baselines.items():
        if [r["window_id"] for r in run.rows] != replay.ids:
            raise ValueError(f"baseline {run.run_id} does not cover the same windows")
        predictions[name] = raw_run_predictions(run)[mask]
    predictions["detector_only"] = replay.candidate[mask]
    costs = {v.name: _cost(outcomes[v.name], price_in, price_out) for v in variants}
    report["main"] = {"variant": _describe(main), "cost": costs["ctav"], "counts": dict(outcomes["ctav"].counts)}
    report["ablation"] = compare_subset(label, {k: predictions[k] for k in outcomes}, n_boot, seed)
    report["ablation"]["costs"] = costs
    report["ablation"]["variants"] = {v.name: _describe(v) for v in variants}
    report["ablation"]["counts"] = {k: dict(o.counts) for k, o in outcomes.items()}
    report["components"] = component_verdicts(report["ablation"]["pairs"], costs, main)
    order = [n for n in ("bm25", "c1", "norag") if n in predictions] + ["ctav", "detector_only"]
    report["baselines"] = compare_subset(label, {k: predictions[k] for k in order if k in predictions}, n_boot, seed)

    budgets = config.get("budgets") or []
    if budgets:
        curve: dict[str, list[dict[str, Any]]] = {"ctav": []}
        for budget in budgets:
            outcome = replay.run(main, int(budget))
            curve["ctav"].append({"budget": budget, "llm_calls": outcome.llm_calls,
                                  **_metrics(label, outcome.predicted[mask], n_boot, seed)})
        for name, run in baselines.items():
            curve[name] = [{"budget": b, **_metrics(label, raw_run_predictions(run, int(b))[mask], n_boot, seed)}
                           for b in budgets]
        report["budget_curve"] = curve
    return report, replay, outcomes["ctav"], main


PER_WINDOW = [
    "window_id", "service", "pod", "window_ts", "label_is_fault", "label_fault_type", "label_root_cause",
    "has_telemetry", "anomaly_score", "is_candidate", "tier1_verdict", "escalation", "routing_tier",
    "raw_verdict", "verdict", "confidence", "threshold_applied", "downgraded_by_evidence_rule",
    "downgraded_by_gating", "downgraded_by_anchoring", "anchor_ids", "judged", "decision",
]  # fmt: skip


def write(report: Mapping[str, Any], replay: Replay, outcome: Outcome, out_dir: Path, config_text: str) -> None:
    if out_dir.exists():
        raise SystemExit(f"{out_dir} already exists: results are never overwritten, use a new run_id")
    out_dir.mkdir(parents=True)
    (out_dir / "ctav.json").write_text(json.dumps(report, indent=2, allow_nan=False, default=str), encoding="utf-8")
    (out_dir / "config.snapshot.yaml").write_text(config_text, encoding="utf-8")
    with (out_dir / "per_window.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PER_WINDOW, extrasaction="ignore")
        writer.writeheader()
        for i, row in enumerate(replay.rows):
            window_id = row["window_id"]
            alert = outcome.alerts.get(window_id)
            tier1 = replay.local.judged.get(window_id)
            record: dict[str, Any] = {**row, "decision": outcome.decisions[i], "judged": int(alert is not None)}
            if alert is not None:
                record.update(
                    {
                        "tier1_verdict": tier1.raw_verdict if tier1 else "",
                        "escalation": outcome.escalations.get(window_id) or "",
                        "routing_tier": alert.routing_tier,
                        "raw_verdict": alert.raw_verdict,
                        "verdict": alert.verdict,
                        "confidence": alert.confidence,
                        "threshold_applied": alert.threshold_applied,
                        "downgraded_by_evidence_rule": int(alert.downgraded_by_evidence_rule),
                        "downgraded_by_gating": int(alert.downgraded_by_gating),
                        "downgraded_by_anchoring": int(alert.downgraded_by_anchoring),
                        "anchor_ids": "|".join(alert.debug.get("anchor_ids", [])),
                    }
                )
            writer.writerow(record)
    with (out_dir / "judged.jsonl").open("w", encoding="utf-8") as handle:
        for window_id in replay.ids:
            if window_id in outcome.alerts:
                handle.write(outcome.alerts[window_id].model_dump_json() + "\n")


def table(report: Mapping[str, Any]) -> str:
    lines = []
    for block_name in ("ablation", "baselines"):
        block = report[block_name]
        lines.append(f"[{block_name}] windows={block['windows']} faults={block['fault_windows']}")
        for name, m in block["methods"].items():
            cost = (block.get("costs") or {}).get(name, {})
            lines.append(
                f"  {name:16s} TP={m['tp']:4d} FP={m['fp']:5d} P={m['precision']:.4f} R={m['recall']:.4f} "
                f"F1={m['f1']:.4f} [{m['f1_ci95'][0]:.4f}; {m['f1_ci95'][1]:.4f}] FPR={m['fpr']:.4f}"
                + (f" calls={cost['llm_calls']} usd={cost['estimated_cost_usd']:.3f}" if cost else "")
            )
        for pair, d in block["pairs"].items():
            lines.append(
                f"  {pair}: dP={d['d_precision']:+.4f} dR={d['d_recall']:+.4f} dF1={d['d_f1']:+.4f} "
                f"[{d['d_f1_ci95'][0]:+.4f}; {d['d_f1_ci95'][1]:+.4f}] dFPR={d['d_fpr']:+.4f} "
                f"[{d['d_fpr_ci95'][0]:+.4f}; {d['d_fpr_ci95'][1]:+.4f}] "
                f"McNemar p(fault/normal)={d['mcnemar_fault']['p_value']:.3g}/{d['mcnemar_normal']['p_value']:.3g}"
            )
    if "sweep" in report:
        lines.append(f"[sweep] selected {report['sweep']['selected']}")
    lines.append("[components] " + ", ".join(f"{k}: {v['contributes']}" for k, v in report["components"].items()))
    return "\n".join(lines)
