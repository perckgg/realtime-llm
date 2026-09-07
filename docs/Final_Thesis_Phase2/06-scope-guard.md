# 06 — Scope Guard: Bộ neo mục tiêu

> Đây là tài liệu quan trọng nhất trong bộ. Nạp nó vào context **mỗi phiên code**, trước cả tài liệu kiến trúc.
>
> Mục đích: giữ cho mọi dòng code phục vụ luận văn, không phục vụ sự thú vị kỹ thuật.

---

## 1. Mục tiêu duy nhất

> Xây dựng một nền tảng chạy được, có khả năng: **(A)** so sánh có kiểm soát bốn biến thể RAG trên dữ liệu Nezha để xác định kiến trúc retrieval tối ưu cho bài toán AIOps, và **(B)** dùng biến thể tối ưu đó làm nền tảng cho một tác tử chẩn đoán nguyên nhân gốc rễ sinh báo cáo có cấu trúc.

Đây không phải một sản phẩm. Đây là **bằng chứng cho hai luận điểm khoa học**. Mọi thứ khác là phương tiện.

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
| Thêm vector search làm biến thể RAG thứ 6 | Nhánh A | Không — 5 biến thể đã đủ trả lời câu hỏi nghiên cứu | Không làm |
| Viết Dockerfile production multi-stage | Không | Không | Không làm |
| Unit test cho hàm tính F1 | Cả hai | Có — F1 sai thì luận văn sai | Làm |

---

## 3. Trong phạm vi

Danh sách đóng. Nếu một việc không nằm ở đây, mặc định là ngoài phạm vi.

### Nhánh A — So sánh chiến lược RAG

- [x] 5 retrieval strategy: `bm25_hybrid` (baseline), `temporal`, `cross_modal`, `graph`, `hybrid_bm25_graph`
- [x] Interface chung `RetrievalStrategy` để hoán đổi bằng config
- [x] Service dependency graph dựng từ trace Nezha
- [x] Weighted Context Fusion cho Topology-Aware RAG có tham số α, β, γ (Paper & Luận văn)
- [x] Eval harness sinh P/R/F1/FPR/coverage/latency/tokens có CI
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
- [x] LLM judge với local-first routing + cache
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
| Biến thể RAG thứ 6 trở lên | 5 biến thể đã trả lời được câu hỏi nghiên cứu; thêm nữa làm loãng và không kịp |
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

Không có "sau này" trong 24 tuần. API chạy trên localhost.

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

## 7. Neo mục tiêu theo tuần

Mỗi tuần chỉ làm việc của tuần đó trong `04-implementation-roadmap.md`.

**Quy tắc nạp context:** chỉ nạp phần tuần hiện tại, không nạp toàn bộ roadmap. Agent nhìn thấy task Tháng 5 khi đang ở Tuần 3 sẽ có xu hướng chuẩn bị trước, và "chuẩn bị trước" là một dạng lạc đề.

Nếu agent thấy mình đang làm việc không có trong tuần hiện tại, dừng và hỏi.

---

## 8. Ba cổng chặn không được vượt

Đây là các mốc mà nếu không đạt thì **không được đi tiếp**, dù có áp lực tiến độ:

| Cổng | Tuần | Điều kiện | Nếu không đạt |
|---|---|---|---|
| Nhãn dữ liệu | 1 | Biết chính xác Nezha có nhãn root-cause hay không | Dừng, gán tay hoặc đổi dataset |
| Tái lập baseline | 3 | Precision ≈ 0.32, FPR ≈ 0.046 trên 300 window | Dừng, tìm lỗi port code |
| Quy trình test split | 11 | Chỉ chạm `test` một lần, sau khi đã chốt tham số trên `val` | Không có cách sửa — phải trung thực ghi lại |

Vượt cổng bằng cách bỏ qua điều kiện là cách chắc chắn nhất để hỏng luận văn.

---

## 9. Câu hỏi tự kiểm mỗi cuối tuần

- [ ] Tuần này tôi có tạo ra bằng chứng nào cho Nhánh A hoặc Nhánh B không?
- [ ] Có dòng code nào tôi viết mà không phục vụ hai nhánh đó không?
- [ ] Tôi có chạm vào `test` split không?
- [ ] Có tham số thí nghiệm nào bị hardcode không?
- [ ] `experiment-log.md` đã cập nhật chưa?
- [ ] Tôi có đang ở đúng tuần trong roadmap không?

Nếu có câu trả lời đáng lo, xử lý ngay trong tuần, đừng để tích tụ.

---

## 10. Nhắc lại, ngắn gọn

```text
Mục tiêu:  A = biến thể RAG nào tốt nhất cho AIOps
           B = tác tử RCA sinh chẩn đoán có cấu trúc

Dữ liệu:   Nezha, chia dev/val/test cố định
Cấm:       test split trước Tuần 11
Cấm:       hardcode tham số thí nghiệm
Cấm:       thêm biến thể / kỹ thuật ngoài kế hoạch
Cấm:       ghi đè kết quả cũ

Khi phân vân: dừng và hỏi, ghi vào ideas.md, làm đúng đặc tả
```
