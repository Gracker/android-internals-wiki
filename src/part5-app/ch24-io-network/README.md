# 第 24 章：I/O 与网络优化

I/O 与网络优化覆盖文件读写、数据库、序列化、连接建立、数据传输和缓存。分析时应把主线程阻塞、系统调用、协议时延和失败重试分开度量。

第 6 章分析存储与 I/O 机制，第 12 章讨论系统网络性能；这里聚焦 App 侧的 API 选型、弱网策略和线上治理。

## 内容索引

- [24.1 文件 I/O 优化](01-file-io-optimization.md)
- [24.2 数据库性能优化（SQLite/Room）](02-database-optimization.md)
- [24.3 序列化性能对比与选型](03-serialization-performance.md)
- [24.4 网络架构与连接管理](04-network-architecture.md)
- [24.5 网络协议优化（HTTP/2、HTTP/3、gRPC）](05-protocol-optimization.md)
- [24.6 数据压缩与缓存策略](06-data-caching.md)
- [24.7 离线优先架构](07-offline-first.md)
- [24.8 I/O 与网络优化案例集](08-io-network-case-studies.md)
- [24.9 Wi-Fi 评分、网络选择与连接切换性能](09-wifi-connectivity-selection.md)
- [24.10 HTTPDNS 与 OkHttp Dns 执行边界](10-httpdns-okhttp-dns-boundary.md)
- [24.11 卫星与低带宽网络适配](11-satellite-low-bandwidth-network.md)
- [24.12 MediaStore 与 MediaProvider 性能治理](12-mediastore-mediaprovider-performance.md)
- [24.13 Photo Picker、媒体转码与缓存治理](13-photo-picker-transcoding-performance.md)
- [24.14 网络请求分段优化与弱网治理](14-network-request-performance-playbook.md)
- [24.15 移动网络性能优化实战：DNS、连接、传输与容灾](15-network-performance-baseline.md)
- [24.16 Android 17 流媒体网络预算与本地网络权限适配](16-android17-streaming-local-network.md)
- [24.17 Room 3.0 与 SQLiteDriver 迁移性能边界](17-room3-sqlitedriver-kmp-performance.md)
- [24.18 Android 17 ECH 与 domainEncryption 网络适配](18-android17-ech-domain-encryption.md)
- [24.18 补充：Android 17 CameraX 1.6 性能边界与实战](24.18-camerax-3.0-performance-boundary.md)
- [24.19 BluetoothSocket read 断开语义与长连接治理](19-bluetoothsocket-read-disconnect.md)
- [24.20 Android 17 NetworkStatsService 与 NetworkPolicyManagerService 移动数据 quota 限速源码路径](20-android17-network-quota-management.md)
- [24.21 SAF、DocumentFile 与 ContentResolver 文件访问性能选型与治理](21-saf-documentfile-contentresolver-performance.md)
- [24.22 Android 17 NFC 性能优化与无接触支付](22-nfc-contactless-payment-performance.md)

## 阅读建议

- 主线程 I/O 问题可从 24.1、24.2 和 24.3 开始，弱网问题可先读 24.4、24.5 和 24.14。
- 网络测试需要同时记录网络类型、信号质量、DNS、连接复用和重试次数。
- 文件访问方案应结合存储权限、数据规模、并发模式和跨进程需求选择。
