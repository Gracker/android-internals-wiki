#!/usr/bin/env python3
"""Validate mdBook SUMMARY.md links before running `mdbook build`.

Checks are intentionally stricter than mdBook's late parser errors:
- every local chapter link must resolve relative to the directory that contains SUMMARY.md;
- local hrefs must not contain raw whitespace, because mdBook treats those as malformed links;
- duplicate links are reported as warnings so generated SUMMARY churn is easier to spot.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlparse

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
EXTERNAL_SCHEMES = {"http", "https", "mailto", "tel"}


def is_external_or_anchor(href: str) -> bool:
    if href.startswith("#"):
        return True
    parsed = urlparse(href)
    return parsed.scheme in EXTERNAL_SCHEMES


def strip_fragment(href: str) -> str:
    return href.split("#", 1)[0]


def github_error(path: Path, line_no: int, message: str) -> None:
    print(f"::error file={path},line={line_no}::{message}")


def github_warning(path: Path, line_no: int, message: str) -> None:
    print(f"::warning file={path},line={line_no}::{message}")


def validate(summary: Path) -> int:
    if not summary.exists():
        print(f"SUMMARY file not found: {summary}", file=sys.stderr)
        return 2

    base = summary.parent
    errors: list[str] = []
    links: list[tuple[int, str]] = []

    for line_no, line in enumerate(summary.read_text(encoding="utf-8").splitlines(), 1):
        for match in LINK_RE.finditer(line):
            raw_href = match.group(1).strip()
            if is_external_or_anchor(raw_href):
                continue
            href_no_fragment = strip_fragment(raw_href)
            if not href_no_fragment:
                continue
            links.append((line_no, href_no_fragment))

            if any(ch.isspace() for ch in href_no_fragment):
                msg = (
                    f"raw whitespace in SUMMARY link '{raw_href}'. "
                    "Rename the file or percent-encode the href; mdBook may parse this as a malformed nested item."
                )
                github_error(summary, line_no, msg)
                errors.append(f"line {line_no}: {msg}")
                continue

            decoded = unquote(href_no_fragment)
            target = (base / decoded).resolve()
            try:
                target.relative_to(base.resolve())
            except ValueError:
                msg = f"SUMMARY link escapes book src directory: '{raw_href}'"
                github_error(summary, line_no, msg)
                errors.append(f"line {line_no}: {msg}")
                continue

            if not target.exists():
                msg = f"SUMMARY link target not found: '{raw_href}' -> {base / decoded}"
                github_error(summary, line_no, msg)
                errors.append(f"line {line_no}: {msg}")

    counts = Counter(href for _, href in links)
    first_line = {href: line for line, href in links}
    duplicate_count = 0
    for href, count in sorted(counts.items()):
        if count > 1:
            duplicate_count += 1
            github_warning(summary, first_line[href], f"duplicate SUMMARY link appears {count} times: '{href}'")

    if errors:
        print(f"SUMMARY link check failed: {len(errors)} error(s), {duplicate_count} duplicate warning(s).")
        for err in errors[:50]:
            print(f"- {err}")
        return 1

    print(f"SUMMARY link check passed: {len(links)} local link(s), {duplicate_count} duplicate warning(s).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate mdBook SUMMARY.md local links")
    parser.add_argument("--summary", default="src/SUMMARY.md", type=Path)
    args = parser.parse_args()
    return validate(args.summary)


if __name__ == "__main__":
    raise SystemExit(main())
