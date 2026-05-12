## [2026-05-11] 2.10 GPU 渲染深入 — 知识盲区

### 盲区描述
生产环境GPU性能问题的调试方法论缺失。当前章节主要介绍了GPU渲染原理，但缺少在生产环境中如何系统性排查GPU性能问题的方法论，包括GPU性能瓶颈的识别工具、分析方法、以及不同厂商GPU的调试特性。

### 重要程度
高

### 建议研究方向
- 深入研究Android GPU Inspector (AGI)、Perfetto GPU counters在生产环境中的使用方法
- 分析Qualcomm Adreno、ARM Mali、Imagination PowerVR等主流GPU厂商的调试工具差异
- 建立GPU性能问题的系统性排查流程，从CPU-GPU同步、内存带宽、着色器编译等多维度分析
- 研究GPU性能问题的在线监控和自动化告警机制

### 关联章节
2.10, 3.13, 7.9, 14.3

---

## [2026-05-11] 8.9 Android 游戏性能与 Game Mode/State API — 知识盲区

### 盲区描述
OEM设备厂商特有游戏性能模式与标准Game Mode/State API的交互机制不明确。当前章节只讨论了标准的Android API，但缺少对设备厂商（如小米、OPPO、vivo等）特有的游戏性能优化模式如何与标准API协作的分析。

### 重要程度
高

### 建议研究方向
- 分析主流设备厂商（Qualcomm、MediaTek、三星）的游戏性能优化技术栈
- 研究OEM游戏模式与标准Game Mode API的优先级和覆盖关系
- 建立厂商特性适配指南，帮助开发者识别和适配不同设备的游戏优化机制
- 分析厂商模式下系统资源调度、热管理、GPU驱动的具体实现差异

### 关联章节
8.9, 5.5, 7.1, 5.9

---

## [2026-05-11] 2.9 渲染机制的版本演进 — 知识盲区

### 盲区描述
GPU渲染在不同硬件厂商（Qualcomm、MediaTek、三星等）SoC上的实现差异说明不足。当前章节从Android版本演进角度介绍了渲染机制变化，但缺少对硬件厂商具体实现差异的分析，这导致开发者难以针对不同硬件进行针对性优化。

### 重要程度
高

### 建议研究方向
- 分析主流GPU厂商（Qualcomm Adreno、MediaTek MTP、ARM Mali）的渲染架构差异
- 研究不同厂商GPU驱动的优化特性和限制条件
- 建立厂商特性适配指南，包括GPU指令集优化、内存管理、调度策略等
- 分析厂商特有技术（如Qualcomm的FlexRender、MediaTek的Mali优化）对渲染性能的影响

### 关联章节
2.9, 3.13, 7.9, 16.1
## [2026-05-12] 17.2 SoC 平台差异 — 知识盲区

### 盲区描述
Oryon 处理器的微架构细节，特别是 L1/L2 缓存的具体容量、访问延迟周期、以及缓存拓扑结构。现有资料主要依赖二手分析和推测性文章，缺乏 Qualcomm 官方白皮书、Hot Chips/ISSCC 学术演讲或权威芯片拆解报告的确认。

### 重要程度
高

### 建议研究方向
- 跟踪 Qualcomm 官方技术文档发布，特别是针对 Snapdragon X Elite 的微架构详解
- 关注芯片拆解报告中的实际测量数据（如 AnandTech、Chipworks 等专业机构）
- 研究面向开发者的性能分析工具中的硬件计数器暴露情况
- 分析 AOSP 源码中与 Qualcomm 硬件相关的适配代码

### 关联章节
5.1, 5.3, 5.4, 2.10, 17.1

## [2026-05-12] 20.8 崩溃聚合与归因分析 — 知识盲区

### 盲区描述
基于大模型的崩溃分析新技术应用，包括深度学习在崩溃模式识别、根因分析、趋势预测等方面的应用。现有内容主要基于传统统计和规则方法，缺少 AI 时代的崩溃治理技术演进。

### 重要程度
高

### 建议研究方向
- 研究业界领先的崩溃分析平台（如 Sentry、Firebase Crashlytics）中的 ML 应用
- 探索深度学习在崩溃模式聚类和异常检测中的应用
- 分析大语言模型在崩溃根因分析和修复建议生成中的潜力
- 研究国际化应用的崩溃聚合特殊挑战和解决方案

### 关联章节
20.6, 26.2, 19.18

## [2026-05-12] ch20 Native Crash 高级防护 — 参考书素材

### 来源
[结构参考: Clippings/Android 应用稳定性剖析与优化 - pthread_create 回溯：原来 Native 也有 try catch！.md]

### 知识点
1. C 语言非局部跳转（sigsetjmp/siglongjmp）原理及其在信号处理中的应用
2. 通过 GOT Hook pthread_create 实现线程级 crash 安全点：在 start_routine 执行前设置 sigsetjmp，crash 时通过信号处理器调用 siglongjmp 回到安全点
3. sigaltstack 为 SIGSEGV 等信号预留独立栈空间（避免默认栈不可用）
4. handleFlag 标志位管理：线程进入时置 1、退出时置 0，防止非线程 crash 被误拦截
5. bhook/bytehook 框架内置类似回溯机制的实际工程应用
6. 开源实现 mooner (TestPlanB/mooner) 的完整代码参考

### 重要程度
高

### 建议加工方向
- 整理为 ch20 中「Native Crash 兜底机制」专题，与已有的信号捕获（20.5）和 Native Backtrace（20.6）形成递进
- 补充 sigsetjmp/siglongjmp 在不同 Android 版本/架构上的兼容性验证
- 结合实际大厂（微信、字节）的线程级 crash 防护实践案例
- 讨论 hook 点选择的工程权衡（pthread_create hook vs 其他方案）

## [2026-05-12] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 知识盲区

### 盲区描述
DeliQueue drain 过程中的同步屏障处理机制缺失

### 重要程度
高

### 建议研究方向
- - 深入研究 frameworks/base/core/java/android/os/Looper.java 中的 drain 逻辑
- 分析同步屏障在 DeliQueue 中的特殊处理路径
- 对比 Android 16 和 17 中屏障语义的兼容性处理

### 关联章节
2.9, 2.10


## [2026-05-12] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 知识盲区

### 盲区描述
Generational CMC 与传统 CC GC 的具体实现对比数据缺失

### 重要程度
高

### 建议研究方向
- - 获取 AOSP art/runtime/gc/collector/ 目录下的具体实现对比
- 分析 young generation GC 与 full GC 的暂停时间差异
- 验证不同内存工作负载下的分代效果

### 关联章节
4.3, 4.8


## [2026-05-12] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 知识盲区

### 盲区描述
ProfilingManager 新触发器在不同 Android 版本中的兼容性处理缺失

### 重要程度
中

### 建议研究方向
- - 分析 ProfilingManagerService.java 中的版本判断逻辑
- 验证 trigger 常量在不同 API 版本中的可用性
- 提供兼容性检查和降级处理建议

### 关联章节
14.7, 1.13


## [2026-05-12] 17.2 SoC 平台差异 — 知识盲区

### 盲区描述
各平台实机测试数据缺失，结论缺乏数据支撑

### 重要程度
高

### 建议研究方向
- - 设计跨平台性能基准测试方案
- 收集 Snapdragon 8 Gen 3、Dimensity 9400、Tensor G4 的实际性能数据
- 建立 Perfetto trace 对比分析方法

### 关联章节
5.1, 2.10


## [2026-05-12] 17.2 SoC 平台差异 — 知识盲区

### 盲区描述
高通 Oryon 缓存参数缺乏权威数据支撑

### 重要程度
高

### 建议研究方向
- - 获取 Qualcomm 官方的架构文档和缓存参数
- 验证 Oryon L1/L2 缓存的容量和延迟数据
- 对比与 Apple A17/M2 的缓存架构差异

### 关联章节
5.3, 5.4

## [2026-05-12] 17.2 SoC 平台差异 — 知识盲区

### 盲区描述
各平台实际性能对比的测试数据缺失，结论缺乏数据支撑。需要补充实机测试数据来验证 SoC 性能差异分析。

### 重要程度
高

### 建议研究方向
- 补充各平台（高通Oryon、联发科Tensor、三星Exynos）的实际性能对比测试
- 收集Perfetto trace分析数据验证调度策略效果
- 建立统一的性能测试基准和测试环境

### 关联章节
- 5.1 Linux 调度器
- 2.10 GPU 渲染深入
- 16.5 Android 17 性能变更

## [2026-05-12] 8.8 Android 多媒体管线性能 — Codec2 / tunneled playback / Media3 ABR

### 盲区描述
章节需要补齐 OMX → Codec2 的媒体框架演进、tunneled playback 在 OMX 与 Codec2 下的实现差异，以及 Media3 ABR “主动预测 / 亚 100ms 决策”是否有官方 release note、commit 或 benchmark 支撑。

### 重要程度
高

### 建议研究方向
- 核对 `frameworks/av/media/codec2/`、`frameworks/av/media/libstagefright/`、Codec2 component 配置与 tunneled playback 相关源码锚点。
- 核对 AndroidX Media3 release notes、`AdaptiveTrackSelection` / `BandwidthMeter` 变更与可复现实验数据。
- 整理 SurfaceView / TextureView / tunneled sideband 三路径在 Android 10-17 的版本边界。

### 关联章节
8.8、2.6、2.15、2.16、14.9
