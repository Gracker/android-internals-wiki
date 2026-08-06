---
title: "Android 17 Modular Startup Framework Dependency Graph"
chapter: "21.20"
status: "finalized"
task6_state: "reviewed"
task9_state: "reviewed"
pipeline_stage: "finalized"
applicable_versions: "Android 17 (API 37)"
tags: ["android17", "ch08", "performance", "optimization", "app-startup", "androidx"]
related_chapters: ["8.02", "8.37"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-08"
gap_source: "AOSP结构"
last_verified: "2026-07-30"
last_verified_against: "AOSP android-17.0.0_r1 + AndroidX App Startup 1.2.0"
last_draft_polish_at: "2026-07-30T15:35:43+08:00"
last_draft_polish_run_id: "20260730-153543-draft-polish-bf92af44"
confidence: "medium-high"
reviewed_date: "2026-07-30"
reviewed_by: "hermes-aiw-review-finalize-apply"
last_review_finalize_at: "2026-07-30T16:06:42+08:00"
last_review_finalize_run_id: "20260730-160642-907d4a28"
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java"
    tag: "android-17.0.0_r1"
    url: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/LoadedApk.java"
    tag: "android-17.0.0_r1"
  - type: jetpack
    path: "androidx/startup/AppInitializer.java"
    version: "1.2.0"
    url: "https://android.googlesource.com/platform/frameworks/support/+/2bbbb9ffed2413b31a95f0fa838532db5b541e2e/startup/startup-runtime/src/main/java/androidx/startup/AppInitializer.java"
  - type: jetpack
    path: "androidx/startup/InitializationProvider.java"
    version: "1.2.0"
    url: "https://android.googlesource.com/platform/frameworks/support/+/2bbbb9ffed2413b31a95f0fa838532db5b541e2e/startup/startup-runtime/src/main/java/androidx/startup/InitializationProvider.java"
  - type: jetpack
    path: "androidx/startup/Initializer.java"
    version: "1.2.0"
    url: "https://android.googlesource.com/platform/frameworks/support/+/2bbbb9ffed2413b31a95f0fa838532db5b541e2e/startup/startup-runtime/src/main/java/androidx/startup/Initializer.java"
  - type: official
    path: "https://developer.android.com/topic/libraries/app-startup"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/startup"
---

# 21.20 Android 17 应用启动边界与 AndroidX App Startup 依赖图

## 1. 先划清版本和组件边界

本章的平台源码基线是 Android 17 / API 37 / `android-17.0.0_r1`，应用启动依赖管理以 AndroidX App Startup 1.2.0 为基线。

这两个版本号描述的是不同层次：

- Android 17 决定应用进程如何进入 `ActivityThread.handleBindApplication()`，以及 `Application`、`ContentProvider` 的创建顺序。
- AndroidX App Startup 是随应用打包的独立 Jetpack 库。1.2.0 的 `minSdk` 是 21，它不是 Android 17 新增的平台服务，也不是 AOSP 中名为 “Modular Startup Framework” 的系统模块。

因此，本章所说的“依赖图”只负责组织当前应用进程中的 `Initializer`。它不会调度 SystemServer 服务，不会改变 `init` 的启动顺序，也不会自动管理所有第三方 SDK。

## 2. Android 17 平台先建立了什么顺序

> 源码参照：`frameworks/base/core/java/android/app/ActivityThread.java` (`android-17.0.0_r1`)，`handleBindApplication()` 与 `installContentProviders()` 主路径。

Android 17 的 `ActivityThread.handleBindApplication()` 主路径可以压缩成下面四步：

1. `LoadedApk.makeApplicationInner()` 创建并绑定 `Application` 对象，但此时还没有调用 `Application.onCreate()`。
2. `installContentProviders(app, data.providers)` 安装分配给当前进程的 Provider。
3. 安装每个本地 Provider 时，框架会创建实例并调用其 `onCreate()`。
4. Provider 安装完成后，`Instrumentation.callApplicationOnCreate(app)` 才进入应用的 `Application.onCreate()`。

由此可以得到一个可靠的时序：

```text
创建 Application 对象
    ↓
安装当前进程的 ContentProvider
    ↓
InitializationProvider.onCreate()
    ↓
执行被发现的 Initializer.create()
    ↓
Application.onCreate()
    ↓
创建首个 Activity
```

这段时序用于定位 App Startup 在平台启动路径中的位置。它说明 `Initializer.create()` 属于 `Application.onCreate()` 之前的同步启动成本，但不代表不同 Provider 之间可以通过声明顺序建立业务依赖。

`ActivityThread.installContentProviders()` 会逐个安装 Provider，把得到的 `ContentProviderHolder` 放进列表，汇总后用一次 `IActivityManager.publishContentProviders()` 将该列表发布给 system_server。因而，“N 个 Provider 必然对应 N 次 `publishContentProviders` Binder 调用”不符合 Android 17 源码。合并 Provider 仍能减少组件实例、类加载和各 Provider `onCreate()` 的固定开销，只是不能把收益错误归因于 N 次发布调用变成一次。

## 3. App Startup 如何发现初始化器

> 源码参照：`androidx/startup/InitializationProvider.java` 与 `androidx/startup/AppInitializer.java`（App Startup 1.2.0，commit `2bbbb9f`）。

App Startup 1.2.0 的 AAR 会通过 manifest 合并加入一个未导出的 Provider：

```xml
<provider
    android:name="androidx.startup.InitializationProvider"
    android:authorities="${applicationId}.androidx-startup"
    android:exported="false"
    tools:node="merge" />
```

这段 manifest 用于说明库的默认入口。它没有声明 `android:process`，所以默认只会在应用默认进程创建，不会自动进入每一个命名进程。

各库或应用再把初始化器类名写成该 Provider 的 `<meta-data>` key，value 必须是资源 `androidx.startup` 对应的标记值。`InitializationProvider.onCreate()` 会取得 application context，然后把自己的实际 Provider 类传给 `AppInitializer.discoverAndInitialize()`。

1.2.0 的发现过程包含以下动作：

1. 根据当前 `InitializationProvider` 的具体类名读取 `ProviderInfo.metaData`。
2. 遍历 metadata，只接受 value 等于 `androidx.startup` 标记的条目。
3. 对 key 执行 `Class.forName()`。
4. 仅收集实现了 `Initializer` 的类。
5. 发现全部入口后，再逐个进入依赖初始化。

“先完成发现，再执行初始化”很重要。`AppInitializer.isEagerlyInitialized()` 查询的是某个初始化器是否来自 manifest 的主动发现集合，而不是它是否已经在任意路径上创建过。

## 4. 依赖图的执行语义

`Initializer<T>` 只有两个需要实现的方法：

- `dependencies()` 返回必须先完成的其他 `Initializer` 类型。
- `create(context)` 执行当前组件的初始化，并返回可缓存的结果。

下面的示例用于表达一个最小依赖关系：日志设施先就绪，网络组件随后读取日志能力。

```kotlin
class LoggingInitializer : Initializer<Logger> {
    override fun create(context: Context): Logger {
        return Logger.install(context)
    }

    override fun dependencies(): List<Class<out Initializer<*>>> = emptyList()
}

class NetworkInitializer : Initializer<ApiClient> {
    override fun create(context: Context): ApiClient {
        return ApiClient.create(context)
    }

    override fun dependencies(): List<Class<out Initializer<*>>> {
        return listOf(LoggingInitializer::class.java)
    }
}
```

当 `NetworkInitializer` 被发现时，App Startup 会先执行 `LoggingInitializer.create()`，再执行 `NetworkInitializer.create()`。这段代码只声明先后关系，不会创建后台线程；两个 `create()` 默认都在 Provider 创建所在的主线程同步运行。

源码中的核心算法是深度优先遍历（`AppInitializer.initializeComponent()` 递归路径，`mInitialized` 缓存表，`initializing` 集合做环检测）：

- 进入一个节点时，把它放进当前递归路径的 `initializing` 集合。
- 先递归执行 `dependencies()` 返回的节点。
- 依赖完成后调用当前节点的 `create()`。
- 将返回值放进 `mInitialized`，同一进程后续请求直接复用。
- 如果递归路径再次遇到同一类，抛出包含 “Cycle detected” 的异常，并由 `StartupException` 包装。

这能保证依赖先于使用方初始化，也能阻止 `A → B → A` 这样的环。它不保证同一层无依赖节点的稳定顺序；metadata 和 `HashSet` 的遍历顺序都不应被当作接口。需要先后关系时，应在 `dependencies()` 中明确声明。

`AppInitializer` 的单例和缓存都是进程内静态状态。“只初始化一次”的准确含义是：一个进程内的同一个 `AppInitializer` 实例只缓存一次该初始化器结果，而不是整个应用包跨进程只执行一次。

## 5. 主线程成本：依赖声明不会让工作并行

App Startup 解决的是初始化入口分散和依赖顺序不透明的问题，不是主线程调度器。`InitializationProvider.onCreate()`、依赖遍历和 `Initializer.create()` 都位于启动主线程路径中，而且 `AppInitializer` 还会用进程内锁保护初始化和缓存。

适合主动初始化的工作通常同时满足这些条件：

- 首屏或首个关键业务入口在使用前必须完成。
- 工作量小，耗时边界可测。
- 不依赖尚未创建的 Activity、窗口或用户交互。
- 失败策略明确，不会把可降级能力变成进程启动失败。

下面这些操作要格外谨慎：

- 同步网络请求；
- 大文件读取、数据库迁移或全表扫描；
- 大量反射、Dex 类加载或原生库加载；
- 等待锁、Binder 服务或其他线程结果；
- 与首屏无关的统计、预热和低频功能准备。

把耗时工作从 `Application.onCreate()` 搬进 `Initializer.create()`，只是把它提前到了更早的 Provider 阶段，冷启动耗时不会自动减少。评审时应先回答“首个消费者何时需要结果”，再决定主动初始化、延迟初始化或拆分轻重阶段。

## 6. 主动发现与手动初始化

如果某个组件不需要在 `Application.onCreate()` 之前就绪，可以从默认 Provider 的 metadata 中移除它，并在首个可靠使用点手动初始化。

下面的 manifest 片段用于关闭某个库初始化器的自动发现。`tools:node="remove"` 的匹配目标必须与最终合并 manifest 中的 key 完全一致。

```xml
<provider
    android:name="androidx.startup.InitializationProvider"
    android:authorities="${applicationId}.androidx-startup"
    tools:node="merge">

    <meta-data
        android:name="com.example.analytics.AnalyticsInitializer"
        tools:node="remove" />
</provider>
```

移除 metadata 后，默认 Provider 不会主动发现这个初始化器。应在 Android Studio 的 Merged Manifest 视图或构建产物中确认规则已经生效，避免只检查当前模块的源 manifest。

关闭一个组件的自动初始化，也会关闭只经该组件依赖边到达的初始化器；若同一个依赖还出现在其他自动发现入口的 `dependencies()` 中，或它自己的 metadata 仍被保留，它仍会从那条路径执行。判断结果时要检查完整依赖图，不能只检查被移除的 metadata。

下面的调用用于在首个业务消费者之前同步完成该组件初始化：

```kotlin
val analytics = AppInitializer.getInstance(context)
    .initializeComponent(AnalyticsInitializer::class.java)
```

`initializeComponent()` 仍然是同步调用，并继续遵守该节点的 `dependencies()`。它会把成本移动到调用线程和调用时刻，不会把工作自动转为异步；若首个调用发生在点击处理的主线程，卡顿也会移动到那次点击。

如果初始化器需要异步准备，可以让 `create()` 只建立轻量对象和线程安全状态，再由组件自己的异步 API 执行耗时工作。此时必须定义“未准备完成时”的调用行为，不能只启动一个后台任务就假定所有消费者已可用。

## 7. 多进程不是默认覆盖

AndroidX App Startup 1.2.0 的默认 Provider 没有 `android:process`，所以它只属于默认进程。一个声明为 `android:process=":worker"` 的 Service 启动新进程时，不会因为主进程已经执行过 App Startup 就继承初始化结果；两个进程拥有不同的虚拟机、静态字段和 `mInitialized` 缓存。

App Startup 从 1.1.0 开始支持为多个进程配置多个 `InitializationProvider`。常见做法是：

1. 为目标进程定义一个 `InitializationProvider` 子类。
2. 在 manifest 中为它声明不同的 authority 和 `android:process`。
3. 把该进程需要的 metadata 放在这个 Provider 节点下。
4. 确保初始化器可以在目标进程重复执行，或者自行采用 IPC、文件锁、数据库事务等跨进程协调手段。

下面的声明用于展示一个独立的 `:worker` 进程入口。子类可以保持空实现，因为 `InitializationProvider.onCreate()` 会按运行时类读取对应 Provider 的 metadata。

```kotlin
class WorkerInitializationProvider : InitializationProvider()
```

这个子类提供了可单独寻址的 Provider 组件名，自身不需要重写 `onCreate()`。接下来用 manifest 把它放进目标进程，并只挂载该进程需要的初始化器：

```xml
<provider
    android:name=".WorkerInitializationProvider"
    android:authorities="${applicationId}.androidx-startup.worker"
    android:exported="false"
    android:process=":worker">

    <meta-data
        android:name="com.example.worker.WorkerInitializer"
        android:value="androidx.startup" />
</provider>
```

这组代码会在 `:worker` 进程创建该 Provider 时发现 `WorkerInitializer`。不同 authority 避免 Provider 冲突；不同 Provider 类让 1.2.0 能读取正确的 metadata。两个进程仍然各自执行自己的依赖图，App Startup 不提供跨进程拓扑排序或完成通知。

1.2.0 修复了 Provider 位于次进程时的 metadata 查询问题。若项目依赖旧版并采用多进程配置，应先升级并回归各进程入口，不要通过复制默认 Provider 配置来绕过版本问题。

## 8. 动态特性模块与类加载边界

manifest 主动发现会直接对 metadata key 执行 `Class.forName()`。Provider 运行时，声明的初始化器类必须已经可以由当前进程的 ClassLoader 加载。

如果 metadata 指向尚未安装的动态特性模块，类查找会失败并被包装成 `StartupException`，进程可能在进入 `Application.onCreate()` 前就终止。稳妥的设计是把入口桥接类放在 base 模块，或在动态特性安装完成后从可确认的业务入口手动调用初始化。具体选择需要结合拆包方式、按需安装状态和目标进程验证，不能假定 ClassLoader 会忽略缺失类。

同理，“类已经被 ClassLoader 缓存”不能等价为零成本。每个进程仍可能产生类解析、校验、静态初始化和首次代码执行成本，应以目标设备的启动测量为准。

## 9. 如何观察依赖图是否拖慢启动

> 源码参照：`androidx/startup/AppInitializer.java` 1.2.0 `beginStartupSection()` / `endStartupSection()` 调用，trace section 名为 `Startup` 与各初始化器简单类名。

App Startup 1.2.0 通过 AndroidX Tracing 创建 `Startup` trace section，并用每个初始化器的简单类名创建子 section。抓取冷启动 Perfetto trace 后，可以直接检查这些 section 在主线程上的位置和持续时间。

一次有价值的排查应同时完成以下检查：

1. 查看 Merged Manifest，列出最终挂在每个 `InitializationProvider` 下的 metadata。
2. 确认默认进程和命名进程分别创建了哪些 Provider。
3. 在 Perfetto 中定位 `Startup` 和具体初始化器 section，检查磁盘 I/O、Binder 等待、锁等待和类加载。
4. 用 Macrobenchmark 的启动指标比较修改前后，覆盖冷启动并保持设备、构建类型、编译模式和测试入口一致。
5. 在调试构建中配合 StrictMode 找到不该出现在主线程的磁盘与网络访问。
6. 对手动初始化路径补充首个消费者的耗时和并发测试，避免只优化启动数字却把延迟转移到第一次交互。

`isEagerlyInitialized(SomeInitializer::class.java)` 可用于测试某个初始化器是否由 manifest 主动发现。它不应成为生产代码里的业务分支，因为它描述的是发现方式，不是组件完整的健康状态。

## 10. 常见误区与修正

| 误区 | Android 17 / App Startup 1.2.0 下的结论 |
|---|---|
| Android 17 新增了系统级 Modular Startup Framework | 没有这个平台 API；本章讨论的是独立发布的 AndroidX App Startup |
| 声明顺序就是 Provider 或初始化器顺序 | Provider 顺序不适合表达业务依赖；初始化器顺序应由 `dependencies()` 明确描述 |
| App Startup 会并行执行无依赖节点 | 1.2.0 的发现、深度优先遍历和 `create()` 都是同步执行 |
| 每个 Provider 都会单独调用一次 `publishContentProviders` | Android 17 会先收集当前批次的 holder，再用一次调用发布列表 |
| 默认 Provider 会在所有应用进程运行 | 默认配置没有 `android:process`，只属于默认进程 |
| 初始化器在整个应用包只运行一次 | 缓存只在当前进程内有效，多进程会各自执行 |
| 改成手动初始化就没有成本 | 成本移动到手动调用的位置，调用本身仍是同步的 |
| 依赖图可以自动解决动态特性类缺失 | 主动发现使用 `Class.forName()`，类不可用会导致失败 |

## 11. 评审清单

接入或审查 App Startup 时，可以依次回答这些问题：

- 当前使用的 AndroidX Startup 版本是什么，是否需要多进程修复？
- 最终合并 manifest 中有哪些入口初始化器？
- 每个入口属于哪个进程？
- `dependencies()` 是否完整，是否存在环或隐含顺序？
- 每个 `create()` 的主线程耗时、I/O、Binder 和锁等待是多少？
- 哪些结果必须在 `Application.onCreate()` 前可用？
- 延迟初始化后的首个消费者是否能处理并发、失败和未就绪状态？
- 初始化器类在 base、动态特性和目标进程的 ClassLoader 中是否可用？
- 修改是否经过冷启动 Macrobenchmark 和 Perfetto 前后对比？

## 12. 小结

Android 17 平台为 App Startup 提供的是一个明确的 Provider 启动窗口：`Application` 对象创建之后、`Application.onCreate()` 之前。AndroidX App Startup 1.2.0 在这个窗口中发现 `Initializer`，用进程内深度优先遍历处理依赖、检测环并缓存结果。

它适合管理少量、必要且可测的前置初始化。它不会并行执行任务，不会建立跨进程依赖，也不会消除初始化本身的时间。优化工作的重点应放在最终 manifest、每个进程的入口、主线程 trace 和首个消费者的真实约束上。

## 参考资料

- [Android 17 `ActivityThread.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [AndroidX App Startup 使用指南](https://developer.android.com/topic/libraries/app-startup)
- [AndroidX Startup 版本说明](https://developer.android.com/jetpack/androidx/releases/startup)
- [AndroidX App Startup 1.2.0 `AppInitializer.java`](https://android.googlesource.com/platform/frameworks/support/+/2bbbb9ffed2413b31a95f0fa838532db5b541e2e/startup/startup-runtime/src/main/java/androidx/startup/AppInitializer.java)
- [AndroidX App Startup 1.2.0 `InitializationProvider.java`](https://android.googlesource.com/platform/frameworks/support/+/2bbbb9ffed2413b31a95f0fa838532db5b541e2e/startup/startup-runtime/src/main/java/androidx/startup/InitializationProvider.java)
- [AndroidX App Startup 1.2.0 `Initializer.java`](https://android.googlesource.com/platform/frameworks/support/+/2bbbb9ffed2413b31a95f0fa838532db5b541e2e/startup/startup-runtime/src/main/java/androidx/startup/Initializer.java)
