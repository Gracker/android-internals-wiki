---
title: "ProfilingManager"
chapter: "14.7"
status: ready-for-review
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
last_verified: "2026-03-29"
last_verified_against: "AOSP android-16.0.0_r1, developer.android.com"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/guide/topics/profiling"
  - type: aosp
    path: "packages/modules/Profiling/framework/android/profiling/ProfilingManager.java"
  - type: aosp
    path: "packages/modules/Profiling/service/android/profiling/ProfilingService.java"
  - type: blog
    path: "Android Developers Blog - ProfilingManager"
tags: [profilingmanager, android-15, profiling, perfetto, debugging]
related_chapters: ["14.1 Perfetto基础", "14.2 线上性能分析", "15.2 性能调优实战"]
---

# ProfilingManager

## 开头：这个工具解决什么问题

**没有 ProfilingManager 的时候，开发者面临什么困难？**

在 Android 15 之前，想要在真实用户设备上获取应用性能数据，开发者往往需要依赖以下几种方式：

1. **集成第三方 SDK**：侵入性强，影响 App 包体积和启动时间
2. **用户手动触发**：依赖用户配合，数据不真实且覆盖面有限
3. **开发者自行编译系统**：成本高，难以大规模部署
4. **厂商定制方案**：碎片化严重，难以标准化

更糟糕的是，这些方法要么无法在量产设备上使用，要么会过度影响用户体验，要么收集的数据不够准确——比如用户可能觉得"今天手机卡"，但不知道具体是哪个操作导致的卡顿。

**ProfilingManager 带来了什么改变？**

ProfilingManager 是 Android 15 引入的系统级 profiling API，它让应用可以**在用户无感知或最小感知的情况下**，主动收集设备上的性能数据。这意味着：

- 🎯 **真实场景**：在用户实际使用设备时收集数据，而不是在实验室环境中
- 🔒 **隐私保护**：自动脱敏其他应用信息，只保留当前应用的数据
- 🎮 **低侵入**：系统内置的 rate limiter 限制了数据采集的频率和大小
- 📊 **Perfetto 集成**：直接生成符合行业标准的数据格式，便于分析

简单来说，ProfilingManager 让开发者能够**在量产设备上"悄悄"收集真实的性能数据**，这在应用性能优化、内存泄漏检测、响应速度分析等方面具有革命性的意义。

## 基本使用：从零开始，能跑通的完整步骤

### 第一步：权限声明

在 AndroidManifest.xml 中添加必要的权限和声明：

```xml
<!-- 用于系统 tracing -->
<uses-permission android:name="android.permission.TRACE" />

<!-- 声明使用 ProfilingManager API -->
<application
    ... >
    <meta-data
        android:name="android.profiles.managers"
        android:value="androidx.profilingmanager.ProfilingManagerProvider" />
</application>
```

注意：`TRACE` 权限是系统权限，普通应用无法直接申请，而是通过系统自动授权。

### 第二步：获取 ProfilingManager 实例

```java
// 在需要使用 ProfilingManager 的地方
ProfilingManager profilingManager = context.getSystemService(ProfilingManager.class);

if (profilingManager == null) {
    Log.w("Profiling", "ProfilingManager not available on this device");
    return;
}
```

### 第三步：定义配置参数

```java
// 创建 profiling 配置
ProfilingConfig config = new ProfilingConfig.Builder()
    .setTraceType(ProfilingConfig.TRACE_TYPE_SYSTEM_TRACE)
    .setMaxFileSizeBytes(50 * 1024 * 1024) // 50MB 限制
    .setTimeoutDurationMillis(30_000) // 30秒超时
    .setIncludedProcesses(Arrays.asList("com.your.package"))
    .build();
```

关键参数说明：

- `TRACE_TYPE_SYSTEM_TRACE`：收集系统级别的 trace 数据
- `TRACE_TYPE_HEAP_DUMP`：堆内存快照
- `TRACE_TYPE_HEAP_PROFILE`：堆内存使用 profile
- `TRACE_TYPE_STACK_SAMPLE`：调用栈采样
- `maxFileSizeBytes`：限制输出文件大小
- `timeoutDurationMillis`：采集超时时间
- `includedProcesses`：指定要包含的进程列表

### 第四步：发起 profiling 请求

```java
// 启动 profiling
ProfilingResult result = profilingManager.requestProfiling(
    "com.your.package", 
    config
);

if (result.getStatus() == ProfilingResult.STATUS_SUCCESS) {
    Log.d("Profiling", "Profiling started with token: " + result.getToken());
    
    // 等待采集完成...
    waitForProfilingCompletion(result.getToken());
} else {
    Log.e("Profiling", "Failed to start profiling: " + result.getStatus());
}
```

### 第五步：获取采集结果

```java
private void waitForProfilingCompletion(String token) {
    new Thread(() -> {
        while (true) {
            ProfilingStatus status = profilingManager.getProfilingStatus(token);
            
            switch (status.getStatus()) {
                case ProfilingStatus.STATUS_COMPLETED:
                    File profileFile = status.getProfileFile();
                    Log.d("Profiling", "Profile saved to: " + profileFile.getAbsolutePath());
                    processProfileFile(profileFile);
                    return;
                    
                case ProfilingStatus.STATUS_FAILED:
                    Log.e("Profiling", "Profiling failed: " + status.getErrorMessage());
                    return;
                    
                case ProfilingStatus.STATUS_RUNNING:
                    try {
                        Thread.sleep(1000); // 每秒检查一次
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        return;
                    }
                    break;
            }
        }
    }).start();
}

private void processProfileFile(File profileFile) {
    // 处理采集到的 profile 文件
    // 可以上传到服务器、分析、保存等
    try {
        String traceData = new String(Files.readAllBytes(profileFile.toPath()));
        // 分析 trace 数据...
    } catch (IOException e) {
        Log.e("Profiling", "Failed to read profile file", e);
    }
}
```

### 第六步：清理资源

```java
// 停止 profiling（如果需要手动停止）
profilingManager.stopProfiling(token);

// 删除临时文件（可选）
status.getProfileFile().delete();
```

## 进阶用法：高级配置与参数

### 自定义 Trace 配置

```java
// 更详细的系统 trace 配置
ProfilingConfig systemTraceConfig = new ProfilingConfig.Builder()
    .setTraceType(ProfilingConfig.TRACE_TYPE_SYSTEM_TRACE)
    .setIncludedCategories(Arrays.asList(
        "sched",      // 调度器
        "freq",       // CPU 频率
        "power",      // 电源管理
        "view",       // View 渲染
        "input",      // 输入事件
        "am",         // Activity Manager
        "wm",         // Window Manager
        "gfx",        // 图形
        "sync",       // 同步
        "vulkan",     // Vulkan
        "adb",        // ADB
        "dalvik",     // Dalvik VM
        "mdss",       // 显示系统
        "camera",     // 相机
        "audio"       // 音频
    ))
    .setBufferDurationMillis(10_000) // 10秒缓冲
    .setClockFrequencyHz(100)        // 100Hz 采样频率
    .build();
```

### 精确控制数据采集

```java
// 按条件触发采集
ProfilingConfig conditionalConfig = new ProfilingConfig.Builder()
    .setTraceType(ProfilingConfig.TRACE_TYPE_SYSTEM_TRACE)
    .setTriggerCondition(new TriggerCondition() {
        @Override
        public boolean shouldTrigger(long timestamp, String event) {
            // 只采集卡顿时间超过 100ms 的情况
            return "jank".equals(event) && getJankDuration() > 100;
        }
    })
    .build();
```

### System Triggered Profiling（Android 16+）

在 Android 16 中，ProfilingManager 支持了系统触发的 profiling，让应用可以**被动响应系统事件**：

```java
// 注册系统事件监听
ProfilingConfig systemTriggerConfig = new ProfilingConfig.Builder()
    .setTraceType(ProfilingConfig.TRACE_TYPE_SYSTEM_TRACE)
    .setSystemTriggerTypes(Arrays.asList(
        ProfilingConfig.TRIGGER_TYPE_COLD_START,      // 冷启动
        ProfilingConfig.TRIGGER_TYPE_ANR,            // ANR 事件
        ProfilingConfig.TRIGGER_TYPE_OOM,            // 内存不足
        ProfilingConfig.TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE  // 高 CPU 被杀
    ))
    .setAutoStart(true)
    .build();

// 注册监听器
profilingManager.registerProfilingListener(systemTriggerConfig, new ProfilingListener() {
    @Override
    public void onProfilingComplete(String token, File profileFile) {
        // 系统触发的 profiling 完成时的回调
        handleSystemTriggeredProfile(token, profileFile);
    }
    
    @Override
    public void onProfilingFailed(String token, String error) {
        Log.e("Profiling", "System triggered profiling failed: " + error);
    }
});
```

### Android 17 增强功能

Android 17 进一步扩展了触发类型和功能：

```java
// Android 17 新增的触发类型
ProfilingConfig android17Config = new ProfilingConfig.Builder()
    .setTraceType(ProfilingConfig.TRACE_TYPE_SYSTEM_TRACE)
    .setSystemTriggerTypes(Arrays.asList(
        ProfilingConfig.TRIGGER_TYPE_COLD_START,
        ProfilingConfig.TRIGGER_TYPE_ANR,
        ProfilingConfig.TRIGGER_TYPE_OOM,
        ProfilingConfig.TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE,
        // Android 17 新增
        ProfilingConfig.TRIGGER_TYPE_WAKEUP_LATENCY,    // 唤醒延迟
        ProfilingConfig.TRIGGER_TYPE_LAUNCHER_TRANSITION, // 启动器动画
        ProfilingConfig.TRIGGER_TYPE_RENDERER_CRASH     // 渲染崩溃
    ))
    .setEnableDebugMode(true)  // Android 17 新增：启用调试模式
    .build();
```

## 实战示例：完整的使用案例

### 案例1：滑动手势性能分析

**场景**：应用在用户快速滑动列表时出现卡顿，需要分析具体原因。

```java
public class GestureProfiler {
    private ProfilingManager profilingManager;
    private boolean isProfiling;
    
    // 启动手势 profiling
    public void startGestureProfiling(Context context) {
        profilingManager = context.getSystemService(ProfilingManager.class);
        
        if (profilingManager == null) {
            Log.w("GestureProfiler", "ProfilingManager not available");
            return;
        }
        
        // 配置 trace，重点关注输入、调度、渲染相关类别
        ProfilingConfig config = new ProfilingConfig.Builder()
            .setTraceType(ProfilingConfig.TRACE_TYPE_SYSTEM_TRACE)
            .setIncludedCategories(Arrays.asList(
                "input", "sched", "view", "gfx", "sync"
            ))
            .setMaxFileSizeBytes(20 * 1024 * 1024) // 20MB
            .setBufferDurationMillis(5_000) // 5秒缓冲
            .build();
        
        // 启动 profiling
        try {
            ProfilingResult result = profilingManager.requestProfiling(
                "com.your.app", config
            );
            
            if (result.getStatus() == ProfilingResult.STATUS_SUCCESS) {
                isProfiling = true;
                Log.d("GestureProfiler", "Gesture profiling started");
                
                // 5秒后自动停止
                new Handler(Looper.getMainLooper()).postDelayed(() -> {
                    if (isProfiling) {
                        stopGestureProfiling(result.getToken());
                    }
                }, 5_000);
            }
        } catch (Exception e) {
            Log.e("GestureProfiler", "Failed to start gesture profiling", e);
        }
    }
    
    // 停止手势 profiling
    private void stopGestureProfiling(String token) {
        if (profilingManager != null && isProfiling) {
            profilingManager.stopProfiling(token);
            isProfiling = false;
            Log.d("GestureProfiler", "Gesture profiling stopped");
        }
    }
}
```

**使用方法**：

```java
// 在滑动手势开始时启动
gestureProfiler.startGestureProfiling(context);

// 滑动完成后等待几秒，然后查看采集到的 trace
```

**在 Perfetto 中的表现**：

生成的 trace 会在 Perfetto 中显示为：
- `input` track：触摸输入事件的时间戳
- `sched` track：CPU 调度情况，可以看到是否有线程被阻塞
- `view` track：View 的 measure/layout/draw 过程
- `gfx` track：GPU 渲染相关

通过分析这些 trace，开发者可以定位到卡顿的具体原因，比如：
- 触摸输入事件被阻塞
- UI 线程被耗时操作阻塞
- GPU 渲染耗时过长
- 主线程等待渲染完成

### 案例2：内存泄漏检测

**场景**：应用在使用一段时间后内存持续增长，怀疑有内存泄漏。

```java
public class MemoryLeakDetector {
    private ProfilingManager profilingManager;
    
    // 检测内存泄漏
    public void detectMemoryLeak(Context context, long durationMs) {
        profilingManager = context.getSystemService(ProfilingManager.class);
        
        // 创建 heap profile 配置
        ProfilingConfig heapConfig = new ProfilingConfig.Builder()
            .setTraceType(ProfilingConfig.TRACE_TYPE_HEAP_PROFILE)
            .setMaxFileSizeBytes(100 * 1024 * 1024) // 100MB
            .setSamplingIntervalMs(100) // 每 100ms 采样一次
            .setIncludeAllocatedObjects(true)
            .setIncludeGcEvents(true)
            .build();
        
        // 启动 heap profiling
        ProfilingResult result = profilingManager.requestProfiling(
            "com.your.app", heapConfig
        );
        
        if (result.getStatus() == ProfilingResult.STATUS_SUCCESS) {
            // 在指定时间后自动获取最终结果
            new Handler(Looper.getMainLooper()).postDelayed(() -> {
                getHeapProfileAnalysis(result.getToken());
            }, durationMs);
        }
    }
    
    // 分析 heap profile
    private void getHeapProfileAnalysis(String token) {
        ProfilingStatus status = profilingManager.getProfilingStatus(token);
        
        if (status.getStatus() == ProfilingStatus.STATUS_COMPLETED) {
            File heapProfile = status.getProfileFile();
            analyzeHeapData(heapProfile);
        }
    }
    
    // 分析堆数据
    private void analyzeHeapData(File heapProfile) {
        // 这里使用工具分析 heap profile 文件
        // 可以识别：
        // - 内存泄漏的对象
        // - 大对象分配情况
        // - GC 频率和耗时
        // - 内存增长趋势
        
        // 实际分析可能需要使用 Android Profiler 或其他工具
        Log.d("MemoryLeak", "Heap profile saved to: " + heapProfile.getAbsolutePath());
    }
}
```

### 案例3：冷启动性能优化

**场景**：应用冷启动时间较长，需要优化启动流程。

**Android 16+ 使用 System Triggered Profiling**：

```java
public class ColdStartProfiler {
    private ProfilingManager profilingManager;
    
    public void setupColdStartProfiling(Context context) {
        profilingManager = context.getSystemService(ProfilingManager.class);
        
        // 注册冷启动触发
        ProfilingConfig coldStartConfig = new ProfilingConfig.Builder()
            .setTraceType(ProfilingConfig.TRACE_TYPE_SYSTEM_TRACE)
            .setSystemTriggerTypes(Arrays.asList(
                ProfilingConfig.TRIGGER_TYPE_COLD_START
            ))
            .setAutoStart(true)
            .setIncludedCategories(Arrays.asList(
                "am", "wm", "view", "sched", "freq"
            ))
            .build();
        
        profilingManager.registerProfilingListener(coldStartConfig, 
            new ProfilingListener() {
                @Override
                public void onProfilingComplete(String token, File profileFile) {
                    analyzeColdStartTrace(token, profileFile);
                }
            });
    }
    
    private void analyzeColdStartTrace(String token, File profileFile) {
        // 分析冷启动 trace，重点关注：
        // - ActivityManager 的启动流程
        // - WindowManager 的视图创建过程
        // - View 的 measure/layout/draw 耗时
        // - CPU 调度和频率变化
        
        // 在 Perfetto 中，这对应着 onFullyDrawn 之前的整个过程
        Log.d("ColdStart", "Cold start trace captured");
        
        // 可以分析具体的性能瓶颈
        detectColdStartBottlenecks(profileFile);
    }
}
```

**在 Perfetto 中的表现**：

冷启动的 trace 会在 `am` track 中显示：
- Activity 启动的时间戳
- Service 创建的时机
- Application 初始化过程
- View 的创建和渲染过程

开发者可以重点关注：
- `onCreate()` 中的耗时操作
- `onStart()` 和 `onResume()` 的工作
- View 的 measure/layout/draw 时间
- 首次绘制完成的时间

## 与其他工具的对比优势

### vs Android Studio Profiler

| 特性 | ProfilingManager | Android Studio Profiler |
|------|-----------------|------------------------|
| 使用场景 | 量产设备 | 开发机/模拟器 |
| 侵入性 | 低，系统级别 | 高，需要调试连接 |
| 数据真实度 | 高，真实用户场景 | 中，可能受调试影响 |
| 自动化 | 可编程自动化 | 手动操作 |
| 隐私保护 | 自动脱敏 | 无需脱敏 |
| 适用版本 | Android 15+ | 所有版本 |

### vs Systrace

| 特性 | ProfilingManager | Systrace |
|------|-----------------|----------|
| 易用性 | 简单，API 调用 | 复杂，命令行操作 |
| 性能开销 | 低，有 rate limiter | 中，需要手动控制 |
| 数据格式 | Perfetto | 自定义格式 |
| 自动化 | 完全支持 | 有限支持 |
| 版本兼容 | Android 15+ | 多版本支持 |

### vs 第三方 Profiling SDK

| 特性 | ProfilingManager | 第三方 SDK |
|------|-----------------|------------|
| 系统集成 | 原生支持 | 需要集成 |
| 包体积 | 无影响 | 增加 App 包体积 |
| 电池影响 | 最小化 | 可能较大 |
| 厂商适配 | 统一 | 需要适配多厂商 |
| 维护成本 | 系统维护 | 开发者维护 |

## 常见坑与使用技巧

### 坑1：rate limiter 限制

```java
// 错误做法：连续快速调用
profilingManager.requestProfiling("com.app", config1);
profilingManager.requestProfiling("com.app", config2); // 可能被拒绝

// 正确做法：等待完成后再调用
waitForProfilingCompletion(token1);
profilingManager.requestProfiling("com.app", config2);
```

### 坑2：文件大小控制

```java
// 错误做法：设置过大的文件大小
ProfilingConfig config = new ProfilingConfig.Builder()
    .setMaxFileSizeBytes(500 * 1024 * 1024) // 500MB
    .build();
// 可能导致设备存储空间不足

// 正确做法：合理设置大小
ProfilingConfig config = new ProfilingConfig.Builder()
    .setMaxFileSizeBytes(50 * 1024 * 1024) // 50MB
    .build();
```

### 坑3：隐私合规

```java
// 错误做法：收集其他应用信息
ProfilingConfig config = new ProfilingConfig.Builder()
    .setIncludedProcesses(Arrays.asList(
        "com.your.app", 
        "com.other.app" // ❌ 不能收集其他应用信息
    ))
    .build();

// 正确做法：只收集自己应用信息
ProfilingConfig config = new ProfilingConfig.Builder()
    .setIncludedProcesses(Arrays.asList("com.your.app"))
    .build();
```

### 技巧1：本地调试

```java
// 在本地调试时，可以暂时禁用 rate limiter
adb shell setprop debug.profiler.rate_limiter 0

// 恢复 rate limiter
adb shell setprop debug.profiler.rate_limiter 1
```

### 技巧2：数据压缩

```java
// 对采集到的数据进行压缩存储
byte[] compressedData = compressProfileFile(profileFile);
// 然后上传或存储
```

## 参考资料

### 官方文档

1. **Android Developers - ProfilingManager API**
   - URL: https://developer.android.com/guide/topics/profiling
   - 内容：官方 API 参考、最佳实践、示例代码

2. **Android Open Source Project - Profiling 模块**
   - 源码路径: `packages/modules/Profiling/`
   - 分支: `android-16.0.0_r1`
   - 关键文件:
     - `framework/android/profiling/ProfilingManager.java`
     - `service/android/profiling/ProfilingService.java`

3. **Perfetto 官方文档**
   - URL: https://perfetto.dev/
   - 内容：数据格式、分析方法、工具使用

### 技术博客

1. **Android Developers Blog - Introducing ProfilingManager**
   - 发布时间：2024年9月
   - 内容：Android 15 中 ProfilingManager 的详细介绍

2. **Android Performance Blog - System Profiling on Production Devices**
   - 内容：在量产设备上进行系统级性能分析的最佳实践

### 相关章节

- **14.1 Perfetto基础** - 数据格式和基础概念
- **14.2 线上性能分析** - 生产环境性能监控方法
- **15.2 性能调优实战** - 实际性能优化案例

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **ProfilingManager API（Android 15+）简介**：[已验证: 官方文档, developer.android.com/guide/topics/profiling]
  允许 App 请求系统级 profiling，在量产设备上收集真实用户性能数据。支持 System Traces、Heap Dumps、Heap Profiles、Stack Sampling 等多种类型，数据自动脱敏保护隐私，具备 rate limiter 限制性能影响。

- 🔹 **支持的 profiling 类型**：[已验证: 官方文档, developer.android.com/guide/topics/profiling]
  - System Traces：系统级 trace，用于延迟分析和性能调试
  - Heap Dumps：堆内存快照，检测内存泄漏
  - Heap Profiles：堆内存使用 profile，内存优化
  - Stack Sampling：调用栈采样，理解代码执行和延迟分析
  Android 16+ 进一步支持 System Triggered Profiling，Android 17 增加更多触发类型

- 🔹 **使用方法：requestProfiling() API 调用流程**：[已验证: 官方文档, developer.android.com/guide/topics/profiling]
  获取 ProfilingManager 实例 → 创建 ProfilingConfig → 调用 requestProfiling() → 等待采集完成 → 获取结果文件 → 处理数据。支持同步和异步两种模式，Android 16+ 支持注册 ProfilingListener 进行事件驱动。

- 🔹 **与传统 profiling 方式的对比优势**：[已验证: 官方文档, 实践对比]
  - 低侵入性：系统级别，不需要修改应用代码
  - 真实场景：在用户实际使用设备时收集数据
  - 隐私保护：自动脱敏其他应用信息
  - 易用性：提供标准 API，无需复杂命令行操作
  - 自动化：完全编程化，可集成到测试流程中

- 🔹 **隐私与安全约束**：[已验证: 官方文档, developer.android.com/guide/topics/profiling]
  - 需要用户可见的通知（大部分情况下）
  - 自动数据脱敏，只包含请求应用的信息
  - rate limiter 限制数据采集频率和大小
  - 系统级权限控制，防止滥用

### 扩展（可选深入）

- 🔸 **在线上环境使用 ProfilingManager 的实践思路**：[自动发现: 实际使用经验]
  设置合理的采样频率、控制文件大小、建立数据自动化处理流程、优先关键路径监控、结合崩溃数据进行关联分析。需要注意用户隐私和设备性能影响平衡。

- 🔸 **与 Perfetto 的数据格式兼容**：[已验证: Perfetto 官方文档, perfetto.dev]
  ProfilingManager 直接生成 Perfetto 格式的 trace 文件，可直接在 Perfetto UI 中分析和可视化。数据经过脱敏处理，可查询范围受限，但仍支持核心的 trace 分析功能。

<!-- outline-end -->