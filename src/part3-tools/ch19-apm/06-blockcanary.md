---
title: "BlockCanary"
chapter: "19"
section: "19.06"
status: draft
drafted_date: "2026-04-24"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-24"
last_verified_against: "markzhai/AndroidPerformanceMonitor GitHub README"
confidence: medium
tags: [apm]
related_chapters: ["19.0"]
sources:
  - type: blog
    path: "https://github.com/markzhai/AndroidPerformanceMonitor"
pipeline_stage: drafted
---

# BlockCanary

## BlockCanary 更适合当原理样本

BlockCanary 是早期开源的 Android 主线程卡顿检测库，仓库名是 `AndroidPerformanceMonitor`。它的设计目标很单一：当主线程一次消息执行时间超过阈值时，抓取堆栈并生成报告。

放到 2026 年看，它不适合作为新项目线上监控首选。它更适合用来理解一类经典卡顿监控方案：基于 Looper 消息边界判断主线程阻塞，再用定时抓栈保留现场。

## 它抓的是一次 Looper 消息

Android 主线程大部分工作都通过 `Looper.loop()` 分发 `Message`。BlockCanary 利用 `Looper.setMessageLogging()` 设置 `Printer`，在每个 Message 开始和结束时记录时间。如果开始到结束超过阈值，就认为这次消息执行期间发生了 block。

这条路径的好处是接入轻、侵入小，不需要修改业务代码，也不需要系统权限。缺点也同样清楚：

- 它只能看到 Message 粒度，无法自然区分 Input、Animation、Traversal、RenderThread 等阶段。
- 采样线程抓到的是某几个时刻的主线程堆栈，不一定覆盖最慢的那一行代码。
- 如果主线程被调度饿死，堆栈可能停在一个并不耗时的函数上。

所以 BlockCanary 报告适合当“卡顿方向提示”，不能直接当最终结论。

## 配置项决定误报率

BlockCanary 常见配置包括 block 阈值、dump 间隔、日志保存路径、设备信息、包名过滤等。阈值设置会直接影响报告质量。

| 配置方向 | 过低的结果 | 过高的结果 |
|---|---|---|
| block 阈值 | 报告过多，正常轻微抖动也被记录 | 只剩严重卡顿，很多慢交互被漏掉 |
| dump 间隔 | 抓栈太频繁，监控本身增加负担 | 堆栈太稀疏，错过关键调用 |
| 保存数量 | 占用磁盘，清理成本上升 | 样本不足，问题复现后找不到日志 |

线上系统通常还要加采样率、白名单、页面状态和远程开关。早期 BlockCanary 示例更偏本地或小范围调试，新项目不能照搬默认值。

## 和 JankStats、FrameMetrics 的差别

JankStats 和 FrameMetrics 关心帧。BlockCanary 关心主线程 Message。

这两个口径不会完全一致。一个 Message 可能跨多帧，导致连续慢帧；也可能某个 Message 很长，但窗口不在动画或用户交互期间，用户感知没那么明显。反过来，一次掉帧也可能来自 RenderThread、GPU、SurfaceFlinger 或调度问题，BlockCanary 只看主线程就会漏掉。

工程上更稳的搭配是：

- 用 JankStats / FrameMetrics 统计用户可感知的慢帧。
- 用 Looper block 监控捕获主线程长消息。
- 用 Perfetto 还原线程调度和渲染管线。

## 使用建议

如果维护老项目里已有 BlockCanary，可以保留它作为低成本主线程 block 信号，但要减少它的决策权。报告进入分析平台前，至少补上页面、前后台、线程状态、采样时间、版本和机型。

如果是新项目，更建议直接用 JankStats、FrameMetrics、Matrix Trace Canary 或自研轻量 Looper 监控。BlockCanary 的代码和思想仍有学习价值，但它的维护状态和现代 Android 渲染口径已经不适合作为唯一方案。

## Looper 监听的基本原理

BlockCanary 的核心是 `Looper.setMessageLogging()`。主线程每次开始和结束处理 `Message` 时，Looper 会向 `Printer` 打印一行日志。BlockCanary 利用这两个边界计算一次 Message 的执行时间。

简化后的逻辑如下：

```java
Looper.getMainLooper().setMessageLogging(new Printer() {
    private long startTimeMillis;

    @Override
    public void println(String x) {
        if (x.startsWith(">>>>> Dispatching")) {
            startTimeMillis = SystemClock.uptimeMillis();
            stackSampler.start();
        } else if (x.startsWith("<<<<< Finished")) {
            long cost = SystemClock.uptimeMillis() - startTimeMillis;
            stackSampler.stop();
            if (cost > blockThresholdMillis) {
                reportBlock(cost, stackSampler.getSamples());
            }
        }
    }
});
```

这段代码说明了 BlockCanary 的本质：它不直接知道某一帧是否掉帧，也不直接知道渲染阶段。它只知道“主线程某次消息从开始到结束花了多久”。

## 抓栈线程和主线程的关系

BlockCanary 通常会启动一个后台采样线程，在主线程 Message 执行期间按固定间隔抓主线程堆栈。这个设计有两个后果：

- 如果主线程正在执行 Java/Kotlin 代码，采样堆栈有机会抓到业务函数。
- 如果主线程卡在 native、Binder、I/O、锁等待或调度等待，堆栈只能显示等待点，不能直接显示根因。

例如一次 1200ms block，采样线程每 300ms 抓一次，最多只拿到 4 个堆栈。若最慢的函数只运行 80ms，采样可能完全错过它。BlockCanary 的报告要按概率证据看，不能按精确 trace 看。

## 典型报告应该怎样聚合

BlockCanary 原始日志适合本地看，线上平台要做归一化。建议字段如下：

| 字段 | 说明 |
|---|---|
| `message_cost_ms` | 本次 Message 总耗时 |
| `block_threshold_ms` | 当前阈值，便于不同版本比较 |
| `top_stack_signature` | 采样堆栈归一化签名 |
| `sample_count` | 本次 block 抓到多少个堆栈 |
| `page` | block 发生时的页面或路由 |
| `input_active` | 是否处于触摸、滑动、动画等交互期间 |
| `foreground` | 前台/后台状态 |
| `cpu_state` | 可选，结合本地 CPU 采样判断系统忙闲 |

只按堆栈聚合会丢页面信息。只按页面聚合又无法分配给代码负责人。两者都要有。

## 和慢帧指标的错位

一次 80ms Message 在 60Hz 下可能造成 4-5 帧延迟，但如果它发生在页面静止、没有动画的时间窗口，用户未必感知明显。一次 25ms Message 低于很多 block 阈值，但在滚动过程中已经可能造成慢帧。

所以 Looper block 监控和帧监控要分开建指标：

- Looper block 适合抓主线程长任务。
- JankStats / FrameMetrics 适合抓用户可感知慢帧。
- Perfetto 适合把二者放到同一时间轴上校验。

不要用 BlockCanary 的 block 次数直接替代慢帧率。它们的分母、窗口和感知口径都不同。

## 自研轻量卡顿监控时的改进点

如果团队要基于 BlockCanary 思路自研，建议补这些能力：

1. 用 `Choreographer` 或 JankStats 记录交互期间慢帧。
2. Looper block 只作为主线程长任务样本。
3. 抓栈采样线程要有最大时长和频率限制。
4. 上报前对堆栈做签名，避免原始堆栈爆量。
5. 采样只在前台和目标页面开启。
6. 与 ANR、启动、页面切换等事件共享 trace id 或 session id。

BlockCanary 的价值在于简单。现代线上体系要在简单之上补上下文和采样控制。
