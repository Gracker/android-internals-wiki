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

4.4 节讲了 lmkd 的整体工作原理：oom_score_adj 分级、两种检测模式（minfree 阈值与 PSI 驱动）、kill 执行流程。本节关注 Android 17 上的架构变化——lmkd 源码从 `system/core/` 迁移到 `system/memory/` 后，PSI 监控、BPF memevents、zone watermark 三条信号如何被统一进 `__mp_event_psi()` 的 kill 决策链，以及老路径（memcg v1 + `mp_event_common()`）的废弃时间线。

## PSI 内核接口与 libpsi 适配层

### /proc/pressure/memory 的 some 与 full

Linux PSI（Pressure Stall Information）在 `/proc/pressure/memory` 暴露两类停顿信号：

```
some avg10=0.12 avg60=0.05 avg300=0.01 total=12345678
full avg10=0.03 avg60=0.01 avg300=0.00 total=3456789
```

- **some**：至少一个任务因内存分配而阻塞（等待 page fault、内存回收等）
- **full**：所有任务都在等待内存分配，CPU 空转

`avg10` / `avg60` / `avg300` 是 10 秒 / 60 秒 / 300 秒的指数衰减平均，`total` 是累计阻塞微秒数。

lmkd 用 PSI monitor 机制而非轮询读取这些文件。PSI monitor 允许用户空间注册一个阈值（如"1 秒窗口内 some stall 累计 ≥ 70ms"），当阈值触发时内核通过 epoll 的 `EPOLLPRI` 通知注册者。每个 monitor fd 的生命周期绑定到文件描述符，fd 关闭后内核自动销毁 monitor。

[已验证: AOSP android-17.0.0_r1, system/memory/lmkd/libpsi/psi.cpp]

### libpsi 独立共享库

Android 12 将 lmkd 从 `system/core/lmkd/` 迁移到 `system/memory/lmkd/`，同时把 PSI 操作抽成独立共享库 `libpsi`，位于 `system/memory/lmkd/libpsi/`。其他需要监控内存压力的系统组件也可以复用这套接口，不必各自实现 epoll + PSI fd 管理。

`libpsi/include/psi/psi.h` 导出五个函数：

| 函数 | 用途 |
|------|------|
| `init_psi_monitor(stall_type, threshold_us, window_us, resource)` | 打开 `/proc/pressure/<resource>` 并写入阈值字符串，返回 monitor fd |
| `register_psi_monitor(epollfd, fd, data)` | 将 monitor fd 加入 epoll 实例，监听 `EPOLLPRI` |
| `unregister_psi_monitor(epollfd, fd)` | 从 epoll 移除 |
| `destroy_psi_monitor(fd)` | 关闭 fd，内核自动销毁 monitor |
| `parse_psi_line(line, stall_type, stats[])` | 解析 `/proc/pressure/*` 的 `some` / `full` 行，提取 avg 和 total |

`init_psi_monitor` 的实现写得很直接：以 `O_WRONLY` 打开 `/proc/pressure/memory`，snprintf 拼出 `"some 70000 1000000"` 格式的阈值字符串（70ms 阈值 / 1 秒窗口），write 进去，返回 fd。`resource` 参数支持 `PSI_MEMORY`、`PSI_IO`、`PSI_CPU` 三种资源，lmkd 只用 memory。

```c
// libpsi/psi.cpp — init_psi_monitor 核心路径
fd = open(psi_resource_file[resource], O_WRONLY | O_CLOEXEC);
snprintf(buf, sizeof(buf), "%s %d %d",
         stall_type_name[stall_type], threshold_us, window_us);
write(fd, buf, strlen(buf) + 1);
return fd;
```

[已验证: AOSP android-17.0.0_r1, system/memory/lmkd/libpsi/psi.cpp + libpsi/include/psi/psi.h]

### PSI monitor 的资源语义

`psi_resource_file[]` 数组把枚举映射到路径：

- `PSI_MEMORY` → `/proc/pressure/memory`
- `PSI_IO` → `/proc/pressure/io`
- `PSI_CPU` → `/proc/pressure/cpu`

lmkd 在 `__mp_event_psi()` 决策完成后还会调用 `psi_parse_mem()` / `psi_parse_io()` / `psi_parse_cpu()` 读取当前 PSI 统计值，写入 kill 日志（`KILLINFO_LOG_TAG`），用于事后分析。这些统计值不参与 kill 决策，只做记录。

## lmkd 检测路径演进

### 三代检测方案

| 时期 | 检测方式 | 核心函数 | 状态 |
|------|---------|---------|------|
| Android 8-9 | vmpressure 事件 + minfree 阈值 | `mp_event_common()` | deprecated，依赖 memcg v1 |
| Android 10-11 | PSI monitor + vmpressure 回退 | `mp_event_psi()` 或 `mp_event_common()` | 混合 |
| Android 12-17 | PSI monitor 为主 + BPF memevents | `__mp_event_psi()` | 当前主路径 |

`mp_event_common()` 在 Android 17 源码中被标记为：

```cpp
[[deprecated("memcg v1 is not supported after Dec. 2026")]]
static void mp_event_common(int data, uint32_t events, struct polling_params *poll_params)
```

这个函数依赖 `GetCgroupAttributePath("MemUsage")` 和 `GetCgroupAttributePath("MemAndSwapUsage")`，通过读取 memcg v1 的 `memory.usage_in_bytes` 和 `memory.memsw.usage_in_bytes` 来计算内存压力比。memcg v2 的统计接口不同，这条路径不兼容。

lmkd 启动时通过 `use_new_strategy` 标志选择走 `mp_event_psi` 还是 `mp_event_common`。Android 12+ 设备默认走 `mp_event_psi`。`mp_event_psi` 是一个薄封装，把 PSI 事件等级包装后调用 `__mp_event_psi(PSI, ...)`。

[已验证: AOSP android-17.0.0_r1, system/memory/lmkd/lmkd.cpp]

### PSI 阈值参数

`psi_thresholds` 数组定义了三个压力级别的触发条件：

```cpp
static struct psi_threshold psi_thresholds[VMPRESS_LEVEL_COUNT] = {
    { PSI_SOME, 70 },    // 70ms / 1s — low pressure
    { PSI_SOME, 100 },   // 100ms / 1s — medium pressure
    { PSI_FULL, 70 },    // 70ms / 1s — critical pressure
};
```

窗口大小 `DEFAULT_PSI_WINDOW_SIZE_MS = 1000`（1 秒）。这些值可通过系统属性覆盖：

| 属性 | 默认值 | 含义 |
|------|--------|------|
| `ro.lmk.psi_partial_stall_ms` | 70 | low 级 some stall 阈值（ms） |
| `ro.lmk.psi_complete_stall_ms` | 700 | critical 级 full stall 阈值（ms） |

`ro.lmk.psi_complete_stall_ms` 默认 700ms，但 `psi_thresholds[VMPRESS_LEVEL_CRITICAL]` 初始硬编码为 70ms（PSI_FULL 70ms / 1s）。`update_props()` 在运行时会用属性值覆盖数组中对应字段。低内存设备（`ro.config.low_ram=true`）的 partial stall 默认值为 200ms，检测更宽松——低内存设备 PSI 事件频繁，阈值过低会导致持续杀进程。

[已验证: AOSP android-17.0.0_r1, system/memory/lmkd/lmkd.cpp — DEF_PARTIAL_STALL=70, DEF_COMPLETE_STALL=700]

### PSI 事件触发后的轮询机制

PSI monitor 只是入口信号。收到事件后 lmkd 进入轮询模式，在 `DEFAULT_PSI_WINDOW_SIZE_MS`（1 秒）窗口内持续读取 `/proc/meminfo`、`/proc/vmstat`、`/proc/zoneinfo`，判断压力是否持续。

轮询间隔有两个档位：

- `PSI_POLL_PERIOD_SHORT_MS = 10`（高压力时）
- `PSI_POLL_PERIOD_LONG_MS = 100`（低压力时）

轮询在 kill 完成、swap 充足且没有 direct reclaim 时停止，回到等待 PSI 事件状态。这个设计避免了"PSI 事件 → kill → PSI 事件"的振荡：kill 之后进入轮询窗口观察效果，如果压力仍然存在，继续 kill；如果压力消退，退出轮询。

## BPF memevents 事件订阅机制

### 架构概述

Android 17 的 lmkd 引入了基于 BPF 的 memevents 事件订阅机制。`memevent_listener` 是一个 `std::unique_ptr<MemEventListener>` 实例，通过 BPF ring buffer 从内核订阅内存事件。

初始化代码在 `init_memevent_listener_monitoring()` 中：

```cpp
android::bpf::waitForProgsLoaded();
memevent_listener = std::make_unique<MemEventListener>(
    android::bpf::memevents::MemEventClient::LMKD);
```

`waitForProgsLoaded()` 确保 BPF 程序已加载——如果 lmkd 在 BPF 程序就绪前尝试创建 listener，初始化会失败。

### 四类事件

| 事件类型 | 触发条件 | lmkd 处理 |
|---------|---------|----------|
| `MEM_EVENT_DIRECT_RECLAIM_BEGIN` | 内核进入直接内存回收 | 记录 direct reclaim 开始时间戳 |
| `MEM_EVENT_DIRECT_RECLAIM_END` | 直接回收结束 | 清除时间戳 |
| `MEM_EVENT_KSWAPD_WAKE` | kswapd 内核线程唤醒 | 记录 kswapd 开始时间戳 |
| `MEM_EVENT_KSWAPD_SLEEP` | kswapd 进入睡眠 | 清除时间戳 |
| `MEM_EVENT_VENDOR_LMK_KILL` | 厂商内核 LMK 杀进程 | 转发到 `__mp_event_psi(VENDOR, ...)` |
| `MEM_EVENT_UPDATE_ZONEINFO` | zone 水位线更新 | 调用 `update_zoneinfo_watermarks()` 刷新缓存 |

[已验证: AOSP android-17.0.0_r1, system/memory/lmkd/lmkd.cpp — memevent_listener_notification()]

### 注册时机：boot_completed 之后

memevent listener 的注册推迟到 `LMK_BOOT_COMPLETED` 之后。`lmkd.rc` 中配置了对应的 init 触发：

```
on property:sys.boot_completed=1
    exec_background /system/bin/lmkd --boot_completed
```

lmkd 收到 `LMK_BOOT_COMPLETED` 命令后调用 `init_memevent()`。这个延迟注册的考虑是：启动阶段 BPF 程序可能尚未加载完成，`waitForProgsLoaded()` 会阻塞等待，如果在启动早期注册会拖慢 boot。

`LMK_START_MONITORING` 命令是另一条路径，用于 PSI monitor 的延迟初始化。如果 `sys.boot_completed` 为 true 且 monitors 尚未初始化，`LMK_START_MONITORING` 触发 `init_monitors()`，注册 PSI epoll fd。

[已验证: AOSP android-17.0.0_r1, system/memory/lmkd/lmkd.rc + lmkd.cpp]

### memevents 与 PSI 的互补关系

PSI monitor 检测的是**持续的内存压力**——some stall 70ms / 1s 意味着压力已经持续了一段时间。memevents 捕获的是**瞬时内核事件**——direct reclaim 开始的那一刻就发出通知，不需要等到 stall 累积。

在 `__mp_event_psi()` 的决策链中，direct reclaim 的持续时长是一个判定因子。如果 direct reclaim 持续超过 `direct_reclaim_threshold_ms`（通过 `ro.lmk.direct_reclaim_threshold_ms` 配置），触发 `DIRECT_RECL_STUCK` kill reason。这个时长就是通过 `MEM_EVENT_DIRECT_RECLAIM_BEGIN` / `END` 事件的时间戳差计算的。

当 `MEM_EVENT_UPDATE_ZONEINFO` 可用时，lmkd 不再需要每分钟轮询 `/proc/zoneinfo` 刷新水位线（`wmark_update_tm` 的 60 秒超时检查被跳过），改为事件驱动刷新。

## lmkd kill 决策链

### __mp_event_psi 的判定流程

`__mp_event_psi()` 是 Android 17 lmkd 的核心决策函数。无论是 PSI epoll 事件、PSI 轮询超时，还是 BPF memevents 中的 vendor kill 事件，都经过这个函数。

收到压力信号后，函数依次检查以下条件，命中第一个就确定 kill reason 和 `min_score_adj`（候选进程的最低 oom_score_adj 门槛）：

1. **Vendor kill**：厂商内核 LMK 通过 `MEM_EVENT_VENDOR_LMK_KILL` 发来的杀进程请求，使用 vendor 指定的 reason 和 min_oom_score_adj

2. **Pressure after kill**（`cycle_after_kill`）：上一轮已经杀过进程，但 zone watermark 仍低于 LOW —— 说明上一轮 kill 释放的内存不够，继续杀，门槛降到 `pressure_after_kill_min_score`

3. **Critical stall + NOT_RESPONDING**：PSI critical 事件 + watermark ≤ HIGH —— 设备已无法正常响应，`min_score_adj` 从 `lowmem_min_oom_score` 开始

4. **Low swap + thrashing**：swap 低于阈值 + page cache thrashing 超过 `thrashing_limit_pct`。如果 watermark > MIN 且 thrashing < `thrashing_critical_pct`，`min_score_adj = PERCEPTIBLE_APP_ADJ + 1`（201），避免杀可感知进程

5. **Low swap + low watermark**：swap 低 + watermark < HIGH。同样保护 perceptible 进程

6. **Low watermark + high swap utilization**：watermark < HIGH + swap 利用率超过 `swap_util_max`

7. **Low watermark + thrashing**：watermark < HIGH + thrashing > `thrashing_limit`。如果 thrashing < critical，保护 perceptible

8. **Direct reclaim + thrashing**：处于直接回收状态 + thrashing > limit。主要出现在低内存设备上

9. **Direct reclaim stuck**：direct reclaim 持续时长 > `direct_reclaim_threshold_ms`。依赖 memevents 提供的时间戳

10. **Low filecache after thrashing**：thrashing 之后 file-backed page cache 低于 `filecache_min_kb`

11. **Low watermark (fallback)**：以上都不命中，但 watermark < HIGH 且 `lowmem_min_oom_score <= OOM_SCORE_ADJ_MAX`，按 `lowmem_min_oom_score` 门槛杀

所有条件都未命中时，`kill_reason = NONE`，本轮不杀进程。

### Critical stall 的特殊处理

在确定要 kill 之后，还有一个关键检查：

```cpp
if (critical_stall) {
    min_score_adj = 0;
}
```

`critical_stall` 的判定依据是 `psi_parse_mem()` 读取的 `PSI_FULL` avg10 值是否超过 `stall_limit_critical`。当系统进入 critical stall——所有任务都因内存阻塞——lmkd 将 `min_score_adj` 设为 0，意味着前台进程（FOREGROUND_APP_ADJ = 0）也在候选范围内。这是 lmkd 的最后一道防线：宁可杀前台 App 也不让整个系统挂死。

### kill 执行：find_and_kill_process

确定 `min_score_adj` 后，`find_and_kill_process()` 从 `OOM_SCORE_ADJ_MAX`（1000）向下扫描到 `min_score_adj`，逐级查找候选进程：

```cpp
for (i = OOM_SCORE_ADJ_MAX; i >= min_score_adj; i--) {
    procp = choose_heaviest_task ? proc_get_heaviest(i) : proc_adj_tail(i);
    // ...
    killed_size = kill_one_process(procp, min_score_adj, ...);
}
```

当候选 `oom_score_adj ≤ PERCEPTIBLE_APP_ADJ`（200）时，切换为 `choose_heaviest_task` 策略——选内存占用最大的进程，试图用最少的 kill 数量释放最多的内存。

`kill_one_process()` 最终走 `reaper.kill()`：先 `pidfd_send_signal(SIGKILL)`，再 `process_mrelease()` 促使内核尽快回收匿名页和页表。`process_mrelease()` 是 Linux 5.11+ 的系统调用，lmkd 从 Android 16 开始使用（详见 4.4 节对 reaper 的分析）。

[已验证: AOSP android-17.0.0_r1, system/memory/lmkd/lmkd.cpp + reaper.cpp]

## PSI 阈值调优与性能影响

### 阈值过高与过低的后果

PSI 阈值直接控制 lmkd 的反应速度。配置过高（如 partial stall 200ms 以上），内存压力积累到很严重才触发 kill，用户感知到 ANR 和全局卡顿。配置过低（如 partial stall 30ms），lmkd 过于激进，缓存进程很快被清空，用户切回 App 时频繁冷启动。

Android 17 的默认值（partial 70ms / complete 700ms / window 1s）是 AOSP 在 Pixel 设备上的经验值。OEM 通过 `ro.lmk.psi_partial_stall_ms` 和 `ro.lmk.psi_complete_stall_ms` 调整，也可以通过 DeviceConfig（`persist.device_config.lmkd_native.*`）在运行时动态切换。

### 不同 RAM 容量下的差异

低内存设备（`ro.config.low_ram=true`，通常 ≤ 2GB RAM）的 partial stall 默认 200ms——这些设备内存回收频繁，阈值过低会导致 lmkd 几乎不停地在杀进程。同时 `low_ram_device` 标志让 `find_and_kill_process()` 每轮只杀一个进程（`For Go devices kill only one task`）。

大内存设备（8GB+）通常不需要调高阈值——PSI 事件触发频率本来就低。OEM 更关注的是 thrashing 阈值和 swap 相关参数，因为大内存设备的内存压力更多表现为 swap 耗尽和 file cache thrashing，而非纯粹的空闲内存不足。

### DeviceConfig 暴露的调优参数

`lmkd.rc` 在 Android 17 中通过 init property 触发 lmkd 重新初始化（`lmkd.reinit=1` → `lmkd --reinit`）。以下参数均支持运行时热更新：

| DeviceConfig 属性 | 对应内部变量 | 默认值 |
|---|---|---|
| `psi_partial_stall_ms` | `psi_partial_stall_ms` | 70 |
| `psi_complete_stall_ms` | `psi_complete_stall_ms` | 700 |
| `psi_window_size_ms` | `psi_window_size_ms` | 1000 |
| `thrashing_limit` | `thrashing_limit_pct` | 设备配置 |
| `thrashing_limit_decay` | `thrashing_limit_decay_pct` | 设备配置 |
| `thrashing_limit_critical` | `thrashing_critical_pct` | 设备配置 |
| `swap_free_low_percentage` | `swap_free_low_percentage` | 设备配置 |
| `swap_util_max` | `swap_util_max` | 100 |
| `filecache_min_kb` | `filecache_min_kb` | 设备配置 |
| `kill_heaviest_task` | `kill_heaviest_task` | false |
| `kill_timeout_ms` | `kill_timeout_ms` | 设备配置 |
| `lowmem_min_oom_score` | `lowmem_min_oom_score` | PREVIOUS_APP_ADJ+1 |
| `direct_reclaim_threshold_ms` | `direct_reclaim_threshold_ms` | 0（禁用） |

[已验证: AOSP android-17.0.0_r1, system/memory/lmkd/lmkd.rc]

## LowMemDetector 与 lmkd 的协作边界

Android 系统中"低内存杀进程"这件事有两个独立机制：内核里的 LowMemoryKiller（旧版已被移除的驱动）和用户空间的 lmkd。但在 Android 17 上还有一个内核侧的内存检测组件需要厘清。

### /proc/lowmemorykiller 的 poll 接口

lmkd.cpp 中有一行容易被忽视的代码：

```cpp
kpoll_fd = TEMP_FAILURE_RETRY(
    open("/proc/lowmemorykiller", O_RDONLY | O_NONBLOCK | O_CLOEXEC));
```

这个 fd 被加入 epoll，当内核检测到内存水位跌破最低水位线（min watermark）时，`/proc/lowmemorykiller` 变为可读，通知 lmkd。这是一种内核到用户空间的主动通知机制，让 lmkd 不必轮询 `/proc/meminfo`。

这个接口的存在取决于内核是否编译了对应的 driver（部分厂商内核有，AOSP 通用内核不一定有）。如果 `open()` 失败，lmkd 回退到纯 PSI + zoneinfo 轮询路径。

[已验证: AOSP android-17.0.0_r1, system/memory/lmkd/lmkd.cpp — kpoll_fd 初始化]

### Zone watermark 作为 kill 决策的底层锚点

lmkd 的 kill 决策链中，zone watermark 是几乎每个条件都要检查的基础指标。`get_lowest_watermark()` 比较当前空闲页（减去 CMA 区域）与三个水位线：

```cpp
int64_t nr_free_pages = mi->field.nr_free_pages - mi->field.cma_free;

if (nr_free_pages < watermarks->min_wmark)  return WMARK_MIN;
if (nr_free_pages < watermarks->low_wmark)  return WMARK_LOW;
if (nr_free_pages < watermarks->high_wmark) return WMARK_HIGH;
return WMARK_NONE;
```

水位线从 `/proc/zoneinfo` 的每个 zone 的 `min` / `low` / `high` 字段加上 `max_protection`（zone 的累积保护页数）计算得来。`MEM_EVENT_UPDATE_ZONEINFO` 事件可用时，内核在水位线变化时主动通知 lmkd 刷新缓存；不可用时 lmkd 每 60 秒刷新一次。

### 两个检测层的分工

| 层 | 检测目标 | 响应方式 |
|---|---|---|
| PSI monitor（内核 → lmkd） | 持续性内存停顿（some/full stall） | epoll EPOLLPRI，触发 `__mp_event_psi()` |
| BPF memevents（内核 → lmkd） | 瞬时回收事件（direct reclaim、kswapd、vendor kill） | ring buffer 通知，更新状态变量 |
| Zone watermark（lmkd 读取） | 空闲页数量是否低于水位线 | kill 决策中的核心判定因子 |
| `/proc/lowmemorykiller` poll（内核 → lmkd） | 内存极度不足（min watermark 以下） | epoll 可读通知 |

PSI 负责"压力已经持续了一阵"的检测，memevents 负责"内核正在做内存回收"的即时通知，zone watermark 是两者共同的底层量化依据。lmkd 把这三条信号汇入同一个决策函数，根据 watermark 级别、thrashing 程度、swap 状态、reclaim 状态的组合，决定是否 kill 以及 kill 到哪个优先级。

## 扩展

### PSI for I/O 与 CPU 的分析价值

`/proc/pressure/io` 和 `/proc/pressure/cpu` 不被 lmkd 用于 kill 决策，但在性能分析中有直接价值。IO stall 高通常意味着存储子系统成为瓶颈——可能是 f2fs garbage collection、或者大量脏页 writeback。CPU stall 高说明 CPU 调度延迟大，可能是 RT 进程抢占或者 CPU 频率锁定在低位。

lmkd 在 kill 事件日志中会一并记录当时的 IO 和 CPU PSI avg10 值（`psi_parse_io()` / `psi_parse_cpu()` 的输出），在事后分析内存 kill 是否伴随 IO 或 CPU 压力时可以参考。

### memcg v2 迁移对内存管理的影响

`mp_event_common()` 的 deprecated 标注标志着 memcg v1 的退出。memcg v2 的统计接口从 `memory.usage_in_bytes` 变为 `memory.current`，粒度更细（新增 `memory.peak`、`memory.swap.current` 等）。但 lmkd 的现代路径（`__mp_event_psi()`）完全不依赖 memcg 统计——它用的是全局 `/proc/meminfo` 和 `/proc/zoneinfo`。

memcg v2 迁移影响更大的是 per-app 内存归因和 `dumpsys meminfo` 的输出格式，对 lmkd kill 策略本身没有直接影响。对应用开发者来说，`Debug.getMemoryInfo()` 和 `ActivityManager.getProcessMemoryInfo()` 的返回值在 memcg v2 下可能略有差异，但框架层做了兼容。

### 开发者可观测的 PSI 信号

应用进程可以读取 `/proc/pressure/memory` 做主动内存管理。Android 的 Memory Advice API（`android.performance.MemoryAdvice`，Jetpack library）底层就参考了 PSI 数据。开发者可以注册 `MemoryAdvice.OnAvailabilityListener`，在收到 `PRESSURE_MEDIUM` 或 `PRESSURE_HIGH` 时主动释放缓存。

在低内存设备上，主动释放的效果比被动等 lmkd kill 好得多——lmkd kill 是 SIGKILL，进程没有机会做清理；MemoryAdvice 回调允许 App 在被杀之前主动缩减内存占用。

[适用版本: Android 11+ — Memory Advice API 通过 Jetpack 分发]
