---
title: "卫星与低带宽网络适配"
chapter: "24.11"
section: "24.11"
status: draft
applicable_versions: "Android 16 QPR2 - Android 17 (API 37); 低带宽/高时延网络场景"
tags: [network, satellite, low-bandwidth, connectivity, reliability]
related_chapters: ["12.2", "12.5", "12.6", "24.4", "24.5", "24.7", "24.10", "26.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-20"
gap_source: "官方文档/每日信息/章节深挖"
gap_score: 15
sources:
  - type: official
    path: "https://developer.android.com/about/versions/17/features"
  - type: official
    path: "https://developer.android.com/about/versions/17/release-notes"
  - type: carrier
    path: "https://www.t-mobile.com/support/coverage/satellite-support"
  - type: local
    path: "intake/daily-info/2026-05-20.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
---

# 24.11 卫星与低带宽网络适配

<!-- outline-start -->
## 要点

### 🔹 场景边界与版本口径
区分普通弱网、蜂窝网络拥塞、漫游、卫星直连和运营商白名单应用场景。加工时先复核 Android 17 features / release notes 对低带宽卫星网络的公开描述，以及 Android 16 QPR2 是否已有相关能力；无法确认的版本口径标注 `[待验证]`。

### 🔹 网络能力识别与降级开关
整理 `ConnectivityManager` / `NetworkCapabilities` 可公开读取的网络能力、上下行带宽、计费状态、漫游状态和传输类型边界。重点说明哪些字段能支撑 App 降级，哪些字段不能直接等同于“卫星网络”。

### 🔹 请求调度、超时与重试退避
建立低带宽/高时延下的请求优先级：登录态、消息确认、配置拉取、图片/视频、批量同步分别如何限流。覆盖连接超时、读写超时、指数退避、幂等键、请求合并和失败隔离，避免弱网下重试风暴。

### 🔹 数据压缩、缓存与离线优先
围绕 24.6 / 24.7 的缓存与离线优先策略，补充低带宽网络下的字段裁剪、分页大小、增量同步、图片规格降级、预取禁用、写入队列和最终一致性处理。

### 🔹 协议与传输选型
对照 HTTP/2、HTTP/3、gRPC、WebSocket、长轮询和短连接在高 RTT / 低吞吐场景下的行为差异。加工时只写有公开文档或可验证实验支撑的结论，避免泛化“某协议一定更快”。

### 🔹 可观测性与灰度门禁
定义线上指标：网络类型、RTT、DNS 耗时、TLS 耗时、TTFB、下载字节数、重试次数、超时率、缓存命中率、离线队列积压长度、关键路径成功率。说明如何与 26.3 性能指标采集和 26.7 发版质量门禁连接。

## 扩展

### 🔸 运营商卫星服务白名单与 App 适配边界
记录运营商文档中“低带宽优化应用”的适配要求，但不把单一运营商策略写成 Android 平台通用能力。

### 🔸 多设备形态与紧急通信场景
补充手机、平板、车载、可穿戴在低带宽网络下的交互差异，重点关注关键消息、地图、定位和离线内容。

### 🔸 与 HTTPDNS / OkHttp Dns 的关系
本节处理弱网策略；24.10 继续负责 DNS 执行边界。加工时只引用结论，不重复展开 HTTPDNS 实现。

<!-- outline-end -->

> 本节内容待加工。
