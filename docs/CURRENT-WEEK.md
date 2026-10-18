# Tuần hiện tại

> Cập nhật file này vào đầu mỗi tuần. Agent đọc file này để biết được phép làm gì.
> Chỉ chép phần tuần hiện tại từ `docs/Final_Thesis_Phase2/04-implementation-roadmap.md` vào đây.

---

## Tuần: 8 / 24 (Chặng 1 — Tái lập)
## Ngày bắt đầu: 2026-10-19
## Trạng thái: chưa bắt đầu

**Bối cảnh (QĐ-011, QĐ-012, 2026-10-18).** Kế hoạch đã đổi: GĐ2 đề xuất giải pháp
**CTAV** và chứng minh nó, vẫn giữ platform để demo — đọc
`docs/Final_Thesis_Phase2/08-research-direction.md` trước khi làm. Tuần 3–7 không có
tiến độ; tuần này làm phần việc của Tuần 3 cũ, cộng các điểm sửa từ review.

---

## Mục tiêu tuần này

Sửa detector, chốt hợp đồng dữ liệu cho retrieval/judge, port BM25 và judge — để Tuần 9
chạy được cổng chặn G-port.

---

## Quyết định phải chốt đầu tuần (`08` §9)

- [x] Q1 — Judge chính: `gemini-2.5-flash-lite` qua API, không local, không fallback (QĐ-013, lý do ở `08` §4.1)
- [ ] Q2 — Đánh giá trên toàn `val`/`test` hay thêm tập cố định. Mặc định: toàn split, ngân sách gọi LLM giới hạn + cache
- [x] Q3 — D1: điền metric thiếu bằng **giá trị gần nhất của cùng pod + cột chỉ báo thiếu** (người dùng chọn 2026-10-18; ghi QĐ-014 khi cài xong)
- [x] Q4 — D2: **có** — replayer phát lịch sử liên tục để cập nhật buffer, split chỉ lọc cửa sổ được chấm và ghi kết quả (người dùng chọn 2026-10-18; ghi QĐ-014 khi cài xong)
- [ ] Q5 — Mốc bảo vệ Tuần 24 (tuần 2027-02-08) cố định? Lưu ý Tết ~2027-02-06

---

## Task được phép làm

- [ ] D1–D6 (`08` §8.1): metric thiếu, lịch sử buffer liên tục, `score()` không trạng thái ẩn, mypy/ruff sạch, chặn `run_id` trùng, việc nhỏ
- [ ] `packages/schemas/protocols.py` — 4 Protocol theo `01` §5
- [ ] `packages/schemas/models.py` — `ContextEvent` (có `origin`, `graph_distance`), `RetrievalBudget`, `RetrievalResult`, `JudgedAlert` (có trường CTAV) theo `03` §1.3–1.4
- [ ] `packages/schemas/evidence.py` — loader log/trace Nezha → kho bằng chứng
- [ ] `services/retrieval/bm25_hybrid.py` — port GĐ1, bỏ tag fault type khỏi truy vấn
- [ ] `services/judge/` — port prompt, 3 nhãn, `require_evidence`, cache (key có `repeat`), client `gemini-2.5-flash-lite` (ghi model id trả về, retry có trần → `manual_review`), backend `mock`
- [ ] `services/retrieval/registry.py`
- [ ] Dọn repo: commit/bỏ 4 file `legacy/` đang sửa; ignore `legacy/outputs/test_results/*_cache_*.jsonl`; dời `front_matter.txt`, `refs_sample.txt`, `toc_out.txt` khỏi gốc repo

**Không làm tuần này:** harness, ánh xạ `paper_300` (Tuần 9); graph, C1 (Tuần 10); C2–C4 (Tuần 13–14).

---

## Definition of Done

- [ ] `py -m pytest tests/ -q`, `py -m mypy packages services`, `py -m ruff check .` đều sạch
- [ ] Một candidate dev đi hết BM25 → judge (mock và LLM thật) → `JudgedAlert` có `debug` đầy đủ
- [ ] Unit test: cache key, không rò tag fault type, `require_evidence`
- [ ] QĐ-014 (D1/D2 đã cài, có số đo trước/sau) ghi vào `docs/experiment-log.md`; Q2, Q5 chốt trước Tuần 9

---

## Tuần sau (Tuần 9) — chưa được bắt đầu

Eval harness (runner, metrics, bootstrap CI + McNemar) và **cổng chặn G-port**: tái lập GĐ1
Phase 4 trên `paper_300` theo từng tầng với judge mock (QĐ-012).

---

## Lệnh tái lập Tuần 1–2

```bash
bash scripts/download_nezha.sh          # nếu chưa có data/Nezha/
py scripts/verify_labels.py             # -> docs/label-audit.md (~80 s)
py scripts/make_splits.py --check       # xác nhận split không đổi
docker compose --profile dev up -d      # clickhouse + postgres
py -m pytest tests/ -q                  # 32 test
py scripts/replay_smoke.py --windows 50 # fit + replay + ghi ClickHouse
```

Lịch sử Tuần 1–2 (cổng chặn, ghi chú QĐ-002, QĐ-006, QĐ-007, QĐ-009, QĐ-010): xem
`docs/experiment-log.md` và `git log`.
