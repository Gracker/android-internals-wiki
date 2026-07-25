#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI guard for the current AIW no-new-chapter freeze.

Fails when a push/PR adds/renames/copies src/**/*.md chapter files or modifies
src/SUMMARY.md. Manual exceptional commits can include [allow-new-aiw-chapter]
in the commit message.
"""
from __future__ import annotations

import os
import subprocess
import sys

ALLOW_MARKER = "[allow-new-aiw-chapter]"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True)


def main() -> int:
    base = os.environ.get("AIW_FREEZE_BASE", "HEAD^")
    head = os.environ.get("AIW_FREEZE_HEAD", "HEAD")
    msg = run(["git", "log", "-1", "--pretty=%B", head]).stdout
    if ALLOW_MARKER in msg:
        print(f"AIW no-new-chapter guard bypassed by {ALLOW_MARKER}")
        return 0
    diff = run(["git", "diff", "--name-status", "--diff-filter=ACMRT", f"{base}..{head}"])
    if diff.returncode != 0:
        print(diff.stdout + diff.stderr)
        return diff.returncode
    violations: list[str] = []
    lines = [x for x in diff.stdout.splitlines() if x.strip()]
    for line in lines:
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]
        code = status[0]
        if path == "src/SUMMARY.md":
            violations.append(f"{status}\t{path}\tSUMMARY edits are frozen")
        elif path.startswith("src/") and path.endswith(".md") and code in {"A", "C", "R"}:
            violations.append(f"{status}\t{path}\tnew/renamed chapter files are frozen")
    if violations:
        print("AIW no-new-chapter freeze violation:")
        for v in violations:
            print(f"- {v}")
        print(f"If this is explicit manual chapter work, include {ALLOW_MARKER} in the commit message.")
        return 3
    print("AIW no-new-chapter guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
