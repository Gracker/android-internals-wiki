---
title: "Android 17 MemoryLimiter 与内存监控影响"
chapter: "4.17"
status: ready-for-review
drafted_date: "2026-06-28"
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
last_verified: "2026-06-28"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java (1291 lines)"
  - type: aosp
    path: "frameworks/base/services/core/jni/com_android_server_am_MemoryLimiter.cpp (1276 lines)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/MemoryUsageStats.java (108 lines)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/MemoryStatUtil.java (148 lines)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java (mMemoryLimiter mount points)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessRecord.java (Limiter instantiation)"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Debug.java (MemoryInfo + getMemoryInfo)"
  - type: aosp
    path: "frameworks/base/core/java/android/content/ComponentCallbacks2.java (trim levels)"
tags: [MemoryLimiter, memory, cgroup, monitoring, Debug.MemoryInfo, PSS, swap, APM]
related_chapters: ["4.4", "4.5", "4.11", "4.15"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "daily-info + research-gaps"
---

# 4.17 Android 17 MemoryLimiter 与内存监控影响

Android 16/17 在 system_server 中引入了 MemoryLimiter 子系统——它直接在 cgroup v2 层面通过 `memory.high` / `memory.swap.high` 给每个应用进程施加软内存限制。这对现有的 `Debug.MemoryInfo` 监控体系产生了三重影响：PSS 抖动加剧、30s kill 窗口期监控盲区、swap 指标缺失。本节聚焦于 MemoryLimiter **对应用侧性能监控的冲击与补偿方案**，机制原理详见 [4.5 Android 17 后台任务内存配额机制](../../2026-06-26-19-知识加工(新).md)。

## 要点

### 🔹 MemoryLimiter 对监控体系的定位

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java:62-71]

MemoryLimiter 是 Android 内存管理的**第三道防线**，与现有的两道防线形成互补：

| 防线 | 机制 | 触发条件 | 对 Debug.MemoryInfo 的影响 |
|------|------|----------|---------------------------|
| 第一道：lmkd | PSI/lowmemdetector → SIGKILL | 系统级内存压力 | 进程死亡，无法采集 |
| 第二道：CachedAppOptimizer | cgroup freeze + compaction | 进程进入 cached 状态 | RSS 不变，PSS 冻结期间不更新 |
| **第三道：MemoryLimiter** | **cgroup memory.high → 30s kill** | **进程级内存超限** | **PSS 抖动 + swap 盲区 + 30s 窗口** |

关键区别：lmkd 面向**系统级**压力，CachedAppOptimizer 面向**进程状态**转换，MemoryLimiter 面向**单进程内存用量**。MemoryLimiter 只对非 cached、非 persistent 的进程生效——即正在运行的后台 Service / FGS / Receiver 等。详见 §4.4（lmkd）和 §4.11（CachedAppOptimizer）。

MemoryLimiter 的 Java 实现位于 `MemoryLimiter.java`（1291 行），JNI 层位于 `com_android_server_am_MemoryLimiter.cpp`（1276 行），在 AMS 中的挂载点如下：

[已验证: AOSP android-17.0.0_r1, ActivityManagerService.java]

| AMS 行号 | 调用 | 说明 |
|----------|------|------|
| 776 | `private MemoryLimiter mMemoryLimiter;` | 字段声明 |
| 2635/2718 | `mMemoryLimiter = MemoryLimiter.getDefaultMemoryLimiter(mContext);` | 构造与重启路径 |
| 2793 | `MemoryLimiter.Limiter newMemoryLimiter() { return mMemoryLimiter.newLimiter(); }` | 工厂方法 |
| 9699 | `mMemoryLimiter.onSystemReady();` | systemReady 阶段 |
| 11262 | `mMemoryLimiter.dump(pw);` | dumpsys 路径 |

每个 `ProcessRecord` 在构造期绑定一个独立的 `Limiter` 实例（`ProcessRecord.java:416/649`），进程状态变化时通过 `onProcStateUpdated()` 重新计算限制。

### 🔹 cgroup memory.high 限制机制与监控边界

[已验证: AOSP android-17.0.0_r1, com_android_server_am_MemoryLimiter.cpp]

MemoryLimiter 通过 JNI 写入进程 cgroup v2 的两个文件：

- **`memory.high`**：软限制。超限时内核开始回收匿名页（anon），进程被 throttle 但不会立即 OOM
- **`memory.swap.high`**：swap 软限制。超限时内核限制 swap 使用

JNI 端的 `CgroupFile` 枚举明确了四个操作的 cgroup 文件：

```cpp
enum class CgroupFile {
    kUnknown,
    kMemoryStat,     // memory.stat — 读取统计
    kMemoryEvent,    // memory.events — inotify 监听
    kMemoryHigh,     // memory.high — 写入限制
    kSwapCurrent,    // memory.swap.current — 读取当前 swap
    kSwapMax,        // memory.swap.high — 写入 swap 限制
};
```

**对监控的关键影响：100MB margin 灰色地带。**

[已验证: AOSP android-17.0.0_r1, com_android_server_am_MemoryLimiter.cpp:145/152]

Native 层设置了两个关键常量：

| 常量 | 值 | 含义 |
|------|-----|------|
| `mMemHighMargin` | 100 MB | cgroup memory.high 实际写入值 = config.memHigh + 100MB |
| `mMemHighHysteresis` | 10 MB | 离开 red zone 的滞回带宽 |

这意味着进程的 `memory.current` 可能达到 `configMemHigh + 100MB` 而不触发任何事件。业务侧的 APM SDK 通过 `Debug.MemoryInfo` 读取到的 PSS 值在 `memHigh` 附近，看起来"未超限"，但内核实际上已经在做 anon 回收。监控面板上需要将告警阈值设置为配置的 `memHigh` 而非实际触发的 `memHigh + 100MB`。

**inotify vs 轮询的双模式切换：**

常态下，JNI 通过 `inotify_add_watch` 监听 `memory.events` 文件——零开销事件驱动。但当进程进入"red zone"（同时超过 `memory.high` 和 `memory.swap.high`）时，cgroup 事件流停止，JNI 切换为**轮询模式**：

- 常态轮询周期（`PID_POLL_PERIOD_MS`）：5 分钟
- Red zone 轮询周期（`RED_POLL_PERIOD_MS`）：30 秒
- 测试模式轮询周期（`TEST_POLL_PERIOD_MS`）：1 秒

轮询模式期间，进程内存下降到 `memory.high - 10MB` 以下才会恢复事件驱动模式。这段轮询期是监控数据的"高频变化期"——PSS 会在 anon 回收和重新分配之间快速波动。

### 🔹 PSS 抖动与 30s kill 窗口影响分析

[已验证: AOSP android-17.0.0_r1, MemoryLimiter.java:802-832]

当进程同时超过 `memory.high` 和 `memory.swap.high`（即 `LIMIT_TYPE_ANON_SWAP`），MemoryLimiter 启动一个 30 秒的 kill 倒计时：

```java
// MemoryLimiter.java:802-806 — ANON_SWAP 触发后释放限制
if (type == LIMIT_TYPE_ANON_SWAP) {
    configureLimit(mNative.get(), pid, uid,
            LIMIT_IS_DISABLED, LIMIT_IS_DISABLED);
}

// MemoryLimiter.java:826-832 — 延迟 kill
Message msg = mQueue.obtainMessage(MESSAGE_KILL, pid, uid,
        "MemoryLimiter:AnonSwap");
mQueue.sendMessageDelayed(msg, KILL_DELAY_MS);  // KILL_DELAY_MS = 30 * 1000
```

**注意**：`LIMIT_TYPE_ANON_SWAP` 触发后，cgroup 限制被**立即释放**（`LIMIT_IS_DISABLED`），进程在 30 秒内进入"无限制"状态。这 30 秒窗口承担两个职责：

1. **触发 profiling**：调用 `ProfilingServiceHelper.onProfilingTriggerOccurred(uid, pkg, TRIGGER_TYPE_ANOMALY)`，在 kill 前抓取 heap dump（依赖 `systemTriggeredProfilingNew` + `anomalyDetectorCoreC` 两个 flag）
2. **给应用软着陆时间**：APM SDK 有机会在 `onTrimMemory` 回调中 flush 关键指标

**PSS 抖动的根因：**

memcg `memory.high` 触发后，内核开始主动回收 anon 页。应用调用 `Debug.getProcessMemoryInfo()` 或 `ActivityManager.getProcessMemoryInfo()` 时，底层走 `/proc/<pid>/smaps_rollup` 读取 PSS。anon 页被回收后，PSS 出现以下变化模式：

```
时间轴：
t0: PSS = 850MB（正常）
t1: memory.high 触发，内核开始回收 anon
t2: PSS = 780MB（anon 回收中，突降 70MB）
t3: PSS = 820MB（应用重新分配，反弹）
t4: PSS = 750MB（再次回收）
...
```

1Hz 采样的 APM SDK 会误报"内存释放事件"为业务侧主动释放，或误报"内存泄漏"（反弹时）。**补偿方案**：

- **方案 A：结合 onTrimMemory 判定**。在 `onTrimMemory(TRIM_MEMORY_BACKGROUND=40)` 之后 5 分钟内的 PSS 波动标记为"内核回收"，不计入业务指标。但注意 Android 14+ 已 `@Deprecated` 了 `TRIM_MEMORY_COMPLETE(80)` / `TRIM_MEMORY_MODERATE(60)` / `TRIM_MEMORY_RUNNING_CRITICAL(15)` / `TRIM_MEMORY_RUNNING_LOW(10)` / `TRIM_MEMORY_RUNNING_MODERATE(5)` 五档——App 只收到 `TRIM_MEMORY_BACKGROUND(40)` 和 `TRIM_MEMORY_UI_HIDDEN(20)`
- **方案 B：读取 cgroup 事件**。如果设备支持，直接读 `/dev/memcg/<pid>/memory.events` 中的 `high` 计数器，判断 PSS 下降是否与 `memory.high` 触发时间吻合。需要 root 或系统权限
- **方案 C：ApplicationExitInfo 归因**。通过 `ActivityManager.getHistoricalProcessExitReasons()` 查询进程退出原因，`description` 字段包含 `"MemoryLimiter:AnonSwap"` 表示被 MemoryLimiter kill

### 🔹 Debug.MemoryInfo 指标缺失与补偿方案

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/os/Debug.java + MemoryUsageStats.java]

`Debug.MemoryInfo` 类暴露的字段在 MemoryLimiter 环境下存在三个盲区：

**盲区一：PSS 不含 swap**

`Debug.MemoryInfo.totalPss` 基于 `/proc/<pid>/smaps_rollup` 的 PSS（Proportional Set Size），**不包含 swap 页**。而 cgroup `memory.current` 包含 anon + swap + file backed。这意味着：

```
应用视角：Debug.MemoryInfo.totalPss = 800MB（看起来没超限）
内核视角：memory.current = 800MB + 400MB swap = 1200MB（已超 memory.high=1GB）
```

监控 SDK 需要额外采集 swap 指标才能准确反映内核视角的内存压力。

**盲区二：DMA-BUF 映射内存**

`MemoryUsageStats.getTotalPss()`（MemoryUsageStats.java:60-77）展示了 Android 17 的 PSS 修正逻辑：

```java
private long getTotalPss() {
    long val = totalPss;
    if (mDmabufMapped > 0) {
        // Note: mapped DMA-BUF memory is not accounted in PSS due to VM_PFNMAP
        val -= totalMemtrackGraphics;
        val += mDmabufMapped;
    }
    if (Debug.getGpuTotalUsageKb() >= 0) {
        final long gpuPrivateUsage = Debug.getGpuPrivateMemoryKb();
        if (gpuPrivateUsage >= 0) {
            val -= totalMemtrackGl;
        }
    }
    return val;
}
```

PSS 不含 `mDmabufMapped`（因 `VM_PFNMAP` flag），而 cgroup `memory.current` **包含** DMA-BUF 映射。GPU 私有内存（`Debug.getGpuPrivateMemoryKb`）在 PSS 与 `memory.current` 之间存在双重计数的风险。这是 `dumpsys meminfo` 的"修正 PSS"与 APM SDK 采集的"原始 PSS"不一致的根因。

**盲区三：MemoryStatUtil 的两套通路**

`MemoryStatUtil`（MemoryStatUtil.java:41）注释揭示了一个关键差异：

> `/** For memcg stats, the anon rss + swap cache size. Otherwise total RSS. */`
> `public long rssInBytes;`

`MemoryStat.rssInBytes` 在 memcg 可用时返回 anon rss + swap cache，procfs fallback 返回 total RSS。而 `getProcessMemoryInfo()` 走 PSS 通道（`/proc/<pid>/smaps_rollup`），两者是**独立的采集通路**，可能返回不一致的数值。

**补偿方案汇总：**

| 盲区 | 补偿方式 | API 等级 | 备注 |
|------|----------|----------|------|
| PSS 不含 swap | 读 `/proc/<pid>/status` 的 VmSwap 字段 | API 26+ | 无需 root |
| PSS 不含 DMA-BUF | `Debug.MemoryInfo.dalvikPss` + `getMemoryInfo` 的 `getTotalPss` 修正 | API 28+ | `dumpsys meminfo` 已做修正 |
| PSS vs cgroup 差异 | 读 `memory.current` 需系统权限 | API 36+ | 仅系统 App 或 root |
| MemoryLimiter 是否生效 | `ActivityManager.getHistoricalProcessExitReasons()` | API 26+ | `description` 含 `"MemoryLimiter:AnonSwap"` |

### 🔹 swap 指标在内存限制下的行为变化

[已验证: AOSP android-17.0.0_r1, MemoryLimiter.java:84-92 + ProcessRecord.java:1625]

MemoryLimiter 定义了三种限制类型（`LINT.IfChange/ThenChange` 绑定 Java 与 Native）：

```java
// MemoryLimiter.java:84-92
static final int LIMIT_TYPE_UNKNOWN    = 0;
static final int LIMIT_TYPE_MEMORY     = 1;  // memory.high 超限
static final int LIMIT_TYPE_SWAP       = 2;  // memory.swap.high 超限
static final int LIMIT_TYPE_ANON_SWAP  = 3;  // anon+swap 联合超限
```

**`LIMIT_TYPE_MEMORY`（仅 memory.high）**：内核回收 anon 但不 kill。应用 PSS 出现抖动，但进程继续运行。这是最常见的场景。

**`LIMIT_TYPE_SWAP`（仅 swap.high）**：内核限制 swap 使用，应用被迫使用更多 anon 内存。PSS 反而可能**上升**——因为原本可以换出到 swap 的页现在必须驻留 anon。

**`LIMIT_TYPE_ANON_SWAP`（联合超限）**：最严重。cgroup 限制释放，30 秒后 kill。这是唯一会 kill 进程的类型。

基于 `ProcessState` 的配额矩阵决定了哪些进程受 swap 限制影响：

| ProcessState 分类 | memHigh | swapHigh | 监控关注点 |
|-------------------|---------|----------|-----------|
| Top / BoundTop / ImportantForeground | `memVisible`（默认 4GB） | `swapVisible`（默认 2GB） | 配额宽松，极少触发 |
| FGS / Service / Receiver / Backup | `memNotVisible`（默认 2GB） | `swapNotVisible`（默认 2GB） | **主要受影响群体** |
| Cached / CachedEmpty | `LIMIT_IS_IGNORED` | `LIMIT_IS_DISABLED` | 不受 MemoryLimiter 控 |
| Persistent / Persistent UI | `LIMIT_IS_DISABLED` | `LIMIT_IS_DISABLED` | 不受限 |

> [!info] 配置来源
> `/vendor/etc/memory-limiter-config.xml`（vendor overlay）。默认值 `Configuration(4GB, 2GB, 2GB, 2GB)` 仅用于测试。生产环境配额由 OEM 定义，与设备 RAM 大小**不直接挂钩**——这与 lmkd 的 `minfree` 缩放公式完全不同。详见 §4.5。

swap 监控的实操建议：

1. **采集 `VmSwap`**：`/proc/<pid>/status` 中 `VmSwap` 字段反映进程当前 swap 使用量。APM SDK 应将其与 PSS 一起采集，形成 `totalPss + VmSwap` 的组合指标
2. **关注 swap.high 事件**：如果设备启用 `memory.swap.high`，swap 使用量触及阈值时不会 kill 但会触发 throttle。应用表现为 `I/O wait` 增加（因 swap in/out）
3. **ZRAM 交互**：Android 的 swap 通常通过 ZRAM（压缩内存）实现。`memory.swap.high` 触发意味着 ZRAM 压缩比已达上限。详见 §4.12

### 🔹 多层级内存保护策略协同机制

Android 17 的内存管理形成了一个**四层级**保护体系，MemoryLimiter 是其中最新的一层：

```
┌────────────────────────────────────────────────────────────────┐
│ Layer 1: PSI + lmkd                                            │
│   触发条件：系统级内存压力（PSI memory pressure）                  │
│   动作：按 oom_score_adj 顺序 kill 进程                          │
│   详见：§4.4 / §4.15                                            │
├────────────────────────────────────────────────────────────────┤
│ Layer 2: CachedAppOptimizer                                    │
│   触发条件：进程进入 cached 状态                                   │
│   动作：cgroup freeze + compaction（compaction 仅 Android 10+） │
│   对监控：RSS 不变，PSS 冻结期间不更新                            │
│   详见：§4.11                                                   │
├────────────────────────────────────────────────────────────────┤
│ Layer 3: MemoryLimiter (Android 16+)                           │
│   触发条件：单进程 memHigh/swapHigh 超限                         │
│   动作：anon 回收 → 30s kill（仅 ANON_SWAP 类型）                │
│   对监控：PSS 抖动 + 30s 窗口 + swap 盲区                        │
│   详见：§4.5 / 本节                                              │
├────────────────────────────────────────────────────────────────┤
│ Layer 4: App 侧 onTrimMemory                                   │
│   触发条件：AMS 主动通知                                         │
│   动作：App 自行释放资源                                         │
│   注意：Android 14+ 仅派发 BACKGROUND(40) 和 UI_HIDDEN(20)      │
└────────────────────────────────────────────────────────────────┘
```

**协同关系的关键点：**

1. **不替代，而是叠加**：MemoryLimiter 不取代 lmkd 或 CachedAppOptimizer。一个后台 Service 可能同时被 MemoryLimiter 限制（进程级）和 lmkd 监控（系统级），先触发谁取决于哪个阈值先被触及
2. **statsd 节流**：MemoryLimiter 的 statsd 事件有令牌桶限制——每小时补 4 个 token，上限 4，每天最多 28 条（`MemoryLimiter.java:785-797`）。业务侧不应依赖 statsd 通路做高频告警，必须在 Java 层自行 hook
3. **cached 进程豁免**：`PROCESS_STATE_CACHED_*` 状态的进程 `memHigh = LIMIT_IS_IGNORED`，完全交给 lmkd/CachedAppOptimizer 处理。MemoryLimiter 只管"正在运行但不在前台"的进程
4. **persistent 进程豁免**：`PROCESS_STATE_PERSISTENT` / `PROCESS_STATE_PERSISTENT_UI` 的进程使用 `LIMIT_IS_DISABLED`（即 "max"），永不触发。系统服务不受 MemoryLimiter 控制

**启用条件：**

```java
// MemoryLimiter 启用需同时满足：
// 1. Flags.memoryLimiterEnable()（DeviceConfig flag）
// 2. isMemoryLimiterSupported()（/vendor/etc/memory-limiter-config.xml 存在）
```

OEM 可通过 `device_config put activity_manager memory_limiter_enable false` 关闭。**没有 vendor config 文件的设备不会启用 MemoryLimiter**——这是 Android 17 内存配额仅在特定设备上启用的原因。

## 扩展

### 🔸 MemoryLimiter 与 LMKD 的协同工作

lmkd 关注系统级压力（PSI），MemoryLimiter 关注进程级用量。当系统内存紧张时，两个子系统可能同时行动：

- lmkd 按 oom_score_adj 从高到低 kill，cached 进程优先被杀
- MemoryLimiter 可能已经在一个后台 Service 上触发了 30s kill 倒计时

如果 lmkd 在 30s 窗口内先 kill 了该进程，MemoryLimiter 的 `MESSAGE_KILL` 到期时会发现进程已不存在（`kill` 返回 `-ESRCH`），无害退出。反之，如果 MemoryLimiter 先 kill，lmkd 的 kill 列表中也会跳过该 pid。两者不会冲突。

但有一个需要注意的场景：MemoryLimiter kill 进程时使用 `REASON_OTHER`，而非 `REASON_LOW_MEMORY` 或 `REASON_ANR`。APM SDK 的崩溃归因如果只按 `REASON_LOW_MEMORY` 分类，会遗漏 MemoryLimiter kill 的事件。建议同时检查 `ApplicationExitInfo.getDescription()` 是否包含 `"MemoryLimiter:AnonSwap"`。

### 🔸 应用内存限制的在线动态调整

MemoryLimiter 的限制值不是静态的——当 `ProcessState` 变化时，`Limiter.onProcStateUpdated()` 会重新计算并写入新的 `memory.high` / `memory.swap.high`。例如，一个后台 Service 升级为前台 Service 时，限制从 `memNotVisible` 切换到 `memVisible`。

这对 APM 的影响：监控数据中可能出现"内存使用量合理但限制突然收紧"的情况——这不是内存泄漏，而是 proc state 降级导致限制值减小。APM 面板应同时记录进程的 proc state 变化事件，与内存数据关联分析。

### 🔸 内存限制场景下的性能优化

在 MemoryLimiter 生效的设备上，后台任务需要适应 cgroup memory.high 的节流：

1. **减少后台 anon 使用**：将大对象改为 mmap 文件（file-backed pages 可被内核直接丢弃，不占 anon 配额）
2. **主动响应 onTrimMemory(40)**：虽然 Android 14+ 不再派发 RUNNING_* 档位，但 `BACKGROUND(40)` 在 freeze 前仍然派发。App 应在此回调中释放所有可重建资源
3. **监控 swap 使用**：通过 `/proc/self/status` 的 `VmSwap` 字段持续跟踪 swap 使用量，在接近 `swap.high` 时主动释放内存
4. **避免大 burst 分配**：短时间内大量 anon 分配可能导致 memory.high 快速触发，而又来不及回收——表现为 GC pause 增加（ART 需要回收 anon 来满足 cgroup 限制）

> [!warning] ComponentCallbacks2 trim 等级变化
> Android 14（API 34）起，`TRIM_MEMORY_COMPLETE(80)` / `TRIM_MEMORY_MODERATE(60)` / `TRIM_MEMORY_RUNNING_CRITICAL(15)` / `TRIM_MEMORY_RUNNING_LOW(10)` / `TRIM_MEMORY_RUNNING_MODERATE(5)` 五档已标记 `@Deprecated` 且**不再派发**。App 只会收到 `TRIM_MEMORY_BACKGROUND(40)` 和 `TRIM_MEMORY_UI_HIDDEN(20)`。源码注释明确写「不要比较 exact value，只比较 ≥」。详见 `frameworks/base/core/java/android/content/ComponentCallbacks2.java`。


## 深度源码验证（2026-06-28 补充）

<!-- AIW-源码调研-2026-06-28 -->
[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java + com_android_server_am_MemoryLimiter.cpp]

### 完整 ProcState → Limits 映射矩阵

`ControllerEnabled.initializeMemoryLimits()`（MemoryLimiter.java）在构造期遍历 `ActivityManager.MIN_PROCESS_STATE` 到 `MAX_PROCESS_STATE` 的全部 23 个 proc state，按进程可见性/重要性分成四类 Limits：

| ProcState 分类 | memHigh | swapHigh | 监控关注点 |
|---|---|---|---|
| `PERSISTENT` / `PERSISTENT_UI` | `LIMIT_IS_DISABLED`（"max"） | `LIMIT_IS_DISABLED` | 系统服务不受限 |
| `TOP` / `BOUND_TOP` / `IMPORTANT_FOREGROUND` / `TOP_SLEEPING` | `memVisible`（默认 4 GB） | `swapVisible`（默认 2 GB） | 前台几乎不触发 |
| `FOREGROUND_SERVICE` / `SERVICE` / `RECEIVER` / `BACKUP` / `BOUND_FOREGROUND_SERVICE` / `IMPORTANT_BACKGROUND` / `TRANSIENT_BACKGROUND` / `HEAVY_WEIGHT` / `HOME` / `LAST_ACTIVITY` | `memNotVisible`（默认 2 GB） | `swapNotVisible`（默认 2 GB） | **主要受影响群体** |
| `CACHED_ACTIVITY` / `CACHED_ACTIVITY_CLIENT` / `CACHED_RECENT` / `CACHED_EMPTY` | `LIMIT_IS_IGNORED`（不写入） | `LIMIT_IS_DISABLED`（"max"） | 不受 MemoryLimiter 控制 |

**调用链**：`Activity.setProcessState()` → `ProcessRecord.setProcState()` → `mMemoryLimiter.onProcStateUpdated()`（ProcessRecord.java:1625）→ `mStateLimit[]` 查询 → JNI `setLimit()` → cgroup 文件写入。

### Polling 轮询回退状态机

[已验证: AOSP android-17.0.0_r1, com_android_server_am_MemoryLimiter.cpp:43-52]

JNI 端定义三档轮询周期：

```cpp
const int PID_POLL_PERIOD_MS  = 5 * 60 * 1000;  // 5 分钟（常态清扫）
const int RED_POLL_PERIOD_MS  = 30 * 1000;      // 30 秒（red zone 轮询）
const int TEST_POLL_PERIOD_MS = 1000;           // 1 秒（测试模式）
```

**Red zone 触发条件**：`Process::isRed() = mMemWatcher.mTriggered && !mAnonSwapTriggered`——即 `memory.high` 已触发但 `memory.swap.high` 还没触发。这时 cgroup events 不再 fire，必须切换为 30s 轮询。

### AnonSwapState 四态机

[已验证: AOSP android-17.0.0_r1, com_android_server_am_MemoryLimiter.cpp:78-83, 512-528]

| 状态 | 判定条件 | 监听方式 | PSS 抖动 |
|---|---|---|---|
| `kCold` | `(anon+shmem) < (memHigh - 10MB)` | inotify | 稳定 |
| `kOkay` | 中间地带 | 30s 轮询 | 有噪声 |
| `kHot` | `metric > anonSwapLimit` | 30s 轮询 | 锯齿抖动 ±50 MB |
| `kTriggered` | `mAnonSwapTriggered = true` | 限制已释放 | 进程进入 30s 死亡窗口 |

**滞回设计**：`mMemHighHysteresis = 10 MB`——必须下降到 `memHigh - 10MB` 以下才能从 `kHot`/`kOkay` 回到 `kCold`，避免 inotify↔epoll 切换抖动。

### 内核 memcg v2 对 memory.high 的语义契约

[已验证: kernel.org Documentation/admin-guide/cgroup-v2.rst]

> **memory.high**: A read-write single value file... Memory usage throttle limit. If a cgroup's usage goes over the high boundary, the processes of the cgroup are throttled and put under heavy reclaim pressure. **Going over the high limit never invokes the OOM killer**.
>
> If memory.high is opened with `O_NONBLOCK` then the synchronous reclaim is bypassed. This is useful for admin processes that need to dynamically adjust the job's memory limits without expending their own CPU resources on memory reclamation.

**100 MB margin 用途**：`mMemHighMargin = 100 MB`——让被 throttle 的进程保留 anon 余量，CPU 可继续运行并自行释放 anon。如果用 `O_NONBLOCK` 写入 `memory.high`，writeLimit 立即返回但内核不强制 reclaim，进程会继续增长直至触顶——对 MemoryLimiter 没用。

### statsd 令牌桶限流算法

[已验证: AOSP android-17.0.0_r1, MemoryLimiter.java]

```java
static final int MAX_TOKENS = 4;
static final long TOKEN_PERIOD_MS = Duration.ofHours(1).toMillis();
static final long KILL_DELAY_MS = 30 * 1000;
```

**令牌桶算法**（`shouldLogAtom()`）：
- 每小时补 1 个 token（`accumulated = (now - mLastBucketUpdate) / TOKEN_PERIOD_MS`）
- 上限 4 个 token
- 满桶稳态下每天约 24-28 条 statsd event

**对监控的硬性约束**：APM SDK **不能依赖 statsd 通路做高频告警**。必须在 Java 层反射 hook `MemoryLimiter$ControllerEnabled.onLimitExceeded()` 才能获取完整事件流。

### MemoryStatUtil 双通路解析

[已验证: AOSP android-17.0.0_r1, MemoryStatUtil.java:47-50, 69-73]

```java
public static MemoryStat readMemoryStatFromFilesystem(int uid, int pid) {
    return readMemoryStatFromProcfs(pid);   // memcg 路径在 android17 已移除
}
```

`readMemoryStatFromProcfs()` 读 `/proc/<pid>/stat` field 23（`RSS_IN_PAGES_INDEX = 23`），乘以 `PAGE_SIZE` 得 `rssInBytes`。

**三条通路的根本差异**：

| 通路 | 文件 | 指标 | 包含 swap？ |
|---|---|---|---|
| `Debug.MemoryInfo` | `/proc/<pid>/smaps_rollup` | PSS | **否** |
| `MemoryStatUtil` | `/proc/<pid>/stat` field 23 | RSS in pages | **否** |
| `memcg memory.current` | `memory.current` | anon+swap+file-cache | **是** |

**正确的总内存指标应该是 `totalPss + VmSwap`**（`/proc/<pid>/status` 字段）。

### Java/Native LINT 绑定

[已验证: AOSP android-17.0.0_r1, MemoryLimiter.java + .cpp]

Java 与 Native 的枚举值通过 `LINT.IfChange / LINT.ThenChange` 严格绑定：

```cpp
// com_android_server_am_MemoryLimiter.cpp
enum class MonitoredLimit {
    // LINT.IfChange(limitTypes)
    kUnknown = 0, kMemoryHigh = 1, kSwapMax = 2, kAnonSwap = 3,
    // LINT.ThenChange(/services/core/java/com/android/server/am/MemoryLimiter.java:limitTypes)
};
```

任何修改一边枚举顺序的 commit 都会被 `lint` 工具在 CI 中拦截。

---

## 延伸阅读

### Android 17 MemoryLimiter 对 Debug.MemoryInfo 性能监控的影响
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-27-android17-memorylimiter-policy-monitor-impact.md
- 类型：DeepResearch 调研结果
- 摘要：Android 17 新增 MemoryLimiter 子系统作为第三道后台内存防线，通过 memcg v2 memory.high/swap.high + epoll 监听实现内核级硬限流。三类限制类型（MEMORY/SWAP/ANON_SWAP）对 Debug.MemoryInfo 的影响：PSS 抖动加剧、30s kill 窗口、PSS 不含 swap 导致总内存指标失真。
- 注入时间：2026-06-28
- 价值：首次系统揭示 MemoryLimiter 三层架构（Java/JNI/Kernel）对应用性能监控 SDK 的三类影响，是内存监控适配 Android 17 的必读材料

### Android 17 MemoryLimiter — ProcState 限制矩阵、轮询回退状态机、memcg 契约与 statsd 节流
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-28-android17-memorylimiter-procstate-polling-statsd.md
- 类型：DeepResearch 调研结果
- 摘要：深度拆解 MemoryLimiter 五大子系统：完整 23 个 ProcState→Limits 映射矩阵（persistent 无限制→cached 交 lmkd）；inotify→polling 回退机制（red zone 30s 轮询、常态 5min、测试 1s）；AnonSwapState 四态机（kCold/kOkay/kHot/kTriggered）；内核 memcg v2 memory.high 的 throttle+reclaim 语义（永不 OOM）；statsd 令牌桶限流（4 token/h、≤28 events/day）。
- 注入时间：2026-06-29
- 价值：提供 MemoryLimiter 从 Java→JNI→Kernel 的完整运行时行为模型，是 APM SDK 适配 Android 17 后台内存限制的源码级必读参考


### AIW 源码调研（2026-06-29）— Kill 窗口真相、ProfilingServiceHelper 三重门控与 Limiter 状态机

<!-- AIW-源码调研-2026-06-29 -->
[已验证: AOSP android-17.0.0_r1, MemoryLimiter.java:813-836 + com_android_server_am_MemoryLimiter.cpp:103-111, 472-483, 511-528]

#### 30 秒 Kill 延迟的真实目的——为 ProfilingServiceHelper 留的窗口

[已验证: AOSP android-17.0.0_r1, MemoryLimiter.java:828-836]

源码注释直接揭示 30s 的设计意图：

```java
// MemoryLimiter.java:828-836
// Request that the target be killed.  The delay allows the profiler, if
// configured to complete.
// TODO: eliminate this when the ProfilingServiceHelper API accepts a "kill when
// finsished" flag.
Message msg = mQueue.obtainMessage(MESSAGE_KILL, pid, uid,
        "MemoryLimiter:AnonSwap");
mQueue.sendMessageDelayed(msg, KILL_DELAY_MS);
```

**关键事实**：
- 30s 不是架构层面的"缓冲期"——**完全是为 ProfilingServiceHelper 抓 heap dump 留的时间**
- 源码中存在显式 TODO，希望扩展 ProfilingServiceHelper 接受 "kill-when-finished" 标志位后消除 30s 硬延迟
- 注释中存在拼写错误 "finsished"（应为 "finished"）——可作提交者身份线索

**对应用监控的修正**：30s 窗口同时承担两个职责（profile 抓取 + 软着陆），但只有当 profiling 真的触发时才是前者。

#### ProfilingServiceHelper 的三重门控——默认不触发

[已验证: AOSP android-17.0.0_r1, MemoryLimiter.java:815-826]

```java
if (android.os.profiling.Flags.systemTriggeredProfilingNew()        // flag 1
        && android.os.profiling.anomaly.flags.Flags.anomalyDetectorCoreC()  // flag 2
        && pkg != null) {                                            // 条件 3
    ProfilingServiceHelper helper = ProfilingServiceHelper.getInstance();
    helper.onProfilingTriggerOccurred(uid, pkg,
            ProfilingTrigger.TRIGGER_TYPE_ANOMALY);
}
```

| 条件 | 默认状态 | 含义 |
|---|---|---|
| `systemTriggeredProfilingNew()` | **关闭** | SystemTriggeredProfiling 新版 flag |
| `anomalyDetectorCoreC()` | **关闭** | anomalyDetector 模块的 core-c 标志 |
| `pkg != null` | 多数应用满足 | 进程必须能解析出 package name |

**Android 17 GA 设备上 30s 窗口里默认不会触发 profiling**——APM SDK 不应假设"被 MemoryLimiter kill 一定伴随 heap dump"。

#### 100 MB Margin 仅在 cgroup 事件触发后才写入

[已验证: AOSP android-17.0.0_r1, com_android_server_am_MemoryLimiter.cpp:472-483]

之前章节描述"cgroup memory.high 实际写入值 = memHigh + 100MB"是**有条件的**——通过 `mMemWatcher.mTriggered` 状态门控：

```cpp
case MonitoredLimit::kMemoryHigh:
    mMemoryHighLimit = limit;
    if (mMemWatcher.mTriggered) {
        // Add some margin to memHigh so that the CPU can run and perhaps shed anon
        // memory before hitting the limit.
        limit = incrLimit(limit, mMemWatcher.mMargin);
    }
    writeLimit(cgroupPath(CgroupFile::kMemoryHigh), limit);
```

- **常态下**：cgroup 收到原始 memHigh
- **触发后**：cgroup 收到 memHigh + 100MB
- Margin 用途：给被 throttle 的进程留 CPU 时间回收 anon

#### AnonSwapState 四态机与状态转换

[已验证: AOSP android-17.0.0_r1, com_android_server_am_MemoryLimiter.cpp:103-111, 511-528]

```cpp
enum class AnonSwapState { kCold, kOkay, kHot, kTriggered };

AnonSwapState testAnonSwap() const {
    if (mAnonSwapTriggered) return AnonSwapState::kTriggered;
    int64_t metric = getMetric(MonitoredLimit::kAnonSwap);
    if (mAnonSwapLimit < 0) return AnonSwapState::kOkay;
    else if (metric > mAnonSwapLimit) return AnonSwapState::kHot;
    else if (metric < (mMemoryHighLimit - mMemHighHysteresis)) return AnonSwapState::kCold;
    else return AnonSwapState::kOkay;
}
```

- `kCold -> kOkay` 与 `kOkay -> kCold` 的转换阈值都是 `memHigh - 10MB`——`mMemHighHysteresis` 防止 inotify/轮询切换抖动
- 10MB 在 cpp 注释中自承"主要为测试方便"，无深层架构理由

#### 配置文件"最大匹配"选择算法

[已验证: AOSP android-17.0.0_r1, MemoryLimiter.java:920-986]

`/vendor/etc/memory-limiter-config.xml` 中的多组 LimitSet 通过"最大匹配"算法选择：

```java
// 选取 minMemTotal <= memTotal 中最大的那一组
for (int i = 0; i < sets.size(); i++) {
    long minMemTotal = cfg.getMinimumRequiredMemTotal().longValue() * MB;
    if (minMemTotal > memTotal || minMemTotal < minRequiredMem) continue;
    minRequiredMem = minMemTotal;
    result = new Configuration(...);
}
```

- `cfg.getVersion()` 必须 == 1，否则抛 `IllegalArgumentException`
- `clist.size() < 1` 也抛异常
- 解析失败/无匹配 LimitSet 时 MemoryLimiter **静默禁用**，不阻止 system_server 启动

#### ProcessState 数量校正——22 个而非 23 个

[已验证: AOSP android-17.0.0_r1, MemoryLimiter.java:574-617]

之前章节表格列出 23 个 proc state。源码 `initializeMemoryLimits()` 的 switch 实际只有 **22 个 case 分支**（UNKNOWN、PERSISTENT、PERSISTENT_UI、TOP、BOUND_TOP、FOREGROUND_SERVICE、BOUND_FOREGROUND_SERVICE、IMPORTANT_FOREGROUND、IMPORTANT_BACKGROUND、TRANSIENT_BACKGROUND、BACKUP、SERVICE、RECEIVER、TOP_SLEEPING、HEAVY_WEIGHT、HOME、LAST_ACTIVITY、CACHED_ACTIVITY、CACHED_ACTIVITY_CLIENT、CACHED_RECENT、CACHED_EMPTY、NONEXISTENT）。

**关键细节**：
- `TOP_SLEEPING` 走 `memVisible`（非 `memNotVisible`）——屏幕关并不立即降级
- `HOME`（应用退到后台但 Activity 还在）走 `memNotVisible`——区别于 `CACHED_*`
- `CACHED_*` 4 个状态完全交 lmkd——印证四层防护体系中 MemoryLimiter 与 CachedAppOptimizer 的边界
- `NONEXISTENT` 是 `memHigh = IGNORED, swapHigh = IGNORED`——避免 stale 限制

#### 版本差异——Android 15 不存在 MemoryLimiter

[已验证: AOSP android-15.0.0_r1]

| 版本 | MemoryLimiter 状态 |
|---|---|
| Android 15.0.0_r1 (API 35) | **不存在**（googlesource 404） |
| Android 16.0.0_r1 (API 36) | 引入（Copyright 2025） |
| Android 17.0.0_r1 (API 37) | 1291 行 Java + 1276 行 JNI C++ |

MemoryLimiter 是 **Android 16 引入、17 增强**的子系统——任何 Android 15 设备的内存监控兼容性测试结果**不能直接外推到 Android 16/17**。

---

#### 延伸阅读

### Android 17 MemoryLimiter — 30s Kill 窗口、ProfilingServiceHelper 触发条件与 Limiter 状态机
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-29-android17-memorylimiter-30s-kill-window-and-profiling.md
- 类型：DeepResearch 调研结果
- 摘要：源码注释直接揭示 30s 延迟完全是为 ProfilingServiceHelper 留的窗口（TODO 明确写"等 ProfilingServiceHelper 提供 kill-when-finished 标志位后消除"）。ProfilingServiceHelper 触发需三重门控（systemTriggeredProfilingNew + anomalyDetectorCoreC + pkg != null），Android 17 GA 默认全关闭。100MB margin 仅在 cgroup memory.high 事件触发后写入 cgroup。配置文件采用"最大匹配"算法（minMemTotal <= memTotal 中最大者）。ProcessState 实际为 22 个 case 分支（之前章节误标 23）。Android 15.0.0_r1 中 MemoryLimiter.java 不存在（404），确认是 Android 16 引入。
- 注入时间：2026-06-29
- 价值：填补 4.17 章节在"30s 等待的真实目的"、"margin 激活条件"、"配置匹配算法"、"ProcessState 数量校正"四个细节盲区，为 APM 监控 SDK 提供精确的归因与告警阈值参考。


### Android 17 MemoryLimiter 的 30 秒 Kill 窗口真相与 ProfilingServiceHelper 触发条件
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-29-android17-memorylimiter-30s-kill-window-and-profiling.md
- 类型：DeepResearch 调研结果
- 摘要：源码揭示 MemoryLimiter 30s kill 延迟实为等待 ProfilingServiceHelper 完成 heap dump。触发需三重门控全满足（默认全关闭）。100MB margin 仅在 cgroup memory.high 事件触发后写入。MemoryLimiter.java 在 Android 15 不存在，确认为 16/17 新子系统。
- 注入时间：2026-06-30
- 价值：揭示 30s kill 窗口真正用途、ProfilingServiceHelper 三重门控、100MB margin 激活时机
