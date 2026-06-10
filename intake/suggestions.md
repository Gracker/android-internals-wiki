## [Task9 Deep Review] 14.2 Simpleperf — 2026-06-10 19:20

- **类型**：源码准确性
- **位置**：14.2.1 简介与用途
- **问题**：源码路径错误，引用 `system/extras/simpleperf/main.cpp` 但实际路径为 `system/extras/simpleperf/simpleperf/main.cpp`
- **建议**：修正AOSP源码引用路径为正确路径

- **类型**：交叉引用一致性
- **位置**：14.2.1 简介与用途
- **问题**：提到"与 Linux perf 的关系"但未引用相关章节
- **建议**：添加对章节14.1或其他Linux perf相关章节的引用说明

- **类型**：数据缺失
- **位置**：14.2.3 基本使用方法
- **问题**：采样开销数据（2-5%）没有具体测试条件说明
- **建议**：提供测试环境、设备型号、Android版本等具体测试条件

- **类型**：数据缺失
- **位置**：14.2.6 数据分析与解读
- **问题**：性能基准测试章节缺少IPC和cache-miss率的具体基线值
- **建议**：提供典型应用的IPC和cache-miss率基准数据

- **类型**：原理链完整性
- **位置**：14.2.5 Perfetto集成
- **问题**：未说明Perfetto如何识别simpleperf事件的原理
- **建议**：补充Perfetto linux.perf data source的工作原理

- **类型**：原理链完整性
- **位置**：14.2.5 符号解析机制
- **问题**：未说明不同符号源的优先级冲突处理机制
- **建议**：解释ELF符号表与DWARF符号的冲突解析规则

- **类型**：版本差异覆盖
- **位置**：版本兼容性概览表格
- **问题**：ARM64 PAC支持版本标注不准确
- **建议**：明确ARM64 PAC支持的最低Android版本

- **类型**：知识盲区
- **位置**：14.2.8 常见问题与解决方案
- **问题**：缺少与Android Studio Profiler对比
- **建议**：添加与Android Studio Profiler的优缺点对比

- **类型**：数据缺失
- **位置**：符号解析机制章节
- **问题**：不同符号解析方法的成功率数据缺失
- **建议**：提供ELF vs DWARF vs JIT符号解析的成功率对比

- **类型**：数据缺失
- **位置**：系统级采样章节
- **问题**：LOST事件与-m参数关系的量化数据缺失
- **建议**：提供不同-m值下的LOST事件减少比例数据

- **类型**：源码准确性
- **位置**：14.2.6 数据分析与解读 - 调用栈重建原理
- **问题**：JIT符号文件路径写为 `/tmp/perf-<pid>.map`，实际为 `/data/local/tmp/perf-<pid>.map`
- **建议**：修正符号文件路径并添加验证方法

- **类型**：原理链完整性
- **位置**：14.2.6 数据分析与解读 - 调用栈重建原理
- **问题**：未解释为何默认启用DWARF而非FP回溯
- **建议**：解释-g默认使用DWARF的设计考虑和性能权衡

- **类型**：源码准确性
- **位置**：14.2.6 数据分析与解读
- **问题**：声称-g等价于--call-graph fp，但实际等价于--call-graph dwarf
- **建议**：修正调用栈重建机制描述，引用源码证据

## [Task2A Gap Mining] 本轮已检查方向 — 2026-06-10 20:04

本轮知识缺口挖掘已覆盖以下方向，均未产出评分 ≥ 14 的候选：

### 1. source-index.json 高质量未映射素材
- 结果：0 篇 quality ≥ 16 且 mapped_chapters 为空的素材
- 结论：所有高质量素材已映射到现有章节

### 2. AOSP frameworks/ 服务覆盖对比
- 已覆盖：AMS(1.8)、PMS(1.9)、WMS(2.12)、SF(2.6)、InputDispatcher(3.x)、Lmkd(4.4)、SensorService(5.15)、vold(6.6)、netd(12.6)、ConnectivityService(12.5)、AudioFlinger(1.16)、statsd(14.17)、NotificationManagerService(9.6)、InputMethodManagerService(3.11)、AccessibilityManagerService(7.19)
- 未覆盖但有评估：TelephonyManager/Phone（非性能核心）、ClipboardService（非性能核心）、DevicePolicyManager（非性能核心）、RoleManager（非性能核心）
- 结论：未覆盖的 AOSP 服务与全书性能主题关联度不足，评分均 < 14

### 3. AOSP system/ 核心组件
- 已覆盖：init(1.2)、vold(6.6)、netd(12.6)、lmkd(4.4)、tombstoned(20.3)、installd(1.9)、surfaceflinger(2.x)、audioserver(1.16)
- 未覆盖评估：storaged（素材 2 分，总评 9）、installd dex2oat 队列（部分已覆盖于 1.9）
- 结论：storaged 读者需求度低，素材少

### 4. Android 17 行为变更覆盖
- 已覆盖：Edge-to-Edge(2.26)、FGS类型(5.17)、Excessive CPU Kill(25.12)、allow-while-idle(25.20)、background audio(25.17)、ECH(24.18)、streaming(24.16)、Keystore quota(20.16)、Tare(11.8)、Native DCL(20.15)、Developer Verification(1.21)、16KB Page(4.7)
- 未覆盖评估：StrictMode safer intent（已在 14.23 中）、Health Connect/Content Capture/AutoFill（非性能核心）
- 结论：Android 17 所有性能相关变更均已有对应章节

### 5. DeepResearch 近期产出映射（2026-06-08 至 2026-06-10）
- simpleperf call stack unwinding → 14.2（review 中）
- ondevice LLM runtime → 5.11/5.13/5.14（均已定稿）
- input queue iq/oq/wq → 3.7/3.10（均已定稿）
- LRU lock optimization → 1.14（已定稿）
- binder transaction queue → 1.4/20.17（均已定稿或有内容）
- GPU Vulkan loader → 2.10/18.9（均已定稿）
- cloud compilation SDM/DM → 21.11（ready-for-review）
- ART GC fragmentation → 4.8（已定稿）
- SF transaction queue lockless → 2.22（已定稿）
- codec2 tunneled ABR → 18.23（ready-for-review）
- 结论：所有 DeepResearch 均映射到现有章节

### 6. 存储子系统深度（ch6 最薄章节，仅 7 节）
- 候选：f2fs 深度调优 → 素材 4 + 相关性 4 + 需求 3 + 时效 3 = 14（边界）
- 候选：UFS 硬件性能 → 素材 3 + 相关性 3 + 需求 2 + 时效 3 = 11
- 候选：dm-verity 性能 → 素材 2 + 相关性 2 + 需求 2 + 时效 2 = 8
- 结论：f2fs 深度调优恰好踩线 14 分但素材为内核文档为主，实战素材不足；其余均不达标

### 7. Clippings 参考书对比
- 《稳定性》15 篇已全部映射到 ch20
- 《性能优化》16 篇已全部映射到 ch21-25
- 《线上疑难》59 篇已全部映射到 ch26 及其他章节
- 候选：ASM 字节码插桩 → 已覆盖于 14.13 Hook 基础设施
- 候选：缓存优化（冷热端分离）→ 已覆盖于 5.18 CPU Cache 友好代码
- 结论：参考书知识点均已覆盖

### 总结论
全书 422 节、288 finalized、75 ready-for-review。连续多轮缺口挖掘未产出合格候选，知识库已接近全面饱和状态。建议下一轮将重心转向：
1. 已 ready-for-review 的 75 节进入 Task6/Review 管线加速定稿
2. 对已定稿但时间较早的章节做 Android 17 源码交叉验证
3. f2fs 深度调优可作为储备选题，待素材积累后重新评估
