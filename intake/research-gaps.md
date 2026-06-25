## [2026-06-26] ch15-methodology — 知识盲区

### 盲区描述
性能分析工具的演进历程缺失。当前章节提到了Perfetto、Systrace等工具，但缺少从Android 8到17的工具链演进介绍，以及各工具在不同版本中的适用性和替代关系。

重要程度
高

### 建议研究方向
- 研究Android 8-17中性能分析工具的演进路径（Systrace → Perfetto的过渡过程）
- 分析不同版本下工具的性能特点和适用场景
- 调查主流厂商（华为、小米、OPPO等）性能监控工具的差异和特点
- 研究AI辅助性能分析工具在当前Android生态中的应用和发展趋势

### 关联章节
- 13.3 Perfetto 内存分析
- 14.2 Android 性能分析工具对比
- 15.1 Android 性能优化研究方法论

---

## [2026-06-26] 15.1 Android 性能优化研究方法论 — 知识盲区

### 盲区描述
章节缺少对厂商定制化性能工具的讨论。当前内容主要关注 AOSP 标准工具链（Perfetto、SimplePerf、Systrace），但对华为、小米、OPPO 等厂商提供的定制化性能分析工具（如 Huawei Profiler、Mi Performance Toolkit 等）适配和使用方法覆盖不足。

### 重要程度
高

### 建议研究方向
- 研究主流厂商（华为、小米、OPPO）的定制化性能工具
- 分析厂商工具与 AOSP 标准工具的异同点和适用场景
- 收集厂商工具的最佳实践和迁移指南
- 建立厂商工具与 AOSP 工具的对比矩阵

### 关联章节
- 14.5 Android 性能分析工具全景
- 14.12 各厂商性能优化实践
- 15.5 性能优化实战案例

---

## [2026-06-26] 15.2 线上性能监控体系建设 — 知识盲区

### 盲区描述
章节对线上性能监控体系建设深度不足。当前内容主要集中在调试阶段的性能分析工具，对线上持续监控、预警体系、性能基线管理等运维环节讨论较少，缺少从开发到线上全链路的性能监控策略。

### 重要程度
中

### 建议研究方向
- 研究线上性能监控的架构设计和实现方案
- 分析性能指标采集、聚合、存储的最佳实践
- 建立性能异常检测和预警机制
- 开发性能基线管理和自动优化建议系统

### 关联章节
- 14.8 性能监控平台架构
- 15.6 性能优化自动化
- 16.2 运维监控体系设计

---

## [2026-06-25] 14.1 Android Studio Profiler — 知识盲区

### 盲区描述
Memory Profiler 的 JVMTI 版本演进历史不清晰。当前章节声称 "在 Android 8.0（API 26）之后，Memory Profiler 的数据精度大幅提升。这得益于 Android 8.0 引入的 JVMTI（JVM Tool Interface）机制"，但 JVMTI 作为 JVM Tool Interface 在更早的 Java 版本中就已存在，Android 8.0 的具体改进内容和影响需要进一步研究。

### 重要程度
高

### 建议研究方向
- 研究Android 8.0对JVMTI的具体增强内容和API变化
- 分析Android 8.0前后Memory Profiler数据精度的差异量化
- 调查其他Android版本（Android 9、10、11+）对JVMTI/Memory Profiler的持续改进
- 收集不同Android版本下Memory Profiler的准确性和性能基准数据

### 关联章节
- 5.4 JVM 性能优化基础
- 13.3 Perfetto 内存分析
- 14.2 Android 性能分析工具对比

## [2026-06-26] 20.x 稳定性监控基础设施：字节码插桩（ASM） — 参考书素材

### 来源
[结构参考: Clippings/Android 应用稳定性剖析与优化 - ASM 与字节码插桩：改写字节码的"神器".md]

### 知识点
1. ASM TreeAPI 核心类：ClassNode（类结构）、FieldNode（属性）、MethodNode（方法）与字节码的映射关系
2. 字节码指令集 AbstractInsnNode 体系：JumpInsnNode（跳转）、LdcInsnNode（常量入栈）、MethodInsnNode（方法调用 INVOKESTATIC/INVOKEVIRTUAL）等
3. 实战示例：通过 ASM 替换 System.loadLibrary 为自定义 loader（Native Hook 前置基建）
4. ASM 在大厂监控框架中的应用：阿里、字节、滴滴、美团的插件基本基于 ASM 做字节码修改

### 重要程度
中

### 建议加工方向
- 可作为 ch20（稳定性治理）或 ch26（可观测性）的「监控基建」子节
- 重点不是教 ASM 语法，而是说明「为什么稳定性监控需要字节码插桩」以及在 Android 编译管线（AGP Transform / Lint Variant API）中的接入点
- 结合 Android 16/17 的 AGP 版本变化，说明新版编译管线对 ASM 插桩的影响

---

## [2026-06-26] 16.3 AOSP 源码导航：Android.bp 与符号定位 — 参考书素材 [章节待创建/补充]

### 来源
[结构参考: Clippings/Android 应用稳定性剖析与优化 - Android.bp 文件与符号表：如何才能找到函数符号？.md]

### 知识点
1. Android.bp → Soong → Ninja 构建链路：从源码文件到 .so 库的映射关系查找
2. C++ name mangling 规则：_ZN 前缀（类成员函数）、_Z 前缀（静态/全局）的 demangling
3. readelf -s / c++filt 工具链：定位 native 函数符号的实操流程
4. 实战案例：从 AOSP 源码定位 BpBinder::transact → libbinder.so → 符号 _ZN7android8BpBinder8transactEjRKNS_6ParcelEPS1_j

### 重要程度
中

### 建议加工方向
- 补充到 ch16.3（AOSP 源码编译与调试环境）或 ch15.7（AOSP 代码阅读）
- 现有 ch16.3 已覆盖 Soong/Ninja 构建链路，但缺少「如何反向定位函数在哪个 .so 中」的实操
- 可新增小节：「符号定位实战」— 从 AOSP 源码到 .so 映射、readelf/c++filt 工具使用
