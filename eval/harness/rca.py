"""RCA harness (M9): CTAV alerts of one run -> incidents -> root cause -> Hit@k, ARR, reports.

    py -m eval rca --config eval/configs/rca_final.yaml

Input: the alerts of a CTAV run (`input.alerts_run`: its per_window.csv + judged.jsonl), or of
one named ablation variant replayed from a CTAV config (`input.ctav_config` + `input.variant`,
for the sensitivity line of QD-039). Evidence text comes from `input.evidence_run`.

Everything below was written before any val number was computed (QD-040):

Ground truth (02 SS4.3, QD-001). A fault injection covers [first fault window, last fault window
+ window_seconds) (QD-003: inject_ts - 60 s .. + 360 s). An alert belongs to every injection its
window overlaps, whatever its service. An incident is `labelled` when its alerts belong to
exactly one injection (ground truth = that injection's root cause service), `ambiguous` with two
or more (excluded from Hit@k, counted), `no_fault` with none (no root cause to find; excluded,
counted).

Alert Reduction Ratio (02 SS4.3) on a set of alerts = 1 - (#incidents holding at least one of
them) / (#alerts). Sets: `all`; `fault` (alerts of any injection); `type:<fault_type>`; `cascade`
= alerts of the injections whose alerts touch >= `labels.cascade_min_services` services.

Hit@k (02 SS4.3) over labelled incidents: ground truth in the top k of the ranking. Level 1 =
services/rca_agent/propagation.py; baseline = highest anomaly score among the incident's alerts.
Also per injection (all injections of the split, an injection without any labelled incident is
a miss; with several, the earliest incident counts).

CI: percentile bootstrap, `n_boot` resamples, `seed` (eval/harness/stats.py). Hit@k resamples
incidents (the paired delta uses the same resamples); ARR resamples the time clusters of the
largest T_group in play, which contain the incidents of every smaller T_group.

Selection rules -- `select_t_group`, `select_sign` -- are fixed in this file, see their docstrings.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import time
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from eval.harness.stats import bootstrap_ci
from packages.graph.service_graph import ServiceGraph, load_graph
from packages.schemas.models import ContextEvent, Incident, JudgedAlert
from services.judge.backends import JUDGE_MODEL, PRICES_PER_1M
from services.judge.cache import ResponseCache
from services.rca_agent.grouping import group_alerts, time_clusters
from services.rca_agent.propagation import (
    SIGNS,
    RankedService,
    Sign,
    backward_one_hop,
    propagation_path,
    rank_by_anomaly_score,
)
from services.rca_agent.summarizer import (
    PROMPT_VERSION,
    GeminiSummaryBackend,
    MockSummaryBackend,
    Summarizer,
    SummaryBackend,
    SummaryResult,
    compose_prompt,
    prompt_fingerprint,
)

REPO = Path(__file__).resolve().parents[2]
WINDOW_INDEX = REPO / "data" / "window_index.csv"
LLM_CACHE = REPO / "data" / "llm_cache" / "gemini.jsonl"


def load_rca_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if config.get("kind") != "rca":
        raise ValueError(f"{path}: expected `kind: rca`")
    for key in ("run_id", "split", "input", "grouping", "propagation"):
        if key not in config:
            raise ValueError(f"{path}: missing `{key}`")
    if config["split"] == "test" and not config.get("h5_test", False):
        # M9-B only: rca_final.yaml must be committed first (QD-037, QD-039).
        raise ValueError(f"{path}: split test is only allowed at M9-B (set h5_test: true there)")
    source = config["input"]
    if ("alerts_run" in source) == ("ctav_config" in source):
        raise ValueError(f"{path}: input needs exactly one of `alerts_run`, `ctav_config`")
    if config["propagation"].get("sign", "alert") not in SIGNS:
        raise ValueError(f"{path}: propagation.sign must be one of {SIGNS}")
    return dict(config)


# --- inputs --------------------------------------------------------------------------------


def _flag(value: str) -> bool:
    return value not in ("", "0", "False", "false")


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


@dataclass(frozen=True)
class Injection:
    injection_id: str
    fault_type: str
    root_cause_service: str
    start: datetime
    end: datetime  # exclusive


@dataclass
class Inputs:
    rows: list[dict[str, str]]  # every window of the split: window_id, service, window_ts, anomaly_score, is_candidate
    alerts: list[JudgedAlert]
    source: str


def load_inputs(config: Mapping[str, Any], results: Path) -> Inputs:
    source = config["input"]
    if "alerts_run" in source:
        base = results / source["alerts_run"]
        with (base / "per_window.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        wanted = {r["window_id"] for r in rows if r["decision"] == "alert"}
        alerts = []
        with (base / "judged.jsonl").open(encoding="utf-8") as handle:
            for line in handle:
                alert = JudgedAlert.model_validate_json(line)
                if alert.window_id in wanted:
                    alerts.append(alert)
        if {a.window_id for a in alerts} != wanted:
            raise ValueError(f"{base}: judged.jsonl does not hold every alert of per_window.csv")
        return Inputs(rows, alerts, f"{source['alerts_run']} (decision == alert)")
    from eval.harness import ctav

    ctav_config = ctav.load_ctav_config(REPO / source["ctav_config"])
    if ctav_config["split"] != config["split"]:
        raise ValueError("input.ctav_config is on another split than this RCA config")
    tiers = ctav_config["tiers"]
    replay = ctav.Replay(
        ctav.load_tier_run(results, tiers["local"]),
        ctav.load_tier_run(results, tiers["topology"]),
        ctav.load_facts(results, ctav_config["anchor_features"]),
    )
    variants = {v.name: v for v in ctav.ablations(ctav.variant_from_config(ctav_config))}
    name = source.get("variant", "ctav")
    if name not in variants:
        raise ValueError(f"input.variant {name!r} is not one of {sorted(variants)}")
    outcome = replay.run(variants[name])
    alerts = [outcome.alerts[w] for i, w in enumerate(replay.ids) if outcome.predicted[i]]
    return Inputs(replay.rows, alerts, f"{source['ctav_config']} variant {name}")


def load_injections(window_ids: set[str], window_seconds: float, path: Path = WINDOW_INDEX) -> list[Injection]:
    """Injections of the split, from the fault windows of data/window_index.csv restricted to
    `window_ids` -- windows of other splits are never read into the result."""
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["injection_id"] and _flag(row["is_fault"]) and row["window_id"] in window_ids:
                grouped[row["injection_id"]].append(row)
    out = []
    for injection_id, rows in grouped.items():
        starts = [_ts(r["start_ts"]) for r in rows]
        out.append(
            Injection(
                injection_id=injection_id,
                fault_type=rows[0]["fault_type"],
                root_cause_service=rows[0]["root_cause_service"],
                start=min(starts),
                end=max(starts) + timedelta(seconds=window_seconds),
            )
        )
    return sorted(out, key=lambda i: (i.start, i.injection_id))


def load_evidence(results: Path, run_id: str, window_ids: set[str]) -> dict[str, dict[str, ContextEvent]]:
    """window_id -> event_id -> event, for the alert windows only."""
    out: dict[str, dict[str, ContextEvent]] = {}
    with (results / run_id / "retrieval.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["window_id"] in window_ids:
                out[row["window_id"]] = {e["event_id"]: ContextEvent.model_validate(e) for e in row["events"]}
    return out


class ServiceSeries:
    """Per service: window start times with anomaly score and detector flag, for span lookups."""

    def __init__(self, rows: Sequence[Mapping[str, str]]) -> None:
        grouped: dict[str, list[tuple[datetime, float, bool]]] = defaultdict(list)
        for row in rows:
            score = float(row["anomaly_score"]) if row.get("anomaly_score") not in (None, "") else 0.0
            if math.isnan(score):
                score = 0.0
            grouped[row["service"]].append((_ts(row["window_ts"]), score, _flag(row["is_candidate"])))
        self._data = {s: sorted(v) for s, v in grouped.items()}
        self._times = {s: [t for t, _, _ in v] for s, v in self._data.items()}

    def span(self, service: str, start: datetime, end: datetime) -> tuple[float, bool]:
        """(highest anomaly score, any detector candidate) of the service's windows starting in [start, end]."""
        times = self._times.get(service)
        if not times:
            return 0.0, False
        chunk = self._data[service][bisect_left(times, start) : bisect_right(times, end)]
        if not chunk:
            return 0.0, False
        return max(s for _, s, _ in chunk), any(c for _, _, c in chunk)


# --- labels --------------------------------------------------------------------------------


def alert_injections(alert: JudgedAlert, injections: Sequence[Injection], window_seconds: float) -> list[str]:
    end = alert.ts + timedelta(seconds=window_seconds)
    return [i.injection_id for i in injections if alert.ts < i.end and end > i.start]


@dataclass
class Labelled:
    incident: Incident
    status: str  # labelled | ambiguous | no_fault
    injection_ids: list[str]
    fault_type: str | None
    root_cause: str | None


def label_incidents(
    incidents: Sequence[Incident], membership: Mapping[str, Sequence[str]], injections: Mapping[str, Injection]
) -> list[Labelled]:
    out = []
    for incident in incidents:
        ids = sorted({i for alert_id in incident.alert_ids for i in membership[alert_id]})
        if len(ids) == 1:
            injection = injections[ids[0]]
            out.append(Labelled(incident, "labelled", ids, injection.fault_type, injection.root_cause_service))
        else:
            out.append(Labelled(incident, "ambiguous" if ids else "no_fault", ids, None, None))
    return out


def alert_sets(
    alerts: Sequence[JudgedAlert],
    membership: Mapping[str, Sequence[str]],
    injections: Mapping[str, Injection],
    cascade_min_services: int,
) -> dict[str, set[str]]:
    """Named sets of alert ids the ARR is reported on (module docstring)."""
    services: dict[str, set[str]] = defaultdict(set)
    for alert in alerts:
        for injection_id in membership[alert.alert_id]:
            services[injection_id].add(alert.service)
    cascade = {i for i, s in services.items() if len(s) >= cascade_min_services}
    sets: dict[str, set[str]] = {"all": {a.alert_id for a in alerts}, "fault": set(), "cascade": set()}
    for fault_type in sorted({i.fault_type for i in injections.values()}):
        sets[f"type:{fault_type}"] = set()
    for alert in alerts:
        ids = membership[alert.alert_id]
        if ids:
            sets["fault"].add(alert.alert_id)
        if any(i in cascade for i in ids):
            sets["cascade"].add(alert.alert_id)
        for injection_id in ids:
            sets[f"type:{injections[injection_id].fault_type}"].add(alert.alert_id)
    return sets


# --- alert reduction -----------------------------------------------------------------------


def _unit_counts(
    units: Sequence[Sequence[JudgedAlert]], incidents: Sequence[Incident], subset: set[str]
) -> tuple[np.ndarray, np.ndarray]:
    """Per resampling unit: (#subset alerts, #incidents holding one). Every incident lies in one unit."""
    unit_of = {a.alert_id: u for u, unit in enumerate(units) for a in unit}
    n_alerts = np.zeros(len(units))
    n_incidents = np.zeros(len(units))
    for u, unit in enumerate(units):
        n_alerts[u] = sum(1 for a in unit if a.alert_id in subset)
    for incident in incidents:
        if any(alert_id in subset for alert_id in incident.alert_ids):
            n_incidents[unit_of[incident.alert_ids[0]]] += 1
    return n_alerts, n_incidents


def _ci(values: np.ndarray, alpha: float = 0.05) -> list[float] | None:
    values = values[~np.isnan(values)]
    if values.size == 0:
        return None
    return [float(np.quantile(values, alpha / 2)), float(np.quantile(values, 1 - alpha / 2))]


def reduction_table(
    units: Sequence[Sequence[JudgedAlert]],
    incidents_by_t: Mapping[float, Sequence[Incident]],
    sets: Mapping[str, set[str]],
    reference_t: float,
    n_boot: int,
    seed: int,
) -> dict[str, Any]:
    """ARR per alert set and T_group with CI, and the paired difference to `reference_t`."""
    draws = np.random.default_rng(seed).integers(0, len(units), size=(n_boot, len(units))) if units else None
    table: dict[str, Any] = {}
    for name, subset in sets.items():
        per_t: dict[str, Any] = {}
        boots: dict[float, np.ndarray] = {}
        for t, incidents in incidents_by_t.items():
            n_alerts, n_incidents = _unit_counts(units, incidents, subset)
            total = float(n_alerts.sum())
            point = 1.0 - float(n_incidents.sum()) / total if total else None
            if draws is not None and total:
                a, i = n_alerts[draws].sum(axis=1), n_incidents[draws].sum(axis=1)
                with np.errstate(divide="ignore", invalid="ignore"):
                    boots[t] = np.where(a > 0, 1.0 - i / a, np.nan)
            per_t[str(int(t))] = {
                "alerts": int(total),
                "incidents": int(n_incidents.sum()),
                "arr": point,
                "arr_ci95": _ci(boots[t]) if t in boots else None,
            }
        for t in incidents_by_t:
            if t != reference_t and t in boots and reference_t in boots:
                ref, cur = per_t[str(int(reference_t))]["arr"], per_t[str(int(t))]["arr"]
                per_t[str(int(t))]["d_arr_vs_reference"] = cur - ref
                per_t[str(int(t))]["d_arr_vs_reference_ci95"] = _ci(boots[t] - boots[reference_t])
        table[name] = per_t
    return table


def select_t_group(
    grid: Sequence[float], default: float, ambiguous: Mapping[float, int], reduction: Mapping[str, Any]
) -> tuple[float, str]:
    """T_group rule, fixed before the val numbers (QD-040). `reduction` = reduction_table(...)["fault"]
    computed with `reference_t` = the reference of step 2.

    1. Keep the T with the fewest ambiguous incidents: merging two faults into one incident is
       the one error grouping must not trade for alert reduction.
    2. Reference = `default` (01 SS6.5: 300 s) when kept, else the smallest kept T.
    3. Another kept T replaces the reference only when its ARR on fault alerts is higher with a
       paired bootstrap CI95 lower bound > 0. Several such T: the highest ARR, then the smaller T.
    4. Otherwise the reference stays: a difference inside its CI -- and any tie -- never moves T.
    """
    fewest = min(ambiguous[t] for t in grid)
    kept = [t for t in grid if ambiguous[t] == fewest]
    reference = default if default in kept else min(kept)
    better = []
    for t in kept:
        ci = reduction[str(int(t))].get("d_arr_vs_reference_ci95") if t != reference else None
        if ci is not None and ci[0] > 0:
            better.append(t)
    if not better:
        why = "default" if reference == default else "smallest T among those with the fewest ambiguous incidents"
        return reference, f"reference kept ({why}); no other T has d_ARR(fault) CI95 lower bound > 0"
    best = max(better, key=lambda t: (round(reduction[str(int(t))]["arr"], 9), -t))
    return best, "ARR(fault) higher than the reference with CI95 lower bound > 0"


def reference_t_group(grid: Sequence[float], default: float, ambiguous: Mapping[float, int]) -> float:
    fewest = min(ambiguous[t] for t in grid)
    kept = [t for t in grid if ambiguous[t] == fewest]
    return default if default in kept else min(kept)


# --- localisation --------------------------------------------------------------------------


@dataclass
class Located:
    labelled: Labelled
    level1: list[RankedService]
    baseline: list[str]
    elapsed_ms: float


def locate(
    labelled: Labelled,
    alerts_by_id: Mapping[str, JudgedAlert],
    alert_scores: Mapping[str, float],
    graph: ServiceGraph,
    series: ServiceSeries,
    sign: Sign,
    pad_seconds: float,
) -> Located:
    started = time.perf_counter()
    incident = labelled.incident
    start = incident.start_ts - timedelta(seconds=pad_seconds)
    end = incident.end_ts + timedelta(seconds=pad_seconds)
    own: dict[str, float] = {}
    for alert_id in incident.alert_ids:
        service = alerts_by_id[alert_id].service
        own[service] = max(own.get(service, 0.0), alert_scores[alert_id])
    callees = {c for s in own if s in graph.directed for c in graph.directed.successors(s)}
    scores, abnormal = dict(own), set()
    for service in sorted(callees | set(own)):
        best, flagged = series.span(service, start, end)
        scores[service] = max(scores.get(service, 0.0), best)
        if sign == "candidate" and flagged and service not in own:
            abnormal.add(service)
    level1 = backward_one_hop(own.keys(), graph, scores, abnormal)
    return Located(labelled, level1, rank_by_anomaly_score(own), (time.perf_counter() - started) * 1000.0)


def _hit(ranking: Sequence[str], truth: str | None, k: int) -> bool:
    return truth is not None and truth in ranking[:k]


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else math.nan


def hit_table(located: Sequence[Located], n_boot: int, seed: int) -> dict[str, Any]:
    """Hit@1 / Hit@3 of level 1 and the baseline over labelled incidents, paired deltas, CI."""
    rows = [
        (
            _hit([r.service for r in item.level1], item.labelled.root_cause, 1),
            _hit([r.service for r in item.level1], item.labelled.root_cause, 3),
            _hit(item.baseline, item.labelled.root_cause, 1),
            _hit(item.baseline, item.labelled.root_cause, 3),
        )
        for item in located
        if item.labelled.status == "labelled"
    ]
    return _hit_stats(rows, n_boot, seed)


def _column_mean(rows: Sequence[tuple[bool, bool, bool, bool]], col: int) -> float:
    return _mean([float(r[col]) for r in rows])


def _column_delta(rows: Sequence[tuple[bool, bool, bool, bool]], a: int, b: int) -> float:
    return _mean([float(r[a]) - float(r[b]) for r in rows])


def _hit_stats(rows: Sequence[tuple[bool, bool, bool, bool]], n_boot: int, seed: int) -> dict[str, Any]:
    out: dict[str, Any] = {"n": len(rows)}
    columns = {"level1_hit1": 0, "level1_hit3": 1, "baseline_hit1": 2, "baseline_hit3": 3}
    for name, col in columns.items():
        out[name] = _mean([float(r[col]) for r in rows]) if rows else None
        out[f"{name}_count"] = sum(int(r[col]) for r in rows)
        out[f"{name}_ci95"] = list(bootstrap_ci(rows, partial(_column_mean, col=col), n_boot, seed)) if rows else None
    for k, (a, b) in {"1": (0, 2), "3": (1, 3)}.items():
        out[f"d_hit{k}"] = _mean([float(r[a]) - float(r[b]) for r in rows]) if rows else None
        out[f"d_hit{k}_ci95"] = list(bootstrap_ci(rows, partial(_column_delta, a=a, b=b), n_boot, seed)) if rows else None
        out[f"discordant_hit{k}"] = {
            "level1_only": sum(1 for r in rows if r[a] and not r[b]),
            "baseline_only": sum(1 for r in rows if r[b] and not r[a]),
        }
    return out


def injection_table(
    located: Sequence[Located], injections: Sequence[Injection], n_boot: int, seed: int
) -> dict[str, Any]:
    """Hit@k over every injection of the split: no labelled incident = miss; several = the earliest."""
    first: dict[str, Located] = {}
    ambiguous_only: set[str] = set()
    for item in sorted(located, key=lambda x: (x.labelled.incident.start_ts, x.labelled.incident.incident_id)):
        if item.labelled.status == "labelled":
            first.setdefault(item.labelled.injection_ids[0], item)
        elif item.labelled.status == "ambiguous":
            ambiguous_only.update(item.labelled.injection_ids)
    rows = []
    by_type: dict[str, Counter[str]] = defaultdict(Counter)
    for injection in injections:
        hit = first.get(injection.injection_id)
        by_type[injection.fault_type]["injections"] += 1
        if hit is None:
            rows.append((False, False, False, False))
            continue
        by_type[injection.fault_type]["with_labelled_incident"] += 1
        level1 = [r.service for r in hit.level1]
        row = (
            _hit(level1, injection.root_cause_service, 1),
            _hit(level1, injection.root_cause_service, 3),
            _hit(hit.baseline, injection.root_cause_service, 1),
            _hit(hit.baseline, injection.root_cause_service, 3),
        )
        by_type[injection.fault_type]["level1_hit1"] += int(row[0])
        by_type[injection.fault_type]["baseline_hit1"] += int(row[2])
        rows.append(row)
    out = _hit_stats(rows, n_boot, seed)
    out["injections"] = len(injections)
    out["with_labelled_incident"] = len(first)
    out["only_in_ambiguous_incidents"] = len(ambiguous_only - set(first))
    out["without_alert"] = len(injections) - len(first) - out["only_in_ambiguous_incidents"]
    out["by_fault_type"] = {k: dict(v) for k, v in sorted(by_type.items())}
    return out


def select_sign(default: Sign, paired: Mapping[str, Any]) -> tuple[Sign, str]:
    """Abnormal-sign rule of level 1, fixed before the val numbers (QD-040).

    `alert` (only CTAV-confirmed services count as abnormal) is the default: it does not depend
    on how many candidates the detector raises. `candidate` replaces it only when its Hit@1 on
    labelled incidents is higher with a paired bootstrap CI95 lower bound > 0. Inside the CI, or
    tied, the default stays."""
    ci = paired.get("d_hit1_ci95")
    if default == "alert" and ci is not None and ci[0] > 0:
        return "candidate", "Hit@1(candidate) - Hit@1(alert) CI95 lower bound > 0"
    return default, "default kept; d_Hit@1(candidate - alert) CI95 lower bound is not > 0"


def paired_sign(a: Sequence[Located], b: Sequence[Located], n_boot: int, seed: int) -> dict[str, Any]:
    """Hit@1 of ranking `b` minus ranking `a` over the same labelled incidents."""
    rows = [
        (
            float(_hit([r.service for r in y.level1], y.labelled.root_cause, 1)),
            float(_hit([r.service for r in x.level1], x.labelled.root_cause, 1)),
        )
        for x, y in zip(a, b, strict=True)
        if x.labelled.status == "labelled"
    ]
    if not rows:
        return {"n": 0, "d_hit1": None, "d_hit1_ci95": None}
    return {
        "n": len(rows),
        "d_hit1": _mean([p - q for p, q in rows]),
        "d_hit1_ci95": list(bootstrap_ci(rows, lambda rs: _mean([p - q for p, q in rs]), n_boot, seed)),
    }


# --- one T_group ---------------------------------------------------------------------------


def _describe_incidents(labelled: Sequence[Labelled]) -> dict[str, Any]:
    sizes = [len(x.incident.alert_ids) for x in labelled]
    status = Counter(x.status for x in labelled)
    return {
        "incidents": len(labelled),
        "labelled": status["labelled"],
        "ambiguous": status["ambiguous"],
        "no_fault": status["no_fault"],
        "multi_service": sum(1 for x in labelled if len(x.incident.services) > 1),
        "multi_alert": sum(1 for s in sizes if s > 1),
        "max_alerts": max(sizes, default=0),
        "labelled_by_fault_type": dict(sorted(Counter(x.fault_type for x in labelled if x.status == "labelled").items())),
    }


def evaluate(config: Mapping[str, Any], results: Path) -> tuple[dict[str, Any], list[Located], Inputs, ServiceGraph]:
    n_boot, seed = int(config.get("n_boot", 1000)), int(config.get("seed", 42))
    labels = config.get("labels") or {}
    window_seconds = float(labels.get("window_seconds", 60))
    cascade_min = int(labels.get("cascade_min_services", 2))
    grouping, propagation = config["grouping"], config["propagation"]
    default_t = float(grouping["t_group_seconds"])
    grid = sorted({float(t) for t in grouping.get("sweep") or [default_t]})
    pad = float(propagation.get("sign_pad_seconds", window_seconds))
    default_sign: Sign = propagation.get("sign", "alert")

    inputs = load_inputs(config, results)
    graph = load_graph()
    injections = load_injections({r["window_id"] for r in inputs.rows}, window_seconds)
    by_injection = {i.injection_id: i for i in injections}
    membership = {a.alert_id: alert_injections(a, injections, window_seconds) for a in inputs.alerts}
    alerts_by_id = {a.alert_id: a for a in inputs.alerts}
    score_of_window = {r["window_id"]: float(r["anomaly_score"] or 0.0) for r in inputs.rows}
    alert_scores = {a.alert_id: score_of_window[a.window_id] for a in inputs.alerts}
    series = ServiceSeries(inputs.rows)
    sets = alert_sets(inputs.alerts, membership, by_injection, cascade_min)

    run_id = str(config["run_id"])
    incidents_by_t = {t: group_alerts(inputs.alerts, graph, run_id, t) for t in grid}
    labelled_by_t = {t: label_incidents(incidents_by_t[t], membership, by_injection) for t in grid}
    ambiguous = {t: sum(1 for x in labelled_by_t[t] if x.status == "ambiguous") for t in grid}
    units = time_clusters(inputs.alerts, max(grid))
    reference = reference_t_group(grid, default_t, ambiguous)
    reduction = reduction_table(units, incidents_by_t, sets, reference, n_boot, seed)

    fault_alerts = len(sets["fault"])
    report: dict[str, Any] = {
        "created_at": datetime.now(UTC).isoformat(),
        "config": dict(config),
        "input": inputs.source,
        "split": config["split"],
        "alerts": len(inputs.alerts),
        "alerts_in_a_fault": fault_alerts,
        "alerts_outside_any_fault": len(inputs.alerts) - fault_alerts,
        "alerted_services": len({a.service for a in inputs.alerts}),
        "injections": len(injections),
        "injections_by_fault_type": dict(sorted(Counter(i.fault_type for i in injections).items())),
        "cascade_injections": len({i for a in sets["cascade"] for i in membership[a]}),
        "resampling_units": len(units),
        "n_boot": n_boot,
        "seed": seed,
        "reduction": reduction,
    }

    if len(grid) > 1:
        selected_t, reason = select_t_group(grid, default_t, ambiguous, reduction["fault"])
        report["t_group_selection"] = {
            "grid": grid, "default": default_t, "reference": reference, "ambiguous": {str(int(t)): n for t, n in ambiguous.items()},
            "selected": selected_t, "reason": reason, "applied": bool(grouping.get("apply_selection", False)),
        }  # fmt: skip
        t_group = selected_t if grouping.get("apply_selection", False) else default_t
    else:
        t_group = default_t
    report["t_group_seconds"] = t_group

    per_t: dict[str, Any] = {}
    located_by: dict[tuple[float, str], list[Located]] = {}
    signs: list[Sign] = list(dict.fromkeys([default_sign, *(propagation.get("sweep") or [])]))
    for t in grid:
        entry: dict[str, Any] = _describe_incidents(labelled_by_t[t])
        for sign in signs:
            located = [locate(x, alerts_by_id, alert_scores, graph, series, sign, pad) for x in labelled_by_t[t]]
            located_by[(t, sign)] = located
            entry[f"hit_{sign}"] = hit_table(located, n_boot, seed)
            entry[f"per_injection_{sign}"] = injection_table(located, injections, n_boot, seed)
        per_t[str(int(t))] = entry
    report["by_t_group"] = per_t

    sign = default_sign
    if len(signs) > 1:
        paired = paired_sign(located_by[(t_group, "alert")], located_by[(t_group, "candidate")], n_boot, seed)
        selected_sign, reason = select_sign(default_sign, paired)
        report["sign_selection"] = {
            "candidates": signs, "default": default_sign, "paired_candidate_minus_alert": paired,
            "selected": selected_sign, "reason": reason, "applied": bool(propagation.get("apply_selection", False)),
        }  # fmt: skip
        if propagation.get("apply_selection", False):
            sign = selected_sign
    report["sign"] = sign
    final = located_by[(t_group, sign)]
    report["main"] = {
        "t_group_seconds": t_group,
        "sign": sign,
        **per_t[str(int(t_group))],
        "hit": per_t[str(int(t_group))][f"hit_{sign}"],
        "per_injection": per_t[str(int(t_group))][f"per_injection_{sign}"],
        "reduction": {name: values[str(int(t_group))] for name, values in reduction.items()},
        "level1_top1_differs_from_baseline": sum(
            1 for x in final if x.level1 and x.baseline and x.level1[0].service != x.baseline[0]
        ),
        "level1_top1_not_alerted": sum(1 for x in final if x.level1 and not x.level1[0].alerted),
    }
    return report, final, inputs, graph


# --- summaries -----------------------------------------------------------------------------


def incident_evidence(
    item: Located, alerts_by_id: Mapping[str, JudgedAlert], evidence: Mapping[str, Mapping[str, ContextEvent]]
) -> list[ContextEvent]:
    """Events cited by the incident's alerts, without duplicates: root-cause service first, then alert order."""
    seen: dict[str, ContextEvent] = {}
    for alert_id in item.labelled.incident.alert_ids:
        alert = alerts_by_id[alert_id]
        for event_id in alert.evidence_event_ids:
            event = evidence.get(alert.window_id, {}).get(event_id)
            if event is not None and event_id not in seen:
                seen[event_id] = event
    root = item.level1[0].service if item.level1 else None
    return sorted(seen.values(), key=lambda e: e.service != root)  # stable: keeps alert order


def build_backend(spec: Mapping[str, Any]) -> SummaryBackend:
    if spec.get("backend", "mock") == "mock":
        return MockSummaryBackend()
    if spec["backend"] != "gemini":
        raise ValueError("summarizer.backend must be mock or gemini")
    model = str(spec.get("model", JUDGE_MODEL))
    if model != JUDGE_MODEL:
        raise ValueError(f"summarizer.model must be the judge model {JUDGE_MODEL} (QD-013, QD-021)")
    return GeminiSummaryBackend(ResponseCache(LLM_CACHE), model, int(spec["max_output_tokens"]),
                                max_calls_per_minute=int(spec.get("max_calls_per_minute", 60)))  # fmt: skip


def summarize(
    config: Mapping[str, Any], located: Sequence[Located], inputs: Inputs, graph: ServiceGraph, results: Path
) -> tuple[dict[str, Any], list[SummaryResult]]:
    spec = config["summarizer"]
    if spec.get("prompt_version") != PROMPT_VERSION or spec.get("prompt_fingerprint") != prompt_fingerprint():
        raise ValueError(
            f"summarizer prompt is {PROMPT_VERSION} / {prompt_fingerprint()}, the config pins "
            f"{spec.get('prompt_version')} / {spec.get('prompt_fingerprint')}"
        )
    backend = build_backend(spec)
    summarizer = Summarizer(
        backend, graph, bool(spec.get("require_evidence", True)), int(spec.get("max_evidence", 12)),
        int(spec.get("excerpt_chars", 240)),
    )  # fmt: skip
    alerts_by_id = {a.alert_id: a for a in inputs.alerts}
    evidence = load_evidence(results, config["input"]["evidence_run"], {a.window_id for a in inputs.alerts})
    price_in, price_out = PRICES_PER_1M.get(backend.name, (0.0, 0.0))
    jobs = []
    for item in located:
        incident = item.labelled.incident
        alerts = [alerts_by_id[i] for i in incident.alert_ids]
        jobs.append((item, alerts, propagation_path(item.level1, graph), incident_evidence(item, alerts_by_id, evidence)))

    # Budget rule 1 (CURRENT-MILESTONE.md): estimate the new calls before any of them is made.
    new_calls, estimate = 0, 0.0
    if isinstance(backend, GeminiSummaryBackend):
        for item, alerts, path, events in jobs:
            if not item.level1 or not events:
                continue
            shown = events[: summarizer.max_evidence]
            services = set(item.labelled.incident.services) | {r.service for r in item.level1[:3]}
            edges = sorted((a, b) for a, b in graph.directed.edges if a in services and b in services)
            prompt = compose_prompt(item.labelled.incident, alerts, item.level1, path, shown, edges, summarizer.excerpt_chars)
            if backend.cache.get(backend.cache_key(prompt)) is None:
                new_calls += 1
                estimate += len(prompt) / 3.0 / 1e6 * price_in + backend.max_output_tokens / 1e6 * price_out
        budget = float(spec.get("budget_usd", 0.0))
        if estimate > budget:
            raise SystemExit(f"summarizer: {new_calls} new calls, worst case {estimate:.3f} USD > budget {budget} USD")
        print(f"summarizer: {new_calls} new calls, worst case {estimate:.4f} USD (budget {budget} USD)")

    stop = float(spec.get("stop_usd", math.inf))
    outputs: list[SummaryResult] = []
    spent = 0.0
    for item, alerts, path, events in jobs:
        started = time.perf_counter()
        result = summarizer.summarize(item.labelled.incident, alerts, item.level1, path, events)
        result.debug["latency_ms"] = item.elapsed_ms + (time.perf_counter() - started) * 1000.0
        if result.debug.get("actual_api_call"):
            spent += (
                result.debug["prompt_tokens"] / 1e6 * price_in + result.debug["completion_tokens"] / 1e6 * price_out
            )
        outputs.append(result)
        if spent > stop:
            raise SystemExit(f"summarizer: spent {spent:.3f} USD > stop threshold {stop} USD -- stopped")

    called = [r for r in outputs if r.llm_called]
    valid = [r for r in called if r.valid]
    flags = [float(r.valid) for r in called]
    reasons = Counter((r.reject_reason or "").split(":")[0] for r in outputs if not r.valid)
    stats = {
        "backend": backend.name,
        "prompt_version": PROMPT_VERSION,
        "prompt_fingerprint": prompt_fingerprint(),
        "incidents": len(outputs),
        "llm_calls": len(called),
        "not_called": len(outputs) - len(called),
        "valid": len(valid),
        "json_valid_rate": len(valid) / len(called) if called else None,
        "json_valid_rate_ci95": list(bootstrap_ci(flags, _mean, int(config.get("n_boot", 1000)), int(config.get("seed", 42)))) if called else None,  # fmt: skip
        "rejected_by_reason": dict(sorted(reasons.items())),
        "suspicious": sum(1 for r in valid if r.suspicious),
        "reports_with_invented_evidence_ids": sum(1 for r in called if r.invalid_evidence_ids),
        "fault_type_reported": dict(sorted(Counter(r.report.fault_type for r in valid if r.report).items())),
        "new_api_calls": sum(1 for r in outputs if r.debug.get("actual_api_call")),
        "cache_hits": sum(1 for r in outputs if r.debug.get("cache_hit")),
        "prompt_tokens_new": sum(r.debug.get("prompt_tokens", 0) for r in outputs if r.debug.get("actual_api_call")),
        "completion_tokens_new": sum(r.debug.get("completion_tokens", 0) for r in outputs if r.debug.get("actual_api_call")),  # fmt: skip
        "estimated_usd_by_tokens": spent,
        "latency_ms_median": float(np.median([r.debug["latency_ms"] for r in outputs])) if outputs else None,
    }
    return stats, outputs


# --- outputs -------------------------------------------------------------------------------


def incident_record(item: Located) -> dict[str, Any]:
    incident = item.labelled.incident
    level1 = [r.service for r in item.level1]
    truth = item.labelled.root_cause
    return {
        **incident.model_dump(mode="json"),
        "status": item.labelled.status,
        "injection_ids": item.labelled.injection_ids,
        "fault_type": item.labelled.fault_type,
        "root_cause": truth,
        "level1": [
            {"service": r.service, "score": r.score, "anomaly_score": r.anomaly_score, "alerted": r.alerted,
             "blamed_by": list(r.blamed_by)}
            for r in item.level1
        ],  # fmt: skip
        "baseline": item.baseline,
        "level1_hit1": _hit(level1, truth, 1) if truth else None,
        "level1_hit3": _hit(level1, truth, 3) if truth else None,
        "baseline_hit1": _hit(item.baseline, truth, 1) if truth else None,
        "baseline_hit3": _hit(item.baseline, truth, 3) if truth else None,
    }


def write(
    report: Mapping[str, Any],
    located: Sequence[Located],
    summaries: Sequence[SummaryResult] | None,
    out_dir: Path,
    config_text: str,
) -> None:
    if out_dir.exists():
        raise SystemExit(f"{out_dir} already exists: results are never overwritten, use a new run_id")
    out_dir.mkdir(parents=True)
    (out_dir / "rca.json").write_text(json.dumps(report, indent=2, allow_nan=False, default=str), encoding="utf-8")
    (out_dir / "config.snapshot.yaml").write_text(config_text, encoding="utf-8")
    with (out_dir / "incidents.jsonl").open("w", encoding="utf-8") as handle:
        for item in located:
            handle.write(json.dumps(incident_record(item), ensure_ascii=False) + "\n")
    if summaries is not None:
        with (out_dir / "reports.jsonl").open("w", encoding="utf-8") as reports, (
            out_dir / "rejected.jsonl"
        ).open("w", encoding="utf-8") as rejected:
            for result in summaries:
                if result.report is not None:
                    record = {"suspicious": result.suspicious, "invalid_evidence_ids": result.invalid_evidence_ids,
                              "debug": result.debug, "report": result.report.model_dump(mode="json")}  # fmt: skip
                    reports.write(json.dumps(record, ensure_ascii=False) + "\n")
                else:
                    record = {"incident_id": result.incident_id, "reject_reason": result.reject_reason,
                              "llm_called": result.llm_called, "raw_output": result.raw_output, "debug": result.debug}  # fmt: skip
                    rejected.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_postgres(
    config: Mapping[str, Any],
    config_text: str,
    git_commit: str,
    started_at: datetime,
    located: Sequence[Located],
    summaries: Sequence[SummaryResult] | None,
) -> dict[str, int]:
    """One transaction: run_registry + incidents (+ diagnostic_reports / diagnostic_rejected)."""
    from services.rca_agent import store

    run_id = str(config["run_id"])
    with store.connect() as conn:
        store.register_run(conn, run_id, config_text, git_commit, str(config["split"]), int(config.get("seed", 42)),
                           started_at, notes="py -m eval rca")  # fmt: skip
        store.insert_incidents(conn, [item.labelled.incident for item in located])
        for result in summaries or []:
            if result.report is not None:
                store.insert_report(conn, result.report, result.suspicious, result.debug.get("latency_ms"))
            else:
                store.insert_rejected(conn, result.incident_id, run_id, result.raw_output, result.reject_reason or "")
        store.finish_run(conn, run_id, datetime.now(UTC))
        conn.commit()
        return store.counts(conn, run_id)


def config_fingerprint(config: Mapping[str, Any]) -> str:
    """Hash of the method parameters only (grouping, propagation, labels, summarizer, n_boot, seed):
    the val run and the test run of one frozen method must print the same value."""
    keys = ("grouping", "propagation", "labels", "summarizer", "n_boot", "seed")
    fixed = json.dumps({k: config.get(k) for k in keys}, sort_keys=True)
    return hashlib.sha256(fixed.encode("utf-8")).hexdigest()[:16]


def _pct(value: float | None) -> str:
    return "   n/a" if value is None else f"{value:6.3f}"


def _range(ci: Sequence[float] | None) -> str:
    return "[n/a]" if ci is None else f"[{ci[0]:.3f}; {ci[1]:.3f}]"


def table(report: Mapping[str, Any]) -> str:
    lines = [
        f"[input] {report['input']}: {report['alerts']} alerts ({report['alerts_in_a_fault']} inside a fault, "
        f"{report['alerts_outside_any_fault']} outside), {report['injections']} injections, "
        f"{report['cascade_injections']} cascade"
    ]
    for t, entry in report["by_t_group"].items():
        lines.append(
            f"[T={t}] incidents={entry['incidents']} labelled={entry['labelled']} ambiguous={entry['ambiguous']} "
            f"no_fault={entry['no_fault']} multi_service={entry['multi_service']}"
        )
        for name, values in report["reduction"].items():
            v = values[t]
            if v["alerts"]:
                lines.append(f"    ARR {name:22s} {v['alerts']:3d} alerts -> {v['incidents']:3d} incidents  "
                             f"{_pct(v['arr'])} {_range(v['arr_ci95'])}")  # fmt: skip
        for key in sorted(k for k in entry if k.startswith("hit_")):
            h = entry[key]
            lines.append(
                f"    {key:14s} n={h['n']} L1 Hit@1={_pct(h['level1_hit1'])} {_range(h['level1_hit1_ci95'])} "
                f"Hit@3={_pct(h['level1_hit3'])} {_range(h['level1_hit3_ci95'])} | base Hit@1={_pct(h['baseline_hit1'])} "
                f"{_range(h['baseline_hit1_ci95'])} Hit@3={_pct(h['baseline_hit3'])} | dHit@1={_pct(h['d_hit1'])} "
                f"{_range(h['d_hit1_ci95'])}"
            )
    for key in ("t_group_selection", "sign_selection"):
        if key in report:
            lines.append(f"[{key}] selected {report[key]['selected']} ({report[key]['reason']}); applied={report[key]['applied']}")
    main = report["main"]
    p = main["per_injection"]
    lines.append(
        f"[main] T_group={main['t_group_seconds']:.0f}s sign={main['sign']}; per injection: {p['with_labelled_incident']}/"
        f"{p['injections']} with a labelled incident, Hit@1={_pct(p['level1_hit1'])} Hit@3={_pct(p['level1_hit3'])} "
        f"(baseline {_pct(p['baseline_hit1'])} / {_pct(p['baseline_hit3'])})"
    )
    if "summarizer" in report:
        s = report["summarizer"]
        lines.append(
            f"[summarizer] backend={s['backend']} calls={s['llm_calls']} valid={s['valid']} "
            f"JSON valid rate={_pct(s['json_valid_rate'])} {_range(s['json_valid_rate_ci95'])} rejected={s['rejected_by_reason']} "
            f"new_api_calls={s['new_api_calls']} usd={s['estimated_usd_by_tokens']:.4f}"
        )
    return "\n".join(lines)
