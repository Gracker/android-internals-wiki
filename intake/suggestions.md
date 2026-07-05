## [Task9 Deep Review] 14.13 Hook 基础设施与性能工具实现原理 — 2026-07-04
- **类型**：源码准确性
- **位置**：entrypoint_utils.h路径引用
- **问题**：该文件在android-17.0.0_r1中可能不存在，与章节中引用的art/runtime/art_method.h存在冲突
- **建议**：删除entrypoint_utils.h的引用，统一使用art/runtime/art_method.h中的entry_point_from_quick_compiled_code_字段作为ART Method Entry替换的权威源码路径

## [Task9 Deep Review] 14.13 Hook 基础设施与性能工具实现原理 — 2026-07-04
- **类型**：原理完整性
- **位置**：16KB page size对Hook影响章节
- **问题**：缺少"为什么16KB会影响"的因果解释，读者难以理解page size变化的技术影响机制
- **建议**：补充因果解释："page size增大导致mprotect粒度变化，可能意外修改相邻函数的代码段保护属性，影响代码执行安全性"

## [Task9 Deep Review] 14.13 Hook 基础设施与性能工具实现原理 — 2026-07-04
- **类型**：知识盲区
- **位置**：Hook技术限制章节
- **问题**：未讨论Android 17+可能引入的新Hook限制或安全机制
- **建议**：在限制章节补充："Android 17可能进一步加强的Hook控制措施，包括更严格的SELinux策略、进程级内存保护机制等"
## [Task2A Gap Mining] 2026-07-05 知识缺口挖掘方向记录

**本轮未发现评分 ≥ 14 的知识缺口。**

### 已检查方向（避免下轮重复）

1. **Kotlin/ART Runtime Performance**（value class/inline/suspend bytecode performance）
   - 评分：13/20（素材3 × 相关3 × 需求4 × 时效3）
   - 判定：Kotlin 编译器行为而非 Android 系统内部，与全书"系统运行机制"定位偏差
   - ch01/07（ART编译）和 ch01/35（ART去优化）已覆盖核心 ART 运行时行为

2. **Android Build Performance**（Gradle/AGP/R8 Full Mode/KSP/Configuration Cache）
   - 评分：13/20（素材3 × 相关2 × 需求5 × 时效4 → 严格按标准素材2 × 相关2 × 需求4 × 时效4 = 12）
   - 判定：构建时性能而非运行时性能，与全书核心目标（启动/滑动/功耗/内存）不直接相关
   - ch14/20（R8 配置分析）和 ch25/07（R8 资源优化）已从工具和包体积角度覆盖 R8

3. **Compose / View Interop Performance**（AndroidView Tax / ViewCompositionStrategy）
   - 判定：已覆盖。ch22/03 有 59 行专节，ch22/15 有迁移性能成本分析

4. **Compose Snapshot / RecomposeScope Performance**
   - 判定：已覆盖。ch22/22.29（并发安全机制）深入覆盖了 Snapshot 系统、globalSnapshot、Recomposer 状态机

5. **Flutter Impeller Shader Compilation Performance**
   - 判定：已覆盖。ch02/11 和 ch18/12 有源码级 Impeller shader 编译流水线和 PSO 缓存分析

6. **SoC-specific Power Optimization**（Qualcomm LPM / MediaTek MTLP）
   - 评分：12/20（素材2 × 相关4 × 需求3 × 时效3）
   - 判定：SoC 厂商专有数据缺乏公开素材支撑，ch17/02 已提供 SoC 差异高层覆盖

7. **Android 17 MediaProjection / Screen Capture Pipeline**
   - 评分：13/20（素材3 × 相关3 × 需求3 × 时效4）
   - 判定：属于系统组件但读者需求集中度高，下轮可深入

8. **Android 17 ContentProvider Batch Operations / Cursor Window Performance**
   - 评分：10/20（素材3 × 相关3 × 需求2 × 时效2）
   - 判定：ch01/10 和 ch01/1.11 已覆盖 ContentProvider 优化

9. **Compose Material 3 Expressive / Dynamic Color Rendering Performance**
   - 评分：8/20（素材2 × 相关2 × 需求2 × 时效2）
   - 判定：偏 UI 设计主题，非系统级性能问题

10. **Android 17 Predictive Back Animation / Shared Element Transition Performance**
    - 判定：已覆盖。ch03/12 + ch22/13 + ch22/05 + ch22/12 + ch02/29 多章节交叉覆盖

11. **Android 17 Play Integrity / DRM / KeyStore Cryptistic Overhead**
    - 判定：已覆盖。ch08/12（Keystore）、ch08/13（BiometricPrompt）、ch08/15（Play Integrity）

12. **Compose Multiplatform / KMP Performance**
    - 评分：13/20（素材3 × 相关3 × 需求3 × 时效4）
    - 判定：KMP 生态尚在发展，ch24/17 已覆盖 Room3 KMP 性能

### 结论
全书 589 文件、17+ 章覆盖范围极其完整，本轮 30+ 候选缺口中无 ≥ 14 分通过者。
建议下轮关注方向：
- Android 17 新增 API 37 特性的运行时性能影响（API diff 中尚未被覆盖的新 API）
- Compose 1.10+ Pausable Composition 在生产环境的实际性能数据
- Android 17 Game Mode 3.0 / Game Intents 性能影响
- Android 17 16KB Page Size 对 GPU/DMA 缓冲区分配的性能量化影响


## [Task9 Deep Review] 25.17 Android 17 后台音频硬化与播放功耗治理 — 2026-07-05
- **类型**：案例支撑
- **位置**：Android 17 适配与灰度验证部分
- **问题**：缺少线上案例分析
- **建议**：增加实际企业项目中遇到的音频硬化问题案例，包括问题现象、排查过程、解决方案和效果验证，特别关注锁屏蓝牙断连、后台播放静默等典型场景


## [Task2A Gap Mining] 2026-07-05 01:04 知识缺口挖掘方向记录

**本轮未发现评分 ≥ 14 的知识缺口。**

### 已检查方向（避免下轮重复）

1. **Android 17 PMS × cpuidle × schedutil 三层协作闭环**
   - 判定：已覆盖。ch05/5.4 (DVFS) 已在 line 540-640 插入 `<!-- AIW-源码调研-2026-07-04 -->` 子节，完整覆盖 PMS DIRTY 位掩码 → IPower HAL hint → schedutil/cpuidle menu governor 闭环
   - DeepResearch 材料 `2026-07-04-android17-pms-cpuidle-schedutil-closed-loop.md` (21KB) 已被 ch5.4 吸收

2. **eScope 移动应用算子级功耗预测（论文）**
   - 评分：12/20（素材3 × 相关3 × 需求3 × 时效3）
   - 判定：学术方法论文，ch11.1 已覆盖功耗模型基础，eScope 的 SoC→算子关联方法离工程实践较远

3. **Android Desktop Experience / 窗口管理性能**
   - 判定：已覆盖。ch08/8.6 WindowManager 性能优化 + ch22 多窗口渲染覆盖

4. **NSD / Wi-Fi Direct / BLE 近场通信性能**
   - 评分：11/20（素材2 × 相关2 × 需求4 × 时效3）
   - 判定：偏 API 使用教程，非系统级性能问题。ch08/8.8 (TelephonyManager) + ch08/8.9 (ConnectivityManager) 已覆盖网络栈性能

5. **Repository suspend fun / 结构化并发性能**
   - 判定：Kotlin 协程架构模式，非系统运行时性能。ch01 已覆盖 Binder/消息驱动架构

### 结论
全书 577+ 文件覆盖范围极其完整，本轮检查 5 个新候选缺口中无 ≥ 14 分通过者。
连续 17 轮无合格候选，覆盖率真正饱和。

## [Task9 Deep Review] 25.17 Android 17 后台音频硬化与播放功耗治理 — 2026-07-05
- **类型**：源码准确性
- **位置**：shell 命令文档章节
- **问题**： 命令在 task2b 中已验证，但文档中缺少明确的源码锚点引用
- **建议**：补充 AudioManagerShellCommand.java:182-185,517-563 作为证据支撑，增强可验证性

## [Task9 Deep Review] 25.17 Android 17 后台音频硬化与播放功耗治理 — 2026-07-05
- **类型**：知识盲区
- **位置**：OEM 策略章节
- **问题**：文档提到厂商可能有额外策略，但缺乏具体测试清单和设备差异说明
- **建议**：补充主流设备厂商（小米、华为、OPPO、vivo）的后台音频限制实测清单，包括是否支持强制开启、默认行为差异等

## [Task9 Deep Review] 25.17 Android 17 后台音频硬化与播放功耗治理 — 2026-07-05
- **类型**：知识盲区
- **位置**：多音频流处理章节
- **问题**：未覆盖应用同时存在多个音频流时的硬化和冲突处理
- **建议**：增加「多音频流场景」小节，说明 MediaSession 多实例、AudioFocus 冲突解决、优先级管理等内容

## [Task9 Deep Review] 25.17 Android 17 后台音频硬化与播放功耗治理 — 2026-07-05
- **类型**：数据支撑
- **位置**：audio offload 功耗章节
- **问题**：audio offload 的具体功耗节省数据、长时播放的典型功耗模型缺乏量化数据支撑
- **建议**：补充 audio offload vs software decoding 在不同场景下的功耗对比数据，包括 CPU 占用、电池续航影响等


## [Task2A Gap Mining] 2026-07-05 知识缺口挖掘方向记录（Round 18）

**本轮未发现评分 ≥ 14 的知识缺口。连续 18 轮无合格候选。**

### 已检查方向

1. **PMS × cpuidle × schedutil 三层闭环**（DeepResearch 2026-07-04）
   - 判定：已覆盖。ch05.04 (DVFS)、ch05.01 (Linux Scheduling)、ch05.02 (EAS) 已从调度器层面覆盖

2. **Modular Startup Framework Dependency Graph**（DeepResearch 2026-07-04）
   - 判定：已覆盖。ch21.01 (Startup Analysis) 已覆盖启动框架依赖分析

3. **heapprofd Production Deployment Permissions**（DeepResearch 2026-07-04）
   - 判定：已覆盖。ch14.22 (HPROF HeapDump) 和 ch13.21 (Perfetto) 已覆盖

4. **Flutter Impeller Shader Compilation Pipeline**（DeepResearch 2026-07-04）
   - 判定：已覆盖。ch02.11 和 ch18.12 有源码级覆盖

5. **LMKD Procs Prio Batch Thrashing Mainline Fork**（DeepResearch 2026-07-04）
   - 判定：已覆盖。ch04 多个小节覆盖 LMKD 机制

6. **Binder Node Release Death Notification Batch**（DeepResearch 2026-07-04）
   - 判定：已覆盖。ch01.25 (Binder IPC Async Pipeline) 已覆盖

7. **Material 3 Expressive Performance** — 0 files found
   - 判定：偏 UI 设计主题，非系统级性能。排除

8. **Desktop Mode / Adaptive App Quality** — 14 files found
   - 判定：已充分覆盖

### 结论
全书 577 文件覆盖范围极其完整。连续 18 轮无 ≥14 分通过者。覆盖率真正饱和。


## 2026-07-05 03:05 知识缺口挖掘检查记录（Round 19）
- **检查方向**: 1 个新 DeepResearch 文件 `2026-07-05-background-audio-hardening-power.md`
- **评估结果**: 关联 ch25.17（已 finalized），为已有章节补充材料，非新章节候选
- **结论**: 0 个 ≥14 分候选，连续 19 轮覆盖饱和


## 2026-07-05 05:06 知识缺口挖掘检查记录（Round 21）
- **检查方向**: 今日 daily-info 新内容（Clean Architecture/Repository/Compose Pager/Room 3.0/AI Benchmark/Android 17 ML Scheduler/Linux 6.10 内存碎片）
- **评估结果**: 
  - 5 个应用架构/UI 教程主题 <14 分（非系统性能范畴）
  - Android 17 ML 调度器 14 分但已在 ch1.43 覆盖
  - Linux 6.10 内存碎片 10 分，已在 ch6.19 覆盖
- **结论**: 0 个 ≥14 分新候选，连续 21 轮覆盖饱和


## [Task9 Deep Review] 13.12 Perfetto Profile 导入与 Flamegraph 分析 — 2026-07-05

- **类型**：版本说明
- **位置**：适用版本说明部分
- **问题**：文中提到 "Perfetto linux.perf data source 的采集前提需要单独说明：Perfetto 官方文档标注 Android command line 路径要求 **Android 15+** 设备"，但未明确说明这是指 API level 35 还是 Android 版本号
- **建议**：在适用版本描述中明确标注 "Android 15 (API 35) - Android 17 (API 37)"，避免版本号混淆

## [Task9 Deep Review] 13.12 Perfetto Profile 导入与 Flamegraph 分析 — 2026-07-05

- **类型**：原理解释
- **位置**：采样频率建议部分
- **问题**：文中提到 "Perfetto 文档建议 Android 上非 native 调用栈采样频率低于 200Hz，避免 unwinder 压力反过来干扰被测场景"，但未解释为什么 200Hz 是分界线
- **建议**：补充 unwinder 压力影响的具体机制，说明 200Hz 以上采样会导致 unwinder 过载的原理

## [Task9 Deep Review] 13.12 Perfetto Profile 导入与 Flamegraph 分析 — 2026-07-05

- **类型**：知识盲区
- **位置**：多核分析策略
- **问题**：未讨论多核设备上不同 CPU 核心的 profiling 策略差异
- **建议**：补充多核设备上的 profiling 策略，包括 big.LITTLE 架构下的采样优化建议

## [Task9 Deep Review] 13.12 Perfetto Profile 导入与 Flamegraph 分析 — 2026-07-05

- **类型**：知识盲区
- **位置**：功耗影响
- **问题**：未说明 profiling 过程本身对设备功耗和性能的干扰
- **建议**：补充 profiling 对设备功耗和性能的影响分析，以及如何最小化干扰的实用建议


## 2026-07-05 06:07 知识缺口挖掘检查记录（Round 22）
- **检查方向**: 
  1. 全书空 draft 扫描（0 个空 draft）
  2. Task2B backlog = 0（允许挖掘）
  3. source-index.json 38 条素材中无 quality≥16 且 unmapped 的条目
  4. research-feeds 近期 5 篇已全部映射
  5. 全书 589 文件关键词反查（App Cloning/Wear OS/Health Connect/SafetyCore/Direct Share/MediaProjection/JVMTI/Smart Recapture 等 27 个关键词）
  6. 对照 Clippings 三本参考书（稳定性 25 篇 / 性能优化 22 篇 / 线上疑难 58 篇）章节结构
- **新检查候选**:
  1. App Cloning / Multi-User Performance Isolation — 素材1×相关3×需求3×时效5 = 12
  2. Wear OS / Wearable Performance — 素材2×相关2×需求3×时效3 = 10
  3. SafetyCore / Security Center Performance — 素材1×相关2×需求2×时效5 = 10
  4. Direct Share / Sharing Shortcuts Performance — 素材2×相关2×需求3×时效2 = 9
  5. MediaProjection / Screen Capture Pipeline — 13（与 Round 1 一致，维持不达标）
- **评估结果**: 0 个 ≥14 分新候选，连续 22 轮覆盖饱和
- **结论**: 全书覆盖范围极度完整。建议下轮可关注：
  - Android 17 App Cloning 对进程隔离和内存计费的性能影响（待公开素材增多后重评）
  - SafetyCore API 在性能链路中的开销（待官方文档补充）

## [Task9 Deep Review] 21.2 启动框架设计与任务编排 — 2026-07-05

- **类型**：源码准确性
- **位置**：Alpha框架Task构造函数描述
- **问题**：文中提到 `Task(String taskName, boolean isInUiThread)` 和 `Task(String taskName, int threadPriority)` 两个构造函数，但根据 alibaba/alpha 04fe7f2 源码实际只有 `Task(String taskName, boolean isInUiThread)` 一个构造函数
- **建议**：修正Task构造函数描述，补充说明线程优先级通过 `setThreadPriority(int)` 方法设置

- **类型**：版本差异覆盖
- **位置**：App Startup环检测机制
- **问题**：文中提到"框架层面必须在构建阶段做环检测"，但未说明不同版本的App Startup环检测实现差异
- **建议**：补充App Startup环检测机制在Android 13+中的改进，包括运行时循环依赖检测和优雅降级

- **类型**：版本差异覆盖
- **位置**：线程池参数配置
- **问题**：推荐的线程池配置参数在Android 17+中可能需要调整，因为Android 17引入了更智能的CPU调度策略和更严格的后台任务调度限制
- **建议**：补充Android 17+中线程池配置的注意事项

---

2026-07-05 Task14 扫描追加（赵子健性能优化 #12-15）

## [Task14 参考书扫描] 第8章 响应速度优化 — 2026-07-05
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 如何才能做好 Android 性能优化？.md]
- **建议补充**：性能优化三维方法论：硬件层→系统层→应用层自下而上的优化思维框架
- **参考书覆盖深度**：概述
## [Task14 参考书扫描] 第8章 响应速度优化 — 2026-07-05
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 如何才能做好 Android 性能优化？.md]
- **建议补充**：性能优化三大主题划分：内存优化、速度优化、包体积优化（流量/功耗优先级较低）
- **参考书覆盖深度**：概述
## [Task14 参考书扫描] 第8章 响应速度优化 — 2026-07-05
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 如何才能做好 Android 性能优化？.md]
- **建议补充**：性能优化常见误区：照搬网上方案缺乏体系化，未结合应用特性调整
- **参考书覆盖深度**：概述
## [Task14 参考书扫描] 第8章 启动优化 — 2026-07-05
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动速度？.md]
- **建议补充**：Android 8+ 系统自带启动 GC 抑制：TriggerPostForkCCGcTask 阻塞 HeapTaskDaemon 2秒
- **参考书覆盖深度**：中等
## [Task14 参考书扫描] Part5 ch23 内存实战 — 2026-07-05
- **类型**：版本更新
- **来源**：[结构参考: Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动速度？.md]
- **过时内容**：符号查找使用 ndk_dlopen/ndk_dlsym 开源库（源码引用 master 分支，需验证 android-17.0.0_r1 兼容性）
- **建议更新至**：Android 17 源码链接指向 cs.android.com master 分支，需确认在 android-17.0.0_r1 下的 API 兼容性
## [Task14 参考书扫描] 第4章 内存管理 — 2026-07-05
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]
- **建议补充**：Java 堆五大 Space 组成：ImageSpace/ZygoteSpace/NonMovingSpace/LargeObjectSpace/MainSpace
- **参考书覆盖深度**：深入
## [Task14 参考书扫描] 第4章 内存管理 — 2026-07-05
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]
- **建议补充**：Java 对象申请流程：AllocObjectWithAllocator→大对象判断(ShouldAllocLargeObject,>3页)→TryToAllocate→AllocateInternalWithGc
- **参考书覆盖深度**：深入
## [Task14 参考书扫描] 第4章 内存管理 — 2026-07-05
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]
- **建议补充**：Java 堆 OOM 判定：num_bytes_allocated_ > growth_limit_（通常512M）
- **参考书覆盖深度**：深入
## [Task14 参考书扫描] 第4章 内存管理 — 2026-07-05
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]
- **建议补充**：Java 堆创建流程与 Space 管理器：DlMallocSpace/MainMallocSpace(rosalloc)/BumpPointerSpace/RegionSpace/FreeListSpace
- **参考书覆盖深度**：深入
## [Task14 参考书扫描] 第4章 内存管理 — 2026-07-05
- **类型**：版本更新
- **来源**：[结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]
- **过时内容**：Android 5.x~7.x vs 8.0+ GC 算法差异：SS(半空间回收) vs CC(并发复制)，对应不同 Space 创建策略
- **建议更新至**：Android 17 源码引用 master 分支，需验证 Android 17 (API 37) 下 CC 算法是否仍为前台默认 GC
## [Task14 参考书扫描] 第8章 启动优化 — 2026-07-05
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]
- **建议补充**：冷热端分离 LruCache：按使用频率拆分冷热队列，热端存高频数据，提升低端设备缓存命中率
- **参考书覆盖深度**：中等
## [Task14 参考书扫描] 第8章 启动优化 — 2026-07-05
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]
- **建议补充**：Dex 类文件重排序：按启动类加载顺序重排 dex 中 class 位置，提升 cache line 命中率
- **参考书覆盖深度**：中等
## [Task14 参考书扫描] 第8章 启动优化 — 2026-07-05
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]
- **建议补充**：Facebook Redex 工具链：InterDexPass + coldstart_classes 配置实现 dex 重排
- **参考书覆盖深度**：中等
## [Task14 参考书扫描] 第8章 启动优化 — 2026-07-05
- **类型**：版本更新
- **来源**：[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]
- **过时内容**：Baseline Profiles 作为官方推荐的编译优化方案，与 Redex dex 重排的关系和优先级需在 Android 17 语境下更新
- **建议更新至**：Android 17 Redex 的 dex 重排在 ART Baseline Profiles 时代（Android 12+）的相关性和效果需重新评估

## 2026-07-05 07:12 知识缺口挖掘检查记录（Round 23）

- **检查方向**:
  1. 全书空 draft 扫描（0 个空 draft）
  2. Task2B backlog = 0（允许挖掘）
  3. source-index.json 38 条素材中无 quality≥16 且 unmapped 的条目
  4. research-feeds 近期文件已全部映射
  5. 扩展关键词扫描：Data Saver/ANGLE/AIDL/System Intelligence/JobScheduler/ContentProvider/Broadcast/SQLite/f2fs/OkHttp/Doze 等 27+ 系统子领域
  6. 对照 Clippings 三本参考书章节结构（108 篇）
- **新检查候选**:
  1. ContentProvider 性能 — 素材2×相关4×需求3×时效3 = 12（6 mentions/0 primary，已有 ch01.10 从架构覆盖）
  2. JobScheduler 性能 — 素材2×相关4×需求3×时效3 = 12（10 mentions/0 primary，分散于 ch05 功耗章节）
  3. Broadcast 投递性能 — 素材1×相关3×需求3×时效3 = 10（0 mentions，素材不足）
  4. SQLite 性能 — 已充分覆盖（14 files >5 mentions，含 3 个专节 80+97 mentions）
  5. Android System Intelligence — 素材1×相关1×需求2×时效4 = 8（偏应用层智能，非系统性能核心）
- **评估结果**: 0 个 ≥14 分新候选，连续 23 轮覆盖饱和

## 2026-07-05 08:23 知识缺口挖掘检查记录（Round 24）

- **检查方向**:
  1. 全书空 draft 扫描（0 个空 draft）
  2. Task2B backlog = 0（允许挖掘）
  3. source-index.json 无 quality≥16 且 unmapped 的条目
  4. research-feeds 近期文件（Perfetto v54 等）已映射
  5. 对照 Clippings 三本参考书章节结构（108 篇全文扫描）
     - 《Android 应用稳定性剖析与优化》15 篇 → 全部已有对应章节
     - 《Android 性能优化》16 篇 → 15/16 已覆盖（插件化包体积因技术淘汰跳过）
     - 《线上疑难问题》59 篇 → 核心主题已覆盖
  6. AOSP 框架服务覆盖审计：AMS/WMS/PMS/NotificationManager/PowerManager/Sensor/Location/Connectivity/JobScheduler/InputManager/DisplayManager 全部已有专节
  7. Android 17 新特性覆盖审计：AppFlow/LMKD/AppHibernation/JobScheduler5维节流/FGS类型/16KB Page/MTE/Staged Install 全部已覆盖
  8. 评估 ch27.2 线程优先级与 CPU 核心绑定 → 12/20（ch5 调度理论 + ch27.1 线程池已覆盖，素材不足 3 篇）
  9. 评估 ch21.17 启动内存峰值与 LMK 协同 → 12/20（ch16.8 AppFlow 系统侧 + ch21.6 延迟初始化 + ch21.7 多进程已覆盖；AppFlow 仅为研究原型未进入 AOSP 主线）
- **新检查候选**:
  1. 线程优先级调度实战 — 素材3×相关4×需求3×时效2 = 12（已有 ch05 调度理论覆盖，ch27.1 线程池 draft 覆盖）
  2. 启动内存峰值控制 — 素材2×相关4×需求3×时效3 = 12（AppFlow 为研究原型，ch16.8 已系统侧覆盖）
- **评估结果**: 0 个 ≥14 分新候选，连续 24 轮覆盖饱和
