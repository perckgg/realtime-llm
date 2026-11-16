/**
 * Explicit hex tokens for SVG renderers (Recharts / React Flow), kept synchronized
 * with `src/index.css`.
 */

export const ink = {
  primary: "#0f172a",
  secondary: "#475569",
  muted: "#64748b",
  grid: "#e2e8f0",
  axis: "#cbd5e1",
  surface: "#ffffff",
  plane: "#f7f7f5",
} as const;

/** Fixed categorical palette — assigned by entity, never rotated. */
export const series = [
  "#2a78d6", // 1 blue
  "#eb6834", // 2 orange
  "#1baf7a", // 3 aqua
  "#eda100", // 4 yellow
  "#e87ba4", // 5 magenta
] as const;

/** Sequential blue ramp for normalized scores. */
export const sequential = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"] as const;

/** Reserved status colors — always paired with a symbol and text label. */
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
  TRUE_ALERT: "Confirmed Alert",
  FALSE_POSITIVE: "False Positive",
  UNCERTAIN: "Suppressed / Uncertain",
};

export const verdictShortLabel: Record<Verdict, string> = {
  TRUE_ALERT: "Confirmed",
  FALSE_POSITIVE: "False Pos.",
  UNCERTAIN: "Suppressed",
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
  network_delay: "Network Delay",
  cpu_contention: "CPU Contention",
  exception: "Unhandled Exception",
  return: "Return Payload Fault",
  cpu_consumed: "CPU Exhaustion",
};

export function formatFaultType(ft: string | null | undefined): string {
  if (!ft) return "Normal Traffic";
  if (ft in faultTypeLabel) return faultTypeLabel[ft as FaultType];
  return ft;
}

/**
 * Fixed colors for the five evaluated validation architectures.
 */
export const STRATEGY_ORDER: RetrievalStrategy[] = [
  "ctav",
  "hybrid_bm25_graph",
  "bm25_hybrid",
  "no_rag",
  "detector_only",
];

export const strategyColor: Record<RetrievalStrategy, string> = {
  ctav: series[2], // aqua — proposed CTAV pipeline
  hybrid_bm25_graph: series[4], // magenta — uncalibrated topology RAG
  bm25_hybrid: series[0], // blue — lexical RAG baseline
  no_rag: series[3], // yellow — LLM judge without RAG
  detector_only: series[1], // orange — unsupervised Isolation Forest
};

export const strategyLabel: Record<RetrievalStrategy, string> = {
  ctav: "CTAV (Calibrated Topology-Aware Validation)",
  hybrid_bm25_graph: "Uncalibrated Topology RAG",
  bm25_hybrid: "BM25 Lexical RAG (Baseline)",
  no_rag: "LLM Judge without RAG",
  detector_only: "Isolation Forest Detector Only",
};

export const strategyShortLabel: Record<RetrievalStrategy, string> = {
  ctav: "CTAV (Proposed)",
  hybrid_bm25_graph: "Topology RAG",
  bm25_hybrid: "BM25 Baseline",
  no_rag: "LLM (No RAG)",
  detector_only: "IForest Only",
};

export const modalityLabel: Record<"log" | "trace" | "metric", string> = {
  log: "Log",
  trace: "Trace",
  metric: "Metric",
};
