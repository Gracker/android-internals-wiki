---
title: Java 类加载与 ART Boot Image
chapter: '1.4'
section: '1.4'
status: finalized
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
last_verified: '2026-09-15'
last_source_verified_at: '2026-09-15'
last_verified_against: AOSP android-17.0.0_r1 / Android common kernel android17-6.18-2026-06_r6 / Android Developers Baseline & Startup Profile docs checked 2026-09-15 / source.android.com Boot Image Profiles and on-device signing docs checked 2026-09-15
confidence: high
sources:
- type: aosp
  path: libcore/dalvik/src/main/java/dalvik/system/BaseDexClassLoader.java
- type: aosp
  path: libcore/dalvik/src/main/java/dalvik/system/DexPathList.java
- type: aosp
  path: libcore/dalvik/src/main/java/dalvik/system/DexFile.java
- type: aosp
  path: libcore/dalvik/src/main/java/dalvik/system/DelegateLastClassLoader.java
- type: aosp
  path: libcore/ojluni/src/main/java/java/lang/ClassLoader.java
- type: aosp
  path: libcore/ojluni/src/main/java/java/lang/Class.java
- type: aosp
  path: art/runtime/class_linker.cc
- type: aosp
  path: art/runtime/class_loader_utils.h
- type: aosp
  path: art/runtime/class_status.h
- type: aosp
  path: art/runtime/native/dalvik_system_DexFile.cc
- type: aosp
  path: art/runtime/oat/oat_file.cc
- type: aosp
  path: art/libdexfile/dex/type_lookup_table.h
- type: aosp
  path: art/libdexfile/dex/dex_file.cc
- type: aosp
  path: art/runtime/verifier/class_verifier.cc
- type: aosp
  path: art/libartservice/service/README.md
- type: aosp
  path: frameworks/base/core/java/com/android/internal/os/ZygoteInit.java
- type: aosp
  path: frameworks/base/core/java/android/app/ApplicationLoaders.java
- type: aosp
  path: frameworks/base/core/java/android/app/ActivityThread.java
- type: aosp
  path: frameworks/base/core/java/android/app/LoadedApk.java
- type: aosp
  path: system/core/debuggerd/debuggerd.cpp
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/difference-baseline-startup
- type: aosp
  path: art/runtime/oat/image.h, art/runtime/oat/image.cc @ android-17.0.0_r1
- type: aosp
  path: art/runtime/oat/oat_file.cc, art/runtime/oat/elf_file.cc @ android-17.0.0_r1
- type: aosp
  path: art/runtime/gc/space/image_space.h, art/runtime/gc/space/image_space.cc @ android-17.0.0_r1
- type: aosp
  path: art/libartbase/base/file_utils.cc @ android-17.0.0_r1
- type: aosp
  path: art/dex2oat/dex2oat.cc, art/dex2oat/linker/image_writer.cc @ android-17.0.0_r1
- type: aosp
  path: art/odrefresh/odrefresh.cc @ android-17.0.0_r1
- type: aosp
  path: art/profman/boot_image_profile.cc @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/com/android/internal/os/ZygoteInit.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/config/preloaded-classes @ android-17.0.0_r1
- type: kernel
  path: common/mm/memory.c @ android17-6.18-2026-06_r6
- type: official
  path: https://source.android.com/docs/core/runtime/boot-image-profiles
- type: official
  path: https://source.android.com/docs/security/features/verifiedboot/on-device-signing-architecture
- type: official
  path: https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations
- type: article
  path: 技术文章/source/juejin-android/2026-09-12-76841401-车载多 App 同屏渲染二 SurfaceControlView.md
  role: 插件同进程 ClassLoader 与 SurfaceControlViewHost 跨进程方案的边界对照
- type: article
  path: 技术文章/source/juejin-android/2026-09-15-76851907-车载多 App 同屏渲染(三) RemoteCompose 序列.md
  role: RemoteCompose 序列化 UI 作为不加载插件代码、不共享图层的边界对照
tags:
- classloader
- class-loading
- dexpathlist
- startup
- verification
- art
- ART
- boot-image
- boot.art
- boot.oat
- 内存映射
- Zygote
- 启动优化
- mmap
- dex2oat
- ImageSpace
related_chapters:
- '1.5'
- '1.16'
- '1.3'
- '8.2'
- '21.1'
- '21.4'
- '4.2'
pipeline_stage: ready-to-publish
task2b_state: body-applied
task6_state: reviewed
task9_state: reviewed
last_review_finalize_at: '2026-09-15T10:14:14+08:00'
last_review_finalize_run_id: '20260915-100505-7d4537d2'
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part1-fundamentals/ch01-architecture/36-java-class-loading-performance.md
- src/part1-fundamentals/ch01-architecture/49-art-boot-image-memory-mapping-startup.md
last_body_apply_at: '2026-09-15T09:18:26+08:00'
last_body_apply_run_id: '20260915-091600-2942e850'
---

# Java 类加载与 ART Boot Image

类加载性能取决于查找路径、DEX 元数据、验证与初始化；Boot Image 把一部分核心类和运行时状态提前生成并跨进程共享。两者共同影响启动期缺页、映射和类链接成本。

版本边界：本文按 AOSP `android-17.0.0_r1` 解释 ART、libcore 与 Framework 行为，按 Android common kernel `android17-6.18-2026-06_r6` 解释 `MAP_PRIVATE` 写时复制；应用侧 Baseline Profile 和 Startup Profile 结论以 Android Developers 文档为边界，最终仍要回到所用 AGP/R8 版本、release APK 和目标设备 trace 验证。

## 类加载委派、查找与启动成本

### 类加载包含三个动作

类加载性能涉及三类不同工作：

1. **查找并定义类**：找到 DEX 中描述该类的 `class_def`，构造 `java.lang.Class` 对象，装入字段、方法、父类和接口信息，再完成方法表布局、引用解析等链接工作。
2. **验证类**：检查 DEX 指令、类型流和访问约束。VDEX/OAT 是 dexopt 生成或使用的 ART 产物，其中可复用的验证信息能够省掉重复验证；缺少有效结果时，运行时仍要调用验证器（verifier）。
3. **初始化类**：写入 DEX 编码的静态字段初值，再执行 `<clinit>`。`<clinit>` 是虚拟机看到的类初始化方法，由静态字段初始化表达式和 `static` 代码块汇成；完成后，ART 还要按 Java 内存模型让其他线程看到初始化结果。

`ClassLoader.loadClass()` 会取得类并完成 ART 所需的定义/链接，但不会仅因这次调用就执行 `<clinit>`。验证结果可能已经存在于有效产物中；尚未满足验证条件的类，可以在后续初始化或使用路径进入 verifier。`Class.forName(name)` 的单参数重载会请求初始化。`new`、调用静态方法、读写非常量静态字段等“主动使用”也可能触发初始化。

因此，即使一段启动耗时由某个类首次出现引起，也要继续判断时间落在查找、定义/链接、验证，还是业务自己的 `<clinit>`。四者的修复方向不同。

### 从 Java API 到 ART

#### 常规 Java 路径

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

#### API 37 的 ART 快速路径

ART 自己解析类型引用时，不一定重新递归调用上述 Java 方法。`ClassLinker::FindClass()` 会先看已加载类表；未命中时，只对下列标准加载器的精确类型以及由这些标准加载器组成的 parent 链使用快速路径：

- `PathClassLoader` / `DexClassLoader`
- `InMemoryDexClassLoader`
- `DelegateLastClassLoader`

对可识别的链，`FindClassInBaseDexClassLoader()` 在 ART 原生层按对应委托顺序查找，减少 Java 与原生层之间的多次调用切换。API 37 的识别谓词比较的是这些 well-known class 的精确类型；自定义 `ClassLoader`，以及虽然继承自标准加载器、但不等于这些精确类型的加载器，都可能让 ART 回到该加载器定义的 Java `loadClass()` 行为。原生快速路径仍遵循 Java 侧对应的委托顺序。

#### `DelegateLastClassLoader` 的准确顺序

`DelegateLastClassLoader` 从 API 27 开始提供。API 37 中，已加载类仍然先由 `findLoadedClass()` 命中；新查找的顺序为：

1. boot class path；
2. `sharedLibraryLoaders`；
3. 本加载器的 DEX；
4. `sharedLibraryLoadersAfter`；
5. parent。

它只把应用/库 DEX 放到了普通 parent 之前，boot class path 仍有最高优先级。该策略适合有明确隔离需求的运行环境，不能用来给普通应用加速类加载。Java 类型身份由二进制类名和定义它的类加载器共同决定，因此同名类由谁定义会影响强制转换、包访问和链接约束。应先保证正确性，再评估性能收益。

### DEX 中怎样找到 `class_def`

“每个 DEX 都对 `class_defs` 做二分查找”不符合 API 37 实现。

`DexPathList` 或 ART 的标准加载器快速路径会依次访问加载器持有的 DEX。进入某一个 DEX 后，`OatDexFile::FindClassDef()` 的优先路径如下：

1. 如果该 DEX 关联的 `TypeLookupTable` 有效，就按类型描述符（descriptor）的 modified UTF-8 哈希值查找 `class_def_idx`；描述符形如 `Lcom/example/Foo;`，`class_def_idx` 是该类定义在 DEX 表中的索引。
2. 如果没有有效查找表，先由描述符找到 `type_id`，也就是 DEX 类型表中的条目。
3. 再调用 `DexFile::FindClassDef(type_idx)`；它在 API 37 中顺序扫描 `class_defs`，寻找引用该 `type_id` 的类定义。

`TypeLookupTable` 在编译阶段创建，运行时从已经映射到进程地址空间的产物中读取。它避免了常见路径上的整表扫描。外层 DEX 元素仍然按类路径（class path）顺序访问，所以 Startup Profile 对 DEX 布局的优化依旧有价值。

#### MultiDex 优化应看什么

评估 MultiDex 要同时检查 DEX 次序、加载器结构和运行时产物：

- 启动所需类是否集中在靠前的 DEX；
- 未命中查找是否反复穿过多个元素；
- 动态功能模块（dynamic feature）、插件或补丁是否增加了额外加载器层级；
- 产物中是否带有有效的 profile、验证信息和 `TypeLookupTable`；
- 类是否在首帧前确有必要。

Startup Profile 是构建期输入。D8/R8 用它调整 DEX 布局，优先把启动类和方法放入主 `classes.dex`；空间不足时会放到后续 DEX。Baseline Profile 则随 APK/AAB 提供给 ART，用于设备侧的 Profile 引导编译（profile-guided compilation）：ART 会优先处理 Profile 覆盖的类和方法。两者可以来自同一套生成流程，但作用阶段不同。

不要用“首 DEX 命中率必须达到某个百分比”代替测量。可在 Android Studio 的 APK Analyzer 或同等解包工具中检查 DEX 分布；如果构建链路还输出 R8/Startup Profile 元数据，也应把它当成布局辅助证据，并最终回到 release 产物和启动 trace 验证。

### `ClassLinker::DefineClass()` 做了什么

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

这段顺序解释了两个常见性能时间线（trace）现象。定义一个类可能递归解析父类和接口，因此一个外层类的实际经过时间（wall time，包含计算、等待和被调度出去的时间）会包含依赖类的工作。CHA 更新发生在类变为 `kResolved` 之前；新类若推翻了 JIT 编译器此前采用的“某调用点只有一个实现”假设，还可能让已编译代码失效并触发去优化，相关机制见 §1.5。

#### 托管堆与 `LinearAlloc` 的边界

`mirror::Class` 是 ART 托管堆中的类对象，由 `AllocClass()` 分配。`LinearAlloc` 是随类加载器管理的一类线性原生内存分配器，主要承载以下元数据：

- `ArtMethod` 数组；
- `ArtField` 数组；
- 部分 IMT、方法冲突表和链接期表结构。

应用类加载器注册时，ART 为它创建 `ClassTable` 和专属 `LinearAlloc`。当该类加载器不再可达并被清理时，ART 会移除相关 JIT/CHA 依赖，随后删除对应分配器和类表。“LinearAlloc 中的类元数据永不释放”只适用于类加载器长期存活的观察窗口，不能当成 ART 的一般回收规则。

#### 并发定义使用多层同步

`classlinker_classes_lock_` 保护全局类表、各加载器类表等共享结构，但 `DefineClass()` 不会从头到尾独占这把锁。插入、更新或访问 `ClassTable` 时才在限定范围内持锁。类对象自身的监视器（monitor，即 `synchronized` 使用的锁和等待机制）以及类状态变化，共同协调同一个类的并发定义、解析、验证与初始化。

并发加载不同类仍可能互相影响，来源包括：

- 类表和 DEX 注册的短临界区；
- 两个类共享父类或接口；
- verifier 递归验证父类型；
- 初始化代码等待其他线程、I/O 或应用锁；
- CHA 假设失效处理和 JIT 代码缓存（code cache）的更新。

仅凭主线程进入阻塞状态，不能直接归因于一把“ClassLinker 全局锁”。需要结合等待栈和被等待线程确认。

### 验证：编译过滤器能省掉哪部分工作

`ClassLinker::VerifyClass()` 先检查类是否已经验证，然后尝试使用 OAT/VDEX 记录的状态。只有无法取得有效的预验证结果时，才调用 `ClassVerifier::VerifyClass()`。运行时 verifier 会遍历方法，对指令和类型流做检查；API 37 的 trace 名称为 `VerifyClass <PrettyDescriptor>`，其中 `PrettyDescriptor` 表示便于阅读的类名格式。

compiler filter 决定 dexopt 执行验证、提取和方法编译到什么程度。ART Service 对三个正式支持的 filter 定义如下：

| filter | 验证与提取 | 方法编译 | profile 中类的解析与初始化 |
|---|---:|---:|---:|
| `verify` | 是 | 否 | 否 |
| `speed-profile` | 是 | profile 中的方法 | 是 |
| `speed` | 是 | 全部方法 | 否 |

`verify` 会在 dexopt 阶段执行验证并生成可复用结果；它不做预先（AOT）方法编译，也不做类解析与初始化。运行时能否跳过 verifier，还取决于产物是否存在、校验是否通过、class loader context（编译时记录的加载器类型、DEX 路径及依赖关系）是否与运行时匹配，以及编译期是否记录了需要在运行时重试的软失败。

同理，`speed-profile` 也不能保证每个启动类都不需要运行时验证。profile 覆盖范围、产物有效性、依赖变化和验证器失败类型都会改变实际路径。验证优化应以 `VerifyClass ...` 时间片（Perfetto 中记录一段起止时间的 slice）、ART 产物状态和可重复的启动测量为证据。

### 初始化：`<clinit>`、状态与可见性

#### 状态包含成功、重试与失败分支

API 37 的成功主路径可概括为：

```text
kNotReady → kIdx → kLoaded → kResolving/kResolved
  → kVerifying → kVerified → kInitializing
  → kInitialized（部分架构的过渡态）→ kVisiblyInitialized
```

失败路径可能进入 `kErrorUnresolved` 或 `kErrorResolved`；编译期软验证失败还可能记录 `kRetryVerificationAtRuntime` 或 `kVerifiedNeedsAccessChecks`。OAT 中记录的 class status 可用 `kSuperclassValidated` 表示父类描述符已经校验，但运行时类对象不会把它作为每次初始化都经历的固定节点。临时类在确定最终大小并复制到正式对象后会进入 `kRetired`。因此，诊断代码不应假设每个类都会逐项经历同一组状态。

`kInitialized` 表示执行初始化的线程已经完成工作，但其他线程仍需通过 acquire 内存语义取得此前写入的值。`kVisiblyInitialized` 表示初始化结果已经对所有线程可见，编译代码因而可以使用开销更小的检查。API 37 在 x86/x86_64 或单线程事务中可直接进入 `kVisiblyInitialized`；其他路径先记录 `kInitialized`，再由批处理回调使用 `membarrier()`（Linux 内存屏障系统调用）或线程 checkpoint（让目标线程运行一段 ART 检查代码）建立可见性。

#### 谁执行，谁等待

`InitializeClass()` 按《Java 语言规范》（JLS）12.4.2，使用类对象的 monitor 协调：

- 当前线程若已在初始化同一个类，递归调用直接返回成功，让当前初始化继续；
- 其他线程看到 `kInitializing` 时，在 `WaitForInitializeClass()` 中等待；
- `<clinit>` 抛异常后，类进入错误状态，后续使用会收到相应的初始化失败异常；
- 成功后更新统计、发布状态并唤醒等待线程。

同线程递归初始化可能让该线程在 `<clinit>` 尚未结束时读到默认值或阶段性值。其他线程不会把 `kInitializing` 当成初始化成功，它们会等待。两个线程分别初始化存在交叉依赖的类时，仍可能形成跨线程死锁；“`<clinit>` 可重入”只处理同一线程的递归情形。

#### `<clinit>` 耗时属于应用代码

ART 会先初始化父类，并按规范处理声明了默认方法（default method）的接口，再写入 DEX 编码的静态值，最终调用类初始化方法。此处可以执行任意应用逻辑，例如读取磁盘、初始化序列化元数据、创建线程池或等待锁。耗时来自这些逻辑时，调整 compiler filter 或 DEX 次序通常只能改善外围成本，不能消除 `<clinit>` 本身。

把静态初始化改为按需加载的 holder 类、按需缓存或显式初始化前，要检查线程安全和首次使用位置。如果工作只是从进程启动移到另一个用户动作，还应衡量该动作的延迟。

### 应用冷启动中的准确时序

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

### Zygote 与应用类路径

#### 预加载共享了什么

`ZygoteInit.preloadClasses()` 读取 `/system/etc/preloaded-classes`。每个有效条目都通过 `Class.forName(name, true, null)` 交给 boot class loader 加载并初始化，最后调用 `VMRuntime.preloadDexCaches()`。列表条数由具体产品配置决定，不能写成跨设备固定值。

`fork` 后，应用可以借助写时复制（copy-on-write，进程修改页面时才复制）共享 Zygote 已建立的类元数据、初始化状态和相关内存页。应用仍要按 boot class path 和类表执行查找；首次解析指向自身 DEX 的引用，也可能更新应用侧用于缓存已解析字符串、类型、字段和方法的 `DexCache`。成功预加载类的定义、验证和初始化已经在 Zygote 完成，并具备共享条件，但后续查找仍有成本。

`--enable-lazy-preload` 是 Zygote 的配置分支。启用时，Zygote 启动阶段跳过立即预加载（eager preload），改在第一次 `fork` 前完成预加载。该选项由产品启动策略决定，应用不能假定 Android 17 设备都采用同一配置。

#### `ApplicationLoaders` 缓存存在适用条件

`ApplicationLoaders` 的 `mLoaders` 通常以 APK/zip 路径作为缓存键（cache key），但只在 parent 等于 base parent 时查找和写入该缓存。使用自定义 parent 会新建加载器，也不会进入这条普通缓存路径。系统还会为部分不在 boot class path 中的系统库建立独立缓存，并校验 parent、加载器名称和 shared-library 环境。

同一路径只有满足缓存条件时才会复用 `PathClassLoader`。分析拆分 APK、共享库（shared library）、WebView 或插件时，要同时检查 parent 与共享库加载关系图。

#### 插件加载不是进程隔离边界

把插件 APK 追加到宿主的 `DexClassLoader`、`PathClassLoader` 或其他 `BaseDexClassLoader` 链路时，改变的是宿主进程内的 DEX 查找路径和类定义归属；插件的静态初始化、View/Compose 运行时代码和崩溃仍发生在宿主进程内。外部材料中的车载多 App 同屏案例把这种 ClassLoader 方案作为第一版：插件 APK 被加载进宿主进程，插件 View 直接挂在宿主视图树，集成简单，但插件崩溃会带崩宿主，Compose 版本也必须与宿主对齐。[来源: 技术文章/source/juejin-android/2026-09-12-76841401-车载多 App 同屏渲染二 SurfaceControlView.md；已验证: libcore/dalvik/src/main/java/dalvik/system/BaseDexClassLoader.java 与 frameworks/base/core/java/android/app/ApplicationLoaders.java @ android-17.0.0_r1]

因此，优化或重排类加载路径只能降低查找、定义、验证和初始化成本，不能提供故障隔离或依赖版本隔离。需要“插件独立进程渲染、宿主只展示结果”的场景，应切到 IPC 与跨进程 UI 嵌入：前一篇材料用 `SurfaceControlViewHost` 对照说明，宿主通过 AIDL 传出 `hostToken`，Provider 在自己的进程中创建内容并把 `SurfacePackage` 回传，最终由 SurfaceFlinger 合成到同一屏；这解决的是进程隔离和图层嵌入，不是一个更快的 ClassLoader。[来源: 技术文章/source/juejin-android/2026-09-12-76841401-车载多 App 同屏渲染二 SurfaceControlView.md]

如果场景只是展示型卡片，RemoteCompose 这类数据化方案把边界推得更远：Provider 把 UI 描述序列化成字节文档，通过 AIDL 交给宿主；宿主用自己的播放器解释并绘制这份文档，既不把插件 View 挂进宿主视图树，也不共享 Provider 的实时 `Surface`，插件代码不会在宿主进程执行。Provider 交付文档后不必持续持有渲染面，崩溃边界不再表现为宿主类加载失败或嵌入图层黑屏；代价是交互被收敛到预声明动作、回传 `actionId`、重新生成文档这类有限往返，不适合滚动、拖拽等连续交互。该材料使用的是应用层 `androidx.compose.remote:*` alpha 实现，并提醒平台侧 `com.android.internal.widget.remotecompose.*` 属于隐藏实现，不能把示例 API 写成 Android 17 稳定 SDK 契约。[来源: 技术文章/source/juejin-android/2026-09-15-76851907-车载多 App 同屏渲染(三) RemoteCompose 序列.md]

排查这类方案时，先确认代码运行在哪个进程：同进程插件的类加载、`<clinit>` 和崩溃栈会出现在宿主进程，SIGQUIT/Perfetto 中也应在宿主进程看到对应加载器、DEX 路径或类加载 slice；SCVH 这类跨进程嵌入则应同时观察宿主进程、Provider 进程、Binder 连接和 surface 可见性，Provider 死亡可能导致嵌入区域黑屏或停更；RemoteCompose 这类字节文档路径则应优先核对宿主播放器、Binder 文档传输和 Provider 重新生成文档的时机，若宿主出现插件 DEX 加载或插件 `<clinit>` 热点，应先怀疑架构中混入了同进程加载，而不是把它归因于 RemoteCompose 文档渲染。[来源: 技术文章/source/juejin-android/2026-09-12-76841401-车载多 App 同屏渲染二 SurfaceControlView.md；来源: 技术文章/source/juejin-android/2026-09-15-76851907-车载多 App 同屏渲染(三) RemoteCompose 序列.md；已验证: system/core/debuggerd/debuggerd.cpp 与 art/runtime/class_linker.cc @ android-17.0.0_r1]

### 如何在 API 37 上定位成本

#### 1. 固定编译状态

类验证以及即时编译（JIT）/预先编译（AOT）状态会直接改变 trace。对比优化前后时，应明确使用哪种 Macrobenchmark `CompilationMode`，不要把首次安装时的 `verify` 状态和已完成后台 dexopt 后的 `speed-profile` 状态混在一组结果中。

设备支持 ART Service shell 命令时，可这样检查包的 dexopt 状态：

```bash
adb shell pm art dump com.example.app
```

输出可帮助确认每个 DEX 的 compiler filter、编译原因和 profile 情况。不同构建类型与设备策略可能影响可见字段，记录原始输出比只抄一个 filter 名称更可靠。

#### 2. 使用 API 37 的实际 trace 名称

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

#### 3. 用 SIGQUIT 看累计统计

API 37 的 `ClassLinker::DumpForSigQuit()` 会输出 Zygote/非 Zygote 已加载类数量、注册的类加载器和 DEX 路径，以及累计初始化类数量与时间。SIGQUIT 内容会交给系统的崩溃与诊断转储收集服务 `tombstoned`，不会作为完整文本写入 logcat。userdebug 构建或已取得 root 权限的设备可用 `debuggerd -j` 接收 Java dump：

```bash
adb root
pid="$(adb shell pidof com.example.app | tr -d '\r')"
adb shell debuggerd -j "$pid" > java-dump.txt
rg 'Zygote loaded classes|post zygote classes|Classes initialized|Dumping registered class loaders' java-dump.txt
```

API 37 的 `debuggerd` 实现要求 root 权限，量产用的 `user` 构建不应依赖这条流程。这些统计是进程累计值，适合比较同一测试节点上的构建差异，却不会指出单个类为何慢。Java dump 还包含完整线程信息，采集时要考虑它对进程的扰动。

#### 4. 用采样确认 CPU 去向

在 userdebug 构建、可分析应用或具备相应权限的设备上，CPU 采样工具 simpleperf 可以判断时间是否耗在 `ClassLinker`、verifier、CHA，还是应用静态初始化方法。采样看到 `ClassLinker::DefineClass`，只说明采样时 CPU 调用栈经过该函数；还要结合 Perfetto 的实际经过时间，才能区分计算、调度延迟和锁等待。

### 优化顺序

#### 先减少首帧前必须出现的类

优先检查 Provider、`Application.onCreate()`、首屏布局 inflate 和首帧前的同步回调。可以推迟到首帧后的 SDK，不要通过静态字段或清单（manifest）中的 Provider 提前引用。能够按需创建的大型对象依赖图，也不要在 `<clinit>` 中一次性建立。

这一步通常同时减少类定义、验证、对象分配和业务初始化，收益范围比只调 DEX 次序更广。推迟后仍要给新位置做交互延迟和线程安全测试。

#### 再改善 DEX 布局与编译覆盖

- 生成覆盖真实启动入口的 Baseline Profile；
- 只把首帧所需路径纳入 Startup Profile，避免主 DEX 被低优先级路径挤满；
- 用 release/R8 构建检查最终 DEX，不要只检查尚未经过压缩、优化和混淆的 profile 生成变体；
- 通过 Macrobenchmark 分别测 `None`、`BaselineProfile` 等明确编译模式；
- 用 `pm art dump` 确认设备采用了预期产物。

Baseline Profile 可以减少解释执行、JIT 和部分运行时验证，也可能让 profile 覆盖的类从 app image（包含预初始化类对象的 ART 镜像产物）中更快恢复。它不保证消除所有 `Class` 对象的建立工作，也不会自动缩短应用写在 `<clinit>` 中的 I/O 或锁等待。

#### 处理反射和运行时扫描

`Class.forName(name)` 会初始化类；只需加载时可显式使用 `Class.forName(name, false, loader)`。运行路径被 profile 采集后，反射加载的类和方法仍可出现在 Baseline/Startup Profile 中。

反射框架常见的额外成本来自字符串查找、成员枚举、注解解析、可访问性检查、参数装箱和缓存建立。代码生成可以减少这些运行时工作，但是否值得改造要以采样结果为准。隐藏 API 策略限制的是应用访问非 SDK 接口的权限，不属于普通应用的类加载性能结论。

#### 谨慎并行化初始化

把 SDK 初始化全部放进线程池可能增加 DEX 映射、类表临界区、verifier、CPU 和内存带宽竞争，也可能形成跨线程 `<clinit>` 依赖。适合并行的工作应满足：依赖清楚、不阻塞首帧所需类、没有主线程回调要求，并且在目标设备上测得端到端收益。

### Android 17 边界与检查表

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


## Boot Image 的映射、共享与失效

普通类加载沿 ClassLoader 和 DEX 路径查找，Boot Image 则把常用类放进预生成映像。映像是否命中、是否重定位以及页面如何共享，会直接改变前一阶段的成本。

Boot Image 处在 ART 启动、系统镜像预编译和 Zygote 共享内存的交点。排查开机变慢、Zygote 私有脏页增长或 ART Mainline（可独立于完整系统 OTA 更新的 ART 模块）更新后的编译行为时，需要分别观察镜像文件、编译 profile 和 Zygote 预加载。

平台行为以 Android 17 / API 37 / `android-17.0.0_r1` 为准；涉及 `MAP_PRIVATE` 与写时复制的内核行为以 `android17-6.18-2026-06_r6` 为准。

本文中的 ART 指 Android Runtime，Zygote 是预先初始化运行时、再 fork 出 System Server 和应用进程的父进程。Boot Class Path 是系统核心 Java 类路径，System Server Class Path 则承载 `system_server` 专用类。profile 是记录应优先处理哪些类和方法的编译输入；AOT（Ahead-of-Time）表示运行前编译，JIT（Just-in-Time）表示运行时即时编译。

### Boot Image 保存了什么

ART Boot Image 是 `dex2oat` 生成的可加载运行时快照。它保存选入镜像的 Java 对象、类元数据和 ART native 元数据，并与相应的 AOT 代码一起使用。运行时可以直接恢复这批对象和元数据，省去重复分配、链接及一部分初始化工作。

这项机制有两个边界：

- Boot Image 不等于整个 Boot Class Path。哪些类进入 `.art` 镜像、哪些方法获得 AOT 代码，受 Boot Image Profile、编译过滤器和构建配置共同影响。
- Boot Image 不等于 Zygote 完成 `preload()` 后的完整堆。Zygote 还会加载类、资源、共享库和图形驱动；这些操作产生的对象位于其他堆空间。

#### `.art`、`.oat`、`.vdex` 的职责

一个 Boot Image 组件通常对应三类产物：

| 产物 | 主要内容 | 运行时用途 |
| --- | --- | --- |
| `.art` | `ImageHeader`、镜像对象、`ArtField`、`ArtMethod`、类表、字符串表、位图等 | 建立 `ImageSpace`，恢复预先构造的对象和 ART 元数据 |
| `.oat` | OAT 头、编译代码、运行时所需元数据 | 提供 AOT 代码和镜像依赖信息 |
| `.vdex` | DEX 字节码与验证相关数据；是否携带 DEX section（文件区段）取决于产物模式 | 配合 OAT 打开 DEX，复用验证结果 |

“三个固定文件”只适合解释最小模型。Android 17 默认使用多组件能力：一个主镜像可以覆盖多个 Boot Class Path 组件，也可以接若干 Boot Image Extension（附加在主镜像后的扩展镜像）。多镜像构建时会出现 `boot.art`、`boot-framework-*.art` 等文件，并各有对应的 `.oat`、`.vdex`。

`services.jar` 属于 System Server Class Path，不应当为了说明 Boot Image 而写进 Boot Class Path 清单。`odrefresh` 对 Boot Class Path 和 System Server Class Path 使用两套检查与编译流程。

### Android 17 的产物位置由运行时选择

源码中的 image location（镜像位置）是一条组件描述，运行时还要把它展开成当前指令集的文件路径。以 `/system/framework/boot.art` 为例，`GetSystemImageFilename()` 会定位到类似 `/system/framework/arm64/boot.art` 的实际文件。

`GetDefaultBootImageLocationSafe()` 在 Android 17 上按以下次序选择默认镜像：

1. `odsign.verification.success` 为 `true`，且 `/data/misc/apexdata/com.android.art/dalvik-cache` 中存在完整主镜像时，优先使用这里的 `boot.art`。`odrefresh` 负责检查和重建设备端 ART 产物，`odsign` 负责校验这些产物。
2. 完整镜像生成失败但最小镜像可用时，可以使用 `boot_minimal.art`。最小镜像只覆盖 ART 模块内的 Boot Class Path JAR，后续组件按配置处理。
3. 没有可用的 `/data` 产物时，使用系统分区预编译镜像。Android 17 源码注释给出的主位置是 `/system/framework/boot.art`，实际文件仍带指令集子目录。
4. Mainline Boot Class Path JAR 可以拥有单独的 Boot Image Extension，运行时把它附加到主镜像描述中。

ART 已经模块化，并不表示 `boot.art` 一定位于 `/apex/com.android.art`。APEX 是系统模块的安装与更新容器；ART APEX 提供运行时、profile 和工具。当前进程使用的镜像可能来自 `/system`，也可能来自 ART APEX 的 `/data` 目录。

`GetBootImageLocationForDefaultBcpRespectingSysProps()` 会在 `odsign.verification.success` 不为 `true` 时设置 `deny_art_apex_data_files`。即使 `/data` 中残留同名文件，运行时也不会仅凭路径存在就采用它；设备取证应把 `odsign` 验证结果与进程 `maps` 一起检查。

### `dex2oat` 生成 Boot Image 的方式

#### 主镜像与扩展镜像

`dex2oat` 根据参数区分三种 image：

- 传入 `--image` 且没有 `--boot-image`：生成主 Boot Image。
- 同时传入输出 image 和已有 `--boot-image`：生成 Boot Image Extension。
- 传入 `--app-image-file` 或 `--app-image-fd`：生成 App Image。

Android 17 的 AOT 编译统一使用位置无关代码（PIC，代码可在不同装载地址执行），`Dex2Oat::ProcessOptions()` 直接设置 `compile_pic_ = true`。“Boot Image 依赖位置相关机器码，地址稍变就无法运行”不符合当前实现。

#### profile 对类和方法的选择不同

Boot Image Profile 同时携带类和方法信息：

- 类条目参与决定哪些类进入 `.art` 镜像。
- 方法的热（hot）、启动（startup）等标记参与 `speed-profile` 编译决策。

进入镜像的类不代表其全部方法都被 AOT 编译；获得 AOT 代码的方法也不能简单等同于 `preloaded-classes`。Android 12 起，官方 ART 配置将 Boot Image 编译过滤器固定为 `speed-profile`，即按 profile 编译重点方法。Android 17 的 `odrefresh` 也把主镜像和 Mainline 扩展的默认过滤器设为 `speed-profile`；扩展缺少 profile 时会回退到只做验证、不生成同等优化代码的 `verify`。

#### `preloaded-classes` 和 `dirty-image-objects`

`odrefresh` 生成主镜像时还会读取：

- `/system/etc/preloaded-classes`：传给 `dex2oat --preloaded-classes-fds`，同时由 Zygote 在 Java 层逐项加载并初始化。
- `/system/etc/dirty-image-objects` 与 ART APEX 内同名文件：给 `ImageWriter` 提供容易被写脏的对象信息，改善对象排布，减少少量可变对象导致整页失去共享的概率。

Android 17 AOSP 手机配置中的 `preloaded-classes` 有 18,784 个有效条目。这个数字只描述该 tag 的默认 phone 配置；产品可以替换该文件，后续版本也会变化，不能当作平台契约。

### `.art` 文件结构

Android 17 的定义位于 `art/runtime/oat/image.h`，文件格式实现位于 `art/runtime/oat/image.cc`。旧资料常写成 `runtime/image.h` 或不存在的 `runtime/image_header.cc`，检索源码时要用当前路径。

`ImageHeader` 记录的内容包括：

- 格式 magic（文件类型标识）与 version；`android-17.0.0_r1` 中分别为 `art\n` 和 `119`。
- 镜像预留大小、组件数、期望地址、镜像大小与镜像校验和。
- 对应 OAT 的校验和及地址范围。
- 依赖 Boot Image 的起始地址、大小、组件数与组合校验和。
- image roots、指针大小、各 section 的偏移和大小。
- 压缩块信息；镜像可以使用未压缩、LZ4 或压缩率更高的 LZ4HC 存储。

Android 17 的 `ImageSections` 顺序如下：

| Section | 内容 |
| --- | --- |
| `kSectionObjects` | Java 镜像对象 |
| `kSectionArtFields` | `ArtField` 数据 |
| `kSectionArtMethods` | `ArtMethod` 数据 |
| `kSectionImTables` | 接口方法表（IMT） |
| `kSectionIMTConflictTables` | 接口方法表的冲突处理表 |
| `kSectionRuntimeMethods` | ART 运行时方法 |
| `kSectionJniStubMethods` | JNI stub（调用桥接）方法 |
| `kSectionInternedStrings` | intern（驻留并复用唯一实例的）字符串集合 |
| `kSectionClassTable` | 类表 |
| `kSectionStringReferenceOffsets` | 字符串引用偏移 |
| `kSectionDexCacheArrays` | `DexCache` 数组 |
| `kSectionMetadata` | 镜像附加元数据 |
| `kSectionImageBitmap` | ImageSpace 存活位图 |

`ImageHeader::IsValid()` 检查格式和地址范围。加载器还会检查文件长度、位图位置、组件数、预留大小、OAT 校验和及 Boot Class Path 依赖，不只比较魔数。

### 运行时如何映射和重定位

调用起点在 `Heap` 构造阶段。下面的调用骨架只保留与 Boot Image 加载有关的函数：

```text
Runtime::Init()
  └─ Heap::Heap()
      └─ ImageSpace::LoadBootImage()
          └─ ImageSpace::BootImageLoader::LoadFromSystem()
              ├─ ReserveBootImageMemory()
              ├─ LoadComponents()
              │   ├─ ImageSpace::Loader::Init()
              │   └─ OpenOatFile()
              ├─ MaybeRelocateSpaces()
              └─ DeduplicateInternedStrings()
```

这条调用路径发生在 `ZygoteInit.preload()` 之前。Java 层开始预加载时，Boot Image 对应的 `ImageSpace` 和 OAT 已经加入 ART 堆。

#### 预留连续地址并装入组件

`BootImageLoader::LoadImage()` 计算所有组件和 OAT 所需的总预留大小，然后调用 `ReserveBootImageMemory()`。启用 relocation 时，基址由 `ART_BASE_ADDRESS + ChooseRelocationOffsetDelta()` 得出；未启用时使用镜像头中的基址。

地址改变不会直接导致 fatal abort（进程因致命错误退出）。`MaybeRelocateSpaces()` 计算实际地址与 `ImageHeader::GetImageBegin()` 的差值，再由 `Relocator::RelocateBootImage()` 修正镜像内的对象引用和 native 指针。加载器还会为 OAT 初始化运行时 relocation（地址重定位）。

预留连续地址仍有价值：多个 image 与 OAT 可以按构建时布局装入同一段低 4 GB 地址空间，引用编码和相邻空间预留也更容易满足。这里的“低 4 GB”指虚拟地址小于 4 GiB 的区域；它不等于“所有内部指针都是不可调整的绝对地址”。

#### 未压缩镜像与压缩镜像的映射不同

未压缩且允许直接映射时，`LoadImageFile()` 使用：

```cpp
MemMap::MapFileAtAddress(
    address,
    image_size,
    PROT_READ | PROT_WRITE,
    MAP_PRIVATE,
    fd,
    start,
    /* low_4gb= */ true,
    image_filename,
    /* reuse= */ false,
    image_reservation,
    error_msg);
```

这段源码说明 image object 区以 `MAP_PRIVATE` 私有文件映射装入，初始权限 `PROT_READ | PROT_WRITE` 表示可读写。Android 17 的 `ImageSpace` 加载代码没有在 Zygote `fork` 前统一通过 `mprotect(PROT_READ)` 把整段镜像改成只读；把“fork 前统一转为只读”写成固定步骤会误导排查。

压缩镜像需要建立匿名读写映射，再从只读文件映射解压进去；运行期生成到 `memfd`（只存在于内存中的匿名文件描述符）的 Boot Image Extension 也会禁用直接映射，并复制到匿名映射。此时物理页共享特征与直接文件映射不同，诊断时要以 `/proc/<pid>/maps`、`smaps` 中的实际映射为准。

记录镜像对象位置的 Image bitmap 单独以 `PROT_READ | MAP_PRIVATE` 映射。OAT 则由 `OatFile::Open()` 按文件段及是否允许执行建立映射，不能用一句“整个 `boot.oat` 都是 `PROT_READ|PROT_EXEC`”概括。

### Zygote 共享与写时复制

Boot Image 的内存收益有两层来源：

1. 直接文件映射让多个进程可以引用同一份 page cache（文件页缓存）。
2. Zygote `fork()` 让子进程继承相同页表；匿名页和私有文件页在发生写入前都可以共享。

`MAP_PRIVATE` 表示写入不会回写原文件。Linux 在私有映射发生 write fault（首次写入触发的页故障）时执行写时复制（Copy-on-Write，COW）；`android17-6.18-2026-06_r6` 的相关实现位于 `mm/memory.c`。页面一旦被某个进程修改，该进程获得私有页，PSS、`Private_Dirty` 和物理内存占用随之变化。

读写权限并不等于页面已经私有化。只有写入落到该页时才会产生私有副本。文件映射也不保证永远保持 `Shared_Clean`（可共享且未被写脏的页）：类初始化、对象头中的锁状态、运行时修正或同页其他可变对象都可能写脏页面。`dirty-image-objects` 的排布优化用于减少“一处写入使整页私有化”的页级放大。

#### Zygote 的 `preload()` 是另一层共享

`ZygoteInit.preload()` 的 Android 17 顺序包括：

- `preloadClasses()`：读取 `/system/etc/preloaded-classes`，对每个条目执行 `Class.forName(line, true, null)`，明确要求初始化。
- 缓存非 Boot Class Path 的类加载器。
- 预加载资源、共享库、文本资源、兼容性配置和部分图形相关组件。
- `ZygoteHooks.onEndPreload()` 完成 ART 侧收尾。
- 返回主流程后调用 `gcAndFinalize()`，清理预加载期间产生的临时对象，再开始 fork System Server 和应用进程。

Boot Image 提供构建期生成的对象与元数据；Zygote preload 提供本次开机中的类初始化和额外对象。两者都能减少子进程重复工作，但对象来源、生成时机和调优入口不同。

### 五类 profile 与清单的作用阶段

| 名称 | 作用对象 | 使用阶段 | 是否直接改变 Boot Image |
| --- | --- | --- | --- |
| Boot Image Profile | Boot Class Path 的类和方法 | 系统构建或 `odrefresh` 编译 Boot Image | 是，影响 image class 与 `speed-profile` 方法编译 |
| `preloaded-classes` | Zygote 要加载并初始化的类 | Zygote 启动；也传给 Boot Image 编译器 | 会参与编译约束，但主要职责是 Zygote 预加载 |
| System Server profile | System Server Class Path JAR | 系统构建或 `odrefresh` 编译 System Server 产物 | 不修改主 Boot Image |
| 应用 Baseline Profile | 应用或库的方法与类 | 安装、更新及 ART dexopt | 不修改平台 Boot Image |
| 应用 Startup Profile | 应用启动路径中的类和方法 | R8/D8 构建应用时优化 DEX 布局 | 不修改平台 Boot Image |

应用 Startup Profile 通常对应 Baseline Profile 中启动路径规则的那一部分，用来影响最终安装 APK 中 DEX 的排列，让启动代码更集中。官方构建链路把这项优化限定在应用构建期：需要启用 R8（release build 的 minify）和 AGP 8.1+ 的 DEX layout optimization，AGP 8.3 起默认启用；AGP 8.1–8.2 需要在 app 模块 `baselineProfile {}` 中显式设置 `dexLayoutOptimization = true`，AGP 8.2 还不支持按 variant 区分 Startup Profile。Startup Profile 不能由库单独贡献，必须由应用启动测试生成。它不会生成 `/system/etc/preloaded-classes`，也不会选择平台 `boot.art` 中的类。

Boot Image Profile 与 `preloaded-classes` 可以来自同一批代表性使用场景采样。`profman --generate-boot-image-profile` 也能同时输出 Boot Image Profile 和预加载类清单，但两个输出文件的用途不同。

### ART Mainline 更新与 `odrefresh`

Android 12 起，ART 是可更新的 Mainline 模块。早期启动阶段的 `odsign` 会调用 `odrefresh` 检查运行时产物；Android 17 源码检查的输入包括：

- ART APEX 与其他相关 APEX 的版本信息。
- 影响编译结果的系统属性。
- Boot Class Path JAR 的数量、大小和校验和。
- System Server Class Path JAR 的数量、大小和校验和。
- 已生成产物及 `cache-info.xml` 的一致性。

检查失败时，`odrefresh` 可以重新生成主 Boot Image、Mainline Extension 和需要更新的 System Server 产物，默认输出目录是 `/data/misc/apexdata/com.android.art/dalvik-cache`。完整主镜像编译失败时，源码还会尝试生成只覆盖 ART 模块 JAR 的最小镜像，并在后续启动重试完整编译。

profile 输入和运行时产物的边界如下：

- 官方文档所说“Boot Image Profile 只能随 OTA（系统无线更新）更新”，对应系统镜像内的 framework profile。Mainline APEX 还可以携带模块自己的 `etc/boot-image.prof`，Android 17 会把已安装模块提供的 profile 加入扩展镜像编译。
- `odrefresh` 可以在 ART/APEX 或 Boot Class Path 变化后，用当前系统和 APEX 提供的 profile 输入重新生成 `/data` 下的 `.art/.oat/.vdex`。

“ART Mainline 更新不会重建 Boot Image”不符合上述流程。

#### Boot Image 变化不代表所有应用立即重编

应用 OAT 产物记录 Boot Class Path、image checksum（镜像校验和）或 class loader context（类加载器及依赖关系描述）等依赖信息。ART 按产物和当前上下文判断能否继续使用；失效的产物再由 ART Service 安排 dexopt（DEX 优化或编译）。一次 Boot Image 变化可能让大量应用产物失效，但源码没有“无条件重新编译所有应用”的规则。

Boot Image、System Server 产物与普通应用产物的维护者也不同：

- `odrefresh`/`odsign` 负责早期启动需要的 Boot Class Path 与 System Server 运行时产物。
- Android 14 及以后由 ART Service 管理普通应用 dexopt。
- 产物不可用时，ART 还可能以 JIT、解释执行或 imageless（不加载 Boot Image）模式继续启动；具体退化方式取决于缺失的是主镜像、扩展还是应用编译产物。

### 确认设备正在使用的镜像

#### 1. 查看配置与进程映射

以下命令用于确认是否覆盖默认 image location，并查出 Zygote 映射的实际文件。读取其他进程的 `/proc` 信息通常需要 root，或用于调试的 `userdebug`/`eng` 构建。

```bash
adb shell getprop dalvik.vm.boot-image
adb shell 'pid=$(pidof zygote64); cat /proc/$pid/maps | grep -E "boot.*\\.(art|oat|vdex)"'
```

属性为空表示运行时采用默认选择逻辑，不代表没有 Boot Image。`/proc/<pid>/maps` 列出进程的虚拟内存映射，其中的路径是当前进程使用位置的直接证据；还要同时检查 32 位 Zygote 或其他运行时进程。

#### 2. 用 `smaps` 判断共享质量

`smaps` 在 `maps` 基础上给出每段映射的内存统计。以下命令用于观察 Boot Image 的 `Shared_Clean`（可共享的干净页）、`Private_Clean`（当前为该进程私有、但未写脏的页）和 `Private_Dirty`（该进程私有且已写脏的页）：

```bash
adb shell 'pid=$(pidof zygote64); cat /proc/$pid/smaps' > zygote64-smaps.txt
```

从输出中按 `.art`、`.oat` 路径分组，再比较 Zygote 与多个应用进程。RSS（驻留物理内存）会在每个进程中重复计入共享页；PSS（按共享者数量分摊后的物理内存）适合估算分摊成本，`Private_Dirty` 更适合定位写时复制增长。

#### 3. 用 `oatdump` 检查镜像内容

`oatdump` 是 ART 产物检查工具，其 `--image` 参数接受单个或冒号分隔的 Boot Image location。下面的命令用于检查系统分区上的一个主镜像：

```bash
adb shell oatdump --image=/system/framework/boot.art
```

设备若使用 `/data` 产物或扩展组件，需要把 `maps` 中确认的 location 按组件顺序传入。输出可核对 image header、section、对象、OAT 依赖和编译代码；工具可用性与读取权限取决于构建类型。

#### 4. 区分 `odrefresh` 与应用 dexopt

ART 产物更新问题应同时收集：

- early boot（系统早期启动）日志中的 `odrefresh`、`odsign`、`dex2oat`。
- `/data/misc/apexdata/com.android.art/dalvik-cache` 中产物的时间戳和完整性。
- `odrefresh` 的编译阶段、触发原因与失败原因。
- ART Service 对应用执行的 dexopt 记录。

这些证据可以区分 Boot Image 重建、System Server 编译和应用 dexopt，避免把三类耗时合成一个“OTA 后重编”结论。

### OEM 调整的验证边界

OEM 可以调整 Boot Class Path、Boot Image Profile、`preloaded-classes` 和 `dirty-image-objects`，但每项改动都需要整机数据验证：

- Boot Image Profile 过小，会增加常用类恢复、方法解释/JIT 和随机 I/O；过大则增加文件尺寸、映射范围及实际驻留内存的页数。
- `preloaded-classes` 过小，会把类加载和初始化移到应用冷启动；过大会拉长 Zygote preload，并增加共享堆与脏页压力。
- 容易写入的对象散布在大量页面中，会抬高每个子进程的 `Private_Dirty`。只比较 `boot.art` 文件大小看不到这项成本。
- Mainline Boot Class Path JAR、System Server JAR 和自定义 Boot Class Path JAR 要放在正确的 classpath（类路径）配置中。把 `services.jar` 当作 Boot Class Path 组件会让编译依赖模型失真。

调优至少要同时观察 Zygote preload 时间、应用冷启动、Boot Image/OAT 文件尺寸、各进程 PSS、`Private_Dirty`、page fault（缺页异常）和 dexopt/JIT 行为。单个指标变好不能证明整机收益。

### 源码阅读入口

- `art/runtime/oat/image.h`、`image.cc`：格式版本、`ImageHeader`、section 和压缩块。
- `art/runtime/oat/oat_file.cc`、`elf_file.cc`：OAT 文件打开路径与 ELF segment 权限映射。
- `art/runtime/gc/space/image_space.h`、`image_space.cc`：image location 解析、预留、映射、校验、扩展加载和重定位。
- `art/libartbase/base/file_utils.cc`：Android 17 默认 Boot Image location 与 `/system`、`/data` 选择。
- `art/dex2oat/dex2oat.cc`、`dex2oat/linker/image_writer.cc`：主镜像/扩展识别、profile、对象选择与布局。
- `art/odrefresh/odrefresh.cc`：更新检查、`speed-profile` 参数、完整/最小镜像与 System Server 编译。
- `art/profman/boot_image_profile.cc`：从采样 profile 生成 Boot Image Profile 和预加载类清单。
- `frameworks/base/core/java/com/android/internal/os/ZygoteInit.java`：`preload()`、`preloadClasses()`、`gcAndFinalize()` 与 `fork` 前流程。
- `common/mm/memory.c`：`MAP_PRIVATE` 写 fault 与写时复制。

### Android 17 的映射与共享边界

Android 17 的 Boot Image 是一组可校验、可重定位、可扩展的 ART 运行时产物。`.art` 保存选入镜像的对象和元数据，`.oat` 提供编译代码，`.vdex` 保存 DEX 与验证相关数据；运行时可能从系统分区加载，也可能使用 `odrefresh` 在 ART APEX 数据目录生成的版本。

Boot Image Profile、Boot Image Extension、Zygote `preloaded-classes`、应用 Baseline Profile 和应用 Startup Profile 分属不同环节。性能分析只有在文件来源、映射类型、私有脏页、Zygote 预加载和 ART 产物更新原因分别确认后，才有足够证据修改配置。
