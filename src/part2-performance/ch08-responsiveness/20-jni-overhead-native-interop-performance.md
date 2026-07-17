---
title: "JNI 调用开销与 Native 互操作性能边界"
chapter: "8.20"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: ['jni', 'native-interop', 'jni-overhead', 'critical-region', 'android-17']
related_chapters: ['1.15', '8.11', '8.19']
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
drafted_date: "2026-07-17"
last_verified: "2026-07-17"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/training/articles/perf-jni"
  - type: official
    path: "https://developer.android.com/reference/dalvik/annotation/optimization/FastNative"
  - type: official
    path: "https://developer.android.com/reference/dalvik/annotation/optimization/CriticalNative"
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
  - type: aosp
    path: "art/runtime/native_entry_points.h (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/jni/jni_env_ext.h (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/thread.h (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Parcel.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Binder.java (android-17.0.0_r1)"
  - type: blog
    path: "Cubox/ART 虚拟机 - JNI 优化简史-2023-06-27.md [结构参考]"
  - type: research
    path: "intake/research-feeds/2026-04-07-19-art-fastnative-criticalnative-jni-optimization.md"
  - type: research
    path: "intake/research-feeds/2026-04-07-11-android-16kb-page-size-jni-native-library-quantification.md"
---

# 8.20 JNI 调用开销与 Native 互操作性能边界

§1.15 讲了 JNI/NDK 的通用优化原则——缓存 ID、减少调用次数、`@FastNative`/`@CriticalNative` 的适用边界。这一节不重复那些内容，而是从**开销拆解**的角度切入：一次 JNI 调用的纳秒到底花在哪里，ART 内部的 trampoline 做了什么，JNI critical region 怎样阻塞 GC，引用表泄漏怎样拖垮性能，以及 Android 17 上哪些变化影响了 JNI 热路径。

如果你在做音视频编解码、端侧 AI 推理、游戏引擎桥接，或者任何"每帧调几千次 native"的场景，这些细节决定了"够不够快"和"会不会突然卡"之间的分界线。

[已验证: AOSP android-17.0.0_r1, art/runtime/ + frameworks/base/core/java/]

## JNI 调用开销拆解

### 从 Java 方法到 native 函数的三段路径

当 Java/Kotlin 代码调用一个 `native` 方法时，控制流并不直接跳到开发者写的 C/C++ 函数上。中间至少经历三段：

**第一段：JNI Trampoline 入口**

ART 为每个 native 方法准备了一个"跳板"函数（trampoline）。它的职责是完成从托管代码执行环境到 native 执行环境的过渡。对于解释执行模式，ART 使用通用的 `art_quick_generic_jni_trampoline`；对于 AOT/JIT 编译模式，编译器会根据参数类型生成特定的 "compiler JNI trampoline"。

通用 trampoline 的问题在于它必须考虑最极端情况。ART 源码中有一段注释直接写明了预留空间：

```c
// art/runtime/arch/arch_jni_frame.h (android-17.0.0_r1 仍保留该结构)
// Reserved area on stack for art_quick_generic_jni_trampoline:
// 4 local state ref
// 4 padding
// 4096 4k scratch space, enough for 2x 256 8-byte parameters
// 8*(32+32) max 32 GPRs and 32 FPRs on each architecture, 8 bytes each
// + 4 padding for 16-bytes alignment
// -----------
// 4616
// Round up to 5k, total 5120
```

也就是说，即使是只传一个 `int` 参数的 native 方法，解释器走通用 trampoline 也会在栈上预留 5120 字节。JVM 规范限制 Java 方法最多 255 个参数（含 `this`），通用 trampoline 要为这个理论上限做准备。

[已验证: AOSP android-17.0.0_r1, art/runtime/arch/ 通用 JNI 栈帧定义]

**第二段：线程状态切换**

Java 线程有两种与 JNI 相关的状态：

- **Runnable**：线程运行在 Java 世界，随时可能访问托管堆。GC 可以在安全点（safepoint）暂停它。
- **Native**：线程运行在 C/C++ 世界。在 GC 眼中，Native 状态的线程是"暂停"的——不是真的停了，而是 GC 假定它不碰 Java 堆。

普通 JNI 调用发生时，trampoline 必须把线程从 Runnable 切换到 Native。这个切换涉及：
1. 将线程状态写入 `Thread::state_and_flags`（一个原子操作，使用 `stlxr`/`ldaxr` 指令在 ARM64 上实现）
2. 更新 `JNIEnv` 内部的 `locals_cookie`（用于 local reference table 管理）
3. 保存 `frame_base` 和 `top_quick_frame_method`

调用返回时，再把状态切回 Runnable，并检查是否需要触发挂起（`pTestSuspend`）。

[已验证: AOSP android-17.0.0_r1, art/runtime/thread.h — Thread 状态机定义]

**第三段：参数 marshal 与引用表更新**

Java 引用类型的参数（`String`、`Object`、数组）需要被注册为 GC Root，否则 GC 可能漏掉仍在 native 侧持有的对象。这个注册动作发生在 Local Reference Table 中。trampoline 要：

1. 为每个引用参数在 Local Reference Table 中分配 slot
2. 处理 `jclass`（对静态方法）和 `JNIEnv*` 的传递
3. 对 `@CriticalNative` 方法，完全跳过这一段

### 汇编视角的开销对比

从 `oatdump` 的输出可以看到不同 JNI 路径生成的代码量差异（以下基于 ARM64）：

| JNI 路径 | 典型汇编行数 | 关键差异 |
| --- | --- | --- |
| 解释器通用 trampoline | ~120+ 行（含函数调用） | 栈预留 5120B，处理所有参数类型 |
| AOT/JIT compiler trampoline（普通） | ~75 行 | 参数类型已知，栈帧 176B；完整状态切换含 `stlxr`/`ldaxr` 原子操作 |
| AOT/JIT trampoline（`@FastNative`） | ~61 行 | 省去线程状态切换的原子操作序列 |
| `@CriticalNative` | ~4 行 | 仅参数搬运 + 间接跳转 |

[结构参考: Cubox/ART 虚拟机 - JNI 优化简史-2023-06-27.md]

`@CriticalNative` 为什么只有 4 行？因为它的 ABI 里没有 `JNIEnv*` 和 `jclass`，不需要引用表操作，不需要线程状态切换，不需要异常检查。编译器只需要把参数从 Java 调用约定搬到 native 调用约定，然后 `br x16`（间接分支）跳到目标函数。

但这 4 行并不是免费的——它带来的约束（不能访问托管堆、不能长时间运行、GC 无法暂停执行线程）才是真正的成本。

### RegisterNatives vs 动态查找（dlsym）性能差异

JNI 方法注册有两种方式：

1. **动态查找**（name-based lookup）：运行时根据方法名和签名，用 `dlsym` 在已加载的 `.so` 中查找符号。符号命名规则为 `Java_包名_类名_方法名`。
2. **RegisterNatives**（显式注册）：在 `JNI_OnLoad` 中通过 `env->RegisterNatives()` 显式建立 Java 方法与 native 函数的映射。

性能差异体现在两个层面：

**首次查找成本**：动态查找需要字符串拼接（构造完整符号名）+ `dlsym` 调用（遍历动态符号表），RegisterNatives 在 `JNI_OnLoad` 时一次性完成，后续调用直接走已建立的映射。

**AOT/JIT 可见性**：RegisterNatives 注册的方法在编译时就能被 ART 识别为 native 方法，可以生成特定的 compiler trampoline。动态查找的方法在首次调用时走解释器通用 trampoline，直到 JIT 热点检测触发编译后才升级。

[已验证: 官方文档, https://developer.android.com/training/articles/perf-jni — "RegisterNatives 的优势在于预先检查符号是否存在，且生成更小更快的共享库"]

**实践建议**：对启动路径上的 native 方法，优先使用 RegisterNatives。对只在运行时按需加载的功能模块，动态查找可以接受，但要注意首次调用的额外开销。

### 16KB page size 对 native 库加载与 JNI 的影响

16KB page size 变更主要影响 native 库的可加载性（详见 §8.11），但对 JNI 热路径也有间接影响：

1. **TLB 命中率提升**：16KB 页减少了 TLB 条目数量，降低 page table walk 开销。对 JNI 代码中频繁访问 native 内存（如音视频 buffer）的场景，数据面访存会有边际改善。Google 官方数据表明，在内存压力下 app 启动速度可达 30% 提升，但这种全局收益不单独归属 JNI。

2. **代码段对齐变化**：16KB 对齐意味着 `.so` 的 code segment 和 data segment 的 mmap 边界变了。对 JNI trampoline 这类极短函数密集的代码，instruction cache 的利用率取决于函数在虚拟地址空间中的布局。这种影响通常可忽略，但在极端微优化场景中值得知晓。

3. **兼容性阻断**：未做 16KB 对齐的第三方 `.so` 在 16KB 设备上直接 crash，谈不上 JNI 性能——连 `JNI_OnLoad` 都跑不到。AGP 8.5.1+ 和 NDK r28+ 默认启用对齐。

[已验证: 官方文档, https://developer.android.com/guide/practices/page-sizes]

## Get\<Type\>ArrayElements vs Get\<Type\>ArrayRegion

这是 JNI 数组访问中最高频的性能决策点之一。

### 两种 API 的语义差异

```c
// 方式 A：Get<Type>ArrayElements + Release
jbyte* data = env->GetByteArrayElements(array, NULL);
if (data != NULL) {
    memcpy(buffer, data, len);
    env->ReleaseByteArrayElements(array, data, JNI_ABORT);
}

// 方式 B：Get<Type>ArrayRegion
env->GetByteArrayRegion(array, 0, len, buffer);
```

方式 A 调用了两次 JNI 函数（Get + Release），方式 B 只调用了一次。方式 A 可能返回指向 Java 堆内部的真实指针（零拷贝），也可能返回一份 native 堆上的拷贝——这个行为由运行时决定，调用方通过 `isCopy` 出参获知。

方式 B 始终做一次拷贝（从 Java 数组到调用方提供的 buffer），但不涉及 pin 或 release 语义，也不会持有对 Java 堆内部指针的引用。

### 性能对比的关键结论

| 维度 | Get\<Type\>ArrayElements | Get\<Type\>ArrayRegion |
| --- | --- | --- |
| JNI 调用次数 | 2（Get + Release） | 1 |
| 是否可能零拷贝 | 是（返回内部指针） | 否（始终拷贝到调用方 buffer） |
| 是否 pin 数组 | 是（Release 之前数组被固定） | 否 |
| 对 GC 的影响 | pin 期间阻止压缩式 GC 移动该数组 | 无持续影响 |
| 代码出错风险 | 忘记 Release / 模式选错 | 低（无配对调用） |
| 适用场景 | 需要在 native 侧长时间读写整个数组 | 只需拷贝一段数据到/从 native buffer |

**Region 调用通常更安全且足够快**。官方 JNI 文档明确推荐：如果目的只是复制数据，优先使用 `Get<Type>ArrayRegion` / `Set<Type>ArrayRegion`。

[已验证: 官方文档, https://developer.android.com/training/articles/perf-jni]

### GetPrimitiveArrayCritical 的特殊性

`GetPrimitiveArrayCritical()` 试图返回指向 Java 数组真实内存的指针，同时通知运行时"不要打扰我"。它和 `GetStringCritical()` 一样，要求调用方在释放前不得执行任何其他 JNI 调用。

关键风险：在 critical region 内，ART **无法移动**被持有的数组，也无法做某些 GC 操作。如果 native 侧在 critical region 内执行耗时操作（磁盘 I/O、网络等待、长时间计算），GC 会被阻塞，表现为整个进程的堆无法被整理。

Android 8+ 的 moving GC（concurrent copying GC, CC）使得 `GetPrimitiveArrayCritical()` 更可能返回拷贝而非内部指针——因为 CC 收集器需要能够移动对象，直接暴露内部指针的风险太大。

[已验证: 官方文档, https://developer.android.com/training/articles/perf-jni — "启用扩展 JNI 检查时，运行时会检测 critical 区域内的违规调用"]

## JNI Critical Region 与 ART GC 阻塞

### GC 暂停（Pause）的工作机制

ART 的 GC 需要一个"stop-the-world"窗口来执行某些关键阶段（mark root、flip、forward）。在这个窗口内，所有 Runnable 状态的线程必须在 safepoint 暂停。

线程在以下位置检查 safepoint：
- 方法入口/出口（compiled code 中插入的 suspend check）
- 回边（back-edge，循环跳回时）
- JNI 调用的状态切换点

当线程状态为 Native 时，GC 将其视为"已经暂停"——因为假定它不会访问 Java 堆。这带来一个推论：**JNI 调用执行时间越长，GC 等待该线程返回 Runnable 状态的时间就越久**。

### @FastNative / @CriticalNative 的 GC 阻塞风险

`@FastNative` 和 `@CriticalNative` 省去了线程状态切换，意味着线程在执行这些方法时**保持 Runnable 状态**。这对 GC 的影响是：

1. GC 在 safepoint 请求暂停后，必须等到线程到达下一个 safepoint 检查点
2. 处于 `@FastNative`/`@CriticalNative` 执行中的线程不会主动检查 safepoint（因为没经过标准的状态切换路径）
3. 如果方法执行时间很长，GC 会被阻塞，其他线程的分配请求也会被阻塞

ART 内部通过 `Thread::state_and_flags` 的原子读写来实现状态切换。普通 JNI trampoline 使用 `stlxr`/`ldaxr` 指令（ARM64 排他存储/加载）来原子地更新线程状态，并在返回时检查 `is_gc_marking` flag。`@FastNative` trampoline 跳过了这个原子序列，但在返回时仍会检查 `state_and_flags` 以确认是否有挂起请求。

[已验证: AOSP android-17.0.0_r1, art/runtime/thread.h — `state_and_flags` 字段定义及 safepoint 机制]

### PNR（Pause Not Responding）风险

当 GC 暂停超时（通常 > 5s），系统会触发 PNR 告警，表现为 ANR 类似的用户体验。一个常见场景：

1. 音频回调线程每 10ms 通过 JNI 调用一次 native 解码函数
2. 某次解码因锁竞争变慢，耗时 8s
3. GC 请求暂停，但音频线程处于 Native 状态（或标注了 `@FastNative`），GC 等不到 safepoint
4. 其他线程因 GC 未完成而无法分配内存，大面积卡住
5. 系统 ANR/PNR 触发

这解释了为什么官方文档反复强调：**`@FastNative`/`@CriticalNative` 只适合很短、很确定、不会阻塞的 native 路径**。文档没有给出阈值（不说"50μs 以下可以用"），因为正确的判断标准是"方法内部是否会等锁、等 I/O、执行不可预期时间的系统调用"。

[已验证: 官方文档, https://developer.android.com/reference/dalvik/annotation/optimization/CriticalNative — "These annotations should not be used for long-running methods"]

## Local Reference / Global Reference 管理与泄漏

### 三种引用类型

| 类型 | 创建方式 | 生命周期 | 自动释放 |
| --- | --- | --- | --- |
| Local Reference | JNI 函数返回的对象、`NewLocalRef` | 当前 native 方法调用期间 | 方法返回时由运行时释放 |
| Global Reference | `NewGlobalRef` | 直到 `DeleteGlobalRef` | 否 |
| Weak Global Reference | `NewWeakGlobalRef` | 直到 `DeleteWeakGlobalRef` 或对象被 GC 回收 | 否 |

### Local Reference Table 溢出

JNI 规范只要求实现至少保留 **16 个** local reference slot。Android 8.0+ 放宽了这个限制（支持"无限"local reference），但仍然需要管理。

典型的溢出场景：

```c
// 危险：循环内创建 local reference 但不释放
for (int i = 0; i < 10000; i++) {
    jstring str = env->NewStringUTF(items[i]);
    env->CallVoidMethod(callback, onItem, str);
    // str 在这里已经没用了，但 local reference 不会被自动释放
    // 因为方法还没返回
}
```

正确做法：

```c
for (int i = 0; i < 10000; i++) {
    jstring str = env->NewStringUTF(items[i]);
    env->CallVoidMethod(callback, onItem, str);
    env->DeleteLocalRef(str);  // 显式释放
}
```

或者使用 `PushLocalFrame()` / `PopLocalFrame()` 批量管理：

```c
if (env->PushLocalFrame(256) == 0) {
    for (int i = 0; i < 10000; i++) {
        jstring str = env->NewStringUTF(items[i]);
        env->CallVoidMethod(callback, onItem, str);
    }
    env->PopLocalFrame(NULL);  // 一次性释放所有 local reference
}
```

[已验证: 官方文档, https://developer.android.com/training/articles/perf-jni]

### Attached 线程的特殊风险

通过 `AttachCurrentThread()` 挂入 JVM 的 native 线程有一个关键差异：**local reference 不会在方法返回时自动释放**，因为"方法返回"的概念不适用于 attached 线程——它没有 Java 调用栈帧。

这意味着，attached 线程中创建的所有 local reference 会一直存在，直到线程调用 `DetachCurrentThread()`。

正确模式（推荐使用 `pthread_key_create` 自动清理）：

```c
static pthread_key_t jni_env_key;

void jni_env_destructor(void* data) {
    JavaVM* vm = (JavaVM*) data;
    vm->DetachCurrentThread();
}

void native_thread_init(JavaVM* vm) {
    pthread_key_create(&jni_env_key, jni_env_destructor);
    // ...
}

void native_thread_entry(JavaVM* vm) {
    JNIEnv* env;
    vm->AttachCurrentThread(&env, NULL);
    pthread_setspecific(jni_env_key, vm);
    // 线程退出时 destructor 会自动调用 DetachCurrentThread
    // 从而释放所有 local reference
}
```

[已验证: 官方文档, https://developer.android.com/training/articles/perf-jni — "在已附加的线程上调用 AttachCurrentThread() 属于空操作"]

### Global Reference 泄漏的线上检测

Global Reference 泄漏比 local reference 隐蔽——不会 crash，但会持续占用内存并阻止 GC 回收对象。Android Studio 的 Memory Profiler 提供 JNI heap 视图，可以查看所有 global reference 及其创建位置。

对线上监控，可以通过反射读取 `Debug.getGlobalAllocCount()` 和 `Debug.getGlobalFreedCount()` 的差值来判断 global reference 是否在持续增长。差值持续上升且不回落，几乎一定是某处忘记 `DeleteGlobalRef`。

[已验证: 官方文档, https://developer.android.com/studio/profile/memory-profiler#jni-references]

## JNI 线程 attach / detach 开销与 ThreadLocal 管理

### attach 的成本

`AttachCurrentThread()` 不是零成本。它需要：

1. 创建 `Thread` 对象并注册到运行时的线程列表
2. 分配 `JNIEnvExt` 结构体（包含 local reference table、monitor table 等）
3. 设置 thread-local storage
4. 将线程加入 `ThreadGroup`（使调试器可见）

对于频繁创建/销毁的 native 线程，每次 attach/detach 的成本会累积。更严重的是，attached 线程创建的 `Thread` 对象本身也是 GC Root，如果线程没有正确 detach，这个 `Thread` 对象和它的 `JNIEnvExt` 都会泄漏。

### 推荐的线程管理模式

**模式 A：长期存活的工作线程**

```c
// 线程启动时 attach，线程退出时 detach
void worker_thread_entry(JavaVM* vm) {
    JNIEnv* env;
    vm->AttachCurrentThread(&env, "worker-thread");
    // ... 长期工作 ...
    vm->DetachCurrentThread();
}
```

**模式 B：线程池 + 复用**

线程池中的工作线程长期存活，只在首次获取任务时 attach，线程被回收前 detach。任务之间复用同一个 `JNIEnv`。注意：任务间创建的 local reference 需要手动清理，因为不会自动释放。

**反模式：每个任务 attach/detach**

```c
// 危险：每个任务都 attach/detach
void process_task(JavaVM* vm, Task* task) {
    JNIEnv* env;
    vm->AttachCurrentThread(&env, NULL);
    // 处理任务
    vm->DetachCurrentThread();
}
```

如果任务粒度很小（比如每个音频帧一次），attach/detach 的开销可能超过任务本身。正确做法是把线程生命周期和 attach/detach 绑定，而不是和任务绑定。

[已验证: 官方文档, https://developer.android.com/training/articles/perf-jni — "尽可能减少需要接触 JNI 或被 JNI 接触的线程数"]

### Java 层创建线程 vs Native 层创建线程

从 Java 层 `Thread.start()` 创建的线程：
- 由 ART 管理，自动有 `JNIEnv`
- 堆栈大小由 `Thread` 构造参数控制
- 属于正确的 `ThreadGroup`
- 使用与创建者相同的 `ClassLoader`

从 Native 层 `pthread_create()` 创建的线程：
- 需要手动 `AttachCurrentThread()`
- 堆栈大小由 `pthread_create` 参数决定
- `FindClass()` 可能因 class loader 问题失败（详见 §1.15）
- 线程名需要通过 `pthread_setname_np()` 单独设置

对需要在 native 回调 Java 的场景，优先从 Java 层创建线程，除非有明确的 native 栈大小或优先级控制需求。

## Android 17 ART JNI 内联优化与 16KB page size 影响

### Android 17 的 JNI 相关变化

基于 `android-17.0.0_r1` 源码核查，ART 在 JNI 路径上的核心机制（trampoline 结构、`@FastNative`/`@CriticalNative` 语义、线程状态机）与 Android 14-16 保持一致。没有引入新的 JNI 注解类型，也没有改变 `GetPrimitiveArrayCritical` 的约束模型。

需要注意的变化集中在两个方向：

1. **ART Module 独立更新**：自 Android 12 起，ART 作为 Mainline Module 可以独立于系统版本更新。这意味着同一 `android-17.0.0_r1` tag 上的 ART 行为，可能因设备厂商推送的 ART Module 更新而不同。对 JNI 性能测试，应确认设备的 ART Module 版本（`adb shell cmd package list apks | grep com.google.android.art`）。

2. **16KB page size 强制执行**：Android 15 引入 16KB 支持，2025 年 11 月起 Google Play 对 targeting Android 15+ 的 64 位提交强制要求。Android 17 设备普遍启用 16KB page size。对 JNI 的影响：
   - native 库必须 16KB 对齐（否则加载失败）
   - `mmap` 的页边界从 4KB 变为 16KB，影响 native 内存映射的粒度
   - TLB 命中率改善的收益主要在数据面（如 JNI 传引用的大 buffer），不在 JNI transition 本身

[已验证: AOSP android-17.0.0_r1, art/runtime/ — JNI 核心机制未变]
[已验证: 官方文档, https://developer.android.com/guide/practices/page-sizes — 16KB 合规要求时间线]

### ART AOT/JIT 与 JNI trampoline 的协同

`@FastNative`/`@CriticalNative` 的加速效果依赖编译模式：

| 执行模式 | 普通 JNI trampoline | @FastNative trampoline | @CriticalNative |
| --- | --- | --- | --- |
| 解释执行 | 通用 trampoline（~5120B 栈预留） | 通用 trampoline（注解被解释器部分利用） | 通用 trampoline（注解被解释器部分利用） |
| JIT 编译 | compiler trampoline（~176B 栈帧） | 精简 trampoline（省状态切换） | 极简 trampoline（~4 行汇编） |
| AOT 编译 | 同 JIT | 同 JIT | 同 JIT |

关键推论：`@CriticalNative` 的最大收益在 AOT/JIT 编译模式下。解释执行时，注解的效果有限。这意味着：
- 冷启动阶段（大量方法未编译）的 JNI 调用仍走解释器，收益不明显
- 将包含 `@CriticalNative` 调用的代码路径加入 Baseline Profile，能确保 AOT 编译，最大化注解收益

[结构参考: Cubox/ART 虚拟机 - JNI 优化简史-2023-06-27.md — "相同参数类型的不同方法共用一个 trampoline"]
[已验证: 官方文档, https://developer.android.com/reference/dalvik/annotation/optimization/CriticalNative — 建议调用方加入 Baseline Profile]

### Compiler Trampoline 的共享机制

一个重要但容易被忽略的细节：compiler trampoline 是按参数类型共享的，不是按方法共享的。两个参数类型相同的 native 方法（如都是 `(String, int)`），即使业务含义完全不同，在 AOT 产物（`.oat` 文件）中共用同一个 trampoline 二进制代码。

通过 `oatdump` 可以验证：不同方法指向同一个 `code_offset`。这意味着：
- 将更多 native 方法加入 Baseline Profile 的 code size 增量很小
- 但每个方法仍需各自的方法入口（`OatMethodOffsets`）
- 这个共享机制从 Android 8 持续到 Android 17 未变

[结构参考: Cubox/ART 虚拟机 - JNI 优化简史-2023-06-27.md — oatdump 输出验证]

## JNI 性能分析：Perfetto JNI trace 与 systrace 插桩

Perfetto 不会自动为每次 JNI 调用生成命名的 slice。要看 JNI 热路径，需要配合手工插桩和采样。详见 §1.15 中关于"Perfetto 中的 JNI 可观测性有三条路"的完整说明，这里只补充 §1.15 未覆盖的实战要点。

### JNI 调用计数的工程化方法

在不知道 JNI 调用频率是否过高时，先量化次数而不是单次开销：

1. **Build 期插桩**：在 debug build 中，用 ASM 或 Jacoco 在每个 `native` 方法调用前后插入计数器。适用于初次摸底，不适合线上。

2. **Perfetto callstack 采样**：以 1000Hz 采样频率抓取 callstack，统计 `art_jni_trampoline`、`Java_` 前缀符号出现的频率。能定位热点方法，但不能给出精确调用次数。

3. **simpleperf stat 模式**：`simpleperf stat -e raw-faults,cpu-cycles -p <pid>` 收集运行时硬件计数器，间接反映 native 执行时间占比。

### JNI 热路径的 Trace 插桩模式

对已确认的热路径，推荐的插桩方式：

```c
// NDK 侧
#include <android/trace.h>

void process_audio_frame(JNIEnv* env, jbyteArray data) {
    ATrace_beginSection("jni:process_audio_frame");
    
    jbyte* buffer = env->GetByteArrayElements(data, NULL);
    // ... 处理 ...
    env->ReleaseByteArrayElements(data, buffer, 0);
    
    ATrace_endSection();
}
```

```kotlin
// Java/Kotlin 侧
fun processFrame(data: ByteArray) {
    android.os.Trace.beginSection("jni:processFrame")
    nativeProcessFrame(data)
    android.os.Trace.endSection()
}
```

两侧同时插桩，可以在 Perfetto 的同一个线程轨上看到 Java 侧和 native 侧的 slice 拼接。如果 native slice 远大于 Java 侧的 transition 时间，说明开销在算法而非 JNI 边界；反之则需要优化接口设计。

[已验证: AOSP android-17.0.0_r1, frameworks/native/include/android/trace.h — `ATrace_beginSection`/`ATrace_endSection` 公开 API]

### systrace 和 Perfetto 的 JNI 证据链

历史上 `systrace.py` 工具已被官方标记为 deprecated（Android 10 之后），替换为 Perfetto。如果还在用 systrace 抓 JNI 数据，应该迁移到 Perfetto 的 `record_android_trace` 或直接用 `adb shell perfetto`。

Perfetto 的 SQL 查询（详见 §13.22 Perfetto SQL 查询手册）可以统计 JNI 相关 slice 的聚合数据：

```sql
-- 统计自定义 JNI section 的总耗时和调用次数
SELECT
  name,
  COUNT(*) as call_count,
  SUM(dur) / 1e6 as total_ms,
  AVG(dur) / 1e3 as avg_us
FROM slice
WHERE name LIKE 'jni:%'
GROUP BY name
ORDER BY total_ms DESC;
```

## JNI 批量化调用模式设计

减少 JNI 调用次数是最有效的优化手段，但接口设计往往受限于业务模型。几种常见的批量化模式：

**模式 A：数据批量传递**

```c
// 反模式：每个元素一次 JNI
for (int i = 0; i < count; i++) {
    env->CallVoidMethod(callback, onSample, samples[i]);
}

// 批量化：一次传递整个数组
env->CallVoidMethod(callback, onSamples, samplesArray, count);
```

**模式 B：命令缓冲区**

将多个 JNI 操作打包成一个"命令列表"，一次 JNI 调用提交执行：

```c
struct NativeCommand {
    int type;     // 操作类型
    int arg1;
    long arg2;
};

void flush_commands(JNIEnv* env, jobject dispatcher, 
                    NativeCommand* cmds, int count) {
    // 一次 JNI 调用处理 count 个命令
    // ...
}
```

这种模式在游戏引擎（Unity/Unreal 的 Java bridge）中很常见，适合高频、小粒度的操作。

**模式 C：DirectByteBuffer 共享内存**

对大块数据的双向传输，用 `ByteBuffer.allocateDirect()` 在 native 堆分配内存，Java 和 native 共享同一块缓冲区，完全绕过 JNI 的数组拷贝路径：

```kotlin
// Java 侧
val buffer = ByteBuffer.allocateDirect(4096)
nativeSetBuffer(buffer)  // 一次 JNI 调用建立映射

// 之后 native 侧直接读写 buffer，不需要再过 JNI
```

```c
// Native 侧
static uint8_t* shared_buffer;

JNIEXPORT void JNICALL nativeSetBuffer(JNIEnv* env, jobject thiz, jobject buf) {
    shared_buffer = (uint8_t*) env->GetDirectBufferAddress(buf);
}
```

DirectByteBuffer 的代价是分配/回收成本高（涉及 native 内存分配），适合池化复用。详见 §1.15 中关于 DirectByteBuffer 的讨论。

[已验证: 官方文档, https://developer.android.com/training/articles/perf-jni — "尽量减少跨 Java 层与 native 调用次数"]

## Native 线程创建开销（pthread_create 成本拆解）

[待补充: 本节扩展点涉及 native 线程创建的 CPU/内存开销量化分析（stack 分配、TLS 初始化、kernel clone 系统调用等），当前轮次素材不足，留待后续补充。]

## AOSP JNI 性能 benchmark 参考

[待补充: 本节扩展点涉及 AOSP 源码树中的 JNI benchmark（`art/runtime/jni/jni_benchmark.cc` 等）的运行方法和基线数据，当前轮次素材不足，留待后续补充。]

## 版本演进

| Android 版本 | JNI 相关变化 |
| --- | --- |
| Android 8 (API 26) | `@FastNative`/`@CriticalNative` 在系统内部引入；Local Reference 上限取消（Android 8.0+） |
| Android 9 (API 28) | ART concurrent copying GC 正式启用，`GetPrimitiveArrayCritical` 更可能返回拷贝 |
| Android 12 (API 31) | 内建 dynamic JNI linking 对 `@FastNative`/`@CriticalNative` 完整支持 |
| Android 14 (API 34) | `@FastNative`/`@CriticalNative` 成为 CTS-tested public API |
| Android 15 (API 35) | 16KB page size 支持，Google Play 强制要求 targeting Android 15+ 的 64 位提交 |
| Android 16 (API 36) | 未发现新的公开 JNI annotation 语义变化 |
| Android 17 (API 37) | JNI 核心机制未变；ART Module 独立更新可能带来设备差异；16KB page size 在新设备上普遍启用 |

## 与其他章节的关系

- **§1.15 JNI/NDK 性能优化**：本节的总纲，涵盖 `@FastNative`/`@CriticalNative` 通用准则、字符串/数组/DirectByteBuffer 选型、16KB page size 对 NDK 的影响
- **§8.11 Native 库加载与动态链接性能**：Bionic linker 加载 `.so` 的流程、Linker Namespace、16KB 对齐检查
- **§8.19 端到端触控延迟优化实战**：输入事件管线中的 native 调用路径
- **§13.22 Perfetto SQL 查询手册**：JNI 相关 slice 的聚合查询方法

## 参考资料

- 官方文档
  - `https://developer.android.com/training/articles/perf-jni` — JNI 性能提示
  - `https://developer.android.com/reference/dalvik/annotation/optimization/FastNative` — @FastNative 参考
  - `https://developer.android.com/reference/dalvik/annotation/optimization/CriticalNative` — @CriticalNative 参考
  - `https://developer.android.com/guide/practices/page-sizes` — 16KB page size 指南
  - `https://developer.android.com/studio/profile/memory-profiler#jni-references` — JNI 引用监控
- AOSP 源码路径（android-17.0.0_r1）
  - `art/runtime/native_entry_points.h` — ART native 方法入口点定义
  - `art/runtime/jni/jni_env_ext.h` — JNIEnv 扩展结构
  - `art/runtime/thread.h` — Thread 状态机和 `state_and_flags` 字段
  - `art/runtime/arch/arch_jni_frame.h` — JNI 栈帧布局
  - `frameworks/base/core/java/android/os/Parcel.java` — @FastNative 使用示例
  - `frameworks/base/core/java/android/os/Binder.java` — @CriticalNative 使用示例
  - `frameworks/native/include/android/trace.h` — ATrace_beginSection / ATrace_endSection
- 研究素材
  - `intake/research-feeds/2026-04-07-19-art-fastnative-criticalnative-jni-optimization.md`
  - `intake/research-feeds/2026-04-07-11-android-16kb-page-size-jni-native-library-quantification.md`
  - `[结构参考: Cubox/ART 虚拟机 - JNI 优化简史-2023-06-27.md]`
  - `[结构参考: Cubox/Android C++系列：JNI开发准则 - 掘金-2022-04-21.md]`
