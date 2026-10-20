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

---

## 2026-10-19 — QĐ-016. M1 việc 2–5: hợp đồng retrieval/judge, kho bằng chứng, port BM25 + judge; tái lập nửa BM25 của paper từ cache; hai phát hiện về đánh giá của paper

**Bối cảnh.** Việc 2–5 của M1 (`docs/CURRENT-MILESTONE.md`). Ràng buộc từ M3 (G-paper):
prompt GĐ2 phải trùng từng byte prompt GĐ1 để trúng 100% cache Gemini của paper; đồng thời
M1 yêu cầu bỏ tag fault type khỏi truy vấn BM25 (lỗi paper §3.5). Hai yêu cầu mâu thuẫn nếu
chỉ có một chế độ, vì truy vấn GĐ1 chứa fault type.

**Quyết định.**

| # | Nội dung | File |
|---|---|---|
| 1 | 4 Protocol `01` §5, `runtime_checkable` | `packages/schemas/protocols.py` |
| 2 | `ContextEvent`, `RetrievalBudget`, `RetrievalResult`, `JudgedAlert` + trường CTAV theo `03` §1.3–1.4. Thêm `JudgedAlert.debug` (DoD M1 đòi "`JudgedAlert` có `debug`"; `08` §4.1 đòi ghi model id/phiên bản) và `AlertCandidate.pod/end_ts/metric_snapshot/top_features` (prompt GĐ1 đọc `node_id`, `time_window`, `metric_snapshot`, `top_features`) | `packages/schemas/models.py`, `03` §1 |
| 3 | Kho bằng chứng: mỗi dòng log/span Nezha → `EvidenceDoc` đúng định dạng GĐ1 (doc id, text, severity trace = WARN khi ≥ 1.000 ms, bỏ health-check, bỏ trùng). `NezhaEvidenceStore` đọc **toàn bộ** `rca_data` (4,18 M log + 4,12 M span) theo file từng phút, LRU 48 file; không lọc theo nhãn | `packages/schemas/evidence.py` |
| 4 | `bm25_hybrid` port nguyên văn công thức GĐ1. Mặc định: truy vấn không có fault type; `pool="window"` = bằng chứng của `s_0` trong ±8 phút, thống kê BM25 trên pool. Chế độ parity `pool="global"` + `extra_query_terms` (đưa lại `detector_label`, `fault_type`) chỉ dùng cho G-port/G-paper | `services/retrieval/bm25_hybrid.py`, `registry.py` |
| 5 | Judge: prompt nguyên văn; cache JSONL đọc thẳng file GĐ1, key GĐ1 + `|repeat=n` khi n > 0; `GeminiBackend` (request, retry, schema như GĐ1; ghi `modelVersion`); `MockBackend` = mock GĐ1; luật quyết định `03` §1.4 | `services/judge/` |
| 6 | Migration CTAV cho ClickHouse, idempotent | `infra/clickhouse/migrations/001_ctav_columns.sql`, `scripts/apply_clickhouse_migrations.py` |

Lý do `pool="window"`: GĐ1 tìm trên toàn corpus, lấy top `max(search_k, 20·top_k)` = 120
rồi mới lọc thời gian. Corpus GĐ1 chỉ có 11.696 event; trên 8,3 M event của Nezha đầy đủ,
120 kết quả toàn cục gần như không bao giờ rơi vào cửa sổ ±8 phút ⇒ hầu như mọi alert không
có bằng chứng. Giới hạn ở `s_0` làm baseline thành "chỉ bằng chứng cục bộ" — đúng tầng 1
của CTAV (`08` §4); bằng chứng service khác là việc của C1.

**Kiểm chứng tái lập GĐ1** (`scripts/dump_gd1_prompts.py` chạy lại pipeline Step 7 View A
của GĐ1 trên `paper_500`, biến thể `hybrid_bm25_top6`, judge ép `mock`, không gọi API, 84 s;
`scripts/check_gd1_parity.py` chạy port GĐ2 ở chế độ parity trên cùng đầu vào, 30 s):

Bảng QĐ-016-1. Port GĐ2 so với GĐ1 trên 489 lần gọi LLM của paper (BM25, full budget).

| Kiểm tra | Khớp |
|---|---|
| Prompt GĐ1 tái lập được và key có trong cache Gemini của paper | 489 / 489 |
| Top-6 doc ID của `bm25_hybrid` (parity) trùng GĐ1, đúng thứ tự | 489 / 489 |
| Chuỗi prompt GĐ2 trùng GĐ1 | 489 / 489 |
| Key cache GĐ2 trùng, trúng cache GĐ1 (không cần API key) | 489 / 489 |

Verdict của `LLMJudge` GĐ2 tính lại từ các câu trả lời đã cache: TRUE_ALERT 65 (58 fault,
7 normal), FALSE_POSITIVE 33, UNCERTAIN 391. Trên 100 fault của `paper_500`: P = 58/65 =
0,8923, R = 0,58, **F1 = 0,7030, FP = 7 — trùng Table 1 của paper** (BM25, full budget).
Nửa BM25 của cổng G-paper (M3) vì vậy đã đạt; nửa topology chờ port C1.

**Phát hiện 1 — có bằng chứng hay không gần như lộ nhãn, cả ở paper lẫn ở Nezha gốc.**
Hai nguyên nhân chồng lên nhau:

1. *Dataset:* Nezha chỉ có file log/trace cho một số phút quanh các lần tiêm lỗi (vd.
   2022-08-22: 72 phút có log trong khoảng 03:53–07:55; cả 4 ngày: 303 phút), trong khi metric
   liên tục cả ngày. Cửa sổ normal xa lần tiêm lỗi không có log/trace nào.
2. *GĐ1:* `legacy/nezha_setup/prepare_nezha_data.py` còn lọc tiếp, chỉ giữ log/trace của
   service/pod bị tiêm lỗi trong [−300 s, +600 s] quanh mỗi lần tiêm, tối đa 80 event mỗi
   nguồn (`context_filter_rule` trong `processed/summary.json`).

Bảng QĐ-016-2. Có bằng chứng hay không, theo nhãn, trên 489 lần gọi LLM của paper
(`py scripts/evidence_coverage.py`, 4 phút).

| | Fault (98) | Normal (391) |
|---|---|---|
| GĐ1/paper: top-6 không rỗng | 89 (90,8%) | 21 (5,4%) |
| GĐ2 (`NezhaEvidenceStore` đầy đủ, `pool="window"`): top-6 không rỗng | 98 (100%) | 76 (19,4%) |
| Có file log/trace trong ±8 phút | 98 (100%) | 106 (27,1%) |

Bảng QĐ-016-3. Cửa sổ của split GĐ2 có file log/trace trong ±8 phút.

| Split | Fault | Normal |
|---|---|---|
| dev | 149/149 (100%) | 4.881/19.167 (25,5%) |
| val | 209/209 (100%) | 7.427/28.689 (25,9%) |
| test | 346/346 (100%) | 11.639/46.503 (25,0%) |

Hệ quả. (i) Trong paper, 370/391 normal không có bằng chứng; 360 trong số đó được LLM gắn
true_alert và chỉ bị `require_evidence` chặn thành manual_review. FP = 7 của BM25 vì vậy chủ
yếu đến từ việc normal **không có** bằng chứng, không phải từ việc BM25 chọn bằng chứng tốt;
topology mở rộng sang service lân cận ⇒ thêm normal có bằng chứng ⇒ FP 137 — một cách giải
thích khác cho "thiên lệch xác nhận do ngữ cảnh", cần tách ra ở H1. (ii) **GĐ2 cũng mắc nếu
đánh giá trên toàn split**: ~75% normal của `val`/`test` không có log/trace nào, judge với
`require_evidence` sẽ "đúng" một cách tầm thường trên chúng. Giao thức đánh giá (Q2) phải
xử lý việc này — xem báo cáo M1 §3 V7. G-paper vẫn tái lập trên kho GĐ1 (để chứng minh port
đúng), nhưng kho này không dùng cho kết quả khoa học nào của GĐ2.

**Phát hiện 2 — confidence của Gemini chủ yếu là `anomaly_score` chép lại.** Trong 489 câu
trả lời của paper (BM25), 365 (74,6%) có `confidence` **bằng đúng** `anomaly_score` trong
prompt; 404 (82,6%) lệch ≤ 0,005. Smoke M1 lặp lại hiện tượng (0,8885 ↔ 0,8885; 0,8784 ↔
0,8784). Ngưỡng confidence (0,80 của GĐ1, θ_local/θ_topo của C2) vì thế phần lớn là ngưỡng
trên điểm detector.

**Smoke end-to-end** (`py scripts/judge_smoke.py`): detector fit trên dev (30 s), replay dev,
`bm25_hybrid` trên kho đầy đủ, judge mock và `gemini-2.5-flash-lite` thật (5 lần gọi API,
`modelVersion = gemini-2.5-flash-lite`, ~1.950 token prompt + ~460 token output mỗi lần).

Bảng QĐ-016-4. Năm candidate dev qua BM25 → judge.

| Run | Candidate | Nhãn | Pool | Mock | Gemini (conf) |
|---|---|---|---|---|---|
| `m1-judge-smoke` | cartservice 03:54 | normal | 4.032 | TRUE_ALERT | FALSE_POSITIVE (0,8885) |
| | cartservice 03:55 | normal | 4.638 | TRUE_ALERT | FALSE_POSITIVE (0,80) |
| | cartservice 03:56 | normal | 4.640 | TRUE_ALERT | FALSE_POSITIVE (0,80) |
| `m1-judge-smoke-fault` | checkoutservice 04:43 | cpu_contention | 6.816 | TRUE_ALERT | FALSE_POSITIVE (0,90) |
| | checkoutservice 04:44 | cpu_contention | 6.958 | TRUE_ALERT | TRUE_ALERT (0,8784) |

Độ trễ retrieval: 4–8 s khi phải đọc file lần đầu, 90–140 ms khi đã có trong LRU. Mock GĐ1
gắn TRUE_ALERT cho mọi context có span (luật `duration_ms=`), nên mock chỉ có giá trị cho
G-port. 5 candidate không đủ để kết luận gì về chất lượng.

**Kiểm chứng.** `py -m pytest tests/ -q` → 86 pass (thêm 38 test: protocol; định dạng doc so
trực tiếp với hàm GĐ1; bỏ trùng file chồng lấn; không rò fault type, kèm kiểm tra độ nhạy;
BM25 parity so trực tiếp `HybridRetriever` GĐ1 và top-6 thật của `paper_500`; prompt/mock so
trực tiếp code GĐ1; key cache = key GĐ1 với `repeat = 0`, khác với `repeat > 0`; cache hit
không cần API key; luật `require_evidence`, ID bịa, ngưỡng, lỗi API/JSON); `py -m mypy
packages services` → sạch; `py -m ruff check .` → sạch. Migration áp hai lần không lỗi, 100
dòng smoke M0/M1 giữ nguyên với giá trị mặc định.

**Chưa làm / dời.** `top_features` của detector GĐ2 còn rỗng; metric snapshot GĐ2 là 19
metric thô (GĐ1: 6 đặc trưng tổng hợp) — cả hai ảnh hưởng prompt của mọi run GĐ2, cần chốt
trước H0 (M4). Phụ thuộc `packages` → `scripts` tăng thêm một chỗ (`evidence.py` dùng
`scripts.nezha_windows`), gộp vào việc D6 ở M2.

---

## 2026-10-19 — QĐ-017. Chốt V7, V8, V9 sau báo cáo M1; mở M2

**Bối cảnh.** Báo cáo `docs/milestones/M1-detector-bm25-judge.md` §3 nêu ba vấn đề mới
(QĐ-016, Phát hiện 1–2). Người dùng đã xem báo cáo và chọn:

**Quyết định.**

- **V7 → (a). Kết quả chính chấm trên cửa sổ có telemetry.** Một cửa sổ "có telemetry" khi
  Nezha có ít nhất một file log/trace trong ±8 phút quanh nó (cùng lề với `bm25_hybrid`).
  Chỉ số chính (P/R/F1/FPR, CI, McNemar) tính trên tập này; toàn split báo cáo làm số phụ.
  `val`: 209 fault + 7.427 normal; `test`: 346 + 11.639. Mask được tính từ danh sách file
  của dataset, không từ nhãn, nên không rò nhãn. **Thay mặc định của Q2** (`08` §9: "toàn
  split") — Q2 coi như đã chốt; số candidate thật trên `val` vẫn đo ở M2 để ước chi phí.
  Luận văn trình bày hiện tượng "có bằng chứng ⇔ gần sự cố" như hạn chế của giao thức paper
  và lý do của giao thức GĐ2.
- **V8 → (a). Giữ prompt GĐ1 nguyên văn cho mọi biến thể** (một judge, một prompt); C2
  (M6) gating dựa trên nguồn gốc/neo bằng chứng thay vì chỉ confidence; log-prob của nhãn
  đo thêm như ablation ở M4.
- **V9 → làm ở M2.** Detector GĐ2 báo top-3 đặc trưng lệch như GĐ1 để `top_features` của
  prompt không rỗng, trước khi chạy H0 (M4).

**Hệ quả.** Harness M2 phải ghi cột `has_telemetry` cho mọi cửa sổ và tính chỉ số trên cả
hai tập. `08` §9 Q2 và `02` §4.1 cập nhật cùng commit.

---

## 2026-10-19 — QĐ-018. M2: harness, V9, D6; cổng G-port đo theo tầng; số candidate thật trên `val`

**Thay đổi.**

| Việc | File |
|---|---|
| V9: `IsolationForestDetector.top_features()` — 3 metric lệch nhất so với tập fit (max theo metric của \|x − mean\| / std), như `_top_contributing_features` của GĐ1; `build_alert_candidate(..., top_features)` | `services/detector/isolation_forest.py`, `candidates.py` |
| D6: `scripts/nezha_windows.py` → `packages/schemas/nezha.py`; `packages` không còn import `scripts`; tham số detector (`threshold`, `buffer_size`, `fit`) đọc từ config | `packages/schemas/nezha.py`, harness |
| Harness `py -m eval run --config X`: replay có lịch sử → detector → gate GĐ1 (tùy chọn, có ngân sách) → retrieval → judge; 7 file output; ClickHouse tùy chọn (`fact_alert_evaluation` có cột CTAV, `fact_retrieval_trace`); `stages: detector` | `eval/harness/runner.py`, `eval/__main__.py` |
| Chỉ số trên tập có telemetry và toàn bộ (QĐ-017); CI bootstrap 95% (multinomial trên 4 ô — tương đương lấy mẫu lại cửa sổ); McNemar chính xác | `eval/harness/metrics.py`, `stats.py` |
| `NezhaEvidenceStore.has_telemetry()` — mask QĐ-017, chỉ dùng danh sách file | `packages/schemas/evidence.py` |
| Ánh xạ cửa sổ GĐ1 → GĐ2; dump Phase 4; so từng tầng | `scripts/map_gd1_windows.py`, `dump_gd1_prompts.py --split phase4`, `scripts/gport_layers.py` |

**Ánh xạ cửa sổ.** `paper_300` = 300 cửa sổ GĐ1 đầu tiên = 300 phút liên tiếp của **một**
pod (`cartservice-579f59597d-wc2lz`, 2022-08-22 03:51–08:50); fit Phase 4 = 1.000 cửa sổ
đầu của cùng pod. Cửa sổ GĐ1 [T, T+120) chứa đúng 2 mẫu (1.000/1.000); ánh xạ sang cửa sổ
GĐ2 của mẫu cuối (lệch T + 60 s ở 568 cửa sổ, T + 61 s ở 432 — GĐ1 dựng lưới cố định, nhịp
lấy mẫu Nezha trôi 1 s). Đồng hồ epoch như GĐ1. Nhãn: GĐ1 16 fault, GĐ2 (mẫu cuối) 14 — 2
cửa sổ cuối đợt lỗi (index 41, 50) mà GĐ1 gắn fault vì mẫu đầu còn lỗi; config parity dùng
nhãn GĐ1.

**Phát hiện về Phase 4.** Lần chạy Phase 4 đã commit (code GĐ1 cũ hơn) chuyển 10 candidate
hết ngân sách LLM thành **route_alert**; cả 10 là normal. **10/13 FP của Phase 4 đến từ quy
tắc hết ngân sách, chỉ 3 từ judge.** Code GĐ1 hiện tại mặc định manual_review. Config parity
dùng `budget_exhausted_action: route_alert` để tái lập.

**Cổng G-port** (`py scripts/gport_layers.py --run gd1_phase4_parity_v1` →
`eval/results/gport_layers_phase4.json`; `py -m eval run --config
eval/configs/gd1_phase4_parity.yaml` → `eval/results/gd1_phase4_parity_v1/`):

Bảng QĐ-018-1. G-port theo tầng, mỗi tầng nhận đúng đầu vào của GĐ1.

| Tầng | Đầu vào | Kết quả | Đạt |
|---|---|---|---|
| 0. Dump GĐ1 | Chạy lại Phase 4 | 40/40 candidate trùng audit đã commit | — |
| 1. Retrieval | 40 candidate GĐ1, corpus GĐ1 | Top-6 doc ID trùng **40/40**, đúng thứ tự | Đạt |
| 2. Judge mock | Candidate + context GĐ1 | Verdict trùng **30/30** lần GĐ1 chấm | Đạt |
| 3a. Gate + ngân sách + retrieval + judge + quyết định của harness | 300 cửa sổ, 40 candidate GĐ1 | TP/FP/FN/TN **6/13/10/271 = GĐ1**, 0 cửa sổ khác | Đạt |
| 3b. Toàn pipeline GĐ2 (detector GĐ2) | 300 cửa sổ ánh xạ | 6/**19**/10/**265**: P 0,2400 (GĐ1 0,3158), R 0,375 (=), FPR 0,0669 (GĐ1 0,0458) | **Lệch FP +6** (> ±1) |
| 4. Detector | 300 cửa sổ ánh xạ | Spearman điểm 0,79; trung bình 0,604 vs 0,584; candidate 41 vs 40, chung 32 | So phân phối (QĐ-009) |

Phân rã 14 cửa sổ lệch ở tầng 3b (cả 14 đều normal; TP, FN không đổi):
- 6 cửa sổ cả hai cùng chấm nhưng verdict mock khác (index 7, 8, 11, 87, 90, 99): context
  khác vì candidate GĐ2 mang cửa sổ thời gian [T+60, T+120) và metric/top-feature GĐ2 thay cho
  [T, T+120) và 6 đặc trưng chuẩn hoá của GĐ1 ⇒ truy vấn BM25 và điểm thời gian khác. Trên 22
  cửa sổ cả hai cùng chấm, chỉ 8 có top-6 giống. Mã retrieval/judge đã đúng ở tầng 1, 2, 3a.
- 8 cửa sổ do tập candidate khác (detector, QĐ-009) và hệ quả của nó lên thứ tự tiêu ngân
  sách 30 lần gọi (index 3, 174, 175, 176, 182, 190, 198, 219).

**Đếm candidate trên `val`** (`eval/configs/val_detector_count.yaml`, chỉ detector,
threshold 0,85, fit dev, 305 s):

Bảng QĐ-018-2. Detector GĐ2 trên `val`.

| Tập | Cửa sổ | Candidate | TP | Recall detector (CI 95%) | FPR |
|---|---|---|---|---|---|
| Có telemetry (chính) | 7.636 | 1.749 | 109 / 209 | 0,52 (0,45–0,59) | 0,221 |
| Toàn split | 28.898 | 5.677 | 109 / 209 | 0,52 | 0,194 |

Chi phí ước tính mỗi run trên tập chính: 1.749 lần gọi × ~0,00038 USD (≈ 1.950 token prompt
+ 460 token output đo ở smoke M1, giá 0,10/0,40 USD mỗi 1 M token) ≈ **0,67 USD**; toàn split
≈ 2,2 USD. Thời gian ở giới hạn 15 lần/phút của GĐ1: ≈ 2 giờ mỗi run trên tập chính —
giới hạn thực tế là tốc độ, không phải tiền.

**Kiểm chứng.** `py -m pytest tests/ -q` → 100 pass (thêm: top_features, harness stats/metrics/
gate/quyết định/config); mypy `packages services eval` sạch; ruff sạch; `make_splits.py
--check` khớp. Ghi ClickHouse thử với run `m2-clickhouse-smoke`: 300 dòng
`fact_alert_evaluation` có cột CTAV, 54 dòng `fact_retrieval_trace`; truy vấn `03` §3.3 ra
TP 6 / FP 19, khớp `metrics.json`.

---

## 2026-10-19 — QĐ-019. Chốt V10 (G-port đạt theo tầng), V11 (judge song song, 200 lần gọi/phút); tinh chỉnh Phát hiện 2

**V10 → (a).** Người dùng chốt: G-port **đạt**. Căn cứ: mọi tầng nhận đầu vào GĐ1 đều trùng
tuyệt đối (retrieval 40/40, judge 30/30, gate + ngân sách + retrieval + judge + quyết định
6/13/10/271); phần lệch FP +6 của toàn pipeline (QĐ-018, Bảng QĐ-018-1) do detector cửa sổ
60 s (QĐ-009) và candidate mang dữ liệu GĐ2, đã phân rã đủ 14 cửa sổ. Không viết detector
"chế độ GĐ1". Luận văn trình bày G-port theo tầng như Bảng QĐ-018-1.

**V11.** API key ở gói Pay-as-you-go Tier 1 (hạn mức 1.000+ RPM cho dòng Flash, ~80 USD
credit). Thay đổi:

| | Trước | Sau | File |
|---|---|---|---|
| Giới hạn tốc độ | 15 lần/phút, không an toàn đa luồng | `RateLimiter` dùng chung giữa các thread, mỗi lần thử HTTP (kể cả retry) lấy một slot; mặc định **200 lần/phút** | `services/judge/backends.py` |
| Judge trong harness | Tuần tự trong vòng replay | Pha 1 tuần tự (replay, detector, gate/ngân sách, retrieval); pha 2 `judge_all()` trên `judge.workers` thread (mặc định **8**); kết quả ghi theo thứ tự candidate ⇒ output không phụ thuộc số worker | `eval/harness/runner.py` |
| Cache | Có khoá | Không đổi; test 200 lần ghi đồng thời từ 8 thread | `services/judge/cache.py` |

200 lần/phút thấp hơn nhiều hạn mức Tier 1, và với độ trễ ~2,4 s mỗi lần gọi thì 8 worker
đạt đúng ~200 lần/phút; muốn tăng RPM phải tăng worker theo (RPM ≈ worker × 60 / 2,4).
Gate/ngân sách chỉ phụ thuộc thứ tự candidate, không phụ thuộc kết quả judge, nên tách pha
không đổi ngữ nghĩa: chạy lại `gd1_phase4_parity` cho `per_window.csv` trùng 300/300 dòng
(trừ cột độ trễ).

Bảng QĐ-019-1. Smoke judge song song với Gemini thật (`eval/configs/m2_parallel_judge_smoke.yaml`,
1.000 cửa sổ dev đầu tiên, BM25 GĐ2, 8 worker, 200 lần/phút).

| Chỉ số | Giá trị |
|---|---|
| Candidate / lần gọi API | 196 / 196 (cache trống) |
| Thời gian pha judge | 60,1 s (≈ 196 lần/phút — chạm trần limiter) |
| Lỗi / retry / 429 | 0 / 0 / 0 |
| Token prompt / output | 301.196 / 65.087 (trung bình 1.537 / 332 mỗi lần) |
| Chi phí | 0,056 USD (≈ 0,00029 USD mỗi lần) |
| Độ trễ LLM trung bình / P95 | 2,41 s / 3,09 s |
| Retrieval trung bình | 0,30 s (tuần tự, CPU) |
| Tổng thời gian run | 168 s (fit 28 s, replay + retrieval 80 s, judge 60 s) |

Ước tính một run trên tập chính của `val` (1.749 candidate, QĐ-018): judge ≈ 9 phút,
retrieval tuần tự ≈ 9 phút, replay + fit ≈ 6 phút ⇒ **~25 phút, ~0,50 USD**. Nút thắt giờ là
retrieval (CPU, tuần tự) — nếu M4 cần nhanh hơn: song song hoá retrieval bằng process, hoặc
dùng lại kết quả detector giữa các biến thể.

**Tinh chỉnh Phát hiện 2 (QĐ-016).** Tỷ lệ `confidence` = `anomaly_score`:

| | Có confidence = `anomaly_score` |
|---|---|
| Paper, prompt không có context | 316 / 379 (83,4%) |
| Paper, prompt có context | 49 / 110 (44,5%) |
| GĐ2 smoke (mọi candidate có context, có `top_features`) | 16 / 196 (8,2%) |

Hiện tượng chép điểm gắn chặt với việc prompt thiếu bằng chứng. Quyết định V8 (a) giữ nguyên
(C2 không dựa chỉ vào confidence), nhưng trên giao thức GĐ2 mức độ nhẹ hơn nhiều; đo lại trên
`val` ở M4.

**Kiểm chứng.** 103 test pass (thêm: limiter đa luồng, `judge_all` song song = tuần tự và
giữ thứ tự, cache ghi đồng thời); mypy, ruff sạch.

---

## 2026-10-19 — QĐ-020. Khảo sát trước M3: retrieval topology của paper không giới hạn thời gian; model Gemini bị chuyển ngầm; chặn lệch model

**Bối cảnh.** Chuẩn bị M3 (C1 + nửa topology của G-paper). Đọc code topology GĐ1
(`legacy/src/phase2/retrieval/`) và chạy lại biến thể `topology_aware_fusion_top6` của paper
offline: `py scripts/dump_gd1_prompts.py --variant topology_aware_fusion_top6` (judge mock).

**Kết quả tái lập.** 489/489 prompt topology tái lập được và có key trong cache Gemini của
paper ⇒ nửa topology của G-paper khả thi nếu port đúng.

**Phát hiện 3 — biến thể "topology" của paper chủ yếu là BM25 không giới hạn thời gian.**
`TopologyAwareRetriever` gộp (i) top-60 BM25 tìm trên **toàn corpus, không lọc thời gian**
và (ii) mở rộng đồ thị 2-hop trong ±8 phút, rồi xếp bằng Fusion Score. Trên 489 prompt:

Bảng QĐ-020-1. Nguồn và thời điểm của 2.934 context topology trong paper (BM25: QĐ-016 —
mọi context nằm trong ±8 phút).

| | Số context | Tỷ lệ |
|---|---|---|
| Chỉ từ BM25 toàn corpus | 2.612 | 89,0% |
| Chỉ từ mở rộng đồ thị | 229 | 7,8% |
| Cả hai | 93 | 3,2% |
| Ngoài ±8 phút quanh cửa sổ | 2.354 | 80,2% |
| … trong đó cách > 1 giờ | 2.200 | 75,0% |
| Prompt có ít nhất một context ngoài ±8 phút | 411 / 489 | 84,0% |
| Normal có context | 391 / 391 | 100% (BM25: 21 / 391) |

`graph_distance` của context: 0 → 1.364, 1 → 147, 2 → 401, 3+ → 190, không tới được → 832
(BM25 lấy cả service ngoài 2-hop). Kết hợp QĐ-016 (corpus GĐ1 chỉ gồm log/trace quanh các
lần tiêm lỗi): với biến thể topology, **mọi** normal nhận bằng chứng — phần lớn là log/trace
của sự cố ở thời điểm khác. Đây là một giải thích cạnh tranh cho FP 137 của paper, khác
"thiên lệch do topology": bằng chứng lệch thời gian, không phải bằng chứng lân cận trên đồ thị.

**Đồ thị service** (`legacy/outputs/phase2/service_graph_*`): dựng từ **toàn bộ** trace thô
(`rca_data` + `construct_data`, 4,18 M span), không lọc theo nhãn; 56 service, 68 cạnh (vô
hướng = có hướng, không có cặp hai chiều), trọng số cạnh nhỏ nhất 126 ⇒ `min_edge_count = 5`
(`02` §1.3) không loại cạnh nào; 18 service train-ticket cô lập. Coverage: 149/149 (dev),
209/209 (val), 346/346 (test) fault window nằm trên service có cạnh ⇒ ngưỡng fallback 60% không
kích hoạt (các service cô lập chưa từng bị tiêm lỗi).

**Model Gemini — yêu cầu nâng cấp của người dùng (chưa chốt, xem V12).** Thử một request
judge (payload GĐ1: temperature 0, `thinkingBudget: 0`, JSON schema) lên các model Flash
key được phép dùng:

Bảng QĐ-020-2. Thử một prompt paper (prompt 1.725 token) trên các model Flash, 2026-10-19.

| Model gọi | `modelVersion` API trả về | Độ trễ | Token output | Ghi chú |
|---|---|---|---|---|
| `gemini-2.5-flash-lite` | gemini-2.5-flash-lite | 2,3 s | 462 | Judge hiện tại (QĐ-013) |
| `gemini-2.5-flash` | gemini-2.5-flash | 3,4 s | 420 | Đúng model, phiên bản "001" |
| `gemini-3.5-flash` | **gemini-3.6-flash** | 3,0 s | 186 | Bị chuyển ngầm |
| `gemini-3.7-flash` | **gemini-3.8-flash** | 4,3 s | 180 | Bị chuyển ngầm |
| `gemini-3.8-flash` | gemini-3.8-flash | 4,5 s | 219 | Mới nhất |

Cả 5 chấp nhận `thinkingBudget: 0`. Hai id dòng 3.x được phục vụ bởi model mới hơn mà không
báo. **Quyết định:** `GeminiBackend` so `modelVersion` của mọi câu trả lời với model đã cấu
hình; lệch ⇒ `ModelVersionMismatch`, run dừng, câu trả lời không vào cache
(`services/judge/backends.py`, test `test_model_version_mismatch_stops_and_is_not_cached`).
Một run luôn do đúng một model chấm.

**Hệ quả cho M3–M4.** V12–V15 trong `docs/CURRENT-MILESTONE.md` (chờ người dùng). G-paper
không bị ảnh hưởng bởi việc đổi model: nó phát lại cache `gemini-2.5-flash-lite` của paper.

---

## 2026-10-19 — QĐ-021. Chốt V12–V15; M3: đồ thị, C1, cổng G-paper đạt; C1 của paper không đưa được bằng chứng lân cận trên dữ liệu đầy đủ

**Quyết định (người dùng duyệt toàn bộ đề xuất của QĐ-020).**

- **V12 → `gemini-2.5-flash`** là judge của mọi thực nghiệm GĐ2 (thay QĐ-013 ở điểm này);
  temperature 0, `thinkingBudget: 0`, cùng prompt. `gemini-2.5-flash-lite` chỉ còn dùng để
  phát lại cache của paper (G-paper). `GeminiBackend` không còn model mặc định
  (`JUDGE_MODEL`, `PAPER_MODEL` trong `services/judge/backends.py`).
- **V13 → C1 có cờ `bm25_pool`**: `global` = đúng paper (không giới hạn thời gian, chỉ trên
  corpus cố định — parity); `window` = GĐ2 (bằng chứng của các service trong 2-hop, ±8 phút,
  kho Nezha đầy đủ).
- **V14 → `origin`** theo khoảng cách: event ở `s0` là `local`, còn lại là `graph`; kênh tìm
  thấy ghi ở `debug.source_flags`.
- **V15 → dựng cả hai đồ thị**: vô hướng cho d_G của C1, có hướng cho C3.

**Kết quả M3.**

| Việc | Kết quả |
|---|---|
| Đồ thị (`packages/graph/service_graph.py`, `scripts/build_service_graph.py` → `data/graph/service_graph.json`) | 56 service, 68 cạnh; **trùng GĐ1 68/68 cạnh, cùng trọng số, 56/56 node**; 30 s |
| `docs/graph-coverage.md` (sinh tự động) | Service coverage 38/56 = 67,9% (< 80% → cảnh báo; 18 service train-ticket cô lập, không bị tiêm lỗi); edge density 0,0221; fault window có service trong graph 100% ở dev/val/test ⇒ không fallback |
| C1 `services/retrieval/hybrid_bm25_graph.py` | Port `TopologyAwareRetriever` + `FusionRanker` + `TopologyCandidateExpander`; registry; điểm prompt làm tròn 6 chữ số như GĐ1 |
| G-paper (`py scripts/check_gd1_parity.py --variant ...` → `eval/results/gpaper_viewA_paper500.json`) | Bảng QĐ-021-1 |
| Chặn chế độ parity trên `val`/`test` (`load_config`) | `parity_query_terms`, corpus GĐ1, `bm25_pool: global` bị từ chối |

Bảng QĐ-021-1. Cổng G-paper: tái lập Table 1 của paper (full budget) từ cache, không gọi API.

| Biến thể | Top-6 trùng | Prompt trùng | Cache hit | TP | FP | P | R | F1 | Paper |
|---|---|---|---|---|---|---|---|---|---|
| BM25 | 489/489 | 489/489 | 489/489 | 58 | 7 | 0,8923 | 0,58 | **0,7030** | 0,7030 / FP 7 |
| Topology | 489/489 | 489/489 | 489/489 | 74 | 137 | 0,3507 | 0,74 | **0,4759** | 0,4759 / FP 137 |

**Smoke judge `gemini-2.5-flash`** (`eval/configs/m3_flash_judge_smoke.yaml`, cùng 196
candidate dev với smoke flash-lite QĐ-019):

Bảng QĐ-021-2. flash so với flash-lite trên cùng 196 candidate (BM25 GĐ2, 8 worker, 200 lần/phút).

| | flash-lite (QĐ-019) | flash |
|---|---|---|
| Thời gian pha judge | 60 s | 74 s |
| Chi phí ước tính | 0,056 USD | 0,229 USD (≈ 0,00117 USD/lần — giá công bố tôi biết: 0,30 / 2,50 USD mỗi 1 M token, cần đối chiếu billing) |
| Độ trễ trung bình | 2,4 s | 2,9 s |
| Verdict thô TRUE / FP / UNCERTAIN | 26 / 124 / 46 | 40 / 155 / 1 |
| TP / FP / FN (pipeline, toàn bộ 1.000 cửa sổ) | 5 / 5 / 16 | 8 / 25 / 13 |
| confidence = `anomaly_score` | 16 | 1 |
| Verdict thô trùng nhau | 102 / 196 (52%) | |
| Lỗi | 0 | 1 × HTTP 403 (tạm thời; chạy lại run_id `_v2`: 1 lần gọi API, 195 cache hit, 0 lỗi) |

flash gần như không trả UNCERTAIN và chép `anomaly_score` ít hẳn. Ước một run trên tập chính
của `val` (1.749 lần gọi): ≈ 2 USD, judge ≈ 9–10 phút. `runtime.json` giờ ghi `judge_errors` và
CLI cảnh báo khi > 0 (chạy lại với run_id mới chỉ hỏi lại các câu lỗi).

**Phát hiện 4 — C1 với trọng số của paper không đưa được bằng chứng lân cận trên dữ liệu
đầy đủ.** Smoke C1 `bm25_pool: window` (`eval/configs/m3_c1_window_smoke.yaml`, 1.000 cửa
sổ dev đầu, judge mock):

Bảng QĐ-021-3. C1 (A4, `window`) trên kho Nezha đầy đủ, 196 lần retrieval.

| Chỉ số | Giá trị |
|---|---|
| Event được chọn (top-6) | 810, **100% local (d = 0)** |
| Prompt có ít nhất một bằng chứng lân cận | **0 / 196** |
| Ứng viên đồ thị trong pool (trung vị) | 200, trên 10 service tới được |
| Điểm của event hạng 6 (trung vị) | 0,841 |
| Điểm tối đa có thể của event lân cận d = 1 (BM25_norm = 1, TimeSim = 1) | 0,35 + 0,25 + 0,40 × 0,5 = **0,80** |
| Retrieval rỗng (không có telemetry) | 61 / 196 |
| Bằng chứng ngoài ±8 phút | 0 |
| Độ trễ retrieval trung bình / trung vị / P95 | 2,89 s / 2,63 s / 7,85 s (pool trung vị 146.667 event) |

Về cấu trúc: GraphSim(s0) = 1 > GraphSim(d = 1) = 0,5, và truy vấn chứa tên service/pod của
`s0` nên BM25 cũng ưu tiên `s0`. Khi `s0` có ≥ 6 event khớp trong cửa sổ, không event lân
cận nào vượt được. Trong paper bằng chứng lân cận xuất hiện (QĐ-020: 548 context ở d = 1–2)
vì corpus GĐ1 đã lọc theo nhãn rất thưa. Hệ quả: trên giao thức GĐ2, C1 đúng như công bố gần
như **trùng tầng 1 cục bộ** — H0 ("topology tăng recall và FPR") có nguy cơ không tái lập.
Cần quyết định trước M4 (báo cáo M3 §3, V16). Độ trễ ~2,9 s/lần ⇒ ~85 phút retrieval mỗi
run `val` (V17).

**Kiểm chứng.** 115 test pass (thêm: đồ thị, C1 so trực tiếp `TopologyAwareRetriever` GĐ1,
2 ca prompt topology thật của paper, time bounding, origin, chặn parity trên val/test,
lệch model); mypy, ruff sạch.

## 2026-10-20 — QĐ-022. V16 (b) C1-quota, V17 (a) tăng tốc C1 giữ ngữ nghĩa; thử đổi judge sang Gemini 3.x; phương án dự phòng

**Quyết định (người dùng, 2026-10-20).** V1 đã gửi. Làm V16 theo (b), V17 theo (a), bắt buộc có
phương án dự phòng. Thử đổi judge từ `gemini-2.5-flash` sang 3.8-flash hoặc 3.5-flash.

**V17 — tăng tốc C1, giữ nguyên ngữ nghĩa.**

- `services/retrieval/window_index.py` (mới): chỉ mục theo file phút (LRU 48 file), posting list
  numpy, BM25 cộng dồn theo đúng thứ tự token của truy vấn, cosine tính lại bằng `cosine()` gốc ở
  các ca mà thứ tự cộng float có thể khác. C1 có tham số `engine: vectorized` (mặc định) /
  `reference` (đường thuần Python cũ). `NezhaEvidenceStore` thêm `files_for()`, `load_file()`,
  memo `pod_to_service`.
- `eval/harness/runner.py`: `retrieval.workers` > 1 ⇒ retrieval chạy sau replay trên N process
  (đoạn liên tục theo thời gian). Retrieval là hàm thuần của (candidate, kho) nên kết quả không
  đổi; `latency_ms` đo dưới tải song song chỉ để tham khảo.
- Công cụ đo: `scripts/retrieval_bench.py` (`collect` / `run` / `compare`, kết quả ở `data/bench/`,
  không commit).

Bảng QĐ-022-1. C1 `window` trên 196 candidate của smoke M3 (dev, 1.000 cửa sổ đầu).

| | Tham chiếu (`reference`) | `vectorized`, 1 process | `vectorized`, 6 process (harness) |
|---|---|---|---|
| Top-6 trùng tham chiếu | — | 196/196, lệch điểm tối đa 0,0 | 196/196 event, score, origin; `per_window.csv` chỉ lệch cột latency |
| Độ trễ trung bình / trung vị / P95 | 3,56 s / 2,58 s / 10,7 s | 0,62 s / 0,15 s / 3,1 s | (tham khảo) 1,7 s / 0,25 s |
| Wall | 702 s (bench) · 593 s replay+retrieval (`m3_c1_window_smoke_v1`) | 122 s (bench) | **88 s replay+retrieval** (`m4_c1_vec_smoke_v1`), ≈ 0,45 s/lần theo throughput |

Phần còn lại chủ yếu là đọc + token hoá file phút lần đầu (~0,7 s/file); bản thân tìm kiếm
≈ 0,1 s/truy vấn. Ước run `val`: ~85 phút → ~12–15 phút retrieval với 6 process.
Khác biệt debug duy nhất: `timeout_exceeded` (phụ thuộc thời gian, 82/196) và 3 key mới.

**V16 — C1-quota.** `k_graph` (mặc định 0 = C1-paper): giữ tối thiểu min(`k_graph`, số có sẵn) chỗ
trong top-k cho event d_G ≥ 1 có Fusion Score cao nhất, phần còn lại theo thứ hạng, thứ tự cuối
vẫn theo Fusion Score; `debug.quota_promoted` ghi số event được đẩy vào. Không đổi trọng số
α, β, γ, không đổi signature Protocol.

Bảng QĐ-022-2. Ảnh hưởng của `k_graph` (cùng 196 candidate, top-6, retrieval-only, chưa có judge).

| `k_graph` | Prompt có ≥ 1 bằng chứng lân cận | Bằng chứng lân cận / prompt | Tỷ lệ bằng chứng lân cận |
|---|---|---|---|
| 0 (C1-paper) | 0 / 196 (0%) | 0 | 0% |
| 1 | 135 / 196 (68,9%) | 0,69 | 16,7% |
| 2 | 135 / 196 (68,9%) | 1,38 | 33,3% |
| 3 | 135 / 196 (68,9%) | 2,07 | 50,0% |

61 candidate không có telemetry nên retrieval rỗng; vậy mọi candidate có bằng chứng đều nhận
được bằng chứng lân cận khi `k_graph` ≥ 1. Chọn `k_graph` trên `val` cần tiêu chí, chưa chốt (V18).

**Kiểm chứng.** `tests/test_window_index.py` (12 test): chỉ mục ≡ `_Corpus` tham chiếu trên kho
ngẫu nhiên có trùng lặp, ts trùng, file chồng nhau; engine vectorized ≡ reference (k_graph 0 và 2,
service cô lập); kho không có file; quota (k = 0 ≡ paper, giữ thứ tự, ít lân cận hơn k, tham số sai).
124 test pass (bỏ `tests/test_storage.py` vì máy thiếu `clickhouse_connect` — lỗi môi trường có sẵn);
mypy sạch; ruff sạch trên các file đã sửa.

**Thử đổi judge.** `scripts/probe_gemini_models.py`: 1 lần gọi/model, prompt paper #0, so
`modelVersion` API trả về.

| Id gọi | `modelVersion` trả về | Dùng được? |
|---|---|---|
| `gemini-2.5-flash` | `gemini-2.5-flash` | Có (judge hiện tại) |
| `gemini-3.5-flash` | **`gemini-3.6-flash`** (bị chuyển ngầm) | **Không** — harness dừng với `ModelVersionMismatch` (QĐ-020) |
| `gemini-3.6-flash` | `gemini-3.6-flash` | Có |
| `gemini-3.8-flash` | `gemini-3.8-flash` | Có |
| `gemini-3.8-flash-001` | 404 | Không |

Giá 3.6/3.8-flash (0,75 / 3,75 USD mỗi 1 M token, giá khuyến mãi tới 31/12/2026) lấy từ trang
theo dõi giá bên thứ ba, **chưa đối chiếu trang giá Google** — chỉ dùng ước tính.

Bảng QĐ-022-3. Smoke judge trên cùng 196 candidate (BM25 GĐ2, 8 worker, 200 lần/phút). Không phải
kết quả khoa học.

| | 2.5-flash (`m3_flash_judge_smoke_v2`) | 3.6-flash (`m4_judge_g36_smoke_v1`) | 3.8-flash (`m4_judge_g38_smoke_v2`) |
|---|---|---|---|
| Verdict thô TRUE / FP / UNCERTAIN | 40 / **156** / 0 | 141 / **2** / 53 | 94 / **2** / 100 |
| Verdict cuối TRUE / FP / UNCERTAIN | 33 / 156 / 7 | 128 / 2 / 66 | 46 / 2 / **148** |
| Hạ cấp do thiếu bằng chứng hợp lệ | 7 | 13 | **48** |
| JSON hỏng | 0 | 0 | 1 (cắt cụt sau 28 token, nằm trong cache — chạy lại không hỏi lại) |
| TP / FP / FN (pipeline, 1.000 cửa sổ) | 8 / 25 / 13 | 11 / 117 / 10 | 6 / 40 / 15 |
| Độ trễ trung bình (lần gọi API thật) | 2,9 s | 2,5 s | 4,1 s |
| Chi phí ước tính | 0,229 USD | 0,330 USD | 0,315 USD |
| Verdict thô trùng 2.5-flash | — | 37 / 196 | 21 / 196 |

Dòng 3.x gần như **không bao giờ bác bỏ cảnh báo** (FALSE_POSITIVE 1%), thay bằng UNCERTAIN
(= chuyển người duyệt). CTAV cần judge biết bác bỏ báo động giả (H-FP); với 3.8, 75% candidate
rơi về người duyệt, và 3.8 thường không trích `evidence_event_ids` hợp lệ. Đổi model cũng
nghĩa là phải đổi/hiệu chỉnh lại prompt và làm lại baseline — ngoài phạm vi M4.
**Khuyến nghị: giữ `gemini-2.5-flash`** (V19, chờ người dùng chốt).

**Phương án dự phòng.**

| Rủi ro | Dự phòng |
|---|---|
| Engine vectorized có lỗi chưa phát hiện | `engine: reference` (oracle, đúng port); `scripts/retrieval_bench.py compare` đối chiếu bất kỳ lúc nào |
| Song song theo process lỗi / thiếu RAM (~1–1,5 GB/process) | `retrieval.workers: 1` (tuần tự, vẫn nhanh ~5,8×); giảm số process |
| C1-quota không tái lập được H0 | Báo cáo trung thực C1-paper (V16 a) + viết lại câu chuyện theo `08` §5.1; chỉnh GraphSim chỉ làm ablation (V16 c) |
| Model judge bị chuyển ngầm / ngừng hỗ trợ giữa chừng | Cache giữ mọi câu trả lời đã có ⇒ run cũ vẫn tái lập; run mới dừng (`ModelVersionMismatch`) ⇒ chốt một model trước H0, mọi run H dùng cùng model; dự phòng là `gemini-2.5-flash` |
| Giá 3.x tăng sau 2026 | Không phụ thuộc nếu giữ 2.5-flash |

**Phát hiện 5 — vì sao Gemini 3.x không bác bỏ cảnh báo: cột `PodSuccessRate(%)` của Nezha luôn
bằng 0.** `PodSuccessRate(%)` = 0,0 ở **95.660 / 95.660** dòng metric của Nezha (112 file) và ở
196/196 candidate smoke — cột chết (không có dữ liệu), nhưng `metric_snapshot` đưa nguyên giá trị
vào prompt (như paper). Prompt vì vậy luôn nói "tỷ lệ thành công 0%".

| Reasoning nhắc "success"/"0%" | 2.5-flash | 3.6-flash | 3.8-flash |
|---|---|---|---|
| … và trả FALSE_POSITIVE | 135 (coi nhẹ: "workload thấp", "trace bình thường") | 1 | 1 |
| … và trả TRUE_ALERT | 33 | 141 | 94 |
| … và trả UNCERTAIN | 0 | 44 | 93 |
| Reasoning nêu "thiếu log/bằng chứng" | 0 | 39 | 46 |

Giải thích: 3.x đọc "0% success" theo nghĩa đen là sự cố → không dám bác bỏ; khi bằng chứng
(log/trace) bình thường hoặc vắng thì 3.8 chọn `uncertain` đúng theo luật prompt "Use uncertain
when evidence is weak or unrelated". Ở 61 candidate không có telemetry, 3.8 thường trả TRUE_ALERT
với danh sách evidence rỗng → luật `require_evidence` hạ xuống UNCERTAIN (48 lần). 2.5-flash "đoán"
tín hiệu này là nhiễu nên bác bỏ nhiều, đúng hướng hơn với dữ liệu nhưng bằng suy diễn chứ không
nhờ bằng chứng. Hệ quả: hành vi judge phụ thuộc mạnh vào một cột lỗi của dataset — cũng ảnh hưởng
2.5-flash (33 TRUE_ALERT dựa vào "0%"). Bỏ cột chết khỏi prompt là thay đổi prompt (lệch parity
G-paper, phải làm lại smoke) ⇒ V20, chờ người dùng.

## 2026-10-20 — QĐ-023. Chốt V19 (judge giữ `gemini-2.5-flash`) và V20 (bỏ metric chết khỏi prompt GĐ2)

**Quyết định (người dùng, 2026-10-20).** Chốt theo khuyến nghị QĐ-022:

- **V20 → `judge.drop_metrics`**: danh sách metric bị bỏ khỏi `metric_snapshot` và `top_features`
  của prompt (`alert_payload`, `LLMJudge`, registry). Mặc định `[]` = prompt GĐ1 từng byte
  (G-paper, G-port không đổi). Mọi run GĐ2 có judge thật từ nay đặt
  `drop_metrics: ["PodSuccessRate(%)"]`. Chỉ thay đổi prompt; retrieval không đổi.
- **V19 → `gemini-2.5-flash`** tiếp tục là judge GĐ2 (QĐ-021 giữ nguyên), xác nhận bằng smoke
  sau V20 bên dưới.

**Căn cứ chọn cột (không đụng `test`).** Trên 48.214 cửa sổ dev + val (`iter_telemetry_windows`),
chỉ `PodSuccessRate(%)` là hằng (luôn 0,0); không metric nào khác hằng. Cột này không bao giờ vào
`top_features` (IForest không dùng được cột hằng) và không vào truy vấn BM25 (truy vấn lấy các
metric có |giá trị| lớn nhất).

Bảng QĐ-023-1. Smoke 196 candidate dev (BM25 GĐ2, 8 worker), tập có telemetry, pipeline. Không phải
kết quả khoa học (21 fault window, CI rộng).

| | 2.5-flash trước | **2.5-flash V20** | 3.8-flash trước | 3.8-flash V20 |
|---|---|---|---|---|
| Run | `m3_flash_judge_smoke_v2` | `m4_v20_g25_smoke_v2` | `m4_judge_g38_smoke_v2` | `m4_v20_g38_smoke_v1` |
| TP / FP / FN | 8 / 25 / 13 | **7 / 1 / 14** | 6 / 40 / 15 | 3 / 0 / 18 |
| P / R / F1 | 0,242 / 0,381 / 0,296 | **0,875 / 0,333 / 0,483** | 0,130 / 0,286 / 0,179 | 1,000 / 0,143 / 0,250 |
| F1 CI95 | [0,14; 0,45] | [0,24; 0,69] | [0,06; 0,30] | [0,00; 0,47] |
| FPR | 0,040 | **0,002** | 0,064 | 0,000 |
| Verdict thô TRUE / FP / UNC | 40 / 156 / 0 | 12 / 181 / 3 | 94 / 2 / 100 | 4 / 152 / 40 |
| Hạ cấp do thiếu bằng chứng | 7 | 4 | 48 | 1 |
| Pha judge / chi phí | 74 s / 0,229 USD | 76 s / 0,232 USD | — / 0,315 USD | 87 s, 3,4 s/lần / 0,332 USD |
| Verdict thô trùng bản trước | | 165 / 196 | | 15 / 196 |

Nhận xét:
- Bỏ "0% success" đổi hẳn hành vi 3.8 (trùng bản trước 15/196): giờ bác bỏ nhiều như 2.5 —
  xác nhận Phát hiện 5 là nguyên nhân. Nhưng 3.8 thận trọng hơn: recall 0,14 so với 0,33.
- 2.5-flash: 28 TRUE_ALERT trước đây dựa vào "0%" thành FALSE_POSITIVE; FP pipeline 25 → 1,
  mất 1 TP. 2.5-flash vẫn rẻ hơn, nhanh hơn, recall cao hơn 3.8 ⇒ giữ (V19).
- Phát hiện 5 hệ quả cho luận văn: một cột lỗi của dataset làm lệch judge mạnh hơn cả việc đổi
  model; paper (GĐ1) có cùng cột này trong prompt.

**Vấn đề mới (V21).** Câu trả lời JSON hỏng vẫn được ghi vào cache, nên chạy lại với run_id mới
không hỏi lại (`api_calls: 0` ở `m4_v20_g25_smoke_v2`): 1/196 ở 2.5 V20 (chuỗi bị cắt giữa
`evidence`), 1/196 ở 3.8 trước. Lỗi HTTP thì không bị cache nên vẫn hỏi lại được. Hiện câu lỗi
tính là UNCERTAIN/manual review (QĐ-016), không bao giờ thành TRUE_ALERT.

**Kiểm chứng.** Thêm test `drop_metrics` (prompt mặc định vẫn có cột, có `drop_metrics` thì không;
`top_features` cũng lọc). Docker `--profile dev` chạy: **127 test pass, gồm `tests/test_storage.py`**
(ClickHouse + Postgres thật; đã cài lại `clickhouse-connect`, `psycopg` có sẵn trong
`pyproject.toml`; `apply_clickhouse_migrations.py` chạy lại); mypy sạch.

---

## QĐ-024 — V18: quét `k_graph` trên `val` (2026-10-20)

**Thiết lập.** `m4_kgraph_val_k{0,1,2,3}_v1` (config `eval/configs/m4_kgraph_val_k*.yaml`): split
`val`, C1 window, `engine: vectorized`, `retrieval.workers: 6`, judge **mock** (chỉ để chạy
pipeline; không dùng số judge). Wall time 8 m 43 s / 7 m 41 s / 7 m 49 s / 7 m 52 s. Chọn bằng
`py scripts/kgraph_select.py` → `eval/results/m4_kgraph_selection_v2.json` (`_v1` cùng nội dung
nhưng ghi `NaN` không hợp lệ JSON; giữ nguyên, không ghi đè).

**Kết quả theo tiêu chí đã chốt (proxy root hit).** Tập xét: 109 fault window có telemetry, có
root label, có retrieval.

Bảng QĐ-024-1. Root hit trong top-6 (`val`, retrieval-only).

| `k_graph` | Root hit | CI95 | s0 = root | s0 ≠ root | Fault window có bằng chứng lân cận | McNemar vs k0 |
|---|---|---|---|---|---|---|
| 0 | 109/109 | [1,00; 1,00] | 109/109 | 0/0 | 0 | — |
| 1 | 109/109 | [1,00; 1,00] | 109/109 | 0/0 | 109 | p = 1 |
| 2 | 109/109 | [1,00; 1,00] | 109/109 | 0/0 | 109 | p = 1 |
| 3 | 109/109 | [1,00; 1,00] | 109/109 | 0/0 | 109 | p = 1 |

Quy tắc (hoà ⇒ k nhỏ nhất) cho **`k_graph = 1`**, nhưng **proxy suy biến**: trong nhãn GĐ2,
mọi fault window đều là cửa sổ của chính service gốc (`service == label_root_cause` ở 209/209
fault window; nhóm s0 ≠ root rỗng). Bằng chứng local luôn chứa root ⇒ proxy không phân biệt
được k. Đây là lỗi thiết kế tiêu chí (tôi đề xuất), không phải lỗi code.

**Số đo bổ sung (retrieval-only, có thông tin).** 1.640 candidate không lỗi có telemetry;
166 trong số đó trùng thời điểm với fault ở service khác.

Bảng QĐ-024-2. Candidate không lỗi (`val`).

| `k_graph` | Có bằng chứng lân cận | Top-6 chứa service gốc đang lỗi cùng lúc (/166) | Tỷ lệ chỗ local trong top-6 |
|---|---|---|---|
| 0 | 3 | 0 | 0,997 |
| 1 | 1.177 | 7 | 0,831 |
| 2 | 1.177 | 10 | 0,665 |
| 3 | 1.177 | 16 | 0,499 |

Nhận xét: k tăng chỉ thay chỗ local bằng lân cận; bằng chứng lan truyền thật (root đang lỗi)
rất hiếm (≤ 16/166 = 9,6%) vì root đồng thời thường không phải lân cận hoặc không có telemetry.
Ảnh hưởng thật của k lên FP/recall chỉ đo được bằng judge thật.

**Trạng thái.** Đã chốt (a) (người dùng, 2026-10-20): **`k_graph = 1`** cho C1-quota ở H0. Luận
văn phải ghi rõ proxy suy biến; ảnh hưởng thật của k đo ở H0 (C1-paper k = 0 vs C1-quota k = 1).
Sửa kèm: `summarize` ghi `null` thay `NaN`, `kgraph_select.py` dùng `allow_nan=False`.

---

## QĐ-025 — V22 (a) + M4 việc 3: ablation retrieval-only α, β, γ × `k_graph` trên `val` (2026-10-20)

**Quyết định (người dùng, 2026-10-20).** V22 → (a): ablation không gọi LLM, đo bằng (1) bằng
chứng lân cận trong top-6 (fault / không lỗi) và (2) "root đang lỗi cùng lúc": trong các
candidate không lỗi có fault ở service khác cùng timestamp, tỷ lệ top-6 chứa bằng chứng của
service đó. Root hit của fault window chỉ là kiểm tra hợp lý (suy biến, QĐ-024).

**Cài đặt.** `HybridBm25GraphRetriever.retrieve()` tách thành `build_pool()` (không phụ thuộc
α, β, γ, `k_graph`) + `top_events()`; `reweighted()` tạo bản sao với trọng số khác. Refactor
thuần: test cũ pass, test mới `test_reweighted_pool_equals_fresh_retriever` (4 bộ trọng số ×
k ∈ {0, 1, 3}) xác nhận pool xếp hạng lại ≡ `retrieve()` của retriever mới. Module
`eval/harness/fusion_ablation.py`, CLI `scripts/fusion_ablation.py`, config
`eval/configs/m4_fusion_ablation_val.yaml`. Lưới: đơn hình bước 0,25 (15 điểm, gồm lexical-only
(1, 0, 0), temporal-only (0, 1, 0), graph-only (0, 0, 1)) + trọng số paper, × `k_graph` ∈ {0, 1}
= 32 điểm. Không đổi signature Protocol.

**Run `m4_fusion_ablation_val_v1`.** 28.898 cửa sổ, 5.677 candidate, 6 process; replay 287 s,
dựng pool + xếp hạng 32 điểm 259 s (wall 9 m 10 s; 32 run harness riêng sẽ mất ~4 giờ).
**Đối chiếu:** ở trọng số paper, top-6 trùng từng event với `m4_kgraph_val_k0_v1` và
`m4_kgraph_val_k1_v1`: 5.677/5.677 mỗi run.

Tập xét: candidate có telemetry — 109 fault, 1.640 không lỗi (463 có retrieval rỗng), 166 không
lỗi có fault đồng thời ở service khác.

Bảng QĐ-025-1. `k_graph = 0` (C1-paper), các điểm có bằng chứng lân cận + đối chứng.

| α / β / γ | Không lỗi có lân cận (/1.177) | Tỷ lệ lân cận (không lỗi / fault) | Root đang lỗi cùng lúc (/166) | Root hit (/109) |
|---|---|---|---|---|
| **0,35 / 0,25 / 0,40 (paper)** | 3 | 0,003 / 0,000 | 0 | 109 |
| 0 / 0 / 1 (graph-only) | 3 | 0,003 / 0,000 | 0 | 109 |
| 1 / 0 / 0 (lexical-only) | 115 | 0,052 / 0,037 | 0 | 108 |
| 0,75 / 0,25 / 0 | 104 | 0,046 / 0,021 | 0 | 108 |
| 0,5 / 0,5 / 0 | 95 | 0,039 / 0,020 | 0 | 109 |
| 0,25 / 0,75 / 0 | 94 | 0,031 / 0,028 | 1 | 109 |
| **0 / 1 / 0 (temporal-only)** | 1.171 | **0,906 / 0,945** | 4 | **9** |
| 9 điểm còn lại có γ ≥ 0,25 | 3–66 | ≤ 0,032 / 0,000 | 0 | 109 |

Bảng QĐ-025-2. `k_graph = 1` (C1-quota) — mọi điểm có 1.177/1.177 prompt không lỗi và 109/109
fault có lân cận.

| α / β / γ | Tỷ lệ lân cận (không lỗi / fault) | Root đang lỗi cùng lúc (/166) | CI95 |
|---|---|---|---|
| **0,35 / 0,25 / 0,40 (paper)** | 0,169 / 0,167 | 7 (4,2%) | [1,2%; 7,8%] |
| 0 / 0 / 1 (graph-only) | 0,169 / 0,167 | 9 (5,4%) | [2,4%; 9,0%] |
| 1 / 0 / 0 (lexical-only) | 0,203 / 0,187 | 11 (6,6%) | [3,0%; 10,8%] |
| **0,25 / 0,75 / 0** (cao nhất) | 0,184 / 0,174 | **14 (8,4%)** | [4,2%; 13,3%] |
| 0 / 1 / 0 (temporal-only) | 0,907 / 0,950 | 4 (2,4%) | [0,6%; 4,8%]; root hit 9/109 |
| 11 điểm còn lại | 0,169–0,198 / 0,167–0,176 | 5–11 | |

**Phát hiện 6 — trọng số Fusion gần như không điều khiển được bằng chứng lân cận.**
1. Với `k_graph = 0`, mọi điểm có γ ≥ 0,25 đều giữ top-6 gần như toàn local (≤ 66/1.177 prompt
   có lân cận; trọng số paper: 3). Lý do như Phát hiện 4: GraphSim local = 1 > lân cận ≤ 0,5,
   cộng thêm BM25 của local cao hơn. Bỏ γ (γ = 0) chỉ đưa vào ≤ 5,2% lân cận; chỉ **temporal-only** đảo
   ngược hẳn (91–95% lân cận), và khi đó mất bằng chứng của chính service gốc (root hit 9/109).
   Không có điểm lưới nào trộn local + lân cận một cách cân bằng ⇒ cần quota (V16 b) chứ không
   phải chỉnh trọng số (V16 c) — củng cố lựa chọn C1-quota.
2. Bằng chứng lan truyền thật (root đang lỗi cùng lúc) hiếm ở mọi điểm: tối đa 14/166 (8,4%).
   CI của điểm cao nhất chồng lên CI của trọng số paper ⇒ không có căn cứ đổi trọng số.
3. Với `k_graph = 1`, trọng số chỉ chọn *lân cận nào* vào chỗ quota; tỷ lệ lân cận gần như cố
   định (≈ 1/6).

**Hệ quả cho H0.** Giữ trọng số paper (0,35 / 0,25 / 0,40) cho cả C1-paper (`k_graph = 0`) và
C1-quota (`k_graph = 1`); ablation này là kết quả mô tả, không dùng để tune. Không gọi API (0 USD).

---

## QĐ-026 — M4 việc 4: thiết lập H0 trên `val` (2026-10-20, đang chạy)

**Người dùng chốt (2026-10-20).** (1) Judge **toàn bộ** 5.677 candidate (chỉ số chính vẫn trên tập
có telemetry, phụ trên toàn bộ — QĐ-017). (2) LLM-không-RAG: số chính `require_evidence: false`
(với `true` recall = 0 theo cấu trúc), báo cáo thêm bản `true`. (3) Thêm ngân sách 120 lần gọi
theo thứ tự thời gian, chạy lại từ cache (0 USD).

**Cài đặt.** Retrieval `none` (`services/retrieval/no_retrieval.py`) — baseline LLM-không-RAG nằm
trong roadmap M4, không phải strategy thứ 3 (QĐ-011). Prompt chỉ phụ thuộc candidate + context
⇒ candidate có retrieval rỗng (4.391/5.677 ở C1) có prompt giống hệt giữa BM25 / C1 / không-RAG
và dùng chung cache. `py -m eval compare` (`eval/harness/compare.py`): P/R/F1/FPR + CI, hiệu số
so với run tham chiếu kèm CI bootstrap **có cặp** (multinomial trên 8 ô nhãn × dự đoán A × B),
McNemar chính xác trên mọi cửa sổ / fault / normal. Config `eval/configs/h0_val_*.yaml`: judge
`gemini-2.5-flash`, nhiệt độ 0, ngưỡng 0,80, `drop_metrics: ["PodSuccessRate(%)"]`, trọng số
C1 paper (QĐ-025), `k_graph` 0 / 1. Test: `tests/test_compare.py`; 148 test pass.

**Sự cố.** `h0_val_bm25_v1` dừng sau 4.722/5.677 lần gọi: API trả 429 "Your project has exceeded
its monthly spending cap". Câu trả lời đã nhận nằm trong cache; thư mục `h0_val_bm25_v1` rỗng,
không có kết quả; config chuyển sang `_v2`. Chi phí thực đo ≈ 0,00074 USD/lần (prompt ≈ 1.080
token, output ≈ 165 token) — tới lúc dừng ≈ 3,0 USD; còn ≈ 4.800 lần gọi ≈ 3,6 USD. Chờ người
dùng nâng spend cap (V23).
