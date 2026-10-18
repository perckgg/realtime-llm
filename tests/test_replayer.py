"""Unit tests for services.replayer.nezha_source.NezhaReplaySource -- pure
ordering/config logic, no Nezha dataset needed (the loader is monkeypatched).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from packages.schemas.models import TelemetryWindow
from services.replayer import nezha_source


def _window(window_id: str, service: str, ts: datetime) -> TelemetryWindow:
    return TelemetryWindow(window_id=window_id, service=service, start_ts=ts, end_ts=ts + timedelta(seconds=60))


@pytest.fixture
def unordered_windows() -> list[TelemetryWindow]:
    base = datetime(2023, 1, 1, tzinfo=UTC)
    return [
        _window("c", "checkout", base + timedelta(minutes=2)),
        _window("a", "checkout", base),
        _window("b", "payment", base + timedelta(minutes=1)),
    ]


def test_stream_sorts_by_start_ts_then_window_id(monkeypatch, unordered_windows):
    monkeypatch.setattr(nezha_source, "iter_telemetry_windows", lambda **kwargs: iter(list(unordered_windows)))
    source = nezha_source.NezhaReplaySource(window_ids={"a", "b", "c"}, speed_multiplier=0)
    assert [w.window_id for w in source.stream()] == ["a", "b", "c"]


def test_limit_stops_early(monkeypatch, unordered_windows):
    monkeypatch.setattr(nezha_source, "iter_telemetry_windows", lambda **kwargs: iter(list(unordered_windows)))
    source = nezha_source.NezhaReplaySource(window_ids={"a", "b", "c"}, speed_multiplier=0, limit=2)
    assert [w.window_id for w in source.stream()] == ["a", "b"]


def test_speed_multiplier_zero_does_not_sleep(monkeypatch, unordered_windows):
    monkeypatch.setattr(nezha_source, "iter_telemetry_windows", lambda **kwargs: iter(list(unordered_windows)))
    calls = []
    monkeypatch.setattr(nezha_source.time, "sleep", lambda s: calls.append(s))
    source = nezha_source.NezhaReplaySource(window_ids={"a", "b", "c"}, speed_multiplier=0)
    list(source.stream())
    assert calls == []


def test_split_and_window_ids_are_mutually_exclusive():
    with pytest.raises(ValueError):
        nezha_source.NezhaReplaySource(split="dev", window_ids={"a"})


def test_deterministic_across_repeated_streams(monkeypatch, unordered_windows):
    monkeypatch.setattr(nezha_source, "iter_telemetry_windows", lambda **kwargs: iter(list(unordered_windows)))
    source = nezha_source.NezhaReplaySource(window_ids={"a", "b", "c"}, speed_multiplier=0)
    first = [w.window_id for w in source.stream()]
    second = [w.window_id for w in source.stream()]
    assert first == second == ["a", "b", "c"]


def test_history_mode_streams_all_but_evaluates_only_selected(monkeypatch, unordered_windows):
    # QD-015 (D2): the split marks evaluated windows; history windows still stream.
    seen_filters = []

    def fake_loader(**kwargs):
        seen_filters.append(kwargs.get("window_ids"))
        return iter(list(unordered_windows))

    monkeypatch.setattr(nezha_source, "iter_telemetry_windows", fake_loader)
    source = nezha_source.NezhaReplaySource(window_ids={"b"}, speed_multiplier=0, include_history=True)
    streamed = list(source.stream())
    assert [w.window_id for w in streamed] == ["a", "b", "c"]
    assert [source.is_evaluated(w) for w in streamed] == [False, True, False]
    assert seen_filters == [None]


def test_history_mode_limit_counts_evaluated_windows_only(monkeypatch, unordered_windows):
    monkeypatch.setattr(nezha_source, "iter_telemetry_windows", lambda **kwargs: iter(list(unordered_windows)))
    source = nezha_source.NezhaReplaySource(window_ids={"b"}, speed_multiplier=0, include_history=True, limit=1)
    assert [w.window_id for w in source.stream()] == ["a", "b"]


def test_without_history_split_filter_is_passed_to_loader(monkeypatch, unordered_windows):
    seen_filters = []

    def fake_loader(**kwargs):
        seen_filters.append(kwargs.get("window_ids"))
        return iter([w for w in unordered_windows if w.window_id in kwargs["window_ids"]])

    monkeypatch.setattr(nezha_source, "iter_telemetry_windows", fake_loader)
    source = nezha_source.NezhaReplaySource(window_ids={"b"}, speed_multiplier=0)
    assert [w.window_id for w in source.stream()] == ["b"]
    assert seen_filters == [{"b"}]
