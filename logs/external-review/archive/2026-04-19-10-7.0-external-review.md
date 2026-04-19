# AIW 自动 Review 任务报告

## 一、目标发现结果
- 扫描范围：`src/part2-performance/ch07-smoothness/`
- 候选章节：
  1. `README.md` | 章节入口，列出核心大纲。
  2. `01-jank-definition.md` | 核心原理篇，定义技术标准。
- 最终选择：`src/part2-performance/ch07-smoothness/README.md` (连带审计核心原理篇)
- 选择理由：用户明确指定，且作为第 7 章的入口，其结构的准确性决定了整章的知识广度。
- 排除的高频原因：暂无（直接执行用户指令）。

## 二、总体结论
- 总体技术评分：2.0/5
- 是否建议回炉：是
- 主要风险：**内容与版本声明严重不符**。声明已验证至 Android 16，但正文缺失了 Android 15/16 渲染链路上的所有重大变更（ARR/VRR、ADPF GPU 监控、Slow Sessions）。
- 评分理由：
  - 存在 1 处 P0：版本核验声明与事实严重不符（虚假验证）。
  - 存在 4 处 P1：关键分类缺失、核心指标缺失、目录严重滞后、硬件链路演进缺失。
- 闭环建议：必须进入重度回炉流程，补齐 Android 15/16 差异。
- 本轮 review 覆盖范围：`README.md` 目录结构、`01-jank-definition.md` 全文。
- 本轮未完成部分：02-14 章节的细分实战内容（如 Compose、Webview 专项）。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 2.0/5 | 2 |
| 原理链完整性 | 3.0/5 | 1 |
| 版本差异覆盖 | 1.0/5 | 3 |
| 知识盲区 | 2.0/5 | 2 |
| 数据/案例支撑 | 3.0/5 | 1 |
| 交叉引用一致性 | 2.0/5 | 1 |

## 四、P0 问题（事实错误）
- [P0][版本差异覆盖][frontmatter]
- 原文问题：声明 `last_verified_against: "AOSP android-16.0.0_r1"`，但在 Jank 分类中未提及该版本引入的任何新特性。
- 源码 / 一手资料锚点：`frameworks/native/services/surfaceflinger/FrameTimeline/JankInfo.h` (Android 15+ 增加 `JANK_DISPLAY_MODE_CHANGE_IN_PROGRESS` 等枚举)。
- 关键代码逻辑：系统在进行自适应刷新率切换时，会自动标记此类延迟以避免归责给 App。
- 运行原理说明：Android 15 引入 ARR，VSync 信号在单模式内可变。
- 核验结论：原文描述的 Jank 分类仍基于 Android 12。
- 为什么错：作者可能只更新了日期，未同步 AOSP 最新的代码演进。
- 建议修正方向：在 Jank 分类节补充 Android 15+ 的 4 种新分类。

## 五、P1 问题（重要缺失）
- [P1][交叉引用一致性][README.md]
- 原文问题：目录仅列出 6 项，而目录下实际有 14 个文件。
- 缺失内容：7.7-7.14 章节（Compose, Webview, SystemUI, GAPS 等）。
- 为什么这是重要缺失：读者无法通过 README 导航到这些高价值实战篇章。
- 建议补充方向：更新 README.md 中的“本章内容”列表，确保与物理文件同步。

- [P1][知识盲区][01-jank-definition.md]
- 缺失内容：**Android 15 Slow Sessions 指标**。
- 运行原理说明：Google Vitals 在 Android 15 中将“慢会话”作为核心流畅度指标（>25% 的帧超过 50ms/34ms）。
- 为什么这是重要缺失：这是目前线上监测卡顿的最权威标准。
- 建议补充方向：在“掉帧率与卡顿率”小节新增 Slow Sessions 详解。

- [P1][原理链完整性][01-jank-definition.md]
- 缺失内容：**ADPF GPU 负载监控**。
- 关键代码逻辑：`PerformanceHintManager` 在 Android 15 中支持 `reportActualWorkDuration` 同时上报 CPU 和 GPU 时长。
- 为什么这是重要缺失：现代卡顿常由 GPU 瓶颈引起，只讲 CPU 错过 deadline 已不完整。
- 建议补充方向：在 AppDeadlineMissed 小节补充 GPU 耗时对 Jank 判定的贡献。

## 六、P2 问题（建议改进）
- [P2][数据/案例支撑][01-jank-definition.md]
- 原文问题：BufferStuffing 节缺少具体的 Latency 增加数据说明。
- 建议：补充 BufferStuffing 导致“画面流畅但输入极度不跟手”的 Perfetto 观察点（如 BufferQueue 深度 > 1 时 Latency 的阶梯式增长）。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|----------|--------------|
| ARR (Adaptive Refresh Rate) 与 VSync 解耦 | 高 | 研究 HWC 3.0 如何在单模式内通过 VSync 步长调整刷新率 |
| ProfilingManager 系统触发采样 | 中 | 研究 Android 16 如何根据卡顿自动触发 Perfetto 追踪 |
| RecyclerView 1.4 的 ARR 自动适配 | 高 | 分析其如何通过 WindowInsets 接口向 SF 请求动态刷新率 |

## 八、外部核验建议
- 搜索关键词：`Android 15 FrameTimeline Jank classification`, `Android ARR Vsync 1.0`, `Slow Sessions Android Vitals`
- 建议查：
  - `frameworks/native/services/surfaceflinger/FrameTimeline/` 下的 `FrameTimeline.cpp`
  - Perfetto 官方文档中关于 `JANK_DISPLAY_MODE_CHANGE` 的说明
  - Android Developers 官网关于 Slow Sessions 的最新定义

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：`README.md` / `01-jank-definition.md`
- **严重级别**：P0/P1
- **问题类型**：源码错误 / 目录滞后 / 版本差异缺失
- **位置**：frontmatter 及 Jank 分类全节
- **问题描述**：版本声明与内容脱节，缺失 Android 15/16 关键渲染技术点。
- **建议修正方向**：同步最新 AOSP 源码中的 `JankInfo.h` 枚举，并补齐 ARR 与 Slow Sessions 内容。

### 9.2 知识盲区清单（供后续研究）
- **章节**：`01-jank-definition.md`
- **盲区描述**：Android 16 ARR 深度适配机制
- **重要程度**：高
- **建议研究方向**：RecyclerView 如何利用新 API 动态提频。

### 9.3 可复用知识资产
- **章节**：`01-jank-definition.md`
- **一手资料链接**：`https://perfetto.dev/docs/data-sources/frametimeline`
- **关键源码路径**：`frameworks/native/services/surfaceflinger/FrameTimeline/JankInfo.h`
- **关键类 / 方法**：`enum class JankType`
- **版本差异摘要**：Android 15 引入 `JANK_DISPLAY_MODE_CHANGE` 过滤机制。
- **技术结论**：FrameTimeline 在 Android 15 之后已具备“系统预知延迟”过滤能力，诊断时需排除标记为 `DISPLAY_MODE_CHANGE` 的红色帧。

## 十、下一候选章节
- `07-compose-performance.md`（作为 README 中缺失的重要实战篇章，建议优先 review）

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-19-10-README-external-review.md`
