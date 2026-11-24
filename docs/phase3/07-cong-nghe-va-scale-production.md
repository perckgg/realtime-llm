# 07 — Lựa chọn Công nghệ & Chiến lược Scale khi lên Production

> **Bản thiết kế (2026-11-24).** Bổ sung cho `05-kien-truc-bigdata-ai-production.md`: 05 mô tả kiến trúc **đích** (v0.3);
> file này quyết định **công nghệ nào được dùng ở bậc nào, vì sao, và scale ra sao**. Mọi con số tải ở §1 là **giả định
> thiết kế**, phải đo lại ở GĐ3 (testbed) và ở shadow POC trước khi dựa vào.

---

## 0. Bộ lọc 5 câu hỏi (áp cho mọi công nghệ)

Một công nghệ chỉ được thêm khi trả lời được cả năm câu:

| # | Câu hỏi | Trượt nghĩa là |
|---|---|---|
| **Q1** | **Phục vụ việc gì?** Gắn được với một RQ/mốc GĐ3, một yêu cầu FR/NFR ở `04`, hoặc một nút thắt **đã đo** | Không thêm |
| **Q2** | **Có giữ được tái lập không?** Cache LLM, tính tất định, parity GĐ2 `26/26` / `38/38` / `114/114` | Không dùng trong repo luận văn |
| **Q3** | **Chạy được trên phần cứng hiện có không?** (máy cá nhân / VM thuê theo giờ / hạ tầng khách) | Hoãn tới khi có phần cứng |
| **Q4** | **Có đường lui không?** Cắt được mà không mất bằng chứng hoặc không làm sập sản phẩm | Chỉ dùng sau lớp trừu tượng có bản dự phòng |
| **Q5** | **Chi phí học và vận hành có vừa lịch không?** (mỗi mốc GĐ3 chỉ 2–3 tuần; product do một người vận hành) | Hoãn |

Kết luận ghi theo 4 mức: **Dùng** · **Có điều kiện** (kèm điều kiện đo được) · **Chưa** (ghi bậc sẽ xét lại) · **Không**.

---

## 1. Hồ sơ tải giả định

| Hồ sơ | Giả định | Hệ quả |
|---|---|---|
| **GĐ3 — testbed** | Online Boutique ~11 service, bộ sinh tải cố định; cảnh báo do detector sinh | Tải nhỏ; mục tiêu là **parity và số đo độ trễ**, không phải thông lượng |
| **v0.1 — 1 tenant** | 40 service; 10.000 cảnh báo/tháng (≈ 0,23 cảnh báo/phút trung bình); bão 200–500 cảnh báo trong ~5 phút; 3–6 truy vấn Loki/Tempo/Prometheus cho mỗi cảnh báo đi qua khử trùng | Một tiến trình FastAPI + PostgreSQL chịu được thoải mái; giới hạn thật là **API LLM và cụm Loki/Tempo của khách** |
| **v0.3 — nhiều tenant (Managed)** | 50 tenant; giả sử 3 tenant bão cùng lúc ⇒ ~1.500 cảnh báo/phút (≈ 25/giây) | Cần hàng đợi bền + worker scale ngang + token bucket LLM dùng chung |
| **Span metric** (phương án A, §4.3) | `40 service × 20 operation × 2 span.kind × 2 status.code` ≈ 3.200 chuỗi/tenant, 1 điểm/phút ⇒ 50 tenant ≈ 160.000 điểm/phút (≈ 2.700/giây) | Prometheus/Mimir hoặc ClickHouse xử lý được, không cần Kafka |
| **Span thô** (phương án B, §4.3) | 1.000 request/giây × ~10 span ⇒ ~10.000 span/giây **mỗi tenant** | Đây là điểm duy nhất thực sự cần Kafka/Redpanda và scale ngang |

---

## 2. Bảng quyết định công nghệ

| Công nghệ | Q1 — phục vụ | Q2 / Q3 / Q4 / Q5 | GĐ3 | v0.1 | v0.2 | v0.3 |
|---|---|---|---|---|---|---|
| **Python 3 + FastAPI + asyncio** | Toàn bộ lõi `ctav-core` và API hiện có | Đã có, parity đã kiểm; học 0 | **Dùng** | **Dùng** | **Dùng** | **Dùng** |
| **PostgreSQL** | Sự cố, báo cáo, cấu hình, phản hồi; ở v0.1 còn làm **hàng đợi** (`FOR UPDATE SKIP LOCKED`), khử trùng (`UNIQUE` + `ON CONFLICT`) và trần ngân sách (`UPDATE … RETURNING`) | Đã có | **Dùng** | **Dùng** | **Dùng** | **Dùng** |
| **ClickHouse** | Nhật ký kiểm toán, sổ chi phí, sketch phân vị | Đã có; TTL sẵn | **Dùng** | **Dùng** | **Dùng** | **Dùng** |
| **OTel Collector + `spanmetrics` connector (exponential histogram)** | Ngưỡng nền `C3-Online` **không cần hút span thô** (phương án A, §4.3) | Connector đang ở mức *alpha*; tên mới `span_metrics`; đơn vị mặc định `ms` | **Dùng** (thu telemetry testbed) | **Dùng** | **Dùng** | **Dùng** |
| **Redpanda** (1 node) | G-stream (M15): replay vs stream phải cho cùng candidate | Có sẵn trong profile `full`; nhẹ trên một máy; license BSL 1.1 (§7) | **Dùng** | Chưa | Chưa | Có điều kiện |
| **Apache Kafka** (KRaft) | Hàng đợi bền + scale ngang ở v0.3, đặc biệt nếu chọn phương án B | Apache-2.0; nặng hơn Redpanda khi tự vận hành | Không | Chưa | Chưa | **Có điều kiện** (§3) |
| **Redis / Valkey** | Khóa khử trùng, rate limit, bộ đếm ngân sách **dùng chung giữa ≥ 2 bản API** | Một instance là đủ; Sentinel cho HA | Không | Chưa | **Có điều kiện** (≥ 2 replica) | **Dùng** |
| **DDSketch (`quantileDD` của ClickHouse)** | Phương án B của `C3-Online` | Chỉ khi có span thô; tên hàm phải kiểm trên phiên bản thật (`05` §2.1) | Không (dùng phân vị chính xác) | Chưa | Chưa | Có điều kiện |
| **kind/minikube + Chaos Mesh** | Testbed có nhãn lỗi (M14) | Online Boutique cần ~4 CPU, 4–8 GB RAM; nếu thiếu thì thuê VM theo giờ | **Dùng** | Dùng (môi trường test) | Dùng | Dùng |
| **Helm / Kubernetes cho chính sản phẩm** | Triển khai Enterprise/HA | Không cần khi một máy đủ | Không | Không | Chưa | **Dùng** |
| **Slack Bolt (Socket Mode)** | FR-16, không cần mở cổng public | SDK chính thức | Không | **Dùng** | **Dùng** | **Dùng** |
| **SSE** | Dashboard trực tiếp (M20) | Nhẹ, không cần WebSocket | **Dùng** | Có điều kiện | Dùng | Dùng |
| **Rust (PyO3 extension)** | Đường nóng CPU và bộ lọc PII an toàn trước ReDoS | Xem đánh giá riêng §5 | **Không** | Chưa | Có điều kiện | Có điều kiện |
| **Celery / Temporal** | Điều phối tác vụ | Thừa so với hàng đợi PostgreSQL hoặc consumer group | Không | Không | Không | Chưa |
| **Flink / Spark** | Xử lý luồng lớn | Quá tay ở mọi hồ sơ tải §1 | Không | Không | Không | Không |
| **Vector DB / embedding** | Truy xuất ngữ nghĩa | Đổi bài toán retriever (đã cắt ở QĐ-011), C1 không còn so được với GĐ2 | Không | Không | Chưa | Chưa |
| **LangChain / LlamaIndex** | Điều phối LLM | Prompt ẩn làm vỡ cache key và nhật ký kiểm toán (N5) | Không | Không | Không | Không |
| **vLLM / Ollama** | Model tự host cho khách air-gapped | Cần GPU; GĐ1 đã đo model nhỏ yếu | Không | Không | Không | Có điều kiện (Enterprise) |

---

## 3. Kiến trúc theo bậc và điều kiện nâng bậc

Chỉ nâng bậc khi **chỉ số đo được** chạm ngưỡng, không nâng theo cảm tính.

| Bậc | Thành phần | Nâng lên bậc sau khi |
|---|---|---|
| **Bậc 0 — GĐ3** | Pipeline Python một tiến trình, Redpanda 1 node (1 partition/topic), ClickHouse, PostgreSQL, testbed kind + Chaos Mesh | — (không nâng; mục tiêu là bằng chứng) |
| **Bậc 1 — v0.1** | 1 tiến trình FastAPI (ingest + worker asyncio), PostgreSQL (hàng đợi, khử trùng, ngân sách), ClickHouse, Slack Socket Mode | Cần **≥ 2 bản API** để chịu lỗi, **hoặc** độ sâu hàng đợi PostgreSQL > 1.000 việc trong > 5 phút |
| **Bậc 2 — v0.2** | 2–3 bản API sau load balancer, worker tách tiến trình, **Valkey + Sentinel**, PostgreSQL có PgBouncer | Nhiều tenant với tổng bão > ~20 cảnh báo/giây, **hoặc** phải tự thu span thô (phương án B), **hoặc** độ trễ đọc hàng đợi vượt SLO §6 |
| **Bậc 3 — v0.3** | Kafka (hoặc Redpanda) 3 broker, consumer group cho worker, Valkey, ClickHouse có replica, Helm | Xét shard ClickHouse theo `tenant_id` khi một node không đủ dung lượng |

---

## 4. Scale từng thành phần

### 4.1 Ingest API (không trạng thái)
- **Ngang:** thêm bản sau load balancer; mọi bản như nhau.
- **Đúng đắn:** chỉ trả `202 Accepted` **sau khi đã ghi bền** (PostgreSQL commit ở bậc 1–2; Kafka `acks=all` ở bậc 3). Khử trùng theo `fingerprint` là idempotent nên Alertmanager gửi lại cũng không sinh việc trùng.
- **Dọc:** hầu như không cần — mỗi request chỉ là một lần ghi.

### 4.2 Worker thẩm định
- **Ngang:** thêm worker (bậc 1–2: nhiều tiến trình cùng đọc `SKIP LOCKED`; bậc 3: consumer group).
- **Trần thật không nằm ở số worker** mà ở: (a) rate limit và trần chi phí của API LLM, (b) sức chịu của cụm Loki/Tempo của khách. Vì vậy mỗi worker phải xin "vé" từ **token bucket LLM dùng chung** và **giới hạn đồng thời theo tenant** cho truy vấn telemetry.
- **Hết vé hoặc quá hạn chót 12 s ⇒ fail-open** (N1), không xếp hàng chờ vô hạn.
- **Chống bão:** gom cảnh báo theo sự cố trước, gọi summarizer **một lần mỗi sự cố**, nên số lượt gọi LLM tăng theo số sự cố chứ không theo số cảnh báo.

### 4.3 Ngưỡng nền `C3-Online` — chọn nguồn phân vị
| | **Phương án A (mặc định v0.1–v0.2)** | **Phương án B (v0.3, khi cần độ chính xác cao)** | **GĐ3 (luận văn)** |
|---|---|---|---|
| Nguồn | OTel `spanmetrics` connector với `histogram: exponential` (`max_size` mặc định 160), chiều mặc định `service.name`, `span.name`, `span.kind`, `status.code` | Span thô → Kafka → ClickHouse Materialized View `quantileDDState` | Span thô của testbed trong ClickHouse |
| Tính phân vị | Từ exponential histogram (sai số theo độ rộng thùng) | DDSketch, sai số tương đối 1% | **Phân vị chính xác** (`quantileExact`) để tái lập |
| Hút span thô? | Không — khớp nguyên tắc zero-copy | Có | Có (môi trường thử) |
| Scale | Theo số chuỗi (§1), rất nhẹ | Theo số span/giây, cần partition theo `(tenant, service)` | Không cần |

**Kiểm chứng bắt buộc trước khi dùng A hoặc B ngoài GĐ3:** chạy trên `val` của testbed, so phán quyết `C3` dùng phân vị xấp xỉ với phân vị chính xác; yêu cầu tỷ lệ phán quyết trùng ≥ 99% (con số mục tiêu, chốt lại khi đo).

### 4.4 Kafka / Redpanda (bậc 3)
- **Ngang:** partition là đơn vị song song; một consumer group chỉ có tối đa N consumer hoạt động với N partition. Thêm broker để rải partition.
- **Khóa partition:**

| Topic | Khóa | Lý do |
|---|---|---|
| `raw_alerts` | `tenant_id` | Gom sự cố cần thấy cảnh báo của nhiều service cùng lúc |
| `span_raw` (chỉ phương án B) | `(tenant_id, service)` | Mọi span của một service vào cùng consumer để gom sketch |
| `change_events` | `tenant_id` | Ít, đi cùng ngữ cảnh cảnh báo |

- **Bền:** `replication.factor=3`, `min.insync.replicas=2`, producer `acks=all` và bật idempotent.
- **Ngữ nghĩa:** *at-least-once* + ghi idempotent (khóa `fingerprint`, upsert sự cố) — không cần *exactly-once*.
- **Thứ tự:** chỉ có trong một partition ⇒ cắt cửa sổ theo **thời gian sự kiện + watermark**, không theo thứ tự đến (cùng nguyên tắc với G-stream ở GĐ3).
- **Bẫy:** tăng số partition sẽ đổi ánh xạ khóa → partition; không giảm được. Chọn dư từ đầu (ví dụ 12–24 partition cho `raw_alerts`).
- **Dọc:** đĩa nhanh, RAM cho page cache, băng thông mạng. Redpanda tận dụng tốt việc thêm nhân CPU (mô hình mỗi luồng một nhân).
- Kafka từ bản 4.0 chỉ chạy KRaft, không còn ZooKeeper.

### 4.5 Redis / Valkey (bậc 2–3)
- **Dọc là chính:** thực thi lệnh trên một luồng; một instance thừa sức cho khử trùng, rate limit và bộ đếm ngân sách ở mọi hồ sơ §1.
- **HA:** Sentinel (tự chuyển master) — đây là chịu lỗi, không phải scale.
- **Ngang:** chỉ khi dữ liệu vượt RAM một máy ⇒ Redis Cluster; dùng hash tag để các khóa cùng tenant cùng slot: `budget:{t42}:2027-03-01`, `alert:dedup:{t42}:<fp>`.
- **Không đọc bộ đếm ngân sách từ replica** (sao chép bất đồng bộ). Bộ đếm phải dựng lại được từ `fact_llm_cost_ledger` nếu Redis mất dữ liệu.

### 4.6 PostgreSQL
- **Dọc trước:** CPU/RAM/IOPS; PgBouncer khi số kết nối tăng theo số worker.
- **Bảng lớn** (phản hồi, sự cố lâu năm): partition theo thời gian.
- **Replica đọc** cho Web UI và báo cáo tuần.
- **Gom sự cố đồng thời:** khóa tư vấn (`pg_advisory_xact_lock`) theo `tenant_id` để hai worker không mở hai sự cố cho cùng một đợt lỗi.

### 4.7 ClickHouse
- **Dọc trước**; TTL như `05` §4.
- **HA:** `ReplicatedMergeTree` + ClickHouse Keeper khi cần chịu lỗi.
- **Ngang:** shard theo `tenant_id` ở v0.3+ khi một node không đủ dung lượng hoặc tốc độ ghi.

### 4.8 Bảo vệ cụm Observability của khách
- Giới hạn đồng thời và tốc độ truy vấn theo tenant tới Loki/Tempo/Prometheus; timeout cứng 3 s (FR-04).
- Circuit breaker: lỗi liên tiếp ⇒ ngừng truy vấn một khoảng, cảnh báo đi nhánh fail-open.
- Cache ngữ cảnh theo vùng đồ thị (`05` §2.2), TTL ngắn.

---

## 5. Rust — đánh giá riêng

**Kết luận ngắn:** không dùng trong GĐ3; trong product chỉ dùng **có mục tiêu**, dưới dạng module mở rộng cho Python (PyO3/maturin), sau khi profiling chứng minh nút thắt. Không viết lại lõi bằng Rust.

| Câu hỏi | GĐ3 (luận văn) | Product |
|---|---|---|
| **Q1 — phục vụ** | Không RQ nào cần; nút thắt là API LLM và I/O, không phải CPU | (a) Bộ lọc PII: crate `regex` của Rust bảo đảm thời gian khớp tuyến tính, **không bị backtracking thảm họa (ReDoS)** khi gặp dòng log độc hại — `re` của Python thì có thể; (b) đường nóng CPU nếu đo ra: tách token BM25 trên nhiều dòng log, trích đặc trưng span; (c) agent biên dạng một file nhị phân nhỏ cho khách Enterprise/air-gapped |
| **Q2 — tái lập** | Viết lại lõi có nguy cơ vỡ parity `26/26`, `38/38`, `114/114` | Giữ bản Python làm **bản tham chiếu**; module Rust phải qua cùng bộ test vector và test parity |
| **Q3 — phần cứng** | Không liên quan | Không liên quan; lợi ích là giảm CPU/RAM mỗi cảnh báo |
| **Q4 — đường lui** | — | Luôn có bản Python thuần dự phòng, chọn bằng cờ cấu hình |
| **Q5 — chi phí** | Lấy giờ của M13–M19 | Thêm ngôn ngữ thứ hai, CI phải build wheel cho Linux x86_64/arm64 |

**Trình tự đề xuất:**
1. **v0.1:** Python. Bộ lọc PII dùng binding RE2 cho Python (`google-re2`, cũng khớp tuyến tính) để có an toàn ReDoS mà chưa cần Rust.
2. **v0.2 (shadow POC):** profiling thật. Kích hoạt chuyển sang Rust khi một thành phần vượt NFR (ví dụ bộ lọc PII `p99 ≥ 10 ms` — NFR-06) **hoặc** chiếm > 30% CPU worker.
3. **v0.3:** chuyển đúng các điểm nóng đã đo sang PyO3; agent biên Rust chỉ khi có khách air-gapped yêu cầu.

**Lưu ý về scale:** Rust cải thiện **hiệu suất theo chiều dọc** (chi phí CPU/RAM mỗi cảnh báo), không thay đổi kiến trúc scale ngang. Phần chậm nhất của luồng (truy vấn Loki/Tempo, gọi LLM) là I/O, Rust gần như không rút ngắn được.

---

## 6. SLO và ngưỡng kích hoạt hành động

| Chỉ số | SLO / ngưỡng | Hành động khi vượt |
|---|---|---|
| Độ trễ `202 Accepted` (NFR-03) | `p99 < 150 ms` | Thêm bản API (ngang) |
| Độ trễ thẻ triage có LLM (NFR-04) | `p95 < 8 s`, hạn chót 12 s | Kiểm token bucket / độ trễ nhà cung cấp; thêm worker nếu hàng đợi dồn |
| Độ sâu hàng đợi (PostgreSQL) / consumer lag (Kafka) | < 1.000 việc hoặc < 60 s lag | Thêm worker; nếu đã ở bậc 1 lâu ⇒ nâng bậc §3 |
| Tỷ lệ fail-open (`triage_fail_open_total`) | Theo dõi xu hướng; tăng đột biến là sự cố | Kiểm nguyên nhân: hết ngân sách, lỗi LLM, lỗi truy vấn telemetry |
| `False Downgrade Rate` (`06` §4) | Mục tiêu chốt sau POC | Tạm tắt cổng bỏ qua LLM cho service liên quan; ghim `severity=critical` |
| Bộ lọc PII (NFR-06) | `p99 < 10 ms` | Chuyển RE2 → module Rust (§5) |
| Chi phí LLM/tenant/ngày (FR-20) | 80% / 100% trần | Báo / chuyển chế độ tất định + fail-open |

---

## 7. Giấy phép các thành phần (kiểm lại điều khoản trước khi đóng gói thương mại)

| Thành phần | Giấy phép | Lưu ý |
|---|---|---|
| Apache Kafka, OTel Collector, ClickHouse | Apache-2.0 | Thoải mái nhúng và phân phối |
| PostgreSQL | PostgreSQL License | Thoải mái |
| Redpanda Community | BSL 1.1 | Hạn chế cung cấp Redpanda như một dịch vụ streaming; với Managed Cloud cần đọc kỹ điều khoản. Đây là lý do bậc 3 ghi "Kafka **hoặc** Redpanda" |
| Redis (bản 8) | Lựa chọn giữa RSALv2 / SSPLv1 / AGPLv3 | Nếu phân phối kèm sản phẩm, ưu tiên **Valkey** (BSD-3, tương thích giao thức) |
| Grafana, Loki, Tempo | AGPLv3 | Sản phẩm chỉ gọi API qua mạng, không nhúng hay sửa mã của chúng |
| Crate Rust phổ biến (`regex`, `pyo3`) | MIT / Apache-2.0 | Thoải mái |

---

## 8. Áp vào GĐ3 (repo luận văn)

- Chỉ dùng **Bậc 0**: Python, Redpanda 1 node, ClickHouse, PostgreSQL, OTel Collector, kind + Chaos Mesh, SSE.
- `C3-Online` trong luận văn tính **phân vị chính xác** trên ClickHouse của testbed để tái lập; phương án A/B chỉ là phép kiểm phụ (§4.3), không thay con số kiểm định H6–H9.
- Số đo cần cho chương thực nghiệm: parity replay–stream (G-stream), độ trễ từng tầng `p50`/`p95`, chi phí theo thời gian. Không đo thông lượng scale ngang — đó là việc của product.
- Không Redis, không Kafka nhiều broker, không Rust trong repo luận văn.

---

## 9. Quyết định cần chốt

| # | Quyết định | Khuyến nghị |
|---|---|---|
| T1 | Nguồn phân vị cho product | Phương án A (spanmetrics exponential histogram) cho v0.1–v0.2 |
| T2 | Broker ở bậc 3 | Kafka nếu bán Managed Cloud (Apache-2.0); Redpanda nếu chỉ phân phối self-host và điều khoản BSL phù hợp |
| T3 | Redis hay Valkey | Valkey nếu phân phối kèm sản phẩm |
| T4 | Ngưỡng kích hoạt Rust | Theo §5 bước 2; không làm trước khi có số profiling |
