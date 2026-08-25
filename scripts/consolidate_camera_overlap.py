#!/usr/bin/env python3
"""Distribute the mixed Camera HAL3/CameraX article into three clear owners.

Platform request/buffer/fence mechanics move to chapter 18, CameraX 1.6.1 ZSL
implementation details move to chapter 22, and ZSL timing formulas move to the
chapter 14 tool workflow. The old mixed-responsibility article is then removed.

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


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import consolidate_articles_v2 as v2  # noqa: E402
import consolidate_obvious_overlaps as prior  # noqa: E402
import consolidate_windowmanager_overlap as window  # noqa: E402
import editorial_fusion_rewrite as fusion  # noqa: E402


SOURCE = "src/part1-fundamentals/ch02-rendering/19-camera-hal3-buffer-camerax-zsl.md"
PLATFORM_TARGET = "src/part2-performance/ch18-rendering-pipelines/11-camera-pipeline.md"
APP_TARGET = "src/part5-app/ch22-rendering-practice/19-camerax-rendering.md"
TOOL_TARGET = "src/part3-tools/ch14-other-tools/14-camera-performance-analysis.md"
PRIMARY_REDIRECT = {SOURCE: PLATFORM_TARGET}
TARGETS = [PLATFORM_TARGET, APP_TARGET, TOOL_TARGET]
AFFECTED_DIRS = {
    "src/part1-fundamentals/ch02-rendering",
    "src/part2-performance/ch18-rendering-pipelines",
    "src/part3-tools/ch14-other-tools",
    "src/part5-app/ch22-rendering-practice",
}
MAP_PATH = "metadata/2026-08-24-editorial-fusion-v6-map.json"
HISTORICAL_JSON = {
    "metadata/2026-08-24-content-consolidation-v2-map.json",
    "metadata/2026-08-24-editorial-fusion-v3-map.json",
    "metadata/2026-08-24-editorial-fusion-v4-map.json",
    "metadata/2026-08-24-editorial-fusion-v5-map.json",
    MAP_PATH,
}
FENCE_RE = re.compile(r"^\s*(```|~~~)")
LINK_RE = re.compile(r"(!?\[[^\]\n]*\])\((<[^>\n]+>|[^)\n]+)\)")
INDEX_HEADING_RE = re.compile(r"^##(?:\s+\d+\.)?\s+(?:内容索引|章节目录|连续阅读目录|章节地图)\s*$")
PLATFORM_TITLE = "Android Camera 平台管线：HAL3、Buffer、ZSL 与显示"
TOOL_TITLE = "Camera 性能分析工具：Perfetto、SQL 与 GFXReconstruct"
STALE_CAMERA_PATHS = {
    "src/part2-performance/ch18-rendering-pipelines/14-camera-pipeline.md",
    "src/part2-performance/ch18-rendering-pipelines/10-camera-pipeline.md",
    "src/part1-fundamentals/ch02-rendering/32-camera-hal3-buffer-management.md",
    "src/part1-fundamentals/ch02-rendering/33-camerax-zsl-hal-mapping.md",
    SOURCE,
}


def canonical_paths() -> list[Path]:
    return sorted(
        path
        for path in ROOT.glob("src/part*/ch*/*.md")
        if path.name != "README.md"
    )


def h3(block: prior.Block, title: str) -> prior.Block:
    _, blocks = window.split_level(block.lines, 3)
    return window.block_map(blocks)[title]


def h4(block: prior.Block, title: str) -> prior.Block:
    _, blocks = window.split_level(block.lines, 4)
    return window.block_map(blocks)[title]


def render_nested(
    block: prior.Block,
    *,
    source_level: int = 4,
    destination_level: int = 4,
    renames: dict[str, str] | None = None,
) -> list[str]:
    prefix, children = window.split_level(block.lines, source_level)
    renames = renames or {}
    revised = [prior.Block(renames.get(item.title, item.title), item.lines) for item in children]
    return window.render_level(prefix, revised, destination_level)


def append_h4(block: prior.Block, title: str, lines: list[str]) -> None:
    prefix, children = window.split_level(block.lines, 4)
    children.append(prior.Block(title, window.trim(lines)))
    block.lines = window.render_level(prefix, children, 4)


def insert_after(blocks: list[prior.Block], anchor: str, item: prior.Block) -> None:
    index = next(index for index, block in enumerate(blocks) if block.title == anchor)
    blocks.insert(index + 1, item)


def merge_meta(target: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    result = prior.merge_meta(target, source, SOURCE)
    result["last_consolidated_at"] = "2026-08-24"
    result["last_verified"] = max(
        str(target.get("last_verified") or ""),
        str(source.get("last_verified") or ""),
    )
    result["last_verified_against"] = " + ".join(
        value
        for value in prior.unique(
            [
                str(target.get("last_verified_against") or ""),
                str(source.get("last_verified_against") or ""),
            ]
        )
        if value
    )
    return normalize_meta_paths(result)


def normalize_meta_paths(meta: dict[str, Any]) -> dict[str, Any]:
    result = dict(meta)
    sources: list[Any] = []
    for item in list(result.get("sources") or []):
        if isinstance(item, dict) and str(item.get("path") or "") in STALE_CAMERA_PATHS:
            item = dict(item)
            item["path"] = PLATFORM_TARGET
        sources.append(item)
    result["sources"] = prior.unique(sources)
    return result


def source_blocks_for(source_text: str, destination: str) -> tuple[dict[str, Any], dict[str, prior.Block]]:
    relocated = relocate_links(source_text, SOURCE, destination)
    meta, body = prior.parse_document(relocated)
    return meta, prior.by_title(prior.split_blocks(body)[1])


def merge_platform(source_text: str, target_text: str) -> str:
    source_meta, sources = source_blocks_for(source_text, PLATFORM_TARGET)
    target_meta, target_body = prior.parse_document(target_text)
    prefix, target_list = prior.split_blocks(target_body)
    target_blocks = prior.by_title(target_list)

    target_meta = merge_meta(target_meta, source_meta)
    target_meta["title"] = PLATFORM_TITLE
    target_meta["tags"] = prior.unique(list(target_meta.get("tags") or []) + ["Buffer", "CameraX"])
    target_meta["related_chapters"] = prior.unique(
        list(target_meta.get("related_chapters") or []) + ["22.19"]
    )
    prefix_text = "\n".join(prefix)
    prefix_text = prefix_text.replace("# Android 17 Camera 渲染管线", f"# {PLATFORM_TITLE}", 1)
    old_opening = (
        "Camera 不是单 Producer 到单 Surface 的线性管线；同一 request 可以生成多个 buffer，并被预览、拍照、分析或编码消费者以不同节奏接收。"
        "诊断卡顿和时序问题时，要沿 request、result、buffer 与时间戳分别追踪。"
    )
    new_opening = (
        "Camera 不是单 Producer 到单 Surface 的线性管线；同一 request 可以生成多个 buffer，并被预览、拍照、分析或编码消费者以不同节奏接收。"
        "本文把 HAL3 request-result、逐 stream buffer 所有权、ZSL 重处理和预览显示放在一条责任链上。诊断时要沿 request、result、buffer、fence 与时间戳分别追踪。"
    )
    if old_opening not in prefix_text:
        raise ValueError("platform opening changed")
    prefix = prefix_text.replace(old_opening, new_opening, 1).splitlines()

    camera3 = sources["Camera3 Request、Buffer 与 Stream"]
    hal = target_blocks["HAL3 的 request-result 与多消费者"]
    hal_prefix, hal_sections = window.split_level(hal.lines, 3)
    hal_map = window.block_map(hal_sections)
    source_config = h3(camera3, "2. `configureStreams()` 决定什么")
    config_prefix, config_children = window.split_level(source_config.lines, 4)
    source_config_parts = window.block_map(config_children)
    config_target = hal_map["配置阶段决定这组输出能不能成立"]
    append_h4(config_target, "`HalStream` 返回的格式、usage 与 buffer 约束", config_prefix)
    append_h4(
        config_target,
        "队列容量为什么不等于 `maxBuffers`",
        source_config_parts["2.1 `maxBuffers` 与队列总量"].lines,
    )
    append_h4(
        config_target,
        "`Camera3BufferManager` 与 HAL buffer management",
        source_config_parts["2.2 系统框架内部 BufferManager 与 HAL 缓冲区管理不同"].lines,
    )
    hal.lines = window.render_level(hal_prefix, hal_sections, 3)

    lifecycle = target_blocks["Android 17 的 Request-Buffer 生命周期"]
    lifecycle_prefix, lifecycle_sections = window.split_level(lifecycle.lines, 3)
    lifecycle_map = window.block_map(lifecycle_sections)
    lifecycle_map["Framework-managed buffer：先借 buffer，再提交 request"].lines = render_nested(
        h3(camera3, "3. 系统框架管理缓冲区时的一帧生命周期"),
        renames={
            "3.1 系统框架从 Surface 取得可写缓冲区": "Surface 交出可写 buffer",
            "3.2 HAL 等待 acquire fence 后写入图像": "HAL 等待 acquire fence 后写入",
            "3.3 HAL 用 release fence 归还写入结果": "HAL 以 release fence 归还结果",
            "3.4 CameraService 将缓冲区入队或取消": "CameraService 决定 queue 或 cancel",
            "3.5 消费方释放后才能再次出队": "consumer 释放后才能再次出队",
        },
    )
    lifecycle_map["HAL buffer management：request 先走，buffer 按需借"].lines = render_nested(
        h3(camera3, "4. Android 17 的 HAL 缓冲区管理路径"),
        renames={
            "4.1 `requestStreamBuffers()` 取得的缓冲区不绑定特定帧": "`requestStreamBuffers()` 不预先绑定 frame",
            "4.2 `bufferId` 与句柄缓存": "`bufferId`、handle 与 cache 生命周期",
            "4.3 `returnStreamBuffers()` 只归还未用于结果的缓冲区": "`returnStreamBuffers()` 只归还未使用 buffer",
            "4.4 `signalStreamFlush()` 与 `flush()` 的区别": "`signalStreamFlush()` 与 `flush()` 的责任差异",
        },
    )
    error_block = h3(camera3, "9. 出错、重配置与关闭时的所有权")
    insert_after(
        lifecycle_sections,
        "三类 fence 要分别看",
        prior.Block(
            "错误、重配置与关闭时的所有权",
            render_nested(
                error_block,
                renames={
                    "9.1 缓冲区出错时也要保留栅栏语义": "错误 buffer 仍要保留 fence 语义",
                    "9.2 Surface 断开是流的局部错误": "Surface 断开是逐 stream 错误",
                    "9.3 `flush()` 返回后不得残留 HAL 缓冲区": "`flush()`、关闭与 cache 失效",
                },
            ),
        ),
    )
    lifecycle.lines = window.render_level(lifecycle_prefix, lifecycle_sections, 3)

    consumers = target_blocks["三种主要消费路径"]
    consumer_prefix, consumer_sections = window.split_level(consumers.lines, 3)
    memory_lines = list(h4(h3(camera3, "6. 多输出的内存与背压"), "6.1 每路输出单独计算，整个会话共同受限").lines)
    memory_lines.extend(
        [
            "",
            "各路输出虽然有独立队列，一次 capture request 仍可能同时要求多路结果。分析流积压后预览也掉帧时，只能先把分析 consumer 列为候选；还要用 frame number、各 stream result 返回时间和 buffer 归还记录，证明它是否通过共享 ISP stage、缩放器、带宽或内部池拖慢了其他流。",
        ]
    )
    consumer_sections.insert(0, prior.Block("按 stream 估算驻留量与跨流反压", memory_lines))
    consumers.lines = window.render_level(consumer_prefix, consumer_sections, 3)

    zsl_source = sources["ZSL 缓存与 Reprocessing"]
    zsl = target_blocks["ZSL：把两种机制分开"]
    zsl_prefix, zsl_sections = window.split_level(zsl.lines, 3)
    zsl_map = window.block_map(zsl_sections)
    zsl_sections.insert(
        0,
        prior.Block("ZSL 只省去按键后的新曝光", h3(zsl_source, "1. ZSL 减少的是哪一段时间").lines),
    )
    app_zsl = zsl_map["Application-operated ZSL：ring buffer + reprocess"]
    app_prefix, app_parts = window.split_level(app_zsl.lines, 4)
    app_prefix_text = "\n".join(app_prefix)
    marker = "CameraX 的 `CAPTURE_MODE_ZERO_SHUTTER_LAG`"
    marker_index = app_prefix_text.find(marker)
    if marker_index < 0:
        raise ValueError("application ZSL marker missing")
    app_prefix_text = app_prefix_text[:marker_index].rstrip() + (
        "\n\nCameraX 对这条路径的 1.6.1 实现、三帧 ring、禁用条件和 CameraPipe 调用链见"
        "[§22.19 CameraX：UseCase、Camera2 映射与性能]"
        "(../../part5-app/ch22-rendering-practice/19-camerax-rendering.md)。"
    )
    app_parts.extend(
        [
            prior.Block(
                "HAL 以 `inputBuffer` 识别重处理请求",
                h3(zsl_source, "7. Android 17 系统框架如何识别重处理请求").lines,
            ),
            prior.Block(
                "输入 buffer 的所有权与 sensor 边界",
                list(h4(h3(zsl_source, "8. 缓冲区、同步栅栏与背压"), "8.2 输入缓冲区的所有权跨过 HAL").lines)
                + [""]
                + list(h4(h3(zsl_source, "8. 缓冲区、同步栅栏与背压"), "8.3 重处理请求不读取传感器").lines),
            ),
        ]
    )
    app_zsl.lines = window.render_level(app_prefix_text.splitlines(), app_parts, 4)
    zsl.lines = window.render_level(zsl_prefix, zsl_sections, 3)

    perfetto = target_blocks["Perfetto：从 request 追到 present"]
    perf_prefix, perf_sections = window.split_level(perfetto.lines, 3)
    perf_source = h3(camera3, "10. 用 Perfetto 和 `dumpsys` 建立证据")
    evidence_children = [
        prior.Block("cameraserver 的源码与 dump 锚点", h4(perf_source, "10.3 AOSP 能直接提供的线索").lines),
        prior.Block("buffer 现象的下一步证据", h4(perf_source, "10.4 常见现象与下一步").lines),
        prior.Block("buffer wait 不自动等于 ANR", h4(perf_source, "10.5 缓冲区阻塞不自动等于 ANR").lines),
    ]
    perf_sections.append(
        prior.Block(
            "CameraService 直接证据与 ANR 边界",
            window.render_level([], evidence_children, 4),
        )
    )
    perfetto.lines = window.render_level(perf_prefix, perf_sections, 3)

    versions = target_blocks["Android 12—17 的版本演进"]
    version_text = "\n".join(versions.lines)
    first_version = "- **Android 12 / API 31**"
    if first_version not in version_text:
        raise ValueError("version list marker missing")
    version_text = version_text.replace(
        first_version,
        "- **Android 10 / API 29**：引入可选的 HAL3 buffer management，request 可以先进入 pipeline，HAL 再按需取得 output buffer。\n"
        + first_version,
        1,
    )
    version_prefix, version_sections = window.split_level(version_text.splitlines(), 3)
    version_sections.append(
        prior.Block(
            "16 KB page size、DMA-BUF heaps 与 ION",
            render_nested(
                h3(camera3, "7. 16 KB 页大小与 ION：纠正常见误解"),
                renames={
                    "7.1 16 KB 页大小并非 Android 17 首次引入": "16 KB page size 不规定 Camera buffer 几何对齐",
                    "7.2 Android 17 不再支持 ION": "Android 17 的共享内存边界不再包含 ION",
                },
            ),
        )
    )
    versions.lines = window.render_level(version_prefix, version_sections, 3)

    mistakes = target_blocks["常见误判"]
    extra_rows = [
        "| `TEMPLATE_ZERO_SHUTTER_LAG` 能证明 HAL 收到历史图像 | 模板只表达上层意图；HAL 边界必须看到有效 `inputBuffer` |",
        "| 重处理会重新曝光一次 | reprocess 从 session input Surface 读取已有图像，不采集新的 sensor 数据 |",
        "| ZSL 失败总会透明重试普通拍照 | 取帧前可以降级；input 已提交后的失败不能假定会自动重试 |",
    ]
    mistakes.lines = window.trim(list(mistakes.lines) + extra_rows)

    relations = target_blocks["与其他章节的关系"]
    relations.lines = window.trim(
        list(relations.lines)
        + [
            "- **§22.19 CameraX：UseCase、Camera2 映射与性能**：CameraX 1.6.1 的 ZSL ring、CameraPipe 重处理、ImageCapture 与用例组合。"
        ]
    )
    return prior.dump_document(target_meta, prior.render_blocks(prefix, target_list))


def merge_app(source_text: str, target_text: str) -> str:
    source_meta, sources = source_blocks_for(source_text, APP_TARGET)
    target_meta, target_body = prior.parse_document(target_text)
    prefix, target_list = prior.split_blocks(target_body)
    target_blocks = prior.by_title(target_list)
    target_meta = merge_meta(target_meta, source_meta)

    image_capture = target_blocks["6. ImageCapture：捕获模式只表达偏好"]
    capture_prefix, capture_sections = window.split_level(image_capture.lines, 3)
    capture_map = window.block_map(capture_sections)
    mode = capture_map["6.1 三种捕获模式"]
    mode_text = "\n".join(mode.lines)
    old = (
        "ZSL 的名称不承诺文件立即可用。它要求 API 23 及以上，并要求设备支持 `PRIVATE` reprocessing；`PRIVATE` 指应用不能直接读取像素布局的私有缓冲区，reprocessing 则把已捕获图像送回相机处理管线。不满足条件时，CameraX 会回退到 `MINIMIZE_LATENCY`。闪光灯为 ON / AUTO、绑定 `VideoCapture` 或使用 Extensions 时，当前公开说明不支持 ZSL。使用前应查询 `CameraInfo.isZslSupported()`，运行日志还要记录查询结果、闪光灯状态、用例组合与捕获模式。\n\n"
        "ZSL 会维护候选帧并增加缓冲区占用。官方文档描述的候选数量属于 CameraX 库实现，不是 Android 17 平台常量；内存评估应以锁定的 CameraX 版本和实际输出尺寸为准。"
    )
    replacement = (
        "ZSL 的名称不承诺文件立即可用；它只表达优先复用历史候选帧的捕获策略。公开能力边界与 CameraX 1.6.1 的具体实现必须分开：设备能力、用例组合和单次 ring 取帧都可能让请求降级，固定实现见 6.4。"
    )
    if old not in mode_text:
        raise ValueError("CameraX public ZSL paragraph changed")
    mode.lines = mode_text.replace(old, replacement, 1).splitlines()

    zsl_source = sources["ZSL 缓存与 Reprocessing"]
    capability = h3(zsl_source, "3. `isZslSupported()` 是设备能力预筛选")
    session = h3(zsl_source, "4. 会话怎样完成配置")
    ring = h3(zsl_source, "5. 环形队列中保存了什么")
    mapping = h3(zsl_source, "6. 从 CameraX 请求映射到 Camera2 重处理请求")
    ownership = h4(h3(zsl_source, "8. 缓冲区、同步栅栏与背压"), "8.1 ZSL 输出也会占用相机流缓冲区")
    ownership_lines = [
        line.replace("[Camera HAL3 Buffer 管理]", "[Camera 平台管线的逐 stream Buffer 方法]")
        for line in ownership.lines
    ]
    verification = h3(zsl_source, "9. 如何验证设备上是否走了 ZSL")
    _, verify_parts = window.split_level(verification.lines, 4)
    verify_map = window.block_map(verify_parts)
    verification_lines = window.render_level(
        [],
        [
            prior.Block("记录应用层条件", verify_map["9.1 记录应用层条件"].lines),
            prior.Block("检查 CameraX 日志", verify_map["9.2 检查 CameraX 日志"].lines),
        ],
        5,
    )
    version_lines = list(sources["版本与实现边界"].lines)
    detail_parts = [
        prior.Block(
            "能力预筛选、会话校验与禁用条件",
            render_nested(capability, source_level=4, destination_level=5, renames={"3.1 CameraX 1.6.1 的禁用条件": "CameraX 1.6.1 的禁用与兼容性条件"}),
        ),
        prior.Block(
            "`PRIVATE` output、input Surface 与 reprocessable session",
            render_nested(session, source_level=4, destination_level=5, renames={"4.1 输入格式固定为 `PRIVATE`": "输入格式与合法输出", "4.2 同一个会话中同时存在输出与输入": "同一 session 的候选输出与重处理输入"}),
        ),
        prior.Block(
            "三帧 ring、元数据匹配与 3A 过滤",
            render_nested(ring, source_level=4, destination_level=5, renames={"5.1 图像必须先与元数据按时间戳匹配": "图像与 metadata 先按 timestamp 配对", "5.2 CameraX 1.6.1 只接纳三自动状态合格的帧": "AF、AE、AWB 决定候选资格", "5.3 三个容易混淆的数量": "ring、ImageReader 与 input 的三个上限", "5.4 当前实现没有“最佳帧评分器”": "当前实现没有图像评分器"}),
        ),
        prior.Block(
            "CameraPipe 怎样构造并回收重处理请求",
            render_nested(mapping, source_level=4, destination_level=5, renames={"6.1 `CaptureConfigAdapter` 生成 `InputRequest`": "`CaptureConfigAdapter` 生成 InputRequest", "6.2 `ImageWriter` 把缓冲区送入会话输入端": "ImageWriter 排入 session input", "6.3 `TotalCaptureResult` 初始化重处理请求": "TotalCaptureResult 初始化 reprocess request", "6.4 生命周期必须覆盖成功、失败和取消": "成功、失败、取消都要回收 input image"}),
        ),
        prior.Block("候选帧也占用 stream buffer", ownership_lines),
        prior.Block("应用条件、降级与日志证据", verification_lines),
        prior.Block("CameraX 1.6.1 与 Android 17 的双版本边界", version_lines),
    ]
    detail = prior.Block(
        "6.4 CameraX 1.6.1 ZSL：3 帧 ring 与 CameraPipe 重处理",
        [
            "6.1 说明公开模式偏好；这一节锁定 CameraX 1.6.1，回答一次请求怎样从能力检查走到 PRIVATE 候选帧、CameraPipe `InputRequest` 和资源回收。升级 CameraX 后，ring 容量、quirk、过滤条件与后端路径都要重新核对。",
            "",
            *window.render_level([], detail_parts, 4),
        ],
    )
    insert_after(capture_sections, "6.3 Android 17 RAW14 与 CameraX RAW 不可直接画等号", detail)
    image_capture.lines = window.render_level(capture_prefix, capture_sections, 3)
    return prior.dump_document(target_meta, prior.render_blocks(prefix, target_list))


def merge_tool(source_text: str, target_text: str) -> str:
    source_meta, sources = source_blocks_for(source_text, TOOL_TARGET)
    target_meta, target_body = prior.parse_document(target_text)
    prefix, target_list = prior.split_blocks(target_body)
    target_blocks = prior.by_title(target_list)
    target_meta = merge_meta(target_meta, source_meta)
    target_meta["title"] = TOOL_TITLE
    prefix_text = "\n".join(prefix).replace(
        "# Android Camera 性能与 Perfetto 分析",
        f"# {TOOL_TITLE}",
        1,
    )
    prefix = prefix_text.splitlines()

    buffer_model = target_blocks["Camera 管线的 Buffer 流转"]
    buffer_model.title = "分析所需的最小 Camera Buffer 模型"

    preview = target_blocks["Camera 预览卡顿分析"]
    preview_prefix, preview_sections = window.split_level(preview.lines, 3)
    zsl = window.block_map(preview_sections)["拍照与 ZSL 的时间边界"]
    timing = h4(h3(sources["ZSL 缓存与 Reprocessing"], "9. 如何验证设备上是否走了 ZSL"), "9.5 延迟要区分源帧年龄与完成时间")
    append_h4(zsl, "`source_age`、`callback_latency` 与 `save_latency`", timing.lines)
    preview.lines = window.render_level(preview_prefix, preview_sections, 3)
    return prior.dump_document(target_meta, prior.render_blocks(prefix, target_list))


def relocate_links(text: str, origin: str, destination: str) -> str:
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
            target = PRIMARY_REDIRECT.get(old_relative, old_relative)
            new_link = os.path.relpath(ROOT / target, destination_path.parent)
            if marker and old_relative not in PRIMARY_REDIRECT:
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


def build_documents() -> tuple[dict[str, tuple[str, str]], dict[str, str]]:
    paths = canonical_paths()
    id_moves = {prior.chapter_id(SOURCE): prior.chapter_id(PLATFORM_TARGET)}
    source_text = (ROOT / SOURCE).read_text(encoding="utf-8")
    merged = {
        PLATFORM_TARGET: merge_platform(source_text, (ROOT / PLATFORM_TARGET).read_text(encoding="utf-8")),
        APP_TARGET: merge_app(source_text, (ROOT / APP_TARGET).read_text(encoding="utf-8")),
        TOOL_TARGET: merge_tool(source_text, (ROOT / TOOL_TARGET).read_text(encoding="utf-8")),
    }
    documents: dict[str, tuple[str, str]] = {}
    for path in paths:
        relative = str(path.relative_to(ROOT))
        if relative == SOURCE:
            continue
        text = merged.get(relative, path.read_text(encoding="utf-8"))
        text = relocate_links(text, relative, relative)
        text = prior.update_document_ids(text, relative, id_moves)
        documents[relative] = (relative, text)
    return documents, id_moves


def rewrite_auxiliary(relative: str, id_moves: dict[str, str]) -> str:
    text = (ROOT / relative).read_text(encoding="utf-8")
    text = relocate_links(text, relative, relative)
    return v2.rewrite_chapter_references(text, id_moves)


def rebuild_readme(relative: str, documents: dict[str, tuple[str, str]], id_moves: dict[str, str]) -> str:
    text = rewrite_auxiliary(relative, id_moves)
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if INDEX_HEADING_RE.match(line)), None)
    if start is None:
        raise ValueError(f"README index heading missing: {relative}")
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    directory = str(Path(relative).parent)
    rows = sorted(
        (path, prior.title_and_id(value))
        for path, (_, value) in documents.items()
        if str(Path(path).parent) == directory
    )
    index = [lines[start], ""] + [
        f"- [{chapter} {title}]({Path(path).name})"
        for path, (title, chapter) in rows
    ] + [""]
    return "\n".join(lines[:start] + index + lines[end:]).rstrip() + "\n"


def rebuild_summary(documents: dict[str, tuple[str, str]], id_moves: dict[str, str]) -> str:
    relative = "src/SUMMARY.md"
    lines = rewrite_auxiliary(relative, id_moves).splitlines()
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
            (path, prior.title_and_id(value))
            for path, (_, value) in documents.items()
            if str(Path(path).parent) == directory
        )
        lines[index + 1 : end] = [
            f"  - [{chapter} {title}]({str(Path(path).relative_to('src'))})"
            for path, (title, chapter) in rows
        ]
        index += 1 + len(rows)
    return "\n".join(lines).rstrip() + "\n"


def replace_json_values(value: Any, id_moves: dict[str, str]) -> Any:
    if isinstance(value, str):
        if value in PRIMARY_REDIRECT:
            return PRIMARY_REDIRECT[value]
        return id_moves.get(value, value)
    if isinstance(value, list):
        return [replace_json_values(item, id_moves) for item in value]
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            new_key = PRIMARY_REDIRECT.get(key, id_moves.get(key, key))
            result[new_key] = replace_json_values(item, id_moves)
        return result
    return value


def build_json_updates(id_moves: dict[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted((ROOT / "metadata").glob("*.json")):
        relative = str(path.relative_to(ROOT))
        if relative in HISTORICAL_JSON:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        revised = replace_json_values(data, id_moves)
        value = json.dumps(revised, ensure_ascii=False, indent=2) + "\n"
        if value != path.read_text(encoding="utf-8"):
            result[relative] = value
    return result


def build_map(id_moves: dict[str, str]) -> str:
    roles = {
        PLATFORM_TARGET: "HAL3 stream/buffer/fence, failure recovery and platform ZSL boundary",
        APP_TARGET: "CameraX 1.6.1 ring buffer, CameraPipe reprocessing and app diagnostics",
        TOOL_TARGET: "ZSL source-age and completion-latency measurement",
    }
    report = {
        "schema_version": 1,
        "reviewed_at": "2026-08-24",
        "before_count": 286,
        "after_count": 285,
        "primary_redirect": {"source": SOURCE, "target": PLATFORM_TARGET},
        "merged_paths": [
            {
                "source": SOURCE,
                "target": target,
                "role": roles[target],
                "recoverable_from_git": True,
            }
            for target in TARGETS
        ],
        "chapter_id_moves": id_moves,
    }
    return json.dumps(report, ensure_ascii=False, indent=2) + "\n"


def validate_documents(documents: dict[str, tuple[str, str]]) -> None:
    if len(documents) != 285:
        raise ValueError(f"expected 285 canonical bodies, got {len(documents)}")
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


def apply_outputs(documents: dict[str, tuple[str, str]], auxiliary: dict[str, str]) -> None:
    affected = set(TARGETS) | {SOURCE}
    with tempfile.TemporaryDirectory(prefix="aiw-camera-consolidation-") as temp_value:
        temp_root = Path(temp_value)
        for relative in TARGETS:
            staged = temp_root / relative
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_text(documents[relative][1], encoding="utf-8", newline="\n")
        for relative in affected:
            path = ROOT / relative
            if path.exists():
                path.unlink()
        for relative in TARGETS:
            target = ROOT / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                (temp_root / relative).read_text(encoding="utf-8"),
                encoding="utf-8",
                newline="\n",
            )

    for relative, (_, text) in documents.items():
        path = ROOT / relative
        if relative not in TARGETS and text != path.read_text(encoding="utf-8"):
            path.write_text(text, encoding="utf-8", newline="\n")
    for relative, text in auxiliary.items():
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    documents, id_moves = build_documents()
    validate_documents(documents)

    current_canonical = {str(path.relative_to(ROOT)) for path in canonical_paths()}
    auxiliary: dict[str, str] = {}
    for path in sorted(ROOT.glob("src/**/*.md")):
        relative = str(path.relative_to(ROOT))
        if relative in current_canonical:
            continue
        auxiliary[relative] = rewrite_auxiliary(relative, id_moves)
    for directory in AFFECTED_DIRS:
        readme = str(Path(directory) / "README.md")
        auxiliary[readme] = rebuild_readme(readme, documents, id_moves)
    auxiliary["src/SUMMARY.md"] = rebuild_summary(documents, id_moves)
    auxiliary.update(build_json_updates(id_moves))
    auxiliary[MAP_PATH] = build_map(id_moves)

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
        apply_outputs(documents, auxiliary)
    print(
        json.dumps(
            {
                "mode": "apply" if args.apply else "dry-run",
                "canonical_bodies": len(documents),
                "distributed_source": SOURCE,
                "targets": TARGETS,
                "chapter_id_moves": id_moves,
                "validated_local_links": checked_links,
                "json_updates": len(build_json_updates(id_moves)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
