---
title: "依赖注入框架性能：Dagger/Hilt/Koin 启动开销与优化"
chapter: "21.12"
section: "21.12"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [dependency-injection, dagger, hilt, koin, startup, ksp, kapt]
related_chapters: ["21.1", "21.2", "21.3", "21.6", "8.2", "1.9"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-24"
gap_source: "AOSP结构+社区高频痛点"
drafted_date: "2026-06-24"
last_verified: "2026-06-24"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/app/Application.java"
  - type: aosp
    path: "frameworks/base/core/java/dagger/hilt/android/HiltApplication.java"
  - type: official
    path: "https://dagger.dev/hilt"
---

# 依赖注入框架性能：Dagger/Hilt/Koin 启动开销与优化

依赖注入的启动成本不能用“框架有多重”概括。一次注入至少包含四类工作：创建容器/组件、建立 provider 字段、解析 binding、执行对象构造与初始化。Dagger/Hilt 把解析关系生成成 Java 代码；Koin 在运行时注册和查询 definition。两者的主要成本位置不同，但重对象的构造函数、`@Provides` 或 definition lambda 才常是启动长尾。

Android 17 的平台边界也很清楚：`ActivityThread.handleBindApplication()` 先安装进程内 `ContentProvider`，之后才调用 `Application.onCreate()`。DI 框架无法改变这个顺序。任何 Provider 中的容器访问，都可能把 component 创建或 runtime resolution 提前到 `Application.onCreate()` 之前。

## Dagger/Hilt component 创建到底做了什么

`@HiltAndroidApp` 让 Hilt 生成应用基类和 `SingletonComponent`。上游 `ApplicationGenerator` 生成的核心顺序可以简化为下面几行。

```java
@Override
public void onCreate() {
    hiltInternalInject();
    super.onCreate();
}
```

`hiltInternalInject()` 会调用 `generatedComponent()` 并给 Application 做成员注入。用户 Application 覆盖 `onCreate()` 时，通常先调用 `super.onCreate()`；Hilt 注入就在这次调用内发生，所以注入字段只应在 `super.onCreate()` 返回后使用。

`ApplicationComponentManager.generatedComponent()` 使用 volatile 字段和双重检查，在第一次访问时调用 component supplier。由此得到两个结论：

- `SingletonComponent` 是按第一次访问创建的；标准 Hilt Application 会在 `super.onCreate()` 的应用注入阶段触发它。
- component 构造不等于把图中所有对象都创建一遍。生成组件主要建立 provider、module 和 scope 缓存关系；某个 binding 何时构造取决于它是否在本次注入路径上被请求。

因此，不能用“图里有 2,000 个 binding”直接推导启动时创建 2,000 个对象。应查看 Application 的注入字段、启动 Provider/Activity 的注入字段，以及它们递归依赖的对象。

## Eager、direct、`Lazy` 与 `Provider`

### `@Singleton` 不等于 eager

`@Singleton` 规定同一个 `SingletonComponent` 内共享一个实例。Dagger 通常用 `DoubleCheck` 包装 provider：第一次 `get()` 计算并缓存，后续返回同一个值。组件创建时没有请求该 binding，就不会因为它带 `@Singleton` 自动构造。

下面几种写法的时机不同：

| 注入形式 | 何时创建 `T` | 后续行为 |
|---|---|---|
| `@Inject lateinit var value: T` | 宿主对象做成员注入时 | 已持有直接引用 |
| 构造参数 `value: T` | 构造宿主对象之前 | 随宿主一起进入依赖链 |
| `Lazy<T>` | 第一次调用该 `Lazy.get()` | 同一个 `Lazy` 缓存同一个值 |
| `Provider<T>` | 每次 `get()` 时请求 | unscoped binding 通常每次新建；scoped binding 仍返回 scope 缓存 |
| `@Singleton T` | 第一次被请求时 | 在该 `SingletonComponent` 内复用 |

`@Inject lateinit var` 只是 Kotlin 的延后赋值字段，**不是延迟注入**。若 Application 直接注入 `Analytics`，Hilt 会在 Application 注入时构造 `Analytics` 及其直接依赖。

下面的写法把非首帧依赖的构造推迟到业务第一次使用。

```kotlin
@Inject
lateinit var analytics: dagger.Lazy<Analytics>

fun onConsentGranted() {
    analytics.get().start()
}
```

Hilt 在 Application 注入时只提供 `Lazy` wrapper；`Analytics` 在 `get()` 时创建并由该 wrapper 缓存。若启动路径仍在首帧前调用 `get()`，这项修改不会减少启动成本。

`UnstableClass` 不是 Dagger/Hilt 的标准延迟机制。需要延迟时应使用 `dagger.Lazy<T>`、`Provider<T>`，或把整个 feature 的入口移出启动路径。

### `@Provides` 也不是自动 eager

`@Provides` 方法在对应 binding 被请求时执行。需要重点审查的是方法体：网络栈构建、证书读取、数据库打开、磁盘配置解析、native library 加载和线程池创建都可能把 DI lookup 变成重任务。

适合 `@Binds` 的接口映射不应写成只返回参数的 `@Provides`。这主要减少手写 module 实例与生成路径的复杂度；性能收益仍需用 release 构建验证。

## Hilt 与 `Application.onCreate()` 关键路径

冷启动可按以下边界拆分：

| 边界 | Hilt 可能发生的工作 | 常见问题 |
|---|---|---|
| Provider 安装 | Provider 自己通过 entry point 访问 SingletonComponent | component 被提前创建，重 binding 进入 Provider 路径 |
| `super.onCreate()` | 创建 SingletonComponent、注入 Application | Application 直接字段拉起整条依赖链 |
| Application 用户代码 | 调用已经注入的服务 | `Lazy.get()` 被过早调用，延迟形同虚设 |
| 首个 Activity 创建 | ActivityComponent 与成员注入 | 首屏字段过多、构造函数做 I/O |
| 首个 ViewModel 请求 | HiltViewModelFactory、ViewModelComponent、SavedStateHandle | 首屏 ViewModel 构造和 repository 初始化偏重 |

Hilt 不直接支持给 `ContentProvider` 添加 `@AndroidEntryPoint`。Provider 若必须访问 binding，可使用显式 entry point，但这只是访问方式，不会改变 Android 17 的创建顺序。非必要 Provider 应移除或延迟；必须保留的 Provider 只读取启动所需的轻量 binding。

同理，不要在一个 Provider 中为“稍后会用到”而解析完整网络、数据库或 analytics 图。这个动作会绕过 Application 中所有延迟策略。

## HiltViewModel 的成本边界

`@HiltViewModel` 不会随进程无条件创建。首屏调用 `ViewModelProvider`/Compose `hiltViewModel()` 时，HiltViewModelFactory 才创建对应 ViewModelComponent 并解析构造参数。它是否属于启动成本，取决于首屏何时请求。

排查 ViewModel 时要分开测：

- Factory/component 建立与 map lookup；
- ViewModel 构造函数；
- 构造参数中的 repository/use case；
- `init {}` 中启动的同步工作；
- `SavedStateHandle` 的读取与反序列化；
- 首次 Flow/LiveData 订阅触发的上游初始化。

把重工作从 Activity 字段移到 ViewModel 构造函数，只是换了调用位置。若首屏同步请求 ViewModel，TTID 路径没有缩短。

## Koin 的运行时成本

Koin 的经典 DSL 在运行时建立 definition registry，并在 `get()`/`inject()` 时按类型、qualifier、scope 和参数解析。它不要求通过 Java 反射完成每次解析；“Koin = 反射”不是准确的性能描述。

启动成本分成两段：

1. `startKoin { modules(...) }` 创建 KoinApplication、注册 GlobalContext、读取 module definitions 和配置。
2. 第一次 `get()` 解析 definition 并执行构造 lambda；之后是否缓存由 `single`、`factory`、scope 和参数决定。

`single` 默认按首次解析创建。显式 `createdAtStart` 或调用 `createEagerInstances()` 才会在启动阶段创建 eager singleton。优化时应先删除没有业务必要的 eager 标记。

Koin 当前提供 `lazyModules()` 后台加载能力，但不能机械地把所有 feature module 移进去。立即加载的 module 若依赖尚未完成加载的 lazy module，会产生时序问题；Koin 文档也提示启动阶段不要混用存在这种依赖的 module。适合延迟的是依赖边界清晰、首屏不访问的 feature。

Release 构建应关闭详细 Koin 日志。开发期 tracing 可以定位 resolution，但日志本身会影响时序，不应作为线上或 benchmark 的默认配置。

## Hilt/Dagger 与 Koin 怎样比较

| 维度 | Hilt/Dagger | Koin 经典 DSL |
|---|---|---|
| 图校验 | 编译期生成并校验大部分依赖关系 | 运行时注册/解析；可另用 verify 或编译插件 |
| component/container 启动 | 生成组件，建立 provider 与 scope 缓存 | 载入 module definitions 与 registry |
| binding 解析 | 生成的直接调用/provider 链 | 运行时 key/scope 查找与 definition lambda |
| 重对象时机 | 直接注入时或 `Lazy`/`Provider` 首次请求 | eager definition、首次 `get()` 或 factory 每次请求 |
| 代码体积 | 生成 Factory/Component/Injector 类 | runtime 库与 DSL/definition 对象 |
| 主要可控项 | Application/入口注入面、scope、Lazy、构造函数 | module 加载、createdAtStart、首次 resolution、scope |

这个表只能帮助定位成本，不能代替 benchmark。小型手写 ServiceLocator 也可能在静态初始化中 eager 创建全部服务；大型 Hilt 图也可能只在启动时创建少量对象。框架名称不能决定结果。

## 生成代码、DEX 与 Startup Profile

Hilt 会为 factory、members injector、component 和 entry point 生成代码，图越大，方法数与 DEX 体积通常越高。R8 会移除未使用代码并做内联，所以应分析 minified release 产物，不能拿 generated source 文件数直接估算线上类加载成本。

“合并 `@Module` 就能减少 component 数量”也是误区。Hilt component 由 `@InstallIn` 目标和 Android 生命周期决定，不由 module 文件数量决定。为了少生成几个源文件而合并 feature 边界，可能降低增量构建与所有权清晰度，却没有可测的启动收益。

Dagger/Hilt 没有 `@Module(isDefault = true)` 这个优化参数。scope 也有生成代码和运行时成本；官方建议只在对象身份/生命周期正确性需要时使用 scope。若只是希望允许复用但不要求唯一实例，可以评估 `@Reusable`，并确认其“不保证每次复用”的语义符合业务。

Baseline Profile 能让启动用到的 generated code 更早 AOT 编译，Startup Profile 能改善这些类的 DEX 布局。Profile 不会提前创建 component 或 binding。生成规则时按正常启动 CUJ 覆盖 DI 路径即可，不要写“预热所有 binding”的测试。

## KSP 与 KAPT：只把它当构建优化

kapt 通过生成 Java stub 让 Java annotation processor 读取 Kotlin，stub 生成成本较高。KSP 直接分析 Kotlin symbol，官方建议在 processor 支持时迁移；Dagger 已支持 KSP。

这项迁移的主要收益是 clean/incremental build 时间和内存。KSP 与 kapt 可能产生不完全相同的中间文件，但它们实现相同的 DI 语义，没有依据把“KSP 最多快两倍的处理速度”换算成 App 冷启动收益。

迁移应这样验收：

- 每个 module 移除全部 kapt processor 后再比较构建时间；只迁一部分仍会生成 stub。
- 对比 clean build、ABI 未变的小改动、跨 module 改动三类场景。
- 检查生成图、qualifier、nullability 和 processor 参数是否一致。
- 运行同一套 DI 测试和 release Macrobenchmark。
- 若 APK/DEX layout 发生变化，把它当独立变量解释，不预设会变快。

## 作用域与内存生命周期

scope 的首要目标是对象身份和生命周期正确性：

- `@Singleton` 活到进程结束，不能持有 Activity、Fragment、View 或短生命周期 listener；
- 需要 Context 的进程级对象使用 `@ApplicationContext`，不要把 Activity Context 传入 Singleton；
- `@ActivityRetainedScoped` 跨 configuration change，不能持有旧 Activity/View；
- `@ActivityScoped`、`@FragmentScoped` 对每个组件实例各有一份，不是全局共享；
- Koin 自定义 scope 必须在 owner 销毁时关闭，动态 module unload 不能代替释放仍被业务对象持有的引用。

过度 scope 会扩大 live set，也会给 provider 增加缓存与同步路径。取消 scope 后又可能反复创建昂贵对象。选择应由身份语义、构造成本和内存保留共同决定。

## 怎样测量 DI 启动成本

给整段 `Application.onCreate()` 打一个点，无法区分 Hilt component、业务初始化和首个 resolution。需要在可控制的边界分别加 trace。

下面的示例把 Hilt Application 注入所在的 `super.onCreate()` 与用户初始化分开。

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

1. 使用 minified、non-debuggable、profileable 的 release 等价构建。
2. 固定设备、Android build、安装来源、compiler filter、账号与启动入口。
3. 同时看 TTID/TTFD、trace section、自身 CPU 时间、Java allocated bytes 和首帧后首交互。
4. 对 Koin 区分 module registration 与 first resolution；对 Hilt 区分 component/injection 与对象构造。
5. 用 P50/P90/P99 判断，不能用一次本地毫秒数决定框架迁移。

Allocation Recording 会显著扰动时序，只用于找对象调用栈；Perfetto/Macrobenchmark 才用于启动回归。

## 优化顺序

按风险和收益排序：

1. 删除 Application、Provider 和首屏入口中不需要的直接注入。
2. 用 `Lazy<T>`/`Provider<T>` 延迟非首帧对象，并确认首帧前没有调用 `get()`。
3. 把 I/O、网络栈、数据库打开和 native library 加载移出 provider/构造函数。
4. 清理 Koin `createdAtStart`、全量 module 加载和 release 详细日志。
5. 重新检查 scope，修复 Singleton/retained 对短生命周期对象的持有。
6. 用 Baseline/Startup Profile 覆盖仍必须位于启动路径的 generated code。
7. 只有在证据显示容器自身仍是主要成本时，才评估局部手写 factory 或 ServiceLocator。

手写替换也要保留相同对象图、生命周期和线程安全再比较。若手写版本通过删除功能、改成全局单例或把错误推迟到运行时获得更快数字，这不是等价实验。

## 排查清单

- Application 直接注入了哪些对象？它们的递归依赖是什么？
- Provider 是否在 `Application.onCreate()` 前访问 component/container？
- `@Singleton` 是否被误当成 eager，或被直接字段提前拉起？
- `Lazy.get()`/`Provider.get()` 是否仍发生在首帧前？
- `@Provides`、构造函数、Koin definition 是否执行 I/O 或启动线程？
- Koin 是否存在 `createdAtStart`、全量 module 和 debug logger？
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
- [`ApplicationComponentManager`](https://github.com/google/dagger/blob/master/hilt-android/main/java/dagger/hilt/android/internal/managers/ApplicationComponentManager.java)
- [`ApplicationGenerator`](https://github.com/google/dagger/blob/master/hilt-compiler/main/java/dagger/hilt/android/processor/internal/androidentrypoint/ApplicationGenerator.java)
- [Migrate from kapt to KSP](https://developer.android.com/build/migrate-to-ksp)
- [Starting Koin](https://insert-koin.io/docs/reference/koin-core/starting-koin/)
- [Koin modules](https://insert-koin.io/docs/reference/koin-core/modules/)
