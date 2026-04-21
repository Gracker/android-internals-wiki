---
title: "场景化性能作战手册"
chapter: "7.15"
section: "7.15"
status: ready-for-review
drafted_date: "2026-04-21"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) - Android 16 (API 36)"
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
related_chapters: ["7.1", "7.3", "8.2", "9.3", "13.3", "15.2"]
pipeline_stage: task9_pending
task6_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: "2026-04-21"
task6_result: pass-light-edit
task9_state: pending
---

# 场景化性能作战手册

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 把常见性能投诉映射到统一排障入口：卡顿 / 响应慢 / ANR / 内存 / 功耗
- 🔹 每类问题先看什么指标、抓什么 trace、优先排哪条链路
- 🔹 不同场景的第一嫌疑人：MainThread / RenderThread / SurfaceFlinger / Binder / IO / 调度
- 🔹 常见误判：把系统负载当成 App 问题、把输入延迟当成掉帧、把 BufferStuffing 当成普通慢帧
- 🔹 用章节跳转形成“现场排障导航”

### 扩展（可选深入）

- 🔸 针对低端机 / 高刷 / 弱网 / 多窗口做差异化排障
- 🔸 把作战手册转成团队内部 checklist / runbook
<!-- outline-end -->

## 为什么需要一份作战手册

掌握 Android 性能原理和拿到线上问题，之间还有一道很大的鸿沟。实际工作里，大家面对的往往不是“解释一下 Choreographer”，而是“为什么这个列表在某台机器上滑不动”“为什么这个页面首帧到了但内容半天不出来”“为什么用户说卡，trace 却看不到红帧”。

这时候最有用的不是再看一遍原理图，而是一份能快速把问题导向正确章节和工具的手册。它的目标不是替代详细分析，而是帮我们在最短时间内走对第一步。

## 一个统一的现场排障四步法

无论是启动慢、滑动卡还是疑似 ANR，大多数问题都可以先按下面四步走：

1. **先定类**：这是 jank、响应慢、ANR、内存压力还是混合问题？
2. **再定窗口**：问题发生在点击后的 500ms、首帧前 3 秒，还是前后台切换的某个阶段？
3. **后定责任链**：MainThread、RenderThread、SurfaceFlinger、Binder、IO、调度，哪条链最可疑？
4. **最后再钻深**：确认了责任链，再决定要不要上更重的工具，如 SQL、heap dump、stack sampling 或 btrace。

这套顺序的价值，是避免一开始就陷入细节。很多排障失败，并不是因为不会看 trace，而是太早去追某个局部 slice，忘了先确定问题属于哪一类。

## 先把投诉翻译成技术问题

| 用户说法 | 技术上的第一判断 | 第一观察点 |
|---|---|---|
| “滑动一卡一卡的” | 狭义流畅性 / jank | `FrameTimeline`、`doFrame`、`RenderThread` |
| “点了没反应” | 输入延迟 / 响应慢 | Input → MainThread → Binder / IO |
| “打开页面要等很久” | 启动或页面可交互时间过长 | TTID / TTFD、首屏数据链路 |
| “界面像死掉了一样” | ANR / 接近 ANR | 主线程栈、`ApplicationExitInfo`、`traces.txt` |
| “越用越卡，退后台再回来更慢” | 内存压力 / 进程回收 / page fault | PSS、GC、LMKD、冷/温/热启动切换 |

## 常见场景速查

### 1. 冷启动慢

- 先看：TTID、TTFD、`reportFullyDrawn()`、首帧前的 `Application` / `ContentProvider` / 首屏数据加载。
- 先抓：冷启动 Macrobenchmark + Perfetto。
- 先排：`ActivityThread.main()` 到首帧之间的主线程、Binder、dex2oat / profile 状态、启动任务依赖。
- 常见误判：把 splash 页出现误当成“启动完成”；把网络首屏加载问题和纯冷启动问题混在一起。
- 对应章节：`8.1`、`8.2`、`8.3`、`15.6`。

### 2. 列表滑动卡顿

- 先看：`FrameTimeline`、Janky Frame Rate、`RecyclerView` bind / layout / prefetch。
- 先抓：滑动过程 Perfetto，必要时补 FrameMetrics / JankStats 线上样本。
- 先排：MainThread 的 `doFrame`、RenderThread `DrawFrame`、图片解码、DiffUtil、过深布局层级。
- 常见误判：只盯 MainThread，不看 RenderThread / SurfaceFlinger；把图片加载抖动误判成布局问题。
- 对应章节：`7.3`、`7.4`、`7.5`、`18.2`、`18.7`。

### 3. 页面切换慢或切页动画不顺

- 先看：输入到页面可见的完整链路，区分“动画掉帧”还是“页面内容没准备好”。
- 先抓：点击事件前后 3-5 秒 Perfetto。
- 先排：Binder 往返、Fragment 事务、路由初始化、首屏数据、过重转场动画。
- 常见误判：把“动画先顺后空白”当成流畅问题，实际上是 TTFD 问题。
- 对应章节：`7.4`、`8.4`、`1.4`、`1.5`。

### 4. 输入延迟高，但不一定掉帧

- 先看：Input 事件到 `doFrame` 的时差、主线程是否长时间 Runnable、是否出现 BufferStuffing。
- 先抓：Input、View、sched、wm 类别的 Trace。
- 先排：InputReader / InputDispatcher、MainThread 调度、锁等待、Binder 等待。
- 常见误判：看到屏幕最终动了，就以为只是普通慢帧；实际上可能是输入排队导致的 high latency state。
- 对应章节：`3.1`、`3.2`、`7.1`、`15.2`。

### 5. 视频列表 / SurfaceView / TextureView 场景卡

- 先看：独立 Surface 数量、App UI 和视频渲染是否互相争抢、HWC overlay 是否命中。
- 先抓：App 进程 + SurfaceFlinger + GPU / composition 相关轨道。
- 先排：SurfaceView / TextureView 选型、BufferQueue 堵塞、合成链路切换。
- 常见误判：把所有掉帧都归到 UI 线程；实际上视频帧和 UI 帧经常是两条链路。
- 对应章节：`18.4`、`18.6`、`18.7`、`18.15`。

### 6. WebView / Flutter / 混合栈场景卡

- 先看：宿主线程和引擎线程谁在超时，是否存在双重合成。
- 先抓：带线程名的 Perfetto，并关注 `org.chromium`、Flutter raster / platform 线程。
- 先排：平台视图混合、纹理拷贝、JavaScript / 页面资源加载、宿主侧重布局。
- 常见误判：只看宿主 App 的 `doFrame`，忽略 WebView / Flutter 自己的线程。
- 对应章节：`2.11`、`7.11`、`18.12`、`18.13`。

### 7. 前后台切换后明显变慢

- 先看：这次是热启动、温启动还是已经变成冷启动；是否有 page fault、GC、LMKD 痕迹。
- 先抓：回到前台前后 5-10 秒 Trace。
- 先排：进程是否被杀、Activity 是否重建、内存回收、后台任务恢复。
- 常见误判：把“回前台慢”当成纯启动问题，但根因可能是低内存下的系统回收策略。
- 对应章节：`4.4`、`8.1`、`10.4`、`15.2`。

### 8. 用户说“卡死了”

- 先看：是不是 ANR，还是长时间无响应但尚未超时。
- 先抓：`ApplicationExitInfo`、`traces.txt`、必要时抓 ANR 前后的 Perfetto。
- 先排：主线程栈、Binder reply wait、锁竞争、主线程 IO、系统高负载。
- 常见误判：只看 ANR 对话框触发后的堆栈，而不看 ANR 前 5 秒内的系统状态。
- 对应章节：`9.1`、`9.2`、`9.3`、`15.5`。

## 不同设备条件下，先验怀疑应该不同

同一个现象，在不同设备条件下的第一嫌疑人并不一样。

| 条件 | 先验怀疑 | 说明 |
|---|---|---|
| 低端机 / 小内存 | 调度、GC、page fault、图片解码 | 资源压力更容易放大 |
| 高刷设备 | 帧 deadline 更紧、尾部延迟更显眼 | 120Hz 下 8.33ms 很容易超 |
| 弱网 / 海外网络 | TTFD、页面切换、首屏骨架加载 | 先分离渲染问题和数据就绪问题 |
| 多窗口 / 浮窗 / PIP | SurfaceFlinger、BufferQueue、合成链路 | 不要只盯 App 主线程 |
| 游戏 / 视频场景 | GPU composition、独立 surface、thermal | UI 线程常常不是主瓶颈 |

所以作战手册不能只写“遇到卡就看 doFrame”。真正的经验，是根据设备和场景先调整怀疑顺序。

## 最小抓取策略

很多团队抓 trace 的第一个问题不是“不会看”，而是“抓得不对”。下面给一个偏保守的最小策略：

- **滑动 / 动画卡顿**：抓 5-10 秒，保留 `gfx`、`view`、`sched`、`input`、`wm`
- **启动慢**：抓冷启动全过程，最好从拉起前开始
- **疑似 ANR**：抓问题前后更长窗口，必要时结合 `ApplicationExitInfo`
- **低概率线上问题**：先用指标缩小范围，再用异常触发补采 trace

要点不是一次把所有源都打开，而是先保证“能回答这次问题最关键的那个因果关系”。  
抓太大、抓太久，反而会降低分析效率。

## 先看哪条链路

| 现象 | 第一责任链 |
|---|---|
| 帧超时 | MainThread → RenderThread → SurfaceFlinger |
| 点击后没反应 | Input → MainThread → Binder / Lock / IO |
| 页面内容迟迟不出现 | 启动链路 / 数据加载 / TTFD |
| 一切都慢 | 调度 / Thermal / 内存压力 / 系统负载 |
| 只有特定渲染容器慢 | BufferQueue / Surface / GPU composition |

这个表还有一个隐含前提：**同一个问题可以跨链路传导**。例如首屏慢，可能起点是启动任务过重，但最后表现为首帧晚；列表滑动卡，也可能根因不是布局，而是图片线程把 CPU 抢满了。

所以“第一责任链”不是最终定论，只是现场排障的第一锚点。

## 常见误判清单

- **把平均 FPS 当成全部真相**：平均值会掩盖尾部延迟。
- **把 SurfaceFlinger 责任误判成 App jank**：黄帧并不天然等于 App 有问题。
- **把高输入延迟误判成普通掉帧**：BufferStuffing 场景尤其容易看错。
- **把系统高负载当成业务代码慢**：先看 Runnable、再看全局 CPU。
- **只看一段堆栈，不看时间线**：ANR 和流畅性问题都需要时序证据。

再补三个很实战的误判：

- **把首帧出现误当成页面完成**：TTID 正常不代表 TTFD 正常。
- **把“只有某些机型差”误当成偶现**：机型聚类往往恰恰说明是结构性问题。
- **把“线下复现不了”误当成无问题**：线上会话上下文通常比本地单次操作更重要。

## 使用方式

这份手册最适合做三件事：

1. 线上问题刚到手时，帮助快速决定先抓什么。
2. 团队复盘时，把“靠经验”沉淀成固定排查路径。
3. 给新人做入门训练时，用真实投诉倒推章节和工具。

更进一步的用法，是把这份手册拆成团队自己的值班 runbook：

- 哪类问题先由客户端同学看
- 哪类问题需要系统 / ROM 协作
- 哪类问题必须补抓 trace 才能继续
- 哪类问题可以直接回到指标平台做聚类

做到这一步，性能排障才真正从“个人经验”变成“团队资产”。
