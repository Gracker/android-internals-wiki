# AIW 最近新增章节清理报告

- 时间：2026-07-19T09:14:01
- 删除章节/重复文件：20
- SUMMARY 删除目录项：15

## 删除清单

- `src/part5-app/ch22-rendering-practice/44-compose-state-subscription-recomposition-control.md`：Compose 微观状态订阅主题，适合合并进 22.39/22.20，不应单独成章
- `src/part5-app/ch22-rendering-practice/45-compose-lazygrid-performance.md`：LazyGrid 是 LazyList/LazyGrid 章节的子话题，重复 22.22，单独成章过细
- `src/part5-app/ch22-rendering-practice/46-compose-textfield-ime-performance.md`：TextField+IME 是输入/Compose 交叉子话题，重复 3.11/22.20/22.41，过细
- `src/part5-app/ch22-rendering-practice/47-compose-nested-scroll-gesture-performance.md`：NestedScroll 手势子话题，重复输入/Compose 滑动章节，过细
- `src/part5-app/ch25-power-size/32-plugin-dynamic-loading-size-optimization.md`：插件化包体积优化偏历史方案，现代主线应并入 App Bundle/Dynamic Feature/包体积优化，不宜单章
- `src/part5-app/ch24-io-network/22-okhttp-cronet-ktor-engine-comparison.md`：网络引擎选型偏产品/框架对比，重复网络性能基础与 HTTPDNS/连接池章节
- `src/part5-app/ch20-stability/29-crash-sdk-architecture-tombstone-parsing.md`：Crash SDK 选型重复 Native crash/tombstone/symbolication/线上崩溃治理章节
- `src/part2-performance/ch09-anr/9.1-anr-detection-monitoring-alerting.md`：9.1 重号且内容是 800 字级目录桩，已有 ANR 机制/监控章节覆盖
- `src/part5-app/ch20-stability/20.1-app-stability-monitoring-practices.md`：20.1 重号/总论桩，已有稳定性章节体系覆盖
- `src/part5-app/ch21-startup/21.1-cold-start-optimization-strategy.md`：21.1 重号/总论桩，已有启动优化章节覆盖
- `src/part5-app/ch22-rendering-practice/22.1-ui-rendering-performance-optimization.md`：22.1 重号/总论桩，已有 Compose/UI 渲染主章节覆盖
- `src/part5-app/ch23-memory-practice/23.1-memory-management-strategy-oom-defense.md`：23.1 重号/总论桩，已有内存管理/OOM 章节覆盖
- `src/part2-performance/ch08-responsiveness/19-touch-latency-optimization-practice.md`：8.19 重号，且输入延迟已有 InputDispatcher/端到端输入延迟章节承载
- `src/part5-app/ch22-rendering-practice/46-compose-textfield-ime-performance 2.md`：iCloud/重复文件副本（文件名带 2），与同名章节重复
- `src/part5-app/ch22-rendering-practice/47-compose-nested-scroll-gesture-performance 2.md`：iCloud/重复文件副本（文件名带 2），与同名章节重复
- `src/part5-app/ch25-power-size/32-plugin-dynamic-loading-size-optimization 2.md`：iCloud/重复文件副本（文件名带 2），与同名章节重复

## SUMMARY 删除目录项

- `- [8.19 端到端触控延迟优化实战：从输入事件到帧上屏的全链路剖析](src/part2-performance/ch08-responsiveness/19-touch-latency-optimization-practice.md)`
- `- [9.1 ANR 检测机制与监控告警](src/part2-performance/ch09-anr/9.1-anr-detection-monitoring-alerting.md)`
- `- [9.1 ANR 检测机制与监控告警](part2-performance/ch09-anr/9.1-anr-detection-monitoring-alerting.md)`
- `- [23.1 内存管理策略与 OOM 防护](part5-app/ch23-memory-practice/23.1-memory-management-strategy-oom-defense.md)`
- `- [21.1 启动优化策略与冷启动链路](part5-app/ch21-startup/21.1-cold-start-optimization-strategy.md)`
- `- [22.44 Compose 状态订阅与重组控制实战](part5-app/ch22-rendering-practice/44-compose-state-subscription-recomposition-control.md)`
- `- [22.45 Compose LazyGrid 性能优化实战](part5-app/ch22-rendering-practice/45-compose-lazygrid-performance.md)`
- `- [22.46 Compose TextField 文本输入与 IME 动画性能实战](part5-app/ch22-rendering-practice/46-compose-textfield-ime-performance.md)`
- `- [22.47 Compose 手势与 NestedScrollConnection 性能实战](part5-app/ch22-rendering-practice/47-compose-nested-scroll-gesture-performance.md)`
- `- [22.1 UI 渲染性能优化与 Compose 渲染管线](part5-app/ch22-rendering-practice/22.1-ui-rendering-performance-optimization.md)`
- `- [20.1 应用稳定性监控与异常处理](part5-app/ch20-stability/20.1-app-stability-monitoring-practices.md)`
- `- [20.29 Crash 报告 SDK 架构选型与 tombstone 解析实战](part5-app/ch20-stability/29-crash-sdk-architecture-tombstone-parsing.md)`
- `- [25.32 插件化包体积优化 — 历史演进与现代替代方案](part5-app/ch25-power-size/32-plugin-dynamic-loading-size-optimization.md)`


## 追加删除清单

- `src/part5-app/ch26-observability/30-performance-regression-governance-ci-gate.md`：偏工程流程/CI 门禁方法论，适合并入观测性或方法论章节，不宜单独成章
- `src/part5-app/ch26-observability/31-high-performance-logging-system-practice.md`：应用日志体系偏通用工程实践，重复线上诊断/日志诊断章节，不宜单独成章
- `src/part5-app/ch27-2-thread-pool-cpu-utilization.md`：路径结构异常（part5-app 根目录 ch27-*），第 27 章规划不存在；线程池优化应并入启动/稳定性/调度章节
- `src/part5-app/ch27-3-task-scheduling-priority-affinity.md`：路径结构异常（part5-app 根目录 ch27-*），第 27 章规划不存在；CPU 亲和性/优先级应并入调度章节

## 追加 SUMMARY 删除目录项

- `- [26.30 性能防劣化体系与 CI 门禁实战](part5-app/ch26-observability/30-performance-regression-governance-ci-gate.md)`
- `- [26.31 应用日志系统性能优化与高效日志体系实战](part5-app/ch26-observability/31-high-performance-logging-system-practice.md)`

## 仍建议后续人工判断

- 其余 2026-07-16/17 的 1.5k-2k 字 draft 章节暂不自动删除：多数虽偏细，但仍可作为既有章节素材；后续应优先“合并进已有章”，而不是继续扩目录。
