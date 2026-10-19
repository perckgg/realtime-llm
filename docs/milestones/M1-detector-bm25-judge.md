# M1 — Sửa detector, hợp đồng dữ liệu, port BM25 + judge

| | |
|---|---|
| Ngày đóng mốc | 2026-10-19 |
| Hạn mục tiêu | 2026-10-25 (sớm 6 ngày) |
| Kết luận | **QUA** — DoD đạt đủ; 3 quyết định mới cần bạn chốt (§3), trong đó V7 cần trước khi viết harness M2 |
| Commit | `d1c5056` (việc 1), commit M1 việc 2–5 (cùng commit với báo cáo này) |
| Quyết định liên quan | QĐ-015 (việc 1), QĐ-016 (việc 2–5) |

## 1. Kết quả hiện tại

| DoD | Đạt? | Bằng chứng |
|---|---|---|
| `pytest`, `mypy packages services`, `ruff check .` sạch | Đạt | 86 test pass (48 → 86); mypy 26 file sạch; ruff sạch |
| Một candidate dev đi hết BM25 → judge (mock và Gemini thật) → `JudgedAlert` có `debug` | Đạt | `py scripts/judge_smoke.py --run-id m1-judge-smoke --candidates 3` và `... m1-judge-smoke-fault --candidates 2 --fault-only` → `eval/results/m1-judge-smoke*/{retrieval,judged}.jsonl`; 5 candidate × 2 backend; `debug` có `model_version`, `cache_key`, token, `raw_response` |
| Unit test: cache key, không rò fault type, `require_evidence`, điền metric thiếu, lịch sử buffer liên tục | Đạt | `tests/test_judge.py`, `tests/test_bm25_hybrid.py` (mới); `tests/test_isolation_forest_detector.py` (QĐ-015) |
| QĐ-015 ghi D1/D2 trước/sau | Đạt | `docs/experiment-log.md` QĐ-015 |
| Báo cáo 4 phần | Đạt | File này |

Việc đã làm (chi tiết QĐ-016):

| Việc | Output |
|---|---|
| 1. Sửa detector D1–D6 | QĐ-015 (phiên trước) |
| 2. 4 Protocol + model retrieval/judge có trường CTAV | `packages/schemas/protocols.py`, `models.py`; `03` §1.2–1.4, §1.6, §6 cập nhật |
| 3. Kho bằng chứng log/trace | `packages/schemas/evidence.py` — toàn bộ `rca_data` (8,3 M event), định dạng doc GĐ1 |
| 4. BM25 hybrid, bỏ fault type | `services/retrieval/bm25_hybrid.py`, `registry.py` |
| 5. Judge | `services/judge/{prompt,cache,backends,llm_judge,registry}.py` |
| + Migration CTAV ClickHouse | `infra/clickhouse/migrations/001_ctav_columns.sql` (đã áp, idempotent) |
| + Công cụ tái lập GĐ1 | `scripts/dump_gd1_prompts.py`, `scripts/check_gd1_parity.py`, `scripts/evidence_coverage.py` |

**Bảng M1-1. Port GĐ2 so với GĐ1 trên 489 lần gọi LLM của paper** (`paper_500`, BM25, full budget).

| Kiểm tra | Khớp |
|---|---|
| Chạy lại pipeline GĐ1, key prompt có trong cache Gemini của paper | 489 / 489 |
| Top-6 doc ID `bm25_hybrid` (chế độ parity) trùng GĐ1, đúng thứ tự | 489 / 489 |
| Chuỗi prompt và key cache GĐ2 trùng GĐ1 | 489 / 489 |
| Verdict `LLMJudge` GĐ2 từ cache: TP / FP / F1 | 58 / 7 / **0,7030** = Table 1 của paper |

Nghĩa là nửa BM25 của cổng G-paper (M3) đã đạt ngay từ M1; M3 chỉ còn nửa topology.

**Bảng M1-2. Có bằng chứng hay không, theo nhãn** (cùng 489 candidate; `py scripts/evidence_coverage.py`).

| | Fault (98) | Normal (391) |
|---|---|---|
| Kho GĐ1/paper (lọc theo nhãn): top-6 không rỗng | 89 (90,8%) | 21 (5,4%) |
| Kho GĐ2 đầy đủ, `pool="window"`: top-6 không rỗng | 98 (100%) | 76 (19,4%) |
| Có file log/trace Nezha trong ±8 phút | 98 (100%) | 106 (27,1%) |

**Bảng M1-3. Split GĐ2: cửa sổ có file log/trace trong ±8 phút.**

| Split | Fault | Normal |
|---|---|---|
| dev | 149/149 (100%) | 4.881/19.167 (25,5%) |
| val | 209/209 (100%) | 7.427/28.689 (25,9%) |
| test | 346/346 (100%) | 11.639/46.503 (25,0%) |

Nezha chỉ có log/trace cho ~303 phút quanh các lần tiêm lỗi; metric thì liên tục. Nên
"có bằng chứng" gần như là "gần sự cố" — ở paper (do dataset + bộ lọc theo nhãn của GĐ1)
và **cả ở GĐ2 nếu chấm trên toàn split** (QĐ-016, Phát hiện 1).

**Bảng M1-4. Smoke 5 candidate dev** — xem QĐ-016-4. Gemini: 4 FALSE_POSITIVE, 1
TRUE_ALERT (fault cpu_contention); mock: 5 TRUE_ALERT (mock coi mọi span là "trace chậm").
Không đủ mẫu để kết luận chất lượng.

## 2. Cần review gì

| # | Kiểm gì | Ở đâu | Vì sao rủi ro |
|---|---|---|---|
| R1 | Chế độ `pool="window"` thay cho cách GĐ1 tìm toàn corpus rồi mới lọc thời gian; giới hạn bằng chứng ở `s_0` | `services/retrieval/bm25_hybrid.py:240` (`_corpus`), docstring đầu file | Đây là khác biệt có chủ đích lớn nhất so với GĐ1/paper; baseline BM25 của H0 sẽ khác BM25 của paper. Lý do: kho đầy đủ 8,3 M event làm cách GĐ1 gần như luôn ra 0 bằng chứng. Hệ quả tốt: BM25 = "tầng 1 cục bộ" đúng định nghĩa CTAV |
| R2 | Luật quyết định của judge (thứ tự: lỗi → evidence → ngưỡng 0,80); ID bằng chứng bịa không được tính | `services/judge/llm_judge.py:88-185` (`evaluate`); `03` §1.4 | Khác GĐ1 ở 2 điểm: JSON lỗi ⇒ UNCERTAIN (GĐ1: route_alert); `require_evidence` chỉ tính ID có trong context (GĐ1: chỉ cần list không rỗng). Trên cache paper hai điểm này không đổi kết quả nào (0 JSON lỗi, 0 ID bịa) |
| R3 | Key cache: `repeat = 0` cho đúng key GĐ1, `max_output_tokens = 1024` mặc định | `services/judge/cache.py:24`, `backends.py:115` | Đổi `max_output_tokens` (GĐ1 config gốc ghi 512, run paper dùng 1024) là mất toàn bộ cache. Test `test_cache_key_is_gd1_key_for_repeat_0_and_new_for_repeat_n` chặn |
| R4 | Định dạng doc log/trace (doc id, timestamp µs, message trace) | `packages/schemas/evidence.py:100` (`log_doc`), `:124` (`trace_doc`) | Lệch một ký tự là prompt khác ⇒ cache miss ở M3. Đã so trực tiếp với `_log_event`/`_trace_event` GĐ1 (`tests/test_evidence.py`) |
| R5 | Số liệu Phát hiện 1 và 2 trước khi đưa vào luận văn (đặc biệt: Nezha thật sự không có log/trace ngoài ~303 phút — mở `data/Nezha/rca_data/2022-08-22/log/` xem danh sách file) | `py scripts/check_gd1_parity.py`, `py scripts/evidence_coverage.py`; QĐ-016 | Hai phát hiện này đổi cách kể chuyện về paper (§3 V7, V8) — nên tự chạy lại và xem vài ca |
| R6 | `NezhaEvidenceStore` dùng tên file `HH_MM` để chọn file, lọc chính xác theo timestamp | `packages/schemas/evidence.py:217` (`NezhaEvidenceStore`), `:265` (`query`) | Mỗi file chứa ~1 phút **trước** tên của nó, chồng lấn vài giây; nếu giả định sai sẽ mất bằng chứng ở mép cửa sổ. Đã kiểm 6 file thật; test có ca chồng lấn |

## 3. Vấn đề cần bạn giải quyết

| # | Vấn đề | Phương án | Khuyến nghị | Chặn mốc sau? |
|---|---|---|---|---|
| V7 | **Có bằng chứng ⇔ gần sự cố** (Bảng M1-2, M1-3). Nezha chỉ có log/trace quanh lần tiêm lỗi: 100% fault nhưng chỉ ~25% normal của `val`/`test` có log/trace trong ±8 phút. Ở paper (thêm bộ lọc theo nhãn của GĐ1) 95% normal không có bằng chứng ⇒ FP = 7 của BM25 chủ yếu do `require_evidence` chặn normal "trống", không do BM25 chọn tốt. Nếu GĐ2 chấm trên toàn split, ~75% normal được "đúng" một cách tầm thường và mọi so sánh BM25/topology/CTAV bị pha loãng | (a) Kết quả chính chấm trên **cửa sổ có telemetry đầy đủ** (có file log/trace trong ±8 phút): `val` 209 fault + 7.427 normal (~1:36), `test` 346 + 11.639; báo cáo toàn split làm số phụ. (b) Toàn split như mặc định Q2 cũ, ghi hạn chế. (c) Tập cố định kiểu `paper_500` nhưng chỉ lấy normal có telemetry | **(a)** — nó cũng trả lời luôn Q2 (giảm ~4× số candidate ⇒ chi phí API). Luận văn nêu hiện tượng này như hạn chế của giao thức paper và lý do của giao thức GĐ2. Nên báo GVHD cùng mail V1 | **Chặn thiết kế harness M2** (mask "có telemetry" là một cột của kết quả) — cần chốt trước khi viết `runner.py` |
| V8 | **Confidence của Gemini là `anomaly_score` chép lại** (74,6% bằng đúng). C2 (gating theo confidence) mất cơ sở nếu giữ prompt nguyên văn | (a) Giữ prompt nguyên văn cho mọi biến thể; C2 gating trên tín hiệu khác confidence (nguồn gốc bằng chứng, số bằng chứng neo, span lỗi); (b) bỏ `anomaly_score` khỏi prompt ở GĐ2 (mất so sánh trực tiếp với paper, phải ghi là thay đổi prompt); (c) lấy log-prob của nhãn từ API làm confidence | **(a)**, và đo thêm (c) trên `val` ở M4 như một ablation. Cần chốt trước M6; nên có ý kiến GVHD | Không chặn M2/M3; chặn thiết kế C2 (M6) |
| V9 | `top_features` rỗng và metric snapshot là 19 metric thô (GĐ1: 6 đặc trưng tổng hợp + top-3 đặc trưng lệch) | (a) Port cách tính top-3 đặc trưng lệch của GĐ1 vào detector GĐ2; (b) để nguyên | **(a)** ở M2 (nhỏ, làm cùng harness) để prompt GĐ2 có cùng loại thông tin như GĐ1 trước khi chạy H0 | Không chặn M2; phải xong trước M4 |
| V1–V6 | Như ghi chú bàn giao trước (mail GVHD, Q2, Q5, file `legacy/` chưa commit, file rác gốc repo, câu "LLM không RAG thất bại" là số mock) | | Không đổi | V1 nên trước M4 |

## 4. Plan cho mốc tiếp theo (M2 — eval harness + G-port)

Việc, theo thứ tự (`04` M2):

1. `eval/harness/runner.py` — đọc config, replay → detector → retrieval → judge, ghi `eval/results/<run_id>/` (6 file `02` §3.3) + ClickHouse (cột CTAV đã có); từ chối `run_id` đã tồn tại.
2. `eval/harness/metrics.py`, `stats.py` — P/R/F1/FPR/coverage/latency/token/chi phí; bootstrap CI + McNemar cặp.
3. `scripts/map_gd1_windows.py` — `paper_300` (cửa sổ GĐ1 120 s) → `window_id` GĐ2.
4. `eval/configs/gd1_phase4_parity.yaml` — dùng chế độ parity đã có (`pool="global"`, corpus GĐ1, judge mock). `scripts/dump_gd1_prompts.py --split paper_300` cho đầu vào từng tầng.
5. V9: top-3 đặc trưng lệch trong detector; phần còn lại của D6 (config `buffer_size`, bỏ `packages` → `scripts`).
6. Đếm candidate thật trên `val` → chi phí API mỗi run → chốt Q2.

DoD (`04` M2): G-port so từng tầng — retrieval 40 candidate trùng doc ID (công cụ đã có, chỉ
cần chạy trên dump Phase 4), judge mock trùng verdict, toàn pipeline P 0,3158 / FPR 0,0458 /
recall 0,375 (lệch ≤ 1 cửa sổ mỗi ô).

Rủi ro đã biết: G-port là cấu hình Phase 4 (`experiment_phase4_benchmark.yaml`, threshold
0,95, ngân sách 30), khác Step 7; `dump_gd1_prompts.py` hiện chỉ hỗ trợ split Step 7 — cần mở
rộng. Đơn vị cửa sổ 120 s vs 60 s (QĐ-009) chỉ ảnh hưởng tầng toàn pipeline.

## Phụ lục

**Sai lệch so với plan.**
- Thêm `JudgedAlert.debug` và 4 trường `AlertCandidate` (pod, end_ts, metric_snapshot, top_features) — có chỗ dùng cụ thể, đã ghi `03`.
- `03` §6 viết cache key là `sha256(prompt + model + temperature + max_tokens)`; thực tế GĐ1 là `sha256(provider|model|prompt|max=..|t=0)`. Đã sửa `03` theo GĐ1 vì yêu cầu trúng cache.
- Ngưỡng confidence 0,80 của GĐ1 đặt trong `LLMJudge` (đối xứng) tới khi `policy.py` (M6) thay thế.
- Làm sớm một phần M3: kiểm chứng nửa BM25 của G-paper (Bảng M1-1).

**Nguyên liệu cho luận văn.**
- Bảng M1-1 (tái lập paper từ cache, chứng minh port đúng) — chương Thực nghiệm, mục tái lập.
- Bảng M1-2, M1-3 + Phát hiện 2 — chương Bài toán / Hạn chế của nghiên cứu trước; là động lực cho CTAV và cho giao thức đánh giá mới.
- Mô tả `bm25_hybrid` (công thức, hai khác biệt có chủ đích) — chương Phương pháp, mục baseline (`01` §6.3).
- Luật quyết định của judge — chương Phương pháp (`03` §1.4).

**Lệnh tái lập M1.**

```bash
docker compose --profile dev up -d
py scripts/apply_clickhouse_migrations.py
py -m pytest tests/ -q                                   # 86 test
py scripts/dump_gd1_prompts.py                           # 489 prompt GĐ1, ~85 s
py scripts/check_gd1_parity.py                           # Bảng M1-1, ~30 s
py scripts/evidence_coverage.py                          # Bảng M1-2
py scripts/judge_smoke.py --run-id <mới> --candidates 3  # cần GEMINI_API_KEY nếu cache miss
```
