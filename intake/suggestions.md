
## [Task9 Deep Review] ch15 Android 性能优化研究方法论 — 2026-06-27
- **类型**：版本差异覆盖
- **位置**：3.2 工具版本演进与兼容性 > Android 8 工具选型部分
- **问题**：Systrace 使用方法缺少明确的 Android 8 版本命令参数限制说明
- **建议**：补充说明 Android 8 下 Systrace 的具体参数限制（如缓冲区大小限制、不支持的功能等），与其他版本的差异点

## [Task9 Deep Review] 15 Android 性能优化研究方法论 - 2026-06-27
- **类型**:源码准确性
- **位置**:Line 204-210 (ADB 命令引用)
- **问题**:ADB 命令缺少版本限定说明,部分命令在不同 Android 版本中行为有差异
- **建议**:为每个 ADB 命令添加版本限定条件,例如 `adb shell dumpsys meminfo` 在 Android 8+ 中的输出格式变化,`adb shell top` 在 Android 9+ 中的进程分组特性等

## [Task9 Idle Audit] 15 Android 性能优化研究方法论 - 2026-06-27
- **类型**:版本差异覆盖
- **位置**:Line 233 (Perfetto 版本可用性描述)
- **问题**:"Android 9(API 28)起 Perfetto 可用"的描述需要官方文档验证准确性
- **建议**:核实 Perfetto 准确的引入版本,并补充 Android 12+ 中 Perfetto 新特性的说明

## [Task2B Lite 已修复] ch15 方法论 - 2026-06-27
- P1 Perfetto 版本描述:已修正为 Android 9 traced 入 system image 但非 Pixel 需手动 enable,Android 11+ 默认启用
- P2 ADB 命令版本限定:已为 dumpsys meminfo / top / batterystats 补版本说明
- 章节 src/ch15-methodology.md 已回 ready-for-review,待 Task6/Task9 复审


## [Task9 Deep Review] ch15 Android 性能优化研究方法论 - 2026-06-27

- **类型**:源码准确性
- **位置**:3.2.2 Android 9 (API 28) - Perfetto 启用说明
- **问题**:描述"Android 9 手动启用 Perfetto traced"不够准确,Android 9 中 Perfetto 还不完整,更常用的是 systrace
- **建议**:修正为"Android 9 Perfetto 功能有限,仍推荐使用 Systrace 作为主要 tracing 工具"

## [Task9 Deep Review] ch15 Android 性能优化研究方法论 - 2026-06-27

- **类型**:源码准确性
- **位置**:3.2.4 Android 14 (API 34) - traced 命令参数
- **问题**:traced 命令在 Android 14 中不支持 -b 16384 参数
- **建议**:修正为"Android 14 traced 使用默认缓冲区大小,可通过其他参数优化"

## [Task9 Deep Review] ch15 Android 性能优化研究方法论 - 2026-06-27

- **类型**:版本差异
- **位置**:3.2 工具版本演进与兼容性
- **问题**:Android 8-9 的工具选型描述过于简化,实际存在更多兼容性问题
- **建议**:补充说明 Android 8-9 中的兼容性挑战和实际推荐方案

## [Task9 Deep Review] ch15 Android 性能优化研究方法论 — 2026-06-27

- **类型**：版本差异
- **位置**：工具选择的具体策略 - Android 14-17
- **问题**：描述"StatsD 网络指标聚合"在 Android 14-17 中实现方式有变化
- **建议**：更新 StatsD 的具体使用方法和版本差异

## [Task9 Idle Audit] ch15 Android 性能优化研究方法论 — 2026-06-27

- **类型**：版本差异覆盖
- **位置**：3.2.1 Android 9+ 工具演进
- **问题**：缺少 Android 10 中间状态说明，Perfetto 从 Android 9 到 Android 11+ 的渐进过程描述不完整
- **建议**：补充 Android 10 中 Perfetto 的可用性和限制说明，说明其与 Android 9 和 Android 11+ 的差异


## [Task14 参考书扫描] 20.18 Native 堆栈回溯与符号化机制 — 2026-06-27
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - ELF 文件与 readelf & objdump ：了解 ELF 格式与解析工具.md]
- **建议补充**：补充 readelf/objdump 工具速查命令表（-h/-l/-S/-s/-d/-r 与 -t/-h/-d/-T/-p 参数说明），当前 ch20.18 侧重 unwinding/symbolication 原理但缺少工具实操速查
- **参考书覆盖深度**：概述（仅基础格式介绍，不含高级技巧）

## [Task14 参考书扫描] 26.2 Crash 上报体系搭建 — 2026-06-27
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - Java Crash 分析与监控原理.md]
- **建议补充**：补充 Crash 监控系统客户端架构流程参考（启动→设置全局处理器→运行时捕获→信息收集→预处理→上传→后台分析），以及监控性能开销量化指标（CPU/内存/网络/存储）与优化策略（采样控制、异步上报、批量上传）
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] 20.2 Java Crash 治理 — 2026-06-27
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - Java Crash 分析与监控原理.md]
- **建议补充**：补充 ART 源码级异常处理流程细节（Thread::SetException 标记、tlsPtr_.exception 存储、HandleUncaughtExceptions 清除与分发链路），当前 ch20.2 已 finalized 但未深入 ART 源码级实现
- **参考书覆盖深度**：中等

## [Task2A Gap Mining] 已检查方向记录 — 2026-06-27

**本轮结论**: 0 个合格缺口（所有候选 < 14 分）。全书 495 小节覆盖已趋成熟。

**已检查方向**（下次跳过）：

### AOSP 核心服务/框架缺口
- ✅ Intent Resolution / Broadcast 调度性能 → 1.8 AMS 已覆盖 BroadcastQueueImpl 架构、按进程队列、ANR 超时、cached state 排队 (评分 12)
- ✅ TelephonyManager / RIL 性能 → 生态太小，开发者侧无法调优
- ✅ NotificationManagerService → 8.14 + 9.6 已覆盖通知管线性能和 ANR
- ✅ BackupManagerService → 运行时性能影响极小 (评分 8)
- ✅ ClipboardService / DragAndDrop / PrintManager → 过于边缘
- ✅ WallpaperService / DreamService → 过于边缘
- ✅ AppSearch / SearchManager → 过于边缘

### 系统级/内核层缺口
- ✅ SELinux/SEPolicy 性能开销 → 开发者无法调优，系统级话题 (评分 11)
- ✅ File-Based Encryption (FBE/fscrypt) I/O → 开发者侧优化空间有限，6.1/6.2 已提及 (评分 13)
- ✅ Android Virtualization Framework (AVF) → 仍在发展期，素材不足 (评分 11)
- ✅ Android Verified Boot 性能 → 主要影响开机耗时，16.7 已覆盖系统启动优化
- ✅ KASLR 性能 → 内核安全特性，非开发者可调优

### 跨平台/设备形态缺口
- ✅ Wear OS 性能优化 → 本书定位通用 Android 性能，Wear OS 生态太小 (评分 12)
- ✅ Android TV / Android Things → 生态太小
- ✅ Android XR → 18.22 已覆盖空间 UI 渲染性能

### 开发模式/架构缺口
- ✅ MVVM vs MVI 性能 → 架构模式差异对性能影响不构成独立小节
- ✅ Handler vs Coroutine 性能 → 8.6 + 8.17 已覆盖
- ✅ KMP (Kotlin Multiplatform) 性能 → 过于新，素材不足
- ✅ Compose Multiplatform 性能 → 同上

### 结论
全书 5 个 Part、18+ Chapters、495 小节的覆盖结构已经高度完整。剩余缺口集中在：
1. 已有小节的内容深化（由 Task 2B / Task 9 负责）
2. Android 18+ 内容（超出 AIW 范围边界）
3. 开发者侧无法直接调优的系统级/内核层话题
