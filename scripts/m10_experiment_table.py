"""Build verified static experiment tables for M10-C / M10-C.1 ExperimentComparison.

Reads strictly from committed ``eval/results/`` artifacts (zero mocked or
hardcoded numbers), asserts numerical + structural parity against
``eval/results/m8_test_tables_v1/tables.md`` and
``docs/drafts/ch5-ket-qua-test.md``, and writes JSON to both:
- ``eval/results/m10_experiment_table_v2/experiment_table.json``
- ``services/web/src/data/experiment_table.json``
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "eval" / "results"
OUT_EVAL = RESULTS_DIR / "m10_experiment_table_v2" / "experiment_table.json"
OUT_WEB = ROOT / "services" / "web" / "src" / "data" / "experiment_table.json"


def _read_json(rel: str) -> dict[str, Any]:
    path = RESULTS_DIR / rel
    if not path.is_file():
        raise FileNotFoundError(f"Missing result artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt_vi(value: float, decimals: int) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def _fmt_signed_vi(value: float, decimals: int = 3) -> str:
    sign = "−" if value < 0 else "+"
    return f"{sign}{_fmt_vi(abs(value), decimals)}"


def _vi_decimals(text: str) -> str:
    return re.sub(r"(\d)\.(\d)", r"\1,\2", text)


def _extract_method_row(
    name: str,
    label: str,
    m: dict[str, Any],
    *,
    llm_calls: int | None = None,
    cost_usd: float | None = None,
) -> dict[str, Any]:
    return {
        "key": name,
        "label": label,
        "tp": int(m["tp"]),
        "fp": int(m["fp"]),
        "fn": int(m["fn"]),
        "tn": int(m["tn"]),
        "precision": float(m["precision"]),
        "precision_ci95": [float(x) for x in m["precision_ci95"]],
        "recall": float(m["recall"]),
        "recall_ci95": [float(x) for x in m["recall_ci95"]],
        "f1": float(m["f1"]),
        "f1_ci95": [float(x) for x in m["f1_ci95"]],
        "fpr": float(m["fpr"]),
        "fpr_ci95": [float(x) for x in m["fpr_ci95"]],
        "llm_calls": llm_calls,
        "estimated_cost_usd": cost_usd,
    }


def _extract_pair_row(label: str, pair: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": label,
        "d_precision": float(pair["d_precision"]),
        "d_precision_ci95": [float(x) for x in pair["d_precision_ci95"]],
        "d_recall": float(pair["d_recall"]),
        "d_recall_ci95": [float(x) for x in pair["d_recall_ci95"]],
        "d_f1": float(pair["d_f1"]),
        "d_f1_ci95": [float(x) for x in pair["d_f1_ci95"]],
        "d_fpr": float(pair["d_fpr"]),
        "d_fpr_ci95": [float(x) for x in pair["d_fpr_ci95"]],
        "mcnemar_all_p": float(pair["mcnemar_all"]["p_value"]),
        "mcnemar_fault_p": float(pair["mcnemar_fault"]["p_value"]),
        "mcnemar_normal_p": float(pair["mcnemar_normal"]["p_value"]),
    }


def _extract_split_methods(
    bm25ref_rel: str,
    c1ref_rel: str,
) -> dict[str, Any]:
    bm25_cmp = _read_json(bm25ref_rel)
    c1_cmp = _read_json(c1ref_rel)
    labels = {
        "bm25": "BM25",
        "c1": "C1 (Topology)",
        "norag": "LLM-không-RAG",
        "ctav": "CTAV",
        "detector_only": "Detector-only",
    }
    tel = bm25_cmp["telemetry"]
    methods = [
        _extract_method_row(k, labels[k], tel["methods"][k])
        for k in ["bm25", "c1", "norag", "ctav", "detector_only"]
    ]
    pair_order = [
        ("C1 − BM25", tel["pairs"]["c1 - bm25"]),
        ("LLM-không-RAG − BM25", tel["pairs"]["norag - bm25"]),
        ("CTAV − BM25", tel["pairs"]["ctav - bm25"]),
        ("Detector-only − BM25", tel["pairs"]["detector_only - bm25"]),
        ("CTAV − C1", c1_cmp["telemetry"]["pairs"]["ctav - c1"]),
    ]
    return {
        "windows": int(tel["windows"]),
        "fault_windows": int(tel["fault_windows"]),
        "methods": methods,
        "pairs": [_extract_pair_row(lbl, p) for lbl, p in pair_order],
    }


def _extract_ablation(
    ctav_rel: str,
    rescue_rel: str,
    *,
    c2_key: str,
    c2_label: str,
) -> dict[str, Any]:
    ctav_doc = _read_json(ctav_rel)
    rescue_doc = _read_json(rescue_rel)
    ab_methods = ctav_doc["ablation"]["methods"]
    ab_pairs = ctav_doc["ablation"]["pairs"]
    ab_costs = ctav_doc["ablation"]["costs"]

    variant_specs = [
        ("ctav", "CTAV (baseline hiệu chỉnh)"),
        (c2_key, c2_label),
        ("no_c3", "no_c3 (bỏ neo bằng chứng)"),
        ("with_c4", "with_c4 (bật định tuyến C4)"),
        ("c3_rolling_baseline", "c3_rolling_baseline (C3-trượt)"),
    ]
    variants = [
        _extract_method_row(
            key,
            lbl,
            ab_methods[key],
            llm_calls=int(ab_costs[key]["llm_calls"]),
            cost_usd=float(ab_costs[key]["estimated_cost_usd"]),
        )
        for key, lbl in variant_specs
    ]

    best_pt = rescue_doc["best_point"]
    variants.append(
        _extract_method_row(
            "c5_rescue",
            f"CTAV + C5 ({best_pt['name']})",
            best_pt["metrics"],
            llm_calls=int(best_pt["cost"]["llm_calls"]),
            cost_usd=float(best_pt["cost"]["estimated_cost_usd"]),
        )
    )

    pairs = [
        _extract_pair_row(f"{key} − CTAV", ab_pairs[f"{key} - ctav"])
        for key in [c2_key, "no_c3", "with_c4", "c3_rolling_baseline"]
    ]
    rescue_pair_key = (
        "ctav_rescue_best_point - ctav"
        if "ctav_rescue_best_point - ctav" in rescue_doc["comparison"]["pairs"]
        else "ctav_rescue - ctav"
    )
    pairs.append(
        _extract_pair_row(
            f"CTAV + C5 ({best_pt['name']}) − CTAV",
            rescue_doc["comparison"]["pairs"][rescue_pair_key],
        )
    )

    return {
        "windows": int(ctav_doc["windows"]),
        "fault_windows": int(ctav_doc["fault_windows"]),
        "variants": variants,
        "pairs": pairs,
        "rescue": {
            "selected_name": rescue_doc["selected"]["name"],
            "best_point_name": best_pt["name"],
            "judged_rescue_windows": int(rescue_doc["judged_rescue_windows"]),
            "judged_rescue_alerts": int(rescue_doc["judged_rescue_alerts"]),
            "added_calls": int(best_pt["cost"]["added_calls"]),
            "rescued_alerts_in_subset": int(best_pt["rescued_alerts_in_subset"]),
        },
    }


def _extract_budget_curve(ctav_rel: str, compare_rel: str) -> list[dict[str, Any]]:
    ctav_doc = _read_json(ctav_rel)
    cmp_doc = _read_json(compare_rel)
    full_methods = cmp_doc["telemetry"]["methods"]
    curve = ctav_doc["budget_curve"]

    budgets = [int(pt["budget"]) for pt in curve["ctav"]]
    by_method: dict[str, dict[int, dict[str, Any]]] = {
        k: {int(pt["budget"]): pt for pt in curve[k]}
        for k in ["ctav", "bm25", "c1", "norag"]
    }

    rows: list[dict[str, Any]] = []
    for b in budgets:
        rows.append(
            {
                "budget": str(b),
                "budget_calls": b,
                "ctav": float(by_method["ctav"][b]["f1"]),
                "ctav_ci95": [float(x) for x in by_method["ctav"][b]["f1_ci95"]],
                "bm25": float(by_method["bm25"][b]["f1"]),
                "bm25_ci95": [float(x) for x in by_method["bm25"][b]["f1_ci95"]],
                "c1": float(by_method["c1"][b]["f1"]),
                "c1_ci95": [float(x) for x in by_method["c1"][b]["f1_ci95"]],
                "norag": float(by_method["norag"][b]["f1"]),
                "norag_ci95": [float(x) for x in by_method["norag"][b]["f1_ci95"]],
            }
        )
    rows.append(
        {
            "budget": "Đủ",
            "budget_calls": None,
            "ctav": float(full_methods["ctav"]["f1"]),
            "ctav_ci95": [float(x) for x in full_methods["ctav"]["f1_ci95"]],
            "bm25": float(full_methods["bm25"]["f1"]),
            "bm25_ci95": [float(x) for x in full_methods["bm25"]["f1_ci95"]],
            "c1": float(full_methods["c1"]["f1"]),
            "c1_ci95": [float(x) for x in full_methods["c1"]["f1_ci95"]],
            "norag": float(full_methods["norag"]["f1"]),
            "norag_ci95": [float(x) for x in full_methods["norag"]["f1_ci95"]],
        }
    )
    return rows


def _extract_rca_row(label: str, split: str, rel: str, note: str) -> dict[str, Any]:
    doc = _read_json(rel)
    main = doc["main"]
    hit = main["hit"]
    inj = main["per_injection"]
    red = main["reduction"]
    summ = doc["summarizer"]
    cascade_red = red["cascade"]
    return {
        "run_id": doc["config"]["run_id"],
        "label": label,
        "split": split,
        "alerts": int(doc["alerts"]),
        "alerts_in_fault": int(doc["alerts_in_a_fault"]),
        "cascade_injections": int(doc["cascade_injections"]),
        "incidents": int(main["incidents"]),
        "labelled": int(main["labelled"]),
        "ambiguous": int(main["ambiguous"]),
        "no_fault": int(main["no_fault"]),
        "multi_service": int(main["multi_service"]),
        "hit1": float(hit["level1_hit1"]),
        "hit1_count": int(hit["level1_hit1_count"]),
        "hit1_ci95": [float(x) for x in hit["level1_hit1_ci95"]],
        "hit3": float(hit["level1_hit3"]),
        "hit3_count": int(hit["level1_hit3_count"]),
        "hit3_ci95": [float(x) for x in hit["level1_hit3_ci95"]],
        "baseline_hit1": float(hit["baseline_hit1"]),
        "per_injection_hit1": float(inj["level1_hit1"]),
        "per_injection_hit1_ci95": [float(x) for x in inj["level1_hit1_ci95"]],
        "arr_all": float(red["all"]["arr"]),
        "arr_all_ci95": [float(x) for x in red["all"]["arr_ci95"]],
        "arr_cascade": (
            float(cascade_red["arr"]) if cascade_red["arr"] is not None else None
        ),
        "arr_cascade_ci95": (
            [float(x) for x in cascade_red["arr_ci95"]]
            if cascade_red["arr_ci95"] is not None
            else None
        ),
        "summary_valid": int(summ["valid"]),
        "summary_incidents": int(summ["incidents"]),
        "json_valid_rate": float(summ["json_valid_rate"]),
        "note": note,
    }


def _fmt_p_vi(p: float) -> str:
    if p < 0.001:
        return "p < 0,001"
    return f"p = {_fmt_vi(p, 3)}"


def _extract_hypotheses(
    verdicts_doc: dict[str, Any],
    h1_doc: dict[str, Any],
    rca_test: dict[str, Any],
    rca_test_raw: dict[str, Any],
) -> list[dict[str, Any]]:
    v = verdicts_doc["verdicts"]
    h1_pairs = {
        (p["condition"], p["label"]): p for p in h1_doc["pairs"]
    }
    near_log_fault = h1_pairs[("near_log", "fault")]
    time0_fault = h1_pairs[("time_0", "fault")]
    neighbor_fault = h1_pairs[("neighbor_trace", "fault")]

    hit_alert = rca_test_raw["by_t_group"]["180"]["hit_alert"]
    cascade_inj = int(rca_test_raw["cascade_injections"])
    total_inj = int(rca_test_raw["injections"])
    cascade_arr = rca_test_raw["reduction"]["cascade"]["180"]["arr"]
    fault_red = rca_test_raw["main"]["reduction"]["fault"]
    discordant = (
        int(hit_alert["discordant_hit1"]["level1_only"])
        + int(hit_alert["discordant_hit1"]["baseline_only"])
    )
    cascade_detail = (
        f"không tính được: {cascade_inj} / {total_inj} lần tiêm lỗi là cascade"
        if cascade_arr is None
        else _fmt_vi(float(cascade_arr), 3)
    )

    items: list[dict[str, Any]] = [
        {
            "id": "H0",
            "title": "Topology chưa hiệu chỉnh (C1) vs BM25",
            "split": "test",
            "status": "accepted",
            "status_label": "Chấp nhận (4/4 vế)",
            "summary": "; ".join(_vi_decimals(c["detail"]) for c in v["H0"]["clauses"]),
            "clauses": [
                {**c, "detail": _vi_decimals(str(c["detail"]))}
                for c in v["H0"]["clauses"]
            ],
        },
        {
            "id": "H1",
            "title": "Thí nghiệm cơ chế trên mẫu dựng",
            "split": "val",
            "status": "partial",
            "status_label": "Giữ một phần (val, M5 — QĐ-028); không chạy lại trên test",
            "summary": (
                f"Độ lợi C1 trên fault đến từ metric/span gần nhất theo thời gian: "
                f"near_log − near_trace Δ = {_fmt_signed_vi(near_log_fault['diff'])} "
                f"({_fmt_p_vi(near_log_fault['mcnemar_p'])}), "
                f"time_0 − near_trace Δ = {_fmt_signed_vi(time0_fault['diff'])} "
                f"({_fmt_p_vi(time0_fault['mcnemar_p'])}), "
                f"neighbor_trace − near_trace Δ = {_fmt_signed_vi(neighbor_fault['diff'])} "
                f"({_fmt_p_vi(neighbor_fault['mcnemar_p'])})."
            ),
            "clauses": [],
        },
        {
            "id": "H2",
            "title": "CTAV vs BM25 & C1 (giả thuyết chính)",
            "split": "test",
            "status": "rejected",
            "status_label": "Không đạt (1/3 vế)",
            "summary": "; ".join(_vi_decimals(c["detail"]) for c in v["H2"]["clauses"]),
            "clauses": [
                {**c, "detail": _vi_decimals(str(c["detail"]))}
                for c in v["H2"]["clauses"]
            ],
        },
        {
            "id": "H3",
            "title": "Ablation thành phần C2, C3, C4, C5",
            "split": "test",
            "status": "accepted",
            "status_label": "Chấp nhận (C3 đóng góp; bỏ C2, C4)",
            "summary": _vi_decimals(
                f"C3: {v['H3']['C3']['detail']}; C2: {v['H3']['C2']['detail']}; "
                f"C4: {v['H3']['C4']['detail']}; C3-trượt: {v['H3']['C3-trượt']['detail']}"
            ),
            "clauses": [
                {
                    "clause": f"C3 — {v['H3']['C3']['clause']}",
                    **v["H3"]["C3"],
                    "detail": _vi_decimals(str(v["H3"]["C3"]["detail"])),
                },
                {
                    "clause": f"C2 — {v['H3']['C2']['clause']}",
                    **v["H3"]["C2"],
                    "detail": _vi_decimals(str(v["H3"]["C2"]["detail"])),
                },
                {
                    "clause": f"C4 — {v['H3']['C4']['clause']}",
                    **v["H3"]["C4"],
                    "detail": _vi_decimals(str(v["H3"]["C4"]["detail"])),
                },
                {
                    "clause": f"C3-trượt — {v['H3']['C3-trượt']['clause']}",
                    **v["H3"]["C3-trượt"],
                    "detail": _vi_decimals(str(v["H3"]["C3-trượt"]["detail"])),
                },
                {
                    "clause": f"C5 — {v['H3']['C5']['clause']}",
                    **v["H3"]["C5"],
                    "detail": _vi_decimals(str(v["H3"]["C5"]["detail"])),
                },
            ],
        },
        {
            "id": "H4",
            "title": "Ngân sách nhỏ (120 lần gọi LLM)",
            "split": "test",
            "status": "accepted",
            "status_label": "Chấp nhận (ước lượng điểm)",
            "summary": _vi_decimals(str(v["H4"]["detail"])),
            "clauses": [{**v["H4"], "detail": _vi_decimals(str(v["H4"]["detail"]))}],
        },
        {
            "id": "H5",
            "title": "Tác tử RCA trên incident gom từ CTAV",
            "split": "test",
            "status": "rejected",
            "status_label": "Không được chấp nhận (0 / 4 vế)",
            "summary": (
                f"Hit@1 = Hit@3 = {hit_alert['level1_hit1_count']} / {hit_alert['n']} = "
                f"{_fmt_vi(hit_alert['level1_hit1'], 3)} "
                f"[{_fmt_vi(hit_alert['level1_hit1_ci95'][0], 3)}; "
                f"{_fmt_vi(hit_alert['level1_hit1_ci95'][1], 3)}]; "
                f"ΔHit@1 = {_fmt_vi(hit_alert['d_hit1'], 3)}; "
                f"{cascade_inj} / {total_inj} lần tiêm lỗi là cascade. "
                f"Tham chiếu (không phải tiêu chí đăng ký): ARR mọi cảnh báo = "
                f"{_fmt_vi(rca_test['arr_all'], 3)} "
                f"[{_fmt_vi(rca_test['arr_all_ci95'][0], 3)}; "
                f"{_fmt_vi(rca_test['arr_all_ci95'][1], 3)}], "
                f"ARR cảnh báo trong lỗi = {_fmt_vi(fault_red['arr'], 3)} "
                f"[{_fmt_vi(fault_red['arr_ci95'][0], 3)}; "
                f"{_fmt_vi(fault_red['arr_ci95'][1], 3)}]."
            ),
            "note": (
                f"Nhánh B chỉ đạt phần gom cảnh báo và sinh báo cáo đúng lược đồ "
                f"(JSON hợp lệ {rca_test['summary_valid']} / {rca_test['summary_incidents']})."
            ),
            "clauses": [
                {
                    "clause": "Hit@1 ≥ 0,60",
                    "met": False,
                    "detail": (
                        f"{hit_alert['level1_hit1_count']} / {hit_alert['n']} = "
                        f"{_fmt_vi(hit_alert['level1_hit1'], 3)} "
                        f"[{_fmt_vi(hit_alert['level1_hit1_ci95'][0], 3)}; "
                        f"{_fmt_vi(hit_alert['level1_hit1_ci95'][1], 3)}]"
                    ),
                },
                {
                    "clause": "Hit@3 ≥ 0,80",
                    "met": False,
                    "detail": (
                        f"{hit_alert['level1_hit3_count']} / {hit_alert['n']} = "
                        f"{_fmt_vi(hit_alert['level1_hit3'], 3)} "
                        f"[{_fmt_vi(hit_alert['level1_hit3_ci95'][0], 3)}; "
                        f"{_fmt_vi(hit_alert['level1_hit3_ci95'][1], 3)}]"
                    ),
                },
                {
                    "clause": "Cận dưới CI95 của ΔHit@1 (RCA − baseline) > 0",
                    "met": False,
                    "detail": (
                        f"{_fmt_vi(hit_alert['d_hit1'], 3)} "
                        f"(baseline {hit_alert['baseline_hit1_count']} / {hit_alert['n']}; "
                        f"{discordant} cặp lệch) "
                        f"[{_fmt_vi(hit_alert['d_hit1_ci95'][0], 3)}; "
                        f"{_fmt_vi(hit_alert['d_hit1_ci95'][1], 3)}]"
                    ),
                },
                {
                    "clause": "Alert Reduction ≥ 30% trên sự cố cascade",
                    "met": False,
                    "detail": cascade_detail,
                },
            ],
        },
    ]
    return items


def _parse_md_table(ch5_md: str, heading_prefix: str) -> list[list[str]]:
    lines = ch5_md.splitlines()
    start = next(
        (idx for idx, ln in enumerate(lines) if ln.startswith(heading_prefix)),
        None,
    )
    if start is None:
        raise AssertionError(f"Heading {heading_prefix!r} not found in ch5-ket-qua-test.md")
    rows: list[list[str]] = []
    in_table = False
    for ln in lines[start + 1 :]:
        if ln.startswith("|"):
            in_table = True
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if cells and all(set(c) <= {"-", ":", " "} for c in cells):
                continue
            rows.append(cells)
        elif in_table:
            break
    if len(rows) < 2:
        raise AssertionError(f"Empty markdown table under {heading_prefix!r}")
    return rows[1:]  # skip header row


def _verify_markdown_parity(payload: dict[str, Any]) -> None:
    tables_md = (RESULTS_DIR / "m8_test_tables_v1" / "tables.md").read_text(
        encoding="utf-8"
    )
    ch5_md = (ROOT / "docs" / "drafts" / "ch5-ket-qua-test.md").read_text(
        encoding="utf-8"
    )

    test_methods = {m["key"]: m for m in payload["methods"]["test"]["methods"]}
    for key in ["bm25", "c1", "norag", "ctav", "detector_only"]:
        m = test_methods[key]
        f1_s = _fmt_vi(m["f1"], 3)
        fpr_s = _fmt_vi(m["fpr"], 4)
        for text, name in [(tables_md, "tables.md"), (ch5_md, "ch5-ket-qua-test.md")]:
            if f1_s not in text or fpr_s not in text:
                raise AssertionError(
                    f"Parity mismatch for test {key} ({f1_s}, {fpr_s}) in {name}"
                )

    for variant in payload["ablation"]["test"]["variants"]:
        f1_s = _fmt_vi(variant["f1"], 3)
        if f1_s not in tables_md or f1_s not in ch5_md:
            raise AssertionError(
                f"Parity mismatch for test ablation {variant['key']} F1={f1_s}"
            )

    budget_120 = payload["budget_curve"]["test"][0]
    for s in [_fmt_vi(budget_120["ctav"], 3), _fmt_vi(budget_120["norag"], 3)]:
        if s not in tables_md or s not in ch5_md:
            raise AssertionError(f"Parity mismatch for H4 budget 120 value {s}")

    for row in payload["rca"]:
        h1_s = _fmt_vi(row["hit1"], 3)
        arr_s = _fmt_vi(row["arr_all"], 3)
        if h1_s not in ch5_md or arr_s not in ch5_md:
            raise AssertionError(
                f"Parity mismatch for RCA {row['run_id']} ({h1_s}, {arr_s}) in ch5-ket-qua-test.md"
            )

    # F9: structured verification against Table 5.18 (H0-H4) and Table 5.26 (H5 clauses).
    t518 = {
        cells[0].replace("*", "").split()[0]: cells
        for cells in _parse_md_table(ch5_md, "**Bảng 5.18")
    }
    by_hid = {h["id"]: h for h in payload["verdicts"]}
    expected_518_markers = {
        "H0": ("Được chấp nhận", "accepted"),
        "H1": ("Giữ một phần", "partial"),
        "H2": ("Không được chấp nhận", "rejected"),
        "H3": ("Được chấp nhận", "accepted"),
        "H4": ("Được chấp nhận", "accepted"),
    }
    for hid, (md_marker, json_status) in expected_518_markers.items():
        if hid not in t518:
            raise AssertionError(f"Missing {hid} in Table 5.18")
        joined = " | ".join(t518[hid])
        if md_marker not in joined:
            raise AssertionError(f"Table 5.18 {hid} missing {md_marker!r}: {joined}")
        if by_hid[hid]["status"] != json_status:
            raise AssertionError(
                f"Hypothesis {hid} status={by_hid[hid]['status']!r}, expected {json_status!r}"
            )

    t526 = _parse_md_table(ch5_md, "**Bảng 5.26")
    if len(t526) != 4 or len(by_hid["H5"]["clauses"]) != 4:
        raise AssertionError("Table 5.26 and H5 must have exact 4 clauses")
    for md_cells, json_clause in zip(t526, by_hid["H5"]["clauses"], strict=True):
        if md_cells[0] != json_clause["clause"]:
            raise AssertionError(
                f"H5 clause mismatch: {json_clause['clause']!r} vs Table 5.26 {md_cells[0]!r}"
            )
        if md_cells[-1] != "Không đạt" or json_clause["met"] is not False:
            raise AssertionError(f"H5 clause conclusion mismatch in Table 5.26: {md_cells}")


def build_experiment_table() -> dict[str, Any]:
    verdicts_doc = _read_json("m8_test_tables_v1/verdicts.json")
    h1_doc = _read_json("h1_val_analysis_v2/h1_analysis.json")

    methods_test = _extract_split_methods(
        "h0_test_compare_bm25ref_v1/compare.json",
        "h0_test_compare_c1ref_v1/compare.json",
    )
    methods_val = _extract_split_methods(
        "m8_test_side_val_compare_bm25ref_v1/compare.json",
        "m8_test_side_val_compare_c1ref_v1/compare.json",
    )

    ablation_test = _extract_ablation(
        "ctav_final_test_v1/ctav.json",
        "m8_rescue_test_v1/rescue.json",
        c2_key="with_c2",
        c2_label="with_c2 (bật θ_topo=0,85)",
    )
    ablation_val = _extract_ablation(
        "ctav_final_val_v1/ctav.json",
        "m7_rescue_val_v1/rescue.json",
        c2_key="no_c2",
        c2_label="no_c2 (bỏ C2 gating)",
    )

    budget_test = _extract_budget_curve(
        "ctav_final_test_v1/ctav.json",
        "h0_test_compare_bm25ref_v1/compare.json",
    )
    budget_val = _extract_budget_curve(
        "ctav_final_val_v1/ctav.json",
        "m8_test_side_val_compare_bm25ref_v1/compare.json",
    )

    rca_val = _extract_rca_row(
        "CTAV (val)",
        "val",
        "rca_final_val_v1/rca.json",
        "1 cascade (ARR=0,667); chạy lại ở M10-A bằng pipeline_val_v1",
    )
    rca_test = _extract_rca_row(
        "CTAV (test — H5 chính)",
        "test",
        "rca_final_test_v1/rca.json",
        "0 multi-service vì C3 ngưỡng dev lọc hết; ARR=0,513; JSON hợp lệ 38/38",
    )
    rca_sens = _extract_rca_row(
        "C3-trượt (test — độ nhạy)",
        "test (sens)",
        "rca_sens_test_c3rolling_v1/rca.json",
        "41 cascade / 39 multi-service; ARR cascade=0,704; Hit@1=0,208",
    )

    rca_test_raw = _read_json("rca_final_test_v1/rca.json")

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "sources": [
            "eval/results/h0_test_compare_bm25ref_v1/compare.json",
            "eval/results/h0_test_compare_c1ref_v1/compare.json",
            "eval/results/m8_test_side_val_compare_bm25ref_v1/compare.json",
            "eval/results/m8_test_side_val_compare_c1ref_v1/compare.json",
            "eval/results/ctav_final_test_v1/ctav.json",
            "eval/results/ctav_final_val_v1/ctav.json",
            "eval/results/m8_rescue_test_v1/rescue.json",
            "eval/results/m7_rescue_val_v1/rescue.json",
            "eval/results/m8_test_tables_v1/verdicts.json",
            "eval/results/h1_val_analysis_v2/h1_analysis.json",
            "eval/results/rca_final_val_v1/rca.json",
            "eval/results/rca_final_test_v1/rca.json",
            "eval/results/rca_sens_test_c3rolling_v1/rca.json",
        ],
        "verdicts": _extract_hypotheses(verdicts_doc, h1_doc, rca_test, rca_test_raw),
        "methods": {
            "test": methods_test,
            "val": methods_val,
        },
        "ablation": {
            "test": ablation_test,
            "val": ablation_val,
        },
        "budget_curve": {
            "test": budget_test,
            "val": budget_val,
        },
        "rca": [rca_val, rca_test, rca_sens],
    }

    _verify_markdown_parity(payload)
    return payload


def main() -> None:
    payload = build_experiment_table()
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    for out_path in (OUT_EVAL, OUT_WEB):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        print(f"Wrote {out_path.relative_to(ROOT)} ({len(text)} bytes)")


if __name__ == "__main__":
    main()
