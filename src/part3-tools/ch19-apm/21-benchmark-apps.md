---
title: "Benchmark 应用（Geekbench、安兔兔、3DMark、PCMark、Vellamo）"
chapter: "19"
section: "19.21"
status: draft
drafted_date: "2026-04-24"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-24"
last_verified_against: "Geekbench and 3DMark official docs / benchmark vendor public materials"
confidence: medium
tags: [apm]
related_chapters: ["19.0"]
sources:
  - type: official
    path: "https://www.geekbench.com/"
  - type: official
    path: "https://benchmarks.ul.com/3dmark-android"
pipeline_stage: drafted
---

# Benchmark 应用（Geekbench、安兔兔、3DMark、PCMark、Vellamo）

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

## Geekbench：CPU 和 Compute

Geekbench 6 官方说明它覆盖 CPU 单核、多核，以及 GPU Compute，使用真实任务和数据集建模，支持 Android、iOS、macOS、Windows、Linux。

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

PCMark 更偏日常任务和续航类负载，适合看设备在较真实工作流下的持续表现。它对普通 App 的机型分层有一定参考，但仍然不能替代 App 自己的启动、滚动和网络指标。

Vellamo 曾经常用于浏览器和 Web 性能测试，但已经偏历史工具。除非维护旧报告或老机型数据，不建议作为现代 Android 性能主参考。

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
| 存储随机 I/O | AndroBench | 启动小文件、SQLite、缓存 |
| 内存容量 | 设备信息 / 线上采集 | OOM、后台恢复、缓存策略 |
| 热稳定性 | 3DMark stress / PerfDog 长测 | 长时间游戏、视频、直播 |

线上 APM 再按这些层级聚合。比如启动慢集中在低单核 + 低随机读设备，优化方向和集中在高端机完全不同。

## Geekbench 分数的工程解释

Geekbench 单核分数对 Android App 很有参考价值，因为主线程仍然是大量体验问题的瓶颈。单核弱的设备上，这些成本会被放大：

- XML inflate / Compose layout。
- JSON / protobuf 解析。
- 首页数据合并。
- RecyclerView bind。
- 加密、压缩、图片预处理中的同步部分。

多核分数更适合看后台并发能力。但多核强不代表 App 快，如果主线程串行工作太多，仍然会慢。

## 3DMark 分数的工程解释

3DMark 对图形场景更有用。它可以帮助判断：

- 设备 GPU 档位。
- Vulkan / OpenGL ES 路径表现。
- 长时间负载后是否热降频。
- 同一设备系统更新后图形表现是否变化。

对于普通信息流 App，3DMark 分数只是一项设备能力背景。对于游戏、相机、视频编辑、AR、地图、特效页面，它的参考价值更高。

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
