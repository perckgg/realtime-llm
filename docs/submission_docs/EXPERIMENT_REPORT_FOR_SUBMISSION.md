# Báo Cáo Tóm Tắt Thí Nghiệm Hybrid Monitoring

## 1. Mục Tiêu Và Phạm Vi

Thí nghiệm này đánh giá một pipeline giám sát lai cho hệ thống cloud/server:

```text
Metric -> Preprocessing -> Anomaly Detector -> Alert Candidate
       -> LLM Gate -> RAG Retrieval -> LLM-as-a-Judge
       -> Decision/Fallback -> Audit/Evaluation
```

Mục tiêu chính là kiểm chứng tính khả thi của cách kết hợp metric detector, truy xuất ngữ cảnh log/trace, và LLM judge. Hệ thống hiện tại chưa nhắm tới production real-time, mà tập trung vào khả năng đo lường, so sánh mode, và audit được toàn bộ quy trình xử lý.

## 2. Dataset Sử Dụng

| Dataset | Dữ liệu chính | Đã xử lý thành | Vai trò trong thí nghiệm |
|---|---:|---:|---|
| Microsoft cloud-monitoring-dataset | 60 time-series CSV, 60 metadata JSON | 225,403 metric points, 4,553 anomaly points | Phù hợp cho detector baseline và anomaly scoring |
| IntelligentDDS/Nezha | 112 metric CSV, log, trace, traceid, fault list | 95,660 metric rows, 11,696 context events | Dataset chính cho hybrid RAG + LLM judge |

Nhận xét:

- Microsoft dataset có nhãn anomaly trực tiếp trên từng điểm metric, nhưng không có log/trace vận hành thật. Vì vậy dataset này phù hợp với detector-only baseline hơn là đánh giá RAG/LLM.
- Nezha có metric, log, trace và fault injection list, nên bám sát kiến trúc nghiên cứu hơn. Label `true_alert` được tạo theo fault injection trên cùng pod trong cửa sổ -60s đến +360s.

Báo cáo dữ liệu chi tiết đã có tại:

```text
DATASET_REPORT.md
outputs/dataset_analysis/dataset_analysis_summary.json
```

### 2.1. Microsoft Cloud-monitoring Dataset Được Dùng Khi Nào?

Microsoft `cloud-monitoring-dataset` được dùng ở giai đoạn đầu của thí nghiệm như một **metric-only feasibility benchmark**. Dataset này phù hợp để kiểm tra:

- đọc và chuẩn hóa time-series metric,
- tạo feature `value`, `value_z`, `abs_delta_z`,
- gom điểm metric thành cửa sổ 1 giờ,
- đánh giá detector baseline trước khi dùng log/trace context và LLM judge.

Dataset này **không dùng để đánh giá RAG hoặc API**, vì nó không có log/trace vận hành thật. File `cloud_monitor_setup/processed/logs.jsonl` chỉ chứa metadata context sinh từ metadata JSON của dataset, nên các output mock/hybrid legacy nếu còn tồn tại sẽ không được đưa vào kết quả báo cáo chính.

Setup hiện tại:

| Hạng mục | Giá trị |
|---|---|
| Config | `cloud_monitor_setup/config/experiment_current.yaml` |
| Processed metrics | `cloud_monitor_setup/processed/metrics.csv` |
| Metadata context | không dùng cho kết quả chính; `logs.jsonl` chỉ là metadata legacy |
| Output detector-only chính | `cloud_monitor_setup/outputs/current_results/detector_only_results.json` |
| Audit detector-only chính | `cloud_monitor_setup/outputs/current_audit/detector_only_audit.jsonl` |
| Report riêng | `reports/cloud_monitoring_experiment_report.md` |
| Metrics CSV | `reports/cloud_monitoring_experiment_metrics.csv` |
| Threshold sweep | `reports/cloud_monitoring_threshold_sweep.csv` |
| Domain analysis | `reports/cloud_monitoring_domain_analysis.csv` |

Tóm tắt dữ liệu đã xử lý:

| Chỉ số | Giá trị |
|---|---:|
| Time series | 60 |
| Metric points | 225,403 |
| Anomaly points | 4,553 |
| Skipped points | 42 |

Kết quả detector-only chính, không dùng RAG và không gọi external LLM API:

| Mode | Windows | Candidates | Routed | Precision | Recall | F1 | FPR | TP | FP | TN | FN | LLM calls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `detector_only` | 49,578 | 14,686 | 14,686 | 0.1222 | 0.8077 | 0.2122 | 0.2722 | 1,794 | 12,892 | 34,465 | 427 | 0 |

Threshold sweep chạy ngày 2026-06-05:

| Threshold | Windows | Candidates | Precision | Recall | F1 | FPR | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.70 | 49,578 | 17,590 | 0.1052 | 0.8330 | 0.1868 | 0.3324 | 1,850 | 15,740 | 371 |
| 0.75 | 49,578 | 16,346 | 0.1118 | 0.8226 | 0.1968 | 0.3066 | 1,827 | 14,519 | 394 |
| 0.80 | 49,578 | 15,485 | 0.1170 | 0.8158 | 0.2047 | 0.2887 | 1,812 | 13,673 | 409 |
| 0.85 | 49,578 | 14,686 | 0.1222 | 0.8077 | 0.2122 | 0.2722 | 1,794 | 12,892 | 427 |
| 0.90 | 49,578 | 13,936 | 0.1269 | 0.7960 | 0.2189 | 0.2569 | 1,768 | 12,168 | 453 |
| 0.95 | 49,578 | 13,310 | 0.1317 | 0.7893 | 0.2257 | 0.2440 | 1,753 | 11,557 | 468 |

Phân tích theo domain ở threshold 0.85, chạy ngày 2026-06-05:

| Domain | Windows | Candidates | Precision | Recall | F1 | FPR | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| application-crash-rate-1 | 5,352 | 1,329 | 0.4432 | 0.8068 | 0.5721 | 0.1601 | 740 | 141 |
| application-crash-rate-2 | 11,011 | 1,965 | 0.2046 | 0.7053 | 0.3172 | 0.1497 | 1,563 | 168 |
| consumer-purchase-rate | 7,488 | 2,386 | 0.0532 | 0.7427 | 0.0993 | 0.3087 | 2,259 | 44 |
| data-ingress-rate | 1,320 | 1,153 | 0.0278 | 1.0000 | 0.0540 | 0.8703 | 1,121 | 0 |
| ecommerce-api-incoming-rps | 6,191 | 2,049 | 0.0517 | 0.8833 | 0.0977 | 0.3200 | 1,943 | 14 |
| middle-tier-api-dependency-latency | 16,560 | 4,462 | 0.1105 | 0.8915 | 0.1966 | 0.2480 | 3,969 | 60 |
| mongodb-application-rps | 1,056 | 1,004 | 0.0209 | 1.0000 | 0.0410 | 0.9498 | 983 | 0 |
| mongodb-machine-rps | 336 | 336 | 0.0714 | 1.0000 | 0.1333 | 1.0000 | 312 | 0 |
| service-unavailable | 264 | 2 | 0.0000 | 0.0000 | 0.0000 | 0.0076 | 2 | 0 |

Diễn giải:

- `detector_only` là kết quả quan trọng nhất từ Microsoft dataset: recall 0.8077 cho thấy detector bắt được nhiều anomaly windows, nhưng precision 0.1222 và 12,892 false positives cho thấy metric-only detector tạo nhiều cảnh báo giả.
- Threshold thấp tạo nhiều candidates và recall cao hơn; threshold cao giảm candidates/FPR nhưng làm recall giảm. Threshold 0.85 vẫn là điểm cân bằng ban đầu.
- Detector hoạt động không đều giữa các domain. Các domain biến động mạnh như `mongodb-machine-rps`, `mongodb-application-rps` và `data-ingress-rate` tạo FPR rất cao, nên cần được xem như nguồn false-positive burden của metric-only detector.
- `service-unavailable` không có anomaly label trong dữ liệu processed, nên recall/F1 ở domain này không nên diễn giải như chất lượng phát hiện anomaly; chỉ dùng FP/FPR để quan sát hành vi false positive.
- Dataset này không được dùng cho `llm_without_rag`, `hybrid`, RAG hoặc API call trong báo cáo chính. Lý do là dataset không có log/trace thật và số candidate 14,686 là quá lớn để gửi API trong phạm vi thí nghiệm luận văn. Nếu thư mục `cloud_monitor_setup/outputs` còn output mock LLM/RAG legacy, các output đó chỉ là plumbing check và bị loại khỏi kết quả submission.
- Trong luận văn, Microsoft dataset nên được trình bày như bước nền: xác định false-positive burden của metric detector, sau đó chuyển sang Nezha để đánh giá hybrid RAG + LLM-as-a-Judge.

## 3. Các Mode Thí Nghiệm

Lưu ý: các mode RAG/LLM trong phần này áp dụng cho Nezha và các phase hybrid sau đó. Microsoft cloud-monitoring-dataset chỉ được dùng cho detector-only baseline, threshold sweep và domain analysis; không dùng cho RAG/API evaluation.

| Mode | Mô tả | Mục đích so sánh |
|---|---|---|
| `detector_only` | Chỉ dùng metric detector, không gọi LLM, không dùng RAG | Baseline chính để đo precision/recall/FPR của detector |
| `llm_without_rag` | Detector tạo candidate, LLM judge không có context truy xuất | Đo vai trò của LLM khi thiếu log/trace context |
| `hybrid` | Detector + gate + RAG + LLM judge | Mode hybrid đầy đủ |
| `hybrid_no_gate` | Hybrid nhưng tắt LLM gate | Kiểm tra ảnh hưởng của gate trong Phase 3 ablation |
| `hybrid_local_top6` | Hybrid với vector backend local hashing, top_k=6 | So sánh backend retrieval |
| `hybrid_bm25_top6` | Hybrid với `hybrid_bm25`, top_k=6 | Backend RAG chính hiện tại |
| `hybrid_bm25_top10` | Hybrid với `hybrid_bm25`, top_k=10 | Kiểm tra ảnh hưởng của số lượng context |
| `hybrid + context_rescue` | Hybrid BM25 thêm bước promote candidate bằng log/trace signal | Cải thiện recall, đặc biệt với fault metric detector bỏ lỡ |
| `local_first` | Ollama local judge trước, Gemini API fallback khi local uncertain/error | Giảm phụ thuộc API nhưng vẫn giữ fallback an toàn |

## 4. Bảng So Sánh Mode Đã Có Sẵn

Repo đã có các bảng so sánh mode được sinh từ script:

| Hạng mục | File Markdown | File CSV | File JSON |
|---|---|---|---|
| Phase 3 ablation: detector-only vs LLM without RAG vs hybrid vs hybrid no gate | `nezha_setup/outputs/phase3_smoke/ablation/ablation_summary.md` | `nezha_setup/outputs/phase3_smoke/ablation/ablation_summary.csv` | `nezha_setup/outputs/phase3_smoke/ablation/ablation_report.json` |
| Phase 4 benchmark: detector-only vs LLM without RAG vs local hashing RAG vs BM25 RAG | `nezha_setup/outputs/phase4_benchmark/results/phase4_benchmark_summary.md` | `nezha_setup/outputs/phase4_benchmark/results/phase4_benchmark_summary.csv` | `nezha_setup/outputs/phase4_benchmark/results/phase4_benchmark_report.json` |
| Phase 5 context rescue summary | `nezha_setup/outputs/phase5_context_rescue/results/hybrid_summary.md` | `nezha_setup/outputs/phase5_context_rescue/results/hybrid_summary.csv` | `nezha_setup/outputs/phase5_context_rescue/results/hybrid_results.json` |
| Local-first Ollama + Gemini fallback summary | `nezha_setup/outputs/local_first_ollama_smoke/results/hybrid_summary.md` | `nezha_setup/outputs/local_first_ollama_smoke/results/hybrid_summary.csv` | `nezha_setup/outputs/local_first_ollama_smoke/results/hybrid_results.json` |

Ngoài ra, report đầy đủ trước đó nằm tại `EXPERIMENT_REPORT.md`, trong đó:

- Phase 3 ablation nằm ở mục `4.6`.
- Phase 4 benchmark nằm ở mục `4.8`.
- Phase 5 context rescue và local-first nằm ở các mục sau Phase 4.

### 4.1. Gói Báo Cáo Theo Tiêu Chí Đánh Giá

Theo brief `CODING_AGENT_CURRENT_TASKS.md`, các kết quả hiện có đã được tái cấu trúc thành một gói report phục vụ viết luận văn. Phần này không rerun full benchmark, không gọi external LLM API và không thay đổi raw dataset; chỉ đọc lại các output CSV/JSON/Markdown hiện có để sinh bảng tổng hợp và diễn giải.

| File | Vai trò |
|---|---|
| `reports/output_inventory.md` | Inventory các evidence file, trạng thái tồn tại, thời điểm sửa cuối và vai trò |
| `reports/consolidated_experiment_metrics.csv` | CSV hợp nhất metric từ Microsoft cloud-monitoring, Phase 3, Phase 4, Phase 5, local-first, streaming replay và cache replay |
| `reports/evaluation_criteria_mapping.md` | Mapping từ tiêu chí đánh giá sang metric: alert quality, contextual effectiveness, cost, risk, real-time feasibility |
| `reports/tradeoff_analysis_table.md` | Bảng trade-off thesis-ready cho detector-only, LLM without RAG, hybrid RAG, BM25, context rescue, local-first, scheduler/cache, streaming |
| `reports/experiment_summary_no_rerun.md` | Báo cáo hợp nhất, nêu rõ kết quả được derive từ output hiện có và không rerun full LLM pipeline |
| `reports/thesis_insert_sections.md` | Các đoạn tiếng Việt có thể đưa vào luận văn, liên kết cost/risk với tiêu chí đánh giá |

Script sinh các file trên:

```powershell
py -B scripts/generate_evaluation_reports.py
```

Mục đích của gói report này là làm rõ luận điểm: cost/risk/trade-off không phải ghi chú phụ, mà là một phần của tiêu chí đánh giá thực nghiệm. Khi một biến thể cải thiện F1/recall/FPR, báo cáo cần đi kèm số LLM calls, context coverage, latency, API/cache/fallback/manual-review để đánh giá khả năng triển khai thực tế.

## 5. Phase 3 Ablation: Ảnh Hưởng Của RAG Và Gate

Config:

```text
nezha_setup/config/experiment_phase3_smoke.yaml
```

Kết quả trên 200 windows:

| Variant | Windows | Candidates | Precision | Recall | F1 | FPR | FP reduction vs detector | LLM calls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `detector_only` | 200 | 35 | 0.1714 | 0.3750 | 0.2353 | 0.1576 | 0.0000 | 0 |
| `llm_without_rag` | 200 | 35 | 0.0000 | 0.0000 | 0.0000 | 0.0815 | 0.4828 | 20 |
| `hybrid` | 200 | 35 | 0.2500 | 0.3750 | 0.3000 | 0.0978 | 0.3793 | 20 |
| `hybrid_no_gate` | 200 | 35 | 0.2500 | 0.3750 | 0.3000 | 0.0978 | 0.3793 | 20 |

Nhận xét:

- `detector_only` có recall 0.3750 nhưng false positive rate còn cao.
- `llm_without_rag` giảm false positive nhưng làm mất toàn bộ true positive trong lát cắt này, cho thấy LLM judge không có context là không đủ tin cậy.
- `hybrid` giữ recall ngang detector-only, đồng thời tăng precision từ 0.1714 lên 0.2500 và giảm FPR từ 0.1576 xuống 0.0978.
- `hybrid` và `hybrid_no_gate` trùng nhau trong run này vì budget/gate setting chưa tạo khác biệt về số call thực tế.

## 6. Phase 4 Benchmark: So Sánh Retrieval Backend Và RAG Setting

Config:

```text
nezha_setup/config/experiment_phase4_benchmark.yaml
```

Kết quả trên 300 windows:

| Variant | Windows | Candidates | Precision | Recall | F1 | FPR | FP reduction vs detector | LLM calls | Context coverage | Avg ctx | Retrieval ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `detector_only` | 300 | 40 | 0.1500 | 0.3750 | 0.2143 | 0.1197 | 0.0000 | 0 | 0.0000 | 0.0000 | 0.0000 |
| `llm_without_rag` | 300 | 40 | 0.0000 | 0.0000 | 0.0000 | 0.0352 | 0.7059 | 30 | 0.0000 | 0.0000 | 0.0000 |
| `hybrid_local_top6` | 300 | 40 | 0.3158 | 0.3750 | 0.3429 | 0.0458 | 0.6176 | 30 | 0.2250 | 0.1667 | 6.4785 |
| `hybrid_bm25_top6` | 300 | 40 | 0.3158 | 0.3750 | 0.3429 | 0.0458 | 0.6176 | 30 | 0.2250 | 0.1667 | 11.1465 |
| `hybrid_bm25_top10` | 300 | 40 | 0.3158 | 0.3750 | 0.3429 | 0.0458 | 0.6176 | 30 | 0.2250 | 0.2733 | 10.3172 |

Nhận xét:

- Cả 3 biến thể hybrid đều tốt hơn `detector_only` về precision, F1 và FPR.
- `llm_without_rag` tiếp tục thất bại về recall/F1, nghĩa là LLM judge cần context log/trace để ra quyết định hữu ích.
- `hybrid_local_top6`, `hybrid_bm25_top6`, và `hybrid_bm25_top10` có cùng classification metrics trong lát cắt này. Khác biệt chính nằm ở retrieval latency và số context trung bình.
- `hybrid_bm25_top10` lấy nhiều context hơn `top6`, nhưng chưa cải thiện F1. Điều này gợi ý bottleneck không nằm ở số lượng context, mà nằm ở việc detector bỏ lỡ một số fault.

## 7. Phase 5: Context Rescue Sau Benchmark

Phase 4 cho thấy bottleneck lớn là detector không tạo candidate cho một số `network_delay`. Phase 5 thêm `candidate_rescue`, cho phép promote candidate dựa trên tín hiệu log/trace gần fault window.

Config:

```text
nezha_setup/config/experiment_phase5_context_rescue.yaml
```

So sánh với mode hybrid tốt nhất ở Phase 4:

| Variant | Windows | Precision | Recall | F1 | FPR | TP | FP | FN | Candidate alerts | LLM calls | Context coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `hybrid_bm25_top6` Phase 4 | 300 | 0.3158 | 0.3750 | 0.3429 | 0.0458 | 6 | 13 | 10 | 40 | 30 | 0.2250 |
| `hybrid + context_rescue` Phase 5 | 300 | 0.6400 | 1.0000 | 0.7805 | 0.0317 | 16 | 9 | 0 | 55 | 55 | 0.4727 |

Nhận xét:

- Context rescue tăng recall từ 0.3750 lên 1.0000 và F1 từ 0.3429 lên 0.7805.
- Số candidate tăng từ 40 lên 55 do có 15 candidate được promote từ context signal.
- False positive rate giảm từ 0.0458 xuống 0.0317, dù số LLM calls tăng từ 30 lên 55.
- Đây là cải tiến quan trọng nhất trong chuỗi thí nghiệm, vì nó xử lý đúng điểm yếu mà Phase 4 phát hiện: detector metric-only không đủ nhạy với một số fault có dấu vết rõ hơn trong log/trace.

Lưu ý công bằng khi so sánh: Phase 5 không chỉ đổi backend RAG, mà thêm hành vi rescue và tăng LLM budget. Vì vậy bảng này nên được trình bày như một cải tiến kiến trúc sau benchmark, không phải ablation chỉ thay một biến duy nhất.

### 7.1. Phân Tích FP/FN Theo Fault Type, Service Và Pod Từ Audit Log

Phần này chỉ đọc lại audit JSONL hiện có, không chạy lại pipeline và không gọi LLM/API. Script sinh bảng:

```text
scripts/analyze_audit_failures.py
```

Output:

```text
reports/audit_failure_analysis.md
reports/audit_failure_by_fault_type.csv
reports/audit_failure_by_service.csv
reports/audit_failure_by_pod.csv
reports/audit_failure_hotspots.csv
```

Bảng theo fault type:

| Run | Fault type | Windows | Candidates | TP | FP | FN | Precision | Recall | F1 | Manual review |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `phase4_hybrid_bm25_top6` | `network_delay` | 8 | 0 | 0 | 0 | 8 | 0.0000 | 0.0000 | 0.0000 | 0 |
| `phase4_hybrid_bm25_top6` | `cpu_contention` | 8 | 6 | 6 | 0 | 2 | 1.0000 | 0.7500 | 0.8571 | 0 |
| `phase4_hybrid_bm25_top6` | `none` | 284 | 34 | 0 | 13 | 0 | 0.0000 | 0.0000 | 0.0000 | 21 |
| `phase5_context_rescue` | `network_delay` | 8 | 8 | 8 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 0 |
| `phase5_context_rescue` | `cpu_contention` | 8 | 8 | 8 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 0 |
| `phase5_context_rescue` | `none` | 284 | 39 | 0 | 9 | 0 | 0.0000 | 0.0000 | 0.0000 | 30 |
| `real_llm_500w_cache_replay` | `network_delay` | 40 | 39 | 14 | 0 | 26 | 1.0000 | 0.3500 | 0.5185 | 22 |
| `real_llm_500w_cache_replay` | `cpu_contention` | 29 | 29 | 15 | 0 | 14 | 1.0000 | 0.5172 | 0.6818 | 10 |
| `real_llm_500w_cache_replay` | `cpu_consumed` | 13 | 13 | 8 | 0 | 5 | 1.0000 | 0.6154 | 0.7619 | 5 |
| `real_llm_500w_cache_replay` | `exception` | 11 | 11 | 6 | 0 | 5 | 1.0000 | 0.5455 | 0.7059 | 4 |
| `real_llm_500w_cache_replay` | `return` | 7 | 7 | 4 | 0 | 3 | 1.0000 | 0.5714 | 0.7273 | 2 |
| `real_llm_500w_cache_replay` | `none` | 400 | 391 | 0 | 56 | 0 | 0.0000 | 0.0000 | 0.0000 | 335 |

Top FP/FN hotspot theo pod:

| Run | Type | Service | Pod/node | Fault type | Windows | FP | FN | TP | Candidates | Manual review | Final decisions |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| `phase4_hybrid_bm25_top6` | FP | cartservice | cartservice-579f59597d-wc2lz | none | 284 | 13 | 0 | 0 | 34 | 21 | suppress=250, manual_review=21, route_alert=13 |
| `phase4_hybrid_bm25_top6` | FN | cartservice | cartservice-579f59597d-wc2lz | network_delay | 8 | 0 | 8 | 0 | 0 | 0 | suppress=8 |
| `phase5_context_rescue` | FP | cartservice | cartservice-579f59597d-wc2lz | none | 284 | 9 | 0 | 0 | 39 | 30 | suppress=245, manual_review=30, route_alert=9 |
| `real_llm_500w_cache_replay` | FP | checkoutservice | checkoutservice-578fcf4766-9csqn | none | 10 | 10 | 0 | 0 | 10 | 0 | route_alert=10 |
| `real_llm_500w_cache_replay` | FP | frontend | frontend-579b9bff58-t2dbm | none | 9 | 8 | 0 | 0 | 9 | 1 | route_alert=8, manual_review=1 |
| `real_llm_500w_cache_replay` | FP | paymentservice | paymentservice-9cdb6588f-554sm | none | 9 | 8 | 0 | 0 | 9 | 1 | route_alert=8, manual_review=1 |
| `real_llm_500w_cache_replay` | FP | shippingservice | shippingservice-7b598fc7d-lmggd | none | 9 | 8 | 0 | 0 | 9 | 1 | route_alert=8, manual_review=1 |
| `real_llm_500w_cache_replay` | FN | ts-food-service | ts-food-service-f5756978c-6sb8t | network_delay | 4 | 0 | 4 | 0 | 4 | 4 | manual_review=4 |
| `real_llm_500w_cache_replay` | FN | adservice | adservice-5f6585d649-fnmft | cpu_consumed | 3 | 0 | 3 | 0 | 3 | 3 | manual_review=3 |
| `real_llm_500w_cache_replay` | FN | currencyservice | currencyservice-cf787dd48-vpjrd | network_delay | 4 | 0 | 2 | 2 | 4 | 1 | route_alert=2, suppress=1, manual_review=1 |

Diễn giải:

- Phase 4 bỏ sót toàn bộ `network_delay` trên `cartservice` vì detector không tạo candidate (`8 FN`, `0 candidates`). Đây là bằng chứng trực tiếp cho bottleneck mà Phase 5 xử lý.
- Phase 5 context rescue loại bỏ FN trên lát cắt 300 windows (`network_delay` và `cpu_contention` đều recall 1.0000), nhưng vẫn còn `9 FP` trên normal windows của `cartservice`.
- Real-LLM 500-window cache replay cho thấy `network_delay` là fault type khó nhất (`26 FN`, recall 0.3500). Nhiều FN không phải do gọi LLM lỗi, mà do policy an toàn đưa alert sang `manual_review` hoặc suppress khi chưa đủ xác nhận.
- FP trong 500-window run tập trung ở normal windows (`fault_type=none`) của `checkoutservice`, `frontend`, `paymentservice`, `shippingservice`, `recommendationservice`, `currencyservice`, và `emailservice`.

## 8. Local-First Ollama Judge Với Gemini API Fallback

Mục tiêu:

```text
Candidate Alert + Retrieved Context
-> Local Ollama Judge
-> Nếu local output hợp lệ và confidence đủ cao: dùng kết quả local
-> Nếu local lỗi, uncertain, confidence thấp, hoặc anomaly_score quá cao: gọi Gemini API fallback
```

Config:

```text
nezha_setup/config/experiment_local_first_ollama_smoke.yaml
```

So sánh smoke test với Gemini-only Phase 5 smoke, đều trên 45 windows:

| Variant | Windows | Precision | Recall | F1 | FPR | LLM calls | API fallback calls | Local valid JSON | Providers | Avg LLM ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| `Gemini-only` Phase 5 smoke | 45 | 0.6667 | 1.0000 | 0.8000 | 0.1429 | 6 | n/a | n/a | Gemini | 338.2988 |
| `Local-first Ollama + Gemini fallback` | 45 | 0.6250 | 1.0000 | 0.7692 | 0.1714 | 6 | 4 | 3 | Ollama, Gemini | 4585.0120 |

Nhận xét:

- Local-first đã hoạt động đúng chiến lược: local Ollama xử lý trước, API chỉ được gọi khi local uncertain/lỗi/không đủ confidence.
- Kết quả giữ recall 1.0000, F1 giảm nhẹ so với Gemini-only smoke.
- Do model local `qwen2.5:1.5b` nhỏ và chạy local, latency LLM cao hơn rõ rệt trong run này.
- API fallback vẫn cần thiết: 4/6 LLM calls phải fallback sang Gemini. Điều này cho thấy local-first khả thi về workflow, nhưng local model nhỏ chưa đủ ổn định để thay API hoàn toàn.

## 9. Streaming Replay

Streaming replay đã được triển khai để xử lý window theo thứ tự thời gian và chỉ nạp context đến watermark hiện tại, tránh việc batch mode vô tình dùng context từ tương lai.

Output hiện có:

```text
nezha_setup/outputs/phase3_streaming/results/streaming_hybrid_summary.md
```

Kết quả smoke 50 windows:

| Mode | Windows | Precision | Recall | F1 | FPR | LLM calls | Retrieval backend |
|---|---:|---:|---:|---:|---:|---:|---|
| `streaming_hybrid` | 50 | 0.5556 | 0.3333 | 0.4167 | 0.1143 | 9 | `local_hashing` |

Nhận xét: streaming replay chủ yếu chứng minh pipeline có thể chạy theo thời gian và không dùng context tương lai. Kết quả này không nên so sánh trực tiếp với Phase 4/5 vì số windows và setting backend khác nhau.

## 10. Provider Thay Thế Gemini Và Cache Chống Rate Limit

Do Gemini free tier dễ gặp `429`, pipeline đã bổ sung các provider real-LLM thay thế:

| Provider | Kiểu API | Env key | Config |
|---|---|---|---|
| Groq | OpenAI-compatible chat completions | `GROQ_API_KEY`, optional `GROQ_MODEL` | `nezha_setup/config/experiment_real_llm_groq_stratified.yaml` |
| OpenRouter | OpenAI-compatible chat completions | `OPENROUTER_API_KEY`, optional `OPENROUTER_MODEL` | `nezha_setup/config/experiment_real_llm_openrouter_stratified.yaml` |
| Cohere | Cohere Chat v2 adapter | `COHERE_API_KEY`, optional `COHERE_MODEL` | `nezha_setup/config/experiment_real_llm_cohere_stratified.yaml` |

Các real-LLM stratified run nên dùng cache:

```powershell
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_real_llm_groq_stratified.yaml --cache-path nezha_setup/outputs/llm_response_cache.jsonl --output-mode groq_stratified
```

Cache được bật bằng `LLM_RESPONSE_CACHE` hoặc `--cache-path`. Audit/evaluation hiện ghi thêm:

- `llm_cache_hit`
- `actual_api_call`
- `llm_retry_count`
- `llm_backoff_sleep_ms`
- `cache_hit_rate`

Nhờ đó báo cáo có thể phân biệt số LLM decision logic với số API call thật, tránh làm sai lệch đánh giá chi phí/quota khi chạy lại thí nghiệm.

Kiểm thử ngày 2026-06-01:

| Run | Provider | Windows | JSON valid | Actual API calls | Cache hits | Avg LLM latency |
|---|---|---:|---:|---:|---:|---:|
| `openrouter_stable_cache_seed` | OpenRouter `openrouter/free` | 1 | 1.0 | 1 | 0 | 19897.0667 ms |
| `openrouter_stable_cache_hit` | OpenRouter `openrouter/free` | 1 | 1.0 | 0 | 1 | 14.3761 ms |
| `cohere_stratified_smoke_v2` | Cohere `command-r-08-2024` | 1 | 1.0 | 1 | 0 | 3831.7613 ms |
| `groq_stratified_smoke2` | Groq env model | 1 | 0.0 | 1 | 0 | API returned `403 Forbidden` |

Trong quá trình kiểm thử cache, phát hiện `alert_id` trước đó dùng Python `hash()`, làm prompt thay đổi giữa các process và khiến cache miss khi rerun. Phần này đã được đổi sang SHA-256 deterministic theo `window_id` và `anomaly_score`, nên cache hiện có thể dùng để giảm API call thật sau lỗi `429`.

Kiểm thử Gemini một-window ngày 2026-06-01:

| Run | Model | Windows | JSON valid | Actual API calls | Error | Avg LLM latency |
|---|---|---:|---:|---:|---|---:|
| `gemini25_flash_one_window` | `gemini-2.5-flash` | 1 | 0.0 | 1 | `HTTP Error 429: Too Many Requests` | 70964.3101 ms |
| `gemini20_flash_one_window` | `gemini-2.0-flash` | 1 | 0.0 | 1 | `HTTP Error 429: Too Many Requests` | 69546.8843 ms |

Kết luận: ngay cả khi chỉ gửi 1 khung thời gian và không dùng streaming replay, cả Gemini 2.5 Flash và 2.0 Flash vẫn bị `429`. Điều này cho thấy giới hạn hiện tại nằm ở quota/API key hoặc project-level rate limit. Để tránh retry kéo dài khi smoke test Gemini, hai config one-window đã đặt `max_retries: 0`; các run lớn nên tiếp tục ưu tiên OpenRouter/Cohere hoặc local-first + API fallback có cache.

## 11. Priority-Aware Local-First Scheduler

Để xử lý vấn đề `429 Too Many Requests`, pipeline đã bổ sung tầng `llm_scheduler` trong `src/llm/scheduler.py`. Scheduler không thay thế detector/RAG/LLM judge, mà quyết định khi nào được phép dùng API:

```text
Candidate Alert + Retrieved Context
-> priority_score
-> high priority: allow API fallback
-> low/medium priority: local-only hoặc defer API
-> API 429: bật cooldown, các alert tiếp theo bị defer/local-only tùy config
```

Audit/evaluation có thêm:

- `scheduler_action`: `call`, `local_only`, hoặc `defer`
- `scheduler_reason`: ví dụ `high_priority`, `below_defer_priority`, `api_cooldown_active`
- `priority_score`
- `scheduled_delay_seconds`
- `api_deferred`
- Summary: `scheduler_deferred`, `scheduler_local_only`, `scheduler_api_allowed`, `api_deferred`, `avg_priority_score`

Config kiểm thử:

```text
nezha_setup/config/experiment_local_first_scheduler_openrouter_smoke.yaml
```

Kết quả smoke ngày 2026-06-01:

| Run | Windows | Scheduler action | API fallback | Cache hit | Actual API call | JSON valid | E2E latency |
|---|---:|---|---:|---:|---:|---:|---:|
| `local_first_scheduler_openrouter_one_window_v2` | 1 | `call` / `high_priority` | 1 | 1 | 0 | 1.0 | 89.0386 ms |

Diễn giải: alert có `anomaly_score=0.999` nên scheduler cho phép API path. Ollama local trả JSON hợp lệ nhưng do rule `high_anomaly_score`, hệ thống vẫn dùng API fallback. OpenRouter response được lấy từ cache nên không phát sinh request API thật.

## 12. So Sánh Local Ollama Models

Sau khi cài thêm `qwen2.5:3b` và `llama3.2:3b`, hai model được kiểm thử local-only trên cùng một positive window, không dùng Gemini/OpenRouter/Cohere fallback.

Config:

```text
nezha_setup/config/experiment_local_only_qwen25_3b_one_window.yaml
nezha_setup/config/experiment_local_only_llama32_3b_one_window.yaml
```

Kết quả ngày 2026-06-01:

| Run | Model | JSON valid | Decision | Confidence | Tokens in/out | LLM latency | Actual external API calls |
|---|---|---:|---|---:|---:|---:|---:|
| `local_only_qwen25_3b_one_window_v2` | `qwen2.5:3b` | 1.0 | `route_alert` | 0.999 | 610 / 131 | 16741.6824 ms | 0 |
| `local_only_llama32_3b_one_window_v2` | `llama3.2:3b` | 1.0 | `route_alert` | 0.999 | 510 / 89 | 12442.8742 ms | 0 |

Nhận xét:

- Cả hai model đều tuân thủ JSON schema trong test một window.
- `llama3.2:3b` nhanh hơn khoảng 25.7% trong lần smoke này và sinh output ngắn hơn.
- `qwen2.5:3b` trả lý do và action cụ thể hơn cho ngữ cảnh checkout trace, nhưng latency cao hơn.
- Với máy hiện tại chạy CPU/local RAM, `llama3.2:3b` phù hợp hơn nếu ưu tiên latency; `qwen2.5:3b` phù hợp hơn nếu ưu tiên giải thích chi tiết và structured reasoning.

Khuyến nghị cho pipeline hiện tại: dùng `llama3.2:3b` làm local-first default để giảm latency, giữ `qwen2.5:3b` làm biến thể ablation hoặc khi cần output giàu ngữ cảnh hơn. Alert high-priority vẫn nên qua scheduler để được API fallback/cache khi cần.

## 13. Chiến Lược Điều Phối Local Models

Sau khi Gemini tiếp tục bị `429`, chiến lược điều phối được chỉnh lại để ưu tiên local LLM và chỉ dùng API như lựa chọn sau cùng. Phiên bản local hiện tại không gọi external API:

```text
Candidate Alert + Retrieved Context
-> Scheduler tính priority_score
-> Primary local judge: llama3.2:3b
-> Nếu primary invalid JSON, uncertain, hoặc confidence < 0.80:
   -> Fallback local judge: qwen2.5:3b
-> Nếu LLM kết luận true_alert nhưng không có evidence:
   -> manual_review thay vì route_alert
-> External API fallback chỉ bật ở config khác, không bật trong local cascade này
```

Config triển khai:

```text
nezha_setup/config/experiment_local_model_cascade_llama_qwen.yaml
```

Tham số chính:

| Nhóm | Tham số | Giá trị |
|---|---|---|
| Detector | `name` | `isolation_forest` |
| Detector | `threshold` | `0.95` |
| Detector | `n_estimators` | `100` |
| Retrieval | `vector_db` | `hybrid_bm25` |
| Retrieval | `top_k` | `6` |
| Retrieval | `time_margin_minutes` | `8` |
| Scheduler | `enabled` | `true` |
| Scheduler | `high_priority_threshold` | `0.98` |
| Scheduler | `defer_below_priority` | `0.80` |
| Primary local | `local_model` | `llama3.2:3b` |
| Primary local | `local_timeout_seconds` | `120` |
| Primary local | `local_max_output_tokens` | `512` |
| Local fallback | `fallback_model` | `qwen2.5:3b` |
| Local fallback | `fallback_timeout_seconds` | `120` |
| Local fallback | `fallback_max_output_tokens` | `512` |
| Fallback rule | `local_confidence_threshold` | `0.80` |
| Fallback rule | `fallback_on_uncertain` | `true` |
| Fallback rule | `high_anomaly_fallback_threshold` | `1.1` |
| Decision guard | `require_evidence_for_true_alert` | `true` |

Lý do đặt `high_anomaly_fallback_threshold=1.1`: với local CPU, nếu fallback chỉ vì anomaly cao thì mỗi alert quan trọng sẽ chạy cả hai model, làm latency quá cao. Vì vậy fallback local chỉ dùng khi primary model thật sự không đáng tin: JSON lỗi, nhãn `uncertain`, hoặc confidence thấp.

Kết quả tổng hợp local LLM ngày 2026-06-01:

| Run | Slice | Precision | Recall | F1 | FPR | LLM calls | Model fallback | External API calls | JSON valid | Avg LLM latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `local_model_cascade_1p1n_v3` | 1 positive + 1 negative | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 1 | 0 | 1.0000 | 59988.9575 ms |

Chi tiết đáng chú ý:

- Positive window `network_delay` được Llama đánh giá confidence thấp và fallback sang Qwen; Qwen trả `true_alert`, evidence đầy đủ, route đúng.
- Negative window có anomaly score cao nhưng không có retrieved context; Llama trả `true_alert` với evidence rỗng. Decision guard đã chuyển sang `manual_review`, tránh false positive.
- Run `3 positive + 3 negative` đã thử hai lần nhưng vượt timeout 6 phút trên CPU. Điều này cho thấy local cascade hai model phù hợp cho alert đã được ưu tiên, chưa phù hợp để xử lý nhiều candidate đồng bộ nếu không có queue/cache/batching.

Kết luận chiến lược: `llama3.2:3b` nên là primary local model vì nhanh hơn; `qwen2.5:3b` nên là fallback local có điều kiện. Với cảnh báo không có context/evidence, không nên route trực tiếp dù LLM confidence cao; đưa vào manual review hoặc chờ thêm context là an toàn hơn.

## 14. Chiến Lược Single Local + Gemini Lite Fallback

Sau khi cập nhật Gemini API key, chiến lược được điều chỉnh theo yêu cầu không chạy đồng thời hai local model. Config mới chỉ dùng một local model:

```text
nezha_setup/config/experiment_local_llama_gemini_lite_scheduler.yaml
```

Luồng xử lý:

```text
Candidate Alert + Retrieved Context
-> Primary local judge: llama3.2:3b
-> Nếu high priority hoặc local không chắc:
   -> Gemini 2.5 Flash Lite fallback
-> Nếu Gemini trả 429:
   -> bật scheduler cooldown
   -> alert tiếp theo bị chặn API fallback và xử lý local-only/manual_review
```

Tham số chính:

| Nhóm | Tham số | Giá trị |
|---|---|---|
| Primary local | `local_model` | `llama3.2:3b` |
| Primary local | `local_max_output_tokens` | `512` |
| Primary local | `local_timeout_seconds` | `120` |
| API fallback | `fallback_provider` | `gemini` |
| API fallback | `fallback_model` | `gemini-2.5-flash-lite` |
| API fallback | `fallback_max_output_tokens` | `512` |
| API fallback | `fallback_max_retries` | `0` |
| Scheduler | `high_priority_threshold` | `0.98` |
| Scheduler | `cooldown_on_429_seconds` | `300` |
| Scheduler | `max_api_calls_per_run` | `2` |
| Gate | `max_llm_calls_per_minute` | `0` |
| Decision guard | `require_evidence_for_true_alert` | `true` |

Kết quả chạy với Gemini key mới ngày 2026-06-01:

| Run | Slice | Precision | Recall | F1 | FPR | LLM calls | API fallback calls | Actual API calls | API deferred | Cache hits | JSON valid | Avg LLM latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `local_llama_gemini_lite_1p1n_v3` | 1 positive + 1 negative | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 2 | 1 | 1 | 1 | 2 | 1.0000 | 560.5661 ms |

Kiểm tra lại với `.env` của workspace hiện tại trước khi nạp credit:

- Runner đã được chỉnh để chỉ tự load `C:\Working\Internship1\.env`; không còn tự load `C:\Working\IELTSApp\.env`.
- Request tối thiểu trực tiếp tới `gemini-2.5-flash-lite` vẫn trả `HTTP 429`.
- Response body của Gemini ghi rõ: `Your prepayment credits are depleted` với status `RESOURCE_EXHAUSTED`.

Diễn giải:

- Gemini `gemini-2.5-flash-lite` vẫn trả `HTTP Error 429: Too Many Requests` với API key mới trong workspace, nhưng nguyên nhân cụ thể là hết prepayment credits/project billing credits, không phải do pipeline gửi quá nhiều request trong run hiện tại.
- Sau lỗi 429 đầu tiên, scheduler đã bật cooldown đúng như mong muốn: alert thứ hai có `scheduler_action=local_only`, `scheduler_reason=api_cooldown_active`, `actual_api_call=false`.
- Không còn chạy hai local model. `primary_local_models=['ollama:llama3.2:3b']`.
- Vì API fallback thất bại và local model không đủ chắc, positive alert được đưa về `manual_review` thay vì route sai; negative alert thiếu evidence cũng được đưa về `manual_review`.
- Chỉ số classification trên lát cắt 1p1n là thấp vì hệ thống ưu tiên an toàn khi API unavailable: không route alert khi thiếu xác nhận/evidence.

Kết luận chiến lược: với Gemini còn bị 429, cấu hình này phù hợp hơn cho thí nghiệm khả thi vì nó kiểm soát được API call thật (`actual_api_calls=1`), bật cooldown sau lỗi, và không làm máy quá tải bằng hai local models. Tuy nhiên để cải thiện recall khi API unavailable, cần cải thiện prompt/local decision hoặc dùng một API fallback khác đã hoạt động ổn hơn như OpenRouter/Cohere.

### Sau khi nạp credit Gemini

Sau khi cập nhật API key mới trong `C:\Working\Internship1\.env` và nạp credit, request tối thiểu tới `gemini-2.5-flash-lite` trả `200 OK`. Runner hiện chỉ tự load `.env` của workspace hiện tại.

Kết quả Gemini-only với key paid mới:

| Run | Slice | Precision | Recall | F1 | FPR | LLM calls | Actual API calls | JSON valid | Avg LLM latency | Cost estimate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `gemini25_flash_lite_1p1n_paid_key` | 1 positive + 1 negative | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 2 | 1.0000 | 1895.1679 ms | not configured |
| `gemini25_flash_lite_paid_3p3n` | 3 positive + 3 negative | 0.6000 | 1.0000 | 0.7500 | 0.6667 | 6 | 6 | 1.0000 | 2175.8783 ms | 0.0014679 USD |
| `local_llama_gemini_lite_3p3n_paid_key` | 3 positive + 3 negative | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 6 | 6 | 1.0000 | 41246.5763 ms | 0.0014679 USD API-only |
| `gemini25_flash_lite_500w_paid_key` | 100 positive + 400 negative | 0.1776 | 0.8400 | 0.2932 | 0.9725 | 120 | 120 | 1.0000 | 754.4694 ms | 0.0256230 USD |
| `gemini25_flash_lite_500w_budget_manual_review_cache_replay` | 100 positive + 400 negative | 0.4563 | 0.4700 | 0.4631 | 0.1400 | 120 | 0, cache hit 120 | 1.0000 | 0.0605 ms | 0 new USD; 0.0256230 USD equivalent |

Config dùng cho run 3p3n:

```text
nezha_setup/config/experiment_real_llm_stratified.yaml
```

Output chính:

```text
nezha_setup/outputs/real_llm_stratified/results/gemini25_flash_lite_paid_3p3n_summary.md
nezha_setup/outputs/real_llm_stratified/audit/gemini25_flash_lite_paid_3p3n_audit.jsonl
```

Nhận xét:

- Gemini `gemini-2.5-flash-lite` hiện đã chạy bình thường sau khi nạp credit.
- `json_valid_rate=1.0`, không còn lỗi `429`.
- Recall tốt trên lát cắt 3p3n, nhưng false positive vẫn cao vì một số negative có anomaly score cao và thiếu/không đủ context; model vẫn có xu hướng route alert. Cần giữ guard `require_evidence_for_true_alert=true` trong các config mới để giảm false positive.
- Sau khi Ollama API local hoạt động lại, chiến lược single-local + Gemini fallback chạy được trên 3p3n. Kết quả đạt F1 1.0000 trên lát cắt nhỏ này, nhưng latency trung bình tăng lên khoảng 41.25s vì mỗi alert chạy `llama3.2:3b` trước rồi mới fallback sang Gemini.
- Run 500 windows chỉ dùng Gemini API đã chạy thành công với `gemini-2.5-flash-lite`. Tuy nhiên kết quả đầu tiên cho thấy giới hạn `max_total_calls=120` là yếu tố chi phối: trong 500 windows có 490 candidate alerts, nhưng chỉ 120 candidate được LLM đánh giá; 370 candidate còn lại rơi vào `llm_budget_exhausted`. Policy cũ route alert khi hết budget, làm false positive rate tăng lên 0.9725.
- Sau khi rà lại `CODEX_EXPERIMENT_GUIDE.md` và `SKILL.md`, policy khi hết LLM budget đã được đổi thành config-first: `decision.llm_budget_exhausted_action`, mặc định `manual_review`. Cache replay cùng 500 windows và cùng 120 Gemini responses cũ cho thấy FPR giảm từ 0.9725 xuống 0.1400, precision tăng từ 0.1776 lên 0.4563, F1 tăng từ 0.2932 lên 0.4631. Recall giảm từ 0.8400 xuống 0.4700 vì 370 candidate hết budget không còn được tính là confirmed routed alert mà chuyển sang manual review. Đây là cách tính đúng hơn cho thí nghiệm feasibility: alert chưa được LLM xác nhận không nên bị đếm như cảnh báo chắc chắn.

Kiểm chứng model Gemini/Gemma thay thế:

| Run | Model | Slice | Precision | Recall | F1 | FPR | API calls | JSON valid | Input tokens | Output tokens | Kết luận |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `gemini3_flash_preview_1p1n_smoke` | `gemini-3-flash-preview` | 1 positive + 1 negative | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 2 | 1.0000 | 2,148 | 314 | Chạy được với schema JSON hiện tại |
| `gemma4_26b_1p1n_smoke` | `gemma-4-26b-a4b-it` | 1 positive + 1 negative | 0.5000 | 1.0000 | 0.6667 | 1.0000 | 2 | 0.0000 | 209 | 0 | Trả `HTTP 400`, chưa phù hợp với Gemini JSON schema adapter hiện tại |

Danh sách model khả dụng từ Gemini API hiện tại có `gemini-3-flash-preview`, `gemini-3.5-flash`, `gemini-3.1-flash-lite`, `gemini-2.5-flash-lite`, `gemma-4-26b-a4b-it`, và `gemma-4-31b-it`. Với thí nghiệm hiện tại, `gemini-2.5-flash-lite` vẫn là lựa chọn chính vì quota tốt và chi phí thấp; `gemini-3-flash-preview` chỉ nên dùng để smoke/đối chiếu nhỏ trước khi biết rõ quota và pricing.

Token, quota và chi phí:

| Scope | Requests | Input tokens | Output tokens | Total tokens | Official estimate USD | Official estimate VND @ 25,500 | Chi phí thực nghiệm |
|---|---:|---:|---:|---:|---:|---:|---:|
| `gemini25_flash_lite_paid_3p3n` | 6 | 7,455 | 1,806 | 9,261 | 0.0014679 | 37.43 VND | khoảng 15.03 VND nếu nội suy theo dashboard |
| `local_llama_gemini_lite_3p3n_paid_key` phần Gemini fallback | 6 | 7,455 | 1,806 | 9,261 | 0.0014679 | 37.43 VND | khoảng 15.03 VND nếu nội suy theo dashboard |
| `gemini25_flash_lite_500w_paid_key` | 120 | 131,046 | 31,296 | 162,342 | 0.0256230 | 653.39 VND | khoảng 263.47 VND nếu nội suy theo dashboard |
| `gemini25_flash_lite_500w_budget_manual_review_cache_replay` | 0 request mới, 120 cache hits | 131,046 cached | 31,296 cached | 162,342 cached | 0 new; 0.0256230 equivalent | 0 VND mới; 653.39 VND equivalent | 0 VND phát sinh thêm; khoảng 263.47 VND nếu gọi thật |
| Dashboard Google AI Studio trước run local-first, ngày 2026-06-01 | 10 | 11,340 | 2,832 | 14,172 | 0.0022668 | 57.80 VND | 23 VND đã quan sát |
| Dashboard Google AI Studio sau run local-first, ngày 2026-06-01 | 16 | 18,795 | 4,638 | 23,433 | 0.0037347 | 95.23 VND | khoảng 38.03 VND nếu nội suy từ 23 VND |
| Phần tăng thêm trên dashboard sau run local-first | 6 | 7,455 | 1,806 | 9,261 | 0.0014679 | 37.43 VND | khoảng 15.03 VND |
| Ước tính Flash Lite sau khi cộng run 500 windows | 136 | 149,841 | 35,934 | 185,775 | 0.0293577 | 748.62 VND | khoảng 301.50 VND nếu nội suy theo dashboard |

Official estimate dùng giá `gemini-2.5-flash-lite`: 0.10 USD / 1M input tokens và 0.40 USD / 1M output tokens. Google AI Studio dashboard đang báo quota theo token/request, không phải lúc nào cũng trùng trực tiếp với tiền bị trừ trong billing do credit, rounding, tax/currency conversion hoặc cách Google ghi nhận spend theo tài khoản. Vì người dùng quan sát mốc thực tế 23 VND tại 14,172 tokens, report dùng thêm đơn giá thực nghiệm:

```text
23 VND / 14,172 tokens = khoảng 0.00162 VND/token
23 VND / 10 requests = khoảng 2.30 VND/request
```

Theo đơn giá thực nghiệm này, quota hiện tại trên Google AI Studio sau run local-first là 23,433 tokens và 16 requests, tương ứng khoảng 38.03 VND tổng cộng. Phần tăng thêm của run local-first là 9,261 tokens và 6 requests, tương ứng khoảng 15.03 VND. Khi lập kế hoạch chạy thí nghiệm lớn hơn, nên dùng official estimate làm trần an toàn, còn chi phí thực nghiệm từ dashboard dùng để đối chiếu billing thực tế.

Sau run 500 windows, phần tăng thêm riêng của `gemini-2.5-flash-lite` là 120 requests, 131,046 input tokens và 31,296 output tokens. Nếu cộng vào quota Flash Lite trước đó, tổng Flash Lite dự kiến là 136 requests, 149,841 input tokens và 35,934 output tokens. Số này cần đối chiếu lại trên Google AI Studio dashboard vì dashboard có thể làm tròn và phân tách theo model.

## 15. Rà Soát Theo Coding Agent Guide

Nguồn đối chiếu:

```text
CODEX_EXPERIMENT_GUIDE.md
SKILL.md
hybrid_monitoring_architecture_ascii.txt
```

| Yêu cầu trong guide | Hiện trạng repo | Bằng chứng | Đánh giá |
|---|---|---|---|
| Pipeline metric -> detector -> candidate -> gate -> RAG -> LLM judge -> decision/audit | Đã triển khai end-to-end | `src/main.py`, `src/decision/policy.py`, `src/retrieval/`, `src/llm/`, audit JSONL trong `nezha_setup/outputs/**/audit/` | Đạt cho feasibility experiment |
| Config-first, không hard-code tham số thí nghiệm | Các tham số chính nằm trong YAML; vừa bổ sung `decision.llm_budget_exhausted_action` | `config/experiment.yaml`, `nezha_setup/config/experiment_real_llm_stratified.yaml`, `nezha_setup/config/experiment_real_llm_stratified_cache_replay.yaml` | Đạt; policy mới có thể đổi bằng config |
| Sliding window và normalization | Có metric preprocessing và tests | `src/preprocessing/metric_preprocessing.py`, `tests/test_preprocessing.py` | Đạt |
| Detector nhẹ, ưu tiên Isolation Forest | Đã có real Isolation Forest | `src/detectors/isolation_forest_detector.py`, `src/detectors/factory.py` | Đạt |
| Alert candidate có ID ổn định, time window, node/service, anomaly score, metric snapshot | Đã có builder và test ổn định `alert_id` | `src/decision/policy.py`, `tests/test_policy.py` | Đạt |
| Không gọi LLM cho mọi window; phải đo calls avoided | Gate và budget đã hoạt động; run 500 windows có 500 windows nhưng chỉ 120 LLM calls | `llm_calls=120`, `llm_calls_avoided=380`, `llm_budget_exhausted=370` trong summary 500w | Đạt; cần scheduler hàng đợi thật nếu muốn real-time production hơn |
| Log/event preprocessing và metadata | Có preprocessing log/trace thành context events | `src/preprocessing/log_preprocessing.py`, `nezha_setup/processed/logs.jsonl`, `DATASET_REPORT.md` | Đạt ở mức dataset Nezha; chưa phải pipeline Kafka/Flink |
| Context store/vector DB có metadata filtering và hybrid retrieval | Đã dùng local hybrid BM25/hash + metadata/time scoring; không phụ thuộc FAISS do setup khó | `src/retrieval/context_store.py`, `src/retrieval/retriever.py`, Phase 4 benchmark | Đạt cho local experiment; Chroma/FAISS vẫn là hướng mở rộng |
| Prompt ngắn, có alert + metric + context + JSON instruction | Đã có prompt composer và token counting | `src/llm/prompt_composer.py`, audit fields `prompt_token_count`, `context_token_count` | Đạt |
| LLM output JSON schema và validate | Đã validate schema; real Gemini JSON valid 1.0 trên các run Flash Lite | `src/llm/schema.py`, `tests/test_llm_schema.py`, summaries real LLM | Đạt |
| Decision/fallback đúng nhánh: false positive suppress, uncertain/low confidence manual review, lỗi LLM fallback | Đã có decision layer; vừa sửa nhánh hết LLM budget sang manual review thay vì route alert | `src/decision/policy.py`, `src/main.py`, `tests/test_policy.py` | Đạt hơn so với bản trước; lỗi JSON/API vẫn fallback theo detector như guide |
| Audit log lưu latency, token, context, response, final decision | Audit JSONL có đủ trường detector/retrieval/LLM latency, token, cache, retry, final decision | `src/main.py`, `src/evaluation/metrics.py`, audit files | Đạt |
| Có baseline detector-only, LLM without RAG, hybrid | Đã có Phase 3/4 ablation và benchmark | Section 5-6 của report, `nezha_setup/outputs/phase3_smoke/`, `phase4_benchmark/` | Đạt |
| Đo precision/recall/F1/FPR, latency, token/cost, JSON valid, fallback/cache | Summary ghi đầy đủ các metric này | `src/evaluation/metrics.py`, `src/evaluation/report.py`, các summary md/csv/json | Đạt |
| Không gọi API thật trong unit tests | Tests dùng mock/provider fake/cache; real API chỉ chạy qua experiments | `tests/test_llm_cache_and_providers.py`, `tests/test_ollama_judge.py` | Đạt |
| README và `.env.example` rõ ràng | Đã cập nhật README cho 500-window/cache replay; `.env.example` đã sửa thành template provider keys | `README.md`, `.env.example` | Đạt |

Thay đổi code sau khi rà guide:

- `src/decision/policy.py`: thêm `decide_llm_budget_exhausted()`, mặc định trả `manual_review`.
- `src/main.py`: dùng decision policy mới khi `max_llm_calls` đã hết.
- `tests/test_policy.py`: thêm test default manual review và test override `route_alert`.
- `config/experiment.yaml` và `nezha_setup/config/experiment_real_llm_stratified.yaml`: thêm `llm_budget_exhausted_action: manual_review`.
- `nezha_setup/config/experiment_real_llm_stratified_cache_replay.yaml`: thêm config replay để tái tính 500 windows bằng cache, không phát sinh request mới.
- `.env.example`: sửa thành template đúng cho `GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `COHERE_API_KEY` và optional model env.
- `README.md`: thêm lệnh run 500-window và cache replay, ghi rõ policy budget mới.

Đánh giá sau khi thực hiện lại theo guide:

- Về kiến trúc, pipeline hiện bám sát guide hơn bản trước vì các alert chưa được LLM xác nhận do hết budget không còn bị route như true alert. Điều này làm kết quả đánh giá ít lạc quan giả và phản ánh đúng khả năng vận hành real-time có giới hạn quota.
- Về kết quả 500 windows, policy mới giảm mạnh false positive nhưng làm tăng manual review. Đây là trade-off hợp lý ở giai đoạn feasibility: hệ thống ưu tiên không tạo cảnh báo sai hàng loạt khi LLM budget cạn.
- Về chi phí, cache replay chứng minh cơ chế cache hoạt động đúng: 120/120 LLM decisions được đọc từ cache, `actual_api_calls=0`, `cache_hit_rate=1.0`, không tốn thêm quota Google AI Studio.
- Giới hạn còn lại: 500-window run vẫn chỉ có 120 LLM-confirmed candidates vì budget. Muốn đánh giá chất lượng model trên toàn bộ 490 candidates cần tăng `max_total_calls`, dùng batch/defer queue, hoặc chạy theo nhiều đợt có cache và quota planning.

## 16. Kết Luận Đưa Vào Báo Cáo

1. Nezha là dataset phù hợp nhất cho kiến trúc hybrid vì có đủ metric, log, trace và fault labels. Microsoft cloud-monitoring-dataset hữu ích cho detector baseline nhưng thiếu context vận hành.
2. So sánh mode cho thấy LLM không có RAG không đủ tin cậy: `llm_without_rag` làm giảm false positive nhưng mất recall/F1 trong các lát cắt Phase 3 và Phase 4.
3. Hybrid RAG cải thiện rõ so với detector-only: trong Phase 4, F1 tăng từ 0.2143 lên 0.3429 và FPR giảm từ 0.1197 xuống 0.0458.
4. Context rescue là cải tiến lớn nhất: trên 300 windows, F1 tăng lên 0.7805 và recall đạt 1.0000, đồng thời FPR giảm xuống 0.0317.
5. Local-first Ollama + Gemini fallback đã chạy được end-to-end. Tuy nhiên model local nhỏ cần fallback API để đảm bảo chất lượng và schema hợp lệ.
6. Với real-LLM API, Groq/OpenRouter/Cohere và response cache giúp giảm phụ thuộc Gemini khi bị rate limit. Các chỉ số cache/API call thật cần được báo cáo riêng khi đánh giá chi phí và độ khả dụng.
7. Sau khi rà lại coding agent guide, policy hết LLM budget đã được sửa từ route alert sang manual review. Trên 500 windows, FPR giảm từ 0.9725 xuống 0.1400 và F1 tăng từ 0.2932 lên 0.4631 khi replay bằng cache cùng 120 Gemini responses.
8. Các bảng so sánh mode đã có sẵn trong thư mục output, đặc biệt `phase3_smoke/ablation` và `phase4_benchmark/results`. Report này đã gom lại các bảng quan trọng để đưa vào báo cáo.

## 17. Lệnh Tái Tạo Kết Quả

```powershell
py -B scripts/generate_evaluation_reports.py
py experiments/run_ablation.py --config nezha_setup/config/experiment_phase3_smoke.yaml
py experiments/run_phase4_benchmark.py --config nezha_setup/config/experiment_phase4_benchmark.yaml
py experiments/run_hybrid.py --config nezha_setup/config/experiment_phase5_context_rescue.yaml
py experiments/run_hybrid.py --config nezha_setup/config/experiment_local_first_ollama_smoke.yaml
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_local_first_scheduler_openrouter_smoke.yaml --max-positives 1 --max-negatives 0 --seed 5 --output-mode local_first_scheduler_openrouter_one_window_v2 --cache-path nezha_setup/outputs/llm_response_cache_openrouter_stable.jsonl
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_local_only_qwen25_3b_one_window.yaml --max-positives 1 --max-negatives 0 --seed 5 --output-mode local_only_qwen25_3b_one_window_v2
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_local_only_llama32_3b_one_window.yaml --max-positives 1 --max-negatives 0 --seed 5 --output-mode local_only_llama32_3b_one_window_v2
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_local_model_cascade_llama_qwen.yaml --max-positives 1 --max-negatives 1 --seed 11 --output-mode local_model_cascade_1p1n_v3
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_local_llama_gemini_lite_scheduler.yaml --max-positives 1 --max-negatives 1 --seed 11 --output-mode local_llama_gemini_lite_1p1n_v3 --cache-path nezha_setup/outputs/llm_response_cache_gemini_lite_scheduler_v2.jsonl
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_real_llm_stratified.yaml --max-positives 3 --max-negatives 3 --seed 11 --output-mode gemini25_flash_lite_paid_3p3n --cache-path nezha_setup/outputs/llm_response_cache_gemini25_flash_lite_paid_3p3n.jsonl
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_local_llama_gemini_lite_scheduler_3p3n.yaml --max-positives 3 --max-negatives 3 --seed 11 --output-mode local_llama_gemini_lite_3p3n_paid_key --cache-path nezha_setup/outputs/llm_response_cache_local_llama_gemini_lite_3p3n_paid_key.jsonl
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_real_llm_stratified.yaml --max-positives 100 --max-negatives 400 --seed 21 --output-mode gemini25_flash_lite_500w_paid_key --cache-path nezha_setup/outputs/llm_response_cache_gemini25_flash_lite_500w_paid_key.jsonl
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_real_llm_stratified_cache_replay.yaml --max-positives 100 --max-negatives 400 --seed 21 --output-mode gemini25_flash_lite_500w_budget_manual_review_cache_replay --cache-path nezha_setup/outputs/llm_response_cache_gemini25_flash_lite_500w_paid_key.jsonl
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_real_llm_gemini3_flash_preview_1p1n.yaml --max-positives 1 --max-negatives 1 --seed 21 --output-mode gemini3_flash_preview_1p1n_smoke --cache-path nezha_setup/outputs/llm_response_cache_gemini3_flash_preview_1p1n_smoke.jsonl
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_real_llm_gemma4_26b_1p1n.yaml --max-positives 1 --max-negatives 1 --seed 21 --output-mode gemma4_26b_1p1n_smoke --cache-path nezha_setup/outputs/llm_response_cache_gemma4_26b_1p1n_smoke.jsonl
```

Với Gemini/API fallback, cần có `GEMINI_API_KEY` trong `.env`; với local-first, cần Ollama đang chạy và đã pull model:

```powershell
ollama pull qwen2.5:1.5b
```

## 18. Submission Spec (Nezha-only)

| Item | Value |
|---|---|
| Dataset | Nezha only |
| Window split | 300 hoặc 500 windows, stratified |
| Baseline inherited | `detector_only`, `llm_without_rag`, `hybrid_bm25_top6`, `hybrid_bm25_top10`, `context_rescue` |
| Proposed | `topology_aware_fusion` |
| LLM model | `gemini-2.5-flash-lite` hoặc cache replay |
| Budget policy | `decision.llm_budget_exhausted_action = manual_review` |
| Decision guard | `require_evidence_for_true_alert = true` |

Phase boundary for execution artifacts:

```text
outputs/phase1/legacy_output_index.json
outputs/phase2/audit_manifest.json
outputs/phase2/window_index.csv
outputs/phase2/baseline_reference.csv
outputs/phase2/input_freeze.json
outputs/phase2/service_graph_edges.csv
outputs/phase2/service_graph_summary.json
outputs/phase2/service_graph_directed.json
outputs/phase2/service_graph_undirected.json
outputs/phase2/retrieval/candidate_pool_debug.jsonl
outputs/phase2/retrieval/topk_contexts_debug.jsonl
outputs/phase2/retrieval/phase2_retrieval_summary.csv
outputs/phase2/retrieval/phase2_retrieval_by_fault_type.csv
outputs/phase2/retrieval/phase2_retrieval_by_service.csv
outputs/phase2/retrieval/phase2_retrieval_network_delay_breakdown.csv
outputs/phase2/retrieval/topk_contexts.jsonl
outputs/phase2/ablation/alpha_beta_gamma_ablation.csv
outputs/phase2/ablation/ablation_by_fault_type.csv
outputs/phase2/ablation/ablation_network_delay_breakdown.csv
outputs/phase2/ablation/ablation_summary.md
outputs/phase2/ablation/ablation_selected_settings.json
outputs/phase2/topology_fusion/audit/topology_fusion_300w_audit.jsonl
outputs/phase2/topology_fusion/audit/topology_fusion_500w_audit.jsonl
outputs/phase2/topology_fusion/results/topology_fusion_300w_summary.csv
outputs/phase2/topology_fusion/results/topology_fusion_500w_summary.csv
```

Bootstrap command for Phase 2 foundation:

```powershell
py scripts\phase2\build_phase2_manifest.py
py scripts\phase2\freeze_phase2_inputs.py
py scripts\phase2\build_service_graph.py
py scripts\phase2\run_topology_retrieval_debug.py
py scripts\phase2\run_retrieval_only_eval.py --splits debug_50 paper_300 paper_500
py scripts\phase2\run_alpha_beta_gamma_ablation.py
py experiments\run_phase2_topology_fusion.py --config nezha_setup\config\experiment_phase2_topology_fusion_300w.yaml --output-mode topology_fusion_300w
py experiments\run_phase2_topology_fusion.py --config nezha_setup\config\experiment_phase2_topology_fusion_500w.yaml --output-mode topology_fusion_500w
```

### 18.1. Phase 2 Current Execution Status

Tính đến bản cập nhật sau Step 9, Phase 2 đã hoàn tất phần khóa input, dựng service topology graph, implement topology-aware retrieval core, chạy Level A retrieval-only evaluation, chạy Level C α/β/γ ablation, tích hợp `topology_aware_fusion` vào hybrid pipeline/audit schema, hoàn tất Step 7 View A/View B, sinh Step 8 paper outputs, và pass Step 9 quality gate. Dataset audit không chạy lại; các bước này chỉ dùng lại Nezha raw/processed data và audit/baseline artifacts đã có.

| Hạng mục | Trạng thái | Artifact |
|---|---|---|
| Freeze window/baseline input | Hoàn tất; `debug_50`, `paper_300`, `paper_500` đều không trùng window và baseline khớp split tương ứng | `outputs/phase2/input_freeze.json`, `outputs/phase2/input_freeze.md` |
| Service topology graph | Hoàn tất graph từ raw Nezha traces: 56 services, 68 directed edges, 68 undirected edges, 307 trace files, 4,180,244 trace rows | `outputs/phase2/service_graph_summary.json`, `outputs/phase2/service_graph_edges.csv` |
| Directed/undirected graph exports | Hoàn tất để phục vụ `GraphSim(sc, s0)` và graph-expanded retrieval ở bước sau | `outputs/phase2/service_graph_directed.json`, `outputs/phase2/service_graph_undirected.json` |
| Topology-aware retrieval core | Hoàn tất candidate expansion, duplicate removal, BM25_norm, TimeSim, GraphSim, Score_final và deterministic top-k ranking trên `debug_50` | `src/phase2/retrieval/topology_candidate_expander.py`, `src/phase2/retrieval/fusion_ranker.py`, `src/phase2/retrieval/topology_aware_retriever.py` |
| Step 3 debug outputs | Hoàn tất debug run: 50 alerts, 300 retrieved contexts, mỗi context có `bm25_raw`, `bm25_norm`, `time_sim`, `graph_distance`, `graph_sim`, `score_final`, `rank` | `outputs/phase2/retrieval/candidate_pool_debug.jsonl`, `outputs/phase2/retrieval/topk_contexts_debug.jsonl` |
| Level A retrieval-only evaluation | Hoàn tất M0/M1/M2/M3 trên `debug_50`, `paper_300`, `paper_500`; không gọi LLM/API | `outputs/phase2/retrieval/phase2_retrieval_summary.csv`, `outputs/phase2/retrieval/topk_contexts.jsonl` |
| Level C α/β/γ ablation | Hoàn tất A0-A4 trên `paper_300`, chọn `A2_bm25_graph` và `A4_topology_heavy` từ tuning split, confirm trên `paper_500`; không gọi LLM/API | `outputs/phase2/ablation/alpha_beta_gamma_ablation.csv`, `outputs/phase2/ablation/ablation_summary.md` |
| Hybrid pipeline integration | Hoàn tất backend `topology_aware_fusion`, config 300w/500w, audit schema topology fields, và mock integration run | `nezha_setup/config/experiment_phase2_topology_fusion_300w.yaml`, `outputs/phase2/topology_fusion/audit/topology_fusion_300w_audit.jsonl` |
| Step 7 View A real/cache LLM evaluation | Hoàn tất retrieval-fair comparison trên frozen `paper_500` với operational/full-budget regimes và paired statistics | `scripts/phase2/run_step7_view_a.py`, `outputs/phase2/step7_rerun/step7_rerun_assessment.md` |
| Step 7 View B architecture evaluation | Hoàn tất detector-only, LLM without RAG, BM25 top-6, topology top-6 và Context Rescue trên cùng frozen `paper_500`, budget 120 | `scripts/phase2/run_step7_view_b.py`, `outputs/phase2/step7_view_b/step7_view_b_report.md` |
| Step 8 paper outputs | Hoàn tất 4 bảng và 5 hình, tách View A/View B và retrieval-only ablation | `scripts/phase2/generate_paper_outputs.py`, `outputs/phase2/paper_tables/`, `outputs/phase2/figures/` |
| Step 9 quality gate | Pass toàn bộ 14 checks và 5 hard-stop conditions; paper result table được phép finalize | `scripts/phase2/run_step9_quality_gate.py`, `outputs/phase2/quality_gate/step9_quality_gate_report.md` |
| Source organization | Hoàn tất boundary Phase 2: code mới nằm dưới `src/phase2/`, script orchestration nằm dưới `scripts/phase2/` | `src/phase2/retrieval/graph_builder.py`, `scripts/phase2/build_service_graph.py` |

Phần thực nghiệm Phase 2 qua Step 9 đã hoàn tất. Phần còn pending là Step 10 submission/thesis package, repeated independent LLM runs, và external validation trên dataset/workload thứ hai.

### 18.2. Level A Retrieval-only Results

Level A so sánh 4 method trên cùng frozen split và cùng `top_k=6`:

| Method | Ý nghĩa | α | β | γ | Graph expansion |
|---|---|---:|---:|---:|---:|
| `M0_bm25_only` | BM25-only | 1.0 | 0.0 | 0.0 | 0/service |
| `M1_bm25_time` | BM25 + TimeSim | 0.5 | 0.5 | 0.0 | 0/service |
| `M2_bm25_graph` | BM25 + GraphSim | 0.5 | 0.0 | 0.5 | 20/service |
| `M3_full_fusion` | BM25 + TimeSim + GraphSim | 0.4 | 0.3 | 0.3 | 20/service |

Kết quả chính:

| Split | Method | Windows | Context coverage | Service context coverage | Avg latency ms | P95 latency ms | Avg graph candidates | Topology context ratio |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `paper_300` | `M0_bm25_only` | 300 | 1.0000 | 1.0000 | 35.7981 | 53.8814 | 0.0000 | 0.0000 |
| `paper_300` | `M1_bm25_time` | 300 | 1.0000 | 1.0000 | 35.0469 | 50.0783 | 0.0000 | 0.0000 |
| `paper_300` | `M2_bm25_graph` | 300 | 1.0000 | 1.0000 | 36.9464 | 51.6285 | 17.7533 | 0.0744 |
| `paper_300` | `M3_full_fusion` | 300 | 1.0000 | 1.0000 | 35.2373 | 46.4673 | 17.7533 | 0.0744 |
| `paper_500` | `M0_bm25_only` | 500 | 1.0000 | 0.4800 | 34.0843 | 43.9075 | 0.0000 | 0.0000 |
| `paper_500` | `M1_bm25_time` | 500 | 1.0000 | 0.4800 | 36.1369 | 55.9718 | 0.0000 | 0.0000 |
| `paper_500` | `M2_bm25_graph` | 500 | 1.0000 | 0.4800 | 37.9791 | 53.5549 | 6.5220 | 0.1757 |
| `paper_500` | `M3_full_fusion` | 500 | 1.0000 | 0.4800 | 38.1668 | 55.0253 | 6.5220 | 0.1947 |

Network-delay breakdown:

| Split | Method | Network-delay windows | Network-delay context coverage | Network-delay service context coverage | Topology context ratio |
|---|---|---:|---:|---:|---:|
| `paper_300` | `M0_bm25_only` | 8 | 1.0000 | 1.0000 | 0.0000 |
| `paper_300` | `M3_full_fusion` | 8 | 1.0000 | 1.0000 | 1.0000 |
| `paper_500` | `M0_bm25_only` | 40 | 1.0000 | 1.0000 | 0.0000 |
| `paper_500` | `M3_full_fusion` | 40 | 1.0000 | 1.0000 | 1.0000 |

Diễn giải an toàn:

- Retrieval-only không đo chất lượng quyết định của LLM; nó chỉ đo chất lượng/trạng thái evidence được đưa vào prompt.
- M2/M3 đã chứng minh graph expansion hoạt động: `avg_graph_candidate_count` > 0 và `topology_context_ratio` tăng rõ, đặc biệt `paper_500` từ 0.0000 lên 0.1947 với M3.
- Proxy `service_context_coverage` chưa cải thiện so với BM25 trên frozen splits. Vì vậy chưa nên claim topology-aware fusion cải thiện diagnosis; claim này chỉ được xét sau Step 7 LLM decision evaluation.
- Với `network_delay`, M3 đưa toàn bộ top-k context qua graph-expanded evidence trong các split chính (`topology_context_ratio=1.0000`) trong khi vẫn giữ coverage 1.0000.

### 18.3. Level C Alpha/Beta/Gamma Ablation

Level C chạy ablation retrieval-only cho 5 cấu hình trọng số:

| Setting | Ý nghĩa | α | β | γ |
|---|---|---:|---:|---:|
| `A0_bm25_only` | BM25 only | 1.00 | 0.00 | 0.00 |
| `A1_bm25_time` | BM25 + Time | 0.50 | 0.50 | 0.00 |
| `A2_bm25_graph` | BM25 + Graph | 0.50 | 0.00 | 0.50 |
| `A3_balanced` | Balanced | 0.40 | 0.30 | 0.30 |
| `A4_topology_heavy` | Topology-heavy | 0.35 | 0.25 | 0.40 |

Execution rule: tune trên `paper_300`, sau đó chỉ confirm setting được chọn trên `paper_500`. `paper_500` không dùng để chọn trọng số.

| Phase | Split | Setting | Windows | Service coverage | Network-delay service coverage | Topology ratio | Avg latency ms |
|---|---|---|---:|---:|---:|---:|---:|
| tuning | `paper_300` | `A0_bm25_only` | 300 | 1.0000 | 1.0000 | 0.0000 | 35.4288 |
| tuning | `paper_300` | `A1_bm25_time` | 300 | 1.0000 | 1.0000 | 0.0000 | 40.4577 |
| tuning | `paper_300` | `A2_bm25_graph` | 300 | 1.0000 | 1.0000 | 0.0744 | 36.7357 |
| tuning | `paper_300` | `A3_balanced` | 300 | 1.0000 | 1.0000 | 0.0744 | 35.5888 |
| tuning | `paper_300` | `A4_topology_heavy` | 300 | 1.0000 | 1.0000 | 0.0744 | 35.0295 |
| confirmation | `paper_500` | `A2_bm25_graph` | 500 | 1.0000 | 1.0000 | 0.1757 | 35.4393 |
| confirmation | `paper_500` | `A4_topology_heavy` | 500 | 1.0000 | 1.0000 | 0.1947 | 37.7365 |

Selected confirmation settings:

```text
A2_bm25_graph
A4_topology_heavy
```

Diễn giải an toàn:

- A0/A1 là baseline không graph; topology ratio bằng 0.0000 là đúng kỳ vọng.
- A2/A3/A4 giữ coverage trên `paper_300` và thêm graph-expanded evidence (`topology_ratio=0.0744`).
- A4 có latency tốt nhất trong nhóm graph-enabled trên tuning split (`35.0295 ms`) và topology ratio cao hơn A2 khi confirm trên `paper_500` (`0.1947` so với `0.1757`), nhưng đây vẫn là retrieval-only signal.
- Chưa claim F1/recall/diagnosis improvement ở Step 5 vì chưa gắn vào LLM decision pipeline.

### 18.4. Step 6 Hybrid Pipeline Integration

Step 6 đã gắn `topology_aware_fusion` vào hybrid monitoring flow hiện tại. Backend mới được chọn bằng config:

```yaml
retrieval:
  backend: topology_aware_fusion
  lexical_backend: hybrid_bm25
  graph_path: outputs\phase2\service_graph_undirected.json
  top_k: 6
  bm25_k: 60
  graph_max_distance: 2
  graph_per_service_limit: 20
  alpha: 0.35
  beta: 0.25
  gamma: 0.40
```

Decision policy trong config Phase 2 dùng guard an toàn:

```yaml
decision:
  require_evidence_for_true_alert: true
  llm_budget_exhausted_action: manual_review
```

Audit JSONL đã được mở rộng với các field topology-aware:

```text
candidate_pool_size
bm25_candidate_count
graph_candidate_count
duplicates_removed
bm25_norm
time_sim
graph_distance
graph_sim
score_final
retrieved_context_score_components
context_coverage
actual_api_calls
cache_hits
final_decision
json_valid
```

Integration run dùng mock LLM, không phát sinh external API call:

| Run | Windows | Candidates | Precision | Recall | F1 | FPR | LLM calls | Context coverage | Avg context | Retrieval ms | Actual API calls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `topology_fusion_300w` | 300 | 40 | 0.1500 | 0.3750 | 0.2143 | 0.1197 | 40 | 1.0000 | 0.8000 | 10.2753 | 0 |
| `topology_fusion_500w` | 500 | 46 | 0.1304 | 0.3750 | 0.1935 | 0.0826 | 46 | 1.0000 | 0.5520 | 6.1906 | 0 |

Schema validation:

| Audit file | Rows | Backend rows | Rows with topology score components | Missing required fields |
|---|---:|---:|---:|---:|
| `topology_fusion_300w_audit.jsonl` | 300 | 300 | 40 | 0 |
| `topology_fusion_500w_audit.jsonl` | 500 | 500 | 46 | 0 |

Diễn giải an toàn:

- Step 6 xác nhận backend mới tích hợp được vào pipeline hybrid và audit schema đủ field để phục vụ Step 7.
- Kết quả ở bảng trên là mock-LLM integration/smoke, chưa phải real/cache LLM decision evaluation chính thức.
- `actual_api_calls=0` và `cache_hits=0` đúng kỳ vọng vì provider đang là `mock`.
- `retrieval_backend` trong audit đã ghi `topology_aware_fusion` cho toàn bộ rows; các candidate có context có `retrieved_context_score_components`.

#### 18.4.1. Đánh giá F1 thấp ở Step 6

F1 hiện tại của Step 6 thấp: `0.2143` trên 300w và `0.1935` trên 500w. Nếu trình bày các số này như kết quả chính thì sẽ làm yếu claim của Phase 2. Tuy nhiên, trong phạm vi Step 6, đây là integration/smoke result chứ chưa phải Step 7 decision evaluation chính thức.

Các nguyên nhân chính:

1. Step 6 hiện chạy theo `max_windows`, tức lấy tuần tự các window đầu tiên, chưa dùng frozen split `paper_300`/`paper_500` từ `outputs/phase2/window_index.csv`.
2. Do lấy tuần tự, cả hai run 300w/500w đều bị service-biased: toàn bộ rows là `cartservice`.
3. `network_delay` có mặt trong tập window nhưng không có candidate alert (`candidate_alerts=0`), nên recall cho fault type khó này bằng 0 trước khi retrieval hoặc LLM có cơ hội can thiệp.
4. Mock judge trong Step 6 route toàn bộ candidate (`manual_review=0`, `suppress=0`), nên F1 gần như phản ánh chất lượng detector candidate hơn là chất lượng topology-aware retrieval.
5. Vì vậy không nên dùng Step 6 để kết luận topology-aware fusion tốt/xấu về diagnosis F1.

Ảnh hưởng đến chất lượng thí nghiệm:

- Không ảnh hưởng đến kết luận Step 6: backend đã tích hợp được, audit schema đủ field, config hoạt động, không crash khi chạy 300/500.
- Có ảnh hưởng nếu dùng số F1 Step 6 làm result chính: split không công bằng và mock judge chưa đại diện cho final LLM decision.
- Bắt buộc Step 7 phải chạy trên frozen split và so sánh BM25/topology trong cùng điều kiện.

Phương hướng cải thiện trước và trong Step 7:

| Vấn đề | Cải thiện cần làm |
|---|---|
| Sequential `max_windows` gây service bias | Thêm runner chọn chính xác frozen `paper_300`/`paper_500` từ `outputs/phase2/window_index.csv` rồi truyền `window_indices` vào `run_pipeline` |
| F1 đang phản ánh detector/mock hơn retrieval | Chạy retrieval-fair comparison: BM25 top-6 vs topology-aware top-6, cùng windows, cùng top-k, cùng budget |
| Mock judge route toàn bộ candidate | Step 7 dùng real/cache LLM nếu có thể; nếu không, mock result phải gắn nhãn mock-only |
| `network_delay` candidate thấp | Báo riêng detector-missed `network_delay`; không quy lỗi cho retrieval khi detector không tạo candidate |
| Claim dễ quá mức | Chỉ claim diagnosis improvement sau khi Step 7 có kết quả fair split và LLM/cache decision |

Test/quality gate cần thêm cho Step 7:

```text
[ ] Frozen split runner chọn đúng số window và đúng window_id hash
[ ] Audit rows khớp frozen split, không còn service-biased do sequential slicing
[ ] BM25 top-6 và topology-aware top-6 dùng cùng top_k, same LLM budget, same decision policy
[ ] Audit candidate rows có đầy đủ topology score components
[ ] Cache/API metrics tách riêng: llm_calls, actual_api_calls, cache_hits
```

#### 18.4.2. Step 7 View A - Frozen real/cache LLM decision evaluation

Step 7 View A đã được chạy bằng runner `scripts/phase2/run_step7_view_a.py`. Runner này:

1. đọc frozen split từ `outputs/phase2/window_index.csv`;
2. map `window_id` sang `run_pipeline(..., window_indices=...)`;
3. verify row count và `window_id_sha256` với `outputs/phase2/input_freeze.json`;
4. chạy cùng một LLM provider/model/policy cho `hybrid_bm25_top6` và `topology_aware_fusion_top6`;
5. tách riêng `llm_calls`, `actual_api_calls`, `cache_hits`.

Artifact chính:

```text
outputs/phase2/step7_view_a/step7_view_a_report.md
outputs/phase2/step7_view_a/step7_view_a_report.csv
outputs/phase2/step7_view_a/step7_view_a_report.json
outputs/phase2/step7_view_a/results/
outputs/phase2/step7_view_a/audit/
```

Kết quả authoritative của View A là fresh-cache rerun trên `paper_500`. Hai operating regime được giữ tách biệt:

| Regime | Method | Precision | Recall | F1 | FPR | Context coverage | API calls | Estimated cost USD |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `operational_budget_120` | `hybrid_bm25_top6` | 1.0000 | 0.3400 | 0.5075 | 0.0000 | 0.1125 | 120 | 0.0214684 |
| `operational_budget_120` | `topology_aware_fusion_top6` | 0.5823 | 0.4600 | 0.5140 | 0.0825 | 0.2454 | 120 | 0.0401765 |
| `quality_full_budget` | `hybrid_bm25_top6` | 0.8923 | 0.5800 | 0.7030 | 0.0175 | 0.2249 | 489 | 0.0627953 |
| `quality_full_budget` | `topology_aware_fusion_top6` | 0.3507 | 0.7400 | 0.4759 | 0.3425 | 1.0000 | 489 | 0.1669426 |

Diễn giải an toàn sau Step 7 View A:

- Ở budget 120, topology tăng recall `+0.1200`, nhưng delta F1 chỉ `+0.0065` với bootstrap 95% CI `[-0.0981, 0.1134]`.
- Ở full budget, topology tăng recall `+0.1600` nhưng giảm F1 `-0.2271`, tăng FPR `+0.3250`, và tăng estimated cost từ `0.0628` lên `0.1669` USD.
- `network_delay` là kết quả fault-specific mạnh nhất: recall tăng từ `0.3750` lên `0.7000`.
- Fresh isolated cache cho từng method xác nhận toàn bộ recorded calls là first-pass API calls; cache hits bằng `0`.
- Claim an toàn là topology cải thiện evidence availability và recall, đặc biệt cho `network_delay`, nhưng policy hiện tại over-route normal windows và làm xấu precision/FPR/cost.

#### 18.4.3. Step 8 plan

Step 8 đã được thực hiện theo hướng "paper-ready nhưng claim-safe", lấy `paper_500` làm split chính:

1. **Main result table**: dùng `paper_500` làm bảng chính cho View A với hai method trong từng operating regime; architecture reference được tách block và gắn nhãn, không trộn với retrieval-fair comparison.
2. **Fault-type breakdown**: xuất breakdown theo `fault_type`, đặc biệt tách riêng `network_delay` và ghi chú khi detector không tạo candidate để tránh quy lỗi sai cho retrieval.
3. **Cost/latency table**: báo riêng `llm_calls`, `actual_api_calls`, `cache_hits`, `json_valid_rate`, `avg_llm_latency_ms`, và `estimated_llm_cost_usd` từ fresh-cache first-pass rerun.
4. **Figures ưu tiên**: `f1_comparison` và `context_coverage_comparison` dùng `paper_500` làm hình chính; `network_delay_recall` là hình phân tích lỗi; `alpha_beta_gamma_ablation` dùng lại artifact Step 5.
5. **Claim boundary trong paper**: không viết "topology-aware improves final diagnosis" như một kết luận mạnh. Framing nên là trade-off finding: recall/context tăng trên split đa service nhưng precision/FPR/cost xấu hơn BM25.
6. **Trạng thái**: generator `scripts/phase2/generate_paper_outputs.py` đã sinh đủ các artifact, không trộn smoke/debug output:

```text
outputs/phase2/paper_tables/main_result_table.csv
outputs/phase2/paper_tables/fault_type_breakdown.csv
outputs/phase2/paper_tables/ablation_table.csv
outputs/phase2/paper_tables/cost_latency_table.csv
outputs/phase2/figures/f1_comparison.png
outputs/phase2/figures/context_coverage_comparison.png
outputs/phase2/figures/network_delay_recall.png
outputs/phase2/figures/alpha_beta_gamma_ablation.png
outputs/phase2/figures/service_graph_example.png
```

#### 18.4.4. Step 7 strengths, limitations, and paper implications

**Strengths**

- View A preserves the main fairness controls: frozen window set, identical `top_k=6`, identical Gemini model, identical decision policy, and identical LLM budget.
- The runner verifies row count and `window_id_sha256`, while each method has separate config, result, and audit artifacts. This gives the experiment strong traceability and reproducibility.
- On the main multi-service split `paper_500`, topology-aware fusion improves recall from `0.5800` to `0.7400` at full budget; the strongest fault-level improvement is `network_delay` recall from `0.3750` to `0.7000`.
- The result exposes a meaningful systems trade-off rather than only reporting a favorable aggregate score: topology-aware retrieval finds more true alerts, but also introduces more false positives and higher token cost.
- JSON validity is `1.0000` for both methods, so schema failure is not driving the observed difference.

**Limitations**

- At full budget, topology F1 decreases from `0.7030` to `0.4759`, precision decreases from `0.8923` to `0.3507`, and FPR increases from `0.0175` to `0.3425`.
- At budget 120, manual-review censoring remains substantial; therefore operational-budget and full-budget results must not be merged.
- Context coverage must be reported together with its denominator. The paper tables distinguish candidate coverage from retrieval-attempt coverage where applicable.
- The fresh-cache rerun removes replay-state ambiguity, but repeated independent LLM runs are still absent.
- `paper_300` contains only one service and is unsuitable as the main validation split for a topology-aware hypothesis.
- Repeated-run stochastic uncertainty and a second dataset are not yet complete. View B, paired bootstrap intervals, exact McNemar tests, and the Step 9 quality gate are complete.

**Paper-safe interpretation**

The strongest defensible finding is that topology-aware evidence selection changes the operating point: it improves recall, especially for `network_delay`, but increases false positives and cost. The current result should be framed as a measured trade-off and fault-specific benefit, not as proof that topology-aware fusion generally improves final diagnosis.

This study does not claim full root cause analysis because root-cause service labels are not available. It also makes no generalization beyond Nezha without evaluation on another dataset or workload.

#### 18.4.5. Step 8 execution status and remaining gates

Step 8 tables and figures are complete. The following list distinguishes completed work from remaining final-paper gates.

1. **Completed - freeze two evaluation regimes.**
   - `quality_full_budget`: set the LLM budget high enough to process the same complete candidate set for both View A methods.
   - `operational_budget_120`: retain the realistic 120-call limit and treat `manual_review` as abstention, not as an ordinary negative prediction.
2. **Completed - rerun `paper_500` View A with Gemini and fresh cache paths.**
3. **Completed - report three metric layers.**
   - End-to-end policy metrics over all windows.
   - Selective/auto-decision metrics with automation coverage and manual-review rate.
   - LLM-conditional metrics over the identical candidate subset actually judged by Gemini.
4. **Completed - correct retrieval reporting.**
5. **Partially completed - quantify uncertainty.** Paired bootstrap and exact McNemar are complete; repeated fresh-cache runs remain optional future work.
6. **Completed - View B architecture-level comparison.** The generated tables keep View B separate from retrieval-fair View A and label Context Rescue as architecture-enhanced.
7. **Completed - generate claim-safe paper tables.**
   - Main table: `paper_500`, View A, both budget regimes clearly labeled.
   - Fault table: include TP/FP/FN and emphasize `network_delay` without hiding degradation on normal windows.
   - Cost table: separate logical LLM calls, actual API calls, cache hits, JSON validity, first-pass latency, and estimated cost.
   - Ablation table: reuse held-out Step 5 results and state that weight selection used `paper_300`.
8. **Completed for Step 8 scope - generate the five required figures with scope labels.**
9. **Completed - run the final Step 9 quality gate.** All 14 checks and all 5 hard-stop conditions pass.

#### 18.4.6. Current paper readiness and acceptance assessment

An exact acceptance probability cannot be estimated without a target venue, reviewer pool, and completed manuscript. A readiness assessment is more defensible:

| Dimension | Current readiness | Assessment |
|---|---:|---|
| Problem relevance | 4/5 | Microservice observability, RAG, and cost-aware LLM diagnosis are relevant topics. |
| Method novelty | 3/5 | Topology-aware fusion is plausible and useful, but must be differentiated clearly from graph-aware retrieval prior work. |
| Reproducibility | 4/5 | Frozen splits, hashes, configs, audit logs, and cache accounting are strong. |
| Experimental rigor | 3/5 | Fresh-cache regimes, paired confidence intervals, McNemar, View B and the quality gate improve rigor; repeated runs and a second dataset remain absent. |
| Evidence strength | 3/5 | The fault-specific recall gain is clear, while the aggregate F1/FPR/cost degradation limits the main claim. |
| Claim safety | 4/5 | Final tables separate scopes and operating regimes and explicitly preserve the negative aggregate result. |
| Overall | 3/5 | Defensible thesis result and workshop-oriented study, but not yet a strong full-paper package. |

Current venue-level outlook:

- **Thesis/internship defense:** reasonably strong if limitations and trade-offs are stated explicitly.
- **Student workshop, poster, demo, or applied workshop:** the experimental package is now reasonably ready if the negative/trade-off result is stated explicitly.
- **Regular peer-reviewed international full paper:** readiness remains moderate-to-low; it needs repeated-run uncertainty and preferably validation on another dataset or workload.
- **Top-tier systems/AI venue:** not ready in the current form because the empirical gain is small, the main result is budget-confounded, and external validity is limited to Nezha.

The shortest credible path to paper standard is:

```text
Completed: budget/manual-review evaluation
→ completed: fresh-cache View A regimes and paired statistics
→ completed: View B architecture comparison
→ completed: Step 8 tables/figures
→ completed: Step 9 quality gate
→ remaining: repeated LLM runs and external validation
→ final framing: recall/FPR/cost trade-off with a network-delay case study
```

If another dataset cannot be added, the paper must narrow its scope to a Nezha case study and make no generalization claim beyond the evaluated microservice workload.

#### 18.4.7. Step 7 View A rerun result

The planned Step 7 rerun was completed on `paper_500` using `gemini-2.5-flash-lite`, fresh isolated caches, and two budget regimes. Both methods used the same 500 frozen windows and the same hash `1745d09ec60c98b8520a6e38ed614f20e39009c3ac7173468f18658066a7cd9e`.

| Regime | Method | Precision | Recall | F1 | FPR | Manual review | Retrieval-attempt coverage | API calls | Cost USD |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Budget 120 | BM25 top-6 | 1.0000 | 0.3400 | 0.5075 | 0.0000 | 0.8860 | 0.4583 | 120 | 0.0214684 |
| Budget 120 | Topology fusion top-6 | 0.5823 | 0.4600 | 0.5140 | 0.0825 | 0.7680 | 1.0000 | 120 | 0.0401765 |
| Full budget | BM25 top-6 | 0.8923 | 0.5800 | 0.7030 | 0.0175 | 0.7820 | 0.2249 | 489 | 0.0627953 |
| Full budget | Topology fusion top-6 | 0.3507 | 0.7400 | 0.4759 | 0.3425 | 0.2200 | 1.0000 | 489 | 0.1669426 |

Paired bootstrap with 10,000 samples shows:

- Budget 120 recall delta is `+0.1200`, 95% CI `[0.0202, 0.2222]`, while F1 delta is `+0.0065`, 95% CI `[-0.0981, 0.1134]`.
- Full-budget recall delta is `+0.1600`, 95% CI `[0.0460, 0.2737]`.
- Full-budget F1 delta is `-0.2271`, 95% CI `[-0.3210, -0.1320]`.
- Full-budget FPR delta is `+0.3250`, 95% CI `[0.2771, 0.3734]`.
- Exact McNemar testing on full-budget paired correctness gives `p=2.61e-19` and favors BM25 overall.

The positive fault-specific result is `network_delay`: recall improves from `0.3750` to `0.7000`. However, topology fusion routes 137 false alerts on normal windows, compared with 7 for BM25.

The full-budget manual-review breakdown explains the mechanism. BM25 has 391 manual reviews, including 369 `llm_valid_missing_evidence` cases. Topology fusion reduces manual review to 110 because it returns context for all 489 retrieval attempts, but the current policy converts too much of that context into routed alerts. Topology therefore improves evidence availability and recall while over-alerting normal windows.

The paper claim must be revised accordingly:

> Topology-aware retrieval improves evidence availability and fault recall, especially for network delay, but requires calibration because the current fusion and decision policy increase false positives, cost, and aggregate error.

Primary artifacts:

```text
outputs/phase2/step7_rerun/operational_budget_120/
outputs/phase2/step7_rerun/quality_full_budget/
outputs/phase2/step7_rerun/step7_rerun_analysis.json
outputs/phase2/step7_rerun/step7_rerun_analysis.csv
outputs/phase2/step7_rerun/step7_rerun_analysis.md
outputs/phase2/step7_rerun/step7_rerun_assessment.md
```

Step 7 View A rerun and View B are complete and remain separated in the paper tables.

#### 18.4.8. Step 7 View B architecture-level result

View B was completed on the same frozen `paper_500` hash with the operational 120-call budget:

| Method | Precision | Recall | F1 | FPR | Manual review | Context coverage | API calls | Cache hits |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Detector-only | 0.2004 | 0.9800 | 0.3328 | 0.9775 | 0.0000 | 0.0000 | 0 | 0 |
| LLM without RAG | 0.5210 | 0.6200 | 0.5662 | 0.1425 | 0.7400 | 0.0000 | 120 | 0 |
| BM25 RAG top-6 | 1.0000 | 0.3400 | 0.5075 | 0.0000 | 0.8860 | 0.1125 | 120 | 0 |
| Topology-Aware Fusion top-6 | 0.5823 | 0.4600 | 0.5140 | 0.0825 | 0.7680 | 0.2454 | 120 | 0 |
| Context Rescue [architecture-enhanced] | 1.0000 | 0.3400 | 0.5075 | 0.0000 | 0.8860 | 0.1125 | 0 | 120 |

`LLM without RAG` has the highest View B F1, while topology provides higher context coverage and recall than BM25 but does not exceed the no-RAG baseline. Context Rescue checks 11 detector-negative windows but promotes none, so its decisions match BM25 in this split. Its 120 logical calls are cache hits seeded from the BM25 View A cache and must not be interpreted as zero first-pass inference cost.

#### 18.4.9. Step 9 quality gate result

The automated Step 9 gate passes all 14 checks. All five hard-stop conditions pass: baseline reproducibility, frozen-window consistency, audit schema validation, `score_final` bounds, and cache/API separation. The final paper result table is therefore traceable and finalizable under the current Nezha-only claim boundary.
