---
title: "Native 内存泄漏线上监控实战：malloc 钩子、Scudo 追踪与 mallinfo 治理"
chapter: "20.26"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [native, memory-leak, malloc, Scudo, mallinfo, monitoring, online]
related_chapters: ["20.3", "20.15", "20.23", "23.3", "23.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "素材驱动+章节深挖"
---

# 20.26 Native 内存泄漏线上监控实战：malloc 钩子、Scudo 追踪与 mallinfo 治理

<!-- outline-start -->
## 要点

### 🔹 Native 内存泄漏的挑战
- Java Heap 有成熟的泄漏检测（LeakCanary / Profile），Native Heap 缺乏等价方案
- Native 泄漏的隐蔽性：RSS 持续增长但无明确 Java 引用链
- Android 17 Scudo 分配器对传统 hook 方案的影响

### 🔹 malloc/free hook 技术路径
- PLT hook（xhook/bhook）：函数级别拦截 malloc/free/calloc/realloc
- Android 8+ linker namespace 对 PLT hook 的限制与绕过
- hook 采样策略：全量 vs 1/1000 采样（性能开销权衡）
- [结构参考: Clippings/Android 应用稳定性剖析与优化 - Native 内存泄漏监控：寻找 Native 中不可达内存]

### 🔹 AddressSanitizer (ASan) 线上灰度
- ASan 编译期插桩的内存开销（2-3x 内存膨胀）
- HWASan（ARM Memory Tagging）在 Android 14+ 上的可用性
- Android 17 GWP-ASan 的灰度采样机制（与 20.23 交叉引用）
- ASan 与 Scudo 的兼容性矩阵

### 🔹 mallinfo / mallinfo2 / malloc_info 系统调用
- mallinfo() 获取 Native heap 统计（已弃用但广泛使用）
- Android 12+ mallinfo2() 替代方案（支持 64 位 size）
- malloc_info() XML 输出解析与 heap region 分析
- 定期采集 RSS 与 Native heap 差值的趋势监控

### 🔹 /proc/self/smaps 与 PSS 追踪
- /proc/self/smaps_rollup 快速获取内存总览
- Native heap 增长趋势与区间对比（启动后 1min vs 10min vs 1hour）
- Smaps 中 Heap 段与 mmap 段的区分

### 🔹 heapprofd 线上部署
- heapprofd 的采样配置与性能开销控制
- Android 17 heapprofd 与 Perfetto 的集成
- 线上灰度策略：按设备/渠道/用户分批开启
- [交叉引用: 26.24 heapprofd 生产级部署与权限模型]

### 🔹 线上 Native 内存监控架构设计
- Native 内存基准线（PSS-Native）建立与版本间回归
- 泄漏检测算法：稳态比较法（后台 N 分钟后对比 PSS 趋势）
- 告警策略：单设备 vs 群体（千万级 DAU 的统计显著性）
- 与 Java 内存监控的联动：Java 堆 + Native 堆综合视图

### 🔹 典型案例
- 图片库 Native Bitmap 泄漏（Skia decodable 未释放）
- 第三方 SDK Native 内存持续增长
- 音视频播放器 Native buffer 泄漏

## 扩展

### 🔸 Android 17 Scudo 分配器的 debugging 模式
- Scudo 的 GWP-ASan 集成采样
- options=scudo_options 环境变量配置

### 🔸 Kohanakai / mmap-based 内存追踪
- Android 14+ 新增的 mmap 追踪机制
- 与传统 malloc hook 的互补关系

<!-- outline-end -->

> 本节内容待加工。
