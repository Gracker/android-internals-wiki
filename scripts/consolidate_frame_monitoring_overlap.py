#!/usr/bin/env python3
"""Fuse the duplicate JankStats/FrameMetrics article into the monitoring owner.

22.7 remains the canonical entry because it already owns the full production
workflow: frame signals, compositor correlation, stack sampling, alerting and
postmortems.  The transform embeds the source-only API/version semantics from
19.6, removes duplicated tutorials, and reindexes the remaining chapter 19
articles.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/part3-tools/ch19-apm/06-jankstats-framemetrics.md"
TARGET = ROOT / "src/part5-app/ch22-rendering-practice/07-frame-monitoring.md"
MAP_PATH = ROOT / "metadata/2026-08-24-editorial-fusion-v10-map.json"

REINDEX = [
    (
        ROOT / "src/part3-tools/ch19-apm/07-jetpack-benchmark-baseline-profiles.md",
        ROOT / "src/part3-tools/ch19-apm/06-jetpack-benchmark-baseline-profiles.md",
        "19.7",
        "19.6",
    ),
    (
        ROOT / "src/part3-tools/ch19-apm/08-lab-tools-device-benchmarks.md",
        ROOT / "src/part3-tools/ch19-apm/07-lab-tools-device-benchmarks.md",
        "19.8",
        "19.7",
    ),
    (
        ROOT / "src/part3-tools/ch19-apm/09-network-apm-internals.md",
        ROOT / "src/part3-tools/ch19-apm/08-network-apm-internals.md",
        "19.9",
        "19.8",
    ),
    (
        ROOT / "src/part3-tools/ch19-apm/10-crash-anr-internals.md",
        ROOT / "src/part3-tools/ch19-apm/09-crash-anr-internals.md",
        "19.10",
        "19.9",
    ),
    (
        ROOT / "src/part3-tools/ch19-apm/11-battery-thermal-apm.md",
        ROOT / "src/part3-tools/ch19-apm/10-battery-thermal-apm.md",
        "19.11",
        "19.10",
    ),
    (
        ROOT / "src/part3-tools/ch19-apm/12-hybrid-apm.md",
        ROOT / "src/part3-tools/ch19-apm/11-hybrid-apm.md",
        "19.12",
        "19.11",
    ),
    (
        ROOT / "src/part3-tools/ch19-apm/13-apm-client-architecture.md",
        ROOT / "src/part3-tools/ch19-apm/12-apm-client-architecture.md",
        "19.13",
        "19.12",
    ),
]

CHAPTER_REMAP = {
    "19.6": "22.7",
    "19.7": "19.6",
    "19.8": "19.7",
    "19.9": "19.8",
    "19.10": "19.9",
    "19.11": "19.10",
    "19.12": "19.11",
    "19.13": "19.12",
}


JANK_ARTIFACT_SECTION = r"""
### 发布物下限、实现分桶与字段语义

版本下限必须以实际发布物为准。`metrics-performance:1.0.0` 的 sources JAR 仍包含 `JankStatsApi16Impl`，但稳定 AAR 的 manifest 声明 `minSdkVersion=23`；正常 Gradle 依赖因此从 Android 6 / API 23 开始，不能因为类名里有 Api16 就写成稳定版支持 API 16。2026-08-14 复核的 AAR SHA-256 为 `efe2e0d92c7cb2f40c77d337052623fdb631d684ba145881e5a52a664d5614a0`，sources JAR 为 `55c5478b4fde6e1cded38d647e9d995a6d9d08e3b8abd28268b5d5a5c3e700a2`。

稳定 AAR 在当前系统范围内采用四条路径：

| Android 版本 | AndroidX 实现 | 关键行为 |
| --- | --- | --- |
| API 23 | `JankStatsApi16Impl` fallback | 用 pre-draw 和反射的 Choreographer 时间估算，精度低于 FrameMetrics |
| API 24—25 | `JankStatsApi24Impl` | 使用 Window FrameMetrics；帧起点仍来自低版本估算，CPU 字段直接取 `TOTAL_DURATION` |
| API 26—30 | `JankStatsApi26Impl` | 帧起点改用 `INTENDED_VSYNC_TIMESTAMP`，仍没有平台 `DEADLINE` |
| API 31—37 | `JankStatsApi31Impl` | 用 `DEADLINE` 作为 expected duration，并增加 total、CPU 与 overrun 字段 |

Android 17 / API 37 仍走 Api31Impl。JankStats 1.0.0 没有 API 36/37 专用实现，也不会把 `FRAME_TIMELINE_VSYNC_ID` 或 `SurfaceControl.JankData` 暴露到 `FrameDataApi31`；应用、合成器和其他系统组件的分类仍要走后文 API 36+ 的直接关联。
""".strip()


STATE_OWNER_SECTION = r"""
### `PerformanceMetricsState` 的时间线与 owner

状态标签不是回调到达瞬间读取的一份“当前页面变量”。`putState()` / `removeState()` 用 `System.nanoTime()` 记录每个 `StateInfo` 的起止时间，JankStats 再用一帧的 `[frameStart, frameEnd]` 与这些区间求交集。因此 `screen=Home`、`interaction=scroll` 表示该状态与这帧时间范围重叠；异步回调到达后再读取当前 route，会把转场后的页面误贴到旧帧上。

同一 View hierarchy 只有一个 `PerformanceMetricsState`，同名 key 会覆盖。团队应明确 owner：页面容器负责 `screen`，交互控制器负责 `interaction`，复用组件使用 `feed.list_state` 这类带命名空间的 key，并在离开层级时清理；只标记下一帧的短事件使用 `putSingleFrameState()`。Compose 没有独立采集器，可由 `LocalView.current` 找到同一个 hierarchy，但 Navigation 转场期间的 `screen` 应由 NavHost 或 Activity 统一维护，避免新旧页面同时写同一 key。
""".strip()


THRESHOLD_SECTION = r"""
### `isJank`、deadline miss 与 frozen frame 是三套口径

JankStats 的默认 `jankHeuristicMultiplier` 是 `2.0f`。API 23—30 根据 `Display.refreshRate` 估算 expected duration；1.0.0 会在进程内缓存首次结果，显示模式切换不会自动重算。API 31—37 则读取当前 `FrameMetrics.DEADLINE`。两条路径都用 `frameDurationUiNanos > expectedDuration × multiplier` 生成 `isJank`。

这与 `frameOverrunNanos = frameDurationTotalNanos - DEADLINE` 不是同一判断：前者比较 UI 时长与默认两倍预算，后者比较 total 时长与一次预算，所以同一帧完全可能 `overrun > 0` 而 `isJank == false`。服务端至少分开保存：

- JankStats jank rate：`isJank=true` 帧数 / 同一窗口全部回调帧数；
- deadline miss rate：API 31+ 中 `frameOverrunNanos > 0` 帧数 / 具有 overrun 字段的帧数；
- frozen frame rate：超过约定 duration 阈值的帧数 / 具有该 duration 字段的帧数，并注明用 UI 还是 total duration；
- UI、CPU、total、overrun 各自的 P50、P90、P95、P99，不能只留平均 FPS。

Firebase Performance 的 slow rendering frame 使用固定 16 ms，frozen frame 使用 700 ms，并明确假定 slow 指标面向 60 Hz。这可以作为外部兼容口径，不能与 JankStats 默认 `isJank` 合并成同一个 `slow_rate`。任何 multiplier、阈值或 duration 选择都要带策略/schema 版本；只上报异常帧会丢失分母，也无法计算可信比例。
""".strip()


FRAME_METRICS_DETAIL = r"""
### 指标是时间线索，不是可相加的阶段账单

Android 17 的 UI 线程和 RenderThread 共同填写 `FrameInfo` 时间戳数组，`FrameMetrics` 再按固定起止索引计算公开指标。Window listener 创建 observer 时使用 `waitForPresentTime=false`，所以回调表示 HWUI 统计已可用，不表示 SurfaceFlinger 已 latch 该 buffer 或屏幕已经 present。

| 指标 | API | 时间边界或含义 | 常见排查入口 |
| --- | ---: | --- | --- |
| `UNKNOWN_DELAY_DURATION` | 24+ | `INTENDED_VSYNC → HANDLE_INPUT_START` | 前序消息、调度、Binder 或锁让 UI 线程晚启动 |
| `INPUT_HANDLING_DURATION` | 24+ | `HANDLE_INPUT_START → ANIMATION_START` | 输入处理 |
| `ANIMATION_DURATION` | 24+ | `ANIMATION_START → PERFORM_TRAVERSALS_START` | animation callback 与状态更新 |
| `LAYOUT_MEASURE_DURATION` | 24+ | `PERFORM_TRAVERSALS_START → DRAW_START` | measure/layout 与 `requestLayout()` 扩散 |
| `DRAW_DURATION` | 24+ | `DRAW_START → SYNC_QUEUED` | display list 记录与自定义绘制 |
| `SYNC_DURATION` | 24+ | `SYNC_START → ISSUE_DRAW_COMMANDS_START` | RenderNode 同步与 RenderThread 压力 |
| `COMMAND_ISSUE_DURATION` | 24+ | `ISSUE_DRAW_COMMANDS_START → SWAP_BUFFERS` | RenderThread CPU 与驱动命令提交 |
| `SWAP_BUFFERS_DURATION` | 24+ | API 31+ 为 `SWAP_BUFFERS → SWAP_BUFFERS_COMPLETED` | BufferQueue 背压、swap 或消费等待 |
| `TOTAL_DURATION` | 24+ | `INTENDED_VSYNC → FRAME_COMPLETED` | HWUI 生产并提交帧的总区间，不是 present duration |
| `FIRST_DRAW_FRAME` | 24+ | Window visibility-change flag | 启动/导航首帧，和稳态滚动分开 |
| `GPU_DURATION` | 31+ | API 33+ 为 submission complete 到 GPU complete | GPU 工作量或资源争用线索 |
| `DEADLINE` | 31+ | `INTENDED_VSYNC → FRAME_DEADLINE` | 应用产出本帧的预算 |
| `FRAME_TIMELINE_VSYNC_ID` | 36+ | FrameTimeline VSync ID | 与 compositor jank data 关联 |

字段不可用时 `getMetric()` 返回 `-1`，不能补零。阶段可能并行，公开字段之间还有未单列的间隙；`TOTAL_DURATION - sum(stages)` 不能直接命名为“其他耗时”。GPU 与 swap 的定义也要按 API 分桶：24—30 没有 GPU/deadline，31—32 的 GPU 从 swap 起算，33—35 改从 command submission complete 起算，36—37 再增加 VSync ID。跨桶比较原始值会把平台定义变化误判成回归。

### Window 与独立内容流的覆盖边界

| 页面内容 | FrameMetrics 能看到 | 不能看到 |
| --- | --- | --- |
| 普通 View / 标准 Compose | 宿主 Window 的 UI、RenderThread 与 swap | 具体调用栈、SurfaceFlinger 和最终 present |
| TextureView | 外部 buffer 被 HWUI 采样后的宿主成本 | 外部 producer 自身、第一套 BufferQueue 与输入 fence |
| SurfaceView | 宿主 UI、hole-punch、几何与控制层帧 | 独立内容 Surface 的 producer、BufferQueue 与 layer 帧 |
| Dialog / PopupWindow / 多窗口 | 每个已注册 Window 各自的帧 | 未注册 Window；不同 Window 不会自动合并 |
| 软件渲染 Window | 没有硬件渲染帧统计 | 软件 Canvas 的完整耗时 |

JankStats 在 API 24+ 内部已经注册 FrameMetrics listener。应用再次直接监听时，要量化双重回调、复制和聚合开销；常规线上分布优先保留 JankStats，只有分段诊断或 API 36+ compositor join 才对受控样本开启直接 FrameMetrics。延迟回调也不能读取“当前 route”：API 26+ 用 `INTENDED_VSYNC_TIMESTAMP` 与应用状态区间关联，API 24—25 只做 Window session 级聚合，或在路由切换时明确结束旧会话。
""".strip()


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
        "applicable_versions: Android 10 (API 29) - Android 17 (API 37)",
        "applicable_versions: Android 6 (API 23) - Android 17 (API 37); advanced FrameMetrics fields require API 24/31/36 as noted",
        "target applicable versions",
    )
    text = replace_once(
        text,
        "last_verified_against: AOSP android-17.0.0_r1; AndroidX Metrics 1.0.0; Android FrameMetrics and JankData docs; Perfetto FrameTimeline docs",
        "last_verified_against: AndroidX metrics-performance 1.0.0 AAR and sources; AOSP android-17.0.0_r1 Choreographer/FrameMetrics/FrameMetricsObserver/SurfaceControl; Android JankStats, FrameMetrics, JankData and Perfetto FrameTimeline docs",
        "target verification provenance",
    )
    release_marker = (
        "- type: official\n"
        "  path: https://developer.android.com/jetpack/androidx/releases/metrics\n"
    )
    artifact_sources = (
        "- type: official\n"
        "  path: https://dl.google.com/android/maven2/androidx/metrics/metrics-performance/maven-metadata.xml\n"
        "- type: official\n"
        "  path: https://dl.google.com/android/maven2/androidx/metrics/metrics-performance/1.0.0/metrics-performance-1.0.0.aar\n"
        "- type: official\n"
        "  path: https://dl.google.com/android/maven2/androidx/metrics/metrics-performance/1.0.0/metrics-performance-1.0.0-sources.jar\n"
    )
    text = replace_once(text, release_marker, release_marker + artifact_sources, "artifact sources")
    aosp_marker = (
        "- type: aosp\n"
        "  path: frameworks/base/core/java/android/view/FrameMetrics.java\n"
    )
    aosp_sources = (
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/FrameMetricsObserver.java\n"
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/FrameMetricsObserver.h\n"
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/SurfaceControl.java\n"
        "- type: official\n"
        "  path: https://firebase.google.com/docs/perf-mon/screen-traces?platform=android\n"
    )
    text = replace_once(text, aosp_marker, aosp_marker + aosp_sources, "platform sources")
    text = replace_once(
        text,
        "- type: aiw\n  path: src/part3-tools/ch19-apm/06-jankstats-framemetrics.md\n",
        "",
        "obsolete internal source",
    )
    text = replace_once(text, "- '19.6'\n", "", "obsolete target relation")
    provenance = "- src/part5-app/ch22-rendering-practice/09-rendering-case-studies.md\n"
    text = replace_once(
        text,
        provenance,
        provenance + "- src/part3-tools/ch19-apm/06-jankstats-framemetrics.md\n",
        "target provenance",
    )
    text = replace_once(
        text,
        "线上出现“滑一下偶尔卡住”时，平均 FPS 很难说明责任在哪。可执行的治理流程要回答四个问题：监控覆盖了渲染路径的哪一段，异常集中在哪类设备和交互状态，代码现场反复出现什么，以及修复后怎样按同一口径验证。卡顿成因见 7.1 节，JankStats 与 FrameMetrics 的接口细节见 19.6 节。",
        "线上出现“滑一下偶尔卡住”时，平均 FPS 很难说明责任在哪。可执行的治理流程要回答四个问题：监控覆盖了渲染路径的哪一段，异常集中在哪类设备和交互状态，代码现场反复出现什么，以及修复后怎样按同一口径验证。本文统一维护 JankStats、FrameMetrics、系统合成器关联、堆栈采样、告警和复盘协议；卡顿定义与线下证据流程分别见 7.1 和 7.2。",
        "target opening",
    )
    jank_opening = (
        "截至 2026-08-14，AndroidX Metrics 当前稳定版为 1.0.0。JankStats 按 `Window` 跟踪帧，并把帧数据与 `PerformanceMetricsState` 中的 UI 状态一同交给监听器。API 16—23 使用较粗的时长估计；API 24+ 依赖平台 FrameMetrics，时长更可信；API 31+ 又增加 CPU、CPU + GPU 总时长与 overrun（超过截止时间的时长）信息。本文范围是 Android 10—17，服务端仍应记录 `api_level` 和 timing capability（可用的计时能力层级），不能把不同能力层的数据直接合成一条基线。"
    )
    jank_rewrite = (
        "截至 2026-08-14，AndroidX Metrics 当前稳定版为 1.0.0。JankStats 按 `Window` 跟踪帧，并把帧数据与 `PerformanceMetricsState` 中的 UI 状态一同交给监听器；它适合做线上第一层信号源，不自动上传、抓栈或生成 Perfetto trace。服务端必须记录 artifact、API level 与 timing capability，不能把不同实现分支的同名字段直接合成一条基线。\n\n"
        + JANK_ARTIFACT_SECTION
    )
    text = replace_once(text, jank_opening, jank_rewrite, "JankStats implementation insertion")
    text = replace_once(
        text,
        "| `FrameDataApi24` | `frameDurationCpuNanos` | 非 GPU 的 CPU 部分，包含 UI 线程和 RenderThread 时间 |",
        "| `FrameDataApi24` | `frameDurationCpuNanos` | API 24—30 直接取 `TOTAL_DURATION`；API 31+ 才用 `TOTAL_DURATION - GPU_DURATION + SWAP_BUFFERS_DURATION` 计算非 GPU 部分 |",
        "JankStats CPU field semantics",
    )
    text = replace_once(
        text,
        "JankStats 的监听线程随 API 层级变化：API 23 及以下是 Main/UI 线程，API 24+ 是内部 FrameMetrics 线程。",
        "JankStats 的监听线程随 API 层级变化：稳定 AAR 的 API 23 fallback 在 Main/UI 线程，API 24+ 使用内部 FrameMetrics 线程。",
        "JankStats callback thread",
    )
    state_marker = (
        "状态标签应采用低基数枚举，也就是取值来自数量有限的小集合，例如 `page=feed`、`feed_list=settling`。列表位置、搜索词、URL、订单号和用户输入会产生大量不同取值，同时带来隐私风险，不应进入帧标签。每个临时状态都要有对应的 `removeState()`；否则后续帧会继续携带已经失效的业务状态。"
    )
    text = replace_once(
        text,
        state_marker,
        state_marker + "\n\n" + STATE_OWNER_SECTION,
        "state interval insertion",
    )
    multiplier_marker = (
        "JankStats 的默认 `jankHeuristicMultiplier`（卡顿阈值倍数）是 2，也是产品统计口径的一部分。线上修改它会改变趋势，调整时必须登记策略版本并建立新基线。上报时保留 `isJank`，同时按能力层记录 UI 时长、CPU 时长、总时长、overrun 和状态；服务端再分析严重程度，无需改写客户端的原始判定。"
    )
    text = replace_once(text, multiplier_marker, THRESHOLD_SECTION, "threshold protocol fusion")
    frame_marker = (
        "API 31+ 可计算 `TOTAL_DURATION - DEADLINE`。结果大于零表示应用没有命中该帧预算；结果小于零表示仍有余量。`TOTAL_DURATION` 与各阶段可能并行，不能简单理解为其他时长字段之和。API 29 / 30 没有 `DEADLINE`，`getMetric()` 对不支持的指标 ID 返回 `-1`。低版本不要用固定刷新率伪造“精确 deadline”，应使用 JankStats 判定、同场景分布与 Perfetto 复核。"
    )
    text = replace_once(
        text,
        frame_marker,
        frame_marker + "\n\n" + FRAME_METRICS_DETAIL,
        "FrameMetrics detail insertion",
    )
    return text


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
        placeholder = f"__AIW_HISTORICAL_19_PATH_{index}__"
        protected = protected.replace(value, placeholder)
        restored[placeholder] = value
    return text[: match.start()] + protected + text[match.end() :], restored


def remap_related(text: str) -> str:
    pattern = re.compile(r"(?m)^(\s*-\s*['\"])(19\.(?:[6-9]|1[0-3]))(['\"]\s*)$")
    text = pattern.sub(lambda m: f"{m.group(1)}{CHAPTER_REMAP[m.group(2)]}{m.group(3)}", text)
    match = re.search(r"(?m)^related_chapters:\n((?:- .*\n)+)", text)
    if not match:
        return text
    seen: set[str] = set()
    kept: list[str] = []
    for line in match.group(1).splitlines(keepends=True):
        key = line.strip()
        if key in seen:
            continue
        seen.add(key)
        kept.append(line)
    return text[: match.start(1)] + "".join(kept) + text[match.end(1) :]


def update_references(path: Path, text: str) -> str:
    navigation_files = {
        ROOT / "src/SUMMARY.md",
        ROOT / "src/part3-tools/ch19-apm/README.md",
    }
    if path in navigation_files:
        lines = [line for line in text.splitlines() if SOURCE.name not in line]
        text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")

    historical = [str(SOURCE.relative_to(ROOT))]
    historical += [str(old.relative_to(ROOT)) for old, _, _, _ in REINDEX]
    text, placeholders = protect_consolidated_paths(text, historical)

    text = text.replace(relpath(SOURCE, path), relpath(TARGET, path))
    text = text.replace(str(SOURCE.relative_to(ROOT)), str(TARGET.relative_to(ROOT)))
    for old, new, _, _ in REINDEX:
        text = text.replace(relpath(old, path), relpath(new, path))
        text = text.replace(str(old.relative_to(ROOT)), str(new.relative_to(ROOT)))

    for placeholder, value in placeholders.items():
        text = text.replace(placeholder, value)
    text = remap_related(text)

    prose = {
        "捕获机制见 20.2、20.3 和 19.10": "捕获机制见 20.2、20.3 和 19.9",
        "Crash / ANR 捕获实现详见 19.10 节": "Crash / ANR 捕获实现详见 19.9 节",
        "14.7、19.10 和 20.3": "14.7、19.9 和 20.3",
        "Hybrid APM（Application Performance Monitoring，应用性能监控）见 19.12 节": "Hybrid APM（Application Performance Monitoring，应用性能监控）见 19.11 节",
        "底层网络 APM（application performance monitoring，应用性能监控）见 19.9": "底层网络 APM（application performance monitoring，应用性能监控）见 19.8",
        "（详见 19.9 节）": "（详见 19.8 节）",
        "详见 19.13 节": "详见 19.12 节",
        "19.13 节说明了": "19.12 节说明了",
        "详见 19.7 节": "详见 19.6 节",
        "19.7 节的 Macrobenchmark": "19.6 节的 Macrobenchmark",
    }
    for old, new in prose.items():
        text = text.replace(old, new)

    if path == ROOT / "src/part3-tools/ch19-apm/README.md":
        text = text.replace(
            "- 关注实验室与 Benchmark：19.9 统一操作复现、CPU/GPU/Web/存储测试和设备性能档位分组。",
            "- 关注回归与实验室测试：19.6 负责 Jetpack Benchmark 测量协议，19.7 负责操作复现、设备 Benchmark 与性能档位分组。",
        )
    if path == ROOT / "src/part3-tools/ch19-apm/01-apm-landscape-firebase-commercial.md":
        text = text.replace(
            "- 19.6—19.8：看官方帧信号、回归测量、Baseline Profiles 与系统受控取证；\n- 19.9：看外部性能测试、操作复现与设备 benchmark；\n- 19.10—19.14：看网络、crash/ANR、功耗、WebView/Flutter 等混合技术栈，以及大规模端侧架构。",
            "- 22.7：看 JankStats、FrameMetrics、系统合成器分类与线上卡顿治理；\n- 19.6—19.7：看 Jetpack Benchmark、Baseline Profile 验证、外部性能测试与设备 benchmark；\n- 19.8—19.12：看网络、crash/ANR、功耗、WebView/Flutter 混合栈与大规模端侧架构。",
        )
    return text


def h2_inventory(text: str) -> list[str]:
    return [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]


def validate(changed: dict[Path, str]) -> None:
    needles = [
        "minSdkVersion=23",
        "JankStatsApi31Impl",
        "状态标签不是回调到达瞬间",
        "frameOverrunNanos = frameDurationTotalNanos - DEADLINE",
        "FrameMetricsObserver.java",
        "Window 与独立内容流的覆盖边界",
        "JankStats 在 API 24+ 内部已经注册 FrameMetrics listener",
    ]
    missing = [needle for needle in needles if needle not in changed[TARGET]]
    if missing:
        raise RuntimeError(f"missing fused monitoring concepts: {missing}")
    h2s = h2_inventory(changed[TARGET])
    if len(h2s) != len(set(h2s)):
        raise RuntimeError("duplicate H2 headings in fused monitoring owner")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    required = [SOURCE, TARGET, *[row[0] for row in REINDEX]]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"Expected predecessor files are missing: {missing}")
    collisions = [row[1] for row in REINDEX if row[1].exists()]
    if collisions:
        raise SystemExit(f"Reindex destinations already exist: {collisions}")

    originals = {path: path.read_text(encoding="utf-8") for path in required}
    changed: dict[Path, str] = {TARGET: build_target(originals[TARGET])}
    for old, new, old_number, new_number in REINDEX:
        body = originals[old]
        body = replace_once(body, f"chapter: '{old_number}'", f"chapter: '{new_number}'", f"{old.name} chapter")
        body = replace_once(body, f"section: '{old_number}'", f"section: '{new_number}'", f"{old.name} section")
        changed[new] = body

    skip = {SOURCE, TARGET, *[row[0] for row in REINDEX]}
    for path in sorted((ROOT / "src").rglob("*.md")):
        if path in skip:
            continue
        original = path.read_text(encoding="utf-8")
        updated = update_references(path, original)
        if updated != original:
            changed[path] = updated
    for path in list(changed):
        changed[path] = update_references(path, changed[path])

    for relative in (
        "metadata/queue.json",
        "metadata/queue_backup.json",
        "metadata/queue.backup.2026-07-08T10-53-47.json",
    ):
        path = ROOT / relative
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        updated = original.replace(str(SOURCE.relative_to(ROOT)), str(TARGET.relative_to(ROOT)))
        for old, new, _, _ in REINDEX:
            updated = updated.replace(str(old.relative_to(ROOT)), str(new.relative_to(ROOT)))
        if updated != original:
            changed[path] = updated

    validate(changed)
    result = {
        "version": 10,
        "operation": "frame_monitoring_editorial_fusion",
        "count_change": {"before": 280, "after": 279},
        "merged_paths": [
            {
                "source": str(SOURCE.relative_to(ROOT)),
                "target": str(TARGET.relative_to(ROOT)),
                "role": "frame_monitoring_and_online_jank_owner",
            }
        ],
        "rewritten_paths": [str(TARGET.relative_to(ROOT))],
        "reindexed_paths": [
            {"from": str(old.relative_to(ROOT)), "to": str(new.relative_to(ROOT))}
            for old, new, _, _ in REINDEX
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
                "source": "19.6 JankStats entry, FrameData output and API-version differences",
                "destination": "22.7 JankStats / artifact and implementation buckets",
                "treatment": "unique_version_semantics_rewritten_and_embedded",
            },
            {
                "source": "19.6 jank threshold and slow-frame protocol",
                "destination": "22.7 isJank, deadline miss and frozen-frame protocol",
                "treatment": "unique_metric_boundaries_rewritten_and_embedded",
            },
            {
                "source": "19.6 FrameMetrics data boundaries and Window topology",
                "destination": "22.7 exact metric intervals and independent-content coverage",
                "treatment": "unique_platform_boundaries_rewritten_and_embedded",
            },
            {
                "source": "19.6 usage advice, UI context and Compose state marking",
                "destination": "22.7 PerformanceMetricsState timeline/owner + existing integration code",
                "treatment": "unique_state_semantics_embedded; duplicate_code_deduplicated",
            },
            {
                "source": "19.6 batch aggregation, rate definitions and common mistakes",
                "destination": "22.7 existing attribution, alert schema, checklist and postmortem sections",
                "treatment": "deduplicated_into_broader_governance_owner",
            },
            {
                "source": "19.6 references",
                "destination": "22.7 metadata sources and source index",
                "treatment": "evidence_reconciled",
            },
        ],
        "updated_reference_files": [
            str(path.relative_to(ROOT))
            for path in sorted(changed)
            if path not in {TARGET, *[row[1] for row in REINDEX]}
        ],
        "applied": args.apply,
    }

    if args.apply:
        for path, body in changed.items():
            path.write_text(body, encoding="utf-8")
        SOURCE.unlink()
        for old, _, _, _ in REINDEX:
            old.unlink()
        MAP_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
