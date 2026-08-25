---
title: 依赖注入框架性能：Dagger/Hilt/Koin 启动开销与优化
chapter: '21.8'
section: '21.8'
status: finalized
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
tags:
- dependency-injection
- dagger
- hilt
- koin
- startup
- ksp
- kapt
related_chapters:
- '21.1'
- '21.2'
- '21.3'
- '8.2'
- '1.7'
last_verified: '2026-08-14'
last_verified_against: AOSP android-17.0.0_r1 ActivityThread; Dagger/Hilt 2.60.1 source and current docs; Koin 4.2/4.2.2 docs and source; Android Developers Hilt and KSP docs updated through 2026-08-13
confidence: high
sources:
- type: aosp
  path: frameworks/base/core/java/android/app/ActivityThread.java
- type: upstream
  path: google/dagger dagger-2.60.1 ApplicationGenerator.java, ApplicationComponentManager.java
- type: official
  path: https://dagger.dev/hilt, https://dagger.dev/hilt/flags, https://dagger.dev/dev-guide/compiler-options
- type: official
  path: https://developer.android.com/training/dependency-injection/hilt-android
- type: official
  path: https://insert-koin.io/docs/reference/koin-core/starting-koin, definitions, lazy-modules
- type: official
  path: https://developer.android.com/build/migrate-to-ksp
---

# 依赖注入框架性能：Dagger/Hilt/Koin 启动开销与优化

依赖注入（Dependency Injection，DI）把一个对象需要的依赖从外部提供给它，避免对象自己查找或创建依赖。一次注入至少包含四类工作：创建 container/component（保存依赖规则与生命周期缓存的容器）、建立 `Provider` 工厂、解析 binding（某个类型应怎样获得实例的绑定规则），以及执行对象构造和初始化。

Dagger/Hilt 在编译期分析依赖关系并生成 Java 代码；Koin 4.2 的经典 DSL 会在运行时注册 definition（Koin 对创建规则的描述）并按 key 查找。两者把成本放在不同阶段，不过启动长尾通常来自被 DI 拉起的重构造函数、`@Provides` 方法或 definition lambda，而非一次轻量查找本身。这里的“长尾”指 P90/P99（分别有 90%、99% 样本不超过的耗时）明显高于中位数。

Android 17 的平台边界也很清楚：`ActivityThread.handleBindApplication()` 先安装进程内 Android `ContentProvider`，之后才调用 `Application.onCreate()`。DI 框架无法改变这个顺序。`ContentProvider` 中若访问 DI 容器，可能把 component 创建或 runtime resolution（运行时查找并取得实例）提前到 `Application.onCreate()` 之前。文中的 Android `ContentProvider` 与 Dagger/JSR-330 的 `Provider<T>` 是两种不同概念。

## Dagger/Hilt component 创建到底做了什么

`@HiltAndroidApp` 让 Hilt 生成应用基类和 `SingletonComponent`；启用 Hilt Gradle 插件时，构建过程会让用户 Application 间接继承这个生成基类。Dagger/Hilt 2.60.1 的 `ApplicationGenerator` 生成的核心顺序可简化为下面几行。

```java
@Override
public void onCreate() {
    hiltInternalInject();
    super.onCreate();
}
```

`hiltInternalInject()` 会调用 `generatedComponent()`，再给 Application 做 members injection（给 `@Inject` 字段赋值）。用户 Application 覆盖 `onCreate()` 时应先调用 `super.onCreate()`；Hilt 注入就在这次调用内发生，因此注入字段只能在 `super.onCreate()` 返回后使用。

`ApplicationComponentManager.generatedComponent()` 使用 `volatile` 字段和 double-checked locking（双重检查锁），在第一次访问时调用 component supplier（组件创建函数）。由此可以得到两个结论：

- `SingletonComponent` 是按第一次访问创建的；标准 Hilt Application 会在 `super.onCreate()` 的应用注入阶段触发它。
- component 构造不会把图中所有业务对象都创建一遍。生成组件主要建立 provider、module（提供 binding 的代码单元）和 scope（实例复用范围）关系；某个 binding 何时构造取决于本次注入路径是否请求了它。

不能用“图里有 2,000 个 binding”直接推导启动时创建了 2,000 个对象。应查看 Application、启动阶段 `ContentProvider` 和首个 Activity 的注入字段，以及它们递归依赖的对象。

### Hilt `fastInit` 的边界

Hilt Gradle 插件默认启用 `fastInit`，用更集中式的 provider 生成方式减少 component 初始化时需要加载的类；普通 Dagger component 默认不启用。这个模式不会让重对象自动延迟，也不会删除 binding。

代价是 `fastInit` 下的 `Provider` 会持有整个 component，而默认模式下通常只持有传递依赖的 provider。若短生命周期对象泄漏了一个 `Provider`，前者可能连带保留更大的对象关系。Hilt 2.60 起可以用 Gradle 属性 `-Pdagger.hilt.fastInit=false` 做发布构建对照；不要把它写进 annotation processor 参数，也不要预设关闭后一定更快。官方边界见 [Hilt Fast Init](https://dagger.dev/hilt/flags.html#fast-init)。

## Eager、direct、`Lazy` 与 `Provider`

eager 表示在 component/container 启动阶段主动创建实例；direct injection（直接注入）则表示宿主被注入或构造时就需要拿到目标实例。两者都可能让对象进入启动路径，但触发点不同。

### `@Singleton` 不等于 eager

`@Singleton` 规定同一个 `SingletonComponent` 内共享一个实例。Dagger 通常用 `DoubleCheck` 包装 provider：第一次 `get()` 计算并缓存，后续返回同一个值。component 创建时若没有请求该 binding，`@Singleton` 本身不会让它提前构造。

下面几种写法的时机不同：

| 注入形式 | 何时创建 `T` | 后续行为 |
|---|---|---|
| `@Inject lateinit var value: T` | 宿主对象做成员注入时 | 已持有直接引用 |
| 构造参数 `value: T` | 构造宿主对象之前 | 随宿主一起进入依赖链 |
| `Lazy<T>` | 第一次调用该 `Lazy.get()` | 同一个 `Lazy` 缓存同一个值 |
| `Provider<T>` | 每次 `get()` 时向 Dagger 请求 | unscoped（无 scope）binding 通常每次新建；scoped binding 仍返回 scope 缓存 |
| `@Singleton T` | 第一次被请求时 | 在该 `SingletonComponent` 内复用 |

同一个 `dagger.Lazy<T>` 实例会缓存一次结果，但分别注入的两个 `Lazy<T>` 各自独立；若需要所有调用者共享同一对象，仍应由正确的 scope 保证。

`@Inject lateinit var` 只是由 Hilt 稍后赋值的 Kotlin 字段，不具备“第一次业务使用时再注入”的语义。若 Application 直接注入 `Analytics`，Hilt 会在 Application 注入时构造 `Analytics` 及其递归依赖。

下面的写法把非首帧依赖的构造推迟到业务第一次使用。

```kotlin
@Inject
lateinit var analytics: dagger.Lazy<Analytics>

fun onConsentGranted() {
    analytics.get().start()
}
```

Hilt 在 Application 注入时只提供 `Lazy` wrapper（包装器）；`Analytics` 在 `get()` 时创建并由该 wrapper 缓存。若启动路径仍在首帧前调用 `get()`，这项修改不会减少启动成本。

`UnstableClass` 不是 Dagger/Hilt 的标准延迟机制。需要延迟时应使用 `dagger.Lazy<T>`、`Provider<T>`，或把整个 feature 的入口移出启动路径。

### `@Provides` 也不是自动 eager

`@Provides` 方法在对应 binding 被请求时执行。需要审查的是方法体：网络栈构建、证书读取、数据库打开、磁盘配置解析、native library（原生动态库）加载和线程池创建，都可能把一次 DI lookup（依赖查找）变成重任务。

适合 `@Binds` 的接口到实现映射，不应写成只返回参数的 `@Provides`。这主要减少手写 module 实例与生成路径的复杂度；性能收益仍需用 release 构建验证。

## Hilt 与 `Application.onCreate()` 关键路径

冷启动可按以下边界拆分：

| 边界 | Hilt 可能发生的工作 | 常见问题 |
|---|---|---|
| Android `ContentProvider` 安装 | `ContentProvider` 通过 entry point 访问 `SingletonComponent` | component 被提前创建，重 binding 进入 `ContentProvider` 路径 |
| `super.onCreate()` | 创建 SingletonComponent、注入 Application | Application 直接字段拉起整条依赖链 |
| Application 用户代码 | 调用已经注入的服务 | `Lazy.get()` 被过早调用，延迟形同虚设 |
| 首个 Activity 创建 | ActivityComponent 与成员注入 | 首屏字段过多、构造函数做 I/O |
| 首个 ViewModel 请求 | HiltViewModelFactory、ViewModelComponent、SavedStateHandle | 首屏 ViewModel 构造和 repository 初始化偏重 |

Hilt 不直接支持给 `ContentProvider` 添加 `@AndroidEntryPoint`。`ContentProvider` 若必须访问 binding，可声明显式 `@EntryPoint`；它是从 Hilt 管理范围之外访问指定 binding 的接口，只解决访问方式，不会改变 Android 17 的创建顺序。非必要 `ContentProvider` 应移除或延迟；必须保留的只读取启动所需的轻量 binding。Provider 启动治理见 [21.3 ContentProvider 与多进程启动治理](03-contentprovider-multiprocess-startup.md)。

不要在 `ContentProvider` 中为“稍后会用到”而解析完整网络、数据库或 analytics 图；这会绕过 Application 中的延迟策略。

## HiltViewModel 的成本边界

`@HiltViewModel` 不会随进程无条件创建。首屏调用 `ViewModelProvider` 或 Compose `hiltViewModel()` 时，`HiltViewModelFactory` 才创建对应 `ViewModelComponent` 并解析构造参数。它是否属于启动成本，取决于首屏何时请求。

排查 ViewModel 时要分开测：

- Factory/component 建立与 map lookup；
- ViewModel 构造函数；
- 构造参数中的 repository（数据访问层对象）和 use case（封装业务操作的对象）；
- `init {}` 中启动的同步工作；
- `SavedStateHandle`（ViewModel 的键值状态容器）的读取与反序列化；
- 首次 Flow/LiveData 订阅触发的上游初始化。

把重工作从 Activity 字段移到 ViewModel 构造函数，只是换了调用位置。若首屏同步请求 ViewModel，TTID 路径没有缩短。

## Koin 的运行时成本

本节以 Koin 4.2.2 的 classic DSL（经典 Kotlin 配置语法）为主。它在运行时建立 definition registry（创建规则注册表），并在 `get()`/`inject()` 时按类型、qualifier（同类型 binding 的区分标记）、scope 和运行时参数解析。这个过程不要求每次都走 Java 反射，把“Koin”等同于“反射框架”无法准确描述成本。

Koin 4.2 还提供 Compiler Plugin，可在编译期自动连接构造参数并校验缺失 binding、qualifier 和调用点。它改变的是配置生成与校验边界；`startKoin` 仍会启动 Koin container，运行时的实例获取也仍经过 Koin API。比较框架时要写明是否启用了该插件。

启动成本分成两段：

1. `startKoin { modules(...) }` 创建 `KoinApplication`，注册 `GlobalContext`（供全局 API 查找的 Koin 实例），再载入 module definitions 和配置。
2. 第一次 `get()` 解析 definition 并执行构造 lambda；之后是否缓存由 `single`、`factory`（每次请求创建）、scope 和参数决定。

`single` 默认在首次解析时创建。`createdAtStart = true` 只负责标记 eager singleton；标准 `startKoin` 会在配置注册完后自动调用 `createEagerInstances()`，一次性创建所有带该标记的实例。直接使用 `KoinApplication` 或后续加载 module 时也可以显式控制这一步。优化时应先删除没有业务必要的 `createdAtStart`。

Koin 4.2 的 `lazyModules()` 会用协程在后台载入 module；多个 lazy module 从 4.2.0 起各用一个协程并行加载，默认 dispatcher 是 `Dispatchers.Default`。`waitAllStartJobs()` 会阻塞等待，`awaitAllStartJobs()` 则挂起等待；在主线程调用前者可能把成本重新放回启动关键路径。

同步 module 若依赖尚未载入的 lazy module，解析可能失败，Koin 目前也不会自动校验这种跨边界依赖。适合延迟的是依赖边界清晰且首屏不会访问的 feature，不能机械地把所有 module 移进后台。详细限制见 [Lazy Modules and Background Loading](https://insert-koin.io/docs/reference/koin-core/lazy-modules/)。

Koin 4.2 默认使用不输出内容的 `EmptyLogger`。Release 构建不应显式启用 DEBUG/INFO 级 `AndroidLogger`；开发期日志可定位 resolution，但日志本身会改变时序，不能作为线上或 benchmark 的默认配置。

## Hilt/Dagger 与 Koin 怎样比较

| 维度 | Hilt/Dagger 2.60.1 | Koin 4.2.2 经典 DSL |
|---|---|---|
| 图校验 | 编译期生成并校验依赖关系 | 运行时注册/解析；可另用 `verify` 或 Compiler Plugin 提前发现问题 |
| component/container 启动 | 生成组件，建立 provider 与 scope 缓存 | 载入 module definitions 与 registry |
| binding 解析 | 生成的直接调用/provider 链 | 运行时 key/scope 查找与 definition lambda |
| 重对象时机 | 直接注入时或 `Lazy`/`Provider` 首次请求 | eager definition、首次 `get()` 或 factory 每次请求 |
| 代码体积 | 生成 Factory/Component/Injector 类 | runtime 库与 DSL/definition 对象 |
| 主要可控项 | Application/入口注入面、scope、Lazy、构造函数 | module 加载、createdAtStart、首次 resolution、scope |

这个表用于定位成本，不能代替 benchmark（性能基准）。小型手写 `ServiceLocator`（集中保存和查找服务实例的对象）也可能在静态初始化中 eager 创建全部服务；大型 Hilt 图也可能只在启动时创建少量对象。框架名称无法直接决定结果。

## 生成代码、DEX 与 Startup Profile

Hilt 会为 factory、members injector（成员字段注入器）、component 和 entry point 生成代码，图越大，方法数与 DEX（Android 字节码文件）体积通常越高。R8 会在 release 构建中删除未使用代码并做内联，因此应分析 minified release（经过压缩优化的发布）产物，不能拿 generated source 文件数直接估算线上类加载成本。

“合并 `@Module` 就能减少 component 数量”也是误区。Hilt component 由 `@InstallIn` 目标和 Android 生命周期决定，不由 module 文件数量决定。为了少生成几个源文件而合并 feature 边界，可能降低增量构建与所有权清晰度，却没有可测的启动收益。

Dagger/Hilt 没有 `@Module(isDefault = true)` 这个优化参数。scope 也有生成代码和运行时成本；官方建议只在对象身份或生命周期正确性需要时使用 scope。若只希望允许复用、不要求唯一实例，可以评估 `@Reusable`：Dagger 可以在每个使用该 binding 的 component 中分别缓存，也可以不复用，调用方不能依赖对象身份相同。

Baseline Profile 能让启动用到的 generated code 更早进行 AOT（Ahead-Of-Time，运行前预编译），Startup Profile 能改善这些类在 DEX 中的排列。Profile 不会提前创建 component 或 binding。生成规则时按正常启动 CUJ（Critical User Journey，关键用户路径）覆盖 DI 路径即可，不要写“预热所有 binding”的测试。具体方法见 [21.4 Baseline、Startup 与 Cloud Profile 编译优化](04-baseline-startup-cloud-profile.md) 和 [21.4 Baseline、Startup 与 Cloud Profile 编译优化](04-baseline-startup-cloud-profile.md)。

## KSP 与 KAPT：只把它当构建优化

kapt（Kotlin Annotation Processing Tool）通过生成 Java stub（供处理器读取的占位源码）让 Java annotation processor 处理 Kotlin，stub 生成成本较高。KSP（Kotlin Symbol Processing）直接分析 Kotlin symbol；kapt 已进入维护模式，Android Developers 建议在 processor 支持时迁移，Dagger 也已支持 KSP。

这项迁移的收益主要体现在 clean build（全量构建）、incremental build（增量构建）的时间和构建进程内存。官方所说“最高约两倍”描述的是 symbol processing，不是 App 运行速度。KSP 与 kapt 可能产生不同中间文件；在 DI 图、编译选项和发布产物都等价前，不能把处理器提速换算成冷启动收益。

若项目使用 AGP 9 的 built-in Kotlin（Android Gradle Plugin 内置 Kotlin 支持），`org.jetbrains.kotlin.kapt` 插件不兼容；仍未支持 KSP 的 processor 需要按官方迁移指南放在使用 `com.android.legacy-kapt` 的 Gradle module 中。Data Binding 目前也没有 KSP 迁移计划。这个限制属于构建系统兼容性，与设备运行时的 DI 性能分开评估。

迁移应这样验收：

- 每个 Gradle module 移除全部 kapt processor 后再比较构建时间；只迁一部分仍会生成 stub。
- 对比 clean build、ABI（对其他 module 可见的二进制接口）未变的小改动、跨 module 改动三类场景。
- 检查生成图、qualifier、nullability 和 processor 参数是否一致。
- 运行同一套 DI 测试和 release Macrobenchmark。
- 若 APK/DEX layout 发生变化，把它当独立变量解释，不预设会变快。

## 作用域与内存生命周期

scope 的首要目标是对象身份和生命周期正确性，也就是规定一个实例可复用到何时：

- `@Singleton` 实例一旦创建，通常会由进程级 `SingletonComponent` 持有到进程结束，不能持有 Activity、Fragment、View 或短生命周期 listener；
- 需要 Context 的进程级对象使用 `@ApplicationContext`，不要把 Activity Context 传入 Singleton；
- `@ActivityRetainedScoped` 跨 configuration change（例如旋转屏幕导致的 Activity 重建），不能持有旧 Activity/View；
- `@ActivityScoped`、`@FragmentScoped` 对每个组件实例各有一份，不是全局共享；
- Koin 自定义 scope 必须在 owner（拥有该生命周期的对象）销毁时关闭；动态 module unload 会移除映射并丢弃 Koin 管理的缓存实例，却无法释放仍被业务对象持有的引用。需要关闭文件、线程或连接的对象还应配置 `onClose` 或显式生命周期清理。

过度 scope 会扩大 live set（GC 时仍能访问到的对象集合），也会给 provider 增加缓存与同步路径。取消 scope 后又可能反复创建昂贵对象。选择应由身份语义、构造成本和内存保留共同决定；内存侧的验证见 [23.4 Java Heap、GC 与 Compose 内存分配](../ch23-memory-practice/04-java-heap-gc-compose-allocation.md)。

## 怎样测量 DI 启动成本

给整段 `Application.onCreate()` 打一个 trace section（时间线区间）无法区分 Hilt component、业务初始化和首个 resolution，需要在可控制的边界分别加点。下面示例使用 `android.os.Trace` 把 Hilt Application 注入所在的 `super.onCreate()` 与用户初始化分开。

```kotlin
override fun onCreate() {
    Trace.beginSection("App/HiltSuperOnCreate")
    try {
        super.onCreate()
    } finally {
        Trace.endSection()
    }

    Trace.beginSection("App/UserInitialization")
    try {
        initializeRequiredStartupWork()
    } finally {
        Trace.endSection()
    }
}
```

第一段包含 Hilt component 创建和 Application 成员注入，第二段包含用户显式调用。还应给重 `@Provides`、Koin `startKoin`、首个 `get()`、首屏 ViewModel 构造分别加点，才能定位移动后的成本。

测量口径：

1. 使用 minified、non-debuggable（关闭调试能力）、profileable（允许受控性能分析）的 release 等价构建。
2. 固定设备、Android build、安装来源、compiler filter（ART 实际采用的编译强度）、账号与启动入口。
3. 同时看 TTID（首次显示时间）、TTFD（主要内容完整可用时间）、trace section、自身 CPU 时间、Java allocated bytes 和首帧后首交互。
4. 对 Koin 区分 module registration 与 first resolution；对 Hilt 区分 component/injection 与对象构造。
5. 用 P50/P90/P99 判断；它们分别表示有 50%、90%、99% 样本不超过的耗时，不能用一次本地毫秒数决定框架迁移。

Allocation Recording（对象分配记录）会明显扰动时序，只用于找对象调用栈；Perfetto/Macrobenchmark 才用于启动回归。两类工具的边界见 [21.7 ART GC 抑制与启动性能优化](07-art-gc-suppression-startup-performance.md)。

## 优化顺序

按风险和收益排序：

1. 删除 Application、`ContentProvider` 和首屏入口中不需要的直接注入。
2. 用 `Lazy<T>`/`Provider<T>` 延迟非首帧对象，并确认首帧前没有调用 `get()`。
3. 把 I/O、网络栈、数据库打开和 native library 加载移出 `@Provides`、definition lambda 与构造函数。
4. 清理 Koin `createdAtStart`、同步加载的非必要 module 和 release 详细日志。
5. 重新检查 scope，修复 Singleton/retained 对短生命周期对象的持有。
6. 用 Baseline/Startup Profile 覆盖仍必须位于启动路径的 generated code。
7. 只有在证据显示容器自身仍是主要成本时，才评估局部手写 factory 或 ServiceLocator。

手写替换也要保留相同对象图、生命周期和线程安全再比较。若手写版本通过删除功能、改成全局单例或把错误推迟到运行时获得更快数字，这不是等价实验。

## 排查清单

- Application 直接注入了哪些对象？它们的递归依赖是什么？
- Android `ContentProvider` 是否在 `Application.onCreate()` 前访问 component/container？
- `@Singleton` 是否被误当成 eager，或被直接字段提前拉起？
- `Lazy.get()`/`Provider.get()` 是否仍发生在首帧前？
- `@Provides`、构造函数、Koin definition 是否执行 I/O 或启动线程？
- Koin 是否存在 `createdAtStart`、同步加载的非必要 module 和显式 debug logger？
- 首屏 ViewModel 的成本来自 factory 还是构造参数/`init`？
- scope 是否持有错误 Context、View 或旧 Activity？
- A/B 是否固定 compiler filter 与 Startup Profile？
- KSP 迁移是否只按构建指标验收？

## 参考资料

- [`ActivityThread.handleBindApplication()` Provider/Application 顺序](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [Dependency injection with Hilt](https://developer.android.com/training/dependency-injection/hilt-android)
- [Hilt components](https://dagger.dev/hilt/components.html)
- [`dagger.Lazy`](https://dagger.dev/api/latest/dagger/Lazy.html)
- [`@Reusable`](https://dagger.dev/api/latest/dagger/Reusable.html)
- [Hilt Fast Init](https://dagger.dev/hilt/flags.html#fast-init)
- [Dagger 2.60.1 release](https://github.com/google/dagger/releases/tag/dagger-2.60.1)
- [`ApplicationComponentManager`（2.60.1）](https://github.com/google/dagger/blob/dagger-2.60.1/hilt-android/main/java/dagger/hilt/android/internal/managers/ApplicationComponentManager.java)
- [`ApplicationGenerator`（2.60.1）](https://github.com/google/dagger/blob/dagger-2.60.1/hilt-compiler/main/java/dagger/hilt/android/processor/internal/androidentrypoint/ApplicationGenerator.java)
- [`ApplicationComponentManager`](https://github.com/google/dagger/blob/master/hilt-android/main/java/dagger/hilt/android/internal/managers/ApplicationComponentManager.java)
- [`ApplicationGenerator`](https://github.com/google/dagger/blob/master/hilt-compiler/main/java/dagger/hilt/android/processor/internal/androidentrypoint/ApplicationGenerator.java)
- [Migrate from kapt to KSP](https://developer.android.com/build/migrate-to-ksp)
- [AGP 9: KSP, kapt, and legacy-kapt](https://developer.android.com/agents/skills/build-system/agp/agp-9-upgrade/references/ksp-kapt)
- [Starting Koin](https://insert-koin.io/docs/reference/koin-core/starting-koin/)
- [Koin modules](https://insert-koin.io/docs/reference/koin-core/modules/)
- [Koin definitions](https://insert-koin.io/docs/reference/koin-core/definitions/)
- [Koin lazy modules](https://insert-koin.io/docs/reference/koin-core/lazy-modules/)
