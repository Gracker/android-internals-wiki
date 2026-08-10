---
title: "Android 17 cgroup v1/v2 混合层级与进程资源隔离机制"
chapter: "1.56"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [cgroup, cgroup-v2, 资源限制, 进程隔离, CPU, 内存, 后台限制, libprocessgroup, task-profiles]
related_chapters: ["1.3", "1.18", "5.1", "5.2", "5.7", "5.28"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-15"
gap_source: "AOSP结构"
drafted_date: "2026-07-15"
last_verified: "2026-07-25"
last_verified_against: "AOSP android-17.0.0_r1 + kernel android17-6.18-2026-06_r6"
confidence: high
sources:
  - type: aosp
    path: "system/core/libprocessgroup/profiles/cgroups.json (android-17.0.0_r1)"
  - type: aosp
    path: "system/core/libprocessgroup/profiles/task_profiles.json (android-17.0.0_r1)"
  - type: aosp
    path: "system/core/libprocessgroup/task_profiles.cpp, processgroup.cpp (android-17.0.0_r1)"
  - type: aosp
    path: "system/core/libprocessgroup/setup/cgroup_map_write.cpp (android-17.0.0_r1)"
  - type: aosp
    path: "system/core/rootdir/init.rc, init.zygote*.rc (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/core/jni/android_util_Process.cpp (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/psc/OomAdjuster.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java (android-17.0.0_r1)"
  - type: official
    path: "https://source.android.com/docs/core/perf/cgroups"
  - type: kernel
    path: "Documentation/admin-guide/cgroup-v2.rst (android17-6.18-2026-06_r6)"
---

# 1.56 Android 17 cgroup v1/v2 混合层级与进程资源隔离机制

Android 17 使用 cgroup 管理 CPU 调度、CPU 集合、I/O、内存、进程冻结与进程组生命周期。平台通过 `libprocessgroup` 和任务配置（task profile）隐藏底层文件路径，使 framework 和 native service 只表达“后台”“top-app”“冻结”等意图。

`android-17.0.0_r1` 的 AOSP 默认配置仍是 cgroup v1/v2 混合拓扑。cgroup v2 的“统一层级”只约束 v2 控制器；它没有把 Android 的 v1 `cpu`、`cpuset`、`blkio` 自动并入同一棵树。

以下行为以 AOSP `android-17.0.0_r1` 和内核 `android17-6.18-2026-06_r6` 为准。设备厂商可以覆盖控制器版本、挂载点、子组和参数，设备实际值需要另行核对。

## 1. Android 17 的默认拓扑

### 1.1 `cgroups.json` 给出的基线

`system/core/libprocessgroup/profiles/cgroups.json` 直接定义了控制器版本与挂载点：

```json
{
  "Cgroups": [
    { "Controller": "blkio", "Path": "/dev/blkio" },
    { "Controller": "cpu", "Path": "/dev/cpuctl" },
    { "Controller": "cpuset", "Path": "/dev/cpuset" }
  ],
  "Cgroups2": {
    "Path": "/sys/fs/cgroup",
    "Controllers": [
      { "Controller": "freezer", "Path": "." },
      {
        "Controller": "memory",
        "Path": ".",
        "NeedsActivation": true,
        "MaxActivationDepth": 3,
        "Optional": true
      }
    ]
  }
}
```

这段配置得到的 AOSP 基线是：

| 资源 | cgroup 版本 | 默认挂载点 | Android 17 中的主要用途 |
| --- | ---: | --- | --- |
| CPU 调度组 | v1 | `/dev/cpuctl` | `background`、`foreground`、`top-app`、`system`、`rt` 等组 |
| CPU 集合 | v1 | `/dev/cpuset` | 约束线程可运行的 CPU |
| 块 I/O | v1 | `/dev/blkio` | background I/O 权重与优先级 |
| freezer | v2 核心接口 | `/sys/fs/cgroup` | 冻结 app/system 的 per-process cgroup |
| memory | v2，可选 | `/sys/fs/cgroup` | per-process 统计、保护、限制与回收接口 |

Android 17 AOSP 中不存在统一的 `/dev/cgroot/cpu/top-app` 基线路径。CPU profile 写 `/dev/cpuctl/...`，cpuset profile 写 `/dev/cpuset/...`，freezer 和 v2 memory 则写 `/sys/fs/cgroup/...`。

### 1.2 一个进程可以同时出现在多棵树

在混合拓扑下，同一进程可以同时属于：

- `/dev/cpuctl/top-app`；
- `/dev/cpuset/top-app`；
- `/dev/blkio` 或 `/dev/blkio/background`；
- `/sys/fs/cgroup/apps/uid_<uid>/pid_<pid>`。

`/proc/<pid>/cgroup` 会按 hierarchy 列出这些归属。看到 v2 行中的 `0::/apps/...`，不能据此推断 CPU 与 cpuset 也已迁入 v2；必须结合 `/proc/<pid>/mountinfo` 或设备上的 `cgroups.json` 解释每一行。

## 2. init 如何建立层级

### 2.1 控制器挂载由 `CgroupSetup()` 完成

PID 1 在 init 的 `SetupCgroupsAction` 中调用 `CgroupSetup()`。`libprocessgroup/setup/cgroup_map_write.cpp` 根据 descriptor 分别处理：

- v1：以 `cgroup` 文件系统挂载单个控制器；
- v2：以 `cgroup2` 挂载统一层级；
- v2 memory：在允许的层级深度写 `+memory` 到 `cgroup.subtree_control`；
- v2 根：创建 `apps` 和 `system` 两个子层级。

v2 挂载会尝试使用 `memory_recursiveprot`，使 `memory.min`/`memory.low` 的保护可以递归作用于子树；旧内核不支持时再回退到普通挂载。Android 17 的内核锚点支持该选项。

### 2.2 per-UID、per-process 目录

`createProcessGroup()` 为进程建立 v2 cgroup。`task_profiles.cpp` 的路径规则为：

```text
UID >= AID_APP_START：
/sys/fs/cgroup/apps/uid_<uid>/pid_<pid>

UID < AID_APP_START：
/sys/fs/cgroup/system/uid_<uid>/pid_<pid>
```

源码以 `AID_APP_START` 为分界选择 `apps` 或 `system`，并不是根据包名、签名或进程名判断。创建过程会建立 UID 目录、按需激活 memory controller，再建立 PID 目录，并把初始 PID 写入该目录的 `cgroup.procs`。这一级目录同时承载 freezer、`cgroup.kill` 和可用的 memory 文件。

这种布局解决的是应用/系统进程隔离与生命周期管理。它不决定 top-app 或 background 的 CPU 组；CPU 和 cpuset 仍通过各自的 v1 层级管理。

### 2.3 `cgroup.subtree_control` 的作用边界

cgroup v2 controller 默认不会自动向子层级分发。父 cgroup 只能启用 `cgroup.controllers` 中列出的 controller，并且要满足 top-down 和 no-internal-process 约束。Android 的 `NeedsActivation`、`MaxActivationDepth` 和 `ActivateControllers()` 封装了这部分操作。

freezer 需要单独说明。`cgroup.freeze` 是 cgroup v2 的核心接口，存在于非根 cgroup；它不作为 `+freezer` 写入 `cgroup.subtree_control`。AOSP 在 `cgroups.json` 中把它命名为 `freezer`，是为了让 task profile 通过统一的 controller/attribute 抽象找到文件。

## 3. `libprocessgroup`：把意图翻译成文件操作

### 3.1 两类配置文件

`libprocessgroup` 使用两套 JSON：

| 文件 | 作用 |
| --- | --- |
| `cgroups.json` | 定义 controller 名称、版本、挂载点、权限、可选性和激活要求 |
| `task_profiles.json` | 定义 attribute、profile action 和 aggregate profile |

Android 17 支持按产品首发 API、vendor 和 `system_ext` 覆盖或追加配置。源码的加载顺序是：

1. 系统默认文件；
2. `ro.product.first_api_level` 对应的 API-level 文件；
3. vendor 文件；
4. task profile 还会读取 `system_ext` 文件。

同名定义由后加载的文件替换，新增名称则加入集合。分析 OEM 设备时，AOSP 源文件只能作为起点；设备上的实际文件和运行时 cgroupfs 才是有效配置。

### 3.2 配置动作

Android 17 的 action 不限于移动 cgroup：

- `JoinCgroup`：把线程或进程加入指定 controller 的子组；
- `SetAttribute`：通过 attribute 名查找进程/线程对应文件并写值；
- `WriteFile`：写指定路径；
- `SetTimerSlack`：写 `/proc/<tid>/timerslack_ns`；
- `SetSchedulerPolicy`：设置 Linux scheduler policy 和优先级/nice；
- `Compact`：通过 memory cgroup 的 `memory.reclaim` 发起回收；
- aggregate profile：按顺序执行多个 profile。

`SetClamps` 不是 Android 17 `task_profiles.cpp` 支持的 action。UClamp 通过 `UClampMin`、`UClampMax`、`UClampLatencySensitive` attribute 或 cgroup 初始配置表达。

### 3.3 AOSP 默认 Profile 的映射

下面只列出 `android-17.0.0_r1` 中能直接从 JSON 确认的映射：

| Profile | Action | 实际控制器 |
| --- | --- | --- |
| `HighEnergySaving` | 加入 `cpu/background` | v1 `/dev/cpuctl/background` |
| `HighPerformance` | 加入 `cpu/foreground` | v1 `/dev/cpuctl/foreground` |
| `HighPerformanceWI` | 加入 `cpu/foreground_window` | v1 `/dev/cpuctl/foreground_window` |
| `MaxPerformance` | 加入 `cpu/top-app` | v1 `/dev/cpuctl/top-app` |
| `ProcessCapacityLow` | 加入 `cpuset/background` | v1 `/dev/cpuset/background` |
| `ProcessCapacityHigh` | 加入 `cpuset/foreground` | v1 `/dev/cpuset/foreground` |
| `ProcessCapacityMax` | 加入 `cpuset/top-app` | v1 `/dev/cpuset/top-app` |
| `LowIoPriority` | 加入 `blkio/background` | v1 `/dev/blkio/background` |
| `Frozen` / `Unfrozen` | 将 `FreezerState` 写为 `1` / `0` | v2 per-process `cgroup.freeze` |

`MaxPerformance` 本身只移动 CPU controller。聚合配置负责把 CPU 与 cpuset 一起切到 `top-app`：

```text
SCHED_SP_TOP_APP
  = MaxPerformance + MaxIoPriority + TimerSlackNormal

CPUSET_SP_TOP_APP
  = MaxPerformance + ProcessCapacityMax
    + MaxIoPriority + TimerSlackNormal
```

线程 API 名称也反映了这项差别：只设置 scheduling group 的入口不会自动修改 cpuset；“group and cpuset”或进程级入口使用包含 `ProcessCapacity*` 的 aggregate profile。

## 4. Java/JNI 到 task profile 的调用链

### 4.1 三个常用 JNI 入口

Android 17 的 `android_util_Process.cpp` 给出清晰边界：

| Java 入口 | Native 调用 | Profile 名来源 |
| --- | --- | --- |
| `Process.setThreadGroup(tid, group)` | `SetTaskProfiles(..., use_fd_cache=true)` | `SCHED_SP_*` |
| `Process.setThreadGroupAndCpuset(tid, group)` | `SetTaskProfiles(..., use_fd_cache=true)` | `CPUSET_SP_*` |
| `Process.setProcessGroup(pid, group)` | `SetProcessProfilesCached(uid, pid, ...)` | `CPUSET_SP_*` |

`SetProcessProfilesCached` 函数名中的 `Cached` 指文件描述符缓存，可减少反复打开固定 cgroup 文件的成本。它不会比较进程旧状态并跳过所有 profile action。带 `<uid>`/`<pid>` 的动态路径也不会使用同一套全局 fd 缓存。

进程级 `setProcessGroup` 还保留历史约束：不能直接传 `THREAD_GROUP_FOREGROUND`；默认组会按 API 语义处理。阅读 framework 调用时，应继续追踪实际配置名，不要只看 `THREAD_GROUP_*` 的整数。

### 4.2 init service 的启动配置

Android Init Language 支持：

```rc
service zygote /system/bin/app_process64 ...
    task_profiles ProcessCapacityHigh MaxPerformance
```

`Service::Start()` 在子进程执行 `exec` 前应用这些 profile。Android 12 起，`task_profiles` 替代直接写 `writepid /dev/.../tasks` 的旧写法。profile 名稳定后，产品可以改变底层 controller 或路径而不修改 service 定义。

## 5. OomAdjuster 如何决定应用的调度组

### 5.1 procstate 与 sched group 没有固定一一映射

Android 17 的 OomAdjuster 已位于 `services/core/java/com/android/server/am/psc/`。它综合 Activity、可见 UI、前台服务、广播、绑定关系、屏幕状态、远程动画和限制策略计算：

- `oom_score_adj`；
- process state；
- scheduling group；
- capability。

同一个 `PROCESS_STATE_SERVICE` 可能因正在执行前台服务回调、普通后台服务或绑定传播而得到不同 scheduling group。把所有 `PROCESS_STATE_SERVICE` 固定映射到 foreground，或把所有 cached/empty 固定映射到 restricted，都会丢失策略条件。

### 5.2 计算结果转换为调度组

`OomAdjuster.applyResultsLSP()` 对 scheduling group 的关键映射如下：

| Framework scheduling group | `Process.THREAD_GROUP_*` |
| --- | --- |
| `SCHED_GROUP_BACKGROUND` | `THREAD_GROUP_BACKGROUND` |
| `SCHED_GROUP_TOP_APP` / `TOP_APP_BOUND` | `THREAD_GROUP_TOP_APP` |
| `SCHED_GROUP_RESTRICTED` | `THREAD_GROUP_RESTRICTED` |
| `SCHED_GROUP_FOREGROUND_WINDOW` | `THREAD_GROUP_FOREGROUND_WINDOW` |
| 其他默认情形 | `THREAD_GROUP_DEFAULT` |

OomAdjuster 通过 `mProcessGroupHandler` 异步发送组变更，再由 callback 调整应用及相关子进程。profile 文件写入不在 OomAdjuster 的计算循环内执行。状态字段先更新、cgroup 迁移随后执行，因此短时间观察可能同时看到“新 sched group”与“旧 cgroup 路径”；不能预设固定的 100～200 ms 窗口。

进入或离开 `top-app` 时，framework 还可能单独调整主线程/RenderThread nice，或在配置允许时切换 FIFO UI scheduling。这些动作和 cgroup 迁移有关联，但属于不同内核接口，排查时要分别取证。

## 6. CPU、cpuset 与 UClamp

### 6.1 Android 17 AOSP 的 CPU 路径仍是 v1

`rootdir/init.rc` 创建：

```text
/dev/cpuctl/{background,foreground,foreground_window,top-app,rt,system,...}
/dev/cpuset/{background,foreground,foreground_window,top-app,restricted,...}
```

cpuset 挂载使用 `noprefix`，实际文件名是 `/dev/cpuset/<group>/cpus` 和 `mems`，不是 v2 风格的 `cpuset.cpus`。

init 只保证组和权限存在，并把根 CPU mask 复制为初始值。具体 SoC 的 `top-app`、`foreground`、`background` CPU mask 由设备配置写入。AOSP 不能证明“background 固定为 0-3”或“top-app 固定为 0-7”。

### 6.2 UClamp 的位置与含义

Android common kernel 把 `cpu.uclamp.min`、`cpu.uclamp.max` 和 Android 扩展的 latency-sensitive 属性暴露在 `/dev/cpuctl/<group>/`。`task_profiles.json` 把它们声明为 `cpu` controller 的 attribute；进程加入某个 CPU group 后，调度会受该组当前参数约束。

UClamp 钳制调度器看到的利用率上下界，会影响选核与调频决策输入。它不等于锁定频率，也不保证某个线程立即迁移到大核。热限制、CPU affinity、cpuset、调度类、负载和 governor 仍共同决定执行位置与频率。

### 6.3 affinity 与 cpuset 取交集

线程允许使用的 CPU 是 thread affinity 与有效 cpuset 的交集。出现“设置 affinity 后仍不上大核”时，应同时读取：

- `/proc/<tid>/status` 的 `Cpus_allowed_list`；
- `/proc/<tid>/cgroup` 的 cpuset hierarchy；
- `/dev/cpuset/<group>/cpus`；
- CPU online 状态、thermal 与调度 trace。

只检查 `sched_setaffinity()` 的返回值不能证明线程可在目标 CPU 上运行。

### 6.4 `cpu.weight` / `cpu.max` 何时成立

`cpu.weight` 和 `cpu.max` 是 cgroup v2 CPU controller 接口。内核 `6.18` 中：

- `cpu.weight` 以 1～10000 的权重在活跃兄弟 cgroup 间分配 fair-class CPU 时间；
- `cpu.max` 用 `$MAX $PERIOD` 限制带宽，`max` 表示不设上限。

Android 17 AOSP 默认把 CPU controller 挂在 v1 `/dev/cpuctl`，不能用这两个 v2 文件解释平台基线。厂商若通过 `cgroups.json` 把 CPU 改为 v2，才需要核对 `cpu.weight`、`cpu.max` 与 subtree activation。具体产品是否这样配置，应从设备文件和 mountinfo 判断。

## 7. v2 memory controller

### 7.1 AOSP 提供的 attribute

Android 17 的 `task_profiles.json` 为 memory controller 定义了：

- `MemEvents` → `memory.events`；
- `MemStats` → `memory.stat`；
- `MemHigh` → `memory.high`；
- `MemLimit` → v2 的 `memory.max`；
- `MemSoftLimit` → v2 的 `memory.low`；
- `SwapMax` → `memory.swap.max`；
- `MemUsage` 等兼容 attribute。

memory controller 在默认 `cgroups.json` 中标为 optional。设备不支持、没有启用或被 vendor 改为其他布局时，不能假定相应配置动作会沿 AOSP 路径成功执行。

### 7.2 四个接口的语义边界

| 文件 | 内核语义 | 性能风险 |
| --- | --- | --- |
| `memory.low` | 尽力提供回收保护；保护量受祖先和过量承诺影响 | 保护过多会把回收压力转移给其他 cgroup |
| `memory.high` | 超限后让该 cgroup 进入强回收/节流；极端情况下可暂时超过 | 设置过低会增加 direct reclaim 与分配延迟 |
| `memory.max` | 硬上限；回收无法满足时可能触发 cgroup OOM | 错误上限会导致进程被杀或分配失败 |
| `memory.oom.group` | 设为 1 时把 cgroup 作为不可分割 workload 处理 | 可能扩大一次 cgroup OOM 的终止范围 |

`memory.low` 不能概括成“低于该值绝不回收”；它提供尽力而为的保护。`memory.high` 也不是普通告警阈值，超限会让该 cgroup 中的进程进入强回收和节流。

AOSP 默认 profile 暴露这些能力，但没有给所有应用统一写入 `memory.max`/`memory.high`。是否设置、设置多少属于产品策略。不要用假设的 system_server 上限、工作资料（Work Profile）上限或固定阈值解释未知设备。

### 7.3 与 LMKD 的边界

LMKD 主要根据 PSI、内存状态、`oom_score_adj` 和配置选择牺牲进程；memory cgroup 的 reclaim、`memory.max` 和 cgroup OOM 由内核执行。两条路径可以同时存在，但触发条件和受害者选择不同。

排查“进程因内存消失”时至少区分：

- LMKD 日志与杀进程原因；
- kernel OOM/cgroup OOM 日志；
- `memory.events` 中的 `high`、`max`、`oom`、`oom_kill` 计数；
- tombstone、ApplicationExitInfo 和进程自身崩溃证据。

只看到 RSS 接近某个数值，不能判断是哪条机制触发。

## 8. freezer 与 Binder Freezer

### 8.1 `Frozen` profile 写入位置

`Process.setProcessFrozen(pid, uid, true)` 在 JNI 中调用：

```text
SetProcessProfiles(uid, pid, {"Frozen"})
  -> SetAttribute FreezerState = 1
  -> /sys/fs/cgroup/{apps|system}/uid_<uid>/pid_<pid>/cgroup.freeze
```

解冻使用 `Unfrozen` 并写 `0`。这里不使用 cached fd 路径，因为文件名包含 UID/PID，且进程 cgroup 会创建和删除。

向 `cgroup.freeze` 写 `1` 会发起该 cgroup 及其后代的冻结。冻结完成可能滞后于写入；内核通过 `cgroup.events` 的 `frozen` 字段报告完成状态。因此，“一次写入就原子完成冻结”不准确。

### 8.2 Binder Freezer 处理 Binder Freezer

暂停调度不能解决 Binder 中已有事务、同步调用和异步队列的语义。`CachedAppOptimizer.freezeProcess()` 分两次检查 Binder 状态：

1. 调用 `freezeBinder(pid, true, timeout)`。返回值非零表示仍有 outstanding transaction，此时不写 `cgroup.freeze`，交给失败处理逻辑；
2. Binder 侧满足冻结条件后，调用 `setProcessFrozen(..., true)` 写入 cgroup freezer，并记录 framework 冻结状态；
3. 写入后再调用 `getBinderFreezeInfo(pid)`。若两步之间又出现 `TXNS_PENDING_WHILE_FROZEN`，同样进入失败处理逻辑。

第二次检查用于覆盖 Binder 冻结与 cgroup 冻结之间的竞态窗口。解冻时，源码读取 Binder freeze info；若没有需要终止进程的同步事务，就解冻 Binder，随后写 cgroup freezer。cgroup freezer 负责停止线程运行，Binder 驱动负责 IPC 边界；两者不会被一条 `cgroup.freeze` 写操作自动合并。

完整的 pending transaction、oneway 和同步调用规则见 **1.18 Binder Freezer 与缓存进程冻结性能**。

### 8.3 对进程内监控的影响

进程冻结后，其普通线程不再获得 CPU，进程内 Watchdog、采样线程和上传线程也会暂停。解冻后的时间间隔突增不能直接算作 ANR、CPU starvation 或网络超时。

普通应用没有可依赖的公开“即将被冻结”回调。监控系统若需要区分冻结，应结合系统侧/外部观测、生命周期上下文与采样连续性判断，不能靠在已冻结进程里轮询 `cgroup.freeze`。也没有证据支持把后台 profiler 的 10 ms 周期统一换算成 50～100 ms。

## 9. 设备核对方法

以下只读命令用于确认拓扑与进程归属：

```bash
adb shell cat /proc/mounts
adb shell cat /proc/<pid>/cgroup
adb shell cat /system/etc/cgroups.json
adb shell cat /system/etc/task_profiles.json
adb shell cat /vendor/etc/cgroups.json
adb shell cat /vendor/etc/task_profiles.json
```

文件可能通过根目录映射显示为 `/etc/...`，`vendor`/`system_ext` 也可能追加定义。命令失败还可能来自 SELinux 或 shell 权限，不能把“读不到”解释为 controller 不存在。

再按资源检查实际值：

```bash
# v1 CPU / UClamp
adb shell cat /dev/cpuctl/top-app/cpu.uclamp.min
adb shell cat /dev/cpuctl/background/cpu.uclamp.max

# v1 cpuset
adb shell cat /dev/cpuset/top-app/cpus
adb shell cat /dev/cpuset/background/cpus

# v2 per-process
adb shell cat /sys/fs/cgroup/apps/uid_<uid>/pid_<pid>/cgroup.freeze
adb shell cat /sys/fs/cgroup/apps/uid_<uid>/pid_<pid>/memory.events
```

这些值应和 `/proc/<pid>/cgroup` 指向的实际组对应。`top-app` 组存在不代表目标线程已经加入，profile 名存在也不代表所有动作都已成功执行。

Perfetto 适合验证后果：

- `sched_switch` / thread state：线程何时可运行、在哪个 CPU 执行；
- CPU frequency/ idle：UClamp 和负载变化后的频率与 idle 状态；
- Binder/freezer 事件：冻结、解冻和事务失败；
- memory counter /PSI：回收、压力与 cgroup memory 事件的时间关系。

Perfetto 中看到大核迁移或频率上升，只能作为结果证据。要证明 cgroup 切换，还需配合 profile 调用、cgroupfs 或 `/proc` 快照。

## 10. OEM 覆盖的审计方法

厂商常见改动包括：

- 修改 cpuset 的 CPU mask；
- 修改 `/dev/cpuctl/<group>/cpu.uclamp.*`；
- 增加游戏、相机、NNAPI 或系统服务 profile；
- 把更多 controller 迁入 cgroup v2；
- 调整 per-app memory controller 的启用与阈值；
- 由 power/thermal 服务在运行时重写组参数。

审计时按以下顺序收集证据：

1. 查看 mountinfo，确认 controller 版本和挂载点；
2. 读取 system、API-level、`system_ext` 的实际 JSON；
3. 展开 aggregate profile，列出每个 action；
4. 对照目标 PID/TID 的 `/proc/.../cgroup`；
5. 读取目标组的当前文件值；
6. 用 Perfetto 观察调度、频率、freezer、PSI 和用户可见延迟。

不要从 AOSP profile 名推断厂商参数。`MaxPerformance` 表达策略意图，具体 CPU mask、UClamp 与 thermal 上限由产品配置决定。

## 11. Android 17 的资源分组层次

Android 17 的资源分组可以分成三层：

- framework 计算进程重要性和 scheduling group；
- `libprocessgroup` 将稳定的 profile 名转换为 cgroup、scheduler、timer slack 或 memory action；
- 内核按 v1/v2 controller 的实际配置执行调度、限制、回收和冻结。

平台基线中，CPU、cpuset、blkio 仍在 v1，freezer 与可选 memory 位于 v2。v2 的 per-UID/per-process 树提供进程隔离、冻结、kill 和 memory 文件；`top-app`/`background` 的 CPU 差异仍来自 `/dev/cpuctl`、`/dev/cpuset` 及设备参数。

定位问题时，应从设备当前拓扑出发：确认 controller 版本与路径，再确认 profile action 和 PID/TID 归属，然后用 trace 验证性能后果。把“Android 17 支持 cgroup v2”理解为“所有 controller 已迁入统一树”，会让后续 CPU、memory、freezer 结论全部偏离源码。

相关章节：CPU affinity、cpuset 与 task profile 见 **5.1**；EAS/UClamp 见 **5.2** 与 **5.7**；Binder Freezer 见 **1.18**；OomAdjuster 见 **1.34**；LMKD/PSI 见内存管理章节。
