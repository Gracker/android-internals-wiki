## [研究] ContentProvider 启动时序与启动性能影响（AOSP 源码级）

- **来源**：AOSP frameworks/base + developer.android.com + 多源交叉验证
- **作者/机构**：AOSP / Google / 技术社区
- **日期**：2026-04-05
- **四维评分**：相关性 5/5 · 技术深度 4/5 · 时效性 4/5 · 可验证性 5/5 · **总分 18/20**
- **映射章节**：1.10 ContentProvider 性能与优化
- **映射锚点**：启动时序/ContentProvider.onCreate 对启动的影响/installContentProviders 源码路径/ANR 触发链路
- **摘要**：ContentProvider 在 App 启动期间由 ActivityThread.handleBindApplication → installContentProviders 顺序实例化，所有 CP 的 onCreate() 在 Application.onCreate() 之前、在主线程上顺序执行。每个 CP 的 onCreate 开销直接累加到冷启动时间。

### 关键发现
1. **启动时序链**：ActivityThread.main() → attach() → handleBindApplication() → installContentProviders()（逐一调用 installProvider） → Application.onCreate()。CP 的 onCreate 先于 Application 的 onCreate。
2. **主线程阻塞**：所有 ContentProvider 的 onCreate() 在主线程顺序执行。Firebase、WorkManager 等库各自注册独立 CP，每个 CP 带来实例化 + 初始化开销，多个 CP 叠加可导致数十到数百毫秒启动延迟。
3. **AOSP 源码路径**：
   - `frameworks/base/core/java/android/app/ActivityThread.java` — `handleBindApplication()` → `installContentProviders()` → `installProvider()`
   - `frameworks/base/core/java/android/content/ContentProvider.java` — 内部 `Transport` 类处理 Binder IPC
   - `ContentProvider$Transport.query` 是 ANR traces.txt 中的标志性栈帧
4. **初始化顺序不可控**：多个库通过 CP 自动初始化时，执行顺序取决于 manifest 中的声明顺序，可能因依赖未满足导致崩溃。

### 可直接引用段落
> ContentProvider 的 onCreate() 在 Application.onCreate() 之前、在主线程上被 ActivityThread.installContentProviders() 顺序调用。这意味着每个声明在 manifest 中的 ContentProvider 都会在冷启动期间完成实例化和初始化，其耗时直接累加到冷启动延迟中。在 Perfetto 中，这个过程对应 handleBindApplication 到 installContentProviders 的区间，可以在主线程 track 上观察到。

> 当 ContentProvider 跨进程调用时，`ContentProvider$Transport.query` 是 Binder 线程栈帧的标志。如果 ANR traces.txt 中出现该栈帧，说明 query 方法耗时过长，可能是数据库未建索引、大结果集 CursorWindow 翻页、或 Binder 线程耗尽。

### 与 queue.json 联动
- 优先级调整建议：无（§1.10 已 priority 80）
- 素材路径建议：补充到 §1.10 的 material_paths
