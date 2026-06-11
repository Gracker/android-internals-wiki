---


title: "优化策略"
section: "7.5"
chapter: "7.5"
status: finalized
drafted_by: "openclaw-task2a"
reviewed_date: "2026-05-24"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
applicable_versions: "Android 5.0 (API 21) - Android 16 (API 36)"
last_verified: "2026-04-20"
last_verified_against: "AOSP android-16.0.0_r1, Android 官方文档, AndroidX RecyclerView release notes"
confidence: high
sources:
  - type: blog
    path: "obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md"
  - type: official
    path: "developer.android.com/topic/performance/recycler-view"
  - type: official
    path: "developer.android.com/develop/ui/compose/performance"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/RenderEffect"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/RenderEffect.java"
  - type: aosp
    path: "frameworks/base/libs/hwui/jni/RenderEffect.cpp"
  - type: aosp
    path: "frameworks/base/libs/hwui/RenderProperties.h"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/RenderNode.java"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/recyclerview"
  - type: official
    path: "developer.android.com/develop/ui/views/layout/constraint-layout"
  - type: aosp
    path: "frameworks/base/core/java/android/view/ViewStub.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/View.java (LAYER_TYPE_HARDWARE)"
tags:
  - android
  - smoothness
  - jank-optimization
  - recyclerview
  - compose-performance
  - layout-optimization
polish_count: 1
polish_date: "2026-04-09"
polish_by: "task2b-polish"
rework_count: 3
rework_date: "2026-04-30"
rework_by: "task2b-rework"
pipeline_stage: ready-to-publish
task6_state: "reviewed"
last_task6_audit: "2026-05-22"
task9_state: reviewed
task9_result: auto-fixed
task2b_state: fixed
task2b_result: fixed
last_task2b_at: "2026-06-04T10:50:00+08:00"
last_task2b_at: "2026-05-24T11:16:52+08:00"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-05"
last_task9_at: "2026-06-05T18:32:25+08:00"
task9_review_notes: "2026-06-05 Task9 深度复审 AUTO-FIX: 修复 2.x/1.4 跨章 Markdown 链接；RenderThread PRIORITY_DISPLAY 锚点改为 AOSP android-16.0.0_r1 frameworks/base/libs/hwui/renderthread/RenderThread.cpp:394-396。回到 Task6 复审。"
last_task9_audit: "2026-05-23"
last_task9_audit_log: "logs/deep-review/2026-05-23-06-audit.md"
last_task9_review_log: "logs/deep-review/2026-06-05-18-deep-review.md"
last_task6_at: "2026-05-24T13:10:00+08:00"
task6_reviewed_date: "2026-05-24"
last_task6_review_log: "logs/review/2026-05-24-13-review.md"
task6_review_notes: "2026-05-24 13:10 Task6 复审：pass-light-edit。L1/L2 小修 9 处，清理夸张标题/网络化表达并将参考资料移至末尾；既有 Task9 P0/P1/P2 pending 队列继续由 Task2B 处理，Task6 未新增回炉。"
p0: 1
p1: 0
p2: 4
last_task9_autofix_at: "2026-06-05"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-05
---

# 优化策略

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 布局优化：减少层级、ConstraintLayout、ViewStub 延迟加载
- 🔹 RecyclerView 优化：预创建 ViewHolder、DiffUtil、SnapHelper 性能考量
- 🔹 渲染优化：减少 overdraw、合理使用 Hardware Layer、Canvas 操作简化
- 🔹 线程优化：耗时操作异步化、Binder 调用优化、合理的线程池配置
- 🔹 Compose 性能优化：减少重组（Recomposition）、stable 标记、remember/derivedStateOf

### 扩展（可选深入）

- 🔸 RenderEffect / Blur 等特效的性能考量
- 🔸 预渲染（Prefetch）与预计算策略
<!-- outline-end -->

## 为什么要单独讲优化策略

在前面的章节里，我们走完了卡顿的定义（7.1）、原因体系（7.2）、分析方法论（7.3）和典型场景分析（7.4）。知道了"卡顿是什么"和"卡顿怎么查"，这一章回答：**查到原因之后，怎么改？**

同样是"主线程耗时"，有的是布局层级太深导致 measure 反复执行，有的是 RecyclerView 的 onBindViewHolder 里做了不该做的事，有的是一个看似无害的 Binder 调用正好赶上了系统服务繁忙。每一种原因对应的优化策略都不同，用错方法不仅白费力气，还可能引入新问题。

这一章按优化的"作用域"来组织：布局结构 → 列表控件 → 渲染管线 → 线程模型 → Compose。每一条策略都回答三个问题：**为什么有效**、**在 Trace 中怎么验证效果**、**容易踩什么坑**。



## 布局优化：减少层级、ConstraintLayout、ViewStub 延迟加载

### 为什么布局层级会影响性能

Android 的渲染管线在每一帧都需要执行 measure → layout → draw 三个阶段（参见 [2.4 Choreographer 与渲染流水线](../../part1-fundamentals/ch02-rendering/04-choreographer.md)）。measure 和 layout 阶段的耗时与 View 树的深度直接相关——measure 是递归的，父 ViewGroup 需要先遍历所有子 View 确定尺寸，然后才能确定自己的尺寸。布局嵌套越深，递归层数越多。

某些 ViewGroup 还需要**多次测量**。`RelativeLayout` 需要先做一遍测量确定各子 View 之间的依赖关系，然后再做一遍确定最终位置。`LinearLayout` 使用 `layout_weight` 时也有类似问题。

[已验证: 官方文档, developer.android.com/develop/ui/views/layout/constraint-layout — ConstraintLayout 通过消除嵌套来减少 measure/layout pass 次数]

### ConstraintLayout：扁平化布局的主要手段

`ConstraintLayout` 的设计目标是**用一层布局替代多层嵌套**。它通过约束系统让每个子 View 直接描述自己相对于其他 View 或父容器的位置关系。

Google 官方基准测试表明，在同等布局效果下，ConstraintLayout 的 measure 阶段比多层嵌套的 RelativeLayout 方案快约 40%。原理是 ConstraintLayout 内部用优化过的约束求解器，只需要一趟遍历就能确定所有子 View 的位置和大小。

[已验证: Google Developers Blog, ConstraintLayout 性能基准测试 — 在复杂布局场景下比 RelativeLayout 快约 40%]

**使用建议：** 对于复杂布局优先用 ConstraintLayout 替代嵌套；在 RecyclerView 的 item 布局中尤其重要——item 布局会被 inflate 和 measure 成百上千次，每减少一层嵌套都会被放大。

### ViewStub：按需加载的占位机制

`ViewStub` 是一个零大小、不可见、不参与 layout 的占位符。当调用 `inflate()` 或设置 `VISIBLE` 时，它将自己从 View 树中替换为实际的布局。inflate 之前几乎零性能开销；inflate 之后 ViewStub 对象被释放。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/view/ViewStub.java — inflate() 通过 replaceViewInLayout 替换自身]

**注意事项：** ViewStub 只能 inflate 一次；不支持 `<merge>` 标签；只适合"大概率不显示"的 UI 元素。

[已验证: 来源见 2026-03-07_wechat_Android深入卡顿分析与实践.md §ViewStub按需加载]

### 减少层级的其他手段

除了 ConstraintLayout 和 ViewStub，还有几个手段能有效降低布局层级。

`<merge>` 标签是最容易被忽视的一个。当一个布局通过 `<include>` 被嵌入到另一个布局中时，如果被 include 的布局的根元素是 `<merge>`，LayoutInflater 会跳过根节点的创建，直接将子 View 添加到父容器中——不会额外产生一层 ViewGroup 嵌套。在 TabHost、自定义标题栏等场景中，`<merge>` 能省下一到两层不必要的 FrameLayout 或 LinearLayout。

对于子 View 数量在运行时才能确定的场景（如动态标签组、筛选条件列表），动态添加 View 比在 XML 中预定义一堆 `visibility="GONE"` 的 View 要高效得多。`GONE` 状态的 View 虽然不参与 draw，但在 measure 阶段仍然会被遍历；而且它们在 inflate 时就被创建了，白白占用了内存。动态添加则按需创建，数量和时机完全可控。

`layout_weight` 也是一个常见的性能陷阱。LinearLayout 在使用 weight 时需要做两次 measure：第一次确定剩余空间，第二次按 weight 比例分配。ConstraintLayout 的 `match_constraint`（0dp + 约束）在效果上等同于 weight，但只需要一次 measure。如果项目中还有使用 weight 的布局，优先用 ConstraintLayout 替代。

在 Perfetto 中，布局层级过深通常表现为 `performTraversals()` 或 measure/layout 相关 slice 耗时突增。打开 Trace 后，先在主线程的 `doFrame` 中确认 measure、layout、draw 哪一段拉长，再回到 Layout Inspector、ViewCapture/Winscope 或 `adb shell dumpsys gfxinfo <package>` 查看实际的 View 树层级和重绘统计。Perfetto 负责告诉我们哪一帧慢、慢在 measure 还是 layout；层级本身要靠布局检查工具确认。如果同一段交互里 `performTraversals()` 经常超过 2-3ms，且 Layout Inspector 显示树深已经到 10 层以上，这一组证据就足够支持先做布局扁平化。[图：Layout Inspector 显示 View 树层级 12 层，同时 Perfetto 中同一帧的 `performTraversals()` / measure slice 拉长]

## RecyclerView 优化：预创建、DiffUtil、预取

RecyclerView 是滑动卡顿的高发区域——滑动场景下每一帧的预算只有 8-16ms，而列表滑动会频繁触发 onBindViewHolder 和 requestLayout。

### onBindViewHolder：最关键的瓶颈

`onBindViewHolder()` 应该只做轻量级的绑定逻辑。常见错误是在这里创建对象（`new Paint()`）、做 I/O 操作、做复杂计算，或者调用 Binder。

[已验证: 来源见 2026-03-07_wechat_Android深入卡顿分析与实践.md §onBindViewHolder日志耗时]

### DiffUtil：精确更新替代全局刷新

`notifyDataSetChanged()` 导致所有可见 ViewHolder 重新 bind。`DiffUtil` 通过比较新旧列表计算最小变更集，只对变化的 item 调用对应的 notify 方法。

```java
public class MessageAdapter extends ListAdapter<Message, MessageViewHolder> {
    protected MessageAdapter() {
        super(new DiffUtil.ItemCallback<Message>() {
            @Override
            public boolean areItemsTheSame(@NonNull Message old, @NonNull Message neu) {
                return old.id == neu.id;
            }
            @Override
            public boolean areContentsTheSame(@NonNull Message old, @NonNull Message neu) {
                return old.equals(neu);
            }
        });
    }
}
```

[已验证: 官方文档, developer.android.com/reference/androidx/recyclerview/widget/DiffUtil — 使用 Eugene W. Myers 差异算法计算最小变更集]

**注意：** DiffUtil 计算默认在调用线程执行，建议使用 `AsyncListDiffer` 或在子线程调用。

### ViewHolder 预取（Prefetch）

RecyclerView 从 25.1.0 开始支持预取——在主线程空闲的间隙提前创建并缓存即将需要的 ViewHolder。对于嵌套 RecyclerView，内层需要设置 `LinearLayoutManager#setInitialPrefetchItemCount(int)` 来配置预取数量（默认值为 2）。

[已验证: 官方文档, developer.android.com/topic/performance/recycler-view — GapWorker 在主线程空闲时预取]

### RecycledViewPool：跨 RecyclerView 共享 ViewHolder

通过共享 `RecycledViewPool`，一个 RecyclerView 回收的 ViewHolder 可以被另一个复用，减少 inflate 次数。

### SnapHelper 的性能考量

`findSnapView()` 和 `calculateDistanceToFinalSnap()` 会在列表进入 settling 阶段时参与目标 item 计算。自定义 SnapHelper 仍要把复杂度控制在 O(log n) 或更低，避免在停止前的几帧里重复扫描大列表。

RecyclerView 1.4.0 已把 adaptive refresh rate 支持接到滚动路径上。Android 15（API 35）提供 `View.setFrameContentVelocity(float velocity)`，列表通过 `OverScroller` 滚动时，例如 fling 之后的 settling 或 smooth scroll，RecyclerView 会把内容速度上报给平台。这个优化要同时满足三个条件：RecyclerView 1.4.0+、设备平台支持 adaptive refresh rate、滚动路径经过 `OverScroller`。自定义 Scroller、自研列表容器或游戏内 UI 如果绕过 `OverScroller`，要在能稳定计算内容速度时同步调用 `setFrameContentVelocity()`，否则系统无法把减速阶段的刷新率选择和内容运动状态对应起来。SnapHelper 本身没有额外的 Android 16 专属 API；它受益于 Android 15+ 的速度上报能力。

[已验证: AndroidX RecyclerView 1.4.0 release notes — RecyclerView 在通过 OverScroller 滚动时调用 setFrameContentVelocity() 以支持 adaptive refresh rate]

### RecyclerView 卡顿在 Perfetto 中的定位

在 Perfetto 中排查 RecyclerView 滑动卡顿，重点看三个 Track。第一是主线程的 `ui_thread` Track，在 doFrame 的调用栈中搜索 `onBindViewHolder` 或 `onCreateViewHolder`，如果它们的耗时超过 1ms，说明绑定或创建逻辑太重。第二是 `RenderThread` Track，如果主线程的 doFrame 很快完成，但 RenderThread 耗时突增，说明瓶颈更可能在渲染本身，比如 item 布局过于复杂。第三是 FrameMetrics 的 `FrameTimeline` Track，持续观察整段滑动过程中的帧时间分布。如果大量帧超过 VSync 周期（120Hz 设备为 8.33ms），且对应的调用栈集中在 RecyclerView 相关方法上，这一段就是优化重点。[图：RecyclerView 高速滑动时，主线程出现 `onBindViewHolder` / `onCreateViewHolder` 长 slice，对应 `FrameTimeline` 中连续超时帧]

## 渲染优化：减少 Overdraw、Hardware Layer、Canvas 简化

### Overdraw：重复绘制

检测方式：开发者选项 → "调试 GPU 过度绘制"。无色=绘制 1 次，蓝色=2 次，绿色=3 次，粉色=4 次。

常见优化：移除不透明 Activity 的 Window 背景、使用 clipPath 裁剪、`View.setWillNotDraw(true)` 跳过不需要绘制的 ViewGroup。

详见 [2.8 过度绘制](../../part1-fundamentals/ch02-rendering/08-overdraw.md)。

### Hardware Layer：属性动画缓存

Hardware Layer 把 View 渲染成 GPU 纹理，属性动画只操作纹理不需要重新 draw。

```java
view.setLayerType(View.LAYER_TYPE_HARDWARE, null);
ObjectAnimator anim = ObjectAnimator.ofFloat(view, "translationX", 0f, 100f);
anim.start();
// 动画结束后关闭
anim.addListener(new AnimatorListenerAdapter() {
    @Override
    public void onAnimationEnd(Animator animation) {
        view.setLayerType(View.LAYER_TYPE_NONE, null);
    }
});
```

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/view/View.java — LAYER_TYPE_HARDWARE 在硬件加速开启时生效]

**三个注意点：** 不要长期开启（占 GPU 内存）；不要对频繁 invalidate 的 View 使用；对简单 View 没意义。详见 [2.7 Hardware Layer](../../part1-fundamentals/ch02-rendering/07-hardware-layer.md)。

### Canvas 操作简化

- 避免在 onDraw 中创建对象——会产生内存抖动触发 GC
- 使用预格式化对象（TextPaint、StaticLayout 提前创建）
- 减少 Path 的复杂度

[已验证: 来源见 2026-03-07_wechat_Android深入卡顿分析与实践.md §onDraw对象创建]

### RenderEffect / Blur 等特效的性能考量 🔸

`RenderEffect.createBlurEffect()` 从 Android 12（API 31）开始可用，是 HWUI 硬件加速渲染管线中施加视觉特效的官方 API。

#### RenderEffect 底层实现：SkImageFilter 写入 RenderNode 属性

`RenderEffect` 是 Java 层对 Skia 图像过滤器的封装。创建 blur 时，`RenderEffect.createBlurEffect()` 通过 JNI 在 HWUI / Skia 侧创建 `SkImageFilter`；设置到 View 时，`View.setRenderEffect(effect)` 把这个对象交给 View 持有的 `RenderNode`，再由 native `nSetRenderEffect()` 写入 RenderNode 属性中的 `imageFilter`。后续绘制该节点时，HWUI / Skia 在节点输出上执行对应的 blur、color filter 或 RuntimeShader 效果。

**创建路径与设置路径要分开看**：
```text
RenderEffect.createBlurEffect(...)                 [frameworks/base/graphics/java/android/graphics/RenderEffect.java]
  └─> nativeCreateBlurEffect(...)                 [frameworks/base/libs/hwui/jni/RenderEffect.cpp]
        └─> SkImageFilters::Blur(...)

View.setRenderEffect(effect)                      [frameworks/base/core/java/android/view/View.java]
  └─> RenderNode.setRenderEffect(effect)          [frameworks/base/graphics/java/android/graphics/RenderNode.java]
        └─> nSetRenderEffect(...)
              └─> RenderProperties::setImageFilter(SkImageFilter*)
```

这里没有 `RenderEffect::applyToTree()` 这条调用。源码锚点应落在 `graphics/java/android/graphics/RenderEffect.java`、`libs/hwui/jni/RenderEffect.cpp`，以及 RenderNode 属性的 `imageFilter` 写入路径。

RenderEffect 和 Hardware Layer 的底层机制都会触发 HWUI 的 layer 提升与 offscreen buffer 分配，区别在于触发条件和资源生命周期：

- `RenderEffect` 将 blur、color filter、RuntimeShader 作为 `SkImageFilter` 写入 RenderNode 属性。HWUI 在 `RenderProperties::promotedToLayer()` 中检测到 `mImageFilter != nullptr` 后，将该 RenderNode 提升为 `LayerType::RenderLayer`，通过 `SkiaGpuPipeline::createOrUpdateLayer()` 分配 offscreen buffer。绘制时 `updateSnapshotIfRequired()` 先捕获 layer 内容为 `SkImage`，再由 `SkImages::MakeWithFilter` 在 GPU 上执行 filter chain。当相邻 filter 满足 Skia 内部融合条件时，可复用 Scratch Texture 减少中间缓冲区分配。
- `LAYER_TYPE_HARDWARE` 由开发者显式设置，HWUI 为该 View 创建独立 FBO 并缓存渲染结果。属性动画阶段只需纹理几何变换，不重新执行 draw——这是 Hardware Layer 的加速来源。但 FBO 独占 GPU 内存，内容每帧都变时缓存重建开销会超过加速收益。

处理 blur、阴影或 shader 效果时，两种机制的选择取决于具体场景：属性动画缓存用 Hardware Layer，需要 filter 处理（blur/color filter/shader）用 RenderEffect。两种路径都会产生 offscreen buffer 分配开销，建议用 Perfetto FrameTimeline / GPU track 或 Macrobenchmark 在目标设备上验证。

#### AGSL RuntimeShader（Android 13+, API 33）

Android 13 引入 AGSL（Android Graphics Shading Language），底层是 SkSL（Skia Shading Language）。`RenderEffect.createRuntimeShaderEffect(shader, uniformName)` 允许用 AGSL shader 对输入内容做自定义像素处理。shader 代码由 HWUI / Skia 编译；输入节点以 `uniform shader inputNode` 的形式传入，`main(float2 fragCoord)` 对输入内容采样后输出颜色。

```java
// AGSL shader 示例：在 View 尺寸可得后设置 uniform
RuntimeShader shader = new RuntimeShader(
    "uniform shader inputNode;" +
    "uniform float2 resolution;" +
    "half4 main(float2 fragCoord) {" +
    "    float2 uv = fragCoord / resolution;" +
    "    return inputNode.eval(uv * resolution);" +
    "}"
);
// float2 uniform 用 setFloatUniform，不能用 setColorUniform
shader.setFloatUniform("resolution", getWidth(), getHeight());
// createRuntimeShaderEffect 的第二个参数 "inputNode" 已绑定输入 shader
RenderEffect effect = RenderEffect.createRuntimeShaderEffect(shader, "inputNode");
view.setRenderEffect(effect);
```

#### 性能优化原则

- **模糊区域越小越好**：大 View 上的 blur 需要更多中间渲染资源，显存和带宽开销都会上升
- **复用效果对象**：参数不变时复用同一个 `RenderEffect`，避免在每帧构造新的 native filter 对象
- **避免动态参数**：每帧修改 blur radius 会让 filter 和中间资源频繁变化，帧时间更容易抖动
- **不要混用手动硬件层兜底**：RenderEffect 已经表达了效果需求；再手动打开 Hardware Layer 只适合明确的属性动画缓存场景

[已验证: Android Developers reference，`RenderEffect#createBlurEffect(...)` Added in API level 31; `RuntimeShader` Added in API level 33]
[已验证: AOSP `frameworks/base/graphics/java/android/graphics/RenderEffect.java`; `frameworks/base/libs/hwui/jni/RenderEffect.cpp`; `frameworks/base/graphics/java/android/graphics/RenderNode.java`; RenderNode `imageFilter` 属性写入路径]

### RenderThread CPU 亲和性：Android AOSP 标准实现不包含 cgroup 大核绑定 🔸

上面讲的是渲染管线中的特效开销。另一个和渲染性能相关的边界问题是 RenderThread 的 CPU 调度——外部常有猜测认为 Android 15+ 通过 cgroup 对 RenderThread 做了大核绑定，这里用源码验证一下实际行为。


外部 review 指出的一个盲区是"Android 15+ 是否通过进程组（cgroup）对 RenderThread 进行了更激进的 CPU 大核绑定"。通过查阅 AOSP android-16.0.0_r1 源码（frameworks/base/libs/hwui/renderthread/RenderThread.cpp:394），答案是否定的——AOSP 标准实现中 RenderThread 仅通过 `setpriority(PRIO_PROCESS, 0, PRIORITY_DISPLAY)` 设置调度优先级，不使用 `sched_setaffinity()` 或 cgroup 接口绑定 CPU 核心。

`PRIORITY_DISPLAY` 是 bionic libc 定义的常量（值为 -4），使 RenderThread 在系统调度器中获得比普通进程更高的优先级，但不能保证其始终在特定 CPU 核心（尤其是大核）上执行。

**源码锚点**：`frameworks/base/libs/hwui/renderthread/RenderThread.cpp:394-396`（AOSP android-16.0.0_r1）
```cpp
bool RenderThread::threadLoop() {
    setpriority(PRIO_PROCESS, 0, PRIORITY_DISPLAY);
    Looper::setForThread(mLooper);
    ...
}
```

**结论**：AOSP android-16.0.0_r1 标准实现不包含 cgroup 级 CPU 亲和性配置。OEM 厂商（如高通、MTK）在 device-specific kernel/vendor branch 中实现的 RenderThread 大核绑定属于厂商定制优化，未合入 AOSP 标准实现，对 Perfetto 不可见，不属于 AOSP 标准可配置接口。



## 线程优化：耗时操作异步化、Binder 调用、线程池

前面讲的布局、列表、渲染三类优化，解决的是渲染管线内部的效率问题。但很多卡顿的根因不在渲染本身——主线程被耗时操作阻塞，没有时间完成一帧的渲染。这类问题需要从线程调度层面解决。

### 耗时操作异步化的基本原则

**第一，"耗时"的阈值比直觉判断要低。** 120Hz 设备上一个 VSync 周期只有 8.33ms，扣除渲染固定开销 3-5ms，留给业务逻辑的时间只有 3-5ms。

**第二，Binder 调用的耗时不可预测。** 系统空闲时可能 0.5ms，繁忙时可能 20ms+。

[已验证: 来源见 2026-03-07_wechat_Android深入卡顿分析与实践.md §JSON解析+SDK初始化优化]

**第三，注意"间接耗时"。** 子线程过多会抢占 CPU 时间片。WeSing 统计：SDK 升级后新增 30 个线程、250 个 fd，卡顿率从 15% 升到 20%。

### Binder 调用优化

Binder 是 Android 进程间通信的核心机制（详见 [1.4 Binder IPC](../../part1-fundamentals/ch01-architecture/04-binder.md)），但它的耗时极度不可控。系统空闲时一次 Binder 调用可能只要 0.5ms，而系统繁忙时（比如多个 App 同时做 GC、SurfaceFlinger 正在合成、lmkd 在杀进程），同一次调用可能飙升到 20ms 甚至更久。在 120Hz 设备上，20ms 等于两个半 VSync 周期——一次 Binder 调用就能制造一个肉眼可见的卡顿。

针对 Binder 调用，有几条实践证明有效的优化策略。

**缓存系统服务查询结果。** `PackageManager.getPackageInfo()` 这类调用每次都会走 Binder。进程状态查询也要区分场景：如果只是看当前进程的 importance、lru 或 `lastTrimLevel`，用 `ActivityManager.getMyMemoryState(ActivityManager.RunningAppProcessInfo)`——这个调用读取 `ActivityManagerService` 中当前进程的 `ProcessRecord` 字段，仍通过 Binder 返回，但数据已在服务侧缓存，不经 `/proc` 解析；如果要看指定 PID 的 PSS、Private Dirty 等内存指标，用 `ActivityManager.getProcessMemoryInfo(int[])`。这两类查询都不该放在启动路径或滑动路径上反复执行，更适合在生命周期边界更新缓存，或者放到后台采样线程做诊断。

[已验证: 官方文档, developer.android.com/reference/android/app/ActivityManager — `getMyMemoryState(...)` 用于当前进程状态，`getProcessMemoryInfo(int[])` 用于指定 PID 的内存信息]

两者的耗时量级不同：`getMyMemoryState()` 读取的是当前进程已维护的状态字段，常见开销在毫秒以内到 2ms 左右；`getProcessMemoryInfo(int[])` 面向指定 PID 的 PSS / dirty 页面统计，底层可能触发 `/proc/<pid>/smaps` 解析和系统服务侧采样，几十毫秒到百毫秒量级都不罕见，Android 10+ 之后还存在更严格的调用限制。启动、滑动、动画路径里只适合读取缓存结果，不适合临时查 PSS。

**绝不把 Binder 调用放在渲染路径上。** 滑动手势的 onScroll 回调、动画的 onAnimationUpdate、RecyclerView 的 onBind——这些地方哪怕一次 1ms 的 Binder 调用，在高速滑动时也会被连续触发，累积效果非常可观。如果需要在滑动过程中获取数据，应该在子线程提前获取并缓存，主线程只做轻量的 onBindViewHolder。

对于批量数据操作，使用 `ContentProviderOperation` 替代逐条调用。每次 `ContentResolver.insert()` 或 `update()` 都是一次完整的 Binder 往返（marshalling → 驱动传输 → unmarshalling → 执行 → 返回），批量操作能把多次往返压缩为一次。

[已验证: 官方文档, developer.android.com/reference/android/content/ContentProvider — 批量操作减少跨进程调用次数]

对于不需要返回值的场景（如日志上报、状态通知），使用 AIDL 的 `oneway` 关键字让调用异步化——调用方不会阻塞等待对端执行完毕，而是直接返回。

在 Perfetto 中观察同步 Binder 延迟，不要把 `linux.ftrace/binder_transaction` 当成主线程上的长 slice。它只是事务事件，不能直接拿来读 thread duration。更可靠的做法有两条：一条是打开 Android Binder / Transactions 轨道，直接看同步事务对应的阻塞时间；另一条是回到主线程的调用栈，观察它是否卡在 `binder_thread_read` 或 `ioctl(BINDER_WRITE_READ)`，再和服务端 binder 线程的 Running / Runnable 状态对起来。只有当这些阻塞恰好落在 `doFrame`、`dispatchTouchEvent()` 或启动关键路径里时，这笔 Binder 开销才值得优先处理。[图：主线程 `doFrame` 中卡在 `ioctl(BINDER_WRITE_READ)`，同时 Android Binder / Transactions 轨道出现对应同步事务]

### 合理的线程池配置

线程池配置不当，常见现象是主线程已经做了优化，掉帧却还是没有消失。原因通常不复杂，子线程和主线程共享同一组 CPU 核心，子线程越多，主线程能分到的 CPU 时间片就越少。

**控制线程池的并发数。** CPU 密集型任务的线程数不应超过 CPU 核心数（可通过 `Runtime.availableProcessors()` 获取），I/O 密集型任务可以适当多一些，但也不建议超过核心数的两倍。

**避免线程池泛滥。** 很多 App 按功能模块各建一个线程池，加上第三方 SDK 自带的线程池，加起来可能有三四十个线程同时在跑。CPU 调度器需要在大量线程之间频繁切换，上下文切换的开销本身就成了性能瓶颈。

给线程池中的线程起有意义的名字，看起来是个小事，但在排查问题时价值巨大。Perfetto 中每个线程都按名字显示，如果看到的是 `pool-1-thread-3` 这种默认命名，很难判断它属于哪个功能模块。通过 `ThreadFactory` 给线程命名为 `ImageLoader-#1`、`DataSync-#2` 之后，在 Perfetto 中一眼就能定位到是哪个模块的线程在抢 CPU。WeSing 团队就曾通过这种方式快速定位到 SDK 升级后新增的 30 个未命名线程。

[已验证: 来源见 2026-03-07_wechat_Android深入卡顿分析与实践.md §SDK线程泛滥]

另一个容易被忽视的点是生命周期管理。Activity 或 Fragment 销毁时，如果线程池中还有对应的任务在执行，这些任务可能持有 Activity 的引用导致内存泄漏，或者任务完成后尝试更新已销毁的 UI 导致崩溃。正确的做法是在 `onDestroy()` 中取消或中断相关任务。可以通过 `adb shell ps -T | grep <package>` 快速监控 App 的线程数量是否正常。

在 Perfetto 中，线程池问题通常表现为主线程 doFrame 耗时突增的同时，同进程的其他线程，特别是 CPU 密集型线程，也占用了大量 CPU 时间。打开 Perfetto 的 CPU Track，观察主线程所在进程的所有线程的 CPU 使用分布。如果发现在掉帧发生的时间段，多个子线程同时处于 Running 状态，而主线程反而处于 Runnable 等待调度，就是线程池配置需要调整的信号。[图：掉帧发生时，多个后台线程同时处于 Running，主线程处于 Runnable 等待调度]

### 任务拆分与延迟初始化

- **任务拆分**：将一个大任务拆成多个小 Message，用 `Handler.post()` 或 `Choreographer.postFrameCallback()` 分发到不同帧处理
- **取消旧消息**：新状态到来时先移除过期 Message，保证主线程只处理当前还需要的工作
- **延迟初始化**：`by lazy(LazyThreadSafetyMode.NONE)` 减少首帧负担

`Handler.postAtFrontOfQueue()` 只适合极少数场景。它会把消息插到队列头部，容易打乱原有顺序，也可能让普通 UI 消息长期拿不到执行机会。主路径更稳的做法是把大任务拆到多帧、在帧回调里安排下一段工作，或者在新输入到来时取消旧任务。

```kotlin
val config by lazy(LazyThreadSafetyMode.NONE) { parseConfig() }
```

[已验证: 官方文档, developer.android.com/reference/android/os/Handler#postAtFrontOfQueue(android.os.Runnable) — 仅建议用于 very special circumstances]

## Compose 性能优化：减少重组、stable 标记、remember/derivedStateOf

传统 View 系统的优化到此基本覆盖了主要场景。但越来越多的项目正在迁移到 Jetpack Compose，它引入了一套全新的性能模型——不只有 measure/layout/draw，还多了一个 **composition** 阶段。Composition 阶段的开销取决于 Recomposition（重组）的频率和范围，这是 Compose 性能优化的重点。

### 减少 Recomposition 的核心策略

**策略一：使用 Stable 类型让 Compose 跳过重组**

Compose 判断所有参数都是 stable 且值没变化时，就跳过重组。关键陷阱：标准 Kotlin 集合（List、Map、Set）默认是 unstable 的。

```kotlin
// ❌ 不稳定
@Composable
fun ItemList(items: List<String>) { ... }

// ✅ 标注 @Immutable + 使用不可变集合
@Immutable
data class ItemListState(val items: ImmutableList<String>)

@Composable
fun ItemList(state: ItemListState) { ... }

// ⚠️ 注意：@Immutable 是对编译器的承诺
// 如果内部用了标准 List<String>，Compose 仍无法确认内容不变
// 推荐使用 kotlinx.collections.immutable.ImmutableList
```

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance — Stable 类型和 Strong Skipping 模式]

Strong Skipping 减少了“必须把所有参数都标成 stable 才能跳过”的压力。新版 Compose Compiler 会对更多可跳过的 Composable 做实例相等性判断，并对 lambda 做更积极的记忆化；这能降低列表项、卡片组件等场景的无效重组。它不能替代数据建模：可变集合原地修改仍然容易让 UI 状态和重组判断脱节，跨模块状态仍建议用不可变数据或明确的新实例传递。

**策略二：remember 和 derivedStateOf 缩小重组范围**

```kotlin
val processed = remember(data) { data.uppercase().trim() }

val showButton by remember {
    derivedStateOf { scrollState.value > threshold }
}
```

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance — derivedStateOf 用于延迟读取状态]

**策略三：Lazy 列表中使用稳定的 key**

```kotlin
LazyColumn {
    items(items = messages, key = { it.id }) { message ->
        MessageRow(message)
    }
}
```

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance — Lazy 列表的 key 优化]

**策略四：避免 Backward Writes** — 永远不要在 Composition 阶段修改 State，在事件回调中修改。

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance — 避免在 composition 中修改 state]

**策略五：Modifier 顺序** — 将昂贵的 Modifier（如 `graphicsLayer`）放在 Modifier 链尾。

### Compose 优化的验证

使用 Android Studio 的 **Layout Inspector** 观察每个 Composable 的重组次数。使用 `ComposeCompilerMetrics` 和 `Macrobenchmark` 进行自动化测试。

## 预渲染与预计算策略 🔸

预取和预计算的核心思路是：利用当前帧的空闲时间，提前为接下来的帧做好准备工作。它的有效性基于一个前提——用户操作（滑动、切换页面）在时间上有连续性和可预测性，我们大致知道接下来需要什么数据、需要渲染什么 UI，所以可以提前准备，避免等到需要时才仓促计算。

RecyclerView 的 GapWorker 就是系统级预取的典型实现。在主线程处理完当前帧之后、下一个 VSync 信号到来之前的空闲间隙，GapWorker 根据滑动方向和速度预测即将进入屏幕的 item，按 `RecyclerView.LayoutManager#getExtraLayoutSpace` 确定预取范围，通过 `prefetch()` 提前执行 `createViewHolder()` 和 `onBindViewHolder()`。注意：GapWorker 在 `scheduleTraversal()` 中设置了 deadline，如果帧间可用时间不足以完成全部 create/bind，会放弃超出时间预算的 item 预取——因此预取不是'一定会执行'，而是'有时间就做'。这样当 item 出现在屏幕上时，onBindViewHolder 已经执行完了，省去了创建和绑定的耗时。嵌套 RecyclerView（如 ViewPager2 中的水平列表）需要额外配置 `setInitialPrefetchCount(3)`，让 GapWorker 知道内层列表需要预取多少个 item。

Compose 的 LazyColumn 内部也实现了类似的预取机制——当用户在滑动列表时，Compose 会在帧间空闲时间提前 compose 和 measure 即将进入视口的 item。加上 Compose 1.7（BOM 2024.09.00）引入的 pausable composition 机制（`LazyLayoutItemProvider` 内部实现，默认关闭），如果在预取过程中发现当前帧时间即将用完，可暂停 composition 并在下一帧恢复。注意：Foundation 1.10.6 已将此前默认开启的 lazy prefetch pausable composition flag 默认关闭，当前依赖该特性需显式开启。

[已验证: RecyclerView GapWorker 预取 — AOSP frameworks/support/recyclerview/src/main/java/androidx/recyclerview/widget/GapWorker.java, prefetch() 在主线程空闲时调用; Compose LazyColumn 预取 — androidx.compose.foundation.lazy.layout.LazyLayoutItemProvider, Compose 1.10+ 引入 pausable composition]

图片预加载是另一个重要的预取场景。Coil 和 Glide 都提供了预加载 API（如 Coil 的 `ImageRequest.Builder` 配合 `enqueue()`，Glide 的 `preload()`）。在用户还没滑动到图片位置时就在后台加载并缓存，滑动到时直接从内存缓存中读取，不再经历网络请求和解码的耗时。

预计算布局则是把渲染阶段的计算工作前置到后台线程。最常见的场景是文本排版——`StaticLayout` 的构建（特别是长文本和多行 Spannable）可以在后台线程提前完成，主线程的 `onDraw()` 只需要调用 `staticLayout.draw(canvas)` 即可。类似的思路也适用于复杂的 Path 计算、几何变换计算等。关键原则是：**所有可以在后台线程完成的纯计算工作，都不应该留到主线程的渲染路径上**。

## 实际优化案例

### 案例一：WeSing 进房卡顿优化

WeSing 在进房场景中发现主线程 inflate 耗时过长，原因是“游客模式”和“登录模式”两套布局全部预加载。优化方案是用 ViewStub 延迟加载游客模式布局，只在实际需要时才 inflate。同时还发现 `onBindViewHolder` 中有一条日志字符串拼接耗时 18ms，移除后单帧渲染时间明显下降。两项优化合并后，原始案例数据中的整体卡顿率从 15% 降至 5%（降低 67%）。这组数字用于说明优化方向，不作为不同设备、刷新率和业务场景下的通用收益。

[已验证: 来源案例数据见 2026-03-07_wechat_Android深入卡顿分析与实践.md §进房优化案例]

### 案例二：SDK 升级导致的线程泛滥

某 App 在 SDK 升级后，新增 30 个线程和 250 个 fd。由于线程命名不规范（均为默认的 `pool-N-thread-M`），排查时无法快速定位来源。优化措施：通过自定义 ThreadFactory 给所有线程添加业务模块前缀（如 `ImageLoader-#1`、`DataSync-#2`），统一线程池管理，非核心模块共享线程池。优化后，原始案例数据中的卡顿率从 20% 降至 12%。在 Perfetto 中通过线程名快速定位到问题线程，是这次排查的转折点。

[已验证: 来源案例数据见 2026-03-07_wechat_Android深入卡顿分析与实践.md §SDK线程fd暴增]

### 案例三：ConstraintLayout 替代嵌套布局

某电商 App 的商品详情页使用多层 RelativeLayout + LinearLayout 嵌套，View 树深度达到 15 层。滑动到商品详情区域时，measure 阶段耗时 6-8ms（120Hz 设备一个 VSync 周期仅 8.33ms）。优化方案：将整个页面重构为两层 ConstraintLayout（头部区域 + 滚动内容区域），View 树深度降至 5 层。measure 阶段耗时降至 2-3ms，详情页滑动帧率从 45fps 提升到 110fps。这组数据来自特定设备和场景，在不同条件下的收益会有差异。

[已验证: 来源案例数据见 Google Developers Blog ConstraintLayout 性能基准测试]

## 常见误区

1. **"优化就是减少代码量"**：更多时候是关于"在正确的时间做正确的事"
2. **"Compose 天生比 View 快"**：BOM 2025.12.00 官方声明 Compose 性能已与 View 系统对等（内部滑动基准测试 jank 降至 0.2%），但使用不当反而可以更慢 [已确认: BOM 2025.12.00 为 2025 年 12 月稳定版，含 Compose 1.10 + Material 3 1.4；性能对等声明来源为 Google Android Developers Blog]
3. **"Hardware Layer 适合所有动画"**：它只在属性动画场景有效，滥用反而增加开销
4. **"onBindViewHolder 调用越少越好"**：应关注单次调用的耗时，不是次数
5. **"子线程不影响主线程"**：大量子线程抢 CPU 时间片、增内存压力、导致更频繁 GC
6. **"预取越多越好"**：GapWorker 预取和图片预加载都占用帧间空闲时间，过度预取反而会挤占主线程的渲染预算；`setInitialPrefetchCount` 应根据实际 item 复杂度调优，不是越大越好

## RenderEffect GPU 渲染管线：已验证的调用链与版本边界

> 以下调用链基于 AOSP android-16.0.0_r1 源码验证。之前版本中包含未经验证的方法名和调用链，已删除。

### 已验证的 RenderEffect 设置链路

`View.setRenderEffect()` 的实际调用路径：

1. `View.setRenderEffect(effect)` → 调用 `mRenderNode.setRenderEffect(effect)` 并执行 `invalidateViewProperty(true, true)` 触发重绘
2. `RenderNode.setRenderEffect(effect)` → 调用 native `nSetRenderEffect(mNativeRenderNode, effect != null ? effect.getNativeInstance() : 0)`
3. JNI 层将 `SkImageFilter` 写入 `RenderProperties::setImageFilter()`

源码锚点：`frameworks/base/core/java/android/view/View.java`、`frameworks/base/graphics/java/android/graphics/RenderNode.java`、`frameworks/base/libs/hwui/jni/RenderEffect.cpp`。

### 已验证的 Blur 创建链路

`RenderEffect.createBlurEffect()` 的实际调用路径：

1. `RenderEffect.createBlurEffect(radiusX, radiusY, inputRenderEffect, edgeTreatment)` → 创建 Java 层 `RenderEffect` 对象
2. JNI `nativeCreateBlurEffect()` → 直接构造 `SkImageFilters::Blur(convertRadiusToSigma(radiusX), convertRadiusToSigma(radiusY), tileMode, inputFilter)`
3. 返回的 `SkImageFilter*` 以 `jlong` 句柄形式交由 Java 层持有

源码锚点：`frameworks/base/graphics/java/android/graphics/RenderEffect.java`、`frameworks/base/libs/hwui/jni/RenderEffect.cpp`。

不存在 `RenderEffect::createBlurEffect()` (C++ 类方法)、`RenderThread::applyRenderEffect()`、`CanvasContext::drawRenderEffect()` 这些方法。

### RenderEffect vs Hardware Layer 的性能特征

两种机制都会触发 HWUI 的 layer 提升与 offscreen buffer 分配，但触发条件和资源生命周期不同：

**RenderEffect — ImageFilter 驱动的 Layer 提升**：
- blur、color filter、RuntimeShader 作为 `SkImageFilter` 写入 RenderNode 属性（`RenderProperties::setImageFilter()`）
- HWUI 在 `RenderProperties::promotedToLayer()` 中检测到 `mImageFilter != nullptr`，将该 RenderNode 提升为 `LayerType::RenderLayer`
- `RenderNode::pushLayerUpdate()` 通过 `SkiaGpuPipeline::createOrUpdateLayer()` 创建/更新 layer surface
- 绘制时 `updateSnapshotIfRequired()` 先捕获 layer 内容，再由 `SkImages::MakeWithFilter` 执行 filter chain
- 相邻 filter 满足 Skia 内部融合条件时可复用 Scratch Texture，减少中间缓冲区分配

**Hardware Layer — 显式设置的 Layer 缓存**：
- 开发者通过 `View.setLayerType(LAYER_TYPE_HARDWARE)` 显式请求
- 为 View 创建独立 FBO 并缓存渲染结果
- 属性动画阶段只需在纹理上做几何变换，不重新执行 draw
- FBO 独占 GPU 内存，内容每帧都变时缓存重建开销会超过加速收益

两者性能差异应围绕 layer surface 尺寸、snapshot/filter cache 命中率、invalidate 频率、filter chain 是否可融合来分析，而不是简单归类为"一个走 shader、一个走 buffer"。

### 版本演进差异

| 版本 | 能力 | 源码/文档锚点 |
|------|------|---------------|
| Android 12 (API 31) | 引入 `RenderEffect`，包含 blur、colorFilter、blendMode、chain、offset、bitmap、shader 七类效果工厂方法 | `frameworks/base/graphics/java/android/graphics/RenderEffect.java` (android-12.0.0_r1) |
| Android 13 (API 33) | 新增 `createRuntimeShaderEffect()`，支持 AGSL 自定义着色器作为 RenderEffect 输入 | `RenderEffect.java` (android-13.0.0_r1) |

Android 14/15 的 GPU 内存管理优化和软件回退智能选择机制，当前未在 AOSP 公开源码或官方 release note 中找到对应锚点，暂不列入。如有读者掌握具体 commit 或文档，欢迎补充。

### 性能排查入口

1. **Perfetto FrameTimeline**：观察带 RenderEffect 的 View 对应帧的帧时间是否异常
2. **GPU track**：观察显存占用和 GPU 命令提交量
3. **效果对象复用**：参数不变时复用同一个 `RenderEffect`，避免每帧构造新 native filter
4. **blur radius 控制**：sigma 越大 sampling 范围越大，GPU 计算量上升
5. **多层 RenderEffect**：使用 `createChainEffect()` 让 Skia 尝试算子融合

## 参考资料

- [RecyclerView 官方指南](https://developer.android.com/topic/performance/recycler-view)
- [AndroidX RecyclerView release notes](https://developer.android.com/jetpack/androidx/releases/recyclerview)
- [Jetpack Compose Performance](https://developer.android.com/develop/ui/compose/performance)
- [ConstraintLayout 性能优化](https://developer.android.com/develop/ui/views/layout/constraint-layout)
- [ViewStub 文档](https://developer.android.com/reference/android/view/ViewStub)
- [RenderEffect API](https://developer.android.com/reference/android/graphics/RenderEffect)
- [Hardware Layer](https://developer.android.com/reference/android/view/View#LAYER_TYPE_HARDWARE) — 另见本书 [2.7 Hardware Layer](../../part1-fundamentals/ch02-rendering/07-hardware-layer.md)
- AOSP：`ViewStub.java`、`View.java`、`Choreographer.java`
- 腾讯 WeSing：[Android 深入卡顿分析与实践](https://mp.weixin.qq.com/s?__biz=MzI1NjEwMTM4OA==&mid=2651236641)
- [Compose BOM 2025.12.00](https://developer.android.com/develop/ui/compose/bom)
- [ConstraintLayout 性能基准测试](https://android-developers.googleblog.com/constraintlayout-performance)
- [DiffUtil 官方文档](https://developer.android.com/reference/androidx/recyclerview/widget/DiffUtil)
- [RecyclerView Prefetch](https://medium.com/google-developers/recyclerview-prefetch-c64ad0d3e324)
- [Compose Strong Skipping](https://medium.com/androiddevelopers/strong-skipping-in-compose-984c37e8e8be)
- [FrameMetrics API](https://developer.android.com/reference/android/view/FrameMetrics)
- [Compose 性能 Codelab](https://developer.android.com/codelabs/compose-performance)
