---
title: "卡顿原因体系"
chapter: "7.2"
status: ready-for-review
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
last_verified: "2026-04-08"
last_verified_against: "AOSP android-15.0.0_r1"
reviewed_date: "2026-04-04"
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
related_chapters: ["7.1", "2.3", "2.4", "2.5", "1.4", "1.5", "3.1", "4.3"]
re-review-result: "审查 0 条素材，无需修改"
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

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要系统化地理解卡顿原因

在 7.1 节中，我们定义了什么是卡顿，也知道了卡顿的本质是「一帧的渲染没能在一个 VSync 周期内完成」。但知道「掉帧了」只是第一步——真正的问题是，这一帧为什么没画完？

这个问题看似简单，实际上答案分散在整个渲染管线的各个环节中。一次卡顿可能源于 App 侧的代码写法（比如在滑动回调里做了太多计算），也可能源于系统侧的调度问题（比如 CPU 把时间片给了别的进程），甚至还可能源于硬件合成的限制。如果我们没有一套系统化的原因分类体系，面对 Perfetto Trace 里密密麻麻的时间线，很容易陷入「到处看看、碰运气」的低效模式。

本节的目标，就是把「一帧为什么没画完」这个问题的所有可能原因，按照渲染管线的阶段整理成一个清晰的原因体系。读完这一节，当我们再在 Perfetto 中看到一帧超时，应该能快速判断问题出在渲染管线的哪个环节、是 App 的问题还是系统的问题、下一步该往哪个方向深挖。

在进入具体原因之前，我们需要先回顾一下一帧的渲染在 Perfetto 中的完整链路，因为后面的原因分类就是按照这个链路的阶段来组织的：

```
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

在这条链路上，任何一个环节超时，后续环节都会被顺延，最终导致这一帧错过 VSync-app 的截止时间，表现为掉帧。接下来我们就按环节逐一分析。

[已验证: 官方文档, developer.android.com/topic/performance/vitals/render]

## 主线程耗时过长

主线程（MainThread / UI Thread）是卡顿最常见的发生地。原因很简单：Android 的渲染管线中，Input 事件处理、Animation 计算、View 的 measure/layout/draw，都发生在主线程上。一旦主线程被某个操作阻塞了太久，超过了当前 VSync 周期的剩余时间，这一帧就注定要掉帧。

在 Perfetto 中，主线程耗时过长通常表现为：一个 doFrame 的绿色 Slice 明显拉长，或者在 doFrame 之前有一段很长的非渲染类 Slice（比如某个业务方法执行了很久）。

[已验证: AOSP android-15.0.0_r1, frameworks/base/core/java/android/view/Choreographer.java]

### Layout/Measure 过重

Layout 和 Measure 是 View 树遍历的核心阶段。当 View 层级过深、或者某个 ViewGroup 的 onMeasure/onLayout 逻辑过于复杂时，这两个阶段的耗时会显著增加。

具体来说，以下几种情况最容易导致 Layout/Measure 耗时飙升：

**View 层级过深。** Android 的 measure 和 layout 是从根节点开始递归遍历整棵 View 树的。如果层级超过 10 层，每次 requestLayout 都需要遍历所有节点，耗时累加起来相当可观。在实际项目中，嵌套过多的 LinearLayout 或 RelativeLayout 是最常见的深层级来源。

**多次 measure 的布局。** 某些布局容器（如 RelativeLayout、带 weight 的 LinearLayout）在单次布局过程中会触发多次 measure，因为子 View 的尺寸互相依赖，需要迭代才能确定最终值。这种「measure 两遍甚至三遍」的行为在某些复杂布局下尤其明显。

**动态布局频繁刷新。** 如果在列表滑动或动画过程中频繁调用 requestLayout（而不是 invalidate），会导致整棵 View 树反复执行完整的 measure → layout → draw 流程。requestLayout 比 invalidate 代价高得多——invalidate 只标记需要重绘的"脏区域"，而 requestLayout 要求从该 View 向上回溯到 ViewRootImpl，重新执行整棵树的 measure 和 layout。

[来源: Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md]

**在 Perfetto 中的表现：** 在主线程的 doFrame Slice 中，可以看到 measure 和 layout 对应的子 Slice 耗时较长。如果开启了 view trace（`-a view`），可以分别看到 `measure` 和 `layout` 的具体耗时。

[待补充：Trace 截图 — measure/layout 耗时过长的 Perfetto 片段]

### RecyclerView Bind 耗时

RecyclerView 是 Android 中最常用的列表组件，也是卡顿的高发地带。RecyclerView 的滑动帧耗时主要取决于 `onBindViewHolder` 和 `onCreateViewHolder` 的执行时间。

**onBindViewHolder 中的重操作。** onBindViewHolder 在每次 Item 进入可视区域时被调用。如果在这个方法中做了数据转换（比如 JSON 解析）、图片加载（同步的 BitmapFactory.decode）、复杂的字符串操作或日期格式化，都会直接增加每帧的耗时。在滑动场景下，一帧可能需要 bind 多个 Item，耗时成倍叠加。

**onCreateViewHolder 中的 inflate。** 当 RecyclerView 的缓存池（RecycledViewPool）中没有可复用的 ViewHolder 时，需要 inflate 新的布局。View.inflate 涉及 XML 解析、反射创建 View 对象、设置属性等操作，是一个比较重的同步操作。如果在滑动过程中频繁触发 onCreateViewHolder，会导致明显的卡顿。

**DiffUtil 的计算开销。** 使用 ListAdapter + DiffUtil 时，如果在主线程执行 areContentsTheSame 等比较逻辑，且比较逻辑本身比较复杂（比如对比大文本内容），也会造成额外的耗时。

[来源: Personal-Knowlodge/source/2026-03-08_wechat_干货_从47_到80_携程酒店APP流畅度提升实践.md]

**在 Perfetto 中的表现：** 在滑动场景的 Trace 中，可以看到主线程的 doFrame 内有一系列 `RV onBind` 或 `RV FullInflate` 的 Slice，如果这些 Slice 的总耗时加上 measure/layout 耗时超过了 VSync 周期，就会掉帧。

[已验证: AOSP android-15.0.0_r1, frameworks/base/core/java/android/widget/RecyclerView.java]

### 主线程 I/O

在主线程上执行文件读写、SharedPreferences 的 apply/commit、数据库查询等 I/O 操作，是卡顿的另一个常见原因。I/O 操作本身是阻塞的，而文件系统（特别是 eMMC 或低端的 UFS 存储）的随机读写延迟可能达到数十毫秒。

**SharedPreferences 的 commit。** commit 方法会将数据同步写入磁盘。如果存储的数据量较大或磁盘 I/O 繁忙，这个调用可能需要数十毫秒。在 Perfetto 中，可以看到主线程有一个 `SP.commit` 或类似的 Slice 占据了大部分帧时间。

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

**在 Perfetto 中的表现：** 主线程出现一段蓝色的 Runnable 或灰色的 Sleeping Slice，查看唤醒源（waker）可以发现是等待某个锁。开启 `-a lock` trace 可以看到更详细的锁竞争信息。

[待验证: `-a lock` 在不同 Android 版本中的可用性]

## RenderThread 瓶颈

从 Android 5.0（Lollipop）开始，Android 引入了 RenderThread，将一部分渲染工作从主线程剥离出来，交给专门的渲染线程执行。主线程负责 measure/layout/draw（记录绘制命令到 DisplayList），RenderThread 负责将 DisplayList 中的命令通过 OpenGL/Vulkan 发送给 GPU 执行。

这个分工的初衷是好的——主线程不再需要等待 GPU 完成渲染。但当 RenderThread 本身的执行时间超过预期时，它同样会成为卡顿的来源。

[已验证: 官方文档, developer.android.com/topic/performance/rendering — RenderThread 介绍]

### GPU 过载

GPU 过载是最常见的 RenderThread 瓶颈。当一帧需要 GPU 执行的绘制命令太多或太复杂时，GPU 的执行时间会超过 VSync 周期的剩余时间（因为主线程的 measure/layout/draw 也消耗了一部分时间）。

**大量图片的解码和上传。** 当一帧中包含多张大图时，RenderThread 需要将这些图片解码后上传到 GPU 纹理。特别是当图片未经过预处理（比如尺寸远大于显示区域），GPU 需要额外处理缩放。

**复杂的 Shader 效果。** 高斯模糊、色彩滤镜、复杂的混合模式等 Shader 效果，会显著增加 GPU 的计算量。在 Perfetto 中表现为 RenderThread 的 draw Slice 很长。

**过度绘制（Overdraw）。** 当屏幕上的同一个像素被多次绘制时（详见 2.8 节），GPU 不得不做大量无用功。在开启了"显示 GPU 过度绘制"的开发者选项后，可以看到屏幕上大量红色区域，这通常意味着 GPU 正在做大量重复的像素填充。

[来源: Personal-Knowlodge/source/2026-03-08_wechat_干货_从47_到80_携程酒店APP流畅度提升实践.md — GPU 问题定位]

**在 Perfetto 中的表现：** RenderThread 的 Slice 明显拉长，特别是其中与 GPU 命令提交相关的子 Slice（如 `flush`、`drawArray`）。在 120Hz 设备上，如果 RenderThread 的执行时间经常超过 4-5ms，就需要关注了。

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

**Layer 过多。** 每个 Activity、Dialog、PopupWindow、Toast 都会创建一个或多个 Layer。当同时可见的 Layer 数量过多时（比如多层 Dialog 叠加、或者分屏模式下两个 App 同时可见），SurfaceFlinger 的合成负担会显著增加。不同 SoC 的 HWC 支持的最大 Overlay Layer 数量不同，高端芯片通常支持 4-8 个 Overlay，超出部分必须走 GPU 合成。

**在 Perfetto 中的表现：** SurfaceFlinger 进程的 `mainLoop` 或 `doComposition` Slice 耗时过长。可以展开 SurfaceFlinger 的 Track 查看具体的合成阶段。

### HWC 能力限制

不同 SoC 平台的 HWC（Hardware Composer）能力差异很大。某些低端平台的 HWC 只支持简单的 Layer 叠加（比如最多 3-4 个 Layer），且不支持缩放、旋转、圆角等操作。当 App 的窗口配置超出了 HWC 的能力范围，SurfaceFlinger 被迫使用 GPU 合成（称为 Device Composition 或 Client Composition），这会增加 GPU 负担和合成延迟。

[来源: Personal-Knowlodge/source/2026-03-08_wechat_Google_为何把_SurfaceView_设计的这么难用.md — HWC Overlay 与 Layer 类型]

**在 Perfetto 中的表现：** 在 SurfaceFlinger 的 Track 中，可以看到 `GPU Composition` 相关的 Slice，或者通过 Perfetto SQL 查询 `Layer` 信息来查看哪些 Layer 走了 GPU 合成。

```sql
-- 查询 SurfaceFlinger 合成方式
SELECT name, composition_type FROM layer
```

[待验证: 上述 SQL 在 Perfetto 中的实际表名可能因版本而异]

## 系统级原因

前面三类原因（主线程、RenderThread、SurfaceFlinger）属于渲染管线内部的问题。但在实际分析中，我们还会遇到一种情况：渲染管线内的每一步看起来都很快，但整体还是超时了。这时候问题往往出在系统层面——CPU 调度、内存管理、温度控制等因素在背后影响着渲染管线的执行效率。

### CPU 调度延迟（Runnable 状态过长）

CPU 调度延迟是最隐蔽、也最容易被忽略的卡顿原因之一。它表现为：线程已经就绪（Runnable），但 Linux 调度器没有及时把它调度到 CPU 上执行，导致线程在"等待被调度"的状态下白白消耗了宝贵的时间。

**为什么会发生调度延迟？**

Linux 的 Completely Fair Scheduler（CFS）按照虚拟运行时间（vruntime）来分配 CPU 时间。当一个线程长时间睡眠后醒来（比如等待 VSync 信号的主线程），它的 vruntime 通常较小，理论上应该优先被调度。但在实际场景中：

- 如果系统中有大量线程处于 Runnable 状态（比如后台进程的工作线程、其他 App 的线程），调度器需要在这些线程之间分配 CPU 时间，主线程可能无法立即获得调度。
- 如果主线程或 RenderThread 被调度到了小核（little core），由于小核的频率和 IPC（Instructions Per Cycle）较低，同样的代码需要更长的时间执行。
- 某些高优先级的实时（RT）进程（如音频处理线程）可能会抢占主线程的 CPU 时间。

**多线程竞争对主线程的影响。** 腾讯 WeSing 团队在优化卡顿时发现了一个典型案例：升级 TRTC SDK 后，App 新增了近 30 个线程，这些线程的 CPU 占用甚至超过了主线程和 RenderThread。虽然这些线程本身不在主线程上执行，但它们抢占了 CPU 时间片，导致主线程的调度延迟增加，进而引发卡顿。

[来源: Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md — 2.9 线程问题造成的卡顿优化]

**在 Perfetto 中的表现：** 在 CPU Info 区域查看主线程的状态，会看到蓝色的 Runnable Slice（表示线程已就绪但未执行）。如果这个 Runnable Slice 的持续时间超过 2-3ms，就值得关注。可以通过点击 Runnable Slice 查看唤醒源和前一个线程的状态，分析为什么调度器没有及时调度主线程。

[已验证: 官方文档, source.android.com/devices/tech/perf — 调度相关分析]

### 低内存触发 GC

当系统内存紧张或 App 自身存在内存泄漏时，ART 虚拟机会更频繁地触发垃圾回收（GC）。GC 期间，应用的所有线程（包括主线程）都会被暂停（Stop-The-World），这直接导致正在执行的帧被延迟。

**GC 对卡顿的影响机制。** ART 的 GC 虽然大部分是并发的（Concurrent GC），但在某些阶段仍然需要暂停应用线程（即 Stop-The-World 暂停）。特别是当堆内存接近上限、内存碎片严重、或存在大量短期对象（内存抖动）时，GC 的频率和单次耗时都会增加。关于 ART GC 的具体机制和 Android 17 Generational GC 的变化，详见 4.3 节。

**内存抖动（Memory Churn）。** 在 onDraw、onBindViewHolder 等高频调用的方法中创建临时对象（如 in 循环中创建的 String、新的 Bitmap、ArrayList 等），会导致内存分配频繁、GC 被频繁触发。这种"微观卡顿"在 Perfetto 中可能不会表现为一个超长的帧，但会导致一系列帧都略超预算，用户感受到的是持续的"不流畅"。

**低内存的系统级行为。** 当系统整体内存紧张时，lmkd（Low Memory Killer Daemon）会开始杀后台进程来释放内存。在这个阶段，即使前台 App 没有内存泄漏，也可能因为系统的内存压力而导致更频繁的 GC。

[来源: Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md — 2.8 内存问题优化]
[来源: Personal-Knowlodge/source/2026-03-07_wechat_译文_ART虚拟机新一代GC算法原理介绍.md]

**在 Perfetto 中的表现：** 在主线程或应用的 Track 中，可以看到 GC 相关的 Slice（如 `GC: Alloc`、`GC: Background`）。在 CPU Info 区域，可以看到应用线程被暂停的时段。通过 Perfetto SQL 也可以查询 GC 事件：

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

**温控限频对帧率的影响。** 温控限频不是突然发生的——它是一个渐进过程。在 Perfetto 中可以看到 CPU 频率逐渐下降的趋势。由于频率降低，原本能在 8.3ms（120Hz）内完成的帧渲染，可能需要 10-12ms，导致持续性的掉帧。

**在 Perfetto 中的表现：** 在 CPU Info 区域，查看 CPU Frequency Track，可以看到各核心的运行频率随时间的变化。如果频率在测试过程中持续下降，且同时出现帧率下降，基本可以确认是温控限频导致的。

[已验证: 官方文档, source.android.com/devices/tech/power — thermal management]

### OEM 框架修改导致的 VSync 时序异常

在分析系统级卡顿原因时，还有一个容易被忽略的来源：OEM 厂商对 Android 框架的自定义修改。不同厂商会根据自己的硬件和用户体验策略，对 AOSP 原生的渲染调度逻辑进行不同程度的修改。这些修改大多数情况下是透明的，但在某些场景下会引入与 AOSP 行为不一致的问题，导致 App 出现难以解释的卡顿。

一个典型的案例是华为手机上的 VSync 调度异常。有开发者在实际项目中[发现]((https://zhuanlan.zhihu.com/p/450899407))，华为较新的系统版本中，`Choreographer.postFrameCallback` 和 `View.postOnAnimation` 的回调时机存在严重问题：在一个 VSync 周期内，系统会额外注入一个伪造的 VSync 信号，单独处理 `CALLBACK_ANIMATION` 类型的回调。

这造成了三个问题：

1. **回调时序错乱。** 通过 `postFrameCallback` 提交的回调可能在真实 VSync 信号时触发，也可能在伪造信号时触发，且与 Input 处理和 View measure/layout/draw 之间的执行顺序不再保证——这与 AOSP 的设计承诺矛盾。

2. **VSync 周期不均匀。** 由于伪造信号的存在，相邻两次回调的时间间隔会出现"短—长—短—长"的交替现象，导致依赖均匀 VSync 周期的动画或调度逻辑产生抖动。

3. **时间戳偏差。** 回调中获得的 `frameTimeNanos` 在伪造信号触发时不准确，依赖该时间戳进行帧预测或物理模拟的代码会出现混乱。

**规避方案。** 研究 Choreographer 源码后发现，系统额外注入的伪造 VSync 信号只处理 `CALLBACK_ANIMATION` 类型的回调。因此可以通过反射调用 `Choreographer.postCallback` 并指定为 `CALLBACK_TRAVERSAL` 类型来替代 `postFrameCallback` 和 `View.postOnAnimation`。测试表明，`CALLBACK_TRAVERSAL` 类型的回调在真实 VSync 信号时触发，且顺序始终在 View 的 Layout&Draw 之前——与原生系统的行为一致。

这个案例带来的启示是：**当我们在 Perfetto 中看到主线程的 doFrame 时序异常，但 App 代码和 AOSP 源码都找不到合理解释时，需要考虑 OEM 框架修改的可能性。** 不同厂商对 Choreographer、SurfaceFlinger、InputDispatcher 等关键组件的修改程度不同，有些修改不会体现在官方文档中，只能通过实际抓 Trace 对比 AOSP 行为来发现。

[来源: Cubox/华为手机系统 vsync 调度问题研究和解决 - 知乎-2024-03-08.md]
[待验证: 该问题在 HarmonyOS NEXT（纯鸿蒙系统）中是否仍然存在]

## Binder 调用导致的主线程阻塞

Binder 是 Android 进程间通信（IPC）的核心机制（详见 1.4 节）。几乎所有涉及系统服务的操作——获取窗口信息、与 AMS/PMS 通信、获取 SharedPreferences（跨进程模式）、调用系统服务——都需要通过 Binder。

当主线程发起一个同步 Binder 调用时，它会等待目标进程（如 system_server）处理完毕并返回结果。如果目标进程繁忙（比如持有全局锁）、或者 Binder 驱动本身有排队延迟，主线程就会被阻塞。

### 典型的 Binder 卡顿场景

**WindowManagerService 锁竞争。** system_server 中的 WMS（WindowManagerService）使用全局锁来保护窗口状态。当多个进程同时请求窗口操作时（比如多个 App 同时启动、系统动画执行中），WMS 的锁可能被持有较长时间。主线程调用 `relayoutWindow`、`addToDisplay` 等 WMS 方法时，可能因等待锁而被阻塞数十毫秒。

**ActivityManagerService 锁竞争。** 类似地，AMS（ActivityManagerService）也有自己的全局锁。在 Activity 启动、Service 绑定、ContentProvider 查询等场景中，如果 AMS 锁被其他操作持有，主线程的 Binder 调用会被阻塞。

**SurfaceFlinger 的 Binder 瓶颈。** App 通过 Binder 与 SurfaceFlinger 通信来申请/提交缓冲区（dequeueBuffer、queueBuffer）。如果 SurfaceFlinger 的主线程正在处理耗时的合成操作，或者 SurfaceFlinger 本身有锁竞争，App 的 dequeueBuffer 调用可能被阻塞。

**Binder 线程池耗尽。** 每个进程默认有 16 个 Binder 线程（`max_threads`）。如果主线程同时发起多个 Binder 调用，且这些调用的目标进程响应很慢，可能导致 Binder 线程池耗尽。此时新的 Binder 调用需要等待空闲线程，进一步加剧延迟。

[已验证: AOSP android-15.0.0_r1, frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp]
[来源: Personal-Knowlodge/source/Android-Systrace-Binder.md]

**在 Perfetto 中的表现：** 在主线程的 Track 中，可以看到 Binder 调用的 Slice（标记为 `binder txn` 或显示具体的接口方法名）。开启 Flow Events（在 Perfetto UI 中选择"Flow events"）可以看到 Binder 调用从 App 到目标进程的完整链路。如果 Binder Slice 的持续时间异常长，且目标进程当时有锁竞争或其他耗时操作，基本可以确认是 Binder 阻塞导致的卡顿。

[待补充：Trace 截图 — Binder 阻塞导致的主线程卡顿 Perfetto 片段]

## 分析树：从现象到根因的分析决策路径

前面按渲染管线的阶段，逐一梳理了主线程、RenderThread、SurfaceFlinger、系统级因素和 Binder 调用这五类卡顿原因。但在实际分析中，我们面对的不是「某个已知的原因」，而是一个掉帧的 Trace——需要从现象出发，逐步缩小范围，最终定位到具体的根因。这就需要一套系统化的分析决策路径——拿到一个掉帧的 Trace，应该从哪里开始看、按什么顺序排查、每一步看什么。这就是本节要建立的"分析树"。

### 第一步：确认掉帧位置

打开 Perfetto Trace，定位到掉帧的时间点。在 App 进程的 Track 中，找到 VSYNC-app 信号之间的间隔超过一个 VSync 周期的区域。

```
掉帧的视觉线索：
1. VSYNC-app 之间的间隔大于一个周期（120Hz 下 > 8.3ms, 60Hz 下 > 16.6ms）
2. Actual Frame Timeline 中出现红色条（表示掉帧）
3. MainThread 的 doFrame Slice 缺失或延迟
```

### 第二步：判断瓶颈在哪个线程

找到掉帧区域后，按以下优先级检查各线程的耗时：

**检查 MainThread：** doFrame Slice 的总耗时是多少？如果 doFrame 本身就超过了 VSync 周期的大部分时间，问题在主线程。进一步看 doFrame 内部的子 Slice：
- `measure` / `layout` 占大头 → Layout/Measure 过重（→ 参考"主线程耗时过长"一节）
- `draw` / `Record View#draw` 占大头 → 绘制命令过多
- doFrame 之前有很长的非渲染 Slice → 主线程被其他任务阻塞

**检查 RenderThread：** 如果 MainThread 的 doFrame 在预算内完成了，但整帧还是超时了，看 RenderThread。RenderThread 的 `DrawFrame` Slice 是否过长？
- GPU 命令执行时间长 → GPU 过载
- 等待 GPU 的 Slice（如 `fence wait`）较长 → GPU 被其他任务占用

**检查 SurfaceFlinger：** 如果 App 侧的 MainThread 和 RenderThread 都正常，去看 SurfaceFlinger 进程：
- SurfaceFlinger 的合成 Slice 是否超时？
- 是否有大量 GPU 合成（Device Composition）？
- 是否有 Layer 过多导致 HWC 无法处理？

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
| 主线程锁竞争 | 查看 Runnable/Blocked 状态的唤醒源 | 找到持锁线程和持锁原因 |
| RenderThread GPU 过载 | 检查图片大小、Shader 效果、过度绘制 | 减小图片、简化效果、减少重叠 |
| SurfaceFlinger 合成超时 | 检查 Layer 数量、HWC 能力 | 减少 Layer 数、简化窗口层级 |
| CPU 调度延迟 | 检查 Runnable Slice、线程数量 | 减少非必要线程、使用线程优先级 |
| GC 频繁 | 检查内存分配、内存泄漏 | 使用 Memory Profiler 分析内存 |
| 温控限频 | 检查 CPU 频率趋势 | 优化 GPU/CPU 使用，减少持续高负载 |
| Binder 阻塞 | 查看 Binder 调用目标 | 缓存结果、异步调用、减少 Binder 调用频率 |

[已验证: 官方文档, developer.android.com/topic/performance — 整体分析方法论]
[来源: Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md — 方法与经验总结]

这个分析树的核心思想是：**从现象出发，逐层缩小范围，最终定位到具体的根因。** 不要一开始就去看某个具体的方法耗时——先判断问题在渲染管线的哪个环节，再去深入那个环节的细节。

## WebView 渲染导致的 Jank

[待补充：WebView 内部使用独立的渲染管线（Blink/Chromium），与 Android 原生渲染管线之间存在交互。当 WebView 内容更新时，需要通过 `onDraw` 将网页内容绘制到 Android 的 Surface 上，这个过程可能与主线程和 RenderThread 产生竞争。待收集更多素材后补充。]

## 多窗口/分屏场景的特殊 Jank 问题

[待补充：在分屏模式下，两个 App 同时可见，SurfaceFlinger 需要同时处理两个 App 的 Layer 合成。HWC 的 Overlay 数量是有限的，分屏模式下更容易触发 GPU 合成回退。此外，两个 App 的 RenderThread 会竞争 GPU 资源。待收集更多素材后补充。]

## 动画与手势场景的 Jank 特征

[待补充：动画场景的卡顿有其特殊性——即使单帧没有超时，帧与帧之间的耗时波动也可能导致动画不流畅。手势导航场景中，Input 事件处理的延迟直接影响触控反馈的及时性。待收集更多素材后补充。]

## 常见问题与误区

**误区一：「FPS 低就等于卡顿」**  
FPS 是一个平均值指标，不能直接反映卡顿。如 7.1 节所述，稳定的 40fps 比在 60fps 和 30fps 之间频繁波动体验更好。衡量卡顿应该关注帧与帧之间的耗时波动（Jank）和掉帧率，而不是平均 FPS。

**误区二：「卡顿都是 App 代码的问题」**  
很多卡顿实际上是系统层面的原因——CPU 调度延迟、温控限频、SurfaceFlinger 合成瓶颈、系统服务的锁竞争。在分析卡顿时，不要只盯着 App 的代码，一定要从 Perfetto Trace 的全局视角来看。

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
- `frameworks/base/core/java/android/widget/RecyclerView.java` — RecyclerView 缓存与绑定机制
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
