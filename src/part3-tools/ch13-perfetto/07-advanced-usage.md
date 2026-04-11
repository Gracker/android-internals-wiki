---
title: "Perfetto 的高级用法"
chapter: "13.7"
status: ready-for-review
drafted_date: "2026-04-03"
applicable_versions: "Android 8.0 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-03"
last_verified_against: "perfetto.dev/docs/analysis"
confidence: medium
sources:
  - type: official
    path: "https://perfetto.dev/docs/analysis/sql-tables"
  - type: official
    path: "https://perfetto.dev/docs/analysis/trace-processor"
  - type: official
    path: "https://perfetto.dev/docs/visualization/macros"
  - type: official
    path: "https://perfetto.dev/docs/instrumentation/tracing-sdk"
  - type: blog
    path: "https://mp.weixin.qq.com/s/v6fGXbEZcTfxhfaKcMNhEQ"
  - type: official
    path: "https://perfetto.dev/docs/analysis/trace-summarization"
tags:
  - android
  - perfetto
  - research
pipeline_stage: task6_pending
task6_state: pending
task9_state: pending
task2b_state: idle
---


# Perfetto 的高级用法

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 自定义 Perfetto Metric：编写 SQL + proto 定义输出指标
- 🔹 Perfetto 宏（Macros）与仪表板
- 🔹 Trace Processor Python API 的高级用法
- 🔹 将 Perfetto 集成到 CI/CD 的自动化性能测试中
- 🔹 custom trace point 的最佳实践（atrace_begin / TRACE_EVENT）

### 扩展（可选深入）

- 🔸 Perfetto SDK 在 Native 层的使用
- 🔸 构建团队级 Perfetto 分析知识库

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

前面六章我们讲了 Perfetto 是什么、怎么抓 Trace、怎么看 Trace、怎么打开超大 Trace、几个专题怎么分析、线程 CPU 状态怎么看。掌握了这些，你已经能应对大部分日常性能分析场景了。

但 Perfetto 的能力远不止"打开网页看 Trace"。这一章，我们来看 Perfetto 的进阶能力：当你需要把分析从"人眼对着 Trace 看"升级到"机器自动化分析"时，你需要什么。具体来说，我们要解决五个问题：怎么用 SQL 定义自己的指标、怎么用 Python API 批量处理 Trace、怎么把分析固化成可复用的仪表板宏、怎么把 Perfetto 接入 CI/CD 做性能回归检测、以及怎么在你的代码里插入自定义的 Trace 点。

## 自定义 Perfetto Metric：用 SQL 把 Trace 变成结构化指标

### 为什么需要自定义 Metric

Perfetto 自带了 `android_cpu`、`android_mem`、`android_startup` 等内置 Metric，用 `--run-metrics` 参数就能跑。这些覆盖了最常见的需求。但当你需要回答一些特定问题时，内置的就不够用了。比如：

- "我们 App 的首页冷启动，从 `activityStart` 到第一帧上屏，平均耗时是多少？P90 是多少？"
- "RecyclerView 的每个 `onBindViewHolder` 调用耗时，有没有超过 16ms 的？"
- "相机预览的帧间隔抖动程度如何？有多少帧的 capture-to-delivery 超过了阈值？"

这些问题本质上都是对 Trace 中特定 Slice 的过滤、聚合和统计。Perfetto 提供的机制让你用 SQL 表达这些逻辑，然后把结果输出成结构化的 protobuf 消息——这就是自定义 Metric。

### Trace Processor 的核心数据模型

在写 SQL 之前，我们需要理解 Trace Processor 把 Trace 数据组织成了什么样的表。Trace Processor 是一个 C++ 库，它把各种格式的 Trace 文件解析后暴露出 SQL 接口。你在 Perfetto UI 的 Query 页面、命令行的 `trace_processor` shell、以及 Python API 中，查的都是同一套表。

核心表有这几类。**Track 类**：`track`（基表）、`thread_track`（线程级 Track）、`process_track`（进程级 Track）、`process_counter_track`（进程级计数器 Track）等。**Event 类**：`slice`（时间片，比如一次 `doFrame` 就是一个 slice）、`counter`（计数器值，比如 CPU 频率）、`sched`（CPU 调度事件）。**实体类**：`process`（进程信息）、`thread`（线程信息）。

Track 和 Event 之间的关系是通过 `track_id` 关联的。每个 slice 或 counter 都有一个 `track_id`，指向它所属的 Track。Track 又通过 `thread_track` 或 `process_track` 中的 `utid`/`upid` 关联到具体的线程或进程。

这里有个细节值得注意：Trace Processor 没有直接用 PID/TID 做标识，而是引入了 `utid`（unique tid）和 `upid`（unique pid）。原因是 Android/Linux 系统中 PID/TID 会被复用——一个进程退出后，它的 PID 可能被另一个完全不相干的进程拿走。如果直接用 PID 做 JOIN，可能会把不同进程的数据错误地关联到一起。`utid`/`upid` 是 Trace Processor 分配的单调递增 ID，保证了唯一性。

查看当前 Trace 有哪些表，可以执行：

```sql
SELECT name FROM sqlite_master WHERE type='table';
```

查看某张表有哪些字段：

```sql
SELECT * FROM pragma_table_info('slice');
```

[待高爷补充：Perfetto UI Query 页面执行 SQL 查询的截图]

### 编写自定义 Metric 的流程

自定义 Metric 由两部分组成：一个 `.sql` 文件定义查询逻辑，一个 `.proto` 文件定义输出结构。

**第一步：定义 proto 消息结构。**

假设我们要统计 App 冷启动各阶段的耗时分布，先写一个 proto 文件：

```protobuf
// cold_start_metric.proto
syntax = "proto2";
package perfetto.protos;

import "protos/perfetto/metrics/metrics.proto";

// 单次启动的阶段耗时
message ColdStartPhase {
  optional string phase_name = 1;
  optional int64 duration_ns = 2;
}

// 整个 Metric 的输出结构
message ColdStartMetric {
  repeated ColdStartPhase phases = 1;
  optional int64 total_duration_ns = 2;
}

// 扩展根消息，把自己的 Metric 挂上去
extend TraceMetrics {
  optional ColdStartMetric cold_start_metric = 500;
}
```

这里有几个要点。`extend TraceMetrics` 是把你的 Metric 注册到 Perfetto 的 Metric 体系中，字段号在 450–500 范围内用于本地开发。字段名 `cold_start_metric` 会作为 SQL 输出表的表名和最终 proto 中的字段名。

**第二步：编写 SQL 查询。**

对应的 SQL 文件用 PerfettoSQL 的 `SELECT` 和 `CREATE_FUNCTION` 等语法来组织：

```sql
-- cold_start_metric.sql
-- 查询冷启动各阶段耗时

-- 提取关键阶段的 slice
WITH startup_phases AS (
  SELECT
    s.name AS phase_name,
    s.dur AS duration_ns
  FROM slice s
  JOIN thread_track tt ON s.track_id = tt.id
  JOIN thread t ON tt.utid = t.utid
  WHERE s.name IN (
    'activityStart',
    'activityResume',
    'Choreographer#doFrame',
    'DrawFrame'
  )
  AND t.name = 'main'
  ORDER BY s.ts
)

-- 生成最终结果
SELECT
  'cold_start_metric' AS metric_name,
  SUM(duration_ns) AS total_duration_ns
FROM startup_phases;
```

实际工程中，SQL 会比这个示例复杂得多——你可能需要处理多次启动、区分冷启动和热启动、排除异常值等。但核心思路不变：用 SQL 从 Trace 的表中提取你关心的数据，按 proto 定义的结构组织输出。

**第三步：运行 Metric。**

用 `trace_processor` 命令行运行：

```bash
# 下载 trace_processor（Linux 和 Mac）
curl -LO https://get.perfetto.dev/trace_processor
chmod +x ./trace_processor

# 运行自定义 Metric
./trace_processor --run-metrics cold_start_metric trace.perfetto-trace

# 同时运行多个 Metric
./trace_processor --run-metrics cold_start_metric,android_cpu trace.perfetto-trace

# 输出为 JSON 格式
./trace_processor --run-metrics cold_start_metric --metrics-output=json trace.perfetto-trace

# 输出为 protobuf 二进制（方便程序解析）
./trace_processor --run-metrics cold_start_metric --metrics-output=binary trace.perfetto-trace
```

也可以在 Perfetto UI 中直接使用本地 `trace_processor` 实例，避免浏览器的 WASM 内存限制：

```bash
./trace_processor trace.perfetto-trace --httpd
```

启动后 Perfetto UI 会通过 TCP 连接本地的 trace_processor，性能更好，也不会受到浏览器 2GB WASM 内存上限的约束。这对于分析几百 MB 甚至几 GB 的大 Trace 特别有用。

### 内置 Metric 列表

Perfetto 自带的 Metric 涵盖了常见场景。一些常用的：

| Metric 名称 | 说明 |
|---|---|
| `android_cpu` | CPU 使用率和调度统计 |
| `android_mem` | 内存使用统计 |
| `android_power` | 功耗相关统计 |
| `android_startup` | App 启动时间统计 |
| `android_threadtime` | 线程 CPU 时间统计 |
| `android_simpleperf` | Simpleperf 采样数据统计 |

[已确认：内置 Metric 列表来源于 perfetto.dev 官方文档]

当内置 Metric 不满足需求时，你可以用 `--metric-extension` 在运行时覆盖内置 Metric 的 SQL 逻辑，或者完全自定义新的 Metric。

### 旧版 Metric vs Trace Summarization

Perfetto 的 Metric 系统正在经历一次代际更替。上面讲的基于 `.sql` + `.proto` + `--run-metrics` 的工作方式是旧版（v1）Metric 系统。Perfetto 官方推荐新项目使用 **Trace Summarization** API——它是对旧版 Metric 的封装和升级，提供了更稳定的接口和更好的工具链支持。Trace Summarization 通过 Python API 的 `tp.trace_summary()` 调用，返回结构化的 protobuf 消息。在 Python API 一节中我们会详细讲到。

如果你已经在维护旧版 Metric，它们仍然完全可用，不需要立即迁移。但如果是新写的 Metric，建议直接基于 Trace Summarization 的框架来组织。

## Perfetto 宏（Macros）与仪表板

### 什么是宏

Perfetto UI 的宏（Macros）是一种可复用的分析自动化脚本。简单来说，它是一组命名的命令序列，可以在 Perfetto UI 中一键执行，用于完成那些你每次分析都要手动重复的操作。

举个例子：每次分析启动性能时，你都要做这几件事——找到 main 线程、缩放到启动阶段、显示 CPU 频率 Track、隐藏不相关的进程。如果把这些操作固化成一个宏，下次打开 Trace 后一个命令就能完成所有准备工作。

### 宏的配置方式

宏在 Perfetto UI 的设置页面中配置。每个宏有一个唯一标识符（格式如 `user.myteam.StartupAnalysis`）和一组命令。命令包括：

- **Pin track**：固定（钉住）特定的 Track，使其始终可见
- **Add debug track**：添加一个基于 SQL 查询的调试 Track
- **Set viewport**：设置当前可视区域的时间范围
- **Toggle track**：展开或收起指定 Track

在 Perfetto UI 中，通过命令面板（Command Palette，快捷键 `Ctrl+Shift+P`）可以搜索和执行已注册的宏。

### 用宏构建团队分析流程

宏的真正威力在于团队协作。通过 Perfetto 的 Extension Server 机制，团队可以把一套共享的宏部署到内部服务器上，所有团队成员打开 Perfetto UI 时自动加载这些宏。

典型的团队级宏方案可能包括：

- **启动分析宏**：自动定位启动时间窗口、固定关键 Track、高亮 Binder 调用
- **卡顿分析宏**：自动查找 `doFrame` 中耗时超过阈值的帧、展开 RenderThread Track、显示 GPU 渲染阶段
- **功耗分析宏**：自动显示 CPU 频率、集群状态、wakelock 持有时长

这样做的价值不只是省时间。更重要的是，它把团队中资深工程师的分析思路固化下来——新同学拿到一个 Trace，运行团队的标准分析宏，就能看到老手会看的东西。

[待高爷补充：Perfetto UI 命令面板执行宏的截图]

## Trace Processor Python API 的高级用法

### 为什么需要 Python API

命令行 `trace_processor` 适合一次性查询和脚本，但当你需要做以下事情时，Python API 就不可或缺了：

- **批量分析**：一次性跑几百个 Trace，统计 P50/P90/P99 延迟分布
- **与数据科学生态集成**：把 Trace 数据转成 Pandas DataFrame，用 matplotlib 画图，甚至用机器学习模型做异常检测
- **自动化报告**：每天自动分析昨天的回归测试 Trace，生成性能报告推送给我
- **CI/CD 集成**：在持续集成流水线中自动运行性能分析，发现回归时阻塞合并

### 安装与基本使用

```bash
pip install perfetto
```

最基本的使用方式——加载一个 Trace 并执行 SQL 查询：

```python
from perfetto.trace_processor import TraceProcessor

# 加载 Trace 文件
tp = TraceProcessor(trace='path/to/trace.perfetto-trace')

# 执行 SQL 查询
result = tp.query('SELECT name, dur FROM slice WHERE name LIKE "%doFrame%" LIMIT 10')

# 迭代结果
for row in result:
    print(f'{row.name}: {row.dur / 1e6:.2f} ms')
```

查询结果可以直接转为 Pandas DataFrame：

```python
df = result.as_pandas_dataframe()
print(df.describe())
```

这一行转换是 Python API 的关键优势之一。一旦你有了 DataFrame，Pandas 的全部能力都可以用上——过滤、分组、统计、可视化，全部在 Python 生态内完成。

### BatchTraceProcessor：批量分析多个 Trace

当你需要分析一批 Trace 时（比如 CI/CD 中每次构建产出的 Trace），`BatchTraceProcessor` 比循环调用 `TraceProcessor` 高效得多：

```python
from perfetto.batch_trace_processor import BatchTraceProcessor

# 加载多个 Trace
traces = [
    'traces/build_001.perfetto-trace',
    'traces/build_002.perfetto-trace',
    'traces/build_003.perfetto-trace',
]

batch = BatchTraceProcessor(traces=traces)

# 对所有 Trace 执行同一个查询
results = batch.query_and_flatten(
    'SELECT name, dur FROM slice WHERE name = "activityStart"'
)

# results 是一个合并后的 DataFrame，带有一列标识来源 Trace
print(results)
```

`BatchTraceProcessor` 会并行加载和查询所有 Trace。对于统计类分析特别有用——比如你想看最近 100 次构建的冷启动时间分布，用 `query_and_flatten` 一条 SQL 搞定。

需要注意的是，每个 Trace 加载后会完全驻留在内存中。如果 Trace 很大（几百 MB），同时加载几十个可能会撑爆内存。Perfetto 官方建议对于超大规模分析（数千个 Trace）使用 Bigtrace 方案，通过 Kubernetes 集群来分布式处理。

### Trace Summarization：结构化指标提取

前面提到 Trace Summarization 是新版 Metric API。在 Python 中它的用法如下：

```python
from perfetto.trace_processor import TraceProcessor

tp = TraceProcessor(trace='trace.perfetto-trace')

# 运行 Trace Summarization（替代旧版的 tp.metric()）
summary = tp.trace_summary()

# summary 是一个 TraceMetrics protobuf 消息
# 可以访问内置 Metric
if summary.HasField('android_cpu'):
    cpu = summary.android_cpu
    for process in cpu.process_info:
        print(f'{process.name}: {process.cpu_time_ms} ms')
```

如果你有自定义 Metric（SQL + proto 文件），可以通过 `TraceProcessorConfig` 加载：

```python
from perfetto.trace_processor import TraceProcessor, TraceProcessorConfig

config = TraceProcessorConfig(
    add_sql_packages=['/path/to/my_metrics_dir']
)
tp = TraceProcessor(trace='trace.perfetto-trace', config=config)
summary = tp.trace_summary()
```

`add_sql_packages` 选项会加载指定目录下的 SQL 和 proto 文件，目录名会作为包名。这样你的自定义 Metric 就可以像内置 Metric 一样通过 `trace_summary()` 调用了。

### 一个实用的自动化示例：冷启动回归检测

把上面的能力组合起来，我们可以写一个实用的自动化脚本——每次构建后自动抓 Trace、分析冷启动时间、判断是否有回归：

```python
import subprocess
from perfetto.trace_processor import TraceProcessor

def capture_trace(device_serial, config_file, output_path):
    """在设备上抓取 Perfetto Trace"""
    subprocess.run([
        'adb', '-s', device_serial, 'shell',
        'perfetto', '-c', config_file, '-o', '/data/misc/perfetto-traces/trace.pb'
    ])
    subprocess.run([
        'adb', '-s', device_serial, 'pull',
        '/data/misc/perfetto-traces/trace.pb', output_path
    ])

def analyze_startup(trace_path, baseline_ms=800, threshold_pct=10):
    """分析冷启动时间并检测回归"""
    tp = TraceProcessor(trace=trace_path)
    result = tp.query("""
        SELECT
          (s2.ts - s1.ts) / 1e6 AS startup_ms
        FROM slice s1
        JOIN slice s2 ON s2.name = 'FirstFrame'
        WHERE s1.name = 'activityStart'
        ORDER BY startup_ms
        LIMIT 1
    """)
    df = result.as_pandas_dataframe()
    if df.empty:
        return None
    startup_ms = df['startup_ms'].iloc[0]
    regression = startup_ms > baseline_ms * (1 + threshold_pct / 100)
    return {
        'startup_ms': startup_ms,
        'baseline_ms': baseline_ms,
        'is_regression': regression
    }
```

[待验证：`FirstFrame` slice 名称在不同 Android 版本和 App 中的表现可能不同，实际使用时需根据项目中的 atrace 标记调整 SQL]

这个脚本的逻辑很简单：抓 Trace → 查 SQL → 对比基线。但它已经构成了 CI/CD 性能检测的核心骨架。在下一节中我们会把它接入完整的流水线。

## 将 Perfetto 集成到 CI/CD

### 为什么要把 Perfetto 放进 CI/CD

性能问题有一个很讨厌的特性：它是渐进恶化的。每次提交代码增加 10ms 的启动延迟，单个 commit 看不出来，但一个季度下来就是 500ms 的退步。等到用户投诉时，你已经不知道是哪次提交引入的问题了。

把 Perfetto 分析接入 CI/CD，就是为了在每次代码提交时自动检测这种渐进回归。核心思路是：每次构建或合入时自动运行性能测试 → 抓取 Trace → 用 SQL/Python 自动分析 → 与历史基线对比 → 超过阈值就告警或阻塞合并。

### 流水线的整体架构

一个完整的 Perfetto CI/CD 流水线通常由以下环节组成：

**1. 触发**：代码提交（PR / merge to main）、定时任务（每日构建）、或手动触发。

**2. 测试执行**：在稳定的设备或模拟器上运行性能测试。AndroidX Macrobenchmark 库是一个不错的选择——它在底层就是用 Perfetto 抓 Trace 的，提供了标准的 benchmark 框架。如果你的测试场景比较特殊（比如需要特定的硬件环境），也可以自己写脚本通过 `adb shell perfetto` 抓 Trace。

**3. Trace 收集**：从设备拉取 `.perfetto-trace` 文件到 CI 环境的存储中。建议按构建号和时间戳组织目录结构，方便回溯。

**4. 自动分析**：这是流水线的核心。用 Trace Processor 的 Python API（或命令行 `--run-metrics`）对 Trace 做结构化分析，提取关键指标。

**5. 基线对比与告警**：将当前指标与历史基线对比。对比策略可以多种选择：固定阈值（"启动时间不超过 800ms"）、百分比偏差（"不超过历史均值的 110%"）、或统计检验（"P 值 < 0.05 才认为有显著回归"）。检测到回归时，自动在 PR 上添加评论、发送告警、或阻塞合并。

**6. 报告与可视化**：将分析结果输出为报告。简单的可以是一段 JSON 或 Markdown；进阶的可以接入 Grafana 等仪表板工具做趋势图。

### 实战配置示例

下面是一个基于 GitHub Actions 的配置示例，演示如何在 PR 中自动检测启动性能回归：

```yaml
# .github/workflows/perf-regression.yml
name: Performance Regression Detection

on:
  pull_request:
    branches: [main]

jobs:
  perf-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install perfetto

      - name: Run benchmark & capture trace
        run: |
          # 通过 adb 连接设备农场（或 Firebase Test Lab）
          python scripts/run_benchmark.py --output traces/

      - name: Analyze trace & check regression
        run: |
          python scripts/check_regression.py \
            --trace traces/latest.perfetto-trace \
            --baseline baselines/startup.json \
            --threshold-pct 10 \
            --report report.md

      - name: Comment on PR
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('report.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: report
            });
```

[待验证：实际部署需要根据 CI 环境（Jenkins / GitLab CI / GitHub Actions）和设备农场方案调整]

### 降低误报率的几个实践

性能数据天然有噪声。同一台设备上连续跑三次同样的测试，结果可能有 5-10% 的波动。如果阈值设得太紧，你会被误报淹没；太松又放过了真回归。几个实用的建议：

**稳定测试环境**：使用相同的设备型号、相同的系统版本、关闭后台应用、固定屏幕亮度和音量。如果是物理设备，考虑使用制冷夹防止温控降频。Firebase Test Lab 等 cloud 方案也能提供相对稳定的环境。

**多次采样取中位数**：不要只跑一次。跑 3-5 次，取中位数作为本次构建的指标值。中位数比均值更能抵抗极端值。

**滑动窗口基线**：不要用一个固定值做基线。用最近 N 次构建（比如最近 10 次）的指标作为动态基线。这样当整体性能水平缓慢提升时，基线也会跟着上升，不会因为"比半年前快了"而误报。

**分层告警**：设置两级阈值。超过一级阈值（比如 5%）发告警但不阻塞，超过二级阈值（比如 15%）阻塞合并。给团队一个缓冲区间，避免每次 5% 的波动都卡住流程。

## Custom Trace Point 的最佳实践

### 为什么需要自定义 Trace 点

Perfetto 默认抓取的是系统级事件——CPU 调度、Binder 调用、渲染管线各阶段等。这些信息对于分析系统层面的性能问题已经足够。但当你需要分析 App 内部特定逻辑的耗时（比如"图片解码"、"数据库查询"、"JSON 解析"）时，系统级 Trace 看不到这些细节。

这时候就需要在代码里手动插入 Trace 点。当 Perfetto 抓 Trace 时，这些自定义的点会和系统事件一起被记录下来，在 Perfetto UI 中以 Slice 的形式出现在对应线程的 Track 上。

### 方法一：ATrace API（推荐用于 Android）

ATrace 是 Android NDK 提供的轻量级 Trace API，从 API 18 开始支持（native API 从 API 23 开始）。它发出的 Trace 点会直接出现在 Perfetto UI 中，无需额外配置。

**Java/Kotlin 层：**

```java
import android.os.Trace;

// 标记一段代码的开始和结束
Trace.beginSection("ImageDecode");
try {
    decodeImage(bitmap);
} finally {
    Trace.endSection(); // 必须与 beginSection 配对
}
```

注意 `beginSection` 和 `endSection` 必须在同一

## 参考资料

### Perfetto v52/v54 大改版：Dark Mode + ANR 分类 + 位图时序
- 来源：https://github.com/google/perfetto/releases
- 类型：article
- 摘要：UI层：Dark Mode、触摸支持、多Track批量操作。分析层：android_anrs新增anr_type字段、android.bitmaps位图时序数据、slice_self_dur自持续时间计算、regexp_extract函数、JSON trace解析性能提升。
- 入库时间：2026-04-08

