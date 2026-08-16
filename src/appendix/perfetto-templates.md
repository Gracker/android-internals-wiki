# 附录 C：Perfetto TraceConfig 模板集

三份配置用于在 Android 设备上快速验证 UI 卡顿、启动与 I/O、功耗与温度问题。`TraceConfig` 是 Perfetto tracing 会话的 protobuf（Protocol Buffers，结构化序列化格式）配置；PBTX、PBTXT 和 pbtxt 都指它的人类可读文本表示，文件扩展名不影响解析。

`data source` 是向 trace 写入某类数据的采集组件，`buffer` 是 tracing service（管理采集会话的服务）保存数据包的会话缓冲区。`RING_BUFFER` 写满后会用新数据覆盖较早数据，所以容量要按目标设备上的事件速率和采集时长验证。

这些 PBTX 模板适合人工调试和受控实验。Android 10 / API 29 起，设备端 `perfetto` 才支持 `--txt`；官方将文本格式视为可能随 schema（字段结构与规则）变化的接口，长期自动化应生成二进制 `TraceConfig`，并固定生成端和设备端采用的 proto 版本。

## 使用前先确认设备能力

配置字段存在，不代表目标设备一定能产出对应数据。Android 版本、设备内 Perfetto 版本、内核 tracepoint（预定义事件点）、系统构建类型、厂商 HAL（硬件抽象层实现）和权限都会缩小可采集范围。

采集前至少完成三项检查：

1. 用 `adb shell perfetto --query --long` 查看 tracing service 注册的数据源，用 `adb shell atrace --list_categories` 查看设备支持的 atrace category。atrace 是 Android 平台 trace 标记接口，category 是一组标记的开关名称。
2. 在允许读取 tracefs（内核跟踪虚拟文件系统）的调试设备上，对照 `/sys/kernel/tracing/available_events` 检查每个 ftrace tracepoint。ftrace 是 Linux 内核跟踪框架；量产 user build（面向出货的系统构建）可能限制 shell 读取，缺少权限时应记录这一限制。
3. 先抓短 trace，再检查必需轨道、`stats` 表和 ring buffer 覆盖情况。轨道缺失表示数据源不可用、未启用、无权限或场景没有触发，不能按零值解释。

---

## 1. 基础 UI 渲染与卡顿排查模板 (UI Jank)

用途是观察滑动卡顿、掉帧和动画节奏异常。`sched_switch` 记录 CPU 从一条线程切换到另一条线程的时刻，`cpu_frequency` 和 `cpu_idle` 补充频率与空闲状态；`am`、`wm`、`view`、`gfx`、`hal`、`input`、`res`、`bionic` 是 ActivityManager、WindowManager、界面渲染、硬件抽象层、输入、资源和 C 运行库相关的 atrace category。

该配置没有采集 `sched_wakeup` 或 `sched_waking`，因此无法完整计算线程从被唤醒到获得 CPU 的排队时间。Android 12 / API 31 及以上设备若要使用平台逐帧卡顿判定，还要加入独立数据源 `android.surfaceflinger.frametimeline`；`gfx` 和 `view` category 不会自动启用 FrameTimeline。

`atrace_apps: "*"` 会请求采集所有符合平台权限条件的应用 trace 标记，数据量和设备扰动都可能增加。只调查一个应用时，应把通配符换成目标包名。

63,488 KiB（1 KiB 为 1024 字节，约 62 MiB）的 central buffer（会话中央缓冲区）与 10 秒时长只是起始参数，采后仍要检查覆盖和丢包。

```protobuf
buffers: {
    size_kb: 63488
    fill_policy: RING_BUFFER
}
data_sources: {
    config {
        name: "linux.process_stats"
        target_buffer: 0
        process_stats_config {
            scan_all_processes_on_start: true
        }
    }
}
data_sources: {
    config {
        name: "linux.sys_stats"
        sys_stats_config {
            stat_period_ms: 1000
            stat_counters: STAT_CPU_TIMES
            stat_counters: STAT_FORK_COUNT
        }
    }
}
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_config {
            ftrace_events: "sched/sched_switch"
            ftrace_events: "power/cpu_frequency"
            ftrace_events: "power/cpu_idle"
            ftrace_events: "task/task_newtask"
            ftrace_events: "task/task_rename"
            atrace_categories: "am"
            atrace_categories: "wm"
            atrace_categories: "view"
            atrace_categories: "gfx"
            atrace_categories: "hal"
            atrace_categories: "input"
            atrace_categories: "res"
            atrace_categories: "bionic"
            atrace_apps: "*"
        }
    }
}
duration_ms: 10000
```

预期结果包括线程切换、CPU 频率与空闲事件、应用和系统 atrace 标记，以及采集开始时的进程关系。该配置没有设置 `proc_stats_poll_ms`，因此不能期待 `linux.process_stats` 周期输出进程内存；缺少 FrameTimeline 时，也不会出现平台提供的逐帧期望与实际时间线。

---

## 2. 启动与 I/O 排查模板 (App Launch & I/O)

这是一份独立配置，不会继承第 1 份模板中的 `linux.sys_stats`、`cpu_idle`、`input`、`hal` 等数据。它记录块设备请求的发出与完成、F2FS 同步、RSS（Resident Set Size，驻留内存）变化、旧 ION 内存堆事件和用户态缺页事件，可用于启动、SQLite I/O 或内存压力调查。

Block I/O（块设备输入/输出）发生在文件系统之下，`block_rq_issue` 到 `block_rq_complete` 描述存储请求，不会自动把请求归因到某个应用函数。F2FS tracepoint 只适用于采用 F2FS 的分区；使用 ext4 或厂商文件系统的设备不会产生对应事件。

Page Fault（缺页异常）是 CPU 访问虚拟地址时，因映射缺失或权限问题转入内核处理的同步异常。ARM64 设备不保证提供 `exceptions/page_fault_user`。

ION 两个事件也需要按版本处理。Android 12 的 GKI 2.0（Generic Kernel Image，通用内核镜像）已用 DMA-BUF Heaps（共享缓冲区内存堆）替代 ION，现代设备通常没有 `kmem/ion_heap_grow` 和 `kmem/ion_heap_shrink`。

采集前应逐项对照 tracefs，缺失时从设备已有的 `filemap`、`vmscan`、`kmem`、`block` 事件中选择。Page Fault 总量可改用 Android CPU 性能分析工具 Simpleperf 的 `page-faults`、`minor-faults` 和 `major-faults` 软件事件计数。

`kmem/rss_stat` 在较新的内核上可能产生大量事件。目标 Perfetto schema 支持时，可评估 `throttle_rss_stat: true`，让采集端优先使用节流版本；无论是否启用，都要检查每个 CPU 的 ftrace 丢失统计。

```protobuf
buffers: {
    size_kb: 131072
    fill_policy: RING_BUFFER
}
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_config {
            # 基础调度与频率
            ftrace_events: "sched/sched_switch"
            ftrace_events: "sched/sched_wakeup"
            ftrace_events: "power/cpu_frequency"
            
            # 磁盘与 I/O
            ftrace_events: "block/block_rq_issue"
            ftrace_events: "block/block_rq_complete"
            ftrace_events: "f2fs/f2fs_sync_file_enter"
            ftrace_events: "f2fs/f2fs_sync_file_exit"
            
            # 内存事件与 Page Fault
            ftrace_events: "kmem/rss_stat"
            ftrace_events: "kmem/ion_heap_grow"
            ftrace_events: "kmem/ion_heap_shrink"
            ftrace_events: "exceptions/page_fault_user"
            
            atrace_categories: "am"
            atrace_categories: "wm"
            atrace_categories: "view"
            atrace_categories: "gfx"
            atrace_categories: "disk"
            atrace_categories: "dalvik"  # 开启 GC 追踪
            atrace_apps: "*"
        }
    }
}
data_sources: {
    config {
        name: "linux.process_stats"
        process_stats_config {
            scan_all_processes_on_start: true
        }
    }
}
duration_ms: 15000
```

冷启动结果还受进程是否存在、编译状态、页缓存冷热、存储状态和后台负载影响。比较前应固定这些条件，并用应用 trace 标记划出启动阶段。某条 ftrace 轨道为空时，先判断事件是否存在、是否获准启用以及场景是否触发，不能把空轨道写成“该阶段耗时为零”。

---

## 3. 功耗与热约束分析模板 (Power & Thermal)

用途是观察电池计数器、可选电源轨、CPU 频率与空闲状态、系统挂起和内核热事件。配置没有启用高频 `sched_switch`，事件量会较少，但也无法把 CPU 运行时间归因到具体线程；需要线程归因时，应在较短采集窗口中补充调度事件。

`android.power` 通过 IHealth HAL（电池健康硬件抽象层）轮询剩余容量、电荷量和电流，并通过可选的 IPowerStats HAL 读取设备提供的 ODPM power rail。ODPM 是片上电源监视器，rail 是可单独计量的一条硬件供电支路。

该数据源不提供 BatteryStats 的 UID（Android 用于归集应用资源的 Linux 用户标识）、WakeLock（唤醒锁）、Job（系统调度任务）或网络归因。这类结果要从 bugreport（系统诊断包）、`dumpsys batterystats` 或 Battery Historian 获取。

`cpufreq_period_ms: 500` 表示每 500 ms 读取一次 CPU 频率状态。`thermal/thermal_temperature` 和 `thermal/cdev_update` 由内核在事件发生时写出，属于事件驱动记录；厂商内核可能缺少其中一项。`power` 与 `idle` atrace category 也不能代替完整的 WakeLock 持有者记录。

```protobuf
buffers: {
    size_kb: 63488
    fill_policy: RING_BUFFER
}
data_sources: {
    config {
        name: "android.power"
        android_power_config {
            battery_poll_ms: 1000
            collect_power_rails: true
            battery_counters: BATTERY_COUNTER_CAPACITY_PERCENT
            battery_counters: BATTERY_COUNTER_CHARGE
            battery_counters: BATTERY_COUNTER_CURRENT
        }
    }
}
data_sources: {
    config {
        name: "linux.sys_stats"
        sys_stats_config {
            # 轮询 CPU 频率状态，而非依赖高频 ftrace
            cpufreq_period_ms: 500
        }
    }
}
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_config {
            # 功耗强相关事件
            ftrace_events: "power/cpu_frequency"
            ftrace_events: "power/cpu_idle"
            ftrace_events: "power/suspend_resume"
            ftrace_events: "thermal/thermal_temperature"
            ftrace_events: "thermal/cdev_update"
            # 唤醒锁
            atrace_categories: "power"
            atrace_categories: "idle"
        }
    }
}
# 支持长达 1 分钟的追踪
duration_ms: 60000 
```

`duration_ms: 60000` 只把会话时长设为 60 秒，不保证 63,488 KiB ring buffer 能保留完整窗口。高事件率设备可能覆盖早期数据；需要更长窗口时，应根据 `stats` 调整数据源、buffer 或流式写文件策略。

电池电流的正负方向、更新周期和分辨率由设备实现决定，USB 充电还会改变电池计数器含义并让调试连接保持额外唤醒。

Power rail 列表为空是合法结果，表示设备没有向 Perfetto 提供相应硬件计量；不同设备的 rail 名称和覆盖范围也不能直接横向比较。

---

## 4. 如何在设备上使用这些模板

1. 选择一个 `TraceConfig` 代码块并保存为 `config.pbtxt`。
2. 把文件推送到设备临时目录：
   ```bash
   adb push config.pbtxt /data/local/tmp/
   ```
3. 通过标准输入传入配置并启动 Perfetto：
   ```bash
   adb shell "cat /data/local/tmp/config.pbtxt | perfetto --txt -c - -o /data/misc/perfetto-traces/trace.perfetto-trace"
   ```
4. 会话按 `duration_ms` 结束后，把 trace 拉取到电脑：
   ```bash
   adb pull /data/misc/perfetto-traces/trace.perfetto-trace ./
   ```
5. 打开 [ui.perfetto.dev](https://ui.perfetto.dev/)，把 `trace.perfetto-trace` 拖入浏览器分析。

第 3 步使用 `-c -` 从标准输入读取配置，可避开非 root 设备对 `/data/local/tmp/` 配置文件的 SELinux（强制访问控制）读取限制。Android 12 及以上也可以使用 `/data/misc/perfetto-configs/`；Android 10 / 11 继续采用 stdin（标准输入）更稳妥，Android 9 不支持 `--txt`。

输出文件宜使用带时间或场景名的唯一名称，避免旧文件与本次结果混淆。Android 9 若不能直接拉取 trace，可用 `adb shell cat` 把内容重定向到主机文件。

Perfetto UI 默认在浏览器本地解析文件，只有显式使用分享功能时才涉及上传。

## 5. 采后验收

trace 文件可以打开，只能说明 Trace Processor（trace 解析与查询引擎）能解析文件，不能证明采集内容完整。先在 Perfetto UI 的查询页或 `trace_processor_shell` 中执行这条查询：

```sql
SELECT
  name,
  idx,
  severity,
  source,
  value,
  description
FROM stats
WHERE severity IN ('data_loss', 'error')
  AND value > 0
ORDER BY severity, name, idx;
```

命中 `ftrace_cpu_has_data_loss` 时，指定 CPU 的内核 ftrace buffer 丢过事件；命中 `traced_final_flush_failed` 时，trace 尾部可能缺失。查询为空仍要单独查看 `traced_buf_chunks_overwritten`、`traced_buf_bytes_overwritten` 和 `ftrace_cpu_overrun_delta`，因为部分版本把这些统计标成 `info`。

完整性检查通过后，再确认目标场景落在 trace 时间范围内，必需的进程、线程、FrameTimeline、I/O 或 power rail 轨道存在。报告应保存原始 trace、完整 PBTX、设备 build fingerprint（系统构建指纹）、场景步骤和 Trace Processor 版本；缺失数据应标为不可用，不能填成零。

## 相关章节

- [13.2 Trace 抓取](../part3-tools/ch13-perfetto/02-trace-capture.md)
- [13.22 Trace 采集可靠性与可复现诊断](../part3-tools/ch13-perfetto/22-trace-reliability.md)
- [26.21 Page Fault 类型分析与 Android 实践](../part5-app/ch26-observability/21-page-fault-analysis-android.md)
- [11.1 Android 功耗模型](../part2-performance/ch11-power/01-power-model.md)

## 参考资料

- [Perfetto：Trace configuration](https://perfetto.dev/docs/concepts/config)
- [Perfetto：设备端 CLI](https://perfetto.dev/docs/reference/perfetto-cli)
- [Perfetto：Android 完整配置与 SELinux 边界](https://perfetto.dev/docs/learning-more/android)
- [Perfetto：atrace 应用与 category 配置](https://perfetto.dev/docs/getting-started/atrace)
- [Perfetto：FrameTimeline 数据源](https://perfetto.dev/docs/data-sources/frametimeline)
- [Perfetto：电池计数器与 power rail](https://perfetto.dev/docs/data-sources/battery-counters)
- [Perfetto：Trace Processor stats](https://perfetto.dev/docs/analysis/sql-stats)
- [Perfetto：buffer 与数据流](https://perfetto.dev/docs/concepts/buffers)
- [AOSP：Android 12 ION 到 DMA-BUF Heaps 的迁移说明](https://source.android.com/docs/core/architecture/kernel/dma-buf-heaps)
