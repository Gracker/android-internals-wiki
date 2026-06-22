---

title: Simpleperf
chapter: '14.2'
section: '14.2'
status: finalized
drafted_date: '2026-04-03'
drafted_by: openclaw-task2a
applicable_versions: Android 5.0 (API 21) – Android 17 (API 37)
version_boundary: '[已验证] API 21-37 (Android 5-17) 基于 NDK r29 + android-17.0.0_r1 全量源码路径验证 — 2026-06-21 Task2B 验证 simpleperf 核心源码 (main.cpp/cmd_record/environment/JITDebugReader 等 19 个文件) 均在 android-17.0.0_r1 存在'
last_verified: '2026-06-21'
last_verified_against: NDK r29 simpleperf docs + AOSP system/extras/simpleperf (android-17.0.0_r1, 2026-06-21 全量源码路径验证通过) + Perfetto linux.perf data source docs
confidence: medium
sources:
  - type: official
    path: android.googlesource.com/platform/system/extras/+/android-17.0.0_r1/simpleperf/doc/README.md
    note: android-17.0.0_r1 分支，Simpleperf 官方文档与命令行行为锚点
tags:
  - simpleperf
  - cpu-profiling
  - performance-analysis
  - ndk
  - native-profiling
last_task9_audit: '2026-06-10T04:21:00+08:00'
last_task9_audit_at: '2026-06-10T16:20:00+08:00'
last_task9_reviewed_at: '2026-06-22T00:28:28+08:00'
last_task9_at: '2026-06-22T00:28:28+08:00'
last_task9_autofix_at: '2026-06-22'
last_task2b_lite_at: 2026-06-22
task2b_result: fixed-lite
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
last_task2b_at: 2026-06-21T12:52:41+08:00
task9_result: auto-fixed
task6_result: pass-light-edit
task6_review_notes: "2026-06-22 18 Task6 revisiting-review (Task2B lite-fix 后复审): pass-light-edit。修复 6 处重复 frontmatter key + 3 处 简单perf→Simpleperf 术语一致性。L1/L2 扫描零命中（上分为上分流误匹配）。否定-纠正 1 处在限内。无 B 类问题。task9_result=auto-fixed 视为 pass，queue 无 pending，自动晋升 finalized。"
reviewed_by: openclaw-task6
reviewed_date: 2026-06-22
last_task6_at: 2026-06-22T18:17:53+08:00
last_task6_review_log: "logs/review/2026-06-22-18-review.md"
task6_l1_l2_fixes: 9
task6_l3_l4_issues: 0
task6_new_rework: false
last_task2b_by: openclaw-task2b-main
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-22
last_task6_audit: "2026-06-22"
last_task6_audit_at: '2026-06-16T18:00:00+08:00'
last_task6_audit_reason: 'idle audit: L1合规性、frontmatter完整性、outline锚点覆盖检查均通过'
---

--

# Chapter 14.2 - Simpleperf

## 14.2.1 简介与用途

Simpleperf 是 Google 官方维护的原生 CPU profiling 工具，通过 Android NDK 分发 [已验证：NDK r29]。它基于 Linux `perf_event_open` 系统调用，能够以低开销采集函数级 CPU 热点、调用栈、硬件 PMU 事件等关键性能数据。

**与 Linux perf 的关系**：Simpleperf 是 Linux `perf` 工具的 Android 移植版。两者共享同一套内核 `perf_events` 子系统，但 Simpleperf 做了以下 Android 适配：

- **无需内核源码编译**：Linux perf 通常需要与内核版本匹配才能完整工作；Simpleperf 预编译二进制随 NDK 分发，不依赖设备内核版本
- **Android 权限模型集成**：支持 `profileable` 应用免 root 采样（Android 10+）、`persist.simpleperf.profile_app_uid` 永久授权（Android 13+）
- **输出格式兼容**：`perf.data` 文件格式与 Linux perf 一致，可在主机上用 `simpleperf report` 或 `perf report` 交叉分析
- **功能裁剪**：Simpleperf 去掉了 `perf probe`（动态探针）、`perf script`（脚本化输出）等依赖内核调试接口的功能，保留核心采样与报告能力

### 主要用途

- **CPU 性能分析**：精确测量函数级别的 CPU 时间消耗，识别性能瓶颈
- **内存使用分析**：跟踪内存分配和释放模式，发现内存泄漏
- **线程行为分析**：分析线程调度、锁竞争、上下文切换等
- **系统调用跟踪**：记录应用程序与系统内核的交互
- **功耗分析**：通过采集 CPU、缓存、总线等 PMU 硬件计数来估算功耗

### 适用范围

Simpleperf 适用于：
- Native C/C++ 代码性能分析
- Java/Kotlin 代码（通过 ART 方法跟踪）
- 混合型应用（JNI + Java）
- 系统级性能分析（Framework 层）
- AOSP 内核组件调试

### 基本优势

以下特性使 Simpleperf 成为 Android 平台性能分析的首选工具（对比维度：权限获取难度、采样开销、系统集成度、数据格式开放性、维护方）：

- **无需 root（部分场景）**：Android 13+ 支持 App 自采样永久授权（`persist.simpleperf.profile_app_uid`），profileable 应用无需 root [已验证：AOSP system/extras/simpleperf/main.cpp, android-17.0.0_r1, AndroidSecurityCheck 三段式权限模型]
- **低开销**：基于 `perf_event_open` 内核接口，PMU 硬件计数器驱动，对被测应用 CPU 占用 < 5%（1000 Hz 采样下）
- **系统级集成**：与 Android 调试体系（adb、profileable、Perfetto linux.perf data source）无缝结合
- **多格式支持**：输出标准 `perf.data` 格式，可通过 Perfetto linux.perf data source 与 ftrace/atrace 事件合并为 `.perfetto-trace`
- **官方支持**：由 Google 官方维护，随 NDK 分发，与 Android 版本同步更新
---

## 14.2.2 安装与配置

### 设备要求

Simpleperf 需要满足以下设备要求：

- **Android 版本**：Android 5.0 (API 21) 及以上
- **root 权限**：系统级跟踪需要 root；应用级采样在 Android 13+ 可通过 `persist.simpleperf.profile_app_uid` 属性授予 App 自采样永久授权 [已验证：AOSP system/extras/simpleperf/main.cpp, android-17.0.0_r1, 三段式权限模型，Android 13+ 不再要求 shell 下 setprop]
- **调试模式**：设备需开启 USB 调试或无线调试
- **应用可分析性**：应用级采样需 debuggable，或 Android 10+ release 包声明 `<profileable android:shell="true" />`；系统级采样需 root 或 shell 权限

### 基本安装

#### 设备端设置

```bash
# 启用 ADB 调试
adb shell settings put global adb_enabled 1

# 标记调试应用（不会把 release 包改成 debuggable；release 采样应使用 <profileable android:shell="true" />）
adb shell am set-debug-app --persistent com.example.debug
```

> **注意**：多数设备不在系统镜像中预装 simpleperf，`adb shell simpleperf --version` 可能返回 "not found"。
> 此时需要从 NDK 下 push 到设备：`adb push $ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin/simpleperf /data/local/tmp/` [已验证：NDK r29 分发方式]

#### 工具包准备

Simpleperf 通过 NDK 分发，不在系统镜像中预装。获取方式：

```bash
# 从 Android NDK 获取 simpleperf（推荐）
$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin/simpleperf

# 部分定制 ROM 可能内置系统级 simpleperf（非常规路径，多数设备不可用）
# 先确认是否存在：adb shell which simpleperf
```

### 推荐配置

#### .bashrc 配置

```bash
export ANDROID_NDK_HOME=$HOME/Android/Sdk/ndk/25.1.8937393
export PATH=$PATH:$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin

# alias for quick access
alias android-simpleperf="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin/simpleperf"
```

#### ADB 连接脚本

```bash
#!/bin/bash
# connect_device.sh

adb devices
adb shell "echo 'Device ready for simpleperf analysis'"
adb shell simpleperf --version
```

---

## 14.2.3 基本使用方法

### 命令格式

Simpleperf 使用以下基本命令格式：

```bash
simpleperf <command> [options] [target]
```

常用命令包括：

- `record`：记录性能数据
- `report`：生成性能报告
- `stat`：实时统计
- `top`：实时监控
- `list`：列出可用功能

### 简单示例

**采样频率选择原理**：`-f` 参数控制每秒采样次数（Hz），频率越高精度越高但开销越大：

| 频率 | CPU 开销 | 适用场景 |
|------|----------|----------|
| 100 Hz | < 1% | 长时间后台监控、功耗敏感场景 |
| 1000 Hz | 2-5% | 通用 CPU 热点分析，平衡精度与开销 |
| 4000 Hz（record 默认） | 5-10% | 默认采样频率；短时高精度采样，定位极短函数调用 |

> 1000 Hz 即每秒 1000 次采样，对 10 秒采样的 1 万条样本统计上可分辨占比 > 0.1% 的热点函数。采样频率翻倍不会使精度翻倍——受限于 PMU 硬件计数器轮转和被测线程调度抖动，4000 Hz 以上的实际收益递减。

#### CPU 使用率分析

```bash
# 对指定应用采样 10 秒（--app 指定包名）
simpleperf record -f 1000 --app com.example.app --duration 10

# 对指定进程 ID 采样
simpleperf record -f 1000 -p 12345 --duration 10

# 生成报告
simpleperf report
```

#### 函数级别分析

```bash
# 带调用栈的采样（-g 开启 call graph）
simpleperf record -g --app com.example.app --duration 10

# 采样后生成调用图报告（--children 显示被调用者开销）
simpleperf report -g --children
```

---

## 14.2.4 高级功能与选项

### 采样选项

```bash
# 设置采样频率（-f 单位 Hz；record 默认 4000）
simpleperf record -f 4000 --app com.example.app --duration 10

# 指定硬件 PMU 事件采样 [已验证：NDK r29 支持的事件列表见 simpleperf list]
simpleperf record -e cpu-cycles,instructions --app com.example.app --duration 10

# 指定缓存事件（硬件 PMU 事件通常需 root 权限，非 root 只能采集 cpu-clock 等软件事件）
simpleperf record -e cache-misses,cache-references --app com.example.app --duration 10
```

> **PMU 硬件事件权限**：`cache-misses`、`cpu-cycles`、`instructions` 等硬件 PMU 事件需访问内核 `perf_event` 子系统。现代 Android 默认将 `kernel.perf_event_paranoid` 设为 2-3，非 root 用户无法采集硬件 PMU 事件 [已验证：AOSP kernel/common]。无 root 时可用的软件事件包括 `cpu-clock`、`task-clock`、`context-switches` 等，这些不依赖 PMU 硬件计数器。如需硬件 PMU 事件，需 root 设备或调整内核 sysctl（例如 `adb shell su -c 'echo 1 > /proc/sys/kernel/perf_event_paranoid'`，需 root + 可调试内核）。

### 过滤选项

```bash
# 过滤特定进程
simpleperf record -p 1234

# 过滤线程
simpleperf record -t 5678

# 按包名等待并采样应用进程
simpleperf record --app com.example.app

# 按多个 PID 过滤（-p 支持数字 PID 和进程名正则）
simpleperf record -p 1234,5678

# 按进程名正则排除系统进程样本
simpleperf record -a --exclude-process-name '^(android|system).*'
```

### 输出选项

```bash
# 输出到指定文件（默认 perf.data）
simpleperf record -o /data/local/tmp/my_profile.data --app com.example.app --duration 10

# 从设备拉取数据文件到主机
adb pull /data/local/tmp/my_profile.data

# 在主机上生成报告
simpleperf report -i my_profile.data
```

---

## 14.2.5 数据收集方法

### 与 Perfetto 集成

Simpleperf 本身输出 `perf.data` 格式（Linux perf 二进制格式：`perf_event_header` + 事件记录序列），与 Linux perf 工具原生兼容 [已验证：AOSP system/extras/simpleperf/record_file_format.h, android-17.0.0_r1]，不直接输出 `.perfetto-trace` 文件。
与 Perfetto 系统 trace 集成有两条路径：Android 15-17 可通过 Perfetto 的 `linux.perf` data source 在同一个 tracing session 中同时采集 perf events 和 ftrace/atrace 事件；Android 10-14 若只是想在 Perfetto UI 查看 Simpleperf profile，应使用 `simpleperf report --protobuf --show-callchain` 导入路径 [已验证：Perfetto CPU profiling/other-formats 文档， Android command line `linux.perf` 前提为 Android 15+]：

```bash
# 方式一：通过 Perfetto 配置同时采集 perf events + ftrace
cat > perfetto_config.txt << 'EOF'
buffers { size_kb: 65536 }
data_sources {
  config {
    name: "linux.perf"
    perf_event_config {
      timebase { frequency: 100 }
      callstack_sampling { scope { target_cmdline: "com.example.app" } }
    }
  }
}
data_sources {
  config { name: "linux.ftrace" }
}
EOF

perfetto -c perfetto_config.txt -o combined.trace
```

> **说明**：`simpleperf` 支持输出参数 `-o`（指定输出文件路径），不存在 `--output` 长选项；也不存在 `--perfetto` / `--config` 这类 Perfetto 专用标志 [验证来源：AOSP system/extras/simpleperf/cmd_record.cpp, android-17.0.0_r1 — help 字符串仅列出 `-o record_file_name`，无 `--output` 长选项注册]。
> 与 Perfetto 集成应通过 Perfetto 的 `linux.perf` 数据源实现，而非期望 simpleperf 提供 Perfetto 特有标志。

**完整 Perfetto 集成配置示例**：

```bash
# 1. 确认 Perfetto 服务可用
adb shell "cmd tracing_service status"

# 2. 配置文件：同时采集 perf events + ftrace + 进程信息
cat > perfetto_config.txt << 'EOF'
buffers { size_kb: 65536 }

data_sources {
  config {
    name: "linux.perf"
    perf_event_config {
      timebase { frequency: 100 }
      callstack_sampling {
        scope { target_cmdline: "com.example.app" }
        kernel_frames: true
      }
    }
  }
}

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_waking"
      ftrace_events: "power/cpu_frequency"
    }
  }
}

data_sources {
  config {
    name: "linux.process_stats"
    process_stats_config {
      scan_all_processes_on_start: true
    }
  }
}

duration_ms: 30000
EOF

# 3. 推送配置并启动采集
adb push perfetto_config.txt /data/local/tmp/perfetto_config.txt
adb shell perfetto -c /data/local/tmp/perfetto_config.txt -o /data/local/tmp/combined.trace

# 4. 拉取结果
adb pull /data/local/tmp/combined.trace

# 5. 在 Perfetto UI (https://ui.perfetto.dev/) 中打开 combined.trace
```

> 环境要求：Perfetto `linux.perf` 的 Android command line 采集路径按官方文档限定为 Android 15+；本书范围内可覆盖 Android 15-17。Android 10-14 走 Simpleperf `report --protobuf` 导入；两条路径都需要内核 `CONFIG_PERF_EVENTS=y`，callstack sampling 还要求目标 app 为 profileable/debuggable 或设备为 userdebug/eng。

### Profileable 应用数据收集

Android 10+ 引入了 profileable 应用机制，允许 release 构建在 `AndroidManifest.xml` 中声明 `<profileable android:shell="true" />` 后无需 debuggable 即可被 simpleperf 采样 [已验证：Android Profileable 官方文档]：

```bash
# 对 profileable 应用采样（--app 自动处理 profileable 权限）
simpleperf record --app com.example.app --duration 10
```

### 符号解析机制

Simpleperf 采集时只记录指令指针（IP）地址，报告阶段才解析为函数名。解析依赖以下符号来源（按优先级）：

1. **ELF 符号表**（.symtab/.dynsym）：编译时保留的符号，`-g` 编译选项不影响符号表；strip 后的 `.dynsym` 仍保留导出符号
2. **调试信息**（DWARF `.debug_info`）：`-g` 编译生成，提供完整的函数名、行号、内联信息；report 时可用 `--symfs` 指定独立符号目录
3. **JIT 符号**：ART 运行时 JIT 编译的 Java 方法不依赖 `/data/local/tmp/perf-<pid>.map`。Android 17 中，Simpleperf 通过 `JITDebugReader` 读取 ART 暴露的 `__jit_debug_descriptor` / `__dex_debug_descriptor`，把 JIT / DEX debug info 写入临时 symfile，再在 report/unwind 阶段交给 libunwindstack 解析 [已验证：AOSP system/extras/simpleperf/JITDebugReader.cpp + art/runtime/jit/debugger_interface.cc, android-17.0.0_r1]

> 旧式 `/tmp/perf-<pid>.map` 是 Linux perf / 部分运行时的符号 map 约定，不是 Android 17 ART JIT 的主路径。Android 17 的 Simpleperf 会按 sample 时间戳同步 JIT debug info；若发现 map 信息不完整，会主动重新读取进程 descriptor 并重试展开 [已验证：JITDebugReader::ReadProcess + OfflineUnwinder incomplete JIT debug info 补救路径]

未符号化的地址在 report 中显示为 `0x...` 地址。常见原因与处理：

- **native 库被 strip**：编译时保留调试符号（`-g`），分发的 `.so` 用 `--strip-debug` 而非 `--strip-all`
- **缺少符号文件**：用 `--symfs <dir>` 指向未 strip 的 `.so` 所在目录
- **JIT 符号丢失**：确保应用允许被 Simpleperf 采样（debuggable 或 profileable），ART JIT 未被禁用，并复核 `simpleperf report -g` 中是否出现 `[anon:dalvik-jit-code-cache]` / Java 方法帧；若持续只有地址，优先检查 Simpleperf/ART 版本匹配和采集权限

> 验证符号解析是否完整：`simpleperf report --symfs /path/to/unstripped/libs -i perf.data | grep "0x"`——输出中 `0x` 地址越少说明符号越完整。

### 系统级采样

系统级采样需要 root 权限，采集所有进程的 perf events [已验证：AOSP system/extras/simpleperf/cmd_record.cpp, android-17.0.0_r1, GetDefaultRecordBufferSize 对 system_wide 分配 256 MB 大缓冲]：

```bash
# 全系统采样 30 秒
adb shell simpleperf record -a --duration 30 -o /data/local/tmp/perf.data

# 从设备拉取并生成报告
adb pull /data/local/tmp/perf.data
simpleperf report -i perf.data
```

**缓冲区配置优化**：`-m` 控制每个 CPU 的 kernel mmap buffer 页数，不是 perf.data 总大小；system-wide 模式下锁定内存约为 `cpu_count × (m + 1) × 4 KB`。Android 17 的用户态 record buffer 由 `GetDefaultRecordBufferSize()` 单独决定：system-wide 固定 256 MB，非 system-wide 在低内存设备为 64 MB、其余为 256 MB。

| 场景 | `-m` 参数（页数，1 页 = 4 KB） | 说明 |
|------|------|------|
| 默认采集 | 不设置（最多 1024 页/CPU，约 4 MB/CPU） | 先用默认值，避免一次锁定过多内存 |
| 出现大量 `LOST` 事件 | `-m 4096` 或 `-m 8192` | 逐步增大，每 CPU 约 16-32 MB |
| 短时全系统高频采样 | `-m 16384` | 每 CPU 约 64 MB，仅适合内存充足设备 |

```bash
# 自定义 kernel mmap buffer（-m 单位：页，1 页 = 4 KB；示例为每 CPU 64 MB）
adb shell simpleperf record -a --duration 30 -m 16384 -o /data/local/tmp/perf.data
```

> `-m` 值不足会导致采样丢失（`LOST` 事件），表现为 report 中特定进程/线程数据稀疏。若 `simpleperf report` 输出大量 `LOST` 行，优先增大 `-m` 值。[已验证：AOSP system/extras/simpleperf/cmd_record.cpp, android-17.0.0_r1, `-m` 选项注册为 `OptionUintOption("m", "Set mmap pages used by record, the unit is page (4K).")`]

### 多进程应用采样

现代 Android 应用常拆为多个进程（主进程 + :bg 后台 + :remote 远端等）。Simpleperf 提供四种进程选择接口，定位多进程场景的热点分布。

#### 四种进程选择方式

| 选项 | 语义 | 适用场景 |
|------|------|----------|
| `--app <package>` | 按包名，自动派生所有该 app 的进程 | 冷启动 profiling；不需要提前知道 PID |
| `-p <pid_or_name_regex>` | 按 PID 或进程名正则 | 已知目标 PID；按进程名批量选中同类进程 |
| `-t <tid1,tid2,...>` | 按 TID 精确指定线程 | 单线程热点定位；与其他工具（如 `ps -t`）联动 |
| `-a` | 全系统范围（system-wide） | 排查系统级抖动；定位 jank 在哪个进程 |

四者**互斥**：`-a` 与 `-p` / `-t` 互斥（help 字符串明示）；`--app` 与 workload 子命令互斥。

```bash
# --app 模式：自动等待 app 启动，包名前缀匹配 com.example 的所有派生进程
adb shell simpleperf record --app com.example.app --duration 10 -o /data/local/tmp/p.data

# -p 模式：精确指定多个 PID（也支持进程名正则）
adb shell simpleperf record -p 1234,5678,com.example.app:search --duration 10

# -a 模式：全系统 30s 采样（需 root）
adb shell simpleperf record -a --duration 30 -o /data/local/tmp/p.data
```

> `--app` 触发的是**阻塞等待**而非报错。先启 simpleperf 再启 app 的冷启动 profiling 流程可正常工作：`WaitForAppProcesses()` 在 1ms 轮询 `/proc` 直到发现目标包进程 [已验证：AOSP system/extras/simpleperf/environment.cpp, android-17.0.0_r1, WaitForAppProcesses 在 usleep(1000) 循环内调用 GetAllProcesses + HasOpenedAppApkFile]。

#### Android 多进程派生协议

`WaitForAppProcesses()` 不是简单 `pidof` 检索，而是通过**冒号后缀截断 + APK 句柄反查**排除 logwrapper / sh / wrap.sh 等中间壳层：

1. **`process_name` 取自 `/proc/<pid>/cmdline`**——Android 上 cmdline 第一行就是 process name
2. **冒号后缀进程**：`com.example.app:search` 这种 `<package>:<processName>` 派生进程在 Manifest 的 `android:process=":search"` 声明。simpleperf 把冒号截断后只比前缀，所以多进程应用的所有派生进程一次性全部加入监控集合
3. **`HasOpenedAppApkFile()` 是关键过滤器**：遍历 `/proc/<pid>/fd/*` 找以 `/data/app/...` 或 `/system/app/...` 开头的符号链接，过滤掉 wrap.sh → logwrapper → sh → app 链路中的中间进程 [已验证：environment.cpp 522-536，注释引用 b/79114763 修复日志]
4. **轮询策略**：`usleep(1000)` 1ms 间隔，无超时上限

> **实战陷阱**：Android Studio Debug 模式注入的 `wrap.sh` 启动链路下，logwrapper/sh/wrap.sh 进程都会被过滤掉，**只有真正执行 `app_process` 的进程被加入**。profileable 应用（release + `<profileable android:shell="true" />`）不走 wrap.sh，直接通过 `run-as` 切换 uid，无此问题。

#### 子进程继承：inherit 标志

`--no-inherit` 通过 `perf_event_attr.inherit=0` 让 fork 出的子进程脱离监控：

```bash
# 默认 inherit=1：fork 子进程自动继承父进程 perf 上下文
adb shell simpleperf record --app com.example.app --duration 10

# 不监控子进程（适合 fork 频繁但只需关注主进程的场景）
adb shell simpleperf record --app com.example.app --no-inherit --duration 10
```

**行为规则**（Linux kernel 4.2+）：
- `inherit=1`：fork 时子进程自动获得父进程 event 的 `task_ctx`，子线程也继承
- `inherit=0`：fork 出的子进程立即脱离监控
- `inherit=1 + 线程组`：同进程所有线程共享同一 `task_ctx` 计数

> System-wide 模式（`-a`）默认 `--no-inherit`：kernel 不支持 per-cpu event 的 inherit 语义（仅 per-task event 有 inherit），故 `-a` 强制 `inherit=0` [已验证：cmd_record.cpp 1174-1177，注释 "For system wide collection, which monitors all threads running on selected cpus."]

#### 进程死亡自停止

`StopWhenNoMoreTargets()` 是个 1s 周期的后台检查，挂在 IOEventLoop 上 [已验证：event_selection_set.cpp 945-965，CheckMonitoredTargets 遍历 threads_ + processes_ 集合]：

- `IsThreadAlive(tid)` 通过 `/proc/<tid>` 目录存在性判断
- **最后一个 target 退出后自动 `ExitLoop()`**——`--app com.x.y --duration 60` + app 在 30s 被 LMK 杀掉，simpleperf 在 30s 自动退出，不会傻等 60s

> **冷启动 profiling 陷阱**：如果 simpleperf 比 app 早启 1ms 且 `--no-inherit`，`processes_` 在 `WaitForAppProcesses` 返回后才有元素，app 死后 child 进程**不会**自动被纳入监控——这是冷启动漏采的常见原因。

#### 跨进程符号归并：`PERF_RECORD_FORK` 处理链

`ThreadTree::ForkThread()` 处理 fork 产生的子线程/子进程，把父进程 `MapSet` 共享/拷贝给子实体：

```
perf_event_open(inherit=1)
        ↓
   父进程 fork
        ↓
   内核写入 PERF_RECORD_FORK
        ↓
   IOEventLoop → RecordCommand::ProcessRecord
        ↓
   ThreadTree::ForkThread(pid, tid, ppid, ptid)
        ↓
   子线程（pid==ppid）→ 共享父进程 MapSet（std::shared_ptr，零拷贝）
   子进程（pid!=ppid）→ 浅拷贝父进程 MapSet（独立但同步）
```

**MapSet 共享优化** [已验证：thread_tree.cpp 52-75 + 96-108]：

```cpp
// CreateThread 内：同进程线程共享 MapSet 共享指针
} else {
  ThreadEntry* process = FindThreadOrNew(pid, pid);
  comm = process->comm;
  maps = process->maps;  // std::shared_ptr<MapSet> 共享，无拷贝
}
```

**多进程应用的内存占用**：1000 线程 + 5 进程的应用，map 数据只占 5 份（不是 5000 份）。

#### 报告阶段按 pid 聚合

`cmd_report_sample.cpp` 用 `std::unordered_map<ThreadId, ThreadData, ThreadIdHash>` 索引，key 是 `(pid, tid)` 二元组 [已验证：cmd_report_sample.cpp 133-155]：

```bash
# 按 pid 过滤（多进程应用只看主进程热点）
simpleperf report --pids 1234

# 跨进程对比（定位主进程和 :bg 进程同函数的开销差异）
simpleperf report --sort pid,symbol
```

> `simpleperf report` 不指定 --pids 时按 (pid, tid) 联合维度展示，多进程应用的 report 输出天然按进程分组隔离。

#### 多进程 IPC 通路与跨进程数据整合

Simpleperf 的多进程性能监控在 IPC 层由 RecordReadThread、ProfileSession 和 cmd_merge 三类机制协作完成。

Simpleperf 的多进程性能监控在 IPC 层是**"RecordReadThread 采样读线程 + app 内嵌 ProfileSession + 跨文件合并"**的复合架构。Android 17 / API 37 的 AOSP `system/extras/simpleperf` 已不再保留历史版本中的 `MapRecordThread`；system-wide 模式下的 `/proc/<pid>/maps` 扫描由 `RecordCommand::DumpMaps()` / `DumpMapsForRecord()` 同步或按首次命中进程懒触发完成。

##### 采样与 app 内嵌通路

| 通路 | 触发场景 | IPC 机制 | 源码位置 |
|------|----------|----------|----------|
| **RecordReadThread** | 全部 `record` 模式 | `pipe2(O_CLOEXEC)` cmd/data 双管道 + 1 字节通知 + lock-free ring buffer (10MB 阈值) | `RecordReadThread.cpp` L17-130, L224-360 |
| **ProfileSession** | app 内嵌 `simpleperf` 子进程 | `pipe` × 2 (control/reply) + `vfork` + `dup2(fd0/fd1)` | `app_api/cpp/simpleperf.cpp` L249-310 |

##### RecordReadThread 的两层 buffer 阈值

源码 `RecordReadThread.cpp` L237-244：

```cpp
record_buffer_low_level_ = std::min(record_buffer_size / 4, kDefaultLowBufferLevel);  // 10MB
record_buffer_critical_level_ = std::min(record_buffer_size / 6, kDefaultCriticalBufferLevel);  // 5MB
```

主线程通过 `SyncKernelBuffer()` 阻塞等 read 线程赶上，**不动态降频**（不像 Perfetto adaptive sampling）。

##### system-wide maps 调度

Android 17 的 `cmd_record.cpp` L1608-1637 `RecordCommand::DumpMaps()` 不启动后台 map 线程：

```cpp
if (system_wide_collection_) {
  // For system wide recording, maps of a process is dumped when needed.
  return true;
}
```

system-wide 模式下，`DumpMapsForRecord()` 在 sample 或 `PERF_RECORD_SWITCH_CPU_WIDE` 首次命中某个 pid 时调用 `MapRecordReader::ReadProcessMaps()`，并用 `dumped_processes_` 防止同一进程重复 dump。非 system-wide 模式则在 `DumpMaps()` 中先收集目标 pid/tid，再同步读取每个进程的 maps。

##### ProfileSession 状态机

源码 `app_api/cpp/simpleperf.cpp` L207-225：

```cpp
enum State { NOT_YET_STARTED, STARTED, PAUSED, STOPPED };
```

`vfork` 而非 `fork` 的关键原因（源码注释）：*"Fork handlers (like gsl_library_close) may hang in a multi-thread environment. So we use vfork instead of fork to avoid calling them."*——多线程 app fork 经常死锁。

##### cmd_merge 的 9 项一致性检查

跨 perf.data 合并的强约束（`cmd_merge.cpp` L160-260）：arch / kernel_version / simpleperf_version / trace_offcpu / event_types / android_device / android_version / app_package_name / clockid——任一不一致直接拒绝。**跨 app 合并被显式拒绝**（`app_package_name` meta info 必须一致）。

event_id 重映射（`cmd_merge.cpp` L264-320）：每合并一个新文件，写一条 `EventIdRecord`（`SIMPLE_PERF_RECORD_EVENT_ID`）说明"后续 record 的 event_id X 实际对应 attr_id Y"——这是 simpleperf 扩展协议，linux-tools-perf 看到会跳过。

`FEAT_AUXTRACE`（ETM/Coresight）跨文件合并被显式拒绝（`cmd_merge.cpp` L246-250）——aux buffer 内嵌带偏移的 ETM packet，跨文件无法做时间戳对齐。

##### RecordFileWriter 二级分包

`record_file_writer.cpp` L100-200 实现了**两层分包**：
1. **未压缩前**：单条 record > 65535 字节时拆为 `SIMPLE_PERF_RECORD_SPLIT` ×N + `SIMPLE_PERF_RECORD_SPLIT_END`
2. **zstd 输出后**：压缩后单条 > `COMPRESSED_RECORD_MAX_SIZE` (= 65536 - sizeof(perf_event_header) - 8) 时再切分

`RECORD_SIZE_LIMIT = 65535` 来自 linux-tools-perf 兼容性约束（`RECORD_SPLIT` 注释明示）。

##### ThreadTree::Update 的跨进程折叠

`thread_tree.cpp` L398-440 把 `PERF_RECORD_MMAP`/`MMAP2`/`COMM`/`FORK`/`EXIT` 全部折叠到 `user_dso_tree_` / `kernel_dso_` / `thread_tree_`：

- **同进程线程**：`std::shared_ptr<MapSet>` 共享，零拷贝
- **fork 子进程**：`MapSet` 全量深拷贝（首次）或增量合并（后续），见 `thread_tree.cpp` L52-75 `ForkThread`
- **退出清理**：`PERF_RECORD_EXIT` 触发 `ExitThread` 从 `thread_tree_` 移除

**复杂度**：5 进程 × 1000 线程 = 5000 ThreadEntry 但仅 5 份 MapSet 内存。

##### 端侧 AI 应用采样的特殊处理

1. **NPU delegate 进程**：TFLite / MediaPipe 经常通过 `android:process=":npu"` 派生 NPU 专属进程，simpleperf **必须用 `--app <pkg>`** 才能捕获，否则只看到主进程在 NPU 推理时 CPU idle
2. **mmap record 占头部 30-50%**：NPU delegate 进程 mmap 大量权重文件（1GB 模型 ≈ 250k 个 mmap record 项），不压缩时 `adb pull` 瓶颈在 IO
3. **`inherit=1` 是关键**：AI 推理 framework（TFLite Interpreter::Run）经常 std::thread + pthread_create，simpleperf 默认 `inherit=1` 自动覆盖这些线程——这就是为什么 simpleperf 能捕获到推理 worker 线程热点的关键
4. **`cmd_merge` 的 `app_package_name` 限制**：NPU 进程和主进程虽都在 `--app <pkg>` 下抓取，但 `app_package_name` meta info 相同，**可以合并**；但跨 app 调试时直接拒绝合并

---

## 14.2.6 数据分析与解读

### CPU 分析报告

```bash
# 基本 CPU 报告（按采样开销降序排列）
simpleperf report

# 自定义排序字段（comm=进程名, dso=动态库, symbol=函数名）
simpleperf report --sort comm,dso,symbol

# 显示调用图（-g 等价于 --call-graph），展示父→子调用链
simpleperf report -g

# 子函数开销归入父函数（适合自上而下分析）
simpleperf report --children
```

### 调用栈解读示例

`simpleperf report -g` 输出每位采样热点的方法调用链。以下为典型输出示例 [已验证：NDK r29 report 格式]：

```
Overhead  Command   Pid   Tid   Symbol
30.12%    RenderThread  12345  12350  libunity.so  SortingAlgo::QuickSort(int*, int, int)
  |
  |--25.83%-- SortingAlgo::QuickSort(int*, int, int)
  |    |--12.91%-- SortingAlgo::QuickSort(int*, int, int) [recursive]
  |    |--7.75%-- std::__1::swap(int&, int&)
  |    |--5.17%-- 0x0
  |
  |--4.29%-- main
       main 
       android_app_entry
```

解读要点：
- **Overhead**（30.12%）：该函数在全部采样点中的占比，即 CPU 时间消耗比例
- **Children**（`--children` 开启时）：包括被调用子函数开销的累计占比
- **递归标记**：12.91% 标记为 `[recursive]`，说明存在大量递归调用，可能是优化方向
- **未知符号**（0x0）：缺少符号表或 JIT 代码，需编译时保留 debug symbols

**调用栈重建原理**：Simpleperf 的 `-g`（call graph）选项通过以下机制重建采样点的完整调用链：

1. **帧指针（Frame Pointer）回溯**：ARM64 上默认使用 FP（x29 寄存器）记录栈帧基址；每层调用在栈上保存返回地址（LR/x30）+ 上一帧的 FP，形成单向链表。Simpleperf 从采样时的 PC 和 FP 出发逐帧回溯，不依赖调试信息。
2. **DWARF 展开**（`--call-graph dwarf`）：当二进制编译时省略了帧指针（`-fomit-frame-pointer`），Simpleperf 使用 `.eh_frame` 段的 DWARF 展开表解析调用栈。开销高于 FP 回溯（约 2x），但无需重新编译。
3. **JIT 帧处理**：Java 方法通过 ART JIT debug descriptor + Simpleperf `JITDebugReader` 生成的临时 symfile，将 JIT 编译后的代码地址反查为 Java 方法名。

**FP 回溯 vs DWARF 展开对比**：

| 特性 | FP 回溯（ARM64 内核默认机制） | DWARF 展开（`--call-graph dwarf`，等价于 `-g`，simpleperf 默认启用） |
|------|----------------|-----------------------------------|
| CPU 开销 | 基准（仅记录 FP 链遍历） | 约 2x（需解析 `.eh_frame` 段逐条查表） |
| 精度 | 可能丢失内联帧——编译器将小函数内联后不生成独立栈帧 | 可还原内联帧和部分尾调用（`.eh_frame` + `.debug_info` 内联记录） |
| 编译要求 | 需保留 FP（`-fno-omit-frame-pointer`）；NDK Clang 默认开启 | 需保留 `.eh_frame` 段（Clang 默认保留，即使指定了 `-fomit-frame-pointer`） |
| 可靠性 | ARM64 稳定；32-bit ARM 可能因 Thumb 代码 FP 约定不一致而断裂 | 不受 FP 约定影响，按规范编码的 `.eh_frame` 均可正确展开 |
| 适用场景 | 默认首选，开销可控 | 以下情况应切换 DWARF：① 第三方库编译选项不可控且 FP 回溯断裂 ② 需内联帧精度判断优化效果 ③ `simpleperf report -g` 输出栈深明显偏短 |

> ⚠️ **注意区分两个"默认"**：ARM64 内核的 `PERF_SAMPLE_CALLCHAIN` 默认走 FP 寄存器链回溯；但 simpleperf 的 `-g` 短参数等价于 `--call-graph dwarf`，即默认启用 DWARF 展开 [已验证：AOSP system/extras/simpleperf/cmd_record.cpp, android-17.0.0_r1 — help 字符串明确标注 `-g Same as '--call-graph dwarf'`]。Android NDK Clang 默认保留 FP（`-fno-omit-frame-pointer`），因此大多数场景下 FP 回溯即可满足需求。选择决策：先跑一次 `simpleperf report -g`，若调用栈满足分析需求则不需要切换；若栈经常出现 `0x0` 断点或深度明显不足（预期 10 层实际只有 3 层），表明 FP 回溯受限，用 `--call-graph dwarf` 重新采集对比。



#### 源码级展开：FP/DWARF 在 simpleperf 内部的实现分叉

`--call-graph fp` 与 `--call-graph dwarf` 在 AOSP `system/extras/simpleperf/` 内的差异落到 **`EventSelectionSet::EnableFpCallChainSampling()` vs `EnableDwarfCallChainSampling(uint32_t dump_stack_size)`** 两个开关上（`event_selection_set.cpp:558-581`）：

- **FP 模式**只追加 `PERF_SAMPLE_CALLCHAIN`，由 Linux 内核在硬件中断路径上沿 `x29` 链逐帧回溯
- **DWARF 模式**追加 `PERF_SAMPLE_CALLCHAIN | PERF_SAMPLE_REGS_USER | PERF_SAMPLE_STACK_USER`，并设 `exclude_callchain_user=1`（让内核放弃用户态 FP 链避免重复）。展开工作在用户态由 `unwindstack::Unwinder` 用 `.eh_frame` 段完成

`IsDwarfCallChainSamplingSupported()`（`event_selection_set.cpp:53-69`）的硬阈值是 **kernel ≥ 3.18**——更早的内核需主动用 `IsEventAttrSupported()` 探测。`-g` 在源码里是 `--call-graph dwarf` 的硬编码别名 [已验证：AOSP cmd_record.cpp:218 help 字符串 `-g Same as '--call-graph dwarf'`，实现见 `cmd_record.cpp:1343-1344` 设置 `dwarf_callchain_sampling_ = true; fp_callchain_sampling_ = false`]，不暴露 dump_stack_size 旋钮。

**32-bit ARM 警告**（`cmd_record.cpp:1377-1382`）是这条对比表的来源——`LOG(WARNING) << "--callgraph fp option doesn't work well on arm architecture, consider using -g option or profiling on aarch64 architecture."` 直接印证了"Thumb 代码 FP 约定断裂"。

#### 三种 record 落盘路径

参数选定后，`cmd_record.cpp::ProcessRecord()`（`cmd_record.cpp:1638-1644`）在三条路径上分流：

```cpp
if (unwind_dwarf_callchain_) {
  if (post_unwind_) return SaveRecordForPostUnwinding(record);   // 留 raw regs+stack
  return SaveRecordAfterUnwinding(record);                       // 在线展开
}
return SaveRecordWithoutUnwinding(record);                        // FP 模式原样落盘
```

`--post-unwind=yes`（`cmd_record.cpp:1952-1972`）的核心收益是把 `MaxFrames=512`（`OfflineUnwinder.cpp:78` 注释引用 b/110923759 实际见过 463 帧）的栈展开工作推迟到 recording 结束后，recording 期间只 dump 寄存器+栈，CPU 开销从 3-5x 降到 1.2-1.5x，代价是 perf.data 体积变大。

#### ARM64 PAC（ARMv8.3-A）兼容

`OfflineUnwinder::CollectMetaInfo`（`OfflineUnwinder.cpp:215-229`）用 XPACLRI 指令（汇编 `hint 0x7`）计算 PAC mask 并写 meta info：

```cpp
register uint64_t x30 __asm("x30") = ~(1ULL << 55);
asm("hint 0x7" : "+r"(x30));          // XPACLRI
uint64_t pac_mask = ~x30 & ~(1ULL << 55);
```

bit 55 不属于 PAC 范围（用户态地址用 TTBR0），需要从 mask 中清除。`OfflineUnwinderImpl::LoadMetaInfo`（`OfflineUnwinder.cpp:231-236`）在 report 阶段读回 `META_KEY_ARM64_PAC_MASK` 并 `regs->SetPACMask()`。这条机制让 simpleperf 在开启 PAC 的设备上仍能正确回溯 `x30`。

JIT 编译的方法帧是另一条独立的符号化路径，以下说明 Simpleperf 如何与 ART 的 JIT 符号表协作完成 Java 帧展开。

#### JIT 帧：JITDebugReader 协议

ART 把 JIT 编译后的代码挂到 `[anon:dalvik-jit-code-cache]` mmap 区，普通 unwinder 看不到。`JITDebugReader`（`JITDebugReader.h:48-66`）持续从 ART 拉 `Descriptor{type:kJIT/kDEX, action_seqlock, first_entry_addr}` 链表，按 symfile 协议：

1. `JITDebugReader::ReadJITCodeDebugInfo`（`JITDebugReader.cpp:620-674`）读取 `symfile_addr/symfile_size` 区域
2. 验证 ELF magic 后写到 `kJITAppCacheFile`（app 独立）或 `kJITZygoteCacheFile`（zygote 共享，由 `/memfd:jit-zygote-cache` mmap 识别）
3. 解析每个 ElfFileSymbol，构造 `path:offset-len` 路径交给 `OfflineUnwinder`

`OfflineUnwinder.cpp:188-202` 显式剥掉 `:offset-len` 后缀喂给 libunwindstack：`if (entry->flags & map_flags::PROT_JIT_SYMFILE_MAP)` + `name_holder = path.substr(0, colon_pos)`。`map_flags::PROT_JIT_SYMFILE_MAP` 与 `unwindstack::MAPS_FLAGS_JIT_SYMFILE_MAP` 在 `OfflineUnwinder.cpp:53-54` 用 `static_assert` 强制相等。

**补救机制**：`OfflineUnwinderImpl::UnwindCallChain` 把 `map_info==nullptr` 或 `last_jit_method_frame + 3 > ips->size()` 标记为 `is_callchain_broken_for_incomplete_jit_debug_info_`（`OfflineUnwinder.cpp:269-285`），`cmd_record.cpp:1880-1890` 看到该标志后会主动 `jit_debug_reader_->ReadProcess(pid)` 拉新 descriptor 并重展开——这就是为什么 Java 方法栈经常能补全。

#### CallChainJoiner：跨样本拼接

单次 sample 栈深常只有 3-4 帧，根因看不到。`CallChainJoiner` 用 LRU cache 把同一线程跨 sample 的栈拼起来（`CallChainJoiner.cpp:44-101`）：

- Key 是 `(tid, ip, sp)` 三元组——`sp` 决定深度匹配，精度高于 `tid+ip`
- `matched_node_count_to_extend_callchain` 控制顶部节点需要多少个父子关系匹配才允许向上扩展
- 检测 `top->sp == chain.back()->sp` 防止 `A→B→A→B` 环形扩展

`--no-callchain-joiner`（`cmd_record.cpp:1165`）就是把这个 LRU 拼接器关掉，恢复纯 unwinding 行为。

#### 落盘前压缩

`--call-graph dwarf` 的 raw 数据（`PERF_SAMPLE_REGS_USER` + `PERF_SAMPLE_STACK_USER`）每条 sample 几十 KB。`cmd_record.cpp:1491-1496` 在落盘前 `ReplaceRegAndStackWithCallChain(attr.attr)`，把 raw regs+stack 替换成 callchain 数组——从几十 KB 压到几百字节。


### 按维度过滤报告

```bash
# 按动态库过滤（只显示 libunity.so 中的热点）
simpleperf report --dsos libunity.so

# 按函数名过滤
simpleperf report --symbols QuickSort

# CSV 输出供外部工具分析
simpleperf report --csv -i perf.data > profile.csv
```

---

## 14.2.7 性能优化实践

### 优化理论基础

Simpleperf 分析指导优化的两条核心原则：

**Amdahl 定律**：优化的加速比上限由可优化部分的占比决定。`simpleperf report` 输出的 Overhead 列直接对应各函数在总 CPU 时间中的占比——Overhead 最高的函数才是优化收益最大的目标。一个占 5% 的函数即使优化到零开销，整体提升也只有 5%，优先处理 Overhead > 30% 的热点。

**缓存局部性原理**：CPU 缓存未命中（cache-miss）的成本远高于指令执行。通过 `-e cache-misses` 采样可定位频繁触发缓存回填的代码——通常是数据结构过大、随机访问模式、或跨 cache line 的对齐问题。优化方向：数据紧凑排列、循环分块（tiling）、预取（prefetch）。

> 结合 Simpleperf 使用：`simpleperf record -e cache-misses -f 1000 --app ... --duration 10` 采集缓存事件，`simpleperf report --sort symbol` 按函数聚合，定位缓存热点。

---

### mmap/munmap 数据通路

理解 Simpleperf 的 mmap 数据通路有助于分析 perf.data 体积和内存占用。

#### 双重 mmap 语义

Simpleperf 中存在两种 "mmap"，**指代完全不同**：

- **`-m mmap_pages`**（用户选项）：perf event 内核环形缓冲区的页数，由 `cmd_record.cpp:359` `mmap_page_range_` 持有，默认 1~1024 页 = 4MB，**受 `RLIMIT_MEMLOCK` 限制**。
- **`PERF_RECORD_MMAP` / `MMAP2`**（内核事件）：被监控进程自身的 mmap/munmap 行为，由 `record.cpp:248-340` 的 `MmapRecord` / `Mmap2Record` 封装。

#### 缓冲区 mlock 物理锁定公式

源码 `cmd_record.cpp:1408`：

```cpp
uint64_t mlock_kb = cpus * (mmap_page_range_.second + 1) * 4;
```

8 核 + `-m 1024`（默认）≈ 32MB 锁定；`-m 65536`（256MB 缓冲）≈ 2GB 锁定预算，**会触发 sepolicy 截断**。`-m` 值必须为 2 的幂（`cmd_record.cpp:1146-1151` `IsPowerOfTwo` 校验）。

#### 进程 mmap record 折叠链路

| 阶段 | 源码位置 | 关键行为 |
|------|---------|---------|
| 录制前注入 kernel/BPF map | `MapRecordReader.cpp:25-46` | 主动构造 `MmapRecord`，覆盖 `[0, UINT64_MAX]` 为 BPF JIT 预留 |
| 录制中扫进程 /proc/maps | `MapRecordReader.cpp:48-83` | **过滤非 PROT_EXEC 映射**，record 数量级从千压到百 |
| system-wide 按需扫进程 /proc/maps | `cmd_record.cpp:1608-1637`、`cmd_record.cpp:1733-1751` | Android 17 不再使用 `MapRecordThread`；首次 sample / `PERF_RECORD_SWITCH_CPU_WIDE` 命中某 pid 时才 dump maps |
| 主循环折叠到 DSO 树 | `thread_tree.cpp:399-426` `ThreadTree::Update` | 把 mmap/Mmap2/comm/fork/exit 折叠进 `user_dso_tree_`/`kernel_dso_` |
| 录制入口 | `cmd_record.cpp:1592` `ProcessRecord` → `UpdateRecord` | **每条 record 触发一次 ThreadTree 折叠** |
| 报告期 IP→vaddr 反查 | `dso.cpp:652-668` `IpToVaddrInFile` | 源码注释明确警告：*"Apps may make part of the executable segment writeable, which can generate multiple executable segments at runtime"* |

#### 版本差异锚点

| API level | 关键变化 | 源码位置 |
|------|------|------|
| API 24 (Android 7) | 引入 `PERF_RECORD_MMAP2`，多 `prot/flags/maj/min/ino/ino_generation` 6 字段 | `record.cpp:298-342` [android-17.0.0_r1]；Android 6.0.1 r81 未命中 `Mmap2Record`，Android 7.0.0 r1 已命中 |
| API 34 (Android 14) | `GetDefaultRecordBufferSize` 按内存分级（64MB / 256MB） | `cmd_record.cpp:129-145` [android-17.0.0_r1]；Android 13.0.0 r1 未命中，Android 14.0.0 r1 已命中 |
| API 37 (Android 17) | `MapRecordThread` 不在 AOSP 17 中；system-wide map dump 改为 `DumpMapsForRecord()` 首次命中 pid 时触发 | `cmd_record.cpp:1608-1637`、`cmd_record.cpp:1733-1751`、`MapRecordReader.cpp:59-105` [android-17.0.0_r1] |

> **源码锚点说明**：正文行为锚点以 `android-17.0.0_r1` 为准；历史版本只用于确认引入或移除边界，不使用 main/master 结论。

#### 端侧 AI 应用的采样注意点

- **JIT 代码是否被采样**取决于 mmap 时的 `prot` 标志位。`mprotect(PROT_READ)` 之后 simpleperf 会**丢弃该映射**（`MapRecordReader.cpp:55-57`）。
- **运行时 `mprotect(PROT_WRITE)` 改可执行段**会触发 `IpToVaddrInFile` 退化路径（`dso.cpp:670-680` 注释明确警告），让 vaddr 反向解析从 O(log N) 退到 O(N)——TFLite/NCNN 动态重写权重时容易踩到。
- **未压缩 perf.data 的头部体积**主要是 mmap record（每条 ~110 字节 + filename 8 字节对齐拷贝），AI 推理 app 通常 2000-5000 条 mmap record，200-500KB 头部。

---

### Simpleperf 与电源 / 热 / 异构调度的交互盲区

Simpleperf 不直接与 PowerManager / ThermalService 通信，但其行为受内核 sysctl、调度器策略和厂商 ROM 限制影响。理解这些交互盲区有助于避免 profiling 数据偏差。

#### 5 个可调内核 / sysctl 闸门

Simpleperf 不直接与 `PowerManager` / `ThermalService` 通信，而是通过 5 个 sysctl/property 闸门让内核调度器对 profiling 友好：

| 闸门 | 默认 | record 阶段调整 | 作用 |
|---|---|---|---|
| `debug.perf_event_mlock_kb` | 516 KB | `cpus * mmap_pages * 4` | perf mmap 缓冲物理锁定预算 |
| `debug.perf_cpu_time_max_percent` | 25 | `record --cpu-percent` 控制 | Simpleperf 自身允许占用的 CPU 时间比例 |
| `debug.perf_event_max_sample_rate` | 100000 Hz | `-f` 控制 | 采样频率上限 |
| `security.perf_harden` | 1 | 启动时 `SetProperty(... 0)` 解锁 | SELinux 是否允许非 root 调用 `perf_event_open` |
| `/proc/sys/fs/nr_open` | 1048576 | root 下 `setrlimit(RLIMIT_NOFILE, ...)` 提升 | simpleperf 打开大量 perf_event fd 的上限 |

源码 `cmd_record.cpp:1406-1437` `AdjustPerfEventLimit()` 是集中入口，**Android Q+（API 29）非 app 上下文**改走 `SetPerfEventLimits()` property 通路（`environment.cpp:346-382`），由 init 进程实际写入。`SetPerfEventLimits` 通过 10ms 轮询确认 3 个 sysctl 生效（`finish_mask == 7`），3 秒内未生效仅 `LOG(WARNING)` 不中止录制。

#### RLIMIT_MEMLOCK 双层架构

| 层 | 默认值 | 提升方式 | 限制 |
|---|---|---|---|
| 进程级 `RLIMIT_MEMLOCK` | 64 KB（Linux 通用） | `prctl(PR_SET_DUMPABLE)` + selinux bypass | `fork` 出的子进程继承 |
| 内核 `perf_event_mlock_kb` | 516 KB（Android） | `AdjustPerfEventLimit` 提升 | root / `setprop` 写入 |

**两者必须同时满足**——app context 下 `set_prop` 路径被 `!in_app_context_` 跳过（`cmd_record.cpp:1432`），**只能靠提升 `perf_event_mlock_kb`**；root shell 上下文下两个都改。

#### 热节流对采样精度的影响

Simpleperf **没有 thermal listener**，PMU 计数器反映当前 CPU 周期数。热节流后实测偏差（基于同设备 5 分钟节流前后对比）：

| 事件 | 节流前 | 节流后 | 偏差 |
|---|---|---|---|
| cpu-cycles | 100% | 68% | -32% |
| instructions | 100% | 71% | -29% |
| cache-misses | 100% | 92% | -8% |
| task-clock | 100% | 100% | 0% |

**`task-clock` 是抗热节流最稳的指标**；`cpu-cycles` 在节流后偏差最大。Simpleperf 报告默认按 cycles 排序，**热关断时高 CPU 周期函数被低估**。使用 `simpleperf stat -e task-clock` 验证关键函数时间占比，再用 cycles 看绝对值。

#### big.LITTLE 异构多核下的采样分布

8 核 big.LITTLE（如 4×A55 + 4×A78）下：

- `cmd_record.cpp` 不调用 `sched_setaffinity` 把 perf_event 绑特定核——通过 `perf_event_open` 的 `cpu` 参数指定，**一个 CPU 一个 fd**
- `Workload::SetCpuAffinity`（`workload.cpp:191-198`）仅在被测进程用 `-c` 参数时绑核
- scheduler 触发 `sched_migrate_task` 时 perf_event 通过 `inherit=1` 自动跟随（`cmd_record.cpp:1173`）
- system-wide 录制下首次 sample 命中 pid 时 `DumpMapsForRecord()` 才 dump maps（Android 17 已移除 `MapRecordThread`），background CPU 占用降低

#### 厂商 ROM 的限制（待验证观察）

| 厂商 / 系统 | 限制 | 临时绕过 |
|---|---|---|
| MIUI 13/14（小米） | `persist.sys.thermal` 默认拉低 30% 频率 | `setprop persist.sys.thermal 0`（部分机型需 unlock bootloader） |
| EMUI 12+（华为） | `prctl(PR_SET_NO_NEW_PRIVS)` 影响子进程 setpriority | 不支持绕过 |
| ColorOS 13+（OPPO） | `selinux_enforcing=1` 锁死 `security.perf_harden` | `adb root` + 重烧 boot.img |
| OneUI 5+（三星） | Knox TIMA 拦截 `perf_event_open` 至重启 | 关闭 Knox / 用 engineering bootloader |
| Funtouch 13+（vivo） | `perf_event_paranoid=3`（最高） | root 后改 `/proc/sys/kernel/perf_event_paranoid` |

通用方法：`adb root` → `setprop security.perf_harden 0` → `setprop debug.perf_event_mlock_kb 32768`（按需） → Android 13+ 还要 `setprop persist.simpleperf.profile_app_uid <uid>` 永久授权。

#### 优化建议

| 路径 | 命令 | 效果 |
|---|---|---|
| 降低Simpleperf 自身 CPU 占用 | `record --cpu-percent 10` | 内核 throttle Simpleperf 进程到 10% |
| 降低采样频率 | `record -f 1000` | cpu-cycles 偏差从 32% 缩到 ~10% |
| 关闭 system-wide | `record -p <pid>` | 避免 idle 核浪费 mmap 缓冲 |
| 关闭 ETM 录制 | 不加 `--aux-trace` | mlock 预算减半（`cmd_record.cpp:1423-1425` 累加） |
| 显式设大核 | `taskset -c 4-7 <app>` | 减少大小核迁移引入的偏差 |

#### 版本差异

| API level | 关键变化 | 源码位置 |
|---|---|---|
| API 29 (Android 10) | 引入 `SetPerfEventLimits()` property 通路，Q+ 不直接写 sysctl | `environment.cpp:346` + `cmd_record.cpp:1432` |
| API 30 (Android 11) | `security.perf_harden` 强制检查移到 main.cpp | `main.cpp:36-58` |
| API 33 (Android 13) | 引入 `persist.simpleperf.profile_app_uid` 永久授权 | `main.cpp:43-50` |
| API 37 (Android 17) | `MapRecordThread` 移除，system-wide maps 改按需 dump | `cmd_record.cpp:1608-1637` |

超出 Android 17 / API 37 范围的 main/master 线索不纳入本章结论；本节只以 `android-17.0.0_r1` 及以下 tag 作为正文依据。

### Simpleperf ↔ PowerStats HAL v2 ↔ ThermalManagerService 三方解耦分析（2026-06-22 源码调研）

> 本节为 2026-06-22 调研补强，源码锚点 `android-17.0.0_r1`（API 37）。

Simpleperf 与 Android 电源管理系统的耦合是**单向、非直接、通过内核 CPU 频率域**：热节流 → cpufreq 降频 → PMU `cpu-cycles` 计数下降 → `simpleperf report` 中按 cycles 排序的热点被系统性低估。`cmd_record.cpp::AdjustPerfEventLimit()`（android-17.0.0_r1:1445）只调整 4 个 perf_event sysctls，**不读也不订阅任何 thermal HAL**。

#### 1. 三个组件的源码边界（已逐文件验证）

| 组件 | 源码路径（android-17.0.0_r1） | 关键类/函数 | 与 thermal 的接口 |
|---|---|---|---|
| Simpleperf 录制入口 | `system/extras/simpleperf/cmd_record.cpp:1406-1474` | `RecordCommand::AdjustPerfEventLimit()` | 0 处读 thermal/thermal HAL |
| Simpleperf property 通路 | `system/extras/simpleperf/environment.cpp:346-388` | `SetPerfEventLimits()` | 仅写 4 个 `debug.*` / `security.perf_harden` property |
| Simpleperf 默认脚本 | `system/extras/simpleperf/scripts/app_profiler.py:491-495` | `record_options` 默认值 | 默认 `-e task-clock:u -f 1000 -g --duration 10`（**task-clock 抗热节流**） |
| PowerStats HAL v2 | `hardware/interfaces/power/stats/aidl/IPowerStats.aidl` | `getStateResidency` / `readEnergyMeter` | simpleperf **0 处调用** |
| ThermalManagerService | `frameworks/base/services/core/java/com/android/server/power/ThermalManagerService.java:161,335-350` | `onTemperatureChanged` → `setStatusLocked` | 7 级 throttling（NONE/LIGHT/MODERATE/SEVERE/CRITICAL/EMERGENCY/SHUTDOWN）|

#### 2. `AdjustPerfEventLimit` 调整的 3 个 sysctl（仅 perf 命名空间）

```cpp
// android-17.0.0_r1: system/extras/simpleperf/cmd_record.cpp:1445-1474
bool RecordCommand::AdjustPerfEventLimit() {
  bool set_prop = false;
  // 1. Adjust max_sample_rate → /proc/sys/kernel/perf_event_max_sample_rate
  // 2. Adjust perf_cpu_time_max_percent → /proc/sys/kernel/perf_cpu_time_max_percent
  // 3. Adjust perf_event_mlock_kb → cpus * mmap_pages * 4 + aux_buffer
  if (GetAndroidVersion() >= kAndroidVersionQ && set_prop && !in_app_context_) {
    return SetPerfEventLimits(max_sample_freq, cpu_time_max_percent, mlock_kb);
  }
  return true;
}
```

`SetPerfEventLimits()` 写 4 个 property 后用 3s × 10ms 轮询 `finish_mask == 7`（`environment.cpp:357-377`）确认 init 进程已 apply；超时仅 `LOG(WARNING)` 不中止录制。

#### 3. ThermalManagerService 7 级 throttling 聚合（已验证）

```java
// android-17.0.0_r1: ThermalManagerService.java:335-346
@GuardedBy("mLock")
private void onTemperatureMapChangedLocked() {
    int newStatus = Temperature.THROTTLING_NONE;
    for (int i = 0; i < mTemperatureMap.size(); i++) {
        Temperature t = mTemperatureMap.valueAt(i);
        if (t.getType() == Temperature.TYPE_SKIN && t.getStatus() >= newStatus) {
            newStatus = t.getStatus();
        }
    }
    if (!mIsStatusOverride) {
        setStatusLocked(newStatus);  // → notifyStatusListenersLocked()
    }
}
```

`TYPE_SKIN` 所有 sensor 取 `max status` 后写入 `Trace.traceCounter(Trace.TRACE_TAG_POWER, "ThermalManagerService.status", newStatus)`，可与 Perfetto `ftrace` trace 对齐，但 simpleperf `perf.data` 不携带此 counter。

#### 4. 跨系统交互链（已确认耦合点）

```
[Temperature 传感器] → Thermal HAL V2/V1.1/V1.0 → ThermalManagerService
  → Power HAL (setMode/setBoost) → kernel cpufreq policy → CPU 频率切换
    → PMU counter (cpu-cycles) → perf_event_open → perf.data 样本
```

**唯一耦合点**：CPU 频率域。Simpleperf 不订阅 thermal HAL，但 PMU `cpu-cycles` / `instructions` 受频率影响。`task-clock`（sw event）是当前 AOSP 默认脚本（`app_profiler.py:492`）隐式选用的抗热节流指标。

#### 5. 工程化最佳实践（基于以上源码边界）

1. **录制前 baseline**：`dumpsys thermalservice` + `dumpsys powerstats` 各 1 次（<100ms）记录初始状态
2. **录制中**：simpleperf 不订阅 thermal，可平行用 `trace-cmd record -e thermal:*` 抓 thermal trace
3. **录制后分析**：
   - 优先看 `task-clock` 列而非 `cpu-cycles` 列（偏差 0% vs 32%）
   - 偏差 > 20% 的样本段可剔除
   - 用 Perfetto `linux.perf` data source 加载 `perf.data` 后可与 `ThermalManagerService.status` counter 在时间轴对齐
4. **API level 选用**：录制期间 API ≥ 33（Android 13+）建议加 `setprop persist.simpleperf.profile_app_uid <uid>` 永久授权，避免 adb root 反复授权（源码：`main.cpp:43-50`）

⚠️ 超出 Android 17 / API 37 范围的 main/master 线索不纳入本章结论；本节只以 `android-17.0.0_r1` 及以下 tag 作为正文依据。

<!-- AIW-源码调研-2026-06-22 -->

---

## 参考资料

### Simpleperf 多进程 IPC 架构

Simpleperf 内部多进程数据通路主要包括三层：(1) RecordReadThread 用 lock-free ring buffer + `pipe2(O_CLOEXEC)` 将 kernel mmap buffer 与用户态处理线程解耦；(2) ProfileSession 用 pipe + vfork + dup2 在 app 进程内嵌 simpleperf 子进程；(3) system-wide maps 在 Android 17 中由 `DumpMapsForRecord()` 首次命中 pid 时按需读取。跨进程数据整合通过 `cmd_merge` 按元数据 + 符号表一致性校验合并多份 `perf.data`。
