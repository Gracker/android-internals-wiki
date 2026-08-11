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
- [24.8 Wi-Fi 评分、网络选择与连接切换性能](08-wifi-connectivity-selection.md)
- [24.9 HTTPDNS 与 OkHttp Dns 执行边界](09-httpdns-okhttp-dns-boundary.md)
- [24.10 卫星与低带宽网络适配](10-satellite-low-bandwidth-network.md)
- [24.11 MediaStore 与 MediaProvider 性能治理](11-mediastore-mediaprovider-performance.md)
- [24.12 Photo Picker、媒体转码与缓存治理](12-photo-picker-transcoding-performance.md)
- [24.13 移动网络性能优化实战：DNS、连接、传输与容灾](13-network-performance-baseline.md)
- [24.14 Android 17 流媒体网络预算与本地网络权限适配](14-android17-streaming-local-network.md)
- [24.15 Android 17 ECH 与 domainEncryption 网络适配](15-android17-ech-domain-encryption.md)
- [24.16 BluetoothSocket read 断开语义与长连接治理](16-bluetoothsocket-read-disconnect.md)
- [24.17 Android 17 移动数据 quota 限速源码路径](17-android17-network-quota-management.md)
- [24.18 SAF、DocumentFile 与 ContentResolver 文件访问性能选型与治理](18-saf-documentfile-contentresolver-performance.md)
- [24.19 Android 17 NFC 性能优化与无接触支付](19-nfc-contactless-payment-performance.md)

## 阅读建议

- 主线程 I/O 问题可从 24.1、24.2 和 24.3 开始，弱网问题可先读 24.4、24.5 和 24.13。
- 网络测试需要同时记录网络类型、信号质量、DNS、连接复用和重试次数。
- 文件访问方案应结合存储权限、数据规模、并发模式和跨进程需求选择。
- 原案例集中的 SharedPreferences ANR 已并入 24.1，Room 3 已并入 24.2，网络分段治理与大文件传输已并入 24.4；CameraX 归入 [22.31](../ch22-rendering-practice/31-camerax-performance.md)。
