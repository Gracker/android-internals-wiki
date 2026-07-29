---
title: "FragmentTransaction 提交时序与主线程卡顿"
chapter: "7.17"
status: ready-for-review
drafted_date: "2026-05-20"
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37), AndroidX Fragment 1.0+"
last_verified: "2026-05-20"
last_verified_against: "AndroidX androidx-main Fragment source; Android Developers Fragment transactions / Slow rendering docs; AOSP android14-release platform Fragment as deprecated reference"
confidence: high
sources:
  - type: aosp
    path: "https://raw.githubusercontent.com/androidx/androidx/androidx-main/fragment/fragment/src/main/java/androidx/fragment/app/FragmentTransaction.java"
  - type: aosp
    path: "https://raw.githubusercontent.com/androidx/androidx/androidx-main/fragment/fragment/src/main/java/androidx/fragment/app/BackStackRecord.java"
  - type: aosp
    path: "https://raw.githubusercontent.com/androidx/androidx/androidx-main/fragment/fragment/src/main/java/androidx/fragment/app/FragmentManager.java"
  - type: official
    path: "https://developer.android.com/guide/fragments/transactions"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/render"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/fragment"
  - type: research
    path: "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-01-fragmenttransaction-commit-source-chain.md"
  - type: research
    path: "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-05-fragmenttransaction-commit-source-chain.md"
  - type: research
    path: "DeepResearch/2026-05-08-fragment-transaction-commit-source-chain.md"
tags: [fragment, jank, main-thread, choreographer, jetpack]
related_chapters: ["7.3", "7.4", "8.1", "13.3", "13.10", "13.14", "22.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-20"
gap_source: "素材驱动/官方文档/AOSP结构"
gap_score: 17
---

# 7.17 FragmentTransaction 提交时序与主线程卡顿

## 版本锚点与分析对象

本章的平台锚点是 Android 17 / API 37 / `android-17.0.0_r1`，用于解释主线程 Looper、Choreographer、ViewRootImpl 和 FrameTimeline。Fragment 属于独立发布的 AndroidX 库，不能用 Android 平台版本代替库版本。

截至 2026 年 7 月，AndroidX Fragment 稳定版为 1.8.9。本章的库源码锚点是该发行区间末端 commit `f39ca3510efb2347ebfef231e25a3e804922450d`。官方已将 Fragment 标为维护模式，但存量 View/Fragment 项目的切换性能仍需按库源码分析。平台 `android.app.Fragment` 自 API 28 起废弃，只用于理解历史项目。

一次 Fragment 页面切换至少有四个不同时间点：

1. 业务调用 `commit()`；
2. `FragmentManager` 在宿主线程执行事务；
3. 目标 View 完成创建、生命周期推进和特殊效果调度；
4. App Window 经过 traversal、RenderThread、BufferQueue、SurfaceFlinger 与 HWC 后呈现在屏幕上。

`commit()` 耗时短，只能说明入队快。`commitNow()` 返回，也只能说明同步事务推进结束；它没有等待目标像素显示，也没有等待异步动画播放完毕。

## 提交 API 的时序语义

| API | 源码路径 | 同步范围 | 约束与风险 |
|---|---|---|---|
| `commit()` | `commitInternal(false, true) → enqueueAction()` | 调用点主要完成状态检查与入队 | 宿主保存状态后抛出异常；重成本在后续执行 |
| `commitAllowingStateLoss()` | `commitInternal(true, true) → enqueueAction()` | 与 `commit()` 同样异步 | 允许丢失已保存状态后的 UI 变更；Manager 已脱离或销毁时可能直接丢弃事务 |
| `commitNow()` | `disallowAddToBackStack() → execSingleAction()` | 在调用返回前执行该事务、推进 Fragment 状态并创建/attach View | 必须在宿主主线程；不能 `addToBackStack()`；保存状态后抛出异常 |
| `commitNowAllowingStateLoss()` | `disallowAddToBackStack() → execSingleAction(..., true)` | 与 `commitNow()` 同步 | 允许状态丢失；Manager 已脱离或销毁时可能丢弃；仍不能进 back stack |
| `executePendingTransactions()` | `execPendingActions(true)`，随后 `forcePostponedTransactions()` | 执行当前 Manager 的全部 pending transactions | 会带入其他提交者的成本，还会强制启动 postponed transactions |

`allowStateLoss` 处理状态保存与恢复语义，不会减少 inflate、依赖注入、生命周期回调、列表绑定、布局或 transition 的工作量。为了“更快”而改用它，会引入恢复后 UI 丢失或不一致的风险。

`commitNow()` 适合需要明确同步顺序、且事务不进 back stack 的少数场景。它不能作为通用卡顿修复：若调用发生在输入回调、滚动、当前帧动画或启动关键区间，Fragment 创建成本会直接占用该主线程区间。

## AndroidX Fragment 1.8.9 的异步执行路径

稳定版源码中的主要调用关系如下：

```text
BackStackRecord.commit()
  → commitInternal(false, true)
  → FragmentManager.enqueueAction()
      → mPendingActions.add()
      → scheduleCommit()
          → host Handler.post(mExecCommit)

mExecCommit.run()
  → execPendingActions(true)
  → generateOpsForPendingActions()
  → removeRedundantOperationsAndExecute()
  → executeOpsTogether()
      → executeOps()
      → FragmentStateManager.moveToExpectedState()
      → SpecialEffectsController.executePendingOperations()
      → runOnCommitRunnables()
```

这条路径说明三个时序特征。

### 一次 Handler post 可以执行多笔事务

`scheduleCommit()` 只在 `mPendingActions.size() == 1` 时移除旧 callback 并 post `mExecCommit`。同一执行窗口里追加的其他 action 会留在 pending list；`execPendingActions()` 生成 records 时可能一并处理。因此，一个很长的 `mExecCommit` 不一定由 trace 中最近那次 `commit()` 独自造成。

分析时要记录事务 ID、路由来源、目标 Fragment 和提交时间。Navigation、DialogFragment、子 FragmentManager、返回栈 pop 也可能向同一主线程窗口增加工作。

### reordering 会改变中间状态与分组

`removeRedundantOperationsAndExecute()` 按 `mReorderingAllowed` 对相邻 records 分组。官方文档要求每笔事务调用 `setReorderingAllowed(true)`，这样多笔事务一起执行时，中间 Fragment 可跳过无意义的生命周期和动画。

它不是固定比例的提速开关。单笔简单事务可能看不到耗时变化；多笔 add/replace/pop、transition 或 back stack 场景更容易受益。启用后仍需验证回调顺序、共享元素和业务假设。

### 特殊效果可能跨越事务返回点

`executeOpsTogether()` 在状态推进后调用 `SpecialEffectsController.executePendingOperations()`，启动 add/remove/show/hide 对应的动画或 transition。`runOnCommit()` 的 runnable 在同一事务执行流程稍后运行，但它不能与 `addToBackStack()` 共用，也不表示动画完成或屏幕已 present。

这一区分对埋点很有用：`runOnCommit` 可以标记“事务操作已经执行”，首个目标 SurfaceFrame 则标记“Window 已提交该画面”，DisplayFrame/present 才接近用户看到的时刻。

## Handler、Choreographer 与 traversal 的相对顺序

`FragmentManager` 使用宿主 `Handler` 调度 `mExecCommit`。Android 17 的 View 帧调度由 Choreographer 驱动，按 INPUT、ANIMATION、INSETS_ANIMATION、TRAVERSAL、COMMIT 等阶段推进。两套调度共享主 Looper，但没有“`commit()` 后必定在下一个 VSync 前执行”的契约。

主 MessageQueue 的现有消息、同步屏障、异步 Choreographer 消息、提交发生时刻都会改变顺序：

- 事务若在普通主线程消息中入队，`mExecCommit` 可能在后续 VSync 前执行；
- 事务若在当前 `doFrame` 的输入或动画回调中入队，异步提交通常要等当前回调返回；
- `commitNow()` 会在当前调用栈同步推进 Fragment，可能把创建和状态变更压进当前帧；
- View attach、`requestLayout()` 和 `invalidate()` 只建立后续 traversal 的条件，不代表当场完成绘制。

trace 中应直接观察 Looper message、`doFrame`、Fragment marker 和 traversal 的位置，不要按 API 名推测执行帧。

Android 17 的普通 Fragment View 仍走 App Window 渲染路径：

```text
Fragment 状态推进与 View attach
  → requestLayout / invalidate
  → Choreographer traversal
  → ViewRootImpl.performTraversals()
  → ThreadedRenderer / RenderThread
  → BLAST BufferQueue
  → SurfaceFlinger / HWC
  → present
```

UI 线程完成 traversal 后，RenderThread、GPU、BufferQueue 和系统合成仍可能延后结果。Fragment 分析应以用户看到的目标帧为终点。

## 长帧成本从哪里来

FragmentManager 的队列和状态机只是一部分。常见成本可按阶段拆开：

| 阶段 | 典型工作 | 常见风险 |
|---|---|---|
| action 生成与事务分组 | pending actions、back stack、op expand/collapse、reordering | 同一窗口提交过多、复杂 pop/replace、predictive back 中断 |
| Fragment 实例与状态恢复 | FragmentFactory、SavedState、ViewModel、依赖注入 | 主线程创建大对象、读取磁盘、恢复数据过大 |
| View 创建 | `onCreateView()`、XML inflate、自定义 View 构造 | 复杂层级、资源解析、同步初始化 |
| View 初始化 | `onViewCreated()`、listener/adapter、状态绑定 | 数据库/文件 IO、同步 Binder、SDK 初始化 |
| 生命周期推进 | `onStart()`、`onResume()`、observer 变为 active | observer 同步分发、重复注册、批量业务工作 |
| 首次 traversal | measure/layout/draw、Insets、ComposeView 首次 composition | 多轮 layout、昂贵测量、图片或纹理准备 |
| 列表首屏 | adapter 初始化、首批 bind、Diff、预取 | 大量 bind、主线程 Diff、同步解码 |
| special effects | Animator、Transition、共享元素、postpone | 等待条件不稳定、额外布局、多个 transition 互相取消 |

若 `mExecCommit` 区间很短，而目标帧的 traversal 或 RenderThread 很长，责任不应写成“FragmentManager 慢”。反过来，若 records 数量、状态推进或 SpecialEffectsController 已占据主要主线程时间，再检查事务组织、返回栈和动画配置。

## Perfetto 诊断步骤

### 1. 定义用户可见的终点

页面切换至少记录三个 marker：

- 输入或路由开始；
- 事务入队与执行完成；
- 目标页面首个可见内容或可交互状态。

首个容器背景、首个完整内容和可交互状态可能落在不同帧。团队要为具体页面选定终点，避免只优化一个很早出现的空壳帧。

### 2. 从 DisplayFrame 回到 App Window

Android 12+ 在 FrameTimeline 中选择异常 DisplayFrame，再定位对应 App SurfaceFrame。确认 jank 来自 App 侧还是 SurfaceFlinger 侧，然后检查 UI Thread 和 RenderThread。Android 8—11 可回退到 `doFrame`、View/graphics atrace、FrameMetrics 和 sched。

Fragment View 通常属于宿主 App Window，因此 FrameTimeline 能覆盖它的 Window 提交。页面内若还包含 `SurfaceView` 视频、相机或地图独立层，要把宿主 UI 与内容 Layer 分开。

### 3. 找到执行事务的 Looper message

从异常帧向前查看主线程：

- `commit()` marker 位于哪个消息；
- `mExecCommit` 或生命周期 marker 位于哪个消息；
- 期间是否有输入、Binder、锁、GC、IO 或其他业务任务；
- View traversal 与事务执行处于同一帧还是相邻帧。

仅有采样调用栈时，短小 FragmentManager 方法可能漏采。自定义 trace section 能提供更稳定的时间边界。

### 4. 拆开生命周期与首屏业务

下面的 helper 用于给短小同步区间增加系统 trace section：

```kotlin
inline fun <T> tracedSection(name: String, block: () -> T): T {
    Trace.beginSection(name)
    return try {
        block()
    } finally {
        Trace.endSection()
    }
}
```

这里的 `Trace` 是 `android.os.Trace`。section 名应短且稳定，禁止拼入用户数据；`finally` 保证异常路径也能正确结束 section。

下面的示例分别标记事务入队、View 创建和首屏同步绑定：

```kotlin
tracedSection("Route.enqueue.Home.Detail") {
    supportFragmentManager.commit {
        setReorderingAllowed(true)
        replace<DetailFragment>(R.id.container)
        addToBackStack("detail")
    }
}

class DetailFragment : Fragment() {
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View = tracedSection("Detail.createView") {
        inflater.inflate(R.layout.detail, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        tracedSection("Detail.bindInitialUi") {
            setupRecyclerView(view)
            bindCachedState()
        }
    }
}
```

`Route.enqueue` 只测 `commit()` 调用与入队；它不会覆盖 `mExecCommit`。两个 Fragment section 能说明同步回调成本，目标 SurfaceFrame 继续承担 traversal 到 Window 提交的证据。网络、图片和异步流应有各自 marker。

### 5. 核对系统负载

主线程 Runnable 而未运行时，检查同核线程、后台线程池、Binder 和 cgroup；主线程 Running 时，检查具体 section 与调用栈。Fragment 页面切换恰好遇到系统 CPU 争抢时，不能把调度等待归入 inflate。

## 常见误判

- **`commit()` 快等于页面切换快**：它主要测入队，事务执行与目标帧在后面。
- **`commitNow()` 返回等于用户已看到页面**：View attach 后仍有 traversal、RenderThread 和系统合成。
- **`onViewCreated()` 完成等于首屏完成**：列表 bind、Compose composition、图片和异步数据可能继续工作。
- **`runOnCommit()` 等于 transition 完成**：该 runnable 位于事务执行流程，special effect 可跨帧运行。
- **一次 `mExecCommit` 只属于最近事务**：pending list 可以包含多个 action。
- **FrameTimeline 红帧等于 FragmentManager 计算慢**：要区分事务、生命周期、traversal、RenderThread 和系统侧。
- **`setReorderingAllowed(true)` 会自动修复所有卡顿**：它优化事务状态变化，不会消除业务 IO、inflate 或图片成本。
- **`allowStateLoss` 是性能选项**：它改变状态一致性和丢弃行为。
- **打开 Fragment debug log 后的数据可直接当基线**：详细日志会增加开销，应在单独诊断轮次使用。
- **FragmentScenario 的耗时等于生产页面切换**：测试宿主、数据、Window 与动画环境可能不同。

## 优化策略与边界

### 事务组织

- 每笔事务启用 `setReorderingAllowed(true)`，并回归生命周期、动画和 back stack。
- 同一个用户动作产生的 add/remove/show/hide 尽量在一笔 transaction 表达。
- 防止一次点击重复 navigate，但要保留无障碍和快速返回等有效交互。
- 避免用 `executePendingTransactions()` 等待某个 View；它会扫当前 Manager 的全部 pending work。
- `commitNow()` 只用于需要同步顺序且不进 back stack 的场景，并测量调用点是否占用帧预算。

### 主线程工作

- `onCreateView()` 只创建 View；数据库、文件、网络、模型解析和 SDK 初始化移出同步路径。
- `onViewCreated()` 绑定首帧必需状态，非首屏内容按异步数据和分页补充。
- 检查 DI graph、SavedState、ViewModel 初始化和 observer 激活是否重复执行。
- RecyclerView 的 Diff 放在合适的后台执行器，图片解码与变换交给图片管线；首批 bind 数量按目标设备测量。
- ComposeView 的 composition、measure 和资源准备要单独标记，不能归在 `onViewCreated()` 名下。

### View 与内存取舍

`replace()` 可能在返回时重建旧页面 View；`add()/hide()/show()` 可以保留 View 与状态，却增加常驻内存、observer、资源和恢复复杂度。选择依据应包含切换频率、View 重建成本、内存压力和后台生命周期，不能只比较一轮切换帧时间。

预创建 Fragment 或预 inflate 也会移动成本，并可能增加启动耗时与内存。只有目标页面命中率高、收益在低端设备上稳定、生命周期没有副作用时，才适合保留。

### 动画与共享元素

- 共享元素依赖源/目标 View 的稳定尺寸与名称，目标图片或数据未就绪时可能推迟 transition。
- `postponeEnterTransition()` 要有明确的完成条件和超时，并覆盖取消、返回和进程恢复。
- 连续 navigate、pop 和 predictive back 手势会让 transition 状态更复杂；Fragment 1.8.x 对这类场景有多次修复，应用应记录精确库版本。
- 缩小共享元素数量、减少多轮 layout 或改用更简单的过渡后，需要用相同手势与数据集复测。

## Navigation 与 DialogFragment

Navigation 的 `navigate()` 在进入 FragmentManager 前还要处理 route、arguments、Navigator 和 back stack。分析时至少放置 `navigate` 外层 marker、Fragment 事务/生命周期 marker 和目标帧。只看 FragmentManager 区间会漏掉导航层或参数构建成本。

DialogFragment 的 `show()` 使用异步提交，`showNow()` 同步执行。弹窗若由点击、滚动或当前帧动画触发，`showNow()` 会把 Dialog Fragment 创建与 Window 相关工作放进调用区间；是否可接受应由输入到首个弹窗帧的测量决定。

Android 17 的 predictive back 可能让 pop transition 跨多个手势帧。FragmentManager 1.8.x 源码维护 in-flight transitioning operation，并在新 action 到来时处理取消或重新提交。复现脚本要区分手势完成、取消和快速重复返回。

## 性能验证

FragmentScenario 适合验证 Fragment 生命周期、状态恢复和回调顺序。用户可见帧性能应使用真实 Activity/Navigation 宿主，配合 Macrobenchmark、Perfetto 或可重复的端到端测试。

建议至少比较这些指标：

| 指标 | 起点与终点 |
|---|---|
| 输入到容器变化 | 点击事件到目标容器首次可见 |
| 输入到完整首屏 | 点击事件到定义好的完整内容帧 |
| 输入到可交互 | 点击事件到目标页面能响应关键操作 |
| App frame duration | 对应 SurfaceFrame 的 Actual duration 与 jank type |
| 主线程分段 | enqueue、事务执行、createView、bind、traversal |
| RenderThread/GPU | 目标 Window 的绘制与完成时间 |
| 稳定性 | P50/P95/P99、连续坏帧、低端机与高刷设备 |

对照实验一次只改变一个因素，例如事务合并、移除同步 IO、关闭共享元素或调整列表首批绑定。`commit()` 与 `commitNow()` 的 back stack 语义不同，不能只凭耗时把二者当成等价方案。

## 章节导航

| 继续排查 | 章节 |
|---|---|
| 帧调度、FrameTimeline 与 App/SF 归因 | `7.3`、`7.4` |
| 页面切换场景手册 | `7.15` |
| 启动与首帧 | `8.1` |
| Perfetto 采集与 SQL | `13.3`、`13.10`、`13.14` |
| RecyclerView 首屏绑定 | `22.2` |

## 源码与官方资料

- [AndroidX Fragment 1.8.9 release notes](https://developer.android.com/jetpack/androidx/releases/fragment#1.8.9)
- [Fragment transactions 官方指南](https://developer.android.com/guide/fragments/transactions)
- [AndroidX 1.8.9 `BackStackRecord`](https://android.googlesource.com/platform/frameworks/support/+/f39ca3510efb2347ebfef231e25a3e804922450d/fragment/fragment/src/main/java/androidx/fragment/app/BackStackRecord.java)
- [AndroidX 1.8.9 `FragmentManager`](https://android.googlesource.com/platform/frameworks/support/+/f39ca3510efb2347ebfef231e25a3e804922450d/fragment/fragment/src/main/java/androidx/fragment/app/FragmentManager.java)
- [AndroidX 1.8.9 `FragmentTransaction`](https://android.googlesource.com/platform/frameworks/support/+/f39ca3510efb2347ebfef231e25a3e804922450d/fragment/fragment/src/main/java/androidx/fragment/app/FragmentTransaction.java)
- [AndroidX 1.8.9 `FragmentStateManager`](https://android.googlesource.com/platform/frameworks/support/+/f39ca3510efb2347ebfef231e25a3e804922450d/fragment/fragment/src/main/java/androidx/fragment/app/FragmentStateManager.java)
- [AOSP Android 17 `Choreographer`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java)
- [AOSP Android 17 `ViewRootImpl`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [Android slow rendering](https://developer.android.com/topic/performance/vitals/render)
- [Macrobenchmark `FrameTimingMetric`](https://developer.android.com/reference/androidx/benchmark/macro/FrameTimingMetric)
- [Fragment testing](https://developer.android.com/guide/fragments/test)
