#!/usr/bin/env python3
"""Distribute the mixed leak/growth article into its two actual owners.

The former 10.2 combined two different editorial jobs. 23.1 owns leak proof,
reference paths and lifecycle repair; 10.1 owns memory-domain classification,
repeatable baselines and non-leak growth. This transform embeds source-only
material in both owners, removes duplicated exposition and reindexes chapter 10.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/part2-performance/ch10-memory-perf/02-memory-leak-growth.md"
GROWTH_TARGET = ROOT / "src/part2-performance/ch10-memory-perf/01-app-memory-analysis-cases.md"
LEAK_TARGET = ROOT / "src/part5-app/ch23-memory-practice/01-memory-leak-governance.md"
MAP_PATH = ROOT / "metadata/2026-08-24-editorial-fusion-v11-map.json"

REINDEX = [
    (
        ROOT / "src/part2-performance/ch10-memory-perf/03-low-memory-impact.md",
        ROOT / "src/part2-performance/ch10-memory-perf/02-low-memory-impact.md",
        "10.3",
        "10.2",
    ),
    (
        ROOT / "src/part2-performance/ch10-memory-perf/04-memory-churn.md",
        ROOT / "src/part2-performance/ch10-memory-perf/03-memory-churn.md",
        "10.4",
        "10.3",
    ),
    (
        ROOT / "src/part2-performance/ch10-memory-perf/05-gpu-graphics-memory-tracking.md",
        ROOT / "src/part2-performance/ch10-memory-perf/04-gpu-graphics-memory-tracking.md",
        "10.5",
        "10.4",
    ),
]

LEAK_RELATED_OWNERS = {
    ROOT / "src/part1-fundamentals/ch04-memory/06-finalizer-referencequeue.md",
    ROOT / "src/part3-tools/ch14-other-tools/03-memory-hprof-heapdump-tools.md",
}
GROWTH_RELATED_OWNERS = {
    ROOT / "src/part5-app/ch23-memory-practice/07-ondevice-llm-memory-management.md",
    ROOT / "src/part5-app/ch25-power-size/07-hybrid-webview-power.md",
    ROOT / "src/part5-app/ch26-observability/14-heapprofd-procfs-page-fault.md",
}


GROWTH_SECTION = r"""
### 6.2 用回落条件区分缓存、积压与泄漏

持续增长实验要比普通峰值测试多两个采样点：执行业务释放动作后的状态，以及主动收缩可重建资源后的状态。随后用同一输入再跑一轮，观察波峰、波谷和增长斜率是否重复。只在峰值抓一次 `dumpsys meminfo`，无法区分工作集扩大、缓存保留和生命周期错误。

| 增长来源 | 释放或收缩动作 | 仍需补充的证据 |
| --- | --- | --- |
| 业务 live set（仍在使用的数据集合） | 关闭页面、清空数据集或结束会话 | 对象类型、条目数、字节预算与业务容量是否同步变化 |
| 无上限缓存或队列积压 | 执行缓存裁剪、消费完队列或取消任务 | 缓存 owner、队列长度、命中收益和积压产生速度 |
| Java/Kotlin 对象泄漏 | 结束对象的业务生命周期并等待异步清理 | heap dump 中稳定存在的 GC Root 强引用路径，详见 23.1 |
| Native 未释放分配 | 关闭会话或执行配对释放 | heapprofd 的 live allocation 差分与符号化调用栈 |
| allocator 保留 | 确认 live allocation 已下降 | allocator 统计、`smaps` 与匿名驻留页；RSS 不立即回落不能单独命名为泄漏 |
| 直接 `mmap`、文件页或线程栈 | 关闭映射、结束线程并再次采样 | mapping 名称、创建者、线程数量和退出条件 |
| Surface、Image、Codec 或 DMA-BUF | 关闭资源并等待 consumer 释放引用 | 图形内存、layer/buffer 生命周期与相关进程的变化 |
| WebView 工作集 | 销毁实例并分别观察宿主与 renderer 进程 | provider 版本、renderer 生命周期、代码页、缓存与图形内存 |

缓存需要一份可执行协议，而不是“内存高时清一点”的约定。至少记录五项：任何输入下都不能超过的 hard limit（硬上限）、页面不可见或进入后台后的 shrink target（收缩目标）、统一计量单位、负责创建和裁剪的 owner，以及 size/hit/miss/eviction/rebuild cost（大小、命中、未命中、淘汰和重建成本）。`ActivityManager.getMemoryClass()` 只描述 ART 堆的近似上限，不能直接拿来当整个进程的缓存预算。

`LruCache.sizeOf()` 决定预算单位，`maxSize` 必须使用相同单位。条目离开 `LruCache` 后，Adapter、View、任务或其他集合仍可能保存引用；缓存计数下降不等于对象已经回收。`entryRemoved()` 也不是通用的 Bitmap `recycle()` 开关，只有所有权协议能证明没有其他使用者时，才可在淘汰回调中主动销毁资源。

长时间运行的音乐、导航、IM、RTC 等场景还要把运行时长纳入基线。环形缓冲区、历史数据、图片、地图瓦片、字幕和模型缓存分别设上限；音视频会话中的 Codec、Surface、Image 和原生 session 由同一个持有者成对关闭。每轮业务结束后比较 live set，而不是只看进程是否仍能运行。
""".strip()


ROOT_TABLE = r"""
ART 从 GC Root 出发遍历引用图。只要对象仍能通过强引用路径到达，GC 就不能回收它。排查时应按分析器报告的 Root 类型阅读完整路径：

| Root 类别 | 常见来源 | 排查重点 |
| --- | --- | --- |
| 活跃线程栈与 JNI local reference（JNI 局部引用） | 正在执行的方法、原生调用帧 | 长任务、阻塞调用或未结束协程捕获了什么 |
| 活跃线程与线程局部变量 | `Thread`、`ThreadLocal` | 线程是否应退出，线程局部状态是否清理 |
| System class / boot class（系统类或启动类） | 已加载类及其静态字段 | 静态集合、单例与 SDK 注册表 |
| JNI global reference（JNI 全局引用） | `NewGlobalRef()` | 是否存在配对的 `DeleteGlobalRef()` 与明确持有者 |
| VM internal / monitor（运行时内部结构或监视器） | 虚拟机内部对象、锁相关结构 | 结合 Root 类型、引用边与对象生命周期判断 |

静态字段通常位于“类对象 → static field → 业务对象”的路径上。把每个 static 字段都叫作独立 GC Root，会省略类对象这一层，也容易把合法进程级状态误判成泄漏。
""".strip()


RESOURCE_SECTION = r"""
### 2.8 JNI 引用与显式关闭资源

原生代码通过 `NewGlobalRef()` 创建的引用会让 Java 对象跨调用持续可达。每条成功创建的 global reference 都要有明确持有者，并在会话结束、模块卸载或原生对象析构时调用 `DeleteGlobalRef()`。local reference 只在当前原生方法调用范围内有效，不能保存到调用结束以后；跨线程或跨调用时要区分 local、global 与 weak global reference（局部、全局与弱全局引用）。

`Cursor`、`ParcelFileDescriptor`、`MediaCodec`、`Image`、`Surface` 等对象还带有显式关闭协议。Java wrapper（包装对象）可能很小，背后却连接着原生分配、图形缓冲区或内核对象。持有者应通过 `use`、try-with-resources 或对应的 `close()` 在业务生命周期终点释放；finalizer 或 Cleaner 只能作为延迟兜底，不能保证资源及时归还。
""".strip()


HEAP_DUMP_SECTION = r"""

命令行排查 debuggable 进程时，也可以让 ActivityManager 生成完整 HPROF：

```bash
adb shell am dumpheap com.example.app /data/local/tmp/example.hprof
adb pull /data/local/tmp/example.hprof
```

heap dump 会暂停或扰动目标进程，文件还可能包含账号、页面文本与业务对象。采集、保存、上传和删除都要遵守调试数据的访问控制；生产设备不应把全量 HPROF 当作常规定时监控数据。
""".strip()


LEAK_REPORT_SECTION = r"""

阅读一条 LeakCanary 报告时，先确认 `╰→` 指向的对象是否已经越过业务生命周期，再从 GC Root 沿 `↓` 阅读强引用路径。`~~~` 标出的是分析器认为可疑的引用边，修复点仍要回到注册、缓存、任务或 JNI 代码中的实际 owner。

retained size 要和 dominator（支配）关系一起看。它估算某对象不可达后可随之释放的内存，不能单独证明对象已经泄漏。leak signature（泄漏签名）根据可疑路径归组，适合统计同类缺陷；Shark 展示的是便于诊断的一条路径，对象仍可能存在其他到 Root 的路径，修复后必须重新抓取验证。

`Library Leak` 表示路径匹配已知库或 Framework 模式，不等于可以忽略。应核对依赖版本和上游修复，评估发生频率与 retained bytes；应用侧无法消除时，仍要记录受影响版本、规避方案和验收条件。
""".rstrip()


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one marker, found {count}")
    return text.replace(old, new, 1)


def build_growth_target(text: str) -> str:
    source_marker = (
        "- type: aosp\n"
        "  path: frameworks/base/core/java/android/content/ComponentCallbacks2.java\n"
    )
    source_addition = (
        "- type: aosp\n"
        "  path: frameworks/base/core/java/android/util/LruCache.java@android-17.0.0_r1\n"
        "- type: official\n"
        "  path: https://developer.android.com/reference/android/util/LruCache\n"
    )
    text = replace_once(text, source_marker, source_marker + source_addition, "growth sources")
    provenance = "- src/part2-performance/ch10-memory-perf/05-case-studies.md\n"
    text = replace_once(
        text,
        provenance,
        provenance
        + "- src/part2-performance/ch10-memory-perf/02-memory-leak-growth.md\n"
        + "- src/part2-performance/ch10-memory-perf/03-memory-growth.md\n",
        "growth provenance",
    )
    marker = "### 7. 系统内存压力与 LMKD"
    text = replace_once(text, marker, GROWTH_SECTION + "\n\n" + marker, "growth section")
    return text


def build_leak_target(text: str) -> str:
    text = replace_once(
        text,
        "applicable_versions: Android 15 (API 35) - Android 17 (API 37)",
        "applicable_versions: Android 8.0 (API 26) - Android 17 (API 37); ProfilingManager-specific sections require API 35/37 as noted",
        "leak applicable versions",
    )
    text = replace_once(
        text,
        "last_verified_against: Android 17 / API 37 / AOSP android-17.0.0_r1；Android ProfilingManager、MemoryLimiter 与 ApplicationExitInfo 官方文档；LeakCanary 文档；KOOM 仓库与 release；Perfetto heapprofd 文档",
        "last_verified_against: Android 17 / API 37 / AOSP android-17.0.0_r1；Android ProfilingManager、MemoryLimiter 与 ApplicationExitInfo 官方文档；LeakCanary 2.14 与 Shark 文档；KOOM 仓库与 release；Perfetto heapprofd 文档",
        "leak verification provenance",
    )
    leakcanary_source = (
        "- type: reference\n"
        "  path: https://square.github.io/leakcanary/fundamentals-how-leakcanary-works/\n"
    )
    leakcanary_additions = (
        "- type: reference\n"
        "  path: https://square.github.io/leakcanary/fundamentals-fixing-a-memory-leak/\n"
        "- type: reference\n"
        "  path: https://square.github.io/leakcanary/shark/\n"
    )
    text = replace_once(
        text,
        leakcanary_source,
        leakcanary_source + leakcanary_additions,
        "LeakCanary sources",
    )
    provenance = "- src/part5-app/ch23-memory-practice/23.25-android-17-memory-leak-monitoring-framework.md\n"
    text = replace_once(
        text,
        provenance,
        provenance
        + "- src/part2-performance/ch10-memory-perf/02-memory-leak-growth.md\n"
        + "- src/part2-performance/ch10-memory-perf/02-memory-leak.md\n",
        "leak provenance",
    )
    old_roots = (
        "ART 从 GC Root 出发遍历引用图。只要对象仍能通过强引用路径到达，GC 就不能回收它。常见 Root 包括：\n\n"
        "- 活跃线程的栈和 JNI local reference（本次原生方法调用范围内的局部引用）；\n"
        "- Java 静态字段；\n"
        "- JNI global reference（跨原生方法调用持续存在的全局引用）；\n"
        "- 运行时内部持有的对象。"
    )
    text = replace_once(text, old_roots, ROOT_TABLE, "GC Root table")
    case_marker = "### 2.8 案例：常驻 Activity 如何保留已关闭弹窗"
    text = replace_once(
        text,
        case_marker,
        RESOURCE_SECTION + "\n\n### 2.9 案例：常驻 Activity 如何保留已关闭弹窗",
        "resource lifecycle section",
    )
    native_marker = "### 3.4 原生增长要看分配调用栈"
    text = replace_once(
        text,
        native_marker,
        HEAP_DUMP_SECTION + "\n\n" + native_marker,
        "heap dump command and privacy",
    )
    report_marker = "5. 相同可疑引用路径按 signature（路径特征签名）归组。"
    text = replace_once(
        text,
        report_marker,
        report_marker + LEAK_REPORT_SECTION,
        "LeakCanary report reading",
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
        placeholder = f"__AIW_HISTORICAL_MEMORY_PATH_{index}__"
        protected = protected.replace(value, placeholder)
        restored[placeholder] = value
    return text[: match.start()] + protected + text[match.end() :], restored


def remap_related(path: Path, text: str) -> str:
    match = re.search(r"(?m)^related_chapters:\n((?:- .*\n)+)", text)
    if not match:
        return text
    output: list[str] = []
    seen: set[str] = set()
    for line in match.group(1).splitlines():
        value_match = re.fullmatch(r"- ['\"](\d+\.\d+)['\"]", line.strip())
        if not value_match:
            rewritten = line
        else:
            value = value_match.group(1)
            replacement: str | None = value
            if value == "10.2":
                if path == GROWTH_TARGET:
                    replacement = None
                elif path in LEAK_RELATED_OWNERS:
                    replacement = "23.1"
                elif path in GROWTH_RELATED_OWNERS:
                    replacement = "10.1"
                else:
                    replacement = "23.1"
            elif value == "10.3":
                replacement = "10.2"
            elif value == "10.4":
                replacement = "10.3"
            elif value == "10.5":
                replacement = "10.4"
            if replacement is None:
                continue
            rewritten = f"- '{replacement}'"
        if rewritten in seen:
            continue
        seen.add(rewritten)
        output.append(rewritten)
    block = "\n".join(output) + "\n"
    return text[: match.start(1)] + block + text[match.end(1) :]


def update_references(path: Path, text: str) -> str:
    if path == ROOT / "src/SUMMARY.md":
        text = text.replace(
            "  - [10.2 内存泄漏与持续增长](part2-performance/ch10-memory-perf/02-memory-leak-growth.md)\n",
            "",
        )
    if path == ROOT / "src/part2-performance/ch10-memory-perf/README.md":
        text = text.replace("- [10.2 内存泄漏与持续增长](02-memory-leak-growth.md)\n", "")

    historical = [str(SOURCE.relative_to(ROOT))]
    historical += [str(old.relative_to(ROOT)) for old, _, _, _ in REINDEX]
    text, placeholders = protect_consolidated_paths(text, historical)

    text = text.replace(relpath(SOURCE, path), relpath(LEAK_TARGET, path))
    text = text.replace(str(SOURCE.relative_to(ROOT)), str(LEAK_TARGET.relative_to(ROOT)))
    for old, new, _, _ in REINDEX:
        text = text.replace(relpath(old, path), relpath(new, path))
        text = text.replace(str(old.relative_to(ROOT)), str(new.relative_to(ROOT)))

    for placeholder, value in placeholders.items():
        text = text.replace(placeholder, value)

    text = remap_related(path, text)

    prose = {
        "10.1-10.5（内存性能）": "10.1-10.4（内存性能）",
        "§10.2 讨论泄漏模型": "§23.1 讨论泄漏模型",
        "§10.5 讨论应用与图形内存症状": "§10.4 讨论应用与图形内存症状",
        "内存持续增长见 10.2 节": "内存持续增长的分类诊断见 10.1 节",
        "GPU 专项工具与 layer/buffer 追踪见 10.5 节": "GPU 专项工具与 layer/buffer 追踪见 10.4 节",
        "**10.2 内存泄漏分析**": "**23.1 内存泄漏检测与治理**",
        "**10.2 内存泄漏**": "**23.1 内存泄漏检测与治理**",
        "**10.2 内存持续增长**": "**10.1 内存增长分类诊断**",
        "**10.3 低内存": "**10.2 低内存",
        "**10.4 内存抖动": "**10.3 内存抖动",
        "**10.5 GPU": "**10.4 GPU",
        "[10.4 内存抖动与频繁 GC]": "[10.3 内存抖动与频繁 GC]",
        "[§10.4 内存抖动与频繁 GC]": "[§10.3 内存抖动与频繁 GC]",
        "[§10.5 GPU 与图形内存统计]": "[§10.4 GPU 与图形内存统计]",
        "[10.3 低内存对系统性能的影响]": "[10.2 低内存对系统性能的影响]",
        "[10.5 GPU 与图形内存统计]": "[10.4 GPU 与图形内存统计]",
    }
    for old, new in prose.items():
        text = text.replace(old, new)

    if path == ROOT / "src/part2-performance/ch10-memory-perf/README.md":
        text = text.replace(
            "| 页面退出后 Activity、View、callback 或资源仍被持有 | [10.2 内存泄漏与持续增长](../../part5-app/ch23-memory-practice/01-memory-leak-governance.md) |",
            "| 页面退出后 Activity、View、callback 或资源仍被持有 | [23.1 内存泄漏检测与治理](../../part5-app/ch23-memory-practice/01-memory-leak-governance.md) |",
        )
        text = text.replace(
            "| 多轮业务操作后内存持续增长 | [10.2 内存泄漏与持续增长](../../part5-app/ch23-memory-practice/01-memory-leak-governance.md) |",
            "| 多轮业务操作后内存持续增长 | [10.1 App 内存分析与案例](01-app-memory-analysis-cases.md) |",
        )
    if path == ROOT / "src/preface/reading-paths.md":
        text = text.replace(
            "| 内存持续增长 | 10.1 → 10.2 → 23.1 → 23.6 |",
            "| 内存持续增长 | 10.1 → 23.1 → 23.6 |",
        )
    if path == GROWTH_TARGET:
        text = text.replace(
            "- **10.1 App 内存分析**：内存域分类、`dumpsys meminfo`、smaps、Perfetto 与 heapprofd。\n- **23.1 内存泄漏检测与治理**：引用所有权、GC Root 与生命周期修复。\n- **10.1 内存增长分类诊断**：泄漏、缓存、pool 和地址空间增长的区分。",
            "- **10.1 本文**：内存域分类、基线、持续增长、`dumpsys meminfo`、smaps、Perfetto 与 heapprofd。\n- **23.1 内存泄漏检测与治理**：引用所有权、GC Root 与生命周期修复。",
        )
    return text


def h2_inventory(text: str) -> list[str]:
    return [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]


def validate(changed: dict[Path, str]) -> None:
    growth_needles = [
        "### 6.2 用回落条件区分缓存、积压与泄漏",
        "hard limit（硬上限）",
        "`LruCache.sizeOf()`",
        "长时间运行的音乐、导航、IM、RTC",
    ]
    leak_needles = [
        "System class / boot class",
        "### 2.8 JNI 引用与显式关闭资源",
        "adb shell am dumpheap",
        "leak signature（泄漏签名）",
        "`Library Leak`",
    ]
    missing = [needle for needle in growth_needles if needle not in changed[GROWTH_TARGET]]
    missing += [needle for needle in leak_needles if needle not in changed[LEAK_TARGET]]
    if missing:
        raise RuntimeError(f"missing fused memory concepts: {missing}")

    for _, new, _, new_number in REINDEX:
        body = changed[new]
        if f"chapter: '{new_number}'" not in body or f"section: '{new_number}'" not in body:
            raise RuntimeError(f"bad chapter reindex in {new}")

    for path, body in changed.items():
        if path.suffix != ".md":
            continue
        if "](02-memory-leak-growth.md)" in body or "/02-memory-leak-growth.md)" in body:
            raise RuntimeError(f"live link still points to removed source: {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    required = [SOURCE, GROWTH_TARGET, LEAK_TARGET, *[row[0] for row in REINDEX]]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"Expected predecessor files are missing: {missing}")
    collisions = [row[1] for row in REINDEX if row[1].exists()]
    if collisions:
        raise SystemExit(f"Reindex destinations already exist: {collisions}")

    originals = {path: path.read_text(encoding="utf-8") for path in required}
    changed: dict[Path, str] = {
        GROWTH_TARGET: build_growth_target(originals[GROWTH_TARGET]),
        LEAK_TARGET: build_leak_target(originals[LEAK_TARGET]),
    }
    for old, new, old_number, new_number in REINDEX:
        body = originals[old]
        body = replace_once(
            body,
            f"chapter: '{old_number}'",
            f"chapter: '{new_number}'",
            f"{old.name} chapter",
        )
        body = replace_once(
            body,
            f"section: '{old_number}'",
            f"section: '{new_number}'",
            f"{old.name} section",
        )
        changed[new] = body

    skip = {SOURCE, GROWTH_TARGET, LEAK_TARGET, *[row[0] for row in REINDEX]}
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
        "version": 11,
        "operation": "memory_leak_growth_distributed_editorial_fusion",
        "count_change": {"before": 279, "after": 278},
        "merged_paths": [
            {
                "source": str(SOURCE.relative_to(ROOT)),
                "target": str(LEAK_TARGET.relative_to(ROOT)),
                "role": "leak_proof_reference_path_and_lifecycle_owner",
            },
            {
                "source": str(SOURCE.relative_to(ROOT)),
                "target": str(GROWTH_TARGET.relative_to(ROOT)),
                "role": "memory_domain_baseline_and_non_leak_growth_owner",
            },
        ],
        "rewritten_paths": [
            str(GROWTH_TARGET.relative_to(ROOT)),
            str(LEAK_TARGET.relative_to(ROOT)),
        ],
        "reindexed_paths": [
            {"from": str(old.relative_to(ROOT)), "to": str(new.relative_to(ROOT))}
            for old, new, _, _ in REINDEX
        ],
        "source_bytes": {
            str(path.relative_to(ROOT)): len(body.encode("utf-8"))
            for path, body in originals.items()
        },
        "result_bytes": {
            str(path.relative_to(ROOT)): len(changed[path].encode("utf-8"))
            for path in (GROWTH_TARGET, LEAK_TARGET)
        },
        "source_sha256": {
            str(path.relative_to(ROOT)): digest(body) for path, body in originals.items()
        },
        "result_sha256": {
            str(path.relative_to(ROOT)): digest(changed[path])
            for path in (GROWTH_TARGET, LEAK_TARGET)
        },
        "source_h2_inventory": h2_inventory(originals[SOURCE]),
        "content_routes": [
            {
                "source": "10.2 leak definition, GC roots and retained-object proof",
                "destination": "23.1 definition and evidence-chain sections",
                "treatment": "unique_root_taxonomy_embedded; duplicate_definition_deduplicated",
            },
            {
                "source": "10.2 lifecycle mistakes, JNI references and closeable resources",
                "destination": "23.1 Android leak paths",
                "treatment": "unique_JNI_and_explicit_resource_ownership_embedded; duplicate_UI_examples_deduplicated",
            },
            {
                "source": "10.2 heap dump and LeakCanary report interpretation",
                "destination": "23.1 evidence chain and LeakCanary",
                "treatment": "unique_command_privacy_signature_dominator_and_library_leak_semantics_embedded",
            },
            {
                "source": "10.2 native leak tools and ProfilingManager",
                "destination": "23.1 existing native boundary and Android 17 capture sections; 20.13 and 23.3 specialist owners",
                "treatment": "duplicate_overview_deduplicated_against_deeper_existing_owners",
            },
            {
                "source": "10.2 cache, backlog and non-leak growth",
                "destination": "10.1 baseline and growth classification",
                "treatment": "unique_recovery_experiment_resource_matrix_and_cache_contract_embedded",
            },
            {
                "source": "10.2 Bitmap, allocator, physical fragmentation, mmap, graphics, WebView and MemoryLimiter detail",
                "destination": "10.1 routing overview plus existing 23.2, 23.3, 4.7, 10.4, 22.6 and 23.5 specialist owners",
                "treatment": "duplicate_specialist_exposition_deduplicated; diagnostic_boundaries_retained_in_10.1",
            },
            {
                "source": "10.2 version boundaries, checklists and references",
                "destination": "10.1 and 23.1 metadata, checklists and evidence lists",
                "treatment": "evidence_reconciled_and_duplicate_checklists_deduplicated",
            },
        ],
        "updated_reference_files": [
            str(path.relative_to(ROOT))
            for path in sorted(changed)
            if path not in {GROWTH_TARGET, LEAK_TARGET, *[row[1] for row in REINDEX]}
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
