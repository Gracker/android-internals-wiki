---
title: JNI/NDK 性能优化
chapter: '1.15'
section: '1.15'
status: finalized
applicable_versions: Android 8.0 (API 26) - Android 17 (API 37)
last_verified: '2026-07-25'
last_verified_against: AOSP android-17.0.0_r1 + Android NDK official documentation
confidence: high
consolidated_from:
  - "src/part2-performance/ch08-responsiveness/20-jni-overhead-native-interop-performance.md"
sources:
  - type: official
    path: "https://developer.android.com/ndk/guides/jni-tips"
  - type: official
    path: "https://developer.android.com/reference/dalvik/annotation/optimization/FastNative"
  - type: official
    path: "https://developer.android.com/reference/dalvik/annotation/optimization/CriticalNative"
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
  - type: official
    path: "https://developer.android.com/ndk/guides/simpleperf"
  - type: official
    path: "https://perfetto.dev/docs/getting-started/other-formats#simpleperf-proto-format"
  - type: spec
    path: "https://docs.oracle.com/en/java/javase/25/docs/specs/jni/"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Binder.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Parcel.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/SystemProperties.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Trace.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/native/include/android/trace.h @ android-17.0.0_r1"
  - type: aosp
    path: "system/core/libcutils/include/cutils/trace.h @ android-17.0.0_r1"
  - type: aosp
    path: "system/core/libutils/include/utils/Trace.h @ android-17.0.0_r1"
  - type: aosp
    path: "system/extras/simpleperf/doc/view_the_profile.md @ android-17.0.0_r1"
tags:
  - android
  - jni
  - ndk
  - art
  - fastnative
  - criticalnative
  - 16kb-page-size
  - simpleperf
related_chapters:
  - '1.7'
  - '4.7'
  - '14.2'
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
pipeline_stage: ready-to-publish
---

# 1.15 JNI/NDK 性能优化

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

## 1. JNI 成本来自哪里

### 1.1 边界切换

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

### 1.2 数据编组与复制

基本类型标量的传递最直接；`String`、数组和普通 Java 对象都需要运行时参与。

- `String` 可能发生 UTF-16 / Modified UTF-8 转换和复制。
- 基本类型数组可能直接暴露指针，也可能复制到原生缓冲区。
- 对象字段和方法需要 `jfieldID` / `jmethodID`。
- 原生代码回调 Java 又产生一次反向边界切换。
- `DirectByteBuffer` 可让原生代码直接访问地址，但必须明确内存所有权与生命周期。

很多所谓“JNI 慢”来自数据表示在两侧来回转换。

### 1.3 原生函数内部

JNI 只负责跨语言调用。进入原生函数后，锁、I/O、内存分配、算法复杂度和缓存未命中仍要按普通 C/C++ 性能问题处理。

`SystemProperties.java` 在 `android-17.0.0_r1` 里留下了一个很好的边界：

```java
// _NOT_ FastNative: native_set performs IPC and can block
private static native void native_set(String key, String def);
```

这个方法会执行 IPC，并且可能阻塞，所以没有使用 `@FastNative`。即使边界切换变快，调用方实际经历的阻塞时间也不会因此消失。

## 2. 第一原则：减少小粒度 JNI 调用

官方 JNI tips 把“减少跨 JNI 编组的数据量与频率”放在通用建议首位。工程上可以从三个方向做。

### 2.1 批量传输

下面的对比说明为什么应按批次传递数据，而不是为每个元素调用一次原生方法：

```text
差：4096 次 JNI，每次传 1 个 short
好：1 次 JNI，传 short[] / DirectByteBuffer / native handle
```

批量传输也不意味着无条件复制 100MB 数据。接口设计要看数据主要由哪一侧访问：

- Java/Kotlin 侧读写更多：基本类型数组通常更自然；
- C/C++ 侧长期处理：由原生代码拥有的缓冲区，或直接缓冲区（direct buffer）更合适；
- 两侧只传控制信息：可以传 `long` 形式的原生句柄，但必须防止句柄指向的对象已释放、重复释放和跨实例误用。

### 2.2 少做跨语言异步回调

如果 Java 线程池与原生线程池为每个任务相互回调，线程附着、引用和生命周期管理就会分散到大量工作线程。更容易维护的设计是让其中一侧统一管理异步状态，JNI 只在边界传递批量输入和少量完成事件。

UI 更新通常留在托管代码侧：后台 Java/Kotlin 线程执行一次阻塞式原生调用，结束后回到主线程发布结果，比原生工作线程高频回调 UI 层更简单。

### 2.3 缓存类、字段与方法 ID

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

## 3. ClassLoader：原生线程的 `FindClass()` 为什么常失败

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

## 4. `@FastNative` 与 `@CriticalNative`

两个注解都能减少托管代码与原生代码之间的切换成本，但二进制调用约定和使用范围不同。

| 维度 | 普通 JNI | `@FastNative` | `@CriticalNative` |
| --- | --- | --- | --- |
| 托管对象参数/返回值 | 支持 | 支持 | 不支持 |
| 实例方法隐式 `this` | 支持 | 支持 | 不支持，必须是静态方法 |
| 原生签名含 `JNIEnv*` | 是 | 是 | 否 |
| 原生签名含 `jobject` / `jclass` | 视方法而定 | 视方法而定 | 否 |
| 长 I/O / 可能长时间持有的原生锁 | 普通 JNI 仍应谨慎 | 禁止使用 | 禁止使用 |
| Android 14+ CTS 公共保证 | 普通 JNI | 是 | 是 |

### 4.1 `@FastNative` 可以使用托管对象

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

### 4.2 `@CriticalNative` 只能使用基本类型

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

### 4.3 注解之外还有兼容性要求

官方当前口径：

- Android 8 起用于系统内部。
- Android 14 / API 34 起成为通过兼容性测试套件（CTS）验证的公共 API；
- 追求最大兼容性的应用不应在 Android 13 及以下版本调用这些注解方法；
- Android 8～10 没有内建动态原生方法查找，Android 11 还有已知问题；Android 8～11 必须显式调用 `RegisterNatives()`；
- Android 7 及以下忽略注解；CriticalNative 因 ABI 不匹配可能错误编组参数并崩溃。

即使只支持 Android 14 及以上版本，官方仍建议性能关键方法使用 `RegisterNatives()`：这样，签名错误会在库加载时暴露，只需导出 `JNI_OnLoad()`，也不必等到首次调用时再由 `dlsym()` 按符号名称查找。

### 4.4 Baseline Profile 的角色

Baseline Profile 是随应用提供的一份高频方法清单，帮助 ART 提前编译这些方法。JNI 边界切换很快，不代表托管代码调用方已经优化。如果启动阶段频繁执行、显著影响总耗时的路径仍处于解释执行或 JIT 预热阶段，调用方耗时可能掩盖 JNI 差异。把稳定的高频调用方纳入 Baseline Profile，可以让比较聚焦于 JNI 与原生工作，减少首次编译的干扰。

Baseline Profile 不会自动合并 JNI 调用，也不会把不符合条件的方法变成 CriticalNative；它解决的是托管代码调用方的编译状态。

## 5. 线程附着与 `JNIEnv*`

### 5.1 `JNIEnv*` 只能属于当前线程

`JNIEnv*` 包含当前线程在虚拟机中的本地状态，只能由所属线程使用，不能存入全局变量供其他线程复用。可在进程内跨线程共享的是 `JavaVM*`，各线程再通过它取得自己的 `JNIEnv*`。

原生代码需要取得当前线程的 JNI 环境时：

1. 用 `JavaVM::GetEnv()` 查询当前线程是否已经附着到虚拟机；
2. 尚未附着且需要调用 JNI 时，使用 `AttachCurrentThread()` 或 `AttachCurrentThreadAsDaemon()`；
3. 线程退出前调用 `DetachCurrentThread()`。

对已经附着的线程再次调用 attach 不会重复附着，只会直接返回当前环境；但也不应在每个小任务前后反复执行。附着与分离（attach/detach）应和操作系统线程的生命周期绑定。

如果线程本来就要频繁回调 Java，优先考虑通过 Java 的 `Thread.start()` 创建。这样能自然获得合适的栈大小、线程组（ThreadGroup）、类加载器和调试工具中的可见性。

### 5.2 原生线程的本地引用不会按“调用返回”清理

普通原生方法返回 Java 时，本次调用创建的本地引用会失效并被清理。通过 `AttachCurrentThread()` 附着的纯原生线程可能长期不返回 Java；它创建的本地引用要到线程分离时才会自动释放。

循环里创建 `jstring`、对象或数组元素时要：

- 每轮调用 `DeleteLocalRef()`；
- 或使用 `PushLocalFrame()` / `PopLocalFrame()` 管理一批引用；
- 必要时使用 `EnsureLocalCapacity()` 预留容量。

JNI 规范只要求虚拟机保证至少 16 个本地引用槽位。Android 8 移除了旧的固定小容量限制，Android 17 的本地引用表（Local Reference Table）可以扩容，但初始存储和后续扩容仍会消耗进程资源；“可以扩容”不代表可以无限创建引用。长循环应优先按批次使用 `PushLocalFrame()` / `PopLocalFrame()`，并保证提前退出和异常路径也会弹出本地引用帧。

### 5.3 Attach、Detach 与操作系统线程的生命周期

首次调用 `AttachCurrentThread()` 不只是返回一个指针。ART 还要建立 `Thread`、`JNIEnvExt`、本地引用表、与原生线程配对的 Java `Thread` 对象、线程组和运行时登记。已经附着的线程再次调用会返回当前环境，但把附着与分离放进每个小任务，仍会增加生命周期管理的复杂度。

可靠的做法是让一个明确的组件管理长期运行的操作系统线程或有上限的线程池：线程入口先调用 `GetEnv()`，只在线程由该组件首次附着时记录 `attached_here=true`，退出时也只分离这类线程。用于在 C++ 作用域结束时自动清理资源的 RAII 对象，其生命周期必须覆盖整个操作系统线程，而不能只覆盖线程池中的单个任务；`JNIEnv*` 永远不能跨线程保存。

原生线程本身也有成本。Android 17 的 bionic `pthread_create()` 要建立线程栈、栈保护页（guard）和线程本地存储（TLS）映射，再通过 `clone` 创建内核任务；首次访问栈页还会触发缺页。默认栈预留的虚拟地址空间不等于会占用同等大小的驻留物理内存（RSS），但高频创建线程仍会叠加内存映射、TLS、调度实体、ART 附着和缓存预热成本。应根据真实栈深度测量所需的栈大小并复用线程，这通常比为每个数据块创建一个 pthread 更可靠。

## 6. 引用、异常与所有权

### 6.1 本地、全局与弱全局引用

- **本地引用（local reference）**：只在当前线程、当前 JNI 本地引用帧内有效；
- **全局引用（global reference）**：跨调用、跨线程保持对象可达，直到调用 `DeleteGlobalRef()`；
- **弱全局引用（weak global reference）**：不阻止 GC 回收对象。使用时应先调用 `NewLocalRef(weak)`，尝试把它提升为强本地引用；返回 `nullptr` 说明对象已经被回收。后续操作都使用这个本地引用，完成后再调用 `DeleteLocalRef()`。

两个 JNI 引用即使指向同一个 Java 对象，数值也可能不同。不能用 `==` 比较 `jobject`，应使用 `IsSameObject()`；也不能把原始 `jobject` 数值当作长期保存的映射表键。

不能先用 `IsSameObject(weak, nullptr)` 检查弱全局引用，再继续使用原弱引用：检查结束后，GC 仍可能立即回收对象。`NewLocalRef()` 的“提升并判空”会为本次操作建立一个稳定的强引用。

全局引用泄漏会让 Java 对象一直存活。Android Studio 的 JNI 堆视图（JNI heap view）可以查看全局 JNI 引用的创建位置和引用链。

### 6.2 JNI 异常不会像 C++ 异常自动展开

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

### 6.3 用 CheckJNI 找错误，不用它测性能

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

## 7. 字符串：UTF-16 与 Modified UTF-8

Java `String` 按 UTF-16 编码单元表示文本。JNI 中名称带 `UTF` 的 API 使用修改版 UTF-8（Modified UTF-8，MUTF-8），与网络、文件和大多数现代 C++ 库使用的标准 UTF-8 不完全相同。

- `GetStringChars()` / `GetStringRegion()` 面向 UTF-16。
- `GetStringUTFChars()` / `NewStringUTF()` 面向 Modified UTF-8。
- `GetStringLength()` 返回 UTF-16 编码单元（code unit）数量，不是 Unicode 码点（code point）数量；
- `GetStringUTFLength()` 返回的也不是标准 UTF-8 字节数。

不要把文件或网络收到的任意 UTF-8 直接交给 `NewStringUTF()`。无效 MUTF-8 会产生错误结果，CheckJNI 还会直接终止虚拟机进程。

Android 8 以后，ART 使用紧凑字符串表示，并采用可能移动对象位置的垃圾回收器（moving GC）。即使调用 `GetStringCritical()`，运行时也可能复制数据；API 名称中的 Critical 不代表承诺零拷贝。每个 `Get*Chars()` 都必须与对应的 `Release*Chars()` 配对，原生方法返回时不会自动释放取得的字符指针。

如果只需要读取字符串的一段，可用 `GetStringRegion()` 复制到调用方提供的缓冲区，避免先获取整串再做第二次复制。

## 8. 数组与 `DirectByteBuffer`

### 8.1 基本类型数组

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

### 8.2 `GetPrimitiveArrayCritical()` 不是通用加速开关

它也不保证一定返回原数组地址。进入 Critical 临界区后：

- 不要调用任意 JNI API。
- 不要做阻塞系统调用。
- 不要等待锁。
- 尽快完成并调用对应的 Release API。

这种 API 会限制虚拟机执行 GC 和移动堆对象的选择。只有在目标设备上完成测量，并且能严格控制临界区耗时后，才应使用。

### 8.3 直接缓冲区

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

## 9. 如何观察 JNI

Perfetto 的默认系统轨迹（system trace）不会自动为每次 JNI 跨界生成统一的轨迹区段。这里的轨迹区段也叫 slice，指一段带有开始、结束时间和名称的记录。常用证据有三类。

### 9.1 主动插桩

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

### 9.2 Simpleperf / Perfetto CPU sampling

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

### 9.3 微基准

测量一次 JNI 跨界的成本时，要避免混入其他变量：

- 调用方预热到稳定的 JIT/AOT 状态。
- C/C++ 函数只做能够防止编译器消除的最小工作。
- 分开测基本类型、`String`、数组和直接缓冲区。
- 记录设备、构建类型、CPU 频率策略、样本数和分位数。
- 关闭 CheckJNI、调试日志和 sanitizer 后再测发布版本的性能；sanitizer 是用于发现内存、线程等错误的运行时检查器。
- 同时保留开启检查的正确性测试。

只报告平均值会掩盖 GC、调度和锁带来的长尾，至少看 P50/P95/P99。

Android 17 源码中的 `benchmark/jni-perf` 可作为实验设计参考：它比较空 JNI 入口和 ART 内部路径，但依赖平台构建与内部头文件，不能直接复制到普通 APK，也不提供跨设备通用常数。应用侧应使用 AndroidX Microbenchmark，分别测试普通入口、Fast、Critical、`Region`、`Elements` 和批处理接口。测试代码还要实际使用返回值，避免编译器删除没有可见效果的工作。

## 10. 16KB 内存页：Android 17 上必须验证的原生代码边界

Android 15 起支持使用 16KB 内存页的设备。内存页是操作系统管理内存映射的基本单位。只要 APK 或 SDK 包含 `.so`，就要同时检查 ELF 文件、APK 打包布局，以及代码对运行时页大小所作的假设。ELF 是 Android 原生共享库 `.so` 使用的二进制格式。

### 10.1 两种对齐不能混为一谈

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

### 10.2 验证最终产物

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

### 10.3 Android 17 的立即报错验证

16KB 兼容模式（backcompat mode）可能让某些只按 4KB 对齐的应用暂时运行，但这不代表其中的原生库已经兼容。Android 17 可以在测试设备上关闭兼容模式，让不兼容的二进制文件在加载时立即终止进程：

```bash
adb shell setprop bionic.linker.16kb.app_compat.enabled fatal
adb shell setprop pm.16kb.app_compat.disabled true
```

这是设备级测试配置，完成验证后应恢复设置或重启设备。它适合持续集成（CI）设备或专用测试机，不要在日常使用的主力机上保留。

### 10.4 Play 要求与性能数字

从 2025-11-01 起，提交到 Google Play、且面向 Android 15 / API 35 及以上设备的新应用和更新必须支持 16KB 内存页。纯 Java/Kotlin 且所有依赖都不含原生代码的应用天然兼容，但仍应在 16KB 环境中做回归测试。

官方初步测试报告：

| 指标 | 平均变化 |
| --- | ---: |
| 内存压力下应用启动 | 降低 3.16%，部分样本最高 30% |
| 应用启动功耗 | 降低 4.56% |
| 相机热启动 / 冷启动 | 分别加快 4.48% / 6.60% |
| 系统启动 | 改善 8%，约 950ms |

16KB 页会平均增加一些内存使用。上述数字来自平台初步测试，不能当作单个应用的收益承诺；JNI/NDK 项目应先保证原生库能够可靠加载并正确运行，再用自己的设备验证性能变化。

## 11. JNI 不是 IPC 的替代品

JNI 解决同一进程内 Java/Kotlin 与 C/C++ 的互调。Binder/AIDL 解决跨进程通信，还承担调用方身份、权限、进程隔离和生命周期管理。

为了少一次 Binder 就把本应隔离的组件塞进同一进程，再用 JNI 传裸指针，通常会失去：

- 故障隔离。
- 权限边界。
- 进程死亡通知。
- 明确且可检查的数据序列化协议。
- 系统调度与可观测性。

如果服务本来就在 C++ 进程中，使用 NDK Binder 可以让通信接口继续留在 C/C++；如果 API 面向 Java/Kotlin 客户端，Java Binder 往往更自然。性能差异取决于传输的数据量、序列化方式、线程模型和进程安排，不能用固定百分比代替实测。

## 12. 版本边界

| Android 版本 | JNI/NDK 相关变化 |
| --- | --- |
| Android 8（API 26） | `@FastNative` / `@CriticalNative` 开始用于系统内部；`String` 的紧凑存储和会移动对象的 GC 改变了字符指针的复制假设 |
| Android 12（API 31） | 虚拟机内置的动态 JNI 查找开始可靠支持这两种注解；更早的系统需要显式注册 |
| Android 14（API 34） | `@FastNative` / `@CriticalNative` 成为通过兼容性测试套件（CTS）验证的公开 API |
| Android 15（API 35） | AOSP 支持使用 16KB 内存页的设备；Play 要求面向 Android 15 及以上版本的新提交与更新兼容该页大小 |
| Android 17（API 37） | 当前 JNI 语义继续沿用；16KB 测试增加 `fatal` 兼容模式，可让不兼容的原生库立即失败；AOSP 源码统一以 `android-17.0.0_r1` 为准 |

## 13. 常见误区

### “Native 一定比 Java/Kotlin 快”

不成立。ART 已能很好地优化许多 Java/Kotlin 高频路径；频繁 JNI 调用、数据复制和内存安全处理的成本，可能抵消 C/C++ 算法的收益。

### “Perfetto 默认会显示每次 JNI 跨界”

不成立。没有主动插桩时，通常只能结合 CPU 采样、函数符号和相邻轨迹进行判断。

### “`@CriticalNative` 可以传基本类型数组”

不成立。数组是托管对象，CriticalNative 会因对象参数触发校验错误。它只能使用基本类型标量，以及生命周期已经明确的原生句柄。

### “`AttachCurrentThread()` 可以每个任务调一次”

从接口行为看，对已经附加的线程再次调用只是空操作；但清晰的资源边界仍是在线程启动时附加、退出前分离。按任务反复管理，会让线程与虚拟机连接的所有权更难确认。

### “`GetPrimitiveArrayCritical()` 一定零拷贝”

不成立。虚拟机仍可选择复制；Critical 约束的是运行时协调方式和临界区规则，并不承诺零拷贝。

### “DirectByteBuffer 会自动管理 C/C++ 内存”

不成立。`NewDirectByteBuffer()` 不负责释放外部地址指向的内存；缓冲区对象或底层内存失效后，C/C++ 代码也不能继续使用该地址。

### “App 在 16KB 兼容模式能启动就算完成迁移”

不成立。兼容模式只是过渡机制。最终仍要验证 ELF 对齐、APK 中的 ZIP 对齐、所有第三方 `.so`，以及代码对运行时页大小的假设。

## 结论

JNI 优化按这个顺序做：

1. 先减少跨边界次数和数据转换量，把零碎调用合并成批量接口。
2. 缓存类以及方法、字段 ID，明确局部引用和全局引用的生命周期。
3. 让线程附加与分离跟随线程生命周期，并正确处理 `ClassLoader` 和待处理异常。
4. 用 CheckJNI 消除接口误用，再在接近发布配置的构建中，用 ATrace、Simpleperf 和微基准测量性能。
5. 只有短、可预测、不阻塞且调用频率极高的方法，才考虑 `@FastNative` / `@CriticalNative`。
6. C/C++ 产物必须在 16KB 设备上验证 ELF 对齐、APK 打包布局和运行时行为。

完成这些基础工作后，再讨论单次 JNI 跨界的纳秒级优化才有意义。

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
