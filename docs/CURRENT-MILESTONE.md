# Mốc hiện tại

> Cập nhật file này khi bắt đầu một mốc mới. Agent đọc file này để biết được phép làm gì.
> Chỉ chép phần mốc hiện tại từ `docs/Final_Thesis_Phase2/04-implementation-roadmap.md`.
> Đóng mốc = DoD đạt + báo cáo `docs/milestones/M<n>-*.md` (4 phần) + người dùng đã xem (`04` §2).

---

## Trạng thái — 2026-10-19

| Mốc | Trạng thái | Báo cáo / quyết định |
|---|---|---|
| M0 | QUA | `docs/milestones/M0-nen-tang.md` |
| M1 | QUA | `docs/milestones/M1-detector-bm25-judge.md`; QĐ-015..017 |
| M2 | QUA | `docs/milestones/M2-harness-gport.md`; QĐ-018, QĐ-019 |
| M3 | **QUA** (đóng 2026-10-19) | `docs/milestones/M3-graph-c1-gpaper.md`; QĐ-020, QĐ-021 |
| M4 | **Chưa mở — chờ V16, V17** | Mục dưới |

M3 tóm tắt: đồ thị trùng GĐ1 (68/68 cạnh); C1 đã port; **G-paper đạt cả hai biến thể**
(BM25 F1 0,7030 / FP 7, Topology F1 0,4759 / FP 137, cache hit 489/489, không gọi API); judge
GĐ2 = `gemini-2.5-flash` (V12). Phát hiện 4: C1 với trọng số paper không đưa bằng chứng lân
cận nào vào prompt trên dữ liệu đầy đủ (0/196) ⇒ cần chốt V16 trước H0.

---

## Mốc tiếp theo: M4 — H0: tái lập vấn đề trên split GĐ2
## Dự kiến bắt đầu: khi chốt V16, V17

### Việc (dự kiến, chi tiết ở báo cáo M3 §4)

1. - [ ] V17: tăng tốc retrieval C1 (mục tiêu < 0,5 s/lần, giữ ngữ nghĩa)
2. - [ ] Nếu V16 (b): `k_graph` (quota bằng chứng lân cận) trong C1 + test; chọn `k_graph` trên `val`
3. - [ ] Ablation retrieval-only lưới α, β, γ trên `val` (gồm β = 1, γ = 1)
4. - [ ] H0 trên `val` (tập có telemetry, `gemini-2.5-flash`): BM25, C1-paper, (C1-quota), LLM-không-RAG, detector-only; CI + McNemar; ngân sách toàn bộ + 120
5. - [ ] Nháp chương "Bài toán" từ paper + Phát hiện 1–4

### Vấn đề cần chốt

| # | Vấn đề | Khuyến nghị | Chặn gì |
|---|---|---|---|
| **V16** | C1 đúng paper không đưa bằng chứng lân cận vào prompt trên dữ liệu đầy đủ (điểm hạng 6 local 0,84 > tối đa lân cận 0,80) | (b): giữ C1-paper làm baseline + thêm C1-quota (`k_graph` chỗ cho bằng chứng d ≥ 1) làm tầng 2 của CTAV; báo cáo trung thực cả hai | **H0 / M4** |
| **V17** | C1 chậm (~2,9 s/lần ⇒ ~85 phút retrieval mỗi run `val`) | (a): cache thống kê token theo file, BM25 numpy sparse, song song theo process | Thời gian M4 |
| V1 | Mail GVHD — bản cập nhật đã soạn: `docs/drafts/2026-10-19-mail-gvhd-ctav.md` (kèm Phát hiện 1–4, V16, judge mới) | Bạn đọc, sửa và gửi trước M4 | Nên |
| V3 | Q5: mốc bảo vệ tuần 2027-02-08 | | Không |
| V4–V6 | File `legacy/` chưa commit; file rác gốc repo; câu "LLM không RAG thất bại" là số mock | | Không |

---

## Ghi chú bàn giao — dừng phiên 2026-10-19, làm tiếp từ đây

**Trạng thái:** M0–M3 đã đóng; M4 chưa mở. Phiên kế tiếp bắt đầu bằng việc người dùng chốt
**V16** (C1-quota hay giữ đúng paper) và **V17** (tăng tốc C1) — xem bảng trên và
`docs/milestones/M3-graph-c1-gpaper.md` §3. Không viết code M4 trước khi có hai quyết định này.

**Commit của phiên 2026-10-19** (theo thứ tự): `7dbb07f` M1 việc 2–5 (QĐ-016) · `48b2284`,
`b3d1761`, `a688a8a` M2 (QĐ-017, QĐ-018) · `cc3a595` judge song song (QĐ-019) · `aa859f0`
khảo sát M3 (QĐ-020) · `5595e61` M3 (QĐ-021) · commit bàn giao này.

**Báo cáo cột mốc cần đọc:** `docs/milestones/M1-detector-bm25-judge.md`,
`M2-harness-gport.md`, `M3-graph-c1-gpaper.md`.

**Bốn phát hiện quan trọng cho luận văn** (đã ghi trong experiment-log):
1. QĐ-016/017 — Nezha chỉ có log/trace quanh lần tiêm lỗi (100% fault, ~25% normal có); kho
   bằng chứng của paper còn lọc theo nhãn ⇒ chỉ số chính GĐ2 tính trên cửa sổ có telemetry.
2. QĐ-020 — 80% bằng chứng topology của paper lệch thời gian > 8 phút; 100% normal có bằng chứng.
3. QĐ-021 — C1 đúng paper trên dữ liệu đầy đủ chọn 0 bằng chứng lân cận (V16).
4. QĐ-016/019/021 — Gemini chép `anomaly_score` làm confidence khi thiếu bằng chứng (83% ở
   paper); `gemini-2.5-flash` trên prompt GĐ2 chỉ 1/196.

**Ghi nhớ kỹ thuật:**
- Judge GĐ2 = `gemini-2.5-flash` (`JUDGE_MODEL`); flash-lite chỉ cho G-paper (`PAPER_MODEL`).
  Run dừng nếu `modelVersion` lệch (một số id 3.x bị API chuyển ngầm).
- Harness: `py -m eval run --config X`; judge song song 8 worker, 200 lần gọi/phút (Tier 1).
  Lỗi judge ⇒ `runtime.json.judge_errors`; chạy lại với run_id mới chỉ hỏi lại câu lỗi.
- Cache Gemini GĐ2: `data/llm_cache/gemini.jsonl` (397 entry, không commit — giữ file này).
  Dump GĐ1: `data/gd1_parity/` (tạo lại bằng `scripts/dump_gd1_prompts.py`).
- Chi phí API của phiên: ≈ 0,30 USD (smoke M1 5 lần, thử model 5 lần, smoke flash-lite 196 lần
  ≈ 0,056, smoke flash 197 lần ≈ 0,23).
- Docker `clickhouse`, `postgres` đang chạy; volume mới cần `py scripts/apply_clickhouse_migrations.py`.
- Đường dẫn khi viết patch: heredoc `py - <<'EOF'` làm hỏng chuỗi có `
` — dùng file script riêng.
- V17 gợi ý: nút thắt là BM25 thuần Python trên pool trung vị ~147 nghìn event/truy vấn.

---

## Lệnh tái lập M3

```bash
py scripts/build_service_graph.py
py scripts/dump_gd1_prompts.py --variant topology_aware_fusion_top6
py scripts/check_gd1_parity.py --variant hybrid_bm25_top6
py scripts/check_gd1_parity.py --variant topology_aware_fusion_top6
py -m eval run --config eval/configs/m3_c1_window_smoke.yaml       # run_id mới
```

## Lệnh tái lập M0

```bash
bash scripts/download_nezha.sh          # nếu chưa có data/Nezha/
py scripts/verify_labels.py             # -> docs/label-audit.md (~80 s)
py scripts/make_splits.py --check       # xác nhận split không đổi
docker compose --profile dev up -d      # clickhouse + postgres
py -m pytest tests/ -q                  # 115 test (sau QĐ-021)
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
