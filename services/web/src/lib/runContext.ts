import { createContext, useContext } from "react";
import type { Run } from "@/api/types";

export type ThemeMode = "light" | "dark";

/**
 * Shared operational workspace state across screens.
 * Optional fields keep existing unit/smoke harnesses backward-compatible.
 */
export interface RunCtx {
  runs: Run[];
  runId: string;
  setRunId: (id: string) => void;
  runsLoading?: boolean;
  runsError?: string | null;
  groundTruthOverlay?: boolean;
  setGroundTruthOverlay?: (enabled: boolean) => void;
  theme?: ThemeMode;
  toggleTheme?: () => void;
}

export const RunContext = createContext<RunCtx | null>(null);

export function useRuns(): RunCtx {
  const ctx = useContext(RunContext);
  if (!ctx) throw new Error("useRuns must be called within RunContext");
  return ctx;
}

type RunLike = Pick<Run, "run_id" | "alert_count">;

/** Out-of-registration sensitivity runs (c3_rolling_baseline): never selected by default. */
export function isSensitivityRunId(runId: string): boolean {
  return runId.includes("sens") || runId.includes("c3rolling");
}

/**
 * Default session when URL does not specify `?run_id=`:
 * first full pipeline stream with alerts that is not a sensitivity run.
 */
export function pickDefaultRunId(runs: readonly RunLike[]): string {
  return (
    runs.find((r) => r.alert_count > 0 && !isSensitivityRunId(r.run_id))?.run_id ??
    runs.find((r) => r.alert_count > 0)?.run_id ??
    runs[0]?.run_id ??
    ""
  );
}

/**
 * Active run resolution: valid URL `?run_id=` > user-chosen session > default stream.
 */
export function resolveRunId(
  runs: readonly RunLike[],
  urlRunId: string | null,
  chosenRunId: string | null,
): string {
  const known = (id: string | null): id is string =>
    id !== null && runs.some((r) => r.run_id === id);
  if (known(urlRunId)) return urlRunId;
  if (known(chosenRunId)) return chosenRunId;
  return pickDefaultRunId(runs);
}

/** Human-readable operational session name for the top stream selector. */
export function formatSessionLabel(run: Pick<Run, "run_id" | "split" | "alert_count">): string {
  if (run.run_id === "pipeline_test_v2") return "Production Replay · Test Stream (CTAV)";
  if (run.run_id === "pipeline_val_v2") return "Staging Replay · Validation Stream (CTAV)";
  if (isSensitivityRunId(run.run_id)) return "High-Recall Sensitivity · Rolling Baseline";
  if (run.run_id.startsWith("pipeline_")) {
    return `Replay Stream · ${run.split.toUpperCase()} (${run.run_id})`;
  }
  return `Archived RCA Run · ${run.run_id} (${run.split})`;
}

export interface GuidedScenario {
  id: string;
  step: number;
  title: string;
  subtitle: string;
  to: string;
  enableGroundTruth?: boolean;
}

/** Curated operational walkthroughs backed by deterministic seed-42 cases. */
export const GUIDED_SCENARIOS: GuidedScenario[] = [
  {
    id: "overview",
    step: 1,
    title: "Operations Command & Topology",
    subtitle: "Service health map, active incidents & CTAV noise suppression",
    to: "/overview?run_id=pipeline_test_v2",
  },
  {
    id: "c3-downgrade",
    step: 2,
    title: "CTAV C3 False-Alarm Suppression",
    subtitle: "productcatalogservice — raw TRUE_ALERT downgraded to UNCERTAIN",
    to: "/alerts/cand-ad327c0b162f6198:hybrid_bm25_graph:r0?run_id=pipeline_test_v2",
    enableGroundTruth: true,
  },
  {
    id: "topo-rescue",
    step: 3,
    title: "Topology Context Rescue (network_delay)",
    subtitle: "cartservice — missed by BM25, confirmed via C1 graph context",
    to: "/alerts/cand-fa85e82f02f08574:hybrid_bm25_graph:r0?run_id=pipeline_test_v2",
    enableGroundTruth: true,
  },
  {
    id: "cascade-rca",
    step: 4,
    title: "Multi-Service Cascade Localization",
    subtitle: "ts-basic-service -> ts-preserve-service backward 1-hop RCA",
    to: "/incidents/inc-46289ea526eaa3f3?run_id=pipeline_sens_test_v1",
    enableGroundTruth: true,
  },
  {
    id: "benchmark",
    step: 5,
    title: "Offline Benchmark & H0–H5 Evaluation",
    subtitle: "Controlled comparison tables, 95% CIs & budget curves",
    to: "/compare",
  },
];
