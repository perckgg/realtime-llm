# Dataset Analysis Report

Generated at: `2026-05-18T09:59:15.393005+00:00`
Machine-readable summary: `outputs/dataset_analysis/dataset_analysis_summary.json`

## 1. Scope

Report này phân tích 2 dataset đang dùng trong thí nghiệm hybrid monitoring:

- Microsoft `cloud-monitoring-dataset`: time-series metric có nhãn anomaly.
- `IntelligentDDS/Nezha`: metric, log, trace, traceid và danh sách fault injection.

## 2. High-level comparison

| Dataset | Raw focus | Processed rows | Positive labels/events | Vai trò tốt nhất |
| --- | --- | --- | --- | --- |
| Microsoft cloud-monitoring | 60 series CSV, 60 metadata files | 225,403 | 4,553 | Detector baseline, anomaly scoring, alert candidate generation |
| Nezha | 112 metric CSV + log/trace files | 95,660 | 11,696 | Hybrid metric + RAG + LLM judge, streaming replay, context rescue |

## 3. Microsoft cloud-monitoring-dataset

Raw path: `data\cloud-monitoring-dataset\data`

| Metric | Value |
| --- | --- |
| Series CSV | 60 |
| Metadata JSON | 60 |
| Valid points | 225,403 |
| Anomaly points | 4,553 |
| Anomaly rate | 2.02% |
| Skipped points | 42 |
| Time range | 2017-11-01T00:00:00+00:00 -> 2018-07-18T00:00:00+00:00 |
| Value min / mean / max | 0.0000 / 197660.4887 / 3081259.5500 |

Domain breakdown:

| Domain | Series | Points | Anomalies | Anomaly rate |
| --- | --- | --- | --- | --- |
| application-crash-rate-1 | 9 | 5,462 | 746 | 13.66% |
| application-crash-rate-2 | 10 | 11,141 | 574 | 5.15% |
| consumer-purchase-rate | 6 | 7,488 | 171 | 2.28% |
| data-ingress-rate | 5 | 79,200 | 1,089 | 1.38% |
| ecommerce-api-incoming-rps | 1 | 6,192 | 120 | 1.94% |
| middle-tier-api-dependency-latency | 23 | 16,560 | 553 | 3.34% |
| mongodb-application-rps | 4 | 63,360 | 1,098 | 1.73% |
| mongodb-machine-rps | 1 | 20,160 | 202 | 1.00% |
| service-unavailable | 1 | 15,840 | 0 | 0.00% |

Nhận xét:

- Dataset này mạnh ở phần time-series anomaly detection vì mỗi điểm metric đã có label.
- Context dùng cho RAG chỉ đến từ metadata notes, không phải log/trace vận hành thật.
- Vì vậy dataset này phù hợp để đo detector, threshold, false positive reduction sơ bộ; không nên là dataset chính để đánh giá khả năng giải thích RCA bằng LLM.

## 4. Nezha Dataset

Raw path: `data\Nezha`

| Metric | Value |
| --- | --- |
| RCA date partitions | 2022-08-22, 2022-08-23, 2023-01-29, 2023-01-30 |
| Construct date partitions | 2022-08-22, 2022-08-23, 2023-01-29, 2023-01-30 |
| Fault count | 101 |
| Fault time range | 2022-08-22T03:53:54+00:00 -> 2023-01-30T14:08:19+00:00 |
| Raw metric files | 112 |
| Raw metric rows | 95,660 |
| Metric rows inside fault windows | 527 |
| Metric positive rate | 0.55% |
| Services / pods | 56 / 103 |

Fault injection breakdown:

| Inject type | Faults |
| --- | --- |
| network_delay | 30 |
| cpu_contention | 23 |
| exception | 20 |
| return | 18 |
| cpu_consumed | 10 |

Processed data đang được pipeline dùng:

| Artifact | Rows | Schema |
| --- | --- | --- |
| metrics.csv | 95,660 | timestamp, node_id, service_id, cpu, memory, network, latency, workload, success_rate_drop, inject_type, label |
| logs.jsonl | 11,696 | doc_id, timestamp, node_id, service_id, pod_id, severity, event_type, source, message |

Processed label/context breakdown:

| Group | Distribution |
| --- | --- |
| Metric labels | normal=95,133, true_alert=527 |
| Inject types | none=95,133, network_delay=210, cpu_contention=161, cpu_consumed=71, exception=43, return=42 |
| Context event types | application_log=5,921, trace_span=5,775 |
| Context sources | nezha_log=5,921, nezha_trace=5,775 |
| Context severities | INFO=11,544, WARN=94, ERROR=48, WARNING=10 |

Nhận xét:

- Nezha là dataset sát kiến trúc nghiên cứu nhất vì có đủ metric, fault list, log và trace.
- Nhãn `true_alert` hiện được tạo từ fault injection theo cùng pod trong cửa sổ -60s đến +360s.
- Context RAG hiện là log/trace được lọc quanh fault window, giới hạn tối đa theo fault/source để tránh prompt quá dài.
- Tỷ lệ positive metric thấp, nên detector và gate cần được đánh giá kỹ bằng recall/FPR thay vì chỉ accuracy.

## 5. Current data flow in this repo

```text
Raw dataset
  -> prepare_cloud_monitor_data.py / prepare_nezha_data.py
  -> processed metrics.csv + logs.jsonl + summary.json
  -> src preprocessing + detector
  -> alert candidates
  -> retriever over logs/context
  -> local-first/API fallback LLM judge
  -> audit + evaluation report
```

## 6. Recommendations

- Dùng Nezha làm dataset chính cho các phase hybrid, RAG, local-first LLM judge và streaming replay.
- Dùng Microsoft cloud-monitoring để kiểm tra detector baseline, calibration threshold và stress test nhiều time series.
- Với Nezha, nên tiếp tục thêm báo cáo coverage: candidate có lấy đúng context gần fault không, và API fallback có cải thiện decision ở nhóm `uncertain` không.
- Nếu cần benchmark lớn hơn, chạy script này với `--count-raw-event-rows` để thống kê đầy đủ raw log/trace rows; mặc định report ưu tiên nhanh và tập trung vào dữ liệu processed thật sự đang dùng.

## 7. Re-run

```powershell
py experiments/analyze_datasets.py
```

Optional full raw row count:

```powershell
py experiments/analyze_datasets.py --count-raw-event-rows
```
