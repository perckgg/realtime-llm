# M3 — Service graph + C1 + cổng chặn G-paper

| | |
|---|---|
| Ngày đóng mốc | 2026-10-19 |
| Hạn mục tiêu | 2026-11-08 (sớm 20 ngày) |
| Kết luận | **QUA**: G-paper đạt cho cả hai biến thể (489/489, Table 1 trùng chính xác); đồ thị trùng GĐ1; C1 đã port. **Nhưng có một phát hiện cần bạn quyết trước M4 (V16):** trên dữ liệu đầy đủ, C1 với trọng số của paper không bao giờ đưa bằng chứng lân cận vào prompt |
| Commit | commit M3 (cùng commit với báo cáo này) |
| Quyết định liên quan | QĐ-020 (khảo sát), QĐ-021 (V12–V15, kết quả M3) |

## 1. Kết quả hiện tại

| DoD (`04` M3) | Đạt? | Bằng chứng |
|---|---|---|
| Tái lập Table 1 từ cache, không gọi API: BM25 F1 0,7030 / FP 7; Topology F1 0,4759 / FP 137 | Đạt | Bảng M3-1; `eval/results/gpaper_viewA_paper500.json` |
| Cache hit 100% | Đạt | 489/489 mỗi biến thể |
| `docs/graph-coverage.md` có 3 chỉ số; fallback nếu < 60% | Đạt | Sinh tự động; fault window 100% ⇒ không fallback |
| pytest / mypy / ruff sạch | Đạt | 115 test |
| Báo cáo | Đạt | File này |

**Bảng M3-1. Cổng G-paper.**

| Biến thể | Top-6 / prompt / cache trùng | TP | FP | P | R | F1 (paper) |
|---|---|---|---|---|---|---|
| BM25 | 489 / 489 / 489 | 58 | 7 | 0,8923 | 0,58 | **0,7030** (0,7030) |
| Topology | 489 / 489 / 489 | 74 | 137 | 0,3507 | 0,74 | **0,4759** (0,4759) |

**Đồ thị:** 56 service, 68 cạnh, trùng GĐ1 cả cạnh lẫn trọng số. 18 service train-ticket cô
lập; fault window 100% nằm trên service có cạnh.

**Judge mới `gemini-2.5-flash` (V12):** smoke 196 lần gọi, ≈ 0,23 USD, judge 74 s; gần như
không trả UNCERTAIN, chép `anomaly_score` 1/196 lần (flash-lite: 16). Chỉ trùng verdict thô
với flash-lite ở 52% số candidate. Một lỗi HTTP 403 tạm thời, chạy lại tự hỏi lại đúng 1 câu.

**Bảng M3-2. C1 (A4, `bm25_pool: window`) trên kho Nezha đầy đủ** — 196 lần retrieval, judge mock.

| | |
|---|---|
| Bằng chứng lân cận trong top-6 | **0 / 810 event, 0 / 196 prompt** |
| Ứng viên lân cận có sẵn (trung vị) | 200 trên 10 service |
| Điểm event local hạng 6 (trung vị) / điểm tối đa của lân cận d = 1 | 0,841 / 0,80 |
| Độ trễ retrieval trung bình / P95 | 2,9 s / 7,8 s |

## 2. Cần review gì

| # | Kiểm gì | Ở đâu | Vì sao rủi ro |
|---|---|---|---|
| R1 | Phát hiện 4 — lập luận "lân cận không thể thắng" | QĐ-021 Bảng QĐ-021-3; `services/retrieval/hybrid_bm25_graph.py` (`_rank`) | Quyết định V16 dựa hoàn toàn vào đây; nên tự mở `eval/results/m3_c1_window_smoke_v1/retrieval.jsonl` xem vài truy vấn |
| R2 | Chế độ `window` giới hạn BM25 trong các service 2-hop | docstring `hybrid_bm25_graph.py` | Paper cho BM25 lấy cả service ngoài 2-hop (GraphSim 0); GĐ2 bỏ vì quá chậm |
| R3 | Giá `gemini-2.5-flash` dùng để ước chi phí | `services/judge/backends.py` (`PRICES_PER_1M`) | Lấy từ bảng giá tôi biết, chưa đối chiếu billing của bạn |
| R4 | Phát hiện 3 + 4 cùng nhau đổi cách hiểu kết quả paper | QĐ-020, QĐ-021 | Đây là nội dung nhạy cảm khi viết chương Bài toán và khi trao đổi GVHD |

## 3. Vấn đề cần bạn giải quyết

| # | Vấn đề | Phương án | Khuyến nghị | Chặn mốc sau? |
|---|---|---|---|---|
| **V16** | **C1 đúng như paper không đưa bằng chứng lân cận vào prompt trên dữ liệu đầy đủ** (Phát hiện 4). H0 ("topology tăng recall nhưng tăng FPR") vì vậy có thể không tái lập trên GĐ2, và tầng 2 của CTAV sẽ trùng tầng 1 | (a) Chỉ giữ C1 đúng paper; nếu H0 không tái lập thì luận văn kết luận vấn đề của paper là hệ quả của giao thức (corpus lọc theo nhãn + BM25 không giới hạn thời gian) — trung thực, nhưng đóng góp CTAV yếu đi. (b) Giữ C1-paper làm baseline **và** thêm C1-quota: dành `k_graph` chỗ (ví dụ 3/6) cho bằng chứng lân cận (d ≥ 1) xếp bằng chính Fusion Score; C1-quota làm tầng 2 của CTAV; H0 đo cả hai. (c) Chỉnh công thức (GraphSim, truy vấn không chứa tên `s0`) | **(b)**. Vẫn báo cáo trung thực (a) như một phát hiện, nhưng có một phiên bản topology thực sự đưa được bằng chứng lân cận để kiểm H0/H1/H2. `k_graph` chọn trên `val`. Nên hỏi ý GVHD vì đây là thay đổi phương pháp | **Có — chặn M4** (thiết kế H0) |
| **V17** | Độ trễ C1: ~2,9 s/lần ⇒ ~85 phút retrieval mỗi run `val` | (a) Tăng tốc mà giữ ngữ nghĩa: cache thống kê token theo file phút, tính BM25 bằng numpy sparse, chạy retrieval song song theo process; (b) chỉ chạy BM25 trên `s0`, lân cận lấy qua mở rộng đồ thị (đổi ngữ nghĩa) | **(a)** — mục tiêu < 0,5 s/lần, làm đầu M4 | Không chặn, nhưng M4 nhiều run |
| V1 | Mail GVHD — nay nên kèm Phát hiện 1–4 và V16 | | Nên gửi trước M4 | Nên |
| V3–V6 | Như trước | | | Không |

## 4. Plan cho mốc tiếp theo (M4 — H0 trên split GĐ2)

Theo `04` M4, sau khi chốt V16:

1. V17: tăng tốc retrieval; đo lại smoke C1.
2. Nếu V16 (b): thêm `k_graph` vào C1 (quota bằng chứng lân cận) + test; chọn `k_graph` trên `val` (retrieval-only).
3. Ablation retrieval-only (không gọi LLM) lưới α, β, γ trên `val` — gồm temporal-only (β = 1), graph-only (γ = 1); đo tỷ lệ bằng chứng lân cận và context precision proxy.
4. H0 trên `val` (tập có telemetry, `gemini-2.5-flash`): BM25, C1-paper, (C1-quota), LLM-không-RAG, detector-only; bootstrap CI + McNemar; ngân sách toàn bộ + 120 lần gọi.
5. Nháp chương "Bài toán" từ paper + Phát hiện 1–4.

DoD: bảng H0 trên `val` có CI; quyết định tiếp tục / viết lại câu chuyện ghi experiment-log.

Rủi ro: H0 không tái lập ⇒ theo `08` §5.1 phải viết lại câu chuyện — cần GVHD sớm.

## Phụ lục

**Sai lệch so với plan.**
- Judge đổi sang `gemini-2.5-flash` (V12) — G-paper vẫn dùng flash-lite.
- G-paper chạy bằng `scripts/check_gd1_parity.py` trên candidate của GĐ1, không qua harness; `paper_viewA_replay.yaml` không cần vì `paper_500` là cửa sổ 120 s của GĐ1.
- Thêm cờ `bm25_pool` cho C1 (V13), chặn chế độ parity trên `val`/`test`.

**Nguyên liệu cho luận văn.**
- Bảng M3-1: tái lập Table 1 của paper từ cache.
- `docs/graph-coverage.md`: đồ thị và coverage.
- Phát hiện 3 (QĐ-020) + Phát hiện 4 (Bảng M3-2): chương Bài toán / đánh giá lại paper.

**Lệnh tái lập M3.**

```bash
py scripts/build_service_graph.py                                        # 30 s
py scripts/dump_gd1_prompts.py --variant topology_aware_fusion_top6      # ~90 s
py scripts/check_gd1_parity.py --variant hybrid_bm25_top6                # Bảng M3-1
py scripts/check_gd1_parity.py --variant topology_aware_fusion_top6      # Bảng M3-1
py -m eval run --config eval/configs/m3_c1_window_smoke.yaml             # Bảng M3-2, ~10 phút (run_id mới)
py -m eval run --config eval/configs/m3_flash_judge_smoke.yaml           # judge flash (run_id mới)
```
