# AIOps RCA Platform — Giai đoạn 2

> Xây dựng một nền tảng chạy được, có khả năng: **(A)** so sánh có kiểm soát bốn biến
> thể RAG trên dữ liệu Nezha để xác định kiến trúc retrieval tối ưu cho bài toán AIOps,
> và **(B)** dùng biến thể tối ưu đó làm nền tảng cho một tác tử chẩn đoán nguyên nhân
> gốc rễ sinh báo cáo có cấu trúc.

Đây là repo nghiên cứu cho luận văn thạc sĩ, không phải sản phẩm thương mại. Chi tiết
đầy đủ: xem [`AGENTS.md`](AGENTS.md) và bộ tài liệu ở
[`docs/Final_Thesis_Phase2/00-INDEX.md`](docs/Final_Thesis_Phase2/00-INDEX.md).

## Trạng thái hiện tại

Đang ở **Tuần 1/24** (xem [`docs/CURRENT-WEEK.md`](docs/CURRENT-WEEK.md)). Cấu trúc thư
mục đã dựng xong theo `docs/Final_Thesis_Phase2/01-architecture-design.md` §7, nhưng
**chưa có code pipeline** — mọi thư mục trong `services/`, `packages/`, `eval/` hiện chỉ
là khung rỗng có README ghi rõ việc sẽ làm ở tuần nào.

```text
services/     replayer, detector, retrieval, judge, rca_agent, api, web
packages/     schemas, graph, llm, storage
eval/         harness, configs, results
infra/        clickhouse/, postgres/ (docker-compose.yml dev/full)
data/         nezha (raw, gitignored), splits (committed), llm_cache (gitignored)
legacy/       toàn bộ code + kết quả Giai đoạn 1 (Internship 1), nguyên trạng
archive/      phase1_extra — dataset/setup phụ của GĐ1, ngoài phạm vi GĐ2
```

## Kế thừa từ Giai đoạn 1

Code GĐ1 đầy đủ nằm trong [`legacy/`](legacy/README.md) — **port, không viết lại**:
streaming replay, Isolation Forest detector, BM25 hybrid retrieval, LLM-as-a-Judge,
local-first routing, LLM response cache. Context Rescue sẽ được viết lại thành công
thức có tham số (α, β, γ, τ). Xem `legacy/README.md` để chạy lại code GĐ1 (yêu cầu chạy
với `legacy/` làm working directory).

## Bắt đầu

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"
```

Tái lập kết quả Tuần 1:

```bash
bash scripts/download_nezha.sh          # nếu chưa có data/Nezha/
python scripts/verify_labels.py         # -> docs/label-audit.md  (~80 s)
python scripts/make_splits.py           # -> data/splits/*.json
python scripts/make_splits.py --check   # xác nhận split không đổi
python -m pytest tests/ -q              # 8 test canh split
```

Việc tiếp theo là Tuần 2 — xem `docs/Final_Thesis_Phase2/04-implementation-roadmap.md`.
