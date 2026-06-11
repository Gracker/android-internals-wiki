---
title: "SurfaceFlinger Transaction Queue 无锁架构与消息分流"
chapter: "2.27"
status: draft
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
tags: ['SurfaceFlinger', 'LocklessQueue', 'Transaction', 'MPSC', '渲染管线']
related_chapters: ['2.6', '2.22', '2.23']
created_by: "task2a-knowledge-gap"
created_date: "2026-06-11"
gap_source: "DeepResearch 调研结果（score 17）+ AOSP 源码结构"
---

# 2.27 SurfaceFlinger Transaction Queue 无锁架构与消息分流

<!-- outline-start -->
## 要点

### 🔹 锚点 1：LocklessQueue<T> 无锁 MPSC 队列实现
LocklessQueue 使用 compare_exchange_weak CAS 操作维护链表头，push 路径不依赖 mutex，多 binder 线程并发入队不阻塞。pop 通过 mPush.exchange(nullptr) 原子夺取整条链表并就地反转后串行消费。

### 🔹 锚点 2：TransactionHandler 事务批处理流水线
flushPendingTransactionQueues + 多 TransactionFilter 回调实现事务批处理。过滤维度包括时间、buffer barrier、unsignaled fence，未就绪事务留在 mPendingTransactionQueues 等待下次 flush。

### 🔹 锚点 3：setTransactionState 到 applyTransactionState 的落地路径
SurfaceFlinger::setTransactionState 现在只在事务被 applyToken 驱动时才进入 applyTransactionState 落地。期间不持 mStateLock 全局临界区，减少主线程与 binder 线程的锁争用。

### 🔹 锚点 4：FrontEnd 重构后的事务状态拆分
FrontEnd 将客户端提交的事务与合成时读取的状态完全解耦。事务不再直接操作 Layer，而是先入 LocklessQueue 再由主线程批量 drain 过滤后落地。mCurrentState/mDrawingState 双缓冲在新的架构下的角色变化。

### 🔹 锚点 5：BLASTBufferQueue 与 SurfaceFlinger 侧的缓冲区拉取
BLASTBufferQueue 作为 SurfaceFlinger 拉取 buffer 的接口：acquireNextBufferLocked、releaseBufferCallback 承担缓冲区生命周期。与 TransactionQueue 的协作关系。

### 🔹 锚点 6：LocklessQueue vs mutex+condvar 的性能对比
无锁队列省掉 futex 系统调用，避免主线程被 binder 线程争用阻塞。在高并发事务场景（多窗口、桌面模式）下的延迟改善量化分析。

### 🔹 锚点 7：从 Android 15 到 17 的 Transaction 架构演进
Android 15 的 mutex 事务队列 → 16 的 LocklessQueue 引入 → 17 的 TransactionFilter 深化。各版本中事务处理路径的变化与性能影响。

## 扩展

### 🔸 扩展点 1
LocklessQueue 在多窗口/桌面模式高并发事务下的 Perfetto 观察方法

### 🔸 扩展点 2
TransactionFilter 自定义过滤策略的扩展接口与 OEM 定制场景

### 🔸 扩展点 3
SF Transaction Queue 与 Choreographer VSync 对齐的时序关系

<!-- outline-end -->

> 本节内容待加工。
