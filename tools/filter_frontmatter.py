#!/usr/bin/env python3
"""Filter YAML front matter out of every markdown file under src/.

Pandoc is already installed on the macOS host, but we ship a pure-Python
fallback so the GitHub Actions runner does not need pandoc. The fallback
mimics pandoc's behaviour for our corpus: drop the leading `---` block,
promote `title:` to the first H1, and leave everything else alone.

mdbook-mermaid picks up the ```mermaid fences untouched.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

FM_OPEN = re.compile(r"^---\s*$")
TITLE_LINE = re.compile(r"^title:\s*(.+?)\s*$")


def try_pandoc(path: Path) -> str | None:
    binary = shutil.which("pandoc")
    if not binary:
        return None
    try:
        result = subprocess.check_output(
            [
                binary,
                "-f", "markdown",
                "-t", "markdown",
                "--wrap=none",
                "--markdown-headings=atx",
                str(path),
            ],
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError:
        return None
    return result


def python_filter(text: str) -> str:
    """Pure-Python fallback that mirrors pandoc's markdown round-trip."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return text
    fm_block = lines[1:end]
    body = lines[end + 1:]
    title = None
    for ln in fm_block:
        m = TITLE_LINE.match(ln)
        if m:
            title = m.group(1).strip().strip('"').strip("'")
            break
    if title is None:
        return "\n".join(body).lstrip("\n")
    head = f"# {title}\n\n"
    return head + "\n".join(body).lstrip("\n")


def process(path: Path, force_python: bool) -> bool:
    original = path.read_text(encoding="utf-8")
    if not original.lstrip().startswith("---"):
        return False
    filtered = None if not force_python else None
    if not force_python:
        filtered = try_pandoc(path)
    if filtered is None:
        filtered = python_filter(original)
    if filtered == original:
        return False
    path.write_text(filtered, encoding="utf-8")
    return True


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path, help="src/ root of the book")
    p.add_argument("--force-python", action="store_true",
                   help="skip pandoc, use the pure-Python fallback")
    args = p.parse_args()
    root: Path = args.root
    changed = 0
    scanned = 0
    for path in sorted(root.rglob("*.md")):
        scanned += 1
        if process(path, args.force_python):
            changed += 1
    print(f"scanned {scanned} files, rewrote {changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
