# Tuần hiện tại

> Cập nhật file này vào đầu mỗi tuần. Agent đọc file này để biết được phép làm gì.
> Chỉ chép phần tuần hiện tại từ `04-implementation-roadmap.md` vào đây.

---

## Tuần: 1 / 24 — **ĐÃ XONG**
## Ngày bắt đầu: 2026-08-31
## Giai đoạn: Tháng 1 — Nền tảng và kiểm chứng dữ liệu

---

## Mục tiêu tuần này

**Kiểm tra dữ liệu trước, code sau.** Tuần này KHÔNG viết code pipeline.

Rủi ro lớn nhất của toàn đề tài nằm ở đây: nếu Nezha không có nhãn
`root_cause_service`, toàn bộ Nhánh B không đo được Hit@1/Hit@3.

---

## Task được phép làm

- [x] `scripts/verify_labels.py` — kiểm tra nhãn root-cause của Nezha
- [x] Kiểm tra trace có đủ `span_id` / `parent_span_id` để dựng call chain
- [x] Viết `docs/label-audit.md` (một trang, có bảng số liệu)
- [x] `scripts/make_splits.py` — chia dev/val/test stratified, seed 42
- [x] Khởi tạo repo, `pyproject.toml`, cấu trúc thư mục theo `01-architecture-design.md` §7
- [x] Copy `AGENTS.md`, `docs/05-agent-coding-rules.md`, `docs/06-scope-guard.md` vào repo

---

## Task KHÔNG được làm tuần này

- Viết bất kỳ retrieval strategy nào
- Port detector hoặc judge
- Dựng ClickHouse schema
- Viết dashboard
- Bất cứ thứ gì thuộc Tuần 2 trở đi

---

## Definition of Done

- [x] Biết chính xác có bao nhiêu fault window có nhãn root-cause
      → **704 fault window / 95.660 cửa sổ, từ 101/101 lần tiêm lỗi**
- [x] `data/splits/{dev,val,test}.json` được commit
      → dev 19.316 · val 28.898 · test 46.849 cửa sổ, seed 42
- [x] Nếu thiếu nhãn: đã ra quyết định và ghi vào `docs/experiment-log.md`
      → không thiếu nhãn; các quyết định QĐ-001 … QĐ-006 đã ghi

---

## Cổng chặn

**QUA.** Nezha có sẵn nhãn root-cause mức pod cho cả 101 lần tiêm lỗi, ánh xạ
100% lên tên service, trace có đủ `SpanID`/`ParentID`. Không phải gán nhãn tay,
không phải đổi dataset. Được phép sang Tuần 2.

---

## Ghi chú trong tuần

**Lỗi múi giờ trong dataset (QĐ-002).** Nezha ghi mỗi mốc thời gian hai lần và
hai bản không khớp: ngày 2023-01-29 có 24/28 lần tiêm lỗi bị lệch 8 tiếng ở cột
epoch, và một file metric của `adservice` lệch 6,3 năm. Giai đoạn 1 dùng cột
epoch nên đã âm thầm mất 26 lần tiêm lỗi và 177 fault window. Giai đoạn 2 join
theo cột wall-clock.

**Việc này thay đổi cách chạy cổng chặn Tuần 3.** Baseline Giai đoạn 1
(Precision 0.32, FPR 0.046) đo trên nhãn cũ, nên Tuần 3 phải chạy hai lần:
`--time-source epoch` để đối chiếu port đúng/sai, rồi `--time-source wall` để
lấy con số báo cáo chính thức. Chi tiết trong `docs/experiment-log.md` QĐ-002.

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

## Tuần sau (Tuần 2) — chưa được bắt đầu

Hạ tầng và port GĐ1: `docker-compose` profiles, `infra/*/init.sql` theo tài liệu
`03`, `packages/schemas/`, port replayer và detector. Việc đầu tiên nên làm là
bọc `scripts/nezha_windows.py` thành `packages/schemas/loaders.py` để không code
nào phải tự parse CSV Nezha lần nữa.
