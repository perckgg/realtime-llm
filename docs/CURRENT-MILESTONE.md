# Mốc hiện tại

> Cập nhật file này khi bắt đầu một mốc mới. Agent đọc file này để biết được phép làm gì.
> Chỉ chép phần mốc hiện tại từ `docs/Final_Thesis_Phase2/04-implementation-roadmap.md`.
> Đóng mốc = DoD đạt + báo cáo `docs/milestones/M<n>-*.md` (4 phần) + người dùng đã xem (`04` §2).

---

## Trạng thái — 2026-11-01

| Mốc | Trạng thái | Báo cáo / quyết định |
|---|---|---|
| M0 | QUA | `docs/milestones/M0-nen-tang.md` |
| M1 | QUA | `docs/milestones/M1-detector-bm25-judge.md`; QĐ-015..017 |
| M2 | QUA | `docs/milestones/M2-harness-gport.md`; QĐ-018, QĐ-019 |
| M3 | QUA (đóng 2026-10-19) | `docs/milestones/M3-graph-c1-gpaper.md`; QĐ-020, QĐ-021 |
| M4 | QUA (đóng 2026-10-29; GVHD đồng ý V24 (b)) | `docs/milestones/M4-h0.md`; QĐ-022..027 |
| M5 | QUA (đóng 2026-11-01; H1 giữ một phần, V28 (b)) | `docs/milestones/M5-h1.md`; QĐ-028, QĐ-029 |
| M6 | **ĐANG LÀM** (mở 2026-11-01) | Mục dưới; `04` M6 |

M4 tóm tắt: H0 trên `val` tái lập **hiện tượng** (C1-paper − BM25: ΔRecall +0,100 [+0,052; +0,155],
ΔFPR +0,025 [+0,020; +0,031], McNemar có ý nghĩa; ΔF1 CI chứa 0) nhưng **không tái lập cơ chế**
(Phát hiện 7): C1-quota ≡ C1-paper; khác biệt do C1 chọn trace span sát t₀; mọi biến thể có judge F1
≈ detector-only. V24 → (b) đổi trục C2, C3, H1 sang độ gần thời gian / loại bằng chứng, giữ khung
CTAV (QĐ-027; GVHD đồng ý 2026-10-29).

M5 tóm tắt: H1 giữ một phần (QĐ-028). TRUE_ALERT tăng theo độ gần thời gian và cao hơn với trace, nhưng
chững lại từ 67% và tác động cả recall. Không chọn đặc trưng C2 từ H1; V28 (b): M6 chỉ quét θ trên verdict
đã cache, trọng tâm giảm FP sang C3 (QĐ-029).

---

## Mốc hiện tại: M6 — CTAV: C2 + C3 + C4, chốt cấu hình (theo QĐ-029)
## Mở 2026-11-01

### Việc (chi tiết ở `04` M6 và báo cáo M5 §4)

1. - [ ] Ngưỡng nền `duration_ms` theo service + operation (cho C3): baseline `dev` đã dựng nhưng chỉ phủ ≈ 32% span trên `val` (Phát hiện 8, QĐ-030). **Chờ V30**
2. - [ ] `services/judge/policy.py`: C3 (trọng tâm) + gating θ (C2); áp lên verdict **đã cache** từ M4; unit test
3. - [ ] Quét θ, chọn trên `val`, không gọi thêm LLM
4. - [ ] `services/judge/routing.py`: BM25 trước, topology khi UNCERTAIN / thiếu bằng chứng; unit test
5. - [ ] Quét ngân sách gọi LLM (H4)
6. - [ ] Ablation H3: CTAV đầy đủ, bỏ C2, bỏ C3, bỏ C4; C2 không đóng góp ⇒ bỏ khỏi phương pháp (QĐ-029)
7. - [ ] Song song: `rca_agent/grouping.py` bản khởi động (timestamp + graph)

**DoD M6:** `eval/configs/ctav_final.yaml` chốt; bảng H3 trên `val` có CI; θ chọn ghi experiment-log.
Hạn 2026-12-06.

### Vấn đề cần chốt

| # | Vấn đề | Khuyến nghị | Chặn gì |
|---|---|---|---|
| ~~V25~~ | Ý kiến GVHD về V24 (b) | GVHD đồng ý 2026-10-29 | |
| V26 | Billing 5 USD / ≈ 8k request so với ≈ 4,4 USD / ≈ 4.830 request trong log (QĐ-026) | Người dùng cho biết khung thời gian của dashboard ⇒ đối chiếu. Nếu billing thật cao hơn token > 1,3× thì tính lại bảng ngân sách dưới | Không (theo dõi) |
| ~~V28~~ | Đặc trưng C2 sau H1 | Người dùng chốt (b) (QĐ-029) | |
| V30 | Nguồn ngưỡng nền cho C3: baseline `dev` phủ ≈ 32% span trên `val` (QĐ-030) | Baseline trượt 60 phút (phủ ≈ 93%), đổi đặc tả C3 trong `08` | **M6 việc 2** |
| V29 | GVHD chưa được báo V28 (b); cần biết thêm loại báo cáo tháng 11 (tiến độ hay kết quả) | Người dùng báo GVHD; GVHD phản đối ⇒ mở lại V28 | Không (M6 đang chạy song song) |
| V27 | Phạm vi chấm ở M8 (`test`): toàn bộ candidate (như H0, ≈ 14 USD) hay chỉ cửa sổ có telemetry (số chính, ≈ 5 USD) | Quyết định khi mở M8, theo số credit còn lại lúc đó | M8 |
| V3 | Q5: mốc bảo vệ tuần 2027-02-08 | | Không |
| V4–V6 | File `legacy/` chưa commit; file rác gốc repo; câu "LLM không RAG thất bại" là số mock | | Không |

Các vấn đề V16–V24 đã chốt: xem báo cáo M4 §3 và QĐ-022..027. V28: báo cáo M5 §3 và QĐ-029.

---

## Ngân sách API (ghi 2026-10-29, theo yêu cầu người dùng)

**Credit còn lại:** ≈ 1.250.000 đ ≈ **48 USD** (ước theo ≈ 26.000 đ/USD — đối chiếu đơn vị credit trên AI
Studio). Đơn giá thực đo (QĐ-026, M5): ≈ 0,0014 USD / lần gọi theo token với prompt có 6 bằng chứng
(≈ 2.000 token vào / 310 ra); ≈ 0,0006 USD với prompt không bằng chứng; billing ≈ 1,14 × số theo token
(ngày 2026-10-28). Số dưới đây là **ước tính đã nhân 1,14, không phải số billing thật**: hệ số này chỉ
suy từ một lần đối chiếu, giá trong code và số dư credit chưa được đối chiếu (V26).

| Mốc | Phần tốn API | Ngân sách | Ngưỡng dừng |
|---|---|---|---|
| M5 (còn lại) | Xong: 753 lần gọi, 1,0093 USD **theo token** (billing thật chưa biết) | 1,5 USD | 3 USD |
| M6 | C2/C3 áp lên verdict đã cache; định tuyến BM25 → C1 và quét ngân sách từ cache H0 | 2 USD | 4 USD — đổi prompt judge = lập lại ngân sách trước khi chạy |
| M7 | Chỉ chấm các cửa sổ được Rescue Score "cứu" (quét tham số không gọi LLM) | 4 USD | 6 USD |
| M8 | `test` một lần: BM25, C1, không-RAG (CTAV dùng lại cache) + `repeat` trên tập con; phạm vi theo V27 | 17 USD (toàn bộ) / 8 USD (chỉ telemetry) | 20 USD |
| M9 | Tóm tắt incident bằng LLM (vài trăm) | 1 USD | 2 USD |
| M10–M12 | Demo offline từ cache; đánh giá bằng người | 0 | 1 USD |
| Dự phòng | Chạy lại do lỗi pipeline / đổi prompt | 8 USD | — |
| **Tổng** | | **≈ 33 USD** (≈ 24 nếu V27 chọn "chỉ telemetry") | |

**Đã tiêu (ước tính theo token, không phải billing; không gồm request lỗi, retry, request bị ngắt):**
M4 ≈ 8,6 USD; M5 ≈ 9,48 USD / 6.988 lần gọi: 2026-10-29 ≈ 8,47 USD (`ref_flat` 1,77, `order_rev` 1,77,
`time_0/33/67` 0,80 / 0,75 / 0,76, `near_trace` 0,84, `near_log` 0,89, `neighbor_trace` 0,876 tính từ
`usage` trong cache), 2026-11-01 1,0093 USD (`neighbor_trace` 0,0016, `repeat` 1 0,5022, `repeat` 2 0,5056).

**Quy tắc (áp cho mọi mốc):**
1. Trước mỗi lần chạy có gọi API: ước số lần gọi mới (trừ phần trúng cache) × đơn giá theo **token của
   đúng loại prompt** — không dùng đơn giá của run khác loại (bài học QĐ-026).
2. Điều kiện / config mới: chạy thử một điều kiện trước, đọc `runtime.json` (`estimated_usd_by_tokens`),
   rồi mới chạy phần còn lại.
3. Một mốc chạm **ngưỡng dừng** ⇒ dừng, báo người dùng, không tự chạy tiếp.
4. Ghi chi phí thực của mỗi lần chạy vào experiment-log (QĐ của mốc) và cập nhật dòng "Đã tiêu" ở đây.
5. Người dùng đặt spend cap ở AI Studio ≈ 40 USD làm chốt chặn cuối.

---

## Ghi chú bàn giao — phiên 2026-11-01

**Trạng thái:** M5 đóng (QĐ-028, QĐ-029, `h1_val_analysis_v2`): H1 giữ một phần, V28 (b). M6 đã mở,
M6 việc 1 dừng ở QĐ-030: baseline `dev` phủ ≈ 32% span trên `val`, chờ V30. Đính chính M4 (JSON bị cắt
1/5.677) đã ghi ở QĐ-028.
**Việc đầu tiên phiên sau:** hỏi V30, kết quả báo GVHD (V29) và số billing cho V26. Không làm M6 việc 2
trước khi có V30.

## Ghi chú bàn giao — phiên 2026-10-29

**Trạng thái:** V24 chốt (b), GVHD đồng ý ⇒ M4 QUA; M5 mở. Code H1 (`eval/harness/h1.py`,
`scripts/h1.py`, `tests/test_h1.py`, `eval/configs/h1_val.yaml`), mẫu `eval/samples/h1_val_v1.json.gz`
và 8 run `eval/results/h1_val_*` **chưa commit**. Người dùng bảo dừng giữa lúc chạy `neighbor_trace`.
Sơ bộ: `ref_flat` − `ref` trên normal +0,020 [+0,001; +0,042], McNemar p = 0,06 (điểm hiển thị gần như
không đổi hành vi judge). Cần sửa ghi chép M4: lỗi duy nhất ở `h0_val_c1_k0_v1` là **JSON bị cắt
(1/5.677)**, không phải lỗi mạng; V21 (a) vẫn đủ.
**Việc đầu tiên phiên sau:** hỏi người dùng có chạy tiếp không; nếu có: `neighbor_trace` →
`repeat` 1, 2 (`--subset 200`) → `py scripts/h1.py analyze` → báo cáo M5, QĐ-028, commit.

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
