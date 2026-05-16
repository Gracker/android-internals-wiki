---
title: "SafeMode 崩溃循环判定与启动补偿链路"
chapter: "20.12"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [stability, safemode, crash-loop, applicationexitinfo, startup]
related_chapters: ["20.2", "20.3", "20.6", "20.7", "26.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "章节深挖/参考书素材"
---

# 20.12 SafeMode 崩溃循环判定与启动补偿链路

<!-- outline-start -->
## 要点

### 🔹 崩溃循环的状态机设计
围绕启动期连续崩溃、Native 退出、ANR、低内存杀进程和 WebView renderer 退出，补齐 SafeMode 判定与补偿证据链。

### 🔹 启动 marker 的写入、完成与清理
围绕启动期连续崩溃、Native 退出、ANR、低内存杀进程和 WebView renderer 退出，补齐 SafeMode 判定与补偿证据链。

### 🔹 Java / Native / ANR / LMK 的证据差异
围绕启动期连续崩溃、Native 退出、ANR、低内存杀进程和 WebView renderer 退出，补齐 SafeMode 判定与补偿证据链。

### 🔹 ApplicationExitInfo 的补偿入口
围绕启动期连续崩溃、Native 退出、ANR、低内存杀进程和 WebView renderer 退出，补齐 SafeMode 判定与补偿证据链。

### 🔹 WebView renderer 退出的单独处理
围绕启动期连续崩溃、Native 退出、ANR、低内存杀进程和 WebView renderer 退出，补齐 SafeMode 判定与补偿证据链。

### 🔹 SafeMode 降级动作与恢复条件
围绕启动期连续崩溃、Native 退出、ANR、低内存杀进程和 WebView renderer 退出，补齐 SafeMode 判定与补偿证据链。

## 扩展

### 🔸 文件落盘协议：tmp、fsync、rename
待结合素材验证后展开。

### 🔸 版本升级与用户强杀的排除规则
待结合素材验证后展开。

<!-- outline-end -->

> 本节内容待加工。
