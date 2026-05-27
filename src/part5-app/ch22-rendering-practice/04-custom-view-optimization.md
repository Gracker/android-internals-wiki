---
title: "自定义 View 性能优化"
chapter: "22.4"
section: "22.4"
status: ready-for-review
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
related_chapters: ["22.1", "2.5", "2.7", "2.10", "7.12"]
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed-lite
last_task2b_lite_at: "2026-05-27"
reviewed_by: openclaw-task6
reviewed_date: "2026-05-27"
task6_result: pass-light-edit
task9_result: auto-fixed
last_task2b_at: "2026-05-13T23:35:47+08:00"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-27"
last_task9_at: "2026-05-27T12:21:00+08:00"
task6_reviewed_date: "2026-05-27"
task6_review_notes: "2026-05-27 12:06 Task6 revisiting：pass-light-edit。移除自动发现编辑前缀，压掉两处评价性表达；L1 禁用词与高频词扫描无命中；无新增 L3/L4 回炉项，送 Task9 复审。"
last_task6_review_log: "logs/review/2026-05-27-12-review.md"
last_task6_at: "2026-05-27T12:06:00+08:00"
task9_review_notes: "2026-05-27 task9 deep-review: auto-fixed。修正 GC 观测归因、硬件加速 Canvas API 版本边界、debug.hwui.profile/Perfetto 观测口径与 onDraw invalidate 表述；回到 Task6 复审。"
last_task2b_verifier_at: "2026-05-27T11:44:00+08:00"
task2b_verifier_result: ready-for-task6
last_task9_autofix_at: "2026-05-27"
---
# 自定义 View 性能优化

自定义 View 是 Android 开发中最灵活的 UI 扩展手段，也是性能问题的高发区。一条 onDraw() 里多了几行对象分配，就可能在大列表滑动场景中触发每秒 60-120 次的 GC 压力；一次 invalidate() 没有指定脏区域，就会让整棵 View 树重绘。

本节聚焦自定义 View 的四个性能瓶颈：绘制管线开销、对象分配、硬件加速适配、重绘范围控制。每个环节都给出可观察的指标和可执行的改法。

## onMeasure / onLayout / onDraw 性能原则

### 三者的调用频率差异

自定义 View 的 onMeasure()、onLayout()、onDraw() 不是等权重的。onDraw() 的调用频率远高于前两者——任何一次 invalidate() 或父容器布局变化都可能触发 onDraw()，而 onMeasure() 只在布局请求（requestLayout()）时触发，onLayout() 只在布局尺寸变化时触发。

在滑动列表中，一个自定义 View 可能每帧都走一次 `onDraw()`，但 `onMeasure()` 和 `onLayout()` 只在条目进入/离开屏幕时才执行。

**优化优先级**：`onDraw()` > `onLayout()` > `onMeasure()`。把 `onDraw()` 的优化做完，再做 `onLayout()` 的布局计算缓存。

### onMeasure 的常见问题

`onMeasure()` 的性能问题集中在两个场景：

1. **循环测量**：父容器在 `UNSPECIFIED → AT_MOST → EXACTLY` 多次调用 `measure()`。自定义 ViewGroup 如果在 `onMeasure()` 中对子 View 做了多次 `measure()` 调用（典型场景：先测一次拿宽度，再根据宽度决定高度），测量成本翻倍。解法是用一次测量 + `MeasureSpec` 推算代替两次 `measure()` 调用。

2. **测量结果未缓存**：`onMeasure()` 里的中间计算结果（如文字宽度、子 View 总高度）如果每帧重新计算，就是浪费。把结果存到成员变量里，只在尺寸参数变化时重新计算。

```java
// View.java 中 onMeasure 的典型重写
@Override
protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
    int widthMode = MeasureSpec.getMode(widthMeasureSpec);
    int widthSize = MeasureSpec.getSize(widthMeasureSpec);

    // 只在尺寸变化时重新计算
    if (widthSize != mLastMeasuredWidth) {
        mCachedContentWidth = calculateContentWidth(widthSize);
        mLastMeasuredWidth = widthSize;
    }

    setMeasuredDimension(
        resolveSize(mCachedContentWidth, widthMeasureSpec),
        resolveSize(mCachedContentHeight, heightMeasureSpec)
    );
}
```

### onLayout 的注意事项

`onLayout()` 的性能问题通常和 `onMeasure()` 耦合。如果 `onMeasure()` 已经缓存了子 View 的位置，`onLayout()` 只需要读缓存直接设置：

```java
@Override
protected void onLayout(boolean changed, int l, int t, int r, int b) {
    // 如果 measure 阶段已缓存位置，直接使用
    for (int i = 0; i < getChildCount(); i++) {
        View child = getChildAt(i);
        child.layout(mCachedPositions[i].left, mCachedPositions[i].top,
                     mCachedPositions[i].right, mCachedPositions[i].bottom);
    }
}
```

关键点：`onLayout()` 的 `changed` 参数表示父容器给的本 View 尺寸是否变化，但子 View 的位置是否需要重新排列取决于自己的布局逻辑。不要因为 `changed == false` 就跳过所有子 View 的 `layout()` 调用——子 View 的可见性、边距变化同样需要处理。

## Canvas 绘制优化：避免在 onDraw 中分配对象

这条规则在高频绘制场景里通常最先检查。

### 为什么 onDraw 不能分配对象

硬件加速模式下（Android 4.0+ 默认开启），onDraw() 的 Canvas 参数是 RecordingCanvas（AOSP: frameworks/base/libs/hwui/RecordingCanvas.cpp）。每次 onDraw() 调用，系统会把绘制命令录制到 DisplayList 中，由 RenderThread 在 GPU 上回放执行。

如果 onDraw() 里创建了 Paint、Path、Rect、Bitmap 等对象，这些对象会在每帧的录制过程中分配，在 GC 回收时造成内存抖动。Perfetto 里的表现通常先落在 App 进程的 `main` / `HeapTaskDaemon` GC slice 上；这些暂停会挤占 `Choreographer#doFrame` 的时间窗口，进而让 RenderThread 更晚拿到要回放的 DisplayList。

一个每帧分配 2-3 个 Paint 对象的自定义 View，在 120fps 设备上每秒分配 240-360 个短命对象。这在低端设备上会导致明显的帧率不稳定。

### 实操规则

**所有绘制用的对象都在构造函数或 `init()` 方法中创建，`onDraw()` 只使用成员变量。**

```java
public class WaveformView extends View {
    private final Paint mWavePaint;
    private final Paint mGridPaint;
    private final Path mWavePath;
    private final RectF mBounds;

    public WaveformView(Context context, AttributeSet attrs) {
        super(context, attrs);
        mWavePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        mWavePaint.setStyle(Paint.Style.STROKE);
        mWavePaint.setStrokeWidth(2f);

        mGridPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        mGridPaint.setColor(0x40FFFFFF);

        mWavePath = new Path();
        mBounds = new RectF();
    }

    @Override
    protected void onDraw(Canvas canvas) {
        // 只使用成员变量，零分配
        mWavePath.reset();
        mBounds.set(0, 0, getWidth(), getHeight());

        // 绘制网格
        drawGrid(canvas, mBounds, mGridPaint);

        // 绘制波形
        buildWavePath(mWavePath, mBounds);
        canvas.drawPath(mWavePath, mWavePaint);
    }
}
```

### 容易忽略的分配点

以下操作看似无害，但在 onDraw() 中调用会产生隐式对象分配：

| 操作 | 分配的对象 | 替代方案 |
|------|-----------|---------|
| `String.format()` 在 `drawText()` 中 | `String` + 内部 `Formatter` | 预格式化文本，存为成员变量 |
| `canvas.drawText(String.valueOf(value), ...)` | `String` | 用 `Integer.toString()` 预转换 |
| `new float[]` / `new int[]` 传给 `drawLines()` / `drawBitmapMesh()` | 数组 | 复用成员数组 |
| `paint.setColor(Color.parseColor("#FF5722"))` | `substring` + 颜色字符串解析 | 构造函数中解析一次，保存 `int` 色值 |

`canvas.save()` / `restore()` 本身不是 Java 对象分配来源；它的成本主要来自 Canvas 状态栈和裁剪/变换状态管理。现代 API 中不要再推荐带 save flags 的旧重载，控制最小必要保存范围即可。

### 检测方法

在 Android Studio Profiler 的 Memory 面板中，按自定义 View 的类名过滤分配。正常情况下，自定义 View 在 `onDraw()` 中的分配数应为 0。如果看到每帧都有来自 `onDraw()` 调用栈的分配，逐个追踪来源。

Perfetto 里可以用以下 SQL 查到 `onDraw()` 中对象分配引发的 GC 活动。注意 GC 暂停的是分配线程（通常是 main thread / UI thread 的 `doFrame` 阶段），不是 RenderThread；需要按进程范围过滤，并与 `Choreographer#doFrame` 时间窗口关联：

```sql
-- 查询目标进程中的 GC slice，关联 doFrame 时间窗口
SELECT s.name, s.ts, s.dur, t.name AS thread_name
FROM slice s
JOIN thread_track tt ON s.track_id = tt.id
JOIN thread t ON tt.utid = t.utid
JOIN process p ON t.upid = p.upid
WHERE p.name = '${YOUR_APP}'
  AND (s.name GLOB '*GC*' OR s.name GLOB '*HeapTaskDaemon*')
  AND t.name IN ('main', 'HeapTaskDaemon')
ORDER BY s.ts DESC
LIMIT 30
```

## 硬件加速与 Layer 使用

### 硬件加速下的自定义 View 行为

硬件加速模式下，Canvas 的绘制命令不会直接执行，而是录制到 DisplayList 中（详见 2.5 节）。这个模式带来三个行为差异：

1. onDraw() 不是直接在屏幕上画，而是往 DisplayList 里追加命令
2. 如果 View 的绘制内容没变（没有 invalidate()），系统直接复用上一帧的 DisplayList，跳过整个 onDraw() 调用
3. Canvas 的部分 API 在硬件加速下不支持，会静默忽略或降级处理

硬件加速兼容列表是版本相关的，不能把 Android 3.x 时代的 unsupported 清单直接套到 Android 10+。官方表中 `clipPath()` 从 API 18 支持，`drawPicture()` 从 API 23 支持，`drawVertices()` 从 API 29 支持；本节覆盖的 Android 10+ 范围内，这几类调用不应再按“硬件加速不支持”处理。仍需要逐项核对的是表中标记为不支持或有版本边界的 Paint / Xfermode 行为，例如 `setLinearText()`、`setMaskFilter()`，以及旧 API 上的 `PathEffect`、非文字阴影等差异。

### setLayerType 的使用时机

`setLayerType()` 不是全局硬件加速开关；它在单个 View 维度选择无 layer / hardware layer / software layer。`LAYER_TYPE_SOFTWARE` 会让该 View 走软件绘制 fallback，即使窗口整体仍开启硬件加速。

| Layer Type | 缓存位置 | 适用场景 | 代价 |
|-----------|---------|---------|------|
| `LAYER_TYPE_NONE` (默认) | 无缓存 | 内容频繁变化 | 每帧重绘 |
| `LAYER_TYPE_HARDWARE` | GPU 纹理 | 复杂但静态的绘制内容 | 占用 GPU 内存 |
| `LAYER_TYPE_SOFTWARE` | Bitmap (CPU) | 需要关闭硬件加速的局部场景 | 内存占用 + CPU 绘制 |

`LAYER_TYPE_HARDWARE` 的正确用法：当一个自定义 View 的绘制非常复杂（比如多路径叠加、渐变、阴影），但内容不频繁变化时，开启硬件 Layer 可以把绘制结果缓存为 GPU 纹理。后续帧直接用纹理合成，跳过 `onDraw()`。

```java
// 复杂但静态的绘制 → 开启硬件 Layer
setLayerType(LAYER_TYPE_HARDWARE, null);

// 内容发生变化时，手动触发更新
public void updateContent(Data newData) {
    mData = newData;
    invalidate(); // 会重新执行 onDraw 并更新纹理
}
```

**错误用法**：对频繁变化的 View（如动画、实时数据可视化）开启 `LAYER_TYPE_HARDWARE`。每帧 `invalidate()` 都会导致纹理重建，比不缓存更慢。

动画场景的 Layer 使用模式（详见 22.5 节）：

```java
// 动画开始前临时开启
view.setLayerType(View.LAYER_TYPE_HARDWARE, null);
ObjectAnimator animator = ObjectAnimator.ofFloat(view, "alpha", 0f, 1f);
animator.addListener(new AnimatorListenerAdapter() {
    @Override
    public void onAnimationEnd(Animator animation) {
        // 动画结束后恢复
        view.setLayerType(View.LAYER_TYPE_NONE, null);
    }
});
animator.start();
```

### View.setWillNotDraw

如果一个自定义 ViewGroup 不需要绘制自身内容（只负责排列子 View），设置 `setWillNotDraw(true)` 可以让系统跳过它的 `onDraw()` 调用，减少一次不必要的绘制回调。

```java
// 纯布局容器 → 跳过绘制
public class FlowLayout extends ViewGroup {
    public FlowLayout(Context context, AttributeSet attrs) {
        super(context, attrs);
        setWillNotDraw(true); // 没有自身绘制内容
    }
}
```

如果后续需要绘制背景、调试辅助线等，需要重新设置为 `false`。

## invalidate 范围控制

### invalidate() vs postInvalidateOnAnimation()

`invalidate()` 只有一个行为：标记整个 View 需要重绘。硬件加速模式下（API 21+），View/RenderNode 的内部 damage 机制负责决定哪些区域需要重新录制 DisplayList，`invalidate(Rect)` / `invalidate(int, int, int, int)` 已被标记为 deprecated，传入的脏矩形参数会被忽略。

> [已验证: AOSP android-16.0.0_r1, View.java `invalidate(Rect)` 注释明确标注 "Passed dirty rectangle is ignored since API 21"。]

| 方法 | 重绘范围 | 线程 | 适用场景 |
|------|---------|------|----------|
| `invalidate()` | 整个 View | UI 线程 | 内容变化 |
| `postInvalidateOnAnimation()` | 整个 View | 任意线程 | 在下一帧动画时刷新 |

在 API 21 之前的软件绘制路径中，`invalidate(Rect)` 的脏区域合并机制（`ViewRootImpl.invalidateRectOnScreen()`）能减少重绘范围。但现代 Android 默认硬件加速，这条路径已不再适用。

### invalidate 与 RenderNode damage

硬件加速模式下，调用 `invalidate()` 会触发 View 对应的 RenderNode 标记为 needs-update。后续 `performDraw()` 阶段只重新录制被标记的 RenderNode，未变化的子树保持缓存。这是硬件加速管线中控制重绘范围的主要机制——不是通过脏矩形，而是通过 RenderNode 粒度的 DisplayList 更新。

对于需要更细粒度控制的多层内容，可以用 `RenderNode` 手动拆分静态层和动态层（见本章末尾 RenderNode 小节）。

### requestLayout() vs invalidate()

这两者会触发不同范围的重新计算：

- invalidate()：标记 View 需要重绘，触发 onDraw()
- requestLayout()：标记 View 需要重新测量和布局，触发 onMeasure() + onLayout() + onDraw()

`requestLayout()` 的调用会沿 View 树向上冒泡到 `ViewRootImpl`，触发完整的 `performTraversals()`（measure → layout → draw）。如果只需要重绘内容，不要调 `requestLayout()`。

```java
// ❌ 只需要重绘却触发了完整布局
public void setColor(int color) {
    mColor = color;
    requestLayout(); // 多余！尺寸没变
}

// ✅
public void setColor(int color) {
    mColor = color;
    invalidate(); // 只重绘
}
```

### onDraw 中不要调 invalidate

在 `onDraw()` 中调用 `invalidate()` 会造成当前帧绘制未完成就标记下一帧重绘，形成连续重绘循环。如果需要持续动画效果，用 `postInvalidateOnAnimation()` 或 `ValueAnimator`：

```java
// ❌ 永远不要这样写
@Override
protected void onDraw(Canvas canvas) {
    drawFrame(canvas, mFrameIndex++);
    invalidate(); // 持续触发下一帧重绘
}

// ✅ 用 Animator 控制帧率
private ValueAnimator mAnimator;

public void startAnimation() {
    mAnimator = ValueAnimator.ofInt(0, TOTAL_FRAMES);
    mAnimator.setRepeatCount(ValueAnimator.INFINITE);
    mAnimator.setDuration(FRAME_DURATION_MS * TOTAL_FRAMES);
    mAnimator.addUpdateListener(a -> invalidate());
    mAnimator.start();
}
```



## ViewCompat.postInvalidateOnAnimation 的兼容性

`postInvalidateOnAnimation()` 在 API 16 以下的行为是 `postInvalidate()`，即延迟 16ms 而非等到下一个 VSync。`ViewCompat.postInvalidateOnAnimation()` 提供了向后兼容。当前 Android 10+ 的目标版本下这不是问题，但在维护旧版本兼容时需要注意。

[来源: AOSP View.java 源码注释]

## RenderNode 与自定义 View

Android 10 (API 29) 引入了公开的 `RenderNode` API。自定义 View 可以利用 `RenderNode` 把复杂的绘制内容拆成多个独立节点，每个节点单独缓存和更新。这在以下场景有收益：

- 自定义 View 中有一块静态背景和一块动态前景，前景变化时不影响背景的 `DisplayList`
- 多层叠加的绘制内容，各层的更新频率不同

```java
// Android 10+ 使用 RenderNode 拆分绘制层
private RenderNode mBackgroundNode;
private RenderNode mForegroundNode;
private boolean mBackgroundRecorded = false;

@Override
protected void onSizeChanged(int w, int h, int oldw, int oldh) {
    super.onSizeChanged(w, h, oldw, oldh);
    // 尺寸变化时重新录制背景
    mBackgroundRecorded = false;
}

@Override
protected void onDraw(Canvas canvas) {
    // 确保在硬件加速 Canvas 上操作
    if (!canvas.isHardwareAccelerated()) return;

    if (mBackgroundNode == null) {
        mBackgroundNode = new RenderNode("background");
        mForegroundNode = new RenderNode("foreground");
    }

    // 尺寸变化时重新录制静态背景
    if (!mBackgroundRecorded) {
        mBackgroundNode.setPosition(0, 0, getWidth(), getHeight());
        RecordingCanvas bgCanvas = mBackgroundNode.beginRecording();
        try {
            drawBackground(bgCanvas);
        } finally {
            mBackgroundNode.endRecording();
        }
        mBackgroundRecorded = true;
    }

    // 背景 RenderNode 直接提交，不重绘
    canvas.drawRenderNode(mBackgroundNode);

    // 前景每帧更新
    mForegroundNode.setPosition(0, 0, getWidth(), getHeight());
    RecordingCanvas fgCanvas = mForegroundNode.beginRecording();
    try {
        drawForeground(fgCanvas);
    } finally {
        mForegroundNode.endRecording();
    }
    canvas.drawRenderNode(mForegroundNode);
}
```

[已验证: AOSP android-16.0.0_r1, frameworks/base/graphics/java/android/graphics/RenderNode.java。`setPosition()` 设定 RenderNode 尺寸，默认为 0；`endRecording()` 放入 try/finally 防止异常时录制状态泄漏。]

## 扩展

### 🔸 性能自检清单

自定义 View 上线前的性能检查项：

1. `onDraw()` 零对象分配（Android Studio Profiler Memory 面板确认）
2. 静态内容使用 `LAYER_TYPE_HARDWARE` 缓存或 `RenderNode` 分离
3. 多层内容用 `RenderNode` 拆分静态层和动态层，避免全量重录 DisplayList
4. 纯布局容器设置 `setWillNotDraw(true)`
5. 颜色、文字、路径等不变参数在构造函数中初始化
6. 动画场景用临时 `LAYER_TYPE_HARDWARE`，结束即恢复
7. 不在 `onDraw()` 中调用 `invalidate()` 或 `requestLayout()`

### 🔸 Perfetto 观测自定义 View 绘制耗时

在 Perfetto trace 中定位自定义 View 的绘制耗时：

1. 找到 `UI Thread` 上的 `performDraw` → `draw` slice
2. `debug.hwui.profile=true` 对应的是 Profile HWUI / GPU Rendering 柱状图，不能保证在 Perfetto 中自动生成每个自定义 View 的 `onDraw` slice。要定位具体 View，优先在自定义 View 的 `onDraw()` 周围加 `Trace.beginSection()` / `Trace.endSection()`，录制时启用 `view` / `gfx` / `hwui` atrace 类别
3. 关注 `RenderThread` 上的 `DrawFrame` 耗时——如果 `DrawFrame` 远大于 `UI Thread` 的 `draw`，说明 `DisplayList` 回放到 GPU 的阶段是瓶颈，需要减少绘制命令数量或降低绘制复杂度

```sql
-- 查询每帧 DrawFrame 耗时（微秒）
SELECT
  (slice.ts / 1000000) as ts_ms,
  slice.dur / 1000 as dur_us,
  slice.name
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread ON thread_track.utid = thread.utid
WHERE thread.name = 'RenderThread'
  AND slice.name = 'DrawFrame'
ORDER BY slice.ts DESC
LIMIT 50
```
