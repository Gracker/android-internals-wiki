---
title: "应用稳定性全景"
chapter: "20.1"
section: "20.1"
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-06-01"
last_verified_against: "AOSP android-16.0.0_r1, Android Developers ANR documentation, ApplicationExitInfo API reference"
confidence: medium
drafted_date: "2026-05-11"
polish_count: 1
sources:
  - type: official
    path: "https://support.google.com/googleplay/android-developer/answer/9844476"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: official
    path: "https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityManager.java"
  - type: clippings-structure-ref
    path: "Clippings/Android 应用稳定性剖析与优化 - 开篇词：欢迎加入 Android 优化之旅，你将走进稳定性优化的世界！.md"
tags: [stability, crash, anr, oom, app-quality]
related_chapters: ["20.2", "20.4", "20.5", "15.3", "9.1"]
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-01"
last_task9_at: "2026-06-01T14:37:15+08:00"
task9_review_notes: "2026-06-01 Task9 14:37：auto-fixed。P1 1：ContentProvider 查询型 ANR timeout 由 ContentProviderClient.setDetectNotResponding() 配置，不是固定 10 秒；已修正表格和机制段落，回到 Task6 复审。"
task6_reviewed_date: "2026-05-14"
last_task9_review_log: "logs/deep-review/2026-06-01-14-deep-review.md"
status: ready-for-review
reviewed_by: openclaw-task6
reviewed_date: "2026-05-16"
task6_state: "revisiting"
task6_result: needs-rework
task9_state: "reviewed"
task9_result: "auto-fixed"
task2b_state: "fixed"
task2b_result: fixed
pipeline_stage: "task6_pending"
last_task2b_at: "2026-06-01T08:50:00+08:00"
task2b_fixed_at: "2026-06-01T08:50:00+08:00"
last_task6_at: "2026-05-16T16:10:00+08:00"
last_task6_review_log: "logs/review/2026-05-16-16-review.md"
task6_l1_l2_fixes: 1
task6_l3_l4_issues: 1
task6_review_notes: "2026-05-16 Task6：写作层复审通过，frontmatter 格式轻修 1 处；ANR timeout/弹窗边界仍属技术与版本差异问题，沿用既有 queue 回炉项交 Task2B。2026-06-01 Task2B：已补齐 Android 14+ BroadcastReceiver timeout、前台可见 ANR、后台/silent ANR、用户选择等待/关闭与 ApplicationExitInfo 记录边界，回流 Task6。"
last_task9_autofix_at: "2026-06-01"
---

# 应用稳定性全景

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Crash / ANR / OOM 的分类体系与进程退出原因
- 🔹 Java Crash、Native Crash、ANR、OOM 的触发链路与观测入口
- 🔹 Google Play Vitals 与团队内部稳定性指标
- 🔹 稳定性治理流程：预防、发现、诊断、修复、验证
- 🔹 采集方式对比与后续章节的衔接

### 扩展（可选深入）

- 🔸 稳定性治理的组织保障与发版门禁

<!-- outline-end -->

应用稳定性治理要先分清故障类型、度量口径和处理流程。Crash、ANR、OOM 都会表现为退出或卡死，但触发链路、观测入口和治理方法不同；Google Play Vitals 给出外部底线，团队内部指标决定发版节奏；预防、发现、诊断、修复、验证构成日常治理循环。

## Crash / ANR / OOM：三类稳定性问题的分类体系

从观测口径看，Crash、ANR 和 OOM 不应混成同一种“进程被杀”。Java / Native Crash 通常以异常或信号终止进程；LMK / OOM 以资源不足触发回收或抛出 `OutOfMemoryError`；ANR 是系统发现主线程或组件回调超时后的干预流程，可能弹窗、记录 trace、等待用户选择，也可能在后台以 silent ANR 形式被记录。

### Java Crash

Java 层未捕获的异常（RuntimeException、NullPointerException 等）或虚拟机抛出的 Error（OutOfMemoryError、StackOverflowError），最终都会走到 `Thread.dispatchUncaughtException()`。如果应用没有注册 `UncaughtExceptionHandler`，或者注册的 handler 没有拦截住，系统默认行为是终止进程。

AOSP 中的处理链路：

1. 虚拟机在各检查点检测到未处理异常，调用 `HandleUncaughtExceptions()`
2. 通过 JNI 调用 Java 层的 `Thread.dispatchUncaughtException(Throwable)`
3. 沿着 `Thread.getUncaughtExceptionHandler()` → `ThreadGroup.uncaughtException()` → `KillApplicationHandler` 链路，最终调用 `Process.killProcess()` 和 `Runtime.getRuntime().exit()`

[已验证: AOSP android-16.0.0_r1, art/runtime/thread.cc, frameworks/base/core/java/com/android/internal/os/RuntimeInit.java]

Java Crash 的堆栈信息由 ART 虚拟机直接生成，格式规范、可读性好。`CreateInternalStackTrace()`（`art/runtime/thread.cc`）是生成 Java 异常堆栈的核心函数：遍历 `ManagedStack` 链表中的 `ShadowFrame`（解释执行帧）和 `QuickFrame`（编译执行帧），逐帧解析 `ArtMethod` 指针。内部常量 `kMaxSavedFrames = 256` 是首轮栈帧缓存大小，不是硬上限——当实际深度超过 256 时，ART 会通过 `BuildInternalStackTraceVisitor.WalkStack()` 重新遍历完整调用栈。日志中看到的 `... N more` 折叠来自 `Throwable#printStackTrace` 对 common frames 的合并显示，与 `kMaxSavedFrames` 无关。

### Native Crash

Native 代码（C/C++）中的崩溃由信号触发：SIGSEGV（非法内存访问）、SIGABRT（abort 调用）、SIGBUS（总线错误）等。Android 的 `debuggerd` 守护进程负责捕获信号并生成 tombstone 文件。

tombstone 中包含：

- 信号类型和 fault address
- Native 调用栈（通过 `libunwind` 解析）
- 寄存器快照
- 内存映射（`/proc/pid/maps` 摘要）

Native 堆栈解析需要符号表（`.sym` 文件或 `.so` 中的 debug symbols），这在 20.3 节详细讨论。

[已验证: AOSP android-16.0.0_r1, system/core/debuggerd/]

### ANR（Application Not Responding）

ANR 不是崩溃，是系统对"主线程阻塞"的强制干预。触发条件：

| 类型 | 超时阈值 | 触发者 |
|------|----------|--------|
| Input dispatching timed out | 5 秒 | InputDispatcher |
| Service timeout | 前台 Service 20 秒 / 后台 Service 200 秒 | ActiveServices |
| BroadcastReceiver timeout | Android 13 及更低版本：前台 10 秒 / 后台 60 秒；Android 14+：CPU-starved 场景可放宽到前台 10-20 秒 / 后台 60-120 秒 | ActivityManagerService / BroadcastQueue |
| ContentProvider not responding | 由调用方通过 `ContentProviderClient.setDetectNotResponding()` 配置；provider 发布/启动路径另有系统超时 | ContentResolver / ActivityManagerService |

各监控器的实现机制不同。`InputDispatcher`（`frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp`）在分发事件时记录 dispatch timeout 时间点，超时未收到 `finishInputEvent` 回调则触发 ANR。`ActiveServices`（`frameworks/base/services/core/java/com/android/server/am/ActiveServices.java`）通过 `bumpServiceExecutingLocked()` 设置超时消息（`SERVICE_TIMEOUT_MSG`），handler 收到后调用 `ActiveServices.serviceTimeout(proc)`，经由 `mAm.mAnrHelper.appNotResponding(proc, timeoutRecord)` 进入 ANR 流程。BroadcastReceiver 的监控逻辑类似——在系统服务端设置超时定时器，超时后回调对应的 timeout 方法。ContentProvider 查询 ANR 的公开入口是 `ContentProviderClient.setDetectNotResponding()`，超时包含远端进程冷启动和查询执行时间；provider 发布/启动路径另有 AMS 侧系统超时。

ANR 进入 `AnrHelper.appNotResponding()` 之后，系统先采集线程堆栈和进程状态，再由 `AppErrors` 结合进程可见性、后台限制、系统策略和用户交互决定后续动作。前台可见 ANR 通常会展示“应用无响应”对话框，用户可以选择等待或关闭；后台 ANR 与 silent ANR 不一定弹窗，常见结果是记录事件、写入 trace，并按策略终止或保留进程。

trace 文件通常落在 `/data/anr/` 目录（android-16 使用 `ANR_TRACE_DIR`，文件名前缀 `anr_`；旧版设备可能是 `traces.txt`）。`ApplicationExitInfo` 在 API 30+ 提供历史退出查询：当进程因 ANR 退出时，`getReason()` 可返回 `REASON_ANR`；`getTraceInputStream()` 通常可读取 ANR trace。如果进程曾发生 ANR 但后来恢复，并在之后因其他原因退出，系统也可能把之前采集的 trace 附在对应的 `ApplicationExitInfo` 记录中。

[已验证: Android Developers ANR documentation; AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/AnrHelper.java, AppErrors.java, BroadcastQueue.java]

ANR 的治理思路与 Crash 不同。Crash 是"代码逻辑出错，需要修复"；ANR 是"主线程执行耗时操作，需要拆分或异步化"。20.4 节展开 ANR 的治理策略。

[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/AnrHelper.java]

### OOM（OutOfMemory）

OOM 在 Android 上有两层含义：

**Java 堆 OOM**：分配入口是 `Heap::AllocObjectWithAllocator()`（`art/runtime/gc/heap.cc`），先检查当前已分配内存加上新对象大小是否超过 `Runtime.maxMemory()` 限制。超过时进入 `AllocateInternalWithGc()` 触发 GC（根据内存压力选择 kGcCauseForAlloc 对应的 GC 类型），回收后重新检查空间；空间足够时经 `AllocObject()` → `AllocateObject()` 执行实际内存分配。如果 GC 后仍不够，尝试堆扩容（前提是未达到 `HeapGrowthLimit`，由 `dalvik.vm.heapgrowthlimit` 控制）。扩容后仍不够，才抛出 `OutOfMemoryError`。

`Runtime.maxMemory()` 返回值取决于 Manifest 配置：未设置 `largeHeap` 时返回 `dalvik.vm.heapgrowthlimit`（通常 256MB ~ 384MB），设置 `android:largeHeap="true"` 时返回 `dalvik.vm.heapsize`（通常 512MB）。但 `largeHeap` 不等于无限分配——最终仍受物理内存和系统整体内存压力约束。

**虚拟内存耗尽**：进程的虚拟地址空间被耗尽（64 位 ARM 上理论值约 256TB，但实际受 `vm.max_map_count`、文件描述符限制等约束）。典型场景：线程数过多（Android bionic 默认线程栈约 1 MiB，`PTHREAD_STACK_SIZE_DEFAULT` 定义在 `bionic/libc/bionic/pthread_internal.h`，主线程和自定义 `stackSize` 的 Java Thread 可能更大）、内存映射文件过多、JNI 层连续 malloc 但不释放。

OOM 的特殊性在于，它抛出的是 `Error` 而非 `Exception`。Java 的设计意图是 Error 不应被应用层捕获——但实际工程中，部分团队会在 `UncaughtExceptionHandler` 中做差异化处理：只上报 Java 堆 OOM 并尝试恢复（如释放缓存、降低图片分辨率），虚拟内存耗尽则直接放弃。20.5 节展开 OOM 的分类治理。

[已验证: AOSP android-16.0.0_r1, art/runtime/gc/heap.cc]

### 三类问题的关系

```text
                    ┌──────────────┐
                    │  进程被杀     │
                    └──────┬───────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
     ┌──────┴──────┐ ┌────┴─────┐ ┌──────┴──────┐
     │  Crash      │ │   ANR    │ │   LMK/OOM   │
     │ (逻辑错误)   │ │(主线程阻塞)│ │(资源耗尽)   │
     └──────┬──────┘ └────┬─────┘ └──────┬──────┘
            │              │              │
     ┌──────┴──────┐       │       ┌──────┴──────┐
     │ Java Crash  │       │       │ Java 堆 OOM  │
     │ Native Crash│       │       │ 虚拟内存耗尽  │
     └─────────────┘       │       └─────────────┘
                            │
                     ┌──────┴──────┐
                     │ Input 超时   │
                     │ Service 超时 │
                     │ Receiver 超时│
                     │ Provider 超时│
                     └─────────────┘
```

三者的共同点：都会导致用户看到"应用异常退出或卡死"。区分退出原因的第一步是读取 `android.app.ApplicationExitInfo`（API 30+）——这个类封装了进程退出时的上下文：退出原因（`getReason()` 返回 `REASON_CRASH`、`REASON_ANR`、`REASON_LOW_MEMORY` 等常量）、进程 PID（`getPid()`）、退出时间戳（`getTimestamp()`）、异常堆栈（`getTraceInputStream()`：ANR 记录通常可返回 ANR trace；`REASON_CRASH_NATIVE` 在 API 31+ 可返回 tombstone protobuf；也可能因记录过期、缓冲覆盖或权限边界返回 `null`）。通过 `ActivityManager.getHistoricalProcessExitReasons()` 批量查询，可以统计各类型退出的占比和趋势。15.3 节详细介绍了采集方式。

## 稳定性的行业标准与度量维度

### Google Play Vitals 阈值

Google Play 通过 Android Vitals 监控所有上架应用的稳定性和性能表现。两个核心指标：

**User-Perceived Crash Rate（用户感知崩溃率）**：每日活跃用户中，在前台经历过至少一次崩溃的用户占比。

- 全机型不良行为阈值：≥ 1.09%
- 单机型不良行为阈值：≥ 8%

**User-Perceived ANR Rate（用户感知 ANR 率）**：定义类似，统计前台 ANR。

- 全机型不良行为阈值：≥ 0.47%
- 单机型不良行为阈值：≥ 8%

超过阈值后，Play Store 在应用详情页展示警告标签，搜索排名和推荐权重下降。持续不改善可能影响审核。

[已验证: 官方文档, support.google.com/googleplay/android-developer/answer/9844476]

### 行业实践中的度量维度

Google Play 的阈值是底线。团队内部的稳定性度量通常更细：

| 维度 | 说明 | 典型门禁标准 |
|------|------|-------------|
| Crash Rate（按版本） | 单版本的日/周崩溃率 | 大厂内部红线：千分之二（0.2%）以下 |
| Crash-Free Session Rate | 无崩溃会话占总会话数的比例 | 行业基线：≥ 99.5% |
| ANR Rate（按版本） | 单版本日/周 ANR 率 | 大厂内部红线：千分之一（0.1%）以下 |
| Native Crash Rate | Native 崩溃率，单独看 | 取决于 Native 代码占比，通常 ≤ 0.05% |
| OOM Rate | OOM 导致的崩溃占总崩溃的比例 | 单独治理，目标 ≤ 5% 总崩溃 |
| 首次崩溃时间 | 用户打开 App 后多久首次崩溃 | 辅助判断是否与启动流程相关 |
| 崩溃影响用户数 | 单个堆栈簇影响的独立用户数 | Top 10 堆栈簇影响用户数趋势 |

其中「Crash-Free Session Rate」是 Firebase Crashlytics 的默认指标，很多团队拿它做版本发版的门禁——低于 99.5% 不发。

### 采集方式对比

| 方式 | Java Crash | Native Crash | ANR | 优势 | 局限 |
|------|:----------:|:------------:|:---:|------|------|
| Google Play Console | ✅ | ✅ | ✅ | 零接入成本 | 有延迟（约 24h），无法自定义上下文 |
| Firebase Crashlytics | ✅ | ✅ | ✅ | 实时上报、堆栈聚合、用户影响数、ANR tags | ANR 上下文粒度低于自建 SDK |
| 自建 APM SDK | ✅ | ✅ | ✅ | 可附加自定义上下文（内存、线程、用户状态） | 开发维护成本高 |

[结构参考: Clippings/Android 应用稳定性剖析与优化 - 开篇词.md]

采集选择取决于团队规模和稳定性治理阶段。早期用 Google Play Console + Crashlytics 就够；到 DAU 百万级以上，自建 SDK 才有性价比——需要附加运行时上下文（内存水位、线程数、最近用户操作路径）来提升崩溃归因效率。

## 稳定性治理的全局视角

把稳定性治理拆成五个阶段。每个阶段的目标和交付物不同，但它们构成循环：

```text
预防 ──→ 发现 ──→ 诊断 ──→ 修复 ──→ 验证
  ↑                                    │
  └────────────────────────────────────┘
```

### 预防

在崩溃发生之前拦截。工程手段包括：

- **编码规范**：空安全（Kotlin 的 null safety）、资源关闭规范、线程使用规范
- **静态分析**：Lint 规则、Detekt、Android Studio 的 Inspections
- **编译期检查**：R8/ProGuard 的 shrinking 和 obfuscation 配置审查，防止反射调用被误删
- **Crash 防护**：对高风险系统 API 做安全包装——如 `SharedPreferences.commit()` 的 ANR 防护、`WebView` 初始化的 try-catch 包裹、`Toast` 在通知权限关闭时的兼容处理

预防阶段投入产出比最高，但效果最难量化——"没有发生的崩溃"是看不见的。

### 发现

线上崩溃发生后，第一时间知道。依赖监控体系：

- **实时看板**：Crash Rate 和 ANR Rate 按版本、渠道、机型的分时曲线
- **告警机制**：Crash Rate 较前一版本上升超过 X%，或新堆栈簇出现，触发告警
- **自动聚合**：按堆栈相似度聚合成簇（crash clustering），避免同一问题重复处理

发现阶段的核心指标是 MTTD（Mean Time To Detect）——从崩溃发生到团队感知的平均时间。好的监控系统在分钟级完成上报和聚合。

### 诊断

拿到堆栈后，还原崩溃的上下文。诊断效率取决于采集信息的丰富程度：

- **Java Crash**：堆栈 + 异常 message + 设备信息（OS 版本、内存、机型）通常够用
- **Native Crash**：需要 tombstone + 符号表 + 源码对应关系。如果 so 做了 strip，还需要在 CI 中保留未 strip 的版本用于还原行号
- **ANR**：需要 ANR 发生时刻所有线程的堆栈（`ANR trace` 文件）+ 主线程的等待/阻塞关系
- **OOM**：需要崩溃前的内存水位（Java Heap 使用率、Native 内存、FD 数、线程数）+ 对象引用链（如果用了 LeakCanary 或自建 hprof 分析）

20.2 ~ 20.5 节分别展开各类问题的诊断方法。

### 修复

修复本身不复杂，复杂的在于**决策**：

- **影响面评估**：这个崩溃影响了多少用户？是偶现还是必现？集中在特定机型还是全局？
- **修复时机**：是热修复（如果框架支持）还是随下一个版本？热修复的覆盖率和兼容性风险如何？
- **回归风险**：修复是否会引入新问题？需要哪些测试覆盖？

### 验证

修复上线后，确认效果：

- 该堆栈簇的 Crash Rate 是否下降到预期
- 该版本的整体 Crash Rate 是否稳定或改善
- 相同根因是否在其他堆栈簇中出现（表现不同、根因相同）

验证通过后，回到预防阶段——把这个案例的根因加入编码规范或静态分析规则，防止同类问题再次出现。
