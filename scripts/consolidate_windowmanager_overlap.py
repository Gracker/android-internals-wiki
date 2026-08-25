#!/usr/bin/env python3
"""Fuse the duplicate WindowManager article into the display/WMS architecture.

The source article contains several distinct evidence paths, so this pass does
not append it wholesale. StartingWindow, relayout triggers, transition version
boundaries, large-screen configuration, public SurfaceSyncGroup and input
snapshot publication are embedded under their owning WMS mechanisms. Parallel
descriptions of WMS, Surface ownership and Perfetto basics are not duplicated.

Dry-run by default. The removed source remains recoverable from Git.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import consolidate_articles_v2 as v2  # noqa: E402
import consolidate_obvious_overlaps as prior  # noqa: E402
import editorial_fusion_rewrite as fusion  # noqa: E402


SOURCE = "src/part1-fundamentals/ch02-rendering/08-window-manager.md"
TARGET = "src/part1-fundamentals/ch01-architecture/16-display-windowmanager-architecture.md"
REDIRECTS = {SOURCE: TARGET}
AFFECTED_DIR = "src/part1-fundamentals/ch02-rendering"
MAP_PATH = "metadata/2026-08-24-editorial-fusion-v5-map.json"
HISTORICAL_JSON = {
    "metadata/2026-08-24-content-consolidation-v2-map.json",
    "metadata/2026-08-24-editorial-fusion-v3-map.json",
    "metadata/2026-08-24-editorial-fusion-v4-map.json",
    MAP_PATH,
}
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^(#{3,4})\s+\d+(?:\.\d+)*(?:\.)?\s+(.+?)\s*$")
LINK_RE = re.compile(r"(!?\[[^\]\n]*\])\((<[^>\n]+>|[^)\n]+)\)")
INDEX_HEADING_RE = re.compile(r"^##(?:\s+\d+\.)?\s+(?:内容索引|章节目录|连续阅读目录|章节地图)\s*$")


def canonical_paths() -> list[Path]:
    return sorted(
        path
        for path in ROOT.glob("src/part*/ch*/*.md")
        if path.name != "README.md"
    )


def trim(lines: list[str]) -> list[str]:
    return fusion.trim_blank(lines)


def split_level(lines: list[str], level: int) -> tuple[list[str], list[prior.Block]]:
    positions = fusion.heading_positions(lines, level)
    if not positions:
        return trim(lines), []
    prefix = trim(lines[: positions[0][0]])
    blocks: list[prior.Block] = []
    for index, (start, title) in enumerate(positions):
        end = positions[index + 1][0] if index + 1 < len(positions) else len(lines)
        blocks.append(prior.Block(title, trim(lines[start + 1 : end])))
    return prefix, blocks


def render_level(prefix: list[str], blocks: list[prior.Block], level: int) -> list[str]:
    result = trim(prefix)
    marks = "#" * level
    for block in blocks:
        if result:
            result.append("")
        result.extend([f"{marks} {block.title}", ""])
        result.extend(trim(block.lines))
    return trim(result)


def block_map(blocks: list[prior.Block]) -> dict[str, prior.Block]:
    return {block.title: block for block in blocks}


def insert_after(blocks: list[prior.Block], anchor: str, item: prior.Block) -> None:
    index = next(index for index, block in enumerate(blocks) if block.title == anchor)
    blocks.insert(index + 1, item)


def strip_wms_numbers(lines: list[str]) -> list[str]:
    result: list[str] = []
    fenced = False
    for line in lines:
        if FENCE_RE.match(line):
            fenced = not fenced
            result.append(line)
            continue
        if fenced:
            result.append(line)
            continue
        match = HEADING_RE.match(line)
        result.append(f"{match.group(1)} {match.group(2)}" if match else line)
    return result


def source_section(block: prior.Block, title: str, level: int = 3) -> list[str]:
    _, sections = split_level(block.lines, level)
    return list(block_map(sections)[title].lines)


def before_line(lines: list[str], prefix: str) -> list[str]:
    index = next((index for index, line in enumerate(lines) if line.startswith(prefix)), len(lines))
    return trim(lines[:index])


def nested_source_block(block: prior.Block, renames: dict[str, str] | None = None) -> list[str]:
    prefix, sections = split_level(block.lines, 3)
    renames = renames or {}
    revised = [prior.Block(renames.get(item.title, item.title), item.lines) for item in sections]
    return render_level(prefix, revised, 4)


def merge_windowmanager(source_text: str, target_text: str) -> str:
    source_text = relocate_links(source_text, SOURCE, TARGET, {})
    source_meta, source_body = prior.parse_document(source_text)
    target_meta, target_body = prior.parse_document(target_text)
    _, source_blocks_list = prior.split_blocks(source_body)
    source_blocks = prior.by_title(source_blocks_list)
    prefix, target_list = prior.split_blocks(target_body)
    target_blocks = prior.by_title(target_list)

    old_intro = (
        "窗口管理负责窗口身份、层级、布局和 Surface 生命周期，渲染系统负责产生和合成缓冲区。"
        "定位显示问题时，需要先把 WMS 的窗口状态变化与 SurfaceFlinger 的图层和事务对应起来。"
    )
    new_intro = (
        "窗口管理负责窗口身份、层级、布局和 Surface 生命周期，渲染系统负责产生和合成缓冲区。"
        "本文先建立应用窗口到显示设备的公共主线，再沿 addWindow、StartingWindow、relayout、"
        "BLAST 同步、转场和输入窗口快照追踪一次窗口变化。定位问题时，应把 WMS 状态、应用 buffer "
        "与 SurfaceFlinger 的 layer/present 放在同一时间轴上。"
    )
    joined_prefix = "\n".join(prefix)
    if old_intro not in joined_prefix:
        raise ValueError("target opening paragraph changed")
    prefix = joined_prefix.replace(old_intro, new_intro, 1).splitlines()

    wms = target_blocks["WindowManager 的窗口、Surface 与事务"]
    wms.lines = strip_wms_numbers(wms.lines)
    wms_prefix, sections = split_level(wms.lines, 3)
    section_by_title = block_map(sections)

    transaction_lines = source_section(
        source_blocks["Window 与 Surface 的关系"],
        "三类 transaction 的职责不同",
    )
    transaction_lines = [
        "窗口状态变化会同时经过容器、图层几何与内容 buffer 三条事务链。先分清事务承载的对象，才能判断 resize 中的一帧错位发生在哪个边界。",
        "",
        *transaction_lines,
    ]
    insert_after(
        sections,
        "从 `addView()` 到屏幕上的 Layer",
        prior.Block("容器、图层与内容事务的职责边界", transaction_lines),
    )

    starting_lines = nested_source_block(
        source_blocks["StartingWindow 与启动性能"],
        {
            "StartingWindow 的工作原理": "决策与创建为何分属 WMS 和 WM Shell",
            "Android 12 SplashScreen API": "Android 12 SplashScreen API 的责任边界",
            "StartingWindow 的时机陷阱": "移除时机：首帧完成不等于已经呈现",
        },
    )
    starting_lines = [
        "窗口身份建立后，冷启动还需要在应用主窗口交出首帧前维持可见反馈。StartingWindow 是这段窗口生命周期的一部分，但它的创建者、内容生产者和移除信号不在同一进程。",
        "",
        *starting_lines,
    ]
    insert_after(
        sections,
        "`addWindow()`：先证明“这个窗口有资格存在”",
        prior.Block("StartingWindow 与应用首帧交接", starting_lines),
    )

    relayout = section_by_title["relayout：同步返回与异步发送的选择"]
    relayout_prefix, relayout_parts = split_level(relayout.lines, 4)
    trigger_lines = source_section(
        source_blocks["relayoutWindow：重新协商窗口契约"],
        "什么触发 relayoutWindow",
    )
    trigger_lines = before_line(trigger_lines, "Android 14+ 增加了")
    schedule_lines = source_section(
        source_blocks["relayoutWindow：重新协商窗口契约"],
        "scheduleTraversals() 与 performTraversals() 的职责边界",
    )
    insets_lines = source_section(source_blocks["扩展"], "🔸 WindowInsets 与布局性能")
    relayout_parts.insert(0, prior.Block("哪些 traversal 会跨进程 relayout", trigger_lines))
    relayout_parts.insert(
        1,
        prior.Block("scheduleTraversals 与 performTraversals 的进程边界", schedule_lines),
    )
    relayout_parts.append(prior.Block("WindowInsets 更新与应用布局成本", insets_lines))
    relayout.lines = render_level(relayout_prefix, relayout_parts, 4)

    sync = section_by_title["`BLASTSyncEngine`：多 Surface 状态的原子交付"]
    sync_prefix, sync_parts = split_level(sync.lines, 4)
    sync_parts.append(
        prior.Block(
            "与公开 `SurfaceSyncGroup` 的边界",
            [
                "API 34 起公开的 `SurfaceSyncGroup` 面向 `AttachedSurfaceControl`、`SurfaceView`、`SurfaceControlViewHost` 等 Surface，可跨组件甚至跨进程等待多个 Surface ready 后一起应用 transaction。它与 system_server 内部的 `BLASTSyncEngine` 都解决“多个 Surface 何时一起可见”，但调用方和同步对象不同。",
                "",
                "看到 sync id 或超时时，先确认它属于 WMS 的 WindowContainer 同步，还是应用/组件侧的 `SurfaceSyncGroup`。前者继续检查 `WindowState` draw state、SyncGroup 依赖和 transition ready；后者检查参与 Surface 是否报告 ready、回调进程是否存活，以及合并 transaction 是否真正提交。",
            ],
        )
    )
    sync.lines = render_level(sync_prefix, sync_parts, 4)

    transition = section_by_title["窗口转场与动画"]
    transition_prefix, transition_parts = split_level(transition.lines, 4)
    transition_parts.extend(
        [
            prior.Block(
                "Activity 切换的版本边界",
                source_section(source_blocks["Window 动画与过渡性能"], "Activity 切换动画"),
            ),
            prior.Block(
                "Predictive Back 的跨组件路径",
                source_section(source_blocks["Window 动画与过渡性能"], "Predictive Back 动画"),
            ),
        ]
    )
    transition.lines = render_level(transition_prefix, transition_parts, 4)

    input_section = section_by_title["WMS 与输入系统的分工"]
    input_prefix, input_parts = split_level(input_section.lines, 4)
    input_parts.append(
        prior.Block(
            "`WindowInfosUpdate` 的发布与消费时序",
            [
                "Android 17 的 `InputMonitor.UpdateInputWindows` 在 `mGlobalLock` 下按 Z-order 填充窗口输入信息，再用 `SurfaceControl.Transaction.setInputWindowInfo()` 把 touchable region、transform、focusability 与对应 layer 一起提交。非立即路径会先合并进 `DisplayContent` 的 pending transaction，而不是为每个输入事件同步询问 WMS。",
                "",
                "SurfaceFlinger 消费 transaction 后，从已提交的 layer snapshot 生成 `WindowInfo`/`DisplayInfo`，`updateInputFlinger()` 再发布 `WindowInfosUpdate`。InputDispatcher 的 `onWindowInfosChanged()` 按 Display 替换窗口缓存并唤醒 poll loop；`onWindowInfosReported()` 表示监听器已处理通知，不是 InputDispatcher 更新命中缓存的前置等待。",
                "",
                "窗口移动、转场、焦点或 touchable region 变化时，应依次对齐：WMS 标记并提交 input info、SurfaceFlinger 生成新 snapshot、InputDispatcher 替换缓存和处理 focus request、应用 input channel 收到事件。点击无响应可能来自旧 snapshot、不可触摸窗口、未完成的焦点请求、channel backlog 或应用主线程迟到，不能只凭焦点切换下结论。",
            ],
        )
    )
    input_section.lines = render_level(input_prefix, input_parts, 4)

    multiwindow = section_by_title["多窗口、自由窗体与大屏"]
    multi_prefix, multi_parts = split_level(multiwindow.lines, 4)
    multi_parts.extend(
        [
            prior.Block(
                "按 Display、进程与 ViewRoot 划分共享域",
                source_section(
                    source_blocks["WMS 的定位：窗口状态与 Surface 拓扑"],
                    "多窗口先按共享域分组",
                ),
            ),
            prior.Block(
                "折叠屏与大屏的配置边界",
                source_section(
                    source_blocks["多窗口、折叠屏与 Desktop Mode"],
                    "折叠屏与大屏配置变更",
                ),
            ),
            prior.Block(
                "Connected Display Desktop 的设备边界",
                source_section(
                    source_blocks["多窗口、折叠屏与 Desktop Mode"],
                    "Android 16 QPR3 Connected Display Desktop",
                ),
            ),
        ]
    )
    multiwindow.lines = render_level(multi_prefix, multi_parts, 4)

    wms.lines = render_level(wms_prefix, sections, 3)
    meta = prior.merge_meta(target_meta, source_meta, SOURCE)
    meta["last_consolidated_at"] = "2026-08-24"
    meta["last_verified"] = max(
        str(target_meta.get("last_verified") or ""),
        str(source_meta.get("last_verified") or ""),
    )
    meta["last_verified_against"] = " + ".join(
        value
        for value in prior.unique(
            [
                str(target_meta.get("last_verified_against") or ""),
                str(source_meta.get("last_verified_against") or ""),
            ]
        )
        if value
    )
    return prior.dump_document(meta, prior.render_blocks(prefix, target_list))


def number(path: Path) -> int:
    match = re.match(r"(\d+)-", path.name)
    if not match:
        raise ValueError(f"numbered chapter file expected: {path}")
    return int(match.group(1))


def build_path_moves(paths: list[Path]) -> dict[str, str]:
    survivors = sorted(
        (
            path
            for path in paths
            if str(path.parent.relative_to(ROOT)) == AFFECTED_DIR
            and str(path.relative_to(ROOT)) != SOURCE
        ),
        key=number,
    )
    result: dict[str, str] = {}
    for new_number, path in enumerate(survivors, 1):
        old = str(path.relative_to(ROOT))
        suffix = re.sub(r"^\d+-", "", path.name)
        new = str(Path(AFFECTED_DIR) / f"{new_number:02d}-{suffix}")
        if new != old:
            result[old] = new
    return result


def build_id_moves(paths: list[Path], path_moves: dict[str, str]) -> dict[str, str]:
    result: dict[str, str] = {prior.chapter_id(SOURCE): prior.chapter_id(TARGET)}
    for path in paths:
        old = str(path.relative_to(ROOT))
        if old == SOURCE:
            continue
        new = path_moves.get(old, old)
        old_id = prior.chapter_id(old)
        new_id = prior.chapter_id(new)
        if old_id != new_id:
            result[old_id] = new_id
    return result


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
            target = REDIRECTS.get(old_relative, moves.get(old_relative, old_relative))
            new_link = os.path.relpath(ROOT / target, destination_path.parent)
            if marker and old_relative not in REDIRECTS:
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


def build_documents() -> tuple[dict[str, tuple[str, str]], dict[str, str], dict[str, str]]:
    paths = canonical_paths()
    path_moves = build_path_moves(paths)
    id_moves = build_id_moves(paths, path_moves)
    merged_target = merge_windowmanager(
        (ROOT / SOURCE).read_text(encoding="utf-8"),
        (ROOT / TARGET).read_text(encoding="utf-8"),
    )
    documents: dict[str, tuple[str, str]] = {}
    for path in paths:
        old = str(path.relative_to(ROOT))
        if old == SOURCE:
            continue
        new = path_moves.get(old, old)
        text = merged_target if old == TARGET else path.read_text(encoding="utf-8")
        text = relocate_links(text, old, new, path_moves)
        text = prior.update_document_ids(text, new, id_moves)
        documents[new] = (old, text)
    return documents, path_moves, id_moves


def rewrite_auxiliary(relative: str, path_moves: dict[str, str], id_moves: dict[str, str]) -> str:
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
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    rows = sorted(
        (path, prior.title_and_id(value))
        for path, (_, value) in documents.items()
        if str(Path(path).parent) == AFFECTED_DIR
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
        if not match or "src/" + str(Path(match.group(1)).parent) != AFFECTED_DIR:
            index += 1
            continue
        end = index + 1
        while end < len(lines) and lines[end].startswith("  - "):
            end += 1
        rows = sorted(
            (path, prior.title_and_id(value))
            for path, (_, value) in documents.items()
            if str(Path(path).parent) == AFFECTED_DIR
        )
        lines[index + 1 : end] = [
            f"  - [{chapter} {title}]({str(Path(path).relative_to('src'))})"
            for path, (title, chapter) in rows
        ]
        index += 1 + len(rows)
    return "\n".join(lines).rstrip() + "\n"


def replace_json_values(value: Any, path_moves: dict[str, str], id_moves: dict[str, str]) -> Any:
    if isinstance(value, str):
        if value in REDIRECTS:
            return REDIRECTS[value]
        if value in path_moves:
            return path_moves[value]
        return id_moves.get(value, value)
    if isinstance(value, list):
        return [replace_json_values(item, path_moves, id_moves) for item in value]
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            new_key = REDIRECTS.get(key, path_moves.get(key, id_moves.get(key, key)))
            result[new_key] = replace_json_values(item, path_moves, id_moves)
        return result
    return value


def build_json_updates(path_moves: dict[str, str], id_moves: dict[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted((ROOT / "metadata").glob("*.json")):
        relative = str(path.relative_to(ROOT))
        if relative in HISTORICAL_JSON:
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


def build_map(path_moves: dict[str, str], id_moves: dict[str, str]) -> str:
    report = {
        "schema_version": 1,
        "reviewed_at": "2026-08-24",
        "before_count": 287,
        "after_count": 286,
        "merged_paths": [
            {"source": SOURCE, "target": TARGET, "recoverable_from_git": True}
        ],
        "renamed_paths": [
            {"before": old, "after": new, "chapter": prior.chapter_id(new)}
            for old, new in sorted(path_moves.items())
        ],
        "chapter_id_moves": id_moves,
    }
    return json.dumps(report, ensure_ascii=False, indent=2) + "\n"


def validate_documents(documents: dict[str, tuple[str, str]]) -> None:
    if len(documents) != 286:
        raise ValueError(f"expected 286 canonical bodies, got {len(documents)}")
    by_dir: defaultdict[str, list[int]] = defaultdict(list)
    for relative, (_, text) in documents.items():
        fusion.validate_markdown(text, ROOT / relative)
        _, actual = prior.title_and_id(text)
        expected = prior.chapter_id(relative)
        if actual != expected:
            raise ValueError(f"chapter/path mismatch: {relative}: {actual} != {expected}")
        by_dir[str(Path(relative).parent)].append(int(actual.split(".")[1]))
    for directory, ids in by_dir.items():
        if sorted(ids) != list(range(1, len(ids) + 1)):
            raise ValueError(f"noncontinuous numbering: {directory}: {sorted(ids)}")


def validate_local_links(texts: dict[str, str]) -> int:
    known = set(texts)
    checked = 0
    broken: list[str] = []
    for relative, text in texts.items():
        fenced = False
        for line_no, line in enumerate(text.splitlines(), 1):
            if FENCE_RE.match(line):
                fenced = not fenced
                continue
            if fenced:
                continue
            for match in LINK_RE.finditer(line):
                raw = match.group(2)
                target_raw = raw[1:-1] if raw.startswith("<") and raw.endswith(">") else raw
                path_part = target_raw.partition("#")[0]
                if not path_part or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", path_part):
                    continue
                resolved = ((ROOT / relative).parent / unquote(path_part)).resolve()
                try:
                    target = str(resolved.relative_to(ROOT))
                except ValueError:
                    continue
                if Path(target).suffix.lower() != ".md":
                    continue
                checked += 1
                if target not in known and not (
                    not target.startswith("src/") and (ROOT / target).exists()
                ):
                    broken.append(f"{relative}:{line_no} -> {target}")
    if broken:
        raise ValueError("broken local links:\n" + "\n".join(broken[:50]))
    return checked


def apply_outputs(
    documents: dict[str, tuple[str, str]],
    path_moves: dict[str, str],
    auxiliary: dict[str, str],
) -> None:
    affected_old = set(path_moves) | {SOURCE}
    affected_new = {path_moves.get(old, old) for old in affected_old if old != SOURCE}
    affected_new.add(TARGET)
    with tempfile.TemporaryDirectory(prefix="aiw-windowmanager-consolidation-") as temp_value:
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
            target.write_text(
                (temp_root / relative).read_text(encoding="utf-8"),
                encoding="utf-8",
                newline="\n",
            )

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

    current_canonical = {str(path.relative_to(ROOT)) for path in canonical_paths()}
    auxiliary: dict[str, str] = {}
    for path in sorted(ROOT.glob("src/**/*.md")):
        relative = str(path.relative_to(ROOT))
        if relative in current_canonical:
            continue
        auxiliary[relative] = rewrite_auxiliary(relative, path_moves, id_moves)
    readme = str(Path(AFFECTED_DIR) / "README.md")
    auxiliary[readme] = rebuild_readme(readme, documents, path_moves, id_moves)
    auxiliary["src/SUMMARY.md"] = rebuild_summary(documents, path_moves, id_moves)
    auxiliary.update(build_json_updates(path_moves, id_moves))
    auxiliary[MAP_PATH] = build_map(path_moves, id_moves)

    future_markdown = {relative: text for relative, (_, text) in documents.items()}
    future_markdown.update(
        {
            relative: text
            for relative, text in auxiliary.items()
            if relative.startswith("src/") and relative.endswith(".md")
        }
    )
    checked_links = validate_local_links(future_markdown)
    if args.apply:
        apply_outputs(documents, path_moves, auxiliary)
    print(
        json.dumps(
            {
                "mode": "apply" if args.apply else "dry-run",
                "canonical_bodies": len(documents),
                "merged_sources": REDIRECTS,
                "renamed_paths": len(path_moves),
                "chapter_id_moves": id_moves,
                "validated_local_links": checked_links,
                "json_updates": len(build_json_updates(path_moves, id_moves)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
