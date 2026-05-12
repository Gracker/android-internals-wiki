---
source: "高爷手动补充"
date: "2026-04-06"
type: "expert-insight"
target_chapters: ["7.1", "7.2"]
tags: [jank, refresh-rate-switch, step-jitter, vsync-calculation, smoothness]
quality: 20
mapped_chapters: ["7.1", "7.2"]
confidence: high
---

# 高爷卡顿知识补充（2026-04-06）

## 素材 1：帧率切换卡顿

**目标章节**：7.2 卡顿原因体系 → 系统级原因（新增小节）

**内容**：

帧率切换时会卡顿，一个典型的例子：相机界面多任务返回桌面动画，几乎每个 Android 手机都必卡。原因是相机界面一般会设置到 60Hz，而多任务动画一般是 120Hz，这个切换的过程中就会出现明显用户可感知的卡顿。

**技术要点**：
- 不同 Surface/Winddow 可以有不同的 preferred refresh rate（通过 `setFrameRate()` API 设置）
- 当 Activity 切换或系统动画涉及多个不同帧率的 Surface 同时显示时，SurfaceFlinger 需要在一个 VSync 周期内合成不同帧率的内容
- 帧率切换过程中，Display HAL 可能需要重新配置显示参数（PLL 时钟、时序参数），这个过渡期会产生若干帧的延迟
- 在 Perfetto Trace 中表现为：Expected Timeline 出现 VSync 周期跳变，Actual Timeline 与 Expected Timeline 之间出现明显不对齐
- 这类卡顿的瓶颈在 SurfaceFlinger / Display HAL 层面，App 侧 Trace 看起来完全正常

**补充方向**：
- SurfaceFlinger 如何处理多刷新率 Surface 的合成（refresh rate selection 策略）
- Display HAL 帧率切换的硬件过渡时间
- `WindowManager.setDisplayRefreshRateOverride()` 等相关 API
- 在 Perfetto 中如何识别这类卡顿（FrameTimeline 特征）

---

## 素材 2：步幅波动卡顿（Step-Size Jitter）

**目标章节**：7.1 卡顿的定义与分类 → 用户感知与技术指标的映射（新增小节）

**内容**：

步幅波动太大导致的卡顿。这种从 Trace 上来看是没有掉帧的，但是从现象上来看卡卡的。其原因是每一帧的移动距离不符合用户的预期。比如多任务上划回桌面的时候，如果滑动速度太快，则会出现前期窗口动画变化速度过快，导致前一帧和后一帧的画面大小出现明显的变化，感官上就会出现卡顿。

**技术要点**：
- 这是一种「无掉帧卡顿」——FrameTimeline 不会标红，所有帧都在预算时间内完成
- 问题的本质不是帧率，而是「每帧位移量（step size）」的不均匀
- 用户在连续动画中建立的是对运动轨迹的预期，而不是对帧间隔的预期
- 当相邻帧之间的位移差异过大时，视觉系统会感知到「不连贯」——即使帧率是稳定的 120fps
- 这与「帧率稳定性」相关但不同：帧率稳定 ≠ 步幅均匀
- 可能的原因包括：动画插值算法选择不当、物理模拟的时间步长不稳定、手势速度到动画速度的映射函数有突变

**补充方向**：
- 动画插值（interpolator）对步幅均匀性的影响
- OverScroller / SpringAnimation 等动画引擎的位移计算
- 如何在 Perfetto 中量化步幅波动（非标准指标，可能需要自定义分析）
- 与现有「视觉惯性与帧率稳定性」内容的衔接

---

## 素材 3：列表滑动的 VSync 时间计算问题

**目标章节**：7.2 卡顿原因体系 → 动画与手势场景的 Jank 特征（填充现有 [待补充] 区域）

**内容**：

Android 列表滑动，计算这一帧的距离的时候，并不是严格使用 VSync 的时间，而是使用的 VSync 时间的 ms（取整后的毫秒值），这就会导致时间出现波动。比如 VSync 的时间间隔是一定的，但是到了计算当前位置的时候，就不敢保证与上一个的间隔是均匀的。

**技术要点**：
- RecyclerView 的 fling/slide 依赖 OverScroller 计算 scroll position
- OverScroller 使用的是基于时间的物理模型（速度、加速度、减速度）
- 时间参数的精度损失（VSync 纳秒时间戳 → 毫秒级计算）会导致相邻帧的 delta time 出现 ±1ms 的波动
- 在 120Hz 下（VSync 周期 8.33ms），±1ms 的波动意味着约 12% 的帧间时间差异
- 这种微小的时间波动传递到位移计算后，会导致列表每帧滚动的像素数不均匀
- 用户在快速滑动时感知到「一顿一顿」的效果，但 Perfetto FrameTimeline 不会标记为 Jank

**补充方向**：
- AOSP 中 OverScroller / Scroller 的时间精度处理源码分析
- `Choreographer.getFrameTimeNanos()` 到动画引擎之间的精度损失链路
- 是否有厂商对此做过优化（如直接使用纳秒时间戳计算）
- 与素材 2（步幅波动）的关联：两者都是「无掉帧卡顿」的不同表现
