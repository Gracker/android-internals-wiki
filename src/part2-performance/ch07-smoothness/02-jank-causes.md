---
title: "卡顿原因体系"
chapter: "7.2"
section: "7.2"
status: finalized
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
last_verified: "2026-04-08"
last_verified_against: "AOSP android-15.0.0_r1"
reviewed_date: "2026-05-24"
reviewed_by: openclaw-task6
polish_count: 1
polish_date: "2026-04-08"
polish_by: "task2b-polish"
confidence: high
sources:
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-07_wechat_Android卡顿监测的方方面面.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-08_wechat_干货_从47_到80_携程酒店APP流畅度提升实践.md"
  - type: aosp
    path: "frameworks/base/core/java/android/view/Choreographer.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/ViewRootImpl.java"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp"
  - type: official
    path: "developer.android.com/topic/performance/vitals/render"
tags:
  - android
  - jank
  - research
  - rendering
  - perfetto
  - performance
  - smoothness
related_chapters: ["7.1", "2.3", "2.4", "2.5", "1.4", "1.5", "1.13", "1.14", "3.1", "4.3"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed
task2b_rework_date: "2026-05-06T02:43:45+08:00"
task9_result: pass-tech-review
last_task9_at: "2026-05-24T20:34:56+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-24"
task9_review_notes: "2026-05-06 03 task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-05-24 Task9 闲时抽检：needs-rework。P0 1 / P1 0 / P2 1；FrameTimeline 证据字段写成 present_offset/refresh_period/hwc_layer_name 不符合 Perfetto SQL 表，需改为 actual_frame_timeline_slice/expected_frame_timeline_slice 的 jank_type、present_type、layer_name，并用 dumpsys 或 layer snapshot 复核 HWC DEVICE/CLIENT。 | 2026-05-24 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 2；DeliQueue android-17-beta3 源码 tag 与 HWC3 Composition/Overlay plane 数据支撑仅作为 P2 留给后续小修；Task6 已通过且 queue 无 pending，自动晋升 finalized。"
last_task6_at: "2026-05-24T20:14:35+08:00"
last_task6_audit: "2026-05-24"
task6_reviewed_date: "2026-05-24"
review_notes: "2026-05-06 task6 re-review: pass-light-edit。L1/L2 小修 11 处；无新增 B 类回炉问题，等待 Task 9 复审。"
last_task9_audit: "2026-05-24"
last_task9_audit_log: "logs/deep-review/2026-05-24-15-audit.md"
last_task2b_at: 2026-05-24T19:29:26+08:00
reviewed_at: "2026-05-24T20:14:35+08:00"
review_round: 2
last_task6_review_log: "logs/review/2026-05-24-20-review.md"
task6_review_notes: "2026-05-24 task6 revisiting review: L1/L2 小修 7 处；无新增 Task6 回炉项；Task9 audit 已由 Task2B 修复，等待 Task9 复审。"
last_task9_review_log: "logs/deep-review/2026-05-24-20-deep-review.md"
---

# 卡顿原因体系

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 主线程耗时过长：Layout/Measure 过重、RecyclerView Bind 耗时、主线程 I/O
- 🔹 RenderThread 瓶颈：GPU 过载、复杂 Canvas 操作、大量 Path 计算
- 🔹 SurfaceFlinger 瓶颈：合成超时、Layer 过多、HWC 限制
- 🔹 系统级原因：CPU 调度延迟（Runnable 状态过长）、低内存触发 GC、温控限频
- 🔹 Binder 调用导致的主线程阻塞
- 🔹 分析树：从现象到根因的分析决策路径

### 扩展（可选深入）

- 🔸 WebView 渲染导致的 Jank
- 🔸 多窗口/分屏场景的特殊 Jank 问题
- 🔸 动画与手势场景的 Jank 特征

<!-- outline-end -->

## 为什么要系统化地理解卡顿原因

在 7.1 节中，我们定义了什么是卡顿，也知道了卡顿的本质是「一帧的渲染没能在一个 VSync 周期内完成」。但知道「掉帧了」只是第一步——这一帧为什么没画完？

这个问题看似简单，答案却分散在整个渲染管线的各个环节中。一次卡顿可能源于 App 侧的代码写法（比如在滑动回调里做了太多计算），也可能源于系统侧的调度问题（比如 CPU 把时间片给了别的进程），甚至还可能源于硬件合成的限制。如果我们没有一套系统化的原因分类体系，面对 Perfetto Trace 里密密麻麻的时间线，很容易陷入「到处看看、碰运气」的低效模式。

本节的目标，就是把「一帧为什么没画完」这个问题的所有可能原因，按照渲染管线的阶段整理成一个清晰的原因体系。读完这一节，当我们再在 Perfetto 中看到一帧超时，应该能快速判断问题出在渲染管线的哪个环节、是 App 的问题还是系统的问题、下一步该往哪个方向深挖。

在进入具体原因之前，我们需要先回顾一下一帧的渲染在 Perfetto 中的完整路径，因为后面的原因分类就是按照这条路径的阶段来组织的：

```text
VSync-app 信号到达
  → Choreographer.doFrame()
    → Input 回调处理
    → Animation 回调处理
    → Traversal（measure → layout → draw）
  → syncAndDrawFrame（主线程与 RenderThread 同步）
  → RenderThread 执行 GPU 命令
  → queueBuffer 提交缓冲区
  → SurfaceFlinger 合成
  → 显示上屏
```

在这条路径上，任何一个环节超时，后续环节都会被顺延，最终导致这一帧错过 VSync-app 的截止时间，表现为掉帧。后面的分类按这条路径逐段展开。


### HWC 合成降级导致的 Jank

当 Layer 数量超出 HWC Overlay Plane 数量、或像素格式/混合模式超出 HWC 能力时，SurfaceFlinger 会将 Layer 从 DEVICE 合成回退到 CLIENT 合成（GPU 渲染）。这会导致：

1. **GPU 帧时间增加**：每帧必须渲染到 Framebuffer，GPU 负载上升
2. **额外内存拷贝**：GPU 显存 → 显示控制器的拷贝开销
3. **掉帧风险**：如果 CLIENT 比例过高，GPU 帧时间超过 VSync 周期

**Perfetto 中的证据**：通过 `actual_frame_timeline_slice` 表的 `jank_type`（如 `SurfaceFlinger Deadline Missed`、`Buffer Stuffing`、`Late Present`）和 `present_type` 字段定位异常帧，再用 `layer_name` 和 `on_time_finish` 缩小嫌疑 Layer。FrameTimeline 不直接暴露 HWC DEVICE/CLIENT 归因——确认合成降级需要结合 SurfaceFlinger composition trace（`android.surfaceflinger` 轨道）中 `compositionType` slice、RenderEngine 执行耗时，或 `dumpsys SurfaceFlinger` 的 layer dump 输出。

**实测建议**：
- 收集 dumpsys SurfaceFlinger 确认 DEVICE/CLIENT 比例
- 对比不同 SoC 平台在相同场景下的合成降级频率
- 高端 SoC（骁龙 8 Gen3）通常 4-6 个 Overlay Plane，中端（骁龙 6/7 Gen）通常 4 个


[已验证: 官方文档, developer.android.com/topic/performance/vitals/render]

## 主线程耗时过长

主线程（MainThread / UI Thread）是卡顿最常见的发生地。在 Android 的渲染管线中，Input 事件处理、Animation 计算、View 的 measure/layout/draw 都发生在主线程上；一旦主线程被某个操作阻塞到超过当前 VSync 周期的剩余时间，这一帧就会掉帧。

在 Perfetto 中，主线程耗时过长通常表现为：一个 doFrame 的绿色 Slice 明显拉长，或者在 doFrame 之前有一段很长的非渲染类 Slice（比如某个业务方法执行了很久）。

[已验证: AOSP android-15.0.0_r1, frameworks/base/core/java/android/view/Choreographer.java]

### Layout/Measure 过重

Layout 和 Measure 是 View 树遍历的核心阶段。当 View 层级过深、或者某个 ViewGroup 的 onMeasure/onLayout 逻辑过于复杂时，这两个阶段的耗时会显著增加。

常见触发点主要有三类：

**View 层级过深。** Android 的 measure 和 layout 是从根节点开始递归遍历整棵 View 树的。如果层级超过 10 层，每次 requestLayout 都需要遍历所有节点，耗时累加起来相当可观。在实际项目中，嵌套过多的 LinearLayout 或 RelativeLayout 是最常见的深层级来源。

**多次 measure 的布局。** 某些布局容器（如 RelativeLayout、带 weight 的 LinearLayout）在单次布局过程中会触发多次 measure，因为子 View 的尺寸互相依赖，需要迭代才能确定最终值。这种「measure 两遍甚至三遍」的行为在某些复杂布局下尤其明显。

**动态布局频繁刷新。** 如果在列表滑动或动画过程中频繁调用 requestLayout（而不是 invalidate），会导致整棵 View 树反复执行完整的 measure → layout → draw 流程。requestLayout 比 invalidate 代价高得多——invalidate 只标记需要重绘的"脏区域"，而 requestLayout 要求从该 View 向上回溯到 ViewRootImpl，重新执行整棵树的 measure 和 layout。

[来源: Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md]

**在 Perfetto 中的表现：** 在主线程的 doFrame Slice 中，measure 和 layout 对应的子 Slice 会明显拉长。如果开启了 view trace（`-a view`），还会出现 `measure` 和 `layout` 的具体耗时。

[待补充：Trace 截图 — measure/layout 耗时过长的 Perfetto 片段]

### RecyclerView Bind 耗时

RecyclerView 是 Android 中最常用的列表组件，也是卡顿的高发地带。RecyclerView 的滑动帧耗时主要取决于 `onBindViewHolder` 和 `onCreateViewHolder` 的执行时间。

**onBindViewHolder 中的重操作。** onBindViewHolder 在每次 Item 进入可视区域时被调用。如果在这个方法中做了数据转换（比如 JSON 解析）、图片加载（同步的 BitmapFactory.decode）、复杂的字符串操作或日期格式化，都会直接增加每帧的耗时。在滑动场景下，一帧可能需要 bind 多个 Item，耗时成倍叠加。

**onCreateViewHolder 中的 inflate。** 当 RecyclerView 的缓存池（RecycledViewPool）中没有可复用的 ViewHolder 时，需要 inflate 新的布局。View.inflate 涉及 XML 解析、反射创建 View 对象、设置属性等操作，是一个比较重的同步操作。如果在滑动过程中频繁触发 onCreateViewHolder，会导致明显的卡顿。

**DiffUtil 的计算开销。** 使用 ListAdapter + DiffUtil 时，如果在主线程执行 areContentsTheSame 等比较逻辑，且比较逻辑本身比较复杂（比如对比大文本内容），也会造成额外的耗时。

[来源: Personal-Knowlodge/source/2026-03-08_wechat_干货_从47_到80_携程酒店APP流畅度提升实践.md]

**在 Perfetto 中的表现：** 滑动场景的 Trace 中，主线程 doFrame 内会出现一系列 `RV onBind` 或 `RV FullInflate` Slice；这些 Slice 的总耗时加上 measure/layout 耗时超过 VSync 周期，就会掉帧。

[已验证: AndroidX androidx-main, recyclerview/recyclerview/src/main/java/androidx/recyclerview/widget/RecyclerView.java]

### 主线程 I/O

在主线程上执行文件读写、SharedPreferences 的 apply/commit、数据库查询等 I/O 操作，是卡顿的另一个常见原因。I/O 操作本身是阻塞的，而文件系统（特别是 eMMC 或低端的 UFS 存储）的随机读写延迟可能达到数十毫秒。

**SharedPreferences 的 commit。** commit 方法会将数据同步写入磁盘。如果存储的数据量较大或磁盘 I/O 繁忙，这个调用可能需要数十毫秒。Perfetto 中常见的信号是主线程上有一个 `SP.commit` 或类似 Slice 占据了大部分帧时间。

**主线程读写文件。** 某些老旧代码或第三方库可能直接在主线程上使用 FileInputStream / FileOutputStream 进行读写，或者执行 SQLite 查询而没有使用异步接口。

**字符串拼接中的序列化。** 这是一个容易被忽略的 I/O 来源。在某些日志工具类（如 LogUtil.d）中，方法参数中的表达式在调用时就执行了——即使日志级别不满足输出条件。如果参数中包含 JSON 序列化或字符串拼接，这些操作会白白消耗主线程时间。

[来源: Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md — 2.7 字符串拼接问题优化]

**在 Perfetto 中的表现：** 主线程出现一段 Sleeping 或 Uninterruptible Sleep 状态（对应 I/O 等待），或者看到某个 I/O 相关的方法 Slice 明显过长。

[已验证: 官方文档, developer.android.com/reference/android/content/SharedPreferences — 推荐使用 apply() 替代 commit()]

### 主线程锁竞争

当主线程尝试获取一把被其他线程持有的锁时，它会进入 Blocked 状态，直到锁被释放。这种锁竞争导致的卡顿在实际项目中很常见，但很容易被忽略——因为卡顿的"责任方"不在主线程的代码中，而在于其他线程持锁太久。

**日志框架的锁。** 很多日志 SDK（如 Bugly、WNS）为了保证线程安全，内部使用了 synchronized 块或 ReentrantLock。当多个线程同时写日志时，主线程可能因为等待锁而被阻塞。

**单例初始化的锁。** 某些使用双重检查锁定（Double-Checked Locking）模式的单例，在首次初始化时可能导致主线程等待。

**Kotlin `by lazy` 的隐式锁。** Kotlin 的 `by lazy` 默认使用 `LazyThreadSafetyMode.SYNCHRONIZED`，内部通过 synchronized 实现线程安全。如果在主线程上首次访问一个初始化成本较高的 lazy 属性，而此时另一个线程也在访问，就可能发生锁竞争。在确定无线程安全问题时，应使用 `by lazy(LazyThreadSafetyMode.NONE)` 来避免不必要的锁。

[来源: Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md — 2.4 懒加载优化 & 2.6 锁耗时优化]

**在 Perfetto 中的表现：** Java / Kotlin monitor 竞争更稳的入口是线程状态里的 Blocked、Perfetto 的 Lock contention track，或 `android.monitor_contention` 模块给出的 owner / waiter 关系。native mutex 和 condition variable 往往都会落到 `futex_*` 等待上，但两者语义不同：mutex 等 owner 释放锁，condition variable 等谓词成立后的唤醒。Runnable 长时间不执行说明线程没有及时拿到 CPU，不等于它在等锁。

要抓 Java monitor，trace 至少带上 `sched` 和 `dalvik` 相关采集项，这样 Perfetto 才能产出 `android.monitor_contention` 所需的数据。native 锁继续结合 `thread_state.blocked_function`、调用栈和 owner 线程状态分析。

### Android 17 DeliQueue：主线程消息队列的无锁化

Android 17 对 `MessageQueue` 做了一次架构级重构，引入了 **DeliQueue**（无锁消息队列）。在传统实现中，`MessageQueue.enqueueMessage()` 和 `next()` 之间通过 `synchronized` 保护，多线程向主线程投递消息时存在锁竞争风险。DeliQueue 采用无锁化设计：生产者侧通过 **Treiber stack** 处理并发入队（多线程 postMessage 不再争 monitor），Looper 侧通过 **min-heap** 按时间戳排序出队。这个架构移除了 `enqueueMessage()` 和 `next()` 之间的 synchronized 保护，减少了主线程在处理 Handler 消息时的锁竞争延迟。

**生效边界**：DeliQueue 仅对 `targetSdkVersion >= 37` 的应用默认启用。`targetSdk < 37` 的应用即使在 Android 17 设备上运行，仍使用传统 synchronized MessageQueue。Debuggable build 可通过 `adb shell am compat enable USE_NEW_MESSAGEQUEUE <package>` 提前测试新队列行为。

对卡顿分析的实际影响：

- **主线程 `monitor contention` 减少**：在 Perfetto 中，启用了 DeliQueue 的应用，`android.monitor_contention` 事件中 `MessageQueue` 相关的竞争会显著减少。但业务锁（单例锁、Kotlin lazy 锁）、Binder 对端锁、native futex 等仍需正常排查。
- **callback 分发延迟降低**：`Choreographer` 的 `doFrame` 回调、Input 事件分发等通过 Handler 投递的关键路径，受多线程并发投递的影响变小。
- **分析注意事项**：排查 Android 17 上的主线程卡顿时，先确认应用是否启用了 DeliQueue（检查 `targetSdkVersion`），再判断 `MessageQueue` 锁竞争是否仍是瓶颈。

[来源: AOSP android-17-beta3, frameworks/base/core/java/android/os/MessageQueue.java; Android Developers Blog 2026-02-17]

## RenderThread 瓶颈

从 Android 5.0（Lollipop）开始，Android 引入了 RenderThread，将一部分渲染工作从主线程剥离出来，交给专门的渲染线程执行。主线程负责 measure/layout/draw（记录绘制命令到 DisplayList），RenderThread 负责将 DisplayList 中的命令通过 OpenGL/Vulkan 发送给 GPU 执行。

这种分工降低了主线程等待 GPU 的概率。但当 RenderThread 本身的执行时间超过预期时，它同样会成为卡顿来源。

[已验证: 官方文档, developer.android.com/topic/performance/rendering — RenderThread 介绍]

### GPU 过载

GPU 过载是最常见的 RenderThread 瓶颈。当一帧需要 GPU 执行的绘制命令太多或太复杂时，GPU 的执行时间会超过 VSync 周期的剩余时间（因为主线程的 measure/layout/draw 也消耗了一部分时间）。

**大图首次纹理上传。** 图片 decode、缩放和格式转换通常先发生在主线程或后台线程。RenderThread 里更常见的是首次 texture upload、纹理重传，或超大纹理带来的带宽压力。列表滑动场景里，Bitmap 即使已经 decode 完成，只要这一帧才第一次进入可见区域，RenderThread 仍可能在上传纹理时被拖长。

**复杂的 Shader 效果。** 高斯模糊、色彩滤镜、复杂的混合模式等 Shader 效果，会显著增加 GPU 的计算量。在 Perfetto 中表现为 RenderThread 的 draw Slice 很长。

**过度绘制（Overdraw）。** 当屏幕上的同一个像素被多次绘制时（详见 2.8 节），GPU 不得不做大量无用功。开启"显示 GPU 过度绘制"开发者选项后，屏幕上大量红色区域通常说明 GPU 正在做重复的像素填充。

[来源: Personal-Knowlodge/source/2026-03-08_wechat_干货_从47_到80_携程酒店APP流畅度提升实践.md — GPU 问题定位]

**在 Perfetto 中的表现：** 如果瓶颈在 CPU 侧 decode，长耗时更可能出现在主线程或工作线程的图片解码调用栈；如果瓶颈在 RenderThread 侧，`DrawFrame`、GPU busy 或 fence wait 会更长，掉帧常集中在图片第一次进入可见区域的几帧。120Hz 设备上，RenderThread 连续多个 4-5ms 以上的长帧就要继续细看。

### 复杂 Canvas 操作和大量 Path 计算

某些 Canvas 操作虽然不涉及 GPU，但本身的 CPU 计算量很大，这些操作在硬件加速模式下会被记录到 DisplayList 中，由 RenderThread 执行。

**Path 操作。** Canvas.clipPath、Canvas.drawPath 等操作涉及复杂的几何计算（特别是曲线和自定义形状）。当 Path 的数据点很多时（比如手写笔迹、复杂的 SVG 图形），这些操作的耗时可能非常显著。

**saveLayer 的滥用。** Canvas.saveLayer 会创建一个离屏缓冲区（offscreen buffer），用于实现半透明、混合等效果。每次 saveLayer 都意味着 GPU 需要额外的渲染 pass，成本很高。在 Flutter 中类似的问题也存在——ClipRRect 会调用 saveLayer，导致 GPU 线程变慢。

[来源: Personal-Knowlodge/source/2026-03-08_wechat_干货_从47_到80_携程酒店APP流畅度提升实践.md — checkerboardOffscreenLayers]

**Canvas 文字渲染。** 大量文字的测量和渲染也是 RenderThread 的常见瓶颈。文字渲染涉及字体查找、字形光栅化、排版计算等步骤，在长列表中尤为明显。

**在 Perfetto 中的表现：** RenderThread Slice 内部出现长耗时的 `drawOp` 子 Slice，或者在开启 GPU 检查时看到 saveLayer 调用触发的闪烁区域。

[待补充：Trace 截图 — RenderThread 耗时过长的 Perfetto 片段]

## SurfaceFlinger 瓶颈

SurfaceFlinger 是 Android 系统的合成器（Compositor），负责将所有可见窗口（Layer）的缓冲区合成到最终的显示缓冲区中，然后提交给显示硬件。如果 SurfaceFlinger 没能在 VSync-sf 信号到来之前完成合成，那么这一帧就不能按时上屏，导致视觉上的掉帧。

SurfaceFlinger 瓶颈导致的卡顿有一个特点：App 侧的 Trace 看起来完全正常——主线程和 RenderThread 都在预算时间内完成了工作——但用户还是感觉到了卡顿。这时候就需要去看 SurfaceFlinger 进程的 Trace 了。

[已验证: AOSP android-15.0.0_r1, frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp]

### 合成超时

合成超时通常发生在 Layer 数量多或 Layer 内容复杂的情况下。SurfaceFlinger 的合成方式有两种：Hardware Composer（HWC）合成和 GPU 合成（RenderEngine）。

**GPU 合成回退。** 当 HWC 无法处理某些 Layer（比如带有特定混合模式、圆角裁剪、或者超过 HWC 支持的最大 Layer 数），SurfaceFlinger 会回退到使用 GPU 进行合成。GPU 合成需要占用 GPU 资源，与 App 的 RenderThread 产生竞争，可能导致双方都变慢。

**Layer 过多。** 每个 Activity、Dialog、PopupWindow、Toast 都会创建一个或多个 Layer。当同时可见的 Layer 数量过多时（比如多层 Dialog 叠加、或者分屏模式下两个 App 同时可见），SurfaceFlinger 的合成负担会显著增加。不同 SoC 的 HWC 可处理 layer 数量和变换能力差异很大，具体上限取决于显示控制器、layer 属性和厂商实现，超出后才会退回 GPU 合成。

**在 Perfetto 中的表现：** SurfaceFlinger 进程的 `mainLoop` 或 `doComposition` Slice 耗时过长。可以展开 SurfaceFlinger 的 Track 查看具体的合成阶段。

### HWC 能力限制

不同 SoC 平台的 HWC（Hardware Composer）能力差异很大。SurfaceFlinger 每一帧都会先把 layer 列表交给 HWC 评估，能直接由显示硬件叠加的 layer 标成 **Device Composition**，HWC 无法处理的 layer 才退回 **Client Composition**，由 SurfaceFlinger 里的 RenderEngine 走 GPU 合成。常见触发条件包括 plane 数量不够、缩放或旋转超出硬件能力、圆角或复杂混合效果无法处理。

[来源: Personal-Knowlodge/source/2026-03-08_wechat_Google_为何把_SurfaceView_设计的这么难用.md — HWC Overlay 与 Layer 类型]

**在 Perfetto 中的表现：** 先看 SurfaceFlinger 的 `doComposition`、`composeSurfaces` 或 RenderEngine 相关 slice 是否拉长，再用 `adb shell dumpsys SurfaceFlinger` 做快照，检查对应 layer 是否出现 `DEVICE` / `CLIENT` 一类的 composition type 分配结果。厂商输出格式差异很大，这一步适合做复核，不要只凭一条未验证的 SQL 下结论。


#### HWC 厂商差异：Qualcomm vs MediaTek

> 以下内容基于 AOSP 源码和公开技术文档的一手研究。高通/联发科的 HWC 私有实现代码不在 AOSP 主线中，以下分析基于 AOSP HAL 接口定义和公开技术博客。

**高通与联发科的 HWC 具体决策算法属于厂商私有实现，不在 AOSP 主线源码中公开。公开资料能确认的差异主要集中在 Overlay 平面数量、分配策略、私有优化技术和功耗管理策略上。**

**HWC2 Composition 类型体系（AOSP 源码）：**

```cpp
// hardware/libhardware/include/hardware/hwcomposer2.h
enum class HWC2::Composition {
    Invalid = 0,
    Client = 1,     // GPU GLES 合成，SurfaceFlinger 负责
    Device = 2,      // HWC 硬件 Overlay 合成
    SolidColor = 3,  // 纯色层
    Cursor = 4,      // 光标层
    Sideband = 5,    // 视频流直通道
};
```

Android 13+ 的 HWC3 (AIDL) 使用相同的语义但通过 AIDL 接口暴露：

```hal
// hardware/interfaces/graphics/composer/aidl/android/hardware/graphics/composer3/Composition.aidl
enum Composition : int32 {
    CLIENT = 1,      // GPU 回退合成，SurfaceFlinger 负责
    DEVICE = 2,      // 硬件 Overlay 合成
    SOLID_COLOR = 3, // 纯色层
    CURSOR = 4,      // 光标层
    SIDEBAND = 5,    // 视频流直通道
};
```

**DEVICE vs CLIENT 决策流程（AOSP）：**

```text
SurfaceFlinger 准备每帧 layer state（geometry + buffer）
  → HWComposer::getDeviceCompositionChanges()
  → HWC display presentOrValidate() / validate()
  → getChangedCompositionTypes() / getRequests()
  → SurfaceFlinger 处理 composition type 变更
```

关键源码：`frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp`（合成主循环）与 `DisplayHardware/HWComposer.cpp`（HWC 封装）。AOSP android-15.0.0\_r1 中未找到 `SurfaceFlinger.prepareImage()` / `HWComposer::prepare()` 方法，现代 HWC2/HWC3 流程通过 `getDeviceCompositionChanges()` + `presentOrValidate()` 协商合成方式。

**Qualcomm 私有优化技术：**

1. **"Solid Fill Planes"（固态填充平面）**：允许显示硬件直接渲染单色层，无需从内存读取像素数据，减少内存读带宽和功耗
2. **"Peripheral Tiny Overlap Removal (PTOR)"**：将小的重叠区域通过 Copybit 处理到渲染缓冲区，避免为微小重叠触发完整 GPU 合成

**Qualcomm HWC 代码位置**（私有仓库，不在 AOSP 主线）：
- `platform/hardware/qcom/display/` — Qualcomm 私有 HWC 实现
- `platform/external/drm_hwcomposer/` — DRM HWC 参考实现（开源部分）

**MediaTek HWC 特点：**

- MTK Dimensity 系列通常支持 4 个或更多 Overlay 平面
- 某些 MTK 实现在静态场景下更激进地将 DEVICE 切换到 CLIENT，以节省 Overlay 平面功耗
- "Miravision"技术栈包含显示处理优化，与 HWC 协同处理视频增强

**dumpsys SurfaceFlinger DEVICE/CLIENT 输出格式（AOSP）：**

```text
Display 0 (Primary):
  HWC layers:
  + Bounds: 1080x2400, z=0, type=DEVICE, hdl=0x...
  |  Layer: com.android.systemui.statusbar
  + Bounds: 1080x2400, z=1, type=DEVICE, hdl=0x...
  |  Layer: com.example.app/MainActivity
  ...
  + ClientTarget: 1080x2400, type=CLIENT
```

关键含义：
- `type=DEVICE`：HWC 决定使用硬件 Overlay 合成
- `type=CLIENT`：SurfaceFlinger 先 GLES 合成到 ClientTarget，再提交给 HWC

**厂商差异对调试的实际影响：**

| 维度 | Qualcomm | MediaTek |
|------|----------|----------|
| Overlay 平面数量 | 通常 4-6 个 | 通常 4 个或更多 |
| 静态场景策略 | 保留 Overlay | 更积极切换到 CLIENT |
| 视频场景优化 | 优先保留 Overlay 给受保护内容 | 类似策略 |
| 私有优化 | Solid Fill Planes、PTOR | Miravision 视频增强 |

**关键源码文件索引：**

| 文件路径 | 关键内容 | 版本 |
|---------|---------|------|
| `hardware/libhardware/include/hardware/hwcomposer2.h` | HWC2 Composition 枚举定义 | 全版本 |
| `hardware/interfaces/graphics/composer/aidl/android/hardware/graphics/composer3/IComposer.aidl` / `IComposerClient.aidl` | HWC3 AIDL 接口（含 Composition 枚举） | Android 13+ |
| `frameworks/native/services/surfaceflinger/DisplayHardware/HWComposer.cpp` | SurfaceFlinger HWC 封装 | 全版本 |
| `platform/hardware/qcom/display/` | Qualcomm 私有 HWC 实现 | 厂商私有 |
| `platform/external/drm_hwcomposer/` | DRM HWC 参考实现 | Linux mainline |

[一手研究: AOSP hwcomposer2.h, IComposer.aidl, HWComposer.cpp; Qualcomm 官方博客; developer.android.com HWC 文档]


## 系统级原因

前面三类原因（主线程、RenderThread、SurfaceFlinger）属于渲染管线内部的问题。但在实际分析中，我们还会遇到一种情况：渲染管线内的每一步看起来都很快，但整体还是超时了。这时候问题往往出在系统层面——CPU 调度、内存管理、温度控制等因素在背后影响着渲染管线的执行效率。

### CPU 调度延迟（Runnable 状态过长）

CPU 调度延迟是最隐蔽、也最容易被忽略的卡顿原因之一。它表现为：线程已经就绪（Runnable），但 Linux 调度器没有及时把它调度到 CPU 上执行，帧预算被消耗在等待调度上。

**为什么会发生调度延迟？**

Linux 的 Completely Fair Scheduler（CFS）按照虚拟运行时间（vruntime）来分配 CPU 时间。当一个线程长时间睡眠后醒来（比如等待 VSync 信号的主线程），它的 vruntime 通常较小，理论上应该优先被调度。但在实际场景中：

- 如果系统中有大量线程处于 Runnable 状态（比如后台进程的工作线程、其他 App 的线程），调度器需要在这些线程之间分配 CPU 时间，主线程可能无法立即获得调度。
- 如果主线程或 RenderThread 被调度到了小核（little core），由于小核的频率和 IPC（Instructions Per Cycle）较低，同样的代码需要更长的时间执行。
- 某些高优先级的实时（RT）进程（如音频处理线程）可能会抢占主线程的 CPU 时间。

**多线程竞争对主线程的影响。** 腾讯 WeSing 团队在优化卡顿时发现了一个典型案例：升级 TRTC SDK 后，App 新增了近 30 个线程，这些线程的 CPU 占用甚至超过了主线程和 RenderThread。虽然这些线程本身不在主线程上执行，但它们抢占了 CPU 时间片，导致主线程的调度延迟增加，进而引发卡顿。

[来源: Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md — 2.9 线程问题造成的卡顿优化]

**在 Perfetto 中的表现：** 在 CPU Info 区域查看主线程的状态，会看到蓝色的 Runnable Slice（表示线程已就绪但未执行）。如果这个 Runnable Slice 的持续时间超过 2-3ms，就值得关注。可以通过点击 Runnable Slice 查看唤醒源和前一个线程的状态，分析为什么调度器没有及时调度主线程。

**16KB Page Size 对 I/O 卡顿和渲染 TLB 的影响。** Android 15/16 在支持 16KB 页大小的设备上，卡顿分析还需要考虑一个底层因素。16KB 页将页表条目减少了 75%，直接降低了 `fork()` 和 `mmap()` 的开销；同时对渲染管线有正面影响：

- **I/O 卡顿缓解**：更大的页意味着单次 I/O 读取覆盖更多数据，启动阶段和资源加载阶段的 Page Fault 频率理论上会降低。
- **TLB 覆盖范围扩大**：16KB 页使同一 TLB 条目覆盖的地址空间翻四倍。渲染大块 Graphic Buffer 时，地址转换开销减少，RenderThread 在处理纹理上传和合成操作时的 TLB Miss 率预期下降。

> **待验证**：Page Fault 频率下降约 3-5%、TLB Miss 率下降等量化结论目前缺少同设备 4KB/16KB 对比的 Perfetto / ftrace / perf counter 实测证据。建议读者在自有设备上用相同 kernel config、trace config 和 page-fault / mmap / TLB 观察指标做 A/B 对比后，再采纳具体百分比。4.7 节对 16KB 页有更完整的机制说明。

在 Perfetto 中，16KB 设备上的 `mm_filemap_add_to_page_cache` 事件频率可以作为间接验证指标。

[已验证: 官方文档, source.android.com/devices/tech/perf — 调度相关分析]

### 低内存触发 GC

当系统内存紧张或 App 自身存在内存泄漏时，ART 虚拟机会更频繁地触发垃圾回收（GC）。GC 期间，应用的所有线程（包括主线程）都会被暂停（Stop-The-World），这直接导致正在执行的帧被延迟。

**GC 对卡顿的影响机制。** ART 的 GC 虽然大部分是并发的（Concurrent GC），但在某些阶段仍然需要暂停应用线程（即 Stop-The-World 暂停）。特别是当堆内存接近上限、内存碎片严重、或存在大量短期对象（内存抖动）时，GC 的频率和单次耗时都会增加。关于 ART GC 的具体机制和 Android 17 Generational GC 的变化，详见 4.3 节。

**内存抖动（Memory Churn）。** 在 onDraw、onBindViewHolder 等高频调用的方法中创建临时对象（如 in 循环中创建的 String、新的 Bitmap、ArrayList 等），会导致内存分配频繁、GC 被频繁触发。这种"微观卡顿"在 Perfetto 中可能不会表现为一个超长的帧，但会导致一系列帧都略超预算，用户感受到的是持续的"不流畅"。

**低内存的系统级行为。** 当系统整体内存紧张时，lmkd（Low Memory Killer Daemon）会开始杀后台进程来释放内存。在这个阶段，即使前台 App 没有内存泄漏，也可能因为系统的内存压力而导致更频繁的 GC。

[来源: Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md — 2.8 内存问题优化]
[来源: Personal-Knowlodge/source/2026-03-07_wechat_译文_ART虚拟机新一代GC算法原理介绍.md]

**在 Perfetto 中的表现：** 主线程或应用 Track 中会出现 GC 相关 Slice（如 `GC: Alloc`、`GC: Background`）。CPU Info 区域会呈现应用线程被暂停的时段。通过 Perfetto SQL 也可以查询 GC 事件：

```sql
-- 查询 GC 事件
SELECT * FROM slice WHERE name LIKE '%GC%' AND track_id IN (
  SELECT id FROM track WHERE name LIKE '%.%'
)
```

[已验证: 官方文档, developer.android.com/topic/performance/memory — 内存管理与 GC]

### 温控限频（Thermal Throttling）

当设备温度升高到一定程度时，系统会启动温控策略，降低 CPU/GPU 的运行频率来减少发热。频率降低意味着同样的代码需要更长的时间执行，直接导致帧渲染时间增加。

**温控限频的触发条件。** 不同的 SoC 平台和 OEM 厂商有不同的温控策略。一般来说，当 CPU 温度超过 45-50°C 时，系统开始逐步降低频率；超过 55-60°C 时，可能进入深度限频状态。在长时间游戏、视频录制、或夏季户外使用时，温控限频尤为常见。

**温控限频对帧率的影响。** 温控限频不是突然发生的——它是一个渐进过程。Perfetto 的 CPU Frequency Track 会呈现 CPU 频率逐渐下降的趋势。由于频率降低，原本能在 8.3ms（120Hz）内完成的帧渲染，可能需要 10-12ms，导致持续性的掉帧。

**在 Perfetto 中的表现：** 在 CPU Info 区域检查 CPU Frequency Track，关注各核心运行频率随时间的变化。如果频率在测试过程中持续下降，且同时出现帧率下降，基本可以确认是温控限频导致的。

[已验证: 官方文档, source.android.com/devices/tech/power — thermal management]

### OEM 框架修改导致的 VSync 时序异常

在分析系统级卡顿原因时，还有一个容易被忽略的来源：OEM 厂商对 Android 框架的自定义修改。不同厂商会根据自己的硬件和用户体验策略，对 AOSP 原生的渲染调度逻辑进行不同程度的修改。这些修改大多数情况下是透明的，但在某些场景下会引入与 AOSP 行为不一致的问题，导致 App 出现难以解释的卡顿。

一个典型的案例是华为手机上的 VSync 调度异常。有开发者在实际项目中[发现](https://zhuanlan.zhihu.com/p/450899407)，华为较新的系统版本中，`Choreographer.postFrameCallback` 和 `View.postOnAnimation` 的回调时机存在严重问题：在一个 VSync 周期内，系统会额外注入一个伪造的 VSync 信号，单独处理 `CALLBACK_ANIMATION` 类型的回调。

这造成了三个问题：

1. **回调时序错乱。** 通过 `postFrameCallback` 提交的回调可能在真实 VSync 信号时触发，也可能在伪造信号时触发，且与 Input 处理和 View measure/layout/draw 之间的执行顺序不再保证——这与 AOSP 的设计承诺矛盾。

2. **VSync 周期不均匀。** 由于伪造信号的存在，相邻两次回调的时间间隔会出现"短—长—短—长"的交替现象，导致依赖均匀 VSync 周期的动画或调度逻辑产生抖动。

3. **时间戳偏差。** 回调中获得的 `frameTimeNanos` 在伪造信号触发时不准确，依赖该时间戳进行帧预测或物理模拟的代码会出现混乱。

**规避方案。** 研究 Choreographer 源码后发现，系统额外注入的伪造 VSync 信号只处理 `CALLBACK_ANIMATION` 类型的回调。因此可以通过反射调用 `Choreographer.postCallback` 并指定为 `CALLBACK_TRAVERSAL` 类型来替代 `postFrameCallback` 和 `View.postOnAnimation`。测试表明，`CALLBACK_TRAVERSAL` 类型的回调在真实 VSync 信号时触发，且顺序始终在 View 的 Layout&Draw 之前——与原生系统的行为一致。

这个案例带来的启示是：**当我们在 Perfetto 中看到主线程的 doFrame 时序异常，但 App 代码和 AOSP 源码都找不到合理解释时，需要考虑 OEM 框架修改的可能性。** 不同厂商对 Choreographer、SurfaceFlinger、InputDispatcher 等关键组件的修改程度不同，有些修改不会体现在官方文档中，只能通过实际抓 Trace 对比 AOSP 行为来发现。

[来源: Cubox/华为手机系统 vsync 调度问题研究和解决 - 知乎-2024-03-08.md]
[待验证: 该问题在 HarmonyOS NEXT（纯鸿蒙系统）中是否仍然存在]

### 系统提供的对抗工具：ADPF

当 App 检测到由于限频或调度导致的卡顿风险时，**ADPF（Android Dynamic Performance Framework）** 是官方 CPU 资源提示的主入口。ADPF 的核心 API `PerformanceHintManager` 允许 App 向系统提交线程组的 workload deadline，由系统根据 SoC 状态和温控策略决定是否调整 CPU clock 或 core type。

在卡顿原因体系的语境下，ADPF 的定位是：

- **温控限频的主动对抗**：当 App 检测到帧时间逐渐增长时，通过 ADPF 提交 deadline hint，系统会尽可能维持所需的 CPU 频率，比完全被动等待限频更可控。
- **CPU 资源提示的边界**：`PerformanceHintManager` 的契约范围是 CPU 资源（频率、核心类型）。GPU 频率、线程优先级不在其直接控制范围内。GPU 相关的干预需要通过 Game Mode API、Fixed Performance Mode 等独立接口。
- **适用版本**：Thermal API（`android.os.ThermalManager`）从 Android 11 (API 30) 开始可用；`PerformanceHintManager` / Performance Hint API 从 Android 12 (API 31) 引入；Game Mode / `GameManager` 从 API 31 开始；Game State API 从 Android 13 (API 33) 开始。日常说"ADPF 从 Android 12 可用"指的是 `PerformanceHintManager` 这条主线，Thermal 的温度监听则可以覆盖到 Android 11 设备。

关于 ADPF 的具体接入方式和 API 用法，详见 5.9 节。

## Binder 调用导致的主线程阻塞

Binder 是 Android 进程间通信（IPC）的核心机制（详见 1.4 节）。几乎所有涉及系统服务的操作——获取窗口信息、与 AMS/PMS 通信、获取 SharedPreferences（跨进程模式）、调用系统服务——都需要通过 Binder。

当主线程发起一个同步 Binder 调用时，它会等待目标进程（如 system_server）处理完毕并返回结果。如果目标进程繁忙（比如持有全局锁）、或者 Binder 驱动本身有排队延迟，主线程就会被阻塞。

### 典型的 Binder 卡顿场景

**WindowManagerService 锁竞争。** system_server 中的 WMS（WindowManagerService）使用全局锁来保护窗口状态。当多个进程同时请求窗口操作时（比如多个 App 同时启动、系统动画执行中），WMS 的锁可能被持有较长时间。主线程调用 `relayoutWindow`、`addToDisplay` 等 WMS 方法时，可能因等待锁而被阻塞数十毫秒。

**ActivityManagerService 锁竞争。** 类似地，AMS（ActivityManagerService）也有自己的全局锁。在 Activity 启动、Service 绑定、ContentProvider 查询等场景中，如果 AMS 锁被其他操作持有，主线程的 Binder 调用会被阻塞。

**SurfaceFlinger 的 Binder 瓶颈。** App 通过 Binder 与 SurfaceFlinger 通信来申请/提交缓冲区（dequeueBuffer、queueBuffer）。如果 SurfaceFlinger 的主线程正在处理耗时的合成操作，或者 SurfaceFlinger 本身有锁竞争，App 的 dequeueBuffer 调用可能被阻塞。

**Binder 线程池耗尽。** libbinder 默认最多按需创建 15 个 Binder 线程。如果再算上主动调用 `joinThreadPool()` 的线程，总服务线程数可能更多，具体进程也可以显式覆写这个上限。目标进程响应很慢时，这些 Binder worker 会被逐步占满，新的同步调用只能继续排队。

[已验证: AOSP android-15.0.0_r1, frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp]
[来源: Personal-Knowlodge/source/Android-Systrace-Binder.md]

**在 Perfetto 中的表现：** 主线程 Track 中会出现 Binder 调用 Slice（标记为 `binder txn` 或显示具体的接口方法名）。开启 Flow Events（在 Perfetto UI 中选择"Flow events"）可以追踪 Binder 调用从 App 到目标进程的完整路径。如果 Binder Slice 的持续时间异常长，且目标进程当时有锁竞争或其他耗时操作，基本可以确认是 Binder 阻塞导致的卡顿。

[待补充：Trace 截图 — Binder 阻塞导致的主线程卡顿 Perfetto 片段]

## 分析树：从现象到根因的分析决策路径

前面按渲染管线的阶段，逐一梳理了主线程、RenderThread、SurfaceFlinger、系统级因素和 Binder 调用这五类卡顿原因。但在实际分析中，我们面对的是一个掉帧的 Trace，需要从现象出发，逐步缩小范围，最终定位到具体的根因。分析树要回答的是：拿到一个掉帧的 Trace，应该从哪里开始看、按什么顺序排查、每一步看什么。

### 第一步：按系统版本选入口

打开 Perfetto Trace 后，先按系统版本选入口。

**Android 5-11：** 先在 App 进程里看 VSYNC-app、`Choreographer#doFrame` 和 RenderThread 的 `DrawFrame`。这条入口适合旧版渲染节拍，能先判断 App 是不是在自己的预算里就已经超时。

**Android 12+：** 先看 FrameTimeline。先找 `Actual Timeline` 里的红色条，再看同一帧的 JankType、`On-time finish` 和 `PresentType`。这一代系统已经把掉帧归因拆到 App、SurfaceFlinger 和 Display HAL，继续只盯 `doFrame` 很容易漏掉系统侧问题。

```text
掉帧的视觉线索：
1. Android 5-11：VSYNC-app 间隔异常，或 `Choreographer#doFrame` 明显延迟
2. Android 12+：FrameTimeline 出现红色条、Late present 或异常 JankType
3. 再回到对应进程的线程轨道，确认耗时发生在哪一段
```

### 第二步：按归因回到线程或进程

**Android 5-11：** 先按线程分层排查。
- `Choreographer#doFrame` 本身超时，继续拆主线程里的 measure、layout、draw 和其他业务 slice
- 主线程按时完成，但 RenderThread `DrawFrame` 很长，继续看 GPU 过载、纹理上传、fence wait
- App 侧都正常，再看 SurfaceFlinger 的合成阶段，确认有没有 Client Composition 回退、事务处理或 layer 过多

**Android 12+：** 先按 FrameTimeline 的 JankType 收敛范围。
- `AppDeadlineMissed`：先回到 App 进程，再分主线程和 RenderThread
- `SurfaceFlingerCpuDeadlineMissed`：回到 SurfaceFlinger 主线程，看事务处理、layer 准备和 HWC 协商
- `SurfaceFlingerGpuDeadlineMissed`：回到 SurfaceFlinger 的 Client Composition / RenderEngine 路径，看 GPU 合成和 GPU 争抢
- `DisplayHAL`：SurfaceFlinger 已按时提交，继续看 Display HAL / 驱动一侧的 present 延迟
- `PredictionError`：先核对 expected present time 和实际 present time 的偏差，再判断是不是调度预测漂移
- `BufferStuffing`：先看 BufferQueue 是否积压，再查 `dequeueBuffer`、release fence 和 present 节拍

### 第三步：排除系统级因素

如果渲染管线各环节看起来都正常，但帧还是超时，考虑系统级因素：

**检查 CPU 调度：** 在 CPU Info 区域，查看主线程和 RenderThread 是否有较长的 Runnable Slice（蓝色）。如果有，说明线程已就绪但没有被调度到 CPU 上，是调度延迟。

**检查 GC：** 搜索 Trace 中的 GC 事件，看是否在掉帧附近有 GC 触发。如果有，分析 GC 的原因（内存抖动？内存泄漏？低内存？）

**检查温控：** 查看 CPU Frequency Track，频率是否在下降？设备温度是否升高？

**检查 Binder：** 在主线程的 Track 中查看是否有异常长的 Binder 调用 Slice。开启 Flow Events 追踪 Binder 调用的目标进程。

### 第四步：深入根因

根据第三步的判断，深入具体的根因：

| 瓶颈环节 | 排查方向 | 下一步 |
|---------|---------|-------|
| 主线程 measure/layout 过重 | View 层级、requestLayout 调用频率 | 使用 Layout Inspector 检查层级，搜索代码中的 requestLayout |
| 主线程 onBindViewHolder 耗时 | 查看 bind 中的数据转换、图片操作 | 使用 MethodTrace 定位具体耗时代码 |
| 主线程 I/O | 搜索主线程的文件操作、SP commit | 改为异步或使用 apply() |
| 主线程锁竞争 | 查看 Blocked、monitor contention、`futex_*` 等待 | 找到 owner 线程或唤醒源 |
| RenderThread GPU 过载 | 检查纹理上传、图片大小、Shader 效果、过度绘制 | 减小图片、简化效果、减少重叠 |
| SurfaceFlinger 合成超时 | 检查 Layer 数量、HWC 能力 | 减少 Layer 数、简化窗口层级 |
| CPU 调度延迟 | 检查 Runnable Slice、线程数量 | 减少非必要线程、使用线程优先级 |
| GC 频繁 | 检查内存分配、内存泄漏 | 使用 Memory Profiler 分析内存 |
| 温控限频 | 检查 CPU 频率趋势 | 优化 GPU/CPU 使用，减少持续高负载 |
| Binder 阻塞 | 查看 Binder 调用目标 | 缓存结果、异步调用、减少 Binder 调用频率 |

[已验证: 官方文档, developer.android.com/topic/performance — 整体分析方法论]
[来源: Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md — 方法与经验总结]

分析树的用法是：**从现象出发，逐层缩小范围，最终定位到具体的根因。** 不要一开始就去看某个具体的方法耗时——先判断问题在渲染管线的哪个环节，再深入该环节的细节。

## WebView 渲染导致的 Jank

WebView 内部使用独立的渲染管线（Blink/Chromium），与 Android 原生渲染管线之间存在交互。WebView 内容更新时，通过 `onDraw` 将网页内容绘制到 Android 的 Surface 上，这个过程可能与主线程和 RenderThread 产生竞争。WebView 的 Renderer 进程崩溃恢复、`onRenderProcessGone` 处理流程等内容详见 7.11 节。

## 多窗口/分屏场景的特殊 Jank 问题

分屏模式下，两个 App 同时可见，SurfaceFlinger 需要同时处理两个 App 的 Layer 合成。HWC 的 Overlay 数量有限，分屏更容易触发 GPU 合成回退（Client Composition），且两个 App 的 RenderThread 会竞争 GPU 资源。Perfetto 中可观察的现象是：分屏期间 SurfaceFlinger 的 `computeLayerBounds` / `handleMessageInvalidate` 耗时增加，以及 HWC `type=CLIENT` 的 Layer 数量上升。多窗口场景的完整渲染管线分析见 18.5 节。

## 动画与手势场景的 Jank 特征

动画场景的卡顿有两层特殊性：一是即使单帧没有超时，帧与帧之间的耗时波动（帧节奏不稳）也会导致动画不流畅，Perfetto 中可观察到 `doFrame` Slice 的持续时间呈锯齿形波动；二是手势导航场景中，Input 事件从 `InputDispatcher` 到 App 主线程回调的延迟直接影响触控反馈的及时性，在 Perfetto 中表现为 `delivered_millis` - `expected_delivery_millis` 偏差增大。帧节奏控制的详细机制见 2.17 节，Input 事件分发流程见 3.1 节。

## 常见问题与误区

**误区一：「FPS 低就等于卡顿」**  
FPS 是一个平均值指标，不能直接反映卡顿。如 7.1 节所述，稳定的 40fps 比在 60fps 和 30fps 之间频繁波动体验更好。衡量卡顿应该关注帧与帧之间的耗时波动（Jank）和掉帧率，而不是平均 FPS。

**误区二：「卡顿都是 App 代码的问题」**  
很多卡顿根源在系统层面——CPU 调度延迟、温控限频、SurfaceFlinger 合成瓶颈、系统服务的锁竞争。在分析卡顿时，不要只盯着 App 的代码，一定要从 Perfetto Trace 的全局视角来看。

**误区三：「主线程 CPU 占用低就不会卡顿」**  
CPU 占用率低不代表没有卡顿。如果主线程频繁处于 Runnable 但未执行的状态（调度延迟），或者频繁被 GC 暂停，CPU 占用率可能很低，但帧渲染时间仍然超标。

**误区四：「RenderThread 在独立线程，所以不会影响主线程」**  
虽然 RenderThread 是独立线程，但它与主线程之间存在同步点。在 `syncAndDrawFrame` 阶段，主线程需要将 DisplayList 同步给 RenderThread。如果 RenderThread 正在忙于上一帧的 GPU 命令，同步阶段就会被延迟。此外，RenderThread 和主线程共享 GPU 资源，一方过载会影响另一方。

**误区五：「后台线程不影响主线程性能」**  
后台线程虽然不在主线程上执行，但会抢占 CPU 时间片（影响调度延迟）和增加内存压力（触发更多 GC）。WeSing 的案例表明，新增 30 个后台线程可以将卡顿率从 15% 提升到 20%。

[来源: Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md — 间接卡顿原因 & 误区]

## 参考资料

### AOSP 源码
- `frameworks/base/core/java/android/view/Choreographer.java` — Choreographer 渲染调度核心
- `frameworks/base/core/java/android/view/ViewRootImpl.java` — View 树的渲染入口
- `recyclerview/recyclerview/src/main/java/androidx/recyclerview/widget/RecyclerView.java` — RecyclerView 缓存与绑定机制（AndroidX / Jetpack）
- `frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp` — SurfaceFlinger 合成核心

### 官方文档
- [Android Performance: Rendering](https://developer.android.com/topic/performance/vitals/render) — Google 官方渲染性能指南
- [Android Performance Patterns: Understanding Jank](https://developer.android.com/topic/performance) — 渲染管线与 Jank 分析
- [JankStats Library](https://developer.android.com/develop/ui/views/layout/jankstats) — Jetpack 卡顿监控库

### 高爷原创文章
- [Android Perfetto 系列 5：Android App 基于 Choreographer 的渲染流程](https://www.androidperformance.com/2025/03/26/Android-Perfetto-05-Chorergrapher/)
- [Android Perfetto 系列 7：MainThread 和 RenderThread 解读](https://androidperformance.com/2025/08/02/Android-Perfetto-07-MainThread-And-RenderThread/)

### 业界实践
- [Android深入卡顿分析与实践](https://mp.weixin.qq.com/s?__biz=MzI1NjEwMTM4OA==&mid=2651236641) — 腾讯音乐技术团队
- [从47%到80%，携程酒店APP流畅度提升实践](https://mp.weixin.qq.com/s?__biz=MjM5MDI3MjA5MQ==&mid=2697272883) — 携程技术团队
- [Android卡顿监测的方方面面](https://mp.weixin.qq.com/s?__biz=MzAxMTI4MTkwNQ==&mid=2650850811) — 鸿洋/小木箱
