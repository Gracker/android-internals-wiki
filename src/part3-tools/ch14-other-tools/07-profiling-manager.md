---
tags:
  - android
  - paper
  - profiling
---

# ProfilingManager

## 开头：这个工具解决什么问题

在 Android 15 之前，想在真实用户设备上抓取 profiling 数据，开发者需要集成第三方 SDK（侵入性强）、让用户手动触发（数据不真实），或者依赖厂商定制方案（碎片化严重）。更关键的问题是——ANR、冷启动慢、OOM 这些最难复现的问题，发生时开发者往往不在场，错过了最有价值的诊断时机。

Android 15 引入的 ProfilingManager 从系统层面解决了这个问题。它让 App 可以**在量产设备上以最小侵入的方式收集性能数据**，系统自动处理脱敏、频率限制和存储管理。从 Android 16 开始，还支持系统事件触发的自动采集——ANR 发生时、冷启动时、OOM 时，系统会自动抓取对应的 profiling 数据，开发者只需要注册一个触发器就能收到结果。

换一种说法：ProfilingManager 把"开发环境容易分析，生产环境无法抓数据"这个长期矛盾，从系统层面解决了。

### 从 API 到实战：这一节覆盖什么

我们接下来分三个层面讲 ProfilingManager。首先是四种 profiling 类型的 API 调用方式——System Trace、Java Heap Dump、Heap Profile、Stack Sampling，每种都有对应的 RequestBuilder，用法大同小异但参数各有侧重。然后是 Android 16 引入的系统事件触发机制，这是 ProfilingManager 最有价值的部分：注册触发器后，ANR、冷启动、OOM 等事件发生时系统自动采集，开发者不需要提前埋点。最后是 Android 17 新增的能力扩展。

所有采集结果都以 Perfetto 格式输出，直接在 Perfetto UI 中分析，不需要额外的格式转换工具。

## 基本使用：从零到跑通

### 前置准备

ProfilingManager 的 API 有两个层面：平台原生 API（`android.os.ProfilingManager`）和 Jetpack 封装（`androidx.tracing.perfetto`）。Google 推荐使用 Jetpack 封装以获得更好的兼容性和更简洁的 API。下面的示例以 Jetpack API 为主。

添加依赖：

```kotlin
dependencies {
    implementation("androidx.tracing:tracing:1.3.0")
    implementation("androidx.core:core:1.18.0")
}
```

### 第一步：发起一次 System Trace

System Trace 是最常用的 profiling 类型，它记录系统各子系统（调度、渲染、输入、电源等）的时间线，适用于延迟分析和通用性能调试。

```java
import android.content.Context;
import android.os.CancellationSignal;
import android.util.Log;

import androidx.tracing.perfetto.Tracing;
import androidx.tracing.perfetto.ProfilingResult;
import androidx.tracing.perfetto.SystemTraceRequestBuilder;
import androidx.tracing.perfetto.core.concurrent.BufferFillPolicy;

import java.util.concurrent.Executor;
import java.util.concurrent.Executors;
import java.util.function.Consumer;

public class SystemTraceExample {

    private static final String TAG = "Profiling";

    public void startSystemTrace(Context context) {
        // 1. 用非 UI 线程的 Executor 接收结果，避免在回调中做 I/O 导致 ANR
        Executor executor = Executors.newSingleThreadExecutor();

        // 2. 定义结果回调
        Consumer<ProfilingResult> resultCallback = profilingResult -> {
            if (profilingResult.getErrorCode() == ProfilingResult.ERROR_NONE) {
                Log.d(TAG, "Trace saved to: " + profilingResult.getResultFilePath());
                // 这里可以上传到后端、用 adb pull 拉出、或在本地分析
            } else {
                Log.e(TAG, "Profiling failed: " + profilingResult.getErrorMessage()
                        + " (code=" + profilingResult.getErrorCode() + ")");
            }
        };

        // 3. 构建请求
        CancellationSignal stopSignal = new CancellationSignal();
        SystemTraceRequestBuilder requestBuilder = new SystemTraceRequestBuilder();
        requestBuilder.setTag("MyAppOperation");           // 标记这次采集，便于后续识别
        requestBuilder.setDurationMs(10_000);               // 采集 10 秒
        requestBuilder.setBufferFillPolicy(
            BufferFillPolicy.RING_BUFFER);                  // 环形缓冲，满时覆盖旧数据
        requestBuilder.setBufferSizeKb(20_480);             // 20MB 缓冲区
        requestBuilder.setCancellationSignal(stopSignal);   // 可随时取消

        // 4. 发起采集
        Tracing.requestProfiling(
            context,                    // Application Context
            requestBuilder.build(),     // 构建好的请求
            executor,                   // 结果回调线程
            resultCallback              // 结果处理器
        );

        // 如果需要提前结束，调用：
        // stopSignal.cancel();
    }
}
```

这里有几个关键点需要注意：

**`Consumer<ProfilingResult>` 是回调模式，不是轮询模式。** 调用 `requestProfiling()` 后方法立即返回，profiling 在后台运行，完成后系统通过 Consumer 回调通知结果。不存在 `getStatus()` 之类的轮询接口——这是与原始草稿中描述的最大区别。

**`CancellationSignal` 用来主动停止采集。** 如果不设置 `setDurationMs()`，系统会使用默认时长。设置了 `stopSignal` 后，可以在任意时刻调用 `stopSignal.cancel()` 提前结束采集。

**必须使用非 UI 线程的 Executor。** 结果回调中可能涉及文件 I/O（读取 trace 文件、上传到服务器），在主线程执行会触发 ANR——正好是我们要分析的问题。

### 第二步：请求 Heap Dump 和 Heap Profile

当怀疑内存泄漏时，Heap Dump 是第一选择；当需要分析内存分配频率和大小时，用 Heap Profile。

```java
import androidx.tracing.perfetto.JavaHeapDumpRequestBuilder;
import androidx.tracing.perfetto.HeapProfileRequestBuilder;

// —— Heap Dump：捕获某一时刻的堆快照 ——
public void requestHeapDump(Context context) {
    Executor executor = Executors.newSingleThreadExecutor();

    Consumer<ProfilingResult> callback = result -> {
        if (result.getErrorCode() == ProfilingResult.ERROR_NONE) {
            // result.getResultFilePath() 指向一个 .hprof 文件
            // 可以用 Android Studio Profiler 或 jhat 打开分析
            Log.d(TAG, "Heap dump saved: " + result.getResultFilePath());
        }
    };

    JavaHeapDumpRequestBuilder builder = new JavaHeapDumpRequestBuilder();
    builder.setTag("OOM-Investigation");

    Tracing.requestProfiling(context, builder.build(), executor, callback);
}

// —— Heap Profile：持续记录分配行为 ——
public void requestHeapProfile(Context context) {
    Executor executor = Executors.newSingleThreadExecutor();

    Consumer<ProfilingResult> callback = result -> {
        if (result.getErrorCode() == ProfilingResult.ERROR_NONE) {
            Log.d(TAG, "Heap profile saved: " + result.getResultFilePath());
        }
    };

    HeapProfileRequestBuilder builder = new HeapProfileRequestBuilder();
    builder.setTag("AllocationTracking");
    builder.setDurationMs(30_000);               // 采集 30 秒
    builder.setBufferSizeKb(8_192);              // 8MB 缓冲区
    builder.setSamplingIntervalBytes(4096);       // 每 4KB 分配采样一次

    Tracing.requestProfiling(context, builder.build(), executor, callback);
}
```

**Heap Dump 和 Heap Profile 的区别**：Dump 是某一时刻的完整快照（适合找泄漏），Profile 是一段时间内的分配记录（适合分析分配频率和热点）。

### 第三步：请求 Stack Sampling

Stack Sampling 以固定频率采集调用栈，适用于理解代码执行路径和找出耗时函数，性能开销比 System Trace 小。

```java
import androidx.tracing.perfetto.StackSamplingRequestBuilder;

public void requestStackSampling(Context context) {
    Executor executor = Executors.newSingleThreadExecutor();

    Consumer<ProfilingResult> callback = result -> {
        if (result.getErrorCode() == ProfilingResult.ERROR_NONE) {
            Log.d(TAG, "Stack samples saved: " + result.getResultFilePath());
        }
    };

    StackSamplingRequestBuilder builder = new StackSamplingRequestBuilder();
    builder.setTag("ColdPathAnalysis");
    builder.setDurationMs(60_000);               // 采样 60 秒
    builder.setSamplingFrequencyHz(100);         // 每秒 100 次采样

    Tracing.requestProfiling(context, builder.build(), executor, callback);
}
```

## System Triggered Profiling（Android 16+）

前面讲的四种 RequestBuilder 都需要手动调用 `requestProfiling()`——这意味着开发者必须提前知道"什么时候该采集"。但 ANR、OOM、冷启动慢这些问题恰恰是不可预测的，发生时开发者往往不在场。Android 16 引入的 System Triggered Profiling 从根本上改变了这个局面：注册一个触发器，当对应系统事件发生时，系统自动采集并回调结果，整个过程不需要 App 代码参与。

### 注册 ANR 触发器

```java
import android.app.Application;
import android.os.ProfilingManager;
import android.os.ProfilingResult;
import android.os.ProfilingTrigger;
import android.util.Log;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Executor;
import java.util.concurrent.Executors;
import java.util.function.Consumer;

public class MyApplication extends Application {

    private static final String TAG = "ANRProfiling";

    @Override
    public void onCreate() {
        super.onCreate();
        setupANRTrigger();
    }

    private void setupANRTrigger() {
        ProfilingManager pm = getSystemService(ProfilingManager.class);
        if (pm == null) {
            Log.w(TAG, "ProfilingManager not available (requires Android 15+)");
            return;
        }

        // 1. 注册全局结果监听器
        //    这是接收系统触发 profiling 结果的唯一方式
        Executor executor = Executors.newSingleThreadExecutor();
        Consumer<ProfilingResult> resultCallback = result -> {
            if (result.getErrorCode() == ProfilingResult.ERROR_NONE) {
                Log.d(TAG, "ANR trace captured: " + result.getResultFilePath());
                // 上传到后端分析平台
            } else {
                Log.e(TAG, "ANR trace failed: " + result.getErrorMessage());
            }
        };
        pm.registerForAllProfilingResults(executor, resultCallback);

        // 2. 定义 ANR 触发器
        List<ProfilingTrigger> triggers = new ArrayList<>();
        ProfilingTrigger anrTrigger = new ProfilingTrigger.Builder(
                ProfilingTrigger.TRIGGER_TYPE_ANR)
            .setRateLimitingPeriodHours(1)   // 每小时最多采集一次
            .build();
        triggers.add(anrTrigger);

        // 3. 注册触发器
        pm.addProfilingTriggers(triggers);
        Log.d(TAG, "ANR profiling trigger registered");
    }
}
```

**注意**：`registerForAllProfilingResults()` 是接收系统触发结果的唯一途径。`requestProfiling()` 的 Consumer 只接收显式请求的结果，不接收系统触发的结果。这两个 API 的结果通道是独立的。

### 可用的触发器类型

| 触发器 | 引入版本 | 触发时机 | 系统采集的数据类型 |
|--------|---------|---------|------------------|
| `TRIGGER_TYPE_ANR` | Android 16 | ANR 被确认后、系统尝试杀进程之前 | System Trace 快照 |
| `TRIGGER_TYPE_COLD_START` | Android 16 | 冷启动时（`ApplicationStartInfo.getStartType() == START_TYPE_COLD`） | Stack Sampling + System Trace |
| `TRIGGER_TYPE_OOM` | Android 17 | App 抛出 `OutOfMemoryError` 时 | Java Heap Dump |
| `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` | Android 16 | 因异常高 CPU 消耗被系统杀死时 | Stack Sampling |
| `TRIGGER_TYPE_ANOMALY` | Android 17 | 系统检测到 App 行为异常（如兼容性问题）时 | 视异常类型而定 |
| `TRIGGER_TYPE_APP_REQUEST_RUNNING_TRACE` | Android 17 | App 主动调用 `requestRunningSystemTrace()` 请求当前正在运行的 trace 快照 | System Trace 快照 |

[待验证: Android 17 ANOMALY 触发器的子类型（如 ANOMALY_APP_COMPAT）的具体触发条件和返回数据类型]

### 同时注册多个触发器

```java
private void setupMultipleTriggers() {
    ProfilingManager pm = getSystemService(ProfilingManager.class);
    if (pm == null) return;

    Executor executor = Executors.newSingleThreadExecutor();
    pm.registerForAllProfilingResults(executor, result -> {
        // 通过 result 的触发器类型区分不同来源
        Log.d(TAG, "Trigger result: tag=" + result.getTag()
                + " file=" + result.getResultFilePath());
    });

    List<ProfilingTrigger> triggers = new ArrayList<>();
    triggers.add(new ProfilingTrigger.Builder(ProfilingTrigger.TRIGGER_TYPE_ANR)
            .setRateLimitingPeriodHours(1).build());
    triggers.add(new ProfilingTrigger.Builder(ProfilingTrigger.TRIGGER_TYPE_COLD_START)
            .setRateLimitingPeriodHours(6).build());

    pm.addProfilingTriggers(triggers);
}
```

**规则**：每个 App 对每种触发器类型只能注册一个。注册同类型的新触发器会覆盖旧的。

### Android 17 新增能力

Android 17 在触发器之外还新增了 `requestRunningSystemTrace()` 方法，让 App 可以获取当前正在运行的系统 trace 的快照，适用于在线上环境中获取即时性能数据。

[待验证: `requestRunningSystemTrace()` 的确切签名和调用方式需对照 AOSP android-17 分支确认]

## 实战示例

### 案例 1：线上冷启动监控

**场景**：App 的冷启动时间在部分设备上超标，需要收集真实用户的冷启动 trace 来分析瓶颈。

```java
public class ColdStartMonitor {

    public void setup(Context context) {
        ProfilingManager pm = context.getSystemService(ProfilingManager.class);
        if (pm == null) return;

        Executor executor = Executors.newSingleThreadExecutor();

        // 注册全局结果接收器
        pm.registerForAllProfilingResults(executor, result -> {
            if (result.getErrorCode() != ProfilingResult.ERROR_NONE) return;

            // 将 trace 文件上传到后端
            uploadTrace(result.getResultFilePath(),
                        "cold-start-" + result.getTag());
        });

        // 注册冷启动触发器，每天最多采集一次
        List<ProfilingTrigger> triggers = new ArrayList<>();
        triggers.add(new ProfilingTrigger.Builder(
                ProfilingTrigger.TRIGGER_TYPE_COLD_START)
            .setRateLimitingPeriodHours(24)
            .build());

        pm.addProfilingTriggers(triggers);
    }

    private void uploadTrace(String filePath, String name) {
        // 上传逻辑，后续在 Perfetto UI 或内部平台分析
        // 冷启动 trace 中重点看：
        // - am proc_start -> Activity.onCreate -> onFullyDrawn 的完整时间线
        // - Application.onCreate() 中的初始化耗时
        // - ContentView measure/layout/draw 的首帧时间
    }
}
```

**在 Perfetto 中的表现**：

[图：冷启动 System Triggered Profiling 在 Perfetto 中捕获的 trace，标注 Activity 启动、View 创建、首次绘制等关键时间节点]

冷启动的 trace 在 Perfetto 中对应 `am` track（ActivityManager 相关操作）和主线程 track。重点关注从 `ActivityThread.handleBindApplication` 到 `Activity.onWindowFocusChanged` 的完整链路。

### 案例 2：按需采集滑动卡顿的 System Trace

**场景**：用户反馈列表滑动卡顿，需要在特定操作时手动触发一次短暂的 trace。

```java
public class JankTraceCollector {

    private CancellationSignal currentSignal;

    public void captureJankTrace(Context context) {
        Executor executor = Executors.newSingleThreadExecutor();

        Consumer<ProfilingResult> callback = result -> {
            if (result.getErrorCode() == ProfilingResult.ERROR_NONE) {
                Log.d(TAG, "Jank trace saved: " + result.getResultFilePath());
                analyzeJankTrace(result.getResultFilePath());
            }
        };

        currentSignal = new CancellationSignal();
        SystemTraceRequestBuilder builder = new SystemTraceRequestBuilder();
        builder.setTag("ScrollJank");
        builder.setDurationMs(5_000);               // 只采 5 秒，够捕捉一轮滑动
        builder.setBufferSizeKb(10_240);            // 10MB
        builder.setCancellationSignal(currentSignal);

        Tracing.requestProfiling(context, builder.build(), executor, callback);
    }

    // 如果用户停止滑动且已拿到足够数据，可以提前结束
    public void stopCapture() {
        if (currentSignal != null) {
            currentSignal.cancel();
            currentSignal = null;
        }
    }

    private void analyzeJankTrace(String filePath) {
        // 在 Perfetto UI 中打开后重点看：
        // - Input track：触摸事件到 VSync-app 的时间
        // - RenderThread track：DrawOp 耗时
        // - Frame Timeline track：每帧的实际 vs 预期呈现时间
    }
}
```

### 案例 3：OOM 时的 Heap Dump 自动采集

**场景**：线上出现 OOM 崩溃，堆栈信息不足以定位根因，需要 OOM 发生时的完整堆快照。

```java
public class OOMMonitor {

    public void setup(Context context) {
        ProfilingManager pm = context.getSystemService(ProfilingManager.class);
        if (pm == null) return;

        Executor executor = Executors.newSingleThreadExecutor();

        pm.registerForAllProfilingResults(executor, result -> {
            if (result.getErrorCode() == ProfilingResult.ERROR_NONE) {
                // result.getResultFilePath() 是 .hprof 文件
                // 上传后用 Android Studio Profiler 或 MAT 分析
                uploadToServer(result.getResultFilePath());
            }
        });

        List<ProfilingTrigger> triggers = new ArrayList<>();
        // Android 17+ 支持 OOM 触发器
        triggers.add(new ProfilingTrigger.Builder(
                ProfilingTrigger.TRIGGER_TYPE_OOM)
            .setRateLimitingPeriodHours(1)
            .build());

        pm.addProfilingTriggers(triggers);
    }
}
```

**注意**：`TRIGGER_TYPE_OOM` 从 Android 17 才开始支持。对于 Android 16 及以下设备，可以在 `try-catch OutOfMemoryError` 后手动调用 `JavaHeapDumpRequestBuilder` 来实现类似效果。

## 与其他工具的对比

用 ProfilingManager 之前，性能数据采集主要依赖三种方式：Android Studio Profiler（开发机专用）、`atrace`/Systrace（命令行，需要物理连接或 root）、第三方 APM SDK（侵入性强，增加包体积）。

| 维度 | ProfilingManager | Android Studio Profiler | Systrace/`atrace` | 第三方 SDK |
|------|-----------------|------------------------|---------------------|------------|
| **使用环境** | 量产设备 | 开发机/模拟器 | 开发机/root 设备 | 量产设备 |
| **触发方式** | API 调用 + 系统事件 | 手动操作 | 命令行 | API 调用 |
| **数据真实度** | 高（真实用户场景） | 中（调试器可能影响行为） | 高（但需要物理连接） | 高 |
| **包体积影响** | 无（系统 API） | 无 | 无 | 增加 SDK 大小 |
| **隐私处理** | 自动脱敏其他 App | 无需脱敏 | 需手动处理 | 各 SDK 不同 |
| **性能开销** | 低（有 rate limiter） | 中 | 低 | 取决于实现 |
| **数据格式** | Perfetto | 自有格式 | Perfetto/自定义 | 各 SDK 不同 |
| **最低版本** | Android 15（触发器 16+） | 全版本 | Android 4.3+ | 各 SDK 不同 |

[待补充: ProfilingManager 在量产设备上的实际性能开销实测数据（CPU 占用、内存增量、对帧率的影响）]

## 常见问题与使用技巧

### Rate Limiter

系统内置 rate limiter 限制 App 的 profiling 频率。连续快速调用 `requestProfiling()` 可能被拒绝，`ProfilingResult` 的 `errorCode` 会指示 rate limit 错误。触发器也有独立的 rate limit，通过 `setRateLimitingPeriodHours()` 控制。

本地调试时可以临时关闭 rate limiter：

```bash
# 关闭 rate limiter（仅用于调试，不影响量产设备）
adb shell setprop persist.debug.profiler.rate_limiter 0
# [待验证: 此 setprop 属性名需对照 AOSP ProfilingService 源码确认]
```

### 结果文件处理

采集完成后，`ProfilingResult.getResultFilePath()` 返回文件在设备上的路径。这个文件位于 App 的内部存储目录中。

```bash
# 通过 adb 拉取
adb pull /data/user/0/com.your.app/files/profiling/trace_file.pftrace ./
```

也可以在 Consumer 回调中直接读取文件内容并上传到后端。

### 每个 Builder 的关键参数

| Builder | 关键参数 | 说明 |
|---------|---------|------|
| `SystemTraceRequestBuilder` | `setDurationMs()` | 采集时长，默认由系统决定 |
| | `setBufferFillPolicy()` | `RING_BUFFER`（环形覆盖）或 `FLUSH_FULL`（满了就停） |
| | `setBufferSizeKb()` | 缓冲区大小 |
| | `setTag()` | 标记，用于识别结果 |
| `JavaHeapDumpRequestBuilder` | `setTag()` | 标记 |
| `HeapProfileRequestBuilder` | `setDurationMs()` | 采集时长 |
| | `setSamplingIntervalBytes()` | 分配采样间隔（字节数） |
| | `setBufferSizeKb()` | 缓冲区大小 |
| `StackSamplingRequestBuilder` | `setDurationMs()` | 采样时长 |
| | `setSamplingFrequencyHz()` | 采样频率 |
| | `setBufferSizeKb()` | 缓冲区大小 |

### Jetpack vs 平台 API

Jetpack 封装（`androidx.tracing.perfetto`）在平台 API（`android.os.ProfilingManager`）之上提供了更简洁的调用方式——`Tracing.requestProfiling(context, request, executor, callback)`，并自动处理版本兼容。对于 Android 15 以下的设备，Jetpack 会优雅降级（通常返回错误码）。推荐所有场景都使用 Jetpack 封装。

### 隐私合规

- 采集的数据自动脱敏，只包含调用方 App 的信息
- 大部分情况下，采集开始时系统会显示用户可见的通知
- 不需要额外声明权限（TRACE 权限由系统自动管理）
- 通过 `addProfilingTriggers()` 注册的触发器，每次触发采集也会通知用户

## 参考资料

### 官方文档

1. **Android Developers — ProfilingManager API Guide**
   - https://developer.android.com/guide/topics/profiling
   - API 使用指南、RequestBuilder 详解、代码示例

2. **Android Developers Blog — System Triggered Profiling**
   - https://android-developers.googleblog.com/
   - 系统触发 profiling 的设计理念和触发器类型说明

3. **AOSP — Profiling 模块源码**
   - 路径：`packages/modules/Profiling/`
   - 关键文件：
     - `framework/java/android/os/ProfilingManager.java`
     - `framework/java/android/os/ProfilingResult.java`
     - `framework/java/android/os/ProfilingTrigger.java`
     - `framework/java/android/os/SystemTraceRequestBuilder.java`（及其他 RequestBuilder）
     - `service/java/android/profiling/ProfilingService.java`

4. **Perfetto 官方文档**
   - https://perfetto.dev/
   - Trace 文件格式说明、分析工具使用

### 相关章节

- **13.1 Perfetto 简介与演进** — Trace 文件格式和基础分析概念
- **15.5 线上性能监控** — 生产环境的性能监控方法论
- **9.1 ANR 设计思想** — ANR 触发机制与 ProfilingManager ANR 触发器的配合使用
- **8.2 应用启动过程** — 冷启动 trace 中的关键时间节点分析

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **ProfilingManager API（Android 15+）简介**：[已验证: developer.android.com/guide/topics/profiling]
  系统级 profiling API，支持 4 种采集类型（System Trace / Java Heap Dump / Heap Profile / Stack Sampling），通过 RequestBuilder 模式构建请求，Consumer<ProfilingResult> 回调接收结果。Jetpack 封装推荐使用。

- 🔹 **支持的 profiling 类型**：[已验证: developer.android.com]
  - SystemTraceRequestBuilder：系统级 trace，延迟分析和性能调试
  - JavaHeapDumpRequestBuilder：堆内存快照，检测内存泄漏
  - HeapProfileRequestBuilder：堆分配记录，内存优化
  - StackSamplingRequestBuilder：调用栈采样，代码执行路径分析

- 🔹 **使用方法：requestProfiling() 调用流程**：[已验证: developer.android.com]
  获取 Context -> 创建 Executor + Consumer<ProfilingResult> -> 用 RequestBuilder 构建请求 -> 调用 Tracing.requestProfiling(context, request, executor, callback) -> 回调中处理结果。CancellationSignal 可主动取消。

- 🔹 **System Triggered Profiling（Android 16+）**：[已验证: developer.android.com, android-developers.googleblog.com]
  通过 ProfilingTrigger.Builder 注册系统事件触发器，registerForAllProfilingResults() 接收结果。支持 ANR / COLD_START / KILL_EXCESSIVE_CPU_USAGE（Android 16）及 OOM / ANOMALY / APP_REQUEST_RUNNING_TRACE（Android 17）。

- 🔹 **隐私与安全约束**：[已验证: developer.android.com]
  自动数据脱敏、rate limiter 限制频率、用户可见通知、无需额外权限声明。

### 扩展（可选深入）

- 🔸 **线上环境使用实践**：设置合理 rate limit、优先关键路径触发器、结合崩溃数据关联分析
- 🔸 **Jetpack vs 平台 API 选择**：Jetpack 提供版本兼容和更简洁的 API，推荐所有场景使用
<!-- outline-end -->
