# AIW 自动 Review 任务报告

## 一、目标发现结果
- 扫描范围：`src/part3-tools/ch14-other-tools/10-ebpf-performance-analysis.md`
- 候选章节：`14.10 eBPF/BPF 在 Android 性能分析中的应用`
- 最终选择：`14.10 eBPF/BPF 在 Android 性能分析中的应用`
- 选择理由：eBPF 属于前沿深水区，该章节涉及大量 Linux Kernel 特性，需进行内核级准确性复核。

## 二、总体结论
- 总体技术评分：4.5/5
- 是否建议回炉：否（但建议进入队列做 P1 增补）
- 主要风险：对 bpftrace 在 Android 的可用性判断略有偏差。
- 评分理由：本章极其前沿且干货满满（Simpleperf uprobe/kprobe 结合 eBPF、Android 15 UprobeStats、Kernel 6.12 sched_ext）。概念非常精准，代码示例直接可用，是极高水平的技术产出。
- 闭环建议：根据 P1 补充 AOSP 内置 bpftrace 的说明。
- 本轮 review 覆盖范围：系统级 eBPF, Simpleperf uprobe/kprobe, UprobeStats, sched_ext 架构。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 4.5/5 | 0 |
| 原理链完整性 | 5.0/5 | 0 |
| 版本差异覆盖 | 4.5/5 | 1 |
| 知识盲区 | 4.0/5 | 1 |
| 数据/案例支撑 | 4.5/5 | 0 |
| 交叉引用一致性 | 4.5/5 | 0 |

## 四、P0 问题（事实错误）
（无）

## 五、P1 问题（重要缺失）
- [P1][版本差异覆盖/知识盲区][bpftrace 的可用性]
- **原文问题**："bpftrace 不是 Android 标准工具链的一部分，需要在设备上单独编译安装"。
- **核验结论**：自 Android 12/13 开始，AOSP `external/bpftrace` 已经引入了 bpftrace。在 userdebug/eng 版本上，可以通过 `m bpftrace` 编译并在设备上运行，甚至部分 userdebug 固件中可能已自带。
- **建议补充方向**：修正关于 bpftrace 完全不是标准工具链的表述，明确它已作为 external 项目存在于 AOSP，并在 userdebug 研发阶段相对容易获取。

- [P1][版本差异覆盖][Android GKI 版本]
- **原文问题**："Android 17 GKI 是否正式包含 Kernel 6.12"。
- **核验结论**：Android 15 的 GKI 基于 6.6。根据 Google GKI 发布节奏，Android 16 预期包含 6.12，Android 17 通常会跨越到下一个长期支持版本（如 6.14）或者继续提供 6.12。
- **建议补充方向**：可以明确 Kernel 6.12 作为 LTS 是后续 Android 16/17 GKI 的核心选项，说明 sched_ext 进入 Android 生态的必然性。

## 六、P2 问题（建议改进）
- [P2][原理链完整性][UprobeStats 的开销]
- **原文问题**：UprobeStats 工作原理。
- **建议**：可以简单提一句 UprobeStats 中 eBPF 程序通过 RingBuf 将数据送给用户态 Collector 时，如果是高频触发的方法，RingBuf 可能会丢失事件 (drop) 以保护内核性能。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|----------|--------------|
| bpftrace 在 AOSP 的集成现状 | 中 | 查阅 `external/bpftrace` 在 Android 14/15 的编译支持和系统预置情况 |

## 八、外部核验建议
- 搜索关键词：`AOSP external/bpftrace`

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
（无 P0，P1 建议补充即可）

### 9.3 一般建议清单（非阻断）
- **章节**：14.10
- **问题描述**：修正关于 bpftrace 在 Android 上不可用的绝对表述。
- **建议**：补充说明 AOSP `external/bpftrace` 项目，并指出在 userdebug 环境下编译和使用 bpftrace 的标准路径。

### 9.4 可复用知识资产（高价值新增知识）
- **章节**：14.10
- **可复用的技术结论**：Simpleperf 结合 uprobe/kprobe 追踪 RenderThread `eglSwapBuffers`、锁竞争、系统调用的命令行示例，极其具备实战指导意义，可作为工具速查手册。