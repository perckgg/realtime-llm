"""scripts/make_repeat_subset.py: the fixed subset of the judge-variance runs (M8, QD-034)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "make_repeat_subset", Path(__file__).resolve().parents[1] / "scripts" / "make_repeat_subset.py"
)
assert _SPEC is not None and _SPEC.loader is not None
make_repeat_subset = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(make_repeat_subset)


def _rows() -> list[dict[str, str]]:
    rows = []
    for i in range(60):
        rows.append({"window_id": f"w{i:02d}", "is_candidate": str(int(i % 2 == 0)), "has_telemetry": str(int(i % 3 == 0))})
    return rows


def test_draw_uses_only_candidates_with_telemetry_and_is_reproducible() -> None:
    rows = _rows()
    eligible = [r["window_id"] for r in rows if r["is_candidate"] == "1" and r["has_telemetry"] == "1"]
    first = make_repeat_subset.draw(rows, 5, 42)
    assert len(first) == 5 and set(first) <= set(eligible)
    assert first == sorted(first, key=eligible.index)  # replay order kept
    assert first == make_repeat_subset.draw(rows, 5, 42)
    assert first != make_repeat_subset.draw(rows, 5, 43)


def test_draw_refuses_a_pool_that_is_too_small() -> None:
    with pytest.raises(ValueError):
        make_repeat_subset.draw(_rows(), 11, 42)
