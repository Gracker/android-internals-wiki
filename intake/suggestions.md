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
