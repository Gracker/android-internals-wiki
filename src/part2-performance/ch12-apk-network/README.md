# 第 12 章：网络性能

本章关注请求从应用代码进入 Android 网络栈后的端到端成本：请求排队、DNS（Domain Name System，域名系统）解析、连接复用、传输协议、TLS（Transport Layer Security，传输层安全）握手，以及 `netd`（Android 网络管理守护进程）和每个网络各自的 DNS 状态。系统如何选择网络，以及 `NetworkCallback` 回调的语义，另见 1.25。

排查时先按阶段分析一次请求，再根据证据进入 TLS 或 DNS 专项。Wi-Fi 图标、系统网络验证、DNS 可用性和目标服务可达性分别代表不同状态，不能合并成一个“网络正常”或“网络异常”的结论。

## 章节地图

- [12.1 Android 网络与 TLS 性能优化](01-android-network-tls-performance.md)
- [12.2 netd 与 DnsResolver：DNS 解析性能和故障诊断](02-netd-dnsresolver-network-diagnostics.md)

## 阅读路径

### 应用网络性能排查

先读 12.1，建立请求阶段模型并确认连接是否复用，再处理 TLS 握手、证书链和信任配置；若问题集中在解析、Private DNS 或特定网络，继续阅读 12.2。

### 系统网络栈排查

先读 1.25，确定 `NetworkRequest`、`NetworkCallback`、网络排序、rematch（重新匹配网络请求）和 linger（旧网络短暂保留期）的语义，再用 12.2 检查 `netd` 路由与每网络 DNS 状态。Wi-Fi、蜂窝、卫星或 VPN 切换时的业务恢复策略继续参阅第 24 章。

## 版本边界

正文统一以 Android 17 / API 37 / AOSP `android-17.0.0_r1` 为当前平台锚点。涉及 HTTP 客户端、TLS provider（安全协议实现提供方）和协议实现时，以各文章记录的依赖版本与来源为准。版本演进段落用于解释旧设备行为，不能用旧版整数网络分数或已经退出主路径的 API 推导 Android 17 的系统行为。
