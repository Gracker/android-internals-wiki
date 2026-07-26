---
title: "Compose Text 性能深度优化"
chapter: "22.27"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags:
  - Compose
  - 性能优化
  - 文本渲染
  - Android 17
  - 实践
author: "AIW Task 2A"
created: "2026-06-25"
task6_state: pending-source-material
task9_state: pending
pipeline_stage: draft_polish_blocked
last_draft_polish_at: "2026-07-26T19:35:41+08:00"
last_draft_polish_run_id: "20260726-193510-draft-polish-0202a6c7"
last_verified: "2026-07-26"
confidence: low
sources: []
---

# 25 Compose Text 性能深度优化

> **Draft polish 说明（2026-07-26）**：本章当前没有随同输入材料（`materials=[]`），因此本次只做安全打磨：补齐元数据、收敛 Android 17/API 37 版本边界、删除未来源化的“Android 17 特有 API/收益数字”表述，并把正文定位为待 Task6 复核的实践清单。要推进到 `ready-for-review`，需要补充 Jetpack Compose Text 官方文档、Compose release notes、Macrobenchmark/Perfetto 实测或 AOSP/AndroidX 源码定位证据。

## 25.1 版本边界与来源状态

- **Android 基线**：本文面向 Android 10（API 29）到 Android 17（API 37）；不引入 Android 18 / API 38+ 结论。
- **Compose 口径**：Compose Text 的行为主要由 AndroidX Compose UI / Foundation / Material 版本决定，不能把 Android 17 平台版本直接写成 Compose Text 新 API 或默认优化。
- **当前状态**：本章仍是 draft。没有可路由来源材料时，文中的建议只能作为经验性检查清单，不能作为“已由源码或基准验证”的结论。
- **待补证据**：需要在 Task6 中补充官方文档、AndroidX 源码路径、Compose release notes，以及至少一组 Macrobenchmark/Perfetto 或 Android Studio Profiler 复现实验。

## 25.2 Compose Text 渲染与性能关注点

Compose `Text` 是 Android 应用中最常见的 UI 元素之一。性能问题通常不来自单个短文本，而来自以下组合场景：

- 列表中大量文本项反复组合、测量和绘制；
- 复杂 `AnnotatedString`、多 span、多语言或 emoji 文本导致布局成本升高；
- 滚动、输入、主题切换时不必要的 recomposition；
- 在 `onTextLayout` 或组合阶段执行过重的同步计算；
- 未用 Macrobenchmark、Perfetto 或 Profiler 区分“组合、布局、绘制、GC”各自的耗时来源。

### 25.2.1 基础链路（待源码复核）

可以把 Compose Text 的 UI 成本粗略拆成：

```text
Composable 参数变化 → recomposition → measure/layout → draw → frame presentation
```

其中需要重点观察：

- **组合阶段**：是否在组合中构造昂贵对象，或把不稳定参数传入大量列表项；
- **测量/布局阶段**：长文本、复杂 span、换行、`maxLines`、overflow 是否触发布局开销；
- **绘制阶段**：文本数量、透明度、背景、裁剪与父布局层级是否叠加；
- **内存分配**：滚动中是否出现大量短生命周期的 `TextStyle`、`AnnotatedString` 或列表项模型对象。

> 待验证：以上链路需要用 AndroidX Compose Text 源码与 trace 对齐，不能仅凭本文描述作为源码结论。

## 25.3 常见性能陷阱与安全改写

### 25.3.1 在组合路径中重复构造样式

```kotlin
// ❌ 风险示例：如果该 Text 位于高频重组路径中，重复构造对象会增加分配和稳定性分析成本。
Text(
    text = "Hello",
    style = TextStyle(
        fontWeight = FontWeight.Bold,
        color = MaterialTheme.colorScheme.primary
    )
)
```

更安全的做法是优先复用主题样式，或在参数稳定、语义明确时使用 `remember`：

```kotlin
@Composable
fun TitleText(text: String) {
    val color = MaterialTheme.colorScheme.primary
    val style = remember(color) {
        TextStyle(
            fontWeight = FontWeight.Bold,
            color = color
        )
    }

    Text(text = text, style = style)
}
```

注意：`remember` 不是万能优化。若样式本身来自 `MaterialTheme.typography` 且没有额外昂贵构造，优先保持代码简单，并用实际 trace 判断是否需要缓存。

### 25.3.2 长文本和富文本构造

```kotlin
// ❌ 风险示例：在大量列表项或高频更新路径中反复构造富文本。
@Composable
fun RichTextExample(text: String) {
    val annotatedText = buildAnnotatedString {
        append(text)
        addStyle(
            style = SpanStyle(color = Color.Red),
            start = 0,
            end = text.length
        )
    }
    Text(text = annotatedText)
}
```

如果 span 规则只依赖输入文本和少量主题参数，可以把构造边界收敛到 `remember`：

```kotlin
@Composable
fun RichTextOptimized(text: String) {
    val annotatedText = remember(text) {
        buildAnnotatedString {
            append(text)
            if (text.isNotEmpty()) {
                addStyle(
                    style = SpanStyle(color = Color.Red),
                    start = 0,
                    end = text.length
                )
            }
        }
    }

    Text(
        text = annotatedText,
        maxLines = 3,
        overflow = TextOverflow.Ellipsis
    )
}
```

### 25.3.3 列表中的 Text

```kotlin
// ❌ 风险示例：列表项缺少稳定 key，且样式在每个 item 中重复构造。
LazyColumn {
    items(largeList) { item ->
        Text(
            text = item.title,
            style = TextStyle(
                fontWeight = FontWeight.Medium,
                fontSize = 16.sp
            )
        )
    }
}
```

建议优先处理列表层面的稳定性，再考虑样式缓存：

```kotlin
@Composable
fun OptimizedLazyText(largeList: List<ArticleItem>) {
    val titleStyle = remember {
        TextStyle(
            fontWeight = FontWeight.Medium,
            fontSize = 16.sp
        )
    }

    LazyColumn {
        items(
            items = largeList,
            key = { item -> item.id }
        ) { item ->
            Text(
                text = item.title,
                style = titleStyle,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
        }
    }
}
```

> 待验证：`ArticleItem` 的稳定性、`id` 的唯一性、列表数据更新方式，需要结合业务代码和 Compose compiler metrics 检查。

## 25.4 测量与定位

### 25.4.1 Macrobenchmark / JankStats / Profiler

在没有一手 benchmark 前，不应写固定收益百分比。更稳妥的评估顺序是：

1. 用 Macrobenchmark 覆盖关键滚动、首屏和文本更新路径；
2. 用 Android Studio Profiler 或 allocation tracking 检查滚动中的对象分配；
3. 用 Perfetto 观察 frame timeline、主线程阻塞、GC、RenderThread 与 GPU 相关片段；
4. 对比改动前后相同设备、相同 Compose 版本、相同数据规模下的结果。

### 25.4.2 `onTextLayout` 的使用边界

```kotlin
@Composable
fun TextLayoutProbe(text: String) {
    var lineCount by remember { mutableIntStateOf(0) }

    Text(
        text = text,
        maxLines = 5,
        overflow = TextOverflow.Ellipsis,
        onTextLayout = { result ->
            // 只记录轻量状态；避免在这里执行重 IO、复杂解析或同步上报。
            lineCount = result.lineCount
        }
    )

    Text(text = "lines: $lineCount")
}
```

`onTextLayout` 适合记录布局结果或驱动轻量 UI 状态；如果要做耗时分析、日志聚合或埋点上报，应放到可控的异步链路中，并避免每帧触发。

### 25.4.3 Perfetto 观察点

在 Perfetto 中建议围绕以下问题看 trace，而不是只搜索单一固定 slice 名称：

- frame 是否出现 missed deadline 或 jank；
- 主线程是否被文本构造、数据变换、同步 IO 或 GC 阻塞；
- layout/draw 是否与列表滚动、主题切换、输入联动；
- 改动前后是否使用同一测试场景、设备温度和数据量。

## 25.5 实战场景

### 25.5.1 聊天消息列表

```kotlin
@Composable
fun ChatMessageItem(
    message: ChatMessage,
    isMe: Boolean
) {
    val colors = MaterialTheme.colorScheme
    val baseStyle = MaterialTheme.typography.bodyLarge
    val messageStyle = remember(isMe, colors, baseStyle) {
        baseStyle.copy(
            color = if (isMe) colors.onPrimary else colors.onBackground
        )
    }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(8.dp),
        horizontalArrangement = if (isMe) Arrangement.End else Arrangement.Start
    ) {
        Text(
            text = message.text,
            style = messageStyle,
            modifier = Modifier
                .background(if (isMe) colors.primary else colors.surface)
                .padding(12.dp),
            maxLines = 5,
            overflow = TextOverflow.Ellipsis
        )
    }
}
```

复核重点：

- `ChatMessage` 是否是稳定模型；
- `LazyColumn` 是否使用稳定 key；
- 消息更新是否只影响变更项，而非整屏消息重组；
- 长消息、emoji、多语言文本是否纳入 benchmark 数据集。

### 25.5.2 长文档阅读器

```kotlin
@Composable
fun DocumentReader(
    paragraphs: List<String>,
    chapter: Int
) {
    LazyColumn(
        modifier = Modifier.fillMaxSize()
    ) {
        item(key = "chapter-title-$chapter") {
            Text(
                text = "Chapter $chapter",
                style = MaterialTheme.typography.headlineMedium,
                modifier = Modifier.padding(16.dp)
            )
        }

        itemsIndexed(
            items = paragraphs,
            key = { index, paragraph -> "$index-${paragraph.hashCode()}" }
        ) { _, paragraph ->
            Text(
                text = paragraph,
                style = MaterialTheme.typography.bodyLarge,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                softWrap = true
            )
        }
    }
}
```

对长文档而言，优先避免一次性把所有段落放入 `Column.verticalScroll`。如果业务需要全文搜索、高亮、选择或分页，应单独验证富文本构造和滚动性能。

## 25.6 边界与限制

- **不要把 Android 17 直接等同于 Compose Text 性能提升**：除非有 AndroidX / AOSP 源码或 release notes 支撑，否则只能写“待验证”。
- **不要写固定收益数字**：例如“减少 60% 分配”“提升 40% 滚动流畅度”必须有可复现 benchmark；本章当前已移除这类数字。
- **不要引入未确认 API**：当前没有材料证明 `TextMetrics.calculate`、`Android17TextMetrics`、`PlatformFontLoadingStrategy.Async` 等示例可用，已从正文删除。
- **不要过度缓存**：全局 `mutableStateMapOf` 缓存可能引入生命周期、内存增长和状态一致性问题；缓存策略应绑定明确作用域。

## 25.7 Task6 复核清单

- [ ] 补充 AndroidX Compose Text 官方文档和源码路径。
- [ ] 补充 Compose release notes，确认是否存在与本文相关的 Text 行为变化。
- [ ] 用 Macrobenchmark 覆盖列表滚动、长文本展示、富文本构造、主题切换等场景。
- [ ] 用 Perfetto 或 Profiler 标注改动前后的 jank、主线程耗时、GC 和分配。
- [ ] 对 Android 10、Android 14、Android 17 至少各选一个测试环境，避免把单设备结果泛化。
- [ ] 复核所有 Kotlin 片段的可编译性与导入依赖。

## 25.8 当前结论

本章已经从“带有未来源化 Android 17 特性和收益数字的草稿”收敛为“Compose Text 性能复核清单”。由于本轮没有输入材料，状态继续保持 `draft`，置信度为 `low`。下一步应由 Task6 获取来源和实测后，再决定是否提升到 `ready-for-review`。
