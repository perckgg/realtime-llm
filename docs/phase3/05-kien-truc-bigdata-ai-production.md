# 05 — Kiến trúc Kỹ thuật Production: Phần mềm, Big Data Streaming & AI/LLM Engineering

> **Bản thiết kế kiến trúc hệ thống (cập nhật 2026-11-24).**
> Tài liệu này trình bày thiết kế kỹ thuật chuyên sâu dưới góc độ **Kiến trúc Phần mềm, Kỹ thuật Dữ liệu Lớn (Big Data Streaming)** và **Hệ thống AI/LLM Độ tin cậy cao** cho sản phẩm `alert-triage`.
> Tài liệu giải quyết bài toán cốt lõi: làm thế nào xử lý luồng sự kiện telemetry và các cơn bão cảnh báo (*alert storms*) với độ trễ mục tiêu $p_{95} < 8$ giây, chi phí LLM được kiểm soát chặt và độ an toàn vận hành cao.

---

## 1. Tổng quan Kiến trúc Hệ thống (High-Level Architecture)

> **Sơ đồ dưới đây là kiến trúc đích (v0.3, nhiều tenant).** Bản v0.1 chạy cấu hình tối giản (FastAPI + PostgreSQL, chưa có Redis/Redpanda); điều kiện để thêm từng thành phần, cách scale và đánh giá Rust nằm ở `07-cong-nghe-va-scale-production.md`.

Hệ thống áp dụng kiến trúc **Hybrid Federated + Streaming Sketch**:
- **Không sao chép kho dữ liệu thô (Zero-Copy Federated Querying):** Không hút toàn bộ log/trace thô của khách hàng về lưu lại (tránh nhân đôi chi phí băng thông và lưu trữ Big Data so với cụm Loki/Tempo/Prometheus hiện hữu của khách).
- **Chỉ hút luồng siêu dữ liệu nhẹ (Lightweight Span-Metric Stream):** Dùng một luồng tổng hợp nhẹ từ OpenTelemetry Collector / Tempo Metrics-Generator để cập nhật **bản phác thảo phân vị độ trễ trực tuyến (DDSketch qua họ hàm `quantileDD` của ClickHouse cho `C3-Online`)** và **đồ thị phụ thuộc dịch vụ động (`Dynamic Topology`)**.

```mermaid
flowchart TB
    subgraph CustomerObs["Hạ tầng Observability sẵn có của Khách hàng"]
        AM["Alertmanager / Grafana"]
        OTEL["OTel Collector / Tempo Generator"]
        LGTM["Kho Telemetry: Loki (Logs) · Tempo (Traces) · Prometheus (Metrics)"]
        CICD["K8s Rollout / ArgoCD / GitHub Webhook"]
    end

    subgraph IngestionLayer["Tầng 1: Tiếp nhận & Luồng Big Data (Ingestion & Streaming)"]
        API_ING["Ingest Gateway (FastAPI Async, HTTP 202 < 150ms)"]
        RP["Redpanda / Kafka<br/>(Topics: raw_alerts, span_sketches, change_events)"]
        DEDUP["Redis: Fingerprint Dedup, Rate Limit & Spend Counter"]
    end

    subgraph BigDataEngine["Tầng 2: Động cơ Đồ thị & Phân vị Trực tuyến (Streaming State)"]
        SKETCH["Streaming Quantile Aggregator<br/>(ClickHouse quantileDDState / quantileDDMerge)"]
        TOPO["Dynamic Topology Builder<br/>(Sliding 60m Call Graph)"]
    end

    subgraph CoreAI["Tầng 3: Lõi AI/CTAV & RCA Engine (core-v1.x)"]
        FETCH["Federated Evidence Fetcher + C1 Anomaly-Boosted Fusion"]
        GATE["Pre-Judge Deterministic Gate, Cold-Start & Severity Bypass"]
        SCRUB["PII & Secret Redaction Pipeline (p99 < 10ms)"]
        JUDGE["Multi-Provider LLM Judge + C3 Anchoring (policy.py::decide)"]
        RCA["Streaming Incident Grouping + Multi-Hop RCA + 5-Rule Validator (+ P3 Gate)"]
    end

    subgraph StorageAndDelivery["Tầng 4: Lưu trữ Đa tầng & Phân phối"]
        CH[("ClickHouse<br/>(Audit Trail, DDSketches, Cost Ledger)")]
        PG[("PostgreSQL<br/>(Incidents, Tenant Config, Human Feedback)")]
        DELIV["Delivery Router + Fail-Open Watchdog"]
        SLACK["Slack / MS Teams / PagerDuty + Web UI"]
    end

    AM -->|Webhook| API_ING
    CICD -->|Webhook| API_ING
    OTEL -->|OTLP Span Metrics| RP
    API_ING --> DEDUP
    API_ING --> RP
    RP --> SKETCH --> CH
    RP --> TOPO --> PG
    RP --> FETCH
    LGTM <-->|Read-only Query 3s timeout| FETCH
    CH --> GATE
    PG --> FETCH
    FETCH --> GATE
    GATE -->|0 bất thường & severity != critical -> P3 ($0)| DELIV
    GATE -->|Có bất thường hoặc severity == critical| SCRUB --> JUDGE --> RCA --> DELIV
    RCA --> PG
    JUDGE --> CH
    DELIV --> SLACK
    SLACK -->|Feedback 👍/👎| PG
```

---

## 2. Thiết kế Tầng Big Data & Streaming Telemetry

### 2.1 Giải bài toán Ngưỡng nền Trực tuyến (`C3-Online`) bằng `quantileDD` (DDSketch) trong ClickHouse
Trong luận văn GĐ2, `C3` dùng bảng phân vị tĩnh `data/span_baseline.parquet` tính từ tập `dev`, dẫn tới việc thiếu ngưỡng cho `32/42` service trên tập `test` (*Phát hiện 11*). Trong môi trường Production, nếu tính phân vị $p_{90}, p_{99}$ trực tuyến trên hàng triệu trace spans bằng cách lưu toàn bộ `duration_ms` rồi sắp xếp (`ORDER BY`), bộ nhớ RAM và CPU sẽ bị quá tải.

**Giải pháp Big Data Production — Cấu trúc dữ liệu xác suất `DDSketch` (hàm `quantileDD(relative_accuracy, level)` của ClickHouse, có từ v24.1):**

> Đây là **phương án B** trong `07-cong-nghe-va-scale-production.md` §4.3, chỉ dùng khi phải tự thu span thô. Phương án mặc định cho v0.1–v0.2 là exponential histogram của OTel `spanmetrics` connector (không cần hút span thô).

- **Cơ chế lưu trữ & hợp nhất (`AggregatingMergeTree`):**
  - Thay vì lưu từng giá trị `duration_ms`, mỗi cặp `(tenant_id, service, operation)` trong mỗi khung thời gian 1 phút được gom thành trạng thái DDSketch với sai số tương đối $\alpha = 0{,}01$:
    - Tài liệu ClickHouse chỉ mô tả dạng số ít `quantileDD` (mỗi lần một mức phân vị); **chưa thấy tài liệu cho dạng số nhiều `quantilesDD`**, nên thiết kế dùng một cột cho mỗi mức: `p90_state AggregateFunction(quantileDD(0.01, 0.9), Float64)`, `p99_state AggregateFunction(quantileDD(0.01, 0.99), Float64)`. Trước khi code, kiểm bằng `SELECT name FROM system.functions WHERE name ILIKE '%quantile%DD%'` trên đúng phiên bản sẽ triển khai.
    - Khi ghi (Materialized View từ luồng span): `quantileDDState(0.01, 0.9)(duration_ms)`.
    - Khi đọc gộp trên cửa sổ thời gian bất kỳ: `quantileDDMerge(0.01, 0.9)(p90_state)`.
- **Ưu điểm kỹ thuật:**
  1. **Dung lượng bộ nhớ nhỏ và có chặn trên:** Mỗi trạng thái sketch 1 phút của một thao tác chỉ giữ các thùng logarit (logarithmic buckets), không phụ thuộc tuyến tính vào số lượng request/phút.
  2. **Khả năng gộp tuyến tính (*Mergeable*):** Muốn lấy ngưỡng nền $p_{90}$ của 60 phút gần nhất, ClickHouse chỉ cần chạy `quantileDDMerge` trên 60 dòng trạng thái 1 phút trong vài mili-giây.
  3. **Đồng bộ tham chiếu mùa vụ (*Diurnal Seasonality* — khớp `04-prd` FR-08):** Ngưỡng nền hiệu lực $B_{p90}(s, op, t_0)$ được tính từ cửa sổ trượt 60 phút vừa qua (trừ 5 phút sát thời điểm cảnh báo để tránh nhiễm chính sự cố đang diễn ra) kết hợp với cùng khung giờ của **7 ngày trước (`SameHour_7d`)**:
     $$B_{p90}(s, op, t_0) = \max\Big(\text{Quantile}_{0.90}\big([t_0 - 65\text{m}, t_0 - 5\text{m}]\big),\; \text{Quantile}_{0.90}\big(\text{SameHour\_7d}\big)\Big)$$
  4. **Máy trạng thái Khởi động lạnh (`Cold-Start State Machine`):**
     - `sample_count < 50`: Trạng thái `COLD_START` $\rightarrow$ Cấm hạ mức ưu tiên cảnh báo xuống `P3`.
     - `50 <= sample_count < 500`: Trạng thái `WARMING_UP` $\rightarrow$ Nhân hệ số an toàn $1{,}25\times$ và gắn nhãn cảnh báo trên thẻ.
     - `sample_count >= 500`: Trạng thái `CALIBRATED` $\rightarrow$ Kích hoạt Cổng tất định bỏ qua LLM và Neo bằng chứng `C3`.

### 2.2 Truy xuất Ngữ cảnh theo Yêu cầu & Chống Bão Cảnh báo (On-Demand Federated Retrieval & Storm Control)
Khi xảy ra sự cố hạ tầng, Alertmanager có thể bắn hàng trăm cảnh báo trong vòng vài phút. Để không gây quá tải ngược lên cụm Loki/Tempo của khách hàng và không làm nổ chi phí LLM, hệ thống áp dụng 3 lớp giảm tải:

1. **Lớp 1 — Khử trùng Fingerprint tại biên (Redis Atomic Lock):**
   - Khóa `SET alert:dedup:{tenant}:{fingerprint} NX EX 300`. Cảnh báo có cùng `fingerprint` đang `firing` trong 5 phút chỉ tăng bộ đếm lặp trên thẻ hiện có, không sinh lượt truy vấn và không gọi LLM mới.
2. **Lớp 2 — Gom cụm cửa sổ theo Đồ thị & Cache vùng lân cận (`Micro-Batch Incident Coalescing`):**
   - Bộ tiêu thụ Redpanda giữ bộ đệm ngắn (`2–5 giây`) và gộp cảnh báo vào `Incident` đang mở (cửa sổ `T_group = 180s`) nếu nằm cách các dịch vụ đang có sự cố $\le 2$ hop trên đồ thị.
   - **Cache ngữ cảnh dùng chung theo vùng đồ thị (`Neighborhood Context Cache`):** Khi hai dịch vụ kề nhau (ví dụ `frontend` và `checkoutservice`) cùng báo động cách nhau vài giây, kết quả truy vấn Loki/Tempo của vùng đồ thị 2-hop được lưu tạm trong Redis (`TTL = 30s`) để tái sử dụng, tránh truy vấn trùng lặp vào Loki/Tempo.
3. **Lớp 3 — Truy xuất Fusion `C1` có Khuếch đại Bất thường (`Anomaly-Boosted Fusion Score`):**
   - Trong luận văn GĐ2 (`services/retrieval/hybrid_bm25_graph.py:370`), công thức `C1` là:
     $$S_{\text{C1}}(e) = \alpha \cdot \tilde{S}_{\text{BM25}}(e) + \beta \cdot \exp\left(-\frac{|\Delta t|}{\tau}\right) + \gamma \cdot \frac{1}{1 + d_G(s_0, s_e)}$$
   - Trong bản Production, để khắc phục hiện tượng top-6 bị lấp đầy bởi các span bình thường của request khác (*Hạn chế 4* Chương 8: 128 cửa sổ lỗi bị Judge trả `FALSE_POSITIVE` dù có đủ 6 sự kiện), điểm xếp hạng được nhân thêm hệ số khuếch đại độ lệch ngưỡng nền $\Psi_{\text{anom}}(e)$:
     $$\Psi_{\text{anom}}(e) = 1 + \lambda_1 \cdot \mathbb{I}[\text{level} \in \{\text{WARN, ERROR, FATAL}\}] + \lambda_2 \cdot \min\left(3{,}0,\; \max\left(0,\; \frac{\text{duration}(e)}{B_{p90}(s_e, op_e)} - 1\right)\right)$$
   - Nhờ đó, các span thực sự bị nghẽn hoặc có lỗi ứng dụng được ưu tiên đưa vào top-$K$ trước khi gọi Judge.

---

## 3. Thiết kế Tầng AI / LLM Engineering & Độ tin cậy

### 3.1 Phễu Giảm Lượt Gọi LLM & Vai trò Thực tế của Cache (Cost Reduction Funnel)
Trong môi trường phát lại ngoại tuyến (offline replay) của luận văn, cache khóa chính xác `sha256(prompt + model + temperature + max_tokens + repeat)` đạt tỷ lệ trúng 100% ở các lượt chạy lại. Tuy nhiên, **trên luồng thời gian thực (live stream), prompt chứa dấu thời gian (`timestamp`), chuỗi giá trị metric thực và `duration_ms` của từng span mới, nên tỷ lệ trúng prompt cache chính xác gần như bằng 0%** (cache chỉ còn tác dụng chống gọi trùng khi retry lỗi mạng hoặc khi chạy kiểm toán lại).

Do đó, trên luồng Production thật, việc cắt giảm chi phí LLM dựa vào **3 tầng lọc trước Judge** (các tỷ lệ phần trăm dưới đây là **giả định kịch bản thiết kế**, chưa phải số đo thực nghiệm; riêng hiệu quả của Tầng 2 sẽ được kiểm định chính thức qua giả thuyết `H8` ở GĐ3):

```text
100% Raw Alerts từ Alertmanager (Kịch bản minh họa giả định)
  │
  ├─► [Tầng 1: Fingerprint Dedup & Cooldown 300s] ──────────────────► Giả định cắt ~40–50% cảnh báo lặp ($0 LLM)
  │
  ├─► [Tầng 2: Pre-Judge Deterministic Gate (C3-Online, H8)] ───────► Giả định cắt tiếp ~25–35% cảnh báo nhiễu không có
  │    (Chỉ áp dụng khi đã qua Cold-Start và severity != critical)     span > p90 và không có log lỗi ($0 LLM)
  │
  └─► [Tầng 3: LLM Judge + Incident Coalescing cho RCA Summarizer] ─► Mục tiêu chỉ ~15–25% cảnh báo đầu vào phải gọi Judge,
       (Cache SHA-256 dùng cho retry idempotency & offline audit)      và nhiều cảnh báo cùng sự cố chỉ gọi Summarizer 1 lần
```

### 3.2 Bộ lọc Che Dữ liệu Nhạy cảm trước khi rời VPC (`PII & Secret Scrubber`)
Mọi chuỗi văn bản từ log và tag của trace đều phải đi qua pipeline làm sạch tất định trước khi ghép vào prompt (mục tiêu độ trễ **$p_{99} < 10\text{ ms}$/cảnh báo**, đồng bộ với `04-prd` NFR-06):
1. **Xóa khóa bí mật (Secrets & Credentials):** Chuỗi `Bearer [A-Za-z0-9\-._~+/]+=*`, khóa AWS `AKIA[0-9A-Z]{16}`, khóa API tổng quát `(api_key|token|secret|password|passwd|pwd)\s*[:=]\s*\S+` $\rightarrow$ thay bằng `<REDACTED_SECRET>`.
2. **Che thông tin định danh cá nhân (PII):** Email $\rightarrow$ `<EMAIL>`, Số điện thoại $\rightarrow$ `<PHONE>`, Số thẻ thanh toán (kiểm tra Luhn) $\rightarrow$ `<CARD>`, Địa chỉ IPv4/IPv6 $\rightarrow$ băm cố định theo muối `IP_HASH_a1b2` để giữ tính tương quan giữa các dòng log mà không lộ IP thật.

### 3.3 Xử lý Thiên lệch Xác nhận: Cơ chế đã Chứng minh (`C3`) và Giả thuyết Mở rộng trong Prompt
Cần phân biệt rạch ròi giữa **kết quả đã được chứng minh trong luận văn** và **giả thuyết thiết kế mở rộng cho sản phẩm**:
- **Những gì luận văn đã chứng minh (H1 ở M5 và H3 ở M6/M8):**
  - Thí nghiệm can thiệp `H1` trên `val` (QĐ-028) chỉ chứng minh rằng **sự hiện diện của trace cục bộ sát thời điểm cảnh báo ($t_0$) làm tăng mạnh tỷ lệ Judge trả `TRUE_ALERT`** (lên `60,8%` trên cửa sổ bình thường so với `18,1%` khi chỉ có log cục bộ và `27,7%` khi chỉ có trace lân cận), qua đó bác bỏ giả thuyết nhiễu từ bằng chứng lân cận. `H1` **không** chứng minh nguyên nhân là vì prompt thiếu con số ngưỡng nền.
  - Cơ chế đã được chứng minh hiệu quả trong `H3` là **bộ neo bằng chứng hậu kiểm tất định `C3` (`services/judge/policy.py::decide`)**: sau khi Judge trả `raw_verdict = TRUE_ALERT`, hàm `is_abnormal()` kiểm tra xem bằng chứng được trích tại `s0` có chứa log `ERROR/WARN` hoặc trace span có `duration_ms > baseline_ms` hay không; nếu không thỏa thì hạ phán quyết xuống `UNCERTAIN` (trên tập `test`, cơ chế này cắt `1.171 / 1.235` báo động giả của `C1`).
- **Thiết kế trong bản Production:**
  1. **Trụ cột chính (Bắt buộc):** Giữ nguyên bộ neo hậu kiểm tất định `C3` (`policy.py::decide`) kết hợp nguồn ngưỡng nền trực tuyến `C3-Online` và trần bảo vệ `severity = critical` (chỉ hạ tối đa xuống `P2`, không xuống `P3`).
  2. **Giả thuyết mở rộng (Tùy chọn qua cờ cấu hình — cần kiểm nghiệm A/B ở GĐ3):** Thử nghiệm in kèm thông tin phân vị nền từ `DDSketch` ngay bên cạnh mỗi span trong prompt (`duration=420.5ms [baseline p50=42ms, p90=95ms]`) để xem có giúp giảm thêm tỷ lệ Judge bác nhầm các cửa sổ lỗi (*Hạn chế 4*: 128 FN do Judge trả `FALSE_POSITIVE`) hay không.

### 3.4 Động cơ Đánh giá Liên tục & Phát hiện Trôi (`Continuous Eval & Drift Loop`)
- **Thu thập Golden Set tự động:** Mỗi khi kỹ sư SRE bấm `👍` hoặc `👎 (Hạ nhầm)` trên Slack, toàn bộ gói `(AlertEvent, ContextEvents, BaselineSnapshot, HumanVerdict)` được lưu vào bảng `golden_feedback_set` trong PostgreSQL.
- **Shadow Regression Runner:** Trước khi nâng cấp phiên bản model LLM hoặc thay đổi prompt, hệ thống chạy replay tự động trên tập `golden_feedback_set` (tái sử dụng `eval/harness/` của luận văn) để kiểm tra xem tỷ lệ đồng thuận với kỹ sư và **Tỷ lệ sự cố thật bị hạ nhầm xuống P3 (`False Downgrade Rate`)** có bị suy giảm hay không.

---

## 4. Kiến trúc Lưu trữ Đa tầng (Polyglot Persistence Schema)

| Hệ lưu trữ | Bảng / Cấu trúc chính | Mục đích & Chính sách Vòng đời (TTL) |
|---|---|---|
| **ClickHouse**<br>*(OLAP & Time-Series Sketches)* | • `span_latency_sketches_1m` (`AggregatingMergeTree`, mỗi mức phân vị một cột `AggregateFunction(quantileDD(0.01, level), Float64)`)<br>• `fact_triage_audit_log` (`MergeTree` — mở rộng từ `fact_alert_evaluation` với đầy đủ `prompt_tokens`, `completion_tokens`, `estimated_cost_usd`)<br>• `fact_llm_cost_ledger` (`SummingMergeTree`) | • Lưu trạng thái phân vị DDSketch (`quantileDDState`) theo phút (TTL: `14 ngày`).<br>• Lưu nhật ký kiểm toán mọi quyết định, độ trễ từng chặng, chi phí USD và bằng chứng đã che PII (Partition theo tháng, TTL: `90 ngày`).<br>• Tổng hợp chi phí token theo thời gian thực cho từng tenant/service. |
| **PostgreSQL**<br>*(OLTP & Control Plane)* | • `tenants`, `service_mappings`, `budget_policies`<br>• `incidents`, `diagnostic_reports`, `diagnostic_rejected`<br>• `service_topology_snapshots`<br>• `human_feedback` | • Lưu cấu hình khách hàng, hạn mức FinOps, phân quyền RBAC.<br>• Quản lý vòng đời sự cố (`OPEN`, `ACKNOWLEDGED`, `RESOLVED`) và báo cáo RCA.<br>• Lưu phản hồi `👍/👎` của kỹ sư làm dữ liệu kiểm thử hồi quy (giữ vĩnh viễn). |
| **Redis**<br>*(In-Memory State)* | • `alert:dedup:{tenant}:{fp}`<br>• `ctx:cache:{tenant}:{service_hop_hash}`<br>• `budget:daily:{tenant}:{yyyy-mm-dd}` | • Khóa khử trùng cảnh báo và chống bão cảnh báo.<br>• Cache ngắn hạn (`30s`) kết quả truy vấn Loki/Tempo.<br>• Bộ đếm nguyên tử (`INCRBYFLOAT`) kiểm tra trần ngân sách LLM trong `< 1 ms`. |

---

## 5. Kiến trúc Đóng gói & Chia sẻ Lõi với Luận văn (`Clean Core Packaging`)

Để đảm bảo **việc phát triển sản phẩm không bao giờ làm hỏng tính tái lập của luận văn**, cấu trúc phần mềm được tách thành 2 tầng rõ ràng:

1. **Gói lõi Python `ctav-core` (Trích xuất từ repo luận văn ở mốc M13 sau khi gỡ hardcode, gắn tag `core-v1.0.0`):**
   - Chỉ chứa các giao thức và thuật toán Python thuần túy:
     - `packages/schemas/protocols.py` (`SourceAdapter`, `Detector`, `RetrievalStrategy`, `Judge`)
     - `packages/schemas/models.py` (`TelemetryWindow`, `AlertCandidate`, `ContextEvent`, `JudgedAlert`, `DiagnosticReport`)
     - `services/retrieval/` (`bm25_hybrid`, `hybrid_bm25_graph` / Fusion `C1`)
     - `services/judge/policy.py` (`PolicyConfig`, `EvidenceFact`, `PolicyDecision`, `is_abnormal`, `decide`)
     - `services/rca_agent/` (`grouping`, `propagation`, `summarizer` cùng bộ kiểm duyệt 5 quy tắc `invalid_json`, `confidence_out_of_range`, `executable_action`, `no_evidence`, `suspicious`)
2. **Ứng dụng thương mại `alert-triage` (Repo sản phẩm riêng biệt):**
   - Phụ thuộc vào `ctav-core` qua khóa phiên bản cứng.
   - Chứa tầng giao diện TypeScript/React (bao gồm hàm hiển thị chuỗi bước chính sách `policySteps()` ở `services/web/src/lib/util.ts` mô phỏng lại thứ tự của `policy.py::decide`) và toàn bộ phần mở rộng Production: Webhook Alertmanager/Grafana, Connectors Loki/Tempo/Prometheus/K8s, PII Scrubber, Redis/Redpanda Queue, Slack/PagerDuty Bot, cổng tiền lọc nhóm `P3` trước Summarizer và FinOps Spend Guard.
