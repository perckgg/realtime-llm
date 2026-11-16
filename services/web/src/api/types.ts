/**
 * Bản dịch TypeScript của `packages/schemas/` (tài liệu 03 §1, §2) và của các
 * cột trong `fact_alert_evaluation` (tài liệu 03 §3.1).
 */

export type Verdict = "TRUE_ALERT" | "FALSE_POSITIVE" | "UNCERTAIN";

export type FaultType =
  | "network_delay"
  | "cpu_contention"
  | "exception"
  | "return"
  | "cpu_consumed";

export type RetrievalStrategy =
  | "ctav"
  | "hybrid_bm25_graph"
  | "bm25_hybrid"
  | "no_rag"
  | "detector_only";

export type Modality = "log" | "trace" | "metric";

/** 03 §1.3 */
export interface ContextEvent {
  event_id: string;
  modality: Modality;
  ts: string;
  service: string;
  content: string;
  score: number;
  origin?: "local" | "graph";
  graph_distance?: number | null;
  is_c3_anchor?: boolean;
  /** Bắt buộc không rỗng — là dữ liệu chấm context precision. */
  debug: Record<string, string | number | boolean>;
}

/** 03 §1.2 */
export interface AlertCandidate {
  candidate_id: string;
  window_id: string;
  service: string;
  ts: string;
  anomaly_score: number;
  source: "metric" | "rescue";
  rescue_score?: number | null;
  rescue_components?: {
    lambda_log: number;
    phi_topo: number;
    delta_time: number;
  } | null;
}

/** 03 §1.1 — chỉ phần nhãn, web không cần toàn bộ TelemetryWindow. */
export interface WindowLabel {
  is_fault: boolean;
  fault_type: FaultType | null;
  root_cause_service: string | null;
}

/**
 * 03 §1.4 JudgedAlert, dẹt lại kèm nhãn ground truth và các trường CTAV.
 */
export interface Alert {
  alert_id: string;
  candidate_id: string;
  window_id: string;
  run_id: string;
  service: string;
  pod?: string;
  ts: string;
  anomaly_score: number;
  candidate_source: "metric" | "rescue";
  rescue_score: number | null;
  rescue_components: {
    lambda_log: number;
    phi_topo: number;
    delta_time: number;
  } | null;

  retrieval_strategy: RetrievalStrategy;
  retrieval_latency_ms: number;
  context_event_count: number;
  context_tokens: number;
  retrieval_truncated: boolean;

  verdict: Verdict;
  raw_verdict?: Verdict;
  confidence: number;
  judge_backend: string;
  llm_latency_ms: number;
  cache_hit: boolean;
  downgraded_by_evidence_rule: boolean;
  downgraded_by_gating?: boolean;
  downgraded_by_anchoring?: boolean;
  routing_tier?: number;
  evidence_origin?: "local" | "graph" | "mixed" | "none";
  threshold_applied?: number | null;
  anchor_ids?: string[];

  label: WindowLabel;
}

/** `GET /alerts/{alert_id}` — thêm phần chi tiết. */
export interface AlertDetail extends Alert {
  reasoning: string;
  evidence_event_ids: string[];
  context_events: ContextEvent[];
  /** Chuỗi giá trị anomaly_score quanh cửa sổ, để vẽ biểu đồ ngữ cảnh. */
  metric_series: { ts: string; value: number }[];
  metric_name: string;
  detector_threshold: number;
}

/** 03 §2 EvidenceItem */
export interface EvidenceItem {
  event_id: string;
  modality: Modality;
  service: string;
  ts: string;
  excerpt: string;
}

/** 03 §2 SuggestedAction */
export interface SuggestedAction {
  description: string;
  priority: "high" | "medium" | "low";
}

/** 03 §2 DiagnosticReport */
export interface DiagnosticReport {
  incident_id: string;
  run_id: string;
  root_cause_service: string;
  fault_type: string;
  confidence: number;
  evidence: EvidenceItem[];
  propagation_path: string[];
  suggested_actions: SuggestedAction[];
  generated_at: string;
  llm_backend: string;
  schema_version: string;
}

/** 03 §1.5 Incident */
export interface Incident {
  incident_id: string;
  run_id: string;
  alert_ids: string[];
  services: string[];
  start_ts: string;
  end_ts: string;
  grouping_reason: {
    temporal_window_sec: number;
    graph_edges_used: number;
  };
  root_cause_service: string | null;
  ground_truth_service: string | null;
  fault_type: FaultType | null;
}

/** Một cạnh của đồ thị lan truyền, dựng từ trace (tài liệu 02 §1.3). */
export interface GraphEdge {
  source: string;
  target: string;
  call_count: number;
  avg_duration_ms?: number | null;
  error_rate?: number | null;
  on_path: boolean;
}

export interface GraphNode {
  service: string;
  role: "root_cause" | "ground_truth" | "affected" | "healthy";
  alert_count: number;
  max_anomaly_score: number;
  suppressed_count?: number;
  suppressed_alert_ids?: string[];
  confirmed_alert_ids?: string[];
  sample_span_ms?: number | null;
  baseline_p90_ms?: number | null;
  first_alert_ts?: string | null;
}

/** `GET /incidents/{incident_id}` */
export interface IncidentDetail extends Incident {
  nodes: GraphNode[];
  edges: GraphEdge[];
  report: DiagnosticReport | null;
  rejected_reason: string | null;
  alerts: Alert[];
}

/** PostgreSQL `run_registry` (03 §4). */
export interface Run {
  run_id: string;
  retrieval_strategy: RetrievalStrategy;
  split: "dev" | "val" | "test";
  seed: number;
  git_commit: string;
  started_at: string;
  finished_at: string | null;
  status: "running" | "done" | "failed";
  notes: string;
}

/** Khoảng tin cậy bootstrap 95%. */
export interface MetricWithCI {
  value: number;
  ci_low: number;
  ci_high: number;
}

/** `GET /runs/{run_id}/metrics` — khớp `eval/results/<run_id>/metrics.json`. */
export interface RunMetrics {
  run_id: string;
  retrieval_strategy: RetrievalStrategy;
  n_windows: number;
  tp: number;
  fp: number;
  fn: number;
  tn: number;
  precision: MetricWithCI;
  recall: MetricWithCI;
  f1: MetricWithCI;
  fpr: MetricWithCI;
  hit_at_1?: MetricWithCI | null;
  hit_at_3?: MetricWithCI | null;
  context_precision?: MetricWithCI | null;
  retrieval_latency_p95_ms: number;
  llm_latency_p95_ms: number;
  cache_hit_rate: number;
  json_valid_rate?: number | null;
  llm_calls?: number | null;
  estimated_cost_usd?: number | null;
}

/** Một điểm trên trục thời gian của màn hình Timeline. */
export interface TimelineBucket {
  bucket_ts: string;
  TRUE_ALERT: number;
  FALSE_POSITIVE: number;
  UNCERTAIN: number;
  ground_truth_faults: number;
}

/** Bảng ablation H3 + C5 trên `val`. */
export interface AblationRow {
  key: string;
  label: string;
  tp: number;
  fp: number;
  precision: number;
  recall: number;
  f1: number;
  f1_ci95: [number, number];
  fpr: number;
  llm_calls: number;
  estimated_cost_usd: number;
  delta_f1: number | null;
  delta_f1_ci95: [number, number] | null;
  delta_fpr: number | null;
  note: string;
}

/** Đường cong F1 theo ngân sách gọi LLM (H4). */
export interface BudgetCurvePoint {
  budget: number;
  ctav: number;
  ctav_tp: number;
  ctav_fp: number;
  bm25: number;
  bm25_tp: number;
  bm25_fp: number;
  c1: number;
  c1_tp: number;
  c1_fp: number;
  norag: number;
  norag_tp: number;
  norag_fp: number;
}

export interface H0TestMethod {
  key: string;
  label: string;
  tp: number;
  fp: number;
  fn: number;
  tn: number;
  precision: number;
  recall: number;
  f1: number;
  fpr: number;
}

export interface H0TestCriterion {
  criterion: string;
  test_value: string;
  passed: boolean;
}

export interface H0TestComparison {
  windows: number;
  fault_windows: number;
  methods: H0TestMethod[];
  criteria: H0TestCriterion[];
  delta_f1: number;
  delta_f1_ci95: [number, number];
  conclusion: string;
}

export interface DemoHighlight {
  id: string;
  step: string;
  title: string;
  subtitle: string;
  path: string;
}

export interface SnapshotMeta {
  generated_at: string;
  split: string;
  val_telemetry_windows: number;
  val_fault_windows: number;
  test_h0_telemetry_windows: number;
  test_h0_fault_windows: number;
  judge_model: string;
  ctav_val_incidents: number;
  ctav_val_fault_incidents: number;
  ctav_val_1hop_hit1: number;
  source_note: string;
}
