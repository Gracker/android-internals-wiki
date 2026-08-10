---
title: "Compose SubcomposeLayout 性能深度：层级测量、Intrinsic 与重组陷阱"
chapter: "22.34"
status: finalized
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [Compose, SubcomposeLayout, 布局性能, Intrinsics, 测量]
related_chapters: ["22.3", "22.22", "22.25", "22.28"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "章节深挖"
sources:
- type: official
  path: AndroidX Compose UI 1.11.4 SubcomposeLayout.kt @ 854220f44ea8ea80fee824a6c5a045f39bede289
- type: official
  path: AndroidX Compose Foundation 1.11.4 LazyLayout/BoxWithConstraints sources @ 854220f44ea8ea80fee824a6c5a045f39bede289
- type: reference
  path: Android 17 platform tag android-17.0.0_r1
- type: kernel
  path: Android common kernel tag android17-6.18-2026-06_r6
pipeline_stage: finalized
task6_state: reviewed
task9_state: reviewed
last_draft_polish_at: "2026-08-07T23:35:38+08:00"
last_draft_polish_run_id: "20260807-233538-draft-polish-342b11bc"
last_verified: "2026-08-08"
reviewed_date: "2026-08-08"
reviewed_by: "hermes-aiw-review-finalize-apply"
last_review_finalize_at: "2026-08-08T08:12:33+08:00"
last_review_finalize_run_id: "20260808-081000-ee813258"
last_verified_against: "AndroidX Compose UI/Foundation/Runtime 1.11.4 @ 854220f44ea8ea80fee824a6c5a045f39bede289; Android platform android-17.0.0_r1; common kernel android17-6.18-2026-06_r6"
confidence: high
---

# 22.34 Compose SubcomposeLayout 性能深度：层级测量、Intrinsic 与重组陷阱

> **源码锚点**
>
> - 平台：Android 17 / API 37 / `android-17.0.0_r1`
> - 内核：`android17-6.18-2026-06_r6`
> - Compose：UI、Foundation 与 Runtime `1.11.4`
> - AndroidX 源码快照：`854220f44ea8ea80fee824a6c5a045f39bede289`
>
> `SubcomposeLayout` 位于 Compose UI 的 `commonMain`，测量期间的子组合、slot 复用和 intrinsic 限制都由 AndroidX 实现。Android Framework 与内核不提供专门的 SubcomposeLayout 加速路径。平台和内核锚点用于说明它进入 Android 17 标准渲染路径之后的性能边界。

## 1. 先校正常见误差

### 1.1 SubcomposeLayout 不会自动执行 “Intrinsic + 实际测量”

Compose UI `1.11.4` 为 SubcomposeLayout 安装的是 `LayoutNode.NoIntrinsicsMeasurePolicy`。父布局查询它的 `minIntrinsicWidth`、`maxIntrinsicWidth`、`minIntrinsicHeight` 或 `maxIntrinsicHeight` 时，运行时会直接抛出异常。

所以，SubcomposeLayout 的基础成本不能概括成“固定双趟测量”。正常路径是父布局进入 measure，SubcomposeLayout 在该阶段按需组合 slot，再测量返回的 `Measurable`。Lookahead、父布局重复测量、状态失效或业务自己的多阶段算法可能增加 pass，但 intrinsic 不是默认的第一趟。

### 1.2 多层嵌套不等于指数复杂度

每层 SubcomposeLayout 都可能增加子 Composition、slot 查找、测量和回收成本。简单嵌套的成本通常随实际请求的 slot 数和各 slot 子树成本累加。源码没有一条“嵌套 N 层必然指数增长”的规则。

指数增长只可能来自具体算法，例如每一层都为上层的每种结果重新生成多组分支，或不稳定 slot id 导致大量内容反复创建。诊断时要统计实际 subcompose 次数、请求 slot 数和每个 pass 的测量次数，不能只凭布局层数下结论。

### 1.3 BoxWithConstraints 本身使用 SubcomposeLayout

`BoxWithConstraints.kt` 的实现直接调用 `SubcomposeLayout`，在 measure lambda 中把父约束封装成 `BoxWithConstraintsScope`，随后 `subcompose(Unit)`。

内容结构依赖父约束时，它是合适的选择。若目标是移除 subcomposition 成本，把自定义 SubcomposeLayout 改成 BoxWithConstraints 并没有改变机制。更有效的改法可能是把尺寸分支提升到更高层、使用普通 `Layout`，或直接采用 Row、Column、Box 与 Modifier。

### 1.4 LookaheadScope 服务于目标布局与过渡

`LookaheadScope` 从 Compose UI `1.5.0` 开始提供，不是 1.7 才出现。它先执行 lookahead pass 计算目标布局，再按 `approachLayout` 或 `ApproachLayoutModifierNode` 执行 approach pass。

Lookahead 会带来有明确用途的额外布局工作，也有专门的 SubcomposeLayout 协作逻辑。它不替代“根据测量结果决定要组合什么”的能力，不能作为普遍的 SubcomposeLayout 性能方案。

## 2. 普通 Layout 与 SubcomposeLayout 的分界

普通 Compose `Layout` 的子内容在父节点进入 measure 前已经组合完成。measure policy 接收一组确定的 `Measurable`，负责测量、确定自身尺寸并放置。

SubcomposeLayout 改变了组合与布局的顺序：

1. 父节点给出 `Constraints`；
2. SubcomposeLayout 进入 measure；
3. measure policy 根据约束或已测子项结果选择 slot；
4. `subcompose(slotId, content)` 创建或更新该 slot 的子 Composition；
5. 返回该 slot 生成的 `Measurable`；
6. measure policy 测量这些对象并返回 `MeasureResult`；
7. placement 完成后，未使用 slot 被释放或转入复用区。

这个顺序支持三类核心场景：

- 只有拿到父约束后，才能决定子内容结构；
- 需要先测量一个子项，再根据其尺寸组合另一个子项；
- 数据量较大，只组合当前需要的元素，例如 Lazy 布局。

若所有子内容都可以提前组合，普通 Layout 的结构更简单，也少了子 Composition 管理。SubcomposeLayout 应由数据依赖决定，不能仅因为自定义布局复杂就默认采用。

## 3. slot 是子组合的身份边界

`SubcomposeMeasureScope.subcompose()` 的第一个参数是 `slotId`。同一逻辑 slot 在相邻 measure pass 中应提供 `equals()` 相等的 id，Runtime 才能找到原节点和 Composition。

当前实现把子节点分成三段：

| 区域 | 含义 |
| --- | --- |
| active | 上一次或当前 measure pass 使用的 slot |
| reusable | 暂时不用、由复用策略保留的 slot |
| precomposed | 已提前组合，等待后续 measure 使用的 slot |

measure 开始时，`currentIndex` 归零。每次 `subcompose()` 都把目标节点移动到当前 active 位置并递增索引。placement 后，从 `currentIndex` 开始的旧 active slot 会交给复用策略；未保留的 slot 会被 dispose。

### 3.1 id 必须稳定且在当前 pass 内唯一

同一个 slotId 在一次 pass 中使用两次，会触发源码中的 key 重复检查。异常信息也会提示 LazyColumn/LazyRow 使用唯一 key。

自定义布局的固定角色适合使用 enum 或稳定对象；列表内容适合使用业务实体的稳定 id。数组下标只有在元素不会插入、删除或重排时才具备稳定身份。

### 3.2 content 变化与无效状态都会触发子组合

`LayoutNodeSubcompositionsState.subcompose()` 会检查：

- content lambda 引用是否变化；
- 子 Composition 是否有 invalidation；
- `forceRecompose` 是否设置；
- 是否存在尚未处理的 paused composition。

其中任一条件要求更新时，Runtime 才调用子 Composition 的 `setContent()` 或 `setContentWithReuse()`。同一个 slotId 只能解决身份匹配问题；content 每次改变、内部状态持续失效，仍会产生组合工作。

### 3.3 默认 State 不保留离场 slot

无参 `SubcomposeLayoutState()` 使用 `NoOpSubcomposeSlotReusePolicy`。它会清空可复用集合，并把不同 id 视为不兼容。因此，普通 `SubcomposeLayout { ... }` 不会自动维护类似 RecyclerView 的离场缓存。

需要复用时，可以给 `SubcomposeLayoutState` 提供 `SubcomposeSlotReusePolicy`。策略负责两件事：

- 从候选集合中选择要保留的 slot；
- 判断新 slot 与旧 slot 的内容结构是否兼容。

保留数量越多，节点创建和 Composition 初始化机会可能减少，同时会延长节点、remember 对象和相关状态的生命周期。这个取舍要同时测 CPU 与内存。

## 4. 一个有必要使用 SubcomposeLayout 的例子

下面的组件要先获得主体的实测尺寸，再用该尺寸组合覆盖层。固定 enum 让两个 slot 在相邻 pass 中保持身份。

```kotlin
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.SubcomposeLayout
import androidx.compose.ui.unit.Constraints
import androidx.compose.ui.unit.IntSize

private enum class DependentSlot {
    Main,
    Overlay,
}

@Composable
fun SizeAwareOverlay(
    main: @Composable () -> Unit,
    overlay: @Composable (IntSize) -> Unit,
    modifier: Modifier = Modifier,
) {
    SubcomposeLayout(modifier = modifier) { constraints ->
        val mainPlaceables =
            subcompose(DependentSlot.Main, main).map { measurable ->
                measurable.measure(constraints)
            }

        val naturalWidth =
            mainPlaceables.maxOfOrNull { it.width } ?: constraints.minWidth
        val naturalHeight =
            mainPlaceables.maxOfOrNull { it.height } ?: constraints.minHeight
        val size =
            IntSize(
                width = constraints.constrainWidth(naturalWidth),
                height = constraints.constrainHeight(naturalHeight),
            )

        val overlayPlaceables =
            subcompose(DependentSlot.Overlay) {
                overlay(size)
            }
                .map { measurable ->
                    measurable.measure(
                        Constraints.fixed(size.width, size.height)
                    )
                }

        layout(size.width, size.height) {
            mainPlaceables.forEach { it.placeRelative(0, 0) }
            overlayPlaceables.forEach { it.placeRelative(0, 0) }
        }
    }
}
```

这里的第二个 content 必须依赖第一个 slot 的测量结果，使用 SubcomposeLayout 有清晰理由。若覆盖层只需读取绘制区域而不改变可组合结构，`drawWithContent`、`drawBehind` 或普通 Box 往往更轻。

## 5. measure 成本来自实际请求，不是固定的两趟

一个 measure pass 的工作量取决于 measure policy 调用了多少次 `subcompose()`、每个 slot 是否需要重组、每个 slot 产生多少 `Measurable`，以及这些对象的测量成本。

可以用下面的思路估算，而不要套固定倍数：

`本次成本 ≈ slot 查找/移动 + 新建或更新子 Composition + 子项 measure + placement + 未用 slot 的复用或释放`

### 5.1 subcompose 不等于每次都创建新 Composition

slotId 命中 active、precomposed 或兼容 reusable 节点时，Runtime 会复用对应 LayoutNode。content 未变化且 Composition 没有 invalidation 时，子组合也可能跳过。

因此，trace 中出现父布局 measure 不表示所有 slot 都重新组合。需要结合 composable slice、recomposition 计数和 slot 身份判断。

### 5.2 同一 slot 在同一个 Lazy measure pass 有缓存

`LazyLayoutMeasureScopeImpl` 分别缓存当前 pass 已 compose 的 `Measurable` 和旧版 `measure()` API 的 `Placeable`。同一个 index 在本次 pass 被重复查询时，可以返回缓存结果。

这个缓存只覆盖当前 measure scope，不是跨帧 item 缓存。跨 pass 的身份、内容 lambda 和节点复用依赖 key、contentType、SubcomposeLayoutState 与 Snapshot invalidation。

### 5.3 父约束变化会重新进入 measure

窗口尺寸、Insets、动画尺寸、父节点状态或 Modifier 变化都可能产生新约束。measure policy 会再次执行，并重新决定本次需要哪些 slot。

如果内容结构只在少数断点变化，可以在上层把原始宽度归约成稳定的布局模式，例如 compact 或 expanded，再把模式传给多个 item。这样可以减少每个 item 都创建 BoxWithConstraints 或自定义 SubcomposeLayout 的需要。

## 6. Intrinsic 的真实行为

Intrinsic 查询允许父布局在正式 measure 前询问子布局的理想宽高。普通 `MeasurePolicy` 有四个 intrinsic 方法，默认实现会尽力复用 measure 逻辑进行估算；自定义普通 Layout 也可以覆盖这些方法。

SubcomposeLayout 无法在缺少真实父约束与正常 measure 状态时可靠决定要组合哪些 slot，所以当前实现拒绝 intrinsic 查询。错误信息明确列出受影响的组件：

- Lazy list；
- BoxWithConstraints；
- TabRow；
- 其他基于 SubcomposeLayout 的布局。

### 6.1 `IntrinsicSize.Min/Max` 可能直接触发异常

如果父容器对包含上述组件的子树使用 `Modifier.width(IntrinsicSize.Min)`、`height(IntrinsicSize.Max)` 等，查询传播到 SubcomposeLayout 时会失败。这里没有“先 intrinsic 组合整棵树，再正式测量”的过程。

### 6.2 源码给出的两类处理方式

NoIntrinsics 错误信息建议：

- 若 intrinsic 用于实现 match-parent 类需求，改写父自定义 Layout，控制子项测量顺序；
- 给 SubcomposeLayout 组件提供可快速回答 intrinsic 的尺寸 Modifier，使查询不必继续进入其内部。

第二种方式要求业务已经知道合理尺寸。为了绕过异常随意写固定宽高，会损害自适应与可访问性。

### 6.3 `@IntrinsicMeasurer` 不是当前 Compose API

Compose UI `1.11.4` 没有名为 `@IntrinsicMeasurer` 的公开注解。普通自定义 Layout 通过覆盖 `MeasurePolicy` 的四个 intrinsic 方法提供结果；SubcomposeLayout 的 NoIntrinsics policy 不开放这条覆盖入口。

Intrinsic 查询只沿参与该查询的布局关系传播，也不等价于全树重新测量。性能分析应以调用栈和 trace 为证据，避免把一次 intrinsic 请求描述成无条件全树操作。

## 7. Subcomposition 与 recomposition 怎样交互

每个 slot 持有自己的 `ReusableComposition`，其 parent 是 SubcomposeLayout 捕获的 `CompositionContext`。父与子仍共享 Snapshot 状态模型，但 invalidation 和执行边界可以分开观察。

### 7.1 slot content 内读取状态

状态由 slot 的可组合内容读取时，变化会使对应子 Composition 产生 invalidation。下次 subcompose 该 slot 时，Runtime 检测 `hasInvalidations` 并执行所需重组。

如果该 slot 当前不可见且已 dispose，后续重新出现时会重新创建或从兼容节点复用，行为取决于复用策略。

### 7.2 measure policy 内读取状态

状态在 measure lambda 中读取时，变化主要使布局重新测量。重新 measure 后，业务逻辑可能选择不同 slot；选中的 slot 是否重组，仍由 content 身份和子 Composition invalidation 决定。

把高频变化状态读在 measure 阶段，可以跳过父级 composition，但会增加 remeasure。把同一个状态读在 placement 或 draw 阶段，且需求允许只更新对应阶段，成本通常更低。

### 7.3 父 SubcomposeLayout 重组

`SubcomposeLayout` 自身未被跳过时，会通过 `SideEffect` 调用 `state.forceRecomposeChildren()`。当前实现为非 reusable-only 的子节点设置 `forceRecompose`，并请求 remeasure；位于 LookaheadScope 时请求 lookahead remeasure。

把频繁变化且与布局无关的参数捕获进父 SubcomposeLayout，会扩大工作范围。参数稳定性仍有价值，但不能只看 Compiler Metrics 的 stable/unstable 标签判断耗时。

### 7.4 content lambda 身份

源码用引用比较判断 slot content 是否变化。LazyLayout 通过 `LazyLayoutItemContentFactory` 按 key 缓存 content lambda，减少同一 item 因 lambda 实例变化产生的组合。

自定义布局要避免在 measure policy 内构造会频繁改变业务身份的包装对象，并保持 slotId、输入状态和内容结构稳定；不应为了引用稳定强行缓存已经过期的数据。

## 8. LazyColumn 怎样建立在 SubcomposeLayout 上

Foundation `LazyLayout` 创建 `SubcomposeLayoutState(LazyLayoutItemReusePolicy)`，再把 `LazyLayoutMeasureScope` 适配到 SubcomposeMeasureScope。LazyColumn、LazyRow、Lazy grid 与 Pager 的更高层策略决定当前需要 compose 和 measure 哪些 index。

### 8.1 key 与 contentType 的职责不同

| 字段 | 主要作用 |
| --- | --- |
| key | 标识 item 身份，维持 index 变化后的内容、保存状态与 slot 映射 |
| contentType | 判断不同 item 的已有 Composition/LayoutNode 是否适合复用 |

`LazyLayoutItemReusePolicy.areCompatible()` 只有在两个 slot 的 contentType 相等时才返回 true。`LazyLayoutItemContentFactory` 也按 key、index 与 contentType 缓存内容 lambda。

因此，给所有结构差异很大的 item 返回同一个 contentType，会增加不合适结构之间的复用尝试；为每个 item 返回永不相等的 contentType，则失去跨 item 复用机会。

### 8.2 当前保留数量是实现细节

Foundation `1.11.4` 的 LazyLayout policy 每种 contentType 最多保留 7 个 reusable item。源码注释说明该数量参考 RecyclerView 的 5 个 pool slot 加 2 个 cache slot。

这个数字没有暴露成 LazyColumn 的稳定契约，后续版本可以改变。业务优化应依靠 key、contentType、item 成本和 benchmark，不能围绕 7 编写逻辑。

### 8.3 预取与可见区 measure 是两条时机

可见 item 在 LazyLayout measure 中按需 subcompose。屏外预取通过 `SubcomposeLayoutState.precompose()` 或 `createPausedPrecomposition()` 提前准备 slot，并可通过 handle 执行 premeasure。

Compose Foundation `1.11.4` 的 Lazy 预取可使用 PausableComposition 分段完成 composition，但 apply、nested prefetch 与 measure 仍有各自预算。相关状态机见 22.33。

### 8.4 小型固定集合不一定需要 Lazy

官方 Compose 性能 codelab 展示过一种典型问题：每个列表 item 内再放一个只含少量标签的 LazyRow，使 trace 出现额外的容器与 item composition 工作。数据量固定且全部都要显示时，Row 加普通迭代可能更合适。

这不是“禁止嵌套 Lazy”。横向集合很大、需要独立滚动且只显示一部分时，LazyRow 仍有价值。判断依据是可见项数量、预取、节点复用和实测帧成本。

## 9. BoxWithConstraints 的正确使用方式

BoxWithConstraints 适合根据 `minWidth`、`maxWidth`、`minHeight`、`maxHeight` 或原始 Constraints 选择不同 UI 结构。它的 content 在 measure 阶段 subcompose，因此会在 trace 中形成独立于父 composition 的工作。

可以按以下问题决定是否保留：

- content 是否读取 BoxWithConstraintsScope；
- 读取的约束是否会改变要组合的组件，而非只改变尺寸或对齐；
- 相同约束分支是否在大量 Lazy item 中重复计算；
- 是否能在页面或分栏容器层计算一次布局模式，再向下传值；
- 是否可用标准 Box、Row、Column、Flow layout 或 Modifier 解决。

若 content 完全没有读取 scope，Android Lint 的 `UnusedBoxWithConstraintsScope` 也会提示该容器可能多余。

## 10. Lookahead 与 SubcomposeLayout 的协作边界

`LookaheadScope` 内的布局先计算目标 geometry，再运行 approach pass。SubcomposeMeasureScope 的公开文档规定：

- 子组合主要发生在 lookahead pass；
- post-lookahead/main pass 返回 lookahead pass 已组合的 `Measurable`；
- 子树结构依赖 incoming constraints 时，应考虑两次 pass 使用一致的 lookahead 约束决策。

当前 SubcomposeLayout 源码还为 approach 独有 slot 保存 precomposed handle，并在 approach placement 后释放不再需要的 slot。paused precomposition 若尚未完成，在进入需要同步使用它的 pass 时会完成并 apply。

这些逻辑用于保持预测布局与当前布局的子树关系。它不会消除 pass；错误的约束分支还可能让 lookahead 和 approach 需要不同 slot，增加组合与生命周期管理。

适合 LookaheadScope 的需求包括目标位置、目标尺寸和布局切换动画。只想根据宽度显示两套静态内容时，BoxWithConstraints、WindowSizeClass 或更高层布局模式通常更直接。

## 11. 工具能力：能看到什么，不能看到什么

### 11.1 Compose Compiler Metrics

Compiler Metrics 可以报告可组合函数是否 restartable、skippable，以及参数稳定性等编译信息。它没有“SubcomposeLayout 测量次数”或“SubcomposeLayout 标记”。

可以用它检查 slot content 为什么无法跳过，但仍要用运行时 trace 判断这个 content 是否在目标帧被 subcompose，以及执行了多久。

### 11.2 Layout Inspector

Layout Inspector 能查看 Compose 树，并在支持的调试配置下显示 composition、recomposition 与 skip 计数。这些计数是定位异常更新的线索，不是 measure 次数或耗时。

Inspector 本身会增加调试开销。性能结论应在 non-debuggable、可复现的 benchmark 中确认。

### 11.3 Perfetto 与 Composition Tracing

启用 Compose composition tracing 后，Perfetto 可以显示可组合函数名称与重组 slice。SubcomposeLayout 的子内容可能显示为与父容器分开的 composition 工作；Lazy 还会出现预取相关 slice。

当前基线的 Foundation 源码包含这些 Lazy 预取名称：

- `compose:lazy:prefetch:compose`
- `compose:lazy:prefetch:apply`
- `compose:lazy:prefetch:resolve-nested`
- `compose:lazy:prefetch:measure`

`SubcomposeLayout.kt` 本身没有一个面向应用、名称固定为 `subcompose` 的公共 trace slice。`Compose:recompose` 等显示名称会随 Runtime、tracing 配置和构建信息变化，采集前要记录依赖版本。

### 11.4 自定义调试计数

自研 SubcomposeLayout 可以在 debug benchmark 变体中记录：

- 每个 frame/measure pass 请求的 slotId；
- 新建、active 命中、precompose 命中和 reusable 命中；
- 每个 slot 产生的 Measurable 数；
- measure policy 与关键子内容的 trace section；
- 约束和布局模式是否频繁来回变化。

记录代码不能向 Snapshot state 回写并在同一 measure 中读取，否则会制造新的 invalidation。生产版本也不应保留高频字符串拼接或日志输出。

## 12. 一套可复现的性能验证方法

### 12.1 建立对照组

每次只改变一个结构：

- SubcomposeLayout 与普通 Layout；
- 每 item BoxWithConstraints 与上层一次性布局模式；
- 小型 LazyRow 与 Row；
- 默认无复用 policy 与有上限的兼容复用 policy；
- Lookahead 开启与需求允许的非 Lookahead 实现。

### 12.2 固定运行条件

使用同一物理设备、刷新率、数据集、滚动轨迹、Release 构建、R8 与 Baseline Profile 条件。冷运行和热运行分开记录，避免节点复用、图片缓存和 JIT 状态混在一起。

### 12.3 同时看帧指标与阶段证据

Macrobenchmark 的 `FrameTimingMetric` 用于比较 frame duration 和 overrun 分布。Perfetto 用来解释变化来自：

- 父 composition；
- slot composition/recomposition；
- measure 与 placement；
- Lazy 预取；
- RenderThread 或显示路径。

平均值不足以反映偶发的昂贵 slot。报告中至少保留 P50、P90、P95、P99、jank type、GC 与内存变化，不设脱离产品目标的通用阈值。

## 13. Android 17 渲染路径中的位置

SubcomposeLayout 的主要成本位于应用主线程的 Composition 与 Layout。可见内容需要参与当前帧时，路径继续进入：

`vsync-app → Choreographer#doFrame → AndroidComposeView measure/layout/draw → RenderThread/HWUI → BLASTBufferQueue → SurfaceFlinger → HWC → present`

主线程在 measure 中创建或更新大量 slot，会推迟 draw 与 `syncAndDrawFrame()`。预取路径也运行在主线程帧间时间，若工作超过可用预算，可能推迟下一次 doFrame。

Android 17 的 FrameTimeline 能帮助确认 App SurfaceFrame 是否错过 deadline，但它不会指出哪一个 slot 导致超时。需要把 Composition Tracing、measure 证据和 FrameTimeline 放在同一时间轴。

`android-17.0.0_r1` 没有把 SubcomposeLayout 迁移到 Framework 或 RenderThread。`android17-6.18-2026-06_r6` 的调度、内存与图形驱动状态会影响全局时延，但不决定 slotId、子组合或 intrinsic 行为。

## 14. 版本边界

| Compose UI 版本 | 相关公开变化 |
| --- | --- |
| `1.0.0` | `SubcomposeLayout`、`SubcomposeLayoutState` 与 `precompose()` 已提供 |
| `1.2.0` | 接受 `SubcomposeSlotReusePolicy` 的 State 构造函数加入 |
| `1.5.0` | `LookaheadScope` 公开提供 |
| `1.9.0` | `createPausedPrecomposition()` 加入 |
| `1.11.4` | 当前稳定基线，包含 PausableComposition、Lookahead/approach 与当前 Lazy reuse 实现 |

这些能力由 Compose 依赖版本决定，不由设备 Android 版本单独决定。项目升级 Compose 后，应重新核对 release notes、目标 tag 源码和 trace 名称。

## 15. 优化决策清单

遇到 SubcomposeLayout 相关卡顿时，按依赖关系逐项确认：

1. 子内容结构是否必须等待父约束或兄弟尺寸；
2. 每个 measure pass 实际请求多少 slot；
3. slotId 在数据插入、删除和重排后是否稳定；
4. content lambda 是否持续变化，slot 内状态是否高频失效；
5. 未使用 slot 是 dispose 还是进入兼容复用区；
6. Lazy item 的 key 与 contentType 是否准确；
7. 每个 item 是否重复使用 BoxWithConstraints 或小型 Lazy 容器；
8. intrinsic 查询是否会到达 SubcomposeLayout；
9. Lookahead 是否对应真实动画需求；
10. trace 中昂贵阶段属于 composition、measure、draw 还是显示后半段。

有了这组证据，再选择普通 Layout、上移约束分支、调整 slot policy、简化 item、保留 Lazy 或修改 Lookahead 范围。不要为了减少一个 trace slice 牺牲正确的按需组合。

## 16. 常见误判

| 误判 | Compose 1.11.4 的行为 |
| --- | --- |
| SubcomposeLayout 固定执行 intrinsic 和正式 measure 两趟 | 它拒绝 intrinsic 查询；正常 pass 在 measure/layout 中按需 subcompose |
| 嵌套 N 层必然指数增长 | 成本由实际 slot、pass 与子树工作决定，层数本身不能证明复杂度 |
| BoxWithConstraints 可移除 subcomposition | 它内部直接使用 SubcomposeLayout |
| `@IntrinsicMeasurer` 可以修复 SubcomposeLayout | 当前 Compose UI 没有该公开注解，SubcomposeLayout 使用 NoIntrinsics policy |
| slotId 相同就一定不重组 | content 变化、Snapshot invalidation 与 forceRecompose 仍可触发 |
| 默认 State 会缓存离场 slot | 无参 State 的 policy 不保留 reusable slot |
| key 和 contentType 是同一个概念 | key 标识 item；contentType 决定跨 item 复用兼容性 |
| Compiler Metrics 能给出 subcompose 次数 | 它提供编译稳定性与可跳过信息，运行次数要从 trace 或调试计数取得 |
| Layout Inspector 的重组计数等于 measure 次数 | 两者是不同阶段，Inspector 计数不能代替测量证据 |
| LookaheadScope 会减少布局 pass | 它计算目标布局并按需运行 approach pass，适用于过渡需求 |
| Android 17 会原生优化 SubcomposeLayout | 机制位于 AndroidX commonMain，平台继续处理后续窗口渲染 |

## 17. 源码与官方资料

### Compose UI `1.11.4`

- [`SubcomposeLayout.kt`](https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/ui/ui/src/commonMain/kotlin/androidx/compose/ui/layout/SubcomposeLayout.kt)：slot 状态、NoIntrinsics、复用、预组合、Lookahead 与 PausableComposition 协作。
- [`LookaheadScope.kt`](https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/ui/ui/src/commonMain/kotlin/androidx/compose/ui/layout/LookaheadScope.kt)：lookahead 与 approach pass 的公开契约。
- [SubcomposeLayout API Reference](https://developer.android.com/reference/kotlin/androidx/compose/ui/layout/SubcomposeLayout.composable)。
- [SubcomposeLayoutState API Reference](https://developer.android.com/reference/kotlin/androidx/compose/ui/layout/SubcomposeLayoutState)。
- [SubcomposeSlotReusePolicy API Reference](https://developer.android.com/reference/kotlin/androidx/compose/ui/layout/SubcomposeSlotReusePolicy)。
- [LookaheadScope API Reference](https://developer.android.com/reference/kotlin/androidx/compose/ui/layout/LookaheadScope.composable)。
- [Compose UI 发布说明](https://developer.android.com/jetpack/androidx/releases/compose-ui)。

### Compose Foundation `1.11.4`

- [`BoxWithConstraints.kt`](https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/foundation/foundation-layout/src/commonMain/kotlin/androidx/compose/foundation/layout/BoxWithConstraints.kt)：BoxWithConstraints 对 SubcomposeLayout 的直接封装。
- [`LazyLayout.kt`](https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/lazy/layout/LazyLayout.kt)：LazyLayout 的 State、reuse policy 与 SubcomposeLayout 入口。
- [`LazyLayoutMeasureScope.kt`](https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/lazy/layout/LazyLayoutMeasureScope.kt)：当前 pass 的 item compose/measure 缓存。
- [`LazyLayoutItemContentFactory.kt`](https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/lazy/layout/LazyLayoutItemContentFactory.kt)：key、contentType、内容 lambda 与保存状态。

### 官方性能与布局资料

- [Compose phases](https://developer.android.com/develop/ui/compose/phases)：Composition、Layout、Draw 的状态读取与跳过边界。
- [Intrinsic measurements](https://developer.android.com/develop/ui/compose/layouts/intrinsic-measurements)：IntrinsicSize 与普通自定义 Layout 的 intrinsic API。
- [Practical performance problem solving in Jetpack Compose](https://developer.android.com/codelabs/jetpack-compose-performance)：Composition Tracing、Lazy/SubcomposeLayout 与小型 LazyRow 案例。

### Android 17

- [`Choreographer.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java)：应用帧起点、VSync 与 FrameTimeline。
- [`ViewRootImpl.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)：窗口 traversal 与 HWUI 提交入口。
- [Android common kernel（`android17-6.18-2026-06_r6`）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)：统一的内核基线；相关机制没有直接依赖其 API。

## 小结

SubcomposeLayout 允许父布局在 measure 或 layout 阶段选择并组合 slot。它的价值来自约束依赖、兄弟尺寸依赖和按需内容；代价来自子 Composition、slot 生命周期、额外 measure 工作与复用管理。稳定 slotId、准确的 Lazy key/contentType、有限且兼容的复用，以及减少无必要的每 item BoxWithConstraints，都比泛化的“层级过深”更可操作。

Intrinsic 查询在当前实现中直接被拒绝，BoxWithConstraints 自身使用 SubcomposeLayout，LookaheadScope 还会引入目标与 approach pass。性能分析需要把 Compiler Metrics、Layout Inspector 和 Perfetto 的能力分开：编译信息解释可跳过性，Inspector 提供结构与重组线索，Perfetto 和 Macrobenchmark 负责运行时耗时与帧结果。Android 17 继续处理 Compose 输出后的 HWUI、BufferQueue、SurfaceFlinger 和显示路径，不参与 slot 调度。
