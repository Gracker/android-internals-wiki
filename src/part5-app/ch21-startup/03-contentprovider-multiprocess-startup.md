---
title: ContentProvider 与多进程启动治理
chapter: '21.3'
section: '21.3'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-08-14'
last_verified_against: AOSP android-17.0.0_r1 ActivityThread/ContentProvider/ContentProviderRecord/ViewTreeObserver, current Android Developers provider/Direct Boot/manifest docs, AndroidX Startup 1.2.0 latest stable source
confidence: medium-high
sources:
- type: aosp
  path: AOSP android-17.0.0_r1 frameworks/base/core/java/android/app/ActivityThread.java
- type: aosp
  path: AOSP android-17.0.0_r1 frameworks/base/core/java/android/content/ContentProvider.java
- type: aosp
  path: AOSP android-17.0.0_r1 frameworks/base/services/core/java/com/android/server/am/ContentProviderRecord.java
- type: aosp
  path: AOSP android-17.0.0_r1 frameworks/base/core/java/android/view/ViewTreeObserver.java
- type: official
  path: https://developer.android.com/topic/libraries/app-startup
- type: official
  path: https://developer.android.com/guide/topics/manifest/provider-element
- type: official
  path: https://developer.android.com/guide/topics/providers/content-provider-basics
- type: official
  path: https://developer.android.com/privacy-and-security/direct-boot
- type: aosp
  path: androidx.startup:startup-runtime:1.2.0 AppInitializer.java / InitializationProvider.java
- type: clippings-structure-ref
  path: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md
- type: clippings-structure-ref
  path: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md
- type: aosp
  path: frameworks/base/core/java/android/app/ActivityThread.java (handleBindApplication, installContentProviders, callApplicationOnCreate)
- type: aosp
  path: frameworks/base/core/java/android/os/ZygoteProcess.java (startViaZygote)
- type: official
  path: https://developer.android.com/guide/components/processes-and-threads
- type: official
  path: https://developer.android.com/topic/performance/vitals/launch-time
- type: clippings-structure-ref
  path: Clippings/Android 性能优化 - 虚拟内存优化(上):线程+多进程优化.md
- type: clippings-structure-ref
  path: Clippings/Android 性能优化 - 原理:重新认识应用的速度优化.md
- type: clippings-structure-ref
  path: Clippings/Android 性能优化 - CPU 优化(上):合理使用线程池,提升 CPU 利用率.md
- type: clippings-structure-ref
  path: Clippings/Android 性能优化 - 任务调度优化:线程+CPU,提升任务调度优先级.md
tags:
- contentprovider
- startup
- sdk-init
- app-startup
- multiprocess
- process-priority
- ipc
related_chapters:
- '21.1'
- '21.2'
- '1.15'
- '1.1'
- '5.3'
pipeline_stage: finalized
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part5-app/ch21-startup/03-contentprovider-optimization.md
- src/part5-app/ch21-startup/07-multiprocess-startup.md
---

# ContentProvider 与多进程启动治理

ContentProvider 会在 Application.onCreate 之前安装，多进程组件又可能在每个进程重复执行初始化。启动治理需要明确 Provider 权限和依赖，并为每个进程建立独立初始化清单。

## Provider 安装顺序、依赖与延迟方案

### 范围

在本文关心的场景里，ContentProvider 常见于两类用途：通过 `content://` URI 提供结构化数据，或借系统自动创建组件的时机完成“零代码接入”初始化。这里聚焦后一类及其启动成本，不展开数据增删改查（CRUD）、承载部分游标结果的 `CursorWindow`，也不讨论 Provider 响应超时引发的 ANR（应用无响应）。

平台源码锚点为 Android 17 / API 37 / `android-17.0.0_r1`。截至 2026-08-14，App Startup 1.2.0 仍是最新稳定版，本文的库行为固定到该版本。

### 1. Provider 为什么早于 `Application.onCreate()`

#### 1.1 Android 17 的调用顺序

在 Android 17 的 [`ActivityThread.handleBindApplication()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)中，应用进程主线程按以下关键顺序执行：

```text
创建并 attach Application
        ↓
installContentProviders(app, data.providers)
        ↓
Instrumentation.onCreate(...)
        ↓
Instrumentation.callApplicationOnCreate(app)
```

图中的 attach 指把新建的 `Application` 绑定到进程 `Context` 等运行环境。`data.providers` 是 `system_server` 为当前进程准备的 Provider 列表；`system_server` 是承载 ActivityManager 等核心系统服务的进程。Provider 属于哪个进程，由最终 Manifest 中的 `android:process` 决定，未声明时属于应用默认进程。

`installContentProviders()` 对列表逐个调用 `installProvider()`。本地 Provider 的关键路径是：

1. 通过应用的 `AppComponentFactory`，也就是系统创建应用组件时使用的工厂，实例化 Provider 类；
2. 调用 `ContentProvider.attachInfo(...)`；
3. `attachInfo(...)` 内设置权限、authority 等信息；authority 是 `content://` URI 中用于定位 Provider 的唯一名称；
4. 在承载该 Provider 的进程主线程调用 `ContentProvider.onCreate()`；
5. 将已安装的 `ContentProviderHolder` 汇总后，一次调用 `publishContentProviders(...)` 发布给 `system_server`。holder 是框架传递 Provider 信息和 Binder 进程间通信接口的记录对象。

Provider 多时会增加类加载、实例化、`attachInfo()` 和各自 `onCreate()` 的成本，但不能据此写成“每个 Provider 都单独发起一次发布 Binder 调用”。Android 17 会把当前批次的 holder 放在列表中，通过一次 `publishContentProviders()` 调用发布。

#### 1.2 初始化顺序

同一进程中、未启用 `android:multiprocess` 的 Provider 可以用 `android:initOrder` 声明相对实例化顺序，数值高的先初始化。这个属性只能表达静态先后关系：

- 不能让 `onCreate()` 异步；
- 不能表达完成结果、失败或降级；
- 不能解决跨进程依赖；
- 不能缩短各 Provider 的工作；
- Manifest 中元素的书写顺序不是依赖契约。

需要完整任务依赖时，应使用 App Startup 的同步依赖图，或 [启动框架设计与任务编排](02-startup-task-lazy-concurrency.md)中的显式任务框架。

#### 1.3 App 埋点为什么容易漏掉

很多项目从 `Application.onCreate()` 第一行开始计时。Provider 已经在此前完成，因此这类埋点只能看到 Application 阶段，无法解释完整的 `bindApplication`：这是系统把应用信息、组件和 `Application` 绑定到新进程的启动阶段。

启动基线应以 Macrobenchmark 自动化基准测试得到的端到端 TTID/TTFD 为主：TTID 表示首帧首次显示所需时间，TTFD 表示应用达到完整可用状态所需时间。再结合 Perfetto 系统 Trace 的 Android App Startups 区间和自定义 slice；slice 是 Trace 上带开始、结束时间的命名区间，可用于分解自有 Provider。

### 2. 启动成本从哪里来

Provider 框架本身并非唯一成本。一次自动初始化通常包含四层：

| 层次 | 常见工作 | 需要的证据 |
| --- | --- | --- |
| 组件固定成本 | 类加载、构造、`attachInfo()`、authority 注册 | 框架/应用主线程 Trace |
| `onCreate()` 负载 | 文件、数据库、反射、SDK 初始化、原生 `.so` 库加载 | 自定义 slice、方法栈、I/O |
| 资源竞争 | 后台工作线程争用 CPU/I/O、锁、Binder 等待、垃圾回收 | 调度事件、线程状态、Binder、GC |
| 进程成本 | 远端 Provider 触发承载进程启动与发布 | `system_server` 和两个应用进程的 Trace |

几个常见误判：

- `onCreate()` 很快，不代表它创建的后台工作线程不会与首帧争用资源。
- 看到某个 Provider 类，不代表它的全部成本都归属框架；要进入供应商或业务实现。
- 删除一个 Provider 后 TTID 下降，不足以证明固定组件成本很高；也可能是其业务初始化一起被删除。
- 远端 Provider 不会因主进程启动自动出现在主进程。主进程同步访问其 authority 时，可能触发承载进程创建，并等待 Provider 发布。

Provider 数量可以作为审计入口，不能直接换算成毫秒。

### 3. 从 release Manifest 建立清单

#### 3.1 检查最终合并结果

源码里的 Manifest 不是安装包中的最终结果。依赖库、渠道配置、build type（如 debug/release）、product flavor（如 free/paid 产品配置）和构建时替换的 Manifest placeholder 都可能改变最终组件；build type 与 product flavor 等配置的组合称为 build variant（构建变体）。

Android Gradle Plugin（AGP）的合并决策报告位于模块的 `build/outputs/logs/manifest-merger-<variant>-report.txt`。Android Studio 的 Merged Manifest 视图也能定位某个 Provider 来自哪个依赖。应检查准备发布的每个构建变体，不能只看 debug。

下面的脚本读取一个文本形式的 merged Manifest，列出 Provider 的主要属性：

```python
from pathlib import Path
from sys import argv
from xml.etree import ElementTree as ET

ANDROID = "{http://schemas.android.com/apk/res/android}"
manifest = Path(argv[1])
root = ET.parse(manifest).getroot()
application = root.find("application")

for provider in application.findall("provider"):
    value = lambda name: provider.get(f"{ANDROID}{name}")
    print(
        value("name"),
        f"authorities={value('authorities')}",
        f"process={value('process') or '<application-default>'}",
        f"initOrder={value('initOrder') or '0'}",
        f"enabled={value('enabled')}",
        f"exported={value('exported')}",
        f"directBootAware={value('directBootAware')}",
        sep="\t",
    )
```

脚本的输入应是构建工具生成的可读 XML，不能直接使用 APK 中经过编译的二进制 XML。中间产物路径会随 AGP 变化，应从当前构建输出或 Android Studio 获取，避免把某个 AGP 版本的 `intermediates` 路径写死在工具中。

#### 3.2 每个 Provider 要记录什么

| 字段 | 核对内容 |
| --- | --- |
| 身份 | 类名、authority、来源依赖坐标（如 `group:name:version`）、精确版本 |
| 构建 | 出现在哪些构建变体、由哪条 Manifest 合并规则引入 |
| 进程 | `android:process` 与 `<application android:process>` 的合并结果 |
| 顺序 | `initOrder` 及是否存在静态依赖 |
| 生命周期 | enabled、directBootAware、是否会在用户解锁前运行 |
| 安全 | 是否对外暴露、整体读写权限、临时 URI 授权、分路径权限 |
| 工作 | `onCreate()` 同步工作、后台任务、注册项、磁盘和网络 |
| 必要性 | TTID 前、TTFD 前、功能首用或未使用 |
| 运维 | 显式初始化 API、停止/禁用、回退和供应商联系人 |

如果同一 SDK 带来多个 Provider，要按业务能力归组，避免只删表面入口却留下另一个自动入口。

### 4. 如何测量 Provider 成本

#### 4.1 自有 Provider

自有 Provider 可以直接用稳定名称包住 `onCreate()`。下面的代码只用于观测同步入口：

```kotlin
class AppInitProvider : ContentProvider() {
    override fun onCreate(): Boolean {
        return trace("startup/AppInitProvider") {
            installMinimalState(requireNotNull(context))
            true
        }
    }
}
```

这个 slice 的持续时间是同步 `onCreate()` 时间。若 `installMinimalState()` 只提交后台任务，必须继续记录该任务的排队、运行和逻辑完成时间；Provider slice 结束不能代表初始化已就绪。

开发阶段还可用 StrictMode 检测自有代码在主线程发生的磁盘或网络访问。它适合发现违规操作，不是生产环境耗时指标，也不一定覆盖原生代码或供应商内部的全部访问。

#### 4.2 第三方 Provider

闭源 Provider 无法增加切片时，使用组合证据：

1. 从合并后的 Manifest 和合并报告锁定类与来源版本。
2. 在 Perfetto 的 `bindApplication` 窗口看主线程栈、I/O、Binder 和类加载。
3. 生成一对 release 构建产物，唯一差异是是否保留该 Provider 自动入口。
4. 在移除自动入口的产物中，于等价场景显式初始化同一 SDK，分开测量“组件固定成本”和“SDK 业务成本”。
5. 重复冷启动，比较分布和 Trace，不用单次差值。

如果供应商不允许关闭自动初始化，应要求其提供诊断构建、Trace 或源码说明。通过反射跳过私有方法会依赖未公开实现，SDK 升级后很容易失效，不应把这种风险带进启动关键路径。

#### 4.3 观察跨进程等待

主进程通过 `ContentResolver` 获取远端 authority 时，`ActivityThread` 可能向 `system_server` 请求 Provider，并等待承载进程完成发布。诊断时同时看：

- 调用进程的 Binder/等待状态；
- `system_server` 的 Provider 获取和进程启动；
- 承载进程的进程绑定、Provider `onCreate()` 和发布；
- 超时、死亡与重试。

调用方线程若是 Main，这段等待会直接进入 UI 关键路径。远端进程并不会让同步访问自动变快。

### 5. 按用户可见边界分类

不要给 Provider 统一规定 5 ms 或 50 ms。准入预算应从应用的 TTID/TTFD SLO、当前余量、设备档位和入口推导。SLO（Service Level Objective，服务目标）是团队承诺持续满足的可测指标，例如“某类设备冷启动 P95 不超过 1.5 秒”；P95 表示 95% 的启动样本不超过该值。

| 类别 | 判断 | 处理 |
| --- | --- | --- |
| 未使用 | 业务没有调用且组件仅由依赖默认注入 | 移除，并做功能/构建回归 |
| TTID 前必要 | 首个应用帧缺少它就无法正确生成 | 只保留最小同步状态，设置明确失败路径 |
| TTFD 前必要 | 第一帧可先出现，主要操作仍需等待 | 移出 Provider，进入任务图 |
| 功能首用 | 分享、地图、支付、广告等特定入口才需要 | 单次按需初始化 |
| 延后维护 | 日志整理、上传、预取等 | 在页面可用后按资源预算调度 |

“崩溃监控 SDK 必须最早”“远程配置必须首帧前”等结论也要拆分。崩溃捕获、历史日志整理、符号上传可以处于不同阶段；远程配置通常可以先读取上一次保存且校验通过的本地快照。

分类完成后，每个任务都要有维护负责人（owner）、完成条件、失败结果和验证场景。没有这些契约，挪出 Provider 只会把隐式时序问题移到别处。

### 6. 从 Manifest 删除自动入口

#### 6.1 优先使用供应商开关

供应商若提供官方的 Manifest placeholder 或 Gradle 开关，应优先使用。placeholder 是构建时才替换成具体值的占位符；官方开关通常会同时调整 Provider、metadata 和 SDK 内部状态。

没有开关时，可以在高优先级应用 Manifest 中使用合并标记，也就是 `tools:` 命名空间下控制 Manifest Merger 行为的指令。下面的规则按 Provider 类名移除下游库声明：

```xml
<manifest
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools">

    <application>
        <provider
            android:name="com.vendor.sdk.AutoInitProvider"
            tools:node="remove" />
    </application>
</manifest>
```

Manifest Merger 对 `<provider>` 的匹配键是 `android:name`。如果只想影响某个库，可在确认合并来源后使用 `tools:selector`，把标记限定到指定库包名；无论使用哪种方式，都要检查最终结果。

#### 6.2 删除后的验证

至少验证：

- release、debug、渠道和动态特性模块等相关构建变体；
- 合并后的 Manifest 和合并报告已无目标节点；
- SDK 显式初始化只执行一次；
- deep link（从网页或其他应用直达指定页面）、推送、后台任务、登录、分享、支付等入口；
- 用户同意、拒绝、撤回与无网路径；
- Direct Boot（用户首次解锁前运行）、备份恢复、升级安装和进程重建；
- Java 混淆映射文件、原生崩溃符号文件和监控仍可用。

若 Provider 对外提供 `content://` URI，删除它会改变对外 API 和数据共享方式，不能按普通性能优化处理。还要检查调用方、权限、临时 URI 访问授权和历史数据迁移。

`tools:node="remove"` 只改变合并结果，不会阻止供应商以后换类名或新增另一个 Provider。SDK 升级必须重新做 Manifest 差异。

### 7. 显式初始化的状态机

按需初始化至少包含这些状态：

```text
NotStarted → Initializing → Ready
                   ├──────→ Degraded
                   └──────→ Failed
```

`NotStarted` 表示尚未启动，`Initializing` 表示正在初始化，`Ready` 表示能力可用，`Degraded` 表示只能提供约定的备用能力，`Failed` 表示本次初始化失败。并发调用应共享同一个 `Initializing` 结果，不能重复启动；协程调用者可以挂起等待而不占住线程，其他调用者可以注册回调。Main 线程不能用锁或 `Future.get()` 阻塞等待。

状态机还要定义：

- SDK 是否要求 Main 调用；
- 异步回调何时代表逻辑可用；
- 超时是否能协作取消，即任务是否会响应中断、取消标记或底层取消 API；
- 晚到结果是否允许写状态；
- 失败是否缓存、何时重试；
- 用户撤回同意后如何停止与清理；
- 进程重建后如何恢复。

不能笼统地把 SDK 初始化丢进 I/O 线程。有些 SDK 明确要求在 Main 线程调用，有些初始化同时包含 Main 注册和后台准备，应拆成有依赖的两个任务。

### 8. “首帧后”需要说明观测点

`OnPreDrawListener` 在视图树即将绘制时执行，`View.post()` 只表示把一段 `Runnable` 工作放进 Main 消息队列。两者都不能证明该帧已经提交给渲染系统。

适用范围从 API 29 开始。硬件渲染页面可以用 `registerFrameCommitCallback()` 等下一帧提交到 swap chain 后再触发延后任务；swap chain 是渲染系统轮换使用、等待显示的一组图像缓冲区：

```kotlin
val root = window.decorView

root.doOnPreDraw {
    if (root.isHardwareAccelerated) {
        root.viewTreeObserver.registerFrameCommitCallback {
            root.post {
                startupScheduler.start(StartupPhase.DEFERRED)
            }
        }
    } else {
        root.post {
            startupScheduler.start(StartupPhase.DEFERRED)
        }
    }
}
```

`doOnPreDraw` 在本轮绘制前注册回调。硬件路径的回调表示帧已提交到 swap chain，仍不等于像素已经显示；软件渲染的备用分支只保证工作排在当前 traversal 之后。traversal 是本轮测量、布局和绘制组成的界面遍历过程。生产代码还需处理 Activity 销毁、重复注册和取消。

延后任务可能与下一帧交互争用 CPU/I/O。调度后仍要用 FrameTimeline 的逐帧期限与卡顿数据、TTID/TTFD 和真实交互场景验证。若任务是“主要内容可用”的必要条件，应进入 TTFD 图，不能归到 `DEFERRED`。

### 9. App Startup 1.2.0 的准确边界

#### 9.1 它减少的是入口，不是业务工作

[Jetpack App Startup](https://developer.android.com/topic/libraries/app-startup) 让多个组件共享一个 `InitializationProvider`，并用 `Initializer.dependencies()` 声明顺序。相比每个 SDK 各带一个 Provider，它减少了 Provider 类、实例和 `onCreate()` 入口，也让依赖关系集中。[1.2.0 发布说明](https://developer.android.com/jetpack/androidx/releases/startup) 显示它截至 2026-08-14 仍是最新稳定版。

App Startup 仍基于 ContentProvider。Manifest 发现过程和所有 `Initializer.create()` 在 Provider 安装阶段同步运行，不会自动进入后台线程，也不会删除 SDK 内部的磁盘、锁或网络成本。

1.2.0 `AppInitializer` 的核心行为是：

- 从 `InitializationProvider` 的 Manifest metadata 键值配置中发现入口 initializer；
- 通过反射按运行期类名构造 initializer；
- 深度优先执行依赖；
- 用 `initializing` 集合检测环；
- 缓存已经初始化的结果；
- 给发现过程和 initializer 增加 Trace 时间区间。

#### 9.2 自动初始化

下面的 initializer 声明 CrashClient 依赖 Logger：

```kotlin
class CrashInitializer : Initializer<CrashClient> {
    override fun create(context: Context): CrashClient {
        return CrashClient.install(context.applicationContext)
    }

    override fun dependencies(): List<Class<out Initializer<*>>> {
        return listOf(LoggerInitializer::class.java)
    }
}
```

`LoggerInitializer.create()` 完成后，App Startup 才调用 `CrashInitializer.create()`。两个方法都要同步返回可用结果；内部若只提交异步任务，依赖图无法知道何时就绪。

Manifest 只需要声明初始化图的入口节点：

```xml
<provider
    android:name="androidx.startup.InitializationProvider"
    android:authorities="${applicationId}.androidx-startup"
    android:exported="false"
    tools:node="merge">
    <meta-data
        android:name="com.example.CrashInitializer"
        android:value="androidx.startup" />
</provider>
```

依赖节点由 `dependencies()` 发现，不必重复写 metadata。添加前要确认原 SDK Provider 已按官方方式删除，避免两条入口重复初始化。

#### 9.3 手动初始化

不需要在 Provider 阶段自动执行的 initializer，应从最终 Manifest 删除对应 metadata：

```xml
<provider
    android:name="androidx.startup.InitializationProvider"
    android:authorities="${applicationId}.androidx-startup"
    android:exported="false"
    tools:node="merge">
    <meta-data
        android:name="com.example.ShareInitializer"
        tools:node="remove" />
</provider>
```

需要时显式触发该组件：

```kotlin
val shareClient = AppInitializer.getInstance(context)
    .initializeComponent(ShareInitializer::class.java)
```

`initializeComponent()` 会在调用线程同步初始化该组件及尚未完成的依赖。调用方必须满足所有 initializer 的线程契约；改成手动调用不代表可以从任意后台线程执行。

官方文档还指出，关闭某个组件的自动初始化，也会关闭只由它带入的依赖。若另一个自动入口仍依赖其中某个节点，该节点仍会在启动时执行。迁移时应画出完整依赖图，核对每个入口。

### 10. 多进程与 Direct Boot

#### 10.1 Provider 属于承载进程

最终 Manifest 决定 Provider 在哪个承载进程创建。每个进程拥有独立的 Java heap（对象内存区）、类静态字段和 App Startup 单例：

- 默认 Provider 只随应用默认进程安装；
- `android:process=":push"` 的 Provider 在私有 `:push` 进程运行；
- 显式把 InitializationProvider 声明到多个进程，会形成多份独立初始化结果；
- 一个进程不能依赖另一个进程的静态 `initialized` 布尔值。

进程选择应尽量在 Manifest 或构图阶段完成。进入 initializer 后才按进程名提前返回，此前已经可能发生类加载和静态字段初始化。

#### 10.2 Direct Boot

[`android:directBootAware="true"`](https://developer.android.com/privacy-and-security/direct-boot) 允许 Provider 在设备重启后、用户首次解锁前运行。此时只能访问 device-protected storage（设备保护存储）和其他支持 Direct Boot 的能力；默认的 credential-encrypted storage（凭据加密存储）要等用户解锁后才可用。该属性适用于闹钟、短信等确有解锁前需求的组件，不能用作普通的“提前初始化”开关，也不能在设备保护存储中随意保存口令或认证令牌。

#### 10.3 `multiprocess` 与同 UID 多实例

Manifest 的 `android:multiprocess="true"` 允许系统在同一 UID（Linux 用户 ID，Android 用它隔离应用身份）的其他进程中本地创建 Provider 实例，通常对应应用自己的子进程。Android 17 的 [`ContentProviderRecord.canRunHere()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ContentProviderRecord.java) 同时检查 `multiprocess` 和 UID；不同 UID 的外部应用仍通过 Binder 访问承载进程中的实例。

本地实例可以省去应用自身进程间的部分 Binder 调用，却会复制对象、缓存和连接，并要求各实例解决状态一致性。它不适合作为通用启动优化。迁移前要核对旧应用是否依赖这项少见行为，并在目标 API 37 设备上验证。

### 11. 性能优化不能破坏 Provider 安全

每个保留或迁移的 Provider 还要检查：

- authority 是否唯一且使用 applicationId 前缀；
- `android:exported` 是否显式符合共享需求，也就是是否允许其他应用访问；
- 整个 Provider 的读写权限，以及只约束部分 URI 路径的 path permission；
- 临时 URI 访问授权的授予和撤回；
- 组件是否只在必要用户/进程启用；
- `call()`、`openFile()` 和批处理接口是否暴露越权操作，例如绕过查询权限读取文件或执行管理命令。

将外部 Provider 改成应用进程内单例，或把远端 Provider 改到主进程，都可能改变安全边界、故障隔离和内存成本。这类迁移需要单独设计，不能只看 TTID。

### 12. 验收标准

| 验收项 | 需要的证据 |
| --- | --- |
| 组件清单 | 每个 release Provider 有来源、版本、进程、用途和维护负责人 |
| Manifest | 所有目标构建变体的合并结果和差异 |
| 启动 | 冷启动 TTID/TTFD 分布与回归样本 Trace |
| Provider 阶段 | 进程绑定阶段的同步成本、后台任务竞争和跨进程等待 |
| 功能 | 各入口、同意状态、无网、升级、进程重建 |
| 多进程 | 每个进程只执行必要图，跨进程失败可降级 |
| 安全 | `exported`、权限、authority 和临时 URI 授权复核 |
| 运维 | 显式初始化、禁用、回退和 SDK 升级检查 |

完成治理后，报告应能回答：

1. 哪些 Provider 仍会在 TTID 之前自动执行？
2. 每个 `onCreate()` 同步做了什么？
3. 哪些初始化被移到 TTFD 或功能首用？
4. 失败、超时和进程死亡如何降级？
5. SDK 升级新增 Provider 时如何被发现？

Provider 数量减少只是实现变化。验收依据是用户可见启动、功能正确性和安全边界都得到可重复验证。

## 进程拓扑、重复初始化与共享边界

主进程的 Provider 优化完成后，还要检查远程 Service、WebView 或独立业务进程是否重复加载 SDK、线程池和缓存。

多进程可以隔离崩溃、内存峰值和重型 native（C/C++ 等本地代码）模块，也会新增一套进程运行时、初始化链路和 IPC（Inter-Process Communication，进程间通信）边界。它是一项架构取舍，不能代替主进程自身的启动治理。

App 可以控制的部分包括：是否拆进程、何时启动、每个进程初始化什么、调用方怎样等待远程能力，以及如何在 Android 17 上验证收益。进程优先级与回收规则见 [进程模型](../../part1-fundamentals/ch01-architecture/01-android-architecture-process-threading.md)，冷启动分段与 TTID（App 第一帧时间）、TTFD（主要内容可用时间）见 [启动分析](01-app-startup-path-monitoring.md)，后台任务约束见 [后台执行限制](../../part1-fundamentals/ch05-cpu-power/03-background-jobs-hibernation.md)。

### 1. 先确认拆进程的目的

在 Manifest 中给组件设置 `android:process=":worker"`，会让它运行在名为“应用包名`:worker`”的私有远程进程中。这个进程通常仍使用应用的 UID（Linux 用户身份）和权限，但拥有独立的 ART（Android Runtime）实例、Java/Kotlin 堆（托管对象内存）、native 堆（C/C++ 动态分配内存）、静态字段、线程、ClassLoader 类加载状态和 Binder 线程池。主进程里的单例不会自动出现在远程进程，远程进程修改的内存对象也不会同步回来。

拆进程常见的合理目标包括：

- 隔离 WebView 宿主、地图、音视频、图片处理或插件运行时的 native 崩溃与内存峰值；
- 让需要独立生命周期的组件脱离主进程，但仍遵守后台启动和前台服务限制；
- 在 32 位设备上减轻单个进程的虚拟地址空间压力；
- 把需要处理不可信输入、且权限需求很少的 Service 放进 isolated process。

普通私有进程与 isolated process 的语义不同：

| 形式 | manifest 示例 | 身份与权限 | 适用场景 |
| --- | --- | --- | --- |
| 应用私有远程进程 | `android:process=":worker"` | 通常沿用应用 UID、权限和数据目录访问能力 | WebView 宿主、播放、上传、插件容器等应用内能力 |
| isolated service | `android:isolatedProcess="true"` | 使用隔离 UID，没有自身应用权限；只能通过 Service API 与外界通信 | 处理不可信输入、需要更小权限面的计算服务 |

多进程也有固定成本：

- 系统要创建进程并绑定应用；
- 每个进程都要建立自己的运行时和堆；
- 该进程中的 Provider、`Application` 和目标组件需要初始化；
- 数据交换改走 Binder、Provider、文件或数据库；
- 系统可能随时回收远程进程，客户端必须恢复连接和请求状态。

WebView 在多进程模式下会把网页内容放进 renderer process（Chromium 渲染进程），多个 WebView 还可能共享同一个 renderer。把 WebView 宿主 Activity 或 Service 放进应用远程进程，新增的是宿主侧 WebView、业务代码和部分 native 状态的隔离，并没有再增加一层 renderer 隔离。评估拆分时，应同时测量主进程峰值、远程进程峰值和全应用 PSS（Proportional Set Size，按比例分摊共享页后的内存），不能只看主进程数字变小。

### 2. Android 17 的进程启动链路

当系统需要运行一个尚无进程可用的组件时，system_server（运行 Android 核心系统服务的进程）会请求 Zygote 创建应用进程。Zygote 是预加载了通用框架代码的进程，可通过 fork（用写时复制派生子进程，修改内存页时才生成私有副本）快速创建 App 进程。Android 17 的 `ZygoteProcess.startViaZygote()` 负责整理参数，并通过 Zygote socket（进程间通信端点）发送创建请求；新进程随后进入 `ActivityThread` 的应用绑定流程。`ActivityThread` 是 App 进程接收组件与生命周期调度的核心类。

相关链路可以压缩成下面几步：

```text
组件请求
  -> system_server 判断目标进程尚未运行
  -> ZygoteProcess.startViaZygote()
  -> Zygote fork 应用进程
  -> ActivityThread.handleBindApplication()
       -> 创建 Application
       -> 安装分配给该进程的 ContentProvider
       -> 调用 Application.onCreate()
  -> 创建目标 Activity / Service / Receiver / Provider 客户端能力
```

这段链路有两个容易混淆的边界。

第一，Provider 按 Manifest 声明的进程归属安装。系统不会把应用里的所有 Provider 安装到每一个进程；默认进程 Provider 属于主进程，声明了 `android:process=":worker"` 的 Provider 属于对应远程进程。一个进程只要分配到了自动初始化 Provider，系统就会在该进程的 `Application.onCreate()` 之前创建并调用它们。

第二，在 `Application.onCreate()` 中按进程名分支，只能约束分支之后的工作，无法撤销已经执行的 Provider 初始化。第三方 SDK 通过 Provider 或 AndroidX App Startup 自动初始化时，需要同时检查 Manifest 进程归属、initializer（组件初始化器）依赖和自动初始化开关。

这也解释了同步 IPC 对首屏的影响：主进程在首帧前访问远程 Provider，或调用异步 `bindService()` 后又同步等待连接结果，都可能触发远程进程冷启动。等待方会把进程创建、Provider 安装、`Application.onCreate()` 和目标服务准备时间计入自己的启动路径。

### 3. 给每个进程定义最小初始化集

`Application.getProcessName()` 从 Android 9（API 28）开始提供，本文覆盖的 Android 10～17 均可直接使用。它比读取 `/proc` 伪文件或枚举运行进程更简单，也避开了系统实现与权限条件差异带来的误判。

下面的代码用于把进程名映射成稳定的角色，并让每个进程只初始化自己的能力：

```kotlin
enum class ProcessRole {
    MAIN,
    WEB,
    UPLOAD,
    OTHER,
}

private fun Application.processRole(): ProcessRole {
    val current = Application.getProcessName()
    return when (current) {
        packageName -> ProcessRole.MAIN
        "$packageName:web" -> ProcessRole.WEB
        "$packageName:upload" -> ProcessRole.UPLOAD
        else -> ProcessRole.OTHER
    }
}

class App : Application() {
    override fun onCreate() {
        super.onCreate()

        when (processRole()) {
            ProcessRole.MAIN -> initMainProcess()
            ProcessRole.WEB -> initWebProcess()
            ProcessRole.UPLOAD -> initUploadProcess()
            ProcessRole.OTHER -> initMinimalProcess()
        }
    }
}
```

这段分支适合控制日志、线程池、业务 SDK、native 库和缓存等 `Application` 阶段工作。它不控制 Provider 阶段；每个自动初始化 Provider 仍要检查 `android:process`，AndroidX App Startup initializer 还要检查依赖关系，并判断是否改为手动初始化。

初始化清单可以按以下原则收缩：

- 主进程只保留首屏展示、路由、安全校验和首屏必需数据；
- Web 进程只准备 Web 宿主所需的桥接、Cookie 或安全策略，不复制整套主进程 SDK；
- 上传进程只准备任务数据库、网络栈和通知能力，不创建图片 UI、页面路由或主进程业务线程池；
- 所有进程共用的日志与崩溃采集也要有进程预算，不能因为“公共基础设施”就在每个进程启动完整线程和周期任务。

静态初始化同样受进程边界影响。Kotlin `object`、Java 静态字段和 JNI（Java 与 native 代码的调用接口）全局状态都是“每个进程一份”。类第一次加载时触发的重工作不会被 `Application` 分支自动拦住，应通过懒加载或显式入口控制。

### 4. 控制远程进程的拉起时机

Android 没有面向普通应用的通用“只创建进程、暂不运行组件”接口。启动 Activity、`startService()`、`bindService()`、访问远程 Provider、接收广播或运行调度任务，都可能创建进程；每种入口同时受对应组件和后台执行规则约束。

可以按用户路径把拉起时机分成四档：

| 时机 | 判断标准 | 建议 |
| --- | --- | --- |
| 首屏前 | 缺少远程结果就无法展示可交互首屏 | 缩小协议和初始化集；优先采用异步协议、deadline（最晚完成时点）和降级路径，并把等待计入 TTID/TTFD |
| 首帧后 | 首屏不依赖，但用户很快可能进入相关功能 | 等首帧完成后再绑定或发送轻量探测，观察是否与主线程争抢 CPU、I/O |
| 临近入口 | 已出现页面曝光、Tab 切换或点击前置动作 | 用明确的产品信号拉起，过期后取消，不做长期无条件预热 |
| 系统调度 | 上传、同步、清理等不依赖当前页面 | 交给 WorkManager、JobScheduler 或符合规则的前台服务 |

首帧后执行不等于“对启动无影响”。低端设备上，新进程会与主进程竞争 CPU、存储 I/O、页缓存（内存中暂存的文件数据）和内存。预热实验至少要比较以下三组：

1. 不预热，用户进入功能时冷启动；
2. 首帧后立即预热；
3. 临近功能入口再预热。

比较指标应包括主进程 TTID/TTFD、远程能力 ready（协议已经可以接受请求的时点）、用户进入功能后的等待、全应用 PSS、低内存回收次数和失败率。只有用户等待时间的下降覆盖资源与稳定性代价，预热才有保留价值。

### 5. 把 Binder ready 建模为异步能力

同步 Binder 调用会阻塞客户端调用线程，直到服务端返回或调用失败。跨进程事务通常由服务端 Binder 线程池执行，多个客户端可能并发进入同一实现，所以服务端状态要满足线程安全。`oneway` 只让跨进程调用方立即返回；同一 Binder 对象的多次 oneway 调用仍按发送顺序逐个分发，而且“已返回”不表示业务已经完成。结果、超时和取消仍需由协议定义。

客户端不能假设远程服务会一直存在。连接状态至少要区分连接中、可用、断开和失败，并处理 Binder 所在进程死亡。

下面的示例展示一个最小连接状态机。业务协程可以异步等待 ready；主线程不能用 `CountDownLatch`（让线程等待计数归零的同步器）、自旋（循环检查状态并持续占用 CPU）或无限期同步调用来等待：

```kotlin
sealed interface RemoteState {
    data object Disconnected : RemoteState
    data object Connecting : RemoteState
    data class Ready(
        val service: IWorkerService,
        val binder: IBinder,
    ) : RemoteState
    data class Failed(val cause: Throwable?) : RemoteState
}

class WorkerConnection :
    ServiceConnection,
    IBinder.DeathRecipient {

    private val _state =
        MutableStateFlow<RemoteState>(RemoteState.Disconnected)
    val state: StateFlow<RemoteState> = _state.asStateFlow()

    fun markConnecting() {
        _state.value = RemoteState.Connecting
    }

    override fun onServiceConnected(
        name: ComponentName,
        binder: IBinder,
    ) {
        try {
            binder.linkToDeath(this, 0)
            _state.value = RemoteState.Ready(
                service = IWorkerService.Stub.asInterface(binder),
                binder = binder,
            )
        } catch (error: RemoteException) {
            _state.value = RemoteState.Disconnected
        }
    }

    override fun onServiceDisconnected(name: ComponentName) {
        _state.value = RemoteState.Disconnected
    }

    override fun onBindingDied(name: ComponentName) {
        _state.value = RemoteState.Disconnected
    }

    override fun onNullBinding(name: ComponentName) {
        _state.value = RemoteState.Failed(null)
    }

    override fun binderDied() {
        _state.value = RemoteState.Disconnected
    }

    suspend fun awaitReady(timeoutMillis: Long): IWorkerService =
        withTimeout(timeoutMillis) {
            state
                .filterIsInstance<RemoteState.Ready>()
                .first()
                .service
        }
}
```

这段代码只展示连接骨架。调用方仍需成对执行 bind/unbind。`onServiceDisconnected()` 表示连接意外丢失，原绑定仍然有效，服务重新运行后可能再次收到 `onServiceConnected()`；`onBindingDied()` 表示这条绑定不会自动恢复，必须先解绑再按业务需要重绑；`onNullBinding()` 也要解绑以释放跟踪资源。不用仍存活的旧 Binder 时，还要解除 `linkToDeath()` 注册。`binderDied()` 可能在 Binder 线程执行，并与新连接回调并发，生产实现应给每次连接分配代次，忽略旧代次回调，避免旧死亡通知覆盖新的 `Ready` 状态。状态更新之外的重工作应切换到受控协程或执行器。

远程事务可能包含磁盘、网络或重计算。AIDL（Android Interface Definition Language）用于声明跨进程接口；客户端应把同步 AIDL 调用放到允许阻塞的调度器，并给业务请求单独设置超时：

```kotlin
suspend fun transcode(
    connection: WorkerConnection,
    request: TranscodeRequest,
): TranscodeResult = withTimeout(3_000) {
    withContext(Dispatchers.IO) {
        connection.awaitReady(timeoutMillis = 1_000)
            .transcode(request)
    }
}
```

内层超时约束连接等待，外层超时为调用方协程设置业务 deadline。但同步 Binder 一旦进入阻塞，`withTimeout` 不能强制中断正在执行的事务，因此这段代码不能提供严格的墙钟时间上限，也就是从调用开始计算的实际耗时上限。需要硬超时的耗时协议，应改成异步请求加回调，并提供请求 ID、显式 `cancel(requestId)` 和服务端 deadline；服务端还要让重复请求可安全重试。

如果首屏允许降级，超时后应返回本地占位、稍后重试或跳过非核心能力。不要在主线程用同步 Binder、文件锁或数据库锁把远程冷启动串到首帧之前。

### 6. 跨进程状态要有唯一所有者

`Context.MODE_MULTI_PROCESS` 从 API 23 起已废弃。Android 17 的 `Context` 文档明确说明，它不能可靠协调跨进程 `SharedPreferences`；不同进程各自缓存数据，并发修改也没有可依赖的冲突合并规则。

跨进程状态应明确唯一写入者和一致性协议：

- 小型查询或受控写入可以由一个 Provider 统一管理，让其他进程通过 IPC 访问唯一的数据实现；
- 高频、强类型调用可以使用 AIDL，并在服务端串行化关键状态；
- 大对象使用文件、数据库、共享内存或文件描述符传递，Binder 只传请求 ID、状态等控制信息，避免占满事务缓冲区；
- 配置变更携带 `version` 或 `generation`（状态代次），客户端重连时重新拉取快照；
- 一次性事件携带请求 ID，避免进程死亡后的重复提交产生副作用。

数据库能够被多个进程打开，不等于业务事务已经具备一致性保证。需要核对所用数据库库的多进程能力、WAL（Write-Ahead Logging，预写日志）与锁行为、数据失效通知和迁移时序。数据库升级只能有一个受控入口；其他进程在 schema（数据库结构）准备完成前，应等待带超时的状态，不能并发发起迁移。

### 7. 按“会死亡”设计，不做进程保活技巧

远程进程可能因内存压力、组件生命周期结束、崩溃或系统策略而消失。应用不能依赖 `Application.onTerminate()` 做生产环境清理；官方 API 文档明确说明，量产设备结束进程时不会调用这个方法，也不会执行其他应用清理代码。

绑定关系、正在运行的前台服务和用户可感知组件会影响系统对进程重要性的判断，但不能用来任意延长进程寿命。前台服务只适合用户能够感知的持续任务，并要声明正确的服务类型、权限和通知；从后台启动时还要满足对应版本的豁免条件。空 Service、循环广播、主辅进程互相启动和没有业务意义的前台服务会增加功耗与内存，也可能触发系统限制。

更可靠的恢复路径包含：

- 客户端监听 Binder 死亡，清掉旧代理并按当前页面需求决定是否重连；
- 服务端把必要状态持久化，让请求具备幂等键或可恢复检查点（中断后可继续的位置）；
- 客户端保存可序列化、可重建的请求描述，不保存只能由旧进程内存解释的对象引用；
- 连接失败、初始化失败和业务失败使用不同错误码，分别制定逐步延长重试间隔的退避、降级和用户提示；
- 不再有页面或任务需要服务时及时解绑，让系统回收空闲进程。

如果一次冷启动很贵，应优先减少远程进程初始化量、缩短协议握手和缓存可复用产物。是否在首帧后预热，应由命中率和资源数据决定。

### 8. Android 17 上怎样观测

没有 Activity 的远程服务进程不会绘制应用界面，因此没有有意义的 TTID/TTFD。主进程继续观察 TTID、TTFD 和首帧前同步等待；远程进程应定义自己的 `binder_ready`、`provider_ready` 或首个业务结果时间，并写清每个时点代表的可用能力。

Android 15（API 35）加入 `ApplicationStartInfo`，可以读取进程名、启动原因和启动时间戳；Android 16（API 36）又加入 `getStartComponent()`，用于区分 Activity、Service、Broadcast 和 ContentProvider。`getReason()` 给出 launcher、Job、Push 等更细的触发原因，不能单独替代组件类型。Android 17 上可通过 `ActivityManager.getHistoricalProcessStartReasons()` 读取按时间倒序保存的近期记录，其中可能包含仍在启动的未完整记录。它适合解释“为什么创建进程”，应用自己的 trace 和埋点仍要解释初始化阶段耗时。

每次远程进程启动建议至少记录：

| 维度 | 字段 | 诊断目的 |
| --- | --- | --- |
| 身份 | processName、pid（进程 ID）、versionName、启动代次 | 区分多次重启与版本差异 |
| 原因 | `ApplicationStartInfo.reason`、start component、业务入口 | 找出意外 Provider、广播或后台任务拉起 |
| 阶段 | Application 入口/出口、Provider、自定义 SDK、binder ready | 找出远程冷启动的长任务 |
| 主进程影响 | 首帧前 IPC 次数、同步等待、超时与降级 | 判断是否把远程成本传回主线程 |
| 资源 | PSS、RSS、Java/native heap、线程、FD（文件描述符） | 衡量拆分和预热的常驻代价 |
| 稳定性 | `binderDied`、重绑、崩溃、请求重放、失败率 | 验证进程死亡后的恢复质量 |

PSS 会按共享进程数分摊共享内存页，适合估算多个进程合计对系统内存的压力。RSS（Resident Set Size，常驻内存大小）包含该进程映射的全部共享页，适合观察单进程分配趋势；直接相加多个进程的 RSS 会重复计算共享页。报告“多进程节省内存”时，需要说明使用了哪一种统计口径。

本地排查可以先用下面的命令确认进程、内存和长期存活情况：

```bash
adb shell dumpsys activity processes
adb shell dumpsys meminfo com.example.app
adb shell dumpsys procstats --hours 3
```

第一条查看当前进程与组件状态，第二条分项显示应用内存，第三条读取 `procstats`（系统长期记录的进程状态与内存统计）。不同 Android 版本与设备厂商的 `dumpsys` 文本格式可能变化，自动化采集更适合使用稳定 API、Perfetto 数据源或只解析明确支持的系统版本。

Perfetto 是系统级时间线分析工具。分析时要把主进程和远程进程放在同一时间轴上，关注进程创建、`bindApplication`、Provider 初始化、自定义 trace、Binder 阻塞、I/O 和 CPU 竞争。一次优化至少回答三个问题：主进程首帧有没有改善，远程能力可用时间有没有变慢，合计资源与失败率是否可以接受。

### 检查清单

- [ ] 每个远程组件的 `android:process` 都有明确理由。
- [ ] 普通远程进程与 isolated process（隔离 UID、无自身权限）的权限假设已分别验证。
- [ ] Provider 的进程归属和自动初始化项已检查。
- [ ] `Application.getProcessName()` 分支覆盖所有已声明进程。
- [ ] 每个进程只创建本进程需要的 SDK、线程池和 native 状态。
- [ ] 首帧前没有无上限的同步 Binder、Provider 或锁等待。
- [ ] Binder 客户端处理超时、死亡、重绑、取消和请求幂等。
- [ ] 跨进程状态有唯一所有者，没有依赖 `MODE_MULTI_PROCESS`。
- [ ] 远程进程可被回收，恢复路径不依赖 `onTerminate()`。
- [ ] 预热实验同时比较命中率、TTID/TTFD、remote ready（远程能力可用时点）、PSS 和失败率。
- [ ] PSS/RSS 的统计口径和聚合方法已在报告中说明。
- [ ] `ApplicationStartInfo`、应用 trace 与线上埋点能解释进程启动原因和阶段。

## 小结

Provider 治理先从最终 Manifest 建立清单，再按 TTID、TTFD 与功能首用划分必要性；删除自动入口后，必须用显式状态机补齐依赖、失败、安全和回归验证，不能只追求 Provider 数量下降。

多进程优化再按“确认隔离目标 → 明确组件归属 → 压缩每个进程的初始化集 → 设计可超时、可取消、可重连的异步协议”推进。Android 17 的源码时序给出了一条明确边界：属于该进程的 Provider 先于 `Application.onCreate()` 执行，因此进程名分支和 Provider 治理都要检查。验收时同时观察主进程首帧、远程能力 ready、全应用内存与进程死亡恢复，才能判断这次拆分是否值得。

## 参考资料

- [AOSP Android 17 `ActivityThread`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [AOSP Android 17 `ContentProvider`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/ContentProvider.java)
- [AOSP Android 17 `ContentProviderRecord`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ContentProviderRecord.java)
- [Android `<provider>` manifest 元素](https://developer.android.com/guide/topics/manifest/provider-element)
- [Manifest 合并规则](https://developer.android.com/build/manage-manifests)
- [Direct Boot 指南](https://developer.android.com/privacy-and-security/direct-boot)
- [Jetpack App Startup](https://developer.android.com/topic/libraries/app-startup)
- [Jetpack App Startup 发布说明](https://developer.android.com/jetpack/androidx/releases/startup)
- [Jetpack Startup 1.2.0 源码包](https://dl.google.com/dl/android/maven2/androidx/startup/startup-runtime/1.2.0/startup-runtime-1.2.0-sources.jar)
- [`ViewTreeObserver.registerFrameCommitCallback`](https://developer.android.com/reference/android/view/ViewTreeObserver)

- [Android 17 `ActivityThread.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)：`handleBindApplication()`、`installContentProviders()` 与 `callApplicationOnCreate()` 的调用顺序。
- [Android 17 `ZygoteProcess.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/ZygoteProcess.java)：`startViaZygote()` 与 Zygote 请求路径。
- [Android 17 `Context.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/Context.java)：`MODE_MULTI_PROCESS` 的废弃说明与跨进程限制。
- [Processes and threads overview](https://developer.android.com/guide/components/processes-and-threads)：组件进程、Binder 线程与 Provider 调用规则。
- [`Application` API reference](https://developer.android.com/reference/android/app/Application)：`getProcessName()` 与 `onCreate()` 生命周期边界。
- [Bound services overview](https://developer.android.com/develop/background-work/services/bound-services)：绑定生命周期与跨进程服务调用。
- [`ServiceConnection` API reference](https://developer.android.com/reference/android/content/ServiceConnection)：断连、binding 失效和重新绑定要求。
- [`IBinder` API reference](https://developer.android.com/reference/android/os/IBinder)：同步事务、`linkToDeath()` 与死亡通知。
- [`ApplicationStartInfo` API reference](https://developer.android.com/reference/android/app/ApplicationStartInfo)：启动原因、进程名、组件和时间戳。
- [Memory management overview](https://developer.android.com/topic/performance/memory-management)：PSS、RSS 与 Android 内存统计口径。
- [Handle WebView termination](https://developer.android.com/develop/ui/views/layout/webapps/handle-termination)：renderer process 退出与宿主恢复边界。
- [App Startup](https://developer.android.com/topic/libraries/app-startup)：initializer 依赖、自动初始化和手动初始化。
- [App startup time](https://developer.android.com/topic/performance/vitals/launch-time)：TTID、TTFD 与启动测量边界。
