---
title: "Android 17 PSI/LowMemDetector 与 lmkd 内存压力检测架构演进"
chapter: "4.15"
status: ready-for-review
drafted_date: "2026-06-24"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-06-24"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "system/memory/lmkd/lmkd.cpp (android-17.0.0_r1)"
  - type: aosp
    path: "system/memory/lmkd/libpsi/psi.cpp"
  - type: aosp
    path: "system/memory/lmkd/libpsi/include/psi/psi.h"
  - type: aosp
    path: "system/memory/lmkd/lmkd.rc"
  - type: aosp
    path: "system/memory/lmkd/reaper.cpp"
tags: [PSI, lmkd, LowMemDetector, BPF, memevents, memcg, memory-pressure, libpsi, Android-17, oom_score_adj, zone-watermark, direct-reclaim, kswapd]
related_chapters: ["4.4", "4.10", "4.12", "5.15"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-23"
drafted_by: "task2a-content-processing"
---

# 4.15 Android 17 PSI/LowMemDetector 与 lmkd 内存压力检测架构演进

§4.4 介绍了 lmkd 的进程登记、`oom_score_adj` 和基本杀进程流程。Android 17 的压力检测由多类信号共同完成：PSI 负责报告持续停顿，BPF memevents 记录 direct reclaim、kswapd 等内核事件，zone watermark、swap 和 workingset refault 为杀进程判断提供当前状态。

用户空间以 `platform/system/memory/lmkd` 的 `android-17.0.0_r1` 为基准，内核以 common kernel `android17-6.18-2026-06_r6` 为基准。

## 先厘清 LowMemDetector 这个名字

Android 17 的 lmkd 和 common kernel 源码中没有名为 `LowMemDetector` 的类或模块。标题中的 LowMemDetector 只表示“低内存检测层”这个概念，不能把它当作可搜索的源码符号。

Android 17 需要区分两套互斥入口：

| 入口 | 启用条件 | 谁判断并杀进程 |
| --- | --- | --- |
| 用户空间 lmkd | 没有可写的旧 LMK 模块参数 | lmkd 根据 PSI、watermark、swap、thrashing 等信息决策 |
| 旧 in-kernel LMK 兼容接口 | `/sys/module/lowmemorykiller/parameters/minfree` 可写 | 旧内核模块执行 kill，lmkd 读取 kill 记录 |

AOSP lmkd 的 README 已说明，upstream Linux 从 4.12 起移除了旧 lowmemorykiller driver，Android 改由用户空间 lmkd 负责压力监控和进程选择。Android 17 的 common kernel 6.18 基准树也不包含该旧驱动。厂商内核若继续提供兼容模块，lmkd 才会进入第二行的分支。

## PSI：内核怎样量化“系统被内存拖住”

### some、full、avg 与 total

Kernel 6.18 通过 `/proc/pressure/memory` 输出：

```text
some avg10=0.12 avg60=0.05 avg300=0.01 total=12345678
full avg10=0.03 avg60=0.01 avg300=0.00 total=3456789
```

这两行的定义是：

- `some`：在统计区间内，至少有一部分任务因该资源发生停顿；
- `full`：所有 non-idle 任务同时停顿，此时 CPU 没有执行有效工作；
- `avg10`、`avg60`、`avg300`：最近 10、60、300 秒窗口的停顿时间比例，单位是百分比；
- `total`：累计停顿时间，单位是微秒。

“full”不能简化成“所有任务都在等待内存分配”。内核文档使用的是“all non-idle tasks are stalled”，其中包括被内存压力阻塞的有效工作负载；idle task 不计入。

### 从内核记账到 PSI trigger

Kernel 的 `psi_memstall_enter()` / `psi_memstall_leave()` 标记内存停顿区间，随后通过 `psi_task_change()` 和 per-CPU `psi_group_cpu` 更新状态时间。`record_times()` 把从上次状态变化到当前时刻的增量写入对应计数。

用户空间还可以在 `/proc/pressure/memory` 上注册 trigger。trigger 的格式是：

```text
<some|full> <threshold_us> <window_us>
```

例如 `some 70000 1000000` 表示：任意 1 秒跟踪窗口内，some memory stall 累计达到 70ms 时通知。每个 trigger 使用独立 fd；用户空间通过 `poll()` / `epoll()` 等待 `POLLPRI` / `EPOLLPRI`，关闭 fd 后内核销毁 trigger。内核限制通知频率，单个 trigger 每个窗口最多通知一次。

Kernel 6.18 使用 `psi_rtpoll_worker` 汇总 per-CPU 时间并更新 trigger。这里的 rtpoll 是内核 PSI 的实时聚合线程，不是 lmkd 收到事件后的 10ms/100ms 状态轮询，两者不要混为一谈。

## libpsi：lmkd 与 PSI 文件之间的薄适配层

Android 17 的 `libpsi` 位于 `system/memory/lmkd/libpsi/`。头文件导出五个操作：

| 函数 | 作用 |
| --- | --- |
| `init_psi_monitor()` | 打开 PSI 文件并写入 trigger |
| `register_psi_monitor()` | 把 trigger fd 以 `EPOLLPRI` 加入 epoll |
| `unregister_psi_monitor()` | 从 epoll 删除 fd |
| `destroy_psi_monitor()` | 关闭 fd |
| `parse_psi_line()` | 解析某一行 avg10/60/300 与 total |

下面的片段说明 trigger 如何注册：

```cpp
fd = open(psi_resource_file[resource], O_WRONLY | O_CLOEXEC);
snprintf(buf, sizeof(buf), "%s %d %d",
         stall_type_name[stall_type], threshold_us, window_us);
write(fd, buf, strlen(buf) + 1);
```

`resource` 可以选择 memory、I/O 或 CPU。lmkd 的压力 trigger 使用 memory；发生 kill 时还会读取 memory、I/O 与 CPU PSI 数据写入统计。系统级 CPU PSI 没有有意义的 `full` 值，因此 `psi_parse_cpu()` 只解析 `some`。

## Android 17 实际注册哪两个 PSI trigger

### 初始化数组不等于生效配置

`lmkd.cpp` 先定义了 low、medium、critical 三个初始值：

```cpp
static struct psi_threshold psi_thresholds[VMPRESS_LEVEL_COUNT] = {
    { PSI_SOME, 70 },
    { PSI_SOME, 100 },
    { PSI_FULL, 70 },
};
```

这组 70/100/70 会在现代策略中被覆盖。`init_psi_monitors()` 的 `use_new_strategy` 分支执行：

```cpp
psi_thresholds[VMPRESS_LEVEL_LOW].threshold_ms = 0;
psi_thresholds[VMPRESS_LEVEL_MEDIUM].threshold_ms = psi_partial_stall_ms;
psi_thresholds[VMPRESS_LEVEL_CRITICAL].threshold_ms = psi_complete_stall_ms;
```

阈值为 0 的 low 档不会注册 handler。因此，Android 17 的默认新策略实际使用：

| 压力档 | PSI 类型 | 普通设备默认值 | low-RAM 默认值 |
| --- | --- | ---: | ---: |
| low | `PSI_SOME` | 关闭 | 关闭 |
| medium | `PSI_SOME` | 70ms / 1s | 200ms / 1s |
| critical | `PSI_FULL` | 700ms / 1s | 700ms / 1s |

`psi_window_size_ms` 默认 1000ms。将窗口改短时，应连同 partial/complete stall 一起评估；只改窗口会改变阈值占窗口的比例。

### 新旧策略怎样选择

`use_new_strategy` 的默认表达式是：

```text
low_ram_device || !use_minfree_levels
```

`use_minfree_levels` 默认是 `false`，所以常规 AOSP 配置会选新策略。属性可以覆盖该选择；若请求旧策略但系统不是 memcg v1，初始化直接失败，并打印“Old kill strategy can only be used with v1 cgroup hierarchy”。

旧策略的 `mp_event_common()` 依赖 cgroup v1 的 `MemUsage` 和 `MemAndSwapUsage`。Android 17 已用 `[[deprecated("memcg v1 is not supported after Dec. 2026")]]` 标注该函数。这个日期描述的是当前源码中的兼容期限，不应扩展成所有厂商设备在同一天切换的承诺。

### 属性覆盖顺序

`GET_LMK_PROPERTY` 先读：

```text
persist.device_config.lmkd_native.<name>
```

若不存在，再读：

```text
ro.lmk.<name>
```

`lmkd.rc` 为常用实验属性配置了变化触发器：属性变化后设置 `lmkd.reinit`，再通过控制命令重新读取配置并重建 PSI monitors。不是每个 `GET_LMK_PROPERTY` 参数都在 rc 中有热更新触发器，判断某个参数能否即时变化时要同时检查 `update_props()` 和 `lmkd.rc`。

## PSI 事件之后：1 秒窗口内继续观察

PSI trigger 只是一次唤醒信号。`mp_event_psi()` 把压力档封装后调用 `__mp_event_psi(PSI, ...)`；事件处理结束后，lmkd 在 PSI window 内继续调用同一个判断函数，以确认压力是否仍在。

每次判断会读取或计算：

- `/proc/meminfo` 中的 free、swap、anonymous、file cache 等数据；
- `/proc/vmstat` 中的 scan、refill、workingset refault；
- memory PSI，发生 kill 时再补充 I/O 与 CPU PSI；
- 缓存的 zone watermarks，必要时刷新 `/proc/zoneinfo`；
- memevents 提供的 direct reclaim / kswapd 状态。

轮询间隔由当前状态决定：

- swap 低或本轮刚杀过进程：10ms；
- 其他情况：100ms。

等待 pidfd 的进程死亡通知时，轮询会暂停。事件到达、kill 后或 direct reclaim 持续时，轮询继续；单纯的 kswapd 活跃不会无限延长轮询窗口。

10ms/100ms 是 lmkd 对系统内存状态的复查间隔，不是 PSI trigger 的内核采样周期，也不是固定的 kill 周期。

## BPF memevents：补上瞬时回收状态

PSI 反映一段窗口内累积的停顿。Android 17 的 lmkd 还通过 `MemEventListener` 订阅 BPF ring buffer，用时间点事件补充当前回收状态。

### 为什么在 boot completed 后初始化

`LMK_BOOT_COMPLETED` 命令到达后，lmkd 调用 `init_memevent()`。源码注释给出的原因是：避免启动期间等待 BPF programs 加载。若 lmkd 在系统已经完成启动后重启，也会在初始化末尾直接建立 listener。

`lmkd.rc` 在 `sys.boot_completed=1` 时执行：

```text
exec_background /system/bin/lmkd --boot_completed
```

另一个 `LMK_START_MONITORING` 命令只负责补做曾被 `delay_monitors_until_boot` 推迟的 PSI monitor 初始化，不能与 memevents 初始化命令混用。

### 六类事件的作用

Android 17 注册的 memevents 如下：

| 事件 | lmkd 的处理 |
| --- | --- |
| `MEM_EVENT_DIRECT_RECLAIM_BEGIN` | 记录 direct reclaim 起始时间 |
| `MEM_EVENT_DIRECT_RECLAIM_END` | 清除 direct reclaim 起始时间 |
| `MEM_EVENT_KSWAPD_WAKE` | 记录 kswapd 起始时间 |
| `MEM_EVENT_KSWAPD_SLEEP` | 清除 kswapd 起始时间 |
| `MEM_EVENT_VENDOR_LMK_KILL` | 携带厂商 reason 与最低 `oom_score_adj`，进入 `__mp_event_psi(VENDOR, ...)` |
| `MEM_EVENT_UPDATE_ZONEINFO` | 立即刷新 zone watermarks |

direct reclaim 和 kswapd 四个事件是 listener 成功初始化的必要订阅；注册失败会放弃 memevents listener。vendor kill 与 update-zoneinfo 是可选能力，单项失败不会让整个 listener 失效。

只有 vendor kill 会直接调用 `__mp_event_psi()`。direct reclaim / kswapd 事件更新状态，等 PSI 事件或轮询调用时再参与判断；update-zoneinfo 只更新水位线缓存。

若 memevents 不可用，lmkd 通过 `pgscan_direct`、`pgscan_kswapd` 和 `pgrefill` 的变化推断 reclaim 状态。此时 `direct_reclaim_threshold_ms` 会被禁用，因为 vmstat 增量不能提供可靠的 direct reclaim 起始时间。

## Zone watermark：把压力落到可用页状态

lmkd 从 `/proc/zoneinfo` 读取每个 zone 的 `min`、`low`、`high`，并给每一档加上该 zone 的 `max_protection` 后求和。判断时先从 free pages 中减去 CMA free：

```cpp
int64_t free = nr_free_pages - cma_free;
if (free < min_wmark)  return WMARK_MIN;
if (free < low_wmark)  return WMARK_LOW;
if (free < high_wmark) return WMARK_HIGH;
return WMARK_NONE;
```

`MEM_EVENT_UPDATE_ZONEINFO` 可用时，内核事件负责触发缓存更新；不支持该事件时，lmkd 至少每 60 秒重新读取一次 zoneinfo。第一次 kill 前，代码还会强制重新计算，降低陈旧 watermark 导致误判的风险。

watermark 只表示空闲页所处区间。lmkd 还需要结合 swap、refault 和 reclaim 状态，才能区分“短时低水位”与“系统正在持续抖动”。

## ZRAM-aware free swap：逻辑容量还要受物理内存约束

直接使用 `SwapFree` 可能高估 ZRAM 还能接收的数据量：ZRAM 的逻辑 swap slot 最终仍需要物理内存保存压缩页。Android 17 用下面的计算限制有效 free swap：

```cpp
if (swap_compression_ratio) {
  return std::min(
      free_swap,
      easy_available * swap_compression_ratio /
          swap_compression_ratio_div);
}
return free_swap;
```

例如 ratio/div 配为 2/1，表示 1 页容易获得的物理内存按平均 2:1 压缩率估算可承载 2 页 swap 数据。最终值仍取 `free_swap` 与该估算的较小者，防止逻辑 slot 或物理内存任何一侧被高估。把 ratio 设为 0 会忽略这一物理内存约束，直接返回 `free_swap`。

这个值参与 low-swap 判断、swap utilization 和 kill 日志。它不会改变 ZRAM 驱动的压缩器或 slot 数，只改变 lmkd 对“还能换出多少”的估算。

## `__mp_event_psi()`：判断顺序决定 kill reason

`__mp_event_psi()` 先处理未结束的 kill，再读取 vmstat、meminfo、reclaim、thrashing、watermark 和 PSI。随后按源码顺序检查条件，前面的分支命中后不会继续选择后面的 reason。

| 顺序 | 主要条件 | kill reason |
| ---: | --- | --- |
| 1 | vendor memevent | vendor reason |
| 2 | 上一轮已 kill，仍低于 low watermark | `PRESSURE_AFTER_KILL` |
| 3 | critical PSI 事件且任一 watermark 被突破 | `NOT_RESPONDING` |
| 4 | low swap 且 thrashing 超阈值 | `LOW_SWAP_AND_THRASHING` |
| 5 | low swap 且低于 high watermark | `LOW_MEM_AND_SWAP` |
| 6 | 低于 high watermark 且 swap utilization 超阈值 | `LOW_MEM_AND_SWAP_UTIL` |
| 7 | 低于 high watermark 且 thrashing 超阈值 | `LOW_MEM_AND_THRASHING` |
| 8 | direct reclaim 且 thrashing 超阈值 | `DIRECT_RECL_AND_THRASHING` |
| 9 | direct reclaim 持续时间超阈值 | `DIRECT_RECL_STUCK` |
| 10 | 抖动后 file cache 仍低且 watermark 被突破 | `LOW_FILECACHE_AFTER_THRASHING` |
| fallback | 低于 high watermark 且允许 low-memory kill | `LOW_MEM` |

其中“低于 high watermark”在枚举比较中指 `WMARK_MIN` 或 `WMARK_LOW`；“任一 watermark 被突破”还包括 `WMARK_HIGH`。

### Thrashing 怎样计算

lmkd 使用 `workingset_refault`（新内核字段名为 `workingset_refault_file`）相对于 file-backed page cache 基线的增长率：

```text
thrashing =
    (current_refault - initial_refault) * 100 /
    (base_active_file + base_inactive_file + 1)
```

默认每个 `THRASHING_RESET_INTERVAL_MS` 窗口重设基线。若上一窗口没有合适进程可杀，代码会保留并衰减部分增长量，以便新的候选进程出现时继续判断。成功 kill 后，部分 reason 还会按 `thrashing_limit_decay_pct` 下调下一轮阈值。

这个指标描述 file-backed page cache 的 refault 压力，不能直接当作匿名页换入率或 ZRAM 压缩率。

### PSI critical event 与 `critical_stall` 是两个条件

这两个名字很接近，但用途不同：

- critical PSI trigger：默认是 1 秒内累计 700ms `PSI_FULL`，配合 watermark 产生 `NOT_RESPONDING` reason；
- `critical_stall`：当前 memory `full avg10` 大于 `stall_limit_critical` 时为真；已有任意 kill reason 时，它把 `min_score_adj` 改为 0。

`stall_limit_critical` 默认值为 100，而 `avg10` 是 0—100 的百分比，源码使用严格的大于号，因此默认配置下这个额外放宽条件通常不会成立。只有设备把该阈值调低等情况，`critical_stall` 才可能把 foreground-adj 进程纳入候选。

不能把“critical PSI trigger 到达”直接等同于“`critical_stall` 为真”，也不能笼统地说 critical 事件必然允许杀前台进程。

## 选谁杀：`oom_score_adj`、重量与 Reaper

确定 `min_score_adj` 后，`find_and_kill_process()` 从 1000 向下扫描：

- 默认在每个 adj 档选择队列尾部候选；
- `kill_heaviest_task=true` 时，从一开始就选择内存占用最大的候选；
- 扫描进入 `oom_score_adj <= 200` 的可感知进程范围后，即使全局开关为 false，也会改选该档最重进程，希望减少 victim 数量。

多数非紧急分支会把 `min_score_adj` 保持在 201 或 `lowmem_min_oom_score` 以上，以保护可感知进程。`lowmem_min_oom_score` 的默认值是 `PREVIOUS_APP_ADJ + 1`，即 701，并且代码把配置下限夹到 201。vendor、pressure-after-kill、NOT_RESPONDING 等分支可以给出更低门槛。

### Android 17 Reaper 的执行顺序

`reaper.cpp` 的异步线程先尝试：

1. 向目标进程所属 cgroup 的 `cgroup.kill` 写入 `1`；5.10 兼容分支会遍历 `cgroup.procs`；
2. cgroup 路径不可用或失败时，回退到 `pidfd_send_signal(SIGKILL)`；
3. kill 发出后调用 `process_mrelease(pidfd, 0)`，尽早回收目标地址空间。

`process_mrelease()` 需要有效 pidfd。lmkd 的主循环可以借助 pidfd 获知进程死亡；等待期间暂停压力轮询，收到通知或超时后再继续。

## `/proc/lowmemorykiller` 的正确角色

lmkd 只有在检测到旧 in-kernel LMK 模块时才打开 `/proc/lowmemorykiller`。`poll_kernel()` 从中读取的记录包含 pid、uid、group leader、fault、RSS、`oom_score_adj`、最低 adj、启动时间和进程名，用于上报由内核模块完成的 kill。

它不是现代用户空间 lmkd 的 low-watermark 唤醒接口。走该兼容分支时，lmkd 使用内核 LMK 的 minfree/adj 参数；没有旧模块时，lmkd 初始化 PSI monitors，并由用户空间完成判断和 kill。

Android 17 common kernel 6.18 基准树不含旧 lowmemorykiller driver。某台设备出现该 proc 文件时，应把它视为厂商或旧内核兼容实现，并对照该设备内核源码解释。

## 诊断步骤

### 1. 确认 lmkd 使用哪套入口

先查看启动日志中的以下信息：

- `Using in-kernel low memory killer interface`
- `Using psi monitors for memory pressure detection`
- `Using memevents for direct reclaim and kswapd detection`
- `Using vmstats for direct reclaim and kswapd detection`

这些日志比只看 Android 版本可靠。它们分别说明旧内核接口、PSI 新路径、BPF memevents 或 vmstat fallback 的选择结果。

### 2. 读取 PSI 与关键属性

在具备相应权限的调试环境中，可以采集：

```bash
adb shell cat /proc/pressure/memory
adb shell getprop ro.config.low_ram
adb shell getprop ro.lmk.use_new_strategy
adb shell getprop ro.lmk.use_minfree_levels
adb shell getprop ro.lmk.psi_partial_stall_ms
adb shell getprop ro.lmk.psi_complete_stall_ms
adb shell getprop ro.lmk.psi_window_size_ms
adb shell getprop ro.lmk.direct_reclaim_threshold_ms
adb shell getprop ro.lmk.lowmem_min_oom_score
```

DeviceConfig 的 `persist.device_config.lmkd_native.*` 优先级更高，排查时也要读取同名覆盖项。量产机可能限制 proc 文件或部分属性的访问，命令失败时应转向 bugreport、statsd 和系统日志。

### 3. 按同一时间轴关联证据

一次 lmkd kill 至少应关联：

- kill reason 与 victim 的 `oom_score_adj`；
- free pages、有效 free swap、watermark；
- workingset refault / thrashing；
- direct reclaim 或 kswapd 状态；
- memory some/full PSI，以及记录到 kill stats 的 I/O、CPU PSI；
- kill 前后的可用内存、swap 与业务延迟。

单独看到 PSI 升高只能说明任务因资源压力停顿。它不能证明某个进程泄漏，也不能证明杀掉某个缓存进程一定能解除压力。

## 应用工程师需要知道的边界

lmkd 选中进程后会发送 SIGKILL，应用没有清理回调。`onTrimMemory()` 等通知可以帮助应用提前缩减可重建缓存，但回调是否到达、到达级别和后续是否被杀都不构成保证。

应用侧更值得关注：

- 后台进程是否长期持有可重建的大缓存；
- file-backed 数据是否因访问模式不当产生高 refault；
- native / Java heap 增长是否把系统推入 low-swap 或低 watermark；
- 进程恢复是否依赖未持久化状态；
- 一次优化是否减少了 PSI、thrashing 和 kill，而非只让 victim 换成另一个进程。

普通应用不应依赖直接注册系统级 PSI trigger 来实现业务内存管理。Android 权限、SELinux 和厂商配置可能限制 `/proc/pressure` 的写入；系统服务或调试工具也要先验证目标设备权限。

## 版本阅读原则

Android 17 的当前主路径可以概括为：

```text
PSI trigger
  + meminfo / vmstat / zoneinfo
  + BPF memevents 或 vmstat reclaim fallback
  + ZRAM-aware free-swap 估算
  -> __mp_event_psi()
  -> find_and_kill_process()
  -> cgroup kill / pidfd + process_mrelease
```

旧版本或厂商分支可能仍使用 memcg v1 的 `mp_event_common()`、minfree levels 或 in-kernel LMK。版本比较时要同时核对 lmkd tag、内核实现、cgroup 层级和属性，不能只按 API level 推断设备行为。

## 小结

- Android 17 没有名为 `LowMemDetector` 的源码组件；现代低内存检测由 lmkd、PSI、memevents 和内存统计共同完成。
- 新策略默认关闭 low PSI 档，注册 medium SOME 与 critical FULL 两个 trigger；初始数组的 70/100/70 不是最终默认值。
- direct reclaim 与 kswapd memevents 更新状态，只有 vendor kill memevent 直接进入统一判断函数。
- zone watermark、有效 free swap、workingset refault 和 reclaim 状态共同决定 kill reason。
- critical PSI trigger 与 `critical_stall` 是不同条件，默认配置不能简单推导出“critical 事件会杀前台”。
- `/proc/lowmemorykiller` 用于旧 in-kernel LMK 的 kill 记录，common kernel 6.18 基准树没有该驱动。
- Android 17 Reaper 优先尝试 cgroup kill，必要时回退 pidfd signal，再调用 `process_mrelease()`。

## 源码索引

- AOSP lmkd `android-17.0.0_r1`
  - `lmkd.cpp`
  - `lmkd.rc`
  - `reaper.cpp`
  - `libpsi/psi.cpp`
  - `libpsi/include/psi/psi.h`
- Android common kernel `android17-6.18-2026-06_r6`
  - `Documentation/accounting/psi.rst`
  - `kernel/sched/psi.c`
