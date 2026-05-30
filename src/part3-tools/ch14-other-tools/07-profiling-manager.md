---
title: "ProfilingManager"
chapter: "14.7"
section: "14.7"
section_title: "ProfilingManager"
status: ready-for-review
updated_by: "openclaw-task6"
updated_date: "2026-05-30"
task6_result: "pass-light-edit"
task6_reviewed_by: "openclaw-task6"
task6_reviewed_date: "2026-05-30"
applicable_versions: "Android 15+(system-triggered 触发器覆盖 Android 16 / version 36.1 / Android 17)"
sources:
  - type: official
    path: "https://developer.android.com/reference/androidx/core/os/Profiling"
  - type: official
    path: "https://developer.android.com/reference/androidx/core/os/ProfilingRequest"
  - type: official
    path: "https://developer.android.com/reference/androidx/core/os/BufferFillPolicy"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingManager"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingTrigger"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingResult"
  - type: official
    path: "packages/modules/Profiling/"
  - type: official
    path: "https://perfetto.dev/"
tags:
  - android
  - paper
  - profiling
related_chapters:
  - "8.8"
  - "13.1"
  - "15.5"
  - "9.1"
  - "8.2"
pipeline_stage: ready-to-publish
task6_state: revisiting
task6_result: pass-light-edit
task9_state: pending
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed-lite
pipeline_stage: task6_pending
last_task2b_lite_at: "2026-05-30T15:35:00+08:00"
task2b_result: fixed-lite
last_task2b_at: "2026-05-18T15:23:37+08:00"
reviewed_by: openclaw-task6
reviewed_date: "2026-04-22"
last_task9_at: "2026-05-18T15:25:00+08:00"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-18"
task9_review_notes: "2026-05-18 13:20 Task9 闲时抽检:needs-rework。P0 1 / P1 0;显式 requestProfiling 示例把 ProfilingResult 归到 AndroidX 包,官方签名实际为 android.os.ProfilingResult。;2026-05-18 15:25 Task9 deep-review: Task2B 已修正 ProfilingResult 包名口径;本轮 P0 0 / P1 0,queue 无 pending,自动晋升 finalized。"
last_task9_review_log: "logs/deep-review/2026-05-18-15-deep-review.md"
deepseek_polish_state: done
last_deepseek_polish_at: "2026-05-24"
---

# 14.7 ProfilingManager

ProfilingManager 解决的是量产设备上"问题发生时没有开工具"的空档。Android 15 起,应用可以主动请求 system trace、heap dump、heap profile、stack sampling;Android 16 及后续 extension/API 版本再把系统事件触发补齐。把显式请求、trigger 版本边界、结果回传拆开看,线上取证流程才不会写乱。

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 **显式请求入口**:显式请求走 `androidx.core.os.Profiling.requestProfiling(...)`,不是 `Tracing.requestProfiling()`
- 🔹 **四种采集类型**:`SystemTraceRequestBuilder`、`JavaHeapDumpRequestBuilder`、`HeapProfileRequestBuilder`、`StackSamplingRequestBuilder` 分别回答不同问题
- 🔹 **BufferFillPolicy 公开枚举**：只有 `DISCARD` 和 `RING_BUFFER`
- 🔹 **结果分发表**:`registerForAllProfilingResults()` 会收到当前 UID 的全部 profiling 结果;显式请求与 global listener 可以同时命中
- 🔹 **trigger 版本对照表**:API 36、version 36.1、API 37 的 trigger 分层要分开写
- 🔹 **失败结果处理**:`ProfilingResult` 的 rate limit、磁盘不足、post-processing 失败要单独归类

### 扩展(可选深入)

- 🔸 **归档流程**:request callback 负责就地关联 case,global listener 负责统一落盘、上传、清理
- 🔸 **交叉引用**:逐项 trigger 行为、停止条件、AOSP 路径放到 §8.8 展开,本节只保留选型和接入所需信息
<!-- outline-end -->

## 先按结果类型选工具

| AndroidX builder | 回答的问题 | 结果形态 | 主要参数 | 不适合 |
|---|---|---|---|---|
| `SystemTraceRequestBuilder` | 卡顿在哪条线程、启动慢在哪一段、ANR 前后发生了什么 | `.perfetto-trace` | `durationMs`、`bufferSizeKb`、`bufferFillPolicy` | 直接查对象引用链 |
| `JavaHeapDumpRequestBuilder` | 哪个对象组还活着、谁把堆顶满了 | `.hprof` | `tag` | 观察一段时间里的分配波动 |
| `HeapProfileRequestBuilder` | 内存为什么一直涨、哪类分配最密 | heap profile trace | `durationMs`、`samplingIntervalBytes`、`bufferSizeKb` | 直接确认 GC root |
| `StackSamplingRequestBuilder` | CPU 时间主要花在哪段调用栈 | stack samples trace | `durationMs`、`samplingFrequencyHz`、`bufferSizeKb` | 看完整系统时间线 |

这张表最好配合排障问题来用。线程时序问题先去 `System Trace`,对象关系问题直接 `Java Heap Dump`,还没确认是哪类分配在涨时先上 `Heap Profile`,想用较低成本拉长 CPU 观察窗口时再选 `Stack Sampling`。

## 显式请求的公共骨架

下面代码省略 import。构造请求的类(`Profiling`、`ProfilingRequest`、`SystemTraceRequestBuilder`、`BufferFillPolicy`)来自 `androidx.core.os`;结果类 `ProfilingResult` 来自平台包 `android.os`。正文只保留请求构造、提交和结果消费这三段。

```java
ProfilingRequest request = new SystemTraceRequestBuilder()
        .setBufferSizeKb(10_240)
        .setDurationMs(5_000)
        .setBufferFillPolicy(BufferFillPolicy.RING_BUFFER)
        .setTag("scroll-jank")
        .build();

Profiling.requestProfiling(context, request, executor, result -> {
    if (result.getErrorCode() == ProfilingResult.ERROR_NONE) {
        archiveResult(result.getTag(), result.getResultFilePath());
    }
});
```

这套接口把三件事拆开了。请求对象只描述采什么、采多久,平台负责执行、限流、落盘和脱敏,应用在 listener 里做归档。这样调用线程不会被一次长 trace 挂住,四种请求也能共用同一套结果处理。

四个 builder 的共同字段主要来自 `ProfilingRequestBuilder`:

- `setTag(...)`:把 case id、场景名、回归单号写进去,后续聚合比靠文件名稳
- `setCancellationSignal(...)`:更适合手动短 trace;heap dump 和较长 profile 通常让系统自然结束更稳

## BufferFillPolicy 只写两个公开枚举

`SystemTraceRequestBuilder` 里最容易写错的是 buffer 策略。AndroidX 公开文档只有两个枚举:

| 策略 | 缓冲区满了以后怎么做 | 更适合的场景 |
|---|---|---|
| `RING_BUFFER` | 覆盖旧事件,保留离结束点最近的一段数据 | 手动短 trace、ANR 前后取证、滑动卡顿 |
| `DISCARD` | 丢掉新事件,保留窗口开头那段数据 | 冷启动早期阶段、只想保住最早 tracepoint 的场景 |

写"保住窗口开头"时用 `DISCARD`，写"保住结束点附近现场"时用 `RING_BUFFER`，语义就能和真实枚举对上。

## 结果通道别按"显式请求"和"trigger"硬切开

平台文档把 listener 分成 request-specific listener 和 global listener 两层,但 global listener 不是只给 trigger 用。`registerForAllProfilingResults()` 会收到当前 UID 的全部 profiling 结果。只要应用同时注册了 global listener,一次显式请求也会额外命中它。

| 场景 | request-specific listener | global listener | `triggerType` | 归档建议 |
|---|---|---|---|---|
| `Profiling.requestProfiling(...)`,未注册 global listener | 会收到 | 收不到 | `TRIGGER_TYPE_NONE` | callback 里直接归档也能跑通 |
| `Profiling.requestProfiling(...)`,已注册 global listener | 会收到 | 也会收到同一结果 | `TRIGGER_TYPE_NONE` | callback 只做 case 状态更新,global listener 负责真正落库 |
| `addProfilingTriggers(...)` 注册的 system-triggered profiling | 收不到 | 会收到 | 具体 trigger 常量 | global listener 按 `triggerType` 分发到冷启动、ANR、OOM 各自流程 |

同时注册两层 listener 时,去重主键优先用 `resultFilePath`。失败结果没有文件时,再用 `triggerType + tag + errorCode + caseId` 兜底。这样显式请求和 trigger 结果可以走同一条归档流程,不会出现双写同一份 artifact 的情况。

## 结果文件的权限、隐私和合规

Profiling 结果按当前应用 UID 归属返回。`registerForAllProfilingResults(...)` 只接收当前 UID 的 profiling 结果,不能读取其他应用的结果;应用处理 `ProfilingResult.getResultFilePath()` 指向的文件时,也不需要 `READ_EXTERNAL_STORAGE` 这类外部存储权限。把它当成应用私有的诊断文件处理即可。

隐私风险主要来自结果内容,不来自读取权限。system trace 可能包含线程名、进程名、Surface 名、Binder 调用和业务 `tag`;heap dump / heap profile 可能暴露对象类型、字符串内容和内存分配路径;stack sampling 可能包含方法名与包名。平台会对跨应用信息做裁剪,但 App 自己的业务上下文仍然可能进入结果文件。上传前要按采集类型做过滤、压缩、加密、保留期限和用户授权校验。

归档流程里记录三类字段:`profilingType`、`triggerType`、`fileSizeBytes`。`tag` 不要写手机号、订单号、地理位置等可识别用户的信息,用内部 case id 或哈希值更稳。采集策略写进隐私条款和内部数据留存说明,避免线上追踪能力和合规说明不一致。

## System Triggered Profiling 的版本对照表

逐项 trigger 的 stop condition、产物细节和 AOSP 路径放在 §8.8《ProfilingManager 系统触发式性能追踪》展开,这里只保留接入时最容易写错的版本边界。

| 版本 | trigger | 返回物 | 适合场景 |
|---|---|---|---|
| API 36 | `TRIGGER_TYPE_APP_FULLY_DRAWN` | running system trace snapshot | 冷启动收尾阶段复盘 |
| API 36 | `TRIGGER_TYPE_ANR` | running system trace snapshot | 线上 ANR 取证 |
| version 36.1 | `TRIGGER_TYPE_APP_REQUEST_RUNNING_TRACE` | running system trace snapshot | 主动拉取当前正在运行的 background trace |
| version 36.1 | `TRIGGER_TYPE_KILL_FORCE_STOP` / `TRIGGER_TYPE_KILL_RECENTS` / `TRIGGER_TYPE_KILL_TASK_MANAGER` | running system trace snapshot | 用户手动结束进程后的现场 |
| API 37 | `TRIGGER_TYPE_COLD_START` | newly started system trace + stack sampling | 冷启动全窗口取证 |
| API 37 | `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` | running system trace snapshot | 因 `REASON_EXCESSIVE_RESOURCE_USAGE` 被杀的现场 |
| API 37 | `TRIGGER_TYPE_OOM` | Java heap dump | Java 层 OOM 根因定位 |
| API 37 | `TRIGGER_TYPE_ANOMALY` / `TRIGGER_TYPE_APP_COMPAT` | artifact 依异常类型而定 | 异常行为与兼容性问题采样 |

接入这张表时,API 36.1 那一组不要只靠 `SDK_INT` 判断。它们属于 Mainline / extension 版本扩展,和 API 36 不是同一层版本口径。

## 启动相关两种 trigger 不要混写

`TRIGGER_TYPE_APP_FULLY_DRAWN` 和 `TRIGGER_TYPE_COLD_START` 都指向冷启动,但采样窗口不同。

- `APP_FULLY_DRAWN` 在冷启动里调用 `Activity.reportFullyDrawn()` 之后返回一份 running trace snapshot,适合看启动尾段
- `COLD_START` 从冷启动尽早阶段开始录制,持续到 `reportFullyDrawn()`,没有调用时按默认约 5 秒截止;它还会附带 stack sampling,并使用 `DISCARD` 保住窗口开头

启动章节如果把这两个 trigger 写成同一件事,读者对采样起点、停止点和 artifact 都会判断失准。

## 三个更常用的用法

### 1. 交互卡顿

滑动掉帧、输入延迟、动画抖动,通常先手动发一次 3 到 5 秒的 `System Trace`。这类问题看的是结束点附近的线程时序,`RING_BUFFER` 比 `DISCARD` 更合适。回到 Perfetto 后,优先看主线程、`RenderThread`、`Frame Timeline`、Binder 和 `am` track。

### 2. 冷启动与 ANR 回炉

启动回归、偶发 ANR、用户主动结束进程这几类问题,更适合用 `registerForAllProfilingResults(...)` 建一条统一归档流程,再按版本注册 trigger。trigger 的具体行为、停止条件和 AOSP 服务端实现看 §8.8,本节只保留接入层需要的版本对照和结果分发规则。

### 3. 线上内存涨高

根因还不清时,先用 `Heap Profile` 找分配热点,再决定要不要补 `Java Heap Dump` 看引用链。API 37 设备可以再挂一个 `TRIGGER_TYPE_OOM` 兜底。这里说的是 Java 层 OOM,不是 LMK。应用如果自定义了 `UncaughtExceptionHandler`,也要继续调用默认 handler,不然 OOM trigger 不会生效。

## 失败结果要先分清是没采到,还是采了但丢了

| `ProfilingResult` 错误码 | 含义 | 应用侧处理 |
|---|---|---|
| `ERROR_FAILED_RATE_LIMIT_PROCESS` | 进程自己的预算已经用完 | 拉长手动请求间隔,trigger 注册把 `rateLimitingPeriodHours` 设到场景级别 |
| `ERROR_FAILED_RATE_LIMIT_SYSTEM` | 系统级预算没给本次样本 | 把它当"本次没拿到样本",不要在前台循环重试 |
| `ERROR_FAILED_NO_DISK_SPACE` | 结果文件无法落盘 | 建清理 worker,归档后及时删除旧结果 |
| `ERROR_FAILED_POST_PROCESSING` | 采集做了,但后处理失败,结果被丢弃 | 记录设备版本、采集类型、errorCode,排查是否集中在某个系统版本 |
| `ERROR_FAILED_PROFILING_IN_PROGRESS` | 已有 profiling 在跑 | 请求侧做串行化,避免多个长 profile 互相打架 |

失败日志最好是应用自己格式化出来的,不要只存一串整型错误码。下面是一条更适合排障和聚合的样例:

```text
W/ProfilingCaseRepo: result failed, case=scroll-jank-20260419-01, trigger=TRIGGER_TYPE_NONE, code=ERROR_FAILED_RATE_LIMIT_PROCESS, path=null
```

聚合面板按 `errorCode` 分组更稳,`errorMessage` 更适合留在原始日志里做单次排查。

`ERROR_FAILED_RATE_LIMIT_SYSTEM` 的预算不要写死成产品常量。Profiling 模块可通过 Mainline 和 `device_config` 调整阈值,不同版本、OEM 构建和调试配置可能不一致。实验室核验时可以用 `adb shell device_config list profiling` 查看当前设备的 profiling 参数;线上策略只按错误码退避、降采样和聚合统计,不依赖某个固定次数。

## 与其他工具的分工

| 工具 | 更适合的场景 | 局限 |
|---|---|---|
| ProfilingManager | 量产设备、线上回归、系统事件触发 | 受版本、extension、rate limit 约束 |
| Android Studio Profiler | 开发机上的交互式分析 | 很难覆盖真实用户现场 |
| adb / Perfetto CLI | 实验室里的压测、脚本化采集 | 线上设备接入成本高 |
| 第三方 APM SDK | 业务指标、崩溃路径、埋点体系 | 采样能力和隐私责任要自己兜住 |

## 上线前检查清单

- `tag` 直接带 case id、回归单号或场景名,别等结果回来后再猜它属于谁
- global listener 负责统一归档、上传、清理,request callback 负责本次请求的轻量状态更新
- 36.1 这组 trigger 要额外做 extension 版本判断,别把 API 36 和 36.1 混成一类
- 结果文件要有清理策略,避免长期堆在应用目录里
- 用户通知、隐私条款和内部合规说明要和真实采集行为一致

## 参考资料

1. **AndroidX Reference, `androidx.core.os.Profiling`**
   https://developer.android.com/reference/androidx/core/os/Profiling

2. **AndroidX Reference, `ProfilingRequest` / `BufferFillPolicy` / builders**
   https://developer.android.com/reference/androidx/core/os/ProfilingRequest

3. **Android SDK Reference, `android.os.ProfilingManager` / `ProfilingTrigger` / `ProfilingResult`**
   https://developer.android.com/reference/android/os/ProfilingManager

4. **AOSP Profiling Module**
   `packages/modules/Profiling/`

5. **Perfetto Documentation**
   https://perfetto.dev/

## 相关章节

- **8.8 ProfilingManager 系统触发式性能追踪**,trigger 的 stop condition、artifact 差异和 AOSP 路径
- **13.1 Perfetto 简介与演进**,trace 文件格式和基础分析概念
- **15.5 线上性能监控**,线上采样预算、上传流程和告警治理
- **9.1 ANR 设计思想**,ANR 样本和 system-triggered profiling 的配合方式
- **8.2 应用启动过程**,冷启动 trace 的关键节点
