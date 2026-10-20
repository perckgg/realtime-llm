"""V18 (QD-024): choose C1-quota's `k_graph` on `val` without any LLM call.

Criterion, approved by the user on 2026-10-20 (docs/CURRENT-MILESTONE.md V18):
over fault windows with telemetry that reached retrieval, the share whose
top-k contains at least one event of the labelled root-cause service
("root hit"). Constraint: on windows whose alerted service s0 *is* the root,
the root-hit count must not drop below k_graph = 0 (C1-paper) -- the quota
must not push out local evidence the paper already found. Among the k that
pass, the highest root-hit count wins; ties go to the smallest k.

Reads only the harness outputs (`per_window.csv`, `retrieval.jsonl`).
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eval.harness.stats import bootstrap_ci, mcnemar_exact


@dataclass(frozen=True)
class RootHit:
    window_id: str
    s0: str
    root: str
    hit: bool
    n_events: int
    n_graph: int

    @property
    def s0_is_root(self) -> bool:
        return self.s0 == self.root


def root_hits(per_window: Iterable[Mapping[str, str]], retrieval: Iterable[Mapping[str, Any]]) -> list[RootHit]:
    """One RootHit per fault window with telemetry, a labelled root and a retrieval, in per_window order."""
    events = {str(r["window_id"]): r["events"] for r in retrieval}
    out: list[RootHit] = []
    for row in per_window:
        root = row.get("label_root_cause") or ""
        if row["label_is_fault"] != "1" or row["has_telemetry"] != "1" or not root:
            continue
        if row["window_id"] not in events:
            continue
        top = events[row["window_id"]]
        out.append(
            RootHit(
                window_id=row["window_id"],
                s0=row["service"],
                root=root,
                hit=any(e["service"] == root for e in top),
                n_events=len(top),
                n_graph=sum(e.get("origin") == "graph" for e in top),
            )
        )
    return out


def summarize(rows: list[RootHit], seed: int = 42) -> dict[str, Any]:
    def rate(part: Sequence[RootHit]) -> float:
        return sum(r.hit for r in part) / len(part) if part else float("nan")

    local = [r for r in rows if r.s0_is_root]
    other = [r for r in rows if not r.s0_is_root]
    return {
        "n": len(rows),
        "hits": sum(r.hit for r in rows),
        "hit_rate": rate(rows),
        "hit_rate_ci95": bootstrap_ci(rows, rate, seed=seed),
        "s0_is_root": {"n": len(local), "hits": sum(r.hit for r in local), "hit_rate": rate(local) if local else None},
        "s0_not_root": {"n": len(other), "hits": sum(r.hit for r in other), "hit_rate": rate(other) if other else None},
        "with_graph_evidence": sum(r.n_graph > 0 for r in rows),
        "empty_retrieval": sum(r.n_events == 0 for r in rows),
    }


def choose_k(runs: Mapping[int, list[RootHit]]) -> dict[str, Any]:
    """Apply the V18 rule. `runs[0]` (C1-paper) is the reference; all runs must cover the same windows."""
    if 0 not in runs:
        raise ValueError("k_graph = 0 (C1-paper) is the reference and must be included")
    ids = [r.window_id for r in runs[0]]
    for k, rows in runs.items():
        if [r.window_id for r in rows] != ids:
            raise ValueError(f"k_graph={k} covers different windows than k_graph=0")
    reference = runs[0]
    local_floor = sum(r.hit for r in reference if r.s0_is_root)
    table: dict[int, dict[str, Any]] = {}
    for k in sorted(runs):
        rows = runs[k]
        summary = summarize(rows)
        summary["passes_local_constraint"] = summary["s0_is_root"]["hits"] >= local_floor
        summary["mcnemar_p_vs_k0"] = mcnemar_exact([r.hit for r in rows], [r.hit for r in reference])
        table[k] = summary
    eligible = [k for k in sorted(table) if k > 0 and table[k]["passes_local_constraint"]]
    chosen = max(eligible, key=lambda k: (table[k]["hits"], -k)) if eligible else None
    return {"chosen_k_graph": chosen, "local_floor_hits": local_floor, "by_k": table}


def load_run(run_dir: Path) -> list[RootHit]:
    with (run_dir / "per_window.csv").open(encoding="utf-8", newline="") as handle:
        per_window = list(csv.DictReader(handle))
    with (run_dir / "retrieval.jsonl").open(encoding="utf-8") as handle:
        retrieval = [json.loads(line) for line in handle]
    return root_hits(per_window, retrieval)
