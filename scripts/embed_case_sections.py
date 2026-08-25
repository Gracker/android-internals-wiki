#!/usr/bin/env python3
"""Embed former case-source blocks under the mechanism they demonstrate.

Dry-run by default. This removes the last article-level case wrappers created
from standalone source articles while preserving their evidence and nested case
structure.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HEADING_RE = re.compile(r"^(#{1,6})(\s+)(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
TAIL_H3 = {"版本与实现边界", "诊断与验证清单", "常见误区", "结论", "小结"}

MOVES = {
    "src/part2-performance/ch07-smoothness/02-jank-methodology-scenarios-cases.md": (
        "案例中的证据链与修复判断",
        "滚动、动画、启动与交互场景",
        "案例：从现场证据到修复判断",
    ),
    "src/part2-performance/ch08-responsiveness/01-responsiveness-principles-scenarios-cases.md": (
        "案例中的时间线与优化取舍",
        "页面、输入、网络与后台唤醒场景",
        "案例：时间线、优化动作与收益边界",
    ),
    "src/part2-performance/ch11-power/02-app-power-optimization-cases.md": (
        "案例中的能量归因与复测",
        "组件活动、唤醒与后台工作",
        "案例：能量归因、修复与复测",
    ),
}


@dataclass
class Block:
    title: str
    lines: list[str]


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("unclosed YAML frontmatter")
    return text[4:end], text[end + 5 :].lstrip("\n")


def trim(lines: list[str]) -> list[str]:
    while lines and not lines[0].strip():
        lines = lines[1:]
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    return lines


def h2_positions(lines: list[str]) -> list[tuple[int, str]]:
    result = []
    fenced = False
    for index, line in enumerate(lines):
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        match = HEADING_RE.match(line) if not fenced else None
        if match and len(match.group(1)) == 2:
            result.append((index, match.group(3)))
    return result


def split_body(body: str) -> tuple[list[str], list[Block]]:
    lines = body.splitlines()
    positions = h2_positions(lines)
    prefix = trim(lines[: positions[0][0]])
    blocks = []
    for index, (start, title) in enumerate(positions):
        end = positions[index + 1][0] if index + 1 < len(positions) else len(lines)
        blocks.append(Block(title, trim(lines[start + 1 : end])))
    return prefix, blocks


def shift_headings(lines: list[str], delta: int) -> list[str]:
    result = []
    fenced = False
    for line in lines:
        if FENCE_RE.match(line):
            fenced = not fenced
            result.append(line)
            continue
        match = HEADING_RE.match(line) if not fenced else None
        if not match:
            result.append(line)
            continue
        level = min(6, len(match.group(1)) + delta)
        result.append(f"{'#' * level}{match.group(2)}{match.group(3)}")
    return result


def insertion_index(lines: list[str]) -> int:
    fenced = False
    for index, line in enumerate(lines):
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        match = HEADING_RE.match(line) if not fenced else None
        if match and len(match.group(1)) == 3 and match.group(3) in TAIL_H3:
            return index
    return len(lines)


def rewrite(path: Path, move: tuple[str, str, str]) -> tuple[str, str]:
    frontmatter, body = split_frontmatter(path.read_text(encoding="utf-8"))
    prefix, blocks = split_body(body)
    case_title, owner_title, embedded_title = move
    case = next((block for block in blocks if block.title == case_title), None)
    owner = next((block for block in blocks if block.title == owner_title), None)
    if not case or not owner:
        return path.read_text(encoding="utf-8"), "already embedded or headings changed"

    payload = [f"### {embedded_title}", ""] + shift_headings(case.lines, 1)
    at = insertion_index(owner.lines)
    before = trim(owner.lines[:at])
    after = trim(owner.lines[at:])
    owner.lines = before + ([""] if before else []) + payload
    if after:
        owner.lines += [""] + after
    blocks = [block for block in blocks if block is not case]

    output = prefix
    for block in blocks:
        if output:
            output.append("")
        output.extend([f"## {block.title}", ""])
        output.extend(trim(block.lines))
    text = f"---\n{frontmatter}\n---\n\n" + "\n".join(output).rstrip() + "\n"
    return text, f"{case_title} -> {owner_title} / {embedded_title}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    changed = 0
    for rel, move in MOVES.items():
        path = ROOT / rel
        revised, note = rewrite(path, move)
        if revised == path.read_text(encoding="utf-8"):
            print(f"skip {rel}: {note}")
            continue
        changed += 1
        print(f"{rel}: {note}")
        if args.apply:
            path.write_text(revised, encoding="utf-8")
    mode = "applied" if args.apply else "dry-run"
    print(f"{mode}: {changed} case blocks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
