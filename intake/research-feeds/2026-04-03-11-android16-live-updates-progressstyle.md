## [研究] Android 16 Live Updates：ProgressStyle 通知 API + Promoted Ongoing 机制

- **来源**：https://developer.android.com/about/versions/16/features + https://developer.android.com/reference/android/app/Notification.ProgressStyle
- **作者/机构**：Google / Android Developer Documentation
- **日期**：2025-06-10（Android 16 正式发布）
- **四维评分**：相关性 3/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 5/5 · **总分 17/20**
- **映射章节**：§8.1 响应速度原则 / §15 Framework 服务（NotificationManager）
- **映射锚点**：Notification 响应速度对用户感知的影响、系统对 Ongoing Notification 的优先级调度
- **摘要**：Android 16 引入 Live Updates（ProgressStyle 通知 API），提供 segments/points/tracker icon 等组件构建进度型通知。这些通知自动获得提升的可见性（锁屏顶部/状态栏 chip/通知栏置顶），需声明 POST_PROMOTED_NOTIFICATIONS 权限并通过 setRequestPromotedOngoing 请求提升。

### 关键发现
1. **Notification.ProgressStyle 新 API**：
   - Segment：着色进度条不同阶段（如交通状况）
   - Point：里程碑标记（如备餐/配送/取餐）
   - Tracker Icon：可自定义图标沿进度条移动（如车辆图标）
   - Start/End Icon：进度条首尾图标
2. **Promoted Ongoing Notification 机制**：
   - 声明 POST_PROMOTED_NOTIFICATIONS 权限
   - 通过 setRequestPromotedOngoing(true) 请求提升
   - 提升后：锁屏顶部、状态栏 chip、通知栏置顶，不可被其他通知挤下
   - 限制：不可用 Custom View、不可 Group Summary、Channel 不能 Low Importance
3. **适用场景**：必须是用户主动发起、有明确起止的连续活动（打车/外卖/导航）
4. **性能分析角度**：Promoted Notification 在 NotificationManager 调度中享有更高优先级，频繁更新可能影响系统响应速度

### 可直接引用段落
> Android 16 introduces Live Updates with Notification.ProgressStyle API, allowing developers to create progress-centric notifications with segments, points, tracker icons, and start/end icons. These notifications qualify for promoted ongoing status, appearing at the top of the notification drawer, on the lock screen, and as chips in the status bar.

> To qualify as a Live Update, notifications must represent an ongoing, user-initiated activity with a clear start and end. Developers must declare POST_PROMOTED_NOTIFICATIONS permission and use setRequestPromotedOngoing or EXTRA_REQUEST_PROMOTED_ONGOING to request promotion.

### 与 queue.json 联动
- 优先级调整建议：freshness-004（ch08-responsiveness/01-responsiveness-principles.md）的 reason 应补充 Live Updates 对 Notification 响应速度模型的影响
- 素材路径建议：可补充到 §8.1 的"通知与响应速度"讨论和 §15 Framework 服务的 NotificationManager 部分
