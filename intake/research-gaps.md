

## [Task9 Deep Review] 1.10 ContentProvider 性能与优化 — 2026-04-11

### 盲区 1：ContentProvider Binder 线程池模型
**描述**：章节 ANR 机制未覆盖 Provider 端 Binder 线程池的默认线程数、线程耗尽型 ANR 与主线程阻塞型 ANR 的区别、以及跨进程死锁的典型模式（调用方持有锁 A，等待 Provider；Provider 需要锁 A 才能完成请求）。

**重要程度**：高

**建议研究方向**：
- AOSP ActivityManagerService 中 ContentProvider 进程的 Binder 线程池配置
- traces.txt 中 Binder 线程耗尽（"binder thread pool is full"）的特征栈帧
- 经典跨进程死锁案例（ContentProvider + 数据库锁）

**关联章节**：§1.10、§9.1-9.4 ANR 机制、§1.4 Binder IPC

### 盲区 2：Android 11 ContentProvider URI 权限安全变更
**描述**：Android 11 对 FLAG_GRANT_READ_URI_PERMISSION 和 ClipData 的交互引入了重要变化，ALLOWED_URI_LENGTH_SECURITY_SENSITIVE 限制也在 Android 11.0（API 30）中引入，影响跨 App 数据共享的安全性分析。

**重要程度**：中

**建议研究方向**：
- Android 11 变更日志中关于 ContentProvider grant 机制的修改
- AOSP ContentProviderRecord 和 AppOpsManager 相关实现
- URI 权限 grant 操作的性能开销（与 App 启动的关系）

**关联章节**：§1.10、§1.4 Binder IPC

---

## [2026-04-08] 1.1 Android 分层架构 — Zygote 预加载机制源码路径缺失

### 盲区描述
正文描述了"Zygote 进程预加载了 ART 运行时、常用 Java 类、系统资源"，但未给出 `preload()` 方法的源码路径和关键片段。性能分析中，理解 Zygote 预加载了哪些类（`preloadClasses()` / `preloadResources()` 的具体内容和大小）对分析冷启动瓶颈至关重要——如果某个 App 依赖的类不在预加载列表中，就会导致额外的初始化时间。

### 重要程度
高

### 建议研究方向
- 找到 Zygote.java 中 `preloadClasses()` 和 `preloadResources()` 的完整实现
- 确认 Android 16 中预加载列表的变化（是否有新增/删除的预加载类）
- 量化预加载资源的大小（通常在 30-50MB 范围）
- 分析 App 冷启动中 Zygote fork 后、App 代码执行前这段时间的初始化来源（ART 初始化 vs 资源加载）

### 关联章节
1.2（boot-process）、1.11（zygote-startup）、1.7（art-compilation）、8.3（launch-optimization）

## [2026-04-08] 1.2 系统启动全流程 — 知识盲区

### 盲区描述
Zygote fork SystemServer 的触发机制：当前章节描述"Zygote 预加载完成后 fork SystemServer"，但未说明这个 fork 是 ZygoteInit.main() 的主动行为（ZygoteInit.main() 内部调用 startSystemServer()）还是被动等待信号。实际上这是 ZygoteInit 的硬编码流程，不需要外部触发，但正文没有明确这一点，导致读者可能误以为 SystemServer fork 是被某种 IPC 触发的。

### 重要程度
高

### 建议研究方向
- 追溯 ZygoteInit.main() → startSystemServer() 的调用链，确认 Zygote.java vs ZygoteInit.java 的方法归属
- 调研 Zygote fork SystemServer 后，Zygote 主进程（孵蛋进程）和 SystemServer 的角色分化细节
- 对比 Zygote fork app 进程 vs fork SystemServer 的异同

### 关联章节
1.1（Zygote 在分层架构中的定位）、1.3（Zygote 预加载机制细节）、8.2（Zygote 进程监控）

---

## [2026-04-08] 1.2 系统启动全流程 — 知识盲区（SELinux）

### 盲区描述
init 阶段的安全初始化流程（SELinux 策略加载、restorecon）完全缺失。SELinux 加载时机、策略类型（enforcing/permissive）、对 init 阶段耗时的实际影响均未覆盖。这是 Android 安全启动链的重要组成部分，直接影响开机时间分析。

### 重要程度
中

### 建议研究方向
- 调研 init.rc 中 `restorecon` / `restorecon_recursive` 命令的执行时机
- 分析 SELinux 策略加载与 init 阶段耗时的关系
- 调研 Perfetto 中如何追踪 SELinux 加载（sched_wakeup 无法覆盖，需要 ftrace selinux 事件）

### 关联章节
1.1（Linux Kernel 启动）、14.1（Android 16 架构变化中可能有安全部分）


## [2026-04-09] 1.13 MessageQueue 机制与 DeliQueue 无锁优化 — 知识盲区

### 盲区描述
tombstoning 机制是 DeliQueue 数据一致性的核心，但正文描述不够清晰：具体是什么操作会触发 tombstone 标记？是消息被主动移除（removeCallbacks/removeMessages）时标记，还是 Looper 从栈中 pop 时标记？tombstone 消息最终在哪里被跳过？这个机制如果不讲清楚，读者无法理解为何栈和堆的数据迁移是安全的

### 重要程度
高

### 建议研究方向
- 补充 tombstoning 的具体触发时机和处理流程（可标注 [待验证 AOSP 源码]）

### 关联章节
1.5（线程模型）、1.14（锁竞争与同步性能分析）、2.4（Choreographer）



## [2026-04-09] 2.1 Android 渲染架构全景 — 知识盲区

### 盲区描述
HWUI Android 16 重构细节缺失。章节明确提到"Android 16 HWUI 渲染管线进行了内部重构"，但未展开说明具体重构内容。与此同时，章节多处引用 Android 16 之前的 HWUI 内部结构（OpenGLCanvas 类名、RenderNode 详细字段、DisplayListData 结构）均标注了 [待验证]，这些代码片段在 Android 16 中是否仍然有效无法确认。这是章节的核心知识盲区。

### 重要程度
高

### 建议研究方向
- 调研 AOSP android-16.0.0_r1 中 frameworks/base/libs/hwui/ 目录结构，确认 OpenGLCanvas/RenderNode/DisplayList 的实际状态
- 确认 SkiaOpenGLPipeline/SkiaVulkanPipeline 在 Android 16 中的实际类名和调用路径
- 补充"Android 16 HWUI 变化"专节，说明重构前后的架构差异
- 对比 frameworks/base/libs/hwui/ 在 Android 14 vs Android 16 中的文件变化

### 关联章节
2.5（MainThread 与 RenderThread 协作）、2.10（GPU 渲染深入，涉及 Vulkan 后端）、2.6（SurfaceFlinger）



## [2026-04-09] 2.10 GPU 渲染深入 — 知识盲区

### 盲区描述
1. TBR（Tiled-Based Rendering）机制未展开：章节提及 ARM Mali GPU 使用 TBR 架构，但未解释 TBR 的分块策略、On-Chip Tile Memory 与主存访问权衡、TBDR（Tile-Based Deferred Rendering）与 immediate mode rendering 的区别及各自对移动设备功耗/性能的影响。
2. Android 12/13 过渡阶段的 GPU 渲染变化覆盖不足：applicable_versions 标注为 Android 12-16，但 Android 12（FramePacing/双缓冲改进）和 Android 13（渲染 pipeline 微调）的具体 GPU 相关变化几乎没有展开。

### 重要程度
高

### 建议研究方向
- 调研 ARM Mali GPU TBR/TBDR 架构原理及与 Qualcomm Adreno 的架构差异（Adreno 为 tile-based deferred rendering，架构选择不同）
- 梳理 Android 12/13/14 中 GPU 相关的 changelog（从 AOSP change log 或 Android Release Notes 提取）
- 对比主流移动 GPU（Adreno 740/750/760，Mali G710/G720/G720）的 fillrate/带宽/算力典型值，建立性能参考表

### 关联章节
2.3（VSync），2.6（SurfaceFlinger），2.9（渲染机制版本演进），2.5（MainThread/RenderThread 协作）

## [{date}] 2.6 SurfaceFlinger 与合成 — Jank 场景下的 BufferQueue Backpressure 机制

### 盲区描述
章节 Jank 与 SurfaceFlinger 关系一节描述了 SurfaceFlinger 合成延迟对 App 端的影响："SurfaceFlinger 持有 Buffer 的时间变长，releaseBuffer 延迟，导致 App 端 dequeueBuffer 被阻塞"。但该描述不够精确：BufferQueue 的 dequeueBuffer 在 Buffer 全部被占用时会阻塞（当所有 Buffer 都在"已出队但未归队"状态时），但这与 SurfaceFlinger "持有 Buffer 没 release"之间的时序关系、以及实际 Jank 场景下的真实影响路径（如 SurfaceFlinger 合成慢→HWC 持有 Buffer 时间延长→release fence 延迟→App 被 unblock 的时序）需要更精确的建模。

### 重要程度
高

### 建议研究方向
- BufferQueue dequeueBuffer 的阻塞条件（numBuffers、in_use 计数）
- SurfaceFlinger 合成慢时 HWC release fence 的时序延迟路径
- Jank 发生时 App 端 RenderThread 是否实际被阻塞，还是"渲染正常但无法呈现"
- Perfetto 中如何通过 BufferQueue track + release fence track 联合分析 backpressure

### 关联章节
2.6（SurfaceFlinger 与合成）、7.3（卡顿分析方法论）


## [2026-04-09] 2.9 渲染机制的版本演进 — 知识盲区

### 盲区描述
Android 5.0 Dalvik → ART 的切换对渲染性能的影响未被现有章节覆盖。ART 的 AOT 编译使得应用安装时已完成 dex 到本地码的编译，Java 方法调用的 overhead 大幅降低，这是 Android 5.0 后主线程 `performTraversals` 更快的重要原因（不仅是 RenderThread 的功劳）。

### 重要程度
高

### 建议研究方向
- Android 5.0 ART 对 UI 线程性能的具体 benchmark 数据（与 Dalvik 对比）
- ART 编译器（dex2oat）对渲染路径关键类（如 View、Canvas、Drawable）的 AOT 编译策略
- ART 对 DisplayList 录制和提交的性能影响

### 关联章节
- 1.7 ART 编译管线与 dex2oat 优化（已有章节）
- 2.9 渲染机制的版本演进（当前章节）
- 4.3 ART 虚拟机内存管理（已有章节）


## [2026-04-09] 1.5 线程模型 — RenderThread Freeze 机制（Android 11+）

### 盲区描述
Android 11 引入了 RenderThread Freeze 机制：当主线程发生 Long Frame（帧耗时 > 16ms）时，RenderThread 可选择丢弃当前帧的渲染（freeze），避免主线程阻塞导致的渲染级联延迟传播到后续帧。此机制直接影响 Android 11+ 设备的掉帧分析结论，但 1.5 章节完全未覆盖。

### 重要程度
高

### 建议研究方向
- RenderThread Freeze 的触发条件与 threshold（如何判断主线程是否"长时间"阻塞）
- freeze 决策的源码位置（renderthread/RenderThread.cpp 中的 freeze 逻辑）
- 对 Perfetto 分析的影响：freeze 时 RenderThread CPU slice 会中断或变短，易误判为"GPU 空闲"
- Android 11-16 中 freeze 机制的变化

### 关联章节
2.5（MainThread 与 RenderThread 协作）、2.4（Choreographer 与渲染流水线）


## [2026-04-09] 1.5 线程模型 — Android 14 VirtualThread 与线程模型演进

### 盲区描述
Android 14 引入了 VirtualThread（虚拟线程，JDK 21 移植），是 Android 线程模型的重大变化。VirtualThread 由平台线程（PlatformThread）虚拟化实现，与 Kotlin Coroutine 的协程模型有本质区别。VirtualThread 对 Perfetto 线程可见性的影响、VirtualThread 与 SCHED_FIFO/SCHED_OTHER 的交互、以及对主线程 Binder 调用的影响，在 1.5 章节中完全缺失。

### 重要程度
高

### 建议研究方向
- Android 14 VirtualThread 的实现原理（与 JDK 21 VirtualThread 的差异）
- VirtualThread 在 Perfetto 中的可见性（是否作为独立线程可见，还是透明虚拟化）
- VirtualThread 对线程优先级（nice 值/cgroup）继承规则的影响
- Kotlin Coroutine Dispatcher 与 VirtualThread 的结合使用（Dispatchers.VirtualThread）

### 关联章节
2.5、7.7（Compose Performance，涉及协程使用）

## [2026-04-09] 1.1 Android 分层架构 — 知识盲区

### 盲区描述
Stable AIDL 与 Unstable AIDL 的区别在当前章节未覆盖。Framework→HAL 通信使用 Stable AIDL（有版本保证），而 Framework 内部组件间使用 Unstable AIDL（无稳定性保证）。这个区别对理解 Mainline 模块隔离机制至关重要。

### 重要程度
高

### 建议研究方向
- Stable AIDL 的版本管理和向后兼容机制
- Mainline 模块如何利用 Stable AIDL 实现独立更新
- AIDL 的序列化/反序列化开销（Binder Performance 的一部分）

### 关联章节
1.1, 1.2, 16.3（AOSP 编译）, 17.1（OEM 优化）

---

## [2026-04-09] 1.1 Android 分层架构 — 知识盲区

### 盲区描述
hwbinder vs 标准 binder 的底层差异描述不够深入。两者使用不同的设备节点（/dev/hwbinder vs /dev/binder），不同的 IPC 通道，对 Perfetto 追踪事件的可见性也不同（AIDL HAL 使用标准 binder，HIDL HAL 使用 hwbinder）。这个差异直接影响 HAL 问题追踪的难度。

### 重要程度
中

### 建议研究方向
- hwbinder 与 binder 的内核实现差异
- 在 Perfetto 中如何区分 hwbinder 和标准 binder 事件
- HIDL HAL 仍保留的场景（向后兼容）

### 关联章节
1.1, 2.6（SurfaceFlinger）, 13.9（tracing 基础设施）

---

## [2026-04-09] 1.1 Android 分层架构 — 知识盲区

### 盲区描述
Android 12/13 中 AIDL 对 HAL 架构的重要变化未覆盖。Android 12 开始强制要求更多 HAL 使用 AIDL（camera.provider、audio.core 等），这是 Treble 架构真正成熟的关键节点。

### 重要程度
中

### 建议研究方向
- Android 12/13 AIDL HAL 强制迁移清单
- 从 HIDL 到 AIDL 迁移对性能分析的方法论影响

### 关联章节
1.1, 9.3（ANR 分析）, 13.9（tracing 基础设施）

---

## [2026-04-09] 1.1 Android 分层架构 — 知识盲区

### 盲区描述
Android 16 模块数量的具体数字未给出。章节提到"超过 50 个模块"，但没有具体数字（截至 Android 16，Mainline 模块总数约为 57 个，此数据需验证）。

### 重要程度
低

### 建议研究方向
- 验证 Android 16 Mainline 模块确切数量
- 确认哪些模块与性能分析直接相关

### 关联章节
1.1


## [2026-04-09] 2.2 帧率与刷新率 — 知识盲区

### 盲区描述
**三缓冲（Triple Buffer）对帧间隔一致性的改善机制**。当前章节多次提及双缓冲和帧提交时机，但没有覆盖三缓冲在渲染管线中的作用。三缓冲允许渲染线程和显示线程并行进行，当 GPU 渲染时间不稳定时不会导致帧等待 GPU，从而改善帧间隔的均匀性。这是分析帧间隔抖动时的重要概念盲区。

**华为 VSync 调度的具体版本范围**。章节引用了知乎文章描述华为在某些系统版本中注入伪造 VSync 信号导致 Animation 回调时序脱节的问题，但没有标注具体从哪个 EMUI/HarmonyOS 版本开始有此问题、哪个版本已修复。这是 OEM 定制研究中必须精确定位的重要内容。

### 重要程度
高

### 建议研究方向
- 三缓冲的工作原理、在 SurfaceFlinger 中的实现、以及它如何改善帧间隔抖动
- 华为 HarmonyOS 4+ / EMUI 12+ 的 VSync 调度行为是否已与 AOSP 行为一致
- Perfetto 中如何识别三缓冲场景（BufferQueue 深度变化）

### 关联章节
2.2（帧率与刷新率）, 2.6（SurfaceFlinger 与合成）, 2.9（渲染机制版本演进）, 17.2（SoC 平台差异）

## [2026-04-09] 2.5 MainThread 与 RenderThread 协作 — DisplayList 同步机制未揭示

### 盲区描述
正文描述了 SyncFrameState 的四个步骤（等待上一帧、DisplayList 同步、Bitmap 上传GPU、释放主线程），但对"DisplayList 数据如何从 MainThread 转移到 RenderThread"只用了"引用计数和资源所有权转移"这种黑盒描述。实际上这个转移依赖 GraphicBuffer 共享 + Asynchronous Fence 机制，是理解 syncFrameState 性能瓶颈的关键。

### 重要程度
高

### 建议研究方向
- 追溯 DrawFrameTask::syncFrameState() C++ 实现，搞清楚 DisplayList 数据（哪些是共享内存引用，哪些是真正需要拷贝的数据）
- 分析 Bitmap/GraphicBuffer 跨线程传递的 Fence 依赖（acquireFence/releaseFence）在 sync 阶段的时序
- 量化 DisplayList sync 的耗时构成：引用传递 vs 数据拷贝 vs Fence 等待各占多少

### 关联章节
2.5（主章节）、2.16（Sync Fence 框架）、2.15（DMA-BUF/Gralloc）
## [2026-04-09] 1.6 Android 版本演进中的架构变化 — 知识盲区

### 盲区描述
1. **性能测试方法论盲区**: 章节提到性能数据（如启动时间缩短3.16%）但未说明测试环境、样本数量、测试方法，数据可信度存疑
2. **模块化对开发工作流的影响盲区**: 只描述了架构变化，未说明对开发者日常调试、测试、发布工作的实际影响
3. **性能监控工具适配指南盲区**: 提到隐私限制影响工具，但未给出具体的工具适配策略和API使用指南

### 重要程度
高

### 建议研究方向
- 补充性能数据的测试环境说明（设备型号、样本数量、测试时间）
- 分析模块化架构对开发者调试流程的影响（如如何在分离的System/Vendor分区中定位问题）
- 提供性能监控工具适配的具体API使用指南和权限申请策略

### 关联章节
1.1（架构基础）、2.9（渲染演进）、4.4（内存管理）、5.6（功耗管理）


## [2026-04-09] 1.2 系统启动全流程 — 知识盲区（Zygote 64位进程命名）

### 盲区描述
正文 applicable_versions 为 Android 8 (API 26) - Android 16 (API 36)，覆盖了所有现代 Android 版本。但正文只描述"Zygote 进程"，未提及 64 位设备上 Zygote 的实际进程名为 zygote64（而非 zygote）。这与 Perfetto trace 中的实际进程名称直接相关——读者看到 zygote64 的 trace 可能无法与正文对应。此外，zygote64 和 zygote（32位）预加载的类可能不同，对启动时间的影响也不同。

### 重要程度
中

### 建议研究方向
- 调研 AOSP 中 zygote64 的引入版本（Android 5.0+ 64位设备就存在）
- 确认 zygote64 vs zygote 预加载内容是否完全相同
- 确认 Perfetto trace 中两个进程的命名方式

### 关联章节
1.7（ART 编译管线与 dex2oat 优化）、8.2（启动优化策略）


## [2026-04-09] 6.1 Android 存储架构 — 知识盲区

### 盲区描述
f2fs atomic_write 接口与 AOSP SQLite 的实际集成状态。当前正文描述 f2fs 提供 atomic_write ioctl，允许 SQLite"跳过写日志直接原子提交"。但未说明：SQLite 在 AOSP 中默认是否启用 f2fs atomic_write support？该功能需要 SQLite 编译时启用 SQLITE_F2FS_ATOMIC_WRITE 宏，实际设备上该宏是否默认启用？

### 重要程度
高

### 建议研究方向
- 查找 AOSP external/sqlite/dist/SqliteWiki 和 Fts5 源码中 f2fs atomic_write 相关代码
- 确认 Android 10/11/12/13/14 各版本中 SQLite 是否默认启用 f2fs atomic_write
- 如果未默认启用，查找哪些设备/rom 厂商手动启用了该特性，以及量化数据

### 关联章节
6.1（存储架构）、6.3（I/O 调度）、7.2（卡顿原因体系）


## [2026-04-09] 1.7 ART 编译管线与 dex2oat 优化 — 知识盲区

### 盲区描述
Compact DEX（cdex）格式与 raw DEX 格式在 ART 编译行为上的差异。Android 10 引入了 compact DEX（cdex），这是一种将多个 DEX 文件合并打包的格式。cdex 的关键特性是：它不能被 ART 解释执行（因为不是标准 DEX），必须先编译成 OAT 才能运行。这意味着使用 cdex 的应用在安装时必须有 AOT 编译，不能回退到纯解释执行。

### 重要程度
高

### 建议研究方向
- AOSP art/libdexfile/ 中的 cdex 文件格式实现
- Compact DEX 在 Android 10-14 的演进
- cdex 对安装时间、存储占用、启动性能的实际影响量化
- R8/D8 如何决定何时生成 cdex vs raw DEX

### 关联章节
§1.7（本章）、§8.2（App 启动全流程）、§8.3（启动优化策略）


## [2026-04-09] 4.6 内存相关的版本演进 — 知识盲区

### 盲区描述
MTE（Memory Tagging Extension）的硬件依赖性未被明确说明。MTE 需要 ARMv8.5-A 指令集支持，并非所有 Android 14+ 设备都具备此硬件能力。Pixel 8 搭载的 Tensor G3 确认支持，但 MediaTek、Qualcomm 不同芯片型号的支持情况各异。

### 重要程度
高

### 建议研究方向
- 各芯片平台（Dimensity、Snapdragon）的 MTE 支持情况
- Android 14/15 不同 SKU（play services, GMS）中 MTE 的实际启用条件
- 如何在 App 层面检测设备是否支持 MTE（android.os.fea)

### 关联章节
4.6（内存相关的版本演进）、4.3（ART 虚拟机内存管理）

## [2026-04-10] 1.6 Android 版本演进中的架构变化 — 知识盲区

### 盲区描述
Android 16 代号（"Baklava" vs "Vanilla Ice Cream"）与 API 版本（35 vs 36）在章节内存在矛盾，同时 64 位过渡的完整时间线（Android 5.0 → Android 10）未在章节中完整呈现。Android 甜点代号规律（字母顺序）也未作解释，读者无法自行判断未来版本。

### 重要程度
高

### 建议研究方向
- 核实 Android 16 正式代号和 API Level（需查阅 Google 官方 Android 16 发布公告）
- 梳理 Android 64 位过渡完整时间线：5.0（64 位支持引入）→ 10（32 位受限/分离 zygote）→ 14（64 位强制）
- 研究 Android 代号甜点字母顺序规律及其对性能分析的参考价值

### 关联章节
1.4（Binder IPC）、1.7（ART 编译管线）、5.6（Android 功耗管理）、4.6（内存版本演进）


## [2026-04-10] 2.12 Window Manager Service 与窗口管理 — WMS 锁竞争机制缺失

### 盲区描述
章节覆盖了 WMS 的 relayoutWindow、performLayout、StartingWindow 等核心概念，但缺少对 WMS 全局锁（`mGlobalLock`）的锁竞争机制的深度分析。WMS 的 Binder 线程执行 relayoutWindow 时需要获取 mGlobalLock，而 AMS、IMS 等其他系统服务也在同一把锁上。当 AMS 持有锁处理 Activity 生命周期时，所有 WMS 的 relayout 请求都会被阻塞——这是 WMS 性能问题的核心根因，却未在章节中体现。读者无法据此分析"为什么 WMS 耗时但看起来没做什么"的典型场景。

### 重要程度
高

### 建议研究方向
- AOSP WindowManagerService.java 中 mGlobalLock 的获取时机和范围（relayoutWindow、performLayout、addWindow 等关键方法的锁区域）
- system_server 主线程与 Binder 线程在 mGlobalLock 上的竞争模式
- 如何在 Perfetto 中通过锁等待事件（THREAD_WAITING）识别 WMS 锁竞争
- 与 AMS 的 mGlobalLock 共享关系：为什么 AMS 的耗时操作会传导到 WMS

### 关联章节
2.12, 1.8（Activity Manager Service）, 8.2（App 启动全流程）, 8.4（其他响应速度场景）


## [2026-04-10] 1.2 系统启动全流程 — 知识盲区

### 盲区描述
Android 7.0 引入的 Direct Boot 机制让设备在锁屏状态下部分 App 可运行，Credential Encrypted（CE）和 Device Encrypted（DE）存储有不同的访问权限。启动链中 locked_boot_completed 和 boot_completed 的区分与 Direct Boot 直接相关，但本节未覆盖。

### 重要程度
中

### 建议研究方向
- Direct Boot 两个存储区域的访问权限差异
- Credential Encrypted Storage 在启动链中的解锁时机
- locked_boot_completed 与 boot_completed 之间的系统行为变化
- 对 App 冷启动优化的影响（首次解锁后 vs 已解锁状态）

### 关联章节
1.1（Android 分层架构）, 1.3（进程模型与生命周期管理）, 8.2（App 启动全流程）


## [2026-04-10] 1.13 MessageQueue 机制与 DeliQueue 无锁优化 — 知识盲区

### 盲区描述
DeliQueue 中同步屏障（SyncBarrier）与 drain/堆机制的交互：VSync 异步消息在 DeliQueue 架构下如何保证优先级？drain 后同步屏障还按原有逻辑扫描消息吗？tombstoning 是否影响异步消息？

### 重要程度
高

### 建议研究方向
- 找到 AOSP android-17 MessageQueue.java 中 DeliQueue 模式的 next() 实现，核对同步屏障分支
- 确认 VSync 回调消息（FrameDisplayEventReceiver）在 DeliQueue 模式下的入队路径

### 盲区描述
Java MessageQueue 的 native 层协调：DeliQueue 是否完全在 Java 层实现？还是也涉及 native MessageQueue 的改造？nativePollOnce 在 DeliQueue 感知新消息时是否仍有相同作用？

### 重要程度
中

### 建议研究方向
- 研读 AOSP android-17 的 frameworks/base/core/jni/ 相关 native 代码
- 确认 nativeWake/nativePollOnce pair 在 DeliQueue 架构下是否保留


## [2026-04-10] 2.4 Choreographer 与渲染流水线 — FrameMetrics GPU Duration 可用性

### 盲区描述
章节行305-306展示了 `FrameMetrics.METRIC_GPU_DURATION`，但在部分 Android 设备（尤其是联发科早期芯片、模拟器、部分定制 ROM）上，该 metric 返回 0 或不可用——因为 GPU 渲染耗时的采集需要 GPU 时钟计数器硬件支持，并非所有设备都实现了此功能。章节未对此加以说明，读者可能会在真实项目中遇到"FrameMetrics 返回的 GPU 耗时全是 0"的困惑。

### 重要程度
高

### 建议研究方向
- 调研 AOSP 中 `FrameMetrics.GPU_DURATION` 的实现条件（需要 GPU 驱动支持）
- 整理已知不支持该 metric 的芯片/设备列表
- 补充条件性说明（"在支持 GPU 时钟计数器的设备上可用"）
- 如无法获取 GPU 耗时，推荐替代方案：Perfetto 的 `gpu_freq` track 或 `gpu_mem` track

### 关联章节
§2.9（FrameMetrics API 演进）、§2.4（本节）

---

## [2026-04-10] 2.4 Choreographer 与渲染流水线 — Frame Timeline 缺实际 Trace 示例

### 盲区描述
Frame Timeline（帧时间线）是 Android 13（API 33）引入的 Choreographer 核心机制，也是理解"doFrame 耗时超预算≠用户感知卡顿"这一重要结论的关键。章节已描述其作用，但缺少一个真实的 Perfetto trace 可视化示例，导致读者无法直观理解"App 期望的帧时间线"vs."SurfaceFlinger 实际呈现的时间线"之间的差异。这对于实际性能分析工作有较大影响。

### 重要程度
高

### 建议研究方向
- 获取一个真实设备的 Perfetto trace（推荐：掉帧场景 vs. 流畅场景各一份）
- 截取 Frame Timeline Track 的关键片段，标注：VSYNC-app 竖线、App selected timeline（虚线）、SF actual timeline（实线）、frame deadline
- 对比说明：什么情况下 App timeline 超过了 deadline 但 SF 仍能准时呈现？什么情况下 doFrame 超时但用户未感知卡顿？

### 关联章节
§2.3（VSync 机制）、§2.4（本节）、§2.6（SurfaceFlinger 合成）

## [2026-04-10] 1.3 进程模型与生命周期管理 — 知识盲区

### 盲区描述
Android 16 oom_adj常量表不完整：缺失PERCEPTIBLE_RECENT_FOREGROUND_APP_ADJ=50、PERCEPTIBLE_MEDIUM_APP_ADJ=225、CACHED_APP_LMK_FIRST_ADJ=950等新增常量；Phantom Process Killer在Android 13-16的演进（cgroup v2集成）未覆盖；Zygote预加载的具体类和资源对冷启动优化价值未量化。

### 重要程度
高

### 建议研究方向
- 验证AOSP android-16.0.0_r1 ProcessList.java中全部OOM_ADJ常量，建立完整对照表
- 研究Android 15 cgroup v2迁移对lmkd回收机制的影响（per-app memory cgroup limit）
- 量化Zygote预加载资源大小（boot.art、boot.oat等），支撑"几十MB"的表述
- 调研Phantom Process Killer在Android 13-16的变化

### 关联章节
1.2（Zygote启动）、1.7（ART编译）、4.6（内存版本演进）


## [2026-04-10] 1.9 Package Manager Service 与应用安装性能 — 知识盲区

### 盲区描述
installd 是常驻 daemon，通过 fork 子进程的方式执行 dex2oat 等特权操作。PMS 通过 `/dev/socket/installd` 向 installd 发送指令，installd fork 出子进程执行操作后通过 socket 返回结果。这一 fork 机制是从 system_server 权限隔离的关键架构设计，文中完全未提及。

### 重要程度
高

### 建议研究方向
- installd fork 子进程机制的具体实现（system/installd/）
- PMS 与 installd 之间的 socket 协议格式
- installd 的权限模型（CAP_NET_BIND_SERVICE 等）

### 关联章节
§1.7（ART 编译管线）、§1.3（进程与线程）


## [2026-04-10] 1.2 系统启动全流程 — ContentProvider 启动时序缺失

### 盲区描述
章节覆盖了 init → Zygote → SystemServer → Launcher 的完整启动链，但没有覆盖 ContentProvider 的启动时序。在 Android 中，ContentProvider.onCreate() 在 Application.onCreate() 之前执行，这是 App 冷启动的第一道关卡，也是最常见的启动优化盲区。具体来说：
- ContentProvider 的 publishContentProviders() 调用发生在 Application.attachBaseContext() 之后、Application.onCreate() 之前
- 如果 ContentProvider.onCreate() 中有耗时操作（如加载 SO 库、访问数据库），会直接拖慢冷启动速度
- 这是理解 1.10 ContentProvider 性能和 8.2 App 启动全流程的关键前置知识

### 重要程度
高

### 建议研究方向
- ContentProvider.onCreate() 的精确执行时机（相对于 Application 生命周期）
- ActivityThread.installContentProviders() 的完整源码流程
- 如何在 Perfetto 中定位 ContentProvider 初始化耗时
- App Startup 库如何合并多个 ContentProvider 的初始化

### 关联章节
1.10（ContentProvider 性能）, 8.2（App 启动全流程）, 8.3（启动优化策略）

## [2026-04-10] 3.1 Input 事件分发全流程 — 知识盲区

### 盲区描述
章节版本演进表（line 450）称"Android 13: InputDispatcher 使用 mAnrTracker 替代之前的超时检测方式"，但正文完全没有说明 mAnrTracker 具体替代了什么机制，差异在哪里，为何改变。读者无法从现有描述中获得有意义的版本差异知识。

### 重要程度
高

### 建议研究方向
- 调研 Android 13 之前 InputDispatcher ANR 超时检测的实现方式（是否基于 processLocked 中的 mAnrTracker 替代方案？）
- 对比 Android 13 前后的 ANR 检测精度差异
- 补充 mAnrTracker 的数据结构说明及其对 Trace 分析的影响

### 关联章节
3.1（本章）、9.1（ANR 设计思想）

---

## [2026-04-10] 3.1 Input 事件分发全流程 — 知识盲区

### 盲区描述
版本演进表（line 451）称"Android 14+: InputFlinger 进一步模块化，增加对折叠屏、多显示器的支持"，表述模糊。"进一步模块化"不构成有技术价值的版本差异信息。折叠屏/多显示器支持对 Input 路由的具体影响未说明。

### 重要程度
高

### 建议研究方向
- 调研 Android 14 InputFlinger 具体新增模块（InputClassifier？InputFlinger-Performance？）
- 调研折叠屏场景下 InputDispatcher 的多屏路由策略变化
- 调研多显示器场景下触摸事件分发目标窗口的选择逻辑变化

### 关联章节
3.1（本章）、3.3（手势导航与系统交互）

---

## [2026-04-10] 3.1 Input 事件分发全流程 — 知识盲区

### 盲区描述
版本演进表（line 453）标注 Android 16 "[待验证：预测性返回手势（Predictive Back）对 Input 分发路径的影响]"，InputFlinger 扩展章节（line 413）也标注了相同 [待验证]。Predictive Back Gesture 已在 Android 14 正式引入，这对 InputDispatcher 的窗口查找路径有直接影响（back gesture 走 findFocusedWindowTargets 而非 findTouchedWindowTargets）。此差异悬而未决影响章节对 Android 16 的适用性声明。

### 重要程度
高

### 建议研究方向
- 调研 Predictive Back Gesture 在 InputDispatcher 中的处理路径
- 确认 Android 16 中 Predictive Back 是否有新的 Input 事件类型或分发策略
- 补充对 Trace 分析的影响（back gesture 的 ANR 超时判断路径是否与触摸事件不同）

### 关联章节
3.1（本章）、3.3（手势导航与系统交互）、9.1（ANR 设计思想）

---

## [2026-04-10] 3.1 Input 事件分发全流程 — 知识盲区

### 盲区描述
§InputFlinger 的角色与演进（line 413）标注"[待验证：Android 15+ 中 InputFlinger 是否已支持独立进程隔离模式]"。如果 InputFlinger 在 Android 15/16 中真正实现独立进程（而非仍在 system_server 内），这对 Perfetto Trace 分析中 system_server 进程内 InputReader/Dispatcher 线程的可见性有直接影响。

### 重要程度
中

### 建议研究方向
- 调研 AOSP android-15/16 源码，确认 InputFlinger 是否运行在独立进程
- 确认 android-15/16 中 InputFlinger 的实际进程模型
- 分析对 Trace 分析方法的潜在影响

### 关联章节
3.1（本章）



## [2026-04-10] 3.2 触摸响应的性能分析 — 知识盲区

### 盲区描述
PAMTD（Perceivable Average Minimum Time to Display）= 11ms / 点击可接受时延 263ms 的原始学术论文出处缺失。当前引用来源为高爷微信公众号文章而非原始 HCI 学术研究。

### 重要程度
高

### 建议研究方向
- 追溯 PAMTD 指标的原始学术论文（可能是 Card et al. 或 Miller 的经典延迟感知研究）
- 查找 Android 触摸延迟的感知阈值相关的最新学术成果（2015-2024 年）
- 确认该数据是否被 Google 官方文档或 AOSP 文档引用

### 关联章节
3.2 触摸响应的性能分析

## [2026-04-10] 2.5 MainThread 与 RenderThread 协作 — 知识盲区

### 盲区描述
1. **RenderThread Animations API版本溯源**：正文(L380)称"从Android 7.0 (API 24)开始"，版本演进表(L424)称"API 23扩展"，两处矛盾。ViewPropertyAnimator平台API自API 12存在，但其RenderThread执行能力从哪个版本开始？API 23/24各扩展了什么动画类型？

2. **多窗口/PiP场景下RenderThread的调度机制**：多窗口并发时RenderThread如何调度多个Surface？PiP子窗口与主窗口渲染时序？系统内存压力导致GPU资源被抢占时对RenderThread的影响？

### 重要程度
高

### 建议研究方向
- 追溯AOSP：RenderThread.cpp中AnimationChannel的引入版本
- AOSP源码：不同窗口类型（Activity/Dialog/PopupWindow/PiP）渲染路径差异
- Perfetto trace采集：多窗口/PiP场景实际渲染时序

### 关联章节
2.3(VSync), 2.4(Choreographer), 2.6(SurfaceFlinger), 3.1(Input分发)


## [2026-04-10] 1.7 ART 编译管线与 dex2oat 优化 — 知识盲区

### 盲区描述
1. **OatWriter OAT 文件内部结构**：正文（L160-161）描述了编译流程（DEX→H图→机器码→OAT），但未说明 OatWriter 如何在 OAT 文件中物理组织编译后的机器码。理解按类（class）还是按方法（method）组织，对理解类加载性能很关键。

2. **Baseline Profiles / Cloud Profiles 的版本历史**：正文（L219-234）描述了三层 Profile 体系，但未说明 Baseline Profiles 通过 Play 系统下发是从哪个 Android 版本开始的（Android 13？），以及 Cloud Profiles 生成的触发条件（下载量阈值？设备类型？）。

### 重要程度
高

### 建议研究方向
- AOSP 源码：OatWriter::WriteCodeAndData() 中 ArtMethod/ArtField 的排列顺序
- 验证 OatWriter 是否按类为单位组织（同一类的所有方法连续排放）
- Google 官方文档：Baseline Profiles via Play 发布时间
- AOSP：ART Service 中 Cloud Profile 的处理逻辑

### 关联章节
1.6（Android 版本演进）, 4.3（ART 内存管理：OAT 文件内存映射）, 8.2（App 启动全流程：类加载路径）

## [2026-04-11] 1.12 AutoFDO 反馈导向编译优化 — 知识盲区

### 盲区描述
OEM/自研内核接入 AutoFDO 的关键前置条件缺失。正文提到 Kleaf、DDK、vendor 模块和 simpleperf，但没有说明哪些设备具备可用的 ETM/ETE/TRBE 采集能力、采集时是否需要 root/debug 接口、host 侧需要准备哪些符号（`vmlinux`/模块符号）、以及 profile 最终如何挂接到 Kleaf/DDK 构建目标。没有这些信息，读者很难把“知道有 AutoFDO”推进到“真的接进自家内核/模块”。

### 重要程度
高

### 建议研究方向
- 梳理 ARM64 设备采集 ETM/ETE/TRBE 数据的硬件与权限前提（Pixel/GKI 与 OEM 自研设备分别看）
- 补齐 simpleperf host 侧转换链路，明确 branch-list / create_llvm_prof / per-binary profile 的关系
- 调研 Kleaf / DDK 中内核与模块接入 AFDO profile 的 BUILD/Bazel 入口与示例
- 给出 vmlinux 与 vendor 模块分别生成/刷新 profile 的最小实践路径

### 关联章节
1.7（ART 编译管线）、8.7（Baseline Profiles）、14.2（Simpleperf）、16.1（Google 官方的性能优化思路）

## [2026-04-11] 1.14 锁竞争与同步性能分析 — 知识盲区

### 盲区描述
章节已经覆盖 Java monitor、futex 和 DeliQueue，但缺少 Native/system_server 真实热点锁的诊断路径。当前正文没有说明：Binder driver 的 wait queue 与 transaction priority inheritance 怎样区分于 Java monitor；native mutex / rwsem / system_server 全局锁链（如 WMS/AMS/SurfaceFlinger）在 Perfetto 中分别长什么样；当主线程卡在 Binder 时，如何判断根因是服务端锁竞争、线程池耗尽，还是驱动排队。

### 重要程度
高

### 建议研究方向
- 梳理 Binder driver wait queue、transaction priority inheritance、node priority inheritance 的当前实现与版本演进
- 研究 ART monitor、bionic pthread_mutex、binder driver waitqueue 在 Perfetto 中的可观测差异（track、blocked_function、SQL 模块、trace config）
- 补 1 个 system_server / SurfaceFlinger 锁链案例，覆盖 WMS GlobalLock、Binder 线程池耗尽、native mutex 三类路径

### 关联章节
1.4（Binder IPC 机制与性能影响）、1.5（线程模型）、2.12（Window Manager Service 与窗口管理）、14.10（Perfetto SQL Cookbook）


## [2026-04-11] 1.11 Zygote 机制与启动性能优化 — 知识盲区

### 盲区描述
章节提到了 `ZygotePreload`，但没有交代它依附的是 App Zygote / child zygote 机制，也没有解释 primary zygote、WebViewZygote、App Zygote 三者的职责边界。读者很容易误以为任意系统 App 都能直接向主 Zygote 注入自定义 preload。这个盲区会直接影响对启动优化能力边界的判断。

### 重要程度
高

### 建议研究方向
- 梳理 `AppZygote` / `ChildZygoteProcess` / `ZygotePreload` 在 Android 10+ 的完整调用链
- 补清 manifest `useAppZygote` / `zygotePreloadName` 与 isolated service 的约束条件
- 对比 primary zygote、WebViewZygote、App Zygote 的 preload 内容、隔离边界与性能收益
- 补一张“谁负责 fork 谁”的进程关系图，并对应 Perfetto/日志里可观测的 marker

### 关联章节
§1.11、§1.3、§8.2、§8.3

## [2026-04-11] 1.15 JNI/NDK 性能优化 — 知识盲区

### 盲区描述
章节没有覆盖 native 创建线程时的 `AttachCurrentThread` / `DetachCurrentThread` 成本、`JNIEnv*` 的线程亲和性，以及循环里 local reference 表膨胀这组三连坑。对媒体、游戏、端侧 AI 推理这类高频 JNI 场景，这些问题比单次 transition 纳秒数更容易成为真实性能瓶颈。

### 重要程度
高

### 建议研究方向
- `AttachCurrentThread` / `DetachCurrentThread` 在 Android 14-17 的行为边界与线程池复用建议
- local reference table overflow 的触发模式、批量 `DeleteLocalRef` 策略与实测案例
- `RegisterNatives`、线程附着、DirectByteBuffer 在端侧 AI / 音视频 pipeline 中的组合实践

### 关联章节
1.1、4.3、5.11、14.2


## [2026-04-11] 1.16 Audio Pipeline 延迟与性能 — 输入链路与 fast path 选路缺口

### 盲区描述
正文把 round-trip latency 当成关键指标，但实际只覆盖了输出链路。输入侧 `AudioRecord` / AAudio input / FastCapture / input MMAP 完全缺席，同时也没有解释 `LOW_LATENCY` 请求在 AudioPolicyService、`createTrack`、output profile 选择中的决策链。结果是读者知道 Normal / Fast / MMAP 三条路的名字，却还不能回答“为什么这条流没进 fast path”或“往返延迟的输入半边是谁在拖后腿”。

### 重要程度
高

### 建议研究方向
- 补输入侧数据链：App → RecordThread / FastCapture → HAL → DSP / Mic
- 梳理 `AudioTrack` / AAudio 创建流时的关键决策链：request flag、profile match、fast track slot、MMAP output 选择
- 给 round-trip latency 增加一张输入/输出双向时序图，并标注 Perfetto 中可观测的线程与事件
- 对比普通 capture、FastCapture、MMAP input 在调度与缓冲模型上的差异

### 关联章节
§1.16、§1.4 Binder IPC、§5.1 CPU 调度、§16.5 Android 17 变更

## [2026-04-11] 1.17 IPC 全景：Android 进程间通信机制对比与性能选型 — 知识盲区

### 盲区描述
章节把 Binder、共享内存、FMQ、socket 当成并列机制，但缺少 Android 实战里最关键的“控制面 / 数据面”组合模型。尤其是 `BINDER_TYPE_FD`、`ParcelFileDescriptor`、`SCM_RIGHTS` 这条 fd 传递链没有展开，导致 BufferQueue、CursorWindow、GraphicBuffer 这类零拷贝方案的真实工作方式解释不完整。

### 重要程度
高

### 建议研究方向
- 梳理 Binder `BINDER_TYPE_FD`、Java `ParcelFileDescriptor`、native `SCM_RIGHTS` 的角色边界
- 用 BufferQueue / CursorWindow / SharedMemory 各做一个“控制面 + 数据面”案例
- 补充 Stable AIDL HAL、HIDL HwBinder、FMQ 在 HAL 场景下的搭配关系

### 关联章节
1.4, 1.10, 2.13, 2.15


## [Task9 Deep Review] 2.3 VSync 机制 — 2026-04-11

### 盲区 1：Android 13+ 当前 VSync 调度链（app / appSf）
**描述**：正文已经引入 `vsync-appSf` 和 `VsyncConfiguration / VSyncPredictor / VSyncReactor`，但没有把 Android 13+ 当前实现从 `Scheduler::createEventThread("app"/"appSf")`、`VSyncDispatchTimerQueue` 调度，到 `EventThread` / BitTube / `DisplayEventReceiver` 的真实链路讲透，反而混入了旧版 `DispSyncSource` / `CallbackRepeater` 命名。读者会分不清历史 DispSync 时代与当前 Scheduler 时代的边界。

**重要程度**：高

**建议研究方向**：
- 梳理 android-16 `services/surfaceflinger/Scheduler/{Scheduler.cpp, EventThread.cpp, VSyncDispatchTimerQueue.cpp, VSyncPredictor.cpp, VSyncReactor.cpp}` 的调用关系
- 对比 Android 10 的 DispSync 时代和 Android 13+ 的 `app/appSf` 双 EventThread 架构
- 补一张 current vs historical call chain 图，明确 VSYNC-app / VSYNC-sf / VSYNC-appSf 的来源与消费者

**关联章节**：§2.3、§2.4、§2.6

### 盲区 2：Android 17 DeliQueue 对 VSync/Choreographer 的公开证据链
**描述**：§9.6 已给出 DeliQueue 的结构、量化收益和 Perfetto 观察结论，但公开可复核的源码 tag、trace 样本和 benchmark 来源仍不闭环。当前章节把 preview 级结论直接并入 VSync 主线，会放大版本叙事风险。

**重要程度**：高

**建议研究方向**：
- 等待 android-17 public tag 后核实 `MessageQueue` / `Looper` 实现与 DeliQueue 开关路径
- 找公开 trace 或官方 benchmark，确认“4% 掉帧下降 / 9.1% 首帧改善”适用范围
- 明确 DeliQueue 影响的是 `doFrame` 排队延迟、还是 VSync 调度本身，避免把 Looper 改动写成 VSync 机制改动

**关联章节**：§2.3、§2.4、§1.13


## [2026-04-11] 16.1 Google 官方的性能优化思路 — 优化交付路径矩阵缺口

### 盲区描述
正文把系统性能优化放在一条主线上讲，但没有把优化真正“怎么到达用户设备”讲清楚。现在至少混在一起了四条路径：完整 OTA、GKI kernel 分支更新、Play System Update(APEX/Mainline)、以及 Play 安装期/云端 Profile 编译。缺少这张矩阵，读者会把内核优化、ART 模块更新、Cloud Profiles 误认为同一条分发通道。

### 重要程度
高

### 建议研究方向
- 梳理 OTA / GKI / APEX(Mainline) / Play 安装期 Profile 四条路径的边界与触发条件
- 给 AutoFDO、DeliQueue、ART generational GC、Cloud Profiles 各自标注真实分发链路
- 补“系统版本升级”和“Google Play 系统更新”在用户侧的可见差异
- 做一张“技术 -> 分发通道 -> 到达范围 -> 依赖前提”的对照表

### 关联章节
1.12（AutoFDO）, 1.13（DeliQueue）, 8.7（Baseline Profiles）, 16.4（Android 17 + Kernel 6.12 系统级性能优化）

## [2026-04-11] 16.1 Google 官方的性能优化思路 — MessageQueue / Binder 演进时间线缺口

### 盲区描述
正文试图把 Handler/MessageQueue 与 Binder 的性能演进压缩成几句话，但缺少“版本-实现-能力边界”三元关系。没有讲清 legacy locked queue、Android 17 新队列实现、targetSdk gating、Binder thread pool 上限配置、nice/RT priority inheritance、binder 与 hwbinder 域差异，读者很容易记住几个结论，却记错它们分别属于哪个版本和哪个实现。

### 重要程度
高

### 建议研究方向
- 梳理 Android 14-17 MessageQueue 实现谱系与 targetSdk gating
- 用 AOSP 精确路径补全 legacy / concurrent / combined / semi-concurrent queue 的实现差异
- 补 Binder thread pool 的默认上限、按需扩容机制和 `BINDER_SET_MAX_THREADS` / `ProcessState` 关系
- 区分 binder / hwbinder 的 priority inheritance 语义与 Android 8 之后的演进

### 关联章节
1.4（Binder IPC 机制与性能影响）, 1.13（DeliQueue）, 14.10（Perfetto SQL Cookbook）, 16.1（Google 官方的性能优化思路）

## [2026-04-11] 2.13 图形缓冲区管理 (BufferQueue) — 同步栅栏链路

### 盲区描述
正文把重点放在 slot 状态和三缓冲，但几乎没覆盖 acquire fence、release fence、dequeue fence 这条同步链。AOSP `BufferSlot.h` 明确要求 QUEUED / ACQUIRED 状态下必须等待 fence signal 才能安全访问 buffer；如果不把 fence 讲清楚，读者很难解释“queue 了为什么还不能合成”“dequeueBuffer 为什么会卡在 release fence 之后”。这会直接削弱 Perfetto 卡顿定位能力。

### 重要程度
高

### 建议研究方向
- 追 `IGraphicBufferProducer::dequeueBuffer()` / `queueBuffer()` 与 `BufferSlot.h` 中 fence 语义的对应关系
- 补 `acquire fence`、`release fence`、`dequeue fence` 在 App / SurfaceFlinger / HWC 三方之间的传递链
- 对应到 §2.16 Sync Fence，补一张“slot 状态 + fence 信号”的联合时序图

### 关联章节
§2.13、§2.16、§2.6、§13.1-§13.5

## [2026-04-11] 2.13 图形缓冲区管理 (BufferQueue) — BLAST 同步事务细节

### 盲区描述
BLASTBufferQueue 小节只讲了“App 本地管理 buffer，最后用 Transaction 提交”，但没有展开 app 侧 `createBufferQueue()`、`BLASTBufferItemConsumer`、`setFrameAvailableListener()`、`Transaction::setBuffer(..., frameNumber)`、`mergeWithNextTransaction()` / `applyPendingTransactions()` 这条同步链。这样会把 BLAST 写成“少一次 Binder hop”的性能优化，而漏掉它真正解决的 buffer 与 geometry transaction 对齐问题。

### 重要程度
高

### 建议研究方向
- 追 `BLASTBufferQueue.cpp` 中本地 producer / consumer 的创建与回调链
- 说明 frameNumber gating 与 pending transaction merge 如何避免 resize / relayout 场景下的错帧
- 补一张“传统 BufferQueue vs BLASTBufferQueue”的同步路径对比图

### 关联章节
§2.13、§2.12、§2.6、§2.9

## [2026-04-11] 2.14 图形 API 演进与选择策略（OpenGL ES / Vulkan / ANGLE） — 知识盲区

### 盲区描述
章节已经给出 ANGLE allowlist / denylist 的结论，但没有把 Android 上真正决定“某个包是否走 ANGLE、何时回退 native GLES”的选路链讲清楚，也没有拆开 system ANGLE driver 与 Chromium / WebView 自身图形 backend 的边界。对于 API 选型和线上问题定位，这是最容易踩坑的部分。

### 重要程度
高

### 建议研究方向
- 梳理 ANGLE driver package、rules file、per-app override、adb / developer option 与 native fallback 的完整链路
- 验证 Android 16 / 17 新设备政策与旧设备升级场景的差异
- 拆分 Chromium / WebView / WebGL 的 GPU backend 选择逻辑，确认哪些路径受系统 ANGLE policy 影响，哪些由 Chromium build 决定
- 为 Perfetto / AGI 补一张“native Vulkan / GLES / ANGLE / Chromium-WebView”判定矩阵

### 关联章节
§2.9、§2.14、§14.8

## [Task9 Deep Review] 2.15 DMA-BUF、Gralloc 与跨进程图形内存共享 — 2026-04-11

### 盲区 1：BLASTBufferQueue 与 handle cache 的现代窗口路径
**描述**：正文把跨进程共享写成经典的 App → SurfaceFlinger 直连模型，但没有补 Android 现代窗口路径里 BLASTBufferQueue、本地 consumer、slot mirror 和 handle cache 的分层关系。缺这一层，读者很容易把 app 侧 `queueBuffer()`、SurfaceFlinger import、GraphicBuffer 首次同步混成一个事件，进而误判 trace 上的阻塞位置。

**重要程度**：高

**建议研究方向**：
- BLASTBufferQueue / BufferStateLayer 在 modern window path 中的职责边界
- `requestBuffer()` / `BUFFER_NEEDS_REALLOCATION` / consumer import cache 的真实时机
- 在 Perfetto 中如何把 app 侧 `queueBuffer()`、BLAST `QueuedBuffer` 和 SurfaceFlinger `latchBuffer` 串起来

**关联章节**：§2.13 BufferQueue、§2.15 DMA-BUF 与 Gralloc、§2.6 SurfaceFlinger

## [2026-04-11] 2.16 Sync Fence 框架与帧同步机制 — 现代 explicit sync 演进链缺失

### 盲区描述
章节没有把 Android 图形同步的现代演进链讲完整：HWC1 → HWC2 的 fence 语义变化、legacy `sync_timeline`/`sync_pt`/`sync_fence` 与 modern `sync_file` API 的对应关系、HWUI/Skia 在当前版本里如何生成 release fence、present fence 又怎样进入 `VSyncReactor` / FrameTimeline。这些节点分散出现在正文里，但没有被串成一条能指导源码核对与 Perfetto 分析的主线。

### 重要程度
高

### 建议研究方向
- 对比 `android-7.0.0_r1`、`android-8.1.0_r81`、`android-16.0.0_r1` 的 `HWC2.h`、`libsync`、`libs/hwui/pipeline/skia/`
- 梳理 `queueBuffer()` 输入 fence、`releaseBuffer()` 返回 fence、`presentDisplay()` present fence 三类 fence 在 producer / consumer / HWC 三侧的命名映射
- 用一段真实 Perfetto + `dumpsys SurfaceFlinger` 样例验证 acquire / release / present fence 的 trace 位置与等待路径

### 关联章节
§2.3 VSync、§2.5 MainThread 与 RenderThread、§2.6 SurfaceFlinger、§2.13 BufferQueue、§2.15 DMA-BUF 与 Gralloc


## [2026-04-11] 2.19 刷新率切换与帧率适配性能 — 知识盲区

### 盲区描述
章节讨论 ARR 时仍以 `Surface.setFrameRate(float, int)` 的旧模型为主，没有把 Android 15+ 的 `Surface.FrameRateParams`、`Display.FRAME_RATE_CATEGORY_*`、`Display.getSuggestedFrameRate(int)` 等 category/range API 讲清楚，也没有说明它们与 exact-fps 请求的适用边界。

### 重要程度
高

### 建议研究方向
- 梳理 `Surface.setFrameRate(float, int)` → `Surface.FrameRateParams` 的 public API 演进路径
- 结合 `Display.FRAME_RATE_CATEGORY_NORMAL/HIGH`、`Display.getSuggestedFrameRate(int)` 写一套 Android 15+ 的场景化建议
- 补充 RecyclerView / Compose 在 ARR 设备上的真实调用路径和版本边界

### 关联章节
2.18, 2.4

## [2026-04-11] 2.18 Adaptive Refresh Rate 与动态帧率控制 — View 层 ARR API 与滚动速度通路

### 盲区描述
章节把 App 侧 ARR 适配几乎全部收敛到 `Surface.setFrameRate()`，但 Android 15-QPR1+/16 的官方主线已经转向 View / Compose：`View.setRequestedFrameRate()`、`View.setFrameContentVelocity()`、RecyclerView 1.4 / NestedScrollView 的滚动速度上报，以及 Compose 的 `preferredFrameRate()`。如果这一层不补，读者会知道系统侧有 ARR，却不知道 App 侧该如何正确表达帧率意图。

### 重要程度
高

### 建议研究方向
- 核对 android-16.0.0_r1 `View.java` 中 `setRequestedFrameRate()` / `setFrameContentVelocity()` 的行为与限制
- 追踪 AndroidX RecyclerView 1.4 的 ARR 实现，确认 fling / smooth scroll 如何上报 velocity
- 梳理 `Surface.setFrameRate()`、View `requestedFrameRate`、Compose `preferredFrameRate()` 三者的分工边界
- 补一个滚动场景的 Perfetto / FrameTimeline 例子，说明 velocity 与 refresh-rate 变化如何对应

### 关联章节
2.4（Choreographer）、2.17（Frame Pacing Library）、7.8（RecyclerView 列表滑动性能深度优化）

## [Task9 Deep Review] 3.4 输入延迟与预测输入技术 — 2026-04-11

### 盲区 1：batched input / unbuffered dispatch / resampling 的系统内建低延迟路径
**描述**：正文把输入送达 App 和下一帧 doFrame 渲染几乎讲成了同一件事，没有补 ViewRootImpl 的两条关键分叉：一条是 processRawInputEvent() 立即处理路径，另一条是 onBatchedInputEventPending() -> scheduleConsumeBatchedInput() -> Choreographer.CALLBACK_INPUT 的批量消费路径。touch resampling 也没有出现，导致“为什么输入有时立刻处理、有时会贴着 VSync 走”解释不完整。

**重要程度**：高

**建议研究方向**：
- ViewRootImpl.WindowInputEventReceiver.processRawInputEvent() / onBatchedInputEventPending() / scheduleConsumeBatchedInput()
- InputConsumer consumeBatchedInputEvents 与 resampling 的触发条件
- unbuffered input dispatch 对 stylus / drawing / game 场景的影响

**关联章节**：§3.1、§3.2、§3.4、§2.3、§2.4

### 盲区 2：Perfetto end-to-end input latency 的生成条件
**描述**：章节给出了 android_input_events 的 SQL 和字段，但没有解释 end_to_end_latency_dur 依赖什么链路才能生成。AOSP ViewRootImpl 里 InputMetricsListener 通过 HardwareRendererObserver、FrameMetrics.Index.INPUT_EVENT_ID、DISPLAY_PRESENT_TIME / GPU_COMPLETED 去回填 timeline。少了这部分，读者很难理解为什么有些 trace 里 e2e latency 是 null，或者为什么没有 FrameTimeline 时无法算完整端到端。

**重要程度**：高

**建议研究方向**：
- ViewRootImpl.InputMetricsListener 与 HardwareRendererObserver 的工作方式
- FrameMetrics.Index.INPUT_EVENT_ID / DISPLAY_PRESENT_TIME / GPU_COMPLETED 的采样条件
- Perfetto android_input_events 模块如何把 input id 和 frame timeline 关联起来

**关联章节**：§3.4、§13.3、§13.5、§2.4



## [2026-04-11] 2.20 多窗口与桌面模式渲染性能 — 多窗口生命周期与渲染节流

### 盲区描述
正文把“窗口失去焦点”和“Activity 停止可见”近似处理，没有覆盖 Android 10+ multi-resume、top-resumed activity、`onTopResumedActivityChanged()` 这些直接影响渲染节流策略的生命周期边界。对分屏、PiP、桌面窗口来说，这是多窗口性能分析的基础前提。

### 重要程度
高

### 建议研究方向
- 官方 multi-window 文档中 multi-resume / top-resumed / onStop 语义
- `onTopResumedActivityChanged()` 与相机、视频、动画等独占资源的关系
- 分屏、PiP、桌面窗口三种形态下 focus / visible / resumed 的区别

### 关联章节
§2.20、§2.12、§7.4

## [2026-04-11] 2.20 多窗口与桌面模式渲染性能 — Desktop Windowing / Connected Displays 版本与设备矩阵

### 盲区描述
正文把 OEM/大屏设备的 desktop windowing、Android 16 connected displays、外接显示器上的独立 desktop session、以及 Pixel 机型支持范围写成了一条线，版本与设备边界混在一起。读者很难判断某条结论到底适用于平板、折叠屏、ChromeOS，还是只适用于手机外接显示器。

### 重要程度
高

### 建议研究方向
- `support-desktop-windowing` 与 `support-connected-displays` 官方文档的行为边界
- 手机连接外接显示器时的独立 desktop session，与 desktop-windowing enabled device 的扩展模式差异
- Pixel / Samsung 等具体机型支持范围对应的 release note 或官方博客

### 关联章节
§2.20、§2.12、§2.18

## [2026-04-11] 2.21 文字渲染性能 — 知识盲区

### 盲区描述
章节多次指导读者去 Perfetto 里找 TextView.onMeasure、RenderThread 文本绘制、glyph upload、TextBlob 命中，但没有交代默认 trace、gfx/hwui atrace、FrameTimeline、SQL 视图之间各自能看到什么。没有这张“观测面清单”，读者很难判断某个文字性能问题到底该在 MainThread、RenderThread 还是 tracing 配置本身上定位。

### 重要程度
高

### 建议研究方向
- 核对默认 Perfetto 配置下，文字相关问题能直接看到哪些 slice / track
- 补 gfx/hwui/atrace 额外配置后，哪些 HWUI/Skia 事件会出现，哪些仍然不可见
- 给一组“TextView.onMeasure 过长”和一组“RenderThread 纹理上传/首次渲染”示例 trace
- 关联 §13.9 tracing 基础设施，说明为什么同一段文字问题在不同 trace 配置下可见性不同

### 关联章节
2.21、2.5、7.8、7.12、13.9

---

## [2026-04-11] 2.21 文字渲染性能 — 知识盲区

### 盲区描述
Emoji 一节把系统字体、EmojiCompat、下载字体 provider、color font 和“Bitmap Emoji”混成一条线，但没有说明这些机制各自的版本范围和实现边界。结果是正文既写了 EmojiCompat 的 ReplacementSpan/字体路径，又写了 Android 11 之后统一转向 Bitmap 的结论，前后标准不一致。

### 重要程度
高

### 建议研究方向
- 梳理 Android 8-16 间系统 emoji 字体、EmojiCompat/emoji2、下载字体 provider 的时间线
- 区分系统 color font 渲染、EmojiCompat span 渲染、厂商自定义 emoji 字体三类路径
- 核对 NotoColorEmoji / downloadable fonts / EmojiCompatInitializer 的官方文档与 AndroidX 源码
- 补充“哪些说法来自系统实现，哪些只适用于 AndroidX emoji2”的边界说明

### 关联章节
2.21、7.8、7.10、13.9


## [2026-04-12] 3.5 输入事件拦截与安全机制 — 无障碍输入变换链的真实组件边界

### 盲区描述
章节把无障碍输入写成“按键走 InputFilter，触摸走 AccessibilityInteractionController”，但没有把 `AccessibilityInputFilter`、`KeyboardInterceptor`、`TouchExplorer`、`MotionEventInjector` 这些真实组件串起来。读者看完仍然很难回答：按键过滤和触摸探索分别在哪一层完成？哪些事件是原始事件，哪些是消费后重新注入的事件？

### 重要程度
高

### 建议研究方向
- 梳理 `AccessibilityInputFilter.onInputEvent()` 对 KeyEvent / MotionEvent 的两条处理分支
- 追 `KeyboardInterceptor` → `AccessibilityManagerService.notifyKeyEvent()` → `KeyEventDispatcher` 的 500ms 超时机制
- 追 `TouchExplorer` / `MotionEventInjector` 如何把探索手势转成新的 MotionEvent
- 明确 App 侧能看到哪些 flag / source，哪些只是 InputDispatcher 内部 policy flag

### 关联章节
3.1、3.5、9.1、9.2

## [2026-04-12] 3.5 输入事件拦截与安全机制 — 输入安全策略版本演进证据链

### 盲区描述
当前版本表把 Android 4.3 / 8.0 / 9 / 10 / 12 / 13 / 14 的输入安全变化揉在一起，但多数条目没有给出一手依据，且 10 / 13 / 14 至少三条可以直接被现有源码推翻。这个主题需要单独建立“版本号 → 变更点 → 一手证据”的证据链，否则章节会持续复写错误结论。

### 重要程度
高

### 建议研究方向
- 逐个核对 android-4.3.1_r1、android-8.0.0_r1、android-9.0.0_r1、android-10.0.0_r1、android-13.0.0_r1、android-14.0.0_r1 中输入注入和 accessibility 相关 API/权限变更
- 为每个版本条目绑定至少一条一手证据（AOSP tag、官方文档、release notes）
- 单独区分“权限/能力声明”“系统白名单”“App 侧可观测标记”三类变化，避免混写

### 关联章节
3.5、9.2、16.2

## [2026-04-12] 3.6 手势识别算法与性能优化 — VelocityTracker 策略矩阵与版本演进

### 盲区描述
当前章节把 `VelocityTracker` 的 Java wrapper、JNI 边界、native `VelocityTracker.cpp` 策略实现混在一起写，并虚构了 `VelocityTrackerFallbackStrategy.java`。这会让读者误判“默认策略”到底发生在 Java 层还是 native 层，也看不清 X/Y 轴与 scroll axis 的默认策略差异。

### 重要程度
高

### 建议研究方向
- 核对 `android.view.VelocityTracker` 与 `frameworks/native/libs/input/VelocityTracker.cpp` 的真实调用链
- 梳理默认策略按 axis 选择的规则，区分 X/Y 与 scroll axis
- 核对 `obtain(String strategy)` / `obtain(int strategy)` 的调试或测试属性，不要写成生产默认路径
- 对比 Android 10、13、14、16 的策略矩阵与公开 API 变化，确认是否真的存在可写进“版本演进表”的切换点

### 关联章节
§3.6、§3.4、§2.4


## [2026-04-12] 4.8 ART 分代垃圾回收与 GC 暂停优化 — 知识盲区

### 盲区描述
章节把 Android 17 的分代 GC 近似写成“young / old 两代 + Write Barrier / Card Table / Remembered Set”。但当前 AOSP generational MarkCompact 路径已经出现 `YoungMarkCompact`、young / mid / old 三代、old-gen aged cards、native roots to young/mid generation、userfaultfd slow path 等关键实现细节。缺少这些 collector-specific 机制，读者很难把“Android 10 的 generational CC”与“Android 15+/17 的 generational CMC”区分开。

### 重要程度
高

### 建议研究方向
- 核对 `art/runtime/gc/collector/mark_compact.h/.cc` 中 `YoungMarkCompact`、`mid_gen_end_`、`old_gen_end_`、`ScanOldGenObjects()` 的真实职责
- 明确 Android 10 generational CC 与 Android 15+/17 generational CMC 的差异：read barrier、userfaultfd、代际提升规则
- 追踪 `use_generational_cmc`、`persist.device_config.runtime_native_boot.use_generational_gc` 等开关与版本边界

### 关联章节
§4.3、§4.6、§13.10

## [2026-04-12] 4.8 ART 分代垃圾回收与 GC 暂停优化 — Perfetto GC 分析前置条件

### 盲区描述
章节直接给出 `android_garbage_collection_events`、`actual_frame_timeline` 和 `heapprofd` 的查询/命令，但没有说明 trace config、stdlib 版本、表字段和 Java heap sampling / Java heap dump 的边界。缺少这些前置条件，读者照着执行很容易查不到表、字段不匹配，或者把 Java heap dump 和 allocation sampling 混为一谈。

### 重要程度
中

### 建议研究方向
- 整理 `android_garbage_collection_events` / FrameTimeline 相关表的字段、JOIN 关系和版本前提
- 补一组“最小可运行”Perfetto 配置，区分 GC event、Java heap dump、Java heap sampling 三条链
- 说明 `packages_list` / process / thread JOIN 后怎样稳定拿到包名与线程名

### 关联章节
§4.8、§7.2、§13.2、§13.10、§14.3


## [2026-04-12] 5.8 后台执行限制与优化 — 知识盲区（后台任务豁免矩阵）

### 盲区描述
正文把后台任务选型收敛成 WorkManager / JobScheduler / AlarmManager / FGS 四选一，但缺少 Android 12-16 真正常用的豁免路径：expedited jobs、user-initiated data transfer jobs、temporary allowlist、FCM 高优先级、exact alarm 特殊访问等。没有这部分，读者很难解释“为什么某个后台任务在限制开启后仍然跑了起来”。

### 重要程度
高

### 建议研究方向
- 对比 WorkManager expedited work、JobScheduler user-initiated jobs / UIDT 与普通 job 的配额差异
- 梳理 Android 12-16 的 foreground-service start exemptions、temporary allowlist 和 FCM 高优先级触发条件
- 给出 2-3 个“同样是后台同步，为什么一个能跑一个不能跑”的对照案例

### 关联章节
5.6（Android 功耗管理）、5.8（后台执行限制）、8.4（后台启动/响应速度）、11.2（App 端功耗优化）

## [2026-04-12] 5.8 后台执行限制与优化 — 知识盲区（可观测性闭环）

### 盲区描述
当前章节提到了 Perfetto、`dumpsys deviceidle`、Standby Bucket 和 JobScheduler pending reason，但没有形成一套可复核的观测闭环。缺少“抓什么 trace / 看什么 dumpsys / 对应什么症状”的系统性方法，读者仍然很难把后台限制问题落到证据上。

### 重要程度
中

### 建议研究方向
- 整理 `dumpsys deviceidle`、`dumpsys usagestats appstandby`、`dumpsys jobscheduler`、`cmd jobscheduler` 的最小排查流程
- 验证 Perfetto 中可稳定观察的 device idle / job delay / alarm 受限信号，必要时改用 Battery Historian 作为主证据
- 补一个“后台任务未执行”的端到端排查案例，从权限、bucket、Doze、quota 一路走到结论

### 关联章节
5.6（Android 功耗管理）、5.8（后台执行限制）、14.x（工具与调试章节）

## [2026-04-12] 2.7 Hardware Layer — View Layer / RenderNode / Compose graphicsLayer 语义边界

### 盲区描述
当前章节把 `View.setLayerType(LAYER_TYPE_HARDWARE)`、`RenderNode.setUseCompositingLayer(...)`、Compose `Modifier.graphicsLayer` 基本视为同一套“强制缓存成 GPU 纹理”的机制，但 Android 10+ / Compose 1.4+ 以后，这三者在“是否一定分配离屏缓冲”“何时自动晋升 compositing layer”“是否只是 draw layer isolation”上已经出现明显分化。若不把这些边界讲清楚，读者会把 View 时代的 Hardware Layer 经验直接套到 Compose。

### 重要程度
高

### 建议研究方向
- 对照 `android.graphics.RenderNode` 注释，梳理自动晋升 compositing layer 与手动 `forceToLayer` 的边界
- 补 Compose `graphicsLayer` / `CompositingStrategy.Auto` / `Offscreen` / `ModulateAlpha` / `rememberGraphicsLayer()` 的官方语义
- 用一组 Perfetto/FrameTimeline 例子区分 View Hardware Layer、RenderNode forced layer、Compose draw layer 在 trace 中分别长什么样

### 关联章节
2.5、2.7、7.1、7.5

## [2026-04-12] 5.10 JobScheduler/WorkManager 调度与后台任务性能 — 知识盲区

### 盲区描述
章节把 UIDT 只写成“用户发起的长时间数据传输方案”，但没有交代真正会影响实现决策的边界条件：`JobInfo.Builder.setUserInitiated(true)` 仅在 API 34+ 可用，调度时要求前台或允许后台启动 Activity 的状态，需要 `RUN_USER_INITIATED_JOBS` 权限，运行中必须调用 `JobService.setNotification(...)` 绑定通知，Android 14 还要求它是 network data transfer。缺少这些条件后，读者很容易把 UIDT 当成“更强的 WorkManager/FGS 替代品”。

### 重要程度
高

### 建议研究方向
- 系统梳理 UIDT、Expedited Job、Foreground Service、WorkManager 的选择边界和失败返回条件（`RESULT_FAILURE` / quota / user stop）
- 补齐 `setUserInitiated(true)` 的权限、通知、网络约束、停止后不可重调度等官方要求
- 给出一个“用户点击下载大文件”场景的决策树，串起 UIDT 与 5.8 / 11.2 的限制条件

### 关联章节
5.8、11.2、15.5

## [2026-04-12] 5.10 JobScheduler/WorkManager 调度与后台任务性能 — 观测面知识盲区

### 盲区描述
Perfetto 观测面被写成一个平面概念，但实际上至少有三层来源：`android.job_scheduler_states` 模块来自 `ScheduledJobStateChanged` statsd atom，`android.job_scheduler` 模块来自 system_server atrace `ss`，UI 里的 Jobs/Long Wake locks track 又依赖 trace 中实际采到的轨道。正文没有把“采集配置 → 生成哪张表/哪条轨”说清楚，读者难以复现实战排查。

### 重要程度
高

### 建议研究方向
- 区分 statsd atom、atrace、UI track 三种观测面的对应关系
- 给出最小可复现的 Perfetto 配置，并说明何时用 `android_job_scheduler_states`，何时只能看 `android_job_scheduler_events`
- 补一组真实 trace + SQL 查询，验证 `pending reason` 与轨道表现如何互相对照

### 关联章节
5.10、15.5



## [2026-04-12] 2.8 过度绘制 — 现代 HWUI / Skia overdraw 调试实现

### 盲区描述
章节 frontmatter 写的是 `last_verified_against: AOSP android-16.0.0_r1`，但参考资料只保留了早期 `frameworks/base/libs/hwui/OpenGLRenderer.cpp`。对于 Android 10-16 的 HWUI / Skia 路径，Debug GPU Overdraw 的实现入口、system property、与 RenderThread / FrameTimeline 的关系都没有落点，导致“现代版本里 overdraw 调试到底靠什么实现”这一层仍是黑盒。

### 重要程度
高

### 建议研究方向
- 梳理 android-16 `frameworks/base/libs/hwui/` 中 overdraw debug 的实现入口与调试开关
- 确认 Debug GPU Overdraw 在 SkiaGL / SkiaVulkan 路径下的着色或计数实现
- 对齐开发者选项颜色叠加、HWUI slice、FrameTimeline 和 GPU 工具之间的证据关系

### 关联章节
2.5（MainThread 与 RenderThread 协作）、2.6（SurfaceFlinger 与合成）、2.10（GPU 渲染深入）、13.1（Perfetto 基础）

## [2026-04-12] 2.8 过度绘制 — Compose layer / offscreen compositing / overdraw 边界

### 盲区描述
当前 Compose 小节把 `background`、`drawBehind`、`derivedStateOf` 放在一起讨论，但没有区分哪些 API 真正增加像素重复填充，哪些只是减少 recomposition 或 draw phase 的 CPU 开销。对于 Compose UI，`graphicsLayer`、`CompositingStrategy`、alpha、shadow、blur 是否触发离屏 buffer，以及这些行为和 overdraw 指标的关系，都还没有讲清楚。

### 重要程度
高

### 建议研究方向
- 对照 `graphicsLayer` / `CompositingStrategy` / alpha / shadow / blur，梳理哪些场景会增加 offscreen pass 或额外 fill
- 用 Layout Inspector、Android GPU Inspector 或真实 trace 验证 nested background、alpha、graphicsLayer 对 overdraw 的实际影响
- 明确区分“减少重组/状态读取”和“减少 overdraw”的边界，避免把 CPU 优化写成 GPU fill 优化

### 关联章节
2.7（Hardware Layer）、2.8（过度绘制）、7.7（Compose 性能）

## [2026-04-12] 1.9 Package Manager Service 与应用安装性能 — 知识盲区

### 盲区描述
章节没有把 Android 14+ / 16 的现代安装与编译控制链讲完整：`PackageManagerShellCommand -> PackageInstallerSession -> InstallPackageHelper / DexOptHelper -> ART Service / artd / IInstalld`。当前文本把 PMS、installd、dex2oat 压成一层，读者很难建立“安装会话管理”和“编译任务调度”之间的真实边界。

### 重要程度
高

### 建议研究方向
- 对照 `PackageManagerShellCommand.java`、`PackageInstallerSession.java`、`InstallPackageHelper.java`、`DexOptHelper.java` 画出现代安装控制链
- 补出 `Installer.java`、`IInstalld` 与 `artd` / ART Service 的职责分界
- 区分 `adb install`、Play 安装、OTA 后 dexopt 三种触发入口在控制链上的差异

### 关联章节
§1.7、§1.9、§8.2、§8.3



## [2026-04-12] 5.9 ADPF 自适应性能框架 — 控制面分层盲区

### 盲区描述
章节直接从 App 侧 API 跳到“系统会提频 / 系统会热管理”，但没有把 `PerformanceHintManager.Session -> HintManagerService -> vendor power hint HAL/AIDL`，以及 `PowerManager -> IThermalService -> Thermal HAL` 的中间层写出来。缺了这两段，读者无法判断 ADPF 问题该落在 App 集成、system_server 转发，还是 OEM / SoC 实现。

### 重要程度
高

### 建议研究方向
- AOSP `frameworks/base/core/java/android/os/PerformanceHintManager.java`
- AOSP `services/core/java/com/android/server/power/hint/HintManagerService.java`
- `IHintManager` / vendor power hint HAL 或 AIDL 入口
- `PowerManager`、`IThermalService` 与 `hardware/interfaces/thermal/` 的分层关系

### 关联章节
§5.5、§5.6、§5.9

## [2026-04-12] 5.9 ADPF 自适应性能框架 — ADPF 观测证据盲区

### 盲区描述
Perfetto 段落没有给出可复现的观测路径。当前章节直接写 `power.hint_session` / `power.thermal`，但没有 trace config、截图、SQL、可见 counter 名称，也没有说明哪些现象来自 Perfetto，哪些更适合用 AGI、Frame Timeline、CPU frequency 或 PowerManager 热状态去看。

### 重要程度
高

### 建议研究方向
- 一份可复现的 ADPF TraceConfig，覆盖 CPU frequency、Frame Timeline、热状态与电源数据源
- 验证 HintSession 是否会以固定 track 名称暴露，还是需要依赖自定义 trace / OEM 实现
- 补一组真实案例：ADPF 开 / 关对比，CPU-bound 与 GPU-bound 各一组
- 明确 Perfetto / AGI / Game Dashboard 各自负责观察什么

### 关联章节
§5.9、§7.5、§13.2、§13.3、§13.7、§14.8

## [2026-04-12] 5.7 CPU 相关的版本演进 — 调度意图传递链缺口

### 盲区描述
章节从 Android 10 的 EAS 直接跳到 GKI / Android 15，缺少 Android 11-14 这段对 CPU 调度最关键的“意图传递”演进：schedtune 向 uclamp 的迁移、task_profiles.json / libprocessgroup 如何把前台、后台、top-app、latency-sensitive 等意图传给调度器，以及这条链路和 ADPF / PerformanceHint 的关系。没有这段，读者无法把“EAS 会怎么调度”与“系统和 App 怎样表达调度诉求”串起来。

### 重要程度
高

### 建议研究方向
- 核对 Android common kernel 中 schedtune 退场与 uclamp 生效的时间线
- 调研 `system/core/libprocessgroup/profiles/task_profiles.json` 与 task profile 继承关系
- 补充 `android15-6.6` 中 `android_rvh_uclamp_eff_get` 等 hook 与厂商调优的连接点
- 连接 `PerformanceHintManager` / ADPF 与 task profile / uclamp 的实际传递路径

### 关联章节
§5.2 EAS 能量感知调度、§5.9 ADPF 自适应性能框架、§5.6 Android 功耗管理

## [2026-04-12] 1.1 Android 分层架构 — Treble 硬边界的落地机制

### 盲区描述
正文多次提到 Treble 在 Framework 和 HAL 之间画出“硬边界”，但没有把这条边界如何在 AOSP 中真正成立讲出来。当前缺失的关键环节包括：system/vendor 分区切分、VINTF manifest / compatibility matrix、HIDL passthrough vs binderized 的边界、AIDL HAL 为什么只能 binderized。没有这层实现细节，读者很难理解“Treble 解决的到底是接口语言问题，还是系统升级兼容性问题”。

### 重要程度
高

### 建议研究方向
- 调研 VINTF manifest / compatibility matrix 的校验链路与 system/vendor 分区边界
- 对比 HIDL passthrough、HIDL binderized、AIDL HAL 三种模式的进程模型与传输路径
- 补充 framework-only OTA、vendor freeze 与接口稳定性的关系

### 关联章节
1.1、1.2、1.6、2.15

## [2026-04-12] 6.5 SharedPreferences/DataStore 性能与 ANR 优化 — DataStore 迁移语义与多进程边界

### 盲区描述
当前章节仍把 DataStore 描述成“单进程设计”，并把 `SharedPreferencesMigration` 写成一次性自动搬迁后“删除或重命名旧文件”的简单流程。缺失了 DataStore 1.1.0+ `MultiProcessDataStoreFactory` 的官方能力、`keysToMigrate` 的边界、迁移只发生一次的语义，以及旧 SharedPreferences 何时真正清理/删除的条件。这会直接影响迁移方案设计和数据一致性判断。

### 重要程度
高

### 建议研究方向
- DataStore 1.1.0+ `MultiProcessDataStoreFactory` 的一致性保证与适用边界
- `SharedPreferencesMigration` 的 migrate-once 规则、`keysToMigrate` 行为、cleanup / delete 条件
- 单进程 `preferencesDataStore` delegate 与多进程 DataStore factory 的选型边界

### 关联章节
6.5、6.4、9.3、9.4

## [2026-04-12] 6.5 SharedPreferences/DataStore 性能与 ANR 优化 — `QueuedWork.waitToFinish()` 触发点与 trace 特征

### 盲区描述
章节把 SP ANR 诊断几乎全部锚定在 Activity `onPause()` / `handlePauseActivity()`，没有覆盖 modern Activity `handleStopActivity()`、BroadcastReceiver `onReceive()` 收尾、Service command handling / destroy 等实际触发点，也没有说明 trace 中如何区分主线程正在 `processPendingWork()` 执行写盘，还是只是卡在 `CountDownLatch.await()`。这会影响实际排障命中率。

### 重要程度
高

### 建议研究方向
- AOSP `ActivityThread` 中 `handlePauseActivity()` vs `handleStopActivity()` 的版本边界
- Service / BroadcastReceiver 调 `QueuedWork.waitToFinish()` 的调用点与典型 ANR 栈
- Perfetto / traces.txt 中 `processPendingWork()`、`queued-work-looper`、`CountDownLatch.await()` 的判别方式

### 关联章节
6.5、9.3、9.4、9.5

## [2026-04-12] 5.12 Thermal 管控深度：从内核子系统到 ADPF 主动降频 — Thermal Headroom 数据契约

### 盲区描述
正文讨论了 `getThermalHeadroom()` 的预测思路，但没有把 HAL 侧的 `TemperatureThreshold`、`forecastSkinTemperature()`、skin sensor 多样本与 Framework `TemperatureWatcher` 的归一化逻辑串起来。结果是 HAL 一节、headroom 一节、ADPF 一节各说各的，读者看完仍然不知道 headroom 这个值到底建立在什么数据基础上。

### 重要程度
高

### 建议研究方向
- 追 `hardware/interfaces/thermal/aidl/android/hardware/thermal/IThermal.aidl` 中 `getTemperatureThresholds*()` / `forecastSkinTemperature()` 的真实语义
- 追 `ThermalManagerService.TemperatureWatcher` 的样本缓存、线性回归与 severe threshold 归一化流程
- 说明 API 35 `getThermalHeadroomThresholds()` 与 API 36 `AThermal_HeadroomCallback` 如何改变 App 侧策略写法

### 关联章节
5.5、5.9、5.12、8.9、13.9

## [2026-04-12] 5.12 Thermal 管控深度：从内核子系统到 ADPF 主动降频 — Android 17 Thermal 变化未落地

### 盲区描述
frontmatter 把章节适用范围写到 Android 17，但版本演进表对 Android 17 仍停留在“[待验证]”。如果不补齐 Android 17 thermal 改动，读者无法判断哪些 API / HAL / headroom 行为是 Android 16 结论，哪些已经在 Android 17 变化。

### 重要程度
高

### 建议研究方向
- 用 Android 17 release notes / API diff / AOSP 代码比对确认 thermal、ADPF、headroom threshold 的新增或变更
- 核对 `frameworks/base/services/core/java/com/android/server/power/` 与 `frameworks/native/include/android/thermal.h` 在 Android 16 vs 17 的差异
- 若没有实质变化，也需要明确写出“Android 17 没有新增 thermal API，只沿用 Android 16 行为”而不是留占位符

### 关联章节
5.9、5.12、16.4



## [2026-04-12] 5.11 端侧 AI 推理性能：NPU/GPU 加速与 TFLite 管线 — 端侧 AI 可观测性矩阵

### 盲区描述
正文讲了 CPU / GPU / NPU 三条推理路径，但没有建立“默认 Perfetto 能看到什么、需要 app instrumentation 才能看到什么、哪些信号只能依赖厂商 atrace / delegate 日志”的统一观测模型。没有这张矩阵，读者很难把 LiteRT / TFLite 的 delegate 选择和真实 Trace 证据对上。

### 重要程度
高

### 建议研究方向
- Perfetto 默认数据源下可直接观测的 CPU 调度、频率、内存、热信号
- app `Trace.beginSection()` / native atrace / symbolized native slice 对 LiteRT 阶段切片的可见性差异
- Qualcomm / MediaTek / Tensor 平台对 NPU / DSP 推理暴露的 vendor tracepoint 与 counters
- NNAPI / LiteRT delegate 日志与 Trace 的联合定位方法

### 关联章节
5.11、5.9、14.1、2.5

## [2026-04-12] 5.11 端侧 AI 推理性能：NPU/GPU 加速与 TFLite 管线 — AICore / Gemini Nano 设备与版本矩阵

### 盲区描述
正文把 AICore 平台能力、Gemini Nano 模型版本、设备 rollout 和 benchmark 数字写在一起，但缺少一张可核对的“设备 × Android 版本 × 模型版本 × API 可用性”矩阵。没有这张矩阵，AICore 段很容易把“平台支持”误写成“所有 Android 14+ 设备都可用”。

### 重要程度
高

### 建议研究方向
- 官方可核对的 AICore / Gemini Nano 支持设备列表与最低系统版本
- Nano 版本号、参数规模、多模态能力与设备首发时间线
- token/s、首 token 延迟、峰值内存等 benchmark 的统一测试方法
- 无 Play Services / 无 AICore 设备上的 LiteRT fallback 路径

### 关联章节
5.11、5.9、14.1、1.15
