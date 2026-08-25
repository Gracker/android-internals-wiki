#!/usr/bin/env python3
"""Consolidate two remaining one-topic duplicate pairs.

The pass keeps the rendering-pipeline Flutter article and the tools chapter's
ProfilingManager article. Only source material that adds a distinct decision,
workflow or evidence boundary is embedded; parallel explanations of the same
mechanism are not concatenated. It then closes numbering gaps, rewrites links
and chapter references, and rebuilds the affected indexes.

Dry-run by default. Deleted sources remain recoverable from Git.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import consolidate_articles_v2 as v2  # noqa: E402
import editorial_fusion_rewrite as fusion  # noqa: E402


FLUTTER_SOURCE = "src/part1-fundamentals/ch02-rendering/08-flutter-rendering.md"
FLUTTER_TARGET = "src/part2-performance/ch18-rendering-pipelines/08-flutter-rendering-pipeline.md"
PROFILING_SOURCE = "src/part3-tools/ch19-apm/08-profiling-manager.md"
PROFILING_TARGET = "src/part3-tools/ch14-other-tools/08-profiling-manager.md"
DELETED_REDIRECTS = {
    FLUTTER_SOURCE: FLUTTER_TARGET,
    PROFILING_SOURCE: PROFILING_TARGET,
}
AFFECTED_DIRS = {
    "src/part1-fundamentals/ch02-rendering",
    "src/part3-tools/ch19-apm",
}
HISTORICAL_JSON = {
    "metadata/2026-08-24-content-consolidation-v2-map.json",
    "metadata/2026-08-24-editorial-fusion-v3-map.json",
}
MAP_V4 = "metadata/2026-08-24-editorial-fusion-v4-map.json"
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})(\s+)(.+?)\s*$")
LINK_RE = re.compile(r"(!?\[[^\]\n]*\])\((<[^>\n]+>|[^)\n]+)\)")
INDEX_HEADING_RE = re.compile(r"^##(?:\s+\d+\.)?\s+(?:内容索引|章节目录|连续阅读目录|章节地图)\s*$")


def prior_moves() -> dict[str, list[str]]:
    path = ROOT / "metadata/2026-08-24-editorial-fusion-v3-map.json"
    rows = json.loads(path.read_text(encoding="utf-8"))["renamed_or_split_paths"]
    result: defaultdict[str, list[str]] = defaultdict(list)
    for row in rows:
        value = str(row["after"])
        if value not in result[str(row["before"])]:
            result[str(row["before"])].append(value)
    return dict(result)


PRIOR_MOVES = prior_moves()


@dataclass
class Block:
    title: str
    lines: list[str]


def canonical_paths() -> list[Path]:
    return sorted(
        path
        for path in ROOT.glob("src/part*/ch*/*.md")
        if path.name != "README.md"
    )


def parse_document(text: str) -> tuple[dict[str, Any], str]:
    raw, body = fusion.split_frontmatter(text)
    meta = yaml.safe_load(raw) or {}
    if not isinstance(meta, dict):
        raise ValueError("frontmatter must be a mapping")
    return meta, body


def dump_document(meta: dict[str, Any], body: str) -> str:
    raw = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=1000).rstrip()
    return f"---\n{raw}\n---\n\n{body.strip()}\n"


def unique(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[str] = set()
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def trim(lines: list[str]) -> list[str]:
    return fusion.trim_blank(lines)


def split_blocks(body: str) -> tuple[list[str], list[Block]]:
    lines = body.splitlines()
    positions = fusion.heading_positions(lines, 2)
    if not positions:
        raise ValueError("article has no H2")
    prefix = trim(lines[: positions[0][0]])
    blocks = []
    for index, (start, title) in enumerate(positions):
        end = positions[index + 1][0] if index + 1 < len(positions) else len(lines)
        blocks.append(Block(title, trim(lines[start + 1 : end])))
    return prefix, blocks


def render_blocks(prefix: list[str], blocks: list[Block]) -> str:
    result = trim(prefix)
    for block in blocks:
        if result:
            result.append("")
        result.extend([f"## {block.title}", ""])
        result.extend(trim(block.lines))
    return "\n".join(result).rstrip() + "\n"


def by_title(blocks: list[Block]) -> dict[str, Block]:
    return {block.title: block for block in blocks}


def split_subsections(lines: list[str], level: int = 3) -> dict[str, list[str]]:
    positions = fusion.heading_positions(lines, level)
    result: dict[str, list[str]] = {}
    for index, (start, title) in enumerate(positions):
        end = positions[index + 1][0] if index + 1 < len(positions) else len(lines)
        result[title] = trim(lines[start + 1 : end])
    return result


def append_h3(block: Block, title: str, content: list[str], *, shift: bool = False) -> None:
    payload = fusion.shift_headings(content, 1) if shift else content
    block.lines = trim(block.lines)
    if block.lines:
        block.lines.append("")
    block.lines.extend([f"### {title}", ""])
    block.lines.extend(trim(payload))


def relocate_links(text: str, origin: str, destination: str, moves: dict[str, str]) -> str:
    origin_path = ROOT / origin
    destination_path = ROOT / destination
    result: list[str] = []
    fenced = False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            fenced = not fenced
            result.append(line)
            continue
        if fenced:
            result.append(line)
            continue

        def replace(match: re.Match[str]) -> str:
            label, raw = match.groups()
            wrapped = raw.startswith("<") and raw.endswith(">")
            target_raw = raw[1:-1] if wrapped else raw
            path_part, marker, anchor = target_raw.partition("#")
            if not path_part or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", path_part):
                return match.group(0)
            resolved = (origin_path.parent / unquote(path_part)).resolve()
            try:
                old_relative = str(resolved.relative_to(ROOT))
            except ValueError:
                return match.group(0)
            target = DELETED_REDIRECTS.get(old_relative, moves.get(old_relative))
            if not target and old_relative in PRIOR_MOVES:
                candidates = PRIOR_MOVES[old_relative]
                key = label.casefold()
                if len(candidates) == 1:
                    target = candidates[0]
                elif re.search(r"compose|jetpack", key, re.I):
                    target = next((item for item in candidates if "compose" in item), candidates[0])
                elif re.search(r"camera|camerax|相机|拍摄", key, re.I):
                    target = next((item for item in candidates if "camerax" in item), candidates[0])
                elif re.search(r"autofdo|afdo|反馈导向", key, re.I):
                    target = next((item for item in candidates if "autofdo" in item), candidates[0])
                elif re.search(r"connectivity|网络", key, re.I):
                    target = next((item for item in candidates if "connectivity" in item), candidates[0])
                else:
                    target = candidates[0]
            if not target:
                target = old_relative
            new_link = os.path.relpath(ROOT / target, destination_path.parent)
            # Anchors into a removed duplicate are not necessarily preserved. A
            # valid article-level link is more useful than a stale fragment.
            if marker and old_relative not in DELETED_REDIRECTS:
                new_link += f"#{anchor}"
            if " " in new_link:
                new_link = f"<{new_link}>"
            return f"{label}({new_link})"

        parts = re.split(r"(`+[^`]*`+)", line)
        result.append(
            "".join(
                part if index % 2 else LINK_RE.sub(replace, part)
                for index, part in enumerate(parts)
            )
        )
    return "\n".join(result) + ("\n" if text.endswith("\n") else "")


def merge_meta(target: dict[str, Any], source: dict[str, Any], source_path: str) -> dict[str, Any]:
    result = dict(target)
    result["tags"] = unique(list(target.get("tags") or []) + list(source.get("tags") or []))
    result["sources"] = unique(list(target.get("sources") or []) + list(source.get("sources") or []))
    result["related_chapters"] = unique(
        list(target.get("related_chapters") or []) + list(source.get("related_chapters") or [])
    )
    result["consolidated_from"] = unique(
        list(target.get("consolidated_from") or [])
        + list(source.get("consolidated_from") or [])
        + [source_path]
    )
    return result


def merge_flutter(source_text: str, target_text: str) -> str:
    source_text = relocate_links(source_text, FLUTTER_SOURCE, FLUTTER_TARGET, {})
    source_meta, source_body = parse_document(source_text)
    target_meta, target_body = parse_document(target_text)
    source_blocks = by_title(split_blocks(source_body)[1])
    prefix, target_list = split_blocks(target_body)
    target_blocks = by_title(target_list)

    append_h3(
        target_blocks["一帧的公共前半段"],
        "与原生 Android HWUI 的边界",
        source_blocks["与原生 Android HWUI 的边界"].lines,
        shift=True,
    )

    tool_sections = split_subsections(source_blocks["DevTools 与 Perfetto 怎样配合"].lines)
    append_h3(
        target_blocks["在 Perfetto 中识别 Flutter 渲染管线"],
        "DevTools：先区分 Framework 与 Raster",
        tool_sections["DevTools：区分 Framework 与 Raster"],
    )
    append_h3(
        target_blocks["在 Perfetto 中识别 Flutter 渲染管线"],
        "自定义 Trace：关联 Dart、Native 与系统事件",
        tool_sections["自定义 trace event"],
    )
    workflow = split_subsections(source_blocks["一套可复现的 Flutter 帧排查流程"].lines)
    append_h3(
        target_blocks["在 Perfetto 中识别 Flutter 渲染管线"],
        "单变量 A/B 与验收",
        workflow["5. 做单变量 A/B"],
    )
    append_h3(
        target_blocks["Android 12—17 与 Flutter 的版本演进"],
        "16 KB Page Size 与 Flutter 插件",
        source_blocks["16 KB page size 与 Flutter plugin"].lines,
        shift=True,
    )

    perf = source_blocks["常见性能问题"]
    perf.lines = [
        "Trace 已经把延迟定位到 Framework、Raster、GPU、插件或宿主消费阶段后，再选择对应动作；先改代码再找证据，容易把等待转移到下一段。",
        "",
        *perf.lines,
    ]
    at = next(
        index
        for index, block in enumerate(target_list)
        if block.title == "在 Perfetto 中识别 Flutter 渲染管线"
    )
    target_list.insert(at + 1, Block("从慢帧证据到优化动作", perf.lines))

    meta = merge_meta(target_meta, source_meta, FLUTTER_SOURCE)
    meta["related_chapters"] = [item for item in meta["related_chapters"] if str(item) != "18.8"]
    meta["last_verified_against"] = (
        str(target_meta.get("last_verified_against") or "")
        + " + Flutter 3.44.8 unique workflow and 16 KB plugin boundary"
    ).strip(" +")
    return dump_document(meta, render_blocks(prefix, target_list))


def merge_profiling(source_text: str, target_text: str) -> str:
    source_text = relocate_links(source_text, PROFILING_SOURCE, PROFILING_TARGET, {})
    source_meta, source_body = parse_document(source_text)
    target_meta, target_body = parse_document(target_text)
    source_blocks = by_title(split_blocks(source_body)[1])
    prefix, target_list = split_blocks(target_body)
    target_blocks = by_title(target_list)

    append_h3(
        target_blocks["结果文件、字段与隐私"],
        "结果文件生命周期",
        source_blocks["结果文件生命周期"].lines,
        shift=True,
    )
    append_h3(
        target_blocks["结果文件、字段与隐私"],
        "Java Heap Dump 的敏感数据风险",
        source_blocks["Java heap dump 的敏感数据风险"].lines,
        shift=True,
    )
    append_h3(
        target_blocks["设备验证与旧版本降级"],
        "源码调用链核对",
        source_blocks["用源码核对调用链"].lines,
        shift=True,
    )
    target_blocks["覆盖全部失败结果"].lines.extend(
        [
            "",
            "限流不能简化成固定的“每小时几次”。Android 17 会按 profiling 类型计算不同资源成本，并分别检查小时、天、周窗口以及应用 UID 与整机预算；任一预算不足都可能拒绝请求。应用还应设置更保守的本地冷却时间，并保证同类采集串行，不能靠循环重试恢复额度。",
        ]
    )

    meta = merge_meta(target_meta, source_meta, PROFILING_SOURCE)
    meta["related_chapters"] = [item for item in meta["related_chapters"] if str(item) != "14.8"]
    if str(source_meta.get("last_verified") or "") > str(target_meta.get("last_verified") or ""):
        meta["last_verified"] = source_meta["last_verified"]
    meta["last_verified_against"] = unique(
        [target_meta.get("last_verified_against"), source_meta.get("last_verified_against")]
    )
    meta["last_verified_against"] = " + ".join(
        str(item) for item in meta["last_verified_against"] if item
    )
    return dump_document(meta, render_blocks(prefix, target_list))


def number(path: Path) -> int:
    match = re.match(r"(\d+)-", path.name)
    if not match:
        raise ValueError(f"numbered chapter file expected: {path}")
    return int(match.group(1))


def build_path_moves(paths: list[Path]) -> dict[str, str]:
    moves: dict[str, str] = {}
    deleted = set(DELETED_REDIRECTS)
    for directory in sorted(AFFECTED_DIRS):
        survivors = sorted(
            (
                path
                for path in paths
                if str(path.parent.relative_to(ROOT)) == directory
                and str(path.relative_to(ROOT)) not in deleted
            ),
            key=number,
        )
        for new_number, path in enumerate(survivors, 1):
            old = str(path.relative_to(ROOT))
            suffix = re.sub(r"^\d+-", "", path.name)
            new = str(Path(directory) / f"{new_number:02d}-{suffix}")
            if old != new:
                moves[old] = new
    return moves


def chapter_id(relative: str) -> str:
    path = Path(relative)
    chapter = re.match(r"ch(\d+)-", path.parent.name)
    item = re.match(r"(\d+)-", path.name)
    if not chapter or not item:
        raise ValueError(relative)
    return f"{int(chapter.group(1))}.{int(item.group(1))}"


def build_id_moves(paths: list[Path], path_moves: dict[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in paths:
        old = str(path.relative_to(ROOT))
        old_id = chapter_id(old)
        if old in DELETED_REDIRECTS:
            result[old_id] = chapter_id(DELETED_REDIRECTS[old])
        else:
            result[old_id] = chapter_id(path_moves.get(old, old))
    return {old: new for old, new in result.items() if old != new}


def update_document_ids(text: str, relative: str, id_moves: dict[str, str]) -> str:
    raw, body = fusion.split_frontmatter(text)
    original_meta = yaml.safe_load(raw) or {}
    if not isinstance(original_meta, dict):
        raise ValueError("frontmatter must be a mapping")
    meta = dict(original_meta)
    current = chapter_id(relative)
    meta["chapter"] = current
    if "section" in meta:
        meta["section"] = current
    if isinstance(meta.get("related_chapters"), list):
        meta["related_chapters"] = unique(
            [
                id_moves.get(str(item), str(item))
                for item in meta["related_chapters"]
                if id_moves.get(str(item), str(item)) != current
            ]
        )
    revised_body = v2.rewrite_chapter_references(body, id_moves)
    if meta == original_meta:
        return f"---\n{raw}\n---\n\n{revised_body.strip()}\n"
    return dump_document(meta, revised_body)


def build_documents() -> tuple[dict[str, tuple[str, str]], dict[str, str], dict[str, str]]:
    paths = canonical_paths()
    path_moves = build_path_moves(paths)
    id_moves = build_id_moves(paths, path_moves)
    merged = {
        FLUTTER_TARGET: merge_flutter(
            (ROOT / FLUTTER_SOURCE).read_text(encoding="utf-8"),
            (ROOT / FLUTTER_TARGET).read_text(encoding="utf-8"),
        ),
        PROFILING_TARGET: merge_profiling(
            (ROOT / PROFILING_SOURCE).read_text(encoding="utf-8"),
            (ROOT / PROFILING_TARGET).read_text(encoding="utf-8"),
        ),
    }
    documents: dict[str, tuple[str, str]] = {}
    for path in paths:
        old = str(path.relative_to(ROOT))
        if old in DELETED_REDIRECTS:
            continue
        new = path_moves.get(old, old)
        text = merged.get(old, path.read_text(encoding="utf-8"))
        text = relocate_links(text, old, new, path_moves)
        text = update_document_ids(text, new, id_moves)
        documents[new] = (old, text)
    return documents, path_moves, id_moves


def title_and_id(text: str) -> tuple[str, str]:
    meta, _ = parse_document(text)
    return str(meta["title"]), str(meta["chapter"])


def rewrite_auxiliary(
    relative: str,
    path_moves: dict[str, str],
    id_moves: dict[str, str],
) -> str:
    text = (ROOT / relative).read_text(encoding="utf-8")
    text = relocate_links(text, relative, relative, path_moves)
    return v2.rewrite_chapter_references(text, id_moves)


def rebuild_readme(
    relative: str,
    documents: dict[str, tuple[str, str]],
    path_moves: dict[str, str],
    id_moves: dict[str, str],
) -> str:
    text = rewrite_auxiliary(relative, path_moves, id_moves)
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if INDEX_HEADING_RE.match(line)), None)
    if start is None:
        raise ValueError(f"README index heading missing: {relative}")
    end = next((index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")), len(lines))
    directory = str(Path(relative).parent)
    rows = sorted(
        (path, title_and_id(value))
        for path, (_, value) in documents.items()
        if str(Path(path).parent) == directory
    )
    index = [lines[start], ""] + [
        f"- [{chapter} {title}]({Path(path).name})"
        for path, (title, chapter) in rows
    ] + [""]
    return "\n".join(lines[:start] + index + lines[end:]).rstrip() + "\n"


def rebuild_summary(
    documents: dict[str, tuple[str, str]],
    path_moves: dict[str, str],
    id_moves: dict[str, str],
) -> str:
    relative = "src/SUMMARY.md"
    lines = rewrite_auxiliary(relative, path_moves, id_moves).splitlines()
    index = 0
    while index < len(lines):
        match = re.search(r"\(([^)]+/README\.md)\)", lines[index])
        if not match:
            index += 1
            continue
        directory = "src/" + str(Path(match.group(1)).parent)
        if directory not in AFFECTED_DIRS:
            index += 1
            continue
        end = index + 1
        while end < len(lines) and lines[end].startswith("  - "):
            end += 1
        rows = sorted(
            (path, title_and_id(value))
            for path, (_, value) in documents.items()
            if str(Path(path).parent) == directory
        )
        lines[index + 1 : end] = [
            f"  - [{chapter} {title}]({str(Path(path).relative_to('src'))})"
            for path, (title, chapter) in rows
        ]
        index += 1 + len(rows)
    return "\n".join(lines).rstrip() + "\n"


def replace_json_values(value: Any, path_moves: dict[str, str], id_moves: dict[str, str]) -> Any:
    if isinstance(value, str):
        if value in DELETED_REDIRECTS:
            return DELETED_REDIRECTS[value]
        if value in path_moves:
            return path_moves[value]
        return id_moves.get(value, value)
    if isinstance(value, list):
        return [replace_json_values(item, path_moves, id_moves) for item in value]
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            new_key = DELETED_REDIRECTS.get(key, path_moves.get(key, id_moves.get(key, key)))
            result[new_key] = replace_json_values(item, path_moves, id_moves)
        return result
    return value


def build_json_updates(path_moves: dict[str, str], id_moves: dict[str, str]) -> dict[str, str]:
    result = {}
    for path in sorted((ROOT / "metadata").glob("*.json")):
        relative = str(path.relative_to(ROOT))
        if relative in HISTORICAL_JSON or relative == MAP_V4:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        revised = replace_json_values(data, path_moves, id_moves)
        value = json.dumps(revised, ensure_ascii=False, indent=2) + "\n"
        if value != path.read_text(encoding="utf-8"):
            result[relative] = value
    return result


def validate_documents(documents: dict[str, tuple[str, str]]) -> None:
    if len(documents) != 287:
        raise ValueError(f"expected 287 canonical bodies, got {len(documents)}")
    by_dir: defaultdict[str, list[int]] = defaultdict(list)
    for relative, (_, text) in documents.items():
        fusion.validate_markdown(text, ROOT / relative)
        _, actual = title_and_id(text)
        expected = chapter_id(relative)
        if actual != expected:
            raise ValueError(f"chapter/path mismatch: {relative}: {actual} != {expected}")
        by_dir[str(Path(relative).parent)].append(int(actual.split(".")[1]))
    for directory, ids in by_dir.items():
        if sorted(ids) != list(range(1, len(ids) + 1)):
            raise ValueError(f"noncontinuous numbering: {directory}: {sorted(ids)}")


def build_map(path_moves: dict[str, str], id_moves: dict[str, str]) -> str:
    report = {
        "schema_version": 1,
        "reviewed_at": "2026-08-24",
        "before_count": 289,
        "after_count": 287,
        "merged_paths": [
            {"source": source, "target": target, "recoverable_from_git": True}
            for source, target in DELETED_REDIRECTS.items()
        ],
        "renamed_paths": [
            {"before": old, "after": new, "chapter": chapter_id(new)}
            for old, new in sorted(path_moves.items())
        ],
        "chapter_id_moves": id_moves,
    }
    return json.dumps(report, ensure_ascii=False, indent=2) + "\n"


def apply_outputs(
    documents: dict[str, tuple[str, str]],
    path_moves: dict[str, str],
    auxiliary: dict[str, str],
) -> None:
    affected_old = set(path_moves) | set(DELETED_REDIRECTS)
    affected_new = {path_moves.get(old, old) for old in affected_old if old not in DELETED_REDIRECTS}
    affected_new.update(DELETED_REDIRECTS.values())
    with tempfile.TemporaryDirectory(prefix="aiw-overlap-consolidation-") as temp_value:
        temp_root = Path(temp_value)
        for relative in affected_new:
            staged = temp_root / relative
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_text(documents[relative][1], encoding="utf-8", newline="\n")
        for old in sorted(affected_old):
            path = ROOT / old
            if path.exists():
                path.unlink()
        for relative in sorted(affected_new):
            target = ROOT / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text((temp_root / relative).read_text(encoding="utf-8"), encoding="utf-8", newline="\n")

    for relative, (_, text) in documents.items():
        path = ROOT / relative
        if relative not in affected_new and text != path.read_text(encoding="utf-8"):
            path.write_text(text, encoding="utf-8", newline="\n")
    for relative, text in auxiliary.items():
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    documents, path_moves, id_moves = build_documents()
    validate_documents(documents)

    auxiliary: dict[str, str] = {}
    for path in sorted(ROOT.glob("src/**/*.md")):
        relative = str(path.relative_to(ROOT))
        if relative in {str(item.relative_to(ROOT)) for item in canonical_paths()}:
            continue
        auxiliary[relative] = rewrite_auxiliary(relative, path_moves, id_moves)
    for directory in AFFECTED_DIRS:
        relative = str(Path(directory) / "README.md")
        auxiliary[relative] = rebuild_readme(relative, documents, path_moves, id_moves)
    auxiliary["src/SUMMARY.md"] = rebuild_summary(documents, path_moves, id_moves)
    auxiliary.update(build_json_updates(path_moves, id_moves))
    auxiliary[MAP_V4] = build_map(path_moves, id_moves)

    if args.apply:
        apply_outputs(documents, path_moves, auxiliary)
    print(
        json.dumps(
            {
                "mode": "apply" if args.apply else "dry-run",
                "canonical_bodies": len(documents),
                "merged_sources": DELETED_REDIRECTS,
                "renamed_paths": len(path_moves),
                "chapter_id_moves": id_moves,
                "json_updates": len(build_json_updates(path_moves, id_moves)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
