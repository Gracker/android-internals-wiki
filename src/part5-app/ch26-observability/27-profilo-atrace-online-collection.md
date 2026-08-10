---
title: "Facebook Profilo 框架线上 ATrace 收集方案"
chapter: "26.27"
status: ready-for-review
drafted_date: "2026-07-16"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-16"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
tags: [Profilo, atrace, trace-marker, PLT-Hook, observability, Facebook, online-trace]
related_chapters: ["26.21", "26.23", "20.22", "20.24"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "参考书驱动（Clippings/线上疑难问题 46.md）"
sources:
  - type: aosp
    path: "frameworks/native/cmds/atrace/atrace.cpp (android-17.0.0_r1)"
  - type: aosp
    path: "system/core/libcutils/trace-dev.cpp"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - Native Backtrace：Native 堆栈信息获取.md"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - Native Hook 全解析：Native 闯关入门秘籍.md"
  - type: research
    path: "Profilo GitHub: facebook/profilo"
---

# 26.27 Facebook Profilo 框架线上 ATrace 收集方案

## Android 17 的使用边界

[Profilo](https://github.com/facebookarchive/profilo) 的定位是从生产版本收集应用性能 trace。它的 provider、触发控制、内存映射环形缓冲区和异步写文件设计仍有参考价值，但上游在 2023 年进入归档状态，README 也明确说明 API 不稳定。上游没有 Android 17 / API 37 的维护承诺和验证记录。

需要分别处理两件事：

- 解释 Profilo 的 ATrace provider 到底拦截了什么、保存了什么；
- 给出 `android-17.0.0_r1` 下继续维护 fork 时必须验证的边界，以及新项目的替代路线。

“Android 8 到 Android 17 全面覆盖”“生产开销低于 1%”之类结论没有上游基准和 Android 17 测试支撑，不能作为上线依据。开销需要按设备、事件密度、provider 组合、buffer 大小和采样时长重新测量。

## Profilo 的组件职责

Profilo 不是单一的 ATrace hook。官方[架构文档](https://github.com/facebookarchive/profilo/blob/main/docs/architecture.md)把系统分为 TraceController、TraceProvider、配置和写入链路：

| 组件 | 源码中的职责 | 不负责的事情 |
|---|---|---|
| `TraceController` / 配置 | 判断一次 trigger 是否启动 trace，选择 provider 和参数 | 不自动决定业务采样策略 |
| `BaseTraceProvider` | 在 trace 开始和结束时启停一个数据源 | 不保证所有 Android 版本可用 |
| `MultiBufferLogger` | 把标准项和字符串写进一个或多个 buffer | 不直接等于 ftrace ring buffer |
| `MmapBufferManager` | 分配匿名或 file-backed buffer，登记进程与容量信息 | 不上传数据 |
| `TraceWriter` / `FileManager` | 从 buffer 生成 trace 文件并管理待处理文件 | 不内置通用加密与 HTTPS 后端 |

内存侧使用固定容量的并发环形缓冲区。源码 [`LockFreeRingBuffer.h`](https://github.com/facebookarchive/profilo/blob/main/cpp/logger/lfrb/LockFreeRingBuffer.h) 说明：writer 通常不等待 reader，reader 落后时可以发现数据已被覆盖；当 writer 绕回同一 slot 而前一次写入尚未完成时，writer 仍可能等待。用“完全无锁、永不阻塞”概括并不准确。

下面的关系图用于区分应用内 Profilo 数据与系统 trace 数据。

```text
业务 trigger / 远程配置
          │
          ▼
    TraceController
          │ 选择 provider
          ▼
 ┌───────────────────────────────┐
 │ 应用进程                      │
 │ ATrace provider ─┐            │
 │ stack provider ──┼─> logger ──┼─> mmap ring buffer
 │ counters ────────┘            │          │
 └───────────────────────────────┘          ▼
                                      TraceWriter
                                           │
                                           ▼
                                      应用私有文件

系统 Perfetto / ftrace 是另一条采集链路。
```

图中的上传、限额、脱敏和服务端分析需要接入方自行实现。不能从 Profilo 有 `upload` 文件目录推导出“默认会压缩、加密并上传”。

## Android 17 的 ATrace 写入链路

平台锚点为 AOSP `android-17.0.0_r1`。[`libcutils/trace-dev.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/libcutils/trace-dev.cpp) 初始化时优先打开 `/sys/kernel/tracing/trace_marker`，失败后再尝试 `/sys/kernel/debug/tracing/trace_marker`。[`trace-dev.inc`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/libcutils/trace-dev.inc) 保存 `atrace_marker_fd` 和 `atrace_enabled_tags`，并用 `write()` 写入格式化事件。

Android 17 的用户态格式已不止早期五种：

| 前缀 | 语义 | Profilo 上游 ATrace provider |
|---|---|---|
| `B` / `E` | 当前线程同步 slice 开始 / 结束 | 保存 |
| `S` / `F` | 异步事件开始 / 结束 | 忽略 |
| `G` / `H` | 指定 track 的可嵌套异步事件 | 忽略 |
| `I` / `N` | 进程或指定 track 的 instant event | 忽略 |
| `C` | counter | 忽略 |

[`android.os.Trace`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Trace.java) 的 JNI 在 Android 17 进入 [`tracing_perfetto`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/tracing_perfetto/tracing_perfetto.cpp)。它根据启用状态选择 ATrace 兼容路径或 Perfetto Track Event 路径。`Trace.beginSection()` 仍是公共的同步 slice API，名称最多 127 个 UTF-16 code unit，并要求在同一线程以正确嵌套顺序调用 `endSection()`。

下面的写法用于给稳定、低基数的业务阶段添加公共 trace 标记。

```kotlin
import android.os.Trace

inline fun <T> traceSection(name: String, block: () -> T): T {
    Trace.beginSection(name)
    return try {
        block()
    } finally {
        Trace.endSection()
    }
}

val result = traceSection("Feed.bindVisibleItems") {
    bindVisibleItems()
}
```

`finally` 保证异常路径也关闭 slice。线上事件名应使用固定名称，用户输入、URL、账号、订单号等高基数字段不要放进 section name；参数可在采样命中后由受控日志单独记录。

## Profilo ATrace provider 的精确行为

上游实现位于 [`cpp/atrace/Atrace.cpp`](https://github.com/facebookarchive/profilo/blob/main/cpp/atrace/Atrace.cpp) 和 [`SystraceProvider.java`](https://github.com/facebookarchive/profilo/blob/main/java/main/com/facebook/profilo/provider/atrace/SystraceProvider.java)。在 API 27 及更高版本，它的关键步骤是：

1. 用 `dlsym()` 查找进程中的私有实现变量 `atrace_enabled_tags` 和 `atrace_marker_fd`。
2. 在 `libcutils.so` 上安装 `__write_chk` 的 PLT hook。
3. provider 启用时把 `atrace_enabled_tags` 原子交换为 `UINT64_MAX`，并保存原值。
4. 写入目标 fd 且 provider 处于启用状态时，只解析 `B` 与 `E`，把线程 ID、单调时钟时间和名称写入 Profilo logger。
5. provider 停止时卸载 hook，并尝试恢复原 tag mask。

这一点与常见描述有明显差别：命中 hook 后，`write_hook()` 返回 `count`，不会调用原始 `write()`。事件被导向 Profilo buffer，没有同时写入内核 ftrace buffer。下面的伪代码只保留控制流，便于代码审计。

```c
ssize_t profilo_write_hook(int fd, const void* data, size_t size) {
    if (provider_enabled && fd == observed_atrace_fd && size > 0) {
        if (is_sync_begin_or_end(data, size)) {
            write_to_profilo_buffer(current_tid(), monotonic_time(), data, size);
        }
        return size; // 不再写入 trace_marker
    }
    return previous_write(fd, data, size);
}
```

返回成功但忽略 `S/F/G/H/I/N/C` 会让调用方以为事件已经记录，Profilo trace 中却没有相应数据。若业务依赖 async、counter、instant 或自定义 track，上游 provider 的数据模型不够用。

### 能看到哪些进程

PLT hook 只修改当前应用进程中目标库的调用入口。把 tag mask 设为全 1，会放行当前进程里 framework、ART、HWUI 或 native library 执行到的 ATrace 点；它不会进入 `system_server`、SurfaceFlinger、WindowManager 等其他进程，也不会采集 sched、binder、block I/O 等内核 tracepoint。

所以，Profilo ATrace trace 是“本进程同步 slice 的应用内副本”，不是一份完整 systrace。需要跨进程与内核因果关系时，仍要采集 Perfetto system trace。

### B/E 如何配对

Profilo 在 hook 执行时直接调用 `threadID()`，每条 `MARK_PUSH` / `MARK_POP` 已带 TID，不需要依赖 `sched_switch` 推断线程。解析端按 TID 维护栈即可恢复同步嵌套：

```text
tid 4101: PUSH Activity.onCreate
tid 4101:   PUSH inflateContent
tid 4101:   POP
tid 4101: POP

tid 4178: PUSH decodeThumbnail
tid 4178: POP
```

每个 TID 的 `PUSH` 与 `POP` 独立配对。环形 buffer 覆盖、trace 恰好从一个未结束 slice 中间开始、进程异常退出或调用方本身没有成对调用，都会留下不平衡栈。分析端应把对应区间标成不完整数据，不能凭空补出时长。

## ATrace provider 与 stack provider 不要混为一谈

Profilo 的堆栈采样是另一个 provider。上游 [`SamplingProfiler.cpp`](https://github.com/facebookarchive/profilo/blob/main/cpp/profiler/SamplingProfiler.cpp) 为目标线程建立 CPU-time 或 wall-time timer，以 profiler signal 触发 unwind；[`TimerManager.cpp`](https://github.com/facebookarchive/profilo/blob/main/cpp/profiler/TimerManager.cpp) 周期性扫描 `/proc` 线程列表并增删 timer。源码没有“Quicken 模式”，也没有通过 PLT hook `pthread_create` 建立线程清单。

Android 版本边界更严格：

- [`CPUProfiler.java`](https://github.com/facebookarchive/profilo/blob/main/java/main/com/facebook/profilo/provider/stacktrace/CPUProfiler.java) 中基于 ART 内部布局的 Java unwinder 只列到 Android 9；
- API 26 及更高版本会把 native tracer 标为候选，但这不等于上游二进制已经在 Android 17 验证；
- signal handler、ART/DEX/JIT unwind、native unwinder 与其他 SDK 的信号处理会互相影响，需要独立压力测试。

如果目标是 Android 17 Java 方法采样，不应直接复用 Profilo 的 Android 9 ART offset 表，也不应靠扫描 ART 私有内存寻找新偏移。使用 Android Studio CPU Profiler、Simpleperf、Perfetto 支持的数据源或经过版本验证的 JVMTI 方案更可控。

## Android 17 兼容性审计

Profilo 主分支最近一次提交和发布产物都早于 Android 17。源码审计只能指出依赖关系，不能代替真机验证。

| 能力 | Android 17 源码现状 | 结论 |
|---|---|---|
| `libcutils` ATrace 变量 | `atrace_enabled_tags`、`atrace_marker_fd` 仍存在于 `trace-dev.inc` | 存在不代表属于应用可依赖的稳定 ABI |
| Java `Trace` | JNI 经 `tracing_perfetto`，`isTagEnabled()` 不再读取旧 Java 缓存字段 | Profilo 的 `nativeGetEnabledTags` 反射代码已经过时 |
| PLT hook | 上游 API 27+ 固定 hook `libcutils.so::__write_chk` | 必须用 Android 17 构建产物和目标 OEM 镜像验证 relocation |
| ATrace 事件格式 | Android 17 支持 B/E/S/F/G/H/I/N/C | 上游只保存 B/E |
| Java stack sampling | 上游 ART unwinder 版本表截止 Android 9 | Android 17 不可按上游能力宣称支持 |
| 维护状态 | 官方仓库已归档 | 移植、安全修复和回归由采用方负责 |

旧文把 hidden API、SELinux、W^X 都写成 Android 17 已确认的阻断点，再给出扫描 `.bss` 的规避办法，证据不足且风险很高。风险来自对私有符号和具体 relocation 的依赖，任何平台或 OEM 构建变化都可能使 hook 失效。失败时应关闭 provider 并保留诊断信息，不应继续扫描或修改未知内存。

## 继续维护 Profilo fork 时的验证清单

### 固定源码与构建输入

记录 fork 基于的 commit、所有 native 依赖、NDK 版本、ABI、编译器选项和符号化文件。上游 README 明确说 API 不稳定，直接使用未固定版本的 AAR 会让 trace schema 和 native 行为难以追溯。

### 把 provider 安装结果纳入能力协商

`installSystraceHook()` 返回失败时，不启动 ATrace provider；其他 provider 是否继续由配置决定。需要记录失败阶段，例如私有符号未找到、PLT hook 安装失败或 buffer 分配失败。不要向后端上传一份被标成完整、内容却为空的 trace。

### 做事件语义测试

至少覆盖以下用例：

- 同线程嵌套 B/E，确认名称、TID、时间顺序和深度；
- 两个线程同时写入，确认各自栈互不干扰；
- async、counter、instant 和 track 事件，明确是补充实现还是声明不支持；
- trace 开始前已有未结束 section、buffer wrap、异常退出和 provider 重入；
- 启停后 `atrace_enabled_tags` 恢复，并验证并发 Perfetto capture 没有受到破坏；
- `android.os.Trace`、NDK ATrace 和直接使用 Perfetto SDK 的事件分别测试，不能假设它们必经同一 PLT 入口。

### 用上游工具检查文件

Profilo 官方 [`trace-processing` 文档](https://github.com/facebookarchive/profilo/blob/main/docs/trace-processing.md)提供了从应用私有目录拉取最近 trace 的工具。下面的命令用于开发环境验证文件可以被解析，不代表线上上传流程。

```shell
cd python
python3 -m profilo.profilo pull_traces \
  --last com.facebook.profilo.sample
python3 -m profilo.workflow_demo --help
```

成功拉取后，还要检查 provider 注解、事件数量、首尾时间、丢失记录和 buffer 覆盖情况。只验证“文件存在”无法证明 hook 捕获完整。

### 建立本项目的开销预算

不要沿用固定的微秒或百分比。至少测量：

- provider 关闭、只开 ATrace、只开 stack、组合开启四组；
- 冷启动、滚动、动画、后台恢复和空闲五类场景；
- CPU time、帧时长、分配、RSS、功耗、trace 字节数、buffer overwrite；
- 低端与高端设备、4 KB 与 16 KB page-size 设备；
- P50/P95/P99 以及未开启采集的对照组。

事件密度比“是否使用系统调用”更能决定干扰程度。Profilo 命中 hook 时省去了 trace-marker 写入，却增加了解析、时间戳、TID 获取和 buffer 写入；具体差值只能由目标构建测得。

## Android 17 新项目的选择

### 只需要公共业务标记

Java/Kotlin 使用 `android.os.Trace` 或 AndroidX Tracing，native 使用 NDK ATrace。它们适合把业务阶段放进 Perfetto system trace，API 边界比私有变量和 PLT hook 稳定。

### 需要线上应用内 trace

[AndroidX Tracing 的 in-process tracing](https://developer.android.com/topic/performance/tracing/in-process-tracing) 或 [Perfetto Tracing SDK 的 in-process backend](https://perfetto.dev/docs/instrumentation/tracing-sdk) 可以让应用控制自身 trace session，并输出 Perfetto 格式。in-process 数据只包含应用注册的数据源，不会自动包含调度器和其他系统进程；这与线上采集的权限和隐私边界更一致。

选择这条路线时仍需实现采样、限额、脱敏、加密、上传和服务端保留策略。Perfetto 格式解决数据模型与工具兼容问题，不会替应用决定哪些用户、哪些场景可以采集。

### 需要系统级因果分析

Android 10 及更高版本优先使用 Perfetto system trace。它能在一条时间线上组合应用 trace、sched、binder、频率、内存和 I/O 等数据。系统模式的 trace 读取受到权限控制；普通线上应用不应尝试绕过该边界。

## 工程决策

| 现状 | 建议 |
|---|---|
| 已有维护多年的 Profilo fork 和配套后端 | 保留架构，按 Android 17 清单重新验证；把 ATrace B/E 子集和失效条件写进协议 |
| 只想复用上游 AAR 快速上线 | 不建议；仓库已归档，Android 17 与 OEM 兼容性没有维护方保证 |
| 新建应用内线上 trace | 评估 AndroidX Tracing 2.x 或 Perfetto SDK in-process backend |
| 线下或实验室定位跨进程问题 | 使用 Perfetto system trace，不用 Profilo trace 代替系统时间线 |
| 只需持续指标与异常触发 | 优先做聚合指标和短窗口触发，命中后再采集受控 trace |

Profilo 值得借鉴的是 provider 化、触发控制、固定容量 buffer 和异步文件处理。Android 17 上不应照搬的是对 `libcutils` 私有变量、特定 PLT relocation 和旧 ART 布局的依赖。
