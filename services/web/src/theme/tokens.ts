/**
 * Token màu dùng cho SVG (Recharts / react-flow cần giá trị thật, không phải
 * biến CSS). Giữ đồng bộ thủ công với `src/index.css` — hai file, một bảng màu.
 *
 * Bảng màu này đã qua kiểm định: chạy
 *   node scripts/validate_palette.js "#2a78d6,#eb6834,#1baf7a,#eda100,#e87ba4" --mode light
 * → ALL CHECKS PASS.
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

export const verdictColor: Record<Verdict, string> = {
  TRUE_ALERT: series[0],
  FALSE_POSITIVE: series[1],
  UNCERTAIN: series[2],
};

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
 * Màu đi theo *thực thể* (5 phương pháp trong luận văn), không đi theo thứ hạng.
 */
export const STRATEGY_ORDER: RetrievalStrategy[] = [
  "ctav",
  "hybrid_bm25_graph",
  "bm25_hybrid",
  "no_rag",
  "detector_only",
];

export const strategyColor: Record<RetrievalStrategy, string> = {
  ctav: series[2], // aqua — phương pháp đề xuất
  hybrid_bm25_graph: series[4], // magenta — C1 topology chưa hiệu chỉnh
  bm25_hybrid: series[0], // blue — baseline
  no_rag: series[3], // yellow — LLM không RAG
  detector_only: series[1], // orange — IForest không LLM
};

export const strategyLabel: Record<RetrievalStrategy, string> = {
  ctav: "CTAV (C1 + θ 0,80 + C3 dev p90)",
  hybrid_bm25_graph: "C1 Topology (chưa hiệu chỉnh)",
  bm25_hybrid: "BM25 hybrid (baseline)",
  no_rag: "LLM không RAG",
  detector_only: "Detector-only (IForest)",
};

export const strategyShortLabel: Record<RetrievalStrategy, string> = {
  ctav: "CTAV",
  hybrid_bm25_graph: "C1 topo",
  bm25_hybrid: "BM25 (base)",
  no_rag: "Không RAG",
  detector_only: "Detector",
};

export const modalityLabel: Record<"log" | "trace" | "metric", string> = {
  log: "log",
  trace: "trace",
  metric: "metric",
};
