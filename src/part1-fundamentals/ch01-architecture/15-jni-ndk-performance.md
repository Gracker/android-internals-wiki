---
title: JNI/NDK 性能优化
chapter: '1.15'
section: '1.15'
status: finalized
applicable_versions: Android 8.0 (API 26) - Android 17 (API 37)
last_verified: '2026-07-25'
last_verified_against: AOSP android-17.0.0_r1 + Android NDK official documentation
confidence: high
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
drafted_date: '2026-04-06'
reviewed_date: '2026-07-25'
reviewed_by: Codex
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed
pipeline_stage: ready-to-publish
deepseek_cn_review_state: done
task9_reviewed_date: "2026-05-20"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-07-16T14:25:40+08:00+08:00"
last_task2b_lite_at: "2026-07-16"
last_task6_at: "2026-07-16T13:20:00+08:00"
last_task6_audit: "2026-07-16"
last_task6_audit_result: l1-light-edit-revisiting
last_task2b_at: "2026-07-16T11:35:00+08:00"
last_task9_audit: "2026-07-17"
last_task9_review_log: "logs/deep-review/2026-07-16-14-deep-review.md"
task9_review_notes: "2026-07-16 14:25 Task9 深度复审：pass-tech-review。P0 0 / P1 0 / P2 2。P2 为版本演进表缺 Android 17 行、16KB page size 收益数据缺来源链接。原 queue.json P95 issue（2026-07-16T05:32:56Z AOSP 路径不可达）经验证为误判（android-17.0.0_r1 下所有引用路径均 HTTP 200），已标记为 resolved-false-positive。"
last_deepseek_cn_review_at: 2026-07-16
---

# 1.15 JNI/NDK 性能优化

JNI 优化应优先减少跨边界次数和数据编组，并正确管理线程与引用生命周期；继续压缩一次边界切换的十几纳秒排在这些工作之后。

音视频、图像、游戏和端侧推理经常需要 C/C++，但“native 天生比 Java/Kotlin 快”不是可靠结论。一个本来能被 ART JIT/AOT 优化的短循环，如果被拆成大量细粒度 JNI 调用，再叠加字符串转换、数组复制、引用管理和异常检查，整体可能更慢。

分析 JNI 路径时，把成本拆成四段：

```text
托管调用方
  └─ JNI transition
      ├─ 参数与引用处理
      ├─ Native 业务计算 / I/O / 锁
      └─ 返回值、异常与引用清理
          └─ Managed caller 继续执行
```

分析时应区分边界本身的成本与原生函数内部的成本，避免选错优化位置。

## 1. JNI 成本来自哪里

### 1.1 Transition

普通 JNI 调用需要让 ART 知道线程从托管状态进入原生状态，并按 JNI ABI 传递 `JNIEnv*`、`jobject` / `jclass` 和业务参数。返回时再恢复运行时状态、处理引用和异常。

官方 `@CriticalNative` 文档保留了一组 2016 年 7 月、`angler-userdebug` 上的参考数据：

| 路径 | 官方参考值 |
| --- | ---: |
| 普通 JNI | 115ns |
| `@FastNative` | 35ns |
| `@CriticalNative` | 25ns |

这些数字只说明当时设备上的相对量级。芯片、ART 版本、调用方是解释执行、JIT 还是 AOT、编译选项和方法签名都会改变结果，不能把 115ns 当作 Android 17 设备的固定常数。

调用次数会放大 transition。按这组旧参考值计算，1000 次普通 JNI 边界切换约为 115μs；真实路径还要加上参数处理和原生工作。比起争论 35ns 与 25ns，先把一帧内 1000 次调用合并成 1 次，通常更有价值。

### 1.2 数据编组与复制

primitive 标量最直接；`String`、数组和普通 Java 对象都需要运行时参与。

- `String` 可能发生 UTF-16 / Modified UTF-8 转换和复制。
- primitive 数组可能直接暴露指针，也可能复制到 native buffer。
- 对象字段和方法需要 `jfieldID` / `jmethodID`。
- native 回调 Java 又产生一次反向 transition。
- `DirectByteBuffer` 可让 native 直接访问地址，但需要明确内存所有权与生命周期。

很多所谓“JNI 慢”来自数据表示在两侧来回转换。

### 1.3 Native 函数内部

JNI 只是一扇门。门后面的锁、I/O、内存分配、算法复杂度和 cache miss 仍然按普通 C/C++ 性能问题处理。

`SystemProperties.java` 在 `android-17.0.0_r1` 里留下了一个很好的边界：

```java
// _NOT_ FastNative: native_set performs IPC and can block
private static native void native_set(String key, String def);
```

这个方法会做 IPC、可能阻塞，所以没有使用 `@FastNative`。即使 transition 变快，阻塞路径的墙上时间也不会因此消失。

## 2. 第一原则：让 JNI 接口更粗

官方 JNI tips 把“减少跨 JNI 编组的数据量与频率”放在通用建议首位。工程上可以从三个方向做。

### 2.1 批量传输

不要为每个元素调用一次 native：

```text
差：4096 次 JNI，每次传 1 个 short
好：1 次 JNI，传 short[] / DirectByteBuffer / native handle
```

批量并不意味着把 100MB 数据无条件复制一次。接口设计要结合数据主要由哪一侧访问：

- Java/Kotlin 侧读写更多：primitive 数组通常更自然。
- C/C++ 侧长期处理：native-owned buffer 或 direct buffer 更合适。
- 两侧只传控制信息：传 `long` 句柄，但必须防止悬空句柄、重复释放和跨实例误用。

### 2.2 少做跨语言异步回调

Java 线程池与原生线程池互相逐任务回调，会把线程附着、引用和生命周期问题扩散到大量工作线程。更容易维护的设计是让一侧拥有异步状态机，JNI 只在边界处传递批量输入与少量完成事件。

UI 更新通常留在托管侧：后台托管线程做一次阻塞 native 调用，结束后回到主线程发布结果，比 native worker 高频回调 UI 层更简单。

### 2.3 缓存类、字段与方法 ID

`FindClass()`、`GetMethodID()`、`GetFieldID()` 会做查找，不应放在热循环里。缓存时要分清两类值：

- `jmethodID` / `jfieldID` 是不透明 ID，不是 Java 对象引用，不要传给 `NewGlobalRef()`。
- `jclass` 属于 `jobject`，从 `FindClass()` 得到的是 local reference；跨调用保存前必须转成 global reference。

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

如果类可能随自定义 `ClassLoader` 卸载并重新加载，更稳的方案是从该 Java 类的静态初始化器调用 `nativeInit()`，在类每次初始化时重建缓存。无论采用哪种方式，全局引用不再使用时都要调用 `DeleteGlobalRef()`。

## 3. ClassLoader：原生线程的 `FindClass()` 为什么常失败

`JNI_OnLoad()` 是特殊入口。ART 会使用加载 `.so` 的类所对应的 ClassLoader，因此从应用调用 `System.loadLibrary()` 时，通常可以在这里找到应用类。

普通 JNI 调用中，`FindClass()` 使用 Java 调用栈顶部方法对应的 ClassLoader。问题出在 native 创建的线程：

1. `pthread_create()` / `std::thread` 创建线程。
2. 线程通过 `AttachCurrentThread()` 附着到 VM。
3. 当前栈上没有应用的 App Java frame。
4. `FindClass()` 回退到 system class loader。
5. 系统类加载器不认识应用自己的类。

常用解法：

- 在 `JNI_OnLoad()` 或 Java 类初始化器里查找并缓存 `jclass` global reference。
- Java 把 `Class` 实例传给 native。
- 缓存 App `ClassLoader`，需要时调用它的 `loadClass()`。

不要在 native worker 的热路径里反复调用 `FindClass()`，这同时有性能和正确性风险。

## 4. `@FastNative` 与 `@CriticalNative`

两个注解都减少 managed/native transition 成本，但 ABI 和使用范围不同。

| 维度 | 普通 JNI | `@FastNative` | `@CriticalNative` |
| --- | --- | --- | --- |
| Managed 对象参数/返回值 | 支持 | 支持 | 不支持 |
| 实例方法隐式 `this` | 支持 | 支持 | 不支持，必须是 static |
| Native 签名含 `JNIEnv*` | 是 | 是 | 否 |
| Native 签名含 `jobject` / `jclass` | 视方法而定 | 视方法而定 | 否 |
| 长 I/O / 可能长持有的原生锁 | 普通 JNI 仍应谨慎 | 禁止使用 | 禁止使用 |
| Android 14+ CTS 公共保证 | 普通 JNI | 是 | 是 |

### 4.1 `@FastNative` 可以使用托管对象

Android 17 的 `Parcel.java` 直接提供了例子：

```java
@FastNative
private static native void nativeWriteString16(
        long nativePtr, String val);
```

`@FastNative` 仍有 `JNIEnv*`，可以访问 managed heap、调用 JNI API，甚至回调 Java；其执行时间必须短且有界。

官方文档说明，线程执行 `@FastNative` 时，GC 不能为关键工作挂起它。不要在里面：

- 做显著 I/O。
- 等待可能长期持有的原生锁。
- 调用时长通常很短、但最坏情况无界的操作。
- 持有一把也可能被 Java 回调路径持有的原生锁。

最终一种模式可能让 GC、Java 线程和 FastNative 线程形成死锁。

### 4.2 `@CriticalNative` 只能使用 primitive

Android 17 的 `Binder.java`：

```java
@CriticalNative
public static final native int getCallingUid();
```

`@CriticalNative` 不能有任何 managed object 参数、返回值或隐式 `this`。数组也是对象，因此 `byte[]`、`int[]`、`String`、`ByteBuffer` 都不能放进 CriticalNative 签名。它适合 primitive 标量和以 `long` 表示的 native handle。

Java 侧：

```java
@CriticalNative
private static native int nativeWriteInt(long ptr, int value);
```

对应 C/C++ 实现只接收业务参数：

```cpp
static jint NativeWriteInt(jlong ptr, jint value) {
    // 没有 JNIEnv*，也没有 jclass。
    return 0; // 仅示意 ABI；真实实现应返回写入结果
}
```

没有 `JNIEnv*` 就意味着实现中不能调用 JNI API。CriticalNative 同样会阻止 GC 在关键工作中挂起当前线程，因此只适合短、可预测、不阻塞的代码。

### 4.3 注解之外还有兼容性要求

官方当前口径：

- Android 8 起用于系统内部。
- Android 14 / API 34 起成为经过 CTS-tested public API。
- 追求最大兼容性的应用不应在 Android 13 及以下调用这些注解方法。
- Android 8–10 没有内建 dynamic native lookup 支持，Android 11 还有已知问题；Android 8–11 必须显式调用 `RegisterNatives()`。
- Android 7 及以下忽略注解；CriticalNative 因 ABI 不匹配可能错误编组参数并崩溃。

即使只支持 Android 14+，官方仍建议性能关键方法使用 `RegisterNatives()`：签名错误在库加载时暴露，只需导出 `JNI_OnLoad()`，也避免依赖延迟 `dlsym()` 发现。

### 4.4 Baseline Profile 的角色

JNI 边界切换很快不代表托管调用方已经优化。如果启动热路径仍处于解释执行或 JIT 预热阶段，整体耗时会被调用方覆盖。把稳定的热调用方纳入 Baseline Profile，可以让比较聚焦于 JNI 与原生工作，避免首次编译噪声干扰。

Baseline Profile 不会自动合并 JNI 调用，也不会把不合格的方法变成 CriticalNative；它解决的是托管调用方的编译状态。

## 5. 线程附着与 `JNIEnv*`

### 5.1 `JNIEnv*` 只能属于当前线程

`JNIEnv*` 包含线程本地状态，不能存进全局变量供其他线程复用。进程级可共享的是 `JavaVM*`。

native 代码需要获得当前线程的环境时：

1. 用 `JavaVM::GetEnv()` 查询当前线程是否已经附加。
2. 尚未附加且要调用 JNI 时，使用 `AttachCurrentThread()` 或 `AttachCurrentThreadAsDaemon()`。
3. 线程退出前调用 `DetachCurrentThread()`。

对已经附加的线程再次附加是 no-op，但不应在每个任务前后反复执行。attach/detach 应与线程生命周期绑定。

如果线程本来就要频繁回调 Java，优先考虑从 Java `Thread.start()` 创建。这样能自然获得合适的栈大小、ThreadGroup、ClassLoader 和调试可见性。

### 5.2 native 线程的 local reference 不会按“调用返回”清理

普通原生方法返回 Java 时，本次调用创建的 local reference 会失效并被清理。通过 `AttachCurrentThread()` 附加的纯原生线程可能长期不返回 Java；它创建的 local reference 直到 detach 才会被自动释放。

循环里创建 `jstring`、对象或数组元素时要：

- 每轮 `DeleteLocalRef()`。
- 或用 `PushLocalFrame()` / `PopLocalFrame()` 管理一批引用。
- 必要时用 `EnsureLocalCapacity()` 预留容量。

JNI 规范只要求 VM 确保至少 16 个 local reference slot。Android 实现可能扩容，但“可能扩容”不是无限创建引用的理由。

## 6. 引用、异常与所有权

### 6.1 local、global、weak global

- **local reference**：只在当前线程、当前 JNI 局部帧内有效。
- **global reference**：跨调用、跨线程保持对象可达，直到 `DeleteGlobalRef()`。
- **weak global reference**：不阻止 GC 回收对象。使用时应先调用 `NewLocalRef(weak)` 提升为强 local reference；返回 `nullptr` 说明对象已被回收。后续操作都使用这个 local reference，完成后再调用 `DeleteLocalRef()`。

两个 JNI 引用即使指向同一个 Java 对象，数值也可能不同。不要用 `==` 比较 `jobject`，应使用 `IsSameObject()`。也不要把原始 `jobject` 数值当作长期 map key。

不要先用 `IsSameObject(weak, nullptr)` 检查 weak global reference，再继续使用原 weak reference：检查完成后 GC 仍可能回收对象。`NewLocalRef()` 的“提升并判空”可为本次操作建立稳定的强引用。

global reference 泄漏会让 Java 对象一直存活。Android Studio 的 JNI 堆视图可以查看全局 JNI 引用的创建位置与引用链。

### 6.2 JNI 异常不会像 C++ 异常自动展开

许多 JNI API 失败时会设置待处理的 pending Java exception，并返回 `nullptr` 或其他 sentinel。存在待处理异常后，只有一小部分 JNI 函数可以安全调用。

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

不要为“继续运行”随意调用 `ExceptionClear()`。只有 native 明确要把 Java 异常转换成另一种结果或异常时才清除，并确保 Java 侧仍能感知失败。

### 6.3 用 CheckJNI 找错误，不用它测性能

CheckJNI 会检查：

- `JNIEnv*` 是否在错误线程使用。
- reference 与 ID 类型是否匹配。
- pending exception 时是否调用了不允许的 JNI API。
- critical get/release 之间是否调用 JNI。
- Modified UTF-8 是否合法。
- 直接缓冲区参数、数组大小、释放模式等。

模拟器默认启用。普通设备可以在启动目标进程前设置：

```bash
adb shell setprop debug.checkjni 1
adb shell am force-stop com.example.app
```

CheckJNI 的额外检查会改变性能，不要用开启 CheckJNI 的 trace 代表 release 性能。应先用它消除 JNI 违规，再用接近发布配置、保留符号的构建测性能。

## 7. 字符串：UTF-16 与 Modified UTF-8

Java `String` 的语义是 UTF-16。JNI 中带 `UTF` 的 API 使用修改版 UTF-8（Modified UTF-8），并非网络、文件和大多数现代 C++ 库使用的标准 UTF-8。

- `GetStringChars()` / `GetStringRegion()` 面向 UTF-16。
- `GetStringUTFChars()` / `NewStringUTF()` 面向 Modified UTF-8。
- `GetStringLength()` 返回 UTF-16 码元数，不是 Unicode 码点数。
- `GetStringUTFLength()` 也不是标准 UTF-8 字节数。

不要把文件或网络收到的任意 UTF-8 直接交给 `NewStringUTF()`。无效 MUTF-8 会产生错误结果，CheckJNI 还会直接终止 VM。

Android 8 后，ART 使用紧凑字符串表示，并采用移动式 GC。即使调用 `GetStringCritical()`，运行时也可能复制数据；API 名中的 Critical 不等于零拷贝承诺。每个 `Get*Chars()` 都必须配对 `Release*Chars()`，native 方法返回不会替你释放原始字符指针。

如果只需要读取字符串的一段，可用 `GetStringRegion()` 复制到调用方提供的缓冲区，避免先获取整串再做第二次复制。

## 8. 数组与 `DirectByteBuffer`

### 8.1 Primitive 数组

`Get<PrimitiveType>ArrayElements()` 允许 VM：

- 返回指向托管数组的直接指针，并在此期间固定数组。
- 或分配 native buffer，把数组复制进去。

调用方不能假设哪一种发生。必须用对应 `Release<PrimitiveType>ArrayElements()` 结束生命周期。

释放模式的语义：

- `0`：如果拿到的是副本，就把修改复制回 Java；随后释放副本或解除固定。
- `JNI_ABORT`：如果拿到的是副本，就丢弃其中的修改；随后释放副本或解除固定。若 VM 直接返回了数组地址，已经发生的写入无法被“撤销”。
- `JNI_COMMIT`：如果拿到的是副本，就把修改复制回 Java，但不释放该副本；后续还要再次调用 Release 完成清理。

只读输入在语义允许时使用 `JNI_ABORT`，可以避免 VM 返回副本时无意义的回写。它不是通用的“回滚写入”选项。

### 8.2 `GetPrimitiveArrayCritical()` 不是通用加速开关

它也不保证一定返回原数组地址。进入关键区域后：

- 不要调用任意 JNI API。
- 不要做阻塞系统调用。
- 不要等待锁。
- 尽快完成并释放。

它给 VM 的 GC 和堆移动留下更少选择。只有经过目标设备测量，且能严格控制临界区时才使用。

### 8.3 Direct buffer

`ByteBuffer.allocateDirect()` 或 `NewDirectByteBuffer()` 创建的存储不在 managed heap 中，native 可用 `GetDirectBufferAddress()` 取得地址。

适合：

- 大块数据主要由 C/C++ 处理。
- 缓冲区跨多次 JNI 调用复用。
- 下游原生 API 本来就使用指针。

代价与风险：

- 分配、释放通常比 `byte[]` 重，应池化复用。
- Java 侧逐元素访问可能比普通数组慢。
- native 保存地址时，必须保证 `ByteBuffer` 或底层 native allocation 仍存活。
- `NewDirectByteBuffer()` 只是包装地址，不会自动接管 `malloc` 内存的释放。
- 容量、偏移、对齐和线程同步仍由业务保证。

“Direct”只说明可以取得原生地址，不等于整条处理链自动实现零拷贝；下游 API 仍可能复制。

## 9. 如何观察 JNI

默认的 Perfetto 系统跟踪不会自动为每次 JNI 边界切换生成统一片段。常用证据有三类。

### 9.1 主动插桩

第三方 NDK 代码使用稳定 API `<android/trace.h>`：

```cpp
#include <android/trace.h>

ATrace_beginSection("Decoder::decodeBatch");
DecodeBatch(input, output);
ATrace_endSection();
```

`ATrace_beginSection()` / `ATrace_endSection()` 必须在同一线程正确嵌套。名称构建有成本；复杂名称应先用 `ATrace_isEnabled()` 判断，避免关闭跟踪时仍做大量格式化。

平台内部代码还可以用：

- `cutils/trace.h` 的 `ATRACE_BEGIN()` / `ATRACE_END()`。
- `utils/Trace.h` 的 RAII 宏 `ATRACE_NAME()` / `ATRACE_CALL()`。

这些是平台内部接口，不应作为普通 NDK SDK 的稳定 API 暴露。

在 Java 与 native 两侧放相邻片段，可以分出：

```text
托管侧封装
  ├─ 参数准备
  ├─ native batch
  └─ 结果转换
```

相邻片段能把托管侧封装成本与原生批处理本体分开；仍需结合 CPU sampling，确认片段内部具体耗时符号。

### 9.2 Simpleperf / Perfetto CPU sampling

采样能回答“CPU 时间花在哪些符号”，也可能看到 ART JNI 跳板和 native call chain；它不能给出每一次调用的精确起止时长。

带符号的原生构建至少保留：

- unstripped `.so` 或独立 debug symbols。
- 正确的构建 ID。
- 与 APK 完全匹配的符号文件。
- 合适的 call graph 采集方式。

Simpleperf 的 protobuf 可以直接导入 Perfetto：

```bash
simpleperf report-sample \
  --protobuf \
  --show-callchain \
  -i perf.data \
  -o simpleperf.proto
```

Perfetto 界面/Trace Processor 解析的是采样点与调用栈，并不记录每次 JNI trace event。热点在原生算法时看采样；怀疑边界调用过碎时看调用次数、主动 slice 与微基准。

### 9.3 微基准

测量边界切换时要避免混入其他变量：

- 调用方预热到稳定的 JIT/AOT 状态。
- native 函数只做能够防止编译器消除的最小工作。
- 分开测 primitive、String、数组、direct buffer。
- 报告设备、build、CPU 频率策略、样本数和分位数。
- 关闭 CheckJNI、debug logging 和 sanitizer 后再测发布性能。
- 同时保留带检查的 correctness 测试。

只报告平均值会掩盖 GC、调度和锁带来的长尾，至少看 P50/P95/P99。

## 10. 16KB page size：Android 17 上必须验证的原生边界

Android 15 起支持 16KB 页大小的设备。只要 APK 或 SDK 包含 `.so`，就要同时检查 ELF、APK 打包和运行时页大小假设。

### 10.1 两种对齐不能混为一谈

1. **ELF LOAD segment alignment**：每个 `.so` 的 LOAD 段至少按 `2**14` 对齐。
2. **APK ZIP alignment**：未压缩 `.so` 在 APK 中也要放在 16KB 对齐边界。

一个 `.so` 的 ELF 对齐正确，不代表 App Bundle 最终生成的 APK 打包结果一定正确。

当前官方建议：

- AGP 8.5.1 或更高。
- NDK r28 或更高，默认生成按 16KB-aligned ELF。
- 所有预编译 `.so` 和第三方 SDK 也必须兼容。
- 去掉硬编码的 `PAGE_SIZE` / `4096`，运行时使用 `getpagesize()` 或 `sysconf(_SC_PAGESIZE)`。
- 复查 `mmap()`、文件偏移、共享内存和自定义 allocator 的对齐假设。

NDK r27 及更低版本可以按文档配置 linker flags，但升级工具链通常更稳。只重编自研库、遗漏 SDK 附带的 `.so`，最终 APK 仍不兼容。

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

设备页大小应返回 `16384`；ELF LOAD 对齐不应小于 `2**14`；bundletool 应显示 `PAGE_ALIGNMENT_16K`。

### 10.3 Android 17 的 fail-fast 验证

16KB 向后兼容模式可能让某些 4KB 对齐应用暂时运行，但这不代表二进制已经兼容。Android 17 可以在测试设备上关闭 backcompat，并让不兼容二进制立即中止：

```bash
adb shell setprop bionic.linker.16kb.app_compat.enabled fatal
adb shell setprop pm.16kb.app_compat.disabled true
```

这是设备级测试配置，完成验证后应恢复或重启设备。它适合 CI 设备或专用测试机，不要在日常主力机上随意保留。

### 10.4 Play 要求与性能数字

从 2025-11-01 起，提交到 Google Play、且面向 Android 15 / API 35 及以上设备的新应用和更新必须支持 16KB page size。纯 Java/Kotlin 且所有依赖都不含原生代码的应用天然兼容，但仍应在 16KB 环境做回归。

官方初步测试报告：

| 指标 | 平均变化 |
| --- | ---: |
| 内存压力下应用启动 | 降低 3.16%，部分样本最高 30% |
| App 启动功耗 | 降低 4.56% |
| Camera hot / cold start | 分别加快 4.48% / 6.60% |
| 系统启动 | 改善 8%，约 950ms |

16KB 页会平均增加一些内存使用。上述数字来自平台初步测试，不能当作单个应用的收益承诺；JNI/NDK 项目的首要目标是“能可靠加载并正确运行”，性能收益再用自己的设备验证。

## 11. JNI 不是 IPC 的替代品

JNI 解决同进程 managed/native 桥接。Binder/AIDL 解决跨进程边界，包含身份、权限、进程隔离和生命周期语义。

为了少一次 Binder 就把本应隔离的组件塞进同一进程，再用 JNI 传裸指针，通常会失去：

- 故障隔离。
- 权限边界。
- 进程死亡通知。
- 可审计的序列化契约。
- 系统调度与可观测性。

如果服务本来就在 C++ 进程中，使用 NDK Binder 可以保持原生调用栈；如果 API 面向 Java/Kotlin 客户端，Java Binder 往往更自然。性能差异取决于负载、序列化、线程与进程拓扑，不能用固定百分比替代实测。

## 12. 版本边界

| Android 版本 | JNI/NDK 相关变化 |
| --- | --- |
| Android 8（API 26） | `@FastNative` / `@CriticalNative` 开始用于系统内部；String 紧凑表示与移动式 GC 改变字符指针复制假设 |
| Android 12（API 31） | 两种注解的内建动态 JNI 查找进入可靠支持范围；更早系统需显式注册 |
| Android 14（API 34） | `@FastNative` / `@CriticalNative` 成为经过 CTS-tested public API |
| Android 15（API 35） | AOSP 支持 16KB 页大小的设备；Play 要求面向 Android 15+ 的新提交与更新兼容该页大小 |
| Android 17（API 37） | 当前 JNI 语义继续沿用；16KB 测试增加 `fatal` backcompat 模式，可让不兼容 binary 立即失败；AOSP 源码统一锚定 `android-17.0.0_r1` |

## 13. 常见误区

### “Native 一定比 Java/Kotlin 快”

不成立。ART 已能很好优化许多托管热路径；JNI 次数、复制和内存安全成本可能抵消原生算法收益。

### “Perfetto 默认会显示每次 JNI transition”

不成立。没有主动插桩时，通常依赖 CPU sampling、符号和上下文推断。

### “`@CriticalNative` 可以传 primitive array”

不成立。数组是 managed object，CriticalNative 会因对象参数触发校验错误。只使用 primitive 标量和明确生命周期的 native handle。

### “`AttachCurrentThread()` 可以每个任务调一次”

技术上对已附加线程再次调用是 no-op，但正确的资源边界是线程启动时附加、退出前分离。逐任务管理会让所有权更难审计。

### “`GetPrimitiveArrayCritical()` 一定零拷贝”

不成立。VM 仍可复制；Critical 约束的是运行时协调方式和临界区规则，不是零拷贝承诺。

### “DirectByteBuffer 自动管理原生内存”

不成立。`NewDirectByteBuffer()` 不接管外部地址的释放，native 也不能在 buffer 或 allocation 失效后继续使用地址。

### “App 在 16KB 兼容模式能启动就算完成迁移”

不成立。backcompat 只是过渡机制。最终要验证 ELF、ZIP alignment、所有第三方 `.so` 和运行时页大小假设。

## 结论

JNI 优化按这个顺序做：

1. 先减少跨边界次数和编组量，把接口改成批量、粗粒度。
2. 缓存类与方法/字段 ID，明确 local/global reference 生命周期。
3. 让附加/分离跟线程生命周期绑定，处理类加载器与待处理异常。
4. 用 CheckJNI 消除违规，再在 release-like 构建中用 ATrace、Simpleperf 和微基准测性能。
5. 只有短、可预测、不阻塞的极热方法才考虑 `@FastNative` / `@CriticalNative`。
6. native 产物必须在 16KB 设备验证 ELF、APK 打包和运行时行为。

完成这些基础工作后，transition 的纳秒级优化才有意义。

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
