---
name: thesis-latex-build
description: >-
  Compile docs/drafts/Internship2_HK262/main.tex into main.pdf (online PDF mode or
  --print black-link mode), handle MiKTeX / Windows PDF lock issues, and audit
  main.log for undefined references, dead hyperlinks, PDF bookmark warnings, and
  Overfull hbox table overflows. Use whenever building or troubleshooting main.pdf.
---

# Thesis LaTeX Build & Log Audit (Internship2_HK262)

Use this runbook to compile `docs/drafts/Internship2_HK262/main.pdf` cleanly on Windows (MiKTeX) and verify zero reference, hyperlink, or layout regressions.

## 1. Standard Build Commands

Run via `docs\drafts\Internship2_HK262\build.bat` (delegates to `build.ps1`, auto-runs Pass 3 if cross-references or outlines have not converged, preserves SyncTeX):

```powershell
# Online PDF (default: clickable navy links, auto 2–3 passes)
cmd /c "docs\drafts\Internship2_HK262\build.bat --no-pause"

# Clean rebuild (removes .aux/.toc/.lof/.lot/.out/.log first)
cmd /c "docs\drafts\Internship2_HK262\build.bat --clean --no-pause"

# Print edition (all links black via \def\PRINTMODE{1}, without modifying main.tex)
cmd /c "docs\drafts\Internship2_HK262\build.bat --print --no-pause"
```

> **Windows Sandbox note**: MiKTeX reads its user configuration database under `%APPDATA%\MiKTeX`. If a sandboxed run fails with *"It seems that this is a fresh TeX installation"*, retry the exact `build.bat` command with `BypassSandbox: true`.

## 2. Handling Locked `main.pdf` / `main.aux`

- If `build.ps1` reports `File main.pdf đang bị khóa`, the user has `main.pdf` open in a PDF reader.
  - To verify compilation **without** disturbing the open PDF, compile to a temporary jobname (`pdflatex -synctex=0 -interaction=nonstopmode -file-line-error -jobname=main_verify main.tex`), audit `main_verify.log`, then delete `main_verify.*`.
- If `pdflatex` reports `I can't write on file 'main.aux'`, VS Code LaTeX Workshop auto-build-on-save may still be writing `main.aux`. Wait a few seconds until no `pdflatex` process is running and retry.

## 3. Post-Build Log Audit

Run [audit_log.py](./scripts/audit_log.py) after every build:

```powershell
.\.venv\Scripts\python.exe .claude\skills\thesis-latex-build\scripts\audit_log.py
```

### Pass Criteria
- `Undefined refs/cites`: **0**
- `Dead hyperlinks` (`has been referenced but does not exist`): **0**
- `PDF string warnings` (`Token not allowed in a PDF string`): **0**
- `Still needs rerun`: **False**
- `Overfull \hbox in alignment` (table spilling past margin): **0**

If any table shows `Overfull \hbox` >= 8pt:
- Widen the narrow `p{...}` column or insert `\allowbreak` inside long `\code{...}` tokens.
- For dense 7–8 column numeric CI95 tables, use `\tblfontwide` (or `\fontsize{8.5pt}{11.5pt}\selectfont` + `\setlength{\tabcolsep}{2pt}`).
