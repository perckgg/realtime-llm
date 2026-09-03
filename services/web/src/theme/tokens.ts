/**
 * Token màu dùng cho SVG (Recharts / react-flow cần giá trị thật, không phải
 * biến CSS). Giữ đồng bộ thủ công với `src/index.css` — hai file, một bảng màu.
 *
 * Bảng màu này đã qua kiểm định: chạy
 *   node scripts/validate_palette.js "#2a78d6,#eb6834,#1baf7a,#eda100,#e87ba4" --mode light
 * → ALL CHECKS PASS, kèm cảnh báo tương phản cho aqua/yellow/magenta. Vì vậy mọi
 * biểu đồ dùng quá ba slot đều phải có nhãn trực tiếp hoặc bảng số đi kèm.
 * Đổi màu thì phải chạy lại validator trước khi commit.
 */

export const ink = {
  primary: "#0b0b0b",
  secondary: "#52514e",
  muted: "#898781",
  grid: "#e1e0d9",
  axis: "#c3c2b7",
  surface: "#fcfcfb",
  plane: "#f9f9f7",
} as const;

/** Categorical — gán theo thứ tự cố định, không xoay vòng. */
export const series = [
  "#2a78d6", // 1 blue
  "#eb6834", // 2 orange
  "#1baf7a", // 3 aqua
  "#eda100", // 4 yellow
  "#e87ba4", // 5 magenta
] as const;

/** Sequential một sắc (blue) cho độ lớn liên tục. */
export const sequential = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"] as const;

/** Status — dành riêng, luôn đi kèm icon + nhãn chữ, không bao giờ chỉ có màu. */
export const status = {
  good: "#0ca30c",
  warning: "#fab219",
  serious: "#ec835a",
  critical: "#d03b3b",
} as const;

import type { FaultType, RetrievalStrategy, Verdict } from "@/api/types";

/**
 * Verdict là *danh tính*, không phải mức độ nghiêm trọng, nên nó dùng ba slot
 * categorical đầu tiên chứ không dùng bảng status. Ba slot này qua ngưỡng
 * all-pairs ở cả hai chế độ, nên chúng an toàn kể cả trên biểu đồ phân tán.
 */
export const verdictColor: Record<Verdict, string> = {
  TRUE_ALERT: series[0],
  FALSE_POSITIVE: series[1],
  UNCERTAIN: series[2],
};

/** Ký hiệu phụ để danh tính không bao giờ chỉ nằm ở màu. */
export const verdictGlyph: Record<Verdict, string> = {
  TRUE_ALERT: "●",
  FALSE_POSITIVE: "▲",
  UNCERTAIN: "◆",
};

export const verdictLabel: Record<Verdict, string> = {
  TRUE_ALERT: "Đúng cảnh báo",
  FALSE_POSITIVE: "Dương tính giả",
  UNCERTAIN: "Không chắc",
};

/** Thứ tự cố định — dùng cho legend, cột stack, và mọi bảng. */
export const VERDICT_ORDER: Verdict[] = [
  "TRUE_ALERT",
  "FALSE_POSITIVE",
  "UNCERTAIN",
];

export const FAULT_TYPE_ORDER: FaultType[] = [
  "network_delay",
  "cpu_contention",
  "exception",
  "return",
  "cpu_consumed",
];

export const faultTypeLabel: Record<FaultType, string> = {
  network_delay: "network_delay",
  cpu_contention: "cpu_contention",
  exception: "exception",
  return: "return",
  cpu_consumed: "cpu_consumed",
};

/**
 * Màu đi theo *thực thể* (biến thể retrieval), không đi theo thứ hạng. Lọc bớt
 * biến thể trên màn hình so sánh không được sơn lại những biến thể còn lại.
 */
export const STRATEGY_ORDER: RetrievalStrategy[] = [
  "bm25_hybrid",
  "temporal",
  "cross_modal",
  "graph",
  "hybrid_bm25_graph",
];

export const strategyColor: Record<RetrievalStrategy, string> = {
  bm25_hybrid: series[0],
  temporal: series[1],
  cross_modal: series[2],
  graph: series[3],
  hybrid_bm25_graph: series[4],
};

export const strategyLabel: Record<RetrievalStrategy, string> = {
  bm25_hybrid: "BM25 hybrid (baseline)",
  temporal: "Temporal",
  cross_modal: "Cross-modal",
  graph: "Graph RAG",
  hybrid_bm25_graph: "Hybrid BM25 + Graph",
};

export const modalityLabel: Record<"log" | "trace" | "metric", string> = {
  log: "log",
  trace: "trace",
  metric: "metric",
};
