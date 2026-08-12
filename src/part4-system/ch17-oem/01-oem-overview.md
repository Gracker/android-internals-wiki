---
title: "OEM 性能优化的通用思路"
chapter: "17.1"
section: "17.1"
status: "finalized"
pipeline_stage: "ready-to-publish"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
tags: [['oem', 'performance', 'freezer', 'preloading', 'background-management']]
confidence: medium
sources:
- type: official
  path: developer.android.com/topic/performance/background-optimization
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/Freezer.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Process.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/jni/android_util_Process.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/res/values/config.xml
- type: aosp
  path: https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/libprocessgroup/profiles/task_profiles.json
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/ZygoteInit.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/config/preloaded-classes
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/ZygoteConfig.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/ZygoteServer.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/ZygoteProcess.java
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/fair.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/cpufreq_schedutil.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/scheduler/sched-energy.rst
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/admin-guide/cgroup-v2.rst
- type: official
  path: https://source.android.com/docs/core/perf/cached-apps-freezer
- type: official
  path: https://developer.android.com/develop/background-work
- type: official
  path: https://developer.android.com/develop/background-work/background-tasks/persistent
- type: official
  path: https://developer.android.com/develop/background-work/services/fgs
- type: official
  path: https://source.android.com/docs/core/power/thermal-mitigation
- type: official
  path: https://source.android.com/docs/core/power/performance
- type: kernel
  path: kernel/sched/fair.c
- type: aosp
  path: frameworks/base/config/preloaded-classes
last_verified: "2026-07-09"
last_verified_against: "AOSP android-17.0.0_r1 CachedAppOptimizer/Freezer/Process/ZygoteConfig/ZygoteServer"
related_chapters: "[\"5.1\", \"5.5\", \"5.6\", \"4.4\", \"8.3\", \"17.2\"]"
task2b_state: "fixed"
task6_state: "reviewed"
task9_state: "reviewed"
---

# OEM 性能优化的通用思路

## OEM 优化分析要回答什么

同一个 APK 在两台设备上出现不同的启动、掉帧或后台行为，原因可能来自应用代码、硬件能力、AOSP 配置、厂商实现、用户设置，也可能来自测试条件。把差异直接归因给“ROM 优化”没有诊断价值。

OEM 性能分析要回答三个可验证的问题：

1. 当前设备相对 AOSP 基线改了什么；
2. 改动通过哪一层影响了目标进程；
3. 这项改动改善了哪个指标，又把成本转移到了哪里。

平台参照为 `android-17.0.0_r1`，内核参照为 `android17-6.18-2026-06_r6`。它们用于定义源码基线，不代表任意 Android 17 商品设备都运行相同提交。设备的 `ro.build.fingerprint`、APEX 版本、vendor 分区、内核配置、设备树、固件和产品 overlay 都可能改变运行结果。

因此，Pixel Trace 适合作为一组对照数据，无法充当所有设备的“标准答案”。可靠的归因应同时具备源码位置、设备配置和运行证据；缺少其中一项时，结论要保留边界。

## 五类目标与互相牵制的预算

OEM 优化通常覆盖启动、流畅性、内存、功耗和温控。五类目标共享 CPU、GPU、内存带宽、存储带宽、电池功率与散热能力，局部收益经常伴随另一项成本。

| 方向 | 常用观测量 | 系统侧可调位置 | 容易遗漏的代价 |
|---|---|---|---|
| 启动 | TTID、TTFD、进程创建、I/O、类加载、首帧 | Zygote、ART 编译策略、存储预取、启动阶段调度 | 预热内存、后台 CPU、系统启动时长 |
| 流畅性 | 帧时间、deadline miss、输入到显示延迟 | 调度、DVFS、RenderThread、SurfaceFlinger、HWC | 峰值功耗、温升、后台吞吐 |
| 内存 | RSS/PSS、swap、PSI、回收和重启次数 | `lmkd`、压缩、ZRAM、cached freezer、缓存上限 | 解冻延迟、换入抖动、冷启动 |
| 功耗 | CPU/GPU residency、唤醒、网络与传感器活动 | EAS、schedutil、cpuidle、Power HAL、任务批处理 | 响应延迟、吞吐下降、通知延后 |
| 温控 | Thermal HAL severity、频率上限、机身温度、长稳帧率 | Thermal HAL、冷却设备、功率预算、场景策略 | 峰值性能受限，短跑分与长稳态分离 |

### 启动：先分清进程状态

一次 Activity 启动可能落在热启动、温启动或冷启动。系统若保留了进程，或者提前完成了 dexopt、文件页预取、USAP fork，Trace 形态都会变化。分析时要分别记录：

- 目标进程在点击前是否存在；
- Zygote 或 USAP 是否参与进程创建；
- APK、DEX、资源与动态库的页面是否已经进入 page cache；
- 编译产物和 profile 是否发生变化；
- 首帧前线程获得了多少 CPU，是否遭遇 I/O 或 Binder 等待。

只用一次 TTID 比较两台设备，会把进程状态和缓存状态误算成厂商能力。更完整的应用启动方法见[启动优化](../../part2-performance/ch08-responsiveness/03-launch-optimization.md)。

### 流畅性：从 deadline 反推瓶颈

一帧横跨输入、应用主线程、RenderThread、GPU、SurfaceFlinger、HWC 和显示扫描。OEM 可以调整 Power HAL 提示、线程分组、刷新率策略、合成选择和驱动行为。某个线程跑上大核只能证明调度结果，无法单独证明存在“游戏加速”或应用白名单。

分析掉帧时，应围绕 deadline 回看 runnable delay、运行时长、Binder 依赖、GPU fence、合成类型和频率变化。渲染各阶段的职责可结合[渲染管线总览](../../part2-performance/ch18-rendering-pipelines/01-pipeline-overview.md)阅读。

### 内存：保留、压缩、冻结与回收是四种动作

内存治理不等同于调大 `lmkd` 阈值。系统可以保留 cached 进程、压缩其匿名页、把页面换到 ZRAM、冻结进程，也可以在压力升高时终止它。每种动作影响不同：

- 保留进程减少重建成本，但继续占用物理页和内核对象；
- 压缩或换出释放 DRAM，切回时需要解压或换入；
- 冻结停止 CPU 执行，内存仍可被回收或交换；
- 终止进程释放范围最广，下一次进入要重新创建进程和应用状态。

`oom_score_adj` 主要帮助 `lmkd` 选择对象，PSI、thrashing、watermark 和可用文件页等信号参与判断回收时机。相关主线见[`lmkd` 与低内存回收](../../part1-fundamentals/ch04-memory/04-lmk.md)。

### 功耗与温控：短时加速不能替代稳态测试

Android 17 内核参照中的 EAS 会在 `kernel/sched/fair.c` 通过 `find_energy_efficient_cpu()` 比较候选 CPU，并由 `compute_energy()` 使用 Energy Model 估算能耗。`schedutil` 再根据调度器提供的利用率选择频率。设备的 CPU 拓扑、capacity、Energy Model、uclamp、cpuset 和驱动响应都会改变结果；旧资料中的 `sched_energy_cost` 不是这套内核的通用调参入口。

这些机制只能在当前功率和温度边界内工作。Android Thermal HAL 报告的 severity 会影响系统服务、任务调度和冷却动作。测试游戏或相机时，需同时给出冷机阶段、升温过程和稳态窗口。只截取开局几十秒，得到的是 boost 能力，无法说明持续性能。

调度、调频和温控的基础可继续阅读[Linux 调度](../../part1-fundamentals/ch05-cpu-power/01-linux-scheduling.md)、[DVFS](../../part1-fundamentals/ch05-cpu-power/04-dvfs.md)与[温控机制](../../part1-fundamentals/ch05-cpu-power/05-thermal.md)。

## 从 Kernel 到应用的改动位置

OEM 性能能力很少集中在单个服务中。把现象放回分层路径，能缩小排查范围。

### Kernel：执行与资源控制

这一层包括：

- EEVDF/CFS 公平类调度、EAS、uclamp、cpuset 和 CPU affinity；
- schedutil、cpufreq、cpuidle 与 SoC 驱动；
- cgroup v2 的 CPU、memory、I/O 和 freezer 控制；
- PSI、内存回收、ZRAM、块 I/O 与文件系统；
- GPU、显示、相机、网络等设备驱动。

OEM 可能通过内核补丁、Kconfig、设备树、内核模块或 sysfs 参数改变行为。看到一个非标准 tracepoint 或 sysfs 节点时，应先确定它属于 GKI、vendor module 还是产品私有实现，再讨论语义。

### Native：跨进程通信与硬件合成

常见位置包括 Binder 驱动及用户态库、SurfaceFlinger、RenderEngine、HWC、AudioFlinger、媒体服务和硬件 HAL。显示路径的差异往往来自 HWC 能力、buffer 格式、合成策略或驱动 fence。Binder 延迟则要分解为客户端 runnable delay、事务排队、服务端执行和回复，不能看到等待时间就推断厂商改了线程池。

### Framework：策略决策

AMS/ATMS 决定进程状态和组件生命周期，WMS 管理窗口与过渡，`CachedAppOptimizer` 处理 cached 进程压缩和冻结，JobScheduler、AlarmManager、DeviceIdleController、App Standby 与 PowerManager 管理后台和功耗。产品资源 overlay、DeviceConfig、Settings、task profile 及厂商服务均可能在这一层改变策略。

### App 与系统应用：公开契约和产品能力

应用侧能稳定依赖的是 SDK 行为，例如 WorkManager、JobScheduler、foreground service、`PerformanceHintManager`、Game Mode 或厂商公开 SDK。cached freezer 没有面向三方应用的公开控制 API。某个产品若提供“预启动”“内存扩展”“性能引擎”等名称，需要分别查清它控制的是编译、缓存、进程、调度、存储还是 UI 展示；营销名称本身不构成技术证据。

## Cached Apps Freezer：Android 17 的源码边界

### Frozen Process 指什么

Android 文档里的 frozen process 通常指仍有 Linux 进程和内存状态、但线程暂停执行的 cached 进程。它没有 CPU 时间，仍可能持有内存、文件描述符和部分内核资源。内存压力到来时，`lmkd` 仍可终止它。

Android 14 及以后，当一个应用的全部进程进入 frozen 状态，系统还会终止其活动 TCP socket。冻结不能作为后台网络保活手段。

### SIGSTOP 能暂停进程，但缺少 Android 协调

`SIGSTOP` 无法被应用捕获或忽略。向一个进程发送该信号会暂停它的线程组，`SIGCONT` 可恢复执行。其他独立子进程不会因为主进程收到信号而自动同步暂停。

这条方案缺少 Android 进程状态、Binder 和组件生命周期的配合。进程若在持锁或 IPC 临界区停住，依赖方可能长时间等待。SIGSTOP 适合调试和受控实验，不应被三方应用当作后台治理接口。

### cgroup v2 freezer 的语义

内核的 `cgroup.freeze` 接收 `1` 或 `0`。冻结请求可能需要一段时间完成，完成状态从 `cgroup.events` 的 `frozen` 字段读取。冻结一个 cgroup 会暂停其中的 tasks；进程迁入 frozen cgroup 后也会停下，迁出后可以运行。由此可知，“写入以后瞬间、原子地冻结整个应用”属于过度描述。

在 Android 17 r1 中，Framework 按 `ProcessRecord` 发起冻结。`android.os.Process.setProcessFrozen(pid, uid, true)` 的 JNI 实现给目标 pid 应用 `Frozen` task profile；该 profile 把目标 pid cgroup 的 `FreezerState` 写为 `1`。同一 UID 的多个进程会分别进入冻结流程，只有全部进程都被冻结后，`UidRecord` 才标记为 frozen。

下面的源码摘录用于确认 Binder 与 cgroup 的调用顺序，省略了错误处理和统计代码。

```java
// CachedAppOptimizer.java @ android-17.0.0_r1
if (mFreezer.freezeBinder(pid, true, FREEZE_BINDER_TIMEOUT_MS) != 0) {
    handleBinderFreezerFailure(proc, "outstanding txns");
    return;
}
mFreezer.setProcessFrozen(pid, proc.uid, true);

// Freezer.java @ android-17.0.0_r1
public void setProcessFrozen(int pid, int uid, boolean frozen) {
    Process.setProcessFrozen(pid, uid, frozen);
}
```

Framework 先冻结 Binder 接口并冲刷待处理事务，再应用进程 freezer。解冻时先查询 Binder frozen 信息；若冻结期间收到同步事务，AOSP 会终止目标进程，避免调用方无限等待。随后 Framework 解冻 Binder，再撤销进程 freezer。这个顺序是 AOSP cached freezer 与简单 SIGSTOP 的主要工程差别。

### 默认值、覆盖项与豁免

`android-17.0.0_r1` 的基线如下：

- `CachedAppOptimizer.DEFAULT_USE_FREEZER = true`；
- `config_defaultFreezerDebounceTimeout = 10000` 毫秒；
- `Settings.Global.CACHED_APPS_FREEZER_ENABLED` 可写入 `enabled` 或 `disabled` 覆盖策略；
- `activity_manager_native_boot/use_freezer` 与 `freezer_debounce_timeout` 可通过 DeviceConfig 调整；
- 设备还要通过 `Freezer.isFreezerSupported()` 的内核能力检查。

这组默认值仍允许产品 overlay 和运行配置调整。Android 官方文档还列出文件锁、`BIND_WAIVE_PRIORITY` 绑定等豁免。应用进入 cached bucket 后是否在十秒左右冻结，要以目标 build 的 dumpsys 和事件记录确认。

### 如何确认设备发生了冻结

下面的只读命令用于核对开关、AOSP 统计和事件日志。

```bash
# DeviceConfig 中未设置时，AOSP 会回到源码默认值
adb shell device_config get activity_manager_native_boot use_freezer

# 开发者选项使用的全局覆盖值：enabled、disabled 或 null
adb shell settings get global cached_apps_freezer

# CachedAppOptimizer 会打印 use_freezer、debounce timeout 和 Apps frozen
adb shell dumpsys activity | sed -n '/Freezer settings/,+20p'

# AOSP EventLogTags 中的冻结与解冻事件
adb logcat -b events -s am_freeze am_unfreeze
```

`device_config get` 返回 `null` 不表示功能关闭；源码默认值仍可能生效。`Apps frozen` 来自 `CachedAppOptimizer.mFrozenProcesses`，比“线程一段时间没跑”更有判别力。

在 userdebug/root 设备上，还可以检查 Android 17 r1 的 pid 级 cgroup 文件。下面的 uid 和 pid 仅作路径示例。

```bash
adb shell su 0 cat /sys/fs/cgroup/apps/uid_10123/pid_23456/cgroup.freeze
adb shell su 0 cat /sys/fs/cgroup/apps/uid_10123/pid_23456/cgroup.events
```

量产 user build 通常不允许 shell 读取这些节点，厂商也可能通过 task profile overlay 改变布局。读不到节点只能说明权限或路径不匹配，不能据此判定 freezer 关闭。

Perfetto 中可结合 `Freezer` atrace track、进程调度 slice、`am_freeze`/`am_unfreeze` 事件以及 Android 17 的 freezer TrackEvent 判断。线程长期没有 slice 也可能处于正常睡眠，必须与显式状态证据互证。

## 预加载、USAP 与预测启动

### Zygote 预加载

Zygote 在系统启动时读取 `/system/etc/preloaded-classes`，并预加载 Framework 类、资源和部分 native 库。fork 后的应用进程通过写时复制共享未修改页面。扩大预加载集合可能减少应用启动期类加载，也会增加 Zygote 启动工作、常驻共享页和脏页风险。某个应用的业务类通常不在系统 Zygote 的通用预加载集合里。

修改 `frameworks/base/config/preloaded-classes` 前，应在干净开机与多应用场景中同时衡量：

- Zygote preload 时长；
- system_server ready 时间；
- Zygote PSS、共享页和应用私有脏页；
- 多个代表应用的 TTID/TTFD；
- 低内存设备上的重启与 swap。

只优化一个头部应用，可能把成本分摊给每次开机和每个应用进程。

### USAP Pool 预先完成的是 fork

USAP 是已经从主 Zygote 或次 Zygote fork、尚未专门化为某个应用的进程。进程启动请求满足条件时，`ZygoteProcess` 连接 USAP socket，把 uid、gid、SELinux、数据目录和运行参数交给池成员；池成员通过 `Zygote.specializeAppProcess()` 完成专门化。

下面的 r1 判断代码说明 USAP 需要同时满足支持、启用、策略和命令参数四项条件。

```java
// ZygoteProcess.java @ android-17.0.0_r1
private boolean shouldAttemptUsapLaunch(
        int zygotePolicyFlags, ArrayList<String> args) {
    return mUsapPoolSupported
            && mUsapPoolEnabled
            && policySpecifiesUsapPoolLaunch(zygotePolicyFlags)
            && commandSupportedByUsap(args);
}
```

主/次 Zygote 支持 USAP，child Zygote 不支持。策略只把 latency-sensitive、非 system process 的合格请求送入 USAP；需要 wrapper、启动 child Zygote、预加载包等参数会退回普通 Zygote 路径。`ZygoteConfig.USAP_POOL_ENABLED_DEFAULT` 在 Android 17 r1 中仍为 `false`，池容量基线为最少 1、最多 3，产品可以通过 runtime_native DeviceConfig 或 `dalvik.vm.*` 属性覆盖。

可以用以下属性读取区分“源码支持”和“当前 build 已启用”。

```bash
adb shell getprop dalvik.vm.usap_pool_enabled
adb shell device_config get runtime_native usap_pool_enabled
```

两处都为空时，Android 17 r1 回到 `false` 默认值。Trace 中的 `Zygote:FillUsapPool` 可以证明填池动作；某次启动缺少普通 Zygote fork 仍需结合 pid 出生时间和 USAP 专门化路径确认，不能直接标记成厂商预测启动。

### 预测启动要拆成动作验证

“智能预测下一应用”描述的是决策输入，不说明执行动作。产品可能基于时间、位置、前一应用、使用频率或桌面交互做预测，命中后可以选择：

- 提前完成 ART 编译或 profile 维护；
- 预取文件页或资源；
- 保留已有 cached 进程；
- 填充通用 USAP 池；
- 创建产品私有的预热进程；
- 调整短时调度或 I/O 优先级。

这些动作的成本差异很大。提前创建目标应用进程还涉及组件生命周期、权限、存储解锁、隐私和内存压力，不能仅凭“点击后很快”推断存在。

验证预测策略时，应设计命中组和未命中组，固定网络、温度、编译状态与 page cache 条件，并记录预测发生前后的进程、I/O、CPU 和内存。只有产品文档、系统日志或逆向到的调用链能给出策略身份；Trace 主要负责证明动作及效果。

## 后台治理：在系统契约内选择工作类型

后台治理要在三个目标之间取舍：用户可感知功能的连续性、延迟任务的完成率、整机功耗与内存。AOSP 已经提供 Doze、App Standby buckets、后台执行限制、JobScheduler、AlarmManager、foreground service 和 cached freezer。OEM 可以在兼容性约束内配置产品策略，也可能因实现缺陷造成额外延迟或进程终止。

品牌和地区无法替代设备证据。同一品牌的不同系统版本、机型、内存档位、用户省电设置和应用使用频率都可能触发不同结果。用“某厂商一定杀后台”指导代码，会把排障变成长期维护的例外集合。

### App 应该怎样选 API

| 工作 | 推荐入口 | 约束 |
|---|---|---|
| 离开页面即可取消的进程内任务 | coroutine / executor | 进程终止后任务消失 |
| 需要跨进程重启继续的可延期任务 | WorkManager | 受约束、配额与系统调度影响，不承诺精确时刻 |
| 平台级任务调度控制 | JobScheduler | 需要正确声明网络、充电、idle 等条件 |
| 用户指定时刻的提醒 | AlarmManager | 精确闹钟受权限和政策约束 |
| 用户持续可感知的工作 | foreground service | 类型、权限、后台启动和超时均受版本限制 |
| 消息送达 | 平台可用的推送通道 | 推送唤醒后仍要遵守后台启动规则 |

Foreground service 只适合用户能持续感知的工作。Android 12 起限制后台启动 FGS，Android 14 起进一步校验类型与 while-in-use 权限。它不能作为“所有后台任务最稳”的替代品。持久、可延期任务优先使用 WorkManager；要求精确用户提醒时再评估 AlarmManager。

厂商推送通道属于产品集成选项。是否需要接入要按目标市场、系统服务可用性、送达率与隐私要求决策。普通应用也不应依赖互拉进程、静音音频、透明 Activity 或周期性自唤醒绕过系统策略。

### 区分正常约束和产品偏差

下面的命令用于收集后台状态。包名要替换为待测应用。

```bash
adb shell am get-standby-bucket com.example.app
adb shell dumpsys jobscheduler com.example.app
adb shell dumpsys deviceidle
adb shell cmd appops get com.example.app RUN_ANY_IN_BACKGROUND
adb shell dumpsys package com.example.app
```

这组输出分别覆盖 standby bucket、JobScheduler、Doze、后台运行 AppOp 和包配置。它们要与 `ApplicationExitInfo`、logcat、Perfetto 和服务端请求日志按时间对齐。任务延迟可能来自约束未满足、配额、Doze、网络、进程退出或应用异常，不能只看“预定时间没执行”就归因给 OEM。

若设备行为偏离公开 SDK 契约，建议准备最小复现、系统 build 信息、完整 bugreport、Trace 和同版本对照机结果。此类材料比要求用户手动加入白名单更容易定位问题，也能区分产品设计与系统缺陷。

## 一套可复用的 OEM 归因流程

### 1. 固定实验条件

记录机型、内存档位、`ro.build.fingerprint`、安全补丁、目标 SDK、安装来源、温度、刷新率、电量、网络和省电模式。启动实验还要固定编译状态、进程状态和缓存状态。

### 2. 建立 AOSP 17 基线

从 `android-17.0.0_r1` 找到负责决策的 Framework/Native 入口；涉及内核时再对 `android17-6.18-2026-06_r6`。记录基线默认值、可覆盖项和事件输出，避免用旧版本属性解释 Android 17。

### 3. 读取目标设备配置

优先查 Settings、DeviceConfig、resource overlay、task profiles、系统属性、HAL 服务和内核配置。user build 无法读取的内容应标成未知，不用猜测填补。

### 4. 让 Trace 证明动作

围绕问题定义时间窗口和因果链：

- 启动：输入事件 → Activity 启动 → 进程创建/专门化 → `bindApplication` → 首帧；
- 掉帧：应用 deadline → runnable/运行 → GPU fence → SF/HWC → present；
- 后台：组件退入后台 → procstate/adj → freezer 或 kill → 下一次唤醒；
- 功耗：工作负载 → 调度/频率 → idle residency → Thermal severity → 性能变化。

### 5. 做层级消融

能控制的情况下，逐项切换刷新率、省电模式、游戏模式、开发者 freezer 选项或应用后台设置。每次只改一个变量，并恢复到同一热状态。一次切换多个开关，无法确认收益归属。

### 6. 给结论标注证据等级

- **L1：源码与运行证据一致。** 可以描述调用链和目标 build 的行为。
- **L2：官方文档或产品配置，加上运行证据。** 可以描述可观察策略，内部实现仍需保留。
- **L3：仅有 Trace 现象或用户反馈。** 只记录现象与候选原因，不命名私有机制。

## 常见误判

### “进程还在，所以应用可以继续工作”

cached 进程可能已被冻结，也可能没有调度机会；它还可能在内存压力下被终止。后台工作要依赖组件状态和公开调度 API，不能依赖进程恰好存活。

### “启动 Trace 没看到 fork，所以系统预启动了应用”

目标进程可能早已存在，也可能来自 USAP、App Zygote，或者 Trace 窗口漏掉了进程创建。应核对 pid 的创建时间、父进程、`bindApplication` 和 USAP 状态。

### “CPU 上了大核，所以应用命中了白名单”

EAS、uclamp、top-app cpuset、任务利用率、idle 状态、IRQ 和热限制都能影响 CPU 选择。需要额外配置或厂商调用链，才足以命名白名单策略。

### “冻结能省内存”

freezer 的直接作用是停止执行。匿名页是否被压缩、换出或回收，取决于后续 compaction、ZRAM 和内存压力。冻结保留的进程也会继续占用页表、内核对象和未回收页面。

### “加入电池白名单能修复所有后台问题”

白名单只改变特定电源限制，无法修复错误的 WorkManager 约束、FGS 类型、权限、服务端推送、网络失败或应用崩溃。不同设备对用户设置的名称和影响范围也可能不同。

## 版本演进到 Android 17

| 版本 | 对 OEM 性能策略的影响 |
|---|---|
| Android 5.0 / 6.0 | ART、JobScheduler、Doze 和 App Standby 逐步建立编译与后台任务基线 |
| Android 8.0 | 后台服务和隐式广播限制趋严，应用需要迁移到受调度的后台工作 |
| Android 9 | App Standby buckets 与 Adaptive Battery 让使用频率进入资源分配 |
| Android 11 | AOSP 支持 cached apps freezer，cgroup v2 freezer 成为系统冻结基础 |
| Android 12 | 后台启动 foreground service 受到明确限制 |
| Android 14 | cached 进程通常在进入 cached 状态十秒后冻结；动态注册广播可排队到解冻后，FGS 类型和权限约束继续细化 |
| Android 17 / API 37 | r1 基线中 freezer 默认开启且带 Binder 协调，默认 debounce 为十秒；USAP 代码保留但默认关闭，产品差异仍需读取配置确认 |

版本演进可以保留历史语境，排查当前设备时仍要回到 Android 17 的源码和目标 build。旧版属性名、私有 sysfs 节点和早期厂商方案不能直接套用到 API 37。

## 源码与官方资料

### Android 17 / API 37 源码

- [`CachedAppOptimizer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java)：开关、延迟、Binder 协调、冻结与解冻状态机。
- [`Freezer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/Freezer.java)：Framework freezer 包装层。
- [`Process.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Process.java) 与 [`android_util_Process.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/jni/android_util_Process.cpp)：pid 级 Frozen/Unfrozen profile 入口。
- [`config.xml`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/res/values/config.xml)：freezer debounce 的 AOSP 基础资源值。
- [`task_profiles.json`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/libprocessgroup/profiles/task_profiles.json)：`FreezerState` 与 Frozen/Unfrozen profile。
- [`ZygoteInit.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/ZygoteInit.java) 与 [`preloaded-classes`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/config/preloaded-classes)：Zygote 预加载入口和类清单。
- [`ZygoteConfig.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/ZygoteConfig.java)、[`ZygoteServer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/ZygoteServer.java) 与 [`ZygoteProcess.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/ZygoteProcess.java)：USAP 默认值、填池、启动资格和 child Zygote 边界。

### Android 17 kernel 6.18 源码

- [`kernel/sched/fair.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/fair.c)：EAS 的候选 CPU 与能耗估算。
- [`kernel/sched/cpufreq_schedutil.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/cpufreq_schedutil.c)：schedutil governor。
- [`Documentation/scheduler/sched-energy.rst`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/scheduler/sched-energy.rst)：Energy Model 与 EAS 的约束。
- [`Documentation/admin-guide/cgroup-v2.rst`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/admin-guide/cgroup-v2.rst)：`cgroup.freeze` 与 `cgroup.events` 语义。

### 官方行为文档

- [Cached apps freezer](https://source.android.com/docs/core/perf/cached-apps-freezer)
- [Background work](https://developer.android.com/develop/background-work)
- [Task scheduling / WorkManager](https://developer.android.com/develop/background-work/background-tasks/persistent)
- [Foreground services](https://developer.android.com/develop/background-work/services/fgs)
- [Thermal mitigation](https://source.android.com/docs/core/power/thermal-mitigation)
- [Power and performance management](https://source.android.com/docs/core/power/performance)
