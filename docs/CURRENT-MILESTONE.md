# Mốc hiện tại

> Cập nhật file này khi bắt đầu một mốc mới. Agent đọc file này để biết được phép làm gì.
> Chỉ chép phần mốc hiện tại từ `docs/Final_Thesis_Phase2/04-implementation-roadmap.md`.
> Đóng mốc = DoD đạt + báo cáo `docs/milestones/M<n>-*.md` (4 phần) + người dùng đã xem (`04` §2).

---

## Mốc: M2 — Eval harness + cổng chặn G-port
## Bắt đầu: 2026-10-19 · Hạn mục tiêu: 2026-11-01
## Mốc trước: M1 — QUA, báo cáo `docs/milestones/M1-detector-bm25-judge.md`, người dùng đã xem (QĐ-017)

---

## Quyết định đã chốt cho mốc này

- [x] V7 / Q2 — chỉ số chính trên cửa sổ **có telemetry** (file log/trace Nezha trong ±8 phút); toàn split là số phụ (QĐ-017)
- [x] V8 — prompt GĐ1 nguyên văn cho mọi biến thể; C2 không dựa chỉ vào confidence (M6)
- [x] V9 — detector báo top-3 đặc trưng lệch, làm ở mốc này

Còn mở (không chặn M2): Q5 (mốc bảo vệ), V1 (mail GVHD — nên kèm V7, V8).

---

## Việc được phép làm (theo thứ tự)

1. - [x] **Xong (QĐ-018)** — V9 + phần còn lại của D6: top-3 đặc trưng lệch trong `IsolationForestDetector`; tham số detector (`buffer_size`, cách fit) đọc từ config; bỏ phụ thuộc `packages` → `scripts`
2. - [x] **Xong (QĐ-018)** — `eval/harness/` — config loader, `runner.py` (`py -m eval run --config X`), 6 file output `02` §3.3 + ClickHouse, cột `has_telemetry`, từ chối `run_id` đã có
3. - [x] **Xong (QĐ-018)** — `eval/harness/metrics.py` (P/R/F1/FPR/coverage/latency/token/số lần gọi/chi phí, trên tập có telemetry và toàn split), `stats.py` (bootstrap CI + McNemar chính xác)
4. - [x] **Xong, có điều kiện (QĐ-018)** — G-port: `scripts/map_gd1_windows.py` (`paper_300` → `window_id` GĐ2), `eval/configs/gd1_phase4_parity.yaml`, so từng tầng với audit Phase 4
5. - [x] **Xong (QĐ-018)** — Đếm candidate thật trên `val` (toàn split và có telemetry) → ước chi phí API mỗi run

**Không làm ở mốc này:** graph, C1 (M3); H0 trên `val` với Gemini (M4); C2–C4 (M6).

---

## Definition of Done (cổng chặn G-port, QĐ-012)

- [x] Retrieval: 40 candidate Phase 4 → top-6 BM25 GĐ2 (chế độ parity) trùng doc ID GĐ1; mọi khác biệt giải thích được
- [x] Judge mock: cùng candidate + context → verdict trùng audit GĐ1
- [ ] **Một phần** — Toàn pipeline: P = 0,3158 (6 TP, 13 FP), FPR = 0,0458, recall 0,375; lệch ≤ 1 cửa sổ mỗi ô. Phần sau detector trùng tuyệt đối (tầng 3a); với detector GĐ2: 6/19/10/265 (FP +6, phân rã đủ) — chờ người dùng (V10)
- [x] Detector: so phân phối điểm với `detector_only_audit` (không đòi trùng tuyệt đối — QĐ-009)
- [x] Đủ 6 file output `02` §3.3; `pytest`/`mypy`/`ruff` sạch
- [x] Số candidate thật trên `val` + chi phí ước tính ghi vào experiment-log
- [x] Báo cáo `docs/milestones/M2-harness-gport.md` đủ 4 phần — **chờ người dùng xem, chốt V10, V11** trước khi mở M3

Lệch hơn mức trên = port sai. **Dừng và sửa**, không sang M3.

---

## Mốc sau (M3) — chưa được bắt đầu

Service graph + C1 (`hybrid_bm25_graph`) + cổng chặn G-paper (nửa topology; nửa BM25 đã đạt ở M1).

---

## Lệnh tái lập M0

```bash
bash scripts/download_nezha.sh          # nếu chưa có data/Nezha/
py scripts/verify_labels.py             # -> docs/label-audit.md (~80 s)
py scripts/make_splits.py --check       # xác nhận split không đổi
docker compose --profile dev up -d      # clickhouse + postgres
py -m pytest tests/ -q                  # 100 test (sau QĐ-018)
py scripts/replay_smoke.py --windows 50 --run-id <run_id-mới>   # fit + replay + ghi ClickHouse
```

## Lệnh tái lập M2

```bash
py scripts/map_gd1_windows.py
py scripts/dump_gd1_prompts.py --split phase4 --max-total-calls 40
py -m eval run --config eval/configs/gd1_phase4_parity.yaml      # run_id mới nếu đã có
py scripts/gport_layers.py --run gd1_phase4_parity_v1
py -m eval run --config eval/configs/val_detector_count.yaml     # ~5 phút
```

## Lệnh tái lập M1

```bash
py scripts/apply_clickhouse_migrations.py                # cột CTAV (idempotent)
py scripts/dump_gd1_prompts.py                           # 489 prompt GĐ1 paper_500, ~85 s
py scripts/check_gd1_parity.py                           # port GĐ2 vs GĐ1: 489/489
py scripts/evidence_coverage.py                          # bằng chứng theo nhãn: GĐ1 vs GĐ2
py scripts/judge_smoke.py --run-id <mới> --candidates 3  # BM25 -> judge mock + Gemini
```
