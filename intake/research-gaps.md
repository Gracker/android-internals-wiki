
## [2026-05-31] 22.3 Jetpack Compose 性能优化 — 知识盲区

### 盲区描述
缺少 Compose Multiplatform 跨平台性能考量、Baseline Profile 与 Compose 集成优化、Compose 性能测试方法论、Compose 动画性能特殊优化路径

### 重要程度
高

### 建议研究方向
- Compose Multiplatform 在 iOS、Web、桌面端的性能差异和优化策略
- Baseline Profile 如何与 Compose 编译时优化和运行时缓存协同工作
- 建立完整的 Compose 性能测试体系，包括 Macrobenchmark 编写、基线建立、优化效果验证
- Compose 动画性能瓶颈分析，包括 Animatable、Transition、SharedFlow 等组件的性能优化技巧

### 关联章节
7.7, 2.4, 22.1

---

## [2026-05-31] 22.3 Jetpack Compose 性能优化 — 知识盲区(新增)

### 盲区描述
Compose 1.10+ 中 rememberCoroutineScope 和 produceState 对组合性能的影响未充分讨论，非 restartable Composable 在 Strong Skipping 下的优化策略缺失

### 重要程度
高

### 建议研究方向
- 分析 rememberCoroutineScope 和 produceState 的内存分配模式和重组触发机制
- 研究 Strong Skipping 对非 restartable Composable 的限制和替代优化方案
- 调研 Compose 与 View 系统混合场景中的性能边界和最佳实践

### 关联章节
7.7, 22.1, 18.1

---

## [2026-06-02] 5.6 Android 功耗管理 — 知识盲区

### 盲区描述
Android 17 / API 37 范围内是否存在可公开引用的 Energy Limiter / Power Check 机制，尤其是“按 App 后台 μJ 能量计量、超配额强杀后台进程、与 Standby Bucket 绑定”的调用链，目前缺少 Android 17 CDD、AOSP PowerStats/ODPM、CTS 或官方特性页证据。

### 重要程度
高

### 建议研究方向
- 只检索 Android 17 / API 37 及以下资料，跳过 Android 18 / API 38+ 内容
- 复核 Android 17 release notes、CDD、source.android.com power / PowerStats / ODPM 文档是否出现 Energy Limiter / Power Check 约束
- 若仅能找到 main/master 或厂商私有资料，标注“未进入 Android 17”，不得作为正文结论

### 关联章节
5.6, 5.10, 11.1, 11.5

---
