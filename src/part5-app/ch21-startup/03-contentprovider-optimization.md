---
title: "ContentProvider 启动治理"
chapter: "21.3"
section: "21.3"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-10"
last_verified_against: "AOSP android-17.0.0_r1 ActivityThread/ViewTreeObserver, Android Developers App Startup / provider manifest docs, AndroidX Startup 1.2.0 source"
confidence: medium
sources:
  - type: aosp
    path: "AOSP android-17.0.0_r1 frameworks/base/core/java/android/app/ActivityThread.java"
  - type: aosp
    path: "AOSP android-17.0.0_r1 frameworks/base/core/java/android/view/ViewTreeObserver.java"
  - type: official
    path: "https://developer.android.com/topic/libraries/app-startup"
  - type: official
    path: "https://developer.android.com/guide/topics/manifest/provider-element"
  - type: official
    path: "https://developer.android.com/guide/topics/providers/content-provider-basics"
  - type: aosp
    path: "androidx.startup:startup-runtime:1.2.0 AppInitializer.java / InitializationProvider.java"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
tags: [contentprovider, startup, sdk-init, app-startup]
related_chapters: ["21.1", "21.2", "1.10"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---

# ContentProvider 启动治理

## 范围

ContentProvider 有两种角色：对外提供结构化数据，或借组件自动创建完成“免接入”初始化。这里聚焦第二种角色及其对启动的影响，不展开 CRUD、`CursorWindow` 和 Provider ANR。

平台源码锚点为 Android 17 / API 37 / `android-17.0.0_r1`，App Startup 固定到 1.2.0。

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

`data.providers` 是 system_server 为当前进程准备的 Provider 列表。Provider 属于哪个进程，由最终 Manifest 中的 `android:process` 决定；默认值是应用默认进程。

`installContentProviders()` 对列表逐个调用 `installProvider()`。本地 Provider 的关键路径是：

1. 通过应用的 `AppComponentFactory` 实例化 Provider 类；
2. 调用 `ContentProvider.attachInfo(...)`；
3. `attachInfo(...)` 内设置权限、authority 等信息；
4. 在 hosting process 的主线程调用 `ContentProvider.onCreate()`；
5. 将已经安装的 holder 汇总后，一次调用 `publishContentProviders(...)` 发布给 system_server。

Provider 多时会增加类加载、实例化、`attachInfo()` 和各自 `onCreate()` 的成本，但不要误写成“每个 Provider 都单独 publish 一次 Binder”。Android 17 的该路径把当前批次 holder 放在一个列表中发布。

### 1.2 初始化顺序

同一进程的 Provider 可以用 `android:initOrder` 声明相对实例化顺序，数值高的先初始化。它只能表达静态先后关系：

- 不能让 `onCreate()` 异步；
- 不能表达完成结果、失败或降级；
- 不能解决跨进程依赖；
- 不能缩短各 Provider 的工作；
- Manifest 中元素的书写顺序不是依赖契约。

需要完整任务依赖时，应使用 App Startup 的同步依赖图，或 [启动框架设计与任务编排](./02-startup-framework.md)中的显式任务框架。

### 1.3 App 埋点为什么容易漏掉

很多项目从 `Application.onCreate()` 第一行开始计时。Provider 已经在此前完成，因此这类埋点只能看到 Application 阶段，无法解释完整 `bindApplication` 时间。

启动基线应以 Macrobenchmark 的端到端 TTID/TTFD 和 Perfetto 的 Android App Startups 窗口为主，再用自定义切片分解自有 Provider。

## 2. 启动成本从哪里来

Provider 框架本身并非唯一成本。一次自动初始化通常包含四层：

| 层次 | 常见工作 | 需要的证据 |
| --- | --- | --- |
| 组件固定成本 | 类加载、构造、`attachInfo()`、authority 注册 | Framework/App 主线程 Trace |
| `onCreate()` 负载 | 文件、数据库、反射、SDK 初始化、native load | 自定义 slice、方法栈、I/O |
| 资源竞争 | worker 抢 CPU/I/O、锁、Binder 等待、GC | sched、thread state、Binder、GC |
| 进程成本 | 远端 Provider 触发目标进程启动与发布 | system_server 和两个进程的 Trace |

几个常见误判：

- `.onCreate()` 很快，不代表它创建的 worker 不会与首帧争用资源。
- 看到某个 Provider 类，不代表它的全部成本都归属框架；要进入供应商或业务实现。
- 删除一个 Provider 后 TTID 下降，不足以证明固定组件成本很高；也可能是其业务初始化一起被删除。
- 远端 Provider 不会因主进程启动自动出现在主进程。主进程同步访问其 authority 时，可能触发 hosting process 创建并等待发布。

Provider 数量可以作为审计入口，不能直接换算成毫秒。

## 3. 从 release Manifest 建立清单

### 3.1 检查最终合并结果

源码 Manifest 不是发布事实。库、渠道、build type、product flavor 和 manifest placeholder 都会改变最终组件。

Android Gradle Plugin 的合并决策报告位于模块的 `build/outputs/logs/manifest-merger-<variant>-report.txt`。Android Studio 的 Merged Manifest 视图也能定位某个 Provider 来自哪个依赖。检查准备发布的每个 variant，而非只看 debug。

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

脚本的输入应是构建工具生成的可读 XML，不是 APK 中经过编译的二进制 XML。中间产物路径会随 AGP 变化，应从当前构建输出或 Android Studio 获取，不要把某个 AGP 版本的 `intermediates` 路径固化到工具中。

### 3.2 每个 Provider 要记录什么

| 字段 | 核对内容 |
| --- | --- |
| 身份 | 类名、authority、来源 artifact、精确版本 |
| 构建 | 哪些 variant 出现、由哪条 merge 规则引入 |
| 进程 | `android:process` 与 `<application android:process>` 的合并结果 |
| 顺序 | `initOrder` 及是否存在静态依赖 |
| 生命周期 | enabled、directBootAware、是否会在用户解锁前运行 |
| 安全 | exported、read/write permission、URI grant、path permission |
| 工作 | `onCreate()` 同步工作、worker、注册项、磁盘和网络 |
| 必要性 | TTID 前、TTFD 前、功能首用或未使用 |
| 运维 | 显式 init API、停止/禁用、回退和供应商联系人 |

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

这个 slice 的持续时间是同步 `onCreate()` 时间。若 `installMinimalState()` 只提交 worker，必须在 worker 端继续记录排队、运行和逻辑完成；Provider slice 结束不能代表初始化已就绪。

开发阶段还可用 StrictMode 捕获自有代码的主线程磁盘/网络，但它不是生产耗时指标，也不一定覆盖 native 或供应商内部全部访问。

### 4.2 第三方 Provider

闭源 Provider 无法增加切片时，使用组合证据：

1. 从 merged Manifest 和 merge report 锁定类与来源版本。
2. 在 Perfetto 的 `bindApplication` 窗口看主线程栈、I/O、Binder 和类加载。
3. 生成只改变该 Provider 自动入口的 A/B release 产物。
4. 在 B 产物的等价场景显式初始化同一 SDK，分开测量“组件固定成本”和“SDK 业务成本”。
5. 重复冷启动，比较分布和 Trace，不用单次差值。

如果供应商不允许关闭自动初始化，要求其提供诊断构建、Trace 或源码说明。不要通过反射跳过私有方法，这会把升级风险带进启动关键路径。

### 4.3 观察跨进程等待

主进程调用 `ContentResolver` 获取远端 authority 时，ActivityThread 可能向 system_server 请求 Provider，并等待 hosting process 发布。诊断时同时看：

- 调用进程的 Binder/等待状态；
- system_server 的 provider 获取和进程启动；
- hosting process 的 bind、Provider `onCreate()` 和 publish；
- 超时、死亡与重试。

调用方线程若是 Main，这段等待会直接进入 UI 关键路径。远端进程并不会让同步访问自动变快。

## 5. 按用户可见边界分类

不要给 Provider 统一规定 5 ms 或 50 ms。准入预算应从应用的 TTID/TTFD SLO、当前余量、设备档位和入口推导。

| 类别 | 判断 | 处理 |
| --- | --- | --- |
| 未使用 | 业务没有调用且组件仅由依赖默认注入 | 移除，并做功能/构建回归 |
| TTID 前必要 | 首个应用帧缺少它就无法正确生成 | 只保留最小同步状态，设置明确失败路径 |
| TTFD 前必要 | 第一帧可先出现，主要操作仍需等待 | 移出 Provider，进入任务图 |
| 功能首用 | 分享、地图、支付、广告等特定入口才需要 | 单次按需初始化 |
| 延后维护 | 日志整理、上传、预取等 | 在页面可用后按资源预算调度 |

“Crash SDK 必须最早”“远程配置必须首帧前”等结论也要拆分。Crash 捕获、历史日志整理、符号上传可以是不同阶段；远程配置通常可先使用本地可信快照。

分类完成后，每个任务都要有 owner、完成条件、失败结果和验证场景。没有这些契约，挪出 Provider 只会把隐式时序问题移到别处。

## 6. 从 Manifest 删除自动入口

### 6.1 优先使用供应商开关

供应商若提供官方的 manifest placeholder 或 Gradle 开关，应优先使用。它通常会同时调整 Provider、metadata 和 SDK 内部状态。

没有开关时，可以在高优先级应用 Manifest 中使用 merge marker。下面的规则按 Provider 类名移除下游库声明：

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

Manifest merger 对 `<provider>` 的匹配键是 `android:name`。如果只想影响某个库，可在理解 merge 来源后使用 `tools:selector`，但仍要检查最终结果。

### 6.2 删除后的验证

至少验证：

- release、debug、渠道、动态特性等相关变体；
- merged Manifest 和 merger report 已无目标节点；
- SDK 显式初始化只执行一次；
- deep link、推送、后台任务、登录、分享、支付等入口；
- 用户同意、拒绝、撤回与无网路径；
- direct boot、备份恢复、升级安装和进程重建；
- Java mapping、native symbols 和监控仍可用。

若 Provider 对外提供 content URI，删除它属于 API/数据共享变更，不是单纯性能优化。还要检查调用方、权限、URI grant 和历史数据迁移。

`tools:node="remove"` 只改变合并结果，不会阻止供应商以后换类名或新增另一个 Provider。SDK 升级必须重新做 Manifest 差异。

## 7. 显式初始化的状态机

按需初始化至少包含这些状态：

```text
NotStarted → Initializing → Ready
                   ├──────→ Degraded
                   └──────→ Failed
```

并发调用应共享同一个 `Initializing` 结果，不能重复启动；调用者可以挂起或注册回调，不要在 Main 用锁或 `Future.get()` 阻塞等待。

状态机还要定义：

- SDK 是否要求 Main 调用；
- 异步回调何时代表逻辑可用；
- 超时是否能协作取消；
- 晚到结果是否允许写状态；
- 失败是否缓存、何时重试；
- 用户撤回同意后如何停止与清理；
- 进程重建后如何恢复。

不能笼统地把 SDK 初始化丢进 I/O 线程。有些 SDK 明确要求 Main，有些初始化同时包含 Main 注册和 worker 准备，应拆成有依赖的两个任务。

## 8. “首帧后”需要说明观测点

`OnPreDrawListener` 在 draw 之前执行，`View.post()` 也只表示 Runnable 进入 Main 消息队列。两者都不能证明帧已提交。

适用范围从 API 29 开始。硬件渲染页面可以用 `registerFrameCommitCallback()` 在下一帧提交到 swap chain 后触发延后任务：

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

`doOnPreDraw` 在本轮绘制前注册回调。硬件路径的 callback 表示帧已提交到 swap chain，仍不等于像素已经显示；软件渲染 fallback 只保证工作排到当前 traversal 之后。代码还需处理 Activity 销毁、重复注册和取消。

延后任务可能与下一帧交互争用 CPU/I/O。调度后仍要用 FrameTimeline、TTID/TTFD 和真实交互场景验证。若任务是“主要内容可用”的必要条件，应进入 TTFD 图，而非 `DEFERRED`。

## 9. App Startup 1.2.0 的准确边界

### 9.1 它减少的是入口，不是业务工作

[Jetpack App Startup](https://developer.android.com/topic/libraries/app-startup) 让多个组件共享一个 `InitializationProvider`，并用 `Initializer.dependencies()` 声明顺序。相比每个 SDK 各带一个 Provider，它减少了 Provider 类、实例和 `onCreate()` 入口，也让依赖关系集中。

App Startup 仍基于 ContentProvider。Manifest 发现过程和所有 `Initializer.create()` 在 Provider 安装阶段同步运行，不会自动进入 worker，也不会删除 SDK 内部的磁盘、锁或网络成本。

1.2.0 `AppInitializer` 的核心行为是：

- 从 `InitializationProvider` metadata 发现入口 initializer；
- 反射构造 initializer；
- 深度优先执行依赖；
- 用 `initializing` 集合检测环；
- 缓存已经初始化的结果；
- 给发现过程和 initializer 增加 Trace section。

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

不需要 eager 的 initializer，应从最终 Manifest 删除对应 metadata：

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

`initializeComponent()` 会在调用线程同步初始化该组件及未完成的依赖。调用方必须满足所有 initializer 的线程契约，不能因为“手动”就默认安全地从任意 worker 调用。

官方文档还指出，关闭某个组件的自动初始化会同时关闭由它带入的依赖。迁移时应画出完整依赖图，避免另一个入口仍然 eager 初始化同一依赖。

## 10. 多进程与 Direct Boot

### 10.1 Provider 属于 hosting process

最终 Manifest 决定 Provider 在哪个进程创建。每个进程拥有独立 heap、类静态字段和 App Startup 单例：

- 默认 Provider 只随应用默认进程安装；
- `android:process=":push"` 的 Provider 在私有 `:push` 进程运行；
- 显式把 InitializationProvider 声明到多个进程，会形成多份独立初始化结果；
- 一个进程不能依赖另一个进程的静态 `initialized` 布尔值。

进程选择应尽量在 Manifest/构图阶段完成。进入 initializer 后才按进程名 return，已经可能支付类加载和静态初始化成本。

### 10.2 Direct Boot

`android:directBootAware="true"` 允许 Provider 在用户解锁前运行。此时只能依赖 device-protected storage 和 Direct Boot 可用能力。不要为了提早初始化随意打开该属性；凭据加密存储、用户数据和依赖它们的 SDK 在此阶段不可用。

### 10.3 `multiprocess` 与重复实例

Manifest 的 `android:multiprocess="true"` 允许在调用进程创建 Provider 实例，会增加实例与状态一致性复杂度。不要把它当作减少 Binder 延迟的通用启动优化。迁移前要核对旧应用是否依赖这项少见行为，并用目标 API 37 设备验证。

## 11. 性能优化不能破坏 Provider 安全

每个保留或迁移的 Provider 还要检查：

- authority 是否唯一且使用 applicationId 前缀；
- `android:exported` 是否显式符合共享需求；
- read/write permission 与 path permission；
- URI grant 的授予和撤回；
- 组件是否只在必要用户/进程启用；
- `call()`、`openFile()` 和批处理接口是否暴露越权操作。

将外部 Provider 改成应用内 singleton，或把 remote Provider 改到主进程，都可能改变安全边界、故障隔离和内存成本。它们需要单独设计，不能只看 TTID。

## 12. 验收标准

| 验收项 | 需要的证据 |
| --- | --- |
| 组件清单 | 每个 release Provider 有来源、版本、进程、用途和 owner |
| Manifest | 所有目标 variant 的合并结果和差异 |
| 启动 | 冷启动 TTID/TTFD 分布与回归样本 Trace |
| Provider 阶段 | bind 内同步成本、worker 竞争和跨进程等待 |
| 功能 | 各入口、同意状态、无网、升级、进程重建 |
| 多进程 | 每个进程只执行必要图，跨进程失败可降级 |
| 安全 | exported、权限、authority 和 URI grant 复核 |
| 运维 | 显式 init、禁用、回退和 SDK 升级检查 |

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
- [Android `<provider>` manifest 元素](https://developer.android.com/guide/topics/manifest/provider-element)
- [Manifest 合并规则](https://developer.android.com/build/manage-manifests)
- [Jetpack App Startup](https://developer.android.com/topic/libraries/app-startup)
- [Jetpack Startup 1.2.0 源码包](https://dl.google.com/dl/android/maven2/androidx/startup/startup-runtime/1.2.0/startup-runtime-1.2.0-sources.jar)
- [`ViewTreeObserver.registerFrameCommitCallback`](https://developer.android.com/reference/android/view/ViewTreeObserver)
