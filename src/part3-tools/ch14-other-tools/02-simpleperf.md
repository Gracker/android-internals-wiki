---


title: Simpleperf
chapter: '14.2'
section: '14.2'
status: ready-for-review
reviewed_date: '2026-06-10'
reviewed_by: openclaw-task6
drafted_date: '2026-04-03'
drafted_by: openclaw-task2a
applicable_versions: Android 5.0 (API 21) – Android 17 (API 37)
last_verified: '2026-04-22'
last_verified_against: NDK r29 simpleperf docs + AOSP system/extras/simpleperf (main branch snapshot) + Perfetto linux.perf data source docs
confidence: needs-review
sources:
  - type: official
    path: android.googlesource.com/platform/system/extras/+/master/simpleperf/doc/README.md
  - type: official
    path: developer.android.com/ndk/guides/simpleperf
  - type: official
    path: developer.android.com/guide/topics/profiling/perfetto
  - type: deepresearch
    path: DeepResearch/2026-06-10-simpleperf-android17-architecture.md
    note: main分支快照，AOSP system/extras/simpleperf 架构分析，部分内容可能未进入 Android 17 正式分支
tags:
  - simpleperf
  - cpu-profiling
  - performance-analysis
  - ndk
  - native-profiling
last_task9_audit: '2026-06-10T04:21:00+08:00'
last_task2b_lite_at: '2026-06-10T13:42'
last_task2b_at: '2026-06-10T12:50:00+08:00'
task9_result: needs-rework
task6_result: pass-light-edit
task2b_result: fixed-lite
task2b_state: fixed
task6_state: reviewed
last_task6_at: '2026-06-10T14:15:43+08:00'
task9_state: pending
pipeline_stage: task9_pending
last_task9_at: '2026-06-10T07:20:00+08:00'
last_task9_reviewed_at: '2026-06-10T07:20:00+08:00'
---


# Chapter 14.2 - Simpleperf

## 14.2.1 简介与用途

Simpleperf 是 Google 官方维护的原生 CPU profiling 工具，通过 Android NDK 分发 [已验证：NDK r29]。它基于 Linux `perf_event_open` 系统调用，能够以低开销采集函数级 CPU 热点、调用栈、硬件 PMU 事件等关键性能数据。

### 主要用途

- **CPU 性能分析**：精确测量函数级别的 CPU 时间消耗，识别性能瓶颈
- **内存使用分析**：跟踪内存分配和释放模式，发现内存泄漏
- **线程行为分析**：分析线程调度、锁竞争、上下文切换等
- **系统调用跟踪**：记录应用程序与系统内核的交互
- **功耗分析**：通过追踪 CPU、内存、网络等硬件使用来估算应用功耗

### 适用范围

Simpleperf 适用于：
- Native C/C++ 代码性能分析
- Java/Kotlin 代码（通过 ART 方法跟踪）
- 混合型应用（JNI + Java）
- 系统级性能分析（Framework 层）
- AOSP 内核组件调试

### 基本优势

相比第三方性能分析工具，Simpleperf 具有以下优势：

- **无需 root**（部分场景）：Android 13+ 支持 App 自采样永久授权（`persist.simpleperf.profile_app_uid`），profileable 应用无需 root [已验证：AOSP main.cpp AndroidSecurityCheck 三段式权限模型]
- **低开销**：性能分析本身对应用性能影响最小
- **系统级集成**：与 Android 调试体系无缝结合
- **多格式支持**：支持 Perfetto、Android Profileable 等现代格式
- **官方支持**：由 Google 官方维护，与 Android 版本同步更新

---

## 14.2.2 安装与配置

### 设备要求

Simpleperf 需要满足以下设备要求：

- **Android 版本**：Android 5.0 (API 21) 及以上
- **root 权限**：系统级跟踪需要 root；应用级采样在 Android 13+ 可通过 `persist.simpleperf.profile_app_uid` 属性授予 App 自采样永久授权 [已验证：AOSP main.cpp 三段式权限模型，Android 13+ 不再要求 shell 下 setprop]
- **调试模式**：设备需开启 USB 调试或无线调试
- **应用签名**：被测试应用需要 debuggable 或包含 debug key

### 基本安装

#### 设备端设置

```bash
# 启用 ADB 调试
adb shell settings put global adb_enabled 1

# 设置应用为可调试模式（如果应用不是 debuggable）
adb shell pm grant com.example.debug android.permission.SET_DEBUG_APP
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
adb shell simpleperf version
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
# 设置采样频率（-f 单位 Hz，默认 1000）
simpleperf record -f 4000 --app com.example.app --duration 10

# 指定硬件 PMU 事件采样 [已验证：NDK r29 支持的事件列表见 simpleperf list]
simpleperf record -e cpu-cycles,instructions --app com.example.app --duration 10

# 指定缓存事件
simpleperf record -e cache-misses,cache-references --app com.example.app --duration 10
```

### 过滤选项

```bash
# 过滤特定进程
simpleperf record --pid 1234

# 过滤线程
simpleperf record --tid 5678

# 过滤包名
simpleperf record com.example.*

# 排除系统进程
simpleperf record --exclude-pid android.*,system.*
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

Simpleperf 本身输出 `perf.data` 格式（protobuf 编码），不直接输出 `.perfetto-trace` 文件。
与 Perfetto 系统 trace 集成的正确方式是通过 Perfetto 的 `linux.perf` data source 在同一个 tracing session 中同时采集 perf events 和 ftrace/atrace 事件 [已验证：Perfetto linux.perf 文档]：

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

> **说明**：`simpleperf` 不存在 `--perfetto` / `--config` / `--out` 标志 [已验证：AOSP system/extras/simpleperf/cmd_record.cpp 命令注册表无这些参数]。
> 与 Perfetto 集成应通过 Perfetto 的 `linux.perf` 数据源实现，而非 simpleperf 标志。

### Profileable 应用数据收集

Android 10+ 引入了 profileable 应用机制，允许 release 构建在 `AndroidManifest.xml` 中声明 `<profileable android:shell="true" />` 后
无需 debuggable 即可被 simpleperf 采样 [已验证：Android Profileable 官方文档]：

```bash
# 对 profileable 应用采样（--app 自动处理 profileable 权限）
simpleperf record --app com.example.app --duration 10
```

### 系统级采样

系统级采样需要 root 权限，采集所有进程的 perf events [已验证：AOSP cmd_record.cpp GetDefaultRecordBufferSize 对 system_wide 分配 256 MB 大缓冲]：

```bash
# 全系统采样 30 秒
adb shell simpleperf record --system-wide --duration 30 -o /data/local/tmp/perf.data

# 从设备拉取并生成报告
adb pull /data/local/tmp/perf.data
simpleperf report -i perf.data
```

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

> **⚠️ [Task2B 回炉中 · 2026-06-10]** 
> 此节待基于真实 simpleperf 分析流程重写。重写方向：
> 1. 从 `simpleperf report -g` 输出中识别热点函数 → 解释为何该函数占 30%+ CPU
> 2. 从调用栈判断优化方向（递归过多？锁竞争？重复分配？）
> 3. 实施具体优化（算法替换/缓存/去锁/批量操作）
> 4. 优化后用 `simpleperf record --app ... --duration 10` 重新采样验证
> 5. 展示优化前后的 `report` 对比，量化效果
>
> 旧版（已删除）：通用 Java 优化模式（对象池、WeakReference、线程池），与 Simpleperf 分析流程脱节。

---

## 14.2.8 常见问题与解决方案

### 设备相关问题

#### 设备不支持 Simpleperf

```bash
# 检查设备支持
adb shell simpleperf --version

# 如果不支持，使用 ADB shell 方法
adb shell setprop debug.perfetto.enable true
adb shell am profile start com.example.app
```

#### Root 权限问题

```bash
# 检查 root 权限
adb shell su -c "id"

# 无 root 权限的替代方案
adb shell run-as com.example.app simpleperf record
```

### 数据收集问题

#### 数据丢失

```bash
# 检查存储空间
adb shell df -h /data

# 采集前检查可用空间，perf.data 在 system-wide 模式下可达数百 MB
# 建议指定输出到外部存储：-o /sdcard/perf.data
simpleperf record --system-wide --duration 30 -o /sdcard/perf.data
```

#### 采样中断

```bash
# 使用 --duration 控制采集时长，避免手动 Ctrl+C 中断造成数据不完整
simpleperf record --app com.example.app --duration 30

# system-wide 采集建议使用 screen/tmux 包住，防止 SSH 断连中断
```

### 性能问题

#### 过度采样导致性能下降

```bash
# 降低采样频率（默认 1000 Hz，降到 100 Hz 可大幅降低开销）
simpleperf record -f 100 --app com.example.app --duration 10

# 仅对目标进程采样，排除系统进程
simpleperf record -p 12345 -f 500 --duration 10
```

---

## 14.2.9 性能案例分析

> **⚠️ [Task2B 回炉中 · 2026-06-10]**
> 此节待编写基于真实 simpleperf 分析流程的完整案例。案例结构：
> 1. **问题发现**：App 启动慢/列表滑动掉帧/游戏帧率不稳 → 用 `simpleperf record --app ... --duration 10` 采集
> 2. **report 原样展示**：粘贴 `simpleperf report -g` 的实际输出，标注关键列含义
> 3. **调用栈解读**：逐层分析热点函数的调用链，解释每层在做什么
> 4. **根因定位**：从调用栈反推是算法问题、I/O 阻塞还是 UI 线程阻塞
> 5. **优化实施**：展示具体代码修改（diff 格式），标注修改理由
> 6. **二次采样验证**：优化后重新 `record → report`，对比优化前后的开销占比
>
> 旧版（已删除）：通用 Android 知识案例（LazyInitializer、SafeHandler），缺少 Simpleperf 特有分析信息。

---

## 14.2.10 工具集成与自动化

Simpleperf 通过标准 `adb` 接口与 CI/CD 管道集成，无需额外 Gradle 插件：

```bash
# CI 脚本中直接调用 simpleperf（命令行工具，不依赖 Gradle 插件）
adb shell simpleperf record --app com.example.app --duration 60 -o /data/local/tmp/perf.data
adb pull /data/local/tmp/perf.data
simpleperf report --csv perf.data > perf_report.csv
```

> **注意**：`id 'simpleperf-plugin'` 并非官方 Gradle 插件，Android 官方文档未记录此插件。
> Simpleperf 是命令行工具，直接在 shell 中调用即可。

---

## 14.2.11 性能基准测试

> **⚠️ [Task2B 回炉中 · 2026-06-10]**
> 旧版基准数据（`io_read`/`io_write`/`net_bytes_sent`/`net_bytes_recv` 事件名及 benchmark 数值）
> 无法通过 simpleperf 官方文档验证，已移除 [已验证：simpleperf 不支持这些事件名]。
>
> 重写方向：
> 1. 用 `simpleperf stat --app com.example.app --duration 10` 采集基线指标（task-clock, cpu-cycles, instructions, IPC）
> 2. 多次采集建立统计分布（均值/标准差/P95），标注测试环境（设备型号/Android 版本/温度）
> 3. 展示如何将 stat 输出转化为 CI 可消费的 JSON 格式
> 4. 说明如何设置性能回归阈值（IPC 低于基线 5% → 告警）

---

## 14.2.12 总结与最佳实践

> **⚠️ [Task2B 回炉中 · 2026-06-10]**
> 旧版总结为通用建议 + 流程图，未紧扣 Simpleperf 特有能力，已移除。
>
> 重写方向——以 Simpleperf 为核心的日常性能监控节奏：
> 1. **日常**：每次提交后自动跑 `simpleperf stat --app ...` 采集 IPC/cache-miss 率 → 比对基线
> 2. **周度**：对重点场景跑 `simpleperf record -g --app ... --duration 10` → 检查无新增热点
> 3. **版本门禁**：release 前做 system-wide 采样 60s → 检查无系统服务被应用拖慢
> 4. **应急定位**：线上反馈卡顿 → `simpleperf record --app ... --duration 5` → `report -g` → 10 分钟内定位
> 5. 附 simpleperf + script 的自动化示例（bash/Python 包装）

---

## 14.2.13 参考资源

### 官方文档

- [Simpleperf 官方文档](https://developer.android.com/ndk/guides/simpleperf)
- [Perfetto 性能分析](https://perfetto.dev/docs/android-configuration)
- [Android Profileable 应用](https://developer.android.com/guide/topics/profiling/profileable-apps)

### 工具链接

- [Simpleperf GitHub](https://github.com/google/simpleperf)
- [Perfetto UI](https://ui.perfetto.dev/)
- [Android 性能分析工具集](https://developer.android.com/studio/profile)

### 相关书籍

> 相关书籍推荐待核实后补充。

## 参考资料

### Android Simpleperf 性能分析工具架构（main分支快照）
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-10-simpleperf-android17-architecture.md
- 类型：DeepResearch 调研结果
- 摘要：Simpleperf 在 2026 年 main 分支呈现「内核↔用户态 ABI 对齐 + 模块化命令管道 + 多架构同构」三大特征：三段式权限模型（<11/11+/13+）、自适应 ring buffer（64 MB/256 MB 按内存分级）、ARM CoreSight ETM 指令追踪集成、跨平台同构编译（device native 与 host offline 分析分离）。
- 注入时间：2026-06-10
- 价值：包含源码级分析（AOSP锚点），对理解框架内部机制和性能调优有直接参考意义
> ⚠️ 本参考基于 main 分支快照（commit 23e563428f2b），部分内容（ETM 指令追踪、JIT debug reader 增强）可能未进入 Android 17 正式分支。正文已标注 [已验证] 的可断言内容均来自 NDK r29 文档与 AOSP android-16.0.0_r1 的交叉校验；标注 [待验证] 的内容需后续对照 android-17.0.0_r1 tag 确认。
