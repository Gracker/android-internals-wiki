# [研究] Android 15/16 的 16KB Page Size 对 ART 内存的影响

- **来源**: https://developer.android.com/guide/practices/page-sizes + Android 16 Developer Preview 文档
- **作者/机构**: Google Android Team
- **日期**: 2025-2026
- **四维评分**: 相关性 4/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 4/5 · **总分 17/20**
- **映射章节**: 4.3 ART 虚拟机内存管理、4.6 内存相关的版本演进
- **映射锚点**: 16KB page size、内存页对齐、TLB miss、ART 堆布局影响
- **摘要**: Android 15 引入 16KB 内存页支持（替代传统 4KB 页），Android 16 增加兼容模式。分析这一变化对 ART 堆布局、对象分配粒度、TLB 性能和整体内存占用的影响。

### 关键发现

1. **背景与动机**：4KB 页大小已使用 20+ 年。随着设备内存增大（8-16GB 常见），16KB 页可减少页表大小、降低 TLB miss、提升内存密集型工作负载性能
2. **对 ART 的影响**：
   - 堆的 mmap 区域以 16KB 为最小粒度，可能增加小对象的内部碎片
   - RosAlloc 的 slot/page 结构需适配 16KB 页边界
   - TLAB 最小分配单位从 4KB 变为 16KB，可能导致线程闲置内存略增
   - 但整体上，ART 的 Region（256KB）粒度远大于 16KB，影响有限
3. **兼容模式**：Android 16 为未适配 16KB 页的应用提供兼容层，避免因页大小变化导致的 JNI 或 native 内存分配问题
4. **性能数据**：Google 报告在部分工作负载上，16KB 页可带来约 5-10% 的性能提升（主要来自 TLB miss 减少）

### 可直接引用段落

> Android 15 引入了 16KB 内存页大小的支持，这是自 Linux 诞生以来 Android 设备首次脱离 4KB 页的传统。对于 ART 虚拟机来说，这一变化的影响是双面的：一方面，更大的页意味着每个 mmap 调用映射的内存量增加，ART 的 region（默认 256KB）恰好是 16KB 的整数倍，所以 region 级布局几乎不受影响；另一方面，TLAB 的粒度从 4KB 提升到 16KB，如果应用创建了大量线程但每个线程分配量很小，会有更多的内存被 TLAB 预占但未使用。在实际测试中，Google 报告 16KB 页在减少 TLB miss 方面带来了可测量的性能提升，尤其是对内存密集型应用。

### 与 queue.json 联动

- 映射：同时关联 4.3 和 4.6
- 建议：4.6 内存相关的版本演进 可补充 16KB page size 作为 Android 15/16 的重要变更
