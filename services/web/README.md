# `services/web` — Dashboard 4 màn hình (CTAV Demo & M10 Pha 1)

Dashboard chỉ đọc phục vụ demo CTAV trên **dữ liệu thực nghiệm thật** trích từ
`eval/results/` (không dùng số giả lập), hỗ trợ chạy offline tại máy và deploy tĩnh
lên **GitHub Pages** trên nhánh `demo/gh-pages`.

## Cập nhật dữ liệu snapshot từ `eval/results/`

```bash
py scripts/export_web_snapshot.py   # sinh services/web/src/mock/snapshot.json (0 USD)
```

## Chạy và kiểm tra

```bash
cd services/web
npm install
npm run dev            # http://localhost:5173
npm run build          # tsc -b && vite build -> dist/
npm run lint           # tsc -b --noEmit
npm run smoke          # render cả 4 màn hình trong jsdom trên snapshot thật
npm run check          # lint + smoke — chạy trước khi commit
```

Build riêng cho GitHub Pages (subpath `/<repo-name>/`):

```bash
VITE_BASE_PATH=/realtime-llm/ npm run build
```

Workflow tự động `.github/workflows/deploy-pages.yml` chạy `npm run check` rồi
publish `services/web/dist` lên GitHub Pages mỗi khi push nhánh `demo/gh-pages`.

Khi `services/api` (FastAPI, M10 Pha 2) sẵn sàng:

```bash
VITE_DATA_SOURCE=http npm run dev      # proxy /api -> http://localhost:8000
```

## Bốn màn hình, không hơn (`01-architecture-design.md` §6.7)

| # | Màn hình | Đường dẫn | Nội dung |
|---|---|---|---|
| 1 | Timeline | `/timeline` | Cột xếp chồng theo verdict, đường lỗi thật Nezha, bảng cảnh báo thật (kèm nhãn hạ cấp C3), thẻ sự cố gom từ `grouping.py` |
| 2 | Alert detail | `/alerts/:alertId` | Chuỗi `anomaly_score` thật của pod, lý do LLM judge, 6 bằng chứng RAG kèm `duration_ms` vs `dev p90` và ô `debug` |
| 3 | Incident detail | `/incidents/:incidentId` | Đồ thị lan truyền từ `data/graph/service_graph.json` (`@xyflow/react`) + báo cáo cấu trúc (xem dạng thẻ / JSON thô) |
| 4 | Experiment comparison | `/compare` | 4 chỉ số chính (`val`) có CI 95%, đường ngân sách H4, độ trễ p95, bảng chỉ số đầy đủ, bảng ablation H3/C5, và bảng G-test H0 trên `test` |

**Không thêm màn hình thứ năm** (`06-scope-guard.md` §6.4). Chỉ dùng light mode (`06` §4).
