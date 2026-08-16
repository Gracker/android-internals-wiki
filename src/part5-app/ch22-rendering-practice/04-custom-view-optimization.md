---
title: "自定义 View 性能优化"
chapter: "22.4"
section: "22.4"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "AOSP android-17.0.0_r1; Android Developers hardware acceleration docs updated 2026-05-19"
confidence: high
sources:
  - type: official
    path: "developer.android.com/develop/ui/views/layout/custom-views/optimizing-view"
  - type: official
    path: "developer.android.com/topic/performance/hardware-accel"
  - type: official
    path: "perfetto.dev/docs/getting-started/system-tracing"
  - type: official
    path: "developer.android.com/topic/performance/tracing/custom-events"
  - type: aosp
    path: "frameworks/base/core/java/android/view/View.java"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/RenderNode.java"
tags: [custom-view, ondraw, canvas, hardware-acceleration, invalidate, viewrootimpl, hwui]
related_chapters: ["22.1", "2.5", "2.7", "2.10", "7.10"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: "reviewed"
task2b_state: "fixed"
---
# 自定义 View 性能优化

优化自定义 View，需要查看状态变化触发的整条渲染路径。一次变化可能只触发 draw（绘制），也可能通过 `requestLayout()` 增加 measure（测量）和 layout（摆放）；UI 线程完成 DisplayList（绘制命令记录）后，后续线程和显示系统仍会决定这一帧何时上屏。

平台源码固定到 Android 17 / API 37 / `android-17.0.0_r1`，Linux 内核固定到 `android17-6.18-2026-06_r6`。普通自定义 View 没有独立 Surface，走应用窗口的标准 HWUI（Android 硬件加速 UI 渲染器）路径：`Choreographer#doFrame` 驱动 traversal（一次 View 树遍历），UI 线程更新 RenderNode（保存 View 绘制记录和变换属性的渲染节点）及其 DisplayList，`HardwareRenderer.syncAndDrawFrame()` 再把树状态交给专用渲染线程 RenderThread。

随后，BLAST BufferQueue 提交图形缓冲区，SurfaceFlinger（系统合成服务）完成合成，HWC（Hardware Composer，硬件合成器）参与显示，最终得到实际显示时间。显示后段可结合 [Android View 标准渲染链路](../../part2-performance/ch18-rendering-pipelines/02-android-view-standard.md) 阅读。

## 测量、摆放、绘制：按触发条件判断成本

`onMeasure()`、`onLayout()` 与 `onDraw()` 没有固定的优化优先级。应先用性能 trace（时间轴）判断哪一段执行过多或单次过长：

| 回调 | 常见触发条件 | 应避免的工作 |
| --- | --- | --- |
| `onMeasure()` | `requestLayout()`、父约束变化、挂载到窗口、窗口或配置变化 | I/O、重复解析文本、没有次数上限的多轮子 View 测量 |
| `onLayout()` | 布局请求，或 View 边界变化后仍需重新摆放 | 分配临时坐标对象、重复计算测量阶段已有的几何关系 |
| `onDraw()` | 绘制内容失效、动画、父级绘制或 DisplayList 需要重录 | 对象分配、同步 I/O、每帧重建不变的 Path / Shader |

`MeasureSpec` 把父容器给出的尺寸和模式编码在一个整数中。三种模式分别是固定尺寸的 `EXACTLY`、给出上限的 `AT_MOST`，以及不提供父级上限的 `UNSPECIFIED`。同一组 `MeasureSpec` 在没有强制布局标记时可能命中 `View.measure()` 的缓存，`onMeasure()` 不一定执行。

常规路径中的 `requestLayout()` 会清空当前 View 的测量缓存，设置内部标记 `PFLAG_FORCE_LAYOUT` 与 `PFLAG_INVALIDATED`，并向尚未请求布局的父级传播。若调用发生在布局过程中，`ViewRootImpl.requestLayoutDuringLayout()` 会决定本轮接受还是延后处理，不能把一次调用直接等同于一次完整遍历。最终哪些分支重新测量、摆放和绘制，还取决于标记、约束与窗口状态。

### `onMeasure()` 的缓存必须覆盖完整输入

测量缓存不能只比较宽度。高度 `MeasureSpec`、内边距、数据版本、字体、语言与地区设置、布局方向、子 View 可见性和外边距都可能改变结果。缓存适合保存纯计算得到的几何结果，不能绕过 `setMeasuredDimension()` 或破坏父容器约束。

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

数据、字体、语言与地区设置或布局方向发生变化，并且会影响期望尺寸时，更新 `mContentVersion` 后调用 `requestLayout()`。只改变颜色时不应增加测量版本。自定义 `ViewGroup` 还要为每个子 View 生成正确的 `MeasureSpec`、合并 measured state（子 View 报告的尺寸状态），并处理内边距、外边距和最小尺寸，不能用缓存跳过这些契约。

### `onLayout()` 不能只看 `changed`

`changed` 表示当前 View 的 bounds（`left`、`top`、`right`、`bottom` 四条边界）相对上次是否变化。子 View 的测量尺寸、可见性、外边距、布局方向或业务排序变化时，即使父 View 的边界没变，子 View 位置也可能要更新。测量或几何计算阶段应产出一份与完整输入绑定的坐标缓存，`onLayout()` 只读取这份缓存。

若 trace 显示同一帧发生多轮测量与摆放，要查调用栈和请求源。常见原因包括在 `onLayout()` 中再次调用 `requestLayout()`、父子约束互相依赖、权重或 `wrap_content` 协商，以及 Adapter 更新时同时改变布局参数。

## `onDraw()`：移除热路径分配

硬件加速时，UI 线程把 View 的绘制命令记录到 RenderNode 的 DisplayList。内容没有失效的 View 可以复用已有记录；标为 dirty（绘制内容已过期）的节点才需要重录。RenderThread 消费这些命令并准备窗口缓冲区，`onDraw()` 本身仍在 UI 线程执行。

热路径分配会增加分配器工作、缓存扰动和垃圾回收（GC）负载。少量分配不一定产生可见卡顿，结论要由 allocation recording（对象分配记录）、GC 轨道和帧时间共同证明。应移除可避免的逐帧分配，不能用一个对象数量阈值代替测量。

下面是波形 View 的结构节选：它在构造阶段创建绘制对象，在尺寸或数据变化时更新几何，`onDraw()` 只提交绘制命令；`rebuildWavePath()`、`drawGrid()` 等业务辅助方法没有展开。

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

`Canvas.save()` / `restore()` 管理的是 Canvas 状态栈，不能按 Java 对象分配解释。嵌套 layer（离屏层）、复杂 clip（裁剪）和 transform（几何变换）仍有执行成本，应把状态保存范围限制在需要隔离的绘制段。

## 硬件加速、图层与 `setWillNotDraw`

### 以当前 Canvas 判断绘制后端

`View.isHardwareAccelerated()` 表示 View 所在窗口启用了硬件加速；当前绘制可能仍使用软件 Canvas，例如把 View 画入 Bitmap。绘制代码需要分支时，应检查 `canvas.isHardwareAccelerated()`。

Android 10—17 已支持 `clipPath()`、`drawPicture()` 和 `drawVertices()` 等过去受 API 版本限制的调用，其中 `drawVertices()` 从 API 29 起支持硬件 Canvas。兼容性仍要按当前官方表逐项核对；例如官方表仍把 `Paint.setLinearText()` 和 `setMaskFilter()` 标为不支持。问题可能表现为空白、异常或像素错误，系统不会为所有不支持的调用统一切到软件绘制。

### `LAYER_TYPE_NONE` 仍然复用 DisplayList

`setLayerType()` 控制单个 View 是否增加离屏图层，不控制整个窗口是否硬件加速。

| 类型 | Android 17 语义 | 合适场景 | 主要代价 |
| --- | --- | --- | --- |
| `LAYER_TYPE_NONE` | 正常使用 View 的 RenderNode / DisplayList，不强制离屏缓冲区 | 默认选择 | 无额外图层；内容失效时仍需重录 |
| `LAYER_TYPE_HARDWARE` | 在硬件加速窗口中渲染到硬件纹理 | 复杂子树的短时 alpha / transform 动画，或明确的合成效果 | GPU 内存、创建图层与内容失效后的重新栅格化 |
| `LAYER_TYPE_SOFTWARE` | 子树由 CPU 绘制到 Bitmap，再参与宿主窗口绘制 | 硬件 Canvas 不支持且已验证的局部兼容路径 | Bitmap 内存、CPU 栅格化、纹理上传 |

窗口未启用硬件加速时，`LAYER_TYPE_HARDWARE` 的行为与 `LAYER_TYPE_SOFTWARE` 相同；它不能在单个 View 上开启硬件加速。

静态 View 在默认模式下已经能复用 DisplayList，没有必要仅因“内容复杂”长期强制硬件图层。硬件图层适合内容保持不变、外层 `alpha` / `translation` / `scale` / `rotation` 持续变化的短时动画。动画同时修改 View 内容并频繁 `invalidate()` 时，图层仍要重新栅格化，收益可能消失。栅格化指把绘制命令转换成像素。

`ViewPropertyAnimator.withLayer()` 会在动画前启用硬件图层，并在结束后恢复原来的图层类型。先用 trace 确认属性动画的主要成本来自重复栅格化，再考虑下面的局部优化。

```java
view.animate()
        .alpha(0f)
        .translationY(-view.getHeight() / 4f)
        .setDuration(220L)
        .withLayer()
        .start();
```

硬件图层会占用与 View 面积、像素格式相关的 GPU 资源，大面积 View 尤其要检查内存和 RenderThread。`hasOverlappingRendering()` 只有在 View 内容不存在重叠绘制时才可返回 `false`；错误返回会改变透明度合成结果。

### `setWillNotDraw(true)` 只跳过 ViewGroup 自身绘制

纯布局 `ViewGroup` 可以设置 `setWillNotDraw(true)`，让框架跳过它自己的 `onDraw()`。子 View 仍会通过 `dispatchDraw()` 绘制。容器需要画背景、分隔线、调试标记或其他自身内容时，应清除该标记。

下面只截取容器设置绘制标记的构造函数。完整的非抽象 `ViewGroup` 还必须实现 `onMeasure()` 和 `onLayout()`，这段代码不能单独编译。

```java
public final class FlowLayout extends ViewGroup {
    public FlowLayout(Context context, AttributeSet attrs) {
        super(context, attrs);
        setWillNotDraw(true);
    }
}
```

给 ViewGroup 设置背景时，框架可能调整绘制标记。`setWillNotDraw(true)` 不能覆盖所有背景行为；增加自身绘制后应明确改为 `false` 并验证结果。

## `invalidate()`、动画刷新与 `requestLayout()`

| API | 调用线程与时机 | 适用变化 | Android 17 边界 |
| --- | --- | --- | --- |
| `invalidate()` | UI 线程，安排后续绘制 | 像素内容、颜色、Path、Drawable | 标记 View 绘制内容失效，并向父级传播重绘区域（damage） |
| `postInvalidateOnAnimation()` | 挂载到窗口（attach）后可从非 UI 线程调用，在下一动画时间步派发 | 与显示帧节奏对齐的自绘动画 | 未 attach 时没有 `AttachInfo`，调用不会安排刷新 |
| `requestLayout()` | UI 线程，向父级传播布局请求 | 期望尺寸、子 View 尺寸或位置 | 清测量缓存，设置强制布局与失效标记，再安排 View 树遍历 |

API 21 起，`invalidate(Rect)` 和四坐标重载传入的 dirty rectangle（调用方指定的局部脏区域）会被忽略，两个公开 API 也已弃用。Android 17 的 `View.java` 内部仍会传播重绘区域，并按 RenderNode 更新 DisplayList；应用侧应调用无参 `invalidate()`，再通过拆分 View 或 RenderNode 改变重录粒度。

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

`requestLayout()` 不保证自动补齐所有业务绘制状态，因此尺寸与像素都变化时可以同时调用两者。若文字变化但固定边界与现有基线能容纳新内容，只需重建文字布局并调用 `invalidate()`；是否调用 `requestLayout()` 由尺寸契约决定。

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

这段骨架只展示从窗口分离时的停止逻辑。实际组件还要在不可见和业务终止时更新 `mRunning`；若改用 Animator，也要在对应生命周期节点取消动画。

`ValueAnimator` 能提供基于时钟的进度和取消机制，但它的更新回调仍可能每帧触发重绘。选择 Animator 是为了使用明确的时间模型和生命周期，并不会减少刷新次数。

### `ViewCompat.postInvalidateOnAnimation()` 的版本位置

平台 `postInvalidateOnAnimation()` 从 API 16 提供。本文适用范围为 Android 10—17，可以直接调用平台 API。若这段代码还要共享给 API 15 或更低的项目，可考虑 `ViewCompat.postInvalidateOnAnimation()`，但要先确认项目采用的 AndroidX Core 版本仍支持该 `minSdk`。兼容层的选择不会改变 Android 17 的调度语义。

## 手动 `RenderNode`：按更新频率划分节点

公开 `RenderNode` 从 API 29 提供。每个 View 已经由框架持有一个 RenderNode，手动增加节点只适合自定义 View 内面积较大、更新频率不同且能独立记录的区域。若小图元很多、每帧全部变化，或软件 Canvas 必须完整支持，额外节点的管理成本可能超过复用收益。

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

内容更新时设置对应的失效标记并调用 `invalidate()`；尺寸变化要更新两个节点的位置。节点长期不再使用时可以调用 `discardDisplayList()` 释放 DisplayList 持有的原生资源。系统发现节点不再被绘制时也可能自动调用该方法，显式释放适合生命周期由业务代码明确控制的节点。

RenderNode 的 `translation`、`scale`、`rotation` 和 `alpha` 属性可以在不重录 DisplayList 的情况下更新。`setUseCompositingLayer(true, paint)` 会强制增加中间合成缓冲区，公开文档推荐保留默认值 `false`。当中间层能降低开销，或 `alpha` 与重叠绘制的组合要求使用中间层时，RenderNode 会自行建立合成层。只有特效要求或测量结果能证明收益时才应强制开启。

## Perfetto：区分 UI 记录、RenderThread 与显示出口

系统 trace 不会自动为每个自定义 View 生成稳定的 `onDraw` slice（有起止时间的工作区间）。`debug.hwui.profile` 用于生成 Profile HWUI Rendering 柱状图，不能替代 View 级 trace。定位目标 View 时，可以用自定义区间（trace section）包住热方法。

下面的埋点代码给 `onDraw()` 添加可在 Perfetto 中搜索的区间，`finally` 保证发生异常时也会关闭 section。

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

录制时要让配置收集目标进程的应用 trace section，并启用 `view`、`gfx`、`hwui`、线程调度和 FrameTimeline 数据。Macrobenchmark 会自动收集自定义区间；使用 systrace 命令行时要通过 `-a <package>` 指定应用。FrameTimeline 用于把应用帧与 SurfaceFlinger 的实际显示结果对应起来。性能判断按四段进行：

1. `WaveformView#onDraw` 长：检查应用绘制代码、CPU Bitmap、文字布局、Path 构建和同步等待。
2. UI 记录正常，RenderThread `DrawFrame` 长：先区分 CPU 执行与 runnable 时间，后者表示线程已经就绪但还在等待 CPU。然后检查 `dequeueBuffer`（申请可写缓冲区）、Skia 渲染库 / GPU 工作和 fence（跨 CPU、GPU、显示设备传递完成状态的同步对象），不能只写成“GPU 慢”。
3. `queueBuffer()` 之前正常，目标图层的 `BufferTX` / latch 晚：检查 BLAST、transaction readiness（事务依赖是否就绪）和 acquire fence（生产者是否已写完缓冲区）。latch 表示 SurfaceFlinger 选中并接收本帧缓冲区。
4. 应用与 latch 都按时，actual present（实际显示时间）仍超时：检查 SurfaceFlinger 合成、HWC、Display HAL（显示硬件抽象层）和 present timing。

对象分配要用 allocation recording 找调用栈，再与同一时间窗的 GC、主线程状态和 FrameTimeline 对齐。HeapTaskDaemon 是 Android Runtime 的后台堆任务线程；它出现 GC 工作只说明进程正在回收内存。没有主线程暂停或资源竞争证据时，不能把该帧直接归因给 `onDraw()` 分配。

## 验收清单

- `onMeasure()` 的昂贵计算是否由完整输入保护，数据只改颜色时有没有误调 `requestLayout()`。
- `onLayout()` 是否依赖子 View 尺寸、可见性、外边距和布局方向，是否在摆放过程中再次请求布局。
- `onDraw()` 是否含临时对象、格式化、同步 I/O、Bitmap CPU 绘制或逐帧重建不变几何。
- 默认 `LAYER_TYPE_NONE` 是否已经满足需求；硬件 / 软件图层是否有明确场景、开启区间和内存证据。
- `setWillNotDraw(true)` 是否只用于没有自身视觉内容的 ViewGroup。
- 自绘动画是否使用显示帧节奏，并在从窗口分离、不可见和终止状态停止。
- 手动 RenderNode 是否让独立更新区域分别记录，并为软件 Canvas 保留正确输出。
- UI 线程、RenderThread、BLAST、SurfaceFlinger、HWC 与 actual present 是否用同一帧证据关联。

## 源码与文档

- [Android 17 `View.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/View.java)：`requestLayout()`、绘制失效、图层类型、`setWillNotDraw()` 与 View RenderNode 更新。
- [Android 17 `ViewRootImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java) 与 [`ThreadedRenderer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ThreadedRenderer.java)：View 树遍历、测量 / 摆放 / 绘制与 HWUI 同步入口。
- [Android 17 `RenderNode.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/RenderNode.java)、[`RecordingCanvas.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/RecordingCanvas.java) 与 [`HardwareRenderer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/HardwareRenderer.java)：DisplayList 记录、节点属性与 UI 到 RenderThread 的边界。
- [Optimize a custom view](https://developer.android.com/develop/ui/views/layout/custom-views/optimizing-view)：热路径、分配和布局遍历的官方建议。
- [Hardware acceleration](https://developer.android.com/topic/performance/hardware-accel)：DisplayList 模型、Canvas API 支持表和 View 图层契约。
- [`View` API](https://developer.android.com/reference/android/view/View) 与 [`RenderNode` API](https://developer.android.com/reference/android/graphics/RenderNode)：dirty rectangle、动画刷新、公开 RenderNode 和软件 Canvas 边界。
- [Slow rendering](https://developer.android.com/topic/performance/vitals/render)、[Perfetto system tracing](https://perfetto.dev/docs/getting-started/system-tracing) 与 [Define custom events](https://developer.android.com/topic/performance/tracing/custom-events)：UI 记录、RenderThread、GC、系统 trace 与应用自定义区间的观测入口。
