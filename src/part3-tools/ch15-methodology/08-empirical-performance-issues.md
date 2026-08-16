---
title: "Android 性能问题实证：真实世界的分类与代码模式"
chapter: "15.8"
section: "15.8"
status: finalized
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)（章节方法适用范围；实证数据为跨版本综合观察）"
last_verified: "2026-08-14"
last_verified_against: "arXiv:2407.05090v3（2025-10-11）及论文复现仓库；Android 17 / API 37 / AOSP android-17.0.0_r1；kernel android17-6.18-2026-06_r6；2026-08-14 官方 FrameTimeline、ANR、SharedPreferences 与 cached-app freezer 文档"
confidence: medium-high
sources:
  - type: paper
    path: "https://arxiv.org/pdf/2407.05090v3"
  - type: artifact
    path: "https://github.com/Dianshu-Liao/Android-Performance-Analysis"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/frametimeline"
  - type: official
    path: "https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs"
  - type: official
    path: "https://developer.android.com/topic/performance/performance-measurement-examples"
  - type: official
    path: "https://developer.android.com/reference/android/view/View#invalidate()"
  - type: official
    path: "https://developer.android.com/reference/android/view/View#requestLayout()"
  - type: official
    path: "https://developer.android.com/reference/android/content/SharedPreferences"
  - type: official
    path: "https://source.android.com/docs/core/perf/cached-apps-freezer"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/View.java"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/IPCThreadState.cpp"
  - type: source
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6"
tags:
  - android
  - research
  - code-review
  - performance-patterns
  - empirical-study
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---

# Android 性能问题实证：真实世界的分类与代码模式

性能团队很容易被手边的工具塑造优先级：有 heap dump（堆内对象及引用关系的快照），就多查泄漏；有功耗实验室，就多查能耗；有帧时间面板，就多查卡顿。实证研究能提供另一组参照：用户报告什么、开发者讨论和修复什么、论文研究什么。

这类研究适合校准问题覆盖面，不能直接代替本产品的线上数据。样本来源、过滤方法、最终样本量和 Android 版本都会限制结论的外推范围，也就是这些结论能否推广到其他产品、版本或人群。

## 固定论文版本与统计口径

引用版本为 [arXiv:2407.05090v3](https://arxiv.org/pdf/2407.05090v3)，revision（修订版）日期为 2025-10-11。论文的复现资料位于 [Android-Performance-Analysis](https://github.com/Dianshu-Liao/Android-Performance-Analysis)。

版本号必须写进引用。当前 arXiv 摘要页、v3 PDF 和复现仓库 README 存在摘要数字不同步：

- v3 PDF 使用 85 篇论文、14 个公开工具、12 个公开数据集；
- v3 PDF 给出的未覆盖比例是：研究 57.14%、工具 63.41%、数据集 70.73%；
- arXiv 摘要页截至 2026-08-14 仍显示“工具未覆盖 76.39%、数据集未覆盖 66.67%”，与 v3 PDF 的 63.41% 和 70.73% 冲突；
- 复现仓库 README 对汇总表仍写“66 篇论文”，与 v3 PDF 纳入 85 篇冲突。

下文的分子、分母和比例全部以 v3 PDF 正文、表格及结论为准。引用“论文发现”时也要带 revision，避免将不同修订版的数字放在一张表里。

## 数据从哪里来

研究的现实世界部分采用“原始采集 → 87 个性能关键词过滤标题 → 两名作者人工核查”的流程。最终用于分类的样本远小于原始采集量：

| 数据源 | 原始数据 | 关键词过滤后 | 人工核查后 | 代表的视角 |
|---|---:|---:|---:|---|
| Google Play 负面评论 | 60,684 | 165 | 114 | 用户 |
| Stack Overflow Android 问题 | 749,067 | 2,158 | 1,484 | 开发者 |
| GitHub Issues | 16,977 | 149 | 69 | 开发者 |
| GitHub Commits | 344,922 | 558 | 222 | 开发者 |

Google Play 的 60,684 条负面评论来自 909,430 条评论的情感分析模型筛选，该模型用于判断文本偏正面还是负面。GitHub 数据来自 1,643 个同时出现在 F-Droid（开源 Android 应用仓库）与 Google Play 的开源应用。人工核查的一致性以 Cohen's kappa 评估；它是扣除偶然一致后衡量标注者一致性的指标，四组结果为 0.868 至 0.944。

论文部分从五个学术数据库检索，经 venue（期刊、会议等发表场所）过滤、人工排除和前后向 snowballing（沿参考文献与被引论文继续查找），纳入 85 篇 2012—2024 年的研究。论文、工具与数据集可同时覆盖多个性能类别，所以“69/85 篇研究能耗”不是互斥饼图。

### 这些比例能回答什么

它们描述的是这项研究最终样本中的分布，可以用于：

- 检查团队是否只覆盖某一类性能后果；
- 比较用户可感知问题、开发者修复记录与研究投入的差异；
- 寻找静态工具较难覆盖的运行时因素；
- 设计 Code Review 和动态验证的互补范围。

它们无法直接回答：

- 某个产品的 ANR（Application Not Responding，应用无响应）、OOM（Out of Memory，内存不足）或耗电应占多少资源；
- 2026 年全部 Android 应用的总体问题分布；
- Android 17 新机制带来的增量风险；
- 某段可疑代码是否已经造成用户影响。

关键词只匹配标题，可能漏掉没有性能词的记录；最终用户评论只有 114 条，GitHub issue 只有 69 条；开源应用与商业闭源应用也可能不同。论文的 threats to validity（研究局限）章节明确列出了情感模型、抓取完整性、人工标注和样本代表性限制。

## 用户、开发者与研究者的关注点

### 同一张表中的分母不同

| 视角与数据源 | 最常见类别 | 比例 | 分母含义 |
|---|---|---:|---|
| 用户：Google Play | Responsiveness | 62.3% | 114 条核查后评论 |
| 开发者：Stack Overflow | Memory Consumption | 66.1% | 1,484 个核查后问题 |
| 开发者：GitHub Issues | Memory Consumption | 60.0% | 69 个核查后 issue |
| 开发者：GitHub Commits | Memory Consumption | 80.6% | 222 个核查后 commit |
| 研究者：论文 | Energy Consumption | 81.18% | 69/85 篇论文，类别可重叠 |

用户最容易直接描述无响应、界面卡住、操作慢等结果。开发者的问答与修复提交更容易留下 OOM、泄漏、缓存和对象生命周期证据。85 篇论文中有 69 篇涉及能耗，研究投入明显偏向 Energy Consumption。

这些来源仍有交集。用户评论里也有能耗、存储和网络流量，开发者也修复响应性问题，研究也覆盖内存与响应性。研究支持的判断是“各来源的主导类别不同”，不能表述成“各方关注完全分离”。

### 57.14%、63.41%、70.73% 的正确分子

论文先从现实世界样本归纳 63 个 contributing factors（促成因素），再纳入文献结果，形成包含 82 个因素的 taxonomy（分类体系）。最终分类体系比 63 个现实因素多 19 项；这个数字由 82−63 推得，论文没有另列一组 19 项统计。

| 覆盖对象 | 已覆盖 | 未覆盖 | 未覆盖比例 |
|---|---:|---:|---:|
| 学术研究对 63 个现实因素的覆盖 | 27/63 | 36/63 | 57.14% |
| 公开工具对 82 个综合因素的覆盖 | 30/82 | 52/82 | 63.41% |
| 公开数据集对 82 个综合因素的覆盖 | 24/82 | 58/82 | 70.73% |

27/63 是已研究的 42.86%，未研究数是 36，不能把 27 项写成未研究数量。14 个公开工具覆盖 30 个因素，12 个公开数据集覆盖 24 个因素；这里的“覆盖”只记录工具或数据集是否涉及某个因素，不等于工具对这些因素拥有稳定的工业检测率。

## 七类性能后果与 63/82 因素

论文刻意分开 consequence（后果）与 contributing factor（促成因素）：

- **后果**描述用户或工程系统观察到什么；
- **因素**描述哪些行为、资源或代码条件可能促成后果；
- 一个因素可以影响多个后果，一个后果也可能由多个因素共同产生。

例如，“主线程做图片解码”是因素；它可能引发响应性、内存与 CPU 后果。将“卡顿”“复杂布局”“主线程 I/O”写在同一层，会让告警、根因和修复措施混在一起。

为便于回查论文，表中保留英文类别名。Play Vitals 是 Google Play 汇总的线上质量指标，Macrobenchmark 是 Jetpack 的应用级基准测试工具，Binder 是 Android 的进程间通信机制，FrameTimeline 记录帧的预期与实际时间线。

`sched` 指内核调度事件；`heapprofd` 是 Perfetto 的 native 内存分配采样器；PSS 按比例分摊共享页，RSS 则统计进程驻留在内存中的全部页面；WAL 是 SQLite 的 write-ahead log（预写日志）。

| 论文后果类别 | Android 工程里的表现 | Android 17 常用证据 |
|---|---|---|
| Responsiveness | ANR、输入延迟、启动慢、帧延迟 | Play Vitals、ANR trace、Perfetto sched/Binder/FrameTimeline、Macrobenchmark |
| Memory Consumption | OOM、泄漏、频繁 GC、缓存增长 | heap dump、Memory Profiler、heapprofd、PSS/RSS、GC 与 kill 记录 |
| Energy Consumption | 后台 CPU、WakeLock、传感器/定位/网络活跃 | batterystats、Perfetto power/CPU、Job 与 alarm 记录、设备功耗计 |
| Storage Consumption | 数据库、缓存、日志、下载内容增长 | 应用目录分项、SQLite 大小与 WAL、文件 I/O、磁盘统计 |
| CPU Usage | 长时间 Running/Runnable、热点函数、线程竞争 | Perfetto sched、simpleperf、CPU time、线程池队列 |
| GPU Usage | GPU 工作过重、纹理/带宽压力、合成成本 | FrameTimeline、RenderThread、GPU counter（设备支持时）、SurfaceFlinger/HWC |
| Internet Data Usage | 重复下载、失控重试、后台传输 | Network Inspector、TrafficStats、抓包、请求与服务端日志 |

表里的工具是观测入口，不能与论文中的“自动检测工具覆盖率”混为同一指标。Perfetto 能展示调度、帧和 Binder 证据，但不会自动识别全部 82 个因素。

### 版本边界

| 平台范围 | 响应性与帧证据 |
|---|---|
| Android 8—9 | `dumpsys gfxinfo ... framestats`、atrace/systrace、主线程与 RenderThread、ANR trace |
| Android 10—11 | 可使用 Perfetto system trace；FrameTimeline 尚不可用 |
| Android 12—17 | 可采集 FrameTimeline，并结合 sched、Binder、frequency、memory 与自定义 trace |

FrameTimeline 要求 Android 12 及以上。Expected Timeline 表示调度器给帧分配的时间窗；Actual Timeline 从 app 的 `Choreographer#doFrame` 或 native choreographer 回调开始，结束时间取 GPU 完成与 buffer post 中较晚者。它能帮助区分 app 与 SurfaceFlinger 侧 jank（卡顿帧），还要继续查看子 slice（有起止时长的区间事件）、线程状态、flow（跨轨道事件关联）与 `jank_type`（卡顿分类）。

下面的 Trace Processor SQL 用于列出 trace 中的 Actual Timeline 证据。Trace Processor 是 Perfetto 的 SQL 查询引擎：

```sql
SELECT
  process.name AS process_name,
  ts / 1e6 AS ts_ms,
  dur / 1e6 AS dur_ms,
  jank_type,
  present_type,
  on_time_finish,
  layer_name
FROM actual_frame_timeline_slice
LEFT JOIN process USING (upid)
ORDER BY ts
LIMIT 200;
```

查询结果给出帧归属、时长、present 与 jank 分类。它还没有定位 app 内部方法；需要用 token（帧标识）和 flow 对齐 `Choreographer#doFrame`、RenderThread、SurfaceFlinger。Running 表示线程正在 CPU 上执行，Runnable 表示已经可运行但仍在等待 CPU，Sleeping 通常表示正在等待事件；还要同时检查锁等待。

## 六类现实代码模式

论文从 Stack Overflow、GitHub issues 和 commits 的人工编码中归纳出六个宽泛类别。它们是经验分组，不是 Android API 规范，也不是看到一次就能判定为 bug 的静态规则。论文附带的个别代码片段同样要回到对应 Android 版本和运行证据复核。

### 1. API Misuse（API 误用）

论文定义包含调用错误、调用顺序错误和参数错误。Android 工程中还可以把以下候选纳入审查：

- 主线程网络、文件、数据库或重计算；
- 主线程连续同步 Binder 调用；
- 生命周期结束后仍更新旧 UI；
- 对 API 的线程、顺序、资源释放或参数约束理解错误；
- 把异步 API 当作“没有 CPU、锁或磁盘成本”；
- 协程 scope（作用域）与工作生命周期不匹配。

`GlobalScope` 不会自动产生泄漏。它缺少结构化父任务；结构化并发要求子任务的生命周期与取消由父任务管理，而 `GlobalScope` 工作可能长于 Activity/Fragment。闭包若捕获页面、View 或回调，就可能延长引用生命周期。

页面工作通常使用 `lifecycleScope`，跨配置页面状态使用 `viewModelScope`，进程级长期任务需要明确 owner（负责管理任务生命周期的对象）、取消规则和持久化语义。取消 coroutine 也不会自动终止不支持取消的阻塞调用。

#### `requestLayout()` 与 `invalidate()` 不能互换

Android 17 的 `View.requestLayout()` 会清理 measure cache（测量结果缓存），设置 `PFLAG_FORCE_LAYOUT` 与 `PFLAG_INVALIDATED`，并在父节点尚未请求 layout 时向上传递。到 `ViewRootImpl.requestLayout()` 后，根节点设置 `mLayoutRequested` 并调度 traversal（一次 measure、layout、draw 流程）。当前帧是否重测整棵树，仍受父容器、measure spec（父节点给出的尺寸约束）、缓存、可见性和 traversal 状态影响。

`View.invalidate()` 标记绘制内容或区域失效，向父节点传播 damage（需要重绘的区域），必要时也会让 `ViewRootImpl` 调度 traversal。它通常不要求重新计算尺寸，但同一轮 traversal 可能因为其他状态执行 measure、layout、relayout 或 draw。几何尺寸与位置发生变化时用 `requestLayout()`；内容变化且边界不变时用 `invalidate()`；只改 transform、alpha 等渲染属性时还可能走 RenderThread 友好的属性动画路径。

“`requestLayout()` 必然完整 measure + layout + draw”与“`invalidate()` 只执行 draw”都过度简化了 Android 17 的实现。

### 2. Unreleased References（未释放引用）

这一类关注长生命周期 owner 持有短生命周期对象：

- singleton、静态字段或进程级缓存持有 Activity、Fragment、View 或它们的 Context；
- listener、observer、callback、receiver 注册在长生命周期对象上，没有按协议解除；
- Fragment 的 ViewBinding 在 `onDestroyView()` 后仍被 Fragment 字段持有；
- Handler、Runnable、线程、coroutine 或 native callback 捕获已销毁页面；
- 无界缓存、集合或 map 保留旧 key/value。

匿名内部类和 lambda 不会一律捕获整个外部对象，应检查它们实际捕获的字段。注册与注销也应按 API 约定和 owner 生命周期判断，不能机械要求所有 listener 都在 `onDestroy()` 注销。

验证顺序是：观察 retained count（超过预期生命周期仍被保留的对象数）或 heap 增长，获取 heap dump，查看 dominator（释放后可连带释放大量下游对象的支配对象）与到 GC root（垃圾回收器起始引用）的路径，再确认对象已经越过预期生命周期。LeakCanary 适合开发和自动化场景，Memory Profiler 可继续分析 Java/Kotlin heap；native 分配问题再使用 `heapprofd`。单次 heap 大不等于泄漏。

### 3. Redundant Objects（冗余对象）

论文把重复创建等价对象、互相递归创建对象和无意义重复实例化归到这一类。Android 10 及以上的默认 Concurrent Copying（CC）回收器以分代模式运行，会优先回收年轻对象；单次小对象分配不能直接判定为性能问题。高频分配仍可能增加 GC、CPU 和内存压力，影响要通过 allocation trace（分配记录）、GC 频率和帧证据验证。

下面的 View 代码展示可安全复用的绘制状态：

```kotlin
class StatusLineView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {
    private val linePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.RED
        strokeWidth = 2f
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val y = height / 2f
        canvas.drawLine(0f, y, width.toFloat(), y, linePaint)
    }
}
```

`Paint` 与 View 具有相同生命周期，并且只在 UI 线程使用，复用不会引入跨线程状态冲突。对象池不适合当作通用修复：池本身有生命周期、容量、清理和并发成本。优先移除已经证实的热点分配，修改后比较 allocation rate（单位时间的分配量）、GC 与帧指标。

Android Lint 的 `DrawAllocation` 可以发现一部分 draw/layout 内分配；Lint 告警是候选信号，运行时证据决定优先级。

### 4. Large-Scale Data（大规模数据）

论文中的大数据模式包括一次性读取大文件、加载大图、上传大文件和处理超出设备资源的 payload（单次输入数据）。常见修复方向包括流式处理、分页、分块、限流、背压（让上游发送速度服从下游处理能力）、缓存和尺寸约束。

一张 4000 × 3000、每像素 4 byte 的 ARGB_8888 bitmap，像素数据为 48,000,000 byte，约 45.8 MiB（1 MiB = 2²⁰ byte）；实际占用还受 row bytes（每行实际占用字节数）、额外副本、纹理与解码流程影响。不能只按压缩图片文件大小估算内存。

审查大数据路径时记录：

- 输入上限和异常 payload；
- 是否把完整文件或响应读入单个数组/String；
- 解码目标尺寸与原图尺寸；
- 是否在主线程解析、拷贝或解码；
- 临时副本数与峰值内存；
- 取消、超时、重试和部分失败行为；
- 低内存设备与后台状态。

`InputStream.available()` 不是文件总大小，也不适合用来决定“读取完整文件”的 buffer。流式固定大小 buffer 或受控库通常更安全。

### 5. UI Operations（UI 操作）

论文把 draw 循环、重复 UI 工作等归入 UI Operations。Android View 与 Compose 的审查方式不同，但都需要回答“哪些状态变化触发了多少工作”。

View 体系关注：

- 同一帧内重复 `requestLayout()` / `invalidate()`；
- 自定义 View 的 measure、layout、draw 与对象分配；
- RecyclerView 绑定、预取、复用与 payload 更新；
- 图片尺寸、阴影、模糊、clip、离屏渲染；
- 过深或多次测量的布局路径。

不存在通用的“超过 5 层一定慢”或“ConstraintLayout 一定更快”。约束求解、子节点数量、measure spec、权重、嵌套滚动和设备都会改变成本。用 Perfetto 的 `measure`、`layout`、`draw`、FrameTimeline 与 Macrobenchmark 量化。

Compose 关注 state 读取范围、recomposition（状态变化后重新执行受影响的 Composable）、remeasure/redraw、稳定性、Lazy 列表 key、昂贵计算和 snapshot（Compose 状态系统）写入。View 层级规则不能直接套到 Compose。

### 6. Other Patterns（其他模式）

论文举出的其他模式包括一次投递大量 Runnable、主线程访问 `CookieManager` 等。工程中还常见：

- 主线程锁竞争；
- 线程池无界排队或并发过高；
- 反射、序列化或 JNI（Java 与 native 代码之间的接口）往返出现在高频路径；
- 重试没有上限或退避（失败后逐步拉长间隔）；
- 小 Binder 调用在循环中累积；
- 一个 observer、flow 或 callback 同时通知多个下游，造成重复工作。

单次调用快，循环后也可能超预算；单次调用慢，若在后台且不影响目标指标，也可能无需修改。Code Review 负责发现候选，benchmark、trace 和线上指标负责判定影响。

## 现代补充：主线程同步 Binder

主线程同步 Binder 把远端执行时间、服务端排队、锁、I/O 与 CPU 调度传给客户端。Android 官方 ANR 指南把 `slow binder call`（耗时 Binder 调用）和 `many consecutive binder calls`（连续多次 Binder 调用）列为输入分发 ANR 的常见原因。

在经典 kernel Binder 路径中，Android 17 的 `IPCThreadState::talkWithDriver()` 会通过 `BINDER_WRITE_READ` ioctl 与 Binder driver 交换命令。`ioctl` 是用户空间向设备驱动发控制请求的系统调用。Java Manager、ContentProvider 或第三方 SDK 的一行调用，可能跨到 system_server（承载核心 Java 系统服务的进程）、另一个 app、SurfaceFlinger 或 vendor service。

### Perfetto 确认顺序

1. 在 app 主线程定位宽的 `binder transaction` 或等待区间。
2. 沿 Binder flow 到 reply/server 线程；缺少 flow 时用时间、pid/tid（进程 ID/线程 ID）与 transaction 上下文辅助。
3. 检查客户端等待期间的线程状态。Sleeping 可能是在等待 reply；Runnable 表示已经可运行但还在等 CPU；D 状态表示不可中断睡眠，通常需要继续检查 I/O。
4. 检查服务端 Binder 线程是否 Running、Runnable、锁等待、磁盘 I/O，或继续发起下游 Binder。
5. 检查 Binder 线程池是否耗尽，以及同一主线程是否连续发出大量小调用。
6. 对照 ANR trace、Perfetto 时间窗和源码服务入口。

`ioctl(BINDER_WRITE_READ)` 只有在 trace 采集了相关 syscall/ftrace 信息时才会直接显示。Binder transaction slice 与 flow 通常更适合作为入口。

### 修复要按所有权选择

- 调用对首帧或输入不必要：延后、批量或移出主线程；
- 调用必须同步且团队拥有服务端：缩短服务逻辑、减少锁和 I/O；
- 多次查询结果允许短期复用：在明确一致性和失效策略后缓存；
- API 要求主线程：减少调用次数和输入规模，不要强行跨线程；
- 厂商/system_server 高负载：保留系统侧证据，避免把责任写成 app 单函数耗时；
- 第三方 SDK：限制初始化时机、审计 Provider/Manager 调用，并用版本对照验证。

缓存系统查询可能引入权限、包状态或配置过期，异步化也可能改变时序。性能修改要同时通过正确性测试。

## Android 17 cached-app freezer

Cached apps freezer（缓存进程冻结机制）从 Android 11 开始受到平台支持。cached 进程已经离开前台，但系统仍把它保留在内存中，以便后续快速恢复。Android 14 及以上的官方行为说明包括：受支持设备上的 cached 进程通常在进入 cached 状态一段时间后被冻结；生命周期事件会让进程解冻；context-registered broadcast（代码动态注册的广播）可排队到解冻后交付。

Android 17 的资源 `config_defaultFreezerDebounceTimeout` 默认是 10,000 ms；DeviceConfig namespace `activity_manager_native_boot` 下的 key `freeze_debounce_timeout` 可以调整它，厂商资源也会影响行为。DeviceConfig 是平台运行时配置系统；不要把“10 秒”当作所有 Android 17 设备不可变的常量。

进程冻结后，所有线程停止执行，不能做 GC，也不能处理 trim 回调（系统要求进程主动收缩内存的通知）。Android 14 及以上可能在进入 cached 状态后请求预冻结 GC；冻结后还可能执行 compaction（回收或换出进程内存页），包括把匿名页交换到 ZRAM（内存中的压缩交换设备）。系统恢复 Activity 等生命周期时会先解除冻结，后续线程调度、page fault（缺页处理）、GC、消息与业务工作才会继续。

### 冻结进程收到 Binder 的边界

官方 freezer 文档明确说明：客户端向被冻结的 app 进程发出同步 Binder transaction 时，系统会立即终止被冻结的服务端进程，避免客户端无限等待。异步 `oneway` transaction（不等待返回的单向调用）的 buffer 也受到监控，空间耗尽可导致被冻结进程被终止。

因此，不能把“向 frozen 进程发同步 Binder”描述成“系统解冻后处理积压请求”。正常生命周期提升可以触发解冻；错误 IPC 可能走 kill 路径。退出原因可结合 `ApplicationExitInfo.REASON_FREEZER` 和系统日志调查。

### 怎样判断解冻是否参与短时卡顿

Android 17 的 `CachedAppOptimizer.traceAppFreeze()` 在 `system_server` 的 `Freezer` track 记录 `Freeze` / `Unfreeze` instant（瞬时事件），附带进程名、pid 和 reason。分析切回慢或恢复后首个交互时，按同一时间窗查看：

- `Freezer` track 的 Unfreeze；
- app 主线程从停止到 Runnable/Running 的变化；
- page fault、I/O、GC、compaction 与 CPU frequency；
- Binder flow 与 system_server 工作；
- FrameTimeline、首帧与输入事件；
- 进程是否被 kill 后冷启动。

Unfreeze 与慢帧相邻只说明时间相关。只有在调度、page fault、GC、Binder 或业务工作上找到耗时，才能进一步归因。短时 CPU 竞争也要通过 Runnable 时间和同核竞争线程验证。

Framework 结论以 `android-17.0.0_r1` 的 `CachedAppOptimizer.java` 为固定版本依据。cgroup freezer（通过 control group 暂停进程的内核机制）、Binder driver 与调度器结论固定到 `android17-6.18-2026-06_r6`；厂商内核与 AOSP common tag 不一致时，以设备 kernel build（内核构建版本）和对应源码复核。

## 从数据看排查优先级

### 用户面：响应性应有稳定入口

62.3% 的核查后用户评论归到 Responsiveness。团队至少需要覆盖 ANR、启动、帧、输入和明显交互延迟，并将用户动作、版本、机型和时间窗关联到 trace 或线上诊断数据。

### 工程面：内存要覆盖泄漏、峰值和系统回收

Stack Overflow、GitHub issue 与 commit 的主导类别都是 Memory Consumption。只查 Java 泄漏不够，还要区分：

- Java/Kotlin heap retained object（超期保留对象）；
- native heap、graphics、mmap 与共享内存；
- 峰值分配与 OOM；
- PSS/RSS 增长；
- GC 频率与 CPU 影响；
- LMKD（Low Memory Killer Daemon，低内存终止守护进程）kill、后台存活与 cached-app 行为。

### 研究面：能耗工具多，现实因素仍有空白

69/85 篇论文涉及能耗，但 v3 仍报告大面积因素、工具与数据集空白。能耗研究投入高，不代表任何产品都应把能耗排在响应性之前。业务场景、用户影响、发生频率、严重度、可恢复性和证据置信度共同决定顺序。

### 更合适的使用方式

把论文用于“覆盖审计”：

1. 用自家线上数据形成问题排序；
2. 将问题映射到七类后果；
3. 检查是否持续忽略用户可感知类别；
4. 对工具未覆盖因素安排 Code Review、实验和专项 trace；
5. 修复后用原指标与同场景基线验证。

论文比例不能直接变成团队人力比例或发布门禁阈值。

## Code Review 性能检查清单

清单按“静态线索 → 运行证据”使用。命中线索时记录场景和验证方法，不要仅凭模式要求改代码。

| 审查问题 | 静态线索 | 运行时确认 |
|---|---|---|
| 主线程是否做阻塞工作 | 文件、网络、数据库、锁、同步等待 | StrictMode、ANR trace、Perfetto thread state/I/O |
| 是否连续同步 Binder | Manager/Provider 调用位于循环或启动关键路径 | Binder flow、服务端线程、调用次数与累计时间 |
| 异步工作的 owner 是否明确 | `GlobalScope`、裸 Thread、无取消 callback | 页面销毁后任务与引用、重复回调、线程队列 |
| 是否保留短生命周期对象 | singleton/static/cache/listener 捕获页面 | heap dominator、GC root、retained count |
| 高频路径是否重复分配 | draw/layout/bind/loop 内建大对象 | allocation trace、GC、CPU 与帧对照 |
| 大数据是否一次性进入内存 | `readBytes`、完整 JSON、原尺寸 bitmap、大数组 | 峰值 heap/RSS、I/O、解码和 OOM 设备 |
| UI 变化是否触发过量工作 | 高频 `requestLayout`、全量刷新、昂贵 draw | measure/layout/draw、FrameTimeline、Macrobenchmark |
| 数据库路径是否随数据量恶化 | 无界查询、N+1（主查询后逐行追加查询）、缺索引、大事务 | query plan（查询执行计划）、真实规模 benchmark、磁盘与锁 |
| 偏好设置是否阻塞生命周期 | 主线程读写、密集 `apply()`、同步 `commit()` | StrictMode、lifecycle pause、磁盘 trace |
| 后台资源是否按生命周期释放 | WakeLock、sensor、location、socket、Job | batterystats、后台 trace、超时与退出路径 |
| 重试和同步是否放大网络/CPU | 无上限重试、短周期轮询、重复下载 | 请求日志、TrafficStats、CPU/energy 时间窗 |
| freezer 是否改变恢复路径 | cached 多进程 IPC、恢复时大量工作 | Freezer track、exit reason、Unfreeze 后线程证据 |

### SharedPreferences 不能只检查 `apply()` 与 `commit()`

`commit()` 同步写盘，不应在主线程执行。`apply()` 立即更新进程内数据并异步写盘，但 Framework 会在组件生命周期切换时等待未完成写入；密集 `apply()` 仍可能引发主线程阻塞和 ANR。官方当前文档不建议新存储需求继续采用 SharedPreferences。

审查时还要看读取是否触发磁盘、写入频率、durability（崩溃或重启后数据是否仍可靠保存）、一致性、多进程需求和迁移方案。将 `commit()` 机械替换成 `apply()` 只能消除调用点的同步写盘，不能解决所有生命周期 I/O。

## 实践步骤

这套方法可以落实为三项动作：

- 引用研究数字时同时写分子、分母、revision 和样本来源；
- 把性能后果、促成因素、代码模式与观测证据分层；
- 将静态审查结果送入可复现的 benchmark、trace 或线上指标验证。

遇到一条用户“卡”的反馈，可以从 Responsiveness 进入，再判断它对应帧延迟、输入等待、启动、Binder、I/O、锁、调度还是 freezer 恢复。遇到内存修复提交，可以区分 retained reference（超期保留引用）、高频分配与回收、峰值数据、native/graphics 占用和系统回收。遇到研究工具没有规则覆盖的因素，则补充场景化测试与运行时观测。

研究样本跨多个 Android 版本。Android 17 相关机制以 `android-17.0.0_r1` 为固定平台版本；涉及 Binder driver、cgroup freezer 和调度器时，以 `android17-6.18-2026-06_r6` 为固定内核版本。旧版本演进可以保留，不把当前结论外推到 Android 17 之后。

## 参考资料

- [Liao et al., *A Comparative Study of Android Performance Issues in Real-world Applications and Literature*, arXiv:2407.05090v3](https://arxiv.org/pdf/2407.05090v3)
- [论文复现资料：Android-Performance-Analysis](https://github.com/Dianshu-Liao/Android-Performance-Analysis)
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [Android 官方：Diagnose and fix ANRs](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs)
- [Android 官方：Performance measurement examples](https://developer.android.com/topic/performance/performance-measurement-examples)
- [Android 官方：Memory management overview](https://developer.android.com/topic/performance/memory-overview)
- [Android 官方：SharedPreferences](https://developer.android.com/reference/android/content/SharedPreferences)
- [AOSP cached apps freezer](https://source.android.com/docs/core/perf/cached-apps-freezer)
- [Android 17 `View.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/View.java)
- [Android 17 `ViewRootImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)
- [Android 17 `IPCThreadState.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/IPCThreadState.cpp)
- [Android 17 `CachedAppOptimizer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java)
- [Android common kernel `android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6)
- 相关章节：§7.10（View 体系性能优化）、§9.1（ANR 设计思想）、§10.1（App 内存分析）、§14.7（`dumpsys gfxinfo`）、§15.3（性能指标体系）
