---
title: Perfetto 指标自动化与分析平台
chapter: '13.4'
section: '13.4'
applicable_versions: Android 8.0 (API 26) - Android 17 (API 37)
last_verified: '2026-08-13'
last_verified_against: Android 17 / API 37 / android-17.0.0_r1 (Perfetto ece66975738007dd0978b911d8a2077e49b8f31e); Perfetto Trace Processor v57.2-da1d152cf; android17-6.18-2026-06_r6; perfetto.dev (2026-08-13)
confidence: medium
sources:
- type: official
  path: https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/
- type: official
  path: https://android.googlesource.com/platform/system/core/+/android-17.0.0_r1/libcutils/include/cutils/trace.h
- type: official
  path: https://perfetto.dev/docs/analysis/trace-summary
- type: official
  path: https://perfetto.dev/docs/analysis/metrics
- type: official
  path: https://perfetto.dev/docs/analysis/trace-processor-python
- type: official
  path: https://perfetto.dev/docs/analysis/batch-trace-processor
- type: official
  path: https://perfetto.dev/docs/visualization/ui-automation
- type: official
  path: https://perfetto.dev/docs/visualization/commands-automation-reference
- type: official
  path: https://perfetto.dev/docs/visualization/extension-servers
- type: official
  path: https://perfetto.dev/docs/instrumentation/tracing-sdk
- type: official
  path: https://perfetto.dev/docs/getting-started/atrace
- type: official
  path: https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci
- type: official
  path: https://developer.android.com/topic/performance/measuring-performance
- type: blog
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/技术文章/RSS/rss-tech/2026-05-18_RSS_886623bf54.md
- type: github
  path: https://github.com/Gracker/SmartPerfetto
- type: internal
  path: src/part3-tools/ch13-perfetto/09-perfetto-sql-cookbook.md
- type: internal
  path: src/part3-tools/ch13-perfetto/15-agent-perfetto-analysis-protocol.md
- type: internal
  path: src/part3-tools/ch13-perfetto/16-perfetto-sdk-in-app-tracing.md
- type: internal
  path: src/part5-app/ch26-observability/03-performance-collection.md
- type: internal
  path: src/part5-app/ch26-observability/06-ab-testing-regression.md
tags:
- android
- perfetto
- research
- smartperfetto
- trace-analysis
- ai-assistant
- sql-guardrail
- observability
status: finalized
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
task2b_state: fixed
related_chapters:
- '13.2'
- '13.7'
- '13.11'
- '13.12'
- '26.1'
- '26.4'
- '26.6'
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part3-tools/ch13-perfetto/06-advanced-usage.md
- src/part3-tools/ch13-perfetto/17-smartperfetto-trace-analysis-platform.md
---

# Perfetto 指标自动化与分析平台

单份系统 Trace 可以支持一次诊断；可复用查询、结构化指标、批量分析、持续集成和应用埋点还要解决跨人员、跨构建、跨日期的一致性。同一条分析规则应始终产出语义一致的结果，并在异常发生时保留足够的原始证据。

本文核对的平台源码基线是 Android 17 / API 37 / `android-17.0.0_r1`。该标签的 `external/perfetto` 指向提交 `ece66975738007dd0978b911d8a2077e49b8f31e`；调度与 ftrace（Linux 内核跟踪机制）的采集行为以 `android17-6.18-2026-06_r6` 为边界。主机上的 Perfetto UI、Python 包和 Trace Processor 可以独立升级，因此流水线还要固定主机工具版本，不能只记录设备系统版本。

自动化分析把 Trace Processor SQL、metric 和设备批处理组合成可复查流程。平台价值取决于查询版本、输入质量、结果证据和回归基线，而不是只生成一个分数。

## SQL Metric、批处理与回归比较

### 四种可复用能力

Perfetto 提供了几套名称相近、用途不同的机制。选错层次后，查询可能能运行，却很难长期维护。

| 机制 | 输入 | 输出 | 适用位置 |
|---|---|---|---|
| PerfettoSQL 标准库 | `INCLUDE PERFETTO MODULE` | 稳定表、视图和函数 | 单份 Trace 查询的公共语义层 |
| Trace Summarization | 指标规格 + 标准库或 SQL | 统一的 `TraceSummary` protobuf | 新建自动化指标和跨 Trace 分析 |
| 旧版 v1 指标 | SQL + 自定义 protobuf | `TraceMetrics` protobuf | 维护已有指标，或兼容现有读取服务 |
| UI 命令宏 | JSON 命令序列 | 工作区、查询页、调试轨道等界面状态 | 重复执行人工诊断步骤 |

protobuf（Protocol Buffers）是带字段类型的结构化消息格式。自动化分析中的“输出契约”指字段名、类型、单位和含义都可被读取端稳定依赖，不只表示文件采用二进制编码。

PerfettoSQL 还定义了 `CREATE PERFETTO MACRO`，用于在查询执行前展开表达式或子查询。它与 UI 设置里的命令宏没有共享配置，执行方式也不同。

### 自定义指标：新项目从 Trace Summarization 开始

#### 为何不再把 v1 指标当作默认方案

Android 17 标签和 v57.2 命令帮助都把 v1 指标标为软弃用（soft deprecated）：已有指标与命令行兼容接口继续工作，但官方不再为这套体系增加新功能或新指标。新项目应使用 Trace Summarization。两者的 SQL 能力接近，输出契约差异很大。

v1 指标要求每个团队维护独立的输出 protobuf。Trace Summarization 使用统一的 `TraceSummary`，并在规格中声明维度、数值列、单位和极性：维度是进程名、场景等分组字段，极性说明数值升高或降低哪一侧更好。统一结构更适合批量处理、仪表板和长期性能回退追踪。

一个可维护的选择顺序如下：

1. 在标准库中查找已有模块，确认表的语义和版本边界。
2. 用 Trace Summarization 描述新指标。
3. 标准库存在缺口时，在仓库内增加自定义 PerfettoSQL 包。
4. 只有现有读取端依赖 `TraceMetrics` 时，才增加或修改 v1 指标。

#### Trace Summarization 的完整示例

下面的规格按进程计算 `RSS + Swap` 的持续时间加权均值。RSS（Resident Set Size）是进程当前驻留在物理内存中的页面量，Swap 是换出到交换区的页面量。规格使用可读文本形式的 protobuf（textproto），直接引用官方 `linux.memory.process` 模块，并声明字节单位。

```textproto
metric_spec {
  id: "memory_per_process"
  dimensions: "process_name"
  value: "avg_rss_and_swap"
  unit: BYTES
  query {
    table {
      table_name: "memory_rss_and_swap_per_process"
    }
    referenced_modules: "linux.memory.process"
    group_by {
      column_names: "process_name"
      aggregates {
        column_name: "rss_and_swap"
        op: DURATION_WEIGHTED_MEAN
        result_column_name: "avg_rss_and_swap"
      }
    }
  }
}
```

`DURATION_WEIGHTED_MEAN` 按每个样本覆盖的时间长度加权，适合由计数器样本还原出的区间数据。例如一个值保持 9 秒、另一个值只保持 1 秒时，前者应获得九倍权重；普通算术平均会忽略这项差异。

可以用 Android 17 标签已经支持的子命令接口执行这份规格：

```bash
trace_processor summarize \
  --metrics-v2 memory_per_process \
  trace.perfetto-trace \
  spec.textproto
```

输出是 `TraceSummary`，结果位于 `metric_bundles`；每个 bundle（结果包）可以保存一组共享维度结构的指标。`--format binary` 可生成二进制 protobuf，默认 textproto 更适合人工检查。v57.2 仍完整支持旧式 `--summary` 参数，新脚本应采用子命令接口并固定二进制版本。

同一份规格也能从 Python 调用：

```python
from pathlib import Path
from perfetto.trace_processor import TraceProcessor

spec_text = Path("spec.textproto").read_text(encoding="utf-8")

with TraceProcessor(trace="trace.perfetto-trace") as tp:
    summary = tp.trace_summary(
        specs=[spec_text],
        metric_ids=["memory_per_process"],
    )
    print(summary)
```

`metric_ids` 只选择本次需要的指标 ID。省略该参数时，API 可以执行规格中的全部指标；大型规格库更适合显式选择，避免一次运行引入无关查询。

#### 存量 v1 指标：SQL 与 protobuf 的约定

团队如果已有读取 `TraceMetrics` 的服务，v1 指标仍可维护。下面使用 CPU 运行时间展示完整目录和命名约定，避免依赖不稳定的 `activityStart`、`FirstFrame` 等时间片名称。

存量指标可以把两个同名文件放进同一目录：

```text
legacy_metric/
├── top_five_processes.proto
└── top_five_processes.sql
```

Trace Processor 根据传入的 SQL 路径查找同目录、同基本名的 protobuf 文件，再把自定义消息注册为 `TraceMetrics` 的扩展字段。扩展字段是在既有根消息上增加团队自定义结果的 protobuf 机制；这条路径不需要覆盖内置指标。

输出 protobuf 定义如下：

```protobuf
syntax = "proto2";

package perfetto.protos;

import "protos/perfetto/metrics/metrics.proto";

message ProcessCpuInfo {
  optional string process_name = 1;
  optional int64 cpu_time_ms = 2;
  optional uint32 scheduled_thread_count = 3;
}

message TopFiveProcesses {
  repeated ProcessCpuInfo process = 1;
}

extend TraceMetrics {
  optional TopFiveProcesses top_five_processes = 450;
}
```

字段号 `450` 来自 Perfetto 为本地开发保留的 `450–500` 区间。字段号是 protobuf 在线路格式中识别字段的数字，重复会造成定义冲突，因此团队内部仍要登记。扩展字段名 `top_five_processes` 还决定 SQL 文件名和输出视图名。

对应 SQL 统计 `sched` 中已经运行完的调度时间片：

```sql
CREATE PERFETTO VIEW top_five_processes_by_cpu AS
SELECT
  p.name AS process_name,
  CAST(SUM(s.dur) / 1e6 AS INT64) AS cpu_time_ms,
  COUNT(DISTINCT t.utid) AS scheduled_thread_count
FROM sched AS s
JOIN thread AS t USING (utid)
JOIN process AS p USING (upid)
WHERE s.dur > 0
GROUP BY p.upid, p.name
ORDER BY cpu_time_ms DESC
LIMIT 5;

CREATE PERFETTO VIEW top_five_processes_output AS
SELECT TopFiveProcesses(
  'process',
  (
    SELECT RepeatedField(
      ProcessCpuInfo(
        'process_name', process_name,
        'cpu_time_ms', cpu_time_ms,
        'scheduled_thread_count', scheduled_thread_count
      )
    )
    FROM top_five_processes_by_cpu
  )
);
```

`upid` 是 Perfetto 在当前 Trace 内分配的进程唯一标识。按 `upid` 分组可以避开操作系统进程号（PID）复用和同名进程合并。`scheduled_thread_count` 只统计 Trace 中出现过已完成 `sched` 时间片的线程，不代表进程创建过的全部线程。`top_five_processes_output` 必须采用 `{TraceMetrics 扩展字段名}_output`，Trace Processor 通过这个命名约定读取根消息。

Android 17 标签支持两套等价命令。新子命令写法更容易发现参数：

```bash
trace_processor metrics \
  --run legacy_metric/top_five_processes.sql \
  --output json \
  trace.perfetto-trace
```

旧脚本使用的 `--run-metrics legacy_metric/top_five_processes.sql` 与 `--metrics-output=json` 仍受兼容接口支持。`--metric-extension DISK_PATH@VIRTUAL_PATH` 把磁盘目录映射到 Trace Processor 内部的指标路径；把扩展挂到虚拟根路径 `/` 并覆盖内置指标时，工具要求同时传入 `--dev`。`--dev` 会开启可能随时变化的本地开发功能，不应成为生产流水线默认项。升级主机工具时，应在固定测试 Trace 上对比新旧输出，再更新锁定版本。

#### 指标失败时先检查采集条件

SQL 返回空表不等于性能为零。常见原因包括：

- 采集配置没有启用指标所依赖的数据源；
- 轨迹在目标事件发生前结束；
- 目标进程未被 `atrace_apps` 允许；
- 工具版本缺少规格引用的标准库模块；
- 数据质量表已经记录丢包、截断或时钟问题；
- 进程名、包名或启动模式与查询条件不一致。

每个指标规格应同时记录依赖的数据源、支持的系统版本、单位、方向、空值含义和已知失效边界。CI（Continuous Integration，持续集成）不能把空结果自动转成数值零：空值表示没有足够证据，零表示证据完整且测得数值为零。

### 两类宏：SQL 复用与 UI 自动化

#### PerfettoSQL 宏

SQL 宏适合生成表、子查询或表达式片段。普通函数能够完成的标量计算应继续使用函数；宏更适合把表名或列名作为参数的场景。

下面的宏从任意兼容表中选出超过指定时长的时间片：

```sql
CREATE PERFETTO MACRO long_slices(
  input TableOrSubquery,
  min_dur Expr
)
RETURNS TableOrSubquery AS
(
  SELECT ts, dur, name, track_id
  FROM $input
  WHERE dur >= $min_dur
);

SELECT ts, dur, name
FROM long_slices!(slice, 8 * 1000 * 1000)
ORDER BY dur DESC
LIMIT 20;
```

`TableOrSubquery` 和 `Expr` 是宏参数类型，分别表示表或子查询、普通 SQL 表达式。宏调用以 `!` 结尾，参数会在查询真正执行前展开。查询中的 8 ms 只是筛选条件示例，不是“卡顿”的通用判定线；帧是否超期要比较该帧自己的显示期限。

供多人使用的 SQL 不宜只存在于某个查询页。可以把相关模块组织成自定义 SQL 包，并用 `TraceProcessorConfig.add_sql_packages` 或命令行 `--add-sql-package` 注册。包名相当于模块命名空间，用来避免团队模块与标准库或其他团队重名；包名、查询接口和测试 Trace 都应纳入版本控制。

#### UI 命令宏

Perfetto UI 的宏是命名后的稳定命令序列。当前配置入口为 `Settings > Macros`，格式是 JSON 数组。宏由工程师从命令面板执行，也可以被启动命令引用。

下面的宏折叠现有轨道、固定 CPU 轨道，再为所有进程主线程中超过 8 ms 的时间片增加分组调试轨道：

```json
[
  {
    "id": "user.myteam.LongMainThreadSlices",
    "name": "Long Main-thread Slices",
    "run": [
      {
        "id": "dev.perfetto.CollapseTracksByRegex",
        "args": [".*"]
      },
      {
        "id": "dev.perfetto.PinTracksByRegex",
        "args": [".*CPU \\d+$"]
      },
      {
        "id": "dev.perfetto.AddDebugSliceTrackWithPivot",
        "args": [
          "SELECT s.ts, s.dur, s.name, COALESCE(p.name, '[unnamed]') AS process_name FROM slice AS s JOIN thread_track AS tt ON s.track_id = tt.id JOIN thread AS t USING (utid) JOIN process AS p USING (upid) WHERE t.tid = p.pid AND s.dur >= 8000000",
          "process_name",
          "Long main-thread slices"
        ]
      }
    ]
  }
]
```

`AddDebugSliceTrackWithPivot` 要求查询返回 `ts`、`dur`、`name` 和分组列。Pivot 表示按某列的不同取值拆成多条调试轨道；示例用 `process_name` 按进程分组。命令失败不会终止宏中后续命令，因此共享前要用团队的代表性 Trace 检查每一步。命令 ID 还要出现在 Perfetto 的稳定自动化参考中，避免依赖插件私有命令。

宏可以保存在本地设置中。个人使用时，把 JSON 存入仓库并提供安装说明即可；固定录制流程还可以用 `record_android_trace --ui-startup-commands`、带参数的深链接或浏览器窗口消息接口 `postMessage` 注入允许的启动命令。

多人共享更适合使用 Perfetto 扩展服务器。当前接口能分发宏、SQL 模块和 protobuf descriptor（描述字段结构的类型信息），既支持 GitHub 仓库，也支持带认证的 HTTPS 端点。服务器要声明反向域名命名空间，例如 `com.example.perfetto`；宏 ID 和 SQL 模块名必须以该命名空间开头，避免不同服务器重名。扩展加载失败不会阻止 UI 打开 Trace，因此团队仍要把服务端清单、源码和已发布版本纳入版本控制，分析结果不能依赖未固定提交的活动分支。

#### “仪表板”要分成单轨迹和跨轨迹两层

Perfetto UI 擅长对一份轨迹做交互诊断。工作区、查询页和调试轨道可以组成单轨迹仪表板，但它们不会自动保存跨构建趋势。

跨 Trace 仪表板应读取 Trace Summarization 或 Benchmark JSON。后者是 AndroidX Benchmark 输出的结构化测量报告：

| 层次 | 保存内容 | 回答的问题 |
|---|---|---|
| Perfetto UI | 宏、工作区、调试轨道、查询页 | 这次慢在哪里 |
| 指标文件 | `TraceSummary`、Benchmark JSON、工具版本 | 这次测到了什么 |
| 时序存储 | 按时间保存构建、设备、场景、样本与指标 | 何时开始变化 |
| 可视化与告警 | 分位数、基线区间、Trace 链接 | 是否需要人工复核 |

分位数表示样本在排序后所处的位置，例如 P50 是中位数。趋势图上的每个异常点都应能跳回原始 Trace、构建信息和指标规格版本；只保存均值、分位数等聚合值会丢失根因证据。

### Trace Processor Python API

#### 固定二进制，记录包与工具的每次变化

`pip` 是 Python 包安装工具，`pip install perfetto` 会安装 Perfetto Python 客户端。客户端可以下载与包版本匹配的 Trace Processor，也允许显式指定二进制。CI 更适合固定 Python 依赖和二进制摘要；摘要是用于确认文件内容未变的哈希值，应与版本一起写入报告。

下面的示例使用指定二进制查询最长的用户态时间片：

```python
from perfetto.trace_processor import TraceProcessor, TraceProcessorConfig

config = TraceProcessorConfig(
    bin_path="tools/perfetto/trace_processor",
)

with TraceProcessor(
    trace="trace.perfetto-trace",
    config=config,
) as tp:
    rows = tp.query("""
        SELECT ts, dur, name
        FROM slice
        WHERE dur > 0
        ORDER BY dur DESC
        LIMIT 20
    """)
    frame = rows.as_pandas_dataframe()
    print(frame.to_string(index=False))
```

`with` 上下文管理器会在代码块结束时关闭 Trace Processor 子进程。`as_pandas_dataframe()` 把结果复制成 Pandas DataFrame（带列名的内存表格），适合后续统计；只需逐行处理少量结果时，直接遍历查询结果能少保留一份表格数据。

#### 批量查询

`BatchTraceProcessor` 为每份 Trace 启动独立实例，并行执行同一查询。`query()` 返回每份 Trace 各自的数据表；`query_and_flatten()` 把这些表纵向合并，并由 Trace 地址 resolver（把 URI 或路径解析成数据来源的组件）增加来源列。

下面的代码统计每份轨迹中的用户态时间片数量和总时长：

```python
from glob import glob
from perfetto.batch_trace_processor.api import BatchTraceProcessor

trace_paths = sorted(glob("traces/*.perfetto-trace"))

with BatchTraceProcessor(trace_paths) as batch:
    summary = batch.query_and_flatten("""
        SELECT
          COUNT(*) AS slice_count,
          SUM(CASE WHEN dur > 0 THEN dur ELSE 0 END) AS total_slice_dur_ns
        FROM slice
    """)
    print(summary)
```

来源列的名称取决于所用 Trace 地址 resolver，读取结果的代码不应假定固定叫 `source`。每份 Trace 解析后的数据都驻留内存；并发数要按 Trace 内容和机器内存实测，不能只按压缩文件大小估算。官方文档给出的 `2 × 平均文件大小 × Trace 数量` 只能用于粗略起步，数据类型和压缩率会让实际占用明显偏离。

批量规模超过单机资源后，可评估 Bigtrace。它是分布式 Trace Processor 服务，使用 Kubernetes（容器集群编排系统）调度多个工作进程，适合已经具备对象存储和集群运维能力的团队。单纯为了几十份 Trace 引入 Bigtrace，运维成本通常高于收益。

#### 远程 Trace Processor 的支持边界

Android 17 标签和 v57.2 已提供新的服务子命令。下面的命令在本机 9001 端口启动原生 Trace Processor，并开放 RPC（Remote Procedure Call，远程过程调用）接口供 Perfetto UI 探测：

```bash
trace_processor server http trace.perfetto-trace
```

旧写法 `trace_processor --httpd trace.perfetto-trace` 在 v57.2 中仍完整支持。原生进程绕开浏览器 WebAssembly（浏览器内的沙箱二进制执行环境）的内存限制，但 Trace 解析后的内存仍可能显著大于文件大小。

`external/perfetto/src/trace_processor/rpc/` 中的 `Rpc` 负责 protobuf 编解码，HTTP、标准输入输出（stdio）和 WebAssembly 桥接负责传输。Python 客户端已经封装协议协商（确认双方支持的 RPC 版本和能力）、分批响应和错误处理。业务脚本应调用 Python API 或命令行接口，不应手写 `/rpc` 请求、分块传输和序列号管理。

服务应只监听回环地址，即仅本机可访问的 `127.0.0.1` 或 `::1`。Trace 可能包含进程名、文件路径、埋点文本和业务标识，不应把 9001 端口直接暴露到共享网络。UI 和服务器版本相差过大时还可能出现 RPC 版本不匹配，升级时要成套验证。

### 把 Perfetto 放进持续集成

#### 测量值和诊断证据各司其职

AndroidX Macrobenchmark 是在 Android 设备上重复执行启动、滚动等场景的基准测试库。它会输出 Benchmark JSON，并为每次测量保存一份 Perfetto Trace。持续集成中的门禁是根据测量结果自动决定构建是否允许继续；可以分两层处理：

- Benchmark JSON 作为门禁的主要数值来源；
- Perfetto SQL 或 Trace Summarization 生成诊断指标，并保留异常样本的原始轨迹。

不宜从某个可能变化的 Slice 名称重新计算启动时间，再与 Macrobenchmark 的 `StartupTimingMetric` 混为同一个指标。系统升级或埋点名称变化后，两套定义可能产生不易察觉的偏差。

#### 可复现的流水线

一条可靠的流水线至少记录这些信息：

1. 目标 APK（被测应用安装包）、测试 APK、提交和构建参数；
2. 真机序列号、机型、系统指纹（精确标识系统构建的 build fingerprint）、API 级别和电量；
3. 启动模式、编译模式（例如无预编译、部分预编译或完整预编译）、场景参数和迭代次数；
4. Benchmark JSON、每次迭代的轨迹和测试日志；
5. Perfetto Python 包、Trace Processor 二进制版本与摘要；
6. 指标规格、SQL 包和门禁策略的版本。

官方文档不建议用模拟器数值代表用户设备。固定真机适合代码合并前的自动门禁；共享设备池更适合趋势观察和夜间复测。低电量、可调试 APK、未配置为 profileable（允许性能分析）的 APK 等 Macrobenchmark 配置错误不应被统一忽略，否则不同运行可能处于不同测量条件。

按官方示例模块名，本地连接真机时可以这样运行整组基准：

```bash
./gradlew :macrobenchmark:connectedCheck
```

Gradle（Android 项目常用的构建系统）会把 Benchmark JSON 和每次迭代的 `.perfetto-trace` 复制到 `build/outputs/connected_android_test_additional_output/` 下；当前插件还会按测试变体、连接方式和设备继续分子目录，例如 `debugAndroidTest/connected/<device>/`。收集脚本应递归发现报告，不能假定文件直接位于父目录。设备农场通常把构建、安装、运行和拉取测试文件拆成独立阶段，指标含义不应随执行平台变化。

#### 门禁阈值来自设备噪声，不来自通用百分比

“变慢 10%”或“p 值小于 0.05”都不能直接套用到所有场景。p 值来自假设检验，只有结合实验设计、样本数和预先选择的检验方法才有意义。团队应在固定设备和固定构建条件下反复运行未改代码，测出设备与场景自身的自然波动，再为每个场景制定阈值和复测策略。

下面的脚本读取 Macrobenchmark 官方 JSON 结构，检查当前报告和基线是否来自同一系统指纹，再比较指定指标的中位数。基线是用于比较的已批准历史结果，中位数是样本排序后的中间值。阈值由调用者从版本库中的场景策略传入。

```python
#!/usr/bin/env python3
import argparse
import json
import statistics
import sys
from pathlib import Path


def load_report(path, benchmark_name, metric_name):
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    matches = [
        item for item in report["benchmarks"]
        if item["name"] == benchmark_name
    ]
    if len(matches) != 1:
        raise ValueError(
            f"{path}: expected one benchmark named {benchmark_name!r}, "
            f"found {len(matches)}"
        )

    metric = matches[0]["metrics"][metric_name]
    runs = [float(value) for value in metric["runs"]]
    if not runs:
        raise ValueError(f"{path}: metric {metric_name!r} has no samples")
    return report["context"], runs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--metric", required=True)
    parser.add_argument("--max-regression-ratio", required=True, type=float)
    args = parser.parse_args()

    current_context, current_runs = load_report(
        args.current, args.benchmark, args.metric
    )
    baseline_context, baseline_runs = load_report(
        args.baseline, args.benchmark, args.metric
    )

    current_build = current_context["build"]
    baseline_build = baseline_context["build"]
    for key in ("model", "fingerprint"):
        if current_build[key] != baseline_build[key]:
            raise ValueError(f"environment mismatch: build.{key}")

    current_median = statistics.median(current_runs)
    baseline_median = statistics.median(baseline_runs)
    ratio = current_median / baseline_median - 1.0

    print(
        json.dumps(
            {
                "benchmark": args.benchmark,
                "metric": args.metric,
                "current_median": current_median,
                "baseline_median": baseline_median,
                "regression_ratio": ratio,
                "current_sample_count": len(current_runs),
                "baseline_sample_count": len(baseline_runs),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2 if ratio > args.max_regression_ratio else 0


if __name__ == "__main__":
    sys.exit(main())
```

脚本不内置百分比，只拒绝完全没有样本的报告，没有检查业务要求的最小样本数。比值计算只适用于“数值越低越好”且基线中位数大于零的指标；基线为零、可能为负或方向相反的指标要改用对应规则。正式流水线还应校验场景参数、编译模式和样本数；首次超过阈值后在同一设备复测，并把两轮报告与 Trace 一起交给评审。

#### 轨迹诊断不能反向污染测量

增加 ftrace 事件、堆采样或密集应用埋点会改变被测程序和系统的采集开销。门禁配置和深度诊断配置可以分开：

- 常规门禁只采 Macrobenchmark 所需数据；
- 超过阈值后用同一提交复测并启用更详细的数据源；
- 诊断结果用于定位，不拿来替换原门禁样本；
- 每次采集配置变更都建立新基线，避免把工具开销变化记成产品性能变化。

这样可以控制日常测量开销，也能在异常发生后获得调度、Binder、内存或渲染证据。

### 自定义 Trace Point（埋点）

#### 选择平台 API 还是 Perfetto SDK

这里的 Trace Point 指代码主动写入 Trace 的应用或平台埋点，与 Linux 内核预定义的 Tracepoint 分属不同机制。同步时间片描述同一线程上有明确起止的工作，异步时间片可跨线程或跨回调配对，计数器记录随时间变化的数值。Android 应用只需要这三类事件时，平台 Trace 或 NDK（Native Development Kit，C/C++ 开发工具包）的 `ATrace_*` 已经足够；Perfetto SDK 更适合 C++ 引擎、跨平台程序、分类过滤、流事件或强类型扩展。

| 接口 | 可用边界 | 适合场景 |
|---|---|---|
| `Trace.beginSection/endSection` | API 18+ | Java/Kotlin 同线程嵌套阶段 |
| `ATrace_beginSection/endSection` | NDK API 23+ | C/C++ 同线程嵌套阶段 |
| `Trace.beginAsyncSection/endAsyncSection` | API 29+ | Java/Kotlin 跨线程阶段 |
| `ATrace_beginAsyncSection/endAsyncSection` | NDK API 29+ | C/C++ 跨线程阶段 |
| `Trace.setCounter` / `ATrace_setCounter` | API 29+ | 随时间变化的数值 |
| Perfetto SDK `TRACE_EVENT` | C++17 SDK | 分类、流、计数器和扩展字段 |

#### Java/Kotlin 同步时间片

同步时间片必须在同一线程成对结束。下面的包装能在异常路径上保持平衡：

```kotlin
inline fun <T> tracedSection(name: String, block: () -> T): T {
    android.os.Trace.beginSection(name)
    return try {
        block()
    } finally {
        android.os.Trace.endSection()
    }
}

val bitmap = tracedSection("ImageDecode") {
    decodeImage(bytes)
}
```

Android 17 的 `Trace.java` 将名称限制为 127 个 UTF-16 代码单元；普通汉字通常占一个，部分 emoji 等字符会占两个。超长名称会抛出 `IllegalArgumentException`，`|`、换行和空字符则会在底层被替换为空格。名称应保持短、稳定且不含用户数据。

跨线程任务要使用相同名称和 cookie 配对：

```kotlin
fun startCapture(requestId: Int) {
    android.os.Trace.beginAsyncSection("CameraCapture", requestId)
}

fun finishCapture(requestId: Int) {
    android.os.Trace.endAsyncSection("CameraCapture", requestId)
}

fun updateQueueDepth(depth: Int) {
    android.os.Trace.setCounter("DecodeQueueDepth", depth.toLong())
}
```

cookie 是异步区间的整数关联 ID。时间上重叠的同名异步事件必须使用不同 cookie，结束事件再用同一名称与 cookie 找回对应起点。cookie 只负责配对，不应承载账号、文件名或其他敏感信息。

#### NDK `ATrace_*`

Native（C/C++）同步阶段的写法与 Java 层语义一致：

```cpp
#include <android/trace.h>

void DecodeFrame(const EncodedFrame& frame) {
  ATrace_beginSection("ImageDecode");
  Decode(frame);
  ATrace_endSection();
}
```

C++ 代码如果可能抛异常或提前返回，应再封装 RAII（Resource Acquisition Is Initialization，利用对象析构自动清理）守卫，确保 `ATrace_endSection()` 总能执行。异步 NDK API 从 API 29 起使用相同名称和 cookie 配对。

Android 平台、系统服务和 HAL（Hardware Abstraction Layer，硬件抽象层）还会使用 `libcutils` 的小写 `atrace_begin()`，它允许显式选择 `ATRACE_TAG_*`。下面的代码把显示配置阶段放到 graphics 分类中：

```cpp
#include <cutils/trace.h>

void ConfigureDisplay(Display& display) {
  atrace_begin(ATRACE_TAG_GRAPHICS, "ConfigureDisplay");
  display.ApplyPendingConfiguration();
  atrace_end(ATRACE_TAG_GRAPHICS);
}
```

Android 17 的 `libcutils/include/cutils/trace.h` 还提供 `ATRACE_BEGIN` / `ATRACE_END` 宏，宏使用编译单元定义的 `ATRACE_TAG`。这套接口属于平台私有 API，普通应用应使用 SDK `Trace` 或 NDK `ATrace_*`，不能把 `libcutils` 头文件当作稳定 NDK 接口。

应用 Trace Point 只有被采集配置允许时才会出现在系统 Trace 中。下面的 Android Perfetto 配置通过 `atrace_apps` 包名允许列表，启用目标应用的 `TRACE_TAG_APP` 分类事件：

```textproto
buffers {
  size_kb: 32768
  fill_policy: RING_BUFFER
}

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      atrace_apps: "com.example.app"
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_waking"
    }
  }
}
```

`RING_BUFFER` 表示缓冲区满后覆盖最早的数据。`atrace_apps` 可以填写具体包名；`*` 会扩大到所有应用的 ATrace 事件，既增加数据量，也扩大隐私暴露，不适合作为默认团队配置。调度事件来自内核侧，本文统一使用 `android17-6.18-2026-06_r6` 作为内核版本基线。

#### Native Perfetto SDK

如果系统 Trace 要把应用事件与调度、ftrace 等数据放在同一时间轴，应使用 system backend（系统后端）。下面是 TrackEvent 的最小初始化与同步时间片：

```cpp
#include <perfetto.h>

PERFETTO_DEFINE_CATEGORIES(
    perfetto::Category("rendering"),
    perfetto::Category("camera"));
PERFETTO_TRACK_EVENT_STATIC_STORAGE();

void InitTracing() {
  perfetto::TracingInitArgs args;
  args.backends |= perfetto::kSystemBackend;
  perfetto::Tracing::Initialize(args);
  perfetto::TrackEvent::Register();
}

void RenderFrame() {
  TRACE_EVENT("rendering", "RenderFrame");
  SubmitRenderWork();
}
```

`kSystemBackend` 连接系统中的 Perfetto 追踪服务 `traced`，采集会话由外部 Perfetto 客户端控制。该模式适合能控制设备和部署的本地调试或实验室环境。`kInProcessBackend`（进程内后端）只生成当前进程自己的 Trace，不会自行带上系统调度数据；两种后端可以同时注册，但采集权限和输出读取规则不同。

TrackEvent 已支持时间片、计数器、Flow（事件之间的因果连线）和调试注解（附加的键值信息）。Android 17 所带 Perfetto 还支持 TrackEvent protobuf descriptor；需要强类型业务字段时，可以把字段类型描述嵌入 Trace，让 Trace Processor 自动把数据解码到 `args` 表。

自定义 `perfetto::DataSource<T>` 的门槛更高。它能写自定义数据包，但 Trace Processor 也要具备对应导入逻辑。业务工程不能只定义一个独立 `.proto`，再假设代码生成器产生的 setter（字段写入方法）会自动进入上游 `TracePacket`；`TracePacket` 是 Perfetto Trace 的顶层数据包容器。缺少平台 protobuf 扩展、descriptor 或自定义导入器时，这类代码无法形成可查询的结构化数据。

#### 生产包治理

Trace 点的设计质量会直接影响轨迹可读性和线上信息暴露：

- 用稳定阶段名，动态标识放在 cookie、计数器或受控字段中；
- 同步区间严格嵌套，异步区间严格配对；
- 不写账号、URL 参数、文件路径、令牌或用户输入；
- 不在每个元素、每个像素或极短循环中密集埋点；
- 字符串需要格式化时先检查 `Trace.isEnabled()`，确认当前是否启用追踪，减少未采集状态下仍创建临时字符串对象；
- 对埋点开销做目标设备实测，不能沿用其他设备的纳秒级估算。

Android 性能文档给出的经验值约为每个区间 5 微秒，并建议优先标记大于 0.1 ms 的工作。这是选择粒度的参考值，具体开销仍受设备、系统和采集配置影响。

不要用全局 `-assumenosideeffects class android.os.Trace` 规则清除发布包中的平台 Trace 调用。这条 R8（Android 字节码优化与压缩工具）规则会假定方法没有副作用并删除调用，影响应用和依赖库的所有调用点，也会让诊断能力随构建配置变化。更可控的方案是只包装团队自己的可选埋点：

```kotlin
object AppTrace {
    inline fun <T> section(name: String, block: () -> T): T {
        if (!BuildConfig.ENABLE_APP_TRACE) {
            return block()
        }
        android.os.Trace.beginSection(name)
        return try {
            block()
        } finally {
            android.os.Trace.endSection()
        }
    }
}
```

把 `ENABLE_APP_TRACE` 设为构建期常量后，R8 可以移除不可达的 Trace 调用分支。发布前仍要检查 APK、混淆映射文件和实际 Trace，确认敏感字符串已移除、需要的诊断点仍存在。

### 团队级 Perfetto 分析知识库

共享知识库不应只收集零散 SQL。一个可审查的最小目录可以这样组织：

```text
perfetto-analysis/
├── toolchain.lock
├── trace-configs/
│   ├── startup.textproto
│   └── rendering.textproto
├── sql-packages/
│   └── team.android/
├── summaries/
│   ├── startup.textproto
│   └── memory.textproto
├── ui-macros/
│   └── macros.json
├── gates/
│   └── policy.json
├── golden-traces/
│   └── manifest.json
└── tests/
```

`toolchain.lock` 记录 Python 包、Trace Processor 版本和二进制摘要。黄金轨迹（golden trace）是结果已确认、用于回归测试的固定代表性 Trace；清单要记录其来源、系统版本、许可范围和预期结果，含敏感数据的文件本身应放在受控存储。

每次变更至少做四类检查：

1. SQL 能在空轨迹和代表性轨迹上执行；
2. 指标单位、维度、空值和极性符合事先声明的输出契约；
3. UI 宏中的命令 ID 属于稳定自动化接口；
4. 旧工具与新工具的差异经过固定轨迹对比。

知识库的评审重点应放在语义变化。格式调整可以自动化；指标定义、时间窗口、连接键（SQL JOIN 用来匹配两张表的字段）、阈值和采集依赖的变化必须由熟悉该领域的工程师确认。


## 分析平台的任务、证据与版本治理

单个 metric 可回答固定问题，分析平台还要管理 Trace 输入、查询版本、任务编排和证据链接，保证结果能够回到原始时间线。

一条 Perfetto trace 可以回答很多问题，但换一位分析者、隔一周再查，或升级一次工具后，同一个问题的过滤条件、单位和计算方法都可能变化。SmartPerfetto 用统一流程连接 Perfetto UI、`trace_processor_shell`、YAML Skill、场景策略、模型运行时、证据字段和报告存储，让 SQL 可以重跑，结论可以回查，多次分析可以按同一组指标比较。

平台机制以 Android 17 / API 37 / `android-17.0.0_r1` 为上界，涉及内核事件时以 `android17-6.18-2026-06_r6` 为基线。下文涉及字段、阈值、runtime 选择和企业迁移的实现细节，固定到 SmartPerfetto v1.3.0、提交 `24eba544cebf231524294aa50def33ee0e267c9e`；该版本固定使用 Perfetto v57.2 的 host 侧 `trace_processor_shell`。截至 2026-08-13，最新公开版本已经是 v1.5.4、提交 `0ea90aec784ca865d9f952502f87b86dc688bbe5`，v1.4～v1.5 的新增行为不自动套用到这份 v1.3.0 快照。

Android 版本与 host 工具版本是两条独立的版本线：Android 版本决定设备能采到哪些数据源，host 侧 Perfetto 版本决定 trace 解析器、SQL schema 和 stdlib（PerfettoSQL 标准库）能力。用 v57.2 分析 Android 10～17 的 trace，不表示设备端也在运行 v57.2。

### 从单次 Trace 问答到可复用分析结果

手工分析常停在一次会话中：工程师打开 Perfetto UI，运行几段 SQL，再把截图贴到 issue。截图保留了画面，却很难回答“查询条件是什么”“数值来自哪一行”“换一条 trace 后怎样用相同条件和算法复测”。SmartPerfetto 将一次分析产生的内容分为四类：

| 产物 | 主要用途 | 复核能力 |
| --- | --- | --- |
| 聊天答案 | 当前会话内解释现象、安排下一步查询 | 依赖会话中的工具结果 |
| SQL / Skill 表格 | 保存确定性取数结果 | 可检查查询、参数、列与行 |
| HTML 报告 | 分享一次完整调查 | 保留结论、限制和证据入口 |
| analysis result snapshot（分析结果快照） | 跨窗口、跨人员、跨版本比较 | 保存标准化指标、证据引用和报告身份 |

四类产物的保存周期不同。聊天答案可以随会话结束；snapshot 和报告则要携带指标来源、证据引用、运行模式、provider（模型服务提供方）、runtime（调用模型和工具的执行适配层），以及部分失败原因。团队做回归分析时应优先保存 snapshot 或报告。只有一句模型结论时，后来的人无法确认它来自 trace 数据、外部知识，还是模型推断。

SmartPerfetto 也不能代替线上性能平台。线上 P90 / P99（第 90 / 99 百分位值）、慢帧率和启动耗时用于判断影响范围与趋势；少量代表性 trace 用于解释阶段耗时、线程状态和资源竞争怎样变化。两类证据的采样方式不同，复盘时应并列呈现，不能用一条 trace 推导全量用户分布。

### Perfetto AI Assistant 的最小工作流

一次最小分析包含五个动作：加载 `.pftrace` 或 `.perfetto-trace`，说明包名与问题，限定场景或时间窗，选择分析模式，检查报告中的证据。如果已经在 Perfetto UI 选中 area（时间区间）或 track event（时间线事件），前端可以只把该选区作为上下文提交给后端。选区只缩小查询范围，不能自动证明根因就在其中。

`fast`、`full`、`auto` 控制分析 Agent 可以使用的工具范围、运行时间和模型调用量：

| 模式 | v1.3.0 行为 | 适合场景 |
| --- | --- | --- |
| `fast` | 轻量提示词、核心证据工具子集、较少的运行时间与模型调用量 | 已知问题的快速检查 |
| `full` | 完整工具、必须完成的计划与质量检查、notes（过程记录）和 artifact（分析产物） | 因果链较长或需要逐层排除的问题 |
| `auto` | 由硬规则和轻量分类器决定；无法可靠分类时走 `full` | 日常入口 |

引用 reference trace（对照 trace）、已注册源码或私有知识源时，后端会把 `fast` / `auto` 解析为 `full`，以便调用这些材料所需的工具。Smart Profile 负责选择分析场景：preview 阶段先识别可分析的时间段，用户选中启动、滑动、点击、导航、设备状态或 ANR 后，系统再创建对应的深度分析 run（一次分析执行）。Smart Profile 决定“分析哪段场景”，`fast` / `full` 决定“投入多少工具和运行时间”，两者是不同设置。

模型不会直接读取整份 trace 字节。后端通过 `trace_processor_shell`、SQL 和 Skill 取数，再把结构化结果、经过行列截断的表格片段、选区上下文及允许使用的报告片段交给 runtime。这样可以限制模型上下文大小，并让诊断先经过查询接口。数据外发风险仍然存在：工具结果可能包含进程名、线程名、slice 文本或业务标识，使用外部 provider 前仍要评估脱敏与合规要求。

复核时应记录 Result ID（一次分析结果的标识）、`evidenceRefId`（证据引用标识）、表格行列、查询限制和 runtime 身份。只反馈“回答不对”不足以定位缺陷；这些字段可以帮助维护者区分 SQL 条件或单位错误、Skill 兼容问题、trace 数据源缺失、模型推断过度，以及报告展示错误。

### YAML Skill 与场景策略的分层设计

SmartPerfetto 将可复用分析分为 Skill、strategy 和 template。v1.3.0 仓库中的 Skill 是可执行的 YAML 分析定义，不等同于一段提示词。它可以声明参数、SQL、其他 Skill 引用、迭代、并行、条件分支、诊断输出和展示 schema。Skill 目录按 atomic（单项查询）、composite（组合查询）、comparison（对比）、deep（深入分析）、pipelines（多步流程）、modules（共用模块）与 vendor（厂商扩展）组织；文件数量会随版本变化，不宜写死。

| 层级 | 主要职责 | 失败时的症状 | 复核方式 |
| --- | --- | --- | --- |
| Skill | 查询、参数、输出列、执行状态与证据来源 | 空表、错列、错时间窗、单位不一致 | 独立执行并检查 DataEnvelope |
| strategy | 场景路由、执行顺序、质量要求与误诊规则 | 选错调查路径、缺关键分支、过早收敛 | 对照场景和中间证据 |
| template | 报告结构与证据呈现 | 数字可见却无来源，限制项被遗漏 | 检查报告合约与证据引用 |

这组分层减少了临时生成 SQL 的比例。重复使用的查询放进 Skill，场景决策由 strategy 约束，报告格式交给 template。模型仍可解释数据、提出下一步查询和排列假设，但查询条件、单位换算与空结果含义应留在可测试的执行层。

Skill 输出经兼容适配器转换为 `DataEnvelope`，即 SmartPerfetto 的标准结果对象。`meta` 保存 schema 版本、来源、时间、Skill/step、执行状态和证据身份；`data` 保存表格、图表、文本或诊断内容；`display` 保存展示层级、列定义与格式。`observed` 表示得到数据，`empty` 表示查询成功但没有匹配行，`optional_error` 表示可选查询失败。三种状态不能合并解释，尤其不能把查询失败写成“没有发现问题”。

### SQL guardrail、stdlib 文档与证据来源索引

Perfetto SQL 的常见错误包括：工具升级后表或字段发生变化；漏写 stdlib module（PerfettoSQL 标准库模块）；忽略 `dur = -1` 表示事件尚未闭合；混用 `utid/upid`（Trace Processor 内部唯一 ID）与 `tid/pid`（操作系统线程/进程 ID）；没有限制时间窗；以及在大表上执行没有范围限制的 JOIN。SmartPerfetto 对 raw SQL（用户直接提交的 SQL）和 Skill SQL 使用不同的 include 构建路径。raw SQL 会根据生成的 stdlib symbol index（标准库符号索引）分析依赖，按固定顺序补入 `INCLUDE PERFETTO MODULE ...;`；Skill 执行器则按 Skill 声明构造 include。自动补全只覆盖索引中已知的符号，symbol index 为空或语句无法识别时，查询仍需显式写出 include。

执行后的 SQL 会生成 `QueryReviewV1`，这是一份查询复核元数据，记录实际读取的表、过滤条件、输出列、guardrail（规则式风险检查）告警、stdlib 注入、执行时长、行数与截断状态。复杂 CTE（公用表表达式）、嵌套查询、JOIN 或窗口函数只能得到部分静态解析时，review 必须标为 `partial`。`QueryReviewV1` 的允许用途固定为 `review_metadata_only`：它能帮助人了解查询做过什么，但不能单独证明诊断结论。

完整 Query Review 会随 DataEnvelope 或 Artifact（保存下来的分析产物）进入报告；给模型的 compact projection（压缩后的内容片段）不含可执行 SQL。因此，报告中保留了可执行 SQL，不代表模型在每轮分析时都看过完整 SQL 文本。

诊断证据由独立的 Evidence Contract 表达。这里的 contract 是一组必填字段，用来规定结论怎样指回原始查询结果。一个数值证据可以记录 `traceId`、current/reference（当前或对照 trace）、producer kind（数据生产方类型）、Skill 与 step、`queryHash`、`queryReviewId`、artifact、计划阶段，以及具体的 row selector（行定位条件）、column、actual value、单位和时间范围。claim（结论陈述）的支持等级分为 `verified`（证据完整）、`partial`（证据不完整）、`inference`（推断）和 `unsupported`（无支持）。例如报告写“主线程 Runnable 120 ms”，至少要能定位到相应证据行和列；若再写“CPU 争用导致这 120 ms”，还需调度关系或其他证据支持因果判断。

guardrail 只能发现规则中已经列出的风险，无法证明任意 PerfettoSQL 都正确。缺少 FrameTimeline、Binder、sched、GPU counter 或关键应用标记时，报告应列出缺失数据、降低支持等级，并给出补采配置。`empty` 也不能被写成“系统没有问题”。

### 多 Trace 对比与性能回归判断

SmartPerfetto 支持两类对比。raw reference trace 对比要求当前会话同时能够访问 current（当前 trace）与 reference（对照 trace）两份原始数据，适合围绕同一问题继续写查询。analysis result snapshot 对比读取已经完成的分析产物，适合版本回归、A/B、多候选结果和跨窗口复盘；这项对比只使用快照中保存的标准化指标与证据引用，不会重新查询原始 trace。

标准指标键覆盖这些类别：

- 启动：总耗时、首帧、`bindApplication`、Activity start、主线程 blocked；
- 滑动：平均 FPS（每秒帧数）、帧数、Jank（卡顿帧）数量与比例、帧时长 P50/P95/P99；
- CPU：主线程 Running/Runnable、大核占比、平均频率；
- 环境：trace 时长、设备型号、Android 版本和抓取配置摘要。

标准回填的范围更窄，只包含 `startup.total_ms`、`scrolling.avg_fps`、`scrolling.frame_count`、`scrolling.jank_count` 和 `scrolling.jank_rate_pct`。TTFD（Time to Full Display，完全显示耗时）、PSS（Proportional Set Size，按共享比例分摊的内存）、Java/Native Heap、DMA-BUF（Linux 设备驱动间共享的缓冲区）、bitmap、RSS（Resident Set Size，驻留内存）和 swap 等指标可以由 Skill、SQL 或报告模板提供，不属于 v1.3.0 的内置回填集合。缺失字段要显示为 missing metric，不能按零值参与比较。

v1.3.0 的变化高亮同时使用相对阈值和按单位设置的绝对阈值。通用相对阈值为 5%；`ms` 为 5 ms，`fps` 为 1 fps，百分比为 1 个百分点，计数为 1，字节为 1 MiB，纳秒为 5,000,000 ns。时间、FPS、字节等指标通常要同时达到绝对阈值与相对阈值；百分比和计数满足其中一个即可。无单位且只有相对变化时采用 5%。这些规则只决定界面是否高亮，不是统计显著性检验，也不能代替 26.4 节中的置信区间、样本量和实验设计。

例如，发现启动 P90 上升后，可以分别抽取 baseline（改动前基线）与 candidate（改动后候选版本）trace，生成 snapshot，再比较启动阶段、主线程状态、Binder、I/O 和首帧提交证据。若设备、温控、编译状态或抓取配置不一致，应先标注环境差异，避免把不可比样本的变化解释为代码回归。

### Provider Manager：模型服务与执行适配层

模型配置包含 Connection、Provider profile 和 runtime。Connection 保存前端要访问的 SmartPerfetto 后端地址与可选的后端 token。Provider profile 保存模型 endpoint（服务地址）、模型凭证、模型 ID、通信协议及 runtime 选择。runtime 决定由哪套 Agent SDK 或 server adapter 调用 SmartPerfetto 工具。

| 配置项 | 作用 | 常见误解 |
| --- | --- | --- |
| Connection | 前端连接 SmartPerfetto 后端 | 把后端 token 当成模型 key |
| Provider profile | 配模型服务、模型 ID、协议类型 | 保存 profile 后忘记设为 active |
| active provider | 当前会话优先使用的 provider | 以为改 `.env` 会覆盖 active profile |
| env fallback | 脚本和服务端部署的默认凭证 | 只查 `.env`，不看 Provider Manager |
| runtime | 选择 Agent SDK / server adapter | provider 能对话就认定工具调用也一定可用 |

v1.3.0 注册了五种可用于正式运行的 runtime：

| runtime | 适配层 | 配置边界 |
| --- | --- | --- |
| `claude-agent-sdk` | Claude Agent SDK | 默认 runtime；支持 Anthropic、Bedrock、Vertex、DeepSeek 与兼容网关 |
| `openai-agents-sdk` | OpenAI Agents SDK | OpenAI、Ollama 与 OpenAI-compatible endpoint |
| `pi-agent-core` | Pi Agent Core | 仅 custom provider；禁用项目发现和 shell/file tools |
| `opencode` | 隔离的 OpenCode server / SDK | 仅 custom provider；不读取用户本机 OpenCode 项目状态 |
| `qoder-agent-sdk` | Qoder Agent SDK / `qodercli` | custom provider 或显式 env；SDK 为可选依赖 |

Qoder SDK 不随默认 Docker、portable 或 npm 安装提供，启用前要审阅其独立条款，并显式安装 optional peer（可选的同级依赖）。Pi、OpenCode、Qoder 在 SmartPerfetto 中都只获得按请求生成的分析工具，不能按通用 coding agent 的文件、shell 或网络权限理解。

新建 session 时，系统依次检查请求指定的 `providerId`、Provider Manager 当前 active provider、`SMARTPERFETTO_AGENT_RUNTIME`，最后回到默认的 `claude-agent-sdk`。请求明确指定的 provider 不存在时会 fail-fast，即立即返回明确错误。恢复历史 session 时，系统使用会话中保存的 provider/runtime：已保存的 provider 仍优先；env/default session 的 `runtimeOverride` 优先于当前环境变量；后来切换的 active provider 不会改变旧会话。已绑定的 provider 被删除时也会立即报错，不会静默改用另一个 provider。

v1.3.0 的会话快照还有一个缺口。常规 runtime 选择器已经接受 `qoder-agent-sdk`，但 `providerSnapshot.ts` 解析纯环境变量配置时只列出 Claude、OpenAI、Pi 和 OpenCode。只设置 `SMARTPERFETTO_AGENT_RUNTIME=qoder-agent-sdk` 时，本次运行可以进入 Qoder，env/default 会话快照却无法证明 Qoder 身份已被正确保存。这个限制不影响显式 provider 的存在性检查；恢复这类 Qoder session 前，应先在已修复版本上做回归，或重新创建 session。

排障时要读取需要鉴权的 `GET /api/runtime-health`，检查 runtime、模型和 credential source（凭证来源）。公开的 `GET /health` 只表示服务进程存活，不返回凭证来源。因此，`GET /health` 成功不能证明分析 runtime 已按预期切换。

### 运行分发、权限和隐私边界

运行方式应按维护责任选择。Docker 适合服务端部署；三平台 portable（免安装便携版）自带 Node.js 24、后端、预构建前端和固定的 trace processor；源码运行适合维护 Skill、strategy 与后端；npm CLI 提供 `smp` / `smartperfetto`，复用同一套 runtime、MCP（Model Context Protocol）工具、报告和 session snapshot，但不启动 Web UI。批处理、CI（持续集成）或内部服务可以使用 CLI / API / MCP。

部署者设置 `SMARTPERFETTO_API_KEY` 后，受保护 API 要携带相应凭证；企业用户还可以使用带角色与 scope（权限范围）的持久 API key。后端 API key 保护 SmartPerfetto 服务入口，provider key 授权模型服务，二者不能互换。把服务暴露到非可信网络时，还要限制上传大小、代理超时、报告下载与管理接口。

trace 可能含有进程名、线程名、业务路径、URL 片段、用户操作节奏、设备信息与 slice 参数。上传给 provider 的内容片段、Result ID、HTML 报告、日志、workspace（隔离的工作空间）分享和过期清理都应按敏感数据管理。私有源码与外部知识源只有在本次请求明确选择、scope 与授权校验通过后才进入 runtime，不会自动提供给普通 trace 会话。使用 `provider_send` 时还要同时具备“该来源允许发送给 provider”和“本次运行允许发送”两项许可。

SmartPerfetto 只能分析调用方有权提供的 trace。Perfetto SDK 或 AndroidX Tracing 可以增加应用内事件，但不会赋予应用读取整机 ftrace、其他进程或系统服务内部数据的权限。系统级采集仍受 Manifest 中的 `profileable` / `debuggable` 属性、adb、ProfilingManager、系统签名权限和设备策略约束，参见 13.12 与 26.6 节。

### 和原生 Perfetto / Perfetto SDK / APM 平台的组合关系

每个工具负责不同任务。Perfetto UI 提供时间轴观察和人工验证，`trace_processor_shell` 执行结果可重复的查询，Perfetto SDK 把应用事件写入 trace，ProfilingManager 提供受平台控制的 profiling 请求，APM（Application Performance Monitoring，应用性能监控）平台统计长期趋势。SmartPerfetto 位于解析器和团队调查流程之间，负责调用查询、组织证据、生成报告与比较结果。

| 工具 | 更适合的问题 | 产物 |
| --- | --- | --- |
| Perfetto UI | 手工观察时间轴、验证某段事件关系 | 截图、选区、手动 SQL |
| `trace_processor_shell` | 批量查询、可重复 SQL、CI 检查 | CSV / SQL 输出 |
| SmartPerfetto | 开放式 trace 调查、证据报告、多 trace 对比 | Result ID、报告、Skill 表格 |
| Perfetto SDK / AndroidX Tracing | 把应用内部阶段写进 trace | 自定义 slice、counter、data source |
| ProfilingManager | Android 15（API 35）起的受控 profiling 请求 | 系统返回的 profiling 结果 |
| APM 平台 | 长期线上趋势、分位值、告警 | 指标、事件、抽样现场 |

开发期可以分析单条 trace，专项排障可以积累 Skill 与模板，灰度回归可以把异常样本与 baseline snapshot 比较。任何 Agent 生成的因果结论仍需回到 Perfetto UI 或 SQL 结果复核。涉及渲染链时，还要按 App、BufferQueue、SurfaceFlinger、HWC（Hardware Composer，硬件合成器）和显示设备五段组织证据，避免用一个长 slice 代替整条链上的逐段判断。

### Skill 质量评估与回归测试

Skill 进入团队流程后，应按可执行代码维护。最小测试集包含固定 trace、固定参数、SQL smoke test（确认基本路径可运行的快速测试）、输出列校验、空结果与可选错误分支、证据引用校验和 golden report（用于逐次比较的基准报告）。Perfetto schema、stdlib、设备数据源与厂商实现都会变化，只检查 YAML 能否解析并不够。

测试可以分为四层：

1. SQL 在固定 trace 上能够执行；
2. DataEnvelope 的列、单位、layer（展示层）与 level（详细程度）及执行状态符合 contract；
3. 关键指标与 golden（预先确认的基准值）处于允许误差内；
4. 报告中的 evidence anchor 能返回表格行列，claim support 没有把 `partial` 升级成 `verified`。

启动、滑动、ANR、Binder、I/O、内存和功耗场景都要准备成功样本与缺字段样本。缺字段样本用于验证降级路径，例如缺少 FrameTimeline 时，帧级结论必须标为不完整。SmartPerfetto 固定 trace processor 版本后仍需运行 canonical trace（团队指定的标准测试 trace）回归；升级 v57.2 之后的版本时，还要重新核对 schema、stdlib symbol index、标准指标和 golden 输出。

13.7 的 SQL 查询条件、单位与 Jank/CUJ 查询，13.11 的调查协议，以及 26.6 的回归判定可以转为 Skill contract。contract 应声明输入、输出、单位、证据解释、适用版本、缺失数据分支和人工复核入口。

### 企业内部 Trace 分析平台接入清单

企业接入前要确定 trace 存储、留存周期、报告可见范围、provider 凭证归属、模型请求出网策略、脱敏规则和审计范围。tenant 表示租户，workspace 表示租户内隔离的工作空间。表中的项目应落实到部署配置、权限测试和删除演练，不能只停在文档约定。

| 维度 | 建议检查项 |
| --- | --- |
| 多租户 | tenant / workspace 隔离、跨组报告分享审批 |
| Provider 隔离 | 每个租户单独 profile、独立 token、独立用量审计 |
| Trace 留存 | 上传大小限制、过期清理、敏感样本删除流程 |
| 报告权限 | Result ID 可见性、HTML report 分享范围、导出水印 |
| 审计 | 上传、分析、查看、分享、删除和 provider 修改记录 |
| 脱敏 | 包名、URL、账号、地理位置、业务参数、截图附件 |
| 回归 | 固定 trace 集合、Skill golden 基准、发布前 smoke test |

权限测试要覆盖同租户不同 workspace、不同 tenant、资源 owner（所有者）、过期数据和被删除 provider。能够查看报告，不代表同时有权查看原始 trace；两类资源应各自执行授权检查并保留审计记录。

### SmartPerfetto 与技术知识库联动

技术知识库保存机制解释、对应的源码版本和调查顺序，SmartPerfetto 在具体 trace 上执行查询并保存证据。输入参数、SQL、输出列、单位和失败分支等稳定规则适合转换为 Skill；依赖机型、版本或上下文判断的内容更适合放在 strategy 或机制说明中。

一种可执行的维护方法是：从章节选定一个可观察问题，编写 Skill，在固定 trace 上运行，检查报告证据，再把缺字段、厂商差异和误诊条件补回章节。章节修订后还要判断 Skill contract 是否需要同步修改，从而保持“机制说明—可执行查询—真实样本”三者一致。

### 企业版迁移与 404 排查

SmartPerfetto 的企业迁移阶段决定 trace metadata（文件路径、归属和访问范围等元数据）从文件系统还是数据库读取。v1.3.0 的状态如下：

| 阶段 | metadata 读取来源 | 写文件系统 | 写数据库 | 回退方式 |
| --- | --- | --- | --- | --- |
| `legacy` | filesystem | 是 | 否 | 关闭企业模式 |
| `dual-write` | filesystem | 是 | 是 | 删除数据库副本，文件系统仍为权威 |
| `cutover` | DB | 否 | 是 | 恢复切换前已验证的文件系统与 DB 快照 |
| `retired` | DB | 否 | 是 | 恢复退役前快照；不承诺反向转换 |

企业功能启用且未配置 `SMARTPERFETTO_ENTERPRISE_MIGRATION_PHASE` 时，默认阶段是 `dual-write`。进入 `cutover` 还要求 `SMARTPERFETTO_ENTERPRISE_CUTOVER_CONFIRMED=true`；缺少该确认时，服务会在解析迁移计划时拒绝启动。这项启动检查要求运维人员已经完成 filesystem 与 DB 的 reconciliation（逐项比对并处理不一致记录），并验证可用于恢复的快照。

诊断环境阶段时，可用下面的命令只打印两个迁移开关，不要把数据库口令或 provider key 写入工单：

```bash
printf 'phase=%s\n' "${SMARTPERFETTO_ENTERPRISE_MIGRATION_PHASE:-<unset>}"
printf 'cutover_confirmed=%s\n' "${SMARTPERFETTO_ENTERPRISE_CUTOVER_CONFIRMED:-<unset>}"
```

这两行只显示迁移阶段与切换确认，不会输出数据库口令或 provider key。第一行未设置且企业功能已开启时，应按 `dual-write` 解释；第二行只有在准备进入 `cutover` 时才应为 `true`。

`cutover` 阶段的 `readTraceMetadataForContext()` 只按当前 RequestContext 中的 tenant、workspace 和 owner 权限范围查询 `trace_assets`；查不到就返回 `null`，不会改查旧文件系统。RequestContext 表示这次请求携带的身份与授权信息，RBAC（Role-Based Access Control）表示按角色授予访问权限。如果失败后悄悄改查文件系统，就可能绕过 DB 上的 RBAC 检查，还会掩盖尚未迁移的数据，因此这种回退不能用于修复 404。

遇到切换后的 404，可按以下顺序排查：

1. 确认生效阶段、enterprise feature flag（企业功能开关）与 cutover confirmation；
2. 按请求的 tenant、workspace 和 owner 检查 `trace_assets` 是否存在记录；
3. 检查记录中的 `local_path`、文件搬运结果和服务进程访问权限；
4. 检查 SSO（Single Sign-On，单点登录）映射、API key scope 与 RBAC，区分“记录缺失”和“当前用户不可见”；
5. 对照切换前 dry-run fingerprint（试运行结果摘要）、snapshot manifest（快照内容清单）与数据库表计数；
6. 若切换数据不完整，停止写入，按项目提供的 snapshot restore 流程恢复文件系统和 SQLite 快照，再重新处理 reconciliation 中发现的不一致记录。

不能只把环境变量改回 `dual-write`，然后假设 DB 数据会自动写回文件系统。源码明确说明 dual-write 没有实现 reverse importer（从数据库反向导回文件系统的工具）。快照恢复会覆盖目标文件或目录，必须在维护窗口内由部署负责人执行，并在恢复前保留现场副本。

404 率、trace 访问成功率和数据库延迟的阈值应由团队按 SLO（Service Level Objective，服务等级目标）与流量设定，SmartPerfetto 源码没有规定 99.5% 或 0.5% 这类通用目标。迁移监控还应包含 reconciliation 失败数、snapshot 完整性、按 scope 查询时未命中的原因分类，以及恢复演练结果。

### 复核准则

使用 SmartPerfetto 时，可以用四个问题约束分析质量：

1. 报告中的关键数值能否回到证据行列和 trace 身份？
2. 因果结论的支持等级是否与调度、时间关系或跨层证据相符？
3. 多 trace 指标是否使用相同查询条件、单位和采集环境，并明确缺失字段？
4. provider、runtime、私有上下文与企业存储是否遵守当前部署的权限边界？

四项中任何一项无法回答，都应把结论留在待验证状态。SmartPerfetto 可以减少重复查询和报告整理，却不会替代 Android 机制判断、Perfetto UI 人工核验或可重复的实验设计。

## 小结

Perfetto 自动化要从一条可复用 SQL 开始，再逐步扩展到 Trace Summary、批处理、CI 回归和团队分析平台。扩展过程中，每个数值都要保留 trace 身份、查询、单位、样本数和工具版本；Agent、provider 或企业存储只是执行与治理层，不能改变 trace 缺字段、缺因果链时的证据上限。


## 参考资料

- [Android 17 `external/perfetto` 源码](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/)
- [Android 17 `Trace.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/Trace.java)
- [Android 17 `libcutils` ATrace 接口](https://android.googlesource.com/platform/system/core/+/android-17.0.0_r1/libcutils/include/cutils/trace.h)
- [Trace Summarization](https://perfetto.dev/docs/analysis/trace-summary)
- [旧版 Trace-based Metrics](https://perfetto.dev/docs/analysis/metrics)
- [PerfettoSQL 语法](https://perfetto.dev/docs/analysis/perfetto-sql-syntax)
- [Trace Processor Python API](https://perfetto.dev/docs/analysis/trace-processor-python)
- [Batch Trace Processor](https://perfetto.dev/docs/analysis/batch-trace-processor)
- [Perfetto UI 命令与宏](https://perfetto.dev/docs/visualization/ui-automation)
- [稳定 UI 自动化命令参考](https://perfetto.dev/docs/visualization/commands-automation-reference)
- [Perfetto 扩展服务器](https://perfetto.dev/docs/visualization/extension-servers)
- [Perfetto Tracing SDK](https://perfetto.dev/docs/instrumentation/tracing-sdk)
- [Android ATrace 埋点](https://perfetto.dev/docs/getting-started/atrace)
- [Android NDK Tracing API](https://developer.android.com/ndk/reference/group/tracing)
- [Macrobenchmark 持续集成](https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci)
- [Android 性能测量与 Trace Point 开销建议](https://developer.android.com/topic/performance/measuring-performance)

- [SmartPerfetto v1.3.0 核对提交](https://github.com/Gracker/SmartPerfetto/tree/24eba544cebf231524294aa50def33ee0e267c9e)
- [Perfetto v57.2 host 工具固定配置](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/scripts/trace-processor-pin.env)
- [Agent runtime 架构](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/docs/architecture/agent-runtime.md)
- [runtime 选择与 snapshot override 顺序](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/backend/src/agentRuntime/runtimeSelection.ts)
- [v1.3.0 provider/runtime 快照解析](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/backend/src/services/providerManager/providerSnapshot.ts)
- [私有分析上下文边界](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/docs/architecture/private-analysis-context.md)
- [DataEnvelope、Query Review 与 Analysis Receipt](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/backend/docs/DATA_CONTRACT_DESIGN.md)
- [raw SQL stdlib include 注入](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/backend/src/agentv3/sqlIncludeInjector.ts)
- [证据合约类型](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/backend/src/types/evidenceContract.ts)
- [标准对比指标](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/backend/src/types/multiTraceComparison.ts)
- [标准指标回填范围](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/backend/src/services/standardMetricBackfillService.ts)
- [显著变化阈值](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/backend/src/services/comparisonSignificance.ts)
- [企业迁移状态机与快照恢复](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/backend/src/services/enterpriseMigration.ts)
- [企业 trace metadata 的 scoped 读取](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/backend/src/services/traceMetadataStore.ts)
