# 附录 C：Perfetto TraceConfig 模板集

Perfetto 可以按场景选择 data source。采集开销取决于启用的数据源、事件频率、buffer 和采集时长，需要在目标设备上测量。

以下是供 `adb shell perfetto` 或 Python 自动化脚本使用的 `config.pbtxt`（Protocol Buffer Text）模板。

---

## 1. 基础 UI 渲染与卡顿排查模板 (UI Jank)

该模板适用于分析滑动卡顿、掉帧、动画不流畅等问题。它开启了完整的 CPU 调度、频率、以及和渲染强相关的 atrace tag（`gfx`, `view`, `wm`, `am`, `hal`）。

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

---

## 2. 深入 I/O 与启动时间排查模板 (App Launch & I/O)

该模板在基础 UI 分析之上，增加了对 Block I/O、F2FS 文件系统、页错误（Page Fault）和内存管理事件的抓取。适用于冷启动优化、SQLite 数据库性能排障以及低内存卡顿排查。

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

---

## 3. 功耗与热约束分析模板 (Power & Thermal)

该模板关闭了高频的调度事件（减少开销并支持长时间抓取），重点开启了电池统计（BatteryStats）、Android Power HAL、唤醒锁（Wakelock）以及 Thermal（温度传感器）轮询。适用于分析待机耗电、后台自启或游戏过程中的发热降频。

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

---

## 4. 如何在设备上使用这些模板

1. 将上述任一代码块保存为文件，例如 `config.pbtxt`。
2. 将文件推送到手机的临时目录：
   ```bash
   adb push config.pbtxt /data/local/tmp/
   ```
3. 在手机上启动 Perfetto 抓取：
   ```bash
   adb shell "cat /data/local/tmp/config.pbtxt | perfetto --txt -c - -o /data/misc/perfetto-traces/trace.perfetto-trace"
   ```
4. 抓取完成后，将文件拉取到电脑：
   ```bash
   adb pull /data/misc/perfetto-traces/trace.perfetto-trace ./
   ```
5. 打开 [ui.perfetto.dev](https://ui.perfetto.dev/)，将 `trace.perfetto-trace` 拖入浏览器即可开始分析。
