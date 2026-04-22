---
title: "Android 17 (API 37) 性能行为变更与适配方法"
chapter: "16.5"
status: ready-for-review
drafted_date: "2026-04-08"
applicable_versions: "Android 17 (API 37)"
last_verified: "2026-04-21"
last_verified_against: "AOSP android-17-beta3"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17"
  - type: official
    path: "https://developer.android.com/about/versions/17/features"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingTrigger"
  - type: official
    path: "https://developer.android.com/reference/android/app/job/JobScheduler"
  - type: official
    path: "https://developer.android.com/privacy-and-security/security-config"
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
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
pipeline_stage: task6_pending
task6_state: revisiting
task6_result: pass-light-edit
task9_state: pending
task2b_state: fixed
reviewed_by: openclaw-task6
reviewed_date: "2026-04-20"
task2b_rework_date: "2026-04-21"
task2b_fixed_at: "2026-04-21T13:17:26+08:00"
task9_result: needs-rework
last_task9_at: "2026-04-21T12:29:00+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-04-21
task2b_result: fixed
---

# 16.5 Android 17 (API 37) 性能行为变更与适配方法

## 为什么要了解 Android 17 的性能行为变更

`targetSdkVersion` 升级到 37 的 App 必须适配 Android 17 的几项底层变更:重写 `MessageQueue`、ART 分代垃圾回收、`static final` 字段不可强制、网络配置迁移。任何一项未适配都可能导致性能下降或崩溃。

这些变更在 Perfetto 中留下明确特征：DeliQueue 减少主线程锁竞争；分代 GC 改变 Memory Track 中的 GC 切片模式；ProfilingManager 新触发器统一系统事件采样。掌握这些特征，是解决 Android 17 性能问题的关键。

本章聚焦性能相关的核心变更,按影响程度和适配优先级排序。

---

## DeliQueue:20 年来 MessageQueue 的最大架构变更

### 旧实现的问题

从 Android 1.0 开始,`MessageQueue` 的核心数据结构就是一个 `synchronized` 保护的 singly linked list。所有线程通过 `Handler.sendMessage()` 或 `Handler.post()` 投递消息时,都需要获取同一把锁。在 Looper 线程(通常是主线程)从队列头部取消息执行时,其他线程如果想投递消息,就必须等主线程释放锁。

在日常场景下这个锁争用几乎不存在--消息投递操作很快,持有锁的时间极短。但在高并发场景下,问题就暴露出来了。一个典型案例:Launcher 在后台加载应用列表时,多个工作线程同时向主线程投递消息,而主线程正在执行一次耗时的布局计算。此时所有投递操作都被阻塞在 synchronized 块上,主线程的 `enqueueMessage()` 等待时间在 Perfetto 中表现为一截 Lock Wait 切片。如果这个等待恰好发生在 VSync 周期内,就会导致掉帧。

在 Perfetto Trace 中,旧实现的锁争用表现为:
- Main Thread Track 中出现名为 "monitor contention with MessageQueue" 的切片
- 等待线程显示为 Sleeping 状态,持有锁的线程正在执行 Handler 相关代码
- 锁等待时间通常在 1-5ms 范围,但多次累积就会导致帧时间超过 16.6ms(60fps)
- 特别出现在 `Choreographer.doFrame` 期间的消息投递操作中

[待补充:Perfetto Trace 截图,展示旧 MessageQueue 实现下主线程 "monitor contention with MessageQueue" 锁等待切片,以及多线程并发投递时的阻塞特征]

### 新实现:DeliQueue 的混合数据结构

Android 17 用一个名为 DeliQueue 的实现替换了旧的 `MessageQueue`。核心设计思路是将"多线程写入"和"单线程读取"分离开来:

- **写入端**:使用 Treiber Stack(一种无锁栈),通过 CAS(Compare-And-Swap)操作实现多线程并发入队,不需要任何锁
- **读取端**:使用 min-heap(最小堆),由 Looper 线程独占访问,按消息的 `when`(执行时间)排序,天然有序

工作流程是这样的:当任何线程通过 `Handler` 投递一条消息时,消息被 push 到 Treiber Stack 中,这是一个 O(1) 的 CAS 操作,不需要获取锁。当 Looper 线程进入 `loop()` 的下一次迭代时,它会将 Treiber Stack 中积压的所有消息批量"搬"到 min-heap 中(drain 操作),然后从 min-heap 中按时间顺序取出下一条消息执行。

这个设计的精妙之处在于:Treiber Stack 只负责"暂存",不需要维护顺序;min-heap 只负责"调度",只被 Looper 线程访问。两者各司其职,互不干扰。

```
[图:DeliQueue 数据流示意图]
Thread A ──CAS push──▶ Treiber Stack ──drain──▶ Min-Heap ──poll──▶ Looper.loop()
Thread B ──CAS push──▶      ↑                         ↑
Thread C ──CAS push──▶      │                         │
                         (无锁)                   (独占访问)
```

### 性能收益

Google 在内部测试中给出的数据：

- App 掉帧减少 **4%**
- System UI 和 Launcher 交互掉帧减少 **7.7%**
- 主线程锁等待时间减少约 **15%**
- App 启动速度有可测量的提升

这些数字表明:**无需代码修改**,只要 `targetSdkVersion` 升级到 37,App 就自动获得这些性能提升。框架通过无锁队列设计解决了主线程锁争用问题。

### 适配要点

DeliQueue 对绝大多数 App 完全透明。`Handler`、`Looper`、`Message` 的公共 API 没有任何变化。但有一个重要的破坏性变更:**通过反射访问 `MessageQueue` 的私有字段将不再工作。**

旧实现中 `MessageQueue.mMessages` 字段指向链表头节点。一些框架和工具库(比如某些消息监控库、LeakCanary 的早期版本)通过反射读取这个字段来监控消息队列状态。在 DeliQueue 中,`mMessages` 为了保持二进制兼容性仍然存在,但**始终为 null**。消息数据存储在新的内部数据结构中。

如果你的项目中有以下情况,需要检查:

1. 反射访问 `MessageQueue.mMessages` 或其他私有字段
2. 通过 JNI 直接操作 `MessageQueue` 的 native 层结构
3. 使用了依赖上述反射行为的第三方库

[待验证:AOSP android-17-beta3 中 MessageQueue.java 的具体字段变更]

---

## ART 分代垃圾回收

### 从 Concurrent Copying 到 Generational CMC

ART 的垃圾回收器经历过多次演进。Android 8(Oreo)将 Concurrent Copying(CC)作为默认 GC,解决了 Compact GC 的长暂停问题。Android 10 引入了分代 CC(Generational Concurrent Copying),将堆空间分为 young generation 和 old generation,优先回收存活时间短的 young 对象。

Android 17 进一步将分代思想整合到 **Concurrent Mark-Compact(CMC)** 收集器中。CMC 的特点是:标记和压缩都是并发执行的,应用线程只需要在标记开始和结束时经历极短的暂停(通常 < 1ms)。分代 CMC 在此基础上增加了 young generation 的快速回收路径。

### 分代回收的工作原理

分代 GC 的基本假设是"弱分代假说"(Weak Generational Hypothesis):大多数对象在创建后很快就变成垃圾。在 Android App 的实际运行中,这个假设非常成立--方法中的局部变量、临时构建的 `Message` 对象、`RecyclerView` 中滑出屏幕的 `ViewHolder` 绑定数据,这些对象的存活时间通常只有几毫秒到几秒。

分代 CMC 的工作方式:

1. 新创建的对象分配在 **young generation** 空间
2. 当 young generation 空间达到阈值时,触发一次 **young GC**--只扫描和回收 young generation 中的垃圾对象,忽略 old generation
3. 经历了若干次 young GC 仍然存活的对象,被**提升(promote)**到 old generation
4. 当 old generation 空间不足时,才触发一次 **full GC**--扫描整个堆

关键区别在于:young GC 只扫描一小部分堆空间,速度远快于 full GC。这直接减少了 GC 暂停对主线程的影响。

### 对 RecyclerView 滑动的实际影响

RecyclerView 滑动是 GC 敏感场景的典型代表。在滑动过程中,`onBindViewHolder()` 会为每个即将显示的 item 创建临时对象(字符串、Drawable、Bitmap 相关的配置对象等)。这些对象在 item 滑出屏幕后就变成垃圾。

在旧的非分代 GC 中,这些 young 对象会在 full GC 时才被回收。如果 full GC 恰好在 `doFrame()` 期间触发,就会造成帧延迟。在分代 GC 中,这些短命对象被 young GC 快速回收,full GC 的触发频率大幅降低。

[待补充:分代 GC vs 非分代 GC 在 RecyclerView 滑动场景下的 Perfetto 对比截图]

### 与 4.8 ART 分代 GC 章节的关系

本节概述了 Android 17 中分代 GC 的变更和对性能的影响。关于 ART GC 的完整机制(Concurrent Mark-Compact 的工作原理、GC 暂停的产生机制、在不同 Android 版本中的演进),详见 **4.8 ART 分代垃圾回收**。

---

## ProfilingManager 新的系统触发器

### 从手动埋点到系统自动触发

Android 16 引入了 ProfilingManager,允许 App 在运行时请求 heap dump、stack sampling、system trace 等分析产物。Android 17 的新增点,是可以把采集条件交给系统触发器判断,但这仍是一套 trigger-based capture API,不是默认全局开启的自动抓取。

要用这套能力,App 仍要完成两步:先通过 `ProfilingManager.registerForAllProfilingResults()` 注册结果回调,再调用 `ProfilingManager.addProfilingTriggers()` 添加触发器。触发器常量定义在 `android.os.ProfilingTrigger`,真正的产物交付仍由 ProfilingManager 完成。[已验证: Android 17 features 页和 `android.os.ProfilingTrigger` reference 都把 trigger 描述成 ProfilingManager 的注册式能力,而不是无需代码的默认抓取]

### 触发器类型与产物

| 触发器 | 触发时机 | 产物类型 | 典型用途 |
|--------|---------|---------|---------|
| `ProfilingTrigger.TRIGGER_TYPE_COLD_START` | App cold start 尽早阶段 | stack sampling profile + newly started system trace | 定位冷启动瓶颈 |
| `ProfilingTrigger.TRIGGER_TYPE_OOM` | App 发生 `OutOfMemoryError` | Java heap dump | 诊断内存泄漏和内存过度使用 |
| `ProfilingTrigger.TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` | App 因异常 CPU 占用被系统杀死 | call stack sample | 定位后台 CPU 异常占用 |

[已验证: 上述三个触发器常量名称与 Android 17 API reference 一致。API 37 还新增了 `TRIGGER_TYPE_APP_FULLY_DRAWN`、`TRIGGER_TYPE_ANOMALY`、`TRIGGER_TYPE_APP_COMPAT` 等触发器,本节只保留和性能排障直接相关的几项。]

### 注册流程和适配建议

冷启动触发器的文档口径是"app cold start 时尽早触发",它适合补到比 `Application.onCreate()` 更早的启动证据,但仍要靠 ProfilingManager 的注册和回调流程接收产物,不能写成"系统默认替所有 App 抓 trace"。

`TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` 对应的是异常 CPU 占用导致的杀进程,结果更接近 call stack sample,不应写成 system trace。排障时,可以把 cold start、OOM、异常 CPU kill 这些系统事件交给 trigger-based capture,再在 Perfetto、heap dump 或采样结果上继续分析。

详见 **14.7 ProfilingManager**。

---

## JobScheduler pending reasons 诊断 API

### 为什么需要这组 API

`JobScheduler` 是 Android 后台任务调度的核心机制。过去排查"job 为什么没跑"时,很多信息只能从 `dumpsys jobscheduler` 里翻。Android 17 扩了 pending reasons 相关查询接口,但重点不是一个独立的 `JobDebugInfo` 类,而是 `JobScheduler` 上多了几组更细的诊断方法。

### API 边界

- `JobScheduler.getPendingJobReasonStats(int jobId)`:返回指定 job 在 pending 状态期间,各原因聚合后的 `Map<Integer, Duration>`
- `JobScheduler.getPendingJobReasons(int jobId)`:返回当前可能导致该 job pending 的 reason code 数组
- `JobScheduler.getPendingJobReasonsHistory(int jobId)`:返回有限历史视图,元素是 `PendingJobReasonsInfo`

这三组接口连起来,才能回答"某个 job 现在为什么没跑""过去一段时间主要卡在哪类约束上"。如果你的项目通过 WorkManager 间接落到 JobScheduler,调试时最好先拿到对应的 jobId,再对照这三组 API 看 current reason、history 和聚合时长。

与 **5.10 JobScheduler/WorkManager 性能** 章节交叉引用。

---

## static final 字段强制不可变

### 变更内容

从 Android 17(API 37)开始,通过反射或 JNI 修改 `static final` 字段将抛出 `IllegalAccessException` 或导致应用崩溃。在旧版本中,通过 `Field.setAccessible(true)` 可以绕过访问控制修改 `static final` 字段,虽然 Java 规范一直不保证这种操作的行为。

### 对性能的意义

为什么 Android 要强制这个限制?答案是 **ART 的常量折叠优化**。

当 ART 编译器确认一个 `static final` 字段的值在运行时不会改变时,它可以在编译时将所有引用该字段的代码直接替换为常量值(内联)。这消除了字段访问的开销,也使得后续的优化 pass(如死代码消除、循环优化)有更大的发挥空间。

如果允许运行时修改 `static final` 字段,ART 就不能做这个优化--它必须假设字段值可能被修改,每次访问都要从内存中读取。

### 受影响的场景

以下代码模式会受影响:

```java
// 1. 反射修改 static final 字段
Field field = SomeClass.class.getDeclaredField("CONSTANT");
field.setAccessible(true);
field.set(null, newValue); // Android 17 上抛 IllegalAccessException

// 2. JNI 层通过反射 API 修改
// 3. 测试框架通过反射注入 mock 值
// 4. 依赖反射修改 final 字段的依赖注入框架
```

### 适配建议

1. **检查测试代码**:很多单元测试通过反射修改 `static final` 字段来注入测试值。Android 17 上需要改用其他方式(如通过构造函数参数传入、使用非 final 字段 + setter、或者借助 `@VisibleForTesting` 注解暴露的内部 API)
2. **检查依赖注入框架**:某些 DI 框架(特别是较老版本的 Dagger 或 Guice)可能使用了这种技巧。升级到最新版本
3. **检查序列化/反序列化库**:某些 JSON/XML 解析库在反序列化时会修改 `final` 字段

---

## 大屏强制适配的性能影响

### 变更内容

对于 `targetSdkVersion` ≥ 37 的 App,在 smallest width ≥ 600dp 的设备上,以下 Manifest 属性将被忽略:

- `android:screenOrientation`(锁屏方向)
- `android:resizeableActivity="false"`(禁止调整大小)
- 宽高比限制

同时,`Activity` 的 `recreateOnConfigChanges` 行为变更:6 种配置变更(orientation、screenSize、smallestScreenSize、screenLayout、keyboard、keyboardHidden)不再触发 Activity 重建,改为通过 `onConfigurationChanged()` 回调通知。

### 对渲染性能的影响

这个变更对性能的影响主要体现在两个方面:

**1. 多窗口和折叠屏场景下的 Surface 数量变化**

当 App 被强制要求支持多方向和多窗口时,系统可能在生命周期中创建和销毁更多的 Surface。在折叠屏设备上,铰链展开/折叠时 App 需要在不同尺寸间切换。如果 App 的布局层级较深,每次配置变更时的 measure/layout 开销会累加。

在 Perfetto 中,你可以在 Main Thread Track 中观察到 `Choreographer#doFrame` 下 `performTraversal` 的执行时间。如果配置变更后布局耗时明显增加,说明布局需要优化。

**2. Configuration Change 的平滑过渡**

旧模式下,旋转屏幕会导致 Activity 销毁重建,在 Perfetto 中表现为一个明显的生命周期中断。新模式下通过 `onConfigurationChanged()` 处理,App 可以在不停顿的情况下完成布局切换。这在 Trace 中表现为一个连续的帧序列,而不是 Activity 生命周期回调导致的中断。

### 适配建议

如果你的 App 尚未适配大屏和折叠屏:

1. 使用 `WindowMetrics` API 替代硬编码的屏幕尺寸
2. 在 `onConfigurationChanged()` 中处理布局变更,而非依赖 Activity 重建
3. 在 Perfetto 中对比新旧模式下的帧时间分布,确认过渡是否平滑

---

## 网络与安全性能变更

### 明文流量迁移到 Network Security Configuration

Android 17 弃用 `android:usesCleartextTraffic`,迁移到 Network Security Configuration。manifest 中的 `usesCleartextTraffic` 不再是可靠配置,需将必须保留的明文访问迁到 `network_security_config.xml`。

```xml
<!-- res/xml/network_security_config.xml -->
<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">10.0.0.1</domain>
    </domain-config>
</network-security-config>
```

如果项目还留着 HTTP 端点,当前更实际的动作是两件事:先确认哪些域名必须保留明文访问,再把例外放到按域名配置的白名单里。这样即使未来 target SDK gate 继续收紧,迁移成本也更可控。

### Encrypted Client Hello（ECH）

Android 17 支持 ECH（Encrypted Client Hello）。ECH 是 TLS 1.3 扩展，加密 TLS 握手中的 SNI（Server Name Indication），防止网络观察者识别 App 连接的域名。

这一版平台先补了 ECH 所需 API,包括 DnsResolver 查询带 ECH 配置的 HTTPS 记录,以及 Conscrypt 侧 `SSLEngine` / `SSLSocket` 的相关能力。具体到 HttpEngine、WebView、OkHttp 等库,要看各自版本何时接入这些平台 API。平台支持和库已经可用,是两回事。

从性能角度看,ECH 的额外成本取决于 DNS / HTTPS 记录查询、库实现和服务端部署方式。连接协商失败时会回退到普通 TLS 握手,不适合给一个固定的延迟数字。

### Certificate Transparency 默认启用

对于 `targetSdkVersion` ≥ 37 的 App,Certificate Transparency(CT)默认启用。系统会增加证书和 SCT(Signed Certificate Timestamp)校验约束。如果证书链或服务器提供的 SCT 不满足要求,连接会被拒绝。

排障时不要把 CT 理解成"每次 HTTPS 建连都会额外请求一次 CT Log 服务器"。更常见的路径是校验证书里内嵌或握手携带的 SCT;是否出现额外网络往返,取决于证书链和服务器交付方式。

### HPKE 混合加密 SPI

Android 17 新增了 HPKE(Hybrid Public Key Encryption)的加密服务提供者接口(SPI)。HPKE 是一种标准化的公钥加密方案,设计目标是简化和标准化加密消息的发送。这个 API 主要用于端到端加密场景,对大多数 App 的性能没有直接影响,但如果你在实现自定义加密协议,可以考虑使用平台提供的 HPKE 实现来替代自研方案。

---

## 编译链背景:与 API 37 同期演进,但不属于强制行为变更

Baseline Profiles、Startup Profiles、Cloud Profiles、JIT 和系统侧 AutoFDO,会影响安装后首启、热点代码编译和整体运行时表现,但它们不属于"targetSdk 升到 37 就会立刻切换"的兼容行为。把这部分和前面的 DeliQueue、ProfilingTrigger、JobScheduler 诊断 API 放在同一层,容易把适配优先级看错。

做排障时,优先分清三件事:

- App 自带了什么 Baseline / Startup Profiles
- 分发路径是否提供 cloud profile 或预编译产物
- 系统镜像 / 内核是否带平台级编译优化

如果观察到同一 APK 在不同设备、不同安装方式上的启动差异,这一层值得继续往下查。更完整的背景放到 **1.7 ART 编译机制**、**1.12 AutoFDO 优化**、**8.7 Baseline Profiles** 里看会更合适。

---

## 其他值得注意的变更

### 16KB 页面大小对原生库的影响

Android 继续推动 16KB 页面大小的适配,这个变更对使用 NDK 的原生库有直接影响。某些原生库存在对 4KB 页面大小的硬编码假设,在 16KB 页面设备上可能导致问题:

**受影响的原生库类型:**
- **游戏引擎**:特别是较老版本的 Unity、Unreal Engine 可能在内存分配和 mmap 操作中使用硬编码的 PAGE_SIZE 常量
- **图像处理库**:OpenCV、Skia 等库在处理图像数据分配时可能假设 4KB 页面对齐
- **数据库引擎**:SQLite、RocksDB 等存储引擎在内存映射文件时可能使用 4KB 对齐
- **音视频编解码器**:FFmpeg、MediaCodec 等在处理 Buffer 时可能有内存对齐假设

**具体问题和解决方案:**
1. **mmap offset 对齐问题**:使用 `mmap()` 时 `offset` 参数必须是 16KB 对齐,而非传统的 4KB 对齐。受影响的典型场景包括 SQLite 的 WAL 模式文件映射、RocksDB 的 SSTable mmap 读取
2. **PAGE_SIZE 常量硬编码**:原生代码中直接使用 `4096` 而非 `sysconf(_SC_PAGESIZE)` 运行时查询。已知案例:FFmpeg 的某些编解码器模块在 buffer 分配时硬编码 4096 对齐;OpenCV 的 `Mat` 数据分配在特定版本中假设 4KB 页面
3. **ELF 段对齐**:共享库需要使用 NDK r28+ 编译,确保 ELF 段按 16KB 对齐。未对齐的 .so 文件在 16KB 页面设备上加载时会抛出 `UnsatisfiedLinkError`

**官方文档与工具链配置:**
- 官方指南:[Build 16 KB-aligned ELFs](https://developer.android.com/guide/practices/page-sizes)
- Google Play 强制要求:2025 年 11 月 1 日起,新 App 和更新必须支持 16KB 页面大小
- AOSP 构建:`PRODUCT_MAX_PAGE_SIZE_SUPPORTED := 16384`
- NDK 编译:使用 `-Wl,-z,max-page-size=16384` 链接标志(NDK r27 及以下版本)
- 运行时检测:使用 `sysconf(_SC_PAGESIZE)` 替代硬编码常量
- 验证工具:`readelf -l lib.so` 检查 ELF 段对齐;Android Studio APK Analyzer 可自动识别未对齐的 .so 文件

详见 **4.7 16KB 页面大小**章节。

### 后台音频限制加强

Android 17 对所有 App(无论 `targetSdkVersion`)强制执行后台音频限制:当 App 不在有效生命周期状态时,音频播放和焦点请求将静默失败。这对音乐播放器和语音通话类 App 有影响。

### 更安全的 Native 动态代码加载

DCL(Dynamic Code Loading)保护从 DEX/JAR 文件扩展到原生库。通过 `System.load()` 加载的所有 native 文件必须标记为只读,否则抛出 `UnsatisfiedLinkError`。如果你有动态下载 .so 文件并加载的逻辑,需要确保在加载前调用 `chmod` 设置只读权限。

---

## 迁移检查清单

从 Android 16 升级到 Android 17 的性能相关必检项:

- [ ] 搜索代码中所有 `MessageQueue` 的反射访问,确认是否有依赖 `mMessages` 等私有字段的逻辑
- [ ] 搜索 `Field.setAccessible(true)` + `static final` 的组合,确认测试代码是否需要重构
- [ ] 检查所有明文 HTTP 端点,尽量迁移到 HTTPS,并把必须保留的例外迁到 Network Security Configuration
- [ ] 在 600dp+ 设备上测试 App 的方向和多窗口行为
- [ ] 检查 JNI 代码中是否有直接操作 `MessageQueue` native 层的逻辑
- [ ] 确认 NDK 原生库在 16KB 页面大小设备上的兼容性
- [ ] 检查 `System.load()` 加载动态下载的 .so 文件是否设置了只读权限
- [ ] 验证 `JobScheduler` 任务在新 API 下的行为是否符合预期

---

## 参考资料

- [Android 17 Behavior Changes (官方)](https://developer.android.com/about/versions/17/behavior-changes-17)
- [Android 17 Features and Changes (官方)](https://developer.android.com/about/versions/17/features)
- [ProfilingTrigger API Reference (官方)](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [JobScheduler API Reference (官方)](https://developer.android.com/reference/android/app/job/JobScheduler)
- [Network Security Configuration / ECH (官方)](https://developer.android.com/privacy-and-security/security-config)
- [16 KB Page Size Guide (官方)](https://developer.android.com/guide/practices/page-sizes)
- [Google Blog: Android 17 Developer Preview](https://android-developers.googleblog.com/)
- [Android 17 DeliQueue 解读(掘金)](https://juejin.cn/post/7612812060795093002)
- [Android 17 适配要点(掘金)](https://juejin.cn/post/7610233341305389099)
- AOSP: `frameworks/base/core/java/android/os/MessageQueue.java`(android-17 分支)
- AOSP: `art/runtime/gc/collector/` 目录下的分代 GC 实现
- AOSP: `packages/modules/Profiling/` 目录下的 ProfilingManager 实现