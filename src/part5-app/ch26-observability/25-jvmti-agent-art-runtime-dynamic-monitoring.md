---
title: "JVMTI Agent — ART 运行时动态监控的实验入口与证据边界"
chapter: "26.25"
section: "26.25"
status: finalized
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
tags: [JVMTI, ART, runtime-monitoring, dynamic-instrumentation, profilo, method-tracing]
related_chapters: ["26.18", "26.22", "26.23", "1.35", "14.1"]
last_verified: "2026-07-29"
confidence: medium
sources:
  - type: aosp
    path: "art/openjdkjvmti/events.cc (android-17.0.0_r1) — 经由本卷 [1.35] 交叉引用"
  - type: aosp
    path: "art/openjdkjvmti/deopt_manager.cc (android-17.0.0_r1) — 经由本卷 [1.35] 交叉引用"
  - type: aosp
    path: "art/openjdkjvmti/ti_redefine.cc (android-17.0.0_r1) — 经由本卷 [1.35] 交叉引用"
  - type: aosp
    path: "art/runtime/instrumentation.h / instrumentation.cc (android-17.0.0_r1) — 经由本卷 [26.22] 交叉引用"
  - type: aosp
    path: "tools/base/profiler/native/perfa/perfa.cc + memory/memory_tracking_env.cc (Android Studio 源码树 platform/tools/base) — 经由本卷 [14.1] 交叉引用"
  - type: official
    path: "https://developer.android.com/studio/profile/record-java-kotlin-allocations — 经由本卷 [14.1] 交叉引用"
  - type: article
    path: "技术文章/source/juejin-android/2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md"
last_body_apply_at: "2026-07-24T07:15:55+08:00"
last_body_apply_run_id: "20260724-071534-2a71a09c"
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
last_review_finalize_at: "2026-07-30T14:10:00+08:00"
last_review_finalize_run_id: "20260730-140532-12094eb9"
last_rework_at: "2026-07-29T14:25:42+08:00"
last_rework_run_id: "20260729-142542-rework-afd64006"
---

# 26.25 JVMTI Agent — ART 运行时动态监控的实验入口与证据边界

## JVMTI 的使用边界

JVMTI 是 ART 提供给调试器和 profiler 的进程内原生接口。它能观察线程、方法、类、对象分配和 GC，也能设置断点、挂起线程、重定义类。接口能力很强，因此 Android 对普通应用设置了清晰的安全边界：

- ART TI 从 Android 8.0 / API 26 开始提供；
- 公共的 `Debug.attachJvmtiAgent()` 从 Android 9 / API 28 开始提供；
- 运行中的 agent 只能附加到 `android:debuggable="true"` 的应用；
- `profileable` 不等于 `debuggable`，不能让 release 应用获得 JVMTI attach 权限；
- JVMTI 更适合实验室工具、IDE profiler 和专用调试构建，不是线上 release 监控 SDK 的通用入口。

源码锚点为 `android-17.0.0_r1`。Android 官方 [ART TI 说明](https://source.android.com/docs/core/runtime/art-ti) 还指出，Android 8 及以上版本由 CTS 检查 debuggable / non-debuggable attach 边界、已实现的 JVMTI API 和 agent 二进制接口。厂商无需另行实现这套接口，但不同 Android 版本可提供的 capability 仍可能不同。

## ART TI、JVMTI plugin 与 agent 的关系

ART 没有把 JVMTI 固定放在运行时核心路径中，而是通过 `libopenjdkjvmti` plugin 暴露接口。agent 是被加载进目标应用进程的 `.so`，与 plugin 通过 `jvmtiEnv` 调用和回调通信。

下面的关系图用于区分宿主、plugin 和 agent。

```text
adb / Android Studio / debuggable 应用
                 │ attach 请求
                 ▼
        ActivityManager + ART 权限检查
                 │
                 ▼
应用进程 ┌─────────────────────────────────────┐
         │ ART runtime                         │
         │   └─ libopenjdkjvmti plugin         │
         │          ▲ jvmtiEnv 调用 / 回调      │
         │          │                          │
         │      libsample-agent.so             │
         │          └─ 有界缓冲与工作线程       │
         └─────────────────────────────────────┘
```

agent 与应用处于同一地址空间。agent 的越界访问、死锁、ABI 不匹配或回调中的阻塞都会直接影响目标进程；“标准接口”只约束 JVMTI 调用语义，不会隔离 agent 自身的 native 缺陷。

## 两种加载时机

### 独立 ART 进程的启动参数

手动启动 `dalvikvm` 或 `app_process` 时，可以同时指定 `-Xplugin:libopenjdkjvmti.so` 和 `-agentpath`。这条路径主要服务 ART 自测。设备上的普通应用由已运行的 Zygote fork 出来，不能把 `-agentpath` 当成应用 manifest 的启动选项；`system_server` 也不属于普通应用可用范围。

### 运行中附加

Android 提供 shell 命令，把 agent 附加到已经运行的 debuggable 进程。下面的命令只展示接口形状，agent 文件必须位于目标进程能够读取且 SELinux 允许加载的位置。

```shell
adb shell cmd activity attach-agent \
  PROCESS_NAME \
  /data/user/0/PACKAGE_NAME/code_cache/libsample-agent.so=AGENT_OPTIONS
```

`PROCESS_NAME` 可以是目标进程名；等号右侧内容会作为 options 传给 agent。官方建议把 `.so` 放进应用 native library 目录，或通过 `run-as` 复制到应用数据目录。把库推到任意公共路径并不保证目标进程可以 `dlopen()`。

应用也可以在 API 28 及以上版本调用 [`Debug.attachJvmtiAgent()`](https://developer.android.com/reference/android/os/Debug) 附加自身。下面的示例用于调试构建中的显式开关。

```kotlin
import android.os.Debug

fun attachGcCounterAgent() {
    check(BuildConfig.DEBUG)
    Debug.attachJvmtiAgent(
        "libsample-agent.so",
        "mode=gc-counter",
        object {}.javaClass.classLoader
    )
}
```

`classLoader` 决定 native library 的搜索路径，`options` 由 agent 自行解析。non-debuggable 进程会收到 `SecurityException`，加载失败则是 `IOException`。不要捕获异常后继续把实验标成“JVMTI 已启用”。

## Agent_OnLoad、Agent_OnAttach 与 Agent_OnUnload

Android 17 的 [`runtime/ti/agent.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/ti/agent.cc) 会查找三个导出符号：

| 符号 | 调用时机 | 工程含义 |
|---|---|---|
| `Agent_OnLoad` | 独立 runtime 通过启动参数加载 agent | 普通应用通常不用这条路径 |
| `Agent_OnAttach` | 运行中的进程接受 attach | Android 应用调试最常见 |
| `Agent_OnUnload` | runtime 关闭时清理 agent | 不是日常运行中的“detach 回调” |

Android 17 在 runtime 关闭时调用 `Agent_OnUnload`，源码还明确不执行 native library close，因为已有 agent 可能假设库不会在运行中卸载。JVMTI 没有与 attach 对称的通用“卸载 agent”接口。agent 可以停用事件、停止自己的工作线程并 `DisposeEnvironment()`，但这不等于 `.so` 已从进程地址空间移除。需要干净基线时重启目标进程。

## 最小 agent：只统计 GC 事件

agent 应先查询潜在 capability，再只申请本次实验所需部分。下面的 C++ 示例用于说明 `GetEnv → capability → callbacks → enable` 的最小顺序；回调只增加原子计数，避免在 ART 回调线程里做文件 I/O 或复杂分配。

```cpp
#include <atomic>
#include <cstdint>
#include <jni.h>
#include <jvmti.h>

namespace {

std::atomic<uint64_t> g_gc_start_count{0};
std::atomic<uint64_t> g_gc_finish_count{0};

void JNICALL OnGcStart(jvmtiEnv*) {
  g_gc_start_count.fetch_add(1, std::memory_order_relaxed);
}

void JNICALL OnGcFinish(jvmtiEnv*) {
  g_gc_finish_count.fetch_add(1, std::memory_order_relaxed);
}

jint StartAgent(JavaVM* vm) {
  jvmtiEnv* jvmti = nullptr;
  if (vm->GetEnv(
          reinterpret_cast<void**>(&jvmti),
          JVMTI_VERSION_1_0) != JNI_OK ||
      jvmti == nullptr) {
    return JNI_ERR;
  }

  jvmtiCapabilities potential{};
  if (jvmti->GetPotentialCapabilities(&potential) != JVMTI_ERROR_NONE ||
      potential.can_generate_garbage_collection_events == 0) {
    return JNI_ERR;
  }

  jvmtiCapabilities requested{};
  requested.can_generate_garbage_collection_events = 1;
  if (jvmti->AddCapabilities(&requested) != JVMTI_ERROR_NONE) {
    return JNI_ERR;
  }

  jvmtiEventCallbacks callbacks{};
  callbacks.GarbageCollectionStart = &OnGcStart;
  callbacks.GarbageCollectionFinish = &OnGcFinish;
  if (jvmti->SetEventCallbacks(&callbacks, sizeof(callbacks))
      != JVMTI_ERROR_NONE) {
    return JNI_ERR;
  }

  if (jvmti->SetEventNotificationMode(
          JVMTI_ENABLE,
          JVMTI_EVENT_GARBAGE_COLLECTION_START,
          nullptr) != JVMTI_ERROR_NONE) {
    return JNI_ERR;
  }
  if (jvmti->SetEventNotificationMode(
          JVMTI_ENABLE,
          JVMTI_EVENT_GARBAGE_COLLECTION_FINISH,
          nullptr) != JVMTI_ERROR_NONE) {
    jvmti->SetEventNotificationMode(
        JVMTI_DISABLE,
        JVMTI_EVENT_GARBAGE_COLLECTION_START,
        nullptr);
    return JNI_ERR;
  }
  return JNI_OK;
}

}  // namespace

extern "C" JNIEXPORT jint JNICALL Agent_OnAttach(
    JavaVM* vm, char*, void*) {
  return StartAgent(vm);
}

extern "C" JNIEXPORT jint JNICALL Agent_OnLoad(
    JavaVM* vm, char*, void*) {
  return StartAgent(vm);
}
```

示例省略了事件停用、环境释放、计数导出和重复 attach 防护，不能直接作为成品。生产质量的调试工具还要检查每一个 `jvmtiError`，保存 agent 状态机，并保证停用时没有 callback 与销毁操作并发。

### 为什么要先查 capability

官方文档只承诺“实现了一部分 JVMTI”，并提示 capability 可能随 Android 版本变化。agent 应使用 `GetPotentialCapabilities()` 读取当前 runtime 的能力，再调用 `AddCapabilities()`。把桌面 HotSpot 或另一个 Android 版本的 capability 表写死，失败时很难区分“平台不支持”和“agent 初始化有误”。

有 capability 也不表示事件已经开启。常见顺序是：

1. 查询并申请 capability；
2. 用 `SetEventCallbacks()` 登记回调；
3. 用 `SetEventNotificationMode()` 按事件、必要时按线程启用；
4. 运行实验；
5. 先停用事件，再等待 agent 内部工作结束并释放资源。

回调运行在哪个线程、允许调用哪些 JVMTI 方法，要按具体事件的规范和当前 phase 判断。稳妥的回调只复制必要字段到预分配或有界缓冲区，把解析、符号化和文件写入交给 agent 自己的消费者线程。

## 启用事件会怎样影响 ART

不能把 JVMTI 开销概括为“只多一次回调”，也不能说“任意 agent 都让全进程永久解释执行”。Android 17 的 [`openjdkjvmti/events.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/openjdkjvmti/events.cc) 把事件启用所需的去优化分成 `kNone`、`kLimited`、`kThread` 和 `kFull`：

| 事件 | Android 17 的去优化要求 | 如何理解 |
|---|---|---|
| breakpoint、exception、method entry、method exit | `kLimited` | 不直接请求全量去优化，仍会启用相应 instrumentation |
| exception catch | `kFull` | 请求所有方法和线程进入全量去优化状态 |
| field access/modification、single step、frame pop、force early return 更新 | 指定线程时 `kThread`，未指定线程时 `kFull` | 线程过滤器会改变影响范围 |
| thread/class、compiled method、GC、monitor、object free、VM object alloc 等 | `kNone` | 不因“启用事件”进入上述去优化路径；回调与数据采集仍有成本 |

[`deopt_manager.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/openjdkjvmti/deopt_manager.cc) 对请求做计数。启用 full 或 thread 级事件时增加对应请求，停用时移除；多个 agent 或多个事件可以同时持有请求。因此，全量去优化可以撤销，但必须等相关请求都被移除。

`kLimited` 也不是“零影响”。例如设置某个 breakpoint 时，ART 还需要处理目标方法及活动栈；method entry/exit 则会走 ART Instrumentation 的方法事件路径。详细的入口替换、解释器 stub 与 JIT 关系见 [1.35]，Instrumentation listener 的回调位置见 [26.22]。

## 类重定义要分清标准入口与 ART 扩展

Android 的类定义输入是单类 DEX，不是桌面 JVM 常见的 class file。Android 17 的 [`ti_redefine.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/openjdkjvmti/ti_redefine.cc) 为普通 `RedefineClasses()` 和结构性扩展维护了不同模式。

### 普通 RedefineClasses

标准入口适合替换方法实现，不允许随意改变类 schema。添加或删除方法、添加字段、改变类修饰符、父类或接口等变化会按对应 JVMTI 错误拒绝。已经在栈上的旧方法要以 obsolete method 继续执行，后续调用再使用新定义。

这也是为什么“改了一段代码”不能自动推导为“所有线程立刻执行新实现”。活动 frame、内联、JIT code 和类是否可修改都会影响结果。

### 结构性重定义是条件受限的 ART 扩展

Android 17 的 [`ti_extension.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/openjdkjvmti/ti_extension.cc) 可以公布 `com.android.art.class.structurally_redefine_classes`。它不是标准 JVMTI `RedefineClasses()` 的默认语义，而且只在 runtime 条件允许时出现。

扩展仅支持增量添加方法或字段，不允许删除成员，也不允许改变父类和已实现接口。源码路径会暂停类加载与对象分配、执行 GC、替换受影响的类和实例、更新子类关系，并调用 `InvalidateAllCompiledCode()` 清理 JIT code。它适合 IDE 的受控开发操作，不适合作为线上热修复协议。

Android Studio Apply Changes 是否使用普通重定义、结构性扩展或其他部署机制，取决于修改内容和工具版本。不能仅凭界面提示推断进程执行了哪一种 runtime 操作。

## 对象 tag 与堆遍历

`SetTag()` / `GetTag()` 依赖 `can_tag_objects`。Android 17 的 [`ti_heap.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/openjdkjvmti/ti_heap.cc) 为每个 `jvmtiEnv` 维护 object tag table；堆遍历、引用遍历和 `GetObjectsWithTags()` 都从这张表读取。`ObjectFree` 主要用于通知带非零 tag 的对象已经回收，不等于“为所有对象自动发送释放事件”。

tag 是 agent 自己解释的 `jlong`，ART 不知道它代表分配序号、对象类别还是外部索引。设计 tag 时要处理复用、溢出、agent 多环境隔离和上传隐私。对整个堆做遍历或引用追踪可能明显扰动目标进程，不能在没有基线对照的情况下把结果当作原运行状态。

若目标只是观察 native 分配，heapprofd 比 JVMTI 对象事件更贴近问题；若目标是 Java/Kotlin allocation，Android Studio Memory Profiler 已提供受支持的调试路径。自己写 agent 的价值通常在于验证一个标准工具无法表达的窄问题。

## attach 不等于线上动态监控

debuggable 是硬边界。即使应用不通过 Google Play 分发，把 debuggable 构建发给终端用户也会扩大被调试、注入和修改的攻击面。`android:profileable="true"` 允许受支持的 profiler 在更接近 release 的构建上采集有限信息，但不会开放 JVMTI attach。

线上 release 场景应按目标选择公共能力：

| 目标 | 更合适的入口 |
|---|---|
| 业务方法与阶段耗时 | 编译期字节码插桩、`android.os.Trace`、AndroidX Tracing |
| 系统调度、Binder、频率和渲染因果 | Perfetto system trace，受权限与 profileable 约束 |
| Native 分配 | heapprofd / Android Studio Memory Profiler |
| API 35 及以上的应用 profile 请求 | ProfilingManager，接受限流和不保证执行的契约 |
| Java 崩溃、ANR、进程退出 | 应用稳定性采集与 `ApplicationExitInfo` |
| ART 私有 hook 实验 | 仅在固定版本和受控设备验证，边界见 [26.22] |

JVMTI 与 [26.18] 的编译期插桩也不是互相替代。编译期插桩能进入 release，但只能观察构建时选定的点；JVMTI 能在运行中选择事件和类，却要求 debuggable，并可能改变 ART 执行形态。

## 一次可复现的 JVMTI 实验

建议为每次实验保存这些信息：

- 设备型号、Android build fingerprint、API、ABI 和 page size；
- 应用 versionCode、签名摘要、`debuggable`、`profileable` 与构建 ID；
- agent 源码 commit、NDK、编译器、ABI、符号文件和 `.so` 摘要；
- attach 入口、库路径、options、`Agent_OnAttach` 返回值和每个 `jvmtiError`；
- potential / requested / granted capability；
- 启用的事件、线程过滤器、开始与停止时刻；
- 无 agent、已 attach 但未开事件、开启目标事件三组对照；
- wall time、CPU time、帧、内存、GC、JIT 状态和丢弃事件数；
- 进程重启后的恢复结果。

实验结论也要限定范围。Android 17 AOSP 的源码可以解释机制，目标 OEM 镜像上的可用性仍需用同一 agent 验证；一次真机成功则只能证明该构建和配置成功。遇到 attach 失败时，按 debuggable、ABI、库可读性、SELinux、导出符号、capability 和事件 phase 的顺序检查，比扫描 ART 私有内存更可靠。
