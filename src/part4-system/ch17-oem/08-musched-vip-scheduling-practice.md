---
title: "MUSCHED 调度实践：VIP 队列、场景标注与跨进程优先级传播"
chapter: "17.8"
section: "17.8"
status: ready-for-review
drafted_date: "2026-06-09"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
last_verified: "2026-06-09"
last_verified_against: "Linux sched_ext documentation, Android common android16-6.12 kernel/sched/ext.c, Binder driver binder.c, AOSP frameworks/base"
confidence: medium
created_by: "task2a-knowledge-gap"
created_date: "2026-06-09"
gap_source: "Clippings参考书/Chinasys2026论文/社区热点"
gap_score:
  素材丰富度: 3
  与全书目标相关性: 5
  读者需求度: 4
  时效性: 5
  total: 17
material_count: 2
sources:
  - type: research
    path: "Clippings/Chinasys2026：荣耀MUSCHED在移动设备中的调度优化.md"
    note: "[结构参考: 论文分析文，提供 MUSCHED 整体架构和参数体系]"
  - type: research
    path: "DeepResearch/荣耀 MUSCHED 的 VIP 与 Binder 优先级传递深度调研.md"
    note: "[技术验证: 基于 upstream Linux/AOSP 源码反推 MUSCHED 实现路径]"
  - type: upstream-linux
    path: "Linux Documentation/scheduler/sched-ext.rst"
  - type: aosp
    path: "Android common android16-6.12 kernel/sched/ext.c"
  - type: aosp
    path: "Android common android16-6.12 drivers/android/binder.c"
tags: ["sched-ext", "eBPF", "VIP调度", "OEM优化", "荣耀", "优先级传播", "Binder", "场景感知", "sched_ext"]
related_chapters: ["5.1", "5.2", "5.3", "14.10", "17.4", "17.5"]
---

# 17.8 MUSCHED 调度实践：VIP 队列、场景标注与跨进程优先级传播

本节分析荣耀在 Chinasys 2026 发表的 MUSCHED 调度器实践。MUSCHED 基于 Linux `sched_ext` 框架（见 17.4 节），在 RT 与 CFS 之间插入了一层 VIP 调度队列，并实现了场景感知的线程标注和跨进程优先级传播。截至 2026 年 5 月，MUSCHED 已在荣耀 2000 万+ 设备上部署。

读者读完本节能带走三件事：VIP 调度类在 `sched_ext` 内部的工程实现方式、Binder 和锁路径上的优先级传播机制、以及哪些结论经过了上游源码验证、哪些来自论文数据尚未公开验证。

## 问题：120Hz 交互帧的调度压力

120Hz 屏幕每帧预算 8.3ms。触控事件到达后，Vsync deadline 之前要完成输入处理、布局计算、渲染指令提交、GPU 执行和合成显示。这条路径上任何一个环节的 runnable 等待超过一两毫秒，就可能错过 deadline 掉帧。

两个因素让这个问题在传统调度框架下难以解决。

**交互帧的工作负载是突发的。** 一次触控会在几毫秒内激活 UI 线程、RenderThread、动画线程、Binder 调用链。这些线程生命周期短、延迟敏感，但 Linux CFS/EEVDF 调度器不区分"渲染关键帧的 UI 线程"和"后台在做日志上传的 worker"——它们都是普通任务，按虚拟时间公平轮转。

**用 RT 解决会引入副作用。** 把 UI 线程和 RenderThread 设为 `SCHED_FIFO` 或 `SCHED_RR` 可以保证它们优先运行，但 Android 在异构 CPU 上做过实验：官方记录过 `sys.use_fifo_ui` 开启后约 30% 的应用启动性能下降，原因是 RT 线程在部分平台上缺乏 capacity awareness，会被调度到小核，反而拖慢前台。RT 级别的线程数量一多，系统锁死和功耗暴增的风险也大幅上升。

[已验证: Android 官方对 `sys.use_fifo_ui` 的实验记录和副作用说明；120Hz 帧预算 8.3ms 为计算值]

还有两条跨线程/跨进程的阻塞路径，传统调度器不处理：

- **锁等待队列的 FIFO 唤醒。** Linux 互斥锁（mutex、rwsem）的等待队列按先进先出顺序唤醒。VIP 线程等锁时，如果前面排着几个非关键的后台线程，要等它们逐个唤醒并释放才能轮到。
- **Binder IPC 同步调用中的服务侧优先级。** 应用前台线程发起同步 Binder 调用（比如向 SurfaceFlinger 提交 buffer），如果服务侧处理线程的调度优先级低，调用方就阻塞在等待回复上。上游 Binder 有优先级继承机制（见下文），但继承的是 Linux 原生的 policy/prio，不认识厂商自定义的调度语义标签。

[已验证: Linux mutex/rwsem FIFO 唤醒语义；AOSP Binder `binder_transaction_priority()` 的优先级继承机制]

## MUSCHED 架构：sched_ext 内部的分层队列

MUSCHED 基于 Linux 6.12 的 `sched_ext` 框架。17.4 节已覆盖 `sched_ext` 的基础机制（`struct sched_ext_ops` 回调表、DSQ 分发队列、BPF Map 状态管理），这里不再重复。本节只讲 MUSCHED 在这个框架上做了什么。

### full-switch 模式下的内部层级

MUSCHED 大概率采用 full-switch 模式——即不设置 `SCX_OPS_SWITCH_PARTIAL`，让所有 `SCHED_NORMAL`/`SCHED_BATCH`/`SCHED_IDLE` 任务统一切入 `sched_ext`。在 `sched_ext` 内部，MUSCHED 再用自定义 DSQ 把任务分成两层：VIP 队列和普通队列。RT 调度类仍留在 Linux 原生的 RT/DL 调度器，不受 BPF 调度器管理。

从系统效果看，三层优先级关系是：RT > VIP > 普通。但这个"VIP"不是 upstream Linux 新增的 `sched_class`。它是 `sched_ext` full-switch 模式下，BPF 调度器自己维护的内部层级。在调度类序上，`sched_ext` class 的优先级低于 fair class（CFS/EEVDF），所以 partial-switch 模式下无法在 RT 和 CFS 之间插入一层。full-switch 模式下，所有普通任务都进了 `sched_ext`，BPF 调度器可以自由定义内部队列优先级，这才让"RT 之下、普通之上"的效果成立。

[已验证: Linux sched_ext `SCX_OPS_SWITCH_PARTIAL` 语义；`sched_ext` class 优先级与 fair class 的关系；full-switch 模式下 BPF 调度器可自定义 DSQ 层级]

### 两种 BPF Map

MUSCHED 用两类 BPF Map 维护调度器状态：

- **`cpu_contexts`**：`BPF_MAP_TYPE_PERCPU_ARRAY`，per-CPU 存储。内容包括该 CPU 的空闲时间、当前负载、已入队任务数量、挂起/休眠状态。每个 CPU 独立一份，eBPF 程序访问时隐式拿到当前 CPU 的那份值，不需要加锁。
- **`task_contexts`**：`BPF_MAP_TYPE_TASK_STORAGE`，per-task 存储。内容包括任务权重、执行状态、计算负载、入队出队时间戳，以及 VIP 标签和 VIP 来源 refcount。任务退出时条目自动清理。

[已验证: `BPF_MAP_TYPE_PERCPU_ARRAY` 和 `BPF_MAP_TYPE_TASK_STORAGE` 是 Linux upstream 提供的 BPF Map 类型；适用场景与描述一致。具体字段名和含义来自论文数据，未直接从公开源码验证]

### 每个 CPU 独立的 VIP DSQ

MUSCHED 用 `scx_bpf_create_dsq()` 为每个 CPU 核心创建一个独立的 VIP 分发队列（DSQ）。任务被标记为 VIP 后，在 `ops.enqueue()` 中进入该 CPU 的 VIP DSQ；`ops.dispatch()` 总是先从 VIP DSQ 取任务发给 local DSQ，VIP DSQ 空了再从普通队列取。

这个设计把 VIP 和普通任务的调度顺序在 DSQ 层面分开，不依赖 Linux 原生的 nice 值或调度策略。

[已验证: `scx_bpf_create_dsq()` 是 Linux sched_ext API；per-CPU DSQ 创建和 dispatch 优先级逻辑符合 sched_ext 设计]

## VIP 队列的约束机制

VIP 队列有两个约束维度：时间片和限制时间。

**时间片：** 每个 VIP 任务每次最多运行 3ms。时间片耗尽但限制时间未用完时，任务被重新插到 VIP 队列末尾，等下一轮调度。

**限制时间：** 按任务类型设置不同的累计运行上限：

| 任务类型 | 限制时间 |
|----------|----------|
| WebView | 120ms |
| 音频 | 20ms |
| 显示 | 20ms |
| 视频 | 10ms |

时间片和限制时间同时耗尽时，VIP 标签暂时移除，任务降级为普通优先级。下一次 `enqueue()` 时 VIP 标签恢复。这个机制的目的是防止 VIP 任务长期占据 CPU 资源饿死普通任务。

VIP 队列的调度顺序是 FIFO——先入队的先出队。和 CFS/EEVDF 的虚拟时间公平轮转不同，VIP 队列不关心任务的历史运行时间，只关心进入顺序和剩余额度。

[待验证: 3ms 时间片、10/20/120ms 限制时间等具体参数来自 Chinasys 2026 论文分析文，未从公开源码或论文原文直接验证。参数值可能因固件版本和平台不同而有差异]

## 场景感知线程标注

MUSCHED 的 VIP 标签不是静态的。它通过 Android 框架关键路径上的函数钩子（function hooks）动态识别和标注关键线程。

### 标注的目标线程类型

论文列出的关键任务类型：

- **动画（Animator）**：属性动画、过渡动画等正在执行的线程
- **UI 线程**：当前前台 Activity 的主线程
- **渲染线程（RenderThread）**：HWUI 的 RenderThread
- **WebView 加载**：WebView 页面加载期间的渲染和布局线程

这些线程类型和 AOSP 已有的 UI-critical 线程识别逻辑一致。Android 官方在 `sys.use_fifo_ui` 实验中就把 UI 线程和 RenderThread 视为最影响交互体验的两个线程，MUSCHED 的 VIP 标注范围覆盖了这两个再加上动画和 WebView。

[已验证: AOSP `sys.use_fifo_ui` 的 UI-critical 线程识别逻辑；RenderThread 和 UI 线程在渲染管线中的角色详见 5.3 节]

### 钩子安装位置

论文提到的框架钩子位置：

- SystemUI 渲染路径
- 启动器（Launcher）动画回调
- 前后台切换（ActivityManager 的进程切换回调）
- 窗口焦点变化
- 帧渲染提交（Choreographer Vsync 回调）

前台进程切换时，钩子检测到 top-app 变化，立即给新 top-app 的 UI 线程和 RenderThread 打上 VIP 标签。标签写入 `task_contexts`（task storage map），BPF 调度器在后续的 `enqueue()` 和 `dispatch()` 中读取。

### 标签泛滥的防护

论文原文的表达是："如果谁都是 VIP，就意味着谁都不是 VIP。"从工程上看，这个防护至少体现在三处：

- 限制时间耗尽后 VIP 标签暂时移除，防止长时间持有
- 只有前台进程的关键线程才打标签，后台任务不进入 VIP 队列
- VIP 队列的时间片（3ms）比普通队列的 `SCX_SLICE_DFL`（20ms）短，即使 VIP 任务密集，每个任务的连续运行时间也有限

[待验证: 具体钩子安装位置和打标条件来自论文分析文，未从 AOSP 或荣耀公开代码直接验证]

## 锁等待与 Binder IPC 优先级传播

VIP 标签只解决本进程内调度优先级的问题。Android 交互帧的关键路径横跨多个进程——UI 线程发起 Binder 调用给 SurfaceFlinger，SurfaceFlinger 持有锁，如果这些阻塞路径上的线程优先级低，VIP 线程还是要等。MUSCHED 的优先级传播机制针对的就是这两条路径。

### 锁等待队列的 VIP 插队

Linux 互斥锁（mutex、rwsem）的默认唤醒顺序是 FIFO。当 VIP 线程和非 VIP 线程同时等同一个锁时，MUSCHED 修改了唤醒逻辑，让 VIP 线程跳过队列前面的非关键线程优先唤醒。

### 锁链优先级传播（Lock-chain Propagation）

VIP 线程等锁时，锁持有者可能是一个普通优先级的后台线程。即使 VIP 线程能优先唤醒，它还是要等锁持有者释放锁。

MUSCHED 的做法：VIP 线程阻塞在锁上时，把 VIP 标签传递给锁持有者。锁持有者临时获得 VIP 调度优先级，加快执行以尽快释放锁。释放后 VIP 标签清除，锁持有者恢复为普通任务。

这条传播路径和 Android Common Kernel 已经公开的 vendor hook 模式高度一致。2023 年的一条 Android Common Kernel 提交在 rtmutex 路径上增加了 `android_vh_task_blocks_on_rtmutex`、`android_vh_rtmutex_waiter_prio` 和 `android_rvh_rtmutex_force_update` 等 vendor hook，目的就是让 OEM 调度器把 "user-aware property"（比如 RenderThread 这类重要 CFS 线程的语义标签）通过 rtmutex 锁链传播给锁持有者。MUSCHED 的锁链传播可以看作这条思路的产品级实现。

[已验证: Android Common Kernel 的 rtmutex vendor hook 提交（`android_vh_task_blocks_on_rtmutex` 等）；rtmutex PI 机制是 Linux upstream 标准功能。MUSCHED 具体是否复用这些 vendor hook 还是自行实现，未从公开代码验证]

### Binder IPC 跨进程 VIP 传播

Binder 路径的传播需要先分清两层。

**第一层：上游 Binder 自带的优先级继承。** AOSP Binder 驱动在处理同步事务时，会自动让服务端线程继承调用方的 Linux 调度策略和优先级。核心逻辑在 `binder_transaction()` → `binder_transaction_priority()` 这条路径：

- 同步事务创建时，`t->priority` 记录调用方当前的 `policy` 和 `prio`
- 选中服务端 Binder 线程后，比较"调用方传来的优先级"和"Binder 节点的最小优先级"（`node->min_priority`），取更高的
- 用 `sched_setscheduler_nocheck()` 或 `set_user_nice()` 提升服务端线程
- 事务完成（回复返回或线程回到 wait-for-work）时，`binder_restore_priority()` 恢复服务端线程的原优先级

这套机制继承的是 Linux 原生的 `sched_policy + prio`。它不认识任何厂商自定义的语义标签，包括 MUSCHED 的 VIP。

[已验证: AOSP Binder `binder_transaction_priority()` 的完整逻辑；`binder_restore_priority()` 的恢复路径；`flat_binder_object` 的 `sched_policy`/`min_priority`/`inherit_rt` 字段]

**第二层：MUSCHED 的 VIP 语义跨进程传播。** VIP 标签是 `sched_ext` 内部通过 task storage 维护的，Binder 驱动不知道它的存在。要让 VIP 语义跨进程传递到服务端线程，MUSCHED 必须有额外的 sideband 逻辑。从公开内核设施反推，有两条可行路径：

1. **纯 eBPF sideband。** Binder 驱动发出 `trace_binder_transaction`、`trace_binder_transaction_received` 等 trace 事件。MUSCHED 的 BPF 程序可以在这些 tracepoint 上挂载逻辑：观察到同步 Binder 事务从 VIP 调用线程发出时，在目标服务端线程的 task storage 里写入一个 `binder_vip_ref`。事务完成后清除。这种方式不修改 Binder 驱动本身。

2. **Vendor hook 扩展。** 在 Binder 驱动的 `binder_transaction_priority()` 路径上加厂商钩子，让 OEM 调度器在优先级继承的同时同步 VIP 语义。这条路径对 Binder 驱动有侵入性，但实现更直接。

无论走哪条路径，VIP 的跨进程传播都需要解决生命周期管理问题。嵌套 Binder 调用（A→B→C）和连续多次交互场景下，VIP boost 的施加和清除必须配对。如果清除不及时，服务端线程在交互结束后仍留在 VIP 层，就会出现 "boost 泄漏"——这比"加速不够"更容易出 bug。上游 Binder 用 `saved_priority` 和 `transaction_stack` 管理恢复语义点，MUSCHED 的 VIP 传播需要同等级别的生命周期追踪，用 refcount 或 reason 标记来聚合多个 VIP 来源（场景标注 + Binder 传播 + 锁链传播），只有全部归零时才真正退回普通队列。

[待验证: MUSCHED 具体采用 eBPF sideband 还是 vendor hook 路径，以及 refcount 生命周期管理的具体实现，均未从公开代码验证。推断基于公开内核设施和工程可行性分析]

## 负载均衡与 CPU 选核

MUSCHED 的 VIP 任务在唤醒和迁移时遵循一套优先级驱动的选核和均衡策略。

### 唤醒时选核

VIP 任务被唤醒时，`ops.select_cpu()` 按以下优先级选择目标 CPU：

1. 当前处于空闲状态的大核（性能核）
2. 没有 RT 也没有 VIP 任务的大核
3. VIP 任务数量最少的大核

选核策略优先大核，因为 VIP 任务（UI 线程、RenderThread）的计算密集度通常需要大核的算力。如果 `select_cpu()` 找到了空闲大核，任务直接插入该 CPU 的 local DSQ，跳过 `enqueue()` 回调。

### Pull：CPU 空闲时拉取

CPU 进入空闲状态后，调度器遍历其他非空闲 CPU 的队列，优先拉取同时包含 RT 和 VIP 任务的队列中的 VIP 任务。如果没有这样的队列，拉取 VIP 任务最多的队列。拉取通过 `scx_bpf_consume()` 完成。

### Push：Tick 检查时迁移

每次 CPU Tick，调度器检查当前 CPU 上的 VIP 任务是否有等待超过 4ms 的。如果有，且当前 CPU 正在运行 RT 任务，就为该 VIP 任务寻找一个"没有 RT 任务且 VIP 最少"的目标 CPU，主动迁移过去。

Push 机制的触发条件说明了设计意图：RT 和 VIP 不应长期共存在同一个 CPU 上。RT 的调度优先级高于 VIP，如果 RT 任务持续运行，同 CPU 的 VIP 任务会被饿死。Tick 检查 4ms 阈值是在"迁移开销"和"VIP 等待时间"之间取的工程平衡。

### 跨核窃取

CPU 本地 VIP 队列为空时，通过 `scx_bpf_consume()` 窃取相邻核心 VIP DSQ 中的任务。这是 `sched_ext` 标准的 DSQ 消费机制，MUSCHED 把窃取范围限定在 VIP DSQ。

[待验证: 4ms push 阈值和具体选核优先级来自论文分析文。选核策略的工程逻辑符合 sched_ext `select_cpu()` 和 DSQ 分发的设计]

## 冷启动场景实测

论文用冷启动作为压力测试场景。冷启动过程中，系统从零创建进程、初始化运行时、构建第一个 Activity，会瞬间触发 300+ 线程创建、数百 MB 到数 GB 内存分配、密集 I/O。UI、渲染、动画、网络加载、图层合成和 Binder 线程同时激活，是 VIP 调度的典型压力场景。

### 骁龙 8 Gen 4 + Android 15 平台

论文报告的关键指标：

- 触控到显示延迟（touch-to-display latency）最高降低 31%
- 120Hz 模式下消除了 92% 的掉帧（frame drops）

### 荣耀 Magic 7 冷启动对比

在荣耀 Magic 7 上对 10 个常见 App 做了冷启动对比（有/无 MUSCHED），从三个维度观察：

- 冷启动时间
- D 状态（uninterruptible sleep）时长
- Runnable 状态时长

### 产品部署数据

在 2000 万+ 设备的部署中，动画（Animation）、滑动（Swipe）、启动（Startup）场景的异常延迟都有下降。

[待验证: 31% 延迟降低、92% 掉帧消除、具体 App 冷启动耗时对比数据来自 Chinasys 2026 论文。论文原文截至 2026-06-09 未公开 PDF，数据来自第三方分析文，等论文正式发表后需补充具体测试条件和方法论]

## MUSCHED 的工程边界

分析 MUSCHED 时需要守住几条边界，避免把厂商实验写成 Android 通用机制。

### 不是新的 Linux 调度类

VIP 是 `sched_ext` full-switch 模式下的内部分层，不是 Linux 内核新增的 `sched_class`。这个区分影响很大：如果 MUSCHED 的 BPF 调度器卸载或出错，系统回退到默认 CFS，VIP 层不存在了。`sched_ext` 的容错和自动回退路径正是它适合做量产实验的原因。

### 优先级传播不是 AOSP 默认行为

Binder 的 Linux policy/prio 继承是上游标准行为。但 VIP 语义的跨进程传播需要额外的 sideband 逻辑（eBPF tracepoint 或 vendor hook），这一层不在 AOSP 默认路径上。其他厂商即使也用 `sched_ext`，也不一定做了相同的事。

### 数据的适用范围

论文测试平台是骁龙 8 Gen 4 + Android 15 和荣耀 Magic 7。不同 SoC（天玑、Exynos）、不同调度器配置、不同 Android 版本上的效果可能不同。具体参数（3ms 时间片、4ms push 阈值等）是工程调优结果，不是通用最优值。

### 与 17.4 节的关系

17.4 节覆盖了 `sched_ext` 框架本身、`struct sched_ext_ops` 的回调机制、DSQ 分发模型和 OPPO `hmbird_sched` 的公开线索。本节（17.8）是 17.4 的下游应用案例，用荣耀 MUSCHED 展示了 OEM 在 `sched_ext` 上可以做到什么程度。两者的共同边界：都是 vendor kernel 层面的实现，AOSP 默认系统不加载任何 BPF 调度器。

## 扩展

### MUSCHED vs 通用 sched_ext 示例调度器

Linux `tools/sched_ext/` 提供了 `scx_simple`、`scx_rusty` 等示例调度器。它们展示了 `sched_ext` API 的基本用法，但没有场景感知标注、VIP 队列约束、跨进程优先级传播这些产品化逻辑。MUSCHED 的 VIP 类是否可复用到其他 OEM 平台，取决于 VIP 标注逻辑（Android 框架钩子）能否跨厂商移植。sched_ext API 本身是通用的，但框架钩子的安装位置和打标策略需要针对各厂商的系统服务差异做适配。

[待补充: sched_ext API 稳定性与内核版本依赖的详细分析]

### MUSCHED 与 ADPF/Game Mode 的互补关系

MUSCHED 的场景感知在内核层面识别关键线程并提升调度优先级。ADPF（Adaptive Performance Framework，见 5.9 节）在框架层面通过 Hint Session 告知系统 CPU/GPU 的性能需求。两者不冲突：MUSCHED 解决"关键线程在 CPU 调度层面的排队顺序"，ADPF 解决"CPU/GPU 频率是否足够"。Game Mode 的线程优先级设置（见 17.5 节）和 MUSCHED 的 VIP 标签是独立的两个机制——Game Mode 通过 Android framework 设置线程优先级，MUSCHED 在内核层面覆盖调度策略。当两者同时生效时，VIP 标签的调度优先级高于 Game Mode 设置的 nice 值。

[待验证: MUSCHED 和 ADPF/Game Mode 同时生效时的优先级关系需要实机验证]

### 其他 OEM sched_ext 实践对比

OPPO `hmbird_sched`（见 17.4 节）是目前公开线索最多的另一个 OEM sched_ext 实践。它与 MUSCHED 的对比维度：

| 维度 | MUSCHED | hmbird_sched |
|------|---------|-------------|
| VIP 层级 | VIP 队列 + 类型化限制时间 | 未公开完整策略 |
| 场景感知 | Android 框架钩子动态标注 | procfs 运行时参数控制 |
| 优先级传播 | Binder + 锁链传播 | 未公开 |
| 跨核窃取 | VIP DSQ 级别窃取 | 未公开 |
| 公开程度 | 论文描述了架构，无代码 | proc 控制面源码公开 |

不同 SoC（骁龙/天玑/Exynos）的 CPU 拓扑和能效模型差异，会影响 VIP 选核策略中大核/小核的划分。MUSCHED 论文的测试平台是骁龙 8 Gen 4，在异构大小核布局上的选核逻辑可能需要针对天玑和 Exynos 的核心配置做调整。

[待补充: 其他 OEM 的 sched_ext 部署策略对比，等更多公开材料]

## 参考资料

- [结构参考: Chinasys2026 论文分析, Clippings/Chinasys2026：荣耀MUSCHED在移动设备中的调度优化.md]
- [技术验证: 荣耀 MUSCHED VIP 与 Binder 优先级传递深度调研, DeepResearch/荣耀 MUSCHED 的 VIP 与 Binder 优先级传递深度调研.md]
- [已验证: Linux sched_ext 官方文档, Documentation/scheduler/sched-ext.rst]
- [已验证: Linux sched_ext API, kernel/sched/ext.c (torvalds/master + Android common 6.12)]
- [已验证: AOSP Binder 优先级继承, drivers/android/binder.c]
- [已验证: Android Common Kernel rtmutex vendor hooks (android_vh_task_blocks_on_rtmutex 等)]
- [已验证: AOSP sys.use_fifo_ui 实验记录]
- [待验证: MUSCHED 论文原文 PDF（截至 2026-06-09 未公开），具体参数和测试数据需等论文正式发表后补充]
