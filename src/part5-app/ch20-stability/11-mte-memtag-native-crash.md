---
title: "MTE memtagMode 与 Native 崩溃治理"
chapter: "20.11"
section: "20.11"
status: finalized
drafted_date: "2026-05-16"
applicable_versions: "Android 12 (API 31) - Android 16 (API 36)"
last_verified: "2026-05-16"
last_verified_against: "AOSP main / Android Developers docs / source.android.com MTE docs"
confidence: medium
tags: ["mte", "memtag", "native-crash", "stability", "security"]
related_chapters: ["4.5", "10.5", "14.3", "20.3", "23.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "素材驱动/官方文档"
sources:
  - type: official
    path: "https://source.android.com/docs/security/test/memory-safety/arm-mte"
  - type: official
    path: "https://source.android.com/docs/security/test/memory-safety/mte-configuration"
  - type: official
    path: "https://developer.android.com/ndk/guides/arm-mte"
  - type: official
    path: "https://developer.android.com/ndk/guides/memory-debug"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/Zygote.java"
  - type: aosp
    path: "frameworks/base/core/jni/com_android_internal_os_Zygote.cpp"
  - type: aosp
    path: "bionic/libc/bionic/malloc_common.cpp"
  - type: material
    path: "DeepResearch/2026-05-13-android-mte-memtag-async-asymm-analysis.md"
  - type: structure
    path: "Clippings/Android 应用稳定性剖析与优化 - Native Crash 监控：为我们应用插上监控 Native Crash 的电子眼.md"
pipeline_stage: ready-to-publish
task6_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: "2026-05-16"
task6_result: pass-light-edit
task9_state: reviewed
task9_result: pass-tech-review
task9_reviewed_date: "2026-05-16"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-16T01:26:00+08:00"
finalized_date: "2026-05-16"
finalized_by: openclaw-task9
last_task6_audit: "2026-05-24"

---

# 20.11 MTE memtagMode 与 Native 崩溃治理

<!-- outline-start -->
## 要点

### 🔹 MTE 在稳定性治理中的适用场景
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

### 🔹 android:memtagMode 的 off、sync、async 选择
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

### 🔹 ASYMM 模式为何不暴露为应用 API
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

### 🔹 Zygote、bionic、Scudo 的生效路径
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

### 🔹 线上灰度开启 MTE 的崩溃归因策略
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

### 🔹 性能、兼容性与误报边界
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

## 扩展

### 🔸 与 Native Crash 信号处理器的配合方式
{待补充：素材充分时展开。}

### 🔸 MTE 报告进入 APM 平台后的聚合字段
{待补充：素材充分时展开。}

<!-- outline-end -->

MTE 解决的是 Native 堆内存破坏问题：指针携带 tag，分配器给内存块写入 tag，CPU 在 load/store 时比对二者是否一致。tag 不匹配时，进程收到 `SIGSEGV`，崩溃报告里会出现 MTE 相关 `si_code`。

应用稳定性治理里，MTE 的价值不在于替代 tombstone、Breakpad 或 Crashpad，而是把 use-after-free、heap buffer overflow、部分 double-free 这类“偶发、堆栈漂移、复现困难”的 Native 问题更早暴露出来。Native Crash 收集、信号链和 tombstone 解读详见 20.3 节；Native 内存工具横向对比详见 23.3 节。[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Crash 监控：为我们应用插上监控 Native Crash 的电子眼.md]

## MTE 适合放在哪些稳定性场景

MTE 适合三类场景。

- **Native 代码密集的业务**：音视频、地图、游戏引擎、图像处理、加密、模型推理等模块大量使用 C/C++，Java Crash 体系拿不到内存破坏发生点。MTE 能把一部分堆越界和释放后访问转成带 MTE 标识的 `SIGSEGV`。
- **安全敏感业务的生产缓解**：Android Developers 文档把 ASYNC 模式定位为低开销检测与缓解，适合经过 SYNC 测试、内存安全问题密度较低的代码库。
- **疑难 Native Crash 的灰度诊断**：线上发现疑似堆破坏后，可以在小流量、特定进程或 debug build 中打开 MTE，把原本漂移到随机位置的崩溃收敛到 MTE 报告。

MTE 不适合拿来排查所有 Native 内存问题。它不统计 Native Heap 总量，也不回答“谁分配最多”。内存增长仍然要用 heapprofd、`dumpsys meminfo`、`/proc/<pid>/smaps`；MTE 处理的是访问时的内存安全错误。相关排查入口详见 23.3 节。[已验证: 官方文档, https://developer.android.com/ndk/guides/arm-mte]

## `android:memtagMode` 的选择

应用通过 `AndroidManifest.xml` 的 `<application>` 或 `<process>` 配置 `android:memtagMode`。官方文档列出的应用可见值是 `off`、`default`、`sync`、`async`。[已验证: 官方文档, https://source.android.com/docs/security/test/memory-safety/arm-mte]

| 模式 | 适用位置 | 崩溃特征 | 工程建议 |
|------|----------|----------|----------|
| `off` | 对峰值性能敏感、未完成 MTE 测试的进程 | 不启用 MTE 检查 | 发布前没有覆盖 MTE 设备测试时，保持关闭更稳妥 |
| `sync` | debug build、小流量 canary、复现专项包 | tag mismatch 当场终止，`si_code` 常见为 `SEGV_MTESERR`，fault address 与访问点更准 | 用于定位问题，不建议直接面向大流量生产 |
| `async` | 经过 SYNC 测试后的生产灰度 | tag mismatch 可延迟到下一次内核入口再终止，`si_code` 常见为 `SEGV_MTEAERR`，缺少精确 fault address | 适合作为线上低开销探针，命中后再切 SYNC 复现 |

Gradle 工程里，更常见的做法是只给 debug 或 canary build 合并一份 manifest：

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools">
    <application
        android:memtagMode="sync"
        tools:replace="android:memtagMode" />
</manifest>
```

这段配置只表示这个包请求 SYNC。它不能保证所有设备都具备 MTE，也不能保证线上所有进程都按同一模式运行。Zygote 会结合硬件能力、compat change、系统属性和进程级配置再决策。[已验证: 官方文档, https://developer.android.com/ndk/guides/arm-mte]

## ASYMM 为什么不是应用 API

官方平台文档讨论了三种 MTE 运行模式：SYNC、ASYNC、ASYMM。但应用 manifest 只暴露 `off/default/sync/async`，没有 `asymm`。AOSP `Zygote.java` 也只定义了 `MEMORY_TAG_LEVEL_NONE`、`TBI`、`ASYNC`、`SYNC`，`memtagModeToZygoteMemtagLevel()` 只把 `ApplicationInfo.MEMTAG_ASYNC` 和 `ApplicationInfo.MEMTAG_SYNC` 转成 runtime flag。[已验证: AOSP main, frameworks/base/core/java/com/android/internal/os/Zygote.java]

ASYMM 的入口在设备配置侧。source.android.com 的 MTE configuration 文档说明，厂商可以在启动时写 `/sys/devices/system/cpu/cpu*/mte_tcf_preferred`，让请求 ASYNC 的用户态进程在指定 CPU 上被静默升级到 SYNC 或 ASYMM。这个配置可以做到 per-CPU，不属于单个 App 的 manifest 契约。[已验证: 官方文档, https://source.android.com/docs/security/test/memory-safety/mte-configuration]

这带来一个排查边界：看到 `android:memtagMode="async"`，只能说明应用请求 ASYNC。设备可能仍把该进程在某些 CPU 上升级到 ASYMM。线上归因时，manifest、设备型号、系统版本、`mte_tcf_preferred` 配置要分开记录。[来源: DeepResearch/2026-05-13-android-mte-memtag-async-asymm-analysis.md]

## 从 Zygote 到 bionic allocator 的生效路径

应用进程的 MTE 不是在业务代码首次分配内存时临时打开。路径从 Zygote fork 阶段开始：

```text
AndroidManifest.xml
  → ApplicationInfo.memtagMode / ProcessInfo.memtagMode
  → Zygote.getRequestedMemtagLevel()
  → Zygote.decideTaggingLevel()
  → runtimeFlags: MEMORY_TAG_LEVEL_ASYNC / MEMORY_TAG_LEVEL_SYNC
  → com_android_internal_os_Zygote.cpp SpecializeCommon()
  → mallopt(M_BIONIC_SET_HEAP_TAGGING_LEVEL, M_HEAP_TAGGING_LEVEL_*)
  → bionic allocator / Scudo 对 Native heap 分配写 tag
```

`Zygote.java` 会读取进程级 `memtagMode`，再读应用级 `memtagMode`，随后处理 compat change 与系统属性；`decideTaggingLevel()` 再结合硬件能力把请求降级或升级。没有 MTE 硬件时，SYNC/ASYNC 会被降到 TBI 或 NONE。[已验证: AOSP main, frameworks/base/core/java/com/android/internal/os/Zygote.java]

Native 层的 `com_android_internal_os_Zygote.cpp` 维护同一组 runtime flag。`SpecializeCommon()` 从 `runtime_flags` 中取出 `MEMORY_TAG_LEVEL_*`，映射成 `M_HEAP_TAGGING_LEVEL_ASYNC` 或 `M_HEAP_TAGGING_LEVEL_SYNC`，再调用 `mallopt(M_BIONIC_SET_HEAP_TAGGING_LEVEL, heap_tagging_level)`。bionic 的 `malloc_common.cpp` 对这个 mallopt 参数调用 `SetHeapTaggingLevel()`。[已验证: AOSP main, frameworks/base/core/jni/com_android_internal_os_Zygote.cpp；bionic/libc/bionic/malloc_common.cpp]

这个路径解释了两个线上现象：同一个 APK 在不支持 MTE 的设备上没有 MTE 崩溃；同一个进程在不同系统属性、compat change 或厂商配置下，最终 tag 检查模式可能不同。

## 线上灰度开启 MTE 的崩溃归因策略

MTE 灰度的目标是“让疑难内存破坏变成可聚合的 Native Crash”，而不是一次性打开全量用户。建议按进程、机型、版本和业务入口分层。

灰度前要准备三件事：

- **设备筛选**：只选已知支持 MTE 的设备族，Android Developers 文档列出了 Pixel 8/9 系列等可用设备。其他设备即使 manifest 写了 `sync` 或 `async`，也可能被 Zygote 降级。
- **构建分层**：debug 使用 `sync`，canary 可用 `sync` 或 `async`，大流量生产只考虑 `async`。官方配置文档明确提醒不要在生产 manifest 或 Android.bp 中直接使用 `sync`。
- **回滚开关**：每个进程单独控制，命中异常崩溃率阈值后能按进程关闭。Native Crash 归因详见 20.3 节。

MTE 崩溃进入 APM 后，不能只按栈顶帧聚合。ASYNC 模式的崩溃点可能滞后，栈顶帧可能是下一次 syscall、定时器中断或无关 native 调用。聚合时要把 `si_code`、进程名、ABI、设备、build id、so load bias、MTE 模式请求值、业务入口和近邻 native 线程状态一起使用。

SYNC 命中更适合做根因定位。`SEGV_MTESERR` 通常给出更接近真实访问点的上下文；ASYNC 命中后，下一步是把同一灰度桶切到 SYNC 或构造复现包，争取拿到更精确的 tombstone。[已验证: 官方文档, https://developer.android.com/ndk/guides/arm-mte]

## 性能、兼容性与误报边界

MTE 的成本来自两部分：CPU 做 tag 检查，allocator 维护 tag 与报告信息。SYNC 模式为了提供更好的诊断信息，会记录分配和释放栈，成本高于 ASYNC。官方配置文档建议生产的快速配置写 `async`，再由设备侧 `mte_tcf_preferred` 决定每个 CPU 的实际模式。[已验证: 官方文档, https://source.android.com/docs/security/test/memory-safety/mte-configuration]

兼容性风险主要来自“以前就存在但没有暴露”的 Native bug。启用 MTE 后，原来偶发的 heap overflow 或 use-after-free 可能稳定变成 `SIGSEGV`。这不是误报；它说明进程已经触发了内存 tag 不匹配。发布前必须在 MTE 设备上覆盖常用路径，避免只在支持 MTE 的用户设备上暴露问题。

MTE 也有漏检边界。tag 空间有限，某些释放后访问可能碰巧命中新分配对象的 tag；ASYNC 还可能丢失精确 fault address。它适合提高发现率和缩短归因路径，不适合承诺“打开后所有 Native 内存破坏都会被抓到”。[已验证: 官方文档, https://developer.android.com/ndk/guides/memory-debug]

## 与 Native Crash 信号处理器的配合方式

MTE 报告仍然以 `SIGSEGV` 进入 Native Crash 体系。应用内已有 Breakpad、Crashpad、xCrash 或自研 signal handler 时，要复用现有信号链约束：handler 内只做 async-signal-safe 的最小记录，把复杂解析交给 handler 进程或下次启动补偿。

20.3 节已经展开 Android SignalChain、debuggerd、tombstone 和 handler 传递顺序。放到 MTE 场景，处理原则是：signal handler 内不分配堆内存，不在崩溃现场做完整符号化，不吞掉信号导致 debuggerd 拿不到 tombstone。APM 侧记录 MTE `si_code` 后，继续传递给原 handler 或系统默认处理器。[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Crash 监控：为我们应用插上监控 Native Crash 的电子眼.md]

## MTE 报告进入 APM 后的聚合字段

MTE 崩溃事件记录至少保留这些字段：

- `signal` / `si_code`：区分普通 `SIGSEGV`、`SEGV_MTESERR`、`SEGV_MTEAERR`。
- `requested_memtag_mode`：manifest 或 compat change 请求值，取 `off/default/sync/async`。
- `effective_device_context`：设备型号、Android 版本、内核版本、是否已知支持 MTE、可采集时记录 `mte_tcf_preferred`。
- `process_context`：进程名、ABI、线程名、业务入口、灰度桶、前后台状态。
- `native_identity`：so 名、build id、load bias、pc relative offset、符号化结果。
- `report_quality`：SYNC/ASYNC、是否有 fault address、是否有分配/释放栈、是否来自 tombstone 或 APM handler。

聚合规则建议把 `si_code + so build id + pc relative offset + requested_memtag_mode + device family` 作为第一层，再用业务入口和线程名做二次拆分。ASYNC 报告缺少精确访问点时，不能把单个栈顶帧当成唯一 fingerprint；同一个 heap corruption 可能在不同延迟点崩溃。

## 版本边界与待验证项

- Android Developers 文档把 MTE 支持设备列到 Pixel 8/9 系列；其他厂商设备是否支持、是否启用、是否做 ASYMM per-CPU 配置，需要按设备采集。
- ASYMM 由设备侧 `mte_tcf_preferred` 控制，应用层没有公开 API 直接请求。线上报告里不要把 `async` 请求值写成“实际 ASYMM”。
- `BIONIC_MEMTAG_UPGRADE_SECS` 这类系统服务重启后升级诊断机制，本节只作为后续研究线索，不写成应用侧可用能力。[待验证: 需确认该机制在应用侧观测和归因中的适用边界]



<!-- AIW-源码调研-2026-05-21 START -->
## 补充：ASYMM 自动启用的源码级链路（2026-05-21 调研）

本节补充 2026-05-21 源码调研的关键发现，进一步完善 §20.11 中"ASYMM 为什么不是应用 API"和"从 Zygote 到 bionic allocator 的生效路径"两个锚点的源码证据链。

### 1. mte_tcf_preferred：CPU 级别的静默升级机制

source.android.com MTE configuration 文档（2025-12-02）明确：

> MTE modes can be set for each CPU core in the system by writing to /sys/devices/system/cpu/cpu*/mte_tcf_preferred. For example, writing sync (or asymm) would cause any userspace process that has requested Async mode to be silently auto-upgraded to Sync (or Asymm) while running on that core.

这是纯硬件/内核侧的配置，不经过 manifest 或 Zygote。设备厂商可以在开机时统一配置。Linux kernel 文档（docs.kernel.org/arch/arm64/memory-tagging-extension.html）：

> The preferred tag checking mode for each CPU is controlled by /sys/devices/system/cpu/cpu<N>/mte_tcf_preferred, to which a privileged user may write the value async, sync or asymm.

**实战含义**：看到 `android:memtagMode="async"` 的崩溃率数据时，不能直接假设设备上运行的就是 async 模式。需要在支持 MTE 的设备上采集 `/sys/devices/system/cpu/cpu*/mte_tcf_preferred` 的值，才能确认实际模式。

### 2. __libc_init_mte：prctl 调用序列

bionic/docs/mte.md（android.googlesource.com）说明 `__libc_init_mte()` 的职责：

> __libc_init_mte figures out the appropriate MTE level that is requested by the process, calls prctl to request this from the kernel, and stores data in __libc_shared_globals which gets picked up later to enable MTE in scudo.

关键源码（android.googlesource.com platform/bionic，commit 30a1a29ba239，2024-11-18）：

```cpp
if (prctl(PR_SET_TAGGED_ADDR_CTRL, prctl_arg | PR_MTE_TCF_SYNC, 0, 0, 0) == 0 ||
    prctl(PR_SET_TAGGED_ADDR_CTRL, prctl_arg, 0, 0, 0) == 0) {
    __libc_shared_globals()->initial_heap_tagging_level = level;
    __libc_shared_globals()->initial_memtag_stack = memtag_stack;
    // ... set PROT_MTE on stack ...
}
```

`__libc_init_mte()` 在进程启动初期即通过 prctl 向内核请求 MTE 模式。如果是动态链接可执行文件，由 linker 调用；如果是静态可执行文件，由 crtbegin.c 中的 `__libc_init` 调用。

### 3. __libc_init_mte_late：延迟降级机制

bionic/libc/bionic/libc_init_common.cpp 中的 `__libc_init_mte_late()` 实现了定时降级（aosp-mirror/platform_bionic）：

```cpp
__attribute__((no_sanitize("hwaddress", "memtag"))) void
__libc_init_mte_late() {
#if defined(__aarch64__)
    if (!__libc_shared_globals()->heap_tagging_upgrade_timer_sec) {
        return;
    }
    // ... 设置 timer，到期后降级为 ASYNC ...
    async_safe_format_log(ANDROID_LOG_INFO, "libc", "Downgrading MTE to async.");
    SetHeapTaggingLevel(M_HEAP_TAGGING_LEVEL_ASYNC);
#endif
}
```

触发条件：系统服务以 ASYNC 模式崩溃时，init 设置 `BIONIC_MEMTAG_UPGRADE_SECS`，libc 启动时据此启动定时器。**这是系统服务侧的机制，不直接适用于普通应用进程**。

### 4. Arm 硬件能力检测：mte3 与 ASYMM 支持判断

Arm MTE User Guide 说明如何判断设备是否支持 ASYMM：

> For ASYMM mode, look for the presence of the string mte mte3 in /proc/cpuinfo.

"mte3" 表示 Arm v8.7-A 引入的扩展能力，包括 ASYMM 模式。这是判断设备是否支持 ASYMM 的硬件级依据。

### 5. Zygote 始终以 ASYNC MTE 运行的源码级原因

bionic/docs/mte.md 明确：

> Apps can request MTE be enabled for their process via the manifest attribute android:memtagMode. This gets interpreted by Zygote, which always runs with ASYNC MTE enabled, because MTE for a process can only be disabled after it has been initialized, not enabled.

**原因**：MTE 只能在进程初始化后禁用，不能在初始化后启用。Zygote 作为所有普通 App 进程的父进程，如果以更严格模式运行，子进程无法降级。因此 Zygote 固定以 ASYNC 运行，子进程通过 `SpecializeCommon` 中的 `mallopt` 进行调整。

### 6. 完整调用链总结

综合今天的调研，完整调用链如下：

```
AndroidManifest.xml (android:memtagMode="async")
  ↓
Zygote.getRequestedMemtagLevel() / decideTaggingLevel()
  → RuntimeFlags.MEMORY_TAG_LEVEL_ASYNC 编码到 runtimeFlags
  ↓
fork() 后子进程
  ↓
SpecializeCommon() (com_android_internal_os_Zygote.cpp)
  → mallopt(M_BIONIC_SET_HEAP_TAGGING_LEVEL, M_HEAP_TAGGING_LEVEL_ASYNC)
  ↓
bionic libc 接收 mallopt，调用 SetHeapTaggingLevel()
  ↓
__libc_init_mte() (libc_init_mte.cpp)
  → prctl(PR_SET_TAGGED_ADDR_CTRL, prctl_arg, ...) 
  ↓
内核接受请求，检查 mte_tcf_preferred
  → 如果设为 asymm/sync，静默升级
  ↓
Scudo allocator 对 malloc/free 写入 tag
  ↓
CPU load/store 时比对 pointer tag 和 memory tag
```

<!-- AIW-源码调研-2026-05-21 END -->


## 参考资料

### MTE ASYMM 在 Android App memtagMode=async 下的自动启用机制
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-13-mte-asymm-memtag-mode-analysis.md
- 类型：DeepResearch 调研结果
- 摘要：MTE ASYMM/SYNC 启用涉及 bionic libc、Arm 硬件探测、Zygote fork、Manifest memtagMode 属性联动。ASYMM 模式异步标签检查性能开销低，SYNC 同步检查安全性高。厂商芯片支持程度不同，高通/联发科旗舰支持双模式。
- 注入时间：2026-05-17
- 价值：补充 MTE ASYMM/SYNC 启用路径的源码证据链，覆盖 bionic、Zygote、Manifest 路径


<!-- AIW-源码调研-2026-05-26 START -->
## 补充：MTE ASYMM 自动启用的源码闭环（2026-05-26）

本节补充 2026-05-26 源码调研的关键发现，完善 §20.11 中"ASYMM 为什么不是应用 API"和"从 Zygote 到 bionic allocator 的生效路径"两个锚点的三层源码闭环证据。

### 三层源码路径

#### 应用层：android:memtagMode 只暴露 off/default/sync/async

AOSP 源码：`frameworks/base/core/java/android/content/pm/ApplicationInfo.java`

```java
public static final int MEMTAG_OFF = 0;
public static final int MEMTAG_DEFAULT = 1;
public static final int MEMTAG_ASYNC = 2;
public static final int MEMTAG_SYNC = 3;
// 注意：没有 MEMTAG_ASYMM
```

AOSP 源码：`frameworks/base/core/java/com/android/internal/os/Zygote.java`

```java
private static final int MEMORY_TAG_LEVEL_NONE = 0;
private static final int MEMORY_TAG_LEVEL_TBI = 1;
private static final int MEMORY_TAG_LEVEL_ASYNC = 2;
private static final int MEMORY_TAG_LEVEL_SYNC = 3;
// 注意：没有 MEMORY_TAG_LEVEL_ASYMM
```

Zygote 的 `memtagModeToZygoteMemtagLevel()` 只处理 MEMTAG_ASYNC → MEMORY_TAG_LEVEL_ASYNC 和 MEMTAG_SYNC → MEMORY_TAG_LEVEL_SYNC 的映射。**应用层 Zygote 没有任何 ASYMM 代码路径**。

#### Bionic 层：__libc_init_mte 通过 prctl 设置 MTE

AOSP 源码：`bionic/libc/bionic/libc_init_common.cpp`

```cpp
if (prctl(PR_SET_TAGGED_ADDR_CTRL, prctl_arg | PR_MTE_TCF_SYNC, 0, 0, 0) == 0 ||
    prctl(PR_SET_TAGGED_ADDR_CTRL, prctl_arg, 0, 0, 0) == 0) {
    __libc_shared_globals()->initial_heap_tagging_level = level;
    __libc_shared_globals()->initial_memtag_stack = memtag_stack;
    // ... set PROT_MTE on stack ...
}
```

调用路径：动态链接可执行文件由 linker 调用，静态链接可执行文件由 crtbegin.c 中的 `__libc_init` 调用。`bionic/libc/platform/bionic/mte.h` 定义 MemtagMode 枚举：

```cpp
enum MemtagMode {
    MEMTAG_MODE_OFF = 0,
    MEMTAG_MODE_ASYNC = 1,
    MEMTAG_MODE_SYNC = 2,
};
// 同样没有 ASYMM 枚举值
```

#### 内核层：mte_tcf_preferred 实现 per-CPU 静默升级

source.android.com MTE configuration 文档（2025-12-02）：

> MTE modes can be set for each CPU core in the system by writing to /sys/devices/system/cpu/cpu*/mte_tcf_preferred. For example, writing sync (or asymm) would cause any userspace process that has requested Async mode to be silently auto-upgraded to Sync (or Asymm) while running on that core.

**核心结论**：ASYMM 不是应用 API，不能通过 manifest 配置。manifest 中的 `async` 只是请求值，实际运行模式由设备侧 `mte_tcf_preferred` 决定。当设备写入 `asymm` 时，请求 ASYNC 的进程在该 CPU 上会被内核静默升级为 ASYMM，这个升级发生在硬件/内核层，不经过 Zygote 或 bionic 的应用级逻辑。

### 实战排查提示

当看到 `android:memtagMode="async"` 的崩溃率数据时，不能直接假设设备上运行的就是 async 模式。需要在支持 MTE 的设备上采集 `/sys/devices/system/cpu/cpu*/mte_tcf_preferred` 的值，才能确认实际模式。不同厂商设备对 ASYMM 的默认配置可能不同，Pixel 系列与第三方厂商设备的配置策略可能存在差异。
<!-- AIW-源码调研-2026-05-26 END -->

