#!/usr/bin/env python3
"""Strip YAML front matter out of every markdown file under the given root.

The web edition of this book must not expose pipeline state, status
flags, or review timestamps. The original source tree on disk is left
untouched: this script edits an in-tree copy produced by Pages CI.

Behavior:
  * If a file starts with `---`, drop the entire leading front-matter
    block. The body is left exactly as written.
  * If the body already begins with an H1 (`# ...`), do not add another
    one — the chapter's own title wins.
  * If `title:` was present in the dropped block and the body has no
    leading H1, prepend `# title` so mdBook still gets a chapter title.

The fallback path uses pure Python so it works on a GitHub Actions
runner even when pandoc is not installed. When pandoc is available, it
takes over for a higher-fidelity markdown round-trip.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

TITLE_LINE = re.compile(r"^title:\s*(.+?)\s*$")
H1_LINE = re.compile(r"^\s*#\s+\S")


def try_pandoc(path: Path) -> str | None:
    binary = shutil.which("pandoc")
    if not binary:
        return None
    try:
        return subprocess.check_output(
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


def strip_front_matter(text: str) -> str:
    """Drop the leading `---` block. Promote `title:` to an H1 only if
    the body does not already start with one."""
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
    fm = lines[1:end]
    body_lines = lines[end + 1 :]
    while body_lines and body_lines[0].strip() == "":
        body_lines = body_lines[1:]
    title = None
    for ln in fm:
        m = TITLE_LINE.match(ln)
        if m:
            title = m.group(1).strip().strip('"').strip("'")
            break
    if title and body_lines and not H1_LINE.match(body_lines[0]):
        return f"# {title}\n\n" + "\n".join(body_lines).lstrip("\n") + "\n"
    return "\n".join(body_lines).lstrip("\n") + ("\n" if body_lines else "")


def process(path: Path, force_python: bool) -> bool:
    original = path.read_text(encoding="utf-8")
    if not original.lstrip().startswith("---"):
        return False
    if force_python:
        filtered = strip_front_matter(original)
    else:
        rendered = try_pandoc(path)
        filtered = rendered if rendered is not None else strip_front_matter(original)
    if filtered == original:
        return False
    path.write_text(filtered, encoding="utf-8")
    return True


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--force-python", action="store_true")
    args = p.parse_args()
    changed = scanned = 0
    for path in sorted(args.root.rglob("*.md")):
        scanned += 1
        if process(path, args.force_python):
            changed += 1
    print(f"scanned {scanned} files, rewrote {changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
