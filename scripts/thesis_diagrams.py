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


DIAGRAMS: dict[str, Callable[[], None]] = {
    "h4.1": h4_1_architecture,
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
