---
title: "第 1 章：系统架构全景"
chapter: "1.0"
section: "1.0"
status: "finalized"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-05-08"
last_verified_against: "src/SUMMARY.md, 子节 1.7/1.9/1.10/1.13/1.14/1.16/1.17 applicable_versions, AOSP android-17.0.0_r1"
confidence: medium
sources:
  - type: repo
    path: "src/SUMMARY.md"
  - type: review
    path: "logs/external-review/archive/2026-04-22-21-1.0-external-review.md"
  - type: official
    path: "https://developer.android.com/about/versions/16/release-cycle"
tags: ['architecture', 'overview', 'chapter-intro']
related_chapters: ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7", "1.8", "1.9", "1.10", "1.11", "1.12", "1.13", "1.14", "1.16"]
pipeline_stage: "ready-to-publish"
task2b_result: fixed
task2b_state: fixed
task6_state: reviewed
task9_state: "reviewed"
last_task2b_at: "2026-05-09T09:44:52"
reviewed_by: openclaw-task6
reviewed_date: "2026-05-08"
task6_result: "pass-light-edit"
task9_result: "pass-tech-review"
last_task9_at: "2026-05-14T18:30:00+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-14"
last_task9_review_log: "logs/deep-review/2026-05-14-18-deep-review.md"
---

# 第 1 章：系统架构全景

这一章解决的是一个起手问题：当我们说“Android 很复杂”时，复杂到底落在哪些边界上。

今天的 Android 复杂度，已经不只是在 App、Framework 和 Kernel 之间来回切换。Treble 把硬件接口收束到稳定 HAL；Project Mainline 又把 50+ 个系统模块拆到 APEX / APK 更新通道；到 Android 15/16，16KB Page Size、ADPF、Cloud Compilation、Parallel Module Loading 和 Generic Bootloader 继续改写启动、内存、调频和更新方式。Android 17 (API 37) 带来的变化按成熟度分几层：①已确认的平台行为包括 `ConcurrentMessageQueue` 无锁投递、`ProfilingManager` 系统触发式 trace、DeliQueue 命令调度等（见 `1.13`）；②Kernel 6.12 / OEM 可选能力包括 `sched_ext` 可编程调度（见 `5.7`、`14.10`、`16.4`）；③ART Generational CMC 的启用受 runtime flag / device_config gating 控制（见 `4.3`、`4.6`、`16.5`）；④Energy Limiter 配额制当前仍为研究线索，未在官方 behavior changes 文档中确认（见 `5.7`）。后面很多性能现象，都和这些演进直接相关。

这一章的任务，是先把全景图搭起来。读完之后，至少应该能回答四件事：

- App 进程、system_server、Native 服务和内核分别负责什么
- 一次 Binder 调用为什么会拖慢主线程、启动或系统服务
- 模块化、Mainline 和 HAL 分层怎样改变性能问题的落点
- AMS、PMS、Zygote、ART、MessageQueue、锁竞争、Audio Pipeline 应该放进哪张图里

## 本章内容

- `1.1 Android 分层架构`：先看 App、Framework、Native、HAL、Kernel 的职责边界
- `1.2 系统启动全流程`：理解从 Boot ROM 到 Zygote 的启动分段
- `1.3 进程模型与生命周期管理`：把前台、后台、缓存进程和系统调度放进同一张图
- `1.4 Binder IPC 机制与性能影响`：看跨进程通信怎样带来阻塞、复制和优先级继承
- `1.5 线程模型`：建立 Looper、MessageQueue、线程池和调度优先级的基础认知
- `1.6 Android 版本演进中的架构变化`：把 Treble、Mainline、AIDL HAL、16KB Page Size 等变化串起来
- `1.7 ART 编译管线与 dex2oat 优化`：看 JIT、AOT、Profile Guided Compilation 和云编译素材怎样影响冷启动
- `1.8 Activity Manager Service`：理解进程管理、组件调度和前后台切换的系统入口
- `1.9 Package Manager Service`：看安装、扫描、归档和编译产物管理怎样影响安装与首启
- `1.10 ContentProvider 性能与优化`：处理跨进程数据访问、初始化成本和权限检查
- `1.11 Zygote 启动与优化`：解释预加载、fork 继承和启动阶段的共享成本
- `1.12 AutoFDO 优化`：了解系统与编译器怎样用采样结果改善热点代码布局
- `1.13 MessageQueue 机制与 DeliQueue 无锁优化`：看消息投递路径怎样减少锁等待
- `1.14 锁竞争与同步优化`：把 monitor、futex、优先级反转和等待时间放到实战里看
- `1.15 JNI/NDK 性能优化`：处理 Java / Native 边界、拷贝成本和 trace 埋点
- `1.16 Audio Pipeline 延迟与性能`：理解低时延音频、FAST Mixer、AAudio 的系统约束
- `1.17 IPC 全景`：把 Binder、Socket、共享内存、FMQ、DMA-BUF 放到选型视角下比较

## 阅读建议

- 第一次系统读这一章，建议按 `1.1 → 1.5` 顺着走。读完后，应该能把一次 Binder 调用经过的线程、进程和调度点讲清楚。
- 查启动或卡顿问题时，优先看 `1.2`、`1.4`、`1.8`、`1.11`、`1.14`。读完后，应该能在 Perfetto 或 traces.txt 里先分清问题落在启动分段、Binder 等待、系统服务调度还是锁竞争。
- 补 Android 14/15/16/17 的平台变化时：ch01 内重点看 `1.6`（架构变化总览）、`1.7`（ART 编译管线）、`1.9`（PMS）、`1.12`（AutoFDO）、`1.13`（MessageQueue 无锁优化）、`1.15`（JNI/NDK）、`1.16`（Audio Pipeline）。需要追 Android 17 机制细节时，按主题跳转：Generational CMC → `4.3`、`4.6`、`16.5`；sched_ext → `5.7`、`14.10`、`16.4`；Energy Limiter → `5.7`（待验证）；DeliQueue / ConcurrentMessageQueue → `1.13`。
- 只需要先建立整体印象时，先读 `1.1`、`1.2`、`1.3`、`1.6`。这四节足够把系统边界、版本变化和后面章节的入口搭起来。
- 看完 `1.4` 之后，可以留一个检查点：能不能在 Perfetto 里认出 Binder 事务阻塞和优先级继承；看完 `1.11` 之后，再检查一次能不能解释冷启动里 Zygote、预加载和 fork 继承各自带来的收益与代价。

## 参考资料

### 我见过的最反直觉的 Android 架构问题：UseCase 越多，项目越烂Clean Architecture 落地的
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/技术文章/source/juejin-android/2026-07-04-76232428-我见过的最反直觉的Android架构问题.md
- 类型：技术文章
- 摘要：> 发布时间: 2026-03-31T09:39:53.000Z > 原文链接:  2026-03-31 1,907 阅读9分钟 Clean Architecture 被捧上神坛五六年了。但我最近 review 了几个"按规范来的"项目，发现一个反直觉的规律：UseCase 文件越多，项目...
- 入库时间：2026-07-04
- 评分：14/20

