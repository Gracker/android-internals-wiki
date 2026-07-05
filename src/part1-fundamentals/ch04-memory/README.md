# 第 4 章：内存管理

内存问题很容易被狭义理解成“会不会 OOM”，但在 Android 上，真正影响体验的内存问题远不止崩溃。

页面切换越来越慢、后台回来像重启了一次、列表偶发卡一下、系统整体开始发飘，这些现象很多时候都和内存压力有关。  
如果只在 OOM 时才想起看内存，通常已经太晚了。

这一章会把 Android 内存问题拆成两个层次：  
一个是系统到底怎样分配、回收和压缩内存；另一个是这些系统行为最后如何反映到 App 的卡顿、重启、GC、LMK 和图形内存问题上。


Android 内存管理是一个跨层协作的系统。从 App 视角看，内存分配经过 Java Heap（ART 管理）和 Native Heap（scudo/mmap）；当内存紧张时，ART 触发 GC 回收 Java 对象，框架层通过 `ActivityThread.handleTrimMemory()` → `ComponentCallbacks2.onTrimMemory()` 通知 App 释放缓存；如果还不够，内核侧 kswapd 开始后台回收页面，把冷页面压缩写回 ZRAM swap 空间（`/proc/meminfo` 中 `SwapCached` + `SwapTotal` 可观测）；压力继续升级时，LMKD（`system/memory/lmkd/lmkd.cpp`，`mp_event_common` 主循环）按 oom_adj_score 逐级杀进程。整条链路中，App 能做的事情在第一环（主动释放）和最后一环（响应 `onTrimMemory`），中间的 kswapd、ZRAM、LMK 都是系统行为，App 只能观察不能控制。理解这条链路，能帮你在排查内存问题时判断：问题出在 App 自身分配过多，还是系统侧压力传导上来的。

## 本章内容

- Android 内存模型全景
- Linux 内核内存管理
- ART 虚拟机内存管理
- Low Memory Killer
- App 内存优化
- 内存相关的版本演进

## 阅读建议

- 如果你主要做 App 端内存优化，优先看 `4.1`、`4.3`、`4.4`、`4.5`。
- 如果你经常遇到“回前台像冷启动”“低内存设备特别差”这类问题，建议把 `4.2`、`4.4` 和第 10 章一起看。
- 如果你对 GPU/Graphics 内存、DMA-BUF、图形内存口径很关心，读本章时最好和渲染相关章节一起对照。

## 参考资料

### Linux 6.10 引入内存碎片整理新机制
- 来源：https://www.phoronix.com/news/Linux-6.10-Memory-Fragmentation
- 类型：技术深度分析
- 摘要：Linux 6.10 内核引入了创新的内存碎片整理机制，通过智能预分配和动态调整策略，大幅提升长期运行的系统稳定性。新机制采用分层管理策略，对频繁分配释放的热点...
- 入库时间：2026-07-04
- 评分：14/20
### Android 17 ART LargeObjectSpace 512M 突破与 mSponge 技术
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-07-05-android17-art-largeobjectspace-msponge-512m-bypass.md
- 类型：DeepResearch 调研结果
- 摘要：基于 android-17.0.0_r1 源码定位 Heap::num_bytes_allocated_（Atomic<size_t>）与 LargeObjectMapSpace::Alloc 的双路计数汇总链路（LOS 自身 + Heap::AddBytesAllocated）。分析 mSponge 通过 ELF symtab 定位符号、mprotect 修改 bss 段、fetch_sub 扣减 LOS 字节以绕过 512M 软阻塞的技术可行性，以及 SELinux、ART 完整性检查、并发 GC 误触发等风险面。
- 注入时间：2026-07-06
- 价值：为内存优化实战提供 LOS 突破方案的源码级可行性边界与风险评估，是 ch23.6 大内存策略的重要参考
