# Tuần hiện tại

> Cập nhật file này vào đầu mỗi tuần. Agent đọc file này để biết được phép làm gì.
> Chỉ chép phần tuần hiện tại từ `04-implementation-roadmap.md` vào đây.

---

## Tuần: 1 / 24
## Ngày bắt đầu: ______
## Giai đoạn: Tháng 1 — Nền tảng và kiểm chứng dữ liệu

---

## Mục tiêu tuần này

**Kiểm tra dữ liệu trước, code sau.** Tuần này KHÔNG viết code pipeline.

Rủi ro lớn nhất của toàn đề tài nằm ở đây: nếu Nezha không có nhãn `root_cause_service`, toàn bộ Nhánh B không đo được Hit@1/Hit@3.

---

## Task được phép làm

- [ ] `scripts/verify_labels.py` — kiểm tra nhãn root-cause của Nezha
- [ ] Kiểm tra trace có đủ `span_id` / `parent_span_id` để dựng call chain
- [ ] Viết `docs/label-audit.md` (một trang, có bảng số liệu)
- [ ] `scripts/make_splits.py` — chia dev/val/test stratified, seed 42
- [ ] Khởi tạo repo, `pyproject.toml`, cấu trúc thư mục theo `01-architecture-design.md` §7
- [ ] Copy `AGENTS.md`, `docs/05-agent-coding-rules.md`, `docs/06-scope-guard.md` vào repo

---

## Task KHÔNG được làm tuần này

- Viết bất kỳ retrieval strategy nào
- Port detector hoặc judge
- Dựng ClickHouse schema
- Viết dashboard
- Bất cứ thứ gì thuộc Tuần 2 trở đi

---

## Definition of Done

- [ ] Biết chính xác có bao nhiêu fault window có nhãn root-cause
- [ ] `data/splits/{dev,val,test}.json` được commit
- [ ] Nếu thiếu nhãn: đã ra quyết định (gán tay / đổi dataset) và ghi vào `docs/experiment-log.md`

---

## Cổng chặn

**Không sang Tuần 2 nếu chưa trả lời được câu hỏi về nhãn.**

---

## Ghi chú trong tuần

_(ghi lại vướng mắc, quyết định, phát hiện bất ngờ)_
