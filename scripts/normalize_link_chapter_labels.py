#!/usr/bin/env python3
"""Align numbered Markdown link labels with the canonical target metadata.

When chapters are split, merged or renumbered, a path can be correct while the
visible label still names the old chapter. This pass treats the target chapter
and title as authoritative. Dry-run by default.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from urllib.parse import unquote

import yaml


ROOT = Path(__file__).resolve().parents[1]
FENCE_RE = re.compile(r"^\s*(```|~~~)")
LINK_RE = re.compile(r"(?<!!)\[([^\]\n]+)\]\((<[^>\n]+>|[^)\n]+)\)")
NUMBER_RE = re.compile(r"^(\d+\.\d+)(?:\s+(.+))?$")


def targets() -> dict[Path, tuple[str, str]]:
    result = {}
    for path in ROOT.glob("src/part*/ch*/*.md"):
        if path.name == "README.md":
            continue
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        end = text.find("\n---\n", 4)
        meta = yaml.safe_load(text[4:end]) or {}
        result[path.resolve()] = (str(meta["chapter"]), str(meta["title"]))
    return result


def rewrite(path: Path, canonical: dict[Path, tuple[str, str]]) -> tuple[str, list[str]]:
    original = path.read_text(encoding="utf-8")
    result = []
    changes = []
    fenced = False
    for line_no, line in enumerate(original.splitlines(), 1):
        if FENCE_RE.match(line):
            fenced = not fenced
            result.append(line)
            continue
        if fenced:
            result.append(line)
            continue

        def replace(match: re.Match[str]) -> str:
            label, raw = match.groups()
            numbered = NUMBER_RE.match(label.strip())
            if not numbered:
                return match.group(0)
            href = raw[1:-1] if raw.startswith("<") and raw.endswith(">") else raw
            path_part = href.split("#", 1)[0]
            if not path_part or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", path_part):
                return match.group(0)
            target = (path.parent / unquote(path_part)).resolve()
            if target not in canonical:
                return match.group(0)
            chapter, title = canonical[target]
            if numbered.group(1) == chapter:
                return match.group(0)
            new_label = chapter if not numbered.group(2) else f"{chapter} {title}"
            changes.append(f"L{line_no}: {label} -> {new_label}")
            return f"[{new_label}]({raw})"

        parts = re.split(r"(`+[^`]*`+)", line)
        result.append(
            "".join(
                part if index % 2 else LINK_RE.sub(replace, part)
                for index, part in enumerate(parts)
            )
        )
    ending = "\n" if original.endswith("\n") else ""
    return "\n".join(result) + ending, changes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    canonical = targets()
    changed_files = 0
    changes_count = 0
    for path in sorted(ROOT.glob("src/**/*.md")):
        revised, changes = rewrite(path, canonical)
        if not changes:
            continue
        changed_files += 1
        changes_count += len(changes)
        print(path.relative_to(ROOT))
        for change in changes:
            print(f"  {change}")
        if args.apply:
            path.write_text(revised, encoding="utf-8")
    mode = "applied" if args.apply else "dry-run"
    print(f"{mode}: {changes_count} labels across {changed_files} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
