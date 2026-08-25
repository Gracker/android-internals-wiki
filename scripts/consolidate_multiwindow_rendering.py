#!/usr/bin/env python3
"""Fuse the overlapping multi-window rendering owners and close chapter 18.

Chapter 2.10 owns the system Display/Window/SF model. The predecessor 18.3
duplicates that model but contains valuable per-process execution, PiP,
Freeform and trace material. This transform embeds those unique sections into
2.10, removes duplicated exposition, and reindexes the remaining chapter 18
pipeline articles.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/part2-performance/ch18-rendering-pipelines/03-android-view-multi-window.md"
TARGET = ROOT / "src/part1-fundamentals/ch02-rendering/10-multiwindow-desktop-rendering.md"
MAP_PATH = ROOT / "metadata/2026-08-24-editorial-fusion-v13-map.json"

REINDEX = [
    ("04-surfaceview-textureview-pipelines.md", "03-surfaceview-textureview-pipelines.md", "18.4", "18.3"),
    ("05-opengl-egl-angle.md", "04-opengl-egl-angle.md", "18.5", "18.4"),
    ("06-vulkan-hwui-multi-queue.md", "05-vulkan-hwui-multi-queue.md", "18.6", "18.5"),
    ("07-surfacecontrol-hardwarebuffer-renderer.md", "06-surfacecontrol-hardwarebuffer-renderer.md", "18.7", "18.6"),
    ("08-flutter-rendering-pipeline.md", "07-flutter-rendering-pipeline.md", "18.8", "18.7"),
    ("09-compose-rendering-pipeline.md", "08-compose-rendering-pipeline.md", "18.9", "18.8"),
    ("10-webview-rendering.md", "09-webview-rendering.md", "18.10", "18.9"),
    ("11-camera-pipeline.md", "10-camera-pipeline.md", "18.11", "18.10"),
    ("12-video-overlay-media3-codec-pipeline.md", "11-video-overlay-media3-codec-pipeline.md", "18.12", "18.11"),
    ("13-game-engine.md", "12-game-engine.md", "18.13", "18.12"),
    ("14-variable-refresh-rate.md", "13-variable-refresh-rate.md", "18.14", "18.13"),
    ("15-eyedropper-crossdevice.md", "14-eyedropper-crossdevice.md", "18.15", "18.14"),
    ("16-android-xr-spatial-ui-rendering.md", "15-android-xr-spatial-ui-rendering.md", "18.16", "18.15"),
    ("17-webgpu-android-pipeline.md", "16-webgpu-android-pipeline.md", "18.17", "18.16"),
]
REINDEX_PATHS = [
    (
        ROOT / "src/part2-performance/ch18-rendering-pipelines" / old,
        ROOT / "src/part2-performance/ch18-rendering-pipelines" / new,
        old_number,
        new_number,
    )
    for old, new, old_number, new_number in REINDEX
]


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one marker, found {count}")
    return text.replace(old, new, 1)


def extract(text: str, start: str, end: str) -> str:
    if text.count(start) != 1:
        raise RuntimeError(f"source start marker is missing or duplicated: {start}")
    tail = text.split(start, 1)[1]
    if tail.count(end) != 1:
        raise RuntimeError(f"source end marker is missing or duplicated after {start}: {end}")
    return (start + tail.split(end, 1)[0]).strip()


def build_target(target: str, source: str) -> str:
    target = replace_once(
        target,
        "title: 多窗口与桌面模式渲染性能",
        "title: 多窗口、PiP 与桌面模式渲染管线",
        "2.10 title",
    )
    target = replace_once(target, "last_verified: '2026-07-25'", "last_verified: '2026-08-24'", "2.10 verification date")
    target = replace_once(
        target,
        "last_verified_against: AOSP android-17.0.0_r1, Perfetto stdlib / FrameTimeline, kernel android17-6.18-2026-06_r6, Android Developers multi-window / desktop windowing / connected displays, Writer rendering_pipelines S01 / S06 / S08",
        "last_verified_against: AOSP android-17.0.0_r1 DisplayManager, WindowManager, WM Shell PiP, ViewRootImpl, HWUI, BLAST and SurfaceFlinger; Perfetto stdlib / FrameTimeline; kernel android17-6.18-2026-06_r6; current Android multi-window, PiP, desktop windowing and connected-display guidance",
        "2.10 verification provenance",
    )

    source_marker = (
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java\n"
    )
    source_additions = (
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java\n"
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/DrawFrameTask.cpp\n"
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/WindowContainer.java\n"
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/window/WindowContainerTransaction.java\n"
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/BLASTSyncEngine.java\n"
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp\n"
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/PictureInPictureParams.java\n"
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/PictureInPictureUiState.java\n"
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/WindowManager/Shell/src/com/android/wm/shell/pip/PipTaskOrganizer.java\n"
        "- type: official\n"
        "  path: https://developer.android.com/develop/ui/views/picture-in-picture\n"
        "- type: official\n"
        "  path: https://source.android.com/docs/core/display/multi-window\n"
    )
    target = replace_once(target, source_marker, source_marker + source_additions, "2.10 source transfer")
    target = replace_once(
        target,
        "- rendering\nrelated_chapters:\n",
        "- rendering\n- picture-in-picture\n- windowmanager\n- renderthread\nrelated_chapters:\n",
        "2.10 tags",
    )
    target = replace_once(
        target,
        "- '3.3'\npipeline_stage: ready-to-publish",
        "- '3.3'\n- '18.1'\n- '22.10'\npipeline_stage: finalized",
        "2.10 related owners",
    )
    target = replace_once(
        target,
        "last_consolidated_at: '2026-08-11'\nconsolidated_from:\n- src/part1-fundamentals/ch02-rendering/2.29-Android-17-桌面模式窗口管理性能.md",
        "last_consolidated_at: '2026-08-24'\nconsolidated_from:\n- src/part1-fundamentals/ch02-rendering/2.29-Android-17-桌面模式窗口管理性能.md\n- src/part2-performance/ch18-rendering-pipelines/03-android-view-multi-window.md\n- src/part2-performance/ch18-rendering-pipelines/18-pip-freeform.md",
        "2.10 provenance",
    )
    target = replace_once(
        target,
        "# 多窗口与桌面模式渲染性能",
        "# 多窗口、PiP 与桌面模式渲染管线",
        "2.10 H1",
    )

    topology_evidence = r"""
### 先确认画面是否对应多个 Window

同一 Activity 内的双栏 View、`SlidingPaneLayout` 或 Compose pane 可能只有一个 `ViewRootImpl` 和一条 App Window buffer 链路。较强的多窗口证据包括：

- 多个顶层 `ViewRootImpl`；
- WMS 中存在不同的 `WindowState`、Window token、Task 或 TaskFragment；
- 各窗口拥有独立的 App Window Surface、BLAST 提交链和 SF buffer layer；
- 窗口可分别映射到不同的 `pid`、UI `tid` 或 `displayId`。

系统栏、壁纸、输入法、dim layer 和 transition leash 也会增加 SF layer。layer 数量本身不能证明应用创建了多个 Window；需要同时核对 WMS 与 SF 两棵树。
""".strip()
    topology_details = extract(
        source,
        "### 同进程不等于只有一个 Choreographer",
        "## 共享线程上的串行执行",
    )
    topology_marker = (
        "判断时应按 `pid/tid/ViewRootImpl/WindowState/layerId/displayId` 建表。屏幕上的两个 pane（窗格）也可能只是同一 Activity 中的双栏 View，"
        "此时只有一个 ViewRoot 和应用窗口 buffer，不应按多窗口管线分析。"
    )
    target = replace_once(
        target,
        topology_marker,
        topology_marker + "\n\n" + topology_evidence + "\n\n" + topology_details,
        "2.10 execution topology transfer",
    )

    shared_threads = extract(
        source,
        "## 共享线程上的串行执行",
        "## 完整执行流程",
    )
    target = replace_once(
        target,
        "## Android 17 桌面窗口的 Shell 路径",
        shared_threads + "\n\n## Android 17 桌面窗口的 Shell 路径",
        "2.10 shared execution section",
    )

    sequence = extract(
        source,
        "下面的时序图说明 A/B 的共享执行与 C 的独立执行：",
        "### resize 与 transition 的同步",
    )
    geometry_marker = (
        "WMS 内部的 `BLASTSyncEngine` 可以等待一组 WindowContainer 的 draw/transaction；公开的 `SurfaceSyncGroup` 面向应用与嵌入 Surface。"
        "两者只等待已注册参与者，不能替 Camera、codec 或游戏引擎的下一业务帧建立同步关系。"
    )
    target = replace_once(
        target,
        geometry_marker,
        geometry_marker + "\n\n### 从回调队列到 Display present\n\n" + sequence,
        "2.10 end-to-end sequence",
    )

    pip = extract(source, "## PiP 与 Freeform 的特殊边界", "### Freeform resize：分开 geometry 与 buffer")
    freeform = extract(
        source,
        "### Freeform resize：分开 geometry 与 buffer",
        "Android 17 还改变了部分配置变化触发 Activity 重建的规则。",
    )
    target = replace_once(
        target,
        "## 三个容易越界的 Android 17 话题",
        pip + "\n\n" + freeform.rstrip() + "\n\n## 三个容易越界的 Android 17 话题",
        "2.10 PiP and Freeform sections",
    )

    window_table = extract(source, "### 建立 Window 表", "### 同进程：排序两个队列")
    window_table = window_table.replace("### 建立 Window 表", "### 0. 建立 Window 表", 1)
    trace_marker = (
        "## Perfetto 和 dumpsys 的正确观察面\n\n"
        "多窗口分析要避免两类查询错误：使用不存在的表名，以及把某个版本中的 slice 名当成平台通用名称。"
    )
    target = replace_once(
        target,
        trace_marker,
        trace_marker + "\n\n" + window_table,
        "2.10 trace window inventory",
    )

    optimization = extract(source, "## 优化策略", "### Android 12—17 版本边界")
    target = replace_once(
        target,
        "## 版本演进",
        optimization.rstrip() + "\n\n## 版本演进",
        "2.10 responsibility-based optimization",
    )

    reference_marker = (
        "- [Android Developers：Connected displays](https://developer.android.com/develop/ui/compose/layouts/adaptive/support-connected-displays)\n"
    )
    reference_additions = (
        "- [Android Developers：Picture-in-picture](https://developer.android.com/develop/ui/views/picture-in-picture)\n"
        "- [AOSP：Multi-window support](https://source.android.com/docs/core/display/multi-window)\n"
        "- [AOSP `PictureInPictureParams`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/PictureInPictureParams.java)\n"
        "- [AOSP `PipTaskOrganizer`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/WindowManager/Shell/src/com/android/wm/shell/pip/PipTaskOrganizer.java)\n"
    )
    target = replace_once(target, reference_marker, reference_marker + reference_additions, "2.10 references")
    target = replace_once(
        target,
        "下面的代码分别处理顶层交互资格变化和真正离屏：",
        "下面的代码分别处理顶层交互资格变化和 Activity 进入 `onStop()` 后的离屏状态：",
        "2.10 lifecycle wording",
    )
    return target


def relpath(target: Path, source_file: Path) -> str:
    return Path(os.path.relpath(target, source_file.parent)).as_posix()


def protect_consolidated_paths(text: str, paths: list[str]) -> tuple[str, dict[str, str]]:
    restored: dict[str, str] = {}
    match = re.search(r"(?m)^consolidated_from:\n(?:- .*\n)+", text)
    if not match:
        return text, restored
    protected = match.group(0)
    for index, value in enumerate(paths):
        if value not in protected:
            continue
        placeholder = f"__AIW_HISTORICAL_MULTIWINDOW_PATH_{index}__"
        protected = protected.replace(value, placeholder)
        restored[placeholder] = value
    return text[: match.start()] + protected + text[match.end() :], restored


def remap_related(text: str) -> str:
    match = re.search(r"(?m)^related_chapters:\n((?:- .*\n)+)", text)
    if not match:
        return text
    mapping = {old: new for _, _, old, new in REINDEX_PATHS}
    output: list[str] = []
    seen: set[str] = set()
    for line in match.group(1).splitlines():
        value_match = re.fullmatch(r"- ['\"](\d+\.\d+)['\"]", line.strip())
        if not value_match:
            rewritten = line
        else:
            value = value_match.group(1)
            if value == "18.3":
                value = "2.10"
            else:
                value = mapping.get(value, value)
            rewritten = f"- '{value}'"
        if rewritten not in seen:
            seen.add(rewritten)
            output.append(rewritten)
    block = "\n".join(output) + "\n"
    return text[: match.start(1)] + block + text[match.end(1) :]


def update_references(path: Path, text: str) -> str:
    if path == ROOT / "src/SUMMARY.md":
        text = text.replace(
            "  - [18.3 Android 17 多窗口、PiP 与自由窗口渲染](part2-performance/ch18-rendering-pipelines/03-android-view-multi-window.md)\n",
            "",
        )
    if path == ROOT / "src/part2-performance/ch18-rendering-pipelines/README.md":
        text = text.replace(
            "- [18.3 Android 17 多窗口、PiP 与自由窗口渲染](03-android-view-multi-window.md)\n",
            "",
        )

    historical = [str(SOURCE.relative_to(ROOT))]
    historical += [str(old.relative_to(ROOT)) for old, _, _, _ in REINDEX_PATHS]
    text, placeholders = protect_consolidated_paths(text, historical)

    text = text.replace(relpath(SOURCE, path), relpath(TARGET, path))
    text = text.replace(str(SOURCE.relative_to(ROOT)), str(TARGET.relative_to(ROOT)))
    for old, new, _, _ in REINDEX_PATHS:
        text = text.replace(relpath(old, path), relpath(new, path))
        text = text.replace(str(old.relative_to(ROOT)), str(new.relative_to(ROOT)))

    for placeholder, value in placeholders.items():
        text = text.replace(placeholder, value)

    text = remap_related(text)
    text = text.replace("原独立 PiP/Freeform 正文已并入 18.3", "原独立 PiP/Freeform 与多窗口管线正文已并入 2.10")
    text = text.replace("本节“PiP 与 Freeform 的特殊边界”", "2.10 的“PiP 与 Freeform 的特殊边界”")
    return text


def h2_inventory(text: str) -> list[str]:
    return [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]


def validate(changed: dict[Path, str]) -> None:
    owner_needles = [
        "### 先确认画面是否对应多个 Window",
        "### 同进程不等于只有一个 Choreographer",
        "## 共享线程上的串行执行",
        "### 从回调队列到 Display present",
        "sequenceDiagram",
        "## PiP 与 Freeform 的特殊边界",
        "`sourceRectHint`",
        "### Freeform resize：分开 geometry 与 buffer",
        "### 0. 建立 Window 表",
        "## 优化策略",
        "last_consolidated_at: '2026-08-24'",
    ]
    missing = [needle for needle in owner_needles if needle not in changed[TARGET]]
    if missing:
        raise RuntimeError(f"missing fused multi-window concepts: {missing}")

    for _, new, _, new_number in REINDEX_PATHS:
        body = changed[new]
        if f"chapter: '{new_number}'" not in body or f"section: '{new_number}'" not in body:
            raise RuntimeError(f"bad chapter reindex in {new}")

    for path, body in changed.items():
        if path.suffix != ".md":
            continue
        if "](03-android-view-multi-window.md)" in body or "/03-android-view-multi-window.md)" in body:
            raise RuntimeError(f"live link still points to removed multi-window source: {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    required = [SOURCE, TARGET, *[row[0] for row in REINDEX_PATHS]]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"Expected predecessor files are missing: {missing}")

    originals = {path: path.read_text(encoding="utf-8") for path in required}
    changed: dict[Path, str] = {TARGET: build_target(originals[TARGET], originals[SOURCE])}

    for old, new, old_number, new_number in REINDEX_PATHS:
        body = originals[old]
        body = replace_once(body, f"chapter: '{old_number}'", f"chapter: '{new_number}'", f"{old.name} chapter")
        body = replace_once(body, f"section: '{old_number}'", f"section: '{new_number}'", f"{old.name} section")
        changed[new] = body

    skip = {SOURCE, TARGET, *[row[0] for row in REINDEX_PATHS]}
    for path in sorted((ROOT / "src").rglob("*.md")):
        if path in skip:
            continue
        original = path.read_text(encoding="utf-8")
        updated = update_references(path, original)
        if updated != original:
            changed[path] = updated
    for path in list(changed):
        changed[path] = update_references(path, changed[path])

    validate(changed)
    result = {
        "version": 13,
        "operation": "multiwindow_pip_desktop_rendering_editorial_fusion",
        "count_change": {"before": 278, "after": 277},
        "merged_paths": [
            {
                "source": str(SOURCE.relative_to(ROOT)),
                "target": str(TARGET.relative_to(ROOT)),
                "role": "display_window_process_surface_pip_freeform_and_trace_owner",
            }
        ],
        "rewritten_paths": [str(TARGET.relative_to(ROOT))],
        "reindexed_paths": [
            {"from": str(old.relative_to(ROOT)), "to": str(new.relative_to(ROOT))}
            for old, new, _, _ in REINDEX_PATHS
        ],
        "source_bytes": {
            str(path.relative_to(ROOT)): len(body.encode("utf-8"))
            for path, body in originals.items()
        },
        "result_bytes": {str(TARGET.relative_to(ROOT)): len(changed[TARGET].encode("utf-8"))},
        "source_sha256": {
            str(path.relative_to(ROOT)): digest(body) for path, body in originals.items()
        },
        "result_sha256": {str(TARGET.relative_to(ROOT)): digest(changed[TARGET])},
        "source_h2_inventory": h2_inventory(originals[SOURCE]),
        "content_routes": [
            {
                "source": "18.3 multi-window scene taxonomy and WMS/SF hierarchy",
                "destination": "2.10 existing display-session and Window topology sections",
                "treatment": "duplicate_scene_exposition_deduplicated; independent_Window_evidence_embedded",
            },
            {
                "source": "18.3 same-process Choreographer/RenderThread and cross-process/display competition",
                "destination": "2.10 Window/thread/Surface topology and shared-thread sections",
                "treatment": "detailed_execution_model_embedded",
            },
            {
                "source": "18.3 WCT, SurfaceControl, BLAST and per-display present sequence",
                "destination": "2.10 geometry/buffer section",
                "treatment": "unique_end_to_end_sequence_diagram_embedded; duplicate_object_definitions_deduplicated",
            },
            {
                "source": "18.3 PiP parameters, WM Shell transition and producer cadence",
                "destination": "2.10 PiP and Freeform section",
                "treatment": "source_only_PiP_contracts_embedded",
            },
            {
                "source": "18.3 G0/B0 Freeform resize matrix and sync boundaries",
                "destination": "2.10 PiP and Freeform section",
                "treatment": "source_only_resize_state_matrix_embedded",
            },
            {
                "source": "18.3 per-window trace inventory and responsibility-specific optimizations",
                "destination": "2.10 Perfetto/dumpsys and optimization sections",
                "treatment": "diagnostic_table_and_action_routes_embedded",
            },
            {
                "source": "18.3 version/source appendix and overlapping summaries",
                "destination": "2.10 metadata, version table and references",
                "treatment": "evidence_reconciled_and_duplicate_summaries_deduplicated",
            },
            {
                "source": "22.10 adaptive layout and multi-form-factor application practice",
                "destination": "22.10 remains independent",
                "treatment": "kept_as_application_layout_owner; 2.10 owns_platform_rendering_pipeline",
            },
        ],
        "updated_reference_files": [
            str(path.relative_to(ROOT))
            for path in sorted(changed)
            if path not in {TARGET, *[row[1] for row in REINDEX_PATHS]}
        ],
        "applied": args.apply,
    }

    if args.apply:
        for path in [SOURCE, *[row[0] for row in REINDEX_PATHS]]:
            path.unlink()
        for path, body in changed.items():
            path.write_text(body, encoding="utf-8")
        MAP_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
