# AIW 自动 Review 任务报告

## 一、目标发现结果
- 扫描范围：`src/part3-tools/ch14-other-tools/02-simpleperf.md` 及相关元数据。
- 候选章节：
  1. `14.2 Simpleperf` | 明确指定 review 该章节。
- 最终选择：`src/part3-tools/ch14-other-tools/02-simpleperf.md`
- 选择理由：用户指令明确要求对 `02-simpleperf.md` 进行 review。
- 排除的高频原因：N/A

## 二、总体结论
- 总体技术评分：4.0/5
- 是否建议回炉：是（建议进入结构化修正队列，修复 P0 和 P1 问题）
- 主要风险：工具生态链认知混淆，将 Firefox Profiler 的数据格式错误关联到了 Perfetto UI，且遗漏了 PMU 硬件事件在无 Root 设备上的权限墙限制。
- 评分理由：存在 1 个 P0 错误（数据格式与可视化工具对应关系错误）和 1 个 P1（重要缺失：硬件 PMU 权限限制）。整体原理与使用方法覆盖较好，命令参数清晰，但实战环境中的踩坑边界有遗漏。
- 闭环建议：生成回炉问题单，重点修正“在 Perfetto 中的表现”小节中的工具链错误，并补充 PMU 硬件权限限制。
- 本轮 review 覆盖范围：Simpleperf 基本原理、常见命令行参数、版本能力演进、火焰图生成工具链、与 Perfetto 关系对比、内核符号解析等全量知识点。
- 本轮未完成部分：无，已完成全章核心知识点审查。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 4/5 | 1 |
| 原理链完整性 | 4/5 | 1 |
| 版本差异覆盖 | 5/5 | 0 |
| 知识盲区 | 4/5 | 1 |
| 数据/案例支撑 | 4/5 | 0 |
| 交叉引用一致性 | 5/5 | 0 |

## 四、P0 问题（事实错误）
- [P0][源码准确性][在 Perfetto 中的表现]
- **原文问题**：“用 `gecko_profile_generator.py` 把 `perf.data` 转成 Gecko JSON，再拖到 `ui.perfetto.dev`。”
- **源码 / 一手资料锚点**：Simpleperf AOSP `scripts_reference.md` / `gecko_profile_generator.py` 源码 / Firefox Profiler (`profiler.firefox.com`)。
- **关键代码逻辑**：`gecko_profile_generator.py` 生成的是 Mozilla Gecko Profile 格式，专为 Firefox Profiler 设计。
- **运行原理说明**：Perfetto UI (`ui.perfetto.dev`) 不原生支持解析 Gecko JSON 格式（它主要解析 Perfetto 的 protobuf `.trace` 格式）。Gecko JSON 必须拖入 `profiler.firefox.com` 才能查看交互式火焰图和时间轴。
- **版本差异（如适用）**：无。
- **核验结论**：原文工具链错配。
- **为什么错**：会导致读者按指南生成 JSON 后，在 Perfetto UI 导入失败并产生严重挫败感。
- **建议修正方向**：明确拆分两条可视化路径：
  1. Firefox Profiler 路径: 使用 `gecko_profile_generator.py` 生成 JSON，去 `profiler.firefox.com` 查看。
  2. Perfetto UI 路径: 使用 `simpleperf report-sample --protobuf` 导出 `.trace` 文件，去 `ui.perfetto.dev` 查看。

## 五、P1 问题（重要缺失）
- [P1][知识盲区][硬件 PMU 事件]
- **原文问题**：介绍了 `cache-misses`、`branch-misses` 等硬件 PMU 事件的用法，但完全未提及权限门槛。
- **缺失内容**：未说明 Android 系统对硬件 PMU（Performance Monitoring Unit）事件的极其严格的权限限制（受 `kernel.perf_event_paranoid` 控制）。
- **运行原理说明**：出于安全和侧信道攻击（如 Spectre/Meltdown）的防范，现代 Android 设备默认将 `kernel.perf_event_paranoid` 设为 2 或 3。这意味着非 Root 用户（即便是处于 `profileable` 状态的 App）通常只能采样软件事件（如 `cpu-clock`）和内核 Tracepoint，而**无法**访问真实的硬件 PMU 事件（如 `cache-misses`）。
- **为什么这是重要缺失**：如果在未 Root 的生产/测试机上执行 `simpleperf record -e cache-misses`，会直接收到内核级的权限拒绝（EACCES），若文章不写明，读者在实战中会直接受阻并怀疑命令写错。
- **建议补充方向**：在 PMU 事件小节必须补充强提醒：“注意：采集硬件 PMU 事件（如 `cache-misses`）通常强制要求 Root 权限。在非 Root 设备上对 `profileable` / `debuggable` App 采样，一般只能使用 `cpu-clock` 或 `task-clock` 等软件事件。”

## 六、P2 问题（建议改进）
- [P2][原理链完整性][软件事件：cpu-clock 和 task-clock]
- **原文问题**：对 `--trace-offcpu` 原理的解释偏向表象。
- **证据或观察依据**：Simpleperf 的 `--trace-offcpu` 机制强依赖内核 `sched:sched_switch` tracepoint。
- **问题描述**：原文只说“会用它生成 on-CPU 样本”，没有清晰点出 off-CPU 的时间是如何被可视化的。
- **建议**：补充 `--trace-offcpu` 的计算本质：它是通过监听 `sched_switch`（调度切换）事件，计算线程被换出 CPU 和下一次被换入 CPU 之间的**时间差**，然后将这个“墙上时间”（Wall-clock time）作为权重，伪造出 off-CPU 的样本，从而能在火焰图中体现出真实的等待/阻塞比例。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|---------|-------------|
| Android PMU 权限管控 | 高 | 调研不同 Android 版本下 `perf_event_paranoid` 的默认值差异，以及 `simpleperf list` 在 Root / 非 Root 下的输出区别。 |
| 跨厂商 PMU 事件名差异 | 中 | 梳理高通 Snapdragon 与联发科 Dimensity 对自定义 PMU 事件命名的差异。 |

## 八、外部核验建议
- 搜索关键词：`kernel.perf_event_paranoid android simpleperf default`
- 建议查阅：AOSP `system/core/rootdir/init.rc` 中关于 sysctl 的配置，确认现代版本 Android 对非 root App 的真实 perf event 限制边界。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：14.2 Simpleperf
- **严重级别**：P0
- **问题类型**：事实错误 / 工具链关联错误
- **位置**：“在 Perfetto 中的表现”
- **问题描述**：错误地指出 `gecko_profile_generator.py` 的产物可以拖入 `ui.perfetto.dev`，实际上 Gecko JSON 只能在 `profiler.firefox.com` 中使用。
- **建议修正方向**：梳理正确的导出路径：1) Gecko JSON 对应 Firefox Profiler；2) `--protobuf` `.trace` 对应 Perfetto UI。
- **建议补充的验证来源**：Firefox Profiler 官方文档，Simpleperf AOSP `scripts_reference.md`。

- **章节**：14.2 Simpleperf
- **严重级别**：P1
- **问题类型**：知识盲区 / 权限机制缺失
- **位置**：“硬件 PMU 事件”
- **问题描述**：未指明访问 PMU 硬件事件（如 cache-misses）需 Root 权限，容易导致实战读者受挫。
- **建议修正方向**：明确告知在非 Root 设备的 `profileable` 模式下，通常只能使用 `cpu-clock` 等软件事件。

### 9.2 知识盲区清单（供后续研究）
- **章节**：14.2 Simpleperf
- **盲区描述**：Android 各厂商芯片底层 PMU 事件名称的不一致性。
- **重要程度**：中
- **建议研究方向**：调研主流 SoC 在 `simpleperf list` 输出的 Raw PMU Events 异同。

### 9.3 一般建议清单（非阻断）
- **章节**：14.2 Simpleperf
- **问题类型**：原理链补充
- **位置**：“软件事件：cpu-clock 和 task-clock”
- **问题描述**：`--trace-offcpu` 机制解释不够透彻。
- **建议**：补充基于 `sched_switch` 计算时间差加权的原理。

### 9.4 可复用知识资产（高价值新增知识）
- **章节**：14.2 Simpleperf
- **一手资料链接**：https://android.googlesource.com/platform/system/extras/+/master/simpleperf/scripts/gecko_profile_generator.py
- **关键源码路径**：`simpleperf/scripts/gecko_profile_generator.py`
- **可直接复用的技术结论**：Simpleperf 并不只绑定 Perfetto。其自带的 `gecko_profile_generator.py` 能转换出标准的 Gecko Profile 格式，支持直接在 **Firefox Profiler** (`profiler.firefox.com`) 中分析。Firefox Profiler 具备顶级的火焰图和多线程时间轴交互体验，是 Android Native/混合代码剖析中极为强大且被官方推荐的分析管线。
- **为什么这条知识值得保留**：突破了传统工具的思维定势，引入了更高质量的可视化手段。

## 十、下一候选章节
- 建议下一章 review：`src/part3-tools/ch14-other-tools/01-android-studio-profiler.md` （以确保 CPU 采样和 Method Trace 与 Simpleperf 部分相互印证且概念不冲突）。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-21-14-02-simpleperf-external-review.md`