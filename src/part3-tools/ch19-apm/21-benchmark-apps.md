---


title: Benchmark 应用（Geekbench 6、安兔兔、3DMark、PCMark、Speedometer）
chapter: '19'
section: '19.21'
status: finalized
drafted_date: '2026-04-24'
drafted_by: codex
applicable_versions: Geekbench 6：官方当前要求 Android 10+ / 4 GB RAM；Vellamo：历史工具，仅用于旧报告；其他 Benchmark
  按工具版本逐项核验
last_verified: '2026-06-07'
last_verified_against: Geekbench 6 download page / Benchmark Internals, Android Performance
  Class docs, 3DMark / PCMark / Speedometer / AnTuTu official materials
confidence: medium
tags:
- apm
- benchmark
- geekbench
- 3dmark
- device-tiering
- antutu
- pcmark
related_chapters:
- '19.0'
sources:
- type: official
  path: https://www.geekbench.com/
- type: official
  path: https://www.geekbench.com/download/
- type: official
  path: https://www.geekbench.com/doc/geekbench6-benchmark-internals.pdf
- type: official
  path: https://benchmarks.ul.com/3dmark-android
- type: official
  path: https://benchmarks.ul.com/pcmark-android
- type: official
  path: https://browserbench.org/announcements/speedometer3/
- type: official
  path: https://www.antutu.com/en/doc/129591.htm
pipeline_stage: ready-to-publish
task6_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: 2026-06-07
last_task6_audit: '2026-05-21'
task6_result: pass-light-edit
task9_state: 'reviewed'
task2b_state: 'fixed'
task9_result: 'auto-fixed'
task9_reviewed_date: '2026-05-13'
task9_reviewed_by: 'openclaw-task9'
last_task9_at: '2026-06-07T10:20:00+08:00'
task2b_result: fixed
last_task2b_at: '2026-04-25T02:49:32+08:00'
repaired_date: '2026-04-25'
repaired_by: openclaw-task2b
last_task9_review_log: 'logs/deep-review/2026-06-07-10-audit.md'
auto_promoted: true
task9_review_notes: '2026-06-07 idle audit: auto-fixed Geekbench 6 Android requirement drift（官方当前要求 Android 10+ / 4 GB RAM），回到 Task6 复审。'
last_task9_audit: '2026-06-07'
last_task9_autofix_at: '2026-06-07'
last_deepseek_polish_at: 2026-05-25
deepseek_polish_state: done
last_task6_at: 2026-06-07T13:06:00+08:00
---


# Benchmark 应用（Geekbench 6、安兔兔、3DMark、PCMark、Speedometer）

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 说明 Geekbench、安兔兔、3DMark、PCMark、Vellamo 测的是设备能力或综合体验基线，不直接代表某个 App 的性能。
- 🔹 [工具分工] 按 CPU、GPU、Compute、存储、网页、办公负载、综合分拆各工具关注点和适用场景。
- 🔹 [Geekbench] 解释 single-core、multi-core、Compute 分数对启动、JSON、图片处理、加密、ML 推理的工程含义。
- 🔹 [3DMark] 解释图形压力、frame stability、thermal throttling、stress test 对游戏和高负载 UI 的参考价值。
- 🔹 [安兔兔 / PCMark / Vellamo] 写综合分、办公负载、历史网页测试工具的使用边界和过期风险。
- 🔹 [测试规范] 规定设备状态、系统版本、温度、电量、刷新率、性能模式、后台进程、重复次数、取值方式。
- 🔹 [机型分层] 设计线上机型分层方法，把 benchmark 分数与 SoC、RAM、存储、系统版本和线上指标关联。
- 🔹 [分数解释] 说明单项分数比综合分更有用，不能用总分直接解释启动慢或卡顿。
- 🔹 [线上连接] 说明如何把 Benchmark 结果用于低端机分组、灰度策略、性能预算和告警阈值。
- 🔹 [历史工具] 对停止维护或口径变化的工具写处理方式：保留历史基线、停止新增、替换指标。

### 扩展（可选深入）

- 🔸 增加机型分层表，包含入门、中端、高端、旗舰四档和建议性能预算。
- 🔸 补一个 Geekbench 分数与线上启动 P95 的关联示例。
- 🔸 对 Geekbench、3DMark、PCMark 官方资料和 Vellamo 历史状态做核对。
- 🔸 增加测试报告模板，记录分数、温度、轮次、版本和备注。
- 🔸 补充“综合分误导”的案例，说明为什么要看单项分。

### 流水线加工要求

- Benchmark 应用章节必须反复区分设备基线和 App 实测数据。
- 所有分数解释都要绑定具体工程场景。
- 历史工具不得写成当前推荐工具，必须说明状态。

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## Benchmark 应用测的是设备能力

Geekbench、安兔兔、3DMark、PCMark、Vellamo 这类应用主要用于测设备或系统的综合能力。它们和 App 线上 APM 的方向相反：APM 看真实用户里的应用体验，Benchmark 看标准负载下设备表现。

Benchmark 结果可以帮助做机型分层、竞品对比、性能模式验证和硬件回归，但不能直接推出“我们的 App 一定流畅”。

## 各工具关注点不同

| 工具 | 主要方向 | 适合回答的问题 |
|---|---|---|
| Geekbench | CPU 单核、多核、GPU Compute | SoC CPU / Compute 能力怎样，跨平台大致排位如何 |
| 安兔兔 | CPU、GPU、内存、UX 综合分 | 设备综合跑分和大众认知里的性能层级 |
| 3DMark | GPU、游戏图形、压力测试 | 图形性能、热稳定性、Vulkan / OpenGL ES 表现 |
| PCMark | 日常工作负载、续航等 | 生产力场景和持续负载下的设备表现 |
| Vellamo | 浏览器、Web、多核、单核等旧式测试 | 老设备或历史数据对比 |

这些工具的分数不能混用。Geekbench 单核高，不代表 3D 游戏帧率好；3DMark 稳定，不代表 App 冷启动快；安兔兔综合分高，也不能证明磁盘随机写入或 SQLite 事务一定快。

## 适用版本要按工具拆开

不能用一个统一的 Android 版本范围概括所有 Benchmark 工具。工具版本、上架状态和测试口径要分开记录：

| 工具 | 当前定位 | Android 版本边界 | 处理方式 |
|---|---|---|---|
| Geekbench 6 | CPU / Compute 主流基线 | 官方下载页和 Benchmark Internals 当前都写 Android 10+；下载页同时写 4 GB RAM。 | Android 10+ 设备可按同一 Geekbench 6 口径比较；如需覆盖更早设备，保留 Geekbench 5 或旧包历史基线，并单独标注工具版本。 |
| 3DMark / PCMark | 图形、压力、工作负载与续航基线 | 按测试包版本和设备支持列表核验。 | 记录工具版本、测试项目和系统版本，避免跨大版本直接比较。 |
| 安兔兔 | 综合分和大众设备档位参考 | 分数口径随应用大版本变化。 | 用于沟通设备档位，不用于工程归因。 |
| Vellamo | 历史网页 / 设备测试工具 | 已属于历史工具。 | 只用于旧报告复盘；新机型分层改用 Geekbench、3DMark、PCMark、Speedometer 等当前工具。 |

## Geekbench：CPU 和 Compute

下文默认指 Geekbench 6。Geekbench 6 官方说明它覆盖 CPU 单核、多核，以及 GPU Compute，使用真实任务和数据集建模，支持 Android、iOS、macOS、Windows、Linux。

在 Android 性能分析里，Geekbench 更适合做机型分层：

- 单核分数影响主线程 Java/Kotlin 执行能力。
- 多核分数影响并行任务、编译、图片处理、后台计算。
- Compute 分数可以参考 GPU 计算类负载，但不等同于游戏渲染帧率。

使用时不要只看总分。对 App 体验更有用的是把机型按 CPU 单核、内存、存储和 GPU 分层，再看线上性能指标是否集中在低档设备。

## 3DMark：图形和热稳定性

3DMark Android 官方页面强调 GPU 和 CPU 图形相关 benchmark，也支持与大量 Android / iOS 设备比较。它对游戏、图形重的 App、相机预览、视频特效和 AR 场景更有参考意义。

3DMark 的压力测试比单次跑分更有用。很多设备前几轮分数不错，温度上来后降频明显。对游戏和重图形应用，稳定性曲线往往比最高分更能说明问题。

## 安兔兔、PCMark、Vellamo 的使用边界

安兔兔综合分适合快速判断设备档位，但它的 UX、内存、GPU 权重和测试版本会变化，不适合拿不同大版本分数做严肃纵向对比。

PCMark 更偏日常任务和续航类负载，适合看设备在较真实工作流下的持续表现。PCMark Storage 2.0 和 CPDT 更适合当前 Android 存储基线；测试时要区分缓存路径和物理介质，能关闭缓存或记录首轮 / 稳定轮结果时要写进报告。AndroBench 只保留历史对比，不再作为现代默认入口。

Vellamo 曾经常用于浏览器和 Web 性能测试，但已经偏历史工具。除非维护旧报告或老机型数据，不建议作为现代 Android 性能主参考。现代 Web / WebView 基线优先看 Speedometer 3.0；需要 JavaScript 引擎压力时可补 JetStream 2，二者仍不能替代 App 内 WebView trace。

## 测试规范

跑 Benchmark 前要固定条件：

- 电量、充电状态、性能模式。
- 环境温度和设备散热。
- 后台进程和系统更新状态。
- 同一工具版本、同一测试项目。
- 连续多轮，记录均值和波动。

Benchmark 分数最适合做“设备能力分层”。把它和线上 APM 连起来时，应当这样用：先按设备能力分层，再看同一版本在不同层级上的启动、慢帧、ANR、OOM 差异。不要用跑分替代用户体验指标。

## 机型分层方法

把 Benchmark 用到 App 性能治理里，最有价值的是机型分层。可以建立这样的设备能力表：

| 维度 | 数据来源 | 分层用途 |
|---|---|---|
| CPU 单核 | Geekbench | 主线程、启动、JSON、布局计算 |
| CPU 多核 | Geekbench | 后台并发、图片处理、解压 |
| GPU | 3DMark | 游戏、动画、视频特效、地图 |
| 存储随机 I/O | CPDT / PCMark Storage 2.0；AndroBench 仅保留历史对比 | 启动小文件、SQLite、缓存 |
| 内存容量 | 设备信息 / 线上采集 | OOM、后台恢复、缓存策略 |
| 热稳定性 | 3DMark stress / PerfDog 长测 | 长时间游戏、视频、直播 |

Android Performance Class（Media Performance Class）适合作为设备分层的第一层粗筛。Android 12+ 设备可通过 `Build.VERSION.MEDIA_PERFORMANCE_CLASS` 暴露等级；Jetpack Core Performance 的 `DevicePerformance.mediaPerformanceClass` 可以提供兼容查询。它给出的是系统声明的媒体能力下限，覆盖内存、I/O、编解码、相机等维度。Benchmark 分数再用于补充更细的 CPU、GPU、存储和热稳定性差异。

| 信号 | 用法 | 边界 |
|---|---|---|
| Performance Class | 作为服务端设备字典的官方能力标签，例如 PC12、PC13、PC14、PC15。 | 它偏媒体能力，不等同于某个 App 的启动或滚动表现。 |
| Geekbench / 3DMark / CPDT | 补充 CPU、GPU、存储和热稳定性分档。 | 工具版本、测试项目、温度和缓存策略要记录清楚。 |
| 线上 APM 指标 | 验证分档是否真的对应启动慢、慢帧、OOM 或 ANR。 | 不能用跑分替代真实用户指标。 |

线上 APM 再按这些层级聚合。比如启动慢集中在低单核 + 低随机读设备，优化方向和集中在高端机完全不同。

## Geekbench 分数的工程解释

Geekbench 单核分数对 Android App 很有参考价值，因为主线程仍然是大量体验问题的瓶颈。单核弱的设备上，这些成本会被放大：

- XML inflate / Compose layout。
- JSON / protobuf 解析。
- 首页数据合并。
- RecyclerView bind。
- 加密、压缩、图片预处理中的同步部分。

多核分数更适合看后台并发能力。Geekbench 6 多核采用 shared-task 模型，多线程协作完成同一组任务，比 Geekbench 5 的 separate-task 模型更强调线程协作和核心间调度成本。多核强不代表 App 快，如果主线程串行工作太多，仍然会慢。

## 3DMark 分数的工程解释

3DMark 对图形场景更有用。它可以帮助判断：

- 设备 GPU 档位。
- Vulkan / OpenGL ES 路径表现。
- 长时间负载后是否热降频。
- 同一设备系统更新后图形表现是否变化。

对于普通信息流 App，3DMark 分数只是一项设备能力背景。对于游戏、相机、视频编辑、AR、地图、特效页面，它的参考价值更高。Android 12+ 且支持 Vulkan ray query 的设备，可以补 Solar Bay 看移动端光追压力；现代旗舰机型还可以补 Steel Nomad Light，看比 Wild Life 更重的非光追图形负载。

## 综合分的陷阱

安兔兔这类综合分适合产品和测试快速沟通设备档位，但不适合做工程归因。综合分把 CPU、GPU、内存、UX 等合成一个数，合成权重会随版本变化。

工程上更应该拆开看：

- CPU 弱导致主线程慢。
- 存储弱导致启动和数据库慢。
- GPU 弱导致动画和渲染慢。
- 内存小导致 OOM 和后台恢复慢。
- 热稳定性差导致长时间使用后退化。

只用综合分做分层，会把这些完全不同的问题混在一起。

## Benchmark 与线上数据的连接

建议在设备字典里维护 benchmark-derived capability，而不是在每次线上事件里上传跑分。线上事件只带机型、SoC、内存、系统版本，由服务端 join 到能力表。

```text
event: jank_frame_batch
device_model: Pixel 8
soc: Tensor G3
ram_gb: 8

server join:
cpu_single_bucket: high
gpu_bucket: high
storage_random_bucket: medium
thermal_bucket: medium
```

这样既减少上报字段，也能统一更新设备分层策略。

## 历史工具的处理

Vellamo 这类工具如果已经停更或偏历史，只适合用于旧报告对比。新书稿不要把它和 Geekbench 6、3DMark 现代测试放在同等位置。读者需要知道：历史跑分能帮助理解老设备，但不能作为现代 Android 17 设备的主要判断依据。
