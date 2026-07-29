---
title: "Android 17 Staged Install 状态机与原子性安装"
chapter: "1.52"
status: deprecated
applicable_versions: "Android 17 (API 37)"
tags: [安装管理, 状态机, 原子性, APEX, 包管理]
related_chapters: ["1.46", "1.49", "16.6"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-03"
gap_source: "AOSP结构"
---
> ⚠️ **本节已废弃 (deprecated 2026-07-04)**：与 1.45 + 1.49 内容重复。



# 1.52 Android 17 Staged Install 状态机与原子性安装

<!-- outline-start -->
## 要点

### 🔹 会话状态机架构
- pre-reboot verification 状态验证
- ready/applied/failed 状态转换逻辑
- commit/rollback 状态分支处理
- 状态持久化与恢复机制

### 🔹 会话类型差异处理
- APK-only session 的特殊路径
- staged APEX session 的处理流程
- APK-in-APEX session 的嵌套处理
- multi-package staged session 的复杂场景

### 🔹 原子性保证机制
- 会话检查点的创建时机
- 事务原子性的实现原理
- 失败时的回滚触发条件
- 数据一致性保证策略

### 🔹 持久化行为设计
- `/data/app-staging/session_{id}` 目录结构
- session XML 配置文件格式
- apexd checkpoint 的管理方式
- 失败后的清理机制

### 🔹 核心链路解析
- PackageInstallerSession#commit() 调用流程
- StagingManager#commitSession() 实现
- PackageInstallerService#restoreAndApplyStagedSessionIfNeeded() 分工
- StagingManager#restoreSessions() / resumeSession() 协作

## 扩展

### 🔸 回滚机制深度分析
- setSessionFailed() 的触发条件
- abortCommittedSession() 的执行路径
- 数据恢复的完整性保证
- 用户可见状态的同步更新

### 🔸 多设备协作场景
- 跨设备的会话同步机制
- 网络中断的容错处理
- 分发集群的协作协议
- 版本兼容性的保证策略

### 🔸 安全机制设计
- 会话权限的验证机制
- 安装包的完整性校验
- 敏感操作的审计日志
- 恶意安装的防护策略

<!-- outline-end -->

> 本页已废弃。上方历史提纲保留给 Hermes 流水线追踪；完整且已按 Android 17 源码校验的说明见 [Android Staged Install 与安装原子性性能](./23-staged-install-performance.md)。本页只纠正重复提纲中容易扩散的错误。

## 适用边界

校验锚点为平台 `android-17.0.0_r1`。Staged Install 服务于需要经过重启激活的一组 APK/APEX 更新。普通 APK 安装本身也有 Prepare、Scan、Reconcile、Commit 等事务阶段；把所有原子安装都称为 staged，会混淆当前启动内完成的包管理事务与跨重启激活协议。

### 状态与恢复

`PackageInstallerSession` 用 `mSessionReady`、`mSessionApplied`、`mSessionFailed` 等持久化字段表达 staged session 状态。ready 表示重启前验证已经完成，可以进入重启激活；applied 与 failed 是重启后确认的结果。状态写入 Package Installer 的 session 持久化文件，重启时由 `PackageInstallerService` 读取，再把符合条件的顶层 staged session 交给 `StagingManager.restoreSessions()`。

`commit()` 也不是直接跳到重启恢复。session 需要 seal、校验 parent/child 关系、完成通用包验证与 staged 专用验证；包含 APEX 时还要与 apexd 协作。`PackageSessionVerifier.endVerification()` 先把 Package Installer 侧状态写为 ready，再调用 `markStagedSessionReady()` 通知 apexd。这个顺序缩小了“apexd 已准备激活，但 Package Installer 还没有持久化 ready”的不一致窗口。

重启时，apexd 已在 system_server 恢复 session 之前参与 APEX 验证、激活和挂载。`restoreAndApplyStagedSessionIfNeeded()` 随后筛选已提交且尚未终结的 session，`restoreSessions()` 对照 apexd 状态、设备 build fingerprint、checkpoint 能力与 parent/child 完整性，再安装 staged APK 或标记失败。

### session 类型

| 类型 | 重启前 | 重启后 |
| --- | --- | --- |
| APK-only staged | 完成通用验证与 staged 冲突检查 | 通过包管理安装事务应用 APK，成功后标记 applied |
| APEX-only staged | 额外向 apexd 提交并验证 APEX | early boot 激活 APEX，system_server 核对状态并在启动成功后确认 |
| mixed / multi-package staged | parent 统一提交，child 的 staged 与 rollback 属性必须一致 | 任一关键 child 失败会让整组按失败路径处理 |

“APK-in-APEX”表示 APEX 载荷中的 APK 模块，不等于 Package Installer 状态机里自动生成一个嵌套 APK child session。分析时应区分 APEX 容器内容与 multi-package parent/child 关系。

### 原子性与 checkpoint

Staged Install 的原子性来自持久化 session 状态、apexd 激活协议、multi-package 组语义以及可用时的文件系统 checkpoint。`StorageManager.startCheckpoint(2)` 通过 vold 建立文件系统回退边界；apexd 管理 APEX session，它不是 checkpoint 的所有者。设备不支持 checkpoint 时，系统会限制同时活动的 staged 批次，并在包含 APEX 的失败场景使用 apexd revert 与重启等恢复路径。

这里的保证也有边界。checkpoint、APEX revert 和 RollbackManager 的应用数据快照各管一部分状态，不能简化为数据库事务式的“任何时刻断电都自动恢复所有外部副作用”。应用数据迁移、设备厂商组件和安装器自身的网络下载都需要各自的失败处理。

stage 目录常见于 `/data/app-staging/session_<id>/`，但位置由 session volume 与 `buildSessionDir()` 等实现决定；它不是跨设备协议，也不能从目录是否可见推导 session 状态。Package Installer session 只在本机持久化。提纲里的跨设备同步、分发集群协作和网络中断恢复不属于 Android 17 `StagingManager` 的职责，安装器或设备管理系统需要在平台接口之外实现它们。

### 排障入口

1. `PackageInstallerSession` 未到 ready 时，检查 seal、签名、空间、parent/child 属性、staged 冲突和 APEX 验证结果。
2. ready 后重启未 applied 时，对照 Package Installer 与 apexd session 状态，检查 build fingerprint、checkpoint 和 `restoreSessions` 日志。
3. mixed session 失败时，确认失败发生在 APEX early boot、system_server 恢复、APK 安装还是 boot-complete 成功确认阶段。
4. 性能测量应分为重启前验证、early boot 激活、system_server 恢复与 APK/ART 处理几个窗口，避免只报一个不可比较的安装总耗时。

## 源码与文档

- [AOSP `PackageInstallerSession.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerSession.java)
- [AOSP `PackageSessionVerifier.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageSessionVerifier.java)
- [AOSP `PackageInstallerService.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerService.java)
- [AOSP `StagingManager.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/StagingManager.java)
- [Android 官方 APEX 说明](https://source.android.com/docs/core/ota/apex)
