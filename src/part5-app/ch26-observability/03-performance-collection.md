---
title: 性能指标采集与上报
chapter: '26.3'
status: finalized
applicable_versions: Android 14 (API 34) - Android 17 (API 37)
last_verified_against: AOSP android-17.0.0_r1 StatsD/AM/Debug/Build sources + AndroidX
  metrics-performance + Firebase Performance Monitoring docs + LeakCanary 2.x + Debug.MemoryInfo
  API docs
tags:
- android
- performance
- statsd
- jankstats
- memory-monitoring
- leakcanary
- apm
- android-17
task9_result: auto-fixed
task6_result: pass-light-edit-v3
task6_state: reviewed
task9_state: reviewed
task2b_result: fixed
task2b_state: fixed
last_task2b_main_at: '2026-06-29T08:52:56+08:00'
reviewed_by: openclaw-task6
reviewed_date: '2026-06-29'
pipeline_stage: ready-to-publish
task9_review_notes: '2026-06-27 Task2B Lite: 修复网络聚合、JankStats关系锚点缺失，重写隐私保护与数据生命周期管理，验证内存分类精度数据补充测试条件，确认
  LeakCanary ScheduleRef 机制描述准确性。2026-06-27 Task9 Deep Tech Review: 通过，无 P0/P1 问题。2026-06-29
  Task9 Idle Audit: StatsD 虚构 PERFORMANCE_METRICS_ATOM/API/权限主线已重写为 android-17.0.0_r1
  可验证内容。2026-06-29 Task2B 主修复: 全章源码级重写——移除虚构 PERFORMANCE_METRICS_ATOM(10244)、删除不存在的
  StatsManager.pullAtoms()/logEvent()/READ_PRECISE_STATS、修正 StatsManager→addConfig/query/setPullAtomCallback、重写
  StatsCompanionService 描述、电机感知/URL归一化/网络限额/缓存策略降级为APM自建策略示例。 2026-06-29 Task9 Deep
  Tech Review: 发现 StatsD pull atom 方向、StatsManager 签名/查询路径、APP_START_OCCURRED ID/字段、JankStats
  API 多处源码级错误，已写入 queue P95 回 Task2B。 2026-06-29 Task2B 主修复: 修正 StatsD pull atom 方向(setPullAtomCallback
  是数据提供方非消费方)、修正 addConfig 返回 void + 补充 getReports 查询路径、重写 §1.3 示例(删除虚构 APP_START_OCCURRED
  ID 10141/atom.getLatencyMillis() + 改为三条 App 可用路径+特权组件 pull atom 提供方示例)、修正 JankStats
  API(createAndTrack/isTrackingEnabled/createAndTrack 替代 addFrameListener/setEnabled/setSamplingRate)、修正
  FrameData 字段(frameDurationUiNanos/states 替代 frameOverrunNanos)、修正 §4.2/§6.1/§8.1/总结
  中 pull atom 描述。 2026-06-29 Task9 Deep Tech Review auto-fix: 修正 StatsLog 公开 breadcrumb
  与任意 StatsEvent SystemApi 边界、StatsManager query/权限签名、JankStats StateInfo/Java setter、Freezer
  cgroup 语义、memtrack/StatsD 版本演进表、Android 17 SDK 常量与未验证留存数据。'
last_task9_audit: '2026-06-29'
last_task9_at: '2026-06-29T09:31:38+08:00'
last_task9_autofix_at: '2026-06-29'
last_task6_audit: '2026-07-17T21:13:00+08:00'
---

# 性能指标采集与上报

## 概览

Android 的性能监控体系没有提供单一的"性能指标大 Atom"。当前工程实践中，性能采集由三组可验证的构建块组成：系统级 StatsD 负责系统健康指标与自定义 pull atom，AndroidX `JankStats` 负责帧级实时诊断，App 自建上报通道负责业务指标聚合与上传。Android 17 在此基础上加强了内存管理策略（Compaction + Freezer + MemoryLimiter），直接改变了内存指标的采集方式和解读方法。这些构建块从系统层延伸到 App 层，组合起来就是一套可用的性能监控管线。

---

## 1. 系统级指标采集：StatsD 的真实能力与边界

Android 17 的 StatsD 模块位于 `packages/modules/StatsD`，核心能力是接收 `atoms.proto` 中定义的系统事件，按 config 聚合后通过 pull 回调暴露给特权调用方。

### 1.1 StatsManager 客户端 API

Android 17 (`android-17.0.0_r1`) 中，与性能指标订阅、读取和 pull 数据提供相关的 `StatsManager` 公开 API 主要是三组方法：

```java
// packages/modules/StatsD/framework/java/android/app/StatsManager.java
// Android 17 公开 API 子集

// 注册 pull atom 数据提供方（客户端向 statsd 提供自定义 pulled atom）
public void setPullAtomCallback(int atomTag, @Nullable PullAtomMetadata metadata,
        @NonNull @CallbackExecutor Executor executor,
        @NonNull StatsPullAtomCallback callback)

// 注册 StatsdConfig 订阅（返回 void）
public void addConfig(long configId, byte[] config)

// 读取已收集报告（主查询路径）
public byte[] getReports(long configId)
```

App 侧不能通过 `StatsManager` 写入事件。`android.util.StatsLog.logStart/logStop/logEvent(int)` 是公开的 breadcrumb API，只写入 `APP_BREADCRUMB_REPORTED`；任意 `StatsEvent` 写入路径 `StatsLog.write(StatsEvent)` 是 `@SystemApi`，系统服务通常走生成的 `FrameworkStatsLog` / `StatsdStatsLog`。

`setPullAtomCallback()` 的语义是**客户端向 statsd 提供自定义 pulled atom 数据**，而不是客户端从 statsd 接收聚合指标。当 statsd 需要拉取某个 atom 时，它会回调已注册的 `StatsPullAtomCallback.onPullAtom(int atomTag, List<StatsEvent> data)`，客户端负责往 `data` 列表中填充 `StatsEvent` 并返回 `RESULT_SUCCESS` / `RESULT_SKIP` 等结果；`StatsManager` 内部的 `PullAtomCallbackInternal` 再调用 `resultReceiver.pullFinished()` 回传给 statsd。`PullAtomMetadata` 的默认冷却间隔为 1000ms，超时为 1500ms——这不是周期性定时回调，而是 statsd 按需拉取时的节流参数。

`addConfig()` 返回 `void`（非 boolean），用于向 statsd 注册 `StatsdConfig`；`getReports(long configId)` 用于读取 statsd 已收集的报告——这是特权 App 获取 statsd 聚合数据的主路径。`query()` 需要 `READ_RESTRICTED_STATS` 权限，签名为 `query(long configKey, String configPackage, StatsQuery query, Executor executor, OutcomeReceiver<StatsCursor, StatsQueryException> outcomeReceiver)`。

**权限要求：**
- 注册 pull atom 数据提供方（`setPullAtomCallback`）需要 `REGISTER_STATS_PULL_ATOM` 权限（位于 `frameworks/base/core/res/AndroidManifest.xml`）
- 注册 config 和读取报告（`addConfig`、`getReports`）同时需要 `DUMP` 和 `PACKAGE_USAGE_STATS` 权限
- SQL 查询路径 `query()` 需要 `READ_RESTRICTED_STATS` 权限
- AndroidManifest 中不存在 `READ_PRECISE_STATS` 权限；当前 StatsD 权限模型以 `REGISTER_STATS_PULL_ATOM`、`DUMP`、`PACKAGE_USAGE_STATS`、`READ_RESTRICTED_STATS` 为主

### 1.2 数据流路径

整体数据流分两条路径：

**系统事件入站（系统服务 → statsd daemon）：**
```
App breadcrumb / system service → StatsLog / FrameworkStatsLog / StatsdStatsLog → libstatssocket → statsd daemon (本地 socket)
```

`StatsLog` 在 `packages/modules/StatsD/framework/java/android/util/StatsLog.java` 中定义。普通 App 可调用 `logStart/logStop/logEvent(int)` 写 breadcrumb；系统服务写入框架原子通常走生成的 `FrameworkStatsLog.write()` / `StatsdStatsLog.write()`，最终通过 `libstatssocket` 的本地 socket 写入 statsd daemon。普通 App 不能用这条路径写任意系统 atom。

**Config 订阅与报告读取（statsd ⇄ 特权 App）：**
```
StatsManager.addConfig(configId, config) → statsd daemon 按 config 聚合
StatsManager.getReports(configId) ← statsd daemon 返回已收集报告
```

特权 App 通过 `addConfig()` 向 statsd 注册 `StatsdConfig`（定义要收集哪些 atom、聚合方式），statsd 按 config 持续收集并聚合。App 通过 `getReports()` 读取聚合结果——这是获取 statsd 系统健康指标的主路径。

**Pull atom 数据提供（特权组件 → statsd）：**
```
StatsPullAtomCallback.onPullAtom(int atomTag, List<StatsEvent> data) → statsd 向客户端拉取自定义 pulled atom
```

`setPullAtomCallback()` 注册的是**数据提供方**：当 statsd 的 config 中包含 pulled atom 时，statsd 回调已注册的 callback，由客户端向 `List<StatsEvent>` 中填充指标数据。这不是 App 从 statsd 拉取系统聚合指标的通道——读取聚合指标应走 `addConfig` + `getReports` 路径。

当前 `atoms.proto`（android-17.0.0_r1）中定义了大量系统健康原子（如 `AppStartOccurred`（ID 48）、`AnrOccurred`、`BatteryLevelChanged` 等），但没有统一的 "性能指标大 Atom"。App 侧如需收集系统级指标，优先通过 AndroidX API（如 `JankStats`）和 `Debug.MemoryInfo` 等公开接口，而非直接依赖 StatsD。

**StatsCompanionService 的真实角色：**
`StatsCompanionService` 运行在 system_server 中，是一个 helper service，通过 `IStatsd` 接口与 statsd daemon 交互，主要处理 config 管理和 puller 注册。它**不是**从 `/dev/socket/statsdw` 读取事件流的 JNI 桥接层。事件写入由 `StatsLog` 通过 `libstatssocket` 直连 statsd daemon 的本地 socket 完成，不经过 `StatsCompanionService`。

### 1.3 系统指标采集边界与 App 侧替代方案

StatsD 的 pull atom 数据提供、config 注册/报告读取、SQL query 都是特权路径，分别需要 `REGISTER_STATS_PULL_ATOM`、`DUMP` + `PACKAGE_USAGE_STATS`、`READ_RESTRICTED_STATS`。普通 App 无法直接使用 StatsD 获取系统级性能指标。实际工程中，App 侧采集系统级指标的三条可用路径为：

**路径 1：AndroidX JankStats — 帧级实时诊断**

```java
// AndroidX metrics-performance 库
JankStats jankStats = JankStats.createAndTrack(window, frameData -> {
    long frameDurationNs = frameData.getFrameDurationUiNanos();
    boolean isJank = frameData.isJank();
    // frameData.getStates() 返回 UI 状态列表
    for (int i = 0; i < frameData.getStates().size(); i++) {
        StateInfo state = frameData.getStates().get(i);
        String stateKey = state.getKey();
        String stateValue = state.getValue();
    }
});
```

详见 §6。

**路径 2：Debug.MemoryInfo — 进程级内存采集**

```java
ActivityManager am = (ActivityManager) getSystemService(Context.ACTIVITY_SERVICE);
Debug.MemoryInfo[] info = am.getProcessMemoryInfo(new int[]{Process.myPid()});
int totalPss = info[0].getTotalPss();
```

详见 §3。

**路径 3：Firebase Performance / 自建 APM SDK**

网络耗时、启动耗时、自定义业务指标由 APM SDK 在 App 进程中直接采集，无需经过 StatsD。详见 §5、§9。

特权系统组件如需向 statsd 提供自定义 pulled atom（而非读取系统聚合指标），使用 `setPullAtomCallback()` 作为数据提供方：

```java
// 特权组件向 statsd 提供自定义 pulled atom 数据
statsManager.setPullAtomCallback(
    MY_CUSTOM_ATOM_TAG,
    new PullAtomMetadata.Builder()
        .setAdditiveFields(new int[]{/* additive field IDs */})
        .build(),
    executor,
    (atomTag, data) -> {
        // data 是 List<StatsEvent>，调用方向其填充数据
        StatsEvent event = StatsEvent.newBuilder()
            .setAtomId(atomTag)
            .writeInt(myMetricValue)
            .build();
        data.add(event);
        return StatsPullAtomCallback.RESULT_SUCCESS;
    }
);
```

Pull atom ID 和字段定义需要对照 `frameworks/proto_logging/stats/atoms.proto` 的 `android-17.0.0_r1` tag 确认。`AppStartOccurred` atom 在 atoms.proto 中的 ID 为 48（`app_start_occurred = 48`），字段包括 `transition_delay_millis`、`starting_window_delay_millis`、`bind_application_delay_millis`、`windows_drawn_delay_millis` 等，不存在 `latencyMillis` 字段。

[已确认: AOSP android-17.0.0_r1 packages/modules/StatsD/framework/java/android/app/StatsManager.java; frameworks/proto_logging/stats/atoms.proto]

---

## 2. 电池感知采样：App 层实现策略

StatsD 在 daemon 层不根据电池状态自动调节采样率。电池感知采样需要 App 侧基于 `PowerManager` / `BatteryManager` 自行实现。

### 2.1 电池模式与采集频率

| 电池模式 | 建议采样率 | 上报策略 | 适用场景 |
|---------|----------|----------|---------|
| 省电模式 | 5-10%，仅 P0 指标 | 延迟上报 | 长时间低电量 |
| 低电量 (<30%) | 20-30%，P0+部分 P1 | WiFi 优先 | 电量紧张但非省电 |
| 正常 (30-80%) | 60-80%，全量 P0+P1 | 正常上报 | 日常使用 |
| 充电/高电量 | 100%，全量 | 实时上报 | 无电量约束 |

采样率建议参考 Firebase Performance 的 `isPerformanceCollectionEnabled` / `sessionSamplingRate` 机制，不绑定特定 Android 版本。

### 2.2 App 侧实现方案

```java
public class AppSamplingController {
    private PowerManager powerManager;
    private BatteryManager batteryManager;

    public float getSamplingRate() {
        boolean isPowerSave = powerManager != null && powerManager.isPowerSaveMode();
        int batteryLevel = batteryManager != null
                ? batteryManager.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY) : 100;
        boolean isCharging = batteryManager != null && batteryManager.isCharging();

        if (isPowerSave) {
            return 0.05f;   // 省电模式：5%
        } else if (batteryLevel < 30 && !isCharging) {
            return 0.2f;    // 低电量：20%
        } else if (isCharging || batteryLevel > 80) {
            return 1.0f;    // 充电/高电量：100%
        } else {
            return 0.7f;    // 正常：70%
        }
    }
}
```

### 2.3 动态配置下发

采样子系统的配置调整不依赖 `DeviceConfig.NAMESPACE_STATSD_JAVA`（该 namespace 的配置键未在 android-17.0.0_r1 StatsD 模块中广泛公开）。实际工程中通过自有配置中心（Firebase Remote Config、自建 AB 平台等）下发采样率、上报策略和开关。

---

## 3. 内存监控：系统 API 与 Android 17 新政策

Android 17 的内存管理架构由三套机制共同作用，直接影响内存指标的采集方式和解读。

### 3.1 Debug.MemoryInfo 进程级采集

```java
ActivityManager activityManager =
    (ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE);
Debug.MemoryInfo[] memInfoArray =
    activityManager.getProcessMemoryInfo(new int[]{android.os.Process.myPid()});
Debug.MemoryInfo memInfo = memInfoArray[0];

// 分类内存统计（单位：KB）
int dalvikPss = memInfo.dalvikPss;
int nativePss  = memInfo.nativePss;
int totalPss   = memInfo.getTotalPss();
int dalvikPrivateDirty = memInfo.dalvikPrivateDirty;
```

`getProcessMemoryInfo()` 返回的 `Debug.MemoryInfo` 包含 `getMemoryStat(String)` 方法（API 23+），可按 `summary.java-heap`、`summary.native-heap`、`summary.code`、`summary.stack`、`summary.graphics` 等关键字查询子类明细。ART GC 行为通过 `Debug.getRuntimeStat()` 查询（如 `art.gc.gc-count`、`art.gc.gc-time`），`getMemoryStat()` 只覆盖进程级分类，不含 ART 内部堆分区明细。

[已验证: AOSP android.os.Debug.MemoryInfo, API 34-37; art.gc.* 键见 Debug.getRuntimeStat 官方文档]

### 3.2 Native 内存与 Runtime 统计

```java
// Native 堆已分配（API 23）
long nativeAllocated = Debug.getNativeHeapAllocatedSize();

// ART 运行时 GC 统计
String gcCount = Debug.getRuntimeStat("art.gc.gc-count");
String gcTime  = Debug.getRuntimeStat("art.gc.gc-time");
```

[已验证: android.os.Debug 官方文档, API 34]

### 3.3 Android 17 内存管理新政策对监控的影响

Android 17 默认启用 **Compaction** 和 **Freezer**，这两项机制直接影响 `Debug.MemoryInfo` 和 `/proc/<pid>/status` 的连续性和可解释性。

#### Compaction 状态机与 RSS 节流

`CachedAppOptimizer` 默认同时开启 Compaction 和 Freezer：

```java
// CachedAppOptimizer.java: android-17.0.0_r1
@VisibleForTesting static final boolean DEFAULT_USE_COMPACTION = true;
@VisibleForTesting static final boolean DEFAULT_USE_FREEZER = true;

enum CompactProfile {
    NONE, SOME, ANON, FULL
}
```

默认节流窗口：Some→Some 5 秒，Some→Full 10 秒，Full→Some 500 毫秒，Full→Full 10 秒。1Hz 采样 RSS 可能完全无法捕捉压缩事件，因为压缩触发间隔远大于采样间隔。

#### Freezer 冻结器子系统

`CachedAppOptimizer.freezeAppAsyncInternalLSP` 触发冻结前先发送 `TRIM_MEMORY_BACKGROUND`，延迟后通过 `mFreezeHandler` 投递 `DO_FREEZE`。冻结由 cgroup freezer 生效，源码侧记录为 `opt.setFrozen(true)` 并放入 `mFrozenProcesses`，不能等同于 Linux 进程 `D` 状态；冻结期间 `/proc/<pid>/status` 仍可读取，但 RSS 变化会停在冻结前的观测点。开启 `perfettoSdkTracingV3` 时，冻结/解冻事件写入 Perfetto `android.track_event` 的 `FREEZER_EVENT`。

#### MemoryLimiter：memcg 内核级节流

除 `CachedAppOptimizer` 外，Android 17 引入了 `MemoryLimiter`，直接在内核 memcg v2 层写 `memory.high` / `memory.swap.high` 控制阈值。

**对监控采集的三类影响：**

1. **PSS 抖动加剧**：memcg `memory.high` 触发后内核主动回收 anon 页面，`getProcessMemoryInfo()` 可能在毫秒级观测到 PSS 突降。
2. **30 秒 kill 窗口**：`LIMIT_TYPE_ANON_SWAP` 触发后进入 30 秒倒计时（`KILL_DELAY_MS = 30*1000`），超时后系统 kill 进程。APM SDK 需要在这个窗口内通过 `ApplicationExitInfo.REASON_LOW_MEMORY` 归因。
3. **PSS 对 cgroup swap 不可见**：PSS 不含 `mDmabufMapped`（cgroup `memory.current` 包含），可能出现业务侧 PSS 显示未超限但内核已在回收 anon 的情况。

[已验证: AOSP android-17.0.0_r1 MemoryLimiter.java, com_android_server_am_MemoryLimiter.cpp, ProcessRecord.java, ActivityManagerService.java]

### 3.4 Android 17 原生内存跟踪架构

两条路径协同工作：

**Memtrack HAL — 图形内存分类：**
```cpp
struct graphics_memory_pss {
    int graphics;    // 图形内存（SurfaceFlinger 等）
    int gl;          // GL 内存（OpenGL/Vulkan）
    int other;       // 其他内存（Ashmem 等）
};
```

**ProcMemInfo — smaps_rollup 优先：**
```cpp
::android::meminfo::ProcMemInfo proc_mem(pid);
::android::meminfo::MemUsage stats;
if (proc_mem.SmapsOrRollup(&stats)) {
    pss += stats.pss;
    // 失败时自动回退到传统 smaps
}
```

| Android 版本 | 内存分类口径 | 说明 |
|-------------|--------------|------|
| Android 14-17 | graphics / gl / other 三类 memtrack PSS | `android_os_Debug.cpp` 中 `graphics_memory_pss` 与 `memtrack_proc_graphics_pss()` / `memtrack_proc_gl_pss()` / `memtrack_proc_other_pss()` 在这些版本均存在 |
| Android 17 | 同一分类口径，叠加 MemoryLimiter / Freezer 影响 | 三分类不是 Android 17 新增能力；精度取决于 HAL/driver，上述源码没有给出 ±5% 平台保证 |

[已验证: AOSP android-17.0.0_r1 frameworks/base/core/jni/android_os_Debug.cpp, android_util_Process.cpp]

---

## 4. Battery Historian 与性能指标整合

Battery Historian 是一个离线分析工具，通过解析 `bugreport` 中的 statsd 数据和 batterystats 历史来重建设备的功耗和性能时间线。

### 4.1 版本演进

| 版本 | API | 关键变化 |
|------|-----|---------|
| Android 14 | 34 | `StatsManager.addConfig()` / `query()` / `setPullAtomCallback()` 已存在，StatsD 不是 Android 14 才出现的基础框架 |
| Android 15 | 35 | `ApplicationExitInfo.REASON_LOW_MEMORY` / `REASON_FREEZER` 继续作为退出归因 API，不能写成 Android 15 才进入 statsd |
| Android 16 | 36 | StatsD pull callback 主线与 Android 14 基本一致，不应写成 Android 16 新增按需拉取 |
| Android 17 | 37 | `CachedAppOptimizer` 可写入 `FREEZER_EVENT`，`MemoryLimiter` 记录 over-limit 事件；内存策略对监控口径影响更大 |

Android 14→17 对性能采集的核心影响不是 StatsD 框架本身的改变，而是后台内存管理策略（§3.3）和系统事件类型（ApplicationExitInfo、Freezer Event）的扩展。Battery Historian 通过 `adb bugreport` 导出后离线分析这些数据，导出命令：

```bash
adb bugreport bugreport.zip
# Battery Historian 在线分析: https://bathist.ef.lc
```

### 4.2 实际使用建议

Battery Historian 更适合系统级功耗/唤醒问题排查。对于 App 性能诊断，`Android Studio Profiler` + `Perfetto trace` 是更直接的工具。StatsD 的 config 订阅与报告查询机制（`addConfig` + `getReports`，见 §1.2）同时需要 `DUMP` 和 `PACKAGE_USAGE_STATS` 特权权限；只有注册自定义 pull atom 数据提供方时才需要 `REGISTER_STATS_PULL_ATOM`。普通 App 无法在线上大规模使用这条路径。App 侧系统事件采集应优先使用 AndroidX 公开 API（JankStats、Debug.MemoryInfo 等）。

---

## 5. 网络性能指标：App 层自建策略

StatsD 的 `atoms.proto` 中没有定义通用的 `url_pattern`、`request_bytes`、`response_bytes` 等 HTTP 性能字段。网络性能指标需要 App 通过自建方案或第三方 SDK（如 Firebase Performance）采集。

### 5.1 URL 模式归一化

App 侧对 URL 做模板归一化，按 endpoint 聚合：

```
原始 URL: https://api.example.com/v2/user/12345/order/67890
归一化:   /v2/user/{id}/order/{id}
```

Firebase Performance Monitoring 提供了内置的 URL pattern 归一化——相同 URL pattern 的请求自动聚合，`{id}` 等动态段替换为占位符。自建方案可参考同样的规则。

### 5.2 HTTP 状态码分组

按 endpoint pattern 分组统计耗时分布和错误率：

**2xx**：按 P50/P90/P99 统计耗时分布

**4xx**：拆分为四个子类
- 400（请求格式错误）
- 401/403（鉴权失败）
- 404（端点不存在）
- 429（限流）

**5xx**：拆分为 500/502/503/504

网络错误率按 `(5xx_count) / total_count` 计算——4xx 通常属于预期状态（鉴权流程、限流响应），不计入错误率。

### 5.3 Payload Size 统计

记录每次网络请求的请求体和响应体大小，按 endpoint 聚合后输出：

- **平均响应体大小**：识别 API 返回数据膨胀趋势
- **P95 响应体大小**：捕获偶发大包
- **总传输量**：按 endpoint × 时间段统计
- **压缩比**：通过 `response_bytes` 与 `Content-Length` header 的比值计算

这些指标可以通过 `OkHttp EventListener` 或 `HttpURLConnection` 包装器在 App 侧采集。

---

## 6. JankStats 与系统级指标分界

`JankStats`（AndroidX `metrics-performance` 库）和 StatsD 在数据分工上有明确边界。

### 6.1 职责分工对比

| 维度 | JankStats（端侧） | StatsD（系统级） |
|------|-----------------|----------------|
| 采集粒度 | 每帧（`OnFrameListener` 回调） | 按 StatsdConfig 配置聚合周期 |
| 数据内容 | frameDurationUiNanos, isJank, UI states | 订阅的 atom 字段（见 atoms.proto） |
| 运行位置 | App 进程内，AndroidX 库 | statsd daemon 进程 |
| 状态绑定 | 绑定 UI 状态（Activity/Fragment/滚动状态） | 不绑定 UI 状态 |
| 适用场景 | 端侧实时帧诊断，单用户问题复现 | 系统健康指标聚合，版本/设备维度对比 |
| 权限要求 | 无特殊权限 | `REGISTER_STATS_PULL_ATOM`（特权） |

### 6.2 需要自采补充的场景

**1. 单用户卡顿复现：**
StatsD 可以告诉你"版本 4.7 在 Pixel 8 上 P95 帧耗时从 12ms 升到 22ms"，但无法告诉你这个用户在哪个页面、执行什么操作时卡顿。需要 JankStats 绑定的 UI 状态标签：

```java
// AndroidX metrics-performance: 创建 JankStats 时传入 OnFrameListener
JankStats jankStats = JankStats.createAndTrack(window, frameData -> {
    // frameData.getFrameDurationUiNanos() — 帧耗时 (ns)
    // frameData.isJank() — 是否判定为卡顿
    // frameData.getStates() — UI 状态列表 (通过 PerformanceMetricsState 绑定)
    long frameDurationNs = frameData.getFrameDurationUiNanos();
    boolean isJank = frameData.isJank();
    if (isJank) {
        // 上报卡顿帧，附带当前 UI 状态
        reportJankFrame(frameDurationNs, frameData.getStates());
    }
});
```

**2. 帧耗时与 UI 逻辑关联：**
JankStats 按 Window 创建实例，可以将帧耗时直接关联到具体 UI 页面和操作阶段。

**3. 低端设备降级策略验证：**
JankStats 逐帧验证 `isJank` 是否从 true 降为 false。StatsD 的 30s 聚合周期在这种微调验证中粒度过粗。

### 6.3 实际接入建议

JankStats 在以下条件同时满足时打开：
1. 用户在前台且屏幕 on
2. 电量 > 30% 或正在充电
3. 采样率 5-10%

```java
public class JankStatsController {
    private JankStats jankStats;
    private boolean isTracking = false;

    public void enableJankStatsIfAppropriate(Window window, Context context) {
        PowerManager pm = (PowerManager) context.getSystemService(Context.POWER_SERVICE);
        BatteryManager bm = (BatteryManager) context.getSystemService(Context.BATTERY_SERVICE);

        boolean powerSave = pm.isPowerSaveMode();
        int level = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY);
        boolean charging = bm.isCharging();

        if (!powerSave && (level > 30 || charging)) {
            if (jankStats == null) {
                jankStats = JankStats.createAndTrack(window, frameData -> {
                    // 帧级回调：frameDurationUiNanos, isJank, states
                    if (frameData.isJank()) {
                        handleJankFrame(frameData);
                    }
                });
            }
            jankStats.setTrackingEnabled(true);
            isTracking = true;
        } else if (jankStats != null) {
            jankStats.setTrackingEnabled(false);
            isTracking = false;
        }
    }
}
```

---

## 7. 内存泄漏检测

标准 Android SDK 未提供系统级内存泄漏 API。工程实践中由 LeakCanary 负责。

### 7.1 LeakCanary 2.x 工作流程

**初始化：**
```java
LeakCanary.setConfig(LeakCanary.getConfig().newBuilder()
    .retainedVisibleThreshold(5)
    .computeRetainedHeapSize(true)
    .build());
```

**手动触发对象观察：**
```java
AppWatcher.INSTANCE.getObjectWatcher().watch(targetObject, "描述该对象用途");
```

**检测流程：**
1. `ObjectWatcher` 持有弱引用，5 秒后检查引用是否已被 GC 清除
2. 未清除则触发 heap dump，Shark 库解析 hprof 文件
3. 找到到 GC root 的最短引用路径
4. 在通知栏展示泄漏链

### 7.2 架构特点

- **无侵入式初始化**：Debug 构建通过 `ContentProvider` 自动初始化
- **非阻塞分析**：Heap dump 解析在后台线程执行

**Android 17 适配注意点：**
- ContentProvider 初始化时机受严格生命周期管理影响，可能延迟到首个 Activity 启动之后
- 生产环境建议显式调用 `LeakCanary.setConfig()` 确保对象跟踪在 Application.onCreate 完成前就绪

### 7.3 配置建议

```java
LeakCanary.setConfig(LeakCanary.getConfig().newBuilder()
    .retainedVisibleThreshold(3)
    .maxStoredHeapDumps(2)
    .dumpHeapMaxDurationMillis(20000)   // 20 秒超时（低端设备）
    .computeRetainedHeapSize(true)
    .build());
```

---

## 8. 线上采集的边界条件

### 8.1 性能开销

性能监控本身带来的开销需要控制在可接受范围。

**异步采集：**
所有指标采集应在独立线程执行。`StatsManager.setPullAtomCallback()` 注册的 callback 在 statsd 回调时运行于指定的 executor 线程中，不阻塞主线程。`JankStats.OnFrameListener` 回调在帧提交后的 Choreographer 回调线程中触发，应尽量轻量。

**批量处理：**
StatsD 的 config 订阅机制按 `StatsdConfig` 定义的周期聚合原子事件，`getReports()` 返回的是聚合后的报告。App 自建的指标缓冲也应该按周期批量写入上报通道，而不是每采集一点就发一次网络请求。

**内存池管理：**
频繁创建的事件对象应通过对象池复用，避免高频采集下的内存分配抖动。

**开销参考**（实际工程经验值，非 Android 17 平台保证数字）：
- CPU：< 5%
- 内存：< 20MB
- 网络：由上报频率和数据量决定

### 8.2 权限边界

Android 17 的性能监控权限分层明确：

**StatsD config/report/query 路径（需要特权权限）：**
- `REGISTER_STATS_PULL_ATOM`：注册 pull 回调
- `DUMP` + `PACKAGE_USAGE_STATS`：注册 config、读取 `getReports()`
- `READ_RESTRICTED_STATS`：使用 `query()` 查询 SQL 结果

**App 自建指标路径（无需特殊权限）：**
- `Debug.MemoryInfo`：无需额外权限
- `ActivityManager.getProcessMemoryInfo()`
- `Debug.getRuntimeStat()`
- `PowerManager.isPowerSaveMode()`

**网络上报权限：**
- `INTERNET`（清单声明即可）

**兼容性注意：**
- 部分精细指标（如 per-package CPU time）在非特权 App 中返回 0 而非抛异常
- Android 17 对后台采集的频率限制更严格，建议通过 JobScheduler 或 WorkManager 安排采集任务

---

## 9. 数据处理与上报策略

以下策略基于工程实践总结，不绑定 Android 17 StatsD 平台的特定配置项。

### 9.1 本地缓存机制

**环形缓冲：**
App 侧在内存中维护固定大小的环形缓冲，保留最近 15-30 分钟的未上报数据。

**断点续传：**
每个上报批次带序列号和上一个已确认批次 ID，服务端返回确认后本地释放对应缓冲。

### 9.2 上报策略

**WiFi 优先：**
聚合数据块超过阈值时，仅在 WiFi 或 Ethernet 连接下触发上报。紧急事件（Crash、ANR）在任何网络下立即发送。

**移动网络控制：**
4G/5G 下限制上报频率和单次数据量，控制在每小时数百 KB 以内。

**指数退避重试：**
上报失败后按 1s → 2s → 4s → 8s → 16s → 32s（上限）重试，连续 6 次失败后放弃当前批次。

```java
public class UploadManager {
    private ConnectivityManager.NetworkCallback networkCallback;

    public void setupNetworkCallback() {
        ConnectivityManager cm = (ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
        networkCallback = new ConnectivityManager.NetworkCallback() {
            @Override
            public void onAvailable(Network network) {
                sendPendingUploads();
            }
        };
        cm.registerNetworkCallback(new NetworkRequest.Builder().build(), networkCallback);
    }
}
```

---

## 10. 性能监控最佳实践

### 10.1 监控范围控制

性能监控按三级优先级调节采集范围：

**P0 级别（始终 100% 采集）：**
- Crash 和 ANR 事件（`ApplicationExitInfo`）
- 冷启动耗时（> 3s 告警）
- 每日活跃用户数、会话数（基线指标）

**P1 级别（动态调整采样率）：**
- 帧率 / Janky frames（JankStats）
- 内存使用率和 GC 频率
- 网络错误率

**P2 级别（按需采集）：**
- 业务自定义指标
- 用户操作路径
- 设备信息快照

启动超时对留存有明确负向影响，但“每增加 1s 下降 2-4%”这类数字需要补充公开来源、样本条件和适用边界后才能进入正文。Crash、ANR、启动超时应始终全量采集。

### 10.2 隐私保护

1. 敏感数据在写入本地缓冲前完成脱敏
2. 网络上报走 HTTPS
3. 禁止在日志或 URL 中嵌入原始用户标识
4. App 侧采集的数据在客户端匿名化后再上报

### 10.3 数据生命周期

- **App 侧缓冲**：15-30 分钟环形缓冲，用于网络中断容灾
- **服务端实时数据**：保留 7 天，用于即时回溯
- **聚合数据**：保留 90 天，用于趋势分析和版本对比
- **归档数据**：按业务需求保留，建议不超过 12 个月

---

## 11. Android 17 内存监控适配建议

### 11.1 三层降级策略

**L1（Android 17+）：**
优先用 Perfetto 拉取 `android.track_event` 中的 `FREEZER_EVENT`，过滤 `UNFREEZE_REASON_TRIM_MEMORY` / `UNFREEZE_REASON_ACTIVITY` / `UNFREEZE_REASON_UID_IDLE` 等源码中存在的原因。

**L2（Android 14-16）：**
维持 `/proc/<pid>/status` 1Hz 采样，但应用端要做 `onTrimMemory` 事件桥接。

**L3（Android 13-）：**
退化到 `ActivityManager.MemoryInfo` 全局 API，丢弃单进程 RSS 精度。

### 11.2 内存监控代码适配

```java
public class AdaptiveMemoryMonitor {
    public MemorySnapshot getMemorySnapshot(Context context) {
        ActivityManager am = (ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.CINNAMON_BUN) {
            Debug.MemoryInfo[] info = am.getProcessMemoryInfo(new int[]{Process.myPid()});
            return fromDebugMemoryInfo(info[0]);
        } else {
            ActivityManager.MemoryInfo global = new ActivityManager.MemoryInfo();
            am.getMemoryInfo(global);
            return fromGlobalMemoryInfo(global);
        }
    }
}
```

---

## 总结

Android 14-17 的性能监控不是按一个虚构的 "PERFORMANCE_METRICS_ATOM" 运转的。实际工程中，这套体系由三层构建块组成：

1. **系统层**：StatsD 通过 `StatsManager.addConfig()` + `getReports()` 向特权 App 提供 `atoms.proto` 中系统原子（如 `AppStartOccurred`（ID 48）、`AnrOccurred`、`ApplicationExitInfo`）的聚合报告；`setPullAtomCallback()` 是特权组件向 statsd 提供自定义 pulled atom 数据的入口。权限边界为：`setPullAtomCallback()` 需要 `REGISTER_STATS_PULL_ATOM`，`addConfig()` / `getReports()` 同时需要 `DUMP` 和 `PACKAGE_USAGE_STATS`，`query()` 需要 `READ_RESTRICTED_STATS`。
2. **框架层**：AndroidX `JankStats` 负责帧级实时诊断，`Debug.MemoryInfo` 负责进程级内存采集——两者都不需要特殊权限。
3. **App 层**：电池感知采样率、网络指标聚合、上报策略和缓存管理由 App 自行实现或通过 Firebase Performance 等 SDK 接入。

Android 17 对这套体系的实质扩展集中在后台内存管理（Compaction + Freezer + MemoryLimiter），StatsD API 本身未变。这些机制直接改变了内存指标的采集方式和解读方法。P0 始终全量，P1 跟随电量和场景动态调整，P2 按需开启。

## 延伸阅读

- [Android Performance Vitals](https://developer.android.com/topic/performance/vitals) — Google 官方性能指标定义与最佳实践
- [Firebase Performance Monitoring](https://firebase.google.com/docs/perf-mon) — Firebase 性能监控接入指南，含采样率配置与 URL pattern 归一化
- [ApplicationExitInfo API](https://developer.android.com/reference/android/app/ApplicationExitInfo) — Android 11+ 退出原因归因 API
- [JankStats — AndroidX metrics-performance](https://developer.android.com/reference/androidx/metrics/performance/JankStats) — 帧级卡顿检测库官方文档
- [Battery Historian](https://github.com/google/battery-historian) — 电池历史离线分析工具源码
- [LeakCanary](https://square.github.io/leakcanary/) — Square 开源的内存泄漏检测库
- [Debug.MemoryInfo](https://developer.android.com/reference/android/os/Debug.MemoryInfo) — 进程内存使用明细 API
- [StatsD atoms.proto](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/proto_logging/stats/atoms.proto) — android-17.0.0_r1 中完整原子定义
