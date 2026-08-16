---
title: "JVMTI Agent — ART 运行时动态监控的实验入口与证据边界"
chapter: "26.25"
section: "26.25"
status: finalized
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
tags: [JVMTI, ART, runtime-monitoring, dynamic-instrumentation, profilo, method-tracing]
related_chapters: ["26.18", "26.22", "26.23", "1.35", "14.1"]
last_verified: "2026-08-16"
last_source_verified_at: "2026-08-16"
last_verified_against: "AOSP android-17.0.0_r1; current ART TI, Debug.attachJvmtiAgent, profileable manifest, and JVMTI specification retrieved 2026-08-16"
confidence: medium
sources:
  - type: official
    path: "https://source.android.com/docs/core/runtime/art-ti"
  - type: official
    path: "https://developer.android.com/reference/android/os/Debug"
  - type: official
    path: "https://developer.android.com/guide/topics/manifest/profileable-element"
  - type: specification
    path: "https://docs.oracle.com/en/java/javase/21/docs/specs/jvmti.html"
  - type: android-source
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/ti/agent.cc"
  - type: android-source
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/openjdkjvmti/events.cc"
  - type: android-source
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/openjdkjvmti/deopt_manager.cc"
  - type: android-source
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/openjdkjvmti/ti_redefine.cc"
  - type: android-source
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/openjdkjvmti/ti_extension.cc"
  - type: android-source
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/openjdkjvmti/ti_heap.cc"
  - type: android-source
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/instrumentation.h"
  - type: android-source
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/instrumentation.cc"
  - type: official
    path: "https://developer.android.com/studio/profile/record-java-kotlin-allocations"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/native-heap-profiler"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingManager"
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

JVMTI 是 Java Virtual Machine Tool Interface 的缩写，是虚拟机向调试器和性能分析器提供的 Native 工具接口。Native 在这里指通过 C/C++ 二进制接口运行的代码；profiler 则是采样或记录程序行为、帮助定位性能问题的工具。

ART TI 是 Android 运行时（ART）对 JVMTI 的部分实现。它能观察线程、方法、类、对象分配和 GC，也能设置断点、挂起线程、重定义类。GC 是 garbage collection，即垃圾回收。

本文的 agent 指加载进目标进程、通过 JVMTI 调用和回调工作的 Native 共享库。IDE 是 integrated development environment（集成开发环境），SDK 在这里指集成到应用中的开发与采集组件。接口可以改变程序执行，因此 Android 对普通应用设置了明确边界：

- ART TI 从 Android 8.0 / API 26 开始提供；
- 公共的 `Debug.attachJvmtiAgent()` 从 Android 9 / API 28 开始提供；
- 运行中的 agent 只能附加到 `android:debuggable="true"` 的应用；
- `profileable` 只向受支持的分析工具开放有限能力，不能让发布构建获得 JVMTI attach 权限；
- JVMTI 适合实验室工具、IDE profiler 和专用调试构建，线上发布版监控 SDK 应选择其他公共接口。

源码锚点为 `android-17.0.0_r1`。

Android 官方 [ART TI 说明](https://source.android.com/docs/core/runtime/art-ti) 指出，Android 8 及以上版本由 CTS 检查可调试与不可调试应用的 attach 边界、已实现的 JVMTI API，以及 agent 二进制接口的稳定性。CTS 是 Compatibility Test Suite，即设备实现必须通过的 Android 兼容性测试套件。

AOSP 是 Android Open Source Project，即 Android 开源项目。ART TI 属于 AOSP，设备厂商无需自行重写整套接口。不同 Android 版本仍可能提供不同 capability；capability 是 agent 向当前 JVMTI 环境申请的功能位，例如是否允许生成 GC 事件或给对象设置 tag。

## ART TI、JVMTI plugin 与 agent 的关系

`libopenjdkjvmti` 是 ART 按需加载的 plugin。plugin 指可由宿主动态装入的功能组件；该组件加载后才向 agent 暴露 JVMTI 接口。

agent 文件是 `.so` 共享库，`.so` 是 Android 上常见的 ELF 动态库格式。ELF 是 Executable and Linkable Format，规定可执行文件与共享库的二进制布局。

`jvmtiEnv` 是某个 JVMTI 环境的接口指针，agent 通过它发起调用，ART 再通过已登记的 callback（回调函数）通知事件。JNI 是 Java Native Interface，负责 Java/Kotlin 与 Native 代码之间的调用和对象引用。

adb 是 Android Debug Bridge，用于从开发机向设备发送调试命令。关系图区分了宿主、plugin 和 agent：

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

agent 与应用处于同一地址空间，也就是共享同一个进程内存，没有进程隔离。agent 的越界访问、死锁、ABI 不匹配或回调阻塞都会直接影响目标进程。

ABI 是 Application Binary Interface，规定机器码调用约定、数据布局和二进制符号等接口细节。“标准接口”只约束 JVMTI 调用语义，无法隔离 agent 自身的 Native 缺陷。

## 两种加载时机

### 独立 ART 进程的启动参数

手动启动 `dalvikvm` 或 `app_process` 时，可以同时指定 `-Xplugin:libopenjdkjvmti.so` 和 `-agentpath`。这条路径主要服务 ART 自测。

Zygote 是预加载常用框架代码、再通过 fork 派生应用进程的系统进程；fork 指从现有进程复制出子进程。普通应用由已经运行的 Zygote 派生，无法把 `-agentpath` 写成应用 manifest 的启动选项。manifest 是 APK 中声明组件和运行属性的配置文件。`system_server` 是承载核心 Android 系统服务的进程，也不属于普通应用可用范围。

### 运行中附加

Android 提供 shell 命令，把 agent 附加到已经运行的 debuggable 进程。命令示例只展示接口形状，agent 文件必须位于目标进程能够读取且 SELinux 允许加载的位置。SELinux 是 Android 的强制访问控制机制，会在普通文件权限之外继续检查进程能否访问和加载该文件。

```shell
adb shell cmd activity attach-agent \
  PROCESS_NAME \
  /data/user/0/PACKAGE_NAME/code_cache/libsample-agent.so=AGENT_OPTIONS
```

`PROCESS_NAME` 可以是目标进程名；等号后的内容会作为 options 传给 agent。options 是 agent 自行约定的配置字符串。

官方建议把 `.so` 放进应用 Native library 目录，或通过 `run-as` 以应用身份复制到应用数据目录。`dlopen()` 是进程动态装载共享库的系统函数；把库推到任意公共路径，仍可能因文件权限或 SELinux 策略而加载失败。

应用也可以在 API 28 及以上版本调用 [`Debug.attachJvmtiAgent()`](https://developer.android.com/reference/android/os/Debug) 附加自身。代码示例给调试构建提供一个显式开关。

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

`classLoader` 决定 Native library 的搜索路径，`options` 由 agent 自行解析。不可调试进程会收到 `SecurityException`，其他附加失败通过 `IOException` 报告。实验记录应保留异常类型，不能在失败后仍标成“JVMTI 已启用”。

## Agent_OnLoad、Agent_OnAttach 与 Agent_OnUnload

Android 17 的 [`runtime/ti/agent.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/ti/agent.cc) 会查找三个导出符号。导出符号是共享库向动态链接器公开、可按名称查找的函数入口。

| 符号 | 调用时机 | 工程含义 |
|---|---|---|
| `Agent_OnLoad` | 独立 ART 运行时通过启动参数加载 agent | 普通应用通常不用这条路径 |
| `Agent_OnAttach` | 运行中的进程接受 attach | Android 应用调试最常见 |
| `Agent_OnUnload` | ART 运行时关闭时清理 agent | 日常运行中没有与 attach 对称的 detach 回调 |

detach 指在进程继续运行时解除 agent。JVMTI 没有与 attach 对称的通用卸载接口。

Android 17 在 ART 运行时关闭时调用 `Agent_OnUnload`，源码明确不执行 `dlclose()`，因为已有 agent 可能假设库不会在运行中卸载。agent 可以停用事件、停止自己的工作线程并调用 `DisposeEnvironment()`；这个函数释放 JVMTI 环境，`.so` 仍留在进程地址空间。需要无 agent 的干净基线时，应重启目标进程。

## 最小 agent：只统计 GC 事件

agent 应先查询潜在 capability，再只申请本次实验所需部分。callback 是 ART 在事件发生时调用的 agent 函数。

C++ 示例保留 `GetEnv → capability → callbacks → enable` 这条最小顺序。回调只增加原子计数，避免在 ART 回调线程里做文件 I/O 或复杂分配。

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

示例省略了事件停用、环境释放、计数导出和重复 attach 防护，不能直接作为成品。`jvmtiError` 是 JVMTI API 返回的错误码；完整的调试工具要逐项检查并记录。

工具还要保存 agent 状态机，并保证停用时没有 callback 与销毁操作并发。状态机是对“未初始化、运行、停用、释放”等合法状态及转换条件的明确记录。原子计数则保证多个线程更新同一计数器时不会产生数据竞争。

[JVMTI 规范](https://docs.oracle.com/en/java/javase/21/docs/specs/jvmti.html) 规定，`GarbageCollectionStart` 与 `GarbageCollectionFinish` 只报告 stop-the-world GC 暂停。stop-the-world 表示相关应用线程暂时停止修改虚拟机状态；这对计数可用于统计暂停对，不能代表并发回收阶段或全部 GC CPU 工作。

这两个回调发生在虚拟机仍暂停期间，大多数 JNI 与 JVMTI 调用都不可用。示例只做原子加法；需要解析、分配内存或写文件时，应通知 agent 工作线程稍后处理。

### 为什么要先查 capability

官方文档说明 ART TI 只实现部分 JVMTI，capability 还可能随 Android 版本变化。`GetPotentialCapabilities()` 返回当前 ART 运行时可申请的功能位，`AddCapabilities()` 再为这个 `jvmtiEnv` 申请所需部分。

HotSpot 是 OpenJDK 在桌面和服务器环境中常用的虚拟机实现，它的能力表不能直接套到 ART。若写死另一个虚拟机或 Android 版本的 capability，初始化失败后便难以区分平台缺少能力与 agent 自身错误。

取得 capability 仍不表示事件已经开启。完整顺序是：

1. 查询并申请 capability；
2. 用 `SetEventCallbacks()` 登记回调；
3. 用 `SetEventNotificationMode()` 按事件、必要时按线程启用；
4. 运行实验；
5. 先停用事件，再等待 agent 内部工作结束并释放资源。

phase 是 JVMTI 对虚拟机生命周期阶段的划分，例如加载、启动、正常运行和结束阶段。函数与事件各自规定了允许使用的 phase；在错误阶段调用会失败，事件也可能不会发出。

回调通常在触发事件的线程上执行。回调参数中的 JNI 局部引用和指针一般只在回调返回前有效，因此 agent 要复制仍需使用的数据，不能把临时指针直接交给异步线程。消费者线程是从有界缓冲区取出记录并完成解析、符号化或文件写入的 agent 工作线程。

## 启用事件会怎样影响 ART

去优化是让已经编译或优化的代码退出当前执行形态，以便 ART 提供调试事件所需的可观测语义。影响范围可能是单个方法、指定线程或全部方法与线程，也可能完全不需要这一步。

JVMTI 开销无法概括为“一次额外回调”，任意 agent 也不会自动让全进程永久解释执行。Android 17 的 [`openjdkjvmti/events.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/openjdkjvmti/events.cc) 把事件启用所需的去优化分成 `kNone`、`kLimited`、`kThread` 和 `kFull`：

| 事件 | Android 17 的去优化要求 | 如何理解 |
|---|---|---|
| breakpoint、exception、method entry、method exit | `kLimited` | 不直接请求全量去优化，仍会启用相应 instrumentation |
| exception catch | `kFull` | 请求所有方法和线程进入全量去优化状态 |
| field access/modification、single step、frame pop、force early return 更新 | 指定线程时 `kThread`，未指定线程时 `kFull` | 线程过滤器会改变影响范围 |
| thread/class、compiled method、GC、monitor、object free、VM object alloc 等 | `kNone` | 不因“启用事件”进入上述去优化路径；回调与数据采集仍有成本 |

表中的英文事件名与源码枚举对应，保留原名便于搜索。`kNone` 只表示启用事件时没有进入这组去优化流程，回调频率、数据复制和 agent 消费仍会产生开销。

[`deopt_manager.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/openjdkjvmti/deopt_manager.cc) 对请求计数。启用 `kFull` 或 `kThread` 事件时增加相应请求，停用时移除；多个 agent 或事件可以同时持有请求。全量去优化可以撤销，但要等所有相关请求都被移除。

`kLimited` 同样有成本。breakpoint 是调试器设置的代码暂停位置，ART 需要处理目标方法及活动调用栈；method entry/exit 则会经过 ART Instrumentation 的方法事件路径。

JIT 是 just-in-time compilation，指在应用运行时编译热点代码。stub 是连接编译代码、解释器或运行时服务的一小段入口代码。

入口替换、解释器 stub 与 JIT 的关系见 [1.35](../../part1-fundamentals/ch01-architecture/35-art-deoptimization-performance.md)。Instrumentation listener 的回调位置见 [26.22](22-xtrace-art-dynamic-method-tracing.md)。

## 类重定义要分清标准入口与 ART 扩展

DEX 是 Android 保存字节码、类型和方法索引的可执行格式。ART TI 的类定义输入是只包含一个类定义的 DEX；桌面 JVM 通常接收 class file。

Android 17 的 [`ti_redefine.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/openjdkjvmti/ti_redefine.cc) 为普通 `RedefineClasses()` 和结构性扩展维护了不同模式。

### 普通 RedefineClasses

标准入口可以替换方法体，但会拒绝改变类 schema。这里的 schema 指字段、方法签名、修饰符、父类和接口共同构成的类结构；添加或删除方法、增删字段、改变修饰符或继承关系会返回相应 JVMTI 错误。

已经在线程栈上执行的旧方法会成为 obsolete method，也就是仅供现有调用继续执行的旧版本；后续调用才使用新定义。frame 是线程栈里一次方法调用的执行记录，内联则是编译器把被调方法代码嵌入调用点的优化。因此，“改了一段代码”无法自动推导为“所有线程立刻执行新实现”，还要检查活动 frame、内联、JIT 编译代码和类是否可修改。

### 结构性重定义是条件受限的 ART 扩展

Android 17 的 [`ti_extension.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/openjdkjvmti/ti_extension.cc) 可以通过 `GetExtensionFunctions()` 公布 `com.android.art.class.structurally_redefine_classes`。

该函数只在完整 JVMTI 可用且 JNI ID 使用索引模式时出现，调用前必须枚举并匹配扩展 ID。JNI ID 是 Native 代码引用 Java 字段或方法的标识；索引模式通过间接索引解析目标，避免把可移动的运行时内部指针直接暴露为 ID。

`GetExtensionFunctions()` 用于枚举当前实现提供的非标准扩展。结构性重定义函数的存在需要运行时查询，它不改变标准 `RedefineClasses()` 的默认语义。

扩展仅支持增量添加方法或字段，不允许删除成员，也不允许改变父类和已实现接口。Android 17 的实现会暂停类加载与对象分配、执行 GC、重建受影响的类和实例、更新子类关系，并调用 `InvalidateAllCompiledCode()` 使现有 JIT 编译代码失效。它适合 IDE 的受控开发操作，不能当作线上热修复协议。

Android Studio Apply Changes 是否使用普通重定义、结构性扩展或其他部署机制，取决于修改内容和工具版本。仅凭界面提示无法判断进程执行了哪一种 ART 运行时操作。

## 对象 tag 与堆遍历

heap（堆）是 ART 管理 Java/Kotlin 对象的内存区域，堆遍历会访问其中满足条件的对象。tag 是 agent 与某个对象关联的 64 位整数元数据，不会写入应用类的字段。`SetTag()` / `GetTag()` 依赖 `can_tag_objects`。

Android 17 的 [`ti_heap.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/openjdkjvmti/ti_heap.cc) 为每个 `jvmtiEnv` 维护 object tag table；堆遍历、引用遍历和 `GetObjectsWithTags()` 都从这张表读取。

`ObjectFree` 还需要 `can_generate_object_free_events`，并且只通知带非零 tag 的已回收对象。它不能自动报告所有对象释放。回调只给出已释放对象的 tag，原对象引用已经不可用。

`jlong` 是有符号 64 位整数，tag 的业务含义完全由 agent 约定。设计 tag 时要处理数值复用、溢出、多个 `jvmtiEnv` 之间的隔离和上传隐私。对整个堆做遍历或引用追踪可能明显扰动目标进程，没有基线对照时不能把结果视为原始运行状态。

allocation 指为对象或 Native 缓冲区申请内存。[heapprofd](https://perfetto.dev/docs/data-sources/native-heap-profiler) 是 Perfetto 的 Native 堆采样器，会按采样规则记录分配调用栈。观察 Native 内存分配时，它更贴近问题。

观察 Java/Kotlin allocation 时，[Android Studio Memory Profiler](https://developer.android.com/studio/profile/record-java-kotlin-allocations) 已提供受支持的调试路径。自定义 agent 更适合验证标准工具无法表达的窄问题。

## attach 只面向调试构建

debuggable 是运行中附加 JVMTI agent 的硬边界。即使应用不通过 Google Play 分发，把 debuggable 构建发给终端用户也会扩大被调试、注入和修改的攻击面。

[profileable manifest 元素](https://developer.android.com/guide/topics/manifest/profileable-element) 的正确形式是 `<profileable android:shell="true" />`。它允许 shell 侧受支持的 profiler 在发布构建上做有限的本地性能采集，仍不会开放 JVMTI attach。

该元素写在 `<application>` 内部；`android:enabled="false"` 会关闭系统服务和 shell 工具的性能采集权限。

Binder 是 Android 的进程间通信机制，ANR 是 Application Not Responding（应用无响应）。profile 指一次性能采样产生的分析文件或采集过程；hook 指截获或替换内部函数调用的非公开做法。

线上发布场景应按目标选择公共能力：

| 目标 | 更合适的入口 |
|---|---|
| 业务方法与阶段耗时 | 编译期字节码插桩、`android.os.Trace`、AndroidX Tracing |
| 系统调度、Binder、频率和渲染因果 | Perfetto system trace，受权限与 profileable 约束 |
| Native 分配 | heapprofd / Android Studio Memory Profiler |
| API 35 及以上的应用 profile 请求 | [ProfilingManager](https://developer.android.com/reference/android/os/ProfilingManager)，接受限流和不保证执行的契约 |
| Java 崩溃、ANR、进程退出 | 应用稳定性采集与 `ApplicationExitInfo` |
| ART 私有 hook 实验 | 仅在固定版本和受控设备验证，边界见 [26.22](22-xtrace-art-dynamic-method-tracing.md) |

JVMTI 与 [26.18](18-bytecode-instrumentation-monitoring-automation.md) 的编译期插桩适用范围不同。编译期插桩能进入发布构建，但只能观察构建时选定的点；JVMTI 能在运行中选择事件和类，却要求 debuggable，并可能改变 ART 执行形态。

## 一次可复现的 JVMTI 实验

build fingerprint 是系统构建指纹，ABI 是机器码调用与数据布局约定，page size 是虚拟内存管理的基本页大小。三者都可能改变 agent 的兼容性或实验结果。

commit 是源码版本标识，NDK 是 Native Development Kit，即 Android 的 C/C++ 工具链。构建 ID 和 `.so` 摘要用于把事件、符号文件与唯一二进制产物对应起来。

每次实验应保存这些信息：

- 设备型号、Android build fingerprint、API、ABI 和 page size；
- 应用 versionCode、签名摘要、`debuggable`、`profileable` 与构建 ID；
- agent 源码 commit、NDK、编译器、ABI、符号文件和 `.so` 摘要；
- attach 入口、库路径、options、`Agent_OnAttach` 返回值和每个 `jvmtiError`；
- potential / requested / granted capability，即运行时可申请、agent 请求和最终取得的功能位；
- 启用的事件、线程过滤器、开始与停止时刻；
- 无 agent、已 attach 但未开事件、开启目标事件三组对照；
- wall time、CPU time、帧、内存、GC、JIT 状态和丢弃事件数；wall time 是日历经过时间，CPU time 是线程实际占用处理器的累计时间；
- 进程重启后的恢复结果。

实验结论要限定范围。OEM 指设备或系统构建厂商。Android 17 AOSP 源码可以解释参考实现机制，目标 OEM 镜像上的可用性仍需用同一 agent 验证；一次真机成功只能证明该构建和配置成功。

遇到 attach 失败时，依次检查 debuggable、ABI、库可读性、SELinux、导出符号、capability 和事件 phase。每一步都有公开状态或错误码可记录，优先级高于扫描 ART 私有内存。
