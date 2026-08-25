# 第 6 章：存储与 I/O

> 平台源码统一锚定 AOSP `android-17.0.0_r1` / Android 17（API 37）；涉及内核机制时，以 `android17-6.18-2026-06_r6` 为核对基线。量产设备的文件系统、块设备、调度器和厂商补丁以产品配置为准。

Android I/O（输入/输出）问题常以“偶发”的样子出现：主线程某次读取被 page fault（缺页）拉长，`fsync()` 等待闪存完成持久化，后台任务与前台启动争用块设备，或共享存储请求经过 MediaProvider 和 FUSE（用户态文件系统）后增加了延迟。只看 Java 调用栈，很容易把存储等待误判成业务计算。

分析时应先确认请求经过哪些层、具体在哪里等待，再讨论优化，不预设哪个文件系统更快：

- 应用私有目录通常经由 VFS（统一文件系统接口）、ext4/F2FS、device-mapper（块设备映射层）和块 I/O 层到达存储设备；
- 共享存储还要考虑 MediaProvider、FUSE、passthrough（绕过部分用户态数据转发）、FUSE BPF（让部分 FUSE 操作在内核侧处理）和 scoped storage（分区存储）权限检查；
- SharedPreferences 的 `commit()`、`apply()` 与 `QueuedWork` 决定 XML 何时写盘，以及积压的写入何时反过来阻塞调用线程；
- DataStore 解决的是异步、一致性和结构化存储问题，不会消除底层 I/O 延迟；
- 文件级加密、闪存回收、热节流、内存回写和并发负载，都可能改变同一段代码的长尾延迟。

eMMC、UFS 和 NVMe 是不同的存储接口，其并发队列能力并不相同；ext4 与 F2FS 的写入、回收和一致性策略也有差异。Android 平台允许产品选择不同组合，不能把“UFS 已普及”或“F2FS 随机写一定优于 ext4”当作具体设备的事实。调试前应记录挂载表、文件系统、块设备、内核配置和测试负载。

## 内容索引

- [6.1 Android 存储架构](01-storage-architecture.md)
- [6.2 文件系统与 I/O 调度](02-filesystem-io-scheduling.md)
- [6.3 SharedPreferences 与 DataStore：I/O、ANR 与多进程一致性](03-sharedpreferences-datastore.md)
- [6.4 vold、MediaProvider 与 FUSE：共享存储 I/O 路径](04-vold-mediaprovider-fuse.md)

## 阅读建议

遇到主线程处于 `D` 状态时，先查看它正在等待的内核栈、调度事件和 I/O 区间。`D` 只表示线程处于不可中断睡眠，原因还可能是驱动、内存回收或其他内核等待；单独出现 `block_io`、page fault 或 `io_uring`（Linux 异步 I/O 接口）事件，也不能证明它造成了卡顿。

推荐的排查顺序是：

1. 明确文件路径、文件系统、挂载选项和调用线程；
2. 用 Perfetto 和 ftrace（内核跟踪工具）对齐应用延迟、调度、page fault、writeback（脏页回写）和块 I/O；
3. 区分同步语义、队列拥塞、闪存长尾、文件系统回收和权限路径成本；
4. 在同一设备、同一构建和同一温度条件下做单变量复测。

应用启动阶段的 I/O 问题可以结合启动章节分析；如果同时出现 reclaim（内存回收）、PSI（资源压力停顿指标）或 page fault，还应查看内存管理章节。
