---
title: "Android 系统启动耗时优化与 bootanalyze"
chapter: "16.7"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [aosp, boot, boot-time, perfetto, performance]
related_chapters: ["1.2", "8.2", "13.2", "16.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-17"
gap_source: "官方文档/AOSP结构"
---

# 16.7 Android 系统启动耗时优化与 bootanalyze

<!-- outline-start -->
## 要点

### 🔹 系统启动耗时的分段口径
从 bootloader、kernel、init、Zygote、system_server 到 launcher ready 拆分系统启动耗时，区分平台侧 boot time 与 App cold launch 的统计边界。

### 🔹 bootanalyze 与 boot_trace 的观察入口
整理 AOSP `system/extras/boottime_tools` 中的 bootanalyze / boot_trace 使用场景，说明它们分别适合拆启动阶段耗时、文件读取和早期 I/O 访问。

### 🔹 init rc、service class 与并行启动约束
分析 init 服务启动顺序、class 分组、属性触发和关键服务依赖，解释系统启动阶段哪些路径能并行，哪些路径必须串行等待。

### 🔹 Zygote 与 system_server 的启动成本
连接 1.2、1.11 和 16.6 节已有内容，聚焦 Zygote 预加载、system_server 服务初始化和 dexopt/profile 状态对系统 boot time 的影响。

### 🔹 I/O、page fault 与存储预热
把启动早期文件读取、page fault、fsync / checkpoint、apex / odex 访问放到同一条分析线，给出 Perfetto 与 boot_trace 的互证方式。

### 🔹 bootstat 与指标落库
梳理 bootstat 记录的阶段指标、系统属性和统计口径，说明 ROM / 平台团队如何把单次 boot trace 变成可回归的版本指标。

### 🔹 系统启动优化的安全边界
列出不应牺牲的边界：安全策略初始化、存储解密、SELinux、关键系统服务可用性、OTA 后首次启动差异。

## 扩展

### 🔸 Android 16/17 AutoFDO、16KB page size 对 boot time 的间接影响
对照 1.12、4.7 和 16.6 节，只记录系统级优化如何改变启动基线，不重复展开机制。

### 🔸 OEM 定制启动阶段的可观测性缺口
记录厂商定制服务、预装应用和私有守护进程对启动耗时的影响，后续可结合实机 trace 补证。

<!-- outline-end -->

> 本节内容待加工。
