# 05 — Agent Coding Rules

Bộ quy tắc kỹ thuật bắt buộc cho AI coding agent (Claude Code, Codex, Cursor) khi làm việc trên repo này.

Về ranh giới phạm vi và mục tiêu đề tài, xem `06-scope-guard.md`. File này chỉ nói về **cách viết code**.

---

## Nhóm A — Quy tắc nghiên cứu (quan trọng nhất)

Vi phạm nhóm này làm hỏng tính hợp lệ của luận văn, nghiêm trọng hơn bug.

### R-A1 — Mọi thực nghiệm xuất phát từ file config

Không hardcode tham số thí nghiệm trong code.

```python
# SAI
HOP = 2
DECAY = 0.6

# ĐÚNG
def __init__(self, hop: int, decay_factor: float):
    self.hop = hop
    self.decay_factor = decay_factor
# giá trị đến từ eval/configs/*.yaml
```

Mỗi run có `run_id` và `seed` trong config. Không có config thì không phải thực nghiệm, chỉ là thử nghiệm cá nhân — và kết quả không được đưa vào luận văn.

### R-A2 — Không chạm test split trước Tuần 11

Tuning tham số chỉ trên `val`. Debug chỉ trên `dev`.

Nếu agent thấy `split: test` trong config trước Tuần 11, phải dừng và hỏi lại.

### R-A3 — Kết quả không bao giờ bị ghi đè

`eval/results/<run_id>/` là bất biến. Chạy lại với tham số khác → `run_id` mới.

Không có lệnh nào trong repo được phép `rm -rf eval/results/`.

### R-A4 — Mọi run ghi lại commit hash

`git_commit.txt` trong thư mục kết quả. Nếu working tree có thay đổi chưa commit, ghi thêm `-dirty` và cảnh báo.

### R-A5 — LLM response phải qua cache

Cache key = `sha256(prompt + model + temperature + max_tokens)`.

Chạy lại một thực nghiệm đã chạy không được tốn thêm tiền API. Nếu agent viết code gọi LLM mà bỏ qua cache, đó là bug.

### R-A6 — Số liệu trong luận văn sinh từ `eval/results/`

Không tính tay, không copy số từ log ra Word. Bảng và hình sinh bằng script.

### R-A7 — Tính deterministic

Cùng `seed` + cùng `split` + cùng config → cùng kết quả (trừ phần LLM không deterministic, đã được cache khắc phục).

`window_id` sinh từ `hash(service + start_ts)`, không dùng UUID ngẫu nhiên.

---

## Nhóm B — Kiến trúc

### R-B1 — Không đổi signature của 4 Protocol lõi

`SourceAdapter`, `Detector`, `RetrievalStrategy`, `Judge` — định nghĩa ở `01` §5.

Tham số riêng của từng implementation nằm trong `__init__`, không thêm vào method signature. Nếu thật sự cần đổi, phải cập nhật `01-architecture-design.md` trong cùng commit.

### R-B2 — Không định nghĩa lại schema

Mọi model import từ `packages/schemas/`. Không service nào có bản sao riêng.

```python
# SAI: trong services/judge/models.py
class AlertCandidate(BaseModel): ...

# ĐÚNG
from packages.schemas import AlertCandidate
```

### R-B3 — Không query DB trong vòng lặp xử lý window

Service graph, metadata, cấu hình → nạp vào memory một lần khi khởi động.

```python
# SAI
for window in stream:
    graph = load_graph_from_clickhouse()   # mỗi window một query
    
# ĐÚNG
graph = load_graph_from_clickhouse()       # một lần
for window in stream:
    ...
```

### R-B4 — RCA Agent không nằm trên critical path

Judge trả verdict xong là xong. RCA chạy sau, theo lô, có thể tắt bằng `rca.enabled: false`.

### R-B5 — Business logic không nằm trong FastAPI route

`services/api` chỉ đọc DB và trả JSON. Mọi tính toán ở tầng service.

### R-B6 — File không quá 400 dòng

Quá thì tách module. Đặc biệt `retrieval/` — mỗi strategy một file.

---

## Nhóm C — Độ tin cậy

### R-C1 — Mọi external call có timeout

LLM, ClickHouse, Postgres, Ollama. Không có call nào được treo vô hạn.

```python
# retrieval phải tôn trọng budget.timeout_ms
# quá hạn → trả kết quả một phần với truncated=True, không raise
```

### R-C2 — Retry có giới hạn

Tối đa 2 lần, exponential backoff. Không retry vô hạn. Không retry lỗi 4xx.

### R-C3 — Không nuốt lỗi im lặng

```python
# SAI
try:
    result = judge.evaluate(...)
except Exception:
    pass

# ĐÚNG
try:
    result = judge.evaluate(...)
except Exception as e:
    logger.error("judge failed", window_id=w.window_id, error=str(e))
    write_to_dlq(window_id=w.window_id, stage="judge", error=str(e))
    result = None
```

Window/incident lỗi phải đi vào DLQ (`diagnostic_rejected` cho Nhánh B, log có cấu trúc cho Nhánh A). Cần đếm được bao nhiêu window bị lỗi trong mỗi run.

### R-C4 — Validate trước khi ghi DB

Pydantic model là cổng kiểm soát. Không ghi dict thô vào ClickHouse.

### R-C5 — Consumer idempotent

Dedup theo `(run_id, window_id)`. Chạy lại một run không được tạo bản ghi trùng.

---

## Nhóm D — Chất lượng code

### R-D1 — Type hint đầy đủ

Mọi hàm public có type hint. Chạy `mypy` ở mức cơ bản.

### R-D2 — Structured logging

```python
logger.info("retrieval_done",
            run_id=run_id, window_id=w.window_id,
            strategy=s.name, latency_ms=r.latency_ms,
            event_count=len(r.events))
```

Không dùng `print()`. Không nội suy chuỗi trong log message.

### R-D3 — Không log secret

API key của Gemini không xuất hiện trong log, trong output, trong commit.

### R-D4 — `.env.example` luôn cập nhật

Thêm biến môi trường mới → cập nhật `.env.example` trong cùng commit.

### R-D5 — Error message có ngữ cảnh

`ValueError("invalid config")` là vô dụng. `ValueError(f"retrieval.type='{t}' not in registry: {list(REGISTRY)}")` là hữu ích.

---

## Nhóm E — Kiểm thử

### R-E1 — Bắt buộc có unit test cho

- Tính Rescue Score (từng thành phần và tổng)
- RRF merge trong `hybrid_bm25_graph`
- Weighted fusion trong `cross_modal`
- Ánh xạ anomaly score → window size trong `temporal`
- BFS + decay trong `graph`
- Alert grouping (thời gian + liên thông đồ thị)
- Validation của `DiagnosticReport`
- Tính P/R/F1/FPR trong `eval/harness/metrics.py`

Nhóm cuối đặc biệt quan trọng: **nếu hàm tính metric sai, toàn bộ luận văn sai**. Test bằng ví dụ tính tay.

### R-E2 — Test không gọi LLM thật

Dùng `FakeJudge` trả verdict cố định. Test pipeline không được tốn tiền API.

### R-E3 — Test DLQ

Đưa vào một window hỏng, khẳng định nó xuất hiện trong DLQ và không làm sập pipeline.

### R-E4 — Smoke test end-to-end

Một test chạy 10 window qua toàn bộ pipeline với `FakeJudge`, khẳng định có output ở cả ClickHouse và Postgres.

---

## Nhóm F — Tài liệu

### R-F1 — Thêm strategy mới → cập nhật 3 chỗ

1. `retrieval/registry.py`
2. `01-architecture-design.md` §6.3
3. `03-schemas-and-contracts.md` §1.3 (bảng trường `debug`)

### R-F2 — Đổi schema → cập nhật `03` cùng commit

### R-F3 — Mỗi service có README ngắn

Ba phần: service này làm gì, chạy thế nào, input/output là gì.

### R-F4 — Ghi experiment log

Mỗi lần chạy thực nghiệm → thêm một dòng vào `docs/experiment-log.md`. Kể cả lần chạy thất bại.

---

## Nhóm G — Khi không chắc chắn

### R-G1 — Dừng và hỏi, không đoán

Các tình huống phải hỏi người dùng:

- Tham số không có trong config và không có giá trị mặc định rõ ràng
- Task hiện tại có vẻ vượt ra ngoài tuần đang làm trong roadmap
- Cần thêm thư viện mới
- Cần đổi signature của Protocol lõi
- Kết quả thực nghiệm khác xa baseline GĐ1
- Cần chạy trên `test` split

### R-G2 — Không tự ý "cải thiện" thuật toán

Nếu agent nghĩ có cách retrieve tốt hơn, ghi ý tưởng vào `docs/ideas.md` và tiếp tục làm theo đúng đặc tả. Thêm kỹ thuật ngoài kế hoạch làm hỏng tính so sánh được của thực nghiệm.

### R-G3 — Không refactor lớn khi chưa được yêu cầu

Đặc biệt sau Tuần 3 — code đã tái lập được baseline là code đã được kiểm chứng. Refactor có thể làm số liệu đổi mà không ai biết.

---

## Definition of Done cho một task

Một task chỉ xong khi:

- [ ] Code chạy được, không lỗi
- [ ] Có type hint
- [ ] Có unit test nếu thuộc R-E1
- [ ] Không hardcode tham số thí nghiệm
- [ ] Log có cấu trúc, không có secret
- [ ] Tài liệu liên quan đã cập nhật (R-F1, R-F2)
- [ ] `docs/experiment-log.md` đã cập nhật nếu có chạy thực nghiệm
- [ ] Đối chiếu với DoD của tuần trong `04-implementation-roadmap.md`

---

## Các lỗi agent phải tránh

| Lỗi | Vì sao nghiêm trọng |
|---|---|
| Hardcode `hop=2` trong `graph.py` | Không chạy được ablation |
| Gọi LLM không qua cache | Tốn tiền, ablation không khả thi |
| Ghi đè `eval/results/` | Mất bằng chứng tái lập |
| Tự thêm vector database | Ngoài phạm vi, thành biến thể RAG thứ 6 |
| Sửa hàm tính F1 cho "hợp lý hơn" | Số liệu cũ và mới không so sánh được |
| Refactor `bm25_hybrid.py` sau Tuần 3 | Baseline không còn đáng tin |
| Tính Recall chỉ trên candidate | Thổi phồng số liệu, xem `02` §4.1 |
| Dùng `test` split để tune | Hỏng tính hợp lệ của luận văn |
| Thêm LangChain/AutoGen | Ngoài phạm vi, xem `06` |
| Sinh câu lệnh shell trong `suggested_actions` | Vượt phạm vi GĐ2 đã tuyên bố với GVHD |
