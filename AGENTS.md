# AGENTS.md

> Đặt file này ở **gốc repo**. Claude Code, Codex và Cursor tự động đọc nó khi bắt đầu phiên làm việc.

---

## Dự án này là gì

Nền tảng nghiên cứu cho luận văn thạc sĩ: **AIOps RCA Platform**.

Mục tiêu duy nhất:

> **(A)** So sánh có kiểm soát bốn biến thể RAG trên dữ liệu Nezha để xác định kiến trúc retrieval tối ưu cho bài toán giám sát microservices, và **(B)** dùng biến thể tối ưu đó làm nền tảng cho một tác tử chẩn đoán nguyên nhân gốc rễ sinh báo cáo có cấu trúc.

Đây **không phải sản phẩm thương mại**. Đây là bằng chứng cho hai luận điểm khoa học. Tối ưu cho khả năng tái lập thực nghiệm, không phải cho vận hành production.

---

## Đọc gì trước khi code

Bắt buộc, theo thứ tự:

1. `docs/06-scope-guard.md` — mục tiêu và ranh giới. **Đọc trước tiên.**
2. `docs/05-agent-coding-rules.md` — quy tắc kỹ thuật
3. `docs/01-architecture-design.md` — kiến trúc, 4 Protocol lõi
4. `docs/03-schemas-and-contracts.md` — mọi model và DDL
5. `docs/04-implementation-roadmap.md` — **chỉ đọc phần tuần hiện tại**

Tuần hiện tại: xem `docs/CURRENT-WEEK.md`.

---

## Năm quy tắc không được vi phạm

1. **Không hardcode tham số thí nghiệm.** Mọi tham số đến từ `eval/configs/*.yaml`.
2. **Không chạm `test` split trước Tuần 11.** Tuning chỉ trên `val`, debug chỉ trên `dev`.
3. **Không ghi đè `eval/results/`.** Chạy lại với tham số khác = `run_id` mới.
4. **Mọi lời gọi LLM đi qua cache.** Key = `sha256(prompt + model + temperature + max_tokens)`.
5. **Không thêm gì ngoài danh sách phạm vi** trong `docs/06-scope-guard.md` §3.

---

## Cấm tuyệt đối

Không tự ý thêm: Kubernetes · vector database · LangChain/AutoGen/CrewAI · MCTS · fine-tuning · authentication · multi-tenant · alert notification · runbook thực thi · biến thể RAG thứ 6 · detector thứ hai.

Nếu nghĩ một trong số này là ý hay: ghi vào `docs/ideas.md` và tiếp tục làm theo đặc tả.

---

## Kiến trúc tóm tắt

```text
Replayer → Detector → Retrieval → Judge → [RCA Agent] → ClickHouse/Postgres → API → Dashboard
           (IForest)  (5 chiến    (LLM     (grouping →
                       lược)       local-   propagation →
                                   first)   summary)
```

Bốn Protocol lõi ở `packages/schemas/protocols.py`: `SourceAdapter`, `Detector`, `RetrievalStrategy`, `Judge`.
**Không đổi signature của chúng** mà không cập nhật `docs/01-architecture-design.md` trong cùng commit.

Năm retrieval strategy: `bm25_hybrid` (baseline GĐ1) · `temporal` · `cross_modal` · `graph` · `hybrid_bm25_graph`.
Tham số riêng nằm trong `__init__`, không thêm vào signature của `retrieve()`.

---

## Lệnh thường dùng

```bash
# Môi trường
docker compose --profile dev up -d
docker compose --profile full up -d

# Thực nghiệm
python -m eval run --config eval/configs/<name>.yaml
python -m eval compare --runs bm25_baseline,temporal,graph
python -m eval ablation --config eval/configs/rescue_ablation.yaml

# Kiểm tra
pytest
mypy packages services
ruff check .
```

---

## Số liệu baseline Giai đoạn 1 — mốc kiểm chứng

| Chỉ số | Giá trị |
|---|---|
| Precision (BM25 hybrid top-6, 300 window) | 0.32 |
| FPR | 0.046 |
| F1 có Context Rescue | 0.781 |
| Recall có Context Rescue | 1.000 |
| Context coverage | 0.47 |
| Retrieval latency BM25 | ~11 ms |

Pipeline mới phải tái lập được các con số này ở Tuần 3. Lệch nhiều nghĩa là port sai — dừng và sửa.

---

## Khi không chắc chắn

Dừng và hỏi người dùng. Các tình huống bắt buộc phải hỏi:

- Tham số không có trong config và không có mặc định rõ ràng
- Task có vẻ vượt ra ngoài tuần hiện tại
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
