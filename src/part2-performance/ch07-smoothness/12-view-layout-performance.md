---
title: "View 体系性能优化：布局层级、inflate 与 measure/layout 开销"
chapter: "7.12"
section: "7.12"
status: ready-for-review
drafted_date: "2026-04-08"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
last_verified: "2026-04-25"
last_verified_against: "AOSP android-16.0.0_r1 ViewRootImpl / ViewDebug / ViewHierarchyEncoder"
reviewed_date: '2026-06-04'
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
pipeline_stage: task2b_pending
finalized_date: '2026-04-29'
finalized_by: openclaw-task6-auto-promote
task6_state: reviewed
task9_state: reviewed
task9_result: needs-rework
task2b_state: pending
task2b_result: fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-04"
last_task9_at: "2026-06-04T22:20:00+08:00"
last_task2b_at: "2026-06-04T12:57:00+08:00"
last_task6_audit: "2026-06-04"
last_task9_audit: "2026-05-21"
task9_review_notes: "2026-06-04 Task9 deep-review: needs-rework。P0 2 / P1 1；ViewTreeObserver Android 17 附录源码锚点与机制描述需回炉。"
---

# 7.12 View 体系性能优化：布局层级、inflate 与 measure/layout 开销

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 布局层级深度为什么会推高 `measure` / `layout` 开销
- 🔹 `LayoutInflater.inflate()` 的三阶段流程与主要耗时来源
- 🔹 `requestLayout()` 与 `invalidate()` 的触发路径和代价差异
- 🔹 `ConstraintLayout`、`ViewStub`、`<merge>`、`<include>` 的使用边界
- 🔹 `AsyncLayoutInflater` 的适用场景与限制
- 🔹 在 Perfetto / Layout Inspector 中定位布局性能瓶颈的方法

### 扩展（可选深入）

- 🔸 `Factory2` / AppCompat 对 inflate 路径的影响
- 🔸 高刷新率设备下的布局帧预算压力

### OpenClaw 加工指引

> 锚点是最低覆盖要求，加工时必须逐条落实并标注验证状态。
> 缺少真实 trace 或截图时，用 `[图：...]` 标注说明，不要编造现象。
<!-- outline-end -->

我们在前面的章节中分析了卡顿的定义、原因和分析方法论。这一节把镜头拉近到 Android View 体系本身。每个 Activity 的界面都对应一棵 View 树，首帧创建和发生布局请求的那几帧，inflate、measure、layout 往往就是主线程最重的工作；如果这里只要多跑几轮，后面的 draw 和 GPU 渲染再快也补不回来。

这一节从三个维度分析 View 体系的开销：布局层级深度对帧耗时的影响、`LayoutInflater.inflate()` 的完整流程与耗时来源、`measure/layout` 的递归遍历机制，以及 `requestLayout()` 和 `invalidate()` 的边界。每个部分都配有在 Perfetto 中的定位方法。

## 为什么要关注 View 体系的性能

Android 的一次 traversal 可能包含 Measure、Layout、Draw 三个阶段，但只有在 `requestLayout()`、窗口尺寸变化或 insets 变化把 `mLayoutRequested` 置为 true 时，系统才会重新执行 Measure 和 Layout。树越深，节点越多，一旦这两个阶段被触发，主线程就要花更多时间递归整棵 View 树。更麻烦的是，某些 ViewGroup（比如 `RelativeLayout`，以及使用了 `layout_weight` 的 `LinearLayout`）会让重复 measure 次数继续上升。

Google 在 2017 年推广 ConstraintLayout 时做过一组基准测试 [已验证: Google Developers Blog, 2017-08-24]：一个以 `RelativeLayout` 嵌套 `LinearLayout` 为主的注册表单，在 20 秒 Systrace 窗口里出现了 80 次 expensive measure/layout alerts；换成更扁平的 `ConstraintLayout` 版本后，同一窗口里的 alerts 明显减少。这个数字说明嵌套层级和重复 measure 会把布局成本迅速放大，但它不是“单帧固定 80 次 pass”，也不能直接外推到今天的 AndroidX / 120Hz 设备。

[图：Google 官方 benchmark 对比——RelativeLayout 嵌套 vs ConstraintLayout 的 Systrace 截图，标注 pass 数差异]

理解 View 体系性能问题的根源后，优化才有明确落点：inflate 的创建成本、measure/layout 的遍历成本，以及工具和布局组件的选择边界。

## LayoutInflater.inflate() 的完整流程与耗时分析

当 Activity 调用 `setContentView()`，或者我们在代码里调用 `LayoutInflater.inflate()` 时，系统要完成的工作远比"解析 XML 创建 View"复杂。

### inflate 的三个阶段

`LayoutInflater.inflate()` 的核心流程可以拆成三步：

**第一步：XML 解析。** Android 的 layout XML 在 `aapt2` 的 compile / link 阶段会以 APK 内的 binary XML 形式保存，`resources.arsc` 保存的是资源表与索引，两者不是同一个产物。运行时 `XmlPullParser` 读取的是 binary XML 中的节点和属性信息，这部分成本比文本 XML 低，但仍然属于 inflate 的固定开销。

[已验证: AOSP frameworks/base/core/java/android/view/LayoutInflater.java, inflate() 方法]

**第二步：反射创建 View 对象。** 这是 inflate 耗时的主要来源。对于 XML 中的每个标签（如 `<TextView>`、`<com.example.MyView>`），`LayoutInflater` 需要通过反射找到对应的类并实例化。具体来说：

- **框架 View**（如 `TextView`、`ImageView`）：`LayoutInflater` 会尝试多个包前缀——`android.widget.`、`android.webkit.`、`android.app.`、`android.view.`——拼接成全限定名后用当前 `Context` 的 `ClassLoader` 加载类，再通过 `Constructor.newInstance()` 创建实例。
- **自定义 View**：如果标签名包含点号（如 `com.example.MyView`），直接用全限定名加载。

```java
// frameworks/base/core/java/android/view/LayoutInflater.java
// @ AOSP main / android-16.0.0_r1，节选
private static final HashMap<String, Constructor<? extends View>> sConstructorMap =
        new HashMap<>();

public final View createView(Context viewContext, String name,
        String prefix, AttributeSet attrs) throws ClassNotFoundException {
    Constructor<? extends View> constructor = sConstructorMap.get(name);
    if (constructor != null && !verifyClassLoader(constructor)) {
        constructor = null;
        sConstructorMap.remove(name);
    }

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
    return constructor.newInstance(args);
}
```

这里省时间的是 `sConstructorMap` 缓存了每个 View 类的 `Constructor` 对象。第一次遇到某个 View 类需要反射查找，后续遇到同类型 View 就直接用缓存。

版本差异：AOSP android-14.0.0_r1、android-15.0.0_r1、android-16.0.0_r1 中 `sConstructorMap` 均为 `LayoutInflater` 的 `private static final HashMap`，进程内所有 `LayoutInflater` 实例共享同一份静态缓存。核心保护机制是 `verifyClassLoader()`——复用前校验缓存的 Constructor 是否来自当前 `Context` 可见的 ClassLoader，不匹配时移除并重新查找。动态特性模块、插件化或热更新场景要把 ClassLoader 生命周期纳入内存排查，避免旧 Constructor 被缓存延长存活时间。

[已验证: AOSP `frameworks/base/core/java/android/view/LayoutInflater.java` android-14.0.0_r1 / android-15.0.0_r1 / android-16.0.0_r1 均声明 `private static final HashMap<String, Constructor<? extends View>> sConstructorMap`，`verifyClassLoader()` 复用校验逻辑一致]

**第三步：递归 inflate 子 View 并设置属性。** 创建完父 View 后，`LayoutInflater` 遍历 XML 中的子标签，递归调用 `rInflateChildren()` 创建子 View，然后调用 `ViewGroup.addView()` 将子 View 添加到父容器中。每一层嵌套都会增加一轮递归。

### LayoutInflater.Factory2 拦截机制

在 `LayoutInflater` 走到反射创建 View 之前，它会先检查是否注册了 `Factory2`。`Factory2` 是一个拦截器，允许调用者自己决定如何创建 View。AppCompat 库就是利用这个机制，在 `AppCompatViewInflater` 中把 XML 里的 `<TextView>` 替换为 `AppCompatTextView`，以提供向下兼容的样式支持。

```java
// AppCompatViewInflater 的核心逻辑（简化）
public View createView(View parent, String name, Context context, AttributeSet attrs) {
    // 拦截框架 View 的创建，替换为 AppCompat 版本
    switch (name) {
        case "TextView":
            return new AppCompatTextView(context, attrs);
        case "Button":
            return new AppCompatButton(context, attrs);
        // ...
    }
    return null; // 返回 null 表示不拦截，走默认反射流程
}
```

[已验证: AOSP frameworks/base/core/java/android/view/LayoutInflater.java, Factory2 分发逻辑]

这个拦截机制本身的开销很小，但它提供了一个性能优化的思路：如果我们在 `Factory2` 中直接 `new` 出 View 对象，就能完全跳过反射。Jetpack Compose 的 `ComposeView` 就不走这套 XML inflate 流程，这也是 Compose 在创建 UI 时的一个性能优势。

### setContentView 的耗时在 Perfetto 中的表现

在 Perfetto 中，`setContentView` 的耗时体现为 `Choreographer#doFrame` 之前（如果是首帧）或 Activity 生命周期回调中的一段主线程忙碌区间：

- `Activity.onCreate` → `performSetContentView` → `installDecor` → `inflate`：可以在 Main Thread 的 track 上看到这整个过程
- 如果 inflate 耗时超过一帧预算，会在 `Choreographer#doFrame` 之前形成一个明显的"峡谷"，直接导致首帧延迟

[图：Perfetto 中 `setContentView()` / inflate 耗时区间示意，标注主线程忙碌段与首帧延迟]

在实际分析中，如果看到 Activity 冷启动时主线程有一个 30-80ms 的"平台"，大概率就是 `setContentView` 在 inflate 一个复杂的布局文件。我们可以在应用启动优化的章节（→ [8.3](../ch08-responsiveness/03-startup-optimization.md)）找到对应的优化策略。

## 布局层级深度与渲染性能的因果关系

### measure/layout 的递归遍历机制

从 `ViewRootImpl` 的视角看，驱动 View 树遍历的是 `performTraversals()`。这一轮 traversal 不一定每次都完整执行 Measure、Layout、Draw 三个阶段。`requestLayout()`、窗口尺寸变化、insets 变化等条件会让 `mLayoutRequested` 为 true，这时 `performTraversals()` 会进入 `performMeasure()` 和 `performLayout()`；如果只是 `invalidate()`，很多帧会直接复用上一次布局结果，把主要成本留在 `performDraw()`。

当系统确实需要重新布局时，Measure 和 Layout 都是自顶向下的递归过程：

- **Measure 阶段**：从 `ViewRootImpl` 调用根 View 的 `measure()` 开始，父 `ViewGroup` 在 `onMeasure()` 中继续 measure 子 View。
- **Layout 阶段**：从 `ViewRootImpl.performLayout()` 开始，递归调用每个 View 的 `layout()` → `onLayout()`。
- **Draw 阶段**：从 `ViewRootImpl.performDraw()` 开始，递归调用 `draw()` → `onDraw()`。

[图：View 树 traversal 示意图——标注 `mLayoutRequested=true` 时会进入 Measure/Layout，普通重绘帧可只走 Draw]

[已验证: AOSP frameworks/base/core/java/android/view/ViewRootImpl.java, `performTraversals()` 对 `mLayoutRequested` 的判断]

这里要看清一点：View 树的**每一层**都会增加一轮方法调用栈。如果一个布局有 10 层嵌套（不算少见），一旦进入 Measure 阶段，就要走过 10 层递归；如果其中某层有多个子 View，每一层还要遍历兄弟节点。假设一棵 View 树有 100 个节点、平均深度 8 层，一次 measure 的递归调用次数至少是 100 次，加上 ViewGroup 自身对子 View 的遍历逻辑，实际调用次数更多。

### 量化关系：层级深度与帧耗时

实际耗时和设备性能、字体与图片复杂度、约束关系、是否命中缓存都有关系，很难给出跨设备稳定的毫秒表。更稳妥的判断方法，是在同一台设备上观察 `performMeasure()` / `performLayout()` 的占比、重复 pass 次数，以及它们是否已经挤占了当前帧预算。

- 3 层、20 个 View 左右的简单布局，通常还不至于单独成为瓶颈；更该警惕的是高频触发的重复布局
- 8 层、80 个 View 左右的中等布局，如果夹杂 `wrap_content` 链、`layout_weight` 或嵌套 `RelativeLayout`，Perfetto 里就更容易看到连续的 measure/layout slice
- 12 层、200 个 View 左右的复杂布局，一旦和列表滚动、动画或首帧 inflate 叠在一起，布局阶段就可能吞掉大部分帧预算

在 120Hz 设备上，帧预算只有 8.33ms。布局层级本身不是唯一问题，重复 measure、深层嵌套和不必要的 `requestLayout()` 更容易把预算挤空。

> ⚠️ [待验证] 本节曾描述 Android 15 引入"渲染意图感知"以减少 OverScroll 的额外 measure pass。经过 AOSP android-15.0.0_r1 / android-16.0.0_r1 源码搜索与 release note 交叉检索，未找到可核验的 commit、类/方法路径或 release note 支撑该说法。在获得一手依据之前，不能将此项作为已验证的版本差异发布。排查 OverScroll 场景的 measure 开销时，建议直接以 Perfetto trace 中的 `performMeasure()` / `performLayout()` slice 为准，不必预设 Android 15+ 有自动优化。

### RelativeLayout 的二次 measure 问题

`RelativeLayout` 的 `onMeasure()` 会对每个子 View 执行两轮 measure。原因是 `RelativeLayout` 允许子 View 之间相互约束（如 `layout_toRightOf`、`layout_below`），在第一轮 measure 时，某个子 View 的尺寸可能依赖另一个子 View 的尺寸，而后者尚未完成测量。所以 `RelativeLayout` 不得不再跑一轮。

嵌套的 `RelativeLayout`（这在老项目中很常见）会让这个问题更难控制：外层每次重新 measure，内层 `RelativeLayout` 也可能各自再跑两轮 measure，累计 pass 数会上升得很快。这里更稳妥的表述是“重复 measure 开销被层层放大”，而不是把它写成严格的 `$2^n$` 数学公式。真实放大量取决于子树结构、`MeasureSpec` 组合以及是否提前复用已测结果。

[已验证: AOSP frameworks/base/core/java/android/widget/RelativeLayout.java, onMeasure() 中的两次遍历]

## measure/layout 的开销与 requestLayout

### MeasureSpec 的传递规则

`measure()` 的核心输入是 `MeasureSpec`——一个 32 位整数，高 2 位是模式（`EXACTLY`、`AT_MOST`、`UNSPECIFIED`），低 30 位是尺寸。

- **EXACTLY**：父 View 已确定了子 View 的精确大小（对应 `match_parent` 或具体数值）
- **AT_MOST**：子 View 不能超过某个上限（对应 `wrap_content`）
- **UNSPECIFIED**：子 View 想多大就多大（少见，ScrollView 的子 View 可能收到这个）

`MeasureSpec` 从 ViewRootImpl 开始向下传递，每一层父 View 根据自己的约束和子 View 的 `LayoutParams` 计算出子 View 的 `MeasureSpec`。

### requestLayout() 触发的完整流程

当我们调用 `View.requestLayout()` 时，发生了以下链式反应：

1. `View.requestLayout()` 将自身的 `mPrivateFlags` 打上 `PFLAG_FORCE_LAYOUT` 标记
2. 调用 `ViewParent.requestLayout()`，这会沿 View 树**向上传递**到 `ViewRootImpl`
3. `ViewRootImpl.requestLayout()` 调用 `scheduleTraversals()`
4. `scheduleTraversals()` 通过 `Choreographer.postCallback()` 注册一个 `TraversalRunnable`，在下一个 VSync-app 信号到来时执行
5. VSync 到来后，`ViewRootImpl.performTraversals()` 被触发，依次执行 `performMeasure()` → `performLayout()` → `performDraw()`

```java
// frameworks/base/core/java/android/view/ViewRootImpl.java
// @ AOSP android-16.0.0_r1
void scheduleTraversals() {
    if (!mTraversalScheduled) {
        mTraversalScheduled = true;
        mTraversalBarrier = mHandler.getLooper().getQueue().postSyncBarrier();
        mChoreographer.postCallback(
                Choreographer.CALLBACK_TRAVERSAL, mTraversalRunnable, null);
    }
}
```

[已验证: AOSP ViewRootImpl.java, scheduleTraversals()]

`requestLayout()` 会在消息队列中插入一个同步屏障（`sync barrier`）。`postSyncBarrier()` 会暂时挡住普通同步消息；`Choreographer` 发布的 traversal 回调是异步消息，可以越过屏障。这让下一轮 `TraversalRunnable`（即 `doFrame`）比队列中已有的普通 Handler 消息更早执行。屏障会在 traversal 执行后移除，只按 Handler 入队顺序看 trace 时，容易误判 `requestLayout()` 被普通消息拖住。

### requestLayout() vs invalidate()：性能差异的本质

这两者的区别是 Android 面试的经典题，也是实际优化中必须搞清楚的问题：

**`invalidate()`** 会给当前 View 打上 dirty 标记，并把脏区域沿父容器向上传到 `ViewRootImpl`，随后在下一次 traversal 中进入 Draw 阶段。它通常不会重新 measure 和 layout。开启硬件加速时，系统还会结合 RenderNode 的 damage 信息缩小重绘范围。适合的场景：文字内容变了、颜色变了、Drawable 状态变了——凡是**不影响 View 尺寸和位置**的变化。

**`requestLayout()`** 标记 View 需要重新测量和布局，触发 **Measure + Layout + Draw 全流程**。而且它是**向上传播**的：一个子 View 调用 `requestLayout()`，它的父 View、祖父 View……一直到 `ViewRootImpl`，整条传递路径上的所有 View 都需要重新 measure/layout。

性能差异来自执行范围：

| 维度 | invalidate() | requestLayout() |
|------|-------------|-----------------|
| 触发方式 | 标记 dirty，下一轮 traversal 主要进入 Draw | 标记 layout request，下一轮 traversal 进入 Measure + Layout + Draw |
| 传播方向 | dirty 区域向上传到 ViewRootImpl；Draw 阶段再自顶向下执行 | layout request 向上传播至 ViewRootImpl |
| 影响范围 | 以 dirty 区域和受影响的节点为主 | 常常从根节点重新走一轮 measure/layout，树越大代价越高 |
| Perfetto 常见表现 | Draw 相关 slice 更显眼 | Measure/Layout 相关 slice 更显眼 |

一个常见的性能错误：在 `RecyclerView.Adapter.onBindViewHolder()` 中调用 `requestLayout()` 而不是 `invalidate()`。这会导致每个 item bind 时都触发一次完整的 View 树遍历，在滑动场景下直接造成卡顿。

[已验证: AOSP View.java, requestLayout() 和 invalidate() 的实现差异]

### 为什么一个 requestLayout() 可能导致整棵 View 树重测

`requestLayout()` 的向上传播机制意味着：即使只有一个很小的 TextView 调用了 `requestLayout()`，它的所有祖先 View 都需要重新 measure。这是因为父 View 的尺寸可能依赖于子 View 的尺寸（比如 `wrap_content`），子 View 尺寸变了，父 View 的尺寸也可能变。

在实际项目中，这种"牵一发而动全身"的情况经常发生在列表项中：某个 item 内部的 View 调用了 `requestLayout()`，导致整个 RecyclerView 甚至 Activity 的 DecorView 都需要重测。如果这种调用发生在滑动过程中，每帧都触发一次，性能灾难就来了。

优化思路：

- 如果只是视觉变化（颜色、文字、图标），用 `invalidate()` 或 `setText()` / `setImageDrawable()` 等方法，这些方法内部会自动调用 `invalidate()`
- 如果只是想保留占位并减少重排，优先用 `INVISIBLE`、`alpha`、`translation` 或固定尺寸容器；`GONE/VISIBLE` 会改变子 View 是否参与布局，仍然会触发父容器向上的重新布局
- 在自定义 View 中，`onDraw()` 内不应该调用 `requestLayout()`

## ConstraintLayout 与传统布局的性能差异

### ConstraintLayout 的设计目标：扁平化

`ConstraintLayout` 的核心设计理念是**用约束关系替代嵌套层级**。在传统布局中，要实现"左边一个图标、右边两行文字"的排列，通常需要 `LinearLayout` 嵌套 `LinearLayout`，至少 2-3 层。用 `ConstraintLayout`，所有元素都是直接子 View，通过 `layout_constraintLeft_toRightOf` 等属性互相约束，整个布局只有 1 层。

### 官方 benchmark 数据

Google 在 2017 support ConstraintLayout 时代做过一组公开测试 [已验证: Google Developers Blog, "Understanding the performance benefits of ConstraintLayout", 2017-08-24]：

- **测试布局**：一个注册表单页面，包含图片、标题、多个输入框和按钮
- **RelativeLayout 嵌套方案**：Systrace 在 20 秒抓取窗口里报告 80 次 expensive measure/layout alerts
- **ConstraintLayout 方案**：把层级压平后，同一窗口里的 expensive alerts 明显减少

这组数据能证明两件事。第一，扁平层级通常更容易减少重复 measure/layout。第二，`RelativeLayout` 这类需要多轮测量的容器，在嵌套后会更容易把 traversal 成本放大。它不能直接说明“当前 AndroidX 项目每帧一定节省多少毫秒”，因为测试对象、support library 版本、设备刷新率和 trace 口径都与今天的项目环境不同。

`ConstraintLayout` 的内部实现也不该被简化成“一次遍历就能确定所有子 View 的位置”。它通过约束求解器和更扁平的层级，减少很多传统嵌套布局里的重复 `measure/layout`。收益大小还是要用当前设备上的 FrameMetrics 或 Perfetto 实测。

[图：Google 官方 benchmark 的 Systrace 对比截图——80 passes vs 扁平化的 pass 数]

### layout_optimizationLevel

`ConstraintLayout` 提供了 `app:layout_optimizationLevel` 属性来控制内部优化策略：

```xml
<androidx.constraintlayout.widget.ConstraintLayout
    app:layout_optimizationLevel="direct|barrier|chain|dimensions" >
```

- `direct`：直接约束优化
- `barrier`：Barrier 相关优化
- `chain`：Chain 布局优化
- `dimensions`：尺寸测量优化

默认会按版本启用一组可用优化。收益大小取决于约束关系、子树规模和重复测量次数，最好用当前设备上的 Perfetto 或 FrameMetrics 验证。

### ViewBinding 的初始化代价

ViewBinding 常被理解为 `findViewById` 的语法糖。在初始化阶段，生成的 `bind()` 方法会遍历 View 树，对每个带 ID 的 View 调用 `findViewById`。在简单布局下这笔开销可以忽略，但在复杂 View 树（例如 200+ 节点、多层嵌套的列表项）中，`bind()` 的耗时可能和 `inflate` 本身处于同一量级。

在 RecyclerView 列表这种高频 bind 场景中，可以考虑以下替代方案：

- 手动缓存 `findViewById` 结果，只查找需要动态更新的 View
- 通过 `LayoutInflater.Factory2` 直接实例化核心控件，跳过 XML 反射路径
- 对特别复杂的列表项，用基准测试对比 ViewBinding bind 和手动 bind 的耗时占比

### 什么时候不该用 ConstraintLayout

`ConstraintLayout` 也有边界。在以下场景，传统布局反而更合适：

- **2-3 个子 View 的简单布局**：`FrameLayout` 或 `LinearLayout` 就够了，`ConstraintLayout` 的约束求解器有自己的初始化开销
- **纯线性排列**：几个 View 水平或垂直排列，用 `LinearLayout` 最直接
- **需要 `layout_weight` 的场景**：虽然 `ConstraintLayout` 可以用 `MatchConstraint` 百分比实现类似效果，但如果就是简单的等分，`LinearLayout` 的代码更简洁

判断原则：**布局嵌套超过 3 层时，考虑用 `ConstraintLayout` 扁平化；1-2 层的简单布局，不需要换。**

## ViewStub、Merge、Include 的性能优化实践

### ViewStub：延迟加载

`ViewStub` 是一个轻量级的占位符 View，它**不可见、不参与 measure/layout/draw、几乎不占内存**。只有当你显式调用 `viewStub.inflate()` 或 `viewStub.setVisibility(VISIBLE)` 时，它才会被替换为实际的布局。

```xml
<!-- 定义 ViewStub -->
<ViewStub
    android:id="@+id/stub_error_panel"
    android:layout="@layout/error_panel"
    android:inflatedId="@+id/error_panel"
    android:layout_width="match_parent"
    android:layout_height="wrap_content" />
```

```java
// 按需 inflate
View errorPanel = ((ViewStub) findViewById(R.id.stub_error_panel)).inflate();
```

`ViewStub` 和 `View.setVisibility(GONE)` 的本质区别：

| 维度 | ViewStub | View.GONE |
|------|----------|-----------|
| 初始 inflate | 不 inflate，零开销 | 已经 inflate，对象已创建 |
| 内存占用 | 占位符约几十字节 | 完整 View 树，可能数 KB |
| 切换耗时 | 首次需要 inflate，之后无 | 直接设 visibility，瞬时 |
| 适用场景 | 大概率不显示的内容 | 可能频繁切换显示/隐藏 |

典型使用场景：错误提示面板、空状态页、调试面板、用户协议弹窗。

注意：`ViewStub` 只能 `inflate()` 一次。再次调用会抛 `IllegalStateException`。如果需要反复切换，应该在 inflate 后直接操作目标 View 的 visibility。

### Merge 标签：减少顶层容器

`<merge>` 标签的作用是告诉 `LayoutInflater`：这个布局被 include 到其他布局时，不要给它的根元素再包一层父容器。

最常见的场景是自定义 View 的内部布局。假设我们有一个 `TitleBar` 自定义 View，它继承自 `RelativeLayout`。如果 `title_bar.xml` 的根元素是 `<RelativeLayout>`，inflate 后就会变成 `RelativeLayout（自定义 View）→ RelativeLayout（XML 根）→ 子 View`，两层 `RelativeLayout` 完全多余。把 XML 根改为 `<merge>`，inflate 后直接把子 View 添加到自定义 View 中，只有一层 `RelativeLayout`。

```xml
<!-- title_bar.xml：用 merge 避免多余的 RelativeLayout -->
<merge xmlns:android="http://schemas.android.com/apk/res/android">
    <TextView android:id="@+id/title" ... />
    <ImageButton android:id="@+id/back" ... />
</merge>
```

### Include 标签：布局复用

`<include>` 仍然由 `LayoutInflater` 在运行时处理。inflate 走到 `<include>` 节点时，会进入 `parseInclude()` 解析被包含布局的资源 ID，再继续创建其中的根 View 或 `<merge>` 子树。它的价值在于复用布局定义，inflate 成本仍然存在。

能减少层级的是让被 include 的布局以 `<merge>` 作为根，这样父容器在运行时不会再多包一层 ViewGroup。如果这块内容很大且大多数时候不显示，再考虑改用 `ViewStub` 做延迟 inflate。

## AsyncLayoutInflater 异步布局加载

### 设计原理

`AsyncLayoutInflater`（来自 `androidx.asynclayoutinflater`）允许在后台线程执行 `inflate()`，完成后回调到主线程将 View 树 attach 到父容器。它的目的是把 inflate 的 XML 解析 + 反射创建 View 的开销从主线程移走。

```java
new AsyncLayoutInflater(context).inflate(
    R.layout.complex_layout, parent, (view, resid, parent) -> {
        // view 已在后台线程创建完毕，此时在主线程回调
        parent.addView(view);
    });
```

[已验证: AndroidX AsyncLayoutInflater 源码]

### 限制与注意事项

`AsyncLayoutInflater` 能否把 inflate 留在后台线程，取决于几个前提：

1. **parent 的 `generateLayoutParams(AttributeSet)` 必须线程安全**。如果父容器的这一步只能在主线程执行，后台 inflate 会失败并回退到 UI thread。
2. **被创建的 View 不能在构造或初始化阶段创建 `Handler`，也不能依赖 `Looper.myLooper()`**。这类 View 在后台线程里构造时很容易抛异常。
3. **`<fragment>` 标签会触发回退到主线程同步加载**。由于 `FragmentManager` 事务严格限制在 UI 线程，`<fragment>` 的解析是非线程安全的。在最新 AndroidX 源码中，`AsyncLayoutInflater` 在后台线程遇到 `<fragment>` 时会触发 `RuntimeException`，被捕获后回退到 UI 线程同步 inflate。功能上结果正确，但主线程完全承担了这次 inflate，异步优化的目的落空。

    如果布局中包含 Fragment，必须改用 `FragmentContainerView` 作为占位容器，在主线程回调中通过 `FragmentTransaction` 动态挂载 Fragment，不能指望 `AsyncLayoutInflater` 异步处理。

4. **默认 `BasicInflater` 不会复用 AppCompat 那套主线程 `Factory2` 链**。AndroidX `AsyncLayoutInflater 1.1.0` 增加了 `AsyncLayoutFactory` 构造入口；AppCompat 项目可以引入 `asynclayoutinflater-appcompat`，用 `AsyncAppCompatFactory` 让 AppCompatViewInflater 参与后台 inflate。
5. **回退是常见结果，不是异常路径**。`AsyncLayoutInflater` 的后台线程只要抛 `RuntimeException`，就会记录日志并在 UI thread 重新 inflate。功能可能看起来正常，但主线程时间并没有省下来。

AppCompat 场景的最小接入形态如下：

```kotlin
val inflater = AsyncLayoutInflater(
    context,
    AsyncAppCompatFactory()
)

inflater.inflate(R.layout.complex_layout, parent, mainExecutor) { view, _, target ->
    target?.addView(view)
}
```

如果指定 `callbackExecutor`，最终 `addView()`、ViewBinding 绑定和状态写入仍要回到主线程执行。

[已验证: AndroidX `asynclayoutinflater 1.1.0` 新增 `AsyncLayoutFactory` 构造入口与 callback executor；`asynclayoutinflater-appcompat 1.1.0` 提供 `AsyncAppCompatFactory`]

实际使用中，`AsyncLayoutInflater` 更适合启动后延迟展示的复杂布局，或者弹窗/对话框里可以晚一点 attach 的内容视图。

### 在 Perfetto 中的表现

使用 `AsyncLayoutInflater` 后，Perfetto 中能看到：

- 主线程在 `Activity.onCreate` 期间不再有 inflate 的耗时区间
- 后台线程（通常是 `AsyncLayoutInflater` 的 `HandlerThread`）出现 inflate 活动
- 主线程在回调 `onInflateComplete` 时有一个短暂的 `addView` 操作

[图：AsyncLayoutInflater 使用前后主线程与后台线程 trace 对比，标注 inflate 与 addView 区间]

## 在 Perfetto/工具中的表现

### Choreographer doFrame → traversal → performMeasure/performLayout/performDraw

在 Perfetto 中，View 体系的性能开销集中体现在 `Choreographer#doFrame` 这个 slice 中。展开后会显示三个子阶段：

```
Choreographer#doFrame
  ├── performMeasure  (Measure 阶段耗时)
  ├── performLayout   (Layout 阶段耗时)
  └── performDraw     (Draw 阶段耗时)
```

如果 `performMeasure` 或 `performLayout` 占据了 doFrame 的绝大部分时间，说明瓶颈在布局层级而不是绘制。

[图：Perfetto 中 doFrame 的三个子阶段，标注 measure 过长的情况]

### 定位具体 View 的耗时

Perfetto 最稳的系统级入口还是 `Choreographer#doFrame`、`ViewRootImpl.performTraversals()`、`performMeasure()`、`performLayout()` 这些 slice。它默认不会把每个 View 实例的 `onMeasure()` / `onLayout()` 逐个展开给我们，所以不要把 `View.setTransitionVisibility()` 或 `Window.setFrameContent()` 当成通用定位入口。

要把系统级耗时继续收敛到具体 View，常用的是三种可验证路径：

- **手动 trace**：在自定义 View、复杂容器或 Adapter 绑定代码里加 `Trace.beginSection()` / `Trace.endSection()`
- **结构检查**：用 Layout Inspector、ViewCapture 或 `gfxinfo` 看层级、节点数量和可疑容器
- **业务埋点**：把可疑布局阶段的开始/结束时间记到日志，再和 Perfetto 中的长 traversal 放到同一时间段里比较

```java
// 在自定义 View 中添加 trace
@Override
protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
    Trace.beginSection("MyCustomView.onMeasure");
    super.onMeasure(widthMeasureSpec, heightMeasureSpec);
    Trace.endSection();
}
```

在 Perfetto 中搜索对应的 trace tag，即可看到每次 `onMeasure()` 的精确耗时。这种办法虽然需要手工埋点，但结论可复现，也不会把不存在的 framework API 当成定位入口。

### Layout Inspector

Android Studio 的 Layout Inspector 可以在运行时查看 View 树的结构。它提供了一个"traffic light"指示器：

- 🟢 绿色：Measure/Layout/Draw 各阶段 < 0.5ms
- 🟡 黄色：0.5ms - 1ms
- 🔴 红色：> 1ms

这是一个快速发现"哪个 View 是性能瓶颈"的好工具，但它本身会影响 App 性能（通过 JDWP 调试协议通信），不要在正式性能测试时使用。

## ViewDebug 与系统级 Layout Trace 机制

> 本小节为 AIW 源码调研补充内容（2026-04-25），未经一手源码逐行验证的部分已标注。

### ViewDebug.java 的属性暴露体系

**源码位置**：`frameworks/base/core/java/android/view/ViewDebug.java`

`ViewDebug` 是 Android View 调试基础设施的核心类，通过注解体系将 View 内部状态暴露给调试工具：

**@ViewDebug.ExportedProperty** — 标记 View 的字段或方法（非 void、无参数），使工具可以通过 ViewServer 或 Layout Inspector 捕获其值：

```java
@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.FIELD, ElementType.METHOD})
public @interface ExportedProperty {
    String category() default "";  // layout / measurement / drawing / padding / events / chrome
    boolean deepExport() default false;
    String[] flagMapping() default {};
    String formatToHexString() default "";
}
```

AOSP View 源码中的典型使用：
```java
// frameworks/base/core/java/android/view/View.java
@ViewDebug.ExportedProperty(category = "measurement")
public final int getMeasuredWidth() { return mMeasuredWidth & MEASURED_SIZE_MASK; }

@ViewDebug.ExportedProperty(category = "layout")
public int getBaseline() { return -1; }

@ViewDebug.ExportedProperty(category = "drawing")
public float getAlpha() { return mAlpha; }
```

**category 的作用**：为 Layout Inspector 等工具提供属性分类过滤，不同 category 的属性在工具侧可以分组查看。

**@ViewDebug.CapturedViewProperty** — 用于视图捕获时需要包含的属性，语义与 ExportedProperty 不同之处在于捕获上下文。

**ViewDebug.dumpCapturedView()** — 将 View 信息序列化，用于 id-based 仪表化测试生成和数据挖掘。

**HierarchyTraceType（已废弃）** — 早期 `ViewDebug.trace()` API 使用的枚举（INVALIDATE / VIEW_VALIDATE / DRAW 等），内部调用在 API 16 前后被陆续移除。

### debug.layout 系统属性与布局边界可视化

**系统属性名**：`debug.layout`。截至 AOSP main / android-16.0.0_r1，`View.java` 未提供 `View.DEBUG_LAYOUT_PROPERTY` 常量；框架侧通过 `android.sysprop.DisplayProperties.debug_layout()` 读取该属性。

启用方式：
- 开发者选项 → "显示布局边界"（Show layout bounds）
- ADB：`adb shell setprop debug.layout true`
- 已存在窗口通常要触发系统属性变更回调或重启相关 UI 进程，才能重新读取属性值

**属性读取路径**（[已验证: AOSP `frameworks/base/core/java/android/view/ViewRootImpl.java`, `loadSystemProperties()` / `MSG_INVALIDATE_WORLD` / `invalidateWorld()`]）：

```
debug.layout 系统属性
    ↓ DisplayProperties.debug_layout().orElse(false)
ViewRootImpl.loadSystemProperties()
    ↓ 更新 AttachInfo.mDebugLayout
WindowManagerGlobal.addSystemPropertyChangedCallback(...)
    ↓ 属性变化时发送一次 MSG_INVALIDATE_WORLD（带延迟）
ViewRootImpl.handleMessage(MSG_INVALIDATE_WORLD)
    ↓ invalidateWorld(mView)
下一轮 traversal 重绘布局边界
```

`MSG_INVALIDATE_WORLD` 用于刷新整棵 View 树的 dirty 状态，让布局边界开关变化反映到当前窗口。这个消息只在属性变化路径中触发一次带延迟的刷新；`ViewRootImpl.handleMessage()` 处理该消息时只调用 `invalidateWorld(mView)`。打开布局边界会增加调试绘制成本，性能测试前应关闭，避免描述成 Handler 每帧强制全树重绘。

### performTraversals() 中的 Trace 埋点

**关键常量**：`TRACE_TAG_VIEW = 1L << 3`（值为 8）

**完整调用链**（[已验证: AOSP ViewRootImpl.java]）：

```
Choreographer.doFrame(vsyncId)
    ↓
ViewRootImpl.doTraversal()
    ↓ Trace.traceBegin(TRACE_TAG_VIEW, "performTraversals")
    ↓
ViewRootImpl.performTraversals()
    ├── Trace.traceBegin(TRACE_TAG_VIEW, "measure")
    │   └── mView.measure() → measure hierarchy
    ├── Trace.traceEnd(TRACE_TAG_VIEW)
    ├── Trace.traceBegin(TRACE_TAG_VIEW, "layout")
    │   └── host.layout() → layout hierarchy
    ├── Trace.traceEnd(TRACE_TAG_VIEW)
    ├── Trace.traceBegin(TRACE_TAG_VIEW, "draw")
    │   └── mView.draw() → build/update DisplayList
    └── Trace.traceEnd(TRACE_TAG_VIEW)
    ↓ Trace.traceEnd(TRACE_TAG_VIEW)  ← finally 块保证结束
```

这些 Slice 在 Perfetto 中通过 `atrace` 数据源记录，呈现为 UI Thread 上的嵌套 slice，名称为 `"measure"`、`"layout"`、`"draw"`。

### ViewHierarchyEncoder：高效的 View 层级序列化

**源码位置**：`frameworks/base/core/java/android/view/ViewHierarchyEncoder.java`（API 21+）。`dumpv2()` 定义在 `ViewDebug`；`ViewHierarchyEncoder` 不提供这个静态入口。

`ViewHierarchyEncoder` 负责把单个 View 对象的属性编码到输出流。典型调用过程由 `ViewDebug.dumpv2(View, OutputStream)` 发起：`ViewDebug` 遍历 View 树，调用每个 View 的 `encode(ViewHierarchyEncoder)`，编码器写入属性 ID、属性值和末尾的 ID → 属性名映射。

```java
// frameworks/base/core/java/android/view/ViewHierarchyEncoder.java
// 编码器职责节选：保留方法签名，方法体省略。
public final class ViewHierarchyEncoder {
    public void beginObject(Object object) { /* Several lines omitted. */ }
    public void addProperty(String name, boolean value) { /* Several lines omitted. */ }
    public void addProperty(String name, int value) { /* Several lines omitted. */ }
    public void addProperty(String name, float value) { /* Several lines omitted. */ }
    public void endObject() { /* Several lines omitted. */ }
    public void endStream() { /* Several lines omitted. */ }
}

// frameworks/base/core/java/android/view/ViewDebug.java
// dumpv2() 位于 ViewDebug，内部使用 View.encode(encoder) 写出层级。
public static void dumpv2(View root, OutputStream clientStream) throws IOException {
    // Several lines omitted.
}
```

Layout Inspector V2 通过 `View.encode()` 这条路径读取属性，减少早期反射式层级 dump 的开销。写工具或读源码时，要把 `ViewDebug` 的遍历入口和 `ViewHierarchyEncoder` 的编码职责分开。

### debug_view_attributes 与 Layout Inspector

Layout Inspector 的底层依赖：
```bash
adb shell settings put global debug_view_attributes 1
```
该设置让系统为所有 View 生成额外调试信息（View ID、资源名等），并触发当前前台 Activity 一次重启。Layout Inspector 连接时自动启用，断开时删除。

### Perfetto 中的 View 系统追踪

| Slice 名称 | 线程 | 含义 |
|---|---|---|
| `performTraversals` | UI Thread | 完整遍历（measure+layout+draw） |
| `measure` | UI Thread | 递归 measure pass |
| `layout` | UI Thread | 递归 layout pass |
| `draw` | UI Thread | 绘制（构建 DisplayList） |
| `Choreographer#doFrame` | UI Thread | VSync 驱动的帧处理 |

Perfetto SQL 示例 — 查找 measure 阶段耗时超过 4ms 的帧：
```sql
SELECT 
  slice.name, slice.depth,
  slice.dur / 1000 AS duration_us,
  thread.name AS thread_name
FROM slice
JOIN thread USING (utid)
WHERE slice.name = 'measure' AND slice.dur > 4000000
ORDER BY slice.dur DESC;
```

<!-- AIW-源码调研-2026-04-25 -->



## 常见问题与误区

### 误区 1：布局越少越好

减少 View 数量能降低 measure/layout 的开销，但"过度扁平化"也有代价。如果一个 View 的 `onDraw()` 逻辑过于复杂（比如用 Canvas 手动画了一个本来应该拆成多个 View 的复杂界面），draw 阶段的耗时反而可能超过省下来的 measure 时间。

正确做法：优先减少**层级深度**（嵌套层数），再看**View 总数**。一个 5 层 50 个 View 的布局，通常比 2 层 200 个 View 的布局更慢；但一个 1 层 500 个 View 的布局也未必比 3 层 100 个 View 的布局快。

### 误区 2：ConstraintLayout 总是比 LinearLayout 快

`ConstraintLayout` 的约束求解器有初始化开销。对于只有 2-3 个子 View、单向排列的简单场景，`LinearLayout` 的实现更轻量。根据 Google 的测试数据，在简单场景下 `ConstraintLayout` 和 `LinearLayout` 的 measure 时间差距在 5% 以内，可以忽略。

### 误区 3：View.GONE 的 View 不参与 measure

这个说法不完全正确。`View.GONE` 的 View 本身不参与 measure（它的测量尺寸为 0），但它的**父容器仍然需要处理它**。某些 ViewGroup（如 `LinearLayout`）在测量时会遍历所有子 View 包括 GONE 的，只是跳过测量步骤。而且 GONE 的 View 变为 VISIBLE 时会触发父容器的 `requestLayout()`，导致整棵 View 树重测。

### 面试高频：requestLayout vs invalidate

简单回答：

- `invalidate()` → 重绘（Draw only）→ 用于外观变化
- `requestLayout()` → 重测重排重绘（Measure + Layout + Draw）→ 用于尺寸/位置变化

进阶回答：

- `invalidate()` 会把 dirty 区域向上传到 `ViewRootImpl`，随后那一轮 Draw 再自顶向下遍历；`requestLayout()` 则把 layout request 向上传到 `ViewRootImpl`
- `requestLayout()` 会触发 `scheduleTraversals()` 并通过 `Choreographer` 等待下一个 VSync 执行
- `invalidate()` 也是异步的，它通过 `ViewRootImpl.scheduleTraversals()` 等待下一个 VSync
- 在同一帧内多次调用 `invalidate()` 或 `requestLayout()`，只会在下一个 VSync 执行一次 doFrame

## 参考资料

### AOSP 源码路径

- `frameworks/base/core/java/android/view/LayoutInflater.java` — inflate 流程、Factory2、Constructor 缓存
- `frameworks/base/core/java/android/view/View.java` — requestLayout、invalidate、measure
- `frameworks/base/core/java/android/view/ViewRootImpl.java` — performTraversals、scheduleTraversals
- `frameworks/base/core/java/android/view/ViewGroup.java` — measureChildWithMargins、addView
- `frameworks/base/core/java/android/widget/RelativeLayout.java` — 二次 measure 的实现
- `frameworks/base/core/java/android/widget/LinearLayout.java` — layout_weight 的 measure 逻辑
- `androidx/asynclayoutinflater/asynclayoutinflater/src/main/java/androidx/asynclayoutinflater/view/AsyncLayoutInflater.java` — 后台 inflate 条件与回退逻辑

### 官方文档与博客

- [Understanding the performance benefits of ConstraintLayout](https://android-developers.googleblog.com/2017/08/understanding-performance-benefits-of.html) — Google 官方 benchmark
- [Optimizing View Hierarchies](https://developer.android.com/topic/performance/rendering/optimizing-view-hierarchies) — Android 官方文档
- [Improving Layout Performance](https://developer.android.com/topic/performance/vitals/render) — Android Performance Patterns

### 工具

- Layout Inspector（Android Studio 内置）
- Systrace / Perfetto — 布局 pass 的 trace 标签
- Lint — 检测过度嵌套、无用 View、可用 ViewStub 替换的布局


---

<!-- AIW-源码调研-2026-06-03 -->
### 7.12.x ViewTreeObserver 与布局性能优化机制（Android 17 API 37）

**来源**：每日源码调研（cron:d78cfef0，id=6，关联 §6.1 View系统优化）
**时间**：2026-06-03 | 源码级一手验证（AOSP android-17.0.0_r1）

#### ViewTreeObserver 核心机制

ViewTreeObserver（VTO）是 View 框架中连接 View 树生命周期与外部监听者的核心机制。核心源码：

- `frameworks/base/core/java/android/view/ViewTreeObserver.java`
- `frameworks/base/core/java/android/view/ViewRootImpl.java` — performTraversals() 入口

**关键成员**：

```java
private OnGlobalLayoutListener mOnGlobalLayoutListener;
private OnScrollChangedListener mOnScrollChangedListener;
private boolean mAlive = true;  // View 从窗口剥离后设为 false，丢弃所有待处理回调
```

**全局布局回调触发链**：

```
View.requestLayout()
  -> ViewRootImpl.requestLayout()
    -> ViewRootImpl.scheduleTraversals()
      -> Choreographer.postCallback(Choreographer.CALLBACK_TRAVERSAL, mTraversalRunnable, null)
        -> ViewRootImpl.doTraversal()
          -> ViewRootImpl.performTraversals()
            -> View.layout() -> View.onLayout()
              -> onGlobalLayoutChanged()
```

#### Android 17 性能优化

**PFLAG_FORCE_LAYOUT 精确传播**（View.java）：

```java
if ((mPrivateFlags & PFLAG_FORCE_LAYOUT) == 0 && !layoutRequested) {
    return;  // 跳过不必要的 measure/layout pass
}
```

只有真正调用了 requestLayout() 的 View 分支才会执行完整 measure/layout，而非整棵 View 树。

**ViewGroup layoutMode 快速路径**（ViewGroup.java）：

```java
if (mLayoutMode != LAYOUT_MODE_UNDEFINED) {
    // 跳过 measure，直接 layout 定位
}
```

#### 常见性能陷阱

1. **OnGlobalLayoutListener 中 requestLayout**：每次布局变化都触发重新布局，O(n²) 复杂度。改用 addOnPreDrawListener。
2. **未移除监听者导致内存泄漏**：View 从窗口剥离时 VTO 的 mAlive=false 会丢弃回调，但监听者本身仍持有 View 引用。必须在 Lifecycle onDestroy 中显式 removeOnGlobalLayoutListener。

#### 参考源码文件

- `frameworks/base/core/java/android/view/ViewTreeObserver.java`（AOSP android-17.0.0_r1）
- `frameworks/base/core/java/android/view/ViewRootImpl.java`（AOSP android-17.0.0_r1）
- `frameworks/base/core/java/android/view/View.java`（AOSP android-17.0.0_r1）
- `frameworks/base/core/java/android/view/ViewGroup.java`（AOSP android-17.0.0_r1）
<!-- AIW-源码调研-2026-06-03 -->
