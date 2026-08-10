---
title: "写在前面"
chapter: "preface.1"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
drafted_date: "2026-06-22"
drafted_by: openclaw-task2a
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

**当一个 Android 应用或系统组件"变慢、变卡、变得不稳定"时，应该怎样从现象走到机制，再从机制走回可执行的判断和工具。**

系统运行机制、性能专题、工具和分析方法在工程现场本来就连在一起。渲染原理需要配合 Perfetto 才能用于排障；工具分析也需要线程、输入与合成链路作为判断依据，否则只能看到异常，无法定位异常的来源。

书中的技术术语采用中英文混合的方式：对于 Android 领域的专有名词（如 Choreographer、SurfaceFlinger、Binder、VSync 等）保留英文原文，不做翻译；对于通用概念则使用中文，并在首次出现时注明英文对照。完整的术语对照表见附录 E。

正文以 Android 17（API 37）为最高平台基线，平台源码锚定 AOSP `android-17.0.0_r1`，内核源码锚定 Android Common Kernel `android17-6.18-2026-06_r6`。低版本源码只用于解释版本演进或兼容边界，Android 18 及后续版本不进入本书的确定性结论。

完整的 AOSP 开发经验不是阅读前提。具备 Android 应用开发、系统服务或性能测试经验即可从实际问题切入；涉及 Framework、Native 与 Kernel 的章节会先交代对象和调用关系，再给出源码入口、观测方法与版本边界。
