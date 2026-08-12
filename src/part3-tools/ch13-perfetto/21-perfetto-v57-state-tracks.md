---
title: "Perfetto v57 状态轨道与版本边界"
chapter: "13.21"
status: ready-for-review
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: ["Perfetto", "TrackEvent", "状态追踪", "版本边界"]
related_chapters: ["13.1", "13.9", "13.15", "13.16", "13.20"]
last_verified: "2026-07-12"
last_verified_against: "Perfetto v57.1 release (2026-07-02)"
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

> Android 平台版本、Perfetto SDK 与主机分析器各自升级，不能用“Android 17 支持 Perfetto v57”概括。平台基线固定为 Android 17 / API 37 / `android-17.0.0_r1`，上游工具基线固定为 Perfetto v57.1。

## 三条版本线

`android-17.0.0_r1` 的 `external/perfetto/CHANGELOG` 顶部记录了一个尚未发布的 Android `aflags` 补丁，紧接着的完整上游版本是 **v54.0（2026-02-27）**。同一标签下的 `track_event.proto` 只定义到 `TYPE_COUNTER = 4`，没有 `TYPE_STATE`。

Perfetto **v57.1** 于 2026 年 7 月 2 日发布。状态轨道、journald 采集和新版 Trace Processor/UI 属于上游工具版本线，不会自动升级设备中的 `/system/bin/perfetto`、`traced`、`traced_probes` 或 Android Framework API。

| 对象 | 采用的版本 | 在哪里运行 | 能否直接提供 v57 状态轨道 |
|---|---|---|---|
| Android 平台 Perfetto | `android-17.0.0_r1`：v54.0 加平台补丁 | Android 17 设备 | 不能；平台 proto 没有 `TYPE_STATE` |
| Perfetto v57.1 SDK / Trace Processor / UI | `v57.1` tag | 应用、测试工具或开发机 | C/C++ 生产与解析路径可用 |

这个拆分会影响方案选择：

- 只升级主机侧分析器：可以读取新版 schema 和标准库，但不会补出设备未录制的数据。
- 想在 trace 中得到原生 `state` 表：生产端和分析端都要具备 v57 状态轨道能力。
- 只能依赖 Android 17 系统内置组件：继续使用 slice、instant、counter 等 v54 能力，不要发出 `TYPE_STATE` 后假定平台工具可以解释。

## State track 的数据模型

### Slice、counter 和 state 各自回答什么

| 轨道类型 | 数据形态 | 适合回答的问题 | 常见误用 |
|---|---|---|---|
| Slice | 开始、结束、可嵌套 | “这个操作执行了多久？” | 用大量首尾相接的 slice 模拟长期状态 |
| Counter | 时间戳加数值 | “这一刻的频率、字节数或队列深度是多少？” | 用整数枚举表达状态，却遗漏枚举表 |
| State | 时间戳加字符串状态，单轨道至多一个当前值 | “这个子系统在这段时间处于什么状态？” | 把同一时间可并存的多个活动塞进单条 state track |

播放器的 `Buffering → Playing → Paused` 适合 state track。并行的下载任务、解码任务和渲染任务可以同时存在，应分别使用 slice 或多条轨道。

### v57.1 在线路格式中增加了什么

v57.1 的 `TrackEvent.Type` 增加 `TYPE_STATE = 5`。事件的 `track_uuid` 必须指向带 `StateDescriptor` 的轨道。`StateDescriptor` 在 v57.1 中是空消息，只负责类型标记；状态字符串通过事件名称路径传递。空值或未设置状态会结束当前状态，使轨道进入 idle。

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

Android 17 标签中的同一枚举止于 `TYPE_COUNTER = 4`。因此，看到 API 37 或 Android 17 不能推出设备自带 v57 状态轨道。

### Trace Processor 如何形成持续时间

v57.1 的 `StateTracker::UpdateState()` 揭示了几条容易遗漏的语义：

- 新值与当前值不同：关闭旧行，把 `dur` 写成两次状态事件的时间差，再创建新行；
- 新值与当前值相同：不创建新行，只把新参数附加到当前状态；
- 新值为空：关闭旧行，不创建 idle 行；
- 尚未被下一次转换或清空关闭的行以 `dur = -1` 暂存。

这也解释了为什么查询 `state` 表时不应再用 `LEAD(ts)` 计算时长。Trace Processor 已经维护 `dur`；手工 `LEAD` 会绕过相同状态合并、显式清空和开放区间的语义。

## 生产状态事件

### C++ SDK

下面的片段展示一个状态轨道上的三次转换。类别注册、Tracing 初始化和 session 配置沿用 Perfetto SDK 的常规写法，此处省略：

```cpp
perfetto::StateTrack player_state("Player state");

TRACE_STATE("player", "Buffering", player_state);
TRACE_STATE("player", "Playing", player_state);
TRACE_STATE("player", "", player_state);  // 清空当前状态，进入 idle
```

同一逻辑轨道应复用稳定的 `StateTrack` 身份。状态值应来自受控枚举；把请求 ID、文件名等高基数字符串作为状态，会制造大量难以聚合的值，也会增加 trace 体积。

### C SDK 高层 API

下面的调用来自 v57.1 发布说明，用于向已经注册的状态轨道写入 `Buffering`：

```c
PERFETTO_TE(player, PERFETTO_TE_STATE("Buffering"),
            PERFETTO_TE_REGISTERED_TRACK(&player_state_track));
```

`player_state_track` 的声明和注册必须使用状态轨道 API 完成。只把普通 counter 或 named track 传给状态事件，会破坏 descriptor 与事件类型的配对关系。

### Android Java SDK 的 v57.1 标签差异

v57.1 发布说明写明 Android Java SDK 获得了同等能力；源码核查却发现一个必须保留的版本差异：

- `v57.1` tag 下的 `src/android_sdk/.../PerfettoTrace.java` 只公开 slice、instant 和 counter 的事件类型，未出现 `TYPE_STATE` 或 `state(...)`；
- 上游 `main` 的 `sdk: add state track event support (C HL API + Java SDK)` 变更才加入 `PerfettoTrace.state(...)`、state track builder 和 JNI 路径；
- v57.1 release tag 与该 Java 变更所在分支已经分叉，不能把 `main` 上的方法签名回填为 v57.1 tag 的既有 API。

工程上应以项目解析到的 Java artifact 和源码 commit 为准：锁定依赖，查看 `PerfettoTrace` 公共方法并做一次编译验证。若 artifact 没有 state API，可以改用已验证的 C/C++ SDK，或等待所采用的 Java SDK 版本明确包含该变更。不要在文档中给出无法由 v57.1 tag 编译的 `PerfettoTrack` 示例。

## 查询 `state` 表

### 先确认分析器版本和表结构

Android 17 自带的 v54 Trace Processor 不认识 `state` 表。使用 v57.1 或更高的兼容分析器打开 trace 后，可以先执行下面的结构查询：

```sql
PRAGMA table_info(state);
```

v57.1 的公开 view 包含 `id`、`ts`、`dur`、`track_id`、`category`、`value` 和 `arg_set_id`。状态列名是 `value`，不存在名为 `state` 的列。

### 查询转换与已观测时长

下面的查询列出状态转换，并把 trace 结束时仍开放的 `dur = -1` 行裁剪到 `trace_bounds.end_ts`：

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

`observed_dur_ms` 只表示录制窗口内观察到的时长。开放行可能在 trace 开始前已经处于该状态，也可能在 trace 结束后继续保持；不能把裁剪后的值解释成完整业务时长。

### 汇总各状态占比

下面的查询把每行裁剪到 trace 边界后按状态聚合，适合比较一次录制中播放器的缓冲和播放占比：

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

这里的分母只覆盖 `state` 表中有值的区间，idle 不会生成状态行。若指标要求把 idle 计入分母，应使用整个观测窗口，或者另外构造 idle 间隔。

## 在 Android 17 上采用 v57 能力

### 路径一：只升级主机侧分析

这是改动最小的方案：

1. Android 17 继续使用系统 Perfetto 录制 sched、ftrace、atrace、FrameTimeline、heap profile 等既有数据；
2. 开发机安装固定版本的 v57.1 或更高 Trace Processor；
3. 代理读取 trace，执行 SQL 并输出证据。

这个方案能获得新分析器的表结构、标准库和解析修复，不能让旧生产端产生 `TYPE_STATE`。

### 路径二：应用携带新版 SDK 生产 state track

需要原生状态轨道时，应把生产端与消费端作为一个版本化功能交付：

1. 应用或测试进程链接包含状态轨道的 Perfetto SDK；
2. 在 in-process backend 或经验证的 system backend 上录制；
3. 使用 v57.1 兼容 Trace Processor 和 UI 打开结果；
4. 在目标 Android 17 build 上验证注册、SELinux、缓冲区、丢包统计和 SQL 表；
5. 为旧分析器保留可识别的降级标记，或者明确拒绝旧版本工具。

Android 17 的 tracing service 通常只负责搬运 producer 写入的 trace packet，仍不能据此承诺任意新版 SDK 都能无条件接入系统 backend。SDK ABI、socket 权限、系统注册策略和产品 SELinux 规则都可能限制接入，必须以目标镜像上的测试结果为准。

不建议替换产品镜像中的 `traced` 或 `trace_processor_shell` 来追逐上游版本。平台二进制与 init、权限、SELinux、AIDL/IPC 及系统测试一起交付，单独覆盖一个文件会把兼容性问题带进系统分区。

### 路径三：维持 Android 17 平台兼容

无法携带新版 SDK 时，可以按数据含义选择已有轨道：

- 有明确开始和结束的活动：slice；
- 某个时刻的数值：counter；
- 单次状态转换提示：instant，并通过稳定名称或参数携带值；
- 需要计算状态持续时间：由生产端维护成对 slice，或在 SQL 中依据经过审核的 instant 事件构造区间。

这种降级表达缺少 state track 的单值约束和原生 UI 面板。文档、SQL 和指标名称应明确标出它是兼容方案。

## v57.1 的其他变化及 Android 边界

- `linux.systemd_journald` 采集 Linux journald，并在统一日志表中用 `log_source` 区分来源。Android 仍使用 logcat；该数据源不会在 Android 17 上代替 logcat。
- JSON Trace Event Format 中重叠的 `"ph": "X"` 事件会进入 overflow track，UI 再合并显示。该输入仍违反 Trace Event Format 约束，Trace Processor 会记录导入警告；生产工具应使用异步 `"b"` / `"e"` 事件表达重叠区间。
- 查询结果网格增加列排序、重排、隐藏和更清楚的 SQL 错误显示。这是 UI 能力，不改变底层 SQL 语义。
- `heapprofd.process_cmdline` 支持部分通配符；通配符只匹配已经运行的进程，配置必须设置 `no_startup = true`。
- C 高层 API 和 Android Java SDK 增加嵌套轨道及同级排序/合并控制。关联 ID 用来标记同一逻辑操作；有因果方向的跨线程关系继续使用 flow。
- Trace Processor 可从公开 URL 或 Perfetto permalink 加载 trace。生产 trace 常含敏感数据，公开 URL 只适合经过授权和脱敏的文件。
- `perfetto` Python 包默认选择与包版本绑定的 Trace Processor 二进制，有利于复现；切换到 `fetch_latest_trace_processor` 会重新引入版本漂移。
- Adreno 的 `adreno_cmdbatch_retired`、`adreno_cmdbatch_sync` ftrace 事件在 v57.1 中可解析为 GPU timeline slice。设备内核是否暴露事件仍取决于目标 build 和驱动。

## 评审清单

评审含 v57 state track 的改动时，可逐项检查：

- [ ] Android 平台锚点写成 Android 17 / API 37 / `android-17.0.0_r1`
- [ ] 平台内置 Perfetto 标为 v54.0 加平台补丁，没有写成 v57
- [ ] producer SDK、Trace Processor 和 UI 各自记录版本或 commit
- [ ] state track 使用稳定轨道身份和有限状态集合
- [ ] idle 通过清空表达，指标没有漏掉 idle 分母
- [ ] SQL 使用 `state.value` 和 `state.dur`，没有重复用 `LEAD()` 推导时长
- [ ] `dur = -1` 按 trace 边界处理，并注明只是观测窗口
- [ ] Java 示例已经由项目采用的 artifact 编译验证
- [ ] trace 上传、公开 URL 和模型访问符合数据处理规则

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
