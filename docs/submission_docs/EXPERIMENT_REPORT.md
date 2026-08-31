# Hybrid Monitoring Experiment Report

## 1. Mục tiêu thí nghiệm

Thí nghiệm này kiểm chứng một kiến trúc giám sát lai cho môi trường server/cloud:

```text
Metric -> Preprocessing -> Detector -> Alert Candidate
       -> LLM Gate -> RAG Retrieval -> LLM-as-a-Judge
       -> Decision/Fallback -> Audit/Evaluation
```

Mục tiêu hiện tại là kiểm chứng tính khả thi, không phải xây dựng hệ thống production real-time hoàn chỉnh.

## 2. Những gì đã thực hiện

| Hạng mục | Trạng thái |
|---|---|
| Pipeline end-to-end | Đã chạy được với sample data, Microsoft Cloud Monitoring Dataset, và Nezha |
| Metric preprocessing | Có timestamp normalization, sliding window, normalization, raw metric snapshot |
| Detector | Có `FeaturePressureDetector` và sklearn `IsolationForestDetector` thật |
| Alert candidate | Có payload chuẩn gồm alert id, time window, node/service, metric snapshot, anomaly score |
| LLM gate | Có threshold policy, giới hạn tổng LLM calls, và rate limit theo phút cho provider thật |
| RAG retrieval | Có ranker semantic + time proximity + metadata + severity/trace signal |
| Vector/RAG backend | Có `local_hashing`, `hybrid_bm25`, optional FAISS nếu cài `faiss-cpu`; hiện dùng `hybrid_bm25` cho thí nghiệm RAG không cần native dependency |
| LLM judge | Có mock judge và Gemini provider thật |
| Gemini structured output | Có `responseSchema`, tắt `thinkingBudget`, validate JSON bằng Pydantic |
| Decision/fallback | Có route/suppress/manual/fallback khi LLM lỗi hoặc JSON invalid |
| Audit logging | Có JSONL audit cho từng window/alert |
| Evaluation | Có precision, recall, F1, FPR, false positive reduction, latency, token, fallback rate |
| Group metrics | Có metrics theo `service_id` và `fault_type` |
| Report output | Mỗi run sinh JSON đầy đủ, summary Markdown, summary CSV, config snapshot |
| Ablation study | Có runner so sánh detector-only, LLM without RAG, hybrid, hybrid no gate |
| Streaming replay | Có runner replay window theo thời gian, context được nạp theo watermark |
| Phase 4 benchmark | Có runner benchmark detector-only, LLM without RAG, local hashing RAG, hybrid BM25 RAG |
| Retrieval/cost metrics | Có context coverage, avg context count, context tokens, và estimated LLM cost theo config |
| Context rescue | Có bước hậu Phase 4 dùng log/trace signal để promote candidate bị metric detector bỏ lỡ |
| Local-first LLM judge | Có Ollama `qwen2.5:1.5b` chạy local trước và Gemini API fallback khi local lỗi/uncertain/confidence thấp/high anomaly |
| Tests | Có unit tests cho preprocessing, detector, Isolation Forest, retriever, LLM schema/fallback |

## 3. Dataset đã xử lý

### 3.1. Sample Dataset

Dataset nhỏ trong `data/sample/` dùng để kiểm tra nhanh pipeline.

File chính:

```text
data/sample/metrics.csv
data/sample/logs.jsonl
```

### 3.2. Microsoft Cloud Monitoring Dataset

Setup riêng:

```text
cloud_monitor_setup/
```

Đặc điểm:

- Có time series và label anomaly.
- Không có log/trace operational thật.
- Phù hợp làm detector-only baseline hơn là đánh giá hybrid RAG.

Kết quả xử lý:

| Metric | Value |
|---|---:|
| Time series | 60 |
| Valid points | 225,403 |
| Anomaly points | 4,553 |
| Skipped missing points | 42 |

### 3.3. Nezha Dataset

Setup riêng:

```text
nezha_setup/
```

Đặc điểm:

- Có metric, log, trace, traceid và fault list.
- Phù hợp nhất để đánh giá hybrid RAG + LLM judge.

Kết quả xử lý:

| Metric | Value |
|---|---:|
| Fault count | 101 |
| Metric files | 112 |
| Metric rows | 95,660 |
| Labeled metric rows | 527 |
| Log events | 5,921 |
| Trace events | 5,775 |
| Context events | 11,696 |

## 4. Kết quả đạt được

### 4.1. Nezha Smoke Mock

Config:

```text
nezha_setup/config/experiment_nezha_smoke.yaml
```

Kết quả gần nhất:

| Metric | Value |
|---|---:|
| Evaluated windows | 50 |
| Candidate alerts | 5 |
| LLM calls | 5 |
| JSON valid rate | 1.0 |
| Precision | 1.0 |
| Recall | 0.3333 |
| F1 | 0.5 |

Output:

```text
nezha_setup/outputs/smoke/results/
```

### 4.2. Nezha Medium Mock

Config:

```text
nezha_setup/config/experiment_nezha_medium.yaml
```

Kết quả gần nhất:

| Metric | Value |
|---|---:|
| Evaluated windows | 5,000 |
| Candidate alerts | 2,136 |
| Routed alerts | 1,992 |
| LLM calls | 200 |
| LLM calls avoided | 4,800 |
| LLM budget exhausted | 1,936 |
| JSON valid rate | 1.0 |
| Precision | 0.0361 |
| Recall | 0.6429 |
| F1 | 0.0684 |
| FPR | 0.3928 |

Kết quả theo service:

| Service | Precision | Recall | FPR | Notes |
|---|---:|---:|---:|---|
| `cartservice` | 0.7059 | 0.3750 | 0.0026 | Tốt nhất trong medium run |
| `checkoutservice` | 0.0454 | 0.7344 | 0.5297 | Nhiều false positive |
| `currencyservice` | 0.0138 | 0.8125 | 0.8253 | Nhiễu cao, cần tuning |

Kết quả theo fault type:

| Fault type | Precision | Recall | F1 |
|---|---:|---:|---:|
| `cpu_consumed` | 1.0 | 0.8750 | 0.9333 |
| `cpu_contention` | 1.0 | 0.7812 | 0.8772 |
| `exception` | 1.0 | 0.8125 | 0.8966 |
| `return` | 1.0 | 0.8125 | 0.8966 |
| `network_delay` | 1.0 | 0.3500 | 0.5185 |

Điểm đáng chú ý: `network_delay` có recall thấp hơn, còn false positives tập trung nhiều ở nhóm `none`, đặc biệt quanh `checkoutservice` và `currencyservice`.

### 4.3. Gemini Smoke

Config:

```text
nezha_setup/config/experiment_gemini_smoke.yaml
```

Đã kết nối được Gemini API thật qua `GEMINI_API_KEY` trong `.env`.

Những gì đã xử lý:

- Thêm Gemini REST provider.
- Thêm structured JSON schema.
- Tắt `thinkingBudget` để tránh JSON bị cắt.
- Parse token usage thật từ `usageMetadata` khi Gemini trả về.
- Thêm retry/backoff cho `429/5xx`.
- Thêm pacing bằng `llm_gate.max_llm_calls_per_minute`.

Lưu ý hiện tại:

- Gemini free tier có thể trả `429 Too Many Requests`.
- Khi bị 429, pipeline fallback đúng, nhưng kết quả LLM thật không đại diện.
- Cần giảm thêm `max_llm_calls_per_minute` hoặc chờ quota reset nếu muốn chạy Gemini nhiều hơn.

### 4.4. Phase 3 Smoke: Isolation Forest + Improved Retriever

Config:

```text
nezha_setup/config/experiment_phase3_smoke.yaml
```

Kết quả smoke gần nhất:

| Metric | Value |
|---|---:|
| Evaluated windows | 200 |
| Candidate alerts | 35 |
| Routed alerts | 24 |
| LLM calls | 20 |
| JSON valid rate | 1.0 |
| Precision | 0.25 |
| Recall | 0.375 |
| F1 | 0.3 |
| FPR | 0.0978 |

Output:

```text
nezha_setup/outputs/phase3_smoke/results/
```

Điểm đáng chú ý: Isolation Forest giảm mạnh số candidate trong smoke 200 windows. Retrieval mới ghi thêm các thành phần điểm `semantic_score`, `time_score`, `metadata_score`, `severity_score`, `trace_score` trong context payload.

### 4.5. Phase 3 Gemini Smoke + Hybrid BM25 RAG

Config:

```text
nezha_setup/config/experiment_phase3_gemini_smoke.yaml
```

Kết quả smoke gần nhất:

| Metric | Value |
|---|---:|
| Evaluated windows | 80 |
| Candidate alerts | 12 |
| Routed alerts | 9 |
| LLM calls | 3 |
| LLM errors | 0 |
| JSON valid rate | 1.0 |
| Precision | 0.6667 |
| Recall | 0.375 |
| F1 | 0.48 |
| FPR | 0.0469 |
| Retrieval backend | `local_hybrid_bm25` |
| Token source | `gemini_usage_metadata` |

Output:

```text
nezha_setup/outputs/phase3_gemini_smoke/results/
```

Do `faiss-cpu` không setup ổn trên máy hiện tại, Phase 3 Gemini dùng `hybrid_bm25`: BM25 lexical scoring kết hợp hashing semantic, sau đó retriever cộng thêm điểm time/metadata/severity/trace. Cách này phù hợp với log/trace vì nhiều tín hiệu quan trọng nằm trong token cụ thể như service name, node id, operation, `duration_ms`, `ERROR`, `WARN`.

### 4.6. Phase 3 Ablation

Runner:

```text
experiments/run_ablation.py
```

Kết quả gần nhất trên 200 windows:

| Variant | Candidates | Precision | Recall | F1 | FPR | FP Reduction vs Detector | LLM Calls |
|---|---:|---:|---:|---:|---:|---:|---:|
| `detector_only` | 35 | 0.1714 | 0.3750 | 0.2353 | 0.1576 | 0.0 | 0 |
| `llm_without_rag` | 35 | 0.0 | 0.0 | 0.0 | 0.0815 | 0.4828 | 20 |
| `hybrid` | 35 | 0.25 | 0.3750 | 0.3 | 0.0978 | 0.3793 | 20 |
| `hybrid_no_gate` | 35 | 0.25 | 0.3750 | 0.3 | 0.0978 | 0.3793 | 20 |

Output:

```text
nezha_setup/outputs/phase3_smoke/ablation/
```

### 4.7. Phase 3 Streaming Replay

Runner:

```text
experiments/run_streaming_replay.py
```

Kết quả smoke 50 windows:

| Metric | Value |
|---|---:|
| Evaluated windows | 50 |
| Candidate alerts | 9 |
| Routed alerts | 9 |
| LLM calls | 9 |
| Precision | 0.5556 |
| Recall | 0.3333 |
| F1 | 0.4167 |
| FPR | 0.1143 |

Output:

```text
nezha_setup/outputs/phase3_streaming/results/
```

Streaming replay hiện xử lý window theo timestamp và chỉ ingest log/trace đến watermark của window, tránh dùng context tương lai như batch mode.

### 4.8. Phase 4 Benchmark: RAG Backend + Retrieval Metrics

Config:

```text
nezha_setup/config/experiment_phase4_benchmark.yaml
```

Runner:

```text
experiments/run_phase4_benchmark.py
```

Phase 4 bổ sung:

- Benchmark có kiểm soát giữa `detector_only`, `llm_without_rag`, `hybrid_local_top6`, `hybrid_bm25_top6`, `hybrid_bm25_top10`.
- Metrics RAG mới: `avg_retrieved_context_count`, `context_coverage_rate`, `context_tokens`, `avg_context_tokens`.
- Cost estimate theo config: `estimated_input_cost_usd`, `estimated_output_cost_usd`, `estimated_llm_cost_usd`.
- Unit tests riêng cho evaluation summary và cost estimate.

Kết quả benchmark gần nhất trên 300 windows, mock LLM:

| Variant | Candidates | Precision | Recall | F1 | FPR | FP Reduction | LLM Calls | Context Coverage | Avg Context | Retrieval ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `detector_only` | 40 | 0.1500 | 0.3750 | 0.2143 | 0.1197 | 0.0000 | 0 | 0.0000 | 0.0000 | 0.0000 |
| `llm_without_rag` | 40 | 0.0000 | 0.0000 | 0.0000 | 0.0352 | 0.7059 | 30 | 0.0000 | 0.0000 | 0.0000 |
| `hybrid_local_top6` | 40 | 0.3158 | 0.3750 | 0.3429 | 0.0458 | 0.6176 | 30 | 0.2250 | 0.1667 | 6.4785 |
| `hybrid_bm25_top6` | 40 | 0.3158 | 0.3750 | 0.3429 | 0.0458 | 0.6176 | 30 | 0.2250 | 0.1667 | 11.1465 |
| `hybrid_bm25_top10` | 40 | 0.3158 | 0.3750 | 0.3429 | 0.0458 | 0.6176 | 30 | 0.2250 | 0.2733 | 10.3172 |

Output:

```text
nezha_setup/outputs/phase4_benchmark/results/
```

Nhận định: trong lát cắt 300 windows này, `hybrid_bm25` và `local_hashing` cho cùng classification metrics vì số context liên quan còn ít. `hybrid_bm25_top10` lấy nhiều context hơn nhưng chưa cải thiện F1. Bottleneck chính hiện là detector chưa bắt được `network_delay`: nhóm này có 8 windows true alert nhưng 0 candidate.

### 4.9. Phase 5: Context Rescue + Gemini API

Sau Phase 4, bottleneck rõ nhất là metric detector bỏ lỡ `network_delay`. Phase 5 thêm một bước `candidate_rescue`:

```text
Metric Detector normal
  -> RAG context check nhẹ
  -> Nếu trace/log mạnh: promote thành candidate
  -> LLM gate / judge như bình thường
```

Config mock:

```text
nezha_setup/config/experiment_phase5_context_rescue.yaml
```

Kết quả mock trên 300 windows:

| Metric | Value |
|---|---:|
| Evaluated windows | 300 |
| Candidate alerts | 55 |
| Context rescue checked | 260 |
| Context rescue promoted | 15 |
| Network delay promoted | 8 |
| LLM calls | 55 |
| Precision | 0.64 |
| Recall | 1.0 |
| F1 | 0.7805 |
| FPR | 0.0317 |
| Avg retrieval latency ms | 135.6469 |

Theo fault type:

| Fault type | Precision | Recall | F1 | Candidates |
|---|---:|---:|---:|---:|
| `cpu_contention` | 1.0 | 1.0 | 1.0 | 8 |
| `network_delay` | 1.0 | 1.0 | 1.0 | 8 |
| `none` | 0.0 | 0.0 | 0.0 | 39 |

Config Gemini:

```text
nezha_setup/config/experiment_phase5_gemini_smoke.yaml
```

Kết quả Gemini smoke trên 45 windows:

| Metric | Value |
|---|---:|
| Evaluated windows | 45 |
| Candidate alerts | 19 |
| Context rescue checked | 41 |
| Context rescue promoted | 15 |
| Network delay promoted | 8 |
| Gemini calls | 6 |
| Gemini errors | 0 |
| Gemini usage metadata records | 6 |
| JSON valid rate | 1.0 |
| Precision | 0.6667 |
| Recall | 1.0 |
| F1 | 0.8 |
| FPR | 0.1429 |

Output:

```text
nezha_setup/outputs/phase5_context_rescue/results/
nezha_setup/outputs/phase5_gemini_smoke/results/
```

Tradeoff: context rescue tăng recall rất mạnh, đặc biệt cứu được `network_delay`, nhưng làm retrieval latency tăng vì phải kiểm tra context cho nhiều non-candidate. Đây là bước hợp lý cho nghiên cứu, nhưng nếu tiến gần production cần thêm sampling/budget cho rescue.

### 4.10. Local-First LLM-as-a-Judge: Ollama + API Fallback

Mục tiêu:

```text
Candidate Alert + Retrieved Context
  -> Local Ollama Judge
  -> Nếu local JSON hợp lệ và confidence đủ cao: dùng local
  -> Nếu local lỗi / uncertain / confidence thấp / anomaly_score quá cao: gọi Gemini API fallback
```

Config:

```text
nezha_setup/config/experiment_local_first_ollama_smoke.yaml
```

Local model:

```text
qwen2.5:1.5b
```

Các thay đổi chính:

- Thêm provider `ollama` trong `src/llm/judge_client.py`.
- Thêm `LocalFirstJudgeClient` trong `src/llm/local_first_judge.py`.
- Ollama dùng JSON schema ở tham số `format` để ép output đúng schema.
- Audit ghi thêm `llm_provider`, `llm_model`, `api_fallback_used`, `api_fallback_reason`, `local_result_valid_json`, `local_result_label`, `local_result_confidence`.
- Evaluation ghi thêm `api_fallback_calls`, `local_llm_valid_json`, `llm_providers`.

Kết quả smoke local-first trên 45 windows:

| Metric | Value |
|---|---:|
| Evaluated windows | 45 |
| Candidate alerts | 19 |
| LLM calls | 6 |
| Final Ollama decisions | 2 |
| Gemini fallback decisions | 4 |
| Local valid JSON records | 3 |
| API fallback calls | 4 |
| JSON valid rate | 1.0 |
| Pipeline LLM errors | 0 |
| Precision | 0.625 |
| Recall | 1.0 |
| F1 | 0.7692 |
| FPR | 0.1714 |

Fallback reasons trong lần chạy gần nhất:

| Reason | Count |
|---|---:|
| `local_error` | 3 |
| `high_anomaly_score` | 1 |

Output:

```text
nezha_setup/outputs/local_first_ollama_smoke/results/
```

Nhận định: local-first đã hoạt động đúng chiến lược. Sau khi ép JSON schema, Qwen local đã trả được JSON hợp lệ và xử lý được một phần cảnh báo. Tuy nhiên model nhỏ `qwen2.5:1.5b` vẫn chưa ổn định schema/quality trên mọi case, nên API fallback vẫn cần thiết.

## 5. Cấu trúc source code

```text
src/
├── config.py
├── main.py
├── models.py
├── time_utils.py
├── ingestion/
│   ├── metric_loader.py
│   └── log_loader.py
├── preprocessing/
│   ├── metric_preprocessing.py
│   └── log_preprocessing.py
├── detectors/
│   ├── base.py
│   ├── factory.py
│   ├── feature_pressure_detector.py
│   ├── isolation_forest_detector.py
│   └── rrcf_detector.py
├── retrieval/
│   ├── context_store.py
│   ├── embedder.py
│   └── retriever.py
├── llm/
│   ├── judge_client.py
│   ├── local_first_judge.py
│   ├── prompt_composer.py
│   └── schema.py
├── decision/
│   ├── audit_logger.py
│   └── policy.py
└── evaluation/
    ├── metrics.py
    └── report.py
```

### 5.1. `src/ingestion`

Đọc dữ liệu đầu vào:

- `metric_loader.py`: đọc CSV metric chuẩn hóa.
- `log_loader.py`: đọc JSONL logs/events.

### 5.2. `src/preprocessing`

Chuẩn hóa dữ liệu:

- `metric_preprocessing.py`
  - tạo sliding windows
  - normalization
  - giữ raw features
  - gắn `label` và `fault_type`
- `log_preprocessing.py`
  - parse timestamp
  - deduplication
  - regex filtering
  - chuẩn hóa metadata log/event

### 5.3. `src/detectors`

Detector layer:

- `base.py`: abstract detector interface.
- `factory.py`: chọn detector theo config.
- `feature_pressure_detector.py`: detector chính hiện tại, dependency-light.
- `isolation_forest_detector.py`: sklearn Isolation Forest thật, có `fit()` trên metric windows và score percentile.
- `rrcf_detector.py`: placeholder tương thích interface.

### 5.4. `src/retrieval`

RAG retrieval:

- `embedder.py`: hashing embedder và cosine similarity.
- `context_store.py`: local context store, có `search()`, `hybrid_bm25`, và optional FAISS flat index nếu cài `faiss-cpu`.
- `retriever.py`: hybrid retrieval bằng semantic search + time proximity + metadata + severity/trace scoring.

Trong môi trường hiện tại backend thực tế vẫn là:

```text
local_hashing
```

FAISS đã có implementation optional, nhưng máy hiện tại chưa cài `faiss-cpu`, nên thí nghiệm RAG mới dùng:

```text
local_hybrid_bm25
```

Chroma vẫn là fallback an toàn.

### 5.5. `src/llm`

LLM judge:

- `prompt_composer.py`: tạo prompt JSON ngắn, ràng buộc evidence IDs.
- `schema.py`: Pydantic schema validation.
- `judge_client.py`:
  - `mock` provider
  - `gemini` provider
  - `ollama` provider
  - structured output
  - token usage parsing
  - retry/backoff
- `local_first_judge.py`:
  - gọi Ollama trước
  - fallback sang API khi local lỗi, uncertain, confidence thấp, hoặc anomaly score quá cao

### 5.6. `src/decision`

Decision layer:

- `policy.py`:
  - build alert candidate
  - LLM gate
  - final decision
- `audit_logger.py`:
  - ghi JSONL audit.

### 5.7. `src/evaluation`

Evaluation/report:

- `metrics.py`:
  - precision, recall, F1, FPR
  - LLM calls, token, fallback
  - retrieval context coverage và context token metrics
  - group metrics theo service/fault type
- `report.py`:
  - full results JSON
  - summary Markdown
  - summary CSV
  - by-service CSV
  - by-fault-type CSV
  - estimated LLM cost theo config
  - config snapshot

## 6. Cấu trúc setup dữ liệu

### 6.1. Nezha setup

```text
nezha_setup/
├── README.md
├── prepare_nezha_data.py
├── config/
│   ├── experiment_nezha_smoke.yaml
│   ├── experiment_nezha_medium.yaml
│   ├── experiment_nezha_full.yaml
│   ├── experiment_phase3_smoke.yaml
│   ├── experiment_phase3_gemini_smoke.yaml
│   ├── experiment_phase4_benchmark.yaml
│   ├── experiment_phase5_context_rescue.yaml
│   ├── experiment_phase5_gemini_smoke.yaml
│   ├── experiment_local_first_ollama_smoke.yaml
│   ├── experiment_gemini_smoke.yaml
│   └── experiment.yaml
├── processed/
│   ├── metrics.csv
│   ├── logs.jsonl
│   └── summary.json
└── outputs/
```

### 6.2. Microsoft Cloud Monitoring setup

```text
cloud_monitor_setup/
├── README.md
├── prepare_cloud_monitor_data.py
├── config/
│   └── experiment.yaml
├── processed/
│   ├── metrics.csv
│   ├── logs.jsonl
│   └── summary.json
└── outputs/
```

## 7. Hướng dẫn chạy

### 7.1. Chạy unit tests

Trên máy hiện tại nên dùng `py`, vì `python` có thể trỏ tới Microsoft Store alias.

```powershell
py -m unittest discover -s tests
```

Kết quả hiện tại:

```text
Ran 20 tests
OK
```

### 7.2. Chuẩn bị dữ liệu Nezha

```powershell
py nezha_setup/prepare_nezha_data.py
```

Output:

```text
nezha_setup/processed/metrics.csv
nezha_setup/processed/logs.jsonl
nezha_setup/processed/summary.json
```

### 7.3. Chạy Nezha smoke mock

```powershell
py experiments/run_baseline.py --config nezha_setup/config/experiment_nezha_smoke.yaml --mode detector_only
py experiments/run_hybrid.py --config nezha_setup/config/experiment_nezha_smoke.yaml
py experiments/compare_results.py --input nezha_setup/outputs/smoke/results
```

### 7.4. Chạy Nezha medium mock

```powershell
py experiments/run_hybrid.py --config nezha_setup/config/experiment_nezha_medium.yaml
```

Output:

```text
nezha_setup/outputs/medium/results/
```

Các file đáng xem:

```text
hybrid_summary.md
hybrid_summary.csv
hybrid_by_service.csv
hybrid_by_fault_type.csv
hybrid_config_snapshot.json
hybrid_results.json
```

### 7.5. Chạy Gemini smoke

Yêu cầu `.env` có:

```text
GEMINI_API_KEY=<your_key>
```

Chạy:

```powershell
$env:GEMINI_API_KEY = ((Get-Content -LiteralPath .env | Where-Object { $_ -match '^GEMINI_API_KEY=' } | Select-Object -First 1) -replace '^GEMINI_API_KEY=', '').Trim()
py experiments/run_hybrid.py --config nezha_setup/config/experiment_gemini_smoke.yaml
```

Khuyến nghị:

- Chỉ chạy smoke trước.
- Không chạy full Gemini ngay.
- Nếu gặp `429 Too Many Requests`, giảm `llm_gate.max_llm_calls_per_minute`, giảm `evaluation.max_llm_calls`, hoặc chờ quota reset.

### 7.6. Chạy Phase 3 smoke

```powershell
py experiments/run_hybrid.py --config nezha_setup/config/experiment_phase3_smoke.yaml
```

### 7.7. Chạy Phase 3 Gemini smoke

```powershell
$env:GEMINI_API_KEY = ((Get-Content -LiteralPath .env | Where-Object { $_ -match '^GEMINI_API_KEY=' } | Select-Object -First 1) -replace '^GEMINI_API_KEY=', '').Trim()
py experiments/run_hybrid.py --config nezha_setup/config/experiment_phase3_gemini_smoke.yaml
```

### 7.8. Chạy ablation study

```powershell
py experiments/run_ablation.py --config nezha_setup/config/experiment_phase3_smoke.yaml
```

Output:

```text
nezha_setup/outputs/phase3_smoke/ablation/ablation_summary.md
nezha_setup/outputs/phase3_smoke/ablation/ablation_summary.csv
nezha_setup/outputs/phase3_smoke/ablation/ablation_report.json
```

### 7.9. Chạy streaming replay

```powershell
py experiments/run_streaming_replay.py --config nezha_setup/config/experiment_phase3_smoke.yaml --output-dir nezha_setup/outputs/phase3_streaming/results --audit-dir nezha_setup/outputs/phase3_streaming/audit --max-windows 50
```

### 7.10. Chạy Phase 4 benchmark

```powershell
py experiments/run_phase4_benchmark.py --config nezha_setup/config/experiment_phase4_benchmark.yaml
```

Output:

```text
nezha_setup/outputs/phase4_benchmark/results/phase4_benchmark_summary.md
nezha_setup/outputs/phase4_benchmark/results/phase4_benchmark_summary.csv
nezha_setup/outputs/phase4_benchmark/results/phase4_benchmark_report.json
```

### 7.11. Chạy Phase 5 context rescue mock

```powershell
py experiments/run_hybrid.py --config nezha_setup/config/experiment_phase5_context_rescue.yaml
```

### 7.12. Chạy Phase 5 Gemini smoke

```powershell
$env:GEMINI_API_KEY = ((Get-Content -LiteralPath .env | Where-Object { $_ -match '^GEMINI_API_KEY=' } | Select-Object -First 1) -replace '^GEMINI_API_KEY=', '').Trim()
py experiments/run_hybrid.py --config nezha_setup/config/experiment_phase5_gemini_smoke.yaml
```

### 7.13. Chạy Local-first Ollama + API fallback

Yêu cầu Ollama đang chạy local và đã có model:

```powershell
ollama pull qwen2.5:1.5b
```

Chạy:

```powershell
$env:GEMINI_API_KEY = ((Get-Content -LiteralPath .env | Where-Object { $_ -match '^GEMINI_API_KEY=' } | Select-Object -First 1) -replace '^GEMINI_API_KEY=', '').Trim()
py experiments/run_hybrid.py --config nezha_setup/config/experiment_local_first_ollama_smoke.yaml
```

## 8. Hạn chế hiện tại

| Hạn chế | Ghi chú |
|---|---|
| Chưa production real-time streaming | Đã có streaming replay giả lập từ CSV, chưa có message broker |
| Detector metric-only vẫn chưa đủ | Context rescue đã cứu `network_delay`, nhưng bản chất metric-only IF vẫn miss nhóm này |
| Vector DB phụ thuộc dependency | FAISS optional đã có, nhưng máy hiện tại chưa cài `faiss-cpu`; `hybrid_bm25` là backend local thay thế |
| Retrieval latency tăng ở context rescue | Phase 5 kiểm tra nhiều non-candidate nên avg retrieval latency tăng đáng kể |
| Local model nhỏ chưa ổn định hoàn toàn | `qwen2.5:1.5b` đã dùng được nhưng vẫn cần schema forcing và API fallback |
| Gemini free tier dễ 429 | Cần pacing/rate limit chặt hơn |
| Cost estimate chưa hoàn hảo | Gemini có token usage thật, mock vẫn estimate |
| Full result JSON lớn | Đã có summary CSV/MD để đọc nhanh hơn |

## 9. Hướng cải thiện tiếp theo

Ưu tiên gần nhất:

1. Thêm budget/sampling cho context rescue để giảm retrieval latency khi chạy rộng hơn.
2. Tune local-first thresholds: `local_confidence_threshold`, `fallback_on_uncertain`, `high_anomaly_fallback_threshold`.
3. Mở rộng Phase 5/local-first benchmark lên 1,000-5,000 windows để xem recall/FPR/API fallback rate có ổn định không.
4. Tune `candidate_rescue.min_context_score`, `min_trace_duration_ms`, và `min_detector_score` theo service/fault type.
5. Thêm trace dependency graph để retrieval hiểu upstream/downstream thay vì chỉ cùng service/node.
6. Tách cost report riêng cho Gemini bằng pricing config thật tại thời điểm chạy.
7. Nếu cần vector DB thật, thử Chroma trước FAISS vì ít phụ thuộc native hơn trên Windows.
8. Nâng streaming replay thành ingestion service có queue/watermark/backpressure.

## 10. Kết luận

Thiết kế hiện tại đã bám được skeleton kiến trúc ban đầu và chạy được end-to-end. Nezha là dataset phù hợp nhất cho hybrid vì có đủ metric, log, trace và fault labels. Microsoft Cloud Monitoring Dataset hữu ích cho detector baseline nhưng không đủ context để đánh giá RAG/LLM.

Hệ thống hiện đã có nền tảng thí nghiệm tương đối sạch: có cấu hình, audit, fallback, report, smoke/medium/full configs, Isolation Forest thật, `hybrid_bm25` RAG, Gemini smoke thật, local-first Ollama + API fallback, ablation, streaming replay, Phase 4 benchmark, Phase 5 context rescue, và kiểm thử cơ bản. Kết quả mới cho thấy hướng hybrid metric + context signal hiệu quả hơn metric-only cho `network_delay`; local-first cũng khả thi nhưng model nhỏ cần API fallback để giữ độ tin cậy.
