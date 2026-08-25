---
title: 用户设置对能耗的影响：亮度、刷新率与深色模式
chapter: '11.5'
section: '11.5'
status: finalized
applicable_versions: Android 11 (API 30) - Android 17 (API 37)
last_verified: '2026-07-31'
last_verified_against: AOSP android-17.0.0_r1；Android 17 / API 37 SDK；arXiv 2604.25587v1；Android 官方显示与功耗文档 2026-07
confidence: high
sources:
- type: paper
  path: https://arxiv.org/abs/2604.25587
- type: source
  path: https://github.com/wellington-oj/user_energy
- type: official
  path: https://source.android.com/docs/core/power/values
- type: official
  path: https://source.android.com/docs/core/graphics/arr
- type: official
  path: https://source.android.com/docs/core/graphics/multiple-refresh-rate
- type: official
  path: https://developer.android.com/media/optimize/performance/frame-rate
- type: official
  path: https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate
- type: official
  path: https://developer.android.com/develop/ui/views/theming/darktheme
- type: official
  path: https://developer.android.com/topic/performance/power/setup-battery-historian
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/stats/ScreenPowerStatsCollector.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/stats/processor/ScreenPowerStatsProcessor.java
- type: aosp
  path: frameworks/base/core/java/com/android/internal/os/PowerProfile.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/display/mode/DisplayModeDirector.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/display/BrightnessMappingStrategy.java
- type: aosp
  path: frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp
- type: local
  path: intake/daily-info/2026-05-22.md
tags:
- power
- battery
- display
- refresh-rate
- dark-mode
- empirical-study
related_chapters:
- '2.2'
- '5.2'
- '11.1'
- '11.2'
- '15.5'
- '25.1'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---

# 用户设置对能耗的影响：亮度、刷新率与深色模式

“亮度 50%、高刷开启、深色模式开启”不是测试报告里的装饰信息。它们会改变面板发光、显示时序、应用渲染、视频管线和系统调度。若两轮实验的设置不同，所得差值很可能混入了显示侧变化。

平台锚点为 Android 17 / API 37 和 AOSP `android-17.0.0_r1`，同时复核论文《An Empirical Analysis of Mobile Energy Consumption Across User Configurations》。论文中的百分比只描述一台 Samsung Galaxy S23 Ultra 上的自动化短场景，不能当作其他设备的预期收益。

## 11.5.1 先确认能耗数字来自哪里

“屏幕耗电”可能来自四种口径，几种数字不能直接互换：

| 证据 | 表达的含义 | 适合回答的问题 | 主要边界 |
|---|---|---|---|
| 外接电源分析仪 | 设备输入侧的电压、电流与能量 | 整机在两个配置下相差多少 | 需要稳定供电、采样与电池旁路方案 |
| 设备 power rail（电源轨）/ ODPM（设备端功耗测量） | SoC（片上系统）或设备定义 rail 的能量 | 哪条硬件供电链路发生变化 | rail 名称、覆盖范围和开放程度由设备决定 |
| 燃料计 / 电池电量变化 | 一段时间内的电池侧变化 | 长场景的整机续航趋势 | 短窗口易受计数精度、温度和电池状态影响 |
| BatteryStats / power profile（功耗估算参数） | 组件活动和 UID（应用用户标识）的测量或估算归因 | 谁在何时使用了哪些组件 | 归因口径不等于外接仪器的整机能量 |

### Android 17 的显示归因有测量与模型两条路径

旧资料常把 BatteryStats 描述成“状态时长乘 power profile”。这个描述已经不完整。Android 17 的 `ScreenPowerStatsCollector` 会收集：

- `DISPLAY` energy consumer（显示能量计量组件）提供的 consumed energy（已消耗能量）；
- 各显示的 screen-on、doze（低功耗显示）与亮度档位时长；
- UID 的 top activity（最前台 Activity）时长。

`ScreenPowerStatsProcessor` 在设备提供显示 energy consumer 时，把硬件报告的微库仑换算成 mAh（毫安时）；没有这类数据时，才使用 `PowerProfile` 的显示参数估算。现代参数按显示设备区分，包括 `ambient.on.display`、`screen.on.display` 和 `screen.full.display`。旧的 `screen.on`、`screen.full` 常量只保留兼容含义。

UID 归因也要单独理解。处理器会依据 top activity 时长分配一部分显示成本。这能支持系统级归因，却不能证明某个 View、某帧 GPU 工作或某个颜色像素消耗了对应能量。文章或评审报告若要证明产品设置带来的整机收益，仍应使用设备 rail、长时间燃料计测试或外接仪器补证。

## 11.3.2 如何阅读 2026 年单机实验

论文与公开复现仓库给出了较完整的实验信息：

- 设备为一台 Galaxy S23 Ultra，Snapdragon 8 Gen 2、5000 mAh 电池、Dynamic AMOLED、最高 120 Hz；
- 场景覆盖 WhatsApp、Instagram、TikTok、YouTube 和手电筒；
- 879 组唯一配置，每组执行 15 次；
- 初始记录 13,184 条，移除 536 条异常值后保留 12,649 条；
- 主要场景持续 15 或 30 秒，手电筒另含 60 秒条件；
- 通过 `dumpsys batterystats` 获取 mAh，再按采样电压换算为焦耳；
- 使用 Mann-Whitney U（两组独立样本的非参数检验），以 `p < 0.05` 判定统计显著差异。

这项工作适合用来建立实验变量表，也能说明同一设备、同一脚本下的变化方向。它没有提供跨面板、跨 SoC、跨 OEM（设备厂商）或长时间稳态结论。软件归因、短采样窗口和单机设计会限制外推范围。

后文引用其数字时，都应读作“该设备、该脚本、该窗口的观察”。产品文案、系统默认值和 KPI（关键绩效指标）不能直接套用这些百分比。

## 11.5.3 亮度：滑块位置、面板亮度与显示功耗

论文中，亮度是影响范围较大且方向稳定的变量：

| 比较 | 论文观察 | 使用边界 |
|---|---:|---|
| 0% → 100%，全部场景汇总 | +86.5% | 单台 S23 Ultra、短场景、BatteryStats 口径 |
| 0% → 100%，Instagram | +96.8% | 受该次内容与交互脚本影响 |
| 0% → 100%，WhatsApp | +210.2% | 基线较低，百分比会被放大 |
| 0% → 50%，全部场景汇总 | +46.0% | 不能推导 50% 对应某个固定 nit（尼特，亮度单位）值 |

### “50% 亮度”不是跨设备物理量

Android 的应用层亮度通常使用归一化范围，系统再通过设备配置与映射策略换算为面板可执行亮度。`BrightnessMappingStrategy` 可以使用亮度—nit 曲线、环境照度曲线和校准数据。滑块 50% 在两台设备上可能对应不同 nit 值，也可能经过不同的非线性映射。

因此，跨设备实验应同时记录：

- 设置滑块值或 Window brightness；
- 是否开启自动亮度；
- 环境照度；
- 若设备可读，记录目标与当前 nit；
- HBM（High Brightness Mode，高亮模式）、HDR（高动态范围）、相机或阳光可读模式是否触发；
- 面板类型与显示模式。

### 面板类型改变内容与亮度的关系

LCD（液晶显示器）的背光通常是显示功耗的重要来源，页面颜色对背光本身的影响有限。OLED / AMOLED（有机发光二极管）面板的像素自发光，像素亮度、颜色、发光面积和面板实现都会改变成本。相同滑块值下，白底网页、低平均画面亮度的视频和大面积黑色界面可能有不同功耗。

亮度还会影响热状态。户外高亮或 HDR 峰值亮度可能抬高面板与整机温度，继而触发显示、CPU 或 GPU 的 thermal throttling（过热降频）。短测若刚好跨过热阈值，帧率变化与显示功耗变化会混在一起。

### 固定亮度与自动亮度用于不同问题

- 固定亮度适合回归测试，用来减少环境光带来的变化；
- 自动亮度适合用户场景复测，用来检查策略在环境变化下的表现；
- 户外高亮、HDR 与相机预览应单独建组，避免与普通室内结果合并。

固定档位时还要关闭会自动改变亮度的测试外变量，等待亮度稳定后再开始采样。报告只写“亮度 50%”不够；至少要补充自动亮度状态、环境与设备。

## 11.5.4 刷新率：四个频率不能混为一个数字

显示链路里至少有四个相关频率：

1. 应用产生新 buffer（图形缓冲区）的速率；
2. Choreographer / VSync（垂直同步信号）驱动 UI 的节奏；
3. SurfaceFlinger（系统显示合成服务）合成与提交的节奏；
4. 面板执行的物理刷新率。

应用以 30 fps（每秒帧数）解码视频，不代表面板工作在 30 Hz（每秒刷新次数）。面板可能运行 60 Hz、90 Hz 或 120 Hz，并通过重复帧显示 30 fps 内容。支持 Android Adaptive Refresh Rate（自适应刷新率，ARR）的设备还可能保持某个面板模式，在该模式内改变 VSync 节奏。实验报告要分别写“请求值”和“观察值”。

60 Hz 的单帧预算约为 16.67 ms，120 Hz 约为 8.33 ms。这说明高刷新 UI 给主线程、RenderThread（渲染线程）和 GPU 留出的单帧时间更短。它不表示每次升到 120 Hz 都会让应用计算量翻倍；静态内容、复用 buffer、硬件能力和系统 vote（投票请求）都会改变结果。

### 论文中的刷新率数字

| 比较 | 论文观察 | 解释范围 |
|---|---:|---|
| 30 Hz → 120 Hz，全部场景汇总 | +10.8% | 单台设备的设置扫描 |
| 30 Hz → 60 Hz，Instagram | +9.1% | 受滚动与内容脚本影响 |
| YouTube 的最高差值 | +16.3% | 不能推导所有视频场景的固定成本 |
| WhatsApp | 未发现显著差异 | 只说明该脚本没有检出差异 |

这些数字不支持“60 Hz 是所有设备的最佳能效点”这类结论。应用应表达内容帧率偏好，系统应结合用户选择、其他可见 Layer（图层）、热状态、省电策略与设备能力决策。

## 11.5.5 Android 17 如何决定刷新率

Android 17 的 `DisplayModeDirector` 汇集多个 vote，并生成显示模式与刷新率范围。输入来源包括：

- 用户的默认、最低和峰值刷新率设置；
- 应用对 mode（显示模式）或 frame rate（帧率）的请求；
- 可见 Surface / View 的内容帧率；
- 屏幕亮度区间与环境光策略；
- High Brightness Mode（高亮模式）；
- 省电模式；
- thermal（热状态）限制；
- OEM 配置与设备支持的显示模式。

SurfaceFlinger 的 `RefreshRateSelector` 再结合 Layer 需求、可选模式与策略选择候选刷新率。应用 API 表达的是提示或兼容性要求，并不独占面板刷新率的控制权。

### `Surface.setFrameRate()` 的边界

`Surface.setFrameRate()` 从 Android 11 / API 30 提供。视频、自绘 Surface 和游戏可以上报内容帧率，系统会评估是否切换显示模式或采用可兼容的倍频，例如 24 fps 内容可能配合 120 Hz。其他 Surface、用户设置、省电模式或设备限制都可能让请求无法满足。

可见但暂停更新的 Surface 应按 API 约定清除不再需要的 frame-rate vote（帧率投票），避免旧请求继续影响选择。业务代码也不能根据 API 调用成功就判定面板已经切换；要用系统状态和 trace（性能跟踪）观察生效结果。

### View 与 ARR

Android 15 / API 35 增加 `View.setRequestedFrameRate()`，普通 View 层级可以提供帧率类别或数值提示。官方 ARR 文档把 Android 15 作为平台引入点，但设备支持还依赖显示硬件、Composer HAL（显示合成硬件抽象层）接口和 OEM 配置。应用侧文档将 Android 15 QPR1（季度平台更新 1）及后续版本列为相关支持范围。

Android 16 / API 36 增加 `Display.hasArrSupport()`。在 Android 17 / API 37 上，应用仍应先检查设备能力，再讨论 ARR 行为。系统版本达到 Android 17 也不能推出设备一定支持 ARR。

### 常见场景的策略

| 场景 | 合理的应用表达 | 观察重点 |
|---|---|---|
| 静态阅读、聊天停留 | 让系统降低更新频率，避免无意义 invalidation（界面重绘请求） | 应用帧产出、VSync、面板观察值 |
| 列表滑动 | 交互期间请求合适帧率，停止后及时撤销 | 掉帧、触摸阶段、静止后的降频延迟 |
| 短视频流 | 视频内容帧率与滚动交互分别处理 | 视频 Layer、UI Layer、模式切换 |
| 长视频 | 用 Surface API 报告源内容帧率 | 24/30/60 fps 的倍频、切换黑屏或卡顿 |
| 游戏 | 结合帧率、热预算和用户画质选择 | sustained fps（可持续帧率）、GPU、温度、功率 |

省电模式常会收窄允许的刷新率范围，但“固定限制到 60 Hz”不应写成所有 Android 设备的 SDK 合同。限制值与行为可受平台版本、OEM 策略和设备配置影响。

## 11.5.6 深色模式：屏幕技术与内容共同决定收益

Android 官方文档把暗色主题的收益放在屏幕技术条件下描述，同时强调低光环境与无障碍价值。功耗分析时应分开看 UI 背景、媒体内容、面板类型和用户亮度。

论文在同一台 AMOLED 设备上得到以下结果：

| 场景 | 深色主题相对浅色主题 | 边界 |
|---|---:|---|
| Instagram | -2.4% | 只覆盖该次内容与短脚本 |
| WhatsApp | -3.8% | 文本页面占比与配色会影响结果 |
| 全部场景汇总 | -1.4% | 不能推广为 AMOLED 的固定收益 |

收益偏小不表示深色主题没有价值。该实验的内容、亮度和时长限制了结果。对 OLED / AMOLED，大面积低亮度像素通常有利；图片、视频、地图与相机预览中的媒体像素，不会因应用的背景、导航栏等界面元素变暗而同步变化。对 LCD，背光仍持续工作，页面配色通常难以形成同等级别的面板收益。

还要防止亮度补偿混入结果。用户若在深色界面上提高亮度，新增的亮度成本可能抵消像素颜色带来的收益。测试时固定滑块有利于比较主题本身，用户研究则应保留用户自主调整后的亮度，两组问题不能合并解释。

产品文案宜写成“在部分 OLED 设备和深色内容页面上可能降低显示功耗”，并把视觉舒适、低光使用和系统一致性作为独立收益。不要承诺所有设备显著省电。

## 11.5.7 省电模式不是一个固定参数包

论文在该设备上观察到省电模式使汇总能耗下降 9.1%，YouTube 下降 14%，TikTok 下降 7.3%，WhatsApp 场景没有表现出相同方向。这仍是设备实现与脚本共同产生的结果。

Android 为应用提供 `PowerManager.isPowerSaveMode()` 等状态接口，系统与 OEM 可以据此限制后台执行、位置、网络、动画、刷新率或处理器策略。具体 CPU 上限、刷新率上限与后台规则不属于统一的应用层保证。

测试报告应记录省电模式是否开启，还要记录它带来的可观察变化：

- 当前刷新率范围是否收窄；
- 后台任务是否推迟；
- 网络请求是否改变；
- 动画或触觉反馈是否调整；
- CPU/GPU 频率、thermal severity（热状态等级）和业务耗时是否变化。

直接读取或写入 `Settings.Global.LOW_POWER_MODE` 不适合作为普通应用的控制方案。测试自动化也应优先使用公开 shell / dumpsys 能力，并在报告中记录设备与权限环境。

## 11.5.8 视频分辨率、消息长度与网络状态

这些变量表面上属于用户设置，测到的能量却往往覆盖整段业务动作。

### 视频分辨率

论文中，YouTube 最高测试分辨率对应的能耗增幅为 5.5%，720p 与 1440p 没有检出统计显著差异。这不能用于证明分辨率“对功耗没有影响”。短窗口内可能同时存在：

- 网络下载与缓存；
- 编解码器固定成本和硬件解码效率；
- Surface 合成与缩放；
- 面板亮度与视频平均画面亮度；
- 播放控件、广告和脚本动作。

弱网、高码率、软件解码、录屏或热限制场景可能得到不同结果。视频测试应至少记录 codec（编解码器）、码率、分辨率、帧率、HDR、缓存状态、网络类型和播放时长。

### 消息长度

论文的 WhatsApp 脚本中，消息从 100 字符增至 200 字符后，总能耗增加 115.6%。这个百分比描述的是整次脚本，不是单字符能量。输入法处理、文本布局、网络传输、加密、回执和发送后的 UI 更新都可能参与。

复现实验应分别记录输入时长、按键或注入方式、布局次数、上下行字节、CPU 时间和后台任务。若动作持续时间也随字符数增加，报告还要区分“单位时间功率”与“完成一次任务的总能量”。

### 网络状态

论文的飞行模式对比没有检出显著差异，只能说明其脚本和缓存条件下没有形成可检测结果。线上弱网、蜂窝寻网、重传、DNS/TLS 重试，以及请求结束后基带仍保持活跃的 radio tail（基带尾时长），都可能改变结论。

网络实验应记录 Wi-Fi / 蜂窝制式、信号强度、传输字节、缓存、请求重试与服务器响应。飞行模式会同时改变多项能力，不适合作为精确模拟弱网的单一开关。

## 11.5.9 测试设计：记录请求值与生效值

一份可复现的用户设置功耗实验至少包含下面这些条件：

| 变量 | 请求或配置值 | 生效值与证据 | 常见混淆 |
|---|---|---|---|
| 亮度 | 滑块、Window brightness（窗口亮度）、自动亮度 | 当前亮度、nit、HBM/HDR 状态 | 同一百分比跨设备比较 |
| 刷新率 | 用户 min/peak（最低/峰值）、应用 frame-rate vote | VSync 间隔、显示模式、面板观察值 | 把请求 120 Hz 写成持续 120 Hz |
| 主题 | 系统与应用主题 | 页面颜色、媒体内容、用户补偿亮度 | 把 OLED 结论用于 LCD |
| 省电模式 | 开关状态 | 刷新率、任务、网络、频率变化 | 把 OEM 行为当成 Android 合同 |
| 网络 | Wi-Fi / 蜂窝 / 弱网配置 | 信号、吞吐、重试、缓存 | 用飞行模式代表所有网络问题 |
| 热状态 | 起始温度、环境温度 | thermal severity、频率、峰值温度 | 冷机组与温度稳定组直接比较 |
| 电池与供电 | 初始电量、USB、充电状态 | fuel gauge（电量计）、rail 或仪器记录 | 充电策略改变调度和统计 |
| 业务 | App 版本、账号、内容、动作 | 成功率、时长、帧数、字节 | 两组脚本没有完成相同任务 |

### 分三层安排实验

1. **固定基线**：固定设备、亮度、刷新率范围、主题、网络、内容、温度区间和采样窗口。
2. **单变量扫描**：每次改变一项设置，并验证其他生效值未随之变化。
3. **用户场景复测**：恢复自动亮度、ARR、动态内容和常用网络，检查实验方向是否仍存在。

固定基线用于比较代码版本，用户场景用于评估体验。两者应分别报告。单变量扫描也要警惕联动：开启省电模式可能同步改变刷新率、后台任务和处理器策略。

### 快速采集系统快照

下面的命令用于在每轮测试前后保存显示状态、SurfaceFlinger 状态、BatteryStats 和完整 bugreport（系统诊断包）：

```bash
adb shell dumpsys display > display.txt
adb shell dumpsys SurfaceFlinger > surfaceflinger.txt
adb shell dumpsys batterystats --charged > batterystats.txt
adb bugreport display-power.zip
```

`dumpsys display` 与 SurfaceFlinger 输出适合确认配置和当时状态，不能替代连续时间线。BatteryStats 用于系统归因，bugreport 保存诊断上下文；命令输出中的应用、账号、设备标识和网络信息应在分享前脱敏。

连续分析时，可在 Perfetto 中同时观察 FrameTimeline（帧时间线）、VSync、调度、CPU frequency/idle（频率/空闲状态）、thermal 与设备开放的 power rail。Battery Historian 适合查看较长时间线上的屏幕亮度、信号和 UID 活动。Android Studio Power Profiler（功耗分析器）或 Macrobenchmark `PowerMetric`（功耗指标）的可用数据取决于设备能力，仍需写明设备与指标来源。

### 重复、统计与失败样本

功耗数据常呈偏态分布，并有少量远高于多数样本的长尾值。报告应给出重复次数、中位数、离散程度、异常值规则与场景成功率。Mann-Whitney U 检验适合比较这类独立样本，但 `p < 0.05` 只说明当前样本存在统计证据，不代表差异一定具有产品价值。

删除异常样本必须有预先定义的规则，并保留失败原因。脚本超时、广告出现、网络失败、温度越界或业务动作未完成，应作为场景质量问题记录，不能只因数值偏大就移除。

## 11.5.10 版本边界：Android 11 到 Android 17

| 平台 | 相关变化 | 阅读方式 |
|---|---|---|
| Android 11 / API 30 | `Surface.setFrameRate()` 与多刷新率应用接入 | 应用可表达 Surface 内容帧率 |
| Android 12 / API 31 | frame-rate API 增加兼容性相关参数 | 区分无缝与可能发生模式切换的请求 |
| Android 15 / API 35 | 平台引入 ARR，增加 View 级帧率请求能力 | 支持受硬件、HAL 与 OEM 配置约束 |
| Android 16 / API 36 | `Display.hasArrSupport()` 提供能力检查 | 系统版本与设备能力分开判断 |
| Android 17 / API 37 | 源码锚点；显示策略继续汇集用户、应用、亮度、热与省电投票 | 以设备生效状态验证请求结果 |

版本表描述平台能力演进，不表示每台升级到对应版本的设备都开放相同显示模式。刷新率列表、ARR、HBM、power rail 和 consumed-energy 数据均可能存在设备差异。

## 11.5.11 产品策略：提示必须带条件

### 亮度

阅读、聊天、图文流与长视频场景可优先检查亮度。提示语应以可读性为前提，例如“环境允许时降低屏幕亮度”。应用不应覆盖用户的无障碍需求，也不应频繁修改系统亮度。

### 刷新率

视频和自绘内容应上报内容帧率，静态 UI 应停止无意义刷新。是否建议用户降低峰值刷新率，要结合设备、场景和体验数据。游戏、绘图与快速滚动页面可能从高刷获得明显体验收益。

### 深色模式

可说明部分 OLED 设备、深色页面和合适亮度下存在省电机会。不要把它写成所有设备通用的续航功能。媒体内容占主导的页面尤其要谨慎。

### 分辨率与网络

弱网、发热、流量受限或解码压力较高时，降低码率与分辨率可能同时改善稳定性和能耗。正常网络下的收益要由业务场景测量，不宜从单机论文数字推导。

### 省电模式

应用应尊重系统省电状态，减少可延迟工作，并验证关键路径是否仍可用。不要假设固定 CPU 上限或固定刷新率上限；这些属于设备策略。

## 11.5.12 评审清单

- [ ] 亮度记录包含固定/自动状态、环境和 HBM/HDR 条件
- [ ] 跨设备比较使用可解释的物理亮度信息，或明确滑块值不可比
- [ ] 刷新率同时记录用户配置、应用请求和系统生效状态
- [ ] ARR 结论包含 `Display.hasArrSupport()` 与设备支持边界
- [ ] 深色模式结论区分 OLED / LCD、页面颜色与媒体内容
- [ ] 省电模式结论没有把 OEM 参数写成平台保证
- [ ] 视频实验记录 codec、码率、帧率、HDR、缓存和网络
- [ ] 网络实验记录信号、重试、字节与 radio 状态
- [ ] BatteryStats 归因与整机测量没有混用
- [ ] 实验写明重复次数、离散程度、异常值规则和失败样本
- [ ] 论文百分比标注单机、短场景与软件归因边界

## 小结

用户设置属于功耗实验条件，也可能改变多条系统链路。亮度要从滑块值追到面板亮度与内容；刷新率要分清应用产帧、VSync、合成和面板刷新；深色模式要结合屏幕技术、页面颜色与用户亮度；省电、视频和网络设置则常带来多变量联动。

Android 17 的 BatteryStats 显示归因可能使用硬件 consumed energy，也可能回退到 `PowerProfile`，两种路径都不能代替产品场景的整机测量。可靠结论应写清设备、请求值、生效值、测量来源、业务动作和统计边界。

## 参考资料

- [An Empirical Analysis of Mobile Energy Consumption Across User Configurations](https://arxiv.org/abs/2604.25587)
- [论文复现仓库：wellington-oj/user_energy](https://github.com/wellington-oj/user_energy)
- [AOSP：Platform power management values](https://source.android.com/docs/core/power/values)
- [AOSP：Adaptive refresh rate](https://source.android.com/docs/core/graphics/arr)
- [AOSP：Multiple refresh rate](https://source.android.com/docs/core/graphics/multiple-refresh-rate)
- [Android Developers：Frame rate](https://developer.android.com/media/optimize/performance/frame-rate)
- [Android Developers：Adaptive refresh rate](https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate)
- [Android Developers：Dark theme](https://developer.android.com/develop/ui/views/theming/darktheme)
- [Android Developers：Battery Historian](https://developer.android.com/topic/performance/power/setup-battery-historian)
- AOSP `android-17.0.0_r1`：`ScreenPowerStatsCollector.java`、`ScreenPowerStatsProcessor.java`、`PowerProfile.java`
- AOSP `android-17.0.0_r1`：`DisplayModeDirector.java`、`BrightnessMappingStrategy.java`、`RefreshRateSelector.cpp`
