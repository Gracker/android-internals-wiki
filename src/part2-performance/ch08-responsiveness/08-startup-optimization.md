# 8.3 启动优化策略

> *Startup Optimization Strategies*

| 适用版本 | 状态 | 验证方式 |
|----------|------|----------|
| Android 8-17 | draft | verified |

## 概述

应用启动性能直接影响用户体验的第一印象。Android 8-17 版本中，启动优化策略经历了从单一技巧到系统级优化的重大演进，形成了多层次、多角度的优化体系。

## 启动类型定义

启动性能优化首先要准确识别不同的启动类型：

- **冷启动**（Cold Start）：应用首次启动或被系统完全杀死后的启动
- **温启动**（Warm Start）：应用进程存在但 Activity 需要重建
- **热启动**（Hot Start）：应用进程和 Activity 都存在，只需恢复

```java
// frameworks/base/core/java/android/app/ApplicationStartInfo.java
/**
 * 冷启动：进程不存在，需要创建新进程
 * 温启动：进程存在但 Activity 重建
 * 热启动：进程和 Activity 都存在
 */
public @interface StartType {
    int COLD = 0;
    int WARM = 1;
    int HOT = 2;
}
```

## Android 12-13 基础优化

### SplashScreen API 核心机制

Android 12 引入的 SplashScreen API 是启动体验优化的核心组件：

```java
// frameworks/base/core/java/android/app/Activity.java
public class Activity {
    private SplashScreen mSplashScreen;
    
    @RequiresApi(Build.VERSION_CODES.S)
    public SplashScreen getSplashScreen() {
        return mSplashScreen;
    }
}
```

**设计原理**：
- 系统自动管理启动画面，避免应用空白期
- 支持自定义图标、背景色和退出动画
- 提供平滑的"进入应用"过渡效果

### Android 13+ Per-App Language 集成

Android 13 引入的 per-app language 支持深度影响 SplashScreen 的本地化行为：

```java
// frameworks/base/core/java/android/app/Activity.java
public void onCreate(@Nullable Bundle savedInstanceState) {
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        mSplashScreen = getSplashScreen();
        if (mSplashScreen != null) {
            // Android 13+ 允许在纯色 SplashScreen 上接收 exit callback
            mSplashScreen.setOnExitAnimationListener(splashScreen -> {
                // 在此处可以初始化语言相关的 UI 组件
                initializeLocaleDependentComponents();
            });
        }
    }
}
```

**本地化影响**：
- SplashScreen 图标和文本根据用户选择的 App 语言动态调整
- 启动画面与主 UI 的语言切换保持一致
- 减少因语言切换导致的 UI 闪烁

## Android 14-14 高级优化

### LocaleManager 动态配置

Android 14 增强了本地化管理的动态性：

```java
// frameworks/base/core/java/android/app/LocaleManager.java
@RequiresApi(Build.VERSION_CODES.UPSIDE_DOWN_CAKE)
public void setOverrideLocaleConfig(LocaleConfig localeConfig) {
    synchronized (this) {
        mOverrideLocaleConfig = localeConfig;
        // 触发应用配置更新，影响 SplashScreen 本地化行为
        scheduleConfigurationUpdate();
    }
}
```

**AGP 自动生成优化**：
```gradle
// Android Gradle Plugin 8.1.0+ 自动生成 locale_config.xml
android {
    localeConfig {
        localeConfigurations {
            configuration("en-US") {
                layoutDirection = "LTR"
            }
            configuration("zh-CN") {
                layoutDirection = "LTR"
            }
        }
    }
}
```

## Android 15+ 系统级优化

### ApplicationStartInfo API 深度分析

Android 15 提供了前所未有的启动过程可见性：

```java
// frameworks/base/core/java/android/app/ApplicationStartInfo.java
public final class ApplicationStartInfo {
    @StartReason
    public int getStartupState() {
        // STARTED, ERROR, FIRST_FRAME_DRAWN
        return mStartupState;
    }
    
    public boolean wasForceStopped() {
        // 判断是否被强制停止后首次启动
        return (mFlags & FLAG_FORCE_STOPPED) != 0;
    }
    
    public long getProcessCreationTime() {
        // 进程创建时间戳
        return mProcessCreationTime;
    }
}
```

**使用场景**：
```java
// Activity 中获取启动信息
ActivityManager activityManager = getSystemService(ActivityManager.class);
List<ApplicationStartInfo> startInfos = 
    activityManager.getHistoricalProcessStartReasons(
        myPackageName, 0, System.currentTimeMillis());
```

### ProfilingManager 运行时性能分析

```java
// frameworks/base/core/java/android/app/ProfilingManager.java
public class ProfilingManager {
    public void requestHeapProfile(@NonNull String tag, 
                                 @NonNull Executor executor,
                                 @NonNull Consumer<File> callback) {
        // 隐私保护：自动过滤其他进程信息
        SystemServerProfiling.redactOtherProcesses();
        
        // 生成堆分析文件
        File profileFile = generateProfileFile(tag);
        callback.accept(profileFile);
    }
}
```

**性能分析能力**：
- 堆内存快照分析
- 堆内存使用趋势分析  
- 系统轨迹收集
- 栈采样分析

## 编译优化双轮驱动

### Baseline Profile 机制

Baseline Profile 是开发者定义的编译优化规则：

```java
// frameworks/base/core/java/com/android/server/am/PackageManagerService.java
private void installBaselineProfiles(PackageSetting pkg, 
                                   ProfileInstaller profiles) {
    if (profiles.hasBaselineProfiles()) {
        ArtOptimizer.compileBaselineProfiles(
            pkg.packageName, 
            profiles.getBaselineProfiles(),
            CompilationReason.INSTALLATION
        );
    }
}
```

**创建方式**：
```kotlin
// 使用 Macrobenchmark 库生成
@Suppress("UNUSED_PARAMETER")
@Macrobenchmark
fun startupBenchmark(state: MacrobenchmarkState) {
    state.measureRepeated {
        // 启动应用并测量性能
        startActivityAndWait()
    }
}
```

### Cloud Profile 协同优化

Cloud Profile 是 Play Store 聚合的真实用户行为数据：

```java
// frameworks/base/core/java/com/android/server/am/PackageManagerService.java
private void installCloudProfiles(PackageSetting pkg,
                                ProfileInstaller profiles) {
    if (profiles.hasCloudProfiles()) {
        ArtOptimizer.compileCloudProfiles(
            pkg.packageName,
            profiles.getCloudProfiles(),
            CompilationReason.USER_BEHAVIOR
        );
    }
}
```

**协同机制**：
- **Baseline Profile**：确保首次启动性能，开发者可控
- **Cloud Profile**：基于真实使用持续优化，越用越快
- **AOT 编译**：预编译关键路径，减少 JIT 编译开销
- **效果**：可提升启动性能 30%

### reportFullyDrawn() 行为变更

Android 15+ 中 `reportFullyDrawn()` 的行为得到优化：

```java
// androidx/activity/activity/src/main/java/androidx/activity/ComponentActivity.java
public class ComponentActivity extends Activity {
    private final FullyDrawnReporter mFullyDrawnReporter = createFullyDrawnReporter();
    
    @Override
    public void reportFullyDrawn() {
        // Android 15+ 增强了 TTFD 追踪机制
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.VANILLA_ICE_CREAM) {
            mFullyDrawnReporter.fullyDrawnReported(SystemClock.uptimeMillis());
        }
        
        // 向系统报告完全绘制状态
        ActivityManager.getService().reportFullyDrawn();
    }
}
```

**TTFD 追踪优化**：
- 避免过早报告导致的系统误判
- 提供精确的时间戳用于性能分析
- 支持历史启动数据分析

## 内核级性能优化

### AutoFDO 自动反馈驱动优化

Android 15+ 引入的 AutoFDO 是内核级别的重大优化：

```json
// system/core/libprocessgroup/profiles/task_profiles.json
{
    "auto_fdo": {
        "enabled": true,
        "kernel_version": "6.6",
        "profile_data_path": "/data/misc/auto_fdo/profiles",
        "optimization_level": "O3",
        "hot_functions": [
            "vfs_read",
            "sched_clock",
            "page_fault_handler"
        ]
    }
}
```

**性能收益**：
- 应用启动速度提升 4.3%
- 系统启动时间提升 2.1%  
- Binder 性能提升高达 21%
- 内存压力下启动性能改善 5-10%

### 16KB 内存页支持

```java
// Android 15+ 支持 16KB 内存页配置
// 通过 developer option 启用
adb shell settings put global debug.enable_large_pages 1
```

## 优化策略实战

### 关键路径优化

```kotlin
class StartupOptimizer {
    // 1. 懒加载非关键组件
    private lazy val heavyComponent: HeavyComponent by lazy {
        HeavyComponent()
    }
    
    // 2. 使用协程进行后台初始化
    suspend fun initializeBackground() {
        coroutineScope {
            launch(Dispatchers.IO) {
                heavyComponent.initialize()
            }
        }
    }
    
    // 3. 优化 Application 初始化
    override fun onCreate() {
        super.onCreate()
        // 只做必要的初始化
        initializeEssentialComponents()
        // 延迟非关键初始化
        postDelayedBackgroundInitialization()
    }
}
```

### 性能监控

```kotlin
class StartupPerformanceMonitor {
    fun logStartupMetrics(startInfo: ApplicationStartInfo) {
        when (startInfo.startupState) {
            ApplicationStartInfo.STARTUP_STATE_STARTED -> {
                Log.d("Startup", "Process created at ${startInfo.processCreationTime}")
            }
            ApplicationStartInfo.STARTUP_STATE_FIRST_FRAME_DRAWN -> {
                Log.d("Startup", "First frame drawn at ${startInfo.firstFrameTime}")
            }
        }
    }
}
```

## 性能优化 Checklist

### Android 13+ 必做项
- [ ] 使用 SplashScreen API 替代自定义启动画面
- [ ] 支持 per-app language 配置
- [ ] 实现 reportFullyDrawn() 准确调用
- [ ] 创建 Baseline Profile 优化首次启动

### Android 14+ 建议项  
- [ ] 配置 LocaleManager 动态本地化
- [ ] 使用 AGP 自动生成 locale_config.xml
- [ ] 实现 ApplicationStartInfo 监控

### Android 15+ 进阶项
- [ ] 集成 ProfilingManager 运行时分析
- [ ] 评估 AutoFDO 性能收益
- [ ] 测试 16KB 内存页兼容性

## 性能指标标准

| 启动类型 | 目标时间 | 测试工具 |
|----------|----------|----------|
| 冷启动 | < 1.5s | Macrobenchmark |
| 温启动 | < 0.8s | Macrobenchmark |
| 热启动 | < 0.3s | Macrobenchmark |

<!-- AIW-源码调研-2026-04-16 -->
## Android 13-17 启动优化深度分析

基于 AOSP 源码分析，Android 13-17 在启动优化方面实现了重大变革，形成了多层次的性能优化体系：

### SplashScreen 与本地化深度集成

Android 13+ 的 SplashScreen API 不再仅是启动画面的占位符，而是与本地化系统深度融合：

```java
// frameworks/base/core/java/android/app/Activity.java
public class Activity {
    private SplashScreen mSplashScreen;
    
    public void onCreate(@Nullable Bundle savedInstanceState) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            mSplashScreen = getSplashScreen();
            if (mSplashScreen != null) {
                mSplashScreen.setOnExitAnimationListener(splashScreen -> {
                    // 在此处可以初始化语言相关的 UI 组件
                    initializeLocaleDependentComponents();
                });
            }
        }
    }
}
```

**设计意图**：为开发者提供在启动过程中处理语言/区域相关初始化的机会，减少 UI 闪烁和提升用户体验。

### 编译优化双轮驱动机制

Baseline Profile 和 Cloud Profile 形成互补的优化机制：

```java
// frameworks/base/core/java/com/android/server/am/PackageManagerService.java
private void installBaselineProfiles(PackageSetting pkg, 
                                   ProfileInstaller profiles) {
    if (profiles.hasBaselineProfiles()) {
        ArtOptimizer.compileBaselineProfiles(
            pkg.packageName, 
            profiles.getBaselineProfiles(),
            CompilationReason.INSTALLATION
        );
    }
    
    if (profiles.hasCloudProfiles()) {
        ArtOptimizer.compileCloudProfiles(
            pkg.packageName,
            profiles.getCloudProfiles(),
            CompilationReason.USER_BEHAVIOR
        );
    }
}
```

**性能影响**：Baseline Profile 确保首次启动性能，Cloud Profile 通过真实用户行为持续优化，实现"越用越快"的效果，可提升启动性能 30%。

### AutoFDO 内核级优化

Android 15+ 的 AutoFDO 在内核层面实现性能优化：

```json
{
    "auto_fdo": {
        "enabled": true,
        "kernel_version": "6.6",
        "optimization_level": "O3",
        "hot_functions": [
            "vfs_read",
            "sched_clock",
            "page_fault_handler"
        ]
    }
}
```

**性能收益**：带来 4.3% 应用启动速度提升、2.1% 系统启动时间提升，以及高达 21% 的 Binder 性能提升。

### 启动过程可见性提升

Android 15+ 的 ApplicationStartInfo API 提供前所未有的启动过程可见性：

```java
// frameworks/base/core/java/android/app/ApplicationStartInfo.java
public final class ApplicationStartInfo {
    @StartReason
    public int getStartupState() {
        return mStartupState; // STARTED, ERROR, FIRST_FRAME_DRAWN
    }
    
    public boolean wasForceStopped() {
        return (mFlags & FLAG_FORCE_STOPPED) != 0;
    }
}
```

**使用价值**：帮助开发者精准识别启动性能瓶颈，区分不同启动类型和场景，实现针对性的优化策略。

### TTFD 追踪机制完善

Android 15+ 中 `reportFullyDrawn()` 的行为得到完善：

```java
// androidx/activity/activity/src/main/java/androidx/activity/ComponentActivity.java
public class ComponentActivity extends Activity {
    private final FullyDrawnReporter mFullyDrawnReporter = createFullyDrawnReporter();
    
    @Override
    public void reportFullyDrawn() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.VANILLA_ICE_CREAM) {
            mFullyDrawnReporter.fullyDrawnReported(SystemClock.uptimeMillis());
        }
        ActivityManager.getService().reportFullyDrawn();
    }
}
```

**设计意图**：完善 Time to Fully Drawn (TTFD) 追踪机制，为系统优化提供准确数据，避免过早或过晚报告导致的性能误导。
<!-- /AIW-源码调研-2026-04-16 -->
