## [研究] Android 分层架构在 Perfetto Trace 中的映射

- **来源**：perfetto.dev/docs/data-sources/atrace + android.com 官方文档
- **作者/机构**：Google / Perfetto Team
- **日期**：2026-03-30
- **四维评分**：相关性 5/5 · 技术深度 4/5 · 时效性 4/5 · 可验证性 5/5 · **总分 18/20**
- **映射章节**：1.1 Android 分层架构
- **映射锚点**：Perfetto/工具中的表现、各架构层的实际映射、架构层交互可视化
- **摘要**：系统梳理 Android 五层架构（Linux内核、HAL、Native/ART、Framework、App）在 Perfetto Trace 中对应的 Track 和事件类别，为 section 1.1 补充"在 Perfetto 中的表现"部分提供直接素材。

### 关键发现

1. **内核层（Linux Kernel）**：对应 Perfetto 中 CPU 调度 Track（sched_switch）、频率变化 Track（freq）、binder_driver Track、I/O 事件 Track。这些事件通过 ftrace 机制直接从内核采集，在 Perfetto UI 中按 CPU 编号展示为独立的 CPU 行。

2. **HAL 层**：通过 Perfetto 的 atrace category "hal" 可以追踪 HAL 模块活动。Project Treble 之后，Binderized HAL 运行在独立进程中，可通过 Binder Transaction Track 观察跨进程调用。HAL 还暴露电池、能耗等 counter 数据。在 Perfetto 中搜索进程名如  可定位 HAL 进程。

3. **Native 层 / ART**：hwui Track 展示硬件加速渲染过程（DisplayList 录制、GPU 命令提交）；ART 的 GC 事件可在 Main Thread Track 中看到（标注为 "GC" slice）；Native 代码可通过 ATrace_beginSection/ATrace_endSection 插桩，在对应线程 Track 中显示为自定义 slice。

4. **Framework 层**：system_server 进程的各线程 Track 展示 AMS/WMS/PMS 等服务活动；Choreographer、Input 事件分发在 App 进程的 Main Thread Track 中可见；SurfaceFlinger 进程 Track 展示合成操作和 VSync 信号分发。

5. **Binder 作为跨层纽带**：binder_driver category 记录所有 Binder IPC，在 Perfetto 中可看到 Transaction 的 client/server 进程对、耗时、数据大小。这是唯一一个横跨所有架构层的数据源。

### 可直接引用段落

> Perfetto 通过 ftrace 从 Linux 内核采集调度、频率、Binder 驱动等事件；通过 atrace 从 Android Framework 和 HAL 采集标记事件；通过 /proc 和 /sys 轮询获取进程状态和内存计数器。这三种数据源恰好对应 Android 的三层架构：内核层 → ftrace，HAL/Framework 层 → atrace，系统级状态 → /proc & /sys 轮询。

> 在 Perfetto UI 中打开一个系统级 Trace，你会看到：最上面是按 CPU 编号排列的调度 Track（内核层），中间是各进程的线程 Track（App/Framework/Native 层），其中 system_server 进程承载了几乎所有 Framework 服务的线程，SurfaceFlinger 进程负责图形合成，而 Binder Transaction Track 贯穿所有进程——它就是架构分层图中那条"跨层通信"的箭头在 Trace 中的具象化。

> Perfetto 的 atrace category 中，"hal" 类别专门用于追踪 HAL 模块活动，"binder_driver" 类别追踪 Binder IPC，"hwui" 追踪硬件加速渲染，"sched" 和 "freq" 追踪内核调度和频率变化——每个 category 恰好对应 Android 架构的一个或多个层级。

### 与 queue.json 联动
- 优先级调整建议：section 1.1 已有 priority 90，维持不变
- 素材路径建议：可补充到 1.1 的 material_paths
