
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
