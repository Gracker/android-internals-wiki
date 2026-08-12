---
title: "各 Android 版本性能变更追踪"
chapter: "16.2"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: 2026-07-30
last_verified_against: AOSP android-17.0.0_r1 / Android 12-17 behavior changes / Android 17 API 37 reference / android17-6.18-2026-06_r6
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/about/versions/12/behavior-changes-12"
  - type: official
    path: "https://developer.android.com/about/versions/12/behavior-changes-all"
  - type: official
    path: "https://developer.android.com/about/versions/13/features"
  - type: official
    path: "https://developer.android.com/about/versions/14/behavior-changes-all"
  - type: official
    path: "https://developer.android.com/about/versions/14/behavior-changes-14"
  - type: official
    path: "https://developer.android.com/about/versions/15/behavior-changes-15"
  - type: official
    path: "https://developer.android.com/about/versions/16/features"
  - type: official
    path: "https://developer.android.com/about/versions/16/behavior-changes-16"
  - type: official
    path: "https://developer.android.com/about/versions/17/release-notes"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-all"
  - type: official
    path: "https://developer.android.com/about/versions/17/changes/messagequeue"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingManager"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingTrigger"
  - type: official
    path: "https://developer.android.com/reference/android/os/PerformanceHintManager.Session"
  - type: official
    path: "https://source.android.com/docs/core/architecture/16kb-page-size/16kb"
  - type: official
    path: "https://source.android.com/docs/core/interaction/neural-networks"
  - type: source
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc"
  - type: source
    path: "https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingManager.java"
tags: ['version-changes', 'behavior-changes', 'api-evolution', 'migration', 'performance-api']
related_chapters: ["1.6", "2.9", "4.6", "5.7", "6.4", "9.2", "13.1", "14.11"]
task6_state: reviewed
section: "16.2"
status: finalized
task9_state: reviewed
task2b_state: fixed
pipeline_stage: ready-to-publish
---

# 各 Android 版本性能变更追踪

## 为什么版本号必须进入性能结论

同一个 APK 在两个系统版本上可能走入不同的调度、进程管理和运行时路径。`targetSdkVersion` 又会单独开启一部分兼容性变更。因此，“Android 17 上发生”还不足以描述问题；性能记录至少要包含设备系统版本、`targetSdkVersion`、主线模块版本和内核版本。

平台上限为 Android 17 / API 37 / `android-17.0.0_r1`。Android 17 对应的新 GKI 分支是 6.18，内核核验锚点为 `android17-6.18-2026-06_r6`。Android 17 设备仍可能采用平台支持期内的较早内核分支，看到 Android 17 不能反推设备必然运行 6.18。

下面的“适用范围”分为两类：

- **所有 App**：只要运行在该系统版本上就受影响，通常与 `targetSdkVersion` 无关。
- **目标版本变更**：只有 App 将 `targetSdkVersion` 提升到对应 API 后才启用。

| 版本 | 性能排查时优先关注 | 适用范围 |
| --- | --- | --- |
| Android 12 / API 31 | 后台前台服务、精确闹钟、通知跳板 | 多数为 target 31 |
| Android 13 / API 33 | 通知权限、文本断字、FrameTimeline | 权限受 target 影响，渲染 API 为能力项 |
| Android 14 / API 34 | 缓存进程资源、前台服务类型、JobScheduler ANR | 同时包含所有 App 与 target 34 |
| Android 15 / API 35 | ProfilingManager、启动信息、ADPF 会话扩展、16 KB 页 | API 能力与 target 35 行为并存 |
| Android 16 / API 36 | 触发式 Profiling、作业诊断、CPU/GPU headroom、大屏适配 | API 能力与 target 36 行为并存 |
| Android 17 / API 37 | 无锁 MessageQueue、分代 CMC、新 ProfilingTrigger、App 内存限制 | 同时包含所有 App 与 target 37 |

## Android 12（API 31）：后台执行边界收窄

### 后台启动前台服务

运行在 Android 12 及以上且 target 31 的 App，从后台启动前台服务时会受到限制。未命中官方豁免条件时，`startForegroundService()` 会抛出 `ForegroundServiceStartNotAllowedException`。这会改变后台采集、上传和周期维护任务的可达性，不能简单解释成任务“变慢”。

迁移方案要按任务语义选择：

- 可延迟、受约束的持久工作交给 WorkManager。
- 必须尽快执行且符合配额条件的短任务可以评估 expedited work。
- 用户明确发起的大文件传输应评估相应系统版本提供的用户发起数据传输机制。
- 需要持续感知的设备类场景还要评估 Companion Device Manager 等专用 API。

WorkManager 不能替代所有前台服务；持续导航、媒体播放、通话等用户可感知工作仍有各自的前台服务类型和运行条件。

### 精确闹钟

target 31 的 App 使用精确闹钟时，需要声明 `SCHEDULE_EXACT_ALARM` 并检查特殊应用访问状态。周期遥测通常允许时间窗口，优先采用非精确闹钟或 WorkManager。只有业务语义要求精确触发时，才接受权限、配额和省电策略带来的成本。

Android 14 又调整了新安装 App 的默认授权状态。排查闹钟延迟时，要同时记录安装来源、授权状态和目标版本。

### 通知跳板

target 31 的 App 不能通过通知启动 BroadcastReceiver 或 Service，再由中间组件启动 Activity。通知点击应直接使用指向 Activity 的 `PendingIntent`。迁移后，冷启动链路会少一个中间组件；收益大小取决于原有实现，不能预设固定时延。

### Stretch Overscroll 与性能提示

Android 12 为所有 App 引入 stretch overscroll。自定义滚动容器若自行处理边缘效果，需要检查重复拉伸、额外绘制和触摸反馈一致性。

`PerformanceHintManager` 也在 API 31 提供公开入口，应用可用线程组、目标工作时长和实际工作时长向系统表达持续负载。它属于 ADPF 的 CPU 性能提示路径，与 Game Mode 是两套 API。Game Mode 描述游戏运行偏好，不能代替每帧工作时长反馈。

## Android 13（API 33）：权限与帧标识能力扩展

### 运行时通知权限

Android 13 引入 `POST_NOTIFICATIONS` 运行时权限。通知是前台服务可见性和后台任务反馈的一部分，拒绝权限不等于前台服务可以省略通知义务。性能测试需要覆盖首次授权、拒绝、升级安装和重新授权，避免把通知流程差异计入启动或任务耗时。

### ART Mainline 更新

Android 13 继续强化 ART 的 Mainline 更新路径。运行时实现可以随 Google Play 系统更新变化，设备的 Android 大版本相同也不保证 ART 构建完全相同。比较启动、编译或 GC 时，应记录 ART 模块版本，并避免将一次设备观测写成全平台结论。

### 文本断字与 FrameTimeline

Android 13 优化了断字实现，官方文档给出的上限描述是“最多约 200%”。开发者可按排版需求选择 `fullFast` 或 `normalFast`。该百分比来自平台说明，不代表任意文本、字体和语言都能复现；正文排版性能仍要用目标语料测量。

Choreographer 和 NDK `ASurfaceControl` 在 Android 13 获得 FrameTimeline 相关能力。一个应用帧可能对应多个 timeline，Vsync ID 可以把 App 侧帧工作与 SurfaceFlinger、显示流水线中的同一帧关联起来。排查卡顿时，应以帧标识对齐各阶段，少用时间戳邻近关系猜测归属。

## Android 14（API 34）：缓存进程和前台服务约束

### 缓存进程的资源限制

Android 14 对所有 App 加强缓存进程管理。进程进入 cached 状态后，系统会在较短时间内限制其后台工作；动态注册的广播也可能在进程离开 cached 状态后再投递。缓存进程中的线程、网络循环或定时器不应被设计成可靠执行机制。

cached、frozen 和 killed 是三种不同状态。线程暂时没有获得 CPU 时间，不能单独证明进程已经冻结；要结合 ActivityManager 状态、freezer 相关系统信息和进程存活证据判断。

### 前台服务类型

target 34 的 App 必须为前台服务声明符合用途的类型及对应权限。漏掉类型会在 `startForeground()` 时触发 `MissingForegroundServiceTypeException`，不满足运行时前置条件则可能触发 `SecurityException`。

Android 14 新增 `shortService` 等类型。`shortService` 的运行窗口约为 3 分钟，超时后系统调用 `Service.onTimeout()`，服务未及时停止会触发 ANR。它适合短而不可延后的用户可感知工作，不适合无限续期的后台循环。

### JobScheduler 回调超时

target 34 的 App 若在 `JobService.onStartJob()` 或 `onStopJob()` 中阻塞主线程，系统会以 ANR 处理。Android 14 对所有 App 还会把多次 JobScheduler ANR 计入受限 standby bucket 的判断。回调应快速返回，耗时工作转移到合适的执行器，并正确处理停止信号。

### 非线性字体缩放

Android 14 将字体最大缩放提高到 200%，并采用非线性缩放。大字号文本增长更明显，已经较大的文本增长较缓。性能测试应同时检查布局重排、文本测量次数、截断和滚动范围，不能把缩放后的布局抖动归因于绘制器本身。

## Android 15（API 35）：进程内 Profiling 与 16 KB 页支持

### ProfilingManager

`ProfilingManager` 在 API 35 加入公开 SDK。App 可以通过 `requestProfiling()` 请求 Java heap dump、heap profile、stack sampling 或 system trace，并通过监听器接收结果。仅注册监听器不会开始采集；调用方还必须显式调用 `requestProfiling()`，否则会一直等待一个从未发起的结果。

它适合在用户同意和产品采样策略允许的场景中取得现场数据。系统仍会执行速率限制，并可能拒绝请求。调用方应把“请求成功提交”“收到结果”“超时或失败”记录为不同状态。

### ApplicationStartInfo

`ApplicationStartInfo` 在 API 35 提供进程启动原因、启动类型、时间点和启动状态等结构化信息。它能减少只靠日志拼接启动阶段的歧义。时间点是否存在与启动路径有关，读取方必须检查返回数据，不能假设每个阶段都有值。

### ADPF 会话扩展

API 35 为 `PerformanceHintManager.Session` 增加 `setPreferPowerEfficiency()` 和基于 `WorkDuration` 的 `reportActualWorkDuration()`。前者表达功耗优先偏好，后者可以报告更丰富的工作时长信息。二者都是提示，设备是否支持、系统如何响应、频点如何变化由实现和当前热状态决定。

### 前台服务时间配额

target 35 的 App 在后台运行 `dataSync` 和 `mediaProcessing` 前台服务时，每种类型共享 24 小时内 6 小时的总配额。用户把 App 带到前台会重置计时器。配额耗尽后，系统调用 `Service.onTimeout(int, int)`；服务只有很短的停止窗口。

这里的 6 小时按同一类型的全部服务累计，不能按每个 Service 实例分别计算。迁移时需要盘点并发服务、重启路径和用户回到前台的状态转换。

### 16 KB 页面大小

Android 15 开始支持 16 KB 页大小的 arm64 设备。它在 Android 15 并未成为所有设备默认配置。含原生代码的 APK 需要检查 ELF 段对齐、打包对齐、预编译依赖和运行期页大小假设。

页大小变化会影响页表、缺页、映射粒度和小对象驻留开销，方向取决于工作负载。只看到系统版本无法判断设备页大小，应用应通过运行期 API 或系统信息识别，并在 4 KB 与 16 KB 环境分别测量。

## Android 16（API 36）：触发式 Profiling 与诊断 API

### 触发式 Profiling

`ProfilingManager.addProfilingTriggers()` 在 API 36 加入。App 可以注册由系统事件触发的采集规则，API 36 的公开触发类型包括 ANR 和 `APP_FULLY_DRAWN`。36.1 又增加运行中 trace 请求、强制停止、最近任务划掉和任务管理器停止等触发类型。

触发式采集仍受系统速率限制和设备条件约束。它适合补充低复现率现场问题，不能保证每次事件都生成产物。

### 启动、帧与作业诊断

`ApplicationStartInfo.getStartComponent()` 在 API 36 加入，用于标识触发启动的组件类型。启动性能数据可以按 Activity、Service、BroadcastReceiver、ContentProvider 等入口分组，避免把不同启动原因混在同一分位数中。

`FrameMetrics.FRAME_TIMELINE_VSYNC_ID` 也在 API 36 提供。它返回当前帧 timeline 的 Vsync ID，可用于关联 HWUI、SurfaceFlinger 和 Perfetto 中的帧记录。设备或窗口条件不支持时，分析工具应保留缺失值。

`JobScheduler.getPendingJobReasons()` 返回一个作业当前可能存在的多个等待原因，`getPendingJobReasonsHistory()` 返回近期约束变化。后台任务“没运行”时，先读取约束历史，再检查配额、网络、电量和待机状态，比仅看一次当前状态更可靠。

### SystemHealthManager headroom

Android 16 在 `SystemHealthManager` 提供 CPU 和 GPU headroom API。支持该能力的设备可以按时间窗口查询资源余量估计。返回值适合驱动画质、工作量或并发度的渐进调整，不能视作固定频率预算，也不能绕开 Thermal API。

调用方需要遵守最小查询间隔，处理设备不支持和无可用样本，并对信号做平滑。按单次读数立刻切换重负载档位，容易形成振荡。

### 大屏自适应

target 36 的 App 在最小宽度 600dp 及以上设备上，系统会忽略一部分方向、宽高比和可调整性限制。迁移重点包括窗口尺寸变化、配置变化、状态恢复和多窗口布局。尺寸变化是否重建 Activity 取决于清单和配置处理，不能写成每次 resize 都必然重建。

target 36 还可以用 `PROPERTY_COMPAT_ALLOW_RESTRICTED_RESIZABILITY` 暂时退出该行为。target 37 会忽略这项临时退出配置，所以 Android 16 的迁移不能停留在兼容模式。

### 预测性返回、定期任务与 edge-to-edge

target 36 的 App 运行在 Android 16 及以上时，系统默认启用 back-to-home、cross-task 和 cross-activity 的预测性返回动画。旧的 `onBackPressed()` 不再收到调用，`KEYCODE_BACK` 也不再分发。AndroidX 返回分发器、平台返回回调和页面状态恢复都要一并测试；清单里的 `android:enableOnBackInvokedCallback="false"` 只适合作为临时退出手段。

`ScheduledThreadPoolExecutor.scheduleAtFixedRate()` 也有 target 36 行为变化。进程离开有效生命周期而错过多个周期后，恢复时最多立即执行一个遗漏任务。依赖“恢复后补跑全部周期”的统计或维护逻辑需要改成显式计算缺口。

Android 16 在本系统上禁用 target 36 App 的 `windowOptOutEdgeToEdgeEnforcement`。页面应正确消费 system bar、display cutout 和 IME insets。布局区域变化会影响测量、绘制和滚动范围，基准测试必须使用迁移后的最终布局。

## Android 17（API 37）：消息队列、GC 与现场诊断

### target 37 的无锁 MessageQueue

运行在 Android 17 且 target 37 的 App 使用新的无锁 `MessageQueue` 实现。官方目标是减少锁竞争和漏帧。公开 API 语义保持兼容，依赖私有字段或方法反射的代码会暴露问题。

兼容层仍保留 `mMessages` 字段，但新实现下该字段始终为 `null`，它不能反映队列是否为空。测试依赖需要升级：

- Espresso 使用 3.7.0 或以上版本。
- Robolectric 使用 4.17 或以上版本，并从 `@LooperMode(LEGACY)` 迁移到 `@LooperMode(PAUSED)`。
- 自研空闲判断改用公开同步机制或 Android 16 引入的 `TestLooperManager` 能力。

可在 debuggable 构建上用兼容性开关提前测试 `USE_NEW_MESSAGEQUEUE`。测试范围要覆盖 Handler 密集场景、IdleHandler、同步屏障、测试框架空闲判断和依赖反射的 SDK。

Android 17 对 target 37 App 还禁止通过反射或 JNI 修改 `static final` 字段。性能测试框架若依赖这种方式替换时钟、常量或单例，需要同步清理。

### ART 分代 Concurrent Mark-Compact

Android 17 的 ART Concurrent Mark-Compact 支持分代 GC。年轻代对象通常存活时间短，平台可以用更频繁、成本较低的 young collection 处理这部分对象，再按条件执行更大范围回收。

这项变化不能和 userfaultfd 混为同一开关。Concurrent Mark-Compact 使用 userfaultfd 的演进早于 Android 17；Android 17 新增的是分代策略。分析时应区分 young/full collection、暂停阶段、并发标记时间、晋升量和回收后驻留集。

分代回收也不保证每个 App 都降低暂停时间。对象存活率高、跨代引用多或堆压力大时，收益会变化。结论需要来自目标设备、目标 ART 构建和稳定负载。

### API 37 的 ProfilingTrigger

Android 17 扩充系统触发式 Profiling：

| 触发类型 | 系统事件 | 产物或行为 |
| --- | --- | --- |
| `TRIGGER_TYPE_OOM` | App 抛出 OOM | Java heap dump |
| `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` | 因 CPU 过度使用被终止 | 运行中 system trace 的快照 |
| `TRIGGER_TYPE_COLD_START` | `START_TYPE_COLD` 冷启动 | 新 system trace 与 stack sampling |
| `TRIGGER_TYPE_ANOMALY` | 平台识别的异常事件 | 产物由异常类型决定 |
| `TRIGGER_TYPE_APP_COMPAT` | 兼容性事件 | 对应触发结果 |

冷启动采集持续到 App 调用 `Activity.reportFullyDrawn()`，默认上限为 5 秒，并使用 discard buffer 保留较早事件。未调用 `reportFullyDrawn()` 会失去业务就绪边界，只能依赖超时停止。

OOM 触发要求自定义 `Thread.UncaughtExceptionHandler` 调用默认异常处理器。若异常链被截断，系统触发无法完成，App 只能另行调用 `requestProfiling()` 请求 heap dump。

### App 内存限制

Android 17 对所有 App 引入保守的 App 内存限制，但只在部分设备上实施。命中限制后，`ApplicationExitInfo` 的 reason 为 `REASON_OTHER`，description 包含 `MemoryLimiter:AnonSwap`。只按 reason 聚合会把它和其他 `REASON_OTHER` 混在一起。

平台提供 `am memory-limiter status`、`manual` 和 `ignore` 子命令用于受支持设备上的测试。线上诊断可以结合 `TRIGGER_TYPE_ANOMALY` 获取命中内存限制时的 heap dump，但仍要考虑采样和速率限制。

### Android 17 的 NPU 与 NNAPI 边界

Android 17 要求 target 37 的 App 在直接访问 NPU 时声明 `FEATURE_NEURAL_PROCESSING_UNIT`。这属于设备能力声明与访问边界，不能据此推导某个模型会自动提速。

NNAPI NDK 从 Android 15 起已废弃，NN HAL 仍供系统和设备实现使用。NN HAL 1.3 也早于 Android 17。`android-17.0.0_r1` 中继续存在相关代码，只能证明兼容实现仍在源码树内，不能把旧接口写成 Android 17 新增能力。

对端侧推理做版本比较时，至少固定模型、delegate/runtime、驱动、量化方案、热状态和功耗窗口。编译缓存是否命中、burst execution 是否可用都要从目标实现和 trace 证据判断，不应填写通用微秒级收益。

## 新增性能 API 的演进脉络

| API | 加入版本 | 用途 | 使用边界 |
| --- | --- | --- | --- |
| `PerformanceHintManager` | API 31 | 线程组工作时长提示 | 提示不等于频点命令 |
| FrameTimeline / Vsync ID 能力 | API 33 起扩展 | 跨渲染阶段关联帧 | 以设备和具体 API 可用性为准 |
| `ProfilingManager.requestProfiling()` | API 35 | App 主动请求 profile | 有速率限制，注册监听器不会发起采集 |
| `ApplicationStartInfo` | API 35 | 结构化启动信息 | 时间点和字段可能缺失 |
| `Session.setPreferPowerEfficiency()` | API 35 | 表达功耗优先偏好 | 由系统决定响应 |
| `ProfilingManager.addProfilingTriggers()` | API 36 | 注册系统事件采集 | 触发类型跨 36、36.1、37 扩展 |
| `FRAME_TIMELINE_VSYNC_ID` | API 36 | 关联窗口帧与系统帧 | 缺失时保留 unknown |
| CPU/GPU headroom | API 36 | 估计资源余量 | 设备可选，限制查询频率 |
| Android 17 新 ProfilingTrigger | API 37 | 冷启动、OOM、异常 CPU 等现场数据 | 受事件条件和速率限制 |

API 级别检查只解决符号可用性。设备能力、服务是否存在、权限、配额和厂商实现仍要单独探测。

## Deprecated API 与替代路径

### 返回手势

`Activity.onBackPressed()` 从 API 33 起废弃，时间点早于 Android 16。应用层优先使用 AndroidX `OnBackPressedDispatcher` 管理回调和生命周期；平台侧可按需求接入 `OnBackInvokedDispatcher`。预测性返回还要求界面状态在手势进行过程中可预览，单纯替换方法名不能完成迁移。

### WebView 强制深色

Android 13 起，`WebSettings.setForceDark()` 对 target 33 App 的行为变化，并进入废弃路径。网页内容应通过 `prefers-color-scheme` 和 WebView 的算法深色策略配合。切换主题时要测量页面重排与重绘，避免在滚动中反复改动设置。

### NNAPI NDK

NNAPI NDK 从 Android 15 起废弃。新推理方案应评估目标运行时及其 delegate，并把模型兼容性、驱动覆盖和回退路径纳入测试。HAL 继续存在不代表 App 应继续新增对废弃 NDK API 的依赖。

### edge-to-edge 与 elegant text

`windowOptOutEdgeToEdgeEnforcement` 在 target 36 且运行 Android 16 时已经失效，替代路径是完整处理窗口 insets。`elegantTextHeight` 也在 target 36 时被忽略；受影响文字系统需要重新验证字形高度、基线、行距和裁切。

废弃标记不等于 API 会立刻消失。迁移顺序应由目标版本行为、调用频率、故障风险和替代方案成熟度共同决定。

## targetSdkVersion 升级检查表

### target 31

- 枚举所有后台启动前台服务的入口及豁免条件。
- 检查精确闹钟授权和非精确调度的容忍窗口。
- 删除通知跳板。

### target 33

- 覆盖通知授权的完整状态转换。
- 清理对 `onBackPressed()` 和旧深色策略的新增依赖。
- 记录 ART 主线模块版本，避免只按 OS 大版本聚合。

### target 34

- 为每个前台服务声明精确类型、权限和运行时前置条件。
- 保证 JobService 回调快速返回。
- 在 cached 状态验证后台工作不会依赖进程持续获得 CPU。

### target 35

- 统计 `dataSync`、`mediaProcessing` 的 24 小时累计用量。
- 实现并测试超时停止路径。
- 在 4 KB 与 16 KB 页设备验证所有原生依赖。

### target 36

- 在 600dp 及以上窗口测试 resize、旋转、多窗口和状态恢复。
- 迁移预测性返回，覆盖 back-to-home、跨任务和跨 Activity。
- 删除对 edge-to-edge 退出属性和 `elegantTextHeight` 的依赖。
- 检查 fixed-rate 定期任务是否依赖恢复后连续补跑。
- 使用新的作业等待原因历史定位后台任务。
- 把 headroom 作为可选信号，保留 Thermal API 和静态档位回退。

### target 37

- 提前启用 `USE_NEW_MESSAGEQUEUE` 兼容性变更，升级测试依赖。
- 搜索对 `MessageQueue` 私有成员和 `static final` 修改的反射/JNI 代码。
- 测试冷启动、OOM、异常 CPU 与内存限制的采集和退出信息解析。
- 直接访问 NPU 的 App 声明对应硬件 feature，并处理设备不支持。

每次升级都应分开比较“系统版本变化”和“target 变化”。可在同一 Android 17 设备上用兼容性框架逐项开关行为，再用两个 target 构建复测，减少变量混杂。

## Perfetto 与平台数据如何配合

版本变化在 Perfetto 中的可见程度不同：

- 无锁 MessageQueue 的效果要从主线程调度、Handler 工作和帧 deadline 观察，trace 中没有一个可替代兼容性检查的“无锁已启用”结论。
- FrameTimeline Vsync ID 可以关联应用帧、HWUI 和 SurfaceFlinger。
- GC 需要区分 young/full collection 及暂停、并发阶段；只有总 GC 次数很难解释分代策略。
- CPU/GPU headroom 是 App 可查询信号，频率、调度和热事件仍需系统 trace 辅助。
- ProfilingManager 生成独立的 profile 产物，不能假设它自动出现在当前 Perfetto 会话中。
- 前台服务配额、权限拒绝和 JobScheduler 等待原因需要结合 dumpsys、API 返回和系统日志，trace 只覆盖其中一部分。

一次可复核的跨版本实验，应固定 APK、数据集、操作序列、设备温度和电源条件，并记录 OS build fingerprint、target、ART/Mainline 模块、页大小、内核版本。Android 17 的内核字段若为 6.18，还要记录精确 tag；这里的核验锚点是 `android17-6.18-2026-06_r6`。

## 常见误区

### “只升级 compileSdk，不改 target，不会影响性能”

compileSdk 只决定编译时可见 API。运行在新系统上的所有 App 变更仍会生效，例如 Android 14 的 cached 进程资源管理和 Android 17 部分设备的内存限制。

### “升 target 后的回归都是平台优化失败”

target 会启用一组兼容性行为。任务不再执行、服务启动异常或测试框架无法判断主线程空闲，可能来自行为边界变化。应按兼容性开关逐项定位。

### “新性能 API 在低版本不能调用，所以没有集成价值”

可以用 API 级别、能力探测和回退实现渐进接入。价值取决于新数据是否改善诊断或控制决策，不取决于覆盖全部历史设备。

### “NN HAL 代码仍在 AOSP，说明 NNAPI 是 Android 17 新加速点”

源码存在表示平台仍维护兼容路径。NNAPI NDK 已在 Android 15 废弃，NN HAL 版本也有独立历史。性能收益必须回到当前 runtime、delegate、驱动和模型测量。

### “Android 17 的分代 GC 等于打开 userfaultfd”

userfaultfd 是 Concurrent Mark-Compact 的一条实现路径，分代是对象代际和回收范围策略。两者处在不同维度。

## 参考资料

### Android Developers

- [Android 12：目标版本行为变化](https://developer.android.com/about/versions/12/behavior-changes-12)
- [Android 12：所有 App 行为变化](https://developer.android.com/about/versions/12/behavior-changes-all)
- [Android 13：功能与 API](https://developer.android.com/about/versions/13/features)
- [Android 14：所有 App 行为变化](https://developer.android.com/about/versions/14/behavior-changes-all)
- [Android 14：目标版本行为变化](https://developer.android.com/about/versions/14/behavior-changes-14)
- [Android 14：前台服务类型](https://developer.android.com/about/versions/14/changes/fgs-types-required)
- [Android 15：目标版本行为变化](https://developer.android.com/about/versions/15/behavior-changes-15)
- [Android 16：功能与 API](https://developer.android.com/about/versions/16/features)
- [Android 16：目标版本行为变化](https://developer.android.com/about/versions/16/behavior-changes-16)
- [Android 17 Release Notes](https://developer.android.com/about/versions/17/release-notes)
- [Android 17：目标版本行为变化](https://developer.android.com/about/versions/17/behavior-changes-17)
- [Android 17：所有 App 行为变化](https://developer.android.com/about/versions/17/behavior-changes-all)
- [Android 17 MessageQueue 迁移指南](https://developer.android.com/about/versions/17/changes/messagequeue)
- [ProfilingManager API](https://developer.android.com/reference/android/os/ProfilingManager)
- [ProfilingTrigger API](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [ApplicationStartInfo API](https://developer.android.com/reference/android/app/ApplicationStartInfo)
- [FrameMetrics API](https://developer.android.com/reference/android/view/FrameMetrics)
- [PerformanceHintManager.Session API](https://developer.android.com/reference/android/os/PerformanceHintManager.Session)

### AOSP 与平台文档

- [`android-17.0.0_r1` ProfilingManager.java](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingManager.java)
- [`android-17.0.0_r1` ART Mark-Compact](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc)
- [16 KB page size](https://source.android.com/docs/core/architecture/16kb-page-size/16kb)
- [NNAPI 驱动与废弃状态](https://source.android.com/docs/core/interaction/neural-networks)
- [Android common kernels](https://source.android.com/docs/core/architecture/kernel/android-common)
- [android17-6.18 release builds](https://source.android.com/docs/core/architecture/kernel/gki-android17-6_18-release-builds)
