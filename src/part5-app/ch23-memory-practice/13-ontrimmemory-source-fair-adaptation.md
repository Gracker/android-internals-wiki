---
title: "Android 17 onTrimMemory 链路源码解析与公平内存适配实战"
chapter: "23.13"
status: draft
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: [memory, onTrimMemory, ComponentCallbacks2, CachedAppOptimizer, Choreographer, cgroup-freeze, memory-adaptation]
related_chapters: ["4.4", "4.5", "4.11", "4.15", "10.4", "20.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "素材驱动"
score: 19
score_breakdown: "素材丰富度5 + 相关性5 + 读者需求4 + 时效性5"
source_material:
  - "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-25-fair-memory-trim-android17-source.md"
  - "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-04-20-android-trim-memory-callback-mechanism.md"
---

# 23.13 Android 17 onTrimMemory 链路源码解析与公平内存适配实战

<!-- outline-start -->
## 要点

### 🔹 TRIM_MEMORY 等级体系演进与 API 34+ 收敛
- ComponentCallbacks2 七档等级定义（TRIM_MEMORY_COMPLETE 到 TRIM_MEMORY_RUNNING_MODERATE）
- API 34（Android 14）起五档标记 @deprecated 的源码事实
- Android 17 仅剩 TRIM_MEMORY_UI_HIDDEN(20) 与 TRIM_MEMORY_BACKGROUND(40) 两档可靠
- 与生命周期回调的关系：onStop → UI_HIDDEN，cgroup-freeze → BACKGROUND

### 🔹 onTrimMemory 调度时机：Choreographer CALLBACK_COMMIT 优化
- ActivityThread.scheduleTrimMemory 通过 Choreographer.CALLBACK_COMMIT 延迟执行
- 避免在帧绘制过程中触发 GC 导致 jank 的设计意图
- PooledLambda 对象池复用减少 GC 压力
- 与 DeliQueue / MessageQueue 调度的关系（详见 §1.26）

### 🔹 handleTrimMemory 分发链路
- ActivityThread.handleTrimMemory 遍历 ComponentCallbacks2 列表
- Application / Activity / Service / ContextWrapper 的回调顺序
- skipBgMemTrimOnFgApp 优化：避免前台 App 短暂离开又返回时收到 background trim

### 🔹 CachedAppOptimizer 冻结前 TRIM_MEMORY_BACKGROUND 下发
- cgroup-freeze 前同步下发 TRIM_MEMORY_BACKGROUND(40) 的源码锚点
- 这是 App 被冻结前的最后一次内存释放机会
- 冻结后进程 IO/CPU 被冻结，内存占用维持高位

### 🔹 完整调用链：lmkd → AMS → ActivityThread → App
- lmkd 通过 PSI/lowmem 检测内存压力
- ActivityManager.updateOomAdj → CachedAppOptimizer
- IApplicationThread.scheduleTrimMemory → ActivityThread
- Application.onTrimMemory(level) → 开发者回调

### 🔹 App 侧公平内存适配策略
- TRIM_MEMORY_UI_HIDDEN(20)：释放 UI 相关资源（图片缓存、Surface）
- TRIM_MEMORY_BACKGROUND(40)：释放非必要 Java 堆 / Bitmap / LruCache
- onTrimMemory 回调内清理工作的 10ms 预算原则
- Glide / Coil / OkHttp 等主流库的内存清理协同
- 多进程 App 的 onTrimMemory 分发差异

### 🔹 调试与验证
- adb shell am set-process-memory-trim-level 手动模拟 trim
- dumpsys meminfo 查看 lastTrimLevel
- ApplicationExitInfo 中 trim level 相关信息
- Perfetto trace 中 trimMemory 的追踪方法

## 扩展

### 🔸 OEM 扩展：小米公平运行内存 / 华为 / OPPO
- 小米 HyperOS 公平运行内存适配基于 AOSP 钩子的 OEM 扩展
- 各厂商 ROM 的 trim 链路差异（不开源，需 perfetto trace 实证）
- App 正确实现 onTrimMemory 即可在所有厂商获得一致的内存预警

### 🔸 Android 17 MemoryLimiter 与 trim 的关系
- MemoryLimiter:AnonSwap exit 与 lmkd kill 的两条独立链路
- memory.high cgroup 限制对 trim 回调的影响
- 与 §4.5 MemoryLimiter 的交叉引用

### 🔸 历史演进：API 26-33 的七档 trim 体系
- 旧版 TRIM_MEMORY_COMPLETE/MODERATE/RUNNING_* 的实际触发频率
- 从七档到两档的收敛对 App 内存策略的影响
- 版本兼容方案：如何在 API 26-33 与 API 34+ 间统一处理

<!-- outline-end -->

> 本节内容待加工。

[结构参考: Clippings/Android 性能优化 - 原理：重新认识内存.md]
[结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]
