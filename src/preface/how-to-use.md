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

如果你已经在做 Android 开发，阅读方式通常会更像这样：

- 遇到列表滑动卡顿，就先看第 7 章和渲染相关章节。
- 遇到启动慢，就直接跳到第 8 章，再配合工具章节一起看。
- 遇到 ANR，就把第 9 章、Perfetto 章节和方法论章节连起来看。
- 需要快速排查线索，可以随时翻阅**附录**中的 Checklist、命令速查表和 Perfetto 模板。

前面的基础章节负责解释系统对象和调用关系，后面的性能专题、工具和分析方法负责处理具体问题。初次阅读不必记住所有源码细节，先掌握问题对应的系统层次、观测工具和主要代码入口，排障时再沿路径核对。

如果你是第一次系统学习 Android 性能，推荐先读：

1. 前言中的阅读路径和版本约定。
2. 第一部分里和线程、渲染、输入最相关的章节。
3. 第二部分里的流畅性、响应速度、ANR。
4. 第三部分里的 Perfetto、方法论和线上监控。

如果已经有明确问题，可以直接从对应章节切入，再回头补前置知识。阅读源码结论时同时确认章节的适用版本：平台代码默认看 AOSP `android-17.0.0_r1`，内核代码默认看 Android Common Kernel `android17-6.18-2026-06_r6`；旧版本只用于说明演进和兼容边界。
