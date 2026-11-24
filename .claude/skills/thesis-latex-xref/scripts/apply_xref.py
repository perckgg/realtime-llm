"""Context-aware LaTeX cross-reference macro applier for Internship2_HK262.

Dynamically discovers active \\input{Sections/...} files from main.tex (excluding title.tex)
unless explicit --files are passed. Safe around comments, math, \\label, \\ref, \\cite,
\\code, \\texttt, \\includegraphics, and \\caption[short].
"""

from __future__ import annotations

import argparse
import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]
THESIS_DIR = REPO_ROOT / "docs" / "drafts" / "Internship2_HK262"
MAIN_TEX = THESIS_DIR / "main.tex"
SECTIONS_DIR = THESIS_DIR / "Sections"

SKIP_CMD_ARGS: dict[str, int] = {
    "label": 1,
    "ref": 1,
    "eqref": 1,
    "pageref": 1,
    "cite": 1,
    "bibitem": 1,
    "includegraphics": 1,
    "graphicspath": 1,
    "input": 1,
    "include": 1,
    "code": 1,
    "texttt": 1,
    "splitname": 1,
    "url": 1,
    "href": 2,
    "hypertarget": 2,
    "hyperlink": 2,
    "hyperref": 1,
    "xtarget": 1,
    "comp": 1,
    "hyp": 1,
    "rqref": 1,
    "term": 2,
    "begin": 1,
    "end": 1,
    "rowcolor": 1,
    "cellcolor": 1,
    "textcolor": 1,
    "color": 1,
    "definecolor": 3,
    "newcolumntype": 2,
    "setcounter": 2,
    "setlength": 2,
    "addcontentsline": 3,
    "texorpdfstring": 2,
}

MATH_ENVS = {
    "equation",
    "equation*",
    "align",
    "align*",
    "gather",
    "gather*",
    "multline",
    "multline*",
    "lstlisting",
    "verbatim",
    "alltt",
}

REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?<![A-Za-z0-9_\\])(C[1-5])(?![A-Za-z0-9_])"), r"\\comp{\1}"),
    (re.compile(r"(?<![A-Za-z0-9_\\])(H[0-5])(?![A-Za-z0-9_])"), r"\\hyp{\1}"),
    (re.compile(r"(?<![A-Za-z0-9_\\])(RQ[1-5])(?![A-Za-z0-9_])"), r"\\rqref{\1}"),
    (re.compile(r"(?<![A-Za-z0-9_\\])CTAV(?![A-Za-z0-9_])"), r"\\CTAV{}"),
    (re.compile(r"(?<![A-Za-z0-9_\\])Fusion Score(?![A-Za-z0-9_])"), r"\\term{FusionScore}{Fusion Score}"),
    (re.compile(r"(?<![A-Za-z0-9_\\])Rescue Score(?![A-Za-z0-9_])"), r"\\term{RescueScore}{Rescue Score}"),
    (re.compile(r"(?<!\\)\b([Tt])hiên lệch xác nhận\b"), r"\\term{ConfirmationBias}{\1hiên lệch xác nhận}"),
    (re.compile(r"(?<!\\)\b([Cc])ửa sổ có telemetry\b"), r"\\term{TelemetryWindow}{\1ửa sổ có telemetry}"),
    (re.compile(r"(?<![A-Za-z0-9_\\])BM25(?![A-Za-z0-9_])"), r"\\term{BM25}{BM25}"),
    (re.compile(r"(?<![A-Za-z0-9_\\])ARR(?![A-Za-z0-9_])"), r"\\term{ARR}{ARR}"),
    (re.compile(r"(?<![A-Za-z0-9_\\])FPR(?![A-Za-z0-9_])"), r"\\term{FPR}{FPR}"),
    (re.compile(r"(?<![A-Za-z0-9_\\])RAG(?![A-Za-z0-9_])"), r"\\term{RAG}{RAG}"),
    (re.compile(r"(?<![A-Za-z0-9_\\])RCA(?![A-Za-z0-9_])"), r"\\term{RCA}{RCA}"),
    (re.compile(r"(?<![A-Za-z0-9_\\])(Hit@(?:1|3|k))(?![A-Za-z0-9_])"), r"\\term{HitK}{\1}"),
]


def discover_active_sections(main_tex: pathlib.Path = MAIN_TEX) -> list[pathlib.Path]:
    """Return active Sections/*.tex files referenced by uncommented \\input{...} in main.tex."""
    found: list[pathlib.Path] = []
    for line in main_tex.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("%"):
            continue
        code = re.sub(r"(?<!\\)%.*$", "", line)
        for m in re.finditer(r"\\input\{([^}]+)\}", code):
            rel = m.group(1).strip()
            if not rel.startswith("Sections/"):
                continue
            name = rel.split("/", 1)[1]
            if not name.endswith(".tex"):
                name += ".tex"
            if name == "title.tex":
                continue
            path = SECTIONS_DIR / name
            if path.exists() and path not in found:
                found.append(path)
    return found


def _consume_balanced(text: str, pos: int, open_ch: str, close_ch: str) -> int:
    depth = 0
    n = len(text)
    i = pos
    while i < n:
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def _transform_plain(chunk: str, stats: dict[str, int]) -> str:
    out = chunk
    for pat, repl in REPLACEMENTS:
        out, count = pat.subn(repl, out)
        if count:
            stats[pat.pattern] = stats.get(pat.pattern, 0) + count
    return out


def transform_tex(text: str) -> tuple[str, dict[str, int]]:
    out: list[str] = []
    buf: list[str] = []
    stats: dict[str, int] = {}
    n = len(text)
    i = 0

    def flush() -> None:
        if buf:
            out.append(_transform_plain("".join(buf), stats))
            buf.clear()

    while i < n:
        ch = text[i]

        if ch == "%":
            flush()
            end = text.find("\n", i)
            if end == -1:
                out.append(text[i:])
                i = n
            else:
                out.append(text[i : end + 1])
                i = end + 1
            continue

        if ch == "$":
            flush()
            if i + 1 < n and text[i + 1] == "$":
                j = text.find("$$", i + 2)
                end = n if j == -1 else j + 2
                out.append(text[i:end])
                i = end
            else:
                j = i + 1
                while j < n:
                    if text[j] == "\\":
                        j += 2
                        continue
                    if text[j] == "$":
                        j += 1
                        break
                    j += 1
                out.append(text[i:j])
                i = j
            continue

        if ch == "\\":
            if i + 1 < n and not text[i + 1].isalpha():
                nxt = text[i + 1]
                if nxt == "(":
                    flush()
                    j = text.find(r"\)", i + 2)
                    end = n if j == -1 else j + 2
                    out.append(text[i:end])
                    i = end
                    continue
                if nxt == "[":
                    flush()
                    j = text.find(r"\]", i + 2)
                    end = n if j == -1 else j + 2
                    out.append(text[i:end])
                    i = end
                    continue
                flush()
                out.append(text[i : i + 2])
                i += 2
                continue

            j = i + 1
            while j < n and text[j].isalpha():
                j += 1
            cmd = text[i + 1 : j]
            if j < n and text[j] == "*":
                j += 1

            if cmd == "begin" and j < n and text[j] == "{":
                env_end = _consume_balanced(text, j, "{", "}")
                env_name = text[j + 1 : env_end - 1].strip()
                flush()
                if env_name in MATH_ENVS:
                    marker = f"\\end{{{env_name}}}"
                    end_pos = text.find(marker, env_end)
                    if end_pos != -1:
                        out.append(text[i : end_pos + len(marker)])
                        i = end_pos + len(marker)
                        continue
                out.append(text[i:env_end])
                i = env_end
                continue

            if cmd == "caption":
                flush()
                k = j
                while k < n and text[k] in " \t":
                    k += 1
                if k < n and text[k] == "[":
                    opt_end = _consume_balanced(text, k, "[", "]")
                    out.append(text[i:opt_end])
                    i = opt_end
                    continue
                out.append(text[i:j])
                i = j
                continue

            if cmd in SKIP_CMD_ARGS:
                flush()
                k = j
                while True:
                    ws = k
                    while ws < n and text[ws] in " \t":
                        ws += 1
                    if ws < n and text[ws] == "[":
                        k = _consume_balanced(text, ws, "[", "]")
                    else:
                        break
                for _ in range(SKIP_CMD_ARGS[cmd]):
                    ws = k
                    while ws < n and text[ws] in " \t":
                        ws += 1
                    if ws < n and text[ws] == "{":
                        k = _consume_balanced(text, ws, "{", "}")
                    else:
                        break
                if cmd == "xtarget":
                    m = re.match(r"\\textbf\{(H[0-5]|C[1-5])\}", text[k:])
                    if m:
                        k += m.end()
                out.append(text[i:k])
                i = k
                continue

            flush()
            out.append(text[i:j])
            i = j
            continue

        buf.append(ch)
        i += 1

    flush()
    return "".join(out), stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply thesis hyperlink macros safely.")
    parser.add_argument("--apply", action="store_true", help="Write changes in place (default is dry-run).")
    parser.add_argument("--files", nargs="*", help="Specific filenames under Sections/ (default: all active).")
    args = parser.parse_args()

    if args.files:
        targets = [SECTIONS_DIR / fn for fn in args.files]
    else:
        targets = discover_active_sections()

    grand_total = 0
    for path in targets:
        if not path.exists():
            print(f"[SKIP] Missing file: {path}")
            continue
        orig = path.read_text(encoding="utf-8")
        new, stats = transform_tex(orig)
        n_changes = sum(stats.values())
        grand_total += n_changes
        print(f"{path.name:32s}: {n_changes:4d} replacements")
        if args.apply and new != orig:
            path.write_text(new, encoding="utf-8")
    mode = "APPLIED" if args.apply else "DRY RUN"
    print(f"TOTAL: {grand_total} replacements ({mode})")


if __name__ == "__main__":
    main()
