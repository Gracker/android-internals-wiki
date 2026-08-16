---
title: "写在前面"
chapter: "preface.1"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-25"
last_verified_against: "AOSP android-17.0.0_r1; Android Common Kernel android17-6.18-2026-06_r6; developer.android.com; source.android.com"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/guide"
  - type: official
    path: "https://source.android.com/docs"
  - type: blog
    path: "obsidian/Android 性能优化实践观察.md"
tags: [introduction, overview, reader-guide, methodology]
related_chapters: ["1.1", "2.1", "3.1"]
---

# 写在前面

本书当前为中文版本，v1.0 发布后将提供英文版本（*Android Internals & Performance: From Principles to Practice*）。

市面上的 Android 资料通常各有侧重：API 手册解决接口怎么用，源码文章解释某一条调用路径，性能案例记录一次问题怎么处理。这本书把系统机制、性能问题、分析工具和版本演进放进同一套结构，方便读者从现象一路查到代码与数据。

全书围绕一个在实际工作里会反复出现的问题展开：

**当一个 Android 应用或系统组件“变慢、变卡、变得不稳定”时，应该怎样从现象走到机制，再从机制走回可执行的判断和工具。**

系统运行机制、性能专题、工具和分析方法在实际排障中互相依赖。渲染问题需要结合 Perfetto 采集的系统跟踪数据（trace）定位；解读工具结果时也要理解线程、输入与画面合成之间的调用关系，否则只能看到异常，无法判断异常从哪里产生。

书中的技术术语采用中英文混合的方式：对于 Android 领域的专有名词（如 Choreographer、SurfaceFlinger、Binder、VSync 等）保留英文原文，不做翻译；对于通用概念则使用中文，并在首次出现时注明英文对照。完整的术语对照表见附录 E。

正文的确定性结论最高覆盖 Android 17（API 37）。核对平台机制时使用 Android 开源项目（Android Open Source Project，AOSP）的固定源码标签 `android-17.0.0_r1`；核对内核机制时使用 Android Common Kernel（Android 公共内核）的固定源码标签 `android17-6.18-2026-06_r6`。固定标签让不同读者可以回到同一份代码核对结论。低版本源码只用于解释版本演进或兼容边界，Android 18 及后续版本不进入本书的确定性结论。

完整的 AOSP 开发经验不是阅读前提。具备 Android 应用开发、系统服务或性能测试经验即可从实际问题开始；涉及 Java 框架层（Framework）、C/C++ 原生层（Native）与 Linux 内核（Kernel）的章节会先交代对象和调用关系，再给出源码入口（类、方法或文件路径）、观测方法与版本边界。
