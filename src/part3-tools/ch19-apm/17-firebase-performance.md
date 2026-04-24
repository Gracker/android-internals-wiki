---
title: "Firebase Performance"
chapter: "19"
section: "19.17"
status: draft
drafted_date: "2026-04-24"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-24"
last_verified_against: "Firebase Performance Monitoring docs"
confidence: medium
tags: [apm]
related_chapters: ["19.0"]
sources:
  - type: official
    path: "https://firebase.google.com/docs/perf-mon"
pipeline_stage: drafted
---

# Firebase Performance

## Firebase Performance 是低门槛平台方案

Firebase Performance Monitoring 是 Google Firebase 体系里的移动性能监控服务。Android 侧常见能力包括 App 启动、前后台、屏幕渲染、HTTP/S 网络请求、自定义 trace 和自定义 metric。

它适合 Google 生态已经可用、希望快速拿到基础性能看板的团队。它不适合所有地区、所有合规场景，也不替代本地 Perfetto、JankStats 的自定义聚合或自建 APM 平台。

## trace 是 Firebase 的基本数据单位

Firebase 文档把 trace 定义为 App 中两个时间点之间捕获的数据报告。不同 trace 会携带不同 metric，例如网络请求 trace 会包含响应时间、payload 大小等字段。

常见 trace 类型包括：

- App start、foreground、background。
- Screen rendering。
- HTTP/S network request。
- Custom trace。

每条 trace 还会带设备、App 版本等属性，用于过滤和聚合。这个模型很适合回答“哪些版本、哪些设备、哪些网络请求变慢”。

## 自动采集和自定义采集

Firebase 的优势是自动采集能力较多。接入 SDK 后，启动、屏幕渲染和网络请求可以较快进入看板。业务侧还可以用 custom trace 标记自己的路径，比如登录、下单、图片加载、首页首屏。

自定义 trace 要注意粒度：

- 只给用户感知路径加 trace，不给普通工具函数加。
- metric 用固定名称，例如 `image_count`、`cache_hit`、`payload_kb`。
- attribute 用有限枚举，例如页面类型、渠道、接口类型。
- 不写用户 id、token、完整 URL、搜索词等敏感内容。

平台型服务越容易接入，越要控制字段。字段失控后，看板会变得难查，也可能触发隐私审查问题。

## 它和 JankStats 的关系

Firebase 可以展示 screen rendering 相关数据，但 JankStats 更适合应用内自定义 UI context。两者可以同时存在：

- Firebase 负责快速平台化展示和版本聚合。
- JankStats 负责更细的页面、状态和业务上下文。
- FrameMetrics 在高版本设备上补阶段耗时。

如果团队只用 Firebase，需要接受它的口径和平台限制。如果团队需要把慢帧数据和内部页面、实验分组、用户路径深度结合，自研或二次上报仍然少不了。

## 网络监控的边界

Firebase 的网络请求监控适合看 URL pattern、响应耗时、payload、成功失败等指标。它不等于网络全路径分析。DNS、TCP、TLS、服务端耗时、网关耗时、弱网重试、缓存命中这些细节，仍然要结合网络库埋点、服务端 trace 和日志。

线上排查时可以这样用：

- Firebase 看某个 endpoint 是否在某版本变慢。
- 网络库日志看请求阶段和错误类型。
- 服务端监控看后端处理耗时和错误率。
- Perfetto 看客户端是否被主线程、I/O 或调度拖住。

只看单端网络耗时，很容易把服务端慢、弱网、客户端排队混在一起。

## 使用建议

Firebase Performance 适合做第一版性能看板：启动、屏幕、网络和少量自定义 trace。接入时先把采样、数据区域、隐私字段和团队权限确认清楚。

如果产品面向无法稳定访问 Firebase 服务的地区，或者公司要求性能数据自托管，就要考虑 Measure、Sentry、自建平台或国内商业 APM。Firebase 的优势是省平台成本，边界是生态、合规和可定制能力。

## 自动 trace 和自定义 trace 的分工

Firebase Performance 的自动 trace 适合做基础盘，自定义 trace 适合补业务路径。两者不要互相替代。

| Trace 类型 | 典型用途 | 边界 |
|---|---|---|
| App start | 冷启动、热启动趋势 | 不能代表首屏数据完整 |
| Screen rendering | 页面渲染基础指标 | UI 状态和业务动作有限 |
| HTTP/S request | 网络耗时和 payload | URL 聚合和服务端阶段要补充 |
| Custom trace | 登录、下单、首屏、图片加载 | 需要业务稳定命名和采样控制 |

如果只依赖自动 trace，平台能看到“启动慢”“网络慢”，但很难回答业务路径。自定义 trace 的作用就是把内部关键路径暴露给平台。

## 自定义 trace 示例

下面示意代码展示业务路径 trace。重点是 trace 名称稳定，metric 和 attribute 都使用低基数字段。

```kotlin
val trace = Firebase.performance.newTrace("home_first_feed")
trace.putAttribute("entry", "cold_start")
trace.start()

try {
    val response = api.loadFirstFeed()
    trace.putMetric("item_count", response.items.size.toLong())
    trace.putMetric("payload_kb", response.rawSizeBytes / 1024)
    render(response.items)
} finally {
    trace.stop()
}
```

不要把用户 id、完整请求 URL、搜索词、商品 id 放进 attribute。Firebase attribute 用于过滤和聚合，字段一旦高基数，查询和隐私都会出问题。

## 网络请求聚合要做 URL pattern

网络监控最容易被 URL 动态参数污染。比如：

```text
/api/item/10001/detail
/api/item/10002/detail
/api/item/10003/detail
```

如果按完整 URL 上报，平台会认为这是三个接口。正确做法是归一化为：

```text
/api/item/{id}/detail
```

还要确认 query 参数策略。分页、实验参数、token、签名、搜索词都不适合直接进入聚合维度。网络 trace 只保留 endpoint pattern、method、status、payload 和阶段耗时即可。

## 采样和阈值策略

Firebase 上手快，但生产环境仍然要控制数据量：

- 自定义 trace 只覆盖关键路径。
- 低价值 trace 不上报或只在 Debug 验证。
- 网络请求按 endpoint 聚合，不记录完整 URL。
- 通过 Remote Config 或自己的开关控制业务 trace。
- 版本灰度期间提高采样，稳定后降低采样。

Firebase 控制台展示的是聚合结果。若团队还要保留单点现场，需要把 Firebase 数据和内部日志、Crash、Perfetto 样本关联起来。

## 和 Google Play Console 的配合

Firebase Performance 和 Android Vitals 都来自 Google 生态，但定位不同：

- Android Vitals 来自 Play 分发面，更适合看真实用户质量门槛。
- Firebase Performance 来自 App SDK，更适合看自定义 trace、网络和版本维度。

如果两边都显示启动或渲染变差，优先级很高。如果 Firebase 变差但 Vitals 没变，可能是采样用户、渠道或自定义 trace 口径差异。如果 Vitals 变差但 Firebase 没变，可能是 SDK 覆盖不足或字段聚合掩盖了问题。

## 适合与不适合

Firebase Performance 适合：

- 快速搭建第一版性能看板。
- 面向 Google Play 和海外用户的产品。
- 需要 App start、screen、network、自定义 trace 的基础聚合。

它不适合：

- 必须完全自托管性能数据的团队。
- 需要深度方法 trace、Hprof、ANR 线程文件、native 内存分析的场景。
- 无法稳定访问 Firebase 服务的发行区域。

书稿里要把这个边界写清。Firebase 是好入口，但不是性能诊断的终点。
