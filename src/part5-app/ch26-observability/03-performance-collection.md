---
title: 性能指标采集与上报
chapter: '26.3'
section: '26.3'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-08-15'
last_source_verified_at: '2026-08-15'
last_verified_against: AOSP android-17.0.0_r1 StatsManager/atoms/ActivityManager/CachedAppOptimizer/MemoryLimiter
  sources, Android common kernel android17-6.18-2026-06_r6 cgroup v2 docs, and current AndroidX
  JankStats, Firebase Performance, Battery Historian, WorkManager, LeakCanary, and Debug.MemoryInfo
  docs retrieved 2026-08-15
confidence: high
tags:
- android
- performance
- statsd
- jankstats
- memory-monitoring
- leakcanary
- apm
- android-17
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
pipeline_stage: ready-to-publish
last_idle_audit_at: '2026-08-09T03:47:35+08:00'
last_idle_audit_run_id: '20260809-034735-idle-audit-0e177ec8'
last_draft_polish_at: '2026-08-15T18:49:56+08:00'
last_draft_polish_run_id: '20260815-184956-gracker-writing-464'
last_review_finalize_at: '2026-08-15T18:49:56+08:00'
last_review_finalize_run_id: '20260815-184956-gracker-writing-464'
last_rework_at: '2026-08-15T18:49:56+08:00'
last_rework_run_id: '20260815-184956-gracker-writing-464'
sources:
- type: source
  path: https://android.googlesource.com/platform/packages/modules/StatsD/+/refs/tags/android-17.0.0_r1/framework/java/android/app/StatsManager.java
- type: source
  path: https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/proto_logging/stats/atoms.proto
- type: source
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java
- type: source
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryLimiter.java
- type: source
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/jni/com_android_server_am_MemoryLimiter.cpp
- type: source
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/admin-guide/cgroup-v2.rst
- type: official
  path: https://developer.android.com/reference/androidx/metrics/performance/JankStats
- type: official
  path: https://developer.android.com/topic/performance/jankstats
- type: official
  path: https://developer.android.com/reference/android/os/Debug
- type: official
  path: https://developer.android.com/reference/android/os/Debug.MemoryInfo
- type: legacy-reference-preserved
  path: https://android.googlesource.com/platform/system/memory/+/refs/tags/android-17.0.0_r1/libmeminfo/
- type: source
  path: https://android.googlesource.com/platform/system/memory/libmeminfo/+/refs/tags/android-17.0.0_r1/
- type: legacy-reference-preserved
  path: https://android.googlesource.com/platform/system/memory/+/refs/tags/android-17.0.0_r1/libmeminfo/libmemevents/
- type: source
  path: https://android.googlesource.com/platform/system/memory/libmeminfo/+/refs/tags/android-17.0.0_r1/libmemevents/
- type: official
  path: https://developer.android.com/reference/android/app/ActivityManager
- type: official
  path: https://developer.android.com/reference/android/app/ActivityManager.MemoryInfo
- type: official
  path: https://developer.android.com/reference/android/app/ApplicationExitInfo
- type: official
  path: https://firebase.google.com/docs/perf-mon
- type: official
  path: https://firebase.google.com/docs/perf-mon/custom-url-patterns
- type: official
  path: https://developer.android.com/topic/performance/power/setup-battery-historian
- type: official
  path: https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work#work-constraints
- type: official
  path: https://square.github.io/leakcanary/getting_started/
---

# 26.3 性能指标采集与上报

## 概览

Android 没有一个面向普通 App、涵盖所有性能问题的“统一性能指标 Atom”。StatsD 是 Android 的系统统计收集与聚合服务，atom 是其数据结构定义中字段固定的一类统计事件。可用能力分布在不同权限层：StatsD 面向系统和特权组件；AndroidX `JankStats` 在 App 进程内提供帧级卡顿数据；`Debug.MemoryInfo`、在网络调用前后加入计时点的插桩，以及业务埋点补充 App 自身指标；上传与服务端统计由 APM（Application Performance Monitoring，应用性能监控）系统负责。

平台上界为 Android 17 / API 37 / `android-17.0.0_r1`。缓存进程内存整理（Compaction）和暂停缓存进程执行的冻结机制（Freezer）早于 Android 17 已存在；Android 17 新增的 `MemoryLimiter` 还受功能开关（feature flag）、设备能力和厂商（vendor）配置控制。观察到内存曲线变化时，要区分公开 App API 能确认的事实与 Android 核心系统服务进程 system_server 的源码解释。PSS（Proportional Set Size，按共享页面比例分摊后的驻留内存）曲线本身不能证明某项系统策略已经触发。

---

## 1. 系统级指标采集：StatsD 的能力与权限边界

Android 17 的 StatsD 模块位于 `packages/modules/StatsD`。statsd 后台守护进程（daemon）接收 `atoms.proto` 定义的 pushed atom，即事件发生方主动推送的原子事件；它也会按照采集配置（config）向已注册的数据提供方请求 pulled atom。后者是由 statsd 发起拉取、提供方通过回调函数（callback）返回数据。聚合结果由具备权限的客户端通过报告或受限查询 API 读取。

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
        throws StatsUnavailableException

// 读取已收集报告（主查询路径）
public byte[] getReports(long configId)
        throws StatsUnavailableException
```

App 侧不能通过 `StatsManager` 写入事件。`android.util.StatsLog.logStart/logStop/logEvent(int)` 是公开的 breadcrumb API；breadcrumb 在这里指用于标记操作起止或单次事件的轻量记录，它只能写入 `APP_BREADCRUMB_REPORTED`。任意 `StatsEvent` 写入路径 `StatsLog.write(StatsEvent)` 属于受限的 `@SystemApi`，系统服务通常使用生成的 `FrameworkStatsLog` / `StatsdStatsLog`。

`setPullAtomCallback()` 用于**客户端向 statsd 提供自定义 pulled atom 数据**，读取 statsd 聚合指标要使用其他接口。当 statsd 需要拉取某个原子事件时，它会调用已注册的 `StatsPullAtomCallback.onPullAtom(int atomTag, List<StatsEvent> data)`；其中 atom tag 是原子事件编号。客户端把 `StatsEvent` 加入 `data` 列表并返回 `RESULT_SUCCESS` / `RESULT_SKIP` 等结果，`StatsManager` 内部的 `PullAtomCallbackInternal` 再调用 `resultReceiver.pullFinished()` 把结果交回 statsd。`PullAtomMetadata` 的默认冷却间隔为 1000 ms，超时为 1500 ms，用于限制按需拉取频率，并不形成周期性定时回调。

`addConfig()` 返回 `void`（而非 boolean），用于向 statsd 注册 `StatsdConfig`；该配置描述要收集的原子事件与聚合方式。`getReports(long configId)` 用于读取 statsd 已收集的报告，是特权 App 获取聚合数据的主要接口。`query()` 需要 `READ_RESTRICTED_STATS` 权限，签名为 `query(long configKey, String configPackage, StatsQuery query, Executor executor, OutcomeReceiver<StatsCursor, StatsQueryException> outcomeReceiver)`。

**权限要求：**
- 注册 pull atom 数据提供方（`setPullAtomCallback`）需要 `REGISTER_STATS_PULL_ATOM` 权限（位于 `frameworks/base/core/res/AndroidManifest.xml`）
- 注册 config 和读取报告（`addConfig`、`getReports`）同时需要 `DUMP` 和 `PACKAGE_USAGE_STATS` 权限
- SQL 查询路径 `query()` 需要 `READ_RESTRICTED_STATS` 权限
- AndroidManifest 中不存在 `READ_PRECISE_STATS` 权限；当前 StatsD 权限模型以 `REGISTER_STATS_PULL_ATOM`、`DUMP`、`PACKAGE_USAGE_STATS`、`READ_RESTRICTED_STATS` 为主

### 1.2 数据流路径

整体数据流分三条路径：

下面的路径表示 pushed atom 和公开 breadcrumb 如何进入 statsd。

**系统事件入站（系统服务 → statsd daemon）：**
```
App breadcrumb / system service → StatsLog / FrameworkStatsLog / StatsdStatsLog → libstatssocket → statsd daemon (本地 socket)
```

`StatsLog` 在 `packages/modules/StatsD/framework/java/android/util/StatsLog.java` 中定义。普通 App 可调用 `logStart/logStop/logEvent(int)` 写 breadcrumb；系统服务写入框架原子通常走生成的 `FrameworkStatsLog.write()` / `StatsdStatsLog.write()`，最终通过 `libstatssocket` 的本地 socket 写入 statsd daemon。普通 App 不能用这条路径写任意系统 atom。

下面的路径表示特权客户端注册 config 并读取聚合报告。

**Config 订阅与报告读取（statsd ⇄ 特权 App）：**
```
StatsManager.addConfig(configId, config) → statsd daemon 按 config 聚合
StatsManager.getReports(configId) ← statsd daemon 返回已收集报告
```

特权 App 通过 `addConfig()` 向 statsd 注册 `StatsdConfig`（定义要收集哪些 atom、聚合方式），statsd 按 config 持续收集并聚合。App 通过 `getReports()` 读取聚合结果——这是获取 statsd 系统健康指标的主路径。

下面的路径表示 statsd 向特权数据提供方发起 pull。

**Pull atom 数据提供（特权组件 → statsd）：**
```
StatsPullAtomCallback.onPullAtom(int atomTag, List<StatsEvent> data) → statsd 向客户端拉取自定义 pulled atom
```

`setPullAtomCallback()` 注册的是**数据提供方**：当 statsd 的 config 中包含 pulled atom 时，statsd 回调已注册的 callback，由客户端向 `List<StatsEvent>` 中填充指标数据。这不是 App 从 statsd 拉取系统聚合指标的通道——读取聚合指标应走 `addConfig` + `getReports` 路径。

当前 `atoms.proto`（android-17.0.0_r1）中定义了大量系统健康原子（如 `AppStartOccurred`（ID 48）、`AnrOccurred`、`BatteryLevelChanged` 等），但没有统一的 "性能指标大 Atom"。App 侧如需收集系统级指标，优先通过 AndroidX API（如 `JankStats`）和 `Debug.MemoryInfo` 等公开接口，而非直接依赖 StatsD。

**StatsCompanionService 的职责：**
`StatsCompanionService` 运行在 system_server 中，是通过 `IStatsd` 接口与 statsd 守护进程交互的辅助服务，主要处理配置管理和数据拉取方注册。事件写入由 `StatsLog` 通过 `libstatssocket` 直接连接 statsd 的本地套接字（socket），不经过 `StatsCompanionService`；因此，它也不是从 `/dev/socket/statsdw` 读取事件流的 JNI（Java Native Interface，Java 原生接口）桥接层。

### 1.3 系统指标采集边界与 App 侧替代方案

StatsD 的 pull atom 数据提供、config 注册/报告读取、SQL query 都是特权路径，分别需要 `REGISTER_STATS_PULL_ATOM`、`DUMP` + `PACKAGE_USAGE_STATS`、`READ_RESTRICTED_STATS`。普通 App 无法直接使用 StatsD 获取系统级性能指标。实际工程中，App 侧采集系统级指标的三条可用路径为：

**路径 1：AndroidX JankStats — 帧级实时诊断**

下面的最小示例读取帧时长、卡顿判定和 UI 状态。

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

回调会在每帧触发，业务不能在这里直接序列化或上传；对象复用与线程边界详见 §6。

**路径 2：Debug.MemoryInfo — 进程级内存采集**

下面的最小示例读取当前进程的总 PSS。

```java
ActivityManager am = (ActivityManager) getSystemService(Context.ACTIVITY_SERVICE);
Debug.MemoryInfo[] info = am.getProcessMemoryInfo(new int[]{Process.myPid()});
int totalPss = info[0].getTotalPss();
```

返回值的 UID（用户标识）与频率限制详见 §3，不能用这段代码轮询其他应用。

**路径 3：Firebase Performance / 自建 APM SDK**

网络耗时、启动耗时、自定义业务指标由 APM SDK 在 App 进程中直接采集，无需经过 StatsD。详见 §5、§9。

特权系统组件若要提供 pulled atom，需要为已经定义并获准使用的 atom tag 调用 `setPullAtomCallback()`。statsd 调用 `StatsPullAtomCallback.onPullAtom()` 时，提供方把符合数据结构定义（schema）的 `StatsEvent` 加入列表并返回结果码。atom ID、字段顺序、字段类型和可累加字段（additive field）必须来自同一次平台发布的 schema，不能用业务自定义常量代替平台定义。

`AppStartOccurred` 在 Android 17 `atoms.proto` 中的 ID 为 48（`app_start_occurred = 48`），字段包含 `transition_delay_millis`、`starting_window_delay_millis`、`bind_application_delay_millis`、`windows_drawn_delay_millis` 等，没有 `latencyMillis` 字段。

---

## 2. 电池感知采样：App 层实现策略

StatsD 在 daemon 层不根据电池状态自动调节采样率。电池感知采样需要 App 侧基于 `PowerManager` / `BatteryManager` 自行实现。

### 2.1 状态只参与策略，不直接决定固定百分比

采样策略可以读取 `PowerManager.isPowerSaveMode()`、`BatteryManager.isCharging()` 和电量信息，但采样率没有跨应用通用的固定值。它取决于单次采集成本、指标价值、产品流量、网络条件和服务端统计所需精度。把“低电量”等同于某个固定百分比，会让不同版本的样本分布发生隐式变化。

更合适的做法是把策略输入和动作分开：

| 策略输入 | 可选动作 | 统计要求 |
| --- | --- | --- |
| 省电模式、未充电、计量网络 | 暂停高成本 trace，降低普通样本纳入率，延后大附件 | 记录策略版本和实际纳入概率 |
| 前台关键路径 | 保留低成本计数与时延摘要 | 不因电池状态丢失分母 |
| 充电且网络不计量 | 处理积压批次或执行已授权的高成本诊断 | 仍受温度、存储和用户设置约束 |
| 远程诊断命令 | 在有效期、配额和同意范围内临时调整 | 记录命令来源、有效期与审计 ID |

同一用户或会话是否被采样，宜使用稳定哈希做确定性分配，即让同一输入始终得到相同的采样结果，避免每次事件随机选择造成会话不完整。若再按机型、版本或场景分层，服务端必须知道各层纳入概率，才能计算可比较的总体指标。

### 2.2 配置与失效保护

采样配置属于 App/APM 的业务配置，不应借用 StatsD 内部的 `DeviceConfig` 命名空间（namespace，即配置项的分组范围）。配置快照至少包含版本、签名或完整性校验、启用范围、过期时间、每类指标配额和回退值。配置拉取失败时沿用最近一份有效快照；快照过期后回到保守策略，而不是默认扩大采集。

电量 API 也需要处理不可用值和设备差异。策略层不要把某次电量读取失败当成“满电”，也不要让电量信号改变 Crash、ANR 等事件的事实计数；它更适合控制附件、trace 和上传时机。

---

## 3. 内存监控：公开 API 与 Android 17 系统策略

App 可见的 PSS、Java/Native 堆和 GC（Garbage Collection，垃圾回收）统计，与 system_server 的 Compaction、Freezer、MemoryLimiter 分属不同观察层。前一层可以通过公开 API 采集；后一层通常只能通过系统 trace（按时间记录系统行为的追踪数据）、`dumpsys` 诊断输出或源码解释。两层可以做时间关联，但不能把一次 PSS 变化直接标记成某个系统事件。

### 3.1 Debug.MemoryInfo 进程级采集

下面的示例读取当前进程的 PSS 与 private dirty 分类。private dirty 指进程私有且已被修改、无法直接与其他进程共享的内存页。

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

`getProcessMemoryInfo()` 返回的 `Debug.MemoryInfo` 包含 `getMemoryStat(String)` 方法（API 23+），可按 `summary.java-heap`、`summary.native-heap`、`summary.code`、`summary.stack`、`summary.graphics` 等关键字查询子类明细。ART（Android Runtime，Android 运行时）的 GC 行为通过 `Debug.getRuntimeStat()` 查询（如 `art.gc.gc-count`、`art.gc.gc-time`），`getMemoryStat()` 只覆盖进程级分类，不含 ART 内部堆分区明细。

Android 10 起，普通 App 只能取得与调用者相同 UID 的进程数据；该 API 还会限制采样频率，调用过快时可能返回与上次相同的数据。它适合低频诊断和趋势采样，不适合用紧密轮询近似实时 RSS（Resident Set Size，进程当前驻留在物理内存中的页面总量，不按共享比例分摊）。

### 3.2 Native 内存与运行时统计

下面的示例分别读取 Native heap 已分配字节数和 ART GC 累计统计。

```java
// Native 堆已分配（API 1）
long nativeAllocated = Debug.getNativeHeapAllocatedSize();

// ART 运行时 GC 统计
String gcCount = Debug.getRuntimeStat("art.gc.gc-count");
String gcTime  = Debug.getRuntimeStat("art.gc.gc-time");
```

`getNativeHeapAllocatedSize()` 返回 Native heap allocator 统计，不等于进程全部 Native 映射；`getRuntimeStat()` 在键不受支持时可以返回 `null`。

### 3.3 Compaction、Freezer 与 Android 17 MemoryLimiter

Android 17 的 `CachedAppOptimizer` 仍把 Compaction 和 Freezer 的构建默认值设为开启，但这两项机制并非 Android 17 新增，运行时状态也会受配置与设备条件影响。Android 17 新出现的 `MemoryLimiter` 则有独立功能开关、`/vendor/etc/memory-limiter-config.xml` 厂商配置文件和设备内存条件；源码存在不表示所有 Android 17 设备都会启用。

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

源码中的四个默认节流值分别约束 Some→Some、Some→Full、Full→Some 和 Full→Full 请求，它们是最短间隔，不是固定调度周期。PSS 轮询只能看到采样点之间的结果变化，无法确认变化发生时刻，也无法仅凭曲线判断是否由 compaction 引起；系统级验证需要结合对应 trace、dumpsys 或日志事件。

#### Freezer 冻结器子系统

`CachedAppOptimizer` 最终通过 cgroup freezer 冻结缓存进程。cgroup 是 Linux 按进程组控制资源的机制，freezer 是其中的冻结控制；源码状态记录为 `opt.setFrozen(true)`。它不等同于 Linux 中表示不可中断睡眠的 `D` 状态。被冻结的 App 进程不能继续运行自己的采样线程，因此无法在冻结期间持续采集自身 RSS。特权观察者或离线 trace 能够观察冻结和解冻事件；普通 App 更适合在恢复后根据生命周期、采样时间间隔和 `ApplicationExitInfo` 退出记录判断数据是否中断。

#### MemoryLimiter：内存控制组的内核级节流

Android 17 的 `MemoryLimiter` 由 system_server 的 Java 控制层与 JNI / Native 监控层组成。启用时，它为目标进程配置 cgroup v2 内存控制组（memcg）的 `memory.high`、`memory.swap.high` 等限制，并监听越界事件。该能力要求功能开关开启、代码运行在系统用户标识（system UID）下、存在有效厂商配置且设备内存满足条件。

内核语义以 `android17-6.18-2026-06_r6` 为锚点。该版本的 [cgroup v2 文档](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/admin-guide/cgroup-v2.rst) 把 `memory.high` 定义为内存使用节流边界：超过后进程承受回收压力，但内核不会仅因越过 `memory.high` 就调用 OOM killer（内存耗尽时选择进程终止的内核机制）。MemoryLimiter 在此基础上监控事件，并在匿名内存与交换空间总量（anon+swap）分支由 system_server 另行安排进程终止；两条行为不能合并描述成“内核越界后自动终止”。

**对监控采集的三类影响：**

1. **指标口径不同**：PSS 按共享页面比例分摊；cgroup memory charge（记入该控制组的内存用量）、anon（匿名内存）与 swap（换出到交换空间的内存）采用另一套归属规则。PSS 未达到某个数值，不能证明进程没有触及限制。
2. **越界后可能先采性能剖析数据再终止**：`LIMIT_TYPE_ANON_SWAP` 分支会触发异常性能剖析（anomaly profiling），并通过 `KILL_DELAY_MS` 延迟终止请求，为系统剖析器留出完成时间。这个延迟不属于 App 的轮询或上传时限。
3. **退出原因要读记录，不要预设**：进程恢复后查询 `ApplicationExitInfo`，记录实际 `reason`、`status`、描述和可用 trace，再与 SDK 样本关联。不能把所有 MemoryLimiter 终止预先写成 `REASON_LOW_MEMORY`。

### 3.4 Android 17 原生内存跟踪架构

两条路径协同工作：

下面的结构展示 framework 汇总 memtrack 图形内存时使用的三个分类。

```cpp
struct graphics_memory_pss {
    int graphics;    // 图形内存（SurfaceFlinger 等）
    int gl;          // GL 内存（OpenGL/Vulkan）
    int other;       // 其他内存（Ashmem 等）
};
```

这三个值来自 memtrack HAL 和驱动实现。HAL（Hardware Abstraction Layer，硬件抽象层）把设备相关实现接到 Android 框架；因此，分类精度和可用性取决于设备，不能当作跨机型恒定口径。

下面的片段展示 `ProcMemInfo` 优先读取 `smaps_rollup` 并在不可用时回退到 `smaps` 的意图。

```cpp
::android::meminfo::ProcMemInfo proc_mem(pid);
::android::meminfo::MemUsage stats;
if (proc_mem.SmapsOrRollup(&stats)) {
    pss += stats.pss;
    // 失败时自动回退到传统 smaps
}
```

回退能让旧读取方式继续工作，但不保证各厂商图形内存分类具有相同精度。

| Android 版本 | 内存分类口径 | 说明 |
|-------------|--------------|------|
| Android 14–17 | graphics / gl / other 三类 memtrack PSS | `android_os_Debug.cpp` 中 `graphics_memory_pss` 与 `memtrack_proc_graphics_pss()` / `memtrack_proc_gl_pss()` / `memtrack_proc_other_pss()` 在这些版本均存在 |
| Android 17 | 同一分类口径，叠加 MemoryLimiter / Freezer 影响 | 三分类不是 Android 17 新增能力；精度取决于 HAL / 驱动实现，这些源码没有给出 ±5% 平台保证 |

### 3.5 `libmeminfo` 与 `libmemevents` 的系统侧边界

`Debug.getMemoryInfo()` 的 JNI 最终使用 `libmeminfo` 汇总进程内存。`ProcMemInfo::SmapsOrRollup()` 优先读取 `smaps_rollup`，不可用时退回逐 VMA 的 `smaps`；VMA（Virtual Memory Area，虚拟内存区域）是进程地址空间中属性连续的一段映射。平台组件还可以使用 pagemap、kpageflags 与 kpagecount 做成本更高的 VMA 或 working set（近期活跃内存页集合）诊断。这些 Native 类面向平台代码、厂商组件与 APEX（可独立更新的系统组件包格式）模块集成，不是普通 App 的对象跟踪 API。应用侧继续以 `Debug.MemoryInfo`、`ActivityManager.MemoryInfo` 和调试工具为兼容边界。

Android 14 相关源码中的 `libmemevents` 使用 eBPF 环形缓冲区接收 OOM killer 选中的进程、直接内存回收、内核回收线程 kswapd 与厂商低内存终止机制（LMK）等事件，Android 17 仍保留这条系统路径。eBPF 是在内核受控环境中运行观测程序的机制，环形缓冲区用于把事件按固定容量传给读取方。该路径依赖内核 tracepoint（事件观测点）、BPF 能力、受信任的加载器和 SELinux（Android 强制访问控制机制）策略；设备存在该源码不表示普通 App 可以订阅，也不表示每台 Android 14–17 设备暴露相同事件。线上 SDK 只能保存自身公开指标，平台或设备厂商（OEM）组件才可把这类事件与 App 快照放到同一时间线。

内存监控可以按成本分两层：常态使用聚合快照发现 PSS、nativePss、GC 或后台回落异常；命中诊断条件后，再在受控设备或受信系统组件中使用 VMA 扫描、`libmemevents`、Perfetto、heap dump（堆转储）或 Perfetto 的 Native 堆分析器 heapprofd。聚合值用于发现趋势，深度工具用于解释来源，二者不能互相替代。

---

## 4. Battery Historian 与性能指标整合

Battery Historian 是离线功耗分析工具，它读取 Batterystats 记录的系统电量账目和 bugreport（系统诊断包），再把设备的电池历史转换为 HTML 时间线。时间线适合关联唤醒锁（wakelock，阻止 CPU 进入休眠的持锁记录）、Android 后台任务调度器 JobScheduler 的任务、进程状态和网络活动。Android 官方已经注明该工具不再积极维护；新分析优先考虑 Android Studio 功耗分析器 Power Profiler、AndroidX 宏基准测试 Macrobenchmark 的功耗指标或系统追踪，历史问题和已有流程仍可使用 Battery Historian。

### 4.1 采集与分析边界

Battery Historian 不等同于 App 线上 APM，也不通过 `StatsManager` 给普通 App 持续返回性能报告。它分析的是开发者从测试设备导出的系统级记录。采集前应清理或标记历史窗口，复现场景后再生成 bugreport，避免把前一次测试残留事件混入结论。

下面的命令通过 ADB（Android Debug Bridge，Android 调试桥）生成 Battery Historian 可读取的 bugreport。

```bash
adb bugreport bugreport.zip
```

命令完成后，应在本地或受控环境运行官方 Battery Historian 镜像并上传该 zip。bugreport 可能包含设备和用户敏感信息，不宜交给未审计的在线站点。

### 4.2 与 App 侧监控的配合

App APM 用于持续记录受控的低成本指标；Battery Historian、Power Profiler 和 Perfetto 用于抽样复现与深入归因。线上告警先确定版本、设备和场景，再在可复现设备上采集系统级证据。StatsD config/report 仍是特权路径，不能因为 Battery Historian 能读取 bugreport，就推导出普通 App 能在线读取同一批系统数据。

---

## 5. 网络性能指标：App 层自建策略

StatsD 的 `atoms.proto` 中没有定义通用的 `url_pattern`、`request_bytes`、`response_bytes` 等 HTTP 性能字段。网络性能指标需要 App 通过自建方案或第三方 SDK（如 Firebase Performance）采集。

### 5.1 URL 模式归一化

App 侧对 URL 做模板归一化，按 endpoint（表示同一类业务接口的路径模板）聚合：

```
原始 URL: https://api.example.com/v2/user/12345/order/67890
归一化:   /v2/user/{id}/order/{id}
```

Firebase Performance Monitoring 会先匹配项目配置的 custom URL pattern，再回退到自动 pattern。其自定义语法使用单段通配符 `*` 和后缀通配符 `**`，并不是 `{id}`。自建系统也要让规则版本化；规则版本发生变化时，历史数据不会自动变成同一口径。

### 5.2 HTTP 状态码分组

按 endpoint pattern 统计 DNS 域名解析、连接建立、TLS 加密握手、请求体发送、响应首字节、响应体读取、总耗时和状态码分布。成功率不能统一定义为“非 5xx”：登录接口的 401 可能是预期结果，也可能表示会话刷新故障；下单接口的 409 可能是业务冲突；429 则常常意味着容量或客户端重试策略存在问题。

每个 endpoint 应维护版本化的成功码规则，并单独统计无 HTTP 状态码的 DNS、连接、TLS、取消和超时错误。Firebase Performance 也允许为 URL pattern 自定义哪些响应码算成功，这说明成功口径属于接口语义，而不是 HTTP 大类的固定映射。

### 5.3 传输体积（Payload Size）统计

记录网络层实际可观测的请求与响应字节数，按 endpoint 聚合后输出：

- **响应体大小分布**：识别 API 返回数据膨胀与偶发大包
- **总传输量**：按 endpoint × 时间段统计
- **缓存命中与重试放大**：区分一次逻辑请求对应的网络尝试次数
- **编码信息**：记录 `Content-Encoding`，仅在同时掌握编码前后字节数时计算压缩比

`Content-Length` 描述消息中的内容长度，其含义还会受编码、分块传输和客户端解码位置影响，不能直接拿它与接收字节数相除后宣称是压缩比。OkHttp 可通过 `EventListener` 的请求体和响应体事件取得相应字节数；自定义拦截器还要避免读取或复制流式传输的数据体。

---

## 6. JankStats 与系统级指标分界

`JankStats`（AndroidX `metrics-performance` 库）和 StatsD 在数据分工上有明确边界。Jank 指未在目标时间内完成绘制、造成视觉卡顿的帧；JankStats 会逐帧报告耗时、卡顿判定和当时的 UI 状态。

### 6.1 职责分工对比

| 维度 | JankStats（端侧） | StatsD（系统级） |
|------|-----------------|----------------|
| 采集粒度 | 每帧（`OnFrameListener` 回调） | 按 StatsdConfig 配置聚合周期 |
| 数据内容 | `frameDurationUiNanos`、`isJank`、UI 状态 | 订阅的 atom 字段（见 `atoms.proto`） |
| 运行位置 | App 进程内，AndroidX 库 | statsd daemon 进程 |
| 状态绑定 | 绑定 UI 状态（Activity/Fragment/滚动状态） | 不绑定 UI 状态 |
| 适用场景 | 端侧实时帧诊断，单用户问题复现 | 系统健康指标聚合，版本/设备维度对比 |
| 权限要求 | 无特殊权限 | 按操作分别需要 `REGISTER_STATS_PULL_ATOM`、`DUMP` + `PACKAGE_USAGE_STATS` 或 `READ_RESTRICTED_STATS` |

### 6.2 需要自采补充的场景

**1. 帧数据与页面状态关联：**

StatsD 的系统 atom 不会自动变成当前 App 的页面级 JankStats 数据。JankStats 按 `Window` 回调每帧数据，并通过 `PerformanceMetricsState` 附带页面、列表滚动或业务阶段等状态。

下面的示例只在回调中读取必要字段，并在需要跨出回调保存时复制 `FrameData`。

```java
// AndroidX metrics-performance: 创建 JankStats 时传入 OnFrameListener
JankStats jankStats = JankStats.createAndTrack(window, frameData -> {
    // frameData.getFrameDurationUiNanos() — 帧耗时 (ns)
    // frameData.isJank() — 是否判定为卡顿
    // frameData.getStates() — UI 状态列表 (通过 PerformanceMetricsState 绑定)
    long frameDurationNs = frameData.getFrameDurationUiNanos();
    boolean isJank = frameData.isJank();
    if (isJank) {
        FrameData snapshot = frameData.copy();
        enqueueJankSnapshot(snapshot);
    }
});
```

JankStats 会复用传给回调监听器（listener）的 `FrameData`，以减少每帧创建对象的开销，因此不能在回调返回后继续持有原对象。即使复制了对象，回调里也只应入队，聚合、序列化和网络上报要在其他执行窗口完成。

**2. 帧耗时组成：**

`FrameData.frameDurationUiNanos` 主要描述 UI 部分，不包含渲染线程 RenderThread 的全部耗时。API 31 及以上的回调对象可能是 `FrameDataApi31`，做 `instanceof` 检查后可读取 `frameOverrunNanos`，用于观察超过帧完成期限（frame deadline）的时间；分析时要记录具体字段，不能把所有值都标成“整帧耗时”。

**3. 优化前后验证：**

使用相同设备层、刷新率、页面状态和采样规则，对比卡顿帧比例与超时（overrun）分布。`isJank` 是 JankStats 基于平台信息和内部启发式规则给出的判定；阈值策略升级时要记录库版本，避免把口径变化误认为优化结果。

### 6.3 实际接入建议

每个需要观察的 `Window` 创建一个 `JankStats` 实例，在 Activity 可交互期间启用，并在进入后台时停用。`createAndTrack()` 要求 Window 已有非空 DecorView，过早调用会抛出 `IllegalStateException`。

listener 每帧都会收到回调。API 24 及以上通常由 FrameMetrics 使用的线程交付，更早版本可能在主线程交付；两种情况下都要快速返回。采样宜作用于“是否保留或上传完整 frame 明细”，页面级总帧数、jank 数等分母仍需使用一致口径。电池或网络策略变化时，记录策略版本和纳入概率，不写死全项目通用阈值。

---

## 7. 内存泄漏检测

标准 Android SDK 不会直接告诉应用“哪个对象泄漏”。LeakCanary 适合在开发和测试构建中检测 retained object（生命周期已经结束、却仍被强引用而无法回收的对象），并执行堆转储与引用链分析；它与低开销的线上内存趋势监控用途不同。

### 7.1 LeakCanary 2.x 工作流程

LeakCanary 官方建议通过 `debugImplementation` 引入完整的 `leakcanary-android`，标准 Activity、Fragment、Fragment view、ViewModel 和 Service 的观察无需业务初始化代码。对自定义生命周期对象，可以在对象不再使用时调用 `AppWatcher.objectWatcher.watch()`。

工作链分为四步：

1. `ObjectWatcher` 用弱引用观察已结束生命周期的对象；弱引用不会为了观察而阻止对象被垃圾回收。
2. 默认等待一段时间并触发 GC；对象仍存在时，将其标为 retained 候选，不会立即断言它就是泄漏根因。
3. retained 数量达到配置阈值后生成 HPROF（Java 堆快照文件）；生成堆转储会暂停应用。
4. LeakCanary 的 Shark 分析器检查引用图，并给出从 GC root（垃圾回收器视为始终可达的根对象）到 retained object 的引用路径。

### 7.2 架构特点

- **自动安装**：库通过 AndroidX Startup 和应用清单（manifest）组件完成默认观察器安装，正常接入不要求在 `Application.onCreate()` 前手动调用配置。
- **分析与停顿分开看**：Shark 可以在后台执行分析，但生成堆转储时会暂停虚拟机（VM），不能描述成全程“非阻塞”。
- **结果需要人工解释**：retained object 是候选证据；已知库泄漏（library leak）、测试框架持有和应用自身泄漏需要结合引用链分类。

### 7.3 线上边界

LeakCanary 官方不建议把完整 `leakcanary-android` 放入发布构建（release build），库还会阻止误装到不可调试 APK。生产环境若只需要 retained object 计数，可单独评估 `leakcanary-object-watcher-android`，并用远程开关、设备条件和隐私规则限制范围。生产环境生成堆转储会造成明显停顿，也可能包含敏感数据，因此必须采用专门的授权诊断方案，不能照用调试构建的默认配置。

---

## 8. 线上采集的边界条件

### 8.1 性能开销

性能监控本身带来的开销需要控制在可接受范围。

**异步采集：**
不能把所有采集都机械地切到后台线程：UI 状态和帧回调有明确的线程语义，跨线程读取 View 反而会出错。应在回调线程读取最小且线程安全的快照，再把聚合、压缩、写入存储和上传交给后台执行器。`StatsManager.setPullAtomCallback()` 使用调用方指定的 executor（任务执行器）；`JankStats.OnFrameListener` 的交付线程随平台机制变化，两者都需要快速返回。

**批量处理：**
StatsD 的 config 订阅机制按 `StatsdConfig` 定义的周期聚合原子事件，`getReports()` 返回的是聚合后的报告。App 自建的指标缓冲也应该按周期批量写入上报通道，而不是每采集一点就发一次网络请求。

**分配与所有权：**
高频路径使用有界缓冲区和紧凑事件结构，避免无上限字符串、堆栈和标签。对象池是重复使用预先创建对象的机制，但它会增加同步、生命周期和旧数据残留风险，不应默认启用。JankStats 已复用回调对象，需要跨回调保存时按文档复制；其他对象是否复用应以基准测试为准。

**开销门禁：**
不要把固定 CPU 或内存比例当成所有设备的安全线。对关闭与开启监控的两组构建执行 Macrobenchmark 或可重复的内部基准，比较 CPU 时间、内存分配、启动、帧超时、耗电和上传字节；再按设备层与场景设定预算。SDK 版本或采样策略改变后重新测量，超出预算就减少字段、附件或样本纳入率。

### 8.2 权限边界

Android 17 的性能监控权限分层明确：

**StatsD config/report/query 路径（需要特权权限）：**
- `REGISTER_STATS_PULL_ATOM`：注册 pull 回调
- `DUMP` + `PACKAGE_USAGE_STATS`：注册 config、读取 `getReports()`
- `READ_RESTRICTED_STATS`：使用 `query()` 查询 SQL 结果

**App 自建指标路径（无需特殊权限）：**
- `Debug.MemoryInfo`：无需额外权限
- `ActivityManager.getProcessMemoryInfo()`：普通 App 仅能读取同 UID 进程，且调用频率受限
- `Debug.getRuntimeStat()`
- `PowerManager.isPowerSaveMode()`

**网络上报权限：**
- `INTERNET`（清单声明即可）

后台持续上传应使用与任务语义匹配的 API。需要在进程重启后继续、且允许延后的批量上传可以交给 WorkManager（Jetpack 持久化后台任务调度器），并通过网络、电量和存储约束（constraint）声明执行条件；前台页面内的短时采样随页面生命周期停止。应明确写出具体 API 和约束，不能只说“Android 17 限制更严格”。

### 8.3 约束驱动的采集降级状态机

监控 SDK 不能把后台定时器当成持续时钟。缓存进程（cached app）可能被冻结，WorkManager 只保证在约束允许时获得执行机会，内存压力下继续申请大附件还会放大故障。实现时可以把生命周期、任务回调和系统结果转换成下面的状态机：

| 状态 | 采集 | 本地处理 | 上报 |
| --- | --- | --- | --- |
| Foreground（前台） | 用户旅程、帧、网络、低频内存与业务指标 | 有界聚合、采样和脱敏 | 批量发送或入队 |
| UI hidden / Background（界面不可见 / 后台） | 停止周期轮询，只保留必要业务事件 | 释放可重建缓存，写小型状态摘要 | 交给受约束的持久化任务 |
| Cached / Frozen（缓存 / 冻结） | 不假设存在用户态执行机会 | 不补造冻结期间样本 | 等待系统解冻 |
| Restart / Resume（重启 / 恢复） | 查询退出记录、注册性能剖析结果监听、读取待传队列 | 标记不可观测区间，去重并恢复 | 先传关键摘要，再按预算传附件 |
| Memory pressure observed（观察到内存压力） | 停止高成本性能剖析与大对象采集 | 缩小缓冲区、拒绝新批次、保存丢弃计数 | 不因压力立即制造额外网络工作 |

状态转换只能由实际生命周期、任务开始/停止和公开系统结果驱动。App 无法可靠查询“当前是否被冻结”，因为被冻结时本身就没有执行代码的机会；恢复后只能承认这段数据缺失，并记录 `unsupported`、`not_scheduled`、`frozen_gap`、`budget_exhausted` 等原因，不能用零填充。

---

## 9. 数据处理与上报策略

以下策略基于工程实践总结，不绑定 Android 17 StatsD 平台的特定配置项。

### 9.1 本地缓存机制

**有界缓冲：**
内存缓冲按字节数与事件数设双重上限，进程恢复后仍有价值的数据写入应用私有目录。配额根据设备存储、事件价值和平均上传能力校准，不用固定时间窗口替代容量管理。

**中断后续传：**
每个批次带稳定 ID、schema 版本、序列范围和内容摘要；内容摘要用于判断数据是否一致。服务端按批次或事件 ID 幂等确认，即重复提交同一数据时只确认一次；客户端只在收到确认后回收已持久化数据。损坏批次进入隔离区，不能让一个坏文件永久阻塞队列。

### 9.2 上报策略

- 普通性能批次使用持久化调度，并按产品策略选择 `CONNECTED`（已有网络连接）或 `UNMETERED`（非计量网络）等 WorkManager 网络约束；大附件还可要求充电和存储空间充足。
- Crash、ANR 摘要与性能批次使用不同优先级，但“高优先级”仍不表示崩溃进程必须现场发网，也不绕过用户的数据设置。
- 失败重试采用带随机扰动的退避：连续失败时逐步延长等待时间，并加入随机偏移，避免大量客户端同时重试。客户端还要尊重服务端 `Retry-After` 指定的再次请求等待时间和自身后台配额。认证失败、schema 不兼容等永久错误进入隔离或升级流程，不能无限重试。
- 使用 WorkManager 的命名唯一任务（unique work）或等价队列键，避免网络恢复时重复创建同一上传任务。网络约束失效时让调度器停止并稍后重试，不在网络状态回调 `NetworkCallback` 中直接发起整批上传。

---

## 10. 性能监控最佳实践

### 10.1 监控范围控制

性能监控可以按信息价值和采集成本分级。下面是职责示例，具体纳入率由测量预算和统计目标决定。

**事实计数与分母：**
- Crash、ANR 与进程退出记录；
- 启动、会话、页面访问等统计分母；
- 监控 SDK 自身的丢弃、上传和配置状态。

这类数据优先保证口径连续，但仍要受用户同意、隐私规则和技术可用性约束。“优先”不等于所有附件都全量上传。

**持续性能摘要：**
- 帧率 / 卡顿帧（JankStats）
- 内存使用率和 GC 频率
- 网络时延与错误率

摘要按设备层、版本和场景确定性采样，服务端保留纳入概率。

**按需诊断附件：**
- Perfetto trace、heap dump、详细行为窗口；
- 高频逐帧明细、完整网络阶段数据；
- 设备与进程快照。

这类数据只在预设配额、远程诊断或代表样本中获取。启动“慢”的阈值应基于 Android Vitals 定义、产品 SLO（Service Level Objective，服务等级目标）和分位数基线，不写成无来源的固定秒数。

### 10.2 隐私保护

1. 敏感数据在写入本地缓冲前完成最小化与脱敏。
2. 网络上报使用 TLS，并对服务端身份、证书策略和失败模式进行测试。
3. 日志、URL、UI 状态标签（如页面或交互阶段）和业务标签不嵌入原始用户标识或用户内容。
4. 需要跨事件关联时使用有明确保留期的假名标识；哈希并不自动等于匿名化。
5. heap dump、trace 和原始日志采用更严格的授权、访问审计与删除策略。

### 10.3 数据生命周期

- App 侧原始事件按字节配额、事件价值和已确认状态回收。
- 服务端原始样本只保留完成定位和重算所需的最短周期，访问必须可审计。
- 聚合数据按趋势比较和合规需求设周期，并记录聚合口径版本。
- 删除流程覆盖主存储、索引、缓存和备份到期策略；用户请求删除时能定位关联数据。

保留时长应由数据分类、业务 SLO、地区法规和成本共同确定，不存在适用于所有项目的固定天数。

---

## 11. Android 17 内存监控适配建议

### 11.1 普通 App 的连续监控

Android 14–17 都可以使用 `Debug.MemoryInfo` 采集同 UID 进程的低频内存快照，不需要为 Android 17 写一条内容相同的版本分支。采样记录至少包含系统日期时间（wall clock）、不受系统校时影响的单调时间 `elapsedRealtime`、进程启动序列、前后台状态和最近一次内存压力等级（trim level）。长时间没有样本，只能说明进程没有执行采样；原因可能是冻结、调度延迟、进程退出或任务被取消。

`ComponentCallbacks2.onTrimMemory()` 是内存压力提示，不能当成每次回收或每次 compaction 的通知。收到回调时记录 level 和业务状态，减少可回收缓存；不要通过高频 PSS 轮询决定运行时核心逻辑。

### 11.2 Android 17 新字段与退出补偿

API 37 在 `ActivityManager.MemoryInfo` 新增 `freeMem`，表示未使用 RAM；`availMem` 还考虑可回收内存，两者含义不同。应用判断系统是否接近低内存时，优先使用 `lowMemory`、`threshold`、`availMem` 和 trim callback，不要把 `freeMem` 越低直接解释成异常。

进程重启后，使用 `ApplicationExitInfo` 核对近期退出原因和时间，再与最近一份内存快照关联。该关联只能说明“退出前观察到什么”；没有系统 trace 时，无法证明 MemoryLimiter、LMKD（Low Memory Killer Daemon，Android 低内存终止守护进程）或某次 Compaction 是根因。

### 11.3 系统组件与实验室诊断

特权组件可以结合 StatsD、`dumpsys`、Perfetto、cgroup 文件和 `MemoryLimiter` 事件分析系统策略。普通 App 不应把读取 `FREEZER_EVENT`、其他进程 `/proc` 或 cgroup 控制文件作为生产环境采集方式。需要验证 Android 17 内存策略时，在可控设备上同时采集 App 快照与系统 trace，并以 `android-17.0.0_r1` 的 `CachedAppOptimizer.java`、`MemoryLimiter.java` 和 JNI 实现解释事件。

---

## 总结

Android 14–17 的性能监控由多组权限和用途不同的 API 组成，可以按三层理解：

1. **系统层**：StatsD 通过 `StatsManager.addConfig()` + `getReports()` 向特权 App 提供 `atoms.proto` 中系统 atom（如 `AppStartOccurred`（ID 48）、`AnrOccurred`）的聚合报告；`setPullAtomCallback()` 是特权组件向 statsd 提供 pulled atom 数据的入口。`ApplicationExitInfo` 属于 ActivityManager 的独立公开查询模型，位于 StatsD atom 体系之外。权限边界为：`setPullAtomCallback()` 需要 `REGISTER_STATS_PULL_ATOM`，`addConfig()` / `getReports()` 同时需要 `DUMP` 和 `PACKAGE_USAGE_STATS`，`query()` 需要 `READ_RESTRICTED_STATS`。
2. **框架层**：AndroidX `JankStats` 负责帧级实时诊断，`Debug.MemoryInfo` 负责进程级内存采集——两者都不需要特殊权限。
3. **App 层**：电池感知采样率、网络指标聚合、上报策略和缓存管理由 App 自行实现或通过 Firebase Performance 等 SDK 接入。

Android 17 增加了 MemoryLimiter 的设备可选能力和 `ActivityManager.MemoryInfo.freeMem` 字段。Compaction 与 Freezer 在更早版本已经存在；`libmeminfo` / `libmemevents` 仍是系统侧能力，没有为普通 App 增加对象跟踪接口。线上系统应保存一致分母、策略版本、纳入概率和缺失原因，并按前台、后台、冻结、恢复与内存压力状态降级；详细 trace、heap dump 与逐帧数据只在成本和授权条件允许时采集。

## 延伸阅读

- [Android Performance Vitals](https://developer.android.com/topic/performance/vitals) — Google 官方性能指标定义与最佳实践
- [ActivityManager](https://developer.android.com/reference/android/app/ActivityManager) — `getProcessMemoryInfo()` 的 UID 与频率限制
- [ActivityManager.MemoryInfo](https://developer.android.com/reference/android/app/ActivityManager.MemoryInfo) — API 37 `freeMem` 与 `availMem` 的口径
- [android.os.Debug](https://developer.android.com/reference/android/os/Debug) — Native heap、PSS、RSS 与运行时统计
- [Firebase Performance Monitoring](https://firebase.google.com/docs/perf-mon) — Firebase 性能监控接入指南，含采样率配置与 URL pattern 归一化
- [Firebase custom URL patterns](https://firebase.google.com/docs/perf-mon/custom-url-patterns) — URL pattern 与成功码配置
- [ApplicationExitInfo API](https://developer.android.com/reference/android/app/ApplicationExitInfo) — Android 11+ 退出原因归因 API
- [JankStats — AndroidX metrics-performance](https://developer.android.com/reference/androidx/metrics/performance/JankStats) — 帧级卡顿检测库官方文档
- [JankStats 使用指南](https://developer.android.com/topic/performance/jankstats) — 回调线程、对象复用和 UI 状态
- [Battery Historian 设置](https://developer.android.com/topic/performance/power/setup-battery-historian) — 维护状态、bugreport 与本地分析
- [WorkManager constraints](https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work#work-constraints) — 持久化上传的网络、电量与存储条件
- [LeakCanary Getting Started](https://square.github.io/leakcanary/getting_started/) — Debug 构建接入边界
- [Debug.MemoryInfo](https://developer.android.com/reference/android/os/Debug.MemoryInfo) — 进程内存使用明细 API
- [AOSP Android 17：StatsManager.java](https://android.googlesource.com/platform/packages/modules/StatsD/+/refs/tags/android-17.0.0_r1/framework/java/android/app/StatsManager.java)
- [AOSP Android 17：CachedAppOptimizer.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java)
- [AOSP Android 17：MemoryLimiter.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryLimiter.java)
- [AOSP Android 17：MemoryLimiter JNI](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/jni/com_android_server_am_MemoryLimiter.cpp)
- [Android common kernel：android17-6.18-2026-06_r6 cgroup v2](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/admin-guide/cgroup-v2.rst)
- [Android common kernel：android17-6.18-2026-06_r6 memcontrol.c](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/memcontrol.c)
- [StatsD atoms.proto](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/proto_logging/stats/atoms.proto) — android-17.0.0_r1 中完整原子定义
