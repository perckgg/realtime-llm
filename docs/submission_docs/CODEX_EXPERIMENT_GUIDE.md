# CODEX_EXPERIMENT_GUIDE.md

## 1. Mục tiêu

Tài liệu này hướng dẫn Codex triển khai thí nghiệm cho kiến trúc giám sát lai trong đề tài:

> Ứng dụng Mô hình Ngôn ngữ Lớn trong xử lý thời gian thực, tập trung vào phát hiện bất thường và thẩm định cảnh báo trong môi trường server/cloud.

Mục tiêu của thí nghiệm **không phải** là đề xuất ngay một kiến trúc tối ưu cuối cùng, mà là kiểm chứng tính khả thi của pipeline lai:

1. Mô hình phát hiện bất thường tốc độ cao xử lý luồng metric.
2. Hệ thống truy xuất log/event liên quan bằng RAG.
3. LLM-as-a-Judge thẩm định cảnh báo dựa trên metric và ngữ cảnh.
4. Hệ thống đo lường false positive reduction, latency, số lần gọi LLM và token/cost.

---

## 2. Kiến trúc thí nghiệm cần triển khai

Pipeline gồm hai luồng dữ liệu chính.

### 2.1. Luồng metric

```text
Metric Stream
    -> Metric Preprocessing
    -> Base Anomaly Detector
    -> Alert Candidate Builder
    -> LLM Gate / Call Policy
    -> Context Retrieval / RAG
    -> Prompt Composer
    -> LLM-as-a-Judge
    -> Decision & Audit
```

### 2.2. Luồng log/event

```text
Log/Event Stream
    -> Log/Event Preprocessing
    -> Chunking
    -> Embedding
    -> Context Store / Vector Database
```

---

## 3. Thành phần cần có trong repository

Codex nên tổ chức project theo cấu trúc sau:

```text
hybrid-monitoring-experiment/
├── README.md
├── requirements.txt
├── .env.example
├── config/
│   ├── experiment.yaml
│   └── prompt_templates/
│       └── judge_prompt.yaml
├── data/
│   ├── raw/
│   │   ├── metrics/
│   │   └── logs/
│   ├── processed/
│   └── sample/
├── src/
│   ├── ingestion/
│   │   ├── metric_loader.py
│   │   └── log_loader.py
│   ├── preprocessing/
│   │   ├── metric_preprocessing.py
│   │   └── log_preprocessing.py
│   ├── detectors/
│   │   ├── base.py
│   │   ├── rrcf_detector.py
│   │   └── isolation_forest_detector.py
│   ├── retrieval/
│   │   ├── context_store.py
│   │   ├── embedder.py
│   │   └── retriever.py
│   ├── llm/
│   │   ├── prompt_composer.py
│   │   ├── judge_client.py
│   │   └── schema.py
│   ├── decision/
│   │   ├── policy.py
│   │   └── audit_logger.py
│   ├── evaluation/
│   │   ├── metrics.py
│   │   └── report.py
│   └── main.py
├── experiments/
│   ├── run_baseline.py
│   ├── run_hybrid.py
│   └── compare_results.py
├── tests/
│   ├── test_preprocessing.py
│   ├── test_detector.py
│   ├── test_retriever.py
│   └── test_llm_schema.py
└── outputs/
    ├── audit/
    ├── results/
    └── figures/
```

---

## 4. Các thành phần kỹ thuật

### 4.1. Metric Preprocessing

Codex cần triển khai:

- Đồng bộ timestamp.
- Sliding window.
- Dynamic Z-score hoặc Min-Max normalization.
- Tạo `metric_window` để đưa vào detector.

Output đề xuất:

```python
{
    "window_id": "...",
    "start_time": "...",
    "end_time": "...",
    "node_id": "...",
    "service_id": "...",
    "features": [[...], [...], ...],
    "feature_names": ["cpu", "memory", "disk_io", "network", "latency"]
}
```

### 4.2. Base Anomaly Detector

Triển khai tối thiểu một detector nhẹ trước:

- `IsolationForestDetector`, hoặc
- `RRCFDetector`.

Nếu còn thời gian, có thể mở rộng sang GNN/MTAD-GAT/GDN, nhưng không bắt buộc ở vòng thí nghiệm đầu tiên.

Output đề xuất:

```python
{
    "window_id": "...",
    "is_candidate": true,
    "anomaly_score": 0.91,
    "detector_label": "anomaly",
    "top_features": ["cpu", "latency"]
}
```

### 4.3. Alert Candidate Builder

Nhiệm vụ:

- Gom thông tin từ detector.
- Trích xuất `time_window`, `node_id`, `service_id`, `metric_snapshot`.
- Tạo payload để gửi sang RAG và LLM.

Output đề xuất:

```python
{
    "alert_id": "...",
    "time_window": {
        "start": "...",
        "end": "..."
    },
    "node_id": "...",
    "service_id": "...",
    "anomaly_score": 0.91,
    "metric_snapshot": {
        "cpu": 94.5,
        "memory": 82.0,
        "disk_io": 76.1,
        "latency": 1200
    }
}
```

### 4.4. LLM Gate / Call Policy

Không gọi LLM cho toàn bộ dữ liệu.

Chính sách gợi ý:

```text
Nếu anomaly_score < low_threshold:
    bỏ qua hoặc chỉ ghi log

Nếu low_threshold <= anomaly_score < high_threshold:
    gọi LLM để thẩm định

Nếu anomaly_score >= high_threshold:
    có thể cảnh báo trực tiếp hoặc vẫn gọi LLM tùy cấu hình
```

Các tham số nên đưa vào `config/experiment.yaml`:

```yaml
llm_gate:
  low_threshold: 0.65
  high_threshold: 0.90
  max_llm_calls_per_minute: 20
```

### 4.5. Log/Event Preprocessing

Codex cần triển khai:

- Chuẩn hóa timestamp.
- Deduplication.
- Regex filtering để loại log nhiễu.
- Chuẩn hóa metadata: `node_id`, `service_id`, `pod_id`, `severity`, `event_type`.
- Giữ lại raw message để phục vụ audit.

Record log/event đề xuất:

```python
{
    "doc_id": "...",
    "timestamp": "...",
    "node_id": "...",
    "service_id": "...",
    "severity": "WARN",
    "event_type": "deployment",
    "message": "Rolling update started for service payment-api"
}
```

### 4.6. Context Store / Vector Database

Ở giai đoạn đầu, có thể dùng FAISS hoặc Chroma local.

Yêu cầu:

- Lưu embedding của log/event.
- Lưu metadata đi kèm.
- Hỗ trợ filter theo:
  - `time_window`
  - `node_id`
  - `service_id`
  - `severity`
  - `event_type`

### 4.7. Context Retrieval / RAG

Không chỉ dùng vector search. Cần dùng hybrid retrieval:

1. Metadata filtering trước:
   - Chỉ lấy log/event trong khoảng thời gian liên quan.
   - Ưu tiên cùng `node_id` hoặc `service_id`.
2. Vector similarity search sau.
3. Trả về `top_k` context.

Output đề xuất:

```python
[
    {
        "doc_id": "...",
        "timestamp": "...",
        "source": "k8s_event",
        "score": 0.87,
        "message": "Autoscaling triggered for service payment-api"
    }
]
```

### 4.8. Prompt Composer

Prompt cần ngắn, có cấu trúc, không nhồi quá nhiều log.

Prompt nên gồm:

1. Vai trò của LLM.
2. Metric snapshot.
3. Anomaly score.
4. Top-k logs/events.
5. Yêu cầu output JSON.

### 4.9. LLM-as-a-Judge Output Schema

LLM phải trả JSON đúng schema:

```json
{
  "label": "true_alert | false_positive | uncertain",
  "severity": "P1 | P2 | P3 | none",
  "confidence": 0.0,
  "evidence": ["log_id_or_event_id"],
  "reason": "short explanation",
  "recommended_action": "short action"
}
```

Yêu cầu bắt buộc:

- Validate JSON bằng Pydantic.
- Nếu parse lỗi, kích hoạt fallback.
- Không chấp nhận text ngoài JSON.

### 4.10. Decision & Audit

Decision logic:

```text
Nếu LLM lỗi hoặc JSON không hợp lệ:
    fallback về cảnh báo gốc từ Base Detector

Nếu label = false_positive:
    suppress alert

Nếu label = true_alert:
    route alert

Nếu label = uncertain hoặc confidence thấp:
    manual review / uncertain bucket
```

Audit DB/log cần lưu:

- alert_id
- metric_window
- anomaly_score
- retrieved_context
- prompt_metadata
- token_count
- llm_latency
- llm_response
- final_decision
- fallback_status

---

## 5. Các baseline cần chạy

Codex nên tạo ít nhất ba chế độ chạy:

### 5.1. Baseline A: Base Detector Only

```text
Metric -> Detector -> Alert
```

Mục tiêu: đo số cảnh báo gốc và false positive trước khi dùng LLM.

### 5.2. Baseline B: LLM Without RAG

```text
Metric -> Detector -> LLM
```

Mục tiêu: kiểm tra LLM khi chỉ có metric, không có log/event.

### 5.3. Proposed Hybrid: Detector + RAG + LLM-as-a-Judge

```text
Metric -> Detector -> RAG -> LLM -> Decision
```

Mục tiêu: đánh giá liệu ngữ cảnh từ log/event có giúp giảm cảnh báo giả không.

---

## 6. Tiêu chí đánh giá

Codex cần tạo script tính các chỉ số sau:

### 6.1. Classification Metrics

- Precision
- Recall
- F1-score
- False Positive Rate
- False Positive Reduction

### 6.2. Runtime Metrics

- End-to-end latency
- Detector latency
- Retrieval latency
- LLM latency
- Throughput

### 6.3. LLM Cost Metrics

- Number of LLM calls
- Input tokens
- Output tokens
- Estimated cost
- JSON valid rate
- Fallback rate

### 6.4. RAG Metrics

- Number of retrieved logs/events
- Retrieval latency
- Context token count
- Top-k sensitivity

---

## 7. Cấu hình thí nghiệm mẫu

Tạo file `config/experiment.yaml`:

```yaml
experiment:
  name: hybrid_monitoring_feasibility
  mode: hybrid

data:
  metric_path: data/sample/metrics.csv
  log_path: data/sample/logs.jsonl

preprocessing:
  window_size: 60
  stride: 10
  normalization: zscore

detector:
  name: isolation_forest
  contamination: 0.05
  threshold: 0.70

retrieval:
  vector_db: faiss
  embedding_model: sentence-transformers/all-MiniLM-L6-v2
  top_k: 5
  time_margin_minutes: 5

llm_gate:
  enabled: true
  low_threshold: 0.65
  high_threshold: 0.90
  max_llm_calls_per_minute: 20

llm:
  provider: openai
  model: gpt-4.1-mini
  temperature: 0
  max_output_tokens: 512

decision:
  confidence_threshold: 0.80

evaluation:
  output_dir: outputs/results
```

---

## 8. Lệnh chạy mong muốn

Codex nên triển khai các lệnh sau:

```bash
python experiments/run_baseline.py --config config/experiment.yaml --mode detector_only
python experiments/run_baseline.py --config config/experiment.yaml --mode llm_without_rag
python experiments/run_hybrid.py --config config/experiment.yaml
python experiments/compare_results.py --input outputs/results
```

---

## 9. Quy tắc làm việc cho Codex

Khi triển khai, Codex phải tuân thủ:

1. Không hard-code đường dẫn dữ liệu; đọc từ config.
2. Mỗi tầng pipeline cần có interface rõ ràng.
3. Mỗi output trung gian nên lưu vào `outputs/audit/`.
4. Mọi response của LLM phải validate bằng schema.
5. Nếu LLM lỗi, không làm crash toàn pipeline; dùng fallback.
6. Không gọi API thật trong unit test; dùng mock.
7. Viết test cho preprocessing, detector, retrieval, JSON schema.
8. Mọi thay đổi lớn cần cập nhật README.
9. Ưu tiên code đơn giản, dễ đọc, dễ tái hiện thí nghiệm.
10. Ghi rõ các giả định nếu dữ liệu thật chưa sẵn có.

---

## 10. Kết quả mong muốn sau khi Codex hoàn thành

Codex cần tạo được:

- Pipeline chạy được end-to-end trên dữ liệu mẫu.
- Baseline detector-only.
- Baseline LLM-without-RAG.
- Pipeline hybrid Detector + RAG + LLM.
- File kết quả CSV/JSON.
- Báo cáo so sánh ngắn.
- Audit log để kiểm tra từng quyết định.
- Test cơ bản cho các module chính.

---

## 11. Phạm vi không bắt buộc ở giai đoạn đầu

Không cần triển khai ngay:

- Full production streaming bằng Kafka/Flink.
- UI dashboard.
- Human-in-the-loop thật.
- Alert routing P1/P2/P3 đầy đủ.
- Fine-tuning LLM.
- GNN phức tạp nếu chưa có đủ dữ liệu.
- Distributed vector database.

Các phần trên có thể được xem là hướng mở rộng sau khi pipeline cơ bản chứng minh được tính khả thi.
