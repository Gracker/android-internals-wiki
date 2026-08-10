---
title: "DisplayManagerService：显示器发现、拓扑、功耗与渲染交接"
chapter: "2.30"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [display, dms, multi-display, foldable, surfaceflinger, syncroot]
related_chapters: ["2.3", "2.6", "2.20", "2.23", "2.28", "18.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-24"
gap_source: "DeepResearch素材驱动"
drafted_date: "2026-06-24"
last_verified: "2026-07-25"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: official
    path: "https://source.android.com/docs/core/display/multi_display"
  - type: official
    path: "https://source.android.com/docs/core/display/multi_display/displays"
  - type: official
    path: "https://developer.android.com/reference/android/hardware/display/DisplayTopology"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/display/DisplayManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/display/DisplayAdapter.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/display/DisplayDeviceRepository.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/display/LogicalDisplayMapper.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/display/DisplayTopologyCoordinator.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/display/LocalDisplayAdapter.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/display/VirtualDisplayAdapter.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/display/DisplayPowerController.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/DisplayEventReceiver.java"
  - type: aosp
    path: "frameworks/base/core/java/android/hardware/display/DisplayManager.java"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/EventThread.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp"
---

# 2.30 DisplayManagerService：显示器发现、拓扑、功耗与渲染交接

`DisplayManagerService`（DMS）管理显示器的发现、身份、能力、逻辑映射、状态、功耗和对外事件。它会把显示器配置交给 WindowManager、InputManager 和 SurfaceFlinger，但不负责应用逐帧绘制，也不直接决定某个图层采用 HWC 设备合成还是客户端合成。

分析 DMS 时，最容易出错的是把几套对象混成一棵树。Android 17 至少要区分：

| 对象 | 所属模块 | 主要职责 |
|---|---|---|
| physical display id / display token | SurfaceFlinger | 标识物理 Display，连接 HWC Display 与 SF Display |
| `DisplayDevice` | DMS / `DisplayAdapter` | 封装本地、无线、虚拟或叠加显示设备及其能力 |
| `LogicalDisplay` | DMS / `LogicalDisplayMapper` | 提供框架使用的逻辑显示器 ID、配置、启用状态与主设备 |
| `DisplayGroup` | DMS | 按显示组 ID 组织一组 LogicalDisplay；它不是屏幕相对位置图 |
| `DisplayTopology` | DMS / InputManager | 描述可扩展显示器的相对位置，服务鼠标跨屏与拓扑持久化 |
| `DisplayContent` | WindowManager | 按 Display 管理窗口、Task、DisplayArea、焦点、Insets 与 policy |
| SF Display / CompositionEngine Output | SurfaceFlinger | 为目标 Display 构造可见 layer 集合，执行合成并取得 present fence |

这些对象通常有关联，但并非严格一一对应。例如，镜像图层可以出现在多个输出中；虚拟显示器有自己的 SF 令牌，却未必承载可启动任意 Activity 的 WMS `DisplayContent`；`DisplayTopology` 也不会替代 `LogicalDisplayMapper` 的设备状态布局。

以下分析以 Android 17 / API 37 / `android-17.0.0_r1` 为准。涉及内核栅栏、调度或显示驱动时，公共语义以 `android17-6.18-2026-06_r6` 为准；物理热插拔、硬件平面分配、带宽和面板时序仍需核对设备厂商 HAL 与驱动。

## 1. 服务启动与默认显示器

### 1.1 `onStart()` 先加载持久化状态

Android 17 的 `DisplayManagerService.onStart()` 先在 `mSyncRoot` 下加载 `PersistentDataStore` 与稳定显示配置，再向 DMS Handler 投递 `MSG_REGISTER_DEFAULT_DISPLAY_ADAPTERS`。随后发布：

- `IDisplayManager` Binder service；
- `DisplayManagerInternal` local service。

默认适配器不会在 `system_server` 启动调用栈中直接注册。DMS Handler 处理消息后，在 `mSyncRoot` 下注册：

1. `LocalDisplayAdapter`；
2. `VirtualDisplayAdapter`。

`OverlayDisplayAdapter` 和 `WifiDisplayAdapter` 属于附加适配器。它们在 `systemReady()` 之后异步注册，安全模式下会跳过；Wi-Fi Display 还受资源和调试属性控制。因此，Android 17 不会固定启用四种适配器。

启动主线如下：

```mermaid
flowchart TD
    A["SystemServer 启动 DisplayManagerService"] --> B["DMS.onStart"]
    B --> C["mSyncRoot 下加载 PersistentDataStore"]
    C --> D["post MSG_REGISTER_DEFAULT_DISPLAY_ADAPTERS"]
    B --> E["发布 Binder 与 LocalService"]
    D --> F["DisplayThread 注册 LocalDisplayAdapter"]
    D --> G["DisplayThread 注册 VirtualDisplayAdapter"]
    F --> H["向 SurfaceFlinger 查询物理显示器 ID 与令牌"]
    H --> I["DisplayDeviceRepository"]
    I --> J["LogicalDisplayMapper 创建默认 LogicalDisplay"]
    J --> K["唤醒默认显示器等待者"]
```

图中的物理显示令牌由 SurfaceFlinger 持有并返回给框架。DMS 不会为本地物理屏重新创建令牌。

### 1.2 等待 phase 与超时值

SystemService 启动会在 `PHASE_WAIT_FOR_DEFAULT_DISPLAY` 调用 DMS。Android 17 的等待条件是：

```text
default LogicalDisplay 已创建
AND
VirtualDisplayAdapter 已创建
```

等待发生在 `mSyncRoot.wait(delay)`，会释放 Java monitor，让 DisplayThread 能继续完成 adapter 事件处理。默认超时常量为 10000 ms，并乘以 `Build.HW_TIMEOUT_MULTIPLIER`；超时后抛出 `RuntimeException`，不是无限等待。

Android 17 在 `PHASE_WAIT_FOR_DEFAULT_DISPLAY` 等待，默认超时为 10 秒，而非 `PHASE_LOCKED_BOOT_COMPLETED` 或 5 秒。排查开机卡住时，应对齐：

- `MSG_REGISTER_DEFAULT_DISPLAY_ADAPTERS` 是否执行；
- `LocalDisplayAdapter.registerLocked()` 是否从 SF 得到 physical display id/token；
- `DISPLAY_DEVICE_EVENT_ADDED` 是否到达 repository；
- `LogicalDisplayMapper` 是否生成 `DEFAULT_DISPLAY`；
- `VirtualDisplayAdapter` 是否成功创建。

`PHASE_BOOT_COMPLETED` 的职责不同：DMS 通知 DisplayPowerController、DisplayModeDirector、LogicalDisplayMapper、外接屏策略等组件 boot completed，不负责首次默认屏发现。

## 2. 物理显示器的发现、变更与移除

### 2.1 本地屏事件从 SurfaceFlinger 进入

`LocalDisplayAdapter.registerLocked()` 创建 `DisplayEventReceiver`，并先枚举 `DisplayControl.getPhysicalDisplayIds()`。对每个 id，它从 SurfaceFlinger 查询：

- physical display token；
- `StaticDisplayInfo`；
- `DynamicDisplayInfo`；
- `DesiredDisplayModeSpecs`。

如果此前没有相同的物理显示器 ID，适配器会创建 `LocalDisplayDevice` 并发送 `DISPLAY_DEVICE_EVENT_ADDED`；已有设备的能力或状态变化时发送 `CHANGED`；热插拔断开时发送 `REMOVED`。

完整事件流如下：

```mermaid
flowchart TD
    A["HWC / vendor display hotplug"] --> B["SurfaceFlinger 更新物理显示器"]
    B --> C["SF EventThread 发送 hotplug event"]
    C --> D["LocalDisplayAdapter 的 DisplayEventReceiver"]
    D --> E["tryConnectDisplayLocked / tryDisconnectDisplayLocked"]
    E --> F["post DISPLAY_DEVICE_EVENT_* 到 DisplayThread"]
    F --> G["DisplayDeviceRepository 在 mSyncRoot 下更新设备集合"]
    G --> H["LogicalDisplayMapper 更新 LogicalDisplay / DisplayGroup"]
    H --> I["DMS LogicalDisplayListener"]
    I --> J["Handler 分发显示器添加 / 变更 / 移除回调"]
    I --> K["scheduleTraversalLocked"]
    K --> L["WindowManager 请求一次显示遍历"]
```

`DisplayAdapter.sendDisplayDeviceEventLocked()` 使用 handler post，把事件从适配器当前回调栈移到 DisplayThread。进入 `DisplayDeviceRepository` 后，设备集合、LogicalDisplay 映射和 DMS 内部监听器仍在同一个 `mSyncRoot` 下更新。

### 2.2 ADDED、CHANGED、REMOVED 的工作不同

`DisplayDeviceRepository` 对三类事件的处理边界是：

- `ADDED`：验证设备未重复，加入仓库，再通知 `LogicalDisplayMapper`；
- `CHANGED`：比较新旧 `DisplayDeviceInfo`，计算 mode、state、rotation、color、timing 等 diff，应用 pending info 后通知 mapper；
- `REMOVED`：从仓库删除设备，再通知映射器。

LogicalDisplay 层还有 `CONNECTED`、`DISCONNECTED`、`ADDED`、`REMOVED`、`BASIC_CHANGED`、`STATE_CHANGED` 等更细的事件掩码。设备断开、LogicalDisplay 停用和框架对外移除不会同时发生。DMS 按预处理和后处理顺序更新资源、DisplayPowerController、拓扑、缓存、外接屏策略与回调，不能只凭一条 `onDisplayRemoved()` 推断所有资源已经释放。

### 2.3 物理热插拔不会重建全局图层树

物理显示器接入后：

1. SurfaceFlinger 已拥有对应的物理显示令牌；
2. DMS 建立 DisplayDevice/LogicalDisplay；
3. WMS 再建立或更新该显示器的 `DisplayContent` 与策略；
4. SF 为该显示器准备输出；
5. 窗口被放到该显示器后，相关 SurfaceControl 才进入目标可见图层集合。

这是一组跨服务状态变化，不是删除后重建 SurfaceFlinger 的整棵全局 layer hierarchy。已有 layer 是否镜像、reparent 或只出现在原 Display，取决于 WMS/Shell transaction、Display projection 与 SF Output 选择。

## 3. `mSyncRoot` 单锁模型

### 3.1 为什么 DMS 使用一把锁

`mSyncRoot` 保护整个 DMS 共享模型，包括：

- DisplayAdapter 与 DisplayDevice repository；
- LogicalDisplay、DisplayGroup、DeviceState Layout；
- Display state、brightness 与 power controller 索引；
- callback registry；
- 视口与待处理遍历；
- DisplayTopology 的当前副本与 id 映射。

一次 hotplug 需要原子地完成“设备集合 → LogicalDisplay → group/layout → power/controller → event”的关系更新。随意拆成多把锁，会引入设备已删除但 LogicalDisplay 仍可见、group 与 topology 不一致、以及与 WMS global lock 反向获取等问题。

DMS 源码明确提醒锁顺序：WMS 可能先持有 `WindowManagerService.mGlobalLock` 再进入 DMS，因此 DMS 持有 `mSyncRoot` 时不得进行可能回调 WMS 的同步调用。

### 3.2 Android 17 已把多类慢工作移出锁

单锁不表示所有工作都在锁内执行。Android 17 使用以下方式缩短危险区：

- adapter 事件通过 DisplayThread handler 投递；
- `scheduleTraversalLocked()` 只设置 `mPendingTraversal` 并 post，WMS out-call 稍后执行；
- 显示器回调先在锁内复制回调列表，再在锁外通过 Binder 通知；
- 拓扑更新复制对象后交给执行器；
- `LocalDisplayDevice.requestDisplayStateLocked()` 只生成 `Runnable`，耗时的 `SurfaceControl.setDisplayPowerMode()` 在锁外执行；
- 显示模式规格通过 `setDesiredDisplayModeSpecsAsync()` 在 Handler 上调用 SF；
- 拓扑重新加载由 DMS 调度到后台线程执行。

拓扑写入是一个例外：Android 17 的 `DisplayTopologyCoordinator.setTopology()` 会在 `mSyncRoot` 内调用 XML 存储的 `saveTopology()`。频繁重排扩展屏时，应测量 `setTopology` 切片与文件系统延迟，不能假设拓扑持久化已经移出锁。

存在全局锁不代表应立即改成细粒度锁。应先用跟踪记录确认：

1. 哪个 tid 等待 `mSyncRoot`；
2. 持锁线程当时执行哪个 `*Locked()` 方法；
3. 等待是否位于用户可见的显示切换路径；
4. 慢点是 Java 状态计算、Binder、文件 I/O，还是锁外 SF/HWC 操作。

### 3.3 DMS 不在普通逐帧热路径

稳定显示期间，App buffer 锁存和 HWC 验证或送显不经过 DMS 的 `mSyncRoot`。DMS 的主要观察窗口通常是：

- 开机默认屏发现；
- 外接屏插拔；
- 折叠/展开或 dock DeviceState 切换；
- Display mode、resolution、color mode 变化；
- 亮度与电源状态变化；
- VirtualDisplay 创建、resize、换 Surface 与销毁。

如果稳定动画每帧都卡，而显示配置没有变化，应先检查应用、SF、HWC 和送显，不应先归因于 DMS 单锁。

## 4. DisplayDevice 到 LogicalDisplay

### 4.1 `LogicalDisplayMapper` 负责映射

`DisplayDevice` 表示发现到的设备，`LogicalDisplay` 表示框架暴露和管理的逻辑屏。`LogicalDisplayMapper` 持有：

- `SparseArray<LogicalDisplay>`；
- `SparseArray<DisplayGroup>`；
- `DeviceStateToLayoutMap`；
- 当前与待处理的 `DeviceState`；
- 当前 `Layout`；
- 虚拟设备与虚拟显示器关联；
- display id / group id 分配状态。

新设备到达时，映射器先为允许成为默认屏的设备初始化默认布局，再创建 LogicalDisplay、应用当前 Layout，并计算需要发送的逻辑显示器事件掩码。

### 4.2 Layout 使用物理地址，不只看运行时 id

DeviceState Layout 按显示器的物理地址和唯一标识查找设备，并规定：

- logical display id；
- 是否 enabled；
- display group name；
- position；
- lead display；
- brightness / refresh-rate / power throttling 配置 id。

logical display id 是运行时 framework 身份；稳定 physical id、EDID/port 与 unique id 用于识别设备。外接屏拔出再插入后，不应只按上一次 logical id 关联历史数据。

### 4.3 DisplayGroup 与 DisplayTopology 不能互换

| 模型 | 解决的问题 | 不负责什么 |
|---|---|---|
| DeviceState `Layout` | 某个设备状态启用哪些内屏、映射到哪个 LogicalDisplay、如何分组和跟随 | 不描述用户拖动排列后的跨屏坐标 |
| `DisplayGroup` | 用 group id 组织 LogicalDisplay 并发送 group event | 不表示左、右、上、下相对位置 |
| `DisplayTopology` | 用 dp 尺寸和相邻关系描述可达扩展屏，向 InputManager 提供图结构 | 不创建或删除显示器，不改变分辨率和密度 |

Android 官方 API 文档把 `DisplayTopology` 标为 version 36.1。Android 17 的 `DisplayTopologyCoordinator` 是当前 tag 下的 system_server 实现，但不能写成 API 37 才首次出现。

`DisplayTopologyCoordinator.setTopology()` 只允许重排同一批显示器。新拓扑不能增加或删除显示器 Display。显示器的添加和移除由生命周期事件驱动，拓扑协调器随后更新并持久化相对位置。

拓扑变化会复制 `DisplayTopology`，再通过 handler executor：

- 把 `DisplayTopologyGraph` 交给 InputManager；
- 向注册的 DisplayManager 回调分发拓扑更新；
- 在需要时触发 backup data changed。

这条路径服务输入跨屏和持久化，不参与 SurfaceFlinger 的逐帧图层合成。

## 5. 折叠与 DeviceState 布局切换

### 5.1 入口与启动期延后

DMS 通过 `DeviceStateManager` 回调接收新的 `DeviceState`，再调用 `LogicalDisplayMapper.setDeviceState()`。该方法先在锁外读取 `PowerManager.isInteractive()`，进入 `mSyncRoot` 后校正缓存的交互状态。

启动完成以前，映射器只保存 `mDeviceStateToBeAppliedAfterBoot`。启动动画仍可能按旧尺寸运行，此时切换内部显示布局会产生错误配置。

### 5.2 Android 17 是两阶段切换

对需要改变内屏启用状态或 logical id 的 DeviceState，mapper 使用以下顺序：

```mermaid
flowchart TD
    A["收到新的 DeviceState"] --> B["resetLayoutLocked 标记受影响显示器处于过渡中"]
    B --> C["updateLogicalDisplaysLocked 发出过渡状态"]
    C --> D["DisplayPowerController 关闭需要切换的显示器"]
    D --> E{"受影响显示器已关闭且唤醒 / 休眠条件满足？"}
    E -->|是| F["transitionToPendingStateLocked"]
    E -->|否| G["等待状态 / 交互性更新"]
    G --> F
    G --> H["500 ms 超时后强制完成"]
    H --> F
    F --> I["清除 transition 标记"]
    I --> J["applyLayoutLocked 应用目标 Layout"]
    J --> K["updateLogicalDisplaysLocked 发布最终状态"]
```

500 ms 消息是状态切换兜底，不代表显示关闭动画固定持续 500 ms。满足条件时会提前完成；超时路径用于避免某个电源或交互性回调缺失后永久卡在待处理状态。

### 5.3 wake/sleep 调用在 handler 上执行

目标 DeviceState 的属性或旧资源配置可能要求：

- unfold/lid open 时 `PowerManager.wakeUp()`；
- fold/lid close/dock 时 `PowerManager.goToSleep()`。

映射器在 `mSyncRoot` 内作出判断，再把调用投递到 Handler，避免持锁进入 PowerManager。`shouldStayAwakeOnFold()`、用户折叠设置、模拟状态和当前交互状态都会影响结果，不能把“合盖必定休眠”或“展开必定唤醒”写成平台保证。

### 5.4 折叠渲染要继续跟到 WMS 与 SF

DMS 完成 Layout 只表示 LogicalDisplay 配置确定。用户看到新画面之前还可能发生：

- WMS `DisplayContent`、Task bounds、configuration 与 Insets 更新；
- Shell transition、snapshot/splash 与 surface geometry transaction；
- 应用重启、重新布局与新尺寸缓冲区；
- SF Output 选择、HWC validate/present；
- 面板切换或厂商显示驱动延迟。

因此，折叠黑帧不能只用 `setDeviceState()` 到 `applyLayoutLocked()` 的时间解释。应把 DMS 过渡、WMS geometry、应用缓冲区和目标显示器送显放在同一条时间线上。

## 6. 显示器事件与 VSync 是两条通道

### 6.1 DMS 分发管理事件

应用通过 `DisplayManager.DisplayListener` 接收显示器添加、移除和变更等事件。Android 17 的 DMS：

1. 在 `mSyncRoot` 内选出回调；
2. 复制到临时列表；
3. 释放锁；
4. 异步 Binder 通知客户端。

这类事件用于刷新显示器列表、能力、mode、状态或拓扑。它们不是逐帧信号，也不保证收到 `onDisplayChanged()` 时对应新模式画面已经送显。

### 6.2 `DisplayEventReceiver` 的 VSync 来自 SurfaceFlinger

App/Choreographer 的 VSync 主线是：

```text
SurfaceFlinger Scheduler / EventThread
  → DisplayEventReceiver event connection
    → app process native DisplayEventReceiver
      → FrameDisplayEventReceiver
        → Choreographer.doFrame()
```

DMS 不在这条逐帧投递路径中。`LocalDisplayAdapter` 也使用 `DisplayEventReceiver`，但它主要订阅物理热插拔、显示模式变化和帧率重写等显示器事件，再更新 DisplayDeviceInfo。

### 6.3 不要假设每块物理屏有独立硬件 VSync

Android 的 `DisplayEventReceiver.onVsync()` 参数包含物理显示器 ID，SurfaceFlinger 也按显示器保存模式与时序信息；这不等于每块屏都有一条可独立调度的框架 VSync 源。

AOSP 多显示器官方文档仍说明系统不支持逐显示器 VSync，显示调度由主内屏的 VSync 驱动。分析双屏或外接屏时，应区分：

- framework/SF 的调度基准；
- 每块屏的当前显示模式、渲染帧率与送显截止时间；
- 每个 SF Output/HWC Display 的 validate/present；
- 每块屏对应的送显栅栏与驱动行为。

不同显示器可以有不同模式和独立送显结果，但不能据此推导两个应用各自获得完全独立的硬件 VSync 时钟。

## 7. 显示模式与刷新率切换

### 7.1 DMS 负责策略输入，SF/HWC 执行

`DisplayModeDirector` 汇总应用帧率投票、系统策略、功耗与设备约束，生成 `DesiredDisplayModeSpecs`。DMS 遍历把每个 LogicalDisplay 的规格交给 DisplayDevice；`LocalDisplayAdapter` 再异步调用：

```text
SurfaceControl.setDesiredDisplayModeSpecs(applyToken, specs[])
```

源码避免在持有 `mSyncRoot` 时调用这个同步 SF 接口。批量规格和应用令牌也用于让多显示器模式更新在 SurfaceFlinger 侧作为一组请求处理。

### 7.2 显示模式变化不会固定重建 BufferQueue

只切换刷新率时，已有应用窗口的 BufferQueue、SurfaceControl 与图层可以继续使用。变化主要落在：

- VSync 预测与 app/SF work duration；
- `Display.Mode`、render frame rate、deadline；
- SF/HWC active mode；
- FrameTimeline 的预期和实际送显时间。

如果显示模式同时改变分辨率，WMS 会看到 DisplayInfo 或配置变化，应用可能重新布局、重建尺寸相关缓冲区或重启 Activity。缓冲区变化来自尺寸与应用响应，不能概括成“Display.Mode 切换必然重建全部 BufferQueue”。

### 7.3 显示模式回调不是送显证据

`DISPLAY_DEVICE_EVENT_CHANGED` 表示框架观察到动态显示信息变化。判断切换何时对用户生效，还要对齐：

- SF active mode / mode change timeline；
- HWC/driver config applied；
- 新 VSync period；
- 目标显示器的送显栅栏；
- 应用是否按新节奏生产缓冲区。

只记录 `DisplayListener.onDisplayChanged()` 会把管理通知时间误当成显示时间。

## 8. DisplayPowerController 与物理 power mode

### 8.1 每个 LogicalDisplay 有一个 controller

DMS 使用 `SparseArray<DisplayPowerController>` 按逻辑显示器 ID 保存控制器。每个控制器有自己的请求状态与 `mLock`，但 Android 17 通过传入的电源 Handler Looper 创建 Handler；多个 DPC 不代表每块屏各有一条独立 Java 线程。

controller 负责汇总：

- ON/OFF/DOZE 等目标 state；
- 距离传感器与策略解除阻塞；
- auto/manual brightness；
- HBM、thermal/power throttling；
- brightness ramp；
- 主导与跟随显示器的亮度关系。

`requestPowerState()` 先更新待处理请求，再用 Handler 合并 `MSG_UPDATE_POWER_STATE`。返回 `false` 表示仍有异步状态要收敛，调用方需要等待状态回调后重试。

### 8.2 从 DPC 到 SurfaceFlinger 的锁边界

power 主线可以拆成：

```text
DisplayPowerController#updatePowerState
  → DisplayBlanker.requestDisplayState(displayId, state, brightness)
    → DMS.requestDisplayStateInternal
      → mSyncRoot 下更新逻辑 state / brightness
      → DisplayDevice.requestDisplayStateLocked 返回 Runnable
    → mSyncRoot 外执行 Runnable
      → SurfaceControl.setDisplayPowerMode(displayToken, mode)
      → backlight / brightness 更新
```

`LocalDisplayAdapter` 注释指出，设置显示器电源模式可能耗时数百毫秒，因此最慢的 SF/HAL 操作必须在 `mSyncRoot` 外执行。Perfetto 中：

- `requestDisplayStateInternal:<displayId>` 主要覆盖 DMS 状态更新；
- `setDisplayState(id=..., state=...)` 才覆盖物理 power mode 调用；
- `DisplayPowerController#updatePowerState` 覆盖 DPC 状态机。

这三段不能合并为一个切片解读。

### 8.3 多屏亮度可使用主导与跟随关系

Layout 可以为 LogicalDisplay 指定主导显示器。DMS 在显示器连接或配置变化时，调用 `updateDisplayPowerControllerLeaderLocked()`：

- 从旧主导显示器移除跟随显示器；
- 向新主导显示器添加跟随显示器；
- 控制器按新的 DisplayDeviceInfo 更新亮度配置。

跟随关系只表示亮度策略关系，不表示两个显示器共用同一个缓冲区、VSync 或送显栅栏。

## 9. VirtualDisplay 生命周期

### 9.1 创建时会在 SurfaceFlinger 建立虚拟显示令牌

VirtualDisplay 的主要路径是：

```text
DisplayManager.createVirtualDisplay()
  → IDisplayManager Binder
    → VirtualDisplayAdapter.createVirtualDisplayLocked()
      → DisplayControl.createVirtualDisplay()
      → VirtualDisplayDevice
      → DisplayDeviceRepository ADDED
      → LogicalDisplayMapper
```

本地物理屏的令牌由 SF/HWC 热插拔路径预先建立；VirtualDisplayAdapter 则主动调用 `DisplayControl.createVirtualDisplay()` 创建虚拟显示令牌。这两类生命周期不能混写。

### 9.2 调用方提供的 Surface 是输出目标

VirtualDisplayDevice 在 DMS 遍历中，通过显示事务把调用方提供的 `Surface` 设为虚拟显示器的输出 Surface。SF 把该显示器的合成结果写入这条 Surface/BufferQueue。

性能取决于：

- 输出尺寸、格式与刷新率；
- 镜像还是独立内容；
- 安全、可信和受保护内容约束；
- SF RenderEngine 或 HWC 虚拟显示能力；
- 输出消费者的出队和获取速度；
- 编码器、ImageReader 或远端传输的背压。

不能从 `VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR` 推导“没有 GPU 合成”或“CPU/GPU 复制成本接近零”。镜像只描述内容来源，不指定设备的合成实现。

### 9.3 resize、换 Surface 与 release

- `resizeVirtualDisplayLocked()` 更新宽高与密度，发送 CHANGED 并请求遍历；
- `setVirtualDisplaySurfaceLocked()` 标记 pending surface change，在 traversal transaction 中生效；
- callback Binder death 或主动 release 会停止设备、释放 Surface 引用、销毁 SF virtual display token，并发送 REMOVED。

更换 Surface 或缩放接口返回，不代表新输出帧已经到达消费者。还需观察虚拟输出合成、目标 BufferQueue 和消费者时间线。

## 10. DMS、WMS 与 SurfaceFlinger 的交接

### 10.1 DMS 遍历配置显示器，不绘制应用内容

`scheduleTraversalLocked()` 使用单个 `mPendingTraversal` 合并请求。DMS Handler 调用 `WindowManagerInternal.requestTraversalFromDisplayManager()`，WMS 在自己的 Surface 放置与遍历中回调 DMS 的 `performTraversalInternal()`。

DMS 随后对每个 LogicalDisplay：

1. 找 primary DisplayDevice；
2. 选择该显示器的事务；
3. 调 `LogicalDisplay.configureDisplayLocked()` 设置 projection、layer stack、position、size 等；
4. 让 DisplayDevice 把 Surface、显示模式规格与其他待处理配置写入事务；
5. 更新输入视口。

应用缓冲区仍由应用、编解码器、相机等生产者提交；窗口几何由 WMS/Shell 管理；SF 最终把图层状态投影到各显示器输出。

### 10.2 三类状态要分开观测

| 状态 | 主要 owner | 典型证据 |
|---|---|---|
| Display 是否存在、enabled、mode、topology | DMS | `dumpsys display`、Display event、DMS power trace |
| Window/Task 在哪个 Display、bounds、focus、Insets | WMS/Shell | `dumpsys window displays`、WindowManager trace、Shell transition |
| layer 是否可见、composition type、present | SF/HWC | layer trace、DisplayFrame、HWC validate/present、present fence |

外接屏黑屏时，`dumpsys display` 中存在 LogicalDisplay 只能证明管理对象存在；WMS 可能没有可见窗口，SF 输出可能没有目标图层，HWC 或面板也可能尚未送显。

### 10.3 多显示器共享资源

SurfaceFlinger 按显示器构造输出和送显结果，但多块屏仍可能共享：

- SF 主线程和合成线程预算；
- RenderEngine 与 GPU queue；
- HWC plane、scaler 与带宽；
- 内存带宽与温控或功耗预算；
- vendor display HAL/driver serialization。

一块屏正常送显不能证明另一块屏也正常。性能数据必须带显示器 present ID 或令牌、显示模式、输出与送显栅栏。

## 11. 性能测量

### 11.1 先定义端到端区间

| 场景 | 建议起点 | 建议终点 |
|---|---|---|
| 开机默认屏就绪 | 注册 default adapters | default LogicalDisplay + VirtualDisplayAdapter 条件满足 |
| 外接屏接入 | SF hotplug timestamp | 目标 Display 第一帧 present |
| 外接屏移除 | SF disconnect | WMS/SF 不再呈现该 Display 内容且资源释放 |
| 折叠/展开 | DeviceState callback | 新目标 Display 的 App frame present |
| 刷新率切换 | 期望规格改变 | 在新模式下稳定送显 |
| power ON/OFF | DPC power request | physical mode committed / panel 侧证据 |
| VirtualDisplay 首帧 | create/set Surface | consumer acquire 第一块有效 buffer |

DMS 内部事件完成与用户可见结果之间通常还隔着 WMS、App、SF、HWC 和 driver。端到端指标不能停在 DMS callback。

### 11.2 Perfetto 采集

下面的命令用于同时保留调度、Binder、图形、窗口与功耗事件：

```bash
adb shell perfetto \
  -o /data/misc/perfetto-traces/display-lifecycle.perfetto-trace \
  -t 20s \
  sched freq idle binder_driver gfx view wm power
```

在 Android 17 跟踪记录中优先搜索：

- `DisplayDeviceRepository#onDisplayDeviceEvent (event=...)`，仅 debug logging 开启时存在；
- `handleDisplayDeviceChanged`，同样受 debug 条件影响；
- `sendDisplayEventsLocked#event=...`；
- `deliverDisplayEvent#events=...,displayId=...`；
- `setTopology`、`sendTopologyUpdateLocked`、`deliverTopologyUpdate`；
- `DisplayPowerController#updatePowerState`；
- `requestDisplayStateInternal:<displayId>`；
- `setDisplayState(id=..., state=...)`；
- `setDisplayBrightness(id=...)`；
- `DisplayPowerMode`、`ScreenState`、`ScreenBrightness` counter；
- WMS display traversal / surface placement；
- SF hotplug、mode change、composition 与目标 Display present。

`mSyncRoot` 没有固定的同名 trace slice。判断锁竞争需要结合 system_server 线程 running/runnable/blocked 状态、Java monitor contention、调用栈和相邻 DMS slice，不能用 `android.display` 线程 CPU 占用替代持锁时间。

### 11.3 dumpsys 与日志基线

下面这组命令先建立显示器、Window、SF 与电源的静态映射：

```bash
adb shell dumpsys display
adb shell dumpsys window displays
adb shell dumpsys SurfaceFlinger --display-id
adb shell dumpsys SurfaceFlinger --list
adb shell dumpsys power
adb shell logcat -b system -s \
  DisplayManagerService \
  DisplayDeviceRepository \
  LogicalDisplayMapper \
  LocalDisplayAdapter
```

记录时至少保存：

- logical display id、unique id、address、group id；
- enabled/state/committedState；
- 当前、默认和支持的显示模式与渲染时序；
- primary DisplayDevice、physical display id/token；
- WMS 的 `DisplayContent`、任务与窗口分布；
- SF 显示对象、输出与可见图层；
- DisplayPowerController request、brightness、lead/follower；
- topology 与 InputManager graph。

单独保存 `dumpsys display` 无法复原屏幕上的窗口与最终送显状态。

## 12. 常见故障的排查顺序

### 12.1 开机报 “Timeout waiting for default display”

按顺序检查：

1. SurfaceFlinger 是否已注册服务并枚举物理显示器；
2. HWC 是否上报主物理显示器；
3. `getPhysicalDisplayToken()` 是否返回 token；
4. LocalDisplayAdapter 是否发送 ADDED；
5. repository 是否接收事件；
6. default LogicalDisplay 是否被 Layout 接纳；
7. VirtualDisplayAdapter 是否创建。

超时日志中的默认显示器与 `mVirtualDisplayAdapter` 值能直接区分两个等待条件。

### 12.2 外接屏已识别但没有画面

依次确认：

- LogicalDisplay 是否启用；
- 外接显示器策略是否允许扩展或镜像；
- WMS 是否创建对应 `DisplayContent`；
- 目标屏是否有可见任务或窗口；
- DMS 投影和图层栈是否配置；
- SF 是否有对应显示对象或输出；
- HWC 验证、送显与驱动是否成功；
- 安全或受保护内容是否允许出现在该显示器。

“DisplayListener 收到 added”只能完成其中前半段。

### 12.3 折叠后黑帧或旧尺寸停留

对齐：

1. `setDeviceState()` 与待处理状态；
2. `isInTransition` 显示器是否按预期关闭；
3. 是否走到 500 ms timeout；
4. target Layout 的物理 address、logical id 与 enabled 状态；
5. WMS configuration/bounds；
6. Shell transition/snapshot；
7. 应用新尺寸缓冲区；
8. 新显示器送显。

若 DMS 在几毫秒内完成，而首帧晚数百毫秒，应继续检查 WMS/App/SF，避免在 SyncRoot 上反复调参。

### 12.4 refresh rate 已变但动画节奏异常

收到 DisplayInfo 显示模式回调后，确认：

- Choreographer 预测周期是否更新；
- 应用是否仍按旧帧率投票；
- SF active mode 与 FrameTimeline deadline；
- 缓冲区是否延迟；
- 目标显示器的送显节奏；
- 外接屏是否受 primary VSync 驱动和 cadence 转换。

DMS 显示模式变化与应用逐帧生产是两个阶段。

### 12.5 `setDisplayPowerMode` 很慢

先看 `setDisplayState(id=..., state=...)` 切片与同名日志耗时，再向下核对：

- SF Binder 排队；
- HWC power mode call；
- panel/driver suspend/resume；
- vendor backlight；
- display offload/sidekick；
- 上下电所需的栅栏或空闲等待。

这段慢工作已经在 `mSyncRoot` 外。优化 DMS 锁不能缩短 HAL 或驱动自身的耗时。

### 12.6 VirtualDisplay 卡住

区分：

- virtual token/LogicalDisplay 未创建；
- output Surface 为 null；
- resize/surface transaction 未应用；
- SF 没有可见内容；
- 消费者不执行出队，BufferQueue 形成背压；
- MediaProjection 或安全策略阻止内容；
- encoder/ImageReader 消费慢；
- 虚拟输出合成或 GPU/HWC 资源不足。

先确认第一块有效缓冲区的生产者与消费者关系，再讨论复制和合成成本。

## 13. 版本演进

| 平台 | 相关边界 | 分析要点 |
|---|---|---|
| Android 12 / API 31 | 现代 BLAST、DisplayArea、LogicalDisplay 与多显示器基线已经存在 | DMS 并非 Android 17 新增服务 |
| Android 13 / API 33 | HWC HAL 转向 AIDL；DMS/SF 的显示器职责分界保持 | HAL 接口变化不等于 LogicalDisplay 模型重写 |
| Android 16 / API 36 | `DisplayManager` 增加按事件掩码注册监听器的公开能力与 `EVENT_TYPE_DISPLAY_*` 常量 | 应用回调仍是管理事件，不是送显信号 |
| version 36.1 | 官方 API 文档标注 `DisplayTopology` 与相关访问入口 | topology 表示可达扩展屏相对位置，不替代 Layout/DisplayGroup |
| Android 17 / API 37 | 当前固定实现：现行 DMS、TopologyCoordinator、content-mode/display policy、DeviceState 和 power 路径 | 以 `android-17.0.0_r1` 的 flag、资源 overlay 与设备能力判断实际行为 |

Android 17 允许部分外接屏在镜像与承载内容之间动态切换，相关系统装饰与内容模式仍受显示器标志、策略和设备配置约束。不能把某个 AOSP 开关路径写成所有 Android 17 设备默认启用。

## 14. Android 17 源码与官方文档入口

### DMS 与映射

- [`DisplayManagerService.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/display/DisplayManagerService.java)：启动 phase、SyncRoot、adapter 注册、LogicalDisplay listener、traversal、回调与 power 接线；
- [`DisplayAdapter.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/display/DisplayAdapter.java)：adapter 事件的 handler 投递；
- [`DisplayDeviceRepository.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/display/DisplayDeviceRepository.java)：DisplayDevice 集合、差异与映射器监听器；
- [`LogicalDisplayMapper.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/display/LogicalDisplayMapper.java)：DeviceState Layout、LogicalDisplay、DisplayGroup 与 500 ms 切换兜底；
- [`DisplayTopologyCoordinator.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/display/DisplayTopologyCoordinator.java)：相对位置、合法性检查、持久化与 InputManager graph。

### 本地、虚拟与功耗显示器

- [`LocalDisplayAdapter.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/display/LocalDisplayAdapter.java)：physical id/token、hotplug、mode specs、power mode 与 brightness；
- [`VirtualDisplayAdapter.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/display/VirtualDisplayAdapter.java)：virtual token、Surface、resize、Binder death 与 release；
- [`DisplayPowerController.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/display/DisplayPowerController.java)：异步 power request、brightness、policy 与状态收敛。

### VSync、SurfaceFlinger 与文档

- [`DisplayEventReceiver.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/DisplayEventReceiver.java) 与 [`EventThread.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/EventThread.cpp)：hotplug/VSync event connection 与分发；
- [`SurfaceFlinger.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp)：physical/virtual Display、mode、Output 与 composition；
- [AOSP Multi-Display overview](https://source.android.com/docs/core/display/multi_display) 与 [Display support](https://source.android.com/docs/core/display/multi_display/displays)：LogicalDisplay、stable id、Display 支持和 per-display VSync 限制；
- [`DisplayTopology` API](https://developer.android.com/reference/android/hardware/display/DisplayTopology)：version 36.1 与相对位置语义。

## 小结

Android 17 的显示器生命周期可分成四段：

1. SurfaceFlinger/HWC 发现物理显示器，或框架创建 VirtualDisplay 令牌；
2. DisplayAdapter 与 repository 形成 DisplayDevice；
3. LogicalDisplayMapper 按 Layout 建立 LogicalDisplay、group 与 DeviceState 过渡；
4. DMS 把配置交给 WMS/InputManager/SF，最终由窗口 Producer、SurfaceFlinger、HWC 与显示设备完成画面 present。

`mSyncRoot` 保证 DMS 共享模型一致，Android 17 已把 Binder callback、WMS out-call、topology callback、mode specs 和耗时 power 操作放到锁外或异步执行。评估性能时，应测量具体持锁段和端到端 Display 结果，不能把单锁存在本身当作卡顿证据。

VSync 由 SurfaceFlinger EventThread 投递，DMS 负责显示器管理事件；DeviceState Layout、DisplayGroup 与 DisplayTopology 也分别解决不同问题。区分这些边界后，才能定位开机默认屏等待、外接屏黑屏、折叠切换、显示模式变化、VirtualDisplay 背压和电源模式延迟。
