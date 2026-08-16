---
title: 典型场景分析
chapter: '7.4'
section: '7.4'
status: "finalized"
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: '2026-07-30'
last_verified_against: "AOSP android-17.0.0_r1, AndroidX Fragment 1.8.x (AIW 22.12 source chain), platform OnBackInvokedCallback/OnBackAnimationCallback @ API 33+, Perfetto/Winscope, Android 17 CDD"
confidence: high
consolidated_from:
- src/part2-performance/ch07-smoothness/15-scenario-playbooks.md
sources:
- type: blog
  path: obsidian/Personal-Knowlodge/source/Android-Perfetto-07-MainThread-And-RenderThread.md
- type: blog
  path: obsidian/Personal-Knowlodge/source/Android-Perfetto-05-Chorergrapher.md
- type: blog
  path: obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-2.md
- type: blog
  path: obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-3.md
- type: blog
  path: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md
- type: blog
  path: obsidian/Personal-Knowlodge/source/Android-Perfetto-06-Why-120Hz.md
- type: official
  path: developer.android.com/topic/performance/recycler-view
- type: official
  path: perfetto.dev/docs/analysis/trace-processor
tags:
- scrolling
- animation
- RecyclerView
- transition
- jank
- Perfetto
related_chapters:
- '7.1'
- '7.2'
- '7.3'
- '2.4'
- '2.5'
pipeline_stage: "finalized"
task6_state: "reviewed"
task9_state: "reviewed"
task2b_state: "fixed"
last_deep_review_at: "2026-07-30T08:35:51+08:00"
last_deep_review_run_id: "20260730-083551-deep-review-0a16d729"
last_review_finalize_at: "2026-07-30T10:05:03+08:00"
last_review_finalize_run_id: "20260730-100503-40fd0f28"
---

# 7.4 典型场景分析

## 场景名只负责缩小范围

“列表卡”“转场卡”“通知栏卡”描述的是用户当时看到了什么，还没有说明哪条渲染链路迟到。同一个列表里可以同时出现普通 View、SurfaceView 视频和 TextureView 地图；同一个页面切换又可能包含应用窗口 buffer（图形缓冲区）、Shell transition（系统窗口过渡）的 leash（用于统一控制窗口动画的临时图层）变换、壁纸、IME（输入法窗口）与 SurfaceFlinger 合成。若从场景名称直接跳到某个线程，证据很容易落到错误的对象上。

定位顺序如下：

1. 记录发生卡顿的交互阶段、显示屏、刷新率和时间区间。
2. 列出屏幕上的内容生产者，以及各自产出的 Surface（图形内容提交接口）、BufferQueue（连接内容生产者和消费者的缓冲队列）和 SurfaceFlinger layer（图层）。
3. 从 FrameTimeline（逐帧时间线）的异常 SurfaceFrame/DisplayFrame（单个 Surface 的帧记录/整屏显示帧记录），或目标 layer 的异常 present（呈现）反查。
4. 沿 token（帧标识）、frame number（帧序号）、transaction（图层状态事务）、buffer 与 fence（同步栅栏）找到最早迟到的阶段。
5. 回到责任线程，检查执行时间、Runnable（可运行但未获得 CPU）等待、锁、Binder、I/O、GC（垃圾回收）、GPU 和温控状态。

60 Hz 的名义刷新间隔约为 16.67 ms，120 Hz 约为 8.33 ms。它们不能直接充当任意线程的固定预算。Choreographer 回调相位、应用 deadline（截止时间）、BufferQueue 状态、SurfaceFlinger 调度和显示模式都会改变一帧的可用时间。诊断目标应写成“该帧相对 expected timeline（预期时间线）在哪里开始偏离”，不宜写成“整条管线必须在一个 VSync（垂直同步）间隔内全部结束”。

### 一张场景取证表

每次复现都建议先填写这张表。缺失的列，就是当前结论无法覆盖的边界。

| 维度 | 需要记录的内容 | 常用证据 |
|---|---|---|
| 交互 | 手指拖动、fling（惯性滑动）、点击、返回进度、窗口进入、通知更新 | input event（输入事件）、应用 marker（跟踪标记）、CUJ（Critical User Journey，关键用户操作流程） |
| 显示 | display id（显示屏标识）、刷新率、分辨率、显示模式 | SurfaceFlinger/Winscope、Perfetto |
| 窗口 | App Window、Dialog、Splash、IME、壁纸、transition leash | WindowManager、Shell Transitions |
| 内容生产者 | UI/RenderThread、MediaCodec、GL/Vulkan、WebView renderer、地图引擎 | 线程、进程、SDK/provider（实现提供方）版本 |
| 提交对象 | ViewRoot buffer、SurfaceView child layer（子图层）、TextureView 输入、task snapshot（任务快照） | BufferQueue、Layer、transaction |
| 帧结果 | expected/actual（预期/实际）、present type（呈现类型）、jank type（卡顿类型）、dropped/duplicated（丢弃/重复） | FrameTimeline、FrameTracer、fence |
| 责任边界 | 应用、SystemUI、Launcher、system_server、SF/HWC（SurfaceFlinger/Hardware Composer，系统合成服务/硬件合成器）、内核/驱动 | sched（调度）、Binder、GPU/HWC、kernel trace（内核跟踪） |

---

## 列表滑动：先区分拖动与 fling

列表滑动至少有两段不同的驱动方式。

- 手指按住并拖动时，输入分发和应用消费决定滚动位置何时更新。检查 MotionEvent（触摸事件）到主线程处理的间隔、输入回调耗时，以及同一帧的 traversal（测量、布局和绘制遍历）。
- 手指抬起进入 fling 后，滚动由动画时钟和 RecyclerView/ScrollView 的滚动计算继续推进。此时没有持续的触摸移动事件；要检查动画回调是否及时，以及每帧滚动工作是否稳定。
- 两个阶段都可能受 RenderThread、GPU、BufferQueue 或显示合成影响。主线程短只排除了部分应用 CPU 工作。

FrameTimeline 可以先圈定异常帧。随后把异常帧与正常帧放在一起比较，查看 UI Thread（主线程）、RenderThread（渲染线程）、对应的 App Window buffer 和 DisplayFrame。只看某个较长的 slice（时间区间），没有相邻正常帧作为对照，常会把稳定存在的初始化或后台任务误判为根因。

### RecyclerView 的三组内建线索

AndroidX RecyclerView 会在系统跟踪中留下有用的 slice。不同库版本的名称可能略有差别，官方慢帧文档常用以下三组线索：

| 线索 | 代表的工作 | 常见原因 | 处理方向 |
|---|---|---|---|
| `RV OnBindView` | 把数据绑定到已有 ViewHolder | 格式化、同步读取、复杂 span（富文本样式）、监听器反复创建 | 把纯数据准备移出 bind（绑定阶段），缓存稳定结果 |
| `RV CreateView` | inflate（创建布局）并创建 ViewHolder | item 树过深、View 类型多、复用不足 | 简化高频 item，按 viewType（视图类型）检查创建频率 |
| `RV Prefetch` | GapWorker（RecyclerView 的预取工作器）执行预取 | 嵌套列表、预取量不合适、共享池边界错误 | 按真实滚动方向和嵌套关系调整参数 |

`onBindViewHolder()` 运行在主线程，但它不一定嵌在名为 measure 或 layout 的 slice 里。判断 bind 是否拖慢一帧，应直接查看 RecyclerView slice 或应用自定义 marker，再观察它与 `Choreographer#doFrame`、traversal 的时间关系。

`onCreateViewHolder()` 偶尔出现是正常行为。只有它在用户可感知的滚动区间反复出现，并与异常帧对齐，才说明创建或复用需要处理。盲目增大 `RecycledViewPool` 会增加常驻 View 的数量，也可能错误共享配置或语义不同的 ViewHolder。缓存大小应由 viewType 分布、窗口尺寸、嵌套列表结构和内存实验共同决定。

布局容器没有固定的性能排名。ConstraintLayout 可以减少某些嵌套，也可能因约束求解、helper（辅助对象）或频繁变化增加工作。优化依据应是目标 item 的 measure/layout 次数和耗时，而非容器名称。

### 图片完成后仍可能影响三条路径

成熟的图片库通常会把网络请求和解码移到后台线程，但显示阶段仍会回到用户可见的渲染链路：

1. 结果回调在主线程更新 ImageView；
2. 尺寸或 drawable（可绘制对象）状态改变可能触发 `invalidate()` 或 `requestLayout()`；
3. 首次使用纹理时，RenderThread/GPU 可能产生上传与采样成本。

列表图片应在绑定前确定稳定的目标尺寸或宽高比。复用 ViewHolder 时，要取消或替换旧请求，并确认回调仍属于当前绑定项。图片预取要结合缓存命中率、解码尺寸和内存占用评估，不能只追求更早加载。

`RecyclerView.setHasFixedSize(true)` 表达的是 RecyclerView 自身尺寸不受 adapter（列表数据适配器）内容变化影响。它不会跳过 bind，也不会阻止 item 内部的 requestLayout。

### 小核、频率与调度结论

RenderThread 在某一帧运行于低容量 CPU，只能说明“当时在哪里执行”。要确认调度因素，需要同时检查：

- wakeup（唤醒）到 Running（开始运行）的等待时间；
- 线程的调度策略、优先级、uclamp（CPU 利用率约束）与 task group（任务组）；
- CPU capacity（算力容量）、频率、idle（空闲状态）退出和迁核；
- 同核更高优先级任务的抢占；
- thermal throttling（温控降频）与持续复现下的变化；
- 相同工作量在正常帧和异常帧上的执行时间。

应用侧通常无法据此要求线程固定运行在某个大核。系统或厂商团队若要修改调度策略，还需在 `android17-6.18-2026-06_r6` 对应的设备内核和 SoC（片上系统）调度实现上验证；Android common kernel 不规定厂商拓扑、频点或 GPU/HWC tracepoint（跟踪点）的统一形态。

---

## 页面切换：拆开内容准备、窗口事务与显示

### Activity transition

Activity 跳转可能发生在同一进程，也可能拉起已有进程或新进程。诊断前要区分热启动、温启动和冷启动，并记录目标页面的 TTID（Time to Initial Display，首次显示时间）、TTFD（Time to Full Display，完全显示时间）与第一帧。把所有跳转都写成“两个应用进程协同”，会漏掉同进程场景，也会掩盖冷启动中的进程创建和类加载。

Android 17 的现代窗口过渡需要同时观察三条线：

- 应用侧：源/目标 Activity 生命周期、inflate、首个 traversal、RenderThread 和窗口 buffer；
- 窗口侧：WindowManager Shell transition、参与者、sync（同步点）、SurfaceControl leash 与几何事务；
- 显示侧：目标 layers 的 buffer/transaction、SurfaceFlinger composition（合成）和 display present。

源窗口和目标窗口的内容提交与 leash 动画可以来自不同线程、不同进程。应用首帧准备较晚时，Shell 可能继续显示 starting window（启动占位窗口）、snapshot（任务快照）或旧 Surface；应用两侧按时而整屏仍迟到时，应查看 SurfaceFlinger/HWC。Winscope 的 Shell Transitions、Window Manager、SurfaceFlinger Layers 和 Transactions 可以复原窗口关系，Perfetto 更适合比较线程调度、buffer 与帧时间。

### Fragment transaction

AndroidX Fragment 的 `commit()` 会把事务加入 FragmentManager 队列：它经 `enqueueAction()` / `scheduleCommit()`，通过宿主的 `Handler`（消息处理器）调用 `post`，投递一个 `mExecCommit`，随后由宿主主线程执行 pending actions（待处理操作）。它不承诺与某个 VSync 对齐。`mExecCommit` 与 Choreographer 帧回调共享同一个主 Looper（消息循环），但实际执行顺序取决于主 MessageQueue（消息队列）中已有消息、同步屏障、异步 Choreographer 消息，以及 `commit()` 的发生时刻；不存在“`execPendingActions()` 必定早于或晚于某次 `doFrame`”的固定顺序。使用 `commitNow()` 会把工作放进当前调用栈，改变这一相对位置。一次切换可能把 Fragment 状态推进、View 创建/移除、SpecialEffectsController（转场与动画效果控制器）、measure/layout 和动画准备集中到相邻几帧。

几个 API 的边界需要分清：

- `commit()` 异步排队；返回时事务通常尚未执行。
- `commitNow()` 在调用线程同步执行，要求主线程，且不能与 `addToBackStack()` 组合。它会把工作提前到当前调用点，不能作为通用的流畅度开关。
- `executePendingTransactions()` 会执行当前待处理事务，影响范围可能超过某一次提交。
- `setReorderingAllowed(true)` 允许 FragmentManager 优化同一批操作的状态变化，并改善 transition/lifecycle（转场/生命周期）语义。它不能消除布局、业务初始化或 GPU 工作。
- `commitAllowingStateLoss()` 改变的是保存状态后的提交约束，用它规避卡顿会引入状态丢失风险。

取证时可以分别标记“发起 commit”“pending actions 开始/结束”“目标 Fragment 首次可见”和“第一帧 present”。若卡点在 `onCreateView()`、`onViewCreated()` 或首个 layout，应处理页面构建；若 App buffer 已经按时提交，则继续检查 transition transaction 和 display frame。更完整的源码链路见 [22.10 FragmentTransaction 提交链路与页面切换性能](../../part5-app/ch22-rendering-practice/10-fragment-transaction-performance.md)。

### Shared element

共享元素转场的成本取决于具体实现和元素类型，可能涉及源/目标 View 的名称匹配、布局坐标捕获、overlay/ghost（叠加层/临时镜像视图）、snapshot、图片资源准备、matrix/clip（变换矩阵/裁剪）更新，以及两个窗口的可见性协调。不能把所有共享元素都概括为“复制一张 bitmap”。

常见的断点包括：

- 目标元素尚未完成布局，终点 bounds（边界）不稳定；
- 大图在转场开始后才解码或上传；
- 元素层级在转场期间触发额外 layout；
- 源窗口、目标窗口与 transition leash 的时序没有对齐；
- alpha（透明度）、圆角、模糊或遮罩改变了合成条件。

应同时记录元素准备回调、目标页首个 traversal、窗口 transition 和对应 layer present。只优化目标 Activity 的 XML，无法覆盖源窗口迟到或显示合成迟到。

---

## 窗口动画：Splash、返回手势与浮层

### SplashScreen 与 starting window

Android 12（API 31）起，系统 SplashScreen API 为冷启动和温启动提供统一的启动画面；热启动通常不会显示该画面。Splash screen（启动画面）是一个独立窗口，会在应用可以绘制前覆盖目标窗口，并在应用第一帧就绪前后退出。

一次“启动时闪顿”可拆成四个时间点：

1. 启动请求进入 ActivityTaskManager（Activity 与任务管理服务）；
2. starting/splash window（启动占位窗口/启动画面）可见；
3. 应用目标窗口提交第一块可用 buffer；
4. splash 退出动画结束，目标窗口在显示端 present。

若第 2 到第 3 个时间点间隔很长，应检查进程启动、Application/Activity 主线程、资源和首帧。若应用 buffer 已经到达而交接仍然抖动，应检查 splash exit listener（启动画面退出监听器）、Shell/WMS transaction（Shell/WindowManagerService 窗口事务）、目标 layer 和 SurfaceFlinger。自定义退出动画完成后还要移除 splash view；持续保留它会延长交接窗口。

### Predictive Back

Android 15 移除了预测性返回的开发者选项。应用完成 opt-in（显式启用）后，系统可以提供返回桌面、跨 Activity 和跨任务的预测动画；具体效果仍受导航结构、回调类型和系统实现影响。相关的平台与 AndroidX 回调接口需要分清，三者不能混用：

- `OnBackPressedCallback`（AndroidX Activity 1.6 及更高版本）：`handleOnBackPressed()` 由 `OnBackPressedDispatcher` 分发；它只在返回提交时触发，本身不提供连续进度。
- `OnBackInvokedCallback`（平台，API 33 及更高版本）：只有 `onBackInvoked()`，在返回“提交”时回调。它同样没有 started/progressed/cancelled（开始/进行/取消）的进度语义。
- `OnBackAnimationCallback`（平台，API 33 及更高版本，依赖 `android:enableOnBackInvokedCallback="true"`）：提供 `onBackStarted(BackEvent)`、`onBackProgressed(BackEvent)`、`onBackCancelled()` 和 `onBackInvoked()` 的完整生命周期。需要按手势进度驱动自定义动画时，必须使用这个接口；前两个接口无法提供连续进度。

诊断要同时检查三个问题：

- 手势进度回调（`OnBackAnimationCallback`）是否短小、连续，取消路径（`onBackCancelled`）能否恢复界面状态；
- 当前回调是否消费了系统返回，导致系统预测动画无法运行；
- 当前窗口、目标窗口或 home/task surface（桌面/任务 Surface）的 leash 与 display frame 是否按时。

Perfetto 中没有名为 `predictive_back_progress` 的标准内置 counter（计数轨道）。返回手势的进度与参与者由 SystemUI `EdgeBackGestureHandler`、WindowManager Shell transition 和 `BackGestureProto`/Winscope 记录。trace 会记录各进程的自定义 Trace section（跟踪区间）、Shell transition marker（标记）与 sched（调度）数据，但没有统一的标准 counter 轨道。需要验证 progress 回调时序时，应使用应用自身插桩（例如 `Trace.beginSection("onBackProgressed")`）或 Winscope 的 Shell 参与者，不要预设某个标准 counter 名称。

Android 16（API 36）起，可以使用 `PRIORITY_SYSTEM_NAVIGATION_OBSERVER` 观察系统导航而不消费返回；Android 17（API 37）继续保留这一能力。默认优先级或 overlay（覆盖层）优先级回调会参与消费决策。注册方式错误时可能出现“没有预测动画”，这与渲染掉帧属于两类问题。

不要假设返回预览总是一张目标 Activity 的缩略图。跨 Activity、跨任务和返回桌面时，参与的 surfaces 由导航状态与 Shell transition 决定，应从 Winscope 的参与者和 layer tree（图层树）确认。

### Dialog 与 PopupWindow

Dialog 和 PopupWindow 都会向 WindowManager 增加窗口对象，并拥有各自的 ViewRoot 与 Surface；它们可以与宿主处于同一进程和同一 UI Looper（界面消息循环）。弹出时的成本可能来自：

- 首次 inflate、measure/layout 和窗口首帧；
- 同一主线程上宿主窗口与浮层窗口的 traversal 排队；
- IME/Insets（输入法与系统栏等占用区域）变化；
- dim（背景变暗）、blur（模糊）、圆角、阴影和动画；
- 新 layer 加入后，HWC 的 DEVICE（显示硬件合成）/CLIENT（GPU 客户端合成）分配变化；
- GPU 带宽、client target 或 present fence 延迟。

“出现额外 layer”不等于“一定走 GPU client composition（客户端合成）”。HWC 是否使用 overlay（硬件叠加平面）取决于整组 layers 的格式、变换、混合、保护属性、硬件资源和厂商能力。可以把弹出前后的 layer composition type（合成类型）、client target（客户端合成目标）、GPU 时长与 present 结果放在一起比较。深入案例见 [HWC Overlay Plane 与合成降级排查](./12-hwc-overlay-composition-downgrade.md)。

---

## Notification 展开与折叠：责任进程在 SystemUI

通知面板的展开、折叠、分组和 Quick Settings（快捷设置）动画，主要由 SystemUI 生成 UI 帧。普通应用在发布或更新通知时通过 Binder 提交 Notification；动画期间如果通知内容没有更新，应用进程可能完全不在关键路径上。

需要分别检查：

| 阶段 | 责任对象 | 典型证据 |
|---|---|---|
| 发布/更新通知 | 应用、system_server、SystemUI | Binder、NotificationManagerService、SystemUI pipeline（处理管线） |
| 应用 RemoteViews/模板 | SystemUI 主线程 | inflate/reapply（创建/重新应用视图）、图片/图标、measure/layout |
| Shade（通知面板）动画 | SystemUI UI Thread/RenderThread | FrameTimeline、CUJ、traversal、DrawFrame |
| 整屏合成 | SurfaceFlinger/HWC | visible layers（可见图层）、composition type、present |

频繁更新进度、反复改变通知布局或提交大图片，会增加跨进程传输和 SystemUI 的处理成本。RemoteViews（可跨进程应用的视图描述）更新时，可能复用已有 View，也可能需要重新应用布局；应以 trace 和通知差异为准，不能断言每次 `notify()` 都会重新 inflate。

以 Android 12（API 31）及更高版本为目标的应用，自定义通知会被系统放入标准模板，以保持图标、展开区域和操作的一致性。这个限制并不会消除自定义内容的处理成本：复杂 RemoteViews、图片尺寸、更新频率和分组规模仍会影响 SystemUI。

如果 SystemUI 的 SurfaceFrame 按时而 DisplayFrame 迟到，再检查遮罩、壁纸、状态栏、导航栏、当前 App 和通知面板的合成。应用自己的 App FrameTimeline 不能代表通知面板。

---

## 桌面滑动与多任务切换：以 OEM 现场为准

### Launcher 桌面

AOSP（Android 开源项目）的 Launcher3 提供 Workspace、CellLayout、Widget 与 Quickstep（手势导航和最近任务组件）的参考实现，量产设备可能替换 Launcher 或修改动画。桌面滑动常见的内容包括图标、文件夹、AppWidget、壁纸和搜索/推荐区域；其中 Widget 更新、动态壁纸和 Launcher 帧可能来自不同的内容生产者。

诊断顺序可按对象展开：

1. Launcher 主线程的输入、动画和 traversal；
2. Launcher RenderThread/GPU；
3. AppWidget 更新是否在同一时间进入 Launcher；
4. 壁纸 layer 或 WallpaperService 是否更新；
5. SurfaceFlinger 的可见 layers、composition 与 present；
6. sched、CPU frequency、thermal 和 GPU 证据。

发现 RenderThread 位于小核时，还要继续验证唤醒等待、CPU capacity、频率与同帧工作量。单帧的 CPU 编号不能单独支持“调度器导致卡顿”的结论。

### Recents / Overview

AOSP Quickstep 由 Launcher3 实现，窗口组织和动画还依赖 WindowManager Shell、ActivityTaskManager、SurfaceControl transactions 与 SurfaceFlinger。OEM（设备厂商）可以更换参与者或动画实现，因此进程名和 slice 名称应从目标设备采集。

多任务手势可能操作以下对象：

- 当前任务的 live surface（实时任务画面）与 transition leash；
- 其他任务的 snapshot；
- Launcher 的 Recents UI；
- 壁纸、系统栏和手势相关 surfaces；
- 即将恢复的目标任务窗口。

Task snapshot 通过 `TaskSnapshot` 携带 HardwareBuffer（硬件图形缓冲区）、色彩空间、方向和裁剪等信息。Launcher 采样硬件 buffer 不等同于执行普通图片文件解码；压力更多来自 snapshot 获取时机、卡片数量、纹理采样、显存/带宽和整屏合成。某些阶段会继续使用 live task surface（实时任务 Surface），因此不能把每张卡片都解释成静态截图。

在 Winscope 中，应检查 Shell transition 的参与者、WindowManager 状态、SurfaceFlinger layers 和 transactions；再在 Perfetto 中对齐 Launcher/SystemUI/system_server 的线程、输入、snapshot 相关 Binder、GPU 与 DisplayFrame。若动画卡片移动正常而内容停住，需要辨别当前看到的是 snapshot、旧 buffer 还是 live surface。

---

## 视频：UI 帧与视频帧要分开

视频通常由 MediaCodec 或播放器渲染器向 Surface 输出 buffer。使用 SurfaceView 时，视频通常拥有独立的 child layer（子图层）；使用 TextureView 时，视频 buffer 先进入 SurfaceTexture，再由宿主 HWUI（Android 硬件加速 UI 渲染管线）在 App Window 中采样。两条路径的责任线程、buffer 数量和 FrameTimeline 覆盖范围不同。

视频“卡”的含义至少有三种：

- 解码器没有按节奏产出可用 buffer；
- buffer 已 queue（入队），但 fence、latch、合成或显示时刻迟到；
- 播放器主动丢帧或重复帧，以维持音视频同步。

应记录媒体 presentation timestamp（PTS，呈现时间戳）、解码输入/输出、目标 Surface 的 frame number、queue/acquire/release（入队/获取/释放）、display present 和音频时钟。UI 的 App FrameTimeline 正常，不能证明独立视频 layer 连续更新；反过来，视频连续也不能证明控制栏动画流畅。

HWC overlay 能减少 GPU 合成压力，但是否可用取决于格式、缩放、旋转、HDR（高动态范围）、受保护内容、其他 layers 与硬件资源。应检查目标 layer 的实际 composition type，不要依据 SurfaceView 或 MediaCodec 名称推断 overlay。详见 [视频 Overlay 与 HWC](../ch18-rendering-pipelines/15-video-overlay-hwc.md) 和 [MediaCodec2、Tunneled Playback 与 Media3 ABR](../ch18-rendering-pipelines/21-media-codec2-tunneled-media3-abr.md)。

---

## 地图与 WebView：先确认承载方式

### 地图 SDK

地图 SDK 可能使用 SurfaceView、TextureView、GLSurfaceView、自建 SurfaceControl，或把部分内容画进宿主窗口。瓦片下载、矢量解析、标注布局和 GL/Vulkan 提交也可能分属不同线程。没有 SDK 版本、实际 View 类型和 layer tree（图层树），就无法把“地图卡顿”归到固定的 GL 线程。

排查时先确认：

- 地图主体是独立 layer，还是作为纹理合入 App Window；
- 相机移动由手势线程、主线程还是渲染线程驱动；
- 瓦片 I/O/解码是否阻塞渲染依赖；
- shader/pipeline（着色器/图形管线）创建、纹理上传和 GPU 执行是否与异常帧对齐；
- 独立 layer 与宿主控件的更新是否落在同一 display frame。

SurfaceView 与 TextureView 的差别可分别参见 [SurfaceView 渲染管线](../ch18-rendering-pipelines/06-surfaceview.md) 和 [TextureView 渲染管线](../ch18-rendering-pipelines/07-textureview.md)。

### WebView

标准硬件加速 WebView 的网页主体通常经 Chromium renderer（渲染进程）、compositor/GPU 服务（合成器/GPU 服务）和 WebView functor（连接 Chromium 与 Android HWUI 的绘制桥接对象）合入宿主 App Window。视频、受保护内容、provider overlay（WebView 实现提供方添加的叠加层）或定制内核可能增加独立的 SurfaceControl layer。网页主体与媒体 overlay 需要分开追踪。

WebView 是可以独立更新的组件。平台源码可以锚定 `android-17.0.0_r1`，分析 Chromium 行为时还必须记录设备上的 WebView provider 包名、版本与 revision（修订版本）。仅凭 Android 17 平台版本标签，无法确认某个 Chromium slice 名称或进程结构。

| 现象 | 优先查看 |
|---|---|
| JS 长任务后页面不动 | renderer main thread（渲染进程主线程）、V8（JavaScript 引擎）、DOM/layout（文档对象模型处理/布局）依赖 |
| 页面 paint/raster（绘制/栅格化）晚 | Blink paint（网页绘制）、compositor、raster/GPU service（栅格化/GPU 服务） |
| 宿主控件和网页一起晚 | App UI Thread、HWUI functor、host RenderThread（宿主渲染线程） |
| 视频晚而页面滚动正常 | 独立媒体 layer、codec（编解码器）、fence、HWC |
| host buffer（宿主缓冲区）已提交但屏幕晚 | SurfaceFlinger/HWC、DisplayFrame |

Renderer 退出应结合进程生命周期、LMK（低内存终止）/OOM（内存不足）证据与 `WebViewClient.onRenderProcessGone()` 判断。除非应用自行插桩，不要预设 trace 中存在名为 `render_process_gone` 的 slice。完整结构见 [WebView 渲染管线](../ch18-rendering-pipelines/13-webview-rendering.md) 和 [WebView 性能优化实战](../../part5-app/ch22-rendering-practice/07-webview-optimization.md)。

---

## 从症状到证据的速查表

| 场景症状 | 第一组对象 | 继续验证 | 容易误判的结论 |
|---|---|---|---|
| 列表拖动立即跟手差 | input、UI Thread、RecyclerView | RenderThread、App Window、DisplayFrame | “一定是 onBind” |
| fling 周期性顿挫 | animation、RV bind/create/prefetch | 图片回调、GC、sched、GPU | “每帧都必须少于刷新间隔” |
| Activity 切换开头停顿 | 目标首帧、启动类型 | Shell transition、source/target layers（源/目标图层） | “总有两个进程” |
| Fragment 切换卡 | pending actions、生命周期、layout | SpecialEffectsController、RenderThread | “改用 commitNow 就会快” |
| Splash 退场抖动 | splash 与目标窗口交接 | exit listener（退出监听器）、transaction、present | “只有 Application 启动慢” |
| 返回动画缺失 | opt-in、callback 消费 | Shell 参与者 | “缺失就是掉帧” |
| Dialog 出现后整屏变慢 | 新 ViewRoot/layer、dim/blur | HWC composition、GPU/present | “多一个 layer 必走 CLIENT” |
| 通知栏卡 | SystemUI FrameTimeline | RemoteViews、SF/HWC | “发布通知的 App 在画 Shade” |
| Recents 卡片内容停住 | snapshot/live surface | Quickstep/Shell、SF transaction | “所有卡片都是 bitmap 解码” |
| 视频停顿、控件流畅 | codec producer（编解码器生产者）、视频 layer | PTS、fence、HWC/present | “App FrameTimeline 正常就没掉视频帧” |
| WebView 页面卡 | provider renderer/compositor | host HWUI、媒体 overlay、SF | “只查宿主主线程” |

---

## Android 17 与内核锚点

平台结论以 Android 17 / API 37、AOSP `android-17.0.0_r1` 为上界。RecyclerView、Fragment、WebView provider 和地图 SDK 都可以独立更新，因此复现报告还要记录它们的版本。厂商 Launcher、SystemUI、HWC、GPU 驱动与调度策略也可能偏离 AOSP 参考实现。

内核侧以 `android17-6.18-2026-06_r6` 为锚点。通用证据包括 sched wakeup/switch（调度唤醒/切换）、CPU frequency/idle（频率/空闲状态）、thermal、dma-buf（设备间共享缓冲区）与 dma-fence（设备缓冲同步栅栏）；设备可见的 GPU、display、HWC 和厂商调度事件由 SoC 与构建配置决定。缺少某个厂商 tracepoint 时，应保留“不足以继续归因”的边界，不能用线程名称或 CPU 编号补全结论。

---

## 复盘模板

一份可复核的场景结论至少回答以下问题：

1. 哪次交互、哪块显示屏、哪个刷新率下复现？
2. 用户感知对应哪个 SurfaceFrame、DisplayFrame 或目标 layer present？
3. 画面由哪些 producer（内容生产者）、Window、Surface 和 layer 构成？
4. 最早偏离 expected timeline 的事件是什么？
5. 迟到线程当时处于 Running（运行中）、Runnable（可运行但未获得 CPU）、Sleeping（睡眠）、Blocked（阻塞）还是 fence wait（栅栏等待）？
6. 应用 buffer、窗口几何 transaction 与 display present 分别何时完成？
7. 修复改变了哪项可测量证据，相邻正常帧和异常帧是否收敛？
8. 结论依赖的平台、AndroidX、WebView provider、OEM 和 kernel（内核）版本是什么？

场景归类的作用是减少待检查对象；真正的归因仍要依靠源码、trace 和对照实验。若证据无法跨过 Surface、进程或显示边界，结论就只能停在当前层级。

---

## 相关章节

- [卡顿的定义与 FrameTimeline 语义](./01-jank-definition.md)
- [卡顿原因分类](./02-jank-causes.md)
- [可复现的卡顿分析方法](./03-jank-methodology.md)
- [渲染管线总览](../ch18-rendering-pipelines/01-pipeline-overview.md)
- [多窗口渲染](../ch18-rendering-pipelines/05-android-view-multi-window.md)
- [渲染管线分析方法](../ch18-rendering-pipelines/01-pipeline-overview.md#统一分析方法)

## 参考资料

- [Slow rendering：RecyclerView trace labels 与常见处理](https://developer.android.com/topic/performance/vitals/render)
- [AndroidX Fragment transactions](https://developer.android.com/guide/fragments/transactions)
- [SplashScreen API](https://developer.android.com/develop/ui/views/launch/splash-screen)
- [Predictive Back gesture](https://developer.android.com/guide/navigation/custom-back/predictive-back-gesture)
- [Create a custom notification layout](https://developer.android.com/develop/ui/views/notifications/custom-notification)
- [Winscope overview](https://source.android.com/docs/core/graphics/winscope/overview)
- [Winscope tables and Shell transitions](https://source.android.com/docs/core/graphics/winscope/analyze/search)
- [Frame pacing](https://source.android.com/docs/core/graphics/frame-pacing)
- [SurfaceFlinger and WindowManager](https://source.android.com/docs/core/graphics)
- [Hardware Composer HAL](https://source.android.com/docs/core/graphics/implement-hwc)
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [AOSP Android 17 Choreographer](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java)
- [AOSP Android 17 FrameTimeline](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp)
- [AOSP Android 17 Shell transitions](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/WindowManager/Shell/src/com/android/wm/shell/transition/)
- [AOSP Android 17 TaskSnapshotController](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/TaskSnapshotController.java)
- [Android common kernel sched tracepoints](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/sched.h)
- [Android common kernel dma-fence](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)
