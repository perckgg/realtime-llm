# Mẫu mail gửi GVHD — kết quả tác tử RCA (M9) và Platform demo end-to-end (M10)

> Soạn 2026-11-17 theo quy định tại `04-implementation-roadmap.md` §10 ("Sau M3, M8, M10: gửi GVHD bản tóm tắt 1 trang
> lấy từ báo cáo mốc"). **Chưa gửi.**
> Có thể đính kèm `docs/milestones/M9-rca.md`, `docs/milestones/M10-platform.md` và `docs/drafts/ch6-demo-platform.md` (xuất PDF).
> Số liệu đối chiếu từ `docs/experiment-log.md` QĐ-040..049, `eval/results/rca_final_test_v1/rca.json`, `eval/results/pipeline_{val_v2,test_v2,sens_test_v1}/runtime.json` và `eval/results/m10_demo_cases_v1/demo_cases.json`.

---

**Tiêu đề:** [CO5107] Báo cáo kết quả tác tử RCA trên tập `test` (M9) và hoàn tất Platform demo ngoại tuyến (M10)

Kính gửi Cô Võ Thị Ngọc Châu,

Em là Nguyễn Văn Hoàng Khang. Tiếp theo báo cáo kết quả cổng G-test (M8 ngày 16/11), em đã hoàn tất phần tác tử phân tích nguyên nhân gốc (**M9 — giả thuyết H5**) và đóng gói **platform end-to-end kèm dashboard bốn màn hình (M10)** chạy hoàn toàn ngoại tuyến từ `cache`. Em xin tóm tắt ngắn gọn kết quả chính thức và sản phẩm demo để báo cáo Cô ạ.

**1. Kết quả kiểm định tác tử RCA trên tập `test` (H5 — M9)**

| Cấu hình (`T_group = 180 s`, mức 1, `gemini-2.5-flash`) | Cảnh báo / Service | Incident (có nhãn / đa service) | Hit@1 [CI 95%] | Hit@3 | Baseline Hit@1 | ARR chung | ARR cascade | JSON hợp lệ |
|---|---|---:|---|---|---|---|---|---|
| `val` (`rca_final_val_v1`) | 80 / 8 | 26 (11 / 1) | 0,636 [0,364; 0,909] | 0,636 | 0,636 | 0,675 | 0,667 (1) | 26 / 26 |
| **`test` chính thức (`rca_final_test_v1`)** | **78 / 5** | **38 (17 / 0)** | **0,471 [0,235; 0,706]** | **0,471** | **0,471** | **0,513** | **— (0)** | **38 / 38** |
| *Độ nhạy ngoài đăng ký (`C3-trượt`)* | *438 / 22* | *114 (48 / 39)* | *0,208 [0,104; 0,333]* | *0,313* | *0,229* | *0,740* | *0,704 (41)* | *114 / 114* |

- **Kết luận H5 — Không được chấp nhận (0 / 4 vế đạt):** Do CTAV đóng băng chỉ giữ 78 cảnh báo trên 5 service nên mọi incident đều chỉ có một service (`Hit@1 = Hit@3 = baseline = 0,471`, `ΔHit@1 = 0,000`, `0 / 50` lần tiêm lỗi là cascade để đo ARR). Trên dòng độ nhạy `C3-trượt` (nơi 49 / 50 lần tiêm lỗi có cảnh báo và có 39 incident đa service, ARR cascade đạt `0,704`), Hit@1 cũng chỉ đạt `0,208` vì service gốc thật chỉ lọt vào danh sách cảnh báo ở `15 / 48` incident có nhãn (trần Hit@3 = `0,313`).
- **Trình bày trong luận văn:** Em báo cáo trung thực H5 không đạt ở nhánh định vị so với baseline (nhánh A), đồng thời ghi nhận **nhánh B** hoàn thành tốt phần gom cụm cảnh báo và tổng hợp báo cáo chẩn đoán JSON có kiểm chứng bằng chứng (`38 / 38` hợp lệ trên `test`, tổng chi phí M9 là `0,2772 USD` theo token).

**2. Platform end-to-end & Dashboard demo ngoại tuyến (M10 — 0 USD chi phí mới)**

- **Kiến trúc & API:** Chuỗi `Replayer → Detector → CTAV → Tác tử RCA → ClickHouse / PostgreSQL → FastAPI (7 endpoint chỉ đọc) → Dashboard React/Vite` đóng gói trong một lệnh `docker compose --profile dev up -d`, chuyển ngữ hoàn toàn sang tiếng Anh để đồng bộ thuật ngữ nghiên cứu và trình bày.
- **Tái lập chính xác từ `cache` (`DEMO_OFFLINE=1` xoá khoá API, tỷ lệ trúng `cache` 100%, `0` gọi API):**

| Lượt chạy DB (`services/rca_agent/pipeline.py`) | Split | Đối chiếu parity vs M9 | Dòng ClickHouse (`eval` / `trace`) | Incident / Báo cáo PG | Thời gian E2E (từ `cache`) |
|---|---|---|---:|---:|---:|
| `pipeline_val_v2` | `val` | `26 / 26` khớp 100% | 5.677 / 7.716 | 26 / 26 | 5.764,165 ms |
| **`pipeline_test_v2` (chính thức)** | `test` | **`38 / 38` khớp 100%** | **13.699 / 19.794** | **38 / 38** | **4.242,424 ms** |
| `pipeline_sens_test_v1` (độ nhạy, có băng cảnh báo) | `test` | `114 / 114` khớp 100% | 13.699 / 19.794 | 114 / 114 | 10.646,898 ms |

- **Kịch bản demo 5 bước & tự kiểm:** Đã xây dựng bộ chọn ca xác định theo quy tắc (`seed = 42`) minh hoạ đủ Timeline `13.699` candidate, ca normal bị C3 hạ (`productcatalogservice`), ca `network_delay` mà BM25 bỏ sót nhưng CTAV giữ được (`cartservice`), đồ thị lan truyền cascade từ dòng độ nhạy (kèm phân tích giới hạn trên `val` và băng cảnh báo ngoài đăng ký), cùng màn hình tổng hợp H0–H5 (`experiment_table.json`). Toàn bộ 5 màn hình đã được tự kiểm qua trình duyệt thật (`0` lỗi console, `0` kết nối ra ngoài `localhost`), lưu 5 ảnh chụp vào `docs/drafts/figures/m10-*.png`, hoàn tất nháp **Chương 6 (`docs/drafts/ch6-demo-platform.md`)** và vượt qua toàn bộ `253 / 253` kiểm thử tự động (`pytest`).

**3. Bước tiếp theo (M11–M12)**

Em chuyển sang **M11**: xuất mẫu ngẫu nhiên 30 incident tập `test` (`eval/manual/diagnostic_quality.csv`) để đánh giá chất lượng nội dung báo cáo RCA, thực hiện phân tích ca sai cho Chương 7 và tổng duyệt demo lần 1, sau đó chốt toàn văn luận văn ở M12.

Em gửi kèm báo cáo mốc `M9-rca.md`, `M10-platform.md` và bản nháp `ch6-demo-platform.md` để Cô xem qua trước khi em tiến hành phần đánh giá định tính M11 ạ.

Em cảm ơn Cô nhiều ạ.

Trân trọng,  
Nguyễn Văn Hoàng Khang
