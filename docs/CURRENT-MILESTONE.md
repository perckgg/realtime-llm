# Mốc hiện tại

> Cập nhật file này khi bắt đầu một mốc mới. Agent đọc file này để biết được phép làm gì.
> Chỉ chép phần mốc hiện tại từ `docs/Final_Thesis_Phase2/04-implementation-roadmap.md`.
> Đóng mốc = DoD đạt + báo cáo `docs/milestones/M<n>-*.md` (4 phần) + người dùng đã xem (`04` §2).

---

## Trạng thái — 2026-10-20

| Mốc | Trạng thái | Báo cáo / quyết định |
|---|---|---|
| M0 | QUA | `docs/milestones/M0-nen-tang.md` |
| M1 | QUA | `docs/milestones/M1-detector-bm25-judge.md`; QĐ-015..017 |
| M2 | QUA | `docs/milestones/M2-harness-gport.md`; QĐ-018, QĐ-019 |
| M3 | **QUA** (đóng 2026-10-19) | `docs/milestones/M3-graph-c1-gpaper.md`; QĐ-020, QĐ-021 |
| M4 | **ĐANG LÀM** — V16–V20, V22 đã chốt; `k_graph = 1`; ablation α/β/γ xong (QĐ-025); tiếp theo H0 | Nháp `docs/milestones/M4-h0.md`; QĐ-022..025; mục dưới |

M3 tóm tắt: đồ thị trùng GĐ1 (68/68 cạnh); C1 đã port; **G-paper đạt cả hai biến thể**
(BM25 F1 0,7030 / FP 7, Topology F1 0,4759 / FP 137, cache hit 489/489, không gọi API); judge
GĐ2 = `gemini-2.5-flash` (V12). Phát hiện 4: C1 với trọng số paper không đưa bằng chứng lân
cận nào vào prompt trên dữ liệu đầy đủ (0/196) ⇒ cần chốt V16 trước H0.

---

## Mốc hiện tại: M4 — H0: tái lập vấn đề trên split GĐ2
## Mở 2026-10-20 (QĐ-022)

### Việc (chi tiết ở báo cáo M3 §4; tiến độ ở nháp `docs/milestones/M4-h0.md`)

1. - [x] V17: engine `vectorized` + `retrieval.workers` — 196/196 top-6 trùng từng bit; 593 s → 88 s (6 process, ≈ 0,45 s/lần); một run `val` judge mock ≈ 8 phút; dự phòng `engine: reference` (QĐ-022)
2. - [x] V16 (b): `k_graph` đã cài + test (k ≥ 1 ⇒ 68,9% prompt có bằng chứng lân cận, k = 0: 0%); quét `val` k = 0..3 (QĐ-024) ⇒ **`k_graph = 1`** (V18 (a))
3. - [x] Ablation retrieval-only lưới α, β, γ × `k_graph` trên `val` (QĐ-025, `m4_fusion_ablation_val_v1`, 9 phút, 0 USD): γ ≥ 0,25 ⇒ gần như không có lân cận nếu không có quota; chỉ temporal-only đảo ngược (mất root); "root đang lỗi cùng lúc" ≤ 8,4% ⇒ **giữ trọng số paper cho H0** (Phát hiện 6)
4. - [ ] H0 trên `val` (tập có telemetry, `gemini-2.5-flash`, `drop_metrics: ["PodSuccessRate(%)"]` — QĐ-023): BM25, C1-paper (`k_graph = 0`), C1-quota (`k_graph = 1`), LLM-không-RAG, detector-only; CI + McNemar; ngân sách toàn bộ + 120. Người dùng chốt: judge toàn bộ 5.677 candidate; LLM-không-RAG số chính `require_evidence: false` (+ bản `true`); ngân sách 120 chạy lại từ cache. **Đã cài** retrieval `none`, `py -m eval compare`, 9 config `h0_val_*` (QĐ-026, 148 test pass). **Đang chặn (V23):** run BM25 dừng ở 4.722/5.677 lần gọi (≈ 3,0 USD, đã vào cache) — API 429 "monthly spending cap". Còn ≈ 4.800 lần gọi ≈ 3,6 USD (thực đo ≈ 0,00074 USD/lần)
5. - [ ] Nháp chương "Bài toán" từ paper + Phát hiện 1–6

### Vấn đề cần chốt

| # | Vấn đề | Khuyến nghị | Chặn gì |
|---|---|---|---|
| ~~V18~~ | Đã chốt (a) (2026-10-20, QĐ-024): **`k_graph = 1`** theo quy tắc hoà ⇒ k nhỏ nhất; proxy suy biến (fault window luôn là cửa sổ của service gốc), ghi rõ trong luận văn | Ảnh hưởng thật của k lên FP/recall đo ở H0 (C1-paper k = 0 vs C1-quota k = 1) | |
| ~~V19~~ | Đã chốt (2026-10-20, QĐ-023): giữ `gemini-2.5-flash` | Sau V20: 2.5 F1 0,48 / FP 1; 3.8 F1 0,25 / FP 0 (recall 0,14) | |
| ~~V20~~ | Đã chốt (QĐ-023): `judge.drop_metrics: ["PodSuccessRate(%)"]` cho mọi run GĐ2 có judge thật; mặc định `[]` = prompt GĐ1 (G-paper) | Smoke 2.5-flash: FP 25 → 1, F1 0,30 → 0,48 | |
| V21 | Câu trả lời JSON hỏng bị ghi vào cache ⇒ chạy lại không hỏi lại được (1/196 mỗi smoke) | (a) giữ như hiện tại: tính UNCERTAIN/manual review, báo cáo tỷ lệ; (b) không cache JSON hỏng — đổi hành vi cache (QĐ-013) | Không (nhỏ) |
| V23 | Gemini API: project vượt **spend cap hàng tháng** (AI Studio → https://ai.studio/spend) | Nâng cap thêm ≥ 5 USD rồi chạy theo thứ tự: `h0_val_bm25` (v2) → `c1_k0` → `c1_k1` → `norag` → `norag_reqev` + 4 `*_b120` (cache) → `py -m eval compare`. Dự phòng: đợi sang tháng mới; hoặc chạy H0 thu hẹp (BM25 vs C1-k0) trước | **H0 (việc 4)** |
| ~~V22~~ | Đã chốt (a) (2026-10-20, QĐ-025): chỉ số ablation = bằng chứng lân cận + "root đang lỗi cùng lúc" | | |
| ~~V16~~ | Đã chốt (b) — QĐ-022 | C1-paper baseline + C1-quota `k_graph`; dự phòng (a)/(c) | |
| ~~V17~~ | Đã chốt (a) — QĐ-022 | `engine: vectorized`, dự phòng `reference`, `retrieval.workers` | |
| ~~V1~~ | Đã gửi (2026-10-20) | | |
| V3 | Q5: mốc bảo vệ tuần 2027-02-08 | | Không |
| V4–V6 | File `legacy/` chưa commit; file rác gốc repo; câu "LLM không RAG thất bại" là số mock | | Không |

---

## Ghi chú bàn giao — phiên 2026-10-20

**Trạng thái:** M4 đã mở; nháp báo cáo `docs/milestones/M4-h0.md`. V16 (b) và V17 (a) đã cài, test, đo (QĐ-022, kèm bảng phương án dự
phòng). V19, V20 đã chốt (QĐ-023); V18 đã chốt (a): `k_graph = 1` (QĐ-024, `m4_kgraph_val_k*_v1`). Docker `--profile dev` cần chạy cho `tests/test_storage.py`.
**Commit:** `20fe298` (M4 tới V18, QĐ-022..024).
Test: 145 pass (gồm `test_fusion_ablation`, `test_storage`, `test_window_index`, `test_kgraph_select`).
Chi phí API phiên 2026-10-20 ≈ 1,2 USD (probe 5 lần, smoke 3.8 ≈ 0,315, 3.6 ≈ 0,33, V20: 2.5 ≈ 0,23, 3.8 ≈ 0,33); quét V18 dùng judge mock (0 USD).
Config mới: `m4_c1_vec_smoke.yaml` (V17, judge mock), `m4_judge_g36_smoke.yaml`,
`m4_judge_g38_smoke.yaml`, `m4_v20_g25_smoke.yaml`, `m4_v20_g38_smoke.yaml`, `m4_kgraph_val_k{0..3}.yaml` (V18, judge mock). Đo retrieval: `py scripts/retrieval_bench.py run --config ... --name ... --set k_graph=1`.
Chọn k: `scripts/kgraph_select.py` + `eval/harness/kgraph.py`.
Ablation α/β/γ (QĐ-025, 0 USD): `scripts/fusion_ablation.py` + `eval/harness/fusion_ablation.py`, config `m4_fusion_ablation_val.yaml` (lưới bước 0,25 — tôi chọn, chưa hỏi), kết quả `eval/results/m4_fusion_ablation_val_v1/`. C1 tách `build_pool`/`top_events`/`reweighted` (refactor thuần, có test). Chưa commit.

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
