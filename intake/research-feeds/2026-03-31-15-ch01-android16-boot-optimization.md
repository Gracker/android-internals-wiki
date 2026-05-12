# [研究] Android 16 启动性能优化：并行模块加载与 AutoFDO

- **来源**: AOSP Gerrit / 9to5Google / TechRepublic
- **作者/机构**: Google
- **日期**: 2026-03-31
- **四维评分**: 相关性 5/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 4/5 · **总分 18/20**
- **映射章节**: 1.2 系统启动全流程 / 16.2 各 Android 版本性能变更追踪
- **映射锚点**: 启动优化、版本演进、内核模块加载、编译优化
- **摘要**: Android 16 引入了两项显著的启动性能优化：并行内核模块加载（Performance Mode）减少模块加载时间约 25-30%；AutoFDO（Automatic Feedback-Directed Optimization）基于真实应用使用数据优化内核热路径，整体启动时间减少约 2.1%。

## 关键发现

### 1. 并行模块加载（Performance Mode）

AOSP 中发现标题为 "Parallel Module Loading: Add Performance Mode" 的代码变更：

- **核心思路**: 在 Linux 内核启动后，将原本串行加载的内核模块改为并行加载
- **实测效果**: Pixel 10 上模块加载时间减少约 30%，2023 Pixel Fold 上减少约 25%
- **适用范围**: 预期惠及所有 Android 设备，不仅限于 Pixel 系列
- **技术原理**: 利用多核 CPU 的并行能力，在模块间无依赖关系时同时发起加载请求

### 2. AutoFDO（Automatic Feedback-Directed Optimization）

Google 将 AutoFDO 引入 Android 内核编译流程：

- **数据来源**: 收集 Pixel 设备上最常用的 100 个 Android 应用的实际运行数据
- **优化目标**: 分析这些应用与内核的交互模式，识别并优化频繁执行的 "热" 代码路径
- **实测效果**: 整体启动时间减少约 2.1%
- **额外收益**: 应用启动更快、多任务更流畅、电池续航改善
- **关键数据**: 内核操作约占 Android 设备 CPU 时间的 40%，因此内核级优化影响显著
- **版本范围**: 在 Android 15、16、17 beta 版本上测试验证

### 3. 与 BootTimingsTraceLog 的配合

这两项优化在 Perfetto 中的影响可以通过以下方式观察到：

- **并行模块加载**: 在 Perfetto 的内核模块加载阶段，原本串行的模块初始化 slice 会变为并行的多行 slice
- **AutoFDO**: 在 Perfetto 的 CPU scheduling view 中，热路径函数的执行时间会缩短
- 通过 BootTimingsTraceLog 标记的 boot_progress 里程碑可以量化优化前后各阶段的改善

## 可直接引用段落

> Android 16 在启动性能方面做出了两项值得关注的优化。第一是并行内核模块加载（Performance Mode），它将内核启动后原本串行的模块加载过程改为并行执行，在 Pixel 10 上实测减少约 30% 的模块加载时间。第二是 AutoFDO（Automatic Feedback-Directed Optimization），Google 通过分析最常用的 100 个 Android 应用在 Pixel 设备上的真实运行数据，识别内核中频繁执行的代码路径并针对性优化编译，使整体启动时间减少约 2.1%。由于内核操作约占 Android 设备 CPU 时间的 40%，这类优化对用户体验的提升是全方位的——不仅启动更快，应用响应和续航也同步改善。

## 与 queue.json 联动

- **优先级调整建议**: 建议将 16.2（各 Android 版本性能变更追踪）的 priority 从 50 提升到 65
- **素材路径建议**: 补充到 1.2 和 16.2 的 material_paths
