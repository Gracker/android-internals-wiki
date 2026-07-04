# 第 17 章：厂商优化实践

Android 性能问题有一个很现实的特点：**AOSP 讲得清楚，不等于到了真实设备上还是那样。**

同一个应用，在 Pixel 上、在某家厂商 ROM 上、在不同 SoC 平台上，表现可能完全不同。  
这并不是“代码突然变了”，而是系统策略、后台限制、调度参数、图形栈、整机热控这些东西一起把结果改写了。

所以这一章不只是“看看厂商做了什么”，更重要的是提醒读者：当问题开始明显表现出设备分布时，思考方式必须从“这段代码慢不慢”切换到“这套系统策略在这台设备上怎么工作”。

## 本章内容

- OEM 性能优化的通用思路
- SoC 平台差异
- 行业案例

## 阅读建议

- 如果你在真实项目里已经遇到明显的机型差异，这一章值得和方法论章节一起看。
- 如果你目前还主要在 App 侧分析单机 trace，可以先记住这章的存在，等问题开始显出设备分布时再回来读。

## 参考资料

### 你可能还不知道 Compose Pager 有多强大从传统的 ViewPager 过渡到 Compose Pager，代
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/技术文章/source/juejin-android/2026-07-04-76184335-你可能还不知道ComposePager有.md
- 类型：技术文章
- 摘要：> 发布时间: 2026-03-19T00:29:43.000Z > 原文链接:  2026-03-19 2,150 阅读9分钟 我同事刚开始用 Compose 没多久，就找上我了，问我 ViewPager 有没有什么替代品。我说 Compose 的 Pager 可比那个强多了，你等我写一...
- 入库时间：2026-07-04
- 评分：12/20

### 为什么 Android 不用接口做 Activity 通信？一、一个 iOS 开发者，把我问住了 上周，一个刚从 iO
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/技术文章/source/juejin-android/2026-07-04-76388970-为什么Android不用接口做Activ.md
- 类型：技术文章
- 摘要：> 发布时间: 2026-05-13T00:03:47.000Z > 原文链接:  2026-05-13 3,478 阅读4分钟 上周，一个刚从 iOS 转过来的同事问我： > “Android 为啥不喜欢用接口回调传结果？ iOS 那边 delegate、closure 不就挺好吗？”...
- 入库时间：2026-07-04
- 评分：14/20

### 现代 Android 官方为什么更推荐 Repository 暴露 suspend fun，而不是在内部 launch
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/技术文章/source/juejin-android/2026-07-04-76500740-现代Android官方为什么更推荐Rep.md
- 类型：技术文章
- 摘要：> 发布时间: 2026-06-11T22:41:13.000Z > 原文链接:  2026-06-12 1,642 阅读12分钟 写这篇文章，其实是因为最近看到有些公众号在介绍 Kotlin 协程时，都推荐在 Repository 中这样写： fun load() { repositor...
- 入库时间：2026-07-04
- 评分：14/20

