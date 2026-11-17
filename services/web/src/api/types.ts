/**
 * Bản dịch TypeScript của `packages/schemas/` (tài liệu 03 §1, §2) và của các
 * cột trong `fact_alert_evaluation` (tài liệu 03 §3.1).
 *
 * QUY TẮC: file này là *bản sao chiếu*, không phải nguồn sự thật. Pydantic model
 * trong `packages/schemas/` mới là nguồn. Khi model đổi, sửa ở đây cho khớp —
 * đừng thêm trường chỉ tồn tại ở web.
 */

export type Verdict = "TRUE_ALERT" | "FALSE_POSITIVE" | "UNCERTAIN";

export type FaultType =
  | "network_delay"
  | "cpu_contention"
  | "exception"
  | "return"
  | "cpu_consumed";

export type RetrievalStrategy =
  | "bm25_hybrid"
  | "temporal"
  | "cross_modal"
  | "graph"
  | "hybrid_bm25_graph";

export type Modality = "log" | "trace" | "metric";

/** 03 §1.3 */
export interface ContextEvent {
  event_id: string;
  modality: Modality;
  ts: string;
  service: string;
  content: string;
  score: number;
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
 * 03 §1.4 JudgedAlert, dẹt lại kèm nhãn ground truth và số liệu retrieval —
 * đúng một dòng của `fact_alert_evaluation`. Đây là thứ `GET /alerts` trả về.
 */
export interface Alert {
  alert_id: string;
  candidate_id: string;
  window_id: string;
  run_id: string;
  service: string;
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
  confidence: number;
  judge_backend: string;
  llm_latency_ms: number;
  cache_hit: boolean;
  downgraded_by_evidence_rule: boolean;
  raw_verdict: Verdict;
  routing_tier: number;
  evidence_origin: "local" | "graph" | "mixed" | "none";
  threshold_applied: number | null;
  downgraded_by_gating: boolean;
  downgraded_by_anchoring: boolean;

  label: WindowLabel;
}

/** `GET /alerts/{alert_id}` — thêm phần đắt tiền. */
export interface AlertDetail extends Alert {
  reasoning: string;
  evidence_event_ids: string[];
  context_events: ContextEvent[];
  /** Chuỗi giá trị metric của cửa sổ, để vẽ biểu đồ ngữ cảnh. */
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
  /** Chỉ có ở danh sách, để hiển thị nhanh mà không phải tải chi tiết. */
  root_cause_service: string | null;
  ground_truth_service: string | null;
  fault_type: FaultType | null;
}

/** Một cạnh của đồ thị lan truyền, dựng từ trace (tài liệu 02 §1.3). */
export interface GraphEdge {
  source: string;
  target: string;
  call_count: number;
  error_rate: number;
  /** Cạnh này nằm trên đường lan truyền mà báo cáo chẩn đoán nêu ra. */
  on_path: boolean;
}

export interface GraphNode {
  service: string;
  /** `root_cause` là service mà tác tử kết luận; `ground_truth` là nhãn Nezha. */
  role: "root_cause" | "ground_truth" | "affected" | "healthy";
  alert_count: number;
  max_anomaly_score: number;
}

/** `GET /incidents/{incident_id}` */
export interface IncidentDetail extends Incident {
  nodes: GraphNode[];
  edges: GraphEdge[];
  report: DiagnosticReport | null;
  /** Điền khi report bị từ chối — bảng `diagnostic_rejected` (03 §4). */
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
  alert_count: number;
}

/** Khoảng tin cậy bootstrap — 02 §4 yêu cầu mọi chỉ số đều có CI. */
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
  hit_at_1: MetricWithCI;
  hit_at_3: MetricWithCI;
  context_precision: MetricWithCI;
  retrieval_latency_p95_ms: number;
  llm_latency_p95_ms: number;
  cache_hit_rate: number;
  json_valid_rate: number;
}

/** Một điểm trên trục thời gian của màn hình Timeline. */
export interface TimelineBucket {
  bucket_ts: string;
  TRUE_ALERT: number;
  FALSE_POSITIVE: number;
  UNCERTAIN: number;
  /** Số cửa sổ thực sự là lỗi theo nhãn Nezha, để đối chiếu. */
  ground_truth_faults: number;
}
