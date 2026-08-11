---
title: "Compose Compiler、Runtime Tracing 与重组诊断"
chapter: "22.22"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-07-01"
last_verified_against: "Compose BOM 2026.06.00, Kotlin 2.2, Compose Compiler Gradle Plugin"
confidence: high
drafted_date: "2026-07-01"
tags: [compose, compiler, recomposition, diagnostics, stability, perfetto, ci]
related_chapters: ["22.3", "7.7"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "章节深挖+官方文档"
gap_score: 17
sources:
  - type: official
    path: "developer.android.com/develop/ui/compose/performance/stability/diagnose"
  - type: official
    path: "developer.android.com/develop/ui/compose/performance/stability/fix"
  - type: official
    path: "developer.android.com/jetpack/androidx/releases/compose-compiler"
  - type: official
    path: "developer.android.com/jetpack/compose/compiler"
consolidated_from:
  - "src/part5-app/ch22-rendering-practice/22.40-compose-compiler-v2-k2-migration-performance.md"
  - "src/part5-app/ch22-rendering-practice/37-compose-runtime-tracing-perfetto-integration.md"
---

# Compose Compiler、Runtime Tracing 与重组诊断

Compose 性能排查容易混淆三类证据：编译器生成了什么代码、运行时执行了哪些组合函数、用户看到的帧是否按时显示。它们分别回答不同问题，不能互相代替。

可复现的诊断链路如下：

1. 用 Compose 编译器报告检查稳定性推断、重启组和可跳过性。
2. 用 Layout Inspector 观察目标交互期间的重组与跳过计数。
3. 用 Composition Tracing 在系统 Trace 中定位组合函数的执行区间。
4. 用 FrameTimeline 和 Macrobenchmark 判断这些工作是否造成可感知慢帧。

## 核查口径与版本锚点

配置、输出格式和运行时行为按以下版本核查：

| 层级 | 固定锚点 | 使用范围 |
| --- | --- | --- |
| Android 平台 | Android 17 / API 37 / `android-17.0.0_r1` | `Choreographer`、`ViewRootImpl`、FrameTimeline、RenderThread、SurfaceFlinger |
| Android kernel | `android17-6.18-2026-06_r6` | 调度、唤醒和 fence 等底层证据 |
| Kotlin | 2.3.20 | Compose 编译器及 Gradle 插件版本 |
| Compose Runtime / UI | 1.11.4 稳定版 | 重组、运行时 Trace 与 UI 执行行为 |

Compose 编译器从 Kotlin 2.0 起随 Kotlin 一同发布，`org.jetbrains.kotlin.plugin.compose` 的版本必须与 Kotlin 插件一致。Compose 库独立于 Android 平台发布；API 37 不会自动决定项目使用哪个 Compose 版本。

版本演进资料可以比较旧版行为。这里的配置、报告字段和示例输出只对上表中的当前锚点作保证。

## 一、先分清四层证据

| 证据 | 能回答的问题 | 不能据此断言的结论 |
| --- | --- | --- |
| `classes.txt`、`composables.txt`、CSV | 编译器如何推断类型稳定性；函数是否生成重启组、是否允许跳过 | 某函数在设备上重组了多少次；一次重组耗时多少 |
| `module.json` | 当前编译任务的模块级代码生成统计和功能开关 | 页面是否流畅；某个函数是否是热点 |
| Layout Inspector | 连接期间，界面节点观察到的重组与跳过计数 | Release 包的精确耗时；线上用户的慢帧比例 |
| Composition Tracing、FrameTimeline | 组合函数何时执行、执行多久；帧是否错过截止时间 | 类型为什么被判为 `unstable`；改动后代码生成是否发生变化 |

因此，“`unstable` 数量下降”只是静态信号，“重组次数下降”是运行时信号，“慢帧下降”才是用户结果。优化结论至少应包含一项静态证据和一项运行时证据。

## 二、按 Kotlin 2.3.20 生成编译器报告

### 1. 应用与 Kotlin 同版本的 Compose 插件

下面的根项目配置用于锁定 Kotlin 与 Compose 编译器插件版本。

```kotlin
plugins {
    id("org.jetbrains.kotlin.android") version "2.3.20" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.3.20" apply false
}
```

两个插件均使用 `2.3.20`。如果项目通过版本目录管理插件，约束仍然相同：Kotlin Android 插件和 Compose 插件引用同一个 Kotlin 版本。

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

`reportsDestination` 生成函数和类型级报告，`metricsDestination` 生成模块级 JSON。旧文章中常见的自定义 `-P composeCompilerReportsDestination=...` 只有在项目脚本主动读取该属性时才有效，它不是 Compose 插件提供的通用 Gradle 参数。

### 2. 固定构建变体和编译输入

官方诊断文档建议使用 Release 构建生成报告。团队基线还应固定 Kotlin 版本、Compose 插件配置、模块、变体、代码压缩设置和源码提交；混用不同输入得到的数量没有可比性。

下面的命令用于重新编译应用模块的 Release 变体。

```bash
./gradlew :app:clean :app:assembleRelease
```

`clean` 可避免把旧编译任务留下的报告误当成本次结果。大型工程可以清理目标模块的输出目录并执行对应编译任务，无须每次清空全仓库缓存。

下面的命令用于确认实际生成的文件，而不是假定某个固定的变体子目录。

```bash
find app/build/compose_compiler -type f -print | sort
```

Kotlin Gradle 插件会按目标和 compilation 组织部分指标目录，多模块工程也会产生不同文件前缀。CI 应从构建产物中发现文件，再按模块和变体归档。

### 3. Kotlin 2.3.20 的输出文件

`reportsDestination` 可产生以下文件：

| 文件 | 内容 |
| --- | --- |
| `*-classes.txt` | 类型及属性的稳定性推断 |
| `*-composables.txt` | 组合函数标签、参数稳定性、组与调用信息 |
| `*-composables.csv` | 便于机器处理的组合函数表 |
| `*-composables.log` | 仅在编译器记录相关日志消息时出现 |

`metricsDestination` 产生 `*-module.json`。Kotlin 2.3.20 的 JSON 包含 `totalComposables`、`skippableComposables`、`restartableComposables`、各类参数和类统计，以及本次编译的 `featureFlags`。

这些文件是编译器实现的诊断接口，不是跨版本不变的公共数据协议。升级 Kotlin 时应先检查字段和语义，再更新 CI 解析器与基线。

## 三、用一份实测报告读懂标签

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

- `restartable`：编译器为该函数建立可独立重新执行的重启边界。
- `skippable`：父级重组调用到这里时，运行时允许在参数满足比较规则后跳过函数体。
- `stable`、`unstable`：参数类型的编译期稳定性分类。
- `unused`：参数没有被该函数生成的组合逻辑读取。
- 没有 `restartable`：该函数不构成可独立重启的组合边界。非 `Unit` 返回值就是一种常见原因。

`UnstableList` 同时出现 `unstable snacks` 和 `skippable` 并不矛盾。Kotlin 2.3.20 默认启用 Strong Skipping，所有可重启的组合函数都可以生成跳过逻辑；参数稳定性决定运行时采用哪种比较方式。

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

`val` 只能保证引用不能重新赋值，不能保证引用指向的对象不可变。`Set<String>` 是接口，运行时对象仍可能是可变集合，所以编译器不能把它证明为不可变。

### 4. CSV 与模块 JSON 的准确含义

Kotlin 2.3.20 的 CSV 表头如下。

```text
package,name,composable,skippable,restartable,readonly,inline,isLambda,hasDefaults,defaultsGroup,groups,calls,
```

布尔列使用 `1` 和 `0`，CSV 没有名为 `params` 的列。表头虽然把第一列命名为 `package`，Kotlin 2.3.20 源码写入的是 `fn.fqName`，实测值形如 `lab.UnstableList`。解析脚本若按 `true`、`false`、`params` 或“纯包名”编写，都会得到错误结果。

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

`featureFlags` 是解释报告不可缺少的上下文。相同源码关闭 Strong Skipping 后，样例中的 `UnstableList` 会从 `restartable skippable` 变为 `restartable`。CI 比较报告前必须先确认开关一致。

## 四、Strong Skipping 改变了诊断方式

### 1. 稳定参数与不稳定参数使用不同相等规则

运行时决定是否跳过函数时会比较本次和上次参数：

- 稳定参数使用对象相等，即 `equals()`。
- 不稳定参数使用引用相等，即 `===`。
- 所有参数均满足各自的“未变化”条件时，函数体才会被跳过。

这组规则带来两个容易漏掉的边界。

传入一个内容相同但新创建的 `List`，引用不同，`UnstableList` 仍会重组。每次在调用点执行 `items.map { ... }` 或 `items.toList()`，都可能制造新容器。

把普通 `MutableList` 原地修改后继续传入同一引用，引用比较可能允许跳过；普通集合的修改又不会通知 Snapshot 系统，界面可能保留旧内容。解决方向是不可变 UI 模型、可观察的 Snapshot 状态或明确的新值流转，不能靠虚假稳定性注解遮住可变对象。

### 2. Lambda 会被自动记忆

Strong Skipping 还会记忆组合函数内部的 Lambda。编译器按捕获值生成近似 `remember(...)` 的逻辑，其中不稳定捕获使用引用相等，稳定捕获使用对象相等。

需要每次创建新 Lambda 的少数场景可以使用 `@DontMemoize`。需要保持可重启、但每次父级重组都执行函数体的场景可以使用 `@NonSkippableComposable`。两者都是针对明确语义的控制手段，不适合作为常规性能开关。

### 3. `skippable` 不等于一定跳过

报告中的 `skippable` 表示“允许跳过”。函数是否被跳过还取决于：

- 对应重启组是否进入本轮重组；
- 参数比较结果；
- 调用位置和组合身份是否保持；
- 读取的 Snapshot 状态是否让该作用域失效；
- 控制流和 key 是否改变了组结构。

因此，不能用 CSV 中 `skippable=1` 计算运行时跳过率。跳过次数需要运行时工具观察。

## 五、稳定性是契约，不是消除警告的标签

### 1. `@Stable` 的三项要求

类型标记为 `@Stable` 后，开发者向编译器承诺：

1. 同一对实例的 `equals` 结果保持不变。
2. 公共属性发生变化时，Compose 会收到通知。
3. 所有公共属性类型也满足稳定性要求。

`@Immutable` 的承诺更强：实例构造完成后，可观察状态不会变化，公开方法也不会破坏这一假设。注解不会把可变实现改造成可观察状态；违反契约可能导致应当执行的重组被跳过。

### 2. 集合与跨模块模型

标准库的 `List`、`Set`、`Map` 都是接口，Compose 编译器按不稳定类型处理。常用处理方式包括：

- 在 UI 边界转换为持久不可变集合；
- 用满足不可变契约的包装类型承载集合；
- 把变化数据放入 `State`、`SnapshotStateList` 或明确的状态流；
- 在不含 Compose 编译器的模型模块外，再定义 UI 专用模型。

如果外部类型已经由团队审计并满足稳定契约，可以通过稳定性配置文件告知编译器。下面的配置用于把一份明确的类型清单加入当前模块。

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

静态治理应关注“与基线相比为什么变化”，而非设定“所有组合函数必须 skippable”的门禁。修复优先级由运行时热点、调用频率、参数分配和帧结果共同决定。

## 六、Layout Inspector 观察次数

Android Studio Layout Inspector 可以显示组合节点的重组次数和跳过次数。它适合回答以下问题：

- 哪个界面区域在目标交互期间反复重组；
- 状态读取是否放在过高层级；
- 参数身份是否在父层频繁变化；
- 修复前后，同一操作脚本下的计数是否收敛。

使用时应固定设备、页面初始状态和交互步骤，并在每轮采样前重置计数。Inspector 是诊断环境，会增加观测开销；计数用于定位范围，耗时与流畅度仍应由 profileable、non-debuggable 构建的 Trace 和基准测试确认。

计数高也不自动等于问题。一个很小的计时文本可以高频重组且成本很低；一个只执行一次的组合函数也可能同步解析大对象并阻塞一帧。排查顺序应把次数与单次成本、作用域大小和帧截止时间放在一起看。

## 七、Composition Tracing 定位运行时间

### 1. 单独加入运行时 Trace 依赖

普通系统 Trace 默认不包含每个组合函数。下面的依赖用于让 Compose 1.11.4 把编译器注入的组合信息写入 Perfetto SDK Trace。

```kotlin
dependencies {
    implementation("androidx.compose.runtime:runtime-tracing:1.11.4")
}
```

该能力要求采集设备至少为 API 30。验证目标为 Android 17 / API 37 设备，满足平台条件。若使用 BOM，应确认 BOM 实际映射的 `runtime-tracing` 版本；这里显式写出 `1.11.4` 以固定实验输入。

Kotlin 2.3.20 的 Compose 插件默认包含 Trace marker 和源码信息。项目若显式关闭 `includeTraceMarkers`，即使加入运行时依赖，也不会得到完整的逐函数信息。

### 2. 使用可分析的构建

下面的 Manifest 片段用于允许 shell 工具分析 Release 性能构建。

```xml
<application
    android:debuggable="false">
    <profileable android:shell="true" />
</application>
```

采集包应为 non-debuggable 且 profileable。Debug 构建的运行时检查、调试器和编译差异会污染耗时，不能作为发布性能结论。

### 3. 正确阅读 Trace

加入 `runtime-tracing` 后，系统 Trace 会显示带函数名、文件和行号信息的组合切片。Compose Runtime 1.11.4 源码还包含 `Recomposer:animation`、`Recomposer:recompose` 等内部区间。

这些名称不是稳定 API。团队查询应先打开当前版本 Trace 确认切片名称，再保存针对该版本的查询；不要假设所有版本都存在固定的 `Compose:measure`、`Compose:layout`、`Compose:draw` 或 `Compose:recompose` 切片组合。

组合函数切片只覆盖组合阶段相关执行。Compose UI 的测量、布局和绘制是后续阶段，可能由不同 Trace marker 表达。看到某个组合函数耗时后，还要检查它是否触发布局、绘制和 RenderThread 工作，不能把四个阶段合并成一个“重组耗时”。

运行时依赖通过 `ComposeTracingInitializer` 安装 `CompositionTracer`，再把编译器传入的 `info` 写入 `PerfettoSdkTrace.beginSection(info)`。这条源码路径说明函数名来自编译器 marker，也解释了缺少依赖或关闭 marker 时为何看不到逐函数切片。

### 4. 控制采集成本

组合函数名和源码信息会增加 APK 体积，逐函数 Trace 也会增加采集数据量。诊断构建应保留与生产一致的优化设置，只增加必要的 profileable 和 Trace 能力。

从终端启用完整 Perfetto SDK tracing 时，还可能需要 `androidx.tracing:tracing-perfetto` 和对应 binary 依赖。官方明确警告不要把 `tracing-perfetto-binary` 发布到生产包。日常排查优先使用 Android Studio System Trace 或 Macrobenchmark 自动采集，减少配置漂移。

## 八、把重组放回 Android 17 渲染流水线

在 Android 17 标准 App Window 路径中，一次可见更新大致经过：

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

这条链路用于标出责任边界。Compose 的组合优化主要减少应用主线程生成 UI 更新的工作，无法直接证明 RenderThread、GPU、SurfaceFlinger 或显示硬件已经按时完成。

诊断时可以按以下证据相互核对：

1. FrameTimeline 标出目标交互中的慢帧，并区分 App 与 SurfaceFlinger 侧截止时间。
2. 主线程轨道检查 `Choreographer#doFrame`、`Recomposer:recompose` 和目标组合函数切片。
3. 若应用主线程按时完成，继续检查 RenderThread、GPU、BufferQueue、SurfaceFlinger 和 fence。
4. 用同一用户操作的 Macrobenchmark 比较修复前后帧指标。

`queueBuffer` 只说明应用提交了一个缓冲，不代表该缓冲已经显示。评估用户结果要看 FrameTimeline 与 present 相关证据。

kernel 锚点 `android17-6.18-2026-06_r6` 只用于解释线程为什么没有及时运行、唤醒是否延迟、fence 是否阻塞等底层现象。kernel Trace 不认识 Compose 的稳定性标签；编译器报告也无法解释 CPU 调度空洞。跨层结论必须用时间戳把两类证据关联起来。

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
- Lazy 列表的 key 和内容类型是否稳定；
- `remember` 的 key 是否准确描述缓存生命周期；
- `derivedStateOf` 是否只在“输入变化频率高于派生结果变化频率”时使用；
- 普通可变对象是否绕过 Snapshot 通知。

报告能指出参数类型，Layout Inspector 能指出作用域，Trace 能指出耗时。三者合并后再改代码，命中率高于从 `unstable` 关键字直接开始加注解。

## 十、CI 中保存可解释的语义快照

### 1. 记录原始产物与构建上下文

每个基线至少应保存：

- Kotlin 与 Compose 插件版本；
- Compose Runtime / UI 版本；
- 模块、target、compilation 与构建变体；
- `module.json` 的 `featureFlags`；
- 原始 `classes.txt`、`composables.txt`、CSV 和 module JSON；
- 源码提交及生成命令；
- 对应 Macrobenchmark 或 Trace 样本标识。

只提交一个“unstable 数量”会丢失函数身份、原因和编译开关，后续无法判断变化来自业务代码还是工具升级。

### 2. 严格解析当前格式

下面的 Python 脚本用于校验 Kotlin 2.3.20 的 CSV 表头和布尔编码，并生成便于代码评审的确定性快照。

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

帧预算受刷新率、设备性能、热状态和同一帧其他工作影响。应从产品 CUJ 和受控实验建立项目阈值，文章无法给出适用于所有设备的常数。

## K2 / Compose Compiler 迁移：先固定构建语义

Kotlin 2.0 起 Compose compiler 随 Kotlin 一同发布，项目应应用与 Kotlin 完全同版本的 `org.jetbrains.kotlin.plugin.compose`。K2 是 Kotlin 前端/分析管线，Compose compiler plugin 仍负责 `@Composable` 的参数改写、组、change mask、lambda memoization 和 tracing marker；两者不能简化成“K2 自动优化 Compose UI”。

迁移时先删除旧 `androidx.compose.compiler:compiler` 依赖、`kotlinCompilerExtensionVersion` 和重复的 `freeCompilerArgs` 插件 option，再在 Compose DSL 中配置 reports、metrics、stability file 等选项。Android 17 / targetSdk 37 不决定 Kotlin 或 Compose compiler 版本；AGP built-in Kotlin、kapt/KSP 和 Compose Multiplatform 也要按各自兼容矩阵核对。

增量编译性能用 Gradle Profiler 或可重复脚本分别测 clean build、无改动 build、单 Kotlin 文件、公共 model 和资源变化。固定 Gradle/AGP/Kotlin/JDK、daemon/JVM 参数、配置缓存、远程缓存和机器负载，并保存 build scan 或 task 失效原因。一次 IDE Build 窗口的体感不能证明 K2 或 Compose plugin 带来收益。

编译成功也不等于运行时性能改善。迁移前后用同一业务代码、release/R8、Baseline Profile、设备与用户旅程比较启动和帧分位数；compiler reports 只能解释生成属性，不能推导重组次数或 frame deadline。value class、Kotlin metadata、R8、Live Edit 与 kapt 故障应作为构建兼容问题单独记录，不要混入 Compose 帧归因。

## Runtime Tracing 的采集与解释边界

`runtime-tracing` 通过 AndroidX Startup 安装全局 tracer，把 compiler 注入的 Composable marker 送到 Perfetto SDK。激活 tracer 与录制 session 是两件事：目标进程必须成功加载匹配的 `tracing-perfetto` binary，trace config 还要订阅 `track_event`；完整渲染调查另需 FrameTimeline、ftrace/sched、gfx/view、RenderThread 和 SurfaceFlinger 数据源。

诊断产物应保持 profileable、non-debuggable。`tracing-perfetto-binary` 会明显增加体积，只放 benchmark/diagnostic 变体；通过 adb 广播激活 `TracingReceiver` 需要 `android.permission.DUMP`，普通线上应用不能把它当远程开关。API 35+ 的 `ProfilingManager` 可以请求受限、隐私删减的 system trace，但是否包含逐个 Composable 仍取决于目标构建和 tracing 激活，不能自动替代 Runtime Tracing 协议。

一条 Composable slice 是同线程同步区间，`dur` 包含 Running、Runnable 与阻塞时间。父 slice 包含子 slice，所有 inclusive duration 不能直接相加；先按名称、线程和时间筛选候选，再计算 occurrence、inclusive 和扣除直接子 slice 的 self time。slice 能证明函数在该窗口执行过，不能直接给出哪一个 State 导致失效，也不能覆盖 Layout、Drawing、RenderThread 或 GPU。

可靠顺序是：FrameTimeline 锁定异常帧 → 主线程对齐 composition slice、状态/业务 marker、measure/layout/draw → 检查线程状态和 GC/Binder/I/O → UI 按时则继续 RenderThread、buffer、SF 与 present。线上 APM 负责筛选页面、设备和操作 cohort；完整 trace 涉及源码位置、线程和用户时序，必须有配额、保留期、访问控制和隐私策略。

## 十一、逐个问题的诊断流程

1. 定义可重复的用户操作，例如打开会话列表并滚动三屏。
2. 用 Macrobenchmark 或 FrameTimeline 确认该操作存在慢帧，并保存设备、温度、刷新率和构建信息。
3. 用 Layout Inspector 缩小反复重组的界面范围。
4. 用 Composition Tracing 找到耗时组合函数及其调用层级。
5. 查阅 `composables.txt` 和 `classes.txt`，确认函数标签与参数稳定性。
6. 回到调用点检查对象身份、状态读取位置、key、集合转换和 Lambda 捕获。
7. 只修改一个主要变量，再用相同脚本复测计数、Trace 和帧结果。
8. 更新编译器语义快照，并记录变化为何符合预期。

若 FrameTimeline 显示 App 侧按时完成，排查应转向 RenderThread、GPU、SurfaceFlinger 和 fence。继续修改稳定性通常不会解决合成侧或显示侧瓶颈。

## 十二、常见误判

| 误判 | 准确口径 |
| --- | --- |
| `unstable` 参数使函数一定无法跳过 | Kotlin 2.3.20 默认 Strong Skipping；可重启函数仍可跳过，不稳定参数用 `===` 比较 |
| `skippable` 证明运行时已经跳过 | 它只表示编译器生成了跳过能力 |
| 编译器 CSV 包含重组次数和参数列表 | Kotlin 2.3.20 CSV 不包含运行时次数，也没有 `params` 列 |
| 同内容的新 `List` 会按元素比较后跳过 | 声明为不稳定参数时比较容器引用，不做逐元素相等判断 |
| 给类加 `@Stable` 就完成优化 | 注解是开发者契约；违反通知或相等约束会造成界面错误 |
| 系统 Trace 默认显示每个组合函数 | 需要 `runtime-tracing`、编译器 marker 和支持的采集方式 |
| `Compose:measure/layout/draw` 是所有版本固定切片 | Trace 名称属于具体库实现，应按当前版本的真实 Trace 核对 |
| 重组计数下降就证明帧性能改善 | 仍需 FrameTimeline 或 Macrobenchmark 验证用户结果 |
| kernel 调度记录能解释稳定性 | kernel 只提供线程运行、唤醒和同步证据，不包含 Compose 类型语义 |

## 十三、核查清单

### 编译配置

- [ ] Kotlin Android 插件与 `org.jetbrains.kotlin.plugin.compose` 使用同一版本。
- [ ] 报告由固定的 Release 变体生成。
- [ ] 归档模块、target、compilation、提交和 `featureFlags`。
- [ ] Kotlin 升级时重新验证 CSV 与 JSON 格式。

### 静态报告

- [ ] 区分 `restartable`、`skippable` 与参数稳定性。
- [ ] 没有把 `skippable` 当成实际跳过次数。
- [ ] 对集合、跨模块类型和稳定性配置做契约审计。
- [ ] 没有为追求统计数字给可变类型添加虚假注解。

### 运行时

- [ ] Layout Inspector 使用相同交互脚本和重置后的计数。
- [ ] Trace 来自 profileable、non-debuggable 构建。
- [ ] Composition Tracing 依赖和 marker 均已启用。
- [ ] 组合、测量、布局、绘制和提交/显示没有混为一段。

### 结果验证

- [ ] FrameTimeline 指明慢帧责任侧。
- [ ] Macrobenchmark 覆盖目标用户操作。
- [ ] 修复前后使用相同设备条件与构建设置。
- [ ] CI 门禁比较同版本、同开关、同模块的基线。

## 源码与资料索引

- [Diagnose stability issues](https://developer.android.com/develop/ui/compose/performance/stability/diagnose)
- [Fix stability issues](https://developer.android.com/develop/ui/compose/performance/stability/fix)
- [Strong skipping mode](https://developer.android.com/develop/ui/compose/performance/stability/strongskipping)
- [Lifecycle of composables：稳定性契约](https://developer.android.com/develop/ui/compose/lifecycle#skipping)
- [Composition tracing](https://developer.android.com/develop/ui/compose/tooling/tracing)
- [Compose compiler options DSL](https://kotlinlang.org/docs/compose-compiler-options.html)
- [Kotlin 2.3.20 `BuildMetrics.kt`](https://github.com/JetBrains/kotlin/blob/v2.3.20/plugins/compose/compiler-hosted/src/main/java/androidx/compose/compiler/plugins/kotlin/BuildMetrics.kt)
- [Compose Runtime 1.11.4 release notes](https://developer.android.com/jetpack/androidx/releases/compose-runtime#1.11.4)
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [Android 17 `Choreographer.java`](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/core/java/android/view/Choreographer.java)
- [Android 17 `ViewRootImpl.java`](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/core/java/android/view/ViewRootImpl.java)
- [Android 17 `FrameTimeline.java`](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/core/java/android/graphics/FrameTimeline.java)
- [Android common kernel `android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)
- [本知识库：Jetpack Compose 性能优化](03-compose-performance.md)
- [本知识库：Android 17 FrameTimeline](../../part1-fundamentals/ch02-rendering/33-android17-frametimeline-composition-boundary.md)

以上版本化结论核查于 2026-07-29。编译器报告样例来自 Kotlin 2.3.20 编译器对最小源码的实测输出；升级 Kotlin 或 Compose 后，应重新生成报告并复核字段、功能开关与 Trace 名称。
