"""Span duration baseline for C3 (M6, QD-029)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from packages.schemas.evidence import EvidenceDoc, trace_doc
from packages.schemas.nezha import Injection, Window
from services.judge.span_baseline import (
    MIN_SPANS,
    SpanBaseline,
    SpanSelector,
    percentile_rows,
    span_operation,
)

T0 = datetime(2022, 8, 22, 4, 0, 0, tzinfo=UTC)


def _window(window_id: str, pod: str, minute: int, fault: bool = False, system: str = "online_boutique") -> Window:
    return Window(
        window_id=window_id,
        day="2022-08-22",
        system=system,
        pod=pod,
        service=pod.split("-")[0],
        start_ts=T0 + timedelta(minutes=minute),
        is_fault=fault,
        fault_type="exception" if fault else "normal",
        root_cause_service="",
        injection_id="",
    )


def _injection(minute: int, system: str = "online_boutique") -> Injection:
    return Injection(
        injection_id=f"i{minute}",
        day="2022-08-22",
        system=system,
        inject_ts=T0 + timedelta(minutes=minute),
        inject_pod="other-pod",
        root_cause_service="other",
        fault_type="exception",
    )


def _doc(pod: str, seconds: float) -> EvidenceDoc:
    return EvidenceDoc(
        doc_id=f"{pod}-{seconds}",
        ts=T0 + timedelta(seconds=seconds),
        pod=pod,
        service=pod.split("-")[0],
        severity="INFO",
        event_type="trace_span",
        source="nezha_trace",
        message=f"Trace span op on {pod} duration_ms=1.000",
        duration_ms=1.0,
    )


def test_span_operation_reads_the_trace_doc_message() -> None:
    raw = {
        "StartTimeUnixNano": "1661140800000000000",
        "EndTimeUnixNano": "1661140800074856000",
        "PodName": "checkoutservice-578fcf4766-9csqn",
        "OperationName": "hipstershop.EmailService/SendOrderConfirmation",
    }
    doc = trace_doc(raw, "2022-08-22", {"checkoutservice": "online_boutique"})
    assert doc is not None and span_operation(doc.message) == "hipstershop.EmailService/SendOrderConfirmation"
    assert span_operation("Trace span GET /a b on pod-1 duration_ms=1.500") == "GET /a b"
    assert span_operation("an application log line") is None


def test_selector_keeps_only_clean_normal_dev_spans() -> None:
    windows = [
        _window("clean", "cart-1", 0),
        _window("val", "cart-1", 1),
        _window("fault", "cart-1", 2, fault=True),
        _window("busy", "cart-1", 9),  # labelled normal, but another pod is under injection
        _window("other", "ticket-1", 9, system="train_ticket"),
    ]
    selector = SpanSelector(
        windows, {"clean", "fault", "busy", "other"}, [_injection(10), _injection(11)]
    )
    assert selector.reason(_doc("cart-1", 30)) == "kept"
    assert selector.reason(_doc("cart-1", 90)) == "not_dev"
    assert selector.reason(_doc("cart-1", 150)) == "fault_window"
    assert selector.reason(_doc("cart-1", 9 * 60 + 30)) == "during_injection"
    # the injection is in the other system
    assert selector.reason(_doc("ticket-1", 9 * 60 + 30)) == "kept"


def test_selector_needs_a_window_covering_the_span() -> None:
    selector = SpanSelector([_window("clean", "cart-1", 0)], {"clean"}, [])
    assert selector.reason(_doc("cart-1", -1)) == "no_window"
    assert selector.reason(_doc("cart-1", 60)) == "no_window"  # window is [start, start + 60 s)
    assert selector.reason(_doc("unknown-1", 10)) == "no_window"


def test_injection_interval_uses_the_label_rule_edges() -> None:
    windows = [_window("before", "cart-1", 8), _window("after", "cart-1", 16), _window("past", "cart-1", 17)]
    selector = SpanSelector(windows, {"before", "after", "past"}, [_injection(10)])
    assert selector.reason(_doc("cart-1", 8 * 60 + 59)) == "kept"
    assert selector.reason(_doc("cart-1", 9 * 60)) == "no_window"  # no window, edge covered below
    assert selector.reason(_doc("cart-1", 16 * 60)) == "during_injection"  # inject + 360 s
    assert selector.reason(_doc("cart-1", 16 * 60 + 1)) == "kept"


def test_baseline_threshold_needs_min_spans() -> None:
    frame = percentile_rows(
        {
            ("cart", "get"): [float(i) for i in range(1, 101)],
            ("cart", "rare"): [1.0] * (MIN_SPANS - 1),
        }
    )
    baseline = SpanBaseline(frame)
    assert baseline.threshold("cart", "get", 50) == pytest.approx(50.5)
    assert baseline.threshold("cart", "get", 99) == pytest.approx(99.01)
    assert baseline.threshold("cart", "rare", 95) is None
    assert baseline.threshold("cart", "unseen", 95) is None
