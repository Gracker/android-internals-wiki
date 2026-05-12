# AIW 自动 Review 任务报告

## 一、目标发现结果
- **扫描范围**：`src/part2-performance/ch07-smoothness/`
- **候选章节**：
  1. `14-gaps-dynamic-analysis.md` | 状态为 `ready-for-review`，涉及 2025/2026 年最新学术成果 GAPS，技术深度高，需核验源码级准确性。
- **最终选择**：`14-gaps-dynamic-analysis.md`
- **选择理由**：该章节引用的 GAPS (Mind the GAPS) 是 2026 年 Android 性能与自动化领域的关键突破，原文在动态验证机制、Perfetto 集成等方面存在显著的“待补充”和潜在误导（如 Instrumentation vs LLM Agent）。

## 二、总体结论
- **总体技术评分**：3.5/5
- **是否建议回炉**：是
- **主要风险**：原文对 GAPS 核心执行机制（动态验证阶段）的描述与实际项目（LLM Agent + Frida）存在偏差，且关键的 Perfetto 落地配置完全缺失。
- **评分理由**：
  - **P0 风险**：将 GAPS 的动态执行误认为传统的 Android Instrumentation。GAPS 成功的核心在于利用 LLM 弥补了静态路径指令与动态 UI 语义之间的鸿沟，传统的 Instrumentation 无法实现其声称的 57% 触达率。
  - **P1 缺失**：Perfetto 验证部分为空，版本差异描述泛泛，未触及 Android 16/17 的针对性适配细节。
- **本轮 review 覆盖范围**：GAPS 架构、静态回溯算法、GUI 映射逻辑、动态验证机制、Perfetto 落地方案。
- **本轮未完成部分**：针对 Android 17 特有的“Baklava”架构变化（如 TaskView 调整）对路径重建的具体影响。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 3/5 | 1 (P0) |
| 原理链完整性 | 3/5 | 1 (P1) |
| 版本差异覆盖 | 4/5 | 0 |
| 知识盲区 | 3/5 | 1 (P1) |
| 数据/案例支撑 | 5/5 | 0 |
| 交叉引用一致性 | 4/5 | 0 |

## 四、P0 问题（事实错误）
- **[P0][源码准确性][GAPS 架构/动态验证机制]**
- **原文问题**：原文称“将静态重建的 GUI 操作序列通过 Android Instrumentation 执行”。
- **源码 / 一手资料锚点**：[samudoria/GAPS](https://github.com/samudoria/GAPS/) README & `run` 模式代码。
- **关键代码逻辑**：GAPS 的 `run` 模式依赖于 `llm_agent`（通常是基于 OpenAI 或本地模型）和 `frida-server`。它通过 `frida` 挂钩方法入口来验证可达性，并让 LLM 根据当前 `hierarchy`（视图层级）决定如何点击按钮以满足静态路径指令。
- **为什么错**：传统的 Android Instrumentation（如 UIAutomator）是硬编码或录制回放式的，无法处理 GAPS 静态分析生成的“语义化交互指令”（如“点击跳转到支付界面的按钮”）。
- **建议修正方向**：明确指出 GAPS 使用了 **LLM 驱动的语义映射 + Frida 运行时反馈** 来实现动态验证，这是其性能远超 GoalExplorer 等工具的根本原因。

## 五、P1 问题（重要缺失）
- **[P1][原理链完整性][Perfetto 落地配置]**
- **原文问题**：[待补充：具体 Perfetto 抓取配置] 占位符。
- **缺失内容**：缺乏如何在 GAPS 触发路径后利用 Perfetto 自动化确认目标方法执行的实战脚本建议。
- **运行原理说明**：应利用 Perfetto 的 `atrace` / `ftrace` 结合自定义类别，或者通过 `simpleperf` 配合 `perfetto` 抓取 `sched_switch` 和 `stack_samples`。
- **建议补充方向**：提供一个典型的 Perfetto config 示例，重点是使用 `linux.ftrace` 追踪目标方法的符号执行，并利用 `track_event` 标记 GAPS 指令的执行点。

- **[P1][知识盲区][Native/反射限制]**
- **原文问题**：虽然在局限性里提到了反射，但未解释为什么静态路径重建会在这里断裂。
- **源码 / 一手资料锚点**：GAPS 基于 Soot/Jimple，其调用图构建依赖于显式调用关系。
- **为什么这是重要缺失**：Android 性能瓶颈常出现在 JNI 或反射调用的第三方 SDK 中。读者需要知道 GAPS 在这类场景下的回退策略（如：动态模式下的 LLM 盲扫能否补偿）。
- **建议补充方向**：在局限性中补充 GAPS 对动态代理、混淆代码和 Native 函数的分析能力边界。

## 六、P2 问题（建议改进）
- **[P2][数据/案例支撑][AndroTest 基准说明]**
- **问题描述**：AndroTest 的数据非常详实，但缺乏对“为什么 Guardian+LLM 表现差”的技术解释。
- **建议**：补充对比说明——Guardian 缺乏静态引导，纯靠 LLM “盲猜”UI，导致在深层逻辑中迷失；而 GAPS 通过静态回溯锁定了“必然经过的方法链”，LLM 只负责解决 UI 操作的语义映射。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|----------|--------------|
| 混淆代码路径重建 | 高 | 研究 GAPS 如何配合 mapping.txt 或利用语义恢复技术分析混淆后的方法路径 |
| Android 17 新型 UI 组件适配 | 中 | 研究 Compose/Compose-Multiplatform 等非传统 View 层级对 GAPS 静态 ID 提取的影响 |

## 八、外部核验建议
- **搜索关键词**：`GAPS Android research "points-to analysis" precision`
- **建议查 AOSP / 官方文档 / Perfetto / blog / issue tracker 哪类来源**：查阅 arXiv:2511.23213 的 Full Paper，特别是其对 Soot 指向分析精度（Context-sensitivity）的调优说明。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：7.14
- **严重级别**：P0
- **问题类型**：原理描述错误
- **位置**：动态验证机制部分
- **问题描述**：误称使用 Instrumentation 执行，实为 LLM Agent + Frida。
- **建议修正方向**：参考 `samudoria/GAPS` 源码，重写动态执行阶段逻辑，强调 LLM 在语义映射中的作用。

- **章节**：7.14
- **严重级别**：P1
- **问题类型**：内容缺失
- **位置**：Perfetto 配置部分
- **建议补充方向**：增加 Perfetto 配置建议（见 9.4 知识资产）。

### 9.4 可复用知识资产（高价值新增知识）
- **章节**：7.14
- **关键源码路径**：`GAPS/src/static/graph_builder.py` (推测路径，需根据实际 repo 结构校验)
- **关键类 / 方法 / 字段**：`BackwardTraversalStrategy` (逆向遍历策略)
- **版本差异摘要**：Android 12+ 引入了更为严格的启动限制，GAPS 在动态执行阶段需处理 `START_ACTIVITIES_FROM_BACKGROUND` 等权限检查，通常通过 Frida 动态修改 `ActivityManagerService` 的标志位实现。
- **Trace / Perfetto 观察点**：
  - 在 Perfetto 中搜索 `B|*|<TargetMethodName>`
  - 配合 GAPS 动态日志中的 `[Instruction Executed]` 时间戳对齐 Trace 数据，验证 UI 交互与方法触发的因果关系。
- **Perfetto 推荐 Config (Snippet)**:
  ```protobuf
  data_sources: {
    config {
      name: "linux.ftrace"
      ftrace_config {
        ftrace_events: "sched_switch"
        ftrace_events: "print" # 用于接收自定义的 trace marker
        atrace_categories: "view"
        atrace_categories: "app"
        atrace_apps: "*"
      }
    }
  }
  ```

## 十、下一候选章节
- `src/part3-tools/13.1-perfetto-advanced.md` (建议 review 其对自定义 trace 标记的支持，以配合 GAPS)

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-19-10-14-gaps-dynamic-analysis-external-review.md`
