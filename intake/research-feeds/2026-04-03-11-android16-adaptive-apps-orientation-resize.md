## [研究] Android 16 Adaptive Apps：大屏强制可调整 + 方向/宽高比限制失效

- **来源**：https://developer.android.com/about/versions/16/behavior-changes-16
- **作者/机构**：Google / Android Developer Documentation
- **日期**：2025-06-10（Android 16 正式发布）
- **四维评分**：相关性 4/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 5/5 · **总分 18/20**
- **映射章节**：§3.1 Input 事件分发全流程 / §16 窗口与显示
- **映射锚点**：Activity 生命周期与配置变更、Input dispatch 在多窗口下的表现、大屏适配对性能分析的影响
- **摘要**：Android 16（API 36）强制在大屏设备（sw≥600dp）上忽略 screenOrientation/resizableActivity/minAspectRatio/maxAspectRatio 及对应 runtime API，推动自适应布局。游戏和 <600dp 屏幕豁免，API 37 将彻底移除 opt-out。

### 关键发现
1. **Manifest 属性全部失效**：screenOrientation（含 portrait/landscape/sensorPortrait 等 8 种值）、resizableActivity="false"、minAspectRatio、maxAspectRatio 在 sw≥600dp 设备上被平台忽略
2. **Runtime API 同步失效**：setRequestedOrientation() 和 getRequestedOrientation() 在大屏上无效
3. **临时 Opt-Out 机制**：PROPERTY_COMPAT_ALLOW_RESTRICTED_RESIZABILITY 可临时 opt-out，但 API 37（Android 17）将移除此逃生通道
4. **性能分析影响**：Activity 因窗口尺寸变化更频繁地 recreate，开发者必须正确保存 UI State，否则用户数据丢失

### 可直接引用段落
> Starting with Android 16 (API level 36), apps targeting this version will have their orientation, resizability, and aspect ratio restrictions ignored on large screens (smallest width ≥ 600dp) in full-screen and multi-window modes. This includes manifest attributes like screenOrientation, resizableActivity="false", minAspectRatio, maxAspectRatio, and runtime APIs setRequestedOrientation() / getRequestedOrientation(). The temporary opt-out via PROPERTY_COMPAT_ALLOW_RESTRICTED_RESIZABILITY will be removed in Android 17 (API 37).

> Apps built with rigid, portrait-only layout assumptions may experience "input glitches" where keyboard and focus behavior fail because the underlying layout assumptions no longer hold true in a dynamic, resizable environment.

### 与 queue.json 联动
- 优先级调整建议：freshness-002（ch03-input/01-input-dispatch.md）reason 更新为包含具体 API 36 行为变更细节
- 素材路径建议：可补充到 §3.1 的"版本演进"小节和"与其他机制的关系"小节
