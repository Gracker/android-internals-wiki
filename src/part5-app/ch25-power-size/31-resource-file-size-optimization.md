---
title: "资源文件体积优化实战"
chapter: "25.31"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [包体积, 资源优化, 图片压缩, ARSC, AAPT2]
related_chapters: ["12.1", "25.7", "25.8", "25.29", "25.30"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-17"
gap_source: "Clippings性能优化参考书（资源文件体积优化实战章）"
gap_score: 15
---

# 25.31 资源文件体积优化实战

<!-- outline-start -->
## 要点

### 🔹 图片资源体积优化
- WebP 格式转换与质量 / 体积权衡
- VectorDrawable 替代 PNG 的适用场景与性能边界
- AVIF 格式在 Android 14+ 的支持与兼容方案
- 图片资源重复检测与自动去重
- [结构参考: Clippings/Android 性能优化 - 资源文件的体积优化实战.md]

### 🔹 资源限定符优化
- 多 dpi 资源（mdpi/hdpi/xhdpi/xxhdpi/xxxhdpi）裁剪策略
- 语言资源、屏幕方向资源的按需保留
- 使用 ABI splits / density splits 减少单包资源量

### 🔹 ARSC 文件优化
- resources.arsc 文件结构与体积构成
- Resource Shrinking 与 R8 的协作机制
- 复杂资源 ID 对 ARSC 体积的影响
- AAPT2 的 resource merging 优化

### 🔹 assets 目录优化
- 原始素材压缩策略（音频 / 字体 / 数据文件）
- 字体子集化（subset）与可变字体
- assets 与 res/ 的选型差异对体积的影响

### 🔹 资源混淆与压缩
- AndResGuard / R8 的资源名混淆
- 7zip / zstd 压缩对 APK 体积的影响
- Android App Bundle 的资源按需分发机制（详见 25.8 节）

### 🔹 R8 Resource Shrinking 深度配置
- shrinkResources true 的底层机制与风险
- keep.xml 精细化资源保留策略
- 反射引用资源的 safe listing

## 扩展

### 🔸 Play Asset Delivery 与动态资源下发
- 大型游戏 / 应用的资源按需下载策略
- Fast-follow 与 on-demand 分发模式

### 🔸 Android 17 AAPT2 资源编译管线变更
- 增量资源编译对构建性能的影响
- 非 SDK 资源引用的兼容性边界

<!-- outline-end -->

> 本节内容待加工。
