## [研究] Android 前台服务 ANR 超时机制演进（Android 12→16）
- **来源**：developer.android.com/about/versions/12/behavior-changes-12 + /14/behavior-changes-14
- **作者/机构**：Google Android Team
- **日期**：2022-2025 (Android 12→16 行为变更文档)
- **四维评分**：相关性 5/5 · 技术深度 4/5 · 时效性 4/5 · 可验证性 5/5 · **总分 18/20**
- **映射章节**：§9.2 ANR 类型与触发条件 / §9.4 特殊场景的 ANR
- **映射锚点**：Service ANR 超时值、前台服务限制、fg service type、onTimeout 回调
- **摘要**：Android 12-16 对前台服务 ANR 机制进行了重大演进：Android 12 引入前台服务启动限制；Android 14 要求声明特定 fg service type 并请求对应权限，新增 onTimeout() 回调；Android 16 进一步优化 JobScheduler 配额。

### 关键发现
1. Service ANR 超时值区分：前台服务默认超时约 5 秒（startForeground 未调用）/ 20 秒（执行超时），后台服务超时 200 秒
2. Android 12 变更：引入 ForegroundServiceStartNotAllowedException，App 在后台时一般不能启动前台服务
3. Android 14 变更：必须为每个前台服务声明 foreground service type；必须请求对应权限；shortService 有严格的生命周期限制（约 3 分钟），超时触发 onTimeout() + ANR
4. Android 16 变更：JobScheduler 配额优化，STOP_REASON_TIMEOUT_ABANDONED，scheduleAtFixedRate 最多补执行 1 次

### 可直接引用段落
> Starting in Android 14 (API level 34), apps must declare a foreground service type for each foreground service and request the corresponding permission. The shortService type has a strict time limit of approximately 3 minutes. When this limit is exceeded, the system calls Service.onTimeout() and the app has a brief window to call stopSelf() before an ANR is triggered.
> — 来源: developer.android.com behavior-changes-12, behavior-changes-14

### 与 queue.json 联动
- 素材路径建议：补充到 §9.2 和 §9.4 的 material_paths
- 优先级调整建议：§9.4 建议从 50 提升到 60
