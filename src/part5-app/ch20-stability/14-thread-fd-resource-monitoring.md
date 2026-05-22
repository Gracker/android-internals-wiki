---
title: "线程与 FD 资源监控治理"
chapter: "20.14"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [stability, thread, fd, oom, observability]
related_chapters: ["20.5", "20.7", "26.2", "26.5", "14.13"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-23"
gap_source: "参考书素材 + research-gaps + AOSP/官方文档对照"
last_verified: "2026-05-23"
last_verified_against: "AOSP android-16.0.0_r1 / AOSP main 搜索结果 / Android Developers API reference"
confidence: medium
sources:
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - 线程监控：如何解决“匿名”线程？.md"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - 实现 FD 监控：文件描述符（FD）超限怎么办？.md"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - OOM 发生路径：了解 OOM 是如何产生的.md"
  - type: aosp
    path: "https://android.googlesource.com/platform/libcore/+/refs/heads/main/ojluni/src/main/java/java/lang/Thread.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/heads/main/runtime/native/java_lang_Thread.cc"
  - type: aosp
    path: "https://android.googlesource.com/platform/bionic/+/refs/heads/main/libc/private/bionic_fortify.h"
  - type: official
    path: "https://developer.android.com/reference/java/io/FileDescriptor"
  - type: official
    path: "https://developer.android.com/ndk/reference/group/file-descriptor"
---

# 20.14 线程与 FD 资源监控治理

<!-- outline-start -->
## 要点

### 🔹 线程与 FD 为什么要放在同一套资源治理里
线程数失控、FD 泄漏、虚拟地址空间不足和 OOM/Native Crash 常在同一条稳定性链路上出现。本节从「资源数量 → 创建来源 → 关闭/回收 → 崩溃补偿」四层建立治理入口，避免只在崩溃栈上找最后一次触发点。

### 🔹 线程快照：数量、名称、状态与调用栈
覆盖 `Thread.getAllStackTraces()`、线程名规范、线程池命名策略、匿名线程识别和采样频率边界。重点说明快照适合回答「当前有哪些线程」，不适合单独回答「是谁创建了线程」。[结构参考: Clippings/Android 应用稳定性剖析与优化 - 线程监控：如何解决“匿名”线程？.md]

### 🔹 匿名线程归因：字节码插桩与运行时兜底
整理无参 `Thread()` / `Thread(Runnable)` 构造的归因方案：编译期 ASM 改写、统一 ThreadFactory、运行时监控三种路径。需要区分可控业务代码、三方库代码、动态加载代码的覆盖边界。[结构参考: Clippings/Android 应用稳定性剖析与优化 - 线程监控：如何解决“匿名”线程？.md]

### 🔹 FD 快照：`/proc/$pid/fd`、`Os.readlink()` 与类型聚合
覆盖普通文件、socket、pipe、anon_inode、ashmem/memfd、eventfd/epoll 等 FD 类型的线上采集字段。重点说明采集要保留数量、目标路径、进程、线程、采样时间和 top-N 聚合结果。[结构参考: Clippings/Android 应用稳定性剖析与优化 - 实现 FD 监控：文件描述符（FD）超限怎么办？.md]

### 🔹 FD 创建归因：open/pipe/socket/dup/close 的 hook 边界
整理 FD 创建函数监控的最小集合、堆栈采样策略、性能开销和安全边界。hook 方案只作为灰度诊断能力，常态监控优先使用低频快照和阈值触发。[结构参考: Clippings/Android 应用稳定性剖析与优化 - 实现 FD 监控：文件描述符（FD）超限怎么办？.md]

### 🔹 与 OOM、ANR、Native Crash 的关联判定
把线程创建失败、FD 超限、Looper/epoll 相关 FD、Binder 线程池耗尽、日志 mmap 文件泄漏放到同一张判定表。结论要回连 20.5 OOM 治理、20.4 ANR 治理和 20.3 Native Crash 分析，不重复展开底层机制。[结构参考: Clippings/Android 应用稳定性剖析与优化 - OOM 发生路径：了解 OOM 是如何产生的.md]

### 🔹 线上治理策略：阈值、分位值、灰度和止血动作
给出线程数、FD 数、增长斜率、重复路径、创建堆栈聚类的指标设计。止血动作只讨论降级、限流、关闭非关键模块、重启子进程，不把强杀进程写成默认治理手段。

## 扩展

### 🔸 与 20.7 异常处理架构的边界
20.7 负责异常捕获和恢复策略，本节只负责资源监控与归因数据。后续加工时用「详见 20.7 节」交叉引用，不重复写异常框架设计。

### 🔸 与 26.2 / 26.5 线上证据包的衔接
本节产出的线程快照、FD 快照、FD 创建堆栈需要进入 crash/ANR 证据包，作为 ApplicationExitInfo、tombstone、traces.txt 的补充材料。

### 🔸 待验证：Android 16/17 bionic fortify 与 FD_SETSIZE 触发路径
需要复核 `__FD_SET_chk`、`FD_SETSIZE`、厂商 libc 差异和目标 SDK 行为边界，避免把老设备现象写成所有 Android 版本的通用结论。

### 🔸 待验证：字节码插桩与现代 AGP/ASM Transform 接入方式
需要补齐 AGP 8.x 插件接入方式、Transform API 退场后的替代路径，以及 R8/混淆对线程归因类名的影响。

<!-- outline-end -->

> 本节内容待加工。
