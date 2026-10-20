# eval

**Làm gì.** Harness thực nghiệm: đọc một config trong `configs/`, chạy pipeline
(replay → detector → gate → retrieval → judge) và ghi `results/<run_id>/` (`02` §3.3).
`results/` được commit và **bất biến** — chạy lại với tham số khác = `run_id` mới; harness
từ chối thư mục đã tồn tại (R-A3).

**Chạy thế nào.**

```bash
py -m eval run --config eval/configs/gd1_phase4_parity.yaml   # cổng G-port (M2)
py -m eval run --config eval/configs/val_detector_count.yaml  # đếm candidate val
py -m eval compare --runs bm25=h0_val_bm25_v1,c1=h0_val_c1_k0_v1 --detector-only h0_val_bm25_v1 --out <tên-mới>
```

| File | Nội dung |
|---|---|
| `harness/runner.py` | Config → pipeline → 7 file output (+ ClickHouse nếu `storage.clickhouse: true`). Pha 1 tuần tự (replay, detector, gate, retrieval), pha 2 judge song song `judge.workers` (mặc định 8) — QĐ-019. `retrieval.workers` > 1 (chỉ kho Nezha, không `parity_query_terms`): retrieval chạy sau replay trên N process, chia đoạn liên tục theo thời gian; kết quả trùng tuần tự, riêng `latency_ms` đo dưới tải song song nên chỉ để tham khảo — QĐ-022 |
| `harness/metrics.py` | P/R/F1/FPR, coverage, độ trễ, token, chi phí; tập có telemetry (chính) và toàn bộ (QĐ-017) |
| `harness/stats.py` | `bootstrap_ci`, `bootstrap_confusion_ci`, `mcnemar_exact` |
| `harness/compare.py` | `py -m eval compare --runs a=run_a,b=run_b [--detector-only run] --out <tên-mới>`: so sánh có cặp trên cùng cửa sổ (tập có telemetry + toàn bộ) — P/R/F1/FPR + CI, hiệu số so với run đầu tiên kèm CI bootstrap có cặp, McNemar chính xác (mọi cửa sổ / fault / normal). Ghi `results/<tên>/compare.json` (QĐ-026) |
| `configs/h0_val_*.yaml` | H0 (QĐ-026): `bm25`, `c1_k0`, `c1_k1`, `norag` (`require_evidence: false`), `norag_reqev`; `*_b120` = ngân sách 120 lần gọi, chạy lại từ cache |
| `harness/kgraph.py` + `scripts/kgraph_select.py` | Chọn `k_graph` trên `val` từ các run harness (V18, QĐ-024) |
| `harness/fusion_ablation.py` + `scripts/fusion_ablation.py` | Ablation retrieval-only lưới α, β, γ × `k_graph` (QĐ-025): pool C1 dựng một lần/candidate, xếp hạng lại mỗi điểm lưới; khóa `ablation` (`grid_step`, `extra_points`, `k_graph`, `keep_ids_for`, `verify_against`); ghi `grid.json`, `per_candidate.csv`, `runtime.json`. Config `configs/m4_fusion_ablation_val.yaml` |
| `configs/gd1_phase4_parity.yaml` | Cấu hình GĐ1 Phase 4 (chỉ cho G-port) |
| `configs/gd1_phase4_windows.csv` | 1.000 cửa sổ GĐ1 → `window_id` GĐ2 (`scripts/map_gd1_windows.py`) |
| `configs/val_detector_count.yaml` | Chỉ detector trên `val` |
| `configs/m2_parallel_judge_smoke.yaml` | Smoke judge song song với Gemini thật (QĐ-019) |
| `configs/bm25_baseline.yaml` | Bản nháp M0, sẽ thay ở M4 |

**Input/Output.** YAML config (khóa: xem docstring `harness/runner.py`) → `results/<run_id>/`
gồm `metrics.json`, `per_window.csv`, `retrieval.jsonl`, `judged.jsonl`,
`config.snapshot.yaml`, `git_commit.txt`, `runtime.json`. Test: `tests/test_harness.py`.
