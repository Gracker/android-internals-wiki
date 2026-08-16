# 附录 E：术语表（中英对照）

中文列帮助快速理解，英文或原名列保留源码、日志、API 和 Perfetto UI 中可检索的写法。工具名、进程名、类名和字段名不强行翻译；首次出现时解释职责，后续继续使用原名。

同一个词在不同工具中可能有不同统计口径。记录 FPS、启动时间或内存数值时，还要写明数据来源、时间窗口、设备状态和 Android 版本。

## 启动与响应

| 中文 | 英文或原名 | 说明 |
|------|------------|------|
| 响应速度 | Responsiveness | 从输入、系统事件或业务请求发生，到用户看到结果或任务完成的延迟。它会受到排队、线程调度、I/O（磁盘、网络等输入/输出）、Binder 跨进程调用和渲染的共同影响，不能只用帧率判断。 |
| 应用无响应 | ANR（Application Not Responding） | Android 判定应用没有在规定时间内处理输入、广播、Service 组件等工作。主线程长时间阻塞是常见原因，短暂卡顿不一定形成 ANR。 |
| 冷启动 | Cold Start / Cold Launch | 启动前应用进程不存在，系统需要创建进程、应用级 `Application` 对象、`Activity` 页面和首帧所需对象，工作量通常最多。 |
| 温启动 | Warm Start | 介于冷启动和热启动之间的一组情况。常见情况是进程仍在但 Activity 需要重建，也可能利用已保存状态减少部分初始化；分析工具采用的分类口径应随结果记录。 |
| 热启动 | Hot Start | 进程、Activity 和大部分界面对象仍在内存中，系统把现有 Activity 带到前台。被内存整理清除的对象仍可能需要重建。 |
| 首次显示耗时 | TTID（Time to Initial Display） | 从系统收到启动请求到应用首帧显示的时间。首帧出现只表示用户已经看到画面，不表示数据已经加载完或页面已经可操作。 |
| 完全显示耗时 | TTFD（Time to Full Display） | 从启动请求到应用认为关键内容可用并调用 `reportFullyDrawn()` 的时间。该指标依赖应用选择的上报时机，跨版本或跨应用比较前要核对口径。 |
| 关键用户操作场景 | CUJ（Critical User Journey） | 可重复执行和测量的一段用户操作，例如启动、滚动列表或打开详情页。CUJ 是测试单元，不要求覆盖一次完整会话。 |

启动类型描述起点条件，TTID 和 TTFD 描述两个完成时刻，ANR 描述系统判定的无响应结果。排查启动慢时，应同时记录启动类型和测量终点。

## 帧与显示

| 中文 | 英文或原名 | 说明 |
|------|------------|------|
| 卡顿 | Jank / Stutter | 画面没有按预期节奏连续呈现，用户看到停顿或跳动。晚帧、掉帧和帧间隔波动都可能造成卡顿，具体标签由平台帧时间线 `FrameTimeline` 或应用侧卡顿统计库 `JankStats` 按各自规则给出。 |
| 流畅性 | Smoothness | 一段交互中画面节奏和输入反馈的稳定程度。平均 FPS 相同的两次运行，仍可能因少量特别慢的帧和帧间隔不均而有不同观感。 |
| 帧率 | Frame Rate（FPS） | 每秒生成、提交或呈现的帧数；具体含义取决于采样位置。应用生成 FPS、图形缓冲区提交 FPS 和屏幕呈现 FPS 不能直接混用。 |
| 刷新率 | Refresh Rate（Hz） | 显示设备每秒扫描或更新画面的次数。刷新率提供呈现机会，应用帧率可能低于它，系统也可能重复显示旧画面。 |
| 垂直同步 | VSync | 显示系统提供的同步时序，Android 用它协调应用产帧、图层合成和屏幕呈现。收到 VSync 不保证应用线程会立即获得 CPU。 |
| 帧截止时间 | Frame Deadline | 一帧为赶上目标呈现时刻而需要完成的时间点。它随刷新模式和系统调度变化，不能把所有设备都固定为 16.67 ms。 |
| 掉帧 | Dropped Frame / Frame Drop | 目标呈现时刻没有按计划显示对应新帧，系统可能继续显示旧缓冲区、延后呈现或采用更新的帧。单个函数超过一帧时长不足以独立证明掉帧。 |
| 渲染管线 / 渲染流水线 | Rendering Pipeline | 从应用处理输入、构建界面和提交绘制工作，到 GPU（图形处理器）执行、缓冲区传递、系统合成服务 SurfaceFlinger 合成并交给显示硬件的整套过程。不同 UI 或图形 API 会绕过其中某些阶段。 |
| 帧调度器 | `Choreographer` | 按显示时序在带 Looper 消息循环的线程上安排输入、动画以及 View 测量、布局和绘制准备等回调。`Choreographer#doFrame` 是常见帧入口，但它不执行全部 GPU 和系统合成工作。 |
| 渲染线程 | `RenderThread` | Android 硬件加速 UI 渲染系统 HWUI 的原生线程，处理应用记录的渲染节点和绘制命令，并准备或提交图形工作。界面线程仍负责输入、布局和部分绘制记录。 |
| 绘制目标 | `Surface` | 图像生产者写入图形缓冲区的接口，通常对应图形缓冲队列 BufferQueue 的生产者端。Surface 本身只提供写入接口，不代表一张固定图片，也不与单个 View 一一对应。 |
| 图形缓冲队列 | `BufferQueue` | 连接图像生产者与消费者并管理缓冲区循环复用的组件。生产者取得并提交缓冲区，消费者获取并释放缓冲区；可用缓冲区不足时，生产者可能等待。 |
| 图层 | `Layer` | SurfaceFlinger 管理和合成的显示单元，可携带缓冲区、位置、裁剪、透明度等信息。它属于系统显示模型，不等同于 View 层级中的节点。 |
| 系统显示合成服务 | `SurfaceFlinger` | 接收可见 Surface 的缓冲区与事务，组织图层，并协调 GPU、HWC 和显示设备完成合成与呈现。 |
| 硬件合成器 | HWC（Hardware Composer） | 显示子系统的 HAL（Hardware Abstraction Layer，硬件抽象层）接口。它根据设备能力选择由显示硬件直接合成哪些图层，剩余图层可先由 GPU 合成到一个缓冲区，这一步称为客户端合成。 |
| 合成 | Composition | 把多个图层组织成屏幕画面的过程。SurfaceFlinger 负责协调，工作可以由 GPU 或显示硬件完成。 |
| 过度绘制 | Overdraw | 应用在同一帧内多次绘制同一像素，较早绘制的内容随后被遮住。它描述应用绘制中的重复工作，不等同于 SurfaceFlinger 处理多个重叠图层。 |
| 帧时间线 | `FrameTimeline` | Android 12 / API 31 起提供的逐帧期望时间与实际时间数据，并带有平台判定的卡顿信息。它能定位异常帧，但不能单独给出业务代码中的原因。 |
| 图形同步栅栏 | `fence` | 表示异步 GPU、合成或显示工作何时完成的同步对象。缓冲区可跨组件传递，fence 用来阻止接收方过早读写该缓冲区；它与 Java 锁的用途不同。 |

帧率描述产出数量，刷新率描述显示节奏，帧截止时间和 FrameTimeline 描述单帧是否按时。遇到卡顿时，应沿应用线程、RenderThread、GPU、BufferQueue、SurfaceFlinger 和 HWC 的时间关系定位等待位置。

## 进程与内存

| 中文 | 英文或原名 | 说明 |
|------|------------|------|
| 进程间通信 | IPC（Inter-Process Communication） | 不同进程交换请求、数据和结果的统称。Binder 是 Android 主要的 IPC 机制之一。 |
| Binder 调用 | Binder IPC | 由内核 Binder 驱动、用户态库和服务端线程共同完成的跨进程调用。调用语法可能像本地方法，但仍有序列化、排队、调度、权限检查和远端失败成本。 |
| 进程重要性（常被写成进程优先级） | `Process State` / `adj` | 系统进程管理服务 `ActivityManagerService` 根据可见组件、前台服务、进程依赖等信息评估进程保留价值，并形成内部 `adj` 档位。它影响内存回收顺序，不等同于线程的 CPU 调度优先级。 |
| 内存回收候选分数 | `oom_score_adj` | Linux 内核暴露的进程分值，Android 会把进程重要性映射到该值。取值通常为 -1000 到 1000，数值越高，内存紧张时越倾向于成为终止候选；该值不控制 CPU 优先级。`oom_adj` 常作为历史简称或出现在旧配置说明中，检查 `/proc` 时应使用实际字段名 `oom_score_adj`。 |
| 内存压力 | Memory Pressure | 可及时分配或回收的内存不足，任务开始等待回收、换页或终止进程。仅看到“空闲内存少”还不能确认存在压力，因为 Android 会主动利用空闲 RAM（随机存取存储器）保存文件页和后台进程。 |
| 低内存终止守护进程 | `lmkd`（Low Memory Killer Daemon） | 运行在用户空间的守护进程，监测 PSI（Pressure Stall Information，任务因资源压力而停顿的内核统计）等内存信号，并结合 `oom_score_adj` 选择可终止进程。LMK（low-memory kill，低内存终止）常指一次终止结果；旧内核中的 LMK 驱动是历史实现。 |
| 终止进程（俗称杀进程） | Process Kill | 进程被系统、用户、应用或工具结束的结果。低内存终止只是其中一种原因，崩溃、ANR、强行停止和系统策略也会结束进程。 |
| 虚拟内存集 | VSS（Virtual Set Size） | 进程映射或保留的虚拟地址空间总量，包含尚未驻留 RAM 的区域。VSS 很大不代表占用了同等物理内存。 |
| 驻留内存集 | RSS（Resident Set Size） | 当前驻留在物理内存中的内存页总量；内存页是操作系统管理 RAM 的基本单位。共享页会在每个相关进程的 RSS 中完整计数，因此 RSS 适合观察单进程变化，不适合直接相加得到整机占用。 |
| 按比例分摊内存 | PSS（Proportional Set Size） | 私有驻留页加上按共享进程数分摊的共享页。比较多个进程的物理内存占用时，PSS 可减少共享页重复计数。 |
| 独占驻留内存 | USS（Unique Set Size） | 只由该进程使用的驻留页，不包含共享页。它可近似描述进程退出后可能释放的私有页，但不覆盖内核对象等全部系统成本。 |
| 垃圾回收 | GC（Garbage Collection） | ART（`Android Runtime`，Android 运行时）识别并回收无法再访问的托管对象。一次 GC 不保证 Java Heap（Java 堆）立刻缩小，也不会自动释放仍被引用的对象或所有 C/C++ 原生内存分配。 |

内存数字回答的问题不同：VSS 看地址空间，RSS 看驻留页，PSS 适合跨进程归属，USS 看私有驻留页。分析进程退出时，还要区分正常结束、崩溃、ANR、用户操作和 `lmkd` 低内存终止。

## CPU、温度与耗电

| 中文 | 英文或原名 | 说明 |
|------|------------|------|
| 大小核 | Arm big.LITTLE / DynamIQ | 对不同性能与能效 CPU 核心的口语称呼。“大”“小”描述相对处理能力和能效，与物理尺寸无关。big.LITTLE 是异构多核方案；DynamIQ 是可在集成集群中组合不同核心类型的较新架构，二者不能当作同一名称。 |
| CPU 集群 | CPU Cluster | 共享部分缓存、时钟或电源控制的一组 CPU 核心。集群边界取决于系统级芯片（SoC）的设计，不能只按当前频率猜测。 |
| 动态电压频率调整 | DVFS（Dynamic Voltage and Frequency Scaling） | 系统随负载、能效目标和限制条件改变处理器电压与频率。降频可能是普通负载决策，不一定由过热触发。 |
| 过热限频 | Thermal Throttling | 温度达到控制阈值后，系统限制 CPU、GPU 或其他硬件的可用性能以控制温度。确认它需要温度、冷却设备或频率上限等证据。 |
| 功耗、功率与耗电量 | Power / Energy / Power Consumption | “功耗”在口语中可能指功率，也可能指累计耗电量。功率表示某一时刻消耗能量的速率，常用 W（瓦）；耗电量是功率随时间累积的结果，常用 J（焦耳）、Wh（瓦时）或 mAh（毫安时）。mAh 表示电荷量，跨电压比较时不能直接当作能量。 |
| 唤醒锁 | WakeLock | 应用请求设备暂时保持特定工作状态的机制。常见的 `PARTIAL_WAKE_LOCK` 可在屏幕关闭后让 CPU 保持运行；持有时间过长会增加耗电，使用后应及时释放。 |
| 链式唤醒 | Chained Wakeup | 一个事件唤醒进程或组件后，又触发其他服务、网络请求或定时任务的现象。它描述一串因果事件，Android 没有名为 Chained Wakeup 的正式 API。 |

低频可能来自 DVFS 的正常选择、过热限制、省电策略或厂商调度，单条频率曲线无法区分原因。耗电分析还要同时记录持续时间、屏幕、网络、温度、WakeLock 和设备电源状态。

## 跟踪采集与分析

| 中文 | 英文或原名 | 说明 |
|------|------------|------|
| 性能跟踪数据 | `trace` | 按时间记录线程、调度、频率、内存、应用标记等事件的数据。它不特指方法调用记录或崩溃堆栈，采到了哪些数据由配置和权限决定。 |
| 系统跟踪工具集 | Perfetto | 用于采集、存储、可视化和查询 trace 的开源工具集，包括设备端服务、Perfetto UI 和 Trace Processor 查询引擎；网页查看器只是其中一个组成部分。 |
| Linux 内核跟踪 | ftrace | Linux 内核内置的跟踪框架，可记录调度、频率、进程生命周期等预定义事件。事件没有启用或内核没有提供时，Perfetto 无法补出这部分数据。 |
| Android 跟踪接口 | atrace | Android 的命令、类别和应用标记约定，用来启用平台事件或写入 `Trace.beginSection()`、`ATrace_*` 等标记。Perfetto 可以采集这些事件。 |
| 旧式系统跟踪 | Systrace | 旧文档中常指基于 atrace、ftrace 的采集工具与 HTML 报告；现代 Android 分析通常使用 Perfetto。小写 systrace 也可能泛指 system trace，要结合语境判断。 |
| 静态事件点 | tracepoint | 预先定义在内核代码中的低开销事件位置，启用后按事件格式写出字段。它与任意函数采样、日志文本的含义不同。 |
| 时间轴轨道 | `track` | Perfetto 时间轴中承载同类事件的一行，例如线程、CPU 或计数器轨道。名称相同的轨道不一定来自同一进程或同一数据源。 |
| 时间片段 | `slice` | track 上带起点和持续时间的事件，例如一次方法区间或 Binder 处理。slice 持续时间包含运行、等待或嵌套工作，不能直接当作 CPU 执行时间。 |
| 数值序列 | `counter` | 随时间记录数值样本的轨，例如 CPU 频率、内存量或队列深度。相邻样本间通常表示数值保持或变化，不表示一个函数执行区间。 |
| 事件关联 | `flow` | 在不同 slice 之间标记请求传递或依赖关系的连线。flow 帮助追踪事件去向，但单条连线不能自动证明业务因果。 |

读取 trace 时，先确认采集配置和缺失数据，再按 track 找到目标线程或组件，展开 slice、counter 与 flow。没有记录到的事件应标为证据缺口，不能按零耗时处理。

## 校准来源

- [Android Developers：应用启动时间](https://developer.android.com/topic/performance/vitals/launch-time)
- [Android Developers：ANR](https://developer.android.com/topic/performance/vitals/anr)
- [Android Developers：性能测量与关键用户场景](https://developer.android.com/topic/performance/measuring-performance)
- [Android Developers：慢渲染](https://developer.android.com/topic/performance/vitals/render)
- [Android Studio：Android 12 及以上版本的卡顿检测](https://developer.android.com/studio/profile/jank-detection)
- [Perfetto：FrameTimeline 卡顿检测](https://perfetto.dev/docs/data-sources/frametimeline)
- [AOSP：Android 图形架构](https://source.android.com/docs/core/graphics)
- [AOSP：Hardware Composer HAL](https://source.android.com/docs/core/graphics/hwc)
- [AOSP：Binder 概览](https://source.android.com/docs/core/architecture/ipc/binder-overview)
- [Android Developers：进程内存分配](https://developer.android.com/topic/performance/memory-management)
- [AOSP：低内存终止守护进程](https://source.android.com/docs/core/perf/lmkd)
- [Linux Kernel：`oom_score_adj` 取值与旧字段兼容](https://docs.kernel.org/filesystems/proc.html#proc-pid-oom-adj-proc-pid-oom-score-adj-adjust-the-oom-killer-score)
- [Android Developers：使用 WakeLock](https://developer.android.com/develop/background-work/background-tasks/awake/wakelock)
- [Perfetto：工具集概览](https://perfetto.dev/docs/)
- [Perfetto：录制系统 trace](https://perfetto.dev/docs/getting-started/system-tracing)
- [Arm：big.LITTLE 与 DynamIQ 的关系](https://developer.arm.com/community/arm-community-blogs/b/architectures-and-processors-blog/posts/where-does-big-little-fit-in-the-world-of-dynamiq)
