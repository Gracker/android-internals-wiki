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

JNI 性能问题很少由某一条指令单独决定。一次跨边界调用会叠加入口桩、线程状态、引用管理、参数转换、数据复制、native 算法和线程生命周期等成本。调用频率达到每帧数百次后，原本很小的边界成本也会进入帧预算；单次 native 工作持续数毫秒时，算法和锁竞争通常占据主要时间。

§1.15 已介绍 JNI 的通用用法。下面沿 Android 17 的 ART 实现向下追踪调用路径，回答以下问题：

- 普通 JNI、`@FastNative` 与 `@CriticalNative` 分别省掉了哪些步骤；
- `RegisterNatives` 改变的是哪一段成本；
- Android 17 上数组 Elements、Region 与 Critical API 的复制行为；
- Local/Global Reference、线程挂载和 native 线程创建如何进入性能账单；
- 怎样用 trace、采样和 Microbenchmark 分开测量边界与业务代码。

平台锚点为 AOSP `android-17.0.0_r1`，内核锚点为 `android17-6.18-2026-06_r6`。不同厂商构建、编译模式、CPU 微架构和温控状态都会改变绝对耗时，某组设备上的纳秒数不能当作平台常量。

## 1. 先建立可计算的成本模型

一批 JNI 工作的总耗时可以近似拆成：

`总耗时 = 调用次数 × 单次边界成本 + 数据转换与复制 + native 工作 + 等待与调度`

这个公式能直接指导排查顺序。

| 观察 | 优先检查 | 常见改法 |
| --- | --- | --- |
| 空 native 方法已占据可见 CPU 时间 | 调用次数、入口类型、编译状态 | 批量接口，减少逐元素调用 |
| native 方法本身很长 | 算法、锁、I/O、CPU 采样栈 | 优化 native 主体，避免先改 JNI 注解 |
| 数组越大越慢 | Elements/Region、复制方向、临时分配 | 明确所有权，按访问模式选择 API |
| GC 暂停与 Critical 区间重叠 | `GetPrimitiveArrayCritical`、Fast/Critical 长调用 | 缩短临界区，不在其中等待 |
| 运行一段时间后引用表或内存增长 | Local/Global Reference 生命周期 | 分批弹出 Local Frame，配对删除 Global Ref |
| native 线程频繁创建和退出 | `pthread_create`、Attach/Detach、线程池粒度 | 复用少量物理线程 |

边界优化最常见的收益来自“少调用几次”。把一万个 `nativeProcessOne(value)` 合成一次 `nativeProcessBatch(values)`，会同时减少入口桩、线程状态处理、引用帧和 Java/native 调度开销。注解优化只减少其中若干步骤，无法抵消不合适的接口粒度。

## 2. Android 17 的 JNI 入口路径

### 2.1 通用 JNI 跳板的 5120 字节是什么

尚未走专用编译桩的 native 方法可以进入 generic JNI trampoline。Android 17 的 `entrypoint_asm_constants.h` 定义 `GENERIC_JNI_TRAMPOLINE_RESERVED_AREA` 为 5120，ARM64 汇编入口会从栈指针减去这段空间，再调用 `artQuickGenericJniTrampoline` 计算参数布局。

这 5120 字节有三个边界：

- 它是 generic quick trampoline 的栈预留空间；
- 它不是一次 5120 字节的堆分配；
- 它也不是所有 JNI 调用都会产生的固定成本。

栈指针调整本身不能直接换算成耗时。通用桩还会根据 shorty 描述处理整数、浮点和引用参数，准备 `JNIEnv*` 与接收者，并在返回阶段恢复引用和线程状态。AOT/JIT 编译出的 JNI stub 已知方法签名，可以按目标 ISA 的调用约定生成更紧凑的路径。

源码入口：

- [`GENERIC_JNI_TRAMPOLINE_RESERVED_AREA`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/entrypoints/entrypoint_asm_constants.h)
- [ARM64 generic JNI 汇编入口](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/arch/arm64/quick_entrypoints_arm64.S)
- [`artQuickGenericJniTrampoline`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/entrypoints/quick/quick_trampoline_entrypoints.cc)

### 2.2 普通 JNI 会切到 Native 状态

普通 JNI 入口通过 `artJniMethodStart` 把线程从 Runnable 切换到 `kNative`。返回时，`artJniMethodEnd` 将线程切回 Runnable，并处理挂起请求。转换的目的包括释放 mutator lock 的共享持有状态，让 GC 可以在当前线程执行 native 代码时推进。

这带来一个容易写反的结论：

> 普通 JNI 方法在纯 native 代码里长时间计算，不会仅因“仍在 native 方法中”就挡住 GC。ART 把 `kNative` 线程视为已经挂起。它通过 JNI API 再次访问托管对象时，运行时会执行相应的访问检查和状态协调。

会拖延 GC 的路径另有来源，例如长时间保持 Primitive Critical 区间，或者让 Fast/Critical Native 方法长时间运行。二者都绕开了普通 JNI 的完整状态转换。

Android 17 的对应实现位于：

- [`artJniMethodStart` / `artJniMethodEnd`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/entrypoints/quick/quick_jni_entrypoints.cc)
- [JNI trampoline 的起止处理](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/entrypoints/quick/quick_trampoline_entrypoints.cc)

### 2.3 引用参数为什么比纯标量更重

普通 native 实例方法的 ABI 包含 `JNIEnv*` 和 `jobject`；静态方法包含 `JNIEnv*` 和 `jclass`。其他对象参数也要以 GC 可追踪的形式进入引用表或栈根。入口与出口需要处理：

1. JNI Local Reference Table 的调用段；
2. `jobject`、`jclass`、数组和字符串等引用参数；
3. 引用类型返回值的解码；
4. 待处理异常和 CheckJNI 检查。

纯 primitive 参数省去了对象引用管理，但普通 JNI 仍保留线程状态转换和 `JNIEnv*`/接收者 ABI。由此可知，`int`、`long` 参数的小函数更容易让边界成本占据高比例。

### 2.4 编译桩可以复用，但条件比“签名相同”更细

Android 17 的 `JniStubKey` 会考虑 static、synchronized、Fast、Critical 等访问标志、shorty 和目标 ISA。ART 还会把调用约定上等价的参数布局归并，使若干方法复用同一份编译 JNI stub。

所以“每个 native 方法都有完全独立的一套桩”和“签名相同就一定共用桩”都不够准确。复用由 ART 按 ABI 等价关系判定，应用不能依赖具体代码地址。源码可查阅 [`jni_stub_hash_map.h`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/oat/jni_stub_hash_map.h) 与对应的 [编译器测试](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/compiler/oat/jni_stub_hash_map_test.cc)。

## 3. 普通、Fast 与 Critical Native 的边界

三条路径省略的工作不同。

| 路径 | 线程状态转换 | `JNIEnv*` | 对象参数 | Local Reference 调用段 | 适合的工作 |
| --- | --- | --- | --- | --- | --- |
| 普通 JNI | Runnable ↔ Native | 有 | 支持 | 有 | 通用调用、可能较长的 native 工作 |
| `@FastNative` | 保持 Runnable | 有 | 支持 | 有 | 很短、无阻塞、仍需 JNI API 的方法 |
| `@CriticalNative` | 保持 Runnable | 无 | 不支持 | 无 | static、纯 primitive、极短的叶子函数 |

`@FastNative` 和 `@CriticalNative` 执行期间，线程仍处于 Runnable。GC 发出挂起请求后，Fast 路径通常要等方法返回并执行 `CheckSuspend()`；Critical 路径也没有普通 JNI 的挂起转换。因此两种方法都不能承载锁等待、文件或网络 I/O、睡眠、不可控循环及长算法。

`@CriticalNative` 还改变了 native ABI：没有 `JNIEnv*`，也没有 `jclass`。它只能用于 static native 方法，参数和返回值只能是 primitive。下面的声明用于展示这组约束：

```java
import dalvik.annotation.optimization.CriticalNative;
import dalvik.annotation.optimization.FastNative;

final class NativeMath {
    private NativeMath() {}

    @CriticalNative
    static native long add(long left, long right);

    @FastNative
    static native int checksum(byte[] data);
}
```

`add` 不能接收数组、字符串或对象，也不能抛出 Java 异常；`checksum` 仍有常规 JNI 参数和引用能力。注解没有替开发者证明函数足够短，是否会阻塞仍要由代码审阅和 trace 验证。

下面的 native 声明对应动态符号查找时的两种 ABI：

```cpp
extern "C" JNIEXPORT jlong JNICALL
Java_com_example_NativeMath_add(jlong left, jlong right) {
  return left + right;
}

extern "C" JNIEXPORT jint JNICALL
Java_com_example_NativeMath_checksum(
    JNIEnv* env, jclass, jbyteArray data) {
  // 省略数组读取和校验。
  return 0;
}
```

Critical 方法没有 `JNIEnv*` 和 `jclass`；Fast 方法的 C++ 签名与普通 static JNI 一致。若改用 `RegisterNatives`，函数指针仍须匹配各自 ABI，签名错配会造成未定义行为。

### 3.1 版本兼容边界

| Android 版本 | Fast/Critical 的应用侧边界 |
| --- | --- |
| Android 8～11 | Critical Native 需要显式 `RegisterNatives`；依赖动态符号发现可能失败 |
| Android 12～13 | 运行时支持 Critical Native 的动态符号发现；低版本兼容仍需单独设计 |
| Android 14～17 | 两个注解进入公开 API 并受 CTS 约束；运行时限制保持 |

官方文档建议，若 APK 还要兼容 Android 13 及更低版本，应谨慎使用公开注解，或准备按版本隔离的实现。最低适用范围是 Android 8，因此不能只在 Android 17 设备上验证一次就宣称兼容全范围。

ARM64 编译器中，Critical stub 可在没有栈参数、没有返回值扩展等条件满足时使用 tail call；条件不满足时仍会生成参数搬运和返回处理。固定的“4 条指令”无法覆盖不同签名、ISA、编译状态和插桩配置。可复核 [Android 17 ARM64 JNI calling convention](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/compiler/jni/quick/arm64/calling_convention_arm64.cc)。

## 4. `RegisterNatives` 优化的是绑定，不会改变 native 属性

没有显式注册时，首次调用要构造短名和长名，并在与声明类 ClassLoader 关联的 JNI 库中查找符号。ART 找到地址后会注册到对应 `ArtMethod`，后续调用通常直接使用已缓存的入口。

`RegisterNatives` 的主要价值包括：

- 在 `JNI_OnLoad` 阶段集中验证类名、方法名和签名；
- 提前建立 `ArtMethod` 到函数指针的映射，避开首次调用的 `dlsym` 查找；
- 动态符号表只需导出 `JNI_OnLoad`，减少可见符号；
- Critical Native 在 Android 8～11 上可获得明确的绑定路径。

Java 方法是否为 native 已经写在方法访问标志中。显式注册不会让编译器到注册时才“发现它是 native”，也不能自动把普通 JNI 变成 Fast 或 Critical。

下面的注册代码演示了失败检查与 Local Reference 清理：

```cpp
#include <jni.h>

namespace {

jlong NativeSum(JNIEnv*, jclass, jlong left, jlong right) {
  return left + right;
}

const JNINativeMethod kMethods[] = {
    {
        "nativeSum",
        "(JJ)J",
        reinterpret_cast<void*>(NativeSum),
    },
};

}  // namespace

JNIEXPORT jint JNI_OnLoad(JavaVM* vm, void*) {
  JNIEnv* env = nullptr;
  if (vm->GetEnv(
          reinterpret_cast<void**>(&env),
          JNI_VERSION_1_6) != JNI_OK) {
    return JNI_ERR;
  }

  jclass clazz = env->FindClass("com/example/NativeBridge");
  if (clazz == nullptr) {
    return JNI_ERR;
  }

  const jint result = env->RegisterNatives(
      clazz,
      kMethods,
      sizeof(kMethods) / sizeof(kMethods[0]));
  env->DeleteLocalRef(clazz);
  return result == JNI_OK ? JNI_VERSION_1_6 : JNI_ERR;
}
```

`FindClass` 或 `RegisterNatives` 失败时返回 `JNI_ERR`，系统不会继续加载一份绑定不完整的库。生产代码还应让类名和签名由测试覆盖；混淆配置也要保证声明类与方法符合注册表预期。

Android 17 的查找与注册路径可从 [`jni_entrypoints.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/entrypoints/jni/jni_entrypoints.cc)、[`java_vm_ext.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/jni/java_vm_ext.cc) 和 [`jni_internal.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/jni/jni_internal.cc) 交叉核对。

## 5. Android 17 的 primitive 数组访问

JNI 规范允许 VM 对 Elements API 选择直接指针或副本。具体到 Android 17，ART 的实现给出了更明确的行为。

| API | Android 17 中的主要行为 | 持有期间的约束 |
| --- | --- | --- |
| `Get<Type>ArrayRegion` | 边界检查后，把指定区间复制到调用方缓冲区 | 调用结束后无持续约束 |
| `Set<Type>ArrayRegion` | 边界检查后，从调用方缓冲区复制回数组 | 调用结束后无持续约束 |
| `Get<Type>ArrayElements` | 可移动数组分配 native 副本并复制；不可移动数组可返回直接地址 | 必须配对 Release；副本可能增加分配与带宽 |
| `GetPrimitiveArrayCritical` | Android 17 对可移动数组暂停 moving GC 或 thread flip，重新解码后返回直接数据地址，`isCopy=false` | 区间内不能阻塞，也不能调用大多数 JNI API |

旧经验常把 Elements 描述成“固定数组并返回堆内指针”。这不符合 Android 17 对可移动数组的普通路径：ART 会分配副本并执行 `memcpy`。相反，Android 17 的 Primitive Critical 实现会提供直接地址，并以限制移动 GC 为代价。

这只是当前平台实现，不能把 `isCopy=false` 写进跨 VM 的程序假设。可移植代码仍应遵守 JNI 规范：检查返回指针、配对 Release、正确选择 mode，并把 Critical 区间压到足够短。

### 5.1 Region 适合一次明确的复制

读取固定长度头部时，Region API 可以省去 Get/Release 配对和临时 Elements 副本。下面的函数只复制需要的字节：

```cpp
#include <array>
#include <cstdint>
#include <cstring>

struct PacketHeader {
  std::uint32_t type;
  std::uint32_t payload_size;
};

bool ReadHeader(
    JNIEnv* env,
    jbyteArray source,
    PacketHeader* output) {
  if (source == nullptr || output == nullptr) {
    return false;
  }

  constexpr jsize kHeaderSize = sizeof(PacketHeader);
  if (env->GetArrayLength(source) < kHeaderSize) {
    return false;
  }

  std::array<jbyte, kHeaderSize> bytes{};
  env->GetByteArrayRegion(
      source,
      0,
      kHeaderSize,
      bytes.data());
  if (env->ExceptionCheck()) {
    return false;
  }

  std::memcpy(output, bytes.data(), kHeaderSize);
  return true;
}
```

这段代码有一次显式区间复制，生命周期很清楚。协议字段还应按约定字节序解码；示例只聚焦 JNI 数组边界。

### 5.2 Elements 适合需要连续访问并明确回写的代码

下面的示例展示读写数组时 Release mode 的选择：

```cpp
bool ClampSamples(JNIEnv* env, jshortArray samples) {
  if (samples == nullptr) {
    return false;
  }

  jboolean is_copy = JNI_FALSE;
  jshort* values =
      env->GetShortArrayElements(samples, &is_copy);
  if (values == nullptr) {
    return false;
  }

  const jsize count = env->GetArrayLength(samples);
  for (jsize i = 0; i < count; ++i) {
    if (values[i] < -30000) values[i] = -30000;
    if (values[i] > 30000) values[i] = 30000;
  }

  env->ReleaseShortArrayElements(samples, values, 0);
  return !env->ExceptionCheck();
}
```

mode `0` 表示复制修改并释放缓冲区；只读场景可用 `JNI_ABORT` 避免回写；`JNI_COMMIT` 会提交修改但保留 Elements 缓冲区，后面仍要再 Release。`is_copy` 可用于诊断，业务正确性不能依赖它的取值。

### 5.3 Primitive Critical 要按 GC 临界区审阅

`GetPrimitiveArrayCritical` 与 `ReleasePrimitiveArrayCritical` 之间只做短、有限、无阻塞的内存访问：

- 不等待 mutex、condition variable 或 future；
- 不执行文件、Binder、socket 和设备 I/O；
- 不回调 Java；
- 不调用可能阻塞或触发复杂运行时工作的 JNI API；
- 所有退出路径都执行 Release。

数组较大并不能自动证明 Critical 更快。普通 Elements 可能产生副本成本，Critical 则把压力转移到 GC 协调。应在目标设备上同时观察 CPU、复制量、GC pause 和尾延迟。

Android 17 的数组实现位于 [`jni_internal.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/jni/jni_internal.cc)。

## 6. Local Reference 与 Global Reference

### 6.1 Android 8 移除固定小上限，不代表资源无限

旧版 Dalvik/ART 曾有较小的 Local Reference 固定容量。Android 8 移除了这项版本相关限制，官方 JNI 文档常用“unlimited local references”描述行为变化。Android 17 的实现仍受进程资源与表大小约束：

- Local Reference Table 的初始存储为 512 字节；
- 容量不足时动态扩展；
- 实现中的硬上限为 128 MiB；
- CheckJNI 会为检测信息使用更多 entry；
- 表项是 GC root，过多引用会增加 GC root 扫描和内存开销。

所以“不再有旧固定上限”只表示表会增长。长循环若一直保存 Local Reference，仍可能因内存耗尽失败。

### 6.2 `PushLocalFrame` 要在循环中周期性弹出

在 10000 次循环外只 Push 一次 frame，并不会控制 frame 内部峰值。下面的写法每批处理 32 个对象：

```cpp
bool VisitItems(
    JNIEnv* env,
    jobject source,
    jmethodID item_at,
    jsize item_count) {
  constexpr jsize kBatchSize = 32;

  for (jsize base = 0; base < item_count;
       base += kBatchSize) {
    if (env->PushLocalFrame(kBatchSize) != JNI_OK) {
      return false;
    }

    bool batch_ok = true;
    const jsize end =
        std::min(item_count, base + kBatchSize);
    for (jsize i = base; i < end; ++i) {
      jobject item =
          env->CallObjectMethod(source, item_at, i);
      if (env->ExceptionCheck() || item == nullptr) {
        batch_ok = false;
        break;
      }
      ConsumeItem(env, item);
      if (env->ExceptionCheck()) {
        batch_ok = false;
        break;
      }
    }

    env->PopLocalFrame(nullptr);
    if (!batch_ok) {
      return false;
    }
  }
  return true;
}
```

每次 `PopLocalFrame` 会批量丢弃这一批的 Local Reference，即使循环提前结束也能恢复 frame。示例假定 `ConsumeItem` 和 `<algorithm>` 已在工程中定义；异常应由上层按接口约定传播或清除。

附着自 native 创建的线程时，Local Reference 不会像 Java 方法帧那样由某个托管返回点自动整理。线程仍要主动删除循环内引用，并在退出前 Detach。

Android 17 的结构与扩容逻辑可查阅 [`local_reference_table.h`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/jni/local_reference_table.h) 和 [`local_reference_table.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/jni/local_reference_table.cc)。

### 6.3 Global Reference 泄漏怎样定位

Global Reference 与 Weak Global Reference 都必须由代码明确释放。Java heap 对象可能因 Global Reference 一直存活，即使 Java 侧已经没有普通引用。

可用三层证据定位：

1. Android Studio Profiler 的 **JNI heap** 视图查看 Global Reference 及其 native 分配/释放调用栈；
2. `adb shell dumpsys meminfo -d <package>` 观察 `.IndirectRef` 内存趋势；
3. 在 `NewGlobalRef`/`DeleteGlobalRef` 的封装层记录带类型、调用点和对象用途的计数。

`.IndirectRef` 是 ART 间接引用表占用的内存，混合了 local/global 等信息，不能当成 Global Reference 的精确对象数。`Debug.getGlobalAllocCount()` 一类 Java API 也不提供 JNI Global Reference 的可靠计数。

## 7. native 线程的 Attach/Detach 边界

`JNIEnv*` 属于线程，不能缓存后交给另一条线程。`JavaVM*` 可以跨线程保存，用它查询或挂载当前线程。

Android 17 中，`AttachCurrentThread` 在首次挂载时会创建 ART `Thread`、初始化 `JNIEnvExt` 和 Local Reference Table、加入线程列表，并建立 Java `Thread` peer、线程组与名称等运行时状态。已经挂载的线程再次调用会返回当前 `JNIEnv*`，但频繁查询和错误的生命周期设计仍会增加复杂度。

下面的 RAII 对象只在本作用域完成首次挂载时负责 Detach：

```cpp
class ScopedJniEnv {
 public:
  explicit ScopedJniEnv(JavaVM* vm) : vm_(vm) {
    const jint status = vm_->GetEnv(
        reinterpret_cast<void**>(&env_),
        JNI_VERSION_1_6);
    if (status == JNI_EDETACHED) {
      attached_here_ =
          vm_->AttachCurrentThread(&env_, nullptr) == JNI_OK;
      if (!attached_here_) {
        env_ = nullptr;
      }
    } else if (status != JNI_OK) {
      env_ = nullptr;
    }
  }

  ~ScopedJniEnv() {
    if (attached_here_) {
      vm_->DetachCurrentThread();
    }
  }

  JNIEnv* get() const { return env_; }

  ScopedJniEnv(const ScopedJniEnv&) = delete;
  ScopedJniEnv& operator=(const ScopedJniEnv&) = delete;

 private:
  JavaVM* vm_;
  JNIEnv* env_ = nullptr;
  bool attached_here_ = false;
};

void* WorkerMain(void* argument) {
  auto* vm = static_cast<JavaVM*>(argument);
  ScopedJniEnv scoped_env(vm);
  if (scoped_env.get() == nullptr) {
    return nullptr;
  }

  RunWorkerLoop(scoped_env.get());
  return nullptr;
}
```

RAII 生命周期覆盖整条物理工作线程，而非线程池中的单个小任务。已有 Java/Kotlin 线程进入 native 时，`GetEnv` 返回现成环境，析构不会错误地 Detach 它。长期运行的第三方线程池也可以用 `pthread_key_create` 的析构回调把 Detach 绑定到线程退出。

线程退出时忘记 Detach 会留下运行时状态。Android 17 的 TLS 析构路径会记录错误，并在无法安全恢复时终止进程，因此不能把 Detach 当成可省略的清理动作。实现细节见 [`java_vm_ext.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/jni/java_vm_ext.cc) 与 [`thread.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread.cc)。

## 8. `pthread_create` 的成本从哪里来

“创建一个 native 线程需要多少微秒”没有跨设备答案。Android 17 的 bionic 和 6.18 内核源码提供了更稳定的成本分解。

### 8.1 bionic 用户空间

Android 17 的 `pthread_create.cpp` 会：

1. 为 guard、stack、static TLS、TCB、libgen 缓冲区和顶部 guard 计算一段映射；
2. 使用 `mmap(MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE)` 建立虚拟地址空间；
3. 用 `mprotect` 开放可写区域并初始化 TLS、stack guard 等状态；
4. 通过 `clone` 创建共享地址空间的内核 task；
5. 在子线程完成启动握手、信号栈、shadow call stack、信号掩码等设置后进入用户函数。

bionic 默认栈配置以约 1 MiB 为基准，再扣除备用信号栈空间。`MAP_NORESERVE` 让这段大小主要表现为虚拟地址预留，物理页按访问逐步进入 RSS。因此“每个 pthread 一创建就常驻 1 MiB 物理内存”也不准确。

源码可核对 [Android 17 `pthread_create.cpp`](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/pthread_create.cpp) 与 [`pthread_internal.h`](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/pthread_internal.h)。

### 8.2 Linux 6.18 内核

`clone` 进入 `copy_process` 后，内核要分配 task 结构、执行调度器初始化，并按 clone flags 复制或共享 files、fs、sighand、signal、mm 等资源。`CLONE_VM`、`CLONE_FILES`、`CLONE_THREAD` 等标志使 pthread 与进程内其他线程共享主要进程资源，但 task、内核栈、调度实体和线程 ID 仍是独立对象。

这条路径解释了频繁创建线程为何会出现：

- 用户空间映射和 TLS 初始化；
- 内核对象分配与调度器工作；
- ART Attach 的额外运行时对象；
- 首次触碰栈页带来的缺页；
- CPU 唤醒、迁移和缓存冷启动。

内核锚点可查阅 [`android17-6.18-2026-06_r6/kernel/fork.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/fork.c)。

工程上应复用有上限的线程池，把 Attach 生命周期绑定到物理线程，并根据栈深度设置经过测量的 stack size。把每个数据块交给新 pthread，通常会让生命周期成本淹没 native 计算。

## 9. 数据所有权比“零拷贝”更重要

跨 JNI 传递数据时，可选方案各自交换了复制、生命周期和 GC 约束。

| 方案 | 复制特征 | 生命周期风险 | 适用场景 |
| --- | --- | --- | --- |
| primitive Region | 一次明确复制 | 低 | 小区间、固定头部、单次处理 |
| primitive Elements | 可移动数组通常产生副本 | Release mode 与临时内存 | 连续读写、代码已有数组接口 |
| Primitive Critical | Android 17 直接地址 | 限制 GC，API 使用受限 | 极短的连续内存操作 |
| Direct `ByteBuffer` | Java/native 可共享 native 内存 | buffer、指针和容量必须共同存活 | 大块数据、多次复用 |
| native handle | Java 保存 `long` 标识 | 释放、并发、重复关闭 | 长寿命 native 对象 |

Direct `ByteBuffer` 的地址只在底层 native 内存仍有效时可用。native 侧若跨调用保存 `GetDirectBufferAddress` 的结果，必须同时建立可证明的 owner 生命周期；常见办法是让 Java owner 持有 buffer，并由一个显式 close 协议释放 native 资源。只缓存裸指针却放弃 buffer/owner 的强引用，会把“零拷贝”变成悬空指针风险。

更完整的缓存 ID、异常、字符串、Direct Buffer 和 native handle 规则见 [§1.15 JNI/NDK 互操作性能](../../part1-fundamentals/ch01-architecture/15-jni-ndk-performance.md)。

## 10. 怎样测出边界开销

### 10.1 trace 只能测被标记的区间

Perfetto 不会默认把每一次 JNI transition 标成独立 slice。若在 Java 调用外层放一个 `Trace.beginSection`，再在 native 函数入口放一个 `ATrace_beginSection`，内层 slice 测到的是 native 函数主体；两层之间的差值还混有 trace 调用、Java 包装、参数准备和调度噪声。

适合 trace 的做法是：

- 用外层 slice 表示一次业务请求；
- 用内层 slice 分出 native 算法阶段；
- 在一帧内另行记录 JNI 调用计数与数据字节数；
- 对高频小调用做采样或批量标记，避免 trace 本身改变被测路径。

下面的 RAII 标记保证异常式 C++ 退出路径也能结束 native slice：

```cpp
#include <android/trace.h>

class ScopedTrace {
 public:
  explicit ScopedTrace(const char* name) {
    ATrace_beginSection(name);
  }

  ~ScopedTrace() {
    ATrace_endSection();
  }

  ScopedTrace(const ScopedTrace&) = delete;
  ScopedTrace& operator=(const ScopedTrace&) = delete;
};

void DecodeBatch(const std::uint8_t* data, std::size_t size) {
  ScopedTrace trace("native/DecodeBatch");
  DecodePackets(data, size);
}
```

这个 slice 包围的是 `DecodePackets` 主体，不能单独给出 JNI 入口耗时。若它已经占据大部分外层请求时间，应先采样 `DecodePackets`；若外层明显更长，再用 Microbenchmark 缩小到边界测试。

### 10.2 CPU sampling 用来回答“时间花在哪个 native 符号”

Perfetto callstack sampling、Android Studio CPU Profiler 或 simpleperf 都可以查看 native 符号栈。采样适合持续时间足够长的算法、锁竞争和批处理；几十纳秒级空调用很难在采样结果中稳定出现。

采样前要准备带 build ID 的未裁剪符号文件，并核对 APK 中 `.so` 与本地符号是否来自同一次构建。调用频率、总字节量和线程名也应进入观测数据，否则“某函数占 5% samples”很难转换成接口改造方向。

### 10.3 Microbenchmark 用来比较边界变体

AndroidX Benchmark 会处理预热、重复测量和部分设备状态检查。下面的基准把输入数组放在测量循环外，避免把 Kotlin 分配算进 JNI 测试：

```kotlin
@RunWith(AndroidJUnit4::class)
class JniBoundaryBenchmark {
    @get:Rule
    val benchmarkRule = BenchmarkRule()

    private val input = ByteArray(4096) { index ->
        (index and 0xff).toByte()
    }

    @Test
    fun checksumRegion() {
        benchmarkRule.measureRepeated {
            BlackHole.consume(
                NativeBridge.checksumRegion(input)
            )
        }
    }
}
```

每个候选方案要放进独立测试，例如 empty regular、empty Fast、primitive Critical、Region 和 Elements。返回值被消费可避免编译器删除无可见效果的工作。基准应在 release-like、可复现的构建上运行，并报告设备、ABI、Android build、样本分布和多轮波动。

空方法基准能比较入口路径，不能代替业务基准。批处理接口还要用真实数据规模检查 cache、复制、GC 和尾延迟。

AndroidX 官方资料：

- [Microbenchmark 概览](https://developer.android.com/topic/performance/benchmarking/microbenchmark-overview)
- [编写 Microbenchmark](https://developer.android.com/topic/performance/benchmarking/microbenchmark-write)
- [`BlackHole`](https://developer.android.com/reference/androidx/benchmark/BlackHole)

### 10.4 AOSP 的 `jni-perf` 是实验模板

Android 17 源码包含 `benchmark/jni-perf`。它比较空 JNI 调用以及 ART 内部 `ScopedObjectAccess` 路径，构建到 `libartbenchmark`。这套代码依赖平台内部头文件与构建环境，适合作为实验设计和回归对照，不适合直接复制到普通 APK，也没有可跨设备复用的固定数字。

源码入口：

- [`JniPerfBenchmark.java`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/benchmark/jni-perf/src/JniPerfBenchmark.java)
- [`perf_jni.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/benchmark/jni-perf/perf_jni.cc)
- [`benchmark/Android.bp`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/benchmark/Android.bp)

## 11. 16KB page size 与 JNI 的关系

Android 17 设备可能采用 4KB 或 16KB page size。page size 会影响 ELF segment 对齐、`mmap` 粒度、guard page、缺页和 native 库可加载性，但不会自动缩短 ART 的 JNI 状态转换。

针对 JNI，16KB 需要检查的是：

- APK 中所有 native 库能否在 16KB 设备加载；
- 自定义 allocator、共享内存、文件映射是否写死 4096；
- pthread stack/guard、自定义 signal stack 的计算是否使用运行时 page size；
- 性能结论是否同时覆盖目标设备的 page-size 配置。

不要把整机启动或内存指标的变化直接归因到 JNI。ELF 对齐、打包工具链与动态链接器验证见 [§8.11 Native 库加载与动态链接器](11-native-library-loading-dynamic-linker.md)。

## 12. 一套可执行的审阅顺序

面对 JNI 热点时，按下面的顺序收集证据：

1. 统计每帧、每请求或每秒的 native 调用数，并记录传输字节量；
2. 用 Perfetto 外层/内层 slice 分开业务请求与 native 主体；
3. 对长 native 主体做 CPU sampling，检查算法、锁和 I/O；
4. 对短高频调用写 Microbenchmark，分别测 regular、Fast、Critical 和批处理；
5. 检查对象参数、字符串、数组 API、Release mode 与临时分配；
6. 将 Critical 区间与 GC pause、帧尾延迟对齐；
7. 用 JNI heap、`.IndirectRef` 趋势和代码计数审计引用生命周期；
8. 检查 pthread 创建率、Attach/Detach 次数、线程上限与栈配置；
9. 优先改接口粒度，再评估注解或局部汇编差异；
10. 在 Android 8～17 的实际支持范围做兼容与回归验证。

结果记录至少包含设备型号、SoC、ABI、Android build、ART 编译状态、温控状态、构建类型、线程策略、输入规模和统计分布。缺少这些条件的单个纳秒数字只能视为一次设备样本。

## 13. 版本演进与 Android 17 结论

| 版本阶段 | 相关影响 |
| --- | --- |
| Android 8 | Local Reference 移除旧固定小容量限制；Critical Native 在应用侧需要显式注册 |
| Android 12 | Critical Native 支持运行时动态符号发现，常规应用接入更简单 |
| Android 14 | `@FastNative` 与 `@CriticalNative` 成为公开 API，并纳入 CTS 兼容约束 |
| Android 15～17 | 16KB page-size 兼容进入 native 工具链和设备验证范围；JNI 的 GC、引用与 ABI 约束仍需按当前 ART 源码审阅 |

Android 17 上可以保留四条稳定结论：

- 普通 JNI 会进入 `kNative`，长纯 native 计算不会仅凭调用时长阻塞 GC；
- Fast/Critical 省去状态转换后必须保持极短、无阻塞；
- 普通 Elements 对可移动 primitive 数组通常复制，Primitive Critical 以限制 moving GC 换取直接地址；
- 批量接口、明确数据所有权和物理线程复用，通常比追逐固定指令数更可靠。

## 参考资料

- [JNI Tips](https://developer.android.com/ndk/guides/jni-tips)
- [`@FastNative`](https://developer.android.com/reference/dalvik/annotation/optimization/FastNative)
- [`@CriticalNative`](https://developer.android.com/reference/dalvik/annotation/optimization/CriticalNative)
- [Android 16KB page-size 支持](https://developer.android.com/guide/practices/page-sizes)
- [Android Studio JNI heap](https://developer.android.com/studio/profile/record-java-kotlin-allocations)
- [`dumpsys meminfo`](https://developer.android.com/tools/dumpsys)
- [AOSP ART `android-17.0.0_r1`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/)
- [AOSP bionic `android-17.0.0_r1`](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/)
- [Android common kernel `android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)

## 交叉引用

- [§1.15 JNI/NDK 互操作性能：ID 缓存、异常、字符串与 Direct Buffer](../../part1-fundamentals/ch01-architecture/15-jni-ndk-performance.md)
- [§8.11 Native 库加载与动态链接器：16KB、ELF 与命名空间](11-native-library-loading-dynamic-linker.md)
- [§8.19 Android 线程模型与 Dispatcher：线程池与调度边界](19-thread-model-dispatcher-selection.md)
