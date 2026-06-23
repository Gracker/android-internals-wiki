---
title: "第 14 章：其他分析工具"
chapter: "14"
status: "draft"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [android, performance]
---

# 第 14 章：其他分析工具

> **注**：本章聚焦 Android 性能分析中非 Peretto 的工具生态。这些工具要么是官方提供的基础工具，要么是开源社区的优秀实现，在实际性能调优和问题排查中发挥着重要作用。

## 本章概述

Android 性能分析工具生态丰富，除了 Perfetto 这类专业级追踪工具外，还有许多针对性强的实用工具。本章将详细介绍这些工具的使用场景、适用问题和分析方法。

### 工具分类体系

| 工具类型 | 特点 | 适用场景 | 典型工具 |
|---------|------|---------|---------|
| **官方工具** | 系统内置，无需额外安装 | 系统级问题排查，快速诊断 | `adb`、`dumpsys`、`am` |
| **IDE 集成** | 与开发环境深度集成 | 开发阶段性能监控 | Android Studio Profiler |
| **三方开源** | 功能专一，性能出色 | 特定领域深度分析 | Simpleperf、LeakCanary |
| **商业平台** | 云端分析，团队协作 | 线上监控，团队共建 | Firebase Performance、Sentry |
| **自动化框架** | 持续集成，批量测试 | 持续性能验证 | Simpleperf + Python 脚本 |

## 14.1 Android Studio Profiler

Android Studio 提供了集成的性能分析工具，是开发阶段最主要的性能监控手段。

### 核心功能模块

#### CPU Profiler
- **采样模式**：基于 `simpleperf` 的 CPU 采样，记录线程调用栈
- **跟踪模式**：基于 `atrace` 的方法级跟踪，精确记录每个方法调用
- **使用场景**：主线程卡顿排查、方法耗时分析、热点函数定位

```java
// 使用 Traceview API 记录方法级跟踪
Trace.beginSection("expensiveOperation");
// 你的代码
Trace.endSection();
```

#### Memory Profiler
- **堆栈分析**：实时显示 Java 堆内存分配
- **Heap Dump**：生成 `.hprof` 文件进行内存泄漏分析
- **Allocation Tracker**：记录对象分配位置和频率
- **使用场景**：内存泄漏定位、内存抖动分析、OOM 预警

#### Network Profiler
- **流量统计**：HTTP/HTTPS 网络请求分析
- **慢请求识别**：自动标记超时请求
- **性能分析**：请求耗时、响应大小、缓存命中率
- **使用场景**：网络性能优化、API 调用质量监控

#### Energy Profiler
- **功耗监控**：CPU、网络、传感器等模块的耗电情况
- **使用场景**：移动端功耗优化、电池续航分析

### 使用技巧

#### 快速入口
```bash
# 直接启动 Profiler 分析
adb shell am profile start com.example.app /data/local/tmp/profile.trace
```

#### 数据导出与分析
```bash
# 导出 CPU 跟踪数据
adb pull /data/local/tmp/profile.trace ./analysis/
```

#### 常见问题排查

**CPU 分析不准确**：
- 采样模式下采样率设置过低
- 跟踪模式下方法调用过于频繁导致性能开销

**内存分析卡顿**：
- Heap Dump 会导致应用暂停 2-5 秒
- 应在测试环境进行，避免在生产环境操作

## 14.2 Simpleperf - 系统级性能分析工具

Simpleperf 是 AOSP 官方提供的性能分析工具，比 `perf` 更适合 Android 环境。

### 核心功能

#### 基础监控
```bash
# 启动监控
adb shell simpleperf record -g -o /data/local/tmp/perf.data

# 后台持续监控
adb shell simpleperf record -p <pid> -f 99 -g -o /data/local/tmp/perf.data

# 监控指定进程
adb shell simpleperf record -p $(pidof com.example.app) -g --sample-rate 1000 -o perf.data
```

#### 详细分析
```bash
# 导出数据到主机
adb pull /data/local/tmp/perf.data

# 生成火焰图
simpleperf report --show-samples -g br_stack --sort comm,dso

# 生成文本报告
simpleperf report --sort comm,dso > report.txt
```

### 使用场景

#### Native 代码性能分析
```bash
# 分析 C++ 代码热点
adb shell simpleperf record -p <app_pid> -g --event cycles,instructions -o perf.data

# 分析指定 so 文件
adb shell simpleperf record -p <app_pid> --export-symbol-file /path/to/your.so -g -o perf.data
```

#### 系统级问题分析
```bash
# 监控系统调用
adb shell simpleperf record -a -e sched:sched_switch,syscalls:sys_enter -o perf.data

# 分析 I/O 瓶颈
adb shell simpleperf record -a -e block:block_io_done -o perf.data
```

### 高级技巧

#### 自定义事件
```bash
# 自定义性能事件
adb shell simpleperf record -e cache-misses,cache-references -p <pid> -o perf.data
```

#### 脚本化分析
```python
#!/usr/bin/env python3
import subprocess
import re

# 获取应用进程
pid = subprocess.check_output(['pidof', 'com.example.app']).decode().strip()

# 启动监控
subprocess.run(['adb', 'shell', 'simpleperf', 'record', '-p', pid, '-g', '-o', '/data/local/tmp/perf.data'])

# 分析热点函数
result = subprocess.run(['simpleperf', 'report', '--show-samples', '-g', 'br_stack', '--sort', 'comm,dso'])
print(result.stdout)
```

## 14.3 内存分析工具集

### LeakCanary
专为内存泄漏设计的自动化工具，支持 Java 和 Native 层面泄漏检测。

#### 使用方法
```java
// 在 Application 中初始化
LeakCanary.installed(new AppWatcher(this));

// 监测 Activity/Fragment
class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Activity 销毁时自动检测泄漏
    }
}
```

#### 原理分析
LeakCanary 通过 `AndroidHeapDump` 在对象销毁后等待 GC，如果对象仍可达则触发 heap dump。核心机制：
1. `ActivityFragmentLifecycleCallbacks` 监听销毁事件
2. `HeapDumpTrigger` 触发 heap dump
3. `HeapAnalyzer` 分析 heap dump 查找泄漏路径

### MAT (Memory Analyzer Tool)
Eclipse 提供的强大内存分析工具，适合分析大型 heap dump 文件。

#### 关键功能
- **Leak Suspects**：自动识别可能的泄漏源头
- **Dominator Tree**：支配树分析，找出大对象根源
- **Path to GC Roots**：找到对象无法被 GC 的原因
- **Histogram**：对象类型分布统计

#### 使用场景
```bash
# 导出 heap dump
adb shell am dumpheap <pkg> /sdcard/heapdump.hprof

# 分析 heap dump
./MemoryAnalyzer.app/Contents/Eclipse/MAT.app/Contents/MacOS/mem-scan heapdump.hprof
```

## 14.4 dumpsys 系列命令

`dumpsys` 是 Android 系统最强大的命令行诊断工具，包含数十个系统服务的状态快照。

### 核心命令分类

#### 系统状态查询
```bash
# 所有系统服务概览
adb shell dumpsys

# 内存使用情况
adb shell dumpsys meminfo

# 当前 Activity 栈
adb shell dumpsys activity top

# 窗口状态
adb shell dumpsys window windows

# 电源管理
adb shell dumpsys power
```

#### 性能相关服务
```bash
# 耗电统计（重置）
adb shell dumpsys batterystats --reset

# ANR 信息
adb shell dumpsys activity processes | grep "ANR"

# 唤醒锁状态
adb shell dumpsys power | grep "WakeLock"

# 内存使用排名
adb shell dumpsys meminfo | sort -k6 -nr
```

#### 深度分析命令
```bash
# 详细内存分析
adb shell dumpsys meminfo com.example.app

# GPU 内存统计
adb shell dumpsys gfxinfo com.example.app

# SurfaceFlinger 状态
adb shell dumpsys SurfaceFlinger

# 网络状态
adb shell dumpsys connectivity
```

### 高级用法

#### 脚本化分析
```bash
#!/bin/bash
# 获取内存使用趋势
adb shell dumpsys meminfo com.example.app | grep "Pss" >> memory_trend.log

# 获取 CPU 使用情况
adb shell dumpsys cpuinfo | grep com.example.app >> cpu_usage.log

# 监控 ANR 发生率
adb logcat -d | grep -c "ANR in" >> anr_count.log
```

#### 定时监控
```bash
# 每5秒收集一次内存使用
while true; do
    adb shell dumpsys meminfo com.example.app | grep "Pss" | awk '{print $2}' >> mem_monitor.log
    sleep 5
done
```

## 14.5 三方性能库

### Matrix (腾讯)
腾讯开源的性能监控平台，提供多维度的性能数据收集。

#### 功能特性
- **卡顿监控**：主线程卡顿检测，自动记录调用栈
- **内存监控**：内存泄漏自动发现，OOM 预警
- **网络监控**：慢请求识别，API 质量监控
- **启动监控**：冷启动、热启动耗时分析

#### 集成方法
```java
// 在 Application 中初始化
Matrix.with(application).link(new MatrixBuilder());

// 启用卡顿监控
MatrixLogConfig config = new MatrixLogConfig.Builder()
    .mainBlockThreshold(200)
    .build();
MatrixLogBuilder.newBuilder().setLogConfig(config).build();
```

### KOOM (快手)
快手开源的内存优化工具，专注于内存泄漏和内存抖动检测。

#### 核心功能
- **内存泄漏检测**：基于 GcRoot 分析的泄漏检测
- **内存抖动监控**：高频对象分配监控
- **OOM 预警**：内存压力实时监控
- **自动优化**：智能化的内存优化建议

#### 使用场景
```java
// 初始化 KOOM
OOMWatcher.init(context, new OOMConfig.Builder()
    .enableLeakCanary(true)
    .enableHeapCanary(false)
    .setHeapThreshold(0.8f)
    .build());

// 监控内存使用
OOMWatcher.get().addHeapInfoObserver(heapInfo -> {
    Log.d("KOOM", "Current heap usage: " + heapInfo.getUsedHeapSize());
});
```

## 14.6 自动化测试工具

### eBPF/BPF 在 Android 性能分析中的应用

eBPF (Extended Berkeley Packet Filter) 是 Linux 内核的强大 tracing 技术，Android 12+ 开始逐步支持。

#### 基本原理
- 在内核层面运行安全的程序
- 无需修改内核代码即可实现系统级 tracing
- 性能开销极低，适合长期监控

#### 使用场景
```bash
# 监控 Binder 调用
sudo apt install bpfcc-tools
bpftool prog list | grep binder

# 追踪系统调用
trace-cmd record -e syscalls:sys_enter -e syscalls:sys_exit

# 监控进程调度
trace-cmd record -e sched:sched_switch
```

#### Android 集成
```java
// 使用 Perfetto + eBPF
PerfettoTracingConfig config = new PerfettoTracingConfig.Builder()
    .addDataSource(PerfettoTracingConfig.DataSource.BINDER)
    .addDataSource(PerfettoTracingConfig.DataSource.SCHED)
    .build();
```

### Winscope - 窗口与合成调试工具

Winscope 是 Android 官方提供的窗口状态可视化工具，特别适合渲染问题排查。

#### 主要功能
- **窗口层级可视化**：展示窗口的 Z-Order 和层级关系
- **Surface 状态监控**：Surface 的创建、销毁和状态变化
- **渲染帧分析**：帧率、掉帧、渲染时间统计
- **合成过程监控**：SurfaceFlinger 合成过程追踪

#### 使用方法
```bash
# 启动 Winscope
adb shell winscope

# 导出窗口信息
adb shell dumpsys activity windows | winscope
```

## 14.7 ProfilingManager - 系统触发式性能追踪

Android 11+ 引入的系统级性能管理服务，支持系统触发式性能追踪。

### 核心功能
- **系统事件追踪**：boot、app launch、activity transition 等
- **资源使用监控**：CPU、内存、网络、电池使用
- **性能基准收集**：建立性能基线，检测异常

#### 使用方法
```java
// 注册性能监控
ProfilingManager profilingManager = getSystemService(ProfilingManager.class);

// 监控应用启动
profilingManager.addRequest(new ProfilingRequest.Builder()
    .setProfilingType(ProfilingManager.PROFILING_TYPE_APP_STARTUP)
    .setTimeoutMillis(10000)
    .build());

// 获取性能数据
List<ProfilingResult> results = profilingManager.getResults();
```

#### 系统触发示例
```java
// 监控 ANR 事件
profilingManager.addRequest(new ProfilingRequest.Builder()
    .setProfilingType(ProfilingManager.PROFILING_TYPE_ANR)
    .setAdditionalInfo("MainActivity")
    .build());

// 监控低内存事件
profilingManager.addRequest(new ProfilingRequest.Builder()
    .setProfilingType(ProfilingManager.PROFILING_TYPE_LOW_MEMORY)
    .build());
```

## 14.8 GPU 图形调试与分析工具

### GPU Inspector (Layout Inspector)
Android Studio 提供的 GPU 渲染分析工具。

#### 功能特性
- **布局层级分析**：View 的层级关系和布局耗时
- **渲染性能分析**：绘制操作的性能分析
- **过度绘制检测**：检测像素过度绘制问题
- **GPU 内存分析**：显存使用情况监控

#### 使用方法
```java
// 启用 GPU 调试
if (BuildConfig.DEBUG) {
    Debug.enableGPUContentViewInflation();
}

// 在 Layout Inspector 中查看 GPU 渲染
```

### RenderScript (已废弃)
虽然 RenderScript 已被废弃，但了解其对于分析遗留代码仍然有用。

#### 主要功能
- GPU 加速计算
- 图像处理算法
- 并行计算任务

## 14.9 Android Camera 性能与 Perfetto 分析

### Camera 性能特点
- 实时性要求高（60fps+）
- 内存带宽要求高
- CPU/GPU 协同工作

### Perfetto 分析要点
```sql
-- 查找 Camera 相关的事件
SELECT name FROM slice WHERE name GLOB 'Camera*';

-- 分析 Camera 操作耗时
SELECT slice.name, slice.dur/1e6 AS dur_ms
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread USING(utid)
JOIN process USING(upid)
WHERE process.name = 'com.example.app'
  AND slice.name GLOB 'Camera*'
ORDER BY slice.dur DESC;

-- 查看 Camera 2 API 调用链
SELECT * FROM slice 
WHERE name GLOB 'Camera2*'
ORDER BY ts;
```

### 调试技巧
```bash
# 检查 Camera 服务状态
adb shell dumpsys media.camera

# 查看 Camera 进程内存使用
adb shell dumpsys meminfo media.process.camera

# 监控 Camera 帧率
adb shell dumpsys gfxinfo | grep -A5 com.example.app
```

## 14.10 eBPF/BPF 在 Android 性能分析中的应用

### 基础概念
eBPF (Extended Berkeley Packet Filter) 是 Linux 内核的 tracing 技术优势：
- 无需内核修改即可运行 tracing 程序
- 性能开销极低（微秒级）
- 支持复杂的数据过滤和聚合

### Android 中的 eBPF 支持
```bash
# 检查 eBPF 支持
adb shell cat /sys/kernel/debug/tracing/available_events | grep binder

# 使用 trace-cmd 进行 eBPF tracing
trace-cmd record -e binder: binder_transaction -e sched:sched_switch
```

### 实际应用
#### Binder 调用监控
```c
// eBPF 程序示例
SEC("tracepoint/syscalls/sys_enter_openat")
int trace_openat(void *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    bpf_map_update_elem(&pid_map, &pid, &pid, BPF_ANY);
    return 0;
}
```

#### 进程调度分析
```sql
-- 使用 eBPF 数据分析进程调度
SELECT thread.name, sched.prio, slice.dur/1e6 AS dur_ms
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread USING(utid)
JOIN sched USING(utid)
WHERE process.name = 'com.example.app'
  AND slice.name GLOB 'sched*'
ORDER BY slice.ts;
```

## 14.11 Battery Historian 与功耗分析工具

### Battery Historian 简介
Google 官方的电池使用历史分析工具，用于详细分析设备功耗情况。

#### 使用方法
```bash
# 收集 bugreport
adb bugreport > bugreport.zip

# 使用 Battery Historian 分析
python /path/to/battery-historian/battery-historian.py bugreport.zip
```

#### 分析维度
- **CPU 使用率**：各进程 CPU 时间分布
- **网络使用**：数据传输和 Wi-Fi/蓝牙使用
- **传感器使用**：GPS、加速度计等传感器活动
- **屏幕亮度**：显示相关功耗分析

### 实际应用场景
```bash
# 监控特定应用的功耗
adb shell dumpsys batterystats com.example.app

# 重置电池统计（测试前使用）
adb shell dumpsys batterystats --reset

# 导出电池使用详情
adb shell dumpsys batterystats > battery_log.txt
```

## 14.12 APM / 可观测性平台与 SDK 选型

### APM 平台选型矩阵

| 平台 | 适用场景 | 优势 | 劣势 |
|------|---------|------|------|
| **Firebase Performance** | 中小团队，云端分析 | 无需自建，集成简单 | 自定义能力有限 |
| **Sentry** | 崩溃监控，错误追踪 | 错误归因能力强 | 功耗监控较弱 |
| **APMPlus (阿里)** | 国内企业，深度定制 | 符合国内环境，功能全面 | 学习成本高 |
| **Custom Solution** | 大型企业，定制需求 | 完全可控，深度定制 | 开发维护成本高 |

### SDK 集成指南

#### Firebase Performance 集成
```java
// Firebase 初始化
FirebasePerformance firebasePerformance = FirebasePerformance.getInstance();

// 监控网络请求
HttpMetric networkMetric = firebasePerformance.newHttpMetric("https://api.example.com/data", HttpMethod.GET);
networkMetric.startTiming();
// 发起网络请求...
networkMetric.stopTiming();

// 监控自定义指标
MetricCounter counter = firebasePerformance.newCounter("custom_events");
counter.increment();
```

#### 自定义监控方案
```java
// 自定义性能监控类
public class PerformanceMonitor {
    private Map<String, Long> timers = new HashMap<>();
    
    public void startTimer(String name) {
        timers.put(name, System.currentTimeMillis());
    }
    
    public void endTimer(String name) {
        Long start = timers.get(name);
        if (start != null) {
            long duration = System.currentTimeMillis() - start;
            // 上报到监控平台
            MetricsManager.getInstance().record(name, duration);
            timers.remove(name);
        }
    }
}
```

## 14.13 Hook 基础设施与性能工具实现原理

### Hook 技术原理
Hook 技术通过在方法调用前后插入代码来监控或修改行为。

#### 常见 Hook 方案
```java
// 基于 AspectJ 的方法级监控
@Around("execution(* com.example.app.MainActivity.*(..))")
public void monitorMethod(ProceedingJoinPoint joinPoint) throws Throwable {
    long start = System.currentTimeMillis();
    joinPoint.proceed();
    long duration = System.currentTimeMillis() - start;
    Log.d("MethodMonitor", joinPoint.getSignature() + " took " + duration + "ms");
}
```

#### Xposed 框架示例
```java
public class PerformanceHook implements IXposedHookLoadPackage {
    @Override
    public void handleLoadPackage(LoadPackageParam lpparam) {
        findAndHookMethod("com.example.app.MainActivity", 
            lpparam.classLoader, "onCreate", Bundle.class, new XC_MethodReplacement() {
                @Override
                protected Object replaceHookedMethod(MethodHookParam param) throws Throwable {
                    long start = System.currentTimeMillis();
                    Object result = super.replaceHookedMethod(param);
                    long duration = System.currentTimeMillis() - start;
                    Log.d("XposedHook", "MainActivity.onCreate took " + duration + "ms");
                    return result;
                }
            });
    }
}
```

### 性能工具实现原理

#### 火焰图生成
```python
def generate_flamegraph(stack_samples, output_file):
    """
    根据调用栈样本生成火焰图
    """
    from collections import defaultdict
    
    # 统计调用栈出现次数
    stack_counts = defaultdict(int)
    for stack in stack_samples:
        stack_counts[stack] += 1
    
    # 生成火焰图数据
    flame_data = []
    for stack, count in stack_counts.items():
        flame_data.append(f"{stack} {count}")
    
    # 保存到文件
    with open(output_file, 'w') as f:
        f.write('\n'.join(flame_data))
```

## 14.14 Android Studio LeakCanary Profiler 与堆转储分析

### LeakCanary 集成
Square 开源的内存泄漏检测工具，已被集成到 Android Studio 中。

#### 基础用法
```java
// Application 初始化
public class MyApplication extends Application {
    @Override
    public void onCreate() {
        super.onCreate();
        if (LeakCanary.isInAnalyzerProcess(this)) {
            return;
        }
        LeakCanary.install(this);
    }
}
```

#### 监测特定对象
```java
// 监测 Activity 泄漏
RefWatcher refWatcher = LeakCanary.refWatcher(this);
refWatcher.watch(targetActivity);

// 监测自定义对象
refWatcher.watch(mySingleton);
```

### 堆转储分析
```bash
# 导出 heap dump
adb shell am dumpheap <pkg> /sdcard/heapdump.hprof

# 使用 Android Studio 分析
adb pull /sdcard/heapdump.hprof ./analysis/
```

#### 分析技巧
- 使用 **Memory > Heap Dump** 视图分析
- 使用 **Leak Suspects** 自动查找泄漏
- 使用 **Path to GC Roots** 找到无法回收的原因

## 14.15 Winscope 与窗口/合成状态可视化调试

### Winscope 功能概述
Winscope 是 Android 官方提供的窗口状态可视化工具，特别适合渲染问题排查。

#### 主要功能
- **窗口层级可视化**：展示窗口的 Z-Order 和层级关系
- **Surface 状态监控**：Surface 的创建、销毁和状态变化
- **渲染帧分析**：帧率、掉帧、渲染时间统计
- **合成过程监控**：SurfaceFlinger 合成过程追踪

#### 使用方法
```bash
# 启动 Winscope
adb shell winscope

# 导出窗口信息
adb shell dumpsys activity windows | winscope

# 实时监控窗口变化
adb shell dumpsys activity windows --include=changed
```

### 实际应用场景

#### 渲染卡顿分析
```sql
-- 使用 Winscope 分析渲染卡顿
SELECT slice.name, slice.dur/1e6 AS dur_ms
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread USING(utid)
JOIN process USING(upid)
WHERE process.name = 'com.example.app'
  AND slice.name GLOB 'Choreographer#doFrame*'
  AND slice.dur > 16e6
ORDER BY slice.ts DESC;
```

#### 窗口层级问题
```sql
-- 查找窗口层级异常
SELECT window.name, window.z, window.layer_id
FROM window
WHERE window.name LIKE '%com.example.app%'
ORDER BY window.z;
```

## 14.16 Layout Inspector 与 ViewDebug 布局调试

### Layout Inspector 功能
Android Studio 提供的布局可视化分析工具。

#### 核心功能
- **布局层级可视化**：View 的层级关系和属性
- **渲染性能分析**：绘制操作的性能分析
- **过度绘制检测**：检测像素过度绘制问题
- **GPU 内存分析**：显存使用情况监控

#### 使用方法
```java
// 启用 GPU 调试
if (BuildConfig.DEBUG) {
    Debug.enableGPUContentViewInflation();
}

// 在 Layout Inspector 中查看布局结构
```

### ViewDebug 命令行工具
```bash
# 导出布局信息
adb shell dumpsys activity top | grep -A10 "View Hierarchy"

# 查看视图树
adb shell dumpsys activity windows | grep -A20 "View Hierarchy"

# 导出布局快照
adb shell uiautomator dump /sdcard/window_dump.xml
```

## 14.17 statsd 与系统级指标采集

### statsd 简介
Android 系统级指标收集服务，用于收集和聚合系统性能数据。

#### 基本使用
```bash
# 启用 statsd 收集
adb shell cmd statsd help

# 查看统计规则
adb shell cmd statsd list

# 添加监控规则
adb shell cmd statsd add-config my_config --condition=uid=<uid>
```

#### 配置示例
```bash
# 监控 ANR 事件
adb shell cmd statsd add-config anr_config \
    --condition=uid=$(adb shell pidof com.example.app) \
    --metric=anr \
    --sampling-interval=3600

# 监控内存使用
adb shell cmd statsd add-config memory_config \
    --condition=uid=$(adb shell pidof com.example.app) \
    --metric=memory.pss \
    --sampling-interval=60
```

### 高级配置
```python
#!/usr/bin/env python3
import subprocess
import json

def configure_statsd():
    """配置 statsd 收集规则"""
    app_uid = get_app_uid("com.example.app")
    
    # 配置 CPU 使用率监控
    cmd = [
        "adb", "shell", "cmd", "statsd", "add-config",
        f"cpu_config_{app_uid}",
        f"--condition=uid={app_uid}",
        "--metric=cpu.usage",
        "--sampling-interval=60"
    ]
    subprocess.run(cmd)
    
    # 配置内存监控
    cmd = [
        "adb", "shell", "cmd", "statsd", "add-config",
        f"memory_config_{app_uid}",
        f"--condition=uid={app_uid}",
        "--metric=memory.pss",
        "--sampling-interval=60"
    ]
    subprocess.run(cmd)

def get_app_uid(package_name):
    """获取应用 UID"""
    result = subprocess.run([
        "adb", "shell", "dumpsys", "package", package_name, 
        "| grep \"userId\""
    ], capture_output=True, text=True)
    uid = result.stdout.split()[1]
    return uid
```

## 14.18 Android Performance Analyzer 与系统性能分析

### Android Performance Analyzer (APA)
Google 官方的系统级性能分析工具。

#### 主要功能
- **启动性能分析**：冷启动、热启动耗时分解
- **内存分析**：应用内存使用趋势
- **渲染性能**：帧率、掉帧、渲染时间
- **功耗分析**：各组件耗电情况

#### 使用方法
```bash
# 启动 APA 监控
adb shell cmd performance start

# 停止监控并导出报告
adb shell cmd performance stop --output /data/local/tmp/performance_report.pb

# 导出报告到主机
adb pull /data/local/tmp/performance_report.pb

# 生成可读报告
python /path/to/apa/apa_performance_report.py performance_report.pb
```

#### 分析维度
```python
def analyze_performance_report(report_path):
    """分析性能报告"""
    import json
    
    with open(report_path, 'r') as f:
        report = json.load(f)
    
    # 启动时间分析
    startup_time = report.get('startup_time', {})
    print(f"冷启动时间: {startup_time.get('cold_start', 0)}ms")
    print(f"热启动时间: {startup_time.get('warm_start', 0)}ms")
    
    # 内存使用分析
    memory_usage = report.get('memory_usage', {})
    print(f"峰值内存: {memory_usage.get('peak_memory', 0)}MB")
    print(f"内存泄漏: {memory_usage.get('memory_leak', 0)}MB")
```

## 14.19 Android CLI 与 Agent 化性能调试工作流

### Android CLI 工具集
Android 提供了丰富的命令行工具用于性能调试。

#### 基础命令
```bash
# 获取设备信息
adb shell getprop | grep -i "ro.build"

# 监控设备状态
adb shell dumpsys cpuinfo | grep -E "com.example|system_server"

# 内存监控
adb shell dumpsys meminfo com.example.app | grep -E "Pss|Private"

# 网络监控
adb shell dumpsys connectivity | grep -A5 "com.example"
```

### Agent 化性能调试
```python
#!/usr/bin/env python3
import subprocess
import time
import json
from typing import Dict, List

class PerformanceAgent:
    """性能调试 Agent"""
    
    def __init__(self, package_name: str):
        self.package_name = package_name
        self.pid = self.get_pid()
        
    def get_pid(self) -> str:
        """获取应用进程 ID"""
        result = subprocess.run([
            "adb", "shell", "pidof", self.package_name
        ], capture_output=True, text=True)
        return result.stdout.strip()
    
    def monitor_cpu(self, duration: int = 60) -> Dict:
        """监控 CPU 使用情况"""
        cmd = [
            "adb", "shell", "dumpsys", "cpuinfo", 
            "|", "grep", "-E", f"{self.package_name}|system_server",
            "|", "awk", "'{print $3, $8}'"
        ]
        result = subprocess.run(" ".join(cmd), shell=True, 
                              capture_output=True, text=True)
        
        return {
            "package": self.package_name,
            "pid": self.pid,
            "cpu_info": result.stdout.strip(),
            "timestamp": time.time()
        }
    
    def monitor_memory(self) -> Dict:
        """监控内存使用情况"""
        cmd = [
            "adb", "shell", "dumpsys", "meminfo", self.package_name,
            "|", "grep", "-E", "Pss|Private|Heap"
        ]
        result = subprocess.run(" ".join(cmd), shell=True,
                              capture_output=True, text=True)
        
        return {
            "package": self.package_name,
            "memory_info": result.stdout.strip(),
            "timestamp": time.time()
        }
    
    def generate_report(self, data: List[Dict]) -> str:
        """生成性能报告"""
        report = {
            "package": self.package_name,
            "monitoring_data": data,
            "summary": self._analyze_data(data)
        }
        return json.dumps(report, indent=2)
    
    def _analyze_data(self, data: List[Dict]) -> Dict:
        """分析性能数据"""
        # 实现数据分析逻辑
        return {"status": "analyzed"}

# 使用示例
if __name__ == "__main__":
    agent = PerformanceAgent("com.example.app")
    
    # 监控 CPU
    cpu_data = agent.monitor_cpu()
    print(cpu_data)
    
    # 监控内存
    memory_data = agent.monitor_memory()
    print(memory_data)
```

## 14.20 R8 Configuration Analyzer 与 keep 规则体积归因

### R8 优化分析工具
R8 是 Android 的代码优化工具，可用于分析应用体积优化。

#### 基础分析
```bash
# 生成 R8 配置分析报告
./r8-config-analyzer app/build/intermediates/r8_bundle/debug/classes.jar

# 分析 keep 规则效果
./r8-config-analyzer --analyze-keep-rules app/build/intermediates/r8_bundle/debug/classes.jar
```

#### 体积归因分析
```python
#!/usr/bin/env python3
import subprocess
import re
from collections import defaultdict

def analyze_app_size():
    """分析应用体积组成"""
    # 获取 APK 大小
    result = subprocess.run([
        "adb", "shell", "stat", "-c", "%s", 
        "/data/app/com.example.app/base.apk"
    ], capture_output=True, text=True)
    apk_size = int(result.stdout.strip())
    
    # 分析各模块大小
    result = subprocess.run([
        "adb", "shell", "dumpsys", "package", "com.example.app",
        "|", "grep", "-A5", "PackageSignatures"
    ], shell=True, capture_output=True, text=True)
    
    # 解析模块大小
    module_sizes = {}
    for line in result.stdout.splitlines():
        if "codeSize" in line:
            match = re.search(r"(\w+): (\d+) bytes", line)
            if match:
                module = match.group(1)
                size = int(match.group(2))
                module_sizes[module] = size
    
    return {
        "total_apk_size": apk_size,
        "module_sizes": module_sizes,
        "recommendations": generate_recommendations(module_sizes)
    }

def generate_recommendations(module_sizes):
    """生成优化建议"""
    recommendations = []
    
    # 找出最大的模块
    if module_sizes:
        largest_module = max(module_sizes.items(), key=lambda x: x[1])
        recommendations.append(
            f"考虑优化 {largest_module[0]} 模块，当前大小 {largest_module[1]/1024/1024:.2f}MB"
        )
    
    return recommendations

if __name__ == "__main__":
    analysis = analyze_app_size()
    print(json.dumps(analysis, indent=2))
```

## 14.21 eBPF 系统架构：bpfloader Rust 化与 BPF 程序组织

### eBPF 在 Android 中的架构
Android 12+ 开始逐步支持 eBPF 技术，主要用于系统级 tracing。

#### 基本架构
```c
// eBPF 程序示例：监控系统调用
SEC("tracepoint/syscalls/sys_enter_openat")
int trace_openat(void *ctx) {
    struct event_t {
        u32 pid;
        u32 uid;
        char comm[16];
        char filename[127];
    } event = {};
    
    struct trace_event_raw_sys_enter *args = ctx;
    event.pid = bpf_get_current_pid_tgid() >> 32;
    event.uid = bpf_get_current_uid_gid() >> 32;
    bpf_get_current_comm(&event.comm, sizeof(event.comm));
    bpf_probe_read_user_str(&event.filename, sizeof(event.filename), 
                           (void *)args->args[0]);
    
    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, 
                         &event, sizeof(event));
    
    return 0;
}
```

### bpfloader Rust 实现
Android 13+ 开始使用 Rust 实现 bpfloader。

```rust
// bpfloader 简化实现
pub struct BpfLoader {
    programs: HashMap<String, BpfProgram>,
    maps: HashMap<String, BpfMap>,
}

impl BpfLoader {
    pub fn new() -> Self {
        Self {
            programs: HashMap::new(),
            maps: HashMap::new(),
        }
    }
    
    pub fn load_program(&mut self, name: &str, code: &[u8]) -> Result<(), Error> {
        let prog = BpfProgram::load(name, code)?;
        self.programs.insert(name.to_string(), prog);
        Ok(())
    }
    
    pub fn attach(&self, name: &str, event: &str) -> Result<(), Error> {
        if let Some(prog) = self.programs.get(name) {
            prog.attach(event)?;
        }
        Ok(())
    }
}
```

### 实际应用场景
```bash
# 加载 eBPF 程序
sudo /system/bin/bpfloader load /path/to/binder_tracer.o

# 监控 Binder 调用
sudo /system/bin/bpfloader attach binder_tracer binder_transaction

# 查看结果
cat /sys/kernel/debug/tracing/trace_pipe
```

## 14.22 HPROF Heap Dump 管线与 Perfetto java_hprof 数据源

### HPROF 堆转储管线
Android 中常用的内存分析数据格式。

#### 基本概念
- **HPROF**：Java 堆内存转储格式
- **Heap Dump**：包含对象分配、引用关系等信息
- **Memory Profiler**：分析 heap dump 的工具

#### 生成方式
```bash
# 使用 am dumpheap
adb shell am dumpheap com.example.app /sdcard/heapdump.hprof

# 使用 Runtime.getRuntime().gc()
adb shell am broadcast -a android.intent.action.MEMORY_DUMP --es target com.example.app
```

### Perfetto java_hprof 数据源
Perfetto 支持直接分析 HPROF 数据。

#### 配置示例
```sql
-- 使用 java_hprof 数据源
INCLUDE PERFETTO MODULE java_hprof;

-- 查找内存泄漏
SELECT obj.name, obj.size, obj.count
FROM java_heap_object obj
WHERE obj.retained_size > 1e6
  AND obj.root_type = 'GLOBAL JNI REF'
ORDER BY obj.retained_size DESC;

-- 分析对象引用链
SELECT * FROM java_object_reference 
WHERE source_object_id = 12345;
```

### 实际分析流程
```python
#!/usr/bin/env python3
import subprocess
import json

def analyze_hprof(hprof_path):
    """分析 HPROF 文件"""
    # 使用 MAT 或 Android Studio 分析
    cmd = [
        "android-studio", 
        "/path/to/mat/plugins/org.eclipse.mat.hprof.ui_*.jar",
        "--vmargs", "-Xmx4g",
        hprof_path
    ]
    subprocess.run(cmd)
    
    # 或者使用命令行工具
    cmd = [
        "java", "-jar", "/path/to/mat/plugins/org.eclipse.mat.api_*.jar",
        "--vmargs", "-Xmx4g",
        "--parse", hprof_path,
        "--report", "memory_leak_report.html"
    ]
    subprocess.run(cmd)
```

## 14.23 StrictMode 性能检查与开发期诊断

### StrictMode 简介
Android 提供的开发期性能检查工具，用于检测性能问题。

#### 基本使用
```java
// 启用 StrictMode
StrictMode.setThreadPolicy(new StrictMode.ThreadPolicy.Builder()
    .detectDiskReads()
    .detectDiskWrites()
    .detectNetwork()
    .penaltyLog()
    .build());

StrictMode.setVmPolicy(new StrictMode.VmPolicy.Builder()
    .detectLeakedSqlLiteObjects()
    .detectLeakedClosableObjects()
    .penaltyLog()
    .build());
```

#### 自定义检查
```java
// 自定义性能检查
StrictMode.setThreadPolicy(new StrictMode.ThreadPolicy.Builder()
    .penaltyLog() // 记录日志
    .penaltyDeath() // 直接崩溃（开发环境）
    .detectCustomSlowCalls(100) // 检测慢调用
    .build());

// 自定义慢调用检查
public void customSlowMethod() {
    StrictMode.noteSlowCall("Custom slow method called");
    // 你的慢代码
}
```

### 开发期诊断
```java
// 应用启动时检查
public class MyApplication extends Application {
    @Override
    public void onCreate() {
        super.onCreate();
        
        // 启用 StrictMode（仅调试版本）
        if (BuildConfig.DEBUG) {
            enableStrictMode();
        }
    }
    
    private void enableStrictMode() {
        StrictMode.setThreadPolicy(new StrictMode.ThreadPolicy.Builder()
            .detectDiskReads()
            .detectDiskWrites()
            .detectNetwork()
            .penaltyLog()
            .penaltyFlashScreen()
            .build());
    }
}
```

### 日志分析
```bash
# 查看 StrictMode 警告
adb logcat | grep "StrictMode"

# 过滤特定类型的 StrictMode 违规
adb logcat | grep "StrictMode.*diskRead"
```

## 版本演进

### 工具演进趋势

#### Android 11 (API 30)
- 引入 ProfilingManager 系统 API
- Battery Historian 功能增强
- 新增网络质量监控 API

#### Android 12 (API 31)
- eBPF 支持增强
- 新增 WindowMetrics API
- 性能基线数据收集

#### Android 13 (API 33)
- bpfloader Rust 化实现
- Perfetto 支持增强
- 内存分析工具改进

#### Android 14 (API 34)
- 性能监控 API 稳定
- 新增功耗监控模块
- 渲染性能分析工具改进

#### Android 15 (API 35)
- 实时性能监控能力
- AI 辅助性能分析
- 自动化性能优化建议

#### Android 16 (API 36)
- 性能数据云端同步
- 实时性能基准比较
- 跨设备性能分析

#### Android 17 (API 37)
- 全面支持 eBPF tracing
- 智能性能优化建议
- 实时性能基线调整

### 使用建议

#### 开发阶段
1. **Android Studio Profiler**：开发阶段最主要的性能监控工具
2. **StrictMode**：开发期的性能检查，避免常见性能问题
3. **LeakCanary**：内存泄漏检测，确保内存使用健康

#### 测试阶段
1. **Perfetto**：深度性能分析，查找复杂性能问题
2. **Simpleperf**：Native 代码性能分析
3. **Battery Historian**：功耗分析

#### 生产环境
1. **APM 平台**：线上性能监控和告警
2. **自定义监控**：基于业务需求的性能监控
3. **自动化报告**：定期性能报告和分析

## 常见问题与误区

### 误区：工具越多越好

**实际情况**：
- 工具过多会造成维护负担
- 不同工具有不同的适用场景
- 监控过多会影响应用性能

**正确做法**：
- 根据开发阶段选择合适的工具
- 重点关注核心性能指标
- 建立统一的性能监控体系

### 误区：监控数据越多越好

**实际情况**：
- 过多的监控数据会占用大量内存
- 影响应用运行性能
- 数据分析复杂度增加

**正确做法**：
- 监控关键性能指标
- 合理设置采样频率
- 使用分级监控策略

### 误区：工具可以替代人工分析

**实际情况**：
- 工具只能提供数据，无法替代人工判断
- 复杂性能问题需要综合分析
- 工具可能产生误报或漏报

**正确做法**：
- 工具和人工分析相结合
- 建立性能问题的分析流程
- 积累经验，提高分析效率

## 与其他章节的关系

本章内容与其他章节有密切关联：

- **第 13 章：Perfetto** - 本章是 Perfetto 的重要补充，提供其他分析工具
- **第 7 章：流畅性** - 本章工具可用于分析流畅性问题
- **第 9 章：ANR** - 本章工具可用于 ANR 问题排查
- **第 10 章：内存性能** - 本章工具用于内存问题分析
- **第 11 章：功耗** - 本章工具用于功耗问题分析

## 参考资料

- Android Developer 文档：https://developer.android.com/studio/profile
- LeakCanary 文档：https://github.com/square/leakcanary
- Battery Historian 文档：https://github.com/google/battery-historian
- Perfetto 文档：https://perfetto.dev/docs
- Simpleperf 文档：https://source.android.com/docs/perfetto/record-and-analyze/simpleperf
- MAT 文档：https://www.eclipse.org/mat/
- eBPF 教程：https://ebpf.io/what-is-ebpf/
- Winscope 文档：https://source.android.com/docs/core-ui/windows/window-composition/winscope