# 06 — Scope Guard: Bộ neo mục tiêu

> Đây là tài liệu quan trọng nhất trong bộ. Nạp nó vào context **mỗi phiên code**, trước cả tài liệu kiến trúc.
>
> Mục đích: giữ cho mọi dòng code phục vụ luận văn, không phục vụ sự thú vị kỹ thuật.

---

## 1. Mục tiêu duy nhất

> **(A)** Đề xuất và chứng minh **CTAV** — thẩm định cảnh báo có nhận biết topology, được hiệu chỉnh theo nguồn gốc bằng chứng — giữ mức tăng recall của topology mà không làm tăng báo động giả so với BM25 trong cùng ngân sách LLM; **(B)** dùng CTAV làm nền cho tác tử RCA định vị service gốc và sinh báo cáo có cấu trúc; cả hai chạy trên **một platform demo được** trước hội đồng.

Đây không phải một sản phẩm. Đây là **bằng chứng cho hai luận điểm khoa học** (giả thuyết H0–H5, `08-research-direction.md` §5), cộng với platform hiện thực hoá chúng. Mọi thứ khác là phương tiện.

> Cập nhật 2026-10-18 (QĐ-011): trước đây Nhánh A là "so sánh 4–5 biến thể RAG". GVHD yêu cầu GĐ2 đưa ra giải pháp và chứng minh nó, nên Nhánh A đổi sang CTAV; số biến thể retrieval thu gọn (xem §3).

---

## 2. Phép thử hai câu hỏi

Trước khi viết bất kỳ dòng code nào, agent trả lời:

**Câu 1: Việc này phục vụ Nhánh A hay Nhánh B?**

Nếu câu trả lời là "cả hai đều không" — dừng lại.

**Câu 2: Nếu bỏ việc này, luận văn có thiếu bằng chứng nào không?**

Nếu câu trả lời là "không" — việc này là tùy chọn, và tùy chọn nghĩa là **không làm trong 24 tuần**.

Ví dụ áp dụng:

| Đề xuất | Câu 1 | Câu 2 | Kết luận |
|---|---|---|---|
| Ghi `graph_distance` vào `debug` | Nhánh A | Có — cần để chấm context precision | Làm |
| Thêm authentication cho API | Không | Không | Không làm |
| Bootstrap CI cho metrics | Cả hai | Có — không có CI thì kết luận không vững | Làm |
| Thêm dark mode cho dashboard | Không | Không | Không làm |
| Cache LLM response | Cả hai | Có — không cache thì ablation không khả thi | Làm |
| Thêm vector search làm biến thể RAG mới | Nhánh A | Không — câu hỏi nghiên cứu là hiệu chỉnh quyết định trên topology, không phải tìm thêm retriever | Không làm |
| Quét θ_topo cho asymmetric gating | Nhánh A | Có — không có đường cong này thì H2/H3 không vững | Làm |
| Viết Dockerfile production multi-stage | Không | Không | Không làm |
| Unit test cho hàm tính F1 | Cả hai | Có — F1 sai thì luận văn sai | Làm |

---

## 3. Trong phạm vi

Danh sách đóng. Nếu một việc không nằm ở đây, mặc định là ngoài phạm vi.

### Nhánh A — Giải pháp CTAV và chứng minh

- [x] 2 retrieval strategy: `bm25_hybrid` (baseline), `hybrid_bm25_graph` (C1 — Weighted Context Fusion α, β, γ của paper)
- [x] Temporal-only (β = 1) và graph-only (γ = 1) **chỉ là ablation** của C1, không phải module riêng
- [x] C2 Asymmetric Confidence Gating (θ_local, θ_topo) — `services/judge/policy.py`
- [x] C3 Evidence anchoring (bằng chứng phải neo vào `s_0` hoặc đường gọi lỗi/chậm tới `s_0`) — `services/judge/policy.py`
- [x] C4 Adaptive Two-Tier Routing (BM25 trước, topology khi cần) — `services/judge/routing.py`
- [x] Baseline so sánh: detector-only, LLM-không-RAG, BM25, C1 chưa hiệu chỉnh
- [x] Thí nghiệm cơ chế H1 (tỷ lệ bằng chứng graph trong prompt)
- [x] Interface chung `RetrievalStrategy` để hoán đổi bằng config
- [x] Service dependency graph dựng từ trace Nezha
- [x] Eval harness sinh P/R/F1/FPR/coverage/latency/tokens/chi phí có bootstrap CI + McNemar
- [x] Đăng ký giả thuyết trước khi chạy `test`
- [x] Chấm context precision thủ công trên mẫu

### Nhánh B — RCA Agent

- [x] Rescue Score có tham số η1, η2, η3, τ + ablation xác định cấu hình tối ưu
- [x] Alert Grouping theo thời gian + topology
- [x] Fault Propagation Analysis: backward tracing mức 1-hop và mức full path
- [x] Diagnostic Summary theo JSON schema cố định, có validator
- [x] `require_evidence`: không có bằng chứng thì không phát hành chẩn đoán
- [x] Hit@1, Hit@3, Alert Reduction Ratio, JSON valid rate, E2E latency
- [x] Đánh giá chất lượng chẩn đoán bằng người trên mẫu 30 incident

### Hạ tầng tối thiểu để hai nhánh chạy được

- [x] Stream replayer từ Nezha có watermark
- [x] Isolation Forest detector
- [x] LLM judge: một model API cố định `gemini-2.5-flash-lite` + cache (QĐ-013; local-first không dùng trong GĐ2)
- [x] ClickHouse + PostgreSQL lưu kết quả
- [x] API đọc dữ liệu
- [x] Dashboard 4 màn hình
- [x] Docker Compose profiles dev/full
- [x] Unit test cho các hàm tính toán quan trọng

---

## 4. Ngoài phạm vi — danh sách cấm

Agent **không được tự ý thêm** bất kỳ mục nào dưới đây. Nếu người dùng yêu cầu, agent phải hỏi lại: "việc này nằm ngoài phạm vi GĐ2, xác nhận vẫn muốn làm?"

### Cấm về công nghệ

| Mục | Vì sao cấm |
|---|---|
| Kubernetes, Helm | Ngoài phạm vi đã tuyên bố với GVHD |
| Vector database (Chroma, Qdrant, pgvector) | Thành biến thể RAG thứ 6, làm loãng so sánh |
| Agent framework (LangChain, AutoGen, CrewAI) | Tác tử ở đây là 3 bước tuần tự có kiểm soát; framework thêm biến số không kiểm soát được |
| Fine-tuning LLM | Ngoài phạm vi, ngoài khả năng phần cứng |
| MCTS / Monte Carlo Tree Search | Bản định hướng đã ghi rõ vượt phạm vi phần cứng hiện tại |
| Multi-agent song song (Recursion-of-Thought) | Bản định hướng đã chọn chạy tuần tự cho phạm vi 6 tháng |
| Message queue phức tạp, Kafka Streams, Flink | Profile `dev` chạy in-process là đủ |
| Redis, Elasticsearch | Không có nhu cầu trong phạm vi |
| CI/CD pipeline đầy đủ | Repo nghiên cứu, không phải sản phẩm |
| Web framework nặng cho dashboard | 4 màn hình, Streamlit cũng chấp nhận được |

### Cấm về tính năng

| Mục | Vì sao cấm |
|---|---|
| Authentication, RBAC, user management | Chạy local, một người dùng |
| Multi-tenant, workspace | Không có trong bài toán nghiên cứu |
| Alert notification (email, Slack, webhook) | Không tạo bằng chứng cho luận văn |
| Runbook thực thi tự động | Bản định hướng đã tuyên bố rõ không làm |
| Sinh câu lệnh shell trong `suggested_actions` | Chỉ sinh mô tả, đã cam kết với GVHD |
| Self-healing, auto-remediation | Vượt xa phạm vi |
| Real-time streaming từ hệ thống thật | Là việc của GĐ3 |
| Hỗ trợ dataset thứ hai | Là việc của GĐ3 |
| Billing, quota, rate limiting | Không liên quan |

### Cấm về mở rộng nghiên cứu

| Mục | Vì sao cấm |
|---|---|
| Biến thể retrieval thứ 3 trở lên (`cross_modal`, RRF, vector search, reranker...) | Đã cắt ở QĐ-011, ghi trong `ideas.md`; câu hỏi nghiên cứu nằm ở chính sách quyết định, không ở retriever |
| Detector thứ hai (LSTM, GDN, MTAD-GAT) | Detector là biến cố định trong thiết kế thực nghiệm; đổi nó phá vỡ tính so sánh |
| Thêm nhãn thứ tư cho judge | GĐ1 đã chốt 3 nhãn |
| Prompt engineering tùy hứng | Prompt là biến cố định giữa các biến thể RAG; đổi prompt giữa chừng làm kết quả không so sánh được |
| Đổi LLM backend giữa chừng | Cùng lý do trên |

---

## 5. Cây quyết định khi có đề xuất mới

```text
Có đề xuất thêm một thứ gì đó
        │
        ▼
Nó có trong §3 (trong phạm vi) không?
        │
   ┌────┴────┐
  Có        Không
   │          │
   │          ▼
   │    Nó có trong §4 (danh sách cấm) không?
   │          │
   │     ┌────┴────┐
   │    Có        Không
   │     │          │
   │     ▼          ▼
   │  TỪ CHỐI   Áp phép thử 2 câu hỏi (§2)
   │  ghi vào        │
   │  ideas.md  ┌────┴────┐
   │        Cả 2 "có"   Có 1 "không"
   │            │          │
   ▼            ▼          ▼
 LÀM          HỎI       TỪ CHỐI
           người dùng  ghi ideas.md
```

**`docs/ideas.md`** là nơi chứa mọi ý tưởng bị từ chối. Không xóa chúng — chúng là nguyên liệu cho phần "hướng phát triển" của luận văn và cho GĐ3.

---

## 6. Các kiểu lạc đề thường gặp

Nhận diện sớm để chặn.

### 6.1 Lạc đề kiểu "làm cho chắc"

> "Thêm authentication cho API phòng khi sau này deploy public."

Không có "sau này" trong GĐ2. API chạy trên localhost.

### 6.2 Lạc đề kiểu "chuẩn công nghiệp"

> "Nên dùng LangChain cho phần agent vì đó là chuẩn."

Đây là luận văn, không phải sản phẩm. Tác tử ba bước tuần tự viết tay dễ giải thích, dễ debug, và dễ bảo vệ trước hội đồng hơn một framework hộp đen.

### 6.3 Lạc đề kiểu "cải thiện nhỏ"

> "Thêm reranking bằng cross-encoder sau retrieval, chắc sẽ tốt hơn."

Đây là một biến can thiệp mới. Thêm nó vào giữa chừng làm hỏng so sánh có kiểm soát. Ghi vào `ideas.md`.

### 6.4 Lạc đề kiểu "đằng nào cũng phải làm"

> "Dashboard cần thêm màn hình quản lý cấu hình để tiện chỉnh tham số."

Tham số nằm trong YAML. Chỉnh bằng editor. Màn hình quản lý không tạo ra bằng chứng nào cho luận văn.

### 6.5 Lạc đề kiểu "sản phẩm hóa"

> "Nên tách repo thành microservices riêng, mỗi service một Dockerfile production."

Đây là repo nghiên cứu. Tối ưu cho khả năng tái lập thực nghiệm, không phải cho vận hành production.

### 6.6 Lạc đề kiểu "kéo dự án khác vào"

> "Có thể dùng Smart AI Ops Gateway làm nguồn dữ liệu live."

Đó là kế hoạch GĐ3, đã được cân nhắc và xếp là phương án rủi ro cao. Không làm trong GĐ2.

---

## 7. Neo mục tiêu theo cột mốc

Mỗi lúc chỉ làm việc của mốc hiện tại (`docs/CURRENT-MILESTONE.md`) trong `04-implementation-roadmap.md`.

**Quy tắc nạp context:** chỉ nạp phần mốc hiện tại, không nạp toàn bộ roadmap. Agent nhìn thấy việc của M10 khi đang ở M1 sẽ có xu hướng chuẩn bị trước, và "chuẩn bị trước" là một dạng lạc đề.

Nếu agent thấy mình đang làm việc không có trong mốc hiện tại, dừng và hỏi. Hết mốc thì viết báo cáo mốc (`04` §2) trước khi sang mốc sau.

---

## 8. Ba cổng chặn không được vượt

Đây là các mốc mà nếu không đạt thì **không được đi tiếp**, dù có áp lực tiến độ:

| Cổng | Mốc | Điều kiện | Nếu không đạt |
|---|---|---|---|
| Nhãn dữ liệu | M0 | Biết chính xác Nezha có nhãn root-cause hay không | Dừng, gán tay hoặc đổi dataset |
| G-port | M2 | Tái lập GĐ1 Phase 4 theo từng tầng trên `paper_300` (judge mock): P = 0.3158, FPR = 0.0458, lệch ≤ 1 cửa sổ mỗi ô — QĐ-012 | Dừng, tìm lỗi port code |
| G-paper | M3 | Tái lập Table 1 của paper từ cache Gemini, cache hit 100% | Dừng, tìm chỗ prompt/retrieval khác GĐ1 |
| H0 tái lập vấn đề | M4 | Topology chưa hiệu chỉnh tăng FPR so với BM25 trên split GĐ2 | Dừng, trao đổi GVHD, viết lại câu chuyện |
| Quy trình test split | M8 | Chỉ chạm `test` một lần, sau khi đã đăng ký giả thuyết và chốt tham số trên `val` | Không có cách sửa — phải trung thực ghi lại |

(Hai cổng "Tái lập baseline Tuần 3" và "test split Tuần 11" của bản gốc được thay bằng các cổng trên ở QĐ-011/012/014.)

Vượt cổng bằng cách bỏ qua điều kiện là cách chắc chắn nhất để hỏng luận văn.

---

## 9. Câu hỏi tự kiểm khi đóng mỗi mốc

- [ ] Mốc này tôi có tạo ra bằng chứng nào cho Nhánh A hoặc Nhánh B không?
- [ ] Có dòng code nào tôi viết mà không phục vụ hai nhánh đó không?
- [ ] Tôi có chạm vào `test` split không?
- [ ] Có tham số thí nghiệm nào bị hardcode không?
- [ ] `experiment-log.md` đã cập nhật chưa?
- [ ] Tôi có đang ở đúng mốc trong roadmap không?
- [ ] Báo cáo mốc đã đủ 4 phần, nhất là "Cần review gì" và "Vấn đề cần bạn giải quyết"?

Nếu có câu trả lời đáng lo, xử lý ngay trong mốc, đừng để tích tụ.

---

## 10. Nhắc lại, ngắn gọn

```text
Mục tiêu:  A = CTAV: topology + hiệu chỉnh theo nguồn gốc bằng chứng, chứng minh bằng H0–H4
           B = tác tử RCA trên nền CTAV, chứng minh bằng H5
           Platform demo được trước hội đồng

Dữ liệu:   Nezha, chia dev/val/test cố định
Cấm:       test split trước M8 (và trước đăng ký giả thuyết ở M7)
Bắt buộc:  báo cáo mốc sau mỗi mốc (docs/milestones/)
Cấm:       hardcode tham số thí nghiệm
Cấm:       thêm biến thể / kỹ thuật ngoài kế hoạch
Cấm:       ghi đè kết quả cũ

Khi phân vân: dừng và hỏi, ghi vào ideas.md, làm đúng đặc tả
```
