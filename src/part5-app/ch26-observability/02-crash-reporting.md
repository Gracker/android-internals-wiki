---
title: "Crash 上报体系搭建"
chapter: "26.2"
section: "26.2"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-05-15"
last_verified_against: "AOSP android-16.0.0_r1, Android Developers docs, Firebase Crashlytics docs, Clippings structure references"
confidence: medium
drafted_date: "2026-05-15"
polish_count: 0
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
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/RuntimeInit.java"
  - type: aosp
    path: "system/core/debuggerd/crash_dump.cpp"
tags: [crash-reporting, symbolication, deobfuscation, alerting]
related_chapters: ["26.1", "20.2", "20.3", "19.24", "20.8"]
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: pending
task2b_state: fixed
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: "2026-06-03"
last_task6_at: "2026-06-03T22:37:00+08:00"
last_task6_review_log: logs/review/2026-06-03-22-review.md
task6_reviewed_at: "2026-05-15T02:12:00+08:00"
task6_reviewed_by: openclaw-task6
task6_review_notes: '2026-05-15 task6 review: pass-light-edit。L1/L2 小修 3 处(结构性元叙述 1、抽象词风险 2);无新增 L3/L4 回炉项,等待 Task9 技术复审。'
task9_reviewed_date: "2026-06-03"
last_task9_at: "2026-06-03T21:54:00+08:00"
last_task9_review_log: "logs/deep-review/2026-05-15-02-deep-review.md"
task9_result: auto-fixed
task9_review_notes: "2026-05-15 Task9:needs-rework。Native signal-safe 持久化边界与 ApplicationExitInfo 补偿链路缺失,需 Task2B 回炉。"
task2b_result: fixed-lite
last_task2b_lite_at: 2026-06-04
---

last_task9_autofix_at: "2026-06-03"
---

## 附录:源码调研补充 - Android 线上诊断能力版本边界(2026-05-15)

*来源:AIW 每日源码调研 | 关联章节:§26.5、§13.2、§15.5、§20.3*

### A.1 ApplicationExitInfo 版本行为差异

| API Level | ANR Trace | Native Tombstone | 备注 |
|-----------|-----------|------------------|------|
| 30 | `getTraceInputStream()` ✅ | ❌ | 仅 Java ANR trace |
| 31+ | ✅ | ✅ (`tombstone.proto`) | `REASON_CRASH_NATIVE` 返回 protobuf |

**SDK envelope 与系统 exit reason 去重键**:pid + timestamp + process_name + reason + tombstone/build_id + top_frame

### A.2 ProfilingManager(API 35+)

Android 15 `ProfilingManager.requestProfiling()` 支持 App-driven system trace / heap / stack profiling:

```java
public void requestProfiling(
    int profilingType,        // PROFILING_TYPE_SYSTEM_TRACE | HEAP_DUMP | HEAP_PROFILE | STACK_TRACE
    Bundle options,
    String packageName,
    CancellationSignal signal,
    Executor executor,
    Consumer<ProfilingResult> resultCallback
)
```

**Result 回调**:
```java
ProfilingResult#getResultFilePath()  // trace 文件路径(系统管理,应用只读)
ProfilingResult#getResultStatus()    // 状态码
```

**限制**:Rate limiter 存在(结果去重、频率控制);连续 profiling 类型建议提前开始、及时取消

### A.3 ProfilingTrigger(API 36+)

Android 16 事件触发采集:

**Trigger 类型**:
- `TRIGGER_TYPE_APP_FULLY_DRAWN`:app 报告首帧完成并可交互
- `TRIGGER_TYPE_APP_REQUESTED`:app 主动请求
- `TRIGGER_TYPE_ANR`:ANR 发生时(推测)
- `TRIGGER_TYPE_CRASH`:crash 发生时(推测)

**使用模式**:
```java
val triggerBuilder = ProfilingTrigger.Builder(ProfilingTrigger.TRIGGER_TYPE_APP_FULLY_DRAWN)
    .setRateLimitingPeriodHours(1)
profilingManager.registerTrigger(triggerBuilder.build(), executor, callback)
```

### A.4 Android 线上诊断能力版本表

| 能力 | Android 10-14 (API 29-34) | Android 15 (API 35) | Android 16+ (API 36) |
|------|---------------------------|---------------------|----------------------|
| 退出原因查询 | `getHistoricalProcessExitReasons()` ✅ | ✅ | ✅ |
| ANR Trace | `getTraceInputStream()` ✅ | ✅ | ✅ |
| Native Tombstone | ✅ (API 31+) | ✅ | ✅ |
| App-driven Profiling | ❌ | `ProfilingManager` ✅ | ✅ |
| Trigger-based Profiling | ❌ | ❌ | `ProfilingTrigger` ✅ |
| 系统 trace 路径 | Perfetto / bugreport | ✅ | ✅ |

### A.5 Native Crash Signal Handler 边界(未经一手验证)

- Signal handler 必须是 async-signal-safe:不能调用 `malloc`/`free`、不能使用锁、不能分配内存
- Crashpad Android client 使用 out-of-process handler 模型
- `sigaction()` 设置 `SA_SIGINFO` 获取 signal number 和 siginfo_t 地址

<!-- AIW-源码调研-2026-05-15 -->


---

<!-- AIW-源码调研-2026-05-16 -->
## 补充:Native Crash 与 ApplicationExitInfo 补偿链路(源码级验证)

### 关键源码路径

| 组件 | 源码路径 |
|------|----------|
| ApplicationExitInfo Java API | `frameworks/base/core/java/android/app/ApplicationExitInfo.java` |
| AMS 历史退出原因服务 | `frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java` |
| Google Breakpad crash 客户端 | `external/google-breakpad/client/crashpad_client.cc` |
| Crashpad (后续版本) | `external/crashpad/client/crashpad_client.cc` |

### 退出原因常量(API 30+)

- `REASON_SIGNALED` (2):进程被信号终止
- `REASON_CRASH` (4):Java 未捕获异常
- `REASON_CRASH_NATIVE` (5):Native 代码崩溃--补偿链路核心

### Native Crash 信号捕获链路

1. **信号注册**:crashpad_client 在进程启动时注册 `SIGSEGV`、`SIGABRT` 等信号处理器
2. **minidump 生成**:崩溃时 `CrashpadHandler` 生成 minidump 到 `/data/data/<package>/databases/crashpad/`
3. **进程退出**:通过 `Process.exit(code)` 退出
4. **AMS 感知**:Zygote 通知 AMS,AMS 通过 `appDiedLocked()` 记录退出原因
5. **补偿读取**:下次启动通过 `getHistoricalProcessExitReasons()` 拉取 `REASON_CRASH_NATIVE`

### 版本差异

| 版本 | API Level | 变化 |
|------|-----------|------|
| Android 11 | 30 | 引入 `ApplicationExitInfo`,`REASON_CRASH_NATIVE`=5 |
| Android 12 | 31 | `REASON_CRASH_NATIVE` 可通过 `traceInputStream` 读取 tombstone protobuf |

### 已知未验证项

- crashpad_client 信号注册具体时机(需进一步源码确认)
- minidump 路径与 `ApplicationExitInfo` 的字段关联
- Android 15+ 是否从 Breakpad 完全迁移到 crashpad 官方仓库

<!-- AIW-源码调研-2026-05-19: Native Crash Signal Handler 与 ApplicationExitInfo 补偿链路 -->

### 源码级补充:Native Crash Signal Handler 边界(2026-05-19)

**来源**:DeepResearch/2026-05-19-native-crash-applicationexitinfo-compensation-chain.md

**debuggerd 架构三层**:
- debuggerd 常驻进程:通过 `sigaction()` 注册信号处理
- crash_dump fork 子进程:执行实际 dump
- tombstone 写入:`/data/tombstones/tombstone_XX`(Android 10+ 逐步 proto 化)

**async-signal-safe 严格边界**:
- 允许:`write()`, `pipe()`, `sigprocmask()`, `sync()`
- 禁止:`malloc()`, `free()`, `printf()`, `std::string`, 任何堆操作
- debuggerd handler 通过 `write()` 向 debuggerd 写管道,不在进程内堆分配

**源码路径**:
- `system/core/debuggerd/crash_dump.cpp l.303, l.497` - 主流程与 tombstone 写入路径
- `system/core/debuggerd/libdebuggerd/tombstone.cpp l.336` - tombstone 写入实现
- `system/core/debuggerd/proto/tombstone.proto` - proto 格式定义

**ApplicationExitInfo 补偿入口**(API 30+):
- `REASON_CRASH_NATIVE` = 5,对应 tombstone 文件
- `getTraceFile()` 返回 `/data/tombstones/tombstone_XX` 的 FileInputStream
- 服务端追踪:`ActivityManagerService.java l.5213`
- 系统记录:`AppExitInfoTracker.java`

**版本边界**:
- Android 9 以下:无 ApplicationExitInfo,需自建 Signal Handler
- Android 11+:完整支持 getTraceFile()
- Android 14+:proto 格式 tombstone

<!-- AIW-源码调研-2026-05-25 -->
### 源码调研补充(2026-05-25)

**调研议题**:Android 版本化线上诊断能力--ApplicationExitInfo、ProfilingManager 与 ProfilingTrigger

**关键发现**:

1. **debuggerd async-signal-safe 约束**(已在 §26.2 中标注源码路径,此处补充验证)
   - 允许:`write()`, `pipe()`, `sigprocmask()`, `sync()`
   - 禁止:`malloc()`, `free()`, `printf()`, `std::string`,任何堆操作
   - 源码:`system/core/debuggerd/crash_dump.cpp l.303, l.497`

2. **Crashpad Out-of-Process Handler 模型**(未经一手 AOSP 源码验证,建议读 `external/google-breakpad/client/crashpad_client_linux.cc`)
   - signal handler 必须是 async-signal-safe
   - minidump 写入由独立 handler 进程完成,不阻塞应用主线程
   - 双策略:RequestCrashDumpHandler(与已运行 handler 通信)/ LaunchAtCrashHandler(crash 时启动)

3. **ApplicationExitInfo 补偿入口版本差异**
   - API 30:`getTraceInputStream()` 仅对 ANR 返回 trace
   - API 31+:`REASON_CRASH_NATIVE` 返回 native tombstone protobuf

**信息源**:developer.android.com NDK debug 文档(✅)