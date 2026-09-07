# Tuần hiện tại

> Cập nhật file này vào đầu mỗi tuần. Agent đọc file này để biết được phép làm gì.
> Chỉ chép phần tuần hiện tại từ `04-implementation-roadmap.md` vào đây.

---

## Tuần: 2 / 24 — **QUA**
## Ngày bắt đầu: 2026-09-03
## Ngày qua cổng chặn: 2026-09-07
## Giai đoạn: Tháng 1 — Nền tảng và kiểm chứng dữ liệu

---

## Mục tiêu tuần này

Hạ tầng và port GĐ1: `docker-compose` profiles, `infra/*/init.sql` theo tài
liệu `03`, `packages/schemas/`, port `services/replayer` và `services/detector`.

---

## Task được phép làm

- [x] `docker-compose.yml` profiles dev/full
- [x] `infra/clickhouse/init.sql`, `infra/postgres/init.sql` theo `03`
- [x] `packages/schemas/` — toàn bộ model ở `03` §1, kèm `loaders.py` bọc `scripts/nezha_windows.py`
- [x] Port `services/replayer` từ GĐ1 → `NezhaReplaySource`
- [x] Port `services/detector` (Isolation Forest 0.85) → `IsolationForestDetector`

---

## Definition of Done

- [x] Một lệnh dựng được toàn bộ môi trường dev
      → `docker compose --profile dev up -d` chạy được, `clickhouse` +
      `postgres` đều `healthy`. Hai lỗi hạ tầng gặp và vá khi kiểm chứng lần
      đầu — xem QĐ-010 trong `docs/experiment-log.md`.
- [x] Replay 50 window → alert candidate ghi vào ClickHouse
      → `scripts/replay_smoke.py --windows 50`: fit 19.316 cửa sổ dev, replay
      50 cửa sổ, sinh 14 `AlertCandidate`. Xác nhận bằng truy vấn trực tiếp:
      `SELECT count(), sum(candidate_source='metric') FROM
      aiops.fact_alert_evaluation WHERE run_id='week2-smoke'` → `50  14`,
      khớp chính xác với output script.

---

## Cổng chặn

**QUA.** Toàn bộ code và test (32/32, `pytest tests/ -q`) đã xong và xác nhận
đúng trên dữ liệu thật. Cả hai vế DoD đã kiểm chứng: môi trường dev dựng bằng
một lệnh, và 50 window replay ghi đúng 50 dòng (14 candidate) vào
`fact_alert_evaluation`, xác nhận bằng truy vấn trực tiếp trong ClickHouse.
Được phép sang Tuần 3.

---

## Cổng chặn Tuần 1 (đã qua)

**QUA.** Nezha có sẵn nhãn root-cause mức pod cho cả 101 lần tiêm lỗi, ánh xạ
100% lên tên service, trace có đủ `SpanID`/`ParentID`. Không phải gán nhãn tay,
không phải đổi dataset. Được phép sang Tuần 2.

---

## Ghi chú trong tuần

**Rolling buffer, hoãn Rescue Score, lỗi dữ liệu NaN latency (QĐ-009).** Port
`IsolationForestDetector` gặp ba vấn đề ngoài roadmap gốc: (1) lệch đơn vị cửa
sổ giữa `MetricWindow` nhiều-điểm của GĐ1 và `TelemetryWindow` một-điểm của
GĐ2 — giải quyết bằng rolling buffer theo service (người dùng chọn qua
AskUserQuestion), kèm cold-start guard để không cảnh báo giả khi buffer chưa
đầy; (2) Rescue Score (nhánh "else" SS6.2) hoãn có chủ ý sang Tuần 8 — chưa có
dữ liệu log/trace trong `TelemetryWindow` và roadmap không yêu cầu ở Tuần 2;
(3) 6 cột latency percentile của Nezha chứa chuỗi literal `"NaN"` ở cửa sổ 0
request, ảnh hưởng 28,58% số cửa sổ toàn corpus — đã lọc bỏ trong
`packages/schemas/loaders.py`. Chi tiết đầy đủ trong `docs/experiment-log.md`
QĐ-009.

**Lỗi múi giờ trong dataset (QĐ-002).** Nezha ghi mỗi mốc thời gian hai lần và
hai bản không khớp: ngày 2023-01-29 có 24/28 lần tiêm lỗi bị lệch 8 tiếng ở cột
epoch, và một file metric của `adservice` lệch 6,3 năm. Giai đoạn 1 dùng cột
epoch nên đã âm thầm mất 26 lần tiêm lỗi và 177 fault window. Giai đoạn 2 join
theo cột wall-clock.

**Việc này thay đổi cách chạy cổng chặn Tuần 3.** Baseline Giai đoạn 1
(Precision 0.32, FPR 0.046) đo trên nhãn cũ, nên Tuần 3 phải chạy hai lần:
`--time-source epoch` để đối chiếu port đúng/sai, rồi `--time-source wall` để
lấy con số báo cáo chính thức. Chi tiết trong `docs/experiment-log.md` QĐ-002.

**Dashboard dựng trước tiến độ (QĐ-007).** Ngoài phạm vi Tuần 1 nhưng trong
phạm vi Giai đoạn 2: `services/web/` đã có MVP bốn màn hình bằng React + Vite +
Recharts + react-flow, chạy trên dữ liệu giả. Đây là lệch **thứ tự**, không phải
lệch **phạm vi** — `06-scope-guard.md` §3 vẫn liệt kê "Dashboard 4 màn hình" là
in-scope. Không có màn hình thứ năm, không có form, không có dark mode.

**Vá setup.** `pip install -e ".[dev]"` không chạy được với `pyproject.toml`
ban đầu (setuptools từ chối flat-layout vì repo có nhiều thư mục top-level).
Đã vá, xem QĐ-006.

---

## Lệnh tái lập Tuần 1

```bash
bash scripts/download_nezha.sh          # nếu chưa có data/Nezha/
python scripts/verify_labels.py         # -> docs/label-audit.md (~80 s)
python scripts/make_splits.py           # -> data/splits/*.json
python scripts/make_splits.py --check   # xác nhận split không đổi
python -m pytest tests/ -q              # 8 test canh split
```

---

## Lệnh tái lập Tuần 2 (cần Docker Desktop đang chạy, xem QĐ-010 nếu cổng 9000 bận)

```bash
docker compose --profile dev up -d      # clickhouse + postgres
python -m pytest tests/ -q              # 32 test, không cần Docker/dataset
python scripts/replay_smoke.py --windows 50   # fit + replay + ghi ClickHouse
```

---

## Tuần sau (Tuần 3) — chưa được bắt đầu

Interface và tái lập baseline GĐ1 — tuần quan trọng nhất của Tháng 1. Phải
chạy cổng chặn hai lần (`--time-source epoch` rồi `--time-source wall`, xem
QĐ-002) để phân biệt "port sai" với "nhãn đã sửa".
