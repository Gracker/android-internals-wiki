#!/usr/bin/env python3
"""Normalize mechanical heading defects introduced during editorial fusion.

Dry-run by default. The script makes only two narrowly-scoped changes:

1. promote a heading when it skips directly from H2 to H4+;
2. disambiguate a shared-tail H3 that repeats a mechanism H2 verbatim.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HEADING_RE = re.compile(r"^(#{1,6})(\s+)(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
TAIL_LABELS = {
    "版本与实现边界": "版本边界",
    "诊断与验证清单": "检查项",
    "常见误区": "常见误区",
    "结论": "结论",
}


def canonical_bodies() -> list[Path]:
    return sorted(
        path
        for path in ROOT.glob("src/part*/ch*/*.md")
        if path.name != "README.md"
    )


def normalize_title(value: str) -> str:
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"^(?:\d+(?:\.\d+)*|[一二三四五六七八九十]+)[.、：:]\s*", "", value)
    value = re.sub(r"[\s`*_—–:：,，。！？?!（）()《》/·]+", "", value)
    return value.casefold()


def rewrite(path: Path) -> tuple[str, list[str]]:
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines()
    h2_titles: set[str] = set()
    fenced = False
    for line in lines:
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        match = HEADING_RE.match(line) if not fenced else None
        if match and len(match.group(1)) == 2:
            h2_titles.add(normalize_title(match.group(3)))

    changes: list[str] = []
    result: list[str] = []
    fenced = False
    previous_level = 1
    parent_h2 = ""
    for line_no, line in enumerate(lines, 1):
        if FENCE_RE.match(line):
            fenced = not fenced
            result.append(line)
            continue
        match = HEADING_RE.match(line) if not fenced else None
        if not match:
            result.append(line)
            continue

        level = len(match.group(1))
        space = match.group(2)
        title = match.group(3)
        if level > previous_level + 1 and previous_level == 2:
            changes.append(f"L{line_no}: H{level}->H3 {title}")
            level = 3

        if level == 2:
            parent_h2 = title
        elif (
            level == 3
            and parent_h2 in TAIL_LABELS
            and normalize_title(title) in h2_titles
        ):
            label = TAIL_LABELS[parent_h2]
            if label:
                revised = f"{title}：{label}"
                changes.append(f"L{line_no}: {title} -> {revised}")
                title = revised

        result.append(f"{'#' * level}{space}{title}")
        previous_level = level

    ending = "\n" if original.endswith("\n") else ""
    return "\n".join(result) + ending, changes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    changed = 0
    edits = 0
    for path in canonical_bodies():
        revised, changes = rewrite(path)
        if not changes:
            continue
        changed += 1
        edits += len(changes)
        rel = path.relative_to(ROOT)
        print(rel)
        for change in changes:
            print(f"  {change}")
        if args.apply:
            path.write_text(revised, encoding="utf-8")
    mode = "applied" if args.apply else "dry-run"
    print(f"{mode}: {edits} edits across {changed} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
