---
title: "Trace 采集可靠性与可复现诊断"
chapter: "13.22"
status: finalized
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: ["Perfetto", "Data Explorer", "v54", "性能分析", "数据可视化", "Trace Processor"]
related_chapters: ["13.2", "13.4", "13.13", "13.15"]
last_verified: "2026-08-13"
last_verified_against: "AOSP android-17.0.0_r1; Perfetto v54.0"
confidence: high
sources:
  - type: official
    path: "https://perfetto.dev/docs/"
  - type: blog
    path: "Perfetto数据流架构故障分析（CSDN, 2024-02）"
  - type: blog
    path: "系统级性能分析与调优 Systrace/Perfetto（微信公众号, 2026-04）"
  - type: aosp
    path: "external/perfetto/ (android-17.0.0_r1)"
---
# 13.22 Trace 采集可靠性与可复现诊断

> 平台基线是 Android 17 / API 37 / `android-17.0.0_r1`，工具基线是该平台 `external/perfetto` 中包含的 Perfetto v54.0。CUJ（Critical User Journey）是启动、滚动或页面切换等用户能直接感知的关键操作；界面操作、SQL 节点图与 Jank CUJ 指标口径见 [13.13 DataGrid、Data Explorer 与 Jank CUJ](13-perfetto-data-explorer-jank-cuj.md)。

---

## 1. 先判断 trace 能不能支撑结论

性能分析常从时间线开始，却可能在采集阶段就失去可信度：内核调度事件被覆盖、producer 的共享内存写满后丢包、结束 flush 失败，或 ring buffer（写满后覆盖最早内容的环形缓冲区）已经冲掉问题发生前的数据。producer 是生成 trace 数据的进程，flush 是要求它提交仍暂存在本地缓冲区中的数据。Trace Processor 能打开文件，只说明文件可解析，不能证明事件完整。

诊断采用一条固定顺序：

1. 明确要回答的问题和所需数据源；
2. 估算数据率，设置 ftrace（Linux 内核事件追踪机制）、共享内存和 central buffer（tracing service 管理的会话缓冲区）；
3. 采集后检查 `stats` 与时间范围；
4. 通过完整性检查后，再做 Data Explorer、PerfettoSQL 或 metric（按固定定义计算的性能指标）分析；
5. 保存配置、工具版本、SQL 与原始 trace，供同事复核。

这套顺序对 UI 卡顿、启动、ANR（Application Not Responding，应用无响应）、功耗和内存分析都适用。不同场景的配置可以不同，数据完整性检查不应省略。

## 2. Android 17 上的数据流

### 2.1 四个角色

Perfetto 的系统采集路径可分成四个角色。data source 是可被会话启用的一类数据能力，producer 承载 data source 并生成数据；consumer 负责配置、读取或停止会话。

| 角色 | Android 上的常见实例 | 职责 |
| --- | --- | --- |
| Producer / data source | 应用中的 Track Event、`traced_probes` 托管的 ftrace/process stats 等 | 生成 `TracePacket` 数据包 |
| 共享内存缓冲区（SMB） | 每个 producer 与 tracing service 之间的一对一暂存区 | 让高频写入路径直接序列化，吸收 service 短时调度延迟 |
| Tracing service | `traced` | 把 producer 的 chunk（SMB 中的一块连续写入区）复制到会话 central buffer，处理 flush、触发与输出 |
| Consumer / 分析端 | `perfetto` CLI、Perfetto UI、`trace_processor_shell` | 配置和读取会话，或在采集后解析 trace |

`traced_probes` 与 `traced` 是两个职责不同的进程。前者承载 ftrace、进程统计等系统探针，后者是 tracing service。producer/service 控制通道使用 Perfetto IPC（进程间通信协议）；Android system backend 通常通过 Unix domain socket（本机进程通信端点）连接，不走 Binder 调用。

Trace Processor 不位于设备的采集 hot path（调用频繁且对延迟敏感的路径）中。它在采集后读取 trace，把 protobuf（Protocol Buffers 序列化格式）packet 解析成 `slice`、`sched_slice`、`thread`、`process` 等表，再加载 PerfettoSQL 标准库与 metric。

### 2.2 三层 buffer 不能混为一谈

启用 `linux.ftrace` 时，数据通常经过三类 buffer：

```text
kernel per-CPU ftrace buffer
  → traced_probes 所在 producer 的 SMB
  → traced 会话的 central buffer
  → trace 文件或 consumer
```

每一层解决的问题不同：

- ftrace buffer 位于内核，每个 CPU 各有一份；`traced_probes` 周期读取；
- SMB 是 producer 与 service 共享的短期暂存区，每个 producer 进程一份；
- central buffer 由 `TraceConfig.buffers` 定义，可接收多个 producer 和 data source 的 packet，最终在会话结束或流式写入时输出。

把 `TraceConfig.buffers.size_kb` 调大，只会扩大 central buffer；它不会同步扩大内核 ftrace buffer 或 SDK producer 的 SMB。ftrace 使用 `ftrace_config.buffer_size_kb`，SDK producer 可通过 `TracingInitArgs.shmem_size_hint_kb` 等初始化参数请求 SMB 大小。三层容量必须分别评估。

### 2.3 一个 packet 如何到达 central buffer

producer 中的 `TraceWriter` 取得一个 SMB chunk 后，通过 ProtoZero（Perfetto 的低开销 protobuf 写入库）直接序列化数据。chunk 写满或被主动提交后，producer 发送异步 IPC；service 把已提交 chunk 复制到 central buffer，再把 SMB 空间交还 producer。page 是 SMB 的固定大小内存页，一个 page 可以按布局分成多个 chunk。

共享内存 ABI（producer 与 service 都必须遵守的二进制内存布局约定）中的 chunk 状态为：

| 状态 | 含义 |
| --- | --- |
| `Free` | producer 可以取得并开始写入 |
| `BeingWritten` | producer 正在写，service 不应改动状态 |
| `Complete` | producer 已完成写入，service 可以取得该 chunk |
| `BeingRead` | service 正在复制，完成后转回 `Free` |

一个 `TracePacket` 可以跨越多个 chunk，每一段称为 fragment（分片）；protobuf 的长度字段也可能要等整段消息写完后才能确定。v54 协议用 `CommitDataRequest.ChunkToPatch` 等机制修补已提交 chunk 中预留的长度字段。读取端会按 `{ProducerID, WriterID, ChunkID}` 顺序重组 fragment：只有链条完整且待写字段已经 patch（回填）后，才把它作为完整 packet 输出；遇到缺口时会标记数据丢失，不能把残片当作有效 packet。

这种完整 packet 输出规则不保证每个 packet 都能保留。SMB 耗尽、central ring buffer 覆盖或读取不及时，仍可能丢失整个 packet、连续多个 packet，甚至让同一 writer 的后续序列暂时无法解析。

## 3. 顺序、flush 与增量状态

### 3.1 文件顺序不是全局时间顺序

一个 `TraceWriter` sequence 是同一 writer 按顺序生成的一串 packet，该序列内部保持写入顺序。多个 writer 会并发提交，因此 trace 文件中的 packet 不保证按全局时间戳排列；Trace Processor 导入时会在排序窗口内按时间整理事件。

低频 data source 可能长时间没有填满 SMB page。若没有 flush，一条较早的事件可能在数分钟后才提交，与其他序列的新事件混在文件后部。长 trace 的乱序跨度超过导入器的排序窗口时，可能出现 out-of-order（事件到达次序与时间戳次序不一致）警告或解析问题。

`flush_period_ms` 会周期性向所有 data source 发出 flush 请求，让它们提交尚未送达 service 的数据，从而缩小乱序窗口。v54 的 `TraceConfig` 明确提示高频 flush 会增加 producer 与 service 开销；普通采集不应只为追求更低延迟而设置成毫秒级。

导入旧 trace 时若已经遇到超大乱序窗口，可让 shell 使用完整排序：

```bash
./trace_processor_shell \
  --full-sort \
  trace.perfetto-trace
```

`--full-sort` 会提高导入内存占用。它只能改变解析排序策略，不能找回采集时已经丢失的数据。

### 3.2 环形覆盖为何会破坏后续解释

Track Event 常通过 string interning（把重复字符串登记一次并分配整数 ID）压缩数据，后续 packet 只引用 ID。`linux.process_stats` 也可能先记录线程与进程的对应关系，后续 ftrace packet 再引用 TID（线程 ID）。若 ring buffer 覆盖了较早的映射，保留下来的事件就可能缺少解释后续 ID 所需的 incremental state（增量状态）。

Trace Processor 会检测部分无效增量状态，并跳过依赖缺失 interned data 的 packet。结果未必只是名称为空：整段 sequence 都可能无法进入分析表。

两种常用缓解方式是：

- 设置 `incremental_state_config.clear_period_ms`，让支持该协议的 data source 周期重置增量状态并重新发出描述；
- 把低频、但决定解释关系的数据源放入单独 target buffer（指定的 central buffer 下标），减少被高频 ftrace 数据覆盖的机会。

`clear_period_ms` 不是所有 data source 的强制刷新开关。只有声明 `handles_incremental_state_clear` 的 data source 会响应；周期越短，重复描述带来的数据量和开销越高。

## 4. 数据完整性检查

### 4.1 不要只看 `severity = 'data_loss'`

`stats` 表汇总 trace 自带的采集统计和 Trace Processor 导入时发现的问题。`severity` 是严重程度，`source` 标明问题来自采集记录还是分析阶段，`idx` 用来区分 CPU 或 buffer。下面的查询列出 severity 为 data loss 或 error 的非零统计：

```sql
SELECT
  name,
  idx,
  severity,
  source,
  value,
  description
FROM stats
WHERE
  severity IN ('data_loss', 'error')
  AND value > 0
ORDER BY
  severity,
  name,
  idx;
```

它能捕获 `ftrace_cpu_has_data_loss`、`traced_buf_trace_writer_packet_loss`、`traced_final_flush_failed`，以及 severity 同为 `data_loss` 的 `misplaced_end_event` 等关键项。不过，v54 的 `traced_buf_chunks_overwritten`、`traced_buf_chunks_discarded` 和 `ftrace_cpu_overrun_delta` 在 `stats.h` 中仍标为 `info`。该查询返回空时，仍不能单独证明 central buffer 没有覆盖或 ftrace 没有 overrun（内核事件生成速度超过读取速度）。

下面的第二条查询专门查看 central buffer 容量与写入状态。其中 `traced_buf_bytes_written` 是正常写入量，用来理解数据规模，不表示发生错误：

```sql
SELECT
  name,
  idx AS buffer_index,
  severity,
  value,
  description
FROM stats
WHERE
  name IN (
    'traced_buf_chunks_overwritten',
    'traced_buf_chunks_discarded',
    'traced_buf_bytes_overwritten',
    'traced_buf_bytes_written',
    'traced_buf_trace_writer_packet_loss',
    'traced_buf_patches_failed'
  )
  AND value > 0
ORDER BY
  buffer_index,
  name;
```

`idx` 对 central buffer 统计通常是 buffer 下标，对 ftrace 统计通常是 CPU 下标。报告问题时应保留 `idx`，它能定位发生异常的 buffer 或 CPU。分析 ftrace 时还应按名称查看 `ftrace_cpu_overrun_delta`，并与同一 CPU 的 `ftrace_cpu_has_data_loss` 对照。

### 4.2 关键统计怎么解释

| 统计项 | 表示什么 | 优先检查 |
| --- | --- | --- |
| `ftrace_cpu_has_data_loss` | 指定 CPU 的内核 ftrace buffer 在用户态读取前覆盖了事件 | 减少 ftrace 事件、增大 `buffer_size_kb`、确认读取调度 |
| `ftrace_cpu_overrun_delta` | 采集区间内的 ftrace overrun 计数差，即内核覆盖了尚未读取的事件 | 与 `ftrace_cpu_has_data_loss` 和 CPU 下标一起看 |
| `traced_buf_trace_writer_packet_loss` | service 在指定 target buffer 中观察到 writer 丢包 | producer 突发写入、SMB 大小与等待（stall）/丢弃（drop）策略 |
| `traced_buf_chunks_overwritten` | `RING_BUFFER` 中旧 chunk 被新数据覆盖 | central buffer 容量、采集时长、数据率 |
| `traced_buf_chunks_discarded` | `DISCARD` 满后拒收新 chunk | central buffer 容量、是否选错 fill policy |
| `traced_buf_patches_failed` | 跨 chunk packet 的 patch 失败，可能丢数据；若 `DISCARD` 已满且有 discarded chunk，失败可能只是被拒收数据的后果 | 同 buffer 的 discard 与 packet loss |
| `traced_final_flush_failed` | 会话结束时至少一个 producer 或 data source 未在超时内完成 flush | producer 状态、超时与 trace 尾部可信度 |
| `traced_buf_incremental_sequences_dropped` | 缺少有效增量状态而丢弃 sequence | 环形覆盖、clear 周期、target buffer 划分 |
| `misplaced_end_event` | 解析 slice 时遇到无法配对的 end；v54 将它标为 `data_loss` | 插桩是否配对；其 `source` 是 analysis |

`source = 'trace'` 指向 trace 自带的采集统计，`source = 'analysis'` 表示导入或建表阶段发现的问题。前者通常要调整采集配置或 producer，后者还可能来自插桩配对、文件内容或分析器版本。

### 4.3 “有丢失”之后还能不能分析

能否继续分析取决于损失所在的 CPU、buffer、时间段和数据源：

- 目标是主线程锁等待，而目标 CPU 的 sched 事件有丢失，调度因果不能下强结论；
- 只分析一个应用 Track Event 区间，而丢失发生在无关 target buffer，结论可能仍可用；
- ring buffer 有覆盖，但所需窗口完整保留且增量状态有效，可以限定时间范围继续；
- 结束 flush 失败时，trace 尾部事件可能缺失，不能把“没看到结束”解释成“操作没有结束”。

报告中应明确写出损失项、下标、数值及它可能影响的结论。重采成本较低时，应先修正配置并重新采集。

## 5. 用数据率计算 buffer，不背固定数值

### 5.1 Central buffer

非流式采集近似满足：

```text
可保留时长 ≈ central buffer 字节数 ÷ 聚合写入速率
```

MiB 是二进制容量单位，1 MiB 为 1,048,576 字节。例如所有 producer 合计写入约 2 MiB/s，32 MiB buffer 只能保存约 16 秒。fill policy（写满后的处理策略）为 `RING_BUFFER` 时保留靠近结束的窗口，较早数据会被覆盖；`DISCARD` 则保留开头，满后拒绝新数据。v54 配置中的枚举名是 `RING_BUFFER` 与 `DISCARD`，没有 `STOP_WHEN_FULL`。

写入速率与设备负载、CPU 数、启用事件和应用插桩量相关。syscall（系统调用）、page fault（缺页异常）、Binder 事务或大量应用 trace point（代码观测点）都可能让速率提高一个数量级。估算值只用于选择初始配置，采集后还要用 buffer 统计校正。

### 5.2 Ftrace per-CPU buffer

内核 ftrace buffer 需要容纳两次读取之间每个 CPU 产生的事件。影响它的配置是：

- `ftrace_config.buffer_size_kb`：每 CPU buffer 的目标大小；
- `ftrace_config.drain_period_ms`：`traced_probes` 读取周期；
- `ftrace_events` 与 atrace category：决定事件率。

减少 `drain_period_ms` 能降低覆盖风险，但会增加唤醒和读取开销。增大 `buffer_size_kb` 会按 CPU 数增加内核内存占用。两者都应由 `ftrace_cpu_has_data_loss` 与实际负载来调整。

### 5.3 Producer SMB

SMB 要吸收 producer 的峰值写入，而非平均值。一个 data source 每 10 秒写一个 2 MiB packet，平均只有 0.2 MiB/s，但瞬时连续序列化的速度可能远高于平均值，仍会耗尽较小的 SMB。

可选方向包括：

- 提高 producer 的 SMB size hint（请求的共享内存容量）；
- 把大 payload（packet 承载的数据内容）分段并避免瞬时连续写入；
- SDK data source 在业务允许时使用 `BufferExhaustedPolicy::kStall`。

自定义 SDK data source 的默认策略是 `kDrop`，SMB 无空闲 chunk 时丢弃 trace 数据。`kStall` 会让写入线程等待空闲 chunk，数秒后仍无空间时还会中止 producer 进程；它可能显著改变时序，也有可用性风险。性能敏感路径通常更重视低扰动，应保留 `kDrop`，再用 stats 明确标记 trace 不完整。只有“丢数据比阻塞或进程终止更危险”的专用采集，才适合评估 `kStall`。

## 6. 一份可解释的 Android 17 短 trace 配置

下面这份 pbtxt（protobuf text format，protobuf 的文本配置格式）面向约 15 秒的 UI 调度观察。数值只作为起始点，仍需根据目标设备的 stats 和实际数据率校正：

```protobuf
buffers {
  size_kb: 65536
  fill_policy: RING_BUFFER
}

buffers {
  size_kb: 4096
  fill_policy: RING_BUFFER
}

duration_ms: 15000

data_sources {
  config {
    name: "linux.ftrace"
    target_buffer: 0
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_waking"
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "power/suspend_resume"

      atrace_categories: "gfx"
      atrace_categories: "view"
      atrace_categories: "wm"
      atrace_categories: "am"
      atrace_apps: "com.example.app"

      buffer_size_kb: 8192
      drain_period_ms: 250
    }
  }
}

data_sources {
  config {
    name: "linux.process_stats"
    target_buffer: 1
    process_stats_config {
      scan_all_processes_on_start: true
    }
  }
}
```

`target_buffer` 使用从 0 开始的下标，把 data source 指向前面声明的 central buffer。高频 ftrace 写入 buffer 0，低频进程映射放在 buffer 1，可降低映射被调度事件覆盖的概率。`scan_all_processes_on_start` 会在会话启动时扫描全部进程，有助于建立初始进程/线程关系，也会增加采集量。

`ftrace_config.buffer_size_kb` 是每 CPU 的请求大小；8192 KiB 在 8 核设备上的名义总量约为 64 MiB。存在并发 ftrace 会话时，内核缓冲区不能随意暂停并重设，实际大小未必等于请求值。多数 v43 及更高版本配置可以先保留默认值；确需调优时，应结合设备 CPU 数、内存限制与 `ftrace_cpu_has_data_loss` 验证。15 秒短采集通常可依赖停止会话时的 final flush，因此示例没有默认加入周期 flush 和增量状态清除。

该配置没有罗列 Binder、IRQ（硬件中断）、workqueue（内核工作队列）、CPU idle、内存和 heap profiling（堆内存采样与分析）等所有数据源。应先写出诊断问题，再加入能回答该问题的事件。若 UI 卡顿分析需要 Binder 调用关系，可补充 Binder ftrace；若只关心应用 slice，就不应默认开启高频 syscall。

### 6.1 采集后要保存什么

每次可复核采集至少保存：

- 完整 pbtxt 配置；
- Android build fingerprint（唯一标识系统构建版本的一串属性值）或明确的 `android-17.0.0_r1` 构建标识；
- `trace_processor_shell --version` 输出；
- 原始 trace 文件；
- 数据完整性查询结果；
- 用于计算最终数字的 SQL 或 metric 命令；
- 操作步骤和观察时间窗口。

只保存 Perfetto UI 截图，会丢掉单位、过滤条件、工具版本与缺失数据提示，其他人也无法重新执行查询。

## 7. 长 trace：文件流式写入与 v54 flush 策略

### 7.1 `write_into_file` 解决 central buffer 容量问题

长 trace 若只在结束时读取 central buffer，容量必须覆盖整个目标时段，否则就要接受 ring 覆盖。`write_into_file: true` 让 service 周期性地从 central buffer 读取并写入文件，buffer 主要承载两个写周期之间的数据峰值。它解决内存保留时长问题，仍需确保写文件速度跟得上数据生成速度。

下面片段展示 v54 的相关字段：

```protobuf
write_into_file: true
file_write_period_ms: 5000
max_file_size_bytes: 1073741824
write_flush_mode: WRITE_FLUSH_AUTO
```

`file_write_period_ms` 控制写文件周期，`max_file_size_bytes` 达到上限时会停止 tracing。若配置 `output_path`，Android system `traced` 只允许使用 `/data/misc/perfetto-traces/` 下尚不存在的文件；更常见的 CLI 方式是由 consumer 传入 file descriptor（操作系统用来引用已打开文件的整数句柄）。

### 7.2 v54 的 `write_flush_mode`

v54 用 `write_flush_mode` 替换已移除的 `no_flush_before_write_into_file`。三种有意义的模式为：

| 模式 | 行为 |
| --- | --- |
| `WRITE_FLUSH_AUTO` | 默认；根据 file write period 自动决定 flush 频率 |
| `WRITE_FLUSH_DISABLED` | 周期写文件前不强制 flush；允许较新数据暂留 SMB |
| `WRITE_FLUSH_ENABLED` | 每次周期写前都 flush；数据更新更及时，开销更高 |

在 AUTO 下，`file_write_period_ms <= 5s` 时不会每次写都 flush，而是每 5 秒发起一次周期 flush；write period 大于 5 秒时，每次写文件前 flush。这个规则来自 v54 `TraceConfig` 注释，脚本迁移时不应继续使用已经移除的旧字段。

`fflush_post_write: FFLUSH_ENABLED` 会在每轮写入后执行存储同步。字段名虽然含 `fflush`，v54 在 Android/Linux 的实现实际调用 `fdatasync()`，把文件数据从内核缓存同步到存储；这能减少进程或系统崩溃时尚未持久化的数据，同时增加 I/O 延迟与写放大。它不能承诺任何硬件掉电场景都绝对无损，一般性能采集也不应默认开启。

## 8. 诊断流程：从问题窗口到证据

### 8.1 UI 卡顿

建议按下面的顺序检查：

1. 确认 trace 的 ftrace、FrameTimeline、应用 atrace 和进程映射没有关键丢失；
2. 在 timeline（按时间排列事件的视图）或 CUJ 表确定异常帧和时间窗口；
3. 分开判断 app missed（应用未按期提交帧）与 SurfaceFlinger missed（系统合成未按期完成）；
4. 检查 UI thread、RenderThread 的 `thread_state` 与 `sched_slice`；
5. 对 Runnable 时间检查 CPU 竞争、优先级与频率；
6. 对 sleeping/blocking 时间检查 binder、锁、I/O 和回调；
7. 对 GPU/合成问题检查 FrameTimeline、SurfaceFlinger 与图形数据；
8. 把候选原因与正常帧对照，确认差异可重复。

Running 表示线程正在 CPU 上执行，Runnable 表示线程具备运行条件却还在调度队列中等待；wall duration 是从开始到结束的现实经过时间，包含运行、调度等待、阻塞和睡眠。一个帧超过预算，可能是线程没有及时获得 CPU，也可能是获得 CPU 后执行过多，还可能在 Binder 或 fence（表示图形工作完成状态的同步原语）上等待。

### 8.2 应用启动

启动分析至少要区分：

- 进程是否已存在；
- 冷、温、热启动口径：冷启动时进程不存在；温启动时进程仍在，但 Activity 需要重建；热启动时 Activity 仍在内存中，只需恢复到前台；
- launcher 点击、ActivityTaskManager 处理、进程创建、Application、Activity 与首帧；
- 主线程 CPU 执行、调度等待、I/O、类加载和锁。

不要把某个 `slice.dur` 直接命名为完整启动时间。使用 Android startup metric 或 PerfettoSQL 标准库时，应先核对该 metric 对启动类型、起点和终点的定义，再用 slice 解释具体慢在哪里。

### 8.3 ANR

ANR 查询可从 `android_anrs` 获取事件时间、类型、`subject`（原因摘要）、`intent`（触发请求）与 `component`（目标组件），再回到时间线检查：

- 主线程当时处于 Running、Runnable、Sleeping 还是阻塞态；
- binder 调用链是否完整；
- 是否有 CPU starvation（线程长时间得不到足够 CPU）、锁竞争、I/O 或长回调；
- `traced_final_flush_failed` 是否让 trace 尾部缺失。

没有看到解锁、Binder reply（服务端返回事务结果）或回调结束，不足以证明它从未发生；应先排除尾部未 flush 与相关 buffer 丢失。

### 8.4 功耗

短时间高 CPU 与长期耗电不能画等号。功耗分析应对齐：

- CPU/GPU 频率，以及 idle state 与 residency（处理器在各空闲状态停留的时长）；
- suspend/wakeup；
- 进程或线程活动；
- 网络、定位、相机、音频等设备使用；
- 测量窗口和设备状态。

trace 只能解释已经采到的数据。没有设备功率计、fuel gauge（电池电量计）或 Wattson（基于设备模型估算功耗的 Perfetto/Android 分析能力）支持时，不能把调度时长直接换算成毫瓦时。

## 9. 插桩需要遵守的边界

应用 Track Event 或 atrace 名称应稳定、短小，并表达业务阶段。同步 begin/end 必须在同一线程和控制流上正确配对；异步操作应使用能够区分并发实例的 cookie（整数关联标识）或独立 track。

插桩前要评估：

- 高频循环是否产生过量事件；
- 动态名称是否产生大量 interned string（登记后以整数 ID 引用的字符串）；
- 是否把用户数据、URL、账号或业务内容写入 trace；
- release/user build（面向用户发布的生产构建）上是否允许该数据源；
- 关闭 tracing 时高频调用路径的开销是否可接受。

`misplaced_end_event` 增长时，应检查 begin/end 配对和线程迁移。用名称搜索到一段 slice，不代表异步任务边界一定正确。

## 10. 观测开销怎么评估

观测动作本身可能改变被测系统，这称为 probe effect（探针效应）。Tracing 会消耗 CPU、内存、I/O 和被观测进程时间，开销随配置变化，不能只引用一个“Perfetto 通常很低”的百分比。

建议做三组同场景重复测试：

1. 不采 trace 的基线；
2. 最小必要配置；
3. 候选完整配置。

比较业务指标的中位数和 tail（P90/P95/P99 等尾部结果）、设备温度、频率状态、掉帧，以及 `stats` 中的丢失项。若完整配置显著改变被测指标，应缩小事件集、降低 polling（定时读取状态）频率、缩短采集窗口或使用触发式采集。

对小于几毫秒的阶段，插桩本身、调度抖动和设备温控都可能接近差异量级。此时需要足够样本和对照组，不能依赖单次 trace 下结论。

## 11. Data Explorer 在这套流程中的位置

通过完整性检查后，Data Explorer 这个可视化查询构建器适合交互式探索。Table/Query 是表或 SQL 查询数据源，Time Range 用来限定时间窗口，Join 按键连接两组记录，pivot 按维度分组汇总，bar 与 histogram 分别显示条形比较和数值分布。它适合：

- 从 Table 或 Query 源快速确认字段；
- 用 Time Range 与问题窗口对齐；
- 在 Join 前后观察行数，发现一对多关联造成的重复；
- 用 pivot、bar、histogram 找分布和异常组；
- 把有价值的探索转换成可保存 SQL。

它无法替代采集与质量判断：

- 选择设备采集了哪些事件；
- 判断 trace 是否因 buffer 覆盖而缺数据；
- 自动消除一对多 Join 造成的行数膨胀；
- 为缺失字段编造 0；
- 保证导出的节点图跨 Perfetto 版本兼容。

### 11.1 命令行完整性检查

将完整性 SQL 保存为 `check_trace.sql` 后，可用固定版本的 v54 shell 执行：

```bash
./trace_processor_shell \
  --query-file check_trace.sql \
  trace.perfetto-trace
```

脚本应把非零 data-loss/error 统计和 central buffer 覆盖项保存为结构化结果。是否让 CI（持续集成）任务失败，应根据指标依赖的数据源判断；不能静默忽略所有 warning，也不必因无关 buffer 的单个计数丢弃整份数据。

## 12. 常见误判

| 误判 | 修正 |
| --- | --- |
| Trace Processor 能打开，所以 trace 完整 | 可解析与无丢失是两件事，先查 `stats` |
| `severity='data_loss'` 无结果，所以没有覆盖 | v54 的 overwritten/discarded 还是 `info`，需单独查询 |
| 调大 `buffers.size_kb` 就解决 ftrace overrun | 它只影响 central buffer；ftrace 有每 CPU buffer |
| 环形 buffer 覆盖只影响旧时间段 | 被覆盖的 interned data 可能让后续 sequence 失去解释条件 |
| 更频繁 flush 总是更安全 | flush 提高新鲜度，也增加 producer 与 service 开销 |
| `DISCARD` 就叫 `STOP_WHEN_FULL` | v54 proto 枚举名是 `DISCARD` |
| 文件中的 packet 按时间戳全局有序 | 只保证 writer sequence 内顺序，导入器负责跨序列排序 |
| 一条 trace 足以证明优化有效 | 需要相同条件的重复样本与无 tracing 基线 |

## 13. 源码与文档版本依据

版本与行为以这些 v54/Android 17 一手资料为准：

- [Android 17 `external/perfetto` CHANGELOG](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/CHANGELOG)
- [Perfetto v54.0 release notes](https://github.com/google/perfetto/blob/v54.0/CHANGELOG)
- [Buffers and dataflow](https://github.com/google/perfetto/blob/v54.0/docs/concepts/buffers.md)
- [Perfetto service model](https://github.com/google/perfetto/blob/v54.0/docs/concepts/service-model.md)
- [Shared-memory API/ABI](https://github.com/google/perfetto/blob/v54.0/docs/design-docs/api-and-abi.md)
- [Trace buffer design](https://github.com/google/perfetto/blob/v54.0/docs/design-docs/trace-buffer.md)
- [v54 `TraceConfig` proto](https://github.com/google/perfetto/blob/v54.0/protos/perfetto/config/trace_config.proto)
- [v54 `FtraceConfig` proto](https://github.com/google/perfetto/blob/v54.0/protos/perfetto/config/ftrace/ftrace_config.proto)
- [v54 Trace Processor stats definitions](https://github.com/google/perfetto/blob/v54.0/src/trace_processor/storage/stats.h)
- [Trace Processor shell](https://github.com/google/perfetto/blob/v54.0/src/trace_processor/trace_processor_shell.cc)

Android 17 平台源码用于确认设备侧包含的 Perfetto 能力，v54 标签用于固定主机工具和文档语义。使用更新工具解析旧 trace 时，应记录工具版本，并重新核对配置字段、stats severity 和标准库表定义。
