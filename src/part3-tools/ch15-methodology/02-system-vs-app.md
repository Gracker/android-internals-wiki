---
title: "如何区分系统问题和 App 问题"
chapter: "15.2"
section: "15.2"
status: ready-for-review
pipeline_stage: task2b_pending
task2b_result: fixed
task2b_state: pending
task6_state: reviewed
task6_reviewed_date: "2026-06-17"
last_task6_at: "2026-06-19T02:06:00+08:00"
task6_result: needs-rework
last_task2b_lite_at: 2026-06-17
drafted_date: "2026-04-04"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-06-19"
last_verified_against: "AOSP android-17.0.0_r1; Perfetto memory-counters"
confidence: high
sources:
 - type: blog
 path: "androidperformance.com/2025/11/12/Android-Perfetto-09-CPU/"
 - type: blog
 path: "androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/"
 - type: official
 path: "perfetto.dev/docs/data-sources/cpu-scheduling"
 - type: official
 path: "developer.android.com/topic/performance"
 - type: official
 path: "https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs"
 - type: official
 path: "perfetto.dev/docs/data-sources/frametimeline"
 - type: official
 path: "perfetto.dev/docs/data-sources/memory-counters"
 - type: aosp
 path: "frameworks/native/services/surfaceflinger/"
tags: ['methodology', 'system-vs-app', 'trace-analysis', 'attribution']
related_chapters: ["5.1", "7.1", "7.2", "7.3", "13.3", "13.6", "15.1"]
last_task6_audit: "2026-06-18"
task6_reviewed_by: "openclaw-task6"
last_task6_review_log: "logs/review/2026-06-19-02-review.md"
task6_l1_l2_fixes: 8
task6_l3_l4_issues: 0
task6_review_notes: "2026-06-19 Task6 revisiting-review: needs-rework。Task9 auto-fix（Perfetto RSS anon GLOB 顺序）正确；但发现 B 类格式问题：全文 27/32 个标题与正文之间的换行丢失（heading+body 合并到同一行），列表项同样合并，属于大规模格式损坏，需 Task2B 重新排版。"
task9_state: reviewed
task9_result: auto-fixed
last_task9_at: "2026-06-19T00:26:33+08:00"
task9_reviewed_date: "2026-06-19"
task9_reviewed_by: openclaw-task9
last_task9_review_log: "logs/deep-review/2026-06-19-00-deep-review.md"
task9_review_notes: "2026-06-19 Task9 deep-review: auto-fixed。修复 Perfetto RSS anon 查询使用错误 GLOB 顺序，改为 process_counter_track.name = 'mem.rss.anon'；证据：Perfetto memory-counters / §13.5；回到 Task6 复审。"
p0: 1
p1: 0
p2: 0
review_round: 3
repaired_date: "2026-04-27"
repaired_by: "openclaw-task2b"
last_task2b_at: 2026-06-18T22:50:00+08:00
finalized_date: "2026-05-28"
finalized_by: openclaw-task9
last_task9_audit: "2026-06-16"
last_task9_audit_log: "logs/deep-review/2026-06-16-04-audit.md"
last_task9_autofix_at: "2026-06-19"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-19
last_task2b_recovery: data recovery from commit 2c5c7c85 after Lite truncation (ec2e99c4)
---

# 如何区分系统问题和 App 问题<!-- outline-start -->

## 本节要点大纲

## 锚点- 🔹 区分系统问题 vs App 问题的重要性- 🔹 从 Trace 判断：CPU 调度延迟 → 系统、主线程耗时 → App- 🔹 系统负载高的特征：CPU 全核满载、kswapd 活跃、SurfaceFlinger 延迟- 🔹 App 自身问题的特征：主线程 Slice 耗时明显、特定操作触发- 🔹 灰色地带：系统资源不足导致 App 表现差（谁该负责？）

## 扩展- 🔸 多 App 共存时的性能归因- 🔸 系统级性能回归的排查方法

## 为什么一定要区分系统问题和 App 问题很多性能排查卡在后半段——trace 够了，工具也会用，问题出在一开始就把责任链看错了。用户反馈你的 App 滑动卡顿，你打开 Perfetto 一看，主线程每一帧都在 20ms 左右——超标了，但 MainThread 的 Slice 里没有特别长的耗时段。放大去看，主线程大部分时间处于 Runnable 状态，也就是“准备好了但上不去 CPU”。同时 CPU 区域里 8 个核心全满，system_server、媒体扫描器、另一个游戏进程各占了不少核。这种情况，该谁改？如果你的回答是"App 端优化"，那方向就偏了。主线程并没有做太多计算，它只是拿不到 CPU 时间——这是调度器的问题，根源是系统资源竞争。反过来，如果主线程在 Traversal（measure/layout/draw）阶段就耗了 18ms，CPU 也没满载、频率也正常，那这就是 App 自身的问题。**区分系统问题和 App 问题，决定了优化方向。**方向错了，花再多时间也出不了结果。App 开发者去优化系统调度，或者系统工程师去改 App 的布局层级，都是南辕北辙。在不少团队里，App 组和系统组本来就是分开的。能不能把责任链说清楚，直接影响后面的排期和资源分配。后面的判断方法围绕三个问题展开：打开 Perfetto 之后，按照什么顺序看、看什么信号、怎么下结论。

## 核心判断框架：从 Trace 里把责任链读出来打开一份 Perfetto Trace，面对一个已知的性能问题（比如滑动卡顿、启动慢、ANR），按以下顺序进行归因：

## 第一步：看主线程的 Wall 时间 vs CPU 时间在 Perfetto 中选中主线程的某个关键 Slice（比如 `Choreographer#doFrame`），下方的详情面板会显示 `Wall` 和 `CPU` 两个时间。`Wall` 是这个 Slice 从开始到结束的真实世界耗时；`CPU` 是这个线程在 CPU 上执行代码的时间。两者的关系是：```Wall = CPU 时间 + Runnable 时间 + Sleep 时间```如果 `Wall ≈ CPU`，说明主线程一直在跑代码，没有怎么等待——这是**典型的 App 自身问题**，需要用火焰图找出是哪个函数吃掉了时间。如果 `Wall >> CPU`，差值主要花在了等待上，那就需要进一步区分：是在等 CPU（Runnable），还是在等别的资源（Sleep/D 状态）。

## 第二步：区分 Runnable 和 Sleep看主线程的 `thread_state` 轨道（就是紧挨着主线程 Slice 下方的彩色条）：- 如果差值主要是 **Runnable（浅绿色）**：线程准备好了，但调度器没有给它 CPU 时间。这是**系统侧调度延迟**的信号。- 如果差值主要是 **Sleep（蓝色）**：线程在等某个事件完成。需要进一步看 `blocked_function` 字段：是 `binder_thread_read`（等 Binder 回复）、`futex_wait_queue_me`（等锁）、还是 `epoll_wait`（等 I/O）。Binder 等待可能是服务端慢；锁等待可能是本进程内其他线程持有锁；I/O 等待可能是存储子系统的问题。- 如果差值主要是 **D 状态（橙色/红色）**：线程在做不可中断的磁盘 I/O。如果 App 在主线程做文件读写，那是 App 的错；如果是因为系统内存不足导致频繁 swap，那又回到了系统问题。

## 第三步：确认系统上下文确认了主线程的等待类型后，还需要看全局的系统状态来佐证判断：- **CPU 区域**：所有核心是否满载？如果是，说明系统负载很高，主线程拿不到 CPU 是合理的。- **频率轨道**：CPU 频率是否正常？如果被温控限频（`scaling_max_freq` 被压低），即使主线程分到了 CPU，执行速度也会打折扣。- **内存压力**：有没有看到 `kswapd` 线程活跃？有没有大量的 `direct reclaim` 事件？- **SurfaceFlinger 轨道**：Android 14+ 的 trace 里优先看 `commit` 和 `composite`。`commit` 处理事务、状态更新和 buffer latch；`composite` 负责合成决策、HWC/GPU 提交和 present 前后的工作。旧 trace 或部分设备上仍可能看到 `onMessageRefresh`，它更像外层刷新入口，不要把它当成唯一耗时归因点。这三步形成了一个从局部到全局的判断链：先看问题线程本身，再看等待类型，再结合系统环境佐证。

## 系统问题的典型特征

## CPU 全核满载在 Perfetto 顶部的 CPU 区域，你能看到每个核心上正在执行的线程。如果所有核心（包括大核和小核）都被密集占满，且持续较长时间，这就是系统负载过高的直接证据。满载本身不一定是问题——后台编译（dex2oat）、大文件下载、游戏引擎渲染，都可能让 CPU 跑满。问题在于，当 CPU 全部满载时，调度器不得不在所有竞争者之间分配时间片。低优先级的线程（比如后台 App 的主线程）很容易被反复抢占，长时间处于 Runnable 状态排不上队。在 Perfetto 中你可以用这个 SQL 查询来量化某个时间段内的系统负载：```sql-- 查看某段时间内各进程的 CPU 时间SELECT process.name, sum(dur) / 1e9 AS total_cpu_time_sFROM schedJOIN thread ON sched.utid = thread.utidJOIN process ON thread.upid = process.upidWHERE ts > 2e9 AND ts < 5e9 -- 替换为你的时间范围GROUP BY process.nameORDER BY total_cpu_time_s DESCLIMIT 10;```**注意一种常见的误判**：CPU 看起来满载，但满载的主力可能是你的 App 自己。在归因之前，先确认"满载的主力"是不是你自己的进程。如果 top 1 的 CPU 消耗者就是你的 App，那问题回到了 App 端——可能是后台线程在做不必要的计算。

## kswapd 活跃与内存压力`kswapd` 是 Linux 内核的后台内存回收守护线程。当系统空闲内存低于阈值时，`kswapd` 被唤醒，开始扫描并回收可回收的内存页（如 clean page cache），或者将匿名页压缩到 zRAM 中。在 Perfetto 中，如果你在 CPU 区域看到 `kswapd0`（或 `kswapd1`、`kswapd2`，取决于 NUMA 节点数）频繁且持续地出现在 CPU 上，说明系统正在经历持续的内存压力。这种内存压力会导致一系列连锁反应：1. **App 进程被 LMK 杀掉**：如果 `kswapd` 回收不够快，现代 Android 通常由 userspace `lmkd` 结合 `oom_score_adj`、PSI 和 reclaim 信号决定是否杀进程。旧资料里的 `oom_adj` 是历史字段名。App 被杀后用户下次打开就是冷启动，体验变差。2. **主线程进入 D 状态**：内存不足时，页面换入（page fault）会触发同步的磁盘 I/O，主线程如果触发了 page fault，就会进入不可中断的 D 状态等待 I/O 完成。3. **GC 频繁触发**：ART 在内存紧张时会更频繁地触发 GC。Android 10+ 默认的 Generational Concurrent Copying GC 中，Young GC 暂停往往在 1-3ms，但在高负载场景里这段暂停仍可能被放大，因为 GC 线程本身也要争抢 CPU。定位内存压力来源时，不要停在 `kswapd` 这个信号上。继续看 `rss_stat` / process memory 轨道，把问题时间窗内各进程的 RSS 增长排出来，再结合 `lmkd` kill 事件、`oom_score_adj` 和 `ApplicationExitInfo.getRss()` 判断谁在制造压力。常用查询可以从 anon RSS 增长开始：```sql-- 按进程统计问题时间窗内 anon RSS 增长SELECT process.name, max(c.value) - min(c.value) AS anon_rss_growth_bytes, max(c.value) AS anon_rss_peak_bytesFROM counter cJOIN process_counter_track pct ON c.track_id = pct.idJOIN process ON pct.upid = process.upidWHERE c.ts BETWEEN 2e9 AND 5e9 AND pct.name = 'mem.rss.anon'GROUP BY process.nameHAVING anon_rss_growth_bytes > 0ORDER BY anon_rss_growth_bytes DESCLIMIT 10;```不同 Android 版本和采集配置下，track 名称可能略有差异。查询没有结果时，先在 Perfetto UI 搜索 `rss_stat`、`mem.rss.anon`、`mem.rss.file`，确认 trace 是否采到了进程级内存 counter。所以当你看到 `kswapd` 活跃 + 主线程出现 D 状态 + LMK 频繁杀进程这三件套，可以判定这是系统级内存压力。App 端仍要确认自身 RSS 是否异常增长；如果自身内存稳定，最终解决通常需要系统层面调整 LMK 策略或增加物理内存。

## SurfaceFlinger 合成延迟SurfaceFlinger 是系统级的合成服务，它负责把所有 App 的 Layer 合成为最终显示的画面。当 SurfaceFlinger 自身出现性能瓶颈时，**所有可见的 App 都会受影响**，而不仅仅是某个 App。在 Perfetto 中排查 SurfaceFlinger 延迟，主要看这几个信号（详见 §2.6）：- SurfaceFlinger 主线程 Track 上 `commit`、`composite`，以及旧 trace 中可能出现的 `onMessageRefresh`。Android 14+ 里 `commit` 主要覆盖事务处理和 buffer latch，`composite` 主要覆盖合成决策、HWC/GPU 提交和 present 相关工作。判断 SF 延迟时，先和同设备、同分辨率、同刷新率、相近 Layer 数量的正常帧对比。Client 合成在不同 GPU、HWC 能力和分辨率下差异很大；只有相对基线持续拉长，并且 FrameTimeline 标记指向 SF 侧，才把 SF 作为主要方向。- `VSYNC-sf` 信号到来时 SurfaceFlinger 是否及时响应。如果 SF 在一个 VSync 周期内没能完成合成，这一帧就会被延迟到下一个 VSync 才呈现——表现为全局性的掉帧，不只是一个 App 的掉帧。- Android 12+ 的 `FrameTimeline` 数据会明确标记 jank 的类型：如果是 `SurfaceFlingerCpuDeadlineMissed` 或 `SurfaceFlingerGpuDeadlineMissed`，那就是 SF 侧的问题。SurfaceFlinger 延迟的常见原因包括：GPU 被其他进程（如游戏）占用导致 Client 合成排队；Layer 数量过多（多个浮窗、画中画、分屏）；HWC（Hardware Composer）能力不足，需要回退到 GPU 合成等。

## App 自身问题的典型特征

## 主线程 Slice 耗时明显这是最直观的 App 侧问题信号。在 Perfetto 中展开目标 App 进程，找到主线程 Track，看看 `Choreographer#doFrame` Slice 的耗时：- `doFrame` 内部的 `performTraversals` 耗时是否超过帧预算（60Hz 下 16.6ms，120Hz 下 8.3ms）？- 是 `measure`、`layout` 还是 `draw` 阶段过长？- 有没有出现连续多帧的长耗时（而非偶尔一帧）？如果 `doFrame` 的 `Wall ≈ CPU`（即主线程一直在执行代码，没有被调度延迟或等待打断），那就需要用火焰图（CPU Flamegraph）来定位具体是哪个函数在消耗时间。常见的原因包括：布局层级过深、在 `onDraw` 中做了不必要的对象创建、JSON 解析放在了主线程等。

## 特定操作触发App 侧问题的另一个特征是**可重现、可关联到特定用户操作**。比如：- 用户滑动 RecyclerView 时卡顿 → 可能是 `onBindViewHolder` 里有耗时操作。- 用户点击某个按钮后界面卡死 2 秒 → 可能是在点击回调里做了同步网络请求或数据库查询。- App 从后台切到前台时卡顿 → 可能是 `onResume` 里重新加载了大量数据。这种"操作触发型"的卡顿与系统问题形成鲜明对比——系统级问题往往是全局性的、持续性的，不会因为某个用户操作而突然出现或消失。在 Perfetto 中确认操作触发型问题的方法：对比问题帧和正常帧。找到问题发生前的几帧正常渲染（`doFrame` 耗时正常），以及问题帧。在问题帧的 Slice 里，你会看到比正常帧多出来的操作——这就是触发原因。

## RenderThread 耗时不要忘了 RenderThread。即使主线程很快完成了 `measure/layout/draw`，如果 RenderThread 的 `DrawFrame` 耗时过长，帧仍然会延迟呈现。RenderThread 的常见问题包括：- 过度绘制（Overdraw）严重：同一像素被绘制多次，GPU 工作量大。- 硬件层（Hardware Layer）滥用：设置了很多 `LAYER_TYPE_HARDWARE`，但 View 内容频繁变化，导致硬件层反复重建。- Shader 编译：首次使用复杂的 Shader 时，编译耗时可能达到几十毫秒。在 Perfetto 中，如果看到主线程的 `doFrame` 耗时正常（< 8ms），但 RenderThread 的 `DrawFrame` 耗时很长（> 10ms），那问题就在渲染管线后半段。这仍然是 App 端的问题——需要优化渲染策略，而不是去找系统组。

## 灰色地带：谁该负责理想世界里，问题要么是系统的，要么是 App 的。但在实际工作中，最常见的情况往往是灰色地带：**系统资源不足，导致 App 本来没问题的代码跑出了问题**。这种情况下，"归因"就变得微妙了。

## 场景一：CPU 被其他 App 占满你的 App 主线程本来只需要 6ms 就能完成一帧的渲染，但系统中有另一个高优先级进程占满了 CPU，导致你的主线程在 Runnable 状态等了 12ms 才拿到 CPU，最终这帧花了 18ms——掉了。从 App 的角度看，"我没有做错任何事"。从系统角度看，"调度器按优先级分配资源，没有 bug"。但从用户角度看，你的 App 就是卡了。**判断原则**：如果 App 的代码在**理想条件下**（CPU 不满载、频率正常、内存充足）可以满足性能目标，那优化方向应该是**系统侧的资源管控**——比如提高前台 App 主线程的调度优先级（通过 `cgroup` 前台组已经自动做了），或者限制后台进程的 CPU 使用。App 端可以做的"兜底"是减少计算量、异步化重操作，减少帧渲染时间，给调度延迟留出更多容错空间。

## 场景二：内存不足导致 App 频繁 GC系统内存紧张时，ART 的 GC 触发频率会升高。GC 本身会暂停所有线程（包括主线程），暂停时间虽然通常只有 1-3ms（Generational GC），但在内存极度紧张时 Young GC 可能每秒触发多次，累计暂停时间就很可观了。这种情况严格来说是"系统内存不足"引发的问题，但**根因可能在 App 端**：如果 App 自身占用了大量内存（Bitmap 缓存、内存泄漏），它就是内存紧张的制造者之一。解决方向是 App 减少自身的内存占用。**判断原则**：查看 App 自身的内存占用曲线。如果 App 的 Java Heap 或 Native Heap 在持续增长，那 App 就是问题的一部分。如果 App 内存稳定但系统整体内存仍然紧张（因为其他 App），那需要系统层面管控。

## 场景三：温度控制导致降频设备过热时，温控系统会强制降低 CPU 频率。此时所有 App 的执行速度都会变慢——本来 6ms 能完成的工作可能要 12ms。这是物理限制，App 和调度器都无能为力。**判断原则**：这种场景下，查看 CPU Frequency 轨道，如果 `scaling_max_freq` 被明显压低（比如大核从 3.0GHz 降到 1.5GHz），且设备温度传感器数值很高，就可以确认是温控降频。App 端能做的是降低计算量（减少渲染复杂度、降低帧率目标），系统端能做的是优化温控策略和散热设计。

## 多 App 共存时的性能归因现代 Android 设备上通常同时运行着几十个进程。当一个 App 出现性能问题时，影响来源可能是另一个 App。这时候归因需要做"跨进程分析"。

## 方法一：CPU 时间排行用 Perfetto 的 SQL 查询，看看在问题发生的时间段内，哪些进程消耗了最多的 CPU 时间：```sql-- 问题时间段内各进程 CPU 时间排行SELECT process.name, sum(dur) / 1e6 AS total_cpu_ms, count(*) AS slicesFROM schedJOIN thread ON sched.utid = thread.utidJOIN process ON thread.upid = process.upidWHERE ts > 2e9 AND ts < 5e9GROUP BY process.nameORDER BY total_cpu_ms DESCLIMIT 15;```如果 top 1 的 CPU 消耗者是一个后台 App（比如某社交软件的后台同步服务），那问题可能就是这个进程抢了 CPU 资源。

## 方法二：唤醒链分析在 Perfetto 的 CPU 区域点击一个被延迟的线程 Task，Perfetto 会自动绘制唤醒箭头，显示是谁唤醒了这个线程。沿着唤醒链往回追溯，往往能找到问题的源头。举个例子：你的主线程在等一个 Binder 调用返回。通过唤醒链分析，你发现服务端（system_server）的 Binder 线程在处理你的请求之前，先花了 30ms 处理了另一个进程的请求。这说明你的请求本身不慢，只是排队等了——如果那个"插队"的进程一直在发密集的 Binder 调用，它就是问题间接制造者。

## Binder 归因：追到服务端线程状态客户端主线程 Sleep 在 `binder_thread_read` 或 Binder ioctl 上，只能证明它在等回复，不能直接证明服务端代码慢。要把责任链说清楚，需要追到服务端 Binder 线程：1. 在客户端线程选中等待片段，记录等待开始时间、结束时间、`blocked_function` 和调用栈。2. 沿 Perfetto 的 wakeup arrow、Binder transaction slice，或同一时间窗内的 server 进程 Binder 线程跳转到服务端。3. 在服务端线程上拆 `Wall / CPU / thread_state`：`Wall ≈ CPU` 说明服务端代码在执行；Runnable 占比高说明服务端也在等 CPU；Sleep / futex 指向锁或另一个 Binder 对端；D 状态指向存储或内存压力。4. 如果服务端线程本身排队很久，再回到 CPU 区域看是谁占核，避免把系统调度拥塞误写成 system_server 逻辑慢。这条链能区分三类结论：客户端调用太频繁、服务端逻辑慢、系统资源竞争导致服务端也跑不上 CPU。报告里建议把客户端等待片段、服务端线程状态和全局 CPU top 进程放在同一个时间窗里说明。

## 系统级性能回归的排查方法当你怀疑是系统版本升级或厂商 OTA 导致了性能回归时，排查方法需要更加系统化：

## 1. 固定场景 A/B 对比同一台设备（或同型号设备），分别抓取升级前和升级后的 Trace，使用**完全相同的操作步骤和测试数据**。对比同一帧的 `doFrame` 耗时、调度延迟、CPU 频率等关键指标。

## 2. 关注内核调度行为变化系统升级可能更换了调度器配置（比如 EAS 参数、UClamp 限制、绑核策略）。在 Perfetto 中对比升级前后的：- 主线程被调度到哪个核心（大核 vs 小核）- 调度延迟（Runnable 时间）是否增加- CPU 频率上限是否被更严格地限制

## 3. 检查新增的系统服务或后台任务Android 大版本升级往往会引入新的系统服务，或者让既有服务承担新的任务。在 Perfetto 的进程列表中对比升级前后多出来的进程、Binder 服务和后台任务，再看它们的 CPU、内存和 Binder 活动，定位会更稳。

## 快速判断速查表面对一份 Perfetto Trace，可以按这个速查路径快速定位问题归属：| 观察到的现象 | 主要嫌疑方向 | 关键佐证 ||:--|:--|:--|| `doFrame` Wall ≈ CPU，且 CPU 耗时超过帧预算 | App：计算过重 | 火焰图定位热点函数 || `doFrame` Wall >> CPU，差值主要是 Runnable | 系统：调度延迟 | CPU 区域是否满载？哪些进程在占 CPU？ || `doFrame` Wall >> CPU，差值主要是 Sleep (binder) | App 或系统：Binder 对端慢 / 对端也被调度延迟 | 追到服务端 Binder 线程，看 thread_state、CPU 调度和锁/I/O 等待 || `doFrame` Wall >> CPU，差值主要是 D 状态 | 系统：I/O 延迟（可能是内存不足） | 看 kswapd 活跃度、zRAM 使用率、rss_stat 增长进程 || SurfaceFlinger `commit` / `composite` 耗时异常 | 系统：合成瓶颈 | 看 GPU 占用、Layer 数量、FrameTimeline jank 类型，并与同设备基线对比 || 升级后性能普遍下降 | 系统：版本回归 | A/B 对比 Trace || 特定操作才卡，其他时候正常 | App：操作触发 | 对比问题帧和正常帧 |这张速查表综合了多个章节的分析方法（§5.1 调度延迟、§7.3 卡顿分析方法论、§13.6 线程 CPU 状态分析），可以作为日常分析的入口参考。

## 在 Perfetto 中的实操步骤面对一个性能问题，打开 Perfetto 后按以下顺序操作：1. **定位问题帧**：在主线程 Track 上找到 `doFrame` 耗时明显超过帧预算的那一帧。2. **查看 Wall vs CPU**：选中这个 `doFrame` Slice，看 `Wall` 和 `CPU` 的差值。3. **查看 thread_state**：在主线程下方找到 `thread_state` Track，观察这段时间内的状态分布（Running / Runnable / Sleep / D）。4. **追 Binder 对端**：如果 Sleep 来自 Binder，沿 wakeup arrow 或 Binder transaction 追到服务端线程，再看服务端 `thread_state`。5. **查看 CPU 全局状态**：跳到顶部 CPU 区域，看这段时间所有核心的负载情况。是否有空闲核心？主线程是否被调度到了小核？6. **查看频率限制**：在 CPU Frequency Track 看 `scaling_max_freq` 是否被压低。7. **查看内存状态**：搜索 `kswapd`，看它在这段时间是否活跃；再看 `rss_stat` / process memory 轨道和 `lmkd` 事件，确认是否有进程制造内存压力或被杀。8. **查看 SurfaceFlinger**：跳到 SurfaceFlinger 进程，看 `commit`、`composite` 以及旧 trace 中的 `onMessageRefresh` 是否相对基线变长。9. **形成结论**：综合以上信息，判断问题归属——是 App 代码慢，还是系统资源不够。

## 常见误区**误区一："主线程 Runnable 时间长就是系统问题"**不一定。如果你的 App 自己创建了大量后台线程（比如线程池里 50 个并发任务），这些线程和主线程争抢 CPU，导致主线程排不上队——这是 App 内部线程间的资源竞争。系统调度器只是公平地分配 CPU，它不知道哪些线程对你更重要（除非你设置了优先级）。**误区二："系统问题我改不了，不用分析"**即使问题属于系统侧（比如 OEM 的调度策略不合理），你也应该分析清楚并量化影响。原因有三：一是你可以向系统组提供详细的 Trace 分析报告来推动修复；二是你可以在 App 端做防御性优化（减少计算量、异步化），降低对系统资源的依赖；三是在与 OEM 或合作方沟通时，有数据支撑的分析比模糊的"系统卡"有效得多。**误区三："CPU 利用率低就说明没问题"**CPU 利用率低也可能说明有问题——如果你的主线程在 Runnable 状态等了很久，但 CPU 看起来"不满载"，可能是因为调度器在等当前 CPU 空闲而不愿意把线程迁移到另一个空闲核心（Linux 调度器的非严格 work-conserving 行为）。这种情况下，虽然总利用率不高，但对你的线程来说延迟是实实在在的。**误区四："ANR 一定是 App 的问题"**AOSP 默认的 ANR 窗口要按组件类型拆开看，不能压成一个统一数字：| 场景 | 常见默认阈值 | 备注 ||:--|:--|:--|| Input dispatching | 5 秒 | 前台输入无响应最常见 || Service timeout（前台进程） | 20 秒 | `ActiveServices` 前台 service 执行超时 || Service timeout（后台进程） | 200 秒 | 后台 service 窗口更长 || BroadcastReceiver（前台优先级） | 10 秒，Android 14+ 在 CPU 饥饿时可放宽到 20 秒 | 冷启动时间也算在窗口内 || BroadcastReceiver（后台优先级） | 60 秒，Android 14+ 在 CPU 饥饿时可放宽到 120 秒 | `goAsync()` 也算在窗口内 || `startForegroundService()` 后未及时调用 `startForeground()` | Android 8 默认 5 秒；Android 9-12 常见 AOSP 默认 10 秒；Android 13+ 拆成 `fgs_start_foreground_timeout`、`service_start_foreground_timeout_ms` 和 `service_start_foreground_anr_delay_ms` | OEM / DeviceConfig 可能调整具体阈值 |具体值仍以当版 `ActiveServices`、Broadcast 常量和官方 ANR 文档为准。如果主线程被调度延迟阻塞了 3 秒，再加上自身代码耗时 2 秒，总共就超过了 5 秒的 Input ANR 阈值。这种情况下，如果只看 App 代码可能只看到了 2 秒，漏掉了调度延迟的 3 秒。分析 ANR 时要把主线程、Binder 对端、系统负载和组件类型一起看。**误区五："SurfaceFlinger 延迟是 GPU 厂商的问题"**SurfaceFlinger 合成延迟的原因有很多，不一定是 GPU 硬件的问题。常见的原因包括：App 提交了过多或过大的 Layer、HWC 的能力没有充分利用、GPU 被 App 的自定义渲染占用、以及系统内存不足导致 GPU Buffer 分配慢。归因时需要具体分析 SF Track 中的耗时分布。

## 参考资料- [Perfetto CPU Scheduling 官方文档](https://perfetto.dev/docs/data-sources/cpu-scheduling) — CPU 调度数据采集与分析- [Perfetto Thread State 分析](https://perfetto.dev/docs/data-sources/cpu-scheduling#thread-states) — 线程状态详解- [Android Memory allocation 官方文档](https://developer.android.com/topic/performance/memory-management) — kswapd 与 zRAM 机制- [AOSP lmkd 官方文档](https://source.android.com/docs/core/perf/lmkd) — userspace lmkd、PSI 与低内存杀进程策略- [Android Performance 官方指南](https://developer.android.com/topic/performance) — 性能优化最佳实践- [Diagnose and fix ANRs 官方文档](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs) — ANR 类型与超时口径- [Perfetto FrameTimeline 官方文档](https://perfetto.dev/docs/data-sources/frametimeline) — App / SurfaceFlinger jank 归因- [AOSP SurfaceFlinger 源码](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp) — Android 17 tag 下的合成流程源码
---
*本节内容与 §5.1（Linux 进程调度基础）、§7.3（卡顿分析方法论）、§13.6（线程 CPU 状态分析）形成交叉参考体系。建议先掌握 §5.1 中的线程状态和调度延迟概念，再阅读本节进行归因实战。*