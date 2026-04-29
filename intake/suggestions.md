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
