"""Vẽ các sơ đồ khối của luận văn (PNG, 300 dpi, chữ tiếng Anh).

Sơ đồ vẽ bằng matplotlib để cùng phong cách và bảng màu với ``scripts/thesis_figures.py``. Nội dung lấy từ
``docs/drafts/outline-bao-cao-gd2.md`` mục 5 và ``docs/Final_Thesis_Phase2/01-architecture-design.md`` §3.

    py scripts/thesis_diagrams.py              # vẽ tất cả
    py scripts/thesis_diagrams.py --only h4.1  # vẽ một hình
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "drafts" / "figures"
DPI = 300
WIDTH = 6.3

BLUE = "#2a78d6"
AQUA = "#1baf7a"
ORANGE = "#e06d1f"
VIOLET = "#6250d6"
NEUTRAL = "#52514e"
INK = "#0b0b0b"
INK_2 = "#52514e"
FRAME_FILL = "#f6f6f4"
FRAME_EDGE = "#c9c8c2"
ARROW = "#52514e"
DASH = (0, (3, 2))

plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "text.color": INK})


def box(ax: Axes, x: float, y: float, w: float, h: float, title: str, body: str = "", *, edge: str = NEUTRAL,
        dashed: bool = False) -> None:
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.0", fc="white", ec=edge,
                                lw=1.1, ls=DASH if dashed else "-", zorder=2))
    ax.text(x + w / 2, y + h - 1.5, title, ha="center", va="top", fontsize=6.6, fontweight="semibold",
            color=INK_2 if dashed else INK, zorder=3)
    if body:
        ax.text(x + w / 2, y + h - 4.0, body, ha="center", va="top", fontsize=5.7, color=INK_2,
                linespacing=1.25, zorder=3)


def frame(ax: Axes, x: float, y: float, w: float, h: float, title: str, accent: str) -> None:
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.4", fc=FRAME_FILL,
                                ec=FRAME_EDGE, lw=0.9, zorder=1))
    ax.add_patch(FancyBboxPatch((x, y + h - 0.8), w, 0.8, boxstyle="square,pad=0", fc=accent, ec="none", zorder=1.5))
    ax.text(x + 1.2, y + h - 1.8, title, ha="left", va="top", fontsize=7.2, fontweight="bold", color=INK, zorder=3)


def arrow(ax: Axes, pts: list[tuple[float, float]], *, dashed: bool = False) -> None:
    """Poly-line arrow through ``pts``; the head sits on the last point."""
    ls = DASH if dashed else "-"
    color = BLUE if dashed else ARROW
    for (x1, y1), (x2, y2) in zip(pts[:-2], pts[1:-1], strict=True):
        ax.plot([x1, x2], [y1, y2], color=color, lw=1.1, ls=ls, solid_capstyle="round", zorder=1.8)
    ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle="-|>", mutation_scale=9, lw=1.1, color=color,
                                 ls=ls, zorder=1.8, shrinkA=0, shrinkB=0))


def label(ax: Axes, x: float, y: float, text: str, *, rotation: float = 0, ha: str = "center",
          va: str = "center") -> None:
    ax.text(x, y, text, ha=ha, va=va, rotation=rotation, fontsize=5.8, color=INK_2, style="italic", zorder=3,
            linespacing=1.15, bbox={"boxstyle": "round,pad=0.12", "fc": "white", "ec": "none"})


def save(fig: Figure, rel: str) -> None:
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  {path.relative_to(REPO)}")


# ----------------------------------------------------------------------------- H4.1


def h4_1_architecture() -> None:
    """H4.1 — Overall architecture: detection → CTAV → RCA agent → platform (final configuration)."""
    fig, ax = plt.subplots(figsize=(WIDTH, 4.0))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")

    # Stage frames: (x, width, title, accent); inner boxes are inset by 1.5 on each side.
    s1, s2, s3, s4 = (1, 19), (23.5, 26), (54, 19.5), (78, 21)
    fy, fh = 9, 37
    for (x, w), t, c in [(s1, "1 · Detection", BLUE), (s2, "2 · CTAV", AQUA), (s3, "3 · RCA agent", VIOLET),
                         (s4, "4 · Platform", NEUTRAL)]:
        frame(ax, x, fy, w, fh, t, c)

    def inner(s: tuple[float, float]) -> tuple[float, float, float]:
        x, w = s
        return x + 1.5, w - 3, x + w / 2

    bh = 8.4
    r0, r1, r2 = 32.0, 21.5, 11.0  # bottoms of the three inner rows

    # 1 · Detection
    x, w, c1x = inner(s1)
    box(ax, x, r0, w, bh, "Isolation Forest", "per-service metric\nfeatures, score 0–1", edge=BLUE)
    box(ax, x, r1, w, bh, "Candidate rule", "score ≥ 0.85\n→ alert candidate", edge=BLUE)
    box(ax, x, r2, w, bh, "Rescue gate (C5)", "below-threshold\nwindows", edge=BLUE, dashed=True)
    arrow(ax, [(c1x, r0), (c1x, r1 + bh)])
    arrow(ax, [(c1x, r1), (c1x, r2 + bh)], dashed=True)

    # 2 · CTAV
    x, w, c2x = inner(s2)
    box(ax, x, r0, w, bh, "Evidence retrieval (C1)", "BM25 + 2-hop topology\nFusion Score, top-6", edge=AQUA)
    box(ax, x, r1, w, bh, "LLM judge", "gemini-2.5-flash\nJSON verdict, cached", edge=AQUA)
    box(ax, x, r2, w, bh, "Decision policy", "confidence θ = 0.80\n+ evidence anchoring (C3)", edge=AQUA)
    for a, b in [(r0, r1), (r1, r2)]:
        arrow(ax, [(c2x, a), (c2x, b + bh)])

    # 3 · RCA agent
    x, w, c3x = inner(s3)
    box(ax, x, r0, w, bh, "Alert grouping", "time + topology\nT_group = 180 s", edge=VIOLET)
    box(ax, x, r1, w, bh, "Propagation", "backward 1 hop,\nrank root service", edge=VIOLET)
    box(ax, x, r2, w, bh, "Diagnostic report", "1 LLM call / incident,\nvalidated JSON", edge=VIOLET)
    for a, b in [(r0, r1), (r1, r2)]:
        arrow(ax, [(c3x, a), (c3x, b + bh)])

    # 4 · Platform (flows bottom-up)
    x, w, c4x = inner(s4)
    box(ax, x, r0, w, bh, "Dashboard", "timeline · alert ·\nincident · experiments")
    box(ax, x, r1, w, bh, "Read-only API", "FastAPI")
    box(ax, x, r2, w, bh, "Storage", "ClickHouse: verdicts\nPostgreSQL: incidents")
    for a, b in [(r2, r1), (r1, r0)]:
        arrow(ax, [(c4x, a + bh), (c4x, b)])

    # Inputs (top row) and their arrows; arrows land right of each frame title.
    top = r0 + bh
    box(ax, 1, 50, 44, 8, "Nezha telemetry", "metrics · logs · traces, replayed in 60 s windows")
    box(ax, 48, 50, 30, 8, "Service dependency graph", "from traces: 56 services, 68 edges")
    arrow(ax, [(16.5, 50), (16.5, top)])
    arrow(ax, [(39, 50), (39, top)])
    label(ax, 39, 47.6, "logs, traces")
    arrow(ax, [(52, 50), (52, 47.5), (46, 47.5), (46, top)])
    arrow(ax, [(69, 50), (69, top)])

    # Stage → stage
    arrow(ax, [(s1[0] + s1[1] - 1.5, r1 + bh / 2), (21.75, r1 + bh / 2), (21.75, r0 + bh / 2),
               (s2[0] + 1.5, r0 + bh / 2)])
    label(ax, 21.75, (r1 + r0 + bh) / 2 + 0.6, "candidates", rotation=90)
    arrow(ax, [(s2[0] + s2[1] - 1.5, r2 + bh / 2), (51.75, r2 + bh / 2), (51.75, r0 + bh / 2),
               (s3[0] + 1.5, r0 + bh / 2)])
    label(ax, 51.75, (r2 + r0 + bh) / 2, "TRUE_ALERT only", rotation=90)
    arrow(ax, [(s3[0] + s3[1] - 1.5, r2 + bh / 2), (s4[0] + 1.5, r2 + bh / 2)])
    label(ax, 75.75, r2 + bh / 2 + 3.2, "incidents,\nreports")
    arrow(ax, [(c2x, r2), (c2x, 5.0), (c4x, 5.0), (c4x, r2)])
    label(ax, (c2x + c4x) / 2, 5.0, "every verdict with its evidence")

    # Legend for the dashed box
    ax.add_patch(FancyBboxPatch((1, 1.4), 4.0, 2.2, boxstyle="round,pad=0,rounding_size=0.5", fc="white",
                                ec=BLUE, lw=1.0, ls=DASH))
    ax.text(6.0, 2.5, "ablation only, not in the final pipeline", fontsize=5.8, color=INK_2, va="center")

    save(fig, "ch4/h4.1-architecture.png")


# ----------------------------------------------------------------------------- H2.7


def h2_7_confirmation_bias() -> None:
    """H2.7 — Confirmation bias of the LLM judge: same normal candidate, two contexts, two verdicts."""
    fig, ax = plt.subplots(figsize=(WIDTH, 3.3))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 52)
    ax.axis("off")

    # Left input: single normal candidate
    box(
        ax,
        1.5,
        18.5,
        22.5,
        15.0,
        "Same normal window",
        "alert candidate on s0\nanomaly score >= 0.85\n(ground truth: NORMAL)",
        edge=NEUTRAL,
    )

    # Top frame: Branch (a) — Local, distant context -> FALSE_POSITIVE
    frame(ax, 29.0, 28.0, 69.5, 22.0, "(a) Local, time-distant context -> correct suppression", AQUA)
    box(
        ax,
        31.0,
        30.5,
        26.5,
        13.0,
        "Retrieved context",
        "logs/spans from s0 only\nfar from t0 (|dt| > 5 min)\nbenign baseline activity",
        edge=BLUE,
    )
    box(
        ax,
        61.5,
        32.0,
        13.5,
        10.0,
        "LLM Judge",
        "same prompt\ntemp = 0",
        edge=NEUTRAL,
    )
    box(
        ax,
        79.0,
        30.5,
        17.5,
        13.0,
        "FALSE_POSITIVE",
        "suppressed\n(correct TN)",
        edge=AQUA,
    )
    arrow(ax, [(57.5, 37.0), (61.5, 37.0)])
    arrow(ax, [(75.0, 37.0), (79.0, 37.0)])

    # Bottom frame: Branch (b) — Near-time / neighbor context -> TRUE_ALERT (FP)
    frame(ax, 29.0, 2.0, 69.5, 22.0, "(b) Near-time or neighbor context -> confirmation bias", ORANGE)
    box(
        ax,
        31.0,
        4.5,
        26.5,
        13.0,
        "Retrieved context",
        "near-t0 spans/logs (s0 or\n1-hop neighbor); benign\n'error'/'timeout' keywords",
        edge=ORANGE,
    )
    box(
        ax,
        61.5,
        6.0,
        13.5,
        10.0,
        "LLM Judge",
        "same prompt\ntemp = 0",
        edge=NEUTRAL,
    )
    box(
        ax,
        79.0,
        4.5,
        17.5,
        13.0,
        "TRUE_ALERT",
        "confidence = 0.90\n(false positive)",
        edge=ORANGE,
    )
    arrow(ax, [(57.5, 11.0), (61.5, 11.0)])
    arrow(ax, [(75.0, 11.0), (79.0, 11.0)])

    # Split arrows from candidate to both branches
    arrow(ax, [(24.0, 28.5), (26.5, 28.5), (26.5, 37.0), (31.0, 37.0)])
    arrow(ax, [(24.0, 23.5), (26.5, 23.5), (26.5, 11.0), (31.0, 11.0)])

    save(fig, "ch2/h2.7-confirmation-bias.png")


# ----------------------------------------------------------------------------- H4.4


def h4_4_ctav_design_vs_final() -> None:
    """H4.4 — CTAV initial two-tier design vs final configuration after val ablation."""
    fig, ax = plt.subplots(figsize=(WIDTH, 4.1))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 62)
    ax.axis("off")

    # Top frame: Initial design (two-tier + C2 + C3 + C4)
    frame(ax, 1.0, 31.5, 98.0, 29.0, "(a) Initial CTAV design (C1 + C2 + C3 + C4)", ORANGE)
    box(ax, 3.0, 44.5, 13.5, 9.5, "Candidate", "from detector\n(s0, t0)", edge=NEUTRAL)
    box(ax, 20.5, 44.5, 16.5, 9.5, "Tier 1: BM25", "local logs/spans\n-> LLM judge", edge=BLUE)
    box(ax, 41.5, 44.5, 17.5, 9.5, "Router (C4)", "no_context / weak_fp\n/ uncertain?", edge=ORANGE, dashed=True)
    box(ax, 63.5, 44.5, 16.5, 9.5, "Tier 2: C1", "2-hop topology\n-> LLM judge", edge=AQUA)
    box(ax, 83.5, 34.5, 13.5, 19.5, "Policy", "C2: theta_topo\n(dropped)\n+ C3 anchor\n-> verdict", edge=AQUA)

    # Direct shortcut from C4 (confident Tier 1) to Policy
    box(ax, 41.5, 33.4, 17.5, 8.2, "Tier 1 verdict", "theta_local = 0.80\n+ C3 anchor", edge=BLUE, dashed=True)

    arrow(ax, [(16.5, 49.2), (20.5, 49.2)])
    arrow(ax, [(37.0, 49.2), (41.5, 49.2)])
    arrow(ax, [(59.0, 49.2), (63.5, 49.2)], dashed=True)
    label(ax, 61.2, 51.6, "escalate")
    arrow(ax, [(80.0, 49.2), (83.5, 49.2)])
    arrow(ax, [(50.25, 44.5), (50.25, 41.6)], dashed=True)
    label(ax, 53.6, 43.1, "sure")
    arrow(ax, [(59.0, 37.5), (83.5, 37.5)], dashed=True)

    # Bottom frame: Final configuration (C1 + theta=0.80 + C3)
    frame(ax, 1.0, 6.5, 98.0, 21.5, "(b) Final CTAV configuration (C1 + theta = 0.80 + C3; C2 & C4 dropped)", AQUA)
    box(ax, 3.0, 9.5, 14.5, 11.5, "Candidate", "every candidate\nfrom detector", edge=NEUTRAL)
    box(ax, 22.0, 9.5, 20.5, 11.5, "C1 Retrieval", "BM25 + 2-hop topology\nFusion Score, top-6", edge=AQUA)
    box(ax, 47.0, 9.5, 19.5, 11.5, "LLM Judge", "gemini-2.5-flash\ntemp = 0, cached", edge=AQUA)
    box(ax, 71.0, 9.5, 26.0, 11.5, "Policy (theta + C3)", "theta_local = 0.80\n+ s0 abnormal anchor\n(dev p90 / ERROR-WARN)", edge=AQUA)

    arrow(ax, [(17.5, 15.25), (22.0, 15.25)])
    arrow(ax, [(42.5, 15.25), (47.0, 15.25)])
    arrow(ax, [(66.5, 15.25), (71.0, 15.25)])

    # Legend at bottom
    ax.add_patch(FancyBboxPatch((1.5, 1.4), 4.2, 2.3, boxstyle="round,pad=0,rounding_size=0.5", fc="white",
                                ec=ORANGE, lw=1.0, ls=DASH))
    ax.text(6.8, 2.55, "dropped after val ablation (C2, C4); retained in code for H3 ablation",
            fontsize=5.8, color=INK_2, va="center")

    save(fig, "ch4/h4.4-ctav-design-vs-final.png")


# ----------------------------------------------------------------------------- H4.5


def h4_5_c1_2hop_fusion() -> None:
    """H4.5 — C1 topology-aware retrieval: 2-hop expansion + Fusion Score ranking."""
    fig, ax = plt.subplots(figsize=(WIDTH, 3.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 56)
    ax.axis("off")

    # Left: Alert + 2-hop graph mini-diagram
    frame(ax, 1.0, 4.0, 31.0, 48.0, "1 · 2-hop graph (d <= 2)", BLUE)
    box(ax, 7.5, 34.5, 18.0, 9.5, "s0 (d = 0)", "alerted service\n60 s window (t0)", edge=ORANGE)
    box(ax, 2.5, 19.5, 13.2, 8.5, "s1 (d = 1)", "1-hop neighbor\nGraphSim = 0.50", edge=BLUE)
    box(ax, 17.3, 19.5, 13.2, 8.5, "s2 (d = 1)", "1-hop neighbor\nGraphSim = 0.50", edge=BLUE)
    box(ax, 8.0, 6.5, 17.0, 8.0, "s3 (d = 2)", "2-hop neighbor\nGraphSim = 0.33", edge=NEUTRAL)

    arrow(ax, [(13.0, 34.5), (9.1, 28.0)])
    arrow(ax, [(20.0, 34.5), (23.9, 28.0)])
    arrow(ax, [(9.1, 19.5), (14.5, 14.5)])
    arrow(ax, [(23.9, 19.5), (18.5, 14.5)])

    # Middle: Dual candidate pool
    frame(ax, 35.5, 4.0, 29.0, 48.0, "2 · Pool (+/- 8 min)", AQUA)
    box(ax, 37.5, 31.5, 25.0, 12.5, "BM25 lexical pool", "top bm25_k = 60 docs\nover reachable services\n(no fault-type tags)", edge=BLUE)
    box(ax, 37.5, 16.0, 25.0, 12.5, "Graph expansion", "up to 20 events / service\nclosest in time to t0\n(logs & trace spans)", edge=AQUA)
    box(ax, 37.5, 6.0, 25.0, 7.5, "Deduplicated union", "origin: local (d=0) | graph", edge=NEUTRAL)

    arrow(ax, [(32.0, 37.5), (37.5, 37.5)])
    arrow(ax, [(32.0, 22.0), (37.5, 22.0)])
    arrow(ax, [(50.0, 31.5), (50.0, 28.5)])
    arrow(ax, [(50.0, 16.0), (50.0, 13.5)])

    # Right: Fusion Score & top-6 selection
    frame(ax, 68.0, 4.0, 31.0, 48.0, "3 · Fusion Score & selection", VIOLET)
    box(ax, 70.0, 31.5, 27.0, 12.5, "Three normalized terms", "0.35 * BM25_norm\n+ 0.25 * exp(-|t-t0|/300s)\n+ 0.40 * 1 / (1 + d_G)", edge=VIOLET)
    box(ax, 70.0, 18.0, 27.0, 10.5, "Rank & budget filter", "top-k = 6 events\n<= 4,000 tokens\n(k_graph = 0 in final)", edge=AQUA)
    box(ax, 70.0, 6.0, 27.0, 8.5, "RetrievalResult", "to LLM judge prompt\n+ retrieval.jsonl trace", edge=NEUTRAL)

    arrow(ax, [(62.5, 9.7), (66.2, 9.7), (66.2, 37.5), (70.0, 37.5)])
    arrow(ax, [(83.5, 31.5), (83.5, 28.5)])
    arrow(ax, [(83.5, 18.0), (83.5, 14.5)])

    save(fig, "ch4/h4.5-c1-2hop-fusion.png")


# ----------------------------------------------------------------------------- H4.6


def h4_6_decision_policy() -> None:
    """H4.6 — CTAV decision policy flow (pure function on cached judge verdicts)."""
    fig, ax = plt.subplots(figsize=(WIDTH, 3.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 56)
    ax.axis("off")

    # Main vertical/horizontal gate chain
    box(ax, 1.5, 37.0, 16.5, 12.5, "Raw verdict", "from cached LLM\n(verdict, conf,\ncited event IDs)", edge=NEUTRAL)
    box(ax, 22.0, 37.0, 16.5, 12.5, "1 · Label check", "raw == TRUE_ALERT\n& cited != empty?", edge=BLUE)
    box(ax, 42.5, 37.0, 16.5, 12.5, "2 · Threshold", "confidence >=\ntheta_local (0.80)?", edge=BLUE)
    box(ax, 63.0, 37.0, 16.5, 12.5, "3 · C3 Anchoring", ">= 1 abnormal s0\nevent cited?\n(ERROR/WARN or\nspan > dev p90)", edge=AQUA)
    box(ax, 83.5, 37.0, 15.0, 12.5, "TRUE_ALERT", "kept & forwarded\nto RCA agent", edge=AQUA)

    # Dropped C2 dashed note above step 2
    box(ax, 42.5, 20.5, 16.5, 10.5, "C2 Gating", "dropped after val\n(tier 2: theta_topo)", edge=ORANGE, dashed=True)

    # Downgraded / pass-through outputs at bottom
    box(ax, 22.0, 5.0, 16.5, 10.5, "Pass / Downgrade", "FP/UNC unchanged;\nno cite -> UNCERTAIN", edge=NEUTRAL)
    box(ax, 42.5, 5.0, 16.5, 10.5, "UNCERTAIN", "downgraded_by_\nthreshold (or gating)", edge=ORANGE)
    box(ax, 63.0, 5.0, 16.5, 10.5, "UNCERTAIN", "downgraded_by_\nanchoring (C3)\n(blocks normal FP)", edge=ORANGE)

    # Horizontal pass arrows
    arrow(ax, [(18.0, 43.25), (22.0, 43.25)])
    arrow(ax, [(38.5, 43.25), (42.5, 43.25)])
    label(ax, 40.5, 45.6, "yes")
    arrow(ax, [(59.0, 43.25), (63.0, 43.25)])
    label(ax, 61.0, 45.6, "yes")
    arrow(ax, [(79.5, 43.25), (83.5, 43.25)])
    label(ax, 81.5, 45.6, "yes")

    # Vertical fail/no arrows
    arrow(ax, [(30.25, 37.0), (30.25, 15.5)])
    label(ax, 30.25, 27.0, "no")
    arrow(ax, [(50.75, 37.0), (50.75, 31.0)], dashed=True)
    arrow(ax, [(50.75, 20.5), (50.75, 15.5)])
    label(ax, 54.0, 18.0, "no")
    arrow(ax, [(71.25, 37.0), (71.25, 15.5)])
    label(ax, 71.25, 27.0, "no")

    # Bottom note
    ax.text(1.5, 1.4, "Pure function over cached verdicts: threshold sweeps & H3 ablations cost 0 LLM API calls.",
            fontsize=5.8, color=INK_2, style="italic")

    save(fig, "ch4/h4.6-decision-policy.png")


# ----------------------------------------------------------------------------- H4.10


def h4_10_rca_agent() -> None:
    """H4.10 — RCA Agent 3-stage pipeline: grouping -> 1-hop propagation -> validated JSON report."""
    fig, ax = plt.subplots(figsize=(WIDTH, 3.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 56)
    ax.axis("off")

    # Stage 1: Grouping
    frame(ax, 1.0, 13.0, 29.0, 39.0, "1 · Alert grouping", BLUE)
    box(ax, 3.0, 33.5, 25.0, 11.5, "Temporal clustering", "sort TRUE_ALERT by ts\nsplit when gap > 180 s\n(T_group = 180 s)", edge=BLUE)
    box(ax, 3.0, 16.0, 25.0, 12.5, "Topology components", "induced undirected subgraph\nconnected components\n-> Incident (inc-...)", edge=BLUE)
    arrow(ax, [(15.5, 33.5), (15.5, 28.5)])

    # Stage 2: Propagation
    frame(ax, 33.5, 13.0, 30.0, 39.0, "2 · Root-cause ranking", VIOLET)
    box(ax, 35.5, 33.5, 26.0, 11.5, "Backward 1-hop voting", "each alerted service s votes\nfor abnormal direct callees\n(else blames itself)", edge=VIOLET)
    box(ax, 35.5, 16.0, 26.0, 12.5, "Score & path", "score(v) = votes(v) / |A|\ntie-break: max anomaly score\n-> root cause & path hint", edge=VIOLET)
    arrow(ax, [(48.5, 33.5), (48.5, 28.5)])

    # Stage 3: Summarizer + Validator
    frame(ax, 67.0, 13.0, 32.0, 39.0, "3 · Diagnostic summarizer", AQUA)
    box(ax, 69.0, 33.5, 28.0, 11.5, "LLM report writer", "1 call / incident (cached)\nfixed root_cause_service\n<= 12 evidence items", edge=AQUA)
    box(ax, 69.0, 16.0, 28.0, 12.5, "5-rule validator", "JSON schema · conf in [0,1]\nno shell commands ·\nrequire_evidence · graph", edge=AQUA)
    arrow(ax, [(83.0, 33.5), (83.0, 28.5)])

    # Stage transitions
    arrow(ax, [(28.0, 22.25), (31.8, 22.25), (31.8, 39.25), (35.5, 39.25)])
    arrow(ax, [(61.5, 22.25), (65.2, 22.25), (65.2, 39.25), (69.0, 39.25)])

    # Storage outputs at bottom
    box(ax, 35.5, 2.0, 28.0, 7.5, "PostgreSQL: incidents", "alert_ids, services, ranking", edge=NEUTRAL)
    box(ax, 67.0, 2.0, 15.0, 7.5, "Published", "diagnostic_reports", edge=AQUA)
    box(ax, 84.0, 2.0, 15.0, 7.5, "Rejected", "diagnostic_rejected", edge=ORANGE)

    arrow(ax, [(48.5, 16.0), (48.5, 9.5)])
    arrow(ax, [(76.0, 16.0), (76.0, 9.5)])
    label(ax, 76.0, 12.2, "pass")
    arrow(ax, [(91.5, 16.0), (91.5, 9.5)])
    label(ax, 91.5, 12.2, "fail")

    save(fig, "ch4/h4.10-rca-agent.png")


# ----------------------------------------------------------------------------- H5.1


def h5_1_split_protocol() -> None:
    """H5.1 — Leakage-free split protocol by injection_id with 600 s guard buffer."""
    fig, ax = plt.subplots(figsize=(WIDTH, 3.2))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 50)
    ax.axis("off")

    # Top timeline frame
    frame(ax, 1.0, 26.5, 98.0, 22.0, "1 · Group by injection_id (7 windows / injection) & drop 600 s buffer", BLUE)
    box(ax, 3.0, 30.0, 20.5, 11.5, "Fault block (7 win)", "all 7 windows stay\nin the same split", edge=ORANGE)
    box(ax, 27.5, 30.0, 19.5, 11.5, "600 s guard buffer", "597 normal windows\non same pod dropped", edge=ORANGE, dashed=True)
    box(ax, 51.0, 30.0, 21.0, 11.5, "Normal day|pod", "assigned intact by\n(day, pod), no undersamp.", edge=BLUE)
    box(ax, 76.0, 30.0, 21.0, 11.5, "Primary subset", "telemetry windows only\n(all faults + ~25% norm.)", edge=AQUA)

    arrow(ax, [(23.5, 35.75), (27.5, 35.75)])
    arrow(ax, [(47.0, 35.75), (51.0, 35.75)])
    arrow(ax, [(72.0, 35.75), (76.0, 35.75)])

    # Bottom three split boxes
    frame(ax, 1.0, 2.0, 98.0, 21.5, "2 · Frozen splits (seed = 42, committed before any experiment)", NEUTRAL)
    box(ax, 3.0, 4.5, 29.0, 12.5, "dev (fit & debug)", "19,316 win · 21 inj · 149 fault\ntelemetry: 5,030 (25.5% norm.)\nfit IForest + C3 dev p90", edge=BLUE)
    box(ax, 35.5, 4.5, 29.0, 12.5, "val (tuning & selection)", "28,898 win · 30 inj · 209 fault\ntelemetry: 7,636 (25.9% norm.)\nH1 + select CTAV, C5, T_group", edge=AQUA)
    box(ax, 68.0, 4.5, 29.0, 12.5, "test (sealed, 1 run only)", "46,849 win · 50 inj · 346 fault\ntelemetry: 11,985 (25.0% norm.)\nG-test (H0, H2-H5) after commit", edge=ORANGE)

    arrow(ax, [(32.0, 10.75), (35.5, 10.75)])
    arrow(ax, [(64.5, 10.75), (68.0, 10.75)])

    save(fig, "ch5/h5.1-split-protocol.png")


# ----------------------------------------------------------------------------- H5.3


def h5_3_three_gates() -> None:
    """H5.3 — Three verification gates (G-port, G-paper, G-test) and sealed test workflow."""
    fig, ax = plt.subplots(figsize=(WIDTH, 3.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 56)
    ax.axis("off")

    # Top row: Three sequential gates
    frame(ax, 1.0, 29.5, 98.0, 25.0, "1 · Three verification gates across the experimental protocol", BLUE)
    box(ax, 3.0, 32.5, 28.0, 15.0, "Gate 1: G-port (pipeline)", "mock judge on paper_300\nlayer parity: 6 TP / 13 FP\n(0 diff on retrieval & gate)", edge=BLUE)
    box(ax, 36.0, 32.5, 28.0, 15.0, "Gate 2: G-paper (regression)", "paper_500, 100% cache hit\nBM25 F1 0.703 / FP 7\nTopo F1 0.476 / FP 137", edge=AQUA)
    box(ax, 69.0, 32.5, 28.0, 15.0, "Gate 3: G-test (sealed)", "pre-registered H0-H5\n(commit be2b985)\nsingle run on test split", edge=ORANGE)

    arrow(ax, [(31.0, 40.0), (36.0, 40.0)])
    arrow(ax, [(64.0, 40.0), (69.0, 40.0)])

    # Bottom row: G-test step-by-step execution
    frame(ax, 1.0, 2.0, 98.0, 24.0, "2 · G-test execution flow (0 parameter edits after pre-registration)", ORANGE)
    box(ax, 3.0, 5.5, 16.5, 13.5, "1. Freeze val", "CTAV, C5, RCA\nconfigs locked\n+ commit", edge=BLUE)
    box(ax, 22.5, 5.5, 16.5, 13.5, "2. Detector", "count 13,699\ncandidates\n(0 USD)", edge=NEUTRAL)
    box(ax, 42.0, 5.5, 17.0, 13.5, "3. Judge runs", "BM25, C1, no-RAG\n+ C5 + repeat\n(cached API)", edge=AQUA)
    box(ax, 62.0, 5.5, 16.5, 13.5, "4. Replay", "CTAV + H3 abl.\n+ RCA agent\n(0 LLM calls)", edge=VIOLET)
    box(ax, 81.5, 5.5, 15.5, 13.5, "5. Verdict", "bootstrap CI95\nMcNemar test\nH0-H5 tables", edge=ORANGE)

    arrow(ax, [(19.5, 12.25), (22.5, 12.25)])
    arrow(ax, [(39.0, 12.25), (42.0, 12.25)])
    arrow(ax, [(59.0, 12.25), (62.0, 12.25)])
    arrow(ax, [(78.5, 12.25), (81.5, 12.25)])

    save(fig, "ch5/h5.3-three-gates.png")


# ----------------------------------------------------------------------------- H5.11


def h5_11_ctav_funnel_test() -> None:
    """H5.11 — CTAV decision funnel on test telemetry windows (11,985 windows, 346 faults)."""
    fig, ax = plt.subplots(figsize=(WIDTH, 4.3))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 66)
    ax.axis("off")

    stages = [
        (56.0, 74.0, "Telemetry windows (test primary subset)", "11,985 windows  |  346 fault  |  11,639 normal", NEUTRAL, ""),
        (43.0, 64.0, "Detector candidates (Isolation Forest >= 0.85)", "3,659 candidates  |  224 fault  |  3,435 normal", BLUE, "-122 fault, -8,204 normal"),
        (30.0, 56.0, "C1 + LLM judge: raw TRUE_ALERT", "1,418 raw alerts  |  96 fault  |  1,322 normal", VIOLET, "-128 fault, -2,113 normal"),
        (17.0, 50.0, "After require_evidence & theta = 0.80 (= C1)", "1,331 alerts  |  96 TP  |  1,235 FP", ORANGE, "-0 fault, -87 normal"),
        (4.0, 44.0, "After C3 anchoring (dev p90) -> CTAV final", "78 alerts  |  14 TP  |  64 FP  (-94.8% FP, -85.4% TP)", AQUA, "-82 fault, -1,171 normal"),
    ]

    bh = 8.4
    cx = 40.0
    for idx, (y, w, title, body, color, dropped) in enumerate(stages):
        x = cx - w / 2
        box(ax, x, y, w, bh, title, body, edge=color)
        if idx > 0:
            prev_y = stages[idx - 1][0]
            arrow(ax, [(cx, prev_y), (cx, y + bh)])
            # Side note showing filtered counts
            ax.text(79.5, (prev_y + y + bh) / 2, dropped, ha="left", va="center", fontsize=5.7, color=ORANGE,
                    bbox={"boxstyle": "round,pad=0.25", "fc": "#fff6f0", "ec": ORANGE, "lw": 0.6})
            arrow(ax, [(cx + 0.8, (prev_y + y + bh) / 2), (79.0, (prev_y + y + bh) / 2)], dashed=True)

    ax.text(3.0, 0.8, "Source: ctav_final_test_v1 (dev p90). Of 82 faults dropped by C3, 67 belong to 32 services without a dev baseline.",
            fontsize=5.6, color=INK_2, style="italic")

    save(fig, "ch5/h5.11-ctav-funnel-test.png")


DIAGRAMS: dict[str, Callable[[], None]] = {
    "h2.7": h2_7_confirmation_bias,
    "h4.1": h4_1_architecture,
    "h4.4": h4_4_ctav_design_vs_final,
    "h4.5": h4_5_c1_2hop_fusion,
    "h4.6": h4_6_decision_policy,
    "h4.10": h4_10_rca_agent,
    "h5.1": h5_1_split_protocol,
    "h5.3": h5_3_three_gates,
    "h5.11": h5_11_ctav_funnel_test,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", choices=sorted(DIAGRAMS), action="append", help="chỉ vẽ hình này (lặp được)")
    args = parser.parse_args()
    for code in args.only or list(DIAGRAMS):
        print(code)
        DIAGRAMS[code]()


if __name__ == "__main__":
    main()
