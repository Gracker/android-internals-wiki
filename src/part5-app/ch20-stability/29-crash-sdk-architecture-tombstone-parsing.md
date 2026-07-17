---
title: "Crash 报告 SDK 架构选型与 tombstone 解析实战"
chapter: "20.29"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [crash, tombstone, stack-unwind, symbolication, Firebase, Bugly, SDK]
related_chapters: ["20.01", "20.03", "20.18", "26.02", "26.23"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-17"
gap_source: "章节深挖+素材驱动"
---

# 20.29 Crash 报告 SDK 架构选型与 tombstone 解析实战

<!-- outline-start -->
## 要点

### 🔹 Crash 捕获 SDK 架构选型对比
- Firebase Crashlytics：集成成本最低，Google Play 生态首选
- Bugly / 友盟：国内非 Play 渠道主力，支持 Java/Native crash
- 自建 Crash SDK（XCrash / Razor / Bootlegger）：控制力最强，成本最高
- 选型决策矩阵：渠道分布、Native crash 比例、团队维护能力

### 🔹 Java 异常捕获链路
- Thread.setDefaultUncaughtExceptionHandler 的注册时机与优先级
- 与 tombstoned / debuggerd 的协同（Java crash → native crash 转换场景）
- ART 的 abort() 路径绕过 UEH 的陷阱

### 🔹 Native crash 信号捕获与 tombstone 解析
- sigaction 注册 SIGSEGV/SIGABRT/SIGBUS 的链式调用问题
- signal handler 中的 async-signal-safe 函数限制
- tombstone 文件格式解析：backtrace / memory map / fault address
- /proc/self/maps 与 /proc/self/status 的采集策略

### 🔹 Native 堆栈还原（Symbolication）
- 本地 symbol server vs 云端符号化（addr2line / llvm-symbolizer）
- minidebuginfo 与 .sym 文件的生成与存储
- system framework 符号表的获取（*/symbols/ 目录）
- ProGuard/R8 mapping 与 Native symbol 的双轨映射

### 🔹 Crash 报告的上报策略与节流
- 崩溃时的磁盘 IO：追加写 vs mmap buffer
- 上报时机：下次启动上报 vs 即时上报
- 节流策略：同一 crash hash 的采样率与去重
- Crash 报告体积控制：backtrace frames 截断、memory dump 范围

### 🔹 Android 17 debuggerd 与 tombstoned 架构变化
- debuggerd_client 的 socket 通信协议演进
- tombstoned 的 crash 墓碑文件的 rotation 与权限
- ProcessRecordType 与 crash 分类标签
- HWASan/MTE crash 报告的特殊字段

## 扩展

### 🔸 Crash 报告中的隐私合规
- backtrace 中的路径泄漏风险
- 内存 dump 的 PII 扫描与脱敏

### 🔸 从 Crash 到在线诊断
- 详见 26.05 在线疑难排查与 26.23 XTrace 动态追踪

<!-- outline-end -->

> 本节内容待加工。 [结构参考: Clippings/《线上疑难问题该如何排查和跟踪》crash 诊断相关章节]
