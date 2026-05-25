---
title: "Private Space 与应用锁的兼容性边界"
chapter: "17.7"
status: draft
applicable_versions: "Android 15 (API 35) - Android 16 QPR2；Android 17 应用锁功能待官方源码确认"
tags: [private-space, app-lock, user-profile, launcher, notification, media-access]
related_chapters: ["1.3", "1.9", "12.2", "17.1", "20.7", "24.13", "26.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-25"
gap_source: "官方文档/每日信息/素材驱动"
sources:
  - type: official
    path: "https://source.android.com/docs/security/features/private-space"
  - type: official
    path: "https://source.android.com/docs/whatsnew/android-16-release"
  - type: blog
    path: "intake/daily-info/2026-05-25.md"
  - type: blog
    path: "source/juejin-android/2026-05-22-76046943-Android_17_终于有原生应用锁了.md"
---

# 17.7 Private Space 与应用锁的兼容性边界

<!-- outline-start -->
## 要点

### 🔹 Private Space 的系统模型
说明 Private Space 作为独立 profile 的安装、隐藏、锁定和解锁状态，重点落到 Launcher、Settings、PackageManager 查询和跨 profile 可见性边界。

### 🔹 应用锁与 Private Space 的边界差异
区分系统级 profile 隔离、OEM 应用锁、传闻中的 Android 17 原生应用锁三类机制，避免把通知隐藏、启动拦截、任务栈恢复写成同一个能力。

### 🔹 对启动、任务栈和进程生命周期的影响
梳理用户解锁、从 Launcher 启动、从通知进入、从分享入口进入时，Activity 启动、冷启动归因、最近任务和进程保活的观察点。

### 🔹 通知、媒体访问和 URI 授权边界
覆盖锁定状态下通知内容展示、Photo Picker/MediaStore 结果、DocumentsUI 回退、一次性 URI 授权失效和用户中断导致的稳定性问题。

### 🔹 OEM 差异与兼容性探测
整理小米、三星等应用锁方案与 AOSP Private Space 的能力差异，用能力探测、失败码、版本/品牌维度统计替代厂商硬编码。

### 🔹 线上指标与排查入口
建立应用锁/Private Space 相关的启动失败率、空数据率、授权失败率、通知点击丢失率和页面恢复耗时指标，并给出日志字段建议。

## 扩展

### 🔸 与 24.13 Photo Picker、媒体转码与缓存治理的交叉
媒体选择、云端照片、隐私空间和应用锁会同时影响 URI 可用性，需要在 24.13 只保留性能处理，系统兼容性放到本节。

### 🔸 与 26.3 性能指标采集与上报的交叉
隐私相关状态不能直接采集个人敏感信息，只记录匿名化的系统版本、profile/锁定状态可见信号和失败类型。

### 🔸 Android 17 原生应用锁待验证清单
记录需要等待官方 SDK、AOSP tag 或 Android Developers 文档确认的 API、广播、权限、通知策略和 Launcher 行为。

<!-- outline-end -->

> 本节内容待加工。
