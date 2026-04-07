---
tags:
  - android
  - memory
  - research
---

# [研究] ART @FastNative/@CriticalNative JNI 调用优化详解

- **来源**: https://developer.android.com/reference/dalvik/annotation/optimization/CriticalNative
- **作者/机构**: Google Android Team (ART)
- **日期**: 2026-04-07
- **四维评分**: 相关性 5/5 · 技术深度 4/5 · 时效性 4/5 · 可验证性 5/5 · **总分 18/20**
- **映射章节**: 1.15 JNI/NDK 性能优化
- **映射锚点**: @FastNative 优化、@CriticalNative 优化、JNI 调用开销、ART JNI 内部机制
- **摘要**: ART 内置 @FastNative/@CriticalNative 注解可将 JNI 调用开销从 115ns 降至 25ns（5x 提升）。@CriticalNative 于 Android 14 成为 CTS 测试的公开 API，适用于纯原语参数的静态方法；@FastNative 支持托管对象但仍有 GC 不可暂停的约束。

### 关键发现

1. **精确纳秒级测量**（Nexus 6P 基准）：Regular JNI 115ns → @FastNative 35ns（3x 提升）→ @CriticalNative 25ns（5x 提升）。@CriticalNative 是 Android 上最快的 JNI 调用路径。

2. **@CriticalNative 严格约束**：仅限 static 方法；参数和返回值必须为原语类型或原语数组；函数签名排除 JNIEnv* 和 jclass；执行期间 GC 无法暂停线程——禁止用于长时间运行、I/O 或持锁操作。Android 14 起为 CTS 测试公开 API；Android 8-13 需显式 JNI RegisterNatives 注册才能生效；Android 7 及以下忽略。

3. **@FastNative 灵活但有限制**：支持非静态方法和托管对象参数/返回值；同样 GC 不可暂停约束；建议将调用方加入 Baseline Profile 以优化启动性能。

4. **编译器协同优化**：ART 通过 AOT/JIT/PGO 与 JNI 优化联动，结合 Class Hierarchy Analysis (CHA)、循环优化和 SIMD 向量化进一步减少托管代码层面的开销。Android 17 的 static final 不可变约束与 JNI RegisterNatives 显式注册协同，为 ART 常量折叠提供基础。

### 可直接引用段落

> Measurements on a Nexus 6P showed a "Regular JNI" call costing 115 nanoseconds, while a @FastNative call reduced this to 35ns, and @CriticalNative offered the fastest transition at 25ns. This translates to @FastNative potentially improving native method performance up to 3 times, and @CriticalNative up to 5 times.
>
> @CriticalNative became a CTS-tested public API in Android 14. For Android versions 8-13, the optimization is likely to work, especially on devices with the official ART Module (like Android 12+), but explicit registration with JNI RegisterNatives is strictly required for Android 8-11. These annotations are ignored on Android 7 and older.

### 与 queue.json 联动
- 优先级调整建议：1.15 保持 priority 80 不变
- 素材路径建议：追加到 1.15 的 material_paths
