---
title: "LeakCanary"
chapter: "19"
section: "19.05"
status: finalized
drafted_date: "2026-04-24"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-25"
last_verified_against: "LeakCanary fundamentals, changelog 2.6 ServiceWatcher, recipes / leakcanary-android-instrumentation"
confidence: medium
tags: [apm, memory, leak-detection, debug-tools, shark]
related_chapters: ["19.0"]
sources:
  - type: official
    path: "https://square.github.io/leakcanary/"
  - type: official
    path: "https://square.github.io/leakcanary/fundamentals-how-leakcanary-works/"
  - type: official
    path: "https://square.github.io/leakcanary/changelog/"
  - type: official
    path: "https://square.github.io/leakcanary/recipes/"
pipeline_stage: ready-to-publish
task6_state: "reviewed"
task6_result: "pass-light-edit"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-04-25"
last_task6_audit: "2026-07-04"
task9_state: reviewed
task9_result: pass-tech-review
task9_reviewed_date: "2026-04-26"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-04-26T23:27:38+08:00"
last_task9_audit: "2026-06-15"
task2b_state: fixed
task2b_result: fixed
last_task2b_at: "2026-04-25T08:51:01+08:00"
repaired_date: "2026-04-25"
repaired_by: "openclaw-task2b"
review_round: 5
review_notes_5: "2026-04-25 task6 re-review (round 5): pass-light-edit. L1: 1 banned word fix (可以看到→直接陈述) in 03-metrics; AI句式 3→1 in 03-metrics. 01-rendering-overview and 05-leakcanary clean. No B-class issues across all 3 chapters."
deepseek_polish_state: done
last_deepseek_polish_at: 2026-05-26
---

# LeakCanary

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 说明 LeakCanary 是 Debug / QA 阶段的本地泄漏诊断工具，不是线上内存平台；写清它和 KOOM、Profiler 的分工。
- 🔹 [保留判定] 展开 ObjectWatcher、弱引用、GC、retained object、heap dump、Shark 分析的流程。
- 🔹 [默认观察对象] 列出 Activity、Fragment、ViewModel、View、Service 等默认对象，说明 AndroidX / Lifecycle 依赖关系。
- 🔹 [自定义观察] 给出业务对象 `ObjectWatcher` 示例，说明何时观察、何时取消、如何避免测试噪声。
- 🔹 [leak trace 读法] 教读者区分 GC root、引用路径、suspect reference、retained size；必须写一个逐行阅读案例。
- 🔹 [泄漏模式] 覆盖 static、Handler / Runnable、Coroutine、Flow、Listener、Adapter、匿名内部类、Context、Dialog、WebView。
- 🔹 [Application / Library] 说明 Application Leak 和 Library Leak 的处理策略，哪些可以暂缓，哪些必须修。
- 🔹 [Release 边界] 写清为什么 Release 中要克制使用 heap dump，涉及性能、隐私、文件大小和用户体验。
- 🔹 [线上联动] 说明 KOOM / APM 发现页面内存异常后，如何回到 Debug 包复现并用 LeakCanary 验证修复。
- 🔹 [测试集成] 说明 instrumentation test、CI 泄漏门禁、已知泄漏白名单和误报维护方式。

### 扩展（可选深入）

- 🔸 增加 Fragment / RecyclerView / coroutine 三个典型泄漏案例，每个案例包含代码片段和 leak trace 解释。
- 🔸 补充 Shark 分析产物的字段说明，区分对象数量、retained size 和泄漏路径。
- 🔸 对 LeakCanary 版本、默认观察对象、AndroidX 集成方式做官方文档核对。
- 🔸 增加“泄漏修复后如何验证”的清单，覆盖本地复现、自动化测试、线上指标回看。
- 🔸 补充不适合 LeakCanary 直接判断的问题，比如 native 内存上涨、Bitmap 复用策略、系统 WebView 问题。

### 流水线加工要求

- 泄漏案例必须能从代码走到 leak trace，再走到修复方式。
- 不要只写“释放引用”，要指出哪个对象持有哪个对象、生命周期为什么不匹配。
- 涉及线上样本时必须说明数据只用于定位入口，不用 LeakCanary 直接在用户设备上 dump。

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## LeakCanary 是本地泄漏诊断工具

LeakCanary 是 Square 开源的 Android 内存泄漏检测库。它最适合开发和测试阶段使用：当 Activity、Fragment、ViewModel 或业务对象在应该释放后仍然存活时，LeakCanary 会 dump heap、分析引用链，并把可疑引用标出来。

它不应该被放进“线上 APM 框架”同一格里比较。LeakCanary 的强项是把本地泄漏讲清楚，线上内存趋势、采样、平台聚合和 OOM 分析不是它的默认目标。

## 它怎样判断对象被保留

LeakCanary 不会在对象一销毁时就立刻 dump heap。实际流程如下：

1. `Activity.onDestroy()`、`Fragment.onDestroy()`、`Fragment.onDestroyView()`、`ViewModel.onCleared()` 这些生命周期结束点把对象交给 `AppWatcher` / `ObjectWatcher`。
2. `ObjectWatcher` 为对象保存弱引用。
3. 等待 5 秒后再次检查，并主动触发 GC。弱引用还没清掉时，这个对象才算 retained object。
4. LeakCanary 先累计 retained object 数量。默认阈值是应用可见时 5 个、应用不可见时 1 个；App 退到后台后按不可见阈值计算，少量 retained object 也可能触发 dump。
5. 只有达到阈值后才会 dump `.hprof`，再由 Shark 分析 GC Root、引用路径、suspect reference 和 retained size。

这套流程把 retained check 和 heap dump 分成了两步。日常接入里最容易写错的地方，就是把“对象还活着”直接写成“马上 dump”。
## leak trace 比堆大小更有用

内存泄漏排查里，堆大小只能告诉你结果，引用链才能告诉你原因。LeakCanary 输出的 leak trace 会标出：

- GC Root 类型，比如 native local、thread、system class。
- 每一段强引用路径。
- 哪些引用最可疑。
- 泄漏对象的状态，例如 destroyed Activity。
- 是否命中已知 library leak 模式。

这类信息能直接指导修复。比如一个单例静态字段持有 `View`，trace 会把单例、集合、View、Activity 之间的引用关系展开；开发者不需要在 Hprof 里手动找半天。

## Application Leak 和 Library Leak 要分开看

LeakCanary 会把泄漏分成 Application Leak 和 Library Leak。前者是应用代码导致，通常应该修。后者来自系统或第三方库已知问题，应用侧未必能直接修复。

这层分类很实用。团队看泄漏列表时，不能把所有报告都按同一优先级处理。Application Leak 应进入代码修复；Library Leak 更适合做版本规避、反射补丁、依赖升级或忽略规则。

## Release 中使用要很克制

完整 LeakCanary 能力和 retained-object 观察能力不要混在一起写。常见边界如下：

| 依赖 / 能力 | 默认内容 | 适合场景 |
|---|---|---|
| `leakcanary-android` | 自动观察 + heap dump + Shark 分析 + 本地结果展示 | Debug / QA 包里的完整本地分析 |
| `leakcanary-object-watcher-android` | 自动安装 `ObjectWatcher`，只保留 retained object 计数信号 | Release / 灰度包里只统计 retained object |
| release heap analysis | 需要额外评估 dump、分析、脱敏和上传流程 | 预发或专项诊断，不适合默认常开 |

实践中，完整 `leakcanary-android` 通常只放 debug；release 若要保留信号，只接 `leakcanary-object-watcher-android`。线上直接做 heap dump 仍然要面对三个代价：

- dump 会冻结进程一小段时间，交互体验会抖。
- Hprof 可能带出对象字段、URL、文本和用户态数据，隐私审查压力高。
- 文件体积和上传成本都不低，频繁抓取会挤压磁盘和网络预算。

生产环境内存治理更常见的搭配是：KOOM 或自研 SDK 负责线上趋势和样本，LeakCanary 负责本地复现和修复。
## 和 Perfetto、Profiler 的边界

Perfetto 可以看进程内存曲线、RSS/PSS、GC、heap profile 等信号；Android Studio Memory Profiler 可以交互式查看对象分配和引用。LeakCanary 的优势是自动化和针对性：它知道 Android Framework 的生命周期语义，也内置了很多系统泄漏模式。

拿到一个 OOM 或内存上涨问题时，可以这样分工：

- 线上平台确认问题版本、机型和页面分布。
- KOOM 或 heap dump 样本确认泄漏候选。
- LeakCanary 在本地复现路径上输出引用链。
- Profiler / MAT / Shark 辅助查看更大的对象图。

LeakCanary 是开发者修内存泄漏时最省时间的本地工具之一，但不是完整的线上内存 APM。

## 默认观察对象

LeakCanary 2.x 的自动观察对象主要覆盖 Android 生命周期对象：

- destroyed `Activity`
- destroyed `Fragment`
- destroyed fragment `View`
- cleared `ViewModel`
- detached root `View`
- destroyed `Service`（LeakCanary 2.6 起默认包含 `ServiceWatcher`）

这些对象背后依赖 Android 生命周期和 AndroidX / Lifecycle 回调，不会扫描整个堆。Activity 由 `Application.ActivityLifecycleCallbacks` 兜住；Fragment 与 fragment view 依赖 AndroidX Fragment 生命周期；ViewModel 依赖 `onCleared()`；Service 监测来自 2.6 加入的 `ServiceWatcher`，它通过灰名单反射观察 Service 生命周期。项目停留在 2.5 或更早版本时，Service 仍要手动观察。

播放器容器、地图控制器、业务 presenter、手动创建的 detached view 这些对象，通常还要开发者自己调用 `AppWatcher.objectWatcher.watch()`。代码示例保留必要调用：

```kotlin
class PlayerController {
    fun release() {
        stopPlayback()
        AppWatcher.objectWatcher.watch(
            watchedObject = this,
            description = "PlayerController should be released after playback page exits"
        )
    }
}
```

如果对象本来就应该常驻，加入 watch 只会制造噪声。LeakCanary 的前提一直是：这个对象在当前时间点应该已经可回收。
## leak trace 应该怎么读

LeakCanary 报告里的 leak trace 是从 GC Root 到泄漏对象的引用路径，和普通调用栈不同。读的时候先抓四个点：

1. 末尾对象：确认被泄漏的是 `Activity`、`Fragment view`、`Dialog` 还是业务对象。
2. suspect reference：这些引用是 LeakCanary 标红的可疑保留点。
3. GC Root：判断根来自线程、静态字段、JNI 还是系统对象。
4. retained size：如果这个对象被释放，连带能回收多少内存。它决定了规模是几十 KB 的小泄漏，还是几 MB 的大对象链。

例如，一个简化后的泄漏可能长这样：

```text
GC Root: System class
|
| static AnalyticsDispatcher.callbacks
v
ArrayList
|
| elementData[2]
v
HomeFragment$callback
|
| this$0
v
HomeFragment
|
| mView
v
RecyclerView
```

这里的 `this$0` 是编译器为匿名内部类生成的对外部类实例的隐式引用。它把 `HomeFragment$callback` 和 `HomeFragment` 连在一起，所以修复点是 `AnalyticsDispatcher.callbacks` 里保存的 callback 没有移除。

如果同一条 leak trace 还带着较大的 retained size，优先级就要往前提。一个泄漏的 `Dialog` 只占几十 KB，和一个把整页 Bitmap、Adapter、缓存对象都拖住的链，处理顺序不会一样。
## 常见泄漏模式

| 模式 | 表现 | 修复方向 |
|---|---|---|
| 静态单例持有 Context / View | Activity 销毁后仍被 static 字段引用 | 存应用上下文，避免持有 View |
| Handler / Runnable 延迟任务 | MessageQueue 中的任务持有页面对象 | 页面销毁时 `removeCallbacksAndMessages()` |
| 监听器未注销 | 全局 dispatcher、网络回调、传感器监听持有页面 | 成对注册和注销 |
| 协程 / Rx / Flow 收集未取消 | 页面销毁后 collector 还在推数据，闭包继续持有页面对象 | 绑定 lifecycle scope，退出页面时 cancel / dispose |
| 匿名内部类 / lambda 持有外部类 | `this$0` 把 callback 和 Activity / Fragment 连在一起 | 改成静态类、顶层类，或在退出时解绑 |
| Fragment view 泄漏 | `onDestroyView()` 后 adapter / binding 仍持有 View | 清空 binding、adapter、listener |
| Dialog / PopupWindow 泄漏 | 弹窗 dismiss 后仍被 Window、listener 或 manager 持有 | `dismiss()` 后清理 listener、adapter、上下文链 |
| WebView / Map / Player 容器 | native 资源或内部线程持有 Activity | 独立生命周期封装，销毁顺序明确 |

LeakCanary 的优势是直接告诉你引用路径。修复时不要只把字段置空，而要找到谁负责释放这条引用。
## Library Leak 的处理方式

Library Leak 不是“可以忽略”的同义词。它表示泄漏来自系统或第三方库的已知模式，应用不一定能直接修，但仍要评估影响：

- 如果只在老系统小比例出现，可以标记已知风险。
- 如果影响主流程或大内存页面，要考虑规避代码路径。
- 如果来自第三方 SDK，要推动升级或降级验证。
- 如果能用生命周期顺序规避，可以在业务容器里做封装。

不要把 Library Leak 批量关掉。关掉后，后续同类系统问题和业务问题混在一起时，团队会失去早期信号。

## 和线上内存样本联动

LeakCanary 更适合本地修复，但它可以和线上样本组成一条修复路径：

1. KOOM 或线上 APM 发现某页面 OOM / heap 抬升。
2. 根据页面和操作路径在 Debug 包复现。
3. LeakCanary 输出引用链。
4. 修复后用 LeakCanary 确认对象释放。
5. 灰度后看线上 OOM、PSS、heap 使用率是否下降。

这个流程比“线上拿到 OOM 后盲改缓存大小”可靠。内存问题经常同时有泄漏和缓存策略两类原因，LeakCanary 负责确认泄漏部分。

## 测试集成建议

LeakCanary 放进 UI / instrumentation 测试时，先用官方的 `leakcanary-android-instrumentation`，让测试结束后自动检查泄漏。手写 `sleep + retainedObjectCount` 只适合临时验证，因为它容易受主线程空闲、GC 时机和异步任务收尾影响。

Gradle 依赖只放在 `androidTest`：

```kotlin
dependencies {
    androidTestImplementation("com.squareup.leakcanary:leakcanary-android-instrumentation:<leakcanary_version>")
}
```

官方集成会在测试成功结束后运行检测逻辑，常见封装是 `DetectLeaksAfterTestSuccess` TestRule 或版本对应的 RunListener。CI 报告应保留 leak signature、页面路由、retained size 和构建版本，便于区分老问题复现和新泄漏。

如果项目暂时不能接官方 instrumentation 依赖，再保留最小手写门禁：进入页面、触发主路径、退出页面，再检查 retained object 是否回到 0。下面这段示意代码保留必要调用：

```kotlin
// Several unrelated imports are omitted.
@RunWith(AndroidJUnit4::class)
class PlayerLeakTest {

    @Test
    fun playerPage_should_not_leave_retained_objects() {
        ActivityScenario.launch(PlayerActivity::class.java).use { scenario ->
            scenario.moveToState(Lifecycle.State.DESTROYED)
        }

        InstrumentationRegistry.getInstrumentation().waitForIdleSync()
        Runtime.getRuntime().gc()
        SystemClock.sleep(6_000)

        assertEquals(0, AppWatcher.objectWatcher.retainedObjectCount)
    }
}
```

这类门禁要配两条补充规则：

- 只盯核心页面、核心容器和高频回归路径，不要把全量页面一次性全挂进 CI。
- 退出页面后给异步任务、主线程空闲和 GC 留缓冲窗口，否则短暂存活对象会被误判成泄漏。

已知系统泄漏或第三方库泄漏不能直接让 CI 全红。调试包可以把已知模式放进 `referenceMatchers`，在门禁里把噪声先分流：

```kotlin
class DebugExampleApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        LeakCanary.config = LeakCanary.config.copy(
            referenceMatchers = AndroidReferenceMatchers.appDefaults +
                AndroidReferenceMatchers.staticFieldLeak(
                    className = "com.example.LegacySingleton",
                    fieldName = "sContext",
                    description = "LegacySingleton keeps a destroyed activity.",
                    patternApplies = { manufacturer == "ExampleVendor" && sdkInt == 33 }
                )
        )
    }
}
```

门禁报告里至少保留 leak signature、页面路由、retained size 和构建版本。这样才能把“同一条老问题重复出现”与“新引入的泄漏”分开看。

## 参考资料

- [LeakCanary documentation](https://square.github.io/leakcanary/)
- [LeakCanary changelog](https://square.github.io/leakcanary/changelog/)
- [LeakCanary recipes](https://square.github.io/leakcanary/recipes/)
