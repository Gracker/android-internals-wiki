## [研究] Startup Profiles 与 DEX Layout 优化：冷启动 15-30% 提升

- **来源**：https://developer.android.com/topic/performance/baselineprofiles/overview
- **作者/机构**：Google / Android Developer Documentation
- **日期**：2025-06 (AGP 8.3 GA, Android 16 release)
- **四维评分**：相关性 5/5 · 技术深度 4/5 · 时效性 4/5 · 可验证性 5/5 · **总分 18/20**
- **映射章节**：8.3 启动优化策略 / 16.x 构建优化
- **映射锚点**：Baseline Profiles、Startup Profiles、DEX layout、AGP 8.3+、冷启动量化数据
- **摘要**：Startup Profiles 是 Baseline Profiles 的子集，专门优化启动路径。AGP 8.3 起默认启用 DEX layout 优化，R8/D8 编译器将启动关键类集中到 classes.dex，冷启动速度提升 15-30%（相比单独使用 Baseline Profiles）。

### 关键发现
1. **Startup Profiles ≠ Baseline Profiles**：Startup Profiles 是 Baseline Profiles 的启动子集，用于编译时 DEX 文件布局优化，而 Baseline Profiles 用于运行时 AOT 编译。两者互补。
2. **DEX Layout 机制**：R8/D8 编译器根据 Startup Profiles 将启动关键类排列到 classes.dex（主 DEX 文件），确保类加载器优先命中。如果关键类超过 65535 方法数限制，溢出到后续 DEX 文件。
3. **AGP 8.3 默认启用**：`dexLayoutOptimization = true` 在 AGP 8.3+ 默认开启；AGP 8.1-8.2 需手动在 `baselineProfile {}` 块中设置。每个 variant 可配置独立 Startup Profile。
4. **量化数据**：使用 Startup Profiles + DEX layout 后，冷启动速度比单独使用 Baseline Profiles 快 15-30%。综合使用 Baseline + Startup Profiles，总体启动和运行时性能可提升 30%+。
5. **测量工具**：推荐使用 Jetpack Macrobenchmark 的 `StartupProfileBenchmark` 测量，结合 `CompilationMode.None()`（冷启动基线）和 `CompilationMode.Partial()`（Profile 启动）对比。

### 可直接引用段落
> Startup Profiles are a subset of Baseline Profiles specifically designed to optimize your app's startup path. At compile time, the build system uses Startup Profiles to determine the layout of code within the APK's DEX files — ensuring that the classes and methods needed during startup are placed in the primary classes.dex file for faster class loading. This can lead to 15% to 30% faster app startup compared to using Baseline Profiles alone. Starting with AGP 8.3, DEX layout optimizations are enabled by default.
> — developer.android.com

### 与 queue.json 联动
- 优先级调整建议：建议检查 §8.3 启动优化策略是否已覆盖 Startup Profiles 与 DEX Layout 的详细机制
- 素材路径建议：可补充到 §8.3 的 material_paths
