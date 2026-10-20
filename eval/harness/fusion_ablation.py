"""Retrieval-only ablation of the C1 Fusion weights (alpha, beta, gamma) x k_graph (M4 task 3, V22, QD-025).

C1's candidate pool (lexical top-`bm25_k` + graph expansion) does not depend on
the weights or the quota, so every candidate's pool is built once
(`HybridBm25GraphRetriever.build_pool`) and re-ranked for each grid point
(`reweighted(...).top_events`) -- the same code path as `retrieve()`.

No LLM is called. V22 (a) metrics, on candidates whose window has telemetry:

- neighbour evidence: prompts with >= 1 event of another service (origin
  "graph") and the mean share of such events in the top-k, for fault and
  non-fault candidates separately;
- concurrent-root hit: among non-fault candidates whose timestamp also has a
  fault window of another service, the share whose top-k contains evidence of
  that faulty service (bootstrap CI);
- root hit of fault candidates -- a sanity check only: fault windows are always
  the root service's own window, so it is 1.0 whenever retrieval is non-empty
  (QD-024).
"""

from __future__ import annotations

import csv
import json
import math
import time
from collections import defaultdict
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from eval.harness.runner import (
    RESULTS,
    _dataset_label,
    _detector,
    _evaluated,
    _git_commit,
    _train_ids,
)
from eval.harness.stats import bootstrap_ci
from packages.schemas.evidence import NezhaEvidenceStore
from packages.schemas.models import AlertCandidate
from services.detector.candidates import build_alert_candidate
from services.replayer.nezha_source import NezhaReplaySource
from services.retrieval.hybrid_bm25_graph import HybridBm25GraphRetriever
from services.retrieval.registry import build_budget, build_strategy


@dataclass(frozen=True)
class GridPoint:
    alpha: float
    beta: float
    gamma: float
    k_graph: int

    @property
    def name(self) -> str:
        return f"a{self.alpha:g}_b{self.beta:g}_g{self.gamma:g}_k{self.k_graph}"


@dataclass(frozen=True)
class WindowInfo:
    window_id: str
    service: str
    ts: datetime
    is_fault: bool
    root: str
    has_telemetry: bool


@dataclass(frozen=True)
class TopK:
    """Top-k of one candidate at one grid point (event ids only kept for `keep_ids` points)."""

    services: tuple[str, ...]
    origins: tuple[str, ...]
    event_ids: tuple[str, ...] = ()


def build_grid(spec: Mapping[str, Any]) -> list[GridPoint]:
    """Simplex grid with `grid_step` (+ `extra_points`), crossed with `k_graph` values."""
    step = float(spec["grid_step"])
    n = round(1 / step)
    if n < 1 or not math.isclose(n * step, 1.0, abs_tol=1e-9):
        raise ValueError("grid_step must divide 1")
    weights: list[tuple[float, float, float]] = []
    for i in range(n + 1):
        for j in range(n + 1 - i):
            weights.append((round(i * step, 10), round(j * step, 10), round(1 - (i + j) * step, 10)))
    for extra in spec.get("extra_points") or []:
        a, b, g = (float(x) for x in extra)
        if not any(all(math.isclose(x, y, abs_tol=1e-9) for x, y in zip(w, (a, b, g), strict=True)) for w in weights):
            weights.append((a, b, g))
    ks = [int(k) for k in spec.get("k_graph", [0])]
    return [GridPoint(a, b, g, k) for k in ks for a, b, g in weights]


def _is_kept(point: GridPoint, keep: Sequence[Sequence[float]]) -> bool:
    return any(
        all(math.isclose(x, float(y), abs_tol=1e-9) for x, y in zip((point.alpha, point.beta, point.gamma), w, strict=True))
        for w in keep
    )


def collect(config: Mapping[str, Any]) -> tuple[list[WindowInfo], list[tuple[AlertCandidate, WindowInfo]]]:
    """Replay + detector exactly as the harness (no gate): every evaluated window and the candidates."""
    if config.get("gate"):
        raise ValueError("the retrieval-only ablation retrieves for every candidate; remove `gate`")
    time_source = config.get("time_source", "wall")
    evaluated, override = _evaluated(dict(config))
    if override:
        raise ValueError("window_set labels are not supported here; use `split`")
    detector, fit = _detector(dict(config))
    train_ids = _train_ids(fit)
    detector.fit(
        NezhaReplaySource(window_ids=train_ids, include_history=True, time_source=time_source).stream(),
        train_ids=train_ids,
    )
    nezha = NezhaEvidenceStore()
    replay = NezhaReplaySource(
        window_ids=evaluated, include_history=True, time_source=time_source, limit=config.get("n_windows")
    )
    windows: list[WindowInfo] = []
    candidates: list[tuple[AlertCandidate, WindowInfo]] = []
    for window in replay.stream():
        if not replay.is_evaluated(window):
            detector.observe(window)
            continue
        label = _dataset_label(window)
        info = WindowInfo(
            window.window_id,
            window.service,
            window.start_ts,
            label.is_fault,
            label.root_cause,
            nezha.has_telemetry(window.start_ts, window.end_ts),
        )
        windows.append(info)
        score = detector.score(window)
        candidate = build_alert_candidate(
            window, score, detector.is_candidate(window, score), detector.top_features(window)
        )
        if candidate is not None:
            candidates.append((candidate, info))
    return windows, candidates


_WORKER: dict[str, Any] = {}


def _init_worker(retrieval_config: dict[str, Any], points: list[GridPoint], keep: list[list[float]]) -> None:
    base = build_strategy(retrieval_config, NezhaEvidenceStore())
    if not isinstance(base, HybridBm25GraphRetriever):
        raise ValueError("the Fusion ablation needs retrieval.type = hybrid_bm25_graph")
    _WORKER["base"] = base
    _WORKER["budget"] = build_budget(retrieval_config)
    _WORKER["variants"] = [(base.reweighted(p.alpha, p.beta, p.gamma, p.k_graph), _is_kept(p, keep)) for p in points]


def _chunk(candidates: list[AlertCandidate]) -> list[list[TopK]]:
    base: HybridBm25GraphRetriever = _WORKER["base"]
    out: list[list[TopK]] = []
    for candidate in candidates:
        pool = base.build_pool(candidate)
        row: list[TopK] = []
        for variant, keep_ids in _WORKER["variants"]:
            events = variant.top_events(pool, _WORKER["budget"])[0]
            row.append(
                TopK(
                    tuple(e.service for e in events),
                    tuple(e.origin for e in events),
                    tuple(e.event_id for e in events) if keep_ids else (),
                )
            )
        out.append(row)
    return out


def rank_grid(
    retrieval_config: dict[str, Any],
    candidates: Sequence[AlertCandidate],
    points: list[GridPoint],
    keep: list[list[float]],
    workers: int,
) -> list[list[TopK]]:
    """`result[c][p]` = top-k of candidate c at grid point p; contiguous time-ordered chunks per process."""
    if not candidates:
        return []
    args = (retrieval_config, points, keep)
    if workers <= 1:
        _init_worker(*args)
        return _chunk(list(candidates))
    n_chunks = min(len(candidates), workers * 4)
    size = -(-len(candidates) // n_chunks)
    chunks = [list(candidates[i : i + size]) for i in range(0, len(candidates), size)]
    with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker, initargs=args) as pool:
        return [row for part in pool.map(_chunk, chunks) for row in part]


def concurrent_faults(windows: Sequence[WindowInfo]) -> dict[datetime, set[str]]:
    faulty: dict[datetime, set[str]] = defaultdict(set)
    for w in windows:
        if w.is_fault:
            faulty[w.ts].add(w.service)
    return faulty


def _mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def summarize(
    points: Sequence[GridPoint],
    infos: Sequence[WindowInfo],
    topk: Sequence[Sequence[TopK]],
    faulty: Mapping[datetime, set[str]],
    seed: int = 42,
) -> list[dict[str, Any]]:
    """V22 (a) metrics per grid point, on candidates whose window has telemetry."""
    table: list[dict[str, Any]] = []
    for p_idx, point in enumerate(points):
        groups: dict[str, list[TopK]] = {"fault": [], "nonfault": []}
        roots: list[bool] = []
        concurrent: list[bool] = []
        for info, row in zip(infos, topk, strict=True):
            if not info.has_telemetry:
                continue
            top = row[p_idx]
            groups["fault" if info.is_fault else "nonfault"].append(top)
            if info.is_fault and info.root:
                roots.append(info.root in top.services)
            others = set(faulty.get(info.ts, set())) - {info.service}
            if not info.is_fault and others:
                concurrent.append(any(s in others for s in top.services))
        entry: dict[str, Any] = {"point": point.name, **point.__dict__}
        for name, rows in groups.items():
            nonempty = [t for t in rows if t.services]
            entry[name] = {
                "n": len(rows),
                "empty_retrieval": len(rows) - len(nonempty),
                "with_graph_evidence": sum(1 for t in nonempty if "graph" in t.origins),
                "graph_share_mean": _mean([t.origins.count("graph") / len(t.origins) for t in nonempty]),
            }
        entry["root_hit_sanity"] = {"n": len(roots), "hits": sum(roots)}
        entry["concurrent_root"] = {
            "n": len(concurrent),
            "hits": sum(concurrent),
            "hit_rate": _rate(concurrent) if concurrent else None,
            "hit_rate_ci95": list(bootstrap_ci(concurrent, _rate, seed=seed)) if concurrent else None,
        }
        table.append(entry)
    return table


def _rate(values: Sequence[bool]) -> float:
    return sum(values) / len(values)


def verify_against(
    points: Sequence[GridPoint], infos: Sequence[WindowInfo], topk: Sequence[Sequence[TopK]],
    runs: Mapping[int, str], keep: Sequence[Sequence[float]], results_root: Path = RESULTS,
) -> dict[str, Any]:
    """Top-k event ids at the kept weights must equal an earlier harness run with the same k_graph."""
    report: dict[str, Any] = {}
    for k, run_id in runs.items():
        idx = [i for i, p in enumerate(points) if p.k_graph == int(k) and _is_kept(p, keep)]
        if not idx:
            raise ValueError(f"no kept grid point with k_graph={k}")
        expected: dict[str, list[str]] = {}
        with (results_root / run_id / "retrieval.jsonl").open(encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                expected[record["window_id"]] = [e["event_id"] for e in record["events"]]
        same = differ = missing = 0
        for info, row in zip(infos, topk, strict=True):
            ids = expected.get(info.window_id)
            if ids is None:
                missing += 1
            elif list(row[idx[0]].event_ids) == ids:
                same += 1
            else:
                differ += 1
        report[run_id] = {"point": points[idx[0]].name, "identical": same, "different": differ, "missing": missing}
    return report


def run(config: dict[str, Any], results_root: Path = RESULTS) -> Path:
    spec = config.get("ablation")
    if not spec or "retrieval" not in config:
        raise ValueError("config needs `retrieval` and `ablation`")
    out_dir = results_root / str(config["run_id"])
    if out_dir.exists():
        raise SystemExit(f"{out_dir} already exists: results are never overwritten, use a new run_id")
    retrieval_config = dict(config["retrieval"])
    workers = int(retrieval_config.get("workers", 1))
    points = build_grid(spec)
    keep = [list(map(float, w)) for w in spec.get("keep_ids_for") or []]

    started = time.perf_counter()
    windows, pairs = collect(config)
    replay_s = time.perf_counter() - started
    candidates = [c for c, _ in pairs]
    infos = [info for _, info in pairs]
    topk = rank_grid(retrieval_config, candidates, points, keep, workers)
    rank_s = time.perf_counter() - started - replay_s
    faulty = concurrent_faults(windows)
    table = summarize(points, infos, topk, faulty, seed=int(config.get("seed", 42)))

    out_dir.mkdir(parents=True)
    (out_dir / "config.snapshot.yaml").write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True), "utf-8")
    (out_dir / "git_commit.txt").write_text(_git_commit() + "\n", "utf-8")
    (out_dir / "grid.json").write_text(json.dumps(table, indent=2, allow_nan=False) + "\n", "utf-8")
    with (out_dir / "per_candidate.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["window_id", "point", "n_events", "n_graph", "services"])
        for info, row in zip(infos, topk, strict=True):
            if not info.has_telemetry:
                continue
            for point, top in zip(points, row, strict=True):
                writer.writerow([info.window_id, point.name, len(top.services), top.origins.count("graph"),
                                 "|".join(top.services)])
    verification = verify_against(points, infos, topk, spec.get("verify_against") or {}, keep, results_root)
    runtime = {
        "windows": len(windows),
        "candidates": len(candidates),
        "grid_points": len(points),
        "workers": workers,
        "replay_seconds": round(replay_s, 1),
        "rank_seconds": round(rank_s, 1),
        "verify_against": verification,
    }
    (out_dir / "runtime.json").write_text(json.dumps(runtime, indent=2) + "\n", "utf-8")
    return out_dir
