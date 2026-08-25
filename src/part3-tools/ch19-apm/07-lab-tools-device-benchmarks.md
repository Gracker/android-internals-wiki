---
title: 实验室测试工具与设备 Benchmark
chapter: '19.7'
section: '19.7'
status: finalized
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: '2026-08-21'
last_verified_against: PerfDog current official site plus client, Service, metric and network docs; SoloPi v1.0.2 release and pinned source; Emmagee V2.5.1 release and pinned source; Android performance docs; AOSP android-17.0.0_r1 PowerStats, Thermal and SurfaceFlinger anchors
last_rework_at: '2026-08-05T13:35:16+08:00'
last_rework_run_id: 20260805-133516-rework-bdb326bd
confidence: medium
tags:
- apm
- perfdog
- testing
- benchmark
- tools
- geekbench
- 3dmark
- device-tiering
- antutu
- pcmark
related_chapters:
- '19.0'
consolidated_from:
- src/part3-tools/ch19-apm/20-solopi-emmagee.md
- src/part3-tools/ch19-apm/22-storage-benchmark.md
- src/part3-tools/ch19-apm/16-testing-tools.md
- src/part3-tools/ch19-apm/17-device-benchmarks.md
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
- type: official
  path: https://www.geekbench.com/
- type: official
  path: https://www.geekbench.com/download/
- type: official
  path: https://www.geekbench.com/doc/geekbench6-benchmark-internals.pdf
- type: official
  path: https://www.geekbench.com/blog/2026/07/geekbench-7/
- type: official
  path: https://benchmarks.ul.com/3dmark-android
- type: official
  path: https://support.benchmarks.ul.com/support/solutions/articles/44002142020-3dmark-android-application-release-notes
- type: official
  path: https://support.benchmarks.ul.com/support/solutions/articles/44002135597-3dmark-wild-life-system-requirements
- type: official
  path: https://support.benchmarks.ul.com/support/solutions/articles/44002528073-steel-nomad-light-requirements
- type: official
  path: https://support.benchmarks.ul.com/support/solutions/articles/44002466574-3dmark-solar-bay-system-requirements
- type: official
  path: https://benchmarks.ul.com/pcmark-android
- type: official
  path: https://support.benchmarks.ul.com/support/solutions/articles/44002199189-pcmark-for-android-application-release-notes
- type: official
  path: https://browserbench.org/announcements/speedometer3/
- type: official
  path: https://www.browserbench.org/Speedometer3.1/
- type: official
  path: https://www.antutu.com/en/doc/129591.htm
- type: official
  path: https://antutu.com/download.htm
- type: official
  path: https://developer.android.com/topic/performance/performance-class
pipeline_stage: finalized
task6_state: reviewed
last_review_finalize_at: '2026-08-05T14:07:37+08:00'
last_review_finalize_run_id: 20260805-140520-70395a2d
task9_state: reviewed
task2b_state: fixed
last_idle_audit_at: '2026-08-21T18:42:54+08:00'
last_idle_audit_run_id: 20260821-183524-idle-audit-d188495e
last_consolidated_at: '2026-08-24'
---

# 实验室测试工具与设备 Benchmark

PerfDog、SoloPi 和 Emmagee 采集应用场景中的帧率、CPU、内存和功耗近似信号；设备 Benchmark 测量 CPU、GPU、Web 和存储能力。前者偏场景回归，后者偏设备基线。

## 场景测试、指标采集与自动化

### PerfDog 的位置：实验室观测工具

PerfDog 是腾讯 WeTest 提供的跨平台性能测试与分析工具。Android 测试不要求被测 App 接入 SDK（Software Development Kit，此处指需嵌入 App 的采集组件），也不要求设备 root（取得系统最高权限），适合下面几类工作：

- QA（Quality Assurance，此处指测试或质量保障人员）在固定设备和固定脚本上做发版回归。
- 开发团队快速筛出帧率、CPU、内存、温度或整机功耗异常的时间段。
- 在拿不到源码时观察第三方 App 或游戏的外部表现。
- 通过 PerfDog Service（自动化接口服务）或 CLI（命令行工具）接入实验室自动化。

截至 2026 年 8 月 14 日，官网还提供 MCP（Model Context Protocol，让 AI 客户端调用工具的标准接口）与 Skills（封装分析流程和判断规则的规则包）入口。这些入口可以调用数据、触发分析或生成报告，不会改变底层指标的采集口径，即数据来源、计算方式和适用条件；AI 给出的瓶颈判断仍需原始数据和系统 trace（按时间记录的运行轨迹）验证。

它不能代替线上 APM（生产环境中的应用性能监控）。PerfDog 覆盖的是受控环境里的单台或一组设备，线上 APM 负责汇总真实用户、真实网络和设备分布下的长期数据。它也不能仅凭一条外部曲线证明某个函数、线程或缓存策略有问题；根因仍需 Perfetto（Android 系统级时间线工具）、Android Studio、simpleperf（Android native CPU 分析器）、日志或业务埋点提供证据。

#### Android 的两种设备模式

PerfDog 官方客户端手册把 Android 设备分为“非安装模式”和“安装模式”。这里的“安装”指手机端的 `PerfDog.apk`，不是被测 App 接入组件；PC 端 PerfDog 本身采用解压运行方式。

| 项目 | 非安装模式 | 安装模式 |
|---|---|---|
| 手机端组件 | 不安装 `PerfDog.apk` | PC 端向设备安装 `PerfDog.apk` |
| 实时显示 | 手机屏幕不显示 PerfDog 浮窗 | 手机端可显示实时指标 |
| 基础条件 | USB 调试、ADB（Android Debug Bridge，Android 调试桥）授权和稳定连接 | 在基础条件上增加 USB 安装与悬浮窗权限 |
| 适用场景 | 回归、竞品测试、希望减少手机端组件干扰 | 现场观察、演示或需要手机端实时读数 |
| 常见误解 | “没有浮窗”不代表没有采集 | 手机端显示进程被系统回收，不一定会中断 PC 端采集 |

不要把辅助功能、通知读取或 `android.permission.DUMP` 写成所有版本都必须授予的固定清单。不同客户端、Service 版本和所选指标会给出不同提示，应以当前官方安装包和设备页面为准。若某个侧载组件在 Android 13 至 Android 17 上请求辅助功能或通知读取，系统可能显示 Restricted Settings（受限设置，即系统对侧载 App 敏感能力的额外确认页）；只对来源可信、用途已确认的版本开放对应入口，测试结束后撤销不再需要的权限。

#### USB 与 Wi-Fi 的采集条件不能混用

USB 模式便于保持连接和采集多数指标，但连接线会给设备充电。PerfDog 官方手册明确把 Android 的 Battery Power 放在 Wi-Fi 模式下采集：先通过 USB 建立 Wi-Fi 设备连接，连接成功后拔线，再开始功耗测试。测试报告必须写明连接方式；USB 下的电流或功耗曲线不能和断线后的 Wi-Fi 结果混在同一组基线里。

### 指标范围与可用条件

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

### 帧指标要按 PerfDog 自己的定义阅读

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

#### 先选对窗口，再谈 FPS

一个包名可能同时存在 Activity 主窗口、`SurfaceView`、`TextureView`、视频层、游戏渲染层和子进程窗口。选错窗口时，PerfDog 可能显示系统 UI、静止层或与用户所见不一致的帧率。测试开始前至少确认：

- 包名、进程名和前台 Activity。
- PerfDog 当前选择的窗口或 Surface 名称。
- 游戏、视频、小程序是否使用独立 Surface。
- 旋转、画中画、弹窗或场景切换后，目标窗口是否发生变化。

PerfDog Service 提供 `getAppWindowsMap` 一类接口，可查询 Android 应用各进程涉及的 Activity 与 SurfaceView。人工核对时也可用 SurfaceFlinger（Android 的系统显示合成服务）的 layer 列表；layer 是参与合成的显示层，其名称属于系统调试信息，不能把名称相似当成归属证据。

### 测试条件决定结果能否复现

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

### 平均 FPS 不够

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

### 功耗、温度和频率要一起看

PerfDog 的 Android Battery Power 是整机口径，不是目标 App 的独占功耗。屏幕、基带（蜂窝通信模块）、Wi-Fi、后台进程和系统服务都包含在内。对比时应固定亮度、音量、网络、账号数据和后台状态，并使用 Wi-Fi 连接后拔掉 USB。

`FPower` 在 PerfDog 数据处理中的口径是 `Power / FPS`，界面单位仍为 mW。它用于在相近场景和帧率下做归一化比较，也就是按同一尺度比较功耗；不能把它当作物理单位为焦耳的“单帧能量”。当 FPS 接近 0、场景静止或两组帧率差距很大时，这个比值也会失去解释力。

判断热降频时，推荐寻找同一时间轴上的证据组合：

1. CPU、GPU、SoC、机身或电池温度持续上升。
2. CPU Frequency Limits、CPU Clock 或 GPU Frequency 出现台阶式下降。
3. FTime P95/P99、1% Low 或 Stutter 同步恶化。
4. 在相同操作标签处，CPU/GPU 负载没有出现能够单独解释退化的新峰值。

单个温度值不等于系统已经限频。不同厂商暴露的传感器名称、安装位置与校准方式不同；同为 `CTemp` 的绝对值也不适合跨设备排名。报告应写起止温度、曲线拐点和系统 thermal status（温控等级），避免只贴峰值。

精确的能耗实验应使用外置功耗仪，并清楚区分电池端、USB 端和整机输入端的测量位置。PerfDog 更适合实验室回归中的相对变化监控。

### PerfDog、Perfetto、Profiler 与 Macrobenchmark 的分工

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

### 三类使用流程

#### 发版前回归

1. 从高端、中端和业务重点机型中选固定设备池。
2. 每个场景规定预热、冷却、账号、缓存和网络状态。
3. 当前版本与基线版本都至少运行多轮，保存每轮原始文件。
4. 使用各轮中位数比较，并同时检查最差有效轮次。
5. 超过门禁后回放曲线；需要根因时补抓 Perfetto。

#### 专项优化

1. 用场景标签缩小异常时间段。
2. 一次只改变一个可控变量，例如纹理规格、线程数或缓存策略。
3. 交替运行基线与实验版本，减少升温和测试顺序带来的偏差。
4. 同时观察目标指标和副作用，例如 FPS 改善时内存、功耗是否上升。
5. 将确认有效的场景加入持续回归。

#### 竞品分析

1. 使用同一台设备、同一系统、同一刷新率和同一网络。
2. 对齐账号等级、内容资源、画质、广告状态和下载完成度。
3. A/B 交替测试，并在每轮前恢复到相同温度区间。
4. 只报告外部可观察差异，不把现象直接写成对方的内部实现。
5. 使用测试账号和脱敏数据，遵守产品条款，不在共享报告里泄露账号、设备标识、聊天内容或内部服务器地址。

“竞品 A 在同机同场景下 FTime P95 较低”是可验证结论；“竞品 A 使用了更好的缓存算法”只是需继续验证的假设。

### 自动化：固定操作，也固定判废规则

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

### 可直接使用的报告模板

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

### Android 17 上如何交叉核验

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

#### 帧时间：SurfaceFlinger 与 FrameTimeline

Android 17 `android-17.0.0_r1` 中，`SurfaceFlinger.cpp` 把 `--latency` 分派给 `SurfaceFlinger::dumpStats()`。该函数先输出当前 pacesetter VSYNC（SurfaceFlinger 用作节奏参考的垂直同步信号）周期，再按完整 layer 名查找目标并调用 `Layer::dumpFrameStats()`。`Layer.cpp` 随后经 `Layer::getFrameStats()` 从对应 timeline 生成 `desiredPresentTimesNano`、`actualPresentTimesNano` 和 `frameReadyTimesNano` 三列。

这条源码路径能解释几个常见现象：

- layer 名不完全匹配时，输出可能只有刷新周期，没有帧记录。
- Surface 重建后名称或序列会变化，长时脚本要重新确认目标。
- `gfxinfo framestats` 主要覆盖 Android UI Toolkit/HWUI（系统 UI 硬件加速渲染管线）参与的帧。直接使用 OpenGL ES、Vulkan、Unity 或 Unreal 的应用可能只有部分数据，Android 官方慢帧文档也明确提示了这一限制。
- Perfetto FrameTimeline 提供预期与呈现时序以及 jank 分类，更适合查“哪一段流水线错过了截止时间”。

`FrameTracer` 是 SurfaceFlinger 内记录部分帧时间戳和 fence（协调 GPU 与显示完成时序的同步对象）事件的模块，但 Android 17 的 `--latency` 路径不能简化成“直接读取 FrameTracer”。

#### 温度与限频：`thermalservice`

Android 17 的 framework（系统框架层）实现位于：

`frameworks/base/services/core/java/com/android/server/power/thermal/ThermalManagerService.java`

服务通过 `Context.THERMAL_SERVICE` 发布，服务名是 `thermalservice`，所以核验命令应写成 `adb shell dumpsys thermalservice`。连接 HAL 时，Android 17 依次尝试 AIDL（Android Interface Definition Language，Android 接口定义语言）、Thermal HAL 2.0、1.1 和 1.0 兼容实现。

AIDL 接口位于：

`hardware/interfaces/thermal/aidl/android/hardware/thermal/IThermal.aidl`

它提供温度、按类型过滤的温度、CoolingDevice（降频、限流或风扇等冷却执行项）、静态阈值和温度变化回调。节流等级位于返回的 `Temperature.throttlingStatus`，并不存在 `getThrottlingStatus()` 这个 HAL 方法。AIDL 注释还强调：设备温控策略可能包含迟滞（阈值上下保留回差，避免状态反复切换）和复合条件，静态阈值不足以准确推断当前节流状态，应读取温度状态或回调。

Android 10 引入 framework thermal service 和 Thermal HAL 2.0；Android 14 将 `IThermal` 从 HIDL（旧一代 HAL 接口描述语言）迁移到 AIDL。Android 17 保留旧 HAL 回退是设备兼容策略，不表示每台设备都会暴露 CPU、GPU、NPU 和机身传感器。

#### 能耗：PowerStats 与电池口径不能混为一谈

Android 17 的系统服务位于：

`frameworks/base/services/core/java/com/android/server/powerstats/PowerStatsService.java`

`PowerStatsService` 发布 `powerstats` Binder 服务，可列出代表硬件或子系统的 `PowerEntity`、能耗消费者 `EnergyConsumer` 和能量表 `EnergyMeter`，并通过 HAL 读取状态驻留时间（硬件在某个状态停留多久）或累计能量。`PowerStatsHALWrapper.getPowerStatsHalImpl()` 优先连接：

`android.hardware.power.stats.IPowerStats/default`

若 AIDL/PowerStats HAL 2.0 不可用，framework 回退到 HAL 1.0 JNI wrapper（Java 与 native 代码之间的桥接层）。是否有显示、CPU、GPU、Wi-Fi 等细分项，取决于设备 HAL；`dumpsys powerstats` 没有数据不等于 PerfDog 的整机 Battery Power 必然无数据。

PerfDog 官方把 Android Battery Power 描述为 Wi-Fi 模式下的整机 Current、Voltage 和 Power。PowerStats HAL 则可能提供硬件能量表或子系统累计能量，两者的对象、单位、采样周期和计算过程都可能不同。只有在工具厂商公开采集细节后，才能声明它们存在直接依赖。

#### CPU、内存、GPU 与网络

`dumpsys meminfo <package>` 可核对 PSS 分类，但多进程应用要逐个确认进程，汇总规则也要与 PerfDog 选择项一致。CPU 还要区分 AppCPU/TotalCPU、规范化/未规范化以及采样窗口。

Android 没有向普通工具保证一套跨厂商一致的 GPU 利用率、频率和 Counter API。PerfDog 能否显示这些字段取决于机型适配与驱动接口，不能由 `gfxinfo` 反推出 GPU 使用率；`gfxinfo` 的核心用途是应用图形与帧统计。

常规 Network 的 Recv/Send 是流量观察。要解释延迟或丢包，需要 PerfDog 网络分析、抓包、服务端日志或受控弱网记录提供额外证据。

### SoloPi：复现工具，不能当作指标的权威来源

SoloPi 的开源部分提供录制回放、设备侧操作、悬浮窗采样和视觉响应分析，适合 QA 固定复现路径；一机多控（用一套操作同步控制多台设备）的实现并未完整开源。截至 2026 年 8 月 21 日，GitHub 最新发布为 `v1.0.2`（2026 年 8 月 19 日），对应 `master` 提交 `c83276286183f43d99f35cd52a6e2432bd11c7af`；发布说明只声明悬浮窗授权流程修复。当前源码基线声明 `appVersionName=1.0.2`，仍使用 AGP（Android Gradle Plugin）4.0.2、compile/targetSdk 29 和 NDK 21.1.6352462（native 开发工具链）。它可以作为较新的 APK 基线重新验收，但不能替代 Android 17 / targetSdk 37 下的权限、存储、前台服务、录屏和 16 KB 兼容检查。

讨论兼容时要分开两个问题：当前 target 29 APK 能否在某台 API 37 设备运行，以及源码升级到 targetSdk 37 后能否满足现代规则。前者只证明一组 APK、系统镜像与厂商策略共同可用，不能替代后者的构建、权限、前台服务、存储和 16 KB 验收。

#### Android 17 准入项

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

#### 字段口径必须逐项标注

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

### Emmagee：只用于解释历史报告

Emmagee `V2.5.1` 发布于 2017 年 8 月 25 日，上游 `master` 最后提交于 2018 年 3 月 16 日，README 已明确 Android 7.0 不受支持。其目标 PID、TopActivity（前台 Activity）、CPU、PSS、流量和电流依赖受限的进程枚举、`/proc`、跨 UID API、旧 sysfs 或 Root shell（具有 root 权限的命令环境）；这些限制会破坏整条采样链，不存在 Android 17 上“降低精度后继续使用”的可靠路线。

旧 CSV 只能在原工具、原版本、相近设备与系统条件下阅读。缺少版本和口径时，把数值作为背景材料，不重新接入、补跑或与 PerfDog/SoloPi 当前字段直接换算。

### 三种工具怎样协作

| 工具 | 主要职责 | 不应负责 |
|---|---|---|
| SoloPi | 固定操作、回放、视觉响应和现场辅助 | 根因、线上分布或跨工具指标真值 |
| PerfDog | 外部帧、CPU、内存、温度与功耗趋势 | 函数和线程级因果 |
| Macrobenchmark | 受控编译/启动状态下的可重复基准 | 第三方 App 和真实用户分布 |
| Perfetto | 调度、Binder、渲染、I/O 与系统时间线 | 业务正确性断言 |

推荐链路是 SoloPi 或确定性 UIAutomator 固定路径，PerfDog 筛选异常区间，Macrobenchmark 把 App 场景转成可重复的自动测量，Perfetto 继续定位原因。权限、Restricted Settings、无线 ADB、录屏、截图和 CSV 只在隔离设备与测试账号中使用，测试文件需要脱敏、访问控制和删除期限。

### 结论

在 Android 17 / API 37 上，PerfDog 仍适合作为低接入成本的实验室观测工具，SoloPi 适合经过逐项验收后的操作复现，Emmagee 只留作历史解释。可靠使用依赖四条纪律：

- 先确认窗口、可用指标与连接模式，再开始采集。
- 把设备、温度、刷新率、网络和脚本写进报告。
- 用帧时间分布、长帧和热稳定曲线补足平均 FPS。
- 把 PerfDog 的异常区间交给 Perfetto、Profiler、Macrobenchmark 或源码 trace 继续验证。

工具给出的数值只有在口径和条件可复现时才有工程意义。

## 设备能力基线与跨设备比较

场景工具发现应用回归后，设备 Benchmark 可解释硬件能力差异。不同版本、温度和系统策略下的分数不能直接比较。

### 先把设备基线和 App 数据分开

Benchmark（基准测试）用统一任务测量设备在特定条件下的表现。本文所说的设备基线，是在固定工具、版本和环境下保存的设备参照数据。Geekbench、3DMark、PCMark、安兔兔和 Speedometer 给设备施加固定负载，用于描述 CPU、GPU、存储或浏览器执行路径的能力。线上 APM（生产环境中的应用性能监控）、Macrobenchmark（Jetpack 宏基准测试）和业务场景 trace（按时间记录的运行轨迹）描述 App 在指定版本、账号、网络和数据规模下的体验。两类数据可以互相解释，不能互相替代。

下面三种说法都越过了证据边界：

- “Geekbench 单核高，所以 App 冷启动一定快。”
- “3DMark 稳定性高，所以列表滚动一定稳定。”
- “安兔兔总分高，所以 SQLite 事务一定快。”

更稳妥的表达是：某项设备分数提示了可能的资源上限；要判断它是否限制当前 App，还要用启动、帧时间、I/O（Input/Output，输入输出，此处主要指存储读写）、内存和功耗数据验证。

### 版本号决定分数能不能比较

测试报告至少要记录三个版本：Benchmark 应用版本、应用内测试项目版本、被测系统与驱动版本。只写“3DMark 最新版”或“Geekbench 6”不足以复现结果。

截至 2026 年 8 月 14 日，各工具的公开版本与比较规则如下。表中的 workload 指工具内一组固定的测试任务：

| 工具 | 当前状态 | 可比性规则 | Android 17 项目的建议 |
|---|---|---|---|
| Geekbench 7 | 2026-07-23 发布；官方下载页要求 Android 12+、4 GB RAM | CPU、GPU 工作负载和多核规则相对 Geekbench 6 均有改动，不能把两个大版本的分数放进同一时间序列 | 新建 Geekbench 7 基线；已有 Geekbench 6 数据冻结在独立字段 |
| Geekbench 6 | 保留其公开 Benchmark Internals 作为可审计的工作负载样本 | 同一大版本也要保存精确应用版本；没有官方兼容声明时，按精确版本比较 | 用于维护既有 GB6 设备库，不再向 GB7 字段写入 |
| 3DMark Android | 当前应用版本 2.6.5056，发布于 2026-04-07 | 应用版本和 Wild Life、Steel Nomad Light 等测试版本是两套编号；比较时以同一测试及其版本为准 | 从设置页同时抄录应用版本、测试名、测试版本和模式 |
| PCMark Android | 当前应用版本 3.1.4113，发布于 2026-06-15 | 3.1 与 3.0 的总分大致可比，但官方仍建议使用同一 workload 版本；Work 3.0、Storage 2.0 不可与旧测试混比 | 新报告固定 Work 3.0 或 Storage 2.0，并保存 System WebView 版本 |
| 安兔兔 | 官方下载区当前为 V11.1.4，发布于 2026-06-30 | V11 和 V10 因测试项变化不可比；跨 OS 的分数也不用于工程回归（检查版本变更是否引起性能退化） | 总分仅作沟通标签，定位原因时查看 CPU、GPU、MEM、UX 子项及 App 实测 |
| Speedometer | 当前稳定版本为 3.1 | 3.1 修正了测量框架；不要把 3.0 和 3.1 混在一组 | 固定 Speedometer、浏览器或 WebView、系统和电源状态 |
| Vellamo | Qualcomm 的可核验官方资料停留在 2012 年的套件介绍，没有当前版本依据 | 历史报告只能在原工具、原版本和相近环境内阅读 | 冻结旧数据，不再补录 Android 17 新设备 |

Geekbench 7 于 2026 年 7 月 23 日发布。当前设备库若已积累大量 Geekbench 6 数据，不应为追新而覆盖旧列；增加 `geekbench_major=7` 和新分数字段，等样本覆盖率足够后再迁移设备分档规则。

### 工具分工：先选问题，再选分数

| 要回答的问题 | 首选信号 | 它没有回答什么 |
|---|---|---|
| 单线程通用 CPU 容量怎样 | Geekbench CPU single-core（单核） | App 主线程具体花在 Java、Binder（Android 跨进程通信）、I/O 还是锁等待 |
| 受控工作负载的多线程吞吐怎样 | Geekbench CPU multi-core（多核） | App 是否具备可并行任务、线程池是否合理 |
| GPU Compute（通用计算）容量怎样 | Geekbench GPU（Vulkan / OpenCL） | 图形渲染帧率、合成、触控延迟 |
| 重图形短时性能怎样 | 3DMark 指定图形测试 | 普通 View 或 Compose 页面是否卡顿 |
| 重图形持续性能怎样 | 3DMark Stress Test 的循环曲线 | App 自身的帧生成、资产加载和网络抖动 |
| WebView、视频、文档、图片、数据处理的组合表现怎样 | PCMark Work 3.0 子项 | 单个业务页面的启动或交互时延 |
| 内部存储、外部存储和 SQLite 组合表现怎样 | PCMark Storage 2.0 子项 | 某个文件系统调用、Room 查询或数据库事务的根因 |
| 浏览器前端交互执行路径怎样 | Speedometer 3.1 | 网络速度、服务端耗时、App 内 WebView 的完整链路 |
| 面向大众的设备综合档位怎样 | 安兔兔 V11 总分与子项 | 单项资源瓶颈和 App 性能因果 |

分数命名也要带上工具语义。`gpu_score` 这样的字段会把 Geekbench Compute 和 3DMark Graphics 混在一起，建议写成 `gb7_vulkan_compute`、`3dmark_wild_life_v1_score` 和 `3dmark_wild_life_stability`。字段名中的工具、大版本、测试和 API 共同说明分数来自哪套规则。

### Geekbench：把分数理解为代理变量

代理变量是间接反映目标能力的信号。它可以帮助提出假设，不能替代 App 自身的直接测量。

#### Geekbench 6 的单核分数由什么组成

Geekbench 6 的公开内部文档说明，CPU 总分由 integer（整数）和 floating-point（浮点）两部分加权，权重分别为 65% 和 35%；各子测试先按参考系统归一化，也就是换算到统一基准，再组合成分数。分数翻倍表示这套 Benchmark 工作负载中的性能翻倍，不表示任意 App 代码都快一倍。

下表把公开工作负载映射到 Android 工程问题。表中的“可提出假设”只用于确定下一步测量方向：

| Geekbench 6 工作负载 | 主要资源或算法 | 可提出的 Android 假设 | App 内验证方式 |
|---|---|---|---|
| File Compression（LZ4、ZSTD、AES、SHA1） | 整数、内存访问、压缩与加密指令 | 安装包解压、离线资源解压或同步加密可能受 CPU 限制 | 对 App 使用的压缩库、数据规模和线程模式做 Microbenchmark（Jetpack 微基准测试） |
| Navigation（Dijkstra、OpenStreetMap 数据） | 图算法、分支和内存访问 | 离线路径规划或大型关系图计算可能受单线程容量影响 | 对业务图规模采样，并在目标机型上测端到端耗时 |
| HTML5 Browser | 受控的 HTML/JavaScript 负载 | 轻线程网页计算可能随单核档位变化 | 用目标 WebView 版本跑页面 trace；不能把该子项当作 Chrome 或 WebView 分数 |
| PDF Renderer（PDFium） | 文档解析与栅格化 | PDF 首屏或翻页可能受 CPU 和内存共同影响 | 固定 PDF 文件，在 App 使用的 PDF 组件中测首屏和逐页时间 |
| Photo Library / Photo Editor | 图片编解码、SQLite、图像处理及部分 ML | 相册扫描、缩略图生成或编辑可能受 CPU、内存和指令集影响 | 复用业务图片格式、分辨率和模型做 Macrobenchmark 或业务基准 |
| Clang、Text Processing、Asset Compression | 编译、正则、SQLite、纹理及几何资产压缩 | 文本处理、开发工具或图形资源处理流程可能有相近计算特征 | 对业务库直接基准；不要把 Text Processing 等同于 JSON 解析 |

“单核分数影响 JSON 解析”这句话过于确定。Geekbench 6 没有以你的 JSON 库、序列化模型和数据规模运行；它只能给出通用单线程容量线索。JSON、protobuf（二进制序列化格式）、XML inflate（从布局 XML 创建 View）、Compose measure/layout（测量与布局）和 `RecyclerView` bind（把数据绑定到列表项）仍要分别测量。I/O 等待、锁竞争或 Binder 往返占比高时，单核分数的解释力会更弱。

ARM 设备还可能按运行时能力使用 AES、SHA、FP16、Dot Product、I8MM 等加密、半精度浮点、点积或整数矩阵指令。两个设备的分差有时来自特定指令路径，而业务实现未必走同一条路径。跨 SoC（System on Chip，系统级芯片）解释子项时，要核对 App 使用的库、ABI（Application Binary Interface，应用二进制接口，例如 `arm64-v8a`）、编译选项和硬件加速路径。

#### 多核分数不是“所有核心相加”

Geekbench 6 相对 Geekbench 5 改用 shared-task（共享任务）模型，让多个线程协作处理同一批任务，纳入线程协调和共享数据带来的成本。2026 年 7 月 23 日发布的 Geekbench 7 又调整了规则：只有在对应现实任务适合并行时才进入多线程套件，例如其 HTML5 Browser 不进入多线程测试。

因此，GB6 和 GB7 的多核分数都不能直接回答“App 开八个线程会快多少”。要先检查任务依赖、可并行比例、调度优先级、线程池拥塞和内存带宽。主线程上的串行关键路径不会因多核总分高而自动缩短。

#### Compute 分数不等于图形帧率

Geekbench 6 的 GPU Benchmark 通过 Vulkan 或 OpenCL 运行计算工作负载，并将子项组合成 Compute 分数。它适合为图像处理、部分 ML（Machine Learning，机器学习）、视频处理或通用 GPU 计算提出容量假设。

游戏和 Android UI 还涉及顶点与像素着色、光栅化、纹理、内存带宽、SurfaceFlinger 合成、显示刷新和帧调度。Compute 分数没有覆盖从 App 生成帧到屏幕显示的完整流程。分析渲染问题时应改看 3DMark Graphics、Perfetto、FrameTimeline 和 App 自身帧数据。

### 3DMark：峰值、持续性能和温控要一起看

#### 选择设备能稳定完成的测试

3DMark Android 会根据设备能力推荐测试。Android 17 项目常见选择如下：

| 测试 | 适用对象 | 读取结果时的重点 |
|---|---|---|
| Wild Life | 支持 Android 10、Vulkan 1.1 且至少 3 GB RAM 的主流设备 | 短时 Graphics score、平均帧率以及同型号分布 |
| Wild Life Extreme | 能稳定完成更重 Vulkan 负载的高性能设备 | 重负载下的性能上限；低帧率本身不代表测试异常 |
| Steel Nomad Light | Android 10+、8 GB RAM、Vulkan 1.1 的高性能移动设备 | 更重的非光追现代图形路径；不满足门槛的设备改用较轻测试 |
| Solar Bay | Android 12+、4 GB RAM，并支持 Vulkan 1.1 ray query 的设备 | ray query 是查询光线与场景相交结果的光追能力；它不覆盖普通设备，也不代表传统栅格化帧率 |
| Sling Shot / Sling Shot Extreme | 旧设备与历史 OpenGL ES 数据 | 只维护历史序列，不与 Wild Life 或新测试换算 |

标准测试、Extreme、Stress 和 Unlimited（离屏，即不受设备屏幕分辨率限制）模式是不同负载。即使名称相近，也要分别存储，不能只保留一个 `3dmark_score`。

#### Stability 需要和帧率共同解释

Wild Life 的普通 Benchmark 用于观察短时间高性能；Stress Test 连续运行二十轮，每轮称为一个 loop，用于观察性能和温度随时间的变化。UL 面向 PC Stress Test 结果页公开的 Frame Rate Stability 定义是最低循环平均帧率除以最高循环平均帧率，再乘以 100%；Android Wild Life 官方说明更强调二十轮曲线。移动端报告应保存应用显示的 stability 和整条曲线，不要把 PC 页面给出的 97% pass 条件照搬成 App 的产品门槛。

这个比例有两个容易忽略的边界：

- 98% stability 可能来自“每一轮都只有较低帧率”，说明稳定但不够快。
- 很高的首轮帧率配合 65% stability 可能说明峰值强、持续性能弱。

报告至少同时列出 best loop（最高轮）、worst loop（最低轮）、stability、每轮帧率曲线和热状态。若要解释游戏体验，还要在游戏自身固定场景中采集帧时间、CPU/GPU 频率、功耗和温控事件。

#### 热数据不要只抄一个温度

Android 17 平台的 `ThermalManagerService` 聚合 Thermal HAL（Hardware Abstraction Layer，硬件抽象层）上报并维护当前 thermal status（温控等级），`PowerManager.getCurrentThermalStatus()` 向应用提供从 `NONE` 到 `SHUTDOWN` 的状态。`THERMAL_STATUS_NONE` 只表示当前没有进入节流状态，不表示设备已经回到相同初始温度。

内核侧以 `android17-6.18-2026-06_r6` 为源码锚点。Linux thermal sysfs（`/sys` 下的内核设备接口）文档说明，`thermal_zone` 暴露当前温度与 trip point（触发温控动作的阈值），cooling device（降频、限流或风扇等冷却执行项）参与温控。量产设备对传感器名称、可见性和温度标定的实现不同，不能把两个厂商的 `thermal_zone0` 数值直接横向比较。

温控测试更适合记录同一设备的相对变化：起始表面温度、每轮温度或 thermal status、首轮到稳定轮的性能衰减，以及冷却回基线所需时间。

### PCMark：工作负载比总分更有解释力

PCMark Android 3.1.4113 是当前应用版本，Work 3.0 包含 Web Browsing、Video Editing、Writing、Photo Editing 和 Data Manipulation；Storage 2.0 覆盖内部存储、外部存储和 SQLite 数据库操作。

这些子项比总分更接近 Android 业务，但仍需注意实现差异：

- Web Browsing 3.0 使用系统 Android WebView。系统更新后，即使 PCMark 应用版本不变，执行引擎也可能变化，因此要记录 `com.google.android.webview` 或设备实际 WebView provider（提供 WebView 实现的应用包）版本。
- Video Editing 3.0 使用 `MediaCodec`、ExoPlayer 和 OpenGL ES 2.0。它反映一套固定的媒体处理流程，不代表 App 的编解码参数、滤镜和文件格式。
- Writing 3.0 使用 Android `EditText` 与 `PdfDocument`。它适合作为文档工作负载背景，不能替代业务编辑器测量。
- Storage 2.0 的 Database 子项使用 SQLite，但 App 的 schema（表、列和约束的结构）、index（索引）、transaction（事务）、WAL（Write-Ahead Logging，预写式日志）、文件系统和缓存状态都会改变结果。

PCMark 3.1 发布说明指出，3.1 与 3.0 总体分数大致可比，同时明确建议在相同 workload 版本间比较。工程回归应遵守更严格的后一句：版本或 workload 变化就切分时间序列。Work 3.0、Storage 2.0 也不能与 Work 2.0、Storage 1.0 混比。

### 存储专项 Benchmark：协议比工具名重要

存储工具只能描述“这台设备在这套路径、参数和缓存状态下”的 I/O 背景，不能指出 App 哪个文件、线程或 SQL 慢，也不能证明一次 `write()` 已经持久化到闪存。从分数到业务结论还要补 App 路径、调用栈、事务、查询计划与用户场景。

#### AndroBench、A1 SD Bench 与现代替代

AndroBench 可公开核对的协议源于 2011 年：顺序读文件 32 MB、写文件 2 MB，随机测试使用 4 KiB 操作，每项三轮平均。这样的文件规模很容易被 page cache（内核把近期文件内容保留在内存中的页缓存）、write buffer（暂存待写数据的缓冲区）和设备只能短时间维持的高吞吐主导。A1 SD Bench 公开描述了 Quick、Longer、Accurate、Random I/O、RAM、SD/USB 与自定义路径，但没有足够信息说明 cache、同步、block size、预分配和汇总算法。

两者保留用于解释历史报告，不作为 Android 17 新设备库的默认基线。因历史连续性而补测时，要保存 APK 版本、文件 hash（用于识别文件内容的指纹）、模式和全部参数。

现代设备实验室优先选择协议可审计的工具或业务自建基准：

- CPDT（Cross Platform Disk Test）可以配置文件大小、4 KiB random、write buffering（写入缓冲）与 in-memory caching（内存缓存），并导出时序；仍需固定源码版本，并先验证该版本能否在 API 37 上正确运行。
- PCMark Storage 2.0 提供内部、外部与 SQLite 的组合 workload，但输出仍是工作负载分数，不代表 UFS（Universal Flash Storage，移动设备常用的闪存接口）设备本身的原始吞吐。
- 最有预测力的方案是在目标 App 实际目录中复用相同文件格式、SQLite schema、事务、同步语义和线程模型。

#### 四类指标与必要参数

IOPS（Input/Output Operations Per Second）表示每秒完成的 I/O 次数，latency 表示单次操作的等待时间。两者都要连同 block size（每次读写的数据块大小）和 QD（queue depth，队列中同时等待的请求数）记录。`direct` 表示尽量绕过页缓存，`buffered` 表示经过页缓存；`sync` 语义则说明何时停止计时，例如数据只进入内核缓存，还是等待同步调用返回。

| 指标 | 必填参数 | 可提出的假设 | 不能直接解释 |
|---|---|---|---|
| 顺序读吞吐 | 文件、buffer size、cache 状态、并发 | 大资源连续读取上限 | 大量小文件冷启动 |
| 顺序写吞吐 | 文件、buffer size、direct/buffered、sync 语义 | 下载、导出、批量日志 | 单事务 commit 延迟 |
| 随机读 IOPS/latency | block、范围、QD、线程、分布 | 小块读取与索引背景 | 目录扫描和反序列化 CPU |
| 随机写 IOPS/latency | 上述参数 + 同步频率和预分配 | 数据库日志与元数据更新风险 | 业务事务设计是否合理 |

IOPS 不带 block size 和 QD 没有工程意义。吞吐越高越好，但较差结果位于数值低的一侧，多轮报告应看 median（中位数）与 P10（第 10 百分位）；latency 越低越好，单次操作可看 p50、p95 和 p99。MAD（median absolute deviation，中位数绝对偏差）描述样本相对中位数的离散程度。只有五轮时，分位数还不稳定，宜报告 median、min/max 与 MAD。

#### 路径、缓存与持久化语义

| 路径 | Android 17 访问模型 | 结果边界 |
|---|---|---|
| `filesDir` / `cacheDir` / database | App 私有内部存储 | 接近业务私有数据，但仍包含加密、文件系统和内核缓存 |
| `getExternalFilesDir()` | App-specific external（系统分配给该 App 的外部存储目录） | 可能位于共享或可移除卷，不能假设永远可用 |
| MediaStore | 媒体集合、权限与 ContentProvider | 包含 Binder、元数据和介质路径 |
| SAF（Storage Access Framework） | 用户授权的 URI（资源标识符）或 directory tree（目录子树） | 包含 DocumentsProvider（向系统暴露文档的内容提供程序）与底层介质 |
| SD / USB | 卷、文件系统、读卡器和授权 | 不只代表卡片本身 |
| RAM | 内存复制或内存文件 | 不进入闪存排名 |

普通 buffered write 返回时，数据可能只进入 page cache。`fsync`、`fdatasync` 等调用要求内核在返回前将相关数据写到存储设备，`fsync` 还会处理恢复文件所需的元数据；测试协议没有同步步骤时，不能宣称写入已经安全持久化。cold read（缓存中没有目标数据）、warm read（缓存中已有数据）和 reboot 后首次读取是三组不同实验；量产 user build（面向普通用户的系统构建）不应为跑分操作 `drop_caches`（主动清空内核缓存）。剩余空间、文件系统 GC（回收无效存储块）、discard（通知存储设备哪些块可回收）、加密、温度、后台媒体扫描和系统更新都要记录。

SQLite 分数也使用工具自己的表、索引、journal（事务日志）和 transaction。业务验证要检查批量写是否放在同一 transaction，并记录 WAL、`synchronous`（写入持久化强度）、checkpoint（把 WAL 内容合并回主数据库）、N+1 查询（一次主查询后又逐行追加查询）、索引和 `EXPLAIN QUERY PLAN`（查看 SQLite 查询计划）。测试应使用真实数据记录 p50/p95 latency 与 rows scanned（实际扫描的行数）。

存储 Benchmark 只提供设备背景。Perfetto 的 database/文件系统事件、Matrix IO Canary（辅助定位主线程等 I/O 问题的 Android 工具）或 StrictMode（发现主线程磁盘与网络访问的系统诊断机制）可以给出发生时间和调用位置，再用 A/B 业务测试（保持其他条件一致，比较修改前后）验证效果。比如，先发现设备随机写较慢，再由 trace 定位启动主线程的重复小写入，最后验证改成后台批量写后 P95 回落，才形成较完整的证据链；单张跑分截图做不到。

### 安兔兔：总分只保留为沟通标签

安兔兔 V11 包含 CPU、GPU、MEM（内存）和 UX（用户交互体验）等组合测试。官方 V11 公测说明明确写出，V11 因测试项调整不能与 V10 比较，并给出 27℃±1℃、电量 80% 以上、亮度 300 nit 的示例测试条件；nit 是屏幕亮度常用单位，1 nit 等于 1 cd/m²。这里的条件说明跑分对环境敏感，不表示所有团队都必须采用相同电量。

若产品、测试和市场已经习惯用安兔兔总分描述设备档位，可以保留总分，但设备字典还要保存大版本和子项。工程排查从相关子项开始：

- 启动慢优先检查 CPU 单线程、存储和 App 启动 trace。
- 游戏掉帧优先检查 GPU 子项、持续性能和游戏帧时间。
- 数据库慢优先检查存储与业务 SQL，不从 UX 总分推断。
- 后台恢复或 OOM（Out Of Memory，内存耗尽）优先检查物理内存、进程状态和 App 内存峰值。

两个设备总分相近时，一个可能是 CPU 强、存储弱，另一个是 CPU 弱、GPU 强。总分把不同资源结构压成一个数，会隐藏 App 所依赖的那一维。

### Speedometer：浏览器分数不能代替 WebView 实测

Speedometer 3.1 通过模拟用户操作，测量 TodoMVC（一组用不同前端技术实现的待办事项示例应用）、富文本编辑器、图表和新闻站点等 Web 应用负载的响应性。它不测网络吞吐，也不覆盖 Web Worker（在后台线程执行 JavaScript 的浏览器机制）中并发异步工作的完整成本；官方还明确说明，不能用它比较 JavaScript 框架优劣。

Android 上用 Chrome 跑出的分数描述“这台设备 + 这个 Chrome 版本 + 当前配置”的浏览器路径。App 内 WebView 的 provider、版本、启动方式、缓存、JS bridge（JavaScript 与原生代码之间的调用接口）、页面资源和进程模型都可能不同。需要判断 App 的 Web 页面时，建议补一套受控 WebView 容器，固定 provider 与页面资源，并采集 WebView/Chromium trace。

Speedometer 官方建议使用最新稳定浏览器、干净 profile（不受扩展、历史缓存和自定义设置干扰的独立用户配置）、关闭其他标签页和后台程序、保持页面前台，并在两次测试间按需冷却。移动设备测试还要把充电状态记入报告；若团队选择不充电以避开发热，也可以，但同一比较组必须保持一致。

### Vellamo：冻结历史，不推断“当前版本”

Qualcomm 2012 年官方资料把 Vellamo 描述为包含 HTML5 与 Metal 等章节的移动 Benchmark 套件。该资料可用于解释旧报告中的字段，不能证明它在 Android 17 上仍有维护、兼容性或稳定测试规则。

处理旧数据时保留 APK hash、工具版本、Android 版本、设备和原始分数。新设备不再补跑，也不尝试把 Vellamo 分数换算成 Speedometer、Geekbench 或 PCMark 分数。

### Performance Class 只能做能力下限标签

Android 的 Media Performance Class（MPC，媒体性能等级）从 Android 12 体系引入。它用 CDD（Compatibility Definition Document，Android 兼容性定义文档）规定能力要求，并由 CTS（Compatibility Test Suite，兼容性测试套件）验证。Android 17 / API 37 的 AOSP（Android Open Source Project）`Build.VERSION.MEDIA_PERFORMANCE_CLASS` 仍从设备属性读取声明值，未声明时返回 0。Jetpack Core Performance 是读取设备性能等级的 Jetpack 库，可以从系统 build 信息或 Google Play services（Google Play 服务组件）查询兼容等级。

截至 2026 年 8 月 14 日，Android 官方公开定义的等级是 30、31、33、34、35，其中没有 MPC 32；0 表示未定义。Performance Class 可向前兼容：设备升级到 Android 17 后，仍可能报告它原先满足的 33、34 或 35。不要自行创造“MPC 37”，也不要把 Android 版本号当作设备必然报告的等级。

| 信号 | 可以表达什么 | 不能表达什么 |
|---|---|---|
| Media Performance Class | CDD/CTS 约束下的媒体、相机、内存、I/O、显示等能力下限 | CPU 综合排名、App 启动 P95、列表慢帧率 |
| Geekbench / 3DMark / PCMark | 固定测试里的 CPU、GPU、工作流和存储代理信号 | 业务代码路径的直接结果 |
| 线上 APM 和 App 基准 | 指定 App 版本与真实用户/受控场景的体验 | 脱离样本分布后的通用硬件排名 |

因此，Performance Class 适合做设备字典中的官方标签，不适合作为唯一档位。服务端要把它和 CPU、GPU、RAM、存储、热稳定性及线上表现组合使用。

### 可复现测试规范

下面是一套适合团队设备实验室的起始规范。次数和温度窗口不是 Android 或 Benchmark 厂商规定，可在试运行后按方差调整。

#### 记录设备身份

- 设备品牌、市场型号、硬件 SKU（厂商用于区分配置的商品编号）、SoC、RAM、存储容量；同名机型的不同 SoC 或内存版本分开。
- Android 版本、build fingerprint（唯一标识系统构建的字符串）、安全补丁、基带、GPU driver（图形处理器驱动版本）、实际 kernel release（内核版本）。知识库源码锚点是 Android 17 / API 37 / `android-17.0.0_r1` 与 `android17-6.18-2026-06_r6`，测试报告仍应记录量产机的实际构建。
- Benchmark 应用版本、测试名、测试版本、API 或运行模式。Web 测试另记浏览器或 WebView provider 版本。

#### 固定运行条件

- 固定屏幕分辨率、刷新率和亮度；关闭自动亮度。
- 固定充电或放电状态、电量区间、性能/游戏模式、省电模式和散热配件。
- 固定室温与设备摆放；每组开始前等待表面温度回到约定窗口，并记录 thermal status。
- 完成系统更新和应用优化后再测试；关闭无关应用、下载、录屏、日志洪泛和同步任务。
- 需要联网的测试固定接入点与网络条件；不需要联网的负载避免让后台网络成为噪声。

这些 shell 命令用于保存 Android 17 设备的基本身份与热状态快照：

```bash
adb shell getprop ro.build.fingerprint
adb shell getprop ro.build.version.release
adb shell getprop ro.build.version.sdk
adb shell getprop ro.build.version.security_patch
adb shell uname -r
adb shell dumpsys battery
adb shell dumpsys thermalservice
adb shell dumpsys webviewupdate
```

`dumpsys thermalservice` 能显示框架服务掌握的 thermal status 与温度信息，但不同厂商的字段和传感器可见性不同。报告应保存原始输出，不要只提取一个跨设备比较的“CPU 温度”。

#### 重复、取值与作废规则

- 短测试建议预热一轮后至少保留 5 个有效轮次；报告中给出中位数、最小值、最大值和 MAD，以说明典型结果与波动范围。
- 长时间 Stress Test 建议在完整冷却后做至少 3 个独立 session（从冷却、启动到完成测试的一次完整实验）；每个 session 保留全部循环曲线。
- 轮次更多时可以报告 P10/P90，即第 10 和第 90 百分位；5 个样本不足以形成稳定的分位数分布。
- 来电、通知弹窗、失去前台、后台安装、系统更新、意外网络切换或测试崩溃都应作废并写明原因。
- 热状态或起始温度不在约定窗口时不并入同一比较组。`THERMAL_STATUS_NONE` 不能单独证明温度已经复位。

平均值容易被一次异常高分或低分拉动，中位数更适合小样本跑分。任何“回归 3%”的结论都要先和同设备、同版本的自然波动比较。

### 用分项能力建立机型分层

设备分层指按相近能力把设备分组。每台设备应保存能力向量，也就是一组相互独立的 CPU、GPU、存储、内存和持续性能字段，不能只保存一个综合档位：

| 维度 | 建议来源 | 线上问题 |
|---|---|---|
| CPU single | GB6 或 GB7 的独立版本序列 | 主线程 CPU 计算、启动中的串行计算 |
| CPU multi | 同一 Geekbench 大版本 | 可并行图片、压缩、媒体或后台批处理 |
| GPU graphics | 3DMark 指定测试与模式 | 游戏、地图、相机特效和重图形页面 |
| GPU compute | Geekbench Vulkan/OpenCL 或业务计算基准 | 图像、部分 ML 与通用计算 |
| Storage | PCMark Storage 2.0 子项与业务 I/O 基准 | 冷启动文件、SQLite、缓存和资源加载 |
| RAM | 物理内存、低内存设备标志和线上采集 | OOM、后台恢复、缓存上限 |
| Thermal | 3DMark Stress 曲线、thermal status 和业务长测 | 游戏、视频、直播的持续性能 |
| MPC | Jetpack Core Performance | 官方能力下限与功能开关参考 |

#### 四档不是四个固定分数线

入门、中端、高端、旗舰的边界应从团队已冻结版本的设备样本分布中计算。例如，可在同一国家/渠道覆盖集内按关键维度的 P20、P50、P80（第 20、50、80 百分位）切四档，再由线上数据校正。换 Geekbench 大版本、3DMark 测试或设备覆盖集后，要重新计算边界。这里的性能预算，是每档设备对启动时延、慢帧率、内存等指标设定的上限。

| 档位 | 设备能力特征 | 性能预算与产品策略 |
|---|---|---|
| 入门 | 一个或多个关键维度位于低分位，常伴随小 RAM 或弱存储 | 核心路径采用最严格预算；默认降低预取、并发、图片规格和高成本效果 |
| 中端 | 关键维度覆盖主流下半区 | 维持完整核心功能；对非必要动画、媒体和缓存设置上限 |
| 高端 | 关键维度位于主流上半区且持续性能稳定 | 可开放更高质量资源，但仍受线上耗时和内存预算约束 |
| 旗舰 | 多个相关维度处于高分位 | 可试验高规格效果；不能因档位高而跳过启动、慢帧、功耗和温控验收 |

分档应围绕业务选择维度。资讯 App 可能重视 CPU single、Storage 和 RAM；游戏更重视 GPU graphics 与 Thermal；离线视频编辑还要加入媒体编解码业务基准。不存在一套对所有 App 都合理的总分权重。

### 把设备字典连接到线上数据

不建议让每个客户端在线跑 Benchmark，也不建议在每条 APM 事件里上传跑分。团队可以维护版本化设备字典，也就是一张从设备与系统标识映射到能力字段的表。客户端只上报已有标识，分析平台再关联对应字段。

下面是一个仅用于说明字段关系的虚构事件，不代表 Pixel 8 或 Tensor G3 的实测结论。`capability_schema` 的日期只是规则版本名示例，不表示这份文档仍以 2026 年 7 月为验证日期：

```text
event: app_start
app_version: 12.4.0
device_model: Pixel 8
soc: Tensor G3
ram_gb: 8
android_sdk: 37

device_dictionary_join:
capability_schema: 2026-07-gb7
cpu_single_bucket: high
gpu_graphics_bucket: high
storage_bucket: medium
thermal_bucket: medium
mpc: 35
```

`capability_schema` 让历史事件始终能还原当时的分层规则。设备字典还应区分同型号的 SoC、RAM、存储和区域版本；无法精确匹配时写入 `unknown`，不要凭市场名称猜测。

#### 关联示例不能当作因果结论

假设某次分析得到以下虚构结果：

| CPU single 档位 | 冷启动 P95 | 样本量 |
|---|---:|---:|
| low | 1,480 ms | 820,000 |
| medium | 1,090 ms | 1,760,000 |
| high | 810 ms | 940,000 |

这个表只说明分档和启动 P95 同时变化。低档设备还可能拥有更慢存储、更小 RAM、旧系统或不同地区网络。分析时应固定 App 版本与启动计算规则，并按存储、RAM、Android 版本、网络和地区分别比较；再用区间趋势或 Spearman 秩相关（比较两组数据排序的一致程度）判断关系是否稳定。需要证明某段 CPU 代码受限，还要回到 Macrobenchmark、trace 或 Microbenchmark。

#### 灰度、预算和告警

- 灰度发布指先向一小部分用户开放版本。抽样时要覆盖各能力档位；新效果可以从小比例高档设备开始，但向所有符合条件的用户发布前必须覆盖入门档。面向低端优化的版本应优先保证低档样本量。
- 性能预算从真实用户分布和业务目标制定。例如按档位分别约束冷启动 P95、慢帧率、OOM 率和峰值内存，不从 Geekbench 分数换算毫秒。
- 告警阈值使用同 App 版本、同能力档位的历史波动。Benchmark 版本变化只触发设备字典重算，不直接触发线上性能告警。
- 功能降级由明确能力维度驱动。例如 GPU/thermal 弱时降低实时特效质量，RAM 小时降低缓存；不要用安兔兔总分作为单一开关。

### 综合分误导的一个例子

假设设备 A 的 CPU single 很强、存储随机读写较弱，设备 B 的 CPU single 较弱、存储较强，两者恰好拥有相同综合分。图片解码计算重的 App 可能在 A 上更快；冷启动读取许多小文件的 App 可能在 B 上更快。相同总分无法给出统一排序。

工程报告应从业务关键路径反推资源维度，再选择子项。综合分可以留在摘要中，结论和行动项必须引用相关分项及 App 证据。

### 历史数据与工具迁移

工具停更、测试项目升级或评分规则改变时，按下面的规则处理：

- 冻结旧序列，保留原始分数、单位、应用版本、测试版本、日期和运行条件。
- 新工具或大版本使用新字段，不覆盖历史分数。
- 厂商没有发布换算公式时，不做经验换算，也不把百分位强行对齐成“等价分数”。
- 分层迁移期并行维护两套设备覆盖率，通过线上指标验证新分档后再切换配置。
- 旧工具只用于解释原报告，不为 Android 17 新设备补跑 Vellamo 等历史项目。

Geekbench 6 到 7、安兔兔 V10 到 V11、PCMark Work 2.0 到 3.0 都应按大版本迁移处理。3DMark 还要在应用版本之外维护测试版本，避免应用自动更新后误判数据已经跨代。

### 测试报告模板

下面的模板用于保存可复现信息和结论边界。`report_id` 中的日期只是命名示例，实际报告要替换为测试日期：

```yaml
report_id: android-benchmark-2026-07-25-001
device:
  brand: ""
  model: ""
  sku: ""
  soc: ""
  ram_gb: 0
  storage_gb: 0
software:
  android_release: "17"
  api_level: 37
  build_fingerprint: ""
  security_patch: ""
  kernel_release: ""
  gpu_driver: ""
benchmark:
  app_name: ""
  app_version: ""
  test_name: ""
  test_version: ""
  api_or_mode: ""
conditions:
  room_temperature_c: null
  start_surface_temperature_c: null
  battery_percent: null
  charging: false
  brightness_nit: null
  refresh_rate_hz: null
  performance_mode: ""
  thermal_status_start: ""
results:
  warmup_runs: 1
  valid_runs: []
  median: null
  min: null
  max: null
  mad: null
  invalid_runs: []
app_validation:
  metric: ""
  app_version: ""
  scenario: ""
  result: ""
conclusion:
  supported_claim: ""
  unsupported_inference: ""
```

模板把设备基线与 App 验证分开保存。`supported_claim` 只写当前数据能支持的判断，`unsupported_inference` 主动记录容易被误读的推论。

### 源码与官方资料

- [Geekbench 7 发布说明](https://www.geekbench.com/blog/2026/07/geekbench-7/)
- [Geekbench 当前下载要求](https://www.geekbench.com/download/)
- [Geekbench 6 Benchmark Internals](https://www.geekbench.com/doc/geekbench6-benchmark-internals.pdf)
- [3DMark for Android](https://benchmarks.ul.com/3dmark-android)
- [3DMark Android 应用版本说明](https://support.benchmarks.ul.com/support/solutions/articles/44002142020-3dmark-android-application-release-notes)
- [3DMark Wild Life 概览](https://support.benchmarks.ul.com/support/solutions/articles/44002135593)
- [3DMark Wild Life 系统要求](https://support.benchmarks.ul.com/support/solutions/articles/44002135597-3dmark-wild-life-system-requirements)
- [3DMark Steel Nomad Light 系统要求](https://support.benchmarks.ul.com/support/solutions/articles/44002528073-steel-nomad-light-requirements)
- [3DMark Solar Bay 系统要求](https://support.benchmarks.ul.com/support/solutions/articles/44002466574-3dmark-solar-bay-system-requirements)
- [3DMark Stress Test 结果定义](https://support.benchmarks.ul.com/support/solutions/articles/44002134931-stress-test-result-screen)
- [PCMark for Android](https://benchmarks.ul.com/pcmark-android)
- [PCMark Android 应用版本说明](https://support.benchmarks.ul.com/support/solutions/articles/44002199189-pcmark-for-android-application-release-notes)
- [Speedometer 3.1](https://www.browserbench.org/Speedometer3.1/)
- [Speedometer 3.1 方法说明](https://www.browserbench.org/Speedometer3.1/about.html)
- [Speedometer 3.1 测试说明](https://www.browserbench.org/Speedometer3.1/instructions.html)
- [安兔兔 V11 公测说明](https://www.antutu.com/doc/135125.htm)
- [安兔兔官方下载](https://antutu.com/download.htm)
- [Qualcomm 2012 Vellamo 资料](https://www.qualcomm.com/news/onq/2012/09/vellamo-mobile-benchmark-suite)
- [Android Performance Class](https://developer.android.com/topic/performance/performance-class)
- [Android `PowerManager` Thermal API](https://developer.android.com/reference/android/os/PowerManager#getCurrentThermalStatus())
- [AOSP `Build.VERSION.MEDIA_PERFORMANCE_CLASS`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/Build.java)
- [AOSP `ThermalManagerService`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/power/thermal/ThermalManagerService.java)
- [Linux thermal sysfs（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/driver-api/thermal/sysfs-api.rst)
- [AndroBench 论文 DOI](https://doi.org/10.1007/978-3-642-27552-4_89)
- [CPDT 固定源码](https://github.com/maxim-saplin/CrossPlatformDiskTest/tree/a507cda4f487afc9334e0f02673af34a366961d9)
- [Android SQLite 性能指南](https://developer.android.com/topic/performance/sqlite-performance-best-practices)
- [Linux F2FS 文档（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/f2fs.rst)

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
