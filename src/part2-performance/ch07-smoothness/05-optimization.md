---


title: "优化策略"
section: "7.5"
chapter: "7.5"
status: finalized
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
last_verified: "2026-04-20"
last_verified_against: "AOSP android-16.0.0_r1, Android 官方文档, AndroidX RecyclerView release notes"
confidence: high
sources:
  - type: blog
    path: "obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md"
  - type: official
    path: "developer.android.com/topic/performance/recycler-view"
  - type: official
    path: "developer.android.com/develop/ui/compose/performance"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/RenderEffect"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/RenderEffect.java"
  - type: aosp
    path: "frameworks/base/libs/hwui/jni/RenderEffect.cpp"
  - type: aosp
    path: "frameworks/base/libs/hwui/RenderProperties.h"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/RenderNode.java"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/recyclerview"
  - type: official
    path: "developer.android.com/develop/ui/views/layout/constraint-layout"
  - type: aosp
    path: "frameworks/base/core/java/android/view/ViewStub.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/View.java (LAYER_TYPE_HARDWARE)"
tags:
  - android
  - smoothness
  - jank-optimization
  - recyclerview
  - compose-performance
  - layout-optimization
pipeline_stage: ready-to-publish
task6_state: "reviewed"
task9_state: reviewed
task2b_state: fixed
---

# 7.5 优化策略

## 优化从一条可证伪的假设开始

卡顿优化的单位应是“某类帧上的某段工作”，而不是布局、线程或框架名称。一次修改至少要写清四件事：

- 哪个 SurfaceFrame 或 DisplayFrame 异常；
- 最早迟到的是 UI Thread、RenderThread、GPU、buffer/fence、SurfaceFlinger 还是 HWC；
- 修改准备减少哪段工作、等待或资源占用；
- 在相同设备、刷新率、数据集和热状态下，哪项指标应发生变化。

这套约束能挡住两类无效优化。一类是把工作挪到别处，应用主线程变短了，后台线程、GPU 或内存压力却升高；另一类是改完平均值，长尾帧和用户感知没有变化。

评估前应固定测试条件。至少记录设备与 build、Android/AndroidX/Compose/WebView 版本、显示模式、功耗模式、温度、编译模式、数据规模和交互脚本。帧指标优先看分位数、slow/frozen frame、FrameTimeline jank type 和目标 CUJ，平均 FPS 只适合补充描述。

---

## 布局优化：减少无用工作，不追求最低层数

### View 树成本由次数和单次成本共同决定

一次 traversal 可能包含 measure、layout、draw record，但不是每帧都会完整执行三段。属性变化、requestLayout、窗口尺寸、Insets、动画和父容器实现会决定哪些阶段重跑。布局性能可以拆成：

> 总成本 ≈ traversal 次数 × 每次访问的节点数 × 单节点工作量

树深只是其中一个变量。浅层容器也可能拥有大量子节点、复杂文本、昂贵自定义测量或反复 requestLayout；多一层简单 FrameLayout 在许多页面里几乎不可见。优化时应从异常帧里的 measure/layout slice 和调用来源出发，再用 Layout Inspector、ViewCapture 或应用 marker 确认目标子树。

没有通用的“超过 N 层必须重构”或“measure 超过 N ms 必须换布局”。高刷新率、低端设备、大字号、横竖屏与多窗口会改变成本边界。

### ConstraintLayout 的适用条件

ConstraintLayout 适合把多层相对定位、权重分配和对齐关系放进一个容器。它的收益来自减少中间 ViewGroup 和重复传播，不代表约束求解永远只需一次测量，也不代表它在简单横排/竖排上固定快于 LinearLayout。

判断是否值得替换时，比较以下证据：

- 替换前后 View 节点数与层级；
- 目标子树的 measure/layout 次数；
- 相同内容下的主线程 CPU 时间与分配；
- 约束变化、Barrier/Flow/Group 等 helper 带来的额外工作；
- 可读性、可访问性和适配复杂度。

对只有少量子 View 的静态行，简单容器往往更容易维护。对 RecyclerView 热点 item，任何重构都应在真实 bind、字体比例和 item 宽度下跑 Macrobenchmark。

### ViewStub 的边界

ViewStub 是不可见、零尺寸的占位 View。调用 `inflate()` 或把它设为 VISIBLE/INVISIBLE 时，`inflateViewNoAdd()` 使用 LayoutInflater 创建目标布局；`replaceSelfWithView()` 随后调用父 ViewGroup 的 `removeViewInLayout()` 和 `addView()`，在原索引处换入新 View。Android 17 源码仍沿用这条路径。

它适合低命中率、创建成本较高且允许延后出现的区域，例如错误面板、一次性引导或少见配置页。使用时要考虑：

- 一个 ViewStub 实例只能完成一次替换；需要保留 `inflate()` 的返回 View 或新布局 id；
- inflate 仍在调用线程执行，若在动画关键帧里触发，成本只是被推迟；
- 目标资源不能以 `<merge>` 作为根，因为 ViewStub 的 inflate 路径不以 attach-to-root 方式处理该资源；
- 延后创建会改变首次交互延迟、焦点、无障碍节点和状态恢复时机。

已知页面必然展示的核心区域不适合用 ViewStub 延迟到首次触摸才创建。

### `<merge>`、`<include>` 与 GONE

`<merge>` 可以在 include 场景省去一个纯包装根节点，前提是父容器能负责原根节点的布局语义。去掉根节点后，layout params 的归属、背景、padding、clip 和 accessibility 语义都要复核。

预先 inflate 一组 GONE View 会支付对象创建和内存成本。多数 ViewGroup 在测量与布局时会跳过 GONE child，但仍可能在遍历、状态分发或自定义容器逻辑中遇到它们。低概率且较重的区域可用 ViewStub；高频切换的小组件保留为 GONE 通常更合适，避免反复创建。

### 布局修改怎样验收

一次布局优化应同时检查：

| 证据 | 希望看到的变化 | 不能单独证明什么 |
|---|---|---|
| FrameTimeline | 目标帧的 App deadline miss 减少 | 根因必然是布局 |
| UI Thread slice | measure/layout/traversal 缩短 | Display 已按时 present |
| Layout Inspector/ViewCapture | 目标子树结构符合预期 | 运行时成本一定下降 |
| 分配/GC | 热路径临时对象减少 | GPU 或合成压力下降 |
| 截图与无障碍测试 | 视觉、焦点、语义未回归 | 长尾帧已经改善 |

---

## RecyclerView：把创建、绑定与变更分开处理

### bind 与 create 各有不同的优化入口

`RV OnBindView` 长时，检查数据格式化、同步 I/O、跨进程调用、span 构造、监听器创建、图片请求和 item 内部的 requestLayout。可复用的纯计算结果应在数据层生成；UI 相关结果仍需尊重主题、locale、尺寸和生命周期。

`RV CreateView` 长时，检查 inflate、View 数量、构造函数、自定义属性解析与 viewType 分布。创建频率高还可能说明 pool 边界、stable id、嵌套列表或快速滚动行为不符合预期。减少单次创建成本与减少创建次数是两项独立工作。

应用自定义 trace section 应包住目标业务逻辑，并避免在 section 名里拼接无限种 position/id。高基数 slice 会增加 trace 体积，也不利于聚合。

### DiffUtil、ListAdapter 与 payload

`DiffUtil.calculateDiff()` 是同步计算 API；在哪个线程调用，它就在哪个线程执行。ListAdapter 与 AsyncListDiffer 通过异步 differ 把 diff 计算移出主线程，再在主线程分发更新。自建路径必须保证新旧列表在计算期间不被修改。

`areItemsTheSame()` 判断业务实体身份，`areContentsTheSame()` 判断可见内容是否相同。两者写错会产生错误动画、漏更新或无效 bind。内容只有局部变化时，可通过 change payload 做局部绑定，但 payload 的合并、丢弃和完整绑定路径都要正确处理。

`notifyDataSetChanged()` 丢失 item 级变更信息，RecyclerView 只能按“整体结构可能变化”处理。它有时是语义正确的兜底，不应为了追求最小更新而提交错误 diff。

### 预创建、GapWorker 与共享池

RecyclerView GapWorker 在主线程执行，并根据滚动信息和 deadline 尝试预取即将进入视口的 item。它利用的是预计可用预算，不等同于一个保证存在的“空闲线程”。create/bind 太重时，预取自身也可能贴近当前帧或抢占其他 UI 工作。

嵌套 RecyclerView 可通过 LayoutManager 的 initial prefetch item count 表达首屏需要的内层 item 数量。数值应覆盖可见需求，并由 trace 校正。设得过大会增加创建、绑定、图片请求和内存占用。

共享 RecycledViewPool 前要保证参与列表的 viewType 语义兼容。共享池减少 inflate 的机会，也会延长 ViewHolder 和其资源的存活。配置变更、主题差异、ComposeView 状态和图片请求都要进入复用测试。

若希望在业务空闲期主动预创建 ViewHolder，需要设置明确上限、取消条件和内存预算，并确认创建路径允许脱离当前 layout 状态。很多页面直接依赖 RecyclerView 自带预取会更稳。

### SnapHelper

SnapHelper 在滚动结束和 fling 目标计算附近工作。自定义实现应只检查可见或邻近候选项，避免遍历完整数据集、读取磁盘或触发新的布局。几何计算要覆盖 reverseLayout、RTL、padding、item decoration 与可变尺寸 item。

Android 15（API 35）引入 `View.setFrameContentVelocity()`。RecyclerView 1.4.0 起可在 OverScroller 路径向平台报告内容速度，帮助支持该能力的设备选择刷新行为。自定义滚动器绕开 OverScroller 时，是否上报速度应按目标 API、运动模型和设备验证；SnapHelper 没有一套单独的 Android 17 优化接口。

### RecyclerView 验收清单

- 异常帧中的 `RV OnBindView`、`RV CreateView`、`RV Prefetch` 分别怎样变化？
- 更新列表时，diff CPU、主线程 apply、动画和 bind 次数是否分别统计？
- 快速 fling、反向滚动、数据插入和配置变更下，复用是否正确？
- 图片请求是否随 ViewHolder 复用取消，目标尺寸是否稳定？
- 预取增加的内存、后台解码和网络流量是否在预算内？
- App SurfaceFrame 改善后，DisplayFrame 是否也改善？

更完整的场景分析见 [RecyclerView 性能](./08-recyclerview-performance.md)。

---

## 渲染优化：减少像素工作和中间目标

### Overdraw 要结合像素成本

Overdraw 表示同一像素在一帧内被多次覆盖。开发者选项的 GPU overdraw 可视化适合找大片重复背景，但颜色只是次数分档，无法说明每次绘制的 shader、纹理采样、blend 和目标分辨率成本。

常见处理包括移除被完全遮住的背景、缩小透明区域、避免重复全屏遮罩，并让 clip/damage 与可见区域匹配。clipPath 本身可能带来 stencil、mask 或额外 GPU 工作，不能当作通用的 overdraw 优化。宿主窗口内部的透明、圆角、模糊和阴影主要增加 HWUI/GPU 工作；发生在独立 Window 或 SurfaceFlinger layer 上的透明、模糊与变换还可能改变 HWC composition 条件。

### Hardware Layer

在硬件加速窗口中，`LAYER_TYPE_HARDWARE` 可让一个 View 子树缓存在 GPU 离屏资源中。子树内容稳定、只变化 translation/scale/alpha 等合成属性时，后续帧可以复用缓存，减少 display list 重放和栅格化。

下列场景收益有限或可能倒退：

- 子树内容每帧 invalidate，缓存需要持续更新；
- layer 面积很大，显存和带宽成本高；
- View 很简单，建立/管理 layer 的成本超过省下的绘制；
- 多个半透明 layer 叠加，GPU blend 或 HWC 资源受压；
- 忘记在临时动画结束后恢复 layer type。

硬件 layer 是宿主 App Window 内的离屏资源，不会因此自动成为 SurfaceFlinger 可见的独立 layer。验证时看 UI/RenderThread、GPU、内存和宿主窗口 FrameTimeline。

### Canvas 与自定义 View

自定义绘制的优化入口包括：

- 在尺寸、文本或数据变化时准备 Paint、Path、StaticLayout 等对象，避免在每次 draw 中重复分配和解析；
- 复用对象时保证状态被完整重置，避免共享可变 Paint 引入渲染错误；
- 限制 save/restore、saveLayer、clipPath 和大面积透明 blend；
- 只在内容变化时 invalidate，能确定脏区时缩小 damage；
- 将独立纯计算移出 UI Thread，同时把线程安全、字体、locale 和尺寸作为输入；
- 对复杂路径、图片上传和 shader 编译分别检查 CPU 与 GPU 证据。

“onDraw 中零分配”是有用的目标，但不能以缓存无限增长或共享错误状态为代价。

---

## RenderEffect 与 Blur

`RenderEffect` 从 Android 12（API 31）公开。Android 17 的设置链路仍是 `View.setRenderEffect()` 把效果交给该 View 的 RenderNode，`RenderNode.setRenderEffect()` 通过 native 方法写入 image filter 属性。Blur 的工厂方法经 JNI 创建 Skia image filter；Android 13（API 33）又增加了 `createRuntimeShaderEffect()`，允许 RuntimeShader 读取输入内容。

这类效果通常需要离屏中间结果，再进行 blur、color filter、blend 或 shader 处理。成本由多项因素共同决定：

| 因素 | 为什么影响成本 |
|---|---|
| 处理区域 | 像素越多，中间资源与带宽越高 |
| blur 半径 | 采样范围和实现策略会变化 |
| 内容更新频率 | 输入变化会让缓存失效或重算 |
| effect chain | 可能融合，也可能增加中间 pass |
| 透明/裁剪 | 会改变 blend、边界与中间目标 |
| 后端与 GPU | GLES/Vulkan、驱动和 Skia 策略存在设备差异 |

RenderEffect 与手动 Hardware Layer 解决的问题不同。前者描述像素效果，后者请求缓存一个 View 子树；两者组合可能增加一层无收益的离屏工作。只有 trace/benchmark 显示属性动画缓存带来收益时，才额外启用 hardware layer。

优化顺序通常是缩小效果区域、降低持续更新时间、复用参数稳定的 effect、减少链条和在低性能设备提供降级。FrameTimeline 负责定位异常窗口帧；GPU counter、RenderThread、内存与 SurfaceFlinger composition 用来判断代价落在哪一侧。不存在统一的 blur radius 安全值。

Android 17 源码锚点：

- `frameworks/base/core/java/android/view/View.java`：View API 与属性失效；
- `frameworks/base/graphics/java/android/graphics/RenderNode.java`：RenderNode 设置入口；
- `frameworks/base/graphics/java/android/graphics/RenderEffect.java`：公开工厂 API；
- `frameworks/base/libs/hwui/jni/RenderEffect.cpp`：Skia filter 的 JNI 创建；
- `frameworks/base/libs/hwui/RenderProperties.h`：image filter 与 layer 属性。

---

## 线程优化：异步化也要守住依赖和资源

### 把工作移出主线程前，先画出依赖

适合后台执行的工作通常是磁盘/网络、解码、解析、diff、搜索和纯计算。能否异步还取决于 UI 是否必须等待结果。主线程发起任务后立刻 `get()`、锁等待或同步 Binder，只改变了线程名字，没有消除关键路径等待。

后台结果回到 UI 时要处理：

- 页面或 ViewHolder 已复用/销毁；
- 新请求已经取代旧请求；
- 结果触发大范围 requestLayout；
- 多个结果在同一帧集中投递；
- 任务无法取消，持续占用 CPU、I/O 和内存；
- 错误、超时与降级路径。

并发 CPU 任务会与 UI Thread、RenderThread 和 system_server 争夺 CPU。异步化验收必须同时看主线程 Runnable 延迟、整机 CPU、频率、thermal 和目标帧，不能只看某个方法从主线程消失。

### Binder

同步 Binder 会阻塞调用线程，直到服务端处理并返回。UI 路径上的包管理、ContentProvider、系统设置或自定义服务调用，需要结合客户端阻塞、binder transaction 和服务端线程一起分析。

常见策略：

- 把不随帧变化的数据提前获取并设定失效规则；
- 合并可批处理的请求，例如 ContentProvider 的批量操作；
- 避免在 bind、measure、draw、输入回调和动画进度回调中发起同步事务；
- 记录服务端排队和执行时间，防止只优化客户端封装；
- 对不需要返回值的 AIDL 方法评估 `oneway`。

`oneway` 让调用方不等待服务端方法执行完成，但事务仍需序列化、进入 Binder 队列并占用服务端资源。调用方拿不到同步返回值和服务端异常；高频 oneway 还可能造成积压。它属于接口语义选择，不能用作同步接口的机械替换。

### 线程池、优先级与回压

线程数没有“CPU 核心数”或“核心数两倍”的通用答案。合适的并发度取决于任务是 CPU、I/O 还是混合型，单任务内存、外部服务限流、设备大小核、前台状态和 thermal 都会影响结果。

线程池至少需要以下约束：

| 约束 | 目的 |
|---|---|
| 有界队列 | 防止突发请求无限占内存 |
| 明确拒绝/合并策略 | 保留新任务、关键任务或完整性 |
| 可取消 | 页面退出或新状态到来时停止旧任务 |
| 模块化命名 | 在 Perfetto 和 tombstone 中定位来源 |
| 合适优先级 | 后台吞吐不压住交互线程 |
| 统一监控 | 统计 active、queue、wait、run 和 rejection |
| 生命周期归属 | 防止任务持有失效 UI |

进程里线程很多不等于存在调度问题；要在卡顿区间看到后台 Running 与主线程 Runnable 等待、CPU 饱和或频繁迁核等对应证据。反过来，线程数不多也可能因一个高优先级 CPU 任务造成明显抢占。

### 分帧、延迟与空闲

把大任务拆成可取消的小单元，可以降低单次占用。调度点需要谨慎选择：

- `Choreographer.postFrameCallback()` 的回调运行在帧开始附近，回调工作会占用该帧预算；
- `Handler.post()` 只保证进入消息队列，没有 deadline 和空闲保证；
- IdleHandler 只在 Looper 空闲时运行，不能负责必须及时完成的任务；
- 后台线程适合无 UI 依赖的工作，结果投递仍要限流；
- 延迟初始化必须定义最迟完成时刻，避免把启动卡顿变成首次点击卡顿。

“拆成多帧”需要每段都有时间上限、进度状态和取消路径。若每帧都固定塞入一段昂贵工作，连续小卡会取代一次长卡。

---

## Compose：分别优化 composition、layout 与 draw

### 重组次数不是唯一指标

Compose 状态变化可能触发 recomposition，随后是否进入 layout/draw 取决于读取状态的位置和节点变化。某个 Composable 重组次数多但工作很轻，未必形成慢帧；低频重组也可能因子树大、Subcompose、图片或自定义绘制造成长帧。

优化时同时查看：

- 重组是否可跳过、范围有多大；
- 状态读取发生在 composition、layout 还是 draw；
- layout/draw 是否仍被高频触发；
- Lazy 列表的 compose/measure/prefetch；
- 首次运行的类加载、JIT 和 shader/pipeline；
- host App Window 的 FrameTimeline。

### Stable 与不可变性

Compose 编译器根据类型稳定性和参数比较决定跳过机会。现代编译器的 strong skipping 能让更多 restartable composable 获得跳过与 lambda memoization，但不能修复错误的数据模型。

`@Stable` 和 `@Immutable` 是开发者对编译器的契约。给内部可变且不通知 Compose 的对象加注解，会让 UI 漏更新。标准集合的稳定性、跨模块类型和编译器配置应通过 Compose compiler reports 确认；不可变集合或稳定包装应保持引用与内容语义一致。

优化目标是让状态变化只影响需要更新的子树，而非追求给所有类加 stable 注解。

### remember 与 derivedStateOf

`remember(keys...)` 缓存当前 composition 中的计算结果，key 变化时重算。key 漏项会返回陈旧结果，key 过宽会失去缓存收益。它不负责跨配置持久化，也不自动管理需要关闭的外部资源。

`derivedStateOf` 适合“输入变化频率高于 UI 判断变化频率”的场景，例如滚动位置每帧变化，而按钮只在越过阈值时切换可见性。它自身有观察和计算成本；对字符串拼接或与输入同频变化的简单结果，普通表达式或 `remember` 往往更直接。

能把高频状态读取延后到 layout/draw lambda 时，可减少 composition 失效范围。例如位移只影响布局或绘制时，优先选接收 lambda 的 modifier/API，并用 trace 验证阶段是否转移成功。

### Lazy 列表

LazyColumn/LazyRow 的性能依赖 item key、contentType、item 结构、数据稳定性和预取。稳定且唯一的 key 帮助状态与 item 身份对应；contentType 帮助复用兼容结构。key 冲突或可变对象原地修改会造成错误复用或漏更新。

嵌套 lazy 容器、SubcomposeLayout、每项 BoxWithConstraints 和同步图片工作都可能放大成本。预取实现与开关会随 Compose Foundation 版本演进，项目应记录依赖版本，用对应 release note 和 trace 解释行为，避免把某个版本的实验 flag 写成平台常量。

### Compose 验收

Macrobenchmark 应在 release-like、可比较的编译模式下运行，并覆盖首次启动与稳态交互。Baseline Profile 可改善关键路径的解释/JIT 成本，但不会消除业务 I/O、布局、GPU 或 display 延迟。

Layout Inspector 的重组计数适合定位候选点；Compose compiler metrics/reports 可解释稳定性；Perfetto 与 FrameTimeline 负责确认用户看到的帧。三者应对到同一交互，不能用“重组次数下降”单独宣布流畅度改善。

详见 [Compose 性能](./07-compose-performance.md) 与 [Compose 渲染管线](../ch18-rendering-pipelines/23-compose-rendering-pipeline.md)。

---

## 预取与预计算：提前支付也要记账

预取把未来可能需要的工作提前执行。它有收益必须同时满足：

1. 预测命中率足够高；
2. 提前工作没有挤压当前关键帧；
3. 结果在使用前没有失效；
4. CPU、内存、I/O、网络和 GPU 预算可接受；
5. 页面退出、方向改变或新请求到来时能够取消。

| 对象 | 可提前的工作 | 常见风险 |
|---|---|---|
| RecyclerView | create/bind 邻近 item | 主线程 deadline、池膨胀、图片请求放大 |
| Compose Lazy | compose/measure 邻近 item | 版本差异、无效预取、composition 竞争 |
| 图片 | 下载、解码、按目标尺寸缓存 | 内存、网络、错误尺寸、纹理上传仍在首显 |
| 文本 | 字形/段落相关预计算、PrecomputedText | span/字体/locale/宽度失效 |
| 路径/几何 | 纯计算、索引、采样点 | 数据版本与线程安全 |
| Shader/pipeline | 有支持时预热或缓存 | 驱动差异、缓存体积、首次设备成本 |

预计算结果需要显式 key，至少覆盖数据版本、尺寸、密度、字体比例、locale、主题和渲染参数中会影响结果的部分。缓存还要有容量和淘汰策略。命中率低的预取会让 benchmark 的目标场景变快，却让整机功耗和其他交互变差。

---

## Android 17 与内核边界

平台上界是 Android 17 / API 37，源码锚定 `android-17.0.0_r1`。RecyclerView、Compose、ConstraintLayout 与 WebView 是独立更新组件，优化报告要另记依赖版本，不能用平台 API 级别替代库版本。

内核侧以 `android17-6.18-2026-06_r6` 为锚点。线程优化可使用 sched wakeup/switch、CPU frequency/idle、thermal、PSI 和 dma-fence 等证据；设备上的 EAS/uclamp 策略、大小核拓扑、GPU/DPU 驱动与 HWC 行为仍由 SoC 和厂商实现决定。应用代码无法从一次 CPU 编号或频率采样推出通用的亲和性方案。

Android 17 AOSP 的 RenderThread 会设置显示相关优先级，标准源码没有给应用公开“绑定大核”的 RenderThread API。OEM 可能加入额外策略，结论需以目标 build 的源码与 trace 为准。

---

## 优化决策表

| 证据 | 优先动作 | 避免的动作 |
|---|---|---|
| measure/layout 长且重复 | 找 requestLayout 来源、缩小子树、稳定尺寸 | 仅按层数重写整个页面 |
| RV bind 长 | 移出 I/O/计算、payload、稳定图片尺寸 | 无上限增大 pool |
| RV create 长且频繁 | 降低 inflate 成本、核对 viewType/复用 | 假设预取一定能遮住 |
| UI 快、RenderThread/GPU 慢 | 减少像素、离屏、上传与复杂绘制 | 继续拆主线程方法 |
| blur 后 GPU/带宽上升 | 缩小区域、降低更新、提供降级 | 叠加 hardware layer 试运气 |
| 主线程同步 Binder 阻塞 | 缓存、批处理、移出帧路径、查服务端 | 把所有方法改为 oneway |
| 主线程 Runnable 等待长 | 查并发、优先级、CPU/thermal | 只增加后台线程 |
| Compose 重组范围大 | 收窄状态、修稳定性、延后读取 | 到处添加 @Stable |
| 预取命中低 | 缩小窗口、取消旧任务、限制缓存 | 继续提高预取数量 |
| App 帧按时、Display 帧晚 | 查 SF/HWC、fence、composition | 宣布应用优化完成 |

优化结束时，应保留修改前后的 trace、测试脚本、指标口径和版本信息。若收益只在单次运行出现，或代价转移到功耗、内存、启动和后台任务，当前方案还不能进入长期配置。

---

## 相关章节

- [卡顿定义](./01-jank-definition.md)
- [卡顿原因](./02-jank-causes.md)
- [分析方法](./03-jank-methodology.md)
- [典型场景](./04-typical-scenarios.md)
- [View 标准硬件渲染](../ch18-rendering-pipelines/02-android-view-standard.md)
- [软件与离屏渲染](../ch18-rendering-pipelines/03-android-view-software.md)
- [渲染管线分析方法](../ch18-rendering-pipelines/01-pipeline-overview.md#统一分析方法)

## 参考资料

- [Optimizing view hierarchies](https://developer.android.com/topic/performance/rendering/optimizing-view-hierarchies)
- [ConstraintLayout](https://developer.android.com/develop/ui/views/layout/constraint-layout)
- [ViewStub API](https://developer.android.com/reference/android/view/ViewStub)
- [RecyclerView performance](https://developer.android.com/topic/performance/vitals/render)
- [DiffUtil API](https://developer.android.com/reference/androidx/recyclerview/widget/DiffUtil)
- [ListAdapter API](https://developer.android.com/reference/androidx/recyclerview/widget/ListAdapter)
- [RecyclerView release notes](https://developer.android.com/jetpack/androidx/releases/recyclerview)
- [Hardware layers](https://developer.android.com/reference/android/view/View#LAYER_TYPE_HARDWARE)
- [RenderEffect API](https://developer.android.com/reference/android/graphics/RenderEffect)
- [Compose performance best practices](https://developer.android.com/develop/ui/compose/performance/bestpractices)
- [Compose stability fixes](https://developer.android.com/develop/ui/compose/performance/stability/fix)
- [Compose derivedStateOf](https://developer.android.com/develop/ui/compose/side-effects#derivedstateof)
- [AIDL](https://developer.android.com/develop/background-work/services/aidl)
- [AOSP Android 17 ViewStub](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewStub.java)
- [AOSP Android 17 View](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/View.java)
- [AOSP Android 17 RenderNode](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/RenderNode.java)
- [AOSP Android 17 RenderEffect](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/RenderEffect.java)
- [AOSP Android 17 RenderEffect JNI](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/jni/RenderEffect.cpp)
- [AOSP Android 17 RenderProperties](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/RenderProperties.h)
- [AOSP Android 17 RenderThread](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/RenderThread.cpp)
- [Android common kernel sched tracepoints](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/sched.h)
- [Android common kernel dma-fence](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)
