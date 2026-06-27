---
title: "命令行打开超大 Trace"
chapter: "13.4"
section: "13.4"
status: finalized
drafted_date: "2026-04-03"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-27"
last_verified_against: "AOSP external/perfetto trace_processor_shell.cc + Perfetto docs/python api"
confidence: medium
sources:
  - type: official
    path: "https://perfetto.dev/docs/analysis/trace-processor"
  - type: official
    path: "https://perfetto.dev/docs/analysis/trace-analysis-with-sql"
  - type: official
    path: "https://perfetto.dev/docs/analysis/batch-trace-processor"
  - type: aosp
    path: "external/perfetto/src/trace_processor/"
tags: [perfetto, trace_processor, sql, python, cli, large-traces]
related_chapters: ["13.1", "13.2", "13.3", "13.5"]
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed
task6_state: reviewed
task6_result: pass-light-edit
reviewed_date: "2026-04-27"
reviewed_by: openclaw-task6
pipeline_stage: ready-to-publish
task9_reviewed_date: "2026-04-28"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-04-28T06:20:00+08:00"
last_task2b_at: "2026-04-27T12:54:09+08:00"
task9_review_notes: "2026-04-28 task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 2。"
last_task6_audit: "2026-06-27"
last_task9_audit: "2026-06-11"
last_task9_audit_log: "logs/deep-review/2026-06-11-16-audit.md"
deepseek_polish_state: done
last_deepseek_polish_at: 2026-05-27
---

# 命令行打开超大 Trace

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 大 Trace 的挑战：几百 MB 到 GB 级别，浏览器内存不足
- 🔹 trace_processor：命令行交互式查询工具
- 🔹 Perfetto SQL 查询基础：tables、views、常用查询模式
- 🔹 用 trace_processor 批量跑 SQL 脚本
- 🔹 用 Python 的 perfetto.trace_processor 库做自动化分析

### 扩展（可选深入）

- 🔸 traceconv 转换工具
- 🔸 自建 Perfetto 分析 Pipeline 的实践

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要用命令行分析 Trace

我们在上一节里用 Perfetto UI 打开 Trace、看 Track、看 Slice，体验很流畅。但当我们遇到一个 500MB 甚至 2GB 的 Trace 文件时，情况就不一样了——浏览器标签页开始疯狂吃内存，UI 变得卡顿甚至直接崩溃。瓶颈出在浏览器的 WebAssembly（WASM）引擎——处理如此大的数据集时它力不从心。

更常见的一个场景是：我们需要对一批 Trace 做批量分析，比如每天自动抓取 50 个冷启动 Trace，统计 P95 启动时间。手动一个个打开 UI 不现实，我们需要一个可以用脚本驱动、不依赖浏览器的分析工具。

Perfetto 官方为我们准备的就是 `trace_processor`——一个 C++ 实现的命令行工具，它能把 Trace 文件当作数据库来查询。我们写 SQL，它返回结果。它会把 Trace 中的每一类事件解析成结构化的表（`slice`、`sched`、`counter`……），然后我们直接用 SQL 去查。

还有一个经常被忽略的好处是**隐私**。`trace_processor` 是本地工具，Trace 文件完全在本地解析，不需要上传到任何云端。对于包含敏感信息的系统级 Trace，这种本地解析方式更稳妥。

## 大 Trace 的挑战：浏览器为什么扛不住

[已验证: 官方文档, perfetto.dev/docs/analysis/trace-processor]

Perfetto UI（ui.perfetto.dev）是在浏览器里运行一个由 C++ 编译成的 WebAssembly 模块。这个模块负责解析 protobuf 格式的 Trace 数据，构建内存中的 SQL 数据库，然后在 UI 上渲染各种 Track。

当 Trace 文件在几十 MB 以内时，这套流程工作得很好。但当 Trace 超过 200MB，问题开始出现：

浏览器对单个标签页的内存有限制（Chrome 通常是 2-4GB），而解析一个大 Trace 本身就需要大量内存——原始 protobuf 数据、解析后的 SQL 表、UI 渲染用的数据结构，加起来往往是原始文件大小的 3-5 倍。一个 500MB 的 Trace 轻松就能吃掉 1.5GB 以上的浏览器内存。

另外，Perfetto UI 加载 Trace 时是先把整个文件读入内存，再逐步解析。加载完成之前，UI 通常会冻结，我们看到的往往只是一个转圈圈的进度条。

而 `trace_processor` 作为原生 C++ 二进制文件，没有浏览器的内存沙箱限制，可以直接使用操作系统的全部可用内存。同样的 500MB Trace，在命令行下通常能更快速、更稳定地完成解析和查询。

## trace_processor：命令行交互式查询工具

[已验证: 官方文档, perfetto.dev/docs/analysis/trace-processor]

### 下载与安装

Perfetto 官方提供了预编译的二进制文件，支持 Linux、macOS 和 Windows：

```bash
# Linux / macOS
curl -LO https://get.perfetto.dev/trace_processor
chmod +x ./trace_processor
```

[已验证: 官方文档, get.perfetto.dev]

这个二进制文件是自包含的，不依赖任何外部库，下载后直接运行即可。

### 基本使用：交互式查询

加载一个 Trace 文件进入交互式 SQL shell：

```bash
./trace_processor my_trace.perfetto-trace
```

这会启动一个交互式命令行，提示符变成 `sql>`。在这个 shell 里，我们可以直接写 SQL 查询 Trace 数据。几个关键的元命令（不是 SQL，是 shell 自带的命令）我们需要先知道：

`.tables` 列出当前 Trace 中所有可用的表。这是我们拿到一个陌生 Trace 后的第一步——先看看有哪些数据可用：

```
sql> .tables
args                cpu_freq              process_tree         slice
binder_tx           counter               sched                thread_state
cpu_active          cpu_track             thread               track
...
```

`.schema <表名>` 查看某个表的列定义。比如我们想查 `slice` 表有哪些字段：

```
sql> .schema slice
```

它会返回完整的 CREATE TABLE 语句，告诉我们每列的名称和类型。

`.read <文件>` 从外部 `.sql` 文件批量执行查询。对于复杂的分析脚本，我们会把 SQL 写到文件里，然后用 `.read` 一次性执行。

`.quit` 或 `.q` 退出 shell。

### 两种工作模式

`trace_processor` 主要有两种工作模式。

**交互模式**就是上面说的，直接启动 shell 手动查询，适合探索性的分析——我们对 Trace 里有什么还不太确定，想先看看。

**HTTP 守护进程模式**则更适合配合 Perfetto UI 使用。启动时加 `--httpd` 参数：

```bash
./trace_processor --httpd /path/to/trace.perfetto-trace
```

这会在本地启动一个 HTTP 服务（默认监听 `127.0.0.1:9001`）。然后我们打开 ui.perfetto.dev，浏览器会弹窗询问是否连接到本地 trace processor，选"YES"后，UI 就不再自己解析 Trace 了——它把 SQL 查询发给本地的 `trace_processor` 进程，由 C++ 后端完成解析和计算，UI 只负责展示结果。

这个模式的好处是：我们同时拥有了命令行的分析能力和 UI 的可视化能力。对于大 Trace 文件，这是推荐的工作方式。

## Perfetto SQL 查询基础

[已验证: 官方文档, perfetto.dev/docs/analysis/trace-analysis-with-sql]

PerfettoSQL 建立在 SQLite 引擎之上，语法与标准 SQL 基本一致。但 Perfetto 在此基础上扩展了一些专有语法（如 `CREATE PERFETTO VIEW`、`CREATE PERFETTO MACRO`），并提供了一组专门用于 Trace 分析的表和函数。

### 核心概念：时间戳、Slice、Counter、Track

在写查询之前，我们需要理解 Perfetto 对 Trace 数据的抽象方式。

所有时间戳都以**纳秒**为单位。它从某个起始点开始单调递增（通常是 BOOTTIME 时钟），不同于 wall clock time。所以我们可以直接对时间戳做减法得到持续时长，但不能把它直接当成“几点几分”这样的时钟时间。

**Slice** 是一个时间段，表示"某个操作从什么时候开始、持续了多久"。比如主线程上一次 `measure` 操作、一个 Binder 调用的耗时、一次 GC 过程，在 Perfetto 中都是一个 Slice。

**Counter** 是一个随时间变化的数值。比如 CPU 频率、内存使用量、帧率。Counter 没有持续时间的概念，它只是在某个时间点记录了一个值。

**Track** 是同一类型、同一上下文的事件集合。可以理解成 Perfetto UI 中的一行——CPU 0 的调度事件在一条 Track 上，主线程的 Slice 在另一条 Track 上。

### 常用表速览

我们不需要记住所有表，但以下几张表是分析中最常用的：

`slice` 表是使用频率最高的。它记录了所有的 Slice 事件，核心列包括 `ts`（开始时间戳）、`dur`（持续时长，纳秒）、`name`（Slice 名称）、`track_id`（所属 Track）。如果我们想查"主线程上耗时最长的 10 个操作"，查的就是这张表。

`sched` 表记录了 CPU 调度事件——哪个线程在哪个 CPU 核心上跑了多久。它是分析 CPU 使用、线程迁移、调度延迟的核心数据源。

`thread` 和 `process` 表提供了线程和进程的元信息。Perfetto 使用 `utid`（unique tid）和 `upid`（unique pid）来标识线程和进程，而不是系统原生的 `tid`/`pid`。这是因为系统级的 ID 会被复用——一个已退出的线程的 `tid` 可能被新线程拿走，直接用 `tid` 做 JOIN 会得到错误的结果。`utid` 和 `upid` 在一次 Trace 中是唯一且不变的。

`counter` 表存储了所有 Counter 事件，通过 `track_id` 关联到具体的 Counter Track。

### 使用前必做：验证事件是否存在

在写任何针对具体 Slice 名称的查询之前，先用一个简单查询确认目标事件在当前 Trace 中确实存在：

```sql
-- 查看当前 Trace 中有哪些 Slice 名称（采样前 50 条）
SELECT DISTINCT name FROM slice ORDER BY name LIMIT 50;

-- 或者在 EXTRACT_ARG 之前，先确认目标 Slice 存在
SELECT COUNT(*) FROM slice WHERE name = 'inflate';
```

这是因为很多 Slice 名称（如 `inflate`、`Application.onCreate`、`ActivityThread.handleBindApplication`、`ANR`）是否出现在 Trace 中，取决于采集时开启了哪些 atrace category 和应用是否打了自定义 Trace marker。如果查询返回空结果，多半是采集配置没有覆盖对应事件，而不是 SQL 本身写错了。

### 几个典型查询

下面通过几个实际查询来理解 PerfettoSQL 的用法。

**查询某个进程中耗时最长的 10 个 Slice：**

```sql
SELECT
  slice.name,
  slice.ts,
  slice.dur,
  slice.dur / 1e6 AS dur_ms
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread USING (utid)
JOIN process USING (upid)
WHERE process.name = 'com.example.app'
ORDER BY slice.dur DESC
LIMIT 10;
```

这个查询的逻辑是：从 `slice` 出发，通过 `track_id` 关联到 `thread_track`，再通过 `utid` 关联到 `thread`，最后通过 `upid` 关联到 `process`，然后按进程名过滤。`dur / 1e6` 把纳秒转换成毫秒，方便阅读。

**查询每个进程的 CPU 占用总时长：**

```sql
SELECT
  process.name AS process_name,
  SUM(sched.dur) / 1e9 AS total_cpu_sec
FROM sched
JOIN thread USING (utid)
JOIN process USING (upid)
GROUP BY process.name
ORDER BY total_cpu_sec DESC
LIMIT 20;
```

这里我们从 `sched` 表出发，关联到进程信息后，按进程名分组求和。`dur / 1e9` 把纳秒转换成秒。

**查询主线程在某个时间段内的 D 状态（Uninterruptible Sleep）时长：**

```sql
SELECT
  SUM(thread_state.dur) / 1e6 AS d_state_ms
FROM thread_state
JOIN thread USING (utid)
JOIN process USING (upid)
WHERE process.name = 'com.example.app'
  AND thread.name = 'main'
  AND thread_state.state = 'D'
  AND thread_state.ts >= 10e9      -- 从第 10 秒开始
  AND thread_state.ts < 20e9;     -- 到第 20 秒结束
```

`thread_state` 表记录了线程的状态变迁，`state = 'D'` 表示不可中断睡眠（通常是等 I/O）。这个查询帮助我们判断主线程是否在等磁盘 I/O。

### JOIN 的路径模式

PerfettoSQL 查询中最容易出错的部分是表之间的 JOIN 路径。一个常见的模式是：

- 要获取 Slice 所属的进程/线程信息：`slice` → `thread_track`（通过 `track_id`）→ `thread`（通过 `utid`）→ `process`（通过 `upid`）
- 要获取 Counter 所属的上下文：`counter` → 对应的 counter_track 表（`process_counter_track` 或 `cpu_counter_track`）→ 进一步关联到进程或 CPU

记住这条路径就够了：`slice → thread_track → thread → process`。绝大多数分析查询都是这条路径的变体。

[自动发现] Perfetto 还提供了一组辅助函数来简化 JOIN 操作。`EXTRACT_ARG(arg_set_id, key)` 可以直接从 `args` 表中提取某个 Slice 的自定义属性，而不需要显式 JOIN `args` 表。比如查看 `sched_switch` ftrace 事件中被换出的前一个进程名：

```sql
SELECT
  name,
  EXTRACT_ARG(arg_set_id, 'prev_comm') AS prev_comm
FROM ftrace_event
WHERE name = 'sched_switch'
LIMIT 10;
```

> **注意**：`EXTRACT_ARG` 可用的 key 取决于对应事件的 `args` 表内容。使用前建议先查看 schema：`.schema args` 或 `SELECT DISTINCT key FROM args LIMIT 50`。
>
> 另外 `EXTRACT_ARG` 在大表上性能不如显式 JOIN——它每行都要执行一次子查询。对探索性分析没问题，但在批量脚本中如果性能敏感，建议改用 JOIN。

## 用 trace_processor 批量跑 SQL 脚本

当我们确定了查询逻辑后，下一步通常是把它固化成脚本，实现自动化分析。

### 用 `-q` 执行 SQL 文件

如果已经进入交互式 shell，可以用 `.read` 执行外部 SQL 文件。脚本场景里，更常用的是 `-q`：

```bash
./trace_processor -q my_analysis.sql trace.perfetto-trace
```

`-q` 模式下，`trace_processor` 不会进入交互式 shell，而是执行完 SQL 文件后直接退出，结果输出到 stdout。`trace_processor --help` 也明确写了 `-q/--query-file` 只是“从文件读取并执行 SQL 查询”。这里只需要记一条规则：SQL 文件里可以有多个语句，但允许返回结果的只能是末尾那条语句；如果前面已经有 `SELECT` 产出行，CLI 会直接报错。

### 一个完整的批量分析脚本示例

假设需要对每个 Trace 统计：主线程总运行时长、GC 次数、ANR 数量。`analyze_trace.sql` 可以写成一个最终 `SELECT`：

```sql
SELECT 'main_thread_cpu_ms' AS metric,
       COALESCE(SUM(sched.dur) / 1e6, 0) AS value
FROM sched
JOIN thread USING (utid)
WHERE thread.is_main_thread = 1

UNION ALL

SELECT 'gc_count' AS metric,
       COUNT(*) AS value
FROM slice
WHERE name LIKE '%GC%'

UNION ALL

SELECT 'anr_count' AS metric,
       COUNT(*) AS value
FROM slice
WHERE name = 'ANR';
```

然后用一个 shell 脚本遍历所有 Trace 文件：

```bash
#!/bin/bash
TRACE_DIR="/data/traces/daily"
TRACE_PROCESSOR="./trace_processor"
SQL_FILE="analyze_trace.sql"

echo "trace_file,metric,value"
for trace in "$TRACE_DIR"/*.perfetto-trace; do
  filename=$(basename "$trace")
  tmp_csv=$(mktemp)
  "$TRACE_PROCESSOR" -q "$SQL_FILE" "$trace" > "$tmp_csv"
  python3 - "$filename" "$tmp_csv" <<'PY'
import csv
import sys

trace_name, csv_path = sys.argv[1], sys.argv[2]
with open(csv_path, newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(f"{trace_name},{row['metric']},{row['value']}")
PY
  rm -f "$tmp_csv"
done
```

这里 trace 文件要作为位置参数传给 `trace_processor`，`-q` 只负责指定 SQL 文件。非交互模式下的查询结果是带表头的 CSV。做最小验证时优先使用长参数 `--query-string`，例如 `trace_processor --query-string "select 1 as a, 2 as b" trace.perfetto-trace`；如果手头的发行版没有开放 query-string 参数，就把查询写入临时 `.sql` 文件后用 `-q` 执行。输出是标准 CSV，例如 `"a","b"` 和 `1,2` 两行，分隔符不会变成 `|` 或制表符。

### 查询结果的格式控制

批处理时先把输出理解成 CSV。交互式 shell 里看到的是排版后的表格，两者不要混用。如果需要更稳定的结构化结果，有三种方案：

**方案一：Python API**（推荐，灵活性最高）

前面介绍的 Python `TraceProcessor.query().as_pandas_dataframe()` 可以直接拿到结构化数据，导出为 CSV、JSON 或 Parquet 都很方便。

**方案二：导出为 SQLite 数据库**

```bash
./trace_processor -q analysis.sql -e result.sqlite trace.perfetto-trace
```

`-e` 参数会把 trace_processor 的内存数据库导出为 SQLite 文件，之后可以用任意 SQLite 工具查询，也可以用 `sqlite3` 命令行的 `.mode json` 输出 JSON。

**方案三：shell 脚本后处理**

如果只想留在 shell，按 CSV 解析就够了。可以用 Python `csv`、`xsv`、`mlr --icsv --ocsv` 这一类工具，不要假设分隔符是 `|` 或制表符。

### trace_processor 的高级参数

一些实用的启动参数：

`--httpd` 启动 HTTP 守护进程模式，配合 Perfetto UI 使用。前面已经讲过。AOSP `external/perfetto` 版本公开的 HTTP 参数包含 `--http-port PORT`；不要在教程里假设存在 `--http-ip-address`。如果使用的是独立上游二进制，先以 `trace_processor --help` 的本机输出为准。

`-W` 或 `--wide` 加宽输出列宽，让长字符串（如完整 Slice 名称）不被截断。在交互式查询中查看长名称时很有用。

`-e <path>` 将内存中的数据库导出为 SQLite 文件。分析完成后可以把整个 Trace 数据库持久化，后续用 `sqlite3` 命令行或其他工具继续分析，不用重新加载原始 Trace。

[已验证: perfetto.dev docs + trace_processor shell v52.0 --help / 最小查询, 2026-04-22]

## 用 Python 的 perfetto.trace_processor 库做自动化分析

[已验证: 官方文档, perfetto.dev/docs/analysis/batch-trace-processor]

当分析逻辑变得复杂——比如需要多步查询、结果需要进一步计算、要生成图表——shell 脚本就开始力不从心了。这时更适合切到 Python，用 Perfetto 官方提供的 Python API 组织查询和后处理。

### 安装

```bash
pip install perfetto
pip install pandas  # 推荐安装，用于 DataFrame 输出
```

Perfetto Python API 要求 Python 3，底层仍然调用 C++ 的 `trace_processor` 库，所以性能不会因为用了 Python 而变差。

### 基本使用

[已验证: 官方文档, perfetto.dev/docs/analysis/trace-processor#python-api]

```python
from perfetto.trace_processor import TraceProcessor

# 加载 Trace 文件
tp = TraceProcessor(trace='my_trace.perfetto-trace')

# 执行 SQL 查询
qr_it = tp.query('SELECT name, dur / 1e6 AS dur_ms FROM slice ORDER BY dur DESC LIMIT 10')

# 迭代结果
for row in qr_it:
    print(f'{row.name}: {row.dur_ms:.2f} ms')

# 或者直接转成 Pandas DataFrame
df = tp.query('SELECT ts, dur, name FROM slice').as_pandas_dataframe()
print(df.head())
```

`tp.query()` 返回的是迭代器，不是一次性加载所有结果的列表。这样设计，是为了处理可能很大的查询结果集。结果不大时，直接迭代就行；如果准备交给 Pandas 做后续分析，再用 `as_pandas_dataframe()` 一次性转成 DataFrame。

### 实战：冷启动分析脚本

下面是一个实际可用的脚本，用来统计一批冷启动 Trace 的关键指标：

```python
import glob
from perfetto.trace_processor import TraceProcessor

def analyze_cold_start(trace_path):
    """分析单个 Trace 的冷启动指标"""
    tp = TraceProcessor(trace=trace_path)

    # 1. 找到启动阶段关键 Slice 的耗时
    # 注意：这些 slice name 来自 atrace 的 gfx/input/view category + 应用自定义 Trace marker，
    # 采集时必须开启对应 category 才能查到
    oncreate = tp.query("""
        SELECT dur / 1e6 AS dur_ms
        FROM slice
        WHERE name = 'Application.onCreate'
        LIMIT 1
    """).as_pandas_dataframe()

    # 2. 统计主线程在启动期间的 D 状态时长
    # 先定位启动起点（handleBindApplication 通常是系统侧标记），
    # 如果该 slice 不存在，可以退而用 trace 开头时间作为起点
    startup_start = tp.query("""
        SELECT COALESCE(
          (SELECT MIN(ts) FROM slice WHERE name = 'ActivityThread.handleBindApplication'),
          (SELECT MIN(ts) FROM slice LIMIT 1)
        ) AS ts
    """).as_pandas_dataframe()

    # 2b. 用 startup_start 计算 D 状态时长
    if len(startup_start) > 0 and startup_start['ts'].iloc[0] is not None:
        start_ts = startup_start['ts'].iloc[0]
        d_state = tp.query(f"""
            SELECT SUM(dur) / 1e6 AS d_state_ms
            FROM thread_state
            JOIN thread USING (utid)
            WHERE thread.is_main_thread = 1
              AND state = 'D'
              AND ts >= {start_ts}
              AND ts < {start_ts} + 5e9
        """).as_pandas_dataframe()
    else:
        d_state = None

    # 3. 统计启动阶段主线程的 Binder 调用次数
    # 注意：binder slice name 格式取决于 atrace 配置，不同版本可能有差异
    binder_count = tp.query("""
        SELECT COUNT(*) AS cnt
        FROM slice
        JOIN thread_track ON slice.track_id = thread_track.id
        JOIN thread USING (utid)
        WHERE thread.is_main_thread = 1
          AND slice.name LIKE 'binder%'
          AND slice.ts < (SELECT MIN(ts) + 5e9 FROM slice
                          WHERE name = 'ActivityThread.handleBindApplication')
    """).as_pandas_dataframe()

    tp.close()

    return {
        'oncreate_ms': oncreate['dur_ms'].iloc[0] if len(oncreate) > 0 else None,
        'd_state_ms': d_state['d_state_ms'].iloc[0] if d_state is not None and len(d_state) > 0 else 0,
        'binder_calls': binder_count['cnt'].iloc[0] if len(binder_count) > 0 else 0,
    }

# 批量分析
traces = glob.glob('traces/cold_start_*.perfetto-trace')
results = []
for t in traces:
    metrics = analyze_cold_start(t)
    metrics['trace'] = t
    results.append(metrics)

import pandas as pd
df = pd.DataFrame(results)
print(df.describe())  # 统计 P50/P95/P99
```

这个脚本做了三件事：提取 `Application.onCreate` 的耗时、统计主线程 D 状态时长（反映 I/O 瓶颈）、统计启动阶段的 Binder 调用次数。三个指标分别反映了启动过程的三个不同维度：代码执行、I/O 等待、IPC 开销。

### 批量分析：BatchTraceProcessor

[已验证: 官方文档, perfetto.dev/docs/analysis/batch-trace-processor]

当需要同时分析多个 Trace 文件时，Perfetto 提供了 `BatchTraceProcessor`，它在底层管理多个 `trace_processor` 实例的生命周期：

```python
from perfetto.batch_trace_processor.api import BatchTraceProcessor

files = glob.glob('traces/*.perfetto-trace')

with BatchTraceProcessor(files) as btp:
    # 对每个 Trace 执行同一个查询，返回 DataFrame 列表
    results = btp.query('SELECT COUNT(*) AS slice_count FROM slice')
    for i, df in enumerate(results):
        print(f'{files[i]}: {df["slice_count"].iloc[0]} slices')
```

`BatchTraceProcessor` 会为每个 Trace 文件启动一个 `trace_processor` 实例。当 Trace 数量较多（几十个以上）时，需要注意内存消耗——每个实例都会在内存中维护一份完整的 SQL 数据库。如果遇到内存不足，可以分批处理，或者考虑使用 Perfetto 的 Bigtrace 分布式方案（适用于需要分析数千个 Trace 的场景）。

### TraceProcessorConfig

默认情况下，Python API 不把 ftrace 原始数据加载到 `ftrace_event` 表中（为了节省内存）。如果我们需要查 ftrace 级别的数据，需要手动开启：

```python
from perfetto.trace_processor import TraceProcessor, TraceProcessorConfig

config = TraceProcessorConfig(ingest_ftrace_in_raw=True)
tp = TraceProcessor(trace='trace.perfetto-trace', config=config)
```

[已验证: 官方文档, perfetto.dev/docs/analysis/trace-processor#python-api]

## traceconv：格式转换工具

[已验证: 官方文档, perfetto.dev/docs/analysis/traceconv]

在有些场景下，我们需要把 Perfetto 的 protobuf 格式 Trace 转成其他格式。比如需要在 `chrome://tracing` 中打开，或者需要人类可读的文本格式做快速检查。

Perfetto 提供了 `traceconv` 工具（早期叫 `trace_to_text`）：

```bash
# 下载
curl -LO https://get.perfetto.dev/traceconv
chmod +x traceconv

# 转为 protobuf text 格式（人类可读）
./traceconv text trace.perfetto-trace output.txt

# 转为 Chrome JSON 格式（可在 chrome://tracing 打开）
./traceconv json trace.perfetto-trace output.json

# 转为 systrace 文本格式（兼容旧版 Android systrace 工具）
./traceconv systrace trace.perfetto-trace output.txt

# 提取 heapprofd 的 profile 数据为 pprof 格式
./traceconv profile trace.perfetto-trace heap_profile.pb
```

其中 `text` 格式输出的是 protobuf 的文本序列化形式，每个事件一行，适合用 `grep`、`awk` 等文本工具做快速过滤。`json` 格式则是 Chrome Trace Event 格式，可以直接拖入 `chrome://tracing` 查看。

需要注意：对于大 Trace 文件，`traceconv` 转换过程本身也需要相当的时间和内存。特别是 `json` 格式，输出文件可能比原始 protobuf 大好几倍。建议只在确实需要其他工具兼容时才做转换，日常分析直接用 `trace_processor` 更高效。

## 自建 Perfetto 分析 Pipeline 的实践建议

[已验证: 官方文档, perfetto.dev/docs/analysis/batch-trace-processor]

当我们的分析需求从"偶尔查一个 Trace"演进到"每天自动分析几十个 Trace 并出报告"时，就需要搭建一个分析 Pipeline。这里分享一些实践经验。

### 结果存储与趋势追踪

每次分析的结果应该持久化存储（SQLite、CSV、或者时序数据库），这样才能做趋势对比。最省事的做法，是每次分析结果写入带日期列的 CSV，再用 Pandas 看趋势：

```python
import pandas as pd
from datetime import date

# 追加今天的分析结果
today = date.today().isoformat()
df = pd.DataFrame(results)
df['date'] = today
df.to_csv('metrics_history.csv', mode='a', header=False, index=False)

# 读取历史数据，看趋势
history = pd.read_csv('metrics_history.csv')
recent = history[history['date'] >= '2026-03-01']
print(recent.groupby('date')['oncreate_ms'].describe())
```

### SQL 查询的版本管理

分析用的 SQL 文件应该纳入版本控制（Git）。原因是：Perfetto 的表结构在不同版本之间可能变化——比如 Android 14 新增的 `power_rail` 表在 Android 12 的 Trace 里不存在。我们的查询逻辑也需要随着 Trace 格式演进。

### 查询性能优化

对大 Trace 做查询时，几个优化点值得记住：

在 WHERE 子句中尽量缩小时间范围。Perfetto 的底层存储是按时间排序的列式存储，带时间范围的查询可以利用时间索引快速跳过不相关的数据块。

避免 `SELECT *`。只查需要的列，减少内存占用。

`EXTRACT_ARG` 函数虽然方便，但在大表上性能不如显式 JOIN。生产脚本中建议用 JOIN 替代。

如果查询涉及 `GROUP BY` + `SUM`，可以先加 `WHERE` 条件过滤，再做聚合，而不是先全量聚合再过滤。

### 与 CI/CD 集成

如果团队有自动化测试流程（比如每天跑一次启动性能测试），可以把 Perfetto 分析脚本集成到 CI 中：

1. 测试完成后自动抓取 Trace
2. 用 `trace_processor -q` 执行分析 SQL
3. 把结果写入数据库
4. 如果关键指标超过阈值，自动发告警

这样性能回归就能在第一时间被发现，而不是等用户投诉。

## 常见问题与误区

**"trace_processor 能完全替代 Perfetto UI 吗？"**

不能，也不应该。两者是互补关系。`trace_processor` 擅长精确的数值查询和批量分析，Perfetto UI 擅长可视化——看 Track 上的时间分布、看 Slice 的嵌套关系、看多个 Track 之间的时间关系。实际工作里，通常先用 `trace_processor` 做初步筛选和指标提取，发现可疑区域后，再用 UI 上的 HTTP 守护进程模式打开同一个 Trace 做深入可视化分析。

**"Python API 是不是比命令行慢？"**

不是。Python API 底层调用的仍然是 C++ 的 `trace_processor` 库，数据解析和 SQL 执行都在 C++ 层完成。Python 层只负责发送 SQL 和接收结果，这层开销几乎可以忽略。

**"Trace 文件太大，trace_processor 也吃不下怎么办？"**

可以尝试几种方法：一是抓 Trace 时缩小时间范围，只保留要分析的窗口；二是用 ring buffer 模式抓取，只保留最近的数据；三是减少 atrace category 和高开销 data source；四是把多份文件拆批交给 `BatchTraceProcessor`；五是在更大规模场景下改用 Bigtrace。Python `TraceProcessor` / `BatchTraceProcessor` 都会 ingest 整个 trace，不支持按 track 局部加载。

**"PerfettoSQL 和标准 SQL 有什么区别？"**

语法上 95% 是一样的——SELECT/FROM/WHERE/JOIN/GROUP BY/ORDER BY/LIMIT 完全一致。区别主要在两方面：一是 Perfetto 提供了一些扩展语法，如 `CREATE PERFETTO VIEW`、`CREATE PERFETTO MACRO`、以及 `SPAN_JOIN` 等专有操作符表；二是时间戳和持续时长都以纳秒为单位，做计算时需要注意单位转换。

## 参考资料

- Perfetto 官方文档 - Trace Processor: https://perfetto.dev/docs/analysis/trace-processor
- Perfetto 官方文档 - SQL 分析: https://perfetto.dev/docs/analysis/trace-analysis-with-sql
- Perfetto 官方文档 - Batch Trace Processor: https://perfetto.dev/docs/analysis/batch-trace-processor
- Perfetto 官方文档 - traceconv: https://perfetto.dev/docs/analysis/traceconv
- Perfetto SQL 表参考: https://perfetto.dev/docs/analysis/sql-tables
- AOSP 源码路径: external/perfetto/src/trace_processor/
