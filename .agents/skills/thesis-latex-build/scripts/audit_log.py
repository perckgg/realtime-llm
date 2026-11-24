"""Parse docs/drafts/Internship2_HK262/main.log and report refs, links, and table overflows."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]
DEFAULT_LOG = REPO_ROOT / "docs" / "drafts" / "Internship2_HK262" / "main.log"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit pdflatex main.log for quality issues.")
    parser.add_argument("--log", type=pathlib.Path, default=DEFAULT_LOG, help="Path to main.log")
    parser.add_argument("--overfull-pt", type=float, default=8.0, help="Threshold (pt) to list Overfull hbox")
    args = parser.parse_args()

    if not args.log.exists():
        print(f"[ERROR] Log file not found: {args.log}")
        return 1

    text = args.log.read_text(encoding="latin-1", errors="replace")

    pages_m = re.search(r"Output written on [^\s]+\.pdf \((\d+) pages", text)
    pages = pages_m.group(1) if pages_m else "unknown"

    undef_refs = re.findall(r"(?:Reference|Citation) `[^']+` on page .* undefined", text)
    dead_links = re.findall(r".*has been referenced but does not exist.*", text)
    pdf_strings = re.findall(r".*Token not allowed in a PDF string.*", text)
    dup_dests = re.findall(r".*destination with the same identifier.*", text)
    needs_rerun = bool(re.search(r"Rerun to get cross-references right|Label\(s\) may have changed", text))

    cur_file = "main.tex"
    overfulls: list[tuple[str, float, str, int, int]] = []
    for line in text.splitlines():
        for m in re.finditer(r"\(((?:Sections/)?[A-Za-z0-9_.-]+\.tex)", line):
            cur_file = m.group(1)
        m = re.match(
            r"Overfull \\hbox \(([0-9.]+)pt too wide\) in (alignment|paragraph) at lines (\d+)--(\d+)",
            line,
        )
        if m and float(m.group(1)) >= args.overfull_pt:
            overfulls.append((cur_file, float(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4))))

    align_overfulls = [o for o in overfulls if o[2] == "alignment"]

    print(f"=== Log Audit: {args.log.name} ({pages} pages) ===")
    print(f"  Undefined refs/cites    : {len(undef_refs)}")
    print(f"  Dead hyperlinks         : {len(dead_links)}")
    print(f"  PDF string warnings     : {len(pdf_strings)}")
    print(f"  Duplicate dests         : {len(dup_dests)}")
    print(f"  Still needs rerun       : {needs_rerun}")
    print(f"  Table alignment overfull: {len(align_overfulls)}")
    print(f"  All Overfull >= {args.overfull_pt:.0f}pt     : {len(overfulls)}")

    for item in undef_refs[:10]:
        print(f"  [UNDEF] {item.strip()}")
    for item in dead_links[:10]:
        print(f"  [DEAD ] {item.strip()}")
    for item in overfulls[:20]:
        print(f"  [OVF  ] {item[0]:34s} {item[1]:6.1f}pt  {item[2]:9s}  L{item[3]}--{item[4]}")

    failed = bool(undef_refs or dead_links or pdf_strings or needs_rerun or align_overfulls)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
