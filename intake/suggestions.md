## [Task9 Deep Review] 1.5 线程模型 — 2026-07-06
- **类型**：版本差异覆盖
- **位置**：章节开头适用版本声明
- **问题**：章节声明适用 Android 5.0 - Android 17，但源码引用基于 android-16.0.0_r1，与目标版本 Android 17 (android-17.0.0_r1) 存在版本差异
- **建议**：要么将源码引用更新为 android-17.0.0_r1 并验证对应的 API 行为，要么明确标注当前内容基于 Android 16，并说明 Android 17 中的关键差异点

## [Task9 Deep Review] 1.5 线程模型 — 2026-07-06
- **类型**：版本差异覆盖
- **位置**：MessageQueue 实现演进段落
- **问题**：章节明确覆盖 LegacyMessageQueue、CombinedMessageQueue、ConcurrentMessageQueue 三套实现，但未明确说明各版本的启用边界和默认实现路径
- **建议**：补充三个实现版本的启用条件、默认路径选择逻辑，以及 Android 17 中新队列的实际启用情况

## [Task2A 知识缺口挖掘] 已检查方向 — 2026-07-06 08:04

**本轮挖掘结果**：未发现评分 ≥ 14 的知识缺口，跳过新章节创建。

**已检查方向（避免下轮重复）**：

### Part 5 ch20（稳定性）— 20 节，与 Clippings《稳定性剖析》25 篇交叉验证
- Java Crash 治理 ✓ (20.02)
- Native Crash 治理 ✓ (20.03, 含 MTE/16KB/Native DCL)
- ANR 治理 ✓ (20.04)
- OOM 治理 ✓ (20.05)
- 稳定性指标 ✓ (20.06)
- 异常架构 ✓ (20.07)
- Crash 聚合 ✓ (20.08)
- 案例集 ✓ (20.09)
- WebView Renderer OOM ✓ (20.10)
- 线程/FD 监控 ✓ (20.14)
- SafeMode ✓ (20.12)
- Binder 异常 ✓ (20.17)
- Native 堆栈符号化 ✓ (20.18)
- → Clippings 素材已被现有章节充分覆盖

### Part 5 ch21（启动）— 17 节，与 Clippings《性能优化》启动篇交叉验证
- 启动分析 ✓ (21.01)
- 启动框架 ✓ (21.02)
- ContentProvider 优化 ✓ (21.03)
- Baseline Profile ✓ (21.04)
- Splash Screen ✓ (21.05)
- 懒初始化 ✓ (21.06)
- 多进程启动 ✓ (21.07)
- 启动监控 ✓ (21.08)
- 案例集 ✓ (21.09)
- SDK Runtime ✓ (21.10)
- DI 框架 ✓ (21.14)
- Compose 首帧 ✓ (21.15)
- 线程池并发 ✓ (21.16)
- Startup Insights API ✓ (21.17, draft)
- GC 抑制 ✓ (21.13)
- → 启动优化方向充分覆盖

### Part 5 ch22（渲染实战）— 31 节
- Compose 性能 ✓ (22.03)
- Compose 盲区 ✓ (22.20)
- Compose LazyList ✓ (22.22) ← 曾以为是缺口，已存在
- Compose 布局测量 ✓ (22.25)
- Compose 文本 ✓ (22.25b)
- Compose 编译器指标 ✓ (22.28)
- Compose 动画 ✓ (22.21)
- Compose 并发安全 ✓ (22.29)
- Compose Navigation ✓ (22.23) ← 曾以为是缺口，已存在
- RecyclerView 实战 ✓ (22.02)
- 自定义 View ✓ (22.04)
- WebView 优化 ✓ (22.07)
- 图片加载 ✓ (22.06)
- 帧监控 ✓ (22.08)
- Fragment 事务 ✓ (22.12)
- 预测返回 ✓ (22.13)
- 桌面窗口 ✓ (22.14)
- Adaptive 刷新率 ✓ (22.18)
- App Widget ✓ (22.24)
- 多形态自适应 ✓ (22.27)
- Vulkan 异步编译 ✓ (22.29b)
- Impeller Shader ✓ (22.30)
- → 渲染实战方向充分覆盖

### Part 5 ch25（功耗与体积）— 22 节
- 功耗诊断 ✓ (25.01)
- 后台功耗 ✓ (25.02)
- WakeLock/Alarm ✓ (25.03)
- WorkManager ✓ (25.04 + 25.24)
- 位置/传感器 ✓ (25.05, 25.22)
- APK 分析 ✓ (25.06)
- R8/资源优化 ✓ (25.07)
- AAB 交付 ✓ (25.08)
- FGS 超时/配额 ✓ (25.13)
- 过度 CPU Kill ✓ (25.12)
- ADPF ✓ (25.11, 25.16)
- 音频 Offload ✓ (25.18)
- 后台音频硬化 ✓ (25.17)
- Android Vitals ✓ (25.19)
- → 功耗体积方向充分覆盖

### Part 5 ch26（可观测性）— 24 节
- 可观测架构 ✓ (26.01)
- Crash 上报 ✓ (26.02)
- 性能采集 ✓ (26.03)
- ANR 监控 ✓ (26.04)
- 在线排障 ✓ (26.05)
- A/B 回归 ✓ (26.06)
- 发布质量门禁 ✓ (26.07)
- ApplicationExitInfo ✓ (26.09)
- eBPF 在线追踪 ✓ (26.11)
- App Start Info ✓ (26.13)
- Android Vitals ✓ (26.15)
- 存储/SQLite 可观测 ✓ (26.16)
- 网络质量可观测 ✓ (26.17)
- 性能评分 ✓ (26.18)
- → 可观测性方向充分覆盖

### 已检查的 AOSP/官方文档方向
- NotificationManagerService → 已有 08.14 覆盖
- AlarmManagerService → 已有 25.03 覆盖
- SensorManagerService → 已有 25.05/25.22 覆盖
- InputMethodManager → 已有 03.11 覆盖
- AccessibilityService → 已有 07.19 覆盖
- MediaSessionService → 非核心性能路径
- ProfilingManager → 已有 08.16/14.07 覆盖
- GPU 跨厂商计数器 → 已有 14.28 (draft) 覆盖
- GPU DVFS → 已有 17.09 (draft) 覆盖

### 结论
全书 599 个文件，Part 5 已有 120+ 节，覆盖了 Android 17 性能优化的绝大多数主题。
Clippings 三本参考书的知识点已被现有章节充分消化。
下一轮可探索 Book 2（线上疑难问题 59 篇）的深度扫描，看是否有新的知识点缺口。
