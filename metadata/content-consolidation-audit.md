# 正文收敛审阅台账

本台账记录逐章全文审阅、合并和编号整理的结果。它只描述当前规范正文；历史日志、已关闭 review finding 和素材采集记录保留发生时的旧路径。

## 审阅规则

1. 阅读一章内全部正文和章节 README，再判断主题边界，不按文件名机械合并。
2. 同一概念保留一个完整解释；重复文章中的独有源码证据、版本边界、实验方法和排障步骤并入保留正文。
3. 只保留能独立回答问题的文章。导读、版本概览或“小节级”内容不单独占用正文编号。
4. 错放内容并入实际主题所在章节，不为维持旧编号保留空壳。
5. 每章同步 `src/SUMMARY.md`、章节 README、活动脚本映射、跨章引用和进度统计，验证后独立提交。

## 总体进度

| 章节 | 审阅前正文 | 审阅后正文 | 状态 | 完成日期 |
| --- | ---: | ---: | --- | --- |
| ch06 存储与 I/O | 12 | 5 | 已完成 | 2026-08-11 |
| ch03 输入系统 | 14 | 8 | 已完成 | 2026-08-11 |
| ch04 内存管理 | 29 | 17 | 已完成 | 2026-08-11 |
| ch05 CPU 调度与能耗管理 | 38 | 17 | 已完成 | 2026-08-11 |
| ch07 流畅度 | 20 | 14 | 已完成 | 2026-08-11 |
| ch08 响应速度 | 20 | 12 | 已完成 | 2026-08-11 |
| ch09 ANR | 13 | 10 | 已完成 | 2026-08-11 |
| ch10 内存性能 | 10 | 7 | 已完成 | 2026-08-11 |
| ch11 功耗 | 8 | 7 | 已完成 | 2026-08-11 |
| ch12 网络性能 | 8 | 3 | 已完成 | 2026-08-11 |
| ch13 Perfetto | 27 | 22 | 已完成 | 2026-08-11 |
| ch14 其他分析工具 | 32 | 28 | 已完成 | 2026-08-11 |
| ch15 性能方法论 | 12 | 10 | 已完成 | 2026-08-11 |
| ch16 AOSP 性能优化 | 12 | 11 | 已完成 | 2026-08-11 |
| ch17 OEM 与设备差异 | 12 | 10 | 已完成 | 2026-08-11 |
| ch18 渲染管线专题 | 27 | 25 | 已完成 | 2026-08-11 |
| ch19 APM 工具与性能监控生态 | 28 | 22 | 已完成 | 2026-08-11 |
| ch20 应用稳定性治理 | 27 | 22 | 已完成 | 2026-08-11 |
| ch21 启动优化 | 20 | 16 | 已完成 | 2026-08-11 |
| 其余 7 章 | 254 | 待审阅 | 未开始 | - |

当前规范正文总数为 519 篇。这里的“已完成”表示该章每篇正文均已阅读并完成本轮结构收敛，不代表所有技术结论都已达到发布状态。

## ch21 启动优化

保留后的连续编号为 21.1～21.16。内容按“启动路径与任务图 → Provider、Profile、首屏和多进程 → 监控 → 特殊 SDK 与设备编译 → GC、DI、Compose、并发、局部性和设备分级”组织；H1 不再重复章节号。

合并映射：

| 原正文 | 处理结果 | 当前承载位置 |
| --- | --- | --- |
| `02-startup-framework.md` / `20-modular-startup-dependency-graph.md` / 原案例二 | 合并 AndroidX App Startup 的 manifest 发现、DFS 依赖遍历、循环检测、手动初始化、多进程 Provider、动态特性边界和启动任务治理；删除案例页中重复的 DAG 迁移说明 | `../src/part5-app/ch21-startup/02-startup-framework.md`（21.2） |
| `04-baseline-profile-practice.md` / `12-startup-profile-dex-layout.md` / 原案例三 | 将 Startup Profile 收回 Profile 主文，保留生成范围、AGP/R8 条件、`r8.json`/checksum、APK Analyzer、单变量 layout A/B 和失效模式；删除第二套 Profile 概览与案例演练 | `../src/part5-app/ch21-startup/04-baseline-profile-practice.md`（21.4） |
| `08-startup-monitoring.md` / `17-startup-insights-api-observability.md` / 原案例模板 | 合并 `ApplicationStartInfo` 的 API 35～37 边界、记录状态、八类时间戳、当前进程选择、开发者 key 源码差异、安全区间计算、线上 cohort 与工具分工；复盘模板并入监控闭环 | `../src/part5-app/ch21-startup/08-startup-monitoring.md`（21.8） |
| `09-startup-case-studies.md` 其余内容 | 大型 App 初始化、GC、任务框架和 Profile 案例均重复 21.1～21.4、21.6、21.8、21.11 的机制与实验流程，不再保留独立案例汇编 | 21.1～21.4、21.6、21.8、21.11 |
| 原 21.10～21.11、21.13～21.16、21.18～21.19 | 广告 SDK、设备端 Profile/DM、GC、DI、Compose、线程池、缓存局部性和设备分级均能独立回答问题，依次改为连续编号 21.9～21.16 | `../src/part5-app/ch21-startup/09-sdk-runtime-ad-sdk-startup.md`～`../src/part5-app/ch21-startup/16-device-tier-performance-strategy.md` |

章节 README、`src/SUMMARY.md`、活动跨章引用和统计口径已经切换到新编号。历史 changelog、review/audit 日志、关闭 finding、素材索引、锁文件与 `consolidated_from` 保留旧路径和编号。

## ch20 应用稳定性治理

保留后的连续编号为 20.1～20.22。内容按“故障类型 → 度量、恢复与聚合 → 内存安全和平台兼容 → IPC/栈/Hook 诊断 → FD、线程、Native 内存与协程生命周期 → SDK 治理”组织；H1 不再重复章节号。

合并映射：

| 原正文 | 处理结果 | 当前承载位置 |
| --- | --- | --- |
| `03-native-crash-governance.md` / `19-android17-signal-handler-debuggerd-migration.md` | 合并 fatal signal、SignalChain、linker wiring、altstack/pseudothread、CrashInfo、tag bit、debuggerd/tombstone 与采集器共存验证；栈回溯和符号化深挖继续由独立条目承载 | `../src/part5-app/ch20-stability/03-native-crash-governance.md`（20.3） |
| `07-exception-architecture.md` / `12-safemode-crash-loop-recovery.md` | 将 SafeMode 收回异常恢复架构，保留 LaunchLease、两阶段退出证据核对、降级计划、多进程/版本分桶、迟滞恢复与验证矩阵；删除重复的 Java/Native/ANR 捕获说明 | `../src/part5-app/ch20-stability/07-exception-architecture.md`（20.7） |
| `17-binder-exception-ipc-fault-performance.md` / `22-binder-communication-monitoring.md` | 合并 Binder 异常、共享 buffer/freezer/oneway/重试语义与 client/server wrapper、均匀+慢样本采样、Perfetto 长尾分析和监控安全约束 | `../src/part5-app/ch20-stability/15-binder-ipc-fault-monitoring.md`（20.15） |
| `11-mte-memtag-native-crash.md` / `23-gwp-asan-probabilistic-memory-safety-android17.md` | 合并 MTE 与 GWP-ASan 两类 Native 内存安全检测；分别保留 tag/guarded pool、配置、抽样、recoverable 报告和工具分工，共用符号、事件、灰度与修复闭环 | `../src/part5-app/ch20-stability/10-mte-gwp-asan-native-memory-safety.md`（20.10） |
| `09-stability-case-studies.md` | 不再保留跨主题案例集；Native 采集器冲突、ContentProvider 启动 ANR、`pthread_create` OOM 的复现与验收分别回流到 Native Crash、ANR 和线程治理正文 | 20.3、20.4、20.19 |
| `14-thread-fd-resource-monitoring.md` / `25-thread-leak-anonymous-thread-monitoring.md` / `20.27-coroutine-leak-*.md` | 删除 FD 稿中与线程专题重复的 task/ThreadFactory/创建链；保留纯 FD 所有权与限额。线程和协程因观测对象、生命周期与修复动作不同，继续独立承载 | 20.12、20.19、20.21 |
| 原 20.10、20.13～20.18、20.24～20.28 中未合并的主题 | WebView、16 KB、DCL、Keystore、Native unwind、Hook、Java 锁栈、线程、Native 内存、协程和 SDK 均能独立回答问题，依次改为连续编号 | `09-webview-renderer-oom-recovery.md`～`22-sdk-performance-governance.md` |

章节 README、`src/SUMMARY.md`、活动队列、跨章引用和统计口径已经切换到新编号。历史 changelog、review/audit 日志、已关闭 finding、素材索引、锁归档与旧 intake 摘要保留发生时的路径。

## ch19 APM 工具与性能监控生态

保留后的连续编号为 19.1～19.22。内容按“全景与准入 → 当前客户端工具 → 历史方案 → 官方帧与 trace API → Benchmark/编译/系统取证 → 托管平台 → 实验室工具与设备基线 → 网络、稳定性、功耗、混合栈和端侧架构”组织。

合并映射：

| 原正文 | 处理结果 | 当前承载位置 |
| --- | --- | --- |
| `19.10-apm-tool-compatibility.md` | 删除与 Matrix、KOOM、BlockCanary、AndroidGodEye 正文重复的逐工具兼容性复述；独有的七层准入、成对变体、4 KB/16 KB 设备矩阵、测量字段和验收清单并入全景篇 | `../src/part3-tools/ch19-apm/01-apm-landscape.md`（19.1） |
| `06-blockcanary.md` / `08-argusapm.md` / `10-other-opensource-apm.md` | 将已停止维护、只适合原理参考或存量迁移的项目统一为历史开源 APM；保留 Looper dispatch/采样/Printer 语义、Argus 架构与迁移，以及 AndroidGodEye/Collie/Rabbit 的设计取舍 | `../src/part3-tools/ch19-apm/08-open-source-apm-history.md`（19.8） |
| `11-jankstats.md` / `12-framemetrics.md` | 合并同一 Window 帧监控链路；JankStats 负责 UI context 与线上分布，FrameMetrics 负责阶段、Window/Surface 边界和 API 36+ Vsync join；去掉两篇互相重复的分工、指标和聚合说明 | `../src/part3-tools/ch19-apm/09-jankstats-framemetrics.md`（19.9） |
| `19-perfdog.md` / `20-solopi-emmagee.md` | 合并实验室外部观测与操作复现：PerfDog 负责趋势，SoloPi 负责路径，Emmagee 只解释历史；共享一套权限、环境、报告和 Perfetto/Macrobenchmark 分工 | `../src/part3-tools/ch19-apm/16-testing-tools.md`（19.16） |
| `21-benchmark-apps.md` / `22-storage-benchmark.md` | 将存储作为设备能力向量的一部分并入通用设备 Benchmark；保留 AndroBench/A1 历史边界、CPDT/PCMark 替代、I/O 协议、路径/cache/durability 和业务证据链 | `../src/part3-tools/ch19-apm/17-device-benchmarks.md`（19.17） |
| 原 19.7、19.9、19.13～19.18、19.23～19.27 | DoKit、Measure、Tracing、Benchmark、Baseline Profiles、ProfilingManager、Firebase、商业平台和五个采集/架构专题仍能独立回答问题，依次改为连续编号 | `06-dokit.md`～`22-apm-client-architecture.md` |

章节 README、`src/SUMMARY.md`、changelog/review 脚本、活动跨章引用和统计口径已经切换到新编号。历史 changelog、review/audit 日志、关闭 finding、素材索引与 `consolidated_from` 保留旧路径和编号。

## ch18 渲染管线专题

保留后的连续编号为 18.1～18.25。内容按“分类与通用分析 → View/Surface/图形 API → 框架与硬件 Producer → 刷新率、跨设备、XR、媒体与新图形能力”组织。

合并映射：

| 原正文或重复小节 | 处理结果 | 当前承载位置 |
| --- | --- | --- |
| `20-pipeline-analysis-methodology.md` | 删除第二套渲染分类、十二锚点、Producer/Consumer/fence、Perfetto、瓶颈和选型教程；独有的事实/关联/结论分层、对象身份卡、统一取证步骤、SQL 与复核清单并入章节总览 | `../src/part2-performance/ch18-rendering-pipelines/01-pipeline-overview.md`（18.1） |
| `18-pip-freeform.md` | 删除与多窗口正文重复的 WMS/SF 双树、线程共享、BLAST sync、HWC 和 Trace 教程；独有的 PictureInPictureParams、PiP 过渡、geometry/buffer 组合及 Android 17 配置重建边界并入多窗口主文 | `../src/part2-performance/ch18-rendering-pipelines/05-android-view-multi-window.md`（18.5） |
| 18.3 中的 HardwareBufferRenderer 与直接 setBuffer 教程 | 压缩为软件/离屏分类边界；所有权、fence、提交和回收协议统一由 18.10 与 18.17 承载 | 18.3、18.10、18.17 |
| 18.15 中的 tunneled playback 完整教程 | 只保留 SIDEBAND 对 HWC/trace 判读的影响；Codec2、Media3、音视频同步和排障统一由播放管线承载 | `../src/part2-performance/ch18-rendering-pipelines/21-media-codec2-tunneled-media3-abr.md`（18.21） |
| 18.16 中的小游戏、云游戏、AR、XR 四套缩略教程 | 压缩为责任边界和路由；TextureView、媒体/sideband、OpenXR runtime/compositor 分别回到专项 | 18.7、18.20、18.21 |
| 原 18.19、18.21～18.27 | VRR、EyeDropper、XR、媒体、APV、Compose、HWUI Vulkan 多队列与 WebGPU 均能独立回答问题，依次改为连续编号 18.18～18.25 | `18-variable-refresh-rate.md`～`25-webgpu-android-pipeline.md` |

章节 README、`src/SUMMARY.md`、changelog/review 脚本、复审清单、活动跨章链接和统计口径已经切换到新编号。历史 changelog、review/audit 日志、关闭 finding、素材索引与 `consolidated_from` 保留旧路径。

## ch17 OEM 与设备差异

保留后的连续编号为 17.1～17.10，依次覆盖 OEM 归因方法、SoC 平台差异、应用协作案例、sched_ext 与 MUSCHED、游戏输入、Media Performance Class、Private Space/App Lock、Power HAL/schedutil、PowerStats 与车载性能。

合并映射：

| 原正文 | 处理结果 | 当前承载位置 |
| --- | --- | --- |
| `04-sched-ext-oem-bpf-scheduler.md` / `08-musched-vip-scheduling-practice.md` | 保留 sched_ext 的编译、运行、DSQ、schedutil、vendor hook 和 trace 主线；将 MUSCHED 的语义标注、VIP 预算、锁/Binder 传播、选核、量产数据和 6.18 迁移成本作为同一机制的 OEM 案例合并 | `../src/part4-system/ch17-oem/04-sched-ext-oem-bpf-scheduler.md`（17.4） |
| `09-soc-specific-power-optimization.md` / `17.21-android17-soc-vendor-power-hal-schedutil-loop.md` | 合并 Power AIDL、Mode/Boost、Hint Session/FMQ、SCX 三种状态、cpufreq 解析、vendor hook、异常恢复、高通/联发科/三星公开驱动边界和实验方法 | `../src/part4-system/ch17-oem/08-power-hal-schedutil-soc-power.md`（17.8） |
| `17.23-power-stats-hal-oem-implementation.md` | PowerStats 是结果计量与归因链路，不参与 schedutil 控制；保留为独立主题并改为连续编号 | `../src/part4-system/ch17-oem/09-power-stats-hal-oem-implementation.md`（17.9） |
| `25.21-android-auto-car-os-performance.md` | 正文实际位于 ch17，且原编号与 ch25 的 PerformanceHintManager 冲突；保留 Android Auto/AAOS 责任边界、模板、Surface、媒体、VHAL、CarWatchdog 和电源管理，改为 17.10 | `../src/part4-system/ch17-oem/10-android-auto-car-os-performance.md`（17.10） |
| `03-industry-cases.md` 中的 Jetpacker/GenAI 路由教程 | 与 OEM 性能协作无关，且端云选型和 AppFunctions 已由 ch05 与 ch16 专题承载；从案例篇移除，保留 Samsung、Game Mode/ADPF、TikTok/抖音和多形态设备证据 | `../src/part4-system/ch17-oem/03-industry-cases.md`（17.3） |
| 原 17.1～17.7 中未合并的主题 | 仍能独立回答归因、硬件差异、案例、输入、设备能力和隐私边界问题；统一 frontmatter、H1 与目录标题 | `01-oem-overview.md`～`07-private-space-app-lock-boundary.md` |

章节 README、`src/SUMMARY.md`、changelog 映射、活动跨章引用和统计口径已经切换到连续编号。历史 changelog、review 日志、素材索引、freshness 快照与 `consolidated_from` 保留旧编号和路径。

## ch16 AOSP 性能优化

保留后的连续编号为 16.1～16.11，依次覆盖平台优化方法、版本变更、AOSP 构建调试、Kernel 6.18、Android 17 适配、Profile/DM/SDM 安装编译、系统启动、AppFlow、Rust、ARM64 安全缓解和 AOHP。

合并映射：

| 原正文 | 处理结果 | 当前承载位置 |
| --- | --- | --- |
| `01-google-optimization.md` | 删除与 16.2/16.4/16.5 重复的版本史、ART、DeliQueue、Binder 与 BLAST 机制说明；保留并重写为平台问题判断、分层证据、交付版本轴、实验和回滚方法 | `../src/part4-system/ch16-aosp/01-google-optimization.md`（16.1） |
| `04-android17-kernel618-performance.md` 中的 ART 与 DeliQueue | 从 Kernel 专题移除重复的平台运行时内容；generational CMC、MessageQueue gate 与迁移测试统一由 16.5 承载 | `../src/part4-system/ch16-aosp/05-android17-api37-performance-changes.md`（16.5） |
| `06-android16-cloud-profile-dexopt.md` / `09-android17-sdm-install-performance.md` | 合并 Baseline/Startup/Cloud Profile、DM/SDM/SDC、ART Service、安装/后台 dexopt、运行时加载、A/B/C 实验和应用侧检查 | `../src/part4-system/ch16-aosp/06-profile-dm-sdm-install-compilation.md`（16.6） |
| 原 16.10～16.12 | Rust、ARM64 安全缓解与 AOHP 均能独立回答问题，依次改为连续编号 16.9～16.11 | `09-rust-system-services-performance.md`～`11-agent-native-os.md` |
| `参考资料.md` | 通用版本锚点和引用规则并入章节 README；主题来源继续留在各正文，不再保留独立目录项 | `../src/part4-system/ch16-aosp/README.md` |

章节 README、`src/SUMMARY.md`、changelog 映射、活动跨章链接、复审清单和统计口径已经切换到连续编号。历史 changelog、review 日志、关闭 finding、freshness 快照与 `consolidated_from` 保留旧编号和路径。

## ch15 性能方法论

保留后的连续编号为 15.1～15.10，依次覆盖总方法论、系统/App 归因、指标合同、竞品分析、线上监控、性能测试、AOSP 阅读、实证研究、反馈回路与团队治理，以及 AI 编码评测。

合并映射：

| 原正文 | 处理结果 | 当前承载位置 |
| --- | --- | --- |
| `09-observability-closed-loop.md` / `10-performance-governance.md` | 合并监控异常、采样与聚合之后的归因、工单、发布和验收流程；删除与 15.5 重复的 JankStats、ApplicationExitInfo 和线上采样教程，以及与 14.9/15.6 重复的 Macrobenchmark 与 Baseline Profile 示例 | `../src/part3-tools/ch15-methodology/09-performance-governance.md`（15.9） |
| `15.12-android-performance-research-methodology.md` | 删除第二套总方法论、工具选型、Perfetto 采集/SQL、优化和测试教程；独有的证据等级、替代假设与知识交付规范并入总论，Perfetto 与 Power HAL 细节继续由 13.2、13.9、13.22、5.4 和 17.8 承载 | `../src/part3-tools/ch15-methodology/01-philosophy.md`（15.1） |
| `15.11-google-android-bench-ai-coding-evaluation-methodology.md` | 主题独立，改为连续编号 15.10，并移除 H1 中重复的章节号 | `../src/part3-tools/ch15-methodology/10-google-android-bench-ai-coding-evaluation-methodology.md` |
| `08-empirical-performance-issues.md` | 主题独立；统一 H1，不再在正文标题中重复章节号 | `../src/part3-tools/ch15-methodology/08-empirical-performance-issues.md` |

章节 README、`src/SUMMARY.md`、changelog 映射、活动跨章链接、审阅清单和统计口径已经切换到连续编号。历史 changelog、review 日志、关闭 finding 与 `consolidated_from` 保留旧编号和路径。

## ch14 其他分析工具

保留后的连续编号为 14.1～14.28。内容按问题证据重新排列：IDE 与 CPU 分析（14.1～14.4）、内存与系统快照（14.5～14.8）、自动化和线上治理（14.9～14.14）、GPU/窗口/布局（14.15～14.22）、eBPF、Hook、构建归因与动态分析（14.23～14.28）。

合并映射：

| 原正文 | 处理结果 | 当前承载位置 |
| --- | --- | --- |
| `14-android-studio-leakcanary-profiler.md` | 删除第二套 LeakCanary、HPROF 与线上内存取证教程；保留 Panda/Quail IDE task、instrumentation 泄漏断言、测试样本和 release 隔离边界 | `../src/part3-tools/ch14-other-tools/05-memory-tools.md`（14.5） |
| `12-apm-observability.md` | 删除与三方性能库选型重复的平台与 SDK 清单；保留 JankStats、FrameMetrics、ApplicationExitInfo、Vitals 的官方信号分层，以及 schema、主键、采样、隐私和开销口径 | `../src/part3-tools/ch14-other-tools/10-third-party-libs-observability.md`（14.10） |
| `27-macrobenchmark-automation-gate.md` | 删除第二套 Macrobenchmark 工程与指标教程；保留配对实验、绝对/相对预算、样本不足与 inconclusive、温度/网络/cache 噪声控制和异常 trace 诊断 | `../src/part3-tools/ch14-other-tools/09-automation-tools.md`（14.9） |
| `14.31-android17-ftrace-atrace-perfetto-bridge.md` | 与 Perfetto 章的 tracing infrastructure 重复，没有保留第二套 tracefs/atrace/Perfetto probe 说明 | `../src/part3-tools/ch13-perfetto/08-tracing-infrastructure.md`（13.8） |
| 14.1 中的 ProfilingManager 完整 API 教程 | 压缩为生产设备受限采集入口；API 35～37、系统触发、限流、脱敏与产物交付只在专项维护 | `../src/part3-tools/ch14-other-tools/11-profiling-manager.md`（14.11） |
| 原 14.24、14.32、14.3、14.22、14.4、14.11、14.6、14.5、14.7 | 按 CPU → 内存 → 快照 → 自动化 → 可观测性顺序改为 14.3～14.11 | `03-android17-simpleperf-microarch-profiling.md`～`11-profiling-manager.md` |
| 原 14.17、14.23、14.19、14.8、14.28、14.18、14.29、14.30、14.9、14.15、14.16 | 按系统指标/CLI → GPU → Camera → 窗口/布局顺序改为 14.12～14.22 | `12-statsd-system-metrics.md`～`22-layout-inspector-viewdebug.md` |
| 原 14.10、14.21、14.25、14.13、14.20、14.26 | 按 eBPF 工具/加载/矩阵 → Hook → R8 → GAPS 顺序改为 14.23～14.28 | `23-ebpf-performance-analysis.md`～`28-gaps-dynamic-analysis.md` |

章节 README、`src/SUMMARY.md`、changelog 映射、活动跨章链接、审阅清单和统计口径已经切换到连续编号。历史 changelog、review 日志、关闭 finding 和受保护素材索引保留旧路径。

## ch13 Perfetto

保留后的连续编号为 13.1～13.22，依次覆盖简介、采集、UI、大文件、线程状态、指标自动化、输入延迟、Tracing 基础设施、SQL 手册、区间关联、Profile、DVFS、Data Explorer/CUJ、BufferQueue、Agent 协议、应用内 SDK、SmartPerfetto、FrameTracer、FrameTimeline、`android.os.Trace`、v57 state track 与采集可靠性。

合并映射：

| 原正文 | 处理结果 | 当前承载位置 |
| --- | --- | --- |
| `05-topic-analysis.md` | 删除第二套启动、帧、Binder 与内存分析导读；独有的块 I/O、Suspend、WakeLock、频率驻留和跨进程身份查询并入 SQL 手册 | `../src/part3-tools/ch13-perfetto/09-perfetto-sql-cookbook.md`（13.9） |
| `13.21-perfetto-version-evolution.md` | 删除把版本时间线、heapprofd、FrameTimeline 与 Systrace 混在一起的重复概览；平台/分析端版本轴、服务演进与数据源可用性由简介统一承载 | `../src/part3-tools/ch13-perfetto/01-perfetto-intro.md`（13.1） |
| `13.25-perfdog-android-platform-gpu-performance-data-sources.md` | 删除对闭源 PerfDog 内部采集实现的推测；可验证的 GPU/BufferQueue/FrameTimeline 证据继续由图形帧专题和其他工具章承载 | 13.14、13.18、13.19；ch14 后续单独审阅 |
| `17-android17-data-sources.md` | 删除重复的数据源综述；`linux.perf`、FrameTracer、FrameTimeline 的配置、权限、解析与 SQL 分别由三个专项承载 | `11-perfetto-profiles-flamegraph.md`、`18-frametracer-graphics-frame-event.md`、`19-frame-timeline-api33-perfetto-analysis.md` |
| `21-perfetto-pprof-simpleperf-native-visualization.md` | 删除第二套 pprof/Simpleperf/Linux perf 说明；格式边界、采集、符号化、火焰图和同轴分析由 Profile 主文统一承载 | `../src/part3-tools/ch13-perfetto/11-perfetto-profiles-flamegraph.md`（13.11） |
| 原 13.27 的 AI skill 教程 | 与 Agent 调查协议重复，删除安装与交付清单；保留 v57 state track 的生产、查询和 Android 17 版本边界 | 13.15、13.21 |
| 原 13.6～13.20、13.23、13.26～13.27 | 保留主题边界，统一文件名、frontmatter 与 H1 为连续 13.5～13.22 | `05-thread-cpu-states.md`～`22-trace-reliability.md` |

章节 README、`src/SUMMARY.md`、changelog 映射、活动跨章链接、审阅清单和统计口径已经切换到连续编号。历史 changelog、review 日志、关闭 finding 和受保护素材索引保留旧路径。

## ch12 网络性能

保留后的连续编号为：

- 12.1 网络性能优化
- 12.2 Android 网络安全与 TLS 性能优化
- 12.3 netd 与 DnsResolver：DNS 解析性能和故障诊断

合并映射：

| 原正文 | 处理结果 | 当前承载位置 |
| --- | --- | --- |
| `01-apk-size.md` | 从网络性能章移出；合并 APK 的 ZIP 结构、DEX 引用上限、资源与 ELF 压缩、签名块和多种体积口径，DEX、native library、资源与分发细节继续由既有专项承载 | `../src/part5-app/ch25-power-size/06-apk-analysis.md`（25.6），以及 25.7、25.8、25.29～25.31 |
| `03-network-performance-deep.md` | 合并网络栈层次、BlockGuard、连接池精确默认值、HTTP/3/Cronet、长连接、协程、后台网络与 Perfetto 取证；删除与基础稿重复的 DNS、TLS、超时和重试说明 | `../src/part2-performance/ch12-apk-network/01-network-performance.md`（12.1） |
| `05-connectivity-service-network-callback.md` / `08-networkagent-lifecycle-scoring.md` | 从应用网络性能章移出；合并 NetworkAgentInfo 生命周期、netId、offer、FullScore、rematch、linger、回调 API 与 Android 17 能力边界 | `../src/part1-fundamentals/ch01-architecture/1.62-android17-connectivitymanager-architecture-performance.md`（1.62） |
| `07-privacy-sandbox-performance.md` | 从网络性能章移出；合并 Topics、Ad Selection、Measurement 与 SDK Runtime 的退场状态、版本边界和迁移清单 | `../src/part5-app/ch21-startup/09-sdk-runtime-ad-sdk-startup.md`（21.9） |
| 原 12.2 / 12.4 / 12.6 | 客户端网络性能、TLS 和 DNS 三条边界均可独立回答问题，依次改为连续编号 12.1～12.3 | `01-network-performance.md`～`03-netd-dnsresolver-network-diagnostics.md` |

章节 README、`src/SUMMARY.md`、复审清单、阅读路径、活动跨章链接和统计口径已经切换到连续编号。历史 changelog、原始规格、素材索引与 `consolidated_from` 保留旧路径。

## ch11 功耗

保留后的连续编号为：

- 11.1 Android 功耗模型
- 11.2 App 耗电优化
- 11.3 系统级功耗优化
- 11.4 案例集
- 11.5 WakeLock 机制与功耗分析
- 11.6 Bluetooth 扫描与连接功耗分析
- 11.7 用户设置对能耗的影响：亮度、刷新率与深色模式

合并映射：

| 原正文或小节 | 处理结果 | 当前承载位置 |
| --- | --- | --- |
| `08-tare-economic-model.md` | 删除独立专题；Android 17 控制器、quota、flexibility、pending reason、BatteryStats 边界与排障流程已由 JobScheduler 主文覆盖，独有的 Android 13—14 TARE 隐藏/默认关闭、全局耗电校准和 2024 年删除边界并入版本演进 | `../src/part1-fundamentals/ch05-cpu-power/08-jobscheduler-workmanager-performance.md`（5.8） |
| 11.2 的 WakeLock 完整教程 | 压缩为应用选型与安全边界入口；源码调用链、SystemSuspend、内核唤醒源、Vitals 和逐层诊断统一由专项承载 | `../src/part2-performance/ch11-power/05-wakelock.md`（11.5） |
| 11.1～11.5 的标题与元数据 | 统一 H1 编号、`11.04` 编号和 `WakeLock` 大小写；11.6、11.7 主题独立，原位保留 | 11.1～11.7 |

章节 README、`src/SUMMARY.md`、复审清单和统计口径已经切换到连续编号。历史日志、已关闭 finding、素材索引与 `consolidated_from` 保留旧路径。

## ch10 内存性能

保留后的连续编号为：

- 10.1 App 内存分析
- 10.2 内存泄漏
- 10.3 内存持续增长
- 10.4 低内存对系统性能的影响
- 10.5 案例集
- 10.6 内存抖动与频繁 GC
- 10.7 GPU 与图形内存统计

合并映射：

| 原正文 | 处理结果 | 当前承载位置 |
| --- | --- | --- |
| `10.01-android-memory-performance-optimization.md` | 删除与章节 README、内存分析、泄漏、增长、抖动和低内存专题重复的第二套全章导读 | `../src/part2-performance/ch10-memory-perf/README.md`、10.1～10.6 |
| `07-sqlite-room-performance.md` | 从内存性能章移出；合并回滚日志/WAL、checkpoint、Session/连接池、CursorWindow、Room 2.8.4、Paging、PRAGMA、多进程与数据库 ANR 诊断 | `../src/part5-app/ch24-io-network/02-database-optimization.md`（24.2） |
| `10-art-gc-fragmentation-regions-optimization.md` | 合并 CC evacuation 的精确条件与 CMC fault counter；重复的分代、LOS、Perfetto、allocation profile 和应用优化由既有主文承载 | `../src/part1-fundamentals/ch04-memory/07-art-generational-gc.md`（4.7）、10.6 |
| 原 10.8 GPU 正文 | 主题独立，改为连续编号 10.7，并统一标题与活动跨章引用 | `../src/part2-performance/ch10-memory-perf/07-gpu-graphics-memory-tracking.md` |

章节 README、`src/SUMMARY.md`、复审清单、活动跨章链接和统计口径已经切换到连续编号。历史 changelog、已关闭 finding、素材索引与 `consolidated_from` 保留旧路径。

## ch09 ANR

保留后的连续编号为：

- 9.1 ANR 设计思想
- 9.2 ANR 类型与触发条件
- 9.3 ANR 分析方法
- 9.4 特殊与跨边界 ANR
- 9.5 案例集
- 9.6 Notification 性能与 ANR
- 9.7 ANR 与 Kernel Trace 联合诊断
- 9.8 ContentProvider 超时与 ANR 四路径
- 9.9 Android 17 ANR 预警回调与类型枚举
- 9.10 Android 17 Input ANR 与 pre-ANR 实现

合并映射：

| 原正文 | 处理结果 | 当前承载位置 |
| --- | --- | --- |
| `07-non-technical-anr-diagnosis.md` | 删除重复的类型边界、跨进程归因、线程状态和系统压力流程；独有的 InputTransport finished-signal 历史平台缺陷补入案例集 | 9.2～9.5，重点为 `../src/part2-performance/ch09-anr/05-case-studies.md` |
| `13-anr-log-cpu-analysis-methodology.md` | 合并长期/临时 ProcessCpuTracker 采样窗、百分比分母、fault/PSI 边界和三层解析模型 | `../src/part2-performance/ch09-anr/03-anr-analysis.md`（9.3） |
| `9.11-enterprise-anr-monitoring-platform-design.md` | 从 ANR 原理章移出；能力与证据分层、事件 authority、端侧 spool、三层去重、服务端闭环、隐私和验证归入可观测性主文 | `../src/part5-app/ch26-observability/04-anr-monitoring.md`（26.4） |
| 原 9.8 / 9.9 / 9.10 / 9.12 | 每篇均有独立的完整源码责任链，保留并依次改为连续编号 9.7～9.10；Provider 标题按正文的四条计时路径修正，Input 标题不再把局部 pre-ANR 能力泛化为“双层预警” | `07-anr-kernel-trace-joint-diagnosis.md`～`10-android17-input-anr-prewarning.md` |

章节 README、`src/SUMMARY.md`、活动跨章链接和统计口径已经切换到连续编号。历史 changelog、已关闭 finding 与 `consolidated_from` 保留旧路径。

## ch08 响应速度

保留后的连续编号为：

- 8.1 响应速度原理
- 8.2 App 启动全流程
- 8.3 启动优化策略
- 8.4 其他响应速度场景
- 8.5 案例集
- 8.6 Kotlin Coroutine、Flow 与线程调度实践
- 8.7 Baseline Profiles 与编译优化实践
- 8.8 Binder Trace 驱动的 Activity 冷启动性能分析
- 8.9 Keystore/KeyMint 调用延迟与登录链路性能
- 8.10 BiometricPrompt 与 Credential Manager 登录链路性能
- 8.11 推送通知管线性能
- 8.12 Play Integrity API 性能与集成延迟

合并映射：

| 原正文 | 处理结果 | 当前承载位置 |
| --- | --- | --- |
| `08-media-pipeline.md` | 删除跨音频、视频、Camera 和播放器实战的横向重复稿；低延迟/HDR/Eclipsa 组合能力补入播放管线主文 | 1.16、18.14、`../src/part2-performance/ch18-rendering-pipelines/21-media-codec2-tunneled-media3-abr.md`、22.43 |
| `09-game-performance.md` | 合并 Game Mode/State、ADPF、Swappy、headroom 和四组对照实验 | `../src/part2-performance/ch18-rendering-pipelines/16-game-engine.md`、5.9 |
| `08-system-triggered-profiling.md` | 合并 system trigger、设备验证、线上 redaction 与 Android 8—14 降级策略 | `../src/part3-tools/ch14-other-tools/11-profiling-manager.md`（14.11） |
| `11-native-library-loading-dynamic-linker.md` | 合并启动关键路径、`JNI_OnLoad`、三方 SDK/引擎和最终 APK/AAB 门禁 | `../src/part1-fundamentals/ch01-architecture/58-android-dynamic-linker-linker64-native-library.md`（1.58） |
| `17-kotlin-flow-backpressure-performance.md` / `19-thread-model-dispatcher-selection.md` | 合并 Flow 热流/背压/flatten、Executor/HandlerThread、线程优先级、EEVDF 与 ADPF TID 边界 | `../src/part2-performance/ch08-responsiveness/06-coroutine-performance.md`（8.6） |
| `20-jni-overhead-native-interop-performance.md` | 合并 ART transition、数组复制、引用表、Attach/Detach、pthread 与微基准方法 | `../src/part1-fundamentals/ch01-architecture/15-jni-ndk-performance.md`（1.15） |
| `21-broadcast-performance-cross-process-overhead.md` | 合并发送/排队/执行分段、`goAsync()`、sticky、系统事件和任务机制选择 | `../src/part1-fundamentals/ch01-architecture/33-broadcastqueue-scheduling-performance.md`（1.33） |
| `18-binder-trace-cold-start-analysis.md` | 内容足以独立回答启动期 Binder 归因，保留并改为连续编号 8.8 | `../src/part2-performance/ch08-responsiveness/08-binder-trace-cold-start-analysis.md` |
| `12-keystore-keymint-latency.md`～`15-play-integrity-api-performance.md` | 四个专项边界独立，依次改为连续编号 8.9～8.12 | `09-keystore-keymint-latency.md`～`12-play-integrity-api-performance.md` |

章节 README、`src/SUMMARY.md`、活动跨章链接和统计口径已经切换到连续编号。历史 changelog、已关闭 finding、锁文件与 `consolidated_from` 保留旧路径。

## ch07 流畅度

保留后的连续编号为：

- 7.1 卡顿的定义与分类
- 7.2 卡顿原因体系
- 7.3 卡顿分析方法论
- 7.4 典型场景分析
- 7.5 优化策略
- 7.6 案例集
- 7.7 Jetpack Compose 性能优化
- 7.8 RecyclerView 列表滑动性能深度优化
- 7.9 感知流畅性：步幅波动与无掉帧卡顿
- 7.10 View 体系性能优化：布局层级、inflate 与 measure/layout 开销
- 7.11 SystemUI 性能分析
- 7.12 HWC Overlay Plane 与合成降级排查
- 7.13 AccessibilityManagerService 与无障碍服务性能影响
- 7.14 ContentCaptureService 与 Autofill 性能影响

合并映射：

| 原正文 | 处理结果 | 当前承载位置 |
| --- | --- | --- |
| `10-image-bitmap-performance.md` | 删除重复的请求、解码、BitmapPool、Hardware Bitmap 与 Perfetto 说明；保留独有的 Ultra HDR/Gainmap 内存边界 | 22.6、22.17、`../src/part5-app/ch22-rendering-practice/35-bitmap-decode-pipeline-imagedecoder.md` |
| `11-webview-performance.md` | 合并 provider 版本、启动、JS Bridge、宿主 HWUI、renderer 生命周期和诊断方法 | `../src/part5-app/ch22-rendering-practice/07-webview-optimization.md`、18.13 |
| `12-view-layout-performance.md` | 主题独立，改为连续编号 7.10 | `../src/part2-performance/ch07-smoothness/10-view-layout-performance.md` |
| `13-systemui-performance.md` | 主题独立，改为连续编号 7.11 | `../src/part2-performance/ch07-smoothness/11-systemui-performance.md` |
| `14-gaps-dynamic-analysis.md` | 从流畅度章移出；作为目标方法可达性与自动执行工具归入工具章 | `../src/part3-tools/ch14-other-tools/28-gaps-dynamic-analysis.md`（14.28） |
| `15-scenario-playbooks.md` | 删除与分析方法、典型场景重复的第二套 runbook；问题卡、责任链、场景分流和结论模板由主文统一承载 | `../src/part2-performance/ch07-smoothness/03-jank-methodology.md`、`../src/part2-performance/ch07-smoothness/04-typical-scenarios.md` |
| `16-power-thermal-jank-playbook.md` | 拆回功耗诊断与 Thermal 治理主文；补入 thermal throttling 到卡顿的可证伪因果链 | `../src/part5-app/ch25-power-size/01-power-diagnosis.md`、`../src/part5-app/ch25-power-size/28-thermal-manager-throttling-performance.md` |
| `17-fragmenttransaction-commit-jank.md` | 合并提交 API、主线程消息、生命周期、首帧与 Perfetto 诊断 | `../src/part5-app/ch22-rendering-practice/12-fragment-transaction-performance.md`；7.4 保留场景入口 |
| `18-hwc-overlay-composition-downgrade.md` / `19-accessibility-manager-performance.md` / `20-contentcapture-autofill-performance.md` | 主题独立，依次改为连续编号 7.12～7.14 | `12-hwc-overlay-composition-downgrade.md`～`14-contentcapture-autofill-performance.md` |

章节 README、`src/SUMMARY.md`、活动跨章链接和统计口径已经切换到连续编号。历史 changelog、已关闭 finding、已完成 todo 与 `consolidated_from` 保留旧路径。

## ch05 CPU 调度与能耗管理

保留后的连续编号为：

- 5.1 Linux 进程调度基础
- 5.2 EAS 能量感知调度
- 5.3 大小核架构
- 5.4 DVFS 与功耗管理
- 5.5 Thermal 管控
- 5.6 Android 功耗管理
- 5.7 后台执行限制与优化
- 5.8 JobScheduler/WorkManager 调度与后台任务性能
- 5.9 ADPF 自适应性能框架
- 5.10 端侧 AI 推理性能：NPU/GPU 加速与 LiteRT 管线
- 5.11 移动端 LLM 推理的 DVFS 与能效边界
- 5.12 Android 17 ML Runtime 与 NPU 访问边界
- 5.13 SensorService 与传感器批处理功耗模型
- 5.14 CPU Cache 友好代码与数据布局优化
- 5.15 系统托管 GenAI：AICore、OnDeviceIntelligence 与资源竞争
- 5.16 Bluetooth LE Audio 延迟与功耗性能
- 5.17 Android 17 App Hibernation 状态机与冷启动恢复性能

合并映射：

| 原正文 | 处理结果 | 当前承载位置 |
| --- | --- | --- |
| `07-cpu-evolution.md` | 删除横向版本概览；scheduler、DVFS、功耗和后台执行版本边界回到机制主文 | 5.1、5.4、5.6～5.8 |
| `31-android17-eevdf-scheduler.md` / `5.32-linux-610-bpf-dvfs-schedutil-loop.md` / `5.34-android17-task-scheduler-optimization.md` | 合并 EEVDF、`sched_ext`、Android task profile 与分层诊断 | `../src/part1-fundamentals/ch05-cpu-power/01-linux-scheduling.md`、5.4、5.7、5.8 |
| `5.28-android17-pelt-boost-revert-amu-pmu-microarch-frequency-limiting.md` | 合并 PELT 版本边界、AMU/PMU 诊断和提频收益验证 | `../src/part1-fundamentals/ch05-cpu-power/02-eas.md`、`../src/part1-fundamentals/ch05-cpu-power/04-dvfs.md` |
| `5.21-android17-battery-optimization-soc-architecture.md` / `5.29-android17-gpu-dvfs-headroom-power-advisor.md` / `5.35-pms-cpuidle-schedutil.md` | 合并 Power HAL、PowerStats、GPU headroom/PowerAdvisor、CPUIdle 与 schedutil 边界 | 5.4、5.6、5.9 |
| `12-thermal-management-deep-dive.md` | 合并 kernel/HAL/Framework 分层、JobScheduler thermal 消费、主动降载与实验方法 | `../src/part1-fundamentals/ch05-cpu-power/05-thermal.md` |
| `25-low-power-standby-background-performance.md` | 合并 LPS 状态机、网络与 WakeLock 消费者、豁免和观测方法 | `../src/part1-fundamentals/ch05-cpu-power/06-android-power.md` |
| `08-background-execution.md` / `17-fgs-type-declaration-background-performance.md` / `21-adaptive-battery-app-standby-coordination.md` | 合并 FGS 五道门、待机桶消费者、Doze、Alarm 与缓存进程冻结并改为 5.7 | `../src/part1-fundamentals/ch05-cpu-power/07-background-execution.md` |
| `05.26-android17-jobscheduler-service-cpu-quota.md` / `10-jobscheduler-workmanager-performance.md` / `23-android17-jobscheduler-system-throttling.md` | 合并 elapsed-time quota、五个执行关口、controller、并发槽位和公开调试接口并改为 5.8 | `../src/part1-fundamentals/ch05-cpu-power/08-jobscheduler-workmanager-performance.md` |
| `5.19-ondevice-ai-adpf-intelligent-scheduling.md` | 合并 HintSession 的 TID、周期、NDK workload hint 与端侧 AI 使用边界 | `../src/part1-fundamentals/ch05-cpu-power/09-adpf.md` |
| `11-ondevice-ml-inference-performance.md` / `16-gpu-npu-heterogeneous-scheduling.md` | 合并异构 buffer、copy、fence、队列与归因方法并改为 5.10 | `../src/part1-fundamentals/ch05-cpu-power/10-ondevice-ml-inference-performance.md` |
| `13-mobile-llm-dvfs-energy.md` / `14-android17-ml-runtime-npu-boundary.md` / `15-sensorservice-batching-power.md` / `18-cpu-cache-friendly-code-data-layout.md` | 主题独立，依次改为连续编号 5.11～5.14 | `11-mobile-llm-dvfs-energy.md`～`14-cpu-cache-friendly-code-data-layout.md` |
| `20-genai-app-integration-performance.md` / `5.30-android17-ondevice-intelligence-framework-performance.md` | 合并 AICore/ML Kit 与 OEM ODI 的公开范围、进程调度、资源归属和观测边界并改为 5.15 | `../src/part1-fundamentals/ch05-cpu-power/15-genai-app-integration-performance.md` |
| `22-bluetooth-le-audio-performance.md` / `5.23-android17-background-audio-hardening-leaudio-power-source.md` | Android 17 后台音频 hardening 并入 5.7；LE scan/offload/HFP 边界并入 LE Audio 主文并改为 5.16 | 5.7、`../src/part1-fundamentals/ch05-cpu-power/16-bluetooth-le-audio-performance.md` |
| `24-android17-app-hibernation-performance.md` | 主题独立，改为连续编号 5.17 | `../src/part1-fundamentals/ch05-cpu-power/17-android17-app-hibernation-performance.md` |
| `5.21-cross-app-agent-system-primitive.md` | 从 CPU/Power 移出；合并 Accessibility、VoiceInteraction 与 AppFunctions 的选择边界 | `../src/part4-system/ch16-aosp/11-agent-native-os.md` |
| `5.24-android17-binder-sz4m-kernel-buffer-pool-priority-set-called-dedup.md` | 删除已标记 outdated 的迁移壳；Binder 唯一正文不变 | `../src/part1-fundamentals/ch01-architecture/1.44-android17-binder-sz4m-kernel-buffer-pool.md` |
| `5.33-android17-performance-score-attribution-sourcecode.md` | 删除重复评分与样本池稿；保留 ADPF/headroom 主文和第 26 章唯一评分正文 | 5.9、`../src/part5-app/ch26-observability/18-app-performance-score.md` |

章节 README、`src/SUMMARY.md`、活动跨章链接和自动化脚本映射已经切换到连续编号。历史 changelog、已关闭 finding、queue/source 索引与 `consolidated_from` 保留旧路径；原 README 中两个从未存在的 5.18/5.22 链接已移除。

## ch04 内存管理

保留后的连续编号为：

- 4.1 Android 内存模型全景
- 4.2 Linux 内核内存管理
- 4.3 ART 虚拟机内存管理
- 4.4 系统内存压力与 lmkd
- 4.5 App 内存优化与诊断
- 4.6 16 KB Page Size 与 Android 性能
- 4.7 ART 分代 GC、Region 碎片与暂停分析
- 4.8 ART FinalizerDaemon、Cleaner 与 ReferenceQueue
- 4.9 ART HeapTask 调度、启动维护与冻结边界
- 4.10 内存规整与直接回收性能边界
- 4.11 Cached App Freezer、外部页回收与 GC 边界
- 4.12 ZRAM 压缩交换与应用重启延迟
- 4.13 Android 17 MemoryLimiter：memcg 限制与超限诊断
- 4.14 onTrimMemory 回调与 ART Heap Trim
- 4.15 Android 17 ARM MTE 内存标签扩展实战
- 4.16 跨进程内存共享与端侧推理预算
- 4.17 产品侧内存预取与 lmkd 边界

合并映射：

| 原正文 | 处理结果 | 当前承载位置 |
| --- | --- | --- |
| `06-memory-evolution.md` | 删除横向版本概览；ART、Bitmap/Scudo、16 KB、MTE、MemoryLimiter 与 MGLRU 的版本边界回到各自机制主文 | 4.2、4.3、4.5、4.6、4.7、4.13、4.15 |
| `13-anon-vma-lazy-memory-optimization.md` | 合并提案事实核查、公开 tag 边界和厂商验证方法 | `../src/part1-fundamentals/ch04-memory/02-linux-memory.md` |
| `16-art-tlab-object-allocation-performance.md` | 合并 TLAB、RosAlloc thread-local run、slow path 与 allocation profiling | `../src/part1-fundamentals/ch04-memory/03-art-memory.md` |
| `15-psi-lowmemdetector-lmkd-architecture.md` / `4.36-android17-lmkd-procs-prio-batch.md` / `4.50-lmkd-v2-psi-tiered-pressure-governance.md` | 合并 PSI、批量控制协议、thrashing、kill reason 与不存在的版本化命名事实核查 | `../src/part1-fundamentals/ch04-memory/04-lmk.md` |
| `4.35-android17-cpu-cache-locality-pss-accounting.md` / `4.36-android17-advanced-memory-optimization.md` | 合并 PSS 与 cache locality 的层级边界、Perfetto 数据源和分阶段诊断方法 | `../src/part1-fundamentals/ch04-memory/05-app-memory-optimization.md` |
| `07-16kb-page-size.md` / `08-art-generational-gc.md` / `09-finalizer-referencequeue.md` / `21-art-heaptask-scheduling-pipeline.md` | 主题独立，依次改为连续编号 4.6～4.9 | `06-16kb-page-size.md`～`09-art-heaptask-scheduling-pipeline.md` |
| `14-art-gc-region-fragmentation-compaction.md` | 合并 Region 碎片、CC evacuation 与 CMC/UFFD compaction 边界 | `../src/part1-fundamentals/ch04-memory/07-art-generational-gc.md` |
| `04.20-android17-memory-compaction-freezer-performance-impact.md` | 合并 app compaction profile、memcg reclaim、监控口径与 freezer 事件 | `../src/part1-fundamentals/ch04-memory/11-cached-app-freezer-gc-boundary.md` |
| `4.18-android-17-memorylimiter-深度解析.md` | 主题独立，改为 4.13；删除对不存在 4.17 配套正文的依赖 | `../src/part1-fundamentals/ch04-memory/13-android17-memorylimiter.md` |
| `04.18-android17-ontrimmemory-source-fair-adaptation.md` / `4.49-android17-trim-memory-api-evolution.md` | 合并 framework trim dispatch、应用回调与 ART HeapTrimTask | `../src/part1-fundamentals/ch04-memory/14-ontrimmemory-art-heap-trim.md` |
| `4.9-android17-memory-tagging-extension-mte.md` | 主题独立，改为连续编号 4.15 | `../src/part1-fundamentals/ch04-memory/15-android17-memory-tagging-extension-mte.md` |
| `4.22-android17-ai-agent-memory-sandboxed-data-reuse.md` | 改为 4.16，并以平台存在的跨进程共享与端侧推理预算为标题 | `../src/part1-fundamentals/ch04-memory/16-cross-process-memory-ai-inference.md` |
| `4.5-appflow-lmkd-compatibility.md` / `4.04-AppFlow与Android-17-LMKD兼容性方案.md` | 合并为产品侧预取方案的权限、预算、降级与 lmkd/MemoryLimiter 边界 | `../src/part1-fundamentals/ch04-memory/17-product-prefetch-lmkd-boundary.md` |

章节 README、`src/SUMMARY.md`、活动跨章链接和自动化脚本映射已经切换到连续编号。历史 changelog、已关闭 finding 与 `consolidated_from` 保留旧路径。

## ch03 输入系统

保留后的连续编号为：

- 3.1 Input 事件分发：队列、反压与丢弃
- 3.2 触摸延迟、预测与低延迟渲染
- 3.3 手势导航与系统交互
- 3.4 输入事件拦截与安全机制
- 3.5 手势识别算法与性能优化
- 3.6 InputMethodManager 与软键盘性能
- 3.7 Predictive Back 系统架构与动画管线性能
- 3.8 键盘、鼠标与指针输入性能

合并映射：

| 原正文 | 处理结果 | 当前承载位置 |
| --- | --- | --- |
| `04-input-latency-prediction.md` | 合并 MotionPredictor、前缓冲、Perfetto 量化和手写组合方案 | `../src/part1-fundamentals/ch03-input/02-touch-performance.md` |
| `07-inputdispatcher-backpressure.md` | 合并 `iq/oq/wq`、`WOULD_BLOCK`、无响应隔离和队列裁剪 | `../src/part1-fundamentals/ch03-input/01-input-dispatch.md` |
| `08-inputflinger-rust-arr.md` | Rust Bounce/Slow/Sticky Keys 归入外设输入；interaction boost 与 ARR 测量边界归入触摸延迟，完整 ARR 仍由 2.18/2.19 承载 | 3.8、3.2、2.18、2.19 |
| `09-input-latency-budget-perception.md` | 合并四种延迟口径、阶段预算、HCI 研究边界和 FrameTimeline high-latency state | `../src/part1-fundamentals/ch03-input/02-touch-performance.md` |
| `10-inputdispatcher-stale-event.md` | 合并 stale policy、进行中 stroke 豁免、合成 CANCEL 和 drop reason 优先级 | `../src/part1-fundamentals/ch03-input/01-input-dispatch.md` |
| `05-input-interception-security.md` / `06-gesture-recognition-performance.md` | 主题独立，改为连续编号 3.4 / 3.5 | `04-input-interception-security.md` / `05-gesture-recognition-performance.md` |
| `11-input-method-manager-performance.md` / `12-predictive-back-system-architecture.md` | 主题独立，改为连续编号 3.6 / 3.7 | `06-input-method-manager-performance.md` / `07-predictive-back-system-architecture.md` |
| `13-keyboard-mouse-pointer-input-performance.md` | 改为 3.8，并吸收 Rust 键盘 filter | `08-keyboard-mouse-pointer-input-performance.md` |
| `参考资料.md` | 删除重复参考索引页；固定 tag 入口保留在章节 README 和各主题参考资料 | `../src/part1-fundamentals/ch03-input/README.md` |

活动跨章链接、`src/SUMMARY.md` 和 changelog 映射已切换到新编号与路径。历史审计记录和关闭 finding 中的旧路径按维护规则保留。

## ch06 存储与 I/O

保留后的连续编号为：

- 6.1 Android 存储架构
- 6.2 文件系统
- 6.3 I/O 调度与性能
- 6.4 SharedPreferences 与 DataStore：I/O、ANR 与多进程一致性
- 6.5 vold、MediaProvider 与 FUSE：共享存储 I/O 路径

合并映射：

| 原正文 | 处理结果 | 当前承载位置 |
| --- | --- | --- |
| `04-storage-evolution.md` | 删除独立概览；文件系统、UFS、FUSE 等版本信息回到对应主题 | 6.1、6.2、6.5；既有 1.9 与 24.13 保留 IncFS、Photo Picker 专题 |
| `05-sharedpreferences-datastore.md` | 改为连续编号 6.4，并吸收两篇重复正文 | `04-sharedpreferences-datastore.md` |
| `6.03-Android-17-SharedPreferencesImpl-ANR机制.md` | 合并 SP 加载、QueuedWork 与 ANR 机制 | `04-sharedpreferences-datastore.md` |
| `6.1-androidx-datastore--ipc-源码级验证-draft.md` | 合并多进程 DataStore 的锁、通知与一致性边界 | `04-sharedpreferences-datastore.md` |
| `06-vold-fuse-scoped-storage-io.md` | 改为连续编号 6.5，并吸收 FUSE 内核专题 | `05-vold-mediaprovider-fuse.md` |
| `07-fuse-bpf-scoped-storage-io-performance.md` | 合并 passthrough、iomode、FUSE BPF 和 tracepoint | `05-vold-mediaprovider-fuse.md` |
| `6.19-linux-6.10-内存碎片整理机制.md` | 从存储章移出，合并内核主动规整机制 | `../src/part1-fundamentals/ch04-memory/10-memory-compaction-direct-reclaim.md` |
| `6.20-linux-6-10-memory-compaction-optimization.md` | 从存储章移出，合并调参与实验方法 | `../src/part1-fundamentals/ch04-memory/10-memory-compaction-direct-reclaim.md` |
| `ch06-storage.md` | 删除重复路由页 | `../src/part1-fundamentals/ch06-storage/README.md` |

活动引用和生成脚本已经切换到新路径。历史审计记录中的旧路径按维护规则保留。
