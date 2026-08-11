---
title: "产品侧内存预取与 lmkd 边界"
chapter: "4.17"
status: ready-for-review
applicable_versions: "Android 16 (API 35) - Android 17 (API 37)"
tags: ['LMKD', 'AppFlow', '内存管理', '兼容性', '冷启动']
related_chapters: ['4.4', '4.13', '4.16']
created_by: "task2a-knowledge-gap"
created_date: "2026-07-01"
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

`android-17.0.0_r1` 中没有 `AppFlowManager`、`AppFlowState`、`AppFlowMemoryAllocator`、`MemoryLimiterCompat` 或 `lmkd_appflow_compat.xml`。AOSP lmkd 也没有 AppFlow 会话、冷启动内存预分配协议、两阶段提交或状态回滚接口。

**AppFlow** 在这里指厂商或产品侧可能存在的冷启动优化模块。此类外部模块接入 Android 17 时必须遵守 AOSP 边界，设计建议也不代表 AOSP 类或平台 API。

## 1. 进程重要性的数据流

Android 17 中，与冷启动进程保护直接相关的是 framework 进程状态和 `oom_score_adj`：

```text
Activity / Service / Provider 等状态变化
  → OomAdjuster 计算 proc state、adj 与 capability
  → ProcessList 把 adj 更新发送给 lmkd
  → lmkd 按 oom_score_adj 保存候选
  → 全局内存压力到来后，lmkd 决定是否 kill 以及选择谁
```

应用进入启动和前台状态时，framework 已会根据真实依赖关系提高其重要性。lmkd 只消费结果，不参与 Activity 启动事务，也不会替 AppFlow 提高 Linux 调度优先级或预留内存。

这条边界带来三个约束：

1. AppFlow 不能直接伪造 `/proc/<pid>/oom_score_adj`。绕过 OomAdjuster 会让 framework、lmkd、kernel OOM 和 dumpsys 看到不一致的进程重要性。
2. AppFlow 不能把“即将启动”长期伪装成前台状态。错误保护会把内存压力转移给其他进程，增加后台重启与系统抖动。
3. 启动结束、失败、超时和用户取消都要由 AppFlow 自己收敛资源；lmkd 没有 AppFlow session，也不会替它回滚。

## 2. lmkd 控制协议能做什么

framework 与 lmkd 通过本地 `SOCK_SEQPACKET` 控制 socket 通信。与进程优先级直接相关的命令包括：

- `LMK_PROCPRIO`：更新一个进程的 pid、uid、`oom_score_adj`、进程类型等字段；
- `LMK_PROCS_PRIO`：为共享同一 adj 的多个进程批量更新；
- `LMK_PROCREMOVE`：移除进程记录。

Android 17 中 `LMK_PROCS_PRIO` 的命令编号是 11。每个 packet 最多包含 3 条记录，因为控制包上限为 16 个 `int`：1 个命令字加 3 组、每组 5 个字段。

批量命令减少 socket write 和 daemon 收包次数。它没有以下语义：

- 不通过 io_uring 发送；
- 不支持一次 32 个进程；
- 不构成事务或两阶段提交；
- 不携带冷启动 session、预分配大小或回滚 token；
- 不允许 AppFlow 要求 lmkd 暂停 kill。

因此，产品侧模块无需新增 “AppFlow → lmkd” 私有协议。让 OomAdjuster 根据真实进程状态计算 adj，再沿现有控制面更新，兼容性风险更低。

## 3. PSI 是系统压力信号，不保存 AppFlow 状态

Android 17 lmkd 通过 `libpsi` 打开全局 `/proc/pressure/memory` 并注册 trigger。默认 new strategy 使用：

| 档位 | PSI 类型 | 普通设备默认值 | low-RAM 默认值 |
| --- | --- | ---: | ---: |
| medium | `some` | 70ms / 1s | 200ms / 1s |
| critical | `full` | 700ms / 1s | 700ms / 1s |

PSI trigger fd 的生命周期由打开它的进程管理；关闭 fd 后内核删除 trigger。`memory.pressure` 是统计与事件接口，不是持久化文件。`/dev/memcg/memory.pressure` checkpoint、`/data/app-staging/` AppFlow 会话和 PSI 原子状态都没有 AOSP 依据。

PSI 事件只唤醒 lmkd。`__mp_event_psi()` 随后还会读取或计算：

- zone `min/low/high` watermark；
- free swap 与 ZRAM-aware 可换出估算；
- file-backed page cache refault；
- direct reclaim 与 kswapd 状态；
- 候选进程的 adj 和内存重量。

AppFlow 可以把全局 PSI 作为实验观测或取消预取的输入，但不能把它解释为目标 App 自身压力。触发系统压力的进程与最终被杀的进程可能不同。

## 4. 一个外部冷启动模块应怎样设计

### 4.1 权限边界

AppFlow 若运行在普通应用进程，只能管理自己的缓存、线程、I/O 和资源加载。它无权读取大量系统进程状态、改其他进程 adj 或配置 lmkd。

厂商若把模块放进 `system_server`，也应复用现有进程状态控制器，避免建立第二套 adj 真相源。推荐输入包括：

- 明确的启动请求与目标 UID/package；
- ATMS/AMS 已确认的进程或 Activity 状态；
- 可取消的预取任务；
- 产品内定义的内存预算；
- 启动完成、失败、超时、转后台等终止条件。

不推荐把历史使用频率直接换算成永久 adj 保护。历史预测可以决定“是否预取”，进程重要性仍由当前可见性、绑定关系和执行状态决定。

### 4.2 资源预算

预加载会提高 file cache、anonymous RSS、native buffer 或 GPU 资源占用。启动变快与系统留存能力之间需要显式预算。

一个可审计的预算至少包含：

- 每次启动允许新增的 anonymous/native/file-backed 字节数；
- 同时预取的 App 数；
- low-RAM 与普通设备的不同上限；
- PSI、watermark、swap 或前台切换发生时的取消条件；
- 超时后释放资源的责任方；
- 回到基线所需的最长时间。

预算不能用“内存碎片率 25%→12%”这类无定义指标表示。Java/ART heap、native allocator、page cache、DMA-BUF 与物理页外部碎片的定义和测量方法各不相同。

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

这个状态机只约束 AppFlow 自己的工作。它不锁住 lmkd，也不承诺启动进程在期间绝对不会被杀。

## 5. 与 thrashing 的关系

lmkd 的 thrashing 指标来自 `workingset_refault_file` 相对于 file-backed page cache 基线的增长：

```text
thrashing =
    refault 增量 × 100
    ÷ (窗口起点 active_file + inactive_file + 1)
```

`thrashing_limit` 默认每 1 秒窗口重置。某些 kill reason 成功发出 kill 后，动态阈值会按 `thrashing_limit_decay` 降低，使持续抖动更容易再次触发 kill。

这套衰减服务于系统从 page-cache thrashing 中恢复，不是冷启动保护窗口。AppFlow 不能依赖它保护正在启动的进程，也不应为了启动测试修改全局阈值后把结果归因于预取算法。

预取大量文件页可能增加其他工作集的 refault。评估时要同时看目标 App 启动速度和全局 thrashing/kills，防止局部收益由其他 App 的缓存淘汰买单。

## 6. 与 freezer 的边界

Cached App Freezer 根据进程进入 cached 状态安排冻结。`CachedAppOptimizer.freezeAppAsyncInternalLSP()` 在符合条件时先向目标进程发送 `TRIM_MEMORY_BACKGROUND`，再投递延迟冻结消息。

这个回调没有完成确认。AppFlow 不应把 cached/frozen 进程当作可以继续异步预取的执行容器：

- 冻结后线程不能运行；
- Binder 同步事务可能触发临时解冻或异常路径；
- 持有文件页和 anonymous 内存仍占系统资源；
- 进程可以被 lmkd 终止。

目标进入 cached 状态时，产品侧预取任务应取消或转移到拥有明确生命周期的系统组件，并释放仅服务于本次启动预测的资源。

## 7. 与 MemoryLimiter 的边界

Android 17 `MemoryLimiter` 位于 `system_server`，面向符合条件的进程设置 cgroup `memory.high` 与 `memory.swap.max`。它有自己的进程状态映射、检查周期、profiling 与 kill 流程。

MemoryLimiter 没有 `getQuota(packageName)` 这样的 AppFlow 公开接口，也不会向 lmkd 发送“配额转换”。AppFlow 应遵守两点：

1. 不把预取内存从进程计量中隐藏；cgroup 看到的 usage 必须保持完整。
2. 不假设超限前会收到 `onTrimMemory()`。MemoryLimiter 路径没有为目标 App 派发专属 trim。

如果厂商需要让系统启动优化与 MemoryLimiter 共存，应在同一个进程状态与配置体系中评审阈值，明确哪一方拥有配置写权限，并覆盖各种开关组合。不要在应用层再做一套配额仲裁。

## 8. 故障与降级

### 8.1 PSI 初始化失败

userspace lmkd 启动时，`init_psi_monitors()` 失败会让初始化返回错误，daemon 随后由 init 管理其生命周期。源码中没有动态切换到“watermark-only AppFlow 模式”的路径。

旧 in-kernel LMK 兼容路径只在启动时检测到可写的 lowmemorykiller 模块参数后启用。厂商若保留旧模块，需要把它作为单独配置验证。

### 8.2 AppFlow 自身失败

产品侧模块的失败处理应保持简单：

- 取消尚未开始的预取；
- 关闭 fd、映射或缓存引用；
- 不修改或及时撤销模块自己的 task profile；
- 不阻塞 Activity 启动；
- 记录原因和资源回收量；
- 回退到标准 Android 启动路径。

不需要和 lmkd 做分布式回滚。lmkd 继续根据最新 adj 与系统压力独立运行。

## 9. 怎样证明方案有效

38%、73%、52% 等收益数据没有设备、build、样本量、命令或原始数据，不能作为结论。兼容性测试至少包含以下分组。

### 9.1 实验控制

- 同一台设备、同一 build、同一温度与充电状态；
- AppFlow on/off 随机交替；
- 冷启动、温启动、热启动分开统计；
- 每组包含足够重复次数，并报告中位数与 P90/P95；
- 固定后台 App 集合、RAM/ZRAM 配置与网络数据。

### 9.2 指标

| 目标 | 指标 |
| --- | --- |
| 启动 | time to initial/full display、首帧、主线程 runnable/blocked |
| 目标进程内存 | Java/native heap、anon RSS、file RSS、swap、PSS |
| 系统压力 | PSI some/full、watermark、direct reclaim、kswapd |
| 留存代价 | lmkd kill 次数、victim adj、后台重启、warm start 命中 |
| 体验副作用 | jank、输入延迟、I/O wait、温升与能耗 |

### 9.3 证据关联

Perfetto 中先定位启动区间，再对齐：

- framework 的 proc state/adj 变化；
- lmkd 的 `lmk,<pid>,<reason>,<oom_adj>,<min_adj>,<thrashing>` instant event；
- `killinfo` event log；
- PSI、reclaim、调度、I/O 与目标进程内存采样。

只看到目标 App 启动变快还不够。若同一窗口内 cached App 被更多地杀死、PSI 上升或后续 warm start 下降，方案只是把成本转移到了系统其他部分。

## 10. 检查清单

- [ ] 是否明确 AppFlow 是产品/厂商模块，未伪装成 AOSP 类？
- [ ] 是否由 OomAdjuster 保持 proc state 与 adj 的唯一权威来源？
- [ ] 是否没有新增 AppFlow↔lmkd 私有事务协议？
- [ ] 是否给预取设置字节预算、并发上限、取消与超时条件？
- [ ] 是否在 cached/frozen、压力升高和启动失败时释放资源？
- [ ] 是否与 MemoryLimiter 使用一致的进程状态和配置边界？
- [ ] 是否同时评估启动收益与系统级 kill、PSI、后台留存代价？

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

### Kernel：`android17-6.18-2026-06_r6`

- `Documentation/accounting/psi.rst`
- `kernel/sched/psi.c`
- `mm/vmscan.c`
- `mm/workingset.c`

LMKD 的 PSI、thrashing、批量 adj packet 与 kill 决策见 [4.4 系统内存压力与 lmkd](04-lmk.md)，MemoryLimiter 见 [4.13 Android 17 MemoryLimiter](13-android17-memorylimiter.md)。
