# Giai đoạn 3 & Hồ sơ Sản phẩm Thương mại hóa — Tài liệu Định hướng

> **Thư mục này được tách riêng khỏi nội dung quyển luận văn GĐ2 (`docs/drafts/` và `docs/Final_Thesis_Phase2/`).**
> Gồm hai nhóm tài liệu:
> 1. **Kế hoạch nghiên cứu Giai đoạn 3 (`01`) và Kế hoạch ranh giới Luận văn ↔ MVP (`03`)**: Định hướng học thuật cho giai đoạn tiếp theo của **Luận văn Thạc sĩ**, khẳng định rõ luận văn không đưa lên Production thật nhưng thể hiện trực tiếp bản **Technical Core MVP** của hệ thống trên môi trường thực nghiệm có kiểm soát.
> 2. **Bộ hồ sơ Sản phẩm Production & Thương mại hóa (`02`, `04`, `05`, `06`, `07`)**: Ý tưởng và thiết kế sản phẩm độc lập của tác giả (`alert-triage`), hoàn toàn không nhắc tới trong quyển luận văn.

---

## Danh mục Tài liệu

| File | Nhóm | Nội dung chính |
|---|---|---|
| [01-lo-trinh-gd3.md](01-lo-trinh-gd3.md) | **Học thuật (GĐ3)** | Lộ trình nghiên cứu GĐ3 (Luận văn Thạc sĩ): câu hỏi RQ6–RQ9, testbed tự dựng, mốc M13–M22 (T1–T20), giả thuyết H6–H9, ngân sách API, ngưỡng cắt và định vị Technical MVP trong luận văn. |
| [02-mvp-product.md](02-mvp-product.md) | **Sản phẩm (Tóm tắt)** | Tóm tắt định vị MVP `alert-triage`: lớp phân loại không chặn cảnh báo (Non-Suppressing Triage), 6 nguyên tắc thiết kế (N1–N6), phạm vi v0.1–v0.3 và lịch phối hợp với GĐ3. |
| [03-ke-hoach-ranh-gioi-luan-van-va-mvp.md](03-ke-hoach-ranh-gioi-luan-van-va-mvp.md) | **Kế hoạch & Ranh giới** | Tuyên bố định vị *"Luận văn không chạy Production thật nhưng thể hiện MVP kỹ thuật"*; ma trận ánh xạ 3 tầng (GĐ2 $\rightarrow$ GĐ3 Technical MVP $\rightarrow$ Production), lộ trình tái cấu trúc lõi ở M13/M16 và kế hoạch 4 pha song hành (Dual-Track Roadmap). |
| [04-prd-yeu-cau-san-pham-production.md](04-prd-yeu-cau-san-pham-production.md) | **Sản phẩm (PRD)** | Đặc tả Yêu cầu Sản phẩm cấp Production: User Personas, luồng nghiệp vụ End-to-End, 20 Yêu cầu Tính năng (`FR-01`..`FR-20`, kế thừa đúng 5 quy tắc `summarizer.py` + luật bảo vệ `severity=critical` chống hạ ưu tiên nhầm) và 12 Yêu cầu Phi tính năng (`NFR-01`..`NFR-12`). |
| [05-kien-truc-bigdata-ai-production.md](05-kien-truc-bigdata-ai-production.md) | **Sản phẩm (Kiến trúc)** | Kiến trúc Kỹ thuật chuyên sâu: Zero-Copy Federated Querying, Streaming Quantiles cho `C3-Online` (`quantileDDState`/`quantileDDMerge` trong ClickHouse, phương án B), chống bão cảnh báo 3 lớp, phễu giảm lượt gọi LLM, PII Scrubber (`p99 < 10ms`), phân biệt rõ cơ chế `C3` đã chứng minh với giả thuyết prompt mở rộng, và lưu trữ đa tầng. |
| [06-thuong-mai-hoa-gtm-finops.md](06-thuong-mai-hoa-gtm-finops.md) | **Sản phẩm (Thương mại)** | Chiến lược Thương mại hóa & Go-To-Market: định vị thị trường Self-Hosted OTel/Grafana (LGTM), tính toán Unit Economics dựa trên đơn giá thực đo (`$0,0014`/lượt + hệ số billing `1,14x`), phân tách COGS/Gross Margin cho Self-Hosted BYOK vs Managed Cloud, kịch bản *14-Day Shadow POC* (tách rõ `Fail-Open` và `False Downgrade Rate`) và quy trình làm việc với GVHD/Nhà trường về sở hữu trí tuệ. |
| [07-cong-nghe-va-scale-production.md](07-cong-nghe-va-scale-production.md) | **Sản phẩm (Công nghệ & Scale)** | Bộ lọc 5 câu hỏi cho mọi công nghệ, hồ sơ tải giả định, bảng quyết định theo bậc (GĐ3 / v0.1 / v0.2 / v0.3) kèm điều kiện nâng bậc đo được, cách scale ngang/dọc cho API, worker, PostgreSQL, ClickHouse, Kafka/Redpanda, Redis/Valkey và tầng LLM, hai phương án nguồn phân vị cho `C3-Online`, đánh giá riêng Rust, SLO và giấy phép thành phần. |

---

## Quy tắc Quản trị

1. **Không trộn vào quyển luận văn GĐ2:** Các tài liệu sản phẩm (`02`, `04`–`07`) là tài sản thiết kế riêng của tác giả để chuẩn bị cho hướng sản phẩm hóa sau khi bảo vệ.
2. **Bảo toàn tính tái lập của repo luận văn:** Khi bắt đầu viết code cho phần sản phẩm (`v0.1`), khởi tạo một repository riêng biệt (sau khi đã thống nhất quy định sở hữu trí tuệ với GVHD và Nhà trường ở M12) và chỉ tái sử dụng lõi thuật toán thông qua package có khóa phiên bản (`core-v1.0.0` trích xuất ở mốc M13).
