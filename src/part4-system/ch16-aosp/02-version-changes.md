---
title: "各 Android 版本性能变更追踪"
chapter: "16.2"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: 2026-08-14
last_verified_against: AOSP android-17.0.0_r1 / current Android 12-17 behavior changes and API references / Android common-kernel compatibility matrix / android17-6.18-2026-06_r6
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

同一个 APK 在两个系统版本上可能走入不同的调度、进程管理和运行时路径。`targetSdkVersion` 表示 App 声明适配到的 API 级别，又会单独开启一部分兼容性变更。因此，“Android 17 上发生”还不足以描述问题；性能记录至少要包含设备系统版本、`targetSdkVersion`、Mainline（可独立更新的系统模块）版本和内核版本。

平台上限为 Android 17 / API 37 / `android-17.0.0_r1`。Android 17 对应的新 GKI（Generic Kernel Image，通用内核镜像）分支是 6.18，内核核验锚点为 `android17-6.18-2026-06_r6`。官方兼容矩阵还列出多条较早内核分支；其中 `android13-5.10` 与 `android12-5.10` 从 Android 17 QPR1（Quarterly Platform Release 1，该 Android 版本的第 1 次季度平台更新）起不再受支持。看到 Android 17 不能反推设备必然运行 6.18，仍要读取实际内核版本。

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

expedited work 是 WorkManager 中希望尽快执行、但会消耗系统配额的加急任务。WorkManager 不能替代所有 foreground service（前台服务，运行时以持续通知表明正在执行用户可感知工作）；持续导航、媒体播放、通话等场景仍有各自的前台服务类型和运行条件。

### 精确闹钟

target 31 的 App 使用精确闹钟时，需要声明 `SCHEDULE_EXACT_ALARM` 并检查特殊应用访问状态。周期遥测通常允许时间窗口，优先采用非精确闹钟或 WorkManager。只有业务语义要求精确触发时，才接受权限、配额和省电策略带来的成本。

Android 14 又调整了新安装 App 的默认授权状态。排查闹钟延迟时，要同时记录安装来源、授权状态和目标版本。

### 通知跳板

target 31 的 App 不能通过通知启动 BroadcastReceiver（广播接收器）或 Service（无界面组件），再由中间组件启动 Activity（界面组件）。通知点击应直接使用指向 Activity 的 `PendingIntent`，也就是交给系统稍后代表 App 执行的封装操作。迁移后，冷启动链路会少一个中间组件；收益大小取决于原有实现，不能预设固定时延。

### Stretch Overscroll 与性能提示

Android 12 为所有 App 引入 stretch overscroll（滚动到边界后拉伸内容的过度滚动效果）。自定义滚动容器若自行处理边缘效果，需要检查重复拉伸、额外绘制和触摸反馈一致性。

`PerformanceHintManager` 也在 API 31 提供公开入口，App 可用线程组、目标工作时长和实际工作时长向系统表达持续负载。它属于 ADPF（Android Dynamic Performance Framework，应用与系统协同调整性能）的 CPU 性能提示路径，与 Game Mode 是两套 API。Game Mode 描述游戏偏好的性能或省电模式，不能代替每帧工作时长反馈。

## Android 13（API 33）：权限与帧标识能力扩展

### 运行时通知权限

Android 13 引入 `POST_NOTIFICATIONS` 运行时权限。通知是前台服务可见性和后台任务反馈的一部分，拒绝权限不等于前台服务可以省略通知义务。性能测试需要覆盖首次授权、拒绝、升级安装和重新授权，避免把通知流程差异计入启动或任务耗时。

### ART Mainline 更新

ART（Android Runtime，Android 运行时）可作为 Mainline 模块通过 Google Play 系统更新变化；设备的 Android 大版本相同，也不保证 ART 构建完全相同。比较启动、编译或 GC（Garbage Collection，对象垃圾回收）时，应记录 ART 模块版本，不能把一次设备观测写成全平台结论。

### 文本断字与 FrameTimeline

Android 13 优化了断字实现，官方文档给出的上限描述是“最多约 200%”。开发者可按排版质量与成本选择 `fullFast` 或 `normalFast` 两种快速断字频率。该百分比来自平台说明，不代表任意文本、字体和语言都能复现；正文排版性能仍要用目标语料测量。

Choreographer（协调 UI 帧回调的系统类）和 NDK（Native Development Kit，原生开发工具包）`ASurfaceControl` 在 Android 13 获得 FrameTimeline（描述一帧预期与实际显示时序）相关能力。一个应用帧可能对应多个 timeline；Vsync ID 是垂直同步周期的标识，可把 App 侧帧工作与 SurfaceFlinger（系统显示合成服务）、显示流水线中的同一帧关联起来。排查卡顿时，应以帧标识对齐各阶段，少用时间戳邻近关系猜测对应关系。

## Android 14（API 34）：缓存进程和前台服务约束

### 缓存进程的资源限制

Android 14 对所有 App 加强缓存进程管理。进程进入 cached 状态后，系统会在较短时间内限制其后台工作；动态注册的广播也可能在进程离开 cached 状态后再投递。缓存进程中的线程、网络循环或定时器不应被设计成可靠执行机制。

cached 表示进程当前没有活跃组件、可在内存压力下被终止；frozen 表示系统暂停其线程执行；killed 则表示进程已经结束。线程暂时没有获得 CPU 时间，不能单独证明进程已经 frozen；要结合 ActivityManager 状态、freezer（系统冻结进程的机制）信息和进程存活证据判断。

### 前台服务类型

target 34 的 App 必须为前台服务声明符合用途的类型及对应权限。漏掉类型会在 `startForeground()` 时触发 `MissingForegroundServiceTypeException`，不满足运行时前置条件则可能触发 `SecurityException`。

Android 14 新增 `shortService` 等类型。`shortService` 的运行窗口约为 3 分钟，超时后系统调用 `Service.onTimeout()`，服务未及时停止会触发 ANR。它适合短而不可延后的用户可感知工作，不适合无限续期的后台循环。

### JobScheduler 回调超时

target 34 的 App 若在 `JobService.onStartJob()` 或 `onStopJob()` 中阻塞主线程，系统会以 ANR（Application Not Responding，应用无响应）处理。Android 14 对所有 App 还会把多次 JobScheduler ANR 计入 restricted standby bucket（严格限制后台作业、闹钟和网络的待机分组）的判断。回调应快速返回，耗时工作转移到合适的执行器，并正确处理停止信号。

### 非线性字体缩放

Android 14 将字体最大缩放提高到 200%，并采用非线性缩放。大字号文本增长更明显，已经较大的文本增长较缓。性能测试应同时检查布局重排、文本测量次数、截断和滚动范围，不能看到缩放后的布局抖动就直接判定绘制器有问题。

## Android 15（API 35）：进程内 Profiling 与 16 KB 页支持

### ProfilingManager

`ProfilingManager` 在 API 35 加入公开 SDK。App 可以通过 `requestProfiling()` 请求 Java heap dump（Java 堆中对象与引用的快照）、heap profile（按时间或调用栈统计分配）、stack sampling（定期抽样线程调用栈）或 system trace（系统运行轨迹），并通过监听器接收结果。仅注册监听器不会开始采集；调用方还必须显式调用 `requestProfiling()`，否则会一直等待一个从未发起的结果。

它适合在用户同意和产品采样策略允许的场景中取得现场数据。系统仍会执行速率限制，并可能拒绝请求。调用方应把“请求成功提交”“收到结果”“超时或失败”记录为不同状态。

### ApplicationStartInfo

`ApplicationStartInfo` 在 API 35 提供进程启动原因、启动类型、时间点和启动状态等结构化信息。它能减少只靠日志拼接启动阶段的歧义。时间点是否存在与启动路径有关，读取方必须检查返回数据，不能假设每个阶段都有值。

### ADPF 会话扩展

API 35 为 `PerformanceHintManager.Session` 增加 `setPreferPowerEfficiency()` 和基于 `WorkDuration`（一轮工作的起止时间及 CPU/GPU 耗时）的 `reportActualWorkDuration()`。前者表达功耗优先偏好，后者可以报告更丰富的工作时长信息。二者都是提示，设备是否支持、系统如何响应、频点如何变化由实现和当前热状态决定。

### 前台服务时间配额

target 35 的 App 在后台运行 `dataSync` 和 `mediaProcessing` 前台服务时，每种类型共享 24 小时内 6 小时的总配额。用户把 App 带到前台会重置计时器。配额耗尽后，系统调用 `Service.onTimeout(int, int)`；服务只有很短的停止窗口。

这里的 6 小时按同一类型的全部服务累计，不能按每个 Service 实例分别计算。迁移时需要盘点并发服务、重启路径和用户回到前台的状态转换。

### 16 KB 页面大小

Android 15 开始支持 16 KB 页大小的 arm64（64 位 ARM 架构）设备。它在 Android 15 并未成为所有设备默认配置。含原生代码的 APK 需要检查 ELF（Executable and Linkable Format，原生可执行文件和共享库格式）段对齐、打包对齐、预编译依赖和运行期页大小假设。

页大小变化会影响页表、缺页、映射粒度和小对象驻留开销，方向取决于工作负载。只看到系统版本无法判断设备页大小，应用应通过运行期 API 或系统信息识别，并在 4 KB 与 16 KB 环境分别测量。

## Android 16（API 36）：触发式 Profiling 与诊断 API

### 触发式 Profiling

`ProfilingManager.addProfilingTriggers()` 在 API 36 加入。App 可以登记由系统事件触发的采集规则，API 36 的公开触发类型包括 ANR 和 `APP_FULLY_DRAWN`（冷启动后调用 `reportFullyDrawn()`）。36.1 是 Android 16 的 minor SDK（小版本 API），又增加请求运行中 trace、用户强制停止、从最近任务划掉和任务管理器停止等触发类型。

触发式采集仍受系统速率限制和设备条件约束。它适合补充低复现率现场问题，不能保证每次事件都生成产物。

### 启动、帧与作业诊断

`ApplicationStartInfo.getStartComponent()` 在 API 36 加入，用于标识触发进程启动的组件类型。启动性能数据可以按 Activity（界面）、Service（无界面组件）、BroadcastReceiver（广播接收器）、ContentProvider（数据提供组件）等入口分组，避免把不同启动原因混在同一分位数中。

`FrameMetrics.FRAME_TIMELINE_VSYNC_ID` 也在 API 36 提供。它返回当前帧 timeline 的 Vsync ID，可用于关联 HWUI（Android 的硬件加速 UI 渲染管线）、SurfaceFlinger 和 Perfetto（Android 系统性能追踪工具）中的帧记录。设备或窗口条件不支持时，分析工具应保留缺失值。

`JobScheduler.getPendingJobReasons()` 返回一个作业当前可能存在的多个等待原因，`getPendingJobReasonsHistory()` 返回近期约束变化。这里的约束包括 App 显式要求的网络、电量条件，以及系统隐式施加的配额或待机限制。后台任务“没运行”时，先读取约束历史，再检查配额、网络、电量和待机状态，比仅看一次当前状态更可靠。

### SystemHealthManager headroom

Android 16 在 `SystemHealthManager` 提供 CPU 和 GPU headroom API。headroom 是指定时间窗口内还能使用多少处理能力的估计值。返回值适合让画质、工作量或并发度逐步调整，不能视作固定频率预算，也不能替代 Thermal API（系统温度与热节流接口）。

调用方需要遵守系统给出的最小查询间隔，处理设备不支持和无可用样本，并对连续读数做平滑。按单次读数立刻切换重负载档位，容易让工作量在两个档位间反复变化。

### 大屏自适应

target 36 的 App 在 smallest width（最小宽度）达到 600dp 的显示上，系统会忽略一部分方向、宽高比和可调整性限制；dp 是按屏幕密度换算的布局单位。迁移重点包括窗口 resize（尺寸变化）、配置变化、状态恢复和多窗口布局。尺寸变化是否重建 Activity 取决于清单和配置处理，不能写成每次 resize 都必然重建。

target 36 还可以用 `PROPERTY_COMPAT_ALLOW_RESTRICTED_RESIZABILITY` 暂时退出该行为。target 37 会忽略这项临时退出配置，所以 Android 16 的迁移不能停留在兼容模式。

### 预测性返回、定期任务与 edge-to-edge

target 36 的 App 运行在 Android 16 及以上时，系统默认启用 back-to-home（返回桌面）、cross-task（跨任务）和 cross-activity（跨 Activity）的预测性返回动画。旧的 `onBackPressed()` 不再收到调用，`KEYCODE_BACK` 也不再分发。AndroidX 返回分发器、平台返回回调和页面状态恢复都要一并测试；清单里的 `android:enableOnBackInvokedCallback="false"` 只适合作为临时退出手段。

`ScheduledThreadPoolExecutor.scheduleAtFixedRate()` 也有 target 36 行为变化。进程离开有效生命周期而错过多个周期后，恢复时最多立即执行一个遗漏任务。依赖“恢复后补跑全部周期”的统计或维护逻辑需要改成显式计算缺口。

对运行在 Android 16 且 target 36 的 App，系统不再接受 `windowOptOutEdgeToEdgeEnforcement` 退出配置。edge-to-edge 表示内容可以绘制到状态栏和导航栏所在区域；页面应正确处理 system bar（系统栏）、display cutout（刘海或挖孔区域）和 IME（输入法）提供的 insets（需要避让的边缘距离）。布局区域变化会影响测量、绘制和滚动范围，基准测试必须使用迁移后的最终布局。

## Android 17（API 37）：消息队列、GC 与现场诊断

### target 37 的无锁 MessageQueue

运行在 Android 17 且 target 37 的 App 使用新的 lock-free（无锁）`MessageQueue` 实现。lock-free 表示并发竞争时系统整体仍有线程能够前进，不代表每次操作都有固定耗时；官方目标是减少锁竞争和漏帧。公开 API 语义保持兼容，依赖反射读取私有字段或方法的代码会暴露问题。

兼容层仍保留 `mMessages` 字段，但新实现下该字段始终为 `null`，它不能反映队列是否为空。测试依赖需要升级：

- Espresso 使用 3.7.0 或以上版本。
- Robolectric 使用 4.17 或以上版本，并从 `@LooperMode(LEGACY)` 迁移到 `@LooperMode(PAUSED)`。
- 自研空闲判断改用公开同步机制或 Android 16 引入的 `TestLooperManager` 能力。

可在 debuggable（允许调试器附加的）构建上用兼容性开关提前测试 `USE_NEW_MESSAGEQUEUE`。测试范围要覆盖 Handler 密集场景、IdleHandler（消息队列空闲时的回调）、同步屏障（暂时只放行异步消息的队列标记）、测试框架空闲判断和依赖反射的 SDK。

Android 17 对 target 37 App 还禁止通过反射或 JNI（Java Native Interface，Java/Kotlin 与原生代码的调用接口）修改 `static final` 字段。性能测试框架若依赖这种方式替换时钟、常量或单例，需要同步清理。

### ART 分代 Concurrent Mark-Compact

Android 17 发布的 ART Concurrent Mark-Compact（并发标记压缩，简称 CMC）支持分代 GC。年轻代对象通常存活时间短，平台可以用更频繁、成本较低的 young collection（只覆盖年轻代的回收）处理这部分对象，再按条件执行 full collection（覆盖更大范围堆的回收）。

这项变化不能和 `userfaultfd` 混为同一开关。`userfaultfd` 是让用户空间参与处理缺页事件的 Linux 接口，CMC 使用它的演进早于 Android 17；Android 17 新增的是按对象代际选择回收范围的策略。分析时应区分 young/full collection、暂停阶段、并发标记时间、年轻对象进入老年代的晋升量，以及回收后仍驻留内存的集合。

这项 ART 改进还可以通过 Google Play system update 下发到 Android 12 及以上设备，因此“系统不是 Android 17”也不能证明它不存在。实验要同时记录 OS 版本、ART Mainline 模块版本和实际功能状态。

分代回收也不保证每个 App 都降低暂停时间。对象存活率高、跨代引用多或堆压力大时，收益会变化。结论需要来自目标设备、目标 ART 构建和稳定负载。

### API 37 的 ProfilingTrigger

Android 17 扩充系统触发式 Profiling：

| 触发类型 | 系统事件 | 产物或行为 |
| --- | --- | --- |
| `TRIGGER_TYPE_OOM` | App 抛出 OOM（Out of Memory，内存耗尽） | Java heap dump |
| `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` | 因 CPU 过度使用被终止 | 运行中 system trace 的快照 |
| `TRIGGER_TYPE_COLD_START` | `START_TYPE_COLD` 冷启动 | 新 system trace 与 stack sampling |
| `TRIGGER_TYPE_ANOMALY` | 平台识别到 App 的异常行为 | 产物和结果 tag 由异常类型决定 |
| `TRIGGER_TYPE_APP_COMPAT` | 平台识别到未来版本将不再支持的 App 异常行为 | 产物随异常变化，结果 tag 提供兼容性信息 |

冷启动采集持续到 App 调用 `Activity.reportFullyDrawn()`，默认上限为 5 秒，并使用 discard buffer：缓冲区写满后丢弃新事件，从而保留较早的启动轨迹。未调用 `reportFullyDrawn()` 会失去业务就绪边界，只能依赖超时停止。

OOM 触发要求自定义 `Thread.UncaughtExceptionHandler` 调用默认异常处理器。若异常链被截断，系统触发无法完成，App 只能另行调用 `requestProfiling()` 请求 heap dump。

### App 内存限制

Android 17 对所有 App 引入按设备总 RAM 设定的保守内存限制，但并非每台设备都会实施。命中限制后，`ApplicationExitInfo` 的 reason 为 `REASON_OTHER`，description 包含 `MemoryLimiter:AnonSwap`；AnonSwap 指匿名内存及其交换空间口径。只按 reason 聚合会把它和其他 `REASON_OTHER` 混在一起。

平台提供 `am memory-limiter status`、`manual` 和 `ignore` 子命令，用于查看状态、给指定 PID（进程号）施加测试限制或按 UID（App 的系统用户标识）忽略限制；不实施内存限制的设备上，这些命令不会产生对应效果。线上诊断可以结合 `TRIGGER_TYPE_ANOMALY` 获取命中内存限制时的 heap dump，但仍要考虑采样和速率限制。

### Android 17 的 NPU 与 NNAPI 边界

Android 17 要求 target 37 的 App 在直接访问 NPU（Neural Processing Unit，神经网络处理器）时声明 `FEATURE_NEURAL_PROCESSING_UNIT`。这属于设备能力声明与访问边界，不能据此推导某个模型会自动提速。

NNAPI（Neural Networks API）的 NDK App 接口从 Android 15 起已废弃，NN HAL（神经网络硬件抽象层）仍供系统和设备实现使用。NN HAL 1.3 也早于 Android 17。`android-17.0.0_r1` 中继续存在相关代码，只能证明兼容实现仍在源码树内，不能把旧接口写成 Android 17 新增能力。

对端侧推理做版本比较时，至少固定模型、delegate（把算子交给特定加速后端的适配层）、runtime（执行模型的软件运行时）、驱动、量化方案、热状态和功耗窗口。编译缓存是否命中、burst execution（复用执行上下文以减少重复准备开销）是否可用，都要从目标实现和 trace 证据判断，不应填写通用微秒级收益。

## 新增性能 API 的演进脉络

| API | 加入版本 | 用途 | 使用边界 |
| --- | --- | --- | --- |
| `PerformanceHintManager` | API 31 | 线程组工作时长提示 | 提示不等于频点命令 |
| FrameTimeline / Vsync ID 能力 | API 33 起扩展 | 跨渲染阶段关联帧 | 以设备和具体 API 可用性为准 |
| `ProfilingManager.requestProfiling()` | API 35 | App 主动请求 profile | 有速率限制，注册监听器不会发起采集 |
| `ApplicationStartInfo` | API 35 | 结构化启动信息 | 时间点和字段可能缺失 |
| `Session.setPreferPowerEfficiency()` | API 35 | 表达功耗优先偏好 | 由系统决定响应 |
| `ProfilingManager.addProfilingTriggers()` | API 36 | 注册系统事件采集 | 触发类型跨 36、36.1、37 扩展 |
| `FRAME_TIMELINE_VSYNC_ID` | API 36 | 关联窗口帧与系统帧 | 缺失时保留 unknown（未知）值 |
| CPU/GPU headroom | API 36 | 估计资源余量 | 设备可选，限制查询频率 |
| Android 17 新 ProfilingTrigger | API 37 | 冷启动、OOM、异常 CPU 等现场数据 | 受事件条件和速率限制 |

API 级别检查只解决符号可用性。设备能力、服务是否存在、权限、配额和厂商实现仍要单独探测。

## Deprecated API 与替代路径

### 返回手势

`Activity.onBackPressed()` 从 API 33 起废弃，时间点早于 Android 16。应用层优先使用 AndroidX `OnBackPressedDispatcher` 管理回调和生命周期；平台侧可按需求接入 `OnBackInvokedDispatcher`。预测性返回还要求界面状态在手势进行过程中可预览，单纯替换方法名不能完成迁移。

### WebView 强制深色

Android 13 起，`WebSettings.setForceDark()` 对 target 33 App 的行为变化，并进入废弃路径。网页内容应通过 CSS 的 `prefers-color-scheme`（页面声明偏好的明暗主题）和 WebView 的算法深色策略配合。切换主题时要测量页面重排与重绘，避免在滚动中反复改动设置。

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
- 直接访问 NPU 的 App 声明对应硬件 feature（能力声明），并处理设备不支持。

每次升级都应分开比较“系统版本变化”和“target 变化”。可在同一 Android 17 设备上用兼容性框架逐项开关行为，再用两个 target 构建复测，减少变量混杂。

## Perfetto 与平台数据如何配合

版本变化在 Perfetto 中的可见程度不同：

- 无锁 MessageQueue 的效果要从主线程调度、Handler 消息处理和帧 deadline（必须完成本帧工作的时限）观察；trace 中没有一个字段能代替兼容性检查，直接证明“无锁已启用”。
- FrameTimeline Vsync ID 可以关联应用帧、HWUI 和 SurfaceFlinger。
- GC 需要区分 young/full collection 及暂停、并发阶段；只有总 GC 次数很难解释分代策略。
- CPU/GPU headroom 是 App 可查询信号，频率、调度和热事件仍需系统 trace 辅助。
- ProfilingManager 生成独立的 profile 产物，不能假设它自动出现在当前 Perfetto 会话中。
- 前台服务配额、权限拒绝和 JobScheduler 等待原因需要结合 `dumpsys`（导出系统服务状态的命令）、API 返回和系统日志，trace 只覆盖其中一部分。

一次可复核的跨版本实验，应固定 APK、数据集、操作序列、设备温度和电源条件，并记录 OS build fingerprint（标识具体系统构建的一组属性）、target、ART/Mainline 模块、页大小和内核版本。Android 17 的内核字段若为 6.18，还要记录精确 tag；这里的核验锚点是 `android17-6.18-2026-06_r6`。

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
