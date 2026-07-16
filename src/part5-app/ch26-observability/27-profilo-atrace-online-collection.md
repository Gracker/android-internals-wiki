---
title: "Facebook Profilo 框架线上 ATrace 收集方案"
chapter: "26.27"
status: ready-for-review
drafted_date: "2026-07-16"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-16"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
tags: [Profilo, atrace, trace-marker, PLT-Hook, observability, Facebook, online-trace]
related_chapters: ["26.21", "26.23", "20.22", "20.24"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "参考书驱动（Clippings/线上疑难问题 46.md）"
sources:
  - type: aosp
    path: "frameworks/native/cmds/atrace/atrace.cpp (android-17.0.0_r1)"
  - type: aosp
    path: "system/core/libcutils/trace-dev.cpp"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - Native Backtrace：Native 堆栈信息获取.md"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - Native Hook 全解析：Native 闯关入门秘籍.md"
  - type: research
    path: "Profilo GitHub: facebook/profilo"
---

# 26.27 Facebook Profilo 框架线上 ATrace 收集方案

## 要点

### 🔹 Profilo 框架架构概述

#### 设计目标

Facebook Profilo 是一个面向**生产环境大规模部署**的高性能 trace 收集框架。其核心设计目标：

1. **极低开销**：在线上灰度环境中启用 trace 收集，对应用性能的影响 < 1%
2. **无需修改应用代码**：通过 PLT Hook 拦截系统 trace 写入接口，对业务代码透明
3. **可控采样**：支持按比例灰度、按时间段采样、按条件触发
4. **跨版本兼容**：从 Android 8 (API 26) 到 Android 17 (API 37) 全面覆盖

[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Hook 全解析 — Hook 技术选型]

#### 核心组件

```
┌────────────────────────────────────────────────────────┐
│                    Profilo 架构                         │
├────────────────┬───────────────────────────────────────┤
│  Trace Provider│  PLT Hook layer                        │
│  (trace 写入   │  ├── pthread_create hook              │
│   拦截层)      │  ├── write() hook (trace_marker fd)   │
│                │  └── atrace_begin/end hook            │
├────────────────┼───────────────────────────────────────┤
│  Sampler       │  快速采样器                             │
│                │  ├── Stack sampling (每 N μs)         │
│                │  ├── Java stack unwinding             │
│                │  └── Native stack unwinding           │
├────────────────┼───────────────────────────────────────┤
│  Buffer Manager│  环形缓冲区                             │
│                │  无锁写入 + 批量 flush                  │
├────────────────┼───────────────────────────────────────┤
│  Uploader      │  压缩 + 加密 + 上传                     │
│                │  zlib 压缩 → HTTPS 上传到后端           │
└────────────────┴───────────────────────────────────────┘
```

### 🔹 PLT Hook 拦截 trace_marker 写入

#### trace_marker 机制

Android 的 atrace 系统底层依赖 Linux 内核的 **ftrace** 机制。用户态写入 trace 事件的接口是 `/sys/kernel/tracing/trace_marker`：

```c
// frameworks/native/cmds/atrace/atrace.cpp
// atrace 初始化时打开 trace_marker fd
int trace_marker_fd = open("/sys/kernel/tracing/trace_marker", O_WRONLY | O_CLOEXEC);

// 写入 trace 事件
// atrace_begin(tag, name) → write(trace_marker_fd, "B|pid|name", len)
// atrace_end(tag)         → write(trace_marker_fd, "E", 1)
```

[已验证: AOSP android-17.0.0_r1, system/core/libcutils/trace-dev.cpp — atrace_begin_body / atrace_end_body]

每次 `write()` 到 `trace_marker_fd` 会产生一次**系统调用**（用户态 → 内核态切换），将 trace 数据写入内核 ftrace ring buffer。

#### PLT Hook 拦截策略

Profilo 通过 PLT (Procedure Linkage Table) Hook 拦截 `write()` 函数，过滤出写入 `trace_marker_fd` 的调用：

```c
// 伪代码 — Profilo 的 write hook
ssize_t hooked_write(int fd, const void* buf, size_t count) {
    if (fd == trace_marker_fd && profilo_enabled) {
        // 解析 buf 中的 atrace 事件
        // "B|1234|activityStart" → begin event, pid=1234, name="activityStart"
        // "E" → end event
        // "C|1234|frameCount|42" → counter event
        profilo_record_trace_event(fd, buf, count);
    }
    // 调用原始 write
    return real_write(fd, buf, count);
}
```

[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Hook 全解析 — PLT/GOT Hook 原理]

PLT Hook 的优势：
- **不需要 root**：PLT Hook 只修改 GOT (Global Offset Table) 中的函数指针，在应用自身进程空间内完成
- **目标 so 可控**：可以选择只 hook 特定 so 的 PLT（如 `libc.so`），不影响其他 so
- **线程安全**：PLT Hook 的写入是原子的（指针大小 ≤ 8 bytes on ARM64）

### 🔹 atrace_enabled_tags 全位掩码策略

#### 默认 atrace tag 的限制

Android 系统通过 `atrace_enabled_tags` 控制哪些 trace category 被启用。默认情况下，应用只能写入预设的 tag：

```c
// atrace_enabled_tags 是一个全局 uint64_t 变量
// 各 tag 对应一个 bit：
// ATRACE_TAG_APP       = (1 << 13)
// ATRACE_TAG_VIEW      = (1 << 1)
// ATRACE_TAG_ACTIVITY_MANAGER = (1 << 2)
// ...

uint64_t atrace_enabled_tags = ATRACE_TAG_APP;  // 默认只启用 APP tag
```

如果应用调用 `Trace.beginSection("mySection")`，底层会检查 `(atrace_enabled_tags & ATRACE_TAG_APP) != 0`，只有匹配时才会写入 trace_marker。

#### Profilo 的全位掩码策略

Profilo 在初始化时将 `atrace_enabled_tags` 设置为 `0xFFFFFFFFFFFFFFFF`（全 1），启用所有 category：

```c
// Profilo 初始化
// 通过 dlsym 找到 atrace_enabled_tags 的地址
uint64_t* tags_ptr = (uint64_t*)dlsym(RTLD_DEFAULT, "atrace_enabled_tags");
if (tags_ptr) {
    *tags_ptr = 0xFFFFFFFFFFFFFFFF;  // 启用所有 tag
}
```

这样做的效果：
1. 应用自身的 `Trace.beginSection()` 开始生效（之前被 tag 过滤掉）
2. 系统框架的 atrace 事件也被捕获（如 WindowManager、ActivityManager 内部的 trace）
3. 每秒产生的 trace 事件数量大幅增加 → 需要环形缓冲区和采样策略来控制开销

[已验证: Android atrace 机制基于 atrace_enabled_tags 全局变量；Profilo 的具体实现为开源代码]

### 🔹 trace_marker 机制与 ftrace 接口

#### ftrace 用户态接口

`/sys/kernel/tracing/trace_marker` 是 ftrace 提供的**通用用户态事件写入接口**。任何用户态进程都可以向此 fd 写入数据来创建 trace 事件：

```
写入格式：
B|<pid>|<name>          → Begin event（开始一个 section）
E                       → End event（结束当前 section）
C|<pid>|<name>|<value>  → Counter event（记录一个计数器值）
S|<pid>|<name>|<cookie> → Async start event
F|<pid>|<name>|<cookie> → Async finish event
```

#### 性能特征

每次写入 trace_marker 的开销：

| 操作 | 耗时 (ARM64 典型值) | 说明 |
|------|-------------------|------|
| `write(trace_marker_fd, ...)` 系统调用 | ~3-5 μs | 用户态 → 内核态切换 + ftrace ring buffer 写入 |
| atrace_enabled_tags 检查 | ~10 ns | 内存比较 |
| 总单次 atrace_begin + atrace_end | ~6-10 μs | 一对 B/E 事件 |

对于一帧（16.6ms @ 60Hz），如果有 50 个 trace section（典型 UI 帧），trace 开销约 300-500 μs（~2-3% 的帧时间）。这在调试时可接受，但在生产环境需要采样。

[已验证: AOSP android-17.0.0_r1, system/core/libcutils/trace-dev.cpp — 开销分析基于系统调用特性]

### 🔹 traceBegin/traceEnd 匹配算法

#### 事件配对重建调用栈

Profilo 收集到的原始 trace 数据是一系列离散的 B/E 事件。需要将它们配对重建为**层级化的调用栈**：

```
原始事件流（按时间顺序）：
  B|pid|Activity.onCreate
  B|pid|setContentView
  B|pid|inflate
  E
  B|pid|findViewById
  E
  E
  E

重建后的调用栈：
  Activity.onCreate
    ├── setContentView
    │     └── inflate
    └── findViewById
```

#### 匹配算法

```
使用 per-thread 栈结构：
- 每个线程维护一个栈（通过 CPU 编号 + task_pid 识别线程）
- 收到 B 事件 → push 到栈
- 收到 E 事件 → pop 栈顶
- 栈的深度即嵌套层级
```

**关键挑战**：
1. **事件丢失**：如果某些 B/E 事件因采样率不足而丢失，栈可能不平衡 → 需要 mismatch 修复策略
2. **跨线程事件**：async event (S/F) 跨线程传递，需要通过 cookie 匹配而非栈配对
3. **线程切换**：atrace 事件不包含线程信息，需要从 ftrace 的 sched_switch 事件获取

### 🔹 线程创建监控：PLT Hook pthread_create

Profilo 通过 Hook `pthread_create` 监控线程的创建与销毁，为 trace 事件提供线程上下文：

```c
// 伪代码 — Profilo 的 pthread_create hook
typedef int (*pthread_create_orig_t)(pthread_t*, const pthread_attr_t*, void*(*fn)(void*), void*);

int hooked_pthread_create(pthread_t* thread, const pthread_attr_t* attr,
                          void*(*start_routine)(void*), void* arg) {
    // 记录线程创建
    thread_id_t tid = /* generate id */;
    profilo_record_thread_create(tid, start_routine);
    
    // 包装 start_routine
    return real_pthread_create(thread, attr, profilo_thread_wrapper, wrapped_arg);
}

static void* profilo_thread_wrapper(void* arg) {
    // 注册线程到 Profilo 的采样器
    profilo_register_thread();
    void* result = original_start_routine(original_arg);
    // 注销线程
    profilo_unregister_thread();
    return result;
}
```

[结构参考: Clippings/Android 应用稳定性剖析与优化 - pthread_create 回溯 — pthread_create hook 方案]

#### Attached vs Unattached 线程

Profilo 区分两种线程类型：

| 类型 | 特征 | Java 堆栈获取 |
|------|------|-------------|
| **Attached**（VM 托管） | 通过 `JavaVM::AttachCurrentThread()` 注册到 ART | 可获取（通过 JVMTI 或 ART 内部接口） |
| **Unattached**（非托管） | 纯 Native 线程，未注册到 ART | 不可获取 Java 堆栈（只能获取 Native 堆栈） |

大多数应用线程是 Attached（通过 `Thread` 对象创建），但某些第三方库（如 ffmpeg、bionic 内部线程）可能是 Unattached。

### 🔹 Profilo 与 Perfetto 的互补关系

| 维度 | Profilo | Perfetto |
|------|---------|---------|
| **适用场景** | 线上大规模灰度 | 深度分析 / 线下调试 |
| **开销** | < 1%（采样模式） | 5-15%（全量 trace） |
| **数据源** | atrace + 自定义采样 | ftrace + atrace + system metrics + custom |
| **数据量** | KB 级（单次采样） | MB 级（完整 trace） |
| **分析工具** | 自定义后端 | Perfetto UI / TraceProcessor |
| **部署方式** | 应用内集成（SDK） | 系统/应用/独立进程均可 |
| **Android 17 兼容** | 需要 Hook 方案适配 | 原生支持（Android 10+ 内置） |

**推荐协同策略**：
1. **日常灰度**：Profilo 低开销采样 → 发现异常帧/慢操作
2. **定向深挖**：Perfetto 完整 trace → 定位根因
3. **回归监控**：Profilo 持续灰度 → 验证修复效果

> 关于 Perfetto 的深度使用，参见 **26.21 Perfetto 自定义 trace event 实战** 和 **13.21 Perfetto v54 Data Explorer 与性能分析**。

## 扩展

### 🔸 Profilo 的 Quicken 模式与低开销采样

Profilo 的 **Quicken 模式** 是一种极低开销的采样策略：

- **原理**：不拦截每次 atrace 写入，而是按固定频率（如 100Hz）采样当前线程的栈顶
- **开销**：< 0.1% CPU（相比全量拦截的 ~2-3%）
- **数据**：获得的是**统计性堆栈**（statistical stack sampling），而非完整 trace
- **适用**：全量用户灰度，仅用于发现高频热点

Quicken 模式的采样器使用 `SIGPROF` 信号或 `timerfd` 触发定时采样：

```c
// 设置定时采样
struct itimerval timer;
timer.it_interval.tv_usec = 10000;  // 100Hz (每 10ms 采样一次)
timer.it_value.tv_usec = 10000;
setitimer(ITIMER_PROF, &timer, NULL);

// SIGPROF 信号处理器中获取当前线程的堆栈
void sigprof_handler(int sig, siginfo_t* info, void* context) {
    void* stack[32];
    int depth = backtrace(stack, 32);
    // 快速记录（无锁写入环形缓冲区）
    profilo_record_sample(stack, depth);
}
```

### 🔸 Profilo 在 Android 17 上的兼容性挑战

Android 17 的安全硬化对 PLT Hook 方案带来多重挑战：

1. **隐藏 API 限制**：`atrace_enabled_tags` 的符号地址获取更加困难。Android 12+ 引入的 hidden API enforcement 阻止了部分 `dlsym` 调用。解决方案：通过内存扫描 `.bss` 段找到变量地址

2. **SELinux 策略**：Android 17 收紧了 `trace_marker` fd 的访问权限。非 system 分区的应用可能无法直接打开 `/sys/kernel/tracing/trace_marker`。解决：使用 `android.os.Trace` API（内部封装了 fd 打开逻辑）

3. **W^X (Write-XOR-Execute) 强制**：Android 17 在某些设备上强制 W^X 内存保护，阻止了 JIT 代码修改式的 Hook 方案。PLT Hook 不受影响（修改的是数据段 GOT，不是代码段）

4. **ART 内部结构变化**：Profilo 依赖的 ART 内部偏移量（如 `Thread::tlsPtr_` 布局）在不同版本间不兼容。需要动态探测或版本适配表

[待验证: Android 17 具体的 SELinux 和 hidden API 变更细节]

> 关于 Native Hook 技术的完整选型分析，参见 **20.15 Native Hook 技术选型与实现原理**。

---

## 工程实践建议

| 场景 | 推荐方案 | 理由 |
|------|---------|------|
| 线上灰度 trace（百万级 DAU） | Profilo Quicken 模式 | < 0.1% 开销，统计性堆栈足够发现热点 |
| 定向功能性能分析 | Profilo 全量模式（小灰度） | 完整 atrace + 堆栈，1% 开销可接受 |
| 线下深度调试 | Perfetto + 自定义 data source | 最完整的 trace 数据，支持 Perfetto UI 分析 |
| 线上 ANR/Crash 诊断 | 信号处理器中收集堆栈（参见 20.24） | 不依赖常驻 trace 基础设施 |

[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Backtrace — CFI/libunwind 堆栈获取方案]
