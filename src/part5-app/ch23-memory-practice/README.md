# 第 23 章：内存实践

应用内存问题常表现为对象泄漏、频繁分配引发的 GC 抖动、Native Heap 持续增长、图形缓冲区堆积，或超过系统内存限制后进程退出。GC（垃圾回收）会回收不再使用的托管对象；分配过快时，频繁回收可能占用线程时间并造成延迟波动。

诊断前要确定观测口径。堆、虚拟地址映射、驻留页和共享图形缓冲区分别描述不同对象，数值不能直接换算：

| 口径 | 含义 |
|---|---|
| Java Heap | ART（Android 运行时）管理的 Java/Kotlin 对象堆，受 GC 管理；对象仍被引用不等于业务仍需要它。 |
| Native Heap | C/C++ 代码通过 `malloc`、`new` 等方式申请的原生堆，也可能包含图片解码、媒体库和第三方库分配。 |
| 虚拟内存 / VSS | 进程占用的虚拟地址范围，包含尚未驻留、文件映射和共享映射；VSS 大不等于实际占用同等大小的物理内存。 |
| RSS / PSS | RSS 统计进程当前驻留页，共享页会在每个进程中重复计入；PSS 按共享者数量分摊共享页，更适合估算跨进程总占用。 |
| 图形与共享缓冲区 | `GraphicBuffer`、dma-buf 等可在应用、GPU、相机或编解码器之间共享，未必完整计入 Java Heap 或 Native Heap。 |

[第 4 章](../../part1-fundamentals/ch04-memory/README.md)分析 Android 内存管理机制，[第 10 章](../../part2-performance/ch10-memory-perf/README.md)介绍内存分析工具；本章整理应用侧的监控、诊断和优化实践。

## 内容索引

- [23.1 内存泄漏检测与治理](01-memory-leak-governance.md)
- [23.2 Bitmap 与图片内存优化](02-bitmap-optimization.md)
- [23.3 Native 内存管理与优化](03-native-memory-management.md)
- [23.4 Java Heap 优化策略](04-java-heap-optimization.md)
- [23.5 内存抖动与 GC 治理](05-memory-churn-gc.md)
- [23.6 大内存与多进程策略](06-large-heap-multiprocess.md)
- [23.7 内存监控与线上治理](07-memory-monitoring.md)
- [23.8 Jetpack Compose 内存分配与 GC 影响](08-compose-memory-allocation-gc.md)
- [23.9 应用虚拟内存优化实战](09-virtual-memory-optimization.md)
- [23.10 端侧大模型推理的内存管理](10-ondevice-llm-memory-management.md)

## 阅读建议

- 泄漏问题可从 23.1、23.3 和 23.7 开始，分配抖动可直接进入 23.5；Compose 场景进入 23.8。
- Native 场景应同时检查内存分配器（allocator）、线程栈、`mmap` 虚拟地址映射和图形缓冲区，不能只看 Java Heap。
- 大内存、多进程与 Android 17 MemoryLimiter 见 23.6。MemoryLimiter 是系统按设备总 RAM 设置的应用内存上限，目前只在部分设备启用；退出识别需要结合记录进程退出原因的 `ApplicationExitInfo`。
- 端侧模型的权重、`KV Cache`（键值缓存）和推理后端工作缓冲区预算见 23.10。`KV Cache` 保存 Transformer 模型已经计算出的注意力 key/value（键/值），通常随输入序列长度和并发请求增长。
- 线上数据应记录设备总 RAM、`ActivityManager.getMemoryClass()`（普通应用的近似 Java Heap 上限等级）、进程重要性和系统内存压力，用来区分应用自身增长与系统回收。
