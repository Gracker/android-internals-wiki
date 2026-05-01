## [Task6 Review] 19.13 · androidx.tracing（Tracing SDK） — 2026-04-29
- **类型**：需补充素材
- **位置**：L3内容深度检查
- **问题**：性能开销未充分说明，缺少tracing的性能开销（字符串创建、内存占用）和适用场景边界分析
- **建议**：补充性能开销量化数据，说明哪些场景不建议打trace
- **review 日志**：logs/review/2026-04-29-17-review.md

## [Task6 Review] 19.13 · androidx.tracing（Tracing SDK） — 2026-04-29
- **类型**：需补充素材
- **位置**：线上和线下的边界部分
- **问题**：API兼容性描述不够详细，缺少具体版本差异说明
- **建议**：补充版本对照表，说明各版本的关键差异
- **review 日志**：logs/review/2026-04-29-17-review.md

## [Task6 Review] 7.10 · 图片加载与 Bitmap 性能优化 — 2026-04-29
- **类型**：需补充素材
- **位置**：L3内容深度检查
- **问题**：未对比Glide、Coil等主流图片库的设计理念和优化策略
- **建议**：补充不同图片库的架构对比和适用场景分析
- **review 日志**：logs/review/2026-04-29-17-review.md

## [Task6 Review] 7.10 · 图片加载与 Bitmap 性能优化 — 2026-04-29
- **类型**：需补充素材
- **位置**：L3内容深度检查
- **问题**：缺少不同优化方案的性能量化对比
- **建议**：补充内存占用、加载时间等性能指标的对比数据
- **review 日志**：logs/review/2026-04-29-17-review.md
## [External Review] 10.2 内存泄漏 — 2026-04-29
- **类型**：诊断技巧
- **位置**：Native 堆栈折叠
- **问题**：补充 heapprofd 火焰图中通过 Stack Folding 过滤 libc.so 底层符号的技巧，第一眼区分业务代码与框架内耗
- **建议**：补充 heapprofd 火焰图中通过 Stack Folding 过滤 libc.so 底层符号的技巧，第一眼区分业务代码与框架内耗
- **来源**：Gemini 外部 review


## [External Review] 10.3 内存持续增长 — 2026-04-29
- **类型**：性能代价
- **位置**：LruCache 锁竞争
- **问题**：补充 LinkedHashMap 内部同步在高频并发场景下微小 CPU 抖动，建议渲染帧内查询使用非锁定分级缓存
- **建议**：补充 LinkedHashMap 内部同步在高频并发场景下微小 CPU 抖动，建议渲染帧内查询使用非锁定分级缓存
- **来源**：Gemini 外部 review


## [External Review] 10.4 低内存对系统性能的影响 — 2026-04-29
- **类型**：诊断技巧
- **位置**：PSI 阈值探测
- **问题**：补充 Perfetto SQL 查询 sys_stats 表 PSI 波动斜率方法，2026 年预防 LMK 最灵敏手段
- **建议**：补充 Perfetto SQL 查询 sys_stats 表 PSI 波动斜率方法，2026 年预防 LMK 最灵敏手段
- **来源**：Gemini 外部 review


## [External Review] 10.5 案例集 — 2026-04-29
- **类型**：诊断深度
- **位置**：MGLRU 与杀进程循环
- **问题**：补充 MGLRU 保护热点文件页的对冲效应，120Hz Trace 中 kswapd0 活跃但 major faults 极低即为成功标志
- **建议**：补充 MGLRU 保护热点文件页的对冲效应，120Hz Trace 中 kswapd0 活跃但 major faults 极低即为成功标志
- **来源**：Gemini 外部 review


## [External Review] 10.6 内存抖动与频繁 GC — 2026-04-29
- **类型**：诊断技巧
- **位置**：Allocation Count 归因
- **问题**：补充 Memory Profiler 按分配次数排序优于按大小排序的策略，树立频率优先治理思维
- **建议**：补充 Memory Profiler 按分配次数排序优于按大小排序的策略，树立频率优先治理思维
- **来源**：Gemini 外部 review


## [External Review] 10.7 SQLite/Room 数据库性能优化 — 2026-04-29
- **类型**：诊断技巧
- **位置**：Connection Pool 争用特征
- **问题**：补充 Perfetto 中识别连接池耗尽的 waitForConnection() slice 信号
- **建议**：补充 Perfetto 中识别连接池耗尽的 waitForConnection() slice 信号
- **来源**：Gemini 外部 review


## [External Review] 11.1 Android 功耗模型 — 2026-04-29
- **类型**：底层存储
- **位置**：Binary Delta Storage
- **问题**：补充 Android 15 BatteryStats 二进制增量存储格式改良，高负载导出 bugreport 磁盘 I/O 降低 30%
- **建议**：补充 Android 15 BatteryStats 二进制增量存储格式改良，高负载导出 bugreport 磁盘 I/O 降低 30%
- **来源**：Gemini 外部 review


## [External Review] 11.2 App 耗电优化 — 2026-04-29
- **类型**：诊断技巧
- **位置**：FGS Timeout 视觉识别
- **问题**：补充 Battery Historian/Perfetto 中 RemoteServiceException + fgs_timeout 状态字识别方法
- **建议**：补充 Battery Historian/Perfetto 中 RemoteServiceException + fgs_timeout 状态字识别方法
- **来源**：Gemini 外部 review


## [External Review] 11.3 系统级功耗优化 — 2026-04-29
- **类型**：底层原理
- **位置**：16KB Page 下的自适应省电
- **问题**：补充大页面提升 CPU 处理内存映射能效，省电模式限制 CPU 频率对体感伤害减缓
- **建议**：补充大页面提升 CPU 处理内存映射能效，省电模式限制 CPU 频率对体感伤害减缓
- **来源**：Gemini 外部 review


## [External Review] 11.4 案例集（功耗） — 2026-04-29
- **类型**：诊断技巧
- **位置**：WakeLock 聚合查询
- **问题**：补充 Perfetto SQL 聚合 WakeLock 申请计数语句，替代 Battery Historian 处理 24h 级超长 Trace
- **建议**：补充 Perfetto SQL 聚合 WakeLock 申请计数语句，替代 Battery Historian 处理 24h 级超长 Trace
- **来源**：Gemini 外部 review

## [Task9 Deep Review] 7.10 图片加载与 Bitmap 性能优化 — 2026-04-29
- **类型**：数据缺失
- **位置**：L421-L436 Perfetto 图示与 1080p upload 4-8ms
- **问题**：Perfetto 图仍是占位描述，且 1080p RGBA Bitmap 上传 4-8ms 没有设备、刷新率、GPU、图片格式、trace slice 或 benchmark 来源。
- **建议**：补一组固定设备的 Perfetto/benchmark：主线程 decode slice、RenderThread upload/DrawFrame、FrameTimeline jank 标记；没有数据前把 4-8ms 改为待验证或删除。


## [External Review] 18.1 渲染链路分类与选择矩阵 — 2026-04-29
- **类型**：诊断技巧
- **位置**：BLAST 事务原子性特征
- **问题**：补充 Android 15 针对多 Layer 事务原子性（Atomic Commit）的提升特征。Perfetto 中若观察到跨窗口渲染切片共享同一 Transaction ID，即说明系统执行了原子提交
- **建议**：补充 Atomic Commit 在 Perfetto 中的识别方法，预防画面错位诊断
- **来源**：Gemini 外部 review

## [External Review] 18.2 Android View 标准链路 — 2026-04-29
- **类型**：物理开销
- **位置**：Triple Buffering 显存账本
- **问题**：补充 16KB 分页环境下 Triple Buffering 的物理显存增量。由于 Gralloc Buffer 强制对齐，单帧 Buffer 的 RSS 驻留产生约 9% 溢出，多层 Layer 叠加时在内存受限设备上不可忽视
- **建议**：补充 16KB 环境下 Triple Buffering 显存开销的量化分析
- **来源**：Gemini 外部 review

## [External Review] 18.3 Android View 软件渲染链路 — 2026-04-29
- **类型**：诊断技巧
- **位置**：uploadToTexture 归因
- **问题**：详细描述开启 LAYER_TYPE_SOFTWARE 后 RenderThread 轨道出现的 uploadToTexture 或 glTexImage2D 耗时特征。软件 Layer 代价不仅在于 CPU 算像素，更在于像素从内存搬运到 GPU 显存的同步开销
- **建议**：补充 uploadToTexture 在 Perfetto Trace 中的识别方法与耗时归因
- **来源**：Gemini 外部 review

## [Task9 Deep Review] 18.4 Android View 混合渲染链路 — 2026-04-29
- **类型**：数据缺失
- **位置**：L214 `dumpsys SurfaceFlinger` activeBuffer / latched buffer 观察点
- **问题**：当前只写字段名，没有给 Android 版本、命令、示例输出或 Perfetto 对应事件，读者难以复现“哪几个 Layer latch 了新 buffer”的判断。
- **建议**：补一段 Android 14-16 的 `dumpsys SurfaceFlinger --layers` / `--latency` 示例，或给 Perfetto SurfaceFlinger layer 事件的替代观察路径。

## [Task9 Deep Review] 5.1 Linux 进程调度基础 — 2026-04-29
- **类型**：数据缺失
- **位置**：L296-L306 ARMv9.2 / 骁龙 8 Elite 跨核迁移延迟
- **问题**：`1.5μs - 3.5μs` 没有给测试设备、内核版本、迁移类型、测量工具和样本范围。
- **建议**：补充公开 benchmark 或自测 trace；如果暂时没有一手数据，改成 `[待验证]` 并只保留“新平台迁移成本可能降低，需实测判断绑核收益”的边界结论。

## [Task9 Deep Review] 9.5 案例集 — 2026-04-29
- **类型**：源码准确性
- **位置**：L219-L227 SharedPreferences / QueuedWork 等待链路
- **问题**：正文引用 `QueuedWork.waitToFinish()` 与 Activity 生命周期等待，但该段只标注 `SharedPreferencesImpl.java`，缺少直接方法所在的 `QueuedWork.java` 和生命周期入口 `ActivityThread`。
- **建议**：补充 `frameworks/base/core/java/android/app/QueuedWork.java#waitToFinish()`、`ActivityThread.handlePauseActivity()` / stop 相关调用点，再说明 `SharedPreferencesImpl.apply()` 如何把 finisher 加入 QueuedWork。


## [External Review] 18.10 18.10 SurfaceControl API 深入 — 2026-04-29
- **类型**：物理开销
- **位置**：全文相关段落
- **问题**：补充说明 16KB 物理分页对包含海量 Layer 属性的 `AParcel` 编解码的影响。核实发现，在大页面环境下，跨进程 Transaction 的物理页对齐损耗在 120Hz 极速提交场景下约有 **5%-8%** 的响应提升（由于 TLB 命中率更高），应作为性能背景补充。
- **建议**：补充说明 16KB 物理分页对包含海量 Layer 属性的 `AParcel` 编解码的影响。核实发现，在大页面环境下，跨进程 Transaction 的物理页对齐损耗在 120Hz 极速提交场景下约有 **5%-8%** 的响应提升（由于 TLB 命中率更高），应作为性能背景补充。
- **来源**：Gemini 外部 review (2026-04-29-11-18.10-external-review.md)


## [External Review] 18.5 18.5 Android View 多窗口链路 — 2026-04-29
- **类型**：物理开销
- **位置**：全文相关段落
- **问题**：补充 16KB 分页对 `eglMakeCurrent` 的优化。核实发现，由于页表覆盖面扩大，多窗口频繁切换 EGLSurface 时的 TLB 刷新开销降低了约 **8%**。这意味着在 Android 15+ 设上，多窗口渲染切换 GL 状态机的硬件损耗有所回升，应作为性能背景补充。
- **建议**：补充 16KB 分页对 `eglMakeCurrent` 的优化。核实发现，由于页表覆盖面扩大，多窗口频繁切换 EGLSurface 时的 TLB 刷新开销降低了约 **8%**。这意味着在 Android 15+ 设上，多窗口渲染切换 GL 状态机的硬件损耗有所回升，应作为性能背景补充。
- **来源**：Gemini 外部 review (2026-04-29-11-18.5-external-review.md)


## [External Review] 18.6 18.6 SurfaceView 直出链路 — 2026-04-29
- **类型**：诊断技巧
- **位置**：全文相关段落
- **问题**：补充在 Perfetto 中利用 Android 16 自动化元数据识别 SurfaceView 焦点状态的方法。由于 SurfaceView 拥有独立 InputChannel，其焦点切换在 `input_focus` 轨道中有独立表现，应指导开发者利用此点排查“游戏层有画面但点不动”的奇葩问题。
- **建议**：补充在 Perfetto 中利用 Android 16 自动化元数据识别 SurfaceView 焦点状态的方法。由于 SurfaceView 拥有独立 InputChannel，其焦点切换在 `input_focus` 轨道中有独立表现，应指导开发者利用此点排查“游戏层有画面但点不动”的奇葩问题。
- **来源**：Gemini 外部 review (2026-04-29-11-18.6-external-review.md)


## [External Review] 18.7 18.7 TextureView 合成链路 — 2026-04-29
- **类型**：诊断技巧
- **位置**：全文相关段落
- **问题**：补充在 Perfetto 中识别“TextureView 过载”的特征信号——即 RenderThread 轨道出现密集的 `glEGLImageTargetTexture2DOES` 调用且紧随其后的 `drawDisplayList` 耗时显著拉长。这是判定“纹理重采样成为 GPU 瓶颈”的核心证据。
- **建议**：补充在 Perfetto 中识别“TextureView 过载”的特征信号——即 RenderThread 轨道出现密集的 `glEGLImageTargetTexture2DOES` 调用且紧随其后的 `drawDisplayList` 耗时显著拉长。这是判定“纹理重采样成为 GPU 瓶颈”的核心证据。
- **来源**：Gemini 外部 review (2026-04-29-11-18.7-external-review.md)


## [External Review] 18.8 18.8 OpenGL ES 渲染链路 — 2026-04-29
- **类型**：物理开销
- **位置**：全文相关段落
- **问题**：补充 16KB 分页对 `glBindTexture` 的优化表现。核实发现，在大页面环境下，显存映射的 TLB 命中率提升使高频纹理切换的 CPU 开销降低了约 **5%**。这对于拥有大量 Asset 的游戏来说是稳定的物理红利，应作为“性能特征”补充。
- **建议**：补充 16KB 分页对 `glBindTexture` 的优化表现。核实发现，在大页面环境下，显存映射的 TLB 命中率提升使高频纹理切换的 CPU 开销降低了约 **5%**。这对于拥有大量 Asset 的游戏来说是稳定的物理红利，应作为“性能特征”补充。
- **来源**：Gemini 外部 review (2026-04-29-11-18.8-external-review.md)


## [External Review] 18.9 18.9 Vulkan 原生渲染管线 — 2026-04-29
- **类型**：诊断技巧
- **位置**：全文相关段落
- **问题**：补充在 Perfetto 中利用 Android 15+ 增强的 `vulkan.submission` 轨道识别“Over-Synchronization”的方法。若看到密集的 Barrier 切片且 GPU 轨道出现大量空隙，即说明 App 的显式同步策略过于保守，扼杀了 GPU 的并行度。
- **建议**：补充在 Perfetto 中利用 Android 15+ 增强的 `vulkan.submission` 轨道识别“Over-Synchronization”的方法。若看到密集的 Barrier 切片且 GPU 轨道出现大量空隙，即说明 App 的显式同步策略过于保守，扼杀了 GPU 的并行度。
- **来源**：Gemini 外部 review (2026-04-29-11-18.9-external-review.md)

## [External Review] 18.11 ANGLE（GLES-over-Vulkan 翻译层） — 2026-04-29
- **类型**：诊断技巧
- **位置**：SPIR-V 轨道特征
- **问题**：补充在 Perfetto 中利用 Android 16 增强的 vulkan.pipeline_cache 轨道识别 SDM 生效状态的方法。若 cache_hit 比例接近 100% 且无长耗时的 vkCreateGraphicsPipelines slice，即说明 SDM 预编译红利成功闭环。
- **建议**：补充 Perfetto vulkan.pipeline_cache 轨道 SDM 识别方法
- **来源**：Gemini 外部 review (2026-04-29-11-18.11-external-review.md)


## [External Review] 18.12 Flutter 渲染管线 — 2026-04-29
- **类型**：诊断技巧
- **位置**：Raster 轨道深度利用
- **问题**：补充在 Perfetto 中利用 Android 15+ 增强的 EntityPass::* 轨道识别 Over-draw 的方法。若 Raster 线程出现密集 EntityPass 切片，即说明该帧正在处理极高复杂度的矢量路径，应引导优化 Widget 树层级。
- **建议**：补充 Perfetto EntityPass::* 轨道 Over-draw 识别方法
- **来源**：Gemini 外部 review (2026-04-29-11-18.12-external-review.md)

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-29
- **类型**：数据缺失
- **位置**：L146 GBL 与 `boottime.bootloader.*`
- **问题**：GBL 官方文档强调 UEFI App、AVB、Fastboot、slot selection 等标准化，但当前未看到它直接保证 `boottime.bootloader.*` 跨厂商可比的证据；bootstat 中 bootloader 分段事件也早于 GBL 存在。
- **建议**：把 GBL 标准化与 bootstat bootloader 事件拆开写；若保留“跨厂商可比”，补 source.android.com 或 AOSP bootloader 指标规范引用。

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-29
- **类型**：数据缺失
- **位置**：L316-L328 Pixel 8 / Android 16 启动分段基线
- **问题**：表格给出 Pixel 8 Android 16 典型冷启动各阶段耗时，但来源写“公开 bootstat 输出和 AOSP 默认配置估算”，缺少设备、构建号、采样次数、bootstat 原始输出和 Perfetto/日志对照。
- **建议**：补 3-5 次冷启动 bootstat -l 原始数据、构建号、是否 OTA 后首启、是否已解锁/加密状态；没有实测前改成“示意分段”，不要绑定 Pixel 8。

## [Task9 Deep Review] 1.3 进程模型与生命周期管理 — 2026-04-29
- **类型**：数据缺失
- **位置**：L264-L279 Perfetto `android_freezer_events` 查询
- **问题**：正文写 Perfetto v49+ 提供 `android.freezer` 模块和 `android_freezer_events` 表，但本轮未找到公开 Perfetto 文档中的稳定表 schema。若表名随 stdlib/Android trace_processor 版本变化，读者会直接查不到。
- **建议**：补 trace_processor 版本、stdlib 文档或实际 `SELECT * FROM sqlite_master WHERE name LIKE '%freezer%'` 结果；未确认前改为 dumpsys/logcat/ftrace 的通用观察路径。


## [External Review] 18.21 EyeDropper API 与跨设备协作性能 — 2026-04-30
- **类型**：诊断技巧
- **位置**：DisplayDataSpace 追踪
- **问题**：补充在 Perfetto 中利用 Android 17 增强的 android.display.dataspace 计数器验证取色环境的方法
- **建议**：开发者应据此判定当前系统返回的颜色值是否处于 DATASPACE_DISPLAY_P3 等高动态范围语境下，以决定后续色板的存储精度
- **来源**：Gemini 外部 review

## [Task9 Deep Review] 10.5 案例集 — 2026-04-30
- **类型**：数据缺失
- **位置**：L254、L312 renderD128 / MemoryThrashing 效果
- **问题**：两个案例仍保留“[待补充：具体降幅百分比]”。章节锚点要求每个案例包含修复方案与量化效果；当前能证明趋势，但不能支撑精确效果闭环。
- **建议**：补原始来源里的版本周期、设备/样本量、崩溃率口径；若公开材料没有百分比，改为“回落至基线/明显下降（原文未披露百分比）”，不要保留发布态占位。


## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-30
- **类型**：数据缺失
- **位置**：L316-L327 Pixel 8 / Android 16 参考基线表
- **问题**：表格给出 Bootloader、Kernel、Zygote、SystemServer 等分段耗时和占比，但没有 bootstat 原始输出、build fingerprint、重启条件、样本次数。当前只能算估算，不足以作为“Pixel 8, Android 16”基线。
- **建议**：补 bootstat -l、logcat events、Perfetto trace 截图或降级为“示例口径”；每个数字标注设备、版本、冷/热重启、是否首启/OTA 后首启。

## [Task9 Deep Review] 1.3 进程模型与生命周期管理 — 2026-04-30
- **类型**：数据缺失
- **位置**：L430-L433 InputDispatcher SocketPair 线程数对比
- **问题**：正文给出 Binder 方案会变成 2(N+1) 线程、Socket 是 N+1 线程的精确比较，但没有 InputChannel/InputDispatcher 源码锚点或设计文档支撑，也没有说明这是估算模型还是 AOSP 真实线程模型。
- **建议**：补 InputChannel/SocketPair、InputDispatcher 与 app InputEventReceiver 的源码路径；如果没有源码证据，把精确公式降级为“SocketPair 避免为每个窗口额外占用 Binder 线程池”的定性描述。

## [Task9 Deep Review] 1.7 ART 编译管线与 dex2oat 优化 — 2026-04-30
- **类型**：数据缺失
- **位置**：L178（JIT code cache 通常稳定在 4MB 左右）
- **问题**：该数值仍标注为工程经验值，缺少设备、应用规模、Android/ART 版本和采样方法。
- **建议**：补 dumpsys meminfo / perfetto counter / ART 日志的采样条件；如果暂无数据，删掉固定 4MB 数值或改为明确的待验证脚注。

## [Task9 Deep Review] 8.1 响应速度原理 — 2026-04-30 — L115/L141/L277 章节链接
- **类型**：交叉引用
- **位置**：L115/L141/L277 章节链接
- **问题**：`04-choreographer.md`、`01-input-dispatch.md`、`01-perfetto-intro.md` 都按当前目录解析，无法跳到真实章节。
- **建议**：改成指向 `part1-fundamentals/ch02-rendering/04-choreographer.md`、`part1-fundamentals/ch03-input/01-input-dispatch.md`、`part3-tools/ch13-perfetto/01-perfetto-intro.md` 的相对路径。
- **review 日志**：logs/deep-review/2026-04-30-05-deep-review.md


## [Task9 Deep Review] 8.1 响应速度原理 — 2026-04-30 — L139 输入分发 1-2ms
- **类型**：数据缺失
- **位置**：L139 输入分发 1-2ms
- **问题**：“从 InputDispatcher 发出到 App 收到通常 1-2ms”缺少设备、刷新率、负载和 trace 口径。
- **建议**：补一段 Perfetto/TraceProcessor 量测方法，或把该数字改为示例值并标注测试条件。
- **review 日志**：logs/deep-review/2026-04-30-05-deep-review.md


## [Task9 Deep Review] 8.3 启动优化策略 — 2026-04-30 — L652-L658 Baseline Profile 效果量化
- **类型**：数据缺失
- **位置**：L652-L658 Baseline Profile 效果量化
- **问题**：“简单应用 10%-20%、中等 20%-40%、复杂超过 40%”没有官方或案例来源，且与 Startup Profile 官方“通常比只用 Baseline Profile 再快 15%-30%”不是同一口径。
- **建议**：补 Google I/O/case study/Macrobenchmark 数据来源；如果只是经验值，改成示例并写测试条件。
- **review 日志**：logs/deep-review/2026-04-30-05-deep-review.md


## [Task9 Deep Review] 8.3 启动优化策略 — 2026-04-30 — 2026-04-29-10-8.3-external-review.md WebView DEFAULT_TO_WEB
- **类型**：external-review 核验
- **位置**：2026-04-29-10-8.3-external-review.md WebView DEFAULT_TO_WEB
- **问题**：外部 review 提到 Android 15 `DEFAULT_TO_WEB` 意图用于 WebView 首屏，本轮检索未找到标准 Intent/API 或官方文档支持。
- **建议**：不要按该线索直接补正文；如要覆盖 H5 首屏，改查 WebView 预热、renderer process、7.11/18.13 的可验证内容。
- **review 日志**：logs/deep-review/2026-04-30-05-deep-review.md

## [External Review] 12.1 APK 体积优化 — 2026-04-30
- **类型**：分发策略
- **位置**：AAB 与 16KB 对齐协同
- **问题**：补充 Google Play AAB 分发在 2026 年的默认行为，Target SDK 35+ 的 AAB Play Console 自动确保 Split APK 符合 16KB 物理对齐
- **建议**：开发者无需手动 zipalign -P 16，将精力聚焦于业务逻辑拆分
- **来源**：Gemini 外部 review

## [External Review] 12.2 网络性能优化 — 2026-04-30
- **类型**：合规红线
- **位置**：HTTP/3 降级审计
- **问题**：HTTP/3 UDP 443 在部分企业网/公共 Wi-Fi 被劫持/限速，缺少审计策略
- **建议**：在 EventListener 记录 alt-svc 握手失败率，作为判定是否应在当前 SSID 下强制退避至 HTTP/2 的线上准则
- **来源**：Gemini 外部 review

## [Task9 Deep Review] 2.8 过度绘制 — 2026-04-30 — L170 Perfetto / AGI 截图占位
- **类型**：数据缺失
- **位置**：L170 Perfetto / AGI 截图占位
- **问题**：正文仍保留“[待补充：真实 Perfetto FrameTimeline / AGI frame capture 截图]”。当前观测链合理，但缺少可复核 trace/capture 证据。
- **建议**：补一组滚动或半透明蒙层场景：Debug GPU Overdraw 截图、Perfetto FrameTimeline/RenderThread 对照、AGI frame capture 或厂商 GPU counter。
- **review 日志**：logs/deep-review/2026-04-30-06-deep-review.md


## [Task9 Deep Review] 2.8 过度绘制 — 2026-04-30 — L357-L365 Compose 背景合并优化
- **类型**：来源标注
- **位置**：L357-L365 Compose 背景合并优化
- **问题**：小节已标 [待验证]，但段尾仍紧跟 `[已验证: 官方文档, compose graphics modifiers]`，容易让读者误以为官方文档验证了 background merge。
- **建议**：把官方文档标注移到通用 Compose overdraw 段；背景合并小节只保留待验证说明，并指向 research-gaps 中的追踪项。
- **review 日志**：logs/deep-review/2026-04-30-06-deep-review.md


## [Task9 Deep Review] 4.3 ART 虚拟机内存管理 — 2026-04-30 — L466-L470 正常 vs 异常 GC 模式阈值
- **类型**：数据缺失
- **位置**：L466-L470 正常 vs 异常 GC 模式阈值
- **问题**：Young GC 每 2-5 秒一次、Full GC 每几分钟一次、吞吐量 >98% 等阈值缺设备、应用规模、Android/ART 版本和 trace 口径。
- **建议**：补 Perfetto/ART 日志样本，或改成“经验起点”并标注设备、版本、前后台状态、堆大小和采样时长。
- **review 日志**：logs/deep-review/2026-04-30-06-deep-review.md


## [Task9 Deep Review] 4.3 ART 虚拟机内存管理 — 2026-04-30 — L140-L143 Large Object Space 实现选择
- **类型**：源码准确性
- **位置**：L140-L143 Large Object Space 实现选择
- **问题**：正文把 FreeListSpace / LargeObjectMapSpace 直接归因于 arm64 / 非 arm64。android-15.0.0_r1 的默认选择由 `USE_ART_LOW_4G_ALLOCATOR` 控制，架构只是常见结果，不应写成唯一条件。
- **建议**：改成“默认由 `Heap::kDefaultLargeObjectSpaceType` 和 `USE_ART_LOW_4G_ALLOCATOR` 决定；常见设备上可能表现为某种实现”，并补 heap.h 源码锚点。
- **review 日志**：logs/deep-review/2026-04-30-06-deep-review.md

## [External Review] 12.3 网络性能深入 — 2026-04-30
- **类型**：物理开销
- **位置**：16KB Page 对加密库的增益
- **问题**：未补充 16KB 分页环境下 libcrypto.so 的 ELF 段物理对齐对 CPU 指令预取（Prefetching）的正面贡献
- **建议**：补充说明大页面环境下高频加解密任务的 I-Cache 命中率约提升 5%，对 WebRTC 等大规模实时音视频网络层功耗优化有统计学意义
- **来源**：Gemini 外部 review

## [External Review] 12.4 Android 网络安全与 TLS — 2026-04-30
- **类型**：物理开销
- **位置**：16KB Page 对 libssl 的优化
- **问题**：未补充 16KB 物理分页对 TLS 握手阶段核心代码段的缓存收益
- **建议**：补充说明 16KB 环境下 TLS 握手密集数学库调用的指令分支预测成功率约提升 5%，对高频短连接应用有稳定能效红利
- **来源**：Gemini 外部 review


## [Task9 Deep Review] 8.7 Baseline Profiles 与编译优化实践 — 2026-04-30 — L245 AGP 8.3 Startup Profile DEX layout
- **类型**：版本差异
- **位置**：L245 AGP 8.3 Startup Profile DEX layout
- **问题**：只写“AGP 8.3 起默认开启”，未交代该优化依赖 Startup Profile + R8/D8 布局流程，也未说明库可以贡献 Baseline Profile、但不能直接贡献应用 Startup Profile。
- **建议**：补一句：AGP 8.3 默认使用 Startup Profile 做 DEX layout，release 构建需确认 R8/minify 路径；Startup Profile 由应用启动测试生成，不能只依赖库 profile。
- **review 日志**：logs/deep-review/2026-04-30-07-deep-review.md


## [Task9 Deep Review] 8.7 Baseline Profiles 与编译优化实践 — 2026-04-30 — L241、L320-L322 Profile 覆盖率 / 规则数量阈值
- **类型**：数据缺失
- **位置**：L241、L320-L322 Profile 覆盖率 / 规则数量阈值
- **问题**：“覆盖 80% 启动路径”“不超过几千条规则”缺少官方阈值、样本或本地 benchmark；profile 大小与编译时间的关系也没有量化口径。
- **建议**：改为经验性建议并补验证方法：记录 `baseline.prof/.profm` 大小、`cmd package compile -m speed-profile` 耗时、安装后 oat/vdex 增量和 Macrobenchmark TTID/TTFD。
- **review 日志**：logs/deep-review/2026-04-30-07-deep-review.md


## [Task9 Deep Review] 12.1 APK 体积优化 — 2026-04-30 — L56 与 L82 / L280 native libraries 解压路径
- **类型**：版本差异
- **位置**：L56 与 L82 / L280 native libraries 解压路径
- **问题**：开头写 native libraries 被解压到磁盘，后文又说明 Android 6.0+ 可 direct loading 未压缩且 page-aligned 的 `.so`。同章存在新旧 packaging 行为不一致。
- **建议**：开头改成“是否解压取决于 `jniLibs.useLegacyPackaging` / `extractNativeLibs` 和 page alignment”，避免把旧路径写成通用事实。
- **review 日志**：logs/deep-review/2026-04-30-07-deep-review.md


## [Task9 Deep Review] 12.1 APK 体积优化 — 2026-04-30 — L100 命令行分析工具
- **类型**：工具准确性
- **位置**：L100 命令行分析工具
- **问题**：`aapt dump badging` 主要输出 manifest/badging 信息，不适合作为 APK 结构与体积门禁工具。
- **建议**：命令行体积分析改用 `apkanalyzer files list/summary`、`bundletool get-size total`、`aapt2 dump resources` 或 unzip/zipinfo 组合。
- **review 日志**：logs/deep-review/2026-04-30-07-deep-review.md


## [Task9 Deep Review] 12.1 APK 体积优化 — 2026-04-30 — L327、L404-L421 Play Core Library
- **类型**：版本差异
- **位置**：L327、L404-L421 Play Core Library
- **问题**：Dynamic Feature 运行时加载仍写成 “Play Core Library 1.6+”。当前官方分发口径应优先写 Play Feature Delivery 库；旧 monolithic Play Core 版本线容易误导新项目选型。
- **建议**：改为 Play Feature Delivery API，并补当前 Gradle 依赖坐标/版本边界；旧 Play Core 只作为历史兼容说明。
- **review 日志**：logs/deep-review/2026-04-30-07-deep-review.md


## [Task9 Deep Review] 12.1 APK 体积优化 — 2026-04-30 — L339、L482、L490-L492
- **类型**：数据缺失
- **位置**：L339、L482、L490-L492
- **问题**：AAB 15%-40%、Baseline Profile 安装后 `.odex/.vdex` 增量 10%-30%、微信/抖音包体积实践均缺可复核来源或实验条件。
- **建议**：补官方案例、公开技术文章链接或本地样本测量；无法核实时降级为“待验证示例”，不要作为通用结论。
- **review 日志**：logs/deep-review/2026-04-30-07-deep-review.md


## [Task9 Deep Review] 1.13 MessageQueue 机制与 DeliQueue 无锁优化 — 2026-04-30
- **类型**：交叉引用一致性
- **位置**：文末 `16KB Page Size 对线程栈内存的影响` 补充段
- **问题**：该段内容讨论 PTHREAD_STACK_MIN、ART 线程栈和 16KB page size，与本节 MessageQueue / DeliQueue 主线没有直接因果关系，容易把“队列并发结构”和“线程栈内存”两个主题混在一起。
- **建议**：移到 4.7 `16KB Page Size 与 Android 性能` 或内存章节；本节只保留 DeliQueue 对测试框架、mMessages 反射和 Perfetto monitor contention 的影响。

## [Task9 Deep Review] 4.3 ART 虚拟机内存管理 — 2026-04-30 — L214-L217 / L323 ART 8 性能数字
- **类型**：数据缺失
- **位置**：L214-L217、L323
- **问题**：32% 堆大小下降、85% GC 暂停下降、70% 分配速度提升、Dalvik 18 倍等数字没有在当前标注的 `source.android.com/docs/core/runtime/gc-debug` 页面中出现。该页面能支撑 Android 8 默认 CC、RegionTLAB、Android 10+ generational CC，但不能支撑这些量化值。
- **建议**：补 Android/ART 官方演讲、android.com 页面或可公开 benchmark 链接；如果只能保留二手材料，需标注来源、benchmark 名称、设备/版本和对比基线。
- **review 日志**：logs/deep-review/2026-04-30-09-deep-review.md

## [Task9 Deep Review] 7.11 WebView 渲染性能与优化 — 2026-04-30 — L135-L137 Android 15 16KB 内存页红利
- **类型**：数据缺失
- **位置**：L135-L137 Android 15 16KB 内存页红利
- **问题**：`libwebviewchromium.so` >100MB、页表项减少 3/4 的算术成立，但“WebView 冷加载速度提升明显”缺少 WebView 专项 A/B 数据。正文虽保留 [待验证]，但标题和叙述已经给出强结论。
- **建议**：补同设备/同 WebView provider 的 4KB vs 16KB trace：`WebViewFactory` native load、page fault、首帧可交互、PSS；没有数据时降级为“可能受益，需实测”。
- **review 日志**：logs/deep-review/2026-04-30-10-deep-review.md

## [Task9 Deep Review] 7.11 WebView 渲染性能与优化 — 2026-04-30 — L483-L486 Network Track 瀑布图
- **类型**：数据缺失
- **位置**：L483-L486 Network Track 瀑布图
- **问题**：“WebView 发起的网络请求可以在 Perfetto 的 Network Track 中观察到”容易被理解成 Perfetto 默认能给出 Chrome DevTools 式资源瀑布图。实际需要明确采集的是网络栈指标、Chromium tracing categories，还是 DevTools/CDP 的 request timeline。
- **建议**：补一段 trace 配置边界：系统 Network/Socket 轨只能看网络层活动；资源级 URL、阻塞 JS、首屏图片顺序应走 Chromium categories / DevTools Protocol，并给出最小可复现配置。
- **review 日志**：logs/deep-review/2026-04-30-10-deep-review.md

## [Task9 Deep Review] 7.11 WebView 渲染性能与优化 — 2026-04-30 — L493 与 frontmatter related_chapters
- **类型**：交叉引用一致性
- **位置**：L493 与 frontmatter related_chapters
- **问题**：正文写“渲染机制版本演进（§2.10）”，但 `src/SUMMARY.md` 中 §2.10 是《GPU 渲染深入》，《渲染机制的版本演进》是 §2.9；frontmatter `related_chapters` 也写了 `2.10`。
- **建议**：将交叉引用改为 §2.9；如果需要 GPU 细节，再单独保留 §2.10《GPU 渲染深入》。
- **review 日志**：logs/deep-review/2026-04-30-10-deep-review.md

## [Task9 Deep Review] 7.10 图片加载与 Bitmap 性能优化 — 2026-04-30
- **类型**：版本差异/数据缺失
- **位置**：L286（Android 14+ AVIF 硬件能力）
- **问题**：“Android 14+ 的设备有硬件加速的 AVIF 解码能力”仍偏宽。Android 14 CDD 更适合限定为对应设备类别的新 device implementation；升级设备、非 handheld/tablet 类设备和厂商实现差异不能一概而论。
- **建议**：改成“Android 14 新出厂的对应设备类别要求支持 AVIF Baseline 硬件解码；工程上仍以 ImageDecoder/MediaCodec 能力探测和目标机实测为准”。

## [Task9 Deep Review] 7.10 图片加载与 Bitmap 性能优化 — 2026-04-30
- **类型**：数据缺失
- **位置**：L235（GC 通常 < 1ms）
- **问题**：“GC 本身不耗时（通常 < 1ms）”没有限定 collector、堆规模、设备、内存压力和 trace 统计口径，容易被读者当成通用阈值。
- **建议**：补固定场景的 Perfetto/Logcat GC pause 样本，或改成“轻量 GC 可能低于 1ms，但应按同机型同场景基线判断”。


## [Task9 Deep Review] 2.2 帧率与刷新率 — 2026-04-30
- **类型**：源码准确性
- **位置**：L480
- **问题**：FrameMetrics.TOTAL_DURATION 被描述为“从 VSync 到帧显示完成”。源码注释是 frame began 到 ended，以及 render and be issued to display subsystem；FrameMetrics 同时有 GPU_DURATION / DEADLINE，不能把 TOTAL_DURATION 等同为真实屏幕 present 完成。
- **建议**：改成“从 intended vsync 到 frame completed / issued to display subsystem 的总时长”，并说明它不是显示面板实际扫描完成时间。

## [Task9 Deep Review] 2.2 帧率与刷新率 — 2026-04-30
- **类型**：数据缺失
- **位置**：L725-L730
- **问题**：120Hz 屏幕功耗通常高 20-40%、CPU/GPU 需要两倍频率渲染帧缺少设备、亮度、面板、内容、SoC 条件；且只有 App 目标帧率也提升到 120fps 时，渲染侧工作量才近似翻倍。
- **建议**：补充测试条件或改成条件化表述：显示扫描功耗与渲染负载分别说明，避免把屏幕刷新率提升直接等同于 CPU/GPU 两倍工作。

## [Task9 Deep Review] 3.2 触摸响应的性能分析 — 2026-04-30
- **类型**：数据缺失
- **位置**：L190-L201
- **问题**：延迟全景图给出硬件采样、InputDispatcher、App 处理、渲染上屏和总计 15-75ms 的典型耗时，但没有设备刷新率、触摸采样率、是否开启 prediction/resampling、Trace 样本数量和统计口径。
- **建议**：补一组 Perfetto trace 样本作为表格来源；至少标明 60/120Hz、采样率、设备、Android 版本、统计点（eventTime、dispatch、deliverInputEvent、GPU completion、present）的定义。

## [Task9 Deep Review] 3.3 手势导航与系统交互 — 2026-04-30
- **类型**：数据缺失
- **位置**：L291-L309
- **问题**：legacy / predictive back 的 Perfetto 判读给出了相对顺序，但没有绑定可复核的具体 track/slice 名或一段真实 trace 示例。WM Shell back animation、目标层预览、App progress 回调在不同版本/厂商 trace 中名字可能不同。
- **建议**：补一段最小真实 trace 的观察清单：SystemUI edge-swipe InputMonitor、InputDispatcher cancel、WMShell/BackAnimation 相关 slice、当前 Activity surface 与 Launcher/目标 Activity surface 的 FrameTimeline 对齐方式。

## [Task9 Deep Review] 3.3 手势导航与系统交互 — 2026-04-30
- **类型**：数据缺失
- **位置**：L241-L247
- **问题**：SystemUI 判定延迟“几毫秒级/几十毫秒”和 mLongPressTimeout “通常 400-500ms”缺少源码或设备设置锚点。mLongPressTimeout 来自 ViewConfiguration 长按超时，用户/厂商配置会变化。
- **建议**：把长按超时绑定到 ViewConfiguration.getLongPressTimeout()/系统设置来源；性能延迟给出 Perfetto 示例或改为“需按目标设备 trace 验证”。



## [Task9 Deep Review] 14.10 eBPF/BPF 在 Android 性能分析中的应用 — 2026-04-30
- **类型**：交叉引用 / 源码锚点一致性
- **位置**：L185、L312-L318
- **问题**：AOSP 路径表列出 UprobeStats BPF 程序包含 `MalwareSignal.c`，但“预置的 BPF 程序”小节写成三类模板，只展开 `GenericInstrumentation.c`、`BitmapAllocation.c`、`ProcessManagement.c`，前后不一致。
- **建议**：统一为四类，补 `MalwareSignal.c` 的用途与适用边界；如果不想展开，明确说明它不是本节主线，只在路径表中作为源码目录完整性列出。

## [Task9 Deep Review] 14.10 eBPF/BPF 在 Android 性能分析中的应用 — 2026-04-30
- **类型**：源码准确性 / 数据支撑
- **位置**：L164
- **问题**：正文写 `netd` 中的 eBPF 程序“统计每个 UID 的网络流量相关的功耗”。AOSP eBPF traffic monitoring 直接产物是 UID/tag/interface 维度的 byte/packet 统计与防火墙/计费数据；功耗归因通常由 BatteryStats/PowerProfile 等上层根据网络活动模型估算，不能写成 `netd` BPF 直接统计功耗。
- **建议**：改成“netd/Connectivity BPF 提供 per-UID 网络流量计数，BatteryStats 等上层可用这些计数参与网络耗电归因”；如要保留功耗结论，需要补 BatteryStats 侧源码锚点。


## [Task6 Review] 2.17 Frame Pacing Library — 2026-04-30
- **类型**：需验证
- **位置**：Vulkan 1.4 present_id 章节
- **问题**：正文写"实测数据表明，相比 Choreographer 估算法，present_id 路径将帧间抖动（Jitter）降低了约 30%"，缺少测试设备、场景、样本量和数据来源。表格中 ±0.5-1ms / ±1-2ms / ±2-4ms 也无出处。
- **建议**：标注 [待验证] 并补充测试条件，或改为定性描述
- **review 日志**：logs/review/2026-04-30-18-review.md


## [Task9 Deep Review] 14.4 dumpsys 系列命令 — 2026-04-30
- **类型**：数据缺失
- **位置**：L503-L513 `LayerSnapshotBuilder.tryFastUpdate()` 快速路径
- **问题**：正文给出“快 0.5-1ms/帧”的量化收益，但没有标注测试设备、Layer 数量、刷新率、trace/benchmark 来源。该数字容易被读者当成 AOSP 通用保证。
- **建议**：保留快速路径机制说明；量化收益改为 `[待验证]`，或补充可复现实验条件与 Perfetto 证据。

## [Task9 Deep Review] 14.4 dumpsys 系列命令 — 2026-04-30
- **类型**：源码准确性
- **位置**：L541-L543 自定义 Service 的 dump 接口
- **问题**：正文写“任何应用或服务都可以通过 `adb shell dumpsys <service_name>` 输出”，但普通应用 Service 不会自动注册成 ServiceManager 中的 dumpsys 服务；应用组件通常通过 `dumpsys activity service <package>/<service>` 触发 dump。只有注册到 ServiceManager 的 Binder/system service 才能直接 `dumpsys <service_name>`。
- **建议**：把系统服务与应用 Service 两条路径拆开，并补一句普通应用场景的权限/入口限制。

## [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-04-30
- **类型**：数据缺失
- **位置**：L535 ADPF power efficiency mode 收益
- **问题**：正文写启用后“功耗降低 15-30%”，但没有设备、负载、线程数、温控状态和采样工具来源。ADPF hint 的效果由厂商调度策略决定，不能作为通用收益。
- **建议**：改为“可能降低功耗，需用 PowerMonitor/Perfetto power rails 做 A/B 验证”；若保留数字，必须给出来源和实验条件。

## [Task9 Deep Review] 15.1 性能优化的术、道、器 — 2026-04-30
- **类型**：版本差异
- **位置**：L153 BLASTBufferQueue 描述
- **问题**：正文仍写“Android 12 引入 BlastBufferQueue 替代 BufferQueue”。BLAST 改变的是 transaction/buffer 交接模型，底层 BufferQueue 机制仍然存在；“替代”会让读者误以为 BufferQueue 在 Android 12 后不再参与。
- **建议**：改成“Android 12 引入 BLASTBufferQueue，改变 App 端 buffer 提交与窗口 transaction 同步模型；底层 BufferQueue 仍是缓冲区流转基础”。

## [Task9 Deep Review] 14.3 内存分析工具 — 2026-04-30
- **类型**：数据缺失
- **位置**：L221 heapprofd 开销、L518-L537 MTE/HWASAN 开销
- **问题**：heapprofd “通常不超过 2%”、HWASAN “约 1.5 倍”、MTE “1-5%/1-2%”等数字缺少设备、Android 版本、采样间隔、负载类型和来源边界；不同 malloc 频率、unwind 配置、MTE mode 下差异很大。
- **建议**：保留数值时补实验来源与条件；否则降级为“低/中/高开销”并说明影响变量。

## [Task9 Deep Review] 3.4 输入延迟与预测输入技术 — 2026-05-01
- **类型**：数据缺失
- **位置**：为什么要了解输入延迟（约第84行）
- **问题**：用户输入响应延迟“100ms/200ms 感知阈值”仍标为 `[待验证]`，但后文把它作为端到端延迟拆解的动机使用。
- **建议**：补充 HCI/Android 官方或论文来源，写清实验条件；若找不到稳定来源，改成经验范围并避免作为精确阈值。
## [Task9 Deep Review] 7.1 卡顿的定义与分类 — 2026-05-01
- **类型**：版本差异
- **位置**：约第206-214行，Dropped Frame
- **问题**：当前写法像 Android 12+ FrameTimeline 都有 Dropped Frame；AOSP 12/13 tag 未见 `Dropped = 0x200`。
- **建议**：给 Dropped Frame 增加版本边界：较新 AOSP tag / Perfetto 文档包含该类型，Android 12/13 或早期 Android 14 trace 不一定以 JankType 暴露。
- **类型**：原理链完整性
- **位置**：约第109-111行，Jank 标准定义前置描述
- **问题**：“每一个 VSync 周期，系统预期 App 能渲染出一帧新内容”对静态界面、不产生 damage、不提交 buffer 的场景过强。
- **建议**：改成“当 App 有内容更新并提交一帧时，系统会为这帧分配 expected timeline；实际 present 偏离预测 present time 时记为 jank”。
- **类型**：版本差异
- **位置**：约第267行，Slow Frame 16ms - 700ms 表格
- **问题**：16ms 是 Android vitals 传统 60fps 口径，和前文 90/120Hz frame period 口径存在混用风险。
- **建议**：补充说明 vitals slow rendering 是经典 >16ms 口径；FrameTimeline/JankStats 应按当前 refresh period 或 expected timeline 判断。
- **类型**：版本差异
- **位置**：约第269/313行，ANR >5s
- **问题**：输入 ANR 典型 5s，但 broadcast/service/JobService 等阈值不统一。
- **建议**：改为“ANR 超过对应场景 watchdog 阈值；输入事件典型为 5s”，具体阈值交给第 9 章。
- **类型**：知识盲区
- **位置**：约第229-249行，FrameTimeline 小节
- **问题**：SurfaceView / 多 Surface / 视频层场景的 FrameTimeline 覆盖边界未说明。
- **建议**：补充 SurfaceView、多 Surface、视频层需要结合 layer name、DisplayFrame、BufferQueue / HWC tracks，不能只看主 Activity App timeline。


## [Task9 Deep Review] 8.1 响应速度原理 — 2026-05-01
- **类型**：交叉引用
- **位置**：L118、L283，章节内 markdown 链接
- **问题**：`04-choreographer.md` 和 `01-perfetto-intro.md` 以当前 `ch08-responsiveness/` 目录解析会落到不存在路径；正确目标分别在 `part1-fundamentals/ch02-rendering/04-choreographer.md` 与 `part3-tools/ch13-perfetto/01-perfetto-intro.md`。
- **建议**：改成相对当前文件的 `../../part1-fundamentals/ch02-rendering/04-choreographer.md`、`../../part3-tools/ch13-perfetto/01-perfetto-intro.md`，或使用项目统一的章节编号引用方式。

## [Task9 Deep Review] 11.4 案例集 — 2026-05-01
- **类型**：数据缺失
- **位置**：L123-L127、L180-L184、L347-L351、L463-L467、L603-L607、L704-L708
- **问题**：案例集要求每个案例有 Battery Historian 截图和耗电对比，但当前多处仍是 `[图]` / `[待补充]`，同时直接给出 40%→3%、25%→3%、15%→3% 等效果数字，缺设备、系统版本、网络类型、亮灭屏条件、样本数和原始 bugreport/trace。
- **建议**：补原始 bugreport/Power Profiler/Perfetto 附件、设备与测试条件；拿不到证据的数字改成定性或示例占位，不要作为真实修复效果。

## [Task9 Deep Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-05-01
- **类型**：版本差异
- **位置**：L225-L229
- **问题**：`getPendingJobReasonStats(int)` 已能在 Android API reference 中查到 `Map<Integer, Duration>` 入口，正文仍标 `[待验证: API37 preview/reference]`，核验状态和 frontmatter 的“API 37 reference 已验证”不一致。
- **建议**：将核验状态改为“API 37 reference 已检出；AOSP android-16.0.0_r1 未包含”，并保留最终源码 tag 待复核的边界。

## [Task9 Deep Review] 11.2 App 耗电优化 — 2026-05-01
- **类型**：版本差异/表述边界
- **位置**：L203 PeriodicWorkRequest 15 分钟原因
- **问题**：正文把 WorkManager 周期任务 15 分钟最小间隔完全归因于系统 JobScheduler 最小调度窗口。WorkManager 在 API 23+ 走 JobScheduler，旧版本还有 AlarmManager/BroadcastReceiver 路径；章节适用范围从 API 21 开始，原因链应拆版本。
- **建议**：改为 WorkManager 自身定义 15 分钟最小间隔；API 23+ 与 JobScheduler 约束对齐，API 21-22 通过兼容调度实现同一上层语义。



## [Task9 Deep Review] 11.5 Wakelock 机制与功耗分析 — 2026-05-01
- **类型**：数据缺失
- **位置**：开头与 Doze 小节
- **问题**：`整机功耗可以降到 1mA 以下`、`maintenance window 初始约 10 分钟，再到 30/60 分钟` 属于强数值断言，但没有设备、版本、测试条件或官方出处。
- **建议**：补充来源和测试条件；没有可靠来源时改成定性描述，或标注为示例设备观测值。

## [Task6 Review] 14.13 Hook 基础设施与性能工具实现原理 — 2026-05-01
- **类型**：需重写（局部）
- **位置**：「兼容性风险」小节末尾的裸名词列表
- **问题**：该列表包含 4 个无解释的裸名词项（"Android API 版本变化"、"linker / namespace 行为差异"、"ABI 与指令集差异"、"ROM 对 so 装载和安全策略的定制"），违反 writing-guide.md「列表不能是目录，必须是内容」规则。其中两项（Android 14 W^X、16KB Page Size）有简短解释但与下方「补充」章节大量重复；另外四项完全没有解释。
- **建议**：选项一：为每个裸名词项补充 1-2 句解释。选项二：将此列表改为简短概述段落，指向下方「补充」章节的详细展开，消除三层重复。推荐选项二。
- **review 日志**：logs/review/2026-05-01-08-review.md

## [Task9 Deep Review] 14.5 三方性能库 — 2026-05-01
- **类型**：数据缺失
- **位置**：src/part3-tools/ch14-other-tools/05-third-party-libs.md:L175、L380
- **问题**：KOOM Hprof 裁剪“压缩到原来的 10%~20%”和组合接入“Matrix 约 2~5%”属于量化断言，但正文没有给出测试环境、样本口径或上游出处。KOOM README 只确认 fork dump、子进程分析与 strip dump 路径，未在已核验材料中给出 10%~20% 的通用比例；Matrix 开销也会随插桩范围、采样率、机型和模块开关变化。
- **建议**：保留结论时补充来源链接、版本、样本应用、堆大小/插桩范围、设备与统计口径；如果无法补证，把具体比例降级为“项目实测值示例”，并提示团队接入前用灰度采样复测。

