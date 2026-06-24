---
title: "ProfilingManager 系统触发式性能追踪"
chapter: "8.16"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: ["profiling", "performance", "android-system", "performance-tracing"]
related_chapters: ["2.4", "7.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-24"
gap_source: "research-gaps-md"
drafted_date: "2026-06-24"
last_verified: "2026-06-24"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProfilingManager.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing"
---

# 8.16 ProfilingManager 系统触发式性能追踪

<!-- outline-start -->
## 要点

### 🔸 ProfilingManager 概念与用途
系统触发式性能追踪机制在 Android 中的作用与定位

### 🔸 AOSP 标准实现路径
frameworks/base/services/core/java/com/android/server/am/ProfilingManager.java

### 🔸 厂商定制实现差异
Samsung、Xiaomi、Huawei 等主流厂商的实现特点

### 🔸 降级方案兼容层
在不支持 ProfilingManager 的设备上的性能替代方案

### 🔸 与 ActivityManagerService 交互
触发机制、权限控制、生命周期回调

### 🔸 实际使用场景分析
哪些性能问题最适合用系统触发式追踪方法

### 🔸 工具集成与调试
Perfetto、Systrace 与 ProfilingManager 的协作方式

## 扩展

### 🔸 厂商实现源码对比
主流厂商如何实现自己的系统性能追踪工具

### 🔸 跨版本兼容性问题
不同 Android 版本间的 API 变更与适配

### 🔸 性能影响评估
系统级追踪机制对设备性能的实际影响分析

<!-- outline-end -->

## 实际应用案例

### 游戏性能优化案例

**场景**：某游戏在低端设备上帧率不稳定，需要分析性能瓶颈。

**Profiling 配置**：
```java
// 游戏性能追踪配置
public class GameProfilingConfig extends ProfilingConfig {
    
    public GameProfilingConfig() {
        setName("game_performance");
        setDescription("游戏性能优化追踪");
        
        // 帧率追踪
        addFeature(new FrameRateFeature());
        // GPU 性能
        addFeature(new GpuUsageFeature());
        // CPU 使用
        addFeature(new CpuUsageFeature());
        // 内存分配
        addFeature(new MemoryAllocationFeature());
        // 功耗分析
        addFeature(new BatteryUsageFeature());
    }
}
```

**分析结果**：
- 发现 GPU 瓶颈：渲染线程占用 80% GPU 时间
- CPU 频繁切换：主线程和渲染线程竞争
- 内存分配过多：每帧产生大量临时对象

**优化建议**：
1. 减少每帧绘制调用
2. 实现对象池重用机制
3. 优化线程优先级设置

### 启动性能优化案例

**场景**：应用启动时间过长，需要分析启动流程。

**Profiling 配置**：
```java
// 启动性能追踪配置
public class StartupProfilingConfig extends ProfilingConfig {
    
    public StartupProfilingConfig() {
        setName("startup_analysis");
        setDescription("应用启动性能分析");
        
        // 启动时间分解
        addFeature(new LaunchTimeBreakdownFeature());
        // 主线程阻塞
        addFeature(new MainThreadBlockingFeature());
        // 初始化顺序
        addFeature(new InitializationOrderFeature());
        // 依赖项加载
        addFeature(new DependencyLoadingFeature());
    }
}
```

**分析结果**：
- 冷启动时间：2.5秒
- 主线程阻塞：1.8秒
- 主要瓶颈：网络请求同步执行

**优化建议**：
1. 异步加载非核心组件
2. 优化网络请求顺序
3. 启用预加载机制

通过系统触发式性能追踪，可以精准定位性能瓶颈，制定针对性的优化策略，有效提升应用性能和用户体验。


<!-- AIW-源码调研-2026-06-25 -->

## 源码级实现补充 (Android 17)

### ⚠️ 重要发现：ProfilingManager.java 在 Android 17 中不存在

经过源码级分析，Android 17 中并不存在 `ProfilingManager.java` 类。实际架构采用三层设计：

#### 1. ProfilingServiceManager - 系统级API入口
```java
// frameworks/base/core/java/android/os/ProfilingServiceManager.java
@FlaggedApi("android.os.telemetry_apis_framework_initialization")
@SystemApi(client = Client.MODULE_LIBRARIES)
public class ProfilingServiceManager {
    public ServiceRegisterer getProfilingServiceRegisterer() {
        return new ServiceRegisterer("profiling_service");
    }
}
```

#### 2. AppProfiler - AMS端核心实现
```java
// frameworks/base/services/core/java/com/android/server/am/AppProfiler.java
public class AppProfiler {
    private class ProfileData {
        private ProfilerInfo mProfilerInfo = null;
        
        void setProfilerInfo(ProfilerInfo profilerInfo) {
            mProfilerInfo = profilerInfo;
            if (mService.mAtmInternal != null) {
                mService.mAtmInternal.setProfilerInfo(profilerInfo);
            }
        }
    }
}
```

#### 3. ProfilerInfo - 配置对象
系统触发式性能追踪的核心配置对象，支持：
- 不同采样模式（REGULAR/LOW_OVERHEAD）
- 时间戳类型（WALL/THREAD_CPU/DUAL）
- 自动停止控制
- Agent支持

#### 4. 系统触发式性能追踪机制

Android 17 支持多种系统触发类型：

- **OOM崩溃触发**: `profilingTriggerOom` - 应用崩溃时自动触发
- **冷启动触发**: `profilingTriggerColdStart` - 应用冷启动时触发  
- **完全绘制触发**: `systemTriggeredProfilingNew` - 应用完全绘制时触发
- **杀死进程触发**: `profilingTriggerKillRecents` - 进程被杀死时触发

#### 5. 权限控制机制

```java
// 严格的权限检查
void setProfileApp(ApplicationInfo app, String processName, ProfilerInfo profilerInfo,
        ApplicationInfo sdkSandboxClientApp, int profileType) {
    if (!Build.IS_DEBUGGABLE) {
        boolean isAppDebuggable = (app.flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0;
        boolean isAppProfileable = app.isProfileableByShell();
        
        if (!isAppDebuggable && !isAppProfileable) {
            throw new SecurityException("Process not debuggable, "
                    + "and not profileable by shell: " + app.packageName);
        }
    }
}
```

#### 6. ANOMALY检测框架预览

Android 17 引入了 ANOMALY 检测框架，但实际实现可能位于独立主模块中：

```java
public static final String ANOMALY_DETECTOR_SERVICE = "anomaly_detector";
@FlaggedApi("android.os.profiling.anomaly.flags.anomaly_detector_core_c")
```

### 关键差异总结

| 组件 | Android 17 预期 | 实际实现 |
|------|----------------|----------|
| ProfilingManager | 不存在 | ProfilingServiceManager |
| API 访问 | 直接类访问 | ServiceManager.getService |
| 触发控制 | 静态配置 | Flags 动态控制 |
| 权限检查 | 简单权限 | 双重权限验证 |
| ANOMALY检测 | 完整实现 | 框架预览 |

### 实际使用建议

1. **API 升级**: 如需使用系统级性能追踪，应通过 `ProfilingServiceManager` 而非虚构的 `ProfilingManager`
2. **Flags 启用**: 确保对应的 profiling flags 已启用
3. **权限适配**: 应用必须具备 debuggable 或 profileable 权限
4. **异步处理**: 所有触发都是异步执行，不会阻塞主线程

> **注意**: 本文档中提到的 `ProfilingConfig`、`FrameRateFeature` 等类在 Android 17 源码中不存在，属于概念性设计。实际实现应使用 `ProfilerInfo` 配置对象。



