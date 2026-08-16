---
title: "产品侧内存预取与 lmkd 边界"
chapter: "4.17"
status: ready-for-review
applicable_versions: "Android 16 (API 35) - Android 17 (API 37)"
tags: ['LMKD', 'AppFlow', '内存管理', '兼容性', '冷启动']
related_chapters: ['4.4', '4.13', '4.16']
last_verified: "2026-07-01"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
pipeline_stage: ready-for-review
task6_state: pending-verification
last_consolidated_at: "2026-08-11"
consolidated_from:
  - "src/part1-fundamentals/ch04-memory/4.04-AppFlow与Android-17-LMKD兼容性方案.md"
sources:
  - type: aosp
    path: "system/memory/lmkd/"
  - type: paper
    path: "PSI 驱动的 Android LMKD 进程杀机制"
  - type: official
    path: "source.android.com/docs/core/perf/lmkd"
---

# 4.17 产品侧内存预取与 lmkd 边界

## 先确认源码边界

`android-17.0.0_r1` 中没有 `AppFlowManager`、`AppFlowState`、`AppFlowMemoryAllocator`、`MemoryLimiterCompat` 或 `lmkd_appflow_compat.xml`。AOSP 的 lmkd 也没有 AppFlow 会话、冷启动内存预分配协议、两阶段提交或状态回滚接口。

本文中的 **AppFlow** 指厂商或产品侧可能存在的冷启动优化模块。此类外部模块接入 Android 17 时必须遵守 AOSP 边界；下文的设计建议也不代表 AOSP 已有同名类或平台 API。

## 1. 进程重要性的数据流

Android 17 中，与冷启动进程保护直接相关的是 Android framework 层维护的进程状态，以及内存紧张时的终止优先级分值 `oom_score_adj`：

```text
Activity / Service / Provider 等状态变化
  → OomAdjuster 计算 proc state、adj 与 capability
  → ProcessList 把 adj 更新发送给 lmkd
  → lmkd 按 oom_score_adj 保存候选
  → 全局内存压力到来后，lmkd 决定是否 kill 以及选择谁
```

应用进入启动和前台状态时，framework 已经会根据真实依赖关系提高其重要性。lmkd 只使用计算结果，不参与 Activity 启动事务，也不会替 AppFlow 提高 Linux 调度优先级或预留内存。

这条边界带来三个约束：

1. AppFlow 不能直接伪造 `/proc/<pid>/oom_score_adj`。绕过 OomAdjuster 会让 framework、lmkd、内核 OOM 机制和 `dumpsys` 看到不一致的进程重要性。
2. AppFlow 不能把“即将启动”长期伪装成前台状态。错误保护会把内存压力转移给其他进程，增加后台重启与系统抖动。
3. 启动结束、失败、超时和用户取消时，AppFlow 都要自行停止任务并释放资源；lmkd 没有 AppFlow 会话，也不会替它回滚状态。

## 2. lmkd 控制协议能做什么

framework 与 lmkd 通过本地 `SOCK_SEQPACKET` 控制套接字通信。这类 Unix 套接字会保留每个消息包的边界。与进程优先级直接相关的命令包括：

- `LMK_PROCPRIO`：更新一个进程的 PID、UID、`oom_score_adj`、进程类型等字段；
- `LMK_PROCS_PRIO`：为共享同一 `adj` 的多个进程批量更新；
- `LMK_PROCREMOVE`：移除进程记录。

Android 17 中，`LMK_PROCS_PRIO` 的命令编号是 11。每个数据包最多包含 3 条记录，因为控制包上限为 16 个 `int`：1 个命令字，加上 3 组各含 5 个字段的记录。

批量命令可以减少套接字写入和守护进程收包次数，但它没有以下语义：

- 不通过异步 I/O 接口 io_uring 发送；
- 不支持一次 32 个进程；
- 不构成事务或两阶段提交；
- 不携带冷启动会话、预分配大小或回滚令牌；
- 不允许 AppFlow 要求 lmkd 暂停终止进程。

因此，产品侧模块无需新增“AppFlow → lmkd”私有协议。让 OomAdjuster 根据真实进程状态计算 `adj`，再沿现有控制接口更新，兼容性风险更低。

## 3. PSI 是系统压力信号，不保存 AppFlow 状态

PSI（Pressure Stall Information，压力停顿信息）统计任务因 CPU、内存或 I/O 资源不足而停顿的时间。Android 17 的 lmkd 通过 `libpsi` 打开全局 `/proc/pressure/memory` 并注册触发器。默认的新策略（new strategy）使用以下阈值：

| 档位 | PSI 类型 | 普通设备默认值 | 低内存设备默认值 |
| --- | --- | ---: | ---: |
| 中等（medium） | `some` | 70 ms / 1 s | 200 ms / 1 s |
| 严重（critical） | `full` | 700 ms / 1 s | 700 ms / 1 s |

PSI 触发器 fd 的生命周期由打开它的进程管理；关闭 fd 后，内核会删除相应触发器。`memory.pressure` 是统计与事件接口，不是持久化文件。所谓 `/dev/memcg/memory.pressure` 检查点、`/data/app-staging/` AppFlow 会话和 PSI 原子状态，都没有 AOSP 依据。

PSI 事件只负责唤醒 lmkd。`__mp_event_psi()` 随后还会读取或计算：

- 内存区域（zone）的 `min/low/high` 水位；
- 空闲交换空间，以及考虑 ZRAM 后的可换出内存估算；
- 文件页缓存重新缺页（refault）；
- 直接回收（direct reclaim）与后台回收线程 `kswapd` 的状态；
- 候选进程的 `adj` 和内存占用量。

AppFlow 可以把全局 PSI 作为实验观测指标或取消预取的输入，但不能把它解释为目标应用自身的压力。触发系统压力的进程与最终被终止的进程可能不同。

## 4. 一个外部冷启动模块应怎样设计

### 4.1 权限边界

AppFlow 如果运行在普通应用进程中，只能管理自己的缓存、线程、I/O 和资源加载。它无权批量读取系统进程状态、修改其他进程的 `adj` 或配置 lmkd。

厂商如果把模块放进 `system_server`，也应复用现有进程状态控制器，避免再建立一套相互冲突的 `adj` 数据源。推荐输入包括：

- 明确的启动请求与目标 UID/包名；
- ActivityTaskManagerService（ATMS）或 AMS 已确认的进程/Activity 状态；
- 可取消的预取任务；
- 产品内明确规定的内存预算；
- 启动完成、失败、超时、转后台等终止条件。

不建议把历史使用频率直接换算成永久的 `adj` 保护。历史预测可以决定“是否预取”，进程重要性仍由当前可见性、绑定关系和执行状态决定。

### 4.2 资源预算

预加载会增加文件页缓存、匿名页 RSS、原生缓冲区或 GPU 资源占用。启动速度与系统保留后台进程的能力之间，需要有明确的预算约束。

一个可审计的预算至少包含：

- 每次启动允许新增的匿名页、原生内存和文件页字节数；
- 同时预取的应用数量；
- 低内存（low-RAM）设备与普通设备各自的上限；
- PSI、内存水位、交换空间或前台切换发生时的取消条件；
- 超时后释放资源的责任方；
- 回到基线所需的最长时间。

预算不能用“内存碎片率从 25% 降到 12%”这类没有定义的指标表示。Java/ART 堆、原生内存分配器、文件页缓存、DMA-BUF 与物理页外部碎片的定义和测量方法各不相同。

### 4.3 建议的产品状态机

下面是产品设计示例，不对应 AOSP 类：

```text
IDLE
  └─ 收到可确认的冷启动请求 → PREPARING

PREPARING
  ├─ 预算允许 → PREFETCHING
  ├─ 压力升高 / 用户取消 / 超时 → ABORTED
  └─ 目标已变成热启动 → IDLE

PREFETCHING
  ├─ framework 确认目标进入启动状态 → LAUNCHING
  └─ 压力升高 / 目标变化 / 失败 → ABORTED

LAUNCHING
  ├─ 首帧与启动完成条件满足 → IDLE
  └─ 失败 / 超时 / 转后台 → ABORTED

ABORTED
  └─ 取消任务并释放模块持有的资源 → IDLE
```

这个状态机只约束 AppFlow 自己的工作。它不会阻塞 lmkd，也不承诺启动进程在此期间一定不会被终止。

## 5. 与反复换页（thrashing）的关系

lmkd 的 thrashing 指标反映文件页被回收后又很快访问、反复调回内存的程度。它根据 `workingset_refault_file` 相对于文件页缓存基线的增长计算：

```text
thrashing =
    refault 增量 × 100
    ÷ (窗口起点 active_file + inactive_file + 1)
```

`thrashing_limit` 默认每个 1 秒窗口重置。在某些终止原因下，lmkd 成功终止进程后，会按 `thrashing_limit_decay` 降低动态阈值，使持续的反复换页更容易再次触发进程终止。

这套衰减用于帮助系统从文件页缓存反复换页中恢复，不是冷启动保护窗口。AppFlow 不能依赖它保护正在启动的进程，也不应为了启动测试而修改全局阈值，再把结果归因于预取算法。

预取大量文件页可能增加其他工作集的重新缺页。评估时要同时查看目标应用的启动速度、全局 thrashing 和进程终止次数，避免用其他应用的缓存淘汰换取局部收益。

## 6. 与进程冻结器的边界

缓存应用冻结器（Cached App Freezer）会在进程进入缓存状态后安排冻结。`CachedAppOptimizer.freezeAppAsyncInternalLSP()` 在符合条件时，先向目标进程发送 `TRIM_MEMORY_BACKGROUND`，再投递延迟冻结消息。

发送方不会等待这个回调处理完成。AppFlow 不应把缓存或已冻结进程当作可以继续异步预取的执行容器：

- 冻结后线程不能运行；
- Binder 同步事务可能触发临时解冻或进入异常路径；
- 进程持有的文件页和匿名内存仍会占用系统资源；
- lmkd 仍然可以终止该进程。

目标进入缓存状态时，产品侧预取任务应当取消，或转移到拥有明确生命周期的系统组件，同时释放仅服务于本次启动预测的资源。

## 7. 与 MemoryLimiter 的边界

Android 17 的 `MemoryLimiter` 位于 `system_server`，为符合条件的进程设置 cgroup `memory.high` 与 `memory.swap.max`。它有自己的进程状态映射、检查周期、性能剖析和进程终止流程。

MemoryLimiter 没有 `getQuota(packageName)` 这样的 AppFlow 公开接口，也不会向 lmkd 发送所谓“配额转换”。AppFlow 应遵守两点：

1. 不把预取内存从进程计量中隐藏；cgroup 统计到的使用量必须保持完整。
2. 不假设超限前一定会收到 `onTrimMemory()`。MemoryLimiter 路径不会为目标应用派发专用的内存整理回调。

如果厂商需要让系统启动优化与 MemoryLimiter 共存，应在同一套进程状态和配置体系中评审阈值，明确哪一方拥有配置写权限，并覆盖各种开关组合。不要在应用层再建立一套配额仲裁机制。

## 8. 故障与降级

### 8.1 PSI 初始化失败

用户空间 lmkd 启动时，如果 `init_psi_monitors()` 失败，初始化会返回错误；之后由 Android init 进程管理 lmkd 的生命周期。源码中没有动态切换到“只看内存水位的 AppFlow 模式”的路径。

旧版内核内 LMK 兼容路径，只会在启动时检测到可写的 lowmemorykiller 模块参数后启用。厂商如果保留旧模块，需要把它作为一套独立配置验证。

### 8.2 AppFlow 自身失败

产品侧模块的失败处理应保持简单：

- 取消尚未开始的预取；
- 关闭 fd、解除映射或释放缓存引用；
- 不修改任务配置文件（task profile），或及时撤销模块自己的修改；
- 不阻塞 Activity 启动；
- 记录原因和资源回收量；
- 回退到标准的 Android 启动路径。

AppFlow 不需要与 lmkd 执行分布式回滚。lmkd 会继续根据最新的 `adj` 和系统压力独立运行。

## 9. 怎样证明方案有效

如果 38%、73%、52% 等收益数据没有同时说明设备、构建版本、样本量、测试命令和原始数据，就不能作为结论。兼容性测试至少要包含以下分组。

### 9.1 实验控制

- 同一台设备、同一构建版本、同一温度与充电状态；
- AppFlow 启用/关闭两组随机交替；
- 冷启动、温启动、热启动分开统计；
- 每组包含足够重复次数，并报告中位数与 P90/P95；
- 固定后台应用集合、RAM/ZRAM 配置与网络数据。

### 9.2 指标

| 目标 | 指标 |
| --- | --- |
| 启动 | 首次/完整显示时间（time to initial/full display）、首帧、主线程可运行/阻塞状态（runnable/blocked） |
| 目标进程内存 | Java/原生堆、匿名 RSS、文件页 RSS、交换空间、PSS |
| 系统压力 | PSI `some`/`full`、内存水位、直接回收、`kswapd` |
| 留存代价 | lmkd 终止次数、被终止进程的 `adj`、后台重启、温启动命中率 |
| 体验副作用 | 卡顿帧（jank）、输入延迟、I/O 等待、温升与能耗 |

### 9.3 证据关联

Perfetto 中先定位启动区间，再对齐：

- framework 的进程状态/`adj` 变化；
- lmkd 的 `lmk,<pid>,<reason>,<oom_adj>,<min_adj>,<thrashing>` 瞬时事件（instant event）；
- `killinfo` 事件日志；
- PSI、内存回收、线程调度、I/O 与目标进程内存采样。

只看到目标应用启动变快还不够。如果同一时间窗口内有更多缓存应用被终止、PSI 上升，或后续温启动命中率下降，说明方案只是把成本转移到了系统其他部分。

## 10. 检查清单

- [ ] 是否明确 AppFlow 是产品/厂商模块，未伪装成 AOSP 类？
- [ ] 是否由 OomAdjuster 作为进程状态与 `adj` 的唯一权威来源？
- [ ] 是否没有新增 AppFlow↔lmkd 私有事务协议？
- [ ] 是否给预取设置字节预算、并发上限、取消与超时条件？
- [ ] 是否在进程进入缓存/冻结状态、压力升高和启动失败时释放资源？
- [ ] 是否与 MemoryLimiter 使用一致的进程状态和配置边界？
- [ ] 是否同时评估启动收益、系统级进程终止、PSI 和后台留存代价？

## 11. 源码索引

### Android 17 / API 37：`android-17.0.0_r1`

- `frameworks/base/services/core/java/com/android/server/am/ProcessList.java`
- `frameworks/base/services/core/java/com/android/server/am/psc/OomAdjuster.java`
- `frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java`
- `frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java`
- `system/memory/lmkd/include/lmkd.h`
- `system/memory/lmkd/lmkd.cpp`
- `system/memory/lmkd/reaper.cpp`
- `system/memory/lmkd/libpsi/psi.cpp`

### Linux 内核：`android17-6.18-2026-06_r6`

- `Documentation/accounting/psi.rst`
- `kernel/sched/psi.c`
- `mm/vmscan.c`
- `mm/workingset.c`

LMKD 的 PSI、thrashing、批量 `adj` 数据包与进程终止决策见 [4.4 系统内存压力与 lmkd](04-lmk.md)，MemoryLimiter 见 [4.13 Android 17 MemoryLimiter](13-android17-memorylimiter.md)。
