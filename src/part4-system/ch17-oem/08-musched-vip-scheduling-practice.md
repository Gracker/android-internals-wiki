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
related_chapters: ["5.1", "5.2", "5.3", "14.23", "17.4", "17.5"]
---

# 17.8 MUSCHED 调度实践：VIP 队列、场景标注与跨进程优先级传播

MUSCHED 是荣耀面向移动交互负载设计的语义感知调度框架。它把 Android 框架知道的场景、关键线程及依赖关系传给内核，在 RT 与普通公平调度之间提供有时间上限的 VIP 服务。项目从 2021 年开始研究，2024 年 1 月进入量产，2026 年 7 月以 OSDI ’26 论文发表。

证据分为三层：

- MUSCHED 架构、参数和实验结果以 OSDI ’26 论文为准。
- 通用 sched_ext 与 Binder 行为以 Android 17 内核锚点 `android17-6.18-2026-06_r6` 为准。
- 论文没有公开 MUSCHED 源码。凡是论文未说明的 struct_ops flags、私有 kfunc、引用计数和固件配置，都不从通用内核能力反推成产品事实。

## 17.8.1 为什么公平调度不足以表达交互紧迫性

120 Hz 的显示周期约为 8.33 ms。一次触控可能唤醒主线程、RenderThread、窗口动画线程、Binder 服务线程及合成相关线程。每个线程只运行很短一段时间，端到端路径却跨越多个进程和同步点。

论文把矛盾概括为三项约束：

1. 高性能核数量少，还受功耗和温度限制。
2. 关键路径包含 Binder、futex、mutex、rwsem 等跨线程依赖。
3. 交互任务突发且 deadline 紧，基于历史负载的 PELT/WALT 可能反应太慢。

直接把大量应用线程设为 `SCHED_FIFO` 或 `SCHED_RR` 风险很高。RT 线程能压制普通线程；优先级或 CPU 亲和性配置失误时，系统服务会饥饿，功耗与温度也会迅速上升。只调低 nice 值同样不够：调用方得到更高 CFS 权重后，锁持有者或远端 Binder 线程仍可能在别的 runqueue、cgroup 中等待。

MUSCHED 选择了一条受限的中间路径：只在用户可见场景中给关键线程临时 VIP 身份，并沿阻塞依赖传播；时间片和累计预算耗尽后，线程回到普通公平调度。

## 17.8.2 用户空间识别语义，内核执行调度

MUSCHED 采用拆分架构。

用户空间负责：

- 识别启动、滑动、动画、窗口切换等场景。
- 根据线程角色、离线 systrace 和 beta 用户 jank trace 生成标注策略。
- 通过 BPF Map 更新每个应用、每种场景的 VIP 候选和生存时间。
- 协调相互冲突的场景策略。

内核侧负责：

- 维护每 CPU 的 VIP 队列。
- 在没有可运行 RT 任务时，先服务 VIP，再服务普通任务。
- 处理 VIP 时间片、累计预算和跨 CPU 均衡。
- 在锁与同步 Binder 依赖上临时传播 VIP 标签。

论文把有效顺序写成 `RT > VIP > CFS`。这里的 VIP 是 MUSCHED 产品策略，不是 upstream Linux 新增的固定 `sched_class`。论文说明它建立在 sched_ext 之上，却没有公开 `struct sched_ext_ops`、`SCX_OPS_SWITCH_PARTIAL` 配置或内核补丁。读者应把“位于 RT 与 CFS 之间”理解为论文描述的运行效果，不能据此宣称 Linux 6.6 或 Android 17 自带 `SCHED_VIP`。

## 17.8.3 对照 Android 17 的 sched_ext

Android 17 内核锚点中的 sched_ext 提供 full-switch 与 partial-switch 两种范围：

| 模式 | Android 17 / 6.18 行为 |
| --- | --- |
| 未设置 `SCX_OPS_SWITCH_PARTIAL` | `SCHED_NORMAL`、`SCHED_BATCH`、`SCHED_IDLE`、`SCHED_EXT` 都交给 BPF 调度器 |
| 设置 `SCX_OPS_SWITCH_PARTIAL` | 只有显式 `SCHED_EXT` 任务进入 BPF 调度器，其余任务留在 fair class |

MUSCHED 论文没有公布它选择哪一种。若用 full-switch，BPF 程序可把普通任务和 VIP 任务放进不同 DSQ；若用 partial-switch，厂商还需要可靠地把候选线程切到 `SCHED_EXT`，并处理它与 fair class 的相对关系。两条路径都需要产品源码才能确认。

Android 17 / 6.18 的 DSQ 语义可解释 MUSCHED 队列为何可行：

- `scx_bpf_create_dsq()` 创建自定义 DSQ。
- `scx_bpf_dsq_insert()` 按 FIFO 插入任务，并写入运行 slice。
- CPU 只从 local DSQ 执行；`scx_bpf_dsq_move_to_local()` 可把自定义 DSQ 的任务移入当前 CPU。
- `SCX_SLICE_DFL` 在该 tag 中仍为 20 ms。MUSCHED 的 3 ms 是论文给出的私有策略值。
- BPF 调度器退出、触发错误或让 runnable 任务停滞过久时，sched_ext 会终止当前策略并把任务送回 fair class。

论文基于 Linux 6.6 的实现描述仍使用 `scx_bpf_dispatch()` 和 `scx_bpf_consume()`。到了 Android 17 / 6.18，对应接口已经演进为 `scx_bpf_dsq_insert()` 和 `scx_bpf_dsq_move_to_local()`。官方文档明确声明 sched_ext 的 ops、常量和 `scx_bpf_*` kfunc 不提供稳定 ABI；厂商升级内核时必须重新适配和回归，不能只迁移 BPF 对象。

## 17.8.4 VIP 队列如何限制抢占范围

论文公开的 VIP 队列规则如下：

- 每 CPU 维护 VIP 队列，队内按 FIFO 服务。
- 单次时间片为 3 ms。
- 时间片用完但累计预算仍有剩余时，任务回到 VIP 队尾。
- 累计预算耗尽后，VIP 标签临时撤销，线程回到普通公平调度。
- cgroup 的 `cpu.share` 默认沿用内核配置。

不同任务类型的累计预算来自代表性负载 profiling：

| 类型 | 论文预算 | 设计说明 |
| --- | ---: | --- |
| Audio | 20 ms | 覆盖典型音频 buffer 处理窗口 |
| Video | 10 ms | 覆盖一次解码与渲染周期 |
| WebView | 120 ms | 页面布局与脚本执行可能跨多帧 |
| Display | 20 ms | 覆盖合成关键工作 |

这些数值属于论文实现，不是 Android API，也不应复制为其他设备的默认配置。刷新率、CPU 拓扑、温控状态和业务场景都会改变合适的预算。论文对恢复条件分别用了 “next enqueue” 与 “next qualifying event” 两种表述，没有给出完整状态机；实现评审时需要核对标签重置事件、超时和任务退出路径。

时间片解决单次连续运行问题，累计预算限制一次场景能消耗多少 VIP CPU 时间。缺少后者时，一批不断重新入队的 VIP 线程仍可能长期压制普通任务。

## 17.8.5 场景标注从哪里来

MUSCHED 用三类信息寻找交互关键线程：

1. Android 中跨应用较稳定的角色，例如主线程、UI 线程、RenderThread、MotionThread，以及处理用户可见请求的 Binder worker。
2. 对启动、滑动和动画反复采集 systrace，分析唤醒关系、线程 CPU 负载和端到端依赖图。
3. 从 beta 用户的 jank trace 中补充实验环境难以覆盖的线程。

论文表 1 给出的示例包括：

| 类型 | 线程名示例 |
| --- | --- |
| Animator | `splashworker`、`wmshell.main`、`wmshell.anim` |
| UI | Main thread、UI thread |
| Render | Render thread |
| WebView | `CrRendererMain`、`Chrome_InProcRe` |

运行时钩子位于 SystemUI、Launcher 动画切换、应用前后台切换、焦点变化和帧渲染回调附近。框架识别出用户交互场景后，给匹配线程加 VIP 标签。

线程名适合辅助匹配，不适合单独充当安全的身份。应用版本、WebView 实现和线程池复用都会改变名称及职责。量产策略还应结合 UID、进程角色、场景窗口和 trace 依赖；撤销条件与打标条件同样需要测试。

## 17.8.6 锁依赖上的优先级传播

只提升等待线程无法缩短锁持有者的 runnable 等待。MUSCHED 对 futex、mutex 和 rwsem 增加两类策略：

- 等待队列中同时出现普通线程和 VIP 线程时，允许 VIP waiter 越过若干非关键 waiter，优先获得唤醒机会。
- VIP waiter 被普通线程持锁阻塞时，把 VIP 标签临时传播给 owner；锁释放、依赖消失或 boost 超过有界生存时间后撤销。

论文描述的实现会在加锁与释放路径记录 owner tid，在 waiter 阻塞时检查依赖并传播。它也明确指出，仅仅持锁不会让普通线程自动成为 VIP。

这一段是 MUSCHED 的厂商实现，不代表 Android 17 的普通 mutex、rwsem 和 futex 已获得相同语义。上游的 rt_mutex/PI futex 有数值优先级继承机制；普通锁的唤醒与公平性规则又各不相同。把它们统一描述成“Linux 所有锁都严格 FIFO”会掩盖自旋、批量唤醒、读写模式和 PI 路径的差异。

工程评审需要覆盖多级锁链、递归依赖、owner 退出、超时、信号中断和一个 owner 同时接收多个 boost 来源。论文没有公开引用计数及环检测实现，因此不能断言它如何解决这些边界。

## 17.8.7 Binder 已有优先级继承，VIP 仍需额外传播

Android 17 Binder 驱动已经处理同步事务的 Linux 调度优先级：

- 创建同步事务时，`t->priority` 记录调用线程的 `policy` 与 `prio`。
- `binder_transaction_priority()` 将事务优先级与 Binder node 的 `min_priority` 比较。
- node 未设置 `inherit_rt` 时，RT 调用方会降为 `SCHED_NORMAL`、nice 0，再用于服务线程。
- 驱动把服务线程原值保存到 `saved_priority`，在回复、失败或线程重新等待工作时调用 `binder_restore_priority()`。

这套机制传播的是内核认识的 policy/prio。MUSCHED 的 VIP 标签保存在它自己的调度状态中，Binder 默认路径不会自动复制这个标签，也不会自动解除跨 cgroup 的 CPU 带宽限制。

论文说明 MUSCHED 会监控同步 Binder transaction：VIP 调用方发起事务后，调度器定位远端 service thread，临时给它加 VIP 标签，处理结束后撤销。论文没有公开它使用 Binder vendor hook、tracepoint、kfunc 还是私有驱动改动，因此不能基于通用设施推测具体 sideband 路径。可确认的范围是功能已由论文说明，但挂点尚未公开。

异步 oneway 事务不等待远端回复，不能照搬同步传播策略。嵌套调用 `A → B → C`、服务线程池复用、事务失败和调用方死亡都需要成对管理 boost；否则会出现标签提前撤销或长时间残留。

## 17.8.8 选核、pull 与 push

MUSCHED 尽量避免 RT 与 VIP、多条 VIP 同核竞争。论文给出的选择顺序是：

1. 空闲且允许该任务运行的 CPU。
2. 没有 RT/VIP 任务的 CPU。
3. 没有 RT 任务、VIP 数量最少的 CPU。

实现章节又说明 `sched_select_cpu` 会扫描 performance cores，优先空闲大核，再选负载较低的大核。两段描述的粒度不同：前者讲冲突规则，后者讲产品 CPU 集合。不能把“大核优先”外推到所有 SoC；CPU capacity、affinity、thermal pressure 和 idle state 都要参与决策。

负载均衡包含两条路径：

- CPU 进入 idle 后，从其他 runqueue 拉任务；优先处理 RT 与 VIP 共存的队列，否则选择 VIP 数量较多的队列。
- tick 检查到当前 CPU 在跑 RT，且某个 VIP 已 runnable 超过 4 ms 时，把该 VIP 推到没有 RT、VIP 较少的可用 CPU。

4 ms 约等于 120 Hz 一帧预算的一半。论文称低于 2 ms 会因常见的 1–2 ms 短暂排队而触发过多迁移；旗舰机可用较低阈值，温度或续航敏感产品可提高阈值。这个参数是产品调优点，不是 sched_ext 常量。

## 17.8.9 正确解读实验结果

实验室环境是荣耀 Magic7、Snapdragon 8 Elite、MagicOS 9、Android 15、Linux 6.6。10 个应用各测试 100 次，论文固定显示模式、温度状态、电池模式、CPU governor 和清缓存流程，并用实际后台业务与 `stress-ng` / `rt-app` 注入竞争。

| 实验室指标 | 论文结果 |
| --- | ---: |
| 10 个应用平均冷启动时间 | 下降 14.8% |
| 冷启动时间标准差 | 下降 24.25% |
| 全部 VIP 任务 sleep 时间 | 下降 71.8% |
| 全部 VIP 任务 runnable 时间 | 下降 52.6% |
| PiP 视频通话并发的四个前台场景 | 响应延迟下降 9.8%–22.8% |

运行开销测试中，短视频播放的平均 context-switch 延迟保持 5 μs，pick-next-task 从 2 μs 增至 3 μs。120 FPS 游戏的平均帧率从 119.76 变为 119.69，最差掉帧数从 4 变为 3，归一化电流从 726.62 mA 变为 718.16 mA。单组结果只能说明论文测试条件下没有观察到明显回退，不能证明所有设备和负载都无开销。

量产数据覆盖 2024 年 1 月起的 2000 万台以上荣耀设备，包含旗舰和中端、MediaTek 与 Qualcomm 平台。论文以每千小时异常次数统计：

| 场景 | 异常定义 | Baseline | MUSCHED | 改善 |
| --- | --- | ---: | ---: | ---: |
| Animation | 连续掉帧超过 50 ms | 27.2 | 20.4 | 25.0% |
| Swipe | 连续掉帧超过 50 ms | 10.5 | 6.8 | 35.7% |
| Startup | 冷启动超过 2 s | 94.5 | 65.5 | 30.7% |

正式论文没有“触控到显示延迟最高降低 31%”或“消除 92% 掉帧”的结论，不能继续引用旧二手材料中的这两项数字。量产表由系统作者提供，论文未公开设备分层、实验分桶与置信区间；阅读时应把它视为大规模产品证据，同时保留对实验设计透明度的限制说明。

## 17.8.10 量产实现暴露出的成本

论文披露了几项容易被架构图隐藏的工作：

- Android 当时的 `bpfloader` 不支持 sched_ext 所需的 `BPF_MAP_TYPE_STRUCT_OPS`，团队扩展了启动加载流程。
- struct_ops map 更新受限，MUSCHED 没有在运行中卸载 sched_ext program，而是用 `BPF_F_LINK` 驱动 `INIT`、`INUSE`、`TOBEFREE`、`READY` 状态切换。
- eBPF verifier 不允许无界循环和动态内存分配，栈限制为 512 字节。复杂调度逻辑被封装进厂商 kfunc，eBPF 更接近轻量控制面。
- 论文团队实现了类似 `memcpy` 的 BPF kfunc 来修改内核数据结构。这属于厂商信任边界，不能当作通用 BPF 程序应有的能力。
- 高度优化的游戏收益有限；论文测试的大型 MOBA 中，帧率和帧时间波动没有显著改善，电流与机身温度还略有变差。

这些经验解释了“有 sched_ext”与“能量产移动调度器”之间的距离。内核 tag 升级还会遇到 sched_ext ABI 变化、BTF/kfunc 白名单、SELinux、启动加载、watchdog 回退和 SoC 拓扑适配。

## 17.8.11 与 ADPF、Game Mode 的关系

MUSCHED、ADPF 和 Game Mode 处在不同控制层：

| 机制 | 输入 | 主要控制 |
| --- | --- | --- |
| MUSCHED | OEM 场景标注、线程依赖 | runqueue 顺序、选核、临时优先级传播 |
| ADPF Performance Hint Session | App 报告的工作周期与目标时长 | 由设备策略调节 CPU 性能及相关资源 |
| Game Mode / GameManager | 用户或游戏选择的模式 | OEM 定义的性能、续航及游戏策略 |

普通 App 没有 MUSCHED VIP SDK。应用应使用公开的 ADPF、Game Mode、线程与帧时间 API，并减少主线程阻塞。某台设备同时启用多种 OEM 策略时，它们对频率、亲和性、nice、uclamp 和 VIP 标签的合并顺序由固件决定；缺少实机 trace 时，不能声称 VIP 必定覆盖 Game Mode。

OEM 调度团队则需要联合观察：

- `sched_switch`、`sched_wakeup`、CPU frequency、idle 与 thermal pressure。
- 每个 VIP 的来源、预算、撤销原因和 runnable delay。
- Binder transaction 与锁依赖传播的开始、结束、超时和嵌套深度。
- sched_ext watchdog、fallback 次数及 BPF policy 版本。
- 启动、动画和滑动端到端指标，以及功耗与温度。

每个 boost 都应回答三个问题：谁触发、为何仍然有效、何时撤销。只统计“VIP 命中率”无法发现标签残留、错误依赖传播和普通任务饥饿。

## 17.8.12 Android 17 迁移检查表

把 Linux 6.6 上的 MUSCHED 思路迁到 `android17-6.18-2026-06_r6` 时，至少要复查：

- 旧 `scx_bpf_dispatch()` / `scx_bpf_consume()` 到 DSQ insert/move API 的改动。
- full-switch 或 partial-switch 的任务覆盖范围与回退行为。
- 每 CPU DSQ、CPU hotplug、cpuset、affinity 和隔离 CPU。
- 3 ms slice 与 4 ms runnable 阈值在新 SoC、刷新率和 thermal pressure 下是否仍合适。
- Binder 同步、嵌套、失败、oneway 与线程池复用的标签生命周期。
- futex、mutex、rwsem 的 owner 追踪与内核版本差异。
- BPF loader、struct_ops、BTF、kfunc、SELinux 与启动时加载限制。
- watchdog 触发后回到 fair class 时，用户空间状态能否同步清理。

MUSCHED 的价值在于展示了一套完整的产品方法：框架提供交互语义，sched_ext 执行可更新策略，依赖传播缩短关键线程等待，时间预算与回退保护系统。它不是 Android 17 的默认能力，也没有公开代码可供逐行复现。阅读论文时应同时保留产品结果与证据边界。

## 参考资料

- [OSDI ’26 论文介绍：Surviving the Impossible Trinity](https://www.usenix.org/conference/osdi26/presentation/xiao)
- [OSDI ’26 论文 PDF](https://www.usenix.org/system/files/osdi26-xiao.pdf)
- [Android 17 / 6.18 sched_ext 文档](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/scheduler/sched-ext.rst)
- [Android 17 / 6.18 `kernel/sched/ext.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/ext.c)
- [Android 17 / 6.18 `include/linux/sched/ext.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/sched/ext.h)
- [Android 17 / 6.18 Binder driver](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder.c)
