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

## [Task9 Deep Review] 5.12 Thermal 管控深度：从内核子系统到 ADPF 主动降频 — 2026-06-05
- **类型**：数据缺失
- **位置**：测试方法 / 常见问题与误区
- **问题**：环境温度每升高 5°C 会让 throttling 提前 20-30%、单核高频 vs 多核中频功耗差 30%、提前 30 秒降载可延长持续性能窗口 40-60% 等数字缺少设备、SoC、环境温度、负载、测试时长和基线配置。
- **建议**：发布前补实测记录或官方案例原始条件；无法补齐时改为定性趋势，并把阈值/比例留给项目内 A/B 测试。

## [Task9 Deep Review] 5.12 Thermal 管控深度：从内核子系统到 ADPF 主动降频 — 2026-06-05
- **类型**：数据缺失
- **位置**：Thermal 问题分析的决策树
- **问题**：“thermal 事件前 30-60 秒帧时间稳定 → thermal 是唯一原因”判断过强，缺少 CPU/GPU busy、工作负载变化、调度延迟和 DVFS 状态的交叉条件。
- **建议**：改成“thermal 是主要嫌疑”，并要求同时核对 workload、freq、sched latency、GPU counter/FrameTimeline 后再归因。

## [Task9 Deep Review] 8.9 Android 游戏性能与 Game Mode/State API — 2026-06-05
- **类型**：数据缺失
- **位置**：现代 Vulkan 游戏的 GPU 瓶颈分析
- **问题**：动态渲染、PSO、render pass barrier、render target 切换等判断方向合理，但当前段落缺少 AGI/Perfetto renderstages 示例或 Vulkan 官方/Android GPU Inspector 文档锚点。
- **建议**：补一段可复现实例或引用 AGI/Perfetto 官方文档；否则把这段降级为排查假设，不写成通用结论。

