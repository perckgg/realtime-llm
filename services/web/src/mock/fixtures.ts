/**
 * Dữ liệu thực nghiệm thật trích xuất từ `eval/results/` bằng `scripts/export_web_snapshot.py`
 * (M10 Pha 1 — QĐ-038). Không có số giả lập: mọi chỉ số, cảnh báo, bằng chứng RAG,
 * ngưỡng C3 dev p90 và đồ thị service đều đến từ `ctav_final_val_v1`, `h0_val_*`,
 * `m7_rescue_val_v1`, `h0_test_*` và `data/graph/service_graph.json`.
 */

import type {
  AblationRow,
  Alert,
  AlertDetail,
  BudgetCurvePoint,
  ContextEvent,
  DemoHighlight,
  DiagnosticReport,
  GraphEdge,
  GraphNode,
  H0TestComparison,
  Incident,
  IncidentDetail,
  Run,
  RunMetrics,
  SnapshotMeta,
} from "@/api/types";
import rawSnapshot from "./snapshot.json";

interface CompactAlertDetail {
  reasoning: string;
  evidence_event_ids: string[];
  context_events: ContextEvent[];
  metric_name: string;
  detector_threshold: number;
}

interface CompactIncidentDetail extends Incident {
  nodes: GraphNode[];
  edges: GraphEdge[];
  report: DiagnosticReport | null;
  rejected_reason: string | null;
  member_alert_ids: string[];
}

interface SnapshotData {
  meta: SnapshotMeta;
  runs: Run[];
  runMetrics: Record<string, RunMetrics>;
  ablationRows: AblationRow[];
  budgetCurve: BudgetCurvePoint[];
  h0TestComparison: H0TestComparison;
  demoHighlights: DemoHighlight[];
  groundTruthBuckets: { ts_ms: number; faults: number }[];
  podSeries: Record<string, { ts: string; value: number }[]>;
  alertsByRun: Record<string, Alert[]>;
  alertDetails: Record<string, CompactAlertDetail>;
  incidentsByRun: Record<string, Incident[]>;
  incidentDetails: Record<string, CompactIncidentDetail>;
}

const snapshot = rawSnapshot as unknown as SnapshotData;

export const snapshotMeta: SnapshotMeta = snapshot.meta;
export const runs: Run[] = snapshot.runs;
export const runMetrics: Record<string, RunMetrics> = snapshot.runMetrics;
export const ablationRows: AblationRow[] = snapshot.ablationRows;
export const budgetCurve: BudgetCurvePoint[] = snapshot.budgetCurve;
export const h0TestComparison: H0TestComparison = snapshot.h0TestComparison;
export const demoHighlights: DemoHighlight[] = snapshot.demoHighlights;
export const groundTruthBuckets = snapshot.groundTruthBuckets;

const alertById = new Map<string, Alert>();
for (const arr of Object.values(snapshot.alertsByRun)) {
  for (const a of arr) {
    alertById.set(a.alert_id, a);
  }
}

function sliceSeries(pod: string | undefined, targetTs: string, radius = 12): { ts: string; value: number }[] {
  if (!pod) return [];
  const full = snapshot.podSeries[pod];
  if (!full || full.length === 0) return [];
  let idx = full.findIndex((p) => p.ts >= targetTs);
  if (idx < 0) idx = full.length - 1;
  const lo = Math.max(0, idx - radius);
  const hi = Math.min(full.length, idx + radius + 1);
  return full.slice(lo, hi);
}

export function listAlerts(runId: string): Alert[] {
  return snapshot.alertsByRun[runId] ?? [];
}

export function getAlertDetail(alertId: string): AlertDetail | null {
  const base = alertById.get(alertId);
  const detail = snapshot.alertDetails[alertId];
  if (!base || !detail) return null;
  return {
    ...base,
    ...detail,
    metric_series: sliceSeries(base.pod, base.ts),
  };
}

export function listIncidents(runId: string): Incident[] {
  return snapshot.incidentsByRun[runId] ?? [];
}

export function getIncidentDetail(incidentId: string): IncidentDetail | null {
  const raw = snapshot.incidentDetails[incidentId];
  if (!raw) return null;
  const { member_alert_ids, ...rest } = raw;
  const alerts = member_alert_ids
    .map((id) => alertById.get(id))
    .filter((a): a is Alert => Boolean(a));
  return { ...rest, alerts };
}
