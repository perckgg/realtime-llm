from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"


INVENTORY: list[tuple[str, str]] = [
    ("EXPERIMENT_REPORT_FOR_SUBMISSION.md", "Main thesis-facing experiment report"),
    ("EXPERIMENT_REPORT.md", "Long-form experiment report/history"),
    ("DATASET_REPORT.md", "Dataset analysis report"),
    ("outputs/dataset_analysis/dataset_analysis_summary.json", "Dataset summary JSON"),
    ("nezha_setup/outputs/phase3_smoke/ablation/ablation_summary.md", "Phase 3 ablation Markdown"),
    ("nezha_setup/outputs/phase3_smoke/ablation/ablation_summary.csv", "Phase 3 ablation CSV"),
    ("nezha_setup/outputs/phase3_smoke/ablation/ablation_report.json", "Phase 3 ablation JSON"),
    ("nezha_setup/outputs/phase4_benchmark/results/phase4_benchmark_summary.md", "Phase 4 benchmark Markdown"),
    ("nezha_setup/outputs/phase4_benchmark/results/phase4_benchmark_summary.csv", "Phase 4 benchmark CSV"),
    ("nezha_setup/outputs/phase4_benchmark/results/phase4_benchmark_report.json", "Phase 4 benchmark JSON"),
    ("nezha_setup/outputs/phase5_context_rescue/results/hybrid_summary.md", "Phase 5 context rescue Markdown"),
    ("nezha_setup/outputs/phase5_context_rescue/results/hybrid_summary.csv", "Phase 5 context rescue CSV"),
    ("nezha_setup/outputs/phase5_context_rescue/results/hybrid_results.json", "Phase 5 context rescue JSON"),
    ("nezha_setup/outputs/local_first_ollama_smoke/results/hybrid_summary.md", "Local-first smoke Markdown"),
    ("nezha_setup/outputs/local_first_ollama_smoke/results/hybrid_summary.csv", "Local-first smoke CSV"),
    ("nezha_setup/outputs/local_first_ollama_smoke/results/hybrid_results.json", "Local-first smoke JSON"),
    ("nezha_setup/outputs/phase3_streaming/results/streaming_hybrid_summary.md", "Streaming replay Markdown"),
    ("nezha_setup/outputs/llm_response_cache.jsonl", "LLM response cache, optional"),
    ("nezha_setup/outputs/real_llm_stratified/results/gemini25_flash_lite_500w_budget_manual_review_cache_replay_summary.md", "Gemini 500-window cache replay summary"),
    ("cloud_monitor_setup/outputs/current_results/detector_only_results.json", "Microsoft cloud-monitoring detector-only result"),
    ("reports/cloud_monitoring_experiment_report.md", "Microsoft cloud-monitoring experiment report"),
    ("reports/cloud_monitoring_experiment_metrics.csv", "Microsoft cloud-monitoring metrics CSV"),
    ("reports/audit_failure_analysis.md", "Nezha audit-derived FP/FN fault/service/pod analysis"),
    ("reports/audit_failure_by_fault_type.csv", "Nezha audit FP/FN grouped by fault type"),
    ("reports/audit_failure_by_service.csv", "Nezha audit FP/FN grouped by service"),
    ("reports/audit_failure_by_pod.csv", "Nezha audit FP/FN grouped by pod/node"),
    ("reports/audit_failure_hotspots.csv", "Nezha audit top FP/FN hotspot table"),
]


CONSOLIDATED_COLUMNS = [
    "experiment_phase",
    "variant",
    "windows",
    "candidates",
    "precision",
    "recall",
    "f1",
    "fpr",
    "tp",
    "fp",
    "fn",
    "llm_calls",
    "api_fallback_calls",
    "context_coverage",
    "avg_context",
    "retrieval_ms",
    "avg_llm_ms",
    "notes",
]


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    rows = build_consolidated_rows()
    write_inventory()
    write_consolidated_csv(rows)
    write_evaluation_criteria_mapping()
    write_tradeoff_analysis(rows)
    write_experiment_summary(rows)
    write_thesis_insert_sections(rows)


def build_consolidated_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    rows.extend(rows_from_summary_json(
        "Microsoft cloud-monitoring",
        "detector_only",
        "cloud_monitor_setup/outputs/current_results/detector_only_results.json",
        "Metric-only detector baseline; RAG/API evaluation is intentionally not used for this dataset.",
    ))
    rows.extend(rows_from_variant_json("Phase 3 ablation", "nezha_setup/outputs/phase3_smoke/ablation/ablation_report.json"))
    rows.extend(rows_from_variant_json("Phase 4 benchmark", "nezha_setup/outputs/phase4_benchmark/results/phase4_benchmark_report.json"))
    rows.extend(rows_from_summary_json(
        "Phase 5 context rescue",
        "context_rescue",
        "nezha_setup/outputs/phase5_context_rescue/results/hybrid_results.json",
        "Architectural improvement; not a single-variable ablation because rescue behavior and LLM calls changed.",
    ))
    rows.extend(rows_from_summary_json(
        "Local-first fallback",
        "local_first_ollama_gemini",
        "nezha_setup/outputs/local_first_ollama_smoke/results/hybrid_results.json",
        "Operational feasibility smoke; not the main quality benchmark.",
    ))
    rows.extend(rows_from_summary_markdown(
        "Streaming replay",
        "streaming_hybrid",
        "nezha_setup/outputs/phase3_streaming/results/streaming_hybrid_summary.md",
        "Sequential replay smoke; do not compare directly with Phase 4/5 due to different windows/backend.",
    ))
    rows.extend(rows_from_summary_markdown(
        "Real LLM cost/risk",
        "gemini25_flash_lite_500w_budget_manual_review_cache_replay",
        "nezha_setup/outputs/real_llm_stratified/results/gemini25_flash_lite_500w_budget_manual_review_cache_replay_summary.md",
        "Cache replay using existing Gemini decisions; no new external API call.",
    ))
    return rows


def rows_from_variant_json(phase: str, rel_path: str) -> list[dict[str, str]]:
    payload = load_json(rel_path)
    if not isinstance(payload, dict):
        return []
    rows = []
    for variant, summary in payload.items():
        if isinstance(summary, dict) and "summary" in summary and isinstance(summary["summary"], dict):
            summary = summary["summary"]
        if isinstance(summary, dict):
            rows.append(normalize_row(phase, str(variant), summary, note_for_variant(phase, str(variant))))
    return rows


def rows_from_summary_json(phase: str, variant: str, rel_path: str, notes: str) -> list[dict[str, str]]:
    payload = load_json(rel_path)
    if not isinstance(payload, dict):
        return []
    summary = payload.get("summary", payload)
    if not isinstance(summary, dict):
        return []
    return [normalize_row(phase, variant, summary, notes)]


def rows_from_summary_markdown(phase: str, variant: str, rel_path: str, notes: str) -> list[dict[str, str]]:
    summary = parse_summary_markdown(rel_path)
    return [normalize_row(phase, variant, summary, notes)] if summary else []


def normalize_row(phase: str, variant: str, summary: dict[str, Any], notes: str = "") -> dict[str, str]:
    row = {column: "" for column in CONSOLIDATED_COLUMNS}
    row["experiment_phase"] = phase
    row["variant"] = variant
    row["windows"] = s(summary.get("evaluated_windows", summary.get("windows")))
    row["candidates"] = s(summary.get("candidate_alerts", summary.get("candidates")))
    row["precision"] = s(summary.get("precision"))
    row["recall"] = s(summary.get("recall"))
    row["f1"] = s(summary.get("f1"))
    row["fpr"] = s(summary.get("false_positive_rate", summary.get("fpr")))
    row["tp"] = s(summary.get("tp"))
    row["fp"] = s(summary.get("fp"))
    row["fn"] = s(summary.get("fn"))
    row["llm_calls"] = s(summary.get("llm_calls"))
    row["api_fallback_calls"] = s(summary.get("api_fallback_calls"))
    row["context_coverage"] = s(summary.get("context_coverage_rate"))
    row["avg_context"] = s(summary.get("avg_retrieved_context_count"))
    row["retrieval_ms"] = s(summary.get("avg_retrieval_latency_ms"))
    row["avg_llm_ms"] = s(summary.get("avg_llm_latency_ms"))
    row["notes"] = notes
    return row


def write_inventory() -> None:
    lines = [
        "# Output Inventory",
        "",
        "This inventory checks existing evidence files without rerunning the experiment pipeline.",
        "",
        "| file_path | exists | last_modified | role |",
        "|---|---:|---|---|",
    ]
    for rel_path, role in INVENTORY:
        path = ROOT / rel_path
        exists = path.exists()
        modified = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds") if exists else ""
        lines.append(f"| `{rel_path}` | {str(exists).lower()} | {modified} | {role} |")
    write_text("output_inventory.md", "\n".join(lines) + "\n")


def write_consolidated_csv(rows: list[dict[str, str]]) -> None:
    path = REPORTS / "consolidated_experiment_metrics.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CONSOLIDATED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_evaluation_criteria_mapping() -> None:
    content = """# Evaluation Criteria Mapping

This document maps existing experiment outputs to thesis evaluation criteria. It is derived from existing files and does not rerun the full LLM pipeline.

## 1. Alert Quality

Alert quality measures whether the pipeline identifies true alerts while reducing false alarms. The main metrics are precision, recall, F1-score, false positive rate, TP, FP, and FN. These metrics are used in Phase 3, Phase 4, Phase 5, local-first smoke tests, and streaming replay.

## 2. Contextual Effectiveness

Contextual effectiveness evaluates whether retrieved log/trace context improves LLM decisions. The main metrics are context coverage, average retrieved context count, context token count, retrieval latency, and evidence hit@k when explicit evidence matching is available. In the current outputs, context coverage and average context are the strongest available proxies.

## 3. Operational Cost

Operational cost captures the extra runtime and monetary cost introduced by retrieval and LLM judging. The main metrics are LLM calls, actual API calls, cache hits, input/output tokens, retrieval latency, average LLM latency, and estimated cost. These metrics connect model quality improvements to practical deployment constraints.

## 4. Operational Risk and Reliability

Operational risk covers failure modes such as invalid JSON, API fallback, timeout, rate limit, exhausted LLM budget, hallucination risk, and unsupported decisions. In this repository, the most important reported metrics are JSON valid rate, fallback rate, API fallback calls, cache hit rate, retry/backoff metrics, and manual-review behavior when LLM budget is exhausted.

## 5. Real-time / Streaming Feasibility

Real-time feasibility asks whether the pipeline can process telemetry sequentially without future context leakage. Streaming replay, watermark behavior, end-to-end latency, and throughput-related latency metrics are used for this criterion. The current streaming result is a feasibility smoke test, not a direct quality benchmark against Phase 4/5.

## 6. Mapping from Experiments to Criteria

| Criterion Group | Research Question | Metrics | Used In |
|---|---|---|---|
| Alert Quality | Does the system correctly identify true alerts and reduce false alarms? | Precision, Recall, F1, FPR, TP, FP, FN | Phase 3, Phase 4, Phase 5 |
| Contextual Effectiveness | Does RAG/log/trace context improve decision quality? | Context coverage, avg context, retrieval latency, evidence hit@k if available | Phase 3, Phase 4, Phase 5 |
| Operational Cost | How expensive is the improvement? | LLM calls, API calls, token usage, retrieval latency, average LLM latency | Phase 4, Phase 5, Local-first |
| Operational Risk | What can fail during deployment? | fallback rate, JSON valid rate, timeout, 429/rate-limit, hallucination/unsupported decision risk | Local-first, scheduler/cache, real LLM tests |
| Real-time Feasibility | Can the system process data sequentially without future leakage? | streaming replay, watermark, E2E latency | Streaming replay |

## 7. Interpretation Guidelines for Thesis Writing

- Treat cost and risk as evaluation criteria, not only implementation notes.
- When a method improves F1 or recall, also report the additional LLM calls, retrieval latency, token usage, and fallback/manual-review behavior.
- Do not compare streaming replay directly against Phase 4/5 quality numbers because the window count and backend settings differ.
- Present Context Rescue as an architectural improvement, not as a single-variable ablation, because it changes candidate generation and increases LLM calls.
- Avoid claiming production readiness. The current evidence supports feasibility and trade-off analysis.
"""
    write_text("evaluation_criteria_mapping.md", content)


def write_tradeoff_analysis(rows: list[dict[str, str]]) -> None:
    evidence = {row["variant"]: row for row in rows}

    def metric_text(*variants: str) -> str:
        chunks = []
        for variant in variants:
            row = evidence.get(variant)
            if row:
                chunks.append(
                    f"{variant}: F1={row['f1']}, FPR={row['fpr']}, LLM calls={row['llm_calls']}"
                )
        return "; ".join(chunks)

    table = [
        (
            "detector_only",
            "Fast, cheap baseline with no LLM dependency.",
            "Higher false-positive risk and limited semantic validation.",
            "Alert Quality, Operational Cost",
            metric_text("detector_only"),
            "Use as the baseline for measuring whether RAG/LLM reduces false alarms.",
        ),
        (
            "llm_without_rag",
            "Tests whether an LLM can validate alerts from metrics alone.",
            "May suppress false positives but loses true positives without operational context.",
            "Alert Quality, Contextual Effectiveness",
            metric_text("llm_without_rag"),
            "Shows that LLM judging needs retrieved context; metric-only prompts are not reliable in these slices.",
        ),
        (
            "hybrid_rag",
            "Combines detector candidates with retrieved log/trace context.",
            "Adds retrieval and LLM latency/cost.",
            "Alert Quality, Contextual Effectiveness, Operational Cost",
            metric_text("hybrid"),
            "Improves quality over detector-only by giving the judge operational evidence.",
        ),
        (
            "hybrid_bm25_top6",
            "Uses local hybrid BM25/hash retrieval with top_k=6.",
            "Slight retrieval latency cost; context coverage remains limited.",
            "Contextual Effectiveness, Operational Cost",
            metric_text("hybrid_bm25_top6"),
            "Best practical local RAG baseline in Phase 4; improves F1/FPR over detector-only.",
        ),
        (
            "hybrid_bm25_top10",
            "Retrieves more context per candidate.",
            "More context tokens without classification improvement in this slice.",
            "Contextual Effectiveness, Operational Cost",
            metric_text("hybrid_bm25_top10"),
            "Increasing top-k from 6 to 10 raises average context but does not improve F1 here.",
        ),
        (
            "context_rescue",
            "Promotes candidates using log/trace signals that metric-only detection may miss.",
            "Increases candidate alerts and LLM calls.",
            "Alert Quality, Operational Cost, Operational Risk",
            metric_text("context_rescue"),
            "Improves recall and F1 substantially, trading higher inference cost for lower false-negative risk.",
        ),
        (
            "local_first",
            "Uses local Ollama first and API fallback for uncertain/error cases.",
            "Higher local latency; still needs API fallback for quality.",
            "Operational Cost, Operational Risk, Alert Quality",
            metric_text("local_first_ollama_gemini"),
            "Feasible workflow for reducing API dependence, but not yet a full replacement for external LLMs.",
        ),
        (
            "scheduler_cache",
            "Controls external calls with cache, retry/cooldown, and budget-aware handling.",
            "May defer or manual-review alerts when budget is exhausted.",
            "Operational Cost, Operational Risk",
            metric_text("gemini25_flash_lite_500w_budget_manual_review_cache_replay"),
            "Makes quota/cost visible and prevents unconfirmed budget-exhausted candidates from being routed as true alerts.",
        ),
        (
            "streaming_replay",
            "Processes windows sequentially and prevents future context leakage.",
            "Smoke setting is not directly comparable with batch benchmarks.",
            "Real-time Feasibility, Operational Risk",
            metric_text("streaming_hybrid"),
            "Supports real-time feasibility claims, but not production readiness.",
        ),
    ]

    lines = [
        "# Trade-off Analysis Table",
        "",
        "This table connects each system component to the evaluation criteria used in the thesis.",
        "",
        "| Component | Main Benefit | Main Cost / Risk | Evaluation Criteria | Metrics to Report | Thesis Interpretation |",
        "|---|---|---|---|---|---|",
    ]
    for row in table:
        lines.append("| " + " | ".join(row) + " |")
    write_text("tradeoff_analysis_table.md", "\n".join(lines) + "\n")


def write_experiment_summary(rows: list[dict[str, str]]) -> None:
    phase3 = [row for row in rows if row["experiment_phase"] == "Phase 3 ablation"]
    cloud = [row for row in rows if row["experiment_phase"] == "Microsoft cloud-monitoring"]
    phase4 = [row for row in rows if row["experiment_phase"] == "Phase 4 benchmark"]
    phase5 = [row for row in rows if row["experiment_phase"] == "Phase 5 context rescue"]
    local = [row for row in rows if row["experiment_phase"] == "Local-first fallback"]
    streaming = [row for row in rows if row["experiment_phase"] == "Streaming replay"]
    cost = [row for row in rows if row["experiment_phase"] == "Real LLM cost/risk"]

    content = [
        "# Consolidated Experiment Summary Without Rerun",
        "",
        "This summary is derived from existing experiment outputs and does not rerun the full LLM pipeline.",
        "",
        "## 1. Scope",
        "",
        "The summary reorganizes existing outputs into thesis-ready evidence for alert quality, contextual effectiveness, operational cost, operational risk, and real-time feasibility. No full benchmark was rerun, no external LLM API call was made, and no raw dataset was modified.",
        "",
        "## 2. Dataset Roles",
        "",
        "- Microsoft cloud-monitoring-dataset: useful for metric-only detector baselines because it provides labeled metric anomalies but lacks operational log/trace context.",
        "- IntelligentDDS/Nezha: the main dataset for the hybrid experiment because it contains metrics, logs, traces, and fault injection labels.",
        "",
        "## 3. Microsoft Cloud-monitoring Metric-only Baseline",
        "",
        rows_to_markdown(cloud),
        "",
        "The Microsoft dataset is used before the Nezha hybrid experiments as a metric-only feasibility benchmark. It quantifies detector recall and false-positive burden on labeled metric time series. Because it lacks real operational logs/traces and produces too many candidates for API judging, only detector-only results are used for this dataset.",
        "",
        "## 4. Phase 3 Ablation",
        "",
        rows_to_markdown(phase3),
        "",
        "Phase 3 shows that `llm_without_rag` reduces false positives but loses all true positives in this slice. The hybrid variant keeps detector recall while improving precision and FPR, supporting the claim that LLM-as-a-Judge requires operational context.",
        "",
        "## 5. Phase 4 Benchmark",
        "",
        rows_to_markdown(phase4),
        "",
        "Phase 4 shows that local hybrid RAG variants improve precision, F1, and FPR over detector-only. Increasing top-k from 6 to 10 increases average retrieved context but does not improve classification metrics in this slice.",
        "",
        "## 6. Phase 5 Context Rescue",
        "",
        rows_to_markdown(phase5),
        "",
        "Context Rescue improves recall and F1 by promoting candidates from log/trace signals. It also increases candidate alerts and LLM calls, so it should be presented as an architectural improvement with a cost trade-off, not as a one-variable ablation.",
        "",
        "## 7. Local-first and Fallback",
        "",
        rows_to_markdown(local),
        "",
        "The local-first smoke test demonstrates workflow feasibility. It preserves recall in this small slice but increases average LLM latency and still requires API fallback, so it should be interpreted as operational feasibility evidence.",
        "",
        "## 8. Streaming Replay",
        "",
        rows_to_markdown(streaming),
        "",
        "Streaming replay mainly verifies sequential processing and avoidance of future context leakage. It should not be compared directly with Phase 4/5 because the number of windows and backend settings differ.",
        "",
        "## 9. Cost and Risk Summary",
        "",
        rows_to_markdown(cost),
        "",
        "The 500-window cache replay shows that cache and budget-aware policy can reorganize existing LLM decisions without new API calls. It also shows why budget-exhausted candidates should be manual-reviewed instead of routed as confirmed alerts.",
        "",
        "## 10. Final Interpretation",
        "",
        "The strongest current result is that context improves alert validation, especially when Context Rescue uses log/trace evidence to reduce false-negative risk. The main trade-off is higher LLM usage and operational complexity. This positions the system as a cost-aware multi-telemetry AIOps pipeline for alert validation.",
        "",
        "## 11. Limitations",
        "",
        "- Results are based on existing slices and should not be overclaimed as production-ready.",
        "- Some comparisons are not strict ablations because candidate generation, context retrieval, and LLM budget can change together.",
        "- Real LLM behavior can be non-deterministic and subject to rate limits.",
        "- Streaming replay is a feasibility smoke test, not a full real-time deployment benchmark.",
    ]
    write_text("experiment_summary_no_rerun.md", "\n".join(content) + "\n")


def write_thesis_insert_sections(rows: list[dict[str, str]]) -> None:
    content = """# Thesis Insert Sections

## Mục tiêu đánh giá thực nghiệm

Mục tiêu của phần thực nghiệm là đánh giá tính khả thi của một pipeline AIOps lai cho thẩm định cảnh báo bất thường trong môi trường cloud/server. Pipeline sử dụng phát hiện bất thường trên metric để tạo cảnh báo ứng viên, truy xuất ngữ cảnh log/trace bằng RAG, và dùng LLM-as-a-Judge để hỗ trợ quyết định cảnh báo. Trọng tâm không phải là chứng minh hệ thống đã production-ready, mà là phân tích xu hướng chất lượng cảnh báo, hiệu quả ngữ cảnh, chi phí vận hành, rủi ro khi triển khai và khả năng xử lý theo thời gian.

## Tiêu chí đánh giá sự đánh đổi vận hành

Chi phí và rủi ro được xem là tiêu chí đánh giá vì trong bài toán giám sát thời gian thực, một cải thiện về precision hoặc recall chỉ có ý nghĩa nếu hệ thống vẫn kiểm soát được số lần gọi LLM, độ trễ, token, lỗi JSON, fallback và giới hạn quota/API. Do đó, thực nghiệm không chỉ báo cáo precision, recall, F1 và FPR, mà còn báo cáo LLM calls, API calls, context coverage, retrieval latency, average LLM latency, cache hit rate và các trạng thái manual review/fallback.

| Nhóm tiêu chí | Câu hỏi đánh giá | Chỉ số sử dụng |
|---|---|---|
| Chất lượng cảnh báo | Hệ thống có xác định đúng true alert và giảm false alarm không? | Precision, Recall, F1, FPR, TP, FP, FN |
| Hiệu quả ngữ cảnh | Log/trace context có giúp LLM ra quyết định tốt hơn không? | Context coverage, avg context, retrieval latency |
| Chi phí vận hành | Cải thiện chất lượng tốn bao nhiêu tài nguyên? | LLM calls, API calls, token usage, LLM latency |
| Rủi ro vận hành | Khi API lỗi, output lỗi hoặc quota cạn thì hệ thống phản ứng thế nào? | JSON valid rate, fallback rate, retry/backoff, manual review |
| Khả năng thời gian thực | Pipeline có thể xử lý tuần tự mà không dùng context tương lai không? | Streaming replay, watermark, E2E latency |

## Diễn giải kết quả Phase 4

Trong lát cắt Phase 4 gồm 300 windows, các biến thể hybrid RAG cho thấy xu hướng cải thiện so với detector-only. Detector-only đạt F1 = 0.2143 và FPR = 0.1197, trong khi các biến thể hybrid đạt F1 = 0.3429 và FPR = 0.0458. Điều này cho thấy ngữ cảnh log/trace có vai trò hỗ trợ LLM-as-a-Judge trong việc giảm false positive. Tuy nhiên, khi tăng top-k từ 6 lên 10, số context trung bình tăng nhưng classification metrics không thay đổi trong lát cắt thực nghiệm này. Vì vậy, bottleneck không chỉ nằm ở số lượng context được truy xuất, mà còn nằm ở khả năng tạo candidate của detector metric-only.

## Diễn giải kết quả Context Rescue

Context Rescue là cải tiến kiến trúc, không phải ablation một biến duy nhất. Kết quả Phase 5 trên 300 windows cho thấy recall tăng từ 0.3750 lên 1.0000 và F1 tăng từ 0.3429 lên 0.7805 so với cấu hình hybrid BM25 top-6 ở Phase 4. Cơ chế này giúp giảm rủi ro bỏ sót sự cố bằng cách promote candidate từ tín hiệu log/trace khi metric detector chưa đủ nhạy. Đổi lại, số candidate alerts tăng từ 40 lên 55 và số LLM calls tăng từ 30 lên 55. Do đó, lợi ích chính của Context Rescue là giảm false-negative risk, còn chi phí chính là tăng inference cost và khối lượng thẩm định.

## Diễn giải kết quả Local-first

Local-first Ollama + Gemini fallback là một kiểm thử khả thi vận hành, không phải benchmark chất lượng chính. Trong smoke test 45 windows, local-first giữ recall = 1.0000 và đạt F1 = 0.7692, gần với Gemini-only smoke F1 = 0.8000. Tuy nhiên, average LLM latency tăng đáng kể và vẫn có 4 API fallback calls trên 6 LLM calls. Kết quả này cho thấy local model có thể đóng vai trò tầng xử lý trước để giảm phụ thuộc API trong một số trường hợp, nhưng trong cấu hình hiện tại chưa nên xem là phương án hoàn toàn thay thế API.

## Diễn giải kết quả Streaming Replay

Streaming replay đạt F1 = 0.4167 trên 50 windows với backend local_hashing. Kết quả này chủ yếu dùng để đánh giá khả năng xử lý tuần tự và tránh sử dụng ngữ cảnh từ tương lai, không nên so sánh trực tiếp với Phase 4 hoặc Phase 5 vì số lượng windows và cấu hình backend khác nhau. Ý nghĩa chính của streaming replay là chứng minh pipeline có thể được đặt trong bối cảnh real-time feasibility, nhưng chưa phải kiểm chứng production streaming đầy đủ.

## Tổng hợp trade-off của kiến trúc đề xuất

Kiến trúc đề xuất tạo ra một đánh đổi có thể đo lường giữa chất lượng cảnh báo, chi phí và rủi ro vận hành. Detector-only nhanh và rẻ nhưng dễ tạo false positive hoặc bỏ sót fault có dấu hiệu rõ hơn trong log/trace. Hybrid RAG cải thiện F1 và FPR nhờ bổ sung ngữ cảnh, nhưng tăng retrieval/LLM cost. Context Rescue cải thiện mạnh recall và giảm rủi ro bỏ sót sự cố, nhưng làm tăng số candidate và LLM calls. Local-first, scheduler và cache giúp kiểm soát chi phí/API quota, nhưng có thể tăng latency hoặc đưa thêm alert vào manual review. Vì vậy, đóng góp chính của thực nghiệm là cho thấy một hướng thiết kế AIOps cost-aware: dùng metric detector để giới hạn candidate, dùng RAG để bổ sung bằng chứng vận hành, dùng LLM-as-a-Judge để thẩm định, và dùng scheduler/cache/manual review để kiểm soát rủi ro khi triển khai.
"""
    write_text("thesis_insert_sections.md", content)


def rows_to_markdown(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "_No available existing output file was parsed for this section._"
    columns = ["variant", "windows", "candidates", "precision", "recall", "f1", "fpr", "llm_calls", "context_coverage", "avg_context", "retrieval_ms", "avg_llm_ms", "notes"]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row.get(column, "") for column in columns) + " |")
    return "\n".join(lines)


def write_text(name: str, content: str) -> None:
    (REPORTS / name).write_text(content, encoding="utf-8")


def load_json(rel_path: str) -> Any:
    path = ROOT / rel_path
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def parse_summary_markdown(rel_path: str) -> dict[str, Any]:
    path = ROOT / rel_path
    if not path.exists():
        return {}
    summary: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\|\s*`?([^`|]+)`?\s*\|\s*(.*?)\s*\|$", line)
        if not match:
            continue
        key = match.group(1).strip()
        value = match.group(2).strip()
        if key.lower() == "metric" or value.lower() == "value":
            continue
        summary[key] = parse_scalar(value)
    return summary


def parse_scalar(value: str) -> Any:
    cleaned = value.strip().strip("`")
    if cleaned in {"", "[]"}:
        return cleaned
    try:
        if any(ch in cleaned for ch in [".", "e", "E"]):
            return float(cleaned)
        return int(cleaned)
    except ValueError:
        return cleaned


def note_for_variant(phase: str, variant: str) -> str:
    if phase == "Phase 3 ablation" and variant == "llm_without_rag":
        return "Reduces false positives but loses true positives without context."
    if phase == "Phase 4 benchmark" and variant == "hybrid_bm25_top10":
        return "More context than top6 but no classification gain in this slice."
    if variant == "detector_only":
        return "Baseline without LLM/RAG cost."
    if "hybrid" in variant:
        return "Hybrid RAG variant; compare quality with retrieval/context cost."
    return ""


def s(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


if __name__ == "__main__":
    main()
