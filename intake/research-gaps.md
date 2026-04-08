
## [2026-04-08] 1.1 Android 分层架构 — Zygote 预加载机制源码路径缺失

### 盲区描述
正文描述了"Zygote 进程预加载了 ART 运行时、常用 Java 类、系统资源"，但未给出 `preload()` 方法的源码路径和关键片段。性能分析中，理解 Zygote 预加载了哪些类（`preloadClasses()` / `preloadResources()` 的具体内容和大小）对分析冷启动瓶颈至关重要——如果某个 App 依赖的类不在预加载列表中，就会导致额外的初始化时间。

### 重要程度
高

### 建议研究方向
- 找到 Zygote.java 中 `preloadClasses()` 和 `preloadResources()` 的完整实现
- 确认 Android 16 中预加载列表的变化（是否有新增/删除的预加载类）
- 量化预加载资源的大小（通常在 30-50MB 范围）
- 分析 App 冷启动中 Zygote fork 后、App 代码执行前这段时间的初始化来源（ART 初始化 vs 资源加载）

### 关联章节
1.2（boot-process）、1.11（zygote-startup）、1.7（art-compilation）、8.3（launch-optimization）
