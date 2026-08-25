#!/usr/bin/env python3
"""Close the duplicate refresh-rate chapter without losing its source-only detail.

Chapter 2.2 owns the platform frame-rate / display-mode model. Chapter 22.12
remains the application integration and experiment owner, while chapter 18.11
already owns video timestamp-to-present timing. The former chapter 18.13 mostly
repeats those owners; this transform embeds its two source-only Scheduler/View
details into 2.2, records every content route, removes the duplicate, and closes
the numbering gap in chapter 18.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/part2-performance/ch18-rendering-pipelines/13-variable-refresh-rate.md"
TARGET = ROOT / "src/part1-fundamentals/ch02-rendering/02-framerate-refresh-display-mode.md"
APP_OWNER = ROOT / "src/part5-app/ch22-rendering-practice/12-adaptive-refresh-rate.md"
VIDEO_OWNER = ROOT / "src/part2-performance/ch18-rendering-pipelines/11-video-overlay-media3-codec-pipeline.md"
MAP_PATH = ROOT / "metadata/2026-08-24-editorial-fusion-v14-map.json"

REINDEX = [
    ("14-eyedropper-crossdevice.md", "13-eyedropper-crossdevice.md", "18.14", "18.13"),
    (
        "15-android-xr-spatial-ui-rendering.md",
        "14-android-xr-spatial-ui-rendering.md",
        "18.15",
        "18.14",
    ),
    ("16-webgpu-android-pipeline.md", "15-webgpu-android-pipeline.md", "18.16", "18.15"),
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


def build_target(text: str) -> str:
    text = replace_once(
        text,
        "last_verified: '2026-08-21'",
        "last_verified: '2026-08-24'",
        "2.2 verification date",
    )
    view_source = (
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/View.java\n"
    )
    view_root_source = (
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java\n"
    )
    text = replace_once(text, view_source, view_source + view_root_source, "2.2 ViewRootImpl source")
    text = replace_once(
        text,
        "- '2.17'\npipeline_stage: finalized",
        "- '2.17'\n- '22.12'\npipeline_stage: finalized",
        "2.2 application owner relation",
    )
    text = replace_once(
        text,
        "- src/part1-fundamentals/ch02-rendering/34-display-mode-refresh-rate-selection.md\n---",
        "- src/part1-fundamentals/ch02-rendering/34-display-mode-refresh-rate-selection.md\n"
        "- src/part2-performance/ch18-rendering-pipelines/13-variable-refresh-rate.md\n---",
        "2.2 consolidation provenance",
    )

    scheduler_marker = (
        "这段代码说明选择发生在 Layer 状态更新之后。"
        "`Scheduler::chooseRefreshRateForContent()` 先让 `LayerHistory` 汇总可见内容，再把 content requirements（内容帧率需求）应用到刷新率策略。"
        "产生 mode request（显示模式请求）后，SurfaceFlinger 仍会调用 `RefreshRateSelector::isModeAllowed()` 检查候选是否符合 DisplayManager 下发的范围。"
    )
    scheduler_feedback = (
        "当调用参数允许更新应用节奏时，`chooseRefreshRateForContent()` 还会把已选的 pacesetter fps（主导显示设备的帧率）交给 "
        "`updateAttachedChoreographers()`。该函数遍历 layer hierarchy（图层层级），依据 `FIXED_SOURCE`、`DEFAULT` 等 vote 计算显示节奏与应用回调节奏之间的整数 "
        "divisor（分频系数），再更新对应的 `EventThreadConnection.frameRate`。因此，trace 中 `VSYNC-app` 间隔的变化既可能来自应用请求，也可能是显示选择结果反馈给 attached "
        "Choreographer；只观察物理 Display mode 会漏掉这一层。"
    )
    text = replace_once(
        text,
        scheduler_marker,
        scheduler_marker + "\n\n" + scheduler_feedback,
        "2.2 attached Choreographer feedback",
    )

    old_vote = (
        "`setRequestedFrameRate()` 也接受 30、60、120 等正数。数值表示内容偏好，不要求它正好等于设备的物理刷新率。"
        "多个数值投票互为整数倍时，框架通常取较高值；不互为整数倍时，超过 60 Hz 的请求按 `High` 倾向处理，其余按 `Normal` 倾向处理。"
        "官方文档明确说明这套合并策略可能调整，业务代码不应依赖精确的内部优先级。"
    )
    new_vote = (
        "`setRequestedFrameRate()` 也接受 30、60、120 等正数。数值表示内容偏好，不要求它正好等于设备的物理刷新率。"
        "多个数值投票互为整数倍时，`ViewRootImpl` 选择能覆盖其他投票的较高值；无法整除时，源码会设置 conflict（冲突）标记，停止直接提交该数值，并按最大请求是否高于 "
        "60 fps 回退到 `HIGH` 或 `NORMAL` 类别。因此，trace 中出现类别投票不一定表示业务直接调用了类别 API，也可能是数值冲突后的回退结果。"
        "官方文档明确说明这套合并策略可能调整，业务代码不应依赖精确的内部优先级。"
    )
    text = replace_once(text, old_vote, new_vote, "2.2 numeric vote conflict")
    return text


def build_app_owner(text: str) -> str:
    text = replace_once(
        text,
        "last_verified: '2026-08-15'",
        "last_verified: '2026-08-24'",
        "22.12 review date",
    )
    old = (
        "相关系统机制见 [2.2 帧率、刷新率与显示模式选择](../../part1-fundamentals/ch02-rendering/02-framerate-refresh-display-mode.md) "
        "和 [18.13 Android 17 可变刷新率（ARR/VRR）渲染管线](../../part2-performance/ch18-rendering-pipelines/13-variable-refresh-rate.md)。"
    )
    new = (
        "平台选择链、ARR/MRR 分支和 attached Choreographer 反馈统一见 "
        "[2.2 帧率、刷新率与显示模式选择](../../part1-fundamentals/ch02-rendering/02-framerate-refresh-display-mode.md)；"
        "本文只负责应用接入、跨设备实验和回退策略。"
    )
    return replace_once(text, old, new, "22.12 owner boundary")


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
        placeholder = f"__AIW_HISTORICAL_REFRESH_PATH_{index}__"
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
            value = "2.2" if value == "18.13" else mapping.get(value, value)
            rewritten = f"- '{value}'"
        if rewritten not in seen:
            seen.add(rewritten)
            output.append(rewritten)
    block = "\n".join(output) + "\n"
    return text[: match.start(1)] + block + text[match.end(1) :]


def update_references(path: Path, text: str) -> str:
    if path == ROOT / "src/SUMMARY.md":
        text = text.replace(
            "  - [18.13 Android 17 可变刷新率（ARR/VRR）渲染管线](part2-performance/ch18-rendering-pipelines/13-variable-refresh-rate.md)\n",
            "",
        )
    if path == ROOT / "src/part2-performance/ch18-rendering-pipelines/README.md":
        text = text.replace(
            "- [18.13 Android 17 可变刷新率（ARR/VRR）渲染管线](13-variable-refresh-rate.md)\n",
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
    return remap_related(text)


def h2_inventory(text: str) -> list[str]:
    return [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]


def validate(changed: dict[Path, str], originals: dict[Path, str]) -> None:
    required_target = [
        "updateAttachedChoreographers()",
        "EventThreadConnection.frameRate",
        "conflict（冲突）标记",
        "数值冲突后的回退结果",
        "src/part2-performance/ch18-rendering-pipelines/13-variable-refresh-rate.md",
        "- '22.12'",
    ]
    missing = [needle for needle in required_target if needle not in changed[TARGET]]
    if missing:
        raise RuntimeError(f"missing fused refresh-rate concepts: {missing}")
    if "本文只负责应用接入、跨设备实验和回退策略" not in changed[APP_OWNER]:
        raise RuntimeError("22.12 owner boundary was not preserved")

    for _, new, _, new_number in REINDEX_PATHS:
        body = changed[new]
        if f"chapter: '{new_number}'" not in body or f"section: '{new_number}'" not in body:
            raise RuntimeError(f"bad chapter reindex in {new}")

    projected: dict[Path, str] = {}
    for path in [ROOT / "README.md", *sorted((ROOT / "src").rglob("*.md"))]:
        if path == SOURCE or any(path == old for old, _, _, _ in REINDEX_PATHS):
            continue
        projected[path] = changed.get(path, path.read_text(encoding="utf-8"))
    for _, new, _, _ in REINDEX_PATHS:
        projected[new] = changed[new]
    stale = []
    for path, body in projected.items():
        if re.search(r"\]\([^\n)]*13-variable-refresh-rate\.md(?:#[^)]+)?\)", body):
            stale.append(str(path.relative_to(ROOT)))
    if stale:
        raise RuntimeError(f"live files still point to removed refresh-rate source: {stale}")

    source_h2 = h2_inventory(originals[SOURCE])
    expected_h2 = [
        "为什么这一节容易误判",
        "VRR、多刷新率和 ARR 的边界",
        "系统如何决定刷新节奏",
        "App 端 API",
        "Android 17 的 Scheduler 怎样处理 vote",
        "渲染过程里的 deadline 没有消失",
        "在 Perfetto 中分析 VRR / ARR",
        "版本演进",
        "与其他章节的关系",
        "参考资料",
    ]
    if source_h2 != expected_h2:
        raise RuntimeError(f"unexpected source H2 inventory: {source_h2}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    required = [SOURCE, TARGET, APP_OWNER, VIDEO_OWNER, *[row[0] for row in REINDEX_PATHS]]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"Expected predecessor files are missing: {missing}")

    originals = {path: path.read_text(encoding="utf-8") for path in required}
    changed: dict[Path, str] = {
        TARGET: build_target(originals[TARGET]),
        APP_OWNER: build_app_owner(originals[APP_OWNER]),
    }

    for old, new, old_number, new_number in REINDEX_PATHS:
        body = originals[old]
        body = replace_once(body, f"chapter: '{old_number}'", f"chapter: '{new_number}'", f"{old.name} chapter")
        body = replace_once(body, f"section: '{old_number}'", f"section: '{new_number}'", f"{old.name} section")
        changed[new] = body

    skip = {SOURCE, TARGET, APP_OWNER, *[row[0] for row in REINDEX_PATHS]}
    scan_paths = [ROOT / "README.md", *sorted((ROOT / "src").rglob("*.md"))]
    for path in scan_paths:
        if path in skip:
            continue
        original = path.read_text(encoding="utf-8")
        updated = update_references(path, original)
        if updated != original:
            changed[path] = updated
    for path in list(changed):
        changed[path] = update_references(path, changed[path])

    validate(changed, originals)
    result = {
        "version": 14,
        "operation": "variable_refresh_rate_owner_editorial_fusion",
        "count_change": {"before": 277, "after": 276},
        "merged_paths": [
            {
                "source": str(SOURCE.relative_to(ROOT)),
                "target": str(TARGET.relative_to(ROOT)),
                "role": "platform_frame_rate_display_mode_arr_vrr_owner",
            }
        ],
        "retained_independent_owners": [
            {
                "path": str(APP_OWNER.relative_to(ROOT)),
                "role": "application_integration_experiment_and_rollback_owner",
            },
            {
                "path": str(VIDEO_OWNER.relative_to(ROOT)),
                "role": "video_timestamp_bufferqueue_and_present_owner",
            },
        ],
        "rewritten_paths": [str(TARGET.relative_to(ROOT)), str(APP_OWNER.relative_to(ROOT))],
        "reindexed_paths": [
            {"from": str(old.relative_to(ROOT)), "to": str(new.relative_to(ROOT))}
            for old, new, _, _ in REINDEX_PATHS
        ],
        "source_bytes": {
            str(path.relative_to(ROOT)): len(body.encode("utf-8"))
            for path, body in originals.items()
        },
        "result_bytes": {
            str(TARGET.relative_to(ROOT)): len(changed[TARGET].encode("utf-8")),
            str(APP_OWNER.relative_to(ROOT)): len(changed[APP_OWNER].encode("utf-8")),
        },
        "result_delta_bytes": {
            str(TARGET.relative_to(ROOT)): len(changed[TARGET].encode("utf-8"))
            - len(originals[TARGET].encode("utf-8")),
            str(APP_OWNER.relative_to(ROOT)): len(changed[APP_OWNER].encode("utf-8"))
            - len(originals[APP_OWNER].encode("utf-8")),
        },
        "source_sha256": {
            str(path.relative_to(ROOT)): digest(body) for path, body in originals.items()
        },
        "result_sha256": {
            str(TARGET.relative_to(ROOT)): digest(changed[TARGET]),
            str(APP_OWNER.relative_to(ROOT)): digest(changed[APP_OWNER]),
        },
        "source_h2_inventory": h2_inventory(originals[SOURCE]),
        "content_routes": [
            {
                "source": "18.13 why fixed budgets mislead and content/render/display rate taxonomy",
                "destination": "2.2 frame-rate, refresh-rate and deadline sections",
                "treatment": "existing_owner_verified; duplicate_exposition_deduplicated",
            },
            {
                "source": "18.13 MRR, VRR and ARR capability boundaries",
                "destination": "2.2 MRR/ARR/VRR taxonomy and ARR constraint sections",
                "treatment": "existing_owner_verified; duplicate_table_deduplicated",
            },
            {
                "source": "18.13 app View, Compose, Window, Surface and Display APIs",
                "destination": "22.12 remains independent for integration; 2.2 retains platform semantics",
                "treatment": "owner_boundary_rewritten; duplicate_API_tutorial_deduplicated",
            },
            {
                "source": "18.13 numeric View vote aggregation conflict fallback",
                "destination": "2.2 ordinary UI numeric-vote paragraph",
                "treatment": "source_only_conflict_flag_and_trace_interpretation_embedded",
            },
            {
                "source": "18.13 selected pacesetter fps feedback through updateAttachedChoreographers",
                "destination": "2.2 SurfaceFlinger Scheduler control chain",
                "treatment": "source_only_divisor_and_EventThreadConnection_feedback_embedded",
            },
            {
                "source": "18.13 LayerHistory/RefreshRateSelector votes, ARR/MRR branch and multi-display policy",
                "destination": "2.2 existing selector, scoring and pacesetter/follower sections",
                "treatment": "existing_deeper_owner_verified; duplicate_implementation_walkthrough_deduplicated",
            },
            {
                "source": "18.13 video release timestamp, BufferQueue PRESENT_LATER and HWC present",
                "destination": "18.11 video overlay, Media3 and codec pipeline",
                "treatment": "existing_video_owner_verified; duplicate_timing_chain_deduplicated",
            },
            {
                "source": "18.13 producer throttling, deadline and FrameTimeline/Perfetto diagnosis",
                "destination": "2.2 platform diagnosis plus 22.12 application validation",
                "treatment": "existing_owners_verified; duplicate_SQL_and_checklist_deduplicated",
            },
            {
                "source": "18.13 version evolution, kernel boundary, references and related chapters",
                "destination": "2.2 metadata/version/source index and reconciled cross-links",
                "treatment": "evidence_reconciled; duplicate_appendix_deduplicated",
            },
        ],
        "updated_reference_files": [
            str(path.relative_to(ROOT))
            for path in sorted(changed)
            if path not in {TARGET, APP_OWNER, *[row[1] for row in REINDEX_PATHS]}
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
