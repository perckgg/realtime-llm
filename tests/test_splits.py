"""Guards on the committed dev/val/test splits.

The splits are frozen ground truth for the whole thesis
(docs/Final_Thesis_Phase2/02-data-and-experiment-protocol.md §2). These tests
fail loudly if anything silently regenerates or edits them, which is the failure
mode that would invalidate every number reported later.

They read only data/splits/*.json, so they run without the Nezha dataset.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

SPLITS_DIR = Path(__file__).resolve().parent.parent / "data" / "splits"
SPLIT_NAMES = ("dev", "val", "test")
EXPECTED_RATIOS = {"dev": 0.20, "val": 0.30, "test": 0.50}
FAULT_TYPES = {"cpu_consumed", "cpu_contention", "exception", "network_delay", "return"}
TOTAL_INJECTIONS = 101


@pytest.fixture(scope="module")
def splits() -> dict[str, dict]:
    payloads = {}
    for name in SPLIT_NAMES:
        path = SPLITS_DIR / f"{name}.json"
        if not path.exists():
            pytest.skip(f"{path} not generated yet — run scripts/make_splits.py")
        payloads[name] = json.loads(path.read_text(encoding="utf-8"))
    return payloads


def test_seed_is_frozen(splits):
    assert {payload["seed"] for payload in splits.values()} == {42}


def test_window_ids_are_unique_within_each_split(splits):
    for name, payload in splits.items():
        ids = payload["window_ids"]
        assert len(ids) == len(set(ids)), f"{name} contains duplicate window ids"


def test_splits_are_disjoint(splits):
    for left in SPLIT_NAMES:
        for right in SPLIT_NAMES:
            if left >= right:
                continue
            overlap = set(splits[left]["window_ids"]) & set(splits[right]["window_ids"])
            assert not overlap, f"{left} and {right} share {len(overlap)} windows"


def test_ratios_are_within_two_points_of_target(splits):
    total = sum(payload["n_windows"] for payload in splits.values())
    for name, payload in splits.items():
        actual = payload["n_windows"] / total
        assert abs(actual - EXPECTED_RATIOS[name]) < 0.02, (
            f"{name} holds {actual:.1%} of windows, expected ~{EXPECTED_RATIOS[name]:.0%}"
        )


def test_every_fault_type_appears_in_every_split(splits):
    for name, payload in splits.items():
        present = set(payload["counts_by_fault_type"]) - {"normal"}
        assert present == FAULT_TYPES, f"{name} is missing fault types: {FAULT_TYPES - present}"


def test_all_injections_are_used_exactly_once(splits):
    assert sum(payload["n_injections"] for payload in splits.values()) == TOTAL_INJECTIONS


def test_class_imbalance_is_preserved(splits):
    """Every split must keep roughly the corpus-wide 1:135 fault:normal ratio.

    Rebalancing a split would inflate Precision and break the Week 3 gate, so
    this is a correctness guard, not a style preference.
    """
    ratios = {
        name: (payload["n_windows"] - payload["n_fault_windows"]) / payload["n_fault_windows"]
        for name, payload in splits.items()
    }
    assert max(ratios.values()) / min(ratios.values()) < 1.5, (
        f"fault:normal ratios diverge across splits: {ratios}"
    )


def test_manifest_agrees_with_the_split_files(splits):
    path = SPLITS_DIR / "manifest.json"
    if not path.exists():
        pytest.skip("manifest.json not generated yet")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for name, payload in splits.items():
        assert manifest["splits"][name]["n_windows"] == payload["n_windows"]
        assert manifest["splits"][name]["n_fault_windows"] == payload["n_fault_windows"]
