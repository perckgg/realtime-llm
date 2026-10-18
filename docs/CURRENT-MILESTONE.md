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
- [ ] QĐ-015 ghi kết quả D1/D2 (số đo trước/sau) trong `docs/experiment-log.md`
- [ ] Báo cáo `docs/milestones/M1-*.md` đủ 4 phần

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
py -m pytest tests/ -q                  # 32 test
py scripts/replay_smoke.py --windows 50 # fit + replay + ghi ClickHouse
```
