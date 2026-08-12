#!/usr/bin/env python3
"""Remove obsolete workflow fields from AIW article frontmatter.

The rewrite is deliberately line-preserving: retained YAML and article bodies
remain byte-for-byte unchanged. Only complete top-level YAML fields outside the
canonical schema are removed.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

try:
    from frontmatter_schema import ALLOWED_FIELDS
except ModuleNotFoundError:  # Support import-based tests from the repository root.
    from scripts.frontmatter_schema import ALLOWED_FIELDS


REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
TOP_LEVEL_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s|$)")


def article_paths() -> list[Path]:
    return sorted(
        path
        for path in SRC.rglob("*.md")
        if path.name not in {"README.md", "SUMMARY.md"}
    )


def clean_text(text: str, path: Path) -> tuple[str, list[str]]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return text, []

    raw = match.group(1)
    try:
        metadata = yaml.safe_load(raw) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML frontmatter in {path}: {exc}") from exc
    if not isinstance(metadata, dict):
        raise ValueError(f"frontmatter must be a mapping in {path}")

    unknown = {str(key) for key in metadata if str(key) not in ALLOWED_FIELDS}
    if not unknown:
        return text, []

    lines = raw.splitlines(keepends=True)
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        key_match = TOP_LEVEL_KEY_RE.match(line)
        if key_match:
            starts.append((index, key_match.group(1)))

    found = {key for _, key in starts}
    missing = unknown - found
    if missing:
        raise ValueError(
            f"cannot locate top-level YAML fields in {path}: {sorted(missing)}"
        )

    remove_lines: set[int] = set()
    for position, (start, key) in enumerate(starts):
        if key not in unknown:
            continue
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        remove_lines.update(range(start, end))

    cleaned_raw = "".join(
        line for index, line in enumerate(lines) if index not in remove_lines
    )
    suffix = text[match.end():]
    newline_after = "\n" if text[match.end() - 1 : match.end()] == "\n" else ""
    before_closer = "" if cleaned_raw.endswith("\n") else "\n"
    cleaned = f"---\n{cleaned_raw}{before_closer}---{newline_after}{suffix}"
    return cleaned, sorted(unknown)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write",
        action="store_true",
        help="Apply the cleanup. Without this flag, only report planned changes.",
    )
    args = parser.parse_args()

    changed_files = 0
    removed_fields = 0
    for path in article_paths():
        original = path.read_text(encoding="utf-8")
        cleaned, removed = clean_text(original, path)
        if not removed:
            continue
        changed_files += 1
        removed_fields += len(removed)
        print(f"{path.relative_to(REPO)}: {', '.join(removed)}")
        if args.write:
            path.write_text(cleaned, encoding="utf-8")

    action = "removed" if args.write else "would remove"
    print(
        f"{action} {removed_fields} top-level fields from "
        f"{changed_files} article files"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
