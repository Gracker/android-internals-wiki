# 第 12 章：网络性能

本章讲一次请求从应用代码进入 Android 网络栈之后的端到端成本，按处理阶段看依次是请求排队、DNS（Domain Name System，域名系统）解析、连接复用、传输协议和 TLS（Transport Layer Security，传输层安全）握手。`netd`（Android 网络管理守护进程）和每个网络各自的 DNS 状态是另一类观察对象。系统的网络选择和 `NetworkCallback` 回调的语义另见 1.22。

排查时先按阶段分析一次请求，再根据证据进入 TLS 或 DNS 专项。Wi-Fi 图标、系统网络验证、DNS 可用性和目标服务可达性分别代表不同状态，不能合并成一个“网络正常”或“网络异常”的结论。

<!-- gracker-diagram: ch12-index-01-request-stage-map -->
![请求阶段、复用与业务内容可用](../../assets/diagrams/ch12/ch12-index-01-request-stage-map.png)

图：先看请求实际经历的阶段，再区分系统状态与业务端点可用性。 箭头表示依赖，非固定串行时长；连接复用与缓存可跳过新建阶段，流式处理可交叠，示意不声称性能收益。

## 章节地图

- [12.1 Android 网络与 TLS 性能优化](01-android-network-tls-performance.md)
- [12.2 netd 与 DnsResolver：DNS 解析性能和故障诊断](02-netd-dnsresolver-network-diagnostics.md)

## 阅读路径

### 应用网络性能排查

先读 12.1，建立请求阶段模型并确认连接是否复用，再处理 TLS 握手、证书链和信任配置；若问题集中在解析、Private DNS 或特定网络，继续阅读 12.2。

### 系统网络栈排查

先读 1.22，确定 `NetworkRequest`、`NetworkCallback`、网络排序、rematch（重新匹配网络请求）和 linger（旧网络短暂保留期）的语义，再用 12.2 检查 `netd` 路由与每网络 DNS 状态。Wi-Fi、蜂窝、卫星或 VPN 切换时的业务恢复策略继续参阅第 24 章。

<!-- gracker-diagram: ch12-index-02-chapter-reading-map -->
![按应用阶段与系统网络问题选择专项](../../assets/diagrams/ch12/ch12-index-02-chapter-reading-map.png)

图：应用请求先在12.1分段，系统选择先读1.22，再按证据进入DNS或恢复专项。 阅读分支不是故障根因断言；DNS、TLS与系统Network可能共同影响同一请求。

## 版本边界

正文统一以 Android 17 / API 37 / AOSP `android-17.0.0_r1` 为当前平台锚点。涉及 HTTP 客户端、TLS provider（安全协议实现提供方）和协议实现时，以各文章记录的依赖版本与来源为准。版本演进段落用于解释旧设备行为，不能用旧版整数网络分数或已经退出主路径的 API 推导 Android 17 的系统行为。

<!-- gracker-diagram: ch12-index-03-network-version-boundaries -->
![系统、模块与实际连接的版本边界](../../assets/diagrams/ch12/ch12-index-03-network-version-boundaries.png)

图：把系统与target、网络库和模块、DNS与服务端一起纳入证据。 固定r1用于源码核验，不能概括所有更新设备；ECH默认与组合查询线程差异见各专项，不凭版本号推断启用与成功。
