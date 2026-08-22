---
title: PerfDog、SoloPi 与 Emmagee
chapter: '19'
section: '19.16'
status: finalized
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: '2026-08-21'
last_verified_against: "PerfDog current official site plus client, Service, metric and network docs; SoloPi v1.0.2 release and pinned source; Emmagee V2.5.1 release and pinned source; Android performance docs; AOSP android-17.0.0_r1 PowerStats, Thermal and SurfaceFlinger anchors"
last_rework_at: "2026-08-05T13:35:16+08:00"
last_rework_run_id: "20260805-133516-rework-bdb326bd"
confidence: medium
tags:
- apm
- perfdog
- testing
- benchmark
- tools
related_chapters:
- '19.0'
consolidated_from:
- "src/part3-tools/ch19-apm/20-solopi-emmagee.md"
sources:
- type: official
  path: https://perfdog.qq.com/
- type: official
  path: https://perfdog.qq.com/help/faq
- type: official
  path: https://perfdog.qq.com/article_detail?id=10089&issue_id=0&plat_id=1
- type: official
  path: https://perfdog.qq.com/article_detail?id=10162&issue_id=0&plat_id=1
- type: official
  path: https://perfdog.qq.com/article_detail?id=10081&issue_id=0&plat_id=1
- type: official
  path: https://perfdog.qq.com/article_detail?id=10143&issue_id=0&plat_id=2
- type: official
  path: https://perfdog.qq.com/article_detail?id=10210&issue_id=0&plat_id=2
- type: official
  path: https://perfdog.qq.com/article_detail?id=10241&issue_id=0&plat_id=1
- type: official
  path: https://developer.android.com/topic/performance/vitals/render
- type: official
  path: https://developer.android.com/studio/profile/jank-detection
- type: official
  path: https://github.com/alipay/SoloPi/releases/tag/v1.0.2
- type: official
  path: https://github.com/alipay/SoloPi/tree/c83276286183f43d99f35cd52a6e2432bd11c7af
- type: official
  path: https://github.com/NetEase/Emmagee/releases/tag/V2.5.1
- type: official
  path: https://github.com/NetEase/Emmagee/tree/6a382dffe74b5be6d2de78cb0c640cc67e9ce650
- type: official
  path: https://source.android.com/docs/core/power/thermal-mitigation
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/powerstats/PowerStatsService.java (android-17.0.0_r1)
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/powerstats/PowerStatsHALWrapper.java (android-17.0.0_r1)
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/thermal/ThermalManagerService.java (android-17.0.0_r1)
- type: aosp
  path: hardware/interfaces/thermal/aidl/android/hardware/thermal/IThermal.aidl (android-17.0.0_r1)
- type: aosp
  path: frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp (android-17.0.0_r1)
- type: aosp
  path: frameworks/native/services/surfaceflinger/Layer.cpp (android-17.0.0_r1)
pipeline_stage: finalized
task6_state: reviewed
last_review_finalize_at: "2026-08-05T14:07:37+08:00"
last_review_finalize_run_id: "20260805-140520-70395a2d"
task9_state: reviewed
task2b_state: fixed
last_idle_audit_at: "2026-08-21T18:42:54+08:00"
last_idle_audit_run_id: "20260821-183524-idle-audit-d188495e"
---


# PerfDog、SoloPi 与 Emmagee

## PerfDog 的位置：实验室观测工具

PerfDog 是腾讯 WeTest 提供的跨平台性能测试与分析工具。Android 测试不要求被测 App 接入 SDK（Software Development Kit，此处指需嵌入 App 的采集组件），也不要求设备 root（取得系统最高权限），适合下面几类工作：

- QA（Quality Assurance，此处指测试或质量保障人员）在固定设备和固定脚本上做发版回归。
- 开发团队快速筛出帧率、CPU、内存、温度或整机功耗异常的时间段。
- 在拿不到源码时观察第三方 App 或游戏的外部表现。
- 通过 PerfDog Service（自动化接口服务）或 CLI（命令行工具）接入实验室自动化。

截至 2026 年 8 月 14 日，官网还提供 MCP（Model Context Protocol，让 AI 客户端调用工具的标准接口）与 Skills（封装分析流程和判断规则的规则包）入口。这些入口可以调用数据、触发分析或生成报告，不会改变底层指标的采集口径，即数据来源、计算方式和适用条件；AI 给出的瓶颈判断仍需原始数据和系统 trace（按时间记录的运行轨迹）验证。

它不能代替线上 APM（生产环境中的应用性能监控）。PerfDog 覆盖的是受控环境里的单台或一组设备，线上 APM 负责汇总真实用户、真实网络和设备分布下的长期数据。它也不能仅凭一条外部曲线证明某个函数、线程或缓存策略有问题；根因仍需 Perfetto（Android 系统级时间线工具）、Android Studio、simpleperf（Android native CPU 分析器）、日志或业务埋点提供证据。

### Android 的两种设备模式

PerfDog 官方客户端手册把 Android 设备分为“非安装模式”和“安装模式”。这里的“安装”指手机端的 `PerfDog.apk`，不是被测 App 接入组件；PC 端 PerfDog 本身采用解压运行方式。

| 项目 | 非安装模式 | 安装模式 |
|---|---|---|
| 手机端组件 | 不安装 `PerfDog.apk` | PC 端向设备安装 `PerfDog.apk` |
| 实时显示 | 手机屏幕不显示 PerfDog 浮窗 | 手机端可显示实时指标 |
| 基础条件 | USB 调试、ADB（Android Debug Bridge，Android 调试桥）授权和稳定连接 | 在基础条件上增加 USB 安装与悬浮窗权限 |
| 适用场景 | 回归、竞品测试、希望减少手机端组件干扰 | 现场观察、演示或需要手机端实时读数 |
| 常见误解 | “没有浮窗”不代表没有采集 | 手机端显示进程被系统回收，不一定会中断 PC 端采集 |

不要把辅助功能、通知读取或 `android.permission.DUMP` 写成所有版本都必须授予的固定清单。不同客户端、Service 版本和所选指标会给出不同提示，应以当前官方安装包和设备页面为准。若某个侧载组件在 Android 13 至 Android 17 上请求辅助功能或通知读取，系统可能显示 Restricted Settings（受限设置，即系统对侧载 App 敏感能力的额外确认页）；只对来源可信、用途已确认的版本开放对应入口，测试结束后撤销不再需要的权限。

### USB 与 Wi-Fi 的采集条件不能混用

USB 模式便于保持连接和采集多数指标，但连接线会给设备充电。PerfDog 官方手册明确把 Android 的 Battery Power 放在 Wi-Fi 模式下采集：先通过 USB 建立 Wi-Fi 设备连接，连接成功后拔线，再开始功耗测试。测试报告必须写明连接方式；USB 下的电流或功耗曲线不能和断线后的 Wi-Fi 结果混在同一组基线里。

## 指标范围与可用条件

PerfDog 能显示的字段取决于平台、设备、SoC（System on Chip，集成 CPU、GPU 等模块的系统级芯片）、驱动、测试模式、客户端版本和账号权限。开始测试前，应先查看当前设备的可用指标列表；字段为空时，不要用 `0` 代替“未采集”。

下表保留 PerfDog 的字段名。Surface 指 App 提交图形缓冲区的显示目标；GPU Counter 是 GPU 暴露的硬件计数器。PSS（Proportional Set Size）是按共享比例分摊后的进程物理内存，Swap 是换出到交换区的内存，VSS 是进程占用的虚拟地址空间。TTID（Time to Initial Display）和 TTFD（Time to Full Display）分别表示首次画面与完整画面的显示时间。

| 指标组 | Android 常见字段 | 解释时必须保留的条件 |
|---|---|---|
| 帧呈现 | FPS、FTime、Jank、BigJank、SmallJank、TinyJank、Stutter、Smooth、1% Low、InterFrame | 被测窗口或 Surface、刷新率、前后台状态、场景标签 |
| CPU | AppCPU、TotalCPU、规范化 CPU、各核占用、各核频率、频率上限 | PerfDog 的规范化口径、核心数、性能模式、温度 |
| 内存 | PSS、Swap、VSS、Available Memory、Memory Detail | 目标进程、是否包含子进程、采样时长 |
| GPU | GPU Usage、GPU Frequency、GPU Counter | SoC、GPU 型号、驱动和设备支持列表 |
| 温度 | CTemp、GTemp、BTemp、NTemp | 传感器是否存在、起止温度、环境温度 |
| 电池与功耗 | BatteryLevel、Current、Voltage、Power、Sum(Battery)、FPower | Wi-Fi 模式、是否拔线、亮度、电量区间 |
| 网络流量 | 目标进程 Recv、Send | 目标进程、接口、缓存和服务器区域 |
| 启动 | TTID、TTFD | 冷/温/热启动条件、是否允许工具重新拉起 App |

Android 常规测试里的 Network 指标是目标进程的接收和发送流量。延迟、抖动、丢包与弱网模拟属于 PerfDog 的“网络分析”功能，不能由 `Recv/Send` 两条曲线推导。报告应标明使用的是常规流量指标还是网络分析任务。

GPU 是最容易出现“设备已连接但字段缺失”的一组数据。PerfDog 官方文档也把 Android GPU Usage 和 GPU Frequency 标为仅支持部分手机，并按 Adreno、Mali、PowerVR 提供不同 Counter 集。由此可得两个使用边界：

- 同一设备、同一驱动上的版本对比价值较高。
- 跨 SoC 的 GPU 利用率绝对值通常没有可比性，Counter 名称相同也不保证硬件含义相同。

## 帧指标要按 PerfDog 自己的定义阅读

PerfDog 的 Jank 口径与 Android Vitals（Play Console 的质量指标）、JankStats（应用内帧性能库）、Perfetto FrameTimeline（系统帧时间线）的分类不同。官方客户端手册把固定的 24 FPS 电影帧时长用作第二个门槛，这个门槛不会随手机的 60 Hz、90 Hz 或 120 Hz 刷新率变化：

| 指标 | PerfDog 官方判定 |
|---|---|
| SmallJank | 当前 FTime 大于前三帧平均值的 2 倍，且大于约 41.67 ms |
| Jank | 当前 FTime 大于前三帧平均值的 2 倍，且大于约 83.33 ms |
| BigJank | 当前 FTime 大于前三帧平均值的 2 倍，且大于 125 ms |
| Stutter | 测试区间内卡顿时长占比 |
| FTime | 相邻两帧画面显示的时间间隔 |
| 1% Low | 对最慢 1% 帧的平均帧时间取倒数并换算成 FPS |
| Smooth | PerfDog 的稳帧指数，数值越低越稳定 |

这套定义适合在 PerfDog 报告之间保持一致，却不能直接替换系统 jank 分类。120 Hz 屏幕每帧预算约 8.33 ms，一帧 30 ms 已经错过多个刷新周期，但还没有达到 PerfDog 的 SmallJank 固定门槛。因此，高刷新率测试必须同时保留 FTime 分布、P95/P99（第 95/99 百分位）、1% Low 和连续低帧区间。

官方对 Smooth 给出的经验值是游戏或视频小于 8、滑动类 App 小于 20。这是 PerfDog 产品指标的建议区间，不是 Android 平台兼容性标准。团队应先用自身机型和场景建立基线，再决定门禁值，也就是自动通过或阻断测试的阈值。

### 先选对窗口，再谈 FPS

一个包名可能同时存在 Activity 主窗口、`SurfaceView`、`TextureView`、视频层、游戏渲染层和子进程窗口。选错窗口时，PerfDog 可能显示系统 UI、静止层或与用户所见不一致的帧率。测试开始前至少确认：

- 包名、进程名和前台 Activity。
- PerfDog 当前选择的窗口或 Surface 名称。
- 游戏、视频、小程序是否使用独立 Surface。
- 旋转、画中画、弹窗或场景切换后，目标窗口是否发生变化。

PerfDog Service 提供 `getAppWindowsMap` 一类接口，可查询 Android 应用各进程涉及的 Activity 与 SurfaceView。人工核对时也可用 SurfaceFlinger（Android 的系统显示合成服务）的 layer 列表；layer 是参与合成的显示层，其名称属于系统调试信息，不能把名称相似当成归属证据。

## 测试条件决定结果能否复现

性能测试的首要产物是可复现的实验记录。每轮开始前固定并记录下面这些条件：

| 类别 | 必填项 |
|---|---|
| 硬件 | 品牌、完整型号、SoC、RAM；不要把 Pixel 8 写成 Snapdragon 设备，Pixel 8 使用 Google Tensor G3 |
| 系统 | Android 版本、API、构建号、安全补丁、厂商性能模式 |
| 显示 | 分辨率、刷新率、亮度、深色模式、自动亮度是否关闭 |
| 电源 | 起止电量、是否充电、电池健康状态、外接供电方式 |
| 热环境 | 室温、散热配件、起止温度、冷却等待规则 |
| 网络 | Wi-Fi/蜂窝、SSID（Wi-Fi 网络名称）或实验网络、服务器区域、弱网参数 |
| App | 包名、versionName、versionCode、渠道、ABI（native 二进制接口与 CPU 架构）、账号与配置 |
| 数据状态 | 冷启动/热启动、缓存、下载资源、首装或覆盖安装 |
| 操作 | 脚本版本、场景步骤、采集时长、场景标签 |
| 工具 | PerfDog 客户端/Service 版本、连接模式、已启用指标 |

自动刷新率、自动亮度、游戏加速器、厂商性能模式和后台同步都可能改变结果。测试前不要用“清理全部后台”代替条件说明：系统服务无法被等价清空，过度清理还会制造不符合用户场景的冷缓存。更稳妥的做法是列出允许保留的后台进程，并在各轮之间执行同一套恢复步骤。

长时游戏或视频至少覆盖热稳定阶段，也就是运行足够久、温度和频率趋于相对稳定的阶段。只取开局一分钟，测到的往往是尚未受温控约束的峰值。每轮开始温度必须落入预设区间；若达不到，应延长冷却时间并记录，不应临时放宽门槛。

## 平均 FPS 不够

平均值会同时掩盖“长期偏低”和“偶发长帧”。P50 是中位数，P95/P99 表示 95%/99% 的样本不超过该值。下面两个 60 秒场景可能得到相近的平均 FPS：

| 场景 | 平均 FPS | FTime P50 | FTime P95 | FTime P99 | 体感线索 |
|---|---:|---:|---:|---:|---|
| A：稳定受限 | 45 | 22 ms | 24 ms | 27 ms | 持续不够顺滑，但节奏稳定 |
| B：多数时间流畅、偶发尖峰 | 56 | 16 ms | 31 ms | 180 ms | 平时顺滑，间歇出现明显停顿 |

场景 B 的平均 FPS 更高，用户仍可能更容易注意到卡顿。一次回归至少保留：

- FPS 的平均值、中位数、1% Low 和稳定区间。
- FTime 的 P50、P90、P95、P99 和最大值。
- SmallJank/Jank/BigJank 次数及 Stutter。
- 长帧发生时的场景标签、截图或操作步骤。
- 采集区间前半段与后半段的对比。

P95/P99 若由导出数据离线计算，应在报告中写明脚本版本和空值处理方式，不要伪装成 PerfDog 界面原生字段。

## 功耗、温度和频率要一起看

PerfDog 的 Android Battery Power 是整机口径，不是目标 App 的独占功耗。屏幕、基带（蜂窝通信模块）、Wi-Fi、后台进程和系统服务都包含在内。对比时应固定亮度、音量、网络、账号数据和后台状态，并使用 Wi-Fi 连接后拔掉 USB。

`FPower` 在 PerfDog 数据处理中的口径是 `Power / FPS`，界面单位仍为 mW。它用于在相近场景和帧率下做归一化比较，也就是按同一尺度比较功耗；不能把它当作物理单位为焦耳的“单帧能量”。当 FPS 接近 0、场景静止或两组帧率差距很大时，这个比值也会失去解释力。

判断热降频时，推荐寻找同一时间轴上的证据组合：

1. CPU、GPU、SoC、机身或电池温度持续上升。
2. CPU Frequency Limits、CPU Clock 或 GPU Frequency 出现台阶式下降。
3. FTime P95/P99、1% Low 或 Stutter 同步恶化。
4. 在相同操作标签处，CPU/GPU 负载没有出现能够单独解释退化的新峰值。

单个温度值不等于系统已经限频。不同厂商暴露的传感器名称、安装位置与校准方式不同；同为 `CTemp` 的绝对值也不适合跨设备排名。报告应写起止温度、曲线拐点和系统 thermal status（温控等级），避免只贴峰值。

精确的能耗实验应使用外置功耗仪，并清楚区分电池端、USB 端和整机输入端的测量位置。PerfDog 更适合实验室回归中的相对变化监控。

## PerfDog、Perfetto、Profiler 与 Macrobenchmark 的分工

| 工具 | 擅长回答的问题 | 不宜单独负责的结论 |
|---|---|---|
| PerfDog | 哪个版本、设备或时间段的外部指标异常 | 哪个函数造成异常 |
| Perfetto / Android Studio System Trace | 主线程、RenderThread、SurfaceFlinger、调度、Binder（Android 跨进程通信）、I/O 如何重叠 | 大规模版本回归评分 |
| Android Studio Profiler | 开发机上交互查看 CPU、内存和网络，并继续定位到代码 | 低扰动的跨版本基准 |
| Macrobenchmark（Jetpack 宏基准测试框架） | 在受控启动和交互场景中重复测量启动与帧时序 | 第三方 App 的完整系统侧观测 |

一个常用流程是：

1. 用 PerfDog 在固定脚本中定位异常区间，并打上场景标签。
2. 在同一设备、同一构建和同一操作上抓 Perfetto，查看 FrameTimeline、主线程、RenderThread、GPU 和 SurfaceFlinger。
3. 能修改源码时，增加低开销 trace，或使用 Profiler、simpleperf、heap dump（堆内存快照）定位代码。
4. 对已定位且可自动重放的启动、滑动或列表场景，补 Macrobenchmark 防回归用例。

PerfDog 的 StartupTiming 可观察 TTID/TTFD，但精确启动基准仍要写清冷、温、热启动，并优先由 Macrobenchmark 控制启动模式。两种工具的启动数据可以互证，不能把不同启动条件的数值放在同一列比较。

## 三类使用流程

### 发版前回归

1. 从高端、中端和业务重点机型中选固定设备池。
2. 每个场景规定预热、冷却、账号、缓存和网络状态。
3. 当前版本与基线版本都至少运行多轮，保存每轮原始文件。
4. 使用各轮中位数比较，并同时检查最差有效轮次。
5. 超过门禁后回放曲线；需要根因时补抓 Perfetto。

### 专项优化

1. 用场景标签缩小异常时间段。
2. 一次只改变一个可控变量，例如纹理规格、线程数或缓存策略。
3. 交替运行基线与实验版本，减少升温和测试顺序带来的偏差。
4. 同时观察目标指标和副作用，例如 FPS 改善时内存、功耗是否上升。
5. 将确认有效的场景加入持续回归。

### 竞品分析

1. 使用同一台设备、同一系统、同一刷新率和同一网络。
2. 对齐账号等级、内容资源、画质、广告状态和下载完成度。
3. A/B 交替测试，并在每轮前恢复到相同温度区间。
4. 只报告外部可观察差异，不把现象直接写成对方的内部实现。
5. 使用测试账号和脱敏数据，遵守产品条款，不在共享报告里泄露账号、设备标识、聊天内容或内部服务器地址。

“竞品 A 在同机同场景下 FTime P95 较低”是可验证结论；“竞品 A 使用了更好的缓存算法”只是需继续验证的假设。

## 自动化：固定操作，也固定判废规则

精细回归优先使用 UIAutomator（Android UI 自动化框架）或团队内部的确定性脚本。`monkey` 是随机发送系统与触控事件的测试工具，适合稳定性和探索测试，不适合要求逐轮路径一致的性能对比。

PerfDog Service 的公开 gRPC（跨进程远程调用框架）接口覆盖设备初始化、可用指标查询、启停测试、实时数据流、场景标签、保存数据和 Android 窗口查询；当前官网也提供 CLI 与 Service 的 CI/CD（持续集成与交付）入口。接入时应把下面内容纳入脚本：

- 在测试前调用可用指标查询，缺少必填字段就终止该轮。
- 用 `setLabel` 或等价接口标记场景；不要等测试结束后再凭曲线猜测时间点。
- 记录脚本 commit（Git 提交号）、设备序列号映射、PerfDog 版本和报告 ID。
- 停止采集后等待文件写完，再开始清理或下一轮。
- 给每轮保留原始数据、控制台日志、操作日志和判定结果。

“看起来异常就删掉”会带来选择偏差。应在测试前写明判废条件，例如设备断连、必填指标缺失、脚本步骤失败、App 崩溃或网络环境越界。判废轮次仍保留原始文件和原因；性能差但流程完整的轮次属于结果，不能判废。

场景文件可采用下面的命名方式：

`<app>-<version>-<device>-<android>-<scene>-<mode>-<iteration>-<timestamp>`

例如：`demo-6.2.0-pixel8-android17-feed-scroll-wifi-r03-20260725T143000+0800`。名称用于定位文件，完整条件仍写入报告，避免文件名过长。

## 可直接使用的报告模板

下面模板用于 QA 发版记录；尖括号字段必须替换，离线计算的指标要注明来源。

```markdown
# PerfDog 性能测试报告

- App：<package> / <versionName>(<versionCode>) / <channel>
- Commit：<git sha 或构建号>
- 设备：<品牌与完整型号> / <SoC> / <RAM>
- 系统：Android <version> / API <level> / <build> / <security patch>
- PerfDog：<client/service version> / <USB|Wi-Fi> / <enabled metrics>
- 场景：<scene name> / <script version> / <duration> / <轮次数>
- 显示：<resolution> / <refresh rate> / <brightness> / <performance mode>
- 网络：<type> / <server region> / <weak-network profile>
- 电源：<start-end battery> / <charging state> / <external meter>
- 热环境：<ambient> / <cooling> / <start-end temperature> / <thermal state>
- 账号与数据：<account profile> / <cache state> / <download state>
- 判废规则：<predefined invalidation rules>

| 指标 | 基线中位数 | 当前中位数 | 当前 P95 | 当前最差有效轮 | 变化 | 门禁 |
|---|---:|---:|---:|---:|---:|---:|
| FPS | | | | | | |
| 1% Low FPS | | | | | | |
| FTime (ms) | | | | | | |
| Stutter (%) | | | | | | |
| AppCPU (%) | | | | | | |
| PSS (MB) | | | | | | |
| Power (mW) | | | | | | |

## 异常区间

- <label / timestamp>：<外部现象与复现步骤>

## 结论

- <通过、阻断或继续调查；只写证据能够支持的范围>

## 附件

- <PerfDog 原始文件、导出表、脚本日志、Perfetto trace、截图>
```

模板把设备状态、统计汇总和原始附件放在同一份记录中。团队可增加业务指标，但不应删掉连接方式、起止温度、脚本版本和判废规则。

## Android 17 上如何交叉核验

PerfDog 没有公开 Android 客户端每个指标的完整采集实现，因此无法从公开资料证明“Power 一定调用 PowerStats HAL（Hardware Abstraction Layer，硬件抽象层）”或“FPS 一定通过 `SurfaceFlinger --latency` 获取”。下面的 AOSP（Android Open Source Project，Android 开源项目）接口用于解释系统能够提供什么，并在字段缺失或曲线可疑时做独立核验；它们不代表 PerfDog 闭源实现的调用链。

下面这些命令用于同机排障，执行前先替换包名和 layer 名称。

```bash
adb shell dumpsys SurfaceFlinger --list
adb shell dumpsys SurfaceFlinger --latency '<layer-name>'
adb shell dumpsys gfxinfo com.example.app framestats
adb shell dumpsys thermalservice
adb shell dumpsys powerstats
adb shell dumpsys meminfo com.example.app
```

命令输出也有权限、缓存窗口和厂商实现限制。它们适合确认“系统侧是否有数据”和“变化时间是否一致”，不能要求数值与 PerfDog 一一相等。

### 帧时间：SurfaceFlinger 与 FrameTimeline

Android 17 `android-17.0.0_r1` 中，`SurfaceFlinger.cpp` 把 `--latency` 分派给 `SurfaceFlinger::dumpStats()`。该函数先输出当前 pacesetter VSYNC（SurfaceFlinger 用作节奏参考的垂直同步信号）周期，再按完整 layer 名查找目标并调用 `Layer::dumpFrameStats()`。`Layer.cpp` 随后经 `Layer::getFrameStats()` 从对应 timeline 生成 `desiredPresentTimesNano`、`actualPresentTimesNano` 和 `frameReadyTimesNano` 三列。

这条源码路径能解释几个常见现象：

- layer 名不完全匹配时，输出可能只有刷新周期，没有帧记录。
- Surface 重建后名称或序列会变化，长时脚本要重新确认目标。
- `gfxinfo framestats` 主要覆盖 Android UI Toolkit/HWUI（系统 UI 硬件加速渲染管线）参与的帧。直接使用 OpenGL ES、Vulkan、Unity 或 Unreal 的应用可能只有部分数据，Android 官方慢帧文档也明确提示了这一限制。
- Perfetto FrameTimeline 提供预期与呈现时序以及 jank 分类，更适合查“哪一段流水线错过了截止时间”。

`FrameTracer` 是 SurfaceFlinger 内记录部分帧时间戳和 fence（协调 GPU 与显示完成时序的同步对象）事件的模块，但 Android 17 的 `--latency` 路径不能简化成“直接读取 FrameTracer”。

### 温度与限频：`thermalservice`

Android 17 的 framework（系统框架层）实现位于：

`frameworks/base/services/core/java/com/android/server/power/thermal/ThermalManagerService.java`

服务通过 `Context.THERMAL_SERVICE` 发布，服务名是 `thermalservice`，所以核验命令应写成 `adb shell dumpsys thermalservice`。连接 HAL 时，Android 17 依次尝试 AIDL（Android Interface Definition Language，Android 接口定义语言）、Thermal HAL 2.0、1.1 和 1.0 兼容实现。

AIDL 接口位于：

`hardware/interfaces/thermal/aidl/android/hardware/thermal/IThermal.aidl`

它提供温度、按类型过滤的温度、CoolingDevice（降频、限流或风扇等冷却执行项）、静态阈值和温度变化回调。节流等级位于返回的 `Temperature.throttlingStatus`，并不存在 `getThrottlingStatus()` 这个 HAL 方法。AIDL 注释还强调：设备温控策略可能包含迟滞（阈值上下保留回差，避免状态反复切换）和复合条件，静态阈值不足以准确推断当前节流状态，应读取温度状态或回调。

Android 10 引入 framework thermal service 和 Thermal HAL 2.0；Android 14 将 `IThermal` 从 HIDL（旧一代 HAL 接口描述语言）迁移到 AIDL。Android 17 保留旧 HAL 回退是设备兼容策略，不表示每台设备都会暴露 CPU、GPU、NPU 和机身传感器。

### 能耗：PowerStats 与电池口径不能混为一谈

Android 17 的系统服务位于：

`frameworks/base/services/core/java/com/android/server/powerstats/PowerStatsService.java`

`PowerStatsService` 发布 `powerstats` Binder 服务，可列出代表硬件或子系统的 `PowerEntity`、能耗消费者 `EnergyConsumer` 和能量表 `EnergyMeter`，并通过 HAL 读取状态驻留时间（硬件在某个状态停留多久）或累计能量。`PowerStatsHALWrapper.getPowerStatsHalImpl()` 优先连接：

`android.hardware.power.stats.IPowerStats/default`

若 AIDL/PowerStats HAL 2.0 不可用，framework 回退到 HAL 1.0 JNI wrapper（Java 与 native 代码之间的桥接层）。是否有显示、CPU、GPU、Wi-Fi 等细分项，取决于设备 HAL；`dumpsys powerstats` 没有数据不等于 PerfDog 的整机 Battery Power 必然无数据。

PerfDog 官方把 Android Battery Power 描述为 Wi-Fi 模式下的整机 Current、Voltage 和 Power。PowerStats HAL 则可能提供硬件能量表或子系统累计能量，两者的对象、单位、采样周期和计算过程都可能不同。只有在工具厂商公开采集细节后，才能声明它们存在直接依赖。

### CPU、内存、GPU 与网络

`dumpsys meminfo <package>` 可核对 PSS 分类，但多进程应用要逐个确认进程，汇总规则也要与 PerfDog 选择项一致。CPU 还要区分 AppCPU/TotalCPU、规范化/未规范化以及采样窗口。

Android 没有向普通工具保证一套跨厂商一致的 GPU 利用率、频率和 Counter API。PerfDog 能否显示这些字段取决于机型适配与驱动接口，不能由 `gfxinfo` 反推出 GPU 使用率；`gfxinfo` 的核心用途是应用图形与帧统计。

常规 Network 的 Recv/Send 是流量观察。要解释延迟或丢包，需要 PerfDog 网络分析、抓包、服务端日志或受控弱网记录提供额外证据。

## SoloPi：复现工具，不能当作指标的权威来源

SoloPi 的开源部分提供录制回放、设备侧操作、悬浮窗采样和视觉响应分析，适合 QA 固定复现路径；一机多控（用一套操作同步控制多台设备）的实现并未完整开源。截至 2026 年 8 月 21 日，GitHub 最新发布为 `v1.0.2`（2026 年 8 月 19 日），对应 `master` 提交 `c83276286183f43d99f35cd52a6e2432bd11c7af`；发布说明只声明悬浮窗授权流程修复。当前源码基线声明 `appVersionName=1.0.2`，仍使用 AGP（Android Gradle Plugin）4.0.2、compile/targetSdk 29 和 NDK 21.1.6352462（native 开发工具链）。它可以作为较新的 APK 基线重新验收，但不能替代 Android 17 / targetSdk 37 下的权限、存储、前台服务、录屏和 16 KB 兼容检查。

讨论兼容时要分开两个问题：当前 target 29 APK 能否在某台 API 37 设备运行，以及源码升级到 targetSdk 37 后能否满足现代规则。前者只证明一组 APK、系统镜像与厂商策略共同可用，不能替代后者的构建、权限、前台服务、存储和 16 KB 验收。

### Android 17 准入项

| 关卡 | 通过条件 | 失败信号 |
|---|---|---|
| ADB 通道 | 设备内连接持续执行 shell | 授权或密钥失效、厂商断连 |
| 无障碍 | 公开 selector（控件筛选条件）能稳定读、点、输 | 多个节点冲突、回放命中错误 |
| 悬浮窗 | 可显示、拖动和关闭 | AppOp（系统对 App 单项能力的开关）拒绝、触摸冲突 |
| MediaProjection（系统屏幕捕获 API） | 每次录制重新授权并正常结束 | 黑屏、复用授权、前台服务失败 |
| 后台存活 | 切到被测 App 后服务与控制通道持续 | 脚本中止、通知消失 |
| 存储与导出 | CSV（逗号分隔表格文件）、截图和视频位于合规路径 | 旧共享目录写入失败 |
| 指标语义 | 每个字段与独立来源对读 | 固定 0、旧值、单位或进程归属错误 |
| 16 KB | 最终 APK 与动态插件均兼容 | native 库装载或插件加载失败 |

SoloPi 会通过反射调用非 SDK（未公开）接口 `AccessibilityNodeInfo.getSourceNodeId()` 来构建节点 ID，调用失败后多个节点可能都降级为 0；录屏能力还涉及 MediaProjection、`mediaProjection` 前台服务类型与 API 34+ 专用权限。迁到 targetSdk 37 时应使用公开资源 ID、类名、文本、描述、窗口和边界组合定位节点，且每次捕获都重新获得用户授权。

### 字段口径必须逐项标注

| 字段 | 公开源码路径 | 使用边界 |
|---|---|---|
| CPU | 高权限 shell 读取 `/proc/stat` 与 `/proc/<pid>/stat` | 依赖 ADB、PID（进程号）和 procfs（`/proc` 虚拟文件系统）；多进程要核对归属 |
| PSS | `getProcessMemoryInfo(pids)` | Android 10+ 普通 App 跨 UID（Linux 用户标识，通常对应 App 身份）结果受限 |
| Private Dirty（进程独占且已修改的物理页） | shell 解析 `dumpsys meminfo` | 依赖权限和文本格式 |
| 网络 | `/proc/<pid>/net/dev` 或全局 TrafficStats | 前者是 network namespace（网络命名空间）的接口计数，后者含全机流量，均不是目标进程精确字节 |
| FPS | 解析 `dumpsys gfxinfo ... framestats` | 适合现场趋势，不替代 FrameTimeline |
| 视觉响应 | MediaProjection 录屏 + 图像差异 | 点击到画面稳定，不是系统 TTID/TTFD |
| 电流/功率 | BatteryManager 与历史 sysfs（`/sys` 下的内核设备接口）路径 | 设备级数据，单位、符号和传感器需实测 |

每个结果同时记录 `verified`（已核验）、`degraded`（降级）、`unavailable`（不可用）或 `unknown`（未知）。字段有值不代表语义正确，脚本跑完也不能掩盖其中一项失效。视觉响应可以作为用户体验补充；系统启动由 Macrobenchmark 的 TTID/TTFD 与 `reportFullyDrawn()` 单列。

录制回放的性能价值来自路径一致性。固定数据、账号、刷新率和动画，使用状态等待替代固定 sleep（无条件暂停）；正式轮次前先跑正确性，通过后再启用 PerfDog、Macrobenchmark 或 Perfetto。回放失败率与性能结果分开统计，避免把等待控件超时当成 App 变慢。

## Emmagee：只用于解释历史报告

Emmagee `V2.5.1` 发布于 2017 年 8 月 25 日，上游 `master` 最后提交于 2018 年 3 月 16 日，README 已明确 Android 7.0 不受支持。其目标 PID、TopActivity（前台 Activity）、CPU、PSS、流量和电流依赖受限的进程枚举、`/proc`、跨 UID API、旧 sysfs 或 Root shell（具有 root 权限的命令环境）；这些限制会破坏整条采样链，不存在 Android 17 上“降低精度后继续使用”的可靠路线。

旧 CSV 只能在原工具、原版本、相近设备与系统条件下阅读。缺少版本和口径时，把数值作为背景材料，不重新接入、补跑或与 PerfDog/SoloPi 当前字段直接换算。

## 三种工具怎样协作

| 工具 | 主要职责 | 不应负责 |
|---|---|---|
| SoloPi | 固定操作、回放、视觉响应和现场辅助 | 根因、线上分布或跨工具指标真值 |
| PerfDog | 外部帧、CPU、内存、温度与功耗趋势 | 函数和线程级因果 |
| Macrobenchmark | 受控编译/启动状态下的可重复基准 | 第三方 App 和真实用户分布 |
| Perfetto | 调度、Binder、渲染、I/O 与系统时间线 | 业务正确性断言 |

推荐链路是 SoloPi 或确定性 UIAutomator 固定路径，PerfDog 筛选异常区间，Macrobenchmark 把 App 场景转成可重复的自动测量，Perfetto 继续定位原因。权限、Restricted Settings、无线 ADB、录屏、截图和 CSV 只在隔离设备与测试账号中使用，测试文件需要脱敏、访问控制和删除期限。

## 结论

在 Android 17 / API 37 上，PerfDog 仍适合作为低接入成本的实验室观测工具，SoloPi 适合经过逐项验收后的操作复现，Emmagee 只留作历史解释。可靠使用依赖四条纪律：

- 先确认窗口、可用指标与连接模式，再开始采集。
- 把设备、温度、刷新率、网络和脚本写进报告。
- 用帧时间分布、长帧和热稳定曲线补足平均 FPS。
- 把 PerfDog 的异常区间交给 Perfetto、Profiler、Macrobenchmark 或源码 trace 继续验证。

工具给出的数值只有在口径和条件可复现时才有工程意义。

## 参考资料

- [PerfDog 官网](https://perfdog.qq.com/)
- [PerfDog 客户端说明书](https://perfdog.qq.com/article_detail?id=10089&issue_id=0&plat_id=1)
- [PerfDog Jank、BigJank 与 Stutter 说明](https://perfdog.qq.com/article_detail?id=10162&issue_id=0&plat_id=1)
- [PerfDog Android 窗口与 FPS](https://perfdog.qq.com/article_detail?id=10081&issue_id=0&plat_id=1)
- [PerfDog Service 使用说明书](https://perfdog.qq.com/article_detail?id=10143&issue_id=0&plat_id=2)
- [PerfDog Service 指标参数映射表](https://perfdog.qq.com/article_detail?id=10210&issue_id=0&plat_id=2)
- [PerfDog 网络测试说明书](https://perfdog.qq.com/article_detail?id=10241&issue_id=0&plat_id=1)
- [AOSP Android 17 PowerStatsService](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsService.java)
- [AOSP Android 17 PowerStatsHALWrapper](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsHALWrapper.java)
- [AOSP Android 17 ThermalManagerService](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/power/thermal/ThermalManagerService.java)
- [AOSP Android 17 IThermal AIDL](https://android.googlesource.com/platform/hardware/interfaces/+/refs/tags/android-17.0.0_r1/thermal/aidl/android/hardware/thermal/IThermal.aidl)
- [AOSP Android 17 SurfaceFlinger](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp)
- [AOSP Android 17 Layer](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Layer.cpp)
- [Android Thermal mitigation](https://source.android.com/docs/core/power/thermal-mitigation)
- [Android slow rendering 与 FrameTimeline](https://developer.android.com/topic/performance/vitals/render)
- [Android Studio UI jank detection](https://developer.android.com/studio/profile/jank-detection)
- [SoloPi `v1.0.2` release](https://github.com/alipay/SoloPi/releases/tag/v1.0.2)
- [SoloPi 固定源码](https://github.com/alipay/SoloPi/tree/c83276286183f43d99f35cd52a6e2432bd11c7af)
- [SoloPi 性能工具 Wiki](https://github.com/alipay/SoloPi/wiki/Performance)
- [Emmagee `V2.5.1` release](https://github.com/NetEase/Emmagee/releases/tag/V2.5.1)
- [Emmagee 固定源码](https://github.com/NetEase/Emmagee/tree/6a382dffe74b5be6d2de78cb0c640cc67e9ce650)
- [Android MediaProjection 指南](https://developer.android.com/media/grow/media-projection)
- [Android 16 KB 页面兼容指南](https://developer.android.com/guide/practices/page-sizes)
