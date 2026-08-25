#!/usr/bin/env python3
"""Check relative Markdown links and local frontmatter source paths under src/."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
FENCE_RE = re.compile(r"^\s*(```|~~~)")
LINK_RE = re.compile(r"!?\[[^\]]*\]\((<[^>]+>|[^)]+)\)")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def frontmatter(text: str) -> dict[str, object]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    value = yaml.safe_load(text[4:end])
    return value if isinstance(value, dict) else {}


def check_markdown_links(path: Path, text: str) -> tuple[int, list[str]]:
    checked = 0
    broken: list[str] = []
    fenced = False
    for line_no, line in enumerate(text.splitlines(), 1):
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        for match in LINK_RE.finditer(line):
            raw = match.group(1)
            target = raw[1:-1] if raw.startswith("<") and raw.endswith(">") else raw
            path_part = unquote(target.partition("#")[0])
            if not path_part or SCHEME_RE.match(path_part):
                continue
            checked += 1
            resolved = (path.parent / path_part).resolve()
            if not resolved.exists():
                broken.append(f"{path.relative_to(ROOT)}:{line_no} -> {path_part}")
    return checked, broken


def check_local_sources(path: Path, text: str) -> tuple[int, list[str]]:
    metadata = frontmatter(text)
    sources = metadata.get("sources", [])
    if not isinstance(sources, list):
        return 0, []
    checked = 0
    broken: list[str] = []
    for index, source in enumerate(sources, 1):
        if not isinstance(source, dict) or source.get("type") not in {"local", "aiw"}:
            continue
        raw = source.get("path")
        if not isinstance(raw, str) or not raw or SCHEME_RE.match(raw):
            continue
        checked += 1
        resolved = (ROOT / raw).resolve()
        if not resolved.exists():
            broken.append(
                f"{path.relative_to(ROOT)}:sources[{index}] -> {raw}"
            )
    return checked, broken


def main() -> int:
    link_count = 0
    source_count = 0
    failures: list[str] = []
    for path in sorted(SRC.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        checked, broken = check_markdown_links(path, text)
        link_count += checked
        failures.extend(broken)
        checked, broken = check_local_sources(path, text)
        source_count += checked
        failures.extend(broken)

    if failures:
        print("Broken content references:")
        print("\n".join(failures))
        return 1
    print(
        f"Content link check passed: {link_count} relative Markdown link(s), "
        f"{source_count} local/aiw frontmatter source(s)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
