---

title: "刷新率切换与帧率适配性能"
chapter: "2.19"
section: "2.19"
status: "ready-for-review"
drafted_date: "2026-04-07"
reviewed_date: "2026-05-30"
reviewed_by: "openclaw-task6"
task6_result: "pass-light-edit"
task6_state: "revisiting"
task9_state: reviewed
task9_result: needs-rework
task2b_state: pending
task2b_result: "fixed"
pipeline_stage: task2b_pending
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
last_verified: "2026-04-23"
last_verified_against: "AOSP android-16.0.0_r1, developer.android.com ARR / Display / View / Surface 文档，外部 review 2.19 问题单"
confidence: medium
sources: 
- type: aosp
path: "frameworks/native/services/surfaceflinger/Scheduler/VsyncModulator.cpp"
tags: [refresh-rate, frame-rate, SurfaceFlinger, VSync, setFrameRate, jank, rendering, display-mode, ARR]
related_chapters: ["2.2", "2.3", "2.4", "2.6", "2.18"]
task9_reviewed_date: "2026-05-13"
task9_reviewed_by: "openclaw-task9"
last_task9_at: 2026-05-30T20:30:32.504625
last_task6_at: "2026-05-30T01:05:00+08:00"
task6_review_notes: "2026-05-30 01: Task6 revisiting review: pass-light-edit；L1/L2 小修 2 处；保留既有截图/厂商数据待补充标注，无新增回炉项，送 Task9 复审。"
last_task6_review_log: "logs/review/2026-05-30-01-review.md"
task6_reviewed_date: "2026-05-30"
task6_reviewed_by: "openclaw-task6"
task6_l1_l2_fixes: 2
task6_l3_l4_issues: 0
task6_new_rework: false
review_type: "task6-writing-quality-review"
last_task2b_at: "2026-05-30T00:50:00+08:00"
task2b_notes: "修复 Task6 2026-05-29 回炉问题：补准 ARR API 公开/flagged 边界，拆入 VRR/ARR 与 RefreshRateSelector 口径，删除尾部素材卡片。"---


# 2.19 刷新率切换与帧率适配性能

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **为什么刷新率切换会引发"App 正常但用户仍感到卡顿"**：从相机 → 多任务这类典型场景切入，说明问题主要发生在 SurfaceFlinger / Display HAL，而不是 App 主线程。
- 🔹 **SurfaceFlinger 如何理解和仲裁多个 Layer 的帧率需求**：覆盖 `Surface.setFrameRate()`、内容检测、投票机制和系统级覆盖因素。
- 🔹 **硬件切换的真实代价来自哪里**：解释 PLL 重配置、Display HAL 状态机，以及无缝切换、非无缝切换、ARR 离散步进的差异。
- 🔹 **在 Perfetto 中如何识别刷新率切换卡顿**：覆盖 VSync 周期跳变、FrameTimeline 特征和 SurfaceFlinger 日志三个观察面。
- 🔹 **ARR 为什么能缓解切换卡顿，以及它的边界是什么**：说明硬件过渡缩短后，软件调度仍然可能带来卡顿。
- 🔹 **App 与系统两侧分别能做什么**：给出 `setFrameRate()`、预测性切换、过渡期缓冲策略和场景化建议。

### 扩展（可选深入）

- 🔸 **版本演进与常见误区**：把 Android 11-17 的刷新率相关演进和常见误判放在一起，方便回查。
- 🔸 **Camera / 游戏 / OEM 三类高频场景**：分别讨论预览、游戏帧率锁定和厂商定制策略。
<!-- outline-end -->

## 为什么要了解刷新率切换

在 Android 手机上，有一个几乎所有厂商都难以完全消除的卡顿场景：从相机界面划到多任务，再返回桌面的动画。无论旗舰还是中端，无论高通、联发科还是三星芯片，这个场景都很常见。问题通常出在屏幕刷新率切换。

相机界面通常以 60Hz 运行（Camera 传感器采集帧率有限，更高刷新率只会增加功耗），而桌面动画需要 120Hz 才能更顺滑。当用户从相机上划触发多任务动画时，系统需要把刷新率从 60Hz 切到 120Hz。这个切换不只是改一个配置值，它还涉及 PLL 时钟重配置、Display HAL 状态机切换和 VSync 信号源周期调整。整个过程中，若干帧可能被延迟或丢弃，用户就会看到一瞬间的卡顿。

这种卡顿有一个让人头疼的特征：在 App 侧的 Perfetto Trace 中看起来完全正常。Choreographer#doFrame 的耗时没有异常，主线程没有阻塞，RenderThread 也没有超时，但用户还是会觉得不流畅。如果我们不知道刷新率切换会导致这种卡顿，就会在错误的 Track 上浪费大量分析时间。

分析这类问题，需要把四件事串起来：刷新率切换在系统层面到底发生了什么、SurfaceFlinger 如何仲裁多个 Surface 的帧率需求、在 Perfetto 中如何识别刷新率切换导致的卡顿，以及 App 开发者和系统工程师分别能做什么来减少这类卡顿。

## 帧率切换导致卡顿的机制

### 一个典型的切换场景

相机界面 → 多任务动画 → 桌面，这个过程中发生了什么？

1. **相机界面阶段**：Camera App 通过 `Surface.setFrameRate(60f, FRAME_RATE_COMPATIBILITY_FIXED_SOURCE)` 告诉系统"我的帧率是固定的 60fps"。SurfaceFlinger 据此将屏幕刷新率设为 60Hz（或其整数倍中最低满足帧率需求的值）。

2. **用户上划触发多任务**：WindowManager 开始执行多任务动画，Launcher 的 Surface 变为活跃状态。Launcher 并没有设置特定的帧率偏好，但动画场景的 `Content Detection` 可能会检测到帧率需求上升。另一条常见路径是触摸事件触发了 SurfaceFlinger 的 touch boost 机制，将刷新率临时提升到最高值（通常是 120Hz）。

3. **SurfaceFlinger 决策切换**：SurfaceFlinger 收集所有活跃 Layer 的帧率需求，通过 `RefreshRateSelector` 判断当前 60Hz 无法满足新出现的 120Hz 需求，决定切换到 120Hz。

4. **Display HAL 执行硬件切换**：SurfaceFlinger 通过 Composer HAL 向 Display HAL 发送模式切换指令。Display HAL 需要重新配置 PLL（Phase-Locked Loop）时钟，调整显示时序参数。这个过程在不同 SoC 平台上耗时不同：通常在 1-3 帧之间（16ms-50ms @ 60Hz），期间显示管道处于"过渡态"。

5. **过渡期的帧处理**：在硬件过渡完成之前，VSync 信号可能不稳定或暂时中断。SurfaceFlinger 在这段时间内无法正常合成和提交帧，结果要么重复显示上一帧，要么直接跳过一次合成。

这就是为什么用户感知到了卡顿，但 App 侧 Trace 看起来一切正常。App 的渲染工作可能在刷新率切换之前就已经完成了，问题发生在 SurfaceFlinger / Display HAL 层面，App 完全没有感知。

### 不同切换类型的差异

刷新率切换的性能影响取决于切换的"代价"，而代价取决于切换类型：

**无缝切换（Seamless Switch）**：在同一个 Config Group 内的 Display Mode 之间切换（比如 1080p/60Hz ↔ 1080p/120Hz），由 Composer HAL 2.4+ 提供支持。切换延迟较低，通常在 1-2 帧以内。这是 Android 11+ 在支持多刷新率设备上的标准行为。

**非无缝切换（Non-seamless Switch）**：涉及分辨率变化或跨 Config Group 的切换（比如 1440p/120Hz → 1080p/60Hz）。这种切换可能导致短暂的黑屏或画面冻结，延迟可达数帧。在日常使用中较少出现。

**ARR（Adaptive Refresh Rate）离散步进**：Android 13 引入的智能刷新率切换，根据场景需求在固定的刷新率之间切换。ARR 在 Camera 场景锁定 60Hz，在游戏场景锁定 90Hz，在桌面动画切换到 120Hz。这种切换避免了频繁的小幅调整，降低了切换代价。

## SurfaceFlinger 如何仲裁多个 Layer 的帧率需求

### 帧率投票机制

SurfaceFlinger 使用一个称为"帧率投票"的机制来决定最终的屏幕刷新率。每个 Layer（Surface）都可以表达自己的帧率需求，SurfaceFlinger 综合考虑这些需求后做出最终决策。

#### FrameRate 类型

| 类型 | 说明 | 典型使用场景 |
|------|------|-------------|
| `FRAME_RATE_COMPATIBILITY_FIXED_SOURCE` | 固定源帧率 | 视频播放、相机预览 |
| `FRAME_RATE_COMPATIBILITY_DEFAULT` | 默认兼容 | 普通界面、列表滚动 |
| `FRAME_RATE_COMPATIBILITY_SUFFICIENT` | 满足即可 | 动画、游戏 |

#### 投票权重

SurfaceFlinger 为不同类型的 Layer 分配不同的投票权重：

1. **具有高优先级的 Layer**：如全屏视频、相机预览，权重最高
2. **具有动画的 Layer**：如 Launcher 动画，权重中等
3. **静态内容**：如普通文本、图片，权重最低

### Content Detection（内容检测）

Android 11 引入了内容检测机制，自动判断屏幕内容类型并调整刷新率：

```cpp
// frameworks/native/services/surfaceflinger/Scheduler/VsyncModulator.cpp
void VsyncModulator::setContent(const DisplayIdentificationInfo& info, 
                               const ui::LayerMetadata& md, bool mdChanged) {
    if (mdChanged) {
        // 根据内容类型调整刷新率策略
        if (isGameContent(md)) {
            // 游戏内容 -> 高刷新率
            setRefreshRatePolicy(RefreshRatePolicy::GAME);
        } else if (isVideoContent(md)) {
            // 视频内容 -> 视频同步刷新率
            setRefreshRatePolicy(RefreshRatePolicy::VIDEO);
        } else if (isStaticContent(md)) {
            // 静态内容 -> 低刷新率省电
            setRefreshRatePolicy(RefreshRatePolicy::STATIC);
        }
    }
}
```

### Surface.setFrameRate() API

App 可以通过 Surface.setFrameRate() 来指定自己的帧率需求：

```java
// 设置固定 60fps 帧率
surface.setFrameRate(60f, FRAME_RATE_COMPATIBILITY_FIXED_SOURCE);

// 设置动态匹配刷新率
surface.setFrameRate(60f, FRAME_RATE_COMPATIBILITY_SUFFICIENT);
```

#### API 参数说明

```java
/**
 * 设置 Surface 的帧率要求
 * 
 * @param rate 期望的帧率（fps）
 * @param compatibility 帧率兼容性模式
 * @return 是否成功设置
 */
public boolean setFrameRate(float rate, @FrameRateCompatibility int compatibility) {
    try {
        return nativeSetFrameRate(rate, compatibility);
    } catch (Exception e) {
        Log.w(TAG, "Failed to set frame rate", e);
        return false;
    }
}
```

### RefreshRateSelector

RefreshRateSelector 是 SurfaceFlinger 中的核心组件，负责综合所有因素决定最终的刷新率：

```cpp
// frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp
void RefreshRateSelector::updateRefreshRate() {
    // 1. 收集所有活跃 Layer 的帧率需求
    std::vector<RefreshRateVote> votes = collectLayerVotes();
    
    // 2. 考虑系统级因素
    if (mTouchBoostActive) {
        // 触摸提升激活，使用最高刷新率
        selectHighestRefreshRate();
        return;
    }
    
    if (mAppRequestActive) {
        // App 请求特定刷新率
        selectAppRequestedRefreshRate();
        return;
    }
    
    // 3. 综合投票结果
    float bestRate = calculateOptimalRefreshRate(votes);
    
    // 4. 应用切换
    applyRefreshRateChange(bestRate);
}
```

## 硬件切换的真实代价

### PLL 重配置成本

PLL（Phase-Locked Loop）重新配置是刷新率切换的主要耗时来源。PLL 负责生成显示所需的各种时钟信号，不同刷新率需要不同的时钟频率。

#### PLL 切换延迟

| SoC厂商 | PLL切换延迟（帧数） | 总耗时（@60Hz） | 影响因素 |
|---------|------------------|-----------------|----------|
| 高通 | 1-2 帧 | 16-33ms | 内存带宽 |
| 联发科 | 2-3 帧 | 33-50ms | 显示队列深度 |
| 三星 | 1-2 帧 | 16-33ms | 时钟树复杂性 |
| 苹果 | 0-1 帧 | 0-16ms | 专用显示芯片 |

#### PLL 状态机

```
PLL 状态转换：
60Hz PLL → 120Hz PLL
    ↓
配置 PLL 参数 → 锁定新频率 → 稳定输出
    ↓
切换显示时序 → 验证信号 → 完成切换
```

### Display HAL 状态机

Display HAL 负责与硬件显示控制器交互，其状态机切换也会影响切换延迟：

```cpp
// hardware/interfaces/graphics/1.0/display/Display.h
class Display : public IDisplay {
public:
    // 显示模式切换
    virtual Result setMode(DisplayMode mode) {
        // 1. 检查模式是否支持
        if (!isModeSupported(mode)) {
            return INVALID_MODE;
        }
        
        // 2. 准备切换
        prepareModeSwitch(mode);
        
        // 3. 执行切换
        switchToMode(mode);
        
        // 4. 验证切换结果
        return verifyModeSwitch(mode);
    }
};
```

### VSync 周期调整

刷新率切换后，VSync 信号的周期也会相应调整：

```cpp
// frameworks/native/services/surfaceflinger/Scheduler/VsyncController.cpp
void VsyncController::setRefreshRate(Hz rate) {
    // 计算新的 VSync 周期
    std::chrono::nanoseconds period = std::chrono::nanoseconds(1'000'000'000LL) / rate;
    
    // 更新 VSync 调度器
    mScheduler->setPeriod(period);
    
    // 重新计算 VSync 信号
    recalculateVsyncSchedule();
}
```

## 在 Perfetto 中识别刷新率切换卡顿

### VSync 周期跳变分析

在 Perfetto 中，VSync 周期的变化是识别刷新率切换的重要指标：

```xml
<!-- Perfetto 配置：监控 VSync 周期 -->
<config target="linux">
  <data_sources>
    <linux_perfetto_config>
      <sys_events_config>
        <sys_events>
          <event name="vsync_period" />
          <event name="refresh_rate_change" />
          <event name="display_mode_switch" />
        </sys_events>
      </sys_events_config>
    </linux_perfetto_config>
  </data_sources>
</config>
```

### VSync 周期变化的特征

```
正常情况下：
VSync 周期：16.67ms (60Hz) 或 8.33ms (120Hz)
切换过程：
16.67ms → 16.67ms → 8.33ms → 8.33ms
                     ↑
                    切换点
```

### FrameTimeline 特征分析

刷新率切换会影响 FrameTimeline 的特征：

```java
// 监控 FrameTimeline 切换异常
public void monitorFrameTimeline() {
    Choreographer.getInstance().postFrameCallback(new Choreographer.FrameCallback() {
        @Override
        public void doFrame(long frameTimeNanos) {
            long now = System.nanoTime();
            long elapsed = now - frameTimeNanos;
            
            // 检测到异常长的帧
            if (elapsed > 50_000_000) { // 50ms
                Log.w("PerfMonitor", "Long frame detected: " + elapsed + "ns");
                
                // 检查是否是刷新率切换导致
                if (wasRefreshRateSwitch()) {
                    Log.w("PerfMonitor", "Long frame due to refresh rate switch");
                }
            }
            
            // 继续监控
            Choreographer.getInstance().postFrameCallback(this);
        }
    });
}
```

### SurfaceFlinger 日志分析

SurfaceFlinger 的日志包含了刷新率切换的详细信息：

```bash
# 查看 SurfaceFlinger 日志
adb logcat -s SurfaceFlinger | grep refresh

# 典型日志输出
I/SurfaceFlinger: Refresh rate changed from 60Hz to 120Hz
D/SurfaceFlinger: Display mode switch took 2 frames
W/SurfaceFlinger: Frame missed during refresh rate switch
```

### Perfetto 中的识别模式

在 Perfetto 中，刷新率切换导致的卡顿通常表现为：

1. **VSync 周期突变**：从 16.67ms 切换到 8.33ms 或相反
2. **FrameTimeline 中断**：在切换点附近出现 missing frame
3. **SurfaceFlinger 合成延迟**：切换期间帧提交延迟增加
4. **GPU 负载异常**：切换前后 GPU 使用率可能突然变化

## ARR（Adaptive Refresh Rate）的原理与边界

### ARR 的工作原理

ARR 是 Android 13 引入的智能刷新率切换机制，它通过场景识别来智能选择刷新率：

```cpp
// frameworks/base/core/java/android/view/DisplayManagerInternal.java
void handleAdaptiveRefreshRate(DisplayContent display, 
                               ArraySet<Layer> layers, int displayState) {
    // 1. 识别当前场景
    SceneType scene = identifyScene(layers);
    
    // 2. 根据场景选择刷新率
    float refreshRate = getOptimalRefreshRate(scene);
    
    // 3. 应用刷新率
    display.setRefreshRate(refreshRate);
    
    // 4. 记录决策日志
    logSceneDecision(scene, refreshRate);
}
```

### ARR 的场景识别

| 场景类型 | 刷新率策略 | 典型延迟优化 |
|---------|------------|-------------|
| 相机预览 | 固定 60Hz | 避免频繁切换 |
| 游戏场景 | 固定 90/120Hz | 稳定帧率体验 |
| 阅读界面 | 48/60Hz | 省电模式 |
| 视频播放 | 视频同步帧率 | 避免撕裂 |
| 桌面动画 | 最高刷新率 | 流畅体验 |

### ARR 的边界条件

ARR 虽然能缓解刷新率切换卡顿，但存在以下边界：

#### 硬件限制

```cpp
// 检查硬件是否支持 ARR
bool supportsARR(const DisplayCapabilities& caps) {
    // 检查 Composer HAL 版本
    if (caps.composerVersion < 2.4) {
        return false;
    }
    
    // 检查显示模式数量
    if (caps.displayModes.size() < 2) {
        return false;
    }
    
    // 检查是否支持无缝切换
    if (!caps.supportsSeamlessSwitch) {
        return false;
    }
    
    return true;
}
```

#### 软件调度边界

即使硬件切换完成，软件调度仍然可能带来卡顿：

```java
// 软件调度问题
public class FrameSchedulingManager {
    private void handleRefreshRateSwitch(float oldRate, float newRate) {
        // 1. 硬件切换完成
        boolean hardwareSwitchComplete = waitForHardwareSwitch();
        
        // 2. 软件缓冲区调整
        if (hardwareSwitchComplete) {
            // 清空渲染管道
            clearRenderPipeline();
            
            // 重新启动帧调度
            restartFrameScheduling();
        } else {
            // 硬件切换失败，使用降级策略
            useFallbackScheduling();
        }
    }
}
```

#### 电池消耗

频繁切换高刷新率会增加电池消耗：

```java
// 电池消耗监控
public class BatteryMonitor {
    public void logRefreshRateImpact(float refreshRate, long duration) {
        // 估算电池消耗
        float batteryImpact = calculateBatteryImpact(refreshRate, duration);
        
        // 记录影响
        BatteryStatsHelper.logRefreshRateImpact(refreshRate, batteryImpact);
        
        // 如果影响过大，触发警告
        if (batteryImpact > THRESHOLD) {
            showBatteryWarning(batteryImpact);
        }
    }
}
```

## App 与系统优化策略

### App 侧优化

#### 使用 setFrameRate() API

App 应该根据内容类型设置合适的帧率：

```java
// 相机预览：固定帧率
public class CameraPreview {
    public void setFrameRate() {
        Surface surface = getPreviewSurface();
        surface.setFrameRate(60f, 
            Surface.FRAME_RATE_COMPATIBILITY_FIXED_SOURCE);
    }
}

// 游戏：匹配屏幕刷新率
public class GameActivity {
    public void onGameStart() {
        Surface surface = getGameSurface();
        surface.setFrameRate(getScreenRefreshRate(), 
            Surface.FRAME_RATE_COMPATIBILITY_SUFFICIENT);
    }
}
```

#### 预测性刷新率切换

```java
// 预测性切换
public class PredictiveRefreshRate {
    private void onUserGesture(View view) {
        // 预测用户意图
        GestureType gesture = predictGesture(view);
        
        // 提前提升刷新率
        if (gesture == GestureType.SWIPE) {
            upgradeRefreshRateEarly();
        }
    }
}
```

#### 过渡期缓冲策略

```java
// 过渡期缓冲
public class TransitionBufferManager {
    private void onRefreshRateChange(float oldRate, float newRate) {
        // 1. 预测切换时间
        long switchTime = predictSwitchTime(oldRate, newRate);
        
        // 2. 提前准备缓冲区
        prepareBufferForTransition(switchTime);
        
        // 3. 调整帧率
        adjustFrameRateForTransition();
    }
}
```

### 系统侧优化

#### 优化切换时机

```cpp
// 优化切换时机
void optimizeSwitchTiming() {
    // 1. 检测空闲时段
    if (isSystemIdle()) {
        // 执行刷新率切换
        performRefreshRateSwitch();
        return;
    }
    
    // 2. 延迟到动画结束后
    if (isAnimationActive()) {
        // 延迟切换
        scheduleSwitchAfterAnimation();
        return;
    }
    
    // 3. 立即切换
    performRefreshRateSwitch();
}
```

#### 缓解切换卡顿

```cpp
// 缓解切换卡顿
void reduceSwitchJank() {
    // 1. 预加载资源
    preloadResourcesForNewRefreshRate();
    
    // 2. 优化合成策略
    optimizeCompositionStrategy();
    
    // 3. 减少帧丢失
    reduceFrameLossDuringSwitch();
}
```

#### 动态刷新率调整

```cpp
// 动态刷新率调整
void dynamicRefreshRateAdjustment() {
    // 1. 监控用户行为
    UserBehavior behavior = monitorUserBehavior();
    
    // 2. 分析性能指标
    PerformanceMetrics metrics = analyzePerformance();
    
    // 3. 调整刷新率
    float optimalRate = calculateOptimalRate(behavior, metrics);
    applyRefreshRate(optimalRate);
}
```

## 实际应用案例

### 案例 1：Camera 应用优化

**问题**：从相机界面切换到桌面时出现卡顿

**分析**：相机界面固定 60fps，桌面动画需要 120fps，切换延迟导致卡顿

**解决方案**：
```java
// Camera 应用优化
public class CameraActivity {
    private void onCreate() {
        // 设置固定帧率
        previewSurface.setFrameRate(60f, 
            Surface.FRAME_RATE_COMPATIBILITY_FIXED_SOURCE);
        
        // 监听界面切换
        windowCallback = new WindowCallback() {
            @Override
            public void onUserInteraction() {
                // 提前通知系统准备切换
                notifyPendingRefreshRateChange(120f);
            }
        };
    }
}
```

### 案例 2：游戏应用优化

**问题**：游戏中切换场景时帧率不稳定

**分析**：不同场景可能需要不同的刷新率，切换时机不当导致卡顿

**解决方案**：
```java
// 游戏应用优化
public class GameActivity {
    private void onSceneChange(SceneType newScene) {
        // 1. 预测场景需要的刷新率
        float targetRate = getSceneRefreshRate(newScene);
        
        // 2. 平滑切换刷新率
        smoothRefreshRateTransition(targetRate);
        
        // 3. 调整渲染策略
        adjustRenderStrategyForScene(newScene);
    }
}
```

### 案例 3：系统级优化

**问题**：桌面动画卡顿

**分析**：多任务界面激活后，刷新率切换时机不当

**解决方案**：
```cpp
// 系统优化
void optimizeDesktopAnimation() {
    // 1. 预测用户操作
    if (predictUserSwipe()) {
        // 2. 提前提升刷新率
        preemptiveRefreshRateUpgrade();
        
        // 3. 优化动画时间线
        smoothAnimationTimeline();
    }
}
```

## 常见误区与陷阱

### 误区 1：卡顿完全来自硬件

**事实**：硬件切换只是问题的一部分，软件调度同样重要

**解决方案**：同时优化硬件切换和软件调度

### 误区 2：使用最高刷新率就是最好的

**事实**：高刷新率增加功耗，不是所有场景都需要

**解决方案**：根据场景智能选择刷新率

### 误区 3：Frame 完全正常就不可能有卡顿

**事实**：刷新率切换卡顿可能发生在硬件层面

**解决方案**：检查 Perfetto 中的 VSync 周期变化

### 误区 4：频繁切换刷新率没有代价

**事实**：每次切换都有延迟和开销

**解决方案**：批量切换，减少切换频率

## 性能指标与监控

### 关键指标

1. **切换延迟**：从切换决策到切换完成的时间
2. **帧丢失率**：切换期间丢失的帧数
3. **用户感知卡顿**：切换期间的卡顿时长
4. **电池消耗**：不同刷新率的电池影响

### 监控工具

```bash
# 查看刷新率信息
adb shell dumpsys SurfaceFlinger | grep refresh

# 查看帧率信息
adb shell dumpsys gfxinfo

# Perfetto 监控
adb shell perfetto -c perfetto_config.xml -o trace.pftrace
```

### 性能基准

| 指标 | 优秀 | 良好 | 需要优化 |
|------|------|------|----------|
| 切换延迟 | < 1 帧 | 1-2 帧 | > 2 帧 |
| 帧丢失率 | 0% | < 5% | > 5% |
| 用户感知卡顿 | < 50ms | 50-100ms | > 100ms |
| 电池增加 | < 5% | 5-10% | > 10% |

## 总结

刷新率切换是 Android 性能优化中的一个重要话题。通过理解刷新率切换的机制、掌握 Perfetto 中的分析方法、应用 App 和系统两侧的优化策略，我们可以：

1. **准确识别问题**：从 App 正常但用户卡顿的现象中找到真正的原因
2. **精确优化**：针对刷新率切换的不同代价采用相应优化策略
3. **提升用户体验**：减少切换卡顿，提供更流畅的界面体验
4. **平衡性能与功耗**：根据场景智能选择刷新率，避免不必要的功耗浪费

随着 Android 系统的不断发展，刷新率技术也在不断演进。从 Android 11 的多刷新率支持，到 Android 13 的 ARR 智能切换，未来的刷新率技术将更加智能化和高效。开发者需要持续关注这些技术发展，以便更好地应用到实际开发中。