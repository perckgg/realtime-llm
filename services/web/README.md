# `services/web` — Dashboard 4 màn hình

Bản MVP dựng trước tiến độ (roadmap xếp việc này vào Tuần 18) để chốt sớm bố cục,
bảng màu và luồng thao tác. Hiện chạy hoàn toàn trên **dữ liệu giả**: pipeline
chưa chạy nên ClickHouse và PostgreSQL còn rỗng.

## Chạy

```bash
cd services/web
npm install
npm run dev            # http://localhost:5173, đọc fixture
npm run build          # tsc -b && vite build -> dist/
npm run lint           # tsc --noEmit, không thêm ESLint
npm run smoke          # render cả 4 màn hình trong jsdom, soi HTML kết quả
npm run check          # lint + smoke — chạy cái này trước khi commit
```

Khi `services/api` đã có (Tuần 18):

```bash
VITE_DATA_SOURCE=http npm run dev      # proxy /api -> http://localhost:8000
VITE_API_TARGET=http://localhost:9000 VITE_DATA_SOURCE=http npm run dev
```

## Bốn màn hình, không hơn

Đúng theo `docs/Final_Thesis_Phase2/01-architecture-design.md` §6.7:

| # | Màn hình | Đường dẫn | Nội dung |
|---|---|---|---|
| 1 | Timeline | `/timeline` | Cột xếp chồng số cảnh báo theo thời gian, tách theo verdict; đường nhãn Nezha để đối chiếu; bảng cảnh báo và thẻ sự cố |
| 2 | Alert detail | `/alerts/:alertId` | Chuỗi anomaly score quanh cửa sổ, lý do LLM ra verdict, toàn bộ ngữ cảnh RAG đã truy xuất kèm ô `debug` |
| 3 | Incident detail | `/incidents/:incidentId` | Đồ thị lan truyền tương tác (react-flow) + báo cáo chẩn đoán, xem được cả dạng đọc lẫn JSON thô |
| 4 | Experiment comparison | `/compare` | Sáu panel chỉ số, mỗi panel một trục, có thanh sai số CI 95% và vạch baseline; bảng chỉ số đầy đủ |

Màn hình 3 và 4 là hai màn hình dùng khi bảo vệ, nên chúng được đánh bóng kỹ hơn.
**Không thêm màn hình thứ năm** — `06-scope-guard.md` §6.4 cấm màn hình quản trị
cấu hình, §6.5 cấm sản phẩm hoá.

## Kiến trúc

```text
src/
  api/types.ts      bản dịch TypeScript của packages/schemas (03 §1, §2)
  api/client.ts     interface DataSource + hai cài đặt: mock | http
  mock/fixtures.ts  dữ liệu giả sinh từ seed cố định
  theme/tokens.ts   bảng màu đã kiểm định CVD, thứ tự slot cố định
  components/       Card, StatTile, VerdictBadge, Legend, tooltip
  screens/          bốn màn hình
```

Điểm quan trọng: **màn hình không bao giờ import `mock/`**. Chúng chỉ gọi
`api` trong `api/client.ts`, và biến `VITE_DATA_SOURCE` quyết định phía sau là
fixture hay FastAPI. Tuần 18 chỉ cần dựng `services/api` trả đúng bảy endpoint
trong `01` §6.6 là dashboard chạy được với dữ liệu thật, không sửa màn hình nào.

## Quy tắc trực quan hoá

Bảng màu trong `src/theme/tokens.ts` và `src/index.css` đã qua kiểm định mù màu.
Trước khi đổi bất kỳ mã màu nào, chạy lại validator và giữ kết quả PASS:

```bash
node <skill>/scripts/validate_palette.js "#2a78d6,#eb6834,#1baf7a,#eda100,#e87ba4" --mode light
```

Các ràng buộc đang được tuân thủ, đừng phá:

- **Một trục cho một biểu đồ.** Chỉ số chất lượng (0–1) và độ trễ (ms) nằm ở hai
  biểu đồ khác nhau, không bao giờ ghép hai thang đo lên một hình.
- **Màu đi theo thực thể, không theo thứ hạng.** Ẩn bớt biến thể ở màn hình so
  sánh không làm những biến thể còn lại đổi màu.
- **Danh tính không bao giờ chỉ nằm ở màu.** Mọi verdict và mọi vai trò node đều
  có ký hiệu và nhãn chữ đi kèm.
- **Luôn có bảng số.** Biểu đồ nào cũng có bảng tương ứng (Timeline có bảng cảnh
  báo, đồ thị lan truyền có mục "Xem dạng bảng", màn hình so sánh có bảng đầy đủ).
- **Chỉ có light mode** — `06-scope-guard.md` §4 cấm dark mode ở Giai đoạn 2.

## Còn thiếu

- Chưa nối API thật (Tuần 18).
- Bundle 859 kB chưa chia nhỏ. Chấp nhận được cho một dashboard chạy nội bộ; nếu
  cần thì lazy-load riêng màn hình 3 vì react-flow là phần nặng nhất.
- Chưa có test đơn vị. Dashboard chỉ đọc và không chứa logic nghiệp vụ, nên
  `npm run check` (typecheck + smoke test) là mức kiểm tra tương xứng với phạm
  vi. `scripts/smoke.tsx` render cả bốn màn hình trong jsdom rồi khẳng định biểu
  đồ có vẽ ra mark và bảng có dữ liệu — nó bắt được lớp lỗi mà `tsc` không thấy
  (fixture vỡ, biểu đồ rỗng, màn hình kẹt ở trạng thái tải).
- **Chưa ai mở bằng mắt.** Smoke test kiểm tra cấu trúc chứ không kiểm tra thị
  giác: nó không thấy nhãn chồng lên nhau, tràn khung hay khoảng cách xấu. Hãy
  chạy `npm run dev` và soi một lượt trước khi dùng ảnh chụp cho báo cáo.
