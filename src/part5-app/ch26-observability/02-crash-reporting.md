---


title: "Crash 上报体系搭建"
chapter: "26.2"
section: "26.2"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-15"
last_source_verified_at: "2026-08-15"
last_verified_against: "Current Android 17 profiling triggers / ApplicationExitInfo / Android vitals crash / WebView termination / symbolication docs, Firebase Crashlytics docs, and AOSP android-17.0.0_r1 sources retrieved 2026-08-15"
confidence: high
sources:
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪?-Android开发高手课-极客时间 1.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪?-Android开发高手课-极客时间 2.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪?-Android开发高手课-极客时间 3.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪?-Android开发高手课-极客时间 33.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪?-Android开发高手课-极客时间 35.md"
  - type: clipping
    path: "Clippings/Android 应用稳定性剖析与优化 - Java Crash 监控:实现自定义 Crash 处理器.md"
  - type: clipping
    path: "Clippings/Android 应用稳定性剖析与优化 - Native Crash 监控:为我们应用插上监控 Native Crash 的电子眼.md"
  - type: official
    path: "https://developer.android.com/reference/java/lang/Thread.UncaughtExceptionHandler"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/crash"
  - type: official
    path: "https://developer.android.com/tools/retrace"
  - type: official
    path: "https://developer.android.com/ndk/guides/ndk-stack"
  - type: official
    path: "https://developer.android.com/build/include-native-symbols"
  - type: official
    path: "https://firebase.google.com/docs/crashlytics/android/get-deobfuscated-reports"
  - type: official
    path: "https://firebase.google.com/docs/crashlytics/ndk-reports"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: official
    path: "https://developer.android.com/reference/android/app/ActivityManager#getHistoricalProcessExitReasons(java.lang.String,%20int,%20int)"
  - type: official
    path: "https://developer.android.com/develop/ui/views/layout/webapps/handle-termination"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingManager"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingTrigger"
  - type: official
    path: "https://developer.android.com/about/versions/17/features#profiling-triggers"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/RuntimeInit.java"
  - type: aosp
    path: "system/core/debuggerd/crash_dump.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/RuntimeInit.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/handler/debuggerd_handler.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/crash_dump.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/libdebuggerd/tombstone.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/proto/tombstone.proto"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AppExitInfoTracker.java"
tags: [crash-reporting, symbolication, deobfuscation, alerting]
related_chapters: ["26.1", "20.2", "20.3", "19.19", "20.8"]
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: reviewed
task2b_state: fixed
last_draft_polish_at: "2026-08-15T18:25:21+08:00"
last_draft_polish_run_id: "20260815-182521-gracker-writing-463"
last_review_finalize_at: "2026-08-15T18:25:21+08:00"
last_review_finalize_run_id: "20260815-182521-gracker-writing-463"
last_rework_at: "2026-08-15T18:25:21+08:00"
last_rework_run_id: "20260815-182521-gracker-writing-463"
---


# 26.2 Crash 上报体系搭建

崩溃（Crash）上报体系需要在进程退出前尽量保存定位证据，并在后续可用的执行窗口把证据送到分析系统。Java Crash 指未处理的 Java/Kotlin 异常，Native Crash 指 C/C++ 等原生代码触发的致命信号；捕获机制见 20.2、20.3 和 19.19。本节关注本地留存、多进程归集、符号化、告警和发布门禁。符号化是把混淆名或二进制地址还原成可读函数、文件和行号的过程。

平台源码上界为 Android 17 / API 37 / `android-17.0.0_r1`。崩溃主路径位于 Android 框架、bionic C 库与 debuggerd 等用户空间组件，不依赖 Android 17 的某项内核专有实现，因此不附加内核源码标签。

## Crash SDK 的四段路径：捕获、序列化、持久化、上报

崩溃发生后，当前线程、堆、锁、文件描述符和线程池都可能处于异常状态。崩溃入口只保存最小现场；进程退出后，由下次启动或健康的辅助进程补充设备与版本信息、上传并重试；服务端负责符号化、聚合和告警。

下面的流程图用于区分崩溃现场与后续处理窗口。

```mermaid
flowchart TD
  A["Java 未捕获异常 / Native 致命信号"] --> B["受约束的捕获入口"]
  B --> C["写入最小记录"]
  C --> D["继续系统默认退出路径"]
  E["下次启动 / 健康的辅助进程"] --> F["扫描已完成记录"]
  F --> G["补充版本与设备上下文"]
  G --> H["压缩、脱敏、限流"]
  H --> I["服务端接入与幂等去重"]
  I --> J["反混淆 / 符号化"]
  J --> K["Issue 聚合、告警、工单"]
```

`B → C` 对应崩溃现场，不能假设应用运行环境健康；网络请求、数据库索引和复杂对象序列化应放在后续的 `E → H` 阶段。

### 捕获：Java 与 Native 不是同一种执行环境

Java 未捕获异常的公开入口是 `Thread.UncaughtExceptionHandler`，即线程的未捕获异常处理器。在 Android 17 的 [`RuntimeInit.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/RuntimeInit.java) 中，`LoggingHandler` 记录 `FATAL EXCEPTION`，`KillApplicationHandler` 向 ActivityManager（系统活动与进程管理服务）报告崩溃，并在 `finally` 中执行 `Process.killProcess()` 与 `System.exit(10)`。`mCrashing` 状态位用于阻止崩溃处理再次递归进入。

自定义 Java handler（处理器）应在安装时保存前一个处理器，并在最小记录逻辑结束后调用它。调用应放在 `finally` 中且只发生一次；不调用前一个处理器会改变平台的日志、报告与进程退出语义。处理器运行在发生异常的线程上，因此 Java 路径也不适合等待网络、获取业务锁或遍历大型对象图。

Android 平台的 Native Crash 路径约束更多。debuggerd 是 Android 的原生崩溃诊断机制；Android 17 的 [`debuggerd_handler.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/handler/debuggerd_handler.cpp) 会预先准备备用栈，并以 `SA_RESTART | SA_SIGINFO | SA_ONSTACK | SA_EXPOSE_TAGBITS` 标志注册信号处理。收到致命信号后，它在专门准备的环境中启动辅助进程 `crash_dump`，读取崩溃进程的状态。[`crash_dump.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/crash_dump.cpp) 通过 Linux 进程追踪接口 `ptrace` 读取线程状态，再经负责集中保存记录的 tombstoned 服务写出 tombstone。tombstone 是包含信号、寄存器、线程栈和内存映射等信息的原生崩溃诊断记录。

这条路径需要明确两个边界：

- 信号处理代码在目标进程一侧初始化；debuggerd 守护进程不会进入应用替它注册 `sigaction`，`crash_dump` 与 tombstoned 只参与后续抓取和保存。
- 平台处理器依赖预分配栈、管道、专用辅助进程和平台权限，普通 Crash SDK 不能照搬。自定义信号处理函数只能使用经过审计的异步信号安全（async-signal-safe）操作和预分配内存；现场不能构造 JSON、申请堆内存、获取普通互斥锁或发起网络请求。

第三方应用通常无权读取 `/data/tombstones`。应用侧一般通过经过验证的 Native Crash SDK 生成 minidump（只保存诊断所需线程、寄存器和选定内存信息的小型转储），或在后续启动时查询记录近期进程退出原因的系统 API `ApplicationExitInfo`。tombstone、bugreport（系统诊断包）、logcat（Android 日志工具）与 `ndk-stack`（NDK，即 Native Development Kit，原生开发工具包中的地址符号化工具）主要用于开发和平台诊断。

### 最小记录：字段用于关联，不堆积现场信息

捕获入口可以围绕一份版本化的 `CrashEnvelope` 组织数据。CrashEnvelope 是崩溃事件的外层数据结构，其中存放摘要和附件索引；Java 与 Native 路径能够安全写出的字段集合不同。

| 字段 | 用途 | 采集边界 |
| --- | --- | --- |
| `schema_version` | 让服务端兼容旧客户端 | 表示数据结构版本；废弃字段仍保留解析能力 |
| `crash_id` / `sequence` | 幂等上传和端侧关联；幂等表示同一事件重复提交时只记一次 | 尽量提前生成；不要在 Native 信号处理器内临时创建 UUID（Universally Unique Identifier，通用唯一标识符） |
| `event_time_wall_ms` | 与发布、日志和服务端事件对时 | 系统日期时间可能被校准，不单独用于计算耗时 |
| `elapsed_realtime_ms` | 进程内排序和启动后时长 | 使用只递增、不受系统日期校时影响的单调时钟；该值不能跨设备比较 |
| `process_name` / `pid` / `thread_name` | 区分应用进程、进程 ID（PID）与线程 | Native 样本优先使用 minidump 或 tombstone 中已有字段 |
| `exception_type` / `signal` | 区分 Java 异常和 Native 致命信号 | 端侧不做复杂根因推断 |
| `raw_stack` / `top_frame` | 反混淆、符号化和初步聚合 | Native 侧还需 `.so` 共享库、相对地址、ABI（应用二进制接口）与 Build ID（构建时写入二进制的唯一标识） |
| `application_id` / `version_code` / `git_sha` | 绑定发布产物、R8 映射文件（mapping）和原生符号文件（symbols） | `git_sha` 是 Git 提交哈希；这些字段由构建流水线注入，不在崩溃现场拼装 |
| `breadcrumbs` | 提供崩溃前的有限操作轨迹；breadcrumb 是预先记录的关键事件摘要 | 平时写入固定容量环形缓冲区，现场只读取已完成槽位 |
| `privacy_policy_version` | 追踪脱敏与字段许可规则 | 不保存用户明文输入、认证令牌（token）或完整 URL |

对 Java 路径，可以在受控上限内输出异常类型和堆栈；对 Native 路径，推荐让成熟 SDK 或平台机制保存寄存器、线程和内存映射。若某个字段必须通过分配、锁或 Binder（Android 进程间通信机制）调用获取，就不属于 Native 信号处理器的最小字段。

### 序列化：摘要与附件分开演进

Crash 样本不宜直接复用普通业务埋点格式。它的单条价值更高，附件大小差异也更大，还需要跨多个线上版本保持可解析。可以把数据分为两层：

- 摘要：`crash_id`、数据结构版本、异常或信号、进程、线程、构建标识、栈顶帧（top frame）、采样策略版本。
- 附件：完整 Java 堆栈、minidump、可公开取得的 tombstone 数据、受限日志片段、崩溃前的有限操作记录或诊断追踪。

每个附件应记录类型、字节数、压缩方式、脱敏策略版本和内容摘要。服务端先接收小型摘要并完成幂等登记，再根据问题组（issue）的出现时间、样本价值和流量策略请求附件。issue 是服务端把同一根因候选的多条崩溃归在一起形成的问题组。字段新增应保持向后兼容；任一端不认识新字段时，仍要允许最小样本入库。

### 持久化：按捕获环境选择写入方式

“临时文件 → 把数据同步到存储（例如调用 `fsync`）→ 原子重命名（rename）”适合健康执行环境或经过约束的 Java 崩溃记录，但不能直接套用到 Native 信号处理器。

对 Java 路径和后续整理进程，可以采用以下规则：

1. 每个应用进程写独立目录或独立文件，避免共享可变索引。
2. 先完成临时文件，再将其原子重命名为可扫描文件；需要抵御掉电时，还要考虑文件与父目录的持久化语义。
3. 下次启动只处理完整记录，损坏或半写文件进入隔离区，不反复阻塞上传队列。
4. 设置字节配额和保留策略，优先保存未上传的致命崩溃（fatal）样本及新问题组的代表附件。

SQLite 可以用于进程恢复后的索引，并记录“待上传、上传中、已确认”等状态转换，但不应成为崩溃现场唯一的写入路径。崩溃线程可能正持有数据库锁，事务和连接状态也未必可用。

对 Native 路径，应使用经过验证的 minidump 实现、预打开文件描述符与固定大小缓冲区，或把复杂抓取交给健康的进程外组件。平台 debuggerd 采用专用架构，不能作为应用层任意信号处理器的通用模板。

### 上报：崩溃进程不负责把请求发完

上传由下次启动或健康的辅助进程执行。处理顺序通常是：扫描完整记录、补充设备与版本字段、脱敏、上传摘要、按服务端策略上传附件、确认后回收本地文件。fatal 表示会导致进程退出的未处理崩溃，non-fatal 表示应用捕获并继续运行的异常记录；二者不能混用同一统计口径。

| 优先级示例 | 样本 | 处理方式 |
| --- | --- | --- |
| P0 | 新版本启动致命崩溃、核心交易路径致命崩溃 | 尽快上传摘要；附件仍受网络、隐私和大小策略限制 |
| P1 | 新问题组、Native Crash、影响面快速扩大的问题组 | 提高代表样本保留率，并核对符号文件状态 |
| P2 | 已知问题组的重复样本、非致命异常 | 保留计数和分层抽样，减少重复附件 |
| P3 | 大型日志或追踪文件 | 默认不进入崩溃首批上传，只在授权诊断流程中获取 |

服务端以 `crash_id` 和附件内容摘要实现幂等，也就是同一份数据重复上传时只入库一次，不能把客户端重试计为多个受影响事件。采样记录还要包含策略版本与纳入概率，否则服务端无法在分层采样后解释趋势。上传模块自身应公开待上传字节数、丢弃原因、重试次数和最近成功时间，避免“采集失效”被误读为“稳定性改善”。

## 多进程 Crash 上报的可靠性保证

“多进程”至少包含三类对象：应用自己声明的普通进程、isolated service（隔离服务）进程，以及 WebView renderer（WebView 渲染进程，负责解析和绘制网页内容的独立进程）。后两类由不同的系统约束管理，三者不能使用同一套初始化假设。

### 普通应用进程：各自捕获，统一归集

对应用清单（manifest）中以 `android:process` 声明的普通应用进程，可以在每个进程安装轻量捕获模块，但只让主进程或专用上传进程拉取配置并执行网络上传。

| 层次 | 设计 | 需要验证的失败场景 |
| --- | --- | --- |
| 初始化 | 每个目标应用进程安装异常处理器，初始化要幂等 | 子进程早于主进程启动或直接崩溃 |
| 本地文件 | 以稳定的进程角色和唯一文件名隔离写入 | 多进程同时崩溃、PID 被系统复用 |
| 配置 | 主进程写版本化只读快照，其他进程读取 | 快照写到一半、配置过期、回滚 |
| 上传 | 一个健康进程扫描所有应用进程目录 | 主进程无法启动、上传中途再次被杀 |
| 服务端 | 事件幂等与问题组聚合分开 | 同一退出记录被 SDK 与系统历史重复发现 |

进程 ID 只在一次进程生命周期内有意义，不能单独作为崩溃事件 ID。可以用预生成 ID，或用“无法还原原始安装标识的派生值 + 进程序列 + 单调时间 + 构建标识”形成事件关联键，并在服务端检测键冲突。

### WebView 渲染进程：由宿主应用观察退出

WebView 渲染进程由系统和 WebView 实现管理，不是应用可以安装普通 Crash SDK 的业务进程。API 26 起，[`WebViewClient.onRenderProcessGone()`](https://developer.android.com/reference/android/webkit/WebViewClient#onRenderProcessGone(android.webkit.WebView,%20android.webkit.RenderProcessGoneDetail)) 会把渲染进程退出通知宿主应用。

回调中的 `WebView` 已不可继续使用。宿主必须把它从视图层级移除、销毁并清理引用，再决定是否创建新实例。返回 `true` 表示应用已经处理该退出；如果任一共享该渲染进程的 `WebView` 返回 `false`，系统会按渲染进程的退出情况终止应用，崩溃退出会表现为应用崩溃。多个 `WebView` 可能共享同一个渲染进程，因此每个受影响实例都要正确处理回调。上报字段应来自宿主回调提供的 `RenderProcessGoneDetail`（包含是否崩溃及渲染进程优先级等退出信息）、页面的脱敏标识和宿主版本，不能假设应用能够读取渲染进程内部的 Java 栈。

### 隔离服务：不能假设具备上传权限

应用清单中设置 [`android:isolatedProcess="true"`](https://developer.android.com/guide/topics/manifest/service-element#isolated) 的 Service（Android 服务组件）会在特殊隔离进程中运行。该进程没有自己的应用权限，只能通过 Service 的启动或绑定接口与应用交互。它虽然来自同一个 APK，也不能被视为可以直接访问应用私有状态或发起网络上传。

可行的设计是：应用的管理进程通过受控 IPC（Inter-Process Communication，进程间通信）接收隔离服务平时产生的有限诊断数据；进程退出后，再用 `ApplicationExitInfo` 对照进程名、Linux 用户标识（UID）、时间和退出原因补齐记录。隔离进程崩溃后已无法保证 Binder 调用继续执行，因此不能把收尾保存依赖于崩溃发生后的跨进程调用。

### 动态特性模块：记录是否安装，不虚构独立版本

动态特性模块（dynamic feature）通常跟随同一个应用发布产物管理版本。Crash 记录应包含已安装的分包（split）和模块集合、功能开关及实验配置，并继续使用应用构建标识关联 R8 映射文件与原生符号文件。只有业务系统确有独立插件版本时才记录插件版本；普通动态特性模块不能被描述成同一 `versionCode` 下可任意变化的模块版本。

## 用 `ApplicationExitInfo` 补偿退出记录

API 30 起，应用可以通过 [`ActivityManager.getHistoricalProcessExitReasons()`](https://developer.android.com/reference/android/app/ActivityManager#getHistoricalProcessExitReasons(java.lang.String,%20int,%20int)) 查询近期进程退出信息。它适合发现 SDK 没有保存到的低内存终止、ANR、Java Crash 和 Native Crash，也能帮助核对多进程退出。

这项 API 不是无限期、无损的崩溃档案库：

- 返回值来自有界历史记录，按时间从新到旧排列；调用方应保存上次处理到的时间戳，以及由进程名和退出原因等字段组成的记录指纹，并容忍旧记录被淘汰。
- `ApplicationExitInfo` 的 trace（诊断追踪数据）存放在单独的全局循环存储中，可能被包括其他应用在内的后续记录覆盖；`getTraceInputStream()` 允许返回 `null`。
- API 30 的 trace 主要用于 ANR（Application Not Responding，应用无响应）；API 31 起，`REASON_CRASH_NATIVE` 可以返回以 Protocol Buffers 编码的 tombstone 数据流。Protocol Buffers 是一种结构化二进制序列化格式。
- 同一个事件可能同时被 Crash SDK 和系统历史发现。去重应综合应用构建、进程名、相近的发生时间、退出原因、SDK 事件 ID，以及可用的致命信号、Build ID 或栈顶帧，不能只拼接“进程 ID + 时间戳”。

Android 17 的公开模型见 [`ApplicationExitInfo.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java)，服务端记录与诊断追踪数据管理可从 [`AppExitInfoTracker.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AppExitInfoTracker.java) 继续追踪。

## 符号化与反混淆服务

原始混淆名和 Native 地址不能稳定对应源码。每个可发布构建都要把应用包、R8 映射文件和原生符号文件归档为同一组不可变产物。

### Java / Kotlin：R8 映射文件是发布产物的一部分

官方 [`retrace`](https://developer.android.com/tools/retrace) 使用 R8 映射文件还原混淆后的类、方法和行号；工具位于 SDK 命令行工具（Command-Line Tools）的 `cmdline-tools/<version>/bin/retrace`。Firebase Crashlytics 的 [反混淆说明](https://firebase.google.com/docs/crashlytics/android/get-deobfuscated-reports) 则说明其 Gradle 插件会检测混淆并上传映射文件。

自建系统至少应绑定这些键：

- `application_id`、构建变体（variant）、`version_code` 与 `version_name`；
- 构建 ID 或 Git 提交哈希；
- R8 映射文件的内容摘要；
- 最终 APK（Android 应用安装包）或 AAB（Android App Bundle，应用商店发布包）的内容摘要，以及发布系统中的产物 ID。

同一版本号可能被重新构建，单靠 `versionCode` 不能选出正确的 R8 映射文件。构建流水线应在发布前验证应用包与映射文件已经同时归档；启用混淆却缺失映射文件时，应直接阻断发布，避免上线后只能把栈标记为“无法反混淆”。

Kotlin 的协程（coroutine）、内联函数（inline function）与匿名函数（lambda）会改变栈的形态。问题分组不能只取原始栈顶帧文本；应先用 retrace 反混淆，再结合异常类型、规范化后的异常消息、完整调用栈和构建范围生成候选签名。

### Native：用 Build ID 找到准确的共享库

Android 的发布构建（release build）默认会从 Native 库中剥离调试信息，以减小安装包。官方 [Native debug symbols 文档](https://developer.android.com/build/include-native-symbols) 说明，`SYMBOL_TABLE` 可提供函数名，`FULL` 还可提供源码文件和行号；App Bundle 可以携带相应符号，APK 构建也会生成可单独上传的符号压缩包。用于分析的未剥离库或符号文件应保存在受控产物库中，不随应用发布给用户。

Native 样本和符号产物至少要通过以下信息匹配：

| 信息 | 作用 |
| --- | --- |
| ABI | 区分同一共享库针对不同指令集生成的产物 |
| `.so` 文件名与 ELF Build ID | 选择准确的二进制和符号文件；ELF（Executable and Linkable Format，可执行与可链接格式）是 Android 原生二进制采用的文件格式 |
| 程序计数器（pc）、相对地址与加载映射（load map） | 计算模块内地址，并处理 ASLR（Address Space Layout Randomization，地址空间布局随机化）造成的装载地址变化 |
| NDK、编译器和链接参数 | 解释栈展开（unwind）、内联与帧指针（frame pointer）的差异；NDK 是 Android 的 Native 开发工具包 |
| 未剥离产物或独立符号文件 | 恢复函数名、源码文件和行号 |

对第三方或非默认目录的 Native 库，不能只验证主模块中 Native 构建工具 CMake 的输出。以 Crashlytics 为例，额外库可能需要通过 `unstrippedNativeLibsDir` 指定未剥离库的目录；自建流水线同样应枚举最终 APK 或 AAB 中的每个 `.so` 文件，检查其 Build ID，并确认产物库中存在匹配的符号文件。缺失任一目标 ABI 的符号文件时，都应阻断相应发布产物。

### 问题聚合：符号化成功后再生成签名

混淆名、绝对地址和随构建变化的程序计数器都不适合作为跨版本问题组的主键。应把“事件的固定 ID”和“可重新计算的问题签名”分开：

1. Java/Kotlin 候选签名：异常类型、反混淆后的稳定调用帧序列、规范化后的异常消息、构建范围。
2. Native 候选签名：致命信号、模块 Build ID、符号化后的函数、模块内偏移区间、ABI。
3. 服务端保留原始事件与问题组的对应关系；映射文件、符号文件或聚类算法更新后，可以重新符号化和归组，但不改动原始事件。

## Crash 实时告警与分级响应

“出现新问题组”只是一个信号。告警还要结合受影响用户、版本暴露量（实际使用该版本的用户数或会话数）、发生场景、相对稳定版本的变化和统计不确定性，否则低暴露版本容易因偶发样本触发误报，高暴露版本又可能因绝对数量大而长期告警。

### 先把指标分母说清楚

[Android Vitals](https://developer.android.com/topic/performance/vitals/crash) 的 crash rate（崩溃用户率）是“每日活跃用户中至少经历一次崩溃的用户比例”；user-perceived crash rate（用户感知崩溃率）只统计应用处于活跃使用状态时发生崩溃的用户比例，并属于核心质量指标。

自建平台还常用 crash-free（无崩溃率）指标，它与 Vitals 的统计口径不同：

- `Crash-free users = 1 - 发生目标致命崩溃的去重用户数 / 同口径活跃用户数`，表示无崩溃用户比例。
- `Crash-free sessions = 1 - 包含目标致命崩溃的会话数 / 有效会话总数`，表示无崩溃会话比例。
- `Issue impact` 表示单个问题组的影响面，记录受影响用户、事件数、版本、设备、首次发生时间与最近发生时间。

这里的“目标致命崩溃”“活跃用户”“有效会话”和统计窗口必须写进指标定义。致命崩溃、非致命异常与业务主动捕获的异常应分别统计；非致命异常不能混入 Vitals 风格的用户感知崩溃率。

### 告警使用暴露量、基线和严重性

S0/S1/S2 在这里仅作为内部响应级别示例；Android 平台没有这套分级标准。

| 级别 | 触发信号示例 | 响应动作 |
| --- | --- | --- |
| S0 | 启动或核心交易路径出现高影响致命崩溃；灰度版本相对稳定基线显著恶化 | 暂停放量或回滚，通知值班负责人，保留代表性完整附件 |
| S1 | 单个问题组的影响持续增长；特定机型、系统版本或同一 `.so` 文件的 Build ID 明显集中 | 分派模块负责人，调整分层采样，评估热修或小版本 |
| S2 | 低影响非致命异常、老版本存量问题、已知问题组的稳定重复 | 进入排期或继续观察，不中断当前发布 |

阈值应由产品流量、基线波动、样本纳入概率和事故容忍度校准，不能把固定的每日活跃用户数（DAU）、事件数或等待时间写成通用答案。告警页面至少要同时展示分母、趋势、表示估计不确定范围的置信区间或可信区间、版本与设备分布、符号化状态、近期发布记录和代表样本，值班人员才能判断这是发布回归、机型兼容还是数据质量问题。

### 发布门禁检查可诊断性

灰度平台可以根据以下条件决定是否自动扩大版本覆盖范围：

- 新版本暴露不足或不确定性过大时保持当前灰度，不根据几个样本自动扩量或回滚。
- 使用相同分母和窗口，对比候选版本与稳定基线；采样变化时先根据每层样本的纳入概率还原整体趋势。
- 未处置的高严重性新问题组阻止自动扩量。
- 启用 R8 却缺少映射文件，或包含 Native 库却缺少对应符号文件或 Build ID 时，阻断发布。
- Crash SDK 的本地丢弃率、上传成功率和符号化成功率异常时，将稳定性指标标记为数据不完整。

这类门禁把“应用是否稳定”和“出问题后是否能定位”同时纳入发布判断。

## Crash 数据隐私与成本控制

Crash 附件可能包含 URL、请求参数、用户输入、文件路径、设备标识和日志片段。采集前就要确定字段许可与保留策略：

- 端侧使用允许字段清单；操作轨迹摘要写入环形缓冲区前完成脱敏。
- URL 默认只保留必要的主机名（host）、路径模板和错误码，丢弃查询参数（query）、片段标识（fragment）与身份凭据。
- 日志按标签（tag）和字段清单截取，不上传认证令牌、Cookie、账号、手机号或用户正文。
- 大附件设定单独的字节配额、保留期和下载审计，过期后只保留统计摘要。
- 服务端实施项目隔离和最小权限，原始附件访问需要可审计的诊断理由。

成本控制不能只做统一抽样。新问题组、稀有设备、Native Crash 与核心场景需要分层保留代表样本；已知重复问题组可以降低附件采集率，但仍要记录用于估算总体事件数的纳入概率。看板还要呈现被丢弃事件数、配额占用、重试次数、附件大小分位数和符号化失败率，因为采集缺口会让无崩溃率指标偏高。

## Android 10–17 的能力边界

下表只列与 Crash 上报直接相关的公开能力。`ApplicationExitInfo` 从 Android 11 开始提供，Android 10 没有这项 API。

| 平台版本 | API | 相关变化 |
| --- | ---: | --- |
| Android 10 | 29 | 没有 `ApplicationExitInfo`；应用依赖自己的 Crash SDK、平台日志和开发诊断工具 |
| Android 11 | 30 | 新增 `ApplicationExitInfo` 与 `getHistoricalProcessExitReasons()`；`getTraceInputStream()` 主要返回 ANR 诊断追踪数据 |
| Android 12 | 31 | `REASON_CRASH_NATIVE` 的 `getTraceInputStream()` 可以返回以 Protocol Buffers 编码的 tombstone 数据流 |
| Android 15 | 35 | 新增 `ProfilingManager`；它受频率限制且请求不保证执行，不是 Crash 捕获 API |
| Android 16 | 36 | 新增 `ProfilingTrigger`，可按受支持事件请求诊断采集 |
| Android 17 | 37 | 诊断触发器新增冷启动、OOM（内存耗尽）、CPU 使用过量、异常行为和应用兼容性等类型 |

`ProfilingManager` 支持系统追踪（`PROFILING_TYPE_SYSTEM_TRACE`）、Java 堆转储（`PROFILING_TYPE_JAVA_HEAP_DUMP`）、堆性能剖析（`PROFILING_TYPE_HEAP_PROFILE`）和调用栈采样（`PROFILING_TYPE_STACK_SAMPLING`）等类型。`ProfilingTrigger.TRIGGER_TYPE_APP_FULLY_DRAWN` 对应应用调用 `reportFullyDrawn()`，表示应用认为界面已经完整绘制，并不等同于“首帧完成”。Android 17 的 `TRIGGER_TYPE_OOM` 还明确要求自定义 `Thread.UncaughtExceptionHandler` 继续调用默认处理器，否则系统无法使用该触发器。因此，自定义 Java 处理器仍须调用默认处理链。这些 API 适合收集性能诊断资料，不能代替 Java 未捕获异常处理器、Native 崩溃机制或退出历史查询。

## 小结

可靠的 Crash 上报系统依赖三条边界：

- 崩溃现场只执行与捕获环境相符的最小操作。Java 未捕获异常处理器要继续平台默认退出链，Native 信号处理器要遵守异步信号安全约束。
- 普通应用进程、WebView 渲染进程与隔离服务分别处理；`ApplicationExitInfo` 用于补偿和核对近期退出，不能被当作永久档案。
- R8 映射文件、原生符号文件与发布包组成同一组构建产物。服务端完成符号化后再聚合，并以明确分母、暴露量和严重性驱动告警。

## 参考资料

- [Thread.UncaughtExceptionHandler](https://developer.android.com/reference/java/lang/Thread.UncaughtExceptionHandler)
- [Android Vitals：Crash](https://developer.android.com/topic/performance/vitals/crash)
- [ApplicationExitInfo](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [ActivityManager.getHistoricalProcessExitReasons](https://developer.android.com/reference/android/app/ActivityManager#getHistoricalProcessExitReasons(java.lang.String,%20int,%20int))
- [WebView renderer 退出处理](https://developer.android.com/develop/ui/views/layout/webapps/handle-termination)
- [ProfilingManager](https://developer.android.com/reference/android/os/ProfilingManager)
- [ProfilingTrigger](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [Android 17：profiling triggers](https://developer.android.com/about/versions/17/features#profiling-triggers)
- [R8 retrace](https://developer.android.com/tools/retrace)
- [NDK stack](https://developer.android.com/ndk/guides/ndk-stack)
- [为 App Bundle 或 APK 添加 Native debug symbols](https://developer.android.com/build/include-native-symbols)
- [Firebase Crashlytics 反混淆](https://firebase.google.com/docs/crashlytics/android/get-deobfuscated-reports)
- [Firebase Crashlytics NDK 报告](https://firebase.google.com/docs/crashlytics/ndk-reports)
- [AOSP Android 17：RuntimeInit.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/RuntimeInit.java)
- [AOSP Android 17：debuggerd_handler.cpp](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/handler/debuggerd_handler.cpp)
- [AOSP Android 17：crash_dump.cpp](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/crash_dump.cpp)
- [AOSP Android 17：tombstone.cpp](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/libdebuggerd/tombstone.cpp)
- [AOSP Android 17：tombstone.proto](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/proto/tombstone.proto)
- [AOSP Android 17：ApplicationExitInfo.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java)
- [AOSP Android 17：AppExitInfoTracker.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AppExitInfoTracker.java)
