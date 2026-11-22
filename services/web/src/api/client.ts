/**
 * Một lớp mỏng trước dữ liệu, đúng bảy endpoint của `services/api` (tài liệu 01
 * §6.6). Toàn bộ màn hình chỉ gọi qua đây.
 *
 * Ba chế độ nguồn dữ liệu (`VITE_DATA_SOURCE`):
 * - `http` (mặc định): gọi FastAPI qua proxy `/api` (ClickHouse + PostgreSQL).
 * - `static`: đọc JSON tĩnh đã export tại `${BASE_URL}static-api/` (GitHub Pages).
 * - `mock`: dùng bộ fixture tổng hợp cho smoke test SSR.
 */

import type {
  Alert,
  AlertDetail,
  FaultType,
  Incident,
  IncidentDetail,
  Run,
  RunMetrics,
  Verdict,
} from "./types";
import * as fixtures from "@/mock/fixtures";

export interface DataSource {
  readonly kind: "mock" | "http" | "static";
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

// ---------------------------------------------------------------------------
// Static GitHub Pages source (`VITE_DATA_SOURCE=static`)
// ---------------------------------------------------------------------------

interface PackedAlertTable {
  columns: string[];
  rows: unknown[][];
}

function staticBaseUrl(): string {
  const raw = import.meta.env.BASE_URL ?? "/";
  return raw.endsWith("/") ? `${raw}static-api` : `${raw}/static-api`;
}

const staticJsonCache = new Map<string, Promise<unknown>>();

function fetchStaticJson<T>(relPath: string): Promise<T> {
  const existing = staticJsonCache.get(relPath);
  if (existing) return existing as Promise<T>;
  const url = `${staticBaseUrl()}/${relPath}`;
  const req = fetch(url, { headers: { Accept: "application/json" } }).then(async (res) => {
    if (!res.ok) {
      staticJsonCache.delete(relPath);
      throw new Error(`${res.status} ${res.statusText} — GET ${url}`);
    }
    return (await res.json()) as T;
  });
  staticJsonCache.set(relPath, req);
  return req;
}

function unpackAlerts(payload: PackedAlertTable | Alert[]): Alert[] {
  if (Array.isArray(payload)) return payload;
  const cols = payload.columns;
  const idx = (name: string) => cols.indexOf(name);
  const iAlertId = idx("alert_id");
  const iCandId = idx("candidate_id");
  const iWinId = idx("window_id");
  const iRunId = idx("run_id");
  const iSvc = idx("service");
  const iTs = idx("ts");
  const iScore = idx("anomaly_score");
  const iSrc = idx("candidate_source");
  const iRescue = idx("rescue_score");
  const iStrat = idx("retrieval_strategy");
  const iRLat = idx("retrieval_latency_ms");
  const iCtxCnt = idx("context_event_count");
  const iCtxTok = idx("context_tokens");
  const iTrunc = idx("retrieval_truncated");
  const iVerdict = idx("verdict");
  const iConf = idx("confidence");
  const iBackend = idx("judge_backend");
  const iLLMLat = idx("llm_latency_ms");
  const iCache = idx("cache_hit");
  const iDownEv = idx("downgraded_by_evidence_rule");
  const iRawV = idx("raw_verdict");
  const iTier = idx("routing_tier");
  const iOrigin = idx("evidence_origin");
  const iThresh = idx("threshold_applied");
  const iDownGate = idx("downgraded_by_gating");
  const iDownAnchor = idx("downgraded_by_anchoring");
  const iIsFault = idx("label_is_fault");
  const iFaultType = idx("label_fault_type");
  const iRc = idx("label_root_cause_service");

  return payload.rows.map((r) => ({
    alert_id: String(r[iAlertId]),
    candidate_id: String(r[iCandId]),
    window_id: String(r[iWinId]),
    run_id: String(r[iRunId]),
    service: String(r[iSvc]),
    ts: String(r[iTs]),
    anomaly_score: Number(r[iScore]),
    candidate_source: r[iSrc] === "rescue" ? "rescue" : "metric",
    rescue_score: r[iRescue] == null ? null : Number(r[iRescue]),
    rescue_components: null,
    retrieval_strategy: String(r[iStrat]) as Alert["retrieval_strategy"],
    retrieval_latency_ms: Number(r[iRLat]),
    context_event_count: Number(r[iCtxCnt]),
    context_tokens: Number(r[iCtxTok]),
    retrieval_truncated: Boolean(r[iTrunc]),
    verdict: r[iVerdict] as Verdict,
    confidence: Number(r[iConf]),
    judge_backend: String(r[iBackend]),
    llm_latency_ms: Number(r[iLLMLat]),
    cache_hit: Boolean(r[iCache]),
    downgraded_by_evidence_rule: Boolean(r[iDownEv]),
    raw_verdict: r[iRawV] as Verdict,
    routing_tier: Number(r[iTier]),
    evidence_origin: r[iOrigin] as Alert["evidence_origin"],
    threshold_applied: r[iThresh] == null ? null : Number(r[iThresh]),
    downgraded_by_gating: Boolean(r[iDownGate]),
    downgraded_by_anchoring: Boolean(r[iDownAnchor]),
    label: {
      is_fault: Boolean(r[iIsFault]),
      fault_type: r[iFaultType] == null ? null : (String(r[iFaultType]) as FaultType),
      root_cause_service: r[iRc] == null ? null : String(r[iRc]),
    },
  }));
}

const unpackedAlertsCache = new Map<string, Promise<Alert[]>>();

function loadStaticAlerts(runId: string): Promise<Alert[]> {
  const existing = unpackedAlertsCache.get(runId);
  if (existing) return existing;
  const req = fetchStaticJson<PackedAlertTable | Alert[]>(
    `alerts/${encodeURIComponent(runId)}.json`,
  ).then(unpackAlerts);
  unpackedAlertsCache.set(runId, req);
  return req;
}

const staticSource: DataSource = {
  kind: "static",
  health: async () => ({ status: "ok (static snapshot)" }),
  listRuns: () => fetchStaticJson<Run[]>("runs.json"),
  runMetrics: (runId) =>
    fetchStaticJson<RunMetrics>(`metrics/${encodeURIComponent(runId)}.json`),
  listAlerts: async ({ runId, verdict }) => {
    const all = await loadStaticAlerts(runId);
    return !verdict || verdict === "ALL" ? all : all.filter((a) => a.verdict === verdict);
  },
  getAlert: async (alertId, runId) => {
    const runs = await staticSource.listRuns();
    const candidateRuns = runId
      ? [runId, ...runs.map((r) => r.run_id).filter((id) => id !== runId)]
      : runs.map((r) => r.run_id);

    for (const rid of candidateRuns) {
      const details = await fetchStaticJson<Record<string, AlertDetail>>(
        `alert_details/${encodeURIComponent(rid)}.json`,
      );
      const hit = details[alertId];
      if (hit) return hit;
    }

    // Graceful fallback for background candidates whose full trace payload was omitted
    // from the static Pages snapshot to keep CDN payloads small.
    const fallbackRunId = runId ?? runs[0]?.run_id;
    if (fallbackRunId) {
      const all = await loadStaticAlerts(fallbackRunId);
      const base = all.find((a) => a.alert_id === alertId || a.window_id === alertId);
      if (base) {
        return {
          ...base,
          reasoning:
            "Full LLM reasoning and raw context events are omitted in the static GitHub Pages snapshot for this background candidate to keep bundle size small. All TRUE_ALERT cases, all Chapter 6 demo cases, and representative C3-downgraded examples include full details; run locally with Docker (DEMO_OFFLINE=1) to inspect every candidate.",
          evidence_event_ids: [],
          context_events: [],
          metric_series: [{ ts: base.ts, value: base.anomaly_score }],
          metric_name: "anomaly_score (Isolation Forest)",
          detector_threshold: 0.85,
          search_scope: [],
          fusion_weights: null,
        };
      }
    }
    throw new Error(`Alert ${alertId} not found in static snapshot`);
  },
  listIncidents: (runId) =>
    fetchStaticJson<Incident[]>(`incidents/${encodeURIComponent(runId)}.json`),
  getIncident: async (incidentId) => {
    const idx = await fetchStaticJson<Record<string, string>>("incident_index.json");
    const runId = idx[incidentId];
    if (!runId) throw new Error(`Incident ${incidentId} not found in static snapshot`);
    const details = await fetchStaticJson<Record<string, IncidentDetail>>(
      `incident_details/${encodeURIComponent(runId)}.json`,
    );
    const hit = details[incidentId];
    if (!hit) throw new Error(`Incident ${incidentId} missing from ${runId} static details`);
    return hit;
  },
};

const envSource = import.meta.env.VITE_DATA_SOURCE as string | undefined;

const useMock =
  (globalThis as { __USE_MOCK__?: boolean }).__USE_MOCK__ === true || envSource === "mock";

export const api: DataSource = useMock
  ? mockSource
  : envSource === "static"
    ? staticSource
    : httpSource;

export const USING_FIXTURES = api.kind === "mock";
export const USING_STATIC_SNAPSHOT = api.kind === "static";
