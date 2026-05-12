## [研究] Project Treble 架构演进与 HIDL→AIDL 过渡的性能影响

- **来源**：android.com 官方文档 + source.android.com
- **作者/机构**：Google Android Team
- **日期**：2026-03-30
- **四维评分**：相关性 4/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 5/5 · **总分 18/20**
- **映射章节**：1.1 Android 分层架构
- **映射锚点**：版本演进（架构变化）、HAL 层详细说明、Binder 与 HAL 的关系
- **摘要**：梳理 Android 8 引入 Project Treble 后架构分层的重大变化，以及 Android 11+ 从 HIDL 向 AIDL HAL 的过渡。这一演进直接影响了 HAL 层在 Perfetto Trace 中的表现方式，是 section 1.1 "架构演进"部分的关键素材。

### 关键发现

1. **Treble 之前的 HAL**：Android 8 之前，HAL 实现以共享库（.so）形式存在，被 system_server 或 mediaserver 等系统进程直接 dlopen 加载。这意味着 HAL 代码和 Framework 代码运行在同一进程空间，HAL 的崩溃会导致整个系统进程崩溃。在 Perfetto Trace 中，HAL 调用表现为 system_server 内部的函数调用，没有进程边界。

2. **Treble 之后的 Binderized HAL**：Project Treble 将 HAL 拆分为独立进程（如 ），通过 Binder IPC 与 Framework 通信。在 Perfetto 中，HAL 调用现在表现为跨进程的 Binder Transaction，可以在 Binder Track 中追踪完整链路。这也意味着 HAL 调用有了额外的 Binder 开销（但换来了稳定性和可更新性）。

3. **HIDL → AIDL 过渡**：Android 11 开始废弃 HIDL，推荐使用 AIDL 定义 HAL 接口。AIDL HAL 的关键特性：
   - 始终 Binderized（不支持 Passthrough 模式）
   - 使用标准 Binder IPC（而非 HIDL 使用的 hwbinder）
   - 统一了 Framework 间 IPC 和 Framework-HAL IPC 的机制
   - 在 Perfetto 中通过 "aidl" category 追踪

4. **性能影响**：Treble 之前 HAL 调用是进程内函数调用（纳秒级），Treble 之后变为 Binder IPC（微秒级）。单次调用差异不大，但高频 HAL 调用（如传感器数据、音频数据）可能受到影响。Android 通过共享内存（FMQ/SharedMemory）优化高频数据传输场景。

5. **Perfetto 追踪策略变化**：分析 Android 8+ 设备时，需要同时启用 "hal" 和 "binder_driver" category 才能看到完整的 Framework → HAL 调用链路。对于 AIDL HAL，还需启用 "aidl" category。

### 可直接引用段落

> Project Treble 不仅仅是一个"模块化"的架构改进——它从根本上改变了 HAL 层在系统中的位置。从 Perfetto Trace 的视角看，Treble 之前你看不到 HAL 的活动（它们藏在 system_server 进程内部），Treble 之后 HAL 有了自己独立的进程和 Track。这意味着你可以在 Trace 中直接观察到 Framework 和 HAL 之间的 Binder 通信延迟，这在以前是不可能的。

> HIDL 使用的是 hwbinder（/dev/hwbinder），而 AIDL HAL 使用标准 binder（/dev/binder）。这个变化在 Perfetto Trace 中体现为：AIDL HAL 的 IPC 事件出现在标准的 Binder Track 中，与 App ↔ system_server 的通信混在一起，需要通过进程名区分。如果你在分析 Binder 延迟时发现一个不认识的目标进程，它很可能就是一个 AIDL HAL 服务进程。

> 在 Perfetto 中追踪 HAL 问题时，一个常见的错误是只看 Framework 侧的 Binder 调用发起时间。但 Treble 架构下 HAL 是独立进程，你需要同时看 HAL 进程的线程 Track——它可能因为 I/O 等待、锁竞争或其他 HAL 客户端的请求排队而导致响应慢。完整的分析方法应该是：在 Framework 线程找到 Binder 发起点 → 在 Binder Track 找到 Transaction → 在 HAL 进程线程找到处理逻辑 → 检查是否有阻塞。

### 与 queue.json 联动
- 优先级调整建议：维持 1.1 的 priority 90
- 素材路径建议：可补充到 1.1 的 material_paths，同时与 1.6（Android 版本演进中的架构变化）形成交叉引用
