/**
 * Một lớp mỏng trước dữ liệu, đúng bảy endpoint của `services/api` (tài liệu 01
 * §6.6). Toàn bộ màn hình chỉ gọi qua đây.
 *
 * Điểm quan trọng của thiết kế này: khi Tuần 18 dựng xong FastAPI, việc chuyển
 * từ fixture sang API thật là **đổi một biến môi trường**, không phải sửa màn
 * hình. Đặt `VITE_DATA_SOURCE=http` là xong.
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
  getAlert(alertId: string, runId?: string): Promise<AlertDetail>;
  listIncidents(runId: string): Promise<Incident[]>;
  getIncident(incidentId: string): Promise<IncidentDetail>;
}

/** Trễ giả để giao diện lộ ra trạng thái loading ngay từ bản MVP. */
const delay = <T,>(value: T, ms = 120): Promise<T> =>
  new Promise((resolve) => setTimeout(() => resolve(value), ms));

const mockSource: DataSource = {
  kind: "mock",
  health: () => delay({ status: "ok (fixtures)" }, 0),
  listRuns: () => delay(fixtures.runs),
  runMetrics: async (runId) => {
    const m = fixtures.runMetrics[runId];
    if (!m) throw new Error(`Run ${runId} not found`);
    return delay(m);
  },
  listAlerts: async ({ runId, verdict }) => {
    const all = fixtures.listAlerts(runId);
    return delay(!verdict || verdict === "ALL" ? all : all.filter((a) => a.verdict === verdict));
  },
  getAlert: async (alertId, _runId) => {
    void _runId;
    const a = fixtures.getAlertDetail(alertId);
    if (!a) throw new Error(`Alert ${alertId} not found`);
    return delay(a);
  },
  listIncidents: async (runId) => delay(fixtures.listIncidents(runId)),
  getIncident: async (incidentId) => {
    const i = fixtures.getIncidentDetail(incidentId);
    if (!i) throw new Error(`Incident ${incidentId} not found`);
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
  getAlert: (alertId, runId) => {
    const base = `/alerts/${encodeURIComponent(alertId)}`;
    return get(runId ? `${base}?run_id=${encodeURIComponent(runId)}` : base);
  },
  listIncidents: (runId) => get(`/incidents?run_id=${encodeURIComponent(runId)}`),
  getIncident: (incidentId) => get(`/incidents/${encodeURIComponent(incidentId)}`),
};

const useMock =
  (globalThis as { __USE_MOCK__?: boolean }).__USE_MOCK__ === true ||
  (import.meta as { env?: Record<string, string | undefined> }).env
    ?.VITE_DATA_SOURCE === "mock";

export const api: DataSource = useMock ? mockSource : httpSource;

export const USING_FIXTURES = api.kind === "mock";
