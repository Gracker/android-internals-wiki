# 知识盲区清单

## [External Review Integration] 2026-04-21

本次整合未提取到知识盲区内容。外部 review 文件主要关注一般修正建议，暂未识别需要后续研究的技术盲区。

## [2026-04-21] 14.11 Battery Historian 与功耗分析工具 — 知识盲区

### 盲区描述
external-review 已命中 Android 15+ 的代码级功耗采集能力，但正文仍停留在 Studio Power Profiler 视角，缺少 `SystemHealthManager.getSupportedPowerMonitors()` / `getPowerMonitorReadings()`、`PowerMonitor`、`PowerMonitorReadings` 这一整组 PowerMonitor API。

### 重要程度
高

### 建议研究方向
- 核对 Android 15(API 35) PowerMonitor API 的入口类、异步回调模型和设备支持条件
- 研究 PowerMonitor 结果如何与 Macrobenchmark、线上监控和离线 bugreport 分析拼成统一功耗链路
- 区分真实 power rail 与 modeled energy consumer，补清适用边界

### 关联章节
- 14.11
- 11.2
- 15.5
