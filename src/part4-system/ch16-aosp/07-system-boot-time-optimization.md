---
title: "Android 系统启动耗时优化与 bootanalyze"
chapter: "16.7"
section: "16.7"
status: ready-for-review
drafted_date: "2026-05-17"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-30"
last_verified_against: "AOSP android-17.0.0_r1; Android Common Kernel android17-6.18-2026-06_r6; source.android.com boot guidance; Android Developers 16 KB page-size guidance"
confidence: high
sources:
  - type: official
    path: "https://source.android.com/docs/core/perf/boot-times"
  - type: official
    path: "https://source.android.com/docs/core/architecture/kernel/boot-time-opt"
  - type: official
    path: "https://source.android.com/docs/core/runtime/boot-image-profiles"
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/boottime_tools/bootanalyze/README.md"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/boottime_tools/bootio/README.md"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/init/README.md"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/bootstat/bootstat.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/java/com/android/server/SystemServer.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/pm/DexOptHelper.java"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/base/dd.c"
tags: [aosp, boot, boot-time, perfetto, performance]
related_chapters: ["1.2", "8.2", "13.2", "16.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-17"
gap_source: "官方文档/AOSP结构"
last_research_at: "2026-06-28"
last_research_source: "DeepResearch/2026-06-28-android17-bootanalyze-zsygotelazy-sourcepath-correction.md"
---

# Android 系统启动耗时优化与 bootanalyze

系统启动优化研究的是设备从上电到系统可用的整条路径。它横跨 bootloader、kernel、`init`、APEX、Zygote、`system_server`、SystemUI 和 Launcher，和单个 App 的 cold launch 不是同一个实验。

平台源码锚点是 Android 17 / API 37 / `android-17.0.0_r1`，kernel 锚点是 `android17-6.18-2026-06_r6`。历史版本只用于解释机制演进；没有设备实测支撑的收益数字不作为结论。

## 先固定“启动完成”的含义

同一次启动可以有多个终点。终点选错，优化结果会在看板上变好，却没有改善用户等待。

| 终点 | 观察方式 | 能回答的问题 | 不能替代的指标 |
|---|---|---|---|
| kernel entry | bootloader 日志、UART、硬件计时 | bootloader 已经把控制权交给 kernel | 上电到 kernel 的完整时间 |
| second-stage `init` | dmesg、`init second stage started` | kernel 和 first-stage init 的基线 | `/data` 挂载、Zygote、桌面可用 |
| Zygote start | `ro.boottime.zygote`、init 日志；flag 开启时可用 `ro.boottime.event.zygote-start` | framework 进程模型何时开始建立 | `system_server` 是否 ready |
| `sys.boot_completed=1` | property、bootstat | AMS 已进入 boot completion 收尾 | Launcher 是否已绘制且可操作 |
| Launcher shown | Launcher 自有事件、Surface/Window trace | 首个桌面窗口是否显示 | 输入是否已被处理 |
| first interactive | 自动化输入、画面检测、产品事件 | 用户何时能完成第一个关键动作 | 单纯的 property 时间 |

Android 17 的 `ActivityManagerService.finishBooting()` 会设置 `sys.boot_completed`，随后继续处理用户级 boot complete、用户 profile 启动和广播。这个 property 是稳定的平台边界，但它不等于“桌面已显示”，也不等于“触摸已有响应”。

init 会用 `ro.boottime.<service-name>` 记录 service 第一次启动的 `CLOCK_BOOTTIME` 时间，所以主 Zygote 对应 `ro.boottime.zygote`。`ro.boottime.event.<event-name>` 记录 Action 开始执行的时间，但只有 `com.android.init.flags.enable_init_event_timestamp` 开启时才生成。分析工具必须允许 event property 缺失，不能把缺值解释为 Zygote 没有启动。

实验报告应把起点和终点写进指标名。例如：

- `power_on_to_boot_completed_ms` 包含 bootloader，但需要 bootloader 或外部硬件提供上电起点。
- `kernel_to_boot_completed_ms` 从 kernel 时钟起算，适合 userspace 回归。
- `boot_completed_to_launcher_shown_ms` 反映 property 之后的桌面尾部。
- `power_on_to_first_interaction_ms` 接近用户体验，但依赖可靠的外部输入和画面判定。

## 冷启动样本也要分类

以下样本不能放进同一组分布：

| 类型 | 额外工作 | 建议标签 |
|---|---|---|
| 普通 cold boot | 常规挂载、服务启动、桌面启动 | `normal` |
| factory reset 后首启 | 包扫描、初始化、向导和可能的 dexopt | `first_boot` |
| OTA 后首启 | checkpoint、APEX/分区切换、dexopt | `post_ota` |
| Boot Classpath APEX 变化后首启 | ART boot dexopt | `post_bcp_apex` |
| userspace reboot | 不经过完整 bootloader/kernel 路径 | `userspace_reboot` |
| 加密状态或用户状态变化 | CE/DE 存储可用时点不同 | `storage_state_*` |

Android 17 的 `DexOptHelper.performPackageDexOptUpgradeIfNeeded()` 只在 first boot、device upgrade 或 Boot Classpath APEX 发生变化时调用 `ArtManagerLocal.onBoot()`。源码注释明确说明这个调用会阻塞，耗时可能达到 30 秒以上；普通启动会直接返回。版本看板若不区分这些类型，P90 很容易被少量升级样本主导。

## 一套实用的证据层级

系统启动问题适合按“统计 → 分段 → trace → 源码”逐层缩小：

1. bootstat 或产品指标确认回归是否稳定，观察 P50、P90 和离群点。
2. bootanalyze 把 logcat/dmesg 中的稳定事件转成阶段时间。
3. bootio 找启动窗口里的进程 I/O 体量。
4. Perfetto/ftrace 把慢阶段拆到线程调度、CPU 频率、Binder、锁、page fault、block I/O 和 ext4。
5. 回到 `init.rc`、driver probe、Zygote preload 或 SystemServer trace slice 核对依赖。

单份 trace 适合解释一次慢启动，不能单独证明版本回归。阶段统计没有原始 trace 时只能提示方向，也不足以指导 rc、kernel 或 profile 修改。

## bootanalyze：它读什么，输出什么

Android 17 的工具位于：

`system/extras/boottime_tools/bootanalyze/`

目录中的角色如下：

| 文件 | 作用 |
|---|---|
| `bootanalyze.py` | 采集并解析 logcat、dmesg、timing event 和 shutdown event |
| `config.yaml` | 定义单点事件、带耗时事件、关机事件和时钟修正规则 |
| `bootanalyze.sh` | 设置循环、重启方式、bootchart、Automotive 和登录流程 |
| `README.md` | 快速说明，但有文档漂移 |

### README 与 r1 脚本存在漂移

`README.md` 仍写 Python 2.7，`bootanalyze.py` 的 shebang 已是 `#!/usr/bin/python3`。README 还展示了 `stop_event`，r1 脚本没有读取这个字段。脚本默认等待 `BootComplete` 和 `LauncherStart` 两个事件；启用额外选项时，还会等待 `FsStat`、CarWatchdog、`LoginEnd` 或 `LauncherShown`。

这带来两个工程约束：

- 产品定制 `config.yaml` 时，要保留脚本使用的事件键，或同步修改脚本里的停止事件列表。
- Launcher 类名或日志格式发生变化时，默认 `LauncherStart` 正则可能一直匹配不到，采集会等到超时。

### `events` 与 `timings` 的含义不同

`events` 记录一个事件第一次出现的时间点。`timings` 从一条日志中提取子阶段名和耗时，正则必须提供 `name` 与 `time` 命名捕获组。

下面的配置用于解析 SystemServer 的 `took to complete` 日志：

```yaml
timings:
  system_server: 'SystemServerTiming(Async)?\s*:\s*(?P<name>\S+) took to complete:\s(?P<time>[0-9]+)ms'
```

匹配后，工具会把 `StartPackageManagerService` 一类子阶段及其毫秒值分别记录。正则要先在目标版本的原始 logcat 上回放，避免日志 tag 变化后静默丢点。

### 多轮采集

下面的命令使用 r1 wrapper 做十次回归采样：

```bash
ANDROID_BUILD_TOP="$PWD" \
CONFIG_YMAL="$PWD/system/extras/boottime_tools/bootanalyze/config.yaml" \
LOOPS=10 \
RESULTS_DIR="$PWD/out/boot-analyze" \
system/extras/boottime_tools/bootanalyze/bootanalyze.sh -a
```

`CONFIG_YMAL` 是源码里已经固化的拼写，不能改成 `CONFIG_YAML`。工具需要可执行 `su` 的测试设备，适合 userdebug/eng 和实验室环境。r1 wrapper 会无条件执行 `touch /data/bootchart/enabled`，`-b` 只控制后续 bootchart 处理；做低扰动基线时应评估这一行为，或直接调用 `bootanalyze.py` 并自行管理采集开关。

### 时间修正

启动早期的 logcat wall clock 可能被校时。默认配置通过 `time_correction_key: correction` 匹配 `Updating system time`，再修正校时点之前的 logcat 时间。dmesg 使用 kernel 时间，两类时钟不能直接相减；产品新增事件时，应确认它来自哪个时钟域。

## bootio：先找 I/O 责任进程

`bootio` 依赖以下 kernel 配置：

- `CONFIG_TASKSTATS=y`
- `CONFIG_TASK_DELAY_ACCT=y`
- `CONFIG_TASK_XACCT=y`
- `CONFIG_TASK_IO_ACCOUNTING=y`

它记录进程维度的启动 I/O，适合回答“谁读写得多”，不提供文件级调用链。下面的命令设置 120 秒窗口、采五次并在结束后清理控制文件：

```bash
adb shell 'echo "120 5" > /data/misc/bootio/start'
adb reboot
adb shell bootio -p
adb shell rm /data/misc/bootio/start
```

`/data/misc/bootio/start` 不会自动删除。若只看总字节数，仍无法区分顺序读、随机读、page cache 命中或 block queue 等待；定位文件和等待原因还要接 ftrace/Perfetto。

## Perfetto：解释等待发生在哪里

bootanalyze 给出阶段，Perfetto 负责解释阶段内部的并发和等待。启动 trace 至少应覆盖：

- `sched_switch`、`sched_wakeup`、CPU frequency/idle；
- `binder_driver` 和主要 framework atrace category；
- block I/O、ext4、page fault；
- `init`、Zygote、SystemServer 的 atrace slice；
- 目标 HAL、SurfaceFlinger、SystemUI 和 Launcher 的自定义 slice。

启动采集要在重启前安装 trace 配置，并确认 trace session 已经开始。普通的“设备起来后再执行 `perfetto`”会漏掉 kernel、first-stage init、APEX bootstrap 和 Zygote 前半段。采集配置、buffer 大小和 data source 也要作为实验元数据保存，因为丢事件和 trace 开销都会改变结论。

Android 17 的 `SystemServer.run()` 显式调用 `Producer.init(..., 4 * 1024)`，源码注释把它定义为 4 MiB 的 Perfetto producer shared-memory buffer。它服务于 system_server producer，不是整份 trace 的全局 buffer，也不能换算成“追踪精度提升多少”或“固定增加多少 CPU 开销”。

## `init` 的串行队列与进程并发

`init` 的 Action 队列按 rc 文件解析顺序入队。队列中的 Action 依次执行，每个 Action 内的 command 也依次执行。Android 17 `init.cpp` 主循环每次调用一次 `ActionManager::ExecuteOneCommand()`，然后回到事件循环处理 property、子进程和控制消息。

这不表示启动期间只能运行一个进程：

- `start` 和 `class_start` 依次 fork/exec service，但启动后的 service 彼此可以并发运行。
- `exec`、`exec_start` 会让 Action 队列等待进程结束。
- `exec_background` 启动进程后不阻塞后续 command。
- `wait`、`wait_for_prop` 和同步的文件检查会把等待留在 init 关键路径。

下面的 rc 片段展示如何把独立工作放到 service 中，再用 property 表达依赖完成：

```rc
service vendor_prepare_cache /vendor/bin/prepare_cache
    class main
    user system
    group system
    disabled
    oneshot

on post-fs-data
    start vendor_prepare_cache

on property:vendor.prepare_cache.ready=1
    start vendor_consumer
```

这种写法允许 `vendor_prepare_cache` 与其他 service 并发。安全性取决于 `vendor_consumer` 是否只在 ready property 之后启动，以及失败路径是否能超时、降级或阻止错误状态继续传播。

### `class_start` 的边界

Android 17 `do_class_start()` 遍历 `ServiceList`，对属于目标 class 的 service 调用 `StartIfNotDisabled()`。它有三点容易写错：

- `disabled` service 不随 class 自动启动。
- 单个 service 启动失败会记日志，遍历仍会继续。
- class 只提供分组，不表达 service 之间的依赖图。

把 service 移到更早 class 前，应核对分区挂载、SELinux domain、设备节点、APEX 激活、Binder service 和 HAL 依赖。仅凭“没有显式 wait”不能证明它可以提前。

### event trigger 与 property trigger

`on boot && property:x=y` 只在 `boot` event 发生时检查组合条件。如果 `boot` 已经过去，property 随后才变成 `y`，这条 Action 不会补跑。只依赖 property 的 `on property:x=y` 会在属性变成目标值时触发；`boot` event 的末条 command 执行完以后，init 还会对全部 property trigger 做一次检查，执行当时已经满足条件的 Action。

持久化 property 还有额外顺序边界：当 `ro.property_service.async_persist_writes=true` 时，persistent setprop 与普通 setprop 的触发先后没有定义。修改 rc 时要用状态机或显式 property 表达依赖，不能依赖日志里一次偶然的顺序。

### APEX rc 与 `updatable` service

Android 17 会处理 `/apex/*/etc/*rc`，并按 SDK 后缀选择适用的版本化 rc。标记为 `updatable` 的 service 如果在 APEX 激活完成前收到启动请求，init 会把启动延后；没有 `updatable` 标记的 service 不能由 APEX 中的定义覆盖。

启动回归不能只检查 `/system/etc/init/hw/init.rc`。vendor、odm、APEX 和硬件专用 rc 都可能新增 Action、service 或 property 等待。

## kernel：以 android17-6.18-2026-06_r6 为准

kernel 启动耗时通常集中在镜像加载/解压、module load、driver probe、firmware、存储和设备依赖。Android 官方 kernel boot-time 指南给出的优化方向在 6.18 锚点上仍要逐驱动验证。

### 选择性异步 probe

`android17-6.18-2026-06_r6` 的 `drivers/base/dd.c` 会根据 driver 的 `probe_type` 和 `driver_async_probe=` 选择同步或异步 attach。Android 模块还可以通过 `<module>.async_probe=1` 启用异步 probe。

适合评估的对象通常有：

- 慢速 I2C/SPI 总线设备；
- probe 中加载 firmware 的设备；
- 大量硬件初始化且不阻塞首屏的设备。

异步 probe 不能全量开启。consumer 必须正确处理 supplier 未就绪并返回 `-EPROBE_DEFER`；显示、存储、clock、regulator、thermal 等依赖若表达错误，耗时会从 module load 转成更晚的同步等待或功能故障。

官方文档给出的异步 probe 示例收益是 100–500 ms，移动非必要 module 到 second-stage init 的示例收益是 500–1000 ms。这些数字取决于硬件和 driver，只能用来说明量级，不能直接写进产品收益预期。

### first-stage 与 second-stage module

正常启动的 first stage 只应保留完成根文件系统和早期启动所需的 module。recovery/fastbootd 需要的 USB、显示等 module 可以保留在 ramdisk，却不必在 normal boot 的 first stage 全部加载。

相关构建变量包括：

- `BOARD_VENDOR_RAMDISK_KERNEL_MODULES_LOAD`
- `BOARD_VENDOR_RAMDISK_RECOVERY_KERNEL_MODULES_LOAD`
- `BOARD_VENDOR_KERNEL_MODULES_LOAD`

移动 module 后，要同时验证 normal boot、recovery、fastbootd、OTA 和 crash recovery。second-stage 后台加载还要提供 ready property 或可靠的设备节点等待，不能让 HAL 在 driver 未就绪时无限阻塞。

### CPUfreq/devfreq 的启动顺序

CPUfreq、DRAM 和 interconnect devfreq 过晚上线，会让早期串行工作长期运行在 bootloader 留下的低频状态。提前 probe 前要确认 clock、regulator 和 thermal supplier 已就绪。频率上升带来的功耗和温升也要纳入回归，不能只保留 boot time。

## Zygote：预加载成本放在哪个阶段

Android 17 r1 的 primary 64-bit Zygote 由 `init.zygote64.rc` 启动，命令行没有 `--enable-lazy-preload`，因此在 fork `system_server` 前执行完整 preload。

完整 preload 包括：

- classes 与 non-boot classloader cache；
- framework resources；
- app-process HAL 和 graphics driver；
- `android`、`jnigraphics` 等 shared library；
- text/font cache 与 compatibility rules；
- flag 开启时的 `HttpEngine.preload()`；
- WebView Zygote 准备和 JCA provider warm-up。

preload 会增加 boot 阶段的 CPU、I/O 和 page fault，同时让 fork 后进程复用更多已初始化状态。删减预加载项时要同时测系统 boot、首个 App、首个 WebView、PSS/共享页和连续启动。

### lazy preload 不是 Android 17 新能力

`--enable-lazy-preload` 在较早 Android 版本已经存在。Android 17 的 64/32 配置里，`init.zygote64_32.rc` 仍给 32-bit secondary Zygote 传这个参数；primary Zygote不传。

lazy 模式跳过启动期 preload，收到首次 preload 请求时由 `ZygoteConnection` 调用 `ZygoteInit.lazyPreload()`，后者仍执行同一套完整 `preload()`。它改变的是支付时间，不会自动把 preload 拆成增量任务。

回归时应分别记录：

- primary Zygote 的 `ZygotePreload`；
- secondary Zygote 的 `ZygoteInitTiming_lazy`；
- 首个 32-bit 进程请求前后的延迟；
- 双 Zygote 设备与纯 64-bit 设备的配置差异。

## SystemServer：从 trace slice 看同步点

Android 17 `SystemServer.run()` 的主线结构是：

1. 初始化 SystemServer 进程环境和 Perfetto producer；
2. 启动 `SystemServerInitThreadPool`；
3. 把 `SystemConfig::getInstance` 尽早提交到线程池；
4. 加载 `android_servers`；
5. 创建 system context 和 `SystemServiceManager`；
6. 依次进入 bootstrap、core、other、APEX service 分组；
7. 进入各个 boot phase，直到 AMS 完成 boot。

主线程上的 `startService()` 调用顺序仍然重要，但某些 service 会把工作提交到线程池。判断某个 slice 是否阻塞关键路径时，要同时看主线程是否等待 future、Binder reply、锁或 property，不能按 slice 宽度直接推断全部为 CPU 执行。

### SystemConfig 早期并发

r1 无条件调用 `startSystemConfigInit()`，方法把 `SystemConfig::getInstance` 提交给 `SystemServerInitThreadPool`。后续 consumer 第一次取 `SystemConfig` 时，如果后台工作尚未完成，仍可能在那里等待。

优化方向应围绕“提交是否足够早、consumer 在哪里 join、配置扫描是否变重”展开。源码仅证明并发结构，不能推出固定的毫秒收益。

### ART Mainline 的早期初始化

`startBootstrapServices()` 很早就调用 `ArtModuleServiceInitializer.setArtModuleServiceManager(...)`。源码注释说明 `service-art.jar` 的 class linking 和 GC 互斥；把首次引用放在 PackageManager 大量分配之前，可避开后面的 GC 竞争。

这段初始化和特殊启动中的 boot dexopt要分开：

- `ArtModuleServiceInitializer` 是早期注册与 class-linking 时点。
- `UpdatePackagesIfNeeded` 在 later `startOtherServices` 中运行。
- first boot、OTA 或 Boot Classpath APEX 变化时，`ArtManagerLocal.onBoot()` 才执行阻塞式包 dexopt。
- 普通 cold boot 不走这轮 boot dexopt。

### APEX system service 必须位于分组末尾

`startApexServices()` 遍历 `ApexManager.getApexSystemServices()`，启动 APEX 声明的 system service，然后调用 `SystemServiceManager.sealStartedServices()`。源码注释要求 APEX service 是启动 service 的末组，避免 platform service 反向依赖可独立更新的 APEX service。

这是一条架构约束，不是“APEX 并行挂载带来固定收益”的证据。bootanalyze 默认配置只提供 `apexd_activated`、`apexd_bootstrapping_done` 和 `apexd_ready` 三个 apexd 日志事件；挂载 namespace、单个 APEX 校验和单个 service 初始化仍要靠更细的 trace 或自定义日志。

### Boot phase 不是任务并行模型

Android 17 的 SystemServer 会触发 `PHASE_WAIT_FOR_DEFAULT_DISPLAY`、`PHASE_WAIT_FOR_SENSOR_SERVICE`、`PHASE_SYSTEM_SERVICES_READY`、`PHASE_ACTIVITY_MANAGER_READY`、`PHASE_THIRD_PARTY_APPS_CAN_START` 等阶段。`SystemServiceManager.startBootPhase()` 按已启动 service 调用 `onBootPhase()`；阶段号表达生命周期边界，不保证 callback 自动并行。

平台新增 service 时，应记录：

- constructor/start 的 trace slice；
- 各 boot phase callback；
- 首次 Binder 发布和 ready 事件；
- 失败时的降级路径；
- 是否阻塞默认显示、PMS、AMS、SystemUI 或 Launcher。

## `finishBooting()` 内还有哪些工作

Android 17 的 AMS 只有在 boot animation 完成后才继续 `finishBooting()`；若动画尚未完成，会记录待处理状态并返回。进入收尾后，顺序包含：

1. 通知 Zygote 与 VMRuntime boot completed；
2. 提交存储 checkpoint，失败时请求重启；
3. 触发 `PHASE_BOOT_COMPLETED`；
4. 启动此前 hold 的进程；
5. 设置 `sys.boot_completed=1` 和 `dev.bootcomplete=1`；
6. 向 lmkd 发送 `LMK_START_MONITORING`；
7. 进入用户级 boot completion，随后调度用户 profile 启动。

因此，以下说法都不够严谨：

- “boot animation 停止就是 `sys.boot_completed`”：两者有顺序关系，还要看 AMS 收尾。
- “property 置 1 后没有启动工作”：用户回调、广播和应用进程仍可能继续占用 CPU/I/O。
- “LMKD PSI 在 Android 17 全程关闭”：framework 只证明 boot complete 后显式发送 start-monitoring 命令，早期是否已经监控还受 lmkd 配置影响。

## bootstat：适合版本看板的持久化事件

`bootstat` 把事件名和相对时间持久化。Android 17 的 `bootstat.rc` 在第一次 `sys.boot_completed=1` 时执行：

- `--record_boot_complete`
- `--record_boot_reason`
- `--record_time_since_factory_reset`
- `-l`

`RecordBootComplete()` 还会收集一组明确列出的 `ro.boottime.init.*`、`ro.boottime.event.*` 字段，以及 `ro.boot.boottime` 中的 bootloader 分段。event 字段只有在 init 的 event timestamp flag 开启并成功写入 property 时才有值。bootloader 没有提供 `ro.boot.boottime` 时，bootstat 无法补出上电到 kernel 的缺失时间。

下面的命令用于记录自定义事件并检查本机事件：

```bash
adb shell bootstat -r vendor_display_ready
adb shell bootstat -p
adb shell bootstat -l
```

`-r` 记录执行命令时的系统 uptime。r1 的 `-l` 实现会把已支持的事件映射到 bootstats atoms；README 中“EventLog/Tron histogram”的描述已经落后于当前实现。自定义事件仍可持久化和打印，但没有 `kBootEventToAtomInfo` 映射时不会作为受支持 atom 写出。

## I/O、page fault 与文件布局

启动 I/O 要分三层：

| 层级 | 典型现象 | 证据 | 调整方向 |
|---|---|---|---|
| 文件 | APK/JAR/APEX/配置被过早扫描 | file access、bootio、page cache | 延迟非关键读取、减少重复扫描 |
| block/fs | queue 等待、读放大、verity、fsck | block/ext4/f2fs trace | I/O scheduler、read ahead、文件布局 |
| memory mapping | major fault、mmap 抖动、解压 | page fault + sched + file map | 热点布局、预加载清单、压缩策略 |

“减少读取字节”也可能把成本推到 Launcher 显示之后。评估时至少保留两个窗口：

- kernel entry 到 `sys.boot_completed`；
- `sys.boot_completed` 到 first interactive。

OTA 后 checkpoint、pre-reboot dexopt artifact 提交、APEX 切换和首次包扫描要单独标记。它们属于升级成本，不能用普通 cold boot 的目标去裁剪。

## 16 KB page size 是设备级基线变化

Android Developers 的 16 KB page size 文档给出一组初始测试：system boot time 平均改善 8%，约 950 ms，同时说明不同设备结果会变化。这个数字是官方测试样本，不是 Android 17 所有设备的保证。

比较 4 KB 与 16 KB 时，page table、mmap、page fault、ELF 对齐、文件系统和设备内存都发生了变化。应把 page size 写入样本维度，并使用同一硬件、同一 build 配置和同一启动类型做 A/B。不能把跨设备差异归到某个 SystemServer service。

## 从慢阶段回到处理动作

| 慢阶段 | 优先确认 | 常见处理 |
|---|---|---|
| bootloader | 镜像读取、解压、UART、boot reason | 减少日志、选择合适压缩、拆分硬件阶段 |
| kernel / coldboot | module load、probe、firmware、supplier | 移动非必要 module、选择性 async probe |
| first-stage init | 存储、dm-verity、first-stage module | 缩小 ramdisk 关键集合 |
| second-stage init | `exec`、property wait、service class | 后台 service、显式 ready、修正依赖 |
| Zygote | classes/resources/library preload | 调整清单并回归首个 App 与共享内存 |
| PMS / ART | 包扫描、first boot/OTA dexopt | 分类启动类型、检查 compiler filter 与 artifact |
| SystemServer | service start、boot phase、Binder/锁 | trace 到具体 callback 和等待对象 |
| SystemUI / Launcher | 进程创建、首帧、资源竞争 | 单独测 shown 与 first interactive |

每次改动只回答一个假设。例如，“I2C touch probe 阻塞 module load”要用 probe 时间证明；改成 async 后再验证触摸在 Launcher 首帧前 ready、recovery 可用、没有 defer storm。把多项 kernel、rc 和 framework 调整合在一个版本里，会让收益与回归都无法归因。

## 实验与回归门禁

一组可复现的 boot 实验至少记录：

- build fingerprint、AOSP tag、kernel tag、vendor image；
- page size、文件系统、存储型号和加密状态；
- normal/first boot/post-OTA/userspace reboot；
- 电池、充电、温度和关机静置时间；
- bootchart、Perfetto、UART 等采集开关；
- `sys.boot_completed`、Launcher shown、first interactive；
- P50、P90、样本数和剔除规则。

安全与稳定性门禁包含：

- verified boot、SELinux、KeyMint/Gatekeeper 和 checkpoint 顺序不变；
- recovery、fastbootd、OTA、加密解锁都能完成；
- display、touch、radio、audio 等产品关键硬件按场景 ready；
- service 失败有超时和降级，不制造无限 property wait；
- boot 变快后，首屏 jank、首个 App、功耗和内存没有回归。

关闭日志和 trace 可以减少测试机上的开销，但量产配置与可观测性要分别评估。没有可回放证据的优化，一旦在后续版本回归，定位成本通常高于省下的少量启动时间。

## 与其他章节的边界

- 完整启动流程与进程关系见 [[02-boot-process|1.2 系统启动全流程]]。
- Zygote fork、USAP 和 preload 机制见 [[11-zygote-startup|1.11 Zygote 机制与启动性能优化]]。
- ART compiler filter 与 dex2oat 见 [[07-art-compilation|1.7 ART 编译管线与 dex2oat 优化]]。
- Perfetto 配置与采集见 [[02-trace-capture|13.2 Trace 采集]]。
- 16 KB kernel/用户态边界见 [[06-16kb-page-size|4.6 16 KB Page Size]]。

## 参考资料

- [AOSP：Optimize boot times](https://source.android.com/docs/core/perf/boot-times)
- [AOSP：Kernel boot time optimization](https://source.android.com/docs/core/architecture/kernel/boot-time-opt)
- [AOSP：Boot image profiles](https://source.android.com/docs/core/runtime/boot-image-profiles)
- [Android Developers：Support 16 KB page sizes](https://developer.android.com/guide/practices/page-sizes)
- [Perfetto：Record system traces](https://perfetto.dev/docs/getting-started/system-tracing)
- [AOSP r1：bootanalyze.py](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/boottime_tools/bootanalyze/bootanalyze.py)
- [AOSP r1：bootanalyze.sh](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/boottime_tools/bootanalyze/bootanalyze.sh)
- [AOSP r1：bootanalyze config.yaml](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/boottime_tools/bootanalyze/config.yaml)
- [AOSP r1：bootio README](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/boottime_tools/bootio/README.md)
- [AOSP r1：init README](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/init/README.md)
- [AOSP r1：init.cpp](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/init/init.cpp)
- [AOSP r1：init.zygote64_32.rc](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/rootdir/init.zygote64_32.rc)
- [AOSP r1：bootstat.cpp](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/bootstat/bootstat.cpp)
- [AOSP r1：bootstat.rc](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/bootstat/bootstat.rc)
- [AOSP r1：ZygoteInit.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/ZygoteInit.java)
- [AOSP r1：SystemServer.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/java/com/android/server/SystemServer.java)
- [AOSP r1：ActivityManagerService.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java)
- [AOSP r1：ProcessList.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ProcessList.java)
- [AOSP r1：DexOptHelper.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/pm/DexOptHelper.java)
- [AOSP r1：ArtManagerLocal.java](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ArtManagerLocal.java)
- [AOSP kernel：android17-6.18-2026-06_r6 driver core](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/base/dd.c)
