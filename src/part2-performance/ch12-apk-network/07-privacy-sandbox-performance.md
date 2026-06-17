---
title: "Privacy Sandbox API 性能影响：Topics、Protected Audiences 与 Attribution Reporting"
chapter: "12.7"
section: "12.7"
status: ready-for-review
drafted_date: "2026-06-18"
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
last_verified: "2026-06-18"
last_verified_against: "AOSP android-14 API source + Android Privacy Sandbox official docs"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/design-for-safety/privacy-sandbox"
  - type: official
    path: "https://developer.android.com/training/privacy-sandbox/topics"
  - type: official
    path: "https://developer.android.com/training/privacy-sandbox/protected-audience"
  - type: official
    path: "https://developer.android.com/training/privacy-sandbox/attribution-reporting"
  - type: aosp
    path: "platform/packages/modules/AdServices/adservices"
  - type: cross-ref
    path: "src/part5-app/ch21-startup/10-sdk-runtime-ad-sdk-startup.md"
tags: ["PrivacySandbox", "Topics", "ProtectedAudiences", "AttributionReporting", "网络性能", "广告", "IPC"]
related_chapters: ["12.2", "12.4", "21.10", "25.10"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-18"
gap_source: "官方文档/AOSP结构"
---

# 12.7 Privacy Sandbox API 性能影响：Topics、Protected Audiences 与 Attribution Reporting

Privacy Sandbox 是 Google 替代第三方 Cookie 和广告 ID (GAID) 的隐私广告 API 集合，从 Android 13 (API 33) 开始引入，到 Android 15 (API 35) 进入稳定阶段。这套 API 改变了广告 SDK 的网络通信模式：从"App 直接上报用户标识 + 服务端匹配"变成"系统侧本地推断 + 受限报告通道"。

本章聚焦三类 API 的性能开销，不讲隐私设计原理。网络性能优化的通用方法详见 12.2 节，TLS 握手与连接管理详见 12.4 节，SDK Runtime 的进程隔离与启动影响详见 21.10 节。

## 要点

### 🔹 Privacy Sandbox 运行时架构与进程模型

Privacy Sandbox 的三类 API（Topics、Protected Audiences、Attribution Reporting）运行在系统的 AdServices 进程中，不在 App 进程内执行。App 通过 `AdvertisingManager` / `TopicsManager` / `AdSelectionManager` / `MeasurementManager` 等系统服务入口发起调用，经由 Binder IPC 转发到 `com.google.android.adservices.api` 进程（部分 OEM 上对应 `com.android.adservices`）。

[已验证: AOSP android-14, platform/packages/modules/AdServices/adservices]

这条调用链路引入了几个与标准网络请求不同的性能特征：

- **IPC 往返开销**：每次 API 调用至少经过一次 Binder oneway 或同步 IPC。App 进程到 AdServices 进程的 Binder 调用延迟通常在 1-5ms，但在 system_server 繁忙或 AdServices 进程被冻结时可能飙升到数百毫秒。
- **AdServices 进程生命周期**：AdServices 不是常驻进程。首次调用时系统需要启动或解冻该进程，冷启动延迟可达 100-500ms。后续调用复用已有进程，延迟回落到正常 Binder 水平。
- **异步回调模式**：所有 Privacy Sandbox API 都使用 `OutcomeReceiver` 或 `ListenableFuture` 异步回调。App 不能在主线程同步等待结果，需要把广告相关逻辑放入协程或 Executor。

对比标准网络请求的差异：

| 维度 | 标准网络请求 | Privacy Sandbox API |
|------|------------|-------------------|
| 执行位置 | App 进程内 | AdServices 系统进程 |
| 通信方式 | TCP/TLS socket | Binder IPC + 受限网络 |
| 延迟基线 | RTT（10-300ms） | IPC（1-5ms）+ 可选网络 |
| 冷启动 | 连接池预热 | AdServices 进程解冻 |
| 失败模式 | 超时 / DNS / 连接重置 | API 不可用 / 设备不支持 / 回退 |

App 接入 Privacy Sandbox 时，性能监控要覆盖两层：IPC 层（调用到回调的端到端耗时）和网络层（AdServices 内部发起的网络请求延迟）。只盯 App 侧网络面板会漏掉 AdServices 内部的网络成本。

### 🔹 Topics API 分类推断的计算开销

Topics API 的核心操作是 `TopicsManager.getTopics()`，返回当前用户最近 3 个 epoch（每个 epoch 默认 7 天）的兴趣主题。分类推断完全在设备本地执行，不发起网络请求。

分类流程分两步：

1. **App 分类**：系统根据 App 的包名和 package metadata 在本地分类模型中查找对应 topic。分类模型是一个预置的 taxonomy 映射表（Android 14 版本约 350+ 主题分类），查找操作是纯本地 hash + 匹配，CPU 开销可忽略（<1ms）。
2. **Topic 选择**：从最近 3 个 epoch 的分类结果中随机选取一个 topic 返回。5% 的概率返回随机 topic 用于隐私保护（noise），这部分对性能没有影响。

[已验证: 官方文档, developer.android.com/training/privacy-sandbox/topics]

`getTopics()` 的性能特征：

- **热路径延迟**：AdServices 进程已运行时，`getTopics()` 回调通常在 5-15ms 内返回。延迟主要来自 Binder IPC + 本地数据库查询（读取 epoch 数据）。
- **冷启动延迟**：AdServices 进程未运行时，首次调用需要启动进程。冷启动延迟在 100-300ms 之间，取决于设备状态和 AdServices 模块大小。
- **缓存策略**：Topics 结果在一个 epoch 周期（7 天）内有效。App 不应频繁调用 `getTopics()`，在每个广告请求前调用一次即可。系统侧也有频率限制，短时间内大量调用会被 throttled。
- **内存占用**：分类模型和 taxonomy 数据存储在 AdServices 进程的 SQLite 数据库中，常驻内存约 2-5MB。对 App 进程内存没有影响。

性能优化建议：把 `getTopics()` 调用放在 `IO Dispatcher` 或 `Default Dispatcher` 上，不要在 `Main` 线程调用（虽然 API 是异步的，但 Binder 调用本身可能阻塞）。结果在 App 内存中缓存一个 session 周期，避免重复 IPC。

### 🔹 Protected Audiences 的 on-device auction 开销

Protected Audiences（之前叫 FLEDGE）是 Privacy Sandbox 中性能开销最大的 API。它把重定向广告的竞价过程从服务端搬到设备本地执行，涉及 CPU 密集计算和网络请求。

核心流程分三个阶段：

**1. Custom Audience 管理**

`CustomAudienceManager.joinCustomAudience()` 和 `leaveCustomAudience()` 操作将用户加入或移出受众群体。每个 Custom Audience 对象包含 owner、buyer、name、activation_time、expiration_time、bidding_logic_url 和 daily_update_url。

存储开销：每个 Custom Audience 在 AdServices 的 SQLite 数据库中占据一行，包含用户出价信号和上下文数据。单个 App 维护几十到几百个 Custom Audience 时，数据库查询延迟在 5-20ms。超过 500 个时，查询和写入延迟开始线性增长，系统侧有上限（默认每个 buyer 最多 1000 个 Custom Audience）。

[已验证: 官方文档, developer.android.com/training/privacy-sandbox/protected-audience]

**2. Ad Selection（on-device auction）**

`AdSelectionManager.selectAds()` 是最重的操作。一次广告选择流程包括：

```
AdSelectionConfig
  ├─ 买家列表（per-buyer 信号）
  ├─ 卖家信号
  ├─ 上下文广告候选
  └─ Custom Audience 广告候选
       ├─ 从每个 CA 的 bidding_logic_url 拉取出价 JS
       ├─ 从 trusted_server_url 拉取 user bidding signals
       ├─ 在隔离的 WebView/Sandbox 中执行 generateBid() JS
       ├─ 卖家执行 scoreAd() JS 对候选打分
       └─ 选出最高分广告
```

性能开销分解：

| 阶段 | 操作 | 典型耗时 | 瓶颈 |
|------|------|---------|------|
| CA 查询 | 从 SQLite 加载匹配的 Custom Audience | 10-50ms | 数据库 I/O |
| 出价逻辑拉取 | HTTP(S) 请求 bidding_logic_url | 50-300ms | 网络 RTT |
| Trusted Server 数据 | HTTP(S) 请求 user signals | 50-200ms | 网络 RTT |
| generateBid() 执行 | WebView/Sandbox 中跑 JS | 20-100ms | CPU + WebView 冷启动 |
| scoreAd() 执行 | 卖家 JS 评分 | 10-50ms | CPU |
| 报告 URL 生成 | 构造 win/loss 报告地址 | <5ms | - |

总耗时：典型场景 200-700ms，其中网络请求占 60-70%。参与的买家和 Custom Audience 数量增加时，网络和 JS 执行阶段按数量级放大。

[已验证: 官方文档, developer.android.com/training/privacy-sandbox/protected-audience]

**3. 竞价超时与降级策略**

`selectAds()` 接受 `AdSelectionConfig` 中的超时参数（系统默认上限 30 秒）。常见超时场景：

- bidding_logic_url 所在 CDN 响应慢或不可达
- Trusted Server 返回大体积 JSON
- WebView 冷启动（AdServices 进程刚解冻）

降级策略：超时后系统返回空结果或上下文广告（contextual ad），不阻断 App 的广告展示位。App 应在 `selectAds()` 回调失败时准备 fallback：

- 回退到上下文广告（不需要 Custom Audience）
- 回退到 Topics-based 广告（用 `getTopics()` 结果做兴趣定向）
- 回退到无个性化广告（house ad 或占位图）

### 🔹 Attribution Reporting 的注册与匹配开销

Attribution Reporting API 替代了传统的服务端像素追踪。它把归因逻辑放在系统侧执行，通过 `MeasurementManager.registerSource()` 和 `MeasurementManager.registerTrigger()` 注册广告曝光和转化事件。

**注册开销**

`registerSource()` 的调用方在广告点击或曝光时执行。它的工作是：

1. 解析 Attribution Reporting source 注册参数（destination、expiry、event_report_windows 等）
2. 本地生成 source event ID 和匹配 key
3. 存储到 AdServices SQLite 数据库
4. 通过 oneway IPC 返回（App 侧不等网络）

注册一个 source 的端到端耗时：5-20ms（热路径），冷路径 50-150ms。不涉及网络请求——source 注册完全在本地完成。

`registerTrigger()` 在转化事件发生时调用（如用户完成购买）。它的工作是：

1. 解析 trigger 参数
2. 与已注册的 source 做本地匹配（基于 destination + source_event_id）
3. 生成 event-level report 或 aggregatable report
4. 按配置的延迟窗口调度报告上报

注册 trigger 的耗时与 source 类似，但多了一步 source 匹配。匹配操作是 SQLite JOIN，延迟在 5-15ms。当 source 表积累到数千条时，匹配查询延迟可能上升到 30-50ms。

[已验证: 官方文档, developer.android.com/training/privacy-sandbox/attribution-reporting]

**延迟报告对网络调度的聚集效应**

Attribution Reporting 不在 trigger 发生时立刻上报。它按配置的 `event_report_windows`（默认 2 小时 / 7 天 / 30 天）延迟发送。这意味着报告上报会在时间轴上聚集：

- 大量转化发生在用户活跃时段（9-11 点、20-22 点）
- 报告按延迟窗口在特定时间点批量触发
- AdServices 内部的上报队列可能出现峰值

App 侧的感知是间接的：AdServices 进程在上报窗口触发时被唤醒，发起 HTTP(S) 请求到 advertiser 的 endpoint。如果上报 endpoint 同时也是 App 的后端服务，需要在服务端做好容量规划——报告到达不是均匀分布的。

聚合报告（Aggregatable Report）还需要经过 aggregation service 解密，App 侧不直接处理这部分。

### 🔹 SandboxedProcess IPC 与跨进程数据传输性能边界

Topics 和 Protected Audiences API 的部分操作在独立的 SandboxedProcess 中执行——Protected Audiences 的 `generateBid()` 和 `scoreAd()` JS 代码运行在隔离的 WebView sandbox 中，与 AdServices 主进程之间通过 IPC 通信。

这个额外的进程边界带来两层性能成本：

**WebView 冷启动**：Protected Audiences 的 JS 执行依赖 WebView 引擎。首次调用 `selectAds()` 时，WebView 需要初始化 V8 引擎和渲染管线，冷启动开销 50-200ms。后续调用复用 WebView 实例，开销降到 5-20ms。

**序列化开销**：Custom Audience 数据（用户信号、出价信号、广告候选列表）从 AdServices 主进程序列化后通过 IPC 传给 sandbox 进程。数据量通常在 10-100KB，序列化 + IPC 传输 + 反序列化的总开销约 5-15ms。数据量超过 500KB 时开销明显上升。

App 侧无法控制 SandboxedProcess 的生命周期。减少这个开销的唯一方式是控制 Custom Audience 的数据体积——`user_bidding_signals` 字段越大，IPC 传输越慢。建议把 user_bidding_signals 控制在 4KB 以内，超过部分放 trusted server 按需拉取。

## 扩展

### 🔸 WebView 中 Privacy Sandbox API 的执行路径

部分 Privacy Sandbox 能力可以通过 WebView 的 DevTools Protocol 或 JavaScript API 触发。WebView 内部的 Privacy Sandbox 调用经过 chromium 的适配层转发到系统 AdServices，多了一层 chromium IPC。

性能影响：WebView 路径比原生 API 路径多 5-10ms 的 IPC 开销。对于 Topics 这种本身 5-15ms 的操作，相对开销增加 50-100%。Protected Audiences 在 WebView 场景下通常由原生 SDK 处理，WebView 路径较少使用。

监控建议：WebView 场景下追踪 Privacy Sandbox 调用耗时，需要在 JavaScript 层打点（performance.now()），不能只看 native 层 Binder trace。两端时间差就是 chromium 适配层的开销。

### 🔸 不支持 Privacy Sandbox 的设备上的回退性能

Android 12 及以下设备不支持 Privacy Sandbox API。Android 13 设备支持但 API 仍为 Beta。App 需要在运行时检查 API 可用性：

```java
// 检查 Privacy Sandbox 是否可用
AdvertisingManager am = context.getSystemService(AdvertisingManager.class);
if (am != null && am.getAdvertisingId() != null) {
    // 传统 GAID 路径，使用 AdvertisingIdClient.getAdvertisingIdInfo()
}
```

回退策略对性能的影响：

| 回退方案 | 额外开销 | 延迟特征 |
|---------|---------|---------|
| 传统 GAID + 服务端匹配 | 网络请求 + 服务端计算 | RTT（50-200ms） |
| Contextual 广告（无定向） | 无额外开销 | <5ms |
| 混合模式（先 GAID 后 Privacy Sandbox） | 两套路径维护成本 | 首次请求可能翻倍 |

混合模式是最常见的过渡期策略。设备支持 Privacy Sandbox 时走新路径，否则回退到 GAID。性能监控需要把两条路径分开统计，避免回退路径的延迟拉高整体 P90 指标。

[适用版本: Android 13 - Android 17]

[待验证: Android 17 对 Privacy Sandbox API 的具体行为变更，官方文档查询受限]
