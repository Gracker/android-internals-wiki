---
title: "案例集"
chapter: "10.5"
section: "10.5"
status: "ready-for-review"
drafted_date: "2026-04-02"
applicable_versions: "Android 8.0 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-02"
reviewed_date: "2026-05-27"
reviewed_by: "openclaw-task6"
task6_result: pass-light-edit
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium
sources:
  - type: blog
    path: "Personal-Knowlodge/source/Android-Jank-Due-To-Low-Memory.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-08_wechat_谁动了我的内存_揭秘_OOM_崩溃下降_90_的秘密_1.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-06_wechat_抖音renderD128系统级疑难OOM分析与解决.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-08_wechat_MemoryThrashing_抖音直播解决内存抖动实践_1.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-09_wechat_字节跳动应用性能监控帮助客户Java_OOM崩溃率下降80.md"
  - type: official
    path: "https://developer.android.com/topic/performance/memory"
    note: "Android 内存管理官方指南"
  - type: official
    path: "https://source.android.com/docs/core/perf/lmkd"
    note: "userspace lmkd 与 PSI / vmpressure 机制"
tags: ['case-study', 'memory-leak', 'native-memory', 'low-memory', 'oom', 'cache', 'gc']
polish_count: 1
polish_date: "2026-04-09"
polish_by: "task2b-polish"
related_chapters: ["10.1", "10.2", "10.3", "10.4", "10.6"]
task6_state: reviewed
task6_result: pass-light-edit
task6_reviewed_date: "2026-05-27"
last_task6_audit: "2026-05-18"
pipeline_stage: "task9_pending"
review_notes: "2026-04-30 task6 revisiting review: pass-light-edit。修复1处禁用词(意味着)。无B类大问题。评分: 结构5/5·措辞4/5·一致性4/5·验证3/5·元数据4/5。 | 2026-05-07 Task9 01:20：pass-tech-review。无 P0/P1，Task6 已通过且 queue 无 pending，自动晋升 finalized。P2：ProfilingTrigger API37 版本边界、案例效果量化占位仍建议补。"
task9_state: pending
task9_reviewed_date: "2026-05-25"
task2b_state: "fixed"
task2b_result: fixed
rework_fixed_at: "2026-05-06T21:43:37+08:00"
task2b_rework_date: "2026-04-30"
task2b_fixed_at: "2026-04-30T01:40:00+08:00"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-05-07T01:20:00+08:00"
task9_result: "needs-rework"
last_task9_audit: "2026-05-25"
last_task2b_verifier_at: "2026-05-27T03:37:00+08:00"
task2b_verifier_result: "ready-for-task6"
last_task6_at: "2026-05-27T05:14:00+08:00"
last_task6_review_log: "logs/review/2026-05-27-05-review.md"
task6_review_notes: "2026-05-27 Task6 05:14：pass-light-edit。L1/L2 小修 6 处（去第一人称、删除虚假引导语）。无新增 L3/L4 回炉；既有效果量化占位按待补充/P2 保留。Task9 未重新通过，未自动晋升 finalized。"
---

# 案例集

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 提供 3-5 个真实内存性能案例
- 🔹 案例需覆盖：Java 泄漏、Native 泄漏、缓存膨胀、低内存引发的流畅性退化
- 🔹 每个案例包含：问题现象、分析工具使用、根因定位、修复方案与量化效果

### 扩展（可选深入）

- 🔸 大型 App 的内存治理实践
- 🔸 厂商 ROM 对内存管理的定制化案例

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

前面的章节已经分别讨论了内存分析的方法论（10.1）、内存泄漏的识别与修复（10.2）、内存持续增长的排查思路（10.3），以及低内存对系统性能的整体影响（10.4）。这一节把这些知识放到真实场景里，通过四个来自实际产品和线上环境的案例，完整走一遍从"发现问题"到"定位根因"再到"验证修复"的全过程。

每个案例的侧重点不同：有 Java 堆泄漏、有 Native 内存异常、有低内存引发的整机性能退化、还有内存突增导致的 OOM 崩溃。读完之后，面对自己的内存问题时，应该能带走一套可复用的分析框架。

## 案例一：低内存引发整机卡顿与冷启动退化

[来源: Personal-Knowlodge/source/Android-Jank-Due-To-Low-Memory.md]

### 问题现象

这是一台 6GB 内存的设备，用户反馈整机使用体验变差：启动应用比平时慢很多，列表滑动明显掉帧，后台应用经常需要重新加载。测试同学抓取了一个低内存状态下的应用冷启动 Trace，从 bindApplication 到第一帧显示的总耗时达到了 **2 秒**。

而在正常内存状态下，同样的操作只需要 **1.22 秒**——差异超过 60%。更关键的是，Running 时间几乎没有变化（低内存 682ms vs 正常 624ms），说明 CPU 计算本身不是瓶颈，额外的时间消耗来自其他地方。

### 分析思路

面对这种 CPU 计算时间没有明显增加、但总耗时被拉长的情况，第一步是看主线程的调度状态。在 Perfetto 中，Uninterruptible Sleep（D 状态）是最常见的线索——主线程在这个状态意味着它在等待某个内核操作完成，通常是 I/O。

果然，在低内存的 Trace 中，主线程的 **Uninterruptible Sleep | WakeKill - Block I/O** 加上普通 Uninterruptible Sleep 总共占了约 **750ms**。而正常情况下只有 **130ms**。这 620ms 的差距，几乎完美解释了冷启动从 1.22s 退化到 2s 的原因。

### 根因定位

低内存状态下，系统中有几个关键机制同时出问题：

**kswapd0 频繁被唤醒**。这是 Linux 内核的内存回收守护线程，当系统可用内存低于水位线时触发。低内存 Trace 显示，kswapd0 占满了某个大核 CPU（比如 CPU7），以满频运行。如果前台应用的主线程恰好被调度到同一个核心，就会遭遇 CPU 竞争导致调度延迟。

[图：Perfetto 中 kswapd0 占满 CPU7 的 Trace 片段]

**主线程的 Block I/O 增加**。Linux 的 page cache 在低内存时会被频繁回收。当主线程需要读取某个文件（比如 odex 文件、配置文件、布局资源）时，如果对应的 page 已经被回收，就必须重新从磁盘读入。这个过程中，线程会阻塞在 `wait_on_page_bit_killable()` 内核函数中，等待 I/O 完成。在 Perfetto 中表现为大段的 Uninterruptible Sleep - Block I/O。

[图：低内存 vs 正常内存下主线程的 Block I/O 对比]

**进程被频繁查杀和重启**。在 Android 8+ 的主线实现里，低内存查杀主要由 userspace `lmkd` 负责；Android 10+ 在内核具备支持时，`lmkd` 会优先使用 PSI monitors 判断是否进入真实内存压力，`vmpressure` 更多是兼容旧内核的回退路径。SystemServer 日志会记录某些进程（比如 QQ）在短时间内被反复杀死又拉起，形成"杀 → 起 → 杀 → 起"的死循环。每次杀进程和拉起进程都会消耗 CPU、I/O 和内存资源，进一步恶化整机性能。

```logcat
07-23 14:32:16.932  am_proc_start: com.tencent.mobileqq, restart
07-23 14:32:16.969  am_proc_bound: com.tencent.mobileqq
07-23 14:32:16.979  am_kill: com.tencent.mobileqq, adj 901, empty #3
07-23 14:32:16.996  am_proc_died: com.tencent.mobileqq
07-23 14:32:17.028  am_proc_start: com.tencent.mobileqq, restart
07-23 14:32:17.054  am_proc_bound: com.tencent.mobileqq
07-23 14:32:17.064  am_kill: com.tencent.mobileqq, adj 901, empty #3
...（循环重复数十次）
```

[已验证: 官方文档, source.android.com/docs/core/perf/lmkd — userspace lmkd、PSI / vmpressure 机制确认]

### 修复方案与效果

这个问题的根因不在单个 App，而在整机内存水位管理。系统层面的优化方向包括：

**提高 extra_free_kbytes 值**。这个内核参数控制了 kswapd0 提前回收内存的触发阈值。适当提高这个值，可以让系统更早开始内存回收，避免进入紧急回收状态时对前台应用造成冲击。

**优化 `lmkd` 的杀进程策略**。避免对"可快速重启"的缓存进程进行无意义的反复杀起。可以通过调整 minfree / adj 阈值和厂商侧回收策略，让一次回收释放足够的内存，而不是杀一个进程发现不够又杀一个。

**限制后台进程的 I/O**。使用 cgroup 的 blkio 控制器限制后台进程的磁盘读写带宽，确保前台应用的 I/O 请求能优先得到处理。

**App 端的配合**。App 可以通过 `onTrimMemory()` 回调感知系统内存压力，主动释放非必要的缓存（如图片缓存、预加载的数据等）。

`onTrimMemory` 的可用级别在不同 Android 版本上有显著差异：

- **API 33 及以下**：系统会投递从 `TRIM_MEMORY_RUNNING_MODERATE`（5）到 `TRIM_MEMORY_COMPLETE`（80）的各级别回调，App 可以根据级别梯度释放资源
- **API 34（Android 14）起**：`RUNNING_*`、`MODERATE`、`COMPLETE` 等旧级别不再投递给 App，系统改为通过 PSI（Pressure Stall Information）和 `lmkd` 在内核层面做内存压力判断
- **API 35（Android 15）起**：`RUNNING_*` 相关常量标记为 `@Deprecated`

API 34+ 的 App 可靠回调级别主要是 `TRIM_MEMORY_UI_HIDDEN`（20）和 `TRIM_MEMORY_BACKGROUND`（40）。系统级内存压力判断应回到 `meminfo` 轨道、`lmkd` 指标和 PSI 信号，而非依赖已废弃的 trim level。

[已验证: AOSP frameworks/base/core/java/android/content/ComponentCallbacks2.java; API 34+ ComponentCallbacks2 变更]

### 举一反三

这个案例的核心规律是：**低内存会引发系统性连锁反应**。内存不足 → kswapd 频繁回收 → page cache 被清空 → I/O 增加 → 进程被杀又拉起 → CPU 和 I/O 竞争加剧 → 前台应用卡顿。

在 Perfetto 中看到主线程有大量 Uninterruptible Sleep - Block I/O 时，不要只关注 I/O 本身——往上看一眼系统内存水位（Perfetto 中的 `meminfo` track），往往能找到上游原因。

---

## 案例二：Java 堆泄漏导致的 OOM 崩溃率治理

[来源: Personal-Knowlodge/source/2026-03-09_wechat_字节跳动应用性能监控帮助客户Java_OOM崩溃率下降80.md]

### 问题现象

某内容型 App 的线上 Java OOM 崩溃率持续偏高。从 APM（应用性能监控）平台的数据来看，OOM 崩溃堆栈非常分散，分布在各种看似不相关的代码路径中——有的崩溃在 Bitmap 分配，有的在字符串拼接，有的在 JSON 解析。这些堆栈看起来毫无规律，因为它们都是"压死骆驼的最后一根稻草"——根因不在崩溃点本身，而在于 Java 堆已经被某个大户占满了。

### 分析思路

治理 OOM 的第一步是搞清楚**内存被谁占着**。这个案例中，团队采用了基于 Hprof 内存快照的线上归因方案：在 OOM 发生时（或接近发生时），抓取一份 Java 堆的 Hprof 快照，然后在服务端分析各对象的引用链。

分析 Hprof 快照时，最关键的是找到 **Dominator Tree**（支配者树）中的大节点。所谓"支配者"，就是某个对象如果被 GC 回收，它直接或间接持有的所有对象都会被回收。找到几个最大的 Dominator，通常就能定位到内存泄漏的源头。

[已验证: 官方文档, developer.android.com/studio/profile/memory-profiler — Hprof 分析方法确认]

### 根因定位

通过对线上快照的批量分析，团队发现了几个主要问题：

**静态集合持有过期对象**。App 中有一个全局的 `HashMap` 用于缓存用户数据，键是用户 ID，值是完整的用户信息对象。随着用户不断滑动浏览内容，这个 Map 持续增长——即使这些用户已经退出详情页，对应的对象也不会被释放。在某些极端场景下，这个 Map 持有数万个条目，占用数百 MB 的 Java 堆空间。

**Bitmap 未及时回收**。在某些页面退出的代码路径中，缺少对 Bitmap 的 `recycle()` 调用（这在 Android 8.0 以下尤为重要，因为 Bitmap 的像素数据存储在 Java 堆中）。Android 8.0+ 虽然将像素数据移到了 Native 堆，但如果 Bitmap 对象本身（包括对 Native 内存的引用）被泄漏，对应的 Native 内存同样无法释放。

**匿名内部类 / Lambda 隐式持有外部引用**。一些异步回调通过匿名内部类或 Lambda 的方式引用了 Activity 或 Fragment 的实例。即使页面已经关闭，只要回调还没执行完（或者被某个长生命周期的对象间接持有），整个 Activity 及其 View 树就无法被 GC 回收。

[已验证: 官方文档, developer.android.com/reference/android/graphics/Bitmap — Android 8.0 NativeAllocationRegistry 变更确认]

### 修复方案与效果

**方案一：改成容量可控的缓存和显式失效**。不要把 `WeakHashMap` 当作全局 `HashMap` 缓存的通用替代。`WeakHashMap` 只有 key 是弱引用，value 仍由 map 强持有；如果 key 是 `String`、userId 这类长生命周期对象，回收时机并不受缓存策略控制。更稳妥的做法是，对容量型缓存使用 `LruCache`，对页面级或会话级数据做显式失效；只有在 value 可以独立失效、业务也能接受 GC 抖动时，再考虑用 `WeakReference` 包装 value。

**方案二：生命周期感知的资源清理**。在 Activity/Fragment 的 `onDestroy()` 中，主动释放大对象（Bitmap、大数组等），并清空与该页面相关的静态引用。对于异步回调，使用 WeakReference 包装，或者在页面销毁时取消未完成的异步任务。

**方案三：线上 Hprof 归因持续监控**。将 Hprof 快照的自动化分析持续集成到 APM 平台中，监控线上内存分配的大户。当某个版本的内存分布发生异常变化时，自动告警。

**效果**：上线优化后，该 App 的 Java OOM 崩溃率在两个版本周期内下降了约 **80%**。其中收益最大的改动是 LruCache 替换 HashMap，贡献了约 60% 的降幅。

[来源: Personal-Knowlodge/source/2026-03-09_wechat_字节跳动应用性能监控帮助客户Java_OOM崩溃率下降80.md]

### 举一反三

Java 堆泄漏有一个典型特征：**崩溃堆栈分散，但根因集中**。当 OOM 崩溃堆栈分散在看似随机的代码路径中时，不应该在崩溃点逐个排查——先看 Java 堆的整体分布，找到那个"看不见的大象"。线上 Hprof 抓取方案虽然有一定的性能开销，但对于定位这类问题几乎是不可替代的。

另一个需要注意的点是：Android 8.0+ 的 Bitmap 像素数据虽然不在 Java 堆了，但 Bitmap 泄漏仍然是问题。Bitmap 的 Java 对象仍然占空间，而且它持有的 Native 内存引用会阻止对应 Native 内存的释放。在分析泄漏时，需要同时关注 Java 堆和 Native 堆。

---

## 案例三：GPU 驱动导致的 Native 内存异常膨胀

[来源: Personal-Knowlodge/source/2026-03-06_wechat_抖音renderD128系统级疑难OOM分析与解决.md]

### 问题现象

抖音长期存在一个诡异的虚拟内存 OOM 问题：在某些特定机型上（主要是华为 Android 10 设备，搭载联发科芯片和 PowerVR GPU），`/dev/dri/renderD128` 类型的内存占用会异常膨胀到 **1GB 左右**，直接导致 32 位进程的虚拟地址空间耗尽，触发 OOM 崩溃。

这个问题有几个特征：堆栈非常分散（都是系统堆栈），崩溃集中在特定机型和 ABI（armeabi-v7a），而且多次导致发版熔断。更麻烦的是，过去只能通过二分法定位引发问题的 MR（代码修改）来紧急回滚——但那些代码本身并没有 bug，只是"恰好"触发了系统 API 的异常行为。

### 分析思路

这是一个典型的"问题在 App 侧，根因在系统侧"的案例。团队的分析路径可以复用到其他“App 侧问题、系统侧根因”的场景：

**第一步：稳定复现**。通过对历史触发 MR 的分析，团队找到了一种可稳定复现的方法：给 View 设置透明度（`setAlpha(0.5)`）。测试发现，**每增加一个设置了 alpha 的 View，renderD128 内存增加约 25MB**。不设 alpha 的对照组则没有变化。这立刻将排查范围缩小到了"硬件加速渲染管线中与 alpha 合成相关的路径"。

需要说明的是，`setAlpha()` 是否触发 offscreen buffer 创建取决于渲染条件：在硬件加速下，只有当 `hasOverlappingRendering()` 返回 `true`（即 View 存在重叠绘制）时，渲染管线才会为该 View 创建独立的离屏缓冲区来完成 alpha 合成。如果确认 View 不会与子 View 或兄弟 View 重叠，可以通过 `hasOverlappingRendering() → false` 来避免缓冲区分配，同时保留 alpha 效果。本案例中触发的机型和 GPU 驱动组合，在 `hasOverlappingRendering` 为 true 的默认行为下表现出了缓冲区不释放的异常。

**第二步：Hook 关键接口**。团队尝试 Hook mmap/mmap64/mremap/ioctl 等系统调用，试图捕获 renderD128 内存的分配路径。但令人意外的是，mmap 相关的 Hook 完全监控不到 renderD128 的内存分配，ioctl 的 Hook 也只捕获到了一个不影响内存的命令。

**第三步：从内核源码寻找线索**。由于用户空间的 Hook 无法捕获分配，团队转向了内核源码。他们找到了华为畅享 10e 的内核源码，阅读了 DRM（Direct Rendering Manager）驱动的代码，发现 ioctl 命令只是把参数传给驱动，内存分配发生在 GPU 驱动内部。

**第四步：锁定关键 so 库**。通过 ioctl 调用的堆栈，团队锁定了三个"嫌疑人"：`libdrm.so`、`libsrv_um.so`（PowerVR 的用户空间服务库）、`gralloc.mt6765.so`（联发科的内存分配库）。其中 `libsrv_um.so` 是最可疑的，因为它是 PowerVR GPU 的闭源驱动库。

[图：ioctl 堆栈指向 libsrv_um.so 和 gralloc.mt6765.so]

### 根因定位

通过深入分析，团队最终确认了问题的根因：

当 View 被设置了 alpha 值且存在重叠绘制时，Android 的硬件加速渲染管线会创建一个额外的 **离屏缓冲区（offscreen buffer）** 来完成 alpha 合成（条件判断在 `RenderProperties::promotedToLayer()`：alpha 在 (0,1) 且 `hasOverlappingRendering()` 为 true 时，`effectiveLayerType()` 变为 RenderLayer；`RenderNode::pushLayerUpdate()` 负责创建或更新 layer）。这个缓冲区的分配和释放由 GPU 驱动管理。在特定的 GPU 驱动版本（PowerVR 的某些旧版本）上，这些离屏缓冲区在绘制完成后不会被正确释放——它们被 GPU 驱动内部的缓存机制"持有"了。

具体来说，问题出在 PowerVR GPU 驱动的 buffer pool 管理策略：驱动维护了一个缓冲区池来复用 GPU 内存，但当 alpha 合成产生的中间缓冲区尺寸超出池中现有缓冲区的尺寸时，驱动会分配新的缓冲区。由于旧的较小缓冲区没有被及时释放，缓冲区池不断膨胀。

每个需要 offscreen buffer 的 alpha View → GPU 驱动缓存不释放 → renderD128 内存持续增长。25MB/个的速度非常惊人——10 个 View 就是 250MB，对于 32 位进程来说（用户空间约 3GB），这足以在短时间内耗尽虚拟地址空间。

> **16KB Page Size 的潜在影响** [待验证]：本案例发生环境为 Android 10 / 32 位 / PowerVR GPU，不涉及 16KB 页。在 Android 15+ 的 16KB 页环境中，Gralloc 分配的图形缓冲区需要 16KB 物理页对齐。公开资料中的 9% 额外内存开销是系统平均口径（`ceil(buffer_size / 16384) * 16384`），不能直接等同为单个 offscreen buffer 的增量——实际开销取决于宽高、像素格式、stride 和 allocator 对齐策略。如果怀疑 16KB 页加剧了 GPU buffer 膨胀，建议用 `dmabuf_dump -b` 按 buffer 尺寸归因物理开销，并与同设备 4KB 模式做对照。

[待验证: PowerVR GPU 驱动的 buffer pool 管理策略细节，闭源驱动无法直接验证]

### 修复方案与效果

**短期方案：避免不必要的 alpha 设置和减少重叠绘制**。在业务代码中审查所有 `setAlpha()` 调用，将可以通过其他方式实现的效果（如用半透明颜色替代 alpha）改掉。对于必须使用 alpha 的场景：

- 如果 View 确认没有重叠绘制，覆写 `hasOverlappingRendering()` 返回 `false`，这样渲染管线不会为该 View 创建 offscreen buffer，同时 alpha 效果仍然生效
- 避免使用 `setLayerType(LAYER_TYPE_HARDWARE)` 配合 alpha，因为硬件层本身就会强制创建 FBO（Framebuffer Object），这和 alpha 触发的 offscreen buffer 是两套独立的缓冲区机制
- `LAYER_TYPE_NONE` 是 View 的默认层类型，把它作为"规避手段"是错误的——它并不会阻止 alpha 触发的 offscreen buffer 创建
- 有效的优化方向是减少 View 层级重叠、避免 group alpha/saveLayer，以及在不需要动画时及时清除 alpha 值

**长期方案：与 GPU 厂商合作修复驱动**。将问题反馈给联发科和 PowerVR（ImgTec），推动他们在驱动层面修复缓冲区池的释放策略。同时，对于 64 位进程，3GB 的虚拟地址空间限制不再存在，所以推动 64 位化也是一个间接的解决方案。

**监控方案**。在线上监控 `/proc/self/maps` 中 renderD128 相关映射区域的大小变化，当检测到异常增长时触发告警，避免问题再次发生时来不及反应。

**效果**：修复后，renderD128 相关的 OOM 崩溃率下降至基线水平（[待补充：具体降幅百分比]），发版熔断事件未再发生。

> **源码参考**：alpha 合成的自动建层条件在 `RenderProperties::promotedToLayer()`：alpha ∈ (0,1) 且 `hasOverlappingRendering()` 为 true 时触发；`RenderNode::pushLayerUpdate()` / `CanvasContext::createOrUpdateLayer()` 负责实际的 layer 创建与更新。`computeOrderingImpl` 处理子节点排序和投影，不是该条件判断的入口。Alpha 合成与硬件层（LAYER_TYPE_HARDWARE）的 FBO 机制是独立的：前者是渲染管线的 Shader 级处理，后者是 Buffer 级隔离。

[来源: Personal-Knowlodge/source/2026-03-06_wechat_抖音renderD128系统级疑难OOM分析与解决.md]

### 举一反三

这个案例可以提炼出几条实战经验：

第一，**不是所有内存问题都能通过常规手段（如 LeakCanary、MAT）发现**。LeakCanary 只能检测 Java 堆的泄漏，对于 GPU 驱动内部管理的内存完全无能为力。当线上出现大量"虚拟内存 OOM"但 Java 堆远未满时，需要把排查视线转向 Native 内存和设备内存映射。

第二，**二分法定位虽然原始，但有时是唯一可靠的方法**。在无法 Hook 到分配路径的情况下，通过回滚 MR 来缩小问题范围，虽然耗时但有效。有效的前提是找到"能稳定复现的操作"，这比盲目猜测高效得多。

第三，**闭源 GPU 驱动是 Android 性能分析的盲区**。厂商定制的 GPU 驱动行为差异很大，同一段代码在不同机型上可能表现出完全不同的内存行为。如果线上数据显示问题集中在特定机型/SoC，一定要先看看是不是驱动层面的问题。

---

## 案例四：直播场景的内存突增与 OOM

[来源: Personal-Knowlodge/source/2026-03-08_wechat_MemoryThrashing_抖音直播解决内存抖动实践_1.md]

### 问题现象

抖音直播的 OOM 问题有一个特点：内存不是慢慢泄漏的，而是**突然跳升**。比如内存从 600MB 在几秒内跳到 800MB，然后在下一个瞬间 OOM 崩溃。传统的"定时采样内存"方案很难捕获到这种突变的瞬间——因为无法预判该在什么时刻抓取快照。

另一个难点在于，现有的 MemoryGraph 工具虽然能分析 OOM 成因，但性能开销很大，只能低采样率运行，不容易触达问题。而且生成的快照可能不是内存高位（比如设备 4GB 内存时快照只有 1GB），导致分析结果偏离真实的 OOM 现场。

### 分析思路

团队提出了一个叫做 **MemoryThrashing** 的方案。核心思路是：**在内存突变时主动捕获现场**。

所谓"thrashing"（抖动），在这里指的是内存在短时间内大幅波动——比如 200MB 的突然增长。团队定义了一个阈值：当内存增长超过某个值（比如 X 秒内增长超过 Y MB）时，判定为一次"抖动"事件，立即触发一次轻量级的内存分析。

这个方案的关键创新在于"轻量"。它不需要抓取完整的 Hprof 快照（那个太重了），而是通过周期性采样 `Runtime.totalMemory()` 和 `Runtime.freeMemory()` 来检测 Java 堆的变化趋势。当检测到突增时，快速扫描当前线程栈和关键数据结构的大小，记录下"谁在分配内存"。

> **Android 15+ 替代采集后端**：Android 15（API 35）引入了 `ProfilingManager`，App 可主动调用 `requestProfiling(int profilingType, Bundle parameters, String tag, CancellationSignal, Executor, Consumer<ProfilingResult>)` 请求系统转储 heap profile 或 trace。注意：`ProfilingTrigger` 目前只暴露 `TRIGGER_TYPE_APP_FULLY_DRAWN` 和 `TRIGGER_TYPE_ANR`，没有"内存突增"自动触发类型。所以 MemoryThrashing / 业务探针仍然负责发现内存阈值；`ProfilingManager` 可作为触发后的采集后端，比自研方案开销更低。新项目建议"探针检测 + ProfilingManager 采集"的组合模式，MemoryThrashing 作为 Android 15 以下的兼容方案。

### 根因定位

通过 MemoryThrashing 捕获的数据，团队发现了直播场景中几个主要的内存突增来源：

**弹幕和礼物动画的对象风暴**。直播间在热门时段，弹幕消息和礼物动画的创建频率极高。每条弹幕是一个对象（包含文本、样式、位置信息），每个礼物动画需要创建 Bitmap 和动画状态对象。当大量消息同时涌入时，短时间内创建数万个对象，Java 堆迅速膨胀。虽然这些对象的生命周期很短（弹幕滑出屏幕就可以回收），但 GC 来不及跟上创建速度，导致堆内存先到达上限触发 OOM。

**视频解码器的缓冲区累积**。直播流的视频解码需要一组解码缓冲区（通常是 5-8 个，每个大小等于一帧的像素数据）。在分辨率切换（比如从 720p 切到 1080p）时，旧的缓冲区可能还没释放，新的更大尺寸的缓冲区已经分配了。在低端设备上，这种"旧未释放、新已分配"的过渡状态可能消耗大量内存。

**图片加载库的缓存膨胀**。直播间的各种图片（头像、商品图、背景）通过图片加载库（如 Glide/Coil）缓存。默认的缓存策略通常基于可用内存的百分比，但在直播场景下，用户可能在一个直播间停留很长时间，不断加载新的图片。缓存在不知不觉中膨胀到几百 MB。

[来源: Personal-Knowlodge/source/2026-03-08_wechat_MemoryThrashing_抖音直播解决内存抖动实践_1.md]

### 修复方案与效果

**针对弹幕对象风暴**：引入对象池（Object Pool）复用弹幕对象。弹幕滑出屏幕后，不丢弃对象，而是放回池中供下一条弹幕复用。这样避免了频繁的对象创建和 GC 压力。同时在极端情况下（弹幕速度超过某个阈值），进行消息合并和降频显示。

**针对解码器缓冲区**：在分辨率切换时，先释放旧缓冲区再分配新缓冲区，而不是同时持有两套。虽然这可能导致短暂的画面闪烁，但比 OOM 崩溃好得多。

**针对图片缓存**：根据当前场景动态调整缓存策略。直播场景下使用更激进的缓存淘汰策略（比如限制缓存条目数而非百分比），并在内存压力大时（通过 `onTrimMemory` 回调感知）主动清空缓存。

**效果**：MemoryThrashing 方案上线后，直播场景的 OOM 崩溃率明显下降（[待补充：具体降幅百分比]）。这个工具还让团队第一次能够在线上"看到"内存突增的现场，将 OOM 问题的平均定位时间从天级缩短到小时级。对于 Android 15+ 设备，`ProfilingManager` 可作为触发后的采集后端降低运行时开销。

[来源: Personal-Knowlodge/source/2026-03-08_wechat_MemoryThrashing_抖音直播解决内存抖动实践_1.md]

### 举一反三

**内存问题至少要区分两类：泄漏，以及短时间内的过度分配。**

泄漏的特征是内存只增不减，曲线呈单调上升。而"对象风暴"的特征是内存曲线呈锯齿状——快速上升然后被 GC 回收一部分，但下一个高峰可能就突破了上限。两种问题的治理策略完全不同：泄漏需要找到那条"不该存在的引用链"，而对象风暴需要减少分配频率或复用对象。

在 Perfetto 中，通过 **Java Heap Timeline** 和 **GC Event Track** 可以区分这两种模式。如果 GC 事件频繁触发但每次回收的量不大，同时堆内存呈上升趋势，通常是泄漏。如果 GC 回收了大量内存但很快又被分配满，呈现锯齿形，那更可能是对象风暴。

---

## 案例的共通规律

四个案例反复指向几条内存性能分析规律：

**规律一：崩溃堆栈通常不是问题所在**。无论是 Java OOM 还是 Native OOM，崩溃发生的那个内存分配点往往只是"最后一步"。根因通常是某个一直在默默占用内存的大户。先看整体内存分布，再看具体分配点。

**规律二：内存问题经常是系统性的连锁反应**。低内存 → kswapd 频繁回收 → I/O 增加 → 进程被杀重启 → 前台卡顿。解决时不能只盯着某一环，需要从源头（内存水位管理）入手。

**规律三：不同类型的内存问题需要不同的工具**。Java 堆泄漏用 MAT/LeakCanary，Native 泄漏用 heapprofd/ASAN，GPU 相关的内存异常需要看 `/proc/self/maps` 和厂商工具。没有一把万能钥匙。

**规律四：线上监控和线下分析要配合**。很多内存问题（尤其是对象风暴、驱动异常）只在线上特定场景出现，线下很难复现。需要在线上建立足够的监控（内存水位、突变检测、关键数据结构大小追踪），为线下分析提供入口。

**规律五：机型差异不容忽视**。同样一段代码，在 64 位设备上可能完全正常，在 32 位设备上却频繁 OOM。不同 SoC 平台的 GPU 驱动行为差异巨大。分析内存问题时，一定要关注"这个现象是否集中在特定机型/ABI/SoC"。

## 与其他章节的关联

- **10.1 App 内存分析**：本案例集使用的大部分工具和方法论，在 10.1 中有详细介绍。
- **10.2 内存泄漏**：案例二中的 Java 堆泄漏分析，可以直接对照 10.2 中的泄漏模式分类。
- **10.3 内存持续增长**：案例四中的"缓存膨胀"问题，属于 10.3 讨论的持续增长模式之一。
- **10.4 低内存对系统性能的影响**：案例一完整展示了 10.4 中描述的低内存连锁反应机制。
- **10.6 内存抖动与频繁 GC**：案例四中的"对象风暴"是 10.6 要深入讨论的核心话题。
- **4.4 Low Memory Killer**：案例一中进程被频繁查杀的 userspace `lmkd` 路径，在 4.4 中有系统层面的详解。
- **7.4 典型场景分析**：从卡顿分析的角度，低内存引发的卡顿也属于 7.4 讨论的典型场景。

## 参考资料

- [Android 中的卡顿丢帧原因概述 - 低内存篇 — androidperformance.com](https://www.androidperformance.com/2019/09/18/Android-Jank-Due-To-Low-Memory/)
- [谁动了我的内存，揭秘 OOM 崩溃下降 90% 的秘密 — ByteCode 公众号](https://mp.weixin.qq.com/s?__biz=MzAwNDgwMzU4Mw==&mid=2247486738)
- [抖音 renderD128 系统级疑难 OOM 分析与解决 — 字节跳动技术团队](https://mp.weixin.qq.com/s?__biz=MzI1MzYzMjE0MQ==&mid=2247514363)
- [MemoryThrashing：抖音直播解决内存抖动实践 — 字节跳动技术团队](https://mp.weixin.qq.com/s?__biz=MzI1MzYzMjE0MQ==&mid=2247496677)
- [AOSP frameworks/base/core/java/android/content/ComponentCallbacks2.java — onTrimMemory 级别常量定义](https://cs.android.com/android/platform/superproject/+/android-16.0.0_r1:frameworks/base/core/java/android/content/ComponentCallbacks2.java)
- [AOSP frameworks/base/core/java/android/view/View.java — setAlpha 与硬件加速离屏缓冲区](https://cs.android.com/android/platform/superproject/+/android-16.0.0_r1:frameworks/base/core/java/android/view/View.java)
