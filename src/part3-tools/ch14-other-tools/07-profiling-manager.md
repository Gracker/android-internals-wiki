---
title: "ProfilingManager"
chapter: "14.7"
section: "14.7"
section_title: "ProfilingManager"
status: ready-for-review
applicable_versions: "Android 15+（System Triggered Profiling 16+，OOM / ANOMALY / running trace 扩展见 Android 17）"
sources:
  - type: official
    path: "developer.android.com/guide/topics/profiling"
  - type: official
    path: "developer.android.com/reference/android/os/ProfilingManager"
  - type: official
    path: "packages/modules/Profiling/"
  - type: official
    path: "perfetto.dev"
tags:
  - android
  - paper
  - profiling
related_chapters:
  - "13.1"
  - "15.5"
  - "9.1"
  - "8.2"
pipeline_stage: task6_pending
task6_state: revisiting
task6_result: needs-rework
task9_state: pending
task2b_state: fixed
task2b_result: fixed
reviewed_by: openclaw-task6
reviewed_date: 2026-04-19
---

# 14.7 ProfilingManager

ProfilingManager 面向量产设备上的系统级取证。Android 15 提供显式请求，Android 16 支持 ANR、冷启动、异常 CPU 使用等系统事件触发，Android 17 再扩到 OOM、ANOMALY 和 running trace snapshot。System Trace、Heap Profile、Stack Sampling 的结果走 Perfetto，Java Heap Dump 输出 `.hprof`。系统同时处理频率限制、结果文件落盘、脱敏和用户通知。

## 采集类型对照表

| 类型 | 适合问题 | 结果形态 | 参数重点 | 不适合 |
|------|----------|----------|----------|--------|
| `SystemTraceRequestBuilder` | 启动慢、掉帧、输入延迟、ANR 前后时序 | Perfetto trace | `durationMs`、`bufferSizeKb`、`bufferFillPolicy` | 只想看对象引用链 |
| `JavaHeapDumpRequestBuilder` | OOM、泄漏、对象长期滞留 | `.hprof` | `tag` | 观察一段时间内的分配波动 |
| `HeapProfileRequestBuilder` | 内存抖动、分配过密、分配热点不清 | Perfetto heap profile | `durationMs`、`samplingIntervalBytes`、`bufferSizeKb` | 直接确认 GC root 和引用链 |
| `StackSamplingRequestBuilder` | 后台线程 CPU 异常、长任务热点、低开销持续采样 | Perfetto stack samples | `durationMs`、`samplingFrequencyHz` | 分析 VSync、Binder、SurfaceFlinger 的完整时间线 |

选择顺序可以按问题形态来定。

- 启动、卡顿、ANR，优先 `System Trace`
- 泄漏已经比较明确，直接 `Java Heap Dump`
- 内存持续上涨，但还不知道是谁在分配，先做 `Heap Profile`
- 想在几十秒到几分钟范围内找 CPU 热点，用 `Stack Sampling`

## 显式请求的公共骨架

四种 builder 的调用骨架一致，只是请求对象不同。下面代码只保留提交路径，省略上传、重试和清理。

```java
Executor executor = Executors.newSingleThreadExecutor();
CancellationSignal stopSignal = new CancellationSignal();

SystemTraceRequestBuilder builder = new SystemTraceRequestBuilder();
builder.setTag("scroll-jank");
builder.setDurationMs(5_000);
builder.setBufferSizeKb(10_240);
builder.setCancellationSignal(stopSignal);

Tracing.requestProfiling(appContext, builder.build(), executor, result -> {
    if (result.getErrorCode() == ProfilingResult.ERROR_NONE) {
        handleResult(result.getResultFilePath()); // 省略实现
    }
});
```

这段骨架里有几条固定规则。

- `Tracing.requestProfiling()` 只负责提交任务，真正的采集、落盘和脱敏都在后台完成，结果通过 `Consumer<ProfilingResult>` 回调返回
- `executor` 用后台线程，回调里常见操作是上传、压缩和登记 case id
- `tag` 最好直接映射业务场景、回归单号或埋点事件名，后续检索比文件名稳定
- `CancellationSignal` 更适合手动短 trace，Heap Dump 通常让系统自然结束更稳妥
- 显式请求走 Jetpack `Tracing.requestProfiling()`，系统触发的注册入口走平台 `ProfilingManager`

## 四种 RequestBuilder 的差异

### 1. System Trace

System Trace 用来回答时间线问题。卡顿发生在哪一帧，输入到提交之间卡在哪个线程，冷启动慢在 `Application.onCreate()` 还是首帧绘制，这类问题都要看 trace。

```java
SystemTraceRequestBuilder builder = new SystemTraceRequestBuilder();
builder.setTag("cold-start");
builder.setDurationMs(8_000);
builder.setBufferFillPolicy(BufferFillPolicy.RING_BUFFER);
builder.setBufferSizeKb(20_480);
```

`durationMs` 决定窗口长度，`bufferSizeKb` 决定窗口里能留住多少事件。动作持续时间不稳定时，`RING_BUFFER` 更适合保住问题发生前后的近场样本。固定短窗口、又很看重窗口开头时，可以考虑 `FLUSH_FULL`。

打开 Perfetto 后，优先看主线程、`RenderThread`、`Frame Timeline`、`sched`、Binder 和 `am` track。System Trace 的价值在于把系统和 App 放到同一条时间线上。

### 2. Java Heap Dump

Java Heap Dump 用来回答谁还持有对象。结果适合放到 Android Studio Profiler 或 MAT 里看 dominator tree、GC root 和 reference chain。

```java
JavaHeapDumpRequestBuilder builder = new JavaHeapDumpRequestBuilder();
builder.setTag("oom-suspect");
```

这类请求是单点快照，适合页面退出后对象还活着、缓存引用路径过长、OOM 需要回放对象关系的场景。它不负责解释一段时间里的分配节奏。

### 3. Heap Profile

Heap Profile 用来回答内存为什么一直涨。它更像持续观测，适合看分配热点、分配频率和一段时间内的对象 churn。

```java
HeapProfileRequestBuilder builder = new HeapProfileRequestBuilder();
builder.setTag("allocation-churn");
builder.setDurationMs(30_000);
builder.setSamplingIntervalBytes(4096);
builder.setBufferSizeKb(8_192);
```

`samplingIntervalBytes` 越小，样本越密，开销也越高。线上环境一般先从较粗的采样起步，确认热点模块后再缩小采样间隔。还没确定问题落在谁身上时，Heap Profile 往往比 Heap Dump 更容易收窄范围。

### 4. Stack Sampling

Stack Sampling 用来回答 CPU 时间落在哪段代码路径上。它不提供完整系统时间线，但能用更低的成本拉长观察窗口。

```java
StackSamplingRequestBuilder builder = new StackSamplingRequestBuilder();
builder.setTag("bg-cpu");
builder.setDurationMs(60_000);
builder.setSamplingFrequencyHz(100);
```

这类采样适合后台 worker、定时任务、长生命周期线程的热点分析。问题如果和 VSync、输入分发、SurfaceFlinger 合成相关，还是要回到 System Trace。

## Consumer 回调的设计意图

Profiling 请求会跨进程交给系统服务执行，文件生成时间又受到采集时长、写盘和脱敏流程影响。异步回调把请求提交和结果处理拆开，调用线程不会被一个长耗时流程绑住，四种采集类型也能共用一套结果协议。真正需要稳定保存的字段只有三类，`errorCode`、`tag`、`resultFilePath`。

结果通道有两条。

- 显式请求的结果，通过 `requestProfiling(..., callback)` 返回
- 系统触发的结果，通过 `registerForAllProfilingResults(...)` 返回

这两条通道分开管理，显式请求的 callback 收不到 trigger 结果。

## System Triggered Profiling（Android 16+）

ANR、冷启动、异常杀进程这类问题，最有价值的样本往往出现在开发者不在线的时候。trigger 模式解决的就是这个时间点问题。Android 16 开始支持注册系统事件触发器，Android 17 再补 OOM、ANOMALY 和 running trace snapshot。

| 触发器 | 版本 | 适合场景 | 常见结果 |
|--------|------|----------|----------|
| `TRIGGER_TYPE_ANR` | Android 16 | 线上 ANR 取证 | System Trace 快照 |
| `TRIGGER_TYPE_COLD_START` | Android 16 | 冷启动回归 | Stack Sampling + System Trace |
| `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` | Android 16 | 异常 CPU 使用导致被系统杀进程 | Stack Sampling |
| `TRIGGER_TYPE_OOM` | Android 17 | OOM 根因定位 | Java Heap Dump |
| `TRIGGER_TYPE_ANOMALY` | Android 17 | 系统判定的异常行为 | 由异常类型决定 |
| `TRIGGER_TYPE_APP_REQUEST_RUNNING_TRACE` | Android 17 | 获取当前运行中的 trace 快照 | System Trace 快照 |

每个 App 对每种 trigger type 只保留一个注册项，新注册会覆盖旧值。下面代码只保留注册路径。

```java
ProfilingManager pm = context.getSystemService(ProfilingManager.class);
Executor executor = Executors.newSingleThreadExecutor();
pm.registerForAllProfilingResults(executor, result -> {
    if (result.getErrorCode() == ProfilingResult.ERROR_NONE) handleResult(result.getResultFilePath());
});
List<ProfilingTrigger> triggers = new ArrayList<>();
triggers.add(new ProfilingTrigger.Builder(ProfilingTrigger.TRIGGER_TYPE_ANR)
        .setRateLimitingPeriodHours(1).build());
triggers.add(new ProfilingTrigger.Builder(ProfilingTrigger.TRIGGER_TYPE_COLD_START)
        .setRateLimitingPeriodHours(24).build());
pm.addProfilingTriggers(triggers);
```

线上注册前，最好把三件事先定清楚。

- 结果怎么和 case 关联，通常是 `tag`、版本号、设备指纹、回归单号一起上传
- 限流怎么设，ANR/OOM 的预算可以紧一些，冷启动回归一般按天采一条更稳
- 回调里做什么，建议只做轻量登记，把上传、压缩和解析放到后台 worker

## 三个常见使用场景

### 1. 冷启动回归

冷启动问题优先注册 `TRIGGER_TYPE_COLD_START`，按设备和版本做低频采样。回到 Perfetto 时，重点看 `am proc_start`、`ActivityThread.handleBindApplication`、首帧绘制、`reportFullyDrawn()` 附近的时间线。这里的目标不是拿到一份完整日志，而是锁定慢在进程创建、应用初始化还是首屏渲染。

### 2. 滑动卡顿

滑动卡顿更适合手动发起一次 3 到 5 秒的 System Trace。窗口短、定位快，数据量也容易控住。Perfetto 里优先看 Input、主线程、`RenderThread`、`Frame Timeline`。如果问题落在 `RecyclerView` 绑定、图片解码或 Binder 回调，System Trace 会比 Stack Sampling 更直接。

### 3. 线上内存涨高

内存涨高但根因不清时，先做 Heap Profile 找分配热点，再按模块补 Java Heap Dump 看引用链。Android 17 设备可以把 `TRIGGER_TYPE_OOM` 作为兜底样本，至少保证崩溃点附近能留下 `.hprof`。这条路径比在 `OutOfMemoryError` 里临时拼接复杂逻辑稳得多。

## 与其他工具的分工

| 工具 | 更适合的场景 | 局限 |
|------|--------------|------|
| ProfilingManager | 量产设备、线上回归、系统事件触发 | 受版本和 rate limit 约束 |
| Android Studio Profiler | 开发机上的交互式分析 | 很难覆盖真实用户现场 |
| adb / Perfetto CLI | 实验室里的可重复压测和批量脚本化采集 | 需要操作入口，线上设备接入成本高 |
| 第三方 APM SDK | 业务指标、崩溃路径、埋点体系 | 采样能力和隐私责任都要自行承担 |

## 上线前检查清单

- release 配置下不要关闭 rate limiter
- `errorCode`、`tag`、结果文件路径都要落日志或后端元数据
- 回调线程不要做同步压缩、解析和大文件上传
- 结果文件要有清理策略，避免长期堆在应用目录里
- 用户通知、隐私条款和内部合规说明要与实际采集行为一致

## 参考资料

1. **Android Developers, Profiling on Android**  
   https://developer.android.com/guide/topics/profiling

2. **Android SDK Reference, `android.os.ProfilingManager` / `ProfilingTrigger` / `ProfilingResult`**  
   https://developer.android.com/reference/android/os/ProfilingManager

3. **AOSP Profiling Module**  
   `packages/modules/Profiling/`

4. **Perfetto Documentation**  
   https://perfetto.dev/

## 相关章节

- **13.1 Perfetto 简介与演进**，trace 文件格式和基础分析概念
- **15.5 线上性能监控**，线上采样预算、上传流程和告警治理
- **9.1 ANR 设计思想**，ANR 样本和系统触发 profiling 的配合方式
- **8.2 应用启动过程**，冷启动 trace 的关键节点

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **ProfilingManager API（Android 15+）简介**：[已验证: developer.android.com/guide/topics/profiling]
  系统级 profiling API，支持 4 种采集类型，显式请求和系统事件触发分工明确。

- 🔹 **支持的 profiling 类型**：[已验证: developer.android.com]
  `SystemTraceRequestBuilder`、`JavaHeapDumpRequestBuilder`、`HeapProfileRequestBuilder`、`StackSamplingRequestBuilder` 的适用场景、结果形态和参数重点。

- 🔹 **使用方法：requestProfiling() 调用流程**：[已验证: developer.android.com]
  获取 `Context`，创建 `Executor` 和结果回调，构建请求，调用 `Tracing.requestProfiling()`，在回调里处理结果。

- 🔹 **System Triggered Profiling（Android 16+）**：[已验证: developer.android.com]
  通过 `ProfilingTrigger.Builder` 注册系统事件触发器，`registerForAllProfilingResults()` 接收结果。Android 16 覆盖 ANR / COLD_START / KILL_EXCESSIVE_CPU_USAGE，Android 17 扩展到 OOM / ANOMALY / APP_REQUEST_RUNNING_TRACE。

- 🔹 **隐私与安全约束**：[已验证: developer.android.com]
  系统负责限流、脱敏、结果文件管理和用户通知，App 侧需要补齐上传、清理和合规流程。

### 扩展（可选深入）

- 🔸 **线上环境使用实践**：把 tag、版本号、设备指纹和 case id 一起上传，便于回放和聚合分析
- 🔸 **Jetpack vs 平台 API 选择**：显式请求优先 `Tracing.requestProfiling()`，系统触发注册走 `ProfilingManager`
<!-- outline-end -->
