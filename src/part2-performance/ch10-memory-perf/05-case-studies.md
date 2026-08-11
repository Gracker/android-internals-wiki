---
title: "案例集"
chapter: "10.5"
section: "10.5"
drafted_date: "2026-04-02"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-31"
last_verified_against: "AOSP android-17.0.0_r1（ComponentCallbacks2.java、RenderProperties.h、RenderNode.cpp、ProfilingTrigger.java、lmkd.cpp）; Android Common Kernel android17-6.18-2026-06_r6（mm/vmscan.c、include/trace/events/vmscan.h）; Android Developers ProfilingManager/ProfilingTrigger 与 heapprofd 文档"
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
  - type: aosp
    path: "frameworks/base/core/java/android/content/ComponentCallbacks2.java"
  - type: aosp
    path: "frameworks/base/libs/hwui/RenderProperties.h"
  - type: aosp
    path: "frameworks/base/libs/hwui/RenderNode.cpp"
  - type: aosp
    path: "packages/modules/Profiling/framework/java/android/os/ProfilingTrigger.java"
  - type: aosp
    path: "system/memory/lmkd/lmkd.cpp"
  - type: kernel
    path: "mm/vmscan.c@android17-6.18-2026-06_r6"
  - type: kernel
    path: "include/trace/events/vmscan.h@android17-6.18-2026-06_r6"
tags: ['case-study', 'memory-leak', 'native-memory', 'low-memory', 'oom', 'cache', 'gc']
polish_count: 1
polish_date: "2026-04-09"
polish_by: "task2b-polish"
related_chapters: ["10.1", "10.2", "10.3", "10.4", "10.6"]
last_task6_audit: "2026-06-08"
review_notes: "2026-04-30 task6 revisiting review: pass-light-edit。修复1处禁用词(意味着)。无B类大问题。评分: 结构5/5·措辞4/5·一致性4/5·验证3/5·元数据4/5。 | 2026-05-07 Task9 01:20：pass-tech-review。无 P0/P1，Task6 已通过且 queue 无 pending，自动晋升 finalized。P2：ProfilingTrigger API37 版本边界、案例效果量化占位仍建议补。"
task9_reviewed_date: "2026-07-10"
task2b_state: fixed
task2b_result: fixed
rework_fixed_at: "2026-05-06T21:43:37+08:00"
task2b_rework_date: "2026-04-30"
task2b_fixed_at: "2026-04-30T01:40:00+08:00"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-07-10T00:27:54+08:00"
task9_result: "pass-tech-review"
last_task9_audit: "2026-07-09"
last_task9_audit_at: "2026-07-09T15:27:48+08:00"
last_task9_audit_log: "logs/deep-review/2026-07-09-15-audit.md"
last_task9_audit_result: "auto-fixed"
last_task2b_verifier_at: "2026-05-27T03:37:00+08:00"
task2b_verifier_result: "ready-for-task6"
last_task9_review_log: "logs/deep-review/2026-07-10-00-deep-review.md"
last_task9_autofix_at: "2026-07-09"
task9_review_notes: "2026-05-27 Task9 05:28：auto-fixed。修正案例四 ProfilingManager / ProfilingTrigger API 35/36/36.1/37 版本边界：API35 为 app-driven requestProfiling，API36 起提供 trigger 注册，API37 OOM trigger 是事后 Java heap dump，不能替代业务侧内存突增阈值探针。回到 Task6 复审。 | 2026-05-27 07:24 Task9 deep-review：pass-tech-review。复核 lmkd/PSI、ComponentCallbacks2、HWUI alpha layer、ProfilingManager/ProfilingTrigger 版本边界，无 P0/P1；既有效果量化占位保留为 P2，Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-07-09 Task9 idle-audit AUTO-FIX：P0 1 / P1 0 / P2 0。将 ComponentCallbacks2、HWUI alpha 自动建层、ProfilingTrigger 的源码锚点从 android-16.0.0_r1 收敛到 android-17.0.0_r1；View.java 参考改为直接锚定 RenderProperties.h；回到 Task6 复审。详见 logs/deep-review/2026-07-09-15-audit.md。 | 2026-07-09 21:30 Task9 deep-review AUTO-FIX：按 AOSP android-17.0.0_r1 的 RenderProperties::promotedToLayer / RenderNode::pushLayerUpdate 修正源码参考句，避免把 alpha 自动建层误写成纯 Shader 级处理；回到 Task6 复审。 | 2026-07-10 00:27 Task9 deep-review：pass-tech-review。复核 ComponentCallbacks2 API34+ trim level、HWUI alpha 自动建层、ProfilingTrigger API37 触发器与 lmkd/PSI 口径，无新增 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。"
status: "finalized"
pipeline_stage: "ready-to-publish"
reviewed_by: openclaw-task6
reviewed_date: 2026-07-09
task6_result: pass-light-edit
task6_state: reviewed
task6_reviewed_date: 2026-07-09
task6_reviewed_by: openclaw-task6
last_task6_at: 2026-07-09T23:13:00+08:00
last_task6_review_log: "logs/review/2026-05-27-07-review.md"
review_type: "task6-writing-quality-review"
task9_state: "reviewed"
task6_review_notes: "2026-05-27 Task6 05:14：pass-light-edit。L1/L2 小修 6 处（去第一人称、删除虚假引导语）。无新增 L3/L4 回炉；既有效果量化占位按待补充/P2 保留。Task9 未重新通过，未自动晋升 finalized。 | 2026-05-27 07:11 Task6：pass-light-edit。Task9 修正 ProfilingManager / ProfilingTrigger 版本边界后复审通过；L1/L2 未发现新增问题；既有效果量化占位按待补充/P2 保留。Task9 为 auto-fixed，未满足自动晋升 finalized 的 pass-tech-review 条件，送 Task9 复审。 | 2026-07-09 23:13 Task6 revisiting review: pass-light-edit。Task9 auto-fix (RenderProperties::promotedToLayer / RenderNode::pushLayerUpdate 源码锚点修正) 写作质量复审通过。L1/L2 无新增问题（对齐×2 为技术术语 page alignment 非禁用词）。既有效果量化占位 [待补充] 按待补充/P2 保留。task9_result=auto-fixed 未满足自动晋升条件，送 Task9 复审。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-10
updated_by: "openclaw-task9"
updated_date: "2026-07-10"
verifier_checked: 2026-07-09
auto_promoted_by: "openclaw-task9"
auto_promoted_date: "2026-07-10"
---
# 10.5 案例集

这一节复核四个公开案例。每个数字都来自原文所述环境，用于还原取证过程，不宜直接写进其他产品的阈值或收益目标。Android 平台机制以 `android-17.0.0_r1` 为当前锚点；回收内核以 `android17-6.18-2026-06_r6` 为当前锚点。旧设备案例保留原系统、ABI 和驱动条件。

| 案例 | 主要内存域 | 决定性证据 | 原文公布的结果 |
| --- | --- | --- | --- |
| 低内存导致冷启动退化 | 系统回收、文件页、I/O | 主线程 D 状态时长、`kswapd0`、进程杀起记录 | 原文未公布参数调整后的 A/B 数据 |
| 线上 Hprof 归因 Java OOM | Java 堆 | 支配树、Retained Size、GC Root 路径 | Helo 与美篇均有双月数据，口径见案例二 |
| PowerVR `renderD128` 映射增长 | GPU 用户态驱动、虚拟地址空间 | `syscall(__NR_mmap2)`、`KEGLGetPoolBuffers`、buffer pool 阈值 | 受影响机型实验的 OOM 崩溃率下降近 50% |
| MemoryThrashing 差分采样 | 原案例为 iOS Objective-C 对象 | 连续样本间的 alloc/dealloc 与存活实例差值 | 发布时处于测试环境监控，未公布线上 OOM 降幅 |

## 案例一：低内存把冷启动拖进 Block I/O

### 现象与数据边界

历史文章对比了低内存与正常内存下的冷启动 trace。低内存样本的 Running 时间为 682 ms，正常样本为 624 ms；两者的 CPU 执行时间接近。差距集中在主线程不可中断睡眠：低内存样本的 `Uninterruptible Sleep | WakeKill - Block I/O` 与普通 Uninterruptible Sleep 合计约 750 ms，正常样本约 130 ms。正常样本从启动到首帧约 1.22 s。

这些数字只描述该次 trace。单看总启动耗时，很容易把问题归到主线程代码；线程状态已经给出另一条线索：额外时间主要花在等待内核和存储路径。

### 证据如何闭合

诊断需要把四类时间对齐：

1. 在 Perfetto 中圈出启动区间，比较主线程 Running、Runnable、Sleeping 与 D 状态。
2. 展开 D 状态对应的内核调用栈，确认是否等待文件页、块设备或文件系统锁。
3. 同时间窗检查 `kswapd0`、内存回收 tracepoint、`meminfo`、`vmstat`、swap/ZRAM 和 PSI。
4. 检查 `lmkd` 与 ActivityManager 事件，确认是否存在同一进程短时间内反复被杀、又被业务或系统拉起。

`mm/vmscan.c` 中的回收路径解释了 `kswapd` 与直接回收的执行位置，`include/trace/events/vmscan.h` 提供回收 tracepoint 定义。Android 17 的 `lmkd.cpp` 使用 PSI 监视器感知 stall，并结合进程重要性和内存状态选择牺牲进程。两部分要放在同一时间轴上观察：回收忙碌、前台线程 D 状态和杀进程记录同时出现，才足以支持“系统内存压力拖慢前台”的判断。

### 根因判断

该案例的证据支持三段因果关系：

- 内存水位偏低时，后台回收更活跃，文件页更容易被回收。
- 启动读取 odex、资源或配置时发生缺页，主线程等待存储 I/O，D 状态时长增加。
- 缓存进程反复杀起会继续消耗 CPU、I/O 与内存，使压力时间窗延长。

主线程与 `kswapd0` 同核运行可能增加竞争，但一次 trace 中的同核现象还不足以证明调度策略存在缺陷。分析报告应分别列出“trace 直接观察到的事实”和“基于内核机制的解释”。

### 修复与验证

原文给出了调高 `extra_free_kbytes` 等历史建议。它们不能直接迁移到 Android 17 产品：内核回收参数、ZRAM、存储延迟、PSI 阈值和 `lmkd` 策略互相影响，单项调大也可能带来更多后台回收或更高的进程重启率。

系统侧修复应以同场景 A/B 为准：

- 对比压力前后的 PSI `some/full`、direct reclaim、`kswapd` CPU、major fault 和块 I/O 延迟。
- 核对 `lmkd` 每次选择的进程、释放量及后续重启，消除无收益的杀起循环。
- 分设备内存档位校准回收、ZRAM 与杀进程策略，并用前台帧时间、启动耗时和后台存活率共同验收。

App 侧可在 `TRIM_MEMORY_UI_HIDDEN` 或 `TRIM_MEMORY_BACKGROUND` 到来时释放可重建缓存。Android 14（API 34）起，`TRIM_MEMORY_RUNNING_*`、`MODERATE`、`COMPLETE` 不再投递；Android 15（API 35）又将相关常量标为 deprecated。App 无法依靠旧 trim level 推断实时系统压力，也不应在每次回调中同步执行大规模清理。

原文没有给出参数调整后的量化结果。复用这个案例时，可引用 trace 前后的 750 ms 与 130 ms，不能补写不存在的修复收益。

## 案例二：用线上 Hprof 找到 Java OOM 的持有者

### 现象

Java OOM 常落在 Bitmap 分配、字符串构造或数组扩容等位置。该位置只表示本次分配失败，无法回答“此前的堆被谁长期占用”。字节跳动 Client Infra 的公开案例采用线上 Hprof 快照，将崩溃点归因转为对象持有关系归因。

### 采集与分析

公开方案由客户端采集、服务端恢复与自动分析组成：

- 客户端可在 OOM 或可配置的高水位采集 Hprof，使用子进程减轻 dump 对交互线程的影响。
- Tailor 在 native 层裁剪字符串内容、Bitmap 像素等分析无需保留的数据。原文公布的头条样本平均文件大小从 355 MB 降至 44 MB。
- 服务端重建引用图和支配树，计算 Shallow Size、Retained Size 与 GC Root 路径，再按泄漏类、持有业务代码或大对象类聚合。
- 混淆后的类名和引用路径经 Retrace 还原，问题才能分派给代码所有者。

线上 Hprof 可能包含账号、文本和业务对象。采集前要有用户授权与合规评审，上传链路需要加密、限流、访问审计和过期删除。裁掉字符串内容并不能自动覆盖所有敏感字段。

### 根因证据

原文展示的类大对象样本中，`ArticleCell` 有 364 个实例，总 Retained Size 为 51.29 MB，其中 280 个由 `MainActivity` 持有。该数据把排查点从 OOM 栈移到 `MainActivity` 的引用所有权。

修复动作要服从引用语义：

- 页面退出后仍被任务、监听器或容器持有时，取消任务、解除注册并清理页面所有者。
- 数量符合业务需求但 Retained Size 过大时，减少单对象负载或限制集合容量。
- 缓存需要保留时，明确容量、失效条件与低内存行为；`WeakHashMap` 只弱持有 key，无法代替缓存策略。
- Android 8.0（API 26）起 Bitmap 像素位于 native heap。生命周期正常的 Bitmap 通常交给 GC 与 `NativeAllocationRegistry` 管理；不要把批量调用 `Bitmap.recycle()` 写成通用修复。显式提前回收还可能让仍在绘制的调用方访问已释放像素。

修复后应重放同一场景并再次 dump，验证实例数量、GC Root 路径与 Retained Size 同时下降。只看 Java heap 的峰值下降，无法区分引用修复、采样时机变化和 GC 调度差异。

### 原文结果与 Android 17 增量

原文公布了两组产品数据：

- Helo 在一个双月内处理了 80% 以上的 Java OOM 问题，次日留存增长 2% 以上。
- 美篇在一个双月内 Java OOM 降低 80%，用户卡顿率也下降 80%。

这些是来源文章中的平台客户数据，不能推导出任意 App 接入 Hprof 后会获得同等收益。文章没有披露完整实验设计，也没有把收益分摊到某个缓存改动。

Android 17（API 37）的 `ProfilingTrigger.TRIGGER_TYPE_OOM` 可在 OOM 时请求 Java heap dump。App 安装自定义 `UncaughtExceptionHandler` 后，仍须调用默认 handler，否则 OOM trigger 不会生效。`TRIGGER_TYPE_ANOMALY` 可由系统异常检测触发相应 artifact。两类触发均受系统限流，结果也可能为空；它们补充采集入口，引用图、隐私处理、聚合和修复验证仍由诊断系统完成。

## 案例三：PowerVR buffer pool 长期保留 `renderD128` 映射

### 环境与复现

原案例集中在华为 Android 10、联发科芯片、PowerVR GPU 与 32 位 `armeabi-v7a` 进程，少量样本覆盖 Android 8.1、9、11 和 12。OOM 发生时，`/dev/dri/renderD128` 映射接近 1 GB，32 位进程的虚拟地址空间被大量占用。

团队在华为畅享 10e（Android 10）做了对照实验：新增 10 个普通背景 View 时映射无明显变化；给新增 View 设置 `alpha=0.5` 后，每个 View 对应的 `renderD128` 映射约增加 25 MB。这是特定设备、驱动和复现工程的数据，不能外推到其他 GPU。

### 从缺失的 Hook 记录找到映射入口

常见 `mmap`、`mmap64`、`mremap`、`__mmap2` 代理没有记录到这批映射，`ioctl` 记录也无法解释增长。继续反汇编 vendor 库后，团队发现 `libsrv_um.so` 直接调用 `syscall`，系统调用号对应 32 位 ARM 的 `mmap2`。

随后只代理 `libsrv_um.so` 与 `gralloc.mt6765.so` 对 `syscall` 的调用，映射记录出现。这个证据修正了“映射完全发生在内核驱动内部”的早期猜测：PowerVR 用户态库绕过了 libc 的 `mmap` 符号，直接进入系统调用。

调用栈继续指向 `libIMGegl.so` 的 `KEGLGetPoolBuffers`。一次增长会连续调用五次 `PVRSRVAcquireCPUMapping`，五类 buffer 合计约 25 MB，与 View 实验的增量吻合。绘制结束时 `KEGLReleasePoolBuffers` 只把 buffer 标为空闲，没有对应调用 `PVRSRVReleaseCPUMapping`。这些映射可在 EGL surface 或 `CanvasContext` 销毁路径释放，因此文章将其定性为 buffer pool 长期保留，不是“任何时候都无法释放”的永久泄漏。

### 根因与历史修复

反汇编显示 pool 为每类 buffer 设置 `buffer_limits`。测试设备原值为 50，映射峰值约 1.25～1.3 GB；调为 20 时峰值约 530 MB，调为 10 时约 269 MB。团队针对已识别的 vendor 版本修改该阈值。来源文章公布的受影响机型实验中，OOM 崩溃率下降近 50%，观察期间未再发生由 `renderD128` 引起的发版熔断。

这是针对封闭 vendor 实现的历史干预，不能作为通用 App 方案。其他厂商、驱动版本或进程位数可能使用完全不同的 pool 数据结构；错误 Hook 私有函数也可能破坏正在使用的 GPU 资源。

产品侧更稳妥的处理顺序是：

- 先按设备型号、SoC、GPU、OS、驱动与 ABI 聚类，确认问题只落在窄设备组。
- 监控 `/proc/self/maps` 或 smaps 中 `renderD128` 映射，区分虚拟地址耗尽与物理驻留增长。
- 在受影响设备上减少可稳定触发增长的渲染组合，必要时对动画或复杂效果做定向降级。
- 推进 64 位进程可缓解 32 位地址空间耗尽，但不会减少 buffer 的物理内存成本。
- 将复现工程、映射增长曲线和 vendor 调用栈交给 SoC、GPU 或 ROM 厂商修复。

### Android 17 源码边界

Android 17 HWUI 的 `RenderProperties::promotedToLayer()` 会在 alpha 位于 `(0, 1)` 且节点报告 overlapping rendering 时把节点提升为 layer；`RenderNode::pushLayerUpdate()` 负责创建或更新对应 layer。该源码能解释 alpha 组合为何可能进入额外的 layer 路径，不能证明 Android 10 的 PowerVR pool 行为仍存在于 Android 17。

`hasOverlappingRendering()` 返回 `false` 只适合内容没有重叠混合的自定义 View。错误返回可能改变视觉结果。`LAYER_TYPE_NONE` 也不是关闭 alpha 自动提升的开关。渲染优化应以 Frame Timeline、GPU 内存和画面对比共同验收。

## 案例四：保留 MemoryThrashing 的差分思路与平台边界

### 原案例运行在 iOS

MemoryThrashing 原文来自抖音直播 iOS 团队。实现通过 Objective-C Runtime Hook `alloc`、`dealloc`，统计各 Class 的分配、释放和存活实例数；它没有使用 Android 的 `Runtime.totalMemory()`、Java heap 或 ART 分配接口。

工具按多个时间点采样，对相邻样本做对象数量差分，定位两类异常：

- **驻留堆积**：原文样本在两个采样周期之间新增 234,024 个对象，样本末仍有 238,800 个 `LivexxxBigDataRead` 实例，占用 10.9 MB。
- **临时对象洪峰**：开播特效识别人脸后频繁创建轮廓模型；小于 5 秒的采样周期内，临时对象增量峰值约 60,000，累计分配超过百万次。

第二类对象可能很快释放，却会抬高 CPU 与 allocator 压力；第一类需要继续查询引用关系，区分业务保留、缓存超限和泄漏。对象数量差分只能告诉工程师“哪类对象增长”，不能独立回答“谁在持有”。

原文明确列出限制：只覆盖 Objective-C 对象、不能分析多个内存区、没有完整引用图，Hook 还会影响方法缓存。文章发布时工具已部署到测试环境，线上部署仍在规划中，因此没有可引用的线上 OOM 降幅或定位耗时改善数据。

### Android 上如何复用

Android 侧可保留“连续样本差分 + 异常时加深采集”的设计，采集器必须按内存域选择：

| 内存域 | 轻量信号 | 深入证据 |
| --- | --- | --- |
| Java/Kotlin 对象 | heap 使用量、GC 次数与停顿、受控场景的对象分配样本 | Java heap dump、实例数差分、GC Root 路径 |
| Native malloc | RSS/PSS 分区、`anon:libc_malloc`、分配速率 | heapprofd 调用栈与分配生命周期 |
| 图形缓冲区 | dmabuf、GPU 驱动映射、Surface 数量 | `dmabuf_dump`、smaps、Perfetto graphics 轨道、厂商工具 |
| 文件映射与线程栈 | maps 分类、线程数、地址空间余量 | smaps、线程创建栈、映射调用栈 |

业务探针只采集总 PSS 时，Java 临时对象、native buffer 与 GPU 映射会混在一条曲线上。更可靠的报警条件由“场景 + 内存域 + 增长速率 + 回落情况”组成，阈值从设备档位和同场景分位数得到，不写死来源不明的时间与容量数值。

Android 15（API 35）提供 app-driven `ProfilingManager.requestProfiling()`。Android 16（API 36）加入触发器注册。Android 17（API 37）增加 OOM、anomaly 和 cold-start 等 trigger。OOM trigger 发生在 OOM 时，用于申请 Java heap dump，无法替代 OOM 前的突增探针。采集结果受限流和系统策略约束，线上设计仍要允许“触发后没有 artifact”。

当差分指出某一类实例异常增长时，再采集 heap dump 或 allocation profile；当增长落在 native 或 graphics 域时，切换到 heapprofd、smaps 或图形工具。这样既保留 MemoryThrashing 的低成本发现能力，也避免把 iOS Runtime 实现误写成 Android 方案。

## 四个案例共同说明什么

### OOM 栈回答不了历史占用

OOM 栈记录失败的分配点。Java Hprof 的 Retained Size、native 分配调用栈、GPU 映射来源和进程地址空间分布，才能说明此前的内存去了哪里。

### 同一条“内存上涨”曲线可能属于不同机制

Java 引用泄漏、短命对象洪峰、malloc 堆积、GPU pool、文件映射和系统回收压力需要不同证据。排查入口应从 `dumpsys meminfo`、smaps 和 Perfetto 建立内存域分类，再进入专用工具。

### 发布数字要保留实验上下文

80%、近 50%、355 MB 到 44 MB 都是来源文章在特定产品、周期或设备上的数据。文章复用这些数字时，应同时写明产品、周期、设备或指标口径。缺少结果数据的案例保持空白结论，比补一个“明显改善”更可靠。

### 驱动与 ROM 问题先做设备聚类

当问题集中在一个 SoC、GPU、OS 与 ABI 组合时，聚类本身就是证据。通用代码修改可能扩大回归面；窄设备复现、定向规避和厂商修复更适合此类故障。

## 复盘清单

- 现象对应 Java heap、native heap、graphics、mmap、线程栈还是整机压力？
- 效果数字来自本项目实验、公开案例，还是尚未验证的预期？
- 低内存 trace 是否同时包含线程状态、回收、PSI、I/O 与 `lmkd` 事件？
- Hprof 是否记录 Retained Size、GC Root 路径、版本和场景？
- 32 位 OOM 是否先检查地址空间余量，而不是只看 RSS？
- vendor 故障是否按设备、SoC、GPU、驱动、OS 和 ABI 聚类？
- 突增探针是否按内存域采样，并为缺失 artifact 设计回退路径？
- 修复后是否重放同一场景，比较同口径的峰值、回落速度、帧时间和崩溃率？

## 相关章节

- **10.1 App 内存分析**：内存域分类、`dumpsys meminfo`、smaps、Perfetto 与 heapprofd。
- **10.2 内存泄漏**：引用所有权、GC Root 与生命周期修复。
- **10.3 内存持续增长**：泄漏、缓存、pool 和地址空间增长的区分。
- **10.4 低内存对系统性能的影响**：回收、PSI、`lmkd`、ZRAM 与前台性能。
- **10.6 内存抖动与频繁 GC**：分配速率、GC 停顿和短命对象。
- **10.7 GPU 与图形内存统计**：DMA-BUF、GPU 映射与图形缓冲区。
- **4.4 Low Memory Killer**：Android 17 userspace `lmkd` 路径。
- **7.4 典型场景分析**：从线程状态和关键路径解释卡顿。

## 参考资料

- [Android 中的卡顿丢帧原因概述——低内存篇](https://www.androidperformance.com/2019/09/18/Android-Jank-Due-To-Low-Memory/)
- [字节跳动应用性能监控帮助客户 Java OOM 崩溃率下降 80%](https://mp.weixin.qq.com/s?__biz=Mzg2NTYyMjYxNg==&mid=2247486007&idx=1)
- [抖音 renderD128 系统级疑难 OOM 分析与解决](https://mp.weixin.qq.com/s?__biz=MzI1MzYzMjE0MQ==&mid=2247514363&idx=1)
- [MemoryThrashing：抖音直播解决内存抖动实践](https://mp.weixin.qq.com/s?__biz=MzI1MzYzMjE0MQ==&mid=2247496677)
- [Android Developers：内存管理概览](https://developer.android.com/topic/performance/memory-overview)
- [Android Developers：ProfilingManager](https://developer.android.com/reference/android/os/ProfilingManager)
- [Android Developers：ProfilingTrigger](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [Perfetto：heapprofd](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [AOSP `ComponentCallbacks2.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/ComponentCallbacks2.java)
- [AOSP `RenderProperties.h`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/RenderProperties.h)
- [AOSP `RenderNode.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/RenderNode.cpp)
- [AOSP `ProfilingTrigger.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java)
- [AOSP `lmkd.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/lmkd.cpp)
- [Android Common Kernel `mm/vmscan.c`（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/vmscan.c)
- [Android Common Kernel `vmscan.h` tracepoints（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/vmscan.h)
