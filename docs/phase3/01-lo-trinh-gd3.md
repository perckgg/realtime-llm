# 01 — Lộ trình Giai đoạn 3 (Luận văn Thạc sĩ)

> **Bản nháp 2026-11-23.** Viết sau khi GĐ2 xong phần kỹ thuật (M0–M11), trước M12. Chưa có QĐ; mọi mốc, giả thuyết
> và ngân sách ở đây là **đề xuất**, cần người dùng và GVHD duyệt trước khi mở M13.
> Product (nhánh mở rộng riêng) nằm ở `02-mvp-product.md`; file này chỉ nói về phần nghiên cứu.

---

## 0. Những gì giữ nguyên từ GĐ2

- **Hướng đề tài:** CTAV (thẩm định cảnh báo có hiệu chỉnh theo topology) + tác tử RCA, judge LLM qua API.
- **Kỷ luật thực nghiệm:** chọn cấu hình chỉ trên `dev`/`val`; **đăng ký giả thuyết trước** khi chạm `test`; `test` chạy
  một lần; báo cáo đúng kết quả kể cả khi không đạt; mọi lệnh gọi LLM qua cache; không ghi đè `eval/results/`.
- **Kết quả GĐ2 đóng băng:** H0–H5, parity `26/26`, `38/38`, `114/114`, fingerprint `b0c54fa68ef65535`. GĐ3 không sửa
  các con số này.
- **Không tự train / fine-tune LLM; không bắt buộc model tự host** (lý do: `08-research-direction.md` §4, cộng phần
  cứng hạn chế). Model tự host vẫn là hướng mở rộng "khi có phần cứng".

**Ràng buộc quan trọng:** tập `test` của Nezha đã được mở ở M8. Mọi cải tiến mới chỉ được **phân tích thăm dò** trên
Nezha; kết luận chính thức của GĐ3 phải dựa trên **một tập `test` mới, niêm phong** (§2).

**Định vị giữa Luận văn và MVP thực tế (không đưa lên Production thật):**
- Trong phạm vi luận văn (cả GĐ2 và GĐ3), hệ thống **không triển khai lên môi trường Production thương mại thật** của doanh nghiệp bên ngoài (không tích hợp hệ thống trực on-call thật, không multi-tenant/SSO, không phụ thuộc lưu lượng khách hàng không kiểm soát được) để đảm bảo tính tái lập thực nghiệm 100% và có nhãn lỗi gốc (`ground-truth`) chính xác phục vụ kiểm định giả thuyết.
- Tuy nhiên, toàn bộ platform của luận văn (4 Protocol cắm-rút, pipeline CTAV + RCA có kiểm duyệt 5 quy tắc, ClickHouse/PostgreSQL, API và Dashboard 4 màn hình, cộng thêm Testbed trực tuyến + Stream mode ở GĐ3) được thiết kế để **thể hiện trực tiếp bản MVP (Minimum Viable Product) về mặt lõi kỹ thuật của hệ thống**. Chi tiết ánh xạ giữa MVP trong luận văn và nhánh sản phẩm thương mại riêng của tác giả xem tại `03-ke-hoach-ranh-gioi-luan-van-va-mvp.md`.

---

## 1. Câu hỏi nghiên cứu GĐ3

GĐ2 kết luận: nguyên lý neo bằng chứng (C3) đúng, nhưng **ngưỡng nền tĩnh lấy từ `dev`** không phủ `32/42` service của
`test` ⇒ H2 và H5 cùng không đạt. Đối chứng `C3-trượt` (F1 `0,120`) cho thấy hướng sửa trực tiếp. GĐ3 trả lời:

| # | Câu hỏi | Nối với hạn chế Ch8 |
|---|---|---|
| RQ6 | Ngưỡng nền **trực tuyến, không cần nhãn** có khôi phục recall của CTAV mà vẫn giữ FPR thấp không? | (1), (2) |
| RQ7 | Hiện tượng của H0 và cơ chế thiên lệch xác nhận có lặp lại trên **dữ liệu mới** và với **judge khác họ** không? | (6) |
| RQ8 | Một cổng tất định trước judge (**bỏ qua LLM khi không có bằng chứng bất thường**) giảm được bao nhiêu lần gọi và mất bao nhiêu recall? | (8), chi phí |
| RQ9 | Khi đầu vào cảnh báo đủ phủ, tác tử RCA có vượt baseline không (kiểm lại H5)? | (5) |
| — | Pipeline có chạy được ở **chế độ luồng** (stream mode) trên telemetry thật với độ trễ đo được không? | (8) |

---

## 2. Dữ liệu mới: testbed tự dựng

| Thành phần | Đề xuất | Ghi chú |
|---|---|---|
| Hệ microservice | **Online Boutique** (khoảng 11 service, kèm bộ sinh tải) | Cùng loại hệ Nezha dùng; nhẹ, chạy được trên minikube/kind ~4 CPU, 4–8 GB RAM. TrainTicket nặng hơn nhiều, chỉ thêm nếu có máy |
| Thu telemetry | OpenTelemetry Collector → Redpanda → ClickHouse | Profile `full` của `docker-compose.yml` đã chừa Redpanda |
| Tiêm lỗi | Chaos Mesh: CPU, memory, network delay, pod failure; thêm lỗi ứng dụng nếu được | Bám loại lỗi của Nezha để so được |
| Nhãn | Thời điểm + service + loại lỗi từ lịch tiêm (tự động) | Chạy lại `scripts/verify_labels.py` tương đương |
| Split | `dev`/`val`/`test` theo **lần tiêm lỗi**, vùng đệm 600 s, seed cố định — như GĐ2 | `test` niêm phong ngay khi tạo (hash ghi vào experiment-log) |
| Cỡ dữ liệu | Mục tiêu ≥ 60 lần tiêm/loại lỗi chính, ≥ 20 trên `test` mỗi loại | Chốt ở M14 sau khi đo năng lực máy |

**Giới hạn phải ghi trung thực:** dữ liệu mới vẫn từ cùng loại hệ thống demo, nên chỉ chứng minh khả năng **lặp lại**
trên dữ liệu chưa thấy, chưa phải tổng quát hoá sang hệ production.

---

## 3. Tổng quan mốc

Đánh số nối tiếp GĐ2 (M13…) để giữ liền mạch QĐ trong `experiment-log.md`. Tuần tính từ ngày mở GĐ3 (**T0, chờ xác
nhận**; giả định tạm 2027-02-22, sau tuần bảo vệ GĐ2 2027-02-08).

| Mốc | Tên | Loại | Tuần | Hạn mềm (nếu T0 = 2027-02-22) |
|---|---|---|---|---|
| M13 | Khởi động GĐ3 + trả nợ kỹ thuật | Cổng chặn (parity GĐ2) | T1–T2 | 2027-03-07 |
| M14 | Testbed + bộ dữ liệu mới | **Cổng chặn G-data** | T3–T5 | 2027-03-28 |
| M15 | Stream mode | **Cổng chặn G-stream** | T6–T7 | 2027-04-11 |
| M16 | C3 trực tuyến + cổng bỏ qua LLM (chọn trên `val`) | | T8–T10 | 2027-05-02 |
| M17 | Judge thứ hai (khác họ, qua API) trên `val` | | T10–T11 | 2027-05-09 |
| M18 | Đăng ký giả thuyết H6–H9 | Cổng chặn (commit riêng) | T11 | 2027-05-09 |
| M19 | Chạy `test` mới một lần | **Cổng chặn G-test2** | T12–T13 | 2027-05-23 |
| M20 | RCA trên cảnh báo mới (H9) + platform chế độ trực tiếp | | T14–T15 | 2027-06-06 |
| M21 | Đánh giá bằng người + phân tích ca sai | | T16 | 2027-06-13 |
| M22 | Đóng gói luận văn + bảo vệ | | T17–T20 | Theo lịch Khoa |

Quy trình đóng mốc giữ nguyên `04` §2: DoD có bằng chứng → báo cáo `docs/milestones/M<n>-*.md` 4 phần → người dùng
xem → cập nhật `docs/CURRENT-MILESTONE.md`.

---

## M13 — Khởi động GĐ3 + trả nợ kỹ thuật

| Việc | Output |
|---|---|
| Sửa bug tiềm ẩn `eval/harness/rescue.py:186-211` (chỉ dựng `entry` cho điểm feasible) | Test tái hiện điểm infeasible |
| Thắt `services/judge/registry.py` về đúng model đăng ký; bắt lỗi JSON ở `services/judge/backends.py:263` | Unit test |
| Gỡ hardcode tham số (`services/api/readers.py`, `eval/harness/h1.py:318`, default trong `__init__`) → đọc từ config | Config là nguồn sự thật duy nhất |
| Thêm subcommand `ablation` hoặc sửa AGENTS.md cho khớp; xoá dead code `cross_modal` | CLI khớp tài liệu |
| Đóng gói lõi (`packages/*`, `services/{retrieval,judge,rca_agent}`) thành package có phiên bản để product dùng lại | `pyproject.toml` + tag `core-v1.0.0` |
| Mở `docs/CURRENT-MILESTONE.md` cho GĐ3; ghi QĐ mở GĐ3 | |

**DoD M13:** `pytest` xanh; **chạy lại parity GĐ2 ra đúng `26/26`, `38/38`, `114/114` và fingerprint
`b0c54fa68ef65535`** (chứng minh trả nợ không đổi kết quả); `0` USD API.

---

## M14 — Testbed + bộ dữ liệu mới (cổng chặn G-data)

| Việc | Output |
|---|---|
| Dựng Online Boutique + OTel Collector + Chaos Mesh; script dựng lại một lệnh | `infra/testbed/` |
| Lịch tiêm lỗi có seed; sinh tải ổn định; ghi nhãn tự động | `data/testbed/<ver>/injections.json` |
| Thu dữ liệu, chuyển sang `TelemetryWindow` bằng `SourceAdapter` mới | `TestbedReplaySource` |
| Kiểm nhãn (trace `span_id`/`parent_span_id`, độ phủ telemetry quanh mỗi lần tiêm) | `docs/label-audit-testbed.md` |
| Chia split theo lần tiêm; niêm phong `test` (hash) | `data/splits/testbed_*.json` |
| Đếm candidate trên `dev`/`val` ⇒ ước chi phí M16–M19 | Dòng ngân sách trong `CURRENT-MILESTONE.md` |

**DoD M14 (G-data):** nhãn qua kiểm; split đã commit; `test` chưa bị đọc; có ước tính số candidate và chi phí.
**Không qua** ⇒ dừng, xem §5 (cắt sang dữ liệu nhỏ hơn hoặc thuê VM).

---

## M15 — Stream mode (cổng chặn G-stream)

| Việc | Output |
|---|---|
| Hiện thực `KafkaSource` (thay `NotImplementedError`) đọc Redpanda | `services/replayer/` hoặc module mới |
| Cắt cửa sổ trực tuyến theo watermark; đồ thị service cập nhật từ trace trực tiếp | |
| Đo độ trễ từng tầng (detect, retrieve, judge, RCA) và chi phí theo thời gian | `runtime.json` mở rộng |

**DoD M15 (G-stream):** phát lại cùng một đoạn dữ liệu testbed qua **replay** và qua **stream** cho **cùng tập candidate
và cùng verdict** (parity 100%, judge đọc cache); có số đo độ trễ p50/p95.

---

## M16 — C3 trực tuyến + cổng bỏ qua LLM

| Việc | Output |
|---|---|
| `C3-online`: ngưỡng nền theo cặp service–thao tác, cửa sổ trượt không nhãn, có khởi động lạnh (cold start) rõ ràng | `services/judge/policy.py` mở rộng |
| Neo bằng chứng chi tiết hơn (hạn chế (2) Ch8): xét mọi span của service trong cửa sổ, đòi ≥ k span hoặc mức vượt tương đối, xét `WARN` | Biến thể có cờ bật/tắt |
| Cổng bỏ qua LLM: không có span nào vượt ngưỡng nền ⇒ không gọi judge | Biến thể có cờ bật/tắt |
| Quét tham số trên `val` (Nezha `val` + testbed `val`); phân tích thăm dò trên Nezha `test` ghi rõ "không phải kiểm định" | Bảng chọn cấu hình |
| Chốt cấu hình | `eval/configs/ctav_online_final.yaml`, commit riêng |

**DoD M16:** cấu hình chốt có quy tắc chọn ghi trước khi xem số `val`; ablation một-thay-đổi-một-lần trên `val` có CI.

---

## M17 — Judge thứ hai (khác họ, qua API)

| Việc | Output |
|---|---|
| Thêm backend cho một nhà cung cấp khác trong registry; cache key đã chứa `provider`/`model` | Backend + test |
| Chạy BM25, C1, CTAV-online trên một tập con `val` cố định với judge 2 | So sánh judge 1 vs judge 2 |
| Thí nghiệm can thiệp H1 thu nhỏ với judge 2 (trace cục bộ sát t₀ có đẩy `TRUE_ALERT` không) | Bảng cơ chế |

**DoD M17:** có ước chi phí trước khi chạy; số trên `val` cho cả hai judge; quyết định judge 2 có vào `test` không.
**Cắt đầu tiên nếu trễ** (§5).

---

## M18 — Đăng ký giả thuyết H6–H9

Bản nháp (ngưỡng định lượng chốt ở mốc này, **trước** mọi lệnh chạm testbed `test`):

| Giả thuyết | Nội dung đề xuất |
|---|---|
| **H6** (chính) | Trên testbed `test`: CTAV-online có F1 > BM25 (ΔF1 > 0, CI không chứa 0) **và** FPR ≤ FPR(BM25) **và** Recall ≥ Recall(C1) − δ |
| **H7** | Hiện tượng H0 lặp lại trên testbed `test` (C1 − BM25: ΔRecall > 0, ΔFPR > 0); nếu M17 giữ judge 2 thì lặp lại với judge 2 |
| **H8** | Cổng bỏ qua LLM giảm ≥ X% số lần gọi với ΔRecall ≥ −δ so với CTAV-online không có cổng |
| **H9** | Trên sự cố của testbed `test`: Hit@1 tác tử RCA − baseline > 0 (kiểm lại H5 khi đầu vào đủ phủ) |

**DoD M18:** mục "Đăng ký giả thuyết GĐ3" cuối `experiment-log.md`, commit riêng, kèm danh sách config sẽ chạy.

---

## M19 — Cổng chặn G-test2

| Việc | Output |
|---|---|
| Chạy đúng các config đã đăng ký trên testbed `test`, một lần | `eval/results/*_tb_test_v1/` |
| Bootstrap CI + McNemar; bảng H6–H8; lặp đo phương sai trên tập con | Bảng chính GĐ3 |

**DoD M19:** kết luận H6–H8 viết ra **dù kết quả là gì**.

---

## M20 — RCA trên cảnh báo mới + platform trực tiếp

| Việc | Output |
|---|---|
| Chạy tác tử RCA (cấu hình GĐ2, không chỉnh) trên cảnh báo CTAV-online của testbed `test` ⇒ H9 | Hit@1/Hit@3, ARR |
| Dashboard nhận dữ liệu trực tiếp (SSE) bên cạnh chế độ replay; giữ chế độ offline cho bảo vệ | Màn hình Timeline cập nhật trực tiếp |
| (Tuỳ chọn, ideas.md) đồ thị RCA tương tác: playback lan truyền, so sánh trước/sau CTAV | Cắt nếu trễ |

**DoD M20:** H9 có kết luận; demo trực tiếp trên testbed chạy trọn kịch bản; chế độ offline vẫn `0` lần gọi API.

---

## M21 — Đánh giá bằng người + phân tích ca sai

| Việc | Output |
|---|---|
| Chấm mù chất lượng báo cáo chẩn đoán; **thêm người chấm thứ hai** để tính hệ số đồng thuận (hạn chế (7)) | `eval/manual/*_tb.csv` |
| Phân tích FP/FN còn lại của CTAV-online; so sánh với phân loại ca sai GĐ2 | Nguyên liệu chương thảo luận |

---

## M22 — Đóng gói và bảo vệ

- Chốt số liệu H6–H9, chi phí, độ trễ stream; mọi hình sinh từ script.
- Viết luận văn GĐ3 (kế thừa Ch1–Ch4 GĐ2; Ch5 thêm testbed; chương stream mode; thảo luận mới).
- README tái lập cho testbed; kiểm người lạ dựng lại được bảng kết quả.
- Tổng duyệt demo; slide; bảo vệ.

---

## 4. Ngân sách API (ước, chốt ở M14)

Tham chiếu GĐ2: M8 tốn **15,85 USD theo token** cho 21.094 lần gọi trên Nezha `test` (≈ 0,00075 USD/lần).
Testbed nhỏ hơn Nezha nên số candidate dự kiến ít hơn; con số thật chỉ có sau khi đếm ở M14.

| Mốc | Phần tốn API | Ước | Ngưỡng dừng |
|---|---|---|---|
| M13–M15 | Không (parity đọc cache) | 0 | 1 USD |
| M16 | Judge trên testbed `dev`/`val` | 4–8 USD | 10 USD |
| M17 | Judge 2 trên tập con `val` | 2–4 USD | 5 USD |
| M19 | Testbed `test` (+ judge 2 nếu giữ) | 6–12 USD | 15 USD |
| M20 | Summarizer RCA | < 1 USD | 2 USD |
| Dự phòng | Chạy lại do lỗi | 5 USD | — |

Quy tắc chi giữ nguyên GĐ2 (`CURRENT-MILESTONE.md` "Quy tắc"): ước trước khi chạy, chạy thử một điều kiện, dừng khi
chạm ngưỡng.

---

## 5. Ngưỡng cắt khi trễ

| Ưu tiên cắt | Hạng mục | Ảnh hưởng |
|---|---|---|
| 1 | Judge thứ hai (M17) | H7 chỉ còn vế dữ liệu mới; hạn chế (6) chỉ giải một nửa |
| 2 | Đồ thị RCA tương tác (M20) | Demo kém nổi bật, không mất bằng chứng |
| 3 | Cổng bỏ qua LLM (H8) | Mất RQ8; vẫn còn trục chính |
| 4 | Stream mode trực tiếp → chỉ chứng minh parity replay/stream trên dữ liệu đã ghi | Không có số độ trễ trực tiếp |
| 5 | Cỡ dữ liệu testbed giảm (ít lần tiêm hơn) | CI rộng hơn |

**Không bao giờ cắt:** trả nợ kỹ thuật có kiểm parity (M13); tập `test` mới niêm phong (M14); đăng ký trước (M18);
H6 (trục chính); báo cáo trung thực kể cả khi H6 không đạt; chế độ demo offline.

---

## 6. Vấn đề cần chốt trước khi mở M13

| # | Vấn đề | Khuyến nghị |
|---|---|---|
| P1 | Ngày bắt đầu và mốc bảo vệ GĐ3 theo lịch Khoa | Xác nhận để thay ngày tạm ở §3 |
| P2 | Phần cứng cho testbed (máy hiện tại có chạy nổi minikube + Online Boutique + ClickHouse không) | Đo thử ở đầu M14; nếu không đủ, thuê VM theo giờ chỉ trong lúc thu dữ liệu |
| P3 | Nhà cung cấp cho judge thứ hai | Chọn một model cùng hạng giá với `gemini-2.5-flash` để so chi phí công bằng |
| P4 | Ngân sách API GĐ3 | Duyệt bảng §4 (tổng ước 18–30 USD) |
| P5 | GVHD đồng ý trục RQ6 làm đóng góp chính | Gửi bản tóm tắt 1 trang sau buổi bảo vệ GĐ2 |
