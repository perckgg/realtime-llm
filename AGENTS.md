# AGENTS.md

> Đặt file này ở **gốc repo**. Claude Code, Codex và Cursor tự động đọc nó khi bắt đầu phiên làm việc.

---

## Dự án này là gì

Nền tảng nghiên cứu cho luận văn thạc sĩ: **AIOps RCA Platform**.

Mục tiêu duy nhất:

> **(A)** Đề xuất và chứng minh **CTAV** (Calibrated Topology-Aware Alert Validation): thẩm định cảnh báo có nhận biết topology, được hiệu chỉnh theo nguồn gốc bằng chứng, giữ mức tăng recall của topology mà không làm tăng báo động giả so với BM25 trong cùng ngân sách LLM; **(B)** dùng CTAV làm nền cho tác tử RCA định vị service gốc, sinh báo cáo có cấu trúc; cả hai chạy trên **một platform demo được** trước hội đồng.

Đây **không phải sản phẩm thương mại**. Đây là bằng chứng cho hai luận điểm khoa học (giả thuyết H0–H5) cộng platform hiện thực hoá chúng. Tối ưu cho khả năng tái lập thực nghiệm, không phải cho vận hành production.

---

## Đọc gì trước khi code

Bắt buộc, theo thứ tự (tất cả nằm trong `docs/Final_Thesis_Phase2/`):

1. `06-scope-guard.md` — mục tiêu và ranh giới. **Đọc trước tiên.**
2. `08-research-direction.md` — giải pháp CTAV, giả thuyết, cách chứng minh
3. `05-agent-coding-rules.md` — quy tắc kỹ thuật
4. `01-architecture-design.md` — kiến trúc, 4 Protocol lõi
5. `03-schemas-and-contracts.md` — mọi model và DDL
6. `04-implementation-roadmap.md` — **chỉ đọc phần mốc hiện tại**

Mốc hiện tại: xem `docs/CURRENT-MILESTONE.md`. Kế hoạch tổ chức theo **cột mốc** M0–M12 (QĐ-014), không theo tuần.

**Sau mỗi mốc** phải viết báo cáo `docs/milestones/M<n>-*.md` theo mẫu `docs/milestones/README.md`, đủ 4 phần: kết quả hiện tại · cần review gì · vấn đề cần người dùng giải quyết · plan cho mốc tiếp theo. Chưa có báo cáo thì chưa sang mốc sau.

---

## Năm quy tắc không được vi phạm

1. **Không hardcode tham số thí nghiệm.** Mọi tham số đến từ `eval/configs/*.yaml`.
2. **Không chạm `test` split trước mốc M8 (G-test)** và trước khi đăng ký giả thuyết ở M7. Tuning chỉ trên `val`, debug chỉ trên `dev`.
3. **Không ghi đè `eval/results/`.** Chạy lại với tham số khác = `run_id` mới.
4. **Mọi lời gọi LLM đi qua cache.** Key = `sha256(prompt + model + temperature + max_tokens + repeat)`, `repeat` mặc định 0 (QĐ-013). Judge duy nhất: `gemini-2.5-flash` qua API, temperature 0 (QĐ-021) — không local-first, không fallback sang model khác. `gemini-2.5-flash-lite` chỉ còn trong cache của bài báo (G-paper).
5. **Không thêm gì ngoài danh sách phạm vi** trong `docs/06-scope-guard.md` §3.

---

## Cấm tuyệt đối

Không tự ý thêm: Kubernetes · vector database · LangChain/AutoGen/CrewAI · MCTS · fine-tuning · authentication · multi-tenant · alert notification · runbook thực thi · retrieval strategy thứ 3 (`cross_modal`, RRF, reranker... đã cắt ở QĐ-011) · detector thứ hai.

Nếu nghĩ một trong số này là ý hay: ghi vào `docs/ideas.md` và tiếp tục làm theo đặc tả.

---

## Kiến trúc tóm tắt

```text
Replayer → Detector → CTAV ─────────────────────────────────────→ [RCA Agent] → ClickHouse/Postgres → API → Dashboard
           (IForest   tầng 1 BM25 → judge                          (grouping →
            +Rescue)  tầng 2 topology (C1) khi cần (C4) → judge     propagation →
                      policy: gating θ_topo>θ_local (C2) + anchoring (C3)   summary)
```

Bốn Protocol lõi ở `packages/schemas/protocols.py`: `SourceAdapter`, `Detector`, `RetrievalStrategy`, `Judge`.
**Không đổi signature của chúng** mà không cập nhật `docs/Final_Thesis_Phase2/01-architecture-design.md` trong cùng commit.

Hai retrieval strategy: `bm25_hybrid` (baseline) · `hybrid_bm25_graph` (C1, Fusion Score α, β, γ của paper).
Temporal-only / graph-only là ablation của C1, không phải module riêng.
Tham số riêng nằm trong `__init__`, không thêm vào signature của `retrieve()`.
C2/C3 ở `services/judge/policy.py`, C4 ở `services/judge/routing.py`.

---

## Lệnh thường dùng

```bash
# Môi trường
docker compose --profile dev up -d
docker compose --profile full up -d

# Thực nghiệm (máy này dùng `py`, không có `python` trên PATH)
py -m eval run --config eval/configs/<name>.yaml
py -m eval compare --runs bm25_baseline,topology_c1,ctav_final
py -m eval ablation --config eval/configs/rescue_ablation.yaml

# Kiểm tra
py -m pytest
py -m mypy packages services
py -m ruff check .
```

---

## Hai loại baseline — mốc kiểm chứng

**Kiểm tra port (G-port, M2)** — GĐ1 Phase 4, **judge mock**, `paper_300`, threshold 0.95, gate 0.80/0.98, ngân sách 30:
Precision 0.3158 (6 TP / 13 FP), Recall 0.375, FPR 0.0458, latency BM25 ~11 ms.
Config: `eval/configs/gd1_phase4_parity.yaml`. Lệch quá 1 cửa sổ mỗi ô ma trận nhầm lẫn = port sai — dừng và sửa.

**Baseline khoa học (G-paper, M3)** — paper ICAETM 2026, gemini-2.5-flash-lite, `paper_500`, full budget:
BM25 F1 0.703 / FP 7; Topology F1 0.476 / FP 137. Phải tái lập từ cache, cache hit 100%.

Không dùng số mock (kể cả "F1 không RAG = 0.000", "F1 có Rescue = 0.781") làm kết luận khoa học.

---

## Khi viết luận văn

Mọi văn bản đi vào luận văn (sườn, outline, nháp chương, LaTeX) theo `docs/drafts/style-guide-luan-van.md`:
một đề tài thống nhất (không "giai đoạn"/"kế thừa"), bài báo ICAETM chỉ là trích dẫn, kết quả âm viết thẳng,
không "tốt hơn" khi CI chứa 0, chỗ thiếu số ghi `[CHỜ M*]`.

---

## Khi không chắc chắn

Dừng và hỏi người dùng. Các tình huống bắt buộc phải hỏi:

- Tham số không có trong config và không có mặc định rõ ràng
- Task có vẻ vượt ra ngoài mốc hiện tại
- Cần thêm thư viện mới
- Cần đổi signature của Protocol lõi
- Kết quả thực nghiệm khác xa baseline GĐ1
- Cần chạy trên `test` split

Không đoán. Không tự "cải thiện" thuật toán. Không refactor lớn khi chưa được yêu cầu.

---

## Definition of Done cho một task

- [ ] Chạy được, có type hint
- [ ] Có unit test nếu thuộc nhóm tính toán (Rescue Score, RRF, fusion, BFS, grouping, metrics)
- [ ] Không hardcode tham số thí nghiệm
- [ ] Log có cấu trúc, không lộ secret
- [ ] Tài liệu liên quan đã cập nhật
- [ ] `docs/experiment-log.md` đã cập nhật nếu có chạy thực nghiệm
- [ ] Nếu là việc cuối của mốc: báo cáo `docs/milestones/M<n>-*.md` đã viết đủ 4 phần
