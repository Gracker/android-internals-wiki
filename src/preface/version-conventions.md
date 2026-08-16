---
title: "版本约定"
chapter: "preface.5"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-25"
last_verified_against: "AOSP android-17.0.0_r1; Android Common Kernel android17-6.18-2026-06_r6"
confidence: high
sources:
  - type: official
    path: "https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1/default.xml"
  - type: official
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/"
tags: [introduction, versioning, aosp, kernel]
---

# 版本约定

Android 版本会改变系统行为、源码路径和观测能力。同一条排障经验在 Android 10、Android 15 与 Android 17 上可能对应不同方法、系统跟踪（trace）事件或限制条件，因此正文会同时标明版本范围和源码标签（tag）。

## 平台版本标注

正文使用 `Android X（API N）- Android Y（API M）` 表示连续适用范围，例如：

- `Android 8（API 26）- Android 17（API 37）`
- `Android 12（API 31）- Android 17（API 37）`
- `Android 15（API 35）及以上；本书验证到 Android 17（API 37）`

“及以上”只覆盖章节明确验证过的最高版本，不自动包含 Android 18 或后续版本。API 级别表示 SDK 接口版本，AOSP 源码标签表示本次核对的具体源码快照；两者用途不同，正文需要源码论证时应同时给出。

## 默认平台源码

平台结论默认按 Android 开源项目（AOSP）`android-17.0.0_r1` 核对。该源码标签用于核对 Java 框架层（Framework）、C/C++ 原生系统组件、Android 运行时（ART）、Android C 标准库 Bionic、硬件抽象层（HAL）接口定义与平台工具等源码。

旧版源码标签可以保留在版本演进段落中。例如一项行为在 Android 12 引入、Android 15 重构、Android 17 再次调整时，正文应分别指出发生变化的源码标签、路径或符号，并用 `android-17.0.0_r1` 说明当前行为。

`main`、`master` 与开发分支会继续变化。它们可以帮助发现未来方向，但不能作为 Android 17 行为的证据。若开发分支与 Android 17 源码标签不同，正文以固定源码标签为准。

## 默认内核源码

涉及 Linux 调度、内存管理、Binder 驱动、文件系统、BPF 内核程序、PSI 资源压力统计、cgroup 进程资源分组或电源管理时，默认按 Android Common Kernel（ACK，Android 公共内核）`android17-6.18-2026-06_r6` 核对。

ACK 源码标签只覆盖公共内核版本。具体设备还可能包含：

- SoC（片上系统）厂商驱动和调度扩展；
- 通用内核镜像（Generic Kernel Image，GKI）的厂商模块；
- 产品默认内核配置（defconfig）、设备树与内核命令行；
- 厂商性能、温控和功耗策略。

因此，ACK 中存在某项能力不等于所有 Android 17 设备都以同样配置启用；ACK 中没有厂商实现，也不能证明设备上不存在对应扩展。涉及量产设备时，需要补充该设备的内核提交版本、配置和厂商实现证据。

## 阅读版本差异

遇到受版本影响的结论，正文应交代三个观察点：

1. 变化从哪个版本开始，旧行为是什么；
2. 本书采用的 Android 17 固定版本中，代码路径与行为是什么；
3. 系统跟踪数据、日志、命令或 API 表现会怎样变化。

按这三个观察点核对，可以区分“设备没有触发条件”“厂商实现不同”和“资料引用了其他 Android 版本”。全书的确定性结论最高到 Android 17；更高版本只作为明确隔离的后续线索。
