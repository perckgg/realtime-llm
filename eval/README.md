# eval

**Làm gì.** Harness thực nghiệm: đọc một config trong `configs/`, chạy pipeline
(replay → detector → gate → retrieval → judge) và ghi `results/<run_id>/` (`02` §3.3).
`results/` được commit và **bất biến** — chạy lại với tham số khác = `run_id` mới; harness
từ chối thư mục đã tồn tại (R-A3).

**Chạy thế nào.**

```bash
py -m eval run --config eval/configs/gd1_phase4_parity.yaml   # cổng G-port (M2)
py -m eval run --config eval/configs/val_detector_count.yaml  # đếm candidate val
```

| File | Nội dung |
|---|---|
| `harness/runner.py` | Config → pipeline → 7 file output (+ ClickHouse nếu `storage.clickhouse: true`) |
| `harness/metrics.py` | P/R/F1/FPR, coverage, độ trễ, token, chi phí; tập có telemetry (chính) và toàn bộ (QĐ-017) |
| `harness/stats.py` | `bootstrap_ci`, `bootstrap_confusion_ci`, `mcnemar_exact` |
| `configs/gd1_phase4_parity.yaml` | Cấu hình GĐ1 Phase 4 (chỉ cho G-port) |
| `configs/gd1_phase4_windows.csv` | 1.000 cửa sổ GĐ1 → `window_id` GĐ2 (`scripts/map_gd1_windows.py`) |
| `configs/val_detector_count.yaml` | Chỉ detector trên `val` |
| `configs/bm25_baseline.yaml` | Bản nháp M0, sẽ thay ở M4 |

**Input/Output.** YAML config (khóa: xem docstring `harness/runner.py`) → `results/<run_id>/`
gồm `metrics.json`, `per_window.csv`, `retrieval.jsonl`, `judged.jsonl`,
`config.snapshot.yaml`, `git_commit.txt`, `runtime.json`. Test: `tests/test_harness.py`.
