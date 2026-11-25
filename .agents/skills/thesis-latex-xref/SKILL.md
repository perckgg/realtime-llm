---
name: thesis-latex-xref
description: >-
  Apply clickable hyperlink macros (C1–C5, H0–H5, RQ1–RQ5, CTAV, and core terms)
  and run automated LaTeX quality audits across active thesis chapters in
  docs/drafts/Internship2_HK262/. Use after adding a new chapter, editing prose,
  or before building main.pdf to verify zero dead links, zero raw code file paths,
  proper table fonts, citation parity, and style-guide compliance.
---

# Thesis LaTeX Cross-Reference & Audit

This skill automates hyperlink synchronization and static quality checks for all active chapters included by `docs/drafts/Internship2_HK262/main.tex`.

## Workflow

### Step 1: Preview or Apply Clickable Cross-Reference Macros
Run [apply_xref.py](./scripts/apply_xref.py) (it automatically discovers every active `\input{Sections/...}` from `main.tex`, skipping `title.tex`):

```powershell
# Dry-run across all active chapters
.\.venv\Scripts\python.exe .agents\skills\thesis-latex-xref\scripts\apply_xref.py

# Apply to all active chapters (or restrict to specific files)
.\.venv\Scripts\python.exe .agents\skills\thesis-latex-xref\scripts\apply_xref.py --apply
.\.venv\Scripts\python.exe .agents\skills\thesis-latex-xref\scripts\apply_xref.py --apply --files Ch8_TongKet.tex KeHoach_ThucHien.tex
```

The parser automatically skips comments, math environments (`$...$`, `equation`, `align`), `\caption[...]`, `\label`, `\ref`, `\cite`, `\code`, `\texttt`, `\includegraphics`, `\url`, and existing macro arguments.

### Step 2: Run the 7-Point LaTeX Source Audit
Run [audit_tex.py](./scripts/audit_tex.py):

```powershell
.\.venv\Scripts\python.exe .agents\skills\thesis-latex-xref\scripts\audit_tex.py
```

It checks:
1. **Hyperlink symmetry**: every `\hyperlink` / `\comp` / `\hyp` / `\rqref` / `\term` / `\CTAV` has a matching `\xtarget` / `\hypertarget`.
2. **No raw source paths in Ch1–Ch9**: flags `*.py`, `*.tsx`, `services/...`, `packages/...`, `eval/configs/...` outside Appendix `Phuluc_CTAV.tex`.
3. **Table typography**: flags any standalone `\footnotesize`, `\scriptsize`, or `\small` inside `table` environments (should use `\tblfont` or `\tblfontwide`).
4. **Style-guide guardrails**: flags forbidden terms (`GĐ1`, `GĐ2`, `Phase 1/2/3`, `kế thừa từ`, `đột phá`, `vượt trội`, `hoàn hảo`, `Crucial finding`).
5. **PDF bookmark safety**: flags unescaped `$...$` math inside `\section`, `\subsection`, or `\subsubsection` headings (should wrap in `\texorpdfstring`).
6. **Citation parity**: verifies every `\cite{...}` matches a `\bibitem{...}` in `main.tex` (0 missing, 0 unused).
7. **Figure captions & spacing**: verifies every `figure` in active chapters has `\vspace` before `\caption` (preventing `aboveskip=-9pt` overlap) and that each figure caption does not exceed 1 sentence (excluding `(Nguồn: ...)`).

### Step 3: Fix Flagged Issues & Rebuild
Resolve any findings reported by `audit_tex.py`, then compile and verify the final PDF using the `thesis-latex-build` skill.
