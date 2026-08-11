---
title: "View 体系性能优化：布局层级、inflate 与 measure/layout 开销"
chapter: "7.10"
section: "7.10"
status: "finalized"
drafted_date: "2026-04-08"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
last_verified: "2026-04-25"
last_verified_against: "AOSP android-16.0.0_r1 ViewRootImpl / ViewDebug / ViewHierarchyEncoder"
reviewed_date: "2026-06-05"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
confidence: high
sources:
  - type: official
    path: "https://android-developers.googleblog.com/2017/08/understanding-performance-benefits-of.html"
  - type: official
    path: "https://developer.android.com/topic/performance/rendering/optimizing-view-hierarchies"
  - type: aosp
    path: "frameworks/base/core/java/android/view/LayoutInflater.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/View.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/ViewRootImpl.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/Choreographer.java"
tags: [view, layout, inflate, measure, draw, constraintlayout, viewstub, async-inflate, jank]
related_chapters: ["7.1", "7.2", "7.4", "7.5", "2.4", "2.5", "8.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-08"
gap_source: "AOSP结构+官方文档+读者需求"
pipeline_stage: "ready-to-publish"
finalized_date: "2026-06-05"
finalized_by: "openclaw-task6-auto-promote"
task6_state: "reviewed"
task9_state: reviewed
task9_result: auto-fixed
task2b_state: fixed
task2b_result: fixed-lite
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-05"
last_task9_at: "2026-06-05T16:21:00+08:00"
last_task2b_lite_at: "2026-06-04"
last_task2b_at: "2026-06-04T12:57:00+08:00"
last_task6_audit: "2026-06-26"
last_task9_audit: "2026-05-21"
task9_review_notes: "2026-06-05 Task9 auto-fix: ViewTreeObserver 附录从 Android 17 API 37 标题降级为 Android 16 源码边界，避免在 android-17.0.0_r1 tag 未发布时写成 Android 17 新增结论。"
last_task6_at: "2026-06-05T17:22:30"
last_task9_autofix_at: 2026-06-05
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-06
---

# 7.10 View 体系性能优化：布局层级、inflate 与 measure/layout 开销

View UI 在创建、测量和摆放阶段都会占用主线程。分析基线固定为 Android 17 / API 37 / `android-17.0.0_r1`；只有在继续追踪调度、CPU 频率、内存回收或 fence 等内核现象时，才采用 `android17-6.18-2026-06_r6`。View 的布局算法位于 framework，单凭内核 trace 无法解释某个容器为何反复测量。

页面层级值得审查，却不应成为唯一指标。同样数量的节点，简单 `FrameLayout` 与包含权重、文本换行、Drawable 解析、自定义测量逻辑的容器，成本可以相差很大。一次可靠的优化要回答三件事：

- 哪段代码让 View 被创建或再次访问；
- 当前 traversal 访问了哪些子树、访问了几轮；
- 这些工作是否处在用户可感知帧或启动关键路径上。

## 1. 用“节点、访问次数、单节点工作”理解成本

一次布局工作的近似成本可以写成：

> 总成本 ≈ 被访问节点数 × 每个节点的访问次数 × 单次访问成本

这三个乘数分别对应不同问题：

- **被访问节点数**：父容器包含多少可参与当前 pass 的子节点，布局请求传播到了多大的子树；
- **访问次数**：容器是否为了依赖关系、`layout_weight`、最大子项或 layout 期间的新请求再次测量；
- **单次访问成本**：`TextView` 是否重新排版，图片或字体资源是否首次解析，自定义 `onMeasure()` 是否分配对象、查数据库或遍历额外集合。

深层嵌套会增加父链传播、递归调用和容器处理机会，也会放大多 pass 容器的成本。它是一项风险信号，不能单独换算为毫秒，也不存在适用于所有页面的“超过几层就卡”阈值。节点总数、布局算法、更新频率和设备状态要放在同一条 trace 中判断。

60 Hz 的名义 VSync 周期约为 16.67 ms，120 Hz 约为 8.33 ms。这只是显示节拍，不是分给 App 主线程布局的独占 CPU 预算。输入、动画回调、业务代码、View traversal、RenderThread、SurfaceFlinger 和调度延迟共同消耗端到端 deadline。高刷新率下，相同的 4 ms layout 占比更高，但是否丢帧仍应由 FrameTimeline 的 expected/actual timeline 与显示结果确认。

## 2. `LayoutInflater.inflate()` 的三阶段路径

布局 XML 经 AAPT2 编译后，以 binary XML 资源存入 APK；`resources.arsc` 保存资源表与索引，两者负责不同职责。运行时 inflate 仍需解析节点、解析属性、构造对象并组装 View 树，binary XML 没有消除这些工作。

### 2.1 阶段一：读取 XML 与确定上下文

`Resources.getLayout()` 返回解析器后，`LayoutInflater` 找到根标签并读取 `AttributeSet`。每个标签还可能处理：

- `android:theme`，必要时创建 `ContextThemeWrapper`；
- `<include>` 的 layout、theme、id、visibility 与根布局参数覆盖；
- `<merge>`、`<requestFocus>`、`<tag>` 等特殊标签；
- 父容器的 `generateLayoutParams()`。

主题、style 和属性解析会继续访问资源表，View 构造函数还可能加载背景、字体、Drawable、ColorStateList 或兼容资源。把这一段统称为“XML 解析”会漏掉大量可变成本。

### 2.2 阶段二：Factory 链与 View 构造

Android 17 的 `createViewFromTag()` 会先处理主题，再调用 `tryCreateView()`。创建顺序是 `Factory2`、`Factory`、private factory；都返回 `null` 时才进入 inflater 自身的 `onCreateView()` 或全限定类名创建。

下面的节选保留 Android 17 的两个关键分支，省略异常、filter 和 trace 处理：

```java
// frameworks/base/core/java/android/view/LayoutInflater.java
// android-17.0.0_r1，createViewFromTag() 节选
View view = tryCreateView(parent, name, context, attrs);
if (view == null) {
    if (-1 == name.indexOf('.')) {
        view = onCreateView(context, parent, name, attrs);
    } else {
        view = createView(context, name, null, attrs);
    }
}

// android-17.0.0_r1，createView() 节选
Constructor<? extends View> constructor = sConstructorMap.get(name);
if (constructor == null) {
    Class<? extends View> clazz = Class.forName(
            prefix != null ? prefix + name : name,
            false,
            mContext.getClassLoader()).asSubclass(View.class);
    constructor = clazz.getConstructor(mConstructorSignature);
    constructor.setAccessible(true);
    sConstructorMap.put(name, constructor);
}
Object[] args = mConstructorArgs;
args[0] = viewContext;
args[1] = attrs;
View created = constructor.newInstance(args);
```

`sConstructorMap` 是进程内静态缓存；命中前还会通过 `verifyClassLoader()` 检查构造器是否能被当前 Context 的 ClassLoader 使用。源码随后还会为 `ViewStub` 保存同 Context 的 inflater，并在 `finally` 中恢复共享的构造参数数组。缓存减少了重复查找构造器的成本，`Constructor.newInstance()`、View 构造、资源解析和初始化工作仍会发生。

短类名的包前缀由 inflater 类型决定。基础 `LayoutInflater.onCreateView()` 只尝试 `android.view.`；系统的 `PhoneLayoutInflater` 依次尝试 `android.widget.`、`android.webkit.`、`android.app.`，失败后回到基础实现。AppCompat 通过 `Factory2` 创建或替换控件，并处理 context wrapping、主题和 tint。其成本不能靠“多一次 switch”推断，复杂页面应直接测量。

反射也不宜预设为 inflate 的主要耗时。第一次类加载、View 构造、样式解析、字体/Drawable、Factory 逻辑、父容器生成 LayoutParams，以及业务自定义 View 的初始化都可能占主导。采集冷、热两组 trace，才能区分类加载与稳定态成本。

### 2.3 阶段三：递归组装与 `onFinishInflate()`

创建根 View 后，`rInflateChildren()` 递归处理子标签。普通子节点会经历：

1. 创建子 View；
2. 由父 `ViewGroup.generateLayoutParams()` 生成布局参数；
3. 递归创建孙节点；
4. `ViewGroup.addView()` 加入父容器；
5. 子树完成后调用 `onFinishInflate()`。

`inflate(resource, root, false)` 中的 `root` 仍有价值：它为 XML 根节点生成正确的 `LayoutParams`。传 `null` 后再手工 `addView()`，常会丢失父容器专用参数，或者多做一次参数修正。

| 调用形态 | 返回值 | 是否已挂到 `root` | 根布局参数来源 |
|---|---|---:|---|
| `inflate(res, root, true)` | `root` | 是 | `root.generateLayoutParams()` |
| `inflate(res, root, false)` | XML 根 View | 否 | `root.generateLayoutParams()` |
| `inflate(res, null, false)` | XML 根 View | 否 | 无父容器上下文，根参数可能缺失 |

首帧分析时，在 Activity/Fragment 生命周期和 `setContentView` 周围找主线程 CPU 区间，再用方法 trace、app trace section 或 startup benchmark 确认归属。某段 30 ms 主线程忙碌不能仅凭形状认定为 inflate。

## 3. traversal、MeasureSpec 与重复测量

### 3.1 一轮 traversal 不保证三个阶段全部运行

`ViewRootImpl.scheduleTraversals()` 在尚未调度时设置 `mTraversalScheduled`，插入同步屏障，并向 `Choreographer.CALLBACK_TRAVERSAL` 注册 VSync callback。Android 17 使用 `postVsyncCallback()`；callback 到达后移除屏障并进入 `performTraversals()`。

Android 17 的一轮 `Choreographer#doFrame()` 按 `INPUT → ANIMATION → INSETS_ANIMATION → TRAVERSAL → COMMIT` 分发 callback。measure/layout 位于 Traversal 内，前面的输入或动画已经迟到时，即使 layout 本身不长，窗口也可能错过 deadline。Traversal 尾部的 `performDraw()` 还会进入 `ThreadedRenderer.draw()` / `syncAndDrawFrame()`；UI 线程可能等待 RenderThread 完成本帧状态同步，不能把整个 Traversal 或 `doFrame` 时长都记到布局名下。

`performTraversals()` 会根据首帧、`mLayoutRequested`、窗口尺寸、insets、可见性、配置和 relayout 结果决定工作。布局被请求时通常会执行 measure 与 layout；只有绘制失效时可以复用已有尺寸和位置。这里仍有两个限制：

- 同一轮 traversal 中还可能有窗口 relayout、透明区域、insets、pre-draw 和 draw；
- `invalidate()` 与 `requestLayout()` 会共用调度入口，当前窗口的其他状态仍可让 measure/layout 出现在这一轮。

因此，“`invalidate()` 等于 Draw only”只适合作为入门记忆，不能作为 trace 结论。

### 3.2 MeasureSpec 由父规格与子参数共同决定

`MeasureSpec` 把 mode 与 size 编码在一个整数中：

| mode | 含义 |
|---|---|
| `EXACTLY` | 父级要求得到指定尺寸 |
| `AT_MOST` | 子 View 可自行决定，但不得超过上限 |
| `UNSPECIFIED` | 父级不提供上限；常见于某些可滚动方向或离屏测量 |

`match_parent`、`wrap_content` 与固定尺寸不会独立决定 mode。`ViewGroup.getChildMeasureSpec()` 会把父 `MeasureSpec`、padding/margin 和子 `LayoutParams` 组合起来。例如父级为 `AT_MOST` 时，子级 `match_parent` 在 framework 通用算法里得到的仍是 `AT_MOST`；父级为 `EXACTLY` 时才得到对应的 `EXACTLY`。

### 3.3 `measure()` 被调用，不等于 `onMeasure()` 必然执行

Android 17 的 `View.measure()` 会比较新旧 width/height spec、`PFLAG_FORCE_LAYOUT` 和已测尺寸。它还维护按两个 MeasureSpec 组合索引的 `mMeasureCache`。满足条件时可复用测量结果；是否允许 force-layout 路径使用缓存还受 platform flag 控制。

这带来两个分析规则：

- 统计 Java 方法调用次数时，要区分 `measure()` 与自定义 `onMeasure()`；
- 父容器走了第二轮，不代表每个后代都完整重复计算，缓存、规格变化和 force-layout 标志会改变结果。

缓存不能弥补昂贵的布局算法。自定义 View 在输入未变时仍频繁 `requestLayout()`，会清空自己的测量缓存并给父链增加工作。

### 3.4 多 pass 容器的边界

Android 17 `RelativeLayout.onMeasure()` 先按水平依赖排序遍历可见子项，调用 `measureChildHorizontal()`；随后按垂直依赖排序，再调用完整的 `measureChild()`。多数可见子项会在同一次 `onMeasure()` 中收到两次 `measure()`，但第二次是否进入其 `onMeasure()` 还受规格和缓存影响。

`LinearLayout` 的 `layout_weight`、`measureWithLargestChild`、baseline 对齐和交叉轴 `match_parent` 也可能触发重新测量。是否发生、涉及哪些子项，由方向、父规格、剩余空间和参数组合决定。不要把所有 `LinearLayout` 一律归为双 pass。

官方把这类现象称为 double taxation。风险较高的组合包括：

- 多 pass 容器位于页面根部，下面挂着大子树；
- 列表中重复出现同一复杂 item；
- 动画或文本更新持续改变测量输入；
- 多个多 pass 容器嵌套；
- 自定义 `onMeasure()` 在每次调用中分配对象或执行与尺寸无关的工作。

### 3.5 层级优化要看语义

布局变平可以减少中间 ViewGroup，但移除一个容器可能改变 clip、foreground、state propagation、accessibility、touch dispatch、transition name 或 layout semantics。评估时同时记录：

- 节点数与最大深度；
- measure/layout 总时长和 pass 次数；
- TextView、图片、自定义 View 的单节点成本；
- accessibility tree 与点击区域；
- 修改前后的截图、交互和 Macrobenchmark 数据。

一个节点较多但单 pass、更新范围小的页面，可能优于节点较少却反复求解的大子树。优化目标是缩短用户关键路径中的工作，不是追求层级数字。

## 4. `requestLayout()` 与 `invalidate()` 的精确边界

### 4.1 `requestLayout()` 怎样向上走

Android 17 `View.requestLayout()` 会清空该 View 的测量缓存，处理 layout 期间请求，设置 `PFLAG_FORCE_LAYOUT` 与 `PFLAG_INVALIDATED`。父级尚未处于 layout-requested 状态时，请求沿 `ViewParent` 链上传。到达 `ViewRootImpl.requestLayout()` 后，framework 检查线程，设置 `mLayoutRequested = true` 并调度 traversal。

父链传播会在遇到已经标记 layout requested 的父级时停止重复上传。同一 VSync 前的多次请求通常会被 `mTraversalScheduled` 合并为一个已调度 callback，但“合并一次 callback”不保证只有一次 measure/layout：

- 第一次 layout 中出现仍有效的新请求时，`performLayout()` 可以在同一帧执行第二轮 measure/layout；
- 第二轮期间再次请求，会被投递到下一帧，避免无限循环；
- 不同窗口各自拥有 ViewRoot 与 traversal；
- 窗口 relayout、insets 或配置变化还能增加额外测量。

在 `onLayout()`、`OnGlobalLayoutListener` 或数据绑定回调里无条件调用 `requestLayout()`，很容易形成当前帧第二轮与下一帧连续布局。

### 4.2 `invalidate()` 怎样传播绘制失效

`View.invalidate()` 设置 invalidated/dirty 状态，通过父级把失效传到 `ViewRootImpl` 并安排 traversal。硬件加速下，脏矩形参数从 API 21 起不再按旧软件渲染语义使用；framework 与 RenderNode/HWUI 自行维护需要更新的内容。

它表达的是“视觉内容需要更新”，不会主动把尺寸输入改掉。若同一窗口已经有 layout request，或这次属性修改还通过别的代码触发了 `requestLayout()`，同一轮仍会出现 measure/layout。反过来，调用 `requestLayout()` 也不表示每个 View 的 `onMeasure()` 都重算，前述缓存与规格判断仍有效。

| 变化 | 常用信号 | 还要检查 |
|---|---|---|
| 颜色、选中态、自绘内容变化，边界不变 | `invalidate()` | Drawable 是否自行 invalidation；硬件 display list 是否更新 |
| 文本可能换行、字号、padding、LayoutParams 变化 | `requestLayout()`，通常伴随绘制失效 | 新尺寸是否影响父级；TextView 是否已经代为请求 |
| translation、alpha、scale 等属性动画 | 属性 setter / animator | 是否走 RenderNode 快速路径；是否伴随 clip 或布局变化 |
| 添加、删除、显示或隐藏子 View | 由 ViewGroup/API 触发布局 | 影响范围、动画、列表复用 |
| 自定义 View 内部数据变化 | 根据尺寸是否变化选择 | setter 不要无条件同时调用两者 |

`RecyclerView.Adapter.onBindViewHolder()` 中出现 `requestLayout()` 也不能直接判错：内容长度变化可能确需重新测量。应检查同一 item 是否在尺寸不变时重复请求、是否破坏稳定尺寸假设，以及滚动 trace 中 layout 是否越过 deadline。RecyclerView 的专项策略见 [7.8 RecyclerView 性能](08-recyclerview-performance.md)。

## 5. 布局组件的选择边界

### 5.1 `ConstraintLayout`、`FrameLayout`、`LinearLayout`、`RelativeLayout`

| 组件 | 合适场景 | 易放大的成本 |
|---|---|---|
| `FrameLayout` | 少量叠放、单子项容器 | 子项很多时仍要逐项处理；语义能力有限 |
| 无权重 `LinearLayout` | 简单单轴排列 | 嵌套、weight、largest-child、baseline 组合 |
| `ConstraintLayout` | 多方向关系可替代多层嵌套 | 求解器、helper、barrier、ratio、动态约束本身有成本 |
| `RelativeLayout` | 维护既有简单布局 | 水平/垂直依赖排序与多次 child measure |
| 自定义 `ViewGroup` | 规则稳定、可用一次线性遍历表达 | 正确处理 MeasureSpec、RTL、margin、baseline、accessibility 的维护成本 |

Google 2017 年的 ConstraintLayout 博客用一个特定表单对比了嵌套 `RelativeLayout`/`LinearLayout` 与扁平 ConstraintLayout。它能说明该样本中的层级和重复 pass 问题，不能推导任意页面、任意 AndroidX 版本下的固定百分比，也不能证明简单布局都应迁移。当前官方文档仍建议复杂关系优先评估 ConstraintLayout，简单叠放可用 FrameLayout；最终选择应由当前依赖版本和同设备基准决定。

优化 ConstraintLayout 时，先删除冗余 wrapper 和矛盾约束，再观察 solver/measure；不要为了“扁平”把一个清晰的简单容器改成大量动态 ConstraintSet。约束优化选项属于 AndroidX 版本实现，报告中要记录库版本，不能写成 Android 17 framework 行为。

### 5.2 `ViewStub`：把初始成本延后

`ViewStub` 初始状态为 `GONE`、尺寸为 0 且不绘制。调用 `inflate()`，或者把 stub 设为 `VISIBLE`/`INVISIBLE` 时，它同步 inflate 指定资源，从父容器移除自身，并在同一索引放入新 View，沿用 stub 的 LayoutParams。`OnInflateListener` 在新 View 已加入、下一轮 layout 前回调。

下面的 XML 用于延迟创建低概率出现的错误详情：

```xml
<ViewStub
    android:id="@+id/error_details_stub"
    android:inflatedId="@+id/error_details"
    android:layout="@layout/view_error_details"
    android:layout_width="match_parent"
    android:layout_height="wrap_content" />
```

这会降低页面初次 inflate 的对象和资源成本，却把工作移到首次展示时。若用户点击后才在主线程 inflate 大子树，卡顿只会换到交互帧。可以在空闲窗口提前 inflate、用异步 inflater 验证兼容性，或重新设计为更小的子树。`ViewStub` 的 layout 需要能返回单个根 View；`<merge>` 根不能作为它的直接 inflate 结果。

### 5.3 `<merge>` 与 `<include>`

`<include>` 复用 XML 定义，运行时仍会解析和创建被包含内容。被包含布局以 `<merge>` 为根时，子节点会直接加入 include 所在父容器，从而省去没有语义的 wrapper。

下面的布局片段展示 `<merge>` 的典型用途：

```xml
<!-- res/layout/view_profile_actions.xml -->
<merge xmlns:android="http://schemas.android.com/apk/res/android">
    <Button
        android:id="@+id/follow"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content" />

    <Button
        android:id="@+id/message"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content" />
</merge>
```

这个资源只能在有有效 `ViewGroup root` 且 `attachToRoot=true` 的条件下直接 inflate；Android 17 在条件不满足时抛出 `InflateException`。`<merge>` 还意味着这些子项依赖使用方父容器的 LayoutParams 与布局语义，不适合需要独立背景、padding、clip、状态或 accessibility grouping 的根。

`<include>` 上的 LayoutParams 可以覆盖被包含根的值。官方资源文档要求要让其他 layout 属性覆盖生效时，同时声明 `android:layout_width` 与 `android:layout_height`。迁移 wrapper 前应检查 ID、transition、binding 生成结果和点击/无障碍分组。

## 6. `AsyncLayoutInflater`：可回退的搬移工具

截至 2026-07，稳定版 `androidx.asynclayoutinflater` 为 1.1.0。它使用进程内共享的单个后台线程（线程名为 `AsyncLayoutInflator`）和容量为 10 的队列，把 `inflate(..., parent, false)` 尝试放到后台。View 树不会自动加入 parent。

后台创建需要满足：

- parent 的 `generateLayoutParams(AttributeSet)` 可在该后台线程安全执行；
- 所有 View 构造过程不创建依赖当前线程 Looper 的 `Handler`，也不调用需要 Looper 的逻辑；
- 自定义 View、Drawable、字体或 SDK 初始化不触碰只能由主线程访问的状态；
- 布局不包含 `<fragment>`；
- AppCompat 页面使用 `asynclayoutinflater-appcompat` 的 `AsyncAppCompatFactory`，让兼容控件按对应 factory 创建。

后台 inflate 抛出 `RuntimeException` 时，库会记录日志并在创建 inflater 的线程 Handler 上重新同步 inflate。功能看起来正常，也可能完全没有省下 UI 时间。队列满时，UI 线程调用 `inflate()` 还可能阻塞在 `put()`；它不适合短时间提交大量请求。

下面的示例显式选择 AppCompat factory，并把完成回调放回主线程：

```kotlin
val asyncInflater = AsyncLayoutInflater(
    activity,
    AsyncAppCompatFactory()
)

asyncInflater.inflate(
    R.layout.view_heavy_panel,
    container,
    ContextCompat.getMainExecutor(activity)
) { view, _, parent ->
    parent?.addView(view)
}
```

传入 callback executor 后，后台 inflate 成功时回调可直接在该 executor 执行；示例选择 main executor，因 `addView()` 必须发生在 View 所属线程。未传 executor 的重载会回到创建 inflater 的 Looper。布局附加、ViewBinding、状态恢复和后续 layout 仍可能占用主线程。

适用场景是内容稍后才展示、需求确定性较高、可以提前发起且构造器经过线程安全验证的子树。Activity 首屏若必须等待回调才能展示，异步排队和线程切换未必降低启动时延。用同一测试设备比较：

- 同步 inflate 的主线程耗时；
- 后台任务排队与执行时长；
- fallback 次数；
- 回调后的 `addView + measure + layout`；
- 首屏或交互 FrameTimeline。

## 7. `ViewTreeObserver` 的布局回调边界

`ViewTreeObserver` 提供全树级事件。Android 17 `ViewRootImpl.performTraversals()` 在本轮发生 layout，或者需要重新计算全局属性时，调用 `dispatchOnGlobalLayout()`。因此 `OnGlobalLayoutListener` 表示全局布局状态或可见性发生过相应处理，不表示回调由某个 `View.layout()` 直接触发，也不证明该帧已经提交到 SurfaceFlinger 或显示器。

framework traversal 发起的 listener 在 ViewRoot 所在线程串行执行；应用若手动调用公开的 `dispatchOnGlobalLayout()`，回调则发生在调用线程。正常窗口路径中，监听者越多、工作越重，pre-draw/draw 前的主线程时间越长。常见约束包括：

- 只关心一个 View 的 frame 时，优先用 `View.OnLayoutChangeListener` 或 AndroidX `doOnLayout`；
- 一次性 global listener 在满足条件后立即移除；
- listener 内避免 I/O、遍历大树、同步 Binder 和无条件 `requestLayout()`；
- `OnPreDrawListener.onPreDraw()` 返回 `false` 会取消当前 draw 并重新调度，条件若长期不满足会造成连续取消；
- `OnGlobalLayoutListener` 结束点早于 draw、buffer queue 和 display present，首帧完成应使用 FrameTimeline、reportFullyDrawn 或与目标语义匹配的信号。

`View.getViewTreeObserver()` 返回的对象不保证在 View 整个生命周期内保持有效。未 attach 的 View 使用 floating observer；attach 时 listener 会合并到窗口 observer，旧 floating observer 随后被 `kill()`。长时间保存 observer 引用时应检查 `isAlive()`，移除 listener 时重新获取当前 observer 更稳妥。普通 detach 本身不能概括为“observer 被置为 dead”。

## 8. 用 Perfetto 与 Layout Inspector 建立证据

### 8.1 Android 17 可依赖的 framework slice

`android-17.0.0_r1` 的 `ViewRootImpl` 对根测量和布局使用固定 slice 名：

- `measure`：`performMeasure()` 包住根 View 的 `measure()`；
- `layout`：`performLayout()` 包住根 View 的 `layout()`，同一 slice 内可能包含 layout 期间请求引起的第二轮；
- `draw-<mTag>`：`performDraw()` 使用动态名称，完成窗口标签初始化后常见为 `draw-VRI[...]`。

Choreographer callback、窗口 relayout、HWUI sync/draw 与 FrameTimeline 还会出现在相邻 track。不同 Android 版本、厂商实现和 tracing 配置可能增加或缺少 slice，采集后应以当前 trace 的名称与调用栈确认。默认 system trace 通常不会逐个列出每个业务 View 的 `onMeasure()`。

下面的 SQL 用于从 thread track 中找出较长的根 measure/layout；阈值只是筛选条件，不是平台判定标准：

```sql
SELECT
  s.ts,
  s.dur / 1e6 AS dur_ms,
  s.name AS slice_name,
  t.name AS thread_name,
  p.name AS process_name
FROM slice AS s
JOIN thread_track AS tt ON s.track_id = tt.id
JOIN thread AS t ON tt.utid = t.utid
LEFT JOIN process AS p ON t.upid = p.upid
WHERE (s.name = 'measure' OR s.name = 'layout')
  AND s.dur >= 2e6
ORDER BY s.dur DESC;
```

`slice` 没有可直接 `USING (utid)` 的通用关系，必须经 `thread_track` 关联线程。结果还要过滤目标进程/窗口，并回到时间线判断这些 slice 是否属于用户可感知帧。

FrameTimeline 中 App `SurfaceFrame` 的 `surface_frame_token` 与 SF/Display 侧的 `display_frame_token` 负责不同关联语义。一帧 DisplayFrame 可以接纳多个进程或 layer 的 SurfaceFrame，不能把两种 token 拼成一个“端到端 frame id”。measure/layout 只能解释 App 主线程准备阶段，显示结果还要继续对齐 RenderThread、App Window buffer 提交和对应的 DisplayFrame。

### 8.2 给可疑 View 加窄范围 trace

系统 slice 只能证明根阶段变长。定位自定义容器时，在可疑实现周围添加命名稳定的 app trace，保持 `try/finally` 对称：

```kotlin
override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
    Trace.beginSection("MessageCard.onMeasure")
    try {
        measureMessageCard(widthMeasureSpec, heightMeasureSpec)
    } finally {
        Trace.endSection()
    }
}
```

这段埋点会出现在调用线程的 trace 中，可与根 `measure` 嵌套关系、调用次数和帧 deadline 对齐。采样前确认 release-like 构建与 tracing 开销；对大量叶子 View 全面加 section 会扰动结果。

第三方控件无法改源码时，可以组合方法 sampling、布局结构、输入变化和二分替换。只看一张 Layout Inspector 树无法定位毫秒归属。

### 8.3 Layout Inspector 的角色

Layout Inspector 适合检查运行时层级、父链、属性、隐藏 wrapper 和重复子树。它不提供可靠的逐 View measure/layout 性能数值，旧版 Hierarchy Viewer 的“交通灯耗时”也不应套到当前工具。

连接 inspector、live updates、debug view attributes、JDWP 或设备镜像都可能改变被测进程。结构检查与性能采集分开进行：

1. 用 Layout Inspector 保存结构证据；
2. 断开调试附加，使用相同页面状态采集 Perfetto/Macrobenchmark；
3. 按 trace 锁定阶段；
4. 对可疑容器加窄范围 trace 或做单变量 A/B；
5. 同时验证截图、交互、accessibility 与内存。

### 8.4 从长 layout 继续追问

| trace 现象 | 优先检查 |
|---|---|
| 单次 `measure` 很长 | 文本重排、复杂容器、多 pass、自定义 `onMeasure()`、首次资源 |
| 多帧连续 `measure/layout` | 动画中的 LayoutParams、listener 回写、binding 重复赋值、insets/窗口变化 |
| 同一 `layout` slice 内重复业务 trace | layout 期间 `requestLayout()`、第二轮 pass |
| inflate 长，随后 layout 也长 | 对象/资源创建与大子树首次测量应分开优化 |
| UI thread 处于 Runnable、等待 CPU | 调度竞争、thermal、频率；转到 `android17-6.18-2026-06_r6` 的 sched/freq 证据 |
| UI thread 很短但帧仍迟到 | RenderThread、GPU、buffer/fence、SurfaceFlinger；参见 [7.1 卡顿定义](01-jank-definition.md) |

一个长 `measure` slice 只说明根测量区间长。若线程处于 Sleeping/Blocked，还要查锁、Binder、I/O 或等待；若处于 Runnable 却未运行，再看调度与 CPU 竞争。把 wall time 全部归因于布局算法会误导修复方向。

## 9. 复核清单

### inflate

- 冷、热两组数据是否分开；
- 是否记录 Activity/Fragment、layout 资源和依赖版本；
- Factory2、自定义 View 构造、主题、字体、Drawable 是否进入关键路径；
- `inflate(res, parent, false)` 是否保留正确 LayoutParams；
- `ViewStub` 或异步加载是否只是把卡顿推迟到用户点击；
- AsyncLayoutInflater 是否统计 fallback、排队和 attach 后 layout。

### measure/layout

- 是否用 trace 证明 `measure` 或 `layout` 超过当前帧 deadline；
- 是否区分节点数、深度、pass 次数和单节点成本；
- 是否存在 weight、RelativeLayout、largest-child、baseline 或复杂约束；
- 自定义 `onMeasure()` 是否分配、I/O、锁等待或重复遍历；
- layout 期间是否产生第二轮请求；
- 文本、insets、窗口尺寸和列表复用是否改变测量输入。

### 工具与验证

- Android 平台结论是否对应 `android-17.0.0_r1`；
- 进入 sched/freq/fence 时是否对应 `android17-6.18-2026-06_r6`；
- Perfetto SQL 是否经 `thread_track` 关联线程；
- Layout Inspector 是否只用于结构证据；
- 修改前后是否使用相同设备、刷新率、页面数据、温度和构建类型；
- 性能收益是否与视觉、交互、accessibility 和内存回归一起验证。

## 参考资料

### Android 17 源码

- [LayoutInflater.java：inflate、Factory 与构造器缓存](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/LayoutInflater.java)
- [PhoneLayoutInflater.java：framework 短类名前缀](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/com/android/internal/policy/PhoneLayoutInflater.java)
- [View.java：measure、requestLayout 与 invalidate](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/View.java)
- [ViewGroup.java：child MeasureSpec 与层级操作](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewGroup.java)
- [Choreographer.java：VSync 与 callback 顺序](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java)
- [ViewRootImpl.java：traversal、第二轮布局与 trace](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)
- [ThreadedRenderer.java：UI thread 到 RenderThread 的入口](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ThreadedRenderer.java)
- [ViewTreeObserver.java：listener 分发与 observer 生命周期](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewTreeObserver.java)
- [ViewStub.java：同步 inflate 与替换语义](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewStub.java)
- [RelativeLayout.java：水平/垂直依赖测量](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/widget/RelativeLayout.java)
- [LinearLayout.java：weight 与重新测量条件](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/widget/LinearLayout.java)
- [Android 17 kernel 基线](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6)

### AndroidX 与官方指南

- [AsyncLayoutInflater 1.1.0 release notes](https://developer.android.com/jetpack/androidx/releases/asynclayoutinflater)
- [AsyncLayoutInflater 源码](https://android.googlesource.com/platform/frameworks/support/+/androidx-main/asynclayoutinflater/asynclayoutinflater/src/main/java/androidx/asynclayoutinflater/view/AsyncLayoutInflater.java)
- [AsyncAppCompatFactory 源码](https://android.googlesource.com/platform/frameworks/support/+/androidx-main/asynclayoutinflater/asynclayoutinflater-appcompat/src/main/java/androidx/asynclayoutinflater/appcompat/AsyncAppCompatFactory.java)
- [Performance and view hierarchies](https://developer.android.com/topic/performance/rendering/optimizing-view-hierarchies)
- [Layout resource：include、merge 与 ViewStub](https://developer.android.com/guide/topics/resources/layout-resource)
- [LayoutInflater API](https://developer.android.com/reference/android/view/LayoutInflater)
- [OnPreDrawListener API](https://developer.android.com/reference/android/view/ViewTreeObserver.OnPreDrawListener)
- [Layout Inspector](https://developer.android.com/studio/debug/layout-inspector)
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [Understanding the performance benefits of ConstraintLayout（2017 case study）](https://android-developers.googleblog.com/2017/08/understanding-performance-benefits-of.html)
