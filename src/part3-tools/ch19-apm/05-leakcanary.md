---
title: "LeakCanary"
chapter: "19"
section: "19.05"
status: draft
drafted_date: "2026-04-24"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-24"
last_verified_against: "LeakCanary official docs"
confidence: medium
tags: [apm]
related_chapters: ["19.0"]
sources:
  - type: official
    path: "https://square.github.io/leakcanary/"
  - type: official
    path: "https://square.github.io/leakcanary/fundamentals-how-leakcanary-works/"
pipeline_stage: drafted
---

# LeakCanary

## LeakCanary 是本地泄漏诊断工具

LeakCanary 是 Square 开源的 Android 内存泄漏检测库。它最适合开发和测试阶段使用：当 Activity、Fragment、ViewModel 或业务对象在应该释放后仍然存活时，LeakCanary 会 dump heap、分析引用链，并把可疑引用标出来。

它不应该被放进“线上 APM 框架”同一格里比较。LeakCanary 的强项是把本地泄漏讲清楚，线上内存趋势、采样、平台聚合和 OOM 分析不是它的默认目标。

## 它怎样判断对象被保留

LeakCanary 的流程可以拆成四步：

1. 观察对象生命周期，比如 Activity `onDestroy()` 后进入观察队列。
2. 用弱引用判断对象在 GC 后是否仍然存活。
3. 对持续存活的对象触发 heap dump。
4. 用 Shark 分析 Hprof，生成从 GC Root 到泄漏对象的 leak trace。

这套流程的关键点是“应该释放的对象仍然被强引用持有”。LeakCanary 不是单纯看内存数值，也不是看到对象多就报警。它关心的是生命周期已经结束、但引用链仍然存在的对象。

## leak trace 比堆大小更有用

内存泄漏排查里，堆大小只能告诉你结果，引用链才能告诉你原因。LeakCanary 输出的 leak trace 会标出：

- GC Root 类型，比如 native local、thread、system class。
- 每一段强引用路径。
- 哪些引用最可疑。
- 泄漏对象的状态，例如 destroyed Activity。
- 是否命中已知 library leak 模式。

这类信息能直接指导修复。比如一个单例静态字段持有 `View`，trace 会把单例、集合、View、Activity 之间的引用关系展开；开发者不需要在 Hprof 里手动找半天。

## Application Leak 和 Library Leak 要分开看

LeakCanary 会把泄漏分成 Application Leak 和 Library Leak。前者是应用代码导致，通常应该修。后者来自系统或第三方库已知问题，应用侧未必能直接修复。

这层分类很实用。团队看泄漏列表时，不能把所有报告都按同一优先级处理。Application Leak 应进入代码修复；Library Leak 更适合做版本规避、反射补丁、依赖升级或忽略规则。

## Release 中使用要很克制

LeakCanary 官方文档提供了 at scale 和 release 相关能力，但这不等于普通项目应该直接在线上全量打开。heap dump 会带来明显开销，Hprof 也可能包含敏感对象和用户数据。

如果要在预发或小流量包里使用，建议先满足这些条件：

- 只在内部渠道或灰度诊断包启用。
- dump 前后做频率限制，避免短时间多次 dump。
- Hprof 不直接上传，只上传裁剪后的 leak trace 或签名。
- 明确数据保留周期和隐私审查范围。

生产环境内存治理更常见的搭配是：KOOM 或自研 SDK 负责线上趋势和样本，LeakCanary 负责本地复现和修复。

## 和 Perfetto、Profiler 的边界

Perfetto 可以看进程内存曲线、RSS/PSS、GC、heap profile 等信号；Android Studio Memory Profiler 可以交互式查看对象分配和引用。LeakCanary 的优势是自动化和针对性：它知道 Android Framework 的生命周期语义，也内置了很多系统泄漏模式。

拿到一个 OOM 或内存上涨问题时，可以这样分工：

- 线上平台确认问题版本、机型和页面分布。
- KOOM 或 heap dump 样本确认泄漏候选。
- LeakCanary 在本地复现路径上输出引用链。
- Profiler / MAT / Shark 辅助查看更大的对象图。

LeakCanary 的位置很稳：它是开发者修内存泄漏时最省时间的本地工具之一，但不是完整的线上内存 APM。

## 默认观察对象

LeakCanary 会自动覆盖 Android 常见生命周期对象，典型包括 Activity、Fragment、Fragment view、ViewModel 等。它也允许开发者通过 `ObjectWatcher` 观察业务对象。

业务对象观察适合这些场景：

- 复杂播放器、相机、地图、WebView 容器。
- 大型业务 controller / presenter / manager。
- 订阅消息总线、协程、RxJava、Callback 后应释放的对象。
- 持有 Bitmap、ByteArray、native handle 的对象。

示意代码如下，重点是只观察“生命周期已经结束”的对象：

```kotlin
class PlayerController {
    fun release() {
        stopPlayback()
        AppWatcher.objectWatcher.watch(
            watchedObject = this,
            description = "PlayerController should be released after playback page exits"
        )
    }
}
```

如果对象本来就应该常驻，加入 watch 只会制造噪声。LeakCanary 的前提永远是“这个对象此刻应该可回收”。

## leak trace 应该怎么读

LeakCanary 报告里的 leak trace 不是普通调用栈，它是从 GC Root 到泄漏对象的引用路径。读的时候按三步来：

1. 看末尾对象：确认被泄漏的是 Activity、View、Fragment view 还是业务对象。
2. 看红线引用：这些引用是 LeakCanary 判断最可疑的保留点。
3. 看 GC Root：判断根来自线程、静态字段、JNI、系统对象还是局部变量。

例如，一个简化后的泄漏可能长这样：

```text
GC Root: System class
|
| static AnalyticsDispatcher.callbacks
v
ArrayList
|
| elementData[2]
v
HomeFragment$callback
|
| this$0
v
HomeFragment
|
| mView
v
RecyclerView
```

这条链说明问题不在 `RecyclerView` 本身，而在 `AnalyticsDispatcher.callbacks` 里保存的 callback 没有移除。修复点应该回到订阅/反订阅，而不是清空页面里的所有 View 字段。

## 常见泄漏模式

| 模式 | 表现 | 修复方向 |
|---|---|---|
| 静态单例持有 Context / View | Activity 销毁后仍被 static 字段引用 | 存 application context，避免持有 View |
| Handler / Runnable 延迟任务 | MessageQueue 中的任务持有页面对象 | 页面销毁时 remove callbacks |
| 监听器未注销 | 全局 dispatcher、网络回调、传感器监听持有页面 | 成对注册和注销 |
| 协程 / Rx 订阅未取消 | 后台任务完成前页面已销毁 | 绑定 lifecycle scope 或 dispose |
| Fragment view 泄漏 | `onDestroyView()` 后 adapter / binding 仍持有 View | 清空 binding、adapter、listener |
| WebView / Map / Player 容器 | native 资源或内部线程持有 Activity | 独立生命周期封装，销毁顺序明确 |

LeakCanary 的优势是直接告诉你引用路径。修复时不要只“把字段置空”，要理解谁负责释放这条引用。

## Library Leak 的处理方式

Library Leak 不是“可以忽略”的同义词。它表示泄漏来自系统或第三方库的已知模式，应用不一定能直接修，但仍要评估影响：

- 如果只在老系统小比例出现，可以标记已知风险。
- 如果影响主流程或大内存页面，要考虑规避代码路径。
- 如果来自第三方 SDK，要推动升级或降级验证。
- 如果能用生命周期顺序规避，可以在业务容器里做封装。

不要把 Library Leak 批量关掉。关掉后，后续同类系统问题和业务问题混在一起时，团队会失去早期信号。

## 和线上内存样本联动

LeakCanary 更适合本地修复，但它可以和线上样本组成一条修复路径：

1. KOOM 或线上 APM 发现某页面 OOM / heap 抬升。
2. 根据页面和操作路径在 Debug 包复现。
3. LeakCanary 输出引用链。
4. 修复后用 LeakCanary 确认对象释放。
5. 灰度后看线上 OOM、PSS、heap 使用率是否下降。

这个流程比“线上拿到 OOM 后盲改缓存大小”可靠。内存问题经常同时有泄漏和缓存策略两类原因，LeakCanary 负责确认泄漏部分。

## 测试集成建议

LeakCanary 可以进入 UI 测试流程。对关键页面写自动化用例，执行进入、操作、退出，再检查 retained object 是否超过阈值。这样能防止常见生命周期泄漏回归。

测试时要给异步任务留出完成时间，也要避免在刚退出页面后立即断言。更稳的做法是等待主线程空闲、触发 GC、多轮检查后再判断。泄漏测试比普通 UI 测试慢，但对核心页面很值得。
