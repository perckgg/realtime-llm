# M0 — Nền tảng dữ liệu + hạ tầng

| | |
|---|---|
| Ngày đóng mốc | 2026-09-07 (DoD); báo cáo viết bù 2026-10-18 sau review bằng CodeGraph |
| Hạn mục tiêu | 2026-09-07 — đúng hạn |
| Kết luận | **QUA**, kèm 6 điểm sửa ở detector chuyển sang M1 |
| Commit | `8022f5c` (khung repo), `dbf7fb5` (nhãn + split), `149ecfa` (dashboard MVP), `57b9ff9` (hạ tầng, replayer, detector), `fc3b38b` (plan mới) |
| Quyết định liên quan | QĐ-001 … QĐ-010; QĐ-011 … QĐ-014 (đổi hướng, cổng chặn, judge, cột mốc) |

## 1. Kết quả hiện tại

### 1.1 DoD

| DoD | Đạt? | Bằng chứng |
|---|---|---|
| Biết chính xác số fault window có nhãn root-cause | Đạt | 101 lần tiêm lỗi, nhãn mức pod ánh xạ 100% lên service (QĐ-001, `docs/label-audit.md`) |
| Split commit, không đổi | Đạt | `data/splits/*.json`; `py scripts/make_splits.py --check` |
| Một lệnh dựng môi trường dev | Đạt | `docker compose --profile dev up -d` → `clickhouse`, `postgres` healthy (QĐ-010) |
| Replay 50 window → candidate vào ClickHouse | Đạt | `py scripts/replay_smoke.py --windows 50` → 50 dòng, 14 candidate; truy vấn ClickHouse trả `50  14` |
| Test | Đạt | `py -m pytest tests/ -q` → 32/32 pass (chạy lại 2026-10-18, 206 s) |

### 1.2 Số liệu dữ liệu

**Bảng M0-1.** Corpus Nezha sau khi join theo wall-clock (QĐ-002, QĐ-003).

| Chỉ số | Giá trị |
|---|---|
| Cửa sổ (1 mẫu metric / pod / 60 s) | 95.660 |
| Fault window | 704 (0,74%) |
| Lần tiêm lỗi | 101 |
| Cửa sổ có latency percentile `"NaN"` | 27.335 (28,58%) |

**Bảng M0-2.** Split chốt cứng, nhóm theo lần tiêm lỗi, vùng đệm 600 s (QĐ-004).

| Split | Cửa sổ | Fault window | Lần tiêm lỗi |
|---|---|---|---|
| dev | 19.316 | 149 | 21 |
| val | 28.898 | 209 | 30 |
| test | 46.849 | 346 | 50 |
| Bị loại (vùng đệm) | 597 | — | — |

### 1.3 Ngoài DoD

- Dashboard MVP 4 màn hình trên dữ liệu giả (`services/web/`, QĐ-007).
- Kế hoạch GĐ2 được viết lại theo hướng giải pháp CTAV + chứng minh (`08-research-direction.md`, QĐ-011..014).

## 2. Cần review gì

Kết quả review code 2026-10-18 (CodeGraph + chạy thử trên split dev). Các con số dưới đây do
tôi đo; nên chạy lại để xác nhận trước khi sửa.

| # | Kiểm gì | Ở đâu | Vì sao rủi ro |
|---|---|---|---|
| R1 | Detector điền 0.0 cho metric mà loader đã cố tình bỏ (NaN) — ảnh hưởng 4.164/19.316 cửa sổ dev (21,6%), 12.546 giá trị | `services/detector/isolation_forest.py:64` vs `packages/schemas/loaders.py:154-160` | Cửa sổ nhàn rỗi bị coi là "độ trễ 0", ngược với QĐ-009 |
| R2 | Buffer chỉ thấy cửa sổ thuộc split: 3.687/19.288 (19%) cặp liền kề cách > 60 s; 18/138 cửa sổ fault có cửa sổ liền trước không phải t−60 s | `isolation_forest.py:126,148`; `services/replayer/nezha_source.py:69-87` | Gần như mọi cửa sổ khởi phát lỗi bị tính delta/std so với mẫu ≥ 10 phút trước (do vùng đệm 600 s) |
| R3 | `score()` đẩy dữ liệu vào buffer; gọi hai lần trên cùng cửa sổ là hỏng lịch sử; `is_candidate()` phụ thuộc thứ tự gọi | `isolation_forest.py:142-165` | Harness/Rescue chấm lại sẽ âm thầm lệch đặc trưng |
| R4 | `mypy` không chạy được (`python_version = "3.11"`, máy 3.14); `ruff` 11 lỗi | `pyproject.toml:48` | Lệnh kiểm tra trong DoD đang hỏng mà không ai biết |
| R5 | Chạy lại smoke cùng `run_id` nhân đôi dòng ClickHouse | `scripts/replay_smoke.py:33` | Truy vấn kiểm chứng DoD sẽ ra 100 thay vì 50 |
| R6 | Smoke fit và chấm trên cùng dev (in-sample) | `scripts/replay_smoke.py:39-46` | Chấp nhận cho smoke; không được dùng kiểu này cho số liệu báo cáo |
| R7 | Baseline GĐ1 (P 0.32, F1 không RAG 0.000, F1 có Rescue 0.781) đều đo bằng judge `mock` | `legacy/nezha_setup/config/experiment_phase4_benchmark.yaml:45-47` | Báo cáo GĐ1 và luận văn không được dùng các số này làm kết luận về LLM |
| R8 | Plan mới: giải pháp CTAV, giả thuyết H0–H5, lộ trình mốc | `docs/Final_Thesis_Phase2/08-research-direction.md`, `04-implementation-roadmap.md` | Đổi hướng nghiên cứu — cần bạn (và GVHD) đồng ý |

## 3. Vấn đề cần bạn giải quyết

| # | Vấn đề | Phương án | Khuyến nghị | Chặn mốc sau? |
|---|---|---|---|---|
| V1 | GVHD chưa xem hướng CTAV (đổi từ "so sánh 5 biến thể RAG") | Gửi tóm tắt 1 trang từ `08` §2–§5 / đợi | Gửi ngay, trước khi xong M2 — nếu GVHD muốn chỉnh, chỉnh sớm rẻ hơn | Không chặn M1; nên có trước M4 |
| V2 | Q2: đánh giá trên toàn `val`/`test` (1:135) hay thêm tập cố định kiểu `paper_500` | Toàn split / tập cố định / cả hai | Toàn split cho kết quả chính; quyết sau khi M2 đếm được số candidate thật | Chặn M4 |
| V3 | Q5: mốc bảo vệ tuần 2027-02-08 có cố định? Tết ~2027-02-06 | Cố định / dời | Xác nhận với khoa/GVHD | Không chặn; ảnh hưởng hạn mục tiêu |
| V4 | 4 file `legacy/` sửa chưa commit (vá đường dẫn trong `legacy/scripts/phase2/{generate_paper_outputs,run_step9_quality_gate}.py` + timestamp `input_freeze.*`) | Commit riêng / bỏ | Xem diff; nếu là vá sau khi dời code vào `legacy/` thì commit riêng | Không |
| V5 | File rác ở gốc repo: `front_matter.txt`, `refs_sample.txt`, `toc_out.txt`; cache `legacy/outputs/test_results/*_cache_*.jsonl` chưa ignore | Dời / xoá / ignore | Dời 3 file txt vào `docs/submission_docs/` hoặc xoá nếu chỉ là trích tạm; thêm cache vào `.gitignore` | Không |
| V6 | Báo cáo GĐ1 kết luận "LLM không RAG thất bại" dựa trên số mock (R7) | Ghi chú lại trong luận văn GĐ2 | Khi viết chương Bài toán, nói rõ GĐ1 dùng mock và paper (LLM thật) cho F1 0.566 | Không |

Đã giải quyết trong phiên 2026-10-18: Q1 (judge = `gemini-2.5-flash-lite`, QĐ-013), Q3 (metric
thiếu = giá trị gần nhất + cờ), Q4 (lịch sử buffer liên tục).

## 4. Plan cho mốc tiếp theo — M1

**Việc, theo thứ tự làm** (mỗi việc: code + test + ghi experiment-log nếu có số đo):

1. Sửa detector: R1 (giá trị gần nhất của pod + cờ thiếu), R2 (replayer phát lịch sử liên
   tục, split chỉ lọc cửa sổ chấm), R3, R4, R5, D6. Đo lại trước/sau trên dev → QĐ-015.
2. `packages/schemas/protocols.py` + model `ContextEvent`, `RetrievalBudget`, `RetrievalResult`, `JudgedAlert` (`03` §1.3–1.4).
3. `packages/schemas/evidence.py` — loader log/trace Nezha.
4. `services/retrieval/bm25_hybrid.py` — port GĐ1, bỏ tag fault type khỏi truy vấn.
5. `services/judge/` — port prompt **nguyên văn** (để M3 trúng cache), cache có `repeat`, client Gemini, backend mock; `registry.py`.

**DoD M1:** xem `04` §M1.

**Rủi ro đã biết:**
- Prompt/định dạng context lệch GĐ1 một ký tự là M3 cache miss — port nguyên văn, có test so chuỗi với một bản ghi cache GĐ1.
- Khối lượng log/trace Nezha lớn — loader phải lọc theo cửa sổ thời gian, không nạp hết vào RAM.
- Hạn mục tiêu M1 (2026-10-25) chỉ một tuần cho 5 việc; nếu trễ, việc 1–2 là bắt buộc trước, 3–5 có thể tràn sang đầu M2.

## Phụ lục

**Sai lệch so với plan:**
- Rescue Score bị hoãn khỏi M0 (QĐ-009) → M7.
- Dashboard dựng sớm trên dữ liệu giả (QĐ-007) — lệch thứ tự, không lệch phạm vi.
- Tuần 3–7 lịch cũ không có tiến độ GĐ2 → lên lịch lại (QĐ-011), chuyển sang cột mốc (QĐ-014).

**Nguyên liệu cho luận văn:** Bảng M0-1, M0-2; QĐ-002 (lỗi múi giờ Nezha: 26 lần tiêm lỗi và
177 fault window bị mất ở GĐ1); QĐ-004 (chống rò rỉ khi chia split); `docs/label-audit.md`.
