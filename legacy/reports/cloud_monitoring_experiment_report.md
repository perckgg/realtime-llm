# Microsoft Cloud Monitoring Dataset Experiment

This report documents when the Microsoft cloud-monitoring-dataset is used, how it was adapted to the pipeline, and what detector-only metrics were collected. This dataset is not used for RAG or external LLM/API evaluation.

## 1. Dataset Role

The Microsoft dataset is used as a metric-only anomaly detection benchmark. It contains time-series metric values and point labels, but it does not contain operational logs/traces comparable to Nezha. Therefore, it is only appropriate for validating preprocessing, windowing, and detector baseline behavior.

In the thesis, this dataset should be introduced before the Nezha hybrid RAG experiments as an initial metric-stream feasibility dataset. It should not be used for RAG/API experiments because the generated `logs.jsonl` only contains metadata context extracted from dataset metadata files, and the detector produces too many candidates for practical external API judging.

## 2. Prepared Data Summary

- Source root: `data\cloud-monitoring-dataset\data`
- Time series count: 60
- Metric points: 225403
- Anomaly points: 4553
- Skipped points: 42

| Domain | Series | Points | Anomaly points | Skipped points |
|---|---:|---:|---:|---:|
| application-crash-rate-1 | 9 | 5462 | 746 | 42 |
| application-crash-rate-2 | 10 | 11141 | 574 | 0 |
| consumer-purchase-rate | 6 | 7488 | 171 | 0 |
| data-ingress-rate | 5 | 79200 | 1089 | 0 |
| ecommerce-api-incoming-rps | 1 | 6192 | 120 | 0 |
| middle-tier-api-dependency-latency | 23 | 16560 | 553 | 0 |
| mongodb-application-rps | 4 | 63360 | 1098 | 0 |
| mongodb-machine-rps | 1 | 20160 | 202 | 0 |
| service-unavailable | 1 | 15840 | 0 | 0 |

## 3. Experiment Setup

| Item | Value |
|---|---|
| Config | `cloud_monitor_setup/config/experiment_current.yaml` |
| Processed metrics | `cloud_monitor_setup/processed/metrics.csv` |
| Metadata context | not used in reported results; `logs.jsonl` is metadata-only legacy context |
| Window size / stride | 3600s / 3600s |
| Detector | `feature_pressure`, threshold 0.85 |
| LLM provider | not used |
| Detector-only output | `cloud_monitor_setup/outputs/current_results/detector_only_results.json` |
| Detector-only audit | `cloud_monitor_setup/outputs/current_audit/detector_only_audit.jsonl` |
| Threshold sweep | `reports/cloud_monitoring_threshold_sweep.csv` |
| Domain analysis | `reports/cloud_monitoring_domain_analysis.csv` |

The feature set prepared for the detector includes raw value, robust value z-score, and absolute delta z-score. A window is labeled `true_alert` if any point inside the one-hour window is labeled anomalous.

## 4. Results

| Mode | Windows | Candidates | Routed | Precision | Recall | F1 | FPR | TP | FP | TN | FN | LLM calls | Calls avoided |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| detector_only | 49578 | 14686 | 14686 | 0.1222 | 0.8077 | 0.2122 | 0.2722 | 1794 | 12892 | 34465 | 427 | 0 | 49578 |

## 5. Threshold Sweep

| Threshold | Windows | Candidates | Precision | Recall | F1 | FPR | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.70 | 49578 | 17590 | 0.1052 | 0.833 | 0.1868 | 0.3324 | 1850 | 15740 | 371 |
| 0.75 | 49578 | 16346 | 0.1118 | 0.8226 | 0.1968 | 0.3066 | 1827 | 14519 | 394 |
| 0.80 | 49578 | 15485 | 0.117 | 0.8158 | 0.2047 | 0.2887 | 1812 | 13673 | 409 |
| 0.85 | 49578 | 14686 | 0.1222 | 0.8077 | 0.2122 | 0.2722 | 1794 | 12892 | 427 |
| 0.90 | 49578 | 13936 | 0.1269 | 0.796 | 0.2189 | 0.2569 | 1768 | 12168 | 453 |
| 0.95 | 49578 | 13310 | 0.1317 | 0.7893 | 0.2257 | 0.244 | 1753 | 11557 | 468 |

Threshold 0.85 remains the initial balance point: lower thresholds keep more recall but create more candidates; higher thresholds reduce candidates/FPR but lose recall.

## 6. Domain Analysis

| Domain | Windows | Candidates | Precision | Recall | F1 | FPR | FP | FN |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| application-crash-rate-1 | 5352 | 1329 | 0.4432 | 0.8068 | 0.5721 | 0.1601 | 740 | 141 |
| application-crash-rate-2 | 11011 | 1965 | 0.2046 | 0.7053 | 0.3172 | 0.1497 | 1563 | 168 |
| consumer-purchase-rate | 7488 | 2386 | 0.0532 | 0.7427 | 0.0993 | 0.3087 | 2259 | 44 |
| data-ingress-rate | 1320 | 1153 | 0.0278 | 1.0 | 0.054 | 0.8703 | 1121 | 0 |
| ecommerce-api-incoming-rps | 6191 | 2049 | 0.0517 | 0.8833 | 0.0977 | 0.32 | 1943 | 14 |
| middle-tier-api-dependency-latency | 16560 | 4462 | 0.1105 | 0.8915 | 0.1966 | 0.248 | 3969 | 60 |
| mongodb-application-rps | 1056 | 1004 | 0.0209 | 1.0 | 0.041 | 0.9498 | 983 | 0 |
| mongodb-machine-rps | 336 | 336 | 0.0714 | 1.0 | 0.1333 | 1.0 | 312 | 0 |
| service-unavailable | 264 | 2 | 0.0 | 0.0 | 0.0 | 0.0076 | 2 | 0 |

Domains with no positive anomaly windows use `0.0` recall/F1 by denominator convention; use them only to inspect false-positive behavior.

## 7. Interpretation

- `detector_only` evaluated 49578 one-hour windows and generated 14686 candidate alerts. It achieved recall 0.8077 but low precision 0.1222, showing that the metric detector is sensitive enough to catch many anomaly windows but produces many false positives.
- The detector produced 14686 candidates from 49578 windows. This candidate volume is too large for direct external API judging in this thesis setup.
- Detector behavior is uneven by domain. High-FPR domains such as `mongodb-machine-rps`, `mongodb-application-rps`, and `data-ingress-rate` explain much of the false-positive burden.
- The key result collected from this dataset is the detector baseline: it quantifies how many metric windows become alert candidates before the experiment moves to Nezha for log/trace context and LLM judging.
- Legacy mock LLM/RAG plumbing outputs may exist under `cloud_monitor_setup/outputs`, but they are intentionally excluded from this report because this dataset cannot support meaningful RAG evaluation.

## 8. Thesis Usage Guidance

- Use Microsoft cloud-monitoring-dataset in the report as the first metric-only feasibility dataset.
- Use it to explain preprocessing, robust z-score/delta features, one-hour windowing, anomaly labels, detector recall, and false-positive burden.
- Then transition to Nezha for the main hybrid RAG/LLM evaluation because Nezha provides logs/traces/fault labels.
- Do not use this dataset for RAG/API evaluation, since it does not provide real operational log/trace evidence and generates too many candidates.

## 9. Reproduction Commands

```powershell
py cloud_monitor_setup/prepare_cloud_monitor_data.py
py experiments/run_baseline.py --config cloud_monitor_setup/config/experiment_current.yaml --mode detector_only
py -B experiments/run_cloud_threshold_sweep.py
py -B experiments/run_cloud_domain_analysis.py
py -B scripts/summarize_cloud_monitoring_experiment.py
```
