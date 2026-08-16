---
title: "Compose Compiler、Runtime Tracing 与重组诊断"
chapter: "22.22"
status: finalized
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-08-15"
last_verified_against: "Kotlin 与 Compose 编译器插件 2.4.10；Compose Runtime、UI 与 Runtime Tracing 1.12.0；BOM 2026.08.00；报告样本固定为 Kotlin 2.3.20"
confidence: high
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
tags: [compose, compiler, recomposition, diagnostics, stability, perfetto, ci]
related_chapters: ["22.3", "7.7"]
sources:
  - type: official
    path: "https://developer.android.com/develop/ui/compose/performance/stability/diagnose"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/performance/stability/fix"
  - type: official
    path: "https://kotlinlang.org/docs/releases.html"
  - type: official
    path: "https://kotlinlang.org/docs/compose-compiler-options.html"
  - type: official
    path: "https://plugins.gradle.org/plugin/org.jetbrains.kotlin.plugin.compose/2.4.10"
  - type: source
    path: "https://github.com/JetBrains/kotlin/releases/tag/v2.4.10"
  - type: source
    path: "https://github.com/JetBrains/kotlin/blob/v2.4.10/plugins/compose/compiler-hosted/src/main/java/androidx/compose/compiler/plugins/kotlin/BuildMetrics.kt"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/compose-runtime#1.12.0"
  - type: official
    path: "https://dl.google.com/dl/android/maven2/androidx/compose/runtime/runtime-tracing/1.12.0/runtime-tracing-1.12.0-sources.jar"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Recomposer.kt"
  - type: official
    path: "https://dl.google.com/dl/android/maven2/androidx/compose/compose-bom/2026.08.00/compose-bom-2026.08.00.pom"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/tooling/tracing"
previous_sources:
  # 旧版元数据值原样保留，便于追溯迁移前的来源配置。
  - "developer.android.com/develop/ui/compose/performance/stability/diagnose"
  - "developer.android.com/develop/ui/compose/performance/stability/fix"
  - "developer.android.com/jetpack/androidx/releases/compose-compiler"
  - "developer.android.com/jetpack/compose/compiler"
consolidated_from:
  - "src/part5-app/ch22-rendering-practice/22.40-compose-compiler-v2-k2-migration-performance.md"
  - "src/part5-app/ch22-rendering-practice/37-compose-runtime-tracing-perfetto-integration.md"
---

# Compose Compiler、Runtime Tracing 与重组诊断

Compose 性能排查常把三类证据混在一起：编译器生成了什么代码、运行时执行了哪些组合函数、用户看到的帧是否按时显示。三类证据各自回答一个问题，不能互相代替。

可复现的诊断链路如下：

1. 用 Compose 编译器报告检查稳定性推断、重启组和可跳过性。
2. 用 Layout Inspector 观察目标交互期间的重组与跳过计数。
3. 用 Composition Tracing 在系统跟踪中定位组合函数的执行区间。
4. 用 FrameTimeline 和 Macrobenchmark 判断这些工作是否造成可感知慢帧。

## 核查口径与版本锚点

配置、输出格式和运行时行为按以下版本核查：

| 层级 | 固定锚点 | 使用范围 |
| --- | --- | --- |
| Android 平台 | Android 17 / API 37 / `android-17.0.0_r1` | `Choreographer`、`ViewRootImpl`、FrameTimeline、RenderThread、SurfaceFlinger |
| Android 内核 | `android17-6.18-2026-06_r6` | 调度、唤醒和同步栅栏等内核证据 |
| Kotlin / Compose 编译器插件 | 2.4.10 稳定版 | 当前项目配置与插件选项 |
| Compose Runtime / UI / Runtime Tracing | 1.12.0 稳定版 | 重组、运行时跟踪与 UI 执行行为 |
| 报告样本 | Kotlin 2.3.20 | 固定的最小源码、报告文本与 CI 解析器输入 |

Compose 编译器从 Kotlin 2.0 起随 Kotlin 一同发布，`org.jetbrains.kotlin.plugin.compose` 的版本必须与 Kotlin 插件一致。Compose 库独立于 Android 平台发布；API 37 不会自动决定项目使用哪个 Compose 版本。当前 BOM `2026.08.00` 将 `runtime-tracing` 与 Runtime 约束为 1.12.0。

文中的 2.3.20 代码块和报告输出是一组固定实验样本，保留它们才能逐字复现 CSV、JSON 和标签解释；新项目应把 Kotlin 与 Compose 插件同时设为 2.4.10。两版 `BuildMetrics.kt` 的 CSV 表头和模块 JSON 键相同，但 CI 仍要记录编译器版本与 `featureFlags`，因为字段相同不代表代码生成行为完全相同。

## 一、先分清四层证据

| 证据 | 能回答的问题 | 不能据此断言的结论 |
| --- | --- | --- |
| `classes.txt`、`composables.txt`、CSV | 编译器如何推断类型稳定性；函数是否生成重启组、是否允许跳过 | 某函数在设备上重组了多少次；一次重组耗时多少 |
| `module.json` | 当前编译任务的模块级代码生成统计和功能开关 | 页面是否流畅；某个函数是否是热点 |
| Layout Inspector | 连接期间，界面节点观察到的重组与跳过计数 | 发布构建的精确耗时；线上用户的慢帧比例 |
| Composition Tracing、FrameTimeline | 组合函数何时执行、执行多久；帧是否错过截止时间 | 类型为什么被判为 `unstable`；改动后代码生成是否发生变化 |

“`unstable` 数量下降”属于静态证据，“重组次数下降”属于运行时证据，“慢帧下降”才对应用户结果。优化结论至少应包含一项静态证据和一项运行时证据。

## 二、按 Kotlin 2.3.20 生成编译器报告

### 1. 用固定版本复现报告样本

下面的根项目配置把 Kotlin 与 Compose 编译器插件都固定为 2.3.20，用于复现本文的报告样本。当前项目应把两处版本一同改为 2.4.10。

```kotlin
plugins {
    id("org.jetbrains.kotlin.android") version "2.3.20" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.3.20" apply false
}
```

这两行的要点是版本必须相同，而不是继续采用 2.3.20。如果项目通过版本目录管理插件，Kotlin Android 插件和 Compose 插件也应引用同一个 Kotlin 版本。

下面的模块配置用于启用 Compose 编译器报告，并把报告与模块指标分开存放。

```kotlin
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

composeCompiler {
    reportsDestination =
        layout.buildDirectory.dir("compose_compiler/reports")
    metricsDestination =
        layout.buildDirectory.dir("compose_compiler/metrics")
}
```

`reportsDestination` 生成函数和类型级报告，`metricsDestination` 生成模块级 JSON。旧文章中常见的自定义 `-P composeCompilerReportsDestination=...`，只有在项目脚本主动读取该属性时才有效；Compose 插件没有提供这个通用 Gradle 参数。

### 2. 固定构建变体和编译输入

官方诊断文档建议使用发布构建生成报告。团队基线还应固定 Kotlin 版本、Compose 插件配置、模块、构建变体、代码压缩设置和源码提交；不同输入得到的数量不能直接比较。

下面的命令用于重新编译应用模块的 Release 变体，也就是准备发布时使用的构建配置。

```bash
./gradlew :app:clean :app:assembleRelease
```

`clean` 可避免把旧编译任务留下的报告误当成本次结果。大型工程可以清理目标模块的输出目录并执行对应编译任务，无须每次清空全仓库缓存。

下面的命令用于确认实际生成的文件，而不是假定某个固定的变体子目录。

```bash
find app/build/compose_compiler -type f -print | sort
```

Kotlin Gradle 插件会按编译目标和编译单元（compilation）组织部分指标目录，多模块工程也会产生不同文件前缀。CI 应从构建产物中发现文件，再按模块和变体归档。

### 3. Kotlin 2.3.20 样本的输出文件

`reportsDestination` 会生成这些文件：

| 文件 | 内容 |
| --- | --- |
| `*-classes.txt` | 类型及属性的稳定性推断 |
| `*-composables.txt` | 组合函数标签、参数稳定性、组与调用信息 |
| `*-composables.csv` | 便于机器处理的组合函数表 |
| `*-composables.log` | 仅在编译器记录相关日志消息时出现 |

`metricsDestination` 产生 `*-module.json`。Kotlin 2.3.20 的 JSON 包含 `totalComposables`、`skippableComposables`、`restartableComposables`、各类参数和类统计，以及本次编译的 `featureFlags`。这个字段记录各项编译器功能开关是否启用，是解释其他数字的必要条件。

Kotlin 2.4.10 的 `BuildMetrics.kt` 仍输出相同的 CSV 表头和模块 JSON 键，本文的解析器可以读取这两个版本。2.4.10 同时修正了 Compose 稳定性推断：部分过去报告为 `stable` 的类会改为运行时稳定性或 `Uncertain`。解析器可复用不代表旧基线数值可以沿用；升级后必须重新生成报告，解释标签变化，再更新 CI 基线。

## 三、用固定样本读懂报告标签

### 1. 测试源码

下面的最小样例用于同时覆盖稳定参数、不稳定集合、显式禁止跳过和非 `Unit` 返回值。

```kotlin
package lab

import androidx.compose.runtime.Composable
import androidx.compose.runtime.NonSkippableComposable

data class Snack(
    val id: Long,
    val tags: Set<String>,
)

@Composable
fun StableParameters(
    count: Int,
    title: String,
) {
}

@Composable
fun UnstableList(
    snacks: List<Snack>,
    onClick: (Long) -> Unit,
) {
    if (snacks.isNotEmpty()) {
        StableParameters(
            count = snacks.size,
            title = snacks.first().id.toString(),
        )
        onClick(snacks.first().id)
    }
}

@NonSkippableComposable
@Composable
fun ExplicitlyNonSkippable(
    count: Int,
) {
}

@Composable
fun NonUnitResult(
    count: Int,
): Int = count
```

`Set` 和 `List` 的声明类型无法证明底层实现不可变，因此 `Snack` 和 `snacks` 会进入不稳定路径。函数类型由编译器按稳定类型处理。

### 2. `composables.txt` 的实测输出

Kotlin 2.3.20 在默认功能开关下为上述样例生成以下关键记录。

```text
restartable skippable fun lab.StableParameters(
  unused stable count: Int
  unused stable title: String
)
restartable skippable fun lab.UnstableList(
  unstable snacks: List<Snack>
  stable onClick: Function1<Long, Unit>
)
restartable fun lab.ExplicitlyNonSkippable(
  unused stable count: Int
)
fun lab.NonUnitResult(
  stable count: Int
): Int
```

各标签应逐项解读：

- `restartable`：编译器为该函数建立可独立重新执行的组合组；组是 Compose 记录调用身份和状态读取的运行时单元。
- `skippable`：父级重组调用到这里时，运行时允许在参数满足比较规则后跳过函数体。
- `stable`、`unstable`：参数类型的编译期稳定性分类。
- `unused`：参数没有被该函数生成的组合逻辑读取。
- 没有 `restartable`：该函数不构成可独立重启的组合边界。非 `Unit` 返回值就是一种常见原因。

`UnstableList` 同时出现 `unstable snacks` 和 `skippable` 并不矛盾。Strong Skipping（强跳过模式）从 Kotlin 2.0.20 起默认启用，它让所有可重启组合函数都可以生成跳过逻辑；参数稳定性只决定运行时采用哪种比较方式。这项规则在当前 Kotlin 2.4.10 中仍然成立。

`ExplicitlyNonSkippable` 仍是 `restartable`，但 `@NonSkippableComposable` 阻止编译器为它生成 `skippable` 标签。报告中不存在 `@NonSkippableOptIn` 这一注解。

### 3. `classes.txt` 的实测输出

同一编译任务对 `Snack` 产生以下记录。

```text
unstable class lab.Snack {
  stable val id: Long
  unstable val tags: Set<String>
  <runtime stability> = Unstable
}
```

`val` 只能保证引用不能重新赋值，不能保证引用指向的对象不可变。`Set<String>` 是接口，运行时对象仍可能是可变集合，所以编译器无法证明它不可变。

### 4. CSV 与模块 JSON 的准确含义

Kotlin 2.3.20 的 CSV 表头如下。

```text
package,name,composable,skippable,restartable,readonly,inline,isLambda,hasDefaults,defaultsGroup,groups,calls,
```

布尔列使用 `1` 和 `0`，CSV 没有名为 `params` 的列。表头虽然把第一列命名为 `package`，Kotlin 2.3.20 与 2.4.10 的源码写入的都是 `fn.fqName`，即函数的完全限定名；实测值形如 `lab.UnstableList`。解析脚本若按 `true`、`false`、`params` 或“纯包名”编写，都会得到错误结果。

样例的 `module.json` 记录了以下功能开关。

```json
{
  "featureFlags": {
    "StrongSkipping": true,
    "IntrinsicRemember": true,
    "OptimizeNonSkippingGroups": true,
    "PausableComposition": true
  }
}
```

`featureFlags` 是解释报告不可缺少的构建条件。相同源码关闭 Strong Skipping 后，样例中的 `UnstableList` 会从 `restartable skippable` 变为 `restartable`。CI 比较报告前必须先确认开关一致。

## 四、Strong Skipping 怎样改变诊断方式

### 1. 稳定参数与不稳定参数使用不同相等规则

运行时决定是否跳过函数时会比较本次和上次参数：

- 稳定参数使用对象相等，即 `equals()`。
- 不稳定参数使用引用相等，即 `===`。
- 所有参数均满足各自的“未变化”条件时，函数体才会被跳过。

这组规则带来两个容易漏掉的边界。

传入一个内容相同但新创建的 `List`，引用不同，`UnstableList` 仍会重组。每次在调用点执行 `items.map { ... }` 或 `items.toList()`，都可能制造新容器。

把普通 `MutableList` 原地修改后继续传入同一引用，引用比较可能允许跳过；普通集合的修改又不会通知 Snapshot 系统，界面可能保留旧内容。解决方向是不可变 UI 模型、可观察的 Snapshot 状态或明确的新值流转，不能靠虚假稳定性注解遮住可变对象。

### 2. Lambda 会被自动记住

Lambda 是可以作为值传递的函数表达式；它引用外部变量时，这些变量称为捕获值。Strong Skipping 会自动记住组合函数内部的 Lambda，编译器根据捕获值生成近似 `remember(...)` 的逻辑：不稳定捕获使用引用相等，稳定捕获使用对象相等。

少数需要每次创建新 Lambda 的场景可以使用 `@DontMemoize`。需要保持可重启、但每次父级重组都执行函数体的场景可以使用 `@NonSkippableComposable`。两个注解都用于表达明确语义，不适合作为常规性能开关。

### 3. `skippable` 不等于一定跳过

报告中的 `skippable` 表示“允许跳过”。函数是否被跳过还取决于：

- 对应重启组是否进入本轮重组；
- 参数比较结果；
- 调用位置和组合身份是否保持；
- 读取的 Snapshot 状态是否让该作用域失效；
- 控制流和键值是否改变了组结构。

因此，不能用 CSV 中 `skippable=1` 计算运行时跳过率。跳过次数需要运行时工具观察。

## 五、稳定性是一项代码契约

### 1. `@Stable` 的三项要求

类型标记为 `@Stable` 后，开发者向编译器承诺：

1. 同一对实例的 `equals` 结果保持不变。
2. 公共属性发生变化时，Compose 会收到通知。
3. 所有公共属性类型也满足稳定性要求。

`@Immutable` 的承诺更强：实例构造完成后，可观察状态不会变化，公开方法也不会破坏这一假设。注解不会把可变实现改造成可观察状态；违反契约可能导致应当执行的重组被跳过。给类型加注解前，要验证实现符合这些条件。

### 2. 集合与跨模块模型

标准库的 `List`、`Set`、`Map` 都是接口，Compose 编译器按不稳定类型处理。常用处理方式包括：

- 在 UI 边界转换为持久不可变集合；
- 用满足不可变契约的包装类型承载集合；
- 把变化数据放入 `State`、`SnapshotStateList` 或明确的状态流；
- 在不含 Compose 编译器的模型模块外，再定义 UI 专用模型。

持久不可变集合在更新时返回新实例，旧实例保持不变，适合跨越 UI 边界。外部类型经过团队审计并满足稳定契约后，可以通过稳定性配置文件告知编译器。下面的配置把一份明确的类型清单加入当前模块。

```kotlin
composeCompiler {
    stabilityConfigurationFiles.add(
        rootProject.layout.projectDirectory.file("stability_config.conf")
    )
}
```

`stabilityConfigurationFiles` 是当前复数形式的 API；单数 `stabilityConfigurationFile` 已弃用。配置文件只改变编译器判断，不会验证第三方类型的线程安全、可变性或通知机制，清单必须附带审计依据。

下面的配置文件条目用于声明一个经过审计的具体类型。

```text
com.example.model.ImmutableFromAnotherModule
```

优先列出精确类型。大范围通配符会把后续新增类型一并视为稳定，代码评审很难发现契约已经失效。

### 3. 不要追求“全部可跳过”

非 `Unit` 返回值、显式 `@NonSkippableComposable`、不可重启函数和部分内联结构本来就不应生成相同的跳过代码。可跳过性还会增加少量代码体积。

静态检查应关注“与基线相比为什么变化”，不应设置“所有组合函数必须 `skippable`”的门禁。修复优先级由运行时热点、调用频率、参数分配和帧结果共同决定。

## 六、Layout Inspector 观察次数

Android Studio Layout Inspector 可以显示组合节点的重组次数和跳过次数。它适合回答以下问题：

- 哪个界面区域在目标交互期间反复重组；
- 状态读取是否放在过高层级；
- 参数身份是否在父层频繁变化；
- 修复前后，同一操作脚本下的计数是否收敛。

使用时应固定设备、页面初始状态和交互步骤，并在每轮采样前重置计数。Inspector 是诊断环境，会增加观测开销；计数只用于定位范围。精确耗时应由允许性能分析（profileable）且关闭调试（non-debuggable）的构建，通过系统跟踪和基准测试确认。

计数高也不自动等于问题。一个很小的计时文本可以高频重组且成本很低；一个只执行一次的组合函数也可能同步解析大对象并阻塞一帧。排查顺序应把次数与单次成本、作用域大小和帧截止时间放在一起看。

## 七、Composition Tracing 定位运行时间

### 1. 加入 Runtime Tracing 依赖

普通系统跟踪默认不包含每个组合函数。下面的依赖坐标固定为 1.11.4，用于复现旧实验；它展示的是构件名称，不是当前推荐版本。

```kotlin
dependencies {
    implementation("androidx.compose.runtime:runtime-tracing:1.11.4")
}
```

当前项目应使用 `androidx.compose.runtime:runtime-tracing:1.12.0`。若已经导入 Compose BOM `2026.08.00`，依赖可以省略版本号；该 BOM 同样映射到 1.12.0。Composition Tracing 要求采集设备至少为 API 30，Android 17 / API 37 满足这个条件。

Kotlin 2.4.10 的 Compose 插件仍默认注入组合跟踪标记和源码信息。跟踪标记是编译器插入的区间起止调用；项目若显式关闭 `includeTraceMarkers`，即使加入运行时依赖，也不会得到完整的逐函数信息。

### 2. 使用可分析的构建

下面的 Manifest 片段允许 shell 工具分析关闭调试的 Release 性能构建。

```xml
<application
    android:debuggable="false">
    <profileable android:shell="true" />
</application>
```

`non-debuggable` 保留发布构建的优化与运行方式，`profileable` 则允许 shell 和受信任工具在不打开调试器的情况下采集性能数据。Debug 构建的额外检查、调试器和编译差异会改变耗时，不能作为发布性能结论。

### 3. 正确阅读系统跟踪

加入 `runtime-tracing` 后，系统跟踪会显示带函数名、文件和行号信息的组合切片。切片表示线程上从开始标记到结束标记的一段时间。Compose Runtime 1.12.0 源码仍包含 `Recomposer:animation`、`Recomposer:recompose` 等内部区间。

这些名称不是稳定 API。团队查询应先打开当前版本的跟踪数据确认切片名称，再保存针对该版本的查询；不能假设所有版本都存在固定的 `Compose:measure`、`Compose:layout`、`Compose:draw` 或 `Compose:recompose` 切片组合。

组合函数切片只覆盖组合阶段的相关执行。Compose UI 的测量、布局和绘制属于后续阶段，可能由不同跟踪标记表达。某个组合函数耗时后，还要检查它是否触发布局、绘制和 RenderThread 工作，不能把四个阶段合并成一个“重组耗时”。

1.12.0 的运行时依赖通过 `ComposeTracingInitializer` 安装 `CompositionTracer`，再把编译器传入的 `info` 写入 `PerfettoSdkTrace.beginSection(info)`。函数名来自编译器标记，因此缺少依赖或关闭标记时不会出现逐函数切片。

### 4. 控制采集成本

组合函数名和源码信息会增加 APK 体积，逐函数跟踪也会增加采集数据量。诊断构建应保留与生产一致的优化设置，只增加必要的 `profileable` 与跟踪能力。

从终端启用完整的 Perfetto SDK 跟踪时，还可能需要 `androidx.tracing:tracing-perfetto` 和对应的二进制依赖。官方明确警告不要把 `tracing-perfetto-binary` 发布到生产包。日常排查优先使用 Android Studio System Trace 或 Macrobenchmark 自动采集，减少配置差异。

## 八、把重组放回 Android 17 渲染流水线

在 Android 17 标准应用窗口路径中，一次可见更新大致经过：

```text
vsync-app
  -> Choreographer#doFrame
  -> Compose 重组 / 测量 / 布局 / 绘制记录
  -> RenderThread
  -> BufferQueue / BLAST 提交缓冲
  -> SurfaceFlinger 合成
  -> HWC / 显示控制器
  -> present
```

这条路径用于标出责任边界。Compose 的组合优化主要减少应用主线程生成 UI 更新的工作，无法直接证明 RenderThread、GPU、SurfaceFlinger 或显示硬件已经按时完成。

诊断时可以按以下证据相互核对：

1. FrameTimeline 标出目标交互中的慢帧，并区分 App 与 SurfaceFlinger 侧截止时间。
2. 主线程轨道检查 `Choreographer#doFrame`、`Recomposer:recompose` 和目标组合函数切片。
3. 若应用主线程按时完成，继续检查 RenderThread、GPU、BufferQueue、SurfaceFlinger 和同步栅栏；同步栅栏用于表示前一项图形工作何时完成。
4. 用同一用户操作的 Macrobenchmark 比较修复前后帧指标。

`queueBuffer` 只说明应用提交了一个缓冲，不代表该缓冲已经显示。评估用户结果要看 FrameTimeline 与最终呈现时刻相关的证据。

Android 内核锚点 `android17-6.18-2026-06_r6` 只用于解释线程为什么没有及时运行、唤醒是否延迟、同步栅栏是否阻塞等现象。内核跟踪不认识 Compose 的稳定性标签，编译器报告也无法解释 CPU 为什么有一段时间没有调度目标线程。跨层结论必须用时间戳关联两类证据。

## 九、从状态写入追到重组作用域

一条可靠的重组因果链应包含：

```text
状态写入
  -> Snapshot 变化被应用
  -> 读取该状态的组合作用域失效
  -> Recomposer 在帧时钟中处理待办工作
  -> 参数比较与跳过判断
  -> 必要的组合函数重新执行
  -> 节点更新可能触发测量、布局或绘制
```

状态写入不保证产生可见重组。等价写入可能被 `SnapshotMutationPolicy` 忽略；没有组合读取者的状态也不会让界面作用域失效。相反，把频繁变化的状态读取放在页面根部，会让更大的作用域进入重组判断，即使很多子函数随后被跳过。

排查调用点时重点检查：

- 是否在组合期间反复创建集合、包装对象或 Lambda；
- 状态读取能否下移到只需要它的节点；
- Lazy 列表的键值和内容类型是否稳定；
- `remember` 的键值是否准确描述缓存生命周期；
- `derivedStateOf` 是否只在“输入变化频率高于派生结果变化频率”时使用；
- 普通可变对象是否绕过 Snapshot 通知。

报告指出参数类型，Layout Inspector 指出作用域，系统跟踪指出耗时。把三类证据对齐后再改代码，比看到 `unstable` 就添加注解更容易找到实际原因。

## 十、CI 中保存可解释的语义快照

### 1. 记录原始产物与构建条件

这里的“语义快照”指某次固定编译产生的原始报告、统计结果和构建条件，与运行时 Snapshot 无关。它让代码评审可以判断标签变化来自业务代码、编译选项还是工具升级。

每个基线至少应保存：

- Kotlin 与 Compose 插件版本；
- Compose Runtime / UI 版本；
- 模块、编译目标（target）、编译单元（compilation）与构建变体；
- `module.json` 的 `featureFlags`；
- 原始 `classes.txt`、`composables.txt`、CSV 和 module JSON；
- 源码提交及生成命令；
- 对应 Macrobenchmark 或系统跟踪样本标识。

只提交一个“unstable 数量”会丢失函数身份、原因和编译开关，后续无法判断变化来自业务代码还是工具升级。

### 2. 严格解析当前格式

下面的 Python 脚本校验 Kotlin 2.3.20 的 CSV 表头和布尔编码，并生成便于代码评审的确定性快照。2.4.10 源码沿用相同字段，因此脚本也能读取当前版本；版本号与功能开关仍需作为独立门禁。

```python
#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path

EXPECTED_HEADER = [
    "package",
    "name",
    "composable",
    "skippable",
    "restartable",
    "readonly",
    "inline",
    "isLambda",
    "hasDefaults",
    "defaultsGroup",
    "groups",
    "calls",
    "",
]

MODULE_KEYS = [
    "skippableComposables",
    "restartableComposables",
    "readonlyComposables",
    "totalComposables",
    "restartGroups",
    "totalGroups",
    "markedStableClasses",
    "inferredStableClasses",
    "inferredUnstableClasses",
    "inferredUncertainClasses",
    "effectivelyStableClasses",
    "totalClasses",
    "memoizedLambdas",
    "totalLambdas",
]

BOOLEAN_COLUMNS = [
    "composable",
    "skippable",
    "restartable",
    "readonly",
    "inline",
    "isLambda",
    "hasDefaults",
    "defaultsGroup",
]


def relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def read_csv(path: Path, root: Path) -> dict:
    with path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != EXPECTED_HEADER:
            raise ValueError(
                f"{path}: unsupported CSV header: {reader.fieldnames}"
            )
        rows = list(reader)

    for row in rows:
        for column in BOOLEAN_COLUMNS:
            if row[column] not in {"0", "1"}:
                raise ValueError(
                    f"{path}: {column} must use 0/1, got {row[column]!r}"
                )

    non_skippable_restartable = sorted(
        row["package"]
        for row in rows
        if row["composable"] == "1"
        and row["restartable"] == "1"
        and row["skippable"] == "0"
    )
    return {
        "file": relative(path, root),
        "total_rows": len(rows),
        "skippable": sum(int(row["skippable"]) for row in rows),
        "restartable": sum(int(row["restartable"]) for row in rows),
        "non_skippable_restartable": non_skippable_restartable,
    }


def read_module(path: Path, root: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = [key for key in MODULE_KEYS if key not in data]
    if "featureFlags" not in data:
        missing.append("featureFlags")
    if missing:
        raise ValueError(f"{path}: missing fields: {missing}")
    return {
        "file": relative(path, root),
        "metrics": {key: data[key] for key in MODULE_KEYS},
        "featureFlags": dict(sorted(data["featureFlags"].items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.build_root.resolve()
    csv_files = sorted(root.rglob("*-composables.csv"))
    module_files = sorted(root.rglob("*-module.json"))
    if not csv_files or not module_files:
        raise SystemExit("compiler reports or module metrics were not found")

    snapshot = {
        "csv": [read_csv(path, root) for path in csv_files],
        "modules": [read_module(path, root) for path in module_files],
    }
    args.output.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
```

脚本在表头变化时直接失败，避免 Kotlin 升级后继续产出看似正常的错误统计。它列出“可重启但不可跳过”的函数供评审，不把这类函数自动判为失败。

下面的命令用于从应用构建目录生成快照。

```bash
python3 tools/compose_metrics_snapshot.py \
  --build-root app/build/compose_compiler \
  --output app/build/compose-compiler-snapshot.json
```

示例假设团队把脚本保存为 `tools/compose_metrics_snapshot.py`。输出仍是诊断产物；是否阻断合入应由项目基线、函数变化原因和运行时回归共同决定。

### 3. 合理的门禁规则

适合自动阻断的情况包括：

- Kotlin 或 Compose 插件版本变化，但基线没有显式升级；
- `featureFlags` 与基线不一致；
- 报告格式变化而解析器尚未适配；
- 已列入关键路径观察名单的函数发生非预期标签变化；
- Macrobenchmark 的帧指标超过项目在目标设备上建立的回归预算。

不适合使用统一阈值的情况包括：

- 模块中 `unstable` 类型比例超过某个任意百分比；
- 出现任意一个不可跳过函数；
- 单次组合函数切片超过固定的 1 ms 或 8 ms；
- 编译器指标改善，但没有运行时验证。

帧预算受刷新率、设备性能、热状态和同一帧其他工作影响。项目应围绕关键用户旅程（Critical User Journey，CUJ），例如冷启动、打开会话和滚动列表，在受控实验中建立各自阈值；不存在适用于所有设备的统一常数。

## K2 / Compose Compiler 迁移：先固定构建语义

Kotlin 2.0 起，Compose 编译器随 Kotlin 一同发布，项目应应用与 Kotlin 完全同版本的 `org.jetbrains.kotlin.plugin.compose`。K2 负责 Kotlin 源码的前端解析和语义分析；Compose 编译器插件仍负责改写 `@Composable` 参数、生成组合组、生成记录参数变化的掩码（change mask）、记住 Lambda，并注入跟踪标记。K2 本身不承诺自动改善 Compose UI 的运行时性能。

迁移时应删除旧 `androidx.compose.compiler:compiler` 依赖、`kotlinCompilerExtensionVersion` 和重复的 `freeCompilerArgs` 插件参数，再在 Compose DSL 中配置报告目录、指标目录和稳定性配置文件。Android 17 / targetSdk 37 不决定 Kotlin 或 Compose 编译器版本；AGP 内置 Kotlin 支持、kapt/KSP 注解处理和 Compose Multiplatform 也要分别核对兼容性表。

增量编译性能可用 Gradle Profiler 或可重复脚本分别测量全量构建、无改动构建、单个 Kotlin 文件变更、公共模型变更和资源变更。实验要固定 Gradle、AGP、Kotlin、JDK、守护进程与 JVM 参数、配置缓存、远程缓存和机器负载，并保存构建扫描或任务失效原因。一次 IDE 构建面板中的主观感受不能证明 K2 或 Compose 插件改善了构建速度。

编译成功也不等于运行时性能改善。迁移前后应使用同一业务代码、Release/R8 设置、Baseline Profile、设备与用户旅程，比较启动时间和帧耗时分位数。编译器报告只能解释代码生成属性，不能推导重组次数或帧截止时间。值类（value class）、Kotlin 元数据、R8、Live Edit 与 kapt 故障属于构建兼容问题，应单独记录，不能混入 Compose 帧归因。

## Runtime Tracing 的采集与解释边界

`runtime-tracing` 通过 AndroidX Startup 安装全局跟踪器，把编译器注入的可组合函数标记送到 Perfetto SDK。激活跟踪器只让进程具备写入能力，录制会话（session）才决定何时收集数据。终端采集时，目标进程要成功加载匹配的 `tracing-perfetto` 二进制库，跟踪配置还要订阅用于记录应用事件的 `track_event` 数据源；完整渲染调查还需要 FrameTimeline、内核调度事件（ftrace/sched）、图形与 View 事件、RenderThread 和 SurfaceFlinger 数据源。

诊断产物应允许性能分析并关闭调试。`tracing-perfetto-binary` 会明显增加体积，只应放进基准测试或诊断变体；通过 adb 广播激活 `TracingReceiver` 需要 `android.permission.DUMP`，普通线上应用不能把它当作远程开关。API 35 及以上的 `ProfilingManager` 可以请求受限且经过隐私删减的系统跟踪，但能否看到逐个可组合函数，仍取决于目标构建是否保留标记、运行时跟踪是否激活，不能自动替代 Runtime Tracing 的配置要求。

一条可组合函数切片表示同一线程上的同步区间。`dur` 是切片从开始到结束的墙钟时间，既包含线程正在运行（Running）的时间，也包含已经就绪但等待 CPU（Runnable）和阻塞的时间。父切片包含子切片，所有包含耗时（`inclusive duration`）不能直接相加；分析时应按名称、线程和时间筛选候选，再统计出现次数，分别计算包含耗时与扣除直接子切片后的自耗时（`self time`）。切片能证明函数在该时间窗执行过，但不能直接指出哪个 State 导致失效，也不覆盖布局、绘制、RenderThread 或 GPU 工作。

可靠的排查顺序是：用 FrameTimeline 定位异常帧，在主线程对齐组合切片、状态或业务标记、测量、布局和绘制，再检查线程状态、垃圾回收、Binder 与 I/O；若 UI 线程按时完成，则继续查看 RenderThread、缓冲区、SurfaceFlinger 与最终呈现。线上应用性能监控（APM）用于筛选页面、设备和操作样本组（cohort）。完整跟踪包含源码位置、线程和用户操作时序，采集系统必须设置配额、保留期、访问控制和隐私策略。

## 十一、逐个问题的诊断流程

1. 定义可重复的用户操作，例如打开会话列表并滚动三屏。
2. 用 Macrobenchmark 或 FrameTimeline 确认该操作存在慢帧，并保存设备、温度、刷新率和构建信息。
3. 用 Layout Inspector 缩小反复重组的界面范围。
4. 用 Composition Tracing 找到耗时的组合函数及其调用层级。
5. 查阅 `composables.txt` 和 `classes.txt`，确认函数标签与参数稳定性。
6. 回到调用点检查对象身份、状态读取位置、键值、集合转换和 Lambda 捕获。
7. 只修改一个主要变量，再用相同脚本复测计数、系统跟踪和帧结果。
8. 更新编译器语义快照，并记录变化为何符合预期。

若 FrameTimeline 显示应用侧按时完成，排查应转向 RenderThread、GPU、SurfaceFlinger 和同步栅栏。继续修改稳定性通常不会解决合成侧或显示侧瓶颈。

## 十二、常见误判

| 误判 | 准确口径 |
| --- | --- |
| `unstable` 参数使函数一定无法跳过 | Kotlin 2.3.20 与当前 2.4.10 都默认启用 Strong Skipping；可重启函数仍可跳过，不稳定参数用 `===` 比较 |
| `skippable` 证明运行时已经跳过 | 它只表示编译器生成了跳过能力 |
| 编译器 CSV 包含重组次数和参数列表 | Kotlin 2.3.20 CSV 不包含运行时次数，也没有 `params` 列 |
| 同内容的新 `List` 会按元素比较后跳过 | 声明为不稳定参数时比较容器引用，不做逐元素相等判断 |
| 给类加 `@Stable` 就完成优化 | 注解是开发者契约；违反通知或相等约束会造成界面错误 |
| 系统跟踪默认显示每个组合函数 | 需要 `runtime-tracing`、编译器跟踪标记和支持的采集方式 |
| `Compose:measure/layout/draw` 是所有版本固定切片 | 跟踪名称属于具体库实现，应按当前版本的真实数据核对 |
| 重组计数下降就证明帧性能改善 | 仍需 FrameTimeline 或 Macrobenchmark 验证用户结果 |
| 内核调度记录能解释稳定性 | 内核只提供线程运行、唤醒和同步证据，不包含 Compose 类型语义 |

这些误判都把证据用到了它回答不了的问题上：静态报告不能代替运行时计数，组合切片不能代替整帧结果，内核调度也不能解释类型稳定性。

## 十三、核查清单

### 编译配置

- [ ] Kotlin Android 插件与 `org.jetbrains.kotlin.plugin.compose` 使用同一版本。
- [ ] 报告由固定的 Release 变体生成。
- [ ] 归档模块、编译目标、编译单元、提交和 `featureFlags`。
- [ ] Kotlin 升级时重新验证 CSV 与 JSON 格式。

### 静态报告

- [ ] 区分 `restartable`、`skippable` 与参数稳定性。
- [ ] 没有把 `skippable` 当成实际跳过次数。
- [ ] 对集合、跨模块类型和稳定性配置做契约审计。
- [ ] 没有为追求统计数字给可变类型添加虚假注解。

### 运行时

- [ ] Layout Inspector 使用相同交互脚本和重置后的计数。
- [ ] 系统跟踪来自允许性能分析且关闭调试的构建。
- [ ] Composition Tracing 依赖和编译器跟踪标记均已启用。
- [ ] 组合、测量、布局、绘制和提交/显示没有混为一段。

### 结果验证

- [ ] FrameTimeline 指明慢帧责任侧。
- [ ] Macrobenchmark 覆盖目标用户操作。
- [ ] 修复前后使用相同设备条件与构建设置。
- [ ] CI 门禁比较同版本、同开关、同模块的基线。

## 源码与资料索引

- [Kotlin 发布记录：当前稳定版 2.4.10](https://kotlinlang.org/docs/releases.html)
- [Kotlin 2.4.10 发行说明](https://github.com/JetBrains/kotlin/releases/tag/v2.4.10)
- [Compose 编译器插件 2.4.10](https://plugins.gradle.org/plugin/org.jetbrains.kotlin.plugin.compose/2.4.10)
- [Diagnose stability issues](https://developer.android.com/develop/ui/compose/performance/stability/diagnose)
- [Fix stability issues](https://developer.android.com/develop/ui/compose/performance/stability/fix)
- [Strong skipping mode](https://developer.android.com/develop/ui/compose/performance/stability/strongskipping)
- [Lifecycle of composables：稳定性契约](https://developer.android.com/develop/ui/compose/lifecycle#skipping)
- [Composition tracing](https://developer.android.com/develop/ui/compose/tooling/tracing)
- [Compose compiler options DSL](https://kotlinlang.org/docs/compose-compiler-options.html)
- [Kotlin 2.4.10 `BuildMetrics.kt`](https://github.com/JetBrains/kotlin/blob/v2.4.10/plugins/compose/compiler-hosted/src/main/java/androidx/compose/compiler/plugins/kotlin/BuildMetrics.kt)
- [Kotlin 2.3.20 `BuildMetrics.kt`](https://github.com/JetBrains/kotlin/blob/v2.3.20/plugins/compose/compiler-hosted/src/main/java/androidx/compose/compiler/plugins/kotlin/BuildMetrics.kt)
- [Compose Runtime 1.12.0 release notes](https://developer.android.com/jetpack/androidx/releases/compose-runtime#1.12.0)
- [Runtime Tracing 1.12.0 sources.jar](https://dl.google.com/dl/android/maven2/androidx/compose/runtime/runtime-tracing/1.12.0/runtime-tracing-1.12.0-sources.jar)
- [Compose Runtime 1.12.0 `Recomposer.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Recomposer.kt)
- [BOM 2026.08.00 POM](https://dl.google.com/dl/android/maven2/androidx/compose/compose-bom/2026.08.00/compose-bom-2026.08.00.pom)
- [Compose Runtime 1.11.4 release notes](https://developer.android.com/jetpack/androidx/releases/compose-runtime#1.11.4)
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [Android 17 `Choreographer.java`](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/core/java/android/view/Choreographer.java)
- [Android 17 `ViewRootImpl.java`](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/core/java/android/view/ViewRootImpl.java)
- [Android 17 `FrameTimeline.java`](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/core/java/android/graphics/FrameTimeline.java)
- [Android common kernel `android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)
- [本知识库：Jetpack Compose 性能优化](03-compose-performance.md)
- [本知识库：Android 17 FrameTimeline](../../part1-fundamentals/ch02-rendering/30-android17-frametimeline-composition-boundary.md)

当前工具链与运行时结论核查于 2026-08-15。编译器报告样例来自 Kotlin 2.3.20 对最小源码的实测输出，2.4.10 源码核对用于确认 CSV 与模块 JSON 结构仍一致；升级 Kotlin 或 Compose 后，仍应重新生成报告并复核字段、功能开关与跟踪名称。
