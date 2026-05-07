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

## [Task9 Deep Review] 5.2 EAS 能量感知调度 — 2026-05-01
- **类型**：数据缺失
- **位置**：“全大核架构的调度边界”中 Snapdragon 8 Elite Performance 核 capacity≈837（约 L244-L252）
- **问题**：837/1024 是强量化结论，但当前只挂到个人素材来源，缺少设备内核导出的 cpu_capacity 或厂商公开资料锚点。
- **建议**：补一条可复核证据：例如目标设备 `/sys/devices/system/cpu/cpu*/cpu_capacity` 样本、设备树 capacity-dmips-mhz，或明确标注为某台设备实测值，避免把单设备 capacity 当成通用 SoC 事实。

## [Task9 Deep Review] 5.4 DVFS 与功耗管理 — 2026-05-01
- **类型**：数据缺失
- **位置**：“4GHz 时代的能效红线”（约 L111-L117）
- **问题**：“限到 3.5-3.8GHz 只损失 5-10% 单核算力、功耗降低 20-30%”是强量化结论，当前仅标待验证，缺测试条件、SoC、温控状态、benchmark 与功耗测量口径。
- **建议**：补充实测条件或公开资料来源；如果短期无法补证据，应降级为定性描述，不保留具体百分比。


## [Task9 Deep Review] 2.9 渲染机制的版本演进 — 2026-05-01
- **类型**：数据缺失
- **位置**：L472 版本演进表 16KB 页
- **问题**：“TLB 命中率提升约 9%，渲染管线有效带宽增益”没有给出设备、内核、负载、计数器或官方来源。16KB page size 的公开数据更多围绕启动、功耗、相机等宏观指标，不能直接推出渲染带宽收益。
- **建议**：删除 9% 裸数字，或补充同机 4KB/16KB、GPU/CPU counter、fence/RenderThread trace 的可复现实验。


## [Task9 Deep Review] 2.16 Sync Fence 框架与帧同步机制 — 2026-05-01
- **类型**：数据缺失
- **位置**：L278-L280 Timeline Semaphore 可观测性
- **问题**：“在 Perfetto 中仍会以 fence wait 的形式呈现”缺少 producer、driver、Vulkan/Surface 边界前提。Vulkan 内部 timeline wait 不一定自动等价于 Android graphics fence wait slice。
- **建议**：补 trace producer/driver 条件；区分 Vulkan 队列内部等待、sync_file fd 等待、SurfaceFlinger latch/present 等待。


## [Task9 Deep Review] 15.7 AOSP 代码阅读 — 2026-05-01
- **类型**：源码准确性
- **位置**：L184-L186 Logcat 反查源码
- **问题**：小节示例讲 `D/Choreographer: Skipping ...` 日志，但验证锚点写成 `frameworks/base/core/java/android/os/Trace.java`。该日志应回到 `frameworks/base/core/java/android/view/Choreographer.java`，Trace.java 与日志定位无直接对应。
- **建议**：把该小节验证锚点改为 Choreographer.java；Trace.java 只保留在 Perfetto traceBegin/traceEnd 小节。


## [Task9 Deep Review] 15.7 AOSP 代码阅读 — 2026-05-01
- **类型**：版本差异
- **位置**：L302/L306 Choreographer 回调顺序
- **问题**：正文只写 Input → Animation → Traversal 三类回调。对 Android 16 源码阅读来说，还应提醒现代 Choreographer 已包含 Insets Animation 与 Commit 阶段，否则读者对照当前 doFrame() 会漏掉回调队列。
- **建议**：补一句：早期主链是 Input/Animation/Traversal；现代源码还要看 INSETS_ANIMATION 和 COMMIT。

## [Task9 Deep Review] 3.2 触摸响应的性能分析 — 2026-05-01
- **类型**：数据缺失
- **位置**：L80 / L193-L196 延迟预算表
- **问题**：30-80ms 总触摸延迟、InputReader <1ms、InputDispatcher 1-3ms 等数字缺少设备、刷新率、trace 场景、采样次数和统计口径。
- **建议**：补一组 Perfetto 样例：设备型号、刷新率、触摸采样率、场景、p50/p95；没有样本时把数字改成经验范围并标注需按目标设备实测。


## [Task9 Deep Review] 14.9 Android Camera 性能与 Perfetto 分析 — 2026-05-01
- **类型**：数据缺失
- **位置**：L490 CameraX 冷启动额外 80-150ms
- **问题**：“CameraX 首帧前常见额外 80-150ms 初始化开销”缺少测试条件、版本、设备和样本范围。CameraX 不同 use case、extension、device quirk 与预热策略差异很大。
- **建议**：补 benchmark 条件，至少写清 CameraX/Camera2 版本、use case、设备、冷/热启动定义、p50/p95；没有一手数据时改成“可能引入额外初始化阶段，需按首帧 trace 实测”。


## [Task9 Deep Review] 19.23 网络 APM 底层捕获原理 — 2026-05-01
- **类型**：原理口径
- **位置**：L93 Interceptor 与 DNS/TCP 阶段
- **问题**：正文说“拦截器看到请求链条，DNS 查询和 Socket 建连已经由 OkHttp 内部完成或复用了连接”。这对 network interceptor 更接近，但 application interceptor 的 chain.proceed() 会包住后续 ConnectInterceptor，能量到包含 DNS/建连的总耗时，只是拿不到阶段回调。
- **建议**：拆成两句：application interceptor 可量到一次 proceed 的总耗时但不能拆 DNS/TCP/TLS；network interceptor 运行时通常已经有 connection，因此更不能提供 dnsStart/connectStart 阶段口径。


## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-05-01
- **类型**：数据缺失
- **位置**：L317-L330 参考基线数据表
- **问题**：表格给出 Pixel 8 / Android 16 各阶段秒级耗时和占比，但没有 bootstat、dmesg、Perfetto 或复现实测条件。正文虽写“估算值”，仍使用了具体机型和具体区间，容易被读者当作基准数据引用。
- **建议**：补一份真实 bootstat -l / dmesg / Perfetto 截图或原始文本；拿不到实测时，删除 Pixel 8 标签，改成“示意区间”，并避免给精确占比。

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-05-01
- **类型**：版本差异
- **位置**：L408 dm-verity 适用版本
- **问题**：正文写“Android 7.0 起 dm-verity 默认启用”。dm-verity / Verified Boot 支撑链在 Android 4.4 已出现，Android 7.0 关键变化是更严格的 verified boot enforcement 与 FEC 等能力。
- **建议**：改成“Android 7.0 起进入强制 Verified Boot 语义更明确的阶段”；若只服务本书 Android 8-16 范围，直接写“在本书覆盖版本内默认按强制校验链分析”。

## [Task9 Deep Review] 5.3 大小核架构 — 2026-05-01
- **类型**：原理口径
- **位置**：L180 PELT 时间尺度
- **问题**：正文把 PELT 32ms 写成“时间常数约 32ms（1024us × 32）”。Linux PELT 通常以 32ms half-life/半衰期描述，1024us 是采样周期量级；写成时间常数会误导读者理解衰减曲线。
- **建议**：改为“PELT 的历史贡献约每 32ms 衰减一半”，不要写成时间常数。


## [Task9 Deep Review] 5.3 大小核架构 — 2026-05-01
- **类型**：原理口径
- **位置**：L427-L430 线程优先级与大核选核
- **问题**：正文说 Process.setThreadPriority() 会让调度器更积极地把高优先级线程放到大核。nice/priority 主要改变 CFS 权重和抢占机会，不是稳定的大核选择接口；现代 Android 更直接的输入是 task profile、cpuset、uclamp、Power HAL hint 和厂商调度策略。
- **建议**：把 setThreadPriority 降级为“影响调度权重/延迟”的间接因素；大核倾向改写为 cpuset/uclamp/Power HAL/vendor policy 的结果。

## [Task9 Deep Review] 5.5 Thermal 管控 — 2026-05-01
- **类型**：数据缺失
- **位置**：L290（getThermalHeadroom >1.0 解释）
- **问题**：Android 文档只保证 1.0 对应 SEVERE 阈值，>1.0 没有到具体 thermal status 的映射，可能仍是 SEVERE，也可能是更重限频。
- **建议**：把“表示已经超过阈值并处在更重限频状态”改为“超过 SEVERE 阈值，但不映射到具体状态；需要结合 thermal status/thresholds 判断”。

## [Task9 Deep Review] 5.5 Thermal 管控 — 2026-05-01
- **类型**：数据缺失
- **位置**：L443-L447（16KB/MMU 功耗 4.5% 与延迟温控）
- **问题**：4.5% MMU 功耗和“温控降频被推迟”仍缺设备、SoC、内核、负载、测量方法或原始链接；当前 `[待验证]` 不足以支撑“实测数据显示/可观测优化”。
- **建议**：补可复核 benchmark/论文/厂商白皮书；补不上时删除精确数字和因果外推，仅保留“可能影响页表/TLB 开销，热收益需实测”。

## [Task9 Deep Review] 18.4 Android View 混合渲染链路 — 2026-05-01
- **类型**：数据缺失/观测路径
- **位置**：L202、L226（dumpsys SurfaceFlinger 字段与合成类型）
- **问题**：`activeBuffer` / `latched buffer` 与 `GLES/HWC/OVERLAY` 缺少 Android 版本化样例；现代 HWC2/CompositionEngine 输出常见口径是 `CLIENT` / `DEVICE` 等，直接写 `HWC/OVERLAY` 容易让排查命令对不上。
- **建议**：补一段 Android 14-16 dumpsys 或 Perfetto SurfaceFlinger layer 示例，明确字段名和 composition type 在不同版本/OEM 上可能不同。

## [Task9 Deep Review] 14.3 内存分析工具 — 2026-05-01
- **类型**：数据缺失
- **位置**：L547
- **问题**：malloc hooks “2-5 倍分配延迟”缺少 AOSP/实测来源。
- **建议**：补测试条件或改成定性“显著增加分配开销”。

## [Task9 Deep Review] 14.13 Hook 基础设施与性能工具实现原理 — 2026-05-01
- **类型**：版本口径
- **位置**：L418
- **问题**：xHook 官方支持 Android 4.0-10/API 14-29，写“不支持 Android 14+”范围过宽且滞后。
- **建议**：改为“不支持 Android 11+；官方支持范围 API 14-29”。

## [Task9 Deep Review] 14.13 Hook 基础设施与性能工具实现原理 — 2026-05-01
- **类型**：原理补充
- **位置**：L178-L182
- **问题**：PLT Hook 盲区只给结论，缺少同一 so 内直接 BL/B 调用不经 PLT 的例子。
- **建议**：补一句同一 ELF 内部调用通常不走 PLT/GOT。

## [Task9 Deep Review] 5.3 大小核架构 — 2026-05-02
- **类型**：数据/术语缺失
- **位置**：核心迁移的触发条件 / PELT 描述
- **问题**：正文把 32ms 写成“时间常数”。PELT 中常见表述是 32ms half-life/半衰期；严格的指数时间常数不是 32ms。
- **建议**：将“时间常数约 32ms”改为“半衰期约 32ms”，必要时补一句 decay y^32≈0.5 的来源。

## [Task9 Deep Review] 5.5 Thermal 管控 — 2026-05-02
- **类型**：数据缺失/版本细节
- **位置**：Sustained Performance Mode API
- **问题**：正文称 CTS 要求“帧率不能低于未开启模式时的水平”。AOSP 性能管理文档的核心要求是开启 sustained mode 后约 30 分钟内帧率变化 <5%；与未开启模式的比较口径需要按 CTS 原文复核，当前表述可能过强。
- **建议**：补 CTS 原文链接或源码测试名，改成“稳定性 <5%”为主，避免写成绝对不低于普通模式。

## [Task9 Deep Review] 2.16 Sync Fence 框架与帧同步机制 — 2026-05-03
- **类型**：数据缺失
- **位置**：L299-L307 16KB 页对 Fence 路径的潜在影响
- **问题**：该段虽标注待验证，但仍把 16KB 页、TLB miss、GPU IRQ → dma_fence signal → SurfaceFlinger wakeup 延迟串成较具体因果链；目前缺同机 4KB/16KB kernel ftrace、perf counter 与 Perfetto fence wait 尾部抖动数据。
- **建议**：在补齐 GPU IRQ 时间戳、dma_fence_signal、sched_wakeup、TLB miss/perf counter 对照前，建议保留在“待验证研究假设”附录，不放入版本演进主线。

## [Task9 Deep Review] 7.2 卡顿原因体系 — 2026-05-03
- **类型**：数据与案例支撑
- **位置**：L380-L387
- **问题**：16KB Page Size 段落把 Page Fault 频率下降 3-5%、`mm_filemap_add_to_page_cache` 频率下降写成已验证结论，但官方公开数据更接近“内存压力下启动平均 3.16% 改善”等口径，未见当前这组指标来源。
- **建议**：改用官方 16KB page size 性能数据，或补本地 Perfetto 对比实验条件：设备、内核页大小、trace config、page-fault / mmap / TLB 观察指标。
- **review 日志**：logs/deep-review/2026-05-03-02-deep-review.md

## [Task9 Deep Review] 7.2 卡顿原因体系 — 2026-05-03
- **类型**：交叉引用一致性
- **位置**：frontmatter related_chapters / L180-L190
- **问题**：正文新增 DeliQueue，但 related_chapters 未包含 1.13 `MessageQueue / DeliQueue`，读者无法跳到专章核对行为变更。
- **建议**：补交叉引用 1.13，并在 DeliQueue 小节显式指向 1.13。
- **review 日志**：logs/deep-review/2026-05-03-02-deep-review.md

## [Task9 Deep Review] 8.7 Baseline Profiles 与编译优化实践 — 2026-05-03
- **类型**：数据与案例支撑
- **位置**：L250
- **问题**：“Startup Profile 对冷启动贡献 40-60%”没有来源、样本和基线；官方只给 Startup Profiles 相比 Baseline Profiles alone 通常 15-30% 的启动改善口径。
- **建议**：补 Macrobenchmark 对比或改成官方 15-30% 表述，并说明测试路径、设备、AGP 版本。
- **review 日志**：logs/deep-review/2026-05-03-02-deep-review.md

## [Task9 Deep Review] 8.7 Baseline Profiles 与编译优化实践 — 2026-05-03
- **类型**：数据与案例支撑
- **位置**：L340-L342
- **问题**：“Google 建议不超过几千条规则”未给官方阈值。官方更可核验的是 binary profile 小于 1.5 MB 等限制和实际编译耗时。
- **建议**：用 profile/profm 大小、`cmd package compile -m speed-profile` 耗时、oat/vdex 增量做可执行验证。
- **review 日志**：logs/deep-review/2026-05-03-02-deep-review.md


## [Task9 Deep Review] 1.7 ART 编译管线与 dex2oat 优化 — 2026-05-03
- **类型**：数据与版本口径支撑
- **位置**：L140（Cloud Compilation 与 SDM）
- **问题**：正文写 Android 16 Play Store 可直接下发预编译 `.odex` / `.vdex` 产物并由 SDM 校验，但当前 sources 只给了泛化 Google Blog 占位，没有能核验 Android 16 / SDM / 预编译产物格式的官方链接或源码锚点。
- **建议**：补 developer.android.com / AOSP / Play delivery 官方锚点，标明 SDM 文件内容、适用安装来源、设备端校验和 fallback 到本地 dex2oat 的条件；补不到则降级为 `[待验证]` 或删除具体 `.odex/.vdex` 断言。
- **review 日志**：logs/deep-review/2026-05-03-06-deep-review.md

## [Task9 Deep Review] 19.15 Baseline Profiles 与编译优化 — 2026-05-03
- **类型**：源码/API 口径
- **位置**：L221-L226（ProfileVerifier result code 表）
- **问题**：正文列出 `RESULT_CODE_NO_PROFILE`；AndroidX main 源码的 `ProfileVerifier.CompilationStatus` 当前为 `RESULT_CODE_NO_PROFILE_INSTALLED`，而 developer.android.com 调试示例仍出现 `RESULT_CODE_NO_PROFILE`。这是文档与源码口径不一致点，容易让读者复制到具体版本时编译失败。
- **建议**：按实际依赖的 `androidx.profileinstaller` 版本核对常量名；正文注明“以项目依赖版本的 ProfileVerifier 为准”，或同时给出 docs 口径与 AndroidX main 源码口径。
- **review 日志**：logs/deep-review/2026-05-03-06-deep-review.md

## [Task9 Deep Review] 7.4 典型场景分析 — 2026-05-03
- **类型**：数据/观测点支撑
- **位置**：L282-L288（Predictive Back Perfetto 观察点）
- **问题**：正文写 `predictive_back_progress` 计数器，但未给出 AOSP/Perfetto 官方数据源或 trace 字段来源；公开文档更稳定的是 OnBackInvokedCallback/OnBackAnimationCallback、Window/Shell/SystemUI 与 SurfaceFlinger 轨道，不能把该 counter 当成跨设备标准观察点。
- **建议**：补真实 Android 15/16 trace 截图或 SQL 字段；补不上时改成“对 `onBackProgressed()` 自定义 Trace + SystemUI/Shell/SF 轨道联合判断”。
- **review 日志**：logs/deep-review/2026-05-03-08-deep-review.md

## [Task9 Deep Review] 7.4 典型场景分析 — 2026-05-03
- **类型**：源码/Trace 锚点准确性
- **位置**：L289（SurfaceFlinger `composeModese` slice）
- **问题**：`composeModese` 不是稳定可核验的 SurfaceFlinger slice 名，且疑似拼写错误；不同 Android 版本/OEM 的 SF/CompositionEngine/HWC 轨道命名差异较大。
- **建议**：改成可验证口径：FrameTimeline jank type、SurfaceFlinger expected/actual timeline、CompositionEngine/validateDisplay-presentDisplay、CLIENT/DEVICE composition type、present fence；若保留 slice 名，必须附 trace 样例版本。
- **review 日志**：logs/deep-review/2026-05-03-08-deep-review.md

## [Task9 Deep Review] 7.6 案例集 — 2026-05-03
- **类型**：数据与案例支撑
- **位置**：L79-L127、L156-L199、L228-L274、L301-L349、L390-L466（五个主案例）
- **问题**：章节已声明数值为案例化示例且多处 `[待验证]`，但锚点要求每个案例包含 Trace 截图/关键数据、修复方案、效果对比。当前缺 trace 文件名、设备/系统版本、刷新率、脚本、采样窗口和前后对照，正式发布时支撑力不足。
- **建议**：为每个案例补一份最小证据包：Perfetto trace 文件或截图、采集配置、设备/版本/刷新率、复现脚本、核心 SQL/指标、修复前后统计；补不上时将精确 Jank 率和耗时数字降级为“示例口径”。
- **review 日志**：logs/deep-review/2026-05-03-08-deep-review.md

## [Task9 Deep Review] 7.8 RecyclerView 列表滑动性能深度优化 — 2026-05-03
- **类型**：API 语义
- **位置**：L280、L415-L421 `setHasFixedSize(true)`
- **问题**：`setHasFixedSize(true)` 的语义是 Adapter 内容变化不改变 RecyclerView 自身尺寸，可减少 RecyclerView 级 requestLayout；它不等于 item 内容变化时不重新 measure 子 View，也不能保证动态高度 item 的滚动范围一定正确。
- **建议**：改为“仅当 RecyclerView 自身尺寸不随 adapter 内容变化时使用；动态高度/内容改变场景要实测 scroll range 与 child measure”。
- **review 日志**：logs/deep-review/2026-05-03-13-deep-review.md

## [Task9 Deep Review] 7.9 感知流畅性：步幅波动与无掉帧卡顿 — 2026-05-03
- **类型**：版本差异
- **位置**：L170-L189 `AnimationUtils.lockAnimationClock()` 代码片段
- **问题**：正文引用双参数 `lockAnimationClock(vsyncMillis, expectedPresentationTimeNanos)`，但章节适用范围写 API 29-37；旧版本只有单参数/不含 expectedPresentationTimeNanos 的实现形态。核心毫秒截断结论成立，但源码片段需要按版本标注。
- **建议**：补一句“Android 15/16/main 为双参数；早期版本只锁定 vsyncMillis，`frameTimeNanos / NANOS_PER_MS` 的毫秒截断行为仍是关键点”。
- **review 日志**：logs/deep-review/2026-05-03-13-deep-review.md

## [Task9 Deep Review] 7.9 感知流畅性：步幅波动与无掉帧卡顿 — 2026-05-03
- **类型**：API 语义
- **位置**：L244-L250 RelativeFrameTimeHistogram 精度限制
- **问题**：`addRelativeFrameTimeMillis(int)` 的输入单位是整数毫秒，但 AOSP android-16 `RelativeFrameTimeHistogram` 预设 bucket 在 -20ms 到 20ms 附近是 2ms 一档，并非“显式暴露 1ms 精度”的完整统计分辨率。
- **建议**：改成“输入以 ms 为单位，bucket 近 deadline 区域约 2ms 一档；它统计相对 deadline 的帧时间分布，不直接记录位移采样”。
- **review 日志**：logs/deep-review/2026-05-03-13-deep-review.md


## [Task9 Deep Review] 8.5 案例集 — 2026-05-03
- **类型**：数据缺失
- **位置**：L118-L170 Reddit / L249-L263 Disney+ R8 案例
- **问题**：Reddit 与 Disney+ 指标已经能定位到 Android Developers Blog 原文，但正文仍以“Google Performance Spotlight Week 2025”概称承载数据；读者无法区分 Reddit 的线上发布指标、Google/Reddit 后续 macrobenchmark 分析，以及 Disney+ 的 `proguard-android.txt` → `proguard-android-optimize.txt` 配置迁移口径。
- **建议**：补原始 URL：`how-reddit-used-the-r8-optimizer-for-high-impact-performance-improvements` 与 `use-r8-to-shrink-optimize-and-fast-track-your-app`；把 Reddit 的线上效果、Baseline/Startup Profile 深挖实验和 Disney+ 配置迁移拆成不同证据层。

## [Task9 Deep Review] 8.5 案例集 — 2026-05-03
- **类型**：数据缺失
- **位置**：L370-L373 AutoFDO Android GKI / Pixel 表
- **问题**：当前表写 App cold start `-2.1%`、Boot `1-2%`，但 AOSP `android16-6.12/gki/aarch64/afdo/README.md` 当前 6.12.69 profile / Pixel 8 口径为 Cold App launch `4.8%`、Boot `1.3%`、Binder-rpc `20.7%`、Hwbinder `26.4%`；`android-mainline` 汇总口径则是 Boot `2-3%`、Cold App launch `3-4%`、Binder-rpc `8-9%`、Hwbinder `12-18%`。现稿混用了旧冷启动数字和最新 HWBinder 数字。
- **建议**：固定一个口径：要么用 android16-6.12 当前 profile 数字并标注 Pixel 8 / 6.12.69；要么用 android-mainline 汇总范围。不要把不同 profile 日期的数据放在同一行表里。

## [Task9 Deep Review] 8.9 Android 游戏性能与 Game Mode/State API — 2026-05-03
- **类型**：知识盲区
- **位置**：L406 OEM 游戏模式对 Trace 的干扰
- **问题**：正文仍保留“各主要 OEM 厂商游戏模式的关闭方法列表”占位。该列表直接影响 Game Mode、interventions、ADPF 与 OEM 私有策略的归因实验。
- **建议**：补 Pixel / Samsung / Xiaomi / OPPO / vivo 的关闭入口或最小核验清单；无法全量覆盖时，至少说明如何确认 OEM 面板、`game_overlay` 和系统省电模式没有污染基线。


## [Task9 Deep Review] 9.2 ANR 类型与触发条件 — 2026-05-03
- **类型**：版本/调试路径
- **位置**：L331-L332 /data/anr/anr_* 命令
- **问题**：正文给出 Android 11+ `adb shell cat /data/anr/anr_*` 作为查看 trace 命令，但 Android 14+ 非 root 设备通常无法直接访问 /data/anr；同书 9.1 已写 bugreport / ApplicationExitInfo 路径，两个章节会造成实践口径不一致。
- **建议**：命令旁标注“root/userdebug 或 Android 13- 可用”；Android 14+ 普通设备优先用 adb bugreport 或 ApplicationExitInfo.getTraceInputStream()。
- **review 日志**：logs/deep-review/2026-05-03-18-deep-review.md

## [Task9 Deep Review] 9.1 ANR 设计思想 — 2026-05-03
- **类型**：版本差异
- **位置**：L211（getProviderMimeTypeAsync 版本线）
- **问题**：正文把 getProviderMimeType()/getProviderMimeTypeAsync 写成 API 31+ 的通用当前路径。AOSP android-12 的 IActivityManager 确有 getProviderMimeTypeAsync；android-14 的 ContentResolver.getType() 已走 IContentProvider.getTypeAsync() / ActivityManager.getMimeTypeFilterAsync() 等路径，原表述会把 Android 14+ 读者带到旧接口。
- **建议**：拆成 Android 12 引入 getProviderMimeTypeAsync 的历史节点，以及 Android 14+ ContentResolver.getType()/getTypeAsync/getMimeTypeFilterAsync 的当前路径。

## [Task9 Deep Review] 9.1 ANR 设计思想 — 2026-05-03
- **类型**：版本差异/交叉一致性
- **位置**：L400-L404（ANR trace 文件存储演进）
- **问题**：Android 10 段已写“按时间和进程分别存储”，Android 13 段又写“改为按进程独立存储”，两个版本节点的差异边界重叠。
- **建议**：重新核对 AOSP trace 文件命名/写入路径演进，把 Android 10 的 traces.txt→/data/anr/anr_* 与 Android 12/13 的可靠性或按进程改进拆清楚，避免重复归因。

## [Task9 Deep Review] 2.1 Android 渲染架构全景 — 2026-05-04
- **类型**：数据缺失
- **位置**：L546 Vulkan CPU 效率段
- **问题**：“OpenGL ES 驱动状态检查在复杂场景中可能占去数毫秒帧时间”缺少测试条件、设备、trace 或 benchmark 来源。该断言与 HWUI 后端选择强相关，不能脱离 SoC/驱动/场景写成通用成本。
- **建议**：补充具体 benchmark/Perfetto/GPU driver trace，至少给出设备、API 后端、绘制负载、帧预算与 CPU submit 时间；没有数据时改成定性描述。

## [Task9 Deep Review] 2.1 Android 渲染架构全景 — 2026-05-04
- **类型**：原理链完整性
- **位置**：L548 Vulkan 多线程能力与 HWUI 架构
- **问题**：正文把 Vulkan 命令缓冲区可多线程构建，和 HWUI 的“主线程录制 DisplayList + RenderThread 回放”直接连成因果。UI 线程录制的是 View/DisplayList 指令，不是 Vulkan command buffer；是否利用 Vulkan 多线程提交取决于 SkiaVulkan/HWUI 内部实现与具体 workload。
- **建议**：把该段边界收窄：Vulkan 的多线程命令构建主要适用于 native/game/自管 Vulkan renderer；HWUI 场景只说 SkiaVulkan 后端可能降低 CPU submit/driver 开销，避免暗示 UI 线程和 RenderThread 会并行构建 Vulkan command buffer。

## [Task9 Deep Review] 2.12 Window Manager Service 与窗口管理 — 2026-05-04
- **类型**：版本差异/源码准确性
- **位置**：L383 / L456 Android 17 `recreateOnConfigChanges`
- **问题**：正文把 API 37 `recreateOnConfigChanges` 归因到 Android 17 behavior changes 页面，但公开 `behavior-changes-all` 页主要写 IME 可见性恢复等行为；具体 flag 列表更直接的来源是 `android.R.attr#recreateOnConfigChanges`。同时“部分 uiMode”需要给出精确子场景或 AOSP/官方引用。
- **建议**：把来源补到 `developer.android.com/reference/android/R.attr#recreateOnConfigChanges`，并用官方列出的 colorMode、keyboard、keyboardHidden、navigation、touchscreen 等 flag 做表；`uiMode` 若保留，标注具体触发场景和来源，否则删除。

## [Task9 Deep Review] 10.4 低内存对系统性能的影响 — 2026-05-04
- **类型**：数据缺失
- **位置**：L267-L277 ZRAM 压缩比、swappiness 与 16KB page-cluster
- **问题**：正文给出 LZ4 典型 3:1 压缩比、Android 设备 swappiness 10-30 更适合、16KB page-cluster=0 可让 App 切换更快等判断，但没有给出设备配置、内核版本、算法、工作负载或 trace/benchmark 条件。
- **建议**：补一组可复核证据：`/sys/block/zram0/mm_stat`、`/proc/swaps`、`/proc/sys/vm/page-cluster`、页大小、压缩算法、App 切换 trace 或厂商公开数据；无法补证据时把数字改成示例而非通用结论。

## [Task9 Deep Review] 9.3 ANR 分析方法 — 2026-05-04
- **类型**：可复现性/工具配置
- **位置**：L183-L192 Perfetto 抓取与 `am_anr` 定位
- **问题**：正文建议在 Perfetto 搜索 `am_anr`，但没有说明 trace config 必须采集 EventLog/logcat 或 `am` atrace。只抓 sched/binder/input/view 等数据源时，Perfetto 中可能没有 `am_anr` 事件。
- **建议**：补最小抓取配置；或说明 fallback：从 bugreport / `logcat -b events` 定位 `am_anr` 时间，再跳回 Perfetto 分析主线程、binder 与调度状态。

## [Task9 Deep Review] 10.6 内存抖动与频繁 GC — 2026-05-04
- **类型**：数据缺失
- **位置**：L80 / L106 / L110 GC 暂停与 LOS stall 量化值
- **问题**：Young GC 暂停 1-3ms、LOS 分配 Stall Time 降低约 15% 都是量化断言，但正文未给设备、ART 版本、刷新率、对象大小、样本数量或 trace/benchmark 来源；官方 memory 文档不能单独支撑这些固定数值。
- **建议**：补 Perfetto/ART log 样本和测试条件；否则改为“毫秒级暂停”“部分场景下降低”，把 1-3ms、15% 放入待验证数据。

## [Task9 Deep Review] 10.7 SQLite/Room 数据库性能优化 — 2026-05-04
- **类型**：源码准确性
- **位置**：L297-L308 EXPLAIN QUERY PLAN 示例与解读
- **问题**：对 `WHERE conversation_id = 42` 命中 `(conversation_id, date)` 索引的查询，SQLite 实际输出通常是 `SEARCH messages USING INDEX idx_msg_conv_date (conversation_id=?)`，不是正文写的 `SCAN messages USING INDEX...`。现代 SQLite 输出也不一定带 `TABLE` 字样。
- **建议**：把示例输出改成可复现的 SEARCH 结果，并说明 SCAN USING INDEX 只是“按索引顺序扫描”，不等同于等值查找。

## [Task9 Deep Review] 10.7 SQLite/Room 数据库性能优化 — 2026-05-04
- **类型**：数据缺失
- **位置**：L245 / L461 批量事务与 SQLCipher 性能数字
- **问题**：“批量插入速度提升 10x-100x”和“SQLCipher 写入降低 5-15%”缺少设备、数据量、page size、WAL/synchronous 配置、加密算法和测试脚本。
- **建议**：补基准测试条件和来源；否则把固定区间改成定性结论，并标为待验证。


## [Task9 Deep Review] 2.12 Window Manager Service 与窗口管理 — 2026-05-04
- **类型**：版本差异/数据支撑
- **位置**：L367-L388 Android 16 Desktop Windowing 与大屏 adaptive behavior
- **问题**：正文写“Android 16 把 connected display desktop windowing 作为正式特性公开 / GA”，但 frontmatter 使用的 `developer.android.com/about/versions/16/features` 页面没有 Desktop Windowing 条目；可核验的官方博客更偏“upcoming desktop windowing and connected displays in Android 16”与桌面体验设计指引。
- **建议**：补官方博客或产品文档作为来源；如果只有 I/O/Blog 口径，避免写成 GA，改成“Android 16 路线中加入 desktop windowing / connected display，具体可用性取决于设备、QPR 和厂商实现”。
- **review 日志**：logs/deep-review/2026-05-04-08-deep-review.md

## [Task9 Deep Review] 8.9 Android 游戏性能与 Game Mode/State API — 2026-05-04
- **类型**：API 边界
- **位置**：L164-L166 / L226-L227 GameManager 示例代码
- **问题**：示例直接使用 `getSystemService(GameManager.class)` 返回值调用 `getGameMode()` / `setGameState()`。GameManager reference 明确要求对返回值做 null check；TV、Auto、ChromeOS 等设备类型可能不提供 GameManager。
- **建议**：示例加 `GameManager gameManager = getSystemService(GameManager.class); if (gameManager == null) return;` 或等价保护，再进入 Game Mode / Game State 调用。
- **review 日志**：logs/deep-review/2026-05-04-08-deep-review.md


## [Task9 Deep Review] 16.4 Android 17 + Kernel 6.12 系统级性能优化 — 2026-05-04
- **类型**：数据缺失/版本边界
- **位置**：L296-L303（MGLRU 量化数据）
- **问题**：`kswapd` CPU -40%、LMK -85%、渲染延迟 -18% 只给了 `lore.kernel.org/all/` 空泛入口，没有 message-id、patch cover letter 或 Google 报告链接；`6.12 默认启用` 也需要区分 mainline Kconfig 与 Android GKI defconfig。
- **建议**：补具体 lore/kernel message-id 或 Google 公开报告；把默认启用口径限定为 `android16-6.12` GKI defconfig（如 `CONFIG_LRU_GEN=y` / `CONFIG_LRU_GEN_ENABLED=y`），避免读者理解成所有 Linux 6.12 mainline 构建默认启用。

## [Task9 Deep Review] 17.3 行业案例 — 2026-05-04
- **类型**：版本差异/API 边界
- **位置**：L154-L160（ADPF Thermal thresholds）
- **问题**：`PowerManager#getThermalHeadroomThresholds()` 在 Android 16/Baklava 公开源码中是 `@FlaggedApi(FLAG_ALLOW_THERMAL_HEADROOM_THRESHOLDS)`；本节适用范围写 Android 12-16，但正文没有给旧版本 fallback 或 feature flag 边界。
- **建议**：补 `Build.VERSION` / API 可用性守卫；Android 12-15 场景使用 `getThermalHeadroom()`、thermal status、同机型实测阈值作为 fallback。

## [Task9 Deep Review] 17.3 行业案例 — 2026-05-04
- **类型**：源码准确性/案例待验证
- **位置**：L198-L200（FileProvider attachInfo 插桩）
- **问题**：正文把抖音 FileProvider 优化写成“在 `attachInfo()` 临时把 `grantUriPermissions` 设为 false，使 `getPathStrategy()` XML 解析被跳过”。当前 AndroidX `FileProvider.attachInfo()` 已不在该路径解析 XML；旧 support-v4 版本可能不同，缺少库版本和字节原文锚点。
- **建议**：补字节原文链接、目标 FileProvider 版本和源码片段；若无法回源，降级为“通过字节码插桩延迟 FileProvider 路径 XML 解析”，不要写死 `grantUriPermissions=false` 的异常链。

## [Task9 Deep Review] 17.3 行业案例 — 2026-05-04
- **类型**：数据缺失/厂商边界
- **位置**：L254-L257（折叠屏多窗口 GPU 压力）
- **问题**：“120Hz 大屏多窗口对系统性能要求是普通场景 2-3 倍”“前台窗口获得更多 GPU 时间片、后台窗口降帧”缺少公开数据或 trace；GPU 时间片/后台降帧也不是 Android 标准公开机制，容易把 OEM 私有策略写成平台事实。
- **建议**：改成可观测口径：SurfaceFlinger layer 数、HWC/GPU 合成比例、FrameTimeline deadline miss、每窗口 `setFrameRate`/实际 present cadence；若保留 2-3 倍或前后台策略，补具体设备/系统版本/trace。

## [Task9 Deep Review] 18.9 Vulkan 原生渲染管线 — 2026-05-04
- **类型**：调试命令/API 边界
- **位置**：L439-L443（Validation Layer 启用命令）
- **问题**：Android 官方 validation layer 文档没有 `debug.vulkan.enable` 属性；该命令大概率无效，容易让读者以为设置成功但 layer 未加载。
- **建议**：删除 `adb shell setprop debug.vulkan.enable 1`；按官方文档保留 `debug.vulkan.layers`，或补充 per-app `settings put global gpu_debug_layers` / `gpu_debug_layer_app` 流程。

## [Task9 Deep Review] 18.9 Vulkan 原生渲染管线 — 2026-05-04
- **类型**：术语准确性
- **位置**：L84（GLES 错误处理）
- **问题**：“GLSE”不是 GLES/OpenGL 常用术语或 API，疑似把 `glGetError` 写错。
- **建议**：改为 `glGetError` 或 “GL error 状态码”，并说明 GLES 错误多为查询式错误状态而非 validation layer 式即时诊断。

## [Task9 Deep Review] 2.12 Window Manager Service 与窗口管理 — 2026-05-04
- **类型**：版本差异/原理链
- **位置**：L484-L490 WindowInsets 扩展节
- **问题**：正文把 Insets 分发概括为“WMS 计算 → relayoutWindow 返回 → ViewRootImpl dispatchApplyWindowInsets”。这能覆盖 relayout 返回路径，但 IME Insets 动画、运行时 InsetsSourceControl/InsetsController 更新不一定每帧触发 relayout，容易让读者把 Insets 动画成本全归到 `relayoutWindow`。
- **建议**：补一句 IME Insets 动画期间还要看 `InsetsController` / `InsetsSourceConsumer` / `ViewRootImpl` 的运行时分发路径，并在 Perfetto 中把 relayout 与 Insets animation 分开计时。


## [Task9 Deep Review] 2.12 Window Manager Service 与窗口管理 — 2026-05-04
- **类型**：版本差异
- **位置**：L171 / L189 StartingWindow 首帧完成信号
- **问题**：正文并列写 `finishDrawing` / `reportDrawFinished`，但没有说明 legacy drawing finish 与 BLAST/sync-seq 路径的版本边界。读者在不同 Android 版本 trace 中只看到其中一个名字时，可能误以为链路缺失。
- **建议**：补一行版本说明：旧路径常见 `finishDrawing`，现代 BLAST/sync 场景更常看 `reportDrawFinished` / sync seq；两者都表示主 Window 首帧完成信号，但后续 starting surface 移除还要看 Shell 与 SurfaceFlinger。


## [Task9 Deep Review] 7.9 感知流畅性：步幅波动与无掉帧卡顿 — 2026-05-04
- **类型**：版本差异/API 边界
- **位置**：L174-L176 `AnimationUtils.lockAnimationClock(...)`
- **问题**：正文使用 `lockAnimationClock(long, long)` 双参数示例，但章节适用范围写 Android 10-17。双参数版本用于 expected presentation time，旧版本只需要核对单参数动画时钟锁定路径；不标版本会让读者在 Android 10-13 源码中找不到同一签名。
- **建议**：在代码块注释中标注“新版本双参数；旧版本单参数但同样存在 `frameTimeNanos / NANOS_PER_MS` 毫秒化路径”，避免把签名差异误判为机制差异。

## [Task9 Deep Review] 5.5 Thermal 管控 — 2026-05-04
- **类型**：源码/资料链接
- **位置**：frontmatter L23、L500、L685（source.android.com/docs/core/thermal）
- **问题**：该官方文档路径返回 404。本轮复核可打开的是 source.android.com/docs/core/power/thermal-mitigation；Sustained Performance Mode 对应 source.android.com/docs/core/power/performance。
- **建议**：替换失效链接，并按“thermal mitigation / performance management”拆分参考资料。

## [Task6 Review] 16.4 Android 17 + Kernel 6.12 系统级性能优化 — 2026-05-04
- **类型**：需确认
- **位置**：Dispatch Queue（DSQ）机制 / 排查要点
- **问题**：正文仍把 `SCX_DSQ_BYPASS` 和 `SCX_EV_REFILL_SLICE_DFL` 放在 android16-6.12 通用口径附近；上轮 Task9 已提示这些符号/计数器在目标分支可能不匹配。
- **建议**：Task9 按 `android16-6.12` 目标分支源码与 sysfs/trace 输出复核；Task2B 按结论保留、删除，或单列后续 mainline / 厂商分支差异。
- **review 日志**：logs/review/2026-05-04-21-review.md

- **类型**：需补充素材
- **位置**：MGLRU 与页面回收优化
- **问题**：`kswapd` CPU -40%、LMK -85%、渲染延迟 -18% 以及“6.12 默认启用”缺具体公开来源、message-id、报告链接或 Android GKI defconfig 锚点。
- **建议**：补 `CONFIG_LRU_GEN` / `CONFIG_LRU_GEN_ENABLED` 与数据来源；补不齐时降级为限定表述。
- **review 日志**：logs/review/2026-05-04-21-review.md

## [Task6 Review] 7.2 卡顿原因体系 — 2026-05-04
- **类型**：需补充素材
- **位置**：WebView 渲染 / 多窗口分屏 / 动画与手势三个扩展小节
- **问题**：三个扩展小节目前仍是整段 `[待补充]` 占位。作为 ready-for-review 章节，正文连续保留占位会影响发布观感。
- **建议**：Task2B 在处理 7.2 既有技术回炉时同步处理：有素材就补成 1-2 段可用内容；没有素材则把扩展标题移到后续规划，不留整段占位。
- **review 日志**：logs/review/2026-05-04-22-review.md

## [Task9 Deep Review] 10.4 低内存对系统性能的影响 — 2026-05-06
- **类型**：Trace 配置/可观测性
- **位置**：L239-L250 TraceConfig `lowmemorykiller/lowmemorykiller`
- **问题**：示例已修正 `atrace_categories: "lmkd"`，但 `lowmemorykiller` ftrace event 在现代 GKI/设备上可能不存在；AOSP atrace memory category 中该事件是 optional，android16-6.12 kernel common 未核到通用 lowmemorykiller trace header。
- **建议**：录制前补 `adb shell ls /sys/kernel/tracing/events/lowmemorykiller` 检查；不存在时依赖 `atrace_categories: "memory"`、logcat/statsd `lowmemorykiller`、`ProcessKilled` 和 lmkd 日志。


## [Task9 Deep Review] 17.1 OEM 性能优化的通用思路 — 2026-05-06
- **类型**：数据缺失
- **位置**：L184-L188 OPPO Trinity Engine 启动提升数据
- **问题**：正文引用“启动速度提升 28%、加载时间缩短 21%”，但只标注为待验证，缺少机型、系统版本、样本范围、测试口径和是否第三方复测。
- **建议**：补 OPPO 原始发布页的测试条件；若没有条件，改成“厂商公开宣称”，不要作为可复现实测结论使用。

## [Task9 Deep Review] 17.1 OEM 性能优化的通用思路 — 2026-05-06
- **类型**：Trace 观察点待补证
- **位置**：L171 USAP Pool 的 Perfetto 识别
- **问题**：正文给出 `usapReceive` vs `forkAndSpecialize` 的 Trace 识别法，但当前源码锚点只覆盖 `ZygoteServer.fillUsapPool()` 与 USAP 支持边界，未给出该 slice 名称来自哪份 trace 或哪处 ATRACE 标记。
- **建议**：补一张启动 trace 或 trace_processor 查询，确认 USAP 命中时的实际 slice / 线程名；否则改成“观察 Zygote/USAP pool socket 与启动路径是否绕过常规 fork”的泛化描述。

## [Task9 Deep Review] 4.7 16KB Page Size 与 Android 性能 — 2026-05-06
- **类型**：源码准确性
- **位置**：L235-L241「kCompatPageSize 常量」
- **问题**：正文把 `kCompatPageSize` 定义位置写成 `linker_phdr_16kib_compat.cpp` 行 48；AOSP main / android-16.0.0_r1 中该常量定义在 `linker/linker_phdr.h:49`，compat cpp 只是引用。
- **建议**：把源码锚点改为 `bionic/linker/linker_phdr.h:49`，`linker_phdr_16kib_compat.cpp` 只保留为使用路径。

## [Task9 Deep Review] 8.4 其他响应速度场景 — 2026-05-06
- **类型**：源码准确性
- **位置**：点击响应 → InputDispatcher 分发延迟
- **问题**：“应用侧端点通常绑定到主线程 Looper”表述偏粗。AOSP 路径是 `ViewRootImpl.WindowInputEventReceiver` / native `InputEventReceiver` 把 InputChannel fd 注册到主线程 Native Looper/epoll。
- **建议**：改成“fd 注册到主线程 Native Looper，事件到达后回调进入 ViewRootImpl 分发”，与 §3.1 的 Input 章节保持一致。

## [Task9 Deep Review] 8.4 其他响应速度场景 — 2026-05-06
- **类型**：原理边界
- **位置**：搜索防抖 → `flatMapLatest` 说明
- **问题**：正文写旧搜索请求“会被自动取消”，但实际取消取决于 `repository.search()` 是否响应协程取消；阻塞式调用或不支持取消的网络层仍可能继续执行。
- **建议**：补一句：只有 suspend/CallAdapter 能把协程取消传递到底层请求时，旧请求才会真正取消；否则还需请求 id 丢弃过期结果。

## [Task9 Deep Review] 19.02 Tencent Matrix — 2026-05-06
- **类型**：源码/API 边界
- **位置**：接入结构 → `pluginListener(...)` 源码锚点
- **问题**：正文按 `Matrix.java` 写 `pluginListener(...)` 是正确的，但 Matrix 官方 README 的 Android 示例仍出现 `builder.patchListener(...)`，会让读者对照 README 时困惑。
- **建议**：补充说明：README 示例是旧 API 名残留，当前 `Matrix.Builder` 以源码为准使用 `pluginListener(...)`。

## [Task9 Deep Review] 19.02 Tencent Matrix — 2026-05-06
- **类型**：版本差异
- **位置**：Trace Canary 的工程边界 → AGP 兼容
- **问题**：正文写了 AGP 8 Transform API 移除风险，但未给 Matrix 官方 release 支持范围；README 当前说明 Gradle 插件主要覆盖 AGP 3.5/4.0/4.1，AGP 7/8 需分支或自迁移验证。
- **建议**：在 AGP 段落补 Matrix 版本/官方支持范围，并把 AGP 8+ 迁移路径限定为“官方新版、内部分支或社区 fork 已完成 instrumentation 迁移”的前提。

## [Task9 Deep Review] 1.9 Package Manager Service 与应用安装性能 — 2026-05-06
- **类型**：一致性
- **位置**：L196-L214
- **问题**：正文说安装过程“六段”，实际编号 1-7。
- **建议**：改为七段或合并 v4/Incremental 校验小节。


## [Task9 Deep Review] 1.9 Package Manager Service 与应用安装性能 — 2026-05-06
- **类型**：源码锚点
- **位置**：L369-L384
- **问题**：ActivityStarter / PackageArchiver 行号来自 mainline 调研，未标目标分支；Android 15/16 release 行号可能不同。
- **建议**：保留类/方法名，删除固定行号或注明 AOSP main commit。


## [Task9 Deep Review] 2.17 Frame Pacing Library 与帧节奏控制 — 2026-05-06
- **类型**：原理补充
- **位置**：L434
- **问题**：`VK_KHR_present_wait` 依赖 `VK_KHR_present_id`，正文把二者并列列出但未说明依赖关系。
- **建议**：补一句 present_wait depends on present_id，减少读者把二者当独立能力的误解。


## [Task9 Deep Review] 2.17 Frame Pacing Library 与帧节奏控制 — 2026-05-06
- **类型**：源码锚点
- **位置**：L416
- **问题**：“后调用覆盖先前 vote”对 Java Surface 语义清楚，但 native `ANativeWindow_setFrameRate()` 的 last-writer-wins 需补 `Surface.cpp` / native window 锚点。
- **建议**：补 native setFrameRate 调用链或收窄为同一 surface 的 frame-rate vote 更新语义。


## [Task9 Deep Review] 12.1 APK 体积优化 — 2026-05-06
- **类型**：版本差异
- **位置**：L489
- **问题**：Baseline Profile 写成 Android 7.0 开始的安装期 AOT 提示机制，容易混淆 Android 7-8.1 的 ProfileInstaller 首次运行安装、Android 9+ Play 安装期 profile、以及现代 AGP baseline profile 工作流。
- **建议**：拆成 Android 7-8.1 / 9+ / 现代 AGP 三段边界。


## [Task9 Deep Review] 12.1 APK 体积优化 — 2026-05-06
- **类型**：数据缺失
- **位置**：L491
- **问题**：“OAT/VDEX 新增磁盘占用比 DEX 再大 10%-30%”缺测试条件、样本包、ABI、编译 filter 和 Android 版本。
- **建议**：补实测表或改为定性描述；保留数字需给 baseline。


## [Task9 Deep Review] 13.1 Perfetto 简介与演进 — 2026-05-06
- **类型**：版本差异
- **位置**：L413、L417
- **问题**：核心 `traced`/`traced_probes` 已明确不是独立 APEX，但“Android 12+ 部分设备通过 Mainline 机制提供更新”仍偏模糊且带 `[待验证]`。
- **建议**：拆开 core tracing platform binary 与 `com.android.profiling` APEX；不要把 OEM/Mainline 更新口径泛化到核心 tracing 服务。


## [Task9 Deep Review] 13.1 Perfetto 简介与演进 — 2026-05-06
- **类型**：架构口径
- **位置**：L169-L172
- **问题**：atrace 被列为与 ftrace 平级数据源；Perfetto 配置里 atrace category 实际通过 `linux.ftrace` 的 `ftrace_config.atrace_categories` 采集。
- **建议**：把 atrace 改为 ftrace data source 下的用户态标注类别。


## [Task9 Deep Review] 13.1 Perfetto 简介与演进 — 2026-05-06
- **类型**：工具描述
- **位置**：L384
- **问题**：`tracebox` 被称为“单文件可执行程序”，实际是自包含 Python 脚本。
- **建议**：改为“单文件 Python 工具/自包含脚本”。

## [Task9 Deep Review] 2.17 Frame Pacing Library 与帧节奏控制 — 2026-05-06
- **类型**：版本差异/扩展依赖
- **位置**：L458 VK_KHR_present_id / VK_KHR_present_wait 待验证段
- **问题**：正文已把 present_id 从 Swappy 当前实现中剥离出来，但待验证句仍把 VK_KHR_present_id / VK_KHR_present_wait 并列写成可选能力，未说明 present_wait 对 present_id 的依赖和独立 feature 查询边界。
- **建议**：补一句：VK_KHR_present_wait depends on VK_KHR_present_id，设备侧还需查询/启用 VkPhysicalDevicePresentWaitFeaturesKHR；这仍只是未来接入方向，不代表当前 Swappy 使用。

## [Task9 Deep Review] 19.0 第 19 章：APM 工具与性能监控生态 — 2026-05-06
- **类型**：交叉引用一致性
- **位置**：L141-L142 本章内容 / src/SUMMARY.md L254-L255 / 19.21 与 19.22 实际章节
- **问题**：README 与 SUMMARY 已把 19.21/19.22 写成 Speedometer、CPDT、PCMark Storage 口径，但 19.21 H1 仍是“Benchmark 应用（Geekbench、安兔兔、3DMark、PCMark、Vellamo）”，19.22 frontmatter 与 H1 仍是“存储 Benchmark（AndroBench、A1 SD Bench）”。目录、章节标题和实际内容入口不一致。
- **建议**：统一 19.21/19.22 的 frontmatter title、H1、SUMMARY 和 README；若 19.22 仍保留历史存储工具为主，应把 README/SUMMARY 改回历史口径，或先完成 CPDT/PCMark Storage 正文补强后再改标题。


## [Task9 Deep Review] 7.10 图片加载与 Bitmap 性能优化 — 2026-05-06
- **类型**：数据缺失
- **位置**：L231/L279 Hardware Bitmap 省去 4-8ms upload
- **问题**：正文给出“1080p RGBA 首帧 upload 4-8ms”的固定数值，但未绑定设备、GPU、图片格式、trace slice 或 benchmark。
- **建议**：补目标设备 Perfetto/benchmark 数据，或改为 `[待验证]`/经验区间并注明测试条件。

## [Task9 Deep Review] 7.10 图片加载与 Bitmap 性能优化 — 2026-05-06
- **类型**：数据缺失
- **位置**：L547 WebP 有损替代 JPEG 体积小 25-35%
- **问题**：检查清单给出固定压缩收益区间，但正文没有测试样本、质量指标或来源。
- **建议**：补来源/实测表；若无固定样本，改成按业务图片集和质量目标实测。


## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-05-06
- **类型**：源码准确性
- **位置**：L248 Zygote TimingsTraceLog slice 列表
- **问题**：正文列出 `PreloadSharedLibraries`、`PreloadOpenGL` 作为 android-16.0.0_r1 常见 slice；复核 `ZygoteInit.java`，该版本核心 trace 名称包括 `BeginPreload`、`PreloadClasses`、`CacheNonBootClasspathClassLoaders`、`PreloadResources`、`PreloadAppProcessHALs` 等，未见这两个 slice。
- **建议**：按 android-16.0.0_r1 实际 slice 名称改写，并把旧版本/旧资料中的名称单独标注为历史口径。

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-05-06
- **类型**：数据缺失
- **位置**：L320-L332 Pixel 8 / Android 16 参考基线表
- **问题**：表格给出 Pixel 8、Android 16、典型冷启动分段耗时和占比，但来源说明是“公开 bootstat 输出和 AOSP 默认配置的估算值”，没有原始 bootstat、Perfetto、dmesg、测试条件或样本次数。
- **建议**：补 Pixel 8 实测 `bootstat -l` / Perfetto / dmesg 截图和测试条件；如果暂时没有一手数据，把表格改成非机型化的阶段成本示意，避免给出具体秒数和占比。

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-05-06
- **类型**：版本差异
- **位置**：L399-L411 dm-verity / AVB 段
- **问题**：正文写“Android 7.0 起 dm-verity 默认启用”，但官方 Verified Boot 文档给出的演进是 Android 4.4 支持 Verified Boot + dm-verity，Android 7.0 开始严格强制 Verified Boot 并加入 FEC，Android 8.0+ 是 AVB 参考实现。另，“每次读取系统分区数据块都验证 hash”未区分页缓存/块缓存后的重复读取成本。
- **建议**：把版本边界改成 4.4 支持、7.0 严格强制、8.0+ AVB；启动耗时影响写成“块首次从 verified block device 读取时需要 hash tree 校验，缓存命中不会重复产生同等校验成本”。

## [Task9 Deep Review] 7.10 图片加载与 Bitmap 性能优化 — 2026-05-06
- **类型**：数据与案例支撑
- **位置**：L340 AVIF 段引用 HEIC 降本案例
- **问题**：正文在 AVIF 小节引用“抖音 JPEG 转 HEIC 带宽成本降低超过 80%”作为相邻案例。HEIC 与 AVIF 都是高压缩静态图格式，但编码工具链、硬件解码覆盖和兼容性不同，不能直接作为 AVIF 体积/解码收益证据。
- **建议**：把该案例明确收窄为 HEIC 工程案例，或替换成 AVIF 的同源 benchmark / 业务图片集实测数据。

## [Task9 Deep Review] 9.1 ANR 设计思想 — 2026-05-06 — L401-L405 各版本 ANR 机制演进
- **类型**：版本差异
- **位置**：L401-L405 各版本 ANR 机制演进
- **问题**：正文写“ANR 机制自 Android 2.3 引入以来”。AOSP android-1.6_r1 的 ActivityManagerService.java 已有 appNotResponding 路径，2.3 不能写成 ANR 机制起点。
- **建议**：改为“ANR 机制早期版本已存在，Android 8+ 本章只追踪诊断与触发条件变化”；若要保留 2.3，必须指向某个具体实现变化。
- **review 日志**：logs/deep-review/2026-05-06-10-deep-review.md

## [Task9 Deep Review] 9.1 ANR 设计思想 — 2026-05-06 — L300-L302 Watchdog 检测机制
- **类型**：源码准确性
- **位置**：L300-L302 Watchdog 检测机制
- **问题**：正文写 Watchdog 默认每 60 秒发送一次心跳。AOSP android-14 Watchdog.DEFAULT_TIMEOUT=60s，但 run() 中 checkIntervalMillis=watchdogTimeoutMillis/2；默认约 30s 半程检查/WAITED_HALF dump，满 60s 才进入 OVERDUE/重启决策。
- **建议**：改为“默认 timeout 60s；Watchdog 按半程约 30s 做中间检查，满 60s 未完成才判定超时”。
- **review 日志**：logs/deep-review/2026-05-06-10-deep-review.md

## [Task9 Deep Review] 9.6 Notification 性能与 ANR — 2026-05-06 — L501 标准模板 RemoteViews 口径
- **类型**：源码准确性
- **位置**：L501 标准通知模板性能误区
- **问题**：正文写标准通知模板“不需要通用的 RemoteViews inflate 流程”。AOSP/SystemUI 仍会生成并 apply/reapply RemoteViews，只是系统模板布局稳定、缓存/复用和 SystemUI 专用处理更可控。
- **建议**：改成“标准模板通常布局更稳定、SystemUI 适配更成熟，可减少自定义 RemoteViews 带来的布局复杂度和图片绑定风险”，不要写成完全不走 RemoteViews。
- **review 日志**：logs/deep-review/2026-05-06-11-deep-review.md

## [Task9 Deep Review] 17.2 SoC 平台差异 — 2026-05-06 — L106-L112/L169 cpufreq policy 与实机数据
- **类型**：数据缺失
- **位置**：L106-L112、L169 CPU Frequency Track / “两个频率档位”
- **问题**：正文把 Oryon “双集群”写成“只有两个频率档位”，并把 Dimensity 全大核写成“三个频率档位分布紧凑”。Perfetto 中更准确的观察对象是 cpufreq policy/cluster 轨道；每个 policy 内仍有多个频点。当前也缺 8 Elite 与 Dimensity 9400 同场景 sched/cpufreq trace。
- **建议**：改成“两组/三组 cpufreq policy 或 cluster 轨道，每组包含多个频点”；保留迁移次数/频率曲线判断时补同场景 Perfetto 数据，否则标 [待验证]。
- **review 日志**：logs/deep-review/2026-05-06-11-deep-review.md

## [Task9 Deep Review] 7.10 图片加载与 Bitmap 性能优化 — 2026-05-06
- **类型**：源码准确性/版本边界
- **位置**：L342 AVIF 硬件能力 fallback 描述
- **问题**：正文把系统软件解码 fallback 具体写成 `libdav1d`。AOSP android-16.0.0_r1 的 Skia Android target 使用 `SkCrabbyAvifCodec.cpp`，依赖 `libcrabbyavif_ffi` / `libheif` / `libmediandk`；同 tag 下没有 `platform/external/dav1d`。`libdav1d` 不能作为平台默认口径。
- **建议**：改成“退回系统软件 AVIF 解码路径”，或按具体版本写 `SkCrabbyAvifCodec` / `libcrabbyavif_ffi`；除非引用厂商或 App 自带解码库，不指定 `libdav1d`。

## [Task9 Deep Review] 7.10 图片加载与 Bitmap 性能优化 — 2026-05-06
- **类型**：Trace 观察条件
- **位置**：L490 Perfetto “看调用栈”方法
- **问题**：默认 `sched` / FrameTimeline / atrace 抓取通常不会自动带 Java/Native 方法调用栈，读者不能直接从主线程 CPU slice 展开到 `BitmapFactory.nativeDecode*`。
- **建议**：补充采集前提：需要开启 callstack sampling、simpleperf/Perfetto CPU profiler、method tracing，或在业务解码包装层加自定义 Trace；默认调度 trace 只能定位线程长时间运行。

## [Task6 Review] 9.6 Notification 性能与 ANR — 2026-05-06
- **类型**：需确认 / 技术问题残留
- **位置**：版本演进表 Android 14 行；图片通知成本阶梯；常见问题「Icon 构造方式对性能没影响」
- **问题**：Task9 2026-05-06 已判定 RemoteViews Measure Cache/Action-diff 与 Icon.createWithBitmap/HardwareBuffer/Binder buffer 口径不成立。Task2B 标记 completed 后，正文仍保留这些表述。Task6 不裁决技术真伪，仅按 Task9 已有结论重开问题单。
- **建议**：删除 Measure Cache / Action-diff 版本事实；按资源 ID / URI / Bitmap 三类路径重写图片通知成本模型，避免写成通知图片默认 HardwareBuffer 零拷贝或像素整体进入 Binder buffer。
- **review 日志**：logs/review/2026-05-06-13-review.md

## [Task9 Deep Review] 13.7 Perfetto 的高级用法 — 2026-05-06 — L178-L192 cold_start_metric_output
- **类型**：Metric 输出边界
- **位置**：L178-L192 cold_start_metric_output
- **问题**：输出 view 外层使用 FROM cold_start_phases LIMIT 1。当 cold_start_phases 为空时，整个 metric 输出 0 行；官方 trace-based metrics walkthrough 的惯用写法是无外层 FROM 的 SELECT TopMetric(...)，这样 repeated 字段为空时仍能输出 proto。
- **建议**：改成无 FROM 的 SELECT ColdStartMetric(...) AS cold_start_metric；内部 RepeatedField 子查询继续 FROM cold_start_phases。
- **review 日志**：logs/deep-review/2026-05-06-13-deep-review.md

## [Task9 Deep Review] 13.7 Perfetto 的高级用法 — 2026-05-06 — L678-L698 packet->set_render_pass_info()
- **类型**：Custom DataSource 示例可执行性
- **位置**：L678-L698 packet->set_render_pass_info()
- **问题**：packet->set_render_pass_info() 不是 Perfetto SDK 默认 TracePacket API；它要求自定义 proto 扩展、生成代码并让 Trace Processor 侧能导入/解析。正文虽提到“定义自定义 proto”，但最小骨架没有交代 TracePacket 字段扩展和解析注册，读者复制会编译失败。
- **建议**：要么改用官方 set_for_testing() 最小示例；要么补全自定义 TracePacket proto 扩展、生成代码、Trace Processor 解析/SQL 查询边界。
- **review 日志**：logs/deep-review/2026-05-06-13-deep-review.md

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-05-06
- **类型**：数据口径/源码准确性
- **位置**：L147 Bootloader / GBL / bootstat 段
- **问题**：正文把 `boottime.bootloader.*` 写成“系列属性”。复核 `system/core/bootstat/bootstat.cpp`：bootloader 通过 `ro.boot.boottime` 提供 `stage:time` 列表，bootstat 再记录 `boottime.bootloader.<stage>` / `boottime.bootloader.total` boot event；这些不是直接可 `getprop boottime.bootloader.*` 的系统属性。
- **建议**：改成“bootloader 上报 `ro.boot.boottime`；bootstat 展开为 `boottime.bootloader.*` 事件/指标”。GBL 只写成 Android 16 起推荐的 boot firmware 标准化方向，不要暗示这些 bootstat event 是 GBL 才引入或天然跨厂商可比。

## [Task6 Review] 11.5 Wakelock 机制与功耗分析 — 2026-05-06
- **类型**：需确认 / 需重写
- **位置**：`IPowerStats HAL` 与 `Perfetto 端到端观测`；参考资料之后的 `AIW-源码调研-2026-05-06` 段落
- **问题**：Task6 复审发现正文仍把 `android.power_rails` 写成 Perfetto 数据源口径，和前轮 Task9 关于 `android.power` + `collect_power_rails` 的结论不一致；同时新增 ADPF 非游戏场景源码调研被追加在参考资料之后，没有融入正文，并且 `setPreferredPowerEfficiency` / `setPreferPowerEfficiency` 命名不一致。
- **建议**：Task2B 先按 Task9 结论统一 Perfetto power rail 口径；再判断 ADPF 源码调研是否值得整合进前文 ADPF/PowerMonitor 小节，API 命名与 `GPU_LOAD_UP` 等常量交 Task9 复核。
- **review 日志**：logs/review/2026-05-06-17-review.md


## [Task9 Deep Review] 9.6 Notification 性能与 ANR — 2026-05-06
- **类型**：源码边界 / RemoteViews reapply
- **位置**：L226 RemoteViews 的 reapply 机制
- **问题**：`canReapplyRemoteView()` 的条件只写了 package 和 layoutId 相同，遗漏 `!oldView.hasFlags(RemoteViews.FLAG_REAPPLY_DISALLOWED)`。android-16 SystemUI `NotificationContentInflater.canReapplyRemoteView()` 还会检查旧 RemoteViews 是否禁止 reapply。
- **建议**：补一句边界：package/layoutId 稳定只是必要条件；旧 `RemoteViews` 带 `FLAG_REAPPLY_DISALLOWED` 时仍会重新 apply/inflate，排查时要以 SystemUI 实际分支为准。

## [Task9 Deep Review] 9.6 Notification 性能与 ANR — 2026-05-06
- **类型**：源码边界 / RankingMap 可见性过滤
- **位置**：L297 大量通知场景下的 RankingMap 重建
- **问题**：正文写 NMS 对“所有活跃通知”生成完整 `RankingMap` 并分发给所有监听器。android-16 `makeRankingUpdateLocked(info)` 会按 listener 可见性过滤：lockdown、listener filter、敏感内容可见性都会影响进入 `NotificationRankingUpdate` 的记录。
- **建议**：改成“对该 listener 可见的活跃通知集合生成 RankingMap”；性能判断仍看可见通知数和 listener 数，但不要写成全局所有活跃通知无条件下发。

## [Task9 Deep Review] 18.10 SurfaceControl API 深入 — 2026-05-06
- **类型**：交叉引用
- **位置**：L666-L668 底部交叉引用
- **问题**：`13-buffer-queue.md`、`06-surfaceflinger.md`、`16-sync-fence.md` 按当前文件所在目录解析均不存在；实际章节在 `src/part1-fundamentals/ch02-rendering/` 下。
- **建议**：改成正确相对路径（例如 `../../part1-fundamentals/ch02-rendering/13-buffer-queue.md` 等），或使用项目统一章节链接格式。

## [Task6 Review] 11.1 Android 功耗模型 — 2026-05-06
- **类型**：需确认
- **位置**：PowerMonitor API（Android 15+）段落
- **问题**：上一轮 Task9 已提示 PowerMonitor API 调用对象存在风险；正文仍写“App 通过 PowerManager 获取 PowerMonitor 实例”。Task6 已把验证标注降级为待验证，但不裁决 API 入口真伪。
- **建议**：Task9 对照 Android 15/API 35 SDK 与官方文档确认 PowerMonitor 获取入口；Task2B 按确认结果修正文案和验证标注。
- **review 日志**：logs/review/2026-05-06-20-review.md

## [Task6 Review] 11.1 Android 功耗模型 — 2026-05-06
- **类型**：需补充素材
- **位置**：与其他机制的关系 / 版本演进：PAS、ADPF 与 ODPM 动态反馈
- **问题**：PAS 通过 Power HAL AIDL 订阅 ODPM 修正 EM、ADPF 利用 ODPM 预防性降频等表述仍缺公开 AOSP/官方文档逐行支撑。正文已有待验证标注，版本表也已补待验证提示，但仍需技术复核。
- **建议**：补 CDD/source.android.com/AOSP 公开锚点；无法确认时降级表述，避免把推测写成确定机制。
- **review 日志**：logs/review/2026-05-06-20-review.md

## [Task6 Review] 17.2 SoC 平台差异 — 2026-05-06
- **类型**：需确认
- **位置**：主流 SoC 平台概览：高通 Snapdragon 段
- **问题**：正文仍写 Oryon 核心“与苹果 M 系列同源”，与 Task9 11:39 已指出的风险项重叠；后文已改成“Nuvia 背景、创始成员有 Apple CPU 经历”，两处口径不一致。
- **建议**：Task9/Task2B 统一为更稳妥口径：开发团队背景来自 Nuvia，创始成员有 Apple CPU 经历；删除或标注“同源”表述，除非补到 Qualcomm 白皮书或权威拆解锚点。
- **review 日志**：logs/review/2026-05-06-20-review.md

## [Task9 Deep Review] 11.1 Android 功耗模型 — 2026-05-06
- **类型**：交叉引用/数据缺失
- **位置**：参考资料与 Perfetto + ODPM 配置示例
- **问题**：参考链接 `https://perfetto.dev/docs/data-sources/power` 当前返回 404；正文的 `android.hardware.power.stats` Perfetto 配置仍标 `[待验证]`，缺少可访问的一手文档或 AOSP proto/source 锚点支撑。
- **建议**：替换为可访问的 Perfetto power rails / Android power data source 文档、Perfetto proto 或 AOSP 数据源实现链接；配置示例需绑定 Android/Perfetto 版本并验证字段名。

## [Task9 Deep Review] 11.3 系统级功耗优化 — 2026-05-06
- **类型**：数据缺失 / OEM 行为口径
- **位置**：L371-L405 厂商级功耗管理
- **问题**：MIUI/HyperOS 默认自启动、`com.miui.powerkeeper` “通常 10 分钟左右”冻结、OPPO/vivo 默认自启动限制、以及“电池消耗报告差 3-5 倍”等断言缺少机型、ROM 版本、设置项截图、公开来源或本地 Trace/功耗实验条件。`dontkillmyapp.com` 可作为现象入口，但不足以单独支撑具体数值和默认策略。
- **建议**：为每个厂商策略绑定 ROM 版本与证据来源；没有来源的时间/倍数改成待验证或删除。若要保留性能分析结论，补 Pixel 对照机与至少 1 台国产 ROM 的 WorkManager/Alarm/Trace 案例。
- **review 日志**：logs/deep-review/2026-05-06-22-deep-review.md

## [Task9 Deep Review] 17.2 SoC 平台差异 — 2026-05-07 — Perfetto PMU 数据源口径
- **类型**：数据缺失/工具口径
- **位置**：L300 ARM Streamline 与 Perfetto PMU 对比
- **问题**：[P2] 正文写 Perfetto 通过 `linux.ftrace` 的 `pmu` 事件部分获取 PMU 指标。Perfetto 的 PMU 采样/计数通常走 perf_event / linux.perf 数据源；ftrace 主要用于 tracepoint/function/systrace 类事件。
- **建议**：改成“Perfetto 需配置 perf_event/linux.perf 或设备支持的 perf/PMU 数据源；ftrace 只覆盖调度、freq、thermal 等 trace events”。
- **review 日志**：logs/deep-review/2026-05-07-00-deep-review.md

## [Task9 Deep Review] 10.5 案例集 — 2026-05-07
- **类型**：版本差异/数据支撑
- **位置**：L293 ProfilingManager / ProfilingTrigger
- **问题**：正文写 `ProfilingTrigger` 目前只暴露 `TRIGGER_TYPE_APP_FULLY_DRAWN` 和 `TRIGGER_TYPE_ANR`。Android API 37 文档已新增 OOM、Cold Start、Kill、App Request Running Trace 等触发类型；但这些仍不是“内存突增阈值”触发，OOM 触发也是事后 Java heap dump。
- **建议**：把该段限定为 Android 15/16 口径，并补 Android 17/API 37 更新：OOM trigger 可辅助事后取证，但不能替代 MemoryThrashing 这类前置阈值探针；业务仍需自行判断内存突增。



## [Task9 Deep Review] 16.4 Android 17 + Kernel 6.12 系统级性能优化 — 2026-05-07 — Perfetto dm-verity 观察口径
- **类型**：工具口径/数据缺失
- **位置**：L237/L346 dm-crypt/dm-verity track
- **问题**：[P2] 正文写 Perfetto 中看 `dm-crypt/dm-verity track` 或“dm-verity track：哈希验证耗时”。复核 `android16-6.12/drivers/md/dm-verity-target.c` 未见专用 `TRACE_EVENT`；标准 Perfetto/Ftrace 更稳定的观察面是 block tracepoint、CPU scheduling、相关 kworker/crypto CPU slice，或在工程环境中显式打开 function/kprobe/dynamic ftrace。把它写成固定 track 容易误导读者到 UI 里找不存在的数据轨道。
- **建议**：改成“dm-verity 相关耗时需通过 block I/O 延迟、CPU/crypto 热点和可选动态探针间接定位；默认 Perfetto 不保证存在专用 dm-verity track”。
- **review 日志**：logs/deep-review/2026-05-07-02-deep-review.md

## [Task9 Deep Review] 18.3 Android View 软件渲染路径 — 2026-05-07
- **类型**：数据缺失/性能口径
- **位置**：L107-L109 lockCanvas <1ms 与 16KB Page 推导
- **问题**：`lockCanvas` 已被正文写成会受 `dequeueBuffer()` / release fence / BufferQueue 背压影响，但后文又说“正常 <1ms，因为只是内存映射”；16KB Page “Page Fault 数减少约 75%、首帧映射开销降低”也缺实测。
- **建议**：把 `<1ms` 和 75% 页表推导标成示例/理论边界；补 Perfetto slice、page-fault/minflt、分辨率、buffer 格式和 4KB/16KB A/B 条件后再给数字。
- **review 日志**：logs/deep-review/2026-05-07-05-deep-review.md

## [Task9 Deep Review] 18.3 Android View 软件渲染路径 — 2026-05-07
- **类型**：交叉引用
- **位置**：L258-L259 BufferQueue / 图形 API 链接
- **问题**：`13-buffer-queue.md`、`14-graphics-api-evolution.md` 按当前 ch18 目录解析不存在。
- **建议**：改为 `../../part1-fundamentals/ch02-rendering/13-buffer-queue.md` 与 `../../part1-fundamentals/ch02-rendering/14-graphics-api-evolution.md`，或使用项目统一章节链接。
- **review 日志**：logs/deep-review/2026-05-07-05-deep-review.md

## [Task9 Deep Review] 18.5 Android View 多窗口链路 — 2026-05-07
- **类型**：源码边界
- **位置**：L58-L61 Dialog / PopupWindow 是否独立 Window
- **问题**：正文写 Dialog / PopupWindow “不是独立 Window（某些实现中）”。android-16 `Dialog.java` 构造 `PhoneWindow` 并在 `show()` 中 `mWindowManager.addView(mDecor,l)`；`PopupWindow.java` 也通过 `mWindowManager.addView(decorView,p)` 挂窗。
- **建议**：改成“Dialog/PopupWindow 会创建独立 ViewRoot/WindowManager entry，通常会有独立 Surface；具体 Surface/Layer 行为以窗口类型、硬件加速和平台版本为准”。
- **review 日志**：logs/deep-review/2026-05-07-05-deep-review.md

## [Task9 Deep Review] 18.5 Android View 多窗口链路 — 2026-05-07
- **类型**：交叉引用
- **位置**：L316-L317 图形 API / SurfaceFlinger 链接
- **问题**：`../../part1-foundation/ch02-graphics-foundation/` 路径不存在；实际目录为 `src/part1-fundamentals/ch02-rendering/`。且 SurfaceFlinger 实际是 2.6 `06-surfaceflinger.md`，不是 2.5。
- **建议**：改为 `../../part1-fundamentals/ch02-rendering/14-graphics-api-evolution.md` 和 `../../part1-fundamentals/ch02-rendering/06-surfaceflinger.md`。
- **review 日志**：logs/deep-review/2026-05-07-05-deep-review.md

## [Task9 Deep Review] 11.4 案例集 — 2026-05-07
- **类型**：交叉引用错误
- **位置**：参考资料 Android Vitals: Excessive Wakeups
- **问题**：链接 `https://developer.android.com/topic/performance/vitals/wakeups` 当前返回 404。
- **建议**：改为官方当前路径 `https://developer.android.com/topic/performance/vitals/wakeup`。


## [Task9 Deep Review] 17.2 SoC 平台差异 — 2026-05-07
- **类型**：工具口径/数据缺失
- **位置**：L300 ARM PMU 与 Perfetto 数据源
- **问题**：正文写 PMU 指标需要配置 `linux.ftrace` 的 `pmu` 事件；Perfetto 配置 proto 中 perf_event 采样/计数对应 data source name `linux.perf` 和 `perf_event_config`。
- **建议**：改成“Perfetto 需配置 `linux.perf` / `perf_event_config`（或设备支持的 perf/PMU 数据源）；ftrace 只覆盖调度、freq、thermal 等 trace events”。

## [Task6 Review] 7.11 WebView 渲染性能与优化 — 2026-05-07
- **类型**：需重写
- **位置**：“常见问题与误区”之后的“WebView Renderer 进程崩溃恢复”“WebView 渲染管线与 Perfetto 追踪”
- **问题**：两节内容技术密度高，但现在放在常见误区之后，读感像把 AIW 源码调研材料追加到正文尾部；“Perfetto 分析”已经在前文出现一次，后文又以更底层口径重开一节，发布稿收束顺序被打断。
- **建议**：保留现有技术内容，不做技术裁决；请 Task2B 做结构整合：Renderer 崩溃恢复并入多进程/版本演进或常见误区之前；WebView tracing API 与渲染管线内容并入“WebView 在 Perfetto 中的分析”；“常见问题与误区”与“参考资料”放回全文收束位置。
- **review 日志**：logs/review/2026-05-07-08-review.md

## [Task9 Deep Review] 1.7 ART 编译管线与 dex2oat 优化 — 2026-05-07 — AutoFDO 量化数字口径
- **类型**：数据缺失/版本口径
- **位置**：L371-L381 AutoFDO 在 Pixel 设备上的量化效果
- **问题**：当前数字（冷启动 3.0%-4.3%、Binder-rpc 19.5%-21.7%、binder-addints 12.3%-37.7%、HwBinder 11.7%-20%、开机 2%）混用了不同 profile/分支口径。AOSP `android16-6.12/gki/aarch64/afdo/README.md` 当前 6.12.69 profile / Pixel 8 口径为 Boot 1.3%、Cold App launch 4.8%、Binder-rpc 20.7%、Binder-addints 17.0%、Hwbinder 26.4%；`android-mainline` 汇总口径则是 Pixel 6 上 Boot 2-3%、Cold App launch 3-4%、Binder-rpc 8-9%、Binder-addints 12-25%、Hwbinder 12-18%。
- **建议**：固定一个证据口径：要么用 android16-6.12 当前 Pixel 8 / 6.12.69 profile 数字，要么用 android-mainline Pixel 6 汇总范围；不要把不同 profile 日期、设备和分支的数字合并成一组。
- **review 日志**：logs/deep-review/2026-05-07-09-deep-review.md

## [Task9 Deep Review] 7.11 WebView 渲染性能与优化 — 2026-05-07 — render_process_gone Trace 事件
- **类型**：Trace 锚点待验证
- **位置**：L638 Renderer 进程崩溃在 Perfetto 中的表现
- **问题**：正文写 `render_process_gone` 事件会出现在 `android_webview.timeline` 分类下。当前可核验的 Chromium `aw_browser_terminator.cc` / `AwContents.java` 路径能确认 Java 回调与 UMA histogram（`Android.WebView.OnRenderProcessGoneResult2`），但本轮未在这些源码锚点中确认稳定的 `android_webview.timeline` / `render_process_gone` Trace 事件名。
- **建议**：补真实 trace 样例、Chromium trace category 定义或 Perfetto 文档锚点；补不到时改为“通过 renderer 进程结束、`onRenderProcessGone()` 回调、logcat/UMA 线索联合判断”，不要写成稳定 Perfetto 事件。
- **review 日志**：logs/deep-review/2026-05-07-09-deep-review.md


## [Task9 Deep Review] 2.7 Hardware Layer — 2026-05-07
- **类型**：版本差异/数据缺失
- **位置**：L315、L350 Compose 1.10 graphicsLayer 池化
- **问题**：正文把 “Compose 1.10 离屏缓冲池化、LazyLayout item 离开后纹理不销毁并复用”写成确定性版本变化，但正文没有 androidx 源码、release note、commit 或 benchmark 锚点；公开 Compose UI 1.10 release notes 能看到 LayerOutsets 等 graphicsLayer 变更，未能直接支撑该池化描述。
- **建议**：补 androidx 具体 commit/类名/函数与实测指标；找不到证据时从版本表删除，正文改为 [待验证] 研究方向。

## [Task9 Deep Review] 2.7 Hardware Layer — 2026-05-07
- **类型**：数据缺失
- **位置**：L179-L181 16KB 页与 GPU layer 内存
- **问题**：正文已经加了 [待验证]，但仍保留“GPU 显存分配的最小对齐单元提升”这一机制判断；缺 memtrack/gralloc/DMA-BUF/stride 数据，无法判断 16KB page size 对具体 GPU layer texture 的分配影响。
- **建议**：补一组同设备 4KB/16KB 或同 SoC 不同 page size 的 layer 尺寸矩阵，至少包含理论 bytes、stride、memtrack GPU heap、dumpsys meminfo graphics/memtrack 口径；否则改成更弱的风险提示。

## [Task9 Deep Review] 2.7 Hardware Layer — 2026-05-07
- **类型**：原理链边界
- **位置**：L84、L148、L207-L235 属性动画收益判断
- **问题**：正文多处把 Hardware Layer 收益概括为减少“反复重录 DisplayList”，并写“不修改内容时几乎一定能提升性能”。现代 HWUI/RenderNode 的 translation/scale/rotation/alpha 属性动画本身也可能只更新 RenderNode 属性，不必每帧重录 DisplayList；手动 layer 的收益主要来自避免重复光栅化/处理重叠 alpha/offscreen 语义，不应泛化成 DisplayList 重录或必然收益。
- **建议**：补版本/动画类型边界：区分 ViewPropertyAnimator/RenderNode property、普通 invalidate、复杂 alpha overlap/offscreen；把“几乎一定”改成“需用 trace 验证 buildLayer 首帧成本、后续 raster/flush 是否下降”。

## [Task9 Deep Review] 13.7 Perfetto 的高级用法 — 2026-05-07 — L344-L361 BatchTraceProcessor query_and_flatten
- **类型**：Python API 边界
- **位置**：L344-L361 `BatchTraceProcessor.query_and_flatten()` 示例说明
- **问题**：正文写 `query_and_flatten` 的结果“带有一列标识来源 Trace”。复核官方 Batch Trace Processor 文档和 `perfetto` Python 包 0.16.0 源码：只有 URI resolver / custom resolver 提供 metadata 时，flatten 后才会追加来源列；正文示例传入的是普通文件路径列表，默认 metadata 为空，不保证有来源 Trace 列。
- **建议**：改成条件描述：`query_and_flatten` 会把多条 trace 的结果拼成一个 DataFrame；若通过 resolver 提供 `_path` / build id 等 metadata，结果会追加这些来源列。需要稳定来源列时，示例应展示 resolver 或显式维护 trace id。
- **review 日志**：logs/deep-review/2026-05-07-13-deep-review.md

## [Task9 Deep Review] 13.7 Perfetto 的高级用法 — 2026-05-07 — frontmatter source visualization/macros
- **类型**：资料链接准确性
- **位置**：frontmatter L18-L19 `https://perfetto.dev/docs/visualization/macros`
- **问题**：该 URL 当前返回 404；Perfetto 官方“Commands and Macros”文档路径是 `https://perfetto.dev/docs/visualization/ui-automation`，Extension Server 文档路径是 `https://perfetto.dev/docs/visualization/extension-servers`。
- **建议**：把 source 链接改成 `ui-automation`；如果正文继续讨论团队共享宏，再补 `extension-servers` 作为第二个来源。
- **review 日志**：logs/deep-review/2026-05-07-13-deep-review.md

## [Task9 Deep Review] 2.1 Android 渲染架构全景 — 2026-05-07
- **类型**：数据缺失/Vulkan 性能边界
- **位置**：L547-L549 Vulkan 后端性能描述
- **问题**：[P2] “OpenGL ES 状态检查可能占数毫秒帧时间”“Vulkan 多线程能力可以更好利用 HWUI 架构”缺少设备、trace 或 benchmark 支撑；HWUI 是否实际并行构建 Vulkan command buffer 也没有源码锚点。
- **建议**：保留 backend 选择逻辑，但把性能判断改成有条件表述；补 Skia/HWUI Vulkan trace、CPU submit 耗时对比，或删除“数毫秒”和“更好利用”这类量化/因果断言。
- **review 日志**：logs/deep-review/2026-05-07-15-deep-review.md

## [Task9 Deep Review] 2.7 Hardware Layer — 2026-05-07
- **类型**：源码准确性/后端边界
- **位置**：L327 RenderEffect 与 FBO 描述
- **问题**：[P2] “二者底层都依赖 FBO”是 OpenGL 术语；HWUI 也可能走 SkiaVulkanPipeline，RenderEffect/ImageFilter 应描述为 backend-dependent offscreen render target/layer。当前还只写 `SkiaOpenGLPipeline::draw()`，与前文 OpenGL/Vulkan 双后端不一致。
- **建议**：改成“离屏 render target / layer surface”，并分别标注 OpenGL 下可能对应 FBO，Vulkan 下对应 Skia/Vulkan render target；源码锚点保留 RenderProperties/RenderNodeDrawable/SkiaPipeline，避免只锚 OpenGL。
- **review 日志**：logs/deep-review/2026-05-07-15-deep-review.md

## [Task9 Deep Review] 2.7 Hardware Layer — 2026-05-07
- **类型**：数据缺失
- **位置**：L182-L184 16KB 页与 GPU layer 内存
- **问题**：[P2] 已标 `[待验证]`，但正文仍先断言 GPU 显存分配最小对齐单元提升会让小 layer 有更多填充浪费。该影响依赖 gralloc/GPU driver/sub-allocator，不能由 Android 16KB page size 直接推出。
- **建议**：改成研究假设，要求用 memtrack/gralloc/dumpsys gfxinfo 在具体设备上验证；不要把 16KB 页粒度等同于纹理实际分配粒度。
- **review 日志**：logs/deep-review/2026-05-07-15-deep-review.md

## [Task9 Deep Review] 13.7 Perfetto 的高级用法 — 2026-05-07
- **类型**：数据缺失
- **位置**：L762 NDK ATrace_* 开销
- **问题**：[P2] “单次约 50-100ns”没有来源、设备、构建类型、是否 tracing enabled/disabled、字符串长度等条件。Trace 点治理章节给出精确数值但缺测试边界，会误导生产包开销评估。
- **建议**：补 microbenchmark/官方来源；至少拆成 tracing disabled fast path、enabled path，并写明 SoC/Android 版本/编译优化条件。
- **review 日志**：logs/deep-review/2026-05-07-15-deep-review.md

## [Task9 Deep Review] 8.4 其他响应速度场景 — 2026-05-07
- **类型**：源码准确性
- **位置**：L115 Fragment 切换调用链
- **问题**：正文写 `FragmentTransaction.commit()` → `BackStackRecord.execute()`。AndroidX Fragment 当前 `BackStackRecord` 的执行方法是 `executeOps()` / `executePopOps()`，由 `FragmentManager.execPendingActions()`、`removeRedundantOperationsAndExecute()`、`executeOpsTogether()` 等路径调度；不存在稳定的 `BackStackRecord.execute()` 调用点。
- **建议**：改成“`commit()` 入队，`FragmentManager` 在主线程执行 pending actions，最终调用 `BackStackRecord.executeOps()` 推进 Fragment 生命周期”。
- **review 日志**：logs/deep-review/2026-05-07-18-deep-review.md

## [Task9 Deep Review] 15.6 性能测试最佳实践 — 2026-05-07
- **类型**：源码/API 边界
- **位置**：L498-L521 Macrobenchmark JSON 结果自动分析
- **问题**：正文写 JSON 可通过 `androidx.benchmark:benchmark-junit4` 库解析，并列出 `metricName`、`median`、`minimum`、`maximum`、`p90`、`runs`。AndroidX `benchmark-common` 当前 `BenchmarkData.kt` schema 是 `benchmarks[].metrics` / `sampledMetrics` map，metric name 是 map key；单值指标字段为 `minimum`、`maximum`、`median`、`coefficientOfVariation`、`runs`，采样指标为大写 `P50/P90/P95/P99`。`BenchmarkData` 本身带 `@RestrictTo(LIBRARY_GROUP)`，不应写成稳定公开解析 API。
- **建议**：改成“CI 可读取 Macrobenchmark 生成的 JSON artifact 并按当前 schema 解析；解析代码应固定 AndroidX 版本或做 schema 兼容”。不要承诺 `metricName` / 小写 `p90` 字段，也不要把内部 `BenchmarkData` 当公开 API。
- **review 日志**：logs/deep-review/2026-05-07-18-deep-review.md

## [Task9 Deep Review] 8.4 其他响应速度场景 — 2026-05-07
- **类型**：示例代码边界
- **位置**：L196-L214 Lifecycle + ViewModel 懒加载示例
- **问题**：[P2] 示例只在 `viewLifecycleOwner.lifecycleScope.launch` 中 collect `uiState`，没有触发首次加载，也没有 `repeatOnLifecycle` 限制可见状态；与“只在首次可见时加载”的说明没有闭环。
- **建议**：补 `onResume`/`repeatOnLifecycle(Lifecycle.State.RESUMED)` 触发 + ViewModel 幂等 guard，或者把示例改成只展示状态收集，不宣称它完成懒加载。
- **review 日志**：logs/deep-review/2026-05-07-19-deep-review.md

## [Task9 Deep Review] 8.4 其他响应速度场景 — 2026-05-07
- **类型**：Trace 观察点
- **位置**：L407 搜索响应网络请求观察
- **问题**：[P2] 正文写网络请求可以在 `HttpURLConnection` 或 OkHttp 的 trace 中观察到，容易让读者理解为 Perfetto 默认有稳定 OkHttp/HttpURLConnection slice。实际需要 OkHttp EventListener、自定义 `Trace.beginSection`、Network Inspector 或更底层 socket/syscall/ftrace 线索。
- **建议**：改成“默认 Perfetto 不保证有应用层 HTTP client slice；需要在 repository/OkHttp EventListener 外层补稳定 trace 名称，或结合 socket/线程状态侧证”。
- **review 日志**：logs/deep-review/2026-05-07-19-deep-review.md

## [Task9 Deep Review] 19.13 androidx.tracing（Tracing SDK） — 2026-05-07
- **类型**：版本边界
- **位置**：L232 API 31+ app tracing 默认可见性
- **问题**：[P2] 正文写 API 31+ app tracing 在所有应用里默认开启，但 AndroidX Trace 源码注释还列出 `<profileable enabled=false/>` 或 `<profileable shell=false/>` 例外。
- **建议**：补 profileable manifest 例外，避免把“默认开启”写成无条件成立。
- **review 日志**：logs/deep-review/2026-05-07-19-deep-review.md

## [Task9 Deep Review] 4.1 Android 内存模型全景 — 2026-05-07
- **类型**：数据缺失/Trace 观察点
- **位置**：L221、L272、L460、L526
- **问题**：章节仍以 `[待补充]` 占位承载 dumpsys meminfo 真机输出、Graphics 内存、Perfetto 内存曲线和内存压力 Trace，缺少设备版本、page size、TraceConfig 数据源、采样周期与操作步骤。当前机制描述可读，但关键工具段还不能支撑读者复现实验。
- **建议**：补一组同设备、同包名的 `dumpsys meminfo` 前后快照 + Perfetto TraceConfig（至少 `linux.process_stats`、`linux.sys_stats`，必要时加 `kmem/rss_stat`、lmkd/ActivityManager 事件），标注 Android 版本、页大小、采样周期、触发操作与 SQL/UI 观察点。

## [Task9 Deep Review] 10.2 内存泄漏 — 2026-05-08
- **类型**：版本差异/数据缺失
- **位置**：L331 ProfilingManager 线上采集
- **问题**：正文把 Android 15+ `ProfilingManager.requestProfiling()` 描述成“系统级零侵入触发能力”，但缺少 API 35 边界、rate limit、不保证一定执行、结果只落在应用数据目录/会被 redaction 的约束。
- **建议**：补充 `PROFILING_TYPE_JAVA_HEAP_DUMP`、`PROFILING_TYPE_HEAP_PROFILE`、`PROFILING_TYPE_SYSTEM_TRACE` 的类型边界，并写明请求有系统限流与失败路径，线上只能作为按条件采样/诊断入口，不能替代常驻泄漏监控。

## [Task9 Deep Review] 19.13 androidx.tracing（Tracing SDK） — 2026-05-08
- **类型**：数据缺失
- **位置**：L163-L179 Trace 调用开销表
- **问题**：表格给出“亚微秒级/百纳秒级/6-14μs”等具体量级，但没有设备、Android 版本、AndroidX 版本、trace 配置、benchmark 脚本和重复次数；ftrace/atrace 写入成本受 SoC、buffer、trace session 状态影响很大。
- **建议**：要么降级为定性描述（disabled fast path 低、enabled path 包含 tag check/JNI/ftrace write），要么附 `androidx.benchmark` Microbenchmark 条件与 raw result，再把数字限定在测试设备范围内。

## [Task9 Deep Review] 19.26 混合栈与跨平台 APM (WebView / Flutter) — 2026-05-08
- **类型**：数据支撑/监控开销
- **位置**：L149-L178 PixelCopy 白屏采样示例
- **问题**：示例每次创建全宽、最高 480px 的 ARGB_8888 bitmap，没有检查 WebView 宽高/attach/window 状态，也没有复用或回收 bitmap；线上低频采样仍可能带来 Native heap 抖动或在宽高为 0 时抛异常。
- **建议**：补充 `width/height > 0`、`isAttachedToWindow`、window token/可见性检查；使用下采样区域或 bitmap pool，分析后 `recycle()`/复用，并记录 PixelCopy result code 以区分采样失败和“非白屏”。

## [Task9 Deep Review] 19.26 混合栈与跨平台 APM (WebView / Flutter) — 2026-05-08
- **类型**：原理边界
- **位置**：L143 postVisualStateCallback 可见性说明
- **问题**：`postVisualStateCallback` 只保证当前 WebView visual state 已准备好在后续 draw 中呈现，不保证已经显示到屏幕；WebView 被遮挡、未 attach、窗口不可见时也可能触发回调。正文用于白屏采样锚点时缺少这层边界。
- **建议**：补一句：它只能作为渲染管线就绪信号，最终屏幕可见性仍要结合 View attach/visibility/window focus 和 PixelCopy/DOM/业务 ready 交叉判断。


## [Task9 Deep Review] 19.17 Firebase Performance — 2026-05-08
- **类型**：源码准确性/版本差异
- **位置**：L138/L143 App start 起点说明
- **问题**：正文把 API 24+ 启动起点概括为 `Process.getStartUptimeMillis()`，但当前 Firebase Android SDK `AppStartTrace` 中 process start 计时使用 `Process.getStartElapsedRealtime()`；`logAppStartTrace()` 仍以 `getClassLoadTimeCompat()` 写 `_app_start` 的 start/duration，实验 TTID trace 才走 process-start 兼容路径。这会把平台 API、Firebase `_app_start` 与实验 TTID 的口径混在一起。
- **建议**：补一个源码锚点说明：`Process.getStartElapsedRealtime()`/`getStartUptimeMillis()` 是平台进程启动时间 API；Firebase 当前 app-start 实现需区分 `_app_start`、`_experiment_app_start_ttid` 与低版本 class-load fallback。若不展开源码，至少改成“API 24+ 平台提供进程启动时间，Firebase SDK 是否用于控制台指标以当前 SDK 源码为准”。

## [Task9 Deep Review] 19.17 Firebase Performance — 2026-05-08
- **类型**：源码准确性/版本差异
- **位置**：L138/L143 App start 起点口径
- **问题**：正文把 API 24+ 平台进程启动时间和 Firebase Performance 当前 `_app_start` 口径放在同一段，容易让读者以为控制台 `_app_start` 直接使用 `Process.getStartUptimeMillis()`。当前 Firebase Android SDK `AppStartTrace` 保存 process-start 时使用 `Process.getStartElapsedRealtime()`，实验 TTID 走 `getStartTimerCompat()`；公开 `_app_start` 的 `logAppStartTrace()` 仍以 `getClassLoadTimeCompat()` 作为 clientStartTime。
- **建议**：拆成两句写：平台 API 24+ 提供进程启动时间锚点；Firebase 当前指标要按 SDK 源码区分 `_app_start` 与 `_experiment_app_start_ttid`，低版本/兼容路径仍可能退回 Firebase class-load time。

## [Task9 Deep Review] 1.17 IPC 全景：Android 进程间通信机制对比与性能选型 — 2026-05-08
- **类型**：数据缺失
- **位置**：L415-L419 使用频率统计
- **问题**：“Binder ~90% 的 IPC 调用、Unix Socket ~5%”缺少统计口径：没有限定设备、进程集合、采样窗口、trace 配置或统计 SQL，容易被读者当成 AOSP 通用事实。
- **建议**：改成“示意图/经验估计”并标注 `[待验证]`，或补一组可复现统计方法：例如基于 binder driver trace、socket syscall trace 和目标系统进程列表给出采样窗口与 SQL/脚本。

## [Task9 Deep Review] 4.7 16KB Page Size 与 Android 性能 — 2026-05-08
- **类型**：版本差异/源码准确性
- **位置**：L225-L230 控制接口总览
- **问题**：`pm.16kb.app_compat.disabled` 被写成“安装时预检”。官方文档把它作为强制开启/关闭 16KB backcompat 的设备属性；Android 17 还支持 `bionic.linker.16kb.app_compat.enabled=fatal` 使不兼容 binary 立即 abort。
- **建议**：把该行改为“设备级强制关闭 compat / 配合 linker 属性控制 backcompat”，并补 Android 17 `fatal` 模式；不要把它归类为安装时预检。

## [Task9 Deep Review] 1.17 IPC 全景：Android 进程间通信机制对比与性能选型 — 2026-05-08
- **类型**：技术审计/P2 建议
- **位置**：L144/L360-L370 AF_VSOCK / RpcBinder 数据量与拷贝次数
- **问题**：[P2] 表格把 AF_VSOCK / RpcBinder 的数据量写成“与 Binder 同量级”、拷贝次数写成 1，容易让读者误以为 Binder driver 的进程级 transaction buffer 约束也适用于 RpcBinder over vsock。AVF 文档把 host↔VM 主通道描述为 virtio-socket/vsock，数据上限与性能边界应按 vsock/libbinder_rpc framing、socket buffer 和协议实现单独说明。
- **建议**：把该行改成“无 Binder transaction buffer 约束，受 vsock/socket buffer 与 RpcBinder framing 影响；大 payload 仍应另走共享内存/文件/流式协议”，拷贝次数改为“取决于 vsock/virtio 路径，需实测”。
- **review 日志**：logs/deep-review/2026-05-08-04-deep-review.md

## [Task9 Deep Review] 1.17 IPC 全景：Android 进程间通信机制对比与性能选型 — 2026-05-08
- **类型**：技术审计/P2 建议
- **位置**：L274-L291 Parcel::writeBlob 零拷贝表述
- **问题**：[P2] 当前源码链已修正为 16KB 阈值与 ashmem-compatible fd，但标题和说明直接写“实现零拷贝”。AOSP `Parcel::writeBlob()` 对大 blob 是把 fd 写入 Binder transaction，并让调用方写入映射区域；它避免 payload 经过 Binder buffer，不等于所有场景端到端零拷贝。
- **建议**：改成“对 Binder 事务而言只传 fd，不把大 payload 塞进 Parcel buffer；调用方仍可能需要把已有数据写入/拷入共享区域”。
- **review 日志**：logs/deep-review/2026-05-08-04-deep-review.md

## [Task9 Deep Review] 4.7 16KB Page Size 与 Android 性能 — 2026-05-08
- **类型**：技术审计/P2 建议
- **位置**：L126-L139 内部碎片的 5KB 对象例子
- **问题**：[P2] 正文用“App 分配 5KB 对象，16KB 页浪费 11KB”解释内部碎片，容易把 Java/Native 小对象说成直接占一个内核页。ART、malloc/scudo 会在 page/span 内做子分配，小对象通常不会一对象一页；页大小带来的浪费主要体现在页粒度映射、allocator span/class、mmap 大小与 RSS 结算上。
- **建议**：把例子限定为“单独 mmap 或页级分配区域”，并补一句：普通 Java/Native 小对象会被运行时/allocator 打包到页内，内存增长要用 RSS/PSS 和 allocator class 实测。
- **review 日志**：logs/deep-review/2026-05-08-04-deep-review.md

## [Task9 Deep Review] 4.7 16KB Page Size 与 Android 性能 — 2026-05-08
- **类型**：技术审计/P2 建议
- **位置**：L263-L271 NDK r27 mprotect alignment bug 口径
- **问题**：[P2] 正文写“NDK r27 链接器生成的 ELF 文件 p_align=4096”，口径过宽。官方迁移文档说明 NDK r27 及更低版本可通过 `-z,max-page-size=16384` 与 `-z,common-page-size=16384` 生成 16KB-aligned 产物；如果引用 android/ndk#2026，应限定为未正确设置 flags 或特定 r27 linker/RELRO 场景。
- **建议**：改成“NDK r27 及以下默认/未加完整 flags 的产物可能仍是 4KB alignment；android/ndk#2026 对应的 mprotect 失败需按 issue 的复现条件描述”。
- **review 日志**：logs/deep-review/2026-05-08-04-deep-review.md

## [Task9 Deep Review] 10.2 内存泄漏 — 2026-05-08
- **类型**：技术审计/P2 建议
- **位置**：L121-L124 LeakCanary retained 与 leak confirmation
- **问题**：[P2] 流程把“GC 后 WeakReference 没进 ReferenceQueue”直接写成“发生了泄漏”。LeakCanary 更精确的状态是对象被判定 retained；最终 leak 结论依赖 heap dump 后从 GC Root 到 watched object 的引用链分析。`Runtime.getRuntime().gc()` 也是触发请求而非规范保证。
- **建议**：把第三步改成“标记为 retained / suspected leak”，第四步再写“Heap Dump 中找到有效 GC Root 引用链后确认泄漏”。
- **review 日志**：logs/deep-review/2026-05-08-04-deep-review.md

## [Task9 Deep Review] 10.2 内存泄漏 — 2026-05-08
- **类型**：技术审计/P2 建议
- **位置**：L233-L236 libmemunreachable 零开销表述
- **问题**：[P2] `libmemunreachable` 被写成“零开销的泄漏检测”。它没有常驻插桩开销，但触发扫描时仍有暂停、遍历和误报/漏报成本；更适合作为 on-demand native leak sweep，而不是生产环境持续零成本检测。
- **建议**：改成“无持续插桩开销；触发时有扫描成本，结果是不精确的 suspected unreachable blocks”。
- **review 日志**：logs/deep-review/2026-05-08-04-deep-review.md

## [Task9 Deep Review] 10.2 内存泄漏 — 2026-05-08
- **类型**：技术审计/P2 建议
- **位置**：L301 heapprofd Java heap allocation 版本边界
- **问题**：[P2] 正文写 heapprofd 可通过 `heaps: "com.android.art"` 采 Java heap allocations，但版本边界“待核”。Perfetto 文档已经标注 Java allocation profiling available on Android 12 or higher，并说明它是 allocation samples，不是 heap dump/retention graph。
- **建议**：补 Android 12+ 边界，并明确它只能看到对象创建调用栈样本，不能证明对象仍被引用；泄漏确认仍要 Heap Dump/LeakCanary/Shark。
- **review 日志**：logs/deep-review/2026-05-08-04-deep-review.md


## [Task6 Review] 5.5 Thermal 管控 — 2026-05-08
- **类型**：需确认/需补充素材
- **位置**：AIW-源码调研-2026-05-07 / 16KB page size 对 thermal throttling 的延迟影响
- **问题**：残留段落仍把 16KB page size 对 thermal throttling 的收益写成确定性结论，并包含 `thermal_monitor_notify()`、Android 16/17 thermal 管理等未在本节证据中补齐来源的断言；与前文已降级为研究假设的口径冲突。
- **建议**：由 Task2B/Task9 按同设备 4KB/16KB A/B trace、AOSP 路径和官方文档复核；证据不足则删除该 AIW 段落或整体降级为研究假设。
- **review 日志**：logs/review/2026-05-08-05-review.md

## [Task9 Deep Review] 2.17 Frame Pacing Library 与帧节奏控制 — 2026-05-08
- **类型**：交叉引用一致性
- **位置**：L399 `详见 §16.4` / frontmatter `related_chapters`
- **问题**：DeliQueue 的完整架构与 targetSdk 37 行为变更在 §16.5《Android 17 (API 37) 性能行为变更与适配方法》；§16.4 只在 kernel 6.12 系统级优化章节中简述 DeliQueue。当前引用会让读者跳到信息较少的章节。
- **建议**：将正文“详见 §16.4”和 frontmatter `related_chapters` 中的 `16.4` 改为 `16.5`；如仍想保留系统级关联，可同时列 `16.4` 和 `16.5`，但 DeliQueue 深入解释应指向 §16.5。
- **review 日志**：logs/deep-review/2026-05-08-05-deep-review.md

## [Task9 Deep Review] 10.6 内存抖动与频繁 GC — 2026-05-08
- **类型**：版本差异/交叉引用一致性
- **位置**：L92-L94 / L381-L391 ART GC 版本边界
- **问题**：本节把 Android 8-14 主要归为 CC / 分代 CC，把 Android 15 作为 CMC 主线起点；但 §4.3 已写明 `android-14.0.0_r1` 公开源码中已有 `kCollectorTypeCMC` 与 `mark_compact.cc`，更合适的全书口径是 Android 8-13 看 CC，Android 14/15 看 UFFD 驱动的 CMC 路径，Android 16 QPR2 之后再谈 Generational CMC。
- **建议**：同步 §4.3 口径：Android 14/15 已进入 CMC 路径但不要写成 Generational CMC；Android 16 QPR2 是 Generational CMC 的正式公开节点；Android 17 默认状态继续保留 `[待验证]`，等待 release notes / ART flag / 设备配置确认。
- **review 日志**：logs/deep-review/2026-05-08-05-deep-review.md

## [Task9 Deep Review] 10.6 内存抖动与频繁 GC — 2026-05-08
- **类型**：数据缺失
- **位置**：L234 GC Events 频率阈值
- **问题**：正文写 GC 图标“每秒超过 2-3 次”即可说明内存抖动，但这个阈值缺少设备、ART 版本、堆大小、刷新率、负载类型和应用基线。不同应用的正常 GC 频率差异很大，固定阈值容易误导排查。
- **建议**：改成“显著高于该应用在同设备/同场景下的基线频率时需关注”；如保留 2-3 次/秒，标注它只是典型手机场景的经验提示，并补测试条件。
- **review 日志**：logs/deep-review/2026-05-08-05-deep-review.md
