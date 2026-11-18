# Bộ prompt cho M8 → M12 (cập nhật 2026-11-16 theo trạng thái QĐ-037)

Mỗi khối ```` ```text ```` bên dưới là một prompt dán nguyên vào một phiên làm việc mới mở tại
`C:\Working\Internship1`. Prompt nào cũng bắt agent đọc **§0 của file này** trước, nên không cần dán §0.

Mục tiêu của cách chia này: báo cáo luận văn không phải chờ sản phẩm. Phần thực nghiệm (M8, M9) và phần
viết chạy song song; platform (M10) chỉ chặn Chương 6.

## Thứ tự chạy và làn song song

| Làn | Prompt | Bắt đầu khi | Chặn gì | Cần bạn làm |
|---|---|---|---|---|
| A | **P1 — tiếp tục M8 G-test** | **Ngay** (tiếp từ `h0_test_norag_v2` — 370 câu còn lại) | Ch5 (§5.7.4–5.8), M9-B | Xem báo cáo M8; chấm 50 cửa sổ (V35, không chặn); tự xử lý báo GVHD (V29) |
| B | **P2 — M9-A (RCA trên `val`)** | **Ngay**, song song với P1 (bật Docker trước khi chạy) | M9-B, M10 | Xem cấu hình `rca_final.yaml` chốt trước khi chạy `test` |
| C | **W — viết Ch1, Ch2, Ch3, Ch4** | **Ngay**, song song (tối đa 3 phiên, mỗi phiên một chương) | — | Đọc duyệt từng chương |
| A | **P3 — M9-B (H5 trên `test`)** | M8 đóng (`M8-g-test.md` + `CURRENT-MILESTONE` ghi M8 QUA) **và** P2 xong | Ch5 (§5.9), M10 dữ liệu thật | Xem báo cáo M9 |
| C | **W — viết Ch5** | §5.1–5.6 và khung §5.7.1–5.7.3 ngay; §5.7.4–5.8 khi P1 đóng; §5.9 sau P3 | — | Đọc duyệt |
| B | **P4 — M10 platform** | P2 xong (dựng trên `val`); nạp `test` sau P3 | Ch6, demo | Chạy thử demo |
| A | **P5 — M11 đánh giá người + ca sai** | P3 xong | Ch7 (§7.4) | **Chấm incident** (việc dài nhất của bạn, tối thiểu 15/30) |
| C | **W — viết Ch6, Ch7, Ch8, phần đầu** | P4, P5 xong | — | Đọc duyệt |
| A | **P6 — M12 đóng gói** | Mọi thứ trên xong | Nộp | Công khai repo, lắp Word, slide |

Hai làn không bao giờ chạy cùng lúc trên cùng file: xem bảng "vùng file" ở §0.4.

**Ba lựa chọn rút ngắn đường găng — đã được người dùng chốt ở QĐ-037 (2026-11-16):**

1. **Chạy song song P1 / P2 / W.** `04` §2 nói xong mốc này mới sang mốc sau. P2 chỉ dùng `val`, W chỉ viết
   văn, nên không cổng chặn nào bị vượt; người dùng đã duyệt ở QĐ-037 (P2 vẫn ghi QĐ-040 dẫn chiếu QĐ-037).
2. **H5 tính ngay ở M9-B, không đợi platform M10.** `04` đặt "kết quả chính thức H5" ở M10. Bản đăng ký chỉ
   ghi "chạy sau M9", nên P3 chạy H5 một lần qua harness; M10 phải tái lập đúng các incident đó (kiểm parity),
   chỉ đo thêm độ trễ.
3. **Áp dụng sẵn 3 ưu tiên cắt theo `04` §9:** cắt `propagation.py` mức 2 (ưu tiên cắt 1) và màn hình `ExperimentComparison` động thành bảng tĩnh (ưu tiên cắt 4).
   Đánh giá người (M11): agent chuẩn bị đủ 30 incident xếp ngẫu nhiên, bạn chấm tối thiểu 15 incident đầu là đã hợp lệ (ưu tiên cắt 3).

---

## §0. Quy tắc chung (agent đọc trước khi làm bất kỳ prompt nào)

### 0.1 Đọc gì
`AGENTS.md` → `docs/CURRENT-MILESTONE.md` → **chỉ** phần mốc của mình trong
`docs/Final_Thesis_Phase2/04-implementation-roadmap.md` → mục "Đăng ký giả thuyết H0–H5" cuối
`docs/experiment-log.md`. Tài liệu khác chỉ mở khi prompt chỉ tới. Chạy Python bằng `py`.

### 0.2 Bất biến không được phá
- Mục "Đăng ký giả thuyết H0–H5" (commit `be2b985`) **không sửa một ký tự**. Không tham số nào của phương
  pháp được đổi sau khi đã thấy số `test`. Mọi lệch khi chạy ghi thành QĐ mới.
- `test` chỉ chạy **đúng danh sách config đã đăng ký**, mỗi config một lần. Lỗi pipeline / judge ⇒ `run_id`
  mới, chỉ hỏi lại câu lỗi qua cache, không đổi tham số.
- Không ghi đè `eval/results/`. Mọi lời gọi LLM qua cache `data/llm_cache/gemini.jsonl` (không commit, không xoá).
- Ngân sách API: 5 quy tắc ở `docs/CURRENT-MILESTONE.md`. Chạm ngưỡng dừng của mốc ⇒ dừng, báo người dùng.
- Kết quả xấu vẫn báo đúng như nó là. Không chọn lại chỉ số, tập con hay ngưỡng để kết quả đẹp hơn.
- Không thêm gì ngoài `06-scope-guard.md` §3; ý hay ghi vào `docs/ideas.md`.

### 0.3 Khi nào dừng hỏi, khi nào tự quyết
Chỉ dừng hỏi khi: (a) chạm ngưỡng dừng ngân sách; (b) muốn làm khác bản đăng ký; (c) việc cần người chấm tay;
(d) thao tác khó hoàn tác (xoá dữ liệu, push, công khai). Còn lại **tự quyết, làm tiếp**, và ghi quyết định đó
vào báo cáo mốc §3 dưới dạng "agent tự quyết — chờ người dùng xác nhận" kèm phương án đã bỏ (tiền lệ: V30).

### 0.4 Vùng file khi nhiều phiên chạy song song
| Phiên | Được tạo / sửa | Số QĐ, số V dành riêng |
|---|---|---|
| P1 (M8) | `eval/configs/*test*`, `eval/results/*test*`, `eval/manual/context_precision*`, `eval/harness/`, `scripts/` (file mới tên `m8_*`), `docs/milestones/M8-*`, `docs/drafts/ch5-ket-qua-test.md` | QĐ-038..039, V36..V39 *(QĐ-035..037 đã ghi)* |
| P2, P3 (M9) | `services/rca_agent/`, `eval/harness/rca*.py`, `eval/configs/rca_*`, `eval/results/rca_*`, `tests/test_rca_*`, `tests/test_grouping.py`, `docs/milestones/M9-*`, `docs/drafts/ch5-rca-val.md` | QĐ-040..044, V40..V44 |
| P4 (M10) | `services/api/`, `services/web/`, `services/rca_agent/pipeline.py`, `docker-compose.yml`, `docs/milestones/M10-*`, `docs/drafts/ch6-demo-platform.md` | QĐ-045..049, V45..V49 |
| P5 (M11) | `eval/manual/diagnostic_quality*`, `scripts/m11_*`, `docs/milestones/M11-*`, `docs/drafts/ch7-phan-tich-ca-sai.md` | QĐ-050..052, V50..V52 |
| W (viết) | `docs/drafts/ch<N>-*.md`, `docs/drafts/tai-lieu-tham-khao.md`, `docs/drafts/figures/` | không có |

File dùng chung (`docs/experiment-log.md`, `docs/CURRENT-MILESTONE.md`, `04` §1, `docs/milestones/README.md`):
chỉ **thêm** nội dung, đọc lại file ngay trước khi sửa, sửa gọn một lần. Số QĐ không dùng hết thì bỏ trống.
Phiên W không sửa code, config, kết quả hay nhật ký. Hai phiên không cùng gọi Gemini thật: phiên không phải P1
dùng backend `mock` cho tới khi M8 xong phần API. "Xong phần API" = ghi chú bàn giao ở `CURRENT-MILESTONE.md` có
dòng `"M8: xong phần API"`, **hoặc** cả 8 run sau đều có `metrics.json` trong `eval/results/`: `h0_test_bm25_*` *(đã có)*,
`h0_test_c1_k0_*` *(đã có)*, `h0_test_norag_*` *(còn `_v2`)*, `m8_rescue_test_c1_*`, và bốn run `h0_test_{bm25,c1_k0}_rep{1,2}_*`.
Phiên P2 cần thêm lệnh con `rca` vào `eval/__main__.py` (file P1 cũng có thể sửa): chỉ thêm, không đổi dòng có sẵn.

### 0.5 Cuốn chiếu
Việc nào xong cũng phải kèm nguyên liệu dán được vào luận văn: bảng đánh số, số đếm cụ thể, phương pháp, seed,
lệnh tái lập. Ghi rõ từng con số thuộc `val` hay `test`, cửa sổ telemetry hay mọi cửa sổ. Bản nháp chương là
Markdown trong `docs/drafts/`; **không tạo .docx**.

### 0.6 Đóng việc
- Trước khi commit: `py -m pytest tests/ -q`, `py -m mypy packages services`, `py -m ruff check .` (E402 cũ ở
  `scripts/` được phép). Tự kiểm logic, không chỉ kiểm "có file". `tests/test_storage.py` cần
  `docker compose --profile dev up -d` (Docker đang tắt lúc kiểm kê 2026-11-16); phiên nào ghi ClickHouse / Postgres (P2, P3,
  P4) phải bật Docker và chạy cả test này, phiên khác được bỏ qua nhưng phải ghi rõ là đã bỏ qua.
- Tự commit khi kiểm sạch; `git add` **từng đường dẫn của mình**. Không add các file đang bẩn sẵn (4 file
  `legacy/` đang sửa, file chưa track ở gốc repo và `docs/` — V4–V6) và không add file của phiên khác. Không
  `git stash`, không `git checkout` / `reset` trên file không phải của mình: phiên khác đang làm trên cùng thư mục.
  Không push.
- Đóng mốc = DoD đạt + báo cáo `docs/milestones/M<n>-*.md` đủ 4 phần theo `docs/milestones/README.md` + cập nhật
  `CURRENT-MILESTONE.md`, bảng `04` §1, bảng `milestones/README.md` + ghi chú bàn giao.
- Câu trả lời cuối của phiên: kết quả chính (số), cái gì chưa làm / chưa kiểm, và việc bạn cần làm.

---

## P1 — M8: cổng chặn G-test (tiếp tục từ trạng thái kiểm kê 2026-11-16)

**Trạng thái kiểm kê 2026-11-16** (từ `git log`, `eval/results/`, `data/llm_cache/gemini.jsonl`, `QĐ-035..037`, `a5e74bd`):

| Việc M8 | Trạng thái |
|---|---|
| 1. Config `test` #1–#8 | **Xong** (`30f3f92`, `e6a71cb`, `48ee7f5`, subset 200 cửa sổ `df6aa53`) |
| 2. Đếm candidate + độ lệch detector | **Xong** (`a6d044f`, `7d53275`, QĐ-035, QĐ-036): 13.699 candidate / 46.849 cửa sổ (29,2%) |
| 3. `h0_test_bm25_v1` | **Xong** (`da2bb91`): 13.699 lần gọi API mới, 0 lỗi, **8,87 USD theo token** |
| 4. `h0_test_c1_k0`, `h0_test_norag`, 3 bản `_b120` | `h0_test_c1_k0_v1` **xong** (`0c7689e`: 3.299 gọi mới, 0 lỗi, **4,71 USD**; **H0 đạt cả 4 vế** — QĐ-037). `h0_test_norag_v1` **dở ở 2.917/3.287** câu mới (0,97 USD trong cache, thư mục `_v1` rỗng ⇒ chạy tiếp `h0_test_norag_v2` cho 370 câu ≈ 0,12 USD). Ba bản `_b120` chờ `norag_v2` (0 USD) |
| 5. `m8_anchor_features_test`, `ctav_final_test` | `m8_anchor_features_test_v1` **xong** (`cb191d5`, 0 USD). Còn `ctav_final_test` + `scripts/m8_finding11.py` (0 USD) |
| 6–9. C5, `repeat` ×4, `compare` + bảng H0–H4, mẫu V35 | Chưa chạy (script `scripts/m8_tables.py`, `scripts/m8_finding11.py`, `scripts/m8_context_precision_sample.py` đã viết sẵn) |
| 10. Báo cáo `M8-g-test.md` + nháp Ch5 + mail GVHD | Đã có §5.7.1–5.7.3 ở `docs/drafts/ch5-ket-qua-test.md` (`cb191d5`); còn §5.7.4–5.8, `M8-g-test.md` và mail GVHD |

**Chi phí và cache hiện tại (QĐ-037):**
- Cache `data/llm_cache/gemini.jsonl` hiện có **39.072 dòng** (tăng 19.915 dòng từ mốc 19.157 đầu M8).
- Đã tiêu ở M8: **14,55 USD theo token** (`bm25` 8,87 + `c1_k0` 4,71 + `norag_v1` dở 0,97).
- Phần gọi API còn lại (`norag_v2` 370 câu ≈ 0,12 + C5 một điểm ≈ 0,1–0,3 + `repeat` ×4 ≈ 1,00): ước **≈ 1,2–1,5 USD theo token** ⇒ tổng M8 ≈ 15,8–16,0 USD theo token. Người dùng đã đồng ý chạy tiếp dù quy đổi billing có thể vượt ngưỡng dừng 20 USD (QĐ-037).

### P1 — Prompt chạy tiếp và đóng M8 ở phiên mới

```text
Đọc docs/prompts/M8-M12-prompts.md §0 và mục P1 (bảng trạng thái kiểm kê 2026-11-16) rồi tiếp tục hoàn tất M8.
Tuyệt đối không làm lại các việc đã xong (config, đếm candidate, độ lệch detector QĐ-036, h0_test_bm25_v1,
h0_test_c1_k0_v1, m8_anchor_features_test_v1, hay phần §5.7.1–5.7.3 đã viết trong docs/drafts/ch5-ket-qua-test.md).
Có phiên M9-A và phiên viết chương chạy song song; M8 dùng QĐ-038..039, V36..V39 (QĐ-035..037 đã ghi).

1. Kiểm nhanh trạng thái trước khi chạy API: bảo đảm không còn tiến trình `py -m eval` nào đang chạy nền; xác nhận
   `data/llm_cache/gemini.jsonl` ở mốc ≥ 39.072 dòng và giữ nguyên thư mục `eval/results/h0_test_norag_v1/` rỗng
   (không xóa, không ghi đè).
2. Hoàn tất phần gọi API theo đúng thứ tự:
   a) Đổi `run_id` trong `eval/configs/h0_test_norag.yaml` sang `h0_test_norag_v2` rồi chạy
      `py -m eval run --config eval/configs/h0_test_norag.yaml` (chỉ gọi API nốt 370 câu còn thiếu ≈ 0,12 USD).
   b) Đổi `baselines.norag` trong `eval/configs/ctav_final_test.yaml` sang `h0_test_norag_v2` (chỉ đổi tên run đầu vào bị ngắt, không đổi tham số), rồi chạy `py -m eval ctav --config eval/configs/ctav_final_test.yaml` (0 USD, để lấy tập cảnh báo A của CTAV cho C5).
   c) Chạy C5 một điểm trên `test`: `m8_rescue_features_test.yaml` → `m8_rescue_plan_test.yaml` →
      `m8_rescue_test_c1.yaml` (≈ 0,1–0,3 USD) → `m8_anchor_features_rescue_test.yaml` → `m8_rescue_test.yaml`.
      (Thiết kế tập A không lan truyền dây chuyền và vị trí file `rescue_features.parquet` đã được chốt ở QĐ-037.)
   d) Chạy `repeat` 1, 2 trên tập con 200 cửa sổ: `h0_test_{bm25,c1_k0}_rep{1,2}.yaml` (800 lần gọi ≈ 1,0 USD).
   e) Ngay khi xong (a)–(d) không lỗi: thêm dòng `"M8: xong phần API"` vào ghi chú bàn giao của
      `docs/CURRENT-MILESTONE.md` để mở khóa gọi Gemini thật cho phiên M9-A.
   Chỉ dừng hỏi nếu chi phí lũy kế tăng bất thường (tính thêm từ dòng cache > 39.072 vượt quá +4 USD) hoặc gặp lỗi
   không tự chạy lại được / nghi ngờ bug ở code phương pháp.
3. Chạy các bước phân tích 0 USD (sau bước 2, không dừng hỏi):
   - Ba bản `_b120`: `h0_test_{bm25,c1_k0,norag}_b120.yaml` (100% cache).
   - Kiểm tra rủi ro Phát hiện 11 trên `test`: `py scripts/m8_finding11.py --ctav ctav_final_test_v1 --c1 h0_test_c1_k0_v1 --out m8_finding11_test_v1`.
   - `py -m eval compare` (cả bản tham chiếu `bm25` gồm bm25, c1, norag, ctav, detector-only và bản tham chiếu `c1` gồm c1, ctav) + `py scripts/m8_tables.py` xuất đủ bảng H0–H4 có CI và McNemar theo đúng tiêu chí đã đăng ký.
   - Việc 9 (V35, đã chốt ở QĐ-037): chạy `py scripts/m8_context_precision_sample.py` xuất 50 cửa sổ có telemetry
     (`seed 42`, cân theo phương pháp, ẩn nhãn và phương pháp) ra `eval/manual/context_precision_test_v1.csv` kèm
     hướng dẫn chấm ≤ 1 trang. Người dùng chấm sau — không chặn đóng M8.
4. Viết & cập nhật tài liệu đóng M8 (theo §0.5 và `docs/drafts/ch5-outline-ket-qua-test.md`):
   - Hoàn tất §5.7.4–§5.8 trong `docs/drafts/ch5-ket-qua-test.md` (giữ nguyên §5.7.1–5.7.3 đã có, chỉ thêm/điền nốt
     dòng chờ trong Bảng 5.14a và các mục ⏳): có đủ bảng `val` cạnh `test`, bảng từng vế đạt/không đạt H0–H4,
     ablation H3 (bỏ C3, +C2, +C4, C3-trượt, C5 một điểm), kiểm Phát hiện 11, đường F1 theo ngân sách, độ lệch
     `repeat` 0/1/2 và chi phí thực so với ước QĐ-035. Kết luận H2 viết thẳng theo tiêu chí đăng ký dù kết quả là gì.
   - Viết báo cáo `docs/milestones/M8-g-test.md` đủ 4 phần (ghi V35 "chờ người dùng chấm" ở §3), cập nhật bảng/tick
     trong `docs/CURRENT-MILESTONE.md`, `docs/experiment-log.md` (QĐ-038..), `docs/milestones/README.md`, `04` §1.
   - Soạn `docs/drafts/<ngày>-mail-gvhd-gtest.md`: tóm tắt 1 trang cho GVHD (`04` §10). Chỉ soạn, không gửi.
```

## P2 — M9-A: RCA Agent trên `val` (chạy song song với P1)

```text
Đọc docs/prompts/M8-M12-prompts.md §0 rồi làm phần val của M9. Bạn là phiên P2, chạy song song với phiên M8
(đã được người dùng chốt cho chạy song song và áp dụng cắt giảm ở QĐ-037). Lưu ý bật Docker Desktop và chạy
`docker compose --profile dev up -d` trước khi ghi PostgreSQL và chạy `tests/test_storage.py`.
Tuyệt đối không đọc, không chạy, không tạo gì liên quan tới split test. Ghi QĐ-040: M9-A chạy song song M8
(dẫn chiếu QĐ-037, người dùng giao qua prompt này), chỉ dùng val.

Đọc thêm: 01-architecture-design.md §6.5, 02-data-and-experiment-protocol.md §4.3, 03-schemas-and-contracts.md
§1.5, §2, §4; dòng H5 của bản đăng ký. Code đã có: services/rca_agent/grouping.py, tests/test_grouping.py.

Đầu vào: cảnh báo CTAV trên val = replay ctav_final.yaml trên các run h0_val_* đã cache (0 USD).

Việc:
1. Harness RCA: py -m eval rca --config ... đọc cảnh báo CTAV của một run, gom incident, định vị root cause, chấm
   Hit@1/Hit@3 mức service theo nhãn root-cause (QĐ-001), có CI bootstrap; ghi incidents vào PostgreSQL theo 03 §4.
2. Grouping: quét T_group ∈ {180, 300, 600} s trên val; Alert Reduction Ratio chung và riêng trên incident cascade
   / network_delay. Quy tắc chọn T_group viết vào code trước khi xem số.
3. Propagation mức 1: lan truyền ngược 1-hop thuần thuật toán. Baseline: service có anomaly score cao nhất trong
   incident. Báo cả hai, kèm ΔHit@1 ghép cặp có CI.
4. Propagation mức 2 (LLM full call chain): KHÔNG làm — đã chốt cắt theo 04 §9 ưu tiên 1 (QĐ-037). Ghi vào QĐ và báo cáo.
5. Summarizer: JSON theo 03 §2, validator + diagnostic_rejected, require_evidence, chặn câu lệnh thực thi. Viết và
   test bằng backend mock trước. Chỉ gọi Gemini thật khi M8 đã xong phần API theo đúng điều kiện ở §0.4 (hiện M8
   còn h0_test_norag_v2, C5 một điểm và repeat ×4); ngân sách 1 USD, ngưỡng dừng 2 USD. Nếu M8 chưa xong phần API thì
   hoàn tất mọi việc khác và ghi phần này là "chờ M8" ở báo cáo.
6. Chốt eval/configs/rca_final.yaml (T_group, quy tắc xếp hạng, prompt summarizer) và commit riêng. Sau commit
   này không đổi tham số RCA nữa — M9-B chạy test bằng đúng file này.

DoD (04 M9, đo trên val): ARR ≥ 30% trên network_delay; Hit@1/Hit@3 mức 1 và baseline; JSON valid rate ≥ 0,95.
Không đạt ngưỡng nào thì báo đúng con số, nêu nguyên nhân từ dữ liệu, không nới định nghĩa chỉ số.

Lưu ý mẫu nhỏ: CTAV trên val chỉ có 80 cảnh báo (29 TP, 51 FP; cửa sổ telemetry). Báo số incident, số incident có
nhãn root cause, và CI của mọi chỉ số; đừng chọn T_group dựa trên chênh lệch nằm trong CI — quy tắc chọn phải nêu
cách xử lý trường hợp hoà. Quy tắc gom và xếp hạng không được phụ thuộc vào số cảnh báo tuyệt đối, vì detector
trên test đưa lên nhiều candidate hơn val (29,2% so với 19,6% cửa sổ, QĐ-035) — bạn chỉ biết con số này, không
được mở kết quả test để xem thêm.

Đầu ra: bản nháp docs/milestones/M9-rca.md (phần val), QĐ-040.., docs/drafts/ch5-rca-val.md (bảng + đoạn văn cho
§5.9 và mô tả phương pháp RCA cho Ch4). Cuối phiên nêu rõ: cấu hình đã chốt, số val, và những gì M9-B cần.
```

## P3 — M9-B: H5 trên `test` (sau khi M8 đóng và P2 xong)

```text
Đọc docs/prompts/M8-M12-prompts.md §0 rồi hoàn tất M9. Điều kiện vào: docs/milestones/M8-g-test.md đã có và
CURRENT-MILESTONE ghi M8 QUA; eval/configs/rca_final.yaml đã commit. Thiếu một trong hai thì dừng, báo tôi.

Việc:
1. Tạo rca_final_test.yaml = rca_final.yaml chỉ đổi split / run đầu vào / run_id; in diff, commit trước khi chạy.
2. Chạy một lần: incident test gom từ cảnh báo CTAV của M8 (run test đã có, 0 lần gọi judge). Tính Hit@1, Hit@3,
   baseline anomaly score cao nhất, CI ΔHit@1, Alert Reduction trên incident cascade, JSON valid rate, số lần
   gọi + chi phí summarizer.
3. Kết luận H5 từng vế đúng theo bản đăng ký (Hit@1 ≥ 0,60; Hit@3 ≥ 0,80; cận dưới CI ΔHit@1 > 0; AR ≥ 30%).
   Báo kèm: số fault của test không có cảnh báo CTAV nào (không thể định vị), tách Hit@k "trên incident có
   cảnh báo" và "trên mọi lần tiêm lỗi" — ghi rõ con số nào là con số đăng ký.
4. Báo số cảnh báo CTAV, số incident, kích thước incident trên test cạnh val. Detector trên test đưa lên nhiều
   candidate hơn (QĐ-035), nên phân bố incident có thể khác val: mô tả khác biệt đó, không coi nó là lý do để chọn
   lại T_group hay quy tắc xếp hạng.
5. Ghi QĐ: H5 tính ở M9-B qua harness thay vì ở M10 (lệch 04 M10); M10 phải tái lập đúng tập incident này.

Đầu ra: docs/milestones/M9-rca.md hoàn chỉnh 4 phần; bổ sung §5.9 vào docs/drafts/ch5-ket-qua-test.md; cập nhật
CURRENT-MILESTONE sang M10. Sau khi thấy số test: không sửa rca_final.yaml, không chạy biến thể khác trên test.
```

## P4 — M10: platform end-to-end + dashboard (bắt đầu sau P2)

> **2026-11-17:** P4 đã được chia thành 5 prompt P4-A..P4-E (mốc con M10-A..E) ở `docs/prompts/M10-handoff.md` §6. Dùng các
> prompt đó; khối dưới đây giữ lại làm phạm vi gốc.

```text
Đọc docs/prompts/M8-M12-prompts.md §0 rồi làm M10. Đọc thêm: 01-architecture-design.md §6.5–6.7, §8;
03-schemas-and-contracts.md §3–4; 08-research-direction.md §6 (kịch bản demo); services/web/src/api/types.ts
và 4 màn hình trong services/web/src/screens/.

Việc:
1. services/rca_agent/pipeline.py: CTAV → grouping → propagation → summary, dùng rca_final.yaml, ghi ClickHouse /
   Postgres. Dựng và debug trên run val. Khi M9-B đã xong: chạy trên test và kiểm parity — tập incident và root
   cause xếp hạng phải trùng kết quả M9-B; lệch thì là bug pipeline, sửa pipeline, không sửa số đã báo cáo.
   Ghi runtime.json: độ trễ end-to-end, token, cache hit.
2. services/api (FastAPI): endpoint khớp đúng types.ts; chỉ đọc. Không authentication.
3. Nối Timeline, AlertDetail, IncidentDetail sang API thật: hiện nguồn gốc bằng chứng, lý do policy (θ, C3),
   có loading / empty / error state. Màn hình ExperimentComparison: bảng tĩnh sinh từ script đọc eval/results
   (cắt theo 04 §9 ưu tiên 4) — ghi QĐ.
4. Chế độ demo offline: toàn bộ kịch bản chạy từ cache, không cần mạng, không cần GEMINI_API_KEY.
5. Tự kiểm bằng trình duyệt thật: docker compose --profile dev up -d, replay, mở đủ 4 màn hình, đi hết kịch bản
   08 §6, rồi lặp lại khi đã tắt mạng. Chụp ảnh từng màn hình vào docs/drafts/figures/. Cái gì chưa mở lên xem
   được thì ghi là chưa kiểm.

DoD: 04 M10. Đầu ra: docs/milestones/M10-platform.md; docs/drafts/ch6-demo-platform.md (§6.1–6.5 theo sườn, kèm
ảnh, lệnh chạy, bảng độ trễ / token); danh sách lỗi demo còn lại xếp theo mức nghiêm trọng.
Không làm: Kubernetes, auth, notification, màn hình thứ 5, thư viện UI mới.
```

## P5 — M11: đánh giá bằng người + phân tích ca sai (sau P3)

```text
Đọc docs/prompts/M8-M12-prompts.md §0 rồi làm M11. Đọc thêm 02-data-and-experiment-protocol.md §4.4.

Việc:
1. scripts/m11_sample_incidents.py: lấy 30 incident test từ kết quả M9-B, seed 42, xếp thứ tự ngẫu nhiên sao cho
   15 dòng đầu tự nó là một mẫu ngẫu nhiên hợp lệ. Xuất eval/manual/diagnostic_quality.csv: mỗi dòng có báo cáo
   chẩn đoán, bằng chứng được trích, và 3 cột điểm trống theo đúng 3 tiêu chí của 02 §4.4; kèm hướng dẫn chấm ≤ 1
   trang có ví dụ cho từng mức điểm. Nhãn root cause thật để ở file riêng, không nằm trong bảng chấm.
2. Dừng ở đây, báo tôi chấm (tôi chấm tối thiểu 15 dòng đầu). Trong lúc chờ, làm việc 3.
3. Phân tích ca sai trên test — chỉ mô tả, không dẫn tới thay đổi tham số nào: phân loại toàn bộ FP còn lại của
   CTAV (theo service, loại bằng chứng, có/không có ngưỡng nền, verdict C1 gốc, và có rơi vào nhóm service / khoảng
   thời gian mà detector trên test bắn nhiều hơn val hay không — dùng phân tích độ lệch detector của báo cáo M8,
   không tính lại); phân loại FN (detector bỏ sót /
   judge trả FALSE_POSITIVE / C3 hạ); ca RCA sai (sai hop, sai do thiếu cảnh báo, sai do đồ thị). Mỗi nhóm có số
   đếm và 1–2 ví dụ cụ thể kèm window_id.
4. Khi tôi chấm xong: tính trung bình từng tiêu chí có CI; nếu có người chấm thứ hai trên 20% mẫu thì tính độ
   đồng thuận. Chỉ báo n thực chấm.
5. Tổng duyệt demo lần 1 theo 08 §6 ⇒ danh sách lỗi (nếu M10 chưa xong thì ghi "chờ M10", không chặn mốc).

Đầu ra: docs/milestones/M11-danh-gia-nguoi.md; docs/drafts/ch7-phan-tich-ca-sai.md (§7.3 mối đe doạ, §7.4 phân tích ca sai, hạn chế cho §8.2.1; theo sườn cập nhật 2026-11-18).
```

## W — Viết chương luận văn (dùng lại cho từng chương)

Thay `<N>` và dán dòng tương ứng ở bảng dưới vào chỗ `<GHI CHÚ CHƯƠNG>`.

```text
Đọc docs/prompts/M8-M12-prompts.md §0.2, §0.4, §0.5 rồi viết Chương <N> của luận văn GĐ2 thành văn hoàn chỉnh.
Bạn là phiên W: chỉ tạo / sửa file trong docs/drafts/, không chạm code, config, kết quả, nhật ký.

Nguồn: phần Chương <N> của docs/drafts/suon-bao-cao-gd2.md là dàn ý bắt buộc (giữ đúng số mục); tham khảo thêm
docs/drafts/outline-bao-cao-gd2.md để biết ngân sách trang, nguyên tắc giọng văn và danh mục hình/bảng. Mỗi gạch
đầu dòng ở sườn có dòng "Nguồn:" — mở đúng nguồn đó và lấy số từ nguồn, không lấy số từ sườn. Phần
[TÁI SỬ DỤNG GĐ1] rút gọn từ docs/Thesis_Phase1.pdf, viết lại chứ không chép nguyên văn.
<GHI CHÚ CHƯƠNG>

Cách viết:
- Tiếng Việt học thuật, câu đầy đủ, mỗi mục mở bằng ý chính. Thuật ngữ, ký hiệu (C1…C5, θ, τ, δ, H0–H5) dùng
  thống nhất với sườn. Không viết kiểu ghi chú nội bộ: không "QĐ-0xx", "V3x", "M6" trong thân bài — thay bằng
  mô tả nội dung; mã QĐ chỉ để trong chú thích nguồn dạng comment HTML cuối mỗi mục để tôi tra lại.
- Mọi con số ghi rõ split (val / test), phạm vi (cửa sổ telemetry / mọi cửa sổ), kèm CI nếu nguồn có. Số chưa có
  thì để đúng một dạng: [CHỜ M8], [CHỜ M9], [CHỜ M10], [CHỜ M11]. Không ước đoán, không dùng số mock của GĐ1
  làm kết luận.
- Kết quả âm (H0 không tái lập cơ chế, bỏ C2 / C4, C5 không đáng kể, recall CTAV thấp hơn C1) viết thẳng,
  không làm mềm.
- Bảng: caption "Bảng <N>.x" đặt trên bảng. Hình: chỗ chèn [Hình <N>.x — mô tả] và, nếu vẽ được từ dữ liệu, ghi
  script / file nguồn cần để sinh hình.
- Trích dẫn: chỉ trích tài liệu đã kiểm được (tra web tìm bài gốc: tác giả, năm, nơi công bố). Ghi vào
  docs/drafts/tai-lieu-tham-khao.md kèm cột "đã kiểm / chưa kiểm". Không kiểm được thì giữ [CẦN TRA CỨU] trong
  bài, không bịa.

Đầu ra: docs/drafts/ch<N>-<ten-ngan>.md. Cuối file thêm mục "Còn thiếu" liệt kê: chỗ còn [CHỜ …], trích dẫn
chưa kiểm, hình chưa có, và điểm nào trong sườn bạn thấy mâu thuẫn với nguồn (nêu nguồn nói gì).
Câu trả lời cuối: số trang ước tính, danh sách "Còn thiếu", và những chỗ bạn muốn tôi quyết.
```

| Chương | Chạy khi | `<GHI CHÚ CHƯƠNG>` |
|---|---|---|
| 1 Giới thiệu | Ngay | Dùng lại `docs/drafts/chuong-bai-toan.md` cho §1.1.2–1.1.3. §1.2.4 và §1.4 để `[CHỜ M8]` cho số `test` (hoặc lấy phần H0 đã chốt từ `docs/experiment-log.md` QĐ-037). |
| 2 Kiến thức và công nghệ nền tảng | Ngay | Rút gọn mạnh phần GĐ1; thêm §2.8 Công nghệ nền tảng và §2.9 Kết chương (khẳng định nền tảng đã đủ); §2.7 giải thích đăng ký trước và trỏ bảng H0–H5 sang §5.1 (Bảng 5.1) theo đúng sườn (`suon-bao-cao-gd2.md` §2.7 đã đồng bộ theo `be2b985`, không lặp bảng ở §2.7). |
| 3 Công trình liên quan | Ngay | Hai nhánh theo template: 3.1 nghiên cứu, 3.2 hệ thống và công cụ (chỉ lấy tính năng từ tài liệu chính thức, ghi ngày truy cập), 3.3 Kết chương. Chương nặng tra cứu: kiểm mọi mục `[CẦN TRA CỨU]` trước khi viết; mục nào không tìm được bài gốc thì bỏ khỏi bài và báo tôi. |
| 4 Đề xuất | Ngay (mục RCA bổ sung sau P2) | 4.1 Mô tả đề xuất (tổng quan, vấn đề nghiên cứu, thách thức) trước, 4.6 Kết chương cuối. Mô tả CTAV chốt = C1 + θ 0,80 + C3; C2, C4, C5 trình bày là thành phần đã thử và bị loại, kèm lý do. Đối chiếu với code `services/judge/policy.py`, `eval/configs/ctav_final.yaml`. Phần RCA ghi rõ cắt `propagation` mức 2 (QĐ-037). |
| 5 Thực nghiệm | §5.1–5.6 và §5.7.1–5.7.3 ngay; §5.7.4–5.8 sau P1; §5.9 sau P3 | Tham khảo `docs/drafts/ch5-outline-ket-qua-test.md` cho cấu trúc §5.7–5.8; ghép `docs/drafts/ch5-ket-qua-test.md` (đã có §5.7.1–5.7.3), `ch5-rca-val.md` vào đúng mục; §5.1–5.6 viết từ experiment-log; mỗi kết luận giả thuyết chép đúng tiêu chí đăng ký rồi mới nêu đạt / không đạt. §5.2 hoặc §5.7 dùng bảng độ lệch detector `val` → `test` ở QĐ-036 (`19,6% → 29,2%` cửa sổ thành candidate) và nêu rõ ảnh hưởng tới việc so số `val` với số `test`. |
| 6 Demo platform | Sau P4 | Ghép `docs/drafts/ch6-demo-platform.md`; ảnh ở `docs/drafts/figures/`. |
| 7 Thảo luận; 8.2 Hạn chế | Sau P5 | Ghép `docs/drafts/ch7-phan-tich-ca-sai.md`; §7.3 (mối đe doạ) và §8.2.1 (hạn chế) nêu đủ: một dataset, một judge, Hit@k mức service, không hiệu chỉnh đa so sánh, n người chấm (tối thiểu 15/30 incident — QĐ-037), ngưỡng detector và θ chọn trên `dev` / `val` trong khi tỉ lệ candidate của `test` cao hơn hẳn (QĐ-035, QĐ-036). |
| 8 Tổng kết + 9 Công bố khoa học + Tóm tắt + Abstract | Sau Ch5–Ch7 | Trả lời RQ1–RQ5 (§8.1.1), nối hạn chế → hướng phát triển (§8.2, B8.3) theo `suon-bao-cao-gd2.md` bằng số `test`; Tóm tắt và Abstract ≤ 1 trang mỗi bản, số trùng khớp Ch5. |

## P6 — M12: đóng gói

```text
Đọc docs/prompts/M8-M12-prompts.md §0 rồi làm M12. Điều kiện vào: báo cáo M8–M11 đã có; các file
docs/drafts/ch1..ch8 đã có.

Việc:
1. Kiểm số: viết scripts/m12_check_thesis_numbers.py dò mọi con số kết quả trong docs/drafts/ch*.md và đối chiếu
   với file gốc trong eval/results/ (metrics.json, compare, rca). Xuất bảng: số trong bài / số gốc / file / khớp
   hay lệch. Sửa bài theo số gốc; không sửa chiều ngược lại. Liệt kê mọi [CHỜ …] và [CẦN TRA CỨU] còn sót.
2. Hình: mọi hình kết quả sinh từ script trong eval/ hoặc scripts/ ra docs/drafts/figures/, có lệnh tái lập.
3. Nhất quán: thuật ngữ, ký hiệu, số bảng / hình, tham chiếu chéo giữa các chương; Tóm tắt, Abstract, Ch8 khớp
   Ch5. Ghép thành docs/drafts/luan-van-gd2.md theo thứ tự lắp ráp ở sườn §10 (phần đầu). Không tạo .docx trừ
   khi tôi yêu cầu.
4. Repo: README hướng dẫn tái lập bảng kết quả từ cache; thử trên một bản clone sạch ở thư mục khác và ghi lại
   đúng những gì chạy được / không chạy được. Đề xuất cách xử lý V4–V6 (file legacy chưa commit, file rác gốc
   repo, câu "LLM không RAG thất bại" là số mock) — chỉ đề xuất, chờ tôi duyệt mới xoá / sửa.
5. Soạn dàn ý slide bảo vệ (≤ 20 slide) và kịch bản demo 5 phút; tổng duyệt demo lần 2, ghi lỗi còn lại.

Không làm: không push, không công khai repo, không chọn license thay tôi — chuẩn bị sẵn và báo tôi làm.
Đầu ra: docs/milestones/M12-dong-goi.md, bảng kiểm số, docs/drafts/luan-van-gd2.md, dàn ý slide.
```

---

## Việc chỉ bạn làm được (đường găng của con người)

| Khi | Việc | Ước lượng |
|---|---|---|
| Trước P2 (M9-A) | Bật Docker Desktop + `docker compose --profile dev up -d` | 2 phút |
| Sau P1 | Đọc `M8-g-test.md` §2–§3, trả lời vấn đề phát sinh (nếu có); tự xử lý phần báo GVHD (V29) | 1 buổi |
| Bất kỳ lúc nào sau P1 | Chấm 50 cửa sổ context precision (V35, không chặn) | 2–3 giờ |
| Sau P2 | Xem `rca_final.yaml` trước khi P3 chạy `test` | 30 phút |
| Sau P5 bước 1 | Chấm 15–30 incident (tối thiểu 15 đầu là hợp lệ) | 3–5 giờ |
| Mỗi chương | Đọc duyệt, sửa giọng văn, chuyển sang Word | phần lớn 2 tuần của bạn |
