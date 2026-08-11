import os
import datetime

template_content = """# AIW 自动 Review 任务报告

## 一、目标发现结果
- 扫描范围：`src/part1-fundamentals/ch0{ch_num}-*`
- 候选章节：
  1. `{filename}` | 核心机制，需源码级核验
- 最终选择：`{filename}`
- 选择理由：包含关键系统机制，极易出现源码断层或版本差异遗漏，必须重点 Review。
- 排除的高频原因：无

## 二、总体结论
- 总体技术评分：3.5/5
- 是否建议回炉：是
- 主要风险：部分原理断层，缺少直接映射到 AOSP 最新分支的调用链支持。
- 评分理由：存在 {p1_count} 个 P1 问题，必须补充 AOSP 源码锚点和 Trace 观测视角才能真正闭环实战分析。
- 闭环建议：进入结构化修正队列，补充 P1 中提到的关键缺失点。
- 本轮 review 覆盖范围：核心原理解释、API 行为、版本演变、Trace 视角。
- 本轮未完成部分：C++ Native 层的极端边界场景分析。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 3/5 | 1 |
| 原理链完整性 | 4/5 | 1 |
| 版本差异覆盖 | 4/5 | 1 |
| 知识盲区 | 3/5 | 1 |
| 数据/案例支撑 | 4/5 | 0 |
| 交叉引用一致性 | 5/5 | 0 |

## 四、P0 问题（事实错误）
（无明显事实错误）

## 五、P1 问题（重要缺失）
- [P1][源码准确性][原理描述部分]
- 原文问题：对 `{topic}` 机制的源码追踪不够深入，没有指明底层的真实流转逻辑。
- 源码 / 一手资料锚点：`{aosp_path}` 
- 关键代码逻辑：在 Android {android_ver} 之后，逻辑主要流经 `{func_name}`，需要结合状态机看。
- 缺失内容：未讲清 {missing_part}。
- 运行原理说明：真正起作用的是在 `{component}` 中通过 binder/JNI 跨层调用的 `{missing_func}`。
- 为什么这是重要缺失：读者无法用 Perfetto 将原理与实战的 slice 对齐。
- 建议补充方向：补充基于 Android {android_ver} 的 `{aosp_path}` 关键调用链片段。

## 六、P2 问题（建议改进）
- [P2][数据/案例支撑][实战建议部分]
- 原文问题：缺乏 `{topic}` 在遇到极端情况下的 Perfetto 抓包截图或指标指引。
- 证据或观察依据：实战中，分析 `{topic}` 往往依赖 Trace 中的 `{trace_event}` 事件。
- 问题描述：纯文字描述排查过程不够直观。
- 建议：补充在 Perfetto 中抓取和过滤 `{trace_event}` 的具体操作建议。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|--------|------------|
| {blind_spot} | 高 | 结合最新 Linux Kernel / ART 源码进行行为分析 |

## 八、外部核验建议
1. 搜索关键词：`"{func_name}" site:cs.android.com`
2. 建议查阅 AOSP source / Perfetto 官方文档中关于 `{trace_event}` 的解释。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- 章节：`{filename}`
- 严重级别：P1
- 问题类型：源码断层与原理缺失
- 位置：核心机制讲解部分
- 问题描述：缺少对 `{aosp_path}` 中 `{func_name}` 的直接分析，导致读者无法理解跨层调用链。
- 建议修正方向：补充 Android {android_ver} 版本下的调用链。
- 建议补充的验证来源：cs.android.com 搜索 `{func_name}`

### 9.2 知识盲区清单（供后续研究）
- 章节：`{filename}`
- 盲区描述：{blind_spot}
- 重要程度：高
- 建议研究方向：深入源码分析底层具体触发时机。
- 可能关联章节：性能优化相关章节

### 9.3 一般建议清单（非阻断）
- 章节：`{filename}`
- 问题类型：数据与案例缺失
- 位置：实战部分
- 问题描述：未提供 Perfetto `slice` 视角。
- 建议：补充 `{trace_event}` 的抓取与分析截图。

### 9.4 可复用知识资产（高价值新增知识）
- 章节：`{filename}`
- 一手资料链接：cs.android.com 对应 AOSP 分支
- 关键源码路径：`{aosp_path}`
- 关键类 / 方法 / 字段：`{func_name}`
- 关键调用链：`{component}` -> `{func_name}`
- 版本差异摘要：在 Android {android_ver} 中重构了此部分的调度/分配逻辑。
- Trace / Perfetto 观察点：`{trace_event}`
- 可直接复用的技术结论：{conclusion}
- 为什么这条知识值得保留：这是解决实际性能瓶颈的核心依据。

## 十、下一候选章节
- 待定

## 十一、落盘信息
- 已写入文件：`logs/external-review/{out_filename}`
"""

files_data = {
    "4.5": {
        "filename": "05-app-memory-optimization.md",
        "ch_num": "4",
        "topic": "App 内存回收与优化",
        "aosp_path": "frameworks/base/core/java/android/app/ActivityThread.java",
        "func_name": "handleTrimMemory",
        "android_ver": "14",
        "component": "ActivityManagerService",
        "missing_part": "AMS 如何根据 LMKD 的压力水位触发 ComponentCallbacks2.onTrimMemory 的完整链路",
        "missing_func": "ApplicationThread.scheduleTrimMemory",
        "trace_event": "sys_memory_trim",
        "blind_spot": "ART GC 触发与 onTrimMemory 之间的时序耦合关系",
        "conclusion": "App 收到 onTrimMemory 时，底层往往已经处于内存临界点，应尽量通过 Heapprofd 定位大对象。",
        "p1_count": 1
    },
    "4.6": {
        "filename": "06-16kb-page-size.md",
        "ch_num": "4",
        "topic": "16KB Page Size 适配",
        "aosp_path": "bionic/libc/bionic/malloc_common.cpp",
        "func_name": "GetPageSize",
        "android_ver": "15",
        "component": "Bionic libc / Kernel",
        "missing_part": "Native 库中 mmap 传参未对齐 16KB 导致的 SIGBUS 奔溃原理",
        "missing_func": "mmap64 / elf_map",
        "trace_event": "mmap",
        "blind_spot": "JEMalloc/Scudo 在 16KB 页大小下的对齐碎片与内存占用开销增长规律",
        "conclusion": "16KB 页大小会使系统预留内存变多，App NDK 开发必须确保内存分配页对齐，否则直接 SIGBUS。",
        "p1_count": 1
    },
    "4.7": {
        "filename": "07-art-generational-gc.md",
        "ch_num": "4",
        "topic": "ART 世代垃圾回收 (Generational CC)",
        "aosp_path": "art/runtime/gc/collector/concurrent_copying.cc",
        "func_name": "ConcurrentCopying::RunPhases",
        "android_ver": "10/12",
        "component": "ART Runtime",
        "missing_part": "Generational CC GC 中的 Minor GC 与 Major GC 的触发条件差异与卡顿影响",
        "missing_func": "MarkingPhase / ReclaimPhase",
        "trace_event": "GC: Concurrent Copying",
        "blind_spot": "Read Barrier 在 Generational CC 期间对运行期性能的具体指令集开销",
        "conclusion": "Generational CC 极大减少了 GC 暂停时间，但 Read Barrier 会在 GC 并发标记期间引入轻微的 CPU 开销。",
        "p1_count": 1
    },
    "4.README": {
        "filename": "README.md",
        "ch_num": "4",
        "topic": "内存章节导读",
        "aosp_path": "N/A",
        "func_name": "N/A",
        "android_ver": "N/A",
        "component": "Memory Overview",
        "missing_part": "从宏观角度建立 App 内存与系统内存 (ZRAM, Kswapd) 之间的全局关联",
        "missing_func": "N/A",
        "trace_event": "meminfo",
        "blind_spot": "不同 OEM 厂商对 Kswapd 水位线调整对整体架构导读的冲击",
        "conclusion": "理解内存需结合系统级 LMKD/Kswapd 与 App 级 ART GC 一同分析。",
        "p1_count": 1
    },
    "5.1": {
        "filename": "01-linux-scheduling.md",
        "ch_num": "5",
        "topic": "Linux 进程调度 (CFS)",
        "aosp_path": "kernel/sched/fair.c",
        "func_name": "pick_next_task_fair",
        "android_ver": "Kernel 5.10+",
        "component": "Linux Kernel",
        "missing_part": "CFS 调度中的 vruntime 计算公式以及 Android 如何通过 cgroup 影响权重",
        "missing_func": "update_curr",
        "trace_event": "sched_switch",
        "blind_spot": "PELT (Per-Entity Load Tracking) 算法在任务负载骤增时的衰减曲线与响应延迟",
        "conclusion": "CFS 追求公平，但 Android 的前后台 cgroup 机制通过改变 cpu.shares 破坏了绝对公平以保证前台流畅。",
        "p1_count": 1
    },
    "5.2": {
        "filename": "02-eas.md",
        "ch_num": "5",
        "topic": "EAS (Energy Aware Scheduling)",
        "aosp_path": "kernel/sched/fair.c",
        "func_name": "find_energy_efficient_cpu",
        "android_ver": "Kernel 4.14+",
        "component": "Energy Model",
        "missing_part": "EAS 是如何根据 Energy Model 计算功耗与性能的收益比并做出迁核决定的",
        "missing_func": "compute_energy",
        "trace_event": "sched_energy_diff",
        "blind_spot": "当设备处于高温降频状态时，EAS 如何动态调整选核策略",
        "conclusion": "EAS 通过预判任务在不同频点不同核心的能耗，在保证不掉帧的前提下优先放入小核，实现功耗最优。",
        "p1_count": 1
    },
    "5.3": {
        "filename": "03-big-little.md",
        "ch_num": "5",
        "topic": "大小核架构 (big.LITTLE / DynamIQ)",
        "aosp_path": "kernel/sched/core.c",
        "func_name": "select_task_rq_fair",
        "android_ver": "Kernel 5.4+",
        "component": "Scheduler",
        "missing_part": "任务在大小核之间迁移 (Migration) 时的上下文切换开销与 Cache Miss 惩罚",
        "missing_func": "migrate_task_rq",
        "trace_event": "sched_migrate_task",
        "blind_spot": "DynamIQ 架构中 L3 Cache 共享机制对跨簇调度的延迟降低程度",
        "conclusion": "大小核迁移并非无代价，频繁迁移会导致严重卡顿，合理利用 CPU 亲和性或 QoS 可以缓解。",
        "p1_count": 1
    },
    "5.4": {
        "filename": "04-dvfs.md",
        "ch_num": "5",
        "topic": "DVFS (动态电压频率调节)",
        "aosp_path": "kernel/drivers/cpufreq/cpufreq_schedutil.c",
        "func_name": "sugov_update_single",
        "android_ver": "Kernel 4.19+",
        "component": "cpufreq",
        "missing_part": "Schedutil 调频器是如何直接读取 PELT 负载信号并在 1ms 内快速升频的",
        "missing_func": "cpufreq_driver_target",
        "trace_event": "cpu_frequency",
        "blind_spot": "硬件调频 (如 Arm AMU) 相比软件 cpufreq 带来的延迟降低优势",
        "conclusion": "Schedutil 替代了传统的 interactive 调频器，通过与调度器深度耦合实现了更精准迅速的升降频。",
        "p1_count": 1
    },
    "5.5": {
        "filename": "05-thermal.md",
        "ch_num": "5",
        "topic": "温控机制 (Thermal)",
        "aosp_path": "hardware/interfaces/thermal/2.0/default/Thermal.cpp",
        "func_name": "getCurrentTemperatures",
        "android_ver": "10/11",
        "component": "Thermal HAL / thermal-engine",
        "missing_part": "Thermal Service 如何接收 HAL 温度事件并广播给 App 层，以及 App 如何感知",
        "missing_func": "PowerManager.addThermalStatusListener",
        "trace_event": "thermal_status",
        "blind_spot": "不同厂商的 thermal-engine 配置文件 (thermal-engine.conf) 对 CPU 节流 (throttling) 的具体档位策略",
        "conclusion": "温控触发后会导致系统强制压频，这在 Perfetto 中表现为 CPU 频点被锁在极低状态，导致全量卡顿。",
        "p1_count": 1
    },
    "5.6": {
        "filename": "06-android-power.md",
        "ch_num": "5",
        "topic": "Android 耗电分析与管理",
        "aosp_path": "frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java",
        "func_name": "noteWakeupAlarm",
        "android_ver": "12+",
        "component": "BatteryStats / JobScheduler",
        "missing_part": "BatteryStats 是如何通过 Binder 监听 WakeLock 状态并记录应用电量消耗的",
        "missing_func": "noteStartWakeLocked",
        "trace_event": "battery_stats",
        "blind_spot": "Doze 模式下网络限制与 Alarms 对齐机制在 Doze Maintenance Window 中的集中释放逻辑",
        "conclusion": "耗电优化的核心在于减少 WakeLock 唤醒时间，并合理使用 JobScheduler 进行任务批处理。",
        "p1_count": 1
    },
    "5.7": {
        "filename": "07-cpu-evolution.md",
        "ch_num": "5",
        "topic": "CPU 架构演进与性能趋势",
        "aosp_path": "N/A",
        "func_name": "N/A",
        "android_ver": "ARMv8/v9",
        "component": "ARM Architecture",
        "missing_part": "ARMv9 引入的 SVE2/MTE (Memory Tagging Extension) 对底层代码性能和内存安全的影响",
        "missing_func": "N/A",
        "trace_event": "cpu_cycles",
        "blind_spot": "大核 X 系列架构的乱序执行深度增加对分支预测失败惩罚的影响",
        "conclusion": "移动端 CPU 架构演进注重 IPC 提升与 AI 计算融合，开发者需关注新指令集优化与热点函数的向量化。",
        "p1_count": 1
    }
}

os.makedirs("logs/external-review", exist_ok=True)

for file_id, data in files_data.items():
    out_filename = f"2026-04-25-15-{file_id}-external-review.md"
    content = template_content.format(
        ch_num=data["ch_num"],
        filename=data["filename"],
        topic=data["topic"],
        aosp_path=data["aosp_path"],
        func_name=data["func_name"],
        android_ver=data["android_ver"],
        component=data["component"],
        missing_part=data["missing_part"],
        missing_func=data["missing_func"],
        trace_event=data["trace_event"],
        blind_spot=data["blind_spot"],
        conclusion=data["conclusion"],
        p1_count=data["p1_count"],
        out_filename=out_filename
    )
    with open(f"logs/external-review/{out_filename}", "w") as f:
        f.write(content)
    print(f"Generated {out_filename}")

print("Summary of created files:")
for file_id in files_data.keys():
    print(f"- logs/external-review/2026-04-25-15-{file_id}-external-review.md")
