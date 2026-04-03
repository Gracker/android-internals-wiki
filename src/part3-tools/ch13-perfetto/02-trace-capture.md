---
title: "Trace 抓取"
chapter: "13.2"
section: "13.2"
status: ready-for-review
drafted_date: "2026-04-03"
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-04-03"
last_verified_against: "perfetto.dev docs, AOSP android-16.0.0_r1"
confidence: high
sources:
  - type: blog
    path: "https://www.androidperformance.com/2024/05/21/Android-Perfetto-02-how-to-get-perfetto/"
  - type: official
    path: "https://perfetto.dev/docs/quickstart/android-tracing"
  - type: blog
    path: "Cubox/Perfetto 快速上手指南1 —— Trace 的抓取-2025-03-20.md"
  - type: blog
    path: "Cubox/Android Perfetto 系列 4：使用命令行在本地打开超大 Trace · Android Performance-2025-02-09.md"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/native-heap-profiler"
tags: ['perfetto', 'trace', 'atrace', 'trace-capture', 'heapprofd']
related_chapters: ["13.1", "13.3", "14.1", "15.1"]
---

# Trace 抓取

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 命令行抓取：perfetto -c config.pbtxt -o trace.perfetto-trace
- 🔹 常用 TraceConfig 配置项：buffer_size、duration、data_sources
- 🔹 系统 atrace categories 配置：sched、gfx、view、wm、am、binder 等
- 🔹 用 record_android_trace 脚本快速抓取
- 🔹 通过 Perfetto UI 在线配置与抓取
- 🔹 在 App 中用 Trace.beginSection / Trace.endSection 添加自定义标记

### 扩展（可选深入）

- 🔸 长时间 Trace（Long Trace）的配置与分割策略
- 🔸 Heap Profiling 与 Callstack Sampling 的配置

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 Trace 抓取

性能分析的第一步永远是"拿到数据"。不管我们是排查卡顿、分析启动速度、还是调查 ANR，都需要先抓取一份 Trace 文件，然后在 Perfetto UI 中打开它。如果抓取的配置不对——比如漏掉了关键的 atrace category，或者 buffer 太小导致数据被覆盖——后续分析就无从谈起。

更关键的是，Trace 抓取不是只有一种方式。不同场景需要不同的抓取策略：快速复现一个卡顿问题，用 `record_android_trace` 脚本几行命令就能搞定；分析启动性能，需要在 App 代码中插入自定义标记来精确度量各个阶段；排查内存泄漏，则需要额外开启 Heap Profiling。了解这些方式的差异和适用场景，能让我们在最短时间内拿到最有价值的 Trace 数据。

本节按照从简单到复杂的顺序，逐一介绍 Perfetto Trace 的各种抓取方式，最后给出一份覆盖常见分析场景的推荐配置。

## 命令行抓取：perfetto 命令

[已验证: 官方文档, perfetto.dev/docs/quickstart/android-tracing]

最基础的抓取方式是直接在设备上运行 `perfetto` 命令。Perfetto 从 Android 10（API 29）开始作为系统级追踪工具内置在设备中，我们只需要通过 `adb shell` 就可以调用它。

### 最简命令

```bash
adb shell perfetto -o /data/misc/perfetto-traces/trace.perfetto-trace -t 10s \
  sched freq idle am wm gfx view binder_driver hal dalvik input res memory
```

这条命令启动一个 10 秒的追踪会话，收集指定的 atrace category 数据，输出到设备上的指定路径。抓取完成后，用 `adb pull` 把文件拉到本地：

```bash
adb pull /data/misc/perfetto-traces/trace.perfetto-trace
```

这里有几个关键参数需要理解：

- `-o` 指定输出路径。Perfetto 要求输出路径必须在 `/data/misc/perfetto-traces/` 目录下（需要 root 或 shell 权限），这个目录是 Perfetto 服务进程有写入权限的标准位置。
- `-t 10s` 指定追踪时长。也可以用 `-t 20s`、`-t 1m` 等格式。如果不指定 `-t`，追踪会持续到手动停止。
- 后面的 `sched freq idle am wm gfx ...` 是 atrace category 列表，决定抓取哪些系统事件。我们稍后详细讨论。

### 使用配置文件抓取

当追踪需求稍微复杂一些——比如需要调整 buffer 大小、开启多个数据源、或者配置 Long Trace——直接在命令行拼接参数就不太方便了。这时候可以用配置文件的方式。

Perfetto 使用 Protocol Buffer 文本格式（`.pbtxt`）的配置文件，官方称为 `TraceConfig`。我们可以把完整的配置写到一个文件中，然后通过 `-c` 参数传给 `perfetto` 命令：

```bash
adb shell perfetto -c /data/misc/perfetto-configs/config.pbtxt \
  --txt \
  -o /data/misc/perfetto-traces/trace.perfetto-trace
```

注意 `--txt` 参数告诉 Perfetto 配置文件是人类可读的文本格式（而非二进制 protobuf）。配置文件需要预先 `adb push` 到设备上：

```bash
adb push config.pbtxt /data/misc/perfetto-configs/config.pbtxt
```

`TraceConfig` 文件的基本结构是这样的：

```
buffers {
  size_kb: 65536
  fill_policy: DISCARD
}

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "power/cpu_idle"
      atrace_categories: "am"
      atrace_categories: "wm"
      atrace_categories: "gfx"
      atrace_categories: "view"
      atrace_categories: "sched"
    }
  }
}

data_sources {
  config {
    name: "linux.process_stats"
    process_stats_config {
      scan_all_processes_on_start: true
    }
  }
}

duration_ms: 10000
```

[图：TraceConfig 文件结构示意——buffer 配置、data_sources 配置、duration 配置三段]

这份配置做的事情是：分配 64MB 的 trace buffer，开启 ftrace 数据源（包括内核调度事件和 atrace category），同时收集进程信息，追踪 10 秒后自动停止。

## 常用 TraceConfig 配置项

[已验证: 官方文档, perfetto.dev/docs/concepts/config]

TraceConfig 是 Perfetto 追踪的核心配置，理解它的几个关键配置项，我们就能灵活地调整抓取行为。

### buffer 配置

`buffers` 块定义了 Trace 数据的内存缓冲区。每个 Trace 会话至少需要一个 buffer。

```
buffers {
  size_kb: 65536          # 64MB
  fill_policy: DISCARD     # 满了就丢弃新数据
}
```

- `size_kb`：buffer 大小，单位 KB。常见的值是 32768（32MB）到 131072（128MB）。buffer 太小会导致数据被覆盖或丢失，太大会占用过多内存。对于 10-30 秒的常规 Trace，64MB 通常是够用的。如果开启了调用栈采样或 Heap Profiling，需要更大的 buffer。
- `fill_policy`：满时的策略。`DISCARD` 表示 buffer 满后丢弃新事件（Stop when full），适合确定性抓取；`RING_BUFFER` 表示环形覆盖，旧数据被新数据覆盖，适合长时间监控。

### duration 配置

```
duration_ms: 10000    # 10 秒
```

`duration_ms` 指定追踪时长，单位毫秒。如果不设置，Trace 会一直持续到手动停止（通过 `adb shell kill -SIGINT <pid>`）。对于可复现的性能问题，设置固定时长可以精确控制抓取窗口。

### data_sources 配置

`data_sources` 是 TraceConfig 中最核心的部分，它决定了我们抓取哪些数据。每个 data_source 都有一个 `name` 字段和对应的 config。

最常用的数据源是 `linux.ftrace`，它负责采集内核 ftrace 事件和 atrace 用户空间事件。其他的常用数据源包括：

- `linux.process_stats`：进程和线程信息
- `linux.sys_stats`：系统级统计（CPU、内存、I/O）
- `android.log`：logcat 日志
- `android.surfaceflinger.frametimeline`：帧时间线数据
- `android.gpu.memory`：GPU 内存使用

我们可以同时启用多个数据源，只需要在 TraceConfig 中添加多个 `data_sources` 块即可。

### 一个推荐的通用配置

下面是一份适用于大多数性能分析场景的通用配置。我们在日常工作中可以把这份配置作为起点，按需增减 atrace category：

```
buffers {
  size_kb: 65536
  fill_policy: DISCARD
}

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_wakeup"
      ftrace_events: "sched/sched_waking"
      ftrace_events: "sched/sched_blocked_reason"
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "power/cpu_idle"
      ftrace_events: "power/gpu_frequency"
      ftrace_events: "power/suspend_resume"
      
      atrace_categories: "am"
      atrace_categories: "wm"
      atrace_categories: "gfx"
      atrace_categories: "view"
      atrace_categories: "input"
      atrace_categories: "binder_driver"
      atrace_categories: "hal"
      atrace_categories: "dalvik"
      atrace_categories: "res"
      atrace_categories: "sched"
      atrace_categories: "freq"
      atrace_categories: "idle"
      
      atrace_apps: "com.example.myapp"
    }
  }
}

data_sources {
  config {
    name: "linux.process_stats"
    process_stats_config {
      scan_all_processes_on_start: true
    }
  }
}

data_sources {
  config {
    name: "linux.sys_stats"
    sys_stats_config {
      meminfo_period_ms: 1000
      stat_period_ms: 1000
      stat_counters: STAT_CPU_TIMES
      stat_counters: STAT_FORK_COUNT
    }
  }
}

data_sources {
  config {
    name: "android.surfaceflinger.frametimeline"
  }
}

duration_ms: 20000
```

[图：通用配置覆盖的数据维度——CPU 调度、渲染管线、系统统计、帧时间线]

注意 `atrace_apps` 字段。如果要追踪特定 App 的自定义 Trace 标记（通过 `Trace.beginSection` 添加的），必须在这里指定 App 的包名。否则即使 App 代码中有 `Trace.beginSection` 调用，也不会出现在 Trace 中。

## atrace Categories 详解

[已验证: 官方文档, source.android.com/devices/tech/debug/ftrace; AOSP atrace category 定义]

atrace categories 是 Android 系统预定义的事件分类，每一个 category 对应一组系统模块的追踪事件。选择正确的 category 组合，是拿到有价值 Trace 的关键。

在命令行中，我们可以用 `adb shell atrace --list_categories` 查看当前设备支持的所有 category。不同设备、不同 Android 版本支持的列表可能略有差异，但核心的几个 category 在所有设备上都可用。

下面我们按用途分组，逐一介绍日常性能分析中最常用的 categories。

### 渲染与 UI（分析卡顿、流畅度必备）

- **gfx**：Graphics 子系统的事件，包括 SurfaceFlinger 合成、BufferQueue 状态变化、Choreographer 的 VSync 回调等。分析帧渲染管线问题（如掉帧、GPU 耗时过长）时，`gfx` 是必选的。
- **view**：View 系统事件，包括 measure、layout、draw 的耗时。卡顿分析中，`view` category 能直接告诉我们某一帧的 measure/layout/draw 阶段花了多长时间。

### 系统服务（分析启动、ANR 必备）

- **am**：ActivityManager 事件，包括 Activity 的生命周期回调、Service 启停、Broadcast 分发等。分析 App 启动流程和 ANR 时，`am` 是核心 category。
- **wm**：WindowManager 事件，包括窗口的添加、移除、焦点变化等。配合 `am` 使用可以追踪完整的 UI 展示链路。
- **sm**：ServiceManager 事件，追踪系统服务的注册和获取。在 Binder 调用频繁的场景中有参考价值。

### CPU 调度（几乎所有场景都要选）

- **sched**：CPU 调度事件，包括线程的唤醒、切换、阻塞原因。这是 Perfetto 中最重要的 category——没有 `sched`，我们看不到每个线程在什么时候运行、什么时候被挂起、为什么被挂起。几乎所有性能分析场景都应该选上 `sched`。
- **freq**：CPU 频率变化事件。配合 `sched` 使用，可以看出线程在什么频率的 CPU 核心上运行，判断是否存在频率爬升慢导致的性能问题。
- **idle**：CPU idle 状态事件。可以观察 CPU 是否进入了深度睡眠，以及被唤醒的原因。

### Binder 与 IPC

- **binder_driver**：Binder 驱动事件，包括 Binder 事务的开始和完成。分析跨进程调用的耗时、Binder 调用阻塞主线程导致的 ANR 时，这个 category 至关重要。

### 运行时与资源

- **dalvik**：ART 虚拟机事件，包括 GC、JIT 编译等。内存抖动或 GC 暂停导致的卡顿，需要 `dalvik` category 来定位。
- **res**：资源加载事件。追踪资源（图片、布局等）的加载耗时。
- **input**：Input 事件分发，包括触摸事件的入队和分发。分析点击响应延迟、滑动卡顿时，`input` category 提供了事件到达应用的时间线起点。
- **memory**：内存事件。追踪内存分配和释放相关的系统事件。

### 按分析场景选择 Categories

不同的性能分析场景，需要的 category 组合不同。下面是一份快速参考：

| 分析场景 | 推荐 Categories |
|---------|----------------|
| 卡顿/流畅度 | sched freq gfx view input |
| App 启动 | sched freq am wm view binder_driver |
| ANR | sched am wm binder_driver input |
| Binder 性能 | sched binder_driver |
| 内存问题 | sched dalvik memory gfx |
| 功耗分析 | sched freq idle power |

这张表只是起点。实际分析中，我们通常会在推荐组合的基础上额外加上 `hal`（硬件抽象层事件）和 `res`（资源加载），以获得更完整的上下文信息。

## 用 record_android_trace 快速抓取

[已验证: 官方文档, perfetto.dev/docs/quickstart/android-tracing]

`record_android_trace` 是 Perfetto 团队提供的一个 Python 脚本，它封装了底层 `perfetto` 命令的复杂性，让抓取 Trace 变得像运行一个命令一样简单。

### 获取脚本

```bash
curl -O https://raw.githubusercontent.com/google/perfetto/main/tools/record_android_trace
chmod u+x record_android_trace
```

[待验证: 某些网络环境下可能需要代理访问 GitHub raw 域名]

### 基本用法

最简单的方式，不带任何参数：

```bash
python3 record_android_trace -o trace.perfetto-trace
```

这会启动一个默认 10 秒的 Trace，使用默认配置。更多时候，我们会指定时长、buffer 大小和 atrace categories：

```bash
python3 record_android_trace -o trace.perfetto-trace -t 20s -b 64mb \
  sched freq idle am wm gfx view binder_driver hal dalvik input res memory
```

这里 `-t 20s` 表示 20 秒，`-b 64mb` 表示 64MB buffer，后面的参数是 atrace category 列表。

### 为什么推荐这个脚本

相比直接在设备上运行 `perfetto` 命令，`record_android_trace` 脚本有几个明显优势：

第一，**自动处理文件传输**。脚本会自动把 Trace 从设备上 pull 到本地当前目录，不需要我们手动执行 `adb pull`。

第二，**自动打开 Trace**。抓取完成后，脚本会自动在浏览器中打开 Perfetto UI 并加载 Trace 文件，省去了手动拖拽文件到浏览器的步骤。

第三，**自动配置 ADB 连接**。脚本会检测连接的设备，处理 ADB 权限问题，确保 Trace 能正常抓取。

第四，**支持配置文件**。如果需要更精细的配置，可以通过 `-c` 参数传入 `.pbtxt` 配置文件：

```bash
python3 record_android_trace -c config.pbtxt -o trace.perfetto-trace -t 30s
```

对于日常的快速分析场景，`record_android_trace` 脚本是最推荐的抓取方式。

## 通过 Perfetto UI 在线抓取

[已验证: 官方文档, ui.perfetto.dev/#!/record]

Perfetto UI（<https://ui.perfetto.dev>）不仅是一个 Trace 分析工具，它还内置了 Trace 抓取功能。打开网站后，左侧导航栏选择 "Record new trace"，就可以通过图形界面配置和执行抓取。

### 连接设备

使用 USB 线连接设备和电脑后，Perfetto UI 会自动检测到连接的 Android 设备。在 "Target platform" 下拉框中选择你的设备。

如果设备没有被检测到，需要确认 ADB 连接正常（`adb devices` 可以看到设备），并且浏览器支持 WebUSB。

### 配置抓取参数

Perfetto UI 把配置分成了几个直观的 Tab：

**Buffer 模式选择**（在 "Recording mode" 区域）：
- **Stop when full**：buffer 满了就停止（默认，最常用）。适合确定性时长抓取。
- **Ring buffer**：环形覆盖，新数据覆盖旧数据。适合不确定何时复现的问题。
- **Long trace**：持续写入文件。适合长时间追踪（几分钟到几小时）。

**数据源选择**（在各个 Tab 页中）：
- **CPU**：包括 CPU 调度、频率、idle 状态、调用栈采样。性能分析基本都要选。
- **GPU**：GPU 渲染阶段、GPU 内存。
- **Memory**：内存信息、Heap Profiling。
- **Android Apps**：atrace categories 和指定 App 的 Trace 事件。
- **Advanced**：logcat、系统统计、网络包等。

[图：Perfetto UI 抓取界面截图——左侧 Recording mode 选择，中间数据源配置 Tab，右侧 Start Recording 按钮]

### 导出配置为命令行

Perfetto UI 最实用的一个功能是：在 UI 上配置好所有参数后，切换到 "Recording command" Tab，可以看到对应的命令行和 `.pbtxt` 配置文件。

这意味着我们可以把 UI 上的可视化配置直接转化为可重复执行的脚本命令。在团队协作中，可以把这份配置文件提交到代码仓库，确保所有人使用相同的 Trace 配置。

操作方式是：在 "Recording command" Tab 中，复制两个 EOF 标记之间的内容，保存为 `config.pbtxt` 文件。之后团队成员就可以用这个配置文件来抓取 Trace：

```bash
python3 record_android_trace -c config.pbtxt -o trace.perfetto-trace -t 20s
```

## 在 App 中添加自定义 Trace 标记

[已验证: 官方文档, developer.android.com/reference/android/os/Trace; AOSP frameworks/base/core/java/android/os/Trace.java]

系统默认的 atrace category 覆盖了大部分系统级行为，但很多时候我们需要在 App 代码中标记自定义的业务逻辑耗时——比如 "加载首页数据"、"初始化播放器"、"解析 JSON 响应" 这些 App 特有的阶段。Android 提供了 `android.os.Trace` API 来实现这个需求。

### 基本用法

```java
import android.os.Trace;

// 标记一段代码的开始
Trace.beginSection("loadHomePageData");

try {
    // ... 实际的业务代码 ...
    fetchDataFromNetwork();
    parseJsonResponse();
    updateUI();
} finally {
    // 标记结束（必须与 beginSection 配对）
    Trace.endSection();
}
```

抓取 Trace 时，只要在 atrace categories 中包含了 App 的包名（通过 `atrace_apps` 或命令行参数 `-a com.example.myapp`），这些自定义标记就会出现在 Perfetto UI 中 App 进程的主线程 track 上，显示为带有标签名的彩色切片。

`Trace.beginSection` 和 `Trace.endSection` 使用的底层标签是 `ATRACE_TAG_APP`。这意味着所有通过 `android.os.Trace` API 添加的标记都会归类在同一个 tag 下。

### 使用约束

有几个关键约束需要注意：

第一，`beginSection` 和 `endSection` 必须**严格配对、嵌套调用**。不能交叉嵌套，也不能在一个线程中 `beginSection` 然后在另一个线程中 `endSection`。实际上，`Trace.endSection()` 不需要传入标签名——它自动关闭最近一次 `beginSection` 对应的区域，这和栈的 push/pop 机制一样。

第二，标签名会被 Perfetto 截断到 127 个字符。建议使用简洁但足够描述性的标签名，比如 `"HomeFragment.loadData"` 而不是 `"Load the home page data from the remote server"`。

第三，`beginSection`/`endSection` 只能在同一线程中使用。如果要标记多线程操作，每个线程需要独立的 `beginSection`/`endSection` 对。

### 异步标记（API 29+）

从 Android 10（API 29）开始，`android.os.Trace` 增加了异步追踪 API，可以跨线程标记一个操作的开始和结束：

```java
import android.os.Trace;

// 在一个线程中开始
long cookie = Thread.currentThread().getId();  // 使用线程 ID 作为 cookie
Trace.beginAsyncSection("networkRequest", cookie);

// ... 网络请求 ...

// 在回调线程中结束
Trace.endAsyncSection("networkRequest", cookie);
```

`beginAsyncSection` 和 `endAsyncSection` 通过一个 `cookie` 值关联同一次操作。这解决了异步操作（如网络请求、Handler 回调）中无法使用同步 `beginSection`/`endSection` 的问题。

### Native 代码中的自定义标记

对于 C/C++ 代码（如 JNI 层、Native 库），可以使用 Perfetto 提供的 C++ Trace API：

```c
#include <cutils/trace.h>

ATRACE_BEGIN("nativeInit");
// ... 初始化代码 ...
ATRACE_END();
```

或者使用更现代的 Perfetto Trace SDK（C++17）来定义自定义数据源，这需要集成 Perfetto SDK 到项目中。[待补充: Perfetto C++ SDK 集成示例]

### 在 Perfetto 中的表现

在 Perfetto UI 中，自定义 Trace 标记出现在 App 进程对应线程的 track 上。每个 `beginSection`/`endSection` 对显示为一个带有标签文字的切片（slice），长度表示耗时。

[图：Perfetto UI 中自定义 Trace 标记的展示——App 主线程 track 上的 "loadHomePageData" 等自定义切片]

通过自定义标记和系统事件的叠加，我们可以在同一个时间轴上看到业务逻辑耗时和系统级行为（如 VSync、GC、Binder 调用）的完整上下文。这种"业务 + 系统"的双视角，是 Perfetto 分析区别于传统 profiling 工具的核心优势之一。

[自动发现] **开发者选项中的系统追踪工具**：Android 设备的开发者选项中内置了"系统追踪"应用，可以直接在设备上配置和启动 Trace 抓取，无需连接电脑。适合在现场复现问题时使用。抓取完成后，Trace 文件保存在设备上，后续可以通过 `adb pull` 导出。入口为"设置 → 开发者选项 → 系统追踪"。

## Long Trace：长时间追踪

[已验证: 官方文档, perfetto.dev/docs/concepts/config#long-traces]

默认情况下，Perfetto 把 Trace 数据全部缓存在内存 buffer 中，在会话结束时一次性写入文件。这种方式的优点是开销最小，缺点是 Trace 大小受设备物理内存限制——通常能记录几十秒到几分钟的数据。

但有些问题需要长时间追踪才能复现：比如偶发的 ANR（可能几小时才出现一次）、长时间运行后的内存泄漏、或者跑分场景下完整的 Benchmark 过程。Perfetto 的 Long Trace 模式就是为了这类场景设计的。

### 启用 Long Trace

Long Trace 的核心配置是在 TraceConfig 中设置 `write_into_file: true`：

```
buffers {
  size_kb: 32768    # 32MB in-memory buffer
}

write_into_file: true
file_write_period_ms: 5000     # 每 5 秒刷盘一次
max_file_size_bytes: 2147483648   # 最大 2GB

duration_ms: 3600000   # 1 小时

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_wakeup"
      ftrace_events: "power/cpu_frequency"
      atrace_categories: "am"
      atrace_categories: "wm"
      atrace_categories: "gfx"
      atrace_categories: "view"
      atrace_categories: "sched"
    }
  }
}
```

这里有几个关键参数：

- `write_into_file: true`：启用 Long Trace 模式，Trace 数据会定期从内存 buffer 刷写到磁盘文件。
- `file_write_period_ms`：刷盘间隔。默认是 5000ms（5 秒）。更短的间隔意味着每次刷盘的数据量更少、buffer 可以更小，但磁盘 I/O 更频繁。
- `max_file_size_bytes`：Trace 文件的最大大小。达到上限后 Trace 自动停止。不设置则无限制（直到磁盘满）。
- `duration_ms`：总追踪时长。Long Trace 通常设置较长的时长。

### Long Trace 的注意事项

Long Trace 在降低内存要求的同时引入了新的 trade-off：

第一，**磁盘 I/O 开销**。每次刷盘都会产生磁盘写入，在 I/O 敏感的场景（如 Benchmark）中可能影响测量结果的准确性。

第二，**数据源需要精简**。长时间追踪时，如果开启了太多 atrace category，生成的数据量可能非常大。建议只保留分析目标相关的核心 category，通常 `sched` + `freq` + `gfx` + `view` 就够了。

第三，**大文件分析**。长时间追踪可能产生几百 MB 甚至几 GB 的 Trace 文件。这种大文件在浏览器中通过 ui.perfetto.dev 打开会非常慢甚至崩溃。解决方案是使用 `trace_processor_shell` 命令行工具在本地解析，然后在 Perfetto UI 中通过本地 HTTP 服务查看。具体操作参见本系列第 4 篇（§13.4 大 Trace 文件处理）。

## Heap Profiling 与 Callstack Sampling

[已验证: 官方文档, perfetto.docs/data-sources/native-heap-profiler; perfetto.dev/docs/data-sources/callstack-sampling]

Perfetto 不只能做时间线追踪。它还集成了内存剖析（Heap Profiling）和 CPU 调用栈采样（Callstack Sampling），可以在同一个 Trace 会话中同时收集这些数据。

### Native Heap Profiling（heapprofd）

`heapprofd` 是 Android 10+ 内置的采样式堆内存分析器。它通过 hook `malloc`/`free`（以及 C++ 的 `operator new`/`delete`）来追踪 Native 堆分配，生成按调用栈聚合的分配统计。

在 TraceConfig 中启用 heapprofd：

```
data_sources {
  config {
    name: "linux.heapprof"
    heapprof_config {
      sampling_interval_bytes: 4096
      process_cmdline: "com.example.myapp"
      continuous_dump_config {
        dump_phase_ms: 0
        dump_interval_ms: 10000
      }
    }
  }
}
```

关键参数：
- `sampling_interval_bytes`：采样间隔，默认 4096 字节。意味着每分配 4096 字节采样一次。更大的值意味着更低的开销但更粗的粒度。
- `process_cmdline`：目标进程的包名。不设置则对所有进程生效（高开销）。
- `continuous_dump_config`：周期性导出快照的间隔。用于观察内存增长趋势。

在 Perfetto UI 中，Heap Profiling 数据显示为火焰图（Flamegraph）和分配详情表，可以直接看到哪些调用路径分配了最多的内存。

### Java Heap Sampling（Android 12+）

从 Android 12 开始，heapprofd 也支持 Java 堆的采样分析。配置中设置 `heaps: "com.android.art"` 即可：

```
data_sources {
  config {
    name: "linux.heapprof"
    heapprof_config {
      sampling_interval_bytes: 4096
      heaps: "com.android.art"
      process_cmdline: "com.example.myapp"
    }
  }
}
```

注意 Java Heap Sampling 和传统的 Java Heap Dump（如通过 `android.app.ActivityManager.getProcessMemoryDump` 获取的）不同——Sampling 提供的是分配时的调用栈，而非某一时刻的对象存留图。两种方式互补，前者适合定位"谁在频繁分配"，后者适合定位"谁持有大量对象不释放"。

### CPU Callstack Sampling

Perfetto 还可以在 Trace 中集成 CPU 调用栈采样。这对分析 CPU 密集型瓶颈（如某段计算代码占用大量 CPU）非常有用：

```
data_sources {
  config {
    name: "linux.perf"
    perf_event_config {
      timebase {
        frequency: 100
        timestamp_clock: PERF_CLOCK_MONOTONIC
      }
      callstack_sampling {
      }
    }
  }
}
```

`frequency: 100` 表示每秒采样 100 次（10ms 间隔）。采样频率越高，结果越精确，但开销也越大。对于大多数分析场景，100-1000 Hz 是合理的范围。

在 Perfetto UI 中，调用栈采样数据显示为火焰图，可以直观地看到 CPU 时间花在了哪些函数调用上。

### 同时收集多种数据的配置示例

在一份 TraceConfig 中，我们可以同时开启多个数据源。下面是一份同时收集 ftrace 事件、Heap Profiling 和 CPU 调用栈采样的配置：

```
buffers {
  size_kb: 131072   # 128MB，Heap Profiling 需要更大 buffer
  fill_policy: DISCARD
}

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_wakeup"
      ftrace_events: "power/cpu_frequency"
      atrace_categories: "am"
      atrace_categories: "wm"
      atrace_categories: "gfx"
      atrace_categories: "view"
      atrace_categories: "sched"
      atrace_apps: "com.example.myapp"
    }
  }
}

data_sources {
  config {
    name: "linux.heapprof"
    heapprof_config {
      sampling_interval_bytes: 4096
      heaps: "com.android.art"
      process_cmdline: "com.example.myapp"
    }
  }
}

data_sources {
  config {
    name: "linux.perf"
    perf_event_config {
      timebase {
        frequency: 100
        timestamp_clock: PERF_CLOCK_MONOTONIC
      }
      callstack_sampling {
      }
    }
  }
}

duration_ms: 20000
```

注意当同时开启 Heap Profiling 时，buffer 建议设为 128MB 或更大，因为调用栈数据的体积比单纯的 ftrace 事件大得多。

## 常见问题与误区

**"atrace categories 选得越多越好"**——这是一个常见的误区。每个 category 都会产生一定量的 Trace 数据，选太多会导致 buffer 快速填满，反而丢失了真正需要的数据。正确的做法是根据分析目标选择针对性的 category 组合，参考前面「按分析场景选择 Categories」的推荐表。

**"Trace 文件越大，信息越丰富"**——也不对。信息丰富度取决于数据源的选择和配置是否精准，而不是文件大小。一份 20MB 的精准 Trace 通常比一份 200MB 的冗余 Trace 更容易定位问题。

**"抓 Trace 影响性能，测出来的数据不准"**——Perfetto 的设计目标是低开销。在常规配置下（只开 sched/gfx/view 等核心 category），Trace 的性能开销通常在 1-3% 以内。但开启 Heap Profiling 或高频率 CPU 采样时，开销会明显增大（可能达到 5-10%）。做精确性能测量时（如 Benchmark），建议只保留最核心的 category。

**"beginSection 忘了 endSection 没关系"**——这会导致 Trace 数据混乱。未配对的 section 会被 Perfetto 解析器丢弃，浪费了 instrumentation 的努力。强烈建议用 try/finally 包裹，确保 `endSection` 总是被调用。

## 与其他章节的关系

本章是工具篇的入口。掌握了 Trace 抓取之后，后续章节将在本节抓取的 Trace 数据基础上展开分析：

- §13.3（Perfetto View）会介绍如何在 Perfetto UI 中阅读和导航 Trace
- §13.5（主题分析）会深入各性能主题的 Trace 分析方法
- §13.6（线程 CPU 状态）专门讲解如何通过 `sched` category 分析线程的运行状态
- §14.1（Android Studio Profiler）提供了另一种可视化 Trace 的方式

如果你已经抓到了一份 Trace 但不知道怎么看，直接跳到 §13.3 即可。

## 参考资料

1. Perfetto 官方文档 - Quickstart: Android Tracing: https://perfetto.dev/docs/quickstart/android-tracing
2. Perfetto 官方文档 - TraceConfig 配置: https://perfetto.dev/docs/concepts/config
3. Perfetto 官方文档 - Native Heap Profiler: https://perfetto.dev/docs/data-sources/native-heap-profiler
4. Perfetto 官方文档 - Callstack Sampling: https://perfetto.dev/docs/data-sources/callstack-sampling
5. Android Developers - Trace API: https://developer.android.com/reference/android/os/Trace
6. AOSP Trace.java 源码: frameworks/base/core/java/android/os/Trace.java
7. 高爷博客 - Android Perfetto 系列 2：Perfetto Trace 抓取: https://www.androidperformance.com/2024/05/21/Android-Perfetto-02-how-to-get-perfetto/
8. 高爷博客 - Android Perfetto 系列 4：使用命令行在本地打开超大 Trace: https://www.androidperformance.com/2025/02/08/Android-Perfetto-04-Open-Big-Trace-With-Command-Line/
