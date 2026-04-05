---
title: "MessageQueue 机制与 DeliQueue 无锁优化"
chapter: "1.13"
status: draft
applicable_versions: "Android 1.0 (API 1) - Android 17 (API 37)"
tags: [MessageQueue, Looper, DeliQueue, 无锁数据结构, 主线程性能, 掉帧]
related_chapters: ["1.5", "2.4", "2.5", "7.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-05"
gap_source: "研究素材"
---

# 1.13 MessageQueue 机制与 DeliQueue 无锁优化

<!-- outline-start -->
## 要点

### 🔹 锚点 1：传统 MessageQueue 的锁竞争问题
- MessageQueue 在主线程中的角色：UI 线程的任务调度核心
- 传统实现使用单一 monitor lock 管理 mMessages 链表
- 后台线程通过 Handler.sendMessage() 插入消息时必须获取主线程锁
- 锁竞争导致的优先级反转：后台低优先级线程阻塞高优先级 UI 线程
- 在 Perfetto 中表现为主线程的「locked」状态和掉帧

### 🔹 锚点 2：Looper 消息循环的工作机制
- Looper.prepare() 创建 MessageQueue 的线程绑定
- Looper.loop() 的无限循环：next() → dispatchMessage() → 回调
- Message 的优先级与时间排序（when 字段）
- 同步屏障（SyncBarrier）：优先处理异步消息的机制
- IdleHandler：线程空闲时的回调处理

### 🔹 锚点 3：Android 17 DeliQueue 架构设计
- 混合数据结构：无锁 Treiber 栈 + 单线程最小堆
- 生产者路径（插入）：无锁 Treiber 栈，多线程并发 push 无需加锁
- 消费者路径（处理）：Looper 线程独占的最小堆，按 when 排序
- 栈到堆的迁移（drain）：Looper 在 next() 中将栈内容转移到堆
- 为什么 Treiber 栈而非队列：CAS 简单、无 ABA 问题（单消费者）

### 🔹 锚点 4：DeliQueue 的性能实测数据
- 主线程锁竞争时间减少 15%
- App 掉帧减少 4%
- SystemUI / Launcher 掉帧减少 7.7%-9.1%
- App 启动到首帧绘制 P95 改善 9.1%
- 合成基准测试中并发插入比旧实现快 5000 倍

### 🔹 锚点 5：兼容性与迁移影响
- 反射访问 MessageQueue.mMessages 的代码会失效（新实现中始终为 null）
- Handler.postMessage() 的语义不变，API 完全兼容
- targetSdkVersion >= 37 (Android 17) 时启用 DeliQueue
- 旧版本设备升级到 Android 17 不受影响（仅新设备强制）

### 🔹 锚点 6：在 Perfetto 中观察锁竞争变化
- 对比 Android 16 vs Android 17 的主线程 trace
- 锁竞争 slice 的减少与掉帧关联分析
- 如何定位是否仍存在 Handler 导致的主线程阻塞

### 🔹 锚点 7：与 Choreographer 的协作关系
- Choreographer.doFrame() 本质上是 MessageQueue 的一个 Callback
- VSYNC-app 信号通过 FrameDisplayEventReceiver 以异步 Message 形式投递
- DeliQueue 如何影响 VSYNC 回调的及时性
- 主线程消息堆积对渲染帧调度的影响

## 扩展

### 🔸 扩展点 1：无锁数据结构在 Android 系统服务中的应用趋势
- 其他可能从无锁优化受益的锁竞争热点

### 🔸 扩展点 2：Handler 导致的内存泄漏与性能问题
- 内部类持有 Activity 引用导致的泄漏
- Handler.postDelayed 的精确度与系统时钟关系

### 🔸 扩展点 3：其他平台的 MessageQueue 优化对比
- iOS RunLoop 的消息处理机制
- Chrome Mojo MessagePipe 的无锁设计

<!-- outline-end -->

> 本节内容待加工。
