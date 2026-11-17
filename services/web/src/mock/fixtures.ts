/**
 * Dữ liệu giả cho bản MVP.
 *
 * Vì sao có file này: pipeline chưa chạy nên ClickHouse và PostgreSQL còn rỗng.
 * Dashboard vẫn cần dựng được để chốt bố cục, bảng màu và luồng thao tác trước
 * khi Tuần 18 nối API thật. Mọi con số ở đây là *bịa*, nhưng bịa theo đúng hình
 * dạng dữ liệu thật:
 *
 *   - service lấy từ topology OnlineBoutique (hệ hipster của Nezha)
 *   - loại lỗi và tỉ lệ lấy từ `docs/label-audit.md` (network_delay 210,
 *     cpu_contention 161, exception 138, return 124, cpu_consumed 71)
 *   - baseline bm25_hybrid neo quanh Precision 0.32 / FPR 0.046 của Giai đoạn 1
 *   - split dev, seed 42, 19.316 cửa sổ
 *
 * KHÔNG dùng file này để báo cáo bất cứ con số nào trong luận văn. Mỗi màn hình
 * hiển thị một dải cảnh báo "dữ liệu giả" chính vì lý do đó.
 */

import type {
  Alert,
  AlertDetail,
  ContextEvent,
  FaultType,
  GraphEdge,
  GraphNode,
  Incident,
  IncidentDetail,
  MetricWithCI,
  RetrievalStrategy,
  Run,
  RunMetrics,
  Verdict,
} from "@/api/types";

/** PRNG mulberry32 — cùng seed cho cùng dữ liệu ở mọi lần tải trang. */
function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function pick<T>(r: () => number, xs: readonly T[]): T {
  return xs[Math.floor(r() * xs.length)] as T;
}

function round(x: number, places = 3): number {
  const f = 10 ** places;
  return Math.round(x * f) / f;
}

/** Khoảng tin cậy bootstrap giả lập: rộng dần khi giá trị gần 0.5. */
function ci(value: number, n: number, r: () => number): MetricWithCI {
  const se = Math.sqrt((value * (1 - value)) / n);
  const half = 1.96 * se * (0.85 + r() * 0.3);
  return {
    value: round(value),
    ci_low: round(Math.max(0, value - half)),
    ci_high: round(Math.min(1, value + half)),
  };
}

// --- Topology OnlineBoutique -----------------------------------------------

export const SERVICES = [
  "frontend",
  "checkoutservice",
  "cartservice",
  "productcatalogservice",
  "currencyservice",
  "paymentservice",
  "shippingservice",
  "emailservice",
  "recommendationservice",
  "adservice",
  "redis-cart",
] as const;

/** Cạnh gọi thật của OnlineBoutique — dùng chung cho mọi đồ thị lan truyền. */
const CALL_EDGES: [string, string][] = [
  ["frontend", "productcatalogservice"],
  ["frontend", "currencyservice"],
  ["frontend", "cartservice"],
  ["frontend", "recommendationservice"],
  ["frontend", "checkoutservice"],
  ["frontend", "adservice"],
  ["frontend", "shippingservice"],
  ["checkoutservice", "cartservice"],
  ["checkoutservice", "productcatalogservice"],
  ["checkoutservice", "currencyservice"],
  ["checkoutservice", "paymentservice"],
  ["checkoutservice", "shippingservice"],
  ["checkoutservice", "emailservice"],
  ["cartservice", "redis-cart"],
  ["recommendationservice", "productcatalogservice"],
];

const FAULT_TYPES: FaultType[] = [
  "network_delay",
  "cpu_contention",
  "exception",
  "return",
  "cpu_consumed",
];

/** Trọng số lấy từ docs/label-audit.md, giữ đúng tỉ lệ tương đối. */
const FAULT_WEIGHTS: Record<FaultType, number> = {
  network_delay: 210,
  cpu_contention: 161,
  exception: 138,
  return: 124,
  cpu_consumed: 71,
};

function pickFaultType(r: () => number): FaultType {
  const total = Object.values(FAULT_WEIGHTS).reduce((a, b) => a + b, 0);
  let x = r() * total;
  for (const t of FAULT_TYPES) {
    x -= FAULT_WEIGHTS[t];
    if (x <= 0) return t;
  }
  return "network_delay";
}

const DAY_START = Date.parse("2022-08-23T03:00:00Z");
const WINDOW_MS = 60_000;

function iso(ms: number): string {
  return new Date(ms).toISOString();
}

// --- Run registry -----------------------------------------------------------

/**
 * Câu chuyện các con số kể: baseline BM25 tái lập được Giai đoạn 1; temporal
 * nhỉnh hơn chút; graph khá hơn rõ ở Hit@1 vì nó biết topology; cross_modal khá
 * ở context precision nhưng chậm; hybrid tốt nhất nhưng chậm nhất. Đây là giả
 * thuyết của luận văn, không phải kết quả — chỉ để kiểm tra biểu đồ có đọc được
 * khi các thanh sát nhau hay không.
 */
const RUN_SPEC: Record<
  RetrievalStrategy,
  { precision: number; recall: number; fpr: number; hit1: number; hit3: number; ctx: number; rlat: number; llat: number }
> = {
  bm25_hybrid: { precision: 0.32, recall: 0.58, fpr: 0.046, hit1: 0.29, hit3: 0.51, ctx: 0.41, rlat: 88, llat: 1420 },
  temporal: { precision: 0.36, recall: 0.61, fpr: 0.041, hit1: 0.31, hit3: 0.55, ctx: 0.44, rlat: 62, llat: 1380 },
  cross_modal: { precision: 0.44, recall: 0.6, fpr: 0.032, hit1: 0.38, hit3: 0.63, ctx: 0.57, rlat: 210, llat: 1510 },
  graph: { precision: 0.47, recall: 0.57, fpr: 0.028, hit1: 0.49, hit3: 0.71, ctx: 0.55, rlat: 134, llat: 1460 },
  hybrid_bm25_graph: { precision: 0.51, recall: 0.63, fpr: 0.025, hit1: 0.52, hit3: 0.74, ctx: 0.61, rlat: 246, llat: 1490 },
};

const STRATEGIES = Object.keys(RUN_SPEC) as RetrievalStrategy[];

const N_WINDOWS = 300; // theo eval/configs/bm25_baseline.yaml

export const runs: Run[] = STRATEGIES.map((strategy, i) => ({
  run_id: `${strategy}_dev_v1`,
  retrieval_strategy: strategy,
  split: "dev",
  seed: 42,
  git_commit: `8022f5c${i}`,
  started_at: iso(DAY_START + i * 3600_000),
  finished_at: iso(DAY_START + i * 3600_000 + 2100_000),
  status: "done",
  notes:
    strategy === "bm25_hybrid"
      ? "Baseline port từ Giai đoạn 1, time_source=epoch để đối chiếu."
      : `Biến thể ${strategy}, cùng split và seed với baseline.`,
  alert_count: N_WINDOWS,
}));

export const runMetrics: Record<string, RunMetrics> = Object.fromEntries(
  STRATEGIES.map((strategy, i) => {
    const r = rng(1000 + i);
    const s = RUN_SPEC[strategy];
    // 300 cửa sổ, tỉ lệ lỗi ~1:135 nhưng dev sample cân hơn để đo được recall.
    const positives = 62;
    const negatives = N_WINDOWS - positives;
    const tp = Math.round(positives * s.recall);
    const fn = positives - tp;
    const fp = Math.round(negatives * s.fpr);
    const tn = negatives - fp;
    const precision = tp / (tp + fp);
    const f1 = (2 * precision * s.recall) / (precision + s.recall);
    return [
      `${strategy}_dev_v1`,
      {
        run_id: `${strategy}_dev_v1`,
        retrieval_strategy: strategy,
        n_windows: N_WINDOWS,
        tp,
        fp,
        fn,
        tn,
        precision: ci(precision, tp + fp, r),
        recall: ci(s.recall, positives, r),
        f1: ci(f1, N_WINDOWS, r),
        fpr: ci(s.fpr, negatives, r),
        hit_at_1: ci(s.hit1, positives, r),
        hit_at_3: ci(s.hit3, positives, r),
        context_precision: ci(s.ctx, positives * 6, r),
        retrieval_latency_p95_ms: Math.round(s.rlat * (1 + r() * 0.1)),
        llm_latency_p95_ms: Math.round(s.llat * (1 + r() * 0.1)),
        cache_hit_rate: round(0.34 + r() * 0.2),
        json_valid_rate: round(0.95 + r() * 0.045),
      } satisfies RunMetrics,
    ];
  }),
);

// --- Alerts -----------------------------------------------------------------

const LOG_TEMPLATES: Record<FaultType, string[]> = {
  network_delay: [
    'upstream request timeout after 2000ms: rpc error code = DeadlineExceeded',
    'grpc call to {peer} exceeded budget, retrying (attempt 2/3)',
    'connection pool exhausted: 64/64 in use, 17 waiters',
  ],
  cpu_contention: [
    'request latency p99 climbed to 1840ms (baseline 210ms)',
    'goroutine scheduler latency 340ms, runnable queue depth 58',
    'health probe took 1.2s, threshold 1.0s',
  ],
  exception: [
    'panic: runtime error: invalid memory address or nil pointer dereference',
    'unhandled exception in handler PlaceOrder: NullReferenceException',
    'HTTP 500 returned to {peer}: internal handler raised',
  ],
  return: [
    'downstream {peer} returned status 503 Service Unavailable',
    'circuit breaker opened for {peer} after 12 consecutive failures',
    'response validation failed: empty payload where object expected',
  ],
  cpu_consumed: [
    'container cpu usage 0.98 of 1.0 limit for 240s',
    'cpu throttled: 4820ms throttled in 10s period',
    'gc pause 620ms, heap 1.8GiB of 2.0GiB',
  ],
};

const REASONING: Record<Verdict, string[]> = {
  TRUE_ALERT: [
    "Điểm bất thường {score} vượt ngưỡng 0.85, và bằng chứng truy xuất cho thấy {n} sự kiện log mức ERROR cùng cửa sổ trên chính {service}. Trace đi kèm có {span} span lỗi trỏ tới cùng một thao tác. Ba tín hiệu độc lập cùng chỉ về một hướng nên tôi kết luận đây là cảnh báo đúng.",
    "Độ trễ của {service} tăng gấp {mult} lần so với đường nền trong cùng cửa sổ, kèm theo log timeout lặp lại. Sự kiện trace cho thấy lỗi bắt đầu từ {service} rồi mới lan sang phía gọi, không phải ngược lại, nên nguyên nhân nằm tại đây chứ không phải hạ nguồn.",
  ],
  FALSE_POSITIVE: [
    "Điểm bất thường {score} chỉ vừa vượt ngưỡng và toàn bộ {n} sự kiện truy xuất được đều là log mức INFO thuộc luồng khởi động bình thường. Không có span lỗi, không có tăng độ trễ. Đây nhiều khả năng là dao động tải thường ngày.",
    "Cửa sổ này trùng với đợt tăng tải của loadgenerator; metric lệch nhưng success rate giữ nguyên 100% và không có log ERROR nào. Detector bắt đúng biến động nhưng biến động đó không phải sự cố.",
  ],
  UNCERTAIN: [
    "Có tín hiệu bất thường ở metric ({score}) nhưng bằng chứng truy xuất mỏng: chỉ {n} sự kiện, không sự kiện nào nhắc tới lỗi. Không đủ cơ sở để khẳng định cũng không đủ để bác bỏ.",
    "Log cho thấy vài lần retry nhưng không có lỗi cuối cùng nào. Có thể là sự cố thoáng qua đã tự phục hồi, cũng có thể là nhiễu. Cần thêm ngữ cảnh từ service hạ nguồn để kết luận.",
  ],
};

function makeContextEvents(
  r: () => number,
  service: string,
  faultType: FaultType,
  ts: number,
  strategy: RetrievalStrategy,
  k: number,
): ContextEvent[] {
  const peers = CALL_EDGES.filter(([s, t]) => s === service || t === service).map(
    ([s, t]) => (s === service ? t : s),
  );
  const out: ContextEvent[] = [];
  for (let i = 0; i < k; i++) {
    const modality = i % 3 === 0 ? "trace" : i % 5 === 0 ? "metric" : "log";
    const peer = peers.length ? pick(r, peers) : "frontend";
    const evService = i < 2 ? service : pick(r, [service, peer]);
    const offset = Math.round((r() - 0.5) * 240) * 1000;
    const template = pick(r, LOG_TEMPLATES[faultType]).replace("{peer}", peer);
    const content =
      modality === "log"
        ? `[ERROR] ${evService}: ${template}`
        : modality === "trace"
          ? `span ${evService}.${pick(r, ["PlaceOrder", "GetCart", "Charge", "ListProducts", "GetQuote"])} duration=${Math.round(200 + r() * 1800)}ms error=${r() > 0.5}`
          : `metric ${evService}.latency_p99 = ${Math.round(200 + r() * 1600)}ms (baseline 210ms)`;

    // `debug` bắt buộc phải điền, và mỗi strategy ghi thứ đặc thù của nó (03 §1.3).
    const debug: Record<string, string | number | boolean> = ((): Record<
      string,
      string | number | boolean
    > => {
      switch (strategy) {
        case "bm25_hybrid":
          return { bm25_score: round(6.4 - i * 0.45 + r(), 2), time_distance_sec: Math.abs(offset) / 1000 };
        case "temporal":
          return { window_size_sec: 120, score_mapping: "gaussian", time_distance_sec: Math.abs(offset) / 1000 };
        case "cross_modal":
          return { channel: modality, channel_rank: (i % 3) + 1, fusion_weight: round(0.5 - i * 0.05, 2) };
        case "graph":
          return {
            graph_distance: evService === service ? 0 : 1,
            decay_applied: round(evService === service ? 1 : 0.6, 2),
            path: evService === service ? service : `${service} -> ${evService}`,
          };
        case "hybrid_bm25_graph":
          return { bm25_rank: i + 1, graph_rank: ((i * 3) % k) + 1, rrf_score: round(1 / (60 + i + 1), 5) };
      }
    })();

    out.push({
      event_id: `ev_${ts}_${i}`,
      modality,
      ts: iso(ts + offset),
      service: evService,
      content,
      score: round(0.94 - i * 0.09 + r() * 0.03),
      debug,
    });
  }
  return out.sort((a, b) => b.score - a.score);
}

interface AlertSeed {
  alert: Alert;
  faultType: FaultType;
  tsMs: number;
}

function buildAlerts(strategy: RetrievalStrategy): AlertSeed[] {
  const r = rng(7 + STRATEGIES.indexOf(strategy));
  const spec = RUN_SPEC[strategy];
  const seeds: AlertSeed[] = [];
  const count = 184;

  for (let i = 0; i < count; i++) {
    const tsMs = DAY_START + Math.floor(r() * 8 * 60) * WINDOW_MS;
    const service = pick(r, SERVICES);
    const faultType = pickFaultType(r);
    const isFault = r() < 0.34;

    // Verdict tương quan với nhãn theo đúng precision/recall của run.
    let verdict: Verdict;
    if (isFault) {
      verdict = r() < spec.recall ? "TRUE_ALERT" : r() < 0.5 ? "UNCERTAIN" : "FALSE_POSITIVE";
    } else {
      const p = r();
      verdict = p < spec.fpr * 4 ? "TRUE_ALERT" : p < 0.35 ? "UNCERTAIN" : "FALSE_POSITIVE";
    }

    const fromRescue = r() < 0.18;
    const anomaly = fromRescue ? round(0.62 + r() * 0.2) : round(0.85 + r() * 0.14);
    const k = 6;

    seeds.push({
      faultType,
      tsMs,
      alert: {
        alert_id: `al_${strategy}_${String(i).padStart(3, "0")}`,
        candidate_id: `cand_${String(i).padStart(3, "0")}`,
        window_id: `w_${(tsMs / 1000).toString(16)}_${i % 97}`,
        run_id: `${strategy}_dev_v1`,
        service,
        ts: iso(tsMs),
        anomaly_score: anomaly,
        candidate_source: fromRescue ? "rescue" : "metric",
        rescue_score: fromRescue ? round(0.71 + r() * 0.2) : null,
        rescue_components: fromRescue
          ? {
              lambda_log: round(r() * 0.9),
              phi_topo: round(r() * 0.8),
              delta_time: round(r() * 0.7),
            }
          : null,
        retrieval_strategy: strategy,
        retrieval_latency_ms: round(spec.rlat * (0.6 + r() * 0.9), 1),
        context_event_count: k,
        context_tokens: Math.round(1800 + r() * 1900),
        retrieval_truncated: r() < 0.08,
        verdict,
        confidence: round(verdict === "UNCERTAIN" ? 0.35 + r() * 0.25 : 0.62 + r() * 0.35),
        judge_backend: r() < 0.82 ? "llama3.2:3b" : "gemini-flash-lite",
        llm_latency_ms: round(spec.llat * (0.5 + r()), 1),
        cache_hit: r() < 0.38,
        downgraded_by_evidence_rule: verdict === "UNCERTAIN" && r() < 0.3,
        raw_verdict: verdict,
        routing_tier: strategy === "bm25_hybrid" ? 1 : 2,
        evidence_origin: strategy === "bm25_hybrid" ? "local" : "graph",
        threshold_applied: 0.8,
        downgraded_by_gating: false,
        downgraded_by_anchoring: verdict === "UNCERTAIN" && !isFault,
        label: {
          is_fault: isFault,
          fault_type: isFault ? faultType : null,
          root_cause_service: isFault ? service : null,
        },
      },
    });
  }
  return seeds.sort((a, b) => a.tsMs - b.tsMs);
}

const alertsByRun = new Map<string, AlertSeed[]>(
  STRATEGIES.map((s) => [`${s}_dev_v1`, buildAlerts(s)]),
);

export function listAlerts(runId: string): Alert[] {
  return (alertsByRun.get(runId) ?? []).map((s) => s.alert);
}

export function getAlertDetail(alertId: string): AlertDetail | null {
  for (const seeds of alertsByRun.values()) {
    const seed = seeds.find((s) => s.alert.alert_id === alertId);
    if (!seed) continue;
    const { alert, faultType, tsMs } = seed;
    const r = rng(tsMs % 100000);
    const events = makeContextEvents(
      r,
      alert.service,
      faultType,
      tsMs,
      alert.retrieval_strategy,
      alert.context_event_count,
    );
    const nEvidence = alert.verdict === "TRUE_ALERT" ? 3 : alert.verdict === "UNCERTAIN" ? 1 : 0;

    // Chuỗi metric 24 điểm quanh cảnh báo, đỉnh rơi đúng vào cửa sổ cảnh báo.
    const metricSeries = Array.from({ length: 24 }, (_, i) => {
      const t = tsMs + (i - 16) * WINDOW_MS;
      const base = 0.18 + r() * 0.08;
      const bump = i >= 14 && i <= 19 ? (alert.anomaly_score - 0.4) * (1 - Math.abs(i - 16) / 5) : 0;
      return { ts: iso(t), value: round(Math.max(0.02, base + bump)) };
    });

    return {
      ...alert,
      reasoning: pick(r, REASONING[alert.verdict])
        .replace("{score}", alert.anomaly_score.toFixed(2))
        .replace("{n}", String(alert.context_event_count))
        .replace("{service}", alert.service)
        .replace("{span}", String(2 + Math.floor(r() * 5)))
        .replace("{mult}", String(3 + Math.floor(r() * 6))),
      evidence_event_ids: events.slice(0, nEvidence).map((e) => e.event_id),
      context_events: events,
      metric_series: metricSeries,
      metric_name: "anomaly_score (Isolation Forest)",
      detector_threshold: 0.85,
    };
  }
  return null;
}

// --- Incidents --------------------------------------------------------------

/** Bốn kịch bản sự cố, mỗi cái minh hoạ một hình thái lan truyền khác nhau. */
const INCIDENT_SPEC: {
  root: string;
  truth: string;
  faultType: FaultType;
  path: string[];
  correct: boolean;
  rejected: string | null;
}[] = [
  {
    root: "paymentservice",
    truth: "paymentservice",
    faultType: "network_delay",
    path: ["paymentservice", "checkoutservice", "frontend"],
    correct: true,
    rejected: null,
  },
  {
    root: "redis-cart",
    truth: "redis-cart",
    faultType: "cpu_consumed",
    path: ["redis-cart", "cartservice", "frontend"],
    correct: true,
    rejected: null,
  },
  {
    root: "checkoutservice",
    truth: "productcatalogservice",
    faultType: "exception",
    path: ["checkoutservice", "frontend"],
    correct: false,
    rejected: null,
  },
  {
    root: "currencyservice",
    truth: "currencyservice",
    faultType: "return",
    path: ["currencyservice", "checkoutservice", "frontend"],
    correct: true,
    rejected: null,
  },
  {
    root: "recommendationservice",
    truth: "recommendationservice",
    faultType: "cpu_contention",
    path: ["recommendationservice", "frontend"],
    correct: true,
    rejected: "evidence rỗng — LLM trả report không nêu event_id nào (03 §2.1)",
  },
];

const ACTIONS: Record<FaultType, string[]> = {
  network_delay: [
    "Kiểm tra độ trễ mạng giữa {root} và các service gọi nó trong cùng khoảng thời gian.",
    "Xem lại timeout và số lần retry của client gọi {root}; timeout hiện tại có thể ngắn hơn p99 thực tế.",
    "Đối chiếu với lịch thay đổi cấu hình mạng của cụm.",
  ],
  cpu_contention: [
    "So sánh mức sử dụng CPU của {root} với hạn mức đặt cho container.",
    "Kiểm tra xem có tiến trình nào khác dùng chung node với {root} hay không.",
    "Xem lại kích thước pool xử lý của {root}.",
  ],
  exception: [
    "Đọc stack trace trong log của {root} quanh mốc thời gian sự cố.",
    "Kiểm tra dữ liệu đầu vào gây lỗi ở nhánh xử lý được nêu trong bằng chứng.",
    "Đối chiếu với lần triển khai gần nhất của {root}.",
  ],
  return: [
    "Kiểm tra mã lỗi mà {root} trả về cho phía gọi.",
    "Xem trạng thái phụ thuộc hạ nguồn của {root}.",
    "Xác nhận cấu hình circuit breaker có đang mở nhầm không.",
  ],
  cpu_consumed: [
    "Kiểm tra mức tiêu thụ CPU và bộ nhớ của {root} so với hạn mức.",
    "Xem log GC của {root} quanh mốc sự cố.",
    "Cân nhắc nâng hạn mức tài nguyên hoặc giảm tải cho {root}.",
  ],
};

function buildIncidents(runId: string): IncidentDetail[] {
  const alerts = listAlerts(runId);
  return INCIDENT_SPEC.map((spec, i) => {
    const r = rng(500 + i);
    const startMs = DAY_START + (40 + i * 71) * WINDOW_MS;
    const endMs = startMs + (4 + Math.floor(r() * 6)) * WINDOW_MS;
    const involved = new Set(spec.path);
    const memberAlerts = alerts
      .filter((a) => involved.has(a.service))
      .slice(i * 3, i * 3 + 4 + Math.floor(r() * 3));

    const nodes: GraphNode[] = SERVICES.filter(
      (s) =>
        involved.has(s) ||
        CALL_EDGES.some(([a, b]) => (involved.has(a) && b === s) || (involved.has(b) && a === s)),
    ).map((service) => {
      const role: GraphNode["role"] =
        service === spec.root
          ? "root_cause"
          : service === spec.truth
            ? "ground_truth"
            : involved.has(service)
              ? "affected"
              : "healthy";
      return {
        service,
        role,
        alert_count: involved.has(service) ? 1 + Math.floor(r() * 5) : 0,
        max_anomaly_score: involved.has(service) ? round(0.82 + r() * 0.17) : round(0.2 + r() * 0.35),
      };
    });

    const present = new Set(nodes.map((n) => n.service));
    const pathPairs = new Set(
      spec.path.slice(0, -1).map((s, idx) => `${s}->${spec.path[idx + 1]}`),
    );
    const edges: GraphEdge[] = CALL_EDGES.filter(
      ([a, b]) => present.has(a) && present.has(b),
    ).map(([source, target]) => ({
      source,
      target,
      call_count: Math.round(120 + r() * 900),
      error_rate: round(pathPairs.has(`${target}->${source}`) ? 0.2 + r() * 0.4 : r() * 0.03),
      on_path: pathPairs.has(`${target}->${source}`),
    }));

    const incidentId = `inc_${runId}_${String(i + 1).padStart(2, "0")}`;
    const report = spec.rejected
      ? null
      : {
          incident_id: incidentId,
          run_id: runId,
          root_cause_service: spec.root,
          fault_type: spec.faultType,
          confidence: round(spec.correct ? 0.74 + r() * 0.2 : 0.51 + r() * 0.15),
          evidence: memberAlerts.slice(0, 3).map((a, j) => ({
            event_id: `ev_${Date.parse(a.ts)}_${j}`,
            modality: (j === 0 ? "log" : j === 1 ? "trace" : "metric") as "log" | "trace" | "metric",
            service: a.service,
            ts: a.ts,
            excerpt: pick(r, LOG_TEMPLATES[spec.faultType]).replace("{peer}", spec.path[1] ?? "frontend"),
          })),
          propagation_path: spec.path,
          suggested_actions: ACTIONS[spec.faultType].map((d, j) => ({
            description: d.replace("{root}", spec.root),
            priority: (j === 0 ? "high" : j === 1 ? "medium" : "low") as "high" | "medium" | "low",
          })),
          generated_at: iso(endMs + 4000),
          llm_backend: r() < 0.7 ? "llama3.2:3b" : "gemini-flash-lite",
          schema_version: "1.0",
        };

    return {
      incident_id: incidentId,
      run_id: runId,
      alert_ids: memberAlerts.map((a) => a.alert_id),
      services: spec.path,
      start_ts: iso(startMs),
      end_ts: iso(endMs),
      grouping_reason: { temporal_window_sec: 300, graph_edges_used: edges.filter((e) => e.on_path).length },
      root_cause_service: spec.rejected ? null : spec.root,
      ground_truth_service: spec.truth,
      fault_type: spec.faultType,
      nodes,
      edges,
      report,
      rejected_reason: spec.rejected,
      alerts: memberAlerts,
    };
  });
}

const incidentsByRun = new Map<string, IncidentDetail[]>();

function incidentsFor(runId: string): IncidentDetail[] {
  let v = incidentsByRun.get(runId);
  if (!v) {
    v = buildIncidents(runId);
    incidentsByRun.set(runId, v);
  }
  return v;
}

export function listIncidents(runId: string): Incident[] {
  return incidentsFor(runId).map(({ nodes: _n, edges: _e, report: _r, alerts: _a, rejected_reason: _rr, ...rest }) => rest);
}

export function getIncidentDetail(incidentId: string): IncidentDetail | null {
  for (const runId of incidentsByRun.keys()) {
    const found = incidentsFor(runId).find((i) => i.incident_id === incidentId);
    if (found) return found;
  }
  for (const run of runs) {
    const found = incidentsFor(run.run_id).find((i) => i.incident_id === incidentId);
    if (found) return found;
  }
  return null;
}
