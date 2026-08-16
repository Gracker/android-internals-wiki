---
title: "适用读者"
chapter: "preface.3"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-25"
last_verified_against: "repository content scope and chapter prerequisites"
confidence: high
tags: [introduction, reader-guide, prerequisites]
---

# 适用读者

这本书面向初级和中级 Android 工程师，也为需要查源码路径的系统工程师保留足够的实现细节。读者最好已经写过一个完整应用，知道 Activity、主线程、后台线程和日志的基本用法；不要求提前熟悉 Android 开源项目（AOSP）源码、C/C++ 原生层（Native）、Linux 内核（Kernel）或 Perfetto 系统跟踪工具，这些内容会在相关章节逐步介绍。

## 1. 初级应用工程师

做过页面、列表、启动、图片、网络或数据库等常见开发工作后，书中的多数问题都能对应到日常场景。阅读时可以先看现象、观测方法和结论，再沿着章节给出的类名、方法名和源码路径补充系统知识。

## 2. 中级应用与性能优化工程师

经常处理卡顿、启动、ANR、内存或功耗问题时，本书可以作为排障手册。章节会解释机制和源码入口，指出系统跟踪数据（trace）里该看哪些线程、事件和指标，也会说明结论在哪些版本和条件下成立。这样可以把单次经验整理成可重复的分析步骤。

## 3. Android Framework / 系统工程师

Framework、SystemUI、ROM、芯片平台、调度或图形栈方向可以从前半部分给出的源码调用路径开始。渲染、输入、内存、调度和功耗章节按 Android 17 平台源码与 6.18 Android Common Kernel 公共内核源码核对，同时保留必要的历史版本差异。

## 4. 测试、质量与基础架构工程师

需要理解性能问题怎样产生、怎样度量和怎样复现时，可以优先阅读后半部分的分析方法、工具和线上监控章节，不要求每天编写业务代码。

## 前置要求

完全没有 Android 开发经验的读者会遇到较多前置概念。建议先完成一个包含页面、异步任务、网络和本地存储的小型应用，再从本书第一部分开始。书中不要求读者预先会读 AOSP，但会默认读者愿意根据章节给出的路径打开源码、运行命令，并用 trace 或日志验证结论。
