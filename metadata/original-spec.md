# Android Internals & Performance 知识体系项目方案

> 历史基线：本文保留项目初始方案与早期 17 章素材映射，不作为当前目录或统计口径。当前 5 部分、26 章架构以 [`v1.0-definition.md`](v1.0-definition.md) 和 [`../src/SUMMARY.md`](../src/SUMMARY.md) 为准。

## 一、项目定位

**一句话定义**：一本由 AI 辅助持续进化的 Android 系统与性能技术百科，面向有经验的 Android 开发者和系统工程师，追求深度、准确、可追溯。

**与市面上的书的核心区别**：
- Jonathan Levin 的 *Android Internals* 偏系统底层（bootloader、init、native daemon），不聚焦性能
- Google 官方文档偏 API 指南，缺乏系统层视角和实战案例
- 市面上的性能优化书（腾讯 TMQ、张绍文课程等）多成书于 2016-2019，Android 10 之前，大量内容已过时
- 本项目的独特价值：**跨层（App → Framework → Kernel）**、**按 Android 版本持续更新**、**每个知识点标注验证状态和适用版本**、**源码级引用可追溯**

---

## 二、完整大纲

```
Android Internals & Performance
├── 写在前面
│   ├── 本书的使用方式（不是从头读到尾，而是按问题查阅）
│   ├── 适用读者（有 1-2 年 Android 开发经验，或系统工程师）
│   ├── 内容验证标准说明（每个知识点的验证状态含义）
│   └── 版本约定（标注适用的 Android 版本范围）
│
├── 第一部分：Android 系统运行机制
│   │
│   ├── 第 1 章：系统架构全景
│   │   ├── 1.1 Android 分层架构（App / Framework / Native / HAL / Kernel）
│   │   ├── 1.2 系统启动全流程（Bootloader → Kernel → Init → Zygote → SystemServer → Launcher）
│   │   ├── 1.3 进程模型与生命周期管理（AMS、进程优先级、adj 机制）
│   │   ├── 1.4 Binder IPC 机制与性能影响
│   │   │   ├── Binder 架构与通信流程
│   │   │   ├── Binder 线程池与性能瓶颈
│   │   │   ├── oneway 与同步调用的性能差异
│   │   │   └── AIDL 与 Binder 在 Perfetto 中的表现
│   │   ├── 1.5 线程模型
│   │   │   ├── 主线程（UI Thread）运行原理
│   │   │   ├── Message / Handler / MessageQueue / Looper 机制
│   │   │   ├── Android 17 DeliQueue：lock-free MessageQueue 的设计与影响
│   │   │   ├── HandlerThread / IntentService / 线程池最佳实践
│   │   │   └── 线程优先级与调度策略（nice / cgroup / SCHED_FIFO）
│   │   └── 1.6 Android 版本演进中的架构变化
│   │       ├── Project Treble（Android 8）
│   │       ├── Project Mainline / APEX（Android 10+）
│   │       ├── ART 模块化更新（Android 12+）
│   │       └── GKI（Generic Kernel Image）的意义
│   │
│   ├── 第 2 章：渲染系统
│   │   ├── 2.1 Android 渲染架构全景
│   │   │   ├── 从 View.invalidate() 到屏幕像素的完整链路
│   │   │   └── 软件渲染 vs 硬件加速渲染
│   │   ├── 2.2 帧率与刷新率
│   │   │   ├── 为什么是 60fps / 90fps / 120fps
│   │   │   ├── 可变刷新率（VRR）与 LTPO
│   │   │   └── 高刷新率对性能和功耗的影响
│   │   ├── 2.3 VSync 机制
│   │   │   ├── VSync 信号的产生与分发
│   │   │   ├── VSync offset 的设计
│   │   │   └── VSync 在 Perfetto 中的解读
│   │   ├── 2.4 Choreographer 与渲染流水线
│   │   │   ├── Choreographer 的工作原理
│   │   │   ├── CALLBACK_INPUT → TRAVERSAL → COMMIT 的执行顺序
│   │   │   ├── doFrame 的时序分析
│   │   │   └── Choreographer 在 Perfetto 中的表现
│   │   ├── 2.5 MainThread 与 RenderThread 协作
│   │   │   ├── MainThread 的 measure / layout / draw
│   │   │   ├── RenderThread 的 GPU 渲染流程
│   │   │   ├── sync 阶段的含义与优化
│   │   │   └── hwui 渲染管线详解
│   │   ├── 2.6 SurfaceFlinger 与合成
│   │   │   ├── SurfaceFlinger 架构与工作流
│   │   │   ├── BufferQueue / Surface / Layer 的关系
│   │   │   ├── BlastBufferQueue 机制（Android 12+）
│   │   │   ├── GPU 合成 vs HWC Overlay
│   │   │   ├── Triple Buffer 的设计与影响
│   │   │   └── SurfaceFlinger 在 Perfetto 中的解读
│   │   ├── 2.7 Hardware Layer
│   │   │   ├── Hardware Layer 的原理与使用场景
│   │   │   ├── 动画中的 Hardware Layer 优化
│   │   │   └── Hardware Layer 的内存代价
│   │   ├── 2.8 过度绘制（Overdraw）
│   │   │   ├── 过度绘制的原理
│   │   │   ├── 检测方法与工具
│   │   │   └── 优化策略与实战
│   │   └── 2.9 渲染机制的版本演进
│   │       ├── RenderScript → Vulkan 的迁移
│   │       ├── FrameTimeline（Android 12+）
│   │       └── 各版本渲染行为变化汇总
│   │
│   ├── 第 3 章：输入系统
│   │   ├── 3.1 Input 事件分发全流程
│   │   │   ├── 从触摸屏硬件到 InputDispatcher
│   │   │   ├── InputReader → InputDispatcher → App 的完整链路
│   │   │   └── Input 事件在 Perfetto 中的解读
│   │   ├── 3.2 触摸响应的性能分析
│   │   │   ├── 触摸到屏幕响应的延迟构成
│   │   │   ├── Input ANR 的触发条件
│   │   │   └── 输入延迟优化手段
│   │   └── 3.3 手势导航与系统交互
│   │       ├── 系统手势的 Input 处理流程
│   │       └── 手势冲突与优先级
│   │
│   ├── 第 4 章：内存管理
│   │   ├── 4.1 Android 内存模型全景
│   │   │   ├── 虚拟内存 / 物理内存 / 页表
│   │   │   ├── Java Heap / Native Heap / Stack / mmap
│   │   │   ├── GPU 内存 / dmabuf / ION（→ DMA-BUF Heap）
│   │   │   └── 各内存区域在 dumpsys meminfo 中的对应
│   │   ├── 4.2 Linux 内核内存管理
│   │   │   ├── 伙伴系统（Buddy System）
│   │   │   ├── Slab 分配器
│   │   │   ├── 页面回收与 kswapd / direct reclaim
│   │   │   ├── CMA（Contiguous Memory Allocator）
│   │   │   ├── ZRAM 与压缩内存
│   │   │   └── cgroup 内存控制
│   │   ├── 4.3 ART 虚拟机内存管理
│   │   │   ├── ART 堆结构（RegionSpace、LargeObjectSpace 等）
│   │   │   ├── GC 策略与演进（CMS → CC → Generational CC）
│   │   │   ├── Android 17 Generational GC 的设计
│   │   │   ├── JIT / AOT / Baseline Profile 对内存的影响
│   │   │   └── ART 通过 Google Play System Updates 的演进
│   │   ├── 4.4 Low Memory Killer
│   │   │   ├── 传统 LMK → lmkd → 现代 lmkd 的演进
│   │   │   ├── oom_adj / oom_score_adj 的含义与计算
│   │   │   ├── PSI（Pressure Stall Information）驱动的杀进程策略
│   │   │   └── 各厂商的 LMK 定制
│   │   ├── 4.5 App 内存优化
│   │   │   ├── 内存泄漏的常见模式与检测
│   │   │   ├── Bitmap 内存管理与优化
│   │   │   ├── 相机场景的内存优化
│   │   │   ├── onTrimMemory 回调的正确使用
│   │   │   └── 大型 App 的内存治理策略
│   │   └── 4.6 内存相关的版本演进
│   │       ├── 各版本内存机制变化汇总
│   │       └── LPDDR4 → LPDDR5 → LPDDR5X 对系统行为的影响
│   │
│   ├── 第 5 章：CPU 调度与能耗管理
│   │   ├── 5.1 Linux 进程调度基础
│   │   │   ├── CFS（Completely Fair Scheduler）原理
│   │   │   ├── 实时调度策略（SCHED_FIFO / SCHED_RR）
│   │   │   ├── 调度延迟与 runqueue
│   │   │   └── 线程状态在 Perfetto 中的解读（Running / Runnable / Sleep / Uninterruptible Sleep）
│   │   ├── 5.2 EAS（Energy Aware Scheduling）
│   │   │   ├── EAS 的设计思想
│   │   │   ├── CPU capacity / utilization / energy model
│   │   │   ├── task placement 决策逻辑
│   │   │   └── uclamp（util clamping）机制
│   │   ├── 5.3 大小核架构
│   │   │   ├── big.LITTLE / DynamIQ 架构
│   │   │   ├── 大小核调度策略与性能影响
│   │   │   └── 各 SoC 的核心架构对比（高通 / MTK / 三星 / 联发科）
│   │   ├── 5.4 DVFS 与功耗管理
│   │   │   ├── CPUFreq governor 机制
│   │   │   ├── schedutil governor 详解
│   │   │   ├── 频率与功耗的非线性关系
│   │   │   └── GPU DVFS
│   │   ├── 5.5 Thermal 管控
│   │   │   ├── Thermal framework 架构
│   │   │   ├── 降频策略与用户体验的关系
│   │   │   └── 各厂商的 Thermal 定制
│   │   ├── 5.6 Android 功耗管理
│   │   │   ├── Doze / App Standby / App Standby Buckets
│   │   │   ├── WakeLock 机制与滥用检测
│   │   │   ├── 链式唤醒问题
│   │   │   ├── 后台限制策略的演进
│   │   │   └── Battery Historian 与功耗分析
│   │   └── 5.7 CPU 相关的版本演进
│   │       ├── AutoFDO 对 Android Kernel 的优化（Android 17）
│   │       └── 各版本调度与功耗策略变化
│   │
│   └── 第 6 章：存储与 I/O
│       ├── 6.1 Android 存储架构
│       │   ├── 分区布局（super / userdata / metadata）
│       │   ├── 虚拟 A/B 分区与 OTA
│       │   └── Scoped Storage 的设计与性能影响
│       ├── 6.2 文件系统
│       │   ├── F2FS 设计思想与性能特性
│       │   ├── EXT4 vs F2FS 对比
│       │   └── EROFS（只读分区文件系统）
│       ├── 6.3 I/O 调度与性能
│       │   ├── I/O 调度器（BFQ / mq-deadline）
│       │   ├── UFS / eMMC 性能特性
│       │   └── I/O 竞争导致的性能问题分析
│       └── 6.4 存储相关的版本演进
│
├── 第二部分：性能专题
│   │
│   ├── 第 7 章：流畅性（Smoothness）
│   │   ├── 7.1 卡顿的定义与分类
│   │   │   ├── 用户视角 / 开发视角 / 测试视角的定义差异
│   │   │   ├── 广义流畅性：卡顿 + 响应慢 + ANR
│   │   │   └── 帧率 / 帧时间 / Jank 的精确定义
│   │   ├── 7.2 卡顿原因体系
│   │   │   ├── 应用层原因（主线程阻塞、过度布局、不当动画）
│   │   │   ├── 系统层原因（SurfaceFlinger 负载、系统服务繁忙）
│   │   │   ├── 资源竞争原因（低内存、CPU 抢占、I/O 竞争）
│   │   │   └── 硬件层原因（GPU 瓶颈、Thermal 降频）
│   │   ├── 7.3 卡顿分析方法论
│   │   │   ├── 系统化的分析思路（自顶向下 vs 自底向上）
│   │   │   ├── 复现策略
│   │   │   └── 从 Trace 定位到根因的完整流程
│   │   ├── 7.4 典型场景分析
│   │   │   ├── 列表滑动卡顿分析
│   │   │   ├── 页面切换卡顿分析
│   │   │   ├── 动画卡顿分析
│   │   │   ├── 后台无效动画
│   │   │   └── 系统 UI 卡顿（桌面、通知栏、Recent）
│   │   ├── 7.5 优化策略
│   │   │   ├── 布局优化（层级扁平化、ViewStub、merge）
│   │   │   ├── RecyclerView 优化（预加载、DiffUtil、Shared Pool）
│   │   │   ├── 异步加载与线程调度
│   │   │   ├── Compose 性能最佳实践
│   │   │   └── 编码最佳实践 checklist
│   │   └── 7.6 案例集（持续积累）
│   │
│   ├── 第 8 章：响应速度（Responsiveness）
│   │   ├── 8.1 响应速度原理
│   │   │   ├── 用户操作到屏幕响应的时间构成
│   │   │   ├── 冷启动 / 温启动 / 热启动的区别
│   │   │   └── TTID / TTFD / reportFullyDrawn 指标
│   │   ├── 8.2 App 启动全流程
│   │   │   ├── 从 Intent 到 Activity.onCreate 的完整链路
│   │   │   ├── Zygote fork / 进程创建
│   │   │   ├── Application.onCreate / ContentProvider
│   │   │   ├── Activity 生命周期与首帧渲染
│   │   │   └── StartingWindow（Splash Screen）机制
│   │   ├── 8.3 启动优化策略
│   │   │   ├── 延迟初始化（DelayLoad 实现与原理）
│   │   │   ├── Baseline Profile / Startup Profile / DEX 布局优化
│   │   │   ├── R8 全模式优化
│   │   │   ├── 异步初始化与依赖管理
│   │   │   └── App Performance Score（Google 官方框架）
│   │   ├── 8.4 其他响应速度场景
│   │   │   ├── Activity 切换速度
│   │   │   ├── 点击响应速度
│   │   │   └── 系统级响应（解锁、截屏、分屏）
│   │   └── 8.5 案例集（持续积累）
│   │
│   ├── 第 9 章：ANR
│   │   ├── 9.1 ANR 设计思想
│   │   │   ├── 为什么需要 ANR 机制
│   │   │   ├── ANR 的本质：看门狗定时器
│   │   │   └── ANR 与"卡顿"的区别
│   │   ├── 9.2 ANR 类型与触发条件
│   │   │   ├── Input ANR（5s）
│   │   │   ├── Broadcast ANR（前台 10s / 后台 60s）
│   │   │   ├── Service ANR（前台 20s / 后台 200s）
│   │   │   ├── ContentProvider ANR
│   │   │   └── 各类型的超时计算逻辑
│   │   ├── 9.3 ANR 分析方法
│   │   │   ├── ANR 日志结构与关键字段
│   │   │   ├── traces.txt 解读
│   │   │   ├── 从 Log / Trace 定位 ANR 根因
│   │   │   ├── Binder 调用导致的 ANR
│   │   │   ├── 锁竞争导致的 ANR
│   │   │   └── 系统负载导致的 ANR（CPU / IO / 内存）
│   │   ├── 9.4 特殊场景的 ANR
│   │   │   ├── 无障碍服务导致的系统卡顿与 ANR
│   │   │   └── 多进程 App 的 ANR 分析
│   │   └── 9.5 案例集（持续积累）
│   │
│   ├── 第 10 章：内存性能
│   │   ├── 10.1 App 内存分析
│   │   │   ├── 如何准确衡量 App 内存占用
│   │   │   ├── PSS / RSS / USS / Swap 的含义
│   │   │   └── dumpsys meminfo 深度解读
│   │   ├── 10.2 内存泄漏
│   │   │   ├── Java 内存泄漏的常见模式
│   │   │   ├── Native 内存泄漏
│   │   │   ├── MAT 使用（入门 → 进阶 → Bitmap 原图查看）
│   │   │   ├── LeakCanary / KOOM 工作原理
│   │   │   └── 线上内存泄漏监控
│   │   ├── 10.3 内存持续增长
│   │   │   ├── 增长模式识别
│   │   │   ├── 碎片化与虚拟地址空间耗尽
│   │   │   └── 长期运行场景的内存分析
│   │   ├── 10.4 低内存对系统性能的影响
│   │   │   ├── 低内存导致卡顿的机制
│   │   │   ├── kswapd 风暴与 direct reclaim
│   │   │   ├── 进程被杀与重启的恶性循环
│   │   │   └── "系统不释放内存"的真相
│   │   └── 10.5 案例集（持续积累）
│   │
│   ├── 第 11 章：功耗
│   │   ├── 11.1 Android 功耗模型
│   │   │   ├── power_profile.xml 与功耗估算
│   │   │   ├── 各子系统的功耗构成（CPU / GPU / Display / Radio / Sensor）
│   │   │   └── 功耗测量方法
│   │   ├── 11.2 App 耗电优化
│   │   │   ├── WakeLock 最佳实践
│   │   │   ├── JobScheduler / WorkManager 的正确使用
│   │   │   ├── 后台位置访问的功耗影响
│   │   │   ├── Excessive Wake Lock 指标（Android Vitals）
│   │   │   └── 编码最佳实践 checklist
│   │   ├── 11.3 系统级功耗优化
│   │   │   ├── Doze / App Standby / Buckets 的分层策略
│   │   │   ├── Restricted Standby Bucket
│   │   │   └── 各厂商的后台管控策略差异
│   │   └── 11.4 案例集（持续积累）
│   │
│   └── 第 12 章：包体积与其他
│       ├── 12.1 APK 体积优化
│       │   ├── R8 / ProGuard 优化
│       │   ├── 资源优化策略
│       │   ├── App Bundle 与按需分发
│       │   └── So 库优化
│       └── 12.2 网络性能优化
│           ├── 网络请求优化策略
│           └── 弱网与网络切换场景
│
├── 第三部分：工具与方法论
│   │
│   ├── 第 13 章：Perfetto（核心工具，大篇幅）
│   │   ├── 13.1 Perfetto 简介与演进（Systrace → Perfetto）
│   │   ├── 13.2 Trace 抓取
│   │   │   ├── UI 抓取 / 命令行抓取 / 代码埋点
│   │   │   ├── TraceConfig 详解与模板
│   │   │   └── 抓取大 Trace 的技巧
│   │   ├── 13.3 Perfetto View 解读
│   │   │   ├── 界面布局与导航
│   │   │   ├── Track 类型详解
│   │   │   └── SQL 查询的使用
│   │   ├── 13.4 命令行打开超大 Trace
│   │   ├── 13.5 专题解读
│   │   │   ├── CPU 信息解读
│   │   │   ├── Choreographer 渲染流程
│   │   │   ├── MainThread / RenderThread
│   │   │   ├── VSync 机制
│   │   │   ├── SurfaceFlinger
│   │   │   ├── Input 解读
│   │   │   ├── Binder 与锁竞争
│   │   │   └── Triple Buffer
│   │   ├── 13.6 线程 CPU 状态分析
│   │   │   ├── Running 状态分析
│   │   │   ├── Runnable 状态分析
│   │   │   └── Sleep / Uninterruptible Sleep 分析
│   │   └── 13.7 Perfetto 的高级用法
│   │       ├── 自定义 Trace 事件
│   │       ├── Metric 与自动化分析
│   │       └── Perfetto + CI/CD 集成
│   │
│   ├── 第 14 章：其他分析工具
│   │   ├── 14.1 Android Studio Profiler
│   │   │   ├── CPU Profiler（采样 vs 插桩）
│   │   │   ├── Memory Profiler
│   │   │   ├── Network Profiler
│   │   │   └── Energy Profiler
│   │   ├── 14.2 Simpleperf
│   │   │   ├── Simpleperf 原理与使用
│   │   │   ├── ARM PMU 事件
│   │   │   ├── 火焰图生成与解读
│   │   │   └── Simpleperf 与 Perfetto 的配合
│   │   ├── 14.3 内存分析工具
│   │   │   ├── MAT（Memory Analyzer Tool）入门 → 进阶
│   │   │   ├── MAT 中查看 Bitmap 原图
│   │   │   ├── Allocation Tracker
│   │   │   └── KOOM / Matrix 内存监控原理
│   │   ├── 14.4 dumpsys 系列命令
│   │   │   ├── dumpsys meminfo / gfxinfo / cpuinfo
│   │   │   ├── dumpsys SurfaceFlinger
│   │   │   ├── dumpsys activity / input / window
│   │   │   └── dumpsys batterystats
│   │   ├── 14.5 三方性能库
│   │   │   ├── Matrix（微信）
│   │   │   ├── KOOM（快手）
│   │   │   ├── Profilo（Facebook）
│   │   │   ├── BlockCanary / LeakCanary
│   │   │   ├── Benchmark / Macrobenchmark 库
│   │   │   ├── JankStats 库
│   │   │   └── Tailor / Raphael
│   │   ├── 14.6 自动化测试工具
│   │   │   ├── Fastbot / Monkey
│   │   │   ├── UI Automator
│   │   │   └── 自动化性能测试框架搭建
│   │   └── 14.7 ProfilingManager（Android 17 新增）
│   │       ├── 系统触发器类型（COLD_START / OOM / EXCESSIVE_CPU）
│   │       └── 基于触发器的自动化 Profiling
│   │
│   └── 第 15 章：方法论
│       ├── 15.1 性能优化的术、道、器
│       │   ├── 可观测性理论（Log / Metric / Trace 三支柱）
│       │   ├── 数据采集方法（静态 vs 动态、有条件 vs 无条件）
│       │   └── 分析方法（可视化 vs 数据库查询）
│       ├── 15.2 如何区分系统问题和 App 问题
│       │   ├── 判断思路与决策树
│       │   └── 常见误判案例
│       ├── 15.3 性能指标体系
│       │   ├── 核心指标定义（Jank Rate / Startup Time / ANR Rate）
│       │   ├── 侵入式 vs 非侵入式采集
│       │   ├── Google Android Vitals
│       │   ├── App Performance Score 框架
│       │   └── 第三方评测标准（鲁大师、安兔兔等的价值与局限）
│       ├── 15.4 竞品分析方法
│       │   ├── 竞品性能对比框架
│       │   └── 从竞品表现推断优化策略
│       ├── 15.5 线上性能监控
│       │   ├── 线上 vs 线下监控的差异
│       │   ├── 采样策略与性能开销控制
│       │   └── 数据上报与告警
│       ├── 15.6 性能测试最佳实践
│       │   ├── 测试环境标准化
│       │   ├── 性能 Bug 的提报标准
│       │   └── 性能回归检测
│       └── 15.7 AOSP 代码阅读
│           ├── 代码检索工具（cs.android.com / AndroidXRef）
│           ├── AOSP 源码下载与编译
│           ├── 导入 IDE 的技巧（AS / VSCode）
│           └── 画流程图的方法
│
├── 第四部分：系统级优化与行业实践
│   │
│   ├── 第 16 章：AOSP 性能优化
│   │   ├── 16.1 Google 官方的性能优化思路
│   │   │   ├── Performance Leveling Guide（5 级优化路径）
│   │   │   ├── Baseline Profile + Startup Profile
│   │   │   ├── R8 全模式
│   │   │   └── AutoFDO for Android Kernel
│   │   ├── 16.2 各 Android 版本性能变更追踪
│   │   │   ├── Android 10 (Q): Scoped Storage、Bubbles
│   │   │   ├── Android 11 (R): 冻结进程优化
│   │   │   ├── Android 12 (S): SplashScreen、BlastBufferQueue、FrameTimeline
│   │   │   ├── Android 13 (T): 前台服务管理、per-app 语言
│   │   │   ├── Android 14 (U): 应用健康监控
│   │   │   ├── Android 15 (V): 私密空间、部分屏幕共享
│   │   │   ├── Android 16 (Baklava): 自适应布局强制
│   │   │   └── Android 17: lock-free MessageQueue、Generational GC、ProfilingManager
│   │   └── 16.3 AOSP 源码编译与调试环境
│   │
│   └── 第 17 章：厂商优化实践
│       ├── 17.1 OEM 性能优化的通用思路
│       │   ├── 调度优化（核心亲和性、优先级提升）
│       │   ├── 内存优化（杀进程策略、压缩策略）
│       │   ├── 渲染优化（帧率控制、优先渲染）
│       │   └── 编译优化（PGO、LTO）
│       ├── 17.2 SoC 平台差异
│       │   ├── 高通（Snapdragon）平台特性
│       │   ├── 联发科（Dimensity）平台特性
│       │   ├── 三星（Exynos）平台特性
│       │   └── 各平台 Perfetto 特有 Track
│       └── 17.3 行业案例
│           ├── 华为微博体验优化分析
│           ├── 三星闰字重启事件分析
│           └── 更多案例（持续积累）
│
└── 附录
    ├── A. Android 版本性能变更速查表（按版本 × 领域矩阵）
    ├── B. 常用 adb / dumpsys 命令速查
    ├── C. Perfetto TraceConfig 模板集
    ├── D. 性能分析 Checklist（卡顿 / 启动 / ANR / 内存 / 功耗）
    ├── E. 术语表（中英对照）
    └── F. 推荐阅读与资源
```

---

## 三、每个知识点的元数据标准

每篇内容的头部必须包含以下元数据：

```yaml
---
title: "VSync 机制深入解读"
chapter: "2.3"
status: verified | draft | needs-review | outdated
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-03-28"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high | medium | low
sources:
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/VsyncSchedule.cpp"
    branch: "android-17.0.0_r1"
  - type: blog
    url: "https://androidperformance.com/2019/12/01/Android-Systrace-Vsync/"
    author: "Gracker"
  - type: official
    url: "https://developer.android.com/topic/performance/vitals/render"
  - type: paper
    title: "..."
    url: "..."
tags: [rendering, vsync, perfetto, surfaceflinger]
related_chapters: ["2.2", "2.4", "2.6"]
---
```

**status 含义**：
- `verified`：内容已通过 AOSP 源码或实际设备验证，可信度高
- `draft`：初稿完成，等待验证
- `needs-review`：需要人工审核（通常是 AI 生成的内容）
- `outdated`：内容存在已知的过时部分，标注了具体哪些部分过时

---

## 四、内容融入策略

关于知识库里的原文怎么处理，这是最关键的设计决策：

**原则：不是搬运，是重新编织**

具体策略分三种情况：

### 情况 1：高爷原创的完整高质量文章（如博客 Perfetto 系列）
- **保留原文的核心表达和观点**，这是你的独特价值
- **重新组织结构**，使其符合书的章节逻辑（原文可能是独立博客，有重复的背景介绍）
- **补充引用和交叉链接**，与其他章节关联
- **添加元数据**，标注适用版本和验证状态
- **在文中标注来源**：`> 本节基于 [原始文章](url)，经过结构调整和内容更新。`

### 情况 2：高爷的笔记和片段
- **提取知识点**，融入对应章节
- **不保留原始结构**，因为笔记结构不适合阅读
- **标注 [来源: obsidian/path/to/note.md]**

### 情况 3：收藏的他人文章
- **绝不直接搬运**
- **只提取事实性知识点和观点**，用自己的语言重述
- **标注原始出处**，让读者可以追溯
- **如果是关键参考，放入章节末尾的"参考资料"列表**

---

## 五、内容验证机制

这是你提到的第 2 点，也是本项目与普通"整理资料"最大的区别。

### 验证层次

**Level 1：AOSP 源码验证（最高可信度）**
- 对于机制类内容（如 VSync 怎么分发、LMK 怎么算 adj），必须能指出对应的 AOSP 源码路径和关键函数
- OpenClaw 通过 `cs.android.com` 或本地 AOSP 源码库验证
- 标注源码分支和版本：`// frameworks/base/core/java/android/os/MessageQueue.java @ android-17.0.0_r1`

**Level 2：实机验证**
- 对于行为类内容（如"XX 条件下系统会 XX"），通过 Perfetto Trace 或 adb 命令验证
- 记录验证环境：设备型号、Android 版本、验证步骤
- 截图或 Trace 片段作为证据

**Level 3：Deep Research 验证**
- 对于更广泛的技术背景（如 Linux 调度器的演进、EAS 的设计思想），通过搜索学术论文、内核文档、LWN.net 文章验证
- 标注参考资料

**Level 4：交叉验证**
- 对于有争议或不确定的内容，搜索多个信息源交叉验证
- 如果不同来源说法不一致，明确标注争议

### 验证不了的怎么办
- 如实标注 `confidence: low` 和 `status: needs-review`
- 在正文中使用 `> ⚠️ 注意：本节内容基于 Android X 验证，在更新版本上的行为可能有变化。`
- 绝不伪装未验证内容为已验证

---

## 六、Git 管理方案

```
android-internals-book/
├── .git/
├── README.md
├── book.toml                 # mdbook 配置
├── CONTRIBUTING.md           # 贡献规范（包括 OpenClaw 的操作规范）
├── CHANGELOG.md              # 变更记录（人工 + OpenClaw 自动记录）
│
├── src/                      # 书的内容（mdbook 源文件）
│   ├── SUMMARY.md            # 目录结构（mdbook 必需）
│   ├── preface/
│   ├── part1-fundamentals/
│   │   ├── ch01-architecture/
│   │   │   ├── 01-overview.md
│   │   │   ├── 02-boot-process.md
│   │   │   └── ...
│   │   ├── ch02-rendering/
│   │   └── ...
│   ├── part2-performance/
│   ├── part3-tools/
│   ├── part4-system/
│   └── appendix/
│
├── evidence/                 # 验证证据
│   ├── traces/               # Perfetto Trace 片段
│   ├── screenshots/          # 截图
│   └── code-refs/            # AOSP 源码引用快照
│
├── staging/                  # OpenClaw 的工作区（草稿在这里）
│   ├── drafts/               # 加工中的草稿
│   ├── pending-review/       # 等待高爷 review 的内容
│   └── rejected/             # 被驳回的内容（含驳回理由）
│
├── intake/                   # 外部输入（对应你第 3 点的需求）
│   ├── external-outlines/    # 外部提供的目录结构
│   ├── external-resources/   # 外部提供的资料
│   └── suggestions.md        # 高爷的指示和优先级调整
│
├── metadata/                 # 项目元数据
│   ├── inventory.json        # 资产清单
│   ├── progress.json         # 进度追踪
│   ├── freshness-log.json    # 时效性巡检记录
│   └── verification-log.json # 验证记录
│
└── scripts/                  # 辅助脚本
    ├── check-metadata.py     # 检查所有章节是否有完整元数据
    ├── progress-report.py    # 生成进度报告
    └── freshness-check.py    # 时效性检查辅助脚本
```

### Git 工作流

- **OpenClaw 的所有改动先提交到 staging/**，不直接修改 src/
- **OpenClaw 每次改动用规范化的 commit message**：
  ```
  [openclaw] draft: ch02.3 VSync 机制初稿
  [openclaw] verify: ch01.5 确认 DeliQueue 源码路径
  [openclaw] fix: ch09.2 更新 ANR 超时数值（Android 17 变更）
  [openclaw] intake: 处理 external-resources/xxx.pdf
  ```
- **高爷 review 后手动 merge 到 src/**，commit message：
  ```
  [review] approve: ch02.3 VSync 机制 — 已审核通过
  [review] reject: ch05.2 EAS 部分不准确 — 需要重新验证
  ```
- **每周自动生成 CHANGELOG 条目**

---

## 七、外部干涉机制

对应你的第 3 点需求。

### intake/ 目录的使用

你随时可以往 intake/ 目录放东西：

**intake/external-outlines/**
放一个 .md 文件，比如：
```markdown
# 建议：第 2 章增加 HWUI Pipeline 详解
## 来源：某技术分享 / 自己的想法
## 建议位置：2.5 之后
## 参考资料：[链接]
```
OpenClaw 的扫描 task 会检测这个目录，把建议融入加工队列。

**intake/external-resources/**
放 PDF、文章链接列表、或任何原始资料。OpenClaw 会读取并判断属于哪个章节，加入 inventory。

**intake/suggestions.md**
最直接的方式。你直接写指示，比如：
```
- 优先处理第 13 章 Perfetto 部分，把我博客的 Perfetto 系列 1-10 全部加工
- 第 4 章内存部分太弱了，去 deep research 一下 Android 17 的 Generational GC
- 暂停第 12 章，包体积不重要
```
OpenClaw 每次跑 task 前先检查 suggestions.md，据此调整优先级。

---

## 八、OpenClaw Task 设计

### Task 1：知识资产盘点（每日增量）
```
# OpenClaw 知识资产盘点
# cron: 06:00 每日

## 你是谁
你是 OpenClaw，高爷的 AI Agent。你正在执行知识资产盘点任务。

## 本地环境
- Obsidian 根目录：vault/
- 项目目录：projects/android-internals-book/
- 资产清单：{项目目录}/metadata/inventory.json
- 外部输入：{项目目录}/intake/
- Obsidian 落盘：${OBSIDIAN_ROOT}/OpenClaw定时任务/知识资产盘点/YYYY-MM-DD-知识资产盘点.md

## 执行步骤

### Step 1：检查外部输入
先检查 intake/ 目录：
- intake/suggestions.md 是否有新指示？如有，记录并在后续步骤中应用
- intake/external-outlines/ 是否有新增文件？如有，分析建议并记录
- intake/external-resources/ 是否有新增资料？如有，加入待分类队列

### Step 2：增量扫描 Obsidian
扫描自上次盘点以来新增或修改的 .md 文件（通过 mtime 对比上次扫描时间）。
对每篇新文档：
- 提取：标题、字数、最后修改时间、关键词/标签
- 判断来源：高爷原创 / 收藏的他人文章 / 笔记片段
- 映射到大纲章节（可属于多个），标注置信度
- 质量初评：时效性、完整度、可发布度

### Step 3：更新 inventory.json
增量更新资产清单。不要全量覆盖，保留历史记录。

### Step 4：输出盘点报告

## 投递格式（Action 群）

📦 知识资产盘点 | {日期}

📥 外部输入：{suggestions.md 更新/新增资料} 或 无
📊 新增文档：X 篇 | 总文档：X 篇
大纲覆盖：X/17 章有素材

🌟 今日推荐加工（基于优先级和素材质量）
1. {章节} — {文档路径} — {理由}

## 注意事项
- 不读取超大文件全文，前 2000 字足够判断
- 区分高爷原创和收藏文章
- 严禁使用 write/edit 直接写 Obsidian/iCloud 路径
- 先落盘再输出完整报告正文
```

### Task 2：内容加工（每日核心 task）
```
# OpenClaw 知识加工
# cron: 每 4 小时（08:00, 12:00, 16:00, 20:00）

## 你是谁
你是 OpenClaw，高爷的 AI Agent。你正在执行知识加工任务。
你的角色是编辑助理 + 研究员，不是作者。你整理、验证、结构化，但核心技术判断权属于高爷。

## 本地环境
- 项目目录：projects/android-internals-book/
- 资产清单：{项目目录}/metadata/inventory.json
- 加工队列：{项目目录}/metadata/queue.json
- 草稿输出：{项目目录}/staging/drafts/
- 待审核：{项目目录}/staging/pending-review/
- 验证记录：{项目目录}/metadata/verification-log.json
- Obsidian 落盘：${OBSIDIAN_ROOT}/OpenClaw定时任务/知识加工/YYYY-MM-DD-HH-知识加工.md

## 核心原则

### 关于原文融入
- 高爷原创的高质量文章：保留核心表达和观点，重新组织结构以符合章节逻辑，补充引用和交叉链接，添加元数据。在文中标注来源。
- 高爷的笔记片段：提取知识点融入章节，不保留原始结构，标注来源路径。
- 收藏的他人文章：绝不直接搬运，只提取事实性知识点用自己的语言重述，标注原始出处。

### 关于内容验证（每次加工必须执行）
对你加工的每个知识点，按以下层次尽可能验证：

**L1 - AOSP 源码验证**：
- 通过搜索 cs.android.com 或已知的 AOSP 代码路径，确认关键类名、方法名、流程描述是否准确
- 标注源码路径和分支：`frameworks/base/core/java/android/os/Handler.java @ android-17.0.0_r1`

**L2 - 官方文档验证**：
- 查阅 developer.android.com、source.android.com 确认 API 行为、参数、限制
- 查阅 Android Developers Blog 确认官方推荐实践

**L3 - Deep Research 验证**：
- 对于底层机制（Linux 内核、EAS、内存管理），搜索 LWN.net、kernel.org 文档、学术论文
- 对于厂商实践，搜索公开的技术分享和博客

**L4 - 交叉验证**：
- 如果多个来源说法不一致，明确标注争议，不做武断判断

验证结果写入 verification-log.json。

### 加工流程
1. 检查 intake/suggestions.md 是否有优先级调整
2. 从 queue.json 取出最高优先级的待加工项（如队列空，从 inventory.json 选取）
3. 读取原文档，分析核心知识点和适用版本
4. **执行验证**（关键步骤，不可跳过）
5. 生成章节草稿，写入 staging/drafts/{chapter}/{section}.md
6. 草稿必须包含完整的 YAML 元数据头
7. 更新 queue.json 和 progress.json

### 草稿标注规范
- `[已验证: AOSP android-17.0.0_r1, frameworks/base/...]`：已通过源码验证
- `[已验证: 官方文档, developer.android.com/...]`：已通过官方文档验证
- `[待验证]`：内容逻辑上合理但未能验证
- `[待补充]`：内容逻辑上缺失的部分
- `[来源: obsidian/path/to/note.md]`：素材来源
- `[引用: url]`：外部引用
- `[适用版本: Android X - Android Y]`：适用版本范围
- `[争议]`：不同来源说法不一致

### 每次只加工 1 个小节
深度加工一个小节 > 浅处理三个小节。保证每个产出都有验证。

## 投递格式（Action 群）

📝 知识加工 | {日期} {时间}

加工内容：{章节号} {小节名}
素材来源：{路径/URL}
验证结果：L1 ✓ X 处 | L2 ✓ X 处 | 待验证 X 处
产出：staging/drafts/{path}
大纲进度：{已完成小节数}/{总小节数}（{百分比}）

## 注意事项
- 不凭空编造技术细节
- 不改变高爷的技术观点和表述风格
- 遇到无法验证的内容，标注待验证而非跳过
- 严禁使用 write/edit 直接写 Obsidian/iCloud 路径
- 先落盘再输出完整报告正文

## Git 操作
每次加工完成后：
cd {项目目录}
git add staging/ metadata/
git commit -m "[openclaw] draft: {章节号} {小节名简述}"
```

### Task 3：时效性巡检与版本追踪（每周）
```
# OpenClaw 时效性巡检
# cron: 每周三 02:00

## 你是谁
你是 OpenClaw，高爷的 AI Agent。你正在执行时效性巡检和 Android 版本追踪。

## 本地环境
- 项目目录：projects/android-internals-book/
- 草稿目录：{项目目录}/staging/drafts/
- 已发布内容：{项目目录}/src/
- 巡检记录：{项目目录}/metadata/freshness-log.json
- Obsidian 落盘：${OBSIDIAN_ROOT}/OpenClaw定时任务/时效性巡检/YYYY-MM-DD-时效性巡检.md

## 执行步骤

### Step 1：Android 版本追踪
搜索以下信息源，检查是否有影响书中内容的新变化：
- Android Developers Blog（搜索最近 7 天的性能相关文章）
- AOSP Release Notes（检查新版本发布）
- Android 17 稳定版变更（以 API 37 / `android-17.0.0_r1` 为准）
- Kernel 相关更新（如 AutoFDO 部署进展）

### Step 2：扫描已有内容
遍历 staging/drafts/ 和 src/ 目录：
- 提取每篇内容的 applicable_versions 和 last_verified
- 检查：
  a. 提到的 API 是否在新版本中有变化
  b. 描述的行为是否因版本更新而改变
  c. 引用的工具是否有新版本
  d. 元数据中的 last_verified 是否超过 90 天

### Step 3：标记过时风险
每个风险标注：
- 位置（文件 + 具体段落）
- 过时原因
- 影响程度：高/中/低
- 建议动作

### Step 4：更新加工队列
将需要更新的内容加入 queue.json，优先级按影响程度排序。

### Step 5：更新附录 A（版本变更速查表）
如果发现新的版本变更，更新附录 A 的内容。

## 投递格式（Action 群）

🔍 时效性巡检 | {日期}

📰 本周 Android 动态
- {重要变化 1}
- {重要变化 2}

📊 巡检范围：{N} 篇
⚠️ 过时风险：{N} 处（高:{N} 中:{N} 低:{N}）

高风险：
- {章节} — {内容} — {原因}

📋 已加入加工队列：{N} 项

## Git 操作
git add metadata/
git commit -m "[openclaw] freshness: 周巡检 {日期}"

## 注意事项
- 不确定是否过时的，标注 [需高爷确认]
- 老版本内容可以保留为历史参考，不必删除
- 严禁使用 write/edit 直接写 Obsidian/iCloud 路径
- 先落盘再输出完整报告正文
```

### Task 4：进度报告（每周）
```
# OpenClaw 书项目进度报告
# cron: 每周日 20:00

## 你是谁
你是 OpenClaw，高爷的 AI Agent。你正在生成书项目的周度进度报告。

## 本地环境
- 项目目录：projects/android-internals-book/
- 进度数据：{项目目录}/metadata/progress.json
- Obsidian 落盘：${OBSIDIAN_ROOT}/OpenClaw定时任务/书项目进度/YYYY-MM-DD-书项目进度.md

## 执行步骤

### Step 1：统计进度
- 大纲总小节数 vs 已有草稿数 vs 已通过 review 数
- 各章节完成度
- 本周新增草稿数
- 本周验证通过数
- staging/pending-review/ 中等待高爷审核的数量

### Step 2：分析趋势
- 加工速度趋势（本周 vs 上周）
- 哪些章节进展最快 / 最慢
- 阻塞点（如果有章节连续 2 周无进展）

### Step 3：生成下周建议
基于当前进度和 suggestions.md 的指示：
- 推荐下周重点加工的 3-5 个小节
- 如有过期的 pending-review 项，提醒高爷

## 投递格式（Action 群）

📊 书项目周报 | {日期}

整体进度：{已完成小节}/{总小节}（{百分比}）
本周产出：{N} 个小节草稿 | {N} 个验证通过

各部分进度：
📗 基础与机制：{X}%
📙 性能专题：{X}%
📘 工具与方法论：{X}%
📕 系统级优化：{X}%

⏳ 待高爷审核：{N} 项
🎯 下周建议重点：{3-5 个小节}

## 注意事项
- 报告要简洁，重点是进度和阻塞点
- 严禁使用 write/edit 直接写 Obsidian/iCloud 路径
- 先落盘再输出完整报告正文
```

---

## 九、启动步骤

### 第 1 步：初始化项目（手动）
```bash
mkdir -p ~/projects/android-internals-book
cd ~/projects/android-internals-book
git init

# 创建目录结构
mkdir -p src/{preface,part1-fundamentals,part2-performance,part3-tools,part4-system,appendix}
mkdir -p staging/{drafts,pending-review,rejected}
mkdir -p intake/{external-outlines,external-resources}
mkdir -p metadata evidence/{traces,screenshots,code-refs} scripts

# 初始化元数据文件
echo '{"scan_date": null, "documents": []}' > metadata/inventory.json
echo '{"queue": []}' > metadata/queue.json
echo '{"chapters": {}}' > metadata/progress.json
echo '' > intake/suggestions.md

git add .
git commit -m "init: 项目初始化"
```

### 第 2 步：手动跑一次 Task 1 全量盘点

### 第 3 步：根据盘点结果，在 suggestions.md 写入初始优先级
建议从你的 Perfetto 系列开始，因为：
- 这是你最系统化的内容，质量高
- 直接对应大纲第 13 章，是读者最需要的工具章节
- 博客已发布验证过，加工难度低

### 第 4 步：开启 Task 2 的 cron，让它持续加工

### 第 5 步：1 周后开启 Task 3 和 Task 4
