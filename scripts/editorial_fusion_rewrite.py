#!/usr/bin/env python3
"""Rewrite stitched merge targets into integrated editorial structures.

The rewrite is specification-driven and dry-run by default. It preserves every
source block, but replaces source-article wrappers with mechanism-oriented
sections, permits semantic reordering, moves repeated editorial tail sections
into one shared location, and inserts reviewed transitions.
"""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "metadata/2026-08-24-editorial-fusion-v3.json"
FUSED_AT = "2026-08-24"
HEADING_RE = re.compile(r"^(#{1,6})(\s+)(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


@dataclass
class Section:
    title: str
    lines: list[str]


@dataclass
class Block:
    old_title: str
    new_title: str
    preamble: list[str]
    sections: list[Section]
    bridge: str


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("unclosed YAML frontmatter")
    return text[4:end], text[end + 5 :].lstrip("\n")


def set_frontmatter_field(raw: str, key: str, value: str) -> str:
    lines = raw.splitlines()
    pattern = re.compile(rf"^{re.escape(key)}\s*:")
    for index, line in enumerate(lines):
        if pattern.match(line):
            lines[index] = f'{key}: "{value}"'
            return "\n".join(lines)
    lines.append(f'{key}: "{value}"')
    return "\n".join(lines)


def heading_positions(lines: list[str], level: int) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    fenced = False
    for index, line in enumerate(lines):
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        match = HEADING_RE.match(line) if not fenced else None
        if match and len(match.group(1)) == level:
            result.append((index, match.group(3)))
    return result


def split_body(body: str) -> tuple[list[str], str, list[tuple[str, list[str]]]]:
    lines = body.splitlines()
    h1s = heading_positions(lines, 1)
    if len(h1s) != 1:
        raise ValueError(f"expected one H1, got {len(h1s)}")
    h1_index, h1_title = h1s[0]
    h2s = heading_positions(lines, 2)
    if not h2s:
        raise ValueError("stitched target has no H2 blocks")
    prefix = lines[:h1_index]
    blocks: list[tuple[str, list[str]]] = []
    for idx, (start, title) in enumerate(h2s):
        end = h2s[idx + 1][0] if idx + 1 < len(h2s) else len(lines)
        blocks.append((title, lines[start + 1 : end]))
    return prefix, h1_title, blocks


def split_h3_sections(lines: list[str]) -> tuple[list[str], list[Section]]:
    positions = heading_positions(lines, 3)
    if not positions:
        return trim_blank(lines), []
    preamble = trim_blank(lines[: positions[0][0]])
    sections: list[Section] = []
    for idx, (start, title) in enumerate(positions):
        end = positions[idx + 1][0] if idx + 1 < len(positions) else len(lines)
        sections.append(Section(title=title, lines=trim_blank(lines[start + 1 : end])))
    return preamble, sections


def trim_blank(lines: list[str]) -> list[str]:
    start = 0
    end = len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def normalize_heading(title: str) -> str:
    title = re.sub(r"`([^`]*)`", r"\1", title)
    title = re.sub(r"^(?:\d+(?:\.\d+)*|[一二三四五六七八九十]+)[.、：:]\s*", "", title)
    title = re.sub(r"[\s`*_—–:：,，。！？?!（）()《》/·]+", "", title)
    return title.casefold()


def classify_tail(title: str) -> str | None:
    key = normalize_heading(title)
    if re.search(r"(?:参考资料|参考文档|参考材料|参考来源|参考链接|参考源码与文档|源码与参考资料)$", key):
        return "references"
    if key in {
        "官方入口",
        "官方文档",
        "官方文档与源码",
        "固定源码入口",
        "源码入口",
        "源码阅读顺序",
        "references",
        "sources",
    }:
        return "references"
    if re.search(r"(?:常见误区|常见误判|常见问题与误区|反模式|错误做法|容易混淆的.*|错误结论)$", key):
        return "pitfalls"
    if key in {
        "版本边界",
        "版本演进",
        "版本演进速查",
        "版本演进与当前结论",
        "版本锚点与结论范围",
        "平台与版本边界",
        "版本结论",
    }:
        return "versions"
    if key in {"总结", "小结", "结论", "工程结论", "核心结论"}:
        return "conclusions"
    if key in {"检查清单", "诊断检查清单", "实施检查清单", "验证清单"}:
        return "checklists"
    return None


def shift_headings(lines: list[str], delta: int) -> list[str]:
    result: list[str] = []
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
        level = max(1, min(6, len(match.group(1)) + delta))
        result.append(f'{"#" * level}{match.group(2)}{match.group(3)}')
    return result


def compact_reference_lines(groups: list[tuple[Block, Section]]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for _, section in groups:
        for line in section.lines:
            key = re.sub(r"\s+", " ", line.strip()).casefold()
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            result.append(line)
        if result and result[-1].strip():
            result.append("")
    return trim_blank(result)


def tail_context_title(category: str, title: str) -> str:
    """Name a source context by its role in the shared editorial tail."""
    labels = {
        "versions": "版本边界",
        "checklists": "检查项",
        "pitfalls": "常见误区",
        "conclusions": "结论",
    }
    label = labels.get(category, "")
    return title if not label else f"{title}：{label}"


def render_tail(category: str, groups: list[tuple[Block, Section]]) -> list[str]:
    titles = {
        "versions": "版本与实现边界",
        "checklists": "诊断与验证清单",
        "pitfalls": "常见误区",
        "conclusions": "结论",
        "references": "参考资料",
    }
    result = [f'## {titles[category]}', ""]
    if category == "references":
        result.extend(compact_reference_lines(groups))
        return trim_blank(result)

    multiple = len(groups) > 1
    per_block: dict[str, int] = {}
    for block, _ in groups:
        per_block[block.new_title] = per_block.get(block.new_title, 0) + 1
    for block, section in groups:
        if multiple:
            context = tail_context_title(category, block.new_title)
            if per_block[block.new_title] > 1:
                context = f"{block.new_title}：{section.title}"
            result.extend([f"### {context}", ""])
            result.extend(section.lines)
        else:
            result.extend(shift_headings(section.lines, -1))
        result.append("")
    return trim_blank(result)


def render_block(block: Block) -> list[str]:
    result = [f"## {block.new_title}", ""]
    if block.bridge:
        result.extend([block.bridge.strip(), ""])
    if block.preamble:
        result.extend(block.preamble)
        result.append("")
    for section in block.sections:
        result.extend([f"### {section.title}", ""])
        result.extend(section.lines)
        result.append("")
    return trim_blank(result)


def rewrite_text(
    original: str,
    spec: dict[str, object],
    display_path: str,
) -> tuple[str, dict[str, object]]:
    frontmatter, body = split_frontmatter(original)
    prefix, h1_title, raw_blocks = split_body(body)
    section_specs = spec["sections"]
    if not isinstance(section_specs, list):
        raise ValueError("sections must be a list")
    expected = [str(item["from"]) for item in section_specs]
    actual = [title for title, _ in raw_blocks]
    if sorted(expected) != sorted(actual) or len(expected) != len(actual):
        raise ValueError(f"H2 mismatch; expected={expected}; actual={actual}")
    raw_by_title = {title: lines for title, lines in raw_blocks}

    blocks: list[Block] = []
    for item in section_specs:
        old_title = str(item["from"])
        preamble, sections = split_h3_sections(raw_by_title[old_title])
        blocks.append(
            Block(
                old_title=old_title,
                new_title=str(item["title"]),
                preamble=preamble,
                sections=sections,
                bridge=str(item.get("bridge") or ""),
            )
        )

    tails: dict[str, list[tuple[Block, Section]]] = {
        "versions": [],
        "checklists": [],
        "pitfalls": [],
        "conclusions": [],
        "references": [],
    }
    moved = 0
    for block in blocks:
        retained: list[Section] = []
        for section in block.sections:
            category = classify_tail(section.title)
            if category:
                tails[category].append((block, section))
                moved += 1
            else:
                retained.append(section)
        block.sections = retained

    intro = trim_blank(blocks[0].preamble)
    blocks[0].preamble = []
    bridge = str(spec.get("intro_bridge") or "").strip()
    output: list[str] = [*prefix, f"# {h1_title}", ""]
    if intro:
        output.extend(intro)
        output.append("")
    if bridge:
        output.extend([bridge, ""])
    for block in blocks:
        output.extend(render_block(block))
        output.extend(["", ""])
    for category in ("versions", "checklists", "pitfalls", "conclusions", "references"):
        if tails[category]:
            output.extend(render_tail(category, tails[category]))
            output.extend(["", ""])

    rewritten = f"---\n{frontmatter}\n---\n\n" + "\n".join(trim_blank(output)) + "\n"
    report = {
        "path": display_path,
        "old_h2": actual,
        "new_h2": [str(item["title"]) for item in section_specs]
        + [
            {
                "versions": "版本与实现边界",
                "checklists": "诊断与验证清单",
                "pitfalls": "常见误区",
                "conclusions": "结论",
                "references": "参考资料",
            }[category]
            for category in ("versions", "checklists", "pitfalls", "conclusions", "references")
            if tails[category]
        ],
        "moved_tail_sections": moved,
        "bytes_before": len(original.encode("utf-8")),
        "bytes_after": len(rewritten.encode("utf-8")),
    }
    return rewritten, report


def rewrite_target(path: Path, spec: dict[str, object]) -> tuple[str, dict[str, object]]:
    return rewrite_text(
        path.read_text(encoding="utf-8"),
        spec,
        str(path.relative_to(ROOT)),
    )


def validate_markdown(text: str, path: Path) -> None:
    fences = [line for line in text.splitlines() if FENCE_RE.match(line)]
    if len(fences) % 2:
        raise ValueError(f"unbalanced fenced code blocks: {path}")
    h1 = heading_positions(split_frontmatter(text)[1].splitlines(), 1)
    if len(h1) != 1:
        raise ValueError(f"expected one H1 after rewrite: {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--chapter", help="only rewrite targets whose path contains this chapter id")
    args = parser.parse_args()
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    targets = spec["targets"]
    updates: dict[Path, str] = {}
    reports: list[dict[str, object]] = []
    for relative, target_spec in targets.items():
        if target_spec.get("status") != "ready":
            continue
        if args.chapter and f"/{args.chapter}-" not in relative:
            continue
        path = ROOT / relative
        rewritten, report = rewrite_target(path, target_spec)
        validate_markdown(rewritten, path)
        updates[path] = rewritten
        reports.append(report)

    if args.apply:
        with tempfile.TemporaryDirectory(prefix="aiw-editorial-fusion-") as temp_value:
            temp_root = Path(temp_value)
            for path, text in updates.items():
                staged = temp_root / path.relative_to(ROOT)
                staged.parent.mkdir(parents=True, exist_ok=True)
                staged.write_text(text, encoding="utf-8", newline="\n")
            for path in sorted(updates):
                staged = temp_root / path.relative_to(ROOT)
                path.write_text(staged.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")

    print(json.dumps({"mode": "apply" if args.apply else "dry-run", "files": reports}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
