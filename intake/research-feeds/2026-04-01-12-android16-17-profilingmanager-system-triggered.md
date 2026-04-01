---
source: web-search-synthesis
query: "Android 16 17 ProfilingManager system-triggered profiling ANR cold start OOM excessive CPU"
date: 2026-04-01
target_sections:
  - "8.2"
  - "9.1"
  - "9.3"
  - "13.7"
  - "14.7"
relevance: 9
technical_depth: 9
timeliness: 10
verifiability: 9
total_score: 37
status: candidate
---

# Android 16/17 ProfilingManager 系统触发式性能追踪

## 核心发现

### 1. ProfilingManager 演进时间线

| Android 版本 | 能力 | 关键 API |
|---|---|---|
| **15** | 引入 ProfilingManager 基础 API | `registerProfilingListener()`，手动触发 heap dump / stack sample / system trace |
| **16** | 系统触发式追踪（System-Triggered Profiling） | 自动触发 cold start `reportFullyDrawn` trace 和 ANR trace |
| **17** | 扩展触发类型 | `TRIGGER_TYPE_COLD_START`、`TRIGGER_TYPE_OOM`、`TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` |

### 2. Android 16 — 系统触发式追踪

**最大突破**：应用可以注册对特定系统事件的兴趣，由系统自动采集 trace，无需手动在代码中埋点。

**工作流程**：
1. 应用通过 `ProfilingManager` 注册感兴趣的触发事件
2. 当对应系统事件发生时（如 ANR），系统自动开始采集
3. trace 数据（Java Heap Dump / Stack Sample / System Trace）保存到应用的 data 目录
4. 应用可以在后续启动时读取这些 trace 文件进行分析

**Cold Start 追踪**：Android 16 新增了 `reportFullyDrawn` 的自动 trace 能力。这意味着应用可以获取从进程创建到 `reportFullyDrawn` 的完整 Perfetto trace，而不需要在 Application.onCreate() 中手动 `Debug.startMethodTracing()`。

**ANR 追踪**：当 ANR 发生时，系统自动捕获 ANR 时刻的 trace，包括主线程堆栈和系统状态。

**ApplicationStartInfo 增强**：新增 `getStartComponent()` 方法，开发者可以精确知道是哪个组件（Activity/Service/BroadcastReceiver/ContentProvider）触发了应用启动，从而针对性地优化不同的启动路径。

### 3. Android 17 — 新增三种触发类型

#### TRIGGER_TYPE_COLD_START
- 触发时机：应用冷启动时
- 采集内容：call stack sample + system trace
- 价值：替代传统的手动 `Debug.startMethodTracing()`，由系统自动捕获启动全链路 trace

#### TRIGGER_TYPE_OOM
- 触发时机：应用发生 OutOfMemoryError 时
- 采集内容：Java Heap Dump
- 价值：自动捕获 OOM 时刻的堆快照，无需提前埋点。对于线上偶发的 OOM 问题尤其有价值。

#### TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE
- 触发时机：应用因 CPU 使用过高被系统杀掉时
- 采集内容：call stack sample
- 价值：这是之前完全无法获取信息的场景——应用被杀后开发者通常只能看到 tombstone 或 ANR traces，但 CPU 过高被杀通常不会产生 ANR。现在可以在被杀时自动采集堆栈。

### 4. 对 ANR 分析的影响（Ch9 关联）

**传统的 ANR 分析痛点**：
- ANR 发生时，`traces.txt` 只包含 ANR 时刻的快照，缺少 ANR 发生前一段时间的主线程行为
- 开发者需要在应用中预埋监控代码，但 ANR 通常在意料之外的时间点发生

**Android 16/17 的改进**：
- 系统触发式 trace 提供了 **ANR 发生前的历史数据**
- `TRIGGER_TYPE_COLD_START` 可以捕获启动阶段的主线程阻塞
- `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` 解决了"应用因 CPU 过高被杀但无 trace"的黑盒问题

### 5. 对启动优化分析的影响（Ch8 关联）

**ApplicationStartInfo.getStartComponent()** 的价值：
- 冷启动、热启动、温启动的区分更精确
- 可以按启动组件类型分别统计启动耗时
- 配合 Baseline Profiles，可以针对不同启动路径生成不同的 profile

## 对 Wiki 的价值

### 映射到 §14.7 ProfilingManager

这一节目前是 pending 状态，本文可以作为核心素材。ProfilingManager 从 Android 15 引入到 Android 17 扩展，是一个完整的 API 演进故事。

### 映射到 §8.2 App 启动全流程

`ApplicationStartInfo.getStartComponent()` 和 `TRIGGER_TYPE_COLD_START` 是启动分析工具链的重要补充。

### 映射到 §9.3 ANR 分析方法

系统触发式 ANR trace 改变了 ANR 分析的方法论——从"事后分析 traces.txt 快照"到"获取 ANR 前的完整 trace 历史"。

### 映射到 §13.7 Perfetto 的高级用法

ProfilingManager 产生的 trace 文件可以在 Perfetto UI 中分析，这是 Perfetto 在 Android 16/17 的新用法。

## 代码示例（概念级）

```kotlin
// Android 17: 注册系统触发式追踪
val profilingManager = getSystemService(ProfilingManager::class.java)

// 注册感兴趣的触发类型
profilingManager.registerForAllProfilingResults(
    executor = Executors.newSingleThreadExecutor(),
    callback = { result ->
        // result 中包含 trace 文件路径
        val traceFile = File(result.resultFilePath)
        // 上传或本地分析
    }
)

// Android 16+ 自动触发的系统事件（无需额外代码）：
// - cold start reportFullyDrawn trace
// - ANR trace
// Android 17+ 额外触发：
// - OOM heap dump
// - excessive CPU kill stack sample
```

## 验证状态

- [已验证: ProfilingManager 在 Android 15 引入，Android 16 增加系统触发]
- [已验证: ApplicationStartInfo.getStartComponent() 在 Android 16 新增]
- [已验证: Android 17 新增 TRIGGER_TYPE_OOM 和 TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE]
- [待验证: 系统触发 trace 在 Perfetto UI 中的具体展现格式]
- [待验证: TRIGGER_TYPE_COLD_START 与手动 Perfetto trace 抓取的数据差异]
