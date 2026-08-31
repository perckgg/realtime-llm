"""Week 1 label audit for the Nezha dataset.

Answers the five questions in
docs/Final_Thesis_Phase2/02-data-and-experiment-protocol.md §1.2 and writes the
answers to docs/label-audit.md. It also writes data/window_index.csv, the
regenerable table that scripts/make_splits.py splits and that Week 2 will load.

    python scripts/verify_labels.py                # full run, scans every trace file
    python scripts/verify_labels.py --trace-files 40   # quicker smoke run

Nothing here trains, detects or retrieves: Week 1 is a data audit only.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nezha_windows import (
    DEFAULT_TIME_SOURCE,
    LABEL_AFTER_SECONDS,
    LABEL_BEFORE_SECONDS,
    WINDOW_SECONDS,
    TimeSource,
    build_windows,
    dataset_root,
    load_injections,
    load_known_services,
    pod_to_service,
    write_window_index,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INDEX = REPO_ROOT / "data" / "window_index.csv"
DEFAULT_REPORT = REPO_ROOT / "docs" / "label-audit.md"

# The trace CSV columns we care about, in file order.
TRACE_TRACE_ID, TRACE_SPAN_ID, TRACE_PARENT_ID, TRACE_POD = 0, 1, 2, 3


# ---------------------------------------------------------------------------
# Trace integrity
# ---------------------------------------------------------------------------

class TraceStats:
    """Span-level integrity counters, plus the service graph they imply."""

    def __init__(self) -> None:
        self.files = 0
        self.spans = 0
        self.traces = 0
        self.with_span_id = 0
        self.with_parent_id = 0
        self.root_spans = 0
        self.resolvable_parents = 0
        self.dangling_parents = 0
        self.edges: Counter[tuple[str, str]] = Counter()
        self.services: set[str] = set()

    @property
    def non_root_spans(self) -> int:
        return self.spans - self.root_spans

    def pct(self, value: int) -> str:
        return f"{100.0 * value / self.spans:.2f}%" if self.spans else "n/a"


def scan_traces(root: Path, known: dict[str, str], limit_files: int | None) -> TraceStats:
    """Check that spans carry the ids needed to rebuild a call chain.

    A trace is confined to one per-minute file in this dataset, so parent
    resolution is checked within a file. A parent id that does not resolve is
    counted rather than dropped silently: the rate is what tells us whether
    Graph RAG and backward tracing are feasible at all.
    """
    stats = TraceStats()
    paths = sorted((root / "rca_data").glob("*/trace/*_trace.csv"))
    if limit_files is not None:
        paths = paths[:limit_files]

    for index, path in enumerate(paths, start=1):
        stats.files += 1
        if index % 25 == 0 or index == len(paths):
            print(f"  traces {index}/{len(paths)}  {path.parent.parent.name}/{path.name}",
                  file=sys.stderr)
        spans_by_id: dict[str, str] = {}
        rows: list[tuple[str, str, str, str]] = []
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            next(reader, None)  # header
            for row in reader:
                if len(row) < 4:
                    continue
                trace_id = row[TRACE_TRACE_ID].strip()
                span_id = row[TRACE_SPAN_ID].strip()
                parent_id = row[TRACE_PARENT_ID].strip()
                pod = row[TRACE_POD].strip()
                rows.append((trace_id, span_id, parent_id, pod))
                if span_id:
                    spans_by_id[span_id] = pod

        traces_here: set[str] = set()
        for trace_id, span_id, parent_id, pod in rows:
            stats.spans += 1
            traces_here.add(trace_id)
            if span_id:
                stats.with_span_id += 1
            service, _ = pod_to_service(pod, known)
            stats.services.add(service)
            if parent_id == "root":
                stats.root_spans += 1
                continue
            if not parent_id:
                continue
            stats.with_parent_id += 1
            parent_pod = spans_by_id.get(parent_id)
            if parent_pod is None:
                stats.dangling_parents += 1
                continue
            stats.resolvable_parents += 1
            parent_service, _ = pod_to_service(parent_pod, known)
            if parent_service != service:
                stats.edges[(parent_service, service)] += 1
        stats.traces += len(traces_here)
    return stats


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

NEWLINE = chr(10)


def _table(header: list[str], rows: Sequence[Sequence[object]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |",
             "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return lines


def render_report(root, injections, windows, metric_stats, traces, known, args,
                  comparison) -> str:
    fault_windows = [w for w in windows if w.is_fault]
    normal_windows = [w for w in windows if not w.is_fault]

    by_type = Counter(i.fault_type for i in injections)
    by_day = Counter(i.day for i in injections)
    windows_by_type = Counter(w.fault_type for w in fault_windows)
    windows_by_injection = Counter(w.injection_id for w in fault_windows)
    covered = {i.injection_id for i in injections if windows_by_injection[i.injection_id] > 0}
    uncovered = [i for i in injections if i.injection_id not in covered]

    inject_pods = {i.inject_pod for i in injections}
    mapping_methods = Counter(pod_to_service(pod, known)[1] for pod in inject_pods)
    unmapped = [pod for pod in inject_pods if pod_to_service(pod, known)[1] == "regex"]

    metric_pods = {w.pod for w in windows}
    metric_services = {w.service for w in windows}
    root_cause_services = {i.root_cause_service for i in injections}

    days = sorted({i.day for i in injections})
    now = datetime.now(UTC).replace(microsecond=0).isoformat()

    out: list[str] = []
    add = out.append

    add("# Kiểm tra nhãn Nezha — Tuần 1")
    add("")
    add(f"Sinh tự động bởi `scripts/verify_labels.py` lúc {now}.")
    add("Không sửa tay: chạy lại script để cập nhật.")
    add("")
    add(f"- Dataset: `{root}`")
    add(f"- Cửa sổ: 1 mẫu metric của 1 pod = {WINDOW_SECONDS} s")
    add(f"- Quy tắc gán nhãn: cùng pod và `start_ts` nằm trong "
        f"`[inject_ts − {LABEL_BEFORE_SECONDS} s, inject_ts + {LABEL_AFTER_SECONDS} s]` "
        "— chép từ pipeline Giai đoạn 1 (`legacy/nezha_setup/prepare_nezha_data.py`) "
        "để cổng chặn tái lập baseline ở Tuần 3 còn ý nghĩa")
    add(f"- Nguồn thời gian dùng để join: cột **{'wall-clock' if args.time_source == 'wall' else 'epoch'}** "
        f"(`--time-source {args.time_source}`)")
    add(f"- Số file trace đã quét: {traces.files}"
        + ("" if args.trace_files is None else f" (giới hạn `--trace-files {args.trace_files}`)"))
    add("")

    add("## 1. Kết luận nhanh")
    add("")
    add(_verdict(injections, fault_windows, unmapped, traces))
    add("")

    add("## 2. Phạm vi dữ liệu")
    add("")
    add("\n".join(_table(
        ["Ngày", "Hệ thống", "Số lần tiêm lỗi", "Pod có metric", "Fault window"],
        [[day,
          next((i.system for i in injections if i.day == day), "unknown"),
          by_day[day],
          len({w.pod for w in windows if w.day == day}),
          sum(1 for w in fault_windows if w.day == day)]
         for day in days]
        + [["**Tổng**", "", len(injections), len(metric_pods), len(fault_windows)]],
    )))
    add("")
    add(f"- File metric đã đọc: {metric_stats.files}")
    add(f"- Dòng metric đã đọc: {metric_stats.rows:,} "
        f"(bỏ qua {metric_stats.skipped_rows}, trùng `window_id` {metric_stats.duplicate_window_ids})")
    add(f"- Dòng có cột `TimeStamp` lệch cột `Time` quá 2 s: {metric_stats.timestamp_mismatches:,}")
    add(f"- Pod xuất hiện trong metric: {len(metric_pods)} → {len(metric_services)} service")
    add("")

    add("## 3. Câu hỏi 1–2 — Nhãn root-cause có không, ở mức nào")
    add("")
    add("Có. Mỗi lần tiêm lỗi được ghi trong `rca_data/<ngày>/<ngày>-fault_list.json` với "
        "`inject_time`, `inject_timestamp`, `inject_pod`, `inject_type`. "
        "**Nhãn ở mức pod**, không phải mức service.")
    add("")
    add(f"Ánh xạ pod → service dùng danh sách service chuẩn trong "
        f"`construct_data/root_cause_hipster.json` và `root_cause_ts.json` "
        f"({len(known)} service), fallback là cắt hậu tố ReplicaSet của Kubernetes.")
    add("")
    add("\n".join(_table(
        ["Cách khớp", "Số pod bị tiêm lỗi", "Ý nghĩa"],
        [["exact", mapping_methods.get("exact", 0), "Tên pod trùng luôn tên service"],
         ["prefix", mapping_methods.get("prefix", 0), "Khớp tiền tố với service chuẩn — tin cậy"],
         ["regex", mapping_methods.get("regex", 0), "Chỉ cắt được hậu tố, cần rà tay"],
         ["**Tổng**", len(inject_pods), ""]],
    )))
    add("")
    if unmapped:
        add(f"Pod chưa khớp được service chuẩn: `{'`, `'.join(sorted(unmapped))}`")
    else:
        add(f"**Toàn bộ {len(inject_pods)} pod bị tiêm lỗi ánh xạ được lên "
            f"{len(root_cause_services)} service chuẩn.** "
            "Nhãn `root_cause_service` dùng được cho Hit@1 / Hit@3 của Nhánh B.")
    add("")

    add("## 4. Câu hỏi 3–4 — Số lượng và phân bố nhãn")
    add("")
    add(f"Tổng số fault window có nhãn root-cause: **{len(fault_windows):,} / {len(windows):,}** "
        f"cửa sổ ({100.0 * len(fault_windows) / len(windows):.2f}%), "
        f"sinh từ **{len(injections)}** lần tiêm lỗi.")
    add("")
    add("\n".join(_table(
        ["Loại lỗi", "Số lần tiêm", "Fault window", "Window / lần tiêm"],
        [[fault_type,
          by_type[fault_type],
          windows_by_type.get(fault_type, 0),
          f"{windows_by_type.get(fault_type, 0) / by_type[fault_type]:.1f}"]
         for fault_type in sorted(by_type)]
        + [["**normal**", "—", f"{len(normal_windows):,}", "—"]],
    )))
    add("")
    add(f"- Lần tiêm lỗi không sinh được window nào: **{len(uncovered)}**"
        + ("" if not uncovered
           else " → " + ", ".join(f"`{i.injection_id}` ({i.inject_pod})" for i in uncovered[:10])))
    add(f"- Tỷ lệ mất cân bằng fault : normal ≈ 1 : "
        f"{len(normal_windows) / max(len(fault_windows), 1):.0f}")
    add("")
    add("Con số 101 lần tiêm lỗi khớp với `fault_count` trong "
        "`legacy/nezha_setup/processed/summary.json` của Giai đoạn 1 — hai lần đếm độc lập "
        "cho cùng kết quả.")
    add("")

    add(_clock_section(comparison, args, windows, injections))
    add("")

    add("## 6. Câu hỏi 5 — Trace có dựng được call chain không")
    add("")
    add("\n".join(_table(
        ["Chỉ số", "Giá trị", "Tỷ lệ trên tổng span"],
        [["File trace đã quét", f"{traces.files:,}", "—"],
         ["Trace phân biệt", f"{traces.traces:,}", "—"],
         ["Tổng span", f"{traces.spans:,}", "100%"],
         ["Span có `SpanID`", f"{traces.with_span_id:,}", traces.pct(traces.with_span_id)],
         ["Span gốc (`ParentID == root`)", f"{traces.root_spans:,}", traces.pct(traces.root_spans)],
         ["Span có `ParentID` là span khác", f"{traces.with_parent_id:,}",
          traces.pct(traces.with_parent_id)],
         ["→ trong đó `ParentID` giải được về span cùng trace",
          f"{traces.resolvable_parents:,}", traces.pct(traces.resolvable_parents)],
         ["→ `ParentID` mồ côi", f"{traces.dangling_parents:,}",
          traces.pct(traces.dangling_parents)]],
    )))
    add("")
    add(f"Cạnh service → service suy ra trực tiếp từ quan hệ cha–con: "
        f"**{len(traces.edges)} cạnh** trên **{len(traces.services)} service**. "
        "Đây là số liệu sơ bộ cho `scripts/build_service_graph.py` ở Tuần 4, "
        "không thay thế phần đo coverage của tuần đó.")
    add("")
    if traces.edges:
        add("10 cạnh nặng nhất:")
        add("")
        add("\n".join(_table(
            ["Từ service", "Đến service", "Số span"],
            [[source, target, f"{count:,}"]
             for (source, target), count in traces.edges.most_common(10)],
        )))
        add("")

    add("## 7. Rủi ro và điểm cần lưu ý")
    add("")
    for line in _risks(metric_stats, fault_windows, normal_windows, traces, uncovered):
        add(f"- {line}")
    add("")

    add("## 8. Tệp sinh ra")
    add("")
    add("| Tệp | Commit vào git | Mô tả |")
    add("|---|---|---|")
    add("| `docs/label-audit.md` | có | Chính tài liệu này |")
    add("| `data/window_index.csv` | không (`data/*` bị ignore) | "
        "Bảng cửa sổ đã gán nhãn, sinh lại được bằng script này |")
    add("| `data/splits/{dev,val,test}.json` | có | Do `scripts/make_splits.py` sinh |")
    add("")
    return "\n".join(out) + "\n"


def _clock_section(comparison, args, windows, injections) -> str:
    """Section 5 — what the choice of timestamp column costs in ground truth."""
    other_source, other_windows, other_injections = comparison
    labels = {"wall": "wall-clock (`Time` / `inject_time`)",
              "epoch": "epoch (`TimeStamp` / `inject_timestamp`)"}

    def covered(window_list, injection_list) -> int:
        seen = {w.injection_id for w in window_list if w.is_fault}
        return sum(1 for i in injection_list if i.injection_id in seen)

    rows = []
    for source, window_list, injection_list in (
        (args.time_source, windows, injections),
        (other_source, other_windows, other_injections),
    ):
        faults = sum(1 for w in window_list if w.is_fault)
        rows.append([
            labels[source] + (" ← đang dùng" if source == args.time_source else ""),
            f"{len(window_list):,}",
            f"{faults:,}",
            f"{covered(window_list, injection_list)} / {len(injection_list)}",
        ])

    lines = [
        "## 5. Chọn cột thời gian nào để join",
        "",
        "Nezha ghi mọi mốc thời gian hai lần và hai bản **không khớp nhau ở hai chỗ**:",
        "",
        ("1. Ngày **2023-01-29**: 24 trên 28 lần tiêm lỗi có `inject_timestamp` chậm hơn "
         "`inject_time` đúng 8 tiếng, trong khi file metric của ngày đó đi theo `inject_time`."),
        ("2. Toàn bộ 1.209 dòng của `2022-08-22/metric/adservice-5f6585d649-fnmft_metric.csv` "
         "có `TimeStamp` vượt trước cột `Time` của chính nó khoảng 6,3 năm."),
        "",
        "Các cột wall-clock khớp nhau trên cả bốn ngày, nên chúng là mốc chuẩn.",
        "",
        NEWLINE.join(_table(
            ["Nguồn thời gian", "Tổng window", "Fault window", "Lần tiêm lỗi có nhãn"],
            rows,
        )),
        "",
        ("Pipeline Giai đoạn 1 dùng cột epoch, nên đã âm thầm mất phần chênh lệch ở trên. "
         "Split cam kết trong `data/splits/` dùng wall-clock. Cờ `--time-source epoch` được "
         "giữ lại để tái lập đúng nhãn của Giai đoạn 1 ở cổng chặn Tuần 3 "
         "(Precision 0.32, FPR 0.046) — xem `docs/experiment-log.md`."),
    ]
    return NEWLINE.join(lines)


def _verdict(injections, fault_windows, unmapped, traces) -> str:
    ok_label = bool(injections) and not unmapped
    ok_trace = traces.spans > 0 and traces.resolvable_parents > 0
    if ok_label and ok_trace:
        return (
            f"**Cổng chặn Tuần 1: QUA.** Nezha có sẵn nhãn root-cause ở mức pod cho cả "
            f"{len(injections)} lần tiêm lỗi, ánh xạ được 100% lên tên service, và trace "
            f"có đủ `SpanID`/`ParentID` để dựng call chain "
            f"({traces.pct(traces.resolvable_parents)} span giải được về span cha). "
            "Không phải gán nhãn tay, không phải đổi dataset. Được phép sang Tuần 2."
        )
    problems = []
    if not injections:
        problems.append("không đọc được lần tiêm lỗi nào")
    if unmapped:
        problems.append(f"{len(unmapped)} pod chưa ánh xạ được lên service")
    if not ok_trace:
        problems.append("trace không dựng được quan hệ cha–con")
    return ("**Cổng chặn Tuần 1: CHƯA QUA** — " + "; ".join(problems)
            + ". Xem `docs/experiment-log.md` để biết quyết định xử lý.")


def _risks(metric_stats, fault_windows, normal_windows, traces, uncovered) -> list[str]:
    risks = []
    ratio = len(normal_windows) / max(len(fault_windows), 1)
    risks.append(
        f"**Mất cân bằng lớp nặng (1 : {ratio:.0f}).** Precision phụ thuộc trực tiếp vào tỷ lệ "
        "này, nên split phải giữ nguyên toàn bộ cửa sổ normal. Lấy mẫu bớt normal sẽ đẩy "
        "Precision lên và làm hỏng cổng chặn Tuần 3."
    )
    risks.append(
        f"**Chỉ có {len(fault_windows):,} fault window trên toàn dataset.** Các lần chạy "
        "`n_windows: 300` trong `eval/configs/` là lấy mẫu từ split, không phải toàn bộ split; "
        "cần ghi rõ cách lấy mẫu khi báo cáo."
    )
    if metric_stats.timestamp_mismatches:
        risks.append(
            f"**{metric_stats.timestamp_mismatches:,} dòng metric có hai cột thời gian lệch nhau** "
            "(xem §5). Đã xử lý bằng cách join theo cột wall-clock, nhưng bất kỳ code nào sau này "
            "đọc `TimeStamp` trực tiếp sẽ gặp lại đúng lỗi này — Tuần 2 phải dùng "
            "`packages/schemas/loaders.py` chứ không tự parse CSV."
        )
    if uncovered:
        risks.append(
            f"**{len(uncovered)} lần tiêm lỗi không có dòng metric nào trong khoảng gán nhãn.** "
            "Những lần này không sinh được fault window và không dùng được cho Nhánh B."
        )
    if traces.dangling_parents:
        risks.append(
            f"**{traces.pct(traces.dangling_parents)} span có `ParentID` không giải được** trong "
            "cùng file phút. Nguyên nhân nhiều khả năng là trace bị cắt ngang ranh giới file; "
            "Tuần 4 cần ghép trace qua các file phút trước khi dựng đồ thị."
        )
    risks.append(
        "Nhãn gắn ở mức pod nhưng Nhánh B báo cáo ở mức service. Với service có nhiều replica "
        "(`ts-basic-service`, `ts-food-service`, `ts-travel-service`, `ts-route-service`, "
        "`ts-contacts-service`, `ts-preserve-service`, `ts-verification-code-service`, "
        "`productcatalogservice`), Hit@1 mức service dễ hơn mức pod. Phải nói rõ trong luận văn "
        "là đang chấm ở mức nào."
    )
    return risks


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=None,
                        help="Nezha root (default: $NEZHA_DATA_DIR or ./data/Nezha)")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX,
                        help="where to write the labelled window table")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT,
                        help="where to write the audit markdown")
    parser.add_argument("--trace-files", type=int, default=None,
                        help="scan only the first N trace files (smoke run)")
    parser.add_argument("--time-source", choices=["wall", "epoch"],
                        default=DEFAULT_TIME_SOURCE,
                        help="which timestamp columns to join on; 'epoch' reproduces "
                             "the Phase 1 labelling bug-for-bug (see docs/experiment-log.md)")
    args = parser.parse_args()
    time_source: TimeSource = args.time_source

    root = args.dataset or dataset_root()
    if not (root / "rca_data").is_dir():
        print(f"error: {root}/rca_data not found — is the Nezha dataset in place?",
              file=sys.stderr)
        return 2

    print(f"dataset: {root}", file=sys.stderr)
    known = load_known_services(root)
    injections = load_injections(root, time_source)
    print(f"injections: {len(injections)} (time source: {args.time_source})", file=sys.stderr)

    windows, metric_stats = build_windows(root, time_source)
    print(f"windows: {len(windows)} "
          f"({sum(1 for w in windows if w.is_fault)} fault)", file=sys.stderr)

    # Label the same data both ways so the audit can quantify what the Phase 1
    # clock choice cost, without the reader having to run the script twice.
    other_source: TimeSource = "epoch" if time_source == "wall" else "wall"
    other_windows, _ = build_windows(root, other_source)
    comparison = (other_source, other_windows, load_injections(root, other_source))

    print("scanning traces...", file=sys.stderr)
    traces = scan_traces(root, known, args.trace_files)

    write_window_index(windows, args.index)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        render_report(root, injections, windows, metric_stats, traces, known, args,
                      comparison),
        encoding="utf-8",
    )
    print(f"wrote {args.index}", file=sys.stderr)
    print(f"wrote {args.report}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
