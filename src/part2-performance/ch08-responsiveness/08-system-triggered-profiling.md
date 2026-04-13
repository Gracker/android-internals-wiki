---
title: "ProfilingManager 系统触发式性能追踪"
chapter: "8.8"
section: "8.8"
status: ready-for-review
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
tags: [profiling-manager, system-triggered, cold-start, anr, tracing, performance-monitoring]
related_chapters: ["8.2", "9.3", "13.7"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-10"
gap_source: "研究素材"
confidence: medium
sources:
  - type: blog
    path: "Android 16/17 ProfilingManager 系统触发式性能追踪"
    title: "系统触发式性能追踪机制"
    date: "2026-04-01"
  - type: official
    path: "developer.android.com/reference/android/os/ProfilingManager"
    title: "ProfilingManager API Reference"
    date: "2026"
pipeline_stage: task2b_pending
task6_state: reviewed
task9_state: pending
task2b_state: pending
reviewed_by: "openclaw-task6"
reviewed_date: "2026-04-13"
task6_result: "needs-rework"
---

# ProfilingManager 系统触发式性能追踪

## 为什么要了解系统触发式性能追踪

传统性能分析往往要靠工程师手动启动监控，容易错过偶发问题，也很难在问题发生当下保留完整上下文。ProfilingManager 把一部分追踪时机交给系统条件触发，工程师不用每次都手动起 Trace。

对启动速度优化和 ANR 分析来说，这类能力的价值在于，它试图把 `reportFullyDrawn()` 前后的启动路径、ANR 附近的线程状态放进同一份诊断材料里。下面涉及的触发类型、阈值和回调细节，仍要结合官方文档或 AOSP 再核一次。

<!-- outline-start -->
## 要点

### 🔹 ProfilingManager 的定位与版本演进
- Android 15 先提供 ProfilingManager 基础能力，Android 16 / 17 再扩展系统条件触发
- 这一节的重点不是 API 清单，而是哪些场景值得交给系统自动抓取

### 🔹 系统触发类型与采集内容
- 先按冷启动、ANR、OOM、过度 CPU 使用四类触发理解
- 每类都要区分“触发时机”“期望拿到什么材料”“哪些字段仍待核对”

### 🔹 注册监听与参数边界
- 关注监听器注册方式、配置项和结果交付方式
- API 名称、Builder 参数和默认值要回到当前 SDK 再核对

### 🔹 在 Perfetto 中如何落地使用
- 重点看系统触发 Trace 能否和冷启动、主线程阻塞、内存异常对应起来
- SQL 片段只作为排查思路，表名、字段和时间窗口要按当前 schema 调整

### 🔹 与手动抓取和生命周期埋点的关系
- ProfilingManager 不是替代手动 Perfetto，而是补足偶发问题的自动抓取
- 需要和 `ActivityLifecycleCallbacks`、现有监控链路配合使用

### 🔹 版本差异、误区与验证边界
- 版本演进要区分 API 能力、权限模型、触发类型和开销变化
- 量化阈值、默认值、性能开销都不该直接当成结论，必须标注来源

## 扩展

### 🔸 适合交给 Task 9 继续核对的点
- 触发类型常量、阈值、回调签名、AOSP 路径
- Perfetto SQL 与 trace schema 的版本差异

### 🔸 适合交给 Task 2B 回炉的点
- 补真实 Trace 截图或 `[图：...]` 占位
- 把版本演进和误区部分改成“证据 → 判断”的写法

<!-- outline-end -->

## 核心机制

### ProfilingManager 演进时间线

| Android 版本 | 能力 | 关键 API |
|---|---|---|
| **15** | 引入 ProfilingManager 基础 API | `registerProfilingListener()`，手动触发 heap dump / stack sample / system trace |
| **16** | 系统触发式追踪（System-Triggered Profiling） | 自动触发 cold start `reportFullyDrawn` trace 和 ANR trace |
| **17** | 扩展触发类型 | `TRIGGER_TYPE_COLD_START`、`TRIGGER_TYPE_OOM`、`TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` |

> [待验证] 上表里的触发类型和版本边界需要按当前 SDK / 官方文档再核对，尤其是 Android 16 / 17 的新增能力。

### 系统触发条件详解

系统会根据以下条件自动触发性能追踪：

#### 1. 冷启动触发 (`TRIGGER_TYPE_COLD_START`)

```java
// Android 17 中的冷启动自动触发
public static final int TRIGGER_TYPE_COLD_START = 1;
```

**触发时机**：当应用完成冷启动且调用 `Activity.reportFullyDrawn()` 时

**捕获内容**：
- 从 Application.onCreate() 到 Activity.reportFullyDrawn() 的完整时间线
- 主线程关键方法调用（Binder IPC、View 生命周期、布局测量绘制）
- CPU 使用率和线程调度情况
- 内存分配和 GC 活动

**实现原理**：这里先按“围绕 `reportFullyDrawn()` 收集启动诊断材料”的思路理解，具体由哪个系统组件负责触发和落盘，还需要回到 AOSP 核对。

> [待验证] 冷启动触发链路、开始采集时机，以及与 `reportFullyDrawn()` 的精确关系。

#### 2. ANR 触发 (`TRIGGER_TYPE_ANR`)

```java
// ANR 发生前的预警触发
public static final int TRIGGER_TYPE_ANR = 2;
```

**触发时机**：当系统检测到主线程即将超时前（通常是 ANR 报告生成前 500ms）

**捕获内容**：
- 主线程阻塞前 2 秒的函数调用栈
- 相关线程的锁状态和等待时间
- Binder 通信队列情况
- CPU 负载分布

**实现原理**：这一段先按“ANR 临近时补采诊断材料”的方式理解，具体阈值、回调时机和数据窗口需要再核对。

> [待验证] “ANR 前 500ms”“阻塞前 2 秒”等时间窗口的来源，以及触发链路对应的系统服务实现。

#### 3. OOM 触发 (`TRIGGER_TYPE_OOM`)

```java
// 内存不足时的触发
public static final int TRIGGER_TYPE_OOM = 3;
```

**触发时机**：当 Low Memory Killer 即将杀死进程时

**捕获内容**：
- 进程内存使用历史趋势
- 大对象分配情况
- 内存回收活动
- 相关内存页分配状态

> [待验证] OOM 触发条件、采集窗口和产出字段需要补官方来源。

#### 4. 过度 CPU 使用触发 (`TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE`)

```java
// 过度 CPU 使用警告
public static final int TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE = 4;
```

**触发时机**：进程 CPU 使用率超过阈值（通常为 90%）且持续时间超过 5 分钟

**捕获内容**：
- CPU 时间分布（用户空间/内核空间）
- 热点函数调用
- 线程 CPU 使用情况
- 频繁的 JNI 调用

> [待验证] CPU 阈值、持续时长和触发类型常量需要按 SDK 文档或系统源码核对。

### 注册与配置

#### 注册监听器

```java
ProfilingManager profilingManager = getSystemService(ProfilingManager.class);

ProfilingListener listener = new ProfilingListener() {
    @Override
    public void onProfilingTriggered(int triggerType, Bundle profilingData) {
        // 处理系统自动触发的性能数据
        Log.d("Profiling", "Triggered by: " + triggerType);
        // 获取性能数据文件路径
        String tracePath = profilingData.getString("trace_path");
        // 上传到分析服务器或保存到本地
    }
};

// 注册系统触发监听
profilingManager.registerProfilingListener(
    new ProfilingConfig.Builder()
        .addTriggerType(Profiling.TRIGGER_TYPE_COLD_START)
        .addTriggerType(Profiling.TRIGGER_TYPE_ANR)
        .addTriggerType(Profiling.TRIGGER_TYPE_OOM)
        .addTriggerType(Profiling.TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE)
        .setRetentionDuration(Duration.ofDays(7)) // 保留 7 天
        .build(),
    listener
);
```

> [待验证] 代码里的 listener 类型、注册 API、Builder 方法名和结果字段键值，需要按当前 SDK 校对。

#### 配置参数

> [待验证] 下表的参数名与默认值需要按当前 SDK 核对。

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `addTriggerType()` | int | 触发类型组合 | 无（需手动指定） |
| `setRetentionDuration()` | Duration | 数据保留时长 | 24 小时 |
| `setMaxFileSize()` | long | 单个 Trace 文件最大大小 | 100 MB |
| `setSamplingRate()` | int | 抽样率（百分比） | 100（不抽样） |

## 在 Perfetto 中的表现

### 冷启动触发

在 Perfetto 中，这类 Trace 更适合当成“对齐启动阶段和主线程活动”的诊断材料，而不是直接套一套固定查询。

> [待验证] 下列 SQL 片段主要展示排查思路，不保证能直接在当前 Perfetto schema 中运行。

```sql
-- 查看 `reportFullyDrawn()` 附近的 Trace 片段
SELECT ts, name
FROM sched
WHERE name LIKE '%reportFullyDrawn%';

-- 继续围绕目标时间窗口查看相关线程活动
SELECT ts, dur, name
FROM slice
WHERE thread_id = (SELECT id FROM thread WHERE name = 'ui:com.example.app')
  AND ts BETWEEN cold_start_ts AND cold_start_ts + 1000ms;
```

[图：系统触发冷启动 Trace，标出 `Application.onCreate()` 到 `reportFullyDrawn()` 的时间段，以及主线程长任务位置]

> [待验证] 这里的 `200-800 ms` 和 `1.5 s` 只是待核对的经验阈值，不同设备和业务场景差异会很大。

**正常情况**：从 `Application.onCreate()` 到 `reportFullyDrawn()` 的时间在 `200-800 ms` 之间，主线程没有长时间阻塞。

**异常情况**：时间超过 `1.5 s`，或主线程存在明显阻塞。

### ANR 触发

ANR 相关 Trace 的价值在于，把主线程阻塞区间、锁等待和 Binder 活动尽量放到同一个时间窗口里看。

```sql
-- 伪变量 `anr_ts` 需要先由具体 Trace 定位
SELECT name, dur
FROM slice
WHERE thread_id = (SELECT id FROM thread WHERE name = 'ui:com.example.app')
  AND ts BETWEEN anr_ts - 2000ms AND anr_ts
ORDER BY ts DESC;
```

[图：ANR 前 2 秒主线程、Binder 线程和锁等待的对照 Trace]

**关键指标**：
- 主线程 2 秒内是否有方法执行超过 `100 ms`
- 是否存在同步 Binder 调用超过 `16 ms`
- UI 线程是否存在锁等待

> [待验证] `100 ms` / `16 ms` 的阈值需要结合设备刷新率、场景类型和采样口径一起看。

### OOM 触发

内存问题更适合把分配热点、GC 活动和进程内存计数器放在一起看。

```sql
SELECT name, dur
FROM slice
WHERE name LIKE '%alloc%'
  AND thread_id = (SELECT id FROM thread WHERE name = 'gc:/app');
```

[图：内存逼近阈值时的内存计数器、GC 活动和分配热点]

## 与其他机制的关系

### 与 Perfetto 手动抓取的关系

**互补性**：
- 手动抓取：用于特定场景的深度分析
- 系统触发：用于异常情况的全量监控

**数据对比**：
```
# 手动抓取的 Cold Start Trace vs 系统自动捕获
SELECT 
    'manual' as capture_type,
    avg(duration) as avg_duration
FROM manual_cold_traces

UNION ALL

SELECT 
    'auto' as capture_type,
    avg(duration) as avg_duration  
FROM auto_cold_traces
```

### 与 ActivityLifecycleCallbacks 的关系

**协同工作**：
```java
// 在应用中使用监听器捕获关键节点
public class App extends Application implements Application.ActivityLifecycleCallbacks {
    
    @Override
    public void onActivityResumed(Activity activity) {
        // 记录 Activity 恢复时间点
        long resumeTime = System.currentTimeMillis();
        Log.d("Perfetto", "Activity resumed at: " + resumeTime);
    }
    
    // ... 其他生命周期方法
}
```

## 版本演进

> [待验证] 这一节里的权限模型、开销变化和回调能力需要回到 release note / API reference 逐条核对。

### Android 15 (API 35)

- **基础功能**：引入 ProfilingManager，仅支持手动触发
- **关键 API**：`registerProfilingListener()` 基础版本
- **限制**：需要 root 权限，仅用于系统应用

### Android 16 (API 36) 
- **重大改进**：引入系统触发式机制
- **新触发类型**：`TRIGGER_TYPE_COLD_START`
- **权限简化**：普通应用可申请使用，无需 root
- **数据格式**：标准化 Trace 格式，便于分析

### Android 17 (API 37)
- **扩展触发**：新增 OOM 和过度 CPU 使用触发
- **性能优化**：降低 30% 的性能开销
- **数据增强**：添加 CPU 使用率历史记录
- **API 增强**：支持异步回调和批量处理

## 常见问题与误区

### 误区 1：系统触发会严重影响应用性能

**事实**：系统触发使用轻量级 tracing，仅在关键时间点收集数据，额外开销 < 1%。[待验证：量化来源]

**验证方法**：
```bash
# 对比有无 ProfilingManager 的启动时间
adb shell am force-stop com.example.app
adb shell am start -W -n com.example.app/.MainActivity
# 重复多次，计算平均启动时间
```

### 误区 2：所有应用都会自动触发追踪

**事实**：需要主动注册 `ProfilingListener` 才能接收系统触发事件。[待验证：API 与注册条件]

**检查方法**：
```java
// 检查当前应用是否已注册
boolean isRegistered = profilingManager.isProfilingListenerRegistered(listener);
```

### 误区 3：系统触发的 Trace 无法区分正常和异常

**事实**：系统会自动标记异常情况，如 ANR 触发时包含 "ANR-warning" 标记。[待验证：标记来源与字段]

**分析技巧**：
```sql
-- 查看标记的异常 Trace
SELECT ts, name, flags FROM slice 
WHERE flags & 0x1000000 != 0  -- ANR 标记
ORDER BY ts DESC;
```

## 参考资料

- **官方文档**：[ProfilingManager API Reference](https://developer.android.com/reference/android/os/ProfilingManager)
- **AOSP 源码**：`frameworks/base/core/java/android/os/ProfilingManager.java`
- **系统服务实现**：`frameworks/base/services/core/java/com/android/server/am/ProfilingManagerService.java`
- **Android 16 公布**：[Android 16 Performance Features](https://android-developers.googleblog.com/2025/06/android-16-performance-enhancements.html)
- **性能最佳实践**：[Android Performance Tuning Guide](https://developer.android.com/topic/performance)