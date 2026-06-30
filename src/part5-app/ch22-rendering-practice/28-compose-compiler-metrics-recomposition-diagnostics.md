---
title: "Compose Compiler Metrics 与 Recomposition 诊断体系"
chapter: "22.28"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-07-01"
last_verified_against: "Compose BOM 2026.06.00, Kotlin 2.2, Compose Compiler Gradle Plugin"
confidence: high
drafted_date: "2026-07-01"
tags: [compose, compiler, recomposition, diagnostics, stability, perfetto, ci]
related_chapters: ["22.3", "22.20", "7.7"]
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
---

# 22.28 Compose Compiler Metrics 与 Recomposition 诊断体系

Compose 重组控制的基本概念（Stability 推断、Strong Skipping Mode、derivedStateOf）在 §22.3 已系统说明。本节聚焦**诊断工具链**：如何用编译器报告定位不稳定 Composable、如何解读重组原因、如何在 Perfetto 中关联运行时重组行为，以及如何在 CI 中建立自动化 Stability 回归检测。

本节使用 **Compose BOM 2026.06.00 / Kotlin 2.2 / Compose Compiler Gradle Plugin** 作为版本基线。编译器报告功能需要 Kotlin 2.0+（旧版 Compose Compiler 插件用不同的启用方式和字段格式，本节不覆盖）。

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance/stability/diagnose — 最后更新 2026-06-13]
[已验证: 官方文档, developer.android.com/jetpack/androidx/releases/compose-compiler]
[适用版本: Android 12 - Android 17 / Compose Compiler Gradle Plugin (Kotlin 2.0+)]

---

## 编译器报告的生成与文件结构

### 启用报告输出

Compose Compiler Gradle Plugin（Kotlin 2.0+）在模块的 `build.gradle.kts` 中配置：

```kotlin
composeCompiler {
    reportsDestination = layout.buildDirectory.dir("compose_compiler")
    metricsDestination = layout.buildDirectory.dir("compose_compiler")
}
```

- `reportsDestination`：输出 Stability 推断和 Composable 可跳过性分析结果
- `metricsDestination`：输出模块级统计数据（Composable 数量、各类统计）

⚠️ **必须在 Release build 下生成**。Debug build 启用了 Compose Runtime 的调试特性（如 `ComposeNodeData` 追踪），Stability 推断结果可能与 Release 不一致。

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance/stability/diagnose — "Make sure to always run this on a release build to ensure accurate"]

### 输出文件清单

每个模块构建后，`reportsDestination` 生成三个文件：

| 文件 | 内容 | 用途 |
|------|------|------|
| `<module>-classes.txt` | 类的 Stability 推断结果 | 定位不稳定的数据类 |
| `<module>-composables.txt` | Composable 函数分析：restartable / skippable / 参数稳定性 | 定位不可跳过的 Composable |
| `<module>-composables.csv` | composables.txt 的 CSV 版本 | 脚本/CI 批处理 |

`metricsDestination` 额外生成模块级统计文件，包含 Composable 总数、Stable/Unstable 比例等汇总指标。

---

## classes.txt：类的 Stability 推断解读

### 报告格式

每个类在 `classes.txt` 中有一条记录。以官方文档的典型示例：

```
Set<String> is UNSTABLE
```

这表示 `Set<String>` 类型被判定为 Unstable。原因：`Set` 是接口类型，编译器只能看到声明类型，无法确认运行时实现不是 `MutableSet`。即使变量声明为 `val set: Set<String> = setOf("a")`，编译器也无法保证不存在 `val set: Set<String> = mutableSetOf("a")` 的情况。

### Stable 的判定规则

编译器在以下条件全部满足时，将类标记为 Stable：

1. 所有属性都是 `val`（不可变引用）
2. 所有属性的类型本身也是 Stable（递归判定）
3. 属性类型为基本类型（`String`、`Int`、`Boolean` 等）或被标注 `@Stable` / `@Immutable` 的类型

`data class` 满足条件 1 时通常会被自动推断为 Stable——但前提是它的所有属性类型也满足条件 2。如果 `data class` 包含 `List<X>` 属性，即使 `X` 是 Stable，`List<X>` 仍然是 Unstable。

### @Stable 与 @Immutable 注解

这两个注解是开发者与编译器之间的**契约**，不是编译器自动推断的魔法：

- `@Immutable`：承诺类的所有实例在构造后完全不可变，所有方法都是引用透明的
- `@Stable`：承诺属性可以变，但每次变化编译器都能通过 `equals()` 检测到（通常配合 `MutableState` 使用）

⚠️ **错误标注不会导致编译错误，但会导致重组错误**。如果把一个实际可变且 `equals()` 不会变化的类标注为 `@Immutable`，Compose 运行时将无法检测到变化，UI 会"卡住"不更新。

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance/stability/fix]

### 集合类型的默认 Unstable 行为及解决方案

| 解决方式 | 适用场景 | 代价 |
|----------|----------|------|
| `kotlinx.collections.immutable`（`ImmutableList`、`ImmutableSet` 等） | 需要编译时不可变性保证 | alpha 库，API 可能变化 |
| 自定义 Stable 包装类 | 不想引入新依赖 | 需手写 equals/hashCode |
| Stability 配置文件 | 第三方库类不可控 | 绕过编译器安全检查 |
| Strong Skipping Mode（Kotlin 2.0.20+ 默认） | 不想改数据层 | 不减少重组——只减少不可跳过导致的完整执行 |

**Stability 配置文件**（Compose Compiler 1.5.5+）允许将指定类声明为 Stable：

```text
// stability_config.conf
// 考虑 java.time.LocalDateTime 为 Stable
java.time.LocalDateTime

// 考虑整个 datalayer 包为 Stable
com.datalayer.*

// 支持通配符
com.example.GenericClass<*,_>
```

配置方式：

```kotlin
composeCompiler {
    stabilityConfigurationFile = rootProject.layout.projectDirectory.file("stability_config.conf")
}
```

⚠️ 配置文件和注解一样是契约——声明 Stable 后如果类实际可变，重组会静默失效。

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance/stability/fix — "Stability configuration file"]

---

## composables.txt：Composable 可跳过性分析

### 报告字段含义

每个 `@Composable` 函数在 `composables.txt` 中的输出格式：

```
restartable skippable fun SnackCollection(
  snackCollection: Stable
  onSnackClick: Function1<Long, Unit>: Stable
)
```

| 标签 | 含义 | 影响 |
|------|------|------|
| `restartable` | 函数有独立的重启边界，可以作为 Composition 子树独立重组 | 是 skippable 的前提 |
| `skippable` | 所有参数都是 Stable 时，运行时可以跳过函数体执行 | 减少不必要的重组 |
| `restartable skippable` | 两者兼具——理想的 Composable | — |
| `restartable`（无 `skippable`） | 有重启边界但参数含 Unstable 类型，每次父级重组都会执行 | 需检查参数 |
| 无标签 | 内联 Composable 或无独立重启边界 | 无法独立优化 |

### 不可跳过 Composable 的典型场景

```
restartable fun HighlightedSnacks(
  snacks: List<Snack>: Unstable    ← List<Snack> 被判定为 Unstable
  onSnackClick: Function1<Long, Unit>: Stable
)
```

即使 `Snack` 类本身被标注 `@Immutable`，`List<Snack>` 仍然是 Unstable。Strong Skipping Mode（§22.3）启用后，这类 Composable 会被标记为 `restartable skippable`——但**跳过≠不重组**，只是运行时可以用 `equals()` 快速判断是否需要执行函数体。如果 `List<Snack>` 每次都产生新实例，`equals()` 判断为不等，仍然会重组。

**关键区别**：
- **Pre-Strong Skipping**：`skippable = false` → 无条件执行函数体，连 `equals()` 检查都不做
- **Strong Skipping**：`skippable = true` → 做 `equals()` 检查，不等才执行。但 `List` 的 `equals()` 是逐元素比较，大列表的比对开销可能超过直接重组

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance/stability/diagnose]
[结构参考: §22.3 对 Strong Skipping 的完整说明]

---

## Strong Skipping 前后的诊断差异

### Compose Compiler 版本对照

| 时间线 | Compose Compiler | Strong Skipping | 报告变化 |
|--------|-----------------|-----------------|----------|
| Kotlin 1.9.20 | 1.5.11 | 实验性，需手动开启 | `skippable` 字段严格反映参数 Stability |
| Kotlin 2.0.0-2.0.10 | 需手动 `enableStrongSkippingMode = true` | 开启后所有 restartable Composable 标记 skippable | — |
| Kotlin 2.0.20+ | 默认启用 | 稳定，推荐生产使用 | `skippable` 字段几乎总是 true |
| Kotlin 2.2+（本节基线） | 默认启用 | 已合入标准行为 | `skippable` 不再是关注重点 |

[已验证: 官方文档, developer.android.com/jetpack/androidx/releases/compose-compiler — "Strong skipping is no longer considered experimental"]

### Strong Skipping 时代的诊断重心转移

在 Strong Skipping 默认启用后，`composables.txt` 中 `skippable = false` 的 Composable 大幅减少。诊断重心从"为什么不可跳过"转向：

1. **重组频率**：即使可跳过，如果参数频繁变化，`equals()` 比对本身也是开销
2. **Lambda memoize 有效性**：Strong Skipping 自动 memoize lambda，但如果 lambda 的捕获值频繁变化，memoize 失效
3. **Non-restartable Composable**：Strong Skipping 只影响 restartable Composable，内联 Composable 无法独立跳过

[结构参考: §22.3 "Strong Skipping Mode" 和 §22.20 "rememberCoroutineScope 与 Strong Skipping 交互"]

---

## Recomposition 原因解读

### 编译器报告的局限性

Compose Compiler 报告只反映**编译时**的 Stability 推断结果，不包含运行时重组原因。要分析"哪个参数变了、为什么变了"，需要运行时工具：

| 工具 | 能力 | 限制 |
|------|------|------|
| Layout Inspector（Android Studio） | 显示每个 Composable 的重组/跳过次数 | 需要手动连接设备，不适合自动化 |
| Perfetto / systrace | 显示重组时间线、与帧的关系 | 需要开启 Compose tracing |
| Compose Runtime Tracking API | 程序化获取重组回调 | 实验性 API，有运行时开销 |

### Layout Inspector 重组计数

Android Studio 的 Layout Inspector 在 Compose 模式下显示两个计数：

- **Recursion count**（重组次数）：Composable 函数体被执行的次数
- **Skipped count**（跳过次数）：参数未变化，运行时跳过执行的次数

理想状态：大多数 Composable 的 Skipped count 远大于 Recursion count。如果某个 Composable 的 Recursion count 在用户交互后快速增长，说明它被频繁重组。

⚠️ Layout Inspector 本身有性能开销（注入了追踪代码），不能用于精确的耗时测量。用 Layout Inspector 定位问题、用 Perfetto 测量影响。

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance/stability/diagnose — Layout Inspector]

### @SkippableComposable 缺失的原因分析

在 Strong Skipping 之前，`@SkippableComposable` 注解标记（编译器自动添加）表示 Composable 可以被跳过。缺失的原因：

1. **参数含 Unstable 类型**（最常见）
2. **Composable 不是 restartable**（内联函数体内的 Composable、被 `@NonRestartableComposable` 标注）
3. **Composable 有 NonSkippableOptIn**（某些需要每次执行的 Composable，如 `WithConstraintLayout`）

Strong Skipping 之后，原因 1 被自动解决——但要注意：编译器仍然会在 `composables.txt` 中标注参数的 Stability，只是不再阻止 `skippable` 标记。

---

## Compose Runtime Tracing 与 Perfetto 集成

### Compose Tracing 的启用

从 Compose Runtime 1.0+ 起，系统自动在 Perfetto trace 中注入 Compose 相关 slice。Android 12+（API 31+）上这些 slice 通过 `androidx.compose.runtime` 的 `Trace` 调用写入系统 trace buffer：

- `Compose:recompose` — 单次重组的完整执行
- `Compose:applyChanges` — 将 composition 差异应用到 semantics 树
- `Compose:measure` — Composable 的 measure 阶段
- `Compose:layout` — Composable 的 layout 阶段
- `Compose:draw` — Composable 的 draw 阶段

这些 slice 在 Perfetto 中直接可见，不需要额外插件。

[适用版本: Android 12 (API 31)+ — Compose Runtime tracing 依赖系统 atrace 机制]

### Perfetto 中的重组热点识别

在 Perfetto UI 中打开 trace 后，关注以下模式：

**正常模式**（低频重组）：
- `Compose:recompose` slice 间断出现，每次 < 1ms
- 与 `frame` slice 对齐——重组发生在帧截止时间（choreographer deadline）之前

**问题模式**（高频/慢重组）：
- `Compose:recompose` 在连续帧中重复出现——参数频繁变化
- 单个 `Compose:recompose` 持续 > 8ms（超出单帧预算）
- `Compose:recompose` 跨越多个帧边界——导致 jank

**定位根因**：
1. 在 Perfetto 中找到频繁出现的 `Compose:recompose` slice
2. 展开查看其子 slice（如具体哪个 Composable 在执行）
3. 检查同一时间线上 `Choreographer#doFrame` 的耗时
4. 如果 `Compose:applyChanges` 也频繁出现，说明 composition 差异计算量大

### Composition Snapshot 与重组触发

Compose 运行时通过 Snapshot 系统（`Snapshot.kotlin` / `androidx.compose.runtime.snapshots`）管理状态变更的传播。每次 `mutableStateOf` 的值变化都会创建一个 Snapshot mutation，在下一次 Composition 时被读取。

在 Perfetto 中，如果看到 `Compose:recompose` 与 `Compose:applyChanges` 交替出现且间隔极短，通常表示：
- 状态变更 → 触发 recompose → 产生新的 composition 差异 → applyChanges → 可能再次触发 recompose（级联重组）

减少级联重组的方法（详见 §22.3）：
- `derivedStateOf` 合并多个状态读取
- `remember` + key 控制依赖范围
- 将高频变化状态隔离到叶子 Composable

[结构参考: §22.3 "derivedStateOf 与重组范围控制"]

---

## 诊断工作流：从 Metrics 到修复

### Step 1：生成全项目编译器报告

```bash
./gradlew :app:assembleRelease \
  -P composeCompilerReportsDestination=build/compose_compiler \
  -P composeCompilerMetricsDestination=build/compose_compiler
```

或确保 `build.gradle.kts` 中的 `composeCompiler` 块已配置（见上文）。

### Step 2：扫描 Unstable 类和不可跳过 Composable

```bash
# 找出所有 Unstable 类
grep "is UNSTABLE" build/compose_compiler/*-classes.txt

# 找出所有不可跳过的 restartable Composable
# 在 Strong Skipping 之前有效；之后主要用于审计
grep "restartable" build/compose_compiler/*-composables.txt | grep -v "skippable"
```

### Step 3：结合 Layout Inspector 确认运行时影响

在 Android Studio → View → Tool Windows → Layout Inspector 中：
1. 连接设备，选择目标 App
2. 与目标页面交互（滚动、点击）
3. 观察重组计数——找到 Recursion count 异常高的 Composable
4. 对比 Step 2 的编译器报告——确认是否与 Unstable 参数相关

### Step 4：修复 Stability 问题

按优先级选择修复方式（详见 §22.3 和官方 Fix stability issues 文档）：

1. **首选**：将 Unstable 集合替换为 `ImmutableList` / `ImmutableSet`（kotlinx-collections-immutable）
2. **次选**：用 Stability 配置文件将整个 data layer 包标记为 Stable
3. **兜底**：对特定类使用 `@Immutable` / `@Stable` 注解（需严格验证 equals 契约）

⚠️ 不要追求所有 Composable 都 Skippable。官方建议：
- 不常重组的 Composable 不需要 skippable
- 仅调用其他 skippable Composable 的包装函数不需要 skippable
- 参数多且 equals 检查昂贵的 Composable，skippable 的开销可能大于直接重组

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance/stability/fix — "Not every composable should be skippable"]

### Step 5：用 Perfetto 验证修复效果

1. 修复前录制 Perfetto trace（记录重组频率和帧耗时基线）
2. 修复后录制相同操作的 trace
3. 对比 `Compose:recompose` slice 的频率和持续时间
4. 检查 `Choreographer#doFrame` 是否不再超时

---

## CI 集成：自动化 Stability 回归检测

### 解析 composables.csv 建立基线

`composables.csv` 是结构化数据，适合在 CI 中用脚本解析：

```python
import csv

def parse_composables(csv_path):
    """解析 composables.csv，返回不可跳过的 Composable 列表"""
    unstable_composables = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            # CSV 字段因 Compose Compiler 版本可能不同
            # 需根据实际输出调整字段名
            if row.get('skippable', '').strip() != 'true':
                unstable_composables.append({
                    'package': row.get('package', ''),
                    'name': row.get('name', ''),
                    'params': row.get('params', ''),
                })
    return unstable_composables
```

### PR 级别增量检测

CI pipeline 建议：

1. **主分支基线**：将主分支构建产出的 unstable Composable 列表存为基线文件
2. **PR 构建**：构建 PR 分支，产出新的 unstable 列表
3. **Diff 比对**：如果 PR 新增了 unstable Composable（基线中没有的新条目），CI 发出告警

```bash
# 简化的 CI 检测脚本
# baseline_unstable.txt 是主分支的 unstable Composable 名单
NEW_UNSTABLE=$(grep "restartable" build/compose_compiler/*-composables.txt \
  | grep -v "skippable" \
  | awk '{print $3}' \
  | sort -u \
  | comm -23 - baseline_unstable.txt)

if [ -n "$NEW_UNSTABLE" ]; then
  echo "⚠️ 新增不可跳过 Composable:"
  echo "$NEW_UNSTABLE"
  exit 1
fi
```

⚠️ 在 Strong Skipping 默认启用后，"不可跳过"的新增通常意味着 Non-restartable Composable 或 `@NonSkippableComposable` 显式标注，需要人工评估是否合理。

### Compose Compiler 版本兼容性

CI 脚本需要注意 Compose Compiler 输出格式在不同版本间的差异：

| 版本范围 | 报告格式 | 注意事项 |
|----------|----------|----------|
| Kotlin 1.9.x + Compose Compiler 1.5.x | 旧格式（freeForm composeCompiler {} 选项） | 字段名和排列与新版不同 |
| Kotlin 2.0+ Compose Compiler Gradle Plugin | 新格式 | 本节描述的格式 |
| Kotlin 2.2+ (K2 compiler) | 新格式，字段更完整 | 部分 Legacy 字段可能移除 |

如果项目跨越多个 Kotlin 版本，CI 脚本应检测 Kotlin/Compose Compiler 版本并选择对应的解析逻辑。

---

## Compose 1.7+/K2 编译器对 Metrics 的影响

### Kotlin 2.x K2 编译器插件

从 Kotlin 2.0 起，Compose Compiler 以 Kotlin 编译器插件形式集成（不再是独立 `composeOptions`）。K2 编译器（Kotlin 2.0+）的插件 API 变化导致：

1. **报告格式微调**：某些字段名可能略有不同，但核心内容（restartable / skippable / 参数 Stability）保持一致
2. **编译速度提升**：K2 编译器本身更快，生成报告的额外开销降低
3. **诊断信息更丰富**：K2 插件能提供更精确的 Stability 推断原因（部分版本会在 `classes.txt` 中附加推断路径）

### 版本升级时的审计建议

升级 Kotlin / Compose Compiler 版本后：

1. 重新生成全项目编译器报告
2. 与升级前的报告 diff——关注 Stable → Unstable 的回归
3. 某些类的 Stability 判定可能因编译器改进而变化（通常是修正了误判）
4. 更新 CI 基线文件

[待验证: K2 编译器对 `composables.txt` 字段的具体变化，需对照 Kotlin 2.2 release notes 和 Compose Compiler changelog 确认]
