---
title: "Android 17（API 37）性能行为变更与适配方法"
chapter: "16.5"
section: "16.5"
status: finalized
applicable_versions: "Android 17 (API 37)"
last_verified: 2026-08-14
last_verified_against: "AOSP android-17.0.0_r1 frameworks/base + ART + packages/modules/Profiling; current Android 17 behavior, API, security, network, and page-size docs through 2026-08-14"
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-all"
  - type: official
    path: "https://developer.android.com/about/versions/17/changes/messagequeue"
  - type: official
    path: "https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html"
  - type: official
    path: "https://developer.android.com/about/versions/17/features"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingTrigger"
  - type: official
    path: "https://developer.android.com/reference/android/app/job/JobScheduler"
  - type: official
    path: "https://developer.android.com/guide/topics/resources/runtime-changes"
  - type: official
    path: "https://developer.android.com/about/versions/17/changes/ff-restrictions-ignored"
  - type: official
    path: "https://developer.android.com/privacy-and-security/security-config"
  - type: official
    path: "https://developer.android.com/privacy-and-security/local-network-permission"
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
  - type: official
    path: "https://developer.android.com/about/versions/17/changes/bg-audio"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/CombinedMessageQueue/MessageQueue.java"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/res/values/attrs_manifest.xml"
  - type: source
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/runtime.cc"
  - type: source
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc"
  - type: source
    path: "https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java"
tags: "[android17, api37, behavior-changes, performance, deliqueue, generational-gc, profiling-manager, cloud-compilation]"
related_chapters: '["1.6", "1.13", "4.8", "5.7", "8.2", "19", "16.2", "16.4"]'
task9_state: reviewed
task2b_state: fixed
pipeline_stage: ready-to-publish
task6_state: reviewed
---

# Android 17（API 37）性能行为变更与适配方法

## 阅读边界：四组变化不能混在一起

`target SDK` 是应用通过 `targetSdkVersion` 声明的目标行为级别，它会决定一部分兼容开关。设备所运行的系统版本则决定平台实现与可用 API，二者是独立维度。

本文以 Android 17 / API 37 / `android-17.0.0_r1` 为平台锚点。性能文章很容易把 target SDK 行为、所有应用行为、公开 API 和系统实现改动写成同一种“Android 17 强制变化”，迁移时必须按触发条件分开判断。

| 类别 | 触发条件 | 涉及项目 |
|:---|:---|:---|
| target SDK 行为 | Android 17 上运行且 `targetSdkVersion >= 37` | 新 `MessageQueue`、`static final` 写保护、ECH、CT、原生动态加载、局域网权限、大屏约束 |
| Android 17 平台行为 | 运行在 Android 17；文档未声明 target SDK 门槛 | 部分设备的 app memory limits、后台音频基础限制、特定配置变化不再重建 Activity |
| API 与运行时能力 | API 37 或 Android 17 的系统组件提供能力 | `ProfilingTrigger`、`JobScheduler.getPendingJobReasonStats()`、ART 分代 CMC |
| 延续性兼容要求 | 早于 Android 17 已出现，升级时仍需满足 | 16KB 页面大小 |

这四类变化的验证方法也不同。行为开关要做兼容性 A/B，也就是在同一应用上分别启用和关闭开关；公开 API 要检查返回边界；ART 与图形实现要读 trace；16KB 要检查每个 ELF（Executable and Linkable Format，`.so` 使用的二进制格式）及其打包对齐。

## DeliQueue：重写的是消息入队争用

### 旧队列为何会阻塞主线程

旧 `MessageQueue` 用同一个对象 monitor（Java 对象监视器锁）保护按 `when` 排序的单链表。后台线程通过 `Handler.post()` 或 `sendMessage()` 入队，Looper 线程通过 `next()` 取消息，两边会竞争同一把锁。业务回调执行期间不会持有这个 monitor；把整段 `doFrame()` 或布局时间算成队列持锁时间，会误判卡顿来源。

旧实现遇到高并发投递时可能出现优先级反转：较低优先级线程在队列维护代码中持锁，主线程等待 monitor。Perfetto 中应沿 `android.monitor_contention` 事件回到 waiter 与 owner 的调用栈，确认 owner 是否位于 `MessageQueue.enqueueMessage()` 附近。仅凭主线程处于 Sleeping 状态无法证明是消息队列锁。

### Android 17 的启用边界

Android 17 对 target SDK 37 及以上应用启用新的 lock-free `MessageQueue`，这里的 lock-free 指消息入队不再依赖一把全局锁。`android-17.0.0_r1` 把兼容实现和并发实现放在同一个文件：

`frameworks/base/core/java/android/os/CombinedMessageQueue/MessageQueue.java`

该文件中的 compat change ID（兼容性变更编号）为 `USE_NEW_MESSAGEQUEUE = 421623328L`。应用侧选择条件来自 `CompatChanges.isChangeEnabled(USE_NEW_MESSAGEQUEUE)`；平台还保留 feature flag（平台功能开关）和系统进程选择逻辑，因此不能用应用 target SDK 推断所有系统进程的队列模式。

官方把这套设计称为 DeliQueue。下图只表达职责分离：producer 指投递消息的线程，consumer 指取出消息的 Looper 线程；图中的名称不代表 r1 中存在同名 Java 类。

```text
background producer threads
      │  VarHandle CAS
      ▼
Treiber-style StackNode 链
      │  Looper 调用 nextMessage() 时 drain
      ▼
普通消息有序集合 + 异步消息有序集合
      │  when / insertSeq
      ▼
Looper 选择可交付消息
```

后台 producer 通过 CAS（compare-and-set，比较并交换）把消息压入 Treiber stack；它是一种用 CAS 更新栈顶的无锁链栈。Looper 端批量取走节点，再按投递时间和序号选择消息。Looper 线程给自己的队列投递时有直接写入有序集合的快速路径。同步屏障是队列中的特殊标记，可让异步消息越过暂时被拦住的普通消息，因此仍会影响两类消息的选择。

### 博客模型怎样对应到固定 r1 标签源码

Android Developers Blog 用 “Treiber stack + single-threaded min-heap” 解释算法，并讨论 tombstone（逻辑删除标记）、把退出状态编码进原生层引用计数的方案，以及无分支比较器。这个概念模型有助于理解并发写入和有序读取的分工。

`android-17.0.0_r1` 的 Java 源码组织与早期说明不同：

- `StackNode`、`MessageNode`、`StateNode`、`QuittingNode` 是 `MessageQueue.java` 的嵌套类。
- `VarHandle` 是 Java 提供的底层变量访问句柄，源码用 `sState` 对 `mStateValue` 做原子读写。成功的 CAS 决定本次入队何时生效，这个瞬间就是并发语义中的线性化点；CAS 失败的线程重读状态后重试。
- Looper 线程自身入队时直接调用 `insertIntoPriorityQueue()`；其他线程走并发栈。
- drain 后的普通消息与异步消息分别存入两个 `ConcurrentSkipListSet<Message>`：`mPriorityQueue` 和 `mAsyncPriorityQueue`。该类型是基于 skip list（跳表）的并发有序集合。
- 同一 `when` 下用 `insertSeq` 保持顺序；`sendMessageAtFrontOfQueue()` 使用递减序号维持队首投递语义。
- 移除路径会以原子标记完成逻辑删除，Looper 随后跳过或清理已移除节点。

所以，这里的“MessageStack / MessageHeap”只表示写入栈和有序读取端的职责。r1 没有 `MessageStack.java`、`MessageHeap.java`、`CombinedDeliMessageQueue/` 或 `LegacyMessageQueue/` 这些路径。源码定位应以 `CombinedMessageQueue/MessageQueue.java` 为准。

“lock-free MessageQueue”也不表示整个文件没有任何锁。消息入队的共享关键路径不再依赖 legacy 全局 monitor；IdleHandler、文件描述符监听、drain 完成通知等辅助状态仍可使用 `synchronized` 或 `ReentrantLock`。它保证系统在竞争下能持续推进，不保证每个线程都在固定次数内完成操作。

### drain 发生在什么位置

Looper 进入并发实现的 `nextMessage()` 后，会把栈状态切到 active，取得旧栈顶并调用 `drainStack(oldTop)`。这里的 drain 指把并发栈中的一批节点转移到有序集合。随后 Looper 从普通、异步两个集合取最早项，结合同步屏障和当前时间决定交付、等待或再次循环。

drain 是批量转移点，也是理解 trace 的边界。producer 的 CAS 完成只代表消息已发布到并发栈；消息按 `when` 进入可交付顺序，需要 Looper 完成 drain。高频 producer 仍可能增加 Looper 的整理工作，所以 lock contention 下降不等于队列积压消失。

### 兼容性风险与测试方式

公共 `Handler`、`Looper`、`Message` 用法无需迁移。风险集中在私有实现依赖：

- 反射读取 `MessageQueue.mMessages` 或遍历旧链表。
- 自制 idle 检测、测试框架或监控 SDK 假定队头保存在 `mMessages`。
- 通过 JNI 或 hidden API（未公开的平台接口）操作队列内部状态。

为维持二进制兼容，Android 17 仍保留 `mMessages` 字段；并发实现启用时该字段恒为 `null`。字段存在不能说明旧链表仍在工作。

官方给出的测试库基线是 Espresso 3.7.0 及以上、Robolectric 4.17 及以上。Robolectric 测试还要从 `@LooperMode(LEGACY)` 迁到 `@LooperMode(PAUSED)`。

以下命令用于在可调试应用上做同包 A/B。

```bash
adb shell am compat enable USE_NEW_MESSAGEQUEUE com.example.app
adb shell am force-stop com.example.app

adb shell am compat disable USE_NEW_MESSAGEQUEUE com.example.app
adb shell am force-stop com.example.app
```

每次切换后都重新启动进程，并保持机型、构建、场景、trace 配置和热状态一致。compat disable 适合定位，不应作为 target SDK 37 发布方案。

### 公开性能数据该怎样使用

官方博客公开了三组数据：

| 证据 | 官方结果 | 解释边界 |
|:---|:---|:---|
| `busy queue synthetic benchmark`（繁忙队列合成压测） | 多线程插入最高快 5,000 倍 | 压力测试上限，不代表端到端页面性能 |
| internal beta Perfetto traces | App 主线程 lock contention 时间下降 15% | 只衡量锁等待 |
| 同批测试设备体验指标 | App missed frames 下降 4%；System UI / Launcher 下降 7.7%；启动到首帧 P95 下降 9.1% | 官方未公开完整设备、脚本和原始 trace |

业务验收应同时看三类指标：`android.monitor_contention` 中队列 monitor 等待、消息排队时间、帧或启动端到端指标。若锁等待下降而消息排队时间上升，瓶颈已经转移到 producer 数量、Looper 回调成本或 drain 压力。

分析 `system_server` 的消息流时，官方博客给出了 `mq` track-event category，也就是名为 `mq` 的 trace 采集类别。下面是可嵌入 Perfetto 配置的最小片段。

```textproto
data_sources {
  config {
    name: "track_event"
    track_event_config {
      enabled_categories: "mq"
    }
  }
}
```

该 category 用于观察消息投递与交付流。普通应用是否出现同等细节取决于进程、构建类型和 trace 权限，不能把没有 `mq` slice 当成 DeliQueue 未启用。

## ART 分代 CMC：Android 17 新增的是 CMC 分代路径

ART（Android Runtime）在 Android 10 已有分代 Concurrent Copying（CC，并发复制）回收器。Android 17 的变化是 Concurrent Mark-Compact（CMC，并发标记-压缩）加入分代能力。两件事不能写成“Android 17 才有分代 GC”。

官方对收益的表述是：更频繁、成本更低的年轻代回收可减轻 GC 对应用的干扰，并改善最大 RSS（resident set size，进程驻留内存）。官方没有给出适用于所有应用的暂停时间或内存百分比。列表、图片和解析场景都应在自己的分配速率与对象存活分布下测量。

### r1 的 young、mid、old 模型

`art/runtime/gc/collector/mark_compact.cc` 把上次 GC 后的新分配视为 young：

1. 对象存活一次 GC 后进入 mid。
2. 下一次 young GC 同时标记 young 与 mid，并通过 card table 处理 old 到年轻区域的引用。card table 是按固定内存片记录跨代引用的表，可避免每次都扫描整个 old 区域。
3. 存活的 mid 对象压缩后晋升 old，存活的 young 对象压缩后进入 mid。
4. full GC 处理全堆，并重置或更新分代边界。

这里不能写成“young GC 完全忽略 old”。old 区域通常不做整区追踪和压缩，但 old-to-young 引用仍要靠 aged/dirty cards 与根处理保证可达性。

`YoungMarkCompact` 也没有单独的 `young_mark_compact.cc`。它的构造与 `RunPhases()` 实现在 `mark_compact.cc`，内部复用主 `MarkCompact` collector，并在本轮设置 `young_gen_`。

### Generational CMC 的启用门槛

下面的等价表达式用于说明 `android-17.0.0_r1` 的启用关系，变量名与源码一致。

```cpp
use_generational_gc =
    (kUseBakerReadBarrier || gUseUserfaultfd)
    && xgc_option.generational_gc
    && ShouldUseGenerationalGC();

if (gUseUserfaultfd && !flags::use_generational_cmc()) {
    return false;
}
return GetBoolProperty(
    "persist.device_config.runtime_native_boot.use_generational_gc", true);
```

顶层是三项 AND：可兼容的 read barrier（对象引用读取屏障）或 userfaultfd（Linux 用户态缺页处理机制）路径、运行时 GC 选项、`ShouldUseGenerationalGC()`。`use_generational_cmc` 只在 `gUseUserfaultfd` 为真时形成额外门槛。device-config 系统属性的默认值是 `true`，所以 `device_config get` 返回空值不能直接判定功能关闭。

应用不应修改 ART 的 device-config 或假定所有 Android 17 设备使用同一 collector。OEM 配置、ART Mainline（可独立更新的 ART 系统模块）和运行时选项都可能改变选择；Android 17 的 ART 改进还可通过 Google Play 系统更新覆盖 Android 12 及以上版本。

验证时以目标进程的 GC 事件、暂停分布、分配速率和 RSS 为证据。对同一测试负载，对比 young/full collection 次数、GC CPU 时间、mutator stall（应用线程因 GC 停顿的时间）与峰值 RSS，比只查一个属性更可靠。需要展开回收器与暂停分析时，参阅 [[07-art-generational-gc|4.7 ART 分代 GC、Region 碎片与暂停分析]]。

## ProfilingManager：系统事件提供采集时机

Android 17 为 `ProfilingManager` 增加多种系统 trigger，也就是由特定系统事件启动的采集条件。应用仍需注册全局结果监听器并添加 trigger；系统不保证每次事件都有产物，采集还受系统与应用设置的限频约束。

### API 37 主要 trigger 与产物

| trigger | 触发条件 | API 37 定义的产物或边界 |
|:---|:---|:---|
| `TRIGGER_TYPE_COLD_START` | `ApplicationStartInfo.START_TYPE_COLD` | 新启动的 system trace（系统级 Perfetto 轨迹）+ stack sampling（调用栈采样）；持续到 `reportFullyDrawn()`，未调用时默认 5 秒停止 |
| `TRIGGER_TYPE_OOM` | 未捕获 `OutOfMemoryError` | Java heap dump（堆转储）；自定义 uncaught handler（未捕获异常处理器）必须继续调用默认 handler |
| `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` | 进程因过量 CPU 被杀，exit reason 为 `REASON_EXCESSIVE_RESOURCE_USAGE` | 正在运行的 system trace 快照 |
| `TRIGGER_TYPE_ANOMALY` | 系统识别到资源或性能异常 | 产物随 anomaly 类型变化，`ProfilingResult.getTag()` 提供类型信息 |
| `TRIGGER_TYPE_APP_COMPAT` | 系统识别到未来版本将不支持的行为 | 产物随问题变化，tag 提供兼容问题信息 |

`TRIGGER_TYPE_ANOMALY` 注册在 shared UID 场景时，部分异常可能不给产物；shared UID 指多个 package 共用同一个 Linux 用户 ID。OOM trigger 若被自定义 uncaught handler 截断，也不会完成预期 heap dump。接入阶段必须测试这些失败分支。

下面的示例展示最小注册顺序，重点是先注册全局 listener（监听器），再添加 trigger。

```java
if (Build.VERSION.SDK_INT >= 37) {
    ProfilingManager profiling =
            getSystemService(ProfilingManager.class);

    profiling.registerForAllProfilingResults(
            getMainExecutor(),
            result -> handleProfilingResult(result));

    ProfilingTrigger coldStart =
            new ProfilingTrigger.Builder(
                    ProfilingTrigger.TRIGGER_TYPE_COLD_START)
                    .setRateLimitingPeriodHours(24)
                    .build();

    profiling.addProfilingTriggers(List.of(coldStart));
}
```

`setRateLimitingPeriodHours(24)` 是应用提出的最短间隔，系统仍可延后或不交付。回调中要先检查 `getErrorCode()`，成功后再读取 `getResultFilePath()`、`getTriggerType()` 与 `getTag()`；系统 trigger 的结果只交给全局 listener。

把 trigger 当作线上证据入口，不要把它写成常驻采样器。产物可能包含堆对象、调用栈和业务标识，上传与保留策略要遵守隐私、权限和数据最小化要求。完整使用方式参阅 [[16-profiling-manager|ProfilingManager]]。

## JobScheduler pending reason 统计

API 36 已提供当前 pending reasons（任务暂时无法执行的原因）与有限历史。API 37 新增：

`Map<Integer, Duration> JobScheduler.getPendingJobReasonStats(int jobId)`

返回值把 `PENDING_JOB_REASON_*` 映射到该 job 从调度到结束的生命周期内，因该原因 pending 的累计时长。多个原因可能同时成立，各项 `Duration` 之和常会超过总等待时间。

这些统计不跨重启持久化；job 成功完成或取消时也会清空。传入的 ID 若不是当前 pending job，API 会抛出 `IllegalArgumentException`。诊断顺序可按“当前 reasons → history → stats”推进：

- current reasons 回答此刻卡在哪里。
- history 回答约束在何时变化。
- stats 回答长期占比最高的约束，但不能由各项相加计算 wall time，也就是实际流逝的等待时间。

WorkManager 场景还要建立 `WorkSpec` 与系统 job ID 的映射；`WorkSpec` 是 WorkManager 保存的一条内部任务记录。否则，拿错 job ID 会把调度问题变成数据对齐问题。后台调度机制参阅 [[08-jobscheduler-workmanager-performance|5.8 JobScheduler/WorkManager 调度与后台任务性能]]。

## target SDK 37 适配项

### `static final` 字段不可修改

Android 17 上运行且 target SDK 37 及以上的应用，不能再修改 `static final` 字段：

- Java reflection 写入会抛出 `IllegalAccessException`。
- JNI `SetStatic<Type>Field()` 写入会导致应用崩溃。

影响面常在测试注入、旧序列化框架、热修复和 native 测试工具。`setAccessible(true)` 不能绕过该限制。将可变测试值放进构造参数、接口、配置对象或专用的测试替换点；常量继续保持常量。发布前同时扫描 Java/Kotlin 反射与 JNI，因为两条失败路径不同。

这项约束允许 ART 更积极地依赖常量语义做优化，但不能据此推导某段业务代码一定获得可测加速。迁移目标是移除未受规范保证的写入行为。

### 大屏方向、尺寸与 Activity 配置变化

target SDK 37 应用运行在 smallest width（配置中的最小可用宽度）至少 600dp 的大屏上时，平台会忽略固定方向、不可调整大小和宽高比限制，包括相关 manifest 属性与 `setRequestedOrientation()` 值。

以 `android:appCategory` 识别的游戏、较小屏幕以及用户在设备设置中的显式选择属于文档列出的例外。

适配重点是窗口尺寸变化后的正确性与帧稳定性：

- 用 `WindowMetrics`（当前窗口可用范围）和自适应布局决定内容结构，避免用物理屏幕尺寸或启动方向固化布局。
- 保存编辑、滚动、播放等 UI 状态，覆盖旋转、折叠、多窗口和桌面自由窗口。
- 检查相机预览、Surface、地图和 `AndroidView` 等嵌入组件在尺寸连续变化时的重建成本。
- 用 Perfetto 观察配置变化附近的 lifecycle、`performTraversals`（View 系统的一轮测量、布局与绘制遍历）、buffer queue（图形生产者与消费者之间的缓冲队列）和 missed frame。

大屏约束由 target SDK 37 触发，下面的 Activity 重建优化则是另一类 Android 17 平台默认规则。官方运行时配置指南没有为它声明 target SDK 门槛：keyboard、keyboardHidden、navigation、touchscreen、colorMode，以及进出 desk UI mode 时，系统默认不再销毁重建 Activity，而是保留实例并调用 `onConfigurationChanged()`。

`android-17.0.0_r1` 的 `attrs_manifest.xml` 允许 `android:recreateOnConfigChanges` 使用 touchscreen、keyboard、keyboardHidden、navigation、colorMode，以及 Android 8 已有的 mcc、mnc（移动国家码与移动网络码）；同一个标志不能再放入 `android:configChanges`。

该属性没有 `uiMode` 取值，因此进出 desk UI mode（桌面停靠模式）时要由应用更新资源和组件。下面的示例只为确有重建依赖的五类 Android 17 事件恢复旧行为。

```xml
<activity
    android:name=".ReaderActivity"
    android:recreateOnConfigChanges="keyboard|keyboardHidden|navigation|colorMode|touchscreen" />
```

这五类事件发生时，该属性会让 Activity 执行完整的 stop、destroy、recreate 周期。没有重建依赖时，应在 `onConfigurationChanged()` 中更新非 Compose 状态与嵌入组件；Compose 中读取 `LocalConfiguration.current` 的部分会重组，`AndroidView`、`AndroidFragment` 等嵌入对象仍需应用自行刷新。

### Network Security Configuration、ECH 与 CT

Android 17 计划在未来版本弃用 manifest 级 `usesCleartextTraffic`，当前版本尚未删除该属性。Network Security Configuration 是声明式 XML 配置，可把仍需保留的 HTTP 例外限制到具体域名。若 `minSdkVersion >= 24`，可只使用这份配置；若最低支持版本低于 24，官方建议同时保留 `usesCleartextTraffic="true"` 和网络安全配置文件。

对 target SDK 37 应用，Android 17 为 TLS 连接启用 Encrypted Client Hello（ECH），用于加密 ClientHello 中的 SNI（Server Name Indication，服务器名称指示）。生效还要求应用所用网络库已经接入 ECH，服务端也支持协商；无法协商时客户端发送 ECH GREASE，即带随机内容的占位扩展，以减少中间网络设备对固定握手格式的依赖。

Network Security Configuration 新增 `<domainEncryption>`，可在 `<base-config>` 或 `<domain-config>` 中按全局或域名设置 `enabled`、`disabled` 等模式。

下面的配置为 `example.com` 显式选择 `enabled` 模式。

```xml
<network-security-config>
    <domain-config>
        <domain includeSubdomains="true">example.com</domain>
        <domainEncryption mode="enabled" />
    </domain-config>
</network-security-config>
```

`enabled` 表示客户端拿到 ECH 配置时启用 ECH，拿不到时发送 ECH GREASE；它没有提供 fail-closed 语义，也就是不会因服务端缺少 ECH 支持而直接拒绝连接。平台支持、客户端库接入、携带 ECH 配置的 DNS HTTPS 记录和服务端部署都会影响协商。排障要记录网络库版本、DNS 结果和 TLS handshake，不要给 ECH 写固定时延收益。

target SDK 37 应用还会默认启用 Certificate Transparency（CT，证书透明度）。网络栈按 Network Security Configuration 执行 CT 时，证书链或 SCT（Signed Certificate Timestamp，证书已记入日志的签名凭据）不满足策略会使 TLS 连接失败。

若某个 `domain-config` 使用用户证书库或内嵌证书作为 trust anchor（验证证书链的信任根），CT 默认会关闭；需要时可用 `<certificateTransparency enabled="true"/>` 再显式开启。

CT 校验通常使用证书或握手携带的 SCT，不能概括成“每次连接都会访问 CT log”。升级前应覆盖生产域名、备用域名、CDN 切换、证书轮换以及自定义 trust anchor。

### 局域网访问权限

target SDK 37 应用在 Android 17 上访问局域网时，需要声明并在运行时申请 `ACCESS_LOCAL_NETWORK`。该权限属于 `NEARBY_DEVICES` 权限组；用户已授予组内其他权限时，系统不会再次弹出授权框。设备发现、投屏、智能家居、调试桥接和本地 HTTP 服务都要覆盖“未授权、拒绝、之后授权”三条路径。

Google Cast Output Switcher 和带 `DiscoveryRequest.FLAG_SHOW_PICKER` 的 `NsdManager` 可由系统完成发现与选择；这里的 picker 是只把用户选中的设备交给应用的系统选择器，对应场景无需直接获得整个局域网访问权。迁移时应按产品能力选择 picker 或运行时权限，不能用连接超时替代权限状态判断。

缺少权限时，TCP 常表现为超时，UDP 通常返回 `EPERM`（operation not permitted）；native 网络栈可用 `android_getnetworkblockedreason()` 区分 Local Network Protection 拦截。性能测试若包含局域网服务，必须记录授权状态，避免把权限拒绝误判为 DNS、TCP 或服务端性能问题。

### 16KB 页面是延续性发布要求

Android 15 起 AOSP 支持 16KB page-size 设备。这项能力早于 target SDK 37，但 Android 17 迁移仍要检查。Google Play 的现行要求覆盖面向 Android 15（API 35）及以上版本的 64 位设备；自 2027 年 2 月 1 日起，不支持 16KB 页面大小的应用更新将无法发布。

纯 Java/Kotlin 应用通常已兼容。只要 APK/AAB 直接或经 SDK 带有 `.so`，就要同时检查：

- APK/AAB 内未压缩 `.so` 的 ZIP 对齐。
- 每个 ELF `LOAD` segment（装载段）的对齐。
- 所有预编译 SDK 的 native 库版本。
- `mmap()`（内存映射）、共享内存与自制 allocator（内存分配器）是否假定页大小固定为 4096 字节。
- 运行时页大小是否用 `getpagesize()` 或 `sysconf(_SC_PAGESIZE)` 获取。

AGP 8.5.1 及以上配合 NDK r28 及以上，并使用兼容 16KB 的预编译依赖时，官方工具默认处理 16KB ZIP 和 ELF 对齐。NDK r27 及以下可按官方指南为自有库显式加入 `-Wl,-z,max-page-size=16384` 与 `-Wl,-z,common-page-size=16384`；旧版 `libc++_shared.so` 和第三方预编译库仍需逐个核验。

以下命令用于检查 bundle 配置、APK 对齐和 ELF program headers。

```bash
bundletool dump config --bundle app-release.aab
zipalign -c -P 16 -v 4 app-release.apk
llvm-readelf -lW lib/arm64-v8a/libexample.so
adb shell getconf PAGE_SIZE
```

bundle 配置应显示 `PAGE_ALIGNMENT_16K`，`zipalign` 应通过，`readelf` 中每个 `LOAD` segment 的 Align 不得低于 `2**14`，设备命令应返回 `16384`。工具通过后还要在 16KB emulator 或设备上覆盖启动、动态加载、数据库、媒体与 mmap 场景。

Android 17 还能把 16KB backcompat（兼容模式）设为 `fatal`，让不兼容二进制立即终止；这个模式只适合测试，不能代替发布兼容。原理和排查步骤参阅 [[06-16kb-page-size|4.6 16 KB Page Size 与 Android 性能]]。

## 运行在 Android 17 时还要检查的项目

### App memory limits

Android 17 在部分设备上按总 RAM 对应用施加保守的内存上限，面向所有应用。受影响进程的 `ApplicationExitInfo.getReason()` 为 `REASON_OTHER`，description 包含 `MemoryLimiter:AnonSwap` 及附加信息。`TRIGGER_TYPE_ANOMALY` 可在触发限制时请求 heap dump，但交付仍受 trigger 规则约束。

`adb shell am memory-limiter status` 用于查看当前设备是否启用及可见/不可见进程上限。`ignore` 与 `manual` 子命令适合复现测试，不能写成生产规避方式。该退出原因和 LMKD（low-memory killer daemon，系统低内存杀进程服务）的低内存 kill 应分开统计。

### 后台音频

所有运行在 Android 17 的应用，后台播放、audio focus 和音量修改需要可见 Activity，或运行非 `SHORT_SERVICE` 类型的 foreground service（FGS，前台服务）。无效状态下，播放与音量 API 会静默失效，audio focus 返回 `AUDIOFOCUS_REQUEST_FAILED`。

target SDK 37 应用在后台还有一层要求：foreground service 需具备 while-in-use（WIU）能力。这里指系统根据应用可见状态、明确用户交互或受信任的系统委托，判定该 FGS 可以继续使用“仅在使用期间”开放的能力。持有 exact alarm 权限且操作 `USAGE_ALARM` stream 时，文档提供了对应豁免。媒体应用应覆盖通知、蓝牙控制、车机、定时闹钟、进程冻结恢复和用户主动续播。

### 原生动态代码加载

target SDK 37 后，Android 14 对 DEX/JAR 的 Safer Dynamic Code Loading 保护扩展到 native library。经 `System.load()` 加载的 native 文件必须为只读，否则抛出 `UnsatisfiedLinkError`。

优先移除网络下载并执行 native code 的设计。确有动态加载需求时，文件应位于应用私有目录，完成来源与签名或散列校验，并在 `System.load()` 前设置只读。更新时写入独立临时文件，关闭写句柄并校验，设置只读后再原子替换；不要在已加载路径上边写边执行。只读标志满足平台加载检查，签名或散列才用于确认文件来源和内容。

## Choreographer Buffer Stuffing Recovery

这项机制早于 API 37 的迁移边界，但它仍存在于 `android-17.0.0_r1`，分析 Android 17 图形 trace 时容易和 DeliQueue 的效果混淆。buffer stuffing 指图形 buffer 的生产速度持续高于消费速度，导致 buffer queue 被塞满。

`frameworks/base/core/java/android/view/Choreographer.java` 中：

- `onWaitForBufferRelease(durationNanos)` 在等待超过上一帧间隔一半时设置 stuffed 状态。
- `updateBufferStuffingState()` 可能选择 `DELAY_FRAME`，主动等下一次 vsync（垂直同步信号）给 buffer queue 回落机会。
- recovery 进行中可选择 `OFFSET`，把动画时间线向前偏移一个 frame interval，也就是一次垂直同步周期。
- 多次 recovery 与最长累计延迟受 feature flag 控制；r1 常量 `MAX_BUFFER_STUFFING_DELAY_NS` 为 100ms。
- trace 中可出现 `Buffer stuffing recovery`、`buffer stuffed` 和记录负偏移量的事件。

`onWaitForBufferRelease()` 是隐藏接口，应用不能把它当作自定义调度 API。看到 recovery slice（trace 中带持续时间的事件片段）时，应继续查看 `dequeueBuffer` 等待、SurfaceFlinger（系统图形合成服务）、GPU completion、buffer 数量与主线程产出速率。recovery 是缓解 buffer stuffing 的时序策略，也可能主动延迟一帧；它不能证明根因已经消失。

DeliQueue 处理 Java 消息投递争用，Buffer Stuffing Recovery 处理图形 buffer queue 堵塞后的帧时序。两者都可能改善 missed frames，但证据轨道和修复对象不同。

## 迁移检查清单

### 提升 target SDK 前

- [ ] 搜索 `MessageQueue` 私有字段、hidden API、JNI 与自制 idle 检测。
- [ ] 升级到 Espresso 3.7.0+、Robolectric 4.17+，移除 `@LooperMode(LEGACY)`。
- [ ] 搜索反射和 JNI 对 `static final` 的写入。
- [ ] 盘点 HTTP 域名、ECH/CT 兼容、证书、CDN 切换与自定义 trust anchor。
- [ ] 盘点局域网发现和连接入口，覆盖 `ACCESS_LOCAL_NETWORK` 的授权状态。
- [ ] 检查动态 native library 的来源、写权限与加载流程。
- [ ] 在 sw600dp、折叠、多窗口、桌面窗口和方向变化中验证 UI 状态。
- [ ] 审核所有直接和间接 native 依赖的 16KB 对齐。

### Android 17 运行验证

- [ ] 用 compat change 对新旧 MessageQueue 做同包 A/B，记录 monitor contention、排队时间和端到端指标。
- [ ] 以进程 GC 事件确认 collector 和 young/full 分布，不用单一 device-config 值替代 trace。
- [ ] 验证 Profiling trigger 的成功、限频、无产物、shared UID 和自定义 OOM handler 分支。
- [ ] 用 JobScheduler current reasons、history、stats 定位长期 pending 约束。
- [ ] 检查 `ApplicationExitInfo` 中的 `MemoryLimiter:AnonSwap`。
- [ ] 覆盖后台音频在可见、FGS、闹钟、冻结恢复和用户续播状态下的结果。
- [ ] 在 16KB 系统上运行包含 mmap、数据库、媒体和动态加载的回归。

### 性能验收

- [ ] 固定设备、系统 build、应用 build、场景、热状态与 Perfetto 配置。
- [ ] 报告 P50/P95/P99、样本数和波动，不把官方内部百分比当成业务目标。
- [ ] 将 Java 消息争用、GC、Activity 重建、buffer stuffing 和网络握手放到各自证据轨道。
- [ ] 回归正确性、功耗、峰值 RSS 与崩溃，避免只看平均帧时间。

系统与内核边界参阅 [[04-android17-kernel618-performance|16.4 Android 17 系统与内核性能优化]]，其中内核锚点为 `android17-6.18-2026-06_r6`。这是 16.4 为复现实验固定的快照标签，后续发布序列已有更新；API 行为也不能由 kernel tag 单独推导。

## 参考资料

- [Android 17：target SDK 37 行为变更](https://developer.android.com/about/versions/17/behavior-changes-17)
- [Android 17：影响所有应用的行为变更](https://developer.android.com/about/versions/17/behavior-changes-all)
- [MessageQueue behavior change guidance](https://developer.android.com/about/versions/17/changes/messagequeue)
- [Under the hood: Android 17's lock-free MessageQueue](https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html)
- [Android 17 Features and APIs](https://developer.android.com/about/versions/17/features)
- [ProfilingTrigger API reference](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [JobScheduler API reference](https://developer.android.com/reference/android/app/job/JobScheduler)
- [Handle configuration changes](https://developer.android.com/guide/topics/resources/runtime-changes)
- [Restrictions on orientation and resizability are ignored](https://developer.android.com/about/versions/17/changes/ff-restrictions-ignored)
- [Network Security Configuration](https://developer.android.com/privacy-and-security/security-config)
- [Local network permission](https://developer.android.com/privacy-and-security/local-network-permission)
- [Background audio hardening](https://developer.android.com/about/versions/17/changes/bg-audio)
- [Support 16KB page sizes](https://developer.android.com/guide/practices/page-sizes)
- [AOSP r1：CombinedMessageQueue/MessageQueue.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/CombinedMessageQueue/MessageQueue.java)
- [AOSP r1：attrs_manifest.xml](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/res/values/attrs_manifest.xml)
- [AOSP r1：ART runtime.cc](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/runtime.cc)
- [AOSP r1：ART mark_compact.cc](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc)
- [AOSP r1：ProfilingTrigger.java](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java)
- [AOSP r1：JobScheduler.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java)
- [AOSP r1：Choreographer.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java)
