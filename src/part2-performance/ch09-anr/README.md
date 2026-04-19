# 第 9 章：ANR

> 本章节正在建设中。

## 本章内容

- ANR 设计思想
- ANR 类型与触发条件
- ANR 分析方法
- 特殊场景的 ANR
- 案例集
- Notification 性能与 ANR
- ANR 非技术故障诊断

## 延伸阅读

### AnrController 与 BroadcastQueueImpl 在现代 ANR 判责中的作用
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/AnrController 与 BroadcastQueueImpl 在现代 ANR 判责中的作用.md
- 类型：DeepResearch 调研结果
- 摘要：基于 AOSP main 梳理 Input ANR 与 Broadcast ANR 两条判责链，澄清 AnrController 已成为 WMS 侧归因与 pre-dump 取证枢纽，BroadcastQueueModernImpl 也以软硬超时替代旧式“一超时即 ANR”模型，适合用于现代 ANR 自动化判责与 trace 解读。
- 注入时间：2026-04-20
- 价值：把现代 ANR 判责入口、归因边界和广播超时语义讲透了，能直接减少误判。
