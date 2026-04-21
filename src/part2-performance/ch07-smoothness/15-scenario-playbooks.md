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
related_chapters: ["7.1", "7.3", "8.2", "9.3", "13.3", "15.2", "15.5", "15.6"]
pipeline_stage: task6_pending
task6_state: revisiting
reviewed_by: openclaw-task6
reviewed_date: "2026-04-21"
task6_result: pass-light-edit
task9_state: pending
repaired_date: "2026-04-21"
repaired_by: "codex"
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

## 为什么单独写这一章

前面几章把原理、工具和分析方法拆得很细。这种写法适合系统学习，但到了真实现场，读者最先遇到的问题往往不是“Choreographer 是怎么工作的”，而是“用户说卡，这次先从哪看起”。

这两种需求并不冲突。前面的章节负责把问题讲透，这一章负责把它们重新接回真实工作流。它更像一张地图，告诉读者从投诉到结论之间，第一步该往哪里走。

如果只会看单点知识，不会把问题放回场景，排障就很容易出现两种极端：要么见到一个长 slice 就一路追下去，要么因为线索太多，最后什么也没追出来。场景化手册的作用，就是先把问题压缩到一个足够小的范围里。

## 先记住一个最重要的判断

现场排障最容易犯的错误，不是不会看 trace，而是**太早下钻**。

用户的一句“卡”，背后可能是：

- 掉帧
- 输入延迟
- 启动慢
- 前后台恢复慢
- 内存压力
- 接近 ANR

如果第一步就把它当成某一种问题，后面抓 trace、看线程、找责任链路都可能一路跑偏。  
所以排障要先做分类，再做下钻。

## 一个统一的四步框架

不管现场是什么问题，先按下面四步走：

1. **先定类**  
   这是掉帧、响应慢、ANR、内存压力，还是混合问题？

2. **再定窗口**  
   问题发生在点击后的 300ms、首帧前 3 秒，还是前后台切换的某个阶段？

3. **再定责任链**  
   MainThread、RenderThread、SurfaceFlinger、Binder、IO、调度，哪条路径最可疑？

4. **最后才下钻**  
   确定责任链后，再决定要不要继续上 SQL、heap dump、stack sampling 或 btrace。

这四步看起来普通，但它背后的约束非常强：每一步都在缩小问题空间。真正的经验，不在于一上来就知道哪段代码有问题，而在于知道应该先砍掉哪些不相关方向。

## 用户的“卡”，先翻译成技术问题

用户不会说“这像是 AppDeadlineMissed”，也不会说“这应该查 `ApplicationExitInfo`”。他只会说“卡”“慢”“像死掉了一样”。这时候工程师的第一职责，是把投诉翻译成可分析的问题。

| 用户说法 | 第一判断 | 第一观察点 |
|---|---|---|
| “滑动一卡一卡的” | 狭义流畅性 / jank | `FrameTimeline`、`doFrame`、`RenderThread` |
| “点了没反应” | 输入延迟 / 响应慢 | Input → MainThread → Binder / IO |
| “打开页面要等很久” | 启动或页面可交互时间过长 | TTID / TTFD、首屏数据链路 |
| “界面像死掉了一样” | ANR 或接近 ANR | 主线程栈、`ApplicationExitInfo`、`traces.txt` |
| “越用越卡，回前台更慢” | 内存压力 / 进程回收 / page fault | PSS、GC、LMKD、冷 / 温 / 热启动切换 |

这张表最有用的地方，不是它“覆盖得全”，而是它逼着读者先问一句：**我现在看到的，到底是哪一类体验失效？**

## 八类最常见的性能现场

### 1. 冷启动慢

冷启动慢最常见的误判，是把“已经看到画面”误当成“启动结束”。  
很多应用的 TTID 并不难看，真正拖慢体感的是 TTFD。

排这类问题时，先看四件事：

- TTID
- TTFD
- `reportFullyDrawn()`
- 首屏数据加载和骨架屏退出时机

实际落手顺序可以很简单：

1. 先分清这次是冷、温还是热启动，不要混在一起看。
2. 对照 TTID 和 TTFD，先分清“首帧慢”还是“可交互慢”。
3. 抓一次完整冷启动 trace。
4. 如果 TTID 正常但 TTFD 差，先查 Application 初始化、首屏数据和可交互边界。

这一类问题最容易掉进“感觉已经打开了，所以不算慢”的误区。对用户来说，画面出现只是第一步，能不能开始用才是第二步。  
对应章节：`8.1`、`8.2`、`8.3`、`15.6`。

### 2. 列表滑动卡顿

列表卡顿是最典型、也最容易被误判的一类问题。很多人第一反应是去看 `onBindViewHolder()`，这当然没错，但如果还没确认 jank 到底落在哪一层，这个动作还是太早。

先看：

- `FrameTimeline`
- Janky Frame Rate
- `RecyclerView` 的 bind / layout / prefetch 相关工作

再抓：

- 一段稳定滑动过程的 Perfetto
- 必要时补 FrameMetrics / JankStats 线上样本

再排：

- MainThread 的 `doFrame`
- RenderThread 的 `DrawFrame`
- 图片解码
- DiffUtil
- 布局层级

比较稳的顺序是：

1. 先确认是持续性掉帧，还是偶发长帧。
2. 先看 `FrameTimeline` 的 `Jank Type`，不要只看主线程颜色。
3. 再分流到 MainThread、RenderThread、SurfaceFlinger。
4. 最后才回到具体控件、图片、DiffUtil 和业务代码。

这里最常见的误判，是见到滑动卡，就默认问题一定在 UI 线程。实际工程里，图片线程抢 CPU、RenderThread 超时、SurfaceFlinger 合成变慢都很常见。  
对应章节：`7.3`、`7.4`、`7.5`、`18.2`、`18.7`。

### 3. 页面切换慢，或者切页动画不顺

页面切换问题经常有两种长相：

- 动画本身不顺
- 动画顺，但内容来晚了

这两类问题的责任链完全不同。前者更偏流畅性，后者更偏响应速度和数据就绪。

排这类问题时，先做一个粗判断：  
点击之后，页面是不是很快切过去了，只是内容空着？如果是，先别急着看动画。

比较稳的顺序是：

1. 先确定慢的是动画，还是内容。
2. 看点击事件后第一段空白时间花在哪里。
3. 如果页面很快出现但内容迟到，回到响应速度和数据加载路径。
4. 如果动画本身掉帧，再回到 MainThread / RenderThread / SurfaceFlinger。

很多“切页卡”最后都不是切页动画的问题，而是切页后数据、骨架屏、图片、路由初始化堆在一起，用户把它统称成“切页卡”。  
对应章节：`7.4`、`8.4`、`1.4`、`1.5`。

### 4. 输入延迟高，但不一定掉帧

这一类问题最容易被误判成普通慢帧。用户的感觉是“点了没反应”，但等一会儿画面还是动了。问题往往不在渲染本身，而在输入到反馈之间的等待。

先看：

- Input 事件到 `doFrame` 的时差
- 主线程是否长时间 Runnable
- 是否出现 BufferStuffing 或 high latency state

再排：

- InputReader / InputDispatcher
- MainThread 调度
- 锁等待
- Binder 等待

一个可靠的做法是：

1. 从触摸事件落点开始量输入到视觉反馈的窗口。
2. 看主线程是不是长时间 Runnable。
3. 看是否有 Binder reply wait 或锁等待。
4. 再判断是 App 自己堵住了，还是系统没给到 CPU。

这类问题的难点，不是证据少，而是太容易看错成渲染问题。  
对应章节：`3.1`、`3.2`、`7.1`、`15.2`。

### 5. 视频列表、SurfaceView、TextureView 场景卡

只要界面里出现独立 Surface，排障路径就要立刻切换。因为这时候 UI 帧和视频帧很可能已经不是同一条链路了。

先看：

- 独立 Surface 数量
- App UI 和视频渲染是否互相争抢
- HWC overlay 是否命中

再抓：

- App 进程
- SurfaceFlinger
- GPU / composition 相关轨道

再排：

- SurfaceView / TextureView 选型
- BufferQueue 堵塞
- 合成链路切换

实际顺序通常是：

1. 先确认是 UI 卡，还是视频画面卡。
2. 看独立 Surface、Layer 数量和合成路径。
3. 看 App 线程和 SurfaceFlinger 谁在超时。
4. 最后再回到容器选型和播放器实现。

这类问题最典型的误判，就是把所有掉帧都归到 UI 线程。  
对应章节：`18.4`、`18.6`、`18.7`、`18.15`。

### 6. WebView、Flutter、混合栈场景卡

这一类问题的难点在于：宿主和引擎经常不在同一条线程里。只看宿主主线程，结论经常不完整。

先看：

- 宿主线程和引擎线程谁在超时
- 是否存在双重合成

再抓：

- 带线程名的 Perfetto
- Chromium / Flutter 相关线程

再排：

- 平台视图混合
- 纹理采样与拷贝
- JavaScript / 页面资源加载
- 宿主侧布局

这里最重要的一条经验是：不要默认“宿主应用的主线程 = 唯一瓶颈”。  
对应章节：`2.11`、`7.11`、`18.12`、`18.13`。

### 7. 前后台切换后明显变慢

“回前台慢”最容易把人带到启动优化的路径里，但它经常是内存和进程生命周期问题。

先看：

- 这次是热启动、温启动还是已经变成冷启动
- 是否有 page fault、GC、LMKD 痕迹

再抓：

- 回前台前后 5-10 秒的 trace

再排：

- 进程是否被杀
- Activity 是否重建
- 内存回收
- 后台任务恢复

比较稳的顺序是：

1. 先分清这次到底是热启动、温启动还是冷启动。
2. 看进程有没有被系统杀掉。
3. 看回前台前后有没有 page fault、GC、LMKD、进程重建。
4. 再决定是启动问题还是内存问题。

真正麻烦的，不是它像启动慢，而是它“看起来很像启动慢”。  
对应章节：`4.4`、`8.1`、`10.4`、`15.2`。

### 8. 用户说“卡死了”

当用户用“卡死了”来描述问题时，第一反应不应该是“这一定是 ANR”，而应该是先确认系统有没有把它当成 ANR。

先看：

- 是不是 ANR
- 还是长时间无响应但尚未超时

再抓：

- `ApplicationExitInfo`
- `traces.txt`
- 必要时抓 ANR 前后的 Perfetto

再排：

- 主线程栈
- Binder reply wait
- 锁竞争
- 主线程 IO
- 系统高负载

顺序通常是：

1. 先确认是不是系统认定的 ANR。
2. 拉 `ApplicationExitInfo`、`traces.txt`、主线程堆栈。
3. 还原 ANR 前 5 秒窗口。
4. 再决定是 Binder、锁、IO、调度还是业务长任务。

这一类问题最容易犯的错，是只看 ANR 对话框弹出后的堆栈，不去看 ANR 前面的时间线。  
对应章节：`9.1`、`9.2`、`9.3`、`15.5`。

## 同一个现象，在不同设备上的第一怀疑点不同

同样是“卡”，在不同设备和场景里，第一怀疑点并不一样。

| 条件 | 先验怀疑 | 说明 |
|---|---|---|
| 低端机 / 小内存 | 调度、GC、page fault、图片解码 | 资源压力更容易放大 |
| 高刷设备 | deadline 更紧、尾部延迟更显眼 | 120Hz 下 8.33ms 很容易超 |
| 弱网 / 海外网络 | TTFD、页面切换、首屏骨架加载 | 先分离渲染问题和数据就绪问题 |
| 多窗口 / 浮窗 / PIP | SurfaceFlinger、BufferQueue、合成链路 | 不要只盯 App 主线程 |
| 游戏 / 视频场景 | GPU composition、独立 surface、thermal | UI 线程经常不是主瓶颈 |

这张表的意义，不是让读者背下来，而是提醒一件事：排障顺序应该跟着设备现实走，而不是死背模板。

## 抓 trace 时，先求回答问题，不求一次最全

很多团队抓 trace 的问题，不是“不会看”，而是“抓错了”。更稳的做法，是先保守一点：

- **滑动 / 动画卡顿**：抓 5-10 秒，保留 `gfx`、`view`、`sched`、`input`、`wm`
- **启动慢**：抓冷启动全过程，最好从拉起前开始
- **疑似 ANR**：抓问题前后更长窗口，必要时结合 `ApplicationExitInfo`
- **低概率线上问题**：先用指标缩小范围，再用异常触发补采 trace

抓 trace 的目标，不是一次开最全，而是先保证这份数据能回答当前最关键的因果关系。抓太大、抓太久，分析反而容易散。

## 先看哪条责任链

| 现象 | 第一责任链 |
|---|---|
| 帧超时 | MainThread → RenderThread → SurfaceFlinger |
| 点击后没反应 | Input → MainThread → Binder / Lock / IO |
| 页面内容迟迟不出现 | 启动链路 / 数据加载 / TTFD |
| 一切都慢 | 调度 / Thermal / 内存压力 / 系统负载 |
| 只有特定渲染容器慢 | BufferQueue / Surface / GPU composition |

这张表有一个重要前提：**同一个问题可以跨路径传导**。  
首屏慢，起点可能是启动任务过重，表现却是首帧晚；列表滑动卡，根因也可能不是布局，而是图片线程把 CPU 抢满了。

所以“第一责任链”不是最终结论，它只是排障的第一个锚点。

## 最容易出现的误判

- **把平均 FPS 当成全部真相**：平均值会掩盖尾部延迟。
- **把 SurfaceFlinger 责任误判成 App jank**：黄帧不天然等于 App 有问题。
- **把高输入延迟误判成普通掉帧**：BufferStuffing 场景尤其容易看错。
- **把系统高负载当成业务代码慢**：先看 Runnable，再看全局 CPU。
- **只看一段堆栈，不看时间线**：ANR 和流畅性问题都需要时序证据。
- **把首帧出现误当成页面完成**：TTID 正常不代表 TTFD 正常。
- **把“只有某些机型差”误当成偶现**：机型聚类往往说明这是结构性问题。
- **把“线下复现不了”误当成无问题**：线上会话上下文常常比本地单次操作更重要。

## 这份手册怎么用

它最适合三种场景：

1. 线上问题刚到手时，快速决定先抓什么。
2. 团队复盘时，把经验沉淀成固定排查路径。
3. 给新人做训练时，用真实投诉倒推章节和工具。

如果团队已经有值班和灰度治理机制，下一步就可以把这份手册继续拆成自己的 runbook：

- 哪类问题先由客户端同学看
- 哪类问题需要系统 / ROM 协作
- 哪类问题必须补抓 trace 才能继续
- 哪类问题可以直接回到指标平台做聚类

做到这一步，性能排障才真正从个人经验变成团队资产。
