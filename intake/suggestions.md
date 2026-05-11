## [Task9 Deep Review] 20.1 应用稳定性全景 — 2026-05-11
- **类型**：数据缺失
- **位置**：Google Play 阈值数据
- **问题**：文中提到的"全机型不良行为阈值：≥ 1.09%"、"全机型不良行为阈值：≥ 0.47%"等阈值缺乏权威来源引用
- **建议**：补充官方文档链接或Google Play Console的具体技术文档，注明阈值的具体测试条件和统计周期

## [Task9 Deep Review] 20.1 应用稳定性全景 — 2026-05-11
- **类型**：数据缺失
- **位置**：崩溃治理的ROI数据
- **问题**：缺少防御性编程vs根因修复的投入产出比数据，无法评估不同策略的实际效果
- **建议**：补充行业内典型应用的防御性编程成本数据、修复后的复发率对比、以及长期维护成本分析

## [Task9 Deep Review] 20.1 应用稳定性全景 — 2026-05-11
- **类型**：数据缺失
- **位置**：第三方库崩溃占比
- **问题**："第三方库的崩溃占比可达20-30%"的占比数据需要验证性来源
- **建议**：引用行业报告或大型应用的实际统计数据，注明统计样本和应用类型

## [Task9 Deep Review] 20.2 Java Crash 治理 — 2026-05-11
- **类型**：数据缺失
- **位置**：Top Crash分布数据
- **问题**："Top 5类型覆盖80%以上的Java Crash"缺乏具体数据来源
- **建议**：补充Firebase Crashlytics或Google Play的实际统计数据，注明统计周期和样本量

## [Task9 Deep Review] 20.2 Java Crash 治理 — 2026-05-11
- **类型**：数据缺失
- **位置**：堆栈捕获性能开销
- **问题**："256帧限制"的性能影响数据不足，缺乏具体的性能基准测试
- **建议**：补充不同设备配置下堆栈捕获的耗时数据，以及对用户体验的实际影响评估

## [Task9 Deep Review] 20.2 Java Crash 治理 — 2026-05-11
- **类型**：版本差异
- **位置**：UncaughtHandler API演进
- **问题**：Android 13+的UncaughtExceptionHandler行为有变化但未说明
- **建议**：补充Android 13+中Thread.setDefaultUncaughtExceptionHandler()的新特性和限制说明

## [Task9 Deep Review] 2.10 GPU 渲染深入 — 2026-05-11
- **类型**：数据缺失
- **位置**：Vulkan vs OpenGL性能差距
- **问题**："10-50μs vs 1-5μs"缺乏基准测试数据来源
- **建议**：引用ANGLE官方性能报告或社区基准测试，注明测试设备和场景

## [Task9 Deep Review] 2.10 GPU 渲染深入 — 2026-05-11
- **类型**：数据缺失
- **位置**：ANGLE性能开销
- **问题**："2-5%、5-10%、10-20%"区间数据缺乏具体测试条件说明
- **建议**：补充不同场景下的具体测试数据，包括设备类型、分辨率、复杂度等参数

## [Task9 Deep Review] 2.10 GPU 渲染深入 — 2026-05-11
- **类型**：数据缺失
- **位置**：GPU Headroom使用效果
- **问题**：缺少实际应用中的性能提升案例
- **建议**：补充成功应用GPU Headroom API的实际案例，包括性能提升百分比和优化策略

## [Task9 Deep Review] 2.10 GPU 渲染深入 — 2026-05-11
- **类型**：数据缺失
- **位置**：Host Image Copy收益
- **问题**："峰值内存更低、提交抖动更小"缺乏量化数据
- **建议**：补充具体设备的内存使用对比数据和性能改善案例

## [Task9 Deep Review] 2.10 GPU 渲染深入 — 2026-05-11
- **类型**：源码准确性
- **位置**：VkShaderModuleCreateInfo使用
- **问题**：代码示例中spirvCode的处理方式过于简化，未考虑endianness等问题
- **建议**：补充完整的SPIR-V加载代码，包括字节序处理、验证和错误处理机制

## [Task9 Deep Review] 2.10 GPU 渲染深入 — 2026-05-11
- **类型**：原理完整性
- **位置**：GPU Headroom计算机制
- **问题**：未解释getGpuHeadroom()的具体算法和影响因素
- **建议**：补充GPU余量计算的实现细节，包括温度、频率、功耗等影响因素的作用机制

## [Task14 参考书扫描] 14.13 Hook 基础设施 — 2026-05-11
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - ASM 与字节码插桩：改写字节码的"神器".md]
- **建议补充**：ASM Tree API 的 ClassNode/MethodNode/FieldNode 操作模型详解，字节码指令集（InsnList/AbstractInsnNode）与 Java 代码的映射关系。现有 ch14.13 已有 9 处 ASM 提及但未展开 Tree API 细节。
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] 14.13 Hook 基础设施 — 2026-05-11
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - Android.bp 文件与符号表：如何才能找到函数符号？.md]
- **建议补充**：Android.bp 语法与模块类型（cc_library/cc_binary）详解；通过 Android.bp 定位源文件→so 库的映射关系；C/C++ 符号（Symbol）概念与 name mangling 机制；readelf -s 查看符号表。现有 ch14.13 未覆盖 Android.bp 与符号定位的前置知识。
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] 14.13 Hook 基础设施 — 2026-05-11
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - ELF 文件与 readelf & objdump ：了解 ELF 格式与解析工具.md]
- **建议补充**：ELF 文件格式基础（ELF Header/Program Header/Section Header 结构）；ELF 连接视图 vs 运行视图的区别；.so 文件与 ELF 的关系；readelf 常用命令（-h/-S/-s/-d/-r）；objdump 反汇编命令。现有 ch14.13 未系统覆盖 ELF 格式前置知识。
- **参考书覆盖深度**：概述

## [Task14 参考书扫描] 20.2 Java Crash 治理 — 2026-05-11
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - Java Crash 监控：实现自定义 Crash 处理器.md]
- **建议补充**：ART 虚拟机异常处理全流程源码路径（Thread::SetException → HandleUncaughtExceptions → dispatchUncaughtException）；UncaughtExceptionHandler 注册时机与优先级链。AIW 20.2 已覆盖但缺少 Native 层源码级路径的详细追踪。
- **参考书覆盖深度**：深入（含 AOSP 源码引用）

## [Task14 参考书扫描] 20.2 Java Crash 治理 — 2026-05-11
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - Java 堆栈：深入了解 Throwable.md]
- **建议补充**：Throwable 内部堆栈填充机制（fillInStackTrace 源码分析）；堆栈裁剪（stackTrace trimming）与性能优化；堆栈信息中隐藏帧（hidden frames）的处理。AIW 20.2 已有基础覆盖但缺少 fillInStackTrace 的源码级分析。
- **参考书覆盖深度**：深入（含 AOSP 源码引用）

## [Task9 Deep Review] 1.6 Android 版本演进中的架构变化 — 2026-05-11
- **类型**：数据缺失
- **位置**：L367-L372 16KB page size 性能数据
- **问题**：官方 page-sizes 文档给出的 system boot 数据为 improved by 8%（approximately 950 milliseconds）on average；正文写“约 0.8 秒（8%）”，数值与官方口径不完全一致，且未保留“initial testing / actual devices may differ”的条件。
- **建议**：把系统开机时间改为“约 950ms（8%）”，并补一句这些数字来自 Google 初始测试，实际设备可能不同。

## [Task9 Deep Review] 1.9 Package Manager Service 与应用安装性能 — 2026-05-11
- **类型**：源码锚点
- **位置**：L376-L399 App Archiving 源码行号
- **问题**：ActivityStarter / PackageArchiver 行号来自 mainline 调研，但本节 frontmatter 标为 android-16.0.0_r1；固定行号在 release tag 与 mainline 之间容易漂移。
- **建议**：保留类名和方法名，删除固定行号，或补 mainline commit hash / android-16 tag 的精确锚点。

## [Task9 Deep Review] 1.10 ContentProvider 性能与优化 — 2026-05-11
- **类型**：数据缺失
- **位置**：L373 App Startup 量化收益
- **问题**：“每合并一个 ContentProvider 约节省 2ms”“冷启动减少 35% 到 42%”“2.8 秒降至 1.6 秒”缺少样本 App、设备、版本、测量方法和来源。
- **建议**：补 Macrobenchmark / Perfetto 条件与样本，或改成定性描述；保留数字时必须给基线和复现条件。
