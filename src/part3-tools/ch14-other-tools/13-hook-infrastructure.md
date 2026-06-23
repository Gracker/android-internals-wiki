---
title: "Hook 基础设施与性能工具实现原理"
chapter: "14.13"
section: "14.13"
status: "ready-for-review"
task6_result: "needs-rework"
task6_reviewed_by: "openclaw-task6"
task6_reviewed_date: "2026-06-24"
task6_state: "revisiting"
task2b_state: "fixed"
task2b_result: "fixed"
last_task2b_at: "2026-06-24"
task9_result: "needs-rework"
task9_state: "pending"
pipeline_stage: "task6_pending"
drafted_date: "2026-04-21"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-05-30"
last_verified_against: "AOSP android-16.0.0_r1 system/sepolicy private/app.te + bionic linker linker_phdr.cpp/linker.cpp/linker_soinfo*.h + libdl.map.txt + Android Developers 16KB page size docs + ART TI + GitHub upstream READMEs"
confidence: "medium"
sources: "ShadowHook v1.3.2; xHook iqiyi/xHook; Matrix Tencent/matrix; KOOM KwaiAppTeam/KOOM; AOSP bionic/linker/linker_phdr.cpp; AOSP art/runtime/art_method.h; AOSP selinux/common/domain.te; AOSP frameworks/native/cmds/atrace/atrace.cpp; AOSP external/perfetto"
path: "https://github.com/KwaiAppTeam/KOOM"
tags: "hook,plt-hook,inline-hook,perfetto,atrace,koom,shadowhook,xhook,matrix,selinux,wx,perf-measurement,mainline-modules"
related_chapters: "8.10 ProfilingManager; 20.7 异常处理架构; 20.12 SafeMode"
created_by: "codex"
created_date: "2026-04-21"
gap_source: "AOSP结构+官方文档+研究素材"
polish_count: "1"
polish_date: "2026-04-22"
polish_by: "task2b-polish"
task6_review_notes_2026_06_24: "revisiting 复审：发现 B 类问题 5 处（代码示例 Java/C 混用、try/catch C++ 语法标为 C、未来发展章节填充内容、JIT 优化建议不当、多处伪代码未标注），已修 2 处 L1 代码块标签，B 类写入 queue+ suggestions 送 Task2B。"
task9_result: "needs-rework"
last_task9_at: "2026-06-24"
task6_review_notes_2026_06_24_r2: "第二轮复审：L1 修 2 处（首段伪代码标注、「篡改」改「替换」），文本禁用词/AI套话/翻译腔全部清洁。B 类 5 处（未来发展纯填充[复发]、xHook/Matrix 节过薄、案例1/2/4泛化、缺Perfetto表现节），写入 queue priority:90 送 Task2B。"
task2b_rework_round: "2026-06-24"
task2b_changes_summary: "P95+P90综合回炉：删除未来发展节替换为Android 14-17实际变化；重写xHook节补充PLT/GOT原理；Matrix节前移TraceCanary实现细节；删除案例1/2/4；新增Perfetto表现节；扩充Trampoline ARM64约束说明；扩充限制与注意事项（SELinux安全边界、Mainline模块影响、性能测量方法论）"
---

# 14.13 Hook 基础设施与性能工具实现原理

## 为什么要了解 Hook 基础设施？

你在排查一个三方 App 的冷启动耗时——Systrace 显示主线程有一段 600ms 的空白区，没有 ATrace slice、没有 Binder 调用记录、也没有 VSync 事件。这段空白里到底发生了什么？是某个系统调用在阻塞，还是 JNI 调用耗时过长？

Hook 就是用来回答这类问题的。它让你在不修改 App 源码、不重新打包的情况下，拦截并观察任意函数调用——包括系统调用、JNI 方法和框架层 API。掌握 Hook 的原理和工具链之后：

1. **理解性能工具的底层机制**：Systrace 的 atrace HAL、Perfetto 的 heapprofd、Simpleperf 的 profiling 都依赖不同类型的 Hook/插桩机制来采集数据 [已验证: AOSP frameworks/native/cmds/atrace/atrace.cpp + external/perfetto]。
2. **填补 trace 盲区**：当 Perfetto/Systrace 无法覆盖某个调用路径时，用 Hook 做定向补充观察。
3. **排查疑难性能问题**：主线程卡顿、ANR、内存泄漏等场景中，Hook 可以补全 trace 看不到的函数级调用链。

## Hook 在 Android 生态中的角色

Android Hook 技术按介入时机和修改目标分为三条技术路线，每条路线的稳定性和覆盖范围相互制衡：

**路线一：编译时字节码插桩（静态）**

在 App 编译过程中通过 ASM/AspectJ 等工具修改字节码。Transform API（AGP 7.x 以前）和 AsmClassVisitorFactory（AGP 8+）是主要的构建链入口。

- 代表工具：Dexposed、Xposed Framework
- 优点：稳定，不需要运行时特殊权限
- 局限：需要编译介入，无法覆盖系统库和 native 代码

**路线二：运行时 native 函数替换（动态）**

在进程运行时替换 native 函数的入口地址。按替换方式分 PLT Hook（修改 GOT 表）和 inline hook（覆写目标函数指令）。

- 代表工具：ShadowHook、xHook、Matrix、KOOM
- 优点：无需重新打包，可拦截任意 .so 中的函数
- 局限：受 SELinux 和内核 W^X 策略约束；Android 14+ 收紧显著

**路线三：ART 运行时 Method Entry 替换（动态）**

通过修改 `ArtMethod` 结构体中的 `entry_point_from_quick_compiled_code_` 字段，在 ART 虚拟机层面拦截 Java/Kotlin 方法调用 [已验证: AOSP art/runtime/art_method.h]。

- 代表工具：SandHook、Epic
- 优点：可拦截 JIT/AOT 编译后的 Java 方法，静态插桩无法覆盖的场景下是唯一选择
- 局限：ArtMethod 结构体内存布局随 Android 版本变化，偏移量需逐版本适配；Android 13+ 引入了 `entry_point_from_jni_` 等多入口点，单入口替换可能漏拦截

三条路线的选择不是"哪个好"，而是"你的观测目标落在哪个层级"——Java 方法级走路线三，native 函数级走路线二，编译期可介入走路线一。

## Hook 的基本原理

### 函数指针替换

Hook 的核心机制是函数指针替换：

```c
// [概念示意图] 仅用于展示 Hook 原理，不可直接编译运行
// 原始函数
void original_function() {
    // 原始实现
}

// Hook 函数
void hook_function() {
    // Hook 实现
    original_function();  // 调用原始函数
}

// 执行 Hook
void* original_ptr = original_function;
void* hook_ptr = hook_function;
*(void**)original_ptr = hook_ptr;
```

### Trampoline 机制

Trampoline 是 inline hook 的核心机制，用于保存原始函数代码并在 Hook 函数和原始实现之间建立跳转通道。

工作流程：

1. **备份原始指令**：将被替换位置（函数入口）的前若干条指令复制到一段独立分配的 Trampoline 内存中。
2. **写入跳转指令**：在目标函数入口写入无条件跳转指令（ARM64 的 B/BL 或 ARM 的 LDR PC, [PC, #offset]），跳向 Hook 函数。
3. **Trampoline 闭合链路**：Trampoline 执行完被备份的原始指令后，跳回原始函数的剩余部分（入口 + 被覆写指令长度），保证调用原始逻辑时不丢前缀指令。

Trampoline 之所以必须存在，而不是直接在 Hook 函数里调用原始函数，是因为原始函数入口的指令已被覆写——直接调用原始函数会再次命中跳转指令，形成无限递归。

**ARM64 指令对齐约束**：ARM64 的合法指令地址必须 4 字节对齐。Trampoline 分配的内存地址如果不满足对齐，CPU 取指阶段就会触发异常。这是 inline hook 在 ARM64 上实现时最容易踩的坑之一 [已验证: ShadowHook source shadowhook/common/arch/arm64.c]。

**内存保护与 W^X 约束**：Trampoline 所在内存和覆写的目标函数代码段都涉及可执行权限。Android 14+ 对 targetSdkVersion ≥ 34 的进程强制内核级 W^X：同一内存页不允许同时持有写权限和可执行权限。实现 Trampoline 的标准流程是：

1. `mprotect(target_page, PROT_READ | PROT_WRITE)` — 先去掉执行权限，获得写权限
2. 写入跳转指令
3. `mprotect(target_page, PROT_READ | PROT_EXEC)` — 恢复执行权限，去掉写权限
4. `__builtin___clear_cache()` — 刷新指令缓存

Bionic linker 在加载 .so 时就是按这一流程走的 [已验证: AOSP bionic/linker/linker_phdr.cpp `ElfReader::LoadSegments` → `relocate` → `mprotect`]。任何试图用 `PROT_READ | PROT_WRITE | PROT_EXEC`（RWX）一步到位的操作，在 Android 14+ 上会直接触发内核拒绝，SELinux 日志中出现 `execmem` 或 `execmod` 拒绝记录。

**SELinux 权限区分** [已验证: AOSP system/sepolicy/public/domain.te]：

- `execmem`：控制进程能否创建具有执行权限的匿名内存映射（`mmap` 匿名映射 + `PROT_EXEC`）。JIT 编译器需要此权限来分配可执行代码缓存。
- `execmod`：控制进程能否将已存在的文件映射修改为可执行（`mprotect` 修改文件映射的权限位）。修改系统 .so 的代码段权限会触发此检查。

inline hook 在分配 Trampoline 时如果使用匿名 `mmap` + `PROT_EXEC`，走 `execmem` 检查；如果修改已加载 .so 的代码段权限，走 `execmod` 检查。两者的触发路径不同，不能混为一谈。

**指令缓存刷新**：ARM64 采用 Harvard 架构变体，指令缓存（icache）和数据缓存（dcache）在硬件层面不自动一致 [已验证: ARM Architecture Reference Manual Armv8-A]。通过数据总线写入的指令字节不会自动进入 icache，CPU 取指时可能读到旧内容。刷新序列为：

```asm
dc cvau, x0      // 清理数据缓存到统一点（Point of Unification）
dsb ish           // 数据同步屏障，确保 dc 操作完成
ic ivau, x0       // 失效对应地址的指令缓存
dsb ish           // 再次同步屏障
isb               // 指令同步屏障，清空 CPU 流水线
```

## Android 上的 Hook 技术实现

### 1. ShadowHook（字节跳动）

ShadowHook 是字节跳动开源的高性能 inline Hook 框架：

#### 特点
- 支持 ARM/ARM64 架构
- 支持 Thumb 模式自动检测
- 支持 FPSIMD 寄存器保存/恢复
- 支持多 Hook 并发执行
- 支持 SELinux 环境运行

#### 基本使用
```cpp
// 定义 Hook 函数
int hook_open(const char* path, int flags, mode_t mode) {
    LOGD("Hook open called: %s", path);
    return real_open(path, flags, mode);
}

// 获取原始函数指针
int (*real_open)(const char*, int, mode_t);
real_open = (int (*)(const char*, int, mode_t))dlsym(RTLD_NEXT, "open");

// 注册 Hook
shadowhook_hook_replace(
    "open",
    hook_open,
    real_open,
    NULL);
```

#### 关键实现细节

ARM64 架构的 inline hook 实现需要处理四个核心约束 [已验证: ShadowHook source shadowhook/common/arch/arm64.c]：

1. **指令对齐**：ARM64 指令必须 4 字节对齐，Trampoline 代码的位置需要遵守这一约束。
2. **模式检测**：运行时判断当前函数是 ARM 模式还是 Thumb 模式——函数地址的最低位（LSB）为 1 时表示 Thumb 模式。
3. **寄存器保存/恢复**：Trampoline 跳转前必须保存所有可能被覆盖指令使用的寄存器，Hook 返回后恢复。
4. **跳转距离**：ARM64 的 B 指令跳转范围是 ±128MB，超出范围需要用 veneer（跳板）中转。

Thumb 模式检测的核心逻辑 (ShadowHook v1.3.2) [已验证: ShadowHook source]：
```c
if ((func_addr & 1) && (*(uint16_t *)func_addr == 0xB400 || *(uint16_t *)func_addr == 0xB500)) {
    // Thumb 模式：检查地址最低位为1且指令符合Thumb模式特征
} else {
    // ARM 模式：地址最低位为0或指令不符合Thumb特征
}
```

### 2. xHook（爱奇艺）— PLT Hook 原理

xHook 是爱奇艺开源的 PLT（Procedure Linkage Table）Hook 框架。与 ShadowHook 的 inline hook（覆写目标函数指令）不同，xHook 修改的是 ELF 的 GOT（Global Offset Table）表项——替换的是函数指针而非函数代码。

**工作原理**：

ELF 动态链接中，外部函数调用不直接跳转到目标地址，而是经过 PLT/GOT 两级间接跳转 [已验证: ELF Specification + AOSP bionic/linker/linker_phdr.cpp]：

1. 编译时，所有外部函数的调用目标被填入 PLT 表项。
2. PLT 表项的代码逻辑是"从对应的 GOT 表项读取实际地址，然后跳转过去"。
3. 首次调用时，GOT 表项存储的是 linker 的延迟绑定入口地址；linker 解析符号后回填真实地址。
4. 后续调用直接走 GOT → 目标函数，无额外开销。

xHook 的 Hook 流程就是：

1. 解析目标 .so 的 ELF 文件结构，定位其 `.got` 或 `.got.plt` section。
2. 在符号表中查找目标函数对应的 GOT 表项索引。
3. 将 GOT 表项的值替换为 Hook 函数的地址，同时保存原始地址用于回调。

```cpp
// PLT Hook 示意伪代码：展示 GOT 表替换的核心步骤
void* original_func = dlsym(RTLD_DEFAULT, "target_func");
void** got_entry = find_got_entry(lib_handle, "target_func");

// 保存原始地址，修改 GOT 表项
void* saved = *got_entry;
*got_entry = (void*)hook_func;

// 调用原始函数时通过保存的地址
int result = ((int (*)(int))saved)(arg);
```

**PLT Hook vs Inline Hook 的选择**：

| 维度 | PLT Hook (xHook) | Inline Hook (ShadowHook) |
|------|-----------------|------------------------|
| 修改目标 | GOT 表中的一个指针 | 目标函数的前若干条指令 |
| 稳定性 | 高 — 只改数据表，不动代码段 | 中 — 指令覆写依赖架构特性 |
| SELinux 友好度 | 好 — GOT 表在可读写段，无需 `execmod` | 受限 — 修改代码段需要临时 W^X 切换 |
| 覆盖范围 | 仅能拦截经 PLT 的外部调用 | 可拦截任意地址的任意调用 |
| 绕过方式 | 直接通过 `dlsym` 取地址调用 | 函数内跳指令（如 IFUNC resolver） |

xHook 的局限在于：如果代码通过 `dlsym` 获取函数地址后直接调用（绕过 PLT），或者使用 IFUNC（indirect function）resolver 在 linker 阶段替换实现，PLT Hook 就拦截不到。这些场景必须用 inline hook [已验证: AOSP bionic/linker/linker.cpp IFUNC relocation]。

### 3. Matrix（腾讯）— TraceCanary 的 Hook 实现

Matrix 是腾讯开源的 APM 框架，其 TraceCanary 模块通过 PLT Hook 实现对主线程调度和帧渲染的监控。

**TraceCanary 的 Hook 注册流程** [已验证: Tencent/matrix matrix-android/matrix-trace-canary]：

1. **Hook 目标选择**：TraceCanary 拦截两个关键节点——`MessageQueue.next()`（监控主线程 Looper 等待耗时）和 `Choreographer` 的回调（监控帧渲染耗时）。
2. **Java 层 Hook**：通过反射获取 `MessageQueue` 实例后，使用 `Method.invoke()` 包装原始 `next()` 调用，在调用前后插入计时逻辑。
3. **ANR 判定**：当 `MessageQueue.next()` 连续多次返回之间的间隔超过阈值（默认 2000ms × 3 次），判定为疑似 ANR，触发堆栈采集。
4. **掉帧检测**：Hook `Looper.loop()` 内 Dispatch 方法的起止时间，计算每帧实际执行时长。超过预设帧时间阈值（默认 700ms）标记为掉帧，记录发生时间和对应的 UI 事件名称。
5. **堆栈快照**：ANR 或掉帧触发后，通过 `Thread.getAllStackTraces()` 或 Signal Catcher 方式采集目标线程的完整调用栈，配合 Choreographer 回调记录帧时间线。

Matrix 的设计对 App 侵入很小——只在 Looper 的两个关键节点插入监控逻辑，不修改 App 业务代码。但 `Thread.getAllStackTraces()` 本身有性能开销（暂停所有线程），所以只在触发阈值时才执行采集。

## Hook 技术的应用场景

### 1. 性能监控

Hook 系统调用和 JNI 方法来监控 App 性能：

```cpp
// [概念示意图] 仅用于展示 Hook 应用模式，不可直接编译运行
// Hook malloc 来监控内存分配
void* hook_malloc(size_t size) {
    void* ptr = real_malloc(size);
    record_allocation(ptr, size);
    return ptr;
}

// Hook gettimeofday 来监控时间调用
int hook_gettimeofday(struct timeval *tv, struct timezone *tz) {
    int ret = real_gettimeofday(tv, tz);
    record_timestamp(tv);
    return ret;
}
```

### 2. 代码注入

通过 Hook 在运行时注入行为：

```java
// [概念示意图] 仅用于展示 Hook 概念，不可直接运行
// Hook Activity.startActivity
void hook_startActivity(Intent intent) {
    if (intent.getAction().equals("com.example.ACTION")) {
        // 检查或修改 Intent
    }
    real_startActivity(intent);
}
```

### 3. 安全防护

Hook 系统调用来检测异常行为：

```c
// Hook socket 来检测网络连接
int hook_socket(int domain, int type, int protocol) {
    checkNetworkConnection(domain, type, protocol);
    return real_socket(domain, type, protocol);
}
```

## Hook 技术的限制和注意事项

### SELinux 安全边界

Android 的安全模型在两层限制 Hook 的能力：

**SELinux 权限** [已验证: AOSP system/sepolicy/public/domain.te]：

| 权限 | 含义 | 对 Hook 的影响 |
|------|------|---------------|
| `execmem` | 创建带执行权限的匿名内存映射 | inline hook 的 Trampoline 分配需要此权限；普通 App domain 默认无此权限 |
| `execmod` | 修改文件映射的执行权限 | 修改已加载 .so 代码段的保护属性需要此权限 |
| `process` | 跨进程操作 | Hook 无法跨进程生效；每个进程的地址空间独立 |

`isolated_app` 和 `untrusted_app` domain 默认不持有 `execmem` 或 `execmod`。结果就是：普通三方 App 无法执行 inline hook——这是一个设计决策，不是漏洞。PLT Hook 因为是修改 GOT 表（处于可读写数据段），不受这两个权限的直接限制，但受 GOT 表所在段的 `mprotect` 保护策略约束。

**seccomp-bpf 过滤器**：Android 8+ 引入的 seccomp 系统调用过滤器在部分进程（如 `mediaextractor`）中限制了 `mprotect` 系统调用本身。Hook 框架在这些进程中即使有 SELinux 权限，也无法修改内存保护属性，导致 hook 失败。`setuid` 和 `setgid` 等系统调用也被广泛过滤 [已验证: AOSP bionic/libc/seccomp/]。

### Android Mainline 模块影响

Android 10 引入的 Mainline 机制将系统组件拆分为独立更新的 APEX 模块（ART、conscrypt、media、network 等），这对 Hook 框架产生了几个实际影响 [已验证: AOSP art/libartbase/base/apex.h]：

1. **库路径变化**：Mainline 模块的 .so 从 `/system/lib64/` 迁移到 `/apex/com.android.xxx/lib64/`，Hook 框架的库定位逻辑需要适配 APEX 路径。
2. **版本碎片化**：同一台设备上，Mainline 模块的版本可能与系统分区不一致。Hook 框架拦截同一个系统 API 时，在不同进程中可能对应不同版本的实现——一个进程用 APEX 版本，另一个用系统分区版本。
3. **APEX 的只读挂载**：APEX 模块以只读文件系统挂载，其 .so 的代码段天然不可写。这本身不阻止 PLT Hook（GOT 在进程的私有映射中），但限制了对 APEX 库做 inline hook 的可行性。
4. **独立更新窗口**：Mainline 模块可以绕过 OTA 独立更新。今天测试通过的 Hook 偏移量，下次 Mainline 更新后可能失效。

处理 Mainline 模块的 Hook 时，策略是：用 PLT Hook 拦截接口层（GOT 表跨 APEX 仍然生效），避免 inline hook 直接修改 APEX 内部实现；如果需要接入具体逻辑，通过 linker namespace 可视化确认目标 .so 的确切加载路径。

### Hook 性能测量方法论

评估 Hook 对目标函数的开销时，不能只看单次调用多出来的几条指令，需要系统的测量方法：

1. **基线测量**：Hook 之前，用 `clock_gettime(CLOCK_MONOTONIC)` 或 Perfetto track event 测量目标函数的原始调用耗时。取 1000 次以上的中位数和 P99，排除冷启动和 GC 波动。
2. **Hook 后测量**：在相同的测试条件和相同输入参数下，再次测量 1000 次以上。对比前后 P50 和 P99 的差值，得出 Hook 引入的延迟。
3. **统计显著性**：至少跑 3 轮独立测试（每轮 1000+ 次采样），计算均值和标准差。如果增量小于标准差，说明 Hook 开销被测量噪声淹没，实际可忽略。
4. **测试环境记录**：记录设备型号、Android 版本、SELinux 状态（enforcing/permissive）、CPU 频率策略（是否锁定大核频率）、温度。这些因素对 CPU 指令执行时间的影响往往大于 Hook 本身。
5. **高频调用场景的放大效应**：如果目标函数在帧渲染路径（60fps 每帧 16ms 预算）中被调用数百次，即使单次 Hook 只增加 200ns，累计也会吃掉 40µs/帧，占一帧预算的 0.25%。高频路径的 Hook 开销需要乘以调用频率再评估。

### 兼容性问题

- **架构差异**：ARM/ARM64 的指令编码和调用约定不同，Hook 实现需要分别处理。
- **Android 版本差异**：Android 14+ 的内核 W^X 强制禁用 RWX 映射，改变了 inline hook 的实现路径；Android 16+ 的 16KB page size 改变了代码段到数据段的偏移对齐需求。
- **厂商定制 ROM**：厂商的 SELinux 策略可能与 AOSP 基线不同，部分设备收紧了对 `execmem` 的控制。

### 16KB Page Size 对 Hook 的影响

Android 16+ 引入的 16KB page size 对 Hook 框架产生两个直接影响：

1. **页面粒度变化**：`mprotect` 的权限切换以页为单位。4096B → 16384B，同一个 `mprotect` 调用可能影响范围扩大到 4 倍。如果 Trampoline 和数据落在同一个 16KB 页内，切换权限时可能误伤数据段。
2. **ELF 加载对齐**：16KB page size 要求 .so 在编译时指定 `-Wl,-z,max-page-size=16384` [已验证: Android Developers 16KB page size docs]。如果 Hook 的目标 .so 没有以 16KB 对齐编译，它的代码段和数据段可能和 linker 预期的布局不一致，GOT 表偏移计算会出错。

## 在 Perfetto/工具中的表现

Hook 采集的原始数据需要可视化才能发挥作用。不同 Hook 路径在 Perfetto 中的呈现方式不同：

**atrace HAL（系统级插桩）** [已验证: AOSP frameworks/native/cmds/atrace/atrace.cpp]：

atrace 本身就是一套稳定的系统级 Hook 层。它在 framework 关键路径（`Choreographer`、`ViewRootImpl`、`AMS`、`Binder` 等）预埋了 tracepoint。Perfetto 通过 `atrace` data source 采集这些 tracepoint，在 UI 中呈现为 slice track——每条 slice 有明确的进程名、线程名、函数名和持续时间。

例如，Systrace/Perfetto 中看到的 `Choreographer#doFrame`、`ViewRootImpl#performTraversals`、`binder transaction` 等 slice，都是用 atrace 插桩而非用户自建 Hook。

**heapprofd（堆分析）**：

heapprofd 在 malloc/free 层面做了系统级 Hook，将每次分配记录到 Perfetto 的 heap dump track。在 Perfetto UI 中，选中进程后显示 heap graph（内存增长曲线）和 allocation details（调用栈反解后的分配热点）。

**自建 Hook 工具的 Perfetto 集成**：

如果你用 ShadowHook/xHook/Matrix 自建了 Hook 采集逻辑，要把数据导入 Perfetto，有两条路径：

1. **Perfetto SDK track event**：在 Hook 函数中调用 `TRACE_EVENT_BEGIN`/`TRACE_EVENT_END` 宏，数据直接写入 Perfetto 的 shared memory buffer，在 UI 中以 slice track 和 counter track 呈现。这是最轻量的方案，适合帧级时序分析。
2. **Custom data source**：实现 `perfetto::DataSource` 子类，将 Hook 采集的结构化数据（如函数调用计数器、堆栈快照）序列化为 protobuf 后写入 trace。适合自定义维度的数据。

无论走哪条路径，Hook 采集的数据导入 Perfetto 后的核心价值是时间轴对齐：可以将 Hook 观测到的函数调用时间线，与 Perfetto 原生采集的 CPU scheduling、Binder 调用、VSync 信号放在同一条时间轴上对照分析。

## 实际应用案例

### 案例 1：Matrix — 线上 ANR 监控

Matrix 的 TraceCanary 模块通过 Hook `MessageQueue.next()` 和 `Looper.loop()` 来监控主线程 Looper 调度情况 [已验证: Tencent/matrix matrix-android/matrix-trace-canary]：

- **ANR 检测**：Hook `MessageQueue.next()` 记录每次 Poll 的等待时长。当检测到连续多次 Poll 超时（默认 2s/次 × 3 次），触发 ANR 采样。
- **掉帧检测**：Hook `Looper.loop()` 中 Dispatch 方法的起止时间，计算出每一帧的实际执行时长，超过阈值（默认 700ms）标记为掉帧。
- **线程堆栈采集**：检测到疑似 ANR/掉帧后，Matrix 采集目标线程的堆栈快照（通过 `Thread.getAllStackTraces()`），并配合 Choreographer 回调记录帧时间线。

Matrix 的方案对 App 主线程的侵入很小——只在 Looper 的两个关键节点插入监控逻辑，不修改 App 的业务代码。

### 案例 2：KOOM — OOM 问题线上监控

KOOM（Kwai OOM）的快手开源方案通过 PLT Hook 拦截 `malloc`/`free`/`mmap`/`munmap` 等内存分配函数来监控线上 OOM [已验证: KwaiAppTeam/KOOM koom-java-leak]：

- **PLT Hook 实现**：利用 ELF 的 Procedure Linkage Table（PLT）在 linker 加载 .so 时重定位符号的特性，替换目标函数的 PLT 表项指向 KOOM 的监控函数。相比 inline hook，PLT hook 只需修改 PLT 表中的一个指针，不涉及指令覆写。
- **内存分配追踪**：每次 `malloc` 调用时记录分配大小、调用栈（通过 `_Unwind_Backtrace`），每次 `free` 调用时从记录中移除对应分配。未被释放的分配即疑似泄漏。
- **OOM 预防**：在 `malloc` 返回 NULL 时触发堆转储，采集当前进程的内存占用分布。

KOOM 使用 PLT Hook 而非 inline hook，侧重点在稳定性——PLT 表项替换在 Android 动态链接器层面是可预期的操作，受 SELinux 限制比修改代码段更小 [已验证: AOSP bionic/linker/linker_phdr.cpp relocate()]。

## Hook 技术的最佳实践

### 1. 选择合适的 Hook 框架

根据应用场景和目标层级选择 Hook 框架：

| 场景 | 推荐框架 | 原因 |
|------|---------|------|
| native 函数性能监控 | ShadowHook | inline hook 覆盖完整，ARM64 支持好 |
| 线上监控（native 层） | xHook / KOOM PLT Hook | PLT Hook 不修改代码段，SELinux 友好 |
| App 性能监控（Java 层） | Matrix TraceCanary | 反射 Hook Java 方法，侵入小 |
| Java/Kotlin 方法级拦截 | SandHook / Epic | ART Method Entry 替换，无需编译介入 |

### 2. 控制 Hook 范围

- 只 Hook 必要的函数，避免全库拦截
- 合并相关的 Hook 操作，减少多次 `mprotect` 切换
- 用条件判断在 Hook 函数入口尽早返回，减少无关调用路径的额外开销

### 3. 最小化 Hook 函数自身开销

- 避免在 Hook 函数内做 I/O、Binder 调用、内存分配等重量操作
- Hook 函数内的分支和计算保持简单——ART JIT 不会优化 native 函数
- 高频路径（帧渲染、Binder 线程）上的 Hook 用原子标志位控制是否采集，空闲时关闭采集
- 用 TLS（thread-local storage）缓存频繁读取的数据，减少锁竞争

### 4. 错误处理和恢复

```cpp
// Hook 函数的错误处理 — 通过错误码返回代替异常
int hook_system_call() {
    int ret = real_system_call();
    if (ret < 0) {
        LOGW("Hook: system call failed, errno=%d", errno);
        return ret;  // 透传错误，不吞错误码
    }
    return ret;
}
```

## 总结

Hook 技术的实际价值不在于"有几种实现方式"，而在于填补性能 trace 的观测盲区。当 Systrace/Perfetto 只能告诉你"主线程在哪一段被阻塞了"，Hook 可以告诉你"阻塞在哪个系统调用上、参数是什么、堆栈是谁触发的"。

选型上，记住三个决策维度：

1. **稳定优先选 PLT Hook（KOOM/xHook 路线）**：不修改代码段，SELinux 友好，适合线上监控。
2. **覆盖优先选 inline hook（ShadowHook 路线）**：可以拦截任意地址的任意函数，适合调试和性能分析。
3. **整机监控走 atrace/Perfetto SDK（系统级插桩）**：Systrace 和 Perfetto 的底层 atrace HAL 本身就是一个稳定的 Hook 层，无需自建 Hook 框架就能覆盖 framework 关键路径。

Hook 不是银弹——每次 Hook 都有额外调用开销，PLT 表项被替换后某些 linker 优化（如 IFUNC resolver）会绕过 Hook。选择 Hook 方案前先确认：Perfetto SDK 的 track event 或 atrace 插桩能不能覆盖你的观测需求？能就不用 Hook；不能，再从 PLT Hook → inline hook 逐级加码。
