---
title: "自定义 View 性能优化"
chapter: "22.4"
section: "22.4"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-05-12"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium
drafted_date: "2026-05-12"
polish_count: 0
sources:
  - type: official
    path: "developer.android.com/topic/performance/rendering/optimizing-view"
  - type: official
    path: "developer.android.com/develop/ui/views/graphics/hardware-accel"
  - type: official
    path: "perfetto.dev/docs/getting-started/system-tracing"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/Color.java"
tags: [custom-view, ondraw, canvas, hardware-acceleration, invalidate, viewrootimpl, hwui]
related_chapters: ["22.1", "2.5", "2.7", "2.10", "7.10"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: "reviewed"
task2b_state: "fixed"
task2b_result: fixed-lite
last_task2b_lite_at: "2026-05-27"
reviewed_by: openclaw-task6
reviewed_date: '2026-06-17'
task6_result: pass-light-edit
task9_result: "auto-fixed"
last_task2b_at: "2026-05-13T23:35:47+08:00"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-27"
last_task9_at: "2026-06-17T02:36:15+08:00"
task6_reviewed_date: "2026-05-27"
task6_review_notes: "2026-06-17 Task6 revisiting复审：pass-light-edit。L1/L2 扫描通过（22.4 复审无禁用词、高频词、元叙述命中）；task9 auto-fix 已验证写作质量无回归；queue 无 pending；自动晋升 finalized。"
last_task6_review_log: logs/review/2026-06-17-04-review.md
last_task6_at: "2026-06-17T04:06:00+08:00"
task9_review_notes: "2026-05-27 task9 deep-review: auto-fixed。修正 GC 观测归因、硬件加速 Canvas API 版本边界、debug.hwui.profile/Perfetto 观测口径与 onDraw invalidate 表述；回到 Task6 复审。 | 2026-05-27 14:20 Task9 deep-review：pass-tech-review。复核硬件加速 Canvas API 支持表、`invalidate(Rect)` API 21+ 脏区口径、RenderNode API 29 与 Perfetto/GC 观测口径；无 P0/P1，queue 无 pending，自动晋升 finalized。 | 2026-06-17 Task9 idle-audit auto-fix：修正 invalidate 脏区/整树重绘口径、onLayout 触发条件和 postInvalidateOnAnimation 跨线程 attach 边界；回到 Task6 复审。"
last_task2b_verifier_at: "2026-05-27T11:44:00+08:00"
task2b_verifier_result: ready-for-task6
last_task9_autofix_at: "2026-06-17"
last_task9_review_log: "logs/deep-review/2026-06-17-02-audit.md"
p0: 2
p1: 0
p2: 0
last_task9_audit: "2026-06-17"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-16
---
# 自定义 View 性能优化

自定义 View 的优化对象不只是一段 `onDraw()`。一次状态变化可能停在 draw，也可能通过 `requestLayout()` 把工作扩到 measure 和 layout；UI 线程完成 DisplayList 记录后，RenderThread、App Window BufferQueue、SurfaceFlinger、HWC 和 present 仍会决定这一帧何时可见。

平台源码固定到 Android 17 / API 37 / `android-17.0.0_r1`，kernel 固定到 `android17-6.18-2026-06_r6`。普通自定义 View 没有独立 Surface，属于标准 HWUI App Window：`Choreographer#doFrame` 驱动 traversal，UI 线程更新 View 对应的 RenderNode / DisplayList，`HardwareRenderer.syncAndDrawFrame()` 把树状态交给 RenderThread，后续经过 BLAST、SurfaceFlinger、HWC 和 present。显示后段可结合 [Android View 标准渲染链路](../../part2-performance/ch18-rendering-pipelines/02-android-view-standard.md) 阅读。

## measure、layout、draw：按触发条件判断成本

`onMeasure()`、`onLayout()` 与 `onDraw()` 没有固定的优化优先级。应先用 trace 判断哪一段执行过多或单次过长：

| 回调 | 常见触发条件 | 应避免的工作 |
| --- | --- | --- |
| `onMeasure()` | `requestLayout()`、父约束变化、attach、窗口或配置变化 | I/O、重复解析文本、无边界的多轮 child measure |
| `onLayout()` | layout request，或 View 的 bounds 变化并留下 layout-required 状态 | 分配临时坐标对象、重复计算与 measure 相同的几何关系 |
| `onDraw()` | 内容 invalidation、动画、父级绘制或 DisplayList 需要重录 | 对象分配、同步 I/O、每帧重建不变 Path / Shader |

同一组 `MeasureSpec` 在没有 force-layout 时可能命中 `View.measure()` 的缓存，`onMeasure()` 不一定执行。`requestLayout()` 会清空当前 View 的 measure cache，设置 force-layout / invalidated 标记，并向尚未请求布局的父级传播。到 `ViewRootImpl` 后会安排 traversal；本轮哪些分支重新 measure、layout 和 draw，仍由 flags、约束与窗口状态决定。

### `onMeasure()` 的缓存必须覆盖完整输入

测量缓存不能只比较宽度。高度 spec、padding、数据版本、字体和 locale、layout direction、子 View 可见性与 margin 都可能改变结果。缓存适合保存纯计算得到的几何结果，不能绕过 `setMeasuredDimension()` 或破坏父容器约束。

下面的示例用两个 `MeasureSpec` 和显式内容版本保护缓存。`computeGeometry()` 只做 CPU 计算，不修改 View 树。

```java
private int mLastWidthSpec = Integer.MIN_VALUE;
private int mLastHeightSpec = Integer.MIN_VALUE;
private int mLastContentVersion = -1;
private int mLastPaddingLeft = Integer.MIN_VALUE;
private int mLastPaddingTop = Integer.MIN_VALUE;
private int mLastPaddingRight = Integer.MIN_VALUE;
private int mLastPaddingBottom = Integer.MIN_VALUE;
private int mContentVersion;
private int mDesiredWidth;
private int mDesiredHeight;

@Override
protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
    if (widthMeasureSpec != mLastWidthSpec
            || heightMeasureSpec != mLastHeightSpec
            || mContentVersion != mLastContentVersion
            || getPaddingLeft() != mLastPaddingLeft
            || getPaddingTop() != mLastPaddingTop
            || getPaddingRight() != mLastPaddingRight
            || getPaddingBottom() != mLastPaddingBottom) {
        computeGeometry(widthMeasureSpec, heightMeasureSpec);
        mLastWidthSpec = widthMeasureSpec;
        mLastHeightSpec = heightMeasureSpec;
        mLastContentVersion = mContentVersion;
        mLastPaddingLeft = getPaddingLeft();
        mLastPaddingTop = getPaddingTop();
        mLastPaddingRight = getPaddingRight();
        mLastPaddingBottom = getPaddingBottom();
    }

    setMeasuredDimension(
            resolveSizeAndState(mDesiredWidth, widthMeasureSpec, 0),
            resolveSizeAndState(mDesiredHeight, heightMeasureSpec, 0));
}
```

数据、字体、locale 或 layout direction 改变且会影响期望尺寸时，更新 `mContentVersion` 后调用 `requestLayout()`；只改变颜色时不应增加测量版本。自定义 `ViewGroup` 还要为每个 child 生成正确的 child spec、合并 measured state，并处理 margin、padding 和最小尺寸，不能用缓存跳过这些契约。

### `onLayout()` 不能只看 `changed`

`changed` 表示当前 View 的 bounds 相对上次是否变化。child 的测量尺寸、可见性、margin、layout direction 或业务排序变化时，即使父 bounds 没变，child 位置也可能要更新。安全做法是让 measure / 几何计算阶段产出一份与完整输入绑定的坐标缓存，`onLayout()` 只消费这份缓存。

若 trace 显示同一帧发生多轮 measure / layout，要查调用栈和请求源。常见原因包括在 layout 中再次 `requestLayout()`、父子约束互相依赖、权重或 `wrap_content` 协商，以及 Adapter 更新同时改变布局参数。

## `onDraw()`：移除热路径分配

硬件加速时，View 的绘制代码由 UI 线程记录进 RenderNode 的 DisplayList。没有 invalidation 的 View 可以复用已经记录的 DisplayList；被标记为 dirty 的节点才需要更新。RenderThread 消费这些记录并准备窗口 buffer，`onDraw()` 本身仍运行在 UI 线程。

热路径分配会增加分配器工作、缓存扰动和 GC 负载。少量分配不一定产生可见卡顿，结论要由 allocation recording、GC 轨道和帧时间共同证明。工程目标是移除可避免的逐帧分配，而非用一个对象数量阈值代替测量。

下面的波形 View 在构造阶段创建绘制对象，在尺寸或数据变化时更新几何，`onDraw()` 只提交绘制命令。

```java
public final class WaveformView extends View {
    private final Paint mGridPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint mWavePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Path mWavePath = new Path();
    private final RectF mContentBounds = new RectF();

    public WaveformView(Context context, AttributeSet attrs) {
        super(context, attrs);
        mGridPaint.setColor(0x40FFFFFF);
        mWavePaint.setStyle(Paint.Style.STROKE);
        mWavePaint.setStrokeWidth(2f);
    }

    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        super.onSizeChanged(w, h, oldw, oldh);
        mContentBounds.set(
                getPaddingLeft(),
                getPaddingTop(),
                w - getPaddingRight(),
                h - getPaddingBottom());
        rebuildWavePath(mWavePath, mContentBounds);
    }

    public void setSamples(float[] samples) {
        copySamplesAndRebuildPath(samples, mWavePath, mContentBounds);
        invalidate();
    }

    @Override
    protected void onDraw(Canvas canvas) {
        drawGrid(canvas, mContentBounds, mGridPaint);
        canvas.drawPath(mWavePath, mWavePaint);
    }
}
```

`setSamples()` 必须在 UI 线程调用，并复制或接管一份稳定数据，避免调用方在绘制期间修改数组。若采样持续高速到达，还要在上游合并更新；主线程每收到一个点就重建整条 Path，仍可能让记录成本超过预算。

常见分配源包括 `String.format()`、临时 `String`、装箱集合、`new RectF()`、`new Path()`、临时数组和每帧创建的 Shader。文字格式化应在数据变化时完成，数组和几何对象应复用。不变 Path 可以预计算；持续修改复杂 Path 即使没有 Java 分配，也可能增加 HWUI 的几何处理和 GPU 工作。

`Canvas.save()` / `restore()` 管理的是 Canvas 状态栈，不能按 Java 对象分配解释。嵌套 layer、复杂 clip 和 transform 仍有执行成本，应把保存范围限制在需要隔离的绘制段。

## 硬件加速、Layer 与 `setWillNotDraw`

### 以当前 Canvas 判断绘制后端

`View.isHardwareAccelerated()` 表示 View 所在窗口启用了硬件加速；当前绘制可能仍使用软件 Canvas，例如把 View 画入 Bitmap。绘制代码需要分支时，应检查 `canvas.isHardwareAccelerated()`。

Android 10—17 已支持 `clipPath()`、`drawPicture()` 和 `drawVertices()` 等历史上存在边界的调用。兼容性仍要按当前官方表逐项核对；例如官方表仍把 `Paint.setLinearText()` 和 `setMaskFilter()` 标为硬件 Canvas 不支持。问题可能表现为空白、异常或像素错误，不能统一写成“自动软件降级”。

### `LAYER_TYPE_NONE` 仍然复用 DisplayList

`setLayerType()` 控制单个 View 是否增加离屏 layer，不控制整个窗口是否硬件加速。

| 类型 | Android 17 语义 | 合适场景 | 主要代价 |
| --- | --- | --- | --- |
| `LAYER_TYPE_NONE` | 正常 View RenderNode / DisplayList，无强制离屏 buffer | 默认选择 | 无额外 layer；dirty 时仍需重录 |
| `LAYER_TYPE_HARDWARE` | 硬件加速窗口中渲染到硬件纹理 | 复杂子树的短时 alpha / transform 动画，或明确的合成效果 | GPU 内存、建 layer 与内容失效后的重栅格化 |
| `LAYER_TYPE_SOFTWARE` | 子树用 CPU 绘制到 Bitmap，再参与宿主窗口绘制 | 硬件 Canvas 不支持且已验证的局部兼容路径 | Bitmap 内存、CPU 栅格化、纹理上传 |

静态 View 在默认模式下已经能复用 DisplayList，没有必要仅因“内容复杂”长期强制 hardware layer。hardware layer 的典型收益来自内容保持不变、外层 alpha / translation / scale / rotation 持续变化的短时动画。动画同时修改 View 内容并频繁 `invalidate()` 时，layer 仍要更新，收益可能消失。

`ViewPropertyAnimator.withLayer()` 会在动画前启用 hardware layer，并在结束后恢复原 layer type。下面的用法适合先用 trace 证明 rasterization 是属性动画中的主要成本，再作为局部优化。

```java
view.animate()
        .alpha(0f)
        .translationY(-view.getHeight() / 4f)
        .setDuration(220L)
        .withLayer()
        .start();
```

hardware layer 会占用与 View 面积、像素格式相关的 GPU 资源，大面积 View 尤其要检查内存和 RenderThread。`hasOverlappingRendering()` 只有在 View 内容不存在重叠绘制时才可返回 `false`；错误返回会改变透明度合成结果。

### `setWillNotDraw(true)` 只跳过 ViewGroup 自身绘制

纯布局 `ViewGroup` 可以设置 `setWillNotDraw(true)`，让 framework 跳过它自己的 `onDraw()`。child 的 `dispatchDraw()` 不会因此消失。容器需要画背景、分隔线、调试标记或其他自身内容时，应清除该标记。

下面的容器只排列 child，不提供自身视觉内容。

```java
public final class FlowLayout extends ViewGroup {
    public FlowLayout(Context context, AttributeSet attrs) {
        super(context, attrs);
        setWillNotDraw(true);
    }
}
```

给 ViewGroup 设置 background 时，framework 可能调整绘制标记。不要把 `setWillNotDraw(true)` 当作覆盖所有背景行为的强制开关；增加自身绘制后应明确改为 `false` 并验证结果。

## `invalidate()`、动画刷新与 `requestLayout()`

| API | 调用线程与时机 | 适用变化 | Android 17 边界 |
| --- | --- | --- | --- |
| `invalidate()` | UI 线程，安排后续绘制 | 像素内容、颜色、Path、Drawable | 标记 View dirty，并向父级传播 damage |
| `postInvalidateOnAnimation()` | attach 后可从非 UI 线程调用，在下一动画时间步派发 | 与显示帧节奏对齐的自绘动画 | 未 attach 时没有 `AttachInfo`，调用不会安排刷新 |
| `requestLayout()` | UI 线程，向父级传播 layout request | 期望尺寸、child 尺寸或位置 | 清 measure cache，设置 force-layout / invalidated，安排 traversal |

API 21 起，`invalidate(Rect)` 和四坐标重载的调用方 dirty rectangle 被忽略，公开 API 也已弃用。Android 17 的 `View.java` 仍保留内部 damage 传播和 RenderNode 粒度的 DisplayList 更新；应用侧应调用无参 `invalidate()`，再通过拆分 View 或 RenderNode 改变更新粒度。

下面的 setter 区分“只改像素”和“改变尺寸”。

```java
public void setWaveColor(int color) {
    if (mWavePaint.getColor() == color) return;
    mWavePaint.setColor(color);
    invalidate();
}

public void setLabelText(String text) {
    if (Objects.equals(mLabelText, text)) return;
    mLabelText = text;
    mContentVersion++;
    requestLayout();
    invalidate();
}
```

`requestLayout()` 不保证自动补齐所有业务绘制状态，因此尺寸与像素都变化时可以同时调用两者。若文字变化但固定 bounds 与现有基线能容纳新内容，只需要重建文字布局并 `invalidate()`；是否 request layout 由尺寸契约决定。

### 连续动画要有生命周期

在 `onDraw()` 中无条件调用 `invalidate()` 会持续请求后续帧，即使 View 不可见或动画已经完成。自绘动画可以使用 `postInvalidateOnAnimation()`，但必须有明确的运行状态，并在 detach、不可见或终止条件到达时停止。

下面的骨架只在动画活跃时请求下一帧。

```java
@Override
protected void onDraw(Canvas canvas) {
    drawFrame(canvas, mProgress);
    if (mRunning) {
        postInvalidateOnAnimation();
    }
}

@Override
protected void onDetachedFromWindow() {
    mRunning = false;
    super.onDetachedFromWindow();
}
```

`ValueAnimator` 能提供基于时钟的进度和取消机制，但其 update callback 仍可能每帧触发 invalidation。选择 Animator 的理由是时间模型和生命周期更清楚，不是减少刷新次数。

### `ViewCompat.postInvalidateOnAnimation()` 的版本位置

平台 `postInvalidateOnAnimation()` 从 API 16 提供。适用范围为 Android 10—17，可以直接调用平台 API。共享给更低 minSdk 的旧模块可以使用 `ViewCompat.postInvalidateOnAnimation()`；这属于兼容层选择，不改变 Android 17 的调度语义。

## 手动 `RenderNode`：只拆独立更新的内容

公开 `RenderNode` 从 API 29 提供。每个 View 已经由 framework 持有 RenderNode，手动再拆节点只适合一个自定义 View 内存在面积较大、更新频率不同且可独立记录的子场景。小图元很多、每帧都全部变化或软件 Canvas 必须完整支持时，额外节点管理可能得不偿失。

下面的示例把静态网格和动态波形分成两个节点。节点在字段初始化时创建，硬件 Canvas 走 `drawRenderNode()`，软件 Canvas 直接调用原绘制函数，避免截图或 Bitmap 绘制得到空白。

```java
private final RenderNode mGridNode = new RenderNode("wave-grid");
private final RenderNode mWaveNode = new RenderNode("wave-data");
private boolean mGridDirty = true;
private boolean mWaveDirty = true;

@Override
protected void onSizeChanged(int w, int h, int oldw, int oldh) {
    super.onSizeChanged(w, h, oldw, oldh);
    mGridNode.setPosition(0, 0, w, h);
    mWaveNode.setPosition(0, 0, w, h);
    mGridDirty = true;
    mWaveDirty = true;
}

private void recordGridNode() {
    RecordingCanvas recordingCanvas = mGridNode.beginRecording();
    try {
        drawGrid(recordingCanvas);
    } finally {
        mGridNode.endRecording();
    }
}

private void recordWaveNode() {
    RecordingCanvas recordingCanvas = mWaveNode.beginRecording();
    try {
        drawWave(recordingCanvas);
    } finally {
        mWaveNode.endRecording();
    }
}

@Override
protected void onDraw(Canvas canvas) {
    if (!canvas.isHardwareAccelerated()) {
        drawGrid(canvas);
        drawWave(canvas);
        return;
    }

    if (mGridDirty || !mGridNode.hasDisplayList()) {
        recordGridNode();
        mGridDirty = false;
    }
    if (mWaveDirty || !mWaveNode.hasDisplayList()) {
        recordWaveNode();
        mWaveDirty = false;
    }

    canvas.drawRenderNode(mGridNode);
    canvas.drawRenderNode(mWaveNode);
}
```

内容更新时设置对应 dirty flag 并调用 `invalidate()`；尺寸变化要更新两个节点的位置。节点长期不再使用时可调用 `discardDisplayList()` 及时释放 DisplayList 持有的资源。

RenderNode 的 translation、scale、rotation 和 alpha 属性可以在不重录内容 DisplayList 的情况下更新。强制 `setUseCompositingLayer(true, paint)` 仍会增加合成 layer，公开文档把默认 `false` 作为推荐值；应由特效或测量结果驱动。

## Perfetto：区分 UI 记录、RenderThread 与显示出口

系统 trace 不会自动为每个自定义 View 生成稳定的 `onDraw` slice 名。`debug.hwui.profile` 面向 Profile HWUI Rendering 柱状图，也不能替代 View 级 trace。定位目标 View 时，可以在热方法外包一层应用 trace section。

下面的 instrumentation 给 `onDraw()` 添加可在 Perfetto 中搜索的区间，`finally` 保证异常路径也关闭 section。

```java
@Override
protected void onDraw(Canvas canvas) {
    Trace.beginSection("WaveformView#onDraw");
    try {
        drawGrid(canvas, mContentBounds, mGridPaint);
        canvas.drawPath(mWavePath, mWavePaint);
    } finally {
        Trace.endSection();
    }
}
```

录制时启用目标应用的 atrace section，以及 `view`、`gfx`、`hwui`、调度和 FrameTimeline 数据。性能判断按四段进行：

1. `WaveformView#onDraw` 长：检查应用绘制代码、CPU Bitmap、文字布局、Path 构建和同步等待。
2. UI 记录正常，RenderThread `DrawFrame` 长：继续区分 RenderThread CPU、runnable 等待、`dequeueBuffer`、Skia / GPU 工作和 fence，不能只写成“GPU 慢”。
3. `queueBuffer()` 之前正常，目标 layer 的 `BufferTX` / latch 晚：检查 BLAST、transaction readiness 和 acquire fence。
4. App 与 latch 都按时，actual present 仍超时：检查 SurfaceFlinger composition、HWC / DisplayHAL 和 present timing。

对象分配要用 allocation recording 找调用栈，再与同一时间窗的 GC、main thread 状态和 FrameTimeline 对齐。HeapTaskDaemon 有 GC 工作只说明进程在回收；没有主线程暂停或资源竞争证据时，不能把该帧直接归因给 `onDraw()` 分配。

## 验收清单

- `onMeasure()` 的昂贵计算是否由完整输入保护，数据只改颜色时有没有误调 `requestLayout()`。
- `onLayout()` 是否依赖 child 尺寸、可见性、margin 和 layout direction，是否在 layout 内再次请求 layout。
- `onDraw()` 是否含临时对象、格式化、同步 I/O、Bitmap CPU 绘制或逐帧重建不变几何。
- 默认 `LAYER_TYPE_NONE` 是否已经满足需求；hardware / software layer 是否有明确场景、开启区间和内存证据。
- `setWillNotDraw(true)` 是否只用于没有自身视觉内容的 ViewGroup。
- 自绘动画是否使用显示帧节奏，并在 detach、不可见和终止状态停止。
- 手动 RenderNode 是否把独立更新区域拆开，并为软件 Canvas 保留正确输出。
- UI Thread、RenderThread、BLAST、SurfaceFlinger、HWC 与 actual present 是否用同一帧证据关联。

## 源码与文档

- [Android 17 `View.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/View.java)：`requestLayout()`、invalidation、layer type、`setWillNotDraw()` 与 View RenderNode 更新。
- [Android 17 `ViewRootImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java) 与 [`ThreadedRenderer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ThreadedRenderer.java)：traversal、measure / layout / draw 与 HWUI 同步入口。
- [Android 17 `RenderNode.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/RenderNode.java)、[`RecordingCanvas.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/RecordingCanvas.java) 与 [`HardwareRenderer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/HardwareRenderer.java)：DisplayList 记录、节点属性与 UI 到 RenderThread 的边界。
- [Optimize a custom view](https://developer.android.com/develop/ui/views/layout/custom-views/optimizing-view)：热路径、分配和 layout traversal 的官方建议。
- [Hardware acceleration](https://developer.android.com/topic/performance/hardware-accel)：DisplayList 模型、Canvas API 支持表和 View layer 契约。
- [`View` API](https://developer.android.com/reference/android/view/View) 与 [`RenderNode` API](https://developer.android.com/reference/android/graphics/RenderNode)：dirty rectangle、动画刷新、公开 RenderNode 和软件 Canvas 边界。
- [Slow rendering](https://developer.android.com/topic/performance/vitals/render) 与 [Perfetto system tracing](https://perfetto.dev/docs/getting-started/system-tracing)：UI 记录、RenderThread、GC 和 system trace 的观测入口。
