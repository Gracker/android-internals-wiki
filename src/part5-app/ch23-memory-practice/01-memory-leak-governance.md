---
title: "内存泄漏检测与治理"
chapter: "23.1"
section: "23.1"
status: ready-for-review
drafted_date: "2026-05-13"
reviewed_date: "2026-05-13"
reviewed_by: "openclaw-task6"
task6_result: "pass-light-edit"
task6_state: "revisiting"
task9_state: reviewed
task2b_state: fixed
pipeline_stage: task6_pending
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-06-30"
last_verified_against: "AOSP android-17.0.0_r1 + Android Developers + LeakCanary fundamentals"
confidence: medium
polish_count: 0
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/memory"
  - type: official
    path: "https://developer.android.com/topic/libraries/architecture/coroutines"
  - type: official
    path: "https://square.github.io/leakcanary/fundamentals-how-leakcanary-works/"
  - type: aosp
    path: "platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Handler.java"
  - type: aosp
    path: "platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Message.java"
  - type: aosp
    path: "platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/Activity.java"
  - type: aosp
    path: "platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/Bitmap.java"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 应用稳定性剖析与优化 - Java 内存泄漏监控与 OOM：Java 内存泄漏如何定义？.md]"
tags: [memory-leak, leakcanary, activity-leak, reference-chain, java-heap]
related_chapters: ["23.4", "10.2", "4.3", "19.5"]
last_task6_at: "2026-05-13T22:12:00+08:00"
last_task6_audit: "2026-06-06"
task6_review_notes: "2026-05-13 task6 review: 替换正文中的编辑标签式“用途句”，L1/L2 通过，无新增 L3/L4 回炉项。"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: '2026-05-13'
last_task9_at: '2026-05-13T22:26:00+08:00'
last_task9_audit: "2026-06-30"
last_task9_autofix_at: "2026-06-30"
last_task9_review_log: logs/deep-review/2026-05-13-22-deep-review.md
last_task9_audit_log: logs/deep-review/2026-06-30-00-audit.md
task9_result: auto-fixed
task2b_result: fixed
task9_review_notes: "2026-05-13 Task9 22:26：pass-tech-review。无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。本轮 P2 已写入 suggestions.md。 | 2026-06-30 Task9 闲时抽检 AUTO-FIX：将 AOSP 源码锚点从 android-16.0.0_r1 重锚到 android-17.0.0_r1；复核 Activity/Handler/Message/Bitmap 关键行为未变化，回 Task6 复审。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-19
---

# 内存泄漏检测与治理

## 为什么要做内存泄漏治理

内存泄漏治理处理的是一类延迟暴露的问题：页面已经退出、业务对象已经失效，引用链还把它们留在堆里。单次泄漏可能只占几百 KB，连续页面跳转、长列表滑动、图片缓存叠加之后，Java Heap 会越来越紧，GC 频率升高，卡顿和 OOM 才开始出现。

本节只讨论应用侧能执行的做法：开发阶段用 LeakCanary 把引用链找出来，测试阶段把高风险场景纳入巡检，线上用轻量指标发现趋势，再回到可复现环境修复。ART 堆结构和 GC 细节详见 4.3 节，Java Heap 的对象分配与缓存策略详见 23.4 节，LeakCanary 工具细节详见 19.5 节。

## 泄漏判定：对象失效后仍被 GC Root 触达

[已验证: 官方文档, developer.android.com/topic/performance/memory]

Android Developers 的内存文档把泄漏风险落在两个动作上：避免把对象引用长期放进 static 字段，并按生命周期释放引用对象。落到 Java Heap 上，泄漏可以写成一句更工程化的判断：对象已经超出业务生命周期，仍然存在一条从 GC Root 到它的强引用路径。

这条判断包含两个条件：

- **业务生命周期已经结束**：Activity 已经 `onDestroy()`，Fragment View 已经 `onDestroyView()`，ViewModel 已经 `onCleared()`，或者一次业务请求对应的 Presenter / Controller 已经不再服务当前界面。
- **虚拟机仍认为对象可达**：线程栈、静态字段、JNI 引用、消息队列、单例集合等 GC Root 仍能沿强引用路径找到该对象。

两者缺一项都不能直接定性。刚从页面退出的对象可能还没等到下一次 GC；一个全局缓存对象可能长期存活，但它仍被业务使用。泄漏检测要把“生命周期结束点”和“引用链仍存在”合在一起看。

## 常见泄漏模式：生命周期长短不匹配

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/app/Activity.java]
[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/os/Handler.java]
[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/os/Message.java]

大多数 Java 泄漏不复杂，源头是“长生命周期对象持有短生命周期对象”。排查时先找持有者，再判断它的生命周期是否长于被持有对象。

- **Activity 泄漏**：`Activity.finish()` 后 AOSP 会把 `mFinished` 置为 `true`，`performDestroy()` 中会把 `mDestroyed` 置为 `true`，`isDestroyed()` 也直接返回这个字段。被销毁的 Activity 仍被单例、静态集合、未注销 listener、长任务回调引用时，就形成页面级泄漏。Activity 往往还持有 View 树、Fragment、Adapter、图片对象，单个 Activity 泄漏会把一串对象一起留下。
- **Fragment / Fragment View 泄漏**：Fragment 本体和它的 View 生命周期不同。`onDestroyView()` 后如果还持有 binding、Adapter、RecyclerView callback 或 viewLifecycleOwner 之外启动的任务，会保留整棵 View 树。修复点通常在 `onDestroyView()` 清空 View 相关字段，而不是等到 `onDestroy()`。
- **Handler / Runnable 泄漏**：AOSP `Handler.post()` 会把 `Runnable` 包进 `Message.callback`，`enqueueMessage()` 会把 `Message.target` 指向当前 Handler。只要消息还在队列中，`Message → callback / target → 外部类` 这条路径就存在。Activity 退出前没有执行 `removeCallbacksAndMessages(null)`，延迟消息就可能把页面对象保留到执行时刻。
- **匿名内部类与 lambda 泄漏**：非静态匿名内部类默认持有外部类引用，lambda 只要捕获了 `this`、View、binding、Context，也会产生同类路径。风险点常见于 listener、计时器、线程任务、网络回调和动画回调。
- **Bitmap 间接泄漏**：Android 8.0 之后 Bitmap 像素内存主要由 Native 侧承载，但 AOSP `Bitmap` Java 对象仍保存 `mNativePtr`，并通过 `NativeAllocationRegistry.registerNativeAllocation()` 关联 Native 释放。Java 层 Bitmap 或持有它的 Activity 泄漏时，Native 像素内存也可能被拖住。图片问题的完整治理放到 23.2 节，本节只把它作为泄漏放大器处理。[已验证: AOSP android-17.0.0_r1, frameworks/base/graphics/java/android/graphics/Bitmap.java]

Handler 相关风险可以用下面这段代码定位。重点看两个动作：延迟任务入队，以及页面销毁时清队列。

```kotlin
class DetailActivity : AppCompatActivity() {
    private val handler = Handler(Looper.getMainLooper())

    private val refreshTask = Runnable {
        // 省略无关业务逻辑：这里如果访问 Activity 字段，就会捕获页面对象
        renderLatestData()
    }

    override fun onStart() {
        super.onStart()
        handler.postDelayed(refreshTask, 30_000)
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        super.onDestroy()
    }
}
```

这段代码不能证明所有 Handler 写法都安全。它只覆盖“任务只服务当前页面”的场景；如果 Handler 承载跨页面任务，就要用 token 精确移除当前页面提交的消息，避免误删其他业务消息。

## LeakCanary 原理与接入边界

[已验证: LeakCanary 官方文档, square.github.io/leakcanary/fundamentals-how-leakcanary-works/]

LeakCanary 的价值不是“告诉你内存变大了”，而是在对象失效后给出 GC Root 到泄漏对象的引用路径。它的默认流程有四步：

1. **观察失效对象**：Activity、Fragment、Fragment View、ViewModel 等对象生命周期结束后，交给 `ObjectWatcher`。
2. **弱引用等待回收**：`ObjectWatcher` 持有弱引用，等待一段时间并触发 GC。官方文档说明，等待 5 秒后弱引用仍未清除的对象会被视为 retained object。
3. **达到阈值后 dump heap**：应用可见时默认 retained object 阈值为 5，应用不可见时为 1。达到阈值后才生成 `.hprof`，避免每个 retained object 都立刻触发停顿。
4. **Shark 分析引用链**：Shark 解析 Hprof，寻找 retained object 到 GC Root 的路径，并按相同泄漏签名聚合结果。LeakCanary 还会把 Application Leak 和已知 Library Leak 分开，方便团队决定处理策略。

接入时建议把 LeakCanary 放在 debug / QA 包。Heap dump 会冻结进程一段时间，Hprof 文件也包含对象内容，不适合直接作为默认线上能力。线上需要的是趋势发现和样本触发，引用链分析仍应回到可控环境完成。

自定义对象观察适合业务组件、Presenter、长生命周期 Controller。下面这段代码展示对象生命周期结束后主动交给 `ObjectWatcher` 的接入点。

```kotlin
class SearchPresenter(
    private val objectWatcher: ObjectWatcher
) {
    fun destroy() {
        cancelRequests()
        objectWatcher.watch(this, "SearchPresenter.destroy() called")
    }

    private fun cancelRequests() {
        // 省略无关代码：取消网络请求、移除 listener、停止计时器
    }
}
```

这类接入要避免泛化。只有生命周期边界明确的对象才适合 watch；缓存、进程级单例、连接池这类长期对象不应被作为泄漏对象观察，否则会制造噪声。

## 线上泄漏检测：采趋势，不在用户设备上重分析引用链

[已验证: 官方文档, developer.android.com/topic/performance/memory]

线上泄漏治理的目标是发现“哪类页面、哪类路径、哪类版本在持续增长”，而不是把用户设备变成 MAT。建议把线上方案拆成三层：

- **低成本指标层**：按页面、进程、前后台状态采集 Java Heap used / max、Native Heap、PSS、RSS、GC 次数、页面停留时长、Activity 实例数。Java Heap 可用 `Runtime.totalMemory() - Runtime.freeMemory()` 低成本获取；PSS / Native Heap 采样要控制频率，避免把监控本身做重。
- **场景归因层**：记录页面进入、退出、关键业务动作、图片加载、长任务启动和取消。泄漏常常和路径有关，只看全局内存曲线很难定位。
- **样本追踪层**：线上只产出候选页面和版本范围。回到 debug / QA 包后，用 LeakCanary 或 Hprof 工具复现，再用引用链确认修复。涉及用户隐私、文件大小和停顿风险的 heap dump 不进入默认线上路径。

判断是否存在页面级泄漏，可以看“退出页面后若干秒内 Activity 实例数是否下降”“同一路径重复进入退出后 Java Heap 是否阶梯式上升”“GC 后 used heap 是否回到稳定区间”。这些指标只能给出方向，不能替代引用链结论。

## 治理优先级与修复策略

泄漏列表进入修复阶段后，不按“谁先发现”排序，按影响范围和修复成本排序更稳。

| 优先级 | 典型问题 | 处理策略 |
| --- | --- | --- |
| P0 | 首页、核心交易页、播放页、相机页等高频页面泄漏 Activity 或 Fragment View | 当轮修复；用 LeakCanary trace 验证引用链断开；加回归用例 |
| P1 | 长列表、图片页、WebView、地图、IM 会话等重资源页面泄漏 | 限期修复；同步检查 Adapter、listener、协程、图片请求 |
| P2 | 低频页面的小对象泄漏，或者只在 debug 工具链触发 | 排入常规债务；保留 leak signature 和复现路径 |
| P3 | 已知系统 / 三方库 Library Leak，业务侧无法直接释放 | 记录版本、机型、规避方案；评估升级依赖或白名单 |

修复时沿引用链逐段处理：

- **生命周期绑定**：把订阅、listener、callback、动画、计时器绑定到对应生命周期。页面级对象在 `onDestroy()` 释放，Fragment View 相关对象在 `onDestroyView()` 释放。
- **移除队列任务**：Handler、Executor、协程、Rx、Flow 都要有取消点。只服务当前页面的任务，页面退出时全部取消；跨页面任务用 token、job id 或 owner 做精确取消。
- **减少全局持有**：单例和 static 字段只保存 Application Context、配置、轻量状态；不保存 Activity、View、Fragment、binding、Adapter。
- **拆分重资源**：WebView、Bitmap、大缓存、地图组件、播放器对象要有显式 release 路径。页面泄漏带来的资源放大效应比普通对象更明显。
- **验证收束**：修复后重复执行原复现路径，确认 retained object 数量归零或 leak signature 消失，再看线上候选指标是否回落。

## Kotlin Coroutine 与 Flow 的泄漏风险

[已验证: 官方文档, developer.android.com/topic/libraries/architecture/coroutines]

协程泄漏的根源仍是生命周期长短不匹配。Android 官方文档说明，`viewModelScope` 中启动的协程会在 ViewModel cleared 时自动取消；生命周期相关任务应使用 `lifecycleScope`、`repeatOnLifecycle` 等 API，让任务随 Lifecycle 状态启动和停止。

风险最高的写法通常有三类：

- **使用全局作用域承载页面任务**：`GlobalScope.launch` 或进程级 scope 捕获 Activity / View / binding，页面退出后任务仍继续执行。
- **Flow 收集未随生命周期停止**：在 `onCreate()` 里直接 `launch { flow.collect { render(it) } }`，页面进入 STOPPED 后仍可能继续收集和渲染。
- **回调式 API 没有 awaitClose / removeListener**：`callbackFlow` 注册 listener 后没有在 `awaitClose` 中注销，Flow 停止收集后 listener 仍保留页面对象。

下面这段代码展示 Flow 收集与 Fragment View 生命周期绑定的写法，重点看 `viewLifecycleOwner` 和 `repeatOnLifecycle`。

```kotlin
class FeedFragment : Fragment(R.layout.feed) {
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        viewLifecycleOwner.lifecycleScope.launch {
            viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.items.collect { items ->
                    render(items)
                }
            }
        }
    }
}
```

这段写法让收集任务随 View 生命周期停止和重启。Fragment 本体存活但 View 已销毁时，不会继续把旧 View 树留在收集回调里。Compose 场景同理，优先使用 `LaunchedEffect`、`DisposableEffect`、`collectAsStateWithLifecycle` 这类和组合生命周期绑定的入口。

## 排查清单

一次泄漏问题可以按下面顺序处理：

1. **确认对象是否失效**：Activity 看 `isDestroyed()` / 页面退出点，Fragment View 看 `onDestroyView()`，业务对象看明确的 `destroy()` / `close()`。
2. **确认 retained object**：用 LeakCanary 等待 GC 后的结果，不把“刚退出页面还活着”直接当泄漏。
3. **读引用链**：从 GC Root 往下找第一个业务可控引用，通常是 static 字段、单例集合、Handler Message、listener、协程 Job、Adapter、缓存。
4. **按生命周期修复**：移除、取消、置空、注销、release，动作必须落在和对象失效一致的生命周期回调里。
5. **重复复现路径**：至少执行两轮进入退出，确认相同 leak signature 不再出现。
6. **回看线上趋势**：对应页面的 used heap、PSS、Activity 实例数、OOM / 卡顿趋势回落后，再关闭问题。

内存泄漏治理的收益来自稳定重复的流程。工具负责找引用链，工程侧要负责生命周期边界和修复流程。
