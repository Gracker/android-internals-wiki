---
tags:
  - android
  - memory
  - research
---

## [研究] @FastNative/@CriticalNative JNI 快速转换：ART 内置优化机制详解

- **来源**：cs.android.com (art/runtime/native_entry_points.h) + developer.android.com/ndk/guides
- **作者/机构**：AOSP / Google Android Team
- **日期**：2024-2025（Android 14 CTS 公开 API）
- **四维评分**：相关性 4/5 · 技术深度 4/5 · 时效性 4/5 · 可验证性 4/5 · **总分 16/20**
- **映射章节**：1.15 JNI/NDK 性能优化
- **映射锚点**：JNI 调用开销、@FastNative 机制、@CriticalNative 机制、GC 阻塞约束、兼容性矩阵
- **摘要**：@FastNative 和 @CriticalNative 是 ART 内置的 JNI 快速转换优化。@FastNative 允许访问托管对象，将 JNI 调用开销从 ~115ns 降至 ~35ns；@CriticalNative 更严格（不能使用托管对象/JNIEnv/jclass），降至 ~25ns。Android 14 起 @CriticalNative 成为 CTS 测试的公开 API。关键约束：执行期间阻塞 GC，不可用于长耗时操作。

### 关键发现

1. **性能量化**：常规 JNI ~115ns → @FastNative ~35ns（降低 70%）→ @CriticalNative ~25ns（降低 78%）。对热循环中频繁调用的 native 方法效果显著。
2. **GC 阻塞约束**：@FastNative/@CriticalNative 执行期间 GC 无法暂停该线程。不可用于长耗时操作（I/O、长时间持有 native 锁）。
3. **ABI 变更**：@CriticalNative 排除 JNIEnv 和 jclass 参数，改变了 JNI 转换的 ABI。不能处理托管对象。
4. **兼容性矩阵**：Android 14+ CTS 公开 API；Android 12+ 内置动态 JNI 链接完全可用；Android 8-11 需 RegisterNatives 显式注册；Android 7- 注解被忽略，@CriticalNative 会因 ABI 不匹配 crash。

### 可直接引用段落

> @FastNative provides faster JNI transitions while still allowing the native method to interact with managed objects. @CriticalNative offers even faster transitions but cannot use managed objects in parameters or return values, nor JNIEnv or jclass parameters.
>
> Regular JNI calls costing around 115 nanoseconds, @FastNative reduced this to approximately 35 nanoseconds, and @CriticalNative further decreased it to about 25 nanoseconds.
>
> While executing a @FastNative or @CriticalNative method, garbage collection cannot suspend the thread for essential work and may become blocked. Therefore, these annotations should not be used for long-running methods.

### 与 queue.json 联动
- 优先级调整建议：维持 1.15 优先级 80
- 素材路径建议：补充到 1.15 material_paths，可作为 JNI 开销分析的核心素材