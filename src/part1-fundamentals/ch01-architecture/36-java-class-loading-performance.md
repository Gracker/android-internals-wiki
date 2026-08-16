---
title: "Android Java 类加载链路与启动期类加载性能"
chapter: "1.36"
section: "1.36"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-07-25"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "libcore/dalvik/src/main/java/dalvik/system/BaseDexClassLoader.java"
  - type: aosp
    path: "libcore/dalvik/src/main/java/dalvik/system/DexPathList.java"
  - type: aosp
    path: "libcore/dalvik/src/main/java/dalvik/system/DexFile.java"
  - type: aosp
    path: "libcore/dalvik/src/main/java/dalvik/system/DelegateLastClassLoader.java"
  - type: aosp
    path: "libcore/ojluni/src/main/java/java/lang/ClassLoader.java"
  - type: aosp
    path: "art/runtime/class_linker.cc"
  - type: aosp
    path: "art/runtime/class_status.h"
  - type: aosp
    path: "art/runtime/native/dalvik_system_DexFile.cc"
  - type: aosp
    path: "art/runtime/oat/oat_file.cc"
  - type: aosp
    path: "art/libdexfile/dex/type_lookup_table.h"
  - type: aosp
    path: "art/runtime/verifier/class_verifier.cc"
  - type: aosp
    path: "art/libartservice/service/README.md"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/ZygoteInit.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ApplicationLoaders.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/LoadedApk.java"
  - type: aosp
    path: "system/core/debuggerd/debuggerd.cpp"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/difference-baseline-startup"
tags: [classloader, class-loading, dexpathlist, startup, verification, art]
related_chapters: ["1.7", "1.9", "1.11", "1.22", "8.2", "21.1", "21.4"]
---

# 1.36 Android Java 类加载链路与启动期类加载性能

## 类加载包含三个动作

类加载性能涉及三类不同工作：

1. **查找并定义类**：找到 DEX 中描述该类的 `class_def`，构造 `java.lang.Class` 对象，装入字段、方法、父类和接口信息，再完成方法表布局、引用解析等链接工作。
2. **验证类**：检查 DEX 指令、类型流和访问约束。VDEX/OAT 是 dexopt 生成或使用的 ART 产物，其中可复用的验证信息能够省掉重复验证；缺少有效结果时，运行时仍要调用验证器（verifier）。
3. **初始化类**：写入 DEX 编码的静态字段初值，再执行 `<clinit>`。`<clinit>` 是虚拟机看到的类初始化方法，由静态字段初始化表达式和 `static` 代码块汇成；完成后，ART 还要按 Java 内存模型让其他线程看到初始化结果。

`ClassLoader.loadClass()` 会取得类并完成 ART 所需的定义/链接，但不会仅因这次调用就执行 `<clinit>`。验证结果可能已经存在于有效产物中；尚未满足验证条件的类，可以在后续初始化或使用路径进入 verifier。`Class.forName(name)` 的单参数重载会请求初始化。`new`、调用静态方法、读写非常量静态字段等“主动使用”也可能触发初始化。

因此，即使一段启动耗时由某个类首次出现引起，也要继续判断时间落在查找、定义/链接、验证，还是业务自己的 `<clinit>`。四者的修复方向不同。

## 从 Java API 到 ART

### 常规 Java 路径

`PathClassLoader` 在 Java 层找不到已加载类、父加载器也没有命中后，会沿这条路径进入 DEX 和 ART：

```text
ClassLoader.loadClass(name, resolve)
  ├─ findLoadedClass(name)
  ├─ parent.loadClass(name, false) / bootstrap lookup
  └─ BaseDexClassLoader.findClass(name)
       ├─ sharedLibraryLoaders
       ├─ DexPathList.findClass(name, suppressed)
       │    └─ 依次访问 dexElements
       │         └─ DexFile.loadClassBinaryName(...)
       │              └─ DexFile.defineClassNative(...)
       │                   └─ ClassLinker::DefineClass(...)
       └─ sharedLibraryLoadersAfter
```

这里的 `bootstrap lookup` 是从 boot class path 查找平台类；`sharedLibraryLoaders` 与 `sharedLibraryLoadersAfter` 则分别表示在本加载器 DEX 之前、之后参与查找的共享库加载器。

这条链有两个按顺序访问的维度：父加载器链和 `dexElements[]`。`DexPathList.findClass()` 按数组顺序访问元素，命中第一个定义就停止。DEX 数量增加会让一次未命中或靠后命中的查找访问更多元素，但耗时还受缓存、DEX 是否已映射、ART 产物是否有效和设备存储影响，不能只用 DEX 数量换算成固定毫秒数。

### API 37 的 ART 快速路径

ART 自己解析类型引用时，不一定重新递归调用上述 Java 方法。`ClassLinker::FindClass()` 会识别以下标准加载器及其继承关系：

- `PathClassLoader` / `DexClassLoader`
- `InMemoryDexClassLoader`
- `DelegateLastClassLoader`

对可识别的链，`FindClassInBaseDexClassLoader()` 在 ART 原生层按相同策略查找，减少 Java 与原生层之间的多次调用切换。遇到自定义且无法识别的 `ClassLoader` 时，ART 才需要回到该加载器定义的 Java 行为。原生快速路径仍遵循 Java 侧对应的委托顺序。

### `DelegateLastClassLoader` 的准确顺序

`DelegateLastClassLoader` 从 API 27 开始提供。API 37 中，已加载类仍然先由 `findLoadedClass()` 命中；新查找的顺序为：

1. boot class path；
2. `sharedLibraryLoaders`；
3. 本加载器的 DEX；
4. `sharedLibraryLoadersAfter`；
5. parent。

它只把应用/库 DEX 放到了普通 parent 之前，boot class path 仍有最高优先级。该策略适合有明确隔离需求的运行环境，不能用来给普通应用加速类加载。Java 类型身份由二进制类名和定义它的类加载器共同决定，因此同名类由谁定义会影响强制转换、包访问和链接约束。应先保证正确性，再评估性能收益。

## DEX 中怎样找到 `class_def`

“每个 DEX 都对 `class_defs` 做二分查找”不符合 API 37 实现。

`DexPathList` 或 ART 的标准加载器快速路径会依次访问加载器持有的 DEX。进入某一个 DEX 后，`OatDexFile::FindClassDef()` 的优先路径如下：

1. 如果该 DEX 关联的 `TypeLookupTable` 有效，就按类型描述符（descriptor）的 modified UTF-8 哈希值查找 `class_def_idx`；描述符形如 `Lcom/example/Foo;`，`class_def_idx` 是该类定义在 DEX 表中的索引。
2. 如果没有有效查找表，先由描述符找到 `type_id`，也就是 DEX 类型表中的条目。
3. 再调用 `DexFile::FindClassDef(type_idx)`；它在 API 37 中顺序扫描 `class_defs`，寻找引用该 `type_id` 的类定义。

`TypeLookupTable` 在编译阶段创建，运行时从已经映射到进程地址空间的产物中读取。它避免了常见路径上的整表扫描。外层 DEX 元素仍然按类路径（class path）顺序访问，所以 Startup Profile 对 DEX 布局的优化依旧有价值。

### MultiDex 优化应看什么

评估 MultiDex 要同时检查 DEX 次序、加载器结构和运行时产物：

- 启动所需类是否集中在靠前的 DEX；
- 未命中查找是否反复穿过多个元素；
- 动态功能模块（dynamic feature）、插件或补丁是否增加了额外加载器层级；
- 产物中是否带有有效的 profile、验证信息和 `TypeLookupTable`；
- 类是否在首帧前确有必要。

Startup Profile 是构建期输入。D8/R8 用它调整 DEX 布局，优先把启动类和方法放入主 `classes.dex`；空间不足时会放到后续 DEX。Baseline Profile 则随 APK/AAB 提供给 ART，用于设备侧的 Profile 引导编译（profile-guided compilation）：ART 会优先处理 Profile 覆盖的类和方法。两者可以来自同一套生成流程，但作用阶段不同。

不要用“首 DEX 命中率必须达到某个百分比”代替测量。可在 Android Studio 的 APK Analyzer 中检查 DEX 分布；AGP 8.8 及以上还可检查 AAB 内 R8 元数据的 `dexFiles[].startup` 标记。

## `ClassLinker::DefineClass()` 做了什么

API 37 的主要步骤可概括为：

```text
查 ClassTable
  → 分配 mirror::Class
  → RegisterDexFile / SetupClass
  → 尝试插入 ClassTable
  → LoadClass（字段、方法、父类和接口）
  → LinkClass（布局、vtable、iftable、IMT 等）
  → CHA 更新
  → 状态转为 kResolved
  → ClassPrepare 回调
```

其中，vtable、iftable 和 IMT 分别服务于虚方法、接口及接口方法分派；CHA 是类层次分析（Class Hierarchy Analysis），用于根据当前继承关系优化调用。

这段顺序解释了两个常见性能时间线（trace）现象。定义一个类可能递归解析父类和接口，因此一个外层类的实际经过时间（wall time，包含计算、等待和被调度出去的时间）会包含依赖类的工作。CHA 更新发生在类变为 `kResolved` 之前；新类若推翻了 JIT 编译器此前采用的“某调用点只有一个实现”假设，还可能让已编译代码失效并触发去优化，相关机制见 §1.35。

### 托管堆与 `LinearAlloc` 的边界

`mirror::Class` 是 ART 托管堆中的类对象，由 `AllocClass()` 分配。`LinearAlloc` 是随类加载器管理的一类线性原生内存分配器，主要承载以下元数据：

- `ArtMethod` 数组；
- `ArtField` 数组；
- 部分 IMT、方法冲突表和链接期表结构。

应用类加载器注册时，ART 为它创建 `ClassTable` 和专属 `LinearAlloc`。当该类加载器不再可达并被清理时，ART 会移除相关 JIT/CHA 依赖，随后删除对应分配器和类表。“LinearAlloc 中的类元数据永不释放”只适用于类加载器长期存活的观察窗口，不能当成 ART 的一般回收规则。

### 并发定义使用多层同步

`classlinker_classes_lock_` 保护全局类表、各加载器类表等共享结构，但 `DefineClass()` 不会从头到尾独占这把锁。插入、更新或访问 `ClassTable` 时才在限定范围内持锁。类对象自身的监视器（monitor，即 `synchronized` 使用的锁和等待机制）以及类状态变化，共同协调同一个类的并发定义、解析、验证与初始化。

并发加载不同类仍可能互相影响，来源包括：

- 类表和 DEX 注册的短临界区；
- 两个类共享父类或接口；
- verifier 递归验证父类型；
- 初始化代码等待其他线程、I/O 或应用锁；
- CHA 假设失效处理和 JIT 代码缓存（code cache）的更新。

仅凭主线程进入阻塞状态，不能直接归因于一把“ClassLinker 全局锁”。需要结合等待栈和被等待线程确认。

## 验证：编译过滤器能省掉哪部分工作

`ClassLinker::VerifyClass()` 先检查类是否已经验证，然后尝试使用 OAT/VDEX 记录的状态。只有无法取得有效的预验证结果时，才调用 `ClassVerifier::VerifyClass()`。运行时 verifier 会遍历方法，对指令和类型流做检查；API 37 的 trace 名称为 `VerifyClass <PrettyDescriptor>`，其中 `PrettyDescriptor` 表示便于阅读的类名格式。

compiler filter 决定 dexopt 执行验证、提取和方法编译到什么程度。ART Service 对三个正式支持的 filter 定义如下：

| filter | 验证与提取 | 方法编译 | profile 中类的解析与初始化 |
|---|---:|---:|---:|
| `verify` | 是 | 否 | 否 |
| `speed-profile` | 是 | profile 中的方法 | 是 |
| `speed` | 是 | 全部方法 | 否 |

`verify` 会在 dexopt 阶段执行验证并生成可复用结果；它不做预先（AOT）方法编译，也不做类解析与初始化。运行时能否跳过 verifier，还取决于产物是否存在、校验是否通过、class loader context（编译时记录的加载器类型、DEX 路径及依赖关系）是否与运行时匹配，以及编译期是否记录了需要在运行时重试的软失败。

同理，`speed-profile` 也不能保证每个启动类都不需要运行时验证。profile 覆盖范围、产物有效性、依赖变化和验证器失败类型都会改变实际路径。验证优化应以 `VerifyClass ...` 时间片（Perfetto 中记录一段起止时间的 slice）、ART 产物状态和可重复的启动测量为证据。

## 初始化：`<clinit>`、状态与可见性

### 状态包含成功、重试与失败分支

API 37 的成功主路径可概括为：

```text
kNotReady → kIdx → kLoaded → kResolving/kResolved
  → kVerifying → kVerified → kInitializing
  → kInitialized（部分架构的过渡态）→ kVisiblyInitialized
```

失败路径可能进入 `kErrorUnresolved` 或 `kErrorResolved`；编译期软验证失败还可能记录 `kRetryVerificationAtRuntime` 或 `kVerifiedNeedsAccessChecks`。OAT 中记录的 class status 可用 `kSuperclassValidated` 表示父类描述符已经校验，但运行时类对象不会把它作为每次初始化都经历的固定节点。临时类在确定最终大小并复制到正式对象后会进入 `kRetired`。因此，诊断代码不应假设每个类都会逐项经历同一组状态。

`kInitialized` 表示执行初始化的线程已经完成工作，但其他线程仍需通过 acquire 内存语义取得此前写入的值。`kVisiblyInitialized` 表示初始化结果已经对所有线程可见，编译代码因而可以使用开销更小的检查。API 37 在 x86/x86_64 或单线程事务中可直接进入 `kVisiblyInitialized`；其他路径先记录 `kInitialized`，再由批处理回调使用 `membarrier()`（Linux 内存屏障系统调用）或线程 checkpoint（让目标线程运行一段 ART 检查代码）建立可见性。

### 谁执行，谁等待

`InitializeClass()` 按《Java 语言规范》（JLS）12.4.2，使用类对象的 monitor 协调：

- 当前线程若已在初始化同一个类，递归调用直接返回成功，让当前初始化继续；
- 其他线程看到 `kInitializing` 时，在 `WaitForInitializeClass()` 中等待；
- `<clinit>` 抛异常后，类进入错误状态，后续使用会收到相应的初始化失败异常；
- 成功后更新统计、发布状态并唤醒等待线程。

同线程递归初始化可能让该线程在 `<clinit>` 尚未结束时读到默认值或阶段性值。其他线程不会把 `kInitializing` 当成初始化成功，它们会等待。两个线程分别初始化存在交叉依赖的类时，仍可能形成跨线程死锁；“`<clinit>` 可重入”只处理同一线程的递归情形。

### `<clinit>` 耗时属于应用代码

ART 会先初始化父类，并按规范处理声明了默认方法（default method）的接口，再写入 DEX 编码的静态值，最终调用类初始化方法。此处可以执行任意应用逻辑，例如读取磁盘、初始化序列化元数据、创建线程池或等待锁。耗时来自这些逻辑时，调整 compiler filter 或 DEX 次序通常只能改善外围成本，不能消除 `<clinit>` 本身。

把静态初始化改为按需加载的 holder 类、按需缓存或显式初始化前，要检查线程安全和首次使用位置。如果工作只是从进程启动移到另一个用户动作，还应衡量该动作的延迟。

## 应用冷启动中的准确时序

常规应用进程在 `ActivityThread.handleBindApplication()` 中建立 `Application`。API 37 的关键顺序如下：

```text
LoadedApk.makeApplicationInner()
  → Instrumentation.newApplication()
    → AppComponentFactory.instantiateApplication()
    → Application.attach()
      → Application.attachBaseContext()
  → ActivityThread.installContentProviders()
    → ContentProvider.onCreate()
  → Instrumentation.callApplicationOnCreate()
    → Application.onCreate()
  → 启动 Activity
```

清单中声明的 ContentProvider 会在 `attachBaseContext()` 之后、`Application.onCreate()` 之前安装。Jetpack Startup 的 `InitializationProvider` 也处在这个区间，各个 `Initializer` 的类加载和执行会阻塞后续 `Application.onCreate()`。它把多个初始化入口集中到一个 Provider，应用仍需控制每个 `Initializer` 的工作量和依赖关系。

启动阶段常见的类加载来源包括：

- 自定义 `Application`、Provider 和首个 Activity；
- 布局解析与实例化（inflate）触发的 View、Drawable 与反射构造；
- 依赖注入（DI）的生成代码或运行时扫描；
- 序列化、数据库、路由与日志框架的注册表；
- SDK 在静态字段或 `Initializer` 中建立的对象依赖图。

不要预设类加载占启动时间的固定比例。应在同一构建、同一设备和同一编译状态下运行多轮 Macrobenchmark，并从其 trace 中识别稳定热点。

## Zygote 与应用类路径

### 预加载共享了什么

`ZygoteInit.preloadClasses()` 读取 `/system/etc/preloaded-classes`。每个有效条目都通过 `Class.forName(name, true, null)` 交给 boot class loader 加载并初始化，最后调用 `VMRuntime.preloadDexCaches()`。列表条数由具体产品配置决定，不能写成跨设备固定值。

`fork` 后，应用可以借助写时复制（copy-on-write，进程修改页面时才复制）共享 Zygote 已建立的类元数据、初始化状态和相关内存页。应用仍要按 boot class path 和类表执行查找；首次解析指向自身 DEX 的引用，也可能更新应用侧用于缓存已解析字符串、类型、字段和方法的 `DexCache`。成功预加载类的定义、验证和初始化已经在 Zygote 完成，并具备共享条件，但后续查找仍有成本。

`--enable-lazy-preload` 是 Zygote 的配置分支。启用时，Zygote 启动阶段跳过立即预加载（eager preload），改在第一次 `fork` 前完成预加载。该选项由产品启动策略决定，应用不能假定 Android 17 设备都采用同一配置。

### `ApplicationLoaders` 缓存存在适用条件

`ApplicationLoaders` 的 `mLoaders` 通常以 APK/zip 路径作为缓存键（cache key），但只在 parent 等于 base parent 时查找和写入该缓存。使用自定义 parent 会新建加载器，也不会进入这条普通缓存路径。系统还会为部分不在 boot class path 中的系统库建立独立缓存，并校验 parent、加载器名称和 shared-library 环境。

同一路径只有满足缓存条件时才会复用 `PathClassLoader`。分析拆分 APK、共享库（shared library）、WebView 或插件时，要同时检查 parent 与共享库加载关系图。

## 如何在 API 37 上定位成本

### 1. 固定编译状态

类验证以及即时编译（JIT）/预先编译（AOT）状态会直接改变 trace。对比优化前后时，应明确使用哪种 Macrobenchmark `CompilationMode`，不要把首次安装时的 `verify` 状态和已完成后台 dexopt 后的 `speed-profile` 状态混在一组结果中。

设备支持 ART Service shell 命令时，可这样检查包的 dexopt 状态：

```bash
adb shell pm art dump com.example.app
```

输出可帮助确认每个 DEX 的 compiler filter、编译原因和 profile 情况。不同构建类型与设备策略可能影响可见字段，记录原始输出比只抄一个 filter 名称更可靠。

### 2. 使用 API 37 的实际 trace 名称

`ClassLinker::DefineClass()` 在 API 37 使用原始类型描述符作为 `ScopedTrace` 名称，例如 `Lcom/example/Foo;`。verifier 使用 `VerifyClass com.example.Foo` 一类名称。源码没有为每次初始化提供名为 `ClassLinker::InitializeClass` 或 `InitializeClass` 的固定 slice。

下面的 Perfetto SQL 会汇总目标进程中名称形如类描述符的 slice：

```sql
SELECT
  s.name,
  COUNT(*) AS occurrences,
  ROUND(SUM(s.dur) / 1e6, 3) AS total_ms,
  ROUND(MAX(s.dur) / 1e6, 3) AS max_ms
FROM slice AS s
JOIN thread_track AS tt ON s.track_id = tt.id
JOIN thread AS t ON tt.utid = t.utid
JOIN process AS p ON t.upid = p.upid
WHERE p.name = 'com.example.app'
  AND s.name GLOB 'L*;'
GROUP BY s.name
ORDER BY SUM(s.dur) DESC;
```

这里的 slice 覆盖 `DefineClass()` 的实际经过时间，可能包含依赖类解析和等待。汇总后还要回到时间线查看嵌套关系，不能把父 slice 与子 slice 简单相加，误当成彼此独立的成本。

验证事件可在同一查询框架中改用以下条件筛选：

```sql
s.name GLOB 'VerifyClass *'
```

若热点落在 `<clinit>`，需要使用方法采样、范围可控的方法 tracing，或在自有初始化入口增加 `Trace.beginSection()`。系统 trace 没有独立初始化 slice 时，不能拿类描述符 slice 的总时长代替 `<clinit>` 时长。

### 3. 用 SIGQUIT 看累计统计

API 37 的 `ClassLinker::DumpForSigQuit()` 会输出 Zygote/非 Zygote 已加载类数量、注册的类加载器和 DEX 路径，以及累计初始化类数量与时间。SIGQUIT 内容会交给系统的崩溃与诊断转储收集服务 `tombstoned`，不会作为完整文本写入 logcat。userdebug 构建或已取得 root 权限的设备可用 `debuggerd -j` 接收 Java dump：

```bash
adb root
pid="$(adb shell pidof com.example.app | tr -d '\r')"
adb shell debuggerd -j "$pid" > java-dump.txt
rg 'Zygote loaded classes|post zygote classes|Classes initialized|Dumping registered class loaders' java-dump.txt
```

API 37 的 `debuggerd` 实现要求 root 权限，量产用的 `user` 构建不应依赖这条流程。这些统计是进程累计值，适合比较同一测试节点上的构建差异，却不会指出单个类为何慢。Java dump 还包含完整线程信息，采集时要考虑它对进程的扰动。

### 4. 用采样确认 CPU 去向

在 userdebug 构建、可分析应用或具备相应权限的设备上，CPU 采样工具 simpleperf 可以判断时间是否耗在 `ClassLinker`、verifier、CHA，还是应用静态初始化方法。采样看到 `ClassLinker::DefineClass`，只说明采样时 CPU 调用栈经过该函数；还要结合 Perfetto 的实际经过时间，才能区分计算、调度延迟和锁等待。

## 优化顺序

### 先减少首帧前必须出现的类

优先检查 Provider、`Application.onCreate()`、首屏布局 inflate 和首帧前的同步回调。可以推迟到首帧后的 SDK，不要通过静态字段或清单（manifest）中的 Provider 提前引用。能够按需创建的大型对象依赖图，也不要在 `<clinit>` 中一次性建立。

这一步通常同时减少类定义、验证、对象分配和业务初始化，收益范围比只调 DEX 次序更广。推迟后仍要给新位置做交互延迟和线程安全测试。

### 再改善 DEX 布局与编译覆盖

- 生成覆盖真实启动入口的 Baseline Profile；
- 只把首帧所需路径纳入 Startup Profile，避免主 DEX 被低优先级路径挤满；
- 用 release/R8 构建检查最终 DEX，不要只检查尚未经过压缩、优化和混淆的 profile 生成变体；
- 通过 Macrobenchmark 分别测 `None`、`BaselineProfile` 等明确编译模式；
- 用 `pm art dump` 确认设备采用了预期产物。

Baseline Profile 可以减少解释执行、JIT 和部分运行时验证，也可能让 profile 覆盖的类从 app image（包含预初始化类对象的 ART 镜像产物）中更快恢复。它不保证消除所有 `Class` 对象的建立工作，也不会自动缩短应用写在 `<clinit>` 中的 I/O 或锁等待。

### 处理反射和运行时扫描

`Class.forName(name)` 会初始化类；只需加载时可显式使用 `Class.forName(name, false, loader)`。运行路径被 profile 采集后，反射加载的类和方法仍可出现在 Baseline/Startup Profile 中。

反射框架常见的额外成本来自字符串查找、成员枚举、注解解析、可访问性检查、参数装箱和缓存建立。代码生成可以减少这些运行时工作，但是否值得改造要以采样结果为准。隐藏 API 策略限制的是应用访问非 SDK 接口的权限，不属于普通应用的类加载性能结论。

### 谨慎并行化初始化

把 SDK 初始化全部放进线程池可能增加 DEX 映射、类表临界区、verifier、CPU 和内存带宽竞争，也可能形成跨线程 `<clinit>` 依赖。适合并行的工作应满足：依赖清楚、不阻塞首帧所需类、没有主线程回调要求，并且在目标设备上测得端到端收益。

## Android 17 边界与检查表

源码锚点为 `android-17.0.0_r1`。API 37 的结论包括：标准加载器的原生快速路径、`TypeLookupTable` 优先查找、`mirror::Class` 与 `LinearAlloc` 的内存边界、完整类状态、实际 trace 名称和 ART Service 三种正式 compiler filter。没有源码证据的“Android 17 进一步优化了某算法”不作为版本结论。

排查启动类加载时，可按以下顺序复核：

1. 编译状态是否一致，ART 产物是否有效；
2. 慢点属于定义、验证、初始化，还是依赖类递归；
3. Perfetto 中是否使用 API 37 的准确描述符/`VerifyClass` 名称；
4. 热点类为何在首帧前被引用；
5. Startup Profile 是否改善了最终 DEX 布局；
6. Baseline Profile 是否覆盖实际启动入口；
7. `<clinit>` 是否含 I/O、锁等待、大对象图或运行时扫描；
8. 自定义/DelegateLast 加载器是否改变查找顺序和类型身份；
9. 优化是否在多轮 Macrobenchmark 中保持稳定，并且没有把延迟转移到首次交互。
