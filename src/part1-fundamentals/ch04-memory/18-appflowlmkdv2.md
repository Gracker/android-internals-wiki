---
title: "AppFlow大应用冷启动内存联合调度与LMKDv2协作机制"
chapter: "18"
status: deprecated
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: ["memory", "optimization", "android17"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-03"
gap_source: "素材驱动/AOSP结构/章节深挖"
---
> ⚠️ **本节已废弃 (deprecated 2026-07-04)**：与 4.5 + 4.12 内容重复。duplicate of 4.5; wrong chapter number; generic template outline。



# 18 AppFlow大应用冷启动内存联合调度与LMKDv2协作机制

<!-- outline-start -->
## 要点

### 🔹 内存管理基础
AppFlow大应用冷启动内存联合调度与LMKDv2协作机制的核心概念与架构原理

### 🔹 Android 17 新特性
Android 17中的关键改进与性能优化

### 🔹 协作机制实现
AppFlow与LMKD v2的具体协作方式

### 🔹 性能优化策略
针对不同场景的优化配置与参数调优

## 扩展

### 🔸 大应用冷启动优化
GB级应用的启动性能优化方案

### 🔸 内存回收策略
智能内存回收与预加载机制

### 🔸 实战案例分析
典型场景下的优化效果验证

<!-- outline-end -->

## 源码核查结论

这份文件是历史占位稿，不应扩写成独立技术章节。对 Android 17 / `android-17.0.0_r1` 的 `frameworks/base/services/core/java/com/android/server/am` 与 `system/memory/lmkd` 检查后，没有找到下列上游实现：

- `AppFlowManager` 或同名系统服务；
- AppFlow 与 lmkd 的控制命令、Binder 接口或共享阈值协议；
- `/data/app-staging/` 下的 AppFlow checkpoint；
- 名为“LMKD v2”的独立 daemon、接口版本或兼容层。

“AppFlow”如果来自 OEM 私有分支、实验项目或论文，应补充仓库、tag、类名和协议定义，再另行讨论。仅凭概念名无法把它归入 AOSP Android 17。

### 占位 outline 中需要废弃的假设

| 占位说法 | Android 17 源码结果 |
|---|---|
| AppFlow 与 lmkd 有直接协作协议 | 上游 lmkd 控制协议没有 AppFlow 命令 |
| LMKD v2 是正式组件名 | AOSP 仍使用 `lmkd`；新旧能力应按命令、属性和实现提交描述 |
| `LMK_PROCS_PRIO` 一次最多处理 32 个进程 | `ProcessList.MAX_PROCS_PRIO_PACKET_SIZE` 与 `MAX_PROCS_PRIO_RECORD_COUNT` 均为 3 |
| 批量更新基于 io_uring | `ProcessList` 经 `LmkdConnection` 控制 socket 发送，lmkd 端没有这项 io_uring 实现 |
| MGLRU 与 AppFlow 共享状态机 | 内核回收策略与 lmkd 决策可以共同影响冷启动，但源码没有这套共享状态机 |
| 冷启动存在 AppFlow 专属保护窗口 | 上游没有对应窗口；进程保护来自 AMS proc state、`oom_score_adj` 等既有机制 |

这些条目保留在上方受保护 outline 中，只用于说明占位稿原先想覆盖的范围，不能作为已验证事实引用。

## Android 17 中可以确认的边界

### 1. AMS 决定进程优先级

Android 17 的 OomAdjuster 根据组件、可见性、绑定关系和进程状态计算 adj。`ProcessList.setOomAdj()` 再通过 `LMK_PROCPRIO` 把 PID、UID、adj、进程类型和 `for_lmkd_only` 发送给 lmkd。

批量更新使用命令号 11 的 `LMK_PROCS_PRIO`。一条记录包含 5 个整数，每个控制包最多 3 条记录。该优化减少多次 socket exchange，不表示应用获得了修改 lmkd 决策的接口。

### 2. lmkd 独立判断何时杀进程

lmkd 综合 PSI、watermark、swap、回收效率、thrashing 和候选进程 adj 等信号。`ro.lmk.thrashing_limit` 与 `ro.lmk.thrashing_limit_decay` 对应的动态衰减逻辑可在 `lmkd.cpp` 中找到，但它属于 lmkd 的压力判断，不是冷启动专属协议。

应用冷启动进入前台后，AMS 通常会通过 proc state 与 adj 提高其存活优先级。系统内存压力严重时，lmkd 仍可能先杀更容易回收的后台或 cached 进程。这里的因果关系来自 AMS 与 lmkd 的通用机制，无需假设 AppFlow。

### 3. 普通应用不能直接控制 lmkd

`LMK_PROCPRIO`、`LMK_PROCS_PRIO` 和 `LMK_PROCREMOVE` 是 platform 内部协议。普通应用没有权限连接控制 socket，也不应自行写 `oom_score_adj`。冷启动优化应放在应用可控制的范围：

- 减少启动前必须驻留的 Java/native 对象；
- 延迟不影响首帧的解码、模型加载和大缓存初始化；
- 避免并发制造大批匿名页与 swap-in；
- 用启动 trace、PSS/RSS、major fault、PSI 和 lmkd kill 记录验证效果。

如果 OEM 要实现类似 AppFlow 的系统策略，需要在自己的源码分支中说明：谁计算状态、谁有权限更新 adj、如何处理进程死亡与 PID 复用、怎样与 OomAdjuster 保持一致，以及压力下由哪一方作最终决策。

## 迁移说明

本文件保持 `deprecated`，用于阻止旧链接丢失和记录错误假设。后续阅读应转向：

- §4.15：Android 17 PSI、lmkd 压力判断与 kill reason；
- §4.4：低内存管理与进程优先级基础；
- 启动章节：应用冷启动的测量与工作集优化。

原废弃提示提到的 4.5 AppFlow 文稿也需要独立源码审计，不能仅因两篇内容重复就把它当成事实来源。

## 源码索引

- [Android 17 lmkd 控制协议与每包记录上限](https://android.googlesource.com/platform/system/memory/lmkd/+/android-17.0.0_r1/include/lmkd.h)
- [Android 17 lmkd PSI、thrashing 与进程选择](https://android.googlesource.com/platform/system/memory/lmkd/+/android-17.0.0_r1/lmkd.cpp)
- [ProcessList：LMK_PROCPRIO 与 LMK_PROCS_PRIO](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ProcessList.java)
