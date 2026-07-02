# 2026-07-02 Android 性能调研报告与 AIW 缺口对照

来源：Telegram 手动投递的《Android 性能优化技术与工具深度调研报告（截至 2026 年 7 月）》。

用途：把报告内容转成 AIW 可处理的 intake / queue 条目。原报告里的个人转型叙述不进入正文；可保留为面向读者的学习路线、章节补强和技术复核输入。

## 覆盖判断

| 报告主题 | AIW 当前状态 | 处理方式 |
|---|---|---|
| Perfetto、Trace Processor SQL、AI 辅助 trace 分析 | 已有 ch13，含 13.16 Agent 协议、13.18 SmartPerfetto、13.21 Perfetto 版本演进 | 不新增正文章；排队复核 v51-v56、traced_perf、Heap Dump Explorer、LMK stdlib、Perfetto MCP 与 SmartPerfetto 边界 |
| Google 官方 App 性能实践：Baseline Profiles、Startup Profiles、Macrobenchmark、ProfilingManager、16KB page size、ADPF | 已分散在 ch19、ch21、ch04/ch20、ch05/ch25 | 不新增正文章；学习路线附录串联，后续只对版本数据做 review |
| 大厂 APM 底层机制：Matrix、KOOM、btrace、Hook、SIGQUIT、fork+COW、字节码插桩 | 已有 ch19 APM、14.13 Hook、20/23/26 对应治理章节 | 排队补强 btrace 3.0 动态插桩/同步抓栈、Raphael/ByteHook、线上开销与边界 |
| Android Performance Analyzer | 已有 14.18，但正文存在未核验的实现和性能数据断言 | 排队 Task9 深审，优先核实官方发布、工具定位、数据格式、是否存在 eBPF/90% 开销等断言 |
| Framework / 系统背景到 App 性能的学习路径 | `preface/reading-paths.md` 只有角色导航，缺少训练路线与作品集 | 新增附录 G：Android 性能学习路线 |
| AOSP / Framework 学习方法 | 已有 15.7，但该章本身处于 rework 状态 | 附录引用 15.7 作为方法入口；15.7 单独等 Task9/Task2B 修复 |

## 本轮落地

1. 新增 `src/appendix/android-performance-learning-path.md`，状态 `draft`，进入 Task6/Task9。
2. 更新 `src/SUMMARY.md`，把附录 G 暴露到目录。
3. 更新 `metadata/queue.json`，新增 pending：
   - 附录 G 学习路线审校；
   - 14.18 Android Performance Analyzer 技术深审；
   - 19.4 / 14.13 btrace 3.0 与 Hook/APM 底层补强；
   - 13.18 / 13.21 Perfetto 2025-2026 版本与 AI 分析能力复核。

## 不直接进入正文的内容

- 原报告中的个人背景指向全部改成面向读者的角色路径。
- 未核实的开销数字不写入正文，只作为 Task9 待核验项。
- 岗位市场、就业判断不进入 AIW 正文；如果后续要写，也应进入运营文章或读者路线说明，不混入技术章节。
