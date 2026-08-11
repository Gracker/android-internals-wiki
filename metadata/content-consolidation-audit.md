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
| 其余 22 章 | 529 | 待审阅 | 未开始 | - |

当前规范正文总数为 576 篇。这里的“已完成”表示该章每篇正文均已阅读并完成本轮结构收敛，不代表所有技术结论都已达到发布状态。

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
| `5.21-cross-app-agent-system-primitive.md` | 从 CPU/Power 移出；合并 Accessibility、VoiceInteraction 与 AppFunctions 的选择边界 | `../src/part4-system/ch16-aosp/12-agent-native-os.md` |
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
