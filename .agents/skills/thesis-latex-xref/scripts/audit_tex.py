"""7-point static quality audit for docs/drafts/Internship2_HK262/ LaTeX sources."""

from __future__ import annotations

import re
import sys

from apply_xref import MAIN_TEX, THESIS_DIR, _consume_balanced, discover_active_sections

FORBIDDEN_STYLE = re.compile(
    r"\b(?:GĐ[123]|Phase\s+[123]|kế thừa từ|đột phá|vượt trội|hoàn hảo|giải quyết triệt để|Crucial finding)\b",
    re.IGNORECASE,
)
RAW_CODE_PATH = re.compile(
    r"(\b[A-Za-z0-9_\\-]+\.(?:py|ya?ml|tsx?|sql|sh|bat)\b|(?:services|packages|scripts|tests|eval/configs)/[A-Za-z0-9_\\.-]*)"
)


def strip_comment(line: str) -> str:
    if line.lstrip().startswith("%"):
        return ""
    return re.sub(r"(?<!\\)%.*$", "", line)


def strip_texorpdfstring(s: str) -> str:
    out: list[str] = []
    i = 0
    n = len(s)
    marker = r"\texorpdfstring"
    while i < n:
        idx = s.find(marker, i)
        if idx == -1:
            out.append(s[i:])
            break
        out.append(s[i:idx])
        k = idx + len(marker)
        for _ in range(2):
            while k < n and s[k] in " \t":
                k += 1
            if k < n and s[k] == "{":
                k = _consume_balanced(s, k, "{", "}")
        i = k
    return "".join(out)


def main() -> int:
    sections = discover_active_sections()
    all_files = [MAIN_TEX, THESIS_DIR / "macros_xref.tex", *sections]

    issues = 0

    # 1. Hyperlink <-> Target symmetry
    targets: set[str] = set()
    links: set[str] = set()
    for path in all_files:
        if not path.exists():
            continue
        text = "\n".join(strip_comment(line) for line in path.read_text(encoding="utf-8").splitlines())
        targets.update(re.findall(r"\\(?:xtarget|hypertarget)\{([^}]+)\}", text))
        links.update(re.findall(r"\\hyperlink\{([^}]+)\}", text))
        links.update("comp:" + m for m in re.findall(r"\\comp\{([^}]+)\}", text))
        links.update("def:" + m for m in re.findall(r"\\hyp\{([^}]+)\}", text))
        links.update("def:" + m for m in re.findall(r"\\rqref\{([^}]+)\}", text))
        links.update("term:" + m for m in re.findall(r"\\term\{([^}]+)\}", text))
        if r"\CTAV" in text:
            links.add("term:CTAV")
    targets = {t for t in targets if "#" not in t}
    links = {k for k in links if "#" not in k}
    missing_targets = sorted(links - targets)
    print(f"[1/7] Hyperlink symmetry : {len(links)} links, {len(targets)} targets, {len(missing_targets)} missing")
    for m in missing_targets:
        print(f"      ERROR missing target: {m}")
        issues += 1

    # 2. Raw code file paths in Ch1-Ch9 (exclude Appendix Phuluc_CTAV.tex)
    code_hits: list[str] = []
    for path in sections:
        if path.name == "Phuluc_CTAV.tex":
            continue
        for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            c = strip_comment(raw)
            c = re.sub(r"\\includegraphics(?:\[[^\]]*\])?\{[^}]*\}", "", c)
            c = re.sub(r"\\url\{[^}]*\}", "", c)
            ms = RAW_CODE_PATH.findall(c)
            if ms:
                code_hits.append(f"{path.name}:{i}: {ms}")
    print(f"[2/7] Raw code paths     : {len(code_hits)} findings outside Appendix")
    for h in code_hits[:15]:
        print(f"      WARN  {h}")
    issues += len(code_hits)

    # 3. Bare small table fonts
    small_tbl_hits: list[str] = []
    for path in sections:
        in_table = False
        for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            c = strip_comment(raw)
            if r"\begin{table" in c:
                in_table = True
            if in_table and re.match(r"^\s*\\(?:footnotesize|scriptsize|small)\s*$", c):
                small_tbl_hits.append(f"{path.name}:{i}: {c.strip()}")
            if r"\end{table" in c:
                in_table = False
    print(f"[3/7] Small table fonts  : {len(small_tbl_hits)} tables not using \\tblfont/\\tblfontwide")
    for h in small_tbl_hits[:15]:
        print(f"      WARN  {h}")
    issues += len(small_tbl_hits)

    # 4. Style-guide forbidden phrases
    style_hits: list[str] = []
    for path in sections:
        for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            c = strip_comment(raw)
            ms = FORBIDDEN_STYLE.findall(c)
            if ms:
                style_hits.append(f"{path.name}:{i}: {ms}")
    print(f"[4/7] Style-guide check  : {len(style_hits)} forbidden-term matches")
    for h in style_hits[:15]:
        print(f"      WARN  {h}")
    issues += len(style_hits)

    # 5. Unwrapped math in headings (causes hyperref PDF string warnings)
    heading_math: list[str] = []
    for path in sections:
        for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            c = strip_comment(raw)
            m = re.search(r"\\(?:sub)*section\*?\{(.+)\}", c)
            if m:
                body = strip_texorpdfstring(m.group(1))
                if "$" in body:
                    heading_math.append(f"{path.name}:{i}: {c.strip()[:100]}")
    print(f"[5/7] Heading math check : {len(heading_math)} unwrapped math headings")
    for h in heading_math[:15]:
        print(f"      WARN  {h}")
    issues += len(heading_math)

    # 6. Citation parity (\cite <-> \bibitem)
    main_clean = "\n".join(strip_comment(line) for line in MAIN_TEX.read_text(encoding="utf-8").splitlines())
    bibitems = set(re.findall(r"\\bibitem\{([^}]+)\}", main_clean))
    cited: set[str] = set()
    for path in [MAIN_TEX, *sections]:
        c = "\n".join(strip_comment(line) for line in path.read_text(encoding="utf-8").splitlines())
        for grp in re.findall(r"\\cite(?:\[[^\]]*\])?\{([^}]+)\}", c):
            for key in grp.split(","):
                k = key.strip()
                if k:
                    cited.add(k)
    missing_bib = sorted(cited - bibitems)
    unused_bib = sorted(bibitems - cited)
    print(
        f"[6/7] Citation parity    : {len(cited)} cited, {len(bibitems)} bibitems, "
        f"{len(missing_bib)} missing, {len(unused_bib)} unused"
    )
    for k in missing_bib:
        print(f"      ERROR missing bibitem: {k}")
    for k in unused_bib:
        print(f"      WARN  unused bibitem : {k}")
    issues += len(missing_bib) + len(unused_bib)

    # 7. Figure captions & spacing (\vspace before \caption; <= 1 sentence excluding Nguon)
    fig_hits: list[str] = []
    for path in sections:
        clean_doc = "\n".join(strip_comment(line) for line in path.read_text(encoding="utf-8").splitlines())
        for m in re.finditer(r"\\begin\{figure\}.*?\\end\{figure\}", clean_doc, re.S):
            block = m.group(0)
            cap_idx = block.find(r"\caption")
            if cap_idx == -1:
                continue
            line_no = clean_doc[: m.start() + cap_idx].count("\n") + 1
            if r"\vspace" not in block[:cap_idx]:
                fig_hits.append(f"{path.name}:{line_no}: missing \\vspace before \\caption")
            k = cap_idx + len(r"\caption")
            while k < len(block) and block[k] in " \t\n":
                k += 1
            if k < len(block) and block[k] == "[":
                k = _consume_balanced(block, k, "[", "]")
            while k < len(block) and block[k] in " \t\n":
                k += 1
            if k < len(block) and block[k] == "{":
                end_k = _consume_balanced(block, k, "{", "}")
                cap_body = block[k + 1 : end_k - 1]
                cap_no_src = re.sub(r"\\emph\{\(Nguồn:.*?\)\}|\(Nguồn:.*?\)", "", cap_body, flags=re.S).strip()
                cap_no_code = re.sub(r"\\(?:code|texttt)\{[^}]*\}|\$[^$]*\$", "X", cap_no_src)
                if re.search(r"(?<!\d)\.\s+\S", cap_no_code):
                    fig_hits.append(f"{path.name}:{line_no}: multi-sentence figure caption")
    print(f"[7/7] Figure captions    : {len(fig_hits)} spacing/multi-sentence issue(s)")
    for h in fig_hits[:15]:
        print(f"      WARN  {h}")
    issues += len(fig_hits)

    print(f"\nAUDIT SUMMARY: {issues} total finding(s).")
    return 1 if missing_targets or missing_bib else 0


if __name__ == "__main__":
    sys.exit(main())
