## [Task9 Deep Review] 19.22 存储 Benchmark（AndroBench、A1 SD Bench） — 2026-07-16
- **类型**：数据缺失
- **位置**：测试报告模板部分
- **问题**：建议补充具体的 Android 17 下的测试路径权限验证案例
- **建议**：在现有测试报告模板基础上，增加 Android 17 (API 37) 下的特定测试路径验证说明，包括 scoped storage 授权机制、App 私有目录权限检查、MediaStore 访问权限等具体场景的验证方法
## [Task14 参考书扫描] ch20 稳定性治理 — 2026-07-16
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 44.md]
- **建议补充**：Breakpad 在 x86 模拟器上 Clang 编译导致 Crash 日志抓取异常的问题及解决方案（降级 NDK r16b + GCC 工具链）。Minidump 日志解析完整工作流：dump_syms 符号表提取 → 目录结构构建 → minidump_stackwalk 解析 → addr2line 回退方案
- **参考书覆盖深度**：深入（含完整编译配置和命令行操作）

## [Task14 参考书扫描] ch20 稳定性治理 — 2026-07-16
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 44.md]
- **建议补充**：PLT Hook 与 Inline Hook 方案对比（稳定性 vs 灵活性权衡），ndk_dlsym 绕过 Classloader-Namespace Restriction 机制获取 Native 函数符号的方法，Name Mangling 反解技术（c++filt 工具）
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] ch20 稳定性治理 — 2026-07-16
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 44.md]
- **建议补充**：FinalizerWatchdog 系统防护机制说明及系统 Framework 异常的反射/代理绕过思路（如 Toast 异常处理），Memory Allocation Trace 监控模块设计思路（大对象分配监控 + 调用栈分析）
- **参考书覆盖深度**：概述

## [Task14 参考书扫描] ch26 可观测性 — 2026-07-16
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 45.md]
- **建议补充**：ProcessCpuTracker 实现原理——基于 /proc 伪文件系统（/proc/stat、/proc/loadavg、/proc/[pid]/stat、/proc/[pid]/task）的 CPU 数据采集。/proc 文件特性说明：零大小虚拟文件、轮询采集、内核版本兼容处理
- **参考书覆盖深度**：深入（含数据源详解和实践代码）

## [Task14 参考书扫描] ch09 ANR 监控与分析 — 2026-07-16
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 45.md]
- **建议补充**：ANR 日志 CPU 数据分析方法论——System TOTAL 五项指标解读（user/kernel/iowait/irq/idle）、Load Average 与 CPU Core 核数关系、线程 R/S 状态含义（TASK_INTERRUPTIBLE 自愿让出 CPU）。含完整 I/O 写入瓶颈复现案例（12MB 文件写入 → iowait 9.2% + page faults 4965）
- **参考书覆盖深度**：深入（含完整案例和数据对照）

## [Task14 参考书扫描] ch26 可观测性 — 2026-07-16
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 45.md]
- **建议补充**：Page fault 三种类型详解（minor/major/invalid）及 Android 平台特殊性——Android 默认无 Swap 分区，major page fault 主要来自 mmap 文件的磁盘载入。Page fault 计数 × 4KB 估算内存分配量的实践方法
- **参考书覆盖深度**：深入

## [Task14 参考书扫描] ch26 可观测性 — 2026-07-16
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 46.md]
- **建议补充**：Facebook Profilo 框架线上 atrace 日志收集方案——通过 PLT Hook 拦截 write() 到 trace_marker fd 的写入，配合 atrace_enabled_tags 全位掩码（0xFFFFFFFF）启用所有 category。trace_marker 机制说明：ftrace 提供的用户态事件写入接口，产生系统调用（用户态→内核态切换开销）
- **参考书覆盖深度**：深入（含源码级实现分析）

## [Task14 参考书扫描] ch26 可观测性 — 2026-07-16
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 46.md]
- **建议补充**：atrace 日志中 traceBegin/traceEnd 匹配方法——通过 CPU 编号 + task_pid 对应嵌套的 B/E 事件对。线程创建监控方案：PLT Hook pthread_create，但需注意 Attached（托管）与 Unattached（非托管）线程的区分限制
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] ch26 可观测性 — 2026-07-16
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 46.md]
- **建议补充**：Crash 状态下获取 Java 线程堆栈的两种方案：① ThreadList::ForEach 接口间接遍历 ② Profilo Unwinder 机制模拟 StackVisitor 逻辑。MonitorInfo 构造方法用于分析 Object 锁等待线程列表（需计算地址偏移量）
- **参考书覆盖深度**：中等


## [Task2A R132] 已检查方向 — 2026-07-16 07:05
- ART 锁膨胀 ThinLock/FatLock → §1.14 已深入覆盖（425L finalized）
- Huge Pages for Code → 非 Android 系统内部主题
- LBR 分支概率/perf 精确计时 → x86 微架构，Android ARM 不适用
- GWP-ASan 可恢复机制 → §19.24/§20.23 已覆盖/排队
- daily-info 技术文章回流 → 非 Android internals（x86/Linux 通用）

## [Task6 Audit] 1.15 JNI/NDK 性能优化 — 2026-07-16
- **类型**：需确认
- **位置**：frontmatter sources + 正文多处 AOSP 引用 + 参考资料 section
- **问题**：源码路径版本基线仍标注 android-16.0.0_r1（涉及 Binder.java、Parcel.java、SystemProperties.java、Trace.java、trace.h 等所有 aosp 类型 sources），项目基准要求 android-17.0.0_r1
- **建议**：由 Task 9 重新核对 android-17.0.0_r1 中这些文件路径和 API 签名是否有变化，确认后由 Task 2B 统一更新版本标注
- **review 日志**：logs/review/2026-07-16-09-audit.md

## [Task9 Deep Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-07-16
- **类型**：版本差异覆盖
- **位置**：分代 CMC gating 条件说明部分
- **问题**：Android 17分代 CMC gating 条件说明，虽然提到了需要满足多个 AND 条件，但未明确说明 device_config 与其他 gating 条件的组合关系
- **建议**：补充 device_config 检查的实际落地路径，明确 `persist.device_config.runtime_native_boot.use_generational_gc` 与其他条件的关系，增加验证命令示例

## [Task9 Deep Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-07-16
- **类型**：知识盲区
- **位置**：分代 GC 与 MarkCompact 章节
- **问题**：未涵盖 Task2B backlog 中提到的 YoungMarkCompact 与 MarkCompact 关系细节
- **建议**：补充 YoungMarkCompact 是 MarkCompact 的 thin wrapper 这一关键关系，说明 CMC 实际由 userfaultfd + SIGBUS 构成零 STW 搬迁机制


## [Task9 Deep Review] 1.15 JNI/NDK 性能优化 — 2026-07-16
- **类型**：数据缺失
- **位置**：性能基准数据章节
- **问题**：2016年angler-userdebug基准数据直接引用为官方参考值，但缺乏更近期的设备测试数据对比
- **建议**：补充近2-3年的典型设备测试数据，或明确标注数据时效性和适用边界

## [Task9 Deep Review] 1.15 JNI/NDK 性能优化 — 2026-07-16
- **类型**：知识盲区
- **位置**：现代硬件架构影响章节
- **问题**：没有覆盖现代ARM架构（如ARMv9、Neon指令集）对JNI性能的影响
- **建议**：补充现代ARM架构特性对JNI transition优化的相关说明
- **参考书覆盖深度**：中等

## [Task9 Deep Review] 1.15 JNI/NDK 性能优化 — 2026-07-16
- **类型**：知识盲区
- **位置**：编译优化章节
- **问题**：没有提到JIT/AOT编译对JNI调用热路径的影响
- **建议**：补充JIT/AOT编译器对JNI边界调用的优化策略和性能影响
- **参考书覆盖深度**：中等


## [Task9 Deep Review] 1.15 JNI/NDK 性能优化 — 2026-07-16 14:25
- **类型**：版本差异覆盖
- **位置**：版本演进表格
- **问题**：frontmatter `applicable_versions` 标注"Android 8 (API 26) - Android 17 (API 37)"，但版本演进表格只到 Android 16 (API 36)，缺少 Android 17 (API 37) 行。
- **建议**：补充 Android 17 (API 37) 在 JNI/NDK 方向的官方变更（如有），或在表格末尾追加"Android 17 (API 37)：本轮核对未发现对 public JNI annotation 的新语义变化；16KB page size 已强制要求 targeting Android 15+ 的 64 位应用支持；如新增内容需另行调研"。

## [Task9 Deep Review] 1.15 JNI/NDK 性能优化 — 2026-07-16 14:25
- **类型**：数据缺失
- **位置**：16KB page size 收益数据段落
- **问题**：列出的收益百分比（app launch time 平均下降 3.16%、部分应用能到 30%；启动期功耗下降 4.56%；camera hot start 快 4.48%；cold start 快 6.60%；system boot time 提升约 8%）未在章节中给出直接来源链接。
- **建议**：补充 developer.android.com/guide/practices/page-sizes 中具体段落的锚链接，或在 sources 中追加 data sheet 引用。
