---
title: "命令行打开超大 Trace"
chapter: "13.4"
section: "13.4"
section_title: "命令行打开超大 Trace"
status: finalized
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-08-13"
last_verified_against: "AOSP android-17.0.0_r1 external/perfetto ece66975738007dd0978b911d8a2077e49b8f31e（trace_processor shell/query/query-output/server/export + traceconv）+ Perfetto v57.2-da1d152cf 实测 + 2026-08-13 Perfetto 官方 C++/Python/Batch/large-trace 文档"
confidence: high
sources:
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-20-perfetto-remote-trace-processor-architecture.md"
    role: "本机 Trace Processor RPC 与大型 trace 分析架构"
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-30-android17-perfetto-version-availability-verification.md"
    role: "Android 17 Perfetto 主机工具与平台版本边界"
  - type: official
    path: "https://perfetto.dev/docs/visualization/large-traces"
    role: "浏览器内存边界与 native accelerator"
  - type: official
    path: "https://perfetto.dev/docs/analysis/trace-processor"
    role: "Trace Processor 下载、交互模式、query/server/export 子命令与兼容层"
  - type: official
    path: "https://perfetto.dev/docs/analysis/perfetto-sql-getting-started"
    role: "PerfettoSQL 基础"
  - type: official
    path: "https://perfetto.dev/docs/analysis/sql-tables"
    role: "slice、sched、thread_state、counter 等内置表"
  - type: official
    path: "https://perfetto.dev/docs/analysis/trace-processor-python"
    role: "Python TraceProcessor、版本固定与 DataFrame 输出"
  - type: official
    path: "https://perfetto.dev/docs/analysis/batch-trace-processor"
    role: "多 trace 查询、结果合并与内存模型"
  - type: official
    path: "https://perfetto.dev/docs/quickstart/traceconv"
    role: "格式转换、profile 与 bundle"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/trace_processor_shell.cc"
    role: "Android 17 子命令入口、classic 参数兼容与全局选项"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/shell/query_subcommand.cc"
    role: "Android 17 query 文件、stdin 与多语句入口"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/shell/query.cc"
    role: "Android 17 非交互查询的单结果集限制与 CSV 输出"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/shell/server_subcommand.cc"
    role: "Android 17 HTTP/stdio RPC server"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/shell/export_subcommand.cc"
    role: "Android 17 SQLite export"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/traceconv/main.cc"
    role: "Android 17 traceconv mode 与参数"
tags: [perfetto, trace_processor, sql, python, cli, large-traces]
related_chapters: ["13.1", "13.2", "13.3", "13.9", "13.22"]
task9_state: reviewed
task2b_state: fixed
task6_state: reviewed
pipeline_stage: ready-to-publish
---

# 13.4 命令行打开超大 Trace

## 大 Trace 的压力来自运行时表示

Perfetto UI 默认在浏览器中运行 WebAssembly 版 Trace Processor；WebAssembly 是让编译后的程序在浏览器沙箱中执行的二进制格式。浏览器通常会限制单个站点可用的内存，官方文档给出的典型运行时上限约为 2 GB。这个数字指解析和查询期间的站点内存，并非 Trace 文件大小，也不是所有浏览器都遵循的固定阈值。

Trace Processor 会把输入 packet 解析成便于查询的列式表，也就是按列组织值以提高扫描和聚合效率。对未压缩 protobuf Trace，官方给出的运行时内存经验值是文件体积的 2～4 倍；比例仍会随 data source、事件密度、输入格式和工具版本变化。因此，不能用“超过 200 MB 一定打不开”或“500 MB 必然需要多少内存”判断风险。

本机原生 Trace Processor 可以使用主机可用内存，并避开浏览器站点的内存上限。它依旧要读取并解析完整 Trace，不会把超大文件自动变成内存占用恒定的流式查询。遇到加载问题时，应先检查主机资源和 Trace 质量，再决定使用本机后端、缩小采集范围或分批处理。

命令行还可以把同一份 SQL 重复运行在一组 Trace 上，适合回归测试和持续集成。Trace 默认留在本机；若文件包含应用标记、进程名、URL 或用户数据，仍须遵守团队的数据分级、访问和保留策略。

## 固定主机工具版本

Android 17 / API 37 的平台源码锚点是 `android-17.0.0_r1`。Trace 生产端与主机分析工具是两条独立版本线：Android 17 设备产生的 Trace 可以交给匹配版本，或经过兼容性验证的较新主机工具分析。要复现分析结果，必须记录实际使用的主机工具版本，不能只记录设备版本。

下面的命令下载官方启动脚本并打印它选中的 Trace Processor 版本：

```bash
curl -LO https://get.perfetto.dev/trace_processor
chmod +x ./trace_processor
./trace_processor --version
```

下载到的 `trace_processor` 是依赖 Python 3 的轻量启动脚本。首次运行时，它会获取当前平台的原生程序，并缓存到 `~/.local/share/perfetto/prebuilts`。因此，归档分析环境时应记录启动脚本校验和与 `--version` 输出；只有文件名无法证明最终执行的是哪个原生程序。

若流水线要求长期复现，可以把审核过的原生程序放入受控工具目录，并记录其校验和，再让 Python API 的 `bin_path` 指向它。临时探索可以使用官方启动脚本；正式基线不能在没有版本记录的情况下持续跟随“latest”。

## 交互式 Trace Processor

下面的命令加载一份 Trace 并进入 PerfettoSQL 交互终端：

```bash
./trace_processor trace.perfetto-trace
```

程序完成解析后会显示 SQL 提示符。输入文件也可以是包含多份 Trace 的 ZIP 或 TAR；此时 Trace Processor 会把它们合并到同一时间轴上。分析前必须确认各文件的时钟同步、机器或进程归属信息足以支持合并。

交互终端常用的元命令如下：

```text
.tables
.schema slice
.read analysis.sql
.quit
```

`.tables` 列出本次输入产生的表和视图，`.schema` 查看列定义，`.read` 执行 SQL 文件，`.quit` 退出。拿到陌生 Trace 时，应先检查实际表、列和数据，再运行已有查询；采集时没有启用的 data source，不会因为 SQL 正确就自动出现。

## 用本机后端保留 Perfetto UI

需要时间轴、Track 嵌套和跨线程对齐视图时，可以让 UI 连接本机原生后端。这里的 native accelerator 指本机原生 Trace Processor 代替浏览器 WebAssembly 引擎执行解析和 SQL。当前子命令写法如下：

```bash
./trace_processor server http /path/to/trace.pftrace
```

服务默认监听 `127.0.0.1:9001`。打开 [Perfetto UI](https://ui.perfetto.dev) 后，页面会探测该地址，并询问使用外部加速器还是浏览器内置的 WebAssembly 后端。旧写法 `./trace_processor --httpd /path/to/trace.pftrace` 仍由兼容层支持，行为相同。

`server http` 通过 RPC（Remote Procedure Call，远程过程调用）让本机原生进程负责解析和 SQL，UI 负责交互与显示。它不降低 Trace Processor 自身的完整解析内存需求。`--port` 可改端口，`--ip-address` 可改绑定地址，`--additional-cors-origins` 可增加通过浏览器跨来源检查的页面地址。除非已有明确的网络隔离和鉴权方案，不要让包含敏感 Trace 的服务监听局域网或公网地址。

## PerfettoSQL 的数据模型

PerfettoSQL 继承 SQLite 语法，并增加 `CREATE PERFETTO VIEW`、`CREATE PERFETTO MACRO`、标准库模块和区间处理能力。查询能否跨版本工作，取决于表、列、模块及输入 data source，不能用一个固定百分比概括它与 SQLite 的相似程度。

常见内置表负责不同职责：

- `slice` 保存有开始时间和持续时间的区间事件，通过 `track_id` 关联所属 Track。
- `sched` 保存线程在某个 CPU 上实际运行的区间。
- `thread_state` 保存线程运行、可运行、睡眠等状态区间。
- `counter` 保存“时间戳 + 数值”样本，通过 `track_id` 关联计数器 Track。
- `thread` 与 `process` 保存线程、进程元数据。
- `stats` 保存解析错误、数据丢失和调试统计，是自动分析的质量入口。

`ts` 和 `dur` 通常以纳秒表示。Trace 中的单调时钟只保证时间随系统运行向前推进，适合做区间运算，但它的值不能直接当作日期时间。Perfetto 使用 `utid`（Trace 内唯一线程 ID）和 `upid`（Trace 内唯一进程 ID）标识本次 Trace 中的线程与进程实例，避免 Linux `tid`、`pid` 在对象退出后被复用而发生错误关联。按进程聚合时，应同时按 `upid` 与名称分组；只按名称会合并同名的不同进程实例。

### 先确认表和事件

下面的查询用一个结果集检查常用表，并列出实际出现的 Slice 名称：

```sql
SELECT
  'table' AS item_type,
  name AS item_name
FROM sqlite_master
WHERE type IN ('table', 'view')
  AND name IN ('slice', 'sched', 'thread_state', 'counter', 'stats')

UNION ALL

SELECT
  'slice_name' AS item_type,
  name AS item_name
FROM (
  SELECT DISTINCT name
  FROM slice
  ORDER BY name
  LIMIT 100
)
ORDER BY item_type, item_name;
```

`item_type` 区分表名与 Slice 名称。名称列表只用于发现输入中已有的事件。生产指标应绑定经过验证的系统 Slice、自定义 Trace 标记或标准库模块；事件不存在时要保留为缺失值，不能静默写成零，因为零会被误读为“事件存在且测量结果为 0”。

### 先过数据质量门

下面的查询列出解析阶段报告的错误和数据丢失：

```sql
SELECT
  severity,
  name,
  idx,
  value
FROM stats
WHERE severity IN ('error', 'data_loss')
  AND value != 0
ORDER BY severity, name, idx;
```

这里的“质量门”是指标入库前必须通过的检查。有结果不表示整份 Trace 必然不可用，但相应 data source 和时间区间需要单独判定。流水线至少要保存这些记录，并阻止受影响的指标在没有标记的情况下进入历史基线。

### 找出某个进程的长 Slice

下面的查询使用 Android 系统界面进程作为具体例子，找出它的 20 个最长线程 Slice：

```sql
SELECT
  p.upid,
  p.name AS process_name,
  t.utid,
  t.name AS thread_name,
  s.name AS slice_name,
  s.ts,
  s.dur,
  s.dur / 1e6 AS dur_ms
FROM slice AS s
JOIN thread_track AS tt ON s.track_id = tt.id
JOIN thread AS t USING (utid)
JOIN process AS p USING (upid)
WHERE p.name = 'com.android.systemui'
  AND s.dur >= 0
ORDER BY s.dur DESC
LIMIT 20;
```

关联路径是 `slice → thread_track → thread → process`：Slice 先找到所属线程轨道，再找到线程及其进程。分析应用进程时，应先从 `process` 表确认包进程的实际名称，再替换过滤条件；多进程应用的 `:remote` 等进程不会自动并入主进程。

### 按进程实例统计 CPU 运行时间

下面的查询对 `sched` 区间求和，并保留进程实例标识：

```sql
SELECT
  p.upid,
  COALESCE(p.name, '[unknown]') AS process_name,
  SUM(s.dur) / 1e9 AS cpu_seconds
FROM sched AS s
JOIN thread AS t USING (utid)
LEFT JOIN process AS p USING (upid)
WHERE s.dur > 0
GROUP BY p.upid, p.name
ORDER BY cpu_seconds DESC
LIMIT 20;
```

这里得到的是所有线程在各 CPU 上运行时间的总和。两个线程若同时在两颗 CPU 上各运行 1 秒，总 CPU 时间就是 2 秒，因此多核并行时它可以大于墙上经过时间。这个总和也不等于 CPU 利用率；计算利用率还要明确分析窗口长度和作为分母的可用 CPU 数。

### 用真实区间计算线程状态交集

固定“Trace 第 10～20 秒”或“启动后 5 秒”容易把无关工作算入指标。更稳妥的做法是让被测应用写入边界明确的自定义 Trace 标记。下面假定被测代码已经产生一个持续时间大于零、名称唯一的 `cold_start` Slice，并统计该 Slice 所在线程与各线程状态的交集：

```sql
WITH target AS (
  SELECT
    s.ts AS start_ts,
    s.ts + s.dur AS end_ts,
    tt.utid
  FROM slice AS s
  JOIN thread_track AS tt ON s.track_id = tt.id
  WHERE s.name = 'cold_start'
    AND s.dur > 0
  ORDER BY s.ts
  LIMIT 1
),
overlap AS (
  SELECT
    st.state,
    st.io_wait,
    st.blocked_function,
    MIN(st.ts + st.dur, target.end_ts)
      - MAX(st.ts, target.start_ts) AS overlap_ns
  FROM thread_state AS st
  JOIN target USING (utid)
  WHERE st.dur > 0
    AND st.ts < target.end_ts
    AND st.ts + st.dur > target.start_ts
)
SELECT
  state,
  io_wait,
  blocked_function,
  SUM(overlap_ns) / 1e6 AS overlap_ms
FROM overlap
GROUP BY state, io_wait, blocked_function
ORDER BY overlap_ms DESC;
```

区间相交条件使用半开时间窗 `[start_ts, end_ts)`，只累计目标 Slice 内真正重叠的状态片段。Linux 的 `D` 表示不可中断睡眠，磁盘 I/O 只是可能原因之一；还要结合 `io_wait`、`blocked_function`、内核事件和调用栈确认阻塞来源。若 `cold_start` 标记不存在，查询返回空集，流水线应将本次样本判为采集不完整。

## 非交互查询与导出

Android 17 源码中的 Trace Processor 已提供 `query`、`interactive`、`server`、`summarize`、`export` 等子命令。旧的 `-q`、`-Q`、`--httpd`、`-e` 参数仍由兼容层转换，新脚本宜直接使用子命令接口，让参数归属更清楚。

下面展示内联 SQL、SQL 文件和标准输入三种输入方式：

```bash
./trace_processor query trace.pftrace \
  "SELECT ts, dur, name FROM slice LIMIT 5"

./trace_processor query -f queries.sql trace.pftrace

./trace_processor query -f - trace.pftrace < queries.sql
```

SQL 可以包含多条以分号分隔的语句。`android-17.0.0_r1` 的 `query.cc` 会检查前序语句是否产生结果行：只有末尾语句可以返回结果，前面可放不返回行的建表、插入或模块加载语句。非交互结果按 CSV（逗号分隔的结构化文本）输出，字段可能包含引号、逗号或换行，解析时应使用 CSV 库。

截至 2026-08-13，Perfetto 网页文档描述了依次打印多个 CSV 结果集的行为，但官方下载的稳定版 v57.2-da1d152cf 实测仍执行单结果集限制：连续执行两个 `SELECT` 会报错。Android 17 标签源码也采用这条限制。网页文档可能先于稳定二进制更新，因此自动化脚本应按固定版本的 `--help` 和最小行为测试编写，升级工具时重新验证。

同一份大 Trace 要连续执行很多查询时，可以使用 v57.2 已支持的 warm session，避免每条命令都重新解析。`./trace_processor server unix --name mysession --daemonize trace.pftrace` 会在 Linux、macOS 等 POSIX 系统上创建名为 `mysession` 的后台本机进程通信端点（Unix socket）；随后用 `./trace_processor query --remote mysession "SELECT COUNT(*) FROM slice"` 查询，完成后执行 `./trace_processor server kill mysession`。会话会一直占用已解析 Trace 所需内存，脚本要处理命名冲突、超时和异常退出后的清理。

### 给批处理建立固定质量输出

下面的 `trace_quality.sql` 始终返回一行，适合作为每份 Trace 进入历史数据集前的质量检查：

```sql
SELECT
  COALESCE(SUM(
    CASE WHEN severity = 'data_loss' THEN value ELSE 0 END
  ), 0) AS data_loss_count,
  COALESCE(SUM(
    CASE WHEN severity = 'error' THEN value ELSE 0 END
  ), 0) AS parser_error_count
FROM stats
WHERE severity IN ('data_loss', 'error');
```

两个字段只代表 Trace Processor 报告的解析统计，无法发现业务埋点缺失、场景执行失败或时间边界错误。它们应与必需表、必需标记和设备执行日志一起检查。

下面的脚本逐份处理 `./traces` 中的 Trace，并把结果写到独立文件：

```bash
for trace in ./traces/*.pftrace; do
  [ -e "$trace" ] || continue
  ./trace_processor query -f trace_quality.sql "$trace" \
    > "${trace}.quality.csv"
done
```

逐份启动会重复付出解析成本，但能把峰值内存限制在单份 Trace 附近。文件名和 Trace 校验和仍要写进结果清单，避免复制或重命名后失去样本身份。

### 导出 SQLite 与诊断 Trace Processor

下面的命令分别导出 SQLite、关闭通用 ftrace 原始表摄取，并记录加载与查询耗时：

```bash
./trace_processor export sqlite -o result.sqlite trace.pftrace

./trace_processor --no-ftrace-raw trace.pftrace

./trace_processor query --perf-file tp-perf.txt \
  trace.pftrace "SELECT COUNT(*) AS slice_count FROM slice"
```

`export sqlite` 便于交给 SQLite 工具继续处理，但生成数据库前仍要完整解析输入。v57.2 的 `export --help` 只列出 SQLite；当前网页文档已经出现 `perfetto` 可重载归档和 `arrow_tar`，这些格式尚未进入该稳定二进制，不能只看网页就用于 v57.2 流水线。`--no-ftrace-raw` 会阻止类型化 ftrace 事件额外进入通用 `ftrace_event` 原始表，在 SQL 不查询这条路径时可降低内存。`--perf-file` 记录加载和查询耗时，用来区分慢在解析还是 SQL；`--full-sort` 会强制完整排序，不能当作省内存选项。

## Python API

Python API 适合组织多步查询、结构化输出和统计处理。安装要求是 Python 3；`as_pandas_dataframe()` 会把结果转换为 Pandas DataFrame（按行列组织的内存数据表），还需要 Pandas 与 NumPy。

下面的命令安装官方包及 DataFrame 依赖：

```bash
python3 -m pip install perfetto pandas numpy
```

正式流水线应在依赖锁文件中固定 Python 包版本。默认配置会下载与已安装 `perfetto` 包绑定的 Trace Processor 版本；升级 Python 包时，底层原生程序也可能变化。

下面的程序固定原生程序路径，查询长 Slice，并用上下文管理器释放服务进程：

```python
from perfetto.trace_processor import TraceProcessor, TraceProcessorConfig

config = TraceProcessorConfig(
    bin_path="./tools/trace_processor",
)

with TraceProcessor(
    trace="trace.pftrace",
    config=config,
) as tp:
    rows = tp.query("""
        SELECT name, ts, dur / 1e6 AS dur_ms
        FROM slice
        WHERE dur >= 0
        ORDER BY dur DESC
        LIMIT 20
    """)
    for row in rows:
        print(row.name, row.ts, row.dur_ms)
```

`query()` 返回可迭代结果，SQL 的解析和执行由原生 Trace Processor 完成。把结果转换为 Pandas 或 Polars DataFrame 时，会在 Python 进程中物化结果，也就是把返回行实际装入内存数据结构。列数很多或行数很大的明细结果会增加内存占用和转换时间；聚合、过滤和列裁剪应尽量在 SQL 中完成。

`TraceProcessorConfig(bin_path=...)` 适合固定经过审核的原生程序。未指定时，官方包会使用与该 Python 包绑定的版本，只要包版本也被锁定，仍可复现；设置 `fetch_latest_trace_processor=True` 会尝试获取最新预编译程序，不适合作为稳定基线。

### BatchTraceProcessor

下面的程序查询目录中的多份 Trace，并保留每份结果：

```python
from pathlib import Path

from perfetto.batch_trace_processor.api import BatchTraceProcessor

paths = sorted(Path("traces").glob("*.pftrace"))
files = [str(path) for path in paths]

with BatchTraceProcessor(files) as btp:
    results = btp.query("""
        SELECT COUNT(*) AS slice_count
        FROM slice
    """)

for path, frame in zip(paths, results):
    print(path.name, int(frame["slice_count"].iloc[0]))
```

`query()` 返回与输入 Trace 一一对应的 DataFrame 列表。`query_and_flatten()` 会把各份结果纵向合并，并按所用解析器增加来源列。每份已加载 Trace 都完整驻留内存；官方给出的粗略估算是 `2 × 平均文件大小 × Trace 数量`，内容差异会让实际值明显偏离。官方文档提到可查询约千份 Trace，这只是使用规模示例，并非容量承诺；批大小要根据样本内容、主机内存和并发配置压测。

## traceconv 用于格式互操作

`traceconv` 用于格式互操作，可以把 Perfetto protobuf Trace 转为文本、Chrome JSON、systrace、压缩 systrace、pprof 或 Firefox Profiler 格式，也能处理原生符号、R8/ProGuard 混淆映射和压缩包。官方地址下载到的同样是 Python 3 启动脚本，原生程序会缓存在 Perfetto 预编译目录。

下面的命令下载工具，并展示几种经过 Android 17 源码与当前文档核对的模式：

```bash
curl -LO https://get.perfetto.dev/traceconv
chmod +x ./traceconv

./traceconv text trace.pftrace trace.textproto
./traceconv json trace.pftrace trace.json
./traceconv systrace trace.pftrace trace.html
./traceconv profile --output-dir ./profiles trace.pftrace
./traceconv bundle trace.pftrace trace.bundle.tar
```

`profile` 会生成一个或多个 pprof 文件，因此使用 `--output-dir`。`bundle` 要求输入和输出都是实际文件路径；它把 Trace、原生符号和 R8/ProGuard 映射整理成可由 UI 或 Trace Processor 直接打开的 TAR，便于连同符号化资料一起分享和归档。文本与 JSON 输出可能远大于原始 protobuf；格式转换解决的是工具兼容问题，不能降低超大 Trace 的解析内存需求。

## 可复现的分析流水线

持续分析不能只保留一个指标 CSV。每份样本至少要有一份可审计清单，用来追溯输入、环境、查询和输出，记录：

- Trace 文件 SHA-256；
- 设备构建指纹、Android 版本和 API 等级；
- 内核版本；本项目面向 Android 17 时以 `android17-6.18-2026-06_r6` 为内核侧基线；
- Perfetto 采集配置全文或校验和；
- 场景名称、迭代编号、开始与结束判据；
- Trace Processor `--version` 输出和程序校验和；
- SQL 代码提交号、输出结构版本与单位。

这些字段应由采集与分析程序在运行时自动生成。手写设备构建、工具版本或哈希容易出现抄录错误，也会让测试环境变化难以与性能变化区分。

进入历史基线前，至少执行这些检查：

1. `stats` 中与目标数据源有关的数据丢失和解析错误已判定；
2. 必需表、标准库模块和自定义标记存在；
3. 测试场景成功，测量窗口由可复核事件限定；
4. SQL 对目标 Trace Processor 版本有回归测试；
5. 单位在字段名或结构版本中明确，跨版本列变更已有迁移；
6. 缺失值、零值和查询错误分开存储；
7. 每份 Trace 保留独立结果，再计算分位数和置信区间；置信区间用于表达样本估计值的不确定范围。

阈值告警应来自稳定基线和已知噪声分布。P95/P99 分别表示 95%/99% 的样本不超过该值；只有在样本量、设备状态、温度、电量、编译产物和测试步骤受控时，这些分位数才有可比性。

## 原生工具也内存不足时

按下面的顺序处理：

1. 回到采集端缩短时间窗口，只覆盖可复核的测试区间；
2. 减少与问题无关的数据源、atrace 类别和高频事件；
3. 长时间观测使用 ring buffer 或 long trace 配置，保留所需历史；
4. 不需要通用 ftrace 原始表时评估 `--no-ftrace-raw`；
5. 多份 Trace 改为顺序或小批加载，按主机峰值内存设批大小；
6. 单机方案完成容量测试后，再评估 BigTrace 这类分布式大规模 Trace 分析方案。

拆批只减少多文件同时驻留内存的数量。单份 Trace 仍然过大时，需要重新采集或换用内存更大的分析主机；Python `TraceProcessor` 和 `BatchTraceProcessor` 都不会只加载查询涉及的 Track。

## Android 17 源码落点

`android-17.0.0_r1` 的 `external/perfetto` 已包含下列接口：

- `src/trace_processor/trace_processor_shell.cc` 定义子命令入口、公共参数和旧接口转换层；
- `src/trace_processor/shell/query_subcommand.cc` 处理内联 SQL、文件、标准输入和多语句入口；
- `src/trace_processor/shell/query.cc` 检查单结果集约束并生成 CSV；
- `src/trace_processor/shell/server_subcommand.cc` 实现 HTTP 和标准输入输出 RPC 服务；
- `src/trace_processor/shell/export_subcommand.cc` 实现 SQLite 导出；
- `src/traceconv/main.cc` 定义 `text`、`json`、`systrace`、`ctrace`、`profile`、`bundle` 等模式。

这些源码位置证明相应命令在 Android 17 锚点中存在。主机上从 `get.perfetto.dev` 获取的程序可能更新得更快，运行时能力仍以本机 `--version`、子命令 `--help` 和流水线固定版本的行为测试为准。

## 常见误区

**原生后端会让超大 Trace 变成低内存查询吗？**

不会。它解除浏览器站点内存限制并使用原生代码执行，Trace Processor 仍需摄取和维护查询所需的数据结构。

**D 状态就是磁盘 I/O 吗？**

不能这样下结论。D 只表示不可中断睡眠，还要检查 `io_wait`、`blocked_function`、内核事件与调用栈。

**Python API 的额外开销可以忽略吗？**

SQL 解析和执行在原生进程完成，结果传输与 DataFrame 物化仍有成本。查询返回大量行时，这部分可能成为内存和耗时主体。

**导出 JSON 能缓解文件过大吗？**

通常不能。JSON 和 protobuf 文本面向兼容与检查，输出经常更大。分析大文件应优先使用 Trace Processor，或在采集端控制数据量。

**Slice 名称匹配到就能作为跨版本指标吗？**

不能。名称可能来自平台实现、atrace 类别、Track Event 或应用自定义标记。指标必须说明来源、版本边界、线程归属和缺失时的处理规则。

## 参考资料

- [Visualising large traces](https://perfetto.dev/docs/visualization/large-traces)
- [Trace Processor（C++）](https://perfetto.dev/docs/analysis/trace-processor)
- [PerfettoSQL 入门](https://perfetto.dev/docs/analysis/perfetto-sql-getting-started)
- [PerfettoSQL 内置表](https://perfetto.dev/docs/analysis/sql-tables)
- [Trace Processor（Python）](https://perfetto.dev/docs/analysis/trace-processor-python)
- [Batch Trace Processor](https://perfetto.dev/docs/analysis/batch-trace-processor)
- [traceconv](https://perfetto.dev/docs/quickstart/traceconv)
- [Android 17 trace_processor_shell.cc](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/trace_processor_shell.cc)
- [Android 17 query_subcommand.cc](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/shell/query_subcommand.cc)
- [Android 17 query.cc](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/shell/query.cc)
- [Android 17 server_subcommand.cc](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/shell/server_subcommand.cc)
- [Android 17 export_subcommand.cc](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/shell/export_subcommand.cc)
- [Android 17 traceconv/main.cc](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/traceconv/main.cc)
