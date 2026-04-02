## [研究] 2025-2026 Android 内存管理新进展：zRAM 多算法重压缩、MGLRU 与 AI 驱动资源分配
- **来源**：kernel.org changelogs + android-developers.googleblog.com + multiple technical sources
- **作者/机构**：Linux Kernel Team / Google Android Team
- **日期**：2026-04（综合梳理）
- **四维评分**：相关性 4/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 4/5 · **总分 17/20**
- **映射章节**：4.2 Linux 内核内存管理 / 4.4 Low Memory Killer / 4.6 内存相关的版本演进
- **映射锚点**：zRAM 压缩、内存回收、版本演进
- **摘要**：2025-2026 年 Android 内存管理在内核层面有三大突破：Kernel 6.12 引入 CONFIG_ZRAM_MULTI_COMP 允许多算法重压缩（lz4 快速 + zstd 高压缩比），Kernel 6.1 MGLRU 优化页面回收效率，Android 16+ 探索 AI 驱动的 Adaptive Resource Throttling（ART）。

### 关键发现
1. **Kernel 6.12 zRAM 多算法重压缩**：CONFIG_ZRAM_MULTI_COMP 允许对 zRAM 中的页面使用不同算法重压缩——先用 lz4 快速压缩保证低延迟，后台用 zstd 进一步压缩提升压缩比。直接效果：同样 RAM 容量下可容纳更多活跃页面
2. **Kernel 6.1 MGLRU（Multi-Generational LRU）**：替代传统 active/inactive LRU，使用多代链表更精确地跟踪页面热度，显著改善内存回收效率。已在 Android Common Kernel 中启用
3. **16KB Page Size 的内存管理影响**：减少 TLB miss，降低 MMU 开销。冷启动提升 3.16%~30%，功耗降低 4.56%，系统启动减少 8%
4. **AI 驱动资源分配（Adaptive Resource Throttling, ART）**：分析设备型号、OS 版本、可用内存、电池温度、用户行为等信号，动态分配资源，从响应式内存管理转向预测式
5. **Android 16 RAM Booster**：用户可见的 RAM 扩展功能，利用内部存储作为 swap 空间（类似三星 RAM Plus），最高可扩展到 10GB

### 可直接引用段落
> Kernel 6.12 introduces CONFIG_ZRAM_MULTI_COMP, a build setting that allows zRAM to recompress pages using different algorithms (e.g., lz4 for speed, zstd for higher compression ratio), further reducing compressed memory footprint and freeing up space for active tasks.

> MGLRU (Multi-Generational LRU) uses multiple generations of page lists to track page hotness more accurately than the traditional active/inactive LRU, significantly improving memory reclaim efficiency. It has been enabled in the Android Common Kernel.

### 与 queue.json 联动
- 优先级调整建议：§4.2/4.4/4.6 均为 completed 状态，本素材可作为补充材料（无需调 priority）
- 素材路径建议：可追加到 §4.2 和 §4.6 的 material_paths
