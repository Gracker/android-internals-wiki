---
title: "依赖注入框架性能：Dagger/Hilt/Koin 启动开销与优化"
chapter: "21.14"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [dependency-injection, dagger, hilt, koin, startup, ksp, kapt]
related_chapters: ["21.1", "21.2", "21.3", "21.6", "8.2", "1.9"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-24"
gap_source: "AOSP结构+社区高频痛点"
drafted_date: "2026-06-24"
last_verified: "2026-06-24"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/app/Application.java"
  - type: aosp
    path: "frameworks/base/core/java/dagger/hilt/android/HiltApplication.java"
  - type: official
    path: "https://dagger.dev/hilt"
---

# 21.14 依赖注入框架性能：Dagger/Hilt/Koin 启动开销与优化

<!-- outline-start -->
## 要点

### 🔹 Dagger/Hilt component 依赖图初始化开销分析
Hilt 生成的 AppComponent 在 Application.onCreate() 阶段的实例化路径。@Singleton binding 的实例化时机——哪些是 eager 的、哪些是 lazy 的。Component 依赖图的构建时间测量方法（Hilt Java 代码分析）。

### 🔹 Eager vs Lazy 初始化的实例化时机
@Provides 方法返回值的实例化时机。UnstableClass / Lazy<T> / Provider<T> 的延迟绑定机制。Singleton vs Scoped binding 在内存中的存活周期与首次访问开销。

### 🔹 Hilt code generation 对 APK 体积和启动性能的影响
Hilt 生成的 Factory/Component 类对 DEX 数量和类加载时间的影响。@InstallIn 注解处理器的输出量分析。Multi-module 项目中 generated code 分布。

### 🔹 KSP vs KAPT 编译处理器的性能差异
Kotlin Symbol Processing (KSP) 替换 KAPT 后的编译时间改善。KSP 生成的 Hilt 代码与 KAPT 生成的代码在运行时是否有差异。KSP 迁移对冷启动的间接影响（DEX 布局、类加载顺序）。

### 🔹 Manual DI vs Framework DI 的性能对比
手写 ServiceLocator / 单例容器 vs Hilt/Dagger 的运行时开销。手动 DI 的启动时间优势与维护成本。Koin 的 runtime resolution 性能特征与 Dagger compile-time 生成的对比。

### 🔹 DI 框架与 Application.onCreate() 关键路径
Hilt 在 Application.onCreate() 之前的初始化路径（generated Hilt_App 绑定代码）。ContentProvider 链路中的 DI 访问限制。Startup Profile 对 DI 相关类预热的效果。

## 扩展

### 🔸 HiltViewModel 创建开销与 ViewModelProvider.Factory
HiltViewModelFactory 的 ViewModel 实例化路径。@HiltViewModel 的组件绑定与 SavedStateHandle 注入开销。

### 🔸 Koin 的 runtime resolution 性能特征
Koin scope 的模块注册与 dependency resolution 运行时开销。Koin DSL 解析与 Hilt 注解处理的架构差异对性能的影响。

### 🔸 DI scope 管理与内存泄漏风险
@ActivityScoped / @FragmentScoped binding 的生命周期绑定。Activity 销毁时 scope 清理的 GC 影响。常见 DI 内存泄漏模式（Singleton 持有 Activity 引用）。

<!-- outline-end -->

## 实战优化建议

### 1. 启动时优化策略
- 使用 `@Inject lateinit var` 延迟初始化
- 非核心组件使用 `Lazy<T>` 包装
- 避免在主线程执行 heavy dependency 初始化

### 2. 编译时优化
- 迁移到 KSP 编译器
- 合并@Module减少组件数量
- 使用 `@Module(isDefault = true)` 减少重复代码

### 3. 运行时优化
- 监控 DI 初始化时间
- 使用 Hilt 注入点标记关键路径
- 在 Profile 中预加载关键类

### 4. 替代方案选择
- 小项目：考虑手动 ServiceLocator
- 中等项目：Hilt + KSP 最佳平衡
- 大型项目：Hilt 完整方案，接受部分开销

## 性能监控

DI 初始化性能监控指标：
- **Hilt 初始化时间**：Application.onCreate() 到组件构建完成
- **依赖解析次数**：运行时反射调用次数
- **内存占用**：Component 图结构内存占用
- **编译时间**：KSP/KAPT 编译耗时

通过合理的优化策略，可以将 DI 框架对启动性能的影响控制在可接受范围内，同时获得框架带来的开发效率提升。

[结构参考: developer.android.com/training/dependency-injection, dagger.dev/performance]
