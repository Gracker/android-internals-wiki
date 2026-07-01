---
title: "Android 17 ANR 预警回调与类型枚举"
chapter: "9.10"
status: draft
applicable_versions: "Android 17 (API 37)"
tags: [ANR, warning, callback, AnrTypes, observability]
related_chapters: ["9.1", "9.2", "9.3", "9.8", "26.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-02"
gap_source: "每日技术文章 intake"
---

# 9.10 Android 17 ANR 预警回调与类型枚举

<!-- outline-start -->
## 要点

### 🔹 AnrTypes 枚举体系
Android 17 新增 AnrTypes 枚举，定义输入超时、广播超时、前台服务超时等 ANR 类型，为 ANR 分类提供了统一的类型系统。[结构参考: daily-info/2026-07-01 技术文章 #39]

### 🔹 AnrWarningResult 预警结果
新增 AnrWarningResult 数据结构，在 ANR 发生前向调用方发出预警，携带更多调试上下文。[结构参考: daily-info/2026-07-01 技术文章 #39]

### 🔹 IAnrWarningCallback.aidl 预警回调接口
新增 IAnrWarningCallback.aidl，定义 ANR 发生前的预警回调接口。主要文件包括 AnrTypes.java、AnrWarningResult 和 IAnrWarningCallback.aidl。[结构参考: daily-info/2026-07-01 技术文章 #39]

### 🔹 与现有 ANR 监控体系的集成
预警回调系统与现有的 AppNotResponding 检测流程如何协作，以及应用/SDK 如何注册回调以在 ANR 发生前获得预警。[待验证: AOSP android-17.0.0_r1]

### 🔹 ANR 预警对线上可观测性的价值
预警机制让监控 SDK 可以在 ANR 真正触发前采集现场信息（线程栈、锁状态、Binder 队列），提升线上 ANR 诊断的根因定位率。

## 扩展

### 🔸 AnrWarningCallback 与 ProfilingTrigger 的联动
[待验证: ANR 预警回调是否能触发 ProfilingManager 的自动 trace 采集]

### 🔸 预警时序与 ANR 触发时序的关系
[待补充: 从预警回调到真正 ANR 之间的时间窗口，以及该窗口内可执行的诊断动作]

### 🔸 跨厂商兼容性
[待验证: AnrWarningCallback 是否受 OEM 定制 ANR 逻辑影响]

<!-- outline-end -->

> 本节内容待加工。
