---
title: "内存泄漏"
chapter: "10.2"
section: "10.2"
status: "finalized"
drafted_date: "2026-04-02"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-31"
last_verified_against: "AOSP android-17.0.0_r1; Profiling Mainline module android-17.0.0_r1; LeakCanary 2.14 docs"
confidence: high
reviewed_date: "2026-05-08"
reviewed_by: "openclaw-task6"
polish_count: 1
polish_date: "2026-04-08"
polish_by: "task2b-polish"
sources:
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-07_wechat_为什么各大厂自研的内存泄漏检测框架都要参考_LeakCanary_因为它是真强啊.md"
  - type: blog
    path: "性能优化日报/2026-03-15-LeakCanary-内存泄漏检测.md"
  - type: paper
    path: "Manus/android_native_memory_leak_report.md"
  - type: aosp
    path: "platform/packages/modules/Profiling/framework/java/android/os/ProfilingManager.java@android-17.0.0_r1"
  - type: official
    path: "https://square.github.io/leakcanary/fundamentals-how-leakcanary-works/"
  - type: official
    path: "https://square.github.io/leakcanary/shark/"
  - type: official
    path: "https://developer.android.com/studio/profile/capture-heap-dump"
  - type: official
    path: "https://source.android.com/docs/core/tests/debug/native-memory"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/native-heap-profiler"
  - type: official
    path: "https://developer.android.com/ndk/guides/memory-debug"
tags: ['memory-leak', 'leakcanary', 'mat', 'heapprofd', 'heap-dump', 'gc-root', 'native-memory']
related_chapters: ["4.1", "4.3", "4.5", "10.1", "10.6"]
pipeline_stage: "ready-to-publish"
task2b_result: fixed
task2b_state: "fixed"
task6_state: reviewed
task6_reviewed_date: "2026-06-20"
task6_result: "pass-light-edit"
review_log: "logs/review/2026-05-08-04-review.md"
task9_state: "reviewed"
task9_reviewed_date: "2026-06-20"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-20T17:27:45+08:00"
last_task9_audit: "2026-06-20"
task9_review_notes: "2026-06-20 17 Task9 idle-audit AUTO-FIX: 修正 source.android.com native-memory 官方文档路径；补齐 heapprofd Java allocation sampling Android 12+ 版本边界；无 queue pending，回到 Task6 复审。 | 2026-05-08 04 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 仅建议；无 queue pending，Task6 已通过，自动晋升 finalized / ready-to-publish；详见 logs/deep-review/2026-05-08-04-deep-review.md。 | 2026-05-08 03:44 Task2B rework: P0 ProfilingManager requestProfiling API 签名已修正（补 tag/CancellationSignal/Consumer<ProfilingResult>，说明 global listener 路径） | 2026-05-03 04 task9 deep-review: needs-rework。P0 0 / P1 2 / P2 0。 | 2026-05-08 00:28 Task9 deep-review: needs-rework。P0 1 / P1 1 / P2 1。 | 2026-05-08 01:40 Task2B rework: P0 ASan/HWASan 重新定位为内存安全检测器并修正版本；P1 dumpsys meminfo 改为受控复现口径；P2 ProfilingManager 补充限流和约束 | 2026-05-08 02 Task9 deep-review: needs-rework。P0 1 / P1 0 / P2 0。ProfilingManager requestProfiling API 签名错误，需 Task2B 回炉。"
task9_result: "auto-fixed"
last_task6_at: "2026-06-20T20:11:02+08:00"
last_task6_audit: "2026-06-20"
task6_review_notes: "2026-05-07 23:13 task6 revisiting-review: pass-light-edit。修复禁用词、无语言代码块、比喻化开头与少量措辞问题；Task9 历史技术项仍待复审，未自动晋升。 | 2026-05-08 02:09 task6 revisiting-review: pass-light-edit。复核 Task2B 修正后写作层，修复 7 处 L1/L2 表达与格式问题；Task9 仍为 pending，未自动晋升。 | 2026-05-08 04:05 task6 revisiting-review: pass-light-edit。复核 Task2B 修正后写作层，修复 frontmatter YAML 与流程元数据；正文无新增 L1/L2 问题；无新增回炉项，送 Task9 复审。"
last_task9_audit_result: "auto-fixed"
last_task9_audit_log: "logs/deep-review/2026-06-20-17-audit.md"
last_task9_autofix_at: "2026-06-20"
last_task9_review_log: "logs/deep-review/2026-06-20-17-audit.md"
task9_reviewed_at: "2026-06-20T17:27:45+08:00"
updated_by: "openclaw-task9"
updated_date: "2026-06-20"
task2b_verifier_notes: "2026-06-20 Task2B Verifier: status finalized→ready-for-review (Task9 auto-fix 回流，pipeline_stage=task6_pending 但 status 未同步); 2026-06-20T19:27:21+08:00"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-13
---

# 10.2 内存泄漏

> 适用范围：Android 8.0（API 26）至 Android 17（API 37）。平台行为和公开 API 以 `android-17.0.0_r1` 为源码锚点。

内存泄漏是生命周期归属错误：对象或资源已经离开业务生命周期，仍被更长寿命的持有者占用。Java/Kotlin 对象表现为从 GC Root 仍可达；Native 分配表现为所有者失去释放机会，或释放路径没有执行。

内存曲线上升、PSS 增长、GC 变频都只能提供线索。缓存扩容、延迟回收、线程栈增长、图形缓冲区和文件映射也会产生相似曲线。Java 堆泄漏需要引用路径证据，Native 泄漏需要未释放分配及其调用栈证据。

## 从“内存增长”走到“泄漏结论”

一轮可信排查包含六个动作：

1. 定义对象应当结束的生命周期，例如 `Fragment.onDestroyView()` 之后的旧 View。
2. 在受控操作中重复创建和结束该生命周期，并记录操作次数。
3. 等待主线程空闲和必要的异步清理，再观察对象是否仍被保留。
4. 获取 Java heap dump 或 Native allocation profile。
5. 找到长寿命持有者、强引用路径或未释放分配栈。
6. 修正所有权后，用同一操作和同一采集条件复测。

这套流程能区分“暂时还活着”和“生命周期已经结束却持续可达”。单次快照也可能落在消息尚未处理、动画尚未结束或缓存尚未裁剪的窗口，复现脚本和前后对照同样重要。

## Java 堆：GC Root 与强引用路径

ART 从 GC Root 出发标记可达对象。对象仍可达时，GC 会保留它，无论应用是否还会使用它。

常见根类别包括：

| 根类别 | 常见来源 | 排查时关注的边 |
| --- | --- | --- |
| 线程栈与 JNI local reference | 正在执行的方法、Native 调用帧 | 长任务、阻塞调用、未结束协程捕获了什么 |
| 活跃线程 | `Thread` 及线程局部变量 | 线程是否应当退出，`ThreadLocal` 是否清理 |
| System class / boot class | 已加载类及其静态字段 | 静态集合、单例、SDK 注册表 |
| JNI global reference | `NewGlobalRef()` | 是否存在配对的 `DeleteGlobalRef()` |
| VM internal / monitor | 运行时内部结构、锁相关对象 | 结合工具给出的根类型和引用路径判断 |

静态字段通常位于“类对象 → static field → 业务对象”这条路径上。把 static 字段直接称为独立 GC Root 会掩盖引用路径中的类对象，阅读 heap dump 时应按分析器报告的根类型为准。

WeakReference 不会阻止对象回收。监视对象在一次等待和 GC 后仍未清除，只能说明它处于 retained 状态，是泄漏候选。堆图中的强引用路径与业务生命周期共同决定它是否构成泄漏。

## LeakCanary 的检测链路

LeakCanary 默认监视已经销毁的 Activity、Fragment、Fragment View，以及已经 cleared 的 ViewModel。其处理流程可概括为：

1. `ObjectWatcher` 保存目标对象的弱引用，并记录预期结束生命周期的原因。
2. 经过可配置的 retained delay 后请求 GC，检查弱引用是否已经清除。
3. retained 对象达到配置条件时抓取 heap dump。抓取会影响进程运行，不适合与性能基准同时执行。
4. Shark 解析堆图，寻找 retained 对象到 GC Root 的强引用路径。
5. LeakCanary 按引用模式对结果分组，并区分应用代码路径和已知库路径。

对自定义生命周期对象，可以在明确的结束点加入监视。下面的代码用于验证一个已经从窗口分离的 View 能否变为弱可达：

```kotlin
AppWatcher.objectWatcher.watch(
    watchedObject = detachedView,
    description = "Checkout view detached"
)
```

这段调用只登记观察对象。它不会立即证明泄漏，也不负责释放对象；后续仍需等待检测和堆分析。

### 怎样读一条 LeakCanary 报告

阅读顺序建议固定下来：

- 确认 `╰→` 指向的对象是否已经越过业务生命周期。
- 从 GC Root 沿 `↓` 向下读强引用路径。
- 检查 `~~~` 标出的可疑引用，判断它是否应当在生命周期结束时清除。
- 看 retained size 时同时看 dominator 关系。该数值是该对象独占支配的估算量，不能单独证明泄漏。
- 查看 leak signature。多个实例共享签名时，通常来自同一种持有路径。

Shark 给出的是一条适合诊断的强引用路径。对象可能还有其他到根路径，修复后需要重新抓取和分析，不能只凭删除报告里某一条边宣告完成。

`Library Leak` 表示路径匹配已知库或 Framework 模式，不代表可以忽略。处理顺序是核对依赖版本、查阅上游修复、应用可行的规避方案，并评估 retained bytes 和发生频率。无法在应用侧消除时，也要把影响和版本范围记录下来。

## 常见的生命周期归属错误

### Activity 与 Context

进程级单例直接保存 Activity，会把整个窗口、View 树和相关资源留在堆中。修复应围绕所有权：

- 只需要资源、文件或系统服务时，在语义允许的范围内保存 `applicationContext`。
- 需要界面能力时，让调用方在当前操作中传入 Activity，不把它写入进程级字段。
- 单例注册回调时返回可关闭句柄，页面在对应生命周期结束点关闭。
- 不把 WeakReference 当作通用补丁。它会改变可用性语义，也无法修复监听器、任务或缓存的错误归属。

### Fragment View 与 ViewBinding

Fragment 实例可能进入 back stack，而它的 View 已在 `onDestroyView()` 销毁。Binding、Adapter、Animator 或回调持有旧 View，都会跨越 View 生命周期。

下面的模板让 binding 只在 `onCreateView()` 到 `onDestroyView()` 之间有效，同时断开 RecyclerView 对 Adapter 的引用：

```kotlin
private var _binding: FragmentCheckoutBinding? = null
private val binding: FragmentCheckoutBinding
    get() = requireNotNull(_binding)

override fun onDestroyView() {
    binding.items.adapter = null
    _binding = null
    super.onDestroyView()
}
```

清空 binding 只能切断 Fragment 这一侧的引用。Adapter、异步任务或外部监听器仍可能保存 View，报告中的完整引用路径不能省略。

### Handler、Runnable 与异步任务

延迟消息会在 MessageQueue 中保存 Runnable；Runnable 捕获 Activity 或 View 后，其存活时间由消息执行或取消时间决定。优先让任务拥有明确的取消点：

- 保存 Runnable 实例，并在 `onDestroy()` 或 `onDestroyView()` 调用 `removeCallbacks(runnable)`。
- 页面可见性结束就应停止的任务，在 `onStop()` 取消；需要跨短暂不可见状态保留的任务，选择更长的 owner。
- 协程收集界面数据时，将 scope 绑定到 View lifecycle。

下面的收集方式会在 View lifecycle 低于 `STARTED` 时取消内部收集，并在 View 销毁后结束父协程：

```kotlin
viewLifecycleOwner.lifecycleScope.launch {
    viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
        viewModel.uiState.collect { state ->
            render(state)
        }
    }
}
```

它解决的是收集任务与 Fragment View 生命周期的匹配。上游热流、Repository 缓存和外部 callback 仍有各自的所有者，需要分别审查。

### Listener 与注册表

注册和解注册要使用同一个 listener 实例，并选择对称的生命周期事件。不能把 `onStop()` 写成通用答案：

- 仅前台可见时需要的监听，常在 `onStart()` 注册、`onStop()` 解注册。
- View 专属监听，常在创建 View 后注册、`onDestroyView()` 解注册。
- 进程级监听由 Application 持有，不能夹带 Activity、Fragment 或 View。

回调注册 API 若返回 `Closeable`、`Disposable` 或 token，owner 应保存该句柄并按生命周期关闭。只把本地变量置为 `null`，无法移除服务端或单例注册表中的引用。

### Jetpack Compose

`LaunchedEffect(key)` 的协程会在 key 改变或离开 Composition 时取消，`rememberCoroutineScope()` 的 scope 也会随对应 Composition 节点离开而取消。风险多出现在这些对象被传给更长寿命的单例、SDK callback 或自建 scope。

需要注册外部监听器时，用 `DisposableEffect` 同时表达注册和清理。下面的示例假设 `NetworkMonitor.Listener` 是 SAM 接口：

```kotlin
@Composable
fun NetworkAwarePanel(monitor: NetworkMonitor) {
    DisposableEffect(monitor) {
        val listener = NetworkMonitor.Listener { connected ->
            // 把状态写入当前 Composition 管理的状态容器
        }
        monitor.addListener(listener)
        onDispose {
            monitor.removeListener(listener)
        }
    }
}
```

当 `monitor` 改变或该节点离开 Composition 时，旧 listener 会被移除。`remember` 可以保存与 Composition 同寿命的对象；把 Activity、View 或 scope 交给全局持有者仍会扩大生命周期。

### JNI global reference

Native 代码通过 `NewGlobalRef()` 创建的引用会让 Java 对象持续可达。每条成功创建的 global reference 都应有清楚的所有者，并在卸载、会话结束或 Native 对象析构时调用 `DeleteGlobalRef()`。跨线程暂存引用时，还要区分 local、global 和 weak global reference，不能把 local reference 保存到调用结束以后。

### 可关闭资源

Cursor、ParcelFileDescriptor、MediaCodec、Image、Surface 等资源带有显式关闭协议。它们的 Java 包装对象可能很小，背后却连接着 Native 分配、图形缓冲区或内核对象。使用 `use`、try-with-resources 或清楚的 owner 关闭资源，比等待 finalizer 或 Cleaner 更可靠。

## Heap dump：从 retained object 找到 owner

Android Studio Memory Profiler 可以抓取 Java heap dump。命令行排查 debuggable 进程时，也可以用 ActivityManager 请求快照：

```bash
adb shell am dumpheap com.example.myapp /data/local/tmp/myapp.hprof
adb pull /data/local/tmp/myapp.hprof
```

heap dump 会暂停或扰动目标进程，文件中还可能包含账号、页面文本和业务数据。采集、保存、上传和删除都应遵守调试数据的访问控制，生产设备上不能把全量堆快照当作常规遥测。

分析时可按以下顺序推进：

1. 从目标类型的实例数和 shallow size 查看是否随受控操作增长。
2. 用 dominator tree 找到 retained size 较大的支配者。
3. 对已经结束生命周期的实例执行 `Path to GC Roots`，排除 weak/soft reference 路径。
4. 定位引用边对应的 owner，回到注册、缓存、任务或 JNI 代码。
5. 修复后重复相同脚本，确认旧实例数量和路径消失。

`dumpsys meminfo <package>` 中的 Activities、Views、PSS 和 RSS 可用于筛选复现窗口。back stack、停止态组件、共享页、图形缓冲区和映射文件都会影响这些数值，因此它们不能代替 heap graph。

## Native 堆：跟踪分配与释放

Native 泄漏没有 Java GC Root 路径。排查对象变为分配调用栈、当前仍存活的 sampled allocations，以及业务操作前后的增量。

### heapprofd

Android 10 起，Perfetto 的 heapprofd 可以对 Native heap allocation 采样并记录调用栈。下面的命令从 Perfetto checkout 中采集指定进程，持续时间按复现场景调整：

```bash
tools/heap_profile android -n com.example.myapp -d 30
```

结果中的 allocated、freed 和 live allocations 应结合时间窗口与调用栈阅读。采样间隔控制统计精度，不是“低于该字节数的分配必然跳过”的阈值。运行在 user build 时，目标应用需要 `debuggable` 或 `<profileable android:shell="true"/>`；符号化还要求构建产物与设备上的 Build ID 匹配。

判断某条栈是否泄漏，可以在稳定基线后重复一次业务操作，比较 live bytes 或 allocation count 的增量，再执行资源释放或退出页面。持续保留且能映射到缺少释放路径的分配，证据强于单看累计 allocated。

### malloc debug 与 libmemunreachable

AOSP malloc debug 通过 bionic 的调试能力记录分配、释放和回溯，适合受控调试构建。它会改变时序和内存占用，启用方式还受设备 build 类型、目标进程和启动方式约束，使用时应按当前 AOSP `native-memory` 文档配置。

`libmemunreachable` 对 Native 分配执行可达性扫描，报告无法从选定根集合到达的块。扫描本身有成本，也可能漏掉“仍可达但业务已放弃”的分配；结果属于候选证据，仍要回到分配栈和所有权代码。

### HWASan、MTE 与 GWP-ASan 的边界

HWASan、MTE 和 GWP-ASan 面向越界访问、use-after-free、double free 等内存安全错误。它们能解释崩溃与堆损坏，不能取代 heapprofd 或 malloc debug 的长期未释放分析。工具选择应由问题类型决定：

| 问题 | 优先证据 |
| --- | --- |
| Java/Kotlin 对象越过生命周期 | ObjectWatcher + heap dump + GC Root 路径 |
| Native live allocations 随操作增长 | heapprofd 差分 + 符号化调用栈 |
| Native 分配无法从根集合到达 | libmemunreachable + 分配回溯 |
| 越界、释放后使用、double free | HWASan、MTE、GWP-ASan |
| Java heap 与 Native heap 都没有同步增长 | 图形、mmap、线程栈、文件页等其他分类 |

## ProfilingManager 在 Android 17 中的位置

`ProfilingManager` 自 Android 15（API 35）提供公开请求接口。在 `android-17.0.0_r1` 中，源码位于 `packages/modules/Profiling/framework/java/android/os/ProfilingManager.java`，支持 Java heap dump、heap profile、stack sampling 和 system trace。

`requestProfiling()` 的参数仍包括 profiling type、参数 Bundle、tag、CancellationSignal、Executor 和结果 listener。Android 17 源码明确说明：

- 请求受 rate limit 约束，也可能得不到执行。
- request listener 的 Executor 和 Consumer 需要成对提供；也可以预先注册全局 listener。
- 成功结果写入应用内部 files 目录，路径通过 `ProfilingResult` 回传。
- 取消信号只能请求取消，已经产生的结果仍可能回调。

这个 API 是受系统约束的采集入口，没有对象生命周期判断，也不会解析 GC Root 路径。应用仍需根据复现条件触发采集，再用堆分析器完成归因。Android 17 增加的系统触发能力属于诊断采集机制，不能据此把一次 OOM 或内存压力事件等同于泄漏。

## 开发、测试与线上策略

### 本地开发

- LeakCanary 放在 debug 或专门的 QA variant。
- 修复按 leak signature 管理，保留复现步骤、引用路径和验证结果。
- 跑性能基准时关闭自动 heap dump，避免采集暂停污染结果。

### 自动化测试

- 选取页面进出、配置变更、导航返回、进程内账号切换等生命周期密集场景。
- 每轮测试使用固定操作次数，并给异步清理留出可解释的等待条件。
- retained object count 可作为回归信号；失败用例仍需保存 heap 分析证据。
- 不用某个设备上的固定 PSS 差值当作所有机型通用阈值。

### 线上诊断

- 优先上报聚合指标、进程状态、操作序列和匿名化的 leak signature。
- heap dump 或 Native profile 只在严格采样、用户授权和访问控制下采集。
- 文件在设备端和服务端都要设置保留期限，避免把原始内存内容写入普通日志。
- `ProfilingManager`、厂商诊断框架或自建采集只能提供现场，生命周期和引用路径仍由分析阶段判断。

## Android 版本边界

- Android 8.0 至 Android 17 的 Java 泄漏定义没有变化：从根集合仍可达的对象不会被 GC 回收。
- Android 10 引入 heapprofd，为 Native allocation sampling 提供平台工具链。
- Android 12 起，Perfetto 可通过 ART heap 配置采样 Java allocations；它提供分配热点，不能替代完整 heap dump 的对象关系图。
- Android 15（API 35）公开 `ProfilingManager`。
- Android 17（API 37）的 Profiling Mainline 模块扩展了系统触发诊断能力；请求限流、结果回调和应用私有文件路径等约束仍需遵守。

GC 收集器的代际策略或并发实现可能改变回收暂停和检测时序，却不会修复仍存在的强引用路径。LeakCanary 的 retained delay 也不应根据未经测量的收集器推断随意缩短。

## 排查清单

- 对象或资源应在哪个生命周期事件结束？
- 哪个 owner 的寿命更长？
- retained 状态是否经过可解释的等待与复现？
- Java 对象是否有 heap dump 中的强引用路径？
- Native 增量是否能映射到符号化分配栈？
- listener、task、adapter、binding、JNI ref 和资源句柄是否成对清理？
- 修复后是否用同一脚本和同一采集条件复测？
- 诊断文件是否包含敏感数据，访问权限和保留期限是否合规？

## 与其他章节的关系

- [§4.1 Android 内存模型全景](../../part1-fundamentals/ch04-memory/01-memory-overview.md)：区分 Java heap、Native heap、graphics、mmap 和 kernel 统计。
- [§4.3 ART 虚拟机内存管理](../../part1-fundamentals/ch04-memory/03-art-memory.md)：理解可达性、引用处理和 GC。
- [§4.5 App 内存优化](../../part1-fundamentals/ch04-memory/05-app-memory-optimization.md)：把泄漏修复放回进程内存预算。
- [§10.1 App 内存分析](01-app-memory-analysis.md)：建立 PSS、RSS、heap dump、Perfetto 和退出信息的诊断入口。
- [§10.6 内存抖动与频繁 GC](06-memory-churn.md)：区分持续保留与高频短命分配。

## 参考资料

- [AOSP `ProfilingManager.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/packages/modules/Profiling/+/android-17.0.0_r1/framework/java/android/os/ProfilingManager.java)
- [LeakCanary：How LeakCanary works](https://square.github.io/leakcanary/fundamentals-how-leakcanary-works/)
- [LeakCanary：Fixing a memory leak](https://square.github.io/leakcanary/fundamentals-fixing-a-memory-leak/)
- [Shark heap analysis library](https://square.github.io/leakcanary/shark/)
- [Android Studio：Capture a heap dump](https://developer.android.com/studio/profile/capture-heap-dump)
- [Perfetto：Native heap profiler](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [AOSP：Diagnose native memory usage](https://source.android.com/docs/core/tests/debug/native-memory)
- [Android NDK：Memory error debugging and mitigation](https://developer.android.com/ndk/guides/memory-debug)
