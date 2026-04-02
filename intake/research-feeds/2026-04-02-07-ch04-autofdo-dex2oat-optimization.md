## [研究] AutoFDO 内核优化与 dex2oat 编译时间 18% 缩减

- **来源**：https://android-developers.googleblog.com/ (Android Runtime optimizations) + https://source.android.com/docs/core/perf
- **作者/机构**：Google ART Team / Android LLVM Toolchain Team
- **日期**：2025-06 / 2025-12
- **四维评分**：相关性 4/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 4/5 · **总分 17/20**
- **映射章节**：4.6 内存相关的版本演进 / 1.6 版本演进
- **映射锚点**：编译优化 / Profile-Guided Optimization / 版本速查表
- **摘要**：Google 将 AutoFDO（Automatic Feedback-Directed Optimization）集成到 Android 内核（android15-6.6 / android16-6.12），内核占设备 CPU 时间约 40%，优化带来显著性能提升。同时 ART 团队将 dex2oat 编译时间缩减 18%，通过 Mainline 更新推送到 Android 12+ 设备。

### 关键发现
1. **AutoFDO 内核集成**：利用真实使用数据（Top 100 应用负载采样）指导编译器内联和代码布局优化。该技术已在 ChromeOS 和 Google 服务器大规模验证，现移植到 Android 内核
2. **内核占比关键**：Android 内核占设备 CPU 时间的约 40%，AutoFDO 对内核的优化直接转化为用户体验提升——更快的应用启动、更流畅的多任务、更低的功耗
3. **dex2oat 18% 编译提速**：ART 团队在不降低编译质量、不增加峰值内存的前提下，将 dex2oat 编译时间缩短 18%。2025-06 版本推送第一批优化，2025-12 推送第二批，Android 12+ 设备通过 Mainline 更新获取
4. **PGO 生态**：dex2oat 编译优化属于 PGO（Profile-Guided Optimization）体系的一部分——JIT 运行时收集 profile 再驱动 AOT（dex2oat）编译

### 可直接引用段落
> The Android LLVM toolchain team has been integrating AutoFDO directly into the Android kernel. Given that the kernel accounts for approximately 40% of CPU time on Android devices, these kernel-level optimizations yield substantial benefits: faster app launches, smoother multitasking, reduced CPU overhead, improved battery efficiency, and quicker boot times. Profiles are gathered from lab environments using representative workloads, such as running the top 100 most popular applications.
> — Google Blog, Android Performance Updates 2025

> The ART team successfully achieved an 18% reduction in compile times without compromising the quality of the compiled code or increasing peak memory usage. Some speed enhancements were rolled out in the June 2025 Android release, with the remaining optimizations in the end-of-year 2025 release. All Android 12+ devices receive these improvements through mainline updates.
> — android.com/art

### AOSP 验证路径
- AutoFDO 配置：kernel/ 构建系统中 AUTOFDO_BUILD 选项
- dex2oat profile 路径：/data/misc/profiles/cur/0/{pkg}/primary.prof
- Mainline 模块：com.android.art 模块更新

### 与 queue.json 联动
- 素材路径建议：可追加到 4.6 和 1.6 的 material_paths
- 建议：在版本演进速查表中增加 AutoFDO 和 dex2oat 编译优化的条目
