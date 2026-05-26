---
title: "系统启动全流程"
chapter: "1.2"
section: "1.2"
status: ready-for-review
pipeline_stage: task6_pending
drafted_date: "2026-03-30"
drafted_by: openclaw-task2a
reviewed_date: "2026-05-06"
reviewed_by: openclaw-task6
review_type: task6-writing-quality-review
task6_state: revisiting
task6_result: pass-light-edit
task6_reviewed_date: "2026-05-06"
task2b_state: fixed
task2b_result: fixed-lite
task9_state: pending
task9_result: needs-rework
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-05-19
last_task9_at: "2026-05-19T22:20:00+08:00"
last_task2b_at: "2026-05-06T16:04:00+08:00"
last_task2b_lite_at: "2026-05-27"
review_v2_fix: "误区 section boot_completed 事件描述修正 + 事件排序修正"
polish_count: 1
polish_date: "2026-04-05"
polish_by: task2b-polish
applicable_versions: "Android 8 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-17"
last_verified_against: "AOSP android-16.0.0_r1, source.android.com 官方文档"
confidence: high
last_task9_review_log: logs/deep-review/2026-05-19-22-audit.md
sources:
  - type: aosp
    path: "system/core/init/first_stage_init.cpp @ android-16.0.0_r1"
  - type: aosp
    path: "system/core/init/init.cpp @ android-16.0.0_r1"
  - type: aosp
    path: "system/core/rootdir/init.rc @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/config/preloaded-classes @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/ZygoteInit.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/utils/TimingsTraceAndSlog.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/java/com/android/server/SystemServer.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/EventLogTags.logtags @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/EventLogTags.logtags @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/UserController.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityTaskManagerService.java @ android-16.0.0_r1"
  - type: aosp
    path: "system/core/bootstat/bootstat.cpp @ android-16.0.0_r1"
  - type: aosp
    path: "hardware/interfaces/cas/aidl/default/cas-default-lazy.rc @ android-16.0.0_r1"
  - type: official
    path: "https://source.android.com/docs/core/architecture"
  - type: official
    path: "https://source.android.com/docs/core/boot"
  - type: official
    path: "https://source.android.com/docs/core/perf/boot-times"
  - type: blog
    path: "obsidian/Cubox/Android 启动系列之我是 init 进程 - 掘金-2024-01-27.md"
tags:
  - boot
  - init
  - zygote
  - SystemServer
  - 启动优化
  - bootchart
  - bootloader
  - preloaded-classes
  - boot-timings
related_chapters:
  - "1.1"
  - "1.3"
  - "1.4"
  - "1.5"
  - "1.7"
  - "8.2"
  - "1.11"
  - "8.3"
review_notes: "2026-05-06T16:04 Task2B：P0 module.layout 修正为 modules.load / BOARD_VENDOR_KERNEL_MODULES_LOAD / BOARD_VENDOR_RAMDISK_KERNEL_MODULES_LOAD + MODULE_SOFTDEP() + async_probe=1。送 Task6 复审。 | 2026-05-06 task6 re-review: frontmatter 去重并修复 YAML；UserController source 与正文/参考资料一致；完成 L1/L2 轻量文风修订；task9 待复审 task2b 修复后的技术问题。 | 2026-05-06 16:24 Task6：Task2B 修复后写作复审；清理大纲口语化表述，无新增 L3/L4 回炉项，送 Task9 复审。"
task9_review_notes: "2026-05-06 16:39 task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 4。 | 2026-05-19 22:20 闲时抽检：bootstat 命令参数错误。 | 2026-05-20 03:17 Task2B 修正：bootstat -l→-p。"
last_task6_at: "2026-05-18T17:14:29+08:00"
last_task6_audit: "2026-05-18"
last_task6_audit_result: pass-no-edit
task6_review_notes: "2026-05-06 16:24 Task6：Task2B 修复后写作复审；清理大纲口语化表述，无新增 L3/L4 回炉项，送 Task9 复审。"
last_task6_review_log: "logs/review/2026-05-06-16-review.md"
last_task9_audit: "2026-05-19"
last_task9_audit_result: needs-rework
---

# 系统启动全流程

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 完整启动链：Bootloader → Linux Kernel → first-stage init → second-stage init → Zygote → SystemServer → Home / boot completed
- 🔹 init 进程的职责：解析 init.rc、启动关键 native 服务（servicemanager、surfaceflinger 等）
- 🔹 Zygote 预加载机制：preloadClasses / preloadResources，对首次 App 启动的影响
- 🔹 SystemServer 启动的核心服务顺序及依赖关系（AMS、WMS、PMS 等）
- 🔹 启动时间的度量：boot_completed 广播、TimingsTraceLog
- 🔹 开机性能优化的常见手段（task_profiles、lazy HAL、odsign / dexpreopt、启动长尾治理）

### 扩展（可选深入）

- 🔸 AB 分区与 Virtual A/B 对 OTA 和启动时间的影响
- 🔸 dm-verity / AVB 对启动链的安全与性能权衡
- 🔸 各厂商 boot 启动优化策略概述

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 Android 启动流程

当我们按下手机电源键，到看到桌面图标可点击，中间经历了一条长长的时间线。这条时间线涉及硬件初始化、内核启动、用户空间构建、Java 运行时准备、系统服务启动，最终才把一个可用的 Android 桌面呈现在我们面前。

了解这条启动流程的意义远不止"知道就行"。在实际的性能优化工作中，启动流程中的每一个环节都可能成为瓶颈：

- 开机时间太长——用户抱怨"等半天才能用"。这可能是 init 阶段挂载分区慢了，也可能是 SystemServer 启动了太多不必要的服务。
- 冷启动 App 慢——这和 Zygote 的预加载机制直接相关。了解预加载了什么、没预加载什么，才能判断 App 启动时哪些类需要重新加载。
- OTA 升级后首次开机特别慢——这与 dm-verity 校验和 AB 分区切换有关。

在 Perfetto 中，我们可以抓取开机阶段的 Trace，看到 init、Zygote、SystemServer 各自消耗了多少时间。但如果不了解这条启动时间线的来龙去脉，面对 Trace 中的那些色块，只会一头雾水。读完本节后，我们就能打开一份开机 Trace，准确地找到每个阶段对应的区间，并定位到耗时异常的环节。

## 完整启动链：从按下电源到桌面可见

把 Android 开机过程画成一条直线时，最容易丢掉三个节点：first-stage init、Home 首帧可见、boot completed 广播。节点丢了，Trace、logcat 和 bootstat 就对不上。按 android-16.0.0_r1 的实现，主链更接近下面这样：

```
[图：Android 启动全流程时序图]
Boot ROM → Bootloader → Linux Kernel → first-stage init → second-stage init
→ zygote-start → Zygote → SystemServer → ActivityManagerService.systemReady()
→ startHomeOnAllDisplays() → Home 首帧可见 → LOCKED_BOOT_COMPLETED → BOOT_COMPLETED
```

### Boot ROM 与 Bootloader：硬件引导的前两跳

按下电源键后，CPU 先执行芯片内置的 Boot ROM。它负责做最小硬件初始化，并把控制权交给 Bootloader。Bootloader 再完成更完整的板级初始化，装载 kernel、ramdisk、device tree，处理 Verified Boot / 分区选择，然后跳入 Linux Kernel。

这一段通常不在 Perfetto 里直接可见。要分析 Bootloader 本身的耗时，更多还是依赖厂商日志、串口和 bootstat 的外围里程碑。

Android 16 起强烈建议 ARM64 设备部署 Google 审计的 GBL（Generic Bootloader）参考实现。GBL 定义了统一的 Bootloader 行为规范，`bootstat` 支持的 `boottime.bootloader.*` 系列属性是 Bootloader 上报的耗时项。跨设备比较前仍需确认 Bootloader 是否按 GBL 规范上报——未采用 GBL 的设备上，这些属性的口径可能仍然不同。

### Linux Kernel：把调度器、驱动和最小用户态入口拉起来

Kernel 阶段负责建立页表、初始化调度器、内存管理和关键驱动，然后创建 PID 1 的 `/init`。这里要把边界拆清楚：Kernel 会准备 rootfs / ramdisk 和最小设备节点，但 system、vendor、product 这些启动必需分区的 early mount，在现代 Android 里属于 first-stage init，不该写进 Kernel 阶段。

Linux 侧最早的进程关系仍然成立：PID 0 是 swapper，`rest_init()` 会拉起 PID 1 的 init 和 PID 2 的 kthreadd。对启动分析来说，Kernel 阶段的结束标志更适合看“控制权何时进入 `/init`”，而不是“system 分区何时挂好”。

Android 官方的 boot-time optimization 文档强调两个 Kernel 阶段优化手段：选择性异步驱动探针（`module_name.async_probe=1` 通过 kernel cmdline 或模块参数标注非启动必需的驱动模块）和模块加载顺序控制（由 `modules.load`、`BOARD_VENDOR_KERNEL_MODULES_LOAD`、`BOARD_VENDOR_RAMDISK_KERNEL_MODULES_LOAD` 配合 `MODULE_SOFTDEP()` 声明的模块依赖关系共同决定 ko 加载顺序）。GKI 6.12 的 defconfig 中 `CONFIG_MODULES=y` 已默认启用，OEM 可以通过 `/vendor/etc/init/hw/init.hardware.rc` 调整模块加载时机，将非关键驱动的 probe 推迟到 `boot` phase 之后。这两项手段可以通过 dmesg 中驱动的 probe 日志和模块 init/load 顺序确认是否生效，也可以用 ftrace 的 `initcall` / `module` 事件追踪具体驱动的 probe 耗时。

### init：分 first-stage 和 second-stage 两段看

现代 Android 的 init 不能只写成一句“解析 init.rc”。android-16.0.0_r1 的 `init/first_stage_init.cpp` 在早期用户空间会先做几件事：

- 挂载 `/dev`、`/proc`、`/sys` 和 `selinuxfs`
- 建最小设备节点和日志环境
- 调用 `FirstStageMount::DoFirstStageMount()` 挂载启动必需分区
- SELinux 策略文件从 `/sepolicy` 或 vendor/odm overlay 加载到内核，policy load 本身是 first-stage 之后的耗时操作之一，通常占用数十到数百毫秒，具体取决于策略规则数量和硬件 I/O 速度。这一步对开机时间的影响在启用大量 OEM 自定义 SELinux 策略时会更加明显 [待验证：具体设备上的分段耗时]
- `SwitchRoot()` 到新根文件系统，再进入 second-stage init

这一段完成后，second-stage init 才会开始解析 rc 配置。`init.cpp` 默认读取 `/system/etc/init/hw/init.rc`，并继续解析 `/system/etc/init`、`/system_ext/etc/init`、`/vendor/etc/init`、`/odm/etc/init`、`/product/etc/init`（按 `init.cpp` `ParseConfig` 顺序）。product 分区承载产品侧服务和属性配置，启动排查时遗漏会导致服务来源归因不完整。随后 action queue 依次推进 `early-init`、`init`、`late-init`、`post-fs-data`、`zygote-start`、`boot` 等阶段。

`zygote-start` 也是一个独立节点。AOSP `rootdir/init.rc` 会在这个触发点先等待 `odsign.verification.done=1`，再执行 `start zygote` / `start zygote_secondary`。把 `post-fs-data`、`zygote-start`、`boot` 混写成一个“init 阶段”后，很多启动长尾问题就没法定位了。

### Zygote：把 Java 世界的公共准备工作提前做好

Zygote 的目标还是老问题，减少每个 App 冷启动都重复做的基础工作。它会预加载类、资源、共享库，再通过 fork 把这份运行时状态复制给 SystemServer 和 App 进程。

有一个常见旧说法需要修正。老文章常把 preloaded classes 写成“3000-4000 个常用类”。android-16.0.0_r1 的 `frameworks/base/config/preloaded-classes` 去掉注释和空行后有 18431 条，打包产物会进入 ART APEX 提供的 preloaded-classes 文件。老数字放在 Android 8/9 的上下文里还勉强能看，直接拿到新分支会偏差很大。

fork 之后依赖的仍然是 Copy-on-Write。共享页不写就不复制，所以 SystemServer 和 App 进程能复用 Zygote 已经装好的大量类与资源。启动慢到 `Application.onCreate()` 之前时，先看 Zygote 预加载、dexpreopt / odsign 产物是否命中，再看业务进程自己的初始化。

### SystemServer：按真实阶段看服务归属

`SystemServer.run()` 在入口先写 `BOOT_PROGRESS_SYSTEM_RUN`，然后依次执行：

- `startBootstrapServices(t)`
- `startCoreServices(t)`
- `startOtherServices(t)`
- `startApexServices(t)`

这四段的服务归属要按 AOSP 代码来写。

**Bootstrap services** 里有最重的一批基础框架服务，包括 `ActivityTaskManagerService`、`ActivityManagerService`、`PowerManagerService`、`LightsService`、`DisplayManagerService`、`PackageManagerService`。AMS / ATMS 属于这里，不属于 other。

**Core services** 里是第二层基础服务，典型例子有 `BatteryService`、`UsageStatsService`、`WebViewUpdateService`。这些服务依赖前一层基础服务，但还没到窗口和输入这一层。

**Other services** 里才会启动 `InputManagerService`、`WindowManagerService`、`AlarmManagerService`、`JobSchedulerService`、`NotificationManagerService` 等更大一包服务。WMS 和 InputManagerService 属于这一段。`SensorService` 也不是这里直接 new 出来的 Java service，SystemServer 只是通过 `PHASE_WAIT_FOR_SENSOR_SERVICE` 等待相关前置条件，再继续启动 WMS。

`startApexServices(t)` 在 Android 13 引入。APEX 模块化从 Android 10 开始，但独立的 apex services 启动阶段在 `SystemServer.java` 中直到 Android 13 才出现（对比 `android-12.0.0_r34` / `android-12.1.0_r27` 均无此方法）。写文章时最好直接注明“本文按 android-16.0.0_r1 观察到的阶段顺序”，少做未经核对的版本断言。

**启动流程的版本差异（Android 12-16 关键变更）**

启动链的主干在不同版本间是稳定的，但几个关键变化会影响分析方式：

- **Android 13**：引入 `startApexServices()` 独立阶段，APEX 模块（ART、Media 等）可以在开机阶段独立更新，不再随 system 分区整体升级。ART APEX 的更新会直接影响 Zygote 预加载的 dexpreopt 产物路径。
- **Android 13**：Perfetto 的 boot trace 配置改进，增加了更多 init 阶段的 atrace hook。
- **Android 15**：Cloud Profiles 作为 Mainline 模块推送给设备，首次启动时编译产物可能依赖云端下发的 profile，不再只依赖本地 Baseline Profile。OTA 后首启的 dex2oat 策略随之变化。[待验证：Cloud Profiles 对 Pixel 设备首启耗时的量化影响]
- **Android 16**：profileable build 配置的变化影响 Zygote 预加载的命中路径；AutoFDO（Automatic Feedback-Directed Optimization）与 Baseline Profile 协同优化，对冷启动有额外改善。具体数据参见 8.3 节。
- **Android 16（Cloud Compilation / SDM）**：Google Play 在应用安装和更新场景下向设备分发预编译的 `.odex` / `.vdex` 产物（Software Distribution Manager, SDM），减少安装时本地 `dex2oat` 的 CPU 开销，对低端设备的安装体验改善明显。公开资料目前只覆盖应用侧的安装和更新流程；系统 OTA 后首次开机是否也走 SDM 通道，尚无公开 AOSP 或官方文档支撑，不应把 SDM 等同于"OTA 后全机免编译"。

如果分析对象是 Android 12 及之前的设备，`startApexServices()` 不存在，apex 组件的启动混在其他阶段里。

### Home 首帧可见、LOCKED_BOOT_COMPLETED、BOOT_COMPLETED 要拆开

系统服务就绪后，`ActivityManagerService.systemReady()` 会在 system user 路径里调用 `mAtmInternal.startHomeOnAllDisplays(currentUserId, "systemReady")`，把 Home Activity 拉起来。这个节点对应“系统开始尝试显示桌面”。

Home 首帧可见，要再往后看 Launcher 自己的渲染和 SurfaceFlinger 合成。用户此时已经能看到桌面，但广播尾声还没结束。

`ACTION_LOCKED_BOOT_COMPLETED` 和 `ACTION_BOOT_COMPLETED` 都由 `UserController`（`frameworks/base/services/core/java/com/android/server/am/UserController.java`）负责发送。前者发生在用户进入 running locked 阶段，适合 Direct Boot aware 组件；后者要等用户解锁、CE storage 可用之后才发。`UserManagerService` 只负责用户信息与状态管理，不承担 boot completed 广播。这两个广播都不等同于 Launcher 首帧，更不等同于“SystemServer 启动完自动同步收尾”。

[待补充：一张同时标出 systemReady、Home 首帧、LOCKED_BOOT_COMPLETED、BOOT_COMPLETED 的 Trace / logcat 对照图]

## 启动时间的度量

开机时间排查最好同时看 event log、bootstat、Perfetto 和 dmesg。四种信号关注的里程碑不同，混成一个数字后，问题会越看越乱。

### boot completed 广播

`ACTION_LOCKED_BOOT_COMPLETED` 和 `ACTION_BOOT_COMPLETED` 都是 `UserController` 这一侧的用户生命周期广播，不是 Launcher 的 UI 里程碑。

- `ACTION_LOCKED_BOOT_COMPLETED`：用户进入 running locked 阶段后发送，Direct Boot aware 组件可以在这里开始工作。
- `ACTION_BOOT_COMPLETED`：用户解锁、CE storage 可用后发送。

所以“桌面已经出现”并不等于 `BOOT_COMPLETED`。如果我们关心的是用户第一次看到可操作桌面，应该盯 Home 首帧和 `boot_progress_enable_screen` 附近的事件；如果我们关心的是系统广播长尾和应用收尾初始化，才去看 `LOCKED_BOOT_COMPLETED` / `BOOT_COMPLETED`。

### bootstat 工具

`bootstat` 仍然是快速看分段耗时的第一入口，源码在 `system/core/bootstat/bootstat.cpp`。它的价值不在“给一个总耗时”，而在于把关键节点打散成可比较的时间戳。

```bash
adb shell bootstat -p
```

这一步适合先做粗定位：Bootloader / Kernel 慢，还是 Framework 慢，还是用户解锁后的广播尾部长。

### TimingsTraceLog 与 TimingsTraceAndSlog：框架内置的两套秒表

#### TimingsTraceLog：盯 Zygote 预加载

ZygoteInit 在预加载阶段使用 `android.util.TimingsTraceLog`（Zygote 侧的计时工具，变量名 `bootTimingsTraceLog`，trace tag 如 `Zygote64Timing` / `Zygote32Timing`）。常见 slice 包括 `PreloadClasses`、`PreloadResources`、`PreloadSharedLibraries`、`PreloadOpenGL` 等。分析“开机还没到 SystemServer 就已经拖很久”的问题时，先看这里。

如果 `PreloadClasses` 明显变宽，就去核对 preloaded-classes、ART APEX、odsign / dexpreopt 产物；如果 `PreloadResources` 变宽，再查资源包和字体加载。

#### TimingsTraceAndSlog：盯 SystemServer 各阶段

SystemServer 用的是 `TimingsTraceAndSlog`。在 Perfetto 里，`StartServices` 会包住四个大阶段：

- `startBootstrapServices`
- `startCoreServices`
- `startOtherServices`
- `startApexServices`

排查方法很直接：先看哪一段最宽，再钻进那一段找具体服务。AMS / PMS 拉长，问题多半在 bootstrap；WMS / InputManagerService 拉长，通常在 other；APEX service 拉长，就去看主线模块化服务和 updatable 组件。

#### boot_progress 里程碑事件

`boot_progress_*` 事件要按源码语义解释，不要拿名字脑补。

- `boot_progress_system_run`：`SystemServer.run()` 入口写入，表示 system_server 已进入主运行流程，不表示“SystemServer 全部准备就绪”。
- `boot_progress_pms_start` / `boot_progress_pms_ready`：PMS 启动与就绪。
- `boot_progress_ams_ready`：`ActivityManagerService.systemReady()` 开始。
- `boot_progress_enable_screen`：`ActivityTaskManagerService` 调用 `enableScreenAfterBoot()`，随后让 WMS 去 enable screen。它不等于 Launcher 首帧完成。

因此，`boot_progress_enable_screen` 到桌面稳定可交互之间，仍然可能隔着 Launcher 绑定、首帧渲染、Widget 恢复和广播尾部处理。

### dmesg 与 logcat

Kernel 和 early userspace 的问题，先看 `dmesg`；Framework 里程碑和广播尾部，更多靠 `logcat -b events`。

```bash
adb shell dmesg | head -80
adb logcat -b events | grep boot_progress
```

这组命令适合和 bootstat 对照着看。dmesg 里 I/O、dm-verity、驱动初始化拖长，通常早于 Framework；events buffer 里 `boot_progress_*` 拉长，则更多是 system_server 之后的问题。

### Perfetto：区分“开机后抓取”和“重启全过程抓取”

直接在 adb shell 里启动 perfetto，tracing 会从 adb 会话建立之后才开始。用这种方式抓 Trace，目标应该写成“second-stage init 之后，尤其是 Zygote / SystemServer / Launcher 这段”，不要把它写成覆盖 Boot ROM、Bootloader 和整个 Kernel early boot 的完整开机 Trace。

```bash
adb shell perfetto -c - --txt -o /data/misc/perfetto-traces/boot-userspace.pftrace <<'EOF'
buffers: {
  size_kb: 65536
}
data_sources: {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_wakeup"
      ftrace_events: "sched/sched_wakeup_new"
      atrace_categories: "am"
      atrace_categories: "wm"
      atrace_categories: "view"
      atrace_categories: "gfx"
      atrace_categories: "dalvik"
    }
  }
}
duration_ms: 30000
EOF
adb pull /data/misc/perfetto-traces/boot-userspace.pftrace .
```

如果目标是完整 reboot trace，就要在重启前准备专门的 boot tracing 方案，或者结合 bootstat、dmesg、事件日志来拼接时间线。单靠上面这条 adb 命令，结论只能覆盖用户态后半段。

## 开机性能优化的常见手段

开机优化别从“招数列表”开始。更稳的做法是先把慢点钉在具体阶段，再决定动作。对启动链来说，常见的慢点大致分成四段。

> **参考基线数据（Pixel 8, Android 16, 典型冷启动，仅供分段比例参考）**
>
> | 阶段 | 典型耗时 | 占比 | 说明 |
> |------|----------|------|------|
> | Bootloader | ~2-3s | 5-8% | 厂商差异大，依赖 SoC 和板级配置 |
> | Kernel | ~3-5s | 10-15% | 驱动初始化、dm-verity |
> | first-stage init | ~1-2s | 3-5% | early mount、SELinux policy load |
> | second-stage init | ~2-4s | 5-10% | rc 解析、核心 native 服务 |
> | Zygote 预加载 | ~5-8s | 15-20% | 18431 类 + 资源 + 共享库 |
> | SystemServer | ~8-12s | 25-35% | 四段 StartServices |
> | Home 首帧 + 广播长尾 | ~5-10s | 15-25% | Launcher 渲染 + BOOT_COMPLETED 尾声 |
>
> 数据来源：基于公开 bootstat 输出和 AOSP 默认配置的估算值，非严格 Benchmark。[待补充：Pixel 8 实测 bootstat 数据截图]

### 1. first-stage init / second-stage init：先看装载链和 early I/O

如果 bootstat、dmesg 或 init 相关日志显示慢点出现在 early mount、`post-fs-data`、`load_all_props` 之前后，排查方向通常是分区装载、文件系统、verity 校验和启动期 I/O。

这个阶段更有效的动作包括：

- 把非启动必需的数据准备，从 `post-fs-data` 往后挪到 `zygote-start` 或更晚的 boot phase
- 检查 OTA 后首启是否卡在 APEX 激活、odsign 校验、dexpreopt 产物缺失、snapshot merge 抢 I/O
- 减少必须在 early boot 读取的大文件和目录扫描

如果 trace 上 system_server 还没起来，问题大概率在更早的装载链上。

### 2. Zygote：预加载和编译产物命中率

Zygote 慢时，观察点是 `PreloadClasses`、`PreloadResources`、shared libraries 这些 slice。

这里常见的动作有两类：

- 预加载治理：不要把 OEM / 业务侧 jar 轻率塞进 preloaded-classes；加进去会缩短部分进程启动，但会抬高整机开机基线，还会增加常驻内存压力。
- 编译产物治理：核对 odsign、dexpreopt、profile 指导编译是否已经完成。OTA 后首启变慢，很多时候是编译产物尚未就绪，不是 Zygote 逻辑本身退化。

### 3. SystemServer：按服务依赖切割，能 lazy 就 lazy

如果 `StartServices` 很宽，下一步就看是 bootstrap、core、other 还是 apex services 拉长。定位到子阶段后，再决定是拆依赖、改启动时机，还是改服务形态。

lazy service 是这里最常见也最有效的一类动作。AOSP 的 `hardware/interfaces/cas/aidl/default/cas-default-lazy.rc` 就用了这套模式：

```rc
service vendor.cas-default-lazy /vendor/bin/hw/android.hardware.cas-service.example-lazy
    interface aidl android.hardware.cas.IMediaCasService/default
    class hal
    oneshot
    disabled
```

`interface ...` + `disabled` 说明它不是开机就常驻的服务，而是由 servicemanager 在客户端首次查找时拉起。这里没有所谓的“bind 类型服务”。写 HAL / AIDL 启动策略时，优先用 lazy service 这个真实机制来描述。

CPU 和 I/O 调度也别只盯着老文章里的 cpuset。新分支更常见的入口是 `task_profiles`，它把调度、uclamp、cpuset 等策略组合成 profile，再分配给具体服务。分析启动回归时，raw cpuset 写法和 task_profiles 都要查。

### 4. Home 首帧之后还有一段长尾

桌面可见只是“用户已经能看到东西”，还不是“启动链已经全部结束”。`LOCKED_BOOT_COMPLETED` / `BOOT_COMPLETED`、Widget 恢复、首次账号同步、包扫描补尾都可能拖在后面。

如果用户主观感知已经变快，但 boot completed 相关指标仍然长，就把这段单独看：哪些工作必须跟着广播走，哪些可以延到用户第一次打开某个功能时再做。

### 厂商经验单独写，不要冒充平台事实

厂商常见动作无非是调整分区布局、延后非关键服务、把 HAL 改成 lazy、优化预编译命中率、降低 OTA 首启的 I/O 冲突。没有公开配置、设备条件和测试口径时，文章里最好写成“某机型实测”或“厂商 release note 提到”，别直接写成 Android 平台统一事实，更别给一个孤立百分比。

## 扩展：AB 分区与 dm-verity 的影响

### AB 分区与 Virtual A/B

现代 Android 设备使用 AB 分区方案来实现无缝 OTA 更新。设备上有两套系统分区（A 和 B），更新在后台分区进行，重启时切换到新分区。

这对启动的影响：
- **正面**：OTA 后不需要在 recovery 模式下花时间安装，重启即可
- **负面**：需要额外的存储空间（Virtual A/B 通过快照技术缓解了这个问题），启动时 Bootloader 需要确认从哪个分区启动

[待补充：AB 分区切换流程图]

### dm-verity 与 AVB

[图：dm-verity 在启动链中的位置——Bootloader AVB 验证 → Kernel dm-verity 块级校验 → 用户空间]

dm-verity（Device Mapper Verity）是 Android 用于验证系统分区完整性的机制。AVB（Android Verified Boot）是更高层的验证框架。

在启动链中：
1. Bootloader 验证 Kernel 和 initramfs 的完整性（AVB）
2. Kernel 启动后，通过 dm-verity 验证 system 分区的每个块

这对启动时间的直接影响：**每次读取系统分区的数据块时，都需要验证其 hash 值**。在开机阶段，大量文件被读取（dex2oat 编译、类加载等），dm-verity 会引入额外的 CPU 开销。

权衡点在于：
- **安全性更高** → 启动稍慢
- **可以关闭 dm-verity**（需要解锁 bootloader）→ 启动更快但失去安全保护

[适用版本: Android 7.0 (Nougat) 起 dm-verity 默认启用]

## 在 Perfetto 中识别启动各阶段

| 阶段 | 在 Perfetto / 日志里的观察点 | 该去哪里继续查 |
|------|------------------------------|----------------|
| Kernel / first-stage init | Trace 往往不完整，更多靠 `dmesg`、bootstat、串口 | 驱动初始化、early mount、verity、分区 I/O |
| second-stage init | init 进程活跃，`post-fs-data`、`zygote-start` 等 action 依次推进 | init rc、属性、服务装配 |
| Zygote 预加载 | zygote / zygote64 上出现 `PreloadClasses`、`PreloadResources` 等 slice | preloaded-classes、ART APEX、odsign / dexpreopt |
| SystemServer 启动 | `StartServices` 下嵌套 bootstrap / core / other / apex services | 具体 service 的初始化和依赖 |
| Home 首帧 | Launcher bindApplication、首帧提交、SurfaceFlinger 合成 | Launcher 自身初始化、WMS、SF |
| 广播长尾 | UI 已经稳定，events buffer 里还在推进 `LOCKED_BOOT_COMPLETED` / `BOOT_COMPLETED` | UserController、广播接收器、后台收尾任务 |

[待补充：一张按阶段标注的开机 Trace，总结从 init 到 Home 首帧的关键 slice]

## 常见问题与误区

### 误区：“init 进程是 Android 所有进程的鼻祖”

init 是用户空间所有进程的鼻祖。PID 0 的 swapper 才是 Linux 侧最早的起点，PID 2 的 kthreadd 则是内核线程的起点。

### 误区：“开机时间就是到桌面显示的时间”

至少要把下面几类里程碑分开：

- `boot_progress_system_run`
- `boot_progress_enable_screen`
- Home 首帧可见
- `ACTION_LOCKED_BOOT_COMPLETED`
- `ACTION_BOOT_COMPLETED`

如果把它们全都算成“开机完成”，不同版本、不同机型、不同测试脚本的结果就没法比较。

### 误区：“App 冷启动慢，只要多预加载一点类就行”

Zygote 预加载能解决的是公共运行时准备工作，解决不了业务进程自己的 `Application.onCreate()`、主线程 I/O、首次 profile / dex2oat、网络初始化。把更多业务类塞进预加载列表，很可能会把整机开机时间和常驻内存一起抬高。

<!-- AIW-源码调研-2026-04-15 -->
### Zygote fork SystemServer 的触发机制（源码级补充）

正文描述"Zygote 预加载完成后 fork SystemServer"，这里补充 fork 触发的精确机制。

**forkSystemServer 是 ZygoteInit.main() 的主动行为，不是被动等待 IPC。** `--start-system-server` 参数由 `init.zygote64.rc` 传入 `app_process64`，在 ZygoteInit.main() 中解析为布尔标志后直接决定是否调用 forkSystemServer()。不需要 AMS 或任何外部信号触发。

完整调用链（基于 android-16.0.0_r1）：

```
init.zygote64.rc:  service zygote /system/bin/app_process64 ... --start-system-server
  └─ app_main.cpp main() → AndroidRuntime.start("com.android.internal.os.ZygoteInit", args)
      └─ ZygoteInit.main(argv)
            ├─ 解析 argv: "start-system-server" → startSystemServer = true  (行 849-850)
            ├─ preload()          // 预加载 classes / resources / graphics driver
            ├─ gcAndFinalize()   // fork 前 GC，减少 COW 页
            ├─ new ZygoteServer(isPrimaryZygote)  // 创建 zygote socket
            ├─ if (startSystemServer) forkSystemServer(...)  // 行 904-912
            │    ├─ [父进程 Zygote]   pid > 0 → 返回 null → runSelectLoop() 永久等待 AMS
            │    └─ [子进程 system_server] pid == 0 → handleSystemServerProcess() → SystemServer.main()
            └─ runSelectLoop(abiList)  // Zygote 仅在父进程执行
```

关键源码锚点：

| 位置 | 行号 | 内容 |
|------|------|------|
| `ZygoteInit.java` | 844-850 | `startSystemServer` 参数解析 |
| `ZygoteInit.java` | 902-912 | `if (startSystemServer)` 分支判断 |
| `ZygoteInit.java` | 693-801 | `forkSystemServer()` 完整实现 |
| `ZygoteInit.java` | 780 | `Zygote.forkSystemServer()` JNI 调用 |
| `ZygoteInit.java` | 792-798 | 子进程分支：closeServerSocket + handleSystemServerProcess |
| `ZygoteServer.java` | 394 | `runSelectLoop()` — Zygote 仅在此响应 AMS fork 请求 |

补充说明：

1. **fork system_server 与 fork app 进程是不同路径**：前者在 main() 中直接调用，后者通过 Zygote socket 由 AMS 发起 IPC 请求后由 runSelectLoop() 处理。
2. **system_server 不进入 Zygote 事件循环**：子进程 fork 后直接执行 handleSystemServerProcess() → SystemServer.main()，然后 return 退出 ZygoteInit.main()，与 runSelectLoop() 无关。
3. **fork 前 GC 的目的**：`gcAndFinalize()`（行 893）在 fork 前回收软可达对象，减少 fork 后 COW 页数量。

<!-- /AIW-源码调研-2026-04-15 -->

## 参考资料

- AOSP 源码路径：
  - `system/core/init/first_stage_init.cpp` — first-stage init、`DoFirstStageMount()`、`SwitchRoot()`
  - `system/core/init/init.cpp` — second-stage init、rc 解析与 action queue
  - `system/core/rootdir/init.rc` — `zygote-start` 触发点与默认启动动作
  - `frameworks/base/config/preloaded-classes` — 当前分支预加载类列表
  - `frameworks/base/core/java/com/android/internal/os/ZygoteInit.java` — Zygote 预加载与 `startSystemServer()`
  - `frameworks/base/services/core/java/com/android/server/utils/TimingsTraceAndSlog.java` — SystemServer 阶段计时工具
  - `frameworks/base/services/java/com/android/server/SystemServer.java` — `BOOT_PROGRESS_SYSTEM_RUN`、四段 StartServices
  - `frameworks/base/services/core/java/com/android/server/EventLogTags.logtags` — `boot_progress_system_run` / PMS 相关里程碑
  - `frameworks/base/services/core/java/com/android/server/am/EventLogTags.logtags` — `boot_progress_ams_ready` / `boot_progress_enable_screen`
  - `frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java` — `systemReady()`、`startHomeOnAllDisplays()` 调用路径
  - `frameworks/base/services/core/java/com/android/server/am/UserController.java` — `ACTION_LOCKED_BOOT_COMPLETED` / `ACTION_BOOT_COMPLETED` 广播发送
  - `frameworks/base/services/core/java/com/android/server/wm/ActivityTaskManagerService.java` — `enableScreenAfterBoot()`
  - `hardware/interfaces/cas/aidl/default/cas-default-lazy.rc` — lazy AIDL service 的 rc 示例
- 官方文档：
  - [Android Boot Time](https://source.android.com/docs/core/perf/boot-times)
  - [Android Architecture](https://source.android.com/docs/core/architecture)
  - [Android Boot](https://source.android.com/docs/core/boot)
  - [Verified Boot](https://source.android.com/docs/security/features/verifiedboot)
- 其他参考：
  - [Android 启动系列之我是 init 进程 - 掘金](https://juejin.cn/post/7287913415804370955)
