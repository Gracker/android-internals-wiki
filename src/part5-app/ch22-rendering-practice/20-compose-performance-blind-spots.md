---
title: "Jetpack Compose 性能优化盲区：rememberCoroutineScope、produceState 与 Strong Skipping"
chapter: "22.20"
status: draft
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: [compose, coroutine, strong-skipping, performance, recomposition, memory]
related_chapters: ["22.3", "7.7", "2.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-04"
gap_source: "素材驱动"
confidence: high
---

# 22.20 Jetpack Compose 性能优化盲区：rememberCoroutineScope、produceState 与 Strong Skipping

<!-- outline-start -->
## 要点

### 🔹 锚点 1：rememberCoroutineScope 的生命周期与泄漏边界
- rememberCoroutineScope 创建的 CoroutineScope 绑定 Composition 生命周期
- 在 Composable 被移除后，scope 中的协程会被取消——但如果协程持有外部引用（ViewModel、Context），对象不会释放
- 与 LaunchedEffect 的区别：LaunchedEffect 的 key 变化时自动重启，rememberCoroutineScope 不会
- 常见误用：在 rememberCoroutineScope 启动的协程中捕获 Composable 参数，导致无效重组或内存泄漏
- Perfetto 中观察：协程泄漏表现为 CoroutineTracker 中活跃协程数只增不减

### 🔹 锚点 2：produceState 的数据流与 recomposition 开销
- produceState 将非 Compose 数据源（Flow、LiveData、callback）转换为 State<T>
- 内部机制：启动一个协程，通过 awaitProduceState 桥接外部数据源
- 常见问题：produceState 的 producer 在每次 recomposition 时是否重启取决于 key 参数
- 与 collectAsState 的性能对比：produceState 适合一次性转换，collectAsState 适合持续数据流
- produceState 中忘记 dispose 资源导致的泄漏

### 🔹 锚点 3：Strong Skipping 模式与稳定性推断
- Compose Compiler 1.0+ 引入 Strong Skipping：对非 @Stable / @Immutable 参数跳过比较
- Strong Skipping 的判断逻辑：默认所有 Lambda 和非基本类型参数都参与 equals 比较
- @Stable 注解的约束：返回值相同 → 结果相同，但很多开发者误用 @Stable（标注了可变类）
- Strong Skipping 开启后的性能提升量化（重组次数减少百分比）
- 配合 remember、derivedStateOf 使用时 Strong Skipping 的行为差异

### 🔹 锚点 4：rememberCoroutineScope + produceState 组合陷阱
- 在 produceState 内使用 rememberCoroutineScope 获取的 scope 时，作用域叠加导致取消时序复杂
- produceState 的 producer 在 Composition 进入时启动、退出时取消——与 ViewModelScope 的交互
- 多个 produceState 的数据竞争与合并策略

### 🔹 锚点 5：Compose 编译器版本与性能行为变化
- Compose Compiler 1.0 → 1.1 → 1.2 → 1.5 各版本在 skipping 和 stability 推断上的差异
- Kotlin 2.0 Compose Plugin 的变化：新的编译器插件替代 kapt/ksp 路径
- Android 17 (API 37) 上 Compose Runtime 的行为变化（如 Pausable Composition）
- 版本升级导致的静默性能退化案例

### 🔹 锚点 6：Perfetto 中诊断 Compose 性能盲区的方法
- Compose Tracing（Android 12+）在 Perfetto 中的轨道：重组计数、跳过计数、跳过原因
- 如何通过 Perfetto SQL 查询识别 rememberCoroutineScope 泄漏
- Compose Compiler 报告：composableGroup 标签与跳过标记
- 重组热力图：定位哪些 Composable 被频繁重组

## 扩展

### 🔸 扩展点 1：Compose Compiler 代码生成与 skipping 行为
- 反编译 Compose 生成的代码，理解 $changed 参数和 skipping 逻辑
- @Stable 与 @Immutable 在编译器层面的处理差异

### 🔸 扩展点 2：大型 Compose 应用的性能治理实践
- Compose 性能 CI：自动检测重组次数回归
- Compose Preview 对性能验证的局限
- Compose 与 View 混合栈的性能边界

<!-- outline-end -->

> 本节内容待加工。
