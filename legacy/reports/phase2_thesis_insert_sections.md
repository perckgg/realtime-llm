# Phase 2 Thesis Insert Sections

## 1. Mục tiêu và phạm vi

Phase 2 đánh giá một pipeline AIOps lai gồm metric anomaly detector, truy xuất ngữ cảnh log/trace và LLM-as-a-Judge. Mục tiêu là đo ảnh hưởng của topology-aware retrieval đến chất lượng bằng chứng và quyết định cảnh báo, đồng thời kiểm soát false positive, manual review, API calls, cache, độ trễ và chi phí.

Nghiên cứu không claim full root cause analysis vì không có nhãn root-cause service. Kết quả hiện tại cũng chỉ có giá trị trong phạm vi Nezha cho đến khi có external validation.

## 2. Thiết kế phương pháp

### 2.1 Service dependency graph

Service graph được dựng từ distributed traces. Mỗi cạnh lưu quan hệ gọi service, trace/span count, duration statistics, thời gian quan sát và operation samples. Graph Phase 2 có 56 services và 68 edges.

### 2.2 Candidate expansion và fusion

BM25 tạo lexical candidate pool. Topology expander bổ sung context từ service lân cận trong graph. Điểm cuối:

\[
Score_{final} = \alpha BM25_{norm} + \beta TimeSim + \gamma GraphSim
\]

Trong đó `GraphSim=0` khi service không reachable, và `Score_final` luôn được clamp về `[0,1]`.

### 2.3 LLM decision và manual review

LLM phải trả JSON theo schema cố định. Kết quả true alert thiếu evidence có thể chuyển sang manual review. Khi hết budget, hệ thống cũng dùng manual review thay vì xem candidate là confirmed alert.

## 3. Thiết kế thực nghiệm

Split chính `paper_500` gồm 500 windows: 100 true alerts và 400 normal windows trên 56 services. Hash:

```text
1745d09ec60c98b8520a6e38ed614f20e39009c3ac7173468f18658066a7cd9e
```

View A so sánh BM25 top-6 với topology top-6 trong điều kiện retrieval-fair. View B so sánh detector-only, LLM without RAG, BM25, topology và Context Rescue ở mức kiến trúc. Context Rescue luôn được gắn nhãn architecture-enhanced.

## 4. Kết quả View A

| Regime | Method | Precision | Recall | F1 | FPR | Context coverage | Cost USD |
|---|---|---:|---:|---:|---:|---:|---:|
| Budget 120 | BM25 top-6 | 1.0000 | 0.3400 | 0.5075 | 0.0000 | 0.1125 | 0.0214684 |
| Budget 120 | Topology top-6 | 0.5823 | 0.4600 | 0.5140 | 0.0825 | 0.2454 | 0.0401765 |
| Full budget | BM25 top-6 | 0.8923 | 0.5800 | 0.7030 | 0.0175 | 0.2249 | 0.0627953 |
| Full budget | Topology top-6 | 0.3507 | 0.7400 | 0.4759 | 0.3425 | 1.0000 | 0.1669426 |

Topology tăng recall và context availability, nhưng full-budget F1 giảm và FPR tăng mạnh. Bootstrap 95% CI của full-budget F1 delta là `[-0.3210, -0.1320]`; exact McNemar test có `p=2.61e-19` và ưu tiên BM25 về paired correctness tổng thể.

## 5. Kết quả theo fault type

Kết quả tích cực rõ nhất là `network_delay`: recall tăng từ `0.3750` lên `0.7000`. Tuy nhiên, topology route 137 false alerts trên normal windows, trong khi BM25 route 7. Vì vậy, topology giải quyết evidence availability nhưng tạo ra bài toán calibration ở tầng quyết định.

## 6. Kết quả View B

| Method | Precision | Recall | F1 | FPR |
|---|---:|---:|---:|---:|
| Detector-only | 0.2004 | 0.9800 | 0.3328 | 0.9775 |
| LLM without RAG | 0.5210 | 0.6200 | 0.5662 | 0.1425 |
| BM25 top-6 | 1.0000 | 0.3400 | 0.5075 | 0.0000 |
| Topology top-6 | 0.5823 | 0.4600 | 0.5140 | 0.0825 |
| Context Rescue | 1.0000 | 0.3400 | 0.5075 | 0.0000 |

LLM without RAG có F1 cao nhất trong View B budget-120. Context Rescue kiểm tra 11 detector-negative windows nhưng không promote window nào, nên không cải thiện so với BM25 trên split này.

## 7. Ablation và chi phí

Alpha/beta/gamma ablation là retrieval-only, không phải LLM decision ablation. Bảng ablation để trống precision/recall/F1 của tầng quyết định nhằm tránh tạo metric không được đo.

Cost table tách riêng logical calls, actual API calls, cache hits, JSON validity, latency và estimated cost. Cache replay không được dùng để claim first-pass API latency hoặc zero inference cost.

## 8. Quality gate

Step 9 pass toàn bộ 14 checks và 5 hard-stop conditions:

- baseline reproducibility;
- frozen-window consistency;
- audit schema;
- `Score_final` bounds;
- cache/API separation.

Do đó, paper result table hiện tại có thể finalize trong phạm vi claim Nezha-only.

## 9. Thảo luận

Topology-aware retrieval làm tăng khả năng tìm thấy bằng chứng liên quan về mặt kiến trúc và cải thiện recall của fault khó. Tuy nhiên, context gần trên service graph không đồng nghĩa với positive incident evidence. Cần thêm service consistency, negative-evidence checks hoặc calibrated routing threshold.

Đóng góp chính nên được mô tả như một systems trade-off giữa recall, evidence availability, FPR và cost, thay vì khẳng định topology là aggregate winner.

## 10. Hạn chế và hướng phát triển

1. Chưa có ba independent fresh-cache LLM repetitions.
2. Chưa có external validation ngoài Nezha.
3. Chưa có root-cause service labels.
4. Topology policy chưa được tune trên multi-service calibration split độc lập.
5. Related Work cần được hoàn thiện bằng citation đã kiểm chứng.

Roadmap cải thiện full paper được mô tả tại `FULL_PAPER_IMPROVEMENT_PLAN.md`.

## 11. Artifact dùng trong luận văn

```text
outputs/phase2/paper_tables/main_result_table.csv
outputs/phase2/paper_tables/fault_type_breakdown.csv
outputs/phase2/paper_tables/ablation_table.csv
outputs/phase2/paper_tables/cost_latency_table.csv
outputs/phase2/figures/
outputs/phase2/step7_view_b/step7_view_b_report.md
outputs/phase2/quality_gate/step9_quality_gate_report.md
```
