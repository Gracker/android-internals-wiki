---
title: "Crash 状态下 Java 线程堆栈获取与锁等待分析"
chapter: "20.24"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [crash, java-stack, ThreadList, StackVisitor, MonitorInfo, lock-wait]
related_chapters: ["20.02", "20.03", "20.18", "26.27"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "参考书驱动（Clippings/线上疑难问题 46.md）"
---

# 20.24 Crash 状态下 Java 线程堆栈获取与锁等待分析

<!-- outline-start -->
## 要点

### 🔹 Crash 时获取 Java 线程堆栈的挑战
{Native Crash 发生时，ART 虚拟机可能处于不稳定状态，常规 JNI 调用可能失败，需要特殊手段获取 Java 层线程堆栈}

### 🔹 方案一：ThreadList::ForEach 间接遍历
{通过 ART 内部接口 ThreadList::ForEach 遍历所有线程，获取每条线程的 Java 堆栈}

### 🔹 方案二：Profilo Unwinder 模拟 StackVisitor
{模拟 ART StackVisitor 逻辑，自行实现栈遍历，减少对 ART 内部状态的依赖}

### 🔹 MonitorInfo 构造与 Object 锁等待分析
{通过 MonitorInfo 构造方法获取 Object 锁的等待线程列表，需计算地址偏移量定位内存结构}

### 🔹 锁竞争导致的假死/ANR 诊断
{当关键线程被锁阻塞时，即使没有 Crash 也可能导致 ANR；结合锁等待信息可区分真正的死锁与长时间持锁}

### 🔹 FinalizerWatchdog 系统防护机制
{FinalizerWatchdog 监控 finalize 方法执行超时，超时后触发进程退出；了解其工作原理有助于排查莫名退出}

### 🔹 线程堆栈符号化与去重
{获取到的大量线程堆栈需进行符号化和去重处理，才能高效定位问题}

## 扩展

### 🔸 Framework 异常的反射/代理绕过思路
{Toast、Service 等系统组件异常时的绕过策略}

### 🔸 Memory Allocation Trace 监控模块
{大对象分配监控 + 调用栈分析，辅助 OOM 根因定位}

<!-- outline-end -->

> 本节内容待加工。
