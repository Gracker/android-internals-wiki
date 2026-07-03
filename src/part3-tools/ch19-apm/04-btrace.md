---
title: "btrace / RheaTrace"
chapter: "19"
section: "19.04"
status: "finalized"
drafted_date: "2026-04-24"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-03"
deepseek_polish_state: done
last_deepseek_polish_at: 2026-05-25
last_verified_against: "bytedance/btrace v3.0.0/v3.1.0 README.zh-CN + Main.java default capture source; Perfetto UI"
confidence: medium
tags: [apm]
related_chapters: ["19.0"]
sources:
  - type: blog
    path: "https://github.com/bytedance/btrace"
  - type: official
    path: "https://ui.perfetto.dev/"
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: "reviewed"
task2b_state: fixed
reviewed_date: "2026-07-03"
reviewed_by: "openclaw-task6"
task6_result: "pass-light-edit"
task2b_result: fixed
task9_result: "pass-tech-review"
task9_reviewed_date: "2026-07-03"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-07-03T08:38:28+08:00"
last_task9_audit: "2026-07-03"
last_task2b_at: "2026-04-25T07:48:00+08:00"
last_task6_audit: "2026-07-03"
repaired_date: "2026-04-25"
repaired_by: openclaw-task2b
last_task9_autofix_at: "2026-07-03"
last_task2b_verifier_at: "2026-07-03T07:32:03+08:00"
last_task6_at: "2026-07-03T08:10:00+08:00"
last_task9_review_log: "logs/deep-review/2026-07-03-08-deep-review.md"
updated_by: "openclaw-task9"
updated_date: "2026-07-03"
p0: 0
p1: 0
p2: 0
task9_p0_issues: 0
task9_p1_issues: 0
task9_p2_issues: 0
task9_review_notes: "2026-07-03 Task9 deep review: pass-tech-review；无 P0/P1/P2；task6 已通过且 queue.json 无 pending，自动晋升 finalized；详见 logs/deep-review/2026-07-03-08-deep-review.md。"
---

# btrace / RheaTrace

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 说明 btrace / RheaTrace 用来补方法级现场，解决 Perfetto 只有系统轨道时缺少业务函数名的问题。
- 🔹 [采集流程] 展开构建插桩、设备端采集、buffer、导出、Perfetto UI 打开的完整路径；写清各阶段失败点。
- 🔹 [模式对比] 比较 perfetto 模式和 simple 模式的输出、阅读方式、适用场景、数据丢失风险。
- 🔹 [版本边界] 说明 3.0 版本、AGP、ART、Android 版本和 RheaTrace / btrace 名称关系；不确定处标注待核对来源。
- 🔹 [采集参数] 解释采样间隔、buffer size、method include / exclude、trace 时长、目标进程、符号映射的影响。
- 🔹 [Perfetto 读法] 写清线程轨道、slice、sched、CPU frequency、Binder、I/O、RenderThread 如何和业务方法一起看。
- 🔹 [启动案例] 给启动慢分析模板，要求拆 Zygote、bindApplication、ContentProvider、Application、Activity、first draw。
- 🔹 [滑动案例] 给列表滑动卡顿模板，要求结合 `doFrame`、RenderThread、onBind、diff、图片解码和后台线程。
- 🔹 [误判边界] 说明采样 trace 看不到短函数、buffer 覆盖、插桩开销、CPU 争抢和 Binder 等待导致的误判。
- 🔹 [工具关系] 区分 btrace、Perfetto SDK、androidx.tracing、simpleperf 和 Android Studio Profiler 的使用顺序。

### 扩展（可选深入）

- 🔸 增加一份采集命令或配置模板，标明哪些参数需要按设备性能调整。
- 🔸 补一个 Perfetto UI 阅读清单，列出先看哪些轨道、再看哪些 slice。
- 🔸 补一个“报告无法解释问题”的反例，引导读者回到系统调度、I/O 或 Binder 证据。
- 🔸 对 bytedance/btrace upstream README、RheaTrace 文档和 AGP 适配状态做核对。
- 🔸 增加与 Matrix Trace Canary 的差异表，避免两个章节内容重复。

### 流水线加工要求

- 所有案例必须包含“现象 -> 采集参数 -> trace 观察点 -> 判断边界 -> 下一步验证”。
- 不要把方法耗时直接等同于根因，必须同时看调度和线程状态。
- 代码或命令示例必须能说明字段含义，不能只展示空模板。

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## btrace 用来补方法级现场

btrace，也就是 RheaTrace，是字节跳动开源的高性能 tracing 工具。3.0 版本以 Perfetto 为主要承载，采集应用方法栈并叠加系统 trace 信息，最终生成可以在 Perfetto UI 中打开的 `.pb` trace 文件。

它适合“某类启动慢、卡顿或交互延迟已经被发现，需要补一段方法级现场”的场景。它的输出更像诊断证据，不像指标看板。

## 采集流程

Android 侧接入分成两段：

1. App 包里集成 `com.bytedance.btrace:rhea-inhouse:3.0.0` 或对应 no-op 依赖，并在 `Application.attachBaseContext()` 调用初始化。
2. 通过 PC 侧脚本连接设备，用 adb 控制采集时长、包名、输出文件、是否重启 App、是否带系统调度信息。

官方 README 中的典型命令是：

```bash
java -jar rhea-trace-shell.jar -a your.package.name -t 10 -o output.pb -r sched
```

这个命令的含义是抓取指定包名 10 秒 trace，输出 `output.pb`，用 `-r` 重启 App 以覆盖启动阶段，并把 `sched` 作为系统 trace category 一起采集。`sched` 会同时采集 CPU 调度事件，后面才能判断线程是 Running、Runnable，还是被切走。生成的 .pb 文件可以直接拖入 Perfetto UI 打开分析。

## perfetto 模式和 simple 模式

btrace 3.0 有两类模式：

- **perfetto 模式**：README 写的是 Android 8.1 及以上可用，但 v3.0.0/v3.1.0 的 PC 侧源码在自动选择时以 `ro.build.version.sdk >= 28` 才走 `PerfettoCapture`；Android 8.1 设备需要显式验证 `-mode perfetto` 是否可用。可同时采集应用 trace、atrace、ftrace 等系统信息。
- **simple 模式**：设备不支持 Perfetto 时回退，只能采应用侧 trace，缺少 CPU 调度等系统视角。

这一区别会直接影响分析质量。只看应用方法耗时时，容易把“主线程没跑”误判成“业务方法慢”。带上系统调度后，才能判断线程是在运行、等待锁、等 Binder、等 I/O，还是被其他进程抢走 CPU。

## 3.0 版本的几个边界

截至 2026-04-24，btrace README 中列出的 3.0 约束包括：

- Android 设备要求 8.0 及以上。
- 对不支持 Perfetto 的设备，系统信息采集能力受限。
- 32 位设备或 32 位应用无法采集 tracing 数据。
- Android 15 及以上设备的 Java object allocation monitoring 仍有适配限制，若依赖对象分配信息，需要选低于 Android 15 的设备。

这些约束决定了它更适合专项复现、灰度诊断和实验室分析。把它当成所有设备都能跑的常驻线上 SDK，会把兼容性和成本问题放大。

## 和 Perfetto SDK、androidx.tracing 的关系

`androidx.tracing` 和 `Trace.beginSection()` 的作用是给代码区间打标签；Perfetto SDK 可以让应用写入自定义 trace 数据源。它们的共同点是“开发者主动标注”。

btrace 的价值在另一边：它可以从方法栈角度补更多调用信息，并和系统 trace 放在同一时间轴里。问题发生时，读者可以同时看：

- 业务方法在哪个时间窗口执行。
- 主线程和 RenderThread 是否拿到 CPU。
- Binder、I/O、GC、调度是否参与了延迟。
- 启动阶段是否有明显同步等待。

所以 btrace 更适合当“异常样本放大镜”。先由 APM 指标筛出异常版本或异常页面，再用 btrace 抓一段可读 trace。

## 使用建议

接入 btrace 前要把构建开关设计好。Debug / internal 包可以默认集成真实依赖，Release 包通常使用 no-op 或只在灰度诊断包中启用。方法名混淆后还要准备 mapping，否则 Perfetto 中的调用栈会失去可读性。

分析结果不要只看最长方法。从时间轴出发：先确定慢的时间窗口，再确认主线程是否运行，再看方法 trace、系统调度和阻塞点。只有应用方法、系统状态和用户操作能互相对应，结论才适合写进性能修复单。

## 采集参数怎么读

btrace 3.0 的 PC 侧命令参数直接影响 trace 内容。常见参数可以按用途分：

| 参数 | 作用 | 实战建议 |
|---|---|---|
| `-a` | 指定包名 | 必填，确认目标进程是否为主进程 |
| `-t` | 采集时长，单位秒 | 启动 5-15 秒常见，复杂交互按脚本时长设置 |
| `-o` | 输出 `.pb` 文件 | 文件名带场景、版本、设备，方便归档 |
| `-r` | 重启 App 后采集启动阶段 | 冷启动分析常用 |
| `sched` | 系统 trace category，采集 CPU 调度事件 | 启动、滑动、卡顿样本默认带上；缺少它时很难判断 Runnable 线程是否拿到 CPU |
| `-m` | ProGuard mapping 路径 | 混淆包必须带，否则方法名不可读 |
| `-mode perfetto/simple` | 决定是否叠加系统信息 | Android 9/API 28+ 默认走 `PerfettoCapture`；Android 8.1 按设备验证，必要时显式指定 `-mode perfetto` 或回退 simple |
| `-sampleInterval` | 最小采样回溯间隔 | 间隔越小，细节越多，开销也越高 |
| `-maxAppTraceBufferSize` | 应用 trace buffer 上限 | 启动和长交互要避免 buffer 被覆盖 |

`-r` 解决启动阶段覆盖，`sched` 解决系统调度证据。两者不是同一个开关。缺少 `sched` 时，启动慢 trace 容易只剩应用方法名。

这些参数要写进复现记录。没有采集时长、设备、版本和 mode，后续读 trace 的人很难判断“没看到系统信息”是工具没开，还是设备不支持。

## Perfetto UI 里的读法

打开 btrace 输出的 `.pb` 后，不要先搜最长方法。推荐按时间线读：

1. 找目标场景窗口：启动从进程创建到首帧，滑动从触摸开始到列表停止。
2. 看 Main thread：这段时间主线程是在跑、睡眠、等待，还是被调度饿住。
3. 看 RenderThread：UI 线程提交后，RenderThread 是否继续阻塞。
4. 看 CPU 调度：线程是否频繁 Runnable 但拿不到 CPU；Perfetto 中浅色等待段通常对应 Runnable，实际 Running 会在 CPU 轨道或线程状态里显示 CPU core 归属。
5. 看 btrace 方法轨道：业务方法和系统慢段是否在同一窗口。
6. 看 Binder / I/O / GC：是否有跨进程、磁盘或回收事件插入。

如果主线程没有运行，最长方法就不是主因。比如线程 runnable 但长时间不上 CPU，问题可能来自系统负载或优先级竞争；如果主线程卡在 Binder，问题可能在对端进程；如果卡在 I/O，方法名只能告诉你调用入口，文件和系统状态还要另查。

## 启动慢样本的分析模板

启动 trace 建议按阶段拆：

| 阶段 | 观察点 |
|---|---|
| 进程创建 | Zygote fork、bindApplication、ContentProvider 初始化 |
| `attachBaseContext()` | MultiDex、热修复、监控 SDK、动态加载 |
| `Application.onCreate()` | 三方 SDK 初始化、同步 I/O、主线程网络、锁等待 |
| Activity 创建 | `onCreate()`、布局 inflate、Fragment 初始化 |
| 首帧前 | measure/layout/draw、图片解码、首屏数据 |
| 首帧后 | 延迟初始化、异步任务、后台线程争抢 CPU |

btrace 的价值在于把这些业务阶段的函数栈和 Perfetto 的系统事件放在一起。比如启动 P95 抬升，如果 trace 显示 `Application.onCreate()` 里方法耗时变长，但 CPU 轨道显示线程一直 runnable 却拿不到 CPU，修复方向可能是减少启动并发或延迟后台初始化，单纯删除局部代码未必有效。

## 滑动卡顿样本的分析模板

滑动问题要按帧边界分析。建议先在 App 里用 `androidx.tracing` 给列表关键阶段打标：

```kotlin
trace("Feed#submitList") {
    adapter.submitList(items)
}

trace("Feed#bindViewHolder") {
    bind(item)
}
```

再用 btrace 抓目标操作。读 trace 时看三件事：

- 主线程 `doFrame` 窗口内是否有业务方法过长。
- RenderThread 是否在 sync、GPU command issue 或 swap buffers 阶段阻塞。
- 后台线程是否在滑动期间大量解码、JSON 解析或数据库读写，抢占 CPU。

滑动慢经常来自每帧都多出一点工作，而非单个最长函数。btrace 能帮助看到这些“小块重复工作”是不是集中在 `onBindViewHolder()`、图片加载回调、diff 计算或曝光埋点里。

## 采样 trace 的误判

采样式 tracing 的结论有边界：

- 采样间隔会影响能否看到短函数。
- buffer 满后旧样本可能被覆盖。
- 混淆映射不匹配会导致方法名错误。
- 采集本身会改变部分时序，尤其是低端设备。
- 只抓一次 trace 不能代表线上分布。

所以 btrace 适合做“根因候选验证”。先由线上 APM 找到稳定异常，再抓多台设备、多次样本，看慢段是否重复出现。只有重复出现并和指标窗口重合，才适合下结论。
