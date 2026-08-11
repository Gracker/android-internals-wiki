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
| 其余 25 章 | 610 | 待审阅 | 未开始 | - |

当前规范正文总数为 615 篇。这里的“已完成”表示该章每篇正文均已阅读并完成本轮结构收敛，不代表所有技术结论都已达到发布状态。

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
