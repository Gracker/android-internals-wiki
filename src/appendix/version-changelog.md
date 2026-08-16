# 附录 A：Android 版本性能变更速查表

> 核对日期：2026-08-16。覆盖 Android 10—17 的稳定版；开发者预览版和未正式发布的 QPR（季度平台版本）不计入稳定结论。

本页只收录会改变性能表现、诊断数据或测试边界的版本变化。相机格式、隐私权限和界面功能若没有直接影响性能排查，就不纳入这张速查表。

## 读表前先确认四个门槛

- **系统版本**：设备运行的 Android 版本决定平台实现和可用 API。
- **目标版本**：部分行为只对 `targetSdkVersion` 达到该版本的应用生效。看到“Android 17 新增”时，仍要检查它影响所有应用，还是只影响目标 API 37 的应用。
- **设备能力**：内核、SoC（片上系统）、显示面板和厂商配置会决定某项能力是否启用。AOSP（Android Open Source Project）支持某项能力，不代表每台同版本设备都已启用。
- **模块版本**：ART（`Android Runtime`）等 Mainline 模块可通过 Google Play 系统更新独立升级；Mainline 指可脱离整机 OTA 更新的系统组件。同一系统版本的两台设备，运行时实现可能不同。

“引入”“默认启用”“强制执行”也要分开理解。比如 Android 15 引入 16 KB 内存页支持，Android 16 增加 4 KB 应用兼容模式；兼容模式能帮助旧应用运行，却不能替代原生 16 KB 对齐。

## Android 17（API 37，稳定版）

Android 17 已发布稳定版。Beta 3 的 Platform Stability 只表示测试期 API 已锁定，不能代替稳定版发布状态；版本总览与状态以 [Android 17 官方页面](https://developer.android.com/about/versions/17) 和 [稳定版发布说明](https://developer.android.com/blog/posts/android-17-is-here) 为准。

| 变化 | 含义 | 生效与验证边界 |
|------|------|----------------|
| 无锁 `MessageQueue` | `MessageQueue` 是 `Looper` 用来保存和投递定时消息的队列。新实现减少多线程高负载队列中的锁竞争。 | 只对目标 API 37 及以上的应用启用；依赖私有字段或反射的测试代码可能失效。对比启动、帧超时和消息投递延迟，不要只比较单次总耗时。参见 [Android 17 功能列表](https://developer.android.com/about/versions/17/summary) 与 [1.13 MessageQueue](../part1-fundamentals/ch01-architecture/13-messagequeue-deliqueue.md)。 |
| ART 分代 GC | GC（垃圾回收）把短生命周期对象优先放入年轻代，以较轻量的年轻代回收减少全堆扫描。`Concurrent Mark-Compact` 是 ART 的并发标记-整理收集器，Android 17 为它加入分代能力。 | ART 改进也可能通过 Mainline 更新到 Android 12 及以上设备。测试时记录 ART 模块、GC 暂停、CPU 时间和 RSS（进程实际驻留的物理内存），参见 [4.7 ART 分代 GC](../part1-fundamentals/ch04-memory/07-art-generational-gc.md)。 |
| `MemoryLimiter` | 这是使用 cgroup v2（Linux 进程资源统计与限制接口）约束应用进程内存的系统服务，目标是限制极端内存占用对整机的影响。 | 行为变化影响支持该能力的设备上的所有应用，但官方明确说明只在部分设备执行。先用 `am memory-limiter status` 确认，再查 `ApplicationExitInfo`；不要假定统一的固定阈值。参见 [官方行为变更](https://developer.android.com/about/versions/17/behavior-changes-all)、[AOSP 机制说明](https://source.android.com/docs/core/perf/memory-limiter) 与 [4.13 MemoryLimiter](../part1-fundamentals/ch04-memory/13-android17-memorylimiter.md)。 |
| `ProfilingManager` 新触发器 | `ProfilingManager` 用于让应用接收系统采集的性能资料。Android 17 增加冷启动、OOM（Out of Memory，内存耗尽）、异常 CPU 使用和系统异常触发器。 | 触发式采集受注册、配额、设备实现和事件是否发生影响，不能当作每次会话都会生成的日志。参见 [Android 17 性能 API](https://developer.android.com/about/versions/17/features) 与 [14.11 ProfilingManager](../part3-tools/ch14-other-tools/11-profiling-manager.md)。 |
| 精确空闲闹钟回调重载 | `AlarmManager.setExactAndAllowWhileIdle` 新增接收 `OnAlarmListener` 的重载，用于减少回调场景中的长时间部分唤醒锁。 | 这项 API 不会放宽精确闹钟权限或 Doze（设备空闲省电模式）限制。只比较使用新旧调用方式的唤醒锁时长和回调延迟，参见 [Android 17 发布记录](https://developer.android.com/about/versions/17/release-notes)。 |

目标 API 37 的应用还不能再通过反射或 JNI（Java 与 native 代码的互操作接口）修改 `static final` 字段。该变化允许 ART 作出更强的常量假设，也可能暴露测试框架、序列化库或热修复代码对私有实现的依赖；升级时应单独做兼容性测试。

表中五项分别受目标版本、Mainline 模块、设备支持和采集条件控制，不能合并成“升级 Android 17 后统一提升多少”。同一应用也应分别测启动、帧时间、GC、RSS、CPU 和功耗。

## Android 10—16 时间线

下表按能力首次进入稳定平台的版本归档。后续 Mainline 更新或厂商回移不会改变首发版本，但会改变具体设备上能观察到的实现。

| 版本 | 已确认的性能相关变化 | 排查与迁移边界 |
|------|----------------------|----------------|
| Android 16（API 36） | `ProfilingManager` 增加系统触发式采集；ADPF（Android Dynamic Performance Framework，动态性能框架）增加 CPU/GPU headroom API，headroom 表示当前工作负载距离资源上限还有多少余量；自适应刷新率增加能力查询和建议帧率 API；16 KB 设备增加 4 KB 应用兼容模式。 | 自适应刷新率和 headroom 都依赖硬件支持。4 KB 兼容模式只提供过渡性的运行支持，native 库仍应按 16 KB 对齐。参见 [Android 16 功能说明](https://developer.android.com/about/versions/16/features)、[16 KB 兼容模式](https://developer.android.com/about/versions/16/behavior-changes-all)、[2.18 自适应刷新率](../part1-fundamentals/ch02-rendering/18-adaptive-refresh-rate.md)、[4.6 16 KB Page Size](../part1-fundamentals/ch04-memory/06-16kb-page-size.md) 与 [5.9 ADPF](../part1-fundamentals/ch05-cpu-power/09-adpf.md)。 |
| Android 15（API 35） | AOSP 开始支持 16 KB 内存页；ARR（Adaptive Refresh Rate，自适应刷新率）开始支持按内容帧率使用离散 VSync（显示同步节拍）步进；新增应用主动请求采集的 `ProfilingManager` 和记录进程启动原因、类型及阶段时间的 `ApplicationStartInfo`。 | 16 KB 页是系统内存映射粒度，不能等同于 Java 堆块大小；含 NDK（Native Development Kit）库的应用要检查 ELF（native 二进制文件格式）段对齐。ARR 依赖面板与设备实现。参见 [Android 15 功能列表](https://developer.android.com/about/versions/15/summary)、[16 KB 官方迁移指南](https://developer.android.com/guide/practices/page-sizes) 与 [26.11 ApplicationStartInfo](../part5-app/ch26-observability/11-application-start-info.md)。 |
| Android 14（API 34） | 系统更一致地限制缓存态进程继续执行后台工作，并可将动态注册的广播排队到进程离开缓存态后再投递；缓存进程冻结的行为也更完整。 | 缓存态表示进程当前没有用户可感知的活动组件，代码不能依赖它继续运行。后台工作应交给受支持的生命周期或调度 API。参见 [Android 14 行为变更](https://developer.android.com/about/versions/14/behavior-changes-all)、[AOSP Cached App Freezer](https://source.android.com/docs/core/perf/cached-apps-freezer) 与 [4.11 缓存进程冻结边界](../part1-fundamentals/ch04-memory/11-cached-app-freezer-gc-boundary.md)。 |
| Android 13（API 33） | ART 优化降低部分 JNI 切换和引用处理开销；`Choreographer` 与 `ASurfaceControl` 增加候选呈现时间和帧截止时间信息。 | ART 可能经 Mainline 更新出现在 Android 12 及以上设备。帧 API 提供候选时间，显示是否按期完成仍要结合 Perfetto 的 Expected/Actual Timeline。参见 [Android 13 功能说明](https://developer.android.com/about/versions/13/features) 与 [13.19 FrameTimeline](../part3-tools/ch13-perfetto/19-frame-timeline-api33-perfetto-analysis.md)。 |
| Android 12（API 31） | Perfetto 可提供 FrameTimeline 数据，用 Expected Timeline 与 Actual Timeline 区分预期帧和实际帧；目标 API 31 的应用受到更严格的后台前台服务启动和精确闹钟限制；AOSP 构建系统开始支持 AutoFDO。 | AutoFDO 使用采样得到的执行剖面帮助编译器优化原生系统模块，效果取决于剖面能否代表目标工作负载。百分比只能用于同设备、同构建和同场景的对照实验。参见 [Android 12 行为变更](https://developer.android.com/about/versions/12/behavior-changes-12)、[FrameTimeline 诊断说明](https://developer.android.com/topic/performance/jankstats)、[AOSP AutoFDO](https://source.android.com/docs/core/perf/autofdo) 与 [1.12 AutoFDO](../part1-fundamentals/ch01-architecture/12-autofdo-optimization.md)。 |
| Android 11（API 30） | 系统支持 Cached App Freezer：把缓存进程移入冻结 cgroup，使其保留在内存中但不获得 CPU 时间；目标 API 30 后 `Scoped Storage`（分区存储）强制执行，Android 共享存储也转向 FUSE 路径。 | Freezer 没有公开应用 API，并受设备配置影响。FUSE（用户空间文件系统）会改变共享存储 I/O 路径，延迟取决于内核、MediaProvider 和访问方式。参见 [AOSP Cached App Freezer](https://source.android.com/docs/core/perf/cached-apps-freezer)、[Android 11 存储变更](https://developer.android.com/about/versions/11/privacy/storage) 与 [6.5 FUSE I/O 路径](../part1-fundamentals/ch06-storage/05-vold-mediaprovider-fuse.md)。 |
| Android 10（API 29） | 设备端系统追踪开始保存为 Perfetto 格式，并支持按时长或文件大小采集长 Trace；ART 的 GC 触发计算开始计入与 Java 对象关联的大型 native 分配。 | Perfetto 是系统追踪与分析平台，不保证每台设备暴露相同数据源。比较旧设备时先核对 TraceConfig（声明数据源、缓冲区和采集时长的配置）、构建类型和权限，参见 [Android 10 功能说明](https://developer.android.com/about/versions/10/features) 与 [13.1 Perfetto 简介](../part3-tools/ch13-perfetto/01-perfetto-intro.md)。 |

这条时间线记录“该版本新增或改变了什么”，不代表后续版本仍保持完全相同的实现。ART、MediaProvider 等可更新模块尤其需要同时记录模块版本。

## 使用速查表做对照测试

每次对比至少记录设备型号、构建指纹、Android/API 版本、`targetSdkVersion`、关键 Mainline 模块版本和是否启用相关设备能力。只有这些条件一致，版本前后的数据才有可比性。

性能数字还要附上场景、样本量、冷/热状态、温度与功耗条件，以及统计口径。缺少共同硬件、构建基线与工作负载的百分比，只能视为特定实验结果，不能外推成平台级结论。

遇到“版本符合但功能没出现”时，按目标版本门槛、设备能力、模块版本、采集权限的顺序检查。遇到“升级后变快或变慢”时，先拆成启动、帧时间、CPU、GC、RSS、I/O 和功耗指标，再用对应工具复现。
