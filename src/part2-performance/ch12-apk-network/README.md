# 第 12 章：包体积与网络性能

内容覆盖两类直接影响用户等待时间的问题：安装包交付成本，以及请求从应用代码到 Android 网络栈的端到端开销。

前半部分关注 APK/AAB、HTTP、连接池和 TLS；后半部分进入 `ConnectivityService`、`netd`、DNS Resolver、`NetworkAgent` 与 Android 17 的网络选择策略。分析时要区分应用侧慢请求、系统侧网络状态变化和连接迁移，并为每一类问题采集对应证据。

## 章节地图

| 章节 | 主题 | 解决的问题 |
|---|---|---|
| [12.1 APK 体积优化](01-apk-size.md) | APK/AAB 结构、R8、资源与 native library | 包为什么变大，如何按组成部分测量和压缩 |
| [12.2 网络性能优化](02-network-performance.md) | DNS、连接、协议、请求调度 | 一次请求的时间花在哪里 |
| [12.3 网络性能深入](03-network-performance-deep.md) | 连接池、TLS、HTTP/2、HTTP/3 | 如何减少握手、排队和重复建连 |
| [12.4 网络安全与 TLS 性能](04-network-security-tls-performance.md) | TLS 配置、证书、Network Security Config | 如何在安全边界内分析握手与信任失败 |
| [12.5 ConnectivityService 与网络状态监听](05-connectivity-service-network-callback.md) | `NetworkCallback`、capabilities、请求配额 | 应用收到的网络回调代表什么 |
| [12.6 netd 与 DNS Resolver](06-netd-dnsresolver-network-diagnostics.md) | per-network DNS、Private DNS、netd | DNS 失败应在哪一层取证 |
| [12.7 Privacy Sandbox on Android 退场](07-privacy-sandbox-performance.md) | Android 17 API 状态与迁移 | 旧 Privacy Sandbox 集成在 Android 17 如何处理 |
| [12.8 NetworkAgent 与 FullScore](08-networkagent-lifecycle-scoring.md) | agent 生命周期、网络排序、rematch、linger | 系统怎样为请求选择并替换网络 |

## 阅读路径

### 应用性能排查

按 12.2 → 12.3 → 12.4 阅读。先建立请求阶段模型，再检查连接复用和传输协议，随后处理 TLS 安全配置。若现象伴随 Wi-Fi/蜂窝切换或 VPN，继续阅读 12.5 和 12.8。

### 系统网络栈排查

按 12.5 → 12.8 → 12.6 阅读。先确定应用回调和 request 的语义，再还原 `NetworkRanker` 的选择与 linger，随后核对 netd 路由和每网络 DNS 状态。

### 包体积治理

12.1 是包体积主题的独立入口。分析对象应明确区分 APK、App Bundle、设备生成 APK 和安装后占用，避免把不同口径的数字放在一起比较。

## 版本边界

正文统一以 Android 17 / API 37 / AOSP `android-17.0.0_r1` 为当前平台锚点。涉及 HTTP 客户端、TLS provider 和 Play 服务组件时，以各文章记录的依赖版本与来源为准。版本演进段落用于解释旧设备行为，不应用旧整数网络分数或已退场 API 推导 Android 17 的系统行为。
