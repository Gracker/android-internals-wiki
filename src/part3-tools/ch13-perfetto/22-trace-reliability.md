---
title: "Trace 采集可靠性与可复现诊断"
chapter: "13.22"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: ["Perfetto", "Data Explorer", "v54", "性能分析", "数据可视化", "Trace Processor"]
related_chapters: ["13.2", "13.4", "13.13", "13.15"]
last_verified: "2026-07-03"
last_verified_against: "AOSP android-17.0.0_r1"
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

> 平台基线是 Android 17 / API 37 / `android-17.0.0_r1`，工具基线是该平台 `external/perfetto` 中包含的 Perfetto v54.0。界面操作、SQL 节点图与 CUJ 指标口径见 [13.13 DataGrid、Data Explorer 与 Jank CUJ](13-perfetto-data-explorer-jank-cuj.md)。

---

## 1. 先判断 trace 能不能支撑结论

性能分析常从一张漂亮的时间线开始，却可能败在采集阶段：调度事件被覆盖、producer 的共享内存发生丢包、结束 flush 失败，或环形 buffer 已经把问题发生前的数据冲掉。Trace Processor 能打开文件，只能说明文件可解析，不能证明事件完整。

诊断采用一条固定顺序：

1. 明确要回答的问题和所需数据源；
2. 估算数据率，设置 ftrace、共享内存和 central buffer；
3. 采集后检查 `stats` 与时间范围；
4. 通过质量闸门后，再做 Data Explorer、PerfettoSQL 或 metric 分析；
5. 保存配置、工具版本、SQL 与原始 trace，供同事复核。

这套顺序对 UI 卡顿、启动、ANR、功耗和内存分析都适用。不同场景的配置可以不同，数据完整性检查不应省略。

## 2. Android 17 上的数据流

### 2.1 四个角色

Perfetto 的系统采集路径可拆成四个角色：

| 角色 | Android 上的常见实例 | 职责 |
| --- | --- | --- |
| Producer / data source | 应用中的 Track Event、`traced_probes` 托管的 ftrace/process stats 等 | 生成 `TracePacket` |
| 共享内存缓冲区（SMB） | 每个 producer 与 tracing service 之间的一对一暂存区 | 让写入快路径直接序列化，吸收 service 短时调度延迟 |
| Tracing service | `traced` | 把 producer 的 chunk 复制到会话 central buffer，处理 flush、触发与输出 |
| Consumer / 分析端 | `perfetto` CLI、Perfetto UI、`trace_processor_shell` | 配置和读取会话，或在采集后解析 trace |

`traced_probes` 与 `traced` 是两个不同职责的进程。前者承载 ftrace、进程统计等系统探针，后者是 tracing service。producer/service 控制通道使用 Perfetto IPC；Android 系统后端通常通过 Unix domain socket 连接，不能概括成 Binder 调用。

Trace Processor 不位于设备采集热路径中。它在采集后读取 trace，把 protobuf packet 解析成 `slice`、`sched_slice`、`thread`、`process` 等表，再加载 PerfettoSQL 标准库与 metric。

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
- SMB 是 producer 与 service 共享的短期暂存区，每个 producer 一份；
- central buffer 由 `TraceConfig.buffers` 定义，可接收多个 producer 和 data source 的 packet。

把 `TraceConfig.buffers.size_kb` 调大，只扩大 central buffer；它不会同步扩大内核 ftrace buffer或 SDK producer 的 SMB。ftrace 要调 `ftrace_config.buffer_size_kb`，SDK producer 的 SMB 则由 producer 初始化参数等机制决定。

### 2.3 一个 packet 如何到达 central buffer

producer 取得 SMB page/chunk 后，通过 ProtoZero 直接写入 protobuf 字节。写满或主动提交后，producer 发送异步 IPC，service 将已提交 chunk 复制到 central buffer，再把空间交还 producer。

共享内存 ABI 中的 chunk 状态为：

| 状态 | 含义 |
| --- | --- |
| `Free` | producer 可以取得并开始写入 |
| `BeingWritten` | producer 正在写，service 不应改动状态 |
| `BeingRead` | service 正在复制，完成后转回 `Free` |

一个 `TracePacket` 可以跨越多个 chunk，长度字段也可能在写完后回填。v54 协议用 `CommitDataRequest.ChunkToPatch` 等机制处理已经提交 chunk 中需要修补的字段。这里的保证是 packet 级原子性：service 只有在能观察到完整、连续的所有 fragment 时才输出该 packet。

“packet 原子”不等于“所有 packet 都不会丢”。空间耗尽、环形覆盖或读取不及时仍可能丢失整个 packet 或 packet 序列。

## 3. 顺序、flush 与增量状态

### 3.1 文件顺序不是全局时间顺序

同一个 `TraceWriter` 序列内，packet 保持写入顺序；不同 writer 序列并发提交，不保证 trace 文件中的全局时间戳有序。Trace Processor 在导入时按时间整理事件。

低频 data source 可能长时间没有填满 SMB page。若缺少 flush，一条较早的事件可能在数分钟后才提交，与其他序列的新事件混在文件后部。长 trace 的乱序跨度超过窗口排序能力时，导入器可能报告 out-of-order 问题。

`flush_period_ms` 会要求 data source 周期提交未满 page，可缩小这类乱序窗口。v54 的 `TraceConfig` 也提示高频 flush 会增加开销；普通采集不应为了“更实时”设置成毫秒级。

导入旧 trace 时若已经遇到超大乱序窗口，可让 shell 使用完整排序：

```bash
./trace_processor_shell \
  --full-sort \
  trace.perfetto-trace
```

`--full-sort` 会提高导入内存占用。它只能改变解析排序策略，不能找回采集时已经丢失的数据。

### 3.2 环形覆盖为何会破坏后续解释

Track Event 常把字符串、进程/线程描述等内容 intern 成 ID，后续 packet 只引用 ID。`linux.process_stats` 也可能先记录线程与进程的对应关系，后续 ftrace packet 再引用 TID。若环形 buffer 覆盖了较早的映射，保留下来的事件可能失去解释所需的增量状态。

Trace Processor 会检测部分无效增量状态，并跳过依赖缺失 interned data 的 packet。结果不是“名称为空但其余都可靠”，有时是整段 sequence 无法进入分析表。

两种常用缓解方式是：

- 设置 `incremental_state_config.clear_period_ms`，让支持该协议的 data source 周期清除状态并重新发出描述；
- 把低频、但决定解释关系的数据源放入单独 target buffer，减少被高频 ftrace 数据覆盖的机会。

`clear_period_ms` 不是所有 data source 的强制刷新开关。只有声明 `handles_incremental_state_clear` 的 data source 会响应；周期越短，重复描述带来的数据量和开销越高。

## 4. 数据完整性闸门

### 4.1 不要只看 `severity = 'data_loss'`

下面的查询列出 Trace Processor 判定为 data loss 或 error 的非零统计：

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

它能捕获 `ftrace_cpu_has_data_loss`、`traced_buf_trace_writer_packet_loss`、`traced_final_flush_failed` 等关键项。不过，v54 的 `traced_buf_chunks_overwritten` 与 `traced_buf_chunks_discarded` 在 `stats.h` 中仍标为 `info`。所以该查询返回空，也不能单独证明 central buffer 没有覆盖或丢弃。

下面的第二条查询专门查看 central buffer 容量与写入状态：

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

`idx` 对 central buffer 统计通常是 buffer 下标，对 ftrace 统计通常是 CPU 下标。报告问题时不要丢掉 `idx`，它能帮助定位是哪一个 buffer 或 CPU 发生异常。

### 4.2 关键统计怎么解释

| 统计项 | 表示什么 | 优先检查 |
| --- | --- | --- |
| `ftrace_cpu_has_data_loss` | 指定 CPU 的内核 ftrace buffer 在用户态读取前覆盖了事件 | 减少 ftrace 事件、增大 `buffer_size_kb`、确认读取调度 |
| `ftrace_cpu_overrun_delta` | 采集区间内的 ftrace overrun 计数差 | 与 `ftrace_cpu_has_data_loss` 和 CPU 下标一起看 |
| `traced_buf_trace_writer_packet_loss` | service 观察到 target buffer 对应 writer 丢包 | producer 突发写入、SMB 大小与 stall/drop 策略 |
| `traced_buf_chunks_overwritten` | `RING_BUFFER` 中旧 chunk 被新数据覆盖 | central buffer 容量、采集时长、数据率 |
| `traced_buf_chunks_discarded` | `DISCARD` 满后拒收新 chunk | central buffer 容量、是否选错 fill policy |
| `traced_buf_patches_failed` | 跨 chunk packet 的 patch 失败，可能丢数据 | 同 buffer 的 discard 与 packet loss |
| `traced_final_flush_failed` | 会话结束时至少一个 producer 未按时完成 flush | producer 状态、超时与 trace 尾部可信度 |
| `traced_buf_incremental_sequences_dropped` | 缺少有效增量状态而丢弃 sequence | 环形覆盖、clear 周期、target buffer 划分 |
| `misplaced_end_event` | 解析 slice 时遇到无法配对的 end | 插桩是否配对；其 `source` 是 analysis |

`source = 'trace'` 指向 trace 自带的采集统计，`source = 'analysis'` 表示导入/分析阶段发现的问题。两者都要处理，但修复位置不同。

### 4.3 “有丢失”之后还能不能分析

不能只给“能”或“不能”。要看损失发生在哪个 CPU、buffer、时间段和数据源：

- 目标是主线程锁等待，而目标 CPU 的 sched 事件有丢失，调度因果不能下强结论；
- 只分析一个应用 Track Event 区间，而丢失发生在无关 target buffer，结论可能仍可用；
- ring buffer 有覆盖，但所需窗口完整保留且增量状态有效，可以限定时间范围继续；
- 结束 flush 失败时，trace 尾部事件可能缺失，不能把“没看到结束”解释成“操作没有结束”。

报告中应明确写出损失项、下标、数值，以及它可能影响的结论。重采的成本较低时，优先修配置并重采。

## 5. 用数据率计算 buffer，不背固定数值

### 5.1 Central buffer

非流式采集近似满足：

```text
可保留时长 ≈ central buffer 字节数 ÷ 聚合写入速率
```

例如所有 producer 合计写入约 2 MiB/s，32 MiB buffer 只能保存约 16 秒。`RING_BUFFER` 保存靠近结束时的窗口，较早数据会被覆盖；`DISCARD` 保存开头，满后拒绝新数据。后者不是名为 `STOP_WHEN_FULL` 的枚举，v54 配置中的有效值是 `RING_BUFFER` 与 `DISCARD`。

写入速率与设备负载、CPU 数、启用事件和应用插桩量相关。syscall、page fault、binder 或大量应用 trace point 都可能把速率提高一个数量级。估算值只用于起步，采集后要用 buffer 统计校正。

### 5.2 Ftrace per-CPU buffer

内核 ftrace buffer 需要容纳两次读取之间每个 CPU 产生的事件。影响它的配置是：

- `ftrace_config.buffer_size_kb`：每 CPU buffer 的目标大小；
- `ftrace_config.drain_period_ms`：`traced_probes` 读取周期；
- `ftrace_events` 与 atrace category：决定事件率。

减少 `drain_period_ms` 能降低覆盖风险，但会增加唤醒和读取开销。增大 `buffer_size_kb` 会按 CPU 数增加内核内存占用。两者都应由 `ftrace_cpu_has_data_loss` 与实际负载来调整。

### 5.3 Producer SMB

SMB 要吸收的是 producer 的峰值写入，而非平均值。一个 data source 每 10 秒写 2 MiB 大 packet，平均只有 0.2 MiB/s，但写入瞬间仍可能耗尽小 SMB。

可选方向包括：

- 提高 producer 的 SMB size hint；
- 把大 payload 分段并避免瞬时连写；
- SDK data source 在业务允许时使用 `BufferExhaustedPolicy::kStall`。

`kStall` 会让被观测进程等待空闲 buffer，可能显著改变时序。性能关键路径通常更关心低扰动，此时宁可丢 tracing packet，并用 stats 标明 trace 不完整。

## 6. 一份可解释的 Android 17 短 trace 配置

下面配置面向约 15 秒的 UI 调度观察。数值只是起始点，目标设备仍需按上一节的方法校正：

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

高频 ftrace 写入 central buffer 0，低频进程映射放在 buffer 1，可降低映射被调度事件覆盖的概率。`scan_all_processes_on_start` 有助于建立起始时刻的进程/线程关系，也会增加采集量。

`ftrace_config.buffer_size_kb` 是每 CPU 大小；这里的 8192 KiB 在 8 核设备上最多对应约 64 MiB 内核 buffer，应结合设备 CPU 数和内存约束调整。15 秒短采集通常依赖结束 flush 即可，因此示例没有默认加入周期 flush 和增量状态清除。

该配置没有罗列 binder、irq、workqueue、频率 idle、内存和 heap profiling 等所有数据源。先写出诊断问题，再加入能回答问题的事件。若 UI 卡顿需要 binder 因果，可补 binder ftrace；若只关心应用 slice，不应默认开启高频 syscall。

### 6.1 采集后要保存什么

每次可复核采集至少保存：

- 完整 pbtxt 配置；
- Android build fingerprint 或明确的 `android-17.0.0_r1` 构建标识；
- `trace_processor_shell --version` 输出；
- 原始 trace 文件；
- 数据完整性查询结果；
- 用于产生数字的 SQL 或 metric 命令；
- 操作步骤和观察时间窗口。

只保存 Perfetto UI 截图会丢掉单位、过滤条件、工具版本与缺失数据提示。

## 7. 长 trace：文件流式写入与 v54 flush 策略

### 7.1 `write_into_file` 解决 central buffer 容量问题

长 trace 若只在结束时读取 central buffer，容量必须覆盖整个目标时间或接受 ring 覆盖。`write_into_file: true` 让 service 周期把 central buffer 写入文件，buffer 只需覆盖两个写周期之间的数据峰值。

下面片段展示 v54 的相关字段：

```protobuf
write_into_file: true
file_write_period_ms: 5000
max_file_size_bytes: 1073741824
write_flush_mode: WRITE_FLUSH_AUTO
```

`max_file_size_bytes` 达到上限时会停止 tracing。若配置 `output_path`，Android system `traced` 只允许 `/data/misc/perfetto-traces/` 下的路径；更常见的 CLI 方式是由 consumer 提供输出文件描述符。

### 7.2 v54 的 `write_flush_mode`

v54 用 `write_flush_mode` 替换已移除的 `no_flush_before_write_into_file`。三种有意义的模式为：

| 模式 | 行为 |
| --- | --- |
| `WRITE_FLUSH_AUTO` | 默认；根据 write period 自动决定 flush 频率 |
| `WRITE_FLUSH_DISABLED` | 周期写文件前不强制 flush；允许较新数据暂留 SMB |
| `WRITE_FLUSH_ENABLED` | 每次周期写前都 flush；数据更新更及时，开销更高 |

在 AUTO 下，`file_write_period_ms <= 5s` 时不会每次写都 flush，而是约每 5 秒周期 flush；周期大于 5 秒时，每次写前 flush。这个规则来自 v54 `TraceConfig` 注释，脚本迁移时不要继续使用旧字段。

`fflush_post_write: FFLUSH_ENABLED` 会在每次写入后执行存储同步，提高掉电或崩溃场景下的数据持久性，同时增加 I/O 成本。一般性能采集不要默认开启。

## 8. 诊断流程：从问题窗口到证据

### 8.1 UI 卡顿

推荐顺序如下：

1. 确认 trace 的 ftrace、FrameTimeline、应用 atrace 和进程映射没有关键丢失；
2. 在 timeline 或 CUJ 表确定异常帧和时间窗口；
3. 分开判断 app missed 与 SurfaceFlinger missed；
4. 检查 UI thread、RenderThread 的 `thread_state` 与 `sched_slice`；
5. 对 runnable 时间检查 CPU 竞争、优先级与频率；
6. 对 sleeping/blocking 时间检查 binder、锁、I/O 和回调；
7. 对 GPU/合成问题检查 FrameTimeline、SurfaceFlinger 与图形数据；
8. 把候选原因与正常帧对照，确认差异可重复。

CPU 运行时间长、runnable 等待长和 wall duration 长是三个不同概念。一个帧超过预算可能是线程没有获得 CPU，也可能是获得 CPU 后执行过多，还可能在 binder 或 fence 上等待。

### 8.2 应用启动

启动分析至少区分：

- 进程是否已存在；
- 冷、温、热启动口径；
- launcher 点击、ActivityTaskManager 处理、进程创建、Application、Activity 与首帧；
- 主线程 CPU 执行、调度等待、I/O、类加载和锁。

不要把某个 `slice.dur` 直接命名为完整启动时间。使用 Android startup metric 或标准库时，先核对 metric 对该 trace 的启动类型和边界，再用 slice 解释慢在哪里。

### 8.3 ANR

ANR 查询可从 `android_anrs` 获取事件时间、类型、subject、intent 与 component，再回到时间线检查：

- 主线程当时处于 Running、Runnable、Sleeping 还是阻塞态；
- binder 调用链是否完整；
- 是否有 CPU starvation、锁竞争、I/O 或长回调；
- `traced_final_flush_failed` 是否让 trace 尾部缺失。

没有看到解锁、binder reply 或回调结束，不足以证明它从未发生；先排除尾部未 flush 与相关 buffer 丢失。

### 8.4 功耗

短时间高 CPU 与长期耗电不能画等号。功耗分析应对齐：

- CPU/GPU 频率与 idle/residency；
- suspend/wakeup；
- 进程或线程活动；
- 网络、定位、相机、音频等设备使用；
- 测量窗口和设备状态。

trace 只能解释已经采到的数据。没有设备功率计、fuel gauge 或 Wattson 支持时，不要把调度时长直接换算成毫瓦时。

## 9. 插桩需要遵守的边界

应用 Track Event 或 atrace 名称应稳定、短小，并表达业务阶段。同步 begin/end 必须在同一线程和控制流上正确配对；异步操作应使用能够区分并发实例的 cookie/track。

插桩前要评估：

- 高频循环是否产生过量事件；
- 动态名称是否导致大量 interned string；
- 是否把用户数据、URL、账号或业务内容写入 trace；
- release/user build 上是否允许该数据源；
- 关闭 tracing 时快路径开销是否可接受。

`misplaced_end_event` 增长时，应检查 begin/end 配对和线程迁移。用名称搜索到一段 slice，不代表异步任务边界一定正确。

## 10. 观察者开销怎么评估

Tracing 会消耗 CPU、内存、I/O 和被观测进程时间。开销与配置有关，不能只引用一个“Perfetto 通常很低”的百分比。

建议做三组同场景重复测试：

1. 不采 trace 的基线；
2. 最小必要配置；
3. 候选完整配置。

比较业务指标的中位数和尾部、设备温度、频率状态、掉帧，以及 `stats` 中的丢失项。若完整配置显著改变被测指标，应缩小事件集、降低 polling 频率、缩短采集窗口或使用触发式采集。

对小于几毫秒的阶段，插桩本身、调度抖动和设备温控都可能接近差异量级。此时需要足够样本和对照组，不能依赖单次 trace 下结论。

## 11. Data Explorer 在这套流程中的位置

通过完整性闸门后，Data Explorer 适合：

- 从 Table 或 Query 源快速确认字段；
- 用 Time Range 与问题窗口对齐；
- 在 Join 前后观察行数；
- 用 pivot、bar、histogram 找分布和异常组；
- 把有价值的探索转换成可保存 SQL。

它不负责：

- 选择设备采集了哪些事件；
- 判断 trace 是否因 buffer 覆盖而缺数据；
- 自动消除一对多 Join；
- 为缺失字段编造 0；
- 保证导出的节点图跨 Perfetto 版本兼容。

### 11.1 命令行质量闸门

将完整性 SQL 保存为 `check_trace.sql` 后，可用固定版本的 v54 shell 执行：

```bash
./trace_processor_shell \
  --query-file check_trace.sql \
  trace.perfetto-trace
```

脚本应把非零 data-loss/error 统计和 central buffer 覆盖项作为结构化结果保存。是否让 CI 失败，应按指标依赖的数据源判断；不能把所有 warning 静默忽略，也不必因无关 buffer 的单个计数丢弃全部数据。

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

## 13. 源码与文档锚点

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
