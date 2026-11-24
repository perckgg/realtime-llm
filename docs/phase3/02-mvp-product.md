# 02 — Lộ trình MVP product (nhánh mở rộng)

> **Bản nháp 2026-11-23.** Product là nhánh **riêng** của tác giả, dựng trên lõi nghiên cứu; không thuộc phạm vi luận
> văn. Tên sản phẩm chưa chốt (tạm gọi `alert-triage`). Khi bắt đầu code, chuyển file này sang repo product.
> Lộ trình nghiên cứu: `01-lo-trinh-gd3.md`.

---

## 1. Định vị

**Vấn đề:** người trực (on-call) bị gọi bởi quá nhiều cảnh báo, phần lớn không cần xử lý; khi có sự cố thật thì mất
thời gian lần từ cảnh báo tới service gốc.

**Sản phẩm:** một **lớp phân loại (triage) không chặn cảnh báo**, đứng giữa nơi sinh cảnh báo (Alertmanager, Grafana) và
nơi gọi người (Slack, PagerDuty). Với mỗi cảnh báo, nó **gắn độ ưu tiên, trích bằng chứng và báo chi phí**, nhưng
**không bao giờ tự xoá cảnh báo**.

**Khách hàng mục tiêu đầu tiên:** đội vận hành công ty vừa và nhỏ đã dùng OpenTelemetry + bộ Grafana (Prometheus, Loki,
Tempo), chưa có ngân sách cho nền tảng observability thương mại.

**Khác biệt:**
- Mỗi phán quyết trích bằng chứng cụ thể (span, log, ngưỡng nền) và kiểm toán lại được.
- Trần chi phí LLM cứng, báo chi phí trên từng cảnh báo.
- Tự host, trung lập nhà cung cấp, không phải chuyển dữ liệu sang nền tảng khác.

**Đối thủ thật:** hiện trạng — chỉnh luật cảnh báo + group/inhibit/silence của Alertmanager. Sản phẩm phải chứng minh
tốt hơn cách này trên dữ liệu của chính khách.

---

## 2. Nguyên tắc thiết kế (không đánh đổi)

| # | Nguyên tắc | Hệ quả |
|---|---|---|
| N1 | **Fail-open** | LLM lỗi, quá hạn, vượt ngân sách hoặc chính hệ thống lỗi ⇒ cảnh báo đi thẳng tới người trực, gắn nhãn "chưa phân loại" |
| N2 | **Không xoá, chỉ xếp hạng** | Recall thấp không gây mất sự cố; giá trị đo bằng mức giảm số lần bị gọi khẩn |
| N3 | **Có bằng chứng mới được hạ ưu tiên** | Kế thừa `require_evidence` và neo bằng chứng của luận văn |
| N4 | **Không gửi log thô ra ngoài** | Prompt chỉ chứa trường có cấu trúc + message đã che (IP, email, token, ID) |
| N5 | **Mọi quyết định có nhật ký** | Lưu: cảnh báo, bằng chứng, model, phiên bản prompt, verdict, chi phí, độ trễ |
| N6 | **Cài bằng một lệnh** | `docker compose up`; cấu hình bằng một file YAML |

---

## 3. Kiến trúc

```text
Alertmanager / Grafana ──webhook──►  Ingest API
                                        │  chuẩn hoá AlertEvent, ánh xạ nhãn → service
                                        ▼
                                Evidence fetchers  ── Loki (LogQL) / Tempo (trace) / Prometheus (PromQL)
                                        │            / sự kiện deploy (K8s rollout, CI webhook) [v0.2]
                                        ▼
                     Lõi nghiên cứu (package core):
                       Fusion retrieval → ngưỡng nền trực tuyến → (cổng bỏ qua LLM) → judge qua API → neo bằng chứng
                                        │
                     Guard: hạn chót độ trễ, trần chi phí, fail-open
                                        ▼
                                Triage card (ưu tiên + bằng chứng + chi phí)
                                        │
                     ┌──────────────────┼──────────────────┐
                     ▼                  ▼                  ▼
                Slack (Socket Mode)   PagerDuty [v0.3]   Web UI xem lại
                     │
                 Nút 👍 / 👎  ──►  Feedback store (nhãn thật từ vận hành viên)
```

| Thành phần | Tái dùng từ repo luận văn | Viết mới |
|---|---|---|
| Lược đồ dữ liệu | `packages/schemas` | `AlertEvent`, `TriageCard`, `Feedback` |
| Truy xuất bằng chứng | `services/retrieval` (BM25 + Fusion Score) | Adapter Loki/Tempo/Prometheus thay cho Nezha |
| Judge + chính sách | `services/judge` (registry, cache, policy C3) | Guard độ trễ/chi phí, fail-open, che dữ liệu |
| Đồ thị service | `packages/graph` | Dựng từ Tempo theo cửa sổ trượt |
| Gom sự cố + RCA | `services/rca_agent` | Thẻ sự cố cho Slack [v0.2] |
| Giao diện | `services/web` (React) | Màn hình hàng đợi triage + phản hồi |
| Lưu trữ | ClickHouse/PostgreSQL | Bảng nhật ký quyết định, phản hồi |

Lõi được dùng qua package có phiên bản (tag `core-v*`, tạo ở M13 của GĐ3); product không sửa lõi tại chỗ.

---

## 4. Phạm vi theo phiên bản

### v0.1 — "Thẻ triage trên Slack" (một tenant, tự host)

| Việc | DoD |
|---|---|
| Ingest webhook Alertmanager (payload `alerts[]`: `labels`, `annotations`, `startsAt`, `fingerprint`) | Nhận, khử trùng theo `fingerprint`, đưa vào hàng đợi và trả `202 Accepted` trong < 150 ms |
| Ánh xạ nhãn cảnh báo → service trên đồ thị (cấu hình YAML) | Cảnh báo không ánh xạ được vẫn đi qua (N1) |
| Adapter Loki, Tempo, Prometheus | Lấy được bằng chứng trong cửa sổ quanh `startsAt` |
| Ngưỡng nền trực tuyến theo service–thao tác | Cold start rõ ràng: chưa đủ dữ liệu ⇒ không hạ ưu tiên |
| Judge qua API + cache + trần chi phí ngày | Vượt trần ⇒ fail-open, báo một lần trên Slack |
| Che dữ liệu trước khi gửi API | Test với mẫu chứa IP/email/token |
| Thẻ Slack (Socket Mode, không cần URL công khai): ưu tiên, 3 bằng chứng chính, chi phí, nút 👍/👎 | Phản hồi lưu vào DB |
| Nhật ký quyết định + trang web xem lại | Truy vết được mọi thẻ |
| `docker compose up` + README cài đặt | Người lạ cài trên testbed trong < 30 phút |

**Chỉ số thành công v0.1 (chạy shadow mode trên testbed):** fail-open đúng 100% ca lỗi giả lập; độ trễ thẻ p95 < 10 s;
chi phí trên mỗi cảnh báo được báo đúng.

### v0.2 — "Thẻ sự cố + sự kiện thay đổi"

| Việc | DoD |
|---|---|
| Thu sự kiện deploy (theo dõi rollout Kubernetes; webhook GitHub Actions / Argo CD) | Sự kiện hiển thị trên thẻ nếu xảy ra trước cảnh báo trong cửa sổ cấu hình |
| Gom cảnh báo thành sự cố (tái dùng grouping) + service gốc nghi ngờ | Một thẻ sự cố thay cho nhiều thẻ lẻ |
| Tóm tắt sự cố có trích bằng chứng (summarizer + validator) | JSON hợp lệ; không sinh câu lệnh thực thi |
| Báo cáo tuần: số lần gọi khẩn trước/sau, precision từ phản hồi | Xuất được từ Web UI |

### v0.3 — "Sẵn sàng cho đội thứ hai"

| Việc | DoD |
|---|---|
| PagerDuty / Opsgenie: đặt mức khẩn theo ưu tiên triage | Không bao giờ hạ xuống "không gọi" nếu chưa có bằng chứng |
| SSO (OIDC), phân quyền cơ bản, tách dữ liệu theo tenant | |
| Ngân sách theo tenant/service; báo cáo chi phí theo sự cố | |
| Chính sách lưu giữ dữ liệu; tài liệu bảo mật | Đối chiếu quy định bảo vệ dữ liệu cá nhân |

---

## 5. Đo hiệu quả (chỉ số product)

| Chỉ số | Cách đo |
|---|---|
| Số lần gọi khẩn mỗi ca trực | So trước/sau khi bật triage (shadow → thật) |
| Precision thực tế | Từ phản hồi 👍/👎 |
| Sự cố thật bị hạ ưu tiên nhầm | Đối chiếu với postmortem / sự cố đã xác nhận |
| MTTA, MTTR | Từ PagerDuty (v0.3) |
| Chi phí LLM / cảnh báo, / sự cố | Nhật ký quyết định |
| Độ trôi | Theo dõi tỷ lệ verdict theo phiên bản model; bộ hồi quy từ sự cố cũ |

**Ranh giới với luận văn:** các chỉ số ở đây **không** được dùng làm bằng chứng cho H6–H9 (không đăng ký trước, không có
`test` niêm phong). Trong luận văn, product chỉ xuất hiện ở phần hướng phát triển hoặc demo mở rộng.

---

## 6. Ngoài phạm vi MVP

- Tự train / fine-tune LLM; bắt buộc model tự host (để sau, khi có phần cứng và nhãn thật từ phản hồi).
- Tự lưu toàn bộ telemetry (luôn truy vấn hệ thống sẵn có của khách).
- Tự khắc phục sự cố, chạy runbook, sinh câu lệnh shell.
- Detector riêng thay luật cảnh báo của khách (đầu vào là cảnh báo có sẵn).

---

## 7. Lịch so với GĐ3

| Thời điểm | Product | Liên quan GĐ3 |
|---|---|---|
| Trước bảo vệ GĐ2 (2027-02-08) | **Không làm**; chỉ chốt license và hỏi quy định sở hữu trí tuệ | M12 |
| GĐ3 T1–T2 | Tạo repo product, dùng `core-v1.0.0` | M13 đóng gói lõi |
| GĐ3 T3–T7 | v0.1 dựng song song, dùng chung testbed | M14–M15 |
| GĐ3 T8–T13 | Đóng băng tính năng product; ưu tiên thực nghiệm | M16–M19 (không để product lấy giờ của G-test2) |
| GĐ3 T14–T16 | v0.1 chạy shadow mode trên testbed; demo mở rộng | M20–M21 |
| Sau bảo vệ GĐ3 | v0.2, v0.3; tìm đội dùng thử thật | — |

---

## 8. Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Product lấn giờ luận văn | Đóng băng product trong M16–M19; mỗi tuần chỉ một khối thời gian cố định |
| Lõi bị sửa vì product làm lệch kết quả luận văn | Lõi qua package có phiên bản; sửa lõi ⇒ chạy lại parity GĐ2 |
| Không có dữ liệu thật để chứng minh giá trị | Shadow mode trên testbed trước; tìm một đội dùng thử sau bảo vệ |
| Rò dữ liệu qua API | N4 (che dữ liệu, chỉ gửi trường có cấu trúc); hỗ trợ gói API doanh nghiệp không lưu dữ liệu |
| Sở hữu trí tuệ với trường | Hỏi GVHD/Khoa trước khi công khai hoặc thương mại hoá |

---

## 9. Quyết định cần chốt

| # | Quyết định | Phương án |
|---|---|---|
| D1 | License | Lõi Apache-2.0 + product đóng / open-core; hoặc mở toàn bộ |
| D2 | Tên sản phẩm | Kiểm trùng tên trên GitHub, PyPI, nhãn hiệu trước khi chốt |
| D3 | Kênh thông báo đầu tiên | Slack (khuyến nghị, Socket Mode) hoặc Microsoft Teams |
| D4 | Nhà cung cấp LLM mặc định | Giữ Gemini như luận văn; thêm nhà cung cấp thứ hai sau M17 |
