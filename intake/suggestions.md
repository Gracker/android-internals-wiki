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


## [Task2A Gap Mining] 2026-06-05 01:04 知识缺口挖掘 — 本轮未发现 ≥14 分候选

**已检查方向**：
1. source-index.json 高质量未映射素材（6 项）：面试参考(太泛)、Tare 电池统计(已有 11.8)、ltrace(工具/单一素材)、MUSCHED VIP(单一素材)、Staged Install(已有 1.23)、Compose 盲区(已有 22.20 draft)
2. DeepResearch 2026-06-02~04（14 篇）：anon_vma_lazy(内核深层/读者需求低)、agent 长期记忆(非核心性能话题)、TextureView 折叠屏(已有 18.07)、ProfilingManager(已有 14.07/19.16)、其余均已有对应章节
3. research-feeds（7 篇，2026-04）：全部已映射到现有章节
4. daily-info 最近 3 天（2026-06-02~04）：Android 17 相关内容均有对应章节
5. AOSP/官方文档：全书 26 章 406 节已覆盖 frameworks/base 核心服务、system/ 核心组件、packages/modules/ 主要模块
6. Android 17 性能行为变更（15+ 项）：Edge-to-Edge、FGS 类型、Excessive CPU Kill、后台音频硬化、Tare 经济模型、Keystore 配额、Native DCL、ECH、ML Runtime 等均已覆盖
7. Clippings 参考书交叉比对：《稳定性》15 篇全覆盖、《性能优化》20+ 篇全覆盖、《线上疑难》59 篇主题均有对应章节

**结论**：全书 406 节，258 finalized + 110 ready-for-review + 4 draft，覆盖率极高，本轮无合格缺口。

## [Task9 Deep Review] 5.3 大小核架构 — 2026-06-05
- **类型**：知识盲区
- **位置**：扩展：GPU + NPU 的协同调度概念
- **问题**：正文保留了“需补充素材”的占位段。该扩展不影响大小核、EAS、schedutil 主链路准确性，但发布前最好避免空壳扩展。
- **建议**：要么补充 GPU/NPU offloading 对 CPU 调度、uclamp/Power HAL hint 的影响；要么删除该扩展小节，把后续研究留给独立选题。


## [Task2A Gap Mining] 2026-06-05 07:07 知识加工 — 本轮未发现 ≥14 分候选

**已检查方向**（本轮增量 vs 上轮 01:04）：
1. **daily-info 2026-06-05**（22 条新素材）：
   - Linux 调度器优化导致 20% 功耗增加（传音工程师案例）→ 已映射 ch05
   - Cached Apps Freezer 官方文档 → 已映射 ch04 (4.11)
   - Android 17 App Functions / AI 原生 → 非 AIW 核心性能话题
   - Remote Compose (AndroidX) → 新特性但素材不足（1 篇），非核心性能
   - Android 17 Measure + Vitals 集成 → 已映射 ch19
   - 其余掘金文章均无新性能话题
2. **DeepResearch 2026-06-05**（2 篇新素材）：
   - BlockCanary Looper.Observer 验证 → 已映射 ch19.06
   - Trace capture linux.perf 验证 → 已映射 ch13.02
3. **source-index.json 未映射条目**：150 条，上一轮已全部筛查，本轮无新增高分候选
4. **research-feeds**：最新 5 篇（4 月），全部已映射
5. **AOSP/官方文档**：406 节已覆盖 frameworks/base 核心服务、system/ 核心组件、packages/modules/ 主要模块
6. **Clippings 参考书**：全部 3 本已映射

**评分**：所有候选缺口 < 14 分（素材丰富度不足或已有章节覆盖）。

**结论**：全书 406 节（258 finalized + 110 ready-for-review + 5 draft），覆盖率极高。本轮无合格缺口，不创建新章节。


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


## [Task2A Gap Mining] 2026-06-05 09:06 知识加工 — 本轮无操作

**Phase 0 结果**：0 个空 draft（< 15 行）。4 个现有 draft 均有 42-50 行内容。

**Phase 0.5 结果**：Task2B backlog = 0，允许进入 Phase 1。

**Phase 1 增量检查**（vs 07:07 轮）：
1. 3 篇新 DeepResearch（09:02/05:57/03:03）：均为 ch19.18/ch19.06/ch13.02 验证素材，不产生新缺口
2. 其余方向上一轮已穷举

**结论**：本轮无合格缺口（< 14 分），不创建新章节，不加工 draft。

**已检查方向汇总**（三轮 01:04/07:07/09:06 合并）：
- source-index.json：150+ 条全部筛查
- DeepResearch：20+ 篇全部映射
- research-feeds：7 篇（2026-04），全部已映射
- daily-info：2026-06-02~06-05 全覆盖
- AOSP/官方文档：406 节已覆盖核心模块
- Android 17 行为变更：15+ 项全覆盖
- Clippings 参考书：3 本全覆盖

## [Task2A 知识加工] 2026-06-05 10:04 知识加工 — 加工 4.13

**加工章节**：4.13 Linux ANON_VMA_LAZY 优化与 Android 内存性能
**素材来源**：DeepResearch/2026-06-04-anon_vma_lazy_memory_optimization.md
**锚点覆盖**：6/6 锚点 + 2/2 扩展（部分待补充）
**产出**：src/part1-fundamentals/ch04-memory/13-anon-vma-lazy-memory-optimization.md（status → ready-for-review）
**下一待写章节**：7.19 AccessibilityManagerService（draft）
