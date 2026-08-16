---
title: "本书的使用方式"
chapter: "preface.2"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-25"
last_verified_against: "AOSP android-17.0.0_r1; Android Common Kernel android17-6.18-2026-06_r6; repository chapter layout"
confidence: high
tags: [introduction, reader-guide, methodology]
---

# 本书的使用方式

这本书既可以按章节顺序建立系统知识，也可以带着具体问题查阅。对已经遇到性能问题的读者，后者通常更快。

已有 Android 开发经验时，可以按问题跳读：

- 列表滑动卡顿：先看第 7 章和渲染相关章节。
- 启动慢：从第 8 章开始，再配合工具章节核对。
- ANR：结合第 9 章、Perfetto 系统跟踪工具和分析方法章节。
- 快速排查线索：查阅**附录**中的检查清单、命令速查表和 Perfetto 模板。

前面的基础章节负责解释系统对象和调用关系，后面的性能专题、工具和分析方法负责处理具体问题。初次阅读不必记住所有源码细节，先弄清问题涉及哪些系统层次、需要采集什么数据以及主要代码入口，排障时再沿路径核对。

首次系统学习 Android 性能时，推荐按以下顺序阅读：

1. 前言中的阅读路径和版本约定。
2. 第一部分里和线程、渲染、输入最相关的章节。
3. 第二部分里的流畅性、响应速度、ANR。
4. 第三部分里的 Perfetto、分析方法和线上监控。

已有明确问题时，可以直接从对应章节开始，再回头补前置知识。阅读根据源码得出的结论时，还要确认章节的适用版本：平台机制默认按 AOSP `android-17.0.0_r1` 核对，内核机制默认按 Android Common Kernel `android17-6.18-2026-06_r6` 核对；旧版本只用于说明演进和兼容边界。
