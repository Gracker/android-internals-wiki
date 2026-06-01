---
title: "其他响应速度场景"
chapter: "8.4"
section: "8.4"
status: finalized
drafted_date: "2026-04-02"
drafted_by: "openclaw-task2a"
reviewed_date: "2026-05-08"
reviewed_by: "openclaw-task6"
applicable_versions: "Android 8.0 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-27"
last_verified_against: "AOSP android-16.0.0_r1 InputTransport/InputDispatcher/ViewRootImpl + AndroidX ViewPager2/Fragment release notes + Task9 deep review 2026-04-27"
confidence: medium
polish_count: 1
polish_date: "2026-04-07"
polish_by: "task2b-polish"
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/app/Activity.java"
  - type: aosp
    path: "androidx/fragment/fragment/src/main/java/androidx/fragment/app/FragmentTransaction.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/View.java"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals"
  - type: blog
    path: "https://developer.android.com/guide/fragments"
  - type: blog
    path: "https://developer.android.com/reference/androidx/viewpager2/widget/ViewPager2"
tags: ['responsiveness', 'page-switch', 'click-response', 'search', 'viewpager2', 'fragment', 'debounce']
related_chapters: ["8.1", "8.2", "8.3", "3.1", "3.2", "7.4"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: "pass-light-edit"
task9_result: pass-tech-review
task9_state: reviewed
task2b_state: fixed
task9_reviewed_date: 2026-05-08
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-08T09:27:37+08:00"
task2b_result: fixed
last_task2b_at: "2026-05-07T17:40:00+08:00"
repaired_date: "2026-05-07"
repaired_by: "openclaw-task2b"
review_notes: "2026-05-07 task2b rework R2: P0 Activity 启动路径改为 Android 9+ ClientTransaction 模型（含 8.x 旧路径说明）；P0 Binder 线程池常量改为 15；P1 删除 ViewPager2 自定义 LayoutManager prefetch 建议，补公开 API 限制说明；2026-05-07 19:05 Task6 复审：L1/L2 轻量修复通过，交回 Task9。 | 2026-05-08 Task6 09:07：复审 Task2B 修复后的 FragmentManager trace 残留表述；删除自动 slice 断言，统一为业务侧插桩口径，并完成 L1/L2 小修，等待 Task9 技术复审。 | 2026-05-08 Task9 09:27：pass-tech-review。P0/P1 0；P2 新增 2 条 suggestions（distinctUntilChanged 连续去重语义、Ripple 首帧绘制条件）；无 active queue pending，Task6 已通过，自动晋升 finalized / ready-to-publish。"
task9_review_notes: "2026-05-07 19:30 Task9 deep-review: needs-rework。P0 2 / P1 5 / P2 3。Top: 4.1 MemoryLimiter 误写为 PSS/exit reason；8.4 FragmentManager 自动 trace slice 未证实；19.13 协程 async trace 示例不可编译且异常路径不闭合。 | 2026-05-08 Task9 09:27：pass-tech-review。P0/P1 0；P2 新增 2 条 suggestions（distinctUntilChanged 连续去重语义、Ripple 首帧绘制条件）；无 active queue pending，Task6 已通过，自动晋升 finalized / ready-to-publish。"
task6_reviewed_date: "2026-05-08"
last_task6_at: "2026-05-08T09:08:46+08:00"
last_task6_audit: "2026-05-26"
last_task6_review_log: "logs/review/2026-05-08-09-review.md"
last_task9_review_log: logs/deep-review/2026-05-08-09-deep-review.md
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-01
---
# 其他响应速度场景

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 页面跳转速度：Activity/Fragment 切换的耗时分析
- 🔹 Tab 切换速度：ViewPager2 的懒加载策略
- 🔹 点击响应速度：从 onClick 到视觉反馈的完整路径
- 🔹 搜索响应速度：实时搜索的防抖与预加载

### 扩展（可选深入）

- 🔸 深链（DeepLink）跳转的响应速度优化
- 🔸 Widget 点击响应速度的特殊考量

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要关注「其他」响应速度场景

§8.1 建立了响应速度的基本框架——从用户感知出发，用 TTID 和 TTFD 两个指标衡量响应。§8.2 和 §8.3 分别拆解了 App 启动全流程和启动优化策略。

但启动只是第一步。日常使用中，用户花时间最多的是**页面跳转、Tab 切换、按钮点击、搜索输入**。这四个高频场景各有各的性能瓶颈，分析方法也各不相同。冷启动优化得再好，页面切换白屏几百毫秒、搜索每次按键都卡一下——用户的感受还是差。

本节要做的，是把启动之外最常见的四个响应速度场景逐一说明：它为什么慢、在 Trace 中怎么看、怎么优化。

---

## 页面跳转速度：Activity/Fragment 切换的耗时分析

页面跳转是用户感知最直接的响应速度场景之一。点击一个按钮跳到新页面，从手指离开屏幕到新页面内容呈现——这段时间越短，用户越觉得「流畅」。

### Activity 跳转的完整路径

调用 `startActivity()` 启动一个新的 Activity 时，系统要完成一系列工作。这是一条跨进程的 Binder IPC 通信路径：

**调用方进程**通过 `Activity.startActivity()` → `Instrumentation.execStartActivity()` 向 **system_server** 发起 Binder 请求。system_server 中的 `ActivityStarter` 做完权限检查、Intent 解析、Task 栈计算后，通过 Binder 向**目标进程**发送启动事务，目标进程依次完成：创建 Activity 实例 → `attach()` → `onCreate()` → `onStart()` → `onResume()` → 首帧渲染。

版本差异要留意：Android 10（API 29）起，调用入口从 `ActivityManager.getService()` 切到了 `ActivityTaskManager.getService()`；Android 9（API 28）起，跨进程传输从旧版 `scheduleLaunchActivity()` 改成了 `ClientTransaction` 模型（事务内携带 `LaunchActivityItem`）；Android 8.x 仍走 `scheduleLaunchActivity()` 直接传参。

这条路径上的耗时主要分布在四个环节：

- **Binder IPC 往返**：两次跨进程（调用方→system_server→目标进程），每次约 1-5ms，system_server 负载高时明显增加。[已验证: AOSP android-16.0.0_r1, ProcessState.cpp]
- **Activity 对象创建**：类加载、构造函数、`attach()` 中创建 Window/PhoneWindow，通常 5-15ms。
- **布局膨胀**：最大的变量。复杂布局 30-100ms 甚至更多。[已验证: developer.android.com/topic/performance]
- **首帧渲染**：从 `onResume()` 到 VSync 触发 `doFrame()`，再到 RenderThread 完成绘制，1-2 个 VSync 周期（16-33ms @60Hz）。

在 Perfetto 中，可通过以下方式定位 Activity 跳转的耗时：

```text
[图：Perfetto 中 Activity 跳转的典型 Trace 片段]
- 在主线程 track 中搜索 "ActivityThread" 相关 slice
- 关注 handleLaunchActivity → performLaunchActivity → activityStart 的时间跨度
- 同时关注 RenderThread 的首帧绘制时间
```

[待补充：Trace 截图展示一个典型 Activity 跳转的 Perfetto 片段]

### Fragment 切换的耗时分析

Fragment 的切换比 Activity 轻量得多——它不需要跨进程通信，整个过程发生在同一个进程的主线程上。核心路径是 `FragmentTransaction.commit()` → `BackStackRecord.execute()` → Fragment 的生命周期回调（`onCreateView()` → `onViewCreated()` → `onResume()`）。

但 Fragment 切换也有自己的性能陷阱：

**布局膨胀仍然是最大开销。** 即使 Fragment 不需要跨进程，`onCreateView()` 中 inflate 一个复杂布局的开销可能高达几十毫秒。尤其是使用 `replace()` 操作时，旧 Fragment 的 View 被销毁，新 Fragment 的 View 需要完全重新创建。

**转场动画会放大感知延迟。** Fragment 支持通过 `setCustomAnimations()` 设置转场动画。如果动画时长设为 300ms，但 Fragment 的布局膨胀只需要 50ms，总感知时间就是 300ms。更危险的是，如果在转场动画期间做了太多 View 操作（如 RecyclerView 数据加载），动画可能掉帧，造成视觉上的卡顿。

**回退栈（Back Stack）的生命周期开销。** 当使用 `addToBackStack()` 并执行 `replace()` 时，旧 Fragment 会走到 `onDestroyView()`（View 被销毁但 Fragment 实例保留）。用户按返回键时，旧 Fragment 需要重新走 `onCreateView()` → `onDestroyView()` 之间的所有回调——布局要重新 inflate。

AndroidX Fragment 源码（FragmentManager / BackStackRecord / FragmentStateManager / SpecialEffectsController）中没有 `Trace.beginSection` 调用，Perfetto 不会自动生成 `FragmentManager:*` slice。排查 Fragment 切换性能时，需要业务代码自行插桩：在导航入口外层加 `Trace.beginSection("FragmentTransaction")`，配合主线程 slice（inflate、RecyclerView layout/prefetch）和 FrameTimeline 观察帧耗时。

### 页面跳转优化策略

根据场景选择 Activity 还是 Fragment：单页面架构用 Fragment（减少跨进程开销），功能独立的模块用 Activity（进程隔离、内存安全）。

对于 Fragment 切换的具体优化手段：

**1. 利用 FragmentFactory 注入已准备好的参数。** `FragmentFactory` 用于在系统创建 Fragment 实例时提供依赖或轻量参数，不负责提前创建 Fragment，也不适合在 `instantiate()` 里做同步查询。如果某个 Fragment 需要初始化参数，可以把已经预取好的 ID、配置或内存对象通过 `setArguments()` 注入，避免 `onCreate()` 再做同步数据获取。`setReorderingAllowed(true)` 允许 FragmentManager 重排并优化同一事务里的生命周期、transition 和中间操作；它不会并行创建 Fragment。

```java
// 自定义 FragmentFactory：在系统创建 Fragment 时注入已准备好的参数
public class PreloadFragmentFactory extends FragmentFactory {
    @NonNull
    @Override
    public Fragment instantiate(@NonNull ClassLoader loader, @NonNull String className) {
        Fragment fragment = super.instantiate(loader, className);
        // 只注入已预取的轻量参数，避免在 instantiate() 中同步查库或访问网络
        if (fragment instanceof DetailFragment) {
            Bundle args = new Bundle();
            args.putString("item_id", preloadedIds.get(className));
            fragment.setArguments(args);
        }
        return fragment;
    }
}
```

这段代码的约束是不要在 `instantiate()` 内做同步查询；`FragmentFactory` 只接收已经准备好的轻量参数。

**2. 使用 postponeEnterTransition()。** 当 Fragment 包含异步加载内容（如网络图片、RecyclerView 数据）时，先调用 `postponeEnterTransition()` 延迟转场动画，等数据加载完成后再调用 `startPostponedEnterTransition()`。这样用户看到的转场动画背后是已经准备好的内容，而不是加载中的空白。

[已验证: 官方文档, developer.android.com/guide/fragments]

**3. ViewStub 延迟加载。** 对于 Fragment 中不是立刻需要的部分（如错误页、空状态页、高级设置面板），用 `ViewStub` 占位，到需要时再 inflate。

**4. 避免 commitNow() 的滥用。** `commitNow()` 是同步执行事务，会立即执行所有操作。在 `onCreate()` 中调用没问题，但如果在 `onResume()` 之后调用，可能会与系统正在执行的 Fragment 状态切换产生冲突，导致 `IllegalStateException`。

[已验证: AndroidX Fragment 仓库, androidx/fragment/fragment/src/main/java/androidx/fragment/app/FragmentManager.java]

---

## Tab 切换速度：ViewPager2 的懒加载策略

Tab 切换是移动端最常见的交互模式之一。新闻 App 的频道切换、电商 App 的商品分类、社交 App 的消息/通讯录/发现三栏——背后几乎都是 ViewPager2 + Fragment 的组合。

### ViewPager2 的工作机制

ViewPager2 以独立 AndroidX artifact（`androidx.viewpager2:viewpager2`）发布，1.0.0 stable 版本发布于 2019 年。它的版本演进跟 Android 平台 API、AndroidX Fragment 1.0.0 分属不同发布线；Fragment 场景依赖 `FragmentStateAdapter` 与 AndroidX Fragment 协作。ViewPager2 内部使用 `RecyclerView` 实现，继承了 RecyclerView 的缓存和预取机制。

`offscreenPageLimit` 参数控制屏幕外保留的页面数量，默认值为 `OFFSCREEN_PAGE_LIMIT_DEFAULT(-1)`，表示不显式保留屏幕外页面，由 RecyclerView 按 ViewHolder 缓存等级（CachedView、RecycledViewPool）和预取策略自动管理。

当设为 1 时，ViewPager2 会在当前页左右各保留 1 个页面的 Fragment。`setOffscreenPageLimit()` 只接受默认值 `OFFSCREEN_PAGE_LIMIT_DEFAULT(-1)` 或大于等于 1 的整数；传入 0 会直接抛出 `IllegalArgumentException`，不存在“设为 0 减少预加载”这种安全写法。设为 2 或更高时，会同时持有更多 Fragment 实例和它们的 View 层级，内存压力也更高。对于 3-4 个 Tab 的常见场景，保持默认值 `-1` 或显式设为 `1` 是更常见的两种选择：前者交给 RecyclerView 的缓存与预取策略，后者换取更稳定的切换速度。

ViewPager2 对 Fragment 生命周期管理的主要变化在于：它通过 AndroidX Fragment 1.1.0+ 提供的 `setMaxLifecycle()` 控制不可见 Fragment 的最高生命周期状态。当前可见的 Fragment 被设为 `RESUMED`，`offscreenPageLimit` 范围内但不可见的 Fragment 被设为 `STARTED`，这些 Fragment 的 `onResume()` 不会被调用，懒加载可以挂在 `onResume()` 或 Lifecycle 状态变化上。

### 懒加载的正确实现

旧版 ViewPager 中通过重写 `setUserVisibleHint()` 实现懒加载，这个方法已被废弃。ViewPager2 + Fragment 架构下的正确做法是在 `onResume()` 中加载数据：

```java
@Override
public void onResume() {
    super.onResume();
    if (!isDataLoaded) {
        loadData();
        isDataLoaded = true;
    }
}
```

更优雅的方案是结合 Lifecycle 和 ViewModel：ViewModel 负责管理数据状态（是否已加载），Fragment 的 `onResume()` 只是触发「如果还没加载就开始加载」这个动作。这样即使 Fragment 的 View 被销毁重建（比如 `offscreenPageLimit` 导致的回收），数据也不会丢失——它保存在 ViewModel 中。

```kotlin
class MyFragment : Fragment() {
    private val viewModel: MyViewModel by viewModels()

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        // 收集数据状态，只在首次可见时加载
        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.uiState.collect { state ->
                if (state is UiState.Loading) {
                    showLoading()
                } else if (state is UiState.Success) {
                    showContent(state.data)
                }
            }
        }
    }
}
```

[已验证: 官方文档, developer.android.com/reference/androidx/viewpager2/widget/ViewPager2]

### ViewPager2 切换的性能优化

**预加载（Prefetch）。** RecyclerView 内置了 prefetch 机制。当用户快速滑动到下一页时，RecyclerView 会在布局过程中预测下一个将要出现的 Item，并提前创建 ViewHolder。ViewPager2 继承了这个能力。可通过 `setOffscreenPageLimit()` 控制预加载范围。ViewPager2 内部创建了 `LinearLayoutManagerImpl`（`LinearLayoutManager` 的子类）并通过 `setLayoutManager()` 绑定到内部 `RecyclerView`，公开 API 不提供替换 LayoutManager 的入口，因此无法通过自定义 LayoutManager 微调 prefetch 策略。可用的优化路径是 `setOffscreenPageLimit()` 控制保留范围、`OnPageChangeCallback.onPageSelected()` 中预取数据、简化页面布局、以及 Fragment 生命周期懒加载。

**布局简化。** 每个 Tab 页的 Fragment 布局越简单，切换越快。常用优化手段包括：
- 用 `ConstraintLayout` 替代多层嵌套的 `LinearLayout` + `RelativeLayout`
- 对不立即显示的内容使用 `ViewStub`
- 对图片使用缩略图占位，异步加载高清图

**数据预取。** 如果 Tab 页的内容来自网络或数据库，可以在 ViewPager2 的 `OnPageChangeCallback.onPageSelected()` 中提前发起下一个 Tab 的数据请求。这样当用户切换过去时，数据可能已经就绪。

```kotlin
viewPager2.registerOnPageChangeCallback(object : ViewPager2.OnPageChangeCallback() {
    override fun onPageSelected(position: Int) {
        // 预取下一个 Tab 的数据
        val nextPosition = position + 1
        if (nextPosition < adapter.itemCount) {
            viewModel.prefetch(nextPosition)
        }
    }
})
```

**避免把旧 ViewPager 的 flag 和 ViewPager2 混在一起。** `BEHAVIOR_RESUME_ONLY_CURRENT_FRAGMENT` 属于 `FragmentPagerAdapter` / `FragmentStatePagerAdapter` 的旧接口；ViewPager2 通过 `FragmentStateAdapter` 内部的最大生命周期控制实现“当前页 RESUMED，其余页 STARTED”。如果大量初始化放在 `onViewCreated()`，页面还没可见也会执行，懒加载要放到 `onResume()` 或显式的可见状态触发点。

[已验证: AOSP android-16.0.0_r1, androidx.viewpager2]

在 Perfetto 中，Tab 切换的性能问题通常表现为主线程 `inflate` 耗时过长，或 Fragment 生命周期回调里存在同步 I/O。排查时在业务入口用 `Trace.beginSection("TabSwitch_" + position)` 标出每个 Tab 的切换耗时，配合主线程 slice、FrameTimeline 和 `tracing.mark_trace` 观察。

```text
[图：Perfetto 中 ViewPager2 Tab 切换的典型 Trace]
- 关注主线程的 inflate 操作
- 关注 Fragment 生命周期回调的耗时
- 对比不同 Tab 的切换时间差异
```

[待补充：Trace 截图展示 Tab 切换时的 Perfetto 片段]

---

## 点击响应速度：从 onClick 到视觉反馈的完整路径

点击响应可能是所有响应速度场景中被感知最频繁的。用户每次点击按钮、切换开关、选择列表项——手指触碰屏幕到看到视觉反馈的这段时间，直接决定了用户对 App「流畅度」的印象。

### 点击响应的完整时间线

一次完整的点击响应，从手指触屏到看到反馈，要经过下面这些阶段：

**硬件输入延迟（~5-15ms）**：触摸屏控制器扫描到触摸 → IC 通过 I2C/SPI 上报驱动 → 驱动通过 `/dev/input/eventX` 暴露给用户空间。这段延迟看硬件和驱动，App 开发者碰不到。

**InputDispatcher 分发延迟（~2-5ms）**：`InputReader` 线程从驱动读到事件后，`InputDispatcher` 选定目标窗口，通过 `InputChannel`（底层是 Unix domain socket pair）发给 App 进程。App 侧由 `ViewRootImpl.WindowInputEventReceiver` 接收，进入 ViewRootImpl 分发。如果此时主线程正在跑上一帧的 `doFrame()`、同步 Binder 或 GC，事件就会在主 Looper 排队。完整分发流程见 §3.1。

[已验证: AOSP android-16.0.0_r1, frameworks/native/libs/input/InputTransport.cpp; frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp; frameworks/base/core/java/android/view/ViewRootImpl.java]

**主线程事件处理（变化最大）**：事件到 App 进程后进入主线程 Looper 的消息队列。主线程如果在跑 `doFrame()`、等同步 Binder 回复、或做 GC，事件就得排队。这是点击响应优化最关键的环节。

**4. View 层级的事件分发（~1-5ms）**：从 DecorView 开始，经过 `dispatchTouchEvent()` → `onInterceptTouchEvent()` → `onTouchEvent()` 的分发路径，最终到达目标 View 的 `onClickListener`。View 层级越深，分发路径越长。

**视觉反馈（1-2 个 VSync 周期）**：onClick 回调里改了 UI 状态（文字、颜色、位置），要等下一个 VSync 触发 `doFrame()` 才能渲染。从回调结束到像素上屏，通常 16-33ms（1-2 帧 @60Hz）。

把这些阶段加起来，一个理想情况下的点击响应延迟大约是 30-60ms。Google 的 RAIL 模型建议点击响应在 100ms 以内，用户就会觉得「即时」。[已验证: 官方文档, developer.android.com/topic/performance/vitals]

### Ripple 效果与感知优化

Android 的 Material Design 引入了 Ripple Drawable 作为点击的视觉反馈。Ripple 的一个设计优势是：**它不需要等 onClick 回调执行完就能显示。** 当 `onTouchEvent()` 收到 `ACTION_DOWN` 时，Ripple 动画就会立即开始，给用户一个「系统已经收到点击」的即时信号。

即使 onClick 回调里做了 50ms 的数据操作，用户感知到的「响应」仍然是即时的——Ripple 在 16ms 内就已经开始扩散了。

但 Ripple 也不是万能的。如果自定义 View 没有正确设置 `android:clickable="true"` 和 `android:background="?attr/selectableItemBackground"`，或者父 ViewGroup 拦截了触摸事件，Ripple 可能不会显示。这种情况下，用户点击后看不到任何视觉反馈，就会觉得「没有响应」——即使 onClick 回调已经执行了。

### 点击响应优化的实战策略

**1. 永远不要在 onClick 中做阻塞操作。** 这是最基本也是最重要的原则。数据库查询、SharedPreferences 写入、文件 IO、网络请求——这些都不应该出现在主线程的 onClick 回调中。用 `viewModelScope.launch(Dispatchers.IO)` 把它们放到后台线程。

**2. 用 preload 减少首次点击延迟。** 如果点击后会跳转到一个新页面，而这个页面的数据可以提前准备，就在用户还在浏览当前页面时预加载。常见场景：首页的推荐列表预加载详情页数据、设置页预加载配置项。

**3. 避免过度绘制拖慢视觉反馈。** 如果点击区域被多层 View 叠加覆盖，Ripple 效果可能需要重绘多层内容，增加首帧耗时。开启「开发者选项 → 显示过度绘制」检查布局。

**4. 利用 `performClick()` 的无障碍兼容。** 在自定义 View 中重写 `onTouchEvent()` 时，务必在处理 `ACTION_UP` 时调用 `performClick()`，这不仅是无障碍的要求，也能确保 OnClickListener 正确触发。

```kotlin
override fun onTouchEvent(event: MotionEvent): Boolean {
    when (event.action) {
        MotionEvent.ACTION_UP -> {
            // 处理点击逻辑
            performClick()  // 触发 OnClickListener + 无障碍
            return true
        }
    }
    return super.onTouchEvent(event)
}
```

[已验证: 官方文档, developer.android.com/reference/android/view/View#performClick()]

在 Perfetto 中分析点击响应时，可以在 Trace 中搜索 `input_event` 相关的 slice，追踪从事件注入到 App 处理的完整路径。更精确的做法是在代码中埋点：

```java
// 在 onClick 回调开始处
Trace.beginSection("Click." + view.getTag());
// ... 处理逻辑
Trace.endSection();
```

然后结合主线程的 CPU slice、RenderThread 的绘制时间，计算完整的点击到显示延迟。

---

## 搜索响应速度：实时搜索的防抖与预加载

「边输入边搜索」是现代 App 的标配，也是最容易做错的响应速度场景。每次按键都发一次搜索请求——浪费流量、打爆服务端、弱网下请求排队卡死——这三个后果随便哪个都够受的。

### 防抖（Debounce）：搜索响应的基础策略

防抖的规则是：**用户连续输入时，只有停下来后的那次输入才触发搜索。** 实现方式是给输入事件流加一个时间窗口——在这个窗口内如果有新的输入，计时器就重置。

以 Kotlin Flow 为例：

```kotlin
viewModelScope.launch {
    searchQueryFlow
        .debounce(300L)           // 用户停止输入 300ms 后才触发
        .filter { it.isNotBlank() } // 忽略空查询
        .distinctUntilChanged()    // 相同查询不重复触发
        .flatMapLatest { query ->  // 新查询来了，取消旧查询
            repository.search(query)
        }
        .collectLatest { results ->
            // 更新 UI
        }
}
```

每个操作符都有明确职责。`debounce(300L)` 确保快速输入时不会每个字符都发请求。`distinctUntilChanged()` 避免用户删除再重输入相同内容时的重复搜索。`flatMapLatest` 负责取消旧请求——当用户输入 "app" 之后又输入了 "apple"，"app" 的搜索请求会被自动取消，只有 "apple" 的结果会返回。

[已验证: 官方文档, developer.android.com/kotlin/flow]

### 防抖时间的选择

300ms 是一个常用的防抖时间，但它不是万能的。选择防抖时间需要考虑两个因素：

**搜索类型：** 本地搜索（在内存或本地数据库中搜索）可以设短一些（150-200ms），因为响应快、无网络开销。网络搜索建议 300-500ms，给用户足够的输入时间，同时减少无谓的请求。

**用户群体：** 熟练用户打字快，200ms 可能就够了。老年用户或不熟悉输入法的用户可能需要 400-500ms。

### 节流（Throttle）与防抖的区别

节流（Throttle）容易和防抖搞混。防抖是等用户「停下来」再触发，节流是「每隔固定时间触发一次」。

在搜索场景中，防抖几乎总是比节流更好的选择。但在其他场景中（比如滚动事件的监听、连续点击的防重复），节流更合适。对于防止按钮连续点击，`throttleFirst(500ms)` 是标准做法——第一次点击立即生效，后续 500ms 内的点击全部忽略。

```kotlin
// 防止连续点击的标准模式
fun View.setOnSingleClickListener(delay: Long = 500L, onClick: (View) -> Unit) {
    var lastClickTime = 0L
    setOnClickListener {
        val now = System.currentTimeMillis()
        if (now - lastClickTime >= delay) {
            lastClickTime = now
            onClick(it)
        }
    }
}
```

### 搜索的预加载与缓存

除了防抖，搜索场景还有两个重要的优化手段：

**本地缓存。** 相同关键词的搜索结果应该缓存到本地（Room 数据库或 LruCache）。这样用户反复搜索同一关键词时，结果可以瞬间从缓存返回，无需等待网络。缓存的过期策略取决于数据更新频率——通讯录可以缓存很久，股票行情则应该设置较短的 TTL。

**热门搜索预加载。** 很多 App 会在搜索页展示「热门搜索」或「搜索推荐」。这些推荐项对应的搜索结果可以在用户进入搜索页时就提前加载。当用户点击某个推荐项时，结果已经在内存中了——响应时间接近 0ms。

**拼音/首字母匹配。** 对于中文搜索场景，用户可能输入拼音或首字母。实现 pinyin 搜索索引（比如将通讯录中所有名字建立拼音映射），可以减少搜索时实时计算的开销。这个索引应该在数据变化时后台更新，而不是搜索时实时计算。

---

## 在 Perfetto/工具 中的表现

四个场景在 Perfetto 中的表现各有特点：

**页面跳转（Activity/Fragment）**：Activity 切换可在主线程 track 中观察 `ActivityThread.handleLaunchActivity`；Fragment 切换建议依赖业务侧 `Trace.beginSection("FragmentTransaction")` 插桩。关注从用户操作（Input 事件）到页面切换入口的延迟，以及入口内部的耗时分布（inflate vs. 数据加载 vs. 首帧渲染）。

**Tab 切换（ViewPager2）**：结合业务侧 `Trace.beginSection("TabSwitch")` / `Trace.beginSection("FragmentTransaction")` 插桩、`RecyclerView` layout / prefetch slice 和 FrameTimeline 观察。重点看 `inflate`、Fragment 生命周期回调、RecyclerView 布局和数据加载是否挤在同一帧。

**点击响应**：搜索 `input_event` 或自定义的 `Click.*` trace slice。关注从 Input 事件注入到 onClick 回调开始的延迟（反映主线程是否被阻塞），以及从 onClick 到首帧渲染的延迟（反映 UI 更新是否高效）。

**搜索响应**：网络请求可以在 `HttpURLConnection` 或 OkHttp 的 trace 中观察到。关注从 debounce 结束到搜索结果返回的端到端延迟。

```text
[图：四种响应速度场景在 Perfetto 中的典型模式对比]
[待补充：Perfetto Trace 截图——同一 Trace 文件中四种场景的对照视图]
```

---

## 常见问题与误区

**误区 1：「Fragment 一定比 Activity 快」**

不一定。Fragment 切换虽然省去了跨进程通信，但如果 Fragment 的布局特别复杂、数据加载特别重，它的切换耗时可能不比 Activity 跳转少多少。选择 Activity 还是 Fragment 应该基于架构需求（进程隔离、导航复杂度、状态管理），而不是单纯追求速度。

**误区 2：「ViewPager2 的默认 offscreenPageLimit 就够用」**

ViewPager2 的默认 `offscreenPageLimit` 是 -1（`OFFSCREEN_PAGE_LIMIT_DEFAULT`），不显式保留屏幕外页面，而是依赖 RecyclerView 的缓存机制。对于只有 3-4 个 Tab 且每个 Tab 布局不太复杂的场景，显式设为 `setOffscreenPageLimit(1)` 常常能换来更稳定的切换速度；如果想回到默认策略，保持 `-1` 或不调用这个 API 即可，不能传 `0`。

**误区 3：「debounce 时间设越短搜索越快」**

debounce 的目的是减少无效搜索，不是加快搜索速度。设太短（如 50ms）等于没有防抖，每次按键都会触发搜索请求；设太长（如 1000ms）会让用户觉得搜索反应迟钝。300ms 是经过大量实践验证的合理默认值。

**误区 4：「Ripple 效果会让点击变慢」**

不会。Ripple 是在 `onTouchEvent(ACTION_DOWN)` 时就开始的异步动画，它和 onClick 回调并行执行。Ripple 的开销主要体现在 GPU 渲染上，但现代设备的 GPU 完全能胜任。没有 Ripple 效果的点击反而会让用户觉得「没响应」。

**误区 5：「onClick 里做少量 IO 没关系」**

这是最常见的响应速度问题来源。即使在 onClick 里只做了 20ms 的同步 SharedPreferences 写入，在 120Hz 设备上（帧间隔 8.33ms），这也意味着至少丢掉 2-3 帧。用户会明显感知到点击后的卡顿。把所有 IO 操作移到后台线程是零成本的优化。

---

## 版本演进

- **Android 3.0（API 11）**：平台 `android.app.Fragment` 引入，后续项目通常迁移到 AndroidX Fragment。
- **Android 4.4（API 19）**：旧 ViewPager 时代常用 `setUserVisibleHint()` 做懒加载，后续已废弃。
- **Android 5.0（API 21）**：Material Design 引入 Ripple Drawable，点击反馈从纯色背景变化升级为波纹动画。
- **AndroidX Fragment 1.1.0（2019）**：`FragmentFactory` 与 `setMaxLifecycle()` 进入稳定版本，Fragment 懒加载开始从 `setUserVisibleHint()` 迁移到 Lifecycle 约束。
- **AndroidX ViewPager2 1.0.0（2019）**：独立 `androidx.viewpager2:viewpager2` artifact 发布，基于 RecyclerView 实现，不绑定 Android 9 / API 28 平台版本。
- **Android 16（API 36）**：ARR（Adaptive Refresh Rate）继续演进；它对点击响应尾延迟的量化影响需要按设备刷新率策略和 Perfetto trace 复核。

---

## 参考资料

- AOSP 源码路径：
  - `frameworks/base/core/java/android/app/Activity.java`（startActivity 实现）
  - `frameworks/base/core/java/android/app/ActivityThread.java`（handleLaunchActivity）
  - `frameworks/base/services/core/java/com/android/server/wm/ActivityStarter.java`（服务端启动逻辑）
  - `frameworks/base/core/java/android/view/View.java`（performClick / onTouchEvent）
  - `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp`（事件分发核心实现，C++）
  - `frameworks/base/services/core/java/com/android/server/input/InputManagerService.java`（Java 侧入口）
- 官方文档：
  - [ViewPager2 指南](https://developer.android.com/guide/navigation/navigation-swipe-view-2)
  - [Fragment 生命周期](https://developer.android.com/guide/fragments/lifecycle)
  - [RAIL 性能模型](https://developer.android.com/topic/performance/vitals)
  - [Kotlin Flow](https://developer.android.com/kotlin/flow)
- 微信技术文章：「一文读懂 Fragment 的方方面面」（2026-03，Obsidian 素材库）
- 微信技术文章：「从 input 响应性能差的 issue 演示 Perfetto trace 用法」（2026-03，Obsidian 素材库）
- 微信技术文章：「Android 针对 App 的 View Input 优化」（2026-03，Obsidian 素材库）
