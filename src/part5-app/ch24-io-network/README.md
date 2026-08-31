# 第 24 章：I/O 与网络优化

I/O（Input/Output，输入/输出）指应用与文件、数据库、设备或网络之间的数据交换。本章覆盖文件读写、数据库、序列化、连接建立、数据传输和缓存。分析时应分别度量主线程阻塞、系统调用（应用请求内核执行文件或网络操作的接口）、协议往返时延和失败重试，避免把不同原因都归为“接口慢”。

[第 6 章：存储性能](../../part1-fundamentals/ch06-storage/README.md)分析存储与 I/O 机制，[第 12 章：网络性能](../../part2-performance/ch12-apk-network/README.md)讨论系统网络性能；本章聚焦应用侧的 API 选型、弱网策略和线上治理。弱网包括高延迟、丢包、带宽不足和频繁断连；线上治理指发布后的指标监控、问题归因、降级与恢复。

## 内容索引


- [24.1 文件 I/O、SAF 与 ContentResolver 性能](01-file-io-saf-contentresolver.md)
- [24.2 数据库与序列化性能](02-database-serialization-performance.md)
- [24.3 数据缓存与离线优先架构](03-data-cache-offline-first.md)
- [24.4 MediaStore、Photo Picker 与媒体转码](04-mediastore-photo-picker-transcoding.md)
- [24.5 移动网络架构、连接与容灾](05-mobile-network-connection-resilience.md)
- [24.6 HTTP/2、HTTP/3、gRPC 与 ECH](06-http2-http3-grpc-ech.md)
- [24.7 HTTPDNS 与 OkHttp Dns 的执行边界](07-httpdns-okhttp-dns-boundary.md)
- [24.8 Wi-Fi 评分、网络选择与连接切换性能](08-wifi-connectivity-selection.md)
- [24.9 低带宽、流媒体与本地网络适配](09-low-bandwidth-streaming-local-network.md)
- [24.10 Android 17 移动数据配额与 Data Saver 执行链路](10-android17-network-quota-management.md)
- [24.11 BluetoothSocket read() 断开语义与长连接治理](11-bluetoothsocket-read-disconnect.md)
- [24.12 Android 17 NFC 性能：标签读取、HCE 与无接触支付](12-nfc-contactless-payment-performance.md)

## 术语提示

- HTTPDNS 是通过 HTTP 服务取得 DNS（Domain Name System，域名系统）解析结果的应用方案。
- ECH（Encrypted Client Hello）用于加密 `ClientHello` 中的敏感字段；`ClientHello` 是客户端发出的第一条 TLS 握手消息，`domainEncryption` 是按域名表达 ECH 策略的 Android 配置项。
- 24.10 中的 quota 表示剩余字节额度，该篇不讨论带宽整形。
- SAF（Storage Access Framework，存储访问框架）让应用通过 `content://` URI 访问用户授权的文档。
- NFC（Near Field Communication）指近场通信。

## 阅读建议

- 主线程 I/O 问题可从 24.1 和 24.2 开始；弱网问题可先读 24.5、24.6 和 24.3。
- 网络测试需要同时记录网络类型、信号质量、DNS、连接复用和重试次数。
- 文件访问方案应结合存储权限、数据规模、并发模式和跨进程需求选择。
- Wi-Fi 选择与切换见 24.8，卫星和低带宽网络见 24.9，BluetoothSocket 长连接见 24.11，无接触支付见 24.12。
- SharedPreferences 引发的 ANR（Application Not Responding，应用无响应）见 24.1，Room 3 见 24.2，网络分阶段监测与大文件传输见 24.5；CameraX 的采集与渲染见 [22.18](../ch22-rendering-practice/18-camerax-rendering.md)。
