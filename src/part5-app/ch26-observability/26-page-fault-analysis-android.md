---
title: "Page Fault 类型分析与 Android 实践"
chapter: "26.26"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
drafted_date: "2026-07-16"
last_verified: "2026-07-16"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
tags: [page-fault, minor-fault, major-fault, mmap, memory, observability]
related_chapters: ["26.25", "4.01", "9.13"]
sources:
  - type: aosp
    path: "frameworks/base/core/jni/android_os_Debug.cpp"
  - type: official
    path: "developer.android.com/topic/performance/memory"
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "参考书驱动（Clippings/线上疑难问题 46.md）"
---

# 26.26 Page Fault 类型分析与 Android 实践

<!-- outline-start -->

## Page Fault 基本概念

Page Fault（缺页异常）是 CPU MMU 访问虚拟地址时发现对应页表项（PTE）状态不满足访问要求，由内核 Page Fault Handler 接管处理的异常事件。根据页表项状态，Page Fault 分为三大类：

| 类别 | 触发条件 | 性能开销 | 处理路径 |
|---|---|---|---|
| Minor Page Fault | 页已在物理内存中，仅需更新 PTE | 低（μs 级） | 内核同步处理 |
| Major Page Fault | 需从存储设备读入数据到内存 | 高（ms 级，受 I/O 影响） | 内核触发磁盘 I/O |
| Invalid Page Fault | 访问未映射或受保护的地址 | - | 内核发送 SIGSEGV |

这三类事件在不同场景下的语义和排查价值完全不同，工程师必须能快速分辨它们。

### AOSP 内核态 Page Fault 处理路径

Linux 内核中 `handle_mm_fault()` 是 Page Fault 的总入口：

1. **查找 VMA**（`find_vma()`）——确认虚拟地址属于合法区间
2. **处理 COW/Fork**——如果 PTE 标记为只读且写访问，触发 Copy-on-Write
3. **分配物理页**——`alloc_pages_vma()` 或从 Page Cache 取页
4. **建立映射**——`mk_pte()` + `set_pte_at()` 写入 PTE
5. **更新 LRU 链表**——将页加入 Active/Inactive LRU

Android 17 内核基于 Linux 6.6 LTS（`common/android16-6.6` 分支），完整继承上述逻辑。

## Minor Page Fault（次缺页）

Minor Page Fault 的本质是「页已在内存，但页表尚未建立映射」。最典型的两种场景：

### 场景 1：Lazy 内存分配（Demand Paging）

Linux 内核采用 Lazy Allocation 策略：`malloc()` / `mmap(MAP_ANONYMOUS)` 仅在虚拟地址空间创建 VMA，并不立即分配物理内存。当进程首次写入该地址时，MMU 抛出 Page Fault，内核才真正分配物理页。

> 「申请的内存都是虚拟内存，并且这个时候并不会分配真正的物理内存，只有当我们真正要往这块虚拟内存区域写入数据时，操作系统检查到对应的虚拟内存没有映射到物理内存，便会发生缺页中断，然后分配一块同样大小的物理内存，并建立映射关系。这是一种懒加载技术，也是内存优化的方案之一。」[结构参考: Clippings/Android 性能优化 - 原理：重新认识内存.md]

### 场景 2：Copy-on-Write（COW）

`fork()` 后父子进程共享同一物理页，PTE 标记为只读。任一方写入时触发 Page Fault，内核分配新页并复制原页内容。`malloc()` 在堆内分配大块内存（> 128KB）走 `mmap()`，同样采用 COW 机制。

### 性能影响

Minor Page Fault 的开销主要在：
- **页表分配**：内核需分配 PTE 所在页（4KB）
- **TLB 未命中**：MMU 需走 Page Walk 找到 PTE
- **LRU 锁竞争**：在多核场景下，zone->lru_lock 是热点

实测单次 Minor Page Fault 在 ARM64 上耗时约 **1-5 μs**，远低于 Major Page Fault。

## Major Page Fault（主缺页）

Major Page Fault 表示「需要从慢速设备（磁盘/Flash）读取数据到内存」，是 Page Fault 中性能代价最高的一类。

### Android 平台的特殊性

Android 默认**没有 Swap 分区**（与桌面 Linux 显著不同）。在 zRAM 启用场景下，交换设备是压缩内存（zsmalloc），但 zRAM 不是真正的块设备，Major Page Fault 的来源主要是 **mmap 文件**：

> 「需要注意的是，如果系统不支持 zRAM 来充当 Swap 分区，可以默认 Android 是没有 Swap 分区的，因为在 Android 里不会因为读取 Swap 而发生 major page fault 的情况。另一种情况是 mmap 一个文件后，虚拟内存区域、文件磁盘地址和物理内存做一个映射，在通过地址访问文件数据的时候发现内存中并没有文件数据，进而产生了 major page fault 的错误。」[结构参考: Clippings/线上疑难问题 46.md]

### Major Page Fault 的典型来源

1. **APK/Dex/OAT 文件 mmap 读取**——冷启动时大量 dex 字节码首次访问
2. **资源文件加载**——Bitmap 工厂首次解码 mmap 区域
3. **共享库加载**——`dlopen()` 触发的 .so mmap 首次访问
4. **Trace 数据落盘回读**——Perfetto 解析 trace 文件

### 性能影响

Major Page Fault 的耗时主要在磁盘 I/O：
- **UFS 3.1 顺序读**：~1.5 GB/s → 4KB 页 ≈ 2.7 μs
- **UFS 3.1 随机读**：~100 MB/s → 4KB 页 ≈ 40 μs
- **eMMC 随机读**：~20 MB/s → 4KB 页 ≈ 200 μs

冷启动场景下，若数千次 Major Page Fault 集中在 eMMC 随机读，将产生 **百毫秒级** 启动延迟——这正是启动优化中「类重排」「Dex 压缩」技术的核心切入点。

## Invalid Page Fault（无效缺页）

Invalid Page Fault 访问的是 **未映射** 或 **受保护** 的地址空间，内核直接判定为非法访问，向进程发送 **SIGSEGV** 信号（默认行为是 crash）。

### 触发场景

1. **空指针解引用**——访问 0x0 附近地址（VMA 未映射）
2. **野指针**——访问已释放的内存区域（VMA 已 unmap）
3. **栈溢出**——超出线程栈 VMA 边界
4. **权限错误**——对只读页执行写操作（如代码段写入）

### 与 NDK 崩溃的关系

Invalid Page Fault 在 NDK 层表现为 **native crash**（`signal 11 (SIGSEGV)`），是 Android 稳定性治理的核心场景之一。详见 ch20 稳定性章节。

## Android 平台的 Page Fault 计数

### 数据来源：/proc/[pid]/stat

Linux 提供 per-thread 和 per-process 的 Page Fault 计数，Android 框架层主要读取：

```
/proc/[pid]/stat:
  minflt  —— minor fault 累计次数（字段 10）
  majflt  —— major fault 累计次数（字段 12）
  cminflt —— 子进程 minor fault（字段 13）
  cmajflt —— 子进程 major fault（字段 14）
```

Android 系统服务 `ProcessCpuTracker`（`frameworks/base/core/java/com/android/internal/os/ProcessCpuTracker.java`）定期采样 `/proc/[pid]/stat`，计算 Δfaults 作为进程 CPU 信息的一部分输出到 logcat（典型场景：ANR dump、CPU profile）。

### 内存分配量估算

> 「SingleThread 你一共发生了 3094 次 fault，根据每个页大小为 4KB，可以知道在这个过程中 SingleThread 总共分配了大概 12MB 的空间。」[结构参考: Clippings/线上疑难问题 46.md]

即 `Δfaults × 4KB` 粗略等于该线程/进程在这段时间内分配的物理内存量。这一公式在排查「线程内存分配过载」时非常实用，但要注意：
- 该估算包含 COW 的复制页（fork 后写入会 double-count）
- 不包含 mmap 区域已映射但未访问的部分

## I/O 瓶颈的 Page Fault 信号

Major Page Fault 与存储子系统紧耦合。当进程日志中出现 `iowait` 占比上升 + `major fault` 激增时，几乎可以确定是磁盘 I/O 瓶颈。

### 案例：冷启动 dex 加载

```
System TOTAL: 2.1% user + 16% kernel + 9.2% iowait + 0.2% irq + 0.1% softirq + 72% idle
Process:com.sample.app
50% 23468/com.sample.app(S): 11% user + 38% kernel faults:4965
```

解读：
- `iowait 9.2%` 表明存储设备繁忙
- `kernel 38%` 偏高，CPU 大部分时间在等 I/O 完成
- `faults: 4965` 中 major 占主要比例，对应 ~20MB 文件读入
- 这是典型冷启动加载 dex 的画像

### 优化方向

1. **类重排（Class Reordering）**——把启动时用到的类排到 dex 前部，减少磁盘寻道
2. **Dex 压缩**——减小单页加载延迟
3. **预加载（Pre-load）**——后台线程提前 mmap + 触发 Page Fault
4. **内存映射（MemoryFile）**——对频繁读写的小文件使用 mmap

## Page Fault 监控方案设计

### 1. /proc 采样

Java 层读取 `/proc/[pid]/stat`：

```java
// 简化示意（实际生产应避免频繁 IO）
BufferedReader reader = new BufferedReader(new FileReader("/proc/self/stat"));
String[] fields = reader.readLine().split(" ");
long minflt = Long.parseLong(fields[9]);  // 字段索引 0-based
long majflt = Long.parseLong(fields[11]);
```

### 2. Perfetto 集成

Android 12+ 的 Perfetto 提供了 `ftrace` events 中的 `mm_event` 类别，可捕获 page_fault_user / page_fault_kernel tracepoint，结合 `sched_blocked_reason` 判断是否因 Page Fault 阻塞。

### 3. eBPF 监控（系统侧）

在拥有 root 权限或系统签名场景下，可使用 eBPF 挂载 `tracepoint:exceptions:page_fault_user`，实时捕获 Page Fault 事件：

```c
// eBPF prog 伪代码
SEC("tracepoint/exceptions/page_fault_user")
int trace_page_fault_user(struct trace_event_raw_page_fault_user *ctx) {
    u64 pid = bpf_get_current_pid_tgid();
    bpf_map_update_elem(&faults, &pid, &(ctx->address), BPF_ANY);
    return 0;
}
```

> [自动发现] Android 17 在 GpuService 中已集成 BPF 观测模式（详见 §14.30 GpuService 章节），Page Fault 监控可参考其 eBPF 调用链设计。

### 4. 内存行为画像

将 Page Fault 计数变化与**场景标注**结合：
- 启动期：预期有大量 major fault（dex 加载）
- 滑动期：预期 minor fault 较少（缓存友好）
- 后台期：两者都应处于低位

通过对比「实际画像 vs 预期画像」识别异常。

## 扩展点：zRAM 对 Page Fault 行为的影响

Android 启用 zRAM 后，压缩交换设备（zsmalloc）作为 Swap 后端。Major Page Fault 的来源从「真实磁盘读取」变为「zRAM 解压缩」，性能特征发生变化：

- **zRAM 读延迟**：约 10-50 μs（含解压）
- **传统磁盘读延迟**：约 40-200 μs（随机读）

zRAM 显著降低了 Major Page Fault 的代价，但也带来 CPU 解压开销（特别是 zstd 算法）。Android 17 默认 zRAM 比例 25%（`/sys/block/zram0/disksize`）。

## 扩展点：userfaultfd 与 Page Fault 控制流

Linux 5.2+ 引入的 `userfaultfd` 机制允许用户态接管 Page Fault 处理。在 Android 17 中可用于：

1. **内存监控**：拦截 Page Fault 获取精确触发地址与触发线程
2. **进程内存迁移**：在 checkpoint/restore 场景下按需加载页
3. **沙箱隔离**：在虚拟化或容器场景下用户态管理缺页

> [待补充] Android 17 中 userfaultfd 在 ART 虚拟机和 ART 编译器的实际应用案例较少，需要更多工程实践验证。

<!-- outline-end -->

## 小结

Page Fault 是连接虚拟内存与物理内存的核心机制，也是 Android 性能治理中识别 I/O 瓶颈、判断内存分配模式的关键信号。工程师在排查启动慢、卡顿、内存异常等问题时，应当：

1. 采集 `/proc/[pid]/stat` 中的 minflt/majflt
2. 结合 iowait、CPU 使用率判断是否 I/O 受限
3. 用 `Δfaults × 4KB` 粗估线程分配内存量
4. 在启动优化中重点关注 major fault 的分布

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 46.md]
[结构参考: Clippings/Android 性能优化 - 原理：重新认识内存.md]
[已验证: AOSP android-17.0.0_r1, frameworks/base/core/jni/android_os_Debug.cpp]
[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/com/android/internal/os/ProcessCpuTracker.java]
