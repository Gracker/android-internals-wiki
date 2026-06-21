## [Task9 Deep Review] 11.4 案例集 — 2026-06-20

### P2 建议改进：

- **类型**：版本差异覆盖
- **位置**：JobScheduler throttling 机制
- **问题**：11.4.7 提到的三层节流防线在 Android 14-17 有重要变化未区分：Android 14 引入 CountQuotaTracker、Android 15 强化 mEJLimitsMs[] 配置、Android 16+ 完全迁移到 APEX。影响开发者准确理解和适配不同版本的限流策略。
- **建议**：按 Android 14/15/16/17 分节说明各版本的关键变化，特别是 QuotaController 配置差异和 APEX 路径稳定化时间点。

- **类型**：版本差异覆盖  
- **位置**：Location Mode 权限机制
- **问题**：文中提到 Android 12+ 开启后台节流（30min），但 Android 13 新增 READ_LOCATION_BYPASS_ALLOWLIST、Android 14 收紧 LOCATION_BYPASS，这些关键权限和策略演进未覆盖。
- **建议**：补充 Android 13-14 的 Location 权限沙盒演进，说明 OEM 定制点和应用适配策略差异。

- **类型**：原理链完整性
- **位置**：FGS 超时机制引入背景
- **问题**：11.4.1 描述了 Android 14-17 的 FGS 超时机制，但未解释为什么需要引入时间限制机制的根本原因。
- **建议**：补充 FGS 超时机制的引入背景：如无限运行导致的内存泄漏、系统资源竞争、用户投诉等业务场景，帮助读者理解设计动机。

### P3 锦上添花建议：

- **类型**：知识盲区
- **位置**：Radio 状态机与 Thermal 协同
- **问题**：未讨论 Radio 状态与 Thermal Status 协同的具体场景（如高温状态下 Radio 是否自动降频）。
- **建议**：增加 "Radio 状态机与热节流协同" 小节，分析不同 Thermal 等级对 Radio 状态的限制规则。
## [2026-06-20 21:00] Task2A 缺口挖掘 — 第 84 轮

### 本轮检查方向（6 个）
1. 今日 daily-info：ML 内存泄漏检测论文 — 评分 9/20（学术前沿，工程实战素材不足，全书定位不匹配）
2. Android 17 PowerStats 重构（PowerAttributor/PowerStatsProcessor）— 评分 17/20 但已在 11.1 章节由 Task2B 修复覆盖，非新缺口
3. Perfetto Remote Trace Processor 架构 — 评分 12/20，已在 queue 中 pending 供 13.7 章节补充，非新缺口
4. source-index.json 未映射素材 — 9 篇 DeepResearch 均已注入对应章节
5. 近期 research-feeds — 最新为 2026-04 月，全部已映射
6. AOSP frameworks/base 未覆盖服务 — 已在历轮 83+ 次扫描中穷尽

### 结论
- 最高新缺口评分：9/20（远低于 14 分门槛）
- 连续无合格缺口轮次：84 轮
- 全书 443 节（307 finalized, 94 ready-for-review, 3 draft 有实质内容）
- **知识库高度饱和，本轮跳过**


## [Task9 Deep Review] 26.1 App 可观测性架构设计 — 闲时抽检 — 2026-06-21

### P2 建议改进：

- **类型**：源码引用准确性
- **位置**：可观测性架构技术实现
- **问题**：章节提到 'RingBuffer' 和 'mmap' 等技术实现，但未提供具体的 AOSP 源码路径。引用的技术实现细节缺乏源头验证，影响架构设计的可信度。
- **建议**：补充 frameworks/native/services/surfaceflinger/ 中的 RingBuffer 实现和内存映射相关代码，以及相关线程管理类的源码路径。

- **类型**：源码引用准确性
- **位置**：线程模型和监控架构
- **问题**：提到 'Main thread' 和 'RenderThread' 等线程概念，但未引用具体的 AOSP 实现类。技术概念缺乏源码支撑，影响读者理解系统机制。
- **建议**：补充 android/view/ViewRootImpl.java 中的主线程管理、frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp 中的 RenderThread 实现。

- **类型**：版本差异覆盖
- **位置**：Android 可观测性系统演进
- **问题**：章节标注 applicable_versions: Android 10 (API 29) - Android 17 (API 37)，但未详细说明 Android 12 引入的 StrictMode 性能监控、Android 14 中的 Jetpack WindowManager 对可观测性的影响等重要版本变化。
- **建议**：补充 Android 12-17 的可观测性系统关键特性演进，特别是 StrictMode 机制完善、Jetpack 组件监控能力增强、隐私沙盒对监控权限的影响等。

## [Task9 Deep Review] 14.2 Simpleperf — 2026-06-21

### P2 建议改进：

- **类型**：版本差异覆盖
- **位置**：API 24-33 mmap 记录处理转换
- **问题**：章节未详细说明 Android 7 到 Android 13 的 mmap 记录处理变化细节，包括采样机制、缓冲策略和数据处理流程的演进。
- **建议**：补充 Android 7-13 的 mmap 记录处理变化细节，特别是 Android 12+ 的 mmap 机制优化和格式变化，帮助读者理解不同版本的数据处理差异。

- **类型**：版本差异覆盖
- **位置**：Android 12+ 可分析应用权限模型
- **问题**：章节提到可分析应用但未详细说明权限模型如何从 Android 10 演变到 13+，包括权限申请流程、用户授权机制和系统限制。
- **建议**：补充 Android 12-17 的可分析应用权限模型演进，特别是隐私沙盒对 profiling 权限的影响和适配策略。

- **类型**：数据与案例支撑
- **位置**：性能开销声明
- **问题**：章节中的 CPU 开销百分比（"CPU 占用率增加 3-5%"）缺乏实际基准数据支持，未在不同设备配置下验证。
- **建议**：提供实际设备配置下的基准测试数据，包括不同芯片架构、内存大小和 Android 版本下的开销对比。

- **类型**：数据与案例支撑
- **位置**：内存使用估计
- **问题**：200-500KB mmap 记录头估计未在真实 AI 应用中验证，可能存在实际应用场景下的偏差。
- **建议**：在真实 AI 应用场景中验证内存使用数据，包括大型模型、复杂计算和长时间运行场景下的实际内存开销。

- **类型**：交叉引用一致性
- **位置**：术语使用
- **问题**：章节在不同地方使用 "callgraph" 和 "call stack"，与其他分析章节术语不一致，可能造成读者混淆。
- **建议**：统一术语使用，选择一个标准术语（如 "call stack"）并在全文保持一致，同时在章节开始处定义术语规范。

## [Task6 Review] 14.2 Simpleperf — 2026-06-21

### B类问题
- **类型**：存疑-技术准确性
- **位置**：14.2.5 与 Perfetto 集成段
- **问题**：原文称 perf.data 为 "protobuf 编码"，perf.data 实际基于 Linux perf 二进制格式（header + event records），非 protobuf 序列化。已在正文添加 [存疑] 标签。
- **建议**：Task 9 验证后修正格式描述
- **review 日志**：logs/review/2026-06-21-12-review.md

### L3/L4 观察项（不阻塞，供后续优化参考）
1. **开头段落风格**：当前开头为定义式（"Simpleperf 是 Google 官方维护的..."），writing-guide Type C 建议从"这个工具解决什么问题/没有它会多痛苦"切入。不阻塞本轮，但可在下次回炉时优化。
2. **源码深度与章节定位**：14.2.5/14.2.6 中源码级分析（IPC 三层架构、FP/DWARF 分叉、JITdebugReader 协议等）非常深入，超出 Type C（工具使用篇）的典型深度。内容质量高，但可考虑将最深入的部分拆到附录或独立"源码解析"章节，保持工具章的实用性聚焦。
3. **"适用范围"列表项**：纯名词列表（"Native C/C++ 代码性能分析"等），无描述性说明。SKILL.md 3.4 建议列表项自带信息增量，可补充每项的典型场景。
4. **outline 标记缺失**：本章无 `<!-- outline-start/end -->` 标记，无法做锚点覆盖检查。属结构性问题，留给 Task 2 补充。

## [Task6 Review] 14.2 Simpleperf — 2026-06-21 (revisit)

### B类问题（技术准确性，交 Task 9 验证）

- **类型**：存疑-技术准确性
- **位置**：14.2.4 PMU 硬件事件权限段（line ~224）
- **问题**：`adb shell setprop kernel.perf_event_paranoid 1` — `perf_event_paranoid` 是 sysctl 参数（`/proc/sys/kernel/perf_event_paranoid`），不是 Android system property。`setprop` 设置的是 Android 属性系统（`/system/build.prop` 等），不能直接设置 sysctl。正确方式应为 `adb shell "echo 1 > /proc/sys/kernel/perf_event_paranoid"`（需 root）。
- **建议**：Task 9 验证后修正命令为 sysctl 写法或标注设备差异

- **类型**：存疑-命令语法
- **位置**：14.2.4 过滤选项段（line ~236）
- **问题**：`simpleperf record com.example.*` — 无 `--app` 或 `-p` 目标选择标志，直接使用 glob 模式作为 record 参数。Simpleperf CLI 不接受裸包名 glob 作为 record target，应使用 `--app com.example.app` 或 `-p <pid>` 。
- **建议**：Task 9 验证 simpleperf record 是否支持裸进程名 glob，如不支持则修正为 `--app` 语法

- **类型**：存疑-选项存在性
- **位置**：14.2.4 过滤选项段（line ~239）
- **问题**：`simpleperf record --exclude-pid android.*,system.*` — `--exclude-pid` 选项是否存在需要验证。Simpleperf 常用 record 选项为 `--app`、`-p`、`-t`、`-a`，未见 `--exclude-pid` 的官方文档记录。
- **建议**：Task 9 查阅 simpleperf record --help 确认 `--exclude-pid` 是否存在；如不存在则删除该示例

- **review 日志**：logs/review/2026-06-21-13-review.md

## [Task6 Review] 14.2 Simpleperf — 2026-06-21 14:07
- **类型**：存疑-技术一致性
- **位置**：14.2.4 过滤选项 vs 14.2.5 多进程应用采样
- **问题**：-p 参数语义在三处描述不一致——14.2.4 注释写"只接受数字 PID，不支持进程名或正则"；14.2.5 表格写 `<pid_or_name_regex>` 和"按 PID 或进程名正则"；14.2.5 注释写"也支持进程名正则"。需确认 simpleperf -p 在 android-17.0.0_r1 中的实际行为。
- **建议**：查阅 `simpleperf record --help` 确认 -p 参数语义，统一全文三处描述
- **review 日志**：logs/review/2026-06-21-14-review.md

## [Task6 Review] 14.2 Simpleperf — 2026-06-21 14:07
- **类型**：存疑-源码锚点合规性
- **位置**：14.2.7 mmap/munmap 数据通路：源码级展开
- **问题**：该节源码锚点为 LineageOS/android_system_extras@lineage-23.2（非 AOSP 官方 tag），正文虽标注"android-17.0.0_r1 tag 未公开，未进入 Android 17"，但源码分析结论仍作为正文内容。版本差异表行号引用 [android-16.0.0_r1]。需 Task 9 确认 LineageOS lineage-23.2 与 android-17.0.0_r1 代码一致性。
- **建议**：Task 9 验证源码一致性；若无法确认，mmap 数据通路节结论需降级或增加标注
- **review 日志**：logs/review/2026-06-21-14-review.md

## [Task9 Deep Review] 14.2 Simpleperf — 2026-06-22
- **类型**：数据缺失/版本边界
- **位置**：14.2.7 Simpleperf 与电源 / 热 / 异构调度的交互盲区，厂商 ROM 限制表
- **问题**：MIUI/EMUI/ColorOS/OneUI/Funtouch 限制与绕过方式标注为“未一手验证”，但表格给出了具体系统属性、root、boot image 等操作建议；当前没有厂商文档、设备实验记录或日志支撑。
- **建议**：补充可复现实验记录和系统版本/机型边界；如果无法补齐，一律降级为“待验证观察”或移出正文操作建议区。
