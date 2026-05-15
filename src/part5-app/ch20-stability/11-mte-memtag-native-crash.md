---
title: "MTE memtagMode 与 Native 崩溃治理"
chapter: "20.11"
status: draft
applicable_versions: "Android 12 (API 31) - Android 16 (API 36)"
tags: ["mte", "memtag", "native-crash", "stability", "security"]
related_chapters: ["4.5", "10.5", "14.3", "20.3", "23.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "素材驱动/官方文档"
sources:
  - type: official
    path: "source.android.com/docs/security/test/memory-safety/arm-mte"
  - type: official
    path: "source.android.com/docs/security/test/memory-safety/mte-configuration"
  - type: aosp
    path: "cs.android.com frameworks/base/core/java/com/android/internal/os/Zygote.java"
  - type: material
    path: "DeepResearch/2026-05-13-android-mte-memtag-async-asymm-analysis.md"
  - type: structure
    path: "Clippings/Android 应用稳定性剖析与优化 - Native Crash 监控：为我们应用插上监控 Native Crash 的电子眼.md"
---

# 20.11 MTE memtagMode 与 Native 崩溃治理

<!-- outline-start -->
## 要点

### 🔹 MTE 在稳定性治理中的适用场景
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

### 🔹 android:memtagMode 的 off、sync、async 选择
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

### 🔹 ASYMM 模式为何不暴露为应用 API
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

### 🔹 Zygote、bionic、Scudo 的生效路径
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

### 🔹 线上灰度开启 MTE 的崩溃归因策略
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

### 🔹 性能、兼容性与误报边界
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

## 扩展

### 🔸 与 Native Crash 信号处理器的配合方式
{待补充：素材充分时展开。}

### 🔸 MTE 报告进入 APM 平台后的聚合字段
{待补充：素材充分时展开。}

<!-- outline-end -->

> 本节内容待加工。
