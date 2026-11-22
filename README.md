# AIOps RCA Platform — Giai đoạn 2

> **(A)** Đề xuất và chứng minh **CTAV** — thẩm định cảnh báo có nhận biết topology, được
> hiệu chỉnh theo nguồn gốc bằng chứng — giữ mức tăng recall của topology mà không làm
> tăng báo động giả so với BM25 trong cùng ngân sách LLM; **(B)** dùng CTAV làm nền cho
> tác tử RCA định vị service gốc; cả hai chạy trên một platform demo được.
>
> Giải pháp và cách chứng minh: [`docs/Final_Thesis_Phase2/08-research-direction.md`](docs/Final_Thesis_Phase2/08-research-direction.md).

Đây là repo nghiên cứu cho luận văn thạc sĩ, không phải sản phẩm thương mại. Chi tiết
đầy đủ: xem [`AGENTS.md`](AGENTS.md) và bộ tài liệu ở
[`docs/Final_Thesis_Phase2/00-INDEX.md`](docs/Final_Thesis_Phase2/00-INDEX.md).

## Trạng thái hiện tại

Đang ở **mốc M1** (xem [`docs/CURRENT-MILESTONE.md`](docs/CURRENT-MILESTONE.md)). Đã xong M0
([báo cáo](docs/milestones/M0-nen-tang.md)): kiểm chứng nhãn Nezha, split dev/val/test, hạ tầng ClickHouse + Postgres, port
replayer và detector. Retrieval, judge, harness, RCA agent, API chưa có. Lịch đã xếp lại
ngày 2026-10-18 và tổ chức theo cột mốc (QĐ-011..014 trong `docs/experiment-log.md`).

```text
services/     replayer, detector, retrieval, judge, rca_agent, api, web
packages/     schemas, graph, llm, storage
eval/         harness, configs, results
infra/        clickhouse/, postgres/ (docker-compose.yml dev/full)
data/         nezha (raw, gitignored), splits (committed), llm_cache (gitignored)
legacy/       toàn bộ code + kết quả Giai đoạn 1 (Internship 1), nguyên trạng
archive/      phase1_extra — dataset/setup phụ của GĐ1, ngoài phạm vi GĐ2
```

## Kế thừa từ Giai đoạn 1

Code GĐ1 đầy đủ nằm trong [`legacy/`](legacy/README.md) — **port, không viết lại**:
streaming replay, Isolation Forest detector, BM25 hybrid retrieval, LLM-as-a-Judge,
local-first routing, LLM response cache. Context Rescue sẽ được viết lại thành công
thức có tham số (α, β, γ, τ). Xem `legacy/README.md` để chạy lại code GĐ1 (yêu cầu chạy
với `legacy/` làm working directory).

## Bắt đầu

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"
```

Tái lập kết quả M0:

```bash
bash scripts/download_nezha.sh          # nếu chưa có data/Nezha/
python scripts/verify_labels.py         # -> docs/label-audit.md  (~80 s)
python scripts/make_splits.py           # -> data/splits/*.json
python scripts/make_splits.py --check   # xác nhận split không đổi
python -m pytest tests/ -q              # 8 test canh split
```

## Dashboard (dựng trước tiến độ)

`services/web/` đã có bản MVP bốn màn hình — Timeline, Alert detail, Incident
detail, Experiment comparison — chạy trên **dữ liệu giả** vì pipeline chưa chạy.
Roadmap xếp việc nối dữ liệu thật vào mốc M10; dựng sớm để chốt bố cục và để bốn màn hình
ràng buộc ngược lại xem `services/api` phải trả những gì. Lý do và ranh giới:
`docs/experiment-log.md` QĐ-007.

```bash
cd services/web && npm install && npm run dev    # http://localhost:5173
```

Việc tiếp theo là mốc M1 — xem `docs/CURRENT-MILESTONE.md` và `docs/Final_Thesis_Phase2/04-implementation-roadmap.md`.

## Biên soạn báo cáo LaTeX trên VS Code (SyncTeX)

Mã nguồn báo cáo nằm ở `docs/drafts/Internship2_HK262/` (`main.tex`, các chương trong `Sections/`).

1. **Cài đặt công cụ (làm một lần trên máy mới):**
   - Cài **MiKTeX** (Windows) có `pdflatex` trên `PATH` (hoặc ở `%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64`).
   - Cài extension **LaTeX Workshop** (`James-Yu.latex-workshop`) trong VS Code.
   - Mở repo bằng VS Code: cấu hình SyncTeX double-click đã được lưu sẵn tại `.vscode/settings.json` (`"latex-workshop.view.pdf.internal.synctex.keybinding": "double-click"`).
2. **Biên dịch PDF kèm SyncTeX (`-synctex=1`):**
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File docs\drafts\Internship2_HK262\build.ps1
   # Hoặc double-click / chạy: docs\drafts\Internship2_HK262\build.bat
   ```
   Script tự chạy 2 pass `pdflatex -shell-escape -synctex=1`, xuất `main.pdf` và `main.synctex.gz` cùng thư mục (không xóa `*.synctex.gz`).
3. **Nhảy qua lại hai chiều giữa PDF và `.tex`:**
   - Mở `docs/drafts/Internship2_HK262/main.pdf` bằng **LaTeX Workshop Internal PDF Viewer** (tổ hợp `Ctrl+Alt+V` từ `main.tex`).
   - **PDF → `.tex`:** **double-click** vào bất kỳ dòng nào trên PDF để nhảy thẳng về đúng file và dòng trong `Sections/`.
   - **`.tex` → PDF:** nhấn `Ctrl+Alt+J` tại dòng đang soạn.
   - *Lưu ý:* đóng `main.pdf` trên trình đọc ngoài (Acrobat/Edge) trước khi chạy `build.ps1` để tránh lỗi khóa file; dùng Internal PDF Viewer của VS Code thì không bị khóa.
