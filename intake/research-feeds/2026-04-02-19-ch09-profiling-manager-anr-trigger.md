## [研究] Android 16 ProfilingManager 系统触发式 ANR Profiling
- **来源**：https://developer.android.com/reference/android/os/ProfilingManager
- **作者/机构**：Google Android Team
- **日期**：2025-06 (Android 16 正式版)
- **四维评分**：相关性 5/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 5/5 · **总分 19/20**
- **映射章节**：§9.3 ANR 分析方法
- **映射锚点**：系统触发式 Profiling、ANR 自动抓取、ProfilingManager API
- **摘要**：Android 16 为 ProfilingManager 新增 System Triggered Profiling 能力，开发者可注册 TRIGGER_TYPE_ANR 触发器，在系统检测到 ANR 时自动抓取 Perfetto trace，捕获 ANR 发生前的历史数据。这解决了 ANR 不可预测导致手动 Profiling 难以捕获根因的问题。

### 关键发现
1. ProfilingManager 首次引入于 Android 15（API 35），允许 App 请求 Perfetto profiling 数据。Android 16 新增 addProfilingTriggers() 方法，支持系统事件自动触发 profiling
2. TRIGGER_TYPE_ANR 触发器在系统检测到 ANR 时自动启动 profile 录制，捕获 ANR 发生前的历史数据（而非仅 ANR 后的现场）。这意味着开发者可以看到导致 ANR 的实际阻塞操作，即使该操作在 ANR 被正式检测到时已经完成
3. 系统通过回调将采集到的 profile 数据提供给应用，开发者可使用 Perfetto UI (ui.perfetto.dev) 分析。完整的触发类型列表包括：TRIGGER_TYPE_ANR、TRIGGER_TYPE_COLD_START、TRIGGER_TYPE_EXCESSIVE_CPU、TRIGGER_TYPE_OOM

### 可直接引用段落
> Android 16 introduces System Triggered Profiling to the ProfilingManager, allowing apps to register for automatic profiling data collection when specific system events occur, including ANRs. Developers use ProfilingManager#addProfilingTriggers() with ProfilingTrigger.TRIGGER_TYPE_ANR to capture historical Perfetto data leading up to the ANR event. This is particularly valuable because ANRs are unpredictable, and manually starting a profile at the exact moment of the problem is often impossible.
> — 来源: developer.android.com, Android 16 API Reference

### 与 queue.json 联动
- 优先级调整建议：§9.3 建议将 priority 从 50 提升到 65
- 素材路径建议：补充到 §9.3 material_paths，关联 §14.7 (ProfilingManager)
