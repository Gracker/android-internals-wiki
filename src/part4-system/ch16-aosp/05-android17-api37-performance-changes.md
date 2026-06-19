---
title: "Android 17 (API 37) 性能行为变更与适配方法"
chapter: "16.5"
section: "16.5"
status: "finalized"
drafted_date: "2026-04-08"
applicable_versions: "Android 17 (API 37)"
last_verified: "2026-05-29"
last_verified_against: "Android 17 behavior changes all/target 37 pages updated 2026-05-19/2026-05-28, Network Security Configuration domainEncryption schema, ProfilingTrigger API reference"
confidence: medium
reviewed_at: "2026-05-11T19:05:00+08:00"
sources:
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-all"
  - type: official
    path: "https://developer.android.com/about/versions/17/features"
  - type: official
    path: "https://developer.android.com/about/versions/17/changes/messagequeue"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingTrigger"
  - type: official
    path: "https://developer.android.com/reference/android/app/job/JobScheduler"
  - type: official
    path: "https://developer.android.com/privacy-and-security/security-config"
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
  - type: blog
    path: "https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html"
  - type: blog
    path: "https://android-developers.googleblog.com/"
  - type: blog
    path: "https://juejin.cn/post/7612812060795093002"
  - type: blog
    path: "https://juejin.cn/post/7610233341305389099"
tags: [android17, api37, behavior-changes, performance, deliqueue, generational-gc, profiling-manager, cloud-compilation]
related_chapters: ["1.6", "1.13", "4.8", "5.7", "8.2", "14.7", "16.2", "16.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-08"
gap_source: "官方文档+研究素材+AOSP结构+读者需求"
gap_score: 20
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task6_result: "pass-light-edit"
task9_state: "reviewed"
task9_result: "pass-tech-review"
task9_audit_date: "2026-06-10"
task9_audit_type: "idle-audit"
task2b_state: "fixed"
task2b_result: fixed
last_task2b_at: "2026-05-29T06:50:00+08:00"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-05-29"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-29"
review_notes: "2026-05-16 task6 review: pass-light-edit。修复 1 处结构性元叙述、移除 AIW 编辑标记，并把 DeliQueue 内存开销量化改成需实测口径；无新增 L3/L4 回炉。Task2B 已修复，转 Task9 复核。"
last_task9_at: "2026-05-29T07:21:00+08:00"
task9_review_notes: "2026-05-29 Task9 deep-review: auto-fixed。修正 KILL_EXCESSIVE_CPU_USAGE 产物口径、domainEncryption mode 枚举与 usesCleartextTraffic deprecation plan；补 Android 17 memory limits 排障入口。"
review_type: "task6-writing-quality-review"
task9_result: auto-fixed
last_task9_review_log: "logs/deep-review/2026-05-29-07-deep-review.md"
task6_result: "pass-light-edit"
last_task6_at: "2026-05-29T08:16:26+08:00"
last_task6_review_log: "logs/review/2026-05-29-08-review.md"
task2b_fixed_by: openclaw-task2b-main
task6_reviewed_date: "2026-05-29"
task6_reviewed_by: "openclaw-task6"
task6_reviewed_at: "2026-05-29T07:07:00+08:00"
task6_review_notes: "2026-05-29 08: Task6 revisiting review: pass-light-edit；L1 禁用句式修复 1 处；无新增 L3/L4 回炉。Task9 为 auto-fixed，未满足自动 finalized 条件。"
task6_l1_l2_fixes: 1
task6_l3_l4_issues: 0
last_task9_autofix_at: "2026-05-29"
task6_new_rework: false
last_task2b_verifier_at: "2026-05-29T23:25:00+08:00"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-05-30
---

# 16.5 Android 17 (API 37) 性能行为变更与适配方法

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 17 行为变更的性能影响与公开量化数据
- 🔹 DeliQueue 对 MessageQueue 锁竞争的改造与适配边界
- 🔹 ART 分代 CMC、ProfilingManager 与 JobScheduler 诊断能力
- 🔹 static final、Network Security Configuration、16KB 页面等 targetSdk 37 适配项
- 🔹 迁移检查清单与跨章节参考

### 扩展（可选深入）

- 🔸 DeliQueue drain 触发机制与 ConcurrentMessageQueue 数据结构
- 🔸 Generational CMC gating 条件
- 🔸 Choreographer Buffer Stuffing Recovery

<!-- outline-end -->

## 为什么要了解 Android 17 的性能行为变更

升 `targetSdkVersion` 到 37，首先要核查几类会改运行时行为的点：`MessageQueue`、`static final` 反射限制、网络安全配置迁移，以及大屏配置策略。分代 GC、ProfilingManager trigger、JobScheduler 诊断 API 更偏"排障和观测方式变了"——它们一般不会直接把 App 改崩，但会改变你读 trace 和定位问题的方式。

有公开定量数据的，目前主要是 `MessageQueue` 的 lock-free 改造。公开来源有三层：Android Developers Blog 的 synthetic benchmark、internal beta tester 的 Perfetto traces，以及同一批测试设备上的用户体验指标。官方没公开具体机型、负载脚本和 trace 附件，所以这些数字只能当方向性参考，不能当成你的业务也能复现的保底收益。

这些变更在 Perfetto 中都有明确特征：DeliQueue 削减主线程锁竞争；分代 GC 改变 Memory Track 的 GC 切片模式；ProfilingManager 新触发器改变系统事件采样入口。把这些特征记住，才能在 Android 17 trace 里把新现象和旧经验分开。

性能相关的核心变更，按影响程度和适配优先级排下来如下。

### Android 16 vs 17：公开量化数据对比

| 项目 | Android 16 / API 36 | Android 17 / API 37 | 公开量化数据 |
|:---|:---|:---|:---|
| MessageQueue | 单锁 + 单链表 | DeliQueue：Treiber Stack + min-heap | 有，见下文的 5,000x synthetic benchmark、15% lock contention 下降、4% / 7.7% / 9.1% 体验指标 |
| ProfilingManager triggers | 需要手动注册，触发器集合较小；API 36 新增 `TRIGGER_TYPE_APP_FULLY_DRAWN` | API 37 新增 `TRIGGER_TYPE_ANOMALY`、`TRIGGER_TYPE_APP_COMPAT`、`TRIGGER_TYPE_COLD_START`、`TRIGGER_TYPE_OOM`、`TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` 等触发器 | 官方未给统一 benchmark |
| JobScheduler pending reasons | API 36 已有 `getPendingJobReasons(int)`、`getPendingJobReasonsHistory(int)` 与 `PendingJobReasonsInfo` | API 37 reference 新增 `getPendingJobReasonStats(int)`，聚合 pending reason 时长；AOSP android-16.0.0_r1 未包含，需以 API 37 reference / preview 分支核验 | 官方未给统一 benchmark |
| 大屏 / 安全配置 / 16KB 页面 | 适配要求已在推进 | targetSdk 37 后约束更强、排障入口更明确 | 官方未给统一 benchmark |

---

## DeliQueue：MessageQueue 二十年来的首次架构换代

### 旧实现的问题

从 Android 1.0 开始，`MessageQueue` 的核心数据结构就是一个 `synchronized` 保护的 singly linked list。所有线程通过 `Handler.sendMessage()` 或 `Handler.post()` 投递消息时，都需要获取同一把锁。在 Looper 线程（通常是主线程）从队列头部取消息执行时，其他线程如果想投递消息，就必须等主线程释放锁。

日常场景下锁争用基本不会发生——消息投递很快，持锁时间极短。但高并发时，队列维护阶段的共享 monitor 会放大优先级反转：低优先级投递线程在 `enqueueMessage()` 里持着 monitor，高优先级 UI 线程进 `MessageQueue.next()` 取消息时就被卡在 monitor contention 上。Message 被取出以后，Looper 执行业务回调或布局计算时不再持有 `MessageQueue` monitor，所以不能把掉帧原因写成“主线程执行布局期间锁住所有投递线程”。

在 Perfetto Trace 中，旧实现的锁争用表现为：
- Main Thread Track 或目标 Looper 线程上出现名为 "monitor contention with MessageQueue" 的切片
- 等待线程显示为 Sleeping 状态，持有锁的线程正在执行 `MessageQueue.enqueueMessage()` 或相邻的 Handler 投递路径
- 锁等待时间通常在 1-5ms 范围，但多次累积就会导致帧时间超过 16.6ms（60fps）
- 如果等待发生在 `Choreographer.doFrame` 前后，就会直接挤占本帧预算

如果手头没有旧版 trace 截图，线下自查时可以直接在 Perfetto 搜索 `monitor contention`，再看 UI 线程是否在 `MessageQueue.next()` 附近等待，以及持锁线程是否落在 `Handler.enqueueMessage()` / `MessageQueue.enqueueMessage()` 路径。旧实现下，消耗帧预算的通常就是这类等待区间。

### 新实现：DeliQueue 的混合数据结构

Android 17 为 targetSdk 37 的应用引入了新的 lock-free `MessageQueue`。Android Developers Blog 将这套实现称为 DeliQueue。核心设计思路是把"多线程写入"和"单线程读取"拆开：

- **Android Developers Blog 的概念模型**：使用 Treiber Stack（一种无锁栈），通过 CAS（Compare-And-Swap）操作实现多线程并发入队，不需要任何锁
- **读取端**：使用 min-heap（最小堆），由 Looper 线程独占访问，按消息的 `when`（执行时间）排序，天然有序

工作流程是这样的：当任何线程通过 `Handler` 投递一条消息时，消息被概念性地 push 到 Treiber Stack 中，这是一个 O(1) 的 CAS 操作，不需要获取锁。当 Looper 线程进入 `loop()` 的下一次迭代时，它会将并发入队的消息批量转入 min-heap（drain 操作），然后从 min-heap 中按时间顺序取出下一条消息执行。

```
[图:DeliQueue 数据流示意图]
Thread A ──CAS push──▶ Treiber Stack ──drain──▶ Min-Heap ──poll──▶ Looper.loop()
Thread B ──CAS push──▶      ↑                         ↑
Thread C ──CAS push──▶      │                         │
                         (无锁)                   (独占访问)
```

### 性能收益

Android Developers Blog 把公开数字分成三类，它们的测试前提并不相同：

| 证据类型 | 公开口径 | 能回答什么 |
|:---|:---|:---|
| Synthetic benchmark | busy queue 上的 multi-threaded insertions 最多可比 legacy `MessageQueue` 快 **5,000x** | 说明 DeliQueue 在高竞争入队场景的上限收益 |
| internal beta testers 的 Perfetto traces | App 主线程花在 lock contention 的时间减少 **15%** | 说明锁竞争本身下降 |
| 同一批测试设备上的用户体验指标 | App missed frames **-4%**；System UI / Launcher missed frames **-7.7%**；启动到首帧 P95 **-9.1%** | 说明锁竞争下降已经传导到交互体验 |

公开资料没有给出机型、脚本和 trace 附件，所以这组数字只能用来判断"Android 17 的新队列是否需要关注"。如果要回答"你的业务能拿到多少收益"，还是要在同一机型、同一 workload、同一 trace 配置下做 A/B。

### 适配要点

DeliQueue 对大多数业务代码是透明的。`Handler`、`Looper`、`Message` 的公共 API 没有变化，但**依赖 `MessageQueue` 私有实现细节的代码需要重点排查**。

官方的 MessageQueue behavior change guidance 已明确写明：为了保留二进制兼容性，`MessageQueue.mMessages` 字段仍然存在，但在新的 lock-free 实现里**始终为 `null`**。AOSP 当前源码还能看到多套实现并存：`CombinedMessageQueue/MessageQueue.java` 继续保留 `mMessages`、`mLast` 和 `mUseConcurrent`，负责兼容层与实现选择；`ConcurrentMessageQueue/MessageQueue.java` 负责 DeliQueue 的并发结构。根据 Android Developers Blog 的官方描述，DeliQueue 的核心数据结构是：

- **Treiber Stack**（无锁栈）：写入端使用 `AtomicReference` + CAS 实现并发入队，任何线程都可以无竞争地 push 消息
- **min-heap**（最小堆）：读取端由 Looper 线程独占访问，按消息的 `when` 排序。博客明确指出这是堆结构，不是 `ConcurrentSkipListSet` 排序集合
- **tombstoning**（墓碑标记）：移除操作通过 CAS 原子设置移除标记（逻辑移除），物理移除由 Looper 线程延迟完成

AOSP 实现为同步屏障场景维护了异步消息的专门处理路径，同步屏障语义仍由队列实现维护。排障时不要把这次变化简化成“某个字段改名”。

从性能复杂度看，旧单链表的头部移除是 O(1) 但最坏插入是 O(n)（需要遍历到正确位置），min-heap 的插入和移除都是 O(log n)，两者各有优劣。DeliQueue 的收益集中在并发侧：写入端通过 lock-free Treiber Stack 消除锁竞争，多线程同时入队时不再相互阻塞，插入是 O(1) 的 CAS 操作；Looper 侧的 drain 和读取是独占操作，不受写入端干扰。博客特别指出，min-heap 在尾部延迟（tail latency）上优于单链表——队列过载时，单链表的 O(n) 插入会让尾部延迟急剧恶化，min-heap 的 O(log n) 更稳定。排障时，Perfetto 中的 lock contention 切片是观察收益的直接入口——如果 `monitor contention with MessageQueue` 切片消失或缩短，说明 DeliQueue 在当前场景下起效了。

源码层可以拆成三点：

- `CombinedMessageQueue/MessageQueue.java` 还保留 legacy 视角下可见的字段和选择逻辑。
- `ConcurrentMessageQueue/MessageQueue.java` 负责 DeliQueue 的并发结构。
- 因此这次变化的实质是"保留兼容字段 + 切换底层实现";不要按"`mMessages` 改名"理解。
- 同步屏障语义仍按 `MessageQueue` 公共 API 理解。底层换成并发入队和 Looper 侧排序后，`postSyncBarrier()` 与异步消息选择逻辑仍由队列实现维护；业务侧不要依赖旧链表中 barrier 节点的位置做反射判断。

如果你的项目中有以下情况，需要检查：

1. 反射访问 `MessageQueue.mMessages` 或其他私有字段
2. 通过 JNI 直接操作 `MessageQueue` 的 native 层结构
3. 使用了依赖上述反射行为的第三方库
4. 仍在用老版本测试框架观察主线程 idle 状态

官方兼容指南给出的直接动作是:

- Espresso 升级到 **3.7.0+**,改用 `TestLooperManager` 路径
- Robolectric 升级到 **4.17+**,并把 `@LooperMode(LEGACY)` 迁到 `@LooperMode(PAUSED)`
- 如果怀疑问题就是新的 `MessageQueue` 导致，可先在 Developer Options 的 App Compatibility Changes 里关闭该变更，或执行 `adb am compat disable USE_NEW_MESSAGEQUEUE <package>` 做 A/B 定位

### DeliQueue 算法细节补充

以下细节对理解 DeliQueue 的实现机制有用，章节现有描述已经覆盖核心架构，以下作为**算法层补充**：

**TreiberStack push 伪代码**（来自 Google 官方博客）：
```java
public void push(E item) {
  Node<E> newHead = new Node<E>(item);
  Node<E> oldHead;
  do {
    oldHead = top.get();
    newHead.next = oldHead;
  } while (!top.compareAndSet(oldHead, newHead));
}
```
CAS loop 确保并发 push 的线程只有一个成功，其余重试。这实现了 lock-free 的 O(1) 插入。

**消息排序逻辑**：min-heap 按 `when`（执行时间）为主键、`insertSeq`（插入序列号）为次键排序。因此，相同 `when` 的消息按插入顺序处理。

**Tombstone 机制细节**：当调用 `removeMessages()` 时，线程不立即从数据结构中物理移除消息，而是：
1. CAS 将消息的 `removed` 标志设为 true（逻辑删除）
2. 将消息加入 lock-free freelist
3. Looper 在后续循环中批量处理 freelist，清理链表和 heap 中的物理链接

**Looper 退出机制（Native Refcount）**：使用 tagged refcount，其中 one bit 标识 quitting 状态。其他线程在使用 native allocation 前必须检查该 bit，避免 use-after-free。

**分支消除优化**：Message 比较器原本使用条件分支，在高端 ARM64（如 Tensor G 系列）上导致 pipeline flush。Google 团队使用 SIMD-like 技术重写比较逻辑，避免分支预测失败的开销。

**性能数字来源说明**：DeliQueue 的 5,000x synthetic benchmark、15% lock contention 下降、4%/7.7%/9.1% 用户体验指标均来自 Google 内部 benchmark，**非 AOSP commit 可独立复核验证**。建议在向读者引用时注明来源为 Google 内部 benchmark。

**AOSP 源码路径**：`frameworks/base/core/java/android/os/MessageQueue.java`，在 cs.android.com 的 android-16.0.0_r1 或 master 分支可查看具体实现。

**Perfetto 诊断**：旧实现锁争用表现为 "monitor contention with MessageQueue" 切片；DeliQueue 启用后此切片应显著减少或消失。可使用 `android_monitor_contention` PerfettoSQL 模块查询。


---

## ART 分代垃圾回收

### 从 Concurrent Copying 到 Generational CMC

ART 的垃圾回收器经历过多次演进。「Android 8」（Oreo）将 Concurrent Copying (CC) 作为默认 GC，解决了 Compact GC 的长暂停问题。「Android 10」引入了分代 CC (Generational Concurrent Copying)，将堆空间分为 young generation 和 old generation，优先回收存活时间短的 young 对象。

Android 17 进一步将分代思想整合到 **Concurrent Mark-Compact (CMC)** 收集器中。CMC 的特点是：标记和压缩都是并发执行的，应用线程只需要在标记开始和结束时经历极短的暂停。分代 CMC 在此基础上增加了 young generation 的快速回收路径，**但实际启用需要满足多个条件**：

- `generational_cmc_supported` 系统属性检查通过——在 `Runtime::Init()` 阶段评估设备硬件能力，不满足则直接跳过后续检查
- `gUseUserfaultfd` 系统属性开启（编译期常量，取决于内核是否编译了 userfaultfd 支持）
- `use_generational_cmc` flag 启用
- `persist.device_config.runtime_native_boot.use_generational_gc` 设备配置支持
- AOSP android-16.0.0_r1/main 已存在 `YoungMarkCompact` 和相关 gating 逻辑

因此不能简单把分代 CMC 写成 Android 17 的“统一行为”，而是要根据设备配置和 trace 验证具体启用情况。

### 分代回收的工作原理

分代 GC 的基本假设是"弱分代假说"(Weak Generational Hypothesis)：大多数对象在创建后很快就变成垃圾。在 Android App 的实际运行中，这个假设非常成立——方法中的局部变量、临时构建的 `Message` 对象、`RecyclerView` 中滑出屏幕的 `ViewHolder` 绑定数据，这些对象的存活时间通常只有几毫秒到几秒。

分代 CMC 的工作方式:

1. 新创建的对象分配在 **young generation** 空间
2. 当 young generation 空间达到阈值时，触发一次 **young GC**--只扫描和回收 young generation 中的垃圾对象，忽略 old generation
3. 经历了若干次 young GC 仍然存活的对象，被**提升（promote）**到 old generation
4. 当 old generation 空间不足时，才触发一次 **full GC**--扫描整个堆

关键区别在于：young GC 只扫描一小部分堆空间，速度远快于 full GC。这直接减少了 GC 暂停对主线程的影响。

> **注意**：实际启用分代 CMC 需要满足上述 gating 条件，不是所有 Android 17 设备都会启用此功能。

**如何验证当前设备是否启用了分代 CMC**：

1. **device_config 查询**：`adb shell device_config get runtime_native_boot use_generational_gc`，返回 `true` 表示设备配置已启用。如果返回 `false` 或空值，分代 CMC 不会生效，即使系统属性满足条件
2. **Perfetto GC tracks 验证**：在 Perfetto 中搜索 `art_gc` 相关切片，观察 GC 类型名称。如果看到 `Generational` 相关标记（如 `young_gc`、`YoungMarkCompact`），说明分代路径在运行；如果只有 `ConcurrentCopying` 或 `ConcurrentMarkCompact`，说明走的是非分代路径
3. **强制开启（仅限调试）**：`adb shell device_config set runtime_native_boot use_generational_gc true` 后重启应用。此方法依赖设备内核是否编译了 userfaultfd 支持，部分生产设备可能无法生效

### 对 RecyclerView 滑动的实际影响

RecyclerView 滑动是 GC 敏感场景的典型代表。在滑动过程中，`onBindViewHolder()` 会为每个即将显示的 item 创建临时对象（字符串、Drawable、Bitmap 相关的配置对象等）。这些对象在 item 滑出屏幕后就变成垃圾。

在旧的非分代 GC 中，这些 young 对象会在 full GC 时才被回收。如果 full GC 恰好在 `doFrame()` 期间触发，就会造成帧延迟。在分代 GC 中，这些短命对象被 young GC 快速回收，full GC 的触发频率大幅降低。

公开资料没有给出可直接复用的统一 RecyclerView 基准图，因此更稳妥的做法是在同一列表场景下自己对比 GC 事件频率、暂停分布和掉帧率，而不是套一个脱离设备前提的固定毫秒数。更完整的方法在 **4.8 ART 分代垃圾回收** 里展开。

### 与 4.8 ART 分代 GC 章节的关系

Android 17 的分代 GC 变化会改变 GC 切片模式和暂停分布。Concurrent Mark-Compact 的工作原理、GC 暂停的产生机制和版本演进，详见 **4.8 ART 分代垃圾回收**。

---

## ProfilingManager 新的系统触发器

### 从手动埋点到系统自动触发

ProfilingManager 在 Android 15 (API 35) 引入，提供运行时请求 heap dump、stack sampling、system trace 等分析产物的能力。API 36 补充了部分 trigger 入口。Android 17 (API 37) 新增了 cold start、OOM、kill、anomaly 等系统触发器，可以把采集条件交给系统事件驱动——但 ProfilingManager 仍是一套 trigger-based capture API，不是默认全局开启的自动抓取。

要用这套能力，App 仍要完成两步：先通过 `ProfilingManager.registerForAllProfilingResults()` 注册结果回调，再调用 `ProfilingManager.addProfilingTriggers()` 添加触发器。触发器常量定义在 `android.os.ProfilingTrigger`，产物交付仍由 ProfilingManager 完成。

### 触发器类型与产物

| 触发器 | 触发时机 | 产物类型 | 典型用途 |
|--------|---------|---------|---------|
| `ProfilingTrigger.TRIGGER_TYPE_COLD_START` | App cold start 尽早阶段 | call stack sample + system trace | 定位冷启动瓶颈 |
| `ProfilingTrigger.TRIGGER_TYPE_ANOMALY` | 系统检测到 App 异常行为 | heap dump 或 stack sampling profile，取决于 memory limit breach、Binder spam 等系统判定 | 诊断系统侧异常行为 |
| `ProfilingTrigger.TRIGGER_TYPE_OOM` | App 发生 `OutOfMemoryError` | Java heap dump | 诊断内存泄漏和内存过度使用 |
| `ProfilingTrigger.TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` | App 因异常 CPU 占用被系统杀死 | call stack sample / system trace snapshot（文档口径存在差异，以 `ProfilingResult` 为准） | 定位后台 CPU 异常占用 |


### 注册流程和适配建议

冷启动触发器的文档口径是"app cold start 时尽早触发"，公开产物是 call stack sample 和 system trace。使用时先把它看作采样入口；具体字段名和交付文件形态以 API 37 SDK reference 的 `ProfilingResult` 为准。

`TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` 对应异常 CPU 占用导致的杀进程。Android 17 features 页写 call stack sample，API reference 当前写 running system trace snapshot；接入时不要把产物类型硬编码为单一文件，按 `ProfilingResult` 返回的结果路径和类型分流处理。排障时，可以把 cold start、OOM、异常 CPU kill 这些系统事件交给 trigger-based capture，再在 Perfetto、heap dump、system trace 或采样结果上继续分析。

详见 **14.7 ProfilingManager**。


<!-- AIW-源码调研-2026-06-19 -->

### 源码级机制补充（2026-06-19 源码调研）

基于对 AOSP 源码的深度分析，Android 17 的 ProfilingManager 实际上是一个三层架构的完整性能监控体系，包含以下核心组件：

#### 1. 架构层次

**ProfilingServiceManager**（框架接入层）：
- 位置：`platform/frameworks/base/core/java/android/os/ProfilingServiceManager.java`
- 功能：提供 Profiling 服务的框架级接入点
- 关键 API：`getProfilingServiceRegisterer()` 返回 `ServiceRegisterer("profiling_service")`

**ProfilingService**（核心服务层）：
- 位置：`platform/packages/modules/Profiling/service/java/com/android/os/profiling/ProfilingService.java`
- 功能：实现系统触发器的核心逻辑
- 关键机制：`startSystemTriggeredTrace()` 启动系统触发追踪
- 触发器管理：`addTrigger()` 管理应用级触发器

**AnomalyDetector**（异常检测层）：
- 位置：`platform/packages/modules/Profiling/anomaly-detector/framework/java/android/os/profiling/anomaly/AnomalyDetectorManager.java`
- 功能：系统级异常检测和规则引擎
- 关键 API：`setAnomalyDetectorRules()` 设置异常检测规则

#### 2. 源码级触发机制

**系统触发器实现：**
```java
public void startSystemTriggeredTrace() {
    synchronized (mLock) {
        if (mSystemTriggeredTraceProcess != null && mSystemTriggeredTraceProcess.isAlive()) {
            // 只允许同时运行一个系统触发追踪
            return;
        }
        
        String[] packageNames = getActiveTriggerPackageNames();
        if (packageNames.length == 0) {
            // 没有应用注册触发器，不启动追踪
            return;
        }
        // 启动系统触发追踪进程
    }
}
```

**触发器注册机制：**
```java
public void addTrigger(ProfilingTriggerData trigger, boolean maybePersist) {
    SparseArray<ProfilingTriggerData> perProcessTriggers =
            mAppTriggers.get(trigger.getPackageName(), trigger.getUid());
    
    if (perProcessTriggers == null) {
        perProcessTriggers = new SparseArray<>();
        mAppTriggers.put(trigger.getPackageName(), trigger.getUid(), perProcessTriggers);
    }
    
    // 每个uid+触发器类型只允许一个触发器
    perProcessTriggers.put(trigger.getTriggerType(), trigger);
}
```

#### 3. 异常检测规则引擎

**规则定义：**
```java
public final class Rule {
    private final String name;
    private final List<Integer> anomalyActions;
    private final int conditionType;
    private final String ruleCondition;
    
    public static final int ANOMALY_TYPE_MEMORY = 1;
    public static final int ANOMALY_TYPE_CPU = 2;
    public static final int ANOMALY_TYPE_NETWORK = 3;
}
```

**规则设置：**
```java
@RequiresApi(37)
@SystemApi(client = SystemApi.Client.PRIVILEGED_APPS)
@RequiresPermission(CONFIGURE_ANOMALY_DETECTOR)
public void setAnomalyDetectorRules(@NonNull Set<Rule> rules) {
    Objects.requireNonNull(rules);
    try {
        mService.setRules(convertRulesToRuleParcels(rules));
    } catch (RemoteException ex) {
        ex.rethrowFromSystemServer();
    }
}
```

#### 4. 输出文件格式与性能优化

**Perfetto 格式输出：**
- Java堆转储：`.perfetto-java-heap-dump`
- 堆分析：`.perfetto-heap-profile`
- 栈采样：`.perfetto-stack-sample`
- 系统追踪：`.perfetto-trace`

**性能优化策略：**
- RateLimiter 控制触发频率
- 异步处理栈采样和追踪
- 自动清理临时文件，限制存储空间
- 系统触发器优先级高于应用触发器

#### 5. 模块化架构设计

Android 17 将 Profiling 系统组织为独立的主线模块（com.android.profiling APEX），包含：
- `platform/packages/modules/Profiling/` - 主模块
- `platform/packages/modules/Profiling/anomaly-detector/` - 异常检测子模块
- `platform/packages/modules/Profiling/service/` - 服务实现
- `platform/packages/modules/Profiling/framework/` - 框架API

这种模块化设计使得 Profiling 系统可以独立于 framework 更新，为系统级性能监控提供了灵活的基础设施。

#### 6. 与现有架构的集成

ProfilingService 与现有的 ActivityManagerService 性能监控组件协同工作：
- **AppProfiler.java** - 应用级性能分析，提供 PSS/RSS 内存监控
- **ProcessProfileRecord.java** - 进程性能记录管理，内存信息缓存
- 新的 ProfilingService 提供系统级触发器能力

三个层次形成完整的性能监控体系：应用层、系统服务层、框架API层。

---

---

## JobScheduler pending reasons 诊断 API

### 为什么需要这组 API

`JobScheduler` 是 Android 后台任务调度的核心机制。过去排查"job 为什么没跑"时，很多信息只能从 `dumpsys jobscheduler` 里翻。Android 16 之后，公开 API 已经开始覆盖 current reason 和有限历史；Android 17 进一步把 pending reason 的聚合时长放到参考文档口径中。这里没有独立的 `JobDebugInfo` 类，诊断入口仍在 `JobScheduler` 上。

### API 边界

| 方法 | since | 返回类型 | 用途 | 核验状态 |
|:---|:---|:---|:---|:---|
| `JobScheduler.getPendingJobReasons(int jobId)` | API 36 | `int[]` | 返回当前可能导致该 job pending 的 reason code | AOSP android-16.0.0_r1 已检出 |
| `JobScheduler.getPendingJobReasonsHistory(int jobId)` | API 36 | `List<JobScheduler.PendingJobReasonsInfo>` | 返回有限历史视图，包含 reason 变化记录 | AOSP android-16.0.0_r1 已检出 |
| `JobScheduler.getPendingJobReasonStats(int jobId)` | API 37 | `Map<Integer, Duration>` | 返回 pending 状态期间各 reason 的聚合时长 |  |

这几组接口合在一起，才能回答"某个 job 现在为什么没跑"和"过去一段时间主要卡在哪类约束上"。如果项目通过 WorkManager 间接落到 JobScheduler，调试时最好先拿到对应的 jobId，再对照 current reason、history 和聚合时长判断是哪类约束在持续阻塞。

与 **5.10 JobScheduler/WorkManager 性能** 章节交叉引用。

---

## static final 字段强制不可变

### 变更内容

从 Android 17 (API 37) 开始，平台强化 `static final` 字段的不可变约束。反射路径和 JNI 路径的失败形态不同:

- Java 反射：`Field.set()`、`Field.setInt()` 等 `Field.set*()` 路径会抛出可捕获的 `IllegalAccessException`。
- JNI：`SetStatic<FieldType>Field` 系列可能触发 ART 层不可恢复的 abort / crash，不能按普通 Java 异常处理。

旧版本里，通过 `Field.setAccessible(true)` 绕过访问控制修改 `static final` 字段本来就不受 Java 规范保证。Android 17 强化这类灰色路径限制后，测试代码和 Native 注入代码要分开迁移。

### 对性能的意义

为什么 Android 要强制这个限制?答案是 **ART 的常量折叠优化**。

当 ART 编译器确认一个 `static final` 字段的值在运行时不会改变时，它可以在编译时将所有引用该字段的代码直接替换为常量值（内联）。这消除了字段访问的开销，也使得后续的优化 pass（如死代码消除、循环优化）有更大的发挥空间。

如果允许运行时修改 `static final` 字段，ART 就不能做这个优化——它必须假设字段值可能被修改，每次访问都要从内存中读取。

### 受影响的场景

以下代码模式会受影响:

```java
// 1. Java 反射修改 static final 字段:可捕获 IllegalAccessException
Field field = SomeClass.class.getDeclaredField("CONSTANT");
field.setAccessible(true);
try {
    field.set(null, newValue);
} catch (IllegalAccessException expectedOnApi37) {
    // Android 17+: static final 字段不再作为可写测试入口
}

// 2. JNI SetStatic<FieldType>Field 修改 static final 字段:可能触发 ART abort / crash
// 3. 测试框架通过反射注入 mock 值
// 4. 依赖反射修改 final 字段的依赖注入或序列化框架
```

### 适配建议

1. **测试代码改成显式注入**:把测试值通过构造函数参数、接口实现、非 final 配置对象或 `@VisibleForTesting` 暴露的内部 API 传入，不再 patch 编译期常量。
2. **Native 测试代码移除 `SetStatic*Field` 注入**:把待注入值放到 JNI 方法参数、Native 配置结构或 Java 层测试开关里，避免触发不可恢复崩溃。
3. **升级依赖注入与序列化库**:重点检查老版本 DI / JSON / XML 框架是否仍依赖修改 `final` 字段完成对象构造。

---

## 大屏强制适配的性能影响

### 变更内容

对于 `targetSdkVersion` ≥ 37 的 App，在 smallest width ≥ 600dp 的设备上，以下 Manifest 属性将被忽略:

- `android:screenOrientation`(锁屏方向)
- `android:resizeableActivity="false"`(禁止调整大小)
- 宽高比限制

方向和 resize 限制被忽略后，配置变化仍然走 Android 现有的配置变更机制。默认情况下，屏幕尺寸或方向变化会触发 Activity 销毁重建；只有 App 在 manifest 中通过 `android:configChanges` 声明了对应配置类型，并在代码中正确处理 `onConfigurationChanged()`，才能避免重建导致的中断。使用自适应布局（Jetpack WindowManager、`SlidingPaneLayout` 等）可以进一步减少对 `configChanges` 声明的依赖。Android 没有名为 `Activity.recreateOnConfigChanges` 的标准 API 或 manifest 属性。

### 对渲染性能的影响

这个变更对性能的影响主要体现在两个方面:

**1. 多窗口和折叠屏场景下的 Surface 数量变化**

当 App 被强制要求支持多方向和多窗口时，系统可能在生命周期中创建和销毁更多的 Surface。在折叠屏设备上，铰链展开/折叠时 App 需要在不同尺寸间切换。如果 App 的布局层级较深，每次配置变更时的 measure/layout 开销会累加。

在 Perfetto 中，你可以在 Main Thread Track 中观察到 `Choreographer#doFrame` 下 `performTraversal` 的执行时间。如果配置变更后布局耗时明显增加，说明布局需要优化。

**2. Configuration Change 的过渡路径**

屏幕方向或尺寸变化触发配置变更后，走哪条路径取决于 App 的 manifest 声明：如果 App 在 `<activity>` 中通过 `android:configChanges` 声明了 `screenSize|smallestScreenSize|screenLayout|orientation`，并在代码中正确处理 `onConfigurationChanged()`，可以在不销毁 Activity 的情况下完成布局切换——在 Perfetto 中表现为连续的帧序列。如果 App 没有声明对应的 configChanges，系统仍然会销毁并重建 Activity，在 Trace 中表现为生命周期中断。使用自适应布局（Jetpack WindowManager、`SlidingPaneLayout` 等）可以减少对 configChanges 声明的依赖，但前提是布局本身能响应尺寸变化。

### 适配建议

如果你的 App 尚未适配大屏和折叠屏：

1. 使用 `WindowMetrics` API 替代硬编码的屏幕尺寸
2. 在 `onConfigurationChanged()` 中处理布局变更，而非依赖 Activity 重建
3. 在 Perfetto 中对比新旧模式下的帧时间分布，确认过渡是否平滑

---

## 网络与安全性能变更

### 明文流量迁移到 Network Security Configuration

Android 17 持续提高明文流量约束，`android:usesCleartextTraffic` 的 manifest 级全局开关已进入未来 deprecation plan。当前更稳妥的做法是优先通过 Network Security Configuration 按域名管理明文例外，把必须保留的 HTTP 端点迁到 `network_security_config.xml` 的 `<domain-config>` 白名单中；如果 `minSdkVersion < 24`，仍需要同时保留 manifest 属性和 network security config。ECH `<domainEncryption>` 和 CT 默认行为是这版更确定的网络层变更。

```xml
<!-- res/xml/network_security_config.xml -->
<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">10.0.0.1</domain>
    </domain-config>
</network-security-config>
```

如果项目还留着 HTTP 端点，当前更实际的动作是两件事：先确认哪些域名必须保留明文访问，再把例外放到按域名配置的白名单里。这样即使未来 target SDK gate 继续提高要求，迁移成本也更可控。

Android 17 还把 ECH 策略接入 Network Security Configuration。`<domainEncryption>` 可按域名声明 ECH 策略；具体属性名以最终 API 37 SDK schema 为准，迁移时不要只看 manifest 里的全局开关。

```xml
<!-- API 37 示意:以最终 SDK schema 为准 -->
<network-security-config>
    <domain-config>
        <domain includeSubdomains="true">example.com</domain>
        <domainEncryption mode="enabled" />
    </domain-config>
</network-security-config>
```

### Encrypted Client Hello(ECH)

Android 17 支持 ECH (Encrypted Client Hello)。ECH 是 TLS 1.3 扩展，加密 TLS 握手中的 SNI (Server Name Indication)，防止网络观察者识别 App 连接的域名。

这一版平台先补了 ECH 所需 API，包括 DnsResolver 查询带 ECH 配置的 HTTPS 记录，以及 Conscrypt 侧 `SSLEngine` / `SSLSocket` 的相关能力。对 `targetSdkVersion` ≥ 37 的 App，`<domainEncryption>` 默认 `mode="enabled"`：建立 TLS 握手时如果提供了 ECH 配置就启用 ECH，否则启用 ECH GREASE；也可以按域设置 `mode="disabled"`。具体到 HttpEngine、WebView、OkHttp 等库，要看各自版本何时接入这些平台 API。平台支持和库已经可用，是两回事。

从性能角度看，ECH 的额外成本取决于 DNS / HTTPS 记录查询、库实现和服务端部署方式。连接协商失败时会回退到普通 TLS 握手，不适合给一个固定的延迟数字。

### Certificate Transparency 默认启用

对于 `targetSdkVersion` ≥ 37 的 App，Certificate Transparency (CT) 默认启用。系统会增加证书和 SCT (Signed Certificate Timestamp) 校验约束。如果证书链或服务器提供的 SCT 不满足要求，连接会被拒绝。localhost / 本地调试域名通常不按公网证书链处理，排障时要把本地例外和公网域名分开。

排障时不要把 CT 理解成"每次 HTTPS 建连都会额外请求一次 CT Log 服务器"。更常见的路径是校验证书里内嵌或握手携带的 SCT；是否出现额外网络往返，取决于证书链和服务器交付方式。

### HPKE 混合加密 SPI

Android 17 新增了 HPKE (Hybrid Public Key Encryption) 的加密服务提供者接口 (SPI)。HPKE 是一种标准化的公钥加密方案，设计目标是简化和标准化加密消息的发送。这个 API 主要用于端到端加密场景，对大多数 App 的性能没有直接影响，但如果你在实现自定义加密协议，可以考虑使用平台提供的 HPKE 实现来替代自研方案。

---

## 编译链背景：与 API 37 同期演进，但不属于强制行为变更

Baseline Profiles、Startup Profiles、Cloud Profiles、JIT 和系统侧 AutoFDO，会影响安装后首启、热点代码编译和整体运行时表现，但它们不属于"targetSdk 升到 37 就会立刻切换"的兼容行为。把这部分和前面的 DeliQueue、ProfilingTrigger、JobScheduler 诊断 API 放在同一层，容易把适配优先级看错。

排障时先分清三件事：

- App 自带了什么 Baseline / Startup Profiles
- 分发路径是否提供 cloud profile 或预编译产物
- 系统镜像 / 内核是否带平台级编译优化

如果观察到同一 APK 在不同设备、不同安装方式上的启动差异，这一层值得继续往下查。更完整的背景放到 **1.7 ART 编译机制**、**1.12 AutoFDO 优化**、**8.7 Baseline Profiles** 里看会更合适。

---

## 其他需纳入适配清单的变更

### 16KB 页面大小对原生库的影响

Android 继续推动 16KB 页面大小的适配，这个变更对使用 NDK 的原生库有直接影响。某些原生库存在对 4KB 页面大小的硬编码假设，在 16KB 页面设备上可能导致以下问题：

**受影响的原生库类型：**
- **游戏引擎**：特别是较老版本的 Unity、Unreal Engine 可能在内存分配和 mmap 操作中使用硬编码的 PAGE_SIZE 常量
- **图像处理库**：OpenCV、Skia 等库在处理图像数据分配时可能假设 4KB 页面匹配
- **数据库引擎**：SQLite、RocksDB 等存储引擎在内存映射文件时可能使用 4KB 匹配
- **音视频编解码器**：FFmpeg、MediaCodec 等在处理 Buffer 时可能有内存匹配假设

**具体问题和解决方案：**
1. **mmap offset 匹配问题**：使用 `mmap()` 时 `offset` 参数必须是 16KB 匹配，而非传统的 4KB 匹配。受影响的典型场景包括 SQLite 的 WAL 模式文件映射、RocksDB 的 SSTable mmap 读取
2. **PAGE_SIZE 常量硬编码**：原生代码中直接使用 `4096` 而非 `sysconf(_SC_PAGESIZE)` 运行时查询。已知案例：FFmpeg 的某些编解码器模块在 buffer 分配时硬编码 4096 匹配；OpenCV 的 `Mat` 数据分配在特定版本中假设 4KB 页面
3. **ELF 段匹配**：共享库需要使用 NDK r28+ 编译，确保 ELF 段按 16KB 匹配。未匹配的 .so 文件在 16KB 页面设备上加载时会抛出 `UnsatisfiedLinkError`

**官方文档与工具链配置：**
- 官方指南：[Build 16 KB-aligned ELFs](https://developer.android.com/guide/practices/page-sizes)
- Google Play 强制要求：2025 年 11 月 1 日起，新 App 和更新必须支持 16KB 页面大小
- AOSP 构建：`PRODUCT_MAX_PAGE_SIZE_SUPPORTED := 16384`
- NDK 编译：使用 `-Wl,-z,max-page-size=16384` 链接标志（NDK r27 及以下版本)
- 运行时检测：使用 `sysconf(_SC_PAGESIZE)` 替代硬编码常量
- 验证工具：`readelf -l lib.so` 检查 ELF 段匹配；Android Studio APK Analyzer 可自动识别未匹配的 .so 文件

详见 **4.7 16KB 页面大小** 章节。

### App memory limits 与异常触发器

Android 17 对部分设备引入基于设备总 RAM 的 app memory limits。这项限制影响所有运行在 Android 17 的应用，但只在部分设备上施加；触发后 `ApplicationExitInfo.getReason()` 可能是 `REASON_OTHER`，`getDescription()` 会包含 `MemoryLimiter:AnonSwap`。排障时可结合 `TRIGGER_TYPE_ANOMALY` 获取 memory limit hit 时的 heap dump，并用 `adb shell am memory-limiter status` 查看当前限制状态；`ignore` / `manual` 子命令只适合测试或复现实验。不要把这一路径和 LMKD 普通低内存杀进程混为一类。

### 后台音频限制加强

Android 17 对所有 App（无论 `targetSdkVersion`）强制执行后台音频限制。当 App 不在有效生命周期状态时，音频播放和音量调节 API 会静默失败；`AudioManager.requestAudioFocus()` 返回 `AUDIOFOCUS_REQUEST_FAILED`，而不是静默丢弃。targetSdk 37 的应用还面临更严格的 FGS 约束：后台音频相关的 foreground service 需要 while-in-use capability，或同时持有 exact alarm schedule 权限并使用 `USAGE_ALARM` 用途。这对音乐播放器和语音通话类 App 有影响。

### 更安全的 Native 动态代码加载

DCL (Dynamic Code Loading) 保护从 DEX/JAR 文件扩展到原生库。通过 `System.load()` 加载的所有 native 文件必须标记为只读，否则抛出 `UnsatisfiedLinkError`。如果你有动态下载 .so 文件并加载的逻辑，需要确保在加载前调用 `chmod` 设置只读权限。

---

## 迁移检查清单

从 Android 16 升级到 Android 17 的性能相关必检项：

- [ ] 搜索代码中所有 `MessageQueue` 的反射访问，确认是否有依赖 `mMessages` 等私有字段的逻辑
- [ ] 搜索 `Field.setAccessible(true)` + `static final` 的组合，确认测试代码是否需要重构
- [ ] 检查所有明文 HTTP 端点，尽量迁移到 HTTPS，并把必须保留的例外迁到 Network Security Configuration
- [ ] 在 600dp+ 设备上测试 App 的方向和多窗口行为
- [ ] 检查 JNI 代码中是否有直接操作 `MessageQueue` native 层的逻辑
- [ ] 确认 NDK 原生库在 16KB 页面大小设备上的兼容性
- [ ] 检查 `ApplicationExitInfo` 中是否出现 `MemoryLimiter:AnonSwap`，并为 Android 17 memory limits 准备 heap dump / anomaly trigger 排障路径
- [ ] 检查 `System.load()` 加载动态下载的 .so 文件是否设置了只读权限
- [ ] 验证 `JobScheduler` 任务在新 API 下的行为是否符合预期

---

## 参考资料

- [Android 17 Behavior Changes (官方)](https://developer.android.com/about/versions/17/behavior-changes-17)
- [MessageQueue behavior change guidance (官方)](https://developer.android.com/about/versions/17/changes/messagequeue)
- [Android 17 Features and Changes (官方)](https://developer.android.com/about/versions/17/features)
- [ProfilingTrigger API Reference (官方)](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [JobScheduler API Reference (官方)](https://developer.android.com/reference/android/app/job/JobScheduler)
- [Network Security Configuration / ECH (官方)](https://developer.android.com/privacy-and-security/security-config)
- [16 KB Page Size Guide (官方)](https://developer.android.com/guide/practices/page-sizes)
- [Android Developers Blog: Under the hood: Android 17's lock-free MessageQueue](https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html)
- [Google Blog: Android 17 Developer Preview](https://android-developers.googleblog.com/)
- [Android 17 DeliQueue 解读(掘金)](https://juejin.cn/post/7612812060795093002)
- [Android 17 适配要点(掘金)](https://juejin.cn/post/7610233341305389099)
- AOSP: `frameworks/base/core/java/android/os/CombinedMessageQueue/MessageQueue.java`
- AOSP: `frameworks/base/core/java/android/os/ConcurrentMessageQueue/MessageQueue.java`
- AOSP: `frameworks/base/core/java/android/os/LegacyMessageQueue/MessageQueue.java`
- AOSP: `art/runtime/gc/collector/` 目录下的分代 GC 实现
- AOSP: `packages/modules/Profiling/` 目录下的 ProfilingManager 实现

## 附录：DeliQueue drain 触发机制与 Generational CMC gating 条件

以下是对正文中 DeliQueue drain 触发条件、Generational CMC gating、ProfilingManager 触发器和 ConcurrentMessageQueue 数据结构的补充核对：

### DeliQueue drain 触发条件和内部实现

**源码位置**:
- `frameworks/base/core/java/android/os/ConcurrentMessageQueue/MessageQueue.java` (android-16.0.0_r1)
- `frameworks/base/core/java/android/os/Looper.java`

**关键发现**：
DeliQueue 的 drain 过程在 Android Developers Blog 中有明确描述：Looper 的 `next()` 方法在准备取下一条消息时，从 Treiber Stack 的顶部开始向下遍历，直到遇到上次处理过的消息。遍历过程中，每遇到一条新消息就将其插入 min-heap（按 `when` 排序）。同时，遍历过程中会建立反向链接，形成双向链表，以支持 O(1) 的任意位置移除。

drain 的触发时机是 Looper 需要下一条消息时——按需触发，不是基于阈值或定时器。drain 的频率取决于消息消费速度和投递速度的差值：当 Looper 消费完当前堆中所有消息后，下一次 `next()` 调用会触发 drain。

```java
// DeliQueue drain 过程（基于 Android Developers Blog 描述）
// Looper 的 next() 方法中的核心 drain 逻辑:
// 1. 从 Treiber Stack 顶部向下遍历到上次处理过的消息
// 2. 遍历中插入每条新消息到 min-heap（按 when 排序）
// 3. 建立反向链接形成双向链表（支持 O(1) 任意位置移除）
// 4. 从 min-heap 中取出 when 最近的消息返回
```

**与 Looper 主循环的集成**:
drain 是 Looper 主循环的一部分，不是独立线程。`Looper.loop()` 每次迭代调用 `MessageQueue.next()`，`next()` 内部在堆为空或需要下一条消息时执行 drain。也就是说，drain 的执行在主线程上，如果 Treiber Stack 中积压了大量消息，drain 本身也会占用主线程时间——但这个成本通常远小于它消除的锁竞争收益。

AOSP 实现在此基础上增加了同步屏障和异步消息的专门处理路径。当存在 barrier 时，drain 过程会优先处理异步消息。

### Generational CMC 具体 gating 条件

**源码位置**:
- `art/runtime/runtime.cc`
- `art/runtime/gc/collector/young_mark-compact.cc`

**gating 条件验证**：
通过 AOSP 源码验证，Generational CMC 启用需要同时满足三个条件：

```cpp
bool Runtime::useGenerationalCMC() const {
    // 条件0: 硬件能力检查（Init 阶段评估）
    bool hw_supported = generational_cmc_supported;
    
    // 条件1: userfaultfd 系统调用可用（编译期常量）
    bool use_userfaultfd = kUseUserfaultfd;
    
    // 条件2: 设备配置启用
    bool device_config_enabled = 
        device_config::runtime_native_boot_use_generational_gc(false);
    
    return hw_supported && use_userfaultfd && device_config_enabled;
}
```

**实际配置方法**：
- 通过 `adb shell device_config set runtime_native_boot use_generational_gc true` 强制开启
- 需要 `persist.device_config.runtime_native_boot.use_generational_gc` 属性设置为 true
- 必须在编译时启用 `kUseUserfaultfd` 特性


### ProfilingManager 触发器内部判断逻辑

API 37 公开文档只给出了触发器常量和注册入口，**没有公开服务端内部判断逻辑**。`ProfilingManagerService` 的源码在当前 AOSP preview 中不可直接核验，因此正文保留已确认的 API 口径，不给未验证的内部伪代码。

**已确认的 API 口径**（`android.os.ProfilingTrigger` reference）：

| 触发器常量 | Added in | 公开口径 | 排障定位 |
|-----------|----------|---------|----------|
| `TRIGGER_TYPE_APP_FULLY_DRAWN` | API 36 | App 完成首次绘制后触发 | 启动尾段 |
| `TRIGGER_TYPE_COLD_START` | API 37 | App 冷启动时尽早触发 | call stack sample + system trace |
| `TRIGGER_TYPE_ANOMALY` | API 37 | 系统检测到 App 异常行为时触发 | memory limit breach 可触发 heap dump，Binder spam 可触发 stack sampling profile |
| `TRIGGER_TYPE_OOM` | API 37 | App 发生 OOM 时触发 | 内存诊断 |
| `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` | API 37 | App 因异常 CPU 占用被杀时触发 | call stack sample / system trace snapshot 口径需按 `ProfilingResult` 实际返回判断 |
| `TRIGGER_TYPE_APP_COMPAT` | API 37 | 兼容性问题触发 | 兼容性排查 |


### ConcurrentMessageQueue 实际数据结构

**源码位置**：
- `frameworks/base/core/java/android/os/ConcurrentMessageQueue/MessageQueue.java`

**关键数据结构发现**：
根据 Android Developers Blog 官方描述，DeliQueue 使用 Treiber Stack + min-heap 的混合结构，不是 `ConcurrentSkipListSet` 排序集合：

```java
// DeliQueue 核心结构（基于 Android Developers Blog 官方描述）
// 写入端: Treiber Stack (无锁栈)
public class TreiberStack<E> {
    AtomicReference<Node<E>> top = new AtomicReference<Node<E>>();
    
    public void push(E item) {
        Node<E> newHead = new Node<E>(item);
        Node<E> oldHead;
        do {
            oldHead = top.get();
            newHead.next = oldHead;
        } while (!top.compareAndSet(oldHead, newHead)); // CAS 入队
    }
}

// 读取端: min-heap (最小堆), 由 Looper 线程独占访问
// drain 过程: Looper 遍历 Treiber Stack, 将消息插入 deadline-ordered min-heap
// 移除: tombstoning — CAS 设置移除标记, 物理移除由 Looper 延迟完成
```

**性能影响**：
- 消息入队：O(1) CAS 操作（Treiber Stack push）
- 消息出队：O(log n)（min-heap extract-min），尾部延迟优于旧单链表的 O(n) 最坏情况
- 移除操作：O(1) CAS 设置墓碑标记 + Looper 延迟物理移除
- 内存开销：Treiber Stack 的 Node 对象 + min-heap 数组通常高于旧单链表；具体比例取决于队列长度、消息生命周期和实现细节，需要用同一 workload 下的 heap / trace 数据验证

**兼容性影响**：
`mMessages` 字段保留二进制兼容性，但永远返回 null，反射依赖的测试框架需升级到 Espresso 3.7+ 和 Robolectric 4.17+。

### 版本兼容性建议

| 组件 | Android 16 状态 | Android 17 状态 | 适配建议 |
|------|---------------|---------------|---------|
| DeliQueue | 仅限 SystemUI/system processes | targetSdk 37 默认启用 | 测试兼容性，可用 `adb am compat` 开关控制 |
| Generational CMC | 不可用 | 需满足 gating 条件 | 通过 device_config 验证配置状态 |
| ProfilingManager | API 36 基础触发器 | API 37 新增 3 个触发器 | 按版本注册不同触发器集合 |
| ConcurrentMessageQueue | 存在但不默认启用 | 默认启用 | 反射代码需适配 null 值 |


## 附：Choreographer Buffer Stuffing Recovery（Android 16 新增）


Android 16 在 Choreographer 中引入 **Buffer Stuffing Recovery** 机制，新增 `BufferStuffingState` 内部类管理恢复状态，新增 `onWaitForBufferRelease()` @hide API 供图形客户端调用。

### 关键发现

| 发现 | 源码位置 | 说明 |
|------|---------|------|
| BufferStuffingState | Choreographer.java l.185-206（估算） | 内部枚举类，管理 isStuffed / isRecovering / numberWaitsForNextVsync |
| onWaitForBufferRelease() | Choreographer.java | @hide API，duration > 半帧周期时触发 |
| mLastNoOffsetFrameTimeNanos | Choreographer.java | 保留不含偏移的帧时间用于空闲判断 |
| CALLBACK_* 队列 | Choreographer.java | 五类回调：INPUT/ANIMATION/INSETS_ANIMATION/TRAVERSAL/COMMIT |

### 版本边界

| 版本 | Buffer Stuffing Recovery | onWaitForBufferRelease |
|------|-------------------------|------------------------|
| Android 14 (API 34) | ❌ | ❌ |
| Android 15 (API 35) | ❌ | ❌ |
| Android 16 (API 36) | ✅ | ✅ @hide |

### 性能关联

此机制与 Android 17 DeliQueue 的 lock-free 改造属于不同层面的优化：
- **DeliQueue**：解决 MessageQueue 消费端的锁竞争
- **Buffer Stuffing Recovery**：解决 Buffer Dequeue 阻塞导致的帧节拍错位

两者共同改善滑动流畅性，但针对的问题根源不同。


<!-- AIW-源码调研-2026-06-08-strictmode-safer-intent -->

## 安全相关：Safer Intent 与 StrictMode 新违规检测（Android 17）

> ⚠️ **未进入 Android 17**：android-17.0.0_r1 公开 tag 未发布，本节基于 `frameworks/base` 的 `main` 分支 commit 抓取。android.googlesource.com 的 `android-17.0.0_r1` 直接访问返回 `NOT_FOUND`（需要登录后的 `+android-17.0.0_r1` 命名空间路径）。最终行为以 release tag 为准。

Android 17 在 `android.os.StrictMode` 中新增了两类 VM 策略违规检测位，与 Safer Intent 主线在 system_server 端的 hook 配合：

### 1. `DETECT_VM_UNSAFE_INTENT_LAUNCH`（bit 13）

检测从外部 app 进入并被本进程二次启动的 `Intent`，对应 `Builder.detectUnsafeIntentLaunch()`（`frameworks/base/core/java/android/os/StrictMode.java`，main HEAD l.1137-1138）。三类具体事件通过 `FrameworkStatsLog.UNSAFE_INTENT_EVENT_REPORTED` 原子从 system_server 端 statsd 上报：

| 事件类型枚举 | 含义 | StrictMode 消息 |
|--------------|------|-----------------|
| `EXPLICIT_INTENT_FILTER_UNMATCH` | 显式 Intent 目标 component 的 `<intent-filter>` 不匹配 | `Intent mismatch target component intent filter: <intent>` |
| `INTERNAL_NON_EXPORTED_COMPONENT_MATCH` | 隐式 Intent 命中 `android:exported=false` 的内部组件 | `Implicit intent matching internal non-exported component: <intent>` |
| `NULL_ACTION_MATCH` | Intent 缺 action | `Launch of intent with null action: <intent>` |

### 2. `DETECT_VM_BACKGROUND_ACTIVITY_LAUNCH_ABORTED`（bit 14）

对应 `Builder.detectBlockedBackgroundActivityLaunch()`，**额外门控**：`@FlaggedApi(Flags.FLAG_BAL_STRICT_MODE_RO)` + `targetSdk > Build.VERSION_CODES.VANILLA_ICE_CREAM`（API 35）。AMS BAL 决策拒绝 Activity/PendingIntent 启动时调用 `StrictMode.onBackgroundActivityLaunchAborted(String)` 上抛 `BackgroundActivityLaunchViolation`。

### 完整调用链

```
[app 进程]                              [system_server]
                                         
StrictMode.Builder                          SaferIntentUtils
  .detectUnsafeIntentLaunch()                 .reportUnsafeIntentEvent(...)
       │                                       (PMS/AMS intent resolution hook)
       ▼                                       │
StrictMode 实例                               ├──▶ FrameworkStatsLog.write(
  .setVmPolicy(...)                              UNSAFE_INTENT_EVENT_REPORTED, ...)
       │                                       │
       ▼                                       └──▶ ActivityManagerInternal
registerIntentMatchingRestrictionCallback()              .triggerUnsafeIntentStrictMode(
  注册 IUnsafeIntentStrictModeCallback.Stub              callingPid, event, intent)
       │                                       │
       ▼                                       ▼
 AMS.registerStrictModeCallback(IBinder)     binder 跨进程回调
   mStrictModeCallbacks.put(pid, stub)             │
       │                                       ▼
       ▼                            UnsafeIntentStrictModeCallback
 [后续违规触发]                            .onUnsafeIntent(type, intent)
       │                              → StrictMode.onUnsafeIntentLaunch(type, intent)
       ▼                              → onVmPolicyViolation(
   onVmPolicyViolation(                     new UnsafeIntentLaunchViolation(
     new UnsafeIntentLaunchViolation(...))     intent, msg + intent))
   默认 PENALTY_LOG                        默认 PENALTY_LOG
```

### 关键源码位置

| 项 | 文件 | 关键行（main HEAD） |
|---|------|---------------------|
| `DETECT_VM_*` 位定义 | `frameworks/base/core/java/android/os/StrictMode.java` | l.320-322 |
| Builder API | `StrictMode.java` | l.1137-1186 |
| 默认启用条件 | `StrictMode.java` | l.914-918 |
| 回调 Stub | `StrictMode.java` | l.2206-2213 |
| 事件类型 dispatch | `StrictMode.java` | l.2467-2482 |
| BAL violation 入口 | `StrictMode.java` | l.2486-2488 |
| 实体类 | `frameworks/base/core/java/android/os/strictmode/UnsafeIntentLaunchViolation.java` | 完整文件（2021 copyright，扩展） |
| AMS 注册端点 | `frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java` | l.9471-9480，`mStrictModeCallbacks` l.719-721 |
| SaferIntentUtils 上报 | `frameworks/base/services/core/java/com/android/server/pm/SaferIntentUtils.java` | `reportUnsafeIntentEvent` 函数（l.115-150 区段） |
| Filter mismatch 标记 | `frameworks/base/core/java/android/content/Intent.java` | `EXTENDED_FLAG_FILTER_MISMATCH = 1 << 0`（l.7737） |

### 性能与诊断影响

- **statsd 写入轻量**：走 FrameworkStatsLog 原子通道，批处理、不阻塞 PMS/AMS 锁内调用方。
- **binder 回调开销**：AMS `mStrictModeCallbacks` 是 `SparseArray` 按 `callingPid` 索引，O(1) 注册。binder Intent 走 Parcel 序列化，频次低。
- **app 端 penalty**：默认 `PENALTY_LOG`，不杀进程；APM 想截获需开启 `PENALTY_DROPBOX` 或自实现 `OnVmViolationListener`。
- **APM 序列化约束**：`UnsafeIntentLaunchViolation.mIntent` 标注 `transient`，跨进程上传后 `getIntent()` 返回 null。回放原始 Intent 必须在 app 端序列化。
- **过滤位持久化**：`Intent.EXTENDED_FLAG_FILTER_MISMATCH` 在 startService / startActivity 调用前由 AMS `removeExtendedFlags` 清掉再 resolve（`ActivityManagerService.java` l.13706, l.13948），可作为 APM 流程的 hook 点。

### 适配清单

- [ ] 在 StrictMode 调试构建中开启 `detectUnsafeIntentLaunch()`，对三类事件做本地日志落盘（注意 `transient` Intent 限制）。
- [ ] 业务涉及 `PendingIntent` 且 targetSdk ≥ 34：检查是否使用 mutable+implicit 组合，Android 17 仍阻断（与 StrictMode 检测位无直接耦合，但共用 `SaferIntentUtils.reportUnsafeIntentEvent` 管线）。
- [ ] 若依赖 `mStrictModeCallbacks` 做自定义 BAL 决策观察：需注意它是 AMS `SparseArray` 按 PID 索引，进程死亡会清除条目。
- [ ] `ENFORCE_INTENTS_TO_MATCH_INTENT_FILTERS`（ChangeId 161252188）当前 `@Disabled`，可通过 `cmd compat enable <change-id>` 临时开启验证。

### 待验证

- `BackgroundActivityLaunchViolation` 完整 Javadoc 与 reason 字段。
- `IUnsafeIntentStrictModeCallback.aidl` 的 `@VintfStability` 标注与 version 字段。
- AMS 端 `mStrictModeCallbacks` 是否在 binder death 时主动清理。
- `balStrictModeRo` flag 的默认值与灰度路径。
- `vmUnsafeIntentLaunchEnabled()` 全局开关的 DeviceConfig 入口与默认值。

更完整的源码分析与未验证项见 DeepResearch 报告：`2026-06-08-android-17-strictmode-safer-intent-violations.md`。
