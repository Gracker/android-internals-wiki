#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail closed if an AIW automation commit violates the no-new-chapter freeze.

Intended to run after git add and before git commit inside Android-Internal-Wiki.
Bypass only for explicit manual maintenance with AIW_ALLOW_CHAPTER_CREATION=1.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki")


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=str(REPO), text=True, capture_output=True)


def staged_name_status() -> list[tuple[str, str]]:
    r = git("diff", "--cached", "--name-status", "-z")
    if r.returncode != 0:
        raise SystemExit(r.stderr or r.stdout or "git diff failed")
    parts = [p for p in r.stdout.split("\0") if p]
    out: list[tuple[str, str]] = []
    i = 0
    while i < len(parts):
        status = parts[i]
        i += 1
        if not status:
            continue
        code = status[0]
        if code in {"R", "C"} and i + 1 < len(parts):
            _old = parts[i]
            new = parts[i + 1]
            i += 2
            out.append((code, new))
        elif i < len(parts):
            path = parts[i]
            i += 1
            out.append((code, path))
    return out


def main() -> int:
    if os.environ.get("AIW_ALLOW_CHAPTER_CREATION") == "1":
        print("AIW freeze guard bypassed by AIW_ALLOW_CHAPTER_CREATION=1")
        return 0
    violations: list[str] = []
    for status, path in staged_name_status():
        if path == "src/SUMMARY.md":
            violations.append(f"{status}\t{path}\tSUMMARY edits are frozen")
        elif path.startswith("src/") and path.endswith(".md") and status in {"A", "C", "R"}:
            violations.append(f"{status}\t{path}\tnew/renamed chapter files are frozen")
    if violations:
        print("# AIW Freeze Guard")
        print("- status: blocked")
        print("- reason: no-new-chapter freeze violation")
        print("- bypass: set AIW_ALLOW_CHAPTER_CREATION=1 only for explicit manual chapter work")
        print("## Violations")
        for v in violations:
            print(f"- {v}")
        return 3
    print("AIW freeze guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
