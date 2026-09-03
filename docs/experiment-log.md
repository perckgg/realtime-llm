# Nhật ký thực nghiệm — Giai đoạn 2

Ghi lại **quyết định** và **lần chạy thực nghiệm**, theo yêu cầu của
`docs/Final_Thesis_Phase2/04-implementation-roadmap.md` §9. Mỗi mục ghi: ngày,
bối cảnh, quyết định, hệ quả. Chỉ thêm vào cuối, không sửa mục cũ — nếu đổi ý
thì viết mục mới và dẫn chiếu ngược lại.

---

## 2026-08-31 — QĐ-001. Nezha có sẵn nhãn root-cause, không cần đổi dataset

**Bối cảnh.** Cổng chặn Tuần 1: nếu Nezha không có nhãn `root_cause_service`
thì toàn bộ Nhánh B không đo được Hit@1 / Hit@3, và phải chọn giữa gán tay
(2–3 ngày) hay đổi sang RCAEval.

**Phát hiện.** `scripts/verify_labels.py` cho thấy cả 101 lần tiêm lỗi đều có
nhãn trong `rca_data/<ngày>/<ngày>-fault_list.json`, gồm `inject_pod` và
`inject_type`. Nhãn ở **mức pod**; toàn bộ 28 pod bị tiêm lỗi ánh xạ được lên
20 service chuẩn bằng cách khớp tiền tố với danh sách service trong
`construct_data/root_cause_{hipster,ts}.json`. Trace có `SpanID` trên 100% span
và 97,86% span giải được về span cha trong cùng trace.

**Quyết định.** Giữ Nezha. Không gán tay, không đổi dataset. Cổng chặn Tuần 1
coi như qua.

**Hệ quả.** Nhánh B chấm Hit@k ở **mức service**, không phải mức pod. Bảy
service chạy nhiều replica (`ts-basic-service`, `ts-food-service`,
`ts-travel-service`, `ts-route-service`, `ts-contacts-service`,
`ts-preserve-service`, `ts-verification-code-service`) nên chấm ở mức service
dễ hơn mức pod — phải nói rõ điều này trong phần phương pháp của luận văn.

Bằng chứng: `docs/label-audit.md`.

---

## 2026-08-31 — QĐ-002. Join theo cột wall-clock, không theo cột epoch

**Bối cảnh.** Nezha ghi mọi mốc thời gian hai lần: `inject_time` /
`inject_timestamp` trong fault list, `Time` / `TimeStamp` trong metric CSV.
Pipeline Giai đoạn 1 (`legacy/nezha_setup/prepare_nezha_data.py`) dùng cột
epoch.

**Phát hiện.** Hai cột không khớp nhau ở hai chỗ:

1. Ngày **2023-01-29**, 24 trên 28 lần tiêm lỗi có `inject_timestamp` chậm hơn
   `inject_time` đúng 8 tiếng (dataset thu ở UTC+8; cột epoch bị ghi sai múi
   giờ). File metric của ngày đó đi theo `inject_time`.
2. Toàn bộ 1.209 dòng của
   `2022-08-22/metric/adservice-5f6585d649-fnmft_metric.csv` có `TimeStamp`
   vượt trước cột `Time` của chính nó khoảng 6,3 năm.

Các cột wall-clock khớp nhau trên cả bốn ngày.

**Quyết định.** Mặc định join theo cột wall-clock (`time_source="wall"` trong
`scripts/nezha_windows.py`). Giữ lại `--time-source epoch` để tái lập đúng nhãn
của Giai đoạn 1.

**Hệ quả — quan trọng cho Tuần 3.** Số nhãn thay đổi:

| Nguồn thời gian | Fault window | Lần tiêm lỗi có nhãn |
|---|---|---|
| epoch (như Giai đoạn 1) | 527 | 75 / 101 |
| wall-clock (dùng từ nay) | 704 | 101 / 101 |

Baseline Giai đoạn 1 (Precision 0.32, FPR 0.046) được đo trên **nhãn epoch**.
Cổng chặn Tuần 3 vì vậy phải chạy hai lần:

1. `--time-source epoch` để đối chiếu với con số 0.32 / 0.046. Đây mới là phép
   kiểm tra "port đúng hay sai".
2. `--time-source wall` để lấy con số baseline chính thức báo cáo trong luận
   văn. Con số này sẽ **khác** 0.32 / 0.046 và điều đó là đúng, không phải lỗi
   port.

Nếu bỏ qua bước 1, không phân biệt được "port sai" với "nhãn đã sửa".

---

## 2026-08-31 — QĐ-003. Định nghĩa cửa sổ và quy tắc gán nhãn

**Quyết định.** Một cửa sổ = **một mẫu metric của một pod = 60 s**, vì file
metric của Nezha lấy mẫu 60 s một lần. Toàn corpus: **95.660 cửa sổ**, trong đó
**704 fault** (0,74%).

`window_id = sha1(f"{service}|{pod}|{start_ts}")[:16]`, deterministic theo
`docs/Final_Thesis_Phase2/03-schemas-and-contracts.md` §1.1. Tài liệu 03 ghi
`hash(service + start_ts)`; ở đây thêm `pod` vì một service có thể có nhiều
replica sống cùng lúc và ground truth gắn vào pod. Không có `window_id` nào
trùng trên toàn corpus.

Quy tắc gán nhãn giữ nguyên của Giai đoạn 1: cùng pod **và** `start_ts` nằm
trong `[inject_ts − 60 s, inject_ts + 360 s]`.

---

## 2026-08-31 — QĐ-004. Split chốt cứng: nhóm theo lần tiêm lỗi, có vùng đệm

**Bối cảnh.** `02-data-and-experiment-protocol.md` §2 chỉ yêu cầu stratified
theo loại lỗi, seed 42, tỷ lệ 20/30/50.

**Quyết định.** Thêm hai ràng buộc chống rò rỉ, cả hai đã ghi trong docstring
của `scripts/make_splits.py`:

1. **Nhóm theo `injection_id`.** Cả 7 cửa sổ sinh ra từ một lần tiêm lỗi mô tả
   cùng một sự kiện. Chia lẻ chúng thì mô hình tinh chỉnh trên `val` sẽ được
   chấm trên các cửa sổ nó đã thấy. Đơn vị gán là lần tiêm lỗi, không phải cửa
   sổ.
2. **Vùng đệm 600 s.** Cửa sổ normal cùng pod, cách một lần tiêm lỗi dưới 600 s
   thì bị **loại khỏi cả ba split** (597 cửa sổ). Chúng vẫn nằm trong
   `data/window_index.csv`, chỉ không thuộc split nào.

Cửa sổ normal còn lại được gán theo khối `ngày|pod`.

**Kết quả.**

| Split | Cửa sổ | Fault window | Lần tiêm lỗi | Tỷ lệ thực |
|---|---|---|---|---|
| dev | 19.316 | 149 | 21 | 20,3% |
| val | 28.898 | 209 | 30 | 30,4% |
| test | 46.849 | 346 | 50 | 49,3% |

**Không lấy mẫu bớt cửa sổ normal.** Tỷ lệ mất cân bằng 1:135 được giữ nguyên
trong cả ba split vì Precision phụ thuộc trực tiếp vào tỷ lệ này; cân bằng lại
sẽ thổi Precision lên và làm hỏng cổng chặn Tuần 3. `tests/test_splits.py` canh
điều kiện này.

**Chốt cứng.** Ba file `data/splits/{dev,val,test}.json` đã commit. Sinh lại
phải ghi lý do vào commit message và thêm một mục mới trong file này. Kiểm tra
bằng `python scripts/make_splits.py --check`.

---

## 2026-08-31 — QĐ-005. `test` chưa bị chạm

Theo `02` §2.3, `test` không được chạy trước Tuần 11. Đến thời điểm này chưa có
thực nghiệm nào chạy trên bất kỳ split nào — mới chỉ sinh ra split. Ghi lại để
sau này đối chiếu.

---

## 2026-08-31 — QĐ-006. Vá `pyproject.toml` để `pip install -e` chạy được

`pip install -e ".[dev]"` (bước setup ở `07-setup-guide.md` §4) thất bại vì
setuptools thấy nhiều thư mục top-level (`data/`, `infra/`, `paper/`,
`archive/`, `legacy/`) và từ chối flat-layout discovery. Đã thêm khối
`[build-system]` và `[tool.setuptools.packages.find]` giới hạn ở
`packages*`, `services*`, `eval*`. Đồng thời thêm `python-dotenv` vào
dependencies vì bước kiểm tra môi trường ở `07` §11 dùng nó.

Môi trường hiện tại: `.venv` trên **Python 3.14.5** (máy chỉ có bản này). Mọi
dependency trong `pyproject.toml` cài được, không phải hạ phiên bản.

---

## 2026-08-31 — QĐ-007. Dựng MVP dashboard trước tiến độ, chọn React + Vite

**Bối cảnh.** Roadmap xếp dashboard vào Tuần 18. Việc dựng sớm ở Tuần 1 là
**lệch thứ tự, không lệch phạm vi**: `06-scope-guard.md` §3 có mục
"[x] Dashboard 4 màn hình" trong danh sách in-scope.

**Vì sao dựng sớm.** Bốn màn hình trong `01` §6.7 là hợp đồng ngược cho cả
pipeline: chúng quy định `services/api` phải trả gì, và do đó ClickHouse phải
lưu gì. Dựng vỏ trước với dữ liệu giả làm lộ ra sớm những trường còn thiếu
trong `03`, rẻ hơn nhiều so với phát hiện ở Tuần 18. Nó cũng cho một vật thể
chạy được để chụp hình đưa vào báo cáo ngay từ bây giờ, đúng tinh thần cuốn
chiếu.

**Quyết định: React + Vite + TypeScript + Tailwind + Recharts + react-flow
(`@xyflow/react`).**

| Phương án | Vì sao không chọn |
|---|---|
| Streamlit | Nhanh nhất để dựng, nhưng không vẽ được đồ thị lan truyền tương tác — mà đó chính là màn hình gây ấn tượng nhất khi bảo vệ (`01` §6.7). |
| FastAPI + Jinja + HTMX + Chart.js | Ít phụ thuộc nhất, nhưng phải tự viết layout đồ thị và tự quản lý trạng thái lọc. |
| **React + Vite (đã chọn)** | `@xyflow/react` cho đồ thị lan truyền kéo–thả, zoom, tô sáng đường root cause; Recharts cho thanh sai số CI 95%; Vite dev server có sẵn proxy sang FastAPI. |

**Đây có phải "web framework nặng" mà `06` §4 cấm không? Không.** Điều bị cấm
là Next.js / SSR / hệ thống thiết kế đầy đủ. Ở đây là một SPA tĩnh, build ra
một file JS, không có backend riêng, không có bước triển khai riêng.

**Ranh giới đã đặt để không trượt vào sản phẩm hoá.**

1. **Đúng bốn màn hình.** Danh sách sự cố là một tab trong Timeline chứ không
   phải màn hình thứ năm.
2. **Chỉ đọc.** Không có form, không có mutation, không có màn hình cấu hình
   (`06` §6.4).
3. **Chỉ light mode** (`06` §4 cấm dark mode).
4. **Màn hình không bao giờ import `mock/`.** Chúng chỉ gọi interface
   `DataSource` trong `src/api/client.ts`. Tuần 18 chỉ cần đặt
   `VITE_DATA_SOURCE=http` là chạy với dữ liệu thật, không sửa màn hình nào.
5. **Dải cảnh báo "dữ liệu giả"** hiện thường trực trên mọi màn hình khi chạy
   bằng fixture, để không ai chụp màn hình rồi đưa vào luận văn như kết quả
   thật.

**Trực quan hoá.** Bảng màu đã chạy qua bộ kiểm định mù màu (`ALL CHECKS PASS`,
light mode, nền `#fcfcfb`) và ghi lại trong `src/theme/tokens.ts`. Bốn ràng
buộc được giữ: một biểu đồ chỉ một trục (chỉ số 0–1 và độ trễ ms nằm ở hai biểu
đồ khác nhau); màu đi theo biến thể chứ không theo thứ hạng; danh tính luôn có
ký hiệu và nhãn chữ kèm màu; mọi biểu đồ đều có bảng số tương ứng.

**Kiểm chứng.** `npm run check` = typecheck + `scripts/smoke.tsx`. Smoke test
render cả bốn màn hình trong jsdom, chờ dữ liệu về, rồi khẳng định biểu đồ có vẽ
ra mark và bảng có dữ liệu — `tsc` không bắt được lớp lỗi đó. Đã bắt được một
lỗi thật ngay khi viết: alias `@/` mới chỉ khai trong `tsconfig.json` nên
TypeScript hiểu còn Vite thì không.

**Chưa làm.** Chưa nối API thật (Tuần 18). Bundle 859 kB chưa chia nhỏ;
`@xyflow/react` là phần nặng nhất, nếu cần thì lazy-load riêng màn hình 3.
