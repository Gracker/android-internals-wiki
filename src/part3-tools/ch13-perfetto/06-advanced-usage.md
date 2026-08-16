---
title: "Perfetto 指标、自动化与高级用法"
chapter: "13.6"
section: "13.6"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-08-13"
last_verified_against: "Android 17 / API 37 / android-17.0.0_r1 (Perfetto ece66975738007dd0978b911d8a2077e49b8f31e); Perfetto Trace Processor v57.2-da1d152cf; android17-6.18-2026-06_r6; perfetto.dev (2026-08-13)"
confidence: high
sources:
  - type: official
    path: "https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/"
  - type: official
    path: "https://android.googlesource.com/platform/system/core/+/android-17.0.0_r1/libcutils/include/cutils/trace.h"
  - type: official
    path: "https://perfetto.dev/docs/analysis/trace-summary"
  - type: official
    path: "https://perfetto.dev/docs/analysis/metrics"
  - type: official
    path: "https://perfetto.dev/docs/analysis/trace-processor-python"
  - type: official
    path: "https://perfetto.dev/docs/analysis/batch-trace-processor"
  - type: official
    path: "https://perfetto.dev/docs/visualization/ui-automation"
  - type: official
    path: "https://perfetto.dev/docs/visualization/commands-automation-reference"
  - type: official
    path: "https://perfetto.dev/docs/visualization/extension-servers"
  - type: official
    path: "https://perfetto.dev/docs/instrumentation/tracing-sdk"
  - type: official
    path: "https://perfetto.dev/docs/getting-started/atrace"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci"
  - type: official
    path: "https://developer.android.com/topic/performance/measuring-performance"
tags:
  - android
  - perfetto
  - research
status: finalized
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
task2b_state: fixed
---


# 13.6 Perfetto 指标、自动化与高级用法

单份系统 Trace 可以支持一次诊断；可复用查询、结构化指标、批量分析、持续集成和应用埋点还要解决跨人员、跨构建、跨日期的一致性。同一条分析规则应始终产出语义一致的结果，并在异常发生时保留足够的原始证据。

本文核对的平台源码基线是 Android 17 / API 37 / `android-17.0.0_r1`。该标签的 `external/perfetto` 指向提交 `ece66975738007dd0978b911d8a2077e49b8f31e`；调度与 ftrace（Linux 内核跟踪机制）的采集行为以 `android17-6.18-2026-06_r6` 为边界。主机上的 Perfetto UI、Python 包和 Trace Processor 可以独立升级，因此流水线还要固定主机工具版本，不能只记录设备系统版本。

## 四种可复用能力

Perfetto 提供了几套名称相近、用途不同的机制。选错层次后，查询可能能运行，却很难长期维护。

| 机制 | 输入 | 输出 | 适用位置 |
|---|---|---|---|
| PerfettoSQL 标准库 | `INCLUDE PERFETTO MODULE` | 稳定表、视图和函数 | 单份 Trace 查询的公共语义层 |
| Trace Summarization | 指标规格 + 标准库或 SQL | 统一的 `TraceSummary` protobuf | 新建自动化指标和跨 Trace 分析 |
| 旧版 v1 指标 | SQL + 自定义 protobuf | `TraceMetrics` protobuf | 维护已有指标，或兼容现有读取服务 |
| UI 命令宏 | JSON 命令序列 | 工作区、查询页、调试轨道等界面状态 | 重复执行人工诊断步骤 |

protobuf（Protocol Buffers）是带字段类型的结构化消息格式。自动化分析中的“输出契约”指字段名、类型、单位和含义都可被读取端稳定依赖，不只表示文件采用二进制编码。

PerfettoSQL 还定义了 `CREATE PERFETTO MACRO`，用于在查询执行前展开表达式或子查询。它与 UI 设置里的命令宏没有共享配置，执行方式也不同。

## 自定义指标：新项目从 Trace Summarization 开始

### 为何不再把 v1 指标当作默认方案

Android 17 标签和 v57.2 命令帮助都把 v1 指标标为软弃用（soft deprecated）：已有指标与命令行兼容接口继续工作，但官方不再为这套体系增加新功能或新指标。新项目应使用 Trace Summarization。两者的 SQL 能力接近，输出契约差异很大。

v1 指标要求每个团队维护独立的输出 protobuf。Trace Summarization 使用统一的 `TraceSummary`，并在规格中声明维度、数值列、单位和极性：维度是进程名、场景等分组字段，极性说明数值升高或降低哪一侧更好。统一结构更适合批量处理、仪表板和长期性能回退追踪。

一个可维护的选择顺序如下：

1. 在标准库中查找已有模块，确认表的语义和版本边界。
2. 用 Trace Summarization 描述新指标。
3. 标准库存在缺口时，在仓库内增加自定义 PerfettoSQL 包。
4. 只有现有读取端依赖 `TraceMetrics` 时，才增加或修改 v1 指标。

### Trace Summarization 的完整示例

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

### 存量 v1 指标：SQL 与 protobuf 的约定

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

### 指标失败时先检查采集条件

SQL 返回空表不等于性能为零。常见原因包括：

- 采集配置没有启用指标所依赖的数据源；
- 轨迹在目标事件发生前结束；
- 目标进程未被 `atrace_apps` 允许；
- 工具版本缺少规格引用的标准库模块；
- 数据质量表已经记录丢包、截断或时钟问题；
- 进程名、包名或启动模式与查询条件不一致。

每个指标规格应同时记录依赖的数据源、支持的系统版本、单位、方向、空值含义和已知失效边界。CI（Continuous Integration，持续集成）不能把空结果自动转成数值零：空值表示没有足够证据，零表示证据完整且测得数值为零。

## 两类宏：SQL 复用与 UI 自动化

### PerfettoSQL 宏

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

### UI 命令宏

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

### “仪表板”要分成单轨迹和跨轨迹两层

Perfetto UI 擅长对一份轨迹做交互诊断。工作区、查询页和调试轨道可以组成单轨迹仪表板，但它们不会自动保存跨构建趋势。

跨 Trace 仪表板应读取 Trace Summarization 或 Benchmark JSON。后者是 AndroidX Benchmark 输出的结构化测量报告：

| 层次 | 保存内容 | 回答的问题 |
|---|---|---|
| Perfetto UI | 宏、工作区、调试轨道、查询页 | 这次慢在哪里 |
| 指标文件 | `TraceSummary`、Benchmark JSON、工具版本 | 这次测到了什么 |
| 时序存储 | 按时间保存构建、设备、场景、样本与指标 | 何时开始变化 |
| 可视化与告警 | 分位数、基线区间、Trace 链接 | 是否需要人工复核 |

分位数表示样本在排序后所处的位置，例如 P50 是中位数。趋势图上的每个异常点都应能跳回原始 Trace、构建信息和指标规格版本；只保存均值、分位数等聚合值会丢失根因证据。

## Trace Processor Python API

### 固定二进制，记录包与工具的每次变化

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

### 批量查询

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

### 远程 Trace Processor 的支持边界

Android 17 标签和 v57.2 已提供新的服务子命令。下面的命令在本机 9001 端口启动原生 Trace Processor，并开放 RPC（Remote Procedure Call，远程过程调用）接口供 Perfetto UI 探测：

```bash
trace_processor server http trace.perfetto-trace
```

旧写法 `trace_processor --httpd trace.perfetto-trace` 在 v57.2 中仍完整支持。原生进程绕开浏览器 WebAssembly（浏览器内的沙箱二进制执行环境）的内存限制，但 Trace 解析后的内存仍可能显著大于文件大小。

`external/perfetto/src/trace_processor/rpc/` 中的 `Rpc` 负责 protobuf 编解码，HTTP、标准输入输出（stdio）和 WebAssembly 桥接负责传输。Python 客户端已经封装协议协商（确认双方支持的 RPC 版本和能力）、分批响应和错误处理。业务脚本应调用 Python API 或命令行接口，不应手写 `/rpc` 请求、分块传输和序列号管理。

服务应只监听回环地址，即仅本机可访问的 `127.0.0.1` 或 `::1`。Trace 可能包含进程名、文件路径、埋点文本和业务标识，不应把 9001 端口直接暴露到共享网络。UI 和服务器版本相差过大时还可能出现 RPC 版本不匹配，升级时要成套验证。

## 把 Perfetto 放进持续集成

### 测量值和诊断证据各司其职

AndroidX Macrobenchmark 是在 Android 设备上重复执行启动、滚动等场景的基准测试库。它会输出 Benchmark JSON，并为每次测量保存一份 Perfetto Trace。持续集成中的门禁是根据测量结果自动决定构建是否允许继续；可以分两层处理：

- Benchmark JSON 作为门禁的主要数值来源；
- Perfetto SQL 或 Trace Summarization 生成诊断指标，并保留异常样本的原始轨迹。

不宜从某个可能变化的 Slice 名称重新计算启动时间，再与 Macrobenchmark 的 `StartupTimingMetric` 混为同一个指标。系统升级或埋点名称变化后，两套定义可能产生不易察觉的偏差。

### 可复现的流水线

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

### 门禁阈值来自设备噪声，不来自通用百分比

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

### 轨迹诊断不能反向污染测量

增加 ftrace 事件、堆采样或密集应用埋点会改变被测程序和系统的采集开销。门禁配置和深度诊断配置可以分开：

- 常规门禁只采 Macrobenchmark 所需数据；
- 超过阈值后用同一提交复测并启用更详细的数据源；
- 诊断结果用于定位，不拿来替换原门禁样本；
- 每次采集配置变更都建立新基线，避免把工具开销变化记成产品性能变化。

这样可以控制日常测量开销，也能在异常发生后获得调度、Binder、内存或渲染证据。

## 自定义 Trace Point（埋点）

### 选择平台 API 还是 Perfetto SDK

这里的 Trace Point 指代码主动写入 Trace 的应用或平台埋点，与 Linux 内核预定义的 Tracepoint 分属不同机制。同步时间片描述同一线程上有明确起止的工作，异步时间片可跨线程或跨回调配对，计数器记录随时间变化的数值。Android 应用只需要这三类事件时，平台 Trace 或 NDK（Native Development Kit，C/C++ 开发工具包）的 `ATrace_*` 已经足够；Perfetto SDK 更适合 C++ 引擎、跨平台程序、分类过滤、流事件或强类型扩展。

| 接口 | 可用边界 | 适合场景 |
|---|---|---|
| `Trace.beginSection/endSection` | API 18+ | Java/Kotlin 同线程嵌套阶段 |
| `ATrace_beginSection/endSection` | NDK API 23+ | C/C++ 同线程嵌套阶段 |
| `Trace.beginAsyncSection/endAsyncSection` | API 29+ | Java/Kotlin 跨线程阶段 |
| `ATrace_beginAsyncSection/endAsyncSection` | NDK API 29+ | C/C++ 跨线程阶段 |
| `Trace.setCounter` / `ATrace_setCounter` | API 29+ | 随时间变化的数值 |
| Perfetto SDK `TRACE_EVENT` | C++17 SDK | 分类、流、计数器和扩展字段 |

### Java/Kotlin 同步时间片

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

### NDK `ATrace_*`

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

### Native Perfetto SDK

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

### 生产包治理

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

## 团队级 Perfetto 分析知识库

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
