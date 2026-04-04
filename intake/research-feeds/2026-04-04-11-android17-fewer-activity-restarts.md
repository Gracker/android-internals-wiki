## [研究] Android 17 减少 Activity 重启：recreateOnConfigChanges 新机制
- **来源**：https://developer.android.com/about/versions/17/behavior-changes-17#activity-restarts
- **作者/机构**：Google / Android Developer Documentation
- **日期**：2026-03-26 (Beta 3 Platform Stability)
- **四维评分**：相关性 5/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 5/5 · **总分 19/20**
- **映射章节**：§8.4 其他响应速度场景 / §1.6 Android 版本演进中的架构变化 / §3.3 手势导航与系统交互
- **映射锚点**：响应速度定义与分类、版本演进时间线、系统交互与导航
- **摘要**：Android 17（API 37）将 6 种配置变更的默认行为从"销毁重建 Activity"改为"不重启"，引入新 manifest 属性 `android:recreateOnConfigChanges` 供需要重启的 App 显式声明。这一变化直接减少了用户感知的界面闪烁和状态丢失，属于响应速度和用户体验的底层优化。

### 关键发现
1. **6 种配置变更不再触发 Activity 重启**：CONFIG_KEYBOARD、CONFIG_KEYBOARD_HIDDEN、CONFIG_TOUCHSCREEN、CONFIG_COLOR_MODE、CONFIG_NAVIGATION、CONFIG_UI_MODE（仅 UI_MODE_TYPE_DESK 切换）。这些配置在现代设备上频繁发生（如外接键盘、色域切换），过去每次都会触发完整 Activity 销毁-重建周期。
2. **新 manifest 属性 `android:recreateOnConfigChanges`**：如果 App 依赖 Activity 重启来重新加载这些配置的资源，需要显式使用此属性 opt-in。方向与 `android:configChanges` 相反——后者是"我来自处理，别重启"，前者是"请继续帮我重启"。
3. **与 Adaptive Layout 强制化的协同**：Android 17 同时强制大屏设备（sw≥600dp）的 App 必须自适应，忽略 screenOrientation/resizableActivity/minAspectRatio/maxAspectRatio。两者共同推进"App 不应依赖重建来适配新配置"的设计理念。
4. **Compose + ViewModel 最佳实践**：官方推荐使用 ViewModel + rememberSaveable 保存状态，而非依赖 Activity 重建。这与 writing-guide 中"承认复杂性"的原则一致——配置变更处理正在从"重建适配"转向"状态保持适配"。

### 可直接引用段落
> For apps targeting API 37, the system no longer restarts activities by default for configuration changes including CONFIG_KEYBOARD, CONFIG_KEYBOARD_HIDDEN, CONFIG_TOUCHSCREEN, CONFIG_COLOR_MODE, CONFIG_NAVIGATION, and CONFIG_UI_MODE (when changing to/from UI_MODE_TYPE_DESK). If your app relies on activity restarts for these changes, use the new `android:recreateOnConfigChanges` manifest attribute to opt in. (source: developer.android.com)

> The system recommends using ViewModels and `rememberSaveable` to preserve UI state across configuration changes, rather than relying on Activity recreation. The `android:configChanges` attribute should only be used in special cases where performance or responsiveness is a critical concern. (source: developer.android.com)

### 与 queue.json 联动
- 优先级调整建议：无（§8.4 已有较高优先级）
- 素材路径建议：可补充到 §8.4 的 material_paths 作为"Android 17 响应速度优化"案例
- freshness-004 联动：该素材覆盖了 freshness-004（§8.1 responsiveness-principles）中 Live Updates 相关的响应速度设计理念演进
