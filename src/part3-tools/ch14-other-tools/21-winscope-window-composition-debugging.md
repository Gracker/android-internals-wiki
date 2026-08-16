---

title: Winscope 与窗口/合成状态可视化调试
chapter: 14.21
section: 14.21
status: finalized
pipeline_stage: ready-to-publish
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: 2026-08-14
last_verified_against: android-17.0.0_r1 / Android 17 Winscope Perfetto data sources / AOSP Winscope docs updated 2026-06-17
confidence: high
sources: 
  - type: official
    path: "https://source.android.com/docs/core/graphics/winscope/overview"
  - type: official
    path: "https://source.android.com/docs/core/graphics/winscope/capture/winscope"
  - type: official
    path: "https://source.android.com/docs/core/graphics/winscope/capture/adb"
  - type: official
    path: "https://source.android.com/docs/core/graphics/winscope/analyze/sf"
  - type: official
    path: "https://source.android.com/docs/core/graphics/winscope/analyze/search"
  - type: official
    path: "https://source.android.com/docs/core/graphics/surfaceflinger-windowmanager"
  - type: official
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/WindowTracingPerfetto.java"
  - type: official
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Tracing/"
  - type: official
    path: "https://developer.android.com/agi/frame-trace/frame-profiler"
  - type: daily-info
    path: "intake/daily-info/2026-05-19.md"
tags: [winscope, surfaceflinger, windowmanager, perfetto, tracing, rendering, input]
related_chapters: ["2.6", "2.12", "2.13", "2.16", "3.1", "13.3", "13.9", "14.7"]
---

# 14.21 Winscope 与窗口/合成状态可视化调试

Winscope 是 AOSP 提供的系统状态录制、回放和分析工具。它把 WindowManager、SurfaceFlinger、Shell transition、`SurfaceControl.Transaction`、Input、IME、ProtoLog 和 ViewCapture 等数据放到同一时间轴。这里的 Shell transition 是系统窗口转场状态机；`SurfaceControl.Transaction` 是一组同时提交的 layer 属性修改；ProtoLog 是 Android 系统服务的结构化日志；ViewCapture 用于记录受支持系统窗口的 View 属性。

Winscope 适合回答这些问题：目标窗口是否进入可见状态，目标 layer 是否带 buffer，哪一层遮住了它，哪笔 transaction 修改了位置或透明度，转场参与者是否被合并或中止，触摸区域与焦点是否匹配。本文沿用 trace 与源码里的英文名：layer 是 SurfaceFlinger 管理的合成节点，buffer 是 Producer 提交的一帧像素数据，transaction 是一批状态修改，fence 是跨 CPU、GPU 和显示硬件协调读写完成时间的同步对象，present 表示一帧进入显示链路并交付给屏幕。

平台源码固定到 Android 17 / API 37 的 `android-17.0.0_r1`。涉及 fence 或显示驱动等待时，kernel 参考固定到 `android17-6.18-2026-06_r6`。Winscope 提供系统状态证据；CPU 调度、Binder（Android 跨进程调用机制）、RenderThread 渲染线程、GPU 工作、fence 等待和 present 时延继续由 Perfetto（系统 trace 采集与分析工具）、AGI（Android GPU Inspector）与设备侧图形轨迹解释。

## 1. 先明确 Winscope 记录了什么

WindowManager（WMS，窗口管理服务）和 SurfaceFlinger（SF，系统合成器）描述同一屏幕的不同层次。WindowManager 维护 Display（逻辑显示设备）、DisplayArea（显示区域）、Task、Activity、WindowToken（窗口身份与归属的令牌）和 WindowState 等容器，控制窗口生命周期、焦点、Insets、方向、转场与几何。Insets 表示状态栏、导航栏、IME 等占用或要求避让的屏幕边缘区域。

应用、解码器或相机等 Producer（画面生产者）通过 Surface 提交 buffer。WindowManager 与 WM Shell（负责系统窗口行为和动画的进程组件）用 `SurfaceControl.Transaction` 修改 layer 的位置、裁剪、层级和显隐。同一 transaction 内的修改以原子方式应用，也就是不会暴露只应用了一半属性的中间状态。SurfaceFlinger 将这些状态整理成当前时刻的 layer snapshot（图层状态快照），再由 CompositionEngine 选择合成策略，并通过 HWC（Hardware Composer，硬件合成接口）交给显示硬件。

Winscope 中的主要证据如下。

| 数据源 | 记录内容 | 能确认什么 | 仍需其它证据的问题 |
| --- | --- | --- | --- |
| WindowManager | WindowContainer 层级、bounds（矩形边界）、visibility、focus、orientation、Insets 等 | 窗口与 Task 是否处于预期逻辑状态 | 应用是否及时提交新像素，某段代码为何耗时 |
| SurfaceFlinger layers | 每个 snapshot 的 layer 层级、buffer、requested/calculated geometry（请求值/计算值）、可见区域、输入区域等 | layer 在该状态下能否参与显示，父层与遮挡关系是否正确 | buffer 内的像素是否正确，present 是否按目标时限完成 |
| SurfaceFlinger transactions | 初始状态与提交到 SF 的原子状态变化 | 哪个 PID/UID（进程/用户标识）、transaction id、layer id 改了属性 | 发起方为何晚提交，某次 GPU 工作何时结束 |
| Shell transitions | transition id、类型、flags、目标 leash/window、起止 bounds、开始/结束 transaction 与时间戳 | 启动、返回、旋转、分屏、PiP、Recents 的系统转场状态；leash 是转场期间承载动画的临时父 layer | App 内部动画每帧的绘制成本 |
| Input / IME | 输入事件链与输入法（Input Method Editor）状态 | 事件是否进入系统、在哪一段停住，IME 状态是否一致 | 应用回调内部为何阻塞 |
| ViewCapture | 支持该能力的系统窗口 View 属性 | SystemUI、Launcher 等受支持窗口的 View 位移、alpha（透明度）、可见性 | 任意第三方应用的完整 View 树 |
| Screen recording / screenshot | 用户能看到的画面 | 把状态时间点与视觉现象对齐 | 窗口树、layer 树或 transaction 的系统状态证据 |

Android 17 的 WMS Perfetto 路径由 `WindowTracingPerfetto` 注册 `android.windowmanager`，按配置把 `WindowManagerService` 状态序列化到 Perfetto。SurfaceFlinger 的 `LayerDataSource` 注册 `android.surfaceflinger.layers`，`TransactionDataSource` 注册 `android.surfaceflinger.transactions`。`LayerTracing` 的 active 模式直接写 snapshot；generated 模式根据 transaction ring buffer 重建 snapshot。ring buffer 是容量固定的循环缓冲区，写满后会覆盖最旧记录。

两种模式的状态来源不同。active layer trace 是运行时直接采集的状态序列，generated layer trace 是根据 transaction 记录重建的状态序列。排查本地一两帧错位时，可以优先采短时 active trace；需要在 bugreport 中保留较长历史时，generated bugreport 模式的运行开销较低。

## 2. 读 layer tree 前先判断出图拓扑

这里的“出图拓扑”指像素从哪里产生、经过哪些 Surface，最终对应哪些 SF layer。同一张画面在 SurfaceFlinger 中可能只有一个 App Window buffer layer，也可能包含宿主窗口和多个独立内容 layer。若跳过出图类型判断，很容易把“没找到视频 layer”误判成“视频没有提交”。

读 layer tree 前要先判断内容最终进入哪个 Surface，可分为四类。

### 标准 View / Compose 窗口

普通 View 与纯 Compose 内容由宿主 ViewRoot/HWUI 生成 App Window buffer。HWUI 是 Android 的硬件加速 UI 渲染器，主要通过 RenderThread 录制和提交绘制工作。SurfaceFlinger 通常只看到宿主窗口 layer；某个按钮、Compose node 或 TextureView 子区域不会各自成为可见 SF layer。Winscope 可以验证窗口与宿主 layer 的 bounds、buffer 和遮挡，无法从 SF layer tree 还原宿主内部每个 UI 节点。

### SurfaceView 与独立 Surface

SurfaceView 的主体内容走独立 buffer stream（连续提交的图像缓冲序列）。Android 17 的常见对象关系包括 SurfaceView container（承载几何和层级的容器层）、BLAST buffer child（接收内容 buffer 的子层）和按条件显示的背景 color layer。BLAST 是 Buffer Layer Asynchronous Surface Transaction 的缩写，它让 buffer 更新与 `SurfaceControl.Transaction` 协同提交。几何、crop、显隐和相对 Z 主要落在 container；frame number 与内容 buffer 落在 BLAST child。container 的状态进入 SF snapshot，只能证明几何或层级已经生效，不能证明 BLAST child 的新 buffer 也被同一个 display frame 采用。只选中 container 就宣布“有 buffer”会得出错误结论。

宿主 App Window 与 SurfaceView 内容各有自己的 buffer 更新和归还节奏。acquire fence 表示消费者何时可以读取 buffer，release fence 表示生产者何时可以安全复用它。黑屏或一帧错位时要分别检查：

- 宿主是否正确生成 hole-punch（在宿主窗口中留出透明区域，让下方 SurfaceView 内容露出）或覆盖 UI；
- container 的 requested/calculated geometry 是否一致；
- BLAST child 是否收到新 buffer，frame number 是否推进；
- parent、relative Z、crop、alpha 与 visible region 是否匹配；
- 宿主 geometry transaction 与内容 buffer 是否在预期 display frame 生效。

### TextureView

TextureView 的外部 buffer 先由应用进程内的 SurfaceTexture queue（纹理缓冲队列）交给 HWUI，再采样进宿主 App Window buffer。SurfaceFlinger 通常看不到独立的 TextureView 可见 layer。TextureView 黑屏时，Winscope 最多能证明宿主窗口是否提交及显示；外部 SurfaceTexture queue、宿主 RenderThread 采样和纹理内容要用应用、Perfetto 或 AGI 的证据检查。

### 多窗口、PiP、分屏与多 Display

分析顺序采用 `Display → Window/Task → SF layer/leash → 内容 Producer`。屏幕上两个 pane（并排区域）可能只是同一 Window 内的普通 View，也可能是两个 Task 或两个顶层 Window；layer 多也可能来自壁纸、系统栏、IME、dim layer（压暗背景的图层）或 transition leash。

多 Display 需要分开记录 `displayId`、目标窗口、可见 layer 集、刷新率、color mode 与 present 时间。一个进程可以在多个 Display 上有窗口；每个 Display 都有自己的帧与 present 时间线，不能把两个 Display 在相近时刻的 present 合成一帧来解释。

## 3. Android 17 源码对象与 Winscope 面板

Winscope 报告中的对象可以回到以下 Android 17 源码入口。

| 面板或字段 | Android 17 源码入口 | 阅读重点 |
| --- | --- | --- |
| WM hierarchy | `WindowContainer`、`DisplayContent`、`Task`、`ActivityRecord`、`WindowState` | 逻辑 parent、display、bounds、visibility、focus、Insets |
| WM Perfetto trace | `WindowTracingPerfetto`、`WindowTracingDataSource` | `LOG_LEVEL_*`、`LOG_FREQUENCY_*` 与 WMS dump 序列化 |
| Shell transition | `TransitionController`、system_server 与 WM Shell 各自的 `PerfettoTransitionTracer`、`TransitionDataSource` | sync/transition id、target leash layer id、start/finish transaction、handler（处理器）分派、merge（转场合并）、finish/abort（完成/中止） |
| Surface transaction | `SurfaceControl.Transaction`、`SurfaceComposerClient` | position、matrix、crop、alpha、layer、reparent、buffer 与 transaction id |
| SF runtime state | `RequestedLayerState`、`LayerLifecycleManager`、`LayerSnapshotBuilder` | transaction 状态怎样变成当前 snapshot，父层属性怎样影响计算结果 |
| SF layer trace | `LayerDataSource`、`LayerTracing` | active snapshot 与 generated snapshot 的来源 |
| SF transaction trace | `TransactionDataSource`、`TransactionTracing` | continuous ring buffer、active 逐笔写入、PID/UID/layer/vsync id |

固定 tag 的入口如下：

- [WMS `WindowTracingDataSource.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/WindowTracingDataSource.java)
- [WMS `PerfettoTransitionTracer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/PerfettoTransitionTracer.java)
- [WM Shell `PerfettoTransitionTracer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/WindowManager/Shell/src/com/android/wm/shell/transition/tracing/PerfettoTransitionTracer.java)
- [Framework `TransitionDataSource.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/tracing/transition/TransitionDataSource.java)
- [Framework `SurfaceControl.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/SurfaceControl.java)
- [SurfaceFlinger FrontEnd](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/FrontEnd/)
- [SurfaceFlinger tracing](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Tracing/)

这些源码能解释字段来源与状态流转。若还不熟悉 SF 状态模型，可先阅读 [SurfaceFlinger 与合成](../../part1-fundamentals/ch02-rendering/06-surfaceflinger.md) 和 [SurfaceFlinger FrontEnd 与 RequestedLayerState](../../part1-fundamentals/ch02-rendering/22-surfaceflinger-frontend-requestedlayerstate.md)。

某台设备的 HWC plane（显示控制器可直接扫描输出的硬件图层）分配、DPU（Display Processing Unit，显示处理器）限制、GPU driver 和 protected display path（受保护内容的安全显示链路）通常位于 vendor（设备厂商或芯片厂商）实现中，AOSP trace 只能提供公共框架侧线索。

## 4. 版本与采集入口

### Android 15—17

Android 15 起，Winscope traces 接入 Perfetto。每种 trace 都是独立 data source（Perfetto 可单独启停的数据采集模块），可以在一次 tracing session 中组合：

- `android.windowmanager`
- `android.protolog`
- `android.input.inputevent`
- `android.surfaceflinger.layers`
- `android.surfaceflinger.transactions`
- `com.android.wm.shell.transition`
- `android.inputmethod`
- `android.viewcapture`

Android 17 继续沿用这些 data source。平台 tag 变化不代表 viewer 字段在所有厂商构建上都完整；产品裁剪、权限和 trace flags 都会影响数据。

### Android 14 及更早版本

旧版本使用各自的命令和 `/data/misc/wmtrace` 文件，例如 `wm tracing start/stop`。这些 trace 可以继续用 Winscope 加载，但配置名、字段和采集方式应按目标系统版本解释。`RequestedLayerState` 是 SF FrontEnd 接收的 layer 请求状态，`LayerSnapshot` 是计算父子继承、裁剪和可见性后的快照；Android 17 的这套对象模型不能直接套到旧实现的每个内部对象。

### 网页端与命令行

Winscope Web UI 支持 Winscope Proxy 和 Web Device Proxy：前者在本机运行代理并通过 adb 连接设备，后者由浏览器直接连接设备。Winscope Proxy 要求 Python 3.10+ 与 adb；官方文档截至 2026-06-17 仍标明 Web Device Proxy 不支持 macOS。命令行采集面向 `userdebug`/`eng` 调试构建，并要求 `adb root` 取得 root adb daemon；普通量产 user build 不应假定这些命令可用。

## 5. 一份短时、可复现的采集配置

下面的配置面向 15 秒本地窗口转场复现，采集 WM frame snapshot、SF active layer snapshot、SF active transaction 和 Shell transition。`TRACE_FLAG_BUFFERS` 是 SF layer trace 的采集开关，用于捕获没有几何变化时的 buffer 更新；若缺少它，画面内容更新可能不会产生新的 layer snapshot。

```bash
adb root
adb shell perfetto \
  -c - --txt \
  -o /data/misc/perfetto-traces/winscope_window_debug.perfetto-trace <<'EOF'
duration_ms: 15000
unique_session_name: "winscope_window_sf_debug"
buffers: {
  size_kb: 65536
  fill_policy: RING_BUFFER
}
data_sources: {
  config {
    name: "android.windowmanager"
    windowmanager_config: {
      log_level: LOG_LEVEL_DEBUG
      log_frequency: LOG_FREQUENCY_FRAME
    }
  }
}
data_sources: {
  config {
    name: "android.surfaceflinger.layers"
    surfaceflinger_layers_config: {
      mode: MODE_ACTIVE
      trace_flags: TRACE_FLAG_INPUT
      trace_flags: TRACE_FLAG_COMPOSITION
      trace_flags: TRACE_FLAG_BUFFERS
    }
  }
}
data_sources: {
  config {
    name: "android.surfaceflinger.transactions"
    surfaceflinger_transactions_config: {
      mode: MODE_ACTIVE
    }
  }
}
data_sources: {
  config {
    name: "com.android.wm.shell.transition"
  }
}
EOF
adb pull /data/misc/perfetto-traces/winscope_window_debug.perfetto-trace .
```

这段配置启动后等待复现，15 秒结束时把 trace 写到设备文件，再由最后一行拉回当前目录。`MODE_ACTIVE` 会写入采集期间的初始状态和后续变化，适合短时稳定复现；SF layer active 模式计算开销较高，不宜拿来长时间测量性能。问题只涉及当前静态状态时使用 dump（单个状态快照）；需要在 bugreport 中保留故障前历史时，可评估 `MODE_GENERATED_BUGREPORT_ONLY` 和 transaction continuous ring buffer。continuous 模式持续维护循环缓冲区，在 flush（请求输出当前缓冲内容）或 bugreport 时输出其中记录。

默认配置没有启用 `TRACE_FLAG_EXTRA`、`TRACE_FLAG_HWC`、WindowManager verbose、ProtoLog stacktrace（调用栈）和全量 input event。`TRACE_FLAG_EXTRA` 增加额外 layer 元数据，`TRACE_FLAG_HWC` 增加非结构化的 HWC 信息；这些选项会明显增加内存、运行开销或隐私风险。只有当前问题需要对应字段时才在短时本地 trace 中启用。

WindowManager 的 `LOG_FREQUENCY_FRAME` 在 WMS 提交一帧窗口状态时记录快照；纯显示刷新不包含新的 WMS frame commit，因此不会自动增加记录。`LOG_FREQUENCY_TRANSACTION` 在每次 WMS transaction commit 时记录快照，可能保留同一显示周期内的中间状态，适合追一帧错位，但数据量和开销通常更高。默认 `LOG_LEVEL_DEBUG + LOG_FREQUENCY_FRAME` 已覆盖多数窗口问题。

## 6. 从录像到窗口、layer 与 transaction

一轮分析按七个检查点进行。

### 6.1 锁定 Display 与时间点

记录异常发生的 `displayId`（逻辑显示设备编号）和时间戳。Screen recording 可与 trace 同采，支持多 Display 的前提是设备 `screenrecord` 版本达到 1.4；旧版本只记录单 Display。视频帧负责定位现象，state snapshot 才描述当时的窗口与 layer 状态，两者不能互相替代。

### 6.2 在 WindowManager 找逻辑对象

用 title、token、parent token、Task、Activity、WindowState、display、bounds、`is_visible` 与 focused window 找到目标。token 是对象身份标识，parent token 用于确认父子归属；relayout 是应用与 WMS 重新协商窗口几何和 Surface 状态的过程。WM 中不可见时，继续检查 Activity/Task 状态、transition、Insets、relayout 和焦点分配。WM 中可见只说明窗口管理状态满足条件，尚未证明 SF 有可显示 buffer。

### 6.3 按出图类型找 SF 对象

标准 View/Compose 或 TextureView 页面从宿主 App Window layer 开始。SurfaceView、视频、相机、游戏或自研 EGL/Vulkan 输出要继续寻找独立 content/BLAST layer。EGL 是连接 OpenGL ES 等渲染 API 与窗口 Surface 的接口。PiP（Picture-in-Picture，画中画）、分屏和桌面窗口还要记录 task leash、transition leash、caption（窗口标题栏）、dim、wallpaper、IME 和 SystemUI layer。

layer 名称只是检索入口。确认对象时结合 owner PID/UID、layer id、parent、buffer、frame number（该 buffer 流中的帧序号）、bounds 和 transaction，避免把同名旧 layer 或 container 当成当前内容 layer。

### 6.4 解释 SurfaceFlinger 可见性

Winscope 的 rects view（矩形视图）按 layer 的 bounds、z-order（前后层级）、opacity（是否不透明）、relative Z（相对另一 layer 的层级）与圆角绘制屏幕占位。SF viewer 的 `V` chip 是可见性标记，表示该 layer 经 SF 计算后可见。Android 15 起旧的 HWC/GPU hierarchy chips 已弃用；不要依赖旧 chip 判断当前 composition path（由 HWC 还是 GPU 完成合成）。

可见性检查包含：

- `HIDDEN`、父层隐藏、没有 buffer、visible region 为空等 invisibility reason（不可见原因）；
- `Occluded`：上方 opaque layer 完全遮挡；
- `Partially Occluded`：上方 opaque layer 遮挡一部分；
- `Covered`：上方非 opaque layer 覆盖，底层仍可能透出；
- buffer 是否存在、frame number 是否更新、destination frame（buffer 映射到屏幕的目标矩形）是否正确；
- input touchable region（可接收触摸的区域）和 focus 属性是否匹配。

SF 中 layer `visible` 也不保证 buffer 像素正确。应用可能提交一张纯黑帧，decoder（解码器）或 shader（GPU 着色程序）也可能写出错误内容；Winscope 能证明该 buffer layer 参与了当前状态，像素内容仍需 Producer 或 GPU 侧证据。

### 6.5 对比 requested 与 calculated

Requested geometry/effects 是该 layer 提交的几何与效果请求；Calculated 是叠加父层继承、坐标变换和裁剪后用于当前合成的值。requested 正确、calculated 错误时，检查 parent、leash、crop、relative Z、transform 与 display 变换；requested 已经错误时，沿 transaction 找提交者。

### 6.6 回到 transaction 与 transition

SurfaceFlinger transaction trace 提供 transaction id、PID、UID、layer id 与状态变化。`vsync_id` 位于一次 SF commit 形成的 trace entry 上，同一 entry 内的 transactions 共用它；它不表示每笔客户端 transaction 各自的提交时间。看到 bounds、alpha、crop 或 reparent（更换父 layer）异常后，搜索对应 transaction，确认它来自 App、`system_server`（承载 WMS 等系统服务的进程）、SystemUI/WM Shell 还是其它进程。

Android 17 有两份同名的 `PerfettoTransitionTracer`。system_server 中的 `com.android.server.wm.PerfettoTransitionTracer` 记录 transition id、create/send/finish/abort 时间、start/finish transaction id、目标 leash layer id、window id、起止 display/rotation/bounds；WM Shell 中的 `com.android.wm.shell.transition.tracing.PerfettoTransitionTracer` 记录 handler 分派、merge request（合并请求）、merged 和 aborted。两者都通过 `TransitionDataSource` 注册 `com.android.wm.shell.transition`。

通过同一 transition id 可以把 Shell transition 与 SF transaction、WM container、目标 layer 对齐。transition 已 finish 只说明系统状态机结束，仍需检查目标 layer 是否显示正确。

### 6.7 时序问题转到 Perfetto

Winscope 能指出“哪一个状态从哪一帧开始错误”。若状态序列正确但出现卡顿，进入 Perfetto 检查 UI thread、RenderThread、Binder、SF、FrameTimeline、HWC/DisplayHAL、GPU 与 I/O。FrameTimeline 把应用帧和 SurfaceFlinger 帧的预期时间、实际时间关联起来；DisplayHAL 是系统访问显示硬件的接口层。

若 buffer 到达、latch（SF 选取 buffer 进入本次合成）或 present 受 fence 限制，再核对指定 kernel tag 的 [`sync_file.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c) 和 [`dma-fence.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c) 语义，并结合设备 vendor 驱动轨迹。AOSP kernel 文件解释公共同步语义，具体等待来源仍取决于设备驱动。

## 7. 典型问题的证据顺序

### 白屏或黑屏

1. 在录像中锁定异常帧与 Display。
2. 在 WM 中确认目标窗口、starting window（应用内容就绪前的临时启动窗口）、splash 与上层系统窗口的状态。
3. 按出图类型找到宿主与独立内容 layer。
4. 检查 buffer、frame number、visible region、occlusion、parent、crop、alpha 和 z-order。
5. 有 layer 且有 buffer 时，区分“上层遮挡”“提交黑色像素”“protected/secure 内容因安全策略无法截图”。
6. 几何/显隐错误沿 transaction 追提交者；buffer 迟到转到 BLAST、BufferQueue（连接 Producer 与 Consumer 的缓冲队列）和 Perfetto；像素内容错误转到 HWUI、MediaCodec、Camera、GL/Vulkan 或 AGI。

官方 Winscope flicker 样例中，Activity layer 被设为 visible/opaque，但 visible region 为空；上方 opaque `NotificationShade` 成为当前可见内容。该案例说明 WM visible 与 SF 最终可见结果需要分开验证。

### 首帧与 starting window

把 Activity/Window、starting window、splash layer、App Window buffer 和 transition 放在同一时间轴。splash 是 starting window 中显示的启动画面。WM Activity visible 的时刻、App 第一块 buffer 进入 SF 的时刻、splash 移除 transaction 和用户看到首帧的时刻可能不同。App layer 没有 buffer 时进入启动/BLAST 路径；buffer 已存在但 splash 过早移除时检查 transition 与 starting-window policy（启动窗口的显示和移除策略）。

### SurfaceView 一帧错位

同时选择宿主 App Window、SurfaceView container 和 BLAST child。对比 container geometry transaction、宿主 draw transaction、BLAST child frame number、buffer transaction 与目标 display snapshot。container 已移动而 child 沿用旧 buffer 不一定表示异常，因为几何和内容来自不同状态源。只有同步组、同一 `SurfaceControl.Transaction`，或按指定 frame number 把几何 transaction 合入下一次 buffer transaction 时，才能要求两类更新同时生效。若 crop、relative Z 或内容/几何持续错位，继续查 `mergeWithNextTransaction()`、`applyTransactionOnDraw()`、`applyTransactionToFrame()` 等同步入口，以及 Producer 的提交节奏；其中 `applyTransactionToFrame()` 在 SurfaceView 持续出帧时不保证精确对应哪一帧。

### TextureView 黑屏

SF 中找不到独立 TextureView layer 属于正常拓扑。确认宿主 App Window 是否有新 buffer 并可见；随后检查 SurfaceTexture 的 frame-available 通知、HWUI texture acquire（取得待采样纹理）、宿主 RenderThread 和外部 Producer。只在 Winscope 里反复搜索“TextureView layer”不会得到有效证据。

### 转场、旋转、分屏与 PiP

从 transition id 进入目标转场，记录参与 WindowContainer、leash layer、起止 bounds/display/rotation、start/finish transaction 和 played/merged/aborted（已播放/已合并/已中止）状态。随后逐帧检查 child buffer 与 leash geometry。位置跳变可能来自 WCT（`WindowContainerTransaction`，批量修改窗口容器的事务）、WM sync（协调多项窗口更新同步提交）、Shell leash 动画、应用 resize buffer 迟到或 SF parent 变换，录像本身无法区分这些来源。

### 点击无响应

SF `TRACE_FLAG_INPUT` 提供 layer 输入窗口属性、touchable region 和 focus 线索；它不记录完整事件派发。需要事件链时增加 `android.input.inputevent`。`TRACE_MODE_TRACE_ALL` 是全量输入事件模式，会记录系统处理的全部输入事件，只能用于本地设备或测试；现场/线上采集必须配置隐私规则。

分析顺序是触摸坐标对应的 Display → 顶层可触摸窗口/layer → focused window → input target → InputDispatcher（系统输入事件分发器）→ 应用回调。遮挡 layer 能显示不代表它接收输入，视觉 z-order 与 input region 也可能不同。

## 8. Search viewer 与 Perfetto SQL

Winscope Search viewer 借助 Perfetto Trace Processor 提供 `sf_layer_search`、`transactions_search`、`transitions_search`、`viewcapture_search`、`wm_search` 等 helper view（预先整理好的 SQL 视图）。`property` 保留 repeated field（proto 中可重复出现、类似数组的字段）的下标，`flat_property` 忽略下标；`value` 与 `previous_value` 使用字符串表示，布尔值写成 `0`/`1`。

下面的查询列出目标 App layer 被计算为可见的状态。它用于定位候选时间点：

```sql
SELECT DISTINCT ts, layer_id, layer_name
FROM sf_layer_search
WHERE layer_name LIKE '%com.example%'
  AND is_visible = 1
ORDER BY ts;
```

结果中的 `ts` 是 trace 时间戳，可直接映射到 Winscope 时间轴。可见记录很多时，再加 `layer_id` 过滤当前实例，避免混入旧 layer 或同包其它窗口。

下面的查询寻找某个窗口容器可见状态。它验证 WM 逻辑可见与 SF layer 可见是否出现在同一时间区间：

```sql
SELECT DISTINCT ts, title, token, parent_token
FROM wm_search
WHERE title LIKE '%DetailActivity%'
  AND is_visible = 1
ORDER BY ts;
```

若 WM 先可见而 SF 后可见，继续查 App buffer、starting window 与 transition；两边时间不能直接当成同一阶段的重复数据。

下面的查询使用官方 helper view 字段，寻找把 layer x 改为 `-54.0` 的 transaction：

```sql
SELECT ts, transaction_id, value
FROM transactions_search
WHERE flat_property = 'transactions.layer_changes.x'
  AND value = '-54.0'
ORDER BY ts;
```

拿到 transaction id 后，结合底层表 `android_surfaceflinger_transaction` 的 PID/UID/layer id 和 ProtoLog 定位提交方。若查询依赖数值比较，先把字符串显式转换成数值类型，避免按字典序比较。

## 9. Dump、bugreport 与 trace

静态的“当前点不到”或“当前谁盖住谁”可用 WM/SF proto dump。proto dump 是把服务当前状态序列化为 Protocol Buffers 二进制快照。下面两条命令分别保存 WindowManager 与 SurfaceFlinger 快照，供 Winscope 加载。

```bash
adb exec-out dumpsys window --proto > window_dump.winscope
adb exec-out dumpsys SurfaceFlinger --proto > surfaceflinger_dump.winscope
```

命令执行成功后，当前目录会得到两个 `.winscope` 文件。dump 没有前后状态，不能证明闪屏、转场顺序或一帧错位。连续 trace 受开销和 ring buffer 容量影响；bugreport 是 Android 的综合故障报告，适合保留故障前的 ring-buffer 历史，但包含的系统信息更多，隐私等级也更高。三种产物应按问题选择。

## 10. 采集成本、隐私与保真度

- SF layer `MODE_ACTIVE` 会在 layer 状态变化时直接采集 snapshot，计算开销高；长时间性能测试应使用开销更低的模式。
- `TRACE_FLAG_BUFFERS` 记录每次 buffer 变化；缺少这个 flag 时，默认只在几何变化时生成新 SF 状态，可能看不到静止几何下的 frame 推进。
- `TRACE_FLAG_EXTRA` 与 `TRACE_FLAG_HWC` 数据量大。HWC flag 提供未结构化厂商元数据，不能保证跨设备字段一致。
- WindowManager transaction 频率能捕获一帧内中间状态，开销高于 frame 频率。
- ProtoLog stacktrace 会为日志附加调用栈，采集速度慢，适合短时本地复现。
- Input、IME、screen recording、ViewCapture、ProtoLog 和 bugreport 可能包含操作轨迹、文本、窗口标题、应用标识与画面。采集、传输、存储和分享都要按敏感诊断数据管理。
- ring buffer 太小会覆盖故障前状态；过大又增加内存压力。短时确定性复现优先于十几分钟全量采集。
- protected/secure 内容使用受保护的 buffer 与显示路径，可能无法进入 screen recording 或截图。黑色视频区域不能单凭录像判断 Producer 没出帧。

## 11. Winscope、Perfetto、AGI 与 dumpsys 的分工

| 工具 | 主要证据 | 适合的判断 |
| --- | --- | --- |
| Winscope | WM/SF/transition/transaction/input 状态序列 | 对象是谁，窗口与 layer 状态何时偏离预期 |
| Perfetto | 调度、slice（持续时间区间）、counter（数值序列）、Binder、FrameTimeline、ftrace（内核事件）、部分图形数据源 | 哪个阶段迟到，CPU/锁/Binder/fence/I/O 等待在哪里 |
| AGI | GPU counter 与 System Profiler；Vulkan Frame Profiler；经 ANGLE 转译为 Vulkan 后的 OpenGL ES 帧 | GPU 工作量与计数器、Vulkan 调用，或明确走 ANGLE 转译路径的 OpenGL ES 帧；不能把它当作任意原生 GL 调用的通用证据 |
| `dumpsys` | 当前时刻的文本/proto 状态 | 快速复核静态现场或脚本化取证 |

“画面状态错误”优先用 Winscope 定位对象与状态；“状态正确但画面迟到”转到 Perfetto；“buffer 内像素或 GPU 命令错误”根据图形 API 和采集路径选择 AGI 或对应 Producer 工具。复杂问题通常需要在同一时间点组合多类证据。

## 12. 排查清单

1. 异常发生在哪个 `displayId` 和时间点？
2. 目标是一个 Window、一个 SF layer、一个 transition leash，还是宿主内部 UI 节点？
3. 页面属于标准窗口、SurfaceView、TextureView、混合出图还是多窗口？
4. WM 逻辑可见与 SF 计算可见是否分别确认？
5. 目标 SF 对象是 container、buffer layer、background、leash 还是旧实例？
6. requested 与 calculated geometry 差异来自哪个 parent？
7. frame number、buffer、visible region、occlusion、crop、alpha 与 relative Z 是否一致？
8. 修改状态的 transaction id、PID/UID、layer id 与 `vsync_id` 是什么？
9. transition id、目标 window/layer、start/finish transaction 和 finish/abort 状态是否匹配？
10. 现象属于状态错误、buffer 迟到、像素错误还是 present 迟到？
11. trace 模式和 flags 是否足以观察该变化，又是否改变了被测性能？
12. Input、录像、bugreport 与 ProtoLog 是否按敏感数据处理？

## 参考资料

- [Winscope overview](https://source.android.com/docs/core/graphics/winscope/overview)
- [Capture traces with Winscope](https://source.android.com/docs/core/graphics/winscope/capture/winscope)
- [Capture Winscope traces with adb](https://source.android.com/docs/core/graphics/winscope/capture/adb)
- [Winscope SurfaceFlinger viewer](https://source.android.com/docs/core/graphics/winscope/analyze/sf)
- [Winscope trace search](https://source.android.com/docs/core/graphics/winscope/analyze/search)
- [SurfaceFlinger and WindowManager](https://source.android.com/docs/core/graphics/surfaceflinger-windowmanager)
- [AOSP WMS tracing, `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/WindowTracingPerfetto.java)
- [AOSP transition tracing, `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/PerfettoTransitionTracer.java)
- [AOSP WM Shell transition tracing, `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/WindowManager/Shell/src/com/android/wm/shell/transition/tracing/PerfettoTransitionTracer.java)
- [AOSP `SurfaceView.java`, `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/SurfaceView.java)
- [AOSP `TextureView.java`, `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/TextureView.java)
- [AOSP SurfaceFlinger tracing, `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Tracing/)
- [AOSP SurfaceFlinger FrontEnd, `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/FrontEnd/)
- [Kernel sync file, `android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c)
- [AGI Frame Profiler](https://developer.android.com/agi/frame-trace/frame-profiler)
