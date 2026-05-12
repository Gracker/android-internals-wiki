# AIW 自动 Review 任务报告

## 一、目标发现结果
- 扫描范围：`src/part3-tools/ch13-perfetto/`
- 候选章节：
  1. 01-perfetto-intro.md | 基础介绍章节，需要把关基本概念
- 最终选择：`01-perfetto-intro.md`
- 选择理由：系统化地从第一节开始逐步深入。
- 排除的高频原因：暂无。

## 二、总体结论
- 总体技术评分：3.5/5
- 是否建议回炉：是
- 主要风险：存在源码路径的事实错误（P0），以及 Perfetto 核心架构组件介绍遗漏（P1）。
- 评分理由：包含 1 个 P0（源码路径错误）和 1 个 P1（核心 Daemon 遗漏）。基础概念介绍较为清晰，但涉及 AOSP 源码的具体位置不准确。
- 闭环建议：建议根据问题单修正源码路径，并补充缺失的架构组件说明。
- 本轮 review 覆盖范围：全文核心概念、架构图解、源码路径、SQL 示例、版本演进。
- 本轮未完成部分：无。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 2/5 | 1 |
| 原理链完整性 | 3.5/5 | 1 |
| 版本差异覆盖 | 4.5/5 | 0 |
| 知识盲区 | 4/5 | 0 |
| 数据/案例支撑 | 3.5/5 | 1 |
| 交叉引用一致性 | 4/5 | 0 |

## 四、P0 问题（事实错误）
- [P0][源码准确性][参考资料]
- **原文问题**：列出的 AOSP `traced` 和 `traced_probes` 服务源码路径为 `system/tracing/traced/` 和 `system/tracing/traced_probes/`。
- **源码 / 一手资料锚点**：AOSP `external/perfetto/` 目录。
- **关键代码逻辑**：Perfetto 作为一个跨平台项目，在 AOSP 中位于 `external/perfetto/`。核心服务代码位于 `external/perfetto/src/traced/` 下的 `service/` 和 `probes/`。
- **运行原理说明**：无特定运行原理影响，但路径指向完全错误，会导致开发者无法在 AOSP 中找到源码。
- **核验结论**：AOSP 根本不存在 `system/tracing/` 这个目录（存在 `system/core/` 等，但不存放 perfetto 源码）。
- **为什么错**：凭空捏造了符合直觉但实际上不存在的 AOSP 目录结构。
- **建议修正方向**：将路径修正为 `external/perfetto/src/traced/service/` 和 `external/perfetto/src/traced/probes/`。

## 五、P1 问题（重要缺失）
- [P1][原理链完整性][Perfetto 的架构]
- **原文问题**：在介绍架构时，只介绍了 `traced` 和 `traced_probes`。
- **源码 / 一手资料锚点**：Perfetto 官方文档架构图 (https://perfetto.dev/docs/concepts/service-model)。
- **缺失内容**：除了 `traced_probes`，Perfetto 架构中另外两个极为关键的提权/专门守护进程是 `heapprofd`（用于 Native 内存分配追踪）和 `traced_perf`（Android 11+ 引入，用于基于内核 perf_event_open 的 CPU 采样分析）。
- **运行原理说明**：`heapprofd` 负责通过 hook malloc/free 来采集内存分配栈；`traced_perf` 负责读取 Linux perf 子系统的调用栈。它们都是独立于 `traced_probes` 的关键组件。
- **为什么这是重要缺失**：在后续讲解 Native heap sampling 时，如果没有在这里铺垫 `heapprofd`，读者会产生认知断层。
- **建议补充方向**：在 `traced_probes` 之后，简要补充 `heapprofd` 和 `traced_perf` 的角色。

## 六、P2 问题（建议改进）
- [P2][数据/案例支撑][Trace Processor：SQL 分析引擎]
- **原文问题**：提供了一段 SQL 示例统计 `doFrame`，但没有给出预期的输出结果样例。
- **证据或观察依据**：对于没有用过 Trace Processor 的读者，纯 SQL 比较抽象。
- **建议**：补充一个 2-3 行的表格输出样例，展示 `frame_count`、`avg_ms` 等字段的实际长相，增强可读性。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|---------|-------------|
| Track Event SDK 与 atrace 性能对比 | 中 | 在实际 App 开发中，使用 Perfetto SDK 的开销与直接调用 `android.os.Trace` (atrace) 的开销量化对比。 |

## 八、外部核验建议
- 搜索关键词：`perfetto heapprofd architecture`
- 建议查：perfetto.dev 官方文档，确认 heapprofd/traced_perf 与 traced 的通信机制。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：13.1
- **严重级别**：P0
- **问题类型**：源码错误
- **位置**：参考资料
- **问题描述**：AOSP 源码路径 `system/tracing/` 不存在，Perfetto 源码在 `external/perfetto/`。
- **建议修正方向**：修改为正确的 `external/perfetto/src/traced/` 等路径。
- **建议补充的验证来源**：cs.android.com

- **章节**：13.1
- **严重级别**：P1
- **问题类型**：原理断裂
- **位置**：Perfetto 的架构
- **问题描述**：遗漏了核心架构组件 `heapprofd` 和 `traced_perf`。
- **建议修正方向**：在讲解完 `traced_probes` 后补充这两个组件的介绍。
- **建议补充的验证来源**：perfetto.dev/docs/

### 9.2 知识盲区清单（供后续研究）
- **章节**：13.1
- **盲区描述**：Perfetto C++ SDK 与传统 atrace 的性能损耗实测对比。
- **重要程度**：中
- **建议研究方向**：编写基准测试，统计每秒写入 10000 个事件时两者的 CPU 与内存开销。
- **可能关联章节**：13.7 高级用法

### 9.3 一般建议清单（非阻断）
- **章节**：13.1
- **问题类型**：数据缺失
- **位置**：Trace Processor 介绍
- **问题描述**：SQL 示例缺乏运行结果展示。
- **建议**：补充 2-3 行结果表格示例。

### 9.4 可复用知识资产（高价值新增知识）
- **章节**：13.1
- **知识点**：AOSP Perfetto 目录结构
- **源码路径**：`external/perfetto/`
- **可复用结论**：Perfetto 不在 `system/` 或 `frameworks/` 下，它是完全跨平台的 `external/` 项目，其核心服务端代码在 `src/traced/`。

## 十、下一候选章节
- 下一章建议继续 review 的章节：`02-trace-capture.md`

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-21-22-01-perfetto-intro.md-external-review.md`