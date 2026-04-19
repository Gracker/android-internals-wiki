# 第 4 章：内存管理

> 本章节正在建设中。

## 本章内容

- Android 内存模型全景
- Linux 内核内存管理
- ART 虚拟机内存管理
- Low Memory Killer
- App 内存优化
- 内存相关的版本演进

## 延伸阅读

### Android GPU/Graphics 内存归属矩阵与工具链统一语义
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/Android GPU:Graphics 内存归属矩阵与工具链统一语义.md
- 类型：DeepResearch 调研结果
- 摘要：以 AOSP、libmemtrack、DMA-BUF 和 gpu_mem_total 为主线，解释 smaps、memtrack HAL、DMA-BUF sysfs 与 ftrace 四套 GPU/Graphics 内存口径如何交叉与去重，可直接指导 dumpsys meminfo、Lost RAM 和图形内存统计不一致问题排查。
- 注入时间：2026-04-20
- 价值：把最容易混淆的图形内存统计口径统一了，对内存排障非常实用。
