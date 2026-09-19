#!/usr/bin/env python3
"""Strip YAML front matter and rewrite mermaid fences for the web edition.

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
  * Rewrite every ```mermaid block to <pre class="mermaid">…</pre> so
    the client-side renderer shipped via theme/index.hbs picks it up.
    mdBook itself would render these as <pre class="language-mermaid">,
    which highlight.js cannot parse.

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
MERMAID_OPEN = re.compile(r"^\s*```\s*mermaid\s*$")
FENCE_OPEN = re.compile(r"^\s*```")
MERMAID_INLINE = re.compile(r"```mermaid\b")


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


def rewrite_mermaid(body: str) -> str:
    """Replace every ```mermaid ... ``` fence with a <pre class="mermaid">
    block so the client-side mermaid.js renderer picks it up."""
    lines = body.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        if MERMAID_OPEN.match(lines[i]):
            out.append('<pre class="mermaid">')
            i += 1
            while i < len(lines) and not FENCE_OPEN.match(lines[i]):
                out.append(lines[i])
                i += 1
            out.append("</pre>")
            i += 1  # skip the closing fence
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def strip_front_matter(text: str) -> str:
    """Drop the leading `---` block. Promote `title:` to an H1 only if
    the body does not already start with one. Also rewrite mermaid
    fences so the client-side renderer can find them."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return rewrite_mermaid(text)
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return rewrite_mermaid(text)
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
        body = f"# {title}\n\n" + "\n".join(body_lines).lstrip("\n") + "\n"
    else:
        body = "\n".join(body_lines).lstrip("\n") + ("\n" if body_lines else "")
    return rewrite_mermaid(body)


def process(path: Path, force_python: bool) -> bool:
    original = path.read_text(encoding="utf-8")
    if not original.lstrip().startswith("---") and "```mermaid" not in original:
        return False
    if force_python:
        filtered = strip_front_matter(original)
    else:
        rendered = try_pandoc(path)
        # Even when pandoc renders, finish by rewriting mermaid fences.
        filtered = (rendered if rendered is not None else strip_front_matter(original))
        if "```mermaid" in filtered or '<pre class="language-mermaid">' in filtered:
            filtered = rewrite_mermaid(filtered)
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
