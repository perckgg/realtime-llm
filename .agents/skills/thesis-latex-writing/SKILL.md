---
name: thesis-latex-writing
description: >-
  Write, edit, tighten, or review LaTeX chapters of the AIOps RCA / CTAV master thesis
  under docs/drafts/Internship2_HK262/. Use whenever authoring new sections, revising
  prose or tables, standardizing Vietnamese technical terminology, enforcing the thesis
  style guide, or checking compliance before compiling main.pdf.
---

# Thesis LaTeX Writing (Internship2_HK262)

Follow this workflow whenever drafting, editing, or reviewing LaTeX files in
`docs/drafts/Internship2_HK262/`.

## 1. Authoritative Style Rules

Read the project's single source of truth for tone, structure, and scientific honesty before making substantive prose edits:

- `docs/drafts/style-guide-luan-van.md`

Non-negotiable rules to enforce on every edit:
- **Unified thesis framing**: never write `GĐ1`, `GĐ2`, `GĐ3`, `Phase 1/2/3`, `giai đoạn`, `kế thừa từ`, or `phiên bản trước`.
- **Scientific honesty**: report negative results directly (`C2`, `C4` eliminated on `val`; `C5` ablation-only; `H2` / `H5` not accepted as registered). Never claim "better" when 95% CI includes 0.
- **No promotional buzzwords**: avoid *đột phá*, *vượt trội*, *hoàn hảo*, *giải quyết triệt để*, *state-of-the-art*, *Crucial finding*.
- **Missing numbers**: mark with `\CHO{M*}{mô tả}` rather than guessing.
- **No raw source paths in thesis prose (Ch1–Ch9)**: never write `*.py`, `*.tsx`, `services/...`, `packages/...`, or `eval/configs/...` in chapter prose or architecture tables. Refer to logical layers and architectural modules instead (CLI/artifact paths belong only in Appendix `Phuluc_CTAV.tex`).

## 2. Mandatory LaTeX Conventions

### Cross-Reference & Hyperlink Macros (`macros_xref.tex`)
All clickable macros are defined in `docs/drafts/Internship2_HK262/macros_xref.tex`. Consult [xref-cheatsheet.md](./references/xref-cheatsheet.md) for the exact macro names and target keys.

- Always use `\comp{C1}`..`\comp{C5}`, `\hyp{H0}`..`\hyp{H5}`, `\rqref{RQ1}`..`\rqref{RQ5}`, `\CTAV{}`, and `\term{<key>}{<label>}` in body text and tables.
- On the **first mention of each `C1`–`C5` in every chapter**, include its concise Vietnamese function in parentheses (for printed-paper readability), e.g., `\comp{C1} (truy xuất lai \term{BM25}{BM25}--topology)`.
- Never wrap identifiers inside `\label`, `\ref`, `\cite`, `\code`, `\texttt`, `\includegraphics`, or math mode `$...$`.
- Any math or formatting inside `\section`, `\subsection`, or `\subsubsection` must use `\texorpdfstring{...}{...}` so PDF bookmarks stay warning-free.

### Table Typography
Because `main.tex` uses `\documentclass{article}` (10pt base) with `13pt` body text, `\footnotesize` (8pt) and `\scriptsize` (7pt) render unreadably small.

- Use **`\tblfont`** (`10.5pt`) + `\tblsetup` for all standard tables.
- Use **`\tblfontwide`** (`9pt`) + `\tblsetup` only for dense 7–8 column numeric CI95 tables.
- Do **not** use bare `\footnotesize`, `\scriptsize`, or `\small` on tables.
- Use `\allowbreak` inside long `\code{...}` identifiers in narrow columns to prevent `Overfull \hbox`.

### Citations
- Citations follow IEEE style inside `main.tex` (`\begin{thebibliography}`).
- Every `\cite{key}` must match a `\bibitem{key}` in `main.tex`, with zero unused or missing entries.

## 3. Verification Checklist After Editing

After editing any chapter:
1. Run the xref & quality audit from the `thesis-latex-xref` skill (`audit_tex.py`, and `apply_xref.py --apply` if new prose added plain `C1`–`C5` / `H0`–`H5` / terms).
2. Compile and verify the PDF using the `thesis-latex-build` skill.
