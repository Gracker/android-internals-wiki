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

## 版本边界:不同 Android 版本的可用观察入口

本章引用的排障工具和指标,部分在 Android 12+ 才可用。在 Android 8-11 上排查时,需要回退到替代手段。

### FrameTimeline:Android 12+

`FrameTimeline` 是 Android 12(API 31)引入的 Perfetto 数据源,能直接在 trace 中标注每帧的 jank type(`AppDeadlineMissed`、`BufferStuffing`、`SurfaceFlingerCpuDeadlineMissed`、`SurfaceFlingerGpuDeadlineMissed`、`DisplayHAL`、`PredictionError` 等)。Android 8-11 没有 `FrameTimeline`,排查流畅性问题需要回退到以下入口:

- **gfx/view trace tag**:`adb shell setprop debug.atrace.tags.enableflags 0xA` 开启 `gfx` (0x2) + `view` (0x8) tag(0x200 对应的是 ATRACE_TAG_VIDEO,不是 gfx+view),在 Perfetto 中观察 `Choreographer#doFrame` slice 的耗时和 RenderThread 的 `DrawFrame` 区间
- **SurfaceFlinger slice**：按版本选择观察入口：Android 8-10 看 `handleMessageRefresh`；Android 11-12 看 `onMessageRefresh()`；Android 13+ 看 `SurfaceFlinger::commit()` 和 `SurfaceFlinger::composite()` 的 slice。`Output::composeSurfaces()` 仍可作为 CompositionEngine 侧的辅助锚点。如果 Perfetto 中找不到对应 slice，可通过 `SurfaceFlinger` 主线程的 sched 轨道结合 frame timeline 反推合成耗时
- **sched 轨道**:主线程和 RenderThread 的调度状态(Runnable / Sleeping / Uninterruptible),排查调度延迟和 CPU 争抢
- **FrameMetrics / JankStats**(Android 7.0+):通过 `Window.OnFrameMetricsAvailableListener` 或 `JankStats` 库在应用内采集帧耗时分布,作为 `FrameTimeline` 的应用侧替代

### ApplicationExitInfo:API 30+

`ApplicationExitInfo` 在 Android 11(API 30)引入,能查询进程退出的原因、状态和堆栈。Android 8-10 需要回退到:

- **traces.txt**:`adb pull /data/anr/traces.txt`,ANR 发生后系统写入的堆栈快照。注意这只记录 ANR 触发时刻的主线程栈,不含 ANR 前的时间线
- **logcat / EventLog**:过滤 `ActivityManager` 和 `Process` 相关 tag,观察进程被杀的信号和原因(如 `Low Memory Killer`、`Background anr`)
- **bugreport**:完整的系统状态转储,包含进程列表、内存分布、LMKD 记录。对内存压力导致的进程回收,bugreport 比单一 traces.txt 信息更全

### BufferStuffing 识别

`BufferStuffing` 作为 jank type 标注是 Android 12+ `FrameTimeline` 的能力。Android 8-11 没有 `BufferStuffing` 标签,但可以通过以下方式间接识别:

- **帧间隔观察**：在 `Choreographer#doFrame` slice 中，如果连续帧的 Actual Present 持续落后 Expected Present 并呈递增趋势，管线积压（潜在的 BufferStuffing）是候选根因之一。需结合 BufferQueue slot 状态和 jank type 做交叉验证，不能仅凭帧间隔就下结论
- **BufferQueue 状态**:`adb shell dumpsys SurfaceFlinger` 中查看对应 Layer 的 `BufferQueue` 槽位状态,如果多个 slot 处于 `QUEUED` 态,说明帧堆积
- **Input → doFrame 延迟**:从 Input 事件时间戳到对应 `doFrame` 开始时间的差值异常增大,通常伴随输入延迟体感

### 排障入口版本速查

| 工具 / 指标 | 可用版本 | Android 8-11 替代 |
|---|---|---|
| FrameTimeline | Android 12+ | gfx/view/sched trace + FrameMetrics |
| ApplicationExitInfo | API 30+ | traces.txt + logcat + bugreport |
| BufferStuffing 标签 | Android 12+ | 帧间隔观察 + BufferQueue dump |
| JankStats | Android 7.0+ | 直接可用(但不如 FrameTimeline 信息丰富) |
| Perfetto `actual_frame_timeline_slice` / `expected_frame_timeline_slice` 表 | Android 12+ | `slice` 表中过滤 `Choreographer` / `DrawFrame` |

---

## 为什么单独写这一章

前面几章把原理、工具和分析方法拆得很细。这种写法适合系统学习,但到了真实现场,读者最先遇到的问题往往不是"Choreographer 是怎么工作的",而是"用户说卡,这次先从哪看起"。

这两种需求并不冲突。前面的章节负责把问题讲透,这一章负责把它们重新接回真实工作流。它更像一张地图,告诉读者从投诉到结论之间,第一步该往哪里走。

如果只会看单点知识,不会把问题放回场景,排障就很容易出现两种极端:要么见到一个长 slice 就一路追下去,要么因为线索太多,到头来什么也没追出来。场景化手册的作用,就是先把问题压缩到一个足够小的范围里。

## 排障前先分类,再深入细节

现场排障最容易犯的错误是分类没做就一头扎进具体路径。

用户的一句"卡",背后可能是:

- 掉帧
- 输入延迟
- 启动慢
- 前后台恢复慢
- 内存压力
- 接近 ANR

如果第一步就把它当成某一种问题,后面抓 trace、看线程、找责任路径都可能一路跑偏。
所以排障要先做分类,再做深入分析。

## 一个统一的四步框架

不管现场是什么问题,先按下面四步走:

1. **先定类**
   这是掉帧、响应慢、ANR、内存压力,还是混合问题?

2. **再定窗口**
   问题发生在点击后的 300ms、首帧前 3 秒,还是前后台切换的某个阶段?

3. **再定责任链**
   MainThread、RenderThread、SurfaceFlinger、Binder、IO、调度,哪条路径最可疑?

4. **深入到具体代码和工具**
   确定责任链后,再决定要不要继续上 SQL、heap dump、stack sampling 或 btrace。

这四步看起来普通,但它背后的约束非常强:每一步都在缩小问题空间。经验价值在于知道应该先砍掉哪些不相关方向。

## 用户的"卡",先翻译成技术问题

用户不会说"这像是 AppDeadlineMissed",也不会说"这应该查 `ApplicationExitInfo`"。他只会说"卡""慢""像死掉了一样"。这时候工程师的第一职责,是把投诉翻译成可分析的问题。

| 用户说法 | 第一判断 | 第一观察点 |
|---|---|---|
| "滑动一卡一卡的" | 狭义流畅性 / jank | `FrameTimeline`、`doFrame`、`RenderThread` |
| "点了没反应" | 输入延迟 / 响应慢 | Input → MainThread → Binder / IO |
| "打开页面要等很久" | 启动或页面可交互时间过长 | TTID / TTFD、首屏数据路径 |
| "界面像死掉了一样" | ANR 或接近 ANR | 主线程栈、`ApplicationExitInfo`、`traces.txt` |
| "越用越卡,回前台更慢" | 内存压力 / 进程回收 / page fault | PSS、GC、LMKD、冷 / 温 / 热启动切换 |
| "耗电快 / 手机发烫，同时卡" | 功耗/发热伴随卡顿 | Battery Historian、Perfetto power rails、Thermal/CPU frequency 轨道 |

这张表的价值在于逼着读者先问一句:**我现在看到的,到底是哪一类体验失效?**

**耗电/发热伴随卡顿**：这类问题经常是热限频和资源争抢叠加的结果。排查时先确认因果关系——是功耗导致的性能退化，还是性能问题触发了功耗异常。

排障顺序：
1. **先看温度与频率**：在 Perfetto 中打开 `thermal` 和 `cpufreq` 轨道。如果核心频率随温度上升持续下降，说明系统已进入热限频。Android 13+ 的 `android.thermal` 数据源可直接观察 thermal severity level。
2. **看唤醒源**：打开 `wakelock` 轨道，确认是否有长时间持有的 partial wake lock 或 kernel wakelock 阻止了 CPU 进入深度休眠。Battery Historian 的 `Wakelocks` 图表对 24 小时尺度的唤醒摘要比 Perfetto 更直观。
3. **看后台任务与网络**：`JobScheduler` slice 和 `Network` 轨道可以判断是否有高频的定时任务、周期性网络同步或 WorkManager 重试循环在后台持续消耗 CPU。
4. **看渲染负载**：如果功耗异常集中在交互场景，回到 MainThread / RenderThread / GPU 轨道确认是否存在超预算渲染（如 120Hz 无法维持、过度绘制或大纹理频繁上传）。
5. **Battery Historian 做全时段摘要**：单次 Perfetto trace 难以覆盖电池整体表现，用 `adb bugreport` 或 Battery Historian 看全天的耗电排行、唤醒频次和网络传输量，再指向具体可疑的 UID/时间段。

核心分流原则：温度持续上升（thermal throttling active）→ 找 CPU/GPU 负载源头；唤醒频率异常 → 看 wakelock + JobScheduler + 网络重试；耗电分布集中在某 UID → 排除后台异常任务或 SDK 轮询。

> 本小节内容基于 AOSP Perfetto 文档和 Battery Historian 官方指南。所述排障路径为通用方法框架，具体阈值（如温度触发点、wakelock 合理时长）需结合设备 SoC 型号和系统配置判断。

## 八类最常见的性能现场

### 1. 冷启动慢

冷启动慢最常见的误判,是把"已经看到画面"误当成"启动结束"。
很多应用的 TTID 并不难看,拖慢体感的是 TTFD。

排这类问题时,先看四件事:

- TTID
- TTFD
- `reportFullyDrawn()`
- 首屏数据加载和骨架屏退出时机

实际落手顺序可以很简单:

1. 先分清这次是冷、温还是热启动,不要混在一起看。
2. 对照 TTID 和 TTFD,先分清"首帧慢"还是"可交互慢"。
3. 抓一次完整冷启动 trace。
4. 如果 TTID 正常但 TTFD 差,先查 Application 初始化、首屏数据和可交互边界。
5. 如果应用以 4KB page-alignment 编译但运行在 16KB 页设备上,冷启动的 `mmap` + page fault 开销会额外增加。检查 APK 内 `.so` 文件的 ELF LOAD segment alignment 是否为 16KB(`readelf -l libxxx.so | grep LOAD`),非 16KB alignment 的库在 16KB 设备上会触发兼容模式拷贝,PSS 飙升且无法享受大页加速红利。

这一类问题最容易掉进"感觉已经打开了,所以不算慢"的误区。对用户来说,画面出现只是第一步,能不能开始用才是第二步。
对应章节:`8.1`、`8.2`、`8.3`、`15.6`。

### 2. 列表滑动卡顿

列表卡顿是最典型、也最容易被误判的一类问题。很多人第一反应是去看 `onBindViewHolder()`,这当然没错,但如果还没确认 jank 到底落在哪一层,这个动作还是太早。

先看:

- `FrameTimeline`
- Janky Frame Rate
- `RecyclerView` 的 bind / layout / prefetch 相关工作

再抓:

- 一段稳定滑动过程的 Perfetto
- 必要时补 FrameMetrics / JankStats 线上样本

再排:

- MainThread 的 `doFrame`
- RenderThread 的 `DrawFrame`
- 图片解码
- DiffUtil
- 布局层级

比较稳的顺序是:

1. 先确认是持续性掉帧,还是偶发长帧。
2. 先看 `FrameTimeline` 的 `Jank Type`,不要只看主线程颜色。
3. 再分流到 MainThread、RenderThread、SurfaceFlinger。
4. 再回到具体控件、图片、DiffUtil 和业务代码。

这里最常见的误判,是见到滑动卡,就默认问题一定在 UI 线程。实际工程里,图片线程抢 CPU、RenderThread 超时、SurfaceFlinger 合成变慢都很常见。
对应章节:`7.3`、`7.4`、`7.5`、`18.2`、`18.7`。

### 3. 页面切换慢,或者切页动画不顺

页面切换问题经常有两种长相:

- 动画本身不顺
- 动画顺,但内容来晚了

这两类问题的责任链完全不同。前者更偏流畅性,后者更偏响应速度和数据就绪。

排这类问题时,先做一个粗判断:
点击之后,页面是不是很快切过去了,只是内容空着?如果是,先看内容加载路径,再看动画。

比较稳的顺序是:

1. 先确定慢的是动画,还是内容。
2. 看点击事件后第一段空白时间花在哪里。
3. 如果页面很快出现但内容迟到,回到响应速度和数据加载路径。
4. 如果动画本身掉帧,再回到 MainThread / RenderThread / SurfaceFlinger。

很多"切页卡"往往不是切页动画的问题,而是切页后数据、骨架屏、图片、路由初始化堆在一起,用户把它统称成"切页卡"。
对应章节:`7.4`、`8.4`、`1.4`、`1.5`。

### 4. 输入延迟高,但不一定掉帧

这一类问题最容易被误判成普通慢帧。用户的感觉是"点了没反应",但等一会儿画面还是动了。问题往往不在渲染本身,而在输入到反馈之间的等待。

先看:

- Input 事件到 `doFrame` 的时差
- 主线程是否长时间 Runnable
- 是否出现 BufferStuffing 或 high latency state。Perfetto UI 的 FrameTimeline 轨道用浅绿色(Light Green)表示 high latency state:帧率看起来平滑,但帧整体晚呈现,输入延迟升高。Actual Present 稳定落后 Expected Present 只能作为 BufferStuffing 候选信号,需要结合 `jank_type`、BufferQueue slot 状态或 `dequeueBuffer()` 阻塞一起确认

再排:

- InputReader / InputDispatcher
- MainThread 调度
- 锁等待
- Binder 等待

一个可靠的做法是:

1. 从触摸事件落点开始量输入到视觉反馈的窗口。
2. 看主线程是不是长时间 Runnable。
3. 看是否有 Binder reply wait 或锁等待。
4. 再判断是 App 自己堵住了,还是系统没给到 CPU。

这类问题的难点在于太容易看错成渲染问题。
对应章节:`3.1`、`3.2`、`7.1`、`15.2`。

### 5. 视频列表、SurfaceView、TextureView 场景卡

只要界面里出现独立 Surface,排障路径就要立刻切换。因为这时候 UI 帧和视频帧很可能已经不是同一条路径了。

先看:

- 独立 Surface 数量
- App UI 和视频渲染是否互相争抢
- HWC overlay 是否命中

再抓:

- App 进程
- SurfaceFlinger
- GPU / composition 相关轨道

再排:

- SurfaceView / TextureView 选型
- BufferQueue 堵塞
- 合成路径切换

实际顺序通常是:

1. 先确认是 UI 卡,还是视频画面卡。
2. 看独立 Surface、Layer 数量和合成路径。
3. 看 App 线程和 SurfaceFlinger 谁在超时。
4. 再回到容器选型和播放器实现。

这类问题最典型的误判,就是把所有掉帧都归到 UI 线程。
对应章节:`18.4`、`18.6`、`18.7`、`18.15`。



### 5.1 BufferQueue 堵塞的 Perfetto 源码级特征

在视频列表、SurfaceView 这类场景中，卡顿的根因经常落在 `BufferQueueProducer::dequeueBuffer()` 的锁等待上。通过 AOSP 源码(android14-release)可以精确定位以下四类 Perfetto 特征:

#### 特征 1:dequeueBuffer 线程 slice 拉长

`BufferQueueProducer::dequeueBuffer()` 在 Perfetto 中有对应的 `ATRACE_CALL()` 函数级 slice。正常情况下该 slice 应小于 1ms;超过 5ms 说明发生了锁等待。

源码位置:`frameworks/native/libs/gui/BufferQueueProducer.cpp, 行 389-630`

关键等待路径(行 452):
```cpp
status_t status = waitForFreeSlotThenRelock(FreeSlotCaller::Dequeue, lock, &found);
```

`waitForFreeSlotThenRelock()`(行 283-389)在 `mCore->mDequeueCondition` 上等待,默认为无限等待(`mDequeueTimeout = -1`),这是 SurfaceView 卡顿的根因之一。

#### 特征 2:mDequeueCondition 条件变量等待

`mDequeueCondition.wait()`(行 381)是 pthread condition variable 等待。当 SurfaceFlinger 来不及 `acquireBuffer()` 消费队列时,Producer 线程会在此阻塞,状态变为 `Sleeping` 或 `Uninterruptible`。

#### 特征 3:mQueue.size() > 1(队列积压)

`NATIVE_WINDOW_CONSUMER_RUNNING_BEHIND` 查询(行 1197)返回 `true` 时,`mQueue.size() > 1`,说明 Consumer 消费速度跟不上 Producer 生产速度。Perfetto 中搜索 `BufferQueueConsumer::acquireBuffer` 的 `PRESENT_LATER` 返回值频率可判断积压程度。

#### 特征 4:TIMED_OUT 返回值

当 `mDequeueTimeout >= 0`(应用设置过超时)时,`waitForFreeSlotThenRelock()` 在超时后返回 `TIMED_OUT`(行 376-378)。SurfaceView 默认无限等待,不会出现此返回值;但 Camera preview 等场景会设置超时。

**Perfetto 中的实际搜索关键词**:
- `BufferQueueProducer::dequeueBuffer` - Producer 侧取 buffer 耗时 slice
- `BufferQueueConsumer::acquireBuffer` - Consumer 侧取 buffer 耗时 slice
- `PRESENT_LATER` - Consumer 主动推迟的 trace 事件
- `NATIVE_WINDOW_CONSUMER_RUNNING_BEHIND` - 来自 `query()` 的状态值
- `android.surfaceflinger.frametimeline` 数据源中的帧时间线(对应 `actual_frame_timeline_slice` / `expected_frame_timeline_slice` 表)

详情见调研报告:[2026-05-07-bufferqueue-blocking-perfetto-patterns.md](https://github.com/gracker/DeepResearch/blob/main/2026-05-07-bufferqueue-blocking-perfetto-patterns.md)


### 6. WebView、Flutter、混合栈场景卡

这一类问题的难点在于:宿主和引擎经常不在同一条线程里。只看宿主主线程,结论经常不完整。

先看:

- 宿主线程和引擎线程谁在超时
- 是否存在双重合成

再抓:

- 带线程名的 Perfetto
- Chromium / Flutter 相关线程

再排:

- 平台视图混合
- 纹理采样与拷贝
- JavaScript / 页面资源加载
- 宿主侧布局

这类问题的经验是:不要默认"宿主应用的主线程 = 唯一瓶颈"。
对应章节:`2.11`、`7.11`、`18.12`、`18.13`。

### 7. 前后台切换后明显变慢

"回前台慢"最容易把人带到启动优化的路径里,但它经常是内存和进程生命周期问题。

先看:

- 这次是热启动、温启动还是已经变成冷启动
- 是否有 page fault、GC、LMKD 痕迹

再抓:

- 回前台前后 5-10 秒的 trace

再排:

- 进程是否被杀
- Activity 是否重建
- 内存回收
- 后台任务恢复

比较稳的顺序是:

1. 先分清这次到底是热启动、温启动还是冷启动。
2. 看进程有没有被系统杀掉。
3. 看回前台前后有没有 page fault、GC、LMKD、进程重建。
4. 再决定是启动问题还是内存问题。

麻烦的地方在于它"看起来很像启动慢"。
对应章节:`4.4`、`8.1`、`10.4`、`15.2`。

### 8. 用户说"卡死了"

当用户用"卡死了"来描述问题时,第一反应不应该是"这一定是 ANR",而应该是先确认系统有没有把它当成 ANR。

先看:

- 是不是 ANR
- 还是长时间无响应但尚未超时

再抓:

- `ApplicationExitInfo`
- `traces.txt`
- 必要时抓 ANR 前后的 Perfetto

再排:

- 主线程栈
- Binder reply wait
- 锁竞争
- 主线程 IO
- 系统高负载

顺序通常是:

1. 先确认是不是系统认定的 ANR。
2. 拉 `ApplicationExitInfo`、`traces.txt`、主线程堆栈。
3. 还原 ANR 前 5 秒窗口。
4. 再决定是 Binder、锁、IO、调度还是业务长任务。

这一类问题最容易犯的错,是只看 ANR 对话框弹出后的堆栈,不去看 ANR 前面的时间线。
对应章节:`9.1`、`9.2`、`9.3`、`15.5`。

## 同一个现象,在不同设备上的第一怀疑点不同

同样是"卡",在不同设备和场景里,第一怀疑点并不一样。

| 条件 | 先验怀疑 | 说明 |
|---|---|---|
| 低端机 / 小内存 | 调度、GC、page fault、图片解码 | 资源压力更容易放大 |
| 高刷设备 | deadline 更紧、尾部延迟更显眼 | 120Hz 下 8.33ms 很容易超 |
| 弱网 / 海外网络 | TTFD、页面切换、首屏骨架加载 | 先分离渲染问题和数据就绪问题 |
| 多窗口 / 浮窗 / PIP | SurfaceFlinger、BufferQueue、合成路径 | 不要只盯 App 主线程 |
| 游戏 / 视频场景 | GPU composition、独立 surface、thermal | UI 线程经常不是主瓶颈 |

这张表的意义是提醒一件事:排障顺序应该跟着设备现实走,不要死背模板。

## 抓 trace 时,先求回答问题,不求一次最全

抓 trace 最常见的坑是配置不对——事件类别没开全或者窗口太短。建议先保守一点：

- **滑动 / 动画卡顿**:抓 5-10 秒,保留 `gfx`、`view`、`sched`、`input`、`wm`
- **启动慢**:抓冷启动全过程,最好从拉起前开始
- **疑似 ANR**:抓问题前后更长窗口,必要时结合 `ApplicationExitInfo`
- **低概率线上问题**:先用指标缩小范围,再用异常触发补采 trace

抓 trace 的目标,是先保证这份数据能回答当前最关键的因果关系。抓太大、抓太久,分析反而容易散。

## 先看哪条责任链

| 现象 | 第一责任链 |
|---|---|
| 帧超时 | MainThread → RenderThread → SurfaceFlinger |
| 点击后没反应 | Input → MainThread → Binder / Lock / IO |
| 页面内容迟迟不出现 | 启动路径 / 数据加载 / TTFD |
| 一切都慢 | 调度 / Thermal / 内存压力 / 系统负载 |
| 只有特定渲染容器慢 | BufferQueue / Surface / GPU composition |

这张表有一个重要前提:**同一个问题可以跨路径传导**。
首屏慢,起点可能是启动任务过重,表现却是首帧晚;列表滑动卡,根因也可能是图片线程把 CPU 抢满了。

所以"第一责任链"不是最终结论,它只是排障的第一个锚点。

## 最容易出现的误判

- **把平均 FPS 当成全部真相**:平均值会掩盖尾部延迟。
- **把 SurfaceFlinger 责任误判成 App jank**:黄帧不天然等于 App 有问题。
- **把高输入延迟误判成普通掉帧**:BufferStuffing 场景尤其容易看错。
- **把系统高负载当成业务代码慢**:先看 Runnable,再看全局 CPU。
- **只看一段堆栈,不看时间线**:ANR 和流畅性问题都需要时序证据。
- **把首帧出现误当成页面完成**:TTID 正常不代表 TTFD 正常。
- **把"只有某些机型差"误当成偶现**:机型聚类往往说明这是结构性问题。
- **把"线下复现不了"误当成无问题**:线上会话上下文常常比本地单次操作更重要。

## 场景化 Perfetto SQL 快速筛选

每个场景对应的关键 SQL 查询,可以配合 trace 数据做批量初筛:

| 场景 | 关键 SQL | 说明 |
|---|---|---|
| 掉帧 / jank | `SELECT * FROM actual_frame_timeline_slice WHERE jank_type IS NOT NULL AND jank_type != 'None'` | 捞出所有 jank 帧,按 jank_type 分类 |
| BufferStuffing | `SELECT * FROM actual_frame_timeline_slice WHERE jank_type = 'Buffer Stuffing'` | SQL 字段值为 `Buffer Stuffing`; Perfetto UI 中 FrameTimeline 轨道显示为浅绿色 |
| 冷启动 | `SELECT name, ts, dur FROM slice WHERE name LIKE '%ActivityManager%' AND name LIKE '%start%'` | 定位 AMS 启动调度链 |
| ANR | `SELECT * FROM slice WHERE name LIKE '%ANR%'` | 结合 `ApplicationExitInfo` 时间线 |
| Input 延迟 | `SELECT (doFrame_ts - input_ts) AS latency FROM ...` | 输入事件到 `doFrame` 的时差 |
| GC 暂停 | `SELECT * FROM slice WHERE name LIKE '%GC%' AND name LIKE '%pause%'` | GC 暂停对帧预算的侵占 |

使用建议:先跑对应 SQL 做场景初筛,确认命中后,再回到 Perfetto UI 做逐帧时间线分析。10GB 量级的大 trace 用 SQL 比人工滚动轨道效率高一个数量级。

## 这份手册怎么用

它最适合三种场景:

1. 线上问题刚到手时,快速决定先抓什么。
2. 团队复盘时,把经验积累成固定排查路径。
3. 给新人做训练时,用真实投诉倒推章节和工具。

如果团队已经有值班和灰度治理机制,下一步就可以把这份手册继续拆成自己的 runbook:

- 哪类问题先由客户端同学看
- 哪类问题需要系统 / ROM 协作
- 哪类问题必须补抓 trace 才能继续
- 哪类问题可以直接回到指标平台做聚类

做到这一步,性能排障才从个人经验变成团队资产。

## 参考资料

### HWC Overlay Plane Capability 与 SurfaceFlinger 合成降级实战验证
- 来源:/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-22-hwc-overlay-plane-capability-sf-composition-downgrade.md
- 类型:DeepResearch 调研结果
- 摘要:梳理 HWC2/HWC2.4 Overlay Plane 能力查询机制、SurfaceFlinger 合成决策链(validateDisplay→getChangedCompositionTypes→acceptDisplayChanges)、DEVICE→CLIENT 降级触发条件(Layer 超出 Plane 数/像素格式/混合模式/旋转缩放),以及高通/联发科 HWC 实现差异。包含 Perfetto android.surfaceflinger.frametimeline 证据收集路径。
- 注入时间:2026-05-23
- 价值:源码级分析,包含 AOSP 路径交叉验证和版本边界澄清,可作为章节内容的补充参考材料
