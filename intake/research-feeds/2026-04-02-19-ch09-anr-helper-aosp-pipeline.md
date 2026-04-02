## [研究] AOSP AnrHelper + ProcessErrorStateRecord ANR 处理管线深度分析
- **来源**：AOSP frameworks/base/services/core/java/com/android/server/am/AnrHelper.java + ProcessErrorStateRecord.java
- **作者/机构**：AOSP (Google)
- **日期**：持续更新，Android 14-16 架构
- **四维评分**：相关性 5/5 · 技术深度 5/5 · 时效性 4/5 · 可验证性 5/5 · **总分 19/20**
- **映射章节**：§9.3 ANR 分析方法 / §9.1 ANR 设计思想
- **映射锚点**：ANR 检测机制源码、AnrHelper 异步处理、traces.txt 写入流程、ProcessErrorStateRecord 状态管理
- **摘要**：AOSP 中 ANR 处理涉及 ActivityManagerService → ProcessErrorStateRecord → AnrHelper 三层架构。AnrHelper 使用独立的 AnrConsumerThread 异步处理 ANR 事件，将耗时的 stack trace 采集从 system_server 主线程卸载，避免 ANR 处理本身导致系统卡顿。

### 关键发现
1. AnrHelper.java 使用专门的 AnrConsumerThread 线程处理 ANR 事件队列，包含 ProcessErrorStateRecord 对象的队列。这确保 system_server 主线程不会被 ANR 数据采集阻塞
2. ProcessErrorStateRecord 是每个 ProcessRecord 持有的错误状态管理器，记录 ANR 和 Crash 的详细信息（类型、进程、ApplicationErrorReport.AnrInfo、stack trace 详情），维护 crashing/notResponding/forceCrashReport 等状态标志
3. ANR 数据采集流程：AMS 检测超时 → 更新 ProcessErrorStateRecord 标记为 notResponding → 入队给 AnrHelper → AnrConsumerThread 执行 dumpStackTraces() 写入 /data/anr/ → 触发 ANR 对话框（前台应用）
4. Android 14+ 引入 ProcessStateRecord 提供更精细的进程状态区分，ANR dump 信息更丰富

### 可直接引用段落
> AnrHelper serves as a dedicated utility for processing ANR events. Its primary responsibility is to offload the heavy work of collecting ANR-related data from the main system_server thread. It utilizes a dedicated AnrConsumerThread to process a queue of ProcessErrorStateRecord objects asynchronously. When an ANR is detected, AMS updates the ProcessErrorStateRecord for the unresponsive ProcessRecord, marking it as notResponding, and queues it for AnrHelper to process on its dedicated thread.
> — 来源: AOSP cs.android.com AnrHelper.java + ProcessErrorStateRecord.java

### 与 queue.json 联动
- 素材路径建议：补充到 §9.3 material_paths，与 §9.1 交叉引用
