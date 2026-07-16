---
title: "Facebook Profilo 框架线上 ATrace 收集方案"
chapter: "26.27"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [Profilo, atrace, trace-marker, PLT-Hook, observability, Facebook]
related_chapters: ["26.21", "26.23", "20.22"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "参考书驱动（Clippings/线上疑难问题 46.md）"
---

# 26.27 Facebook Profilo 框架线上 ATrace 收集方案

<!-- outline-start -->
## 要点

### 🔹 Profilo 框架架构概述
{Facebook 开源的高性能线上 trace 收集框架，核心能力：atrace 拦截 + 快速采样 + 低开销上传}

### 🔹 PLT Hook 拦截 trace_marker 写入
{通过 PLT Hook 拦截 write() 到 trace_marker fd 的写入，在不修改目标应用代码的情况下收集 atrace 事件}

### 🔹 atrace_enabled_tags 全位掩码策略
{atrace_enabled_tags 设为 0xFFFFFFFF 启用所有 category，突破默认的 atrace tag 限制}

### 🔹 trace_marker 机制与 ftrace 接口
{trace_marker 是 ftrace 提供的用户态事件写入接口（/sys/kernel/tracing/trace_marker），每次写入产生系统调用（用户态→内核态切换）}

### 🔹 traceBegin/traceEnd 匹配算法
{通过 CPU 编号 + task_pid 对应嵌套的 B/E 事件对，重建线程的 trace 调用栈}

### 🔹 线程创建监控：PLT Hook pthread_create
{Hook pthread_create 可监控线程创建，但需区分 Attached（VM 托管）与 Unattached（非托管）线程的限制}

### 🔹 Profilo 与 Perfetto 的互补关系
{Profilo 适合线上大规模灰度（轻量采样），Perfetto 适合深度分析（完整 trace）；两者可协同使用}

## 扩展

### 🔸 Profilo 的 Quicken 模式与低开销采样
{极低开销的采样模式，适用于生产环境全量开启}

### 🔸 Profilo 在 Android 17 上的兼容性挑战
{Android 安全硬化（如 hidden API 限制、SELinux 策略收紧）对 PLT Hook 的影响}

<!-- outline-end -->

> 本节内容待加工。
