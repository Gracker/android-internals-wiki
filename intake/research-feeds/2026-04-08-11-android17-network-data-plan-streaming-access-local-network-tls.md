---
tags:
  - android
  - research
  - network
---
## [研究] Android 17 网络性能相关 API 变更：Data Plan Streaming、本地网络权限与 TLS 增强
- **来源**：https://developer.android.com/about/versions/17 / https://developer.android.com/reference/android/net/NetworkStatsManager
- **作者/机构**：Google Android Team
- **日期**：2026-03-05 (Android 17 Beta 3)
- **四维评分**：相关性 4/5 · 技术深度 3/5 · 时效性 5/5 · 可验证性 4/5 · **总分 16/20**
- **映射章节**：§12.2 网络性能优化 · §12.3 网络性能深入 · §16.5 Android 17 性能行为变更
- **映射锚点**：网络请求优化策略、TLS 连接性能、Radio State Machine、版本演进
- **摘要**：Android 17 (API 37) 引入多项网络性能相关变更：Data Plan Streaming API 允许 App 查询运营商分配的流媒体速率上限，ACCESS_LOCAL_NETWORK 权限新增对本地网络访问的显式管控，OpenJDK 21/25 集成增强 TLS 命名组支持提升安全通信性能，DeliQueue 无锁 MessageQueue 减少网络回调导致的 UI jank。

### 关键发现
1. **Data Plan Streaming API**：`NetworkStatsManager.getStreamingAppMaxDownlinkKbps()` 和 `getStreamingAppMaxUplinkKbps()` 是 Android 17 新增 API，允许 App 查询运营商为流媒体应用分配的上下行速率上限。App 可据此自适应调整视频/音频流质量，避免在受限网络下请求过高码率导致卡顿或超额流量消耗。这为网络自适应优化提供了系统级数据支撑。
2. **ACCESS_LOCAL_NETWORK 权限**：Android 17 引入新的普通权限 `android.permission.ACCESS_LOCAL_NETWORK`，要求 App 显式声明才能访问本地网络（如 mDNS 发现、局域网设备通信）。此前无需任何权限即可访问本地网络。这一变更影响所有通过 Wi-Fi 进行局域网通信的 App（如投屏、IoT 控制、本地服务器），需在 manifest 中声明并处理权限拒绝场景。
3. **OpenJDK 21 & 25 TLS 增强**：Android 17 集成 OpenJDK 21 和 25 的安全更新，包括 TLS 命名组（named groups）扩展支持，支持更多现代加密曲线（如 X25519MLKEM768 等后量子密码学混合密钥交换）。这不仅提升安全性，也通过减少 TLS 握手往返次数间接改善连接建立性能。
4. **DeliQueue 对网络回调的影响**：Android 17 的无锁 MessageQueue 实现（API 37 target 时生效）直接影响网络回调在主线程的投递效率。网络请求的 onResponse/onFailure 回调通过 MessageQueue 投递到主线程，减少锁等待意味着网络结果能更快地驱动 UI 更新，减少「网络完成但 UI 未及时刷新」的感知延迟。

### 可直接引用段落
> Android 17 introduces new APIs in NetworkStatsManager that allow apps to query carrier-allocated maximum streaming rates: getStreamingAppMaxDownlinkKbps() and getStreamingAppMaxUplinkKbps(). These APIs enable apps to make informed decisions about streaming quality, adjusting bitrate based on actual carrier-imposed rate limits rather than estimating from observed throughput. This is particularly relevant for video streaming apps that need to balance quality against data plan constraints.
> — source: developer.android.com/about/versions/17

> The new ACCESS_LOCAL_NETWORK permission requires explicit opt-in for apps that communicate with devices on the local network. This includes mDNS service discovery, local HTTP servers, and peer-to-peer connections. Apps targeting API 37 that access local network resources without this permission will receive SecurityException.
> — source: developer.android.com/about/versions/17/behavior-changes-17

### 与 queue.json 联动
- 优先级调整建议：无（§12.2/§12.3 已完成，§16.5 已有 pending 条目）
- 素材路径建议：可补充到 §16.5 的 material_paths，作为 Android 17 网络性能变更的素材支撑
- FRESHNESS 联动：§12.2 (02-network-performance) 需要补充 Android 17 Data Plan API + ACCESS_LOCAL_NETWORK 权限的版本演进内容
