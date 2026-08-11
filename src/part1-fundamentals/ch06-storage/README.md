# 第 6 章：存储与 I/O

> 平台源码统一锚定 AOSP `android-17.0.0_r1` / Android 17（API 37）；涉及内核机制时，以 `android17-6.18-2026-06_r6` 为核对基线。量产设备的文件系统、块设备、调度器和厂商补丁以产品配置为准。

Android I/O 问题常以“偶发”的样子出现：主线程某次读取被 page fault 拉长，`fsync()` 等待闪存完成写入，后台任务与前台启动争用块设备，或共享存储请求经过 MediaProvider 和 FUSE 后增加了延迟。只看 Java 调用栈，容易把存储等待误判成业务计算。

分析从请求路径和等待位置开始，再讨论优化，不预设哪个文件系统更快：

- 应用私有目录通常经由 VFS、ext4/F2FS、device-mapper 和块层到达存储设备；
- 共享存储还要考虑 MediaProvider、FUSE、passthrough、FUSE BPF 和 scoped storage 权限检查；
- SharedPreferences 的 `commit()`、`apply()` 与 `QueuedWork` 决定 XML 写盘何时反压调用线程；
- DataStore 解决的是异步、一致性和结构化存储问题，不会消除底层 I/O 延迟；
- 文件级加密、闪存回收、热节流、内存回写和并发负载都可能改变同一段代码的长尾。

eMMC、UFS 和 NVMe 的队列能力不同，ext4 与 F2FS 的写入、回收和一致性策略也不同。Android 平台允许产品选择其中的组合，不能把“UFS 已普及”或“F2FS 随机写一定优于 ext4”当作设备事实。调试前应记录挂载表、文件系统、块设备、内核配置和测试负载。

## 内容索引

- [6.1 Android 存储架构](./01-storage-architecture.md)：分区、挂载、FBE、vold、应用目录与共享存储边界；
- [6.2 Android 文件系统](./02-filesystem.md)：ext4、F2FS、EROFS、OverlayFS 及产品选择；
- [6.3 I/O 调度与性能](./03-io-scheduling.md)：块层、调度器、writeback 与请求延迟；
- [6.4 SharedPreferences 与 DataStore](./04-sharedpreferences-datastore.md)：首次加载、`QueuedWork`、ANR、多进程一致性与迁移边界；
- [6.5 vold、MediaProvider 与 FUSE](./05-vold-mediaprovider-fuse.md)：共享存储控制面、数据面、passthrough、FUSE BPF 与现场取证。

SharedPreferences ANR 与 AndroidX DataStore 多进程一致性已经并入 6.4；passthrough 和 FUSE BPF 已并入 6.5。Linux 物理内存规整不属于存储主题，统一见 [4.10 内存规整与直接回收性能边界](../ch04-memory/10-memory-compaction-direct-reclaim.md)。Photo Picker、媒体转码和应用层缓存治理见 [24.12 Photo Picker、媒体转码与缓存治理](../../part5-app/ch24-io-network/12-photo-picker-transcoding-performance.md)。

## 阅读建议

遇到主线程 `D` 状态时，先查看它等待的内核栈、调度事件和 I/O 区间。`D` 只表示不可中断睡眠，原因还可能是驱动、内存回收或其他内核等待；单独出现 `block_io`、page fault 或 `io_uring` 事件也不能证明它造成了卡顿。

推荐的排查顺序是：

1. 明确文件路径、文件系统、挂载选项和调用线程；
2. 用 Perfetto/ftrace 对齐应用延迟、调度、page fault、writeback 和块 I/O；
3. 区分同步语义、队列拥塞、闪存长尾、文件系统回收和权限路径成本；
4. 在同一设备、同一构建和同一温度条件下做单变量复测。

应用启动阶段的 I/O 问题可结合启动章节分析；伴随 reclaim、PSI 或 page fault 时，还应查看内存管理章节。
