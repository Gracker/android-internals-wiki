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
