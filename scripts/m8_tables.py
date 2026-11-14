"""Tables H0-H4 of the G-test and the verdict of each registered criterion (M8). No LLM call.

    py scripts/m8_tables.py --split test \
        --compare-bm25 <compare run, reference bm25: bm25, c1, norag, ctav, detector_only> \
        --compare-c1 <compare run, reference c1: c1, ctav> \
        --ctav <ctav run> [--rescue <rescue run>] --out <name>

Reads only what `py -m eval compare|ctav|rescue` already wrote; it computes no new statistic.
The criteria are the ones registered at the end of docs/experiment-log.md (commit be2b985) and
are applied literally on the main subset (windows with telemetry). Writes `tables.md` and
`verdicts.json` to eval/results/<out>/ (must not exist).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from eval.harness.runner import RESULTS, _git_commit  # noqa: E402

DELTA = 0.05  # V33 (a), QD-034
ALPHA = 0.05
NAMES = {"bm25": "BM25", "c1": "C1", "norag": "LLM-không-RAG", "ctav": "CTAV", "detector_only": "Detector-only"}


def num(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def signed(value: float, digits: int = 3) -> str:
    return ("+" if value >= 0 else "−") + num(abs(value), digits)


def ci(pair: list[float], digits: int = 3, sign: bool = False) -> str:
    f = signed if sign else num
    return f"[{f(pair[0], digits)}; {f(pair[1], digits)}]"


def pval(p: float, prefix: str = "") -> str:
    """`prefix` = "p " gives "p < 0,001" / "p = 0,012"."""
    if p < 0.001:
        return f"{prefix}< 0,001"
    return f"{prefix}= {num(p, 3)}" if prefix else num(p, 3)


def thousands(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _load(run: str, name: str) -> dict[str, Any]:
    with (RESULTS / run / name).open(encoding="utf-8") as handle:
        return dict(json.load(handle))


def methods_table(block: dict[str, Any], title: str) -> list[str]:
    out = [f"**{title}** ({thousands(block['windows'])} cửa sổ, {block['fault_windows']} fault).", "",
           "| Phương pháp | TP | FP | Precision | Recall [CI95] | F1 [CI95] | FPR [CI95] |", "|---|---:|---:|---:|---|---|---|"]
    for name, m in block["methods"].items():
        out.append(
            f"| {NAMES.get(name, name)} | {thousands(m['tp'])} | {thousands(m['fp'])} | {num(m['precision'])} | "
            f"{num(m['recall'])} {ci(m['recall_ci95'])} | {num(m['f1'])} {ci(m['f1_ci95'])} | "
            f"{num(m['fpr'], 4)} {ci(m['fpr_ci95'], 4)} |"
        )
    return out


def pairs_table(pairs: dict[str, Any], title: str) -> list[str]:
    out = [f"**{title}**", "",
           "| Hiệu | ΔRecall [CI95] | ΔFPR [CI95] | ΔF1 [CI95] | ΔPrecision [CI95] | McNemar p (mọi / fault / normal) |",
           "|---|---|---|---|---|---|"]
    for name, p in pairs.items():
        a, b = name.split(" - ")
        out.append(
            f"| {NAMES.get(a, a)} − {NAMES.get(b, b)} | {signed(p['d_recall'])} {ci(p['d_recall_ci95'], sign=True)} | "
            f"{signed(p['d_fpr'], 4)} {ci(p['d_fpr_ci95'], 4, True)} | {signed(p['d_f1'])} {ci(p['d_f1_ci95'], sign=True)} | "
            f"{signed(p['d_precision'])} {ci(p['d_precision_ci95'], sign=True)} | "
            f"{pval(p['mcnemar_all']['p_value'])} / {pval(p['mcnemar_fault']['p_value'])} / {pval(p['mcnemar_normal']['p_value'])} |"
        )
    return out


def clause(text: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"clause": text, "met": bool(ok), "detail": detail}


def verdicts(bm25ref: dict[str, Any], c1ref: dict[str, Any], ctav: dict[str, Any], rescue: dict[str, Any] | None) -> dict[str, Any]:
    """The registered criteria, literally. `bm25ref` / `c1ref` are the telemetry blocks of the compares."""
    out: dict[str, Any] = {}
    h0 = bm25ref["pairs"]["c1 - bm25"]
    out["H0"] = {"clauses": [
        clause("CI ΔRecall(C1 − BM25) có cận dưới > 0", h0["d_recall_ci95"][0] > 0,
               f"{signed(h0['d_recall'])} {ci(h0['d_recall_ci95'], sign=True)}"),
        clause("CI ΔFPR(C1 − BM25) có cận dưới > 0", h0["d_fpr_ci95"][0] > 0,
               f"{signed(h0['d_fpr'], 4)} {ci(h0['d_fpr_ci95'], 4, True)}"),
        clause("McNemar fault p < 0,05", h0["mcnemar_fault"]["p_value"] < ALPHA, pval(h0["mcnemar_fault"]["p_value"], "p ")),
        clause("McNemar normal p < 0,05", h0["mcnemar_normal"]["p_value"] < ALPHA, pval(h0["mcnemar_normal"]["p_value"], "p ")),
    ]}  # fmt: skip
    out["H0"]["accepted"] = all(c["met"] for c in out["H0"]["clauses"])

    h2 = bm25ref["pairs"]["ctav - bm25"]
    h2c = c1ref["pairs"]["ctav - c1"]
    clauses = [
        clause("(i) CI ΔF1(CTAV − BM25) cận dưới > 0 và McNemar p < 0,05",
               h2["d_f1_ci95"][0] > 0 and h2["mcnemar_all"]["p_value"] < ALPHA,
               f"ΔF1 {signed(h2['d_f1'])} {ci(h2['d_f1_ci95'], sign=True)}; McNemar {pval(h2['mcnemar_all']['p_value'], 'p ')}"),
        clause("(ii) CI ΔFPR(CTAV − BM25) không có cận dưới > 0", not h2["d_fpr_ci95"][0] > 0,
               f"ΔFPR {signed(h2['d_fpr'], 4)} {ci(h2['d_fpr_ci95'], 4, True)}"),
        clause(f"(iii) ΔRecall(CTAV − C1) ≥ −{num(DELTA, 2)} (ước lượng điểm)", h2c["d_recall"] >= -DELTA,
               f"ΔRecall {signed(h2c['d_recall'])} {ci(h2c['d_recall_ci95'], sign=True)}"),
    ]  # fmt: skip
    met = [c["met"] for c in clauses]
    out["H2"] = {"clauses": clauses, "accepted": all(met),
                 "label": "đạt" if all(met) else "đạt một phần" if met[0] and met[1] else "không đạt"}

    pairs, costs = ctav["ablation"]["pairs"], ctav["ablation"]["costs"]
    h3: dict[str, Any] = {}
    c3 = pairs["no_c3 - ctav"]
    h3["C3"] = clause("bỏ C3 ⇒ CI ΔPrecision cận trên < 0 (C3 đóng góp)", c3["d_precision_ci95"][1] < 0,
                      f"ΔPrecision {signed(c3['d_precision'])} {ci(c3['d_precision_ci95'], sign=True)}")
    if "with_c2 - ctav" in pairs:
        c2 = pairs["with_c2 - ctav"]
        h3["C2"] = clause("thêm C2 (θ_topo 0,85): xác nhận bỏ nếu CI ΔFPR chứa 0 hoặc > 0", not c2["d_fpr_ci95"][1] < 0,
                          f"ΔFPR {signed(c2['d_fpr'], 4)} {ci(c2['d_fpr_ci95'], 4, True)}")
    if "with_c4 - ctav" in pairs:
        c4 = pairs["with_c4 - ctav"]
        more = costs["with_c4"]["estimated_cost_usd"] > costs["ctav"]["estimated_cost_usd"]
        h3["C4"] = clause("thêm C4: xác nhận bỏ nếu chi phí tăng và CI ΔF1 không có cận dưới > 0",
                          more and not c4["d_f1_ci95"][0] > 0,
                          f"ΔF1 {signed(c4['d_f1'])} {ci(c4['d_f1_ci95'], sign=True)}; chi phí "
                          f"{num(costs['with_c4']['estimated_cost_usd'], 2)} so với {num(costs['ctav']['estimated_cost_usd'], 2)} USD")
    rolling = next((k for k in pairs if k.startswith("c3_") and k.endswith("_baseline - ctav")), None)
    if rolling:
        r = pairs[rolling]
        h3["C3-trượt"] = {"clause": "báo ΔF1, ΔFPR (không có tiêu chí đạt / không đạt)", "met": None,
                          "detail": f"ΔF1 {signed(r['d_f1'])} {ci(r['d_f1_ci95'], sign=True)}; "
                                    f"ΔFPR {signed(r['d_fpr'], 4)} {ci(r['d_fpr_ci95'], 4, True)}; "
                                    f"ΔRecall {signed(r['d_recall'])} {ci(r['d_recall_ci95'], sign=True)}"}
    if rescue is not None:
        off = rescue["face_pairs"]["pairs"]["off - best"]  # reference = the C5 point
        best = rescue["best_point"]
        h3["C5"] = {"clause": "báo ΔRecall, ΔFPR, +lần gọi (không có tiêu chí đạt / không đạt)", "met": None,
                    "detail": f"điểm {best['name']}: ΔRecall {signed(-off['d_recall'])} "
                              f"[{signed(-off['d_recall_ci95'][1])}; {signed(-off['d_recall_ci95'][0])}]; "
                              f"ΔFPR {signed(-off['d_fpr'], 4)} [{signed(-off['d_fpr_ci95'][1], 4)}; {signed(-off['d_fpr_ci95'][0], 4)}]; "
                              f"ΔF1 {signed(-off['d_f1'])} [{signed(-off['d_f1_ci95'][1])}; {signed(-off['d_f1_ci95'][0])}]; "
                              f"+{best['cost']['added_calls']} lần gọi"}
    out["H3"] = h3

    curve = ctav.get("budget_curve") or {}
    if curve:
        at = {name: next(p for p in points if p["budget"] == 120) for name, points in curve.items()}
        out["H4"] = clause("F1(CTAV) ≥ F1(LLM-không-RAG) ở ngân sách 120 lần gọi (ước lượng điểm)",
                           at["ctav"]["f1"] >= at["norag"]["f1"],
                           f"CTAV {num(at['ctav']['f1'])} {ci(at['ctav']['f1_ci95'])}; không-RAG {num(at['norag']['f1'])} {ci(at['norag']['f1_ci95'])}")
    return out


def mark(met: bool | None) -> str:
    return "—" if met is None else "**đạt**" if met else "**không đạt**"


def render(split: str, bm25ref: dict[str, Any], c1ref: dict[str, Any], ctav: dict[str, Any],
           rescue: dict[str, Any] | None, v: dict[str, Any]) -> str:
    out = [f"# Bảng G-test — `{split}`", ""]
    for subset, label in (("telemetry", "cửa sổ có telemetry — chỉ số chính"), ("all", "mọi cửa sổ — phụ")):
        out += methods_table(bm25ref[subset], f"Bảng {split}-1 ({label})") + [""]
        merged = {**bm25ref[subset]["pairs"], **c1ref[subset]["pairs"]}
        out += pairs_table(merged, f"Bảng {split}-2 ({label}): hiệu ghép cặp") + [""]

    out += [f"**Bảng {split}-3. Tiêu chí đã đăng ký (cửa sổ có telemetry).**", "", "| Giả thuyết | Vế | Số đo | Kết quả |", "|---|---|---|---|"]
    for c in v["H0"]["clauses"]:
        out.append(f"| H0 | {c['clause']} | {c['detail']} | {mark(c['met'])} |")
    out.append(f"| H0 | **Kết luận** | | {'**chấp nhận**' if v['H0']['accepted'] else '**không chấp nhận**'} |")
    for c in v["H2"]["clauses"]:
        out.append(f"| H2 | {c['clause']} | {c['detail']} | {mark(c['met'])} |")
    out.append(f"| H2 | **Kết luận** | | **H2 {v['H2']['label']}** |")
    for name, c in v["H3"].items():
        out.append(f"| H3 — {name} | {c['clause']} | {c['detail']} | {mark(c['met'])} |")
    if "H4" in v:
        out.append(f"| H4 | {v['H4']['clause']} | {v['H4']['detail']} | {mark(v['H4']['met'])} |")

    ab = ctav["ablation"]
    out += ["", f"**Bảng {split}-4. Ablation H3 quanh CTAV (cửa sổ có telemetry).**", "",
            "| Biến thể | TP | FP | Precision | Recall | F1 [CI95] | FPR | Lần gọi LLM | USD theo token |", "|---|---:|---:|---:|---:|---|---:|---:|---:|"]
    for name, m in ab["methods"].items():
        cost = ab["costs"][name]
        out.append(f"| {name} | {m['tp']} | {m['fp']} | {num(m['precision'])} | {num(m['recall'])} | {num(m['f1'])} {ci(m['f1_ci95'])} | "
                   f"{num(m['fpr'], 4)} | {thousands(cost['llm_calls'])} | {num(cost['estimated_cost_usd'], 2)} |")
    if rescue is not None:
        best, off = rescue["best_point"], rescue["off"]
        for name, r in (("ctav (off, đối chiếu C5)", off), (f"ctav + C5 {best['name']}", best)):
            m = r["metrics"]
            out.append(f"| {name} | {m['tp']} | {m['fp']} | {num(m['precision'])} | {num(m['recall'])} | {num(m['f1'])} {ci(m['f1_ci95'])} | "
                       f"{num(m['fpr'], 4)} | {thousands(r['cost']['llm_calls'])} | {num(r['cost']['estimated_cost_usd'], 2)} |")
    out += [""] + pairs_table(ab["pairs"], f"Bảng {split}-5. Ablation: hiệu ghép cặp so với CTAV")

    curve = ctav.get("budget_curve") or {}
    if curve:
        budgets = [p["budget"] for p in curve["ctav"]]
        full = {name: bm25ref["telemetry"]["methods"].get(name) for name in curve}
        out += ["", f"**Bảng {split}-6. F1 theo ngân sách lần gọi LLM (cửa sổ có telemetry; candidate theo thứ tự thời gian).**", "",
                "| Phương pháp | " + " | ".join(str(b) for b in budgets) + " | đủ |", "|---|" + "---:|" * (len(budgets) + 1)]
        for name, points in curve.items():
            cells = [num(p["f1"]) for p in points]
            cells.append(num(full[name]["f1"]) if full.get(name) else "—")
            out.append(f"| {NAMES.get(name, name)} | " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", required=True)
    parser.add_argument("--compare-bm25", required=True)
    parser.add_argument("--compare-c1", required=True)
    parser.add_argument("--ctav", required=True)
    parser.add_argument("--rescue", default="")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    out_dir = RESULTS / args.out
    if out_dir.exists():
        raise SystemExit(f"{out_dir} already exists: results are never overwritten")
    bm25ref = _load(args.compare_bm25, "compare.json")
    c1ref = _load(args.compare_c1, "compare.json")
    ctav = _load(args.ctav, "ctav.json")
    rescue = _load(args.rescue, "rescue.json") if args.rescue else None
    if ctav.get("subset", "telemetry") != "telemetry":
        raise SystemExit("the registered main subset is `telemetry`")
    v = verdicts(bm25ref["telemetry"], c1ref["telemetry"], ctav, rescue)
    text = render(args.split, bm25ref, c1ref, ctav, rescue, v)
    out_dir.mkdir(parents=True)
    (out_dir / "tables.md").write_text(text, encoding="utf-8")
    report = {"created_at": datetime.now(UTC).isoformat(), "split": args.split, "git_commit": _git_commit(),
              "inputs": {"compare_bm25": args.compare_bm25, "compare_c1": args.compare_c1, "ctav": args.ctav, "rescue": args.rescue},
              "delta": DELTA, "alpha": ALPHA, "verdicts": v}
    (out_dir / "verdicts.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(text)
    print(f"wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
