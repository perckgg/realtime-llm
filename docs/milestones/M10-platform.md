# M10 — Platform end-to-end + dashboard dữ liệu thật

| | |
|---|---|
| Ngày lập báo cáo | 2026-11-16 (hoàn tất **Pha 1** trên nhánh `demo/gh-pages`) |
| Hạn mục tiêu | 2027-01-10 |
| Kết luận | **ĐANG LÀM — Pha 1 XONG** (Dashboard tĩnh dữ liệu thật + chế độ demo offline + GitHub Pages trên nhánh `demo/gh-pages`); **Pha 2** (API FastAPI + ClickHouse/Postgres + nạp kết quả `test` đầy đủ) chờ M8 & M9-B |
| Commit | Xem `git log` trên nhánh `demo/gh-pages` (sau `a5e74bd`) |
| Quyết định liên quan | QĐ-007 (MVP ban đầu), QĐ-037 (chốt cắt giảm `ExperimentComparison` dùng dữ liệu tĩnh), **QĐ-038** (M10 Pha 1) |

## 1. Kết quả hiện tại

| DoD / việc (`04` M10) | Đạt? | Bằng chứng |
|---|---|---|
| 1. `services/rca_agent/pipeline.py` điều phối E2E + ghi ClickHouse/Postgres | Chờ Pha 2 | Cần cấu hình `rca_final.yaml` (M9-A) và dữ liệu `test` (M8 / M9-B) |
| 2. `services/api` (FastAPI) đọc ClickHouse/Postgres | Chờ Pha 2 | Dựng ở Pha 2; giao diện vẫn giữ nguyên lớp trừu tượng `VITE_DATA_SOURCE=http` trong `services/web/src/api/client.ts` |
| 3. Nối 4 màn hình dashboard sang **dữ liệu thật** + đồ thị tương tác & trang hướng dẫn `/guide` | **Đạt (Pha 1, trên `val` + H0 `test`)** | `scripts/export_web_snapshot.py` → `services/web/src/mock/snapshot.json` (4.788,8 KB); 4 màn hình chính + `/guide` (`MethodologyGuide`) tiếng Anh chuẩn, đồ thị hỗ trợ chế độ Diff trước/sau CTAV, từng bước lan truyền và bấm node/cạnh xem telemetry |
| 4. Chế độ demo **offline** (không cần mạng/API key) + deploy GitHub Pages | **Đạt (Pha 1)** | Chạy thuần tĩnh trên client; `.github/workflows/deploy-pages.yml` + `public/404.html` + `VITE_BASE_PATH` trên nhánh `demo/gh-pages` |
| 5. Chạy E2E trên `test` → kiểm parity H5 với M9-B + `runtime.json` | Chờ Pha 2 | Thực hiện sau M8 và M9-B |
| Kiểm tra build & render `services/web` | **Đạt** | `npm.cmd run check` (`tsc -b --noEmit` + `smoke.tsx` 23/23 assertions trên 5 route & 5 run); `vite build --base=/realtime-llm/` thành công (`dist/assets/*.css` 7,60 kB gzip, `dist/assets/*.js` 745,01 kB gzip) |

**Thống kê dữ liệu thật đã đưa vào Dashboard Pha 1 (`val` + H0 `test`, 0 USD):**
- 5 phương pháp trên `val` (7.636 cửa sổ có telemetry, 209 fault): `ctav_final_val_v1` (F1 0,201; FPR 0,0069; 80 `TRUE_ALERT` xuất đủ), `h0_val_c1_k0_v1` (F1 0,126; FPR 0,0816), `h0_val_bm25_v3` (F1 0,103; FPR 0,0561), `h0_val_norag_v1` (F1 0,092; FPR 0,0224), `detector_only_val_v1` (F1 0,111; FPR 0,2208).
- 19 incident gom từ 80 `TRUE_ALERT` của `ctav_final_val_v1` bằng `services.rca_agent.grouping.group_alerts(..., 300.0)` trên `data/graph/service_graph.json` (7 fault incident, 12 cụm FP bình thường; 1-hop preview đạt 7/7 trên 7 fault incident).
- Bảng Ablation H3 + C5 Rescue trên `val`, đường cong F1 theo ngân sách H4 (120 → 5.677 lần gọi) và bảng kết quả G-test H0 trên `test` (11.985 cửa sổ telemetry, 346 fault — QĐ-037).

## 2. Cần review gì

| # | Kiểm gì | Ở đâu | Vì sao rủi ro |
|---|---|---|---|
| 1 | Mở trực tiếp giao diện trên trình duyệt (local `npm run dev` hoặc link GitHub Pages) | `services/web/` · thanh **Guided Walkthrough** (5 nút kịch bản + `/guide`) | `smoke.tsx` chạy trong jsdom không kiểm được tràn chữ, độ rộng bảng hay bố cục React Flow |
| 2 | Báo cáo trong `IncidentDetail` hiện sinh từ `grouping.py` + lan truyền 1-hop preview (chưa qua LLM Summarizer M9) | `scripts/export_web_snapshot.py` `_build_incidents` | Phân biệt rõ đây là bản xem trước giao diện trên `val`, không dùng thay cho kết quả chính thức H5 (M9-B) |
| 3 | Kích thước bundle JS ~5,68 MB thô (~726 kB gzip) do nhúng trực tiếp `snapshot.json` (4,7 MB) | `services/web/src/mock/snapshot.json` | Chấp nhận được cho demo/GitHub Pages (tải một lần ~726 kB gzip), nhưng ở Pha 2 nên đọc qua API hoặc tách lazy chunk nếu thêm nhiều dữ liệu `test` |

## 3. Vấn đề cần bạn giải quyết

| # | Vấn đề | Phương án | Khuyến nghị | Chặn mốc sau? |
|---|---|---|---|---|
| V45 | Kích hoạt GitHub Pages cho nhánh `demo/gh-pages` trên repo `perckgg/realtime-llm` | (a) Vào GitHub Repo → **Settings → Pages → Build and deployment → Source: GitHub Actions** để workflow `.github/workflows/deploy-pages.yml` publish tự động; (b) chỉ chạy local `npm run dev` | Chọn (a) nếu muốn mở link web trực tiếp từ GitHub Pages | Không |

## 4. Plan cho phần còn lại (M10 Pha 2, sau M8 & M9-B)

- Hoàn tất `services/rca_agent/pipeline.py` dùng cấu hình `eval/configs/rca_final.yaml` (chốt ở M9-A), ghi ClickHouse và PostgreSQL (`docker compose --profile dev up -d`).
- Dựng `services/api` (FastAPI) phục vụ 7 endpoint chuẩn `services/web/src/api/types.ts` để `VITE_DATA_SOURCE=http` đọc trực tiếp dữ liệu từ DB.
- Nạp kết quả `test` đầy đủ (H0–H5) vào `ExperimentComparison` (giữ dạng bảng/biểu đồ tĩnh sinh từ `eval/results/` theo QĐ-037), kiểm parity tập incident của `pipeline.py` khớp đúng kết quả M9-B, đo E2E latency vào `runtime.json` và chụp ảnh cho Chương 6.

## Phụ lục

- **Sai lệch so với plan:** Tách M10 thành 2 pha để dựng sớm bản demo web dữ liệu thật trên GitHub Pages (nhánh `demo/gh-pages`) song song trong lúc `master` hoàn tất M8 (`QĐ-038`).
- **Tài liệu / mã mới:** `scripts/export_web_snapshot.py`, `.github/workflows/deploy-pages.yml`, `services/web/public/404.html`.
