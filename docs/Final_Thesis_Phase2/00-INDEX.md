# AIOps RCA Platform — Bộ tài liệu Giai đoạn 2

**Đề tài:** Ứng dụng Mô hình Ngôn ngữ Lớn trong Giám sát Thời gian thực
**HVTH:** Nguyễn Văn Hoàng Khang · **GVHD:** Võ Thị Ngọc Châu
**Môn:** CO5107 — Thực tập 1/2, HK261 · **ĐH Bách Khoa TP.HCM**

---

## Bộ tài liệu gồm

| File | Nội dung | Đọc khi nào |
|---|---|---|
| `00-INDEX.md` | File này. Tổng quan và thứ tự đọc. | Bắt đầu |
| `01-architecture-design.md` | Kiến trúc hệ thống, service breakdown, interface, luồng dữ liệu | Trước khi code dòng đầu tiên |
| `02-data-and-experiment-protocol.md` | Dữ liệu Nezha, chia split, seed, định nghĩa chỉ số, quy tắc chạy thực nghiệm | Tuần 1, và mỗi khi thêm thí nghiệm |
| `03-schemas-and-contracts.md` | Pydantic model, event schema, JSON diagnostic schema, DDL ClickHouse/Postgres | Khi implement bất kỳ service nào |
| `04-implementation-roadmap.md` | Lộ trình 24 tuần, task theo tuần, Definition of Done từng mốc | Đầu mỗi tuần |
| `05-agent-coding-rules.md` | Quy tắc kỹ thuật bắt buộc cho AI coding agent | Nạp vào context mỗi phiên code |
| `06-scope-guard.md` | **Bộ neo mục tiêu** — chống lạc đề, chống scope creep | Nạp vào context mỗi phiên code |
| `07-setup-guide.md` | Dựng môi trường, bộ khung repo, đưa code GĐ1 vào | **Làm đầu tiên**, trước Tuần 1 |
| `AGENTS.md` | File bootstrap đặt ở gốc repo, agent tự đọc | Copy vào gốc repo |
| `CURRENT-WEEK.md` | Tuần đang làm, cập nhật đầu mỗi tuần | Copy vào `docs/` |

---

## Mục tiêu Giai đoạn 2 — phát biểu một câu

> Xây dựng một nền tảng chạy được, có khả năng: (A) so sánh có kiểm soát bốn biến thể RAG trên dữ liệu Nezha để xác định kiến trúc retrieval tối ưu cho bài toán AIOps, và (B) dùng biến thể tối ưu đó làm nền tảng cho một tác tử chẩn đoán nguyên nhân gốc rễ sinh báo cáo có cấu trúc.

Mọi dòng code trong 24 tuần tới phải phục vụ một trong hai mệnh đề A hoặc B. Nếu không, xem `06-scope-guard.md`.

---

## Kế thừa từ Giai đoạn 1

Những thứ đã có, **port sang chứ không viết lại**:

| Thành phần | Trạng thái GĐ1 | Ghi chú |
|---|---|---|
| Streaming replay + watermark | Đã hoạt động | Port nguyên vẹn |
| Isolation Forest detector | threshold 0.85 | Port nguyên vẹn |
| BM25 hybrid retrieval | top-6, latency ~11ms | Trở thành strategy `bm25_hybrid`, dùng làm baseline |
| LLM-as-a-Judge | 3 nhãn, `require_evidence_for_true_alert` | Port nguyên vẹn |
| Local-first LLM routing | llama3.2:3b + Gemini Flash Lite fallback | Port nguyên vẹn |
| LLM response cache | Đã có | **Bắt buộc giữ** — chạy lại thực nghiệm không được tốn tiền |
| Context Rescue | Heuristic cứng | GĐ2 thay bằng công thức Rescue Score có tham số (η1, η2, η3, τ) |

## Số liệu baseline GĐ1 — mốc so sánh bắt buộc

| Chỉ số | Giá trị GĐ1 | Nguồn |
|---|---|---|
| Precision (hybrid BM25 top-6, 300 windows) | 0.32 | Phase 4 |
| FPR (hybrid BM25 top-6) | 0.046 | Phase 4 |
| F1 (có Context Rescue) | 0.781 | Phase 5 |
| Recall (có Context Rescue) | 1.000 | Phase 5 |
| Context coverage | 0.47 | Phase 5 |
| Retrieval latency (BM25) | ~11 ms | Phase 4 |
| F1 khi không có RAG | 0.000 | Phase 3/4 |

Nếu pipeline GĐ2 không tái lập được các con số này ở Tuần 3, **dừng lại và sửa** trước khi làm tiếp. Đây là kiểm chứng tính đúng đắn của việc port code.

---

## Mục tiêu số liệu Giai đoạn 2

**Nhánh A — RAG variants**

| Chỉ số | Mục tiêu |
|---|---|
| F1 của biến thể tốt nhất | ≥ 0.78 |
| Context coverage | ≥ 0.47 |
| Retrieval latency Graph RAG | ≤ 3× baseline BM25 (≤ 33 ms) |
| Avg context tokens | Ghi nhận để phân tích cost/quality |
| Context precision | Chấm thủ công trên mẫu ≥ 50 window |

**Nhánh B — RCA Agent**

| Chỉ số | Mục tiêu |
|---|---|
| Hit@1 | ≥ 0.60 |
| Hit@3 | ≥ 0.80 |
| Alert Reduction Ratio | ≥ 30% trên cascade fault |
| JSON valid rate | ≥ 0.95 |
| E2E latency | Ghi nhận baseline, không so sánh với SOTA chạy cloud GPU |

---

## Ngăn xếp công nghệ chốt

| Lớp | Công nghệ | Ghi chú |
|---|---|---|
| Ngôn ngữ | Python 3.11+ | Toàn bộ backend |
| Service framework | FastAPI | Chỉ cho `api`, các service khác là process/worker |
| Validation | Pydantic v2 | Mọi schema |
| Message broker | Redpanda | Profile `full`; profile `dev` có thể chạy in-process queue |
| Analytics DB | ClickHouse | Alert, retrieval trace, per-window results |
| Metadata DB | PostgreSQL | Incident, diagnostic report, run registry |
| Graph | NetworkX | Service dependency graph, đủ cho quy mô Nezha |
| LLM local | Ollama + llama3.2:3b | Local-first |
| LLM API | Gemini Flash Lite | Fallback |
| Dashboard | React + Recharts, fallback Streamlit | Quyết định ở Tuần 18, xem `04` |
| Đóng gói | Docker Compose, profiles `dev` / `full` | Không Kubernetes trong GĐ2 |

---

## Thứ tự đọc cho AI coding agent

Khi bắt đầu một phiên code, nạp theo thứ tự:

```
06-scope-guard.md      (mục tiêu và ranh giới)
05-agent-coding-rules.md (quy tắc kỹ thuật)
01-architecture-design.md (kiến trúc)
03-schemas-and-contracts.md (hợp đồng dữ liệu)
04-implementation-roadmap.md (chỉ phần tuần hiện tại)
```

Không nạp toàn bộ roadmap — chỉ nạp tuần đang làm, để agent không tự nhảy sang task tương lai.
