# Mốc hiện tại

> Cập nhật file này khi bắt đầu một mốc mới. Agent đọc file này để biết được phép làm gì.
> Chỉ chép phần mốc hiện tại từ `docs/Final_Thesis_Phase2/04-implementation-roadmap.md`.
> Đóng mốc = DoD đạt + báo cáo `docs/milestones/M<n>-*.md` (4 phần) + người dùng đã xem (`04` §2).

---

## Mốc: M1 — Sửa detector, hợp đồng dữ liệu, port BM25 + judge
## Bắt đầu: 2026-10-19 · Hạn mục tiêu: 2026-10-25
## Mốc trước: M0 — QUA, báo cáo `docs/milestones/M0-nen-tang.md`

**Bối cảnh.** Kế hoạch đã đổi sang giải pháp **CTAV** + chứng minh, giữ platform demo
(QĐ-011..014) — đọc `docs/Final_Thesis_Phase2/08-research-direction.md` trước khi làm.
M1 là phần việc "Tuần 3" của bản gốc, cộng các điểm sửa từ review.

---

## Quyết định đã chốt cho mốc này

- [x] Q1 — Judge: `gemini-2.5-flash-lite` qua API, không local, không fallback (QĐ-013, `08` §4.1)
- [x] Q3 — Metric thiếu: **giá trị gần nhất của cùng pod + cột chỉ báo thiếu**
- [x] Q4 — **Có** cho detector thấy lịch sử liên tục: replayer phát mọi cửa sổ theo thời gian để cập nhật buffer, split chỉ lọc cửa sổ được chấm và ghi kết quả

Còn mở (không chặn M1): Q2 (chốt ở M2), Q5 (mốc bảo vệ) — xem `docs/milestones/M0-nen-tang.md` §3.

---

## Việc được phép làm (theo thứ tự)

1. - [x] **Xong 2026-10-19 (QĐ-015)** — Sửa detector (`docs/milestones/M0-nen-tang.md` §2, R1–R5 + D6): metric thiếu, lịch sử liên tục, `score()` không trạng thái ẩn, mypy/ruff sạch, chặn `run_id` trùng, việc nhỏ. Đo trước/sau trên dev → QĐ-015
2. - [ ] `packages/schemas/protocols.py` — 4 Protocol theo `01` §5; `models.py` — `ContextEvent` (có `origin`, `graph_distance`), `RetrievalBudget`, `RetrievalResult`, `JudgedAlert` (có trường CTAV) theo `03` §1.3–1.4
3. - [ ] `packages/schemas/evidence.py` — loader log/trace Nezha → kho bằng chứng, lọc theo cửa sổ thời gian
4. - [ ] `services/retrieval/bm25_hybrid.py` — port GĐ1, bỏ tag fault type khỏi truy vấn
5. - [ ] `services/judge/` — prompt **nguyên văn** GĐ1, 3 nhãn, `require_evidence`, cache (key có `repeat`), client `gemini-2.5-flash-lite` (ghi model id, retry có trần → `manual_review`), backend `mock`; `services/retrieval/registry.py`

**Không làm ở mốc này:** harness, ánh xạ `paper_300` (M2); graph, C1 (M3); C2–C4 (M6).

---

## Definition of Done

- [ ] `py -m pytest tests/ -q`, `py -m mypy packages services`, `py -m ruff check .` đều sạch
- [ ] Một candidate dev đi hết BM25 → judge (mock và Gemini thật) → `JudgedAlert` có `debug` đầy đủ
- [ ] Unit test: cache key, không rò tag fault type, `require_evidence`, điền metric thiếu, lịch sử buffer liên tục
- [x] QĐ-015 ghi kết quả D1/D2 (số đo trước/sau) trong `docs/experiment-log.md`
- [ ] Báo cáo `docs/milestones/M1-*.md` đủ 4 phần

---

## Ghi chú bàn giao — dừng phiên 2026-10-19, làm tiếp từ đây

### Tiến độ

| Việc M1 | Trạng thái | Bằng chứng |
|---|---|---|
| 1. Sửa detector (D1–D6) | **Xong** | Commit `d1c5056`, QĐ-015. Dev in-sample: recall detector 0.4497 → 0.4899, FPR 0.1475 → 0.1474; 149/149 fault window có mẫu liền trước thật. Smoke `m1-smoke` trên ClickHouse thật: 50 dòng, 9 candidate; chạy lại cùng `run_id` bị từ chối. 48 test pass, mypy + ruff sạch |
| 2. `protocols.py` + model retrieval/judge | **Làm tiếp từ đây** | — |
| 3. `evidence.py` (log/trace) | Chưa | — |
| 4. `bm25_hybrid.py` | Chưa | — |
| 5. `services/judge/` + `registry.py` | Chưa | — |

Các commit trong phiên 2026-10-18/19: `fc3b38b` (plan CTAV, QĐ-011..013), `f6a9ba6` (lộ trình
cột mốc, QĐ-014, báo cáo M0), `d1c5056` (sửa detector, QĐ-015).

### Vấn đề đang chờ người dùng

| # | Vấn đề | Chặn gì | Ghi chú |
|---|---|---|---|
| V1 | Gửi GVHD tóm tắt hướng CTAV | Nên có trước M4 | Mẫu mail: `docs/drafts/2026-10-18-mail-gvhd-ctav.md` |
| V2 | Q2: đánh giá toàn split hay thêm tập cố định | M4 | Mới biết thêm: detector FPR ~0,15 ⇒ ~4.300 candidate/run trên `val` |
| V3 | Q5: mốc bảo vệ tuần 2027-02-08 cố định? (Tết ~2027-02-06) | Không | |
| V4 | 4 file `legacy/` sửa chưa commit (vá đường dẫn + timestamp `input_freeze.*`) | Không | Vẫn để nguyên, chưa đụng |
| V5 | `front_matter.txt`, `refs_sample.txt`, `toc_out.txt` ở gốc repo; cache `legacy/outputs/test_results/*_cache_*.jsonl` chưa ignore | Không | |
| V6 | Luận văn phải nói rõ kết luận "LLM không RAG thất bại" của GĐ1 là số mock | Không | Khi viết chương Bài toán |

### Ghi nhớ kỹ thuật cho việc 2–5

- Việc 2 thêm trường mới vào `ContextEvent`/`JudgedAlert` theo `03` §1.3–1.4; cột ClickHouse
  tương ứng (`03` §1.6) thêm bằng `infra/clickhouse/migrations/001_ctav_columns.sql`, không sửa `init.sql`.
- Việc 4–5: port **nguyên văn** prompt và cách dựng context của GĐ1 — M3 cần trúng 100% cache
  Gemini ở `legacy/outputs/phase2/step7_rerun/quality_full_budget/cache/paper_500/`. Nên có test
  so chuỗi prompt với một bản ghi cache GĐ1.
- Phần còn lại của D6 dời sang M2: đưa `buffer_size`, cách fit vào `eval/configs/`; bỏ phụ thuộc `packages` → `scripts`.
- Docker: container `clickhouse`, `postgres` đang chạy; dừng bằng `docker compose --profile dev down` (dữ liệu giữ trong volume).
- Python: dùng `.venv` (`.venv/Scripts/python.exe` hoặc `py` khi đã activate).

---

## Mốc sau (M2) — chưa được bắt đầu

Eval harness (runner, metrics, bootstrap CI + McNemar) và **cổng chặn G-port**: tái lập GĐ1
Phase 4 trên `paper_300` theo từng tầng với judge mock (QĐ-012); đếm candidate thật trên
`val` để chốt Q2.

---

## Lệnh tái lập M0

```bash
bash scripts/download_nezha.sh          # nếu chưa có data/Nezha/
py scripts/verify_labels.py             # -> docs/label-audit.md (~80 s)
py scripts/make_splits.py --check       # xác nhận split không đổi
docker compose --profile dev up -d      # clickhouse + postgres
py -m pytest tests/ -q                  # 48 test (sau QĐ-015)
py scripts/replay_smoke.py --windows 50 --run-id <run_id-mới>   # fit + replay + ghi ClickHouse
```
