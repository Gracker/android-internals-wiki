---
title: JNI、NDK 与 Bionic 原生运行时性能
chapter: '1.6'
section: '1.6'
status: finalized
applicable_versions: Android 1.0 (API 1) - Android 17 (API 37)
last_verified: '2026-08-23'
last_verified_against: AOSP android-17.0.0_r1
confidence: high
sources:
- type: official
  path: https://developer.android.com/ndk/guides/jni-tips
- type: official
  path: https://developer.android.com/reference/dalvik/annotation/optimization/FastNative
- type: official
  path: https://developer.android.com/reference/dalvik/annotation/optimization/CriticalNative
- type: official
  path: https://developer.android.com/guide/practices/page-sizes
- type: official
  path: https://developer.android.com/ndk/guides/simpleperf
- type: official
  path: https://perfetto.dev/docs/getting-started/other-formats#simpleperf-proto-format
- type: spec
  path: https://docs.oracle.com/en/java/javase/25/docs/specs/jni/
- type: aosp
  path: frameworks/base/core/java/android/os/Binder.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/os/Parcel.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/os/SystemProperties.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/os/Trace.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/native/include/android/trace.h @ android-17.0.0_r1
- type: aosp
  path: system/core/libcutils/include/cutils/trace.h @ android-17.0.0_r1
- type: aosp
  path: system/core/libutils/include/utils/Trace.h @ android-17.0.0_r1
- type: aosp
  path: system/extras/simpleperf/doc/view_the_profile.md @ android-17.0.0_r1
- type: aosp
  path: bionic/README.md (android-17.0.0_r1)
- type: aosp
  path: bionic/libc/Android.bp (android-17.0.0_r1)
- type: aosp
  path: bionic/libc/bionic/malloc_common.cpp, malloc_common_dynamic.cpp (android-17.0.0_r1)
- type: aosp
  path: bionic/libc/bionic/pthread_create.cpp, pthread_attr.cpp, pthread_mutex.cpp, pthread_cond.cpp (android-17.0.0_r1)
- type: aosp
  path: bionic/libc/platform/bionic/page.h, tls.h, tls_defines.h (android-17.0.0_r1)
- type: aosp
  path: bionic/linker/linker_phdr.cpp, linker_phdr.h (android-17.0.0_r1)
- type: aosp
  path: bionic/libc/arch-arm64/ifuncs.cpp (android-17.0.0_r1)
- type: aosp
  path: external/scudo/standalone/allocator_config.h (android-17.0.0_r1)
- type: kernel
  path: kernel/futex/, Documentation/arch/arm64/memory-tagging-extension.rst (android17-6.18-2026-06_r6)
- type: official
  path: developer.android.com/guide/practices/page-sizes
- type: official
  path: source.android.com/docs/security/test/scudo
- type: official
  path: source.android.com/docs/security/test/memory-safety/arm-mte
tags:
- android
- jni
- ndk
- art
- fastnative
- criticalnative
- 16kb-page-size
- simpleperf
- bionic
- libc
- malloc
- scudo
- mte
- 16kb-page
- pthread
- arm64
related_chapters:
- '1.5'
- '4.2'
- '15.2'
- '4.10'
- '23.3'
- '20.11'
- '4.5'
- '20.13'
pipeline_stage: ready-to-publish
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part2-performance/ch08-responsiveness/20-jni-overhead-native-interop-performance.md
- src/part1-fundamentals/ch01-architecture/15-jni-ndk-performance.md
- src/part1-fundamentals/ch01-architecture/39-bionic-libc-performance.md
---

# JNI、NDK 与 Bionic 原生运行时性能

JNI（Java Native Interface，Java 原生接口）用于在 Java/Kotlin 与 C/C++ 之间调用代码；NDK（Native Development Kit）提供 Android 原生开发工具链。优化 JNI 时，应优先减少跨语言调用次数和数据编组，也就是参数在两侧表示之间的转换，并正确管理线程与引用生命周期。继续压缩单次边界切换（transition）的十几纳秒，应排在这些工作之后。

音视频、图像、游戏和设备端 AI 推理经常需要 C/C++，但“原生代码天生比 Java/Kotlin 快”不是可靠结论。一个原本能被 ART 即时编译（JIT）或运行前编译（AOT）优化的短循环，如果被拆成大量小粒度 JNI 调用，再叠加字符串转换、数组复制、引用管理和异常检查，整体可能更慢。

分析 JNI 路径时，把成本拆成四段：

```text
Managed caller
  └─ JNI transition
      ├─ 参数与引用处理
      ├─ Native 业务计算 / I/O / 锁
      └─ 返回值、异常与引用清理
          └─ Managed caller 继续执行
```

这里的“托管代码”指由 ART 管理内存和线程状态的 Java/Kotlin 代码，“原生代码”指 C/C++。分析时应区分 JNI 边界本身的成本与原生函数内部的成本，避免选错优化位置。

Native 性能问题通常跨过 Java/Native 调用边界、动态链接器和 libc 实现。JNI 决定参数转换与线程附着成本，Bionic 决定常用系统接口、分配器和同步原语在 Android 上的具体行为。

## JNI 边界与 Native 调用成本

### 1. JNI 成本来自哪里

#### 1.1 边界切换

普通 JNI 调用需要通知 ART：线程将从托管代码状态进入原生代码状态。随后，调用按 JNI 的二进制调用约定（ABI）传递 `JNIEnv*`、`jobject` / `jclass` 和业务参数；返回时再恢复运行时状态，处理引用和异常。

Android 17 中，普通入口会经过 ART 的 JNI 跳板代码（trampoline），为本次调用建立本地引用区段（local-reference segment），并把线程从可运行的 `Runnable` 状态切换到执行原生代码的 `Native` 状态。返回时，线程再恢复 `Runnable`，检查运行时挂起请求和待处理的 Java 异常（pending exception）。对象参数还要放入引用表，并在原生侧解析为实际对象；纯基本类型（primitive）参数没有这层对象引用处理。因此，一次 JNI 调用并非一条固定指令，方法属性、参数类型、编译状态和运行时挂起请求都会改变执行路径。

`@FastNative` 与 `@CriticalNative` 让线程保持 `Runnable` 状态，省去普通 JNI 状态切换，但也推迟了线程响应垃圾回收暂停请求（GC suspend）的机会。`@CriticalNative` 进一步去掉 `JNIEnv*`、`jclass` 和对象参数能力。它们只适合调用链末端那些极短、无锁、无 I/O 的叶子函数，也就是不会再调用其他函数的末端实现。长计算即使平均耗时更短，也可能延长 GC 在 P95/P99 等尾部样本中的暂停时间。

官方 `@CriticalNative` 文档保留了一组 2016 年 7 月、`angler-userdebug` 上的参考数据：

| 路径 | 官方参考值 |
| --- | ---: |
| 普通 JNI | 115ns |
| `@FastNative` | 35ns |
| `@CriticalNative` | 25ns |

这些数字只说明当时设备上的相对量级。芯片、ART 版本、调用方处于解释执行、JIT 还是 AOT、编译选项和方法签名都会改变结果，不能把 115ns 当作 Android 17 设备的固定常数。

调用次数会累积边界切换开销。按这组旧参考值计算，1000 次普通 JNI 调用约为 115μs，真实路径还要加上参数处理和原生工作。相比争论 35ns 与 25ns 的差异，先把一帧内 1000 次调用合并成 1 次通常更有价值。

#### 1.2 数据编组与复制

基本类型标量的传递最直接；`String`、数组和普通 Java 对象都需要运行时参与。

- `String` 可能发生 UTF-16 / Modified UTF-8 转换和复制。
- 基本类型数组可能直接暴露指针，也可能复制到原生缓冲区。
- 对象字段和方法需要 `jfieldID` / `jmethodID`。
- 原生代码回调 Java 又产生一次反向边界切换。
- `DirectByteBuffer` 可让原生代码直接访问地址，但必须明确内存所有权与生命周期。

很多所谓“JNI 慢”来自数据表示在两侧来回转换。

#### 1.3 原生函数内部

JNI 只负责跨语言调用。进入原生函数后，锁、I/O、内存分配、算法复杂度和缓存未命中仍要按普通 C/C++ 性能问题处理。

`SystemProperties.java` 在 `android-17.0.0_r1` 里留下了一个很好的边界示例：

```java
// _NOT_ FastNative: native_set performs IPC and can block
private static native void native_set(String key, String def);
```

这个方法会执行 IPC，并且可能阻塞，所以没有使用 `@FastNative`。即使边界切换变快，调用方实际经历的阻塞时间也不会因此消失。

### 2. 第一原则：减少小粒度 JNI 调用

官方 JNI tips 把“减少跨 JNI 编组的数据量与频率”放在通用建议首位。工程上可以从三个方向做。

#### 2.1 批量传输

下面的对比说明为什么应按批次传递数据，而不是为每个元素调用一次原生方法：

```text
差：4096 次 JNI，每次传 1 个 short
好：1 次 JNI，传 short[] / DirectByteBuffer / native handle
```

批量传输也不意味着无条件复制 100MB 数据。接口设计要看数据主要由哪一侧访问：

- Java/Kotlin 侧读写更多：基本类型数组通常更自然；
- C/C++ 侧长期处理：由原生代码拥有的缓冲区，或直接缓冲区（direct buffer）更合适；
- 两侧只传控制信息：可以传 `long` 形式的原生句柄，但必须防止句柄指向的对象已释放、重复释放和跨实例误用。

#### 2.2 少做跨语言异步回调

如果 Java 线程池与原生线程池为每个任务相互回调，线程附着、引用和生命周期管理就会分散到大量工作线程。更容易维护的设计是让其中一侧统一管理异步状态，JNI 只在边界传递批量输入和少量完成事件。

UI 更新通常留在托管代码侧：后台 Java/Kotlin 线程执行一次阻塞式原生调用，结束后回到主线程发布结果，比原生工作线程高频回调 UI 层更简单。

#### 2.3 缓存类、字段与方法 ID

`FindClass()`、`GetMethodID()`、`GetFieldID()` 会做查找，不应放在高频循环里。缓存时要分清两类值：

- `jmethodID` / `jfieldID` 是供 JVM 识别成员的不透明 ID，不是 Java 对象引用，不能传给 `NewGlobalRef()`；
- `jclass` 属于 `jobject`，从 `FindClass()` 得到的是本地引用（local reference）；跨调用保存前，必须转成全局引用（global reference）。

下面的 `JNI_OnLoad()` 示例在动态库加载时缓存类的全局引用和方法 ID：

```cpp
static jclass gDecoderClass = nullptr;
static jmethodID gOnFrameReady = nullptr;

JNIEXPORT jint JNI_OnLoad(JavaVM* vm, void*) {
    JNIEnv* env = nullptr;
    if (vm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6) != JNI_OK) {
        return JNI_ERR;
    }

    jclass local = env->FindClass("com/example/Decoder");
    if (local == nullptr) {
        return JNI_ERR; // ClassNotFoundException 仍处于 pending 状态
    }

    gDecoderClass =
            reinterpret_cast<jclass>(env->NewGlobalRef(local));
    env->DeleteLocalRef(local);
    if (gDecoderClass == nullptr) {
        return JNI_ERR;
    }

    gOnFrameReady =
            env->GetMethodID(gDecoderClass, "onFrameReady", "(J)V");
    if (gOnFrameReady == nullptr) {
        env->DeleteGlobalRef(gDecoderClass);
        gDecoderClass = nullptr;
        return JNI_ERR;
    }
    return JNI_VERSION_1_6;
}
```

示例会删除临时本地引用，并在任何查找失败时返回 `JNI_ERR`。如果类可能随自定义类加载器（`ClassLoader`）卸载并重新加载，更稳妥的方案是从该 Java 类的静态初始化器调用 `nativeInit()`，在类每次初始化时重建缓存。无论采用哪种方式，全局引用不再使用时都要调用 `DeleteGlobalRef()`。

### 3. ClassLoader：原生线程的 `FindClass()` 为什么常失败

`JNI_OnLoad()` 是动态库加载时调用的特殊入口。ART 会使用发起 `.so` 加载的类所对应的 `ClassLoader`；因此，应用调用 `System.loadLibrary()` 时，通常可以在这里找到应用自己的类。

普通 JNI 调用中，`FindClass()` 使用 Java 调用栈顶部方法对应的 `ClassLoader`。问题通常出现在由原生代码创建的线程：

1. `pthread_create()` / `std::thread` 创建线程。
2. 线程通过 `AttachCurrentThread()` 附着到 VM。
3. 当前调用栈中没有应用的 Java 栈帧；
4. `FindClass()` 回退到系统类加载器；
5. 系统类加载器不认识应用自己的类。

常用解法：

- 在 `JNI_OnLoad()` 或 Java 类初始化器中查找并缓存 `jclass` 全局引用；
- 由 Java 把 `Class` 实例传给原生代码；
- 缓存应用的 `ClassLoader`，需要时调用其 `loadClass()`。

不要在原生工作线程的高频路径中反复调用 `FindClass()`，这会同时带来性能和正确性风险。

### 4. `@FastNative` 与 `@CriticalNative`

两个注解都能减少托管代码与原生代码之间的切换成本，但二进制调用约定和使用范围不同。

| 维度 | 普通 JNI | `@FastNative` | `@CriticalNative` |
| --- | --- | --- | --- |
| 托管对象参数/返回值 | 支持 | 支持 | 不支持 |
| 实例方法隐式 `this` | 支持 | 支持 | 不支持，必须是静态方法 |
| 原生签名含 `JNIEnv*` | 是 | 是 | 否 |
| 原生签名含 `jobject` / `jclass` | 视方法而定 | 视方法而定 | 否 |
| 长 I/O / 可能长时间持有的原生锁 | 普通 JNI 仍应谨慎 | 禁止使用 | 禁止使用 |
| Android 14+ CTS 公共保证 | 普通 JNI | 是 | 是 |

#### 4.1 `@FastNative` 可以使用托管对象

Android 17 的 `Parcel.java` 直接提供了例子：

```java
@FastNative
private static native void nativeWriteString16(
        long nativePtr, String val);
```

`@FastNative` 仍有 `JNIEnv*`，可以访问托管堆、调用 JNI API，甚至回调 Java；但执行时间必须短，而且最坏耗时有明确上限。

官方文档说明，线程执行 `@FastNative` 时，GC 不能为关键工作挂起它。不要在里面：

- 做显著 I/O。
- 等待可能被长期持有的原生锁。
- 调用时长通常很短、但最坏情况无界的操作。
- 持有一把 Java 回调路径也可能取得的原生锁。

最后一种模式可能让 GC、Java 线程和 FastNative 线程形成环形等待并死锁。

#### 4.2 `@CriticalNative` 只能使用基本类型

Android 17 的 `Binder.java`：

```java
@CriticalNative
public static final native int getCallingUid();
```

`@CriticalNative` 不能有任何托管对象参数、返回值或隐式 `this`。数组也是对象，因此 `byte[]`、`int[]`、`String`、`ByteBuffer` 都不能出现在 CriticalNative 签名中。它适合基本类型标量，以及用 `long` 表示的原生句柄。

Java 声明如下：

```java
@CriticalNative
private static native int nativeWriteInt(long ptr, int value);
```

对应的 C/C++ 实现只接收业务参数：

```cpp
static jint NativeWriteInt(jlong ptr, jint value) {
    // 没有 JNIEnv*，也没有 jclass。
    return 0; // 仅示意 ABI；真实实现应返回写入结果
}
```

两段代码的参数按位置直接对应，不包含 `JNIEnv*` 或 `jclass`。没有 `JNIEnv*` 意味着实现中不能调用 JNI API。CriticalNative 同样会阻止 GC 为关键工作挂起当前线程，因此只适合短、可预测且不阻塞的代码。

#### 4.3 注解之外还有兼容性要求

官方当前口径：

- Android 8 起用于系统内部。
- Android 14 / API 34 起成为通过兼容性测试套件（CTS）验证的公共 API；
- 追求最大兼容性的应用不应在 Android 13 及以下版本调用这些注解方法；
- Android 8～10 没有内建动态原生方法查找，Android 11 还有已知问题；Android 8～11 必须显式调用 `RegisterNatives()`；
- Android 7 及以下忽略注解；CriticalNative 因 ABI 不匹配可能错误编组参数并崩溃。

即使只支持 Android 14 及以上版本，官方仍建议性能关键方法使用 `RegisterNatives()`：这样，签名错误会在库加载时暴露，只需导出 `JNI_OnLoad()`，也不必等到首次调用时再由 `dlsym()` 按符号名称查找。

#### 4.4 Baseline Profile 的角色

Baseline Profile 是随应用提供的一份高频方法清单，帮助 ART 提前编译这些方法。JNI 边界切换很快，不代表托管代码调用方已经优化。如果启动阶段频繁执行、显著影响总耗时的路径仍处于解释执行或 JIT 预热阶段，调用方耗时可能掩盖 JNI 差异。把稳定的高频调用方纳入 Baseline Profile，可以让比较聚焦于 JNI 与原生工作，减少首次编译的干扰。

Baseline Profile 不会自动合并 JNI 调用，也不会把不符合条件的方法变成 CriticalNative；它解决的是托管代码调用方的编译状态。

### 5. 线程附着与 `JNIEnv*`

#### 5.1 `JNIEnv*` 只能属于当前线程

`JNIEnv*` 包含当前线程在虚拟机中的本地状态，只能由所属线程使用，不能存入全局变量供其他线程复用。可在进程内跨线程共享的是 `JavaVM*`，各线程再通过它取得自己的 `JNIEnv*`。

原生代码需要取得当前线程的 JNI 环境时：

1. 用 `JavaVM::GetEnv()` 查询当前线程是否已经附着到虚拟机；
2. 尚未附着且需要调用 JNI 时，使用 `AttachCurrentThread()` 或 `AttachCurrentThreadAsDaemon()`；
3. 线程退出前调用 `DetachCurrentThread()`。

对已经附着的线程再次调用 attach 不会重复附着，只会直接返回当前环境；但也不应在每个小任务前后反复执行。附着与分离（attach/detach）应和操作系统线程的生命周期绑定。

如果线程本来就要频繁回调 Java，优先考虑通过 Java 的 `Thread.start()` 创建。这样能自然获得合适的栈大小、线程组（ThreadGroup）、类加载器和调试工具中的可见性。

#### 5.2 原生线程的本地引用不会按“调用返回”清理

普通原生方法返回 Java 时，本次调用创建的本地引用会失效并被清理。通过 `AttachCurrentThread()` 附着的纯原生线程可能长期不返回 Java；它创建的本地引用要到线程分离时才会自动释放。

循环里创建 `jstring`、对象或数组元素时要：

- 每轮调用 `DeleteLocalRef()`；
- 或使用 `PushLocalFrame()` / `PopLocalFrame()` 管理一批引用；
- 必要时使用 `EnsureLocalCapacity()` 预留容量。

JNI 规范只要求虚拟机保证至少 16 个本地引用槽位。Android 8 移除了旧的固定小容量限制，Android 17 的本地引用表（Local Reference Table）可以扩容，但初始存储和后续扩容仍会消耗进程资源；“可以扩容”不代表可以无限创建引用。长循环应优先按批次使用 `PushLocalFrame()` / `PopLocalFrame()`，并保证提前退出和异常路径也会弹出本地引用帧。

#### 5.3 Attach、Detach 与操作系统线程的生命周期

首次调用 `AttachCurrentThread()` 不只是返回一个指针。ART 还要建立 `Thread`、`JNIEnvExt`、本地引用表、与原生线程配对的 Java `Thread` 对象、线程组和运行时登记。已经附着的线程再次调用会返回当前环境，但把附着与分离放进每个小任务，仍会增加生命周期管理的复杂度。

可靠的做法是让一个明确的组件管理长期运行的操作系统线程或有上限的线程池：线程入口先调用 `GetEnv()`，只在线程由该组件首次附着时记录 `attached_here=true`，退出时也只分离这类线程。用于在 C++ 作用域结束时自动清理资源的 RAII 对象，其生命周期必须覆盖整个操作系统线程，而不能只覆盖线程池中的单个任务；`JNIEnv*` 永远不能跨线程保存。

原生线程本身也有成本。Android 17 的 bionic `pthread_create()` 要建立线程栈、栈保护页（guard）和线程本地存储（TLS）映射，再通过 `clone` 创建内核任务；首次访问栈页还会触发缺页。默认栈预留的虚拟地址空间不等于会占用同等大小的驻留物理内存（RSS），但高频创建线程仍会叠加内存映射、TLS、调度实体、ART 附着和缓存预热成本。应根据真实栈深度测量所需的栈大小并复用线程，这通常比为每个数据块创建一个 pthread 更可靠。

### 6. 引用、异常与所有权

#### 6.1 本地、全局与弱全局引用

- **本地引用（local reference）**：只在当前线程、当前 JNI 本地引用帧内有效；
- **全局引用（global reference）**：跨调用、跨线程保持对象可达，直到调用 `DeleteGlobalRef()`；
- **弱全局引用（weak global reference）**：不阻止 GC 回收对象。使用时应先调用 `NewLocalRef(weak)`，尝试把它提升为强本地引用；返回 `nullptr` 说明对象已经被回收。后续操作都使用这个本地引用，完成后再调用 `DeleteLocalRef()`。

两个 JNI 引用即使指向同一个 Java 对象，数值也可能不同。不能用 `==` 比较 `jobject`，应使用 `IsSameObject()`；也不能把原始 `jobject` 数值当作长期保存的映射表键。

不能先用 `IsSameObject(weak, nullptr)` 检查弱全局引用，再继续使用原弱引用：检查结束后，GC 仍可能立即回收对象。`NewLocalRef()` 的“提升并判空”会为本次操作建立一个稳定的强引用。

全局引用泄漏会让 Java 对象一直存活。Android Studio 的 JNI 堆视图（JNI heap view）可以查看全局 JNI 引用的创建位置和引用链。

#### 6.2 JNI 异常不会像 C++ 异常自动展开

许多 JNI API 失败时会设置待处理的 Java 异常（pending exception），并返回 `nullptr` 或其他表示失败的哨兵值（sentinel）。存在待处理异常后，只有少量 JNI 函数仍可安全调用。下面的代码在类或方法查找失败时立即返回，把异常留给 Java 调用方处理：

```cpp
jclass clazz = env->FindClass("com/example/Decoder");
if (clazz == nullptr) {
    // 此时通常已有待处理的 ClassNotFoundException。
    return;
}

jmethodID method =
        env->GetMethodID(clazz, "decode", "([B)I");
if (method == nullptr) {
    env->DeleteLocalRef(clazz);
    return;
}
```

两处分支都没有调用 `ExceptionClear()`。不能为了“继续运行”随意清除异常；只有原生代码明确要把 Java 异常转换成另一种结果或异常时才应清除，并且要确保 Java 侧仍能感知失败。

#### 6.3 用 CheckJNI 找错误，不用它测性能

CheckJNI 会检查：

- `JNIEnv*` 是否在错误线程使用；
- 引用与 ID 类型是否匹配；
- 存在待处理异常时，是否调用了不允许的 JNI API；
- 数组或字符串的 critical 获取与释放之间，是否调用了 JNI；
- Modified UTF-8 是否合法；
- 直接缓冲区参数、数组大小、释放模式等。

模拟器默认启用。普通设备可以在启动目标进程前设置：

```bash
adb shell setprop debug.checkjni 1
adb shell am force-stop com.example.app
```

CheckJNI 的额外检查会改变性能，不能用开启 CheckJNI 时采集的轨迹代表发布版本性能。应先用它消除 JNI 违规，再使用接近发布配置且保留符号的构建测量性能。

### 7. 字符串：UTF-16 与 Modified UTF-8

Java `String` 按 UTF-16 编码单元表示文本。JNI 中名称带 `UTF` 的 API 使用修改版 UTF-8（Modified UTF-8，MUTF-8），与网络、文件和大多数现代 C++ 库使用的标准 UTF-8 不完全相同。

- `GetStringChars()` / `GetStringRegion()` 面向 UTF-16。
- `GetStringUTFChars()` / `NewStringUTF()` 面向 Modified UTF-8。
- `GetStringLength()` 返回 UTF-16 编码单元（code unit）数量，不是 Unicode 码点（code point）数量；
- `GetStringUTFLength()` 返回的也不是标准 UTF-8 字节数。

不要把文件或网络收到的任意 UTF-8 直接交给 `NewStringUTF()`。无效 MUTF-8 会产生错误结果，CheckJNI 还会直接终止虚拟机进程。

Android 8 以后，ART 使用紧凑字符串表示，并采用可能移动对象位置的垃圾回收器（moving GC）。即使调用 `GetStringCritical()`，运行时也可能复制数据；API 名称中的 Critical 不代表承诺零拷贝。每个 `Get*Chars()` 都必须与对应的 `Release*Chars()` 配对，原生方法返回时不会自动释放取得的字符指针。

如果只需要读取字符串的一段，可用 `GetStringRegion()` 复制到调用方提供的缓冲区，避免先获取整串再做第二次复制。

### 8. 数组与 `DirectByteBuffer`

#### 8.1 基本类型数组

JNI 规范允许 `Get<PrimitiveType>ArrayElements()`：

- 返回指向托管数组的直接指针，并在此期间固定数组位置；
- 或分配原生缓冲区，把数组内容复制进去。

调用方不能把其中一种实现当成跨版本保证。对于 Android 17 中可能被 GC 移动的基本类型数组，ART 的普通 Elements 路径通常建立原生副本并执行 `memcpy`；`GetPrimitiveArrayCritical()` 则可通过限制移动式 GC 和线程翻转（thread flip，ART 协调线程状态的一种机制）来提供直接地址。这种实现差异说明，大数组既要测量复制成本，也要观察 GC 影响，不能只比较 API 名称。所有 Elements 调用仍必须用对应的 `Release<PrimitiveType>ArrayElements()` 结束生命周期。

如果只读写一个明确区间，`Get/Set<PrimitiveType>ArrayRegion()` 用一次显式复制换取更简单的生命周期，通常比长期持有 Elements 指针更容易审查。大批量数据可以比较 Region、Elements、Critical 和 Direct Buffer，但要同时记录调用次数、字节量、临时分配、GC 暂停以及 P95/P99 耗时。

释放模式（release mode）的语义如下：

- `0`：如果取得的是副本，就把修改复制回 Java；随后释放副本或解除数组位置固定（pin）；
- `JNI_ABORT`：如果取得的是副本，就丢弃其中的修改；随后释放副本或解除固定。若虚拟机直接返回数组地址，已经发生的写入无法被“撤销”；
- `JNI_COMMIT`：如果取得的是副本，就把修改复制回 Java，但不释放该副本；后续还要再次调用对应的 Release API 完成清理。

只读输入在语义允许时使用 `JNI_ABORT`，可以避免虚拟机返回副本时执行无意义的回写（copy-back）。它不是通用的“回滚写入”选项。

#### 8.2 `GetPrimitiveArrayCritical()` 不是通用加速开关

它也不保证一定返回原数组地址。进入 Critical 临界区后：

- 不要调用任意 JNI API。
- 不要做阻塞系统调用。
- 不要等待锁。
- 尽快完成并调用对应的 Release API。

这种 API 会限制虚拟机执行 GC 和移动堆对象的选择。只有在目标设备上完成测量，并且能严格控制临界区耗时后，才应使用。

#### 8.3 直接缓冲区

`ByteBuffer.allocateDirect()` 或 `NewDirectByteBuffer()` 创建的存储不在托管堆中，原生代码可用 `GetDirectBufferAddress()` 取得地址。

适合：

- 大块数据主要由 C/C++ 处理；
- 缓冲区需要跨多次 JNI 调用复用；
- 下游原生 API 本来就使用指针。

代价与风险：

- 分配和释放通常比 `byte[]` 成本高，应通过缓冲区池复用；
- Java 侧逐元素访问可能比普通数组慢；
- 原生代码保存地址时，必须保证 `ByteBuffer` 或底层原生内存分配仍然存活；
- `NewDirectByteBuffer()` 只是包装地址，不会自动负责释放 `malloc` 分配的内存；
- 容量、偏移、对齐和线程同步仍由业务代码保证。

“Direct”只说明可以取得原生地址，不代表整条处理链自动实现零拷贝；下游 API 仍可能复制数据。

### 9. 如何观察 JNI

Perfetto 的默认系统轨迹（system trace）不会自动为每次 JNI 跨界生成统一的轨迹区段。这里的轨迹区段也叫 slice，指一段带有开始、结束时间和名称的记录。常用证据有三类。

#### 9.1 主动插桩

主动插桩指在关键路径显式加入轨迹记录。第三方 NDK 代码应使用稳定 API `<android/trace.h>`。下面的代码会记录 `DecodeBatch()` 的完整耗时：

```cpp
#include <android/trace.h>

ATrace_beginSection("Decoder::decodeBatch");
DecodeBatch(input, output);
ATrace_endSection();
```

这段记录会在系统轨迹中生成名为 `Decoder::decodeBatch` 的区段。`ATrace_beginSection()` / `ATrace_endSection()` 必须在同一线程正确嵌套。名称构建也有成本；名称较复杂时，应先用 `ATrace_isEnabled()` 判断轨迹功能是否开启，避免关闭记录后仍执行大量字符串格式化。

平台内部代码还可以用：

- `cutils/trace.h` 的 `ATRACE_BEGIN()` / `ATRACE_END()`。
- `utils/Trace.h` 的 `ATRACE_NAME()` / `ATRACE_CALL()`；这些宏利用 RAII，在当前 C++ 作用域结束时自动结束区段。

这些是平台内部接口，不应作为普通 NDK SDK 的稳定 API 暴露。

在 Java/Kotlin 与 C/C++ 两侧放置相邻的轨迹区段，可以拆分出以下阶段：

```text
managed wrapper
  ├─ 参数准备
  ├─ native batch
  └─ 结果转换
```

相邻区段能把托管侧的参数准备、结果转换与 C/C++ 批处理本身分开。还要结合 CPU 采样，才能确认区段内部究竟耗时在哪个函数。

#### 9.2 Simpleperf / Perfetto CPU sampling

CPU 采样能回答“处理器时间花在哪些函数”，也可能看到 ART 的 JNI 跳板代码（trampoline，即从托管调用约定转入 JNI 的中间代码）以及后续 C/C++ 调用链。采样按固定频率记录程序当时的位置，不能给出每次调用精确的开始和结束时间。

为了把地址还原成可读的 C/C++ 函数名，构建产物至少要保留：

- 未剥离符号的 `.so`，或单独保存的调试符号文件。
- 正确的 build ID；它用于匹配二进制文件与对应的符号文件。
- 与 APK 完全匹配的符号文件。
- 合适的调用栈采集方式。

下面的命令把 Simpleperf 的采样结果转换成 Perfetto 可直接导入的 Protobuf 文件，并保留调用链：

```bash
simpleperf report-sample \
  --protobuf \
  --show-callchain \
  -i perf.data \
  -o simpleperf.proto
```

生成的 `simpleperf.proto` 包含采样点和调用栈，不包含每次 JNI 调用的起止事件。C/C++ 算法本身占用 CPU 时，应优先查看采样结果；怀疑 JNI 调用太零碎时，则应统计调用次数，并结合主动插桩与微基准。

#### 9.3 微基准

测量一次 JNI 跨界的成本时，要避免混入其他变量：

- 调用方预热到稳定的 JIT/AOT 状态。
- C/C++ 函数只做能够防止编译器消除的最小工作。
- 分开测基本类型、`String`、数组和直接缓冲区。
- 记录设备、构建类型、CPU 频率策略、样本数和分位数。
- 关闭 CheckJNI、调试日志和 sanitizer 后再测发布版本的性能；sanitizer 是用于发现内存、线程等错误的运行时检查器。
- 同时保留开启检查的正确性测试。

只报告平均值会掩盖 GC、调度和锁带来的长尾，至少看 P50/P95/P99。

Android 17 源码中的 `benchmark/jni-perf` 可作为实验设计参考：它比较空 JNI 入口和 ART 内部路径，但依赖平台构建与内部头文件，不能直接复制到普通 APK，也不提供跨设备通用常数。应用侧应使用 AndroidX Microbenchmark，分别测试普通入口、Fast、Critical、`Region`、`Elements` 和批处理接口。测试代码还要实际使用返回值，避免编译器删除没有可见效果的工作。

### 10. 16KB 内存页：Android 17 上必须验证的原生代码边界

这一节站在 JNI/NDK 发布验收视角，只回答“最终 App 产物要检查什么”；后文 Bionic 部分再解释运行时页大小、linker 兼容装载和 libc 内部实现。两处是同一个主题，但分工不同：这里负责产物验收，后文负责运行时机制。

Android 15 起支持使用 16KB 内存页的设备。内存页是操作系统管理内存映射的基本单位。只要 APK 或 SDK 包含 `.so`，就要同时检查 ELF 文件、APK 打包布局，以及代码对运行时页大小所作的假设。ELF 是 Android 原生共享库 `.so` 使用的二进制格式。

#### 10.1 两种对齐不能混为一谈

1. **ELF 可加载段对齐**：每个 `.so` 的 `LOAD` segment（装载到内存的文件区段）至少按 `2**14`，也就是 16KB 对齐。
2. **APK ZIP 对齐**：未压缩的 `.so` 在 APK 这个 ZIP 容器中，也要从 16KB 对齐的文件位置开始存放。

一个 `.so` 内部的 ELF 对齐正确，不代表 Android App Bundle（AAB）最终生成的 APK 打包布局也一定正确。这两层需要分别检查。

当前官方建议：

- AGP 8.5.1 或更高。
- NDK r28 或更高；它默认生成可加载段按 16KB 对齐的 ELF 文件。
- 所有预编译 `.so` 和第三方 SDK 也必须兼容。
- 去掉硬编码的 `PAGE_SIZE` / `4096`，运行时使用 `getpagesize()` 或 `sysconf(_SC_PAGESIZE)`。
- 复查 `mmap()`、文件偏移量、共享内存和自定义内存分配器中的对齐假设。

NDK r27 及更低版本可以按文档配置链接器参数，但升级工具链通常能减少兼容风险。只重新编译自研库、却遗漏 SDK 附带的 `.so`，最终 APK 仍然不兼容。

#### 10.2 验证最终产物

下面的命令从设备、APK、AAB 和 ELF 四个层面核对 16 KB 页兼容性：

```bash
# 设备实际页大小
adb shell getconf PAGE_SIZE

# APK 中未压缩 .so 的 ZIP alignment
zipalign -c -P 16 -v 4 app.apk

# AAB 请求的 page alignment
bundletool dump config --bundle=app.aab | grep alignment

# ELF LOAD segment alignment
llvm-objdump -p libexample.so | grep LOAD
```

设备页大小应返回 `16384`；`llvm-objdump` 显示的 ELF `LOAD` 对齐值不应小于 `2**14`；`bundletool` 应显示 `PAGE_ALIGNMENT_16K`。`zipalign` 则检查 APK 内每个未压缩 `.so` 的文件位置是否满足 16KB 对齐。

#### 10.3 Android 17 的立即报错验证

16KB 兼容模式（backcompat mode）可能让某些只按 4KB 对齐的应用暂时运行，但这不代表其中的原生库已经兼容。Android 17 可以在测试设备上关闭兼容模式，让不兼容的二进制文件在加载时立即终止进程：

```bash
adb shell setprop bionic.linker.16kb.app_compat.enabled fatal
adb shell setprop pm.16kb.app_compat.disabled true
```

这是设备级测试配置，完成验证后应恢复设置或重启设备。它适合持续集成（CI）设备或专用测试机，不要在日常使用的主力机上保留。

#### 10.4 Play 要求与性能数字

Google Play 当前要求目标版本为 Android 15 / API 35 或更高的应用支持 64 位设备上的 16 KB 页；从 2027-02-01 起，不支持的应用更新将无法发布。纯 Java/Kotlin 且所有依赖都不含原生代码的应用天然兼容，但仍应在 16KB 环境中做回归测试。

官方初步测试报告：

| 指标 | 平均变化 |
| --- | ---: |
| 内存压力下应用启动 | 降低 3.16%，部分样本最高 30% |
| 应用启动功耗 | 降低 4.56% |
| 相机热启动 / 冷启动 | 分别加快 4.48% / 6.60% |
| 系统启动 | 改善 8%，约 950ms |

16KB 页会平均增加一些内存使用。上述数字来自平台初步测试，不能当作单个应用的收益承诺；JNI/NDK 项目应先保证原生库能够可靠加载并正确运行，再用自己的设备验证性能变化。

### 11. JNI 不是 IPC 的替代品

JNI 解决同一进程内 Java/Kotlin 与 C/C++ 的互调。Binder/AIDL 解决跨进程通信，还承担调用方身份、权限、进程隔离和生命周期管理。

为了少一次 Binder 就把本应隔离的组件塞进同一进程，再用 JNI 传裸指针，通常会失去：

- 故障隔离。
- 权限边界。
- 进程死亡通知。
- 明确且可检查的数据序列化协议。
- 系统调度与可观测性。

如果服务本来就在 C++ 进程中，使用 NDK Binder 可以让通信接口继续留在 C/C++；如果 API 面向 Java/Kotlin 客户端，Java Binder 往往更自然。性能差异取决于传输的数据量、序列化方式、线程模型和进程安排，不能用固定百分比代替实测。


## Bionic libc 的实现与系统影响

跨过 JNI 后，代码进入 Bionic 和内核提供的运行环境。函数实现、FORTIFY、malloc、线程局部存储与系统调用封装会改变 Native 热路径的实际成本。

Bionic 位于 Android 原生运行时的公共路径上。系统调用封装、线程创建、同步原语、ELF 装载、字符串函数以及 Native Heap（C/C++ 代码通过 `malloc` 等接口使用的堆）的入口都经过它。分析 Bionic 性能需要划清实现边界：某个 API 由 Bionic 对外提供，不代表算法主体也在 Bionic 仓库。

平台行为以 Android 17 / API 37 / `android-17.0.0_r1` 为准；涉及 futex 和 MTE 的内核行为以 `android17-6.18-2026-06_r6` 为准。历史版本只用于解释兼容代码为何存在。

### 1. Bionic 的职责边界

Bionic 是 Android 的 C 库、数学库和动态链接器。NDK 使用的 C++ 标准库是 libc++，不能把两者混为一谈。这里的动态链接器负责在进程启动或 `dlopen()` 时装载共享库、解析符号并完成重定位。

| 组件 | Android 17 中的职责 | 容易混淆的边界 |
|---|---|---|
| `libc.so` / `libc.a` | C/POSIX 接口、系统调用封装、pthread 线程接口、stdio 文件 I/O、malloc 入口等 | 堆分配算法主体位于 `external/scudo/` |
| `libm.so` / `libm.a` | 数学函数 | 部分实现来自外部上游项目 |
| `libdl.so` | `dlopen`、`dlsym` 等接口桩 | 运行时实现由动态链接器接管 |
| `/system/bin/linker`、`/system/bin/linker64` | 装载 ELF、解析依赖、重定位、管理限制共享库可见范围的 linker namespace | Android 的名称不是 `ld-android.so` |
| `libstdc++.so` | 少量 C++ ABI（已编译二进制之间的调用约定）支持与兼容符号 | 它不是完整的 STL 实现 |

Bionic 源码也没有单一的“BSD 实现”来源。`libc/upstream-freebsd/`、`upstream-netbsd/`、`upstream-openbsd/` 保存可直接复用的上游代码；`libc/bionic/` 包含 Android 自己维护的实现；系统调用桩由描述文件生成；部分 arm/arm64 字符串、内存和数学例程来自 `external/arm-optimized-routines/` 或 `external/llvm-libc/`。“Bionic 比 glibc 小，所以一定更快”无法作为性能结论，必须在目标 Android 设备和目标 API 上测量。

调用路径的边界如下：

```text
NDK / Framework JNI / native system service
                  |
                  v
              Bionic API
        +---------+----------+
        |                    |
        v                    v
  用户态快速路径          系统调用封装
  TLS / atomic / IFUNC       |
        |                    v
        |       Linux android17-6.18-2026-06_r6
        |
        +--> malloc dispatch --> Scudo（常规产品）
                            \--> jemalloc（malloc_low_memory 产品配置）
```

图中的 TLS 是线程局部存储，atomic 表示用户空间原子操作，IFUNC 负责按硬件能力选择函数实现；系统调用封装才会进入内核。`malloc dispatch` 则是一层函数指针分派，可把请求交给实际分配器或诊断工具。

因此，在 `malloc` 火焰图里看到 `libc.so`，不能直接认定问题在 Bionic；在 `pthread_mutex_lock` 调用栈里看到 futex，也不能认定每次加锁都进入内核。

### 2. malloc：Bionic 负责入口和分派，Scudo 负责分配

#### 2.1 Android 17 的默认关系

`bionic/libc/bionic/malloc_common.cpp` 定义 `MallocDispatch`，其中包含 `malloc`、`free`、`realloc`、`mallopt`、`malloc_info` 等函数指针。正常路径使用默认 dispatch（分派表）；malloc debug、hooks 和堆采样工具 heapprofd 等功能可以安装另一张表，在调用前后插入诊断或采样逻辑。

下面的 Android 17 构建片段用于确认默认分配器和低内存分支：

```bp
cc_defaults {
    name: "libc_native_allocator_defaults",
    whole_static_libs: ["libscudo"],
    cflags: ["-DUSE_SCUDO"],
    product_variables: {
        malloc_low_memory: {
            whole_static_libs: [
                "libjemalloc5",
                "libc_jemalloc_wrapper",
            ],
            exclude_static_libs: ["libscudo"],
        },
    },
}
```

这段配置表明，Android 17 常规产品将 `libscudo` 链入 libc；启用 `malloc_low_memory` 的产品仍可选择 jemalloc。Bionic 的 README 也明确说明，堆实现位于 `external/scudo/`。

可以把一次普通分配理解为：

```text
malloc()
  -> Bionic 当前 dispatch
     -> Scudo C wrapper
        -> Primary：按 size class 管理常规分配
        -> Secondary：处理较大或特殊分配
```

当 heapprofd 或 malloc debug 生效时，中间会多一层拦截。性能分析必须先确认当前 dispatch，再判断耗时来自采样、调用栈回溯、Scudo 元数据操作、锁竞争、缺页，还是内核映射与回收。

#### 2.2 分配器演进边界

| 阶段 | AOSP 主线选择 | 解决的问题 | 阅读时要保留的条件 |
|---|---|---|---|
| Android 早期 | dlmalloc | 实现简单，适合当时的设备规模 | 多线程扩展和碎片控制能力有限 |
| Android 5.0 至 10 前后 | jemalloc | 用多个 arena（相对独立的分配区域）和 size class 改善并发扩展 | 具体参数由 Android 分支配置决定 |
| Android 11 至 17 | Scudo | 强化 chunk（一次分配对应的内存块）元数据、状态与分配行为检查 | 低内存产品仍可能使用 jemalloc |

这条时间线解释设计变化，不能代替基准测试。分配器开销受对象尺寸分布、线程数、存活期、RSS（进程当前驻留在物理内存中的页面总量）压力、MTE 模式和采样工具影响，固定写成“增加 2%～5%”无法用于不同设备或工作负载。

Scudo 是面向堆漏洞的强化分配器。它能检测部分内存块头部损坏、重复释放（double free）、无效状态、未对齐指针和分配/释放类型不匹配。对没有触发这些检查的越界访问或释放后使用（use-after-free），Scudo 不一定能在第一次非法访问处报告。官方因此把它定义为安全缓解措施（mitigation），而不是 ASan/HWASan 那类覆盖范围更完整的错误检测器。出现 `Scudo ERROR:` 时，应把短错误摘要作为排查入口，再结合崩溃转储（tombstone）、HWASan、MTE 或可复现测试定位第一次非法访问。

#### 2.3 API 37 的回收接口

Android 的 `mallopt` 提供若干分配器控制项：

- `M_PURGE`（API 28）尝试立即释放未使用内存；
- `M_PURGE_ALL`（API 34）检查范围更广，也可能阻塞更久；
- `M_PURGE_FAST`（API 37）面向可频繁调用、延迟受限的场景，允许少释放一些内存以缩短执行时间；
- `M_DECAY_TIME` 控制未使用页立即、周期或停止回收；
- `M_MEMTAG_TUNING` 只在 Scudo 且进程启用 MTE 时有意义。

这些接口会改变 CPU 时间、锁持有时间、RSS 和后续缺页之间的平衡。不要把 purge 放到每帧路径，也不要只看调用结束后的 RSS。应同时记录 purge 时延、回收量、下一阶段 minor fault（无需从磁盘读取即可处理的次缺页）和用户可见延迟。

### 3. pthread_create：默认栈只是线程成本的一部分

#### 3.1 子线程与主线程的栈来源不同

Android 17 的默认子线程栈定义在 `pthread_internal.h`：

```cpp
#if defined(__LP64__)
#define SIGNAL_STACK_SIZE_WITHOUT_GUARD (32 * 1024)
#else
#define SIGNAL_STACK_SIZE_WITHOUT_GUARD (16 * 1024)
#endif

#define PTHREAD_STACK_SIZE_DEFAULT \
    ((1 * 1024 * 1024) - SIGNAL_STACK_SIZE_WITHOUT_GUARD)
```

因此，Bionic 创建的子线程默认 `pthread_attr_t::stack_size` 在 LP64（指针和 `long` 都为 64 位的 ABI）上是 992 KiB，在 32 位进程上是 1008 KiB。源码随后会从栈顶划出 `pthread_internal_t`，所以这两个数字也不能直接当成业务代码可用的最大栈深。

主线程走另一条路径。`pthread_attr_getstack` 根据 `RLIMIT_STACK`（进程栈资源限制）和进程映射计算主栈；只有当限制为 `RLIM_INFINITY` 时，Bionic 才把报告值收敛为 8 MiB，避免调用者把无限值当成可用映射。“Android 主线程固定 8 MiB”并不成立。

#### 3.2 一个子线程包含哪些映射

当调用者没有提供栈时，`pthread_create.cpp` 建立一块 `MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE` 映射，布局如下：

```text
低地址
  [调用者配置的 stack guard]
  [线程栈]
  [静态 ELF TLS + bionic_tls]
  [libgen buffers，按页填充]
  [Bionic 末端 guard]
高地址
```

之后才初始化 TCB（线程控制块）、DTV（动态 TLS 模块表）、stack canary（用于检测栈破坏的随机校验值）和 Bionic TLS，并通过带有 `CLONE_SETTLS` 等标志的 `clone` 路径创建内核线程。线程启动后还会建立处理信号时使用的备用栈（alternate signal stack）；arm64/riscv 构建还可能分配用于保护返回地址的 Shadow Call Stack 区域。

这里有三个性能含义：

1. 线程成本不能只用 `stack_size` 估算。TLS、guard（不可访问的保护区）、signal stack、Shadow Call Stack、内核线程对象和调度数据都要计入。
2. `MAP_NORESERVE` 以及按需缺页使虚拟地址空间增长与 RSS 增长不同步。只看 VSS（分配给进程的虚拟地址空间总量）容易高估物理内存，实际触碰大量栈页后 RSS 才会上升。
3. 缩小栈能减少地址空间和最坏物理占用，但 `PTHREAD_STACK_MIN` 只是 ABI 下限。Android 17 中 LP64 为 16 KiB、32 位为 8 KiB；该下限不保证业务调用深度、信号处理、JNI 或第三方库安全。

设置自有栈时，还必须满足运行时页大小对齐。递归、较大的栈上数组、复杂的调用栈展开（unwind）、信号处理和 Sanitizer 检测工具，都可能让“空载测试可用”的小栈在压力场景溢出。调优应使用目标构建测量实际最大用量，再预留 guard 与故障处理余量。

#### 3.3 调度策略与 `top-app` 属于两套接口

`pthread_attr_setschedpolicy` 接受的是 Linux 调度策略，例如 `SCHED_OTHER`/`SCHED_NORMAL`、`SCHED_BATCH`、`SCHED_IDLE`、`SCHED_FIFO` 和 `SCHED_RR`。实时策略还受权限、优先级范围与系统策略约束。

Android 的 `top-app` 属于 task profile（系统为一组线程应用的资源策略）、cgroup 控制组和系统调度配置，`SCHED_TOP_APP` 不是 Bionic 或 Linux 的 `SCHED_*` 常量。前台进程获得怎样的 CPU 集合、uclamp 调度利用率限制或其他参数，由 framework、libprocessgroup、设备配置和内核共同决定。应用不能通过 `pthread_attr_setschedpolicy(..., 5)` 把线程变成 `top-app`；数值碰巧相同也没有这层语义。

### 4. mutex 与 condition variable：用户态快路径和内核等待

#### 4.1 普通 mutex

Android 17 的普通非 PI mutex 使用一个原子状态：

- `0`：未锁；
- `1`：已锁、尚未发现竞争；
- `2`：已锁、存在竞争。

无竞争的 `pthread_mutex_lock` 通过原子比较并交换（compare-and-exchange）把状态从 `0` 改为 `1`，不进入内核。竞争路径把状态改为 `2`，然后通过 futex（Linux 用户空间锁的内核等待/唤醒机制）等待；解锁发现旧状态为 `2` 时，再用 futex 唤醒一个等待者。源码中没有能够证明“Android 17 新增乐观自旋（optimistic spinning）”的分支。

进程间共享的 mutex 会选择共享 futex 操作，进程内私有 mutex 可以使用开销更低的 private futex。recursive 和 errorcheck 类型还要记录持有者（owner）与递归计数。分析高频锁路径时，应确认锁类型、是否跨进程、竞争比例和临界区长度，再讨论是否替换同步原语。

#### 4.2 Priority Inheritance mutex

把 mutex protocol 配置为 `PTHREAD_PRIO_INHERIT` 后，Bionic 使用独立的 PI 状态与 `FUTEX_LOCK_PI`/`FUTEX_UNLOCK_PI` 路径。无竞争时仍尝试以原子操作获得 owner；发生竞争时由内核 `kernel/futex/pi.c` 等代码管理所有权和优先级继承。

PI（Priority Inheritance，优先级继承）可以缓解高优先级线程等待低优先级持锁者造成的优先级反转，但其路径和状态管理更复杂。它不能修复过长临界区、锁顺序错误或持锁 I/O。

#### 4.3 Condition variable

`pthread_cond_t` 在 Android 17 中维护原子 `state` 计数和等待者数量。wait 路径的顺序是：

1. 读取当前 state；
2. 记录等待者；
3. 解开调用者的 mutex；
4. 对旧 state 执行 futex wait；
5. 减少等待者并重新获得 mutex。

`signal`/`broadcast` 会增加 state，再分别唤醒一个或多个等待者。该实现允许虚假唤醒（spurious wakeup），也就是线程可能在条件尚未成立时从等待中返回；POSIX 调用者因此必须使用谓词循环：

```cpp
pthread_mutex_lock(&mutex);
while (!ready) {
    pthread_cond_wait(&cond, &mutex);
}
consume_result();
pthread_mutex_unlock(&mutex);
```

这段循环同时处理虚假唤醒、多个消费者竞争以及条件在重新加锁前发生变化。把 `while` 改成 `if` 会引入正确性问题。`broadcast` 是否造成集中唤醒，要结合等待者数量和谓词设计分析，不能仅凭 API 名称判断。

### 5. TLS：快速寻址不等于零成本

arm64 的 `__get_tls()` 直接读取 `TPIDR_EL0`：

```cpp
static inline void** __get_tls(void) {
  void** result;
  __asm__("mrs %0, tpidr_el0" : "=r"(result));
  return result;
}
```

这段代码只说明线程指针的获取方式。一次 C/C++ `thread_local` 访问还可能包含由编译和链接方式决定的 TLS model 地址计算、DTV 查询、模块初始化和数据访问，不能统一写成固定周期数。

Android 17 在 arm/arm64 上保留的 Bionic TCB slot 包括：

| Slot | 用途 |
|---|---|
| `TLS_SLOT_DTV` | ELF TLS 的动态线程向量，即各 TLS 模块在线程中的地址表 |
| `TLS_SLOT_THREAD_ID` | 线程标识相关快速访问 |
| `TLS_SLOT_APP` | API 29 起留给应用使用的预分配 slot |
| `TLS_SLOT_OPENGL` / `TLS_SLOT_OPENGL_API` | 图形子系统快速访问 |
| `TLS_SLOT_STACK_GUARD` | stack protector 使用的 canary |
| `TLS_SLOT_SANITIZER` | Sanitizer 线程状态 |
| `TLS_SLOT_ART_THREAD_SELF` | ART 的 `Thread::Current()` 快速路径 |
| `TLS_SLOT_BIONIC_TLS` | Bionic 自身 TLS 指针 |
| `TLS_SLOT_NATIVE_BRIDGE_GUEST_STATE` | native bridge guest 状态 |
| `TLS_SLOT_STACK_MTE` | stack MTE ring buffer 指针 |

这些定义位于私有头文件 `tls_defines.h`，不属于 NDK 公共 ABI。业务代码不能依赖 slot（固定槽位）编号；普通线程局部数据应使用 C++ `thread_local`、编译器 ELF TLS 或 `pthread_key_create`。

`TLS_SLOT_STACK_MTE` 也不表示“整个 TLS 区域被 MTE 标记”。Android 17 的 `pthread_create.cpp` 会在需要时让它指向栈 MTE 使用的环形缓冲区；线程主映射在 `__libc_memtag_stack` 开启时可带 `PROT_MTE`。这是栈内存标记支持，需要与 TLS 寻址机制分开说明。

### 6. MTE：诊断精度、运行成本和适用环境要一起看

Arm MTE 把内存划成 16 字节标记粒度（granule），为每个粒度保存 4 位 allocation tag；指针的 logical tag 位于地址高位。CPU 访问内存时比较指针标签与内存标签。两者不匹配时，Android 可按进程配置不同的故障报告模式（fault mode）：

| 模式 | 报告行为 | 适用方向 |
|---|---|---|
| SYNC | 在错误访问处精确触发 `SEGV_MTESERR`，诊断信息更完整 | 开发、测试、需要精确定位的进程 |
| ASYNC | 记录标签不匹配，延迟到后续内核入口附近以 `SEGV_MTEAERR` 终止；故障地址和主回溯通常不精确 | 经过充分测试后的低开销生产监测 |
| ASYMM | 读访问同步报告、写访问异步报告；系统可在应用请求 async 时按 CPU 首选模式升级 | 硬件支持时的生产候选 |

ASYNC 并不会“只记录而不终止”。进程仍会收到 `SIGSEGV`，只是终止点可能靠近下一次系统调用或中断，主回溯通常对应报告时刻。

Android 17 的 Bionic 包含 `note_memtag_heap_async.S` 和 `note_memtag_heap_sync.S`，用于把构建时的 heap memtag 要求写入 ELF note（ELF 文件中的元数据记录）。当前控制边界如下：

- Java 应用通过 `<application>` 或 `<process>` 的 `android:memtagMode` 请求 `off`、`default`、`sync` 或 `async`；
- 原生可执行文件可由 Android 构建系统 Soong/Make 的 `memtag_heap` 配置启用；
- `arm64.memtag.process.<basename>` 只适合原生进程的启动时实验配置，不适用于 Java 应用包名；
- `MEMTAG_OPTIONS` 可覆盖原生进程设置；
- 实际模式还受硬件、内核和设备策略影响。

MTE 的成本与 CPU 实现、访问模式、Scudo 写入内存标签的工作、是否采集分配/释放调用栈以及系统首选模式有关。标签比较由硬件完成，也不表示分配、改标签和报告整条链路都没有成本。应在同一设备、同一温控和同一工作负载下对比 off/async/sync，并同时查看 CPU、功耗、帧延迟和 Native Heap 指标。

更多配置和报告解析见 [AOSP MTE 文档](https://source.android.com/docs/security/test/memory-safety/arm-mte) 以及 **20.11 MTE 与 GWP-ASan Native 内存安全检测**。

### 7. 16 KB 页：运行时页大小、ELF 对齐和兼容装载

#### 7.1 Bionic 获取页大小的方式

Android 17 的内部 helper 如下：

```cpp
inline size_t page_size() {
#if defined(PAGE_SIZE)
  return PAGE_SIZE;
#else
  static const size_t page_size = getauxval(AT_PAGESZ);
  return page_size;
#endif
}
```

可变页大小构建会从内核在进程启动时提供的辅助向量（auxiliary vector）中读取 `AT_PAGESZ`。`page_start`、`page_offset`、`page_end` 以及 pthread 映射随后都使用该值。NDK 代码应使用 `getpagesize()` 或 `sysconf(_SC_PAGESIZE)`，不要假设 `PAGE_SIZE == 4096`。

Android 15 起，AOSP 支持配置为 16 KB 页的设备；4 KB 设备仍受支持。TLB 缓存虚拟地址到物理地址的转换，16 KB 页能让单个 TLB entry 覆盖更多内存，但也会增大映射、保护、文件尾页和部分分配器回收的粒度。小对象通常共享 Scudo slab（为同类小对象集中提供空间的内存页组），一个 1 字节 `malloc` 不会单独占用一个 16 KB 物理页。RSS 是增加还是下降，取决于 TLB miss、页表、文件映射、工作集局部性和页内浪费共同产生的结果。

#### 7.2 linker 的兼容路径不能替代重新构建

`linker_phdr.h` 对 Android 17 兼容开关的注释很直接：

```cpp
// Use app compat mode when loading 4KiB max-page-size ELFs
// on 16KiB page-size devices?
bool should_use_16kib_app_compat_ = false;
```

兼容装载时，linker 以 4 KiB 对齐解释旧 ELF segment（装载时映射的一段文件内容），并通过专门的匿名映射、复制与权限处理装载它。关闭兼容模式后，如果设备页大小至少为 16 KiB 且 `PT_LOAD` 段的最小对齐小于系统页大小，`LoadSegments()` 会拒绝装载；配置为 `fatal` 时还会主动中止。

兼容模式增加映射和权限处理的复杂度，也受设备与应用兼容策略控制。发布包仍应提供正确对齐的全部 native library，包括第三方 SDK 和预编译 `libc++_shared.so`。

当前官方工具链规则是：

| NDK 版本 | 16 KB ELF 对齐 |
|---|---|
| r28 及以上 | 默认生成 16 KB 对齐的 ELF |
| r27 及以下 | 显式加入 `-Wl,-z,max-page-size=16384` 和 `-Wl,-z,common-page-size=16384` |

还要检查自定义链接脚本（linker script）、预编译 `.so`、直接使用 `mmap`/`mprotect` 的对齐计算，以及把 4096 当作 I/O block 大小的代码。构建通过后，应在 16 KB 模式设备上执行启动、`dlopen`、插件加载、解压、数据库和原生崩溃路径测试。完整检查方式见 [Android 16 KB page size 指南](https://developer.android.com/guide/practices/page-sizes)。

### 8. arm64 字符串函数：Android 17 按硬件能力选择实现

Android 17 将部分 arm64 字符串/内存例程链接自 `external/arm-optimized-routines/`，同时保留 Bionic 自有的检查封装、Oryon 例程和 IFUNC resolver。resolver 是进程装载期间运行的选择函数；`ifuncs.cpp` 会根据辅助向量中的硬件能力和 CPU 信息，解析出随后实际调用的实现。

| 函数族 | Android 17 的选择依据 |
|---|---|
| `memcpy` / `memmove` | 优先选择 Arm Memory Operations（MOPS）指令实现；否则识别 Qualcomm Oryon；再看 ASIMD 向量指令；均不匹配时使用通用 arm64 实现 |
| `memset` | 优先 MOPS；否则选择 Oryon 或通用 arm64 实现 |
| `memchr`、`strchr`、`strlen` 等 | 支持 MTE 时选择能正确处理 tagged address 的 MTE 版本 |
| `memcmp`、`strcmp`、`strcpy` 等 | 当前选择 arm64 实现；源码中的 SVE 可伸缩向量指令分支仍是待启用注释 |

“所有大于 64 字节的拷贝都走 NEON”不符合源码。具体汇编内部可能使用成对加载/存储、SIMD 向量指令、预取（prefetch）或尽量减少缓存污染的 non-temporal store，但阈值和收益取决于最终选中的实现及 CPU 微架构，不能从 Bionic API 层统一推导。

排查 `memcpy` 热点时，还要先判断：

- 拷贝是否可以通过所有权转移、分散/聚集 I/O（scatter/gather）或批处理减少；
- 地址是否对齐、是否跨 NUMA 内存节点或共享内存、是否触发缺页；
- 调用长度分布和重叠语义是否匹配；
- 设备最终解析到哪一个 IFUNC；
- 时间消耗来自 CPU 搬运、缓存未命中（cache miss），还是内存带宽饱和。

替换系统 `memcpy` 前必须在目标 SoC 上测量，并覆盖小块、大块、冷热缓存、对齐和重叠输入。系统 resolver 已经包含平台维护的硬件分支，自写版本很容易只在某一项微基准中占优。

### 9. Bionic 与 glibc：API 可用性和性能边界

跨平台代码容易沿用旧版 Bionic 的印象。Android 17 的接口状态如下：

| 接口 | Android 17 状态 |
|---|---|
| `glob` / `globfree` | API 28 起可用 |
| `iconv` / `iconv_open` / `iconv_close` | API 28 起可用，支持的编码集合仍应查当前文档 |
| `posix_spawn` / `posix_spawnp` | API 28 起可用 |
| `backtrace` / `backtrace_symbols` / `backtrace_symbols_fd` | API 33 起可用 |
| `ftw` / `nftw` | API 37 头文件与符号中存在 |
| `pthread_cancel` | Android 17 仍未实现 |

“头文件能编译”与“最低支持版本能运行”属于两个阶段。NDK 会根据 `minSdkVersion` 提供 API stub（只声明接口的链接占位符）和 availability guard（版本可用性检查）；如果库的最低 API 低于符号引入版本，就需要条件编译、运行时查询或兼容实现。直接在低版本进程中装载一个强引用新符号的 `.so`，可能在业务代码执行前就失败。

`pthread_cancel` 缺失时，应采用协作式取消，让任务在安全检查点自行退出，例如使用原子标志、`eventfd`/pipe 唤醒、可中断队列或上层任务状态。不要用信号模拟任意点取消，因为库代码、锁状态和资源释放都可能停在不可恢复的位置。

glibc 的 benchmark 也不能直接预测 Android。Android 设备的分配器、动态链接器、内核配置、SoC 缓存、温控和进程策略都不同，需要在 Android 目标设备上使用相同编译器选项和数据集测试。

### 10. 诊断工具如何选择

| 现象 | 首选工具 | 读取重点 |
|---|---|---|
| Native Heap 持续增长 | heapprofd / Perfetto、`malloc_info` | 调用栈聚合、仍未释放的分配、时间窗口；区分已分配字节数与 RSS |
| 怀疑越界、double free | Scudo 日志、MTE、HWASan | 第一条分配器错误、fault mode、分配/释放调用栈 |
| 需要精确 guard 或每次分配回溯 | malloc debug | 仅在调试环境开启；`backtrace` 选项会让分配慢一个数量级 |
| RSS 下降慢 | `mallopt` 对照实验、Perfetto memory、minor fault | purge 时延、释放页数、后续再次缺页的代价 |
| 锁竞争 | Perfetto `sched`/futex、Simpleperf | owner/waiter、临界区、唤醒延迟、优先级反转 |
| 线程数或栈占用异常 | `/proc/<pid>/maps`、Perfetto、线程 dump | `stack_and_tls:<tid>` 映射、实际触页、高水位 |
| Native crash 符号化 | tombstone、debuggerd、带 build ID（唯一标识二进制构建）的符号文件 | `backtrace_symbols` 只提供进程内基础转换，不能替代完整离线符号化 |

malloc debug 通过 `libc.debug.malloc.options` 或对应环境配置安装 shim（插在调用方与分配器之间的适配层）。guard、fill、backtrace 等选项可以组合，但开销不同；尤其每次分配都展开调用栈，会改变分配时序和竞争。heapprofd 适合按时间采样实际负载，HWASan/MTE 适合查非法访问，工具选择应与问题类型匹配。

### 11. 面向 NDK 代码的检查清单

1. **记录分配尺寸与存活期。** 高频小对象不自动等于需要对象池。对象池会引入生命周期、峰值保留和并发管理成本，只有 benchmark 证明收益时再采用。
2. **分开统计分配次数、已分配字节数和 RSS。** Scudo 缓存、匿名页、文件页和内核回收会让三个指标变化不同步。
3. **控制线程数量，再调整栈。** 优先使用有界执行器；调整 `pthread_attr_setstacksize` 时覆盖递归、JNI、信号和 Sanitizer 场景。
4. **保持条件变量谓词循环。** 任何依赖“不会虚假唤醒”的写法都不符合 Android 17 实现与 POSIX 约束。
5. **不要伪造 `top-app` 策略。** 线程调度问题应分别检查 task profile、nice 优先级、uclamp、CPU affinity（允许运行的 CPU 集合）、实时权限和设备配置。
6. **按运行时页大小计算映射。** 所有传给 `mmap`、`mprotect`、`munmap` 的地址和长度都要复核；ELF 则检查每个 `PT_LOAD` 的对齐。
7. **把 MTE 模式纳入测试组合。** 开发阶段用 sync 获取精确报告，生产候选按安全与性能需求评估 async/asymm。
8. **批量 I/O 时处理系统调用语义。** 直接调用 `write` 仍可能只写入部分数据（short write），或被信号以 `EINTR` 中断；用它替换 stdio 之前，应补齐正确的重试逻辑，并测量缓冲对性能的影响。
9. **遵守 `minSdkVersion`。** 对 API 28、33、37 新增符号分别检查编译期版本保护和运行时装载路径。

### 12. Android 17 的职责分层

Android 17 中，Bionic 的性能角色可以归纳为四层：

- API 与 ABI 层：提供 C/POSIX 接口和系统调用封装；
- 用户态运行时层：实现 pthread 快路径、TLS、stdio 和部分基础例程；
- 分派层：把 Native Heap 调用交给 Scudo/jemalloc，并允许调试与采样插入；
- 装载层：根据 ELF、页大小和硬件能力选择装载与 IFUNC 路径。

定位问题时，应沿实际调用链逐层确认：当前使用哪个分配器、dispatch 是否被工具替换、锁是否发生竞争、线程包含哪些实际映射、页大小和 ELF 对齐是否匹配、arm64 resolver 选择了哪个实现。基于这些证据得出的结论才能在 Android 17 设备上复现，也能解释版本升级后的行为变化。

Native Heap 与 Scudo 的进一步分析见 **23.3 Native 内存管理与优化**；16 KB 页的系统影响与兼容验收见 **4.5 16 KB Page Size 与 Android 性能**；MTE 检测见 **20.11 MTE 与 GWP-ASan Native 内存安全检测**；运行时下载或释放 `.so` 的发布协议见 **20.13 Native 动态库安全发布、装载与回滚**。


## 版本与实现边界

| Android 版本 | JNI/NDK 相关变化 |
| --- | --- |
| Android 8（API 26） | `@FastNative` / `@CriticalNative` 开始用于系统内部；`String` 的紧凑存储和会移动对象的 GC 改变了字符指针的复制假设 |
| Android 12（API 31） | 虚拟机内置的动态 JNI 查找开始可靠支持这两种注解；更早的系统需要显式注册 |
| Android 14（API 34） | `@FastNative` / `@CriticalNative` 成为通过兼容性测试套件（CTS）验证的公开 API |
| Android 15（API 35） | AOSP 支持使用 16KB 内存页的设备；Play 要求面向 Android 15 及以上版本的新提交与更新兼容该页大小 |
| Android 17（API 37） | 当前 JNI 语义继续沿用；16KB 测试增加 `fatal` 兼容模式，可让不兼容的原生库立即失败；AOSP 源码统一以 `android-17.0.0_r1` 为准 |


## 常见误区

### “Native 一定比 Java/Kotlin 快”

不成立。ART 已能很好地优化许多 Java/Kotlin 高频路径；频繁 JNI 调用、数据复制和内存安全处理的成本，可能抵消 C/C++ 算法的收益。

### “Perfetto 默认会显示每次 JNI 跨界”

不成立。没有主动插桩时，通常只能结合 CPU 采样、函数符号和相邻轨迹进行判断。

### “`@CriticalNative` 可以传基本类型数组”

不成立。数组是托管对象，CriticalNative 会因对象参数触发校验错误。它只能使用基本类型标量，以及生命周期已经明确的原生句柄。

### “`AttachCurrentThread()` 可以每个任务调一次”

从接口行为看，对已经附着的线程再次调用只是空操作；但清晰的资源边界仍是在线程启动时附着、退出前分离。按任务反复管理，会让线程与虚拟机连接的所有权更难确认。

### “`GetPrimitiveArrayCritical()` 一定零拷贝”

不成立。虚拟机仍可选择复制；Critical 约束的是运行时协调方式和临界区规则，并不承诺零拷贝。

### “DirectByteBuffer 会自动管理 C/C++ 内存”

不成立。`NewDirectByteBuffer()` 不负责释放外部地址指向的内存；缓冲区对象或底层内存失效后，C/C++ 代码也不能继续使用该地址。

### “App 在 16KB 兼容模式能启动就算完成迁移”

不成立。兼容模式只是过渡机制。最终仍要验证 ELF 对齐、APK 中的 ZIP 对齐、所有第三方 `.so`，以及代码对运行时页大小的假设。


## 结论

这篇文章覆盖两个连续层次：JNI 决定托管代码怎样跨入 Native，Bionic 决定进入 Native 后常用分配、线程、同步、TLS、MTE、页大小和 libc 接口怎样实现。优化时先判断成本位于边界转换还是原生运行时，避免把 Native 内部的锁、分配或装载问题误归为 JNI 开销。

JNI 优化按这个顺序做：

1. 先减少跨边界次数和数据转换量，把零碎调用合并成批量接口。
2. 缓存类以及方法、字段 ID，明确局部引用和全局引用的生命周期。
3. 让线程附着与分离跟随线程生命周期，并正确处理 `ClassLoader` 和待处理异常。
4. 用 CheckJNI 消除接口误用，再在接近发布配置的构建中，用 ATrace、Simpleperf 和微基准测量性能。
5. 只有短、可预测、不阻塞且调用频率极高的方法，才考虑 `@FastNative` / `@CriticalNative`。
6. C/C++ 产物必须在 16KB 设备上验证 ELF 对齐、APK 打包布局和运行时行为。

完成这些基础工作后，再讨论单次 JNI 跨界的纳秒级优化才有意义。Bionic 侧则应以目标设备的分配热点、锁等待、线程数量、MTE 模式和实际页大小为证据，不从 libc 名称或 16 KB 兼容模式直接推断性能收益。


## 参考资料

- [Android NDK：JNI tips](https://developer.android.com/ndk/guides/jni-tips)
- [Android API：FastNative](https://developer.android.com/reference/dalvik/annotation/optimization/FastNative)
- [Android API：CriticalNative](https://developer.android.com/reference/dalvik/annotation/optimization/CriticalNative)
- [Android Developers：Support 16KB page sizes](https://developer.android.com/guide/practices/page-sizes)
- [Android NDK：Simpleperf](https://developer.android.com/ndk/guides/simpleperf)
- [Perfetto：Simpleperf proto format](https://perfetto.dev/docs/getting-started/other-formats#simpleperf-proto-format)
- [JNI Specification（Java 25）](https://docs.oracle.com/en/java/javase/25/docs/specs/jni/)
- [AOSP：Binder.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Binder.java)
- [AOSP：Parcel.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Parcel.java)
- [AOSP：SystemProperties.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/SystemProperties.java)
- [AOSP：Trace.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Trace.java)
- [AOSP：NDK trace.h（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/include/android/trace.h)
- [AOSP：cutils trace.h（android-17.0.0_r1）](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/libcutils/include/cutils/trace.h)
- [AOSP：libutils Trace.h（android-17.0.0_r1）](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/libutils/include/utils/Trace.h)
- [AOSP：Simpleperf view_the_profile.md（android-17.0.0_r1）](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/doc/view_the_profile.md)
