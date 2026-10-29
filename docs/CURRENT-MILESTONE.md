# Mốc hiện tại

> Cập nhật file này khi bắt đầu một mốc mới. Agent đọc file này để biết được phép làm gì.
> Chỉ chép phần mốc hiện tại từ `docs/Final_Thesis_Phase2/04-implementation-roadmap.md`.
> Đóng mốc = DoD đạt + báo cáo `docs/milestones/M<n>-*.md` (4 phần) + người dùng đã xem (`04` §2).

---

## Trạng thái — 2026-10-29

| Mốc | Trạng thái | Báo cáo / quyết định |
|---|---|---|
| M0 | QUA | `docs/milestones/M0-nen-tang.md` |
| M1 | QUA | `docs/milestones/M1-detector-bm25-judge.md`; QĐ-015..017 |
| M2 | QUA | `docs/milestones/M2-harness-gport.md`; QĐ-018, QĐ-019 |
| M3 | QUA (đóng 2026-10-19) | `docs/milestones/M3-graph-c1-gpaper.md`; QĐ-020, QĐ-021 |
| M4 | **QUA CÓ ĐIỀU KIỆN** (đóng 2026-10-29) — điều kiện: GVHD không phản đối V24 (b) | `docs/milestones/M4-h0.md`; QĐ-022..027 |
| M5 | **Chưa mở** — chờ người dùng bắt đầu | Mục dưới; `04` M5 |

M4 tóm tắt: H0 trên `val` tái lập **hiện tượng** (C1-paper − BM25: ΔRecall +0,100 [+0,052; +0,155],
ΔFPR +0,025 [+0,020; +0,031], McNemar có ý nghĩa; ΔF1 CI chứa 0) nhưng **không tái lập cơ chế**
(Phát hiện 7): C1-quota ≡ C1-paper; khác biệt do C1 chọn trace span sát t₀; mọi biến thể có judge F1
≈ detector-only. V24 → (b) đổi trục C2, C3, H1 sang độ gần thời gian / loại bằng chứng, giữ khung
CTAV (QĐ-027, chốt tạm chờ GVHD).

---

## Mốc kế tiếp: M5 — H1: cơ chế thiên lệch xác nhận (theo QĐ-027)
## Chưa mở — chỉ bắt đầu khi người dùng bảo

### Việc (chi tiết ở báo cáo M4 §4 và `04` M5)

1. - [ ] Người dùng gửi mail GVHD `docs/drafts/2026-10-29-mail-gvhd-h0.md`
2. - [ ] Mẫu cố định `eval/samples/h1_val.json` (seed 42): candidate normal có telemetry + 109 fault candidate của `val`; pool cục bộ từ `build_pool`
3. - [ ] Prompt can thiệp, giữ k = 6: tỷ lệ event trong ±60 s quanh t₀ 0/33/67/100%; trace ↔ log; xáo thứ tự; đối chứng âm tỷ lệ lân cận 0/100%. Kiểm tra trước số candidate dựng được mọi điều kiện
4. - [ ] Judge thật từng điều kiện (chạy một điều kiện thử trước); `repeat ∈ {0, 1, 2}` trên tập con
5. - [ ] Phân tích + kết luận H1 + đặc trưng cho C2 ⇒ experiment-log, báo cáo `docs/milestones/M5-h1.md`

**DoD M5:** đường tỷ lệ TRUE_ALERT trên normal (và recall trên fault) theo từng biến can thiệp có
CI; kết luận H1 (giữ / bác bỏ) và đặc trưng cho C2 ghi experiment-log. Hạn 2026-11-22.

### Vấn đề cần chốt

| # | Vấn đề | Khuyến nghị | Chặn gì |
|---|---|---|---|
| V25 | Ý kiến GVHD về V24 (b) | Gửi mail; nếu GVHD phản đối ⇒ dừng M5, mở lại V24 | Điều kiện của M4 |
| V26 | Billing 5 USD / ≈ 8k request so với ≈ 4,4 USD / ≈ 4.830 request trong log (QĐ-026) | Người dùng cho biết khung thời gian của dashboard ⇒ đối chiếu; ước ngân sách M5 (≈ 16–23 USD) theo kết quả | Ngân sách M5 |
| V3 | Q5: mốc bảo vệ tuần 2027-02-08 | | Không |
| V4–V6 | File `legacy/` chưa commit; file rác gốc repo; câu "LLM không RAG thất bại" là số mock | | Không |

Các vấn đề V16–V24 đã chốt: xem báo cáo M4 §3 và QĐ-022..027.

---

## Ghi chú bàn giao — phiên 2026-10-29

**Trạng thái:** V24 chốt (b), tạm (QĐ-027); M4 đóng có điều kiện; `08` (§2, §4, §5.1, §6), `04`
(bảng §1, M4, M5, M6), `06` (dòng H1) và nháp chương (mục 5–6) đã sửa; mail GVHD soạn ở
`docs/drafts/2026-10-29-mail-gvhd-h0.md` (chưa gửi). Chưa viết code cho M5.
**Việc đầu tiên phiên sau:** hỏi người dùng đã gửi mail GVHD / có phản hồi chưa, và khung thời gian
billing (V26); rồi mới mở M5.

## Ghi chú bàn giao — phiên 2026-10-28

**Trạng thái:** M4 xong mọi việc, chờ **V24** để đóng. H0 chạy xong (9 run + 2 compare + `h0_val_evidence_diff_v1`); nháp chương `docs/drafts/chuong-bai-toan.md`.
**Commit:** `1b04c88` (ghi chú bàn giao 10-20). Kết quả H0, sửa retry, script `h0_evidence_diff.py`, nháp chương: xem `git log` (chưa push).
**Sự cố:** `h0_val_bm25_v2` sập do `TimeoutError` khi đọc response không được retry ⇒ sửa `_post_json_with_retry` (bắt `OSError` + `HTTPException`), test mới; BM25 chạy lại `_v3`. Thư mục `_v1`, `_v2` rỗng, để nguyên.
Test: 150 pass. Chi phí phiên: ≈ 4,4 USD theo token (4.808 lần gọi), billing người dùng báo 5 USD / ≈ 8k request — chưa đối chiếu (QĐ-026); M4 ≈ 8,6 USD theo token. Cache Gemini 10.710 entry (không commit — giữ file).
**Việc đầu tiên phiên sau:** người dùng chốt V24 (báo cáo M4 §3); nếu (b) ⇒ QĐ-027, sửa `08` §2/§4/§5 + mô tả M5–M6 trong `04`, cập nhật mục 5–6 nháp chương, đóng M4.

## Ghi chú bàn giao — phiên 2026-10-20

**Trạng thái:** M4 đã mở; nháp báo cáo `docs/milestones/M4-h0.md`. V16 (b) và V17 (a) đã cài, test, đo (QĐ-022, kèm bảng phương án dự
phòng). V19, V20 đã chốt (QĐ-023); V18 đã chốt (a): `k_graph = 1` (QĐ-024, `m4_kgraph_val_k*_v1`); ablation α/β/γ xong (QĐ-025); code H0 xong (QĐ-026), run H0 đang chờ V23. Docker `--profile dev` cần chạy cho `tests/test_storage.py`.
**Commit:** `20fe298` (M4 tới V18, QĐ-022..024) · `4695008` (ghi hash) · `59012f4` (ablation, QĐ-025) · `a351ca5` (chuẩn bị H0, QĐ-026). Chưa push.
Test: 148 pass (gồm `test_compare`, `test_fusion_ablation`, `test_storage`, `test_window_index`, `test_kgraph_select`).
Chi phí API phiên 2026-10-20 ≈ 4,2 USD: ≈ 1,2 USD trước H0 (probe 5 lần, smoke 3.8 ≈ 0,315, 3.6 ≈ 0,33, V20: 2.5 ≈ 0,23, 3.8 ≈ 0,33) + ≈ 3,0 USD cho `h0_val_bm25_v1` (4.722 lần gọi, dừng vì spend cap); quét V18 và ablation dùng judge mock / không gọi LLM (0 USD).
Cache Gemini `data/llm_cache/gemini.jsonl`: 5.903 entry (không commit — giữ file này, H0 chạy tiếp từ đây).
**Việc đầu tiên phiên sau:** kiểm tra API hết 429 (spend cap đúng project của `GEMINI_API_KEY`), rồi chạy H0 theo "Lệnh tái lập M4" bên dưới.
Config mới: `m4_c1_vec_smoke.yaml` (V17, judge mock), `m4_judge_g36_smoke.yaml`,
`m4_judge_g38_smoke.yaml`, `m4_v20_g25_smoke.yaml`, `m4_v20_g38_smoke.yaml`, `m4_kgraph_val_k{0..3}.yaml` (V18, judge mock). Đo retrieval: `py scripts/retrieval_bench.py run --config ... --name ... --set k_graph=1`.
Chọn k: `scripts/kgraph_select.py` + `eval/harness/kgraph.py`.
Ablation α/β/γ (QĐ-025, 0 USD): `scripts/fusion_ablation.py` + `eval/harness/fusion_ablation.py`, config `m4_fusion_ablation_val.yaml` (lưới bước 0,25 — tôi chọn, chưa hỏi), kết quả `eval/results/m4_fusion_ablation_val_v1/`. C1 tách `build_pool`/`top_events`/`reweighted` (refactor thuần, có test).
H0 (QĐ-026): retrieval `none` (`services/retrieval/no_retrieval.py`), `py -m eval compare` (`eval/harness/compare.py`), 9 config `eval/configs/h0_val_*.yaml`. `h0_val_bm25_v1/` (spend cap) và `_v2/` (timeout, 2026-10-28) là thư mục rỗng do run dừng — để nguyên (không ghi đè), run tiếp là `_v3`.

## Ghi chú bàn giao — dừng phiên 2026-10-19

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
- Khi sửa file bằng script: heredoc `py - <<'EOF'` làm hỏng chuỗi chứa ký tự xuống dòng thoát (backslash-n) — viết script ra file riêng rồi chạy.
- V17 gợi ý: nút thắt là BM25 thuần Python trên pool trung vị ~147 nghìn event/truy vấn.

---

## Lệnh tái lập M4 (tới nay)

```bash
py -m eval run --config eval/configs/m4_c1_vec_smoke.yaml          # V17, run_id mới
py -m eval run --config eval/configs/m4_v20_g25_smoke.yaml         # V20, cần GEMINI_API_KEY
py -m eval run --config eval/configs/m4_kgraph_val_k0.yaml         # V18: k0..k3, ~8 phút/run
py scripts/kgraph_select.py --runs 0=m4_kgraph_val_k0_v1,1=m4_kgraph_val_k1_v1,2=m4_kgraph_val_k2_v1,3=m4_kgraph_val_k3_v1 --out <file-mới>.json
py scripts/fusion_ablation.py --config eval/configs/m4_fusion_ablation_val.yaml  # QĐ-025, đổi run_id; ~9 phút

# H0 (QĐ-026) — cần GEMINI_API_KEY, chạy đúng thứ tự (các run sau dùng lại cache của run trước)
py -m eval run --config eval/configs/h0_val_bm25.yaml          # _v3 (v1: spend cap, v2: timeout — cả hai thư mục rỗng)
py -m eval run --config eval/configs/h0_val_c1_k0.yaml
py -m eval run --config eval/configs/h0_val_c1_k1.yaml
py -m eval run --config eval/configs/h0_val_norag.yaml         # require_evidence: false
py -m eval run --config eval/configs/h0_val_norag_reqev.yaml   # 100% cache
py -m eval run --config eval/configs/h0_val_bm25_b120.yaml     # + c1_k0/c1_k1/norag _b120, 100% cache
py -m eval compare --runs bm25=h0_val_bm25_v3,c1_k0=h0_val_c1_k0_v1,c1_k1=h0_val_c1_k1_v1,norag=h0_val_norag_v1 --detector-only h0_val_bm25_v3 --out h0_val_compare_v1
py -m eval compare --runs c1_k0=h0_val_c1_k0_v1,c1_k1=h0_val_c1_k1_v1 --out h0_val_compare_k1_vs_k0_v1
py scripts/h0_evidence_diff.py --a h0_val_bm25_v3 --b h0_val_c1_k0_v1 --out h0_val_evidence_diff_v1   # Phát hiện 7
```

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
