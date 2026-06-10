---


title: Simpleperf
chapter: '14.2'
section: '14.2'
status: ready-for-review
reviewed_date: '2026-06-10'
reviewed_by: openclaw-task6
drafted_date: '2026-04-03'
drafted_by: openclaw-task2a
applicable_versions: Android 5.0 (API 21) - Android 16 (API 36)
last_verified: '2026-04-22'
last_verified_against: NDK r29 simpleperf docs + Perfetto external format docs + Android profileable docs
confidence: needs-review
sources:
  - type: official
    path: android.googlesource.com/platform/system/extras/+/master/simpleperf/doc/README.md
  - type: official
    path: developer.android.com/ndk/guides/simpleperf
  - type: official
    path: developer.android.com/guide/topics/profiling/perfetto
tags:
  - simpleperf
  - cpu-profiling
  - performance-analysis
  - ndk
  - native-profiling
last_task9_audit: '2026-06-10T04:21:00+08:00'
last_task2b_at: '2026-06-10T04:50:00+08:00'
last_task2b_lite_at: '2026-06-10'
task9_result: needs-rework
task6_result: pass-light-edit
task2b_result: fixed-lite
task2b_state: fixed
task6_state: reviewed
task9_state: pending
pipeline_stage: task6_pending
last_task9_at: '2026-06-10T07:20:00+08:00'
last_task9_reviewed_at: '2026-06-10T07:20:00+08:00'
---


# Chapter 14.2 - Simpleperf

## 14.2.1 简介与用途

Simpleperf 是 Android 系统自带的高性能分析工具，专为开发者设计。它能够深入分析应用程序在 Android 设备上的运行性能，包括 CPU 使用率、内存占用、函数调用栈等关键指标。

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

- **零依赖**：无需额外安装，Android 系统自带
- **低开销**：性能分析本身对应用性能影响最小
- **系统级集成**：与 Android 调试体系无缝结合
- **多格式支持**：支持 Perfetto、Android Profileable 等现代格式
- **官方支持**：由 Google 官方维护，与 Android 版本同步更新

---

## 14.2.2 安装与配置

### 设备要求

Simpleperf 需要满足以下设备要求：

- **Android 版本**：Android 5.0 (API 21) 及以上
- **root 权限**：需要 root 权限才能进行完整的系统级跟踪
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

# 验证设备是否支持 simpleperf
adb shell simpleperf --version
```

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
# 启动应用并记录 CPU 使用
simpleperf record com.example.app

# 指定时间限制
simpleperf record -f 5 --trace-fg com.example.app

# 生成报告
simpleperf report
```

#### 函数级别分析

```bash
# 记录函数调用
simpleperf record -g --trace-fg com.example.app

# 只记录特定函数
simpleperf record -g --trace-fg com.example.app -- android.app.Activity.onCreate

# 生成调用图
simpleperf report --show-call-graph
```

---

## 14.2.4 高级功能与选项

### 采样选项

```bash
# 设置采样频率
simpleperf record -f 1000 --trace-fg com.example.app

# 使用硬件事件采样
simpleperf record -e cpu-cycles,instructions --trace-fg com.example.app

# 自定义事件
simpleperf record -e cache-misses,cache-references --trace-fg com.example.app
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
# 输出到文件
simpleperf record -o output.data --trace-fg com.example.app

# 指定格式
simpleperf record -o output.perfetto --trace-fg com.example.app

# 实时输出
simpleperf record --trace-fg com.example.app -f 1000
```

---

## 14.2.5 数据收集方法

### Perfetto 数据收集

Simpleperf 支持输出 Perfetto 格式，这是 Android 10+ 推荐的现代性能分析格式。相比旧版 `perf.data`：
- **统一分析面**：Perfetto 将 CPU profiling、atrace、ftrace、heap profiles、power rails 合并到同一时间轴，消除了跨工具拼图的碎片化问题。
- **在线可视化**：`perfetto.trace` 文件可直接拖入 <https://ui.perfetto.dev>，无需本地安装工具。
- **低开销 SQL 查询**：通过 `trace_processor` 用标准 SQL 做跨维度聚合，替代手工 grep 脚本。
- **与系统 trace 无缝合并**：`simpleperf record --perfetto` 产出的 trace 可与 `perfetto` 系统 tracing 共用同一个 session。

```bash
# 使用 Perfetto 格式
simpleperf record --trace-fg com.example.app --perfetto

# 指定 Perfetto 配置
simpleperf record --trace-fg com.example.app --perfetto --config perfetto_config.xml

# 导出到 Perfetto UI
simpleperf record --trace-fg com.example.app --out perfetto.traces
```

### Android Profileable 数据收集

```bash
# 启用应用的可分析性
adb shell pm grant com.example.app android.permission.SET_DEBUG_APP
adb shell am profile start com.example.app

# 使用 simpleperf 收集数据
simpleperf record --trace-fg com.example.app --android-profileable
```

### 系统级跟踪

```bash
# 全系统跟踪
simpleperf record --system-wide --trace-fg com.example.app

# 指定跟踪时间
simpleperf record --system-wide -f 100 --duration 30 --trace-fg com.example.app

# 混合跟踪
simpleperf record --system-wide --pid 1234 --duration 60
```

---

## 14.2.6 数据分析与解读

### CPU 分析报告

```bash
# 基本 CPU 报告
simpleperf report

# 按函数排序
simpleperf report --sort comm,dso,symbol

# 按热函数显示
simpleperf report --show-total-period

# 显示调用栈
simpleperf report --show-call-graph
```

### 内存分析

```bash
# 内存分配跟踪
simpleperf record -e alloc_count,alloc_size --trace-fg com.example.app

# 内存泄漏检测
simpleperf record -e malloc_count,malloc_size --trace-fg com.example.app

# 报告分析
simpleperf report --show-alloc-stats
```

### 多维度分析

```bash
# 组合分析
simpleperf report --show-branch-miss --show-cache-miss

# 时间线分析
simpleperf report --show-timeline

# 热点分析
simpleperf report --top 10
```

---

## 14.2.7 性能优化实践

> **⚠️ [Task2B 回炉中]** 此节内容根据 Task 6 第二轮 review 意见进行重写。
> 旧版内容为通用 Java 优化模式（对象池、WeakReference、线程池），与 Simpleperf 分析流程脱节，
> 且代码示例中的 Stream API（`numbers.stream()...`）要求 API 24+，与声明的 API 21 下限矛盾。
> 目标重写：simpleperf report 发现热点 → 调用栈解读 → 定位优化方向 → 优化后再用 simpleperf 验证的完整流程。

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

# 增加缓冲区
simpleperf record -b 4096 --trace-fg com.example.app

# 使用压缩输出
simpleperf record -z --trace-fg com.example.app
```

#### 跟踪中断

```bash
# 监控跟踪状态
simpleperf stat --duration 10

# 使用自动保存
simpleperf record -a --trace-fg com.example.app
```

### 性能问题

#### 过度跟踪导致性能下降

```bash
# 降低采样频率
simpleperf record -f 100 --trace-fg com.example.app

# 选择性跟踪
simpleperf record -g --trace-fg com.example.app --com.example.app.MainActivity
```

---

## 14.2.9 性能案例分析

> **⚠️ [Task2B 回炉中]** 此节内容根据 Task 6 第二轮 review 意见进行重写。
> 旧版案例（LazyInitializer 延迟加载、SafeHandler 内存泄漏）为通用 Android 知识，
> 缺少 Simpleperf 特有信息：无 report 输出、无调用栈解读、无 `--show-call-graph` 结果。
> 目标重写：`simpleperf record → report` 完整输出 → 调用栈解读 → 优化 → 验证的全流程案例。

---

## 14.2.10 工具集成与自动化

Simpleperf 通过标准 `adb` 接口与 CI/CD 管道集成，无需额外 Gradle 插件：

```bash
# CI 脚本中直接调用 simpleperf（命令行工具，不依赖 Gradle 插件）
adb shell simpleperf record --trace-fg com.example.app --duration 60 -o /data/local/tmp/perf.data
adb pull /data/local/tmp/perf.data
simpleperf report --csv perf.data > perf_report.csv
```

> **注意**：`id 'simpleperf-plugin'` 并非官方 Gradle 插件，Android 官方文档未记录此插件。
> Simpleperf 是命令行工具，直接在 shell 中调用即可。

---

## 14.2.11 性能基准测试

> **⚠️ [Task2B 回炉中]** 旧版基准数据（`io_read`/`io_write`/`net_bytes_sent`/`net_bytes_recv` 事件名
> 及 benchmark 数值）无法通过 Simpleperf 官方文档验证，已移除。
> 目标重写为基于 `simpleperf stat` 实测的基准流程。

---

## 14.2.12 总结与最佳实践

> **⚠️ [Task2B 回炉中]** 旧版总结为通用建议 + 流程图，未紧扣 Simpleperf 特有能力。
> 重写方向：以 "如何用 Simpleperf 建立日常性能监控节奏" 为主线，
> 落实到 `record → report → 定位热点 → 验证` 的具体步骤。

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
- 摘要：Simpleperf在2026年main分支呈现「内核↔用户态ABI对齐+模块化命令管道+多架构同构」三大特征：三段式权限模型（<11/11+/13+）、自适应ring buffer（64MB/256MB按内存分级）、ARM CoreSight ETM指令追踪集成、跨平台同构编译（device native与host offline分析分离）。
- 注入时间：2026-06-10
- 价值：包含源码级分析（AOSP锚点），对理解框架内部机制和性能调优有直接参考意义
- ⚠️ 来源基于 main/master 分支快照，部分内容可能未进入 Android 17 正式分支，仅供参考不作为正文结论
