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
| 其余 24 章 | 596 | 待审阅 | 未开始 | - |

当前规范正文总数为 609 篇。这里的“已完成”表示该章每篇正文均已阅读并完成本轮结构收敛，不代表所有技术结论都已达到发布状态。

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
