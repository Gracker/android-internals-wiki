# Suggestions

[2026-06-04] 19.18 商业 APM 平台 — 补充自建方案权衡矩阵和 ROI 案例
- **章节**：`src/part3-tools/ch19-apm/18-commercial-apm.md`
- **建议**：补充商业 APM 与自建方案的权衡对比矩阵，包含成本、功能、维护性等维度
- **建议**：补充 ROI 估算的具体案例数据，包含实际节省的人力成本和故障处理效率提升数据
- **优先级**：中

[2026-06-04] 19.18 商业 APM 平台 — 补充 Android 16/17 版本差异说明
- **章节**：`src/part3-tools/ch19-apm/18-commercial-apm.md`
- **建议**：补充 Android 16/17 对商业 APM 平台的关键影响，包括 SDK 兼容性、新特性支持等
- **优先级**：高

[2026-06-04] 19.06 BlockCanary — 明确 Android 17 兼容性说明
- **章节**：`src/part3-tools/ch19-apm/06-blockcanary.md`
- **建议**：明确现代 Android 版本（Android 17）的兼容性说明，包括是否需要适配变更
- **优先级**：中

[2026-06-04] 13.2 Trace 抓取 — 补充 Android 17 新增 tracing 特性
- **章节**：`src/part3-tools/ch13-perfetto/02-trace-capture.md`
- **建议**：补充 Android 17 中新增的 tracing 相关特性，包括新的数据源、配置选项等
- **优先级**：低

[2026-06-04] 13.2 Trace 抓取 — 补充性能数据示例
- **章节**：`src/part3-tools/ch13-perfetto/02-trace-capture.md`
- **建议**：补充性能数据示例，包括不同配置下的内存占用、CPU 占用、捕获速度等
- **优先级**：低

[2026-06-04] 13.2 Trace 抓取 — 补充常见问题排查指南
- **章节**：`src/part3-tools/ch13-perfetto/02-trace-capture.md`
- **建议**：补充常见问题排查指南，包括数据丢失、配置错误、权限问题等常见问题的解决方案
- **优先级**：低

## [Task9 Deep Review] 9.7 ANR 非技术故障诊断 — 2026-06-04
- **类型**：源码准确性
- **位置**：ContentProvider timeout 表格与源码说明
- **问题**：publish timeout 常量 `CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS` 定义在 `ContentResolver`，AMS 通过 `CONTENT_PROVIDER_PUBLISH_TIMEOUT_MSG` 调度；provider call 超时由 `ContentProviderClient.setDetectNotResponding()` 触发并进入 `appNotRespondingViaProvider()`。正文把排查入口概括为 `ContentProviderHelper`，方向可用但源码锚点不够精确。
- **建议**：补充 `frameworks/base/core/java/android/content/ContentResolver.java`、`ContentProviderClient.java`、`ActivityManagerService.java` 与 `ContentProviderHelper.java` 的分工，区分 provider publish 和 provider call timeout。
