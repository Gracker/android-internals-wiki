---
title: "ch06-storage"
chapter: "06"
status: "draft"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [storage, io, filesystem]
---

## 参考资料

### Android 安装优化机制与厂商定制边界
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-14-android-install-optimization-aosp-mechanism.md
- 类型：DeepResearch 调研结果
- 摘要：深度解析 AOSP staged install 全链路源码：从 PackageInstallerSession→PMS→installd→dex2oat 的关键路径，以及厂商（vivo Turbo/小米 HyperOS）在 BackgroundDexOptService 编译策略、idle 窗口、compiler filter 上的定制边界。核心发现厂商优化不涉及内核修改，全在用户态调度层。
- 注入时间：2026-05-14
- 价值：含完整 AOSP 安装管线源码路径和厂商 diff 对比，对理解存储与安装性能优化有直接参考价值


### Android 嵌入式照片选择器，让体验更加丝滑
- 来源：https://juejin.cn/post/7599963665039081522
- 类型：技术文章
- 摘要：Android 14+ 推出 Embedded Photo Picker，替代弹窗式的标准 Photo Picker。核心优势：零权限（不需要存储权限）、云端照片（Google Photos）也能选、嵌入 App 内部不跳转、保持前台活跃。支持 Jetpack Compose 和传统 Views 两种接入方式，可自定义主题色。需要 Android 14 + SDK Extensions 15，不满足条件自动回退到标准 Photo Picker。核心理念：App 只能访问用户明确选择的照片，其他照片完全看不到。
- 入库时间：2026-05-10
- 评分：14/20
