## [研究] Android 16 ApplicationStartInfo.getStartComponent()：精确识别启动触发组件

- **来源**：https://developer.android.com/reference/android/app/ApplicationStartInfo#getStartComponent()
- **作者/机构**：Google / Android API Reference
- **日期**：2025-06-10 (Android 16 API 36)
- **四维评分**：相关性 5/5 · 技术深度 3/5 · 时效性 5/5 · 可验证性 5/5 · **总分 18/20**
- **映射章节**：8.1 响应速度原理 / 8.3 启动优化策略 / 14.7 自动化工具
- **映射锚点**：ApplicationStartInfo、冷启动分析、getStartComponent()、START_COMPONENT_* 常量
- **摘要**：Android 16 在 ApplicationStartInfo（API 35 引入）上新增 getStartComponent() 方法，返回触发进程启动的具体组件类型常量（Activity/Broadcast/ContentProvider/Service/Other）。结合系统触发式 Profiling，开发者可精确区分不同启动路径并针对性优化。

### 关键发现
1. **新 API 常量**：`getStartComponent()` 返回以下常量之一：
   - `START_COMPONENT_ACTIVITY`：由 Activity 启动触发
   - `START_COMPONENT_BROADCAST`：由 BroadcastReceiver 触发
   - `START_COMPONENT_CONTENT_PROVIDER`：由 ContentProvider 触发
   - `START_COMPONENT_SERVICE`：由 Service 触发
   - `START_COMPONENT_OTHER`：其他触发源
2. **与 ProfilingManager 联动**：Android 16 的 `ProfilingManager` 支持 `TRIGGER_TYPE_COLD_START` 系统触发式追踪，结合 getStartComponent() 可建立"启动触发源 → 完整 Perfetto trace"的分析链路。
3. **实际分析场景**：多数开发者假设冷启动由 Activity 触发，但实际上 ContentProvider 初始化（如多个 SDK 的 ContentProvider）和 BroadcastReceiver 也会触发进程创建。不同触发路径的优化策略差异显著。
4. **API 演进**：
   - API 35 (Android 15)：引入 ApplicationStartInfo 基础类，提供 getStartType()、getTimestamp() 等方法
   - API 36 (Android 16)：新增 getStartComponent()，补充组件类型信息

### 可直接引用段落
> ApplicationStartInfo.getStartComponent() returns the component type that triggered the app's process start. This is particularly useful for cold start analysis: different start components (Activity, BroadcastReceiver, ContentProvider, Service) may have vastly different initialization paths and optimization opportunities. Combined with system-triggered profiling via ProfilingManager, developers can now capture Perfetto traces precisely when cold starts occur, without needing to instrument the app beforehand.
> — Android 16 API Documentation

### 与 queue.json 联动
- 优先级调整建议：建议在 §8.3 中补充 ApplicationStartInfo API 的实战用法说明
- 素材路径建议：可补充到 §8.1 / §8.3 的 material_paths
