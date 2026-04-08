---
title: "文字渲染性能"
chapter: "2.21"
status: draft
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
tags: [text, rendering, minikin, skia, emoji, layout, performance]
related_chapters: ["2.1", "2.4", "7.8", "7.12"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-09"
gap_source: "AOSP结构+读者需求"
gap_score: 14
---

# 2.21 文字渲染性能

<!-- outline-start -->
## 要点

### 🔹 锚点 1：为什么文字渲染性能值得关注
- 文字是 Android UI 中最基础的绘制单元：聊天、新闻、社交 App 中文字占比极高
- TextView.measure() 是列表滑动 jank 的常见根源
- 文字渲染管线涉及 CPU 密集的文字整形（shaping）操作
- Emoji 渲染的额外开销：Bitmap/Vector emoji 的 decode 和 draw 开销
- 一个聊天 App 每帧可能需要 measure/layout 数十个 TextView

### 🔹 锚点 2：Android 文字渲染管线全景
- TextView → Layout → StaticLayout/BoringLayout → Minikin → Skia → GPU
- Minikin 的角色：文字整形（text shaping）、换行（line breaking）、测量（measurement）
- Skia 文字绘制路径：TextBlob 缓存 → GPU Glyph Atlas → drawPosText
- BoringLayout vs StaticLayout：单行 vs 多行的性能差异
- PrecomputedText（Android 9+）：将文字测量移到后台线程

### 🔹 锚点 3：Minikin 与文字测量性能
- Minikin 内部架构：FontCollection → Layout → LineBreaker
- getLineBounds/getDesiredWidth 的 CPU 开销：字体查找 + ICU 换行算法
- 复杂文字（CJK、阿拉伯语、印地语）的整形开销远高于拉丁文字
- Tab/space 对齐、Span 对齐对测量性能的影响
- Minikin 的缓存策略与失效条件

### 🔹 锚点 4：StaticLayout 的性能特征
- StaticLayout.Builder 的构建开销：文本 → 测量 → 换行 → 缓存
- Spanned 文字的额外测量开销：CharacterStyle/SubstitutionSpan/ReplacementSpan
- ImageSpan 和 ReplacementSpan 对布局稳定性的影响
- StaticLayout 缓存命中条件与失效触发
- 超长文本（如小说/长文）的 measure 性能陷阱

### 🔹 锚点 5：Emoji 渲染性能
- Emoji 的渲染路径：Unicode → EmojiCompat → BitmapFont/SvgEmoji → draw
- Bitmap emoji 的 decode 开销：首次加载的冷启动延迟
- EmojiCompat 的初始化性能：GlymphChecker 的字体加载时间
- 系统版本差异：不同 Android 版本的 emoji 实现方式
- 大量 emoji 的混合文本渲染性能（如聊天消息）

### 🔹 键点 6：文字渲染优化实践
- PrecomputedText 的集成：测量与布局的线程分离
- TextView.setSingleLine()/setMaxLines() 的性能提示
- IncludeFontPadding 的性能影响
- 使用 BoringLayout 替代 StaticLayout（单行场景）
- 文字缓存策略：TextLine cache、Skia TextBlob cache
- Hyphenation 的性能开关：setHyphenationFrequency 对 layout 速度的影响

### 🔹 锚点 7：在 Perfetto 中识别文字渲染瓶颈
- TextView measure/layout 在 Main Thread 上的占比
- Minikin 相关的 trace point：text measurement / line breaking
- Skia TextBlob 缓存命中率分析
- 文字渲染导致的 RenderThread 开销

## 扩展

### 🔸 扩展点 1：Jetpack Compose 文字渲染性能
- Compose Text vs Android TextView 的渲染路径差异
- Compose 的 Paragraph（Skia Paragraph）vs Minikin
- Compose Text 的测量重组合并（skip/restart）策略

### 🔸 扩展点 2：自定义字体（ downloadable fonts）性能
- Google Fonts API 的异步加载机制
- 字体文件解析（ttf/otf/woff2）的 CPU 开销
- 自定义字体对文字测量缓存的影响
- 多字重（Variable Font）的性能优势

<!-- outline-end -->

> 本节内容待加工。
