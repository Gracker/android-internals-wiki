# AIW 自动 Review 任务报告

## 一、目标发现结果
- 扫描范围：`src/part3-tools/ch14-other-tools/06-automation-tools.md`
- 候选章节：
  1. `14.6 自动化测试工具` | 用户指定
- 最终选择：`src/part3-tools/ch14-other-tools/06-automation-tools.md`
- 选择理由：用户通过 Prompt 明确要求 review 本章。
- 排除的高频原因：N/A

## 二、总体结论
- 总体技术评分：4.0/5
- 是否建议回炉：是（建议进入结构化修正队列）
- 主要风险：部分 API 支持的最低版本说明过时（Microbenchmark 的 API 14、PowerMetric 的 API 31+ 描述），且涉及 Baseline Profile 的 CompilationMode 参数有轻微陈旧。
- 评分理由：存在 2 个 P1 级别的事实与版本差异偏差。虽然主干原理链完整（如对 Macro 和 Micro 的场景区分、UI Automator 驱动原理的黑盒解释非常优秀），但版本限制维度存在误导读者的风险，故最高给 4.0。
- 闭环建议：根据 P1 数量，建议按问题单修正具体的 API 版本和代码片段，无需大规模重写。
- 本轮 review 覆盖范围：Macro/Microbenchmark 定位区别、指标类型 (Startup, Frame, Power)、CompilationMode、UI Automator 驱动原理、CI/CD 集成。
- 本轮未完成部分：无，已完成全章知识点核验。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 4.0/5 | 1 |
| 原理链完整性 | 4.5/5 | 0 |
| 版本差异覆盖 | 3.5/5 | 2 |
| 知识盲区 | 4.0/5 | 1 |
| 数据/案例支撑 | 4.0/5 | 0 |
| 交叉引用一致性 | 4.5/5 | 0 |

## 四、P0 问题（事实错误）
无。

## 五、P1 问题（重要缺失/事实偏差）
- [P1][版本差异覆盖][Macrobenchmark 与 Microbenchmark 节]
  - **原文问题**：`[适用版本: Macrobenchmark 最低 API 23, Microbenchmark 最低 API 14]`
  - **源码 / 一手资料锚点**：Jetpack Benchmark 官方库源码限制 (`minSdk`)。
  - **缺失/错误内容**：现代 Jetpack Microbenchmark (1.1.0+) 的最低 API 级别通常为 19，且为了获取完整的 Perfetto 追踪和热治理检测（Thermal Throttling Detection 依赖 API 29 的 PowerManager），实际上推荐在 API 21/29+ 以上运行。API 14 的说法已经严重过时。
  - **为什么这是重要缺失**：误导开发者在过低版本的设备上配置测试环境，导致 Gradle 构建报错或测试结果无意义。
  - **建议补充方向**：修正 Microbenchmark 的最低版本为 API 19，并建议在 API 29+ 的设备上运行以获取完整的 Perfetto 数据和热治理控制。

- [P1][版本差异覆盖][测量启动时间和滑动帧率 节]
  - **原文问题**：`PowerMetric（API 31+）：测量功耗指标，包括电量消耗和温度变化。`
  - **源码 / 一手资料锚点**：`androidx.benchmark.macro.PowerMetric`
  - **缺失/错误内容**：`PowerMetric` 主要是测量能耗（Energy/Power）和电池电量（Battery）。它的主要目的不是“测量温度变化”（热治理是框架内建的防护机制）。API 限制也不是 31+，高精度能耗追踪需要 API 29+（Android 10），并且强依赖于 ODPM（On-Device Power Monitor）硬件支持（如 Pixel 6+）。
  - **为什么这是重要缺失**：会导致读者误以为在 Android 12 (API 31) 的任何普通手机上都能测功耗。实际上如果缺乏 ODPM 硬件，强行测 Power 会导致指标为空。
  - **建议补充方向**：明确 `PowerMetric` 的两种模式（高精度 Power 模式需要 API 29+ 和 ODPM 硬件，普通 Battery 模式需要长时间运行），并去掉“以温度变化为主”的误导性描述。

## 六、P2 问题（建议改进）
- [P2][源码准确性][CompilationMode 参数]
  - **原文问题**：`CompilationMode.Partial(CompilationMode.Partial.Mode.DEFAULT)`
  - **证据或观察依据**：目前的 Macrobenchmark API 中，通常直接使用无参的 `CompilationMode.Partial()` 即可，内部参数配置方式在迭代中有所变化。
  - **问题描述**：代码片段稍显陈旧或啰嗦。
  - **建议**：建议改为 `CompilationMode.Partial()`。

- [P2][知识盲区][CI/CD 集成]
  - **原文问题**：CI/CD 环节提到了 FTL 和结果收集，但没有提及生成 Baseline Profile 的自动化。
  - **证据或观察依据**：基准测试不仅用于“测量”，在现代工程流中，往往还配套了通过 `BaselineProfileRule` 自动生成 `baseline-prof.txt` 并提交 PR 的流程。
  - **问题描述**：缺失了 Macrobenchmark 衍生出的最具实战价值的场景——自动化生成 Profile。
  - **建议**：在 CI/CD 或扩展部分，提一句 `BaselineProfileRule`，说明它是与 `MacrobenchmarkRule` 同源的工具，专门用于生成基准配置文件。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|---------|-------------|
| ODPM 硬件支持限制 | 高 | 明确哪些设备能够真正跑通 `PowerMetric` 高精度模式，解释为什么有些开发者测不出功耗数据。 |
| BaselineProfileRule 自动生成 | 中 | 扩展 Macrobenchmark 工具在 CI 自动生成 `baseline-prof.txt` 方面的工程应用。 |

## 八、外部核验建议
- 搜索关键词：`Android Jetpack Macrobenchmark PowerMetric ODPM`
  - 建议查：官方文档和 issue tracker，确认非 Pixel 设备的功耗测试支持现状。
- 搜索关键词：`androidx.benchmark.macro.CompilationMode.Partial`
  - 建议查：`cs.android.com` 查看 `CompilationMode.Partial` 的最新默认参数签名。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：14.6 自动化测试工具
- **严重级别**：P1
- **问题类型**：版本差异/事实错误
- **位置**：[Macrobenchmark 与 Microbenchmark 节] 以及 [测量启动时间和滑动帧率 节]
- **问题描述**：Microbenchmark 的 API 14 要求过时，应为 API 19（推荐 29+）；PowerMetric 的 API 31+ 描述不准，且过度强调温度变化，应改为 API 29+ 且高度依赖 ODPM 硬件。
- **建议修正方向**：更新版本说明，增加对 ODPM（On-Device Power Monitor）硬件要求的强调，纠正功耗测试的局限性认知。
- **建议补充的验证来源**：Jetpack Benchmark 官方文档。

### 9.2 知识盲区清单（供后续研究）
- **章节**：14.6 自动化测试工具
- **盲区描述**：使用 `BaselineProfileRule` 自动化生成 Baseline Profile。
- **重要程度**：中
- **建议研究方向**：研究 `androidx.benchmark.macro.junit4.BaselineProfileRule` 的用法及与当前测试体系的 CI 集成策略。
- **可能关联章节**：第 8 章启动优化（关于 Baseline Profile 的生成流程）。

### 9.3 一般建议清单（非阻断）
- **章节**：14.6 自动化测试工具
- **问题类型**：代码示例准确性
- **位置**：[CompilationMode：量化编译优化效果]
- **问题描述**：`CompilationMode.Partial(CompilationMode.Partial.Mode.DEFAULT)` 代码偏老。
- **建议**：简化为 `CompilationMode.Partial()`。

### 9.4 可复用知识资产（高价值新增知识）
- **章节**：14.6 自动化测试工具
- **来源类型**：官方文档 / 源码核验
- **关键结论**：在进行 Android 功耗性能基准测试时，`PowerMetric` 的高精度测量（Energy/Power）强依赖于 Android 10 (API 29+) 引入的 ODPM (On-Device Power Monitor) 硬件支持，目前主要在 Pixel 6 及更新的设备上生效。其他普通设备通常只能使用粗略的 Battery 模式。这个知识点解释了为什么很多开发者在自己的手机上测不出 Macrobenchmark 的细粒度功耗数据。

## 十、下一候选章节
- 建议继续 review 队列中 `task9_state: pending` 的相关章节。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-21-14-06-automation-tools-external-review.md`