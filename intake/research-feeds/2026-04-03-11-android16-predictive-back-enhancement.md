## [研究] Android 16 Predictive Back 全面启用 + 新 Callback API

- **来源**：https://developer.android.com/about/versions/16/behavior-changes-16 + https://developer.android.com/guide/navigation/custom-back/predictive-back
- **作者/机构**：Google / Android Developer Documentation
- **日期**：2025-06-10（Android 16 正式发布）
- **四维评分**：相关性 3/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 5/5 · **总分 17/20**
- **映射章节**：§3.1 Input 事件分发全流程 / §3.3 手势导航与系统交互 / §8.1 响应速度原则
- **映射锚点**：Back 导航 Input 链路、Predictive Back 动画系统、OnBackInvokedDispatcher 调度
- **摘要**：Android 16 将 Predictive Back 设为默认启用，新增 finishAndRemoveTaskCallback/moveTaskToBackCallback 回调注册，以及 PRIORITY_SYSTEM_NAVIGATION_OBSERVER 优先级让 App 观察（但不消费）系统级 back 事件。onBackPressed() 彻底 deprecated。

### 关键发现
1. **Predictive Back 默认启用**：Android 16 中，所有支持的 App 自动启用 Predictive Back 动画（跨 Activity、跨 Task、长按 3-button navigation 的 back 键）
2. **新 Callback API**：
   - finishAndRemoveTaskCallback()：在 OnBackInvokedDispatcher 上注册，back gesture 直接 finish + 移除 Task
   - moveTaskToBackCallback()：注册后 back gesture 将整个 Task 退到后台（等同按 Home）
   - PRIORITY_SYSTEM_NAVIGATION_OBSERVER：只观察不消费 back 事件，用于 analytics 或状态同步
3. **onBackPressed() deprecated 升级**：Android 13 引入 OnBackInvokedDispatcher，Android 16 进一步收紧，不再建议使用旧 API
4. **性能分析影响**：Predictive Back 动画需要 App 在 gesture 阶段（而非 commit 阶段）就准备好目标 UI，对响应速度有更高要求

### 可直接引用段落
> Android 16 enables Predictive Back by default for supported applications. Developers should adopt OnBackInvokedDispatcher and register OnBackInvokedCallback instances for custom back handling. The PRIORITY_SYSTEM_NAVIGATION_OBSERVER allows apps to observe system-handled back navigation (like back-to-home) without consuming the event.

> Predictive back animations now apply across activities, tasks, and even for long-pressing the back button in 3-button navigation. Apps relying on the deprecated onBackPressed() may experience broken back navigation behavior.

### 与 queue.json 联动
- 优先级调整建议：无特别调整，但 §3.1 和 §3.3 的版本演进小节需要补充 Android 16 Predictive Back 默认启用信息
- 素材路径建议：可补充到 §3.3 的"手势导航与系统交互"和 §3.1 的"Input 分发链路"
