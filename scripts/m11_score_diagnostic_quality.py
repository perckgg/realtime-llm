"""Score manual diagnostic-quality grades (M11 step 4, P5; 02 SS4.4). No LLM call.

    py scripts/m11_score_diagnostic_quality.py \
        --graded eval/manual/diagnostic_quality.csv \
        --key eval/manual/diagnostic_quality.key.csv \
        --out eval/results/m11_diagnostic_quality_v1

Optionally pass `--second-rater <path.csv>` to compute exact agreement and
unweighted / quadratic-weighted Cohen's kappa on overlapping graded incidents.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from eval.harness.stats import bootstrap_ci  # noqa: E402

SCORE_COLUMNS = ("root_cause_score", "evidence_score", "action_score")
VALID_SCORES = {"0": 0, "1": 1, "2": 2}


@dataclass(frozen=True)
class GradedRow:
    sample_no: int
    incident_id: str
    root_cause_score: int
    evidence_score: int
    action_score: int
    status: str
    objective_rc_score: int | None


def _parse_score(raw: str, column: str, sample_no: int) -> int:
    token = raw.strip()
    if token not in VALID_SCORES:
        raise ValueError(
            f"Row sample_no={sample_no} column {column!r} has invalid score {raw!r}; expected 0, 1, or 2"
        )
    return VALID_SCORES[token]


def load_graded_rows(
    graded_path: Path,
    key_path: Path,
) -> tuple[list[GradedRow], int, bool]:
    """Load and validate graded rows aligned against `.key.csv`.

    Returns `(graded_rows, total_rows_in_sheet, is_valid_prefix)`.
    """
    with graded_path.open(encoding="utf-8-sig", newline="") as handle:
        sheet_rows = list(csv.DictReader(handle))
    with key_path.open(encoding="utf-8-sig", newline="") as handle:
        key_rows = list(csv.DictReader(handle))

    if len(sheet_rows) != len(key_rows):
        raise ValueError(
            f"Row count mismatch: graded={len(sheet_rows)} vs key={len(key_rows)}"
        )

    key_by_no: dict[int, Mapping[str, str]] = {}
    for krow in key_rows:
        sno = int(krow["sample_no"])
        key_by_no[sno] = krow

    graded: list[GradedRow] = []
    for row in sheet_rows:
        sno = int(row["sample_no"])
        krow = key_by_no.get(sno)
        if krow is None or row["incident_id"] != krow["incident_id"]:
            raise ValueError(
                f"Alignment mismatch at sample_no={sno}: {row.get('incident_id')!r} vs key"
            )
        raw_vals = [str(row.get(col) or "").strip() for col in SCORE_COLUMNS]
        if all(v == "" for v in raw_vals):
            continue
        if any(v == "" for v in raw_vals):
            raise ValueError(
                f"Partially graded row sample_no={sno} ({row['incident_id']}): fill all 3 score columns"
            )
        rc_s = _parse_score(raw_vals[0], "root_cause_score", sno)
        ev_s = _parse_score(raw_vals[1], "evidence_score", sno)
        ac_s = _parse_score(raw_vals[2], "action_score", sno)
        obj_raw = str(krow.get("objective_rc_score") or "").strip()
        obj_rc = int(obj_raw) if obj_raw != "" else None
        graded.append(
            GradedRow(
                sample_no=sno,
                incident_id=str(row["incident_id"]),
                root_cause_score=rc_s,
                evidence_score=ev_s,
                action_score=ac_s,
                status=str(krow.get("status") or ""),
                objective_rc_score=obj_rc,
            )
        )

    graded.sort(key=lambda item: item.sample_no)
    is_valid_prefix = [g.sample_no for g in graded] == list(range(1, len(graded) + 1))
    return graded, len(sheet_rows), is_valid_prefix


def _load_second_rater_map(second_path: Path) -> dict[str, tuple[int, int, int]]:
    with second_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    out: dict[str, tuple[int, int, int]] = {}
    for row in rows:
        sno = int(row["sample_no"])
        raw_vals = [str(row.get(col) or "").strip() for col in SCORE_COLUMNS]
        if all(v == "" for v in raw_vals):
            continue
        if any(v == "" for v in raw_vals):
            raise ValueError(f"Second-rater row sample_no={sno} is partially filled")
        out[str(row["incident_id"])] = (
            _parse_score(raw_vals[0], "root_cause_score", sno),
            _parse_score(raw_vals[1], "evidence_score", sno),
            _parse_score(raw_vals[2], "action_score", sno),
        )
    return out


def cohens_kappa(
    a: Sequence[int],
    b: Sequence[int],
    categories: Sequence[int] = (0, 1, 2),
    weighted: bool = False,
) -> float | None:
    """Exact unweighted or quadratic-weighted Cohen's kappa on discrete categories."""
    if len(a) != len(b):
        raise ValueError("Rater sequences must have equal length")
    n = len(a)
    if n == 0:
        return None
    idx = {cat: i for i, cat in enumerate(categories)}
    k = len(categories)
    matrix = [[0] * k for _ in range(k)]
    for x, y in zip(a, b, strict=True):
        if x not in idx or y not in idx:
            raise ValueError(f"Unexpected category pair ({x}, {y})")
        matrix[idx[x]][idx[y]] += 1

    row_sums = [sum(matrix[i]) for i in range(k)]
    col_sums = [sum(matrix[i][j] for i in range(k)) for j in range(k)]

    if not weighted:
        po = sum(matrix[i][i] for i in range(k)) / n
        pe = sum(row_sums[i] * col_sums[i] for i in range(k)) / (n * n)
        if pe == 1.0:
            return None
        return (po - pe) / (1.0 - pe)

    span = max(1, k - 1)
    obs_dis = 0.0
    exp_dis = 0.0
    for i in range(k):
        for j in range(k):
            w = ((i - j) / span) ** 2
            obs_dis += w * (matrix[i][j] / n)
            exp_dis += w * ((row_sums[i] * col_sums[j]) / (n * n))
    if exp_dis == 0.0:
        return None
    return 1.0 - (obs_dis / exp_dis)


def summarize_criterion(
    values: Sequence[int],
    n_boot: int = 1000,
    seed: int = 42,
) -> dict[str, Any]:
    n = len(values)
    counts = Counter(values)
    dist = {str(c): counts.get(c, 0) for c in (0, 1, 2)}
    if n == 0:
        return {"n": 0, "mean": None, "std": None, "ci95": None, "counts": dist}
    mean_val = sum(values) / n
    std_val = statistics.stdev(values) if n > 1 else 0.0
    ci = bootstrap_ci(list(values), lambda xs: sum(xs) / len(xs), n_boot=n_boot, seed=seed)
    return {
        "n": n,
        "mean": mean_val,
        "std": std_val,
        "ci95": [ci[0], ci[1]],
        "counts": dist,
    }


def score_diagnostic_quality(
    graded_path: Path,
    key_path: Path,
    second_rater_path: Path | None = None,
    n_boot: int = 1000,
    seed: int = 42,
) -> dict[str, Any]:
    rows, total_sheet, is_valid_prefix = load_graded_rows(graded_path, key_path)
    if not rows:
        raise ValueError(f"No graded rows found in {graded_path}")

    overall = {
        "root_cause_score": summarize_criterion([r.root_cause_score for r in rows], n_boot, seed),
        "evidence_score": summarize_criterion([r.evidence_score for r in rows], n_boot, seed),
        "action_score": summarize_criterion([r.action_score for r in rows], n_boot, seed),
    }

    by_status: dict[str, Any] = {}
    for st in ("labelled", "no_fault", "ambiguous"):
        sub = [r for r in rows if r.status == st]
        by_status[st] = {
            "n": len(sub),
            "root_cause_score": summarize_criterion([r.root_cause_score for r in sub], n_boot, seed),
            "evidence_score": summarize_criterion([r.evidence_score for r in sub], n_boot, seed),
            "action_score": summarize_criterion([r.action_score for r in sub], n_boot, seed),
        }

    labelled_obj = [r for r in rows if r.objective_rc_score is not None]
    objective_comparison: dict[str, Any]
    if labelled_obj:
        exact_matches = sum(1 for r in labelled_obj if r.root_cause_score == r.objective_rc_score)
        diffs = [r.root_cause_score - int(r.objective_rc_score) for r in labelled_obj if r.objective_rc_score is not None]
        objective_comparison = {
            "n_labelled": len(labelled_obj),
            "human_mean": sum(r.root_cause_score for r in labelled_obj) / len(labelled_obj),
            "objective_mean": sum(int(r.objective_rc_score) for r in labelled_obj if r.objective_rc_score is not None)
            / len(labelled_obj),
            "exact_match_count": exact_matches,
            "exact_match_rate": exact_matches / len(labelled_obj),
            "mean_diff_human_minus_objective": sum(diffs) / len(diffs),
        }
    else:
        objective_comparison = {"n_labelled": 0}

    agreement: dict[str, Any] | None = None
    if second_rater_path is not None:
        sec_map = _load_second_rater_map(second_rater_path)
        overlap = [r for r in rows if r.incident_id in sec_map]
        if overlap:
            per_crit: dict[str, Any] = {}
            pooled_a: list[int] = []
            pooled_b: list[int] = []
            for idx, col in enumerate(SCORE_COLUMNS):
                vals_a = [getattr(r, col) for r in overlap]
                vals_b = [sec_map[r.incident_id][idx] for r in overlap]
                pooled_a.extend(vals_a)
                pooled_b.extend(vals_b)
                exact = sum(1 for x, y in zip(vals_a, vals_b, strict=True) if x == y) / len(overlap)
                per_crit[col] = {
                    "n": len(overlap),
                    "exact_agreement": exact,
                    "cohens_kappa": cohens_kappa(vals_a, vals_b, weighted=False),
                    "weighted_kappa_quadratic": cohens_kappa(vals_a, vals_b, weighted=True),
                }
            pooled_exact = sum(1 for x, y in zip(pooled_a, pooled_b, strict=True) if x == y) / len(pooled_a)
            agreement = {
                "overlap_incidents": len(overlap),
                "by_criterion": per_crit,
                "pooled": {
                    "n_ratings": len(pooled_a),
                    "exact_agreement": pooled_exact,
                    "cohens_kappa": cohens_kappa(pooled_a, pooled_b, weighted=False),
                    "weighted_kappa_quadratic": cohens_kappa(pooled_a, pooled_b, weighted=True),
                },
            }
        else:
            agreement = {"overlap_incidents": 0}

    return {
        "created_at": datetime.now(UTC).isoformat(),
        "graded_path": str(graded_path),
        "key_path": str(key_path),
        "n_sheet_total": total_sheet,
        "n_graded": len(rows),
        "graded_sample_nos": [r.sample_no for r in rows],
        "is_valid_prefix": is_valid_prefix,
        "n_boot": n_boot,
        "seed": seed,
        "overall": overall,
        "by_status": by_status,
        "objective_rc_comparison": objective_comparison,
        "inter_rater_agreement": agreement,
    }


def _fmt_num(val: float | None, digits: int = 3) -> str:
    return "—" if val is None else f"{val:.{digits}f}".replace(".", ",")


def render_markdown(summary: Mapping[str, Any]) -> str:
    lines = [
        f"## Đánh giá chất lượng báo cáo chẩn đoán (`n = {summary['n_graded']}` / {summary['n_sheet_total']})",
        "",
        f"- Mẫu tiền tố hợp lệ (`sample_no = 1..{summary['n_graded']}`): **{'Có' if summary['is_valid_prefix'] else 'Không'}**",
        "",
        "| Tiêu chí (thang 0–2) | `n` | Trung bình ± SD | CI95 bootstrap | Phân bố `0 / 1 / 2` |",
        "|---|---:|---:|---|---|",
    ]
    labels = {
        "root_cause_score": "Đúng root cause",
        "evidence_score": "Bằng chứng hợp lệ",
        "action_score": "Gợi ý xử lý dùng được",
    }
    for col, label in labels.items():
        s = summary["overall"][col]
        ci = s["ci95"]
        ci_str = f"[{_fmt_num(ci[0])}; {_fmt_num(ci[1])}]" if ci else "—"
        c = s["counts"]
        lines.append(
            f"| {label} | {s['n']} | {_fmt_num(s['mean'])} ± {_fmt_num(s['std'])} | {ci_str} | {c['0']} / {c['1']} / {c['2']} |"
        )

    lines.extend(["", "### Theo trạng thái nhãn thật (`.key.csv`)", "", "| Nhóm | `n` | Root cause | Bằng chứng | Gợi ý xử lý |", "|---|---:|---:|---:|---:|"])
    for st in ("labelled", "no_fault", "ambiguous"):
        b = summary["by_status"][st]
        lines.append(
            f"| `{st}` | {b['n']} | {_fmt_num(b['root_cause_score']['mean'])} | {_fmt_num(b['evidence_score']['mean'])} | {_fmt_num(b['action_score']['mean'])} |"
        )

    obj = summary["objective_rc_comparison"]
    if obj.get("n_labelled", 0) > 0:
        lines.extend(
            [
                "",
                f"- Đối chiếu `root_cause_score` người chấm vs thang đồ thị khách quan (`n_labelled = {obj['n_labelled']}`): "
                f"người `{_fmt_num(obj['human_mean'])}` vs khách quan `{_fmt_num(obj['objective_mean'])}`, "
                f"trùng khớp `{obj['exact_match_count']}/{obj['n_labelled']}` ({_fmt_num(obj['exact_match_rate'])}).",
            ]
        )

    agr = summary.get("inter_rater_agreement")
    if agr and agr.get("overlap_incidents", 0) > 0:
        lines.extend(["", f"### Độ đồng thuận hai người chấm (`n_overlap = {agr['overlap_incidents']}`)", "", "| Tiêu chí | Đồng thuận tuyệt đối | Cohen's κ | Weighted κ (quadratic) |", "|---|---:|---:|---:|"])
        for col, label in labels.items():
            c = agr["by_criterion"][col]
            lines.append(
                f"| {label} | {_fmt_num(c['exact_agreement'])} | {_fmt_num(c['cohens_kappa'])} | {_fmt_num(c['weighted_kappa_quadratic'])} |"
            )
        p = agr["pooled"]
        lines.append(
            f"| **Gộp chung (`{p['n_ratings']}` cặp điểm)** | **{_fmt_num(p['exact_agreement'])}** | **{_fmt_num(p['cohens_kappa'])}** | **{_fmt_num(p['weighted_kappa_quadratic'])}** |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graded", type=Path, default=Path("eval/manual/diagnostic_quality.csv"))
    parser.add_argument("--key", type=Path, default=Path("eval/manual/diagnostic_quality.key.csv"))
    parser.add_argument("--second-rater", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    out_dir = args.out if args.out.is_absolute() else REPO / args.out
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"{out_dir} already exists and is non-empty: results are never overwritten")

    graded_path = args.graded if args.graded.is_absolute() else REPO / args.graded
    key_path = args.key if args.key.is_absolute() else REPO / args.key
    sec_path = (
        None
        if args.second_rater is None
        else (args.second_rater if args.second_rater.is_absolute() else REPO / args.second_rater)
    )

    summary = score_diagnostic_quality(
        graded_path=graded_path,
        key_path=key_path,
        second_rater_path=sec_path,
        n_boot=args.n_boot,
        seed=args.seed,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out_dir / "tables.md").write_text(render_markdown(summary), encoding="utf-8")
    print(f"wrote {out_dir / 'summary.json'} and {out_dir / 'tables.md'} (n_graded={summary['n_graded']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
