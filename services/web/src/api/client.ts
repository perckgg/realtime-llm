/**
 * Thin data-access boundary matching the FastAPI backend contract.
 * Defaults to the static benchmark snapshot for offline demoing; switches to
 * HTTP API via `VITE_DATA_SOURCE=http`.
 */

import type {
  Alert,
  AlertDetail,
  Incident,
  IncidentDetail,
  Run,
  RunMetrics,
  Verdict,
} from "./types";
import * as fixtures from "@/mock/fixtures";

export interface DataSource {
  readonly kind: "mock" | "http";
  health(): Promise<{ status: string }>;
  listRuns(): Promise<Run[]>;
  runMetrics(runId: string): Promise<RunMetrics>;
  listAlerts(params: { runId: string; verdict?: Verdict | "ALL" }): Promise<Alert[]>;
  getAlert(alertId: string): Promise<AlertDetail>;
  listIncidents(runId: string): Promise<Incident[]>;
  getIncident(incidentId: string): Promise<IncidentDetail>;
}

const delay = <T,>(value: T, ms = 80): Promise<T> =>
  new Promise((resolve) => setTimeout(() => resolve(value), ms));

const mockSource: DataSource = {
  kind: "mock",
  health: () => delay({ status: "ok (offline-snapshot)" }, 0),
  listRuns: () => delay(fixtures.runs),
  runMetrics: async (runId) => {
    const m = fixtures.runMetrics[runId];
    if (!m) throw new Error(`Run '${runId}' not found in benchmark snapshot`);
    return delay(m);
  },
  listAlerts: async ({ runId, verdict }) => {
    const all = fixtures.listAlerts(runId);
    return delay(!verdict || verdict === "ALL" ? all : all.filter((a) => a.verdict === verdict));
  },
  getAlert: async (alertId) => {
    const a = fixtures.getAlertDetail(alertId);
    if (!a) throw new Error(`Alert '${alertId}' not found`);
    return delay(a);
  },
  listIncidents: async (runId) => delay(fixtures.listIncidents(runId)),
  getIncident: async (incidentId) => {
    const i = fixtures.getIncidentDetail(incidentId);
    if (!i) throw new Error(`Incident '${incidentId}' not found`);
    return delay(i);
  },
};

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`, { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — GET ${path}`);
  return (await res.json()) as T;
}

const httpSource: DataSource = {
  kind: "http",
  health: () => get("/health"),
  listRuns: () => get("/runs"),
  runMetrics: (runId) => get(`/runs/${encodeURIComponent(runId)}/metrics`),
  listAlerts: ({ runId, verdict }) => {
    const q = new URLSearchParams({ run_id: runId });
    if (verdict && verdict !== "ALL") q.set("verdict", verdict);
    return get(`/alerts?${q}`);
  },
  getAlert: (alertId) => get(`/alerts/${encodeURIComponent(alertId)}`),
  listIncidents: (runId) => get(`/incidents?run_id=${encodeURIComponent(runId)}`),
  getIncident: (incidentId) => get(`/incidents/${encodeURIComponent(incidentId)}`),
};

export const api: DataSource =
  import.meta.env.VITE_DATA_SOURCE === "http" ? httpSource : mockSource;

export const USING_FIXTURES = api.kind === "mock";
