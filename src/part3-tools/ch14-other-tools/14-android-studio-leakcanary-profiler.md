---

title: Android Studio LeakCanary Profiler 与堆转储分析
chapter: 14.14
section: 14.14
status: ready-for-review
drafted_date: 2026-05-17
drafted_by: openclaw-task2a
applicable_versions: Android Studio Panda 3+ / Android 8.0 (API 26) - Android 17 (API 37)
last_verified: 2026-07-30
last_verified_against: Android Studio Quail 2 / Android Developers heap dump docs / android-17.0.0_r1 / LeakCanary 2.14 docs and upstream source
confidence: medium
sources: 
  - type: official
    path: "https://developer.android.com/studio/preview/features"
  - type: official
    path: "https://developer.android.com/studio/profile/capture-heap-dump"
  - type: official
    path: "https://developer.android.com/blog/posts/prioritizing-memory-efficiency-essential-steps-for-android-17"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-all"
  - type: official
    path: "https://square.github.io/leakcanary/fundamentals-how-leakcanary-works/"
  - type: official
    path: "https://square.github.io/leakcanary/fundamentals-fixing-a-memory-leak/"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/native-heap-profiler"
  - type: obsidian
    path: "intake/daily-info/2026-05-17.md"
  - type: obsidian
    path: "DeepResearch/android-skills-profilers/2026-05-16-android-skills-profilers-深度调研.md"
  - type: obsidian
    path: "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-03-app_exit_info_tracker_and_koom_fork_hprof.md"
tags: [android-studio, profiler, leakcanary, memory, hprof, heap-dump]
related_chapters: ["10.2", "14.1", "14.3", "19.5", "23.1"]
created_by: task2a-knowledge-gap
created_date: 2026-05-17
gap_source: 官方文档/每日信息/素材驱动
---

# 14.14 Android Studio LeakCanary Profiler 与堆转储分析

Android Studio 的 LeakCanary Profiler task、LeakCanary 库和 Memory Profiler 都能分析 HPROF，但三者的触发时机与职责不同。版本口径为 Android Studio Quail 2、LeakCanary 2.14 和 `android-17.0.0_r1`：LeakCanary 在应用进程内观察生命周期对象；IDE task 把堆分析移到开发机；Memory Profiler 提供通用堆浏览；Android 17 的系统触发机制负责捕获 OOM 或系统判定的异常现场。

这里讨论 Java / Kotlin 托管堆。C/C++ 分配、图形缓冲区和 `mmap` 区域需要 heapprofd、malloc debug、Perfetto、`showmap` 等工具补证。若只依据 HPROF 判断进程总内存，容易把不同内存域混在一起。

## Panda 3 引入的 LeakCanary Profiler task

Android Studio Panda 3 引入专用 LeakCanary Profiler task。设备仍负责运行应用和生成堆现场，Shark 转到开发机分析；报告可从可疑引用跳到工程源码。到 2026-07-30，Android Studio 稳定版已经进入 Quail 2，这项能力仍属于 IDE 功能，与 Android 平台 API 无绑定关系。

四类入口的分工如下。

| 入口 | 触发位置 | 适合的阶段 | 能回答的问题 | 主要边界 |
|---|---|---|---|---|
| LeakCanary 2.14 | 应用进程内自动观察 | 日常开发、手工走查 | 已销毁的生命周期对象为何仍被强引用 | 堆转储会短暂停顿应用；默认观察范围有限 |
| Android Studio LeakCanary task | 设备采集，开发机分析 | 本地稳定复现后的源码定位 | LeakCanary 报告中的可疑引用对应哪段工程代码 | 依赖支持该 task 的 IDE、可分析的构建和可复现场景 |
| Memory Profiler heap dump | IDE 控制采集和浏览 | 对象数量、支配关系、通用 HPROF 检查 | 某类有多少实例，谁在持有它，释放后可回收多少内存 | 需要开发者判断对象是否越过合法生命周期 |
| 线上采样或系统触发 | 应用 SDK 或 Android 系统 | 难以本地复现、内存限制、长时间运行 | 故障发生时进程处于什么内存状态 | 受限流、隐私、文件体积、设备空间和服务端成本约束 |

Panda 3 的 task 没有改变 LeakCanary 的对象观察语义，也没有扩展 HPROF 对 Native 内存的覆盖范围。它改进的是分析位置和源码导航。即使工程没有使用这个 task，仍可用 LeakCanary 自带界面或导出的 HPROF 完成分析。

## LeakCanary 如何从生命周期走到 HPROF

LeakCanary 2.14 的 `leakcanary-android` 依赖通过 `MainProcessAppWatcherInstaller` 这个 `ContentProvider` 在主进程安装 `AppWatcher`。默认观察 Activity、Fragment、Fragment View、ViewModel 和 Service；普通单进程应用无需自行编写初始化代码。需要多进程覆盖、定制观察时机或修改配置时，再评估 `AppWatcher.manualInstall()`。

检测过程分为四段。

1. 生命周期回调指出某个对象已经离开预期使用期。例如 Activity 执行 `onDestroy()`，Fragment View 执行 `onDestroyView()`，ViewModel 执行 `onCleared()`。
2. `ObjectWatcher` 为该对象创建带队列的弱引用。默认 `retainedDelayMillis` 为 5 秒；延迟到期后，弱引用仍未入队，对象就被计为 retained。
3. 应用可见时，默认累计 5 个 retained object 才触发堆转储；应用不可见时阈值降为 1，并在保留延迟后转储。开发者也可点击通知主动触发。
4. Shark 读取 HPROF，寻找从 GC root 到 retained object 的强引用路径，生成 leak trace 和 leak signature，并区分 Application Leak 与 Library Leak。

“retained”说明对象在观察窗口结束时仍可达；它还不足以单独证明业务泄漏。配置变更、正在执行的异步任务、框架缓存和调试器都可能延长对象寿命。判断要结合生命周期、重复复现和引用路径。

## 阅读 leak trace

Leak trace 从 GC root 开始，经持有者和字段到达被观察对象。报告中的 `Leaking: YES` 表示对象已知应被释放，`NO` 表示对象仍处于合法生命周期，`UNKNOWN` 表示 Shark 无法仅凭已知规则判定。下划线标出的引用是分析器给出的可疑持有边，修复前仍要回到源码确认。

下面的虚构报告只用于说明阅读顺序。

```text
┬───
│ GC Root: System class
├─ com.example.AppRegistry instance
│    ↓ AppRegistry.callbacks
├─ java.util.ArrayList instance
│    ↓ ArrayList.elementData
├─ java.lang.Object[] array
│    ↓ Object[0]
├─ com.example.DetailPresenter instance
│    ↓ DetailPresenter.view
╰→ com.example.DetailActivity instance
```

这条路径指向 `AppRegistry.callbacks`：长生命周期 registry 保存 presenter，presenter 又保存已销毁的 Activity。排查应确认 callback 的注册点、注销点和异常退出路径，而非只改 `DetailActivity`。用弱引用绕过注销往往会掩盖生命周期错误，也可能让依赖对象提前消失。

Leak signature 根据可疑引用路径归并同类泄漏，适合跨设备或多轮回归去重。Application Leak 指向应用可以修复的持有关系；Library Leak 对应 LeakCanary 已知的第三方库或 Android 框架问题。Library Leak 也应核对系统版本、库版本和复现条件，不能看到分类后就忽略。

## Memory Profiler 中的字段与堆类型

Android Studio 的 heap dump 是某一时刻的托管堆快照。类列表和实例列表的字段含义不同，阅读时要先确认当前视图。

| 字段 | 含义 | 使用方式 |
|---|---|---|
| `Allocations` | 当前 HPROF 中该类的实例数 | 对比固定操作前后的数量，寻找不能回落的类 |
| `Shallow Size` | 对象自身在托管堆中的大小 | 衡量对象本体，不代表删除该对象可释放的总量 |
| `Retained Size` | 基于支配树估算；对象回收后可连带释放的大小 | 找占用大且生命周期异常的支配者 |
| `Native Size` | 与 Java 对象关联、分析器能够归属的 Native 大小 | 辅助观察 Bitmap 等对象；Android 7.0 以下不可用 |
| `Depth` | 从任一 GC root 到实例的最短引用跳数 | 帮助寻找靠近长生命周期根的对象；跳数小本身不等于泄漏 |

Profiler 还会区分 `App`、`Image` 和 `Zygote` heap。业务对象通常位于 App heap；Image heap 存放启动映像相关对象；Zygote heap 来自进程 fork 时继承的对象。跨 heap 引用是正常现象，不应把系统 heap 中长期存活的对象直接列为应用泄漏。

`Show activity/fragment leaks` 能缩小候选范围，但筛选结果仍是线索。Fragment back stack、框架缓存、配置变更窗口和调试状态都会影响可达性。Compose 页面也不能只搜索 Activity 或 Fragment；应结合 `ViewModel`、`Composition`、`Recomposer`、保存的 lambda 和 Android View 互操作对象检查持有路径。

`Native Size` 只覆盖分析器能与 Java 对象关联的部分 Native 内存。JNI global reference 会以 GC root 形式出现在 Java 对象图中，但 HPROF 不记录任意 C/C++ `malloc` 块、dma-buf、GPU 驱动分配或完整图形缓冲区生命周期。

## 采集、导出与导入

### Android Studio 采集

Profiler 要连接可分析的目标进程。为了获得完整的对象和字段数据，本地排查通常使用 debuggable 构建；profileable release 构建能够开放受限的分析能力，但结果完整度和可用操作受系统版本与配置影响。Android Studio 当前的通用 Profiler 指南建议 API 29 及以上的 Google Play 设备和 AGP 7.3 及以上，旧设备或旧插件工程应单独验证。

堆转储会暂停应用并消耗额外内存。采集前先固定操作步骤、等待条件和构建版本；不要在内存已经逼近进程上限时连续抓取多个 HPROF。

### `am dumpheap`

Android 17 的 `ActivityManagerShellCommand` 支持以下语法：

```text
dumpheap [--user <USER_ID> current] [-n] [-g] [-b <format>] <PROCESS> <FILE>
```

`<PROCESS>` 可写包进程名或 PID，`-g` 请求转储前执行 GC，`-n` 切换为 Native heap。这里的 Native dump 与 Java HPROF 格式及分析路径不同。

下面的命令在受控测试设备上抓取主进程 Java HPROF。

```bash
adb shell am dumpheap -g --user current com.example.app /data/local/tmp/example-after-exit.hprof
adb pull /data/local/tmp/example-after-exit.hprof ./artifacts/example-after-exit.hprof
adb shell rm /data/local/tmp/example-after-exit.hprof
```

包名避免了 shell 中把 `<pid>` 解释成输入重定向的风险。命令能否成功取决于构建可调试性、调用身份、设备策略和目标进程状态。`-g` 只请求一次 GC；一张 GC 后快照仍不能证明对象永久泄漏。

应用代码也可在授权的调试入口调用 `Debug.dumpHprofData(path)`。该调用会阻塞并生成包含完整对象内容的文件，应放在测试工具或明确受控的诊断流程中，避免主线程长时间停顿。

Android Studio 可以直接导入 HPROF。若其他工具生成的是 Android 特有格式而桌面分析器无法读取，可用 SDK Platform Tools 中的 `hprof-conv` 转换；转换前保留原始文件和工具版本，便于复核。

HPROF 可能包含用户输入、令牌、URL、文件路径、业务字段和对象缓存。原始文件应按敏感诊断数据管理：限制采集对象、加密存储、控制访问、设定过期时间，并在上传前取得合适授权。分享报告时优先分享裁剪后的引用路径和签名，不默认共享原始堆。

## Java、Native 与图形内存的工具边界

先用 `dumpsys meminfo <package>` 或同一轮 Perfetto 记录判断增长来自 Java Heap、Native Heap、Graphics、Code、Stack 还是其他映射，再选择证据工具。

| 现象 | 优先证据 | 可回答的问题 | HPROF 的限制 |
|---|---|---|---|
| Activity、Fragment、ViewModel 退出后仍存活 | LeakCanary、Java HPROF | 哪个 GC root 和字段维持强可达 | 不能依据单次 PSS 涨幅判定 |
| Java Heap 多轮操作后阶梯上涨 | 前后 HPROF、实例数、支配树 | 哪类对象累积，哪位持有者保留最多对象 | 快照不记录完整分配时间线 |
| Native Heap 持续上涨 | heapprofd、malloc debug、libmemunreachable | 哪条 Native 调用栈仍有存活分配，`malloc/free` 是否配对 | Java 对象图不含任意 `malloc` 块 |
| Graphics 或 dma-buf 上涨 | Perfetto、SurfaceFlinger、BufferQueue、`dumpsys meminfo` | Surface、GraphicBuffer、视频与相机缓冲区何时创建和释放 | `Native Size` 不能代表完整图形占用 |
| 系统因内存限制结束进程 | `ApplicationExitInfo`、系统触发 profiling | 退出原因、限制描述、系统捕获的故障现场 | 单个泄漏链不能解释全部进程内存 |

heapprofd 对 Native `malloc` 分配进行采样，记录调用栈和存活分配；它与 HPROF 的 GC root 引用链回答不同问题。§14.3 继续介绍 heapprofd、malloc debug、`showmap` 与 libmeminfo。

## Android 17 的系统内存现场

Android 17 为应用内存限制和触发式 profiling 增加了可观测信号，但这些信号不等同于 LeakCanary 的生命周期检测。

当系统内存限制机制结束进程时，`ApplicationExitInfo.getReason()` 可能仍返回 `REASON_OTHER`，描述中包含 `MemoryLimiter:AnonSwap`。分析代码应同时记录 reason、description、importance、PSS/RSS 和时间戳，且不能把任意 `REASON_OTHER` 都归为内存限制。

`ProfilingTrigger` 在 API 37 定义了两类相关触发器：

- `TRIGGER_TYPE_OOM`（值 7）面向应用抛出的 `OutOfMemoryError`。应用若安装自定义未捕获异常处理器，必须继续调用默认处理器，系统才能完成这条触发路径。结果会在应用下次启动并注册 listener 后交付。
- `TRIGGER_TYPE_ANOMALY`（值 8）由系统异常检测触发，产物类型取决于异常。内存过量或即将执行内存限制时，系统可能交付 heap dump；共享 UID 等条件可能让本轮没有产物。

这两类触发器受系统限流和设备条件约束，适合补充线上故障现场。它们不会自动告诉开发者哪个 Activity 越过生命周期，也不保证每次异常都得到 HPROF。

## 开发、CI 与线上接入

### 开发构建

下面的依赖只进入 debug 变体，用于日常自动观察。

```kotlin
dependencies {
    debugImplementation("com.squareup.leakcanary:leakcanary-android:2.14")
}
```

LeakCanary 2.x 会自动安装主进程 watcher。加入依赖后应运行一个已知泄漏样例，确认通知、堆转储、Shark 分析和 Android Studio task 均能工作；多进程应用还要分别检查每个目标进程的安装策略。

### UI 测试与 CI

LeakCanary 2.14 提供 instrumentation 集成。下面的依赖和规则只在测试成功后执行泄漏断言。

```kotlin
dependencies {
    androidTestImplementation(
        "com.squareup.leakcanary:leakcanary-android-instrumentation:2.14"
    )
}
```

这项依赖只加入 instrumentation 测试 APK。测试类还要注册检测规则：

```kotlin
@get:Rule
val detectLeaksAfterTestSuccess = DetectLeaksAfterTestSuccess()
```

该规则适合生命周期明确、可重复运行的端到端场景。也可在指定检查点调用 `LeakAssertions.assertNoLeaks()`。测试应固定页面操作、空闲等待和后台任务清理，否则异步任务尚未结束时容易出现不稳定结果。

### 线上构建

LeakCanary 提供实验性的 `leakcanary-android-release:2.14`，可在 release 构建中观察并分析泄漏。官方将这条路径标为 experimental，因此不能沿用 debug 环境的全量策略。

线上方案至少要具备远程开关、低采样率、磁盘配额、充电/空闲/网络条件、失败恢复、访问控制和数据过期策略。默认上传原始 HPROF 风险很高；更稳妥的产物是经过本地分析的 leak signature、裁剪引用路径和不含业务值的统计字段。Android 17 的 OOM/anomaly trigger 可作为系统侧补充来源，仍要遵守系统限流。

## 一轮可复查的排查流程

### 1. 固定复现场景

记录设备型号、Android 版本、ABI、应用版本、构建类型、账号条件和操作次数。页面进入、执行目标动作、退出、等待主线程空闲和后台任务结束都要写成确定步骤。随机观察一次内存曲线无法区分缓存、延迟回收和泄漏。

### 2. 确认内存域

同时查看 `dumpsys meminfo` 和 Java 对象现象。Java Heap 与目标类实例数同步上涨时进入 HPROF；Native Heap 或 Graphics 独立上涨时切换到对应工具，避免在错误的数据源上反复采样。

### 3. 捕获基线与问题快照

在相同构建和相同稳定点抓取操作前、重复操作后两份 HPROF。若应用接近内存限制，只抓故障点一份，并记录 dump 本身可能造成的额外峰值。

### 4. 定位持有边

从 LeakCanary 的 retained object 或 Profiler 中增长的类开始，沿 GC root path 查找第一个生命周期不匹配的字段。同步核对该字段的写入点、清理点、异常退出和配置变更分支。

### 5. 做最小生命周期修复

常见修复包括在 `onDestroyView()` 断开 Fragment View binding、adapter 和 listener；在合适的可见性边界注销 callback；取消越过页面生命周期的 coroutine、Rx subscription 或 delayed message；让单例保存业务 ID 或 Application context，避免保存 Activity 与 View。WebView、播放器、相机和大图缓存还要单独释放 Native/图形资源。

### 6. 用同一脚本复验

修复后重复相同次数，比较目标类实例数、retained size、GC root path、LeakCanary signature 和总体内存分区。LeakCanary 未再次报警只能算一项证据；页面恢复、配置变更和 back stack 行为也应通过回归测试。

## Android Studio Panda 的版本边界

专用 LeakCanary Profiler task 从 Panda 3 开始提供，后续 Quail 稳定版继续可用。Panda/Quail 是 IDE 发布线，API 37 是 Android 平台版本，两条版本线应分别记录。App 的 `minSdk` 不决定 IDE task 是否存在；目标进程能否连接、构建是否提供足够调试信息、设备 API、AGP 和 IDE 兼容性会影响分析结果。

遇到 task 无结果时，按以下顺序检查：IDE 是否包含该功能；LeakCanary 2.14 是否已在当前变体安装；当前进程是否为目标进程；是否产生 HPROF；该文件能否被 Memory Profiler 单独打开；工程源码与被测 APK 是否来自同一提交。

## 标准泄漏样例库

团队可维护少量、确定性的泄漏样例，用于验证接入和训练阅读引用路径。

| 样例 | 触发方式 | 预期证据 | 修复方向 |
|---|---|---|---|
| 单例保存 Activity | registry 列表加入 Activity 或 View，退出时不移除 | `Singleton.list` 指向已销毁 Activity | 保存业务 ID 或 Application context，并成对移除 callback |
| Fragment View binding | `onDestroyView()` 后仍保存 binding | Fragment 或 adapter 指向旧 View tree | 在 view 生命周期结束时断开 binding、adapter、listener |
| 延迟消息 | 页面退出前提交长延迟 Runnable | MessageQueue 或 Runnable 指向页面对象 | 在相同生命周期边界移除消息，或使用生命周期作用域 |
| 协程 continuation | 全局 scope 捕获 Activity 或 View | Job/continuation 路径到已销毁对象 | 绑定 `lifecycleScope`/`viewLifecycleOwner` 并正确取消 |
| Listener 未注销 | 注册到系统服务或全局事件源 | 长生命周期 registry 指向 callback | 注册与注销成对，覆盖异常退出 |
| WebView 或播放器 | 页面销毁后仍保存容器与回调 | Java 引用未释放，Graphics/Native 也可能上涨 | 分别清理 Java 持有关系与底层资源 |

样例的验收条件应包括触发次数、等待条件、预期 signature 和修复后的实例上限。若样例依赖 GC 时机或网络回调，应改造成可控制的测试替身。

## Native 内存诊断联动

HPROF 没有异常持有路径而 Native Heap 持续增加时，用 heapprofd 对存活分配做采样；要验证每次分配与释放时，使用调试构建上的 malloc debug；要寻找不可达 Native 分配，可结合 libmemunreachable。Graphics 增长则检查 Surface、BufferQueue、GraphicBuffer、WebView、视频和相机管线，关联 Perfetto 时间线与 SurfaceFlinger 信息。

JNI 是两条证据链的交叉处。HPROF 能显示 JNI global reference 对 Java 对象的保留；Native 分配器工具负责显示 C/C++ 内存块及调用栈。看到 JNI root 时，应同时审查 `NewGlobalRef/DeleteGlobalRef` 配对和对应 Native 对象的释放路径。

## 与其他章节的关系

- §10.2 介绍内存泄漏的定义与生命周期模型；这里聚焦 LeakCanary、Android Studio 和 HPROF 的操作证据。
- §14.3 介绍 MAT、heapprofd、malloc debug、`showmap` 与系统内存工具；Native 或图形内存问题转到该节。
- §19.5 与 §26.2 讨论线上 APM、故障采集和退出原因；这里给出原始堆的隐私边界与 Android 17 触发机制。
- §23.1 承载 Activity、Fragment、WebView、Bitmap、协程和 listener 的应用内存案例。

## 参考资料

- [Android Studio: Capture a heap dump](https://developer.android.com/studio/profile/capture-heap-dump)
- [Android Studio Profiler overview](https://developer.android.com/studio/profile)
- [Android Studio release updates](https://developer.android.com/studio/preview/features)
- [Android 17 memory efficiency guidance](https://developer.android.com/blog/posts/prioritizing-memory-efficiency-essential-steps-for-android-17)
- [Android 17 behavior changes: app memory limits](https://developer.android.com/about/versions/17/behavior-changes-all)
- [LeakCanary 2.14: Getting started](https://square.github.io/leakcanary/getting_started/)
- [LeakCanary: How it works](https://square.github.io/leakcanary/fundamentals-how-leakcanary-works/)
- [LeakCanary: Fixing a memory leak](https://square.github.io/leakcanary/fundamentals-fixing-a-memory-leak/)
- [LeakCanary: UI tests](https://square.github.io/leakcanary/ui-tests/)
- [LeakCanary for release builds](https://square.github.io/leakcanary/leakcanary-for-releases/)
- [Perfetto: Native heap profiler](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [AOSP `ActivityManagerShellCommand.java`, `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerShellCommand.java)
- [AOSP `ApplicationExitInfo.java`, `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java)
- [AOSP `ProfilingTrigger.java`, `android-17.0.0_r1`](https://android.googlesource.com/platform/packages/modules/Profiling/+/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java)
