# Android 性能优化知识图谱（高爷精选资源）

> 来源：https://www.androidperformance.com/2018/05/07/Android-performance-optimization-skills-and-tools/
> 作者：Gracker（高爷）
> 发布日期：2018-05-07（持续更新至 2022-06-27）
> 类型：专家精选资源库（第三方文章+官方文档+团队博客）
> 融入策略：绝不直接搬运，提取事实性知识点用自己语言重述，标注原始出处
> 全部纳入加工

> 这是高爷多年 Android 性能优化工作积累的精选资源，约 255 条，覆盖 15 个分类。
> 每条资源都经过专家筛选，是 AIW 各章节最重要的**参考书目**。

---

## 1. 优化心得与经验（→ 15.1 方法论 + 14.5 三方库 + 15.5 线上监控）

| # | 资源名称 | 映射 AIW 章节 | 备注（来源/类型） |
|---|---------|-------------|-----------------|
| 1 | 抖音 Android 启动优化实践 | 15.1, Ch08 | 字节跳动技术博客 / 大厂实践 |
| 2 | Android Performance Patterns | 15.1 | Google 官方视频系列 / 方法论 |
| 3 | Matrix TraceCanary 源码解析 | 14.5, 15.5 | 腾讯 Matrix / 开源工具 |
| 4 | Matrix IOCanary 源码解析 | 14.5, 15.5 | 腾讯 Matrix / 开源工具 |
| 5 | 微信 Android 内存优化实践 | 15.1, Ch04 | 腾讯微信团队 / 大厂实践 |
| 6 | 支付宝 Android 启动优化 | 15.1, Ch08 | 蚂蚁金服技术博客 / 大厂实践 |
| 7 | 字节 BoostMultiDex 优化 | 14.5, Ch08 | 字节跳动 / 开源工具 |
| 8 | 字节 Olympic（APM 框架） | 15.5 | 字节跳动 / 内部框架 |
| 9 | 字节 Probe（线上监控） | 15.5 | 字节跳动 / 开源工具 |
| 10 | 字节 mSponge（内存优化） | 14.5, Ch04 | 字节跳动 / 开源工具 |
| 11 | 字节 NativeCrash 治理实践 | 15.1, Ch09 | 字节跳动 / 大厂实践 |
| 12 | 字节 Fastbot（稳定性测试） | 15.5, Ch09 | 字节跳动 / 开源工具 |
| 13 | 美团 Android 线程池优化 | 15.1 | 美团技术博客 / 大厂实践 |
| 14 | 高刷新率列表卡顿优化 | 15.1, Ch07 | 大厂实践 / 流畅度 |
| 15 | ASM 字节码插桩大图监控 | 14.5, 15.5 | 字节码插桩 / 线上监控 |
| 16 | Android S 内存泄露检测 | 15.5, Ch04 | Google 官方 / 系统特性 |
| 17 | 全链路可观测架构实践 | 15.5 | 大厂架构 / APM 体系 |

## 2. 响应速度（→ Ch08）

| # | 资源名称 | 映射 AIW 章节 | 备注（来源/类型） |
|---|---------|-------------|-----------------|
| 1 | Android 启动全流程源码分析 | Ch08 | 源码分析 / 系统框架 |
| 2 | Android 启动优化全记录 | Ch08 | 高爷博客 / 实践总结 |
| 3 | Optimizing App Boot Times | Ch08 | Google I/O 演讲 / 官方 |
| 4 | Android 启动时间计算方法 | Ch08 | 技术博客 / 方法论 |
| 5 | Google Launch-time Performance | Ch08 | Google 官方文档 |
| 6 | 冷启动优化新思路 | Ch08 | 大厂实践 / 创新方案 |
| 7 | 支付宝重排布优化实践 | Ch08 | 蚂蚁金服 / 二进制重排 |
| 8 | Redex Interdex 优化 | Ch08 | Facebook / 开源工具 |
| 9 | 抖音二进制重排优化 | Ch08 | 字节跳动 / 大厂实践 |
| 10 | 爱奇艺 Android 启动优化 | Ch08 | 爱奇艺技术博客 / 大厂实践 |
| 11 | APM 页面加载耗时监控 | Ch08, 15.5 | APM 工具 / 线上监控 |
| 12 | Baseline Profiles 实践 | Ch08 | Google 官方 / Android 13+ |
| 13 | Android 冷启动流程详解 | Ch08 | 源码分析 |
| 14 | App Startup 库原理与优化 | Ch08 | Google Jetpack / 官方库 |

## 3. 流畅度（→ Ch07）

| # | 资源名称 | 映射 AIW 章节 | 备注（来源/类型） |
|---|---------|-------------|-----------------|
| 1 | Android 卡顿丢帧原因概述：方法论篇 | Ch07 | 高爷原创 / 方法论 |
| 2 | Android 卡顿丢帧原因概述：系统篇 | Ch07 | 高爷原创 / 系统分析 |
| 3 | Android 卡顿丢帧原因概述：应用篇 | Ch07 | 高爷原创 / 应用优化 |
| 4 | Android 卡顿掉帧分析：原理篇 | Ch07 | 高爷原创 / 原理解析 |
| 5 | Android 卡顿掉帧分析：工具篇 | Ch07, Ch13 | 高爷原创 / 工具使用 |
| 6 | Android 卡顿掉帧分析：实战篇 | Ch07 | 高爷原创 / 实战案例 |
| 7 | 无障碍服务导致全局卡顿分析 | Ch07 | 系统特性 / Bug 分析 |
| 8 | Evaluating Performance using Systrace | Ch07, Ch13 | Google 官方文档 |
| 9 | Understanding Systrace | Ch07, Ch13 | Google 官方文档 |
| 10 | Using ftrace for Performance Analysis | Ch07, Ch13 | Linux 内核 / 工具 |
| 11 | Capacity/Jitter/Jank 性能指标 | Ch07 | 性能指标体系 / 方法论 |
| 12 | Android 显示性能指标详解 | Ch07 | 技术博客 / 指标体系 |
| 13 | Slow Rendering（慢渲染检测） | Ch07 | Google 官方文档 |
| 14 | Android 流畅度检测原理 | Ch07 | 技术分析 / 检测方法 |
| 15 | JankTracker 原理与实现 | Ch07 | Android Framework / 源码 |
| 16 | Android 界面性能调优手册 | Ch07 | 综合指南 / 方法论 |
| 17 | 字节码插桩排查高耗时方法 | Ch07, 14.5 | 字节码插桩 / 工具 |
| 18 | FPS 计算原理与实现 | Ch07 | 技术分析 / 指标 |
| 19 | Jank/Stutter/卡顿率指标详解 | Ch07 | 性能指标 / 方法论 |
| 20 | 直播场景卡顿优化实践 | Ch07 | 大厂实践 / 垂直场景 |

## 4. 内存（→ Ch04 + Ch10）

| # | 资源名称 | 映射 AIW 章节 | 备注（来源/类型） |
|---|---------|-------------|-----------------|
| 1 | 抖音 OOM 优化之 NativeBitmap | Ch04 | 字节跳动 / 大厂实践 |
| 2 | 抖音 mSponge 内存优化 | Ch04 | 字节跳动 / 开源工具 |
| 3 | 抖音 Java 内存优化实践 | Ch04 | 字节跳动 / 大厂实践 |
| 4 | Camera 内存占用分析与优化 | Ch04 | 硬件相关 / 内存优化 |
| 5 | Android 64M 内存限制问题 | Ch04 | 系统限制 / 历史问题 |
| 6 | GWP-ASan 内存安全检测 | Ch04, Ch10 | LLVM/Google / 工具 |
| 7 | MTE（Memory Tagging Extension） | Ch04, Ch10 | ARM 架构 / 硬件特性 |
| 8 | 低内存对 Android 性能的影响 | Ch04 | 高爷原创 / 系统分析 |
| 9 | Android Low RAM 设备优化 | Ch04 | Google 官方文档 |
| 10 | Linux Swap 与 Zram 机制 | Ch04, 5.1 | Linux 内核 / 系统优化 |
| 11 | Android OOM 案例分析 | Ch04, Ch10 | 实战案例 / 问题排查 |
| 12 | Android 内存优化建议系列（4篇） | Ch04 | 高爷原创 / 方法论 |
| 13 | MAT（Memory Analyzer Tool）使用系列 | Ch04, Ch13 | Eclipse/开源工具 |
| 14 | LowMemoryKiller 机制详解 | Ch04, 5.1 | Android 内核 / 系统机制 |
| 15 | Ashmem（匿名共享内存）原理 | Ch04 | Android 系统 / IPC 内存 |
| 16 | 郝健 Linux 内存管理系列（6节） | Ch04, 4.2 | 技术课程 / Linux 内存 |
| 17 | Google Manage Your App's Memory | Ch04 | Google 官方文档 |
| 18 | Google Memory Management Overview | Ch04 | Google 官方文档 |
| 19 | Android Cache Memory 管理 | Ch04 | 系统机制 / 缓存 |
| 20 | Bitmap 内存优化最佳实践 | Ch04 | Google 官方 + 实践 |
| 21 | Android 内存压缩机制 | Ch04 | 系统特性 / zRAM |
| 22 | dumpsys meminfo 详解 | Ch04, Ch13 | Android 工具 / 调试 |
| 23 | Binder 内存拷贝优化 | Ch04, Ch03 | 系统框架 / IPC |
| 24 | Android 纹理压缩格式 | Ch04, Ch02 | 图形栈 / 内存优化 |
| 25 | Perfetto 分析 Native 内存泄漏 | Ch04, Ch13 | Google 工具 / 实战 |
| 26 | JVMTI 内存分析 | Ch04 | JVM 工具接口 / 调试 |
| 27 | ThreadLocal 内存泄漏分析 | Ch04 | Java 机制 / 常见问题 |
| 28 | Android 内存泄漏常见模式 | Ch04, Ch10 | 方法论 / 经验总结 |
| 29 | Large Object Space (LOS) 分析 | Ch04, 4.8 | ART 虚拟机 / 内存管理 |
| 30 | 内存分配器原理（jemalloc/tcmalloc） | Ch04 | 底层技术 / 内存分配 |

## 5. 图形栈（→ Ch02）

| # | 资源名称 | 映射 AIW 章节 | 备注（来源/类型） |
|---|---------|-------------|-----------------|
| 1 | Android 12(S) 图形显示系统（13篇系列） | Ch02 | 系统源码分析 / 图形栈 |
| 2 | Android Display Pipeline 详解 | Ch02 | 系统架构 / 显示管线 |
| 3 | Hardware Layer 原理与应用 | Ch02 | 高爷原创 / 硬件加速 |
| 4 | Android 硬件加速原理 | Ch02 | 系统框架 / 硬件加速 |
| 5 | Android 图形系统整体概述 | Ch02 | 系统架构 / 概览 |
| 6 | Choreographer 原理分析 | Ch02, Ch07 | 系统框架 / VSync |
| 7 | SurfaceFlinger 启动流程 | Ch02 | 系统源码 / 图形合成 |
| 8 | SurfaceFlinger 绘图流程 | Ch02 | 系统源码 / 图形合成 |
| 9 | 老罗 Android UI 硬件加速系列（6篇） | Ch02 | 技术博客 / 源码分析 |
| 10 | GraphicBuffer 与 Fence 机制 | Ch02 | 系统机制 / 图形缓冲 |
| 11 | Android P 图形显示系统（12篇系列） | Ch02 | 系统源码分析 / 图形栈 |
| 12 | Android 光栅化原理（2篇） | Ch02 | 系统原理 / 渲染管线 |
| 13 | RenderThread 工作原理 | Ch02 | 系统框架 / 渲染线程 |
| 14 | View 绘制流程（measure/layout/draw） | Ch02 | 系统框架 / UI 渲染 |
| 15 | Surface 与 SurfaceView 原理 | Ch02 | 系统框架 / 图形 |
| 16 | BufferQueue 工作机制 | Ch02 | 系统机制 / 图形缓冲 |
| 17 | VSync 信号分发机制 | Ch02, Ch07 | 系统框架 / 垂直同步 |
| 18 | HWUI 渲染管线详解 | Ch02 | 系统框架 / 硬件渲染 |
| 19 | OpenGL ES 在 Android 中的使用 | Ch02 | 图形 API / GPU |
| 20 | Vulkan 支持与分析 | Ch02 | 图形 API / GPU |
| 21 | TextureView vs SurfaceView 对比 | Ch02 | 系统组件 / 性能对比 |
| 22 | Layer 类型与性能影响 | Ch02 | 系统框架 / 硬件加速 |
| 23 | RenderNode 与 DisplayList | Ch02 | 系统框架 / 渲染优化 |
| 24 | Android 截图与屏幕录制机制 | Ch02 | 系统框架 / 图形 |
| 25 | Android 13 图形系统新特性 | Ch02 | 系统更新 / 新特性 |

## 6. 虚拟机（→ 1.7 ART + 4.3 + 4.8 GC）

| # | 资源名称 | 映射 AIW 章节 | 备注（来源/类型） |
|---|---------|-------------|-----------------|
| 1 | ART GC 触发时机分析 | 1.7, 4.8 | ART 源码分析 |
| 2 | ART LOS（Large Object Space） | 1.7, 4.8 | ART 源码分析 |
| 3 | ART JNI 实现原理 | 1.7, 4.3 | ART 源码分析 |
| 4 | ART Finalize 机制 | 1.7, 4.8 | ART 源码分析 |
| 5 | ART GC 回收 Native 内存 | 1.7, 4.8 | ART 源码 / 混合回收 |
| 6 | ART 对象内存结构分析 | 1.7, 4.3 | ART 源码分析 |
| 7 | ART JNI 注册机制 | 1.7, 4.3 | ART 源码分析 |
| 8 | ART 锁机制（Lock/Monitor） | 1.7 | ART 源码 / 并发 |
| 9 | ART SIGSEGV 信号处理 | 1.7, Ch09 | ART 源码 / 崩溃处理 |
| 10 | ART GC 优化故事 | 1.7, 4.8 | Google 工程师分享 |
| 11 | GC 超时导致崩溃分析 | 4.8, Ch09 | 实战案例 / 崩溃 |
| 12 | Android 10 ART 改进系列（5篇） | 1.7 | Google 官方 / 系统更新 |
| 13 | ART and Dalvik 对比 | 1.7 | Google 官方文档 |
| 14 | ART Improvements in Android | 1.7 | Google 官方文档 |
| 15 | Dalvik 虚拟机系列（4篇） | 1.7 | 技术博客 / 历史对比 |
| 16 | Configuring ART Virtual Machine | 1.7 | Google 官方文档 |
| 17 | Debugging ART GC Issues | 1.7, 4.8 | Google 官方文档 |
| 18 | ART JIT Compiler 原理 | 1.7 | ART 源码 / JIT |
| 19 | ART 并行拷贝 GC（CC GC） | 1.7, 4.8 | ART 源码 / GC 算法 |
| 20 | dex2oat 编译流程 | 1.7 | ART 源码 / AOT 编译 |
| 21 | ART 解释器与执行模式 | 1.7 | ART 源码 / 执行引擎 |
| 22 | ART GC 算法演进（Concurrent/CC/MC） | 1.7, 4.8 | ART 源码 / GC 演进 |

## 7. 系统框架（→ Ch01 + Ch03）

| # | 资源名称 | 映射 AIW 章节 | 备注（来源/类型） |
|---|---------|-------------|-----------------|
| 1 | Android 画面显示流程（5篇） | Ch01, Ch02 | 源码分析 / 显示系统 |
| 2 | Task Snapshots 机制 | Ch01, Ch03 | Android 系统 / 任务快照 |
| 3 | Android Input 子系统系列（2篇） | Ch01, Ch03 | 系统源码 / 输入系统 |
| 4 | EventHub 事件读取机制 | Ch01, Ch03 | 系统源码 / 输入系统 |
| 5 | Android 消息机制（Java→Native） | Ch01, Ch03 | 系统源码 / Handler |
| 6 | Binder 机制系列（3篇） | Ch03 | 系统源码 / IPC |
| 7 | Binder 设计与实现 | Ch03 | 设计文档 / IPC 架构 |
| 8 | Android 四大组件系列（5篇） | Ch01 | 系统框架 / 组件 |
| 9 | Activity 与 Window 的关系 | Ch01, Ch03 | 系统框架 / UI 架构 |
| 10 | Context 原理分析 | Ch01 | 系统框架 / 上下文 |
| 11 | Application 创建流程 | Ch01 | 系统源码 / 启动 |
| 12 | 从 Window 视角看 startActivity | Ch01, Ch03 | 系统源码 / 启动 |
| 13 | WMS 启动窗口分析 | Ch01, Ch03 | 系统源码 / 窗口管理 |
| 14 | WMS 启动过程详解 | Ch01, Ch03 | 系统源码 / 窗口管理 |
| 15 | Binder 系列（10篇） | Ch03 | 源码分析 / IPC |
| 16 | 彻底理解 Android Binder | Ch03 | 技术博客 / IPC 原理 |
| 17 | Android Binder 指南 | Ch03 | Google 官方文档 |
| 18 | MessageQueue.IdleHandler 原理 | Ch01, Ch03 | 系统源码 / 消息机制 |
| 19 | Android 消息机制详解 | Ch01, Ch03 | 系统源码 / Handler |
| 20 | APK 构建与安装系列 | Ch01 | 系统框架 / 包管理 |
| 21 | Android 事件拦截机制（dispatchTouchEvent） | Ch01, Ch03 | 系统框架 / 触摸事件 |
| 22 | Binder 内存拷贝分析 | Ch03, Ch04 | 系统源码 / IPC 性能 |
| 23 | AIDL inout 参数传递 | Ch03 | 开发指南 / IPC |
| 24 | Binder 异常处理/代理/生命周期 | Ch03 | 系统源码 / IPC |
| 25 | Android 10 Binder 改进系列（10篇） | Ch03 | Google 官方 / 系统更新 |
| 26 | USAP（Uncached App Process）启动机制 | Ch01, Ch03 | Android 10+ / 启动优化 |
| 27 | Native 层 Message/Handler/Looper（2篇） | Ch01, Ch03 | 系统源码 / Native 消息 |
| 28 | Android 启动画面（Splash Screen） | Ch01, Ch08 | Android 12+ / 系统特性 |
| 29 | AMS（ActivityManagerService）启动流程 | Ch01 | 系统源码 / 系统服务 |
| 30 | PMS（PackageManagerService）启动流程 | Ch01 | 系统源码 / 包管理 |
| 31 | Zygote 启动与 Fork 流程 | Ch01 | 系统源码 / 进程孵化 |
| 32 | SystemServer 启动流程 | Ch01 | 系统源码 / 系统服务 |
| 33 | ContentProvider 启动与加载 | Ch01 | 系统框架 / 组件 |
| 34 | Service 绑定与启动机制 | Ch01 | 系统框架 / 组件 |
| 35 | BroadcastReceiver 注册与分发 | Ch01 | 系统框架 / 组件 |

## 8. 稳定性（→ Ch09 + Ch10）

| # | 资源名称 | 映射 AIW 章节 | 备注（来源/类型） |
|---|---------|-------------|-----------------|
| 1 | Android ANR 原理解析 | Ch09 | 系统源码 / ANR 机制 |
| 2 | 彻底理解 Android 无响应（ANR） | Ch09 | 技术分析 / ANR |
| 3 | Android 稳定性优化系列（7篇） | Ch09, Ch10 | 综合实践 / 稳定性体系 |
| 4 | Android 进程名与线程名规范 | Ch09 | 开发规范 / 调试 |
| 5 | ANR/Crash Trace 文件生成机制 | Ch09, Ch13 | 系统源码 / 调试 |
| 6 | FP（Frame Pointer）栈回溯原理 | Ch09, Ch10 | 底层技术 / 崩溃分析 |
| 7 | 资源溢出导致崩溃分析 | Ch09, Ch10 | 实战案例 / 崩溃 |
| 8 | 字节 NativeCrash 治理实践 | Ch09, Ch10 | 字节跳动 / 大厂实践 |
| 9 | 西瓜视频稳定性优化系列（3篇） | Ch09, Ch10 | 字节跳动 / 大厂实践 |
| 10 | 西瓜视频 ANR 优化实践 | Ch09 | 字节跳动 / 大厂实践 |
| 11 | 今日头条 ANR 实践系列（5篇） | Ch09 | 字节跳动 / 大厂实践 |
| 12 | Fastbot 稳定性测试工具 | Ch09, 15.5 | 字节跳动 / 开源工具 |
| 13 | 线上故障分析与定位 | Ch09, Ch10, 15.5 | 方法论 / 线上运维 |
| 14 | Android Tombstone 分析 | Ch09, Ch10 | 系统工具 / 崩溃分析 |
| 15 | Crash 防护与兜底方案 | Ch09, Ch10 | 实践方案 / 稳定性 |

## 9. 功耗（→ Ch11）

| # | 资源名称 | 映射 AIW 章节 | 备注（来源/类型） |
|---|---------|-------------|-----------------|
| 1 | EAS（Energy Aware Scheduling）调度器 | Ch11, 5.1 | Linux 内核 / 调度器 |
| 2 | Android 功耗改进历程 | Ch11 | Google 官方 / 系统优化 |
| 3 | ProMotion 自适应刷新率技术分析 | Ch11, Ch02 | Apple/显示技术 / 功耗 |

## 10. 进程管理（→ 1.3 + 5.1）

| # | 资源名称 | 映射 AIW 章节 | 备注（来源/类型） |
|---|---------|-------------|-----------------|
| 1 | Android cpuset 机制 | 1.3, 5.1 | Linux 内核 / CPU 分组 |
| 2 | Android cgroup 使用 | 1.3, 5.1 | Linux 内核 / 控制组 |
| 3 | Android ADJ 算法（进程优先级） | 1.3, 5.1 | 系统机制 / 进程调度 |
| 4 | Linux 进程管理基础 | 5.1 | Linux 内核 / 进程管理 |
| 5 | Android 进程管理系列（4篇） | 1.3, 5.1 | 系统源码 / 进程管理 |
| 6 | Android init 进程启动流程 | 1.3 | 系统源码 / 启动 |
| 7 | Android 进程保活方案 | 1.3 | 开发实践 / 进程 |
| 8 | 通过线程提升性能 | 5.1 | 方法论 / 多线程 |
| 9 | 进程优先级 ADJ 详解 | 1.3, 5.1 | 系统机制 / 优先级 |
| 10 | 线程优先级与调度策略 | 5.1 | Linux 内核 / 线程调度 |
| 11 | Android 进程生命周期 | 1.3 | 系统框架 / 进程管理 |

## 11. IO（→ Ch06）

| # | 资源名称 | 映射 AIW 章节 | 备注（来源/类型） |
|---|---------|-------------|-----------------|
| 1 | Android IO 监控与优化 | Ch06 | 实践方案 / IO 优化 |
| 2 | Linux 内核文件系统读写原理 | Ch06 | Linux 内核 / 文件系统 |
| 3 | mmap 原理与应用 | Ch06 | Linux 系统 / 内存映射 |
| 4 | Android IO 监控方案（Matrix IOCanary） | Ch06, 14.5 | 腾讯 Matrix / 开源工具 |

## 12. 调试工具（→ Ch13 + Ch14）

| # | 资源名称 | 映射 AIW 章节 | 备注（来源/类型） |
|---|---------|-------------|-----------------|
| 1 | Simpleperf 使用指南 | Ch13 | Google 官方 / 性能采样 |
| 2 | 调试 Android Framework | Ch13 | 开发者指南 / 系统调试 |
| 3 | 调试 Android Native Framework | Ch13 | 开发者指南 / Native 调试 |
| 4 | Catapult（Systrace 前端） | Ch13 | Chrome 开源 / Trace 可视化 |
| 5 | 手把手教你用 Systrace（2篇） | Ch13 | 技术博客 / 工具教程 |
| 6 | Systrace 基础知识系列（12篇） | Ch13 | 高爷原创 / 工具系列 |
| 7 | Systrace 流畅性实战系列（3篇） | Ch13, Ch07 | 高爷原创 / 实战系列 |
| 8 | Systrace 响应速度实战系列（3篇） | Ch13, Ch08 | 高爷原创 / 实战系列 |
| 9 | 线程 CPU 运行状态分析系列（3篇） | Ch13 | 高爷原创 / 性能分析 |
| 10 | Tracing Window Transitions | Ch13 | Google 官方 / 窗口动画 |
| 11 | Android bugreport 分析方法 | Ch13 | 系统工具 / 问题排查 |
| 12 | Matrix 源码解析系列（6篇） | Ch14 | 腾讯 Matrix / 开源工具 |
| 13 | PerfettoViewer 使用指南 | Ch13 | Google 官方 / Trace 可视化 |
| 14 | Android 性能分析工具介绍 | Ch13 | 综合介绍 / 工具概览 |
| 15 | Perfetto SQL 查询入门 | Ch13 | Google 官方 / Trace 分析 |
| 16 | Android Studio Profiler 使用 | Ch13 | Google 官方 / IDE 工具 |
| 17 | Memory Profiler 使用技巧 | Ch13, Ch04 | Google 官方 / 内存分析 |
| 18 | CPU Profiler 使用技巧 | Ch13 | Google 官方 / CPU 分析 |
| 19 | Network Profiler 使用技巧 | Ch13 | Google 官方 / 网络分析 |
| 20 | Layout Inspector 调试布局 | Ch13, Ch02 | Google 官方 / UI 调试 |
| 21 | GAPID（Graphics API Debugger） | Ch13, Ch02 | Google 开源 / 图形调试 |
| 22 | RenderDoc 图形调试 | Ch13, Ch02 | 开源工具 / 图形调试 |
| 23 | Android Studio Debugger（Native） | Ch13 | Google 官方 / Native 调试 |
| 24 | LeakCanary 内存泄漏检测 | Ch14, Ch04 | Square 开源 / 内存工具 |
| 25 | StrictMode 使用指南 | Ch13 | Google 官方 / 开发者工具 |
| 26 | systrace 命令行参数详解 | Ch13 | 工具文档 / 使用指南 |
| 27 | adb shell dumpsys 详解 | Ch13 | 系统工具 / 调试命令 |
| 28 | top/htop 与进程监控 | Ch13 | Linux 工具 / 进程分析 |
| 29 | strace 系统调用追踪 | Ch13 | Linux 工具 / 系统调用 |
| 30 | valgrind 内存检测 | Ch13, Ch04 | 开源工具 / 内存检测 |

## 13. 硬件相关（→ 5.3 + Ch02）

| # | 资源名称 | 映射 AIW 章节 | 备注（来源/类型） |
|---|---------|-------------|-----------------|
| 1 | Flash Wear（闪存磨损）对性能影响 | 5.3 | 硬件知识 / 存储 |
| 2 | Cortex-A75/A55 架构分析 | 5.3, Ch02 | ARM 架构 / CPU 设计 |
| 3 | CPU Utilization is Wrong | 5.3 | Brendan Gregg / 性能分析方法论 |

## 14. 编程语言（→ 8.6 + 1.7）

| # | 资源名称 | 映射 AIW 章节 | 备注（来源/类型） |
|---|---------|-------------|-----------------|
| 1 | Java 隐藏开销（Hidden Costs） | 8.6, 1.7 | 技术分析 / 性能陷阱 |
| 2 | Kotlin 官方文档 | 8.6 | JetBrains 官方 / 语言 |
| 3 | Kotlin Coroutines 系列（6篇） | 8.6 | 技术博客 / 协程 |
| 4 | Java 引用类型原理（Strong/Soft/Weak/Phantom） | 8.6, Ch04 | Java 机制 / 引用 |
| 5 | Kotlin 协程作用域与生命周期 | 8.6 | Kotlin / 协程 |
| 6 | Kotlin Continuation 原理 | 8.6 | Kotlin / 协程实现 |
| 7 | Android Architecture Pattern（MVC/MVP/MVVM） | 8.6 | Google 官方 / 架构 |
| 8 | High Performance Kotlin | 8.6 | 技术博客 / Kotlin 性能 |

## 15. Linux（→ 5.1 + 6.2 + 4.2）

| # | 资源名称 | 映射 AIW 章节 | 备注（来源/类型） |
|---|---------|-------------|-----------------|
| 1 | Regmap 框架（寄存器映射） | 5.1 | Linux 内核 / 驱动框架 |
| 2 | 嵌入式 Linux 启动优化 | 5.1, Ch08 | Linux 系统 / 启动 |
| 3 | Linux 文件系统预读机制 | 6.2 | Linux 内核 / 文件系统 |
| 4 | blktrace 使用与块设备分析 | 6.2, Ch13 | Linux 工具 / IO 分析 |
| 5 | Linux 系统调用原理 | 5.1 | Linux 内核 / 系统调用 |
| 6 | 浅墨 Linux IO 系列（3篇） | 6.2 | 技术博客 / IO 原理 |
| 7 | Linux Deadline 调度器（2篇） | 6.2 | Linux 内核 / IO 调度 |
| 8 | Linux 内存模型详解 | 4.2, Ch04 | Linux 内核 / 内存管理 |
| 9 | Linux CFS 调度器系列（6篇） | 5.1 | Linux 内核 / CPU 调度 |
| 10 | Linux 线程 IO 模型 | 6.2, 5.1 | Linux 系统 / IO 模型 |
| 11 | Linux 进程调度策略对比 | 5.1 | Linux 内核 / 调度 |
| 12 | Linux 中断与软中断机制 | 5.1 | Linux 内核 / 中断 |
| 13 | Linux 定时器与时钟源 | 5.1 | Linux 内核 / 定时 |
| 14 | Linux 虚拟文件系统（VFS） | 6.2 | Linux 内核 / 文件系统 |
| 15 | Linux 页缓存（Page Cache） | 6.2 | Linux 内核 / 缓存 |
| 16 | Linux 写回机制（Writeback） | 6.2 | Linux 内核 / IO |
| 17 | Linux 内存分配器（slab/slub） | 4.2 | Linux 内核 / 内存管理 |
| 18 | Linux eBPF 性能分析 | 5.1, Ch13 | Linux 内核 / 新工具 |

---

## 统计汇总

| 分类 | 资源数 | 主要映射章节 |
|-----|-------|------------|
| 1. 优化心得与经验 | 17 | 15.1, 14.5, 15.5 |
| 2. 响应速度 | 14 | Ch08 |
| 3. 流畅度 | 20 | Ch07 |
| 4. 内存 | 30 | Ch04, Ch10 |
| 5. 图形栈 | 25 | Ch02 |
| 6. 虚拟机 | 22 | 1.7, 4.3, 4.8 |
| 7. 系统框架 | 35 | Ch01, Ch03 |
| 8. 稳定性 | 15 | Ch09, Ch10 |
| 9. 功耗 | 3 | Ch11 |
| 10. 进程管理 | 11 | 1.3, 5.1 |
| 11. IO | 4 | Ch06 |
| 12. 调试工具 | 30 | Ch13, Ch14 |
| 13. 硬件相关 | 3 | 5.3, Ch02 |
| 14. 编程语言 | 8 | 8.6, 1.7 |
| 15. Linux | 18 | 5.1, 6.2, 4.2 |
| **合计** | **255** | — |

## 使用说明

本资源索引是 AIW（Android Internal Wiki）各章节加工时的**参考书目**，使用时遵循以下优先级：

### 加工优先级

1. **高爷原创条目**（最高优先级）：高爷基于自身工作经验撰写的原创分析文章，如 Systrace 基础知识系列（12篇）、流畅性/响应速度实战系列、卡顿分析系列（方法论/系统篇/应用篇）、内存优化建议系列等。这些条目含有一手经验和独特见解，应完整提取知识点。

2. **Google 官方文档**（高优先级）：Android 官方开发者文档、Google I/O 演讲、Android 源码文档。这些是权威参考资料，提取标准做法和官方建议。

3. **大厂实践案例**（中优先级）：字节跳动、腾讯、美团、爱奇艺、支付宝等一线厂商的技术博客。提取具体的优化策略、数据指标和解决方案思路。

4. **第三方技术博客**（参考级）：个人技术博客、教程文章。仅提取事实性知识点和方法论，用 AIW 自己的语言重述，不搬运原文。

### 融入原则

- **绝不直接搬运**：所有内容必须用 AIW 的语言重述
- **标注原始出处**：每条融入的知识点标注来自哪个资源
- **交叉引用**：当多个资源涉及同一知识点时，交叉对比取最优解
- **保持时效性**：优先采用最新版本的信息，过时内容标注版本差异
