---

title: Android Studio LeakCanary Profiler 与堆转储分析
chapter: 14.14
section: 14.14
status: ready-for-review
drafted_date: 2026-05-17
drafted_by: openclaw-task2a
applicable_versions: Android Studio Panda 4+ / Android 8.0 (API 26) - Android 17 (API 37)
last_verified: 2026-05-17
last_verified_against: Android Studio Panda preview/stable docs, Android Developers heap dump docs, Android 17 behavior changes, LeakCanary docs
confidence: medium
sources: 
  - type: official
    path: "https://developer.android.com/studio/preview/features"
  - type: official
    path: "https://developer.android.com/studio/profile/capture-heap-dump"
  - type: official
    path: "https://developer.android.com/blog/posts/the-fourth-beta-of-android-17"
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
-

# 14.14 Android Studio LeakCanary Profiler 与堆转储分析

<!-- outline-start -->
## 要点

### 🔹 LeakCanary Profiler task 的定位
说明 Android Studio Panda 将 LeakCanary 分析接入 Profiler 后，工具链从「App 内通知 + 设备端分析」变成「IDE 内任务 + 源码上下文」的使用方式。

### 🔹 HPROF 采集、导出与对象保留路径
梳理 Memory Profiler 捕获 heap dump 的入口、Activity / Fragment leak 过滤、GC root 距离、retained object 链路等分析字段。

### 🔹 设备端与开发机端分析边界
区分 LeakCanary 运行时检测、Android Studio 离线分析、生产环境 APM 上报三类场景，说明各自适合解决的问题。

### 🔹 Java / Kotlin 堆泄漏与 Native 内存问题的分工
明确 HPROF 主要覆盖托管堆对象，Native allocation、malloc debug、heapprofd、Perfetto 需要走另一套证据链。

### 🔹 与现有 LeakCanary 接入方案的取舍
对比库内置 UI、CI 复现、IDE Profiler task、线上监控 SDK，给出开发期和回归期的选择建议。

### 🔹 实战排查流程
按「复现 → 抓取 heap dump → 定位 retained path → 回到源码 → 修复 → 再抓取验证」组织最小验证流程。

## 扩展

### 🔸 Android Studio Panda 版本边界
跟踪 Panda 稳定版、预览版功能差异，以及 LeakCanary task 对 AGP、JDK、设备 API 的最低要求。

### 🔸 标准泄漏样例库
整理 Activity、Fragment、匿名内部类、协程、监听器、WebView、Bitmap cache 等常见泄漏复现场景。

### 🔸 Native 内存诊断联动
补充 heapprofd、malloc debug、native allocation tab 与 Perfetto 的联动路径。

<!-- outline-end -->

Android Studio Panda 把 LeakCanary 分析放进 Profiler 后，内存泄漏排查多了一个新的工作台。原来的 LeakCanary 更像运行在 App 内的自动哨兵：对象销毁后继续观察，达到阈值后在设备上 dump hprof，再用 Shark 分析引用链。Panda 的 Profiler task 保留 LeakCanary 的泄漏语义，把重分析和源码跳转放到开发机与 IDE 中完成。

这节不重复 §10.2 的泄漏定义，也不替代 §14.3 的内存工具清单。这里解决一个更窄的问题：已经拿到疑似泄漏对象后，怎样在 Android Studio、LeakCanary 和堆转储之间建立可复查证据链。

## Panda 中 LeakCanary Profiler task 的定位

[已验证: 官方文档, https://developer.android.com/studio/preview/features]
[已验证: 官方博客, https://developer.android.com/blog/posts/the-fourth-beta-of-android-17]

Android Studio Panda 的新能力是把 LeakCanary 接到 Android Studio Profiler 中，作为一个专门的泄漏分析 task。官方描述里有两个变化值得单独看：分析阶段从设备转移到开发机，结果在 IDE 里带源码上下文。

这会改变排查路径。

| 方案 | 运行位置 | 适合场景 | 主要收益 | 边界 |
|---|---|---|---|---|
| LeakCanary App 内 UI | 设备端检测、设备端展示 | 日常开发、走查页面、测试机复现 | 自动发现 Activity、Fragment、Fragment View、ViewModel 等生命周期泄漏 | 设备上做 heap 分析会占用 CPU 和内存；大 hprof 分析时间更长 |
| Android Studio LeakCanary task | 设备端产出现场，开发机侧分析与展示 | 本地复现后做源码级定位 | IDE 内跳到源码、复制完整分析、和 Profiler 视图结合 | 依赖 Android Studio Panda 功能；仍要先复现并拿到可用 heap 现场 |
| Memory Profiler 手动 heap dump | Android Studio 控制采集和浏览 | 不确定是否由 LeakCanary 发现，或要手动看对象数量 | 能看 class、instance、retained size、GC root 距离 | 需要人工判断泄漏对象，Activity / Fragment 过滤存在误报 |
| 线上 APM / Koom / ProfilingManager | 线上采样或系统触发 | 难以本地复现、内存上限命中、长时间运行后泄漏 | 能收集真实用户现场 | 要处理采样、隐私、上传体积、限流和服务端分析成本 |

Panda 的 task 不等同于“系统原生替代 LeakCanary”。它更像把 LeakCanary 发现的问题接到 IDE 里，让开发者少在通知、hprof 文件、源码之间来回切换。LeakCanary 负责定义什么对象已经 retained；Android Studio 负责把分析结果和工程源码放在同一个界面里。[已验证: LeakCanary 文档, https://square.github.io/leakcanary/fundamentals-how-leakcanary-works/]

## LeakCanary 到 hprof 的证据链

LeakCanary 的判断从生命周期开始，而不是从内存大小开始。它会监听 Activity、Fragment、Fragment View、ViewModel 等对象的销毁或清理时机，把这些对象交给 `ObjectWatcher`。`ObjectWatcher` 持有弱引用，等待默认 5 秒并触发 GC；如果弱引用没有被清除，这个对象就进入 retained 集合。Retained 对象数量达到阈值后，LeakCanary dump Java heap，再用 Shark 解析 hprof 并计算 leak trace。[已验证: LeakCanary 文档, https://square.github.io/leakcanary/fundamentals-how-leakcanary-works/]

这个流程里有三个判断点。

- **对象何时“应该死亡”**：Activity 收到 `onDestroy()`、Fragment View 进入 `onDestroyView()`、ViewModel 收到 `onCleared()`。这个判断来自 Android 生命周期，不来自内存曲线。
- **对象是否仍可达**：弱引用未入队，说明对象仍有强引用路径。这里只能判断 retained，不能直接说明是哪一行代码导致。
- **哪条引用路径阻止回收**：hprof 中从 GC root 到 retained object 的强引用路径，LeakCanary 称为 leak trace。LeakCanary 会根据对象生命周期标注 `Leaking: YES/NO/UNKNOWN`，再用下划线标出怀疑引用。

Leak trace 的阅读顺序是从上往下。顶部是 GC root，例如线程栈局部变量、活动线程、系统类或 Native 引用；中间是对象和字段；底部是 retained object。修复点通常不在底部对象本身，而在中间某个“生命周期更长的持有者”上，例如单例列表、未解注册 listener、延迟消息、协程闭包或缓存容器。[已验证: LeakCanary 文档, https://square.github.io/leakcanary/fundamentals-fixing-a-memory-leak/]

下面这段示意只展示 leak trace 的读法，不能当成完整代码样例：

```text
┬───
│ GC Root: System class
├─ com.example.AppSingleton instance
│    ↓ AppSingleton.callbacks
├─ java.util.ArrayList instance
│    ↓ ArrayList.elementData
├─ java.lang.Object[] array
│    ↓ Object[0]
├─ com.example.DetailPresenter instance
│    ↓ DetailPresenter.view
╰→ com.example.DetailActivity instance
```

这里的排查方向不是“DetailActivity 为什么存在”，而是 `AppSingleton.callbacks` 为什么还保存 `DetailPresenter`，以及这个 presenter 为什么仍持有已经销毁的 Activity。

## Memory Profiler 里的 heap dump 字段怎么读

[已验证: 官方文档, https://developer.android.com/studio/profile/capture-heap-dump]

Android Studio 的 heap dump 页面给的是某一时刻 Java heap 快照。抓取 heap dump 时，dump 动作发生在 App 进程内，会带来短时间额外内存占用；如果要精确控制采集点，也可以在代码里调用 `Debug.dumpHprofData()`。

打开 heap dump 后，先看这几类字段：

| 字段 | 含义 | 排查用法 |
|---|---|---|
| `Allocations` | 该 class 在 heap 中的实例数量 | 重复进出页面后数量是否单调上升 |
| `Shallow Size` | 对象自身占用的 Java heap 大小 | 判断对象本体成本，通常不代表释放收益 |
| `Retained Size` | 该对象被回收后可连带释放的内存 | 优先找 retained size 大且生命周期异常的持有者 |
| `Native Size` | 与 Java 对象关联的 Native 内存，Android 7.0+ 可见 | Bitmap 等 framework 对象可能在这里体现一部分 Native 成本 |
| `Depth` | 从任一 GC root 到该实例的最短跳数 | 深度小不一定有问题，但适合快速定位长生命周期持有者 |

Heap 过滤也会影响判断。

- **App heap**：应用主要分配区，排查业务泄漏时先看这里。
- **Image heap**：系统启动预加载类所在区域，里面的对象通常不会移动或消失。
- **Zygote heap**：进程从 Zygote fork 继承的 copy-on-write heap，排查业务泄漏时通常只作为背景信息。

Android Studio 提供 `Show activity/fragment leaks` 过滤器，用于显示可能导致 Activity 或 Fragment 泄漏的类。它能节省很多浏览时间，但不能直接当成结论。官方文档也列出误报场景：Fragment 刚创建但还没使用，或 Fragment 被缓存但不属于 FragmentTransaction。这类情况下，过滤器会看到“仍被引用”，但对象生命周期可能仍合法。[已验证: 官方文档, https://developer.android.com/studio/profile/capture-heap-dump]

手动分析时可以按这个顺序推进：先按 class 搜目标 Activity / Fragment / ViewModel，再看实例列表中的 retained size 和 depth，然后在 Instance Details 里沿 Fields / References 找持有者。找到持有者后回到源码，确认这条引用是否应该在 `onStop()`、`onDestroyView()`、`onCleared()` 或取消订阅时释放。

## 设备端、开发机端和线上端的边界

同一个 hprof 可以被多个工具打开，但工具职责不同。

**设备端 LeakCanary 适合早发现。** 它的优势是自动化：开发者不需要盯着 Profiler，页面关闭后就能收到 retained object 通知。缺点也来自自动化：每次 dump hprof 都会冻结 App 一小段时间，设备端分析也会消耗资源。对日常开发来说，这个成本可以接受；对性能测试和线上 release 来说，要严格关掉或改成采样方案。

**开发机端 Android Studio 适合做定位。** Panda 的 LeakCanary task 把分析结果放到 IDE 里，源码跳转和复制完整分析都更顺手。它适合本地稳定复现后的第二步：把 leak trace 中的怀疑引用和项目代码对上。

**线上端方案适合拿现场，不适合常驻全量 dump。** Android 17 文档提到 App memory limits 命中时，`ApplicationExitInfo.getDescription()` 可带 `MemoryLimiter:AnonSwap` 信息，也可以通过 trigger-based profiling 的 `TRIGGER_TYPE_ANOMALY` 收集 heap dump。这个能力适合在系统判定异常时补证据，不应被设计成高频全量采集入口。[已验证: 官方文档, https://developer.android.com/about/versions/17/behavior-changes-all]

Koom 这类线上 SDK 通过 fork 子进程 dump hprof 来降低主进程停顿，本地研究材料记录了 Suspend VM → fork → Resume VM → 子进程 dump 的路径；它能降低 dump 对前台体验的影响，但仍要处理文件体积、隐私字段、上传时机和服务端 Shark 分析成本。[来源: Obsidian, OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-03-app_exit_info_tracker_and_koom_fork_hprof.md]

## Java / Kotlin 堆泄漏与 Native 内存问题要分开查

HPROF 主要回答托管堆问题：Java / Kotlin 对象为什么还可达，哪条引用链阻止 GC 回收。它不能覆盖所有内存增长。

| 现象 | 优先工具 | 判断依据 | 不要误用 |
|---|---|---|---|
| Activity / Fragment 退出后仍存在 | LeakCanary、Android Studio heap dump | retained object、GC root path、字段引用 | 不要只看 PSS 上涨就判定 Java 泄漏 |
| Java Heap 阶梯状上涨 | Memory Profiler、heap dump、`dumpsys meminfo` | class 数量增长、retained size、重复复现后不回落 | 不要用 heapprofd 替代引用链分析 |
| Native Heap 持续上涨 | heapprofd、malloc debug、libmemunreachable | malloc 调用栈、当前存活分配、free 配对关系 | 不要指望 hprof 找到 C++ `malloc` 泄漏 |
| Graphics / dma-buf 上涨 | `dumpsys meminfo`、`showmap`、SurfaceFlinger、Perfetto | Graphic Buffer、Surface、WebView、视频 buffer 生命周期 | 不要把 Graphics 全部归到 Native Heap |
| Android 17 内存上限命中 | `ApplicationExitInfo`、ProfilingTrigger、heap dump | `MemoryLimiter` 描述、系统触发现场 | 不要把系统强制限制写成 App 侧泄漏结论 |

Perfetto 的 heapprofd 适合 Native 分配采样。它记录 `malloc` / `free` 路径和采样调用栈，能看“哪条调用栈当前存活分配最多”。这和 hprof 的 GC root 引用链是两套证据。前者证明 Native 分配没有释放，后者证明托管对象仍可达。[已验证: Perfetto 文档, https://perfetto.dev/docs/data-sources/native-heap-profiler]

§14.3 已经展开 heapprofd、malloc debug、showmap 和 libmeminfo；本节只给工具分工。遇到内存上涨，先用 `dumpsys meminfo` 把 Java Heap、Native Heap、Graphics、TOTAL PSS 分开，再决定进入 hprof、heapprofd 还是图形内存路径。

## 与现有 LeakCanary 接入方案怎么取舍

开发期推荐保留 LeakCanary 的 debug 依赖，再把 Android Studio task 作为重分析入口。这样覆盖两类需求：日常开发自动发现泄漏，稳定复现后在 IDE 里做源码定位。

这段 Gradle 配置的作用是把 LeakCanary 只放到 debug 构建中，避免进入 release 包：

```kotlin
dependencies {
    debugImplementation("com.squareup.leakcanary:leakcanary-android:2.14")
}
```

LeakCanary 2.x 默认通过 ContentProvider 自动初始化。只有多进程、严格启动顺序、direct boot 或需要修改 `retainedDelayMillis` 等场景，才考虑手动安装。普通单进程 App 不要为了“可控”额外写初始化代码，写多了反而容易制造启动顺序问题。

CI 和回归测试更适合用可复现的场景驱动，而不是要求每次测试都打开完整 Profiler。可选做法是维护一个标准泄漏样例库：每个样例规定页面进入/退出次数、等待 GC 的时间、预期 retained 对象数量和修复后的验证方式。LeakCanary 的 UI test / Shark 离线分析可以作为自动化基础；Android Studio task 负责人工复核疑难样例。

线上场景不建议照搬开发期 LeakCanary。更稳的策略是三层：常驻监控只采集轻量指标，异常命中后再采样 heap dump，服务端用 Shark 或自研规则聚合 leak signature。Android 15+ 的 `ProfilingManager` 和 Android 17 的 anomaly trigger 可以作为系统补偿入口，但受限流和触发条件约束，不能替代 SDK 自身的生命周期监控。

## 实战排查流程

一个可复查的泄漏排查流程可以固定成六步。

### 1. 先构造受控复现场景

不要从一次随机内存上涨开始。选择一个页面或业务动作，按固定次数重复：进入页面 → 执行目标操作 → 退出页面 → 等主线程空闲和一次 GC。记录设备、系统版本、构建类型、页面路径、重复次数和等待时间。

如果目标是 Activity / Fragment 泄漏，先看 LeakCanary 是否报告 retained object；如果没有报告，再用 Memory Profiler 手动 heap dump 看对象数量。LeakCanary 没报不代表没有问题，可能还没达到阈值，或观察对象不在默认范围内。

### 2. 抓取 heap dump 并保留原始文件

Android Studio 的 Memory Profiler 可以直接 capture heap dump。命令行也可以用 `am dumpheap` 获取 hprof，适合脚本化场景。

这组命令用于在设备上生成 hprof，再拉到开发机归档：

```bash
adb shell pidof com.example.app
adb shell am dumpheap -g --user 0 <pid> /data/local/tmp/example-after-exit.hprof
adb pull /data/local/tmp/example-after-exit.hprof ./artifacts/example-after-exit.hprof
```

`-g` 会请求 dump 前先执行 GC。GC 是请求，不是严格同步屏障；仍要结合 repeated run 和对象数量趋势判断。

### 3. 从 retained object 回到持有者

在 LeakCanary 报告里看 leak trace，在 Android Studio heap dump 里看 Instance Details。不要停在“Activity retained”这一层，要继续找持有者类型：静态字段、集合、listener、Handler message、协程 job、线程本地变量、JNI global reference，还是 framework 已知 library leak。

定位时优先看两个信息：怀疑引用字段名和持有者生命周期。字段名告诉你代码位置，生命周期告诉你这条引用是否合理。Application 持有全局缓存是合理的；Application 持有 Activity View 通常不合理。线程栈持有局部变量可能是瞬时状态；延迟消息持有 Activity 则要看消息是否超过页面生命周期。

### 4. 回到源码做最小修复

修复动作要清掉“过长生命周期持有短生命周期对象”这条边。常见动作包括：

- 在 `onDestroyView()` 清理 Fragment View binding、adapter、listener。
- 在 `onStop()` 或 `onDestroy()` 解注册系统 callback、EventBus、Flow collector 外部订阅。
- 取消超出页面生命周期的 coroutine、Rx subscription、Handler delayed Runnable。
- 单例只保存 Application context 或业务 ID，不保存 Activity、View、Drawable。
- WebView、Bitmap cache、播放器和 Camera 预览单独管理生命周期，不把释放动作寄托给 GC。

不要把强引用改成弱引用当作默认修复。LeakCanary 文档也明确提醒，弱引用通常只是隐藏了生命周期错误，并可能引入对象过早回收的新问题。[已验证: LeakCanary 文档, https://square.github.io/leakcanary/fundamentals-fixing-a-memory-leak/]

### 5. 再抓一次验证

修复后重复同一脚本。验证不只看“LeakCanary 不再报”，还要看目标 class 实例数量、retained size 和引用路径是否消失。对于曾经有误报风险的 Fragment 缓存场景，还要确认行为没有被误修：页面切换、配置变更、back stack 恢复都要跑一遍。

### 6. 把证据写进回归用例

泄漏修复最怕回归。把复现场景、触发次数、目标对象、修复字段和验证方式写到测试用例或团队知识库里。复杂问题保留 hprof 文件名、LeakCanary leak signature 和修复 commit，后续再遇到同类签名时可以直接对比。

## [自动发现] Android Studio Panda 的版本边界

Android Studio 文档页面显示当前稳定版本线已到 Android Studio Panda 4，Panda 线包含 LeakCanary Profiler task。这个能力属于 IDE 功能，不是 Android 平台 API；因此 App 的 `minSdk` 不决定 task 是否可用。影响可用性的因素是 Android Studio 版本、Profiler 能否连接目标进程、应用是否 debuggable/profileable，以及 LeakCanary 现场能否产出可解析的 hprof。[已验证: 官方文档, https://developer.android.com/studio/preview/features]

AGP 和 JDK 对这项能力的影响主要来自工程同步和运行配置，而不是 LeakCanary task 本身。遇到“Profiler task 看不到结果”时，先检查 Android Studio 版本和 LeakCanary 依赖，再检查设备连接、目标进程、构建变体和 hprof 是否能被 Memory Profiler 打开。

## [自动发现] 标准泄漏样例库

团队里可以维护一组最小泄漏样例，用来训练新人、验证工具和做回归测试。样例不求复杂，目标是覆盖典型持有边。

| 样例 | 触发方式 | 预期证据 | 修复动作 |
|---|---|---|---|
| Activity 被单例持有 | 单例列表保存 Activity 或 View | leak trace 中出现 `Singleton.list` → `Activity` | 单例改存业务 ID 或 Application context，退出时移除引用 |
| Fragment View binding 泄漏 | `onDestroyView()` 不置空 binding | retained object 是 Fragment View 或 Activity | 在 `onDestroyView()` 断开 binding、adapter、listener |
| Handler delayed Runnable | 页面退出前 post long delay | `MessageQueue` / Runnable 持有外部类 | `onDestroy()` 调用 `removeCallbacksAndMessages()` 或改生命周期作用域 |
| 协程闭包持有 Activity | 全局 scope 启动任务并捕获 View | Job / continuation 路径到 Activity | 使用 lifecycle scope，退出时取消任务 |
| Listener 未解注册 | 注册到系统服务或全局事件总线 | 全局 registry 持有 callback | 在可见性边界解注册，避免等待 `onDestroy()` |
| WebView / Bitmap cache | 静态 cache 保存页面对象或大图 | Java 对象路径和 Graphics/Native 同涨 | 拆分 Java 引用释放与 buffer/cache 清理 |

这些样例能让 LeakCanary、Android Studio task、Memory Profiler 和 `dumpsys meminfo` 对同一问题给出不同证据。读者能看到工具分工：LeakCanary 找 retained object，heap dump 查引用路径，`dumpsys meminfo` 看总体变化，Perfetto/heapprofd 查 Native 分配。

## [自动发现] Native 内存诊断联动

当 heap dump 没有发现异常 retained object，但 PSS 或 Native Heap 仍在上涨，排查应切到 Native 路线。§14.3 已经给出工具细节，这里给一条联动路径：

1. 用 `dumpsys meminfo <package>` 区分 Java Heap、Native Heap、Graphics 和 TOTAL PSS。
2. Native Heap 上涨时开 heapprofd，看 `Allocated at snapshot` 中当前存活分配最多的调用栈。
3. 采样精度不够时，用 malloc debug 或 libmemunreachable 做调试版复现。
4. Graphics 上涨时看 `showmap`、SurfaceFlinger layer、BufferQueue 和 Perfetto 图形轨道。
5. Java Heap 正常、Native Heap 正常、系统仍触发 Android 17 memory limit 时，回到 `ApplicationExitInfo` 和 ProfilingTrigger 取系统侧证据。

这条路径能避免一个常见误判：看到内存上涨就反复抓 hprof。hprof 只能证明托管堆对象关系，Native buffer、图形内存、mmap 区域和系统限制要用对应工具验证。

## 与其他章节的关系

- §10.2 讲内存泄漏的定义、常见模式和 Java / Native 分工；本节接在工具层，聚焦 Android Studio + LeakCanary + hprof 工作流。
- §14.3 展开内存分析工具全景，包括 MAT、heapprofd、malloc debug、showmap；本节补 Panda 新 task 和 IDE 内源码上下文。
- §23.1 面向应用内存实战，适合放真实页面泄漏、WebView、Bitmap cache、协程和 listener 的治理案例。
- §19.5 / §26.2 涉及线上 APM、Koom 和系统退出原因时，可以引用本节的 hprof 证据口径，但不要重复解释 LeakCanary 原理。

## 参考资料

- [Android Studio Preview features: LeakCanary in Android Studio Profiler](https://developer.android.com/studio/preview/features)
- [Android Developers Blog: The Fourth Beta of Android 17](https://developer.android.com/blog/posts/the-fourth-beta-of-android-17)
- [Android 17 behavior changes: App memory limits and LeakCanary task](https://developer.android.com/about/versions/17/behavior-changes-all)
- [Android Studio: Capture a heap dump](https://developer.android.com/studio/profile/capture-heap-dump)
- [LeakCanary: How LeakCanary works](https://square.github.io/leakcanary/fundamentals-how-leakcanary-works/)
- [LeakCanary: Fixing a memory leak](https://square.github.io/leakcanary/fundamentals-fixing-a-memory-leak/)
- [Perfetto: Native heap profiler](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [来源: intake/daily-info/2026-05-17.md]
- [来源: DeepResearch/android-skills-profilers/2026-05-16-android-skills-profilers-深度调研.md]
- [来源: OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-03-app_exit_info_tracker_and_koom_fork_hprof.md]
