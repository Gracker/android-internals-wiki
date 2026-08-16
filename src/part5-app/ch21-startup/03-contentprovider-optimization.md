---
title: "ContentProvider 启动治理"
chapter: "21.3"
section: "21.3"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "AOSP android-17.0.0_r1 ActivityThread/ContentProvider/ContentProviderRecord/ViewTreeObserver, current Android Developers provider/Direct Boot/manifest docs, AndroidX Startup 1.2.0 latest stable source"
confidence: medium-high
sources:
  - type: aosp
    path: "AOSP android-17.0.0_r1 frameworks/base/core/java/android/app/ActivityThread.java"
  - type: aosp
    path: "AOSP android-17.0.0_r1 frameworks/base/core/java/android/content/ContentProvider.java"
  - type: aosp
    path: "AOSP android-17.0.0_r1 frameworks/base/services/core/java/com/android/server/am/ContentProviderRecord.java"
  - type: aosp
    path: "AOSP android-17.0.0_r1 frameworks/base/core/java/android/view/ViewTreeObserver.java"
  - type: official
    path: "https://developer.android.com/topic/libraries/app-startup"
  - type: official
    path: "https://developer.android.com/guide/topics/manifest/provider-element"
  - type: official
    path: "https://developer.android.com/guide/topics/providers/content-provider-basics"
  - type: official
    path: "https://developer.android.com/privacy-and-security/direct-boot"
  - type: aosp
    path: "androidx.startup:startup-runtime:1.2.0 AppInitializer.java / InitializationProvider.java"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
tags: [contentprovider, startup, sdk-init, app-startup]
related_chapters: ["21.1", "21.2", "1.10"]
pipeline_stage: finalized
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---

# ContentProvider 启动治理

## 范围

在本文关心的场景里，ContentProvider 常见于两类用途：通过 `content://` URI 提供结构化数据，或借系统自动创建组件的时机完成“零代码接入”初始化。这里聚焦后一类及其启动成本，不展开数据增删改查（CRUD）、承载部分游标结果的 `CursorWindow`，也不讨论 Provider 响应超时引发的 ANR（应用无响应）。

平台源码锚点为 Android 17 / API 37 / `android-17.0.0_r1`。截至 2026-08-14，App Startup 1.2.0 仍是最新稳定版，本文的库行为固定到该版本。

## 1. Provider 为什么早于 `Application.onCreate()`

### 1.1 Android 17 的调用顺序

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

### 1.2 初始化顺序

同一进程中、未启用 `android:multiprocess` 的 Provider 可以用 `android:initOrder` 声明相对实例化顺序，数值高的先初始化。这个属性只能表达静态先后关系：

- 不能让 `onCreate()` 异步；
- 不能表达完成结果、失败或降级；
- 不能解决跨进程依赖；
- 不能缩短各 Provider 的工作；
- Manifest 中元素的书写顺序不是依赖契约。

需要完整任务依赖时，应使用 App Startup 的同步依赖图，或 [启动框架设计与任务编排](./02-startup-framework.md)中的显式任务框架。

### 1.3 App 埋点为什么容易漏掉

很多项目从 `Application.onCreate()` 第一行开始计时。Provider 已经在此前完成，因此这类埋点只能看到 Application 阶段，无法解释完整的 `bindApplication`：这是系统把应用信息、组件和 `Application` 绑定到新进程的启动阶段。

启动基线应以 Macrobenchmark 自动化基准测试得到的端到端 TTID/TTFD 为主：TTID 表示首帧首次显示所需时间，TTFD 表示应用达到完整可用状态所需时间。再结合 Perfetto 系统 Trace 的 Android App Startups 区间和自定义 slice；slice 是 Trace 上带开始、结束时间的命名区间，可用于分解自有 Provider。

## 2. 启动成本从哪里来

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

## 3. 从 release Manifest 建立清单

### 3.1 检查最终合并结果

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

### 3.2 每个 Provider 要记录什么

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

## 4. 如何测量 Provider 成本

### 4.1 自有 Provider

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

### 4.2 第三方 Provider

闭源 Provider 无法增加切片时，使用组合证据：

1. 从合并后的 Manifest 和合并报告锁定类与来源版本。
2. 在 Perfetto 的 `bindApplication` 窗口看主线程栈、I/O、Binder 和类加载。
3. 生成一对 release 构建产物，唯一差异是是否保留该 Provider 自动入口。
4. 在移除自动入口的产物中，于等价场景显式初始化同一 SDK，分开测量“组件固定成本”和“SDK 业务成本”。
5. 重复冷启动，比较分布和 Trace，不用单次差值。

如果供应商不允许关闭自动初始化，应要求其提供诊断构建、Trace 或源码说明。通过反射跳过私有方法会依赖未公开实现，SDK 升级后很容易失效，不应把这种风险带进启动关键路径。

### 4.3 观察跨进程等待

主进程通过 `ContentResolver` 获取远端 authority 时，`ActivityThread` 可能向 `system_server` 请求 Provider，并等待承载进程完成发布。诊断时同时看：

- 调用进程的 Binder/等待状态；
- `system_server` 的 Provider 获取和进程启动；
- 承载进程的进程绑定、Provider `onCreate()` 和发布；
- 超时、死亡与重试。

调用方线程若是 Main，这段等待会直接进入 UI 关键路径。远端进程并不会让同步访问自动变快。

## 5. 按用户可见边界分类

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

## 6. 从 Manifest 删除自动入口

### 6.1 优先使用供应商开关

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

### 6.2 删除后的验证

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

## 7. 显式初始化的状态机

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

## 8. “首帧后”需要说明观测点

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

## 9. App Startup 1.2.0 的准确边界

### 9.1 它减少的是入口，不是业务工作

[Jetpack App Startup](https://developer.android.com/topic/libraries/app-startup) 让多个组件共享一个 `InitializationProvider`，并用 `Initializer.dependencies()` 声明顺序。相比每个 SDK 各带一个 Provider，它减少了 Provider 类、实例和 `onCreate()` 入口，也让依赖关系集中。[1.2.0 发布说明](https://developer.android.com/jetpack/androidx/releases/startup) 显示它截至 2026-08-14 仍是最新稳定版。

App Startup 仍基于 ContentProvider。Manifest 发现过程和所有 `Initializer.create()` 在 Provider 安装阶段同步运行，不会自动进入后台线程，也不会删除 SDK 内部的磁盘、锁或网络成本。

1.2.0 `AppInitializer` 的核心行为是：

- 从 `InitializationProvider` 的 Manifest metadata 键值配置中发现入口 initializer；
- 通过反射按运行期类名构造 initializer；
- 深度优先执行依赖；
- 用 `initializing` 集合检测环；
- 缓存已经初始化的结果；
- 给发现过程和 initializer 增加 Trace 时间区间。

### 9.2 自动初始化

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

### 9.3 手动初始化

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

## 10. 多进程与 Direct Boot

### 10.1 Provider 属于承载进程

最终 Manifest 决定 Provider 在哪个承载进程创建。每个进程拥有独立的 Java heap（对象内存区）、类静态字段和 App Startup 单例：

- 默认 Provider 只随应用默认进程安装；
- `android:process=":push"` 的 Provider 在私有 `:push` 进程运行；
- 显式把 InitializationProvider 声明到多个进程，会形成多份独立初始化结果；
- 一个进程不能依赖另一个进程的静态 `initialized` 布尔值。

进程选择应尽量在 Manifest 或构图阶段完成。进入 initializer 后才按进程名提前返回，此前已经可能发生类加载和静态字段初始化。

### 10.2 Direct Boot

[`android:directBootAware="true"`](https://developer.android.com/privacy-and-security/direct-boot) 允许 Provider 在设备重启后、用户首次解锁前运行。此时只能访问 device-protected storage（设备保护存储）和其他支持 Direct Boot 的能力；默认的 credential-encrypted storage（凭据加密存储）要等用户解锁后才可用。该属性适用于闹钟、短信等确有解锁前需求的组件，不能用作普通的“提前初始化”开关，也不能在设备保护存储中随意保存口令或认证令牌。

### 10.3 `multiprocess` 与同 UID 多实例

Manifest 的 `android:multiprocess="true"` 允许系统在同一 UID（Linux 用户 ID，Android 用它隔离应用身份）的其他进程中本地创建 Provider 实例，通常对应应用自己的子进程。Android 17 的 [`ContentProviderRecord.canRunHere()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ContentProviderRecord.java) 同时检查 `multiprocess` 和 UID；不同 UID 的外部应用仍通过 Binder 访问承载进程中的实例。

本地实例可以省去应用自身进程间的部分 Binder 调用，却会复制对象、缓存和连接，并要求各实例解决状态一致性。它不适合作为通用启动优化。迁移前要核对旧应用是否依赖这项少见行为，并在目标 API 37 设备上验证。

## 11. 性能优化不能破坏 Provider 安全

每个保留或迁移的 Provider 还要检查：

- authority 是否唯一且使用 applicationId 前缀；
- `android:exported` 是否显式符合共享需求，也就是是否允许其他应用访问；
- 整个 Provider 的读写权限，以及只约束部分 URI 路径的 path permission；
- 临时 URI 访问授权的授予和撤回；
- 组件是否只在必要用户/进程启用；
- `call()`、`openFile()` 和批处理接口是否暴露越权操作，例如绕过查询权限读取文件或执行管理命令。

将外部 Provider 改成应用进程内单例，或把远端 Provider 改到主进程，都可能改变安全边界、故障隔离和内存成本。这类迁移需要单独设计，不能只看 TTID。

## 12. 验收标准

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
