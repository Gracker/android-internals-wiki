# AIW 自动 Review 任务报告

## 一、目标发现结果
- 扫描范围：`src/part3-tools/ch14-other-tools/` 目录下的所有 markdown 文件。
- 候选章节：
  1. `01-as-profiler.md` | `status: ready-for-review`, `task9_state: pending` (需技术复审)
  2. `02-simpleperf.md` | 同上
  3. `03-memory-tools.md` | 同上
  （及其他 8 篇同目录文章）
- 最终选择：`01-as-profiler.md` (作为本轮序列的第一个处理项)
- 选择理由：本章是性能工具的核心开篇，与后续工具形成互补关系，亟需确认版本差异与开销特性的准确性。
- 排除的高频原因：暂无排除，将逐个处理。

## 二、总体结论
- 总体技术评分：3.5/5
- 是否建议回炉：是 (进入结构化修正队列)
- 主要风险：部分 API 版本归属（如 ProfilingManager）与硬件支持逻辑（如 ODPM 对应 Pixel 6 的 Android 版本描述）存在事实性瑕疵或易误导读者的表述。
- 评分理由：文章整体结构与对三种 CPU 模式开销的对比非常清晰，具备较高实战价值。但存在 1 个 API 版本的细节混淆（P1），以及对 ODPM 硬件支持前置条件的描述存在逻辑矛盾（P1）。因此不能给予 4.0 以上高分。
- 闭环建议：修正 API 35/36 的演进说明，厘清 ODPM 与 Android 10+ 的硬件依赖关系。
- 本轮 review 覆盖范围：整章（CPU Profiler 模式对比、Memory 曲线与 Dump、Power Profiler、ProfilingManager）。
- 本轮未完成部分：无。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 4/5 | 1 |
| 原理链完整性 | 4/5 | 0 |
| 版本差异覆盖 | 3/5 | 2 |
| 知识盲区 | 4/5 | 0 |
| 数据/案例支撑 | 4/5 | 0 |
| 交叉引用一致性 | 4/5 | 0 |

## 四、P0 问题（事实错误）
无硬性代码逻辑跑不通的 P0。

## 五、P1 问题（重要缺失/版本差异不准确）
- [P1][版本差异覆盖][Power Profiler]
  - 原文问题："目前只有 Pixel 6 及以后的 Pixel 设备、且系统为 Android 10（API 29）及以上才支持 ODPM 数据。"
  - 为什么这是重要缺失：Pixel 6 的出厂系统是 Android 12，因此"Pixel 6 且 Android 10"的表述在逻辑上是矛盾的。ODPM 确实需要 Android 10+ 的软件支持，但搭载 ODPM 的硬件是 Pixel 6+，导致读者可能误以为拿着刷了旧系统的 Pixel 6 就能测，或者拿着 Android 10 的旧 Pixel 就能测。
  - 建议补充方向：更正为"需要设备硬件支持 ODPM（如 Pixel 6 及后续机型），且系统软件在 Android 10（API 29）及以上"。

- [P1][版本差异覆盖][ProfilingManager API]
  - 原文问题："Android 提供了 ProfilingManager API（Android 16，API 36 新增）来支持这种程序化的 profiling 触发... 系统检测到特定事件时自动抓取..."
  - 一手资料锚点：`android.os.ProfilingManager` (API 35 引入)，`System-triggered profiling` (API 36 增强)。
  - 为什么这是重要缺失：混淆了 API 的首次引入版本与系统触发器（System-triggered）的增强版本。`ProfilingManager` 本身是 Android 15 (API 35) 引入的，支持应用内代码请求；而基于冷启动、ANR 等系统事件的自动触发追踪是 Android 16 (API 36) 的新增特性。
  - 建议补充方向：明确区分 API 35 和 API 36 的能力边界。指出 API 35 支持基础请求，API 36 引入了系统级触发器。

## 六、P2 问题（建议改进）
- [P2][源码准确性][Callstack Sample 采样引擎]
  - 原文问题："在 Android Studio 2025 的最新版本中，Google 引入了新的采样引擎..."
  - 证据或观察依据：标有 `[待验证]`，且"Android Studio 2025" 的命名方式较为宽泛（可能是 Ladybug 或 Meerkat）。
  - 建议：建议查阅 AS Ladybug 或最新 Canary 版本的 Release Notes，明确具体是哪个代号的版本引入的新引擎（如 AS Meerkat），避免使用模糊的"2025版本"。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|---------|-------------|
| System Trace 在 Profiler 与直接用 Perfetto 抓取的差异 | 中 | 虽然底层都是 Perfetto，但 Profiler 默认开启的 atrace tag 可能与命令行 `record_android_trace` 有区别，建议对比二者的 config。 |

## 八、外部核验建议
- 搜索关键词：`Android Studio Meerkat CPU Profiler sample engine release notes`
- 建议查：Android Developers Blog / Studio Release Notes，确认新采样引擎的准确发布版本代号。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
1. **章节**：`01-as-profiler.md`
   - **严重级别**：P1
   - **问题类型**：版本差异
   - **位置**：Power Profiler 小节
   - **问题描述**："Pixel 6 且 Android 10"存在硬件出厂版本逻辑矛盾。
   - **建议修正方向**：解耦硬件要求与软件要求，改为"硬件需支持 ODPM（如 Pixel 6+），软件需 Android 10+（API 29+）"。
2. **章节**：`01-as-profiler.md`
   - **严重级别**：P1
   - **问题类型**：版本差异
   - **位置**：使用 Profiler API 在代码中触发 profiling
   - **问题描述**：`ProfilingManager` 首次引入于 API 35，系统触发器（System-triggered）引入于 API 36。原文笼统说是 API 36 新增。
   - **建议修正方向**：明确拆分 API 35（基础调用）与 API 36（系统自动触发器）的区别。

### 9.2 知识盲区清单（供后续研究）
- 章节：`01-as-profiler.md`
- 盲区描述：Profiler System Trace 与纯 CLI Perfetto Trace 的默认 Config 差异。
- 重要程度：中
- 建议研究方向：导出 Profiler 的 `.perfetto-trace` 并在 ui.perfetto.dev 查看它的 data sources 配置。

### 9.3 一般建议清单（非阻断）
- 章节：`01-as-profiler.md`
- 问题类型：描述模糊
- 位置：Callstack Sample 小节
- 问题描述："Android Studio 2025" 命名不够专业确切。
- 建议：定位到具体动物代号（如 Koala, Ladybug, Meerkat）。

### 9.4 可复用知识资产（高价值新增知识）
- 章节：`01-as-profiler.md`
- 一手资料链接：`android.os.ProfilingManager` 官方文档。
- 可直接复用的技术结论：Android 15 (API 35) 首次引入了生产环境的性能数据收集 API `ProfilingManager`。而在 Android 16 (API 36) 中，Google 进一步放开了基于系统事件（如 ANR、OOM、冷启动）的被动触发机制 (`System-triggered profiling`)，极大地降低了线上疑难杂症的排查门槛。这构成了 Android 性能监控从"主动抓取"向"被动捕获"的重要演进。

## 十、下一候选章节
- 下一章建议继续 review 的章节：`02-simpleperf.md`

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-21-14-01-as-profiler-external-review.md`