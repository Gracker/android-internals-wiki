---

title: "JNI/NDK 性能优化"
section: "1.15"
chapter: "1.15"
status: finalized
drafted_date: "2026-04-06"
applicable_versions: "Android 8 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-23"
last_verified_against: "AOSP android-16.0.0_r1 + developer.android.com @CriticalNative"
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
  - type: official
    path: "https://developer.android.com/ndk/guides/simpleperf"
  - type: official
    path: "https://developer.android.com/reference/java/nio/ByteBuffer"
  - type: spec
    path: "https://docs.oracle.com/javase/8/docs/technotes/guides/jni/"
  - type: research
    path: "intake/research-feeds/2026-04-07-19-art-fastnative-criticalnative-jni-optimization.md"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Binder.java (android-16.0.0_r1)"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Parcel.java (android-16.0.0_r1)"
  - type: aosp
    path: "frameworks/base/core/java/android/os/SystemProperties.java (android-16.0.0_r1)"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Trace.java (android-16.0.0_r1)"
  - type: aosp
    path: "frameworks/native/include/android/trace.h (android-16.0.0_r1)"
  - type: aosp
    path: "system/core/libcutils/include/cutils/trace.h (android-16.0.0_r1)"
  - type: aosp
    path: "system/core/libutils/include/utils/Trace.h (android-16.0.0_r1)"
tags:
  - android
  - research
  - jni
  - ndk
  - performance
related_chapters:
  - "4.7"
  - "14.2"
pipeline_stage: "ready-to-publish"
task6_result: pass-light-edit
task9_state: "reviewed"
task9_reviewed_date: "2026-05-20"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-20T11:41:31+08:00"
task2b_state: fixed
task2b_result: fixed
reviewed_by: openclaw-task6
reviewed_date: 2026-04-23
last_task6_at: "2026-05-18T15:14:44+08:00"
last_task6_audit: "2026-05-18"
last_task6_audit_result: l1-light-edit
last_task2b_at: "2026-05-20T11:12:00+08:00"
last_task9_audit: "2026-05-20"
last_task9_review_log: "logs/deep-review/2026-05-20-11-deep-review.md"
task9_review_notes: "2026-05-20 Task9 深度复审：pass-tech-review。P0 0 / P1 0 / P2 3；P2 为 CriticalNative public API 边界、16KB page size NDK 版本口径、Propeller 待验证段。已自动同步 pipeline_stage=ready-to-publish。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-05-30
---

# 1.15 JNI/NDK 性能优化

只要一段调用路径跨过 Java/Kotlin 和 C/C++ 的边界，JNI（Java Native Interface）就是性能模型的一部分。音视频编解码、图像处理、游戏引擎、端侧 AI 推理，这些场景里的热路径的瓶颈往往在于跨了多少次边界、每次跨边界时做了什么、在 Trace 里又能看到多少证据。

如果我们只记住“native 比 Java 快”这种口号，排查问题时很容易看错方向。很多卡顿来自 JNI 调用过碎、字符串和数组在两侧来回拷贝、native 线程 attach/detach 用错位置，或者 16KB page size 下第三方 `.so` 未满足对齐要求，应用连加载都过不了。

这一节不打算把 JNI 写成 API 词典。关心三件事：第一，JNI 开销到底来自哪里；第二，哪些优化真的有效，哪些只是把问题换了个地方；第三，打开 Perfetto 或 simpleperf 时，该沿着什么线索定位问题。

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **Perfetto 中的 JNI 可观测性有三条路**：
  手工 `ATrace`/`android.os.Trace` 插桩会生成精确 slice；callstack 或 native symbol 采样能看到 trampoline 和 native 热点；simpleperf 的 `report-sample --protobuf` 结果可以导入 Perfetto，但它是采样证据，不是逐次调用时长。

- 🔹 **JNI transition 的量级要看来源和设备条件**：
  官方文档给出的参考值来自 `angler-userdebug`（2016-07）：普通 JNI 约 115ns，`@FastNative` 约 35ns，`@CriticalNative` 约 25ns。它能说明量级和优化方向，但不能直接当成今天所有设备的固定数字。

- 🔹 **减少 JNI 次数通常比追逐单次纳秒数更重要**：
  `FindClass()` / `GetMethodID()` / `GetFieldID()` 应该在初始化阶段缓存；热路径优先做批量传输和粗粒度 API 设计，而不是每个元素一次 JNI 调用。

- 🔹 **`@FastNative` 和 `@CriticalNative` 的边界完全不同**：
  `@FastNative` 可以处理托管对象；`@CriticalNative` 的公开约束是方法不能使用托管对象，也不能依赖隐式 `this`，native 侧函数签名里没有 `JNIEnv*` / `jclass`。面向应用的兼容性建议应收敛到 `static native` + primitive 标量参数/返回值；数组不要写成稳定承诺。

- 🔹 **线程和引用生命周期比单次 transition 更常见地出问题**：
  `JNIEnv*` 线程私有，不能跨线程共享；`AttachCurrentThread()` 创建的是可调用 JNI 的线程上下文，不该放在每次任务里反复做；attached native 线程创建的 local reference 不会像普通 JNI 调用那样自动清理。

- 🔹 **16KB page size 影响的是 native library 的可加载性和内存布局**：
  自 2025-11-01 起，提交到 Google Play、且 targeting Android 15+ 的 64 位设备版本必须支持 16KB page size。需要重编和校验的是包含 native code 的应用或 SDK。

### 扩展（可选深入）

- 🔸 `@FastNative` / `@CriticalNative` 调用方与 Baseline Profile 的配合
- 🔸 Java Binder、JNI bridge、`libbinder_ndk` 三种调用栈的证据链怎么拆开看
- 🔸 音视频 / 游戏 / 端侧 AI 场景里 DirectByteBuffer 与对象池的组合策略
<!-- outline-end -->

## 为什么 JNI 性能问题很少表现成“单个函数慢”

一次 JNI 调用的成本，不只是从 Java 栈跳到 native 栈那一下。我们至少要付出几类开销：运行时状态切换、参数编组、对象或数组的引用处理、必要时的字符串编码转换，以及调用结束后的返回路径。如果调用很少，这些成本几乎可以忽略；如果调用发生在每帧、每包音频、每个像素块、每个 Binder transaction 上，问题就会从“一个函数快不快”变成“边界设计得碎不碎”。

分析 JNI 时，先看接口形状，再看具体函数内部。一个粗粒度 JNI 接口，一次把 1MB 数据交给 native 批处理，即使 native 侧算法并不极限，通常也比“循环 10 万次，每次过一次 JNI”更稳。前者把成本集中在一次调用里，后者把 transition、局部引用、异常检查、字符串/数组处理全部放大了。

## 先把证据链搭好：Perfetto 里到底怎么看 JNI

很多章节一上来就说“在 Perfetto 里看 JNI slice”，这句话本身就不完整。默认 system trace 并不会自动替我们生成统一名字的“JNI transition”切片。要在 Perfetto 里看见 JNI，我们通常走三条路，而且每条路回答的问题都不一样。

第一条路：**手工插桩**。如果代码在你控制范围内，Java 侧可以用 `android.os.Trace`，NDK 侧可以直接包含 `<android/trace.h>`，调用 `ATrace_beginSection()` / `ATrace_endSection()`。这时 Perfetto 线程轨上出现的 slice 名字，就是我们自己写进去的 section name。AOSP android-16.0.0_r1 中，公开 NDK 头文件在 `frameworks/native/include/android/trace.h`，`ATrace_beginSection()` 和 `ATrace_endSection()` 也在这个头里声明。系统内部的 `ATRACE_BEGIN` / `ATRACE_END` 宏来自 `system/core/libcutils/include/cutils/trace.h` 这套包装层；声明 `ATrace_beginSection()` 的则是公开 NDK 接口。C++ RAII 宏 `ATRACE_CALL()` / `ATRACE_NAME()` 定义在 `system/core/libutils/include/utils/Trace.h`，不是 `cutils/trace.h`——后者只有 C 风格的 `ATRACE_BEGIN/END`。系统级服务或 HAL 的 C++ 代码通常更适合直接用 `ATRACE_CALL()` / `ATRACE_NAME()`，因为这套宏会把 begin/end 自动配对；给第三方 App 或 SDK 交付的 NDK 代码仍应以 `<android/trace.h>` 这组稳定 API 为准。

第二条路：**采样**。Perfetto 的 callstack / native symbol 采样，或者 simpleperf 采样，能告诉我们 CPU 时间主要烧在什么 native 符号上，也能看到 `art_jni_trampoline` 这一类运行时桥接符号是否频繁出现。但采样给的是“这里经常被采到”，不是“这一次 JNI 调用精确耗时多少微秒”。如果我们要回答“哪个 native 算法最热”，采样很好用；如果我们要回答“Java 调用 native 的边界本身耗了多久”，还是得靠插桩或更细的实验。

第三条路：**simpleperf 导入 Perfetto**。simpleperf 能记录 native call graph，`report-sample --protobuf` 之后可以把样本导入 Perfetto UI 继续看时间线和热点。这条路的好处是应用代码不用预埋 trace label，就能先知道“热点在哪一层”；限制是它依然属于采样视角。我们看到的是热点分布，而不是每次 JNI 调用的 begin/end 切片。具体命令和采样策略，建议跟 `§14.2 Simpleperf` 配合着看，不要在本节重复维护完整工具手册。


把这三条路分清之后，很多误判就会自动消失。比如我们在默认 Trace 里没看到“JNI slice”，不代表 JNI 没有成本，可能只是没有插桩。反过来，如果我们在采样火焰图里看到了 native 热点，也不代表 JNI transition 本身贵，贵的可能是 native 算法本身。

## JNI transition 到底有多贵

官方文档在 `@CriticalNative` 说明页里给过一组常被引用的基准值——测试环境 `angler-userdebug`，时间是 2016-07。这组数字只能建立量级感，不能直接当今天所有设备的固定基准：普通 JNI 约 115ns，`@FastNative` 约 35ns，`@CriticalNative` 约 25ns。

| 调用路径 | 官方参考值 | 这组数字说明了什么 |
| --- | --- | --- |
| 普通 JNI | 115ns | 过边界本身不是“零成本”，但单次也没有慢到值得恐慌 |
| `@FastNative` | 35ns | 运行时少做一部分状态切换后，开销能明显下降 |
| `@CriticalNative` | 25ns | 把 ABI 收紧到只有 primitive 参数/返回值时，过边界还能再快一点 |

官方公开表仍停在 2016 年的 `angler-userdebug`。这组数字只能用来建立量级感，不能外推到今天任何设备；芯片、ART 版本、调用点是否已经 AOT/JIT 编译，都会把结果拉开。需要当前设备结论时，应该在目标机型上单独测。

这组数字最容易被误用的地方有两个。第一，把它当成今天 Pixel 8、骁龙 8 Gen 4 或某台车机上的绝对值。第二，只盯着单次调用的纳秒数，却不算调用次数。假设一帧里做 1000 次普通 JNI，光 transition 的参考量级就是 `1000 × 115ns ≈ 115μs`。它仍然不是 16.67ms 帧预算里的大头，但已经不再是可以完全无视的噪声，何况真实业务里往往还夹着字符串、数组、对象和锁。

所以我们看 JNI 成本时，先问两个问题：**次数是否已经多到要重构接口**，以及**过边界时有没有顺手带上额外成本**。后一种情况比前一种更常见，比如热路径里每次都 `GetMethodID()`、每次都把 `String` 转一遍 MUTF-8、或者在一个 `@FastNative` 方法里做了可能阻塞的系统调用。

## 先把次数降下来：缓存 ID，合并调用，做粗粒度接口

ART 不会替我们优化 API 设计。如果 Java 侧一次只传一个数字，native 侧再返回一个结果，运行时就只能老老实实陪我们来回过边界。减少 JNI 成本最朴素也最有效的办法，通常不是换注解，而是**减少次数**。

第一步：缓存 ID。`FindClass()`、`GetMethodID()`、`GetFieldID()` 都不该出现在热路径。推荐在 `JNI_OnLoad()` 或显式初始化阶段完成查找，把 `jclass` 提升为 global reference，把 `jmethodID` / `jfieldID` 保存在静态缓存里。`jclass` 是 local reference，离开当前 native 调用就失效；`jmethodID` / `jfieldID` 不是 Java 对象，只要对应 class 还活着，就可以跨调用复用。

```cpp
static jclass gDecoderClass;
static jmethodID gOnFrameReady;

JNIEXPORT jint JNI_OnLoad(JavaVM* vm, void* /* reserved */) {
    JNIEnv* env = nullptr;
    if (vm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6) != JNI_OK) {
        return JNI_ERR;
    }

    jclass local = env->FindClass("com/example/Decoder");
    gDecoderClass = reinterpret_cast<jclass>(env->NewGlobalRef(local));
    env->DeleteLocalRef(local);
    gOnFrameReady = env->GetMethodID(gDecoderClass, "onFrameReady", "(J)V");
    return JNI_VERSION_1_6;
}
```

这里还有一个容易踩空的 class loader 语境。`JNI_OnLoad()` 里调用 `FindClass()` 时，运行时会沿着触发 `System.loadLibrary()` 的那条 Java 调用路径解析类，所以缓存 App 自己的 `jclass` 通常能成功。native 自己创建并通过 `AttachCurrentThread()` 挂进 JVM 的线程，如果当前栈上没有来自 App 的 Java frame，`FindClass()` 会从 system class loader 开始查找，App class 往往找不到。规避方式通常有三种：在 `JNI_OnLoad()` 完成查找并缓存 global reference，Java 侧把 `Class` 或 `ClassLoader` 传给 native，或者把查找动作放回 Java 创建的线程执行。

第二步影响更大：**把细粒度接口改成粗粒度接口**。如果我们要把 4096 个采样点从 Java 送到 native，不应该设计成“4096 次 JNI，每次传一个 `short`”。更像样的接口是：一次传整个 `short[]`、`ByteBuffer` 或句柄，让 native 在本地完成整批处理，再把最终结果返回。对于图像、音频、推理输入这类大块数据，粗粒度设计通常比“单次 transition 再压 10ns”更值钱。

## `@FastNative` 和 `@CriticalNative`，到底快在哪，边界又在哪

这两个注解经常一起出现，但它们解决的问题不同。`@FastNative` 仍然是 JNI，只是运行时给它走了更短的过渡路径，所以照样能拿托管对象、能做 JNI 调用；`@CriticalNative` 把规则收得更紧，换来更短的 ABI。

先看 `@FastNative`。AOSP android-16.0.0_r1 的 `frameworks/base/core/java/android/os/Parcel.java` 里有一个很直接的例子：

```java
@FastNative
private static native void nativeWriteString16(long nativePtr, String val);
```

这里的 `String val` 已经说明了问题，`@FastNative` 并不是“不能碰托管对象”，它只是要求这条调用链足够短、足够可控。`frameworks/base/core/java/android/os/SystemProperties.java` 里还有一个反例：源码直接注释了 `native_set` **不能**标成 `@FastNative`，因为它会做 IPC，可能阻塞。这个反例比空泛地说“不要乱用”更有说服力。

再看 `@CriticalNative`。官方文档给出的硬约束是：方法不能使用托管对象，也不能依赖隐式 `this`，所以 Java 侧通常必须写成 `static native`。native 侧函数签名里也没有 `JNIEnv*` 和 `jclass` 参数，因为 JNI transition 的 ABI 已经换成更短的一套。

数组边界是这一节最容易写错的地方。Java 数组本身也是托管对象，而当前公开文档没有把 `byte[]`、`int[]` 这类参数列成稳定承诺，因此正文不再写成“primitive array 一定可用”。面向应用侧的安全边界，收敛到 primitive 标量参数/返回值更稳；如果确实要依赖数组语义，应先核对当前 ART 源码与测试，再决定是否采用。

AOSP 里符合这条规则的例子很多，`frameworks/base/core/java/android/os/Binder.java` 里的 `getCallingUid()` 就很典型：

```java
@CriticalNative
public static final native int getCallingUid();
```

`Parcel.java` 里的 `nativeWriteInt(long nativePtr, int val)`、`nativeReadInt(long nativePtr)` 也是同一路子。参数全是 primitive 或 native 句柄，没有对象参与，所以运行时才能把过渡路径压到最短。

`@CriticalNative` 的加速来源包括更短的 critical ABI、被省掉的常规 JNI trampoline，以及入口侧不再准备 `JNIEnv*` / `jclass` 这层桥接参数；运行期间还不会做常规的线程挂起检查。只要方法里出现 I/O、锁等待或其他不可预期的阻塞，这点过渡收益就会很快被吞掉。

这两个注解还有一条共同约束，官方文档专门强调过：**执行期间，GC 不能把当前线程挂起做关键工作，因此长时间运行、I/O、长时间持有 native 锁都不合适。** 文档没有给 1ms、10ms 这类阈值，也不鼓励我们自己编阈值。更稳的写法是，把它们理解为“只给很短、很确定、很少阻塞的 native 路径使用”。如果方法里会等锁、等 Binder、等磁盘、等网络，那就不该指望 `@FastNative` / `@CriticalNative` 帮我们省时间。

兼容性上也别想当然。官方文档给出的口径是：这套优化从 Android 8 开始在系统内部使用，Android 14 才成为 CTS-tested public API。内建的动态 JNI linking 只在 Android 12+ 工作，Android 8-11 如果要认真依赖它，必须显式 `RegisterNatives()`；Android 7 及以下会忽略注解，而 `@CriticalNative` 还会因为 ABI 不匹配带来参数编组错误甚至崩溃。如果应用要跨很多版本用这条路，最好把版本兼容规则写清楚，而不是只在 Java 层加个注解就当完事。

官方文档还给了一个很实用的建议：如果调用方在启动路径上，最好把这些调用方放进 Baseline Profile。原因很简单，过边界路径再快，如果调用方本身还在解释执行或刚进入 JIT 预热，启动阶段仍然看不到理想收益。

## native 线程与引用生命周期，才是日常最容易踩坑的地方

对多数项目来说，线程模型和引用生命周期没管好，比 `@CriticalNative` 用没用对更容易出事。

第一条：`JNIEnv*` 是线程私有的。官方文档明确说过，`JNIEnv` 用在 thread-local storage 上，不能跨线程共享。正确的共享对象是 `JavaVM*`。如果某段 native 代码需要在当前线程拿到 `JNIEnv*`，应该通过 `JavaVM::GetEnv()` 查询当前线程是否已经 attach，而不是把别的线程里的 `JNIEnv*` 偷过来复用。

第二条：native 自己创建的线程，在调用任何 JNI 之前必须先 `AttachCurrentThread()` 或 `AttachCurrentThreadAsDaemon()`。线程 attach 之后才有 `JNIEnv*`，attach 过的线程再次 attach 是 no-op，所以正确的使用位置通常是**线程启动时 attach 一次，线程退出前 detach 一次**。这类线程如果临时去做 `FindClass()`，还要额外确认 class loader 语境，实践里更稳的是直接复用初始化阶段缓存好的 `jclass` / `jmethodID`。如果在线程池里把 attach/detach 放到每个任务执行前后，等于把线程上下文管理也塞进热路径了，既麻烦又没必要。文档还强调了一点，attached native 线程必须在退出前 `DetachCurrentThread()`，否则运行时资源不会被正常回收。

第三条：local reference 不是无限免费的。普通 JNI 调用返回时，运行时会替我们清理当前调用里创建的大部分 local reference；但如果线程是通过 `AttachCurrentThread()` 进来的，文档明确写了，local reference **不会自动释放，直到线程 detach 为止**。因此，音视频解码循环、遍历 Java 对象数组、构建大量临时 `jstring` 这类代码，必须显式 `DeleteLocalRef()`，或者用 `EnsureLocalCapacity()` / `PushLocalFrame()` / `PopLocalFrame()` 管住引用数量。JNI 规范只要求实现至少保留 16 个 local reference slot，超过这个量还不做管理，问题迟早会出来。

这也是为什么在高频场景里，我们更愿意让 native 线程池长期存活，而不是不停创建线程，再 attach，再构造一堆 local reference。前者的成本和行为边界都更稳定，后者既放大生命周期管理成本，又让问题更难在 Trace 里还原。

## 字符串、数组和 DirectByteBuffer，不要把“零拷贝”想得太轻松

字符串，是 JNI 里最容易被低估的成本。Java `String` 和 native 侧期待的字节序列并不是一回事，`GetStringUTFChars()` 涉及到 MUTF-8 视角，`GetStringChars()` 则保留 UTF-16 视角。Android 8 之后，`String` 的内部表示和 moving GC 行为都变了，官方文档明确提醒过，哪怕是 `GetStringCritical()`，运行时也更经常需要做复制，而不是直接把内部指针借给我们。所以，如果我们只需要一段子串，或者目标本来就接受 UTF-16，优先考虑 `GetStringRegion()` / `GetStringChars()` 这类更贴近需求的 API，不要默认每次都走 UTF 转换。

数组也一样。`Get<PrimitiveType>ArrayElements()` 可能返回真实指针，也可能分配一块 native buffer 再拷贝过去；不管哪种情况，都必须对应一次 `Release`。如果运行时直接把堆里的数组暴露给 native，那块数组在 release 之前就可能被 pin 住，无法参与压缩式移动。

`GetPrimitiveArrayCritical()` 更应该谨慎。它限制运行时干预空间以换取更短的临界区，不能当成“更快的数组 API”来用。官方建议是：critical 区域要尽可能短，不要在中间执行任意 JNI 调用，也不要做阻塞系统调用。正确的理解是：运行时在这段时间里对堆移动和关键回收工作的选择会变得非常受限，所以我们必须尽快 release。这比写一个并无来源的固定阈值可靠得多。

如果数据本来就很大，而且会长期在 Java 和 native 之间来回传，`DirectByteBuffer` 往往是更像样的方案。它把存储放在 managed heap 之外，native 侧可以通过 `GetDirectBufferAddress()` 直接拿到地址，省掉重复拷贝。代价也很明确：direct buffer 的分配和回收比普通 `byte[]` 重，适合池化复用，不适合每次现建现扔。

## 16KB page size：JNI/NDK 项目的上线门槛

很多人第一次关注 16KB page size，是因为 Google Play 的兼容性提醒；但对 JNI/NDK 项目来说，它决定了 native library 能不能在目标设备上被正确加载，远超“发版前顺手看一眼”的检查项级别。

官方文档现在的口径很清楚：**从 2025-11-01 起，所有提交到 Google Play、且 targeting Android 15+ devices 的新应用和更新，都必须在 64 位设备上支持 16KB page sizes。** 这句话的重点有三个。第一，范围是 targeting Android 15+ 的提交，不是所有历史版本一刀切。第二，约束对象是 64 位设备。第三，需要处理的是包含 native code 的应用，包括直接引入 NDK 库，或者通过第三方 SDK 间接带入 `.so` 的情况。纯 Java/Kotlin 应用通常不需要为此重编 NDK 库，但如果包里带了 native 依赖，就必须认真检查。

16KB page size 对性能确实有正向收益，官方给出的初步测试数据包括：内存压力下 app launch time 平均下降 3.16%，部分应用能到 30%；启动期功耗平均下降 4.56%；camera hot start 平均快 4.48%，cold start 平均快 6.60%；system boot time 平均提升约 8%。这些数字可以用来解释“为什么平台要推 16KB”，但它们不是替任何单个应用背书，具体收益还得看自己的内存访问模式和三方库状况。

从 JNI/NDK 视角看，先看 `.so` 的 segment alignment。旧的 4KB 对齐库在 16KB 设备上可能需要额外填充，严重时甚至会因为对齐不满足而加载失败。Android 文档给出的迁移建议也很直接：NDK r28 及以上默认按 16KB 对齐；如果还在 NDK r27，需要按文档补充 linker flags；同时要把三方 SDK 一起纳入检查，不要只修自己写的库。更完整的迁移清单和 APK Analyzer 检查方法，建议回看 `§4.7 16KB Page Size 与 Android 性能`，本节只保留与 JNI/NDK 直接相关的判断准则。

## 系统服务的设计启示：JNI 适合进程内桥接，不适合替代 IPC

AOSP 自己的实现方式很能说明问题。`Binder.java`、`Parcel.java` 这种 framework 边界里，JNI 主要承担的是 Java API 和 native runtime 之间的桥接，所以我们能看到大量 `@FastNative` / `@CriticalNative`。但到了 SurfaceFlinger、AudioFlinger 这类对时延极敏感、又本来就在 native 世界里的服务，系统更愿意直接保持 native-only 栈，而不是再绕回 Java。

判断标准很简单。同进程内，Java/Kotlin 确实要用现成的 C/C++ 库，JNI 是合适的桥。跨进程通信，就老老实实用 Binder / AIDL，不要为了绕开 IPC 把两个组件硬塞进一个进程再走 JNI。至于 `libbinder_ndk` 和 Java Binder 谁更快，不能脱离 payload、序列化路径和测试设备去写固定百分比。更可靠的结论是：native-only 的 Binder 栈可以减少 Java ↔ native 桥接和部分序列化层级，但具体收益必须结合 workload 单独测。

## Post-Link 优化：Propeller

[待验证: NDK r28 changelog 与 LLVM lld 官方文档中未找到 `--propeller-order` flag 的直接说明；8% 收益来自 Google Propeller 论文，为 warehouse-scale workload 评估，不能直接作为 Android NDK 功能背书]

Propeller 是 Google 提出的 Post-Link Optimization 技术，在 PGO 的基础上通过重排二进制中的基本块（basic block）顺序，提升 CPU 的分支预测和指令缓存命中率。Google 的论文显示，在已有 PGO 的基础上，Propeller 可以再带来最高 8% 的性能提升。这项技术目前更适合对启动时间或热路径有极致要求的场景，通用业务可以先确保 PGO / AutoFDO 已接入后再考虑。

如果 NDK 后续版本正式暴露 Propeller flag，启用路径大致为：先用 instrumented binary 采集执行 profile，然后把 profile 反馈给 linker 进行基本块重排，最后输出优化后的 .so。它和 PGO 是互补关系——PGO 影响编译器的内联和代码生成决策，Propeller 影响 linker 的代码布局决策。当前 NDK r28 changelog 中能确认的是 16 KiB alignment 等变更，尚未看到 Propeller 的官方 flag 或 profile 采集流程。

## 版本演进

| Android 版本 | 与本节直接相关的变化 |
| --- | --- |
| Android 8 (API 26) | `@CriticalNative` 在系统内部引入；`@FastNative` / `@CriticalNative` 开始在 framework 代码里广泛使用 |
| Android 12 (API 31) | 官方文档说明：内建 dynamic JNI linking 对这两类注解的支持从 Android 12+ 才完整可用 |
| Android 14 (API 34) | `@FastNative` / `@CriticalNative` 成为 CTS-tested public API |
| Android 15 (API 35) | 16KB page size 成为平台重点兼容项，Google Play 对 targeting Android 15+ 的 64 位提交提出强制支持要求 |
| Android 16 (API 36) | 本轮核对未发现新的 public JNI annotation 语义变化；`@FastNative` / `@CriticalNative` 公开口径仍停留在 Android 8 内部使用、Android 12+ dynamic lookup、Android 14 CTS-tested public API 这组边界 |

## 常见误区

**误区一：native 一定更快。** 如果只是简单计算，Java/JIT/AOT 可能已经足够好；一旦把 JNI transition、对象转换和数据拷贝算进去，native 未必占便宜。

**误区二：默认 Perfetto 会自动把 JNI 开销画出来。** 默认 trace 里没有统一的“JNI transition”切片名。没有插桩时，我们通常只能从采样、符号和上下文去推断。

**误区三：`@CriticalNative` 适合任何“看起来很快”的方法。** 只要方法签名里有对象、数组、隐式 `this`，或者方法内部可能阻塞，这条路就不对。

**误区四：`AttachCurrentThread()` 是小事，哪里需要哪里调。** attach/detach 应该跟线程生命周期绑定，不该跟单次任务绑定。否则线程上下文管理本身就会进入热路径。

**误区五：`GetPrimitiveArrayCritical()` 等于零拷贝且没副作用。** 运行时可能返回真实指针，也可能返回拷贝；关键在于 critical 区域必须短，且要尽快 release。

## 与其他章节的关系

如果我们想继续看 16KB page size 的平台背景、验证手段和迁移清单，去 `§4.7 16KB Page Size 与 Android 性能`。如果我们已经确定热点在 native 栈，准备系统化采样和导出火焰图，去 `§14.2 Simpleperf`。这两节分别负责“兼容性前提”和“工具方法”，本节只负责把 JNI/NDK 设计和性能判断讲清楚。

## 参考资料

- 官方文档
  - `https://developer.android.com/training/articles/perf-jni`
  - `https://developer.android.com/reference/dalvik/annotation/optimization/FastNative`
  - `https://developer.android.com/reference/dalvik/annotation/optimization/CriticalNative`
  - `https://developer.android.com/guide/practices/page-sizes`
  - `https://developer.android.com/ndk/guides/simpleperf`
  - `https://developer.android.com/reference/java/nio/ByteBuffer`
  - `https://docs.oracle.com/javase/8/docs/technotes/guides/jni/`
- AOSP 源码路径（android-16.0.0_r1）
  - `frameworks/base/core/java/android/os/Binder.java`
  - `frameworks/base/core/java/android/os/Parcel.java`
  - `frameworks/base/core/java/android/os/SystemProperties.java`
  - `frameworks/base/core/java/android/os/Trace.java`
  - `frameworks/native/include/android/trace.h`
  - `system/core/libcutils/include/cutils/trace.h`
  - `system/core/libutils/include/utils/Trace.h`
