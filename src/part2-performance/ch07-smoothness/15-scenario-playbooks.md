---

title: "场景化性能作战手册"
chapter: "7.15"
section: "7.15"
status: finalized
drafted_date: "2026-04-21"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-21"
last_verified_against: "AOSP android-16.0.0_r1 + Perfetto docs + Android Developers docs"
confidence: medium
sources:
  - type: official
    path: "https://perfetto.dev/docs/data-sources/frametimeline"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/launch-time"
  - type: official
    path: "https://developer.android.com/reference/androidx/metrics/performance/JankStats"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/anr"
tags: [playbook, smoothness, startup, jank, anr, troubleshooting]
related_chapters: ["7.1", "7.3", "8.2", "9.3", "13.3", "15.2", "15.5", "15.6"]
task9_state: reviewed
repaired_date: "2026-04-21"
repaired_by: "codex"
task9_result: auto-fixed
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-05"
last_task9_at: "2026-06-13T13:28:50+08:00"
last_task9_audit: "2026-06-13"
last_task9_autofix_at: "2026-06-13"
task2b_state: fixed
task2b_result: fixed
task6_state: reviewed
pipeline_stage: ready-to-publish
task2b_fixed_date: "2026-06-05T02:50:00+08:00"
task2b_fixed_by: "openclaw-task2b-main"
task2b_fix_summary: "P0: fixed SurfaceFlinger version-specific observation entries (8-10 handleMessageRefresh, 11-12 onMessageRefresh, 13+ commit/composite); P1: added power/heat troubleshooting chain (thermal, cpufreq, wakelock, JobScheduler, Battery Historian); P2: softened BufferStuffing criteria with cross-validation requirement; updated applicable_versions to Android 17/API 37"

reviewed_date: 2026-06-13
reviewed_by: openclaw-task6
task6_result: pass-light-edit
review_notes: "2026-05-05 Task2B:补充版本边界专节(FrameTimeline 12+/ApplicationExitInfo API 30+/BufferStuffing fallback),Android 8-11 替代观察入口。 | 2026-05-05 Task6 07:30:revisiting 写作复审,清理禁用词并统一路径表达,修复重复 frontmatter;发现大纲要求的功耗排障入口正文缺失,已写入 Task2B queue。 | 2026-05-05 Task9 08:37:Task9 深审发现 Android 8-11 fallback 的 atrace tag 与 FrameTimeline SQL/BufferStuffing 判据仍有技术错误;功耗入口缺失已有 queue pending。"
last_task6_at: 2026-06-13T16:18:11+08:00
auto_promoted_date: 2026-06-13
auto_promoted_by: openclaw-task6
last_task9_review_log: "logs/deep-review/2026-06-13-13-audit.md"
task9_review_notes: "2026-06-13 Task9 闲时抽检 auto-fixed。修正 FrameTimeline SQL:非 jank 过滤需排除 None,BufferStuffing 在 actual_frame_timeline_slice.jank_type 中的字段值为 Buffer Stuffing;同步收敛 BufferStuffing 候选判据。"
task6_reviewed_date: "2026-06-05"
last_task6_review_log: "logs/review/2026-06-13-16-review.md"
task6_review_notes: "2026-06-13 Task6 回炉复审(revisiting→reviewed): pass-light-edit。L1 修复见 review 日志；L2/L3/L4 无新增问题；Task9 已 auto-fixed；queue 无 pending；自动晋升 finalized。"
finalized_date: "2026-06-13"
finalized_by: "openclaw-task6-auto-promote"
deepseek_cn_review_state: done
last_task6_audit: 2026-07-17T14:15:00+08:00
last_deepseek_cn_review_at: 2026-06-23
---

# 场景化性能作战手册

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 把常见性能投诉对应到统一排障入口：卡顿 / 响应慢 / ANR / 内存 / 功耗
- 🔹 每类问题先看什么指标、抓什么 trace、优先排哪条路径
- 🔹 不同场景的第一嫌疑人:MainThread / RenderThread / SurfaceFlinger / Binder / IO / 调度
- 🔹 常见误判:把系统负载当成 App 问题、把输入延迟当成掉帧、把 BufferStuffing 当成普通慢帧
- 🔹 用章节跳转形成"现场排障导航"

### 扩展(可选深入)

- 🔸 针对低端机 / 高刷 / 弱网 / 多窗口做差异化排障
- 🔸 把作战手册转成团队内部 checklist / runbook
<!-- outline-end -->

## 适用范围与证据锚点

本章以 Android 17 / API 37 / `android-17.0.0_r1` 为平台源码锚点。涉及调度、CPU 频率、thermal 与 fence 时，以 `android17-6.18-2026-06_r6` 为内核锚点。Android 8—16 的入口用于说明版本差异，现场结论仍应匹配设备版本、厂商实现、应用构建和复现条件。

排障手册解决的是入口选择问题。它不会用一张固定流程图替代证据：同一句“卡”，可能对应掉帧、输入反馈晚、数据未就绪、进程重建、ANR，或热限频后的系统性退化。工程师要先把用户语言改写为可测量的时间区间，再选择 trace、日志或堆栈。

以下平台能力决定了不同版本能看到什么：

| 能力 | 起始版本 | 能回答的问题 | 使用边界 |
|---|---:|---|---|
| `FrameMetrics` | API 24 | 应用 Window 的帧阶段耗时 | 只覆盖本应用 Window，不能直接归因系统合成 |
| `JankStats` | API 16 | 帧耗时异常与应用 UI 状态 | API 16—23 主要依赖估算；API 24+ 可借助 `FrameMetrics` |
| `ApplicationExitInfo` | API 30 | 进程退出原因、退出时的部分资源数据和可用 trace | PSS/RSS 是系统最近一次采样，可能为 0，也不代表退出瞬间 |
| `FrameTimeline` | API 31 | Window 帧的期望时间、完成时间、呈现类型和 jank 分类 | 当前官方文档明确不支持 `SurfaceView` 内容帧 |
| `ApplicationStartInfo` | API 35 | 冷/温/热启动、启动原因和单调时钟时间戳 | `FULLY_DRAWN` 依赖应用调用 `reportFullyDrawn()` |
| `AppJankStats` | API 36 | 应用向系统报告 View 级卡顿统计 | 它是控件统计入口，不能代替 Perfetto 中的系统归因 |
| `ApplicationExitInfo.AnrInfo` | API 37 | ANR 类型、超时、ID 和用户可感知性 | 只用于系统已记录的 ANR，不能描述尚未触发 ANR 的长停顿 |

Android 8—11 没有 `FrameTimeline`。这几代系统可组合使用 `gfx`、`view`、`sched`、`freq`、`input` 等 trace 类别，观察 `Choreographer#doFrame`、RenderThread、SurfaceFlinger 主线程和线程调度；应用侧再补 `FrameMetrics` 或 `JankStats`。SurfaceFlinger 的 slice 名称受版本、构建和 tracing 配置影响，排查时应按线程、时间和相邻事件定位，不能把某个函数名当成跨版本协议。

## 现场先写一张问题卡

trace 之前缺少场景定义，trace 之后通常只会得到一幅很宽的时间轴。问题卡至少记录以下内容：

| 字段 | 记录要求 |
|---|---|
| 软件身份 | 应用版本、commit、构建类型、WebView/Flutter/播放器版本 |
| 设备身份 | 机型、SoC、内存、Android 版本、Build fingerprint |
| 显示条件 | 分辨率、刷新率、亮度、多窗口或画中画状态 |
| 操作脚本 | 从哪个页面开始、输入动作、数据集、网络条件 |
| 体验失效 | 哪个反馈晚了、哪个画面跳了、是否能继续操作 |
| 时间窗口 | 触发点、异常开始、恢复或超时点 |
| 复现率 | 次数、成功率、冷/温/热状态、是否集中在特定设备 |
| 对照组 | 正常版本、正常设备或关闭某项功能后的结果 |

“点击后大约 700 ms 才出现按压反馈”比“按钮卡”更适合分析。“120 Hz 设备连续滚动第 4 秒出现三次长间隔”也比“列表 FPS 低”提供了更多约束。

## 从投诉到责任路径的五步分流

### 第一步：确认体验失效类型

把现场归入一个主类别，其他现象作为伴随信号：

| 用户描述 | 主类别 | 起始观察点 |
|---|---|---|
| 滑动、动画出现跳变 | 帧节奏异常 | `FrameTimeline`、主线程、RenderThread、SurfaceFlinger |
| 点击后反馈晚 | 输入到反馈延迟 | 输入时间、主线程调度、锁、Binder、IO、首个反馈帧 |
| 页面出现或可用得晚 | 启动/页面就绪慢 | TTID、TTFD、数据与资源就绪 |
| 界面长时间无响应 | ANR 或 near-ANR | ANR 记录、主线程栈、超时前时间线 |
| 回前台越来越慢 | 生命周期/内存压力 | 进程存活、重建、GC、page fault、LMKD |
| 发热后越来越卡 | 功耗与热退化 | 温度、CPU/GPU 频率、调度、后台负载 |

一个现场可以同时存在两类问题。例如页面切换动画按帧运行，内容却在 1.5 秒后出现；此时动画流畅度与内容就绪时间应分别测量。

### 第二步：固定时间窗口

确定一个可重复的起点和终点。输入问题可从事件到达应用或业务埋点开始，到首个可见反馈帧结束；启动问题可从系统启动时间戳开始，到 TTID 或 TTFD 结束；ANR 要覆盖超时前的等待过程。只截取异常发生后的轨道，常会漏掉锁的持有者、Binder 发起方或频率下降的前因。

### 第三步：识别输出类型

渲染路径决定了该追哪条 Surface：

- 普通 View/Compose 内容经过宿主 Window：`vsync-app → Choreographer#doFrame → INPUT/ANIMATION/INSETS_ANIMATION/TRAVERSAL/COMMIT → syncAndDrawFrame → RenderThread → BLAST BufferQueue → SurfaceFlinger → HWC → present`。
- `SurfaceView` 内容由独立 Producer、Surface、BufferQueue 和 Layer 提交；宿主 Window 与内容层要分开分析。
- `TextureView` 接收外部 Buffer 后，由宿主 RenderThread 采样进 App Window；宿主 Window 仍是提交给 SurfaceFlinger 的最终层。
- WebView 常同时包含 Chromium renderer 与宿主 HWUI 路径；视频、受保护内容还可能增加独立层。
- Flutter 要记录根渲染模式、平台视图和外部纹理。线程合并策略会随 Flutter 版本与配置变化，不能只靠固定线程名判断。

这组路径来自 Android 17 源码和本地 `rendering_pipelines` 系列的交叉整理。它约束了一个常见判断：UI 线程退出 `doFrame` 只说明主线程阶段结束，RenderThread、BufferQueue、SurfaceFlinger、HWC 和显示设备仍可能延后该帧。

### 第四步：把帧连接到责任线程

对支持 `FrameTimeline` 的普通 Window，按 `DisplayFrame → SurfaceFrame → 进程/Layer → 主线程或 RenderThread` 逐层定位。若异常发生在 `SurfaceView`、相机或视频独立层，由 Layer、BufferQueue、生产者时间戳、fence、SurfaceFlinger 与 HWC 证据重建同一时间窗口。

`SurfaceFrame` 和 `DisplayFrame` 使用各自的 token 命名空间。数值相同也不能直接相连；应使用 trace 表中的 `display_frame_token` 等显式关系。若现场没有生成目标帧，例如业务等待网络后才触发绘制，帧时间线也无法解释帧创建之前的空白，需要回到输入、业务任务和数据依赖。

### 第五步：写出可证伪假设

每轮分析只保留一个主假设，并附上反证条件。例如：

> 假设：主线程在列表滚动期间等待同步 Binder，导致三个 App SurfaceFrame 超过预算。若移除该调用后相同操作仍出现同一批 SurfaceFlinger deadline miss，当前假设不成立。

这种写法要求结论同时包含时间、线程、等待对象、受影响帧和对照结果，避免从一条长 slice 直接跳到代码归因。

## FrameTimeline 应该怎样读

Android 12+ 的 `android.surfaceflinger.frametimeline` 数据源会生成 Expected 和 Actual 时间线。Expected 描述调度期望；Actual 描述应用或 SurfaceFlinger 完成与呈现的记录。

Perfetto UI 中的颜色负责不同含义：

- 红色表示该进程造成了 jank。
- App 轨道上的黄色表示该 SurfaceFrame 受到 SurfaceFlinger 侧 jank 影响。
- 蓝色表示帧被丢弃。
- 浅绿色表示 high latency state：帧率可能平稳，呈现却持续落后，输入到显示的延迟随之增加。

`Buffer Stuffing` 是 `actual_frame_timeline_slice.jank_type` 中的字段值。它描述应用在旧帧呈现前持续排入新帧，管线延迟逐渐堆积的状态；继续堆积时，Producer 还可能在 dequeue 阶段等待可用 slot。它不能简化为“一帧算得慢”，也不能由一条 `dequeueBuffer` 长 slice 单独确认。

下面的查询用于列出被 FrameTimeline 分类为 jank 的 Actual 帧，并保留进程、Layer、SurfaceFrame 与 DisplayFrame 的关联字段：

```sql
SELECT
  p.name AS process_name,
  a.layer_name,
  a.ts,
  a.dur,
  a.surface_frame_token,
  a.display_frame_token,
  a.jank_type,
  a.on_time_finish,
  a.present_type
FROM actual_frame_timeline_slice AS a
LEFT JOIN process AS p USING (upid)
WHERE a.jank_type != 'None'
ORDER BY a.ts;
```

查询结果适合确定候选帧和责任层。`jank_type` 仍需与线程 slice、调度状态及上下游帧对应，不能单独充当代码根因。

下面的聚合用于找出 trace 中 `Buffer Stuffing` 集中的进程和 Layer：

```sql
SELECT
  p.name AS process_name,
  a.layer_name,
  COUNT(*) AS stuffed_frames,
  SUM(a.dur) / 1e9 AS total_duration_s
FROM actual_frame_timeline_slice AS a
LEFT JOIN process AS p USING (upid)
WHERE a.jank_type = 'Buffer Stuffing'
GROUP BY p.name, a.layer_name
ORDER BY stuffed_frames DESC;
```

聚合高只能说明该 Layer 在采样窗口内多次进入积压状态。还要检查输入到反馈的延迟趋势、Producer 节奏、可用 slot 等待、消费者推进和显示节奏，才能定位积压从哪里开始。

## 九类常见现场

### 1. 冷启动慢

冷启动分析要先确认本次记录属于冷、温还是热启动。Android 15 / API 35 起，`ApplicationStartInfo` 可给出启动类型、原因、启动组件和一组单调时钟时间戳；其中包括 launch、fork、`bindApplication`、`Application.onCreate`、首帧、RenderThread 初始帧、SurfaceFlinger 合成完成，以及应用上报后的 `FULLY_DRAWN`。

排查顺序如下：

1. 分别统计冷、温、热启动，禁止把三类样本混成一个分位数。
2. 对照 TTID 与 TTFD。TTID 晚，追进程创建、初始化、首帧绘制；TTID 正常而 TTFD 晚，追首屏数据、异步资源和可交互边界。
3. trace 从启动动作前开始，覆盖首帧和 `reportFullyDrawn()`；启动末尾缺失会让 TTFD 分析失去终点。
4. 检查 Application/ContentProvider 初始化、主线程 Binder/IO、类加载、资源加载和首屏布局，不用函数总耗时替代关键路径。
5. Native 应用在 16 KB 页设备上要验证 ELF 与 APK ZIP 对齐。兼容模式只表示部分旧应用仍可运行，可靠性和性能影响应在目标设备测量。

下面两条命令分别确认设备页大小和 APK 的 16 KB ZIP 对齐：

```bash
adb shell getconf PAGE_SIZE
zipalign -c -P 16 -v 4 app-release.apk
```

第一条返回 `16384` 时，设备使用 16 KB 页；第二条通过只说明 APK 内未压缩共享库的 ZIP 对齐满足检查，还应使用 NDK r28+ 或按官方指南验证 ELF LOAD segment。不要预设固定的 PSS、page fault 或启动损耗。

Android 17 还提供强制暴露兼容问题的调试开关。下面的命令用于测试环境，执行前应记录设备原值，测试后恢复：

```bash
adb shell setprop bionic.linker.16kb.app_compat.enabled fatal
adb shell setprop pm.16kb.app_compat.disabled true
```

这两个属性会限制加强兼容行为，适合让未正确适配的 Native 依赖尽早失败；它们不属于线上优化参数。

导航：`8.1`、`8.2`、`8.3`、`15.6`。

### 2. 列表滚动和连续动画掉帧

采样时使用固定数据集、固定手势和稳定刷新率，保留进入滚动前后的时间。分析按以下层次推进：

1. 用 `FrameTimeline` 区分 App deadline、SurfaceFlinger deadline、丢帧和 high latency state。
2. App 侧从 `Choreographer#doFrame` 展开 INPUT、ANIMATION、INSETS_ANIMATION、TRAVERSAL、COMMIT，再检查 `syncAndDrawFrame` 与 RenderThread。
3. 主线程长时间 Running 表示正在执行；长时间 Runnable 表示可运行但未得到 CPU。两者对应代码开销与调度争抢两条方向。
4. RenderThread 超预算时检查显示列表、纹理上传、shader、GPU fence 和资源争用，不能把主线程耗时直接视作整帧耗时。
5. SurfaceFlinger 侧异常要检查同一 DisplayFrame 的其他 Layer、合成策略与 HWC，不要只盯当前应用。

线上可用 `JankStats` 记录页面、滚动状态等 UI 上下文。API 16—23 的时序较粗，API 24+ 借助 `FrameMetrics` 后更可靠；API 31+ 的平台帧信息更丰富。API 36 起还可通过 `View.reportAppJankStats()` 向系统报告控件级 `AppJankStats`。这两类统计适合发现“哪个场景常出问题”，系统级责任仍由 trace 还原。

导航：`7.3`、`7.4`、`7.5`、`18.2`、`18.7`。

### 3. 页面切换慢或动画不稳

页面切换要拆成三个时间点：输入被处理、目标容器首次可见、内容达到可交互状态。

- 目标容器出现前停顿：检查输入分发、路由、事务、主线程任务和首个目标帧。
- 容器按时出现，动画跳变：检查该 Window 的 SurfaceFrame、RenderThread 和 SurfaceFlinger。
- 动画稳定，内容迟到：检查网络、数据库、反序列化、图片和占位内容退出条件。

业务 marker 应围住关键事件，例如“点击处理开始”“目标页面提交”“首屏数据就绪”，再与 FrameTimeline 对齐。不要从一个名为 `startActivity` 或 `navigate` 的宽泛 slice 推导整个页面已可交互。

弱网复现要固定延迟、带宽、丢包率和缓存状态。网络改变的是数据到达时间；主线程在等待期间做轮询、同步 IO 或反复布局，则会额外产生渲染问题。

导航：`1.4`、`1.5`、`7.4`、`8.4`。

### 4. 输入反馈晚与 Buffer Stuffing

输入延迟的终点应是用户能看到的反馈帧，不能停在事件回调结束处。建议同时记录：

- Input 事件或应用输入 marker；
- 主线程何时处理事件；
- 业务状态何时提交；
- 哪个 SurfaceFrame 包含反馈；
- 该 SurfaceFrame 对应哪个 DisplayFrame、何时呈现。

主线程 Sleeping 可能在等锁、Binder reply、futex 或 IO；Runnable 可能受 CPU 争抢；Running 但长时间不返回则要看执行栈。帧率平稳也可能存在 high latency state，因此 FPS 无法单独回答“点了多久才看到反馈”。

Android 17 的 `BufferQueueProducer::dequeueBuffer()` 会进入 `waitForFreeSlotThenRelock()`，必要时在 `mDequeueCondition` 上等待空闲 slot；配置 dequeue timeout 后也可能返回 `TIMED_OUT`。这些源码路径解释了 Producer 为何会停住，却没有给出跨设备通用的 1 ms 或 5 ms 阈值。

`NATIVE_WINDOW_CONSUMER_RUNNING_BEHIND` 是 `query()` 返回项，本身没有同名 trace 点。`PRESENT_LATER` 是消费者选择 Buffer 时的返回状态；Android 17 源码在该返回路径上写有 `ATRACE_NAME("PRESENT_LATER")`，启用 graphics atrace 且执行到这条路径时才会出现在 trace 中。它的缺席不能证明 Consumer 从未延后 acquire，命中也只说明本次选择被推迟。现场仍要与 FrameTimeline、线程状态、Layer 和 BufferQueue 推进共同验证。

Android 8—11 缺少 `Buffer Stuffing` 分类时，可将“呈现持续落后、输入反馈延迟增长、Producer 等待可用 slot”视为候选组合。`dumpsys SurfaceFlinger` 的文本与字段会随版本和厂商变化，只适合作为同一时刻的辅助快照。

导航：`3.1`、`3.2`、`7.1`、`15.2`。

### 5. SurfaceView、TextureView、相机和视频

这类场景先回答“卡的是宿主 UI，还是独立内容层”。

`SurfaceView` 的内容 Producer 可绕过宿主 View 绘制，提交到独立 BufferQueue 和 Layer。当前 FrameTimeline 不覆盖 `SurfaceView` 内容帧，宿主 Window 的绿色帧不能证明视频或相机画面按时呈现。应连接生产者时间戳、queue/acquire、release/present fence、SurfaceFlinger 合成和显示节奏。

`TextureView` 把外部 Buffer 当纹理交给宿主 RenderThread 采样。外部内容更新、纹理采样和宿主 Window 提交都可能延时；分析终点仍是宿主 App Window 的 SurfaceFrame。

视频播放器调用 `MediaCodec.releaseOutputBuffer()` 只表示把输出 Buffer 按计划交给后续路径，不代表屏幕已经显示该帧。SurfaceFlinger 是否选择 HWC `DEVICE` composition，也取决于每帧的 Layer 数、格式、变换、混合、保护属性和硬件能力；同一场景可能在 `DEVICE` 与 `CLIENT` 间切换。

排查顺序可固定为：

1. 分别标记宿主 UI 与内容层的异常时间。
2. 识别每个 Layer 的 Producer、刷新率和 Buffer 时间戳。
3. 检查 Producer 是否等 slot、消费者是否延后 acquire、fence 是否晚。
4. 检查 SurfaceFlinger 与 HWC 合成，记录 composition type 的逐帧变化。
5. 用移除覆盖层、降低视频规格、改用单一容器等对照试验验证假设。

导航：`18.4`、`18.6`、`18.7`、`18.15`。

### 6. WebView、Flutter 与混合渲染

WebView 现场必须记录 provider 包名和版本。普通页面常包含 Chromium renderer、宿主进程中的 functor/HWUI 和 App Window；视频或受保护内容还可能出现独立 Surface。JavaScript 长任务、资源加载、renderer 调度、宿主布局和合成都能产生相似体感。

Flutter 现场要记录 Flutter/Engine 版本、根渲染模式、Impeller/Skia 配置、平台视图和外部纹理。Flutter 3.29 起默认线程模型出现 UI 与 platform thread 合并等变化，厂商或应用配置也可能改变线程布局。分析时按进程、线程活动和 Surface 所有权识别角色，避免只搜索 `Flutter UI` 这类固定名字。

若混合场景同时有宿主 Window 和独立内容层，给每条输出路径各画一条时间线，再在 SurfaceFlinger 的 DisplayFrame 汇合。只看宿主主线程会遗漏 renderer、Engine、MediaCodec 和独立 Producer。

导航：`2.11`、`7.11`、`18.12`、`18.13`。

### 7. 回前台慢与内存压力

回前台慢要先确认原进程是否存活：

- 进程存活、Activity 未重建：检查主线程恢复工作、锁、Binder、资源重建和数据刷新。
- 进程存活、Activity 重建：检查配置、状态恢复、资源加载和首帧。
- 进程已退出：按冷启动分析，并查退出原因、LMKD 和后台限制。

API 30+ 可通过 `ActivityManager.getHistoricalProcessExitReasons()` 读取 `ApplicationExitInfo`。`getReason()`、`getStatus()`、`getDescription()` 和可用的 `getTraceInputStream()`用于解释退出；`getPss()`、`getRss()`只是系统最近一次采样，采样时间可能早于退出，也可能返回 0。

低内存退出在不同设备上的上报方式可能不同。调用 `ActivityManager.isLowMemoryKillReportSupported()` 确认平台是否支持可靠的 LMK 原因；缺少该能力时，还要结合 bugreport、LMKD 日志、进程重要性和系统内存压力。

GC、page fault 或 PSS 上升只提供现象。根因仍要回到分配来源、工作集变化、文件映射、对象保留和进程重建的时间关系。

导航：`4.4`、`8.1`、`10.4`、`15.2`。

### 8. ANR 与 near-ANR

“卡死”要分成系统已记录的 ANR 和尚未达到超时的长停顿。前者有系统分类与 trace，后者依赖事前采样、应用 watchdog 或可重复 Perfetto。

API 30+ 的 `ApplicationExitInfo.getTraceInputStream()` 可在系统保留 trace 时读取 ANR 信息。Android 17 / API 37 新增 `getAnrInfo()`，可获取 ANR ID、类型、超时时长和用户可感知性；类型包括 input dispatch、无焦点窗口、broadcast、service、provider、job 与应用启动等。类型决定该还原哪条超时协议，不能把所有 ANR 都归到主线程长任务。

分析至少包含三份证据：

1. 系统记录的 ANR 类型、时间与目标进程。
2. ANR trace 中主线程及相关 Binder/锁持有线程的栈。
3. 超时前的时间线，用来区分执行、等待、调度饥饿和系统负载。

较旧系统常使用 `/data/anr/traces.txt`，较新系统通常在 `/data/anr/anr_*` 保存多份记录。直接拉取这些文件往往需要 root；普通量产设备应通过 bugreport、应用可访问的 `ApplicationExitInfo` 或 Play Console 获取。ANR 时刻的一份栈只代表采样瞬间，锁持有者和调用起点可能已经变化。

常见分流包括主线程 IO/计算、同步 Binder、锁竞争/死锁、广播或服务超时，以及系统长时间不给进程调度。每个结论都要指出等待对象或执行区间，并用调用方、持有者或全局 CPU 轨道补全因果。

导航：`9.1`、`9.2`、`9.3`、`15.5`。

### 9. 耗电、发热与卡顿同时出现

热问题需要时间顺序：温度上升、频率/可用 CPU 容量下降、Runnable 排队变长、帧或响应超时。只看到低频，无法区分 thermal 限制、调速器选择和低负载降频。

Perfetto 没有可跨设备依赖的通用 `android.thermal` 数据源。设备支持时，可采集这些入口：

- ftrace 的 `power/cpu_frequency`、`power/cpu_idle`、`power/suspend_resume`；
- 内核启用时的 `thermal/thermal_temperature`、`thermal/cdev_update`；
- `linux.sys_stats` 的 CPU 频率轮询；
- `android.power` 的电池计数器和 power rails，前提是设备导出相应数据；
- 应用、JobScheduler、WorkManager、网络和 wakelock 的时间线证据。

Android 17 内核锚点 `android17-6.18-2026-06_r6` 用于核对 cpufreq、thermal、调度与 fence 语义。厂商 thermal zone、cooling device、rail 名称和阈值属于设备实现，runbook 应记录原始名字，不能套用另一台设备的温度阈值。

短 Perfetto 适合回答某次卡顿前后发生了什么。Battery Historian 读取 Android 7+ bugreport，适合检查数小时尺度的 wakelock、Job、网络和电池状态。两者的时间尺度不同，结论应通过 UID 和时间窗口互相校验。

排查时依次确认：

1. 性能退化是否随温度和频率变化重复出现。
2. CPU/GPU/显示负载来自前台渲染、后台任务、网络重试还是第三方 SDK。
3. 频率下降前是否已经存在高负载，避免倒置因果。
4. 降低刷新率、关闭特效、暂停后台任务或冷却设备后，异常是否按预测变化。

导航：`13.3`、`15.2`、`15.5`。

## 设备条件会改变排障优先级

| 条件 | 优先检查 | 容易混淆的地方 |
|---|---|---|
| 低端机、小内存 | Runnable 排队、GC、page fault、解码、LMKD | 业务代码未变，资源余量却使尾延迟放大 |
| 90/120/144 Hz | 每帧 deadline、刷新率切换、CPU/GPU 尾延迟 | 固定使用 16.67 ms 会漏掉高刷超时 |
| 弱网、高延迟 | TTFD、数据依赖、重试、缓存状态 | 内容迟到常被写成动画卡顿 |
| 多窗口、浮窗、PIP | Window 可见性、Layer、刷新率、SF/HWC | 宿主主线程正常不代表所有窗口按时呈现 |
| 相机、视频、游戏 | 独立 Surface、GPU、fence、thermal | App Window 的帧统计可能没有覆盖内容帧 |
| 厂商系统 | tracing 可见性、调度/thermal 配置、HWC 能力 | AOSP 函数名和阈值不能直接套用 |

高刷场景要从 trace 中读取当时的显示周期。120 Hz 常见周期约为 8.33 ms，但可变刷新率、帧率投票和设备合成策略会改变 deadline，runbook 不应写死一个预算。

## trace 配置应服从问题

配置选择遵循“能回答当前假设”的原则：

| 场景 | 建议窗口 | 主要数据 |
|---|---|---|
| 滚动/动画 | 操作前 1—2 秒至结束后 1—2 秒 | FrameTimeline、gfx/view、sched、freq、SurfaceFlinger |
| 输入延迟 | 输入前短窗口至反馈帧后 | input、应用 marker、主线程、Binder/锁、FrameTimeline |
| 冷启动 | 拉起前至 TTFD 后 | app startup、atrace、sched、binder、page fault、FrameTimeline |
| ANR/near-ANR | 覆盖超时前数秒或更长 | sched、binder、lock/futex、主线程、系统负载、ANR 记录 |
| 发热卡顿 | 包含升温和退化过程，可配周期快照 | thermal、cpufreq、idle、sched、android.power、应用负载 |

长时间低概率问题可采用 Perfetto periodic trace snapshots，保持循环 buffer，在触发异常时保存快照。高频事件、调用栈和长窗口会增加开销；应先在目标设备验证 tracing 本身没有改变复现结果。

## 常见误判与纠偏

- **平均 FPS 掩盖尾延迟**：同时看帧间隔分布、连续坏帧和输入到呈现延迟。
- **主线程长 slice 等同于 App 责任**：核对该 slice 是否落在受影响 SurfaceFrame 的关键路径，并检查调度、Binder 与锁。
- **App 轨道黄色等同于 App 算慢**：FrameTimeline 中黄色 App slice 表示 SurfaceFlinger 侧 jank 影响了该帧。
- **Buffer Stuffing 等同于普通慢帧**：关注持续积压和 latency state，再核对 Producer/Consumer 推进。
- **Running 与 Runnable 混为一谈**：Running 追执行内容，Runnable 追 CPU 争抢、优先级和调度。
- **`releaseOutputBuffer()` 等同于视频已显示**：补上 BufferQueue、fence、SurfaceFlinger、HWC 和 present。
- **`dumpsys SurfaceFlinger` 某字段等同于稳定协议**：按设备版本保存原始输出，用 trace 和源码确认字段语义。
- **低频等同于热限频**：检查温度、cooling device、负载和频率变化的先后关系。
- **退出记录里的 PSS 等同于死亡瞬间内存**：把它标为最近采样，并注明是否为 0。
- **某个函数超过固定毫秒数就算异常**：预算取决于刷新率、管线阶段和是否位于关键路径。

## 团队 runbook 的交付格式

一份可复用的现场记录应包含：

1. **问题卡**：版本、设备、操作、网络、显示和复现率。
2. **体验时间线**：触发点、异常区间、恢复/超时点。
3. **输出路径**：App Window、SurfaceView、TextureView、WebView、Flutter 或多个 Layer。
4. **候选责任链**：MainThread、RenderThread、SurfaceFlinger、Binder、IO、调度、内存或 thermal。
5. **直接证据**：帧 token、线程 slice、调度状态、堆栈、日志与源码位置。
6. **对照试验**：只改变一个变量，并记录预测与结果。
7. **结论边界**：已证明什么、尚缺什么、适用哪些版本和设备。

结论模板可写成：

> 在设备 A、构建 B、120 Hz 和固定数据集下，输入后第一个反馈 SurfaceFrame 因主线程等待同步 Binder 42 ms 而错过 deadline；Binder 服务端同时在文件 IO。将调用移出输入路径后，同一脚本的反馈延迟 P95 从 X 降到 Y，FrameTimeline 中对应 App deadline miss 消失。当前证据只覆盖该设备与该构建。

这个模板保留了现象、路径、因果证据、对照和适用边界。后续维护者可以复跑同一脚本，也能知道哪些推断还没有证据。

## 现场导航

| 问题 | 继续阅读 |
|---|---|
| VSync、Choreographer、帧调度 | `7.1`、`7.3` |
| RenderThread、GPU、SurfaceFlinger | `7.4`、`7.5`、`18.7` |
| 输入分发和响应延迟 | `3.1`、`3.2`、`15.2` |
| 启动 TTID/TTFD | `8.1`、`8.2`、`8.3`、`15.6` |
| ANR | `9.1`、`9.2`、`9.3`、`15.5` |
| 内存和进程回收 | `4.4`、`10.4` |
| SurfaceView/TextureView/视频 | `18.4`、`18.6`、`18.15` |
| WebView/Flutter | `2.11`、`7.11`、`18.12`、`18.13` |
| 功耗与 thermal | `13.3`、`15.5` |

## 源码与官方资料

- [AOSP Android 17 `Choreographer`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java)
- [AOSP Android 17 `BufferQueueProducer`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BufferQueueProducer.cpp)
- [AOSP Android 17 `SurfaceFlinger`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp)
- [Android Common Kernel `android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/)
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [Perfetto CPU frequency and idle](https://perfetto.dev/docs/data-sources/cpu-freq)
- [Perfetto periodic trace snapshots](https://perfetto.dev/docs/getting-started/periodic-trace-snapshots)
- [Android 启动时间指南](https://developer.android.com/topic/performance/vitals/launch-time)
- [`ApplicationStartInfo` API](https://developer.android.com/reference/android/app/ApplicationStartInfo)
- [`ApplicationExitInfo` API](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [`ApplicationExitInfo.AnrInfo` API](https://developer.android.com/reference/android/app/ApplicationExitInfo.AnrInfo)
- [Android ANR 诊断指南](https://developer.android.com/topic/performance/vitals/anr)
- [JankStats 指南](https://developer.android.com/topic/performance/jankstats)
- [Android 16 KB page size 指南](https://developer.android.com/guide/practices/page-sizes)
- [Battery Historian 配置指南](https://developer.android.com/topic/performance/power/setup-battery-historian)
