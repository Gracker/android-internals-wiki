---
title: "网络 APM 底层捕获原理"
chapter: "19"
section: "19.23"
status: ready-for-review
drafted_date: "2026-04-24"
drafted_by: "gemini"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-24"
confidence: high
tags: [apm, network, okhttp, asm]
related_chapters: ["19.0", "19.08", "19.17"]
pipeline_stage: task6_pending
---

# 网络 APM 底层捕获原理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 说明商业与开源 APM 是如何“无侵入”地拿到网络数据的，揭秘背后的黑魔法，而不仅仅是停留在看板展示。
- 🔹 [OkHttp 捕获] 深度拆解 `EventListener` 与 `Interceptor` 在网络 APM 中的组合使用；说明为何只用 Interceptor 拿不到 DNS 和 TCP 耗时。
- 🔹 [字节码插桩] 解释如何通过 ASM 或 Transform 无侵入地 Hook `HttpURLConnection` 和三方 SDK 内部封装的网络请求。
- 🔹 [Native 网络捕获] 探讨对于基于 C/C++ 的底层网络库（如 Cronet、微信 Mars），APM 如何通过 PLT Hook 或 eBPF 获取流量与耗时。
- 🔹 [指标拆解模型] 将一次网络请求拆解为 DNS、TCP 握手、TLS 握手、Request 发送、Server Wait (TTFB)、Response 接收。
- 🔹 [弱网与重试识别] 说明 APM 如何在底层识别因弱网导致的多次建连重试，避免将重试耗时算入单次请求 Server 耗时。
- 🔹 [隐私与安全] 规定端侧在捕获时如何进行 URL Pattern 聚类、Query 参数剥离、Body 截断以及 Header 过滤。

### 扩展（可选深入）

- 🔸 提供一段完整的 `OkHttp EventListener` 埋点核心代码。
- 🔸 增加一段 ASM Hook `openConnection` 的伪代码或指令说明。
- 🔸 解析 HTTP/3 (QUIC) 对现有网络 APM 捕获机制带来的挑战与应对思路。

### 流水线加工要求

- 必须从架构师的视角解释“如何造轮子”，而不仅是“如何用轮子”。
- 所有网络指标拆解必须符合真实的网络协议栈阶段。
- 强调插桩与拦截器引入的性能开销及防劣化方案。

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
<!-- outline-end -->
