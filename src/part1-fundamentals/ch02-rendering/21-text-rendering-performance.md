---
title: "文字渲染性能"
chapter: "2.21"
status: ready-for-review
drafted_date: "2026-04-09"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-09"
last_verified_against: "AOSP android-16.0.0_r1"
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
related_chapters: ["2.1", "2.4", "2.5", "7.5", "7.12"]
---

# 2.21 文字渲染性能

## 为什么要了解文字渲染

打开手机上任何一个 App——微信聊天、微博信息流、新闻客户端——占据屏幕面积最大的元素是什么？文字。

文字看起来简单，不就是画几个字嘛。但在 Android 的渲染管线中，文字恰恰是 CPU 开销最高的绘制类型之一。原因在于：文字不是简单的像素拷贝，而是需要经过"整形→测量→换行→光栅化→绘制"一整套流水线。其中"整形"（text shaping）和"测量"（measurement）尤其昂贵——它们需要根据字体、语言、上下文计算出每个字符的精确位置，涉及 HarfBuzz 整形引擎和 ICU 换行算法的密集计算。

对于列表类 App（聊天、社交、新闻），一屏可能同时存在几十个 TextView。在滑动过程中，每个 TextView 都需要在 8.33ms（120Hz）或 16.67ms（60Hz）的帧预算内完成 measure → layout → draw 全流程。如果某个 TextView 的文字测量耗时超标，帧就掉了。

我们在 Perfetto 中经常看到的场景是：主线程上一大片 "measure" slice 占了大半个 VSync 周期，展开一看全是 TextView.onMeasure()。这不是个例，而是列表类 App 的通病。

了解文字渲染的性能特征，能让你在分析这类 jank 时直接定位到根因，而不是在 View 层级里盲目猜测。

## Android 文字渲染管线全景

文字从 Java 层的 `TextView.setText()` 到最终在屏幕上显示，需要经过一条相当深的调用链。我们从头跟一遍。

当 App 调用 `TextView.setText()` 时，TextView 会根据文本内容选择一种 Layout 实现来管理文字的测量和布局。Android 提供了三种 Layout：

- **BoringLayout**：用于单行、纯文字、无 Span 的简单场景。它的测量逻辑最简单——直接调用 `Paint.measureText()` 拿到宽度，基本不做额外计算。如果 TextView 设置了 `setSingleLine(true)` 或 `maxLines=1`，且文本中没有任何 Span，大概率走这条路径。

- **StaticLayout**：用于多行文字。这是最常见的 Layout。StaticLayout 的构建过程包括：将文本按行切分（line breaking）、处理 Span 样式、计算每行的基线偏移、最终确定整体高度。这个过程涉及 Minikin 的文字整形和换行算法，CPU 开销显著高于 BoringLayout。

- **DynamicLayout**：用于可编辑文本（EditText）。它在 StaticLayout 的基础上增加了文本变化时的增量更新逻辑。

选好 Layout 之后，文字测量（measure）阶段就算完成了。接下来是 layout 和 draw。在 draw 阶段，Canvas 会调用 `drawText()` 或 `drawTextRun()` 将文字绘制到 Canvas 上。这里的底层调用链是：

```
Canvas.drawText()
  → SkiaCanvas.drawText()
    → SkPaint::textToGlyphs()  // Unicode → Glyph ID 映射
    → SkDraw::drawPosText()    // 按位置绘制 glyph
      → SkGlyphCache::getGlyphMetrics()  // 从 glyph atlas 获取位图
      → GPU texture upload（如果 glyph 不在 atlas 中）
```

Skia 维护了一个 **Glyph Atlas**——一张大的 GPU 纹理，上面缓存了已光栅化好的 glyph 位图。当需要绘制一个字符时，Skia 先查 atlas，找到了就直接从 GPU 纹理中采样，找不到才触发 CPU 光栅化再上传到 atlas。这意味着文字渲染的性能高度依赖 glyph atlas 的缓存命中率。

[待补充：文字渲染管线架构图，展示 TextView → Layout → Minikin → Skia → GPU 的完整路径]

这条管线的性能瓶颈集中在两个地方：

1. **measure 阶段**（CPU 密集）：StaticLayout 的构建涉及 Minikin 文字整形和换行计算，复杂文本（CJK、阿拉伯语、Span 混排）的耗时可能是简单文本的 5-10 倍。
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
- 复杂文字（阿拉伯语、印地语、泰语）：整形规则极度复杂，字符形态取决于上下文位置和连字规则。一个 Unicode 码点可能对应多个 glyph，也可能多个码点合并为一个 glyph。整形开销是拉丁文字的 5-10 倍。

[待验证：CJK 整形开销相对拉丁文字的倍数，需要实际 benchmark 数据]

**LineBreaker** 负责多行文字的换行计算。它调用 ICU 的换行算法，根据语言规则决定在哪里断行。换行算法的复杂度与文本长度线性相关，但 ICU 的实现中涉及大量的字典查找（特别是 CJK，因为中文没有空格作为天然断点），所以 CJK 文本的换行开销明显高于拉丁文本。

一个容易被忽略的性能点是 **Hyphenation**（连字符处理）。从 Android 6.0 开始，TextView 默认开启 hyphenation。当一行文字在某个单词中间断开时，系统需要查 hyphenation 字典确定合法的断点位置，并插入连字符。这个操作涉及 ICU 的 Hyphenator 查找，对于长文本可能产生可测量的性能影响。如果 App 不需要 hyphenation（比如聊天消息、列表项），可以通过 `textView.setHyphenationFrequency(Layout.HYPHENATION_FREQUENCY_NONE)` 显式关闭。

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

从 Android 9.0 (API 28) 开始，Google 引入了 **StaticLayout.Builder**，替代直接调用构造函数的方式。Builder 提供了更清晰的 API，并且在内部做了优化：将布局参数的解析和验证提前到 Builder 阶段，减少了 StaticLayout 构造函数内部的重复计算。

```java
// 推荐用法（Android 9+）
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

对于聊天 App 中常见的富文本消息（带表情、链接、@用户），一次 StaticLayout 构建的耗时可能是纯文本的 2-3 倍。

### StaticLayout 的缓存命中

StaticLayout 本身不做缓存——每次创建新的 StaticLayout 实例都是重新测量。缓存行为发生在两个层面：

1. **TextView 内部**：如果 `setText()` 传入的文本和参数都没变，TextView 会复用上次创建的 Layout 对象，跳过测量。
2. **Minikin 层**：即使创建了新的 StaticLayout，如果 Minikin 的 Layout cache 能命中（文本 hash + 参数相同），整形步骤可以跳过。

所以真正慢的场景是：**新文本 + 新宽度 + 复杂 Span**。这在 RecyclerView 滑动中频繁发生——每个 Item 的文本不同、Span 不同，缓存几乎全 miss。

## Emoji 渲染性能

Emoji 的渲染路径与普通文字不同。Android 系统对 Emoji 的处理经历了几个阶段的演进：

**Android 4.4 - 7.1**：Emoji 由系统字体提供。每个 Emoji 对应字体文件中的一个 glyph，通过正常的文字渲染管线绘制。这种方式的问题是：系统字体不能及时更新新 Emoji，导致不同版本的 Android 显示的 Emoji 不一致（显示为 □）。

**Android 8.0+**：引入了 EmojiCompat 兼容库。EmojiCompat 的工作原理是：初始化时加载一个独立的 Emoji 字体文件（`NotoColorCompat.ttf` 或 `MicrosoftCompatibilityFont.ttf`），通过 `EmojiSpan`（一种 ReplacementSpan）将文本中的 Emoji 替换为字体中的 glyph。

[已验证: AOSP android-16.0.0_r1, frameworks/support/emoji2/]

EmojiCompat 的初始化本身是一个性能关注点。字体文件通常 5-15MB，加载和解析需要 50-200ms。Google 提供了两种初始化方式：

1. **BundledFontConfig**：字体文件打包在 APK 内。初始化快，但增大了 APK 体积。
2. **DefaultEmojiCompatConfig**（推荐）：从系统下载字体。首次使用需要网络下载，之后缓存在本地。

在聊天类 App 中，大量 Emoji 的混合文本（比如 "😂😂😂你好😊"）性能值得关注。每个 Emoji 都是一个独立的 EmojiSpan，StaticLayout 需要为每个 Span 单独测量和绘制。当一条消息包含 20+ 个 Emoji 时，测量耗时可能翻倍。

### Bitmap Emoji vs 系统 glyph

从 Android 11 开始，系统 Emoji 渲染路径开始转向基于 Bitmap 的方式。Bitmap Emoji 的绘制流程是：解码 bitmap → 上传到 GPU 纹理 → 绘制。首次绘制的 decode + upload 开销是普通 glyph 的 10 倍以上（因为涉及图像解码而非矢量光栅化）。

对于列表滑动场景，大量 Bitmap Emoji 的 decode 可能导致 RenderThread 的 texture upload 耗时超标，表现为 RenderThread track 上的长 slice。

## 文字渲染优化实践

### PrecomputedText：将测量移到后台线程

PrecomputedText 是 Android 9.0 (API 28) 引入的 API，核心思路是：将文字测量（measure）从主线程移到后台线程，提前计算好 StaticLayout 的测量结果，主线程只需执行 layout 和 draw。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/text/PrecomputedText.java]

使用方式分两步：

**第一步：后台线程创建 PrecomputedText**

```java
// 在后台线程（如 RecyclerView 的 DiffUtil 回调中）
PrecomputedText.Params params = textView.getTextMetricsParams();
PrecomputedText precomputed = PrecomputedText.create(text, params);
```

`PrecomputedText.create()` 内部执行的就是 StaticLayout 的全部测量逻辑：文字整形、换行计算、Span 处理。但因为不在主线程，不会阻塞帧渲染。

**第二步：主线程设置预计算结果**

```java
// 在主线程（onBindViewHolder 中）
textView.setTextMetricsParams(precomputed.getParams());
textView.setText(precomputed);
```

主线程的 `setText()` 检测到参数是 PrecomputedText，直接跳过测量，使用预计算结果。这在 Perfetto 中表现为 `TextView.onMeasure()` 的耗时从可能的 1-5ms 降到 0.01ms。

有一个关键约束：**PrecomputedText 的 Params 必须与 TextView 的当前参数完全匹配**。如果 textSize、typeface、width 等参数在创建 PrecomputedText 之后发生了变化，系统会回退到正常的测量路径，PrecomputedText 就白做了。所以 PrecomputedText 适合 TextView 参数固定的场景（比如 RecyclerView 中 Item 的固定宽度文字区域）。

从 Android 14 开始，Jetpack 的 `AppCompatTextView` 在设置了 `setPrecomputedText()` 后会自动在后台线程执行测量，开发者不需要手动管理线程。

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

BoringLayout 的测量只调用一次 `Paint.measureText()`，耗时通常是 StaticLayout 的 1/10 以下。

### 关闭不必要的 Hyphenation

如前所述，hyphenation 的换行字典查找对 CJK 文本几乎没有意义（中文不使用连字符），但默认可能是开启的。对于不需要 hyphenation 的场景：

```java
// XML 方式（Android 9+）
<TextView
    android:hyphenationFrequency="none" />

// 代码方式
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
    textView.setHyphenationFrequency(Layout.HYPHENATION_FREQUENCY_NONE);
}
```

[待验证：Android 9+ 是否已将默认 hyphenation 改为频率较低的算法]

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

1. **TextLine cache**：Android 8.0 引入。`TextLine` 是绘制单行文字的内部类，系统会缓存 TextLine 对象（对象池模式），避免每次 drawText 都创建新对象。

2. **Skia TextBlob cache**：Skia 维护的 glyph 批量绘制缓存。当多个连续的 drawText 调用被合并为一个 TextBlob 时，Skia 可以一次性提交给 GPU，减少 draw call 数量。Android 的 RenderThread 在某些条件下会自动将文字绘制合并为 TextBlob。

这两个缓存对开发者是透明的，但在 Perfetto 中可以看到它们的效果：当 TextBlob 缓存命中时，draw 阶段的耗时明显缩短。

## 在 Perfetto 中识别文字渲染瓶颈

文字渲染性能问题在 Perfetto 中有几种典型表现：

### 主线程 measure 耗时过长

在主线程 track 上找到 `Choreographer#doFrame` slice，展开后找到 `performTraversals` → `measure`。如果 measure 的子 slice 中大量出现 `TextView.onMeasure()`，且单次耗时超过 1ms，说明文字测量是瓶颈。

当一条聊天消息有多个 Span（用户名、链接、表情）时，单个 TextView 的 onMeasure 可能耗时 2-5ms。在 120Hz 设备上（8.33ms 帧预算），一个 Item 有 3 个 TextView 就可能吃掉整个帧预算。

[待补充：Perfetto 截图，展示文字 measure 导致的 jank 帧]

### RenderThread 的文字相关开销

RenderThread track 上，文字渲染主要出现在：
- **drawText/drawPosText** slice：文字绘制的基本单元
- **Glyph cache miss**：当新字符首次渲染时，可以看到 GPU texture upload 的耗时突刺

如果 RenderThread 中频繁出现 glyph upload 突刺，通常意味着 App 使用了大量不同的字体或字符集，导致 glyph atlas 频繁淘汰和重建。

### Skia TextBlob 相关指标

在开启了 `android.graphics.Bitmap` atrace 标签的 Trace 中，可以观察 TextBlob 的缓存命中情况。不过这个指标需要自定义 Trace 配置，默认的 Perfetto 抓取可能不包含。

### 定位建议

如果怀疑文字渲染是 jank 根因，推荐的分析路径：

1. 在 Perfetto 中找到 jank 帧（FrameTimeline 标记的红色帧）
2. 检查主线程 measure 阶段是否有大量 TextView.onMeasure()
3. 如果有，检查对应 Item 的文本内容——是否有复杂 Span？长文本？CJK + 阿拉伯语混排？
4. 检查是否可以应用 PrecomputedText
5. 检查 RenderThread 是否有 glyph upload 突刺

## 版本演进

| 版本 | 变化 |
|------|------|
| Android 4.4 (API 19) | 引入 Minikin 库，替代此前 HarfBuzz 直接集成的方式 |
| Android 7.0 (API 24) | 引入 EmojiCompat 兼容库概念 |
| Android 8.0 (API 26) | 正式发布 EmojiCompat；引入 Hardware Bitmap（间接影响文字+图片混合内容的渲染） |
| Android 9.0 (API 28) | 引入 PrecomputedText API；StaticLayout.Builder 成为推荐 API |
| Android 10 (API 29) | Hyphenation 默认频率降低（减少性能开销） |
| Android 11 (API 30) | 系统 Emoji 开始转向 Bitmap 渲染路径 |
| Android 12 (API 31) | 优化了 Minikin 的缓存策略，减少了重复测量时的 CPU 开销 |
| Android 14 (API 34) | AppCompatTextView 自动集成 PrecomputedText 后台测量 |
| Android 16 (API 36) | [待验证：是否有新的文字渲染优化] |

## 常见问题与误区

**误区：TextView.setText() 很轻量，不需要优化。**

 setText() 本身只是设置 CharSequence 引用，确实很快。但 setText() 会触发 `checkForRelayout()`，最终在下一个 VSync 周期的 `performTraversals()` 中执行 measure → layout → draw。如果你在 `onBindViewHolder()` 中调用了 setText()，那么 measure 的开销就计入了这一帧。

**误区：PrecomputedText 能解决所有文字测量问题。**

PrecomputedText 的前提是：TextView 的参数（宽度、字体、字号等）在预计算后不能变。如果 RecyclerView 的 Item 宽度在滑动过程中变化（比如有动画或滑动偏移），PrecomputedText 可能反复失效。

**误区：文字缓存会自动帮我优化。**

Minikin 的缓存是进程级的，跨 TextView 共享。但缓存的 key 包含文本内容 hash——这意味着不同文本几乎不可能命中彼此的缓存。在列表滑动场景中，每个 Item 的文本通常是不同的，缓存命中率很低。

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
- **§7.5 列表滑动优化**：RecyclerView 的滑动流畅性高度依赖 TextView 的测量效率，PrecomputedText 是核心优化手段。
- **§7.12 View 体系性能**：TextView.onMeasure() 是 View 层级 measure 开销的主要贡献者之一，深嵌套层级中的多个 TextView 会叠加出显著的 measure 耗时。

## 参考资料

- [AOSP frameworks/minikin/](https://android.googlesource.com/platform/frameworks/minikin/) — Minikin 文字整形库
- [AOSP TextView.java](https://android.googlesource.com/platform/frameworks/base/+/master/core/java/android/widget/TextView.java) — TextView 源码
- [AOSP StaticLayout.java](https://android.googlesource.com/platform/frameworks/base/+/master/core/java/android/text/StaticLayout.java) — StaticLayout 源码
- [AOSP PrecomputedText.java](https://android.googlesource.com/platform/frameworks/base/+/master/core/java/android/text/PrecomputedText.java) — PrecomputedText API
- [Android Developers - PrecomputedText](https://developer.android.com/reference/android/text/PrecomputedText) — 官方文档
- [Android Developers - Text Performance](https://developer.android.com/topic/performance/text) — 官方文字性能指南
- [Medium - PrecomputedText: Improving Text Rendering](https://medium.com/androiddevelopers/precomputedtext-improving-text-rendering-6f04345b079c) — Android Developers Blog
