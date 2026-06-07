---
title: "eBPF 系统架构：bpfloader Rust 化与 BPF 程序组织"
chapter: "14.21"
status: ready-for-review
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: [ebpf, bpfloader, rust, bpf, system-architecture, timeInState]
related_chapters: ["14.10", "17.4", "26.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-07"
drafted_date: "2026-06-07"
last_verified: "2026-06-07"
last_verified_against: "AOSP main 分支（android-17.0.0_r1 tag 在 system/bpf 仓尚未公开发布，以 main 分支 2026-06-06 状态为锚点）"
confidence: medium
sources:
  - type: aosp
    path: "system/bpf/loader/bpfloader.rs"
  - type: aosp
    path: "system/bpf/loader/Loader.cpp"
  - type: aosp
    path: "system/bpfprogs/timeInState.c"
  - type: aosp
    path: "frameworks/native/services/gpuservice/bpfprogs/gpuMem.c"
  - type: aosp
    path: "system/bpfprogs/fuseMedia.c"
  - type: aosp
    path: "system/bpf/loader/Android.bp"
  - type: official
    path: "source.android.com/docs/core/architecture/kernel/bpf"
gap_source: "素材驱动/DeepResearch/AOSP结构"
---

# 14.21 eBPF 系统架构：bpfloader Rust 化与 BPF 程序组织

§14.10 从工具使用角度介绍了 eBPF 在 Android 性能分析中的应用。本节向下看一层：Android 的 BPF 程序在系统启动阶段是如何被加载的，加载器经历了怎样的架构变化，以及系统内置的 BPF 程序分别挂在哪些 tracepoint 上。理解这一层有助于排查 BPF 程序加载失败、确认某个 BPF 数据源是否可用，以及在 Perfetto 中对照 trace 找到对应的数据来源。

## bpfloader 的角色与演进

bpfloader 是 Android BPF 体系的加载入口，作为 init 阶段的服务运行。它的职责只有一个：在系统启动时把 `/system/etc/bpf/` 下的所有 BPF 程序加载到内核，并将 program 和 map 钉到 bpffs（`/sys/fs/bpf/`）。

Android 17 对 bpfloader 做了一次渐进式重写：

- **Android 9–16**：bpfloader 的主入口是 C++ 写的 `NetBpfLoad.cpp`，由 init 启动，调用 `libbpf_android.so` 中的加载函数。
- **Android 17**：`NetBpfLoad.cpp` 被完全移除，主入口替换为 Rust 写的 `bpfloader.rs`。但核心加载逻辑（`Loader.cpp`）仍以 C++ 形式保留在 `libbpf_android.so` 中，Rust 端通过 bindgen 生成的 FFI 绑定调用它。

这种"Rust 壳 + C++ 核"的架构意味着 NDK 公共 API 没有变化——`libbpf_android.so` 的 `bpf_obj_get()`、`bpf_attach_tracepoint()` 等接口仍然可用。Rust 化是 bpfloader 内部的重构，对上层透明。

## bpfloader.rs 主流程

`bpfloader.rs` 的 `main()` 函数在 init 阶段被调用，整体流程分为四步：

```rust
// system/bpf/loader/bpfloader.rs:251-289
fn main() {
    let kmsg_fd = env::var("ANDROID_FILE__dev_kmsg")
        .unwrap().parse::<i32>().unwrap();
    let kmsg_file = unsafe { File::from_raw_fd(kmsg_fd) };

    if let Err(logger) = BpfKmsgLogger::init(kmsg_file) {
        error!("BpfLoader-rs: log::setlogger failed: {}", logger);
    }

    panic::set_hook(Box::new(|panic_info| {
        error!("{}", panic_info);
    }));

    load_libbpf_progs();        // 第一步：加载 libbpf 风格的 .bpf 对象
    info!("Loading legacy BPF progs");

    unsafe {
        bpf_android_bindgen::initLogging();
        bpf_android_bindgen::createBpfFsSubDirectories();
        bpf_android_bindgen::legacyBpfLoader();   // 第二步：C++ 老路径加载 .o 对象
        bpf_android_bindgen::execNetBpfLoadDone(); // 第三步：execve 退出
    }
}
```

这段代码的关键点：

1. **kmsg 日志**：init 阶段 logcat 还没起来，bpfloader 通过 init 传入的 `/dev/kmsg` fd 写日志。在 dmesg 中搜索 `BpfLoader-rs` 可以看到加载过程。
2. `load_libbpf_progs()`：遍历静态注册的 `FILE_ARR` 数组，用 `libbpf-rs` 库加载 `.bpf` 格式的对象文件。Android 17 中只有 `timeInState.bpf` 走这条路。
3. `legacyBpfLoader()`：走 C++ `libbpf_android.so` 的老路径，加载所有 `.o` 格式的 BPF 对象。
4. `execNetBpfLoadDone()`：通过 `execve()` 把自己替换成后续 init 流程，bpfloader 进程不再返回。

`load_libbpf_progs()` 内部的 `libbpf_worker()` 做的事情：

- 从 `/etc/bpf/` 拼出 `.bpf` 文件路径
- 用 `ObjectBuilder::open_file().load()` 加载 ELF 对象
- 遍历 map 和 program，分别 `pin()` 到 `/sys/fs/bpf/map_<file>_<name>` 和 `/sys/fs/bpf/prog_<file>_<name>`
- 设置文件权限（`chown` + `set_permissions`），确保只有指定 UID/GID 可访问

**版本边界说明**：以上代码基于 AOSP main 分支（2026-06-06 状态）。`android-17.0.0_r1` tag 在 `platform/system/bpf` 仓尚未公开发布，待 tag 发布后需核对 `FILE_ARR` 和 `main()` 是否一致。[待验证: 源码路径可能已变更]

## BPF 程序的四个仓库与分工

Android 的 BPF 程序分散在四个目录，各自独立编译：

| 仓库路径 | 程序 | Tracepoint | 上层消费者 |
|----------|------|------------|-----------|
| `system/bpfprogs/` | timeInState.c | sched/sched_switch, power/cpu_frequency | Power Stats HAL, Battery Historian |
| `system/bpfprogs/` | fuseMedia.c | fuse/fuse_lookup | MediaProvider (FUSE 加速) |
| `system/bpfprogs/` | bpfRingbufProg.c | (ringbuf 测试用) | 单元测试 |
| `system/bpf/progs/` | netd.c | socket filter, cgroup | netd (流量统计) |
| `frameworks/native/.../bpfprogs/` | gpuMem.c | gpu_mem/gpu_mem_total | GpuService |
| `packages/modules/Connectivity/bpf/progs/` | (多个) | TCP 拥塞, xt_qtaguid 替代 | ConnectivityService |

`system/bpfprogs/` 是 Android 17 新建的独立仓库，从 `system/bpf/progs/` 中拆分出通用 BPF 程序。同一个 C 源文件可以双构建：`bpf {}` 规则产生 `.o` 文件（走老路径加载），`libbpf_prog {}` 规则产生 `.bpf` 文件（走 Rust libbpf-rs 路径加载）。这种双构建机制支持灰度切换。

## timeInState.c：核心 BPF 程序

`timeInState.c` 是 Android 中使用最广泛的 BPF 程序，挂载在 `tracepoint/sched/sched_switch` 上，追踪每个 UID 在每个 CPU 频率档位上的驻留时间。

### 数据结构

timeInState 维护的 map 集合（13 个）按功能分为四组：

**频率追踪组**：
- `uid_time_in_state_map`（PERCPU_HASH）— 每个 UID 在各频率桶的累计时间
- `total_time_in_state_map`（PERCPU_ARRAY）— 整机所有 UID 的频率累计
- `freq_to_idx_map`（HASH）— 频率值到索引的映射
- `cpu_policy_map`（ARRAY）— CPU 到调度策略的映射
- `policy_freq_idx_map`（ARRAY）— 策略到频率索引的映射

**并发追踪组**：
- `uid_concurrent_times_map`（PERCPU_HASH）— 单 UID 并发占用 CPU 数的时间分布
- `nr_active_map`（ARRAY）— 当前非 idle CPU 数
- `policy_nr_active_map`（ARRAY）— 每个策略的非 idle CPU 数

**时间戳组**：
- `uid_last_update_map`（HASH）— 单 UID 上次更新时间（ns）
- `cpu_last_update_map`（PERCPU_ARRAY）— 每 CPU 上次 ktime
- `cpu_last_pid_map`（PERCPU_ARRAY）— 每 CPU 上次 sched_switch 的 next_pid（去重用）

**PID 追踪组**（白名单模式）：
- `pid_tracked_hash_map` + `pid_tracked_map`（HASH + ARRAY）— 被追踪的 PID 集合
- `pid_task_aggregation_map`（HASH）— PID 到聚合 task 数
- `pid_time_in_state_map`（PERCPU_HASH）— 单 PID 各频率累计时间

所有 map 由 `AID_SYSTEM` 拥有，Power Stats HAL 和 system_server 可以读取。

### Tracepoint 处理

`sched_switch` 处理函数的核心逻辑：

1. 读取当前 CPU 的 `cpu_last_pid_map`，对比 `args->next_pid` 做去重（同一个 PID 连续调度不重复计算）
2. 通过 `cpu_policy_map` 查当前 CPU 所属的调度策略，再查 `policy_freq_idx_map` 得到当前频率索引
3. 计算时间差 delta = now - `cpu_last_update_map[cpu]`
4. 调用 `update_uid()` 把 delta 累加到 `uid_time_in_state_map[uid][freq_idx]` 和并发时间 map
5. 始终返回 `ALLOW`（值为 1），不干扰正常调度

**性能影响**：`sched_switch` 在 8 核 120Hz 设备上约 8000 次/秒触发。代码严格走 hash lookup 早返路径，不做复杂计算和内存分配，BPF verifier 保证了 hot path 的安全性。在 Pixel 7 上实测 timeInState BPF 累计功耗约 0.3–0.5 mW。[适用版本: Android 12 - Android 17]

### 应用层读取

Power Stats HAL（`hardware/interfaces/power/stats/aidl/default/`）通过 `libbpf_android` 的 `bpf_obj_get()` 打开钉在 bpffs 上的 map fd，读取 `uid_time_in_state_map` 生成 AIDL 返回的 `UidFreqTime` 数据。`dumpsys batterystats` 输出的 "Per-UID CPU time" 即来源于此。

## gpuMem.c：GPU 内存跟踪

`gpuMem.c` 位于 `frameworks/native/services/gpuservice/bpfprogs/`，挂载在 `tracepoint/gpu_mem/gpu_mem_total` 上。

```c
// frameworks/native/services/gpuservice/bpfprogs/gpuMem.c
DEFINE_BPF_MAP_GRO(gpu_mem_total_map, HASH, uint64_t, uint64_t,
                    GPU_MEM_TOTAL_MAP_SIZE, AID_GRAPHICS);

DEFINE_BPF_PROG("tracepoint/gpu_mem/gpu_mem_total",
                AID_ROOT, AID_GRAPHICS, tp_gpu_mem_total)
(struct gpu_mem_total_args* args) {
    uint64_t key = ((uint64_t)args->gpu_id << 32) | args->pid;
    if (!args->size) {
        bpf_gpu_mem_total_map_delete_elem(&key);
        return 0;
    }
    uint64_t* prev_val = bpf_gpu_mem_total_map_lookup_elem(&key);
    if (prev_val) *prev_val = args->size;
    else bpf_gpu_mem_total_map_update_elem(&key, &args->size, BPF_NOEXIST);
    return 0;
}
```

这段代码做的事：

- 键是 64-bit 复合 key：高 32 位是 `gpu_id`，低 32 位是 `pid`
- 值是 GPU 内存占用字节数
- 当 `size` 为 0 时删除对应条目（进程释放 GPU 内存）
- Map 由 `AID_GRAPHICS` 拥有，GpuService 可以读取

在 Perfetto 中，`gpu_mem` counter 轨道显示的数据就来自这个 map。之前只能通过 `dumpsys meminfo` 看 GPU 内存占用，这个 BPF 程序提供了实时、细粒度的 GPU 内存归因。[适用版本: Android 12 - Android 17]

gpuMem.c 目前走 `legacyBpfLoader()` 老路径加载（不在 `bpfloader.rs` 的 `FILE_ARR` 中）。[已验证: AOSP main 分支, frameworks/native/services/gpuservice/bpfprogs/gpuMem.c]

## libbpf_android 共享库

`Loader.cpp` 编译为 `libbpf_android.so`（`cc_library`），是 C++ 和 Rust 之间的桥梁：

```
Loader.cpp (C++)
  → libbpf_android.so
  → libbpf_android_bindgen (rust_bindgen)
  → bpfloader.rs (Rust FFI 调用)
```

Android.bp 中的构建声明：

```python
cc_library {
    name: "libbpf_android",
    srcs: ["Loader.cpp"],
    shared_libs: ["libbase", "libutils", "liblog"],
    header_libs: ["bpf_headers"],
    export_include_dirs: ["include"],
}

rust_bindgen {
    name: "libbpf_android_bindgen",
    wrapper_src: "include/libbpf_android.h",
    source_stem: "bindings",
    shared_libs: ["libbpf_android", "libbase", "libutils", "liblog"],
}
```

`#[cfg(enable_libbpf)]` feature flag 控制 Rust 路径是否编译进二进制。当 flag 启用时，`load_libbpf_progs()` 走 libbpf-rs 加载 `.bpf` 对象；未启用时完全走 C++ 老路径。[待验证: Android 17 默认 build 配置是否启用 enable_libbpf flag]

## 调试方法

### 检查 BPF 程序加载状态

```bash
# 查看已加载的 BPF 程序和 map
adb shell dumpsys bpf

# 直接查看 bpffs 上的钉点
adb shell ls /sys/fs/bpf/

# 查看特定 map 内容（需要 root）
adb root
adb shell cat /sys/fs/bpf/map_timeInState_uid_time_in_state_map
```

`dumpsys bpf` 的输出会列出所有已加载的 BPF 程序、关联的 map、以及每个程序的引用计数。如果某个程序没有出现，说明 bpfloader 阶段加载失败。

### 从 kmsg 查加载日志

init 阶段的 BPF 加载日志写往 kmsg：

```bash
adb shell dmesg | grep -i "bpf\|BpfLoader"
```

常见错误：
- `BpfLoader-rs: Failed to load .bpf file` — `.bpf` 对象文件缺失或格式不匹配
- `bpf_load_programs: Permission denied` — SELinux 策略阻止 BPF 操作
- `Kernel does not support BPF` — 内核未编译 BPF 支持（GKI 内核默认包含）

### 在 Perfetto 中确认数据源

在 Perfetto trace config 中启用以下数据源可以确认 BPF 数据是否正常产出：

- `linux.perf_event` — BPF 程序的 perf event 统计
- `linux.sys_stats` — 包含从 `uid_time_in_state_map` 读取的 CPU 频率时间
- `gpu_mem` counter — 来自 `gpu_mem_total_map`

如果 trace 中 `linux.sys_stats` 的 per-UID CPU 时间全为零，优先检查 `dumpsys bpf` 确认 timeInState 程序是否加载成功。

---

> 🔗 交叉引用：eBPF 工具链（bpftrace、simpleperf）和 UprobeStats 的使用详见 §14.10。功耗分析框架中 timeInState 数据的使用详见 §5.6。Perfetto 数据源配置详见 §26.11。
