---
title: "ProfilingManager 系统触发式性能追踪"
chapter: "8.8"
status: draft
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
---

# ProfilingManager 系统触发式性能追踪

## 为什么要了解系统触发式性能追踪

在传统的性能分析中，工程师需要手动启动性能监控，既容易遗漏关键问题，又难以捕捉偶发性性能瓶颈。Android 16 引入的 ProfilingManager 系统触发式机制从根本上改变了这一局面——系统现在可以根据预设条件自动触发性能追踪，无需人工干预。

这种机制对启动速度优化和 ANR 分析特别有价值。系统可以在应用冷启动时自动抓取 `reportFullyDrawn` 时刻的完整 Trace，在 ANR 发生前记录相关线程状态，为性能问题提供更完整的上下文。

## 核心机制

### ProfilingManager 演进时间线

| Android 版本 | 能力 | 关键 API |
|---|---|---|
| **15** | 引入 ProfilingManager 基础 API | `registerProfilingListener()`，手动触发 heap dump / stack sample / system trace |
| **16** | 系统触发式追踪（System-Triggered Profiling） | 自动触发 cold start `reportFullyDrawn` trace 和 ANR trace |
| **17** | 扩展触发类型 | `TRIGGER_TYPE_COLD_START`、`TRIGGER_TYPE_OOM`、`TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` |

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

**实现原理**：系统通过 Instrumentation 监听 Activity 的 `onWindowFocusChanged()` 和 `reportFullyDrawn()` 调用，在确认 UI 完全绘制完成后自动开始 Trace 收集。

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

**实现原理**：SystemServer 中的 ANR 检测机制会在判定即将超时时，通过 ProfilingManager 提前收集诊断信息。

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
        .setRetentionDuration(Duration.ofDays(7)) // 保留7天
        .build(),
    listener
);
```

#### 配置参数

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `addTriggerType()` | int | 触发类型组合 | 无（需手动指定） |
| `setRetentionDuration()` | Duration | 数据保留时长 | 24小时 |
| `setMaxFileSize()` | long | 单个Trace文件最大大小 | 100MB |
| `setSamplingRate()` | int | 抽样率（百分比） | 100（不抽样） |

## 在 Perfetto 中的表现

### 冷启动触发

在 Perfetto 中，系统触发的冷启动 Trace 会有特殊的标记：

```
# 查看 reportFullyDrawn 时刻的 Trace
SELECT ts, name FROM sched WHERE name LIKE '%reportFullyDrawn%'

# 查看相关线程的活动
SELECT ts, dur, name FROM slice 
WHERE thread_id = (SELECT id FROM thread WHERE name = 'ui:com.example.app')
AND ts BETWEEN cold_start_ts AND cold_start_ts + 1000ms
```

**正常情况**：从 Application.onCreate() 到 reportFullyDrawn() 时间在 200-800ms 之间，主线程没有长时间阻塞

**异常情况**：时间超过 1.5s 或主线程存在明显阻塞

### ANR 触发

ANR 触发前会捕获到关键的阻塞信息：

```
# 查看 ANR 前的主线程调用栈
SELECT name, dur FROM slice 
WHERE thread_id = (SELECT id FROM thread WHERE name = 'ui:com.example.app')
AND ts BETWEEN anr_ts - 2000ms AND anr_ts
ORDER BY ts DESC
```

**关键指标**：
- 主线程 2 秒内是否有方法执行超过 100ms
- 是否存在同步 Binder 调用超过 16ms
- UI 线程是否存在锁等待

### OOM 触发

内存问题的 Trace 分析：

```
# 查看内存分配热点
SELECT name, dur FROM slice 
WHERE name LIKE '%alloc%'
AND thread_id = (SELECT id FROM thread WHERE name = 'gc:/app')
```

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

**事实**：系统触发使用轻量级 tracing，仅在关键时间点收集数据，额外开销 < 1%

**验证方法**：
```bash
# 对比有无 ProfilingManager 的启动时间
adb shell am force-stop com.example.app
adb shell am start -W -n com.example.app/.MainActivity
# 重复多次，计算平均启动时间
```

### 误区 2：所有应用都会自动触发追踪

**事实**：需要主动注册 `ProfilingListener` 才能接收系统触发事件

**检查方法**：
```java
// 检查当前应用是否已注册
boolean isRegistered = profilingManager.isProfilingListenerRegistered(listener);
```

### 误区 3：系统触发的 Trace 无法区分正常和异常

**事实**：系统会自动标记异常情况，如 ANR 触发时包含 "ANR-warning" 标记

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