---
title: "文字渲染性能"
chapter: "2.21"
status: ready-for-review
drafted_date: "2026-04-09"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-12"
last_verified_against: "AOSP android-16.0.0_r1 + androidx-main"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/widget/TextView.java"
  - type: aosp
    path: "frameworks/base/core/java/android/text/StaticLayout.java"
  - type: aosp
    path: "frameworks/base/core/java/android/text/BoringLayout.java"
  - type: aosp
    path: "frameworks/base/core/java/android/text/PrecomputedText.java"
  - type: aosp
    path: "frameworks/minikin/"
  - type: aosp
    path: "frameworks/base/libs/hwui/SkiaCanvas.cpp"
  - type: official
    path: "developer.android.com/reference/android/text/PrecomputedText"
tags: [text, rendering, minikin, skia, emoji, layout, performance, textview, staticlayout]
related_chapters: ["2.1", "2.4", "2.5", "7.8", "7.12"]
reviewed_by: openclaw-task6
reviewed_date: "2026-04-11"
task6_result: needs-rework
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: pending
task9_result: needs-rework
task2b_state: fixed
task2b_result: fixed
---

# 2.21 文字渲染性能

<!-- outline-start -->
## 本节大纲
- 🔹 为什么文字测量会成为列表与聊天场景的瓶颈
- 🔹 TextView、Layout、Minikin、Skia 组成的文字渲染流程
- 🔹 Minikin、StaticLayout、Emoji 的主要性能开销
- 🔹 PrecomputedText、BoringLayout 与参数裁剪的优化手段
- 🔹 在 Perfetto 中定位 measure 与 glyph upload 瓶颈
- 🔹 版本演进、常见误区与相关章节关联
<!-- outline-end -->

## 为什么要了解文字渲染

打开手机上任何一个 App——微信聊天、微博信息流、新闻客户端——占据屏幕面积最大的元素是什么？文字。

文字看起来简单，像是把几个字画到屏幕上。但在 Android 的渲染管线中，文字往往是 CPU 开销最高的绘制类型之一。原因很直接，文字渲染不是简单的像素拷贝，而是要经过“整形→测量→换行→光栅化→绘制”这一整套流程。其中“整形”（text shaping）和“测量”（measurement）尤其昂贵，需要根据字体、语言、上下文计算每个字符的精确位置，背后是 HarfBuzz 整形引擎和 ICU 换行算法的密集计算。

对于列表类 App（聊天、社交、新闻），一屏可能同时存在几十个 TextView。在滑动过程中，每个 TextView 都需要在 8.33ms（120Hz）或 16.67ms（60Hz）的帧预算内完成 measure → layout → draw 全流程。如果某个 TextView 的文字测量耗时超标，帧就掉了。

我们在 Perfetto 中经常看到这样的场景：主线程上一大片 "measure" slice 占了大半个 VSync 周期，展开一看全是 TextView.onMeasure()。这种情况在列表类 App 里很常见。

了解文字渲染的性能特征，能让我们在分析这类 jank 时更快定位到根因，不必在 View 层级里盲目猜测。

## Android 文字渲染管线全景

文字从 Java 层的 `TextView.setText()` 到最终在屏幕上显示，需要经过一条相当深的调用链。我们从头跟一遍。

当 App 调用 `TextView.setText()` 时，TextView 会根据文本内容选择一种 Layout 实现来管理文字的测量和布局。Android 提供了三种 Layout：

- **BoringLayout**：用于单行、纯文字、无 Span 的简单场景。它的测量逻辑最简单——直接调用 `Paint.measureText()` 拿到宽度，基本不做额外计算。如果 TextView 设置了 `setSingleLine(true)` 或 `maxLines=1`，且文本中没有任何 Span，大概率走这条路径。

- **StaticLayout**：用于多行文字。这是最常见的 Layout。StaticLayout 的构建过程包括：将文本按行切分（line breaking）、处理 Span 样式、计算每行的基线偏移、最终确定整体高度。这个过程涉及 Minikin 的文字整形和换行算法，CPU 开销显著高于 BoringLayout。

- **DynamicLayout**：用于可编辑文本（EditText）。它在 StaticLayout 的基础上增加了文本变化时的增量更新逻辑。

选好 Layout 之后，主线程已经拿到了每个 run 的测量结果、行分布和 glyph 位置信息。接下来进入 draw 阶段。这里要避开一个旧资料里很常见的坑：当前 Android 并不是沿着 `SkPaint::textToGlyphs()` → `SkDraw::drawPosText()` 这条旧调用往下走。以 `android-16.0.0_r1` 的 `frameworks/base/libs/hwui/SkiaCanvas.cpp` 为例，HWUI 的文字入口是 `SkiaCanvas::drawGlyphs()`，它先把 glyph 和坐标写进 `SkTextBlobBuilder`，再调用 `mCanvas->drawTextBlob()` 交给 Skia。

```cpp
// frameworks/base/libs/hwui/SkiaCanvas.cpp @ android-16.0.0_r1
void SkiaCanvas::drawGlyphs(...) {
    const SkTextBlobBuilder::RunBuffer& buffer = builder.allocRunPos(font, count);
    glyphFunc(buffer.glyphs, buffer.pos);
    sk_sp<SkTextBlob> textBlob(builder.make());
    mCanvas->drawTextBlob(textBlob, 0, 0, paint);
}
```

这段代码说明两件事。第一，Unicode 到 glyph 的整形主要发生在更早的 `Layout` / Minikin 阶段，HWUI 这一层负责把已经算好的 glyph run 组装后提交给 Skia。第二，当前更稳的描述层级应该是“Java Canvas / TextLine / Layout → HWUI `drawGlyphs()` → Skia `drawTextBlob()`”，不要把已经退场的内部函数名写成今天的真实实现。

Glyph atlas 仍然存在，首次出现的字形也仍可能触发 atlas miss、CPU 光栅化和纹理上传。但这些属于 Skia / HWUI 的内部实现细节，具体函数名会随版本变化；写到书里时保留到可直接核对的层级更稳。
[图：文字渲染管线架构图 — 展示 TextView.setText() → Layout 选择（BoringLayout / StaticLayout / DynamicLayout）→ Minikin 整形 + LineBreaker 换行 → HWUI drawGlyphs() → Skia drawTextBlob() → GPU glyph atlas 的完整路径，标注 measure 和 draw 两个瓶颈区间]

这条管线的性能瓶颈集中在两个地方：

1. **measure 阶段**（CPU 密集）：StaticLayout 的构建涉及 Minikin 文字整形和换行计算，复杂文本（CJK、阿拉伯语、Span 混排）的耗时远高于简单文本。[待验证：具体倍数需要 benchmark 数据支撑]
2. **draw 阶段的首次渲染**（GPU texture upload）：当 glyph 不在 atlas 中时，需要 CPU 光栅化 + GPU 上传，这可能在一帧内引入数毫秒的额外开销。

## Minikin 与文字测量性能

Minikin 是 Android 文字渲染的核心库，负责文字整形（text shaping）、换行（line breaking）和测量（measurement）。它的源码位于 `frameworks/minikin/`。

[已验证: AOSP android-16.0.0_r1, frameworks/minikin/]

Minikin 的内部架构可以简化为三层：

```
FontCollection（字体集合）
  → Layout（单行整形结果）
    → LineBreaker（多行换行结果）
```

**FontCollection** 负责字体匹配。当一段文字包含多种语言时（比如中英混排），Minikin 需要为每个字符找到最合适的字体文件，然后将相同字体的连续字符分成一个个 run。字体匹配本身是 O(n) 的遍历操作，但在字体集合较大时（系统可能加载了上百个字体文件），每个字符的匹配开销不可忽略。

**Layout** 负责对单个 run 进行 HarfBuzz 整形。HarfBuzz 会根据字体中的 OpenType 特性表，将 Unicode 码点序列转换为 glyph 序列，并计算每个 glyph 的精确位置偏移。这个过程是文字测量中最耗 CPU 的环节。一个关键的性能差异在于：

- 拉丁文字（英文、数字）：整形规则简单，通常 1 个 Unicode = 1 个 glyph，整形开销很低。
- CJK 文字（中文、日文、韩文）：整形规则比拉丁复杂，且字符集庞大（CJK Unified Ideographs 有数万个字符），字体查找开销更高。
- 复杂文字（阿拉伯语、印地语、泰语）：整形规则极度复杂，字符形态取决于上下文位置和连字规则。一个 Unicode 码点可能对应多个 glyph，也可能多个码点合并为一个 glyph。整形开销显著高于拉丁文字。[待验证：具体倍数需要 benchmark 数据支撑，当前无法给出可靠范围]

**LineBreaker** 负责多行文字的换行计算。它调用 ICU 的换行算法，根据语言规则决定在哪里断行。换行算法的复杂度与文本长度线性相关，但 ICU 的实现中涉及大量的字典查找（特别是 CJK，因为中文没有空格作为天然断点），所以 CJK 文本的换行开销明显高于拉丁文本。

一个容易被误判的点是 **Hyphenation**（连字符处理）。`android-6.0.1_r1` 的 `TextView.java` 构造默认值已经是 `mHyphenationFrequency = Layout.HYPHENATION_FREQUENCY_NONE`，所以系统默认并不是“全文开启连字符处理”。只有样式或代码把 hyphenation 频率调高时，换行阶段才会额外查 `Hyphenator` 字典并插入连字符。对聊天消息、列表标题这类短文本，我们通常不需要主动开启它。

### Minikin 的缓存策略

Minikin 内部维护了几层缓存来避免重复计算：

1. **Layout cache**：缓存相同文本+字体+宽度的整形结果。key 是 (text hash, paint params, available width)。如果文本内容相同且测量参数不变，直接命中缓存。
2. **FontCollection cache**：缓存字体集合的查找结果。
3. **ICU LineBreaker cache**：缓存换行迭代器的状态。

缓存失效的常见触发条件：
- 文本内容变化（最常见）
- 字体参数变化（textSize、textStyle、typeface）
- 可用宽度变化（比如屏幕旋转、RecyclerView 宽度变化）
- Locale 变化

在列表滑动场景中，RecyclerView 的 Item 宽度通常是固定的，文本内容会变化但可能存在重复（比如聊天消息中的相同文字）。理解这些缓存行为有助于我们判断：哪些情况下文字测量是"快"的（缓存命中），哪些情况下是"慢"的（缓存全miss）。

## StaticLayout 的性能特征

StaticLayout 是多行文字测量的核心类。它的构建过程可以简化为：

```
new StaticLayout(text, paint, width, align, spacingMult, spacingAdd)
  1. 将文本按 run 分组（相同字体、相同样式）
  2. 对每个 run 调用 Minikin 进行整形
  3. 调用 LineBreaker 按行切分
  4. 处理 Span 样式（如果有）
  5. 计算每行的基线、行高、行间距
  6. 缓存测量结果
```

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/text/StaticLayout.java]

在较新的代码里，我们更应该直接使用 **StaticLayout.Builder**。这个 Builder 至少在 `android-6.0.1_r1` 就已经存在，不是 Android 9 才出现。它把布局参数的设置集中到一处，也更容易和 `breakStrategy`、`hyphenationFrequency` 等参数一起核对。

```java
// 推荐用法（android-6.0.1_r1 已可见）
StaticLayout layout = StaticLayout.Builder.obtain(text, 0, text.length(), paint, maxWidth)
    .setAlignment(Layout.Alignment.ALIGN_NORMAL)
    .setLineSpacing(0f, 1f)
    .setIncludePad(true)
    .build();
```

### Span 对性能的影响

当文本中包含 Span（比如 `ForegroundColorSpan`、`StyleSpan`、`URLSpan`）时，StaticLayout 的测量开销会显著增加。原因是 Span 会将文本切分成更多更小的 run，每个 run 需要独立整形和测量。

特别要注意以下几种高开销 Span：

- **ReplacementSpan / ImageSpan**：替换文字为图片或自定义绘制内容。Layout 需要为每个 ReplacementSpan 调用 `getSize()` 和 `draw()`，这涉及额外的测量回调。
- **MetricAffectingSpan**（如 `AbsoluteSizeSpan`、`RelativeSizeSpan`）：改变文字尺寸的 Span。每次遇到这种 Span，都需要创建一个新的 Paint 副本并重新计算字形。
- **ClickableSpan**：虽然本身不影响测量，但设置了 ClickableSpan 的 TextView 通常需要设置 `movementMethod`，这会使 TextView 每次触摸事件都触发 `Spanned` 文本的遍历查找。

对于聊天 App 中常见的富文本消息（带表情、链接、@用户），一次 StaticLayout 构建的耗时通常比纯文本高出数倍。[待验证：具体倍数与 Span 类型和数量相关，需要实测数据]

### StaticLayout 的缓存命中

StaticLayout 本身不做缓存——每次创建新的 StaticLayout 实例都是重新测量。缓存行为发生在两个层面：

1. **TextView 内部**：如果 `setText()` 传入的文本和参数都没变，TextView 会复用上次创建的 Layout 对象，跳过测量。
2. **Minikin 层**：即使创建了新的 StaticLayout，如果 Minikin 的 Layout cache 能命中（文本 hash + 参数相同），整形步骤可以跳过。

所以真正慢的场景是：**新文本 + 新宽度 + 复杂 Span**。这在 RecyclerView 滑动中频繁发生——每个 Item 的文本不同、Span 不同，缓存几乎全 miss。

## Emoji 渲染性能

Emoji 这一节最容易写偏的地方，是把所有 emoji 都当成同一条渲染流程。站在当前可核对的 AOSP / AndroidX 实现上，我们至少要分清三件事。

**Android 4.4 - 7.1**：Emoji 主要依赖系统字体。它和普通文字一样参与字体 fallback、整形和绘制，只是字体文件里保存的是 color emoji glyph。这个阶段的主要问题，是字体版本跟系统版本绑定，新 emoji 很容易显示成 tofu。

**AndroidX EmojiCompat / emoji2**：App 侧如果要在旧系统上显示新 emoji，主流做法是接入 EmojiCompat。它不会把 emoji 统一改成“先 decode bitmap 再绘制”的固定流程，而是把文本里的 emoji 序列替换成 `EmojiSpan` / `TypefaceEmojiSpan`。绘制时，`TypefaceEmojiSpan.draw()` 会进一步走到 `TypefaceEmojiRasterizer.draw()`，临时切换到 emoji typeface，再调用 `canvas.drawText()` 输出 glyph。

```java
// androidx-main/emoji2/.../TypefaceEmojiRasterizer.java
paint.setTypeface(typeface);
canvas.drawText(mMetadataRepo.getEmojiCharArray(), charArrayStartIndex, 2, x, y, paint);
```

**字体来源**：EmojiCompat 有两种常见配置。`FontRequestEmojiCompatConfig` 走 downloadable font provider，`BundledEmojiCompatConfig` 把字体和元数据随 APK 一起打包。前者更省 APK 体积，后者更容易控制离线可用性。

### Emoji 渲染版本与实现边界

分析性能时，我们至少要分清三条路径：

1. **系统 emoji font**：系统字体直接提供 glyph，开销落在字体 fallback、shaping、rasterization 和缓存命中上。
2. **EmojiCompat / emoji2 span**：`EmojiSpan` 会把文本切成更多 run，`getSize()` / `draw()` 也会增加一次 span 级开销。
3. **下载字体 provider**：首次加载的成本在字体元数据初始化和字体文件准备，不等于每次绘制都走 bitmap decode。

所以，这一章不再把“Android 11 之后统一转向 bitmap emoji”写成版本事实。基于当前能核对的实现，更稳的结论是：emoji 可能让 run 数量变多、span 测量变重、首帧字体准备更慢；至于某台设备上是否会出现明显的 GPU upload 突刺，还要结合字体、字符集和机型继续核实。

## 文字渲染优化实践

### PrecomputedText：提前做字符测量，不替代最终布局

`PrecomputedText` 是 Android 9.0 (API 28) 引入的 API，用来把“可以脱离 `TextView` 独立完成”的文字测量工作提前做掉。AOSP 在 `PrecomputedText.Params` 注释里把边界写得很直接：这些参数用于在 **final layout constraints are not known** 时预计算测量元数据。这里提前完成的是字符度量、段落边界、`breakStrategy` / `hyphenationFrequency` 相关准备，不是把最终宽度已经确定的 `StaticLayout` 整体缓存下来。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/text/PrecomputedText.java]

```java
PrecomputedText.Params params = textView.getTextMetricsParams();
PrecomputedText precomputed = PrecomputedText.create(text, params);
textView.setText(precomputed);
```

这个模式能省掉一大块主线程上的 shaping / measurement 开销，但最终布局仍然要看 `TextView` 当时的宽度、`maxLines`、`ellipsize`、行距等条件。如果 `TextView` 当前参数和创建 `PrecomputedText` 时不一致，框架会直接丢弃预计算结果，按当前参数重新计算。

所以，PrecomputedText 更准确的理解是“提前做 `MeasuredText` / 段落测量准备”，不是“主线程完全跳过 `StaticLayout`”。

### AppCompatTextView 的异步接入方式

Jetpack 里对应的能力来自 `PrecomputedTextCompat.getTextFuture()` 和 `AppCompatTextView.setTextFuture()`，不是 Android 14 新增的平台自动行为。`AppCompatTextView` 在 `onMeasure()` 之前会调用 `consumeTextFutureAndSetBlocking()` 取回 future 结果，所以后台线程是谁来执行，仍然由调用方提供的 `Executor` 决定。

```java
PrecomputedTextCompat.Params params = TextViewCompat.getTextMetricsParams(textView);
Future<PrecomputedTextCompat> future =
        PrecomputedTextCompat.getTextFuture(text, params, executor);
textView.setTextFuture(future);
```

这一套更适合 RecyclerView：在 `onBindViewHolder()` 之前启动预计算，把字体、字号、break strategy 这些固定参数先固定下来，再让 `AppCompatTextView` 在测量前消费结果。

有一个边界必须记住：`TextMetricsParams` 包含的是字体、字号、text direction、break strategy、hyphenation 等测量参数，不包含最终可用宽度本身。宽度约束一旦变化，最终 layout 仍可能在主线程重建。这个边界决定了 PrecomputedText 更适合“文本长、参数稳定、宽度相对固定”的场景。

### BoringLayout：单行场景的最优选择

如果 TextView 确实只显示单行文字（比如列表项的标题、按钮文字），且不含 Span，系统通常会自动选择 BoringLayout。但有时候因为 XML 中设置了某些属性（如 `maxLines`），系统可能误选 StaticLayout。

可以通过以下方式帮助系统选择 BoringLayout：

```xml
<TextView
    android:singleLine="true"    <!-- 已废弃但仍有效 -->
    android:maxLines="1"
    android:ellipsize="end" />
```

或者代码中：
```java
textView.setSingleLine(true);
```

BoringLayout 的测量只调用一次 `Paint.measureText()`，开销远低于 StaticLayout 的多行整形与换行计算。[待验证：具体耗时比需要 benchmark 数据]

### 避免误开 Hyphenation

默认 `TextView` 已经是 `HYPHENATION_FREQUENCY_NONE`。真正需要处理的是：项目样式、富文本阅读页，或者某些排版组件把 hyphenation 显式开成 `normal` / `full`。如果场景是短文本、列表项或 CJK 为主的内容，把它关回 `none` 往往更稳。

```java
// XML 方式
<TextView
    android:hyphenationFrequency="none" />

// 代码方式
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
    textView.setHyphenationFrequency(Layout.HYPHENATION_FREQUENCY_NONE);
}
```

这类设置更像是在防止样式误伤，而不是去覆盖系统默认值。

### IncludeFontPadding 的影响

`textView.setIncludePad(true)` 是默认值，它会在文字上下添加额外的留白以容纳字体中的 ascender/descender。这会导致：

1. 测量结果的高度比文字实际显示高度更大（可能多出 20-30%）
2. 在精确布局时需要额外处理上下间距

对于不需要严格字体留白的场景（比如列表项的文字区域），关闭 IncludeFontPadding 可以获得更紧凑的布局，同时测量结果更精确：

```java
textView.setIncludeFontPadding(false);
```

### 文字缓存策略

除了 Minikin 内部的缓存，还有两个与文字缓存相关的机制：

1. **TextLine cache**：`TextLine` 是绘制单行文字的内部类（引入版本待核对），系统会缓存 TextLine 对象（对象池模式），避免每次 drawText 都创建新对象。

2. **Skia TextBlob cache**：Skia 维护的 glyph 批量绘制缓存。当多个连续的 drawText 调用被合并为一个 TextBlob 时，Skia 可以一次性提交给 GPU，减少 draw call 数量。Android 的 RenderThread 在某些条件下会自动将文字绘制合并为 TextBlob。

这两个缓存对开发者是透明的，但在 Perfetto 里有时能观察到它们的效果：当 TextBlob 缓存命中时，draw 阶段的耗时会缩短。

## 在 Perfetto 中识别文字渲染瓶颈

文字渲染性能问题在 Perfetto 中有几种典型表现：

### 主线程 measure 耗时过长

在主线程 track 上找到 `Choreographer#doFrame` slice，展开后找到 `performTraversals` → `measure`。如果 measure 的子 slice 中大量出现 `TextView.onMeasure()`，且单次耗时超过 1ms，说明文字测量是瓶颈。

当一条聊天消息有多个 Span（用户名、链接、表情）时，单个 TextView 的 onMeasure 可能耗时数毫秒（与文本长度、Span 复杂度和设备性能相关）。[待验证：具体耗时需要结合设备与负载条件 benchmark]在 120Hz 设备上（8.33ms 帧预算），一个 Item 有 3 个 TextView 就可能吃掉整个帧预算。

[图：Perfetto Trace 截图 — 主线程 doFrame 展开，measure 子 slice 中多个 TextView.onMeasure() 累计耗时超过帧预算，对应 FrameTimeline 标记的红色 jank 帧。标注关键区域：performTraversals → measure → TextView.onMeasure()]

### 文字渲染在 Perfetto 中的可观测面

这个话题最容易写飘。默认 Perfetto trace 能稳定看到的，主要是 MainThread 上的 `performTraversals → measure / layout`，以及其中的 `TextView.onMeasure()`。如果这里已经占满一帧，根因通常就在文字测量、span 处理或布局约束变化上。

RenderThread / HWUI 侧当然也可能有文字相关成本，但要分清“能推测”和“能稳定看见”：
- **默认 trace**：更适合看 MainThread 的 measure 开销。
- **额外打开 `gfx`、`view`、`hwui` 等 atrace 类别**：能看到录制、提交、上传这类更细的渲染工作。
- **具体 slice 名称**：会随 Android 版本、厂商定制和 trace 配置变化，不适合把 `drawPosText`、`TextBlob` 这类名字当成通用检查清单。

如果你在某台设备上观察到首次 emoji / 生僻字渲染伴随 RenderThread 或 GPU 侧的 upload 突刺，那是一个需要结合 trace 配置和机型继续核实的现象，不是所有设备都会露出的固定 slice。

### 定位建议

[图：Perfetto Trace 对比截图 — 左侧为正常帧（measure 耗时 < 1ms），右侧为文字测量 jank 帧（measure 耗时 > 5ms），标注 FrameTimeline 颜色差异和 VSYNC-app 间隔]

如果怀疑文字渲染是 jank 根因，推荐的分析路径：

1. 在 Perfetto 中找到 jank 帧（FrameTimeline 标记的红色帧）
2. 检查主线程 measure 阶段是否有大量 `TextView.onMeasure()`
3. 如果有，回到对应 Item 的文本内容，确认是不是复杂 Span、长文本，或者多语种混排
4. 评估能不能用 PrecomputedText、BoringLayout、hyphenation 参数裁剪去减轻主线程测量
5. 只有在 trace 配置包含 `gfx` / `hwui` 类别时，再去看 RenderThread 或 GPU 侧有没有 upload / 录制突刺

## 版本演进

下面只保留能直接核对到 tag、源码或官方文档的节点，拿不稳的版本判断先不写。

| 版本 / 组件 | 可直接核对的变化 | 证据锚点 |
|-------------|------------------|----------|
| Android 5.0 (API 21) | AOSP 已有独立 `frameworks/minikin/` 仓库，文字整形与换行能力集中到 Minikin | `platform/frameworks/minikin` @ `android-5.0.0_r1` |
| Android 6.0.1 (API 23) | `StaticLayout.Builder` 已存在；`TextView` 构造默认 `mHyphenationFrequency = HYPHENATION_FREQUENCY_NONE` | `StaticLayout.java` / `TextView.java` @ `android-6.0.1_r1` |
| Android 9.0 (API 28) | framework 引入 `PrecomputedText` | Android Developers `PrecomputedText` reference（Added in API 28） |
| AndroidX core / appcompat | `PrecomputedTextCompat.getTextFuture()` 配合 `AppCompatTextView.setTextFuture()` 提供异步预计算接入 | androidx-main `PrecomputedTextCompat.java` / `AppCompatTextView.java` |
| AndroidX emoji / emoji2 | `EmojiCompat` 通过 `EmojiSpan` / `TypefaceEmojiSpan` 兼容新 emoji，字体来源可选 bundled 或 downloadable font provider | Android Developers EmojiCompat 文档；androidx-main `TypefaceEmojiSpan.java` |

这张表没有再写“Android 11 统一切到 bitmap emoji”或“Android 14 自动后台测量”这类说法，因为它们对不上当前能核对的源码与文档。

## 常见问题与误区

**误区：TextView.setText() 很轻量，不需要优化。**

setText() 本身只是设置 CharSequence 引用，确实很快。但 setText() 会触发 `checkForRelayout()`，最终在下一个 VSync 周期的 `performTraversals()` 中执行 measure → layout → draw。如果你在 `onBindViewHolder()` 中调用了 setText()，那么 measure 的开销就计入了这一帧。

**误区：PrecomputedText 能解决所有文字测量问题。**

PrecomputedText 的前提是：TextView 的参数（宽度、字体、字号等）在预计算后不能变。如果 RecyclerView 的 Item 宽度在滑动过程中变化（比如有动画或滑动偏移），PrecomputedText 可能反复失效。

**误区：文字缓存会自动帮我优化。**

Minikin 的缓存是进程级的，跨 TextView 共享。但缓存的 key 包含文本内容 hash，不同文本几乎不可能命中彼此的缓存。在列表滑动场景中，每个 Item 的文本通常是不同的，缓存命中率很低。

**常见面试问题：RecyclerView 列表中，聊天消息的 TextView 经常导致 jank，你会怎么优化？**

思路：
1. 先确认是否是 StaticLayout 测量耗时（Perfetto 中验证）
2. 如果确认，优先使用 PrecomputedText 将测量移到 DiffUtil 的后台线程
3. 关闭不必要的 hyphenation 和 IncludeFontPadding
4. 检查是否有大量 Span 导致 run 切分过多，考虑简化 Span 结构
5. 检查 Emoji 数量是否过多，考虑对纯 Emoji 消息使用单独的布局

## 与其他机制的关系

- **§2.4 Choreographer**：TextView 的 measure/layout/draw 由 Choreographer 在 VSYNC-app 信号到来时统一调度。文字测量的耗时直接占用了 doFrame 的时间预算。
- **§2.5 MainThread/RenderThread**：文字测量发生在 MainThread，文字绘制（glyph 光栅化、texture upload）发生在 RenderThread。
- **§7.8 RecyclerView 列表滑动性能深度优化**：RecyclerView 的滑动流畅性高度依赖 TextView 的测量效率，PrecomputedText 是核心优化手段。
- **§7.12 View 体系性能**：TextView.onMeasure() 是 View 层级 measure 开销的主要贡献者之一，深嵌套层级中的多个 TextView 会叠加出显著的 measure 耗时。

## 参考资料

- [AOSP frameworks/minikin/](https://android.googlesource.com/platform/frameworks/minikin/) — Minikin 文字整形库
- [AOSP TextView.java](https://android.googlesource.com/platform/frameworks/base/+/master/core/java/android/widget/TextView.java) — TextView 源码
- [AOSP StaticLayout.java](https://android.googlesource.com/platform/frameworks/base/+/master/core/java/android/text/StaticLayout.java) — StaticLayout 源码
- [AOSP PrecomputedText.java](https://android.googlesource.com/platform/frameworks/base/+/master/core/java/android/text/PrecomputedText.java) — PrecomputedText API
- [Android Developers - PrecomputedText](https://developer.android.com/reference/android/text/PrecomputedText) — 官方文档
- [Android Developers - AppCompatTextView](https://developer.android.com/reference/androidx/appcompat/widget/AppCompatTextView) — AndroidX 文档
- [Android Developers - EmojiCompat](https://developer.android.com/develop/ui/views/text-and-emoji/emoji-compat) — Emoji 兼容与字体配置文档
- [Medium - PrecomputedText: Improving Text Rendering](https://medium.com/androiddevelopers/precomputedtext-improving-text-rendering-6f04345b079c) — Android Developers Blog
