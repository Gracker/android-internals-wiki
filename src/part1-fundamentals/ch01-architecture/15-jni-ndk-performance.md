---
title: "JNI/NDK 性能优化"
chapter: "1.15"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [JNI, NDK, native-code, performance, @FastNative, @CriticalNative, 16KB-page-size]
related_chapters: ["1.4", "1.5", "1.7", "4.7", "8.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-06"
gap_source: "AOSP结构+官方文档+研究素材+读者需求"
---

# 1.15 JNI/NDK 性能优化

<!-- outline-start -->
## 要点

### 🔹 锚点 1：JNI 调用开销与性能边界
- JNI transition 的开销构成（Java → native / native → Java）
- JIT 编译器无法跨越 JNI 边界优化——这对热路径意味着什么
- 量化：单次 JNI call 的典型开销（ns 级）
- 在 Perfetto 中如何识别 JNI overhead（函数名包含 `JNI`、`CheckJNI` 的 slice）

### 🔹 锚点 2：JNI ID 缓存与批量操作
- jclass / jmethodID / jfieldID 的查找成本（字符串比较）
- 缓存策略：JNI_OnLoad 中全局缓存 vs 首次调用时缓存
- 批量操作 vs 频繁小调用：设计 native API 时的工作量合并原则
- 案例对比：1000 次 JNI 调用 vs 1 次 JNI 调用传入 1000 个元素

### 🔹 锚点 3：@FastNative 与 @CriticalNative 注解
- Android 7+ @FastNative：跳过部分 JNI 检查，减少 ~30% transition 开销
- Android 8+ @CriticalNative：更极端的优化（无 JNIEnv 访问、无异常、无对象分配）
- 使用约束与陷阱（不能分配 Java 对象、不能 throw）
- ART 内部实现原理：快速路径 vs 普通路径
- 在 AOSP 源码中的使用案例（Zygote、SystemServer 中的关键 JNI 调用）

### 🔹 锚点 4：字符串与数组操作优化
- Java UTF-16 vs JNI Modified UTF-8 转换开销
- GetStringCritical / GetPrimitiveArrayCritical：停止 GC 的代价
- 直接缓冲区（DirectByteBuffer）vs 拷贝方式传递大数据
- ByteBuffer 的 native 地址获取与零拷贝

### 🔹 锚点 5：16KB Page Size 对 Native 库的影响
- Android 15+ 强制 16KB page size 对齐要求
- .so 文件重排（segment 对齐）对内存占用的直接影响
- PLAY 策略：不支持 16KB 的 App 将被拒绝上架
- 工具链适配：LLVM/NDK 的 -Wl,--no-warn-mismatch 与 -Wa,--noexecstack

### 🔹 锚点 6：Native 层性能分析工具
- Simpleperf（Android 原生 perf 工具）采样 native 代码
- Perfetto 中 native 函数的 Trace 点（ATRACE_BEGIN / ATRACE_END）
- NDK Profiler（ndk-profiler）与 Sanitizers（ASan / UBSan / TSan）
- 在 Perfetto 中解读 native 调用栈

### 🔹 锚点 7：Android 系统服务中的 JNI 使用模式
- Binder 的 native 实现（libbinder_ndk）性能对比 Java Binder
- SurfaceFlinger / Hardware Composer 中的 JNI 调用模式
- Media codec 的 native 管线为何绕过 JNI
- 设计启示：什么场景应该用 JNI，什么场景应该用 IPC

## 扩展

### 🔸 扩展点 1：Rust 替代 C/C++ 的性能考量
- Rust FFI vs JNI 的开销对比
- Android 对 Rust 的采用趋势（libbinder_rs）
- 内存安全与性能的平衡

### 🔸 扩展点 2：JNI 线程模型与锁
- JNIEnv 的线程局部性（Thread-Local Storage）
- native 代码中获取 JNIEnv（JavaVM::AttachCurrentThread）
- native 线程与 Java 线程的同步陷阱

### 🔸 扩展点 3：JNI 注册方式对性能的影响
- 静态注册（JNI_OnLoad + RegisterNatives）vs 动态注册（命名约定）
- 启动时 RegisterNatives 的开销与延迟加载策略

<!-- outline-end -->

> 本节内容待加工。
