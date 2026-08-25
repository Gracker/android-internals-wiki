#!/usr/bin/env python3
"""Split four semantically invalid v2 merge groups and renumber their chapters.

Dry-run is the default. The apply path stages all canonical outputs first, then
replaces only the explicitly affected files. Local Markdown links, chapter ids,
related_chapters, chapter README indexes and SUMMARY entries are updated in the
same transaction.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
fusion = importlib.import_module("editorial_fusion_rewrite")
v2 = importlib.import_module("consolidate_articles_v2")

MAP_V2 = ROOT / "metadata/2026-08-24-content-consolidation-v2-map.json"
MAP_V3 = ROOT / "metadata/2026-08-24-editorial-fusion-v3-map.json"
FENCE_RE = re.compile(r"^\s*(```|~~~)")
LINK_RE = re.compile(r"(!?\[[^\]\n]*\])\((<[^>\n]+>|[^)\n]+)\)")


GROUP_ART = "src/part1-fundamentals/ch01-architecture/05-art-compilation-optimization-deoptimization.md"
GROUP_TELEPHONY = "src/part1-fundamentals/ch01-architecture/24-telephony-connectivity-services.md"
GROUP_UI = "src/part2-performance/ch18-rendering-pipelines/08-flutter-compose-rendering-pipelines.md"
GROUP_MEDIA = "src/part5-app/ch22-rendering-practice/18-media3-camerax-rendering.md"


PATH_MOVES = {
    GROUP_ART: "src/part1-fundamentals/ch01-architecture/05-art-compilation-verification-deoptimization.md",
    GROUP_TELEPHONY: "src/part1-fundamentals/ch01-architecture/24-telephony-service.md",
    "src/part1-fundamentals/ch01-architecture/25-notificationmanager-architecture-performance.md": "src/part1-fundamentals/ch01-architecture/26-notificationmanager-architecture-performance.md",
    "src/part1-fundamentals/ch01-architecture/26-biometricservice-architecture-performance.md": "src/part1-fundamentals/ch01-architecture/27-biometricservice-architecture-performance.md",
    "src/part1-fundamentals/ch01-architecture/27-locationmanager-architecture-performance.md": "src/part1-fundamentals/ch01-architecture/28-locationmanager-architecture-performance.md",
    "src/part1-fundamentals/ch01-architecture/28-cgroup-v1-v2-process-isolation.md": "src/part1-fundamentals/ch01-architecture/29-cgroup-v1-v2-process-isolation.md",
    "src/part4-system/ch16-aosp/04-profile-dm-sdm-install-compilation.md": "src/part4-system/ch16-aosp/05-profile-dm-sdm-install-compilation.md",
    "src/part4-system/ch16-aosp/05-system-boot-time-optimization.md": "src/part4-system/ch16-aosp/06-system-boot-time-optimization.md",
    "src/part4-system/ch16-aosp/06-appflow-large-app-cold-launch-memory-scheduling.md": "src/part4-system/ch16-aosp/07-appflow-large-app-cold-launch-memory-scheduling.md",
    "src/part4-system/ch16-aosp/07-rust-system-services-performance.md": "src/part4-system/ch16-aosp/08-rust-system-services-performance.md",
    "src/part4-system/ch16-aosp/08-agent-native-os.md": "src/part4-system/ch16-aosp/09-agent-native-os.md",
    GROUP_UI: "src/part2-performance/ch18-rendering-pipelines/08-flutter-rendering-pipeline.md",
    "src/part2-performance/ch18-rendering-pipelines/09-webview-rendering.md": "src/part2-performance/ch18-rendering-pipelines/10-webview-rendering.md",
    "src/part2-performance/ch18-rendering-pipelines/10-camera-pipeline.md": "src/part2-performance/ch18-rendering-pipelines/11-camera-pipeline.md",
    "src/part2-performance/ch18-rendering-pipelines/11-video-overlay-media3-codec-pipeline.md": "src/part2-performance/ch18-rendering-pipelines/12-video-overlay-media3-codec-pipeline.md",
    "src/part2-performance/ch18-rendering-pipelines/12-game-engine.md": "src/part2-performance/ch18-rendering-pipelines/13-game-engine.md",
    "src/part2-performance/ch18-rendering-pipelines/13-variable-refresh-rate.md": "src/part2-performance/ch18-rendering-pipelines/14-variable-refresh-rate.md",
    "src/part2-performance/ch18-rendering-pipelines/14-eyedropper-crossdevice.md": "src/part2-performance/ch18-rendering-pipelines/15-eyedropper-crossdevice.md",
    "src/part2-performance/ch18-rendering-pipelines/15-android-xr-spatial-ui-rendering.md": "src/part2-performance/ch18-rendering-pipelines/16-android-xr-spatial-ui-rendering.md",
    "src/part2-performance/ch18-rendering-pipelines/16-webgpu-android-pipeline.md": "src/part2-performance/ch18-rendering-pipelines/17-webgpu-android-pipeline.md",
    GROUP_MEDIA: "src/part5-app/ch22-rendering-practice/18-media3-video-rendering.md",
}

NEW_PATHS = {
    "connectivity": "src/part1-fundamentals/ch01-architecture/25-connectivity-service.md",
    "autofdo": "src/part4-system/ch16-aosp/04-autofdo-feedback-directed-optimization.md",
    "compose": "src/part2-performance/ch18-rendering-pipelines/09-compose-rendering-pipeline.md",
    "camerax": "src/part5-app/ch22-rendering-practice/19-camerax-rendering.md",
}

ID_MOVES = {
    "1.25": "1.26",
    "1.26": "1.27",
    "1.27": "1.28",
    "1.28": "1.29",
    "16.4": "16.5",
    "16.5": "16.6",
    "16.6": "16.7",
    "16.7": "16.8",
    "16.8": "16.9",
    "18.9": "18.10",
    "18.10": "18.11",
    "18.11": "18.12",
    "18.12": "18.13",
    "18.13": "18.14",
    "18.14": "18.15",
    "18.15": "18.16",
    "18.16": "18.17",
}

SOURCE_SPECS = {
    "telephony": {
        "group": GROUP_TELEPHONY,
        "block": "Android 17 TelephonyManager 架构、状态传播与性能边界",
        "source": "src/part1-fundamentals/ch01-architecture/42-telephonymanager-architecture-performance.md",
        "target": PATH_MOVES[GROUP_TELEPHONY],
        "id": "1.24",
        "title": "Telephony 服务架构、状态传播与回调",
    },
    "connectivity": {
        "group": GROUP_TELEPHONY,
        "block": "Android 17 ConnectivityManager：架构、网络选择与性能",
        "source": "src/part1-fundamentals/ch01-architecture/43-connectivitymanager-architecture-performance.md",
        "target": NEW_PATHS["connectivity"],
        "id": "1.25",
        "title": "Connectivity 服务、网络选择与回调",
    },
    "flutter": {
        "group": GROUP_UI,
        "block": "Android 17 Flutter 渲染管线",
        "source": "src/part2-performance/ch18-rendering-pipelines/12-flutter-rendering.md",
        "target": PATH_MOVES[GROUP_UI],
        "id": "18.8",
        "title": "Flutter 渲染管线：Engine、Impeller 与 Surface",
    },
    "compose": {
        "group": GROUP_UI,
        "block": "Android 17 Jetpack Compose 渲染管线架构",
        "source": "src/part2-performance/ch18-rendering-pipelines/23-compose-rendering-pipeline.md",
        "target": NEW_PATHS["compose"],
        "id": "18.9",
        "title": "Jetpack Compose 渲染管线：Composition、Layout 与 RenderNode",
    },
    "media3": {
        "group": GROUP_MEDIA,
        "block": "Media3 视频播放：渲染管线、帧时序与排障",
        "source": "src/part5-app/ch22-rendering-practice/30-media3-video-rendering.md",
        "target": PATH_MOVES[GROUP_MEDIA],
        "id": "22.18",
        "title": "Media3 视频播放：解码、帧时序与渲染",
    },
    "camerax": {
        "group": GROUP_MEDIA,
        "block": "CameraX：性能边界、配置与排障（Android 15–17）",
        "source": "src/part5-app/ch22-rendering-practice/31-camerax-performance.md",
        "target": NEW_PATHS["camerax"],
        "id": "22.19",
        "title": "CameraX：UseCase、Camera2 映射与性能",
    },
    "autofdo": {
        "group": GROUP_ART,
        "block": "AutoFDO 反馈导向编译优化",
        "source": "src/part1-fundamentals/ch01-architecture/12-autofdo-optimization.md",
        "target": NEW_PATHS["autofdo"],
        "id": "16.4",
        "title": "AutoFDO 反馈导向优化与 Android 验证",
    },
}


def canonical_paths() -> list[Path]:
    return sorted(
        path
        for path in ROOT.glob("src/part*/ch*/*.md")
        if path.name != "README.md"
    )


def git_text(relative: str) -> str:
    result = subprocess.run(
        ["git", "show", f"HEAD:{relative}"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return result.stdout


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    raw, body = fusion.split_frontmatter(text)
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a mapping")
    return data, body


def dump_document(meta: dict[str, Any], body: str) -> str:
    raw = yaml.safe_dump(
        meta,
        allow_unicode=True,
        sort_keys=False,
        width=1000,
    ).rstrip()
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


def v2_id_map() -> dict[str, str]:
    rows = json.loads(MAP_V2.read_text(encoding="utf-8"))["paths"]
    result: dict[str, str] = {}
    for row in rows:
        result[str(row["source_chapter"])] = str(row["target_chapter"])
    return result


OLD_TO_CURRENT_ID = v2_id_map()


def map_related(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        current = OLD_TO_CURRENT_ID.get(str(value), str(value))
        current = ID_MOVES.get(current, current)
        if current not in result:
            result.append(current)
    return result


def source_meta(relative: str, *, title: str, chapter: str) -> dict[str, Any]:
    meta, _ = parse_frontmatter(git_text(relative))
    meta["title"] = title
    meta["chapter"] = chapter
    if "section" in meta:
        meta["section"] = chapter
    meta["related_chapters"] = [item for item in map_related(meta.get("related_chapters")) if item != chapter]
    consolidated = list(meta.get("consolidated_from") or [])
    consolidated.append(relative)
    meta["consolidated_from"] = unique(consolidated)
    return meta


def group_blocks(relative: str) -> dict[str, list[str]]:
    _, body = fusion.split_frontmatter((ROOT / relative).read_text(encoding="utf-8"))
    _, _, blocks = fusion.split_body(body)
    return {title: lines for title, lines in blocks}


def singleton_body(title: str, lines: list[str]) -> str:
    promoted = fusion.shift_headings(fusion.trim_blank(lines), -1)
    return f"# {title}\n\n" + "\n".join(promoted).strip() + "\n"


def build_singletons() -> dict[str, tuple[str, str]]:
    cache: dict[str, dict[str, list[str]]] = {}
    outputs: dict[str, tuple[str, str]] = {}
    for item in SOURCE_SPECS.values():
        group = str(item["group"])
        cache.setdefault(group, group_blocks(group))
        lines = cache[group][str(item["block"])]
        meta = source_meta(
            str(item["source"]),
            title=str(item["title"]),
            chapter=str(item["id"]),
        )
        body = singleton_body(str(item["title"]), lines)
        outputs[str(item["target"])] = (group, dump_document(meta, body))
    return outputs


def build_art_output() -> tuple[str, str]:
    current = (ROOT / GROUP_ART).read_text(encoding="utf-8")
    current_meta, _ = parse_frontmatter(current)
    keep_sources = [
        "src/part1-fundamentals/ch01-architecture/07-art-compilation.md",
        "src/part1-fundamentals/ch01-architecture/22-art-verifier-quickening-dexopt-filters.md",
        "src/part1-fundamentals/ch01-architecture/35-art-deoptimization-performance.md",
    ]
    source_metas = [parse_frontmatter(git_text(path))[0] for path in keep_sources]
    current_meta["title"] = "ART 编译、验证与去优化机制"
    current_meta["chapter"] = "1.5"
    if "section" in current_meta:
        current_meta["section"] = "1.5"
    current_meta["tags"] = unique([tag for meta in source_metas for tag in (meta.get("tags") or [])])
    current_meta["sources"] = unique([source for meta in source_metas for source in (meta.get("sources") or [])])
    current_meta["related_chapters"] = unique(
        [item for meta in source_metas for item in map_related(meta.get("related_chapters")) if item != "1.5"]
    )
    current_meta["consolidated_from"] = unique(
        [
            value
            for path, meta in zip(keep_sources, source_metas)
            for value in [*(meta.get("consolidated_from") or []), path]
        ]
    )
    blocks = group_blocks(GROUP_ART)
    selected_titles = [
        "ART 编译管线与 dex2oat 优化",
        "ART Verifier Quickening 与 dexopt 过滤器性能边界",
        "Android 17 ART 去优化：触发、栈重建与性能诊断",
    ]
    body_lines = ["# ART 编译、验证与去优化机制", ""]
    for title in selected_titles:
        body_lines.extend([f"## {title}", "", *blocks[title], ""])
    selected = dump_document(current_meta, "\n".join(body_lines))
    spec = {
        "intro_bridge": "ART 从 DEX 验证和编译开始，通过 AOT、JIT 与 Profile 选择执行代码；运行时假设失效时再进入去优化和解释执行。安装、首启和动态调试需要沿同一产物与状态链判断。",
        "sections": [
            {"from": selected_titles[0], "title": "DEX 执行、AOT/JIT 与 Profile"},
            {
                "from": selected_titles[1],
                "title": "Verifier、VDEX/ODEX 与 dexopt",
                "bridge": "编译策略决定生成多少机器码，Verifier 和 dexopt 产物决定代码能否安全复用。安装、首次启动和后台优化使用不同场景与过滤器。",
            },
            {
                "from": selected_titles[2],
                "title": "去优化触发、栈重建与诊断",
                "bridge": "编译代码依赖类层次、类型和调试状态等假设。假设失效后，ART 需要恢复 DEX 执行状态并切换到解释器或重新编译。",
            },
        ],
    }
    rewritten, _ = fusion.rewrite_text(selected, spec, PATH_MOVES[GROUP_ART])
    return GROUP_ART, rewritten


def final_id(relative: str) -> str:
    path = Path(relative)
    chapter_match = re.match(r"ch(\d+)-", path.parent.name)
    file_match = re.match(r"(\d+)-", path.name)
    if not chapter_match or not file_match:
        raise ValueError(f"cannot derive chapter id: {relative}")
    return f"{int(chapter_match.group(1))}.{int(file_match.group(1))}"


def update_meta_ids(text: str, relative: str) -> str:
    meta, body = parse_frontmatter(text)
    chapter = final_id(relative)
    meta["chapter"] = chapter
    if "section" in meta:
        meta["section"] = chapter
    if isinstance(meta.get("related_chapters"), list):
        meta["related_chapters"] = unique(
            [ID_MOVES.get(str(item), str(item)) for item in meta["related_chapters"] if ID_MOVES.get(str(item), str(item)) != chapter]
        )
    return dump_document(meta, body)


def semantic_target(old_relative: str, label: str) -> str:
    key = label.casefold()
    if old_relative == GROUP_ART and re.search(r"autofdo|afdo|反馈导向|kernel\.afdo", key, re.I):
        return NEW_PATHS["autofdo"]
    if old_relative == GROUP_TELEPHONY and re.search(r"connectivity|网络选择|网络连接|network", key, re.I):
        return NEW_PATHS["connectivity"]
    if old_relative == GROUP_UI and re.search(r"compose|jetpack", key, re.I):
        return NEW_PATHS["compose"]
    if old_relative == GROUP_MEDIA and re.search(r"camera|camerax|相机|拍摄", key, re.I):
        return NEW_PATHS["camerax"]
    return PATH_MOVES[old_relative]


def rewrite_links(text: str, origin: str, destination: str) -> str:
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
            label_markup, raw = match.groups()
            wrapped = raw.startswith("<") and raw.endswith(">")
            target_raw = raw[1:-1] if wrapped else raw
            path_part, marker, anchor = target_raw.partition("#")
            if not path_part or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", path_part):
                return match.group(0)
            clean = unquote(path_part)
            resolved = (origin_path.parent / clean).resolve()
            try:
                old_relative = str(resolved.relative_to(ROOT))
            except ValueError:
                return match.group(0)
            if old_relative in {GROUP_ART, GROUP_TELEPHONY, GROUP_UI, GROUP_MEDIA}:
                new_relative = semantic_target(old_relative, label_markup)
            else:
                new_relative = PATH_MOVES.get(old_relative)
            if not new_relative:
                return match.group(0)
            relative_link = os.path.relpath(ROOT / new_relative, destination_path.parent)
            if marker:
                relative_link += f"#{anchor}"
            if " " in relative_link:
                relative_link = f"<{relative_link}>"
            return f"{label_markup}({relative_link})"

        parts = re.split(r"(`+[^`]*`+)", line)
        line = "".join(
            part if index % 2 else LINK_RE.sub(replace, part)
            for index, part in enumerate(parts)
        )
        result.append(line)
    return "\n".join(result) + ("\n" if text.endswith("\n") else "")


def build_documents() -> dict[str, tuple[str, str]]:
    outputs: dict[str, tuple[str, str]] = {}
    replaced_groups = {GROUP_ART, GROUP_TELEPHONY, GROUP_UI, GROUP_MEDIA}
    for path in canonical_paths():
        old = str(path.relative_to(ROOT))
        if old in replaced_groups:
            continue
        new = PATH_MOVES.get(old, old)
        outputs[new] = (old, update_meta_ids(path.read_text(encoding="utf-8"), new))
    outputs.update(build_singletons())
    art_origin, art_text = build_art_output()
    outputs[PATH_MOVES[GROUP_ART]] = (art_origin, art_text)

    rewritten: dict[str, tuple[str, str]] = {}
    for new, (old, text) in outputs.items():
        text = v2.rewrite_chapter_references(text, ID_MOVES)
        text = rewrite_links(text, old, new)
        rewritten[new] = (old, text)
    return rewritten


def title_and_id(text: str) -> tuple[str, str]:
    meta, _ = parse_frontmatter(text)
    return str(meta["title"]), str(meta["chapter"])


INDEX_HEADING_RE = re.compile(r"^##(?:\s+\d+\.)?\s+(?:内容索引|章节目录|连续阅读目录|章节地图)\s*$")


def rebuild_readme(relative: str, documents: dict[str, tuple[str, str]]) -> str:
    path = ROOT / relative
    text = rewrite_links(path.read_text(encoding="utf-8"), relative, relative)
    text = v2.rewrite_chapter_references(text, ID_MOVES)
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if INDEX_HEADING_RE.match(line)), None)
    if start is None:
        raise ValueError(f"README index heading missing: {relative}")
    end = next((index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")), len(lines))
    directory = str(Path(relative).parent)
    rows = sorted(
        (path, title_and_id(text_value))
        for path, (_, text_value) in documents.items()
        if str(Path(path).parent) == directory
    )
    index_lines = [lines[start], ""] + [
        f"- [{chapter} {title}]({Path(path).name})"
        for path, (title, chapter) in rows
    ] + [""]
    return "\n".join(lines[:start] + index_lines + lines[end:]).rstrip() + "\n"


def rebuild_summary(documents: dict[str, tuple[str, str]]) -> str:
    relative = "src/SUMMARY.md"
    text = rewrite_links((ROOT / relative).read_text(encoding="utf-8"), relative, relative)
    text = v2.rewrite_chapter_references(text, ID_MOVES)
    lines = text.splitlines()
    affected = {
        "src/part1-fundamentals/ch01-architecture",
        "src/part4-system/ch16-aosp",
        "src/part2-performance/ch18-rendering-pipelines",
        "src/part5-app/ch22-rendering-practice",
    }
    index = 0
    while index < len(lines):
        match = re.search(r"\(([^)]+/README\.md)\)", lines[index])
        if not match:
            index += 1
            continue
        chapter_dir = "src/" + str(Path(match.group(1)).parent)
        if chapter_dir not in affected:
            index += 1
            continue
        end = index + 1
        while end < len(lines) and lines[end].startswith("  - "):
            end += 1
        rows = sorted(
            (path, title_and_id(text_value))
            for path, (_, text_value) in documents.items()
            if str(Path(path).parent) == chapter_dir
        )
        children = [
            f"  - [{chapter} {title}]({str(Path(path).relative_to('src'))})"
            for path, (title, chapter) in rows
        ]
        lines[index + 1 : end] = children
        index += 1 + len(children)
    return "\n".join(lines).rstrip() + "\n"


def validate_documents(documents: dict[str, tuple[str, str]]) -> None:
    if len(documents) != 289:
        raise ValueError(f"expected 289 canonical bodies, got {len(documents)}")
    by_dir: defaultdict[str, list[int]] = defaultdict(list)
    for relative, (_, text) in documents.items():
        fusion.validate_markdown(text, ROOT / relative)
        _, chapter = title_and_id(text)
        expected = final_id(relative)
        if chapter != expected:
            raise ValueError(f"chapter/path mismatch: {relative}: {chapter} != {expected}")
        by_dir[str(Path(relative).parent)].append(int(chapter.split(".")[1]))
    for directory, ids in by_dir.items():
        if sorted(ids) != list(range(1, len(ids) + 1)):
            raise ValueError(f"noncontinuous numbering: {directory}: {sorted(ids)}")


def build_map_report(documents: dict[str, tuple[str, str]]) -> str:
    rows = [
        {"before": old, "after": new, "chapter": final_id(new)}
        for new, (old, _) in sorted(documents.items())
        if new != old
    ]
    report = {
        "schema_version": 1,
        "reviewed_at": "2026-08-24",
        "before_count": 285,
        "after_count": len(documents),
        "renamed_or_split_paths": rows,
    }
    return json.dumps(report, ensure_ascii=False, indent=2) + "\n"


def apply_outputs(
    documents: dict[str, tuple[str, str]],
    auxiliary: dict[str, str],
) -> None:
    affected_old = set(PATH_MOVES) | {GROUP_ART, GROUP_TELEPHONY, GROUP_UI, GROUP_MEDIA}
    affected_new = {new for new, (old, _) in documents.items() if new != old or old in affected_old}
    with tempfile.TemporaryDirectory(prefix="aiw-editorial-split-") as temp_value:
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

    # Unmoved canonical files may still contain rewritten chapter references or links.
    for relative, (old, text) in documents.items():
        if relative not in affected_new and text != (ROOT / relative).read_text(encoding="utf-8"):
            (ROOT / relative).write_text(text, encoding="utf-8", newline="\n")
    for relative, text in auxiliary.items():
        (ROOT / relative).write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    documents = build_documents()
    validate_documents(documents)
    readmes = [
        "src/part1-fundamentals/ch01-architecture/README.md",
        "src/part4-system/ch16-aosp/README.md",
        "src/part2-performance/ch18-rendering-pipelines/README.md",
        "src/part5-app/ch22-rendering-practice/README.md",
    ]
    auxiliary = {relative: rebuild_readme(relative, documents) for relative in readmes}
    auxiliary["src/SUMMARY.md"] = rebuild_summary(documents)
    auxiliary[str(MAP_V3.relative_to(ROOT))] = build_map_report(documents)
    if args.apply:
        apply_outputs(documents, auxiliary)
    print(
        json.dumps(
            {
                "mode": "apply" if args.apply else "dry-run",
                "canonical_bodies": len(documents),
                "renamed_or_split": sum(new != old for new, (old, _) in documents.items()),
                "new_paths": list(NEW_PATHS.values()),
                "chapter_counts": {
                    chapter: sum(1 for path in documents if f"/{chapter}-" in path)
                    for chapter in ("ch01", "ch16", "ch18", "ch22")
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
