---
title: Android Auto 与 Android Automotive OS 性能优化
chapter: '19.7'
section: '19.7'
status: finalized
applicable_versions: Android 14 (API 34) - Android 17 (API 37)
tags:
  - android-auto
  - car-os
  - 车载
related_chapters:
- '18.6'
- '19.3'
- '25.2'
confidence: medium-high
last_verified: '2026-10-25'
last_verified_against: Android for Cars docs current on 2026-10-25; AOSP android-17.0.0_r1 Car APIs/services and AIDL VHAL; android17-6.18-2026-06_r6
sources:
- type: official
  path: Android for Cars App Library official docs
  urls:
  - https://developer.android.com/training/cars
  - https://developer.android.com/training/cars/apps/library
  - https://developer.android.com/training/cars/apps/library/refresh-template
  - https://developer.android.com/training/cars/apps/library/constraints-api
  - https://developer.android.com/training/cars/apps/library/template-restrictions
  - https://developer.android.com/training/cars/apps/library/draw-maps
  - https://developer.android.com/training/cars/apps/library/glossary-concepts
  - https://developer.android.com/training/cars/whats-new
- type: official
  path: Android for Cars media/navigation/testing official docs
  urls:
  - https://developer.android.com/training/cars/apps/navigation
  - https://developer.android.com/training/cars/media
  - https://developer.android.com/docs/quality-guidelines/car-app-quality
  - https://developer.android.com/training/cars/testing/dhu
  - https://developer.android.com/training/cars/testing/emulator
- type: official
  path: AAOS Automotive overview / VHAL / CarWatchdog / Power Management official docs
  urls:
  - https://source.android.com/docs/automotive/start/what_automotive
  - https://source.android.com/docs/automotive/vhal
  - https://source.android.com/docs/automotive/security/vehicle_system_isolation
  - https://source.android.com/docs/automotive/watchdog/wd_system_health
  - https://source.android.com/docs/automotive/watchdog/wd_flash_memory
  - https://source.android.com/docs/automotive/power/power
  - https://source.android.com/docs/automotive/power/power_policy
  - https://source.android.com/docs/automotive/tools/sys-perf
- type: aosp
  path: packages/services/Car car-lib and service sources @ android-17.0.0_r1
  urls:
  - https://android.googlesource.com/platform/packages/services/Car/+/android-17.0.0_r1/car-lib/src/android/car/hardware/property/CarPropertyManager.java
  - https://android.googlesource.com/platform/packages/services/Car/+/android-17.0.0_r1/car-lib/src/android/car/watchdog/CarWatchdogManager.java
  - https://android.googlesource.com/platform/packages/services/Car/+/android-17.0.0_r1/service/src/com/android/car/watchdog/CarWatchdogService.java
  - https://android.googlesource.com/platform/packages/services/Car/+/android-17.0.0_r1/car-lib/src/android/car/hardware/power/CarPowerManager.java
  - https://android.googlesource.com/platform/packages/services/Car/+/android-17.0.0_r1/service/src/com/android/car/power/CarPowerManagementService.java
- type: aosp
  path: hardware/interfaces/automotive/vehicle/aidl IVehicle.aidl @ android-17.0.0_r1
  url: https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/automotive/vehicle/aidl/android/hardware/automotive/vehicle/IVehicle.aidl
last_deep_review_at: 2026-07-31
last_review_finalize_at: 2026-08-09 04:17:59+08:00
---

# Android Auto 与 Android Automotive OS 性能优化

Android Auto 和 Android Automotive OS（AAOS）都能把应用体验送上车载屏幕，但两者在执行位置、界面生成、网络归属和电源生命周期上走的是不同的路。做性能分析时，我们要先把平台分清：把手机投射延迟归到车机应用，或把 AAOS 的车辆接口套到 Android Auto 客户端，都是常见的归因错误。

> 源码基线：AOSP `android-17.0.0_r1`（Android 17 / API 37），内核标签 `android17-6.18-2026-06_r6`，核对范围是 AAOS 系统侧。Android Auto 场景中，该内核标签只描述运行手机客户端的一端；车机投射接收端使用什么操作系统和内核，取决于具体产品，普通应用检查或控制不了。

## 两种平台，三种 UI 责任

车载界面（UI）由三处责任共同生成，看性能问题前我们先分清它们：模板应用的界面模型（Template）在客户端进程里构建，布局与控件交给 host 绘制；地图 Surface 由应用自己提交图形帧；允许停驻使用的 Activity 走常规 Android 渲染路径。两个平台把这三处责任放在不同设备上，延迟来源也就跟着不同。

### Android Auto：应用与 host 在手机，体验投向车端

Android Auto 平台运行在手机上，再把体验投射到兼容车机。Car App Library 是用于构建车载模板应用的 Jetpack 库；它所说的 host（宿主）由手机上的 Android Auto 实现，负责发现应用、管理生命周期，并把应用返回的 `Template` 数据转换成符合驾驶限制的界面。在这条链路里，车机只承担显示、输入和音频端点的角色。

媒体应用还可以通过 `MediaBrowserService` 或 Media3 的 `MediaLibraryService` 暴露内容，并通过 `MediaSession` 提供播放状态和控制。这条链路里有一块我们动不了：USB、Wi-Fi 或蓝牙投射协议归 Android Auto 所有，车机接收端的重连算法也由它管理。我们能优化的是自己的会话恢复、模板生成、业务网络、地图 Surface 和媒体处理流程。

### AAOS：应用安装在车机

AAOS 则是直接运行在车载硬件上的 Android 系统，应用进程、存储、网络和系统服务都在车辆端，Car App Library 的 host 也换成车机中的系统应用。模板应用照样向 host 提供界面模型；导航、POI（Point of Interest，兴趣点）、天气等允许绘图的类别可以取得 host 提供的 `Surface` 来绘制地图。允许停驻使用的 Activity 在 AAOS 上走的是常规 Android 渲染路径。

AAOS 还包含 CarService、VHAL、CarWatchdog 和车辆电源状态机这一层系统设施。CarService 是车载系统服务入口；VHAL（Vehicle Hardware Abstraction Layer，车辆硬件抽象层）把车辆网络能力表示为属性；CarWatchdog 监测进程健康与闪存写入。启动、休眠、I/O 和车辆属性访问都会受到它们影响，而其中多数控制接口受签名或特权权限保护。

下面的图用于定位应用进程、host、网络和车辆接口。Android Auto 子图中的 host 位于手机，末端节点才代表车机显示、输入与音频。


<details>
<summary>平台责任图的 Mermaid 源码</summary>

```mermaid
flowchart LR
    subgraph auto["Android Auto 手机投射"]
        direction TB
        phone["手机中的应用或 Service"] --> autoHost["Android Auto host"]
        autoHost --> autoDisplay["车载显示、输入与音频"]
        phone --> phoneNet["手机网络"]
    end

    subgraph aaos["Android Automotive OS"]
        direction TB
        carApp["车机中的应用或 Service"] --> aaosHost["模板 host 或系统 UI"]
        parked["允许停驻使用的 Activity"] --> aaosDisplay["车载显示与输入"]
        aaosHost --> aaosDisplay
        carApp --> carNet["车机网络"]
        carApp --> carService["CarService 与权限检查"]
        carService --> vhal["VHAL 与车辆网络"]
    end
```

</details>

定位卡顿时，先把问题归入模板模型、host 绘制、投射传输或应用自己的 Surface 中的一类。上面的图把两种平台的责任落点并排放到了一起：Android Auto 的模板模型与 host 绘制都在手机，车机负责投射接收、显示、输入和音频；AAOS 的应用与 host 则都在车机内。

## 车载应用的版本轴

调试车载应用时，我们至少要记录四类版本：

| 版本轴 | 决定什么 | 调试时怎样记录 |
|---|---|---|
| Android SDK API level | Framework 行为、权限和平台 API | 手机或车机的 SDK、软件构建指纹（build fingerprint） |
| Car App API level | host 与客户端之间可用的模板和 Car App 服务能力 | 应用清单（manifest）的 `minCarApiLevel`、运行时 host 支持 |
| `androidx.car.app` 版本 | 客户端库 API 与兼容修复 | Gradle 依赖版本和发布说明（release notes） |
| host / 整车厂（OEM）软件版本 | 模板渲染、输入、投射和车辆集成 | Android Auto/host 版本、车机软件版本 |

这四条轴相互独立：升级到 Android 17 并不会自动开启某个 Car App Library 模板，Jetpack 库升级也改不了旧 host 的能力，host 支持什么、内容限制在哪里，要靠产品代码在运行时查询。发布阶段同样要单独核对：Car App Library 媒体体验在 Android 17 及更高版本 AAOS 上获得完整支持，在 Android Auto 上仍受早期访问与测试轨道限制；停驻游戏已于 2026 年 9 月 14 日在 Android Auto 与 AAOS 上正式开放，可发布到所有 Play 轨道；浏览器仍仅支持 AAOS 的内部测试轨道。判断类别可用性，要看发布阶段和 host 能力，Android API level 只是四条轴之一。


## 模板应用的性能重点

### 冷启动路径

一个典型模板应用的冷启动，要经过 `CarAppService` 绑定、`Session` 创建、首个 `Screen` 创建和 `Screen.onGetTemplate()` 返回这几步。`Screen` 是管理一页模板及其生命周期的对象；host 只有拿到首个合法模板后才能呈现内容。

`onGetTemplate()` 是同步取模接口，网络、数据库迁移、图片解码和路线计算这类等待，我们都要放到回调之外。更稳妥的结构是：

<!-- gracker-diagram: a205-03-first-template -->
![首模板只依赖可立即读取的本地状态](../../assets/diagrams/ch19/a205-03-first-template.png)

图：先返回可用模板；后台更新就绪后请求刷新，页面或会话失效时取消旧任务。

1. 进程启动时恢复一份小而完整的本地快照；
2. `onGetTemplate()` 只读取不可变界面状态（view state）并构建模板；
3. 网络和磁盘工作在后台执行；
4. 新状态就绪后在主线程调用 `Screen.invalidate()`；
5. 页面销毁或 host 断开时取消无用请求。

`invalidate()` 只请求 host 再次调用 `onGetTemplate()`，应从主线程调用；`Screen` 未达到 `STARTED` 生命周期时，该调用没有效果。它发出一次刷新请求后，新模板返回前的继续调用不会产生新请求。host 还会限制车屏更新频率，短时间内返回多个模板时，车屏可能只显示末次结果。所以它的定位是通知 host“内容变了”，更新节奏由 host 掌握：拿它当动画时钟行不通，为每个网络分片刷一次界面也属于误用。

### 模板配额和内容限制

host 会限制一个任务中的模板步数，最多显示五个模板。配额按 Template 数量计算，与 `Screen` 实例数无关；同类内容刷新、返回上一级（back）和结束一项任务后重置（reset）各有专门规则。配额耗尽后还继续发送新模板，host 可以显示错误并关闭应用。

不同车辆允许展示的条目数量也不同，所以下面的代码按 host 的网格限制裁剪业务数据。

```kotlin
val constraints = carContext.getCarService(ConstraintManager::class.java)
val gridLimit = constraints.getContentLimit(
    ConstraintManager.CONTENT_LIMIT_TYPE_GRID
)
val visibleItems = items.take(gridLimit)
```

`ConstraintManager` 返回 host 设定的内容上限，客户端只能查询。按运行时上限准备模型，比按某个车机分辨率或品牌维护固定列表更可靠；分页和“更多”操作同样要服从对应模板的驾驶限制。


### 模板生成应测什么

模板 UI 由 host 绘制，这带来一个观测问题：FrameTimeline 是 Android 记录应用帧生命周期与延迟的工具，但客户端进程中的 FrameTimeline 覆盖不到 host 的完整绘制和车端显示。所以这些数据要靠客户端自己记录：

- service 绑定到首个模板返回的时间；
- 每次 `onGetTemplate()` 的执行时间分布；
- 界面状态版本、模板类型、条目数和图片数量；
- `invalidate()` 请求到下一次模板返回的间隔；
- host 断开后会话和首屏恢复时间。

车屏端到端延迟还包含 IPC（进程间通信）、投射链路、host 更新限制、布局绘制和显示扫描。trace 是带时间戳的执行事件记录；车端没有 trace 可用时，我们可以用高速摄像和可识别的输入/画面标记，量出触摸到可见反馈的时间。

## 导航与地图 Surface

### Surface 生命周期

导航、POI 和天气类模板要取得地图 Surface，前提是声明相应模板权限以及 `androidx.car.app.ACCESS_SURFACE`。之后应用通过 `AppManager.setSurfaceCallback()` 接收 `onSurfaceAvailable()` 与 `onSurfaceDestroyed()`。

每次 `onSurfaceAvailable()` 到达，都要以 `SurfaceContainer` 提供的宽、高、DPI（每英寸像素数）和 `Surface` 为准；尺寸或 DPI 变化时，即使底层 Surface 尚未销毁，也可能再次收到这个回调。每个收到的 `Surface` 实例都必须调用 `release()`。`onSurfaceDestroyed()` 到达后，我们要停止提交帧，并释放实现中创建的 `VirtualDisplay`（虚拟显示）、`Presentation`（显示内容容器）、EGL 图形接口关联的绘图表面、图形缓冲区和地图引擎引用。

Surface 改变的原因很多：投射断开、host 重建、昼夜模式或配置变化都可能触发。区域信息也随回调更新——host 通过 `onVisibleAreaChanged()` 告知当前保证无遮挡的 visible area，用 `onStableAreaChanged()` 给出考虑动态遮挡后长期稳定的最小区域。布局时按内容性质分配：当前必须可见的重要内容放 visible area；要停在固定位置、避免跟着 host 控件显隐移动的持续内容放 stable area。固定安全边距这套做法，会在超宽屏、远端屏和不同旋转输入布局上出错。

<!-- gracker-diagram: a205-05-surface-lifecycle -->
![每次 Surface 回调都重新确认几何与资源](../../assets/diagrams/ch19/a205-05-surface-lifecycle.png)

图：Surface 未销毁也可再次报告可用；每个收到的 Surface 实例都要释放，地图布局同时响应可见区域和稳定区域。

### 地图渲染预算

只有在地图 Surface 上，应用才有可控的持续帧处理流程。这里的帧预算指生成并提交一帧画面可用的时间。我们优化时把流水线分开观察：

- 路线和定位状态更新；
- 地图瓦片（按区域切分的小块地图数据）请求、缓存命中与磁盘读取；
- 矢量解析、文字标签排布（label placement）和图标纹理集（atlas）；
- RenderThread、GPU（图形处理器）提交与 BufferQueue；
- host 覆盖层（overlay）与显示呈现。

这条流水线要先认清两个角色：RenderThread 是 Android 提交绘制命令的专用线程，BufferQueue 在图形生产者和显示消费者之间传递缓冲区。路线计算、瓦片解码和图标生成不应阻塞渲染线程。快速拖动时可以取消已经离开当前地图范围的请求，合并重复瓦片，限制正在解码的任务数，并复用图形资源。热压力较高或 GPU 可用性能余量（headroom）不足时，可以优先减少非导航覆盖物、阴影和预取范围；路线、下一转向和安全相关提示仍要保持可读。

每帧可用时间由 Surface 尺寸、host 显示模式和车辆产品配置共同决定，所以地图刷新率以设备报告和 trace 为准，固定写 60 Hz 行不通。记录时分别记平均帧率、jank（迟到或丢失的帧）、帧呈现时间与功耗。


### 导航状态和语音

Car App Library 导航应用通过 `NavigationManager` 更新 `Trip`、`TravelEstimate` 和逐向导航状态；host 也可能调用 `onStopNavigation()` 叫停导航。路线会话是否活跃要持久记录下来，不能只依赖当前 `Screen` 是否存在。

导航语音需要请求 audio focus（音频焦点，决定多个声音如何协调），并使用 `AudioAttributes.USAGE_ASSISTANCE_NAVIGATION_GUIDANCE`。官方建议的短时焦点类型是 `AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK`，允许其他媒体暂时降低音量；duck 就是这类自动压低音量。语音生成、媒体降音量和播放完成事件要带会话 ID，避免重算路线后播出旧指令。

定位请求频率以够用为准，服务于导航精度和路线匹配即可，设备最高采样率不适合长期开启。GNSS 是卫星定位系统；把定位时间戳、精度、速度、路线匹配耗时和渲染使用的位置版本都记下来，我们才能区分定位波动、路线计算慢和画面更新慢。

## 媒体应用

媒体浏览和播放围绕 `MediaBrowserService` 或 Media3 的 `MediaLibraryService` 与 `MediaSession` 组织。内容浏览树（browse tree）是供 host 分层浏览的目录；MediaSession 提供播放状态、队列、元数据（metadata，例如标题和封面）以及播放、暂停、跳转等控制。按 host 能力和发布要求保留这些组件或兼容路径，是 Car App Library 媒体体验的前提。

从性能角度看，这类应用的工作可以分为四块：

- **浏览树**：根节点和常用分类从本地索引快速返回；远端结果分页加载，错误状态可恢复。
- **图片**：封面按 host 所需尺寸解码，设置内存和磁盘缓存上限，避免为每个条目保存一份原图。
- **播放状态**：播放器状态先写入 `MediaSession`，UI 作为状态的消费者；host 重连后可立即拿到当前队列和位置。
- **音频**：正确处理音频焦点、自动降音量（duck）、蓝牙或车载输出变化，以及 `ACTION_AUDIO_BECOMING_NOISY`（音频输出设备断开）事件；不要在 UI 线程准备解码器或等待 DRM（数字版权管理）与网络响应。

从播放命令到车载扬声器，中间还有 Android 音频栈、AAOS CarAudioService 或 Android Auto host、DSP（数字信号处理器）和车辆放大器，应用 trace 只能覆盖其中一段。测量时我们分段记录命令接收、播放器状态变化、首个音频缓冲区和车内声学输出。

<!-- gracker-diagram: a205-07-media-path -->
![媒体控制与声音输出分段观测](../../assets/diagrams/ch19/a205-07-media-path.png)

图：用同一命令标识关联状态和缓冲区事件，声学终点需要外部或平台观测补齐。

视频、游戏和浏览器这些停驻体验，要按当前平台支持、车辆状态和发布轨道分别处理。截至 2026 年 10 月 25 日：游戏可在 Android Auto 与 AAOS 上停驻使用，并发布到所有 Play 轨道；浏览器仅支持 AAOS 停驻使用，限内部测试轨道；视频类别支持 AAOS 的所有轨道，主要在停驻时使用。官方允许的行驶中有限使用是音频能力，不能据此在行驶中显示视频。详见[当前支持类别](https://developer.android.com/training/cars#supported-app-categories)与[2026 年 9 月发布更新](https://developer.android.com/training/cars/whats-new)。

## 网络与断线恢复

### 区分投射连接和业务网络

Android Auto 的投射传输由手机上的 Android Auto 与车机接收端管理；客户端的业务请求则通常走手机网络，我们可以通过 `ConnectivityManager` 观察网络是否可用、是否按流量计费。AAOS 应用用的是车机网络，来源可能是蜂窝、Wi-Fi、以太网或厂商网关。

投射连接的重建留给系统，应用不应通过私有 Wi-Fi 或蓝牙自行操作；我们要处理的是 host 会话生命周期和标准网络变化。这两件事可能独立发生：投射仍在但业务网络断开，或业务网络可用但 host 已离开。


### 可恢复的数据管线

导航和媒体的网络层应具备以下属性：

- 请求可取消，切换路线、账号或 Screen 后不会把旧结果写回新状态；
- 分页和下载可续传，每次失败后逐步延长重试等待时间，并加入少量随机量以避免大量客户端同时重试；
- 缓存条目带版本、过期时间和校验值，以便发现不完整或损坏的数据；
- 写入采用事务或临时文件，成功后再替换正式文件，避免进程死亡留下半成品；
- 大文件下载服从网络计费、存储余量和 AAOS power policy；
- 离线状态也返回一个合法模板，`onGetTemplate()` 不等待网络。

Android Auto 和 AAOS 的账号状态同步宜以服务端版本号或只增不减的修订号（revision）为准；播放、收藏、路线目的地等命令应设计成幂等操作，即同一请求重复执行也不会产生额外副作用。业务状态的唯一来源，交给一条永久存活的手机到车机 socket（网络连接）是靠不住的。另外，AAOS power policy（电源策略）可以按车辆状态关闭网络、显示、音频或定位等组件。

## AAOS 的资源与电源约束

### CarWatchdog 与磁盘写入

CarWatchdog 在 AAOS 上跟踪应用和服务的磁盘写入，依据是内核 `/proc/uid_io/stats` 暴露的 per-UID（按应用身份）I/O（磁盘读写）统计。写入量从每个 UTC（协调世界时）自然日开始累计，同一天内的多次车辆启动不会清零。第三方应用反复超过配置阈值时，可以被设为 `COMPONENT_ENABLED_STATE_DISABLED_UNTIL_USED`，即停用到用户再次启动或手动启用。地图和媒体类别可以有较高的独立阈值，具体数值及处理动作由系统和厂商配置共同决定。

`CarWatchdogManager.getResourceOveruseStats(resourceFlag, maxStatsPeriod)` 可以查询调用包当前一天或过去最多 30 天的资源超限统计，`addResourceOveruseListener(executor, resourceFlag, listener)` 则为调用包注册监听器：I/O 写入达到阈值的约 80% 或 100% 时，监听器可收到接近超限或已经超限的通知。对照这套机制，地图应用应特别检查：

- 瓦片和路线缓存是否反复覆盖同一文件；
- SQLite WAL（预写日志）执行 checkpoint（把日志内容合并回主数据库）的频率与日志保留；
- 图片转码和临时文件是否重复生成；
- 离线包解压是否可复用；
- 每次位置更新是否触发持久化。

写放大指底层实际写入量大于业务数据量。要压低它，减少反复改写和无效淘汰通常比单纯扩大缓存更有效；同时应记录逻辑下载字节、文件系统写入字节、缓存命中率和淘汰量。

<!-- gracker-diagram: a205-09-watchdog-writes -->
![CarWatchdog 按 UTC 自然日累计写入](../../assets/diagrams/ch19/a205-09-watchdog-writes.png)

图：日累计不会因同日重启清零；阈值与动作按系统、类别和 OEM 配置执行。

### 车辆电源状态

车辆的电源状态由 `CarPowerManagementService`（CPMS）与 VHAL 协调，涵盖启动（On）、关机准备（Shutdown Prepare）、内存挂起（Suspend-to-RAM，CPU 停止执行而内存继续供电）、磁盘休眠（Suspend-to-Disk，内存写入非易失存储后断电）和关机等状态。`CarPowerPolicyDaemon` 是集中管理电源策略的常驻后台进程，策略可以关闭显示、音频、定位、蓝牙或其他组件。

`CarPowerManager` 的多项状态与完成回调属于仅面向系统组件的受权限保护 System API。`setListenerWithCompletion()` 需要 `CONTROL_SHUTDOWN_PROCESS` 权限，电源切换的延长只属于持有该权限的系统组件，普通第三方应用用不上。我们能做的是按常规 Android 生命周期持久化最小恢复状态，接受进程随时被终止，并在网络、位置或音频能力恢复后重建会话。

在 `android-17.0.0_r1` 中，`CarPowerStateListenerWithCompletion` 只会为允许等待完成的状态传入非空 `CompletablePowerStateChangeFuture`，其中包括 `STATE_SHUTDOWN_PREPARE`、`STATE_SUSPEND_ENTER` 和 `STATE_HIBERNATION_ENTER` 等状态。特权服务完成清理后，要在 `getExpirationTime()` 给出的期限前调用 `complete()`，到期后系统仍会继续转换。因此挂起或关机准备阶段，大规模同步与缓存整理应另择时机。


### 热环境与充电

车内的热负载常常是多因素叠加：高温、阳光直射、无线投射、手机充电和持续导航可能同时起作用。测试至少覆盖冷车（车辆静置并降至环境温度）、热浸后启动（在高温环境静置到座舱和部件充分升温）、持续导航加充电、弱信号和昼夜模式切换。

运行时，应用可以结合 `PowerManager` 的温控状态与 thermal headroom（接近严重温控阈值的归一化指标）调整地图细节、预取、后台同步和动画。测持续负载下温度趋于稳定的热稳态时，要保留原有散热条件；主动风冷只用于组件隔离实验，其结果要与原机分开看。

## VHAL、车辆属性与 ADAS

Android 17 的 VHAL 接口由 AIDL（Android Interface Definition Language，用于定义跨进程接口）定义，接口文件是 `IVehicle.aidl`，它把车速、挡位、空调等车辆属性转换成 Android 侧的统一接口。应用侧的入口是 CarService 的 `CarPropertyManager`，读取属性时接受相应的权限检查；普通应用没有绕过 CarService 直连车内总线的路径。

在 `android-17.0.0_r1` 中，旧的 `registerCallback()` 已弃用。设备开放相应功能开关时，新代码宜使用 `subscribePropertyEvents()`；需要兼容旧系统或未开放该接口的产品时，仍要保留旧订阅路径。连续属性的采样率是请求值，VHAL 不保证按精确频率回调。新接口默认启用可变更新率（variable update rate），数值没有变化时可以省略重复回调；只有业务需要固定频率样本时才关闭它。

同步 `getProperty()` 和各类型的同步读取方法可能耗时数秒，调用位置要放在主线程之外；一次读取多个属性时可以使用 `getPropertiesAsync()`，或在受控后台线程执行兼容路径。订阅回调若未显式指定 `Executor`（负责调度回调任务的执行器），会使用创建 `Car` 时传入的事件线程；没有提供该线程时通常落到主线程。所以回调里我们只保存快照并投递后续任务，解析、聚合和网络上传放到有队列上限的线程池。单次回调数据量过大，或 OEM 自定义车辆属性更新过于频繁，都会挤占车辆属性通道。

<!-- gracker-diagram: a205-11-vehicle-data -->
![车辆属性先过权限，再以有界任务消费](../../assets/diagrams/ch19/a205-11-vehicle-data.png)

图：同步属性读取可能阻塞，回调线程也不宜承载重任务；请求采样率不代表精确回调频率。

Android Auto 客户端没有直接访问 AAOS VHAL 的通道。跨平台需要有限车辆信息时，应使用 Car App Library 对应的 Car Hardware API，并处理 host 不支持该能力或权限受限的情况。

ADAS（Advanced Driver Assistance Systems，高级驾驶辅助系统）和其他安全相关控制不应依赖普通应用的网络、模板或地图渲染时序。保护是分层的：AAOS 通过 CarService 权限、SELinux 和 VHAL 过滤保护车辆系统，SELinux 会按进程身份与资源标签执行强制访问控制，车辆控制器自身还应具备独立的安全机制。信息娱乐应用可以显示经过授权的数据，前提是定义好时间戳、过期判定和数据不可用状态，确保界面上的陈旧数据不参与车辆控制。

## 端到端诊断

### 分段定义延迟

同一个“点击后卡了”在两种平台上的阶段不同：

| 场景 | 建议拆分的时间段 |
|---|---|
| Android Auto 模板 | 车机输入传到手机 → 手机 host 调用应用 → 状态准备 → 模板返回 → host 生成车机界面 |
| AAOS 模板 | 车机输入 → host 调用应用 → 状态准备 → 模板返回 → host 绘制 |
| 地图 Surface | 输入或位置到达 → 路线或相机状态 → 提交渲染命令 → 图形缓冲区呈现 |
| 媒体控制 | host 命令 → MediaSession 回调 → 播放器状态 → 首个音频缓冲区 → 扬声器输出 |
| AAOS 启动/恢复 | 点火或系统恢复 → Android 系统可用 → 用户解锁或切换 → 应用会话 → 可用首屏 |

打点从应用侧开始：用 `Trace.beginSection()` 标记业务阶段和模板构建，网络层记录请求 ID 与状态版本，媒体层记录 MediaSession 命令与播放器事件；Android Auto 场景还要在手机与 DHU 或车机日志中记录同一个测试事件。合并这些时间线时，我们要小心时钟：本机单调时钟适合计算本机阶段耗时，不同设备的起点和漂移却各不相同，两端读数直接相减并不可靠，跨设备合并轨迹前需要共同事件或显式时钟同步，并记录偏移、漂移与对齐误差。Perfetto 的[时钟同步模型](https://perfetto.dev/docs/concepts/clock-sync)说明了以时钟快照建立时间域映射的方式；映射建立不起来时，就分别报告各端耗时和外部端到端测量。


### 工具选择


- **Android Auto**：先用 Desktop Head Unit（DHU，在电脑上模拟兼容车机的测试程序）验证连接、旋钮或触摸等输入和 host 行为，再到多款量产车机做只能从外部观察结果的黑盒延迟与断线实验。
- **AAOS**：用通用 Automotive Emulator 覆盖 API 和屏幕形态，用 OEM 系统镜像验证 CarService 与 VHAL 差异；GPU、音频、启动、休眠和高温表现仍需在量产硬件上测量。
- **Perfetto**：在应用所在设备采集 `sched`（线程调度）、Binder（进程间调用）、CPU 频率、FrameTimeline（帧生命周期）、SurfaceFlinger（系统合成显示服务）、网络和应用自定义轨道。模板 host 的进程轨道或车端接收与呈现轨道无法采集时，在报告中标出观测缺口。
- **CarWatchdog / `dumpsys`**：在 AAOS 上检查资源超限、CarService、电源策略、VHAL 和音频状态。`dumpsys` 用于输出系统服务的当前状态；可用命令和字段会随产品构建版本变化，需要在目标车机上确认。
- **Car App Library 测试**：单元测试 `Screen` 返回栈、模板类型、配额流程，以及不同 host 能力下的分支。

模拟器和 DHU 擅长重现逻辑与协议问题，量产车的 GPU、DSP、触控、无线干扰和散热则要真车才能代表。性能结论至少要在一台目标硬件上复核。


### 建议指标

平均值会掩盖尾部慢请求，报告时对每项指标记录 p50、p95、p99、样本数和异常条件。p50 是中位数，p95 和 p99 分别表示 95% 和 99% 的样本不超过该值，能够暴露少量慢请求：

- 首个模板可用时间（time to first template）；
- `onGetTemplate()` 执行时间；
- 导航 Surface jank 与可见区域变更后的重绘时间；
- 网络断开到离线 UI、恢复到新鲜数据的时间；
- 媒体命令响应、首个音频缓冲区和 underrun（播放器来不及供给数据造成的音频断续）；
- AAOS 从系统恢复到导航或媒体可用的时间；
- 每个驾驶周期的磁盘写入和缓存命中率；
- 温控状态、温控余量与开始降低画质或任务频率的节点。

## 跨车机适配检查表

### 客户端工程师

- 区分 Android Auto、AAOS 模板和 AAOS Activity 三种执行/渲染模型；
- 首模板只依赖本地快照，后台更新完成后再 `invalidate()`；
- 查询 Car App API 级别、host 支持的能力和 `ConstraintManager` 约束；
- Surface 重建时释放旧资源，按稳定区域与当前可见区域布局地图内容；
- 分别维护投射会话、业务网络和账号状态，避免其中一项变化时误置另外两项；
- 处理进程死亡、会话重建、离线、受限权限和不支持能力。

### AAOS 平台与 OEM 工程师

- 为模板 host、CarService、VHAL、音频服务和电源状态提供可对齐的性能轨迹；
- 验证启动、系统恢复、用户切换和关机准备阶段的超时预算；
- 配置并监控 CarWatchdog I/O，避免系统服务和地图缓存争抢闪存；
- 对车辆属性设置权限、更新率和单次回调数据量上限；
- 在车辆规定的工作温度范围、弱信号、多显示屏、多乘员区域和真实音频 DSP 上测试；乘员区域用于区分驾驶员与各座位能访问的显示和音频资源；
- 隔离安全相关控制与信息娱乐应用，使后者崩溃或阻塞时不会影响车辆控制。

## 结语

回到两条平台主线：Android Auto 的性能重心在手机客户端、投射 host 和车端呈现之间的衔接；AAOS 的范围还要算上车机 SoC（集成 CPU、GPU 等部件的主芯片）、CarService、VHAL、CarWatchdog 和车辆电源状态。分工上，模板应用负责快速提供稳定模型，host 负责生成符合驾驶限制的 UI，导航地图 Surface 和停驻 Activity 才进入应用自己的持续渲染流程。

车载性能优化应从责任划分和可观测范围开始：记录 Android、Car App、Jetpack 与 host 四类版本，按阶段测量模板、地图、网络、媒体和恢复路径，并为不支持、断线、休眠、热压力与进程死亡设计可恢复状态。这样得到的结论，才能跨车辆复查。

## 参考资料

### Android for Cars

- [Android for Cars 概览](https://developer.android.com/training/cars)
- [使用 Android for Cars App Library](https://developer.android.com/training/cars/apps/library)
- [Car App Library 术语与 host 模型](https://developer.android.com/training/cars/apps/library/glossary-concepts)
- [Android for Cars 最新变化](https://developer.android.com/training/cars/whats-new)
- [刷新 Template](https://developer.android.com/training/cars/apps/library/refresh-template)
- [Constraints API](https://developer.android.com/training/cars/apps/library/constraints-api)
- [Template restrictions](https://developer.android.com/training/cars/apps/library/template-restrictions)
- [Draw maps：Surface 与可见区域](https://developer.android.com/training/cars/apps/library/draw-maps)
- [构建导航应用](https://developer.android.com/training/cars/apps/navigation)
- [车载媒体应用](https://developer.android.com/training/cars/media)
- [Car app quality](https://developer.android.com/docs/quality-guidelines/car-app-quality)
- [Desktop Head Unit 测试](https://developer.android.com/training/cars/testing/dhu)
- [AAOS Emulator 测试](https://developer.android.com/training/cars/testing/emulator)

### AAOS 平台与 Android 17 源码

- [Android Automotive 与 Android Auto 的区别](https://source.android.com/docs/automotive/start/what_automotive)
- [VHAL 概览](https://source.android.com/docs/automotive/vhal)
- [车辆系统隔离](https://source.android.com/docs/automotive/security/vehicle_system_isolation)
- [CarWatchdog 系统健康监控](https://source.android.com/docs/automotive/watchdog/wd_system_health)
- [CarWatchdog 闪存写入监控](https://source.android.com/docs/automotive/watchdog/wd_flash_memory)
- [AAOS 电源管理](https://source.android.com/docs/automotive/power/power)
- [AAOS 电源策略](https://source.android.com/docs/automotive/power/power_policy)
- [AAOS 系统性能工具](https://source.android.com/docs/automotive/tools/sys-perf)
- [`CarPropertyManager.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/packages/services/Car/+/android-17.0.0_r1/car-lib/src/android/car/hardware/property/CarPropertyManager.java)
- [`CarPowerManager.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/packages/services/Car/+/android-17.0.0_r1/car-lib/src/android/car/hardware/power/CarPowerManager.java)
- [`CarWatchdogManager.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/packages/services/Car/+/android-17.0.0_r1/car-lib/src/android/car/watchdog/CarWatchdogManager.java)
- [`CarWatchdogService.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/packages/services/Car/+/android-17.0.0_r1/service/src/com/android/car/watchdog/CarWatchdogService.java)
- [`CarPowerManagementService.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/packages/services/Car/+/android-17.0.0_r1/service/src/com/android/car/power/CarPowerManagementService.java)
- [`IVehicle.aidl`（android-17.0.0_r1）](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/automotive/vehicle/aidl/android/hardware/automotive/vehicle/IVehicle.aidl)
