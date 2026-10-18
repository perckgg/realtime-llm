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
| `08-research-direction.md` | **Giải pháp CTAV**: vấn đề từ paper, GĐ1 → GĐ2, thành phần C1–C5, giả thuyết H0–H5 và cách chứng minh, platform demo, đầu ra cuối cùng | Đầu mỗi chặng; khi viết luận văn |
| `AGENTS.md` | File bootstrap đặt ở gốc repo, agent tự đọc | Copy vào gốc repo |
| `CURRENT-WEEK.md` | Tuần đang làm, cập nhật đầu mỗi tuần | Copy vào `docs/` |

---

## Mục tiêu Giai đoạn 2 — phát biểu một câu

> Đề xuất và chứng minh **CTAV** (Calibrated Topology-Aware Alert Validation), một phương pháp thẩm định cảnh báo có nhận biết topology, được hiệu chỉnh theo nguồn gốc bằng chứng: giữ mức tăng recall của topology mà không làm tăng báo động giả so với BM25 trong cùng ngân sách LLM **(A)**; dùng CTAV làm nền cho tác tử RCA định vị service gốc **(B)**; hiện thực hoá cả hai trên một platform chạy được để demo trước hội đồng.

Mọi dòng code phải phục vụ A, B, hoặc platform demo của chúng. Nếu không, xem `06-scope-guard.md`.

**Mạch luận văn:** GĐ1 (thực nghiệm khả thi) → paper ICAETM 2026 (phát hiện vấn đề: topology tăng recall nhưng gây thiên lệch xác nhận, FP 7 → 137) → GĐ2 (giải pháp CTAV + chứng minh H0–H5 + platform). Chi tiết giải pháp, giả thuyết, cách chứng minh: **`08-research-direction.md`** (QĐ-011, 2026-10-18).

---

## Kế thừa từ Giai đoạn 1

Những thứ đã có, **port sang chứ không viết lại**:

| Thành phần | Trạng thái GĐ1 | Ghi chú |
|---|---|---|
| Streaming replay + watermark | Đã hoạt động | Port nguyên vẹn |
| Isolation Forest detector | threshold 0.85 | Port nguyên vẹn |
| BM25 hybrid retrieval | top-6, latency ~11ms | Trở thành strategy `bm25_hybrid`, dùng làm baseline |
| Topology fusion (paper) | `legacy/src/phase2/retrieval/` | Trở thành `hybrid_bm25_graph` = C1 của CTAV |
| LLM-as-a-Judge | 3 nhãn, `require_evidence_for_true_alert` | Port nguyên vẹn |
| Local-first LLM routing | qwen2.5:1.5b / llama3.2:3b + Gemini fallback | **Không dùng trong GĐ2** (QĐ-013): judge cố định là `gemini-2.5-flash-lite` qua API — lý do ở `08` §4.1 |
| LLM response cache | Đã có | **Bắt buộc giữ** — chạy lại thực nghiệm không được tốn tiền |
| Context Rescue | Heuristic cứng | GĐ2 thay bằng công thức Rescue Score có tham số (η1, η2, η3, τ) |

## Số liệu baseline — hai loại, dùng cho hai việc khác nhau

**(1) Mốc kiểm tra port — GĐ1 Phase 4/5, judge giả (`provider: mock`).** Chỉ dùng để
kiểm tra code GĐ2 port đúng (cổng chặn G-port, Tuần 9). **Không** dùng làm số liệu khoa
học: judge mock không phải LLM.

| Chỉ số | Giá trị GĐ1 | Nguồn |
|---|---|---|
| Precision (hybrid BM25 top-6, `paper_300`) | 0.3158 (6 TP / 13 FP) | Phase 4, mock |
| Recall / FPR (hybrid BM25 top-6) | 0.375 / 0.0458 | Phase 4, mock |
| F1 khi không có RAG | 0.000 | Phase 4, mock |
| F1 / Recall (có Context Rescue) | 0.781 / 1.000 | Phase 5, mock |
| Retrieval latency (BM25) | ~11 ms | Phase 4 |

Cấu hình GĐ1 Phase 4: threshold 0.95, fit 1.000 cửa sổ đầu, gate 0.80/0.98, ngân sách 30
lần gọi (`legacy/nezha_setup/config/experiment_phase4_benchmark.yaml`).

**(2) Baseline khoa học — paper ICAETM 2026, gemini-2.5-flash-lite thật, `paper_500`.**
Dùng cho cổng chặn G-paper (Tuần 10) và là điểm xuất phát của H0.

| Chỉ số (full budget, top-6) | BM25 | Topology (C1) |
|---|---|---|
| Precision / Recall | 0.892 / 0.58 | 0.351 / 0.74 |
| F1 | 0.703 | 0.476 |
| FPR (FP / 400 normal) | 0.0175 (7) | 0.3425 (137) |
| Context coverage | 0.225 | 1.000 |
| F1 @ 120 lần gọi | 0.508 | 0.514 (LLM-không-RAG: 0.566) |

Lưu ý: "F1 không RAG = 0.000" của GĐ1 (mock) mâu thuẫn với 0.566 của paper (LLM thật).
Luận văn phải nói rõ điều này.

---

## Mục tiêu số liệu Giai đoạn 2

**Nhánh A — CTAV** (định nghĩa đầy đủ ở `08` §5; ngưỡng định lượng chốt khi đăng ký giả thuyết, Tuần 15)

| Chỉ số | Mục tiêu |
|---|---|
| F1(CTAV) − F1(BM25) trên `test` | > 0, CI 95% không chứa 0, McNemar p < 0.05 (H2) |
| Recall CTAV | ≥ Recall C1 − δ (giữ phần lớn mức tăng của topology) |
| FPR CTAV | không tệ hơn BM25 có ý nghĩa thống kê |
| Ablation C2 / C3 / C4 | mỗi thành phần có Δ có ý nghĩa ở chỉ số nó nhắm tới (H3) |
| F1 @ ngân sách giới hạn | ≥ LLM-không-RAG (H4) |
| Retrieval latency C1 | ≤ 3× BM25 |
| Context precision | Chấm thủ công trên mẫu ≥ 50 window |

Chỉ tiêu cũ "F1 ≥ 0.78" bị bỏ: nó lấy từ GĐ1 Phase 5 đo bằng judge mock.

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
| LLM | `gemini-2.5-flash-lite` qua API, temperature 0 | Judge duy nhất, cố định cho mọi thực nghiệm; cache bắt buộc (QĐ-013) |
| LLM local | ~~Ollama~~ | Không dùng trong GĐ2 (phần cứng + lý do phương pháp, `08` §4.1) |
| Dashboard | React + Recharts, fallback Streamlit | Quyết định ở Tuần 18, xem `04` |
| Đóng gói | Docker Compose, profiles `dev` / `full` | Không Kubernetes trong GĐ2 |

---

## Thứ tự đọc cho AI coding agent

Khi bắt đầu một phiên code, nạp theo thứ tự:

```
08-research-direction.md (giải pháp CTAV, giả thuyết — đọc khi bắt đầu chặng mới)
06-scope-guard.md      (mục tiêu và ranh giới)
05-agent-coding-rules.md (quy tắc kỹ thuật)
01-architecture-design.md (kiến trúc)
03-schemas-and-contracts.md (hợp đồng dữ liệu)
04-implementation-roadmap.md (chỉ phần tuần hiện tại)
```

Không nạp toàn bộ roadmap — chỉ nạp tuần đang làm, để agent không tự nhảy sang task tương lai.
