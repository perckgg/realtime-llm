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
2. - [x] **Xong 2026-10-19 (QĐ-016)** — `packages/schemas/protocols.py` — 4 Protocol theo `01` §5; `models.py` — `ContextEvent` (có `origin`, `graph_distance`), `RetrievalBudget`, `RetrievalResult`, `JudgedAlert` (có trường CTAV) theo `03` §1.3–1.4
3. - [x] **Xong (QĐ-016)** — `packages/schemas/evidence.py` — loader log/trace Nezha → kho bằng chứng, lọc theo cửa sổ thời gian
4. - [x] **Xong (QĐ-016)** — `services/retrieval/bm25_hybrid.py` — port GĐ1, bỏ tag fault type khỏi truy vấn
5. - [x] **Xong (QĐ-016)** — `services/judge/` — prompt **nguyên văn** GĐ1, 3 nhãn, `require_evidence`, cache (key có `repeat`), client `gemini-2.5-flash-lite` (ghi model id, retry có trần → `manual_review`), backend `mock`; `services/retrieval/registry.py`

**Không làm ở mốc này:** harness, ánh xạ `paper_300` (M2); graph, C1 (M3); C2–C4 (M6).

---

## Definition of Done

- [x] `py -m pytest tests/ -q` (86 pass), `py -m mypy packages services`, `py -m ruff check .` đều sạch
- [x] Một candidate dev đi hết BM25 → judge (mock và Gemini thật) → `JudgedAlert` có `debug` đầy đủ (`eval/results/m1-judge-smoke*/`)
- [x] Unit test: cache key, không rò tag fault type, `require_evidence`, điền metric thiếu, lịch sử buffer liên tục
- [x] QĐ-015 ghi kết quả D1/D2 (số đo trước/sau) trong `docs/experiment-log.md`
- [x] Báo cáo `docs/milestones/M1-detector-bm25-judge.md` đủ 4 phần — **chờ người dùng xem** trước khi mở M2

---

## Trạng thái — 2026-10-19: M1 xong, chờ người dùng xem báo cáo

Toàn bộ 5 việc và DoD đã đạt — báo cáo `docs/milestones/M1-detector-bm25-judge.md`, chi
tiết QĐ-015 (việc 1) và QĐ-016 (việc 2–5). **Không mở M2 trước khi người dùng xem §3 của
báo cáo** (`04` §2).

Điểm chính: port BM25 + prompt + cache trùng GĐ1 489/489 trên `paper_500`, tái lập F1 0,7030
/ FP 7 của paper từ cache (nửa BM25 của G-paper). Hai phát hiện về giao thức của paper
(có bằng chứng ⇔ gần sự cố, ở paper lẫn ở Nezha gốc; confidence = `anomaly_score` chép lại) — V7, V8.

### Vấn đề đang chờ người dùng

| # | Vấn đề | Chặn gì |
|---|---|---|
| V7 | Có bằng chứng ⇔ gần sự cố: Nezha chỉ có log/trace quanh lần tiêm lỗi (100% fault, ~25% normal có); paper còn lọc theo nhãn → đề xuất chấm trên cửa sổ có telemetry, trả lời luôn Q2 | **Chặn thiết kế harness M2** |
| V8 | Confidence Gemini ≈ `anomaly_score` → C2 cần tín hiệu khác confidence | Chặn thiết kế C2 (M6) |
| V9 | `top_features` rỗng, metric snapshot thô → port top-3 đặc trưng lệch GĐ1 | Phải xong trước M4 (đề xuất làm ở M2) |
| V1 | Gửi GVHD tóm tắt hướng CTAV (`docs/drafts/2026-10-18-mail-gvhd-ctav.md`) — nên kèm V7, V8 | Nên có trước M4 |
| V2 | Q2: toàn split hay thêm tập cố định | M2/M4 |
| V3 | Q5: mốc bảo vệ tuần 2027-02-08 | Không |
| V4 | 4 file `legacy/` sửa chưa commit — vẫn để nguyên | Không |
| V5 | `front_matter.txt`, `refs_sample.txt`, `toc_out.txt`; cache `legacy/outputs/test_results/*_cache_*.jsonl` chưa ignore | Không |
| V6 | Kết luận "LLM không RAG thất bại" của GĐ1 là số mock | Không |

### Ghi nhớ kỹ thuật

- Dump GĐ1 (`data/gd1_parity/`, không commit): tạo lại bằng `py scripts/dump_gd1_prompts.py`.
- Cache Gemini GĐ2: `data/llm_cache/gemini.jsonl` (không commit; 5 entry smoke M1).
- Migration ClickHouse: sau khi tạo volume mới, chạy `py scripts/apply_clickhouse_migrations.py`.
- Docker: `docker compose --profile dev up -d` / `down`.

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
py -m pytest tests/ -q                  # 86 test (sau QĐ-016)
py scripts/replay_smoke.py --windows 50 --run-id <run_id-mới>   # fit + replay + ghi ClickHouse
```

## Lệnh tái lập M1

```bash
py scripts/apply_clickhouse_migrations.py                # cột CTAV (idempotent)
py scripts/dump_gd1_prompts.py                           # 489 prompt GĐ1 paper_500, ~85 s
py scripts/check_gd1_parity.py                           # port GĐ2 vs GĐ1: 489/489
py scripts/evidence_coverage.py                          # bằng chứng theo nhãn: GĐ1 vs GĐ2
py scripts/judge_smoke.py --run-id <mới> --candidates 3  # BM25 -> judge mock + Gemini
```
