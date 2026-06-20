---
title: "Perfetto 的高级用法"
chapter: "13"
section: "13.7"
drafted_date: "2026-04-03"
applicable_versions: "Android 8.0 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-22"
last_verified_against: "perfetto.dev/docs/analysis/metrics, perfetto.dev/docs/analysis/trace-summary, perfetto.dev/docs/instrumentation/tracing-sdk"
confidence: medium
sources:
  - type: official
    path: "https://perfetto.dev/docs/analysis/sql-tables"
  - type: official
    path: "https://perfetto.dev/docs/analysis/trace-processor"
  - type: official
    path: "https://perfetto.dev/docs/analysis/metrics"
  - type: official
    path: "https://perfetto.dev/docs/visualization/macros"
  - type: official
    path: "https://perfetto.dev/docs/instrumentation/tracing-sdk"
  - type: blog
    path: "https://mp.weixin.qq.com/s/v6fGXbEZcTfxhfaKcMNhEQ"
  - type: official
    path: "https://perfetto.dev/docs/analysis/trace-summary"
tags:
  - android
  - perfetto
  - research
task9_result: pass-tech-review
task9_reviewed_date: "2026-05-07"
task9_reviewed_by: openclaw-task9
last_task2b_at: "2026-05-07T15:44:35+08:00"
last_task9_at: "2026-05-07T17:29:52+08:00"
last_task9_audit: "2026-06-18"
last_task9_audit_log: "logs/deep-review/2026-06-18-19-audit.md"
task9_review_notes: "2026-05-07 Task9 17:29：pass-tech-review。P0 0 / P1 0 / P2 4（均为既有 suggestions 或日志记录，本轮不重复写入）；自动晋升 finalized。"
last_task9_review_log: "logs/deep-review/2026-05-07-17-deep-review.md"

status: finalized
reviewed_by: openclaw-task6
reviewed_date: "2026-05-07"
task6_result: pass-light-edit
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
task2b_state: fixed
last_task6_at: "2026-05-07T17:07:00+08:00"
last_task6_audit: "2026-06-20"
last_task6_review_log: "logs/review/2026-05-07-17-review.md"
task2b_result: fixed
task6_review_notes: "2026-05-07 Task6 17:07：Task2B 修复后写作复审；清理形容词冒号起手句 1 处，frontmatter 去重并更新状态；L1/L2 通过，无新增 L3/L4 回炉项，送 Task9 复审。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-20
---


# Perfetto 的高级用法

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 自定义 Perfetto Metric：编写 SQL + proto 定义输出指标
- 🔹 Perfetto 宏（Macros）与仪表板
- 🔹 Trace Processor Python API 的高级用法
- 🔹 将 Perfetto 集成到 CI/CD 的自动化性能测试中
- 🔹 自定义 Trace Point 的最佳实践（atrace_begin / TRACE_EVENT）

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

前面六章已经覆盖了 Perfetto 的基础操作，包括抓 Trace、读 Trace、打开超大 Trace、做专题分析，以及看线程 CPU 状态。掌握这些之后，已经能应对大部分日常性能分析场景。

Perfetto 的能力不止于“打开网页看 Trace”。当分析要从单次排障走向批量处理、团队复用和自动回归检测时，重点就变成了自定义 Metric、Python API、宏、CI/CD 集成，以及代码里的自定义 Trace 点。

## 自定义 Perfetto Metric：用 SQL 把 Trace 变成结构化指标

### 为什么需要自定义 Metric

Perfetto 自带了 `android_cpu`、`android_mem`、`android_startup` 等内置 Metric，用 `--run-metrics` 参数就能跑。这些覆盖了最常见的需求。但当团队要回答一些特定问题时，内置 Metric 就不够用了。比如：

- "App 首页冷启动，从 `activityStart` 到第一帧上屏，平均耗时是多少？P90 是多少？"
- "RecyclerView 的每个 `onBindViewHolder` 调用耗时，有没有超过 16ms 的？"
- "相机预览的帧间隔抖动程度如何？有多少帧的 capture-to-delivery 超过了阈值？"

这些问题都是对 Trace 中特定 Slice 的过滤、聚合和统计。Perfetto 提供的机制允许用 SQL 表达这些逻辑，再把结果输出成结构化的 protobuf 消息，这就是自定义 Metric。

### Trace Processor 的核心数据模型

写 SQL 之前，需要先理解 Trace Processor 把 Trace 数据组织成了什么样的表。Trace Processor 是一个 C++ 库，它把各种格式的 Trace 文件解析后暴露出 SQL 接口。无论是在 Perfetto UI 的 Query 页面、命令行的 `trace_processor` shell，还是 Python API 中，查的都是同一套表。

核心表有这几类。**Track 类**：`track`（基表）、`thread_track`（线程级 Track）、`process_track`（进程级 Track）、`process_counter_track`（进程级计数器 Track）等。**Event 类**：`slice`（时间片，比如一次 `doFrame` 就是一个 slice）、`counter`（计数器值，比如 CPU 频率）、`sched`（CPU 调度事件）。**实体类**：`process`（进程信息）、`thread`（线程信息）。

Track 和 Event 之间的关系是通过 `track_id` 关联的。每个 slice 或 counter 都有一个 `track_id`，指向它所属的 Track。Track 又通过 `thread_track` 或 `process_track` 中的 `utid`/`upid` 关联到具体的线程或进程。

Trace Processor 没有直接用 PID/TID 做标识，而是引入了 `utid`（unique tid）和 `upid`（unique pid）。原因是 Android/Linux 系统中 PID/TID 会被复用，一个进程退出后，它的 PID 可能被另一个完全不相干的进程拿走。如果直接用 PID 做 JOIN，可能会把不同进程的数据错误地关联到一起。`utid`/`upid` 是 Trace Processor 分配的单调递增 ID，保证了唯一性。

查看当前 Trace 有哪些表，可以执行：

```sql
SELECT name FROM sqlite_master WHERE type='table';
```

查看某张表有哪些字段：

```sql
SELECT * FROM pragma_table_info('slice');
```

[待补充：Perfetto UI Query 页面执行 SQL 查询的截图]

### 编写自定义 Metric 的流程

自定义 Metric 由两部分组成：一个 `.sql` 文件定义查询逻辑，一个 `.proto` 文件定义输出结构。

**第一步：定义 proto 消息结构。**

假设要统计 App 冷启动各阶段的耗时分布，先写一个 proto 文件：

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

`extend TraceMetrics` 用来把自定义 Metric 注册到 Perfetto 的 Metric 体系中，字段号在 450–500 范围内用于本地开发。字段名 `cold_start_metric` 会作为 SQL 输出表的表名和最终 proto 中的字段名。

**第二步：编写 SQL 查询。**

对应的 SQL 文件用 PerfettoSQL 的 `SELECT` 和 `CREATE_FUNCTION` 等语法来组织：

```sql
-- cold_start_metric.sql
-- 查询冷启动各阶段耗时

-- 第一步：提取关键阶段的 slice，生成中间视图
CREATE VIEW cold_start_phases AS
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
ORDER BY s.ts;

-- 第二步：用 proto builder 函数组装输出
CREATE VIEW cold_start_metric_output AS
SELECT
  ColdStartMetric(
    'phases',
    (SELECT RepeatedField(
      ColdStartPhase(
        'phase_name', phase_name,
        'duration_ns', duration_ns
      )
    ) FROM cold_start_phases),
    'total_duration_ns',
    (SELECT SUM(duration_ns) FROM cold_start_phases)
  ) AS cold_start_metric
FROM cold_start_phases
LIMIT 1;
```

SQL 文件名（`cold_start_metric`）必须和 proto 中 `extend TraceMetrics` 的字段名一致，这是 Perfetto 的注册约定。中间视图 `cold_start_phases` 负责提取和过滤数据，输出视图 `cold_start_metric_output` 负责用 `ColdStartMetric(...)` proto builder 把结果组装成 proto 消息。`RepeatedField(...)` 用来构造 `repeated` 字段。输出视图必须以 `_output` 结尾，Trace Processor 扫描这个后缀来找到最终输出。

**第三步：运行 Metric。**

本地自定义 metric 不能直接把 `cold_start_metric` 当作内置 metric id 运行。要跑通本地文件，有两种常见方式：

```bash
# 下载 trace_processor（Linux 和 Mac）
curl -LO https://get.perfetto.dev/trace_processor
chmod +x ./trace_processor

# 方式 1：直接把本地 SQL 文件路径传给 --run-metrics
./trace_processor --run-metrics /abs/path/cold_start_metric.sql trace.perfetto-trace

# 输出 JSON 结果
./trace_processor \
  --run-metrics /abs/path/cold_start_metric.sql \
  --metrics-output=json \
  trace.perfetto-trace

# 方式 2：metric 放在扩展目录里，再显式加载扩展目录
./trace_processor \
  --run-metrics cold_start_metric \
  --metric-extension /abs/path/my_metrics@/ \
  trace.perfetto-trace
```

第一种适合本地迭代 SQL；第二种适合把 `.sql` / `.proto` 组织成扩展目录，再用 metric id 复用。官方 metrics 文档里的自定义 metric 示例也是“SQL 文件路径”或“`--metric-extension` + metric id”这两条路径。

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

当内置 Metric 不满足需求时，可以用 `--metric-extension` 在运行时覆盖内置 Metric 的 SQL 逻辑，或者完全自定义新的 Metric。

### 旧版 Metric vs Trace Summarization

Perfetto 的自动化分析能力分三层，由底到顶：

1. **旧版 Metric（v1）**：基于 `.sql` + `.proto` + `--run-metrics`。完全可用，但 SQL 直接操作底层表结构，Trace 格式变化时可能需要调整。

2. **Perfetto Standard Library**：官方维护的标准化 SQL 模块集合，通过 `referenced_modules` 引用。前面的 Trace Summarization 示例中 `referenced_modules: "linux.memory.process"` 就是引用了 Standard Library 的 `linux.memory.process` 模块，它提供了 `memory_rss_and_swap_per_process` 表等标准化视图。已有的官方模块包括 `android.cpu.cpu_per_uid` / `android.cpu.cluster_type`、`android.startup.startups` / `android.startup.startup_breakdowns`、`android.frames.jank_type` / `android.frames.per_frame_metrics`、`linux.memory.process` 等。注意 Standard Library 模块名使用点分命名（如 `android.cpu.cpu_per_uid`），与旧版 v1 metric id（如 `android_cpu`）是两套命名体系；在 `INCLUDE PERFETTO MODULE` 和 `referenced_modules` 中应使用点分模块名。优先复用这些模块，避免从零写底层 SQL。

3. **Trace Summarization（v2）**：基于 Standard Library 模块之上的结构化指标提取 API。通过 `metric_spec` + `referenced_modules` + `group_by` + `aggregates` 声明式定义指标，Python API 调用 `tp.trace_summary()` 返回结构化 `TraceSummary`。

三层的关系是：**Standard Library 提供稳定的中间表和视图 → Trace Summarization 在这些表上声明聚合逻辑 → 旧版 Metric 是最底层的手写 SQL，仍有用但维护成本更高。** 实践中优先用 Standard Library 模块 + Trace Summarization，只有缺口指标才写自定义 PerfettoSQL 模块。

如果团队已经在维护旧版 Metric，它们仍然完全可用，不需要立即迁移。但新写的 Metric 更适合直接基于 Standard Library + Trace Summarization 框架来组织。

## Perfetto 宏（Macros）与仪表板

### 什么是宏

Perfetto UI 的宏（Macros）是一种可复用的分析自动化脚本。简单来说，它是一组命名的命令序列，可以在 Perfetto UI 中一键执行，用来完成那些每次分析都要重复的操作。

举个例子：每次分析启动性能时，通常都要先找到 main 线程、缩放到启动阶段、显示 CPU 频率 Track，再隐藏不相关的进程。如果把这些操作固化成一个宏，下次打开 Trace 后一个命令就能完成准备工作。

### 宏的配置方式

宏在 Perfetto UI 的设置页面中配置。每个宏有一个唯一标识符（格式如 `user.myteam.StartupAnalysis`）和一组命令。命令包括：

- **Pin track**：固定（钉住）特定的 Track，使其始终可见
- **Add debug track**：添加一个基于 SQL 查询的调试 Track
- **Set viewport**：设置当前可视区域的时间范围
- **Toggle track**：展开或收起指定 Track

在 Perfetto UI 中，通过命令面板（Command Palette，快捷键 `Ctrl+Shift+P`）可以搜索和执行已注册的宏。

### 用宏构建团队分析流程

宏的核心价值在于团队协作。通过 Perfetto 的 Extension Server 机制，团队可以把一套共享的宏部署到内部服务器上，所有团队成员打开 Perfetto UI 时自动加载这些宏。

典型的团队级宏方案可能包括：

- **启动分析宏**：自动定位启动时间窗口、固定关键 Track、高亮 Binder 调用
- **卡顿分析宏**：自动查找 `doFrame` 中耗时超过阈值的帧、展开 RenderThread Track、显示 GPU 渲染阶段
- **功耗分析宏**：自动显示 CPU 频率、集群状态、wakelock 持有时长

这样做除了省时间，更实际的价值是把团队里资深工程师的分析思路固化下来。新同学拿到一个 Trace，运行标准分析宏，就能先看到老手会看的东西。

[待补充：Perfetto UI 命令面板执行宏的截图]

## Trace Processor Python API 的高级用法

### 为什么需要 Python API

命令行 `trace_processor` 适合一次性查询和脚本，但下面这些场景更适合用 Python API：

- **批量分析**：一次性跑几百个 Trace，统计 P50/P90/P99 延迟分布
- **与数据科学生态集成**：把 Trace 数据转成 Pandas DataFrame，用 matplotlib 画图，甚至用机器学习模型做异常检测
- **自动化报告**：每天自动分析昨天的回归测试 Trace，生成性能报告
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

这一行转换是 Python API 的关键优势之一。有了 DataFrame，Pandas 的过滤、分组、统计和可视化能力就都能直接用上。

### BatchTraceProcessor：批量分析多个 Trace

需要分析一批 Trace 时（比如 CI/CD 中每次构建产出的 Trace），`BatchTraceProcessor` 比循环调用 `TraceProcessor` 高效得多：

```python
from perfetto.batch_trace_processor.api import BatchTraceProcessor

# 加载多个 Trace，推荐用上下文管理器自动释放资源
traces = [
    'traces/build_001.perfetto-trace',
    'traces/build_002.perfetto-trace',
    'traces/build_003.perfetto-trace',
]

# 依赖安装：pip3 install perfetto pandas
with BatchTraceProcessor(traces=traces) as batch:
    # 对所有 Trace 执行同一个查询
    results = batch.query_and_flatten(
        'SELECT name, dur FROM slice WHERE name = "activityStart"'
    )

    # results 是一个合并后的 DataFrame，带有一列标识来源 Trace
    print(results)
```

`BatchTraceProcessor` 会并行加载和查询所有 Trace。它特别适合统计类分析，比如要看最近 100 次构建的冷启动时间分布，用 `query_and_flatten` 一条 SQL 就够了。

每个 Trace 加载后会完全驻留在内存中。如果 Trace 很大（几百 MB），同时加载几十个可能会撑爆内存。

### BatchTraceProcessor vs Bigtrace

当 Trace 数量超出单机内存能力时，有两个选择：

| 维度 | BatchTraceProcessor | Bigtrace |
|---|---|---|
| 部署模式 | 单机多进程并行加载 | Kubernetes 集群分布式 |
| 架构 | 本机并行加载多个 Trace | Orchestrator 分片调度 → Worker Pod 运行 TraceProcessor → 从 Object Store 读取 trace |
| 适用规模 | 几十到几百个 Trace | 数千到数万个 Trace |
| 内存约束 | 受单机内存限制 | 每个 Worker 独立内存，可水平扩展 |
| 数据源 | 本地文件系统或 GCS | GCS / 本地 Object Store |
| 适用场景 | CI 回归检测、团队级批量分析 | 大规模回归测试、云端 trace 仓库分析 |

BatchTraceProcessor 的适用边界是本机内存能容纳所有待分析 Trace。当 Trace 数量增长到单机无法承载时，Bigtrace 通过 K8s 集群把 SQL 查询分发到多个 Worker Pod 上并行执行。Bigtrace 的部署细节参见 perfetto.dev/docs/deployment/deploying-bigtrace-on-kubernetes。

### Trace Summarization：结构化指标提取

Trace Summarization 是新版 Metric API。它要求先提供 `specs`，再用 `metric_ids` 指定要生成的指标；返回对象是 `TraceSummary`，只包含这次请求到的 summary metric，不是旧版 `TraceMetrics` 的无参替代。

这组示例直接对应官方文档：

```textproto
// spec.textproto
metric_spec {
  id: "memory_per_process"
  dimensions: "process_name"
  value: "avg_rss_and_swap"
  query: {
    table: {
      table_name: "memory_rss_and_swap_per_process"
    }
    referenced_modules: "linux.memory.process"
    group_by: {
      column_names: "process_name"
      aggregates: {
        column_name: "rss_and_swap"
        op: DURATION_WEIGHTED_MEAN
        result_column_name: "avg_rss_and_swap"
      }
    }
  }
}
```

```python
from perfetto.trace_processor import TraceProcessor

with open('spec.textproto', 'r') as f:
    spec_text = f.read()

with TraceProcessor(trace='my_trace.pftrace') as tp:
    summary = tp.trace_summary(
        specs=[spec_text],
        metric_ids=["memory_per_process"],
    )
    print(summary)
```

命令行等价写法是：

```bash
trace_processor_shell summarize --metrics-v2 memory_per_process \
  my_trace.pftrace spec.textproto
```

`summarize` 是 `trace_processor_shell` 的子命令，`--metrics-v2` 指定要跑的 metric id，后面跟 trace 文件和 spec 文件。如果需要多版本兼容，保留旧命令时须标注 trace_processor 版本。

如果要把 summary 结果和 Python 数据处理链串起来，可以先在 Trace Processor 里产出稳定的 `TraceSummary`，再把其中的指标字段转成 DataFrame。这样比直接依赖临时 SQL 表结构更稳。

### 一个实用的自动化示例：冷启动回归检测

把 Metric、Python API 和 SQL 查询组合起来，可以写一个实用的自动化脚本——每次构建后自动抓 Trace、分析冷启动时间、判断是否有回归：

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

def analyze_startup(trace_path, baseline_ms, threshold_pct, target_package):
    """分析冷启动时间并检测回归。

    优先使用 Perfetto Standard Library 的 android.startup 模块；
    如果 Standard Library 不可用，则回退到手写 SQL（需限定进程和时间窗口）。
    """
    tp = TraceProcessor(trace=trace_path)

    # 方案 A：使用 Standard Library android.startup.startups
    # 该模块由 Perfetto 官方维护，内部已处理进程、launch id 和时间窗口约束
    try:
        startup_result = tp.query("""
            INCLUDE PERFETTO MODULE android.startup.startups;
            INCLUDE PERFETTO MODULE android.startup.startup_breakdowns;

            SELECT
              s.package,
              s.dur / 1e6 AS startup_ms
            FROM android_startups s
            WHERE s.package = '{}'
            ORDER BY s.ts DESC
            LIMIT 1
        """.format(target_package))
        df = startup_result.as_pandas_dataframe()
    except Exception:
        # 方案 B：手写 SQL，必须限定目标进程和时间窗口
        # FirstFrame 是业务自定义 trace point，需按实际项目中的 atrace 标记替换
        startup_result = tp.query("""
            SELECT
              (s2.ts - s1.ts) / 1e6 AS startup_ms
            FROM slice s1
            JOIN thread_track tt1 ON s1.track_id = tt1.id
            JOIN thread t1 ON tt1.utid = t1.utid
            JOIN process p ON t1.upid = p.upid
            JOIN slice s2
              ON s2.track_id = s1.track_id
              AND s2.name = 'FirstFrame'
              AND s2.ts > s1.ts
              AND s2.ts - s1.ts < 30e9
            WHERE s1.name = 'activityStart'
              AND p.name = '{}'
            ORDER BY s1.ts DESC
            LIMIT 1
        """.format(target_package))
        df = startup_result.as_pandas_dataframe()
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

方案 A 优先使用 `android.startup.startups` Standard Library 模块，由 Perfetto 官方维护，内部已处理进程、launch id 和时间窗口约束。方案 B 的手写 SQL 至少限定了：① 目标进程（`p.name`）② 时间窗口（`s2.ts > s1.ts` 且差值 < 30s）③ 同一 track（同一线程）。`FirstFrame` 是业务自定义 trace point 名称，需按项目实际的 atrace 标记替换；如果改用 FrameTimeline 的 `actual_present_time`，则应走 `android.frames` 模块。

这个脚本按三步执行：抓 Trace → 查 SQL → 对比基线。它还需要接入完整流水线，才能在每次提交时自动收集指标并比较基线。

## 将 Perfetto 集成到 CI/CD

### 为什么要把 Perfetto 放进 CI/CD

性能问题有一个很讨厌的特性，它往往是渐进恶化的。每次提交代码增加 10ms 的启动延迟，单个 commit 看不出来，但一个季度下来就是 500ms 的退步。等到用户投诉时，团队往往已经不知道是哪次提交引入的问题了。

把 Perfetto 分析接入 CI/CD，就是为了在每次代码提交时自动检测这种渐进回归。核心思路是：每次构建或合入时自动运行性能测试 → 抓取 Trace → 用 SQL/Python 自动分析 → 与历史基线对比 → 超过阈值就告警或阻塞合并。

### 流水线的整体架构

一个完整的 Perfetto CI/CD 流水线通常由以下环节组成：

**1. 触发**：代码提交（PR / merge to main）、定时任务（每日构建）、或手动触发。

**2. 测试执行**：在稳定的设备或模拟器上运行性能测试。AndroidX Macrobenchmark 库是一个不错的选择，它在底层就是用 Perfetto 抓 Trace 的，提供了标准的 benchmark 框架。如果测试场景比较特殊（比如需要特定的硬件环境），也可以自己写脚本通过 `adb shell perfetto` 抓 Trace。

**3. Trace 收集**：从设备拉取 `.perfetto-trace` 文件到 CI 环境的存储中。建议按构建号和时间戳组织目录结构，方便回溯。

**4. 自动分析**：这是流水线的核心。用 Trace Processor 的 Python API（或命令行 `--run-metrics`）对 Trace 做结构化分析，提取关键指标。

**5. 基线对比与告警**：将当前指标与历史基线对比。对比策略可以多种选择：固定阈值（"启动时间不超过 800ms"）、百分比偏差（"不超过历史均值的 110%"）、或统计检验（"P 值 < 0.05 才认为有显著回归"）。检测到回归时，自动在 PR 上添加评论、发送告警、或阻塞合并。

**6. 报告与可视化**：将分析结果输出为报告。简单的可以是一段 JSON 或 Markdown；进阶的可以接入 Grafana 等仪表板工具做趋势图。

### 实战配置示例

一个基于 GitHub Actions 的配置示例，可以在 PR 中自动检测启动性能回归：

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
            --threshold-config baselines/startup-thresholds.json \
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

阈值和测试环境要先绑定，再设置告警线。下面这组建议适合“同一台真机 + 同一 OS 版本 + release / non-debuggable build + Macrobenchmark”这一类固定实验室环境；如果换成共享设备池或模拟器，建议只做趋势告警，不直接拦截合并。

| 环境 | 适合看的指标 | 适合的动作 | 失效边界 |
|---|---|---|---|
| 固定真机（同机型 / 同 OS / 同 build） | 启动 `median`、帧时 `P90/P99`、每次运行的 `runs[]` | 可做 PR 级门禁；发现回归后重跑一次并保留 Trace | 设备发热、后台任务未清空时，单次结果会漂移 |
| 共享真机池 / Firebase Test Lab | `median` 趋势、最近多次构建分布 | 适合 nightly 告警和趋势图 | 设备分配不固定时，不适合一刀切硬阈值 |
| 模拟器 / GMD | 趋势变化、功能级 smoke 回归 | 适合验证流水线通不通 | Android Developers 明确不建议拿模拟器结果代表真实用户性能 |

Macrobenchmark 的 CI 输出本身就带 `runs[]`、`median`、`warmupIterations`、`repeatIterations`。告警逻辑至少要把这些原始字段一起落盘；只保留一个最终百分比，回头很难分辨是代码回归、热限频，还是设备背景噪声。

一个更稳的做法是把阈值改成配置文件，让不同场景单独校准。例如启动时间门禁只比较固定真机冷启动的 `median`，帧时门禁看 `P90` 或 `P99`，共享设备池只做趋势告警。这样能把“固定真机”和“共享设备池”两类噪声水平分开，不会再把一个 10% 阈值硬套到所有环境。

[已验证: 官方文档, developer.android.com/topic/performance/benchmarking/benchmarking-in-ci; developer.android.com/topic/performance/benchmarking/macrobenchmark-overview]

## 自定义 Trace Point 的最佳实践

### 为什么需要自定义 Trace 点

Perfetto 默认抓取的是系统级事件，比如 CPU 调度、Binder 调用、渲染管线各阶段等。这些信息对于分析系统层面的性能问题已经足够。但分析 App 内部特定逻辑的耗时，比如“图片解码”“数据库查询”“JSON 解析”时，系统级 Trace 看不到这些细节。

这时候就需要在代码里手动插入 Trace 点。当 Perfetto 抓 Trace 时，这些自定义的点会和系统事件一起被记录下来，在 Perfetto UI 中以 Slice 的形式出现在对应线程的 Track 上。

### 方法一：`android.os.Trace` / `ATrace_*`（Android-only 场景）

对 Android-only 的应用代码，优先用平台自带的 `android.os.Trace` 或 NDK `ATrace_*`。Perfetto SDK 官方文档也把这条线当成默认建议：如果只需要轻量 slice 标记，没有跨平台和自定义 schema 需求，先用系统自带 tracing API。

**Java/Kotlin 层：**

```java
import android.os.Trace;

Trace.beginSection("ImageDecode");
try {
    decodeImage(bitmap);
} finally {
    Trace.endSection();
}
```

`beginSection()` 和 `endSection()` 必须在同一线程内配对。适合标记主线程、RenderThread 或 worker thread 里的同步阶段。

**Native C/C++ 层：**

```cpp
#include <android/trace.h>

void DecodeFrame() {
  ATrace_beginSection("ImageDecode");
  // Several unrelated lines are omitted.
  ATrace_endSection();
}
```

`ATrace_beginSection()` / `ATrace_endSection()` 从 API 23 起可用，适合 JNI、解码器、渲染引擎这类 Native 代码路径。

**跨线程或跨回调路径：**

```cpp
#include <android/trace.h>

void StartCapture(int request_id) {
  ATrace_beginAsyncSection("CameraCapture", request_id);
}

void FinishCapture(int request_id) {
  ATrace_endAsyncSection("CameraCapture", request_id);
}
```

异步 trace point 更适合相机请求、网络回调、任务队列这类跨线程路径；开始和结束要用同一个 cookie。NDK 异步 API 从 API 29 起可用。

### 方法二：Perfetto SDK `TRACE_EVENT`（Native engine / richer schema）

当场景需要更丰富的 category、Native-only tracing、跨平台复用，或者后面准备扩成 counter / async event / typed schema 时，再切到 Perfetto SDK。一个最小骨架如下：

```cpp
#include <perfetto.h>

PERFETTO_DEFINE_CATEGORIES(
    perfetto::Category("rendering"),
    perfetto::Category("camera"));
PERFETTO_TRACK_EVENT_STATIC_STORAGE();

void InitPerfetto() {
  perfetto::TracingInitArgs args;
  args.backends = perfetto::kInProcessBackend;
  perfetto::Tracing::Initialize(args);
  perfetto::TrackEvent::Register();
}

void RenderFrame() {
  TRACE_EVENT("rendering", "RenderFrame");
  // Several unrelated lines are omitted.
}
```

这条路径更适合游戏引擎、跨平台运行时、系统服务或大型 Native 模块。App 业务代码只想补阶段耗时时，`android.os.Trace` / `ATrace_*` 通常更省事。

### Custom Data Source：结构化二进制 Trace Packet

TrackEvent 和 `TRACE_EVENT` 覆盖的是 slice / counter 这类通用标记。当需要向 Trace 里写入**结构化的二进制数据**（比如引擎级的渲染 pipeline 状态、自定义 schema 的性能采样、或系统服务的内部指标）时，Perfetto SDK 提供了 `perfetto::DataSource<T>` 这一更底层的抽象。

**TrackEvent vs Custom Data Source 的定位差异：**

| 维度 | TrackEvent / TRACE_EVENT | Custom Data Source |
|---|---|---|
| 数据格式 | Slice name + category + 可选 debug annotations | 自定义 protobuf schema |
| 典型用途 | 阶段耗时标记、异步事件、counter | 结构化二进制 packet、自定义 schema |
| 适用场景 | App 业务逻辑的阶段打点 | 引擎级采集、系统服务、自定义 counter/packet |
| Trace Processor 支持 | 内置 slice/counter 表直接可查 | 需自定义 SQL 或在 Trace Processor 侧注册解析 |

**最小 Custom Data Source 骨架：**

```cpp
// render_pipeline.proto — 定义自定义 packet schema
// syntax = "proto2";
// package my.protos;
// message RenderPassInfo {
//   optional string pass_name = 1;
//   optional int64 gpu_duration_ns = 2;
// }

// render_pass_data_source.h — DataSource 类定义与 static members 声明
#include <perfetto.h>

// 1. 继承 perfetto::DataSource<T> 定义数据源类
class RenderPassDataSource : public perfetto::DataSource<RenderPassDataSource> {
 public:
  void OnSetup(const SetupArgs&) override {}
  void OnStart(const StartArgs&) override {}
  void OnStop(const StopArgs&) override {}
};

// 2. 声明 static members（头文件中）
PERFETTO_DECLARE_DATA_SOURCE_STATIC_MEMBERS(RenderPassDataSource);

// render_pass_data_source.cc — static members 定义（源文件中，仅一处）
PERFETTO_DEFINE_DATA_SOURCE_STATIC_MEMBERS(RenderPassDataSource);

// main.cc — 初始化与注册
void InitTracing() {
  perfetto::TracingInitArgs args;
  args.backends = perfetto::kInProcessBackend;
  perfetto::Tracing::Initialize(args);
  perfetto::TrackEvent::Register();   // 如需 TrackEvent

  // 注册自定义 DataSource，必须提供 DataSourceDescriptor
  perfetto::DataSourceDescriptor dsd;
  dsd.set_name("com.example.render_pass");
  RenderPassDataSource::Register(dsd);
}

// 业务代码中写 packet
void RecordRenderPass(const char* name, int64_t gpu_ns) {
  RenderPassDataSource::Trace([&](RenderPassDataSource::TraceContext ctx) {
    auto packet = ctx.NewTracePacket();
    // set_render_pass_info() 由 protoc 生成的代码提供
    // 对应 render_pipeline.proto 中的 RenderPassInfo
    auto* event = packet->set_render_pass_info();
    event->set_pass_name(name);
    event->set_gpu_duration_ns(gpu_ns);
  });
}
```

这个骨架只覆盖最小可编译路径，完整项目还需要：proto 文件经 protoc 生成 C++ 头文件并加入构建；`set_render_pass_info()` 依赖 TracePacket proto 扩展注册。Trace Processor 侧查询自定义 packet 需要 `SELECT * FROM raw` 或注册对应的 proto 解析逻辑。

注册时 DataSourceDescriptor 中的 `name` 必须与 TraceConfig 中的 `data_sources.config.name` 一致，否则 Trace 启动时无法激活该数据源。对应的 TraceConfig 启用片段：

```protobuf
# trace_config.proto 片段
buffers {
  size_kb: 65536
}
data_sources {
  config {
    name: "com.example.render_pass"
  }
}
```

对于大多数 App 级打点需求，TrackEvent 已经够用。Custom Data Source 主要面向引擎开发者、系统服务作者、以及需要把 Trace 当结构化数据通道的进阶场景。

### Trace 点设计的几条使用规则

- 名称保持稳定：同一条业务路径不要频繁改 section 名，否则跨版本对比会断。
- 粒度贴着阶段边界放：初始化阶段、解码阶段、一次 Binder 往返，比给每个小函数都打点更容易读。
- 高频循环少打点：每帧、每 item、每像素循环里密集插桩，很快就会把 Trace 噪声抬高。
- 异步路径优先保留 request id：相机、下载、渲染任务跨线程流转时，没有 cookie 很难在 Perfetto 里串起来。

### 生产包中的 Trace 点治理

`android.os.Trace.beginSection()` 的字符串参数会进入 trace 输出和 DEX 文件。在 Release 包中大量使用自定义 trace point 需要注意几个问题：

**体积与语义暴露。** 每个 `beginSection("...")` 调用点会在 DEX 中保留一个字符串常量。高频打点场景下，section name 的字符串总量不容忽视，且可能暴露业务逻辑细节（如 `"PaymentSubmit"`、`"LoginTokenRefresh"`）。

**构建开关策略。** 对于高频或敏感 trace point，推荐通过构建开关或 R8/ProGuard 规则控制：

```proguard
# R8: 在 release 构建中移除自定义 Trace 调用
-assumenosideeffects class android.os.Trace {
  public static void beginSection(java.lang.String);
  public static void endSection();
}
```

`-assumenosideeffects` 让 R8 在 release 构建中判定 `beginSection` / `endSection` 无副作用并移除调用点。需要在 `proguard-rules.pro` 或 `consumer-rules.pro` 中配置，并确认 R8 版本支持该指令（AGP 7.0+ 的 R8 默认支持）。

**保留必要线上诊断点。** 不是所有 trace point 都该被移除。对于线上问题定位的关键锚点（如启动阶段、核心交易路径），保留 trace 调用并确保 section name 稳定且粒度合理。建议团队明确哪些 trace point 是"线上常驻"，哪些是"仅开发期"，并在构建配置中分开管理。

**NDK 侧 `ATrace_*` 的边界。** `ATrace_beginSection` 是平台 tracing API，Perfetto 在 Android 10+ 通过 `traced` 守护进程采集其输出。在 release native 库中保留 `ATrace_*` 调用的开销很低（单次约 50-100ns），但字符串常量同样会进入 .rodata 段。可通过 `#ifdef NDEBUG` 宏控制 release 构建中的 trace 输出。


## Remote Trace Processor 架构

前面提到 `./trace_processor trace.perfetto-trace --httpd` 可以启动本地 Trace Processor 实例让浏览器直连。这里从源码角度展开其内部架构。

### 核心类与目录

`Perfetto Remote Trace Processor`（RTP）在 AOSP `android-17.0.0_r1` 中位于 `external/perfetto/src/trace_processor/rpc/`（不是上游 main 较新版本的 `remote/` 目录；功能等价）。三个传输后端都共用同一个 `Rpc` 类（`rpc.h` / `rpc.cc`），传输无关：

- `stdiod.cc`（stdin/stdout 字节流，Python 客户端和嵌入式场景）
- `httpd.cc`（HTTP+WebSocket+chunked transfer，浏览器 UI 使用）
- `wasm_bridge.cc`（Emscripten 模式，与 `ui.perfetto.dev` 配合）

`Rpc` 类的注释明确写「This class does NOT define how the transport works, it just deals with marshal/unmarshal」——这是 RTP 实现「传输无关」的关键。

### 关键调用链（`--httpd` 模式）

```
trace_processor_shell --httpd
  → trace_processor_shell.cc:953 转 server subcommand
  → shell/server_subcommand.cc:ServerSubcommand::Run
    → 创建 Rpc 实例（持 std::unique_ptr<TraceProcessor>）
    → RunHttpRPCServer(rpc, listen_ip, port, cors_origins)
      → httpd.cc:Httpd::Run 启动 HttpServer，端口 9001
      → httpd.cc:OnHttpRequest 根据 URI 分派：
          /status         → Rpc::GetStatus
          /websocket      → UpgradeToWebsocket
          /rpc            → SetRpcResponseFunction → Rpc::OnRpcRequest
          /parse /notify_eof /restore_initial_tables /query /compute_metric ...
                         → legacy REST 端点（Python 兼容）
```

### 协议要点

- **Wire format**：`TraceProcessorRpcStream` 消息线性序列，每条 `TraceProcessorRpc` 消息前缀是 `[field=1, length-delimited][varint size]`——这与 trace.proto 中 `Trace { repeated TracePacket packet = 1; }` 完全同构。
- **seq 字段**：`optional int64 seq = 1` 用于检测掉包 / 重复。注释明确「Do NOT expect that a response has the same seq of its corresponding request」——一个 query 可能产生多个 batch 响应。
- **seq=0 重置**：浏览器刷新 trace_processor_shell --httpd 时 seq=0 是合法的「重置」（`rpc.cc:201` 短路判断 `req.seq() != 0 && rx_seq_id_ != 0`）。
- **响应 framing**：`(nullptr, 0)` 是 disconnect 信号，由 fatal framing error 触发。

### 17 个 method（去除 reserved 4/12/14）

`TPM_APPEND_TRACE_DATA(1)` / `TPM_FINALIZE_TRACE_DATA(2)` / `TPM_QUERY_STREAMING(3)` / `TPM_COMPUTE_METRIC(5)` / `TPM_GET_METRIC_DESCRIPTORS(6)` / `TPM_RESTORE_INITIAL_TABLES(7)` / `TPM_ENABLE_METATRACE(8)` / `TPM_DISABLE_AND_READ_METATRACE(9)` / `TPM_GET_STATUS(10)` / `TPM_RESET_TRACE_PROCESSOR(11)` / `TPM_REGISTER_SQL_PACKAGE(13)` / `TPM_SUMMARIZE_TRACE(15)` / `TPM_CREATE_SUMMARIZER(16)` / `TPM_UPDATE_SUMMARIZER_SPEC(17)` / `TPM_QUERY_SUMMARIZER(18)` / `TPM_DESTROY_SUMMARIZER(19)`。

`TPM_SUMMARIZER` 系列（16-19）是 v53+ 引入的新方法，Android 17 已包含。

### 零拷贝设计

`Rpc::Response::Send`（`rpc.cc:74-79`）把 `HeapBuffered<TraceProcessorRpcStream>` 的多个 slice 直接 forward 到 `rpc_response_fn_`——避免了「先 SerializeAsArray 到 std::vector 再转发」的一次堆分配与拷贝。`Response` 的 slice 大小是 `kDefaultBatchSplitThreshold + 4096`，默认每个 query response batch ~128 KiB + 4 KiB 余量。

### 实际用法（场景化）

**场景 1：用 --httpd 让浏览器 UI 加速**

```bash
./trace_processor trace.perfetto-trace --httpd
# 默认监听 127.0.0.1:9001，CORS 已放行 ui.perfetto.dev
# 打开 https://ui.perfetto.dev/，会弹出「Trace Processor native acceleration」确认
```

**场景 2：用 --stdiod 嵌入到 CI 流水线**

```bash
./trace_processor --stdiod trace.perfetto-trace
# 通过 STDIN/STDOUT 走裸字节流协议，Python perfetto.TraceProcessor 可直接对接
# 单线程 reactive 循环，4 KiB 读循环，STDIN EOF 正常退出
```

**场景 3：HTTP /rpc 端点直接打裸 RPC（Python 替代路径）**

```python
import requests
r = requests.post(
    "http://localhost:9001/rpc",
    data=rpc_bytes,
    stream=True,
    headers={"Content-Type": "application/x-protobuf",
             "Transfer-Encoding": "chunked"})
# 响应是 chunked transfer：每个 chunk "hex_len\r\nbody\r\n"
# 解析后是 TraceProcessorRpcStream 字节流
```

> 引用：`external/perfetto/src/trace_processor/rpc/rpc.cc:114-126`（`OnRpcRequest`）、`rpc.cc:152-300`（`ParseRpcRequest`）、`httpd.cc:130-265`（`OnHttpRequest`）、`server_subcommand.cc:Run`（subcommand 入口）。
> 完整调研：`/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-20-perfetto-remote-trace-processor-architecture.md`


## 参考资料

### Perfetto SPAN_JOIN 与窗口函数交叉分析
Perfetto Trace Processor 的 SPAN_JOIN 自定义算子表在 C++ 层实现时间跨度交集，支持 PARTITIONED 分区键避免 O(n×m) 全量比较。配合 SPAN_LEFT_JOIN / SPAN_OUTER_JOIN 变体，以及窗口函数 LEAD() 在 counter→span 视图转换中的核心用法，可以构建帧×GC、Binder、锁等交叉分析。详见 DeepResearch 调研：`DeepResearch/2026-05-13-perfetto-span-join-window-function.md`。


### Perfetto v52/v54 大改版：Dark Mode + ANR 分类 + 位图时序
- 来源：https://github.com/google/perfetto/releases
- 类型：article
- 摘要：UI层：Dark Mode、触摸支持、多Track批量操作。分析层：android_anrs新增anr_type字段、android.bitmaps位图时序数据、slice_self_dur自持续时间计算、regexp_extract函数、JSON trace解析性能提升。
- 入库时间：2026-04-08

### AndroidX Tracing 2.0 架构
AndroidX Tracing 2.0（alpha05）引入了 Tracer、TraceDriver、TraceSink 新对象模型，支持协程上下文传播和纯 Kotlin Perfetto TracePacket 发射路径。详见 DeepResearch 调研：`DeepResearch/AndroidX Tracing 2.0 架构级深度技术分析.md`。

