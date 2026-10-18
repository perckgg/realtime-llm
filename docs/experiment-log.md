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

---

## 2026-09-03 — QĐ-008. Toán học hoá chuẩn tắc và tách bạch ký hiệu Fusion Score & Rescue Score

**Bối cảnh.** Góp ý chiến lược từ phản biện (`5_diem_can_sua_chien_luoc_bao_luan_van.docx`, Điểm 1 & 2)
chỉ ra hai khiếm khuyết trong tài liệu và bản nháp trước:
1. Việc cộng trực tiếp `GraphDistance` vào điểm xếp hạng ranking bị sai chiều (khoảng cách càng lớn thì mức độ liên quan phải càng nhỏ).
2. Việc cùng dùng ký hiệu `(α, β, γ)` cho cả Fusion Score (RAG context ranking) và Rescue Score (candidate promotion) gây nhầm lẫn về mục tiêu nghiên cứu và vai trò của từng cơ chế.

**Quyết định.**
1. **Tách bạch ký hiệu và phạm vi áp dụng:**
   - **Fusion Score (Nhánh A — Paper & Luận văn):** Dùng bộ trọng số `(α, β, γ)` với `α + β + γ = 1`, `α, β, γ >= 0`.
     `Score_fusion(c | s0, t0) = α·BM25_norm(c, q) + β·TimeSim(tc, t0) + γ·GraphSim(sc, s0)`.
     Trong đó:
     - `BM25_norm(c, q)`: Chuẩn hóa Min-Max trên tập context ứng viên.
     - `TimeSim(tc, t0) = exp(- |tc - t0| / τ_time)`: Hàm phân rã thời gian số mũ (`τ_time = 300 s`).
     - `GraphSim(sc, s0) = 1 / (1 + d_G(sc, s0))`: Nghịch đảo khoảng cách đồ thị có hướng từ trace (hoặc `exp(-d_G / τ_graph)`). Khắc phục triệt để lỗi cộng trực tiếp khoảng cách.
   - **Rescue Score (Nhánh B — Luận văn):** Dùng bộ trọng số `(η1, η2, η3)` và ngưỡng `τ` (`η1 + η2 + η3 = 1`).
     `RescueScore(w | A) = η1·Λ_log(w) + η2·Φ_topo(w, A) + η3·Δ_time(w, A) >= τ`.
     Trong đó:
     - `Λ_log(w) = 1 - exp(- N_err(w) / k_log)`: Mật độ log lỗi bão hòa (`k_log = 10`), kháng log storm.
     - `Φ_topo(w, A) = max_{s_a ∈ S_A} [1 / (1 + d_G^undirected(s_w, s_a))]`: Độ cận kề topology vô hướng với tập alert đang hoạt động.
     - `Δ_time(w, A) = max_{t_a ∈ T_A} exp(- |t_w - t_a| / σ_rescue)`: Độ cận kề thời gian với sự cố (`σ_rescue = 300 s`).
2. **Hệ quả kiến trúc & cấu hình:**
   - Đồng bộ hóa các tài liệu `01-architecture-design.md`, `02-data-and-experiment-protocol.md`, `03-schemas-and-contracts.md`, `04-implementation-roadmap.md`, `06-scope-guard.md`.
   - Cấu hình YAML đổi `rescue.alpha, beta, gamma` thành `rescue.eta1, eta2, eta3, tau`.
   - `hybrid_bm25_graph` được định nghĩa rõ: hỗ trợ cả `fusion_mode: weighted` (chính, Paper core) và `fusion_mode: rrf` (baseline phụ không tham số).

---

## 2026-09-03 — QĐ-009. Cổng chặn Tuần 2: rolling buffer cho Isolation Forest, hoãn Rescue Score, và lỗi dữ liệu NaN latency

**Bối cảnh.** Tuần 2 port `IsolationForestDetector` từ
`legacy/src/detectors/isolation_forest_detector.py` sang `services/detector/`,
theo nguyên tắc "bọc, đừng viết lại" (`07-setup-guide.md` §8.1). Ba vấn đề
phát sinh trong quá trình port, không có trong roadmap gốc.

**1. Lệch đơn vị cửa sổ giữa Giai đoạn 1 và Giai đoạn 2.**
GĐ1 tính mean/std/min/max/last/delta trên nhiều mẫu thô trong một
`MetricWindow` (`window_size=120s` trên metric lấy mẫu 60s ⇒ ~2 điểm/cửa sổ).
`TelemetryWindow` của GĐ2 (QĐ-003) chỉ có đúng một điểm/60s. Áp công thức GĐ1
trực tiếp lên một điểm sẽ luôn cho std=0, delta=0 — vô nghĩa.

**Quyết định (người dùng chọn qua AskUserQuestion).** Giữ một rolling buffer
theo từng service (`_ServiceBuffer`, mặc định `buffer_size=2` ≈ 120s lịch sử ở
tần suất lấy mẫu 60s của Nezha, khớp `window_size=120s` của GĐ1) và tính công
thức GĐ1 trên buffer đó thay vì trên một `TelemetryWindow` đơn lẻ. `fit()`
replay buffer theo thứ tự thời gian trên toàn bộ tập fit để tránh lệch phân
phối giữa train và serve; buffer sống (`score()`) bắt đầu rỗng sau khi `fit()`
xong, không rò rỉ từ tập train.

**Hệ quả — cold-start guard.** Điểm cửa sổ đầu tiên của một service có lịch sử
một-điểm (std=0/delta=0 suy biến), về cấu trúc khác thường so với phần lớn
vector train (đa số 2-điểm) bất kể giá trị metric thật là gì. Nếu không chặn,
`is_candidate()` có thể bật/tắt cảnh báo chỉ vì buffer chưa đầy, không phải vì
bất thường thật. Đã thêm `_ServiceBuffer.is_full()`; `is_candidate()` luôn trả
`False` khi buffer chưa đầy, dù `score` cao. Kiểm chứng bằng
`tests/test_isolation_forest_detector.py` (`test_cold_start_first_point_can_look_unusual`,
`test_is_candidate_false_during_cold_start_even_if_score_is_high`).

**2. Rescue Score (nhánh "else" của SS6.2) chưa cài ở Tuần 2 — hoãn có chủ ý.**
Hai lý do: (a) `packages/schemas/loaders.py` chưa nạp `logs`/`spans` vào
`TelemetryWindow` (thiết kế có chủ ý của module đó, chưa ai yêu cầu chiến lược
join log/trace), mà `Λ_log(w)` trong Rescue Score (QĐ-008) cần mật độ log lỗi;
(b) `04-implementation-roadmap.md` đặt ablation Rescue Score ở Tuần 8 (Tháng
2), bảng việc Tuần 2 không nhắc đến. `IsolationForestDetector` vì vậy chỉ sinh
`AlertCandidate(source="metric")`, không có nhánh Rescue.

**3. Lỗi dữ liệu: chuỗi literal `"NaN"` trong 6 cột latency percentile.**
Chạy dry-run trên dữ liệu Nezha thật gây `ValueError: inf or nan encountered
in data` tại `statistics.pstdev`. Quét toàn corpus: 6 cột
`PodClientLatencyP90/95/99(s)`, `PodServerLatencyP90/95/99(s)` chứa chuỗi
`"NaN"` ở các cửa sổ 0 request (percentile không xác định, không phải độ trễ
0) — **27.335 / 95.660 dòng (28,58%)**, tổng **83.695 giá trị** trên toàn
corpus.

**Quyết định.** `packages/schemas/loaders.py::_row_to_window` bỏ giá trị metric
không hữu hạn (`not math.isfinite(parsed)`) — coi là "thiếu", không parse
thành 0.0 hay `inf`, vì cả hai đều mô tả sai một cửa sổ nhàn rỗi. Hồi quy:
`tests/test_loaders.py`.

**Kiểm chứng cổng chặn Tuần 2 (DoD `04` dòng 30–42).** Trên dữ liệu Nezha thật
(không cần Docker): fit trên toàn bộ split dev (19.316 cửa sổ) trong ~24,9s;
replay 50 cửa sổ đầu (`scripts/replay_smoke.py`) trong ~10,5s, sinh 14
`AlertCandidate`. Toàn bộ 32 test đơn vị (`pytest tests/ -q`) pass. Vế "ghi vào
ClickHouse" của DoD được kiểm chứng sau đó, ngày 2026-09-07 — xem QĐ-010.

---

## 2026-09-07 — QĐ-010. Hai lỗi hạ tầng Docker khi kiểm chứng cổng chặn Tuần 2, đã vá trong `docker-compose.yml`

**Bối cảnh.** Mở Docker Desktop và chạy `docker compose --profile dev up -d`
lần đầu trên máy này (Windows, Docker Desktop/WSL2) để chốt vế còn lại của DoD
Tuần 2 (QĐ-009). Hai lỗi hạ tầng gặp phải, không liên quan đến logic pipeline.

**1. Cổng host 9000 đã bị chiếm bởi phần mềm quản lý của công ty.**
`docker compose up -d` tạo container `clickhouse` nhưng không khởi động được:
`ports are not available: exposing port TCP 0.0.0.0:9000`. Xác định bằng
`Get-NetTCPConnection -LocalPort 9000` + `tasklist` rằng cổng 9000 bị giữ vĩnh
viễn bởi `ZSATunnel.exe` (tiến trình VPN/proxy Zscaler chạy nền trên máy công
ty) — không phải xung đột tạm thời, không được và không cần tắt tiến trình
này.

**Quyết định.** Đổi cổng host cho giao thức TCP gốc của ClickHouse từ
`9000:9000` thành `9004:9000` trong `docker-compose.yml`. Không ảnh hưởng
pipeline: `packages/storage/clickhouse.py` dùng `clickhouse_connect`, giao
tiếp qua HTTP ở cổng 8123 (không đổi); cổng 9000 chỉ dùng cho `clickhouse-client`
gõ tay, không có trong luồng chạy tự động nào.

**2. `./volumes/clickhouse` (bind mount) làm insert thất bại vì lỗi quyền ghi.**
Sau khi vá lỗi cổng, `scripts/replay_smoke.py` chạy hết fit + replay nhưng
insert vào ClickHouse báo `DatabaseError: ... filesystem error: in rename:
Permission denied`. Nguyên nhân: ClickHouse ghi dữ liệu bằng cách tạo thư mục
tạm rồi `rename()` sang tên chính thức (atomic insert); thao tác `rename` này
thất bại trên một bind mount trỏ vào ổ đĩa Windows chia sẻ qua WSL2 (khác
`postgres`, vốn healthy ngay với cùng kiểu bind mount `./volumes/postgres` vì
không dùng cơ chế rename tương tự).

**Quyết định.** Đổi volume của service `clickhouse` từ bind mount
`./volumes/clickhouse:/var/lib/clickhouse` sang named volume Docker
(`clickhouse-data:/var/lib/clickhouse`, khai ở khối `volumes:` cấp cao nhất
của `docker-compose.yml`). Named volume do Docker quản lý trực tiếp trên
filesystem của máy ảo WSL2, không đi qua lớp chia sẻ ổ đĩa Windows nên
`rename()` hoạt động bình thường. `postgres` giữ nguyên bind mount vì không có
lỗi.

**Kiểm chứng.** Sau hai thay đổi trên: `docker compose --profile dev up -d`
đưa cả hai container về `healthy`; `SHOW TABLES FROM aiops` liệt kê đúng
`fact_alert_evaluation` và `fact_retrieval_trace` (tự tạo từ
`infra/clickhouse/init.sql`); `scripts/replay_smoke.py --windows 50` chạy
xong, in "Wrote 50 rows to fact_alert_evaluation (14 alert candidates)"; truy
vấn trực tiếp `SELECT count(), sum(candidate_source='metric') FROM
aiops.fact_alert_evaluation WHERE run_id='week2-smoke'` trả về `50  14`,
khớp chính xác với output script. DoD Tuần 2 coi như qua hoàn toàn — xem
`docs/CURRENT-WEEK.md`.

**Hệ quả cho người dùng khác trên máy khác.** Named volume cho `clickhouse`
là lựa chọn an toàn hơn bind mount trên Windows nói chung (không riêng lỗi
Zscaler), nên giữ nguyên kể cả trên máy không có Zscaler. Cổng `9004` chỉ là
vá cho máy này; nếu máy khác không có gì chiếm cổng 9000, đổi lại
`docker-compose.yml` cho khớp môi trường đó không bắt buộc vì client chỉ dùng
8123.

---

## 2026-10-18 — QĐ-011. Đổi hướng GĐ2: từ "so sánh biến thể RAG" sang giải pháp CTAV + chứng minh, giữ platform demo; xếp lại lịch

**Bối cảnh.** GVHD yêu cầu GĐ2 phải đưa ra một giải pháp và chứng minh giải pháp đó,
không chỉ thực nghiệm như GĐ1. Kế hoạch cũ (Nhánh A = so sánh 5 biến thể RAG) vẫn là
thực nghiệm. Paper ICAETM 2026 đã cho thấy topology tăng recall (0.58 → 0.74) nhưng tăng
báo động giả trên traffic bình thường (7 → 137), F1 giảm (0.703 → 0.476) — một vấn đề
cụ thể chưa có lời giải. Review ngày 2026-10-18 còn phát hiện: (1) toàn bộ baseline GĐ1
Phase 4/5 (P 0.32, FPR 0.046, F1 không RAG 0.000, F1 có Rescue 0.781) đo bằng judge
`mock`; (2) `hybrid_bm25_graph` — lõi của paper — vừa nằm ở Tuần 10 vừa đứng đầu danh
sách cắt; (3) Tuần 3–7 không có tiến độ.

**Quyết định (người dùng yêu cầu cập nhật plan theo hướng này).**
1. Mục tiêu GĐ2: đề xuất và chứng minh **CTAV** = C1 Fusion Score topology (paper) +
   C2 asymmetric gating θ_topo > θ_local + C3 evidence anchoring + C4 adaptive two-tier
   routing (+ C5 Rescue Score); Nhánh B = RCA agent trên nền CTAV; platform demo giữ nguyên.
   Chi tiết: `docs/Final_Thesis_Phase2/08-research-direction.md`.
2. Chứng minh bằng giả thuyết H0–H5, đăng ký trước khi chạm `test`, kiểm định bootstrap
   CI + McNemar, ablation từng thành phần, ≥ 3 lần chạy.
3. Retrieval thu gọn còn `bm25_hybrid` và `hybrid_bm25_graph`; `temporal`/`graph` thành
   ablation của C1; `cross_modal` và RRF cắt (ghi `docs/ideas.md`).
4. Ngưỡng gating ký hiệu θ_local, θ_topo (không dùng η như paper, tránh trùng η1..η3 của
   Rescue Score — QĐ-008).
5. Lịch: giữ mốc bảo vệ Tuần 24 (tuần 2027-02-08); việc của Tuần 3 cũ làm ở Tuần 8;
   `test` chạm ở Tuần 16 thay vì Tuần 11; không còn tuần đệm; thứ tự cắt mới ở `04` §8.
6. Bỏ chỉ tiêu "F1 ≥ 0.78" (gốc từ số mock); chỉ tiêu mới theo H2–H5 (`00-INDEX.md`).

**Tài liệu đã cập nhật:** `00-INDEX.md`, `01` §6.3–6.4, `02` §5.3–5.4 và §6.5, `03` §1.3,
§1.4, §1.6, `04` (viết lại từ Tuần 8), `06` §1–§3, §4, §8, §10, `08`, `AGENTS.md`,
`docs/CURRENT-WEEK.md`.

**Còn mở:** Q1–Q5 ở `08` §9 (judge chính, phạm vi đánh giá, xử lý metric thiếu, lịch sử
buffer, mốc bảo vệ) — chốt đầu Tuần 8.

---

## 2026-10-18 — QĐ-012. Định nghĩa lại cổng chặn "tái lập baseline" thành hai cổng G-port và G-paper

**Bối cảnh.** Cổng chặn Tuần 3 cũ yêu cầu Precision ≈ 0.32 (±0.03), FPR ≈ 0.046 trên
"300 window đầu của dev". So với cấu hình đã sinh ra con số đó
(`legacy/nezha_setup/config/experiment_phase4_benchmark.yaml`), `eval/configs/bm25_baseline.yaml`
khác ở: ngưỡng detector (0.85 vs 0.95), cách fit (toàn dev vs 1.000 cửa sổ đầu), judge
(LLM thật vs `mock`), gate (không có vs 0.80/0.98, tối đa 30 lần gọi), tập cửa sổ (dev
theo thời gian, ~2 fault, vs `paper_300` đóng băng, 16 fault / 284 normal), đơn vị cửa
sổ (60 s vs 120 s bước 60 s). Thêm nữa P = 6/19, nên lệch 1 TP đã ra ngoài ±0.03. Cổng
cũ sẽ trượt dù port đúng, và không nói được lỗi nằm ở tầng nào.

**Quyết định.**
- **G-port (Tuần 9):** `eval/configs/gd1_phase4_parity.yaml` đúng cấu hình GĐ1 Phase 4,
  chạy trên `paper_300` ánh xạ sang `window_id` GĐ2. So từng tầng với đầu vào của GĐ1:
  retrieval (40 candidate từ audit GĐ1 → top-6 trùng doc ID), judge mock (verdict trùng),
  toàn pipeline (P 0.3158, FPR 0.0458, recall 0.375; lệch ≤ 1 cửa sổ mỗi ô ma trận nhầm
  lẫn, giải thích được), detector (so phân phối điểm, không đòi trùng tuyệt đối do đơn vị
  cửa sổ khác — QĐ-009).
- **G-paper (Tuần 10):** `eval/configs/paper_viewA_replay.yaml` tái lập Table 1 của paper
  trên `paper_500` từ cache Gemini, cache hit 100%.
- `bm25_baseline.yaml` giữ lại làm điểm xuất phát cho H0 trên split GĐ2 (Tuần 11), không
  còn là config của cổng chặn.

---

## 2026-10-18 — QĐ-013. Judge duy nhất là `gemini-2.5-flash-lite` qua API; không chạy LLM local, không local-first

**Bối cảnh.** Q1 của `08` §9. Kế hoạch cũ port nguyên local-first (llama3.2:3b qua
Ollama, fallback Gemini Flash Lite). Người dùng cho biết máy thực nghiệm không đủ tài
nguyên chạy LLM local, nên sẽ tập trung vào LLM API, nhưng cần lý do hợp lý để trình bày.

**Quyết định.** Mọi thực nghiệm chính (H0–H5) dùng một model API cố định
`gemini-2.5-flash-lite`, temperature 0, cùng prompt; không local-first, không fallback
sang model khác. Lỗi API: retry có trần, hết retry ⇒ `manual_review` + ghi log. Backend
`mock` chỉ dùng cho G-port.

**Lý do** (đầy đủ ở `08` §4.1):
1. Judge là biến cố định của thiết kế thực nghiệm; câu hỏi nghiên cứu nằm ở retrieval +
   chính sách quyết định.
2. Local-first tạo biến ẩn: model nào chấm một alert phụ thuộc lỗi/timeout của model local
   ⇒ so sánh giữa các cấu hình không còn có kiểm soát, không tái lập được.
3. Paper đo bằng `gemini-2.5-flash-lite`; cùng model mới tái lập được paper từ cache (G-paper).
4. GĐ1 đã đo (báo cáo GĐ1 §4.7.5, §4.8.4, qwen2.5:1.5b, 45 cửa sổ): 4/6 lần gọi phải
   chuyển sang Gemini (3 do `local_error`); độ trễ 4.585 ms vs 338 ms; F1 0.769 vs 0.800.
5. Phần cứng không đủ cho model local đủ lớn ở quy mô hàng nghìn lần gọi mỗi run.
6. Chi phí API thấp: paper đo ≈ 0,00013 USD/lần chấm (BM25), ≈ 0,00034 USD (topology);
   policy C2/C3 chạy lại trên cache không tốn lần gọi.
7. Nezha là benchmark công khai ⇒ không có vấn đề riêng tư khi gửi dữ liệu ra API.

**Hệ quả.**
- Cache key thêm `repeat` (mặc định 0): `sha256(prompt + model + temperature + max_tokens + repeat)`.
  Với temperature 0 + cache, "3 lần chạy" cho cùng kết quả; phương sai đo bằng
  `repeat ∈ {0, 1, 2}` trên tập con. Sửa quy tắc 4 trong `AGENTS.md`.
- Mỗi bản ghi lưu model id/phiên bản trả về để chống trôi phiên bản model.
- Demo bảo vệ chạy offline hoàn toàn từ cache.
- `eval/configs/bm25_baseline.yaml` đổi khối `judge` sang `backend: api`, `model: gemini-2.5-flash-lite`.
- Ollama không còn là yêu cầu cài đặt (`07` §1). Local-first được trình bày như kết quả GĐ1 và
  hướng GĐ3 (`docs/ideas.md`).

**Tài liệu đã cập nhật:** `00-INDEX.md` (bảng kế thừa, ngăn xếp công nghệ), `01` §5.4, §6.4,
sơ đồ §3, §7; `02` §3.1; `03` §1.4; `04` Tuần 8; `06` §3; `07` §1; `08` §4.1, §5.2, §9;
`AGENTS.md`; `docs/CURRENT-WEEK.md`; `docs/ideas.md`.

**Cần kiểm ở Tuần 9:** số candidate thật trên `val` ⇒ ước tính chi phí mỗi run và tổng
ngân sách API cho Chặng 2–3, ghi vào file này.

---

## 2026-10-18 — QĐ-014. Lộ trình theo cột mốc M0–M12 thay cho tuần; bắt buộc báo cáo sau mỗi mốc

**Bối cảnh.** QĐ-011 xếp lại lịch theo tuần lịch ("Tuần 8"), trong khi việc đang làm là
"Tuần 3" của bản gốc — người dùng thấy nhầm. Người dùng yêu cầu tổ chức lại theo cột mốc
(không cần theo tuần) và sau mỗi mốc phải có log ghi: cần review gì, plan cho mốc tiếp
theo, kết quả hiện tại, vấn đề cần người dùng giải quyết.

**Quyết định.**
1. `04-implementation-roadmap.md` viết lại thành 13 mốc M0–M12, mỗi mốc có DoD; cổng chặn:
   M0 (nhãn), M2 (G-port), M3 (G-paper), M4 (H0), M8 (G-test). Hạn ghi kèm chỉ là mục
   tiêu mềm để so với mốc bảo vệ (tuần 2027-02-08). Ánh xạ tuần cũ → mốc ở `04` §11.
2. Đóng một mốc = DoD đạt + báo cáo `docs/milestones/M<n>-<ten>.md` theo mẫu
   `docs/milestones/README.md`, đủ bốn phần: **Kết quả hiện tại · Cần review gì · Vấn đề
   cần bạn giải quyết · Plan cho mốc tiếp theo** + người dùng đã xem. Chưa có báo cáo thì
   chưa sang mốc sau. Báo cáo mốc là "không bao giờ cắt" (`04` §9).
3. `docs/CURRENT-WEEK.md` → `docs/CURRENT-MILESTONE.md` (đang ở M1); xoá bản mẫu trống
   `docs/Final_Thesis_Phase2/CURRENT-WEEK.md`.
4. Viết bù báo cáo M0 (`docs/milestones/M0-nen-tang.md`) từ review 2026-10-18.
5. Đánh số lại: kết quả sửa detector D1/D2 ghi ở **QĐ-015** (trước đây dự kiến QĐ-014).

**Tài liệu đã cập nhật:** `00`, `01` §5, §6.5, `02` §2, §4.4, §5.3–5.4, §6, `03` §1.4, §1.6,
`04` (viết lại), `05` R-A2 và checklist, `06` §7–§10, `07` checklist, `08` §5.3, §8, §9,
`AGENTS.md`, `README.md`.

---

## 2026-10-19 — QĐ-015. M1 việc 1: sửa detector (D1–D6) — điền metric thiếu, lịch sử liên tục theo pod, chấm điểm idempotent

**Bối cảnh.** Review 2026-10-18 (`docs/milestones/M0-nen-tang.md` §2, R1–R5) tìm ra các lỗi ở
`IsolationForestDetector` port ở M0. Người dùng chọn: metric thiếu → giá trị gần nhất của
cùng pod + cờ thiếu (Q3); detector được thấy lịch sử liên tục ngoài split (Q4).

**Thay đổi.**

| # | Vấn đề | Sửa | File |
|---|---|---|---|
| D1 | Metric thiếu (latency `"NaN"` bị loader bỏ) bị điền 0.0 trong vector đặc trưng | Điền bằng giá trị quan sát gần nhất của cùng pod; pod chưa từng có → median của tập fit; thêm đặc trưng `missing_fraction` cho mỗi metric (7 đặc trưng/metric thay vì 6) | `services/detector/isolation_forest.py` |
| D2 | Buffer chỉ thấy cửa sổ thuộc split → cửa sổ khởi phát lỗi có lịch sử từ ≥ 10 phút trước | `NezhaReplaySource(include_history=True)` phát mọi cửa sổ theo thời gian, split chỉ đánh dấu cửa sổ được chấm (`is_evaluated`); `detector.observe()` cho cửa sổ ngoài split; `fit(windows, train_ids)` dùng lịch sử đầy đủ nhưng chỉ lấy cửa sổ trong `train_ids` làm mẫu huấn luyện. Không dùng nhãn của cửa sổ ngoài split | `services/replayer/nezha_source.py`, `isolation_forest.py` |
| D3 | `score()` gọi hai lần là đẩy buffer hai lần | Đẩy idempotent theo `window_id`; `is_candidate()` chỉ đúng cho cửa sổ vừa được đẩy cuối cùng | `isolation_forest.py` |
| D4 | mypy dừng ngay (stub numpy cần ≥ 3.12); ruff 11 lỗi | `[tool.mypy] python_version = "3.12"`; sửa hết lỗi ruff | `pyproject.toml` |
| D5 | Chạy lại smoke cùng `run_id` nhân đôi dòng ClickHouse | `run_exists()`; `replay_smoke.py` bắt buộc `--run-id` và từ chối `run_id` đã có | `packages/storage/clickhouse.py`, `scripts/replay_smoke.py` |
| D6 | Buffer theo service, `TelemetryWindow` không có pod | Thêm `TelemetryWindow.pod` (`03` §1.1); buffer theo pod, fallback service | `packages/schemas/models.py`, `loaders.py` |

Phần còn lại của D6 (đưa `buffer_size`, cách fit vào `eval/configs/`; bỏ phụ thuộc
`packages` → `scripts`) dời sang M2 cùng harness.

**Kết quả.** Bảng QĐ-015-1. Detector trên split dev, fit và chấm cùng dev (in-sample, như
smoke M0), threshold 0.85, `buffer_size` 2, seed 42. Script đo: xem phụ lục báo cáo M1.

| Biến thể | Candidate | TP | FP | Recall detector | FPR |
|---|---|---|---|---|---|
| Trước (code M0) | 2.895 | 67 | 2.828 | 0.4497 | 0.1475 |
| Chỉ D1 + D6 (không lịch sử) | 2.896 | 66 | 2.830 | 0.4430 | 0.1476 |
| **Sau: D1 + D2 + D6** | **2.898** | **73** | **2.825** | **0.4899** | **0.1474** |

- 149 fault window dev: trước có 18/138 cửa sổ có mẫu liền trước không phải t−60 s; sau:
  137 cách đúng 60 s, 12 cách 59 hoặc 61 s (lệch nhịp lấy mẫu), 0 cold start ⇒ **149/149 có
  mẫu liền trước thật**.
- 4.164/19.316 cửa sổ dev (21,6%) có ít nhất một metric được điền thay vì 0.0.
- Mức tăng recall (+6 TP) đến từ D2; D1 trung tính về khả năng phát hiện (−1 TP, trong
  nhiễu) nhưng sửa đúng ngữ nghĩa dữ liệu (QĐ-009).
- FPR detector vẫn ~0,15 ⇒ trên `val` dự kiến ~4.300 candidate/run — đầu vào cho Q2 ở M2.

**Kiểm chứng.** `py -m pytest tests/ -q` → 48 pass (thêm 16 test: điền metric, idempotent,
`observe`, buffer theo pod, `train_ids`, chế độ history của replayer, `run_exists`);
`py -m mypy packages services` → sạch; `py -m ruff check .` → sạch.

**Smoke với ClickHouse thật** (`docker compose --profile dev up -d`, cả hai container
healthy): `py scripts/replay_smoke.py --windows 50 --run-id m1-smoke` → 50 dòng, 9 candidate,
48 s. Truy vấn trực tiếp: `run_id='m1-smoke'` có 50 dòng, 50 `window_id` khác nhau, 9
`candidate_source='metric'`. Cùng đúng 50 cửa sổ như `week2-smoke` (đều là normal): trước 14
candidate, sau 9, trùng 8 — tức 6 báo động giả của code M0 biến mất, thêm 1 mới; 50 cửa sổ
normal quá ít để kết luận. Chạy lại cùng `run_id` → script từ chối, số dòng giữ nguyên 50 (D5).
