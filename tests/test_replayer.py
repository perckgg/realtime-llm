"""Unit tests for services.replayer.nezha_source.NezhaReplaySource -- pure
ordering/config logic, no Nezha dataset needed (the loader is monkeypatched).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

import services.replayer.nezha_source as nezha_source
from packages.schemas.models import TelemetryWindow


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
