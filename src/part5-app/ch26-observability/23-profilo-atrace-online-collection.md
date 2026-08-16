---
title: "Facebook Profilo 框架线上 ATrace 收集方案"
chapter: "26.23"
section: "26.23"
status: finalized
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-08-16"
last_source_verified_at: "2026-08-16"
last_verified_against: "Profilo main at 5a66b937; AOSP android-17.0.0_r1; current Android and Perfetto docs retrieved 2026-08-16"
confidence: high
tags: [Profilo, atrace, trace-marker, PLT-Hook, observability, Facebook, online-trace]
related_chapters: ["13.16", "13.20", "14.11", "20.17", "26.22", "26.25"]
sources:
  - type: legacy-reference-preserved
    path: "frameworks/native/cmds/atrace/atrace.cpp (android-17.0.0_r1)"
  - type: legacy-reference-preserved
    path: "system/core/libcutils/trace-dev.cpp"
  - type: legacy-reference-preserved
    path: "Clippings/Android 应用稳定性剖析与优化 - Native Backtrace：Native 堆栈信息获取.md"
  - type: legacy-reference-preserved
    path: "Clippings/Android 应用稳定性剖析与优化 - Native Hook 全解析：Native 闯关入门秘籍.md"
  - type: legacy-reference-preserved
    path: "Profilo GitHub: facebook/profilo"
  - type: source
    path: "https://github.com/facebookarchive/profilo"
    note: "Archived repository; latest main commit and release are dated 2023-02-24"
  - type: source
    path: "https://github.com/facebookarchive/profilo/blob/main/README.md"
  - type: source
    path: "https://github.com/facebookarchive/profilo/blob/main/docs/architecture.md"
  - type: source
    path: "https://github.com/facebookarchive/profilo/blob/main/cpp/logger/lfrb/LockFreeRingBuffer.h"
  - type: source
    path: "https://github.com/facebookarchive/profilo/blob/main/cpp/atrace/Atrace.cpp"
  - type: source
    path: "https://github.com/facebookarchive/profilo/blob/main/java/main/com/facebook/profilo/provider/atrace/Atrace.java"
  - type: source
    path: "https://github.com/facebookarchive/profilo/blob/main/java/main/com/facebook/profilo/provider/atrace/SystraceProvider.java"
  - type: source
    path: "https://github.com/facebookarchive/profilo/blob/main/cpp/profiler/SamplingProfiler.cpp"
  - type: source
    path: "https://github.com/facebookarchive/profilo/blob/main/cpp/profiler/TimerManager.cpp"
  - type: source
    path: "https://github.com/facebookarchive/profilo/blob/main/java/main/com/facebook/profilo/provider/stacktrace/CPUProfiler.java"
  - type: source
    path: "https://github.com/facebookarchive/profilo/blob/main/docs/trace-processing.md"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/libcutils/trace-dev.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/libcutils/trace-dev.inc"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/libcutils/include/cutils/trace.h"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Trace.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/tracing_perfetto/tracing_perfetto.cpp"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/tracing"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/in-process-tracing"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingManager"
  - type: official
    path: "https://perfetto.dev/docs/instrumentation/tracing-sdk"
  - type: official
    path: "https://perfetto.dev/docs/getting-started/atrace"
---

# 26.23 Facebook Profilo 框架线上 ATrace 收集方案

## Android 17 的使用边界

[Profilo](https://github.com/facebookarchive/profilo) 是 Meta（原 Facebook）开源的 Android 性能追踪库，目标是从应用的生产构建中采集性能 trace。trace 是一段时间内带时间戳的事件记录，可用来还原线程执行、方法区间与系统活动之间的先后关系。

Profilo 把一次采集分成可按需启停的数据采集器（源码称 provider），由触发请求（trigger）决定是否启动，并先把事件写入固定容量的内存映射环形缓冲区。环形缓冲区写满后会循环复用旧槽位，内存映射则让进程通过虚拟地址访问匿名内存或文件。这些设计仍有参考价值。

仓库 README 在 2023 年宣布进入维护模式，并计划于 2023-05-01 完全归档；GitHub 元数据现已标记为 archived。主分支最近提交和最近 release 均为 2023-02-24，README 还明确声明 API 尚不稳定。上游没有 Android 17 / API 37 的维护承诺或验证记录。

继续维护 `fork` 时，`fork` 指从上游复制后自行演进的下游仓库。需要先回答两个问题：ATrace provider 捕获了哪些事件；它在 `android-17.0.0_r1` 和目标厂商镜像上还能否按预期工作。

“Android 8 到 Android 17 全面覆盖”“生产开销低于 1%”等结论缺少上游基准和 Android 17 测试支撑，不能用作上线依据。开销必须按目标设备、事件密度、provider 组合、缓冲区容量和采样时长重新测量。

## Profilo 的组件职责

Profilo 包含多个协作组件。官方[架构文档](https://github.com/facebookarchive/profilo/blob/main/docs/architecture.md)对 trace、trigger、`TraceController` 和 `TraceProvider` 给出了定义：

| 组件 | 源码中的职责 | 不负责的事情 |
|---|---|---|
| `TraceController` / 配置 | 根据一次 trigger 和配置决定是否启动 trace，并选择 provider 与参数 | 不自动决定业务采样策略 |
| `BaseTraceProvider` | 在 trace 开始与结束时启停一种数据源 | 不承诺所有 Android 版本都可用 |
| `MultiBufferLogger` | 把标准记录和字符串写入一个或多个 Profilo 缓冲区 | 不等同于内核的 ftrace 环形缓冲区 |
| `MmapBufferManager` | 分配匿名缓冲区或映射到文件的缓冲区，并登记进程与容量 | 不负责上传 |
| `TraceWriter` / `FileManager` | 从缓冲区生成 trace 文件，并管理待处理文件 | 不内置通用加密或 HTTPS 服务端 |

内存侧使用固定容量的并发环形缓冲区。

并发语义见源码 [`LockFreeRingBuffer.h`](https://github.com/facebookarchive/profilo/blob/main/cpp/logger/lfrb/LockFreeRingBuffer.h)。

写线程通常不等待读线程，读线程落后时可以发现数据已经被覆盖。写线程绕回同一槽位，而该槽位的前一次写入尚未完成时，仍可能等待。“完全无锁、永不阻塞”会掩盖这个例外。

这张关系图区分应用内 Profilo 数据与系统 trace 数据：

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

图中的上传、限额、脱敏和服务端分析都需要接入方自行实现。Profilo 存在名为 `upload` 的文件目录，只能说明文件处于待处理阶段，无法据此推导出“默认会压缩、加密并上传”。

## Android 17 的 ATrace 写入路径

平台锚点为 AOSP `android-17.0.0_r1`。ATrace 是用户态埋点 API 与事件协议，ftrace 则是 Linux 内核的追踪设施；`trace_marker` 是用户态向 ftrace 提交文本事件的接口文件。

初始化代码见 [`libcutils/trace-dev.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/libcutils/trace-dev.cpp)。

它优先打开 `/sys/kernel/tracing/trace_marker`，失败后再尝试 `/sys/kernel/debug/tracing/trace_marker`。

状态定义见 [`trace-dev.inc`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/libcutils/trace-dev.inc)。

其中保存 `atrace_marker_fd` 与 `atrace_enabled_tags`，再用 `write()` 写入格式化事件。`fd` 是进程用来标识已打开文件的整数句柄，`atrace_marker_fd` 保存的就是该接口文件句柄。

Android 17 的用户态格式包含以下前缀：

| 前缀 | 语义 | Profilo 上游 ATrace provider |
|---|---|---|
| `B` / `E` | 当前线程同步 slice 开始 / 结束 | 保存 |
| `S` / `F` | 异步事件开始 / 结束 | 忽略 |
| `G` / `H` | 指定 track 的异步事件开始 / 结束 | 忽略 |
| `I` / `N` | 进程或指定 track 的 instant event | 忽略 |
| `C` | counter | 忽略 |

slice 是由开始与结束事件界定的持续区间。异步事件用名称和 cookie 配对，可以跨线程结束；track 是时间线中的独立轨道；instant event 只标记一个时刻；counter 记录随时间变化的数值。cookie 是调用方提供的配对标识，不含浏览器 cookie 的含义。

Java API 见 [`android.os.Trace`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Trace.java)。JNI 是 Java/Kotlin 调用 native C/C++ 实现的桥接接口。

它的 JNI 在 Android 17 进入 native tracing 实现。

[`tracing_perfetto`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/tracing_perfetto/tracing_perfetto.cpp) 按启用状态选择 ATrace 兼容路径或 Perfetto Track Event 路径。Track Event 是 Perfetto 表示 slice、instant 与 counter 等事件的结构化数据模型。

`Trace.beginSection()` 仍是公共同步 slice API，必须在同一线程按嵌套顺序调用 `endSection()`。

名称上限为 127 个 UTF-16 code unit。code unit 是 Java `String.length()` 使用的计数单位：常见基本平面字符占一个，部分 emoji 等补充字符由代理对表示，会占两个。竖线、换行和空字符会在 trace 中替换为空格。

这段写法适合给名称固定的业务阶段添加公共 trace 标记：

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

`finally` 保证异常路径也能关闭 slice。高基数指可能出现大量不同取值，例如 URL、账号与订单号；把这些值放进 section name 会增大 trace 体积，还可能暴露敏感信息。线上事件名应保持固定，必要参数可在采样命中后由受控日志另行记录。

## Profilo ATrace provider 的精确行为

native 捕获逻辑位于 [`cpp/atrace/Atrace.cpp`](https://github.com/facebookarchive/profilo/blob/main/cpp/atrace/Atrace.cpp)。

Java 生命周期入口见 [`SystraceProvider.java`](https://github.com/facebookarchive/profilo/blob/main/java/main/com/facebook/profilo/provider/atrace/SystraceProvider.java)。

在 API 27 及更高版本，关键步骤如下：

1. 用 `dlsym()` 在已加载模块中按名字查找私有变量 `atrace_enabled_tags` 和 `atrace_marker_fd` 的地址。
2. 在 `libcutils.so` 上安装 `__write_chk` 的 PLT hook。PLT 是动态链接调用表，hook 会把该表中的目标函数入口改到 Profilo 的替代函数。
3. provider 启用时把 `atrace_enabled_tags` 原子交换为 `UINT64_MAX`，并保存原值。tag mask 是以位表示 ATrace 类别开关的掩码，全 1 表示放开所有类别位。
4. 写入目标 fd 且 provider 处于启用状态时，只解析 `B` 与 `E`，把线程 ID、单调时钟时间和名称写入 Profilo logger。单调时钟只向前计时，不随系统日期校准而回拨。
5. provider 停止时卸载 hook，并尝试恢复原 tag mask。

这里还有一项私有 ABI 假设。Android 17 的 `trace-dev.inc` 把 `atrace_enabled_tags` 定义为普通 `uint64_t`，Profilo 却把 `dlsym()` 返回的地址转换为 `std::atomic<uint64_t>*` 后执行 `exchange()` 与 `store()`。

私有 ABI 指源码未向应用承诺稳定的二进制布局和调用约定。符号在源码中仍存在，也不能证明这种类型与对齐假设在所有构建上安全。

命中 API 27+ 的 `__write_chk_hook()` 后，hook 直接返回 `count`，不再调用原始 `__write_chk()`。事件被转写到 Profilo 缓冲区，不会同时进入内核 ftrace 缓冲区。这段伪代码只保留该控制流：

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

hook 对 `S/F/G/H/I/N/C` 同样返回成功，却没有向 Profilo 写入对应记录。调用方因此无法从返回值发现丢失。业务若依赖异步事件、counter、instant event 或自定义 track，必须扩展记录格式与解析器，或者明确声明这些事件不受支持。

### 能看到哪些进程

PLT relocation 是动态加载器填入的函数地址槽位。Profilo 修改的是当前应用进程内 `libcutils.so` 的这个槽位，其他进程各有自己的地址空间，不会随之改变。

把 tag mask 设为全 1，只会放行当前进程内 framework、ART、HWUI 或 native library 执行到的 ATrace 点。它触达不了承载系统服务的 `system_server`、负责显示合成的 SurfaceFlinger 或窗口管理服务 WindowManager。

它也不会记录 `sched`、Binder、块 I/O 等内核 tracepoint。tracepoint 是内核预先布置的事件观测点。

Profilo ATrace trace 因而只是一份“当前进程同步 slice 的应用内副本”。systrace 是 Android 早期系统追踪工具和格式的常用称呼；完整的系统时间线还需要跨进程事件与内核调度数据。涉及跨进程因果关系时，应采集 Perfetto system trace。

### B/E 如何配对

Profilo 在 hook 执行时直接调用 `threadID()`。TID 是内核分配给线程的标识；Profilo 把 `B` 转成 `MARK_PUSH`，把 `E` 转成 `MARK_POP`，并在每条记录中保存 TID。解析器按 TID 分别维护调用栈，无需借助 `sched_switch` 推断事件属于哪个线程：

```text
tid 4101: PUSH Activity.onCreate
tid 4101:   PUSH inflateContent
tid 4101:   POP
tid 4101: POP

tid 4178: PUSH decodeThumbnail
tid 4178: POP
```

每个 TID 的 `PUSH` 与 `POP` 独立配对。缓冲区回绕指写指针走完一圈后复用旧槽位；它可能覆盖尚未读取的开始事件。采集恰好从未结束 slice 的中间启动、进程异常退出或调用方漏掉配对调用，也会留下不平衡栈。分析端应把对应区间标为不完整数据，不能补造时长。

## ATrace provider 与 stack provider 不要混为一谈

Profilo 的堆栈采样由另一个 provider 完成，native 入口见 [`SamplingProfiler.cpp`](https://github.com/facebookarchive/profilo/blob/main/cpp/profiler/SamplingProfiler.cpp)。

它为目标线程建立 CPU-time 或 wall-time timer：前者只累计线程占用 CPU 的时间，后者按经过的现实时间计时。

timer 到期后发送 profiler signal，也就是由操作系统异步送达的采样信号。信号处理函数再执行 unwind，从当前寄存器和栈内存中恢复调用帧。

[`TimerManager.cpp`](https://github.com/facebookarchive/profilo/blob/main/cpp/profiler/TimerManager.cpp) 周期性扫描 `/proc` 暴露的线程列表，为新增线程创建 timer，并删除已经退出线程的 timer。

源码中找不到名为“Quicken”的采样模式，也没有通过 PLT hook `pthread_create` 来维护线程清单。

Android 版本边界更严格：

- [`CPUProfiler.java`](https://github.com/facebookarchive/profilo/blob/main/java/main/com/facebook/profilo/provider/stacktrace/CPUProfiler.java) 中基于 ART 内部布局的 Java unwinder 版本表只列到 Android 9；
- API 26 及更高版本会把 native tracer 加入候选集合，这只表示代码允许选择该实现，不代表上游二进制已在 Android 17 验证；
- signal handler、Java 与 native unwinder，以及其他 SDK 注册的信号处理函数可能互相影响，需要独立压力测试。

ART/DEX/JIT unwind 指跨越 ART 运行时、DEX 字节码和即时编译代码恢复 Java 调用帧。Profilo 的旧 Java unwinder 依赖特定版本的 ART 字段偏移；把 Android 9 的偏移表直接用于 Android 17，可能读到错误地址。

Android 17 的 Java 方法采样应优先选择 Android Studio CPU Profiler、Simpleperf 或 Perfetto 支持的数据源。API 35 及更高版本还可评估平台的 `ProfilingManager`。

JVMTI 是虚拟机提供的调试与插桩接口，attach 指运行中把 agent 加载进目标进程。Android 的 JVMTI attach 受可调试应用边界约束，普通生产构建不能把它当作默认入口。扫描 ART 私有内存寻找新偏移同样不适合生产方案。

## Android 17 兼容性审计

Profilo 主分支最近一次提交和 release 均为 2023-02-24，早于 Android 17。源码审计只能找出依赖，仍需在目标 APK、系统镜像与设备上验证。

| 能力 | Android 17 源码现状 | 结论 |
|---|---|---|
| `libcutils` ATrace 变量 | `atrace_enabled_tags`、`atrace_marker_fd` 仍存在；前者在平台侧是 `uint64_t` | Profilo 的原子指针转换属于私有 ABI 假设 |
| Java `Trace` | JNI 经 `tracing_perfetto`，`isTagEnabled()` 直接调用 native | Profilo 反射 `nativeGetEnabledTags` 与 `sEnabledTags` 的代码已经过时 |
| PLT hook | 上游 API 27+ 固定 hook `libcutils.so::__write_chk` | 必须用 Android 17 构建产物和目标 OEM 镜像验证 relocation |
| ATrace 事件格式 | Android 17 支持 B/E/S/F/G/H/I/N/C | 上游只保存 B/E |
| Java stack sampling | 上游 ART unwinder 版本表截止 Android 9 | Android 17 不可按上游能力宣称支持 |
| 维护状态 | 官方仓库已归档 | 移植、安全修复和回归由采用方负责 |

这里涉及的限制机制各不相同。hidden API 通常指 Android 对非 SDK Java 接口的访问限制；SELinux 用安全标签与策略控制进程可以访问的对象；W^X 要求内存页不能同时可写和可执行。

Profilo 的这段 ATrace 代码更直接地依赖 native 私有符号、变量布局和 PLT relocation。

OEM 在这里指基于 Android 生产设备与系统镜像的厂商。现有证据不足以断言 hidden API、SELinux 与 W^X 在所有 Android 17 设备上都会阻断该流程。

ELF 是 Android native 可执行文件与共享库常用的二进制格式，`.bss` 是其中保存未初始化全局变量的区域。扫描它来猜测私有变量地址可能误识别并修改无关内存，风险很高。hook 失败时应关闭 provider、记录失败阶段，并保持应用主流程可用。

## 继续维护 Profilo fork 时的验证清单

### 固定源码与构建输入

记录 fork 基于的 `commit`、所有 native 依赖、NDK 版本、ABI、编译器选项和符号文件。`commit` 是 Git 中唯一标识某次源码快照的哈希；NDK 是 Android 的 native 开发工具集；ABI 是应用与 native 库约定的二进制接口，例如 `arm64-v8a`。

AAR 是 Android 库的发布归档。上游 README 明确声明 API 不稳定，直接依赖未固定版本的 AAR，会让 trace schema 与 native 行为难以追溯。trace schema 指每种记录的字段、类型和编码约定；客户端、解析器与服务端必须使用兼容版本。

### 把 provider 安装结果纳入能力协商

能力协商是客户端在每次采集旁明确报告“哪些 provider 安装成功、哪些事件类型可用”。`installSystraceHook()` 返回失败时，应跳过 ATrace provider；其他 provider 是否继续由配置决定。

诊断信息至少区分私有符号未找到、PLT hook 安装失败与缓冲区分配失败。后端也要收到对应能力位，避免把内容为空或缺少部分事件的 trace 标成完整数据。

### 做事件语义测试

至少覆盖以下用例：

- 同线程嵌套 B/E，确认名称、TID、时间顺序和深度；
- 两个线程同时写入，确认各自栈互不干扰；
- async、counter、instant 和 track 事件，明确是补充实现还是声明不支持；
- trace 开始前已有未结束 section、缓冲区回绕、异常退出和 provider 重复启用；
- 启停后 `atrace_enabled_tags` 恢复，并测试与 Perfetto system trace 并发时的事件缺失；
- `android.os.Trace`、NDK ATrace 和直接使用 Perfetto SDK 的事件分别测试，不能假设它们必经同一 PLT 入口。

Profilo 启用期间会吞掉命中 hook 的 ATrace 写入，因此并发 Perfetto system trace 可能缺少本进程的 ATrace 事件。工程上应禁止两类采集重叠，或者把这种缺失写进采集模式和分析协议，不能把两份结果都标成完整。

### 用上游工具检查文件

Profilo 官方 [`trace-processing` 文档](https://github.com/facebookarchive/profilo/blob/main/docs/trace-processing.md)提供了从应用私有目录拉取最近 trace 的工具。这组命令只用于开发环境验证文件能否下载和解析，不代表线上上传流程：

```shell
cd python
python3 -m profilo.profilo pull_traces \
  --last com.facebook.profilo.sample
python3 -m profilo.workflow_demo --help
```

成功拉取后，还要检查 provider 注解、事件数量、首尾时间、丢失记录和缓冲区覆盖计数。文件存在只证明写文件步骤运行过，无法证明 hook 捕获完整。

### 建立本项目的开销预算

不要沿用固定的微秒或百分比，至少测量：

- provider 关闭、只开 ATrace、只开 stack、组合开启四组；
- 冷启动、滚动、动画、后台恢复和空闲五类场景；
- CPU time、帧时长、内存分配、RSS、功耗、trace 字节数和缓冲区覆盖次数；
- 低端与高端设备、4 KB 与 16 KB page-size 设备；
- P50/P95/P99 以及未开启采集的对照组。

RSS 是进程当前驻留在物理内存中的页总量。P50、P95、P99 分别表示 50%、95%、99% 样本不超过的分位数，可用来观察典型开销与尾部抖动。page size 是内核管理虚拟内存的基本页大小，4 KB 与 16 KB 设备可能呈现不同的分配和映射成本。

事件密度是开销评估的重要变量，不能只凭“是否发生系统调用”推算结果。Profilo 命中 hook 后省去 `trace_marker` 写入，同时增加事件解析、取时间戳、取 TID 与写 Profilo 缓冲区的成本；差值必须由目标构建实测。

## Android 17 新项目的选择

### 只需要公共业务标记

Java/Kotlin 可使用 `android.os.Trace` 或 AndroidX Tracing，native 可使用 NDK ATrace。这些 API 负责发出标记，不会自行启动或保存一份 trace；采集端启用对应类别后，标记才会出现在 Perfetto system trace 中。

截至 2026-08-16，[AndroidX Tracing release notes](https://developer.android.com/jetpack/androidx/releases/tracing) 列出的稳定版是 `1.3.0`。它适合通过公共 API 写系统 trace 标记，维护边界比私有变量与 PLT hook 清晰。

### 需要线上应用内 trace

官方用法见 [AndroidX Tracing 的 in-process tracing](https://developer.android.com/topic/performance/tracing/in-process-tracing)。

`2.0.0-beta01` 提供可插拔 backend 与 sink，并可把应用内事件写成 Perfetto trace packet。trace packet 是 Perfetto 文件中承载事件、时间戳与关联字段的序列化记录单元。

它在当前日期仍是预发布版本。采用方要把 API 变更、依赖升级和回归测试纳入计划。

[Perfetto Tracing SDK 的 in-process backend](https://perfetto.dev/docs/instrumentation/tracing-sdk) 面向 C++17 客户端，也能由应用自行控制采集。

in-process 表示采集服务与应用数据源都运行在同一个应用进程内，不连接系统 `traced`。

trace session 是一次有明确开始、配置、停止和输出结果的采集。backend 决定事件送往进程内服务还是系统 `traced`，sink 则决定数据写到何处。

两种 in-process 方案都只包含应用注册的数据源，不会自动加入调度器、系统调用或其他系统进程。Perfetto 官方也建议：Android 应用若只需简单时间区间和 counter，继续使用 `android.os.Trace` 或 NDK ATrace 即可。

选择应用内采集后，仍需实现抽样、大小与频率限制、脱敏、加密、上传和服务端保留策略。Perfetto 格式解决数据模型与工具兼容问题，不会替应用决定哪些用户、哪些场景允许采集。

### 需要系统级因果分析

Android 10 及更高版本应优先使用 Perfetto system trace。它能在同一时间轴上组合应用标记、`sched`、Binder、CPU 频率、内存和 I/O 等数据。Perfetto SDK 的 system backend 连接系统 `traced`，读取结果受平台权限控制，主要适合开发机、实验室或受控系统环境。

API 35 及更高版本的 [ProfilingManager](https://developer.android.com/reference/android/os/ProfilingManager) 允许应用请求系统 trace、堆采样等受平台管理的 profile。平台负责调度、频率限制与结果交付，它也不授予应用任意读取持续系统 trace 的能力。

## 工程决策

| 现状 | 建议 |
|---|---|
| 已有维护多年的 Profilo fork 和配套后端 | 保留架构，按 Android 17 清单重新验证；把 ATrace B/E 子集和失效条件写进协议 |
| 只想复用上游 AAR 快速上线 | 不建议；仓库已归档，Android 17 与 OEM 兼容性没有维护方保证 |
| 新建 Java/Kotlin 应用内 trace | 评估 AndroidX Tracing `2.0.0-beta01`，并接受预发布 API 风险 |
| 新建 native 应用内 trace | 评估 Perfetto SDK in-process backend |
| 线下或实验室定位跨进程问题 | 使用 Perfetto system trace，不用 Profilo trace 代替系统时间线 |
| 只需持续指标与异常触发 | 优先做聚合指标和短窗口触发，命中后再采集受控 trace |

Profilo 的 provider 组织方式、触发控制、固定容量缓冲区与异步文件处理仍可作为架构参考。Android 17 项目若继续使用其源码，应把 `libcutils` 私有变量、特定 PLT relocation 和旧 ART 布局视为需要逐版本验证的兼容层。
