---
title: "Perfetto v57 状态轨道与版本边界"
chapter: "13.21"
status: finalized
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: ["Perfetto", "TrackEvent", "状态追踪", "版本边界"]
related_chapters: ["13.1", "13.9", "13.15", "13.16", "13.20"]
last_verified: "2026-08-13"
last_verified_against: "Perfetto v57.2 release (2026-07-07); android-17.0.0_r1"
confidence: high
sources:
  - type: official
    path: "https://github.com/google/perfetto/releases/tag/v57.1"
  - type: aosp
    path: "protos/perfetto/trace/track_event/track_event.proto (v57.1 tag)"
  - type: aosp
    path: "protos/perfetto/trace/track_event/state_descriptor.proto (v57.1 tag)"
---

# 13.21 Perfetto v57 状态轨道与版本边界

> Android 平台内置组件、Perfetto SDK 与开发机上的分析器分别升级，不能用“Android 17 支持 Perfetto v57”笼统概括。本文的平台基线固定为 Android 17 / API 37 / `android-17.0.0_r1`；state track 的功能基线是 v57.1，工具补丁基线是 v57.2。

## 三条版本线

`android-17.0.0_r1` 的 `external/perfetto/CHANGELOG` 顶部记录了一个尚未进入完整上游版本的 Android `aflags` 补丁。`aflags` 是 Android 的功能开关机制，用于让平台代码按 flag 启用或停用行为。紧接着的完整上游版本是 **v54.0（2026-02-27）**；同一 Android 标签下的 `track_event.proto` 只定义到 `TYPE_COUNTER = 4`，没有 `TYPE_STATE`。

Perfetto **v57.1** 于 2026 年 7 月 2 日发布，引入 state track 等能力。**v57.2** 于 7 月 7 日发布，是截至 2026-08-13 最新的 v57 补丁版；它只修复 Trace Processor 解析内嵌 proto descriptor 时的兼容问题，其他 v57 功能仍以 v57.1 发布说明为准。state track、journald 采集和新版 Trace Processor/UI 都属于上游版本线，不会自动升级设备中的 `/system/bin/perfetto`、`traced`、`traced_probes` 或 Android Framework API。

| 对象 | 采用的版本 | 在哪里运行 | 能否直接提供 v57 状态轨道 |
|---|---|---|---|
| Android 平台 Perfetto | `android-17.0.0_r1`：v54.0 加平台补丁 | Android 17 设备 | 不能；平台 proto 没有 `TYPE_STATE` |
| Perfetto v57.2 C++ SDK / Trace Processor / UI | `v57.2` tag | 应用、测试工具或开发机 | C++ 生产与解析路径可用；C high-level 与 Java API 另有版本限制 |

这个拆分会影响方案选择：

- 只升级开发机分析器：可以读取新版 schema（trace 的字段与类型定义）和 PerfettoSQL 标准库，但不会补出设备未录制的数据。
- 想在 trace 中得到原生 `state` 表：producer（生产事件的一端）和 Trace Processor（解析事件的一端）都要具备 v57 state track 能力。
- 只能依赖 Android 17 系统内置组件：继续使用 slice、instant、counter 等 v54 能力。即使自行写出 `TYPE_STATE`，也不能假定平台自带工具能够解释。

## State track 的数据模型

### Slice、counter 和 state 各自回答什么

| 轨道类型 | 数据形态 | 适合回答的问题 | 常见误用 |
|---|---|---|---|
| Slice | 开始、结束、可嵌套 | “这个操作执行了多久？” | 用大量首尾相接的 slice 模拟长期状态 |
| Counter | 时间戳加数值 | “这一刻的频率、字节数或队列深度是多少？” | 用整数枚举表达状态，却遗漏枚举表 |
| State | 时间戳加字符串状态，单轨道至多一个当前值 | “这个子系统在这段时间处于什么状态？” | 把同一时间可并存的多个活动塞进单条 state track |

state track 表达单值状态机：一条轨道在任一时刻最多有一个当前值，没有当前值时称为 idle。播放器的 `Buffering → Playing → Paused` 适合 state track。并行的下载任务、解码任务和渲染任务可以同时存在，应分别使用 slice 或多条轨道。

### v57.1 在 trace 二进制格式中增加了什么

v57.1 的 `TrackEvent.Type` 增加 `TYPE_STATE = 5`，v57.2 延续同一 wire format（序列化后的二进制字段格式）。事件的 `track_uuid` 是轨道的 64 位稳定标识，必须指向带 `StateDescriptor` 的轨道；descriptor 是描述轨道类型和属性的元数据。`StateDescriptor` 在 v57.1/v57.2 中是空消息，只负责把轨道标记为 state track。

状态字符串的实际编码走 TrackEvent 的事件名路径，即 `name` 或经过 string interning（把重复字符串换成整数 ID）的 `name_iid`。v57.2 `track_event.proto` 的枚举注释仍写着 `state` 字段，但 schema 已将原字段号 51 标为 `reserved`，表示该编号被保留且不能重新用作普通字段；C++ `TRACE_STATE` 也会把状态值交给事件名参数。手工生成 trace packet（单个 protobuf 事件数据包）时应以真实字段定义和 SDK 实现为准，不能照搬这条过时注释。空字符串或未设置事件名会结束当前状态，使轨道进入 idle。

下面节选只用于展示枚举边界，省略了 proto 中的大段注释和其他字段：

```protobuf
enum Type {
  TYPE_UNSPECIFIED = 0;
  TYPE_SLICE_BEGIN = 1;
  TYPE_SLICE_END = 2;
  TYPE_INSTANT = 3;
  TYPE_COUNTER = 4;
  TYPE_STATE = 5;
}
```

Android 17 标签中的同一枚举止于 `TYPE_COUNTER = 4`。`TYPE_STATE = 5` 只说明 v57 的二进制格式已经分配这个枚举值，不代表每种语言 SDK 都同时提供了高层方法；看到 API 37 或 Android 17 也不能推出设备自带 v57 状态轨道。

### Trace Processor 如何形成持续时间

v57.2 的 `StateTracker::UpdateState()` 展示了几条容易遗漏的语义：

- 新值与当前值不同：关闭旧行，把 `dur` 写成两次状态事件的时间差，再创建新行；
- 新值与当前值相同：不创建新行，只把新参数附加到当前状态；
- 新值为空：关闭旧行，不创建 idle 行；
- 尚未被下一次转换或清空关闭的行以 `dur = -1` 暂存；`-1` 是“持续时间尚未确定”的哨兵值。

这也解释了为什么查询 `state` 表时不应再用 `LEAD(ts)` 计算时长。`LEAD()` 是读取下一行值的 SQL 窗口函数；Trace Processor 已经维护 `dur`，手工用下一行时间戳相减会忽略相同状态合并、显式清空和开放区间的语义。

## 写入 state 事件

### C++ SDK

下面的片段展示一个状态轨道上的三次转换。类别注册、Tracing 初始化和 session 配置沿用 Perfetto SDK 的常规写法，此处省略：

```cpp
perfetto::StateTrack player_state("Player state");

TRACE_STATE("player", "Buffering", player_state);
TRACE_STATE("player", "Playing", player_state);
TRACE_STATE("player", "", player_state);  // 清空当前状态，进入 idle
```

第三次调用传入空字符串，作用是关闭 `Playing` 并进入 idle。同一逻辑轨道应复用稳定的 `StateTrack` 身份，也就是每次更新都指向同一 `track_uuid`。状态值应来自受控枚举；cardinality（基数）表示可能出现的不同取值数量，把请求 ID、文件名等高 cardinality 字符串作为状态，会制造大量难以聚合的值，也会增加 trace 体积。

### 上游 `main` 的 C high-level API

下面的调用展示上游提交 #6464 加入的 C high-level API（用宏封装底层 C ABI 的接口）形态，用于向已经注册的状态轨道写入 `Buffering`。该提交位于 v57.2 之后的 `main` 分支，示例只适用于包含这次变更的 commit（源码提交）或后续明确收录它的版本：

```c
PERFETTO_TE(player, PERFETTO_TE_STATE("Buffering"),
            PERFETTO_TE_REGISTERED_TRACK(&player_state_track));
```

`player_state_track` 的声明和注册必须使用状态轨道 API 完成。普通 counter 或 named track 的 descriptor 不会把轨道标记为 state，不能传给状态事件。v57.2 的公开 C 头文件还没有 `PERFETTO_TE_STATE`、`PerfettoTeStateTrackRegister` 等符号，因此这段代码不能按 v57.2 tag 编译；依赖必须锁定到实际包含 #6464 的版本或 commit。

### Android Java SDK 的 release tag 差异

v57.1 发布了 state track，但各语言 SDK 的高层 API 并未在同一个 release tag 中全部到位。源码核查得到下面的版本差异：

- `v57.1` 与 `v57.2` tag 下的 `src/android_sdk/.../PerfettoTrace.java` 只公开 slice、instant 和 counter 的事件类型，未出现 `TYPE_STATE` 或 `state(...)`；
- 上游 `main` 的 `sdk: add state track event support (C HL API + Java SDK)` 提交 #6464 才加入 `PerfettoTrace.state(...)`、state track builder、C high-level API 和 JNI（Java 与 C/C++ 之间的调用桥梁）路径；
- release tag 与该变更所在分支已经分开，不能把 `main` 上的方法签名写成 v57.1/v57.2 已发布 API。

工程上应以项目解析到的 Java artifact（构建工具实际下载的库文件）和源码 commit 为准：锁定依赖，查看 `PerfettoTrace` 公共方法并做一次编译验证。若 artifact 没有 state API，可以改用 v57.2 C++ SDK，或等待所采用的 Java SDK 版本明确包含该变更。文档中的 Java 示例也必须由所声明的依赖版本实际编译通过。

## 查询 `state` 表

### 先确认分析器版本和表结构

Android 17 自带的 v54 Trace Processor 不认识 `state` 表。使用 v57.1 或更高的兼容分析器打开 trace 后，可以先执行下面的结构查询。`PRAGMA table_info(...)` 是 SQLite/PerfettoSQL 用来列出表或视图字段的命令：

```sql
PRAGMA table_info(state);
```

v57.2 的公开 view（由 SQL 查询定义、读取时计算的表状结果）包含 `id`、`ts`、`dur`、`track_id`、`category`、`value` 和 `arg_set_id`。`ts` 与 `dur` 的单位都是纳秒，`arg_set_id` 可关联该状态附带的参数。状态列名是 `value`，不存在名为 `state` 的列。

### 查询转换与已观测时长

下面的查询列出状态转换，并把 trace 结束时仍开放的 `dur = -1` 行裁剪到 `trace_bounds.end_ts`。`trace_bounds` 给出当前 trace 中数据的起止时间边界：

```sql
SELECT
  t.name AS track_name,
  s.ts,
  s.value,
  s.category,
  CASE
    WHEN s.dur = -1 THEN b.end_ts - s.ts
    ELSE s.dur
  END AS observed_dur_ns,
  ROUND(
    (CASE WHEN s.dur = -1 THEN b.end_ts - s.ts ELSE s.dur END) / 1e6,
    3
  ) AS observed_dur_ms,
  s.arg_set_id
FROM state AS s
JOIN track AS t ON t.id = s.track_id
CROSS JOIN trace_bounds AS b
WHERE t.name = 'Player state'
ORDER BY s.ts;
```

`CROSS JOIN trace_bounds` 把同一行 trace 边界值附到每条状态记录上。`observed_dur_ms` 只表示录制窗口内观察到的时长。开放行可能在 trace 开始前已经处于该状态，也可能在 trace 结束后继续保持；裁剪后的值不能代表完整业务时长。若第一条状态事件晚于 `trace_bounds.start_ts`，更早的状态仍是未知值，查询不会自行补齐。

### 汇总各状态占比

下面的查询把每行限制在 trace 边界内，再按状态值聚合，适合比较一次录制中播放器的缓冲和播放占比：

```sql
WITH bounded AS (
  SELECT
    s.value,
    CASE
      WHEN s.dur = -1 THEN b.end_ts - s.ts
      ELSE s.dur
    END AS dur
  FROM state AS s
  JOIN track AS t ON t.id = s.track_id
  CROSS JOIN trace_bounds AS b
  WHERE t.name = 'Player state'
)
SELECT
  value,
  ROUND(SUM(dur) / 1e6, 3) AS total_ms,
  ROUND(100.0 * SUM(dur) / SUM(SUM(dur)) OVER (), 2) AS observed_percent
FROM bounded
WHERE dur >= 0
GROUP BY value
ORDER BY total_ms DESC;
```

`SUM(SUM(dur)) OVER ()` 先得到每种状态的合计时长，再计算所有状态的总和。这个分母只覆盖 `state` 表中有值的区间，因为 idle 不会生成状态行。若指标要求把 idle 计入分母，应使用整个观测窗口，或根据相邻状态行另外构造 idle 间隔；报告中应说明采用哪种口径。

## 在 Android 17 上采用 v57 能力

### 路径一：只升级开发机分析器

这是改动最小的方案：

1. Android 17 继续使用系统 Perfetto 录制 sched、ftrace、atrace、FrameTimeline、heap profile 等既有数据；
2. 开发机安装固定版本的 v57.2 或更高 Trace Processor；
3. 用该分析器读取 trace，执行 SQL 并保存查询结果、工具版本和原始文件。

这个方案能获得新分析器的表结构、PerfettoSQL 标准库和解析修复，但旧 producer 依旧不会产生 `TYPE_STATE`。

### 路径二：应用携带新版 SDK 生产 state track

需要原生状态轨道时，应把 producer SDK 与 Trace Processor/UI 作为一组有明确版本的能力交付：

1. 应用或测试进程链接包含状态轨道的 Perfetto SDK；
2. 在 in-process backend 或经验证的 system backend 上录制；
3. 使用 v57.2 或更高的兼容 Trace Processor 和 UI 打开结果；
4. 在目标 Android 17 build 上验证注册、SELinux、缓冲区、丢包统计和 SQL 表；
5. 为旧分析器保留可识别的降级标记，或者明确拒绝旧版本工具。

backend 是 SDK 写入 trace 的目标。in-process backend 在本进程内管理缓冲与会话，system backend 则连接设备上的 Perfetto tracing service；trace packet 是 producer 写入服务的 protobuf（Protocol Buffers 序列化格式）数据单元。Android 17 的 tracing service 可以搬运 producer 写入的 packet，但这不表示任意新版 SDK 都能无条件接入 system backend。SDK ABI（二进制调用约定）、Unix socket（本机进程间通信端点）权限、数据源注册策略和产品 SELinux 强制访问规则都可能限制连接，必须在目标系统镜像上实测。

不建议为了追逐上游版本而单独替换产品镜像中的 `traced` 或 `trace_processor_shell`。这些平台二进制会与 Android init 服务启动配置、文件权限、SELinux、AIDL（Android 接口定义语言）生成的 Binder 接口、IPC（进程间通信）协议及系统测试一起交付；只覆盖其中一个文件，可能造成协议、权限或启动流程不匹配。

### 路径三：维持 Android 17 平台兼容

无法携带新版 SDK 时，可以按数据含义选择 Android 17 已有的轨道类型：

- 有明确开始和结束的活动：slice；
- 某个时刻的数值：counter；
- 单次状态转换提示：instant，并通过稳定名称或参数携带值；
- 需要计算状态持续时间：由生产端维护成对 slice，或在 SQL 中依据经过审核的 instant 事件构造区间。

这种兼容表达缺少 state track 的单值约束和专用 UI 展示。生产代码要自行保证状态转换合法，文档、SQL 和指标名称也应标明所用替代方案，避免与原生 `state` 表混用。

## v57 系列的其他变化及 Android 边界

- `linux.journald` data source 采集使用 systemd 的 Linux 系统日志 journald，并在统一日志表中用 `log_source` 标明来源。Android 使用 logcat；该数据源不会在 Android 17 上取代 logcat。
- JSON Trace Event Format 用 `"ph": "X"` 表示带完整时长的 complete event，同一线程上的这类事件按格式约束不应互相重叠。v57 会把重叠事件放入额外的 overflow track（容纳冲突事件的备用轨道），UI 再合并显示，同时记录导入警告。生产工具应使用异步 `"b"` / `"e"` 事件表达可重叠区间。
- 查询结果网格增加列排序、重排、隐藏和更清楚的 SQL 错误显示。这些是 UI 操作能力，不改变表结构或 SQL 计算结果。
- `heapprofd.process_cmdline` 是按进程命令行选择 native heap profiler（C/C++ 堆分析器）目标的配置项。它支持部分通配符，但通配符只能匹配已经运行的进程；配置必须设置 `no_startup = true`，明确禁用“从进程启动时开始 profiling”的模式。
- C high-level API 和 Android Java SDK 增加嵌套轨道及同级轨道的排序、合并控制。correlation ID（关联 ID）只表示多个事件属于同一逻辑操作，不包含因果方向；需要表达跨线程的先后或因果关系时仍应使用 flow。
- Trace Processor 可从公开 URL 或 Perfetto permalink（Perfetto UI 保存并分享 trace 的链接）加载 trace。生产 trace 常含进程、线程与业务信息，公开 URL 只适合经过授权和脱敏的文件。
- `perfetto` Python 包默认选择与包版本对应的 Trace Processor 二进制，便于重复得到相同结果；切换到 `fetch_latest_trace_processor` 会让同一脚本在不同日期下载不同二进制，产生版本漂移。
- Adreno 是 Qualcomm GPU 系列。它的 `adreno_cmdbatch_retired`、`adreno_cmdbatch_sync` ftrace 事件在 v57.1 中可解析为 GPU timeline slice；目标设备是否提供这些内核事件仍取决于系统 build 与 GPU 驱动。
- v57.2 只修复携带自有 proto descriptor 的 trace 在 wire-compatible schema 变化后可能解析失败的问题。wire-compatible 表示字段变更仍遵守 protobuf 的序列化兼容规则；这项修复不改变 state track 的数据模型。

## 评审清单

评审含 v57 state track 的改动时，可逐项检查：

- [ ] Android 平台版本基线写成 Android 17 / API 37 / `android-17.0.0_r1`
- [ ] 平台内置 Perfetto 标为 v54.0 加平台补丁，没有写成 v57
- [ ] producer SDK、Trace Processor 和 UI 各自记录版本或 commit（源码提交标识）
- [ ] state track 使用稳定轨道身份和有限状态集合
- [ ] idle 通过清空表达，指标没有漏掉 idle 分母
- [ ] SQL 使用 `state.value` 和 `state.dur`，没有重复用 `LEAD()` 推导时长
- [ ] `dur = -1` 按 trace 边界处理，并注明只是观测窗口
- [ ] C high-level 与 Java 示例已经由项目采用的 artifact 编译验证，没有把 `main` API 写成 v57.2 API
- [ ] trace 上传、公开 URL 和提供给 AI 模型的方式符合数据处理规则

## 源码与官方资料

- [Perfetto v57.1 release notes](https://github.com/google/perfetto/releases/tag/v57.1)
- [Android 17 标签下的 Perfetto CHANGELOG](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/CHANGELOG)
- [Android 17 标签下的 TrackEvent proto](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/trace/track_event/track_event.proto)
- [v57.1 TrackEvent proto](https://github.com/google/perfetto/blob/v57.1/protos/perfetto/trace/track_event/track_event.proto)
- [v57.1 StateDescriptor proto](https://github.com/google/perfetto/blob/v57.1/protos/perfetto/trace/track_event/state_descriptor.proto)
- [v57.1 `state` SQL view](https://github.com/google/perfetto/blob/v57.1/src/trace_processor/perfetto_sql/stdlib/prelude/after_eof/views.sql)
- [v57.1 StateTracker](https://github.com/google/perfetto/blob/v57.1/src/trace_processor/importers/common/state_tracker.cc)
- [v57.1 Android Java `PerfettoTrace`](https://github.com/google/perfetto/blob/v57.1/src/android_sdk/java/main/dev/perfetto/sdk/PerfettoTrace.java)
- [上游 Java state track 变更 #6464](https://github.com/google/perfetto/commit/0894477744bf11fa1f08ca81bbceb14cd5385737)
