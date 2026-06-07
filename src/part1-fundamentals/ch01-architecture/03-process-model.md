---
title: "进程模型与生命周期管理"
chapter: "1.3"
section: "1.3"
drafted_date: "2026-05-13"
drafted_by: openclaw-task2a
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-13"
last_verified_against: "AOSP android-16.0.0_r1, developer.android.com, source.android.com lmkd docs"
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/guide/components/activities/process-lifecycle"
  - type: official
    path: "https://developer.android.com/guide/components/processes-and-threads"
  - type: official
    path: "https://developer.android.com/guide/topics/manifest/application-element"
  - type: official
    path: "https://developer.android.com/guide/topics/manifest/service-element"
  - type: official
    path: "https://source.android.com/docs/core/perf/lmkd"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessList.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessStateRecord.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Process.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ApplicationExitInfo.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java @ android-16.0.0_r1"
  - type: aosp
    path: "system/memory/lmkd/lmkd.cpp @ android-16.0.0_r1"
  - type: aosp
    path: "system/core/libprocessgroup/profiles/task_profiles.json @ android-16.0.0_r1"
  - type: aosp
    path: "system/core/libprocessgroup/processgroup.cpp @ android-16.0.0_r1"
  - type: aosp
    path: "system/core/libcutils/include/private/android_filesystem_config.h @ android-16.0.0_r1"
tags:
  - process
  - ams
  - oom_adj
  - lmkd
  - zygote
  - process-lifecycle
  - binder
  - cgroup
related_chapters:
  - "1.1"
  - "1.2"
  - "1.4"
  - "1.5"
  - "4.4"
  - "5.1"
  - "5.8"
task2b_state: fixed
task6_state: revisiting
reviewed_by: openclaw-task6
reviewed_date: "2026-05-13"
task6_result: pass-light-edit
task6_reviewed_date: "2026-05-13"
review_round: 1
task6_review_notes: "2026-05-13 task6 review: L1/L2 通过；本轮仅补齐 review 元数据，无新增 L3/L4 回炉项。"
status: ready-for-review
pipeline_stage: task6_pending
task9_state: reviewed
task9_result: auto-fixed
task9_reviewed_date: "2026-06-07"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-07T08:20:00+08:00"
last_task9_autofix_at: "2026-06-07"
last_task9_audit: "2026-06-07"
last_task6_audit: "2026-05-25"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-05-31
---

# 进程模型与生命周期管理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android App 进程边界：默认独立 Linux 进程、`android:process`、UID / GID 与 Zygote fork
- 🔹 组件状态如何影响进程生命周期：Activity、Service、BroadcastReceiver、ContentProvider / bound service 依赖
- 🔹 `oom_score_adj` 与 `procState`：AMS / OomAdjuster 如何把组件状态转成系统可执行的保活优先级
- 🔹 `lmkd` 与低内存回收：PSI、内存压力、进程重要性和 kill 决策
- 🔹 调度组与任务 profile：top-app、foreground、background 对 CPU / I/O 资源分配的影响
- 🔹 多进程架构的收益和代价：隔离、启动、内存、Binder、状态一致性
- 🔹 调试观察点：`dumpsys activity processes`、`/proc/<pid>/oom_score_adj`、Perfetto、lmkd 日志

### 扩展（可选深入）

- 🔸 前台服务、长时间 started service、cached app 限制在 Android 13+ 的行为边界
- 🔸 phantom process / 子进程限制对 native worker 和脚本执行场景的影响
- 🔸 厂商低内存策略差异与线上指标设计

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 进程模型解决的性能问题

Android App 的生命周期不由 App 自己决定。系统会根据当前运行的组件、用户是否能感知这些组件、系统内存压力，把每个进程放到一套重要性序列里；内存紧张时，排在后面的进程先被回收。

这套模型直接影响三类性能问题：

- 启动速度：进程不存在时，AMS 需要通过 Zygote 创建进程、绑定 `Application`、再调度组件入口。
- 内存长尾：cached 进程越多，切回体验越好，但系统可用内存越少，`lmkd` 触发回收的概率越高。
- 后台任务可靠性：组件已经结束但线程还在跑，系统可能把整个进程回收，线程没有机会收尾。

官方文档把这件事讲得很直接：进程在某段代码需要运行时创建，保留到系统需要回收内存且该进程不再有足够重要性为止；进程寿命由系统根据组件状态、用户感知程度和系统内存共同判断。 [已验证: 官方文档, https://developer.android.com/guide/components/activities/process-lifecycle]

## Android App 的进程边界

默认情况下，一个 Android 应用运行在一个独立 Linux 进程里，同一应用的 Activity、Service、BroadcastReceiver、ContentProvider 也运行在同一个主线程里。组件不会天然拥有独立线程；系统回调、生命周期方法和 UI 事件都进入该进程的 main thread。线程模型详见 1.5 节。 [已验证: 官方文档, https://developer.android.com/guide/components/processes-and-threads]

Manifest 可以改变这个默认边界。`<activity>`、`<service>`、`<receiver>`、`<provider>` 都支持 `android:process`，`<application>` 也可以给整包设置默认进程名。进程名以冒号开头时是应用私有进程，例如 `:remote`；使用全限定进程名时，在相同签名和相同 Linux UID 条件下，不同应用可以共享进程。共享进程属于少数系统级或套件级场景，普通业务不应把它当成通用优化手段。 [已验证: 官方文档, https://developer.android.com/guide/topics/manifest/application-element] [已验证: 官方文档, https://developer.android.com/guide/topics/manifest/service-element]

AOSP 侧的进程创建入口在 `android.os.Process.start()`，它把进程类名、UID / GID、ABI、targetSdk、挂载策略、包名等参数交给 `ZygoteProcess.start()`。AMS 调用这条路径时，会为应用分配 Linux UID、进程名和运行时参数，再等待应用进程通过 `attachApplicationLocked()` 回连。 [已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/Process.java] [已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java]

这段代码只用来确认进程创建边界：`Process.start()` 本身不直接 fork，它把请求发给 Zygote。

```java
// frameworks/base/core/java/android/os/Process.java @ android-16.0.0_r1
public static ProcessStartResult start(@NonNull final String processClass,
        @Nullable final String niceName,
        int uid, int gid, @Nullable int[] gids,
        int runtimeFlags, int mountExternal,
        int targetSdkVersion, @Nullable String seInfo,
        @NonNull String abi, @Nullable String instructionSet,
        @Nullable String appDataDir, @Nullable String invokeWith,
        @Nullable String packageName, int zygotePolicyFlags,
        boolean isTopApp, @Nullable long[] disabledCompatChanges,
        @Nullable Map<String, Pair<String, Long>> pkgDataInfoMap,
        @Nullable Map<String, Pair<String, Long>> whitelistedDataInfoMap,
        boolean bindMountAppsData, boolean bindMountAppStorageDirs,
        boolean bindMountSystemOverrides,
        @Nullable String[] zygoteArgs) {
    return ZYGOTE_PROCESS.start(processClass, niceName, uid, gid, gids,
            runtimeFlags, mountExternal, targetSdkVersion, seInfo,
            abi, instructionSet, appDataDir, invokeWith, packageName,
            zygotePolicyFlags, isTopApp, disabledCompatChanges,
            pkgDataInfoMap, whitelistedDataInfoMap, bindMountAppsData,
            bindMountAppStorageDirs, bindMountSystemOverrides, zygoteArgs);
}
```

对性能分析来说，`android:process=":remote"` 不是免费隔离。它会多出一次进程创建、一个独立主线程和消息队列、一份 `Application` 初始化、一套 ClassLoader 与堆内对象；跨进程访问还会变成 Binder IPC。只有在崩溃隔离、内存峰值隔离、插件沙箱、WebView / media / push 这类边界清楚的场景里，多进程才值得付这笔成本。

## 组件状态如何变成进程重要性

官方文档把进程重要性分成 foreground、visible、service、cached 四大类。AOSP 实现里还会继续细分，例如 perceptible、previous、home、backup、service B、cached min/max。越接近前台，`oom_score_adj` 越低，越不容易被 `lmkd` 选中；cached 区间的进程最容易被回收。 [已验证: 官方文档, https://developer.android.com/guide/components/activities/process-lifecycle]

| 状态 | 触发条件 | Android 16 典型 `oom_score_adj` | 性能含义 |
| --- | --- | --- | --- |
| foreground / top | 顶层 resumed Activity、正在执行的 BroadcastReceiver、正在执行回调的 Service | `FOREGROUND_APP_ADJ = 0` | 用户正在交互，内存回收靠后考虑 |
| visible | Activity 可见但不在前台，或正在跑远程动画 | `VISIBLE_APP_ADJ = 100` | 杀掉会产生可见闪断，保护级别很高 |
| perceptible / foreground service | 前台服务、音乐播放、用户可感知的后台能力 | `PERCEPTIBLE_APP_ADJ = 200`，短前台服务在 Android 16 源码里会落到更细的 perceptible medium 区间 | 不在屏幕最前，但用户能感知中断 |
| service | started service 仍在运行 | `SERVICE_ADJ = 500`，老化服务可能进入 `SERVICE_B_ADJ = 800` | 可保留，但内存压力升高时会被牺牲 |
| home / previous | Launcher 或上一个应用 | `HOME_APP_ADJ = 600`、`PREVIOUS_APP_ADJ = 700` | 提升返回桌面和最近任务切换体验 |
| cached | Activity 已 stop，当前没有用户可感知工作 | `CACHED_APP_MIN_ADJ = 900` 到 `CACHED_APP_MAX_ADJ = 999` | 系统优先回收；App 要能无损恢复 |

[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ProcessList.java]

分类规则有两个容易踩坑的地方。

第一，系统按进程内最重要的活跃组件定级。一个进程里同时有 visible Activity 和 started Service 时，它按 visible 处理。Bound service 和 ContentProvider 也会把被依赖进程的级别抬高到调用方所需的保护级别。 [已验证: 官方文档, https://developer.android.com/guide/components/activities/process-lifecycle]

第二，BroadcastReceiver 的 `onReceive()` 返回后，系统就不再认为这个 receiver 处于活跃状态。`onReceive()` 里启动裸线程再返回，线程仍在跑，但进程可能已经降级，内存紧张时会被直接回收。官方建议把这类工作交给 `JobService` / WorkManager 等系统可感知的调度入口。 [已验证: 官方文档, https://developer.android.com/guide/components/activities/process-lifecycle]

## `OomAdjuster` 把组件状态转成系统决策

AMS 不会只保存一个“前台 / 后台”的布尔值。Android 16 的 `OomAdjuster.computeOomAdjLSP()` 会从 top app 开始，按 Activity 可见性、广播执行、Service 执行、前台服务、绑定关系、ContentProvider 依赖、recent task 等条件计算三组结果：`adj`、`procState` 和 `schedGroup`。`ProcessStateRecord` 保存当前值和已提交值，后续再写入内核和 `lmkd` 可见的接口。 [已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java] [已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ProcessStateRecord.java]

这段骨架说明 top app、广播、Service 回调会先拿到较高保护级别，然后才进入 Activity 和前台服务等后续规则。

```java
// frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java @ android-16.0.0_r1
if (app == topApp && PROCESS_STATE_CUR_TOP == PROCESS_STATE_TOP) {
    adj = FOREGROUND_APP_ADJ;
    schedGroup = SCHED_GROUP_TOP_APP;
    state.setAdjType("top-activity");
    procState = PROCESS_STATE_TOP;
} else if (state.isRunningRemoteAnimation()) {
    adj = VISIBLE_APP_ADJ;
    schedGroup = SCHED_GROUP_TOP_APP;
    state.setAdjType("running-remote-anim");
    procState = PROCESS_STATE_CUR_TOP;
} else if (state.getCachedIsReceivingBroadcast(mTmpSchedGroup)) {
    adj = FOREGROUND_APP_ADJ;
    schedGroup = mTmpSchedGroup[0];
    state.setAdjType("broadcast");
    procState = ActivityManager.PROCESS_STATE_RECEIVER;
} else if (psr.numberOfExecutingServices() > 0) {
    adj = FOREGROUND_APP_ADJ;
    schedGroup = psr.shouldExecServicesFg()
            ? SCHED_GROUP_DEFAULT : SCHED_GROUP_BACKGROUND;
    state.setAdjType("exec-service");
    procState = PROCESS_STATE_SERVICE;
}
```

`adj` 决定低内存回收优先级，`procState` 决定更宽的运行状态和统计口径，`schedGroup` 决定进程进入哪个调度组。只看其中一个值容易误判。例如一个前台服务可能拿到 perceptible 级别的 `adj`，但它不等同于 top app；一个 cached recent 进程可能比普通 cached 更靠前，但仍然处在可回收范围里。

## `lmkd` 如何使用 `oom_score_adj`

Android 低内存回收从早期 in-kernel LMK 走向 userspace `lmkd`。官方文档说明，Android 10 及以上支持 PSI（Pressure Stall Information）监控，`ro.lmk.use_psi` 默认启用；PSI 通过任务因内存短缺而停顿的时间衡量压力，比传统 `vmpressure` 更贴近用户体验。 [已验证: 官方文档, https://source.android.com/docs/core/perf/lmkd]

AMS 会把新的 `oom_score_adj` 发送给 `lmkd`。Android 16 的 `ProcessList.setOomAdj()` 通过 `LMK_PROCPRIO` 命令写入 pid、uid、adj；`lmkd` 再结合内存压力、swap、cgroup 统计和设备配置决定 kill 目标。 [已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ProcessList.java] [已验证: AOSP android-16.0.0_r1, system/memory/lmkd/lmkd.cpp]

这段代码对应 AMS → `lmkd` 的优先级同步，不代表马上 kill 进程。

```java
// frameworks/base/services/core/java/com/android/server/am/ProcessList.java @ android-16.0.0_r1
public static void setOomAdj(int pid, int uid, int amt) {
    if (pid <= 0) {
        return;
    }
    if (amt == UNKNOWN_ADJ) {
        return;
    }

    ByteBuffer buf = ByteBuffer.allocate(4 * 4);
    buf.putInt(LMK_PROCPRIO);
    buf.putInt(pid);
    buf.putInt(uid);
    buf.putInt(amt);
    writeLmkd(buf, null);
}
```

`lmkd` 不是按 RSS 从大到小机械杀进程。官方配置里，`ro.lmk.medium` 默认从 `oom_adj >= 800` 的 cached 或非必要 service 开始，`ro.lmk.critical` 才允许从 `oom_adj >= 0` 的更高优先级进程里选目标。不同设备可以通过 `ro.config.low_ram`、`ro.lmk.kill_heaviest_task`、`ro.lmk.kill_timeout_ms` 等属性改变策略，线上指标不应把所有设备的低内存行为混成一个阈值。

## 调度组和任务 profile 影响 CPU / I/O 资源

进程重要性还会影响调度资源。`OomAdjuster` 在计算 `adj` 的同时给出 `schedGroup`，例如 top app 可进入 `SCHED_GROUP_TOP_APP`，普通后台进程进入 background。`system/core/libprocessgroup` 再把这些抽象 profile 映射到 cpuset、uclamp、I/O priority、timer slack 等内核控制面。 [已验证: AOSP android-16.0.0_r1, system/core/libprocessgroup/processgroup.cpp] [已验证: AOSP android-16.0.0_r1, system/core/libprocessgroup/profiles/task_profiles.json]

`task_profiles.json` 里能看到 `SCHED_SP_TOP_APP`、`HighPerformance`、`ProcessCapacityHigh`、`MaxIoPriority` 这类 profile 名称。它们不是 App 可以随意申请的业务开关，而是系统根据进程状态分配的资源策略。对卡顿分析来说，这解释了同一段代码在前台、后台、最近任务切换时 CPU 行为不同的原因：调度组已经变了。

这类差异可以在 Perfetto 里通过线程状态、CPU 迁移、调度延迟和 cpuset 观察；也可以在设备上读取 cgroup 文件辅助确认。不同内核版本和厂商配置的 cgroup 路径会变化，排查时以设备实际挂载为准。

## 多进程架构的收益和代价

多进程最稳的收益是隔离。WebView、播放器、推送、插件、相机预览、第三方 SDK 容器这类模块崩溃时，主进程有机会保住用户当前页面；某些大内存模块放到独立进程，也能在任务结束后通过回收整个进程释放堆、native heap 和图形资源。

代价同样清楚：

- 启动代价：远程进程第一次被拉起时，要经历 Zygote fork、`Application` 初始化、组件绑定和类加载。
- 内存代价：每个进程都有独立 Java heap、native heap、线程栈、ClassLoader、Binder 线程池和运行时元数据。
- IPC 代价：跨进程方法调用会变成 Binder transaction，参数需要序列化，共享大对象还要引入 ashmem / memfd / `ParcelFileDescriptor` 等机制。
- 状态代价：单例、缓存、登录态、实验开关在多进程里各有副本，需要明确同步策略。
- 调试代价：ANR、Crash、内存泄漏和启动耗时要按进程拆开看，不能只盯主进程。

多进程适合“边界稳定、通信少、失败可隔离”的模块，不适合把一个高频同步调用的业务服务拆出去。每秒几十次跨进程同步调用，常会在 Binder 线程池、锁等待和主线程回调上还债。Binder 机制详见 1.4 节。

## 观察进程状态的最小工具组

排查进程生命周期问题时，先把 pid、uid、processName、`oom_score_adj`、`procState`、调度组对上，再看内存和 CPU。只看 Java 堆或只看 RSS，无法解释系统为什么杀这个进程。

下面这组命令用于把 AMS 视角、内核视角和 `lmkd` 视角放在同一张表里。

```bash
# 1. AMS 视角：查看进程、adj、procState、组件归属
adb shell dumpsys activity processes | grep -A 12 "ProcessRecord"

# 2. 内核视角：确认当前 oom_score_adj
adb shell cat /proc/<pid>/oom_score_adj

# 3. 进程与 UID：确认多用户 / 多进程场景下的身份
adb shell ps -A -o PID,UID,NAME | grep <package-or-process>

# 4. lmkd 日志：确认低内存 kill 的触发和目标
adb logcat -b events -b system | grep -i "lmkd\|lowmemorykiller"
```

`dumpsys activity processes` 适合回答“AMS 认为它是什么状态”，`/proc/<pid>/oom_score_adj` 适合确认“内核和 `lmkd` 看到的值是多少”，`logcat` 适合追 kill 事件。三者对不上时，优先怀疑进程刚发生状态变化、AMS 尚未完成 OOM_ADJ 提交，或设备厂商改过低内存策略。

Perfetto 适合补上时间维度：进程何时被启动、主线程何时 attach、Binder 调用卡在哪个进程、`lmkd` kill 前后内存压力如何变化、top-app 调度组何时切换。定位启动慢时，把 `am_proc_start`、`bindApplication`、主线程 `ActivityThread` 切片和 Zygote fork 放到同一条时间线上；定位低内存回收时，把 `lmkd` 事件、PSI / memory counters、目标进程状态变化放在一起看。

## 常见误判

**误判一：进程还在，任务就可靠。** 裸线程、协程、线程池任务如果没有绑定到系统可感知的组件状态，`onReceive()` 或 Activity 生命周期结束后，进程可能降级到 cached。官方文档明确提醒，cached 进程随时可能被杀，`onDestroy()` 在系统 kill 场景下也没有调用保证。 [已验证: 官方文档, https://developer.android.com/guide/components/activities/process-lifecycle]

**误判二：前台服务等同于前台 App。** 前台服务会提高进程重要性，但 Android 16 源码里 top app、visible、foreground service 是不同层级；短前台服务还有单独的超时和能力限制。性能排查时，前台服务保活和前台交互性能不能画等号。

**误判三：低内存回收只看谁占内存大。** `lmkd` 会结合 PSI、设备属性、`oom_score_adj` 和策略参数选目标。大 RSS 的 visible 进程通常比小 RSS 的 cached 进程更受保护，除非系统已经进入很高压力区间。

**误判四：多进程一定提升稳定性。** 多进程能隔离崩溃，但也会增加启动、内存和 Binder 成本。把高频同步服务放到远程进程，可能把原本一次函数调用变成主线程等待 Binder 往返。

## 版本边界

- Android 10 及以上：官方 lmkd 文档将 PSI 作为默认内存压力检测机制，前提是内核启用 `CONFIG_PSI=y`。旧设备可能仍依赖 `vmpressure` 或厂商自定义策略。 [已验证: 官方文档, https://source.android.com/docs/core/perf/lmkd]
- Android 13 及以上：官方文档说明 cached 进程在进入活跃生命周期状态之前，可能获得有限或没有执行时间。后台任务不能依赖 cached 进程持续运行。

### CachedAppOptimizer / Freezer 机制（Android 11+）

AOSP 在 Android 11（API 30）已经引入 `CachedAppOptimizer` / freezer 代码路径和 `Process.setProcessFrozen()`，但默认未启用；Android 12（API 31）把 `DEFAULT_USE_FREEZER` 改为 true，并加入 Binder freeze / unfreeze 处理。它通过 cgroup v2 freezer 将 adj >= 900 的 cached 进程冻结，使其线程停止执行，而非简单降优先级等待调度。

**核心行为：**
- **冻结条件**：`adj >= CACHED_APP_MIN_ADJ (900)` 时触发 `CachedAppOptimizer.freezeAppAsyncLSP()`
- **冻结效果**：线程 slice 在 Perfetto 中彻底消失（零 CPU 时间），但进程本身仍存在
- **解冻触发**：冻结进程收到同步 Binder 调用时被解冻（unfreeze）
- **异常退出**：若解冻后处理不当，系统记录 `ApplicationExitInfo.REASON_FREEZER`（API 33+）

**Perfetto 区分方法：**
- **被 freezer 冻结**：进程存在，线程 slice 消失 → 进程 track 可见，thread track 空白
- **被 LMK 杀死**：进程直接从 track 消失

**版本差异：**

| 特性 | 引入版本 |
|------|---------|
| `CachedAppOptimizer` / freezer 代码路径 | Android 11 (API 30)，AOSP 默认 `DEFAULT_USE_FREEZER = false` |
| freezer 默认启用与 Binder freeze 处理 | Android 12 (API 31)，AOSP `DEFAULT_USE_FREEZER = true` |
| `REASON_FREEZER` | Android 13 (API 33) |

**源码锚点：**
- `frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java`
- `system/core/libprocessgroup/profiles/task_profiles.json`（`FreezerState` / `Frozen` profile）
- `frameworks/base/services/core/java/com/android/server/am/ProcessList.java`（CACHED_APP_MIN_ADJ = 900）

[已验证: 官方文档, https://developer.android.com/guide/components/activities/process-lifecycle] [已验证: AOSP android-11.0.0_r1 / android-12.0.0_r1, frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java] [已验证: AOSP android-16.0.0_r1, system/core/libprocessgroup/profiles/task_profiles.json]
- Android 16 源码：`ProcessList` 的 `CACHED_APP_MIN_ADJ = 900`、`CACHED_APP_MAX_ADJ = 999`、`FOREGROUND_APP_ADJ = 0`、`VISIBLE_APP_ADJ = 100`、`SERVICE_ADJ = 500` 等常量仍是 OOM_ADJ 分层的基础；具体 kill 行为还要看设备 lmkd 配置。 [已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ProcessList.java]

## 参考资料

- Android Developers: Processes and app lifecycle
- Android Developers: Processes and threads overview
- Android Developers: `<application>` / `<service>` manifest elements
- AOSP android-16.0.0_r1: `ProcessList.java`、`OomAdjuster.java`、`ProcessStateRecord.java`、`ActivityManagerService.java`、`Process.java`
- AOSP android-16.0.0_r1: `system/memory/lmkd/lmkd.cpp`、`system/core/libprocessgroup/profiles/task_profiles.json`
- source.android.com: Low memory killer daemon
