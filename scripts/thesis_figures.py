"""Vẽ các biểu đồ số liệu của luận văn (PNG, 300 dpi, chữ trên hình bằng tiếng Anh).

Chỉ gồm các hình được giữ sau đợt cắt hình 2026-11-18 (outline mục 5); H5.5, H5.6 dùng ở Phụ lục D.

Mỗi hình là một hàm, đọc thẳng kết quả đã lưu trong ``eval/results/`` (hoặc ``data/``), không nhập số tay.
Màu theo bảng màu tham chiếu của skill dataviz (đã kiểm bằng ``validate_palette.js``): mỗi phương pháp giữ một màu cố
định ở mọi hình; phương pháp tham chiếu (không RAG, chỉ detector) dùng xám đậm kèm nhãn trực tiếp. Chỉ xuất PNG.

    py scripts/thesis_figures.py              # vẽ tất cả
    py scripts/thesis_figures.py --only h5.9  # vẽ một hình

Danh mục hình và caption: ``docs/drafts/figures/danh-sach-bieu-do.md``.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.ticker import FuncFormatter, NullFormatter  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "eval" / "results"
OUT = REPO / "docs" / "drafts" / "figures"
DPI = 300
WIDTH = 6.3  # inch, A4 text width

# Reference palette (light mode, white surface).
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
YELLOW = "#eda100"
GREEN = "#008300"
VIOLET = "#6250d6"
NEUTRAL = "#52514e"  # reference methods, always with a direct label
LIGHT_NEUTRAL = "#8a8985"  # "all" / background class
BLUE_LIGHT = "#9ec5f4"
SURFACE_MUTED = "#e4e3df"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e6e5e1"

METHODS: dict[str, tuple[str, str, str]] = {  # key -> (label, colour, marker)
    "bm25": ("BM25", BLUE, "o"),
    "c1": ("C1 (BM25 + topology)", ORANGE, "o"),
    "ctav": ("CTAV", AQUA, "o"),
    "norag": ("LLM without RAG", NEUTRAL, "D"),
    "detector_only": ("Detector only", NEUTRAL, "s"),
}

plt.rcParams.update(
    {
        "font.family": ["Segoe UI", "DejaVu Sans"],
        "font.size": 8,
        "axes.titlesize": 8.5,
        "axes.titleweight": "semibold",
        "axes.titlecolor": INK,
        "axes.labelsize": 8,
        "axes.labelcolor": INK_2,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "xtick.color": INK_2,
        "ytick.color": INK_2,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "legend.fontsize": 7.5,
        "legend.frameon": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.edgecolor": "#b9b8b2",
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "text.color": INK,
        "lines.linewidth": 1.6,
        "lines.markersize": 5.5,
        "errorbar.capsize": 2.5,
    }
)


# ----------------------------------------------------------------------------- helpers


def load(rel: str) -> Any:
    return json.loads((RES / rel).read_text(encoding="utf-8"))


def num(x: float, nd: int = 3) -> str:
    return f"{x:,.{nd}f}".replace("-", "−")


def pct(x: float, nd: int = 0) -> str:
    return f"{100 * x:.{nd}f}%"


def fmt_axis(ax: Axes, axis: str = "y", nd: int = 2, percent: bool = False) -> None:
    def fmt(v: float, _pos: int) -> str:
        return pct(v) if percent else num(v, nd)

    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(FuncFormatter(fmt))


def save(fig: Figure, rel: str) -> None:
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  {path.relative_to(REPO)}")


def title(ax: Axes, text: str) -> None:
    ax.set_title(text, loc="left", pad=8)


def err(value: float, ci: list[float]) -> list[list[float]]:
    return [[max(value - ci[0], 0.0)], [max(ci[1] - value, 0.0)]]


def bars(ax: Axes, x: float, h: float, w: float, color: str, label: str | None = None) -> None:
    """Bar with a white 1 pt outline: the surface gap between adjacent fills."""
    ax.bar(x, h, w, color=color, edgecolor="white", linewidth=1.0, label=label, zorder=2)


def legend_top(ax: Axes, ncol: int, **kw: Any) -> None:
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.06), ncol=ncol, handlelength=1.4, columnspacing=1.2,
              borderaxespad=0, **kw)


def value_label(ax: Axes, x: float, y: float, text: str, **kw: Any) -> None:
    ax.text(x, y, text, ha="center", va="bottom", fontsize=6.6, color=INK_2, **kw)


# ----------------------------------------------------------------------------- Chapter 2


def h2_4_service_graph() -> None:
    """H2.4 — Service dependency graph (56 services, 68 edges), with 1- and 2-hop neighbourhoods."""
    g = json.loads((REPO / "data" / "graph" / "service_graph.json").read_text(encoding="utf-8"))
    full = nx.Graph()
    full.add_nodes_from(g["nodes"])
    full.add_edges_from((e["source"], e["target"]) for e in g["edges"])

    def short(name: str) -> str:
        return name.removeprefix("ts-").removesuffix("-service").removesuffix("service") or name

    systems = [
        ("(a) Online Boutique", [n for n in full if not n.startswith("ts-")], "paymentservice", 120, 6.6),
        ("(b) Train Ticket", [n for n in full if n.startswith("ts-")], "ts-travel-service", 60, 5.6),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 3.9), gridspec_kw={"width_ratios": [1, 1.7]})
    for ax, (name, nodes, focus, node_size, font_size) in zip(axes, systems, strict=True):
        sub = full.subgraph(nodes)
        core = sub.subgraph([n for n in sub if sub.degree(n) > 0])
        isolated = sorted(n for n in sub if sub.degree(n) == 0)
        pos = nx.kamada_kawai_layout(core)
        if core.number_of_nodes() > 15:  # Train Ticket is dense: spread it with a spring pass from kamada-kawai
            pos = nx.spring_layout(core, pos=pos, k=0.6, iterations=300, seed=42)
        hop = nx.single_source_shortest_path_length(core, focus, cutoff=2)
        palette = {0: ORANGE, 1: BLUE, 2: BLUE_LIGHT}
        colors = [palette.get(hop.get(n, 99), SURFACE_MUTED) for n in core]
        nx.draw_networkx_edges(core, pos, ax=ax, edge_color="#c4c3bd", width=0.6)
        art = nx.draw_networkx_nodes(
            core, pos, ax=ax, node_color=colors, edgecolors="white", linewidths=0.8,
            node_size=[node_size * (1.8 if n == focus else 1) for n in core],
        )
        art.set_zorder(3)
        for n, (x, y) in pos.items():
            ax.text(x, y - 0.06, short(n), ha="center", va="top", fontsize=font_size, zorder=4,
                    color=INK if n == focus else INK_2, fontweight="semibold" if n == focus else "normal")
        if isolated:
            ax.text(0.0, -0.02, f"{len(isolated)} services with no trace edges are not drawn",
                    transform=ax.transAxes, fontsize=6.2, color=INK_2, va="top")
        title(ax, f"{name}\n{sub.number_of_nodes()} services, {sub.number_of_edges()} edges")
        ax.axis("off")
    handles = [
        plt.Line2D([], [], marker="o", ls="", markerfacecolor=c, markeredgecolor="white", markersize=8, label=lab)
        for c, lab in [(ORANGE, "alerting service $s_0$"), (BLUE, "1-hop neighbour"),
                       (BLUE_LIGHT, "2-hop neighbour"), (SURFACE_MUTED, "farther than 2 hops")]
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.05))
    fig.tight_layout()
    save(fig, "ch2/h2.4-service-graph.png")


# ----------------------------------------------------------------------------- Chapter 5


def h5_4_h1_time() -> None:
    """H5.4 — H1: judge TRUE_ALERT rate vs share of evidence close to alert time (val)."""
    d = load("h1_val_analysis_v2/h1_analysis.json")
    levels = [("time_0", 0.0), ("time_33", 1 / 3), ("time_67", 2 / 3), ("near_trace", 1.0)]
    fig, ax = plt.subplots(figsize=(WIDTH * 0.62, 2.7))
    for label, name, color, marker, dx in [("fault", "Fault windows", VIOLET, "o", 0.012),
                                           ("normal", "Normal windows", LIGHT_NEUTRAL, "s", -0.012)]:
        m = [d["conditions"][cond][label] for cond, _ in levels]
        ys = [x["raw_true"] for x in m]
        yerr = [[y - x["raw_true_ci95"][0] for x, y in zip(m, ys, strict=True)],
                [x["raw_true_ci95"][1] - y for x, y in zip(m, ys, strict=True)]]
        t = d["time_trend"][label]
        ax.errorbar([s + dx for _, s in levels], ys, yerr=yerr, color=color, marker=marker, lw=1.6,
                    label=f"{name} (n = {t['n']}), slope {num(t['slope_raw_true_per_share'], 2)} "
                          f"[{num(t['slope_ci95'][0], 2)}, {num(t['slope_ci95'][1], 2)}]")
    ax.set_xticks([s for _, s in levels], ["0%", "33%", "67%", "100%"])
    ax.set_xlabel("Share of trace evidence close to the alert time")
    ax.set_ylabel("Judge TRUE_ALERT rate")
    ax.set_ylim(0.2, 0.85)
    fmt_axis(ax, percent=True)
    legend_top(ax, ncol=1)
    fig.tight_layout()
    save(fig, "ch5/h5.4-h1-time-proximity.png")


def h5_5_theta_curve() -> None:
    """H5.5 — θ_topo sweep on val (C1 judges every candidate, C3 with the dev p90 baseline)."""
    pts = load("m6_ctav_select_val_v2/ctav.json")["sweep"]["points"]
    rows = sorted(
        (p for p in pts
         if p["variant"]["mode"] == "topology_only" and p["variant"]["baseline"] == "dev"
         and p["variant"]["percentile"] == 90 and p["variant"]["fp_confidence"] == 0.8),
        key=lambda p: p["variant"]["theta_topo"],
    )
    th = [p["variant"]["theta_topo"] for p in rows]
    m = [p["metrics"] for p in rows]
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.5))
    for ax, key, name, ymax, nd in [(axes[0], "recall", "(a) Recall", 0.24, 2), (axes[1], "fpr", "(b) FPR", 0.012, 3)]:
        ys = [x[key] for x in m]
        yerr = [[y - x[f"{key}_ci95"][0] for x, y in zip(m, ys, strict=True)],
                [x[f"{key}_ci95"][1] - y for x, y in zip(m, ys, strict=True)]]
        ax.errorbar(th, ys, yerr=yerr, color=AQUA, marker="o", drawstyle="steps-mid")
        for t, x, y in zip(th, m, ys, strict=True):
            last = t == th[-1]
            ax.annotate(f"TP {x['tp']}\nFP {x['fp']}" if last else f"TP {x['tp']} / FP {x['fp']}", (t, y),
                        textcoords="offset points", xytext=(0, 9) if last else (6, 5),
                        ha="center" if last else "left", va="bottom", fontsize=6.4, color=INK_2)
        ax.axvline(0.80, color=INK_2, ls="--", lw=0.8)
        ax.text(0.803, ymax * 0.95, "selected θ = 0.80", fontsize=6.4, color=INK_2, va="top")
        ax.set_xticks(th, [num(t, 2) for t in th])
        ax.set_xlabel("Confidence threshold θ_topo")
        ax.set_ylim(0, ymax)
        fmt_axis(ax, nd=nd)
        title(ax, name)
    fig.tight_layout()
    save(fig, "ch5/h5.5-theta-sweep-val.png")


def h5_6_rescue_tau() -> None:
    """H5.6 — τ sweep of the Rescue gate (C5) on val at η = (0, 0.4, 0.6)."""
    with (RES / "m7_rescue_val_v1" / "points.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    off = next(r for r in rows if r["name"] == "off")
    sel = sorted(
        (r for r in rows if r["name"] != "off" and (r["eta1"], r["eta2"], r["eta3"]) == ("0.0", "0.4", "0.6")),
        key=lambda r: float(r["tau"]),
    )
    tau = [float(r["tau"]) for r in sel]
    fig, axes = plt.subplots(1, 3, figsize=(WIDTH, 2.4))
    specs = [("recall", "(a) Recall", 2, 0.2), ("fpr", "(b) FPR", 3, 0.016), ("added_calls", "(c) Extra LLM calls", 0, None)]
    for ax, (key, name, nd, ymax) in zip(axes, specs, strict=True):
        ax.plot(tau, [float(r[key]) for r in sel], color=AQUA, marker="o", label="CTAV + C5")
        if key != "added_calls":
            ax.axhline(float(off[key]), color=INK_2, ls=":", lw=1.1, label="CTAV without C5")
        ax.axvline(0.8, color=INK_2, ls="--", lw=0.8)
        ax.set_xlabel("Rescue threshold τ")
        ax.set_xticks([0.3, 0.5, 0.7, 0.9], ["0.3", "0.5", "0.7", "0.9"])
        ax.set_ylim(0, ymax)
        fmt_axis(ax, nd=nd)
        title(ax, name)
    axes[0].legend(loc="lower left", fontsize=6.6)
    fig.tight_layout()
    save(fig, "ch5/h5.6-rescue-tau-val.png")


def h5_8_detector_shift() -> None:
    """H5.8 — Share of windows promoted to candidate per split, by system and by window label."""
    d = load("m8_detector_shift_test_v1/shift.json")["splits"]
    splits = ["dev", "val", "test"]

    def by_system(split: str, tt: bool) -> float:
        svc = d[split]["by_service"]
        win = sum(v["windows"] for k, v in svc.items() if k.startswith("ts-") == tt)
        return sum(v["candidates"] for k, v in svc.items() if k.startswith("ts-") == tt) / win

    panels: list[tuple[str, list[tuple[str, Callable[[str], float], str]]]] = [
        ("(a) By system", [("All", lambda s: d[s]["rate"], LIGHT_NEUTRAL),
                           ("Online Boutique", lambda s: by_system(s, False), YELLOW),
                           ("Train Ticket", lambda s: by_system(s, True), GREEN)]),
        ("(b) By window label", [("Fault", lambda s: d[s]["by_label"]["fault"]["rate"], VIOLET),
                                 ("Normal", lambda s: d[s]["by_label"]["normal"]["rate"], LIGHT_NEUTRAL)]),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.7), sharey=True)
    for ax, (name, series) in zip(axes, panels, strict=True):
        w = 0.8 / len(series)
        for j, (lab, fn, color) in enumerate(series):
            for i, s in enumerate(splits):
                x = i + (j - (len(series) - 1) / 2) * w
                v = fn(s)
                bars(ax, x, v, w, color, lab if i == 0 else None)
                value_label(ax, x, v + 0.01, pct(v))
        ax.set_xticks(range(3), splits)
        ax.set_ylim(0, 0.75)
        fmt_axis(ax, percent=True)
        title(ax, name)
        ax.legend(loc="upper left", fontsize=6.8)
    axes[0].set_ylabel("Windows promoted to candidate")
    fig.tight_layout()
    save(fig, "ch5/h5.8-candidate-rate-by-split.png")


def h5_9_operating_points() -> None:
    """H5.9 — Recall–FPR operating points: val (hollow) and test (filled, 95% CI)."""
    runs = {"val": load("ctav_final_val_v1/ctav.json")["baselines"]["methods"],
            "test": load("ctav_final_test_v1/ctav.json")["baselines"]["methods"]}
    offsets = {"bm25": (8, -16), "norag": (-8, 9), "c1": (8, -16), "ctav": (-12, 10), "detector_only": (-8, 6)}
    fig, ax = plt.subplots(figsize=(WIDTH * 0.85, 3.3))
    for key, (name, color, marker) in METHODS.items():
        v, t = runs["val"][key], runs["test"][key]
        ax.annotate("", xy=(t["fpr"], t["recall"]), xytext=(v["fpr"], v["recall"]),
                    arrowprops={"arrowstyle": "-|>", "color": color, "lw": 0.8, "alpha": 0.6, "shrinkB": 4})
        ax.scatter(v["fpr"], v["recall"], s=30, marker=marker, facecolors="white", edgecolors=color, linewidths=1.3,
                   zorder=3)
        ax.errorbar(t["fpr"], t["recall"], xerr=err(t["fpr"], t["fpr_ci95"]), yerr=err(t["recall"], t["recall_ci95"]),
                    fmt=marker, color=color, ms=6, lw=0.9, zorder=4, mec="white", mew=0.8)
        dx, dy = offsets[key]
        ax.annotate(f"{name}\n{t['tp']} TP / {t['fp']:,} FP", (t["fpr"], t["recall"]), textcoords="offset points",
                    xytext=(dx, dy), ha="right" if dx < 0 else "left", fontsize=6.4, color=INK, linespacing=1.15)
    ax.set_xscale("log")
    ax.set_xlim(0.0018, 0.6)
    ax.set_ylim(0, 0.75)
    ax.set_xticks([0.005, 0.01, 0.03, 0.1, 0.3], ["0.5%", "1%", "3%", "10%", "30%"])
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.grid(axis="x", color=GRID, lw=0.6)
    fmt_axis(ax, percent=True)
    ax.set_xlabel("False-positive rate (log scale)")
    ax.set_ylabel("Recall")
    handles = [plt.Line2D([], [], marker="o", ls="", color=INK_2, label="test (filled, 95% CI)"),
               plt.Line2D([], [], marker="o", ls="", markerfacecolor="white", markeredgecolor=INK_2,
                          label="val (hollow)")]
    ax.legend(handles=handles, loc="upper left", fontsize=6.8)
    fig.tight_layout()
    save(fig, "ch5/h5.9-recall-fpr-operating-points.png")


def h5_10_forest() -> None:
    """H5.10 — Paired differences with 95% bootstrap CI on test (filled) and val (hollow)."""
    test = load("ctav_final_test_v1/ctav.json")["baselines"]["pairs"]
    test_c1ref = load("h0_test_compare_c1ref_v1/compare.json")["telemetry"]["pairs"]
    val = load("ctav_final_val_v1/ctav.json")["baselines"]["pairs"]
    rows = [
        ("C1 − BM25", test["c1 - bm25"], val.get("c1 - bm25")),
        ("LLM without RAG − BM25", test["norag - bm25"], val.get("norag - bm25")),
        ("CTAV − BM25", test["ctav - bm25"], val.get("ctav - bm25")),
        ("CTAV − C1", test_c1ref["ctav - c1"], None),
    ]
    metrics = [("d_recall", "(a) ΔRecall"), ("d_fpr", "(b) ΔFPR"), ("d_f1", "(c) ΔF1")]
    fig, axes = plt.subplots(1, 3, figsize=(WIDTH, 2.5), sharey=True)
    ys = list(range(len(rows)))[::-1]
    for ax, (key, name) in zip(axes, metrics, strict=True):
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", color=GRID, lw=0.6)
        for y, (_label, t, v) in zip(ys, rows, strict=True):
            ax.errorbar(t[key], y + 0.13, xerr=err(t[key], t[f"{key}_ci95"]), fmt="o", color=INK, ms=4.5, lw=1)
            if v is not None:
                ax.errorbar(v[key], y - 0.13, xerr=err(v[key], v[f"{key}_ci95"]), fmt="o", ms=4.5, mfc="white",
                            color=LIGHT_NEUTRAL, lw=1)
        ax.axvline(0, color=ORANGE, lw=0.9)
        fmt_axis(ax, axis="x", nd=2)
        title(ax, name)
    axes[0].set_yticks(ys, [r[0] for r in rows])
    axes[0].tick_params(axis="y", colors=INK)
    handles = [plt.Line2D([], [], marker="o", color=INK, label="test"),
               plt.Line2D([], [], marker="o", color=LIGHT_NEUTRAL, mfc="white", label="val")]
    fig.legend(handles=handles, loc="lower center", ncol=2, bbox_to_anchor=(0.6, -0.07))
    fig.tight_layout()
    save(fig, "ch5/h5.10-paired-differences-ci.png")


def h5_12_service_groups() -> None:
    """H5.12 — Recall of C1 and CTAV for services with / without a dev duration baseline (Finding 11)."""
    data = {"val": load("m8_finding11_val_v1/finding11.json")["groups"],
            "test": load("m8_finding11_test_v1/finding11.json")["groups"]}
    groups = [("with_dev_baseline", "With dev baseline"), ("without_dev_baseline", "Without dev baseline")]
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.7), sharey=True)
    w = 0.38
    for ax, split in zip(axes, ["val", "test"], strict=True):
        for j, key in enumerate(["c1", "ctav"]):
            name, color, _ = METHODS[key]
            for i, (gk, _gl) in enumerate(groups):
                g = data[split][gk]
                x = i + (j - 0.5) * w
                r = g[f"{key}_recall"]
                bars(ax, x, r, w, color, name if i == 0 else None)
                value_label(ax, x, r + 0.008, f"{g[f'{key}_tp']}/{g['fault']}")
        ax.set_xticks(range(2), [f"{gl}\n({len(data[split][gk]['services'])} services)" for gk, gl in groups])
        fmt_axis(ax, percent=True)
        title(ax, f"({'a' if split == 'val' else 'b'}) {split}")
    axes[0].set_ylabel("Recall (TP / fault windows)")
    axes[0].set_ylim(0, 0.38)
    axes[0].legend(loc="upper right", fontsize=6.8)
    fig.tight_layout()
    save(fig, "ch5/h5.12-recall-by-service-group.png")


def h5_13_budget() -> None:
    """H5.13 — F1 vs LLM call budget, val and test."""
    budgets = ["120", "250", "500", "1,000", "2,000", "4,000", "Full"]
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.8), sharey=True)
    for ax, split in zip(axes, ["val", "test"], strict=True):
        d = load(f"ctav_final_{split}_v1/ctav.json")
        curve, full = d["budget_curve"], d["baselines"]["methods"]
        for key in ["bm25", "c1", "ctav", "norag"]:
            name, color, marker = METHODS[key]
            ys = [p["f1"] for p in curve[key]] + [full[key]["f1"]]
            n = len(ys) - 1
            ax.plot(range(n), ys[:n], color=color, marker=marker, ms=4.5, label=name,
                    ls="--" if key == "norag" else "-")
            ax.plot([n - 1, n], ys[n - 1:], color=color, lw=1.0, ls=":")
            ax.plot(n, ys[n], color=color, marker=marker, ms=4.5)
        ax.axvline(0, color=INK_2, ls="--", lw=0.7)
        ax.text(0.1, 0.235, "H4 budget", fontsize=6.4, color=INK_2, va="top")
        ax.set_xticks(range(len(budgets)), budgets)
        ax.set_xlabel("LLM call budget")
        fmt_axis(ax, nd=2)
        title(ax, f"({'a' if split == 'val' else 'b'}) {split}")
    axes[0].set_ylabel("F1")
    axes[0].set_ylim(0, 0.24)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.06))
    fig.tight_layout()
    save(fig, "ch5/h5.13-f1-vs-budget.png")



# ----------------------------------------------------------------------------- run

FIGURES: dict[str, Callable[[], None]] = {
    "h2.4": h2_4_service_graph,
    "h5.4": h5_4_h1_time,
    "h5.5": h5_5_theta_curve,
    "h5.6": h5_6_rescue_tau,
    "h5.8": h5_8_detector_shift,
    "h5.9": h5_9_operating_points,
    "h5.10": h5_10_forest,
    "h5.12": h5_12_service_groups,
    "h5.13": h5_13_budget,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", choices=sorted(FIGURES), action="append", help="chỉ vẽ hình này (lặp được)")
    args = parser.parse_args()
    for code in args.only or list(FIGURES):
        print(code)
        FIGURES[code]()


if __name__ == "__main__":
    main()
