# Cross-Reference Macro Cheatsheet (`macros_xref.tex`)

All macros below are `\DeclareRobustCommand` + `\texorpdfstring`, safe inside `\section`, `\subsection`, `\subsubsection`, `\caption`, `\textbf`, and `tabularx`.

## 1. Component Macros (`C1`–`C5`)

| Macro | Display | Default Target (`comp:`) | Ch4 Detail Target (`def:`) | Short Name (first mention per chapter) |
|---|---|---|---|---|
| `\comp{C1}` | C1 | `comp:C1` (front-matter table) | `def:C1` (`sec:ch4-c1`) | truy xuất lai BM25--topology |
| `\comp{C2}` | C2 | `comp:C2` (front-matter table) | `def:C2` (`sec:ch4-policy`) | ngưỡng bất đối xứng (đã loại) |
| `\comp{C3}` | C3 | `comp:C3` (front-matter table) | `def:C3` (`sec:ch4-policy`) | neo bằng chứng |
| `\comp{C4}` | C4 | `comp:C4` (front-matter table) | `def:C4` (`sec:ch4-c4`) | định tuyến hai tầng (đã loại) |
| `\comp{C5}` | C5 | `comp:C5` (front-matter table) | `def:C5` (`sec:ch4-detector`) | Rescue Score (chỉ là ablation) |

## 2. Hypotheses & Research Questions

- `\hyp{H0}` .. `\hyp{H5}` → jumps to `def:H0`..`def:H5` in `tab:h0-h5` (`Ch5_ThucNghiemVaDanhGia.tex`).
- `\rqref{RQ1}` .. `\rqref{RQ5}` → jumps to `def:RQ1`..`def:RQ5` in *Mục tiêu cụ thể* (`C1_TongQuanDeTai.tex`).

## 3. Core Acronyms & Terms (`\term{<key>}{<display>}`)

| Key (`term:<key>`) | Typical Usage | Target Location |
|---|---|---|
| `CTAV` | `\CTAV{}` | *Danh mục từ viết tắt* (`main.tex`) |
| `BM25` | `\term{BM25}{BM25}` | *Danh mục từ viết tắt* (`main.tex`) |
| `ARR` | `\term{ARR}{ARR}` | *Danh mục từ viết tắt* (`main.tex`) |
| `FPR` | `\term{FPR}{FPR}` | *Danh mục từ viết tắt* (`main.tex`) |
| `RAG` | `\term{RAG}{RAG}` | *Danh mục từ viết tắt* (`main.tex`) |
| `RCA` | `\term{RCA}{RCA}` | *Danh mục từ viết tắt* (`main.tex`) |
| `HitK` | `\term{HitK}{Hit@1}`, `\term{HitK}{Hit@3}`, `\term{HitK}{Hit@k}` | *Danh mục từ viết tắt* (`main.tex`) |
| `FusionScore` | `\term{FusionScore}{Fusion Score}` | *Danh mục thành phần và thuật ngữ hệ thống* (`main.tex`) |
| `RescueScore` | `\term{RescueScore}{Rescue Score}` | *Danh mục thành phần và thuật ngữ hệ thống* (`main.tex`) |
| `ConfirmationBias` | `\term{ConfirmationBias}{thiên lệch xác nhận}` | *Danh mục thành phần và thuật ngữ hệ thống* (`main.tex`) |
| `TelemetryWindow` | `\term{TelemetryWindow}{cửa sổ có telemetry}` | *Danh mục thành phần và thuật ngữ hệ thống* (`main.tex`) |

Additional anchors defined in *Danh mục từ viết tắt* (available via `\term{<key>}{<label>}` if needed, intentionally not auto-linked in numeric tables to avoid visual clutter): `API`, `CI`, `FN`, `FP`, `IF`, `JSON`, `LLM`, `TN`, `TP`.

## 4. Placing New Anchors

Always use `\xtarget{<id>}` (defined as `\raisebox{\ht\strutbox}[0pt][0pt]{\hypertarget{#1}{}}`) so PDF viewers scroll cleanly above the target row without altering table row height.
