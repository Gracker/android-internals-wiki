## [研究] Android 16KB Page Size 全面性能影响与版本演进

- **来源**：https://source.android.com/docs/architecture/16kb-page-size + https://android-developers.googleblog.com/
- **作者/机构**：Google Android Team
- **日期**：2025-11 (强制生效) / 持续更新至 2026
- **四维评分**：相关性 5/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 5/5 · **总分 19/20**
- **映射章节**：4.6 内存相关的版本演进
- **映射锚点**：16KB Page Size 影响 / 内存版本速查表 / Android 15/16/17 内存变更
- **摘要**：Android 15 引入 16KB 页面支持，Android 16 在高端设备默认启用。Google Play 自 2025-11 强制要求适配。性能数据包括冷启动提速 3.16%~30%、功耗降低 4.56%、相机冷启动快 6.6%、系统启动快 8%。

### 关键发现
1. **TLB 效率提升**：16KB 页面减少页表条目数量，TLB 命中率显著提高——这是所有性能改善的底层机制。设备 RAM 越大（12-16GB），收益越明显
2. **量化性能数据**：Google 官方测试显示——App 启动平均快 3.16%（内存压力下最高 30%）、启动功耗降 4.56%、相机冷启动快 6.6%、热启动快 4.48%、系统启动快 ~8%（约 950ms）
3. **强制适配时间线**：2025-11-01 起 Google Play 强制 16KB 适配（延期至 2026-05-31）；纯 Java/Kotlin 应用自动兼容，NDK/C++ 需 NDK r28+ 重编译
4. **内存开销权衡**：小分配（如 mmap 4KB）会实际占用 16KB 页面，造成内部碎片——这是唯一的负面 trade-off

### 可直接引用段落
> Android 15 introduces support for 16KB page sizes. This change is driven by several benefits: reduced memory overhead (fewer page table entries), improved TLB hit rates, and enhanced performance. The shift to 16KB pages can result in faster app launch times (up to 30% for some apps under memory pressure), quicker device boot times (~8%), lower power consumption (~4.56%), and faster camera startup. Devices with 8GB+ RAM are expected to ship with 16KB pages enabled by default.
> — source.android.com

> Starting November 1, 2025, all new apps and updates targeting Android 15+ must support 16KB page sizes on 64-bit devices. NDK r28+ compiles with 16KB ELF segment alignment by default. AGP 8.5.1+ automatically enables 16KB alignment for uncompressed shared libraries.
> — developer.android.com

### AOSP 验证路径
- adb shell getconf PAGE_SIZE 验证设备页面大小
- zipalign -c -P 16 -v 4 APK_NAME.apk 验证 APK 对齐
- PRODUCT_MAX_PAGE_SIZE_SUPPORTED := 16384 构建配置
- PRODUCT_NO_BIONIC_PAGE_SIZE_MACRO := true 移除硬编码 PAGE_SIZE

### 与 queue.json 联动
- 优先级调整建议：4.6 review issue "16KB Page Size 速查表待补充正文" 可用本素材完整支撑正文
- 素材路径建议：追加到 4.6 的 material_paths
