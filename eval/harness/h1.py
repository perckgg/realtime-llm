"""H1 -- mechanism of confirmation bias (M5, QD-027).

H0 (QD-026, finding 7): C1 raised recall and FPR over BM25 without neighbour
evidence; it picked local trace spans closer to the window. H1 tests that
causally: the same candidate is judged with six evidence events chosen to vary
one factor at a time, everything else fixed.

Conditions per candidate (k = 6 events, all of s0 unless stated):

- ``ref``: C1-paper top-6 exactly as in H0 (same prompt => cache hit; checks the
  builder against H0 byte for byte).
- ``ref_flat``: the same events with the per-event ``score`` shown in the prompt
  fixed by position (FLAT_SCORES). C1 shows its Fusion score, which itself
  depends on time proximity; every constructed condition below uses the flat
  scores, so ``ref`` vs ``ref_flat`` measures the score display alone.
- ``order_rev``: ``ref`` events in reverse order, flat scores.
- ``time_0`` / ``time_33`` / ``time_67`` / ``near_trace``: share of trace spans
  with |t - t0| <= ``near_s`` among six trace spans = 0, 2/6, 4/6, 6/6; the rest
  have ``far_min_s`` <= |t - t0|. ``near_trace`` is the 100 % level.
- ``near_log``: six log lines with |t - t0| <= ``near_s`` (vs ``near_trace``).
- ``neighbor_trace``: six trace spans of services 1..2 hops from s0 with
  |t - t0| <= ``near_s`` (negative control vs ``near_trace``).

Events inside a bin are drawn at random and every constructed list is shuffled,
both seeded by (seed, candidate_id, condition), so the draw is reproducible and
position is not tied to the factor. A condition is built only when the
candidate has enough events in every bin it needs (``feasible`` flags).
"""

from __future__ import annotations

import gzip
import json
import math
import random
from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from eval.harness.stats import bootstrap_ci, mcnemar_exact
from packages.schemas.evidence import EvidenceDoc, NezhaEvidenceStore
from packages.schemas.models import AlertCandidate, ContextEvent, JudgedAlert, RetrievalResult
from services.retrieval.hybrid_bm25_graph import HybridBm25GraphRetriever
from services.retrieval.registry import build_budget, build_strategy

K = 6
FLAT_SCORES = (0.95, 0.94, 0.93, 0.92, 0.91, 0.90)
TIME_LEVELS = {"time_0": 0, "time_33": 2, "time_67": 4, "near_trace": 6}
CONDITIONS = ("ref", "ref_flat", "order_rev", *TIME_LEVELS, "near_log", "neighbor_trace")


@dataclass(frozen=True)
class Params:
    near_s: float = 60.0
    far_min_s: float = 180.0
    seed: int = 42

    @classmethod
    def from_config(cls, spec: Mapping[str, Any] | None) -> Params:
        spec = spec or {}
        params = cls(
            near_s=float(spec.get("near_s", cls.near_s)),
            far_min_s=float(spec.get("far_min_s", cls.far_min_s)),
            seed=int(spec.get("seed", cls.seed)),
        )
        if not 0 < params.near_s < params.far_min_s:
            raise ValueError("need 0 < near_s < far_min_s")
        return params


def flat(events: Sequence[ContextEvent]) -> list[ContextEvent]:
    """Same events, prompt score fixed by position (FLAT_SCORES)."""
    if len(events) > len(FLAT_SCORES):
        raise ValueError(f"at most {len(FLAT_SCORES)} events")
    return [
        e.model_copy(update={"score": s, "debug": {**e.debug, "prompt_score": s}})
        for e, s in zip(events, FLAT_SCORES, strict=False)
    ]


def doc_event(doc: EvidenceDoc, distance: int, t0: datetime, start: datetime, end: datetime) -> ContextEvent:
    """An EvidenceDoc as the prompt sees it (the fields `context_payload` reads), score set later by `flat`."""
    if start <= doc.ts <= end:
        time_distance = 0.0
    else:
        time_distance = min(abs((doc.ts - start).total_seconds()), abs((doc.ts - end).total_seconds()))
    return ContextEvent(
        event_id=doc.doc_id,
        modality=doc.modality,
        ts=doc.ts,
        service=doc.service,
        content=doc.message,
        score=0.0,
        origin="local" if distance == 0 else "graph",
        graph_distance=distance,
        debug={
            "abs_dt_s": abs((doc.ts - t0).total_seconds()),
            "time_distance_sec": time_distance,
            "pod": doc.pod,
            "severity": doc.severity,
            "event_type": doc.event_type,
            "source": doc.source,
            "trace_id": doc.trace_id,
            "span_id": doc.span_id,
            "parent_span_id": doc.parent_span_id,
            "duration_ms": doc.duration_ms,
        },
    )


def _rng(params: Params, candidate_id: str, name: str) -> random.Random:
    return random.Random(f"{params.seed}:{candidate_id}:{name}")


def _draw(items: Sequence[ContextEvent], params: Params, candidate_id: str, name: str) -> list[ContextEvent]:
    return _rng(params, candidate_id, name).sample(list(items), K)


def _shuffled(items: Sequence[ContextEvent], params: Params, candidate_id: str, name: str) -> list[ContextEvent]:
    out = list(items)
    _rng(params, candidate_id, f"order:{name}").shuffle(out)
    return out


def build_conditions(
    candidate_id: str,
    ref: Sequence[ContextEvent],
    local: Iterable[ContextEvent],
    neighbors: Iterable[ContextEvent],
    params: Params,
) -> tuple[dict[str, list[ContextEvent]], dict[str, Any]]:
    """All feasible conditions of one candidate + bin counts / feasibility flags.

    `local` / `neighbors` carry `debug["abs_dt_s"]` (from `doc_event`)."""
    def near(e: ContextEvent) -> bool:
        return float(e.debug["abs_dt_s"]) <= params.near_s

    def far(e: ContextEvent) -> bool:
        return float(e.debug["abs_dt_s"]) >= params.far_min_s

    local = list(local)
    neighbors = list(neighbors)
    near_trace = [e for e in local if e.modality == "trace" and near(e)]
    far_trace = [e for e in local if e.modality == "trace" and far(e)]
    near_log = [e for e in local if e.modality == "log" and near(e)]
    nb_trace = [e for e in neighbors if e.modality == "trace" and near(e)]
    counts = {
        "ref": len(ref),
        "near_trace": len(near_trace),
        "far_trace": len(far_trace),
        "near_log": len(near_log),
        "neighbor_near_trace": len(nb_trace),
    }
    feasible = {
        "ref": len(ref) == K,
        "time": len(near_trace) >= K and len(far_trace) >= K,
        "near_trace": len(near_trace) >= K,
        "near_log": len(near_trace) >= K and len(near_log) >= K,
        "neighbor_trace": len(near_trace) >= K and len(nb_trace) >= K,
    }
    out: dict[str, list[ContextEvent]] = {}
    if ref:
        out["ref"] = list(ref)
        out["ref_flat"] = flat(ref)
        out["order_rev"] = flat(list(reversed(ref)))
    if feasible["near_trace"]:
        near_draw = _draw(near_trace, params, candidate_id, "near_trace")
        out["near_trace"] = flat(_shuffled(near_draw, params, candidate_id, "near_trace"))
        if feasible["time"]:
            far_draw = _draw(far_trace, params, candidate_id, "far_trace")
            for name, n_near in TIME_LEVELS.items():
                if name == "near_trace":
                    continue
                mix = near_draw[:n_near] + far_draw[: K - n_near]
                out[name] = flat(_shuffled(mix, params, candidate_id, name))
        if feasible["near_log"]:
            out["near_log"] = flat(_shuffled(_draw(near_log, params, candidate_id, "near_log"), params, candidate_id, "near_log"))
        if feasible["neighbor_trace"]:
            draw = _draw(nb_trace, params, candidate_id, "neighbor_trace")
            out["neighbor_trace"] = flat(_shuffled(draw, params, candidate_id, "neighbor_trace"))
    return out, {"counts": counts, "feasible": feasible}


# ---------------------------------------------------------------- collect (no LLM)

_WORKER: dict[str, Any] = {}


def _init_worker(retrieval_config: dict[str, Any], params: Params) -> None:
    store = NezhaEvidenceStore()
    base = build_strategy(retrieval_config, store)
    if not isinstance(base, HybridBm25GraphRetriever):
        raise ValueError("H1 needs retrieval.type = hybrid_bm25_graph (the C1 reference of H0)")
    _WORKER.update(store=store, base=base, budget=build_budget(retrieval_config), params=params)


def _one(candidate: AlertCandidate) -> dict[str, Any]:
    base: HybridBm25GraphRetriever = _WORKER["base"]
    store: NezhaEvidenceStore = _WORKER["store"]
    params: Params = _WORKER["params"]
    ref = base.retrieve(candidate, _WORKER["budget"]).events
    start = candidate.ts
    end = candidate.end_ts or candidate.ts + base.window
    t0 = start + (end - start) / 2
    lo, hi = start - base.time_margin, end + base.time_margin
    hops = base.graph.distances(candidate.service, 2)
    neighbor_services = {s for s, d in hops.items() if d >= 1}
    local = [doc_event(d, 0, t0, start, end) for d in store.query(lo, hi, {candidate.service})]
    neighbors = [
        doc_event(d, hops[d.service], t0, start, end) for d in store.query(lo, hi, neighbor_services)
    ] if neighbor_services else []
    conditions, meta = build_conditions(candidate.candidate_id, ref, local, neighbors, params)
    return {
        "conditions": {name: [e.model_dump(mode="json") for e in events] for name, events in conditions.items()},
        **meta,
    }


def _chunk(candidates: list[AlertCandidate]) -> list[dict[str, Any]]:
    return [_one(c) for c in candidates]


def build_sample(
    retrieval_config: dict[str, Any], candidates: Sequence[AlertCandidate], params: Params, workers: int
) -> list[dict[str, Any]]:
    """`_one` for every candidate on `workers` processes (contiguous time-ordered chunks), in input order."""
    if not candidates:
        return []
    if workers <= 1:
        _init_worker(retrieval_config, params)
        return _chunk(list(candidates))
    n_chunks = min(len(candidates), workers * 4)
    size = -(-len(candidates) // n_chunks)
    chunks = [list(candidates[i : i + size]) for i in range(0, len(candidates), size)]
    with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker, initargs=(retrieval_config, params)) as pool:
        return [row for part in pool.map(_chunk, chunks) for row in part]


def write_sample(path: Path, rows: Sequence[Mapping[str, Any]], meta: Mapping[str, Any]) -> None:
    if path.exists():
        raise SystemExit(f"{path} already exists: samples are never overwritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump({"meta": dict(meta), "rows": list(rows)}, handle, ensure_ascii=False)


def read_sample(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        data = json.load(handle)
    return data["meta"], data["rows"]


def feasibility(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    """How many candidates (normal / fault) each condition could be built for."""
    out: dict[str, dict[str, int]] = {}
    for name in CONDITIONS:
        out[name] = {
            "normal": sum(1 for r in rows if not r["is_fault"] and name in r["conditions"]),
            "fault": sum(1 for r in rows if r["is_fault"] and name in r["conditions"]),
        }
    return out


# ---------------------------------------------------------------- judge jobs

def jobs_for(rows: Sequence[Mapping[str, Any]], condition: str) -> list[tuple[AlertCandidate, RetrievalResult, bool]]:
    """(candidate, context, is_fault) for every sample row that has `condition`."""
    out = []
    for row in rows:
        events = row["conditions"].get(condition)
        if not events:
            continue
        context = RetrievalResult(
            strategy=f"h1_{condition}",
            events=[ContextEvent.model_validate(e) for e in events],
            latency_ms=0.0,
            token_estimate=0,
        )
        out.append((AlertCandidate.model_validate(row["candidate"]), context, bool(row["is_fault"])))
    return out


def result_row(condition: str, is_fault: bool, judged: JudgedAlert) -> dict[str, Any]:
    d = judged.debug
    return {
        "candidate_id": judged.candidate_id,
        "condition": condition,
        "is_fault": is_fault,
        "raw_verdict": judged.raw_verdict,
        "verdict": judged.verdict,
        "confidence": judged.confidence,
        "evidence_event_ids": judged.evidence_event_ids,
        "status": d.get("status"),
        "error": d.get("error"),
        "cache_hit": judged.cache_hit,
        "actual_api_call": bool(d.get("actual_api_call")),
        "prompt_tokens": d.get("prompt_tokens"),
        "completion_tokens": d.get("completion_tokens"),
    }


# ---------------------------------------------------------------- analysis

# (condition, baseline): the one factor that differs between them
PAIRS = (
    ("ref_flat", "ref"),  # score display
    ("order_rev", "ref_flat"),  # order
    ("time_0", "near_trace"),  # time proximity
    ("time_33", "near_trace"),
    ("time_67", "near_trace"),
    ("near_log", "near_trace"),  # modality
    ("neighbor_trace", "near_trace"),  # graph distance (negative control)
)
TIME_SHARE = {"time_0": 0.0, "time_33": 2 / 6, "time_67": 4 / 6, "near_trace": 1.0}
GATE_THETAS = (0.80, 0.85, 0.90, 0.95)  # C2 candidates: raw TRUE_ALERT with confidence >= theta


def _rate(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else math.nan


def _mean_diff(pairs: Sequence[tuple[int, int]]) -> float:
    return _rate([a - b for a, b in pairs])


def _slope(groups: Sequence[Sequence[tuple[float, int]]]) -> float:
    xy = [p for g in groups for p in g]
    mx = _rate([x for x, _ in xy])
    my = _rate([y for _, y in xy])
    var = sum((x - mx) ** 2 for x, _ in xy)
    return sum((x - mx) * (y - my) for x, y in xy) / var if var else math.nan


def analyze(results: Mapping[str, Sequence[Mapping[str, Any]]], seed: int = 42) -> dict[str, Any]:
    """Rates of raw TRUE_ALERT (the judge's own label) and of routed alerts (verdict after the
    decision rules) per condition and label, paired differences vs the baseline of each
    PAIRS entry (bootstrap over candidates + exact McNemar), and the time-proximity slope."""
    by: dict[str, dict[str, Mapping[str, Any]]] = {c: {r["candidate_id"]: r for r in rows} for c, rows in results.items()}
    report: dict[str, Any] = {"conditions": {}, "pairs": [], "time_trend": {}}
    for cond, rows in by.items():
        entry: dict[str, Any] = {}
        for label, is_fault in (("normal", False), ("fault", True)):
            sub = [r for r in rows.values() if r["is_fault"] == is_fault]
            raw = [int(r["raw_verdict"] == "TRUE_ALERT") for r in sub]
            routed = [int(r["verdict"] == "TRUE_ALERT") for r in sub]
            entry[label] = {
                "n": len(sub),
                "raw_true": _rate(raw),
                "raw_true_ci95": list(bootstrap_ci(raw, _rate, seed=seed)) if raw else None,
                "routed": _rate(routed),
                "routed_ci95": list(bootstrap_ci(routed, _rate, seed=seed)) if routed else None,
                "errors": sum(1 for r in sub if r.get("error")),
                "gate": {
                    f"{theta:.2f}": _rate(
                        [int(r["raw_verdict"] == "TRUE_ALERT" and (r.get("confidence") or 0) >= theta) for r in sub]
                    )
                    for theta in GATE_THETAS
                },
            }
        report["conditions"][cond] = entry
    for cond, base in PAIRS:
        if cond not in by or base not in by:
            continue
        for label, is_fault in (("normal", False), ("fault", True)):
            ids = sorted(i for i in by[cond] if i in by[base] and by[cond][i]["is_fault"] == is_fault)
            pairs = [
                (int(by[cond][i]["raw_verdict"] == "TRUE_ALERT"), int(by[base][i]["raw_verdict"] == "TRUE_ALERT"))
                for i in ids
            ]
            report["pairs"].append(
                {
                    "condition": cond,
                    "baseline": base,
                    "label": label,
                    "n": len(pairs),
                    "raw_true_condition": _rate([a for a, _ in pairs]),
                    "raw_true_baseline": _rate([b for _, b in pairs]),
                    "diff": _mean_diff(pairs),
                    "diff_ci95": list(bootstrap_ci(pairs, _mean_diff, seed=seed)) if pairs else None,
                    "mcnemar_p": mcnemar_exact([bool(a) for a, _ in pairs], [bool(b) for _, b in pairs]),
                }
            )
    if all(c in by for c in TIME_SHARE):
        for label, is_fault in (("normal", False), ("fault", True)):
            ids = sorted(
                i for i in by["near_trace"] if by["near_trace"][i]["is_fault"] == is_fault and all(i in by[c] for c in TIME_SHARE)
            )
            groups = [
                [(share, int(by[c][i]["raw_verdict"] == "TRUE_ALERT")) for c, share in TIME_SHARE.items()] for i in ids
            ]
            report["time_trend"][label] = {
                "n": len(groups),
                "slope_raw_true_per_share": _slope(groups),
                "slope_ci95": list(bootstrap_ci(groups, _slope, seed=seed)) if groups else None,
                "by_level": {c: _rate([g[k][1] for g in groups]) for k, c in enumerate(TIME_SHARE)},
            }
    return report


def _pooled_share(items: Sequence[tuple[int, int]]) -> float:
    total = sum(n for _, n in items)
    return sum(a for a, _ in items) / total if total else math.nan


def cited_near_share(
    results: Mapping[str, Sequence[Mapping[str, Any]]],
    rows: Sequence[Mapping[str, Any]],
    near_s: float,
    seed: int = 42,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Mixed-time conditions: share of near events among those a raw TRUE_ALERT cites, per label
    (2/6 and 4/6 of the prompt are near). Bootstrap over alerts."""
    conditions = {r["candidate"]["candidate_id"]: r["conditions"] for r in rows}
    report: dict[str, dict[str, dict[str, Any]]] = {}
    for cond in ("time_33", "time_67"):
        if cond not in results:
            continue
        report[cond] = {}
        for label, is_fault in (("normal", False), ("fault", True)):
            per_alert = []
            for r in results[cond]:
                if r["is_fault"] != is_fault or r["raw_verdict"] != "TRUE_ALERT":
                    continue
                events = {e["event_id"]: e for e in conditions[r["candidate_id"]].get(cond, [])}
                cited = [events[i] for i in r["evidence_event_ids"] if i in events]
                if cited:
                    per_alert.append((sum(1 for e in cited if float(e["debug"]["abs_dt_s"]) <= near_s), len(cited)))
            report[cond][label] = {
                "alerts": len(per_alert),
                "cited": sum(n for _, n in per_alert),
                "near_share": _pooled_share(per_alert),
                "near_share_ci95": list(bootstrap_ci(per_alert, _pooled_share, seed=seed)) if per_alert else None,
            }
    return report


def repeat_stability(
    runs: Mapping[str, Sequence[Sequence[Mapping[str, Any]]]], seed: int = 42
) -> dict[str, dict[str, dict[str, Any]]]:
    """Variance of the judge across `repeat` runs (QD-013), per condition and label, on the
    candidates present in every repeat: raw TRUE_ALERT rate of each repeat and the share of
    candidates whose raw TRUE_ALERT flag is not the same in all repeats."""
    report: dict[str, dict[str, dict[str, Any]]] = {}
    for cond, repeats in runs.items():
        by = [{r["candidate_id"]: r for r in rows} for rows in repeats]
        common = sorted(set.intersection(*(set(b) for b in by)))
        entry: dict[str, dict[str, Any]] = {}
        for label, is_fault in (("normal", False), ("fault", True)):
            ids = [i for i in common if by[0][i]["is_fault"] == is_fault]
            flags = [[int(b[i]["raw_verdict"] == "TRUE_ALERT") for b in by] for i in ids]
            flipped = [int(len(set(f)) > 1) for f in flags]
            entry[label] = {
                "n": len(ids),
                "repeats": len(by),
                "raw_true_by_repeat": [_rate([f[k] for f in flags]) for k in range(len(by))],
                "flip_rate": _rate(flipped),
                "flip_rate_ci95": list(bootstrap_ci(flipped, _rate, seed=seed)) if flipped else None,
            }
        report[cond] = entry
    return report
