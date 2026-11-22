# Danh sách hình đã sinh (PNG) và caption

> Soạn 2026-11-18, vẽ lại cùng ngày theo yêu cầu: **chữ trên biểu đồ bằng tiếng Anh** (dấu chấm thập phân), phong
> cách mới không theo bài báo. Mọi hình là PNG 300 dpi để chèn vào Word; không xuất PDF. Biểu đồ số liệu sinh bằng
> `py scripts/thesis_figures.py` (vẽ lại một hình: `--only h5.9`). Script đọc thẳng `eval/results/` và `data/`, không
> nhập số tay. Màu: bảng màu tham chiếu của skill dataviz, đã kiểm bằng `validate_palette.js` (BM25 xanh dương, C1 cam,
> CTAV xanh ngọc, giữ nguyên ở mọi hình; LLM không RAG và chỉ detector là xám đậm kèm nhãn trực tiếp).
> Mã hình theo `outline-bao-cao-gd2.md` mục 5. Caption bên dưới bằng tiếng Việt để dán vào luận văn, đặt **dưới** hình
> (style guide §5.1); khi caption nhắc chữ trên hình thì dùng đúng chữ tiếng Anh đó.
>
> Sau đợt cắt hình 2026-11-18, phần chính giữ **23 hình** (outline mục 5). Các biểu đồ H5.2, H5.14, H5.15 đã bỏ
> (số liệu nằm ở Bảng B5.3, B5.31); H5.5, H5.6 chuyển Phụ lục D.

## Chương 1 (sơ đồ, xuất từ TikZ sang PNG)

| Mã | File | Caption | Nguồn |
|---|---|---|---|
| H1.1 | `ch1/h1.1-tong-quan-he-thong.png` | Tổng quan hệ thống: telemetry đi qua bộ phát hiện bất thường, CTAV (truy xuất bằng chứng, judge LLM, chính sách quyết định), tác tử RCA và dashboard. Dòng chữ nghiêng dưới mỗi khối là câu hỏi người vận hành cần trả lời ở khâu đó. | `thesis/figures/ch1/fig-tong-quan.pdf` |
| H1.2 | `ch1/h1.2-danh-doi-ngu-canh-topology.png` | Đánh đổi khi mở rộng ngữ cảnh theo đồ thị: (a) truy xuất cục bộ quanh service phát cảnh báo s₀; (b) mở rộng 2 hop. Mở rộng giúp thấy chuỗi lan truyền ở cửa sổ có sự cố, nhưng đưa thêm bằng chứng nền vô hại vào cửa sổ bình thường. | `thesis/figures/ch1/fig-danh-doi.pdf` |

Hai sơ đồ này thuộc loại phải ghi nguồn AI hỗ trợ dưới caption nếu được vẽ có AI hỗ trợ (style guide §5.3). Bạn xác nhận
trước khi chèn.

## Chương 2

| Mã | File | Caption | Nguồn số liệu |
|---|---|---|---|
| H2.4 | `ch2/h2.4-service-graph.png` | Đồ thị phụ thuộc service dựng từ trace của Nezha: (a) OnlineBoutique, 10 service, 13 cạnh; (b) TrainTicket, 46 service, 55 cạnh. Màu cho thấy phạm vi mở rộng 1 hop và 2 hop từ một service phát cảnh báo s₀ (ví dụ `paymentservice` và `ts-travel-service`). 18 service TrainTicket không xuất hiện trong cạnh nào của trace nên không được vẽ. | `data/graph/service_graph.json` |
| H2.7 | `ch2/h2.7-confirmation-bias.png` | Thiên lệch xác nhận của judge: cùng một candidate trên cửa sổ bình thường, (a) bằng chứng cục bộ xa thời điểm cảnh báo dẫn tới kết luận `false_positive`; (b) bằng chứng sát thời điểm cảnh báo hoặc từ service lân cận chứa từ khoá lỗi nhưng là hoạt động nền dẫn tới `true_alert` với độ tin cậy cao. *Nguồn: tác giả vẽ, có hỗ trợ của công cụ AI [n].* | `scripts/thesis_diagrams.py` |

Ghi chú: ở cụm `preserve` / `preserve-other` của Train Ticket, nhãn còn chồng nhẹ vì đây là hai nút có bậc cao nhất.
Hai sơ đồ Chương 1 vẫn là chữ tiếng Việt (sơ đồ, không phải biểu đồ số liệu).

## Chương 4 (sơ đồ, `py scripts/thesis_diagrams.py`)

| Mã | File | Caption | Nguồn nội dung |
|---|---|---|---|
| H4.1 | `ch4/h4.1-architecture.png` | Kiến trúc tổng thể ở cấu hình chốt, gồm bốn khâu: phát hiện bất thường, CTAV, tác tử RCA và platform. Telemetry Nezha được phát lại theo cửa sổ 60 s; đồ thị phụ thuộc service cấp ngữ cảnh topology cho truy xuất bằng chứng (C1) và cho việc gom cảnh báo. Chỉ cảnh báo TRUE_ALERT đi tiếp sang tác tử RCA; mọi phán quyết cùng bằng chứng được lưu vào ClickHouse để dashboard đọc lại. Khung nét đứt (C5) chỉ dùng cho ablation. *Nguồn: tác giả vẽ, có hỗ trợ của công cụ AI [n].* | `01-architecture-design.md` §3; style guide §1.4 (vai trò C1–C5) |
| H4.4 | `ch4/h4.4-ctav-design-vs-final.png` | So sánh kiến trúc CTAV giữa thiết kế ban đầu (a) gồm hai tầng định tuyến thích nghi C4 cùng chính sách C2 và C3, và cấu hình chốt (b) chỉ giữ C1, ngưỡng $\theta_{\text{local}} = 0{,}80$ và neo bằng chứng C3 sau kiểm định loại trừ trên tập `val`. Các khối nét đứt (C2, C4) đã bị loại nhưng vẫn giữ mã nguồn cho phân tích loại trừ H3. *Nguồn: tác giả vẽ, có hỗ trợ của công cụ AI [n].* | `eval/configs/ctav_final.yaml`; `services/judge/{policy,routing}.py` |
| H4.5 | `ch4/h4.5-c1-2hop-fusion.png` | Cơ chế truy xuất bằng chứng nhận biết topology C1: (1) xác định lân cận vô hướng trong bán kính $d_G \le 2$ quanh service phát cảnh báo $s_0$; (2) hợp nhất và khử trùng lặp ứng viên từ BM25 cục bộ (`bm25_k = 60`) và mở rộng đồ thị (tối đa 20 sự kiện mỗi service gần $t_0$ nhất trong biên $\pm 8$ phút); (3) xếp hạng bằng Fusion Score ($\alpha = 0{,}35$, $\beta = 0{,}25$, $\gamma = 0{,}40$, $\tau_F = 300\,\text{s}$) và chọn top-6 trong ngân sách 4.000 token. *Nguồn: tác giả vẽ, có hỗ trợ của công cụ AI [n].* | `services/retrieval/hybrid_bm25_graph.py`; `eval/configs/h0_val_c1_k0.yaml` |
| H4.6 | `ch4/h4.6-decision-policy.png` | Sơ đồ luồng chính sách quyết định CTAV hoạt động như hàm thuần trên phán quyết thô đã lưu cache: kiểm tra nhãn và bằng chứng trích dẫn, đối chiếu ngưỡng tin cậy $\theta_{\text{local}} = 0{,}80$ (nhánh C2 nét đứt đã loại), cuối cùng kiểm tra điều kiện neo bằng chứng C3 trên sự kiện bất thường của chính $s_0$ (log mức `ERROR`/`WARN` hoặc trace span vượt phân vị p90 nền trên `dev`). *Nguồn: tác giả vẽ, có hỗ trợ của công cụ AI [n].* | `services/judge/policy.py`; `services/judge/span_baseline.py` |
| H4.10 | `ch4/h4.10-rca-agent.png` | Quy trình ba bước của tác tử RCA trên các cảnh báo `TRUE_ALERT` từ CTAV: (1) gom nhóm theo cửa sổ thời gian ($T_{\text{group}} = 180\,\text{s}$) và thành phần liên thông đồ thị vô hướng thành `Incident`; (2) bỏ phiếu lan truyền ngược 1 bước theo chiều gọi trên đồ thị có hướng (`backward_one_hop`) để xếp hạng service gốc; (3) sinh báo cáo chẩn đoán JSON bằng một lần gọi LLM qua cache và kiểm duyệt 5 quy tắc trước khi ghi `diagnostic_reports` hoặc `diagnostic_rejected`. *Nguồn: tác giả vẽ, có hỗ trợ của công cụ AI [n].* | `services/rca_agent/{grouping,propagation,summarizer,pipeline}.py`; `eval/configs/rca_final.yaml` |

## Chương 5

| Mã | File | Caption | Nguồn số liệu |
|---|---|---|---|
| H5.1 | `ch5/h5.1-split-protocol.png` | Giao thức chia split chống rò rỉ trên Nezha: giữ nguyên khối 7 cửa sổ mỗi lần tiêm lỗi, loại vùng đệm 600 s và khóa cứng ba tập `dev`, `val`, `test`. *Nguồn: tác giả vẽ, có hỗ trợ của công cụ AI.* | `scripts/thesis_diagrams.py`; QĐ-004 |
| H5.3 | `ch5/h5.3-three-gates.png` | Ba cổng kiểm chứng thực nghiệm (G-port, G-paper, G-test) và quy trình năm bước khép kín của G-test sau commit `be2b985`. *Nguồn: tác giả vẽ, có hỗ trợ của công cụ AI.* | `scripts/thesis_diagrams.py`; QĐ-034 |
| H5.4 | `ch5/h5.4-h1-time-proximity.png` | H1 trên `val`: tỉ lệ judge trả TRUE_ALERT theo tỉ lệ bằng chứng trace nằm sát thời điểm cảnh báo (0%, 33%, 67%, 100%), trên mẫu cố định gồm 56 cửa sổ có sự cố và 563 cửa sổ bình thường. Thanh lỗi: CI 95% bootstrap. Độ dốc dương ở cả hai nhãn: judge xác nhận nhiều hơn khi bằng chứng sát thời điểm, kể cả ở cửa sổ bình thường. | `h1_val_analysis_v2` |
| H5.5 (Phụ lục D) | `ch5/h5.5-theta-sweep-val.png` | Recall (a) và FPR (b) của CTAV theo ngưỡng tin cậy θ_topo trên `val` (cửa sổ có telemetry: 7.636 cửa sổ, 209 có sự cố), với C1 chấm mọi candidate và C3 dùng ngưỡng nền p90 của `dev`. Đường có dạng bậc vì confidence của judge rời rạc (0,80 / 0,85 / 0,90). Thanh lỗi: CI 95% bootstrap. | `m6_ctav_select_val_v2` |
| H5.6 (Phụ lục D) | `ch5/h5.6-rescue-tau-val.png` | Đường τ của C5 (Rescue Score) trên `val` tại η = (0; 0,4; 0,6): (a) recall, (b) FPR, (c) số lần gọi LLM tăng thêm. Đường chấm là CTAV khi tắt C5; vạch đứt là τ = 0,8 đã chọn. Recall phẳng từ τ = 0,3 đến 0,8, còn hạ τ chỉ làm tăng FPR và số lần gọi. | `m7_rescue_val_v1/points.csv` |
| H5.8 | `ch5/h5.8-candidate-rate-by-split.png` | Tỉ lệ cửa sổ thành candidate (điểm bất thường ≥ 0,85) trên `dev`, `val`, `test` (mọi cửa sổ: 19.316 / 28.898 / 46.849): (a) theo hệ thống, (b) theo nhãn cửa sổ. Tỉ lệ tăng dần từ `dev` sang `test` ở cả hai hệ và cả hai nhãn. | `m8_detector_shift_test_v1` |
| H5.9 | `ch5/h5.9-recall-fpr-operating-points.png` | Điểm vận hành Recall–FPR của năm phương pháp trên cửa sổ có telemetry: `val` (điểm rỗng, 7.636 cửa sổ) và `test` (điểm đặc kèm CI 95%, 11.985 cửa sổ). Trục FPR thang log. Nhãn số là TP / FP trên `test`. | `ctav_final_val_v1`, `ctav_final_test_v1` (`baselines.methods`) |
| H5.10 | `ch5/h5.10-paired-differences-ci.png` | Hiệu ghép cặp ΔRecall (a), ΔFPR (b), ΔF1 (c) với CI 95% bootstrap (1.000 lần lấy mẫu lại) trên cửa sổ có telemetry. Điểm đặc: `test`; điểm rỗng: `val`. Dòng CTAV − C1 chỉ có `test`. Vạch cam là 0: CI cắt vạch này thì chưa đủ bằng chứng khẳng định khác biệt. | `ctav_final_test_v1`, `ctav_final_val_v1` (`baselines.pairs`); `h0_test_compare_c1ref_v1` |
| H5.11 | `ch5/h5.11-ctav-funnel-test.png` | Phễu quyết định của CTAV trên 11.985 cửa sổ có telemetry của `test`, cho thấy tầng C3 cắt 94,8% FP nhưng đồng thời hạ 82 TP (trong đó 67 TP thuộc 32 service thiếu ngưỡng `dev`). *Nguồn: tác giả vẽ, có hỗ trợ của công cụ AI.* | `scripts/thesis_diagrams.py`; `ctav_final_test_v1` |
| H5.12 | `ch5/h5.12-recall-by-service-group.png` | Recall của C1 và CTAV theo nhóm service có / không có ngưỡng nền `dev` (Phát hiện 11): (a) `val`, (b) `test`. Số trên cột là TP / số cửa sổ có sự cố của nhóm. Ở nhóm không có ngưỡng nền, C3 hạ mọi TRUE_ALERT nên CTAV không bắt được sự cố nào. | `m8_finding11_val_v1`, `m8_finding11_test_v1` |
| H5.13 | `ch5/h5.13-f1-vs-budget.png` | F1 theo ngân sách lần gọi LLM, candidate xử lý theo thứ tự thời gian, trên cửa sổ có telemetry: (a) `val`, (b) `test`. "Đủ" là chấm mọi candidate. Vạch đứt là ngân sách 120 lần gọi của H4. | `ctav_final_val_v1`, `ctav_final_test_v1` (`budget_curve`) |

## Đã có từ trước (Chương 6, ảnh chụp)

Giữ bốn ảnh: `m10-timeline.png` (H6.2), `m10-alert-c3-downgrade.png` (H6.3, đề xuất), `m10-incident-cascade.png`
(H6.4), `m10-experiment-comparison.png` (H6.5). Caption nằm sẵn trong `ch6-demo-platform.md`. Nháp Ch6 đang dùng
thêm `m10-alert-topo-rescue.png` (Hình 6.3 của nháp): bỏ ảnh này khi đưa vào Word, hoặc đổi với ảnh C3 nếu bạn muốn
giữ ca cho thấy C1.

## Chưa vẽ (4 hình trong phần chính)

- Có khung Mermaid trong outline: H5.3 ba cổng kiểm chứng (gộp các bước G-test của H5.7).
- Vẽ mới: H5.1 chia split, H6.1 triển khai Docker Compose.
- Bằng script: H5.11 phễu quyết định của CTAV trên `test`.
- Phụ lục: ví dụ prompt và JSON (H4.9, Phụ lục B), cấu trúc repo và harness (H4.12, Phụ lục E).
