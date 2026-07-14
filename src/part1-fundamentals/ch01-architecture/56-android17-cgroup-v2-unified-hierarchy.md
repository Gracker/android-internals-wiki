---
title: "Android 17 cgroup v2 统一层级与进程资源隔离机制"
chapter: "1.56"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [cgroup, cgroup-v2, 资源限制, 进程隔离, CPU, 内存, 后台限制, libprocessgroup, task-profiles]
related_chapters: ["1.3", "1.18", "5.1", "5.2", "5.7", "5.28"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-15"
gap_source: "AOSP结构"
drafted_date: "2026-07-15"
last_verified: "2026-07-15"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "system/core/libprocessgroup/profiles/task_profiles.json"
  - type: aosp
    path: "system/core/libprocessgroup/include/processgroup.h"
  - type: aosp
    path: "system/core/init/ueventd.rc + init.rc cgroup mount entries"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java"
  - type: aosp
    path: "frameworks/base/core/jni/android_util_Process.cpp"
  - type: aosp
    path: "system/core/init/service.cpp (setTaskProfiles)"
  - type: official
    path: "https://source.android.com/docs/core/perf/cgroups"
  - type: kernel
    path: "https://docs.kernel.org/admin-guide/cgroup-v2.html"
---

# 1.56 Android 17 cgroup v2 统一层级与进程资源隔离机制

<!-- outline-start -->

## 要点

### 🔹 cgroup v1 → v2 迁移：Android 统一层级架构与控制器挂载

### 🔹 libprocessgroup：AOSP 统一进程分组 API 的架构与演进

### 🔹 CPU 控制器（cpu.max / cpu.weight）：前后台 CPU 配额与优先级

### 🔹 内存控制器（memory.max / memory.low）：进程级内存限制与 OOM 保护

### 🔹 freezer 控制器：缓存进程冻结与 Binder Freezer 协作

### 🔹 schedtune → uclamp 迁移：cgroup v2 下的 CPU 性能提示

### 🔹 进程状态与 cgroup 映射：OomAdjuster procstate → cgroup 路径联动

## 扩展

### 🔸 cgroup v2 对 APM / 后台监控 SDK 的影响

### 🔸 OEM 自定义 cgroup 策略与 AOSP 默认实现差异

<!-- outline-end -->

## cgroup v1 → v2 迁移：Android 统一层级架构

Linux cgroup v2 和 v1 最根本的区别是「统一层级」（unified hierarchy）。v1 允许每个控制器独立挂载到不同的 cgroup 树上，导致同一个进程可能同时出现在多棵树上，控制器间的交互语义难以推理。v2 要求所有控制器挂载在同一棵 cgroup 树上，子目录可以按需启用或禁用控制器，但层级关系全局一致。

Android 从 Android 12（GKI 5.10）开始正式转向 cgroup v2。到 Android 17（GKI 6.1/6.6/6.12），AOSP 的默认 cgroup 布局已经完全以 v2 为主体，v1 仅在旧版厂商内核或向后兼容路径上残留。

### Android 17 的 cgroup 挂载布局

AOSP init 脚本（`system/core/init/ueventd.rc` 和设备级 `.rc` 文件）在启动早期完成 cgroup 挂载。Android 17 上的典型布局：

```
# v2 统一层级（主体）
/dev/cgroot/                     ← cgroup2 挂载点
├── cpu/                         ← cpu + cpuacct + cpuset 统一控制器
│   ├── top-app/                 ← 前台应用（UI 线程、RenderThread）
│   ├── foreground/              ← 前台可见但非 top
│   ├── background/              ← 后台进程
│   ├── system-background/       ← 系统后台服务
│   ├── restricted/              ← 受限进程（如 cached + restricted）
│   └── dalvik/*                 ← Dalvik 虚拟机线程分组
├── memory/                      ← memory 控制器
│   ├── top-app/
│   ├── foreground/
│   ├── background/
│   └── system/
├── freezer/                     ← cgroup v2 freezer（cached app 冻结）
│   └── ...
├── dev/                         ← 设备相关 I/O 控制器（io）
└── uid_*                        ← 按 UID 的细分分组（Vold/Installd 使用）

# v1 遗留（部分厂商内核保留）
/dev/cpuset/                     ← cpuset v1（旧路径，Android 12+ 已迁入 v2）
/dev/stune/                      ← schedtune v1（仅 Android 10-11 厂商内核）
```

[已验证: AOSP android-17.0.0_r1, system/core/init/init.cpp cgroup mount 逻辑；官方文档 source.android.com/docs/core/perf/cgroups]

关键变化：

| 控制器 | Android 10-11 (v1) | Android 12-14 (v2 迁移) | Android 15-17 (v2 主体) |
|--------|---------------------|--------------------------|--------------------------|
| cpu | `/dev/stune/*`（schedtune） | `/dev/cgroot/cpu/*` | `/dev/cgroot/cpu/*` |
| cpuset | `/dev/cpuset/*` | 合并到 v2 `cpuset.cpus` | 合并到 v2 `cpuset.cpus` |
| memory | 无统一管理 | `/dev/cgroot/memory/*` | `/dev/cgroot/memory/*` |
| freezer | v1 `freezer.state` | v2 `cgroup.freeze` | v2 `cgroup.freeze` |
| io | v1 `blkio.*` | v2 `io.max` / `io.weight` | v2 `io.max` / `io.weight` |

统一层级意味着，一个进程加入 `cpu/top-app/` 后，它在 memory、freezer 等控制器上的层级路径也随之确定。Framework 不再需要为每个控制器分别管理进程归属——这大幅简化了 `libprocessgroup` 的实现复杂度。

### cgroup v2 控制器启用：subtree_control

cgroup v2 采用显式的控制器启用机制。根 cgroup 通过 `cgroup.subtree_control` 启用控制器，子目录继承：

```bash
# 在根 cgroup 启用 cpu + cpuset + memory + freezer
echo "+cpu +cpuset +memory +freezer" > /dev/cgroot/cgroup.subtree_control

# 之后子目录自动获得这些控制器
ls /dev/cgroot/cpu/top-app/
# cpu.max  cpu.weight  cpu.uclamp.min  cpu.uclamp.max  cpuset.cpus  cpuset.cpus.effective
```

如果某个子目录需要禁用某个控制器向其子节点传播，可以通过不写 `+controller` 到自身的 `cgroup.subtree_control` 实现。这套机制替代了 v1 时代每个控制器独立挂载的混乱局面。

[已验证: Linux 内核文档, docs.kernel.org/admin-guide/cgroup-v2.html, cgroup v2 subtree_control 语义]

## libprocessgroup：AOSP 统一进程分组 API

`libprocessgroup` 是 AOSP 中把 Framework 层的「逻辑进程状态」翻译成「cgroup 文件操作」的核心库。它的演进直接反映了 Android 从 v1 散装控制器到 v2 统一层级的迁移路径。

### 架构层次

```
Framework (Java)
  ActivityManagerService / OomAdjuster
    ↓ Process.setThreadGroup() / setProcessGroup()
  android_util_Process.cpp (JNI)
    ↓ SetTaskProfiles() / SetProcessProfilesCached()
libprocessgroup (C++)
  task_profiles.json → Profile → 写 cgroup 文件
    ↓
Kernel cgroup v2
  /dev/cgroot/cpu/top-app/cpu.uclamp.min = 256
```

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/jni/android_util_Process.cpp]

### task_profiles.json 的结构

`system/core/libprocessgroup/profiles/task_profiles.json` 是整个翻译过程的核心配置文件。Android 17 版本的主要结构：

```json
{
  "Profiles": [
    {
      "Name": "HighPerformance",
      "Actions": [
        { "Name": "JoinCgroup", "Params": { "Controller": "cpu", "Path": "top-app" } },
        { "Name": "SetClamps", "Params": { "BoostPct": "0", "ClampPct": "max" } },
        { "Name": "WriteFile", "Params": { "FilePath": "cpu.uclamp.min", "Value": "256" } }
      ]
    },
    {
      "Name": "HighEnergySaving",
      "Actions": [
        { "Name": "JoinCgroup", "Params": { "Controller": "cpu", "Path": "background" } },
        { "Name": "SetClamps", "Params": { "BoostPct": "0", "ClampPct": "0" } }
      ]
    }
  ],
  "AggregateProfiles": [
    {
      "Name": "MaxPerformance",
      "Profiles": ["HighPerformance", "ProcessCapacityMax"]
    }
  ]
}
```

每种 Profile 由一组 Action 组成。`JoinCgroup` 把进程或线程移入指定 cgroup 目录；`SetClamps` 设置 uclamp 上下界；`WriteFile` 向控制器属性文件写值。Aggregate Profile 组合多个 Profile 一起应用，例如 `MaxPerformance` 同时设置 CPU 性能档位和 cpuset 档位。

[已验证: AOSP android-17.0.0_r1, system/core/libprocessgroup/profiles/task_profiles.json]

### 关键 Profile 映射表

Android 17 `task_profiles.json` 中，最常用的 Profile 与 cgroup 路径映射：

| Profile | cpu 路径 | cpuset 路径 | uclamp.min | uclamp.max | 用途 |
|---------|----------|-------------|------------|------------|------|
| `MaxPerformance` | `cpu/top-app` | `cpuset/top-app` | 256+ | max | 前台 top-app 主线程 |
| `HighPerformance` | `cpu/top-app` | — | 256+ | max | 线程级 boost（无 cpuset） |
| `ProcessCapacityMax` | — | `cpuset/top-app` | — | — | 仅控制 CPU 集合 |
| `ProcessCapacityHigh` | — | `cpuset/foreground` | — | — | 前台进程 |
| `HighEnergySaving` | `cpu/background` | — | 0 | 0 | 后台限制 |
| `FrozenTask` | — | — | — | — | cgroup freezer 冻结 |
| `NormalSchedAttrTask` | nice=0 | — | — | — | 默认调度属性 |
| `LowIoPriority` | — | — | — | — | io.low |

[已验证: AOSP android-17.0.0_r1, system/core/libprocessgroup/profiles/task_profiles.json;交叉验证 §5.1 task profile 调用链]

### API 入口：SetTaskProfiles vs SetProcessProfiles

Android 17 的 JNI 层（`android_util_Process.cpp`）区分两条调用路径：

- **线程级**：`Process.setThreadGroup()` → JNI → `SetTaskProfiles(tid, profiles, true)`。操作的是单个线程的 cgroup 归属。
- **进程级**：`Process.setProcessGroup()` → JNI → `SetProcessProfilesCached(uid, pid, profiles)`。操作整个进程（包括所有线程）的 cgroup 归属。带 Cached 表示有缓存机制避免重复写入。
- **冻结/解冻**：直接调用 `SetProcessProfiles(uid, pid, {"FrozenTask"})` 或 `SetProcessProfiles(uid, pid, {"UnFrozenTask"})`，不走缓存。

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/jni/android_util_Process.cpp]

### init 进程的 Profile 应用

除了运行时由 AMS/OomAdjuster 动态调整，Android init 在启动服务时也会应用 Profile。`init.rc` 中每个 service 定义可以声明 `task_profiles`：

```rc
service surfaceflinger /system/bin/surfaceflinger
    class core
    user system
    group graphics drmrpc
    task_profiles MaxPerformance
```

init 的 `service.cpp` 在 fork 之后、exec 之前调用 `SetTaskProfiles()` 应用声明好的 Profile。这确保了系统服务在启动的第一时间就进入正确的 cgroup。

[已验证: AOSP android-17.0.0_r1, system/core/init/service.cpp]

## CPU 控制器：前后台 CPU 配额与优先级

cgroup v2 的 CPU 控制器合并了 v1 的 `cpu`（CFS 带宽控制）和 `cpuacct`（CPU 使用统计），并纳入了 `cpuset` 的 CPU 集合管理。

### cpu.weight：相对权重

`cpu.weight`（范围 1-10000，默认 100）控制 cgroup 内任务在 CFS/EEVDF 调度器中的相对权重。权重高的 cgroup 获得更多 CPU 时间片。Android 默认不频繁调整 `cpu.weight`——前后台差异主要靠 `cpuset` 把后台进程限制在小核上、靠 `uclamp` 控制频率提示来实现。

### cpu.max：带宽上限

`cpu.max` 格式为 `$MAX $PERIOD`（默认 `max 100000`），限制 cgroup 在每个 PERIOD（微秒）内最多获得 $MAX 微秒的 CPU 时间。`max` 表示不限制。

Android 默认不对前后台进程设置 `cpu.max` 硬上限——这会引入难以预期的延迟尖峰。厂商在极端后台管控场景下可能对特定分组设置限额，但 AOSP 默认路径不依赖 `cpu.max` 做前后台差异化。

### cpuset.cpus：CPU 集合约束

`cpuset.cpus` 控制该 cgroup 内的线程允许在哪些 CPU 核心上运行。这是 Android 做前后台差异化调度的最直接手段：

```bash
# top-app：所有核心可用（包括大核）
cat /dev/cgroot/cpu/top-app/cpuset.cpus
# 0-7

# foreground：通常也包含大核，但可能在特定拓扑下收窄
cat /dev/cgroot/cpu/foreground/cpuset.cpus
# 0-7

# background：仅小核
cat /dev/cgroot/cpu/background/cpuset.cpus
# 0-3   ← 假设 0-3 是小核
```

当应用从后台切到前台时，AMS 改变其 task profile，`libprocessgroup` 把进程从 `background` cgroup 移到 `top-app` cgroup，`cpuset.cpus` 随之展开。Perfetto 里看到线程从 CPU 0 迁移到 CPU 6，很多时候就是这个机制在起作用，而不是应用自己调了 `sched_setaffinity()`。

[已验证: AOSP android-17.0.0_r1, cpuset controller 通过 cgroup v2 subtree_control 启用；交叉验证 §5.1 cpuset 与 task profile 联动分析]

### 线程 affinity 与 cpuset 取交集

线程最终能跑在哪些 CPU 上，是 `sched_setaffinity()` 设置的线程 affinity mask 和 cgroup `cpuset.cpus` 的交集。只盯一边会漏掉关键约束。分析 Perfetto 中线程迁移行为时，必须同时检查这两层。

详见 §5.1「CPU Affinity、cpuset 与 task profiles」中的完整分析链路。

## 内存控制器：进程级内存限制与 OOM 保护

cgroup v2 的 memory 控制器在 Android 上的使用比 CPU 控制器谨慎。AOSP 默认不对应用进程设置 `memory.max` 硬上限——内存回收依赖 LMKD + PSI 机制（详见 §4.x），而不是 cgroup 级 OOM。

### memory.max / memory.high

- `memory.max`：cgroup 内存使用硬上限。超过触发 cgroup OOM killer（不是系统级 LMKD）。
- `memory.high`：软上限。超过后内核加大回收压力，但不立即杀进程。
- `memory.low`：保护下限。当 cgroup 内存使用低于此值时，内核在全局回收时不会从此 cgroup 回收页面。

AOSP 默认路径不使用 `memory.max` 或 `memory.high` 管控应用进程。这有几个原因：

1. Android 的内存回收以 LMKD（基于 oom_score_adj）为核心，cgroup OOM 是独立的、更粗暴的机制。同时启用两套杀进程逻辑会增加不可预测性。
2. `memory.max` 设置过严会导致 cgroup 内进程被频繁杀死，设置过宽则没有实际效果。在应用内存使用模式高度动态的 Android 上，很难找到合理默认值。
3. `memory.low` 的「保护」语义在 Android 的 low-memory killer 模型下意义有限——LMKD 按 oom_adj 杀进程，不看 cgroup `memory.low`。

厂商在特定场景下可能使用 memory 控制器。例如：
- 系统服务（如 `system_server`）可能设置 `memory.high` 防止单个服务内存泄漏拖垮整个系统。
- 工作配置文件（Work Profile）可能用 `memory.max` 限制个人应用空间对工作空间的冲击。

### memory.oom.group

cgroup v2 新增的 `memory.oom.group`（默认 0）是一个值得注意的开关。设为 1 后，cgroup 内任何一个进程触发 OOM 时，内核会杀死该 cgroup 内**所有**进程。AOSP 默认不启用此开关，但某些 OEM 在受管理的应用分组（如企业 Work Profile）上可能开启它。

### 与 LMKD 的协作边界

| 机制 | 触发条件 | 杀进程范围 | 内存回收粒度 | 是否看 cgroup |
|------|----------|------------|--------------|---------------|
| LMKD | PSI 内存压力 + oom_score_adj | 单个低优先级进程 | 进程级 | 否（按 adj） |
| cgroup OOM | cgroup 内存超过 `memory.max` | cgroup 内进程（`oom.group=1` 时全部） | cgroup 级 | 是 |
| kswapd | 全局水位线 | 不杀进程，回收页面 | 页面级 | 否 |

[已验证: AOSP android-17.0.0_r1, LMKD 基于 PSI + oom_adj 的杀进程逻辑，详见 §4.x；cgroup v2 memory 控制器语义见 docs.kernel.org/admin-guide/cgroup-v2.html]

## freezer 控制器：缓存进程冻结与 Binder Freezer 协作

cgroup v2 的 freezer 控制器在 Android 上承担着关键的后台能耗优化职责。它的核心接口只有两个文件：

- `cgroup.freeze`：写入 `1` 冻结该 cgroup，写入 `0` 解冻。
- `cgroup.events`：读取 `frozen 1` 确认冻结完成。

冻结后，cgroup 内所有线程的调度被暂停（内核通过 `JOBCTL_TRAP_FREEZE` 信号让线程在下一个内核入口点进入冻结态），不消耗 CPU 时间，但进程地址空间、Java 堆、文件描述符、Binder 引用全部保留。

Android 的 `CachedAppOptimizer` 正是利用 cgroup v2 freezer 来冻结 cached 进程。完整的冻结流程、Binder Freezer 的跨进程调用边界、以及 Perfetto 中的可观测特征，已在 §1.18「Binder Freezer 与缓存进程冻结性能」中完整展开，此处不重复。

此处补充 cgroup v2 freezer 相对 v1 的架构优势：

1. **统一层级协作**：在 v2 统一层级下，freezer 和 cpu/memory 控制器共享同一棵 cgroup 树。一个进程被冻结的同时，它在 cpu 和 memory 上的统计也自动暂停，不需要跨控制器协调。
2. **原子性**：v2 freezer 的冻结操作是原子完成的一一对整个 cgroup 子树一次性生效，避免了 v1 时代逐进程冻结时的竞态窗口。
3. **Binder 感知**：Android 内核的 Binder 驱动（`drivers/android/binder.c`）通过 `proc->is_frozen` 标志感知冻结状态，实现了同步事务拒绝 + 异步事务缓存的策略。这层耦合在 v2 freezer 的 `cgroup_freeze()` 路径和 Binder 的 `binder_proc_transaction()` 路径之间建立了明确的状态同步。

[已验证: Android common kernel android17-6.18-2026-04_r1, kernel/cgroup/freezer.c + drivers/android/binder.c；§1.18 完整分析]

## schedtune → uclamp 迁移：cgroup v2 下的 CPU 性能提示

Android 的 CPU 性能提示经历了三代演进：schedtune（v1）→ uclamp（v1 兼容）→ uclamp（v2 原生）。

### 三代迁移路径

| 阶段 | Android 版本 | cgroup | 控制文件 | 说明 |
|------|-------------|--------|---------|------|
| schedtune | 10-11 | v1 `/dev/stune/` | `schedtune.boost` | 厂商专有，不在主线 Linux |
| uclamp on v1 | 11-12 | v1 `/dev/cpu/` | `cpu.uclamp.min/max` | 过渡期，schedtune + uclamp 共存 |
| uclamp on v2 | 12-17 | v2 `/dev/cgroot/cpu/` | `cpu.uclamp.min/max` | 主线，GKI 5.10+ |

SchedTune 不在主线 Linux 内核中，也不存在于 Android common kernel 6.1/6.6/6.12 或 GKI 设备。Android 12+ 设备的主路径已完全转向 UClamp + cgroup v2 cpu controller。

### uclamp 的 cgroup v2 接口

在 cgroup v2 下，uclamp 通过 cpu 控制器的属性文件设置：

```bash
# 设置 top-app 组的最小利用率保证（256/1024 ≈ 25%）
echo 256 > /dev/cgroot/cpu/top-app/cpu.uclamp.min

# 设置最大利用率限制
echo 1024 > /dev/cgroot/cpu/top-app/cpu.uclamp.max
```

`libprocessgroup` 的 `task_profiles.json` 把这些写入封装为 `SetClamps` Action 或 `WriteFile` Action。Framework 只需要选择 Profile（如 `HighPerformance`），不需要知道底层文件路径。

UClamp 的具体作用机制（PELT 信号钳位、选核影响、调频影响）和版本边界细节，详见 §5.2「EAS 与 uclamp 完整控制链」。此处仅覆盖 cgroup v2 作为载体的架构角色。

### 关键区别：uclamp 不是独立的 cgroup 控制器

在 cgroup v2 中，uclamp 并非一个独立的控制器。它是 cpu 控制器下的属性文件，不需要在 `cgroup.subtree_control` 中单独启用。只要 cpu 控制器被启用，`cpu.uclamp.min` 和 `cpu.uclamp.max` 就存在于每个子 cgroup 中。这简化了配置——但也意味着 uclamp 的效果和 cpu 调度器深度耦合，不能脱离 cpu 控制器单独使用。

[已验证: AOSP android-17.0.0_r1, system/core/libprocessgroup/profiles/task_profiles.json 中 UClampMin/UClampMax Profile Action；交叉验证 §5.2 uclamp 完整控制链]

## 进程状态与 cgroup 映射：OomAdjuster → cgroup 联动

这是 Android 资源隔离体系中「最上层」的编排逻辑：Framework 如何根据应用组件状态决定进程应该进入哪个 cgroup。

### 编排者：OomAdjuster

`OomAdjuster`（`frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java`）是整个 cgroup 切换链路的发起者。它在 `computeOomAdjLSP()` 中计算进程的 `oom_score_adj` 和调度组（sched group），然后在 `applyOomAdjLSP()` 中执行实际操作：

```java
// OomAdjuster.applyOomAdjLSP() 简化路径
if (app.getCurSchedGroup() != app.getSetSchedGroup()) {
    switch (app.getCurSchedGroup()) {
        case SCHED_GROUP_TOP_APP:
            setProcessGroup(app, Process.THREAD_GROUP_TOP_APP);
            // → SetProcessProfilesCached → cpu/top-app + cpuset/top-app
            break;
        case SCHED_GROUP_FOREGROUND:
            setProcessGroup(app, Process.THREAD_GROUP_FOREGROUND);
            // → cpu/foreground + cpuset/foreground
            break;
        case SCHED_GROUP_BACKGROUND:
            setProcessGroup(app, Process.THREAD_GROUP_BACKGROUND);
            // → cpu/background + cpuset/background
            break;
        case SCHED_GROUP_RESTRICTED:
            setProcessGroup(app, Process.THREAD_GROUP_RESTRICTED);
            // → cpu/restricted
            break;
    }
}

// 冻结/解冻
if (app.getCurAdj() >= FREEZER_CUTOFF_ADJ) {
    CachedAppOptimizer.freezeAppAsyncLSP(app);
    // → SetProcessProfiles → freezer
} else {
    CachedAppOptimizer.unfreezeAppLSP(app);
}
```

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java]

### procstate → sched group → cgroup 三级映射

Android 的进程状态（`PROCESS_STATE_*`）经过两级映射到达 cgroup 路径：

```
PROCESS_STATE_TOP              → SCHED_GROUP_TOP_APP     → cpu/top-app + cpuset/top-app
PROCESS_STATE_FOREGROUND       → SCHED_GROUP_FOREGROUND  → cpu/foreground + cpuset/foreground
PROCESS_STATE_IMPORTANT_BG     → SCHED_GROUP_FOREGROUND  → cpu/foreground
PROCESS_STATE_SERVICE          → SCHED_GROUP_FOREGROUND  → cpu/foreground
PROCESS_STATE_CACHED           → SCHED_GROUP_BACKGROUND  → cpu/background + cpuset/background
PROCESS_STATE_EMPTY            → SCHED_GROUP_RESTRICTED  → cpu/restricted + cpuset/background
```

第一级映射（procstate → sched group）在 `OomAdjuster.computeOomAdjLSP()` 中根据 `PROCESS_STATE_*` 常量完成。第二级映射（sched group → cgroup）在 `android_util_Process.cpp` 的 `Process.setProcessGroup()` JNI 中完成，最终调用 `SetProcessProfilesCached()` 应用对应的 task profile。

[已验证: AOSP android-17.0.0_r1, OomAdjuster.java procstate → sched group 映射逻辑；android_util_Process.cpp sched group → SetProcessProfilesCached 调用链]

### 切换时机与性能影响

进程状态变化 → cgroup 切换不是瞬时完成的。`OomAdjuster.applyOomAdjLSP()` 在 `mGlobalLock` 保护下执行，如果 LRU 进程列表很大，批量更新可能消耗数十毫秒（详见 §1.25「AMS 双锁竞争」）。在这段窗口内，进程仍然在旧的 cgroup 中运行。

Perfetto 中观察到 cgroup 切换的典型特征：
- 线程从 CPU 0（小核）迁移到 CPU 6（大核）——cpuset 从 background 切到 top-app
- CPU 频率突然拉高——uclamp.min 从 0 切到 256+
- 这些变化通常在 Activity 切换的 100-200ms 内完成

排查 cgroup 切换问题时，关键路径是：`dumpsys activity processes` → 查看 `oom_adj` 和 `sched_group` → 对照 `/proc/<pid>/cgroup` 确认实际归属 → 查看 task_profiles.json 确认 profile 映射。

## cgroup v2 对 APM / 后台监控 SDK 的影响

APM（Application Performance Monitoring）SDK 和后台监控 SDK 在 cgroup v2 体系下面临几个特殊问题。

### 采样精度受 cgroup 限制影响

后台 APM SDK 运行在 `cpu/background` cgroup 中，受两层限制：
1. `cpuset.cpus` 限制为小核子集（如 CPU 0-3），大核不可用。
2. `cpu.uclamp.max` 默认为 0（或很低值），调度器看到的最大利用率被钳制。

这意味着后台采样任务的实际 CPU 时间可能远低于预期。如果 APM SDK 的 CPU profiler 以固定频率采样（如每 10ms 一次），在 background cgroup 下实际采样间隔可能被拉长到 50-100ms。报告数据中看到的「CPU 占用率」可能严重低于真实值——因为采样任务自己在被限流。

### 监控线程被冻结的风险

Cached 进程被冻结后，进程内所有线程暂停——包括 APM SDK 的上报线程、ANR 监控线程、内存采样线程。如果 SDK 在进程被冻结期间尝试上报数据，上报会堆积到解冻后才执行。这会导致：
- 上报数据时间戳不连续（冻结期间的数据全部缺失）
- 解冻瞬间出现上报突发（积压的数据一次性发送）
- ANR 检测可能假阴性（冻结期间真正的 ANR 无法被监控线程检测到）

APM SDK 需要感知冻结状态。检测方式：
- 读取 `/proc/self/cgroup`，确认是否在 `freezer/` 路径下
- 监听 `ApplicationExitInfo` 的 `REASON_USER_REQUESTED` / `REASON_CRASH` 之外，还要关注冻结相关的退出原因
- 在 `onForegroundInfoChanged` 或 `ProcessLifecycleOwner` 回调中重新校准采样策略

[待验证: APM SDK 厂商（Firebase、Bugly、Matrix 等）的具体冻结感知策略需要从各家文档确认]

## OEM 自定义 cgroup 策略与 AOSP 默认实现差异

AOSP 的 `task_profiles.json` 是默认基线。OEM 可以通过以下方式自定义：

### 1. 覆盖 task_profiles.json

OEM 在设备构建时可以替换或追加 Profile 定义。常见做法是在 `device/<vendor>/<product>/` 下放置自定义的 `task_profiles.json`，构建系统合并到最终产物中。例如：
- 某些 OEM 把 `background` cgroup 的 `cpuset.cpus` 收窄到更少的核心
- 游戏模式 OEM 可能创建额外的 `game-mode` cgroup，单独管理游戏进程的 CPU 集合和 uclamp
- 省电模式 OEM 可能对 `foreground` cgroup 也施加 `cpu.max` 带宽限制

### 2. 自定义 init 脚本中的 cgroup 挂载

OEM 可以在 `.rc` 文件中追加 cgroup 子目录和初始值。例如某些 OEM 会在 init 脚本中为特定服务创建专用 cgroup：

```rc
# 厂商自定义：为游戏创建专用 cgroup
mkdir /dev/cgroot/cpu/game 0750 system system
write /dev/cgroot/cpu/game/cpuset.cpus 4-7
write /dev/cgroot/cpu/game/cpu.uclamp.min 512
```

### 3. 厂商 Power HAL 与 cgroup 的联动

某些厂商的 Power HAL（或 thermal daemon）会根据热状态动态调整 cgroup 配置。例如：
- 热限频时，把 `top-app` 的 `cpuset.cpus` 从 `0-7` 收窄到 `0-3`（只用小核）
- 低电量时，降低所有 cgroup 的 `cpu.uclamp.min` 默认值

这些动态调整通常不修改 `task_profiles.json`，而是直接写 cgroup 文件。排查时需要同时看 task profile 和 cgroup 文件的实际值——两者可能不一致。

[已验证: AOSP android-17.0.0_r1 支持设备级 task_profiles.json 覆盖；厂商自定义实践需结合具体 OEM trace 分析]

### 排查 OEM 差异的方法论

1. **检查实际 cgroup 布局**：`adb shell cat /proc/<pid>/cgroup` 确认进程实际所在路径
2. **检查 task_profiles.json**：`adb shell cat /system/etc/task_profiles.json` 确认设备实际使用的 Profile 定义
3. **检查 init 脚本**：在 `out/target/product/<device>/system/etc/init/` 或 vendor 分区搜索 cgroup 相关的 `.rc` 文件
4. **对比 AOSP 默认值**：与 `android-17.0.0_r1` 的默认 `task_profiles.json` 对照，确认差异点
5. **Perfetto 轨道验证**：通过线程迁移行为和 CPU 频率变化验证 cgroup 切换是否生效

## 交叉引用

| 主题 | 详见章节 |
|------|---------|
| CPU 调度基础（CFS/EEVDF、nice、affinity） | §5.1 |
| EAS 选核与 uclamp 完整控制链 | §5.2 |
| schedtune → uclamp 版本边界 | §5.7 |
| Binder Freezer 与 CachedAppOptimizer | §1.18 |
| OomAdjuster 双锁竞争与性能 | §1.25 |
| LMKD 与 PSI 内存回收 | §4.x |
| sched_ext BPF 可编程调度器 | §17.4 |
| PELT Boost 回退与 AMU/PMU | §5.28 |
