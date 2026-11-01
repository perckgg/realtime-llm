"""H1 condition builder and analysis (M5, QD-027)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from eval.harness.h1 import (
    FLAT_SCORES,
    K,
    Params,
    analyze,
    build_conditions,
    cited_near_share,
    doc_event,
    flat,
    repeat_stability,
)
from packages.schemas.evidence import EvidenceDoc
from packages.schemas.models import ContextEvent

T0 = datetime(2022, 8, 22, 4, 0, 30, tzinfo=UTC)
START, END = T0 - timedelta(seconds=30), T0 + timedelta(seconds=30)


def _doc(i: int, dt: float, kind: str = "trace", service: str = "cartservice") -> EvidenceDoc:
    trace = kind == "trace"
    return EvidenceDoc(
        doc_id=f"{kind}-{service}-{i}",
        ts=T0 + timedelta(seconds=dt),
        pod=f"{service}-pod",
        service=service,
        severity="INFO",
        event_type="trace_span" if trace else "application_log",
        source="nezha_trace" if trace else "nezha_log",
        message=f"{kind} {i}",
        duration_ms=5.0 if trace else None,
    )


def _events(n: int, dt: float, kind: str = "trace", service: str = "cartservice", distance: int = 0) -> list[ContextEvent]:
    return [doc_event(_doc(i, dt + i, kind, service), distance, T0, START, END) for i in range(n)]


def _ref() -> list[ContextEvent]:
    return [e.model_copy(update={"debug": {**e.debug, "prompt_score": 0.99 - i / 100}}) for i, e in enumerate(_events(K, 5))]


def test_flat_fixes_prompt_score_by_position() -> None:
    out = flat(_ref())
    assert [e.debug["prompt_score"] for e in out] == list(FLAT_SCORES)
    assert [e.event_id for e in out] == [e.event_id for e in _ref()]
    with pytest.raises(ValueError):
        flat(_events(K + 1, 0))


def test_time_levels_hold_count_modality_and_mix_near_far() -> None:
    local = _events(8, 0) + _events(8, 200)  # 8 near (0..7 s), 8 far (200..207 s)
    conds, meta = build_conditions("c1", _ref(), local, [], Params())
    assert meta["feasible"]["time"] and not meta["feasible"]["near_log"]
    for name, n_near in (("time_0", 0), ("time_33", 2), ("time_67", 4), ("near_trace", 6)):
        events = conds[name]
        assert len(events) == K and {e.modality for e in events} == {"trace"}
        assert sum(1 for e in events if e.debug["abs_dt_s"] <= 60) == n_near
        assert [e.debug["prompt_score"] for e in events] == list(FLAT_SCORES)
    # the near events of a lower level are a subset of the 100 % level (nested draw)
    near_ids = {e.event_id for e in conds["near_trace"]}
    assert {e.event_id for e in conds["time_67"] if e.debug["abs_dt_s"] <= 60} <= near_ids
    assert "near_log" not in conds and "neighbor_trace" not in conds


def test_ref_order_and_feasibility_flags() -> None:
    local = _events(6, 0) + _events(6, 0, kind="log")
    neighbors = _events(6, 10, service="frontend", distance=1)
    conds, meta = build_conditions("c1", _ref(), local, neighbors, Params())
    assert [e.event_id for e in conds["ref"]] == [e.event_id for e in _ref()]
    assert conds["ref"][0].debug["prompt_score"] == 0.99  # untouched: same prompt as H0
    assert [e.event_id for e in conds["order_rev"]] == [e.event_id for e in reversed(_ref())]
    assert {e.modality for e in conds["near_log"]} == {"log"}
    assert {e.origin for e in conds["neighbor_trace"]} == {"graph"}
    assert not meta["feasible"]["time"] and "time_0" not in conds  # no far events


def test_build_is_deterministic_per_seed() -> None:
    local = _events(20, 0) + _events(20, 200)
    a, _ = build_conditions("c1", _ref(), local, [], Params(seed=42))
    b, _ = build_conditions("c1", _ref(), local, [], Params(seed=42))
    c, _ = build_conditions("c1", _ref(), local, [], Params(seed=7))
    assert [e.event_id for e in a["time_33"]] == [e.event_id for e in b["time_33"]]
    assert [e.event_id for e in a["time_33"]] != [e.event_id for e in c["time_33"]]


def test_params_validation() -> None:
    with pytest.raises(ValueError):
        Params.from_config({"near_s": 200, "far_min_s": 180})


def _rows(condition: str, raw: list[str], fault: bool = False) -> list[dict[str, object]]:
    return [
        {"candidate_id": f"c{i}", "condition": condition, "is_fault": fault, "raw_verdict": v, "verdict": v, "error": None}
        for i, v in enumerate(raw)
    ]


def test_analyze_paired_difference_and_time_slope() -> None:
    n = 40
    results = {
        "near_trace": _rows("near_trace", ["TRUE_ALERT"] * 30 + ["FALSE_POSITIVE"] * 10),
        "time_67": _rows("time_67", ["TRUE_ALERT"] * 25 + ["FALSE_POSITIVE"] * 15),
        "time_33": _rows("time_33", ["TRUE_ALERT"] * 20 + ["FALSE_POSITIVE"] * 20),
        "time_0": _rows("time_0", ["TRUE_ALERT"] * 10 + ["FALSE_POSITIVE"] * 30),
    }
    report = analyze(results)
    assert report["conditions"]["near_trace"]["normal"]["raw_true"] == 30 / n
    pair = next(p for p in report["pairs"] if p["condition"] == "time_0" and p["label"] == "normal")
    assert pair["n"] == n and pair["diff"] == pytest.approx(-20 / n)
    assert pair["diff_ci95"][1] < 0 and pair["mcnemar_p"] < 1e-4
    trend = report["time_trend"]["normal"]
    assert trend["n"] == n and trend["slope_raw_true_per_share"] > 0 and trend["slope_ci95"][0] > 0
    assert report["time_trend"]["fault"]["n"] == 0


def test_gate_counts_only_true_alerts_above_theta() -> None:
    rows = _rows("ref", ["TRUE_ALERT", "TRUE_ALERT", "FALSE_POSITIVE", "UNCERTAIN"])
    for row, confidence in zip(rows, (0.95, 0.85, 0.99, 0.99), strict=True):
        row["confidence"] = confidence
    gate = analyze({"ref": rows})["conditions"]["ref"]["normal"]["gate"]
    assert gate == {"0.80": 0.5, "0.85": 0.5, "0.90": 0.25, "0.95": 0.25}


def test_cited_near_share_pools_cited_events_of_true_alerts() -> None:
    sample = [
        {
            "candidate": {"candidate_id": f"c{i}"},
            "conditions": {
                "time_33": [
                    {"event_id": "near", "debug": {"abs_dt_s": 10}},
                    {"event_id": "far", "debug": {"abs_dt_s": 200}},
                ]
            },
        }
        for i in range(3)
    ]
    rows = _rows("time_33", ["TRUE_ALERT", "TRUE_ALERT", "FALSE_POSITIVE"])
    rows[0]["evidence_event_ids"] = ["near"]
    rows[1]["evidence_event_ids"] = ["near", "far"]
    rows[2]["evidence_event_ids"] = ["near"]  # not an alert: ignored
    report = cited_near_share({"time_33": rows}, sample, 60.0)["time_33"]
    assert report["normal"]["alerts"] == 2 and report["normal"]["cited"] == 3
    assert report["normal"]["near_share"] == pytest.approx(2 / 3)
    assert report["fault"]["alerts"] == 0


def test_repeat_stability_on_candidates_of_every_repeat() -> None:
    r0 = _rows("ref", ["TRUE_ALERT", "TRUE_ALERT", "FALSE_POSITIVE", "FALSE_POSITIVE", "TRUE_ALERT"])  # c4 only here
    r1 = _rows("ref", ["TRUE_ALERT", "UNCERTAIN", "FALSE_POSITIVE", "FALSE_POSITIVE"])
    r2 = _rows("ref", ["TRUE_ALERT", "TRUE_ALERT", "FALSE_POSITIVE", "UNCERTAIN"])
    entry = repeat_stability({"ref": [r0, r1, r2]})["ref"]
    normal = entry["normal"]
    assert normal["n"] == 4 and normal["repeats"] == 3
    assert normal["raw_true_by_repeat"] == [0.5, 0.25, 0.5]
    # c1 flips TRUE_ALERT <-> UNCERTAIN; c3 flips only between two non-alert labels, which does not count
    assert normal["flip_rate"] == 0.25
    assert entry["fault"]["n"] == 0 and entry["fault"]["flip_rate_ci95"] is None
