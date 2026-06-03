# 第 16 章：AOSP 性能优化

前面的大部分章节，更多在解释 Android 系统已经是什么样子。  
这一章开始换一个视角：如果你站在 AOSP、系统服务、ROM 或平台的角度，性能问题还能怎样被直接改。

这时候思考方式会变得不一样。应用开发者更关心“怎么绕开瓶颈”，而系统侧更关心“瓶颈为什么会这样设计、能不能从系统层把它改掉”。  
所以这一章更适合那些已经不满足于只在 App 侧做局部优化的读者。

## 本章内容

- Google 官方的性能优化思路
- 各 Android 版本性能变更追踪
- AOSP 源码编译与调试环境

## 阅读建议

- 如果你主要做 App 侧优化，这一章不用一开始就全读，但读懂其中的系统改动思路会很有帮助。
- 如果你做的是系统、ROM 或平台方向，这一章应该和前面的调度、渲染、内存、功耗章节反复对照着看。

## 延伸阅读

### Android Debug 与 Release 构建在 Profiling 下的系统性行为差异
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/Android Debug 与 Release 构建在 Profiling 下的系统性行为差异.md
- 类型：DeepResearch 调研结果
- 摘要：系统梳理 Debug/Release 构建在 ART、Zygote、dex2oat、SELinux 与 profiling 工具链中的行为差异，解释为什么调试态与生产态 trace、采样和基准测试结果不可直接等价。
- 注入时间：2026-04-25
- 价值：适合作为 AOSP 性能分析方法论的防踩坑材料，帮助区分构建类型带来的 profiling 偏差。

### Android World 与 MobileWorld 深度技术架构调研
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/Android World 与 MobileWorld 深度技术架构调研.md
- 类型：DeepResearch 调研结果
- 摘要：对 google-research/android_world 与 MobileWorld 的任务定义、环境架构、评测协议、ADB/无障碍控制链路和数据闭环做机制级对比，可作为端侧 GUI Agent 与手机自动化评测体系的外部参考。
- 注入时间：2026-04-25
- 价值：能补齐 AI × 手机/GUI Agent 在 Android 系统侧评测环境、动作空间与任务闭环的参考背景。

### Android 17 ResourcesManager 与 Configuration 变更分发机制
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-01-android-17-resourcesmanager-configuration-system.md
- 类型：DeepResearch 调研结果
- 摘要：基于 android-17.0.0_r1 源码分析 Configuration 变更分发路径：ConfigurationChangeToker->ATMS->ActivityThread->ResourcesManager->ResourcesImpl。确认 AOSP 无独立场景感知框架（ATOMSCENE 为 OEM 定制），Configuration 体系是 AOSP 的场景感知体现。
- 注入时间：2026-06-01
- 价值：明确了 Android 17 Configuration 分发源码锚点，澄清 OEM 场景感知框架与 AOSP 的边界

### Android Binder IPC 机制 — 从 Java 层到 Kernel Driver 源码分析
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-01-android-binder-ipc-mechanism-source-analysis.md
- 类型：DeepResearch 调研结果
- 摘要：完整梳理 Binder IPC 三层架构：Java 层 Binder/BinderProxy → JNI(android_util_Binder.cpp) → Native BpBinder/BBinder → IPCThreadState.talkWithDriver() → ioctl(BINDER_WRITE_READ)。详解 BC_/BR_ 命令协议、flat_binder_object 类型编码、Parcel 序列化、死亡通知机制、线程池管理。源码锚点 android-17.0.0_r1，可作为 Binder 全链路阅读导航。
- 注入时间：2026-06-03
- 价值：为AOSP 性能优化章节提供端到端链路梳理和 Perfetto 可观测性方案参考
