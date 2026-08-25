---
title: Accessibility、ContentCapture 与 Autofill 性能
chapter: '7.6'
section: '7.6'
status: finalized
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
tags:
- accessibility
- jank
- layout
- a11y
- performance
- rendering
- contentcapture
- autofill
- ipc
related_chapters:
- '7.1'
- '7.2'
- '2.4'
- '9.1'
- '3.1'
- '22.1'
- '1.3'
last_verified: '2026-08-02'
last_verified_against: AOSP android-17.0.0_r1；Android 17 / API 37 官方行为变更与 API 文档
confidence: medium-high
sources:
- type: aosp
  path: frameworks/base/core/java/android/view/accessibility/AccessibilityManager.java
- type: aosp
  path: frameworks/base/services/accessibility/java/com/android/server/accessibility/AccessibilityManagerService.java
- type: aosp
  path: frameworks/base/core/java/android/view/View.java (onInitializeAccessibilityNodeInfo)
- type: official
  path: https://developer.android.com/reference/android/view/accessibility/AccessibilityManager
- type: official
  path: https://developer.android.com/guide/topics/ui/accessibility/service
- type: aosp
  path: frameworks/base/core/java/android/view/accessibility/AccessibilityInteractionClient.java
- type: aosp
  path: frameworks/base/core/java/android/view/contentcapture/
- type: aosp
  path: frameworks/base/services/contentcapture/java/com/android/server/contentcapture/
- type: aosp
  path: frameworks/base/core/java/android/view/autofill/
- type: aosp
  path: frameworks/base/services/autofill/java/com/android/server/autofill/
- type: official
  path: developer.android.com/identity/autofill/autofill-optimize
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part2-performance/ch07-smoothness/13-accessibility-manager-performance.md
- src/part2-performance/ch07-smoothness/14-contentcapture-autofill-performance.md
---

# Accessibility、ContentCapture 与 Autofill 性能

Android 无障碍框架既支持屏幕阅读、开关控制、放大和语音控制，也被测试自动化等场景使用。分析性能时，不能只按“无障碍是否开启”分组：不同服务订阅的事件类型、读取窗口内容的能力、节点查询频率、输入模式和实现方式都有差异。

本文以 Android 17 / API 37 的 `android-17.0.0_r1` 为平台源码基线，讨论 framework、Binder、应用 UI 线程和无障碍服务进程。需要厂商内核 trace 标签才能识别的专有机制不在本文范围内。

Accessibility、ContentCapture 和 Autofill 都会读取或描述界面状态，但触发条件、数据范围和服务端组件不同。性能问题通常来自频繁事件、视图树遍历、跨进程调用或第三方服务处理。

## 无障碍事件、节点查询与服务开销

### 两条方向相反的性能链

Accessibility（无障碍）框架中与性能关系最密切的工作有两条路径：

- **事件上报**：应用把点击、焦点、文本、滚动或窗口内容变化通知给系统，系统再按照各项服务配置分发事件。
- **节点查询**：`AccessibilityService` 查询窗口或节点，目标应用在 ViewRoot 所在线程生成 `AccessibilityNodeInfo`，再通过回调返回结果。ViewRoot 是一棵界面树与窗口系统之间的连接点，普通应用中的这项工作通常运行在主线程消息循环上。

下图标出了两条路径的方向和实际等待结果的一方。

```mermaid
flowchart LR
    subgraph App["目标应用进程"]
        UI["View / Compose / WebView<br/>UI thread"]
        VR["ViewRootImpl"]
        AM["AccessibilityManager"]
        AICtrl["AccessibilityInteractionController<br/>ViewRoot looper"]
    end

    subgraph SS["system_server"]
        AMS["AccessibilityManagerService"]
        Conn["AccessibilityServiceConnection<br/>filter + delayed dispatch"]
    end

    subgraph Svc["AccessibilityService 进程"]
        Client["AccessibilityService callback"]
        AIC["AccessibilityInteractionClient<br/>cache + bounded wait"]
    end

    UI -->|"AccessibilityEvent"| VR --> AM
    AM -->|"oneway Binder"| AMS --> Conn -->|"Binder callback"| Client

    Client --> AIC
    AIC -->|"node request"| AMS
    AMS -->|"IAccessibilityInteractionConnection"| AICtrl
    AICtrl -->|"create node / provider / prefetch"| UI
    AICtrl -->|"result callback"| AIC
```

事件通过 `oneway` Binder 调用上报，应用发出事务后不会等待 `AccessibilityService` 处理完成。节点查询则由服务侧等待结果，目标应用在自己的 ViewRoot looper（消息循环）上生成节点。分析阻塞时要先判断走的是哪一条路径，不能把事件上报的异步关系套到节点查询上。

### 事件上报：oneway 不等于零成本

Android 17 的 `IAccessibilityManager.aidl` 将 `sendAccessibilityEvent()` 声明为 `oneway`。这里的 `oneway` 表示 Binder 调用方不等待同步返回，并不表示调用方没有工作。应用调用 `AccessibilityManager.sendAccessibilityEvent()` 时仍要完成以下步骤：

1. View 或 ViewParent 创建并补全 `AccessibilityEvent`；
2. `AccessibilityManager` 检查当前状态以及 `mRelevantEventTypes`，后者记录当前服务关心的事件类型；
3. 将事件对象序列化到 Parcel，也就是 Binder 用来传输参数的数据容器；
4. Binder 驱动接收这笔 `oneway` 事务并排队；
5. `system_server` 的 Binder 线程处理权限、用户、窗口和事件来源信息。

`oneway` 省掉的只是等待服务端处理完成的时间。事件构造、字符串复制、Parcel 写入和 Binder 入队仍由调用链承担；高频事件仍会消耗 UI 线程 CPU、Binder 传输缓冲区和 `system_server` 资源。

#### system_server 怎样过滤和排队

`AccessibilityManagerService.sendAccessibilityEvent()` 会校验调用用户和包名，更新活动窗口和无障碍焦点；必要时还会让 WindowManager 重新计算可访问窗口。随后，它会遍历当前用户已经绑定、也就是当前已连接到系统的无障碍服务。

每个 `AbstractAccessibilityServiceConnection` 会按以下条件决定是否接收：

- 服务声明的 `eventTypes`；
- 服务声明的 `packageNames`；
- 事件来源是否被标记为对无障碍重要；
- 服务是否要求 `FLAG_INCLUDE_NOT_IMPORTANT_VIEWS`；
- 敏感事件是否只允许 `isAccessibilityTool=true` 的服务；
- 当前服务是否具备相应的访问权限。

符合条件的事件会为该服务复制一份，再投递到 `mEventDispatchHandler`。当 `notificationTimeout > 0` 时，同一服务通常只保留同类型事件中最新的一条待发送记录。Android 17 对 `TYPE_WINDOW_CONTENT_CHANGED` 使用单独分支，不通过这组 `mPendingEvents` 合并，因此不能假定所有内容变化都会按同一种规则去重。

View 侧还有一层内容变化节流。`ViewRootImpl.SendWindowContentChangedAccessibilityEvent` 会合并可兼容的 change types（变化类型），并按照 `ViewConfiguration.getSendRecurringAccessibilityEventsInterval()` 给出的间隔安排发送。对象复用只减少对象分配，节流则减少实际发送次数；看到 `AccessibilityEvent.obtain()` 或 `recycle()`，不能据此判断事件已经批量合并。

#### 高频从哪里产生

| 事件类别 | 常见来源 | 分析重点 |
|---|---|---|
| `TYPE_VIEW_SCROLLED` | 列表、滚动容器、虚拟节点 | 每次滚动是否都附带大量文本，或触发额外节点查询 |
| `TYPE_WINDOW_CONTENT_CHANGED` | 子树、文本、状态、内容描述变化 | change type、source、ViewRoot 合并情况 |
| `TYPE_VIEW_TEXT_CHANGED` | 输入框、编辑器、自定义文本控件 | 是否手动重复发送，Parcel 文本是否过大 |
| 焦点事件 | 键盘焦点、无障碍焦点、虚拟节点 | touch exploration（触摸探索）与焦点移动节奏 |
| 窗口事件 | Activity、Dialog、PIP、系统窗口变化 | WMS 可访问窗口计算与服务窗口查询 |

事件数量只反映调用流量。单个事件携带的文本长度、事件是否触发后续节点查询、服务能否命中缓存，以及目标应用生成节点的开销，都会影响最终表现。

### 节点查询：工作落在目标应用的 ViewRoot looper

`AccessibilityService` 调用 `getRootInActiveWindow()`、`event.source`、`findFocus()` 或节点查找 API 时，`AccessibilityInteractionClient` 会先查询当前服务连接对应的 `AccessibilityCache`。命中缓存即可直接返回；cache miss（缓存未命中）时才会发起跨进程请求。

请求先由 `AccessibilityServiceConnection` 找到目标窗口的 `IAccessibilityInteractionConnection`，随后进入目标应用的 `AccessibilityInteractionController`。这个 controller 使用 `ViewRootImpl.mHandler` 所在的 looper，因此常规 View 树的节点生成会与应用的 UI 工作共享线程。

节点创建有两种入口：

- 普通 View 调用 `View.createAccessibilityNodeInfo()`，进而执行 `onInitializeAccessibilityNodeInfo()`；
- 暴露虚拟节点的控件调用 `AccessibilityNodeProvider.createAccessibilityNodeInfo()`。虚拟节点没有一一对应的真实 View，常见于画布、自定义控件和 WebView 内部内容。

这也解释了 trace 中的一种常见现象：应用没有主动刷新 UI，主线程上仍出现无障碍节点构造。触发查询的可能是另一个进程中的 `AccessibilityService`，也可能是测试工具使用的 `UiAutomation`。

#### 查询不会固定遍历整棵树

Android 17 提供多种 prefetch（预取）策略，包括 ancestors（祖先节点）、siblings（同级节点），以及 hybrid、depth-first、breadth-first 三种后代节点遍历顺序。源码还设置了三项边界：

- 单次预取上限为 `MAX_NUMBER_OF_PREFETCHED_NODES = 50`；
- 可中断的 prefetch 会在 ViewRoot handler 中已有用户交互消息等待时停止；
- 窗口正在滚动时，`AccessibilityInteractionClient` 会清除 prefetch flags（预取标志）。

因此，不能把一次 `getRootInActiveWindow()` 查询直接等同于递归构造整棵 View 树。定位成本时，需要同时记录请求 API、prefetch flags、缓存是否命中、虚拟节点 provider 和实际返回的节点数。

服务侧的 `AccessibilityInteractionClient` 最多等待 5000 ms 获取查询结果，这段等待发生在发起查询的服务线程。目标应用承担的是另一类风险：ViewRoot looper 上增加了节点创建任务，可能让同一线程上的 input（输入分发）、traversal（测量、布局与绘制）或 frame callback（逐帧回调）延后执行。

### 成本应按四个进程位置拆开

| 位置 | 工作 | 卡顿表现 |
|---|---|---|
| 目标应用 | 事件构造与 Parcel 写入；节点创建、provider 查询、prefetch | UI 线程 CPU 增长，frame callback 或 traversal 排队 |
| `system_server` | 权限过滤、窗口状态维护、bound service 遍历、事件复制与排队 | Binder 或 `system_server` CPU 上升、锁竞争 |
| `AccessibilityService` | `onAccessibilityEvent()`、cache miss 后的查询、业务处理 | 服务主线程阻塞、事件积压、反馈延迟 |
| Binder 与调度 | oneway event、query request、result callback | 线程唤醒、Parcel 处理开销、目标线程调度延迟 |

同时开启两个服务，并不意味着成本必定变成一个服务时的两倍。相比服务数量，`eventTypes`、`packageNames`、`notificationTimeout`、读取窗口内容的 capability（能力声明）、缓存使用方式和查询策略更能解释差异。

Touch exploration（触摸探索）、按键过滤、手势观察和放大还会改变输入处理链。遇到点击延迟或手势行为变化时，应分别检查输入过滤和 `AccessibilityEvent` / `AccessibilityNodeInfo` 开销；按键过滤的系统路径见 [3.1 Input 分发、拦截与安全边界](../../part1-fundamentals/ch03-input/01-input-dispatch-interception-security.md)。

### 应用侧：保持语义正确，再去掉无意义工作

性能优化不能以移除可操作节点、隐藏状态或停止发送必要事件为代价。无障碍功能一旦退化，依赖屏幕阅读器、语音控制或开关控制的用户可能无法继续完成操作。

#### `importantForAccessibility` 只处理装饰与重复语义

纯装饰图片、分隔线，以及语义已经由父控件完整表达的重复子元素，适合设置 `importantForAccessibility="no"`。`NO_HIDE_DESCENDANTS` 会让整个子树不再出现在无障碍节点树中，只有父节点能提供等价说明和操作时才可使用。

下面的 XML 仅把无交互、无信息价值的装饰图排除在无障碍树外。

```xml
<ImageView
    android:id="@+id/cardDecoration"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:importantForAccessibility="no"
    android:src="@drawable/card_decoration" />
```

这项设置只应用于减少没有信息或操作价值的节点。按钮图标、错误提示、金额和开关状态等用户需要感知的信息不能照此隐藏。

#### 节点回调内只读取已准备好的状态

滚动、焦点移动或自动化查询期间，`onInitializeAccessibilityNodeInfo()` 和 `AccessibilityNodeProvider` 都可能被频繁调用。这些回调通常处在目标应用的 UI 工作路径上，不应访问网络、磁盘或数据库，也不应执行大型 JSON 解析、位图分析或全量集合排序。

下面的自定义 View 在业务状态变化时预先生成语义文本，节点查询时只需读取已有字段。API 34 及以上版本还可以声明高频内容变化的最小通知间隔。

```kotlin
class PriceTickerView(context: Context) : View(context) {
    fun updatePrice(price: BigDecimal, change: BigDecimal) {
        contentDescription = formatPriceForAccessibility(price, change)
        invalidate()
    }

    override fun onInitializeAccessibilityNodeInfo(info: AccessibilityNodeInfo) {
        super.onInitializeAccessibilityNodeInfo(info)
        info.className = PriceTickerView::class.java.name

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            info.minDurationBetweenContentChanges = Duration.ofMillis(500)
        }
    }
}
```

示例将格式化工作放在业务状态更新处。`View.setContentDescription()` 会在描述变化时通知无障碍框架，后续节点初始化直接使用 View 已保存的属性。`AccessibilityService` 可以读取节点声明的最小间隔，并据此限制来自该节点的内容变化事件频率。`setMinDurationBetweenContentChanges()` 适合进度、计时器、行情等持续变化、但无须逐次朗读的节点。间隔应按照用户能够理解的更新节奏设置；焦点、错误、可操作状态和关键结果仍需及时上报。

不要为了批量更新，临时将真实内容设置成 `NO_HIDE_DESCENDANTS`。这会让当前焦点节点消失，改变节点树结构，还可能额外触发内容变化。列表应使用增量数据更新并提供正确的 change type，让 ViewRoot 或控件库使用已有的事件合并机制。

#### RecyclerView

RecyclerView 只为当前附着到窗口且可访问的 item（列表项）暴露节点。视图回收机制并不意味着每次查询都会构造全部数据项，应用侧更常见的额外开销来自以下做法：

- item delegate（列表项无障碍代理）动态拼接复杂描述；
- 每次 bind（绑定数据）都重复安装 delegate，或创建大量 action（无障碍操作）；
- 使用全量 `notifyDataSetChanged()`，使语义信息和可见内容一起大范围失效；
- item 的语义状态没有随数据更新，导致服务反复调用 `refresh()`。

可以使用 `DiffUtil` / `ListAdapter` 精确更新发生变化的列表项，复用稳定的 delegate，并在业务状态改变时同步更新简洁的 `stateDescription`、文本和 action。

### Compose：按逻辑控件设计 semantics tree

Compose 会在 UI 树之外维护一棵 semantics tree（语义树），供无障碍服务和测试工具读取。只有带语义属性的 layout node（布局节点）才会成为 semantics node；在 `Column` 上添加 `Modifier.semantics {}`，并不表示框架每次都会无条件递归重建这个 `Column` 的全部子树。

分析时要区分：

- **unmerged tree（未合并树）**：保留各个 semantics node，`AccessibilityService` 会结合 `mergeDescendants` 自行处理；
- **merged tree（合并树）**：测试 API 默认使用的视图，会按照 `mergeDescendants` 和 `clearAndSetSemantics` 简化节点。

Material 与 Foundation 中的 `Button`、`clickable`、`toggleable` 已经提供常用语义和合并规则。自定义组件可以减少重复或没有信息价值的节点，但仍要把一项逻辑控件需要的说明和操作完整保留下来：

- 只有装饰性内容才使用 `hideFromAccessibility()` 或空描述；
- 一组文字、图标和单一点击动作可按逻辑合并；
- 子项有独立动作时保留独立节点；
- `clearAndSetSemantics` 会覆盖无障碍服务和测试工具随后看到的子树语义，使用前要验证 TalkBack、Switch Access、Voice Access 以及自动化测试；
- 动画每帧变化但用户无需逐帧感知的数值，不要每帧写入语义属性。

Compose 来自 AndroidX 依赖，其性能行为应按照项目锁定的 Compose 版本核对，不能用 Android 17 的平台 tag 代替库版本。

### AccessibilityService 开发者：缩小订阅与查询范围

如果可以修改 `AccessibilityService` 的实现，通常应先检查服务配置和查询策略。

下面的配置表示：服务只接收目标包中的点击和窗口切换事件，同时声明可以读取窗口内容。

```xml
<accessibility-service
    android:accessibilityEventTypes="typeViewClicked|typeWindowStateChanged"
    android:accessibilityFeedbackType="feedbackSpoken"
    android:notificationTimeout="100"
    android:packageNames="com.example.target"
    android:canRetrieveWindowContent="true"
    android:isAccessibilityTool="true" />
```

如果服务确实需要支持所有应用，就不能为了减少开销随意填写 `packageNames`。配置范围应与产品功能一致；不需要读取窗口内容时，也不应请求对应的 capability（能力声明）。

服务侧建议遵守以下约束：

1. `eventTypes` 只订阅功能需要的类型，运行时场景变化可用 `setServiceInfo()` 调整。
2. 为可合并事件设置合理的 `notificationTimeout`，同时根据 Android 17 对 `TYPE_WINDOW_CONTENT_CHANGED` 的特殊处理单独实测。
3. 让 `onAccessibilityEvent()` 尽快返回；网络、磁盘、模型推理和大规模解析转到工作线程执行。
4. 优先使用事件已有字段和明确的 source（来源节点）；cache miss 时再发起节点查询。
5. 避免每个事件都调用 `getRootInActiveWindow()`，也不要从 root 反复扫描寻找同一个节点。
6. 先复制跨线程处理需要的字符串、ID 和业务值，不要把只在回调期有效的对象直接交给长时间任务持有。
7. 记录 query API、cache hit / miss（缓存命中 / 未命中）、返回节点数和业务触发原因，以便与目标应用的 trace 对齐。

服务主线程等待节点查询结果期间，该服务收到的其他事件也可能排队。频繁查询 root 节点既会增加目标应用的 UI 线程工作，也会延迟服务自身的反馈。

### 测量：不要靠“开关前后感觉更卡”

#### A/B 条件

保持设备、build（系统构建版本）、刷新率、温度、账号数据和交互脚本一致，至少比较以下四组条件：

1. 没有目标服务；
2. 只启用目标服务；
3. 目标服务与用户常用服务共同启用；
4. 服务功能不变，但减少 event types（事件类型）、节点查询和后台工作的版本。

如果测试需要停用用户的辅助服务，只能在受控测试设备上进行，并确保用户明确知情。线上产品不能为了改善帧率而自动关闭或绕过 `AccessibilityService`。

#### Perfetto：定位线程和帧

系统 trace 至少应采集 FrameTimeline、应用主线程、`system_server`、`AccessibilityService` 进程、Binder driver、sched、freq，以及应用自定义的业务 slice。其中 sched / freq 分别记录线程调度和 CPU 频率，slice 是应用标注的一段工作区间。分析时检查以下时序：

- App frame（应用帧）迟到前，是否出现节点查询任务或耗时较长的 `onInitializeAccessibilityNodeInfo()`；
- 事件上报的 oneway Binder 数量与 Parcel 大小是否异常；
- `system_server` 是否忙于窗口计算、服务过滤或其他锁；
- 服务主线程是否停在 `AccessibilityInteractionClient` 中等待结果；
- 节点结果返回后，服务是否立即进入长 CPU、I/O 或 Binder 工作。

`BinderProxy.transactNative` 只能证明这里发生了 Binder 调用，无法单独说明调用目的。事件上报和节点查询的方向相反，需要结合 interface / method（接口与方法）、调用进程和回调时序识别具体路径。

#### Android 17 accessibility trace

`userdebug` 或 `eng` 构建可以使用专用的 accessibility trace；这两类构建包含面向调试和工程验证的系统能力。下面的命令只启用相关接口类型，避免其他无障碍调用占满 trace。

```bash
adb root
adb shell cmd accessibility start-trace -t \
  IAccessibilityManager \
  IAccessibilityServiceConnection \
  IAccessibilityInteractionConnection \
  IAccessibilityInteractionConnectionCallback \
  AccessibilityService

# 复现目标操作

adb shell cmd accessibility stop-trace
adb pull /data/misc/a11ytrace/a11y_trace.winscope
```

Android 17 源码明确禁止在面向普通用户发布的 user build 上启用这项 trace。停止命令会异步写入 Winscope 文件，拉取前应先确认文件已经生成。Tracing 会记录调用参数、线程和调用栈，本身也会增加运行开销，因此只适合短时间定位问题。

#### dumpsys：确认服务配置，不统计事件速率

`adb shell dumpsys accessibility` 可以查看当前用户处于 bound、enabled、binding 或 crashed 状态的服务，也就是已连接、已启用、正在连接或已崩溃的服务。每个 bound service 的 dump 会列出 label、feedback type、capabilities、event types、`notificationTimeout` 和 accessibility button 请求。

Android 17 的 AOSP dump 没有通用的“Event Dispatch Statistics”或“Interaction Connection Pool”计数器。厂商版本如果扩展了字段，应在报告中标明 build；在 AOSP 设备上，需要通过 trace、自有计数或服务日志测量事件率和查询率。

### 归因表

| 现象 | 还缺的证据 | 更可能的负责位置 |
|---|---|---|
| App 主线程长时间执行节点回调 | 查询来源、node / provider、prefetch、返回数量 | App 自定义 View、Compose adapter 或 WebView provider |
| App 有大量短 oneway event transaction | 事件类型、source、文本大小、ViewRoot 合并 | App 事件设计或高频状态更新 |
| 服务主线程停在 `AccessibilityInteractionClient` | cache miss、目标窗口、callback 时间 | 目标 App UI、`system_server` 路由或服务查询策略 |
| 服务收到事件后长时间运行 | `onAccessibilityEvent()` 后续 CPU/I/O | AccessibilityService 实现 |
| `system_server` 中 A11yMS 段变长 | bound service 数、窗口计算、锁和 CPU 调度 | framework、WMS 或设备系统实现 |
| 开启 touch exploration 后输入节奏变化 | `InputFilter`、手势 / 按键配置、事件与帧 | Accessibility input path（无障碍输入路径），不能只看节点树 |

如果现有证据只能证明“无障碍开启时更慢”，还无法完成归因。报告中应写清事件、查询、节点、服务或输入中的哪条路径发生了变化。

### 运行时上下文与隐私

`AccessibilityManager.isEnabled()` 用来查询框架当前是否启用了无障碍事件发送。Android 17 的 Javadoc 明确提醒，应用不应根据这个布尔值切换产品 UI 或交互路径；专门设置的分支往往测试不足，容易让辅助技术用户进入维护较差的体验。

性能监控可把以下信息作为受控实验上下文：

- `accessibility enabled` 状态；
- `touch exploration enabled` 状态；
- 当前页面是否包含 SurfaceView、WebView、Compose 或大量虚拟节点；
- 测试设备上启用服务的数量和反馈类型。

`getEnabledAccessibilityServiceList()` 会发起跨 Binder 查询，不应在每帧或高频埋点中调用。启用哪些服务还可能暴露敏感的设备使用状态；线上采集前要经过隐私评审，优先记录匿名化的能力类别和数量，不上传服务组件名。

### Android 12—17 版本边界

- **Android 12 / API 31**：`AccessibilityServiceInfo.isAccessibilityTool()` 成为公开 API，系统可以区分面向残障用户的辅助工具和其他服务。
- **Android 13 / API 33**：新增节点 prefetch strategy 与 `MAX_NUMBER_OF_PREFETCHED_NODES = 50`；多项 `obtain()` / `recycle()` 对象池 API 被废弃。
- **Android 14 / API 34**：新增 `setMinDurationBetweenContentChanges()` 和 accessibility data sensitive（无障碍数据敏感）能力，为高频内容节流和敏感事件过滤提供公开接口。
- **Android 17 / API 37**：按 `android-17.0.0_r1` 核对。事件仍通过 oneway `sendAccessibilityEvent()` 上报；服务连接仍按配置过滤/延迟；节点请求仍进入目标 ViewRoot looper，并受缓存、prefetch 策略和 50 节点上限约束。

平台版本无法代替 `AccessibilityService`、TalkBack、Compose、WebView 和厂商 framework 的具体版本。任何以百分比表示的性能结论都应附带设备、服务版本、页面、交互过程和 trace 条件，不能直接套用到其他设备。

### 无障碍源码与资料

- [`AccessibilityManager.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/accessibility/AccessibilityManager.java) 与 [`IAccessibilityManager.aidl`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/accessibility/IAccessibilityManager.aidl)：客户端状态、相关事件过滤和 `oneway` 上报。
- [`AccessibilityManagerService.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/accessibility/java/com/android/server/accessibility/AccessibilityManagerService.java)：事件安全检查、窗口更新与 bound service 分发。
- [`AbstractAccessibilityServiceConnection.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/accessibility/java/com/android/server/accessibility/AbstractAccessibilityServiceConnection.java)：事件类型、包名、敏感数据、重要性与 `notificationTimeout` 处理。
- [`AccessibilityInteractionClient.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/accessibility/AccessibilityInteractionClient.java) 与 [`AccessibilityInteractionController.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/AccessibilityInteractionController.java)：cache、5000 ms 等待、ViewRoot handler、节点创建和 prefetch。
- [`ViewRootImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java) 与 [`View.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/View.java)：事件上报、窗口内容变化合并与节点初始化。
- [`AccessibilityNodeInfo.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/accessibility/AccessibilityNodeInfo.java) 与 [`AccessibilityServiceInfo.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/accessibilityservice/AccessibilityServiceInfo.java)：prefetch、最小内容变化间隔、事件订阅与服务配置。
- [`AccessibilityTraceManager.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/accessibility/java/com/android/server/accessibility/AccessibilityTraceManager.java) 与 [`AccessibilityController.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/AccessibilityController.java)：trace 命令、user build 限制与输出文件。
- [AccessibilityManager API](https://developer.android.com/reference/android/view/accessibility/AccessibilityManager)、[AccessibilityServiceInfo API](https://developer.android.com/reference/android/accessibilityservice/AccessibilityServiceInfo) 与 [创建 AccessibilityService](https://developer.android.com/guide/topics/ui/accessibility/service)：公开接口契约。
- [Compose semantics](https://developer.android.com/develop/ui/compose/accessibility/semantics) 与 [merging/clearing](https://developer.android.com/develop/ui/compose/accessibility/merging-clearing)：merged / unmerged tree 和语义边界。


## 内容捕获、自动填充与视图结构传输

无障碍服务面向交互辅助，ContentCapture 和 Autofill 面向内容理解与字段填充。三者都可能遍历视图结构，但不能共用同一开关或归因。

ContentCapture 和 Autofill 都会读取 View 的结构化信息，但用途并不相同：ContentCapture 持续向系统选定的服务报告页面内容变化，Autofill 则在需要填充字段时采集页面快照并请求候选数据。它们的触发条件、数据模型和进程路径也各不相同。本文以 Android 17 / API 37 的 `android-17.0.0_r1` 为平台源码基线；当密码管理器、IME 和 WebView 同时参与时，需要分别判断每条路径产生了什么开销。

### 三个容易混在一起的数据模型

分析前先区分三套框架及其数据对象：

| 框架 | 主要数据对象 | 生成方式 | 常见消费者 |
|---|---|---|---|
| Accessibility | `AccessibilityEvent`、`AccessibilityNodeInfo` | 事件上报；服务按需查询节点 | TalkBack、Switch Access、自动化工具 |
| ContentCapture | `ContentCaptureEvent`、轻量 `ViewNode` / `ViewStructure` | 初始结构报告；View 出现、消失、文本变化等增量事件 | 系统选中并授权的 `ContentCaptureService` |
| Autofill | `AssistStructure`、`FillRequest` | Autofill 会话触发后采集应用窗口结构 | `AutofillService`、密码管理器、Credential Manager 相关提供方 |

ContentCapture 的常规采集不依赖 `AccessibilityEvent`，也不会在每次增量变化时重新创建完整的 `AssistStructure`。Autofill 的结构快照才由 `AssistStructure` 承载。如果把三者都称为“无障碍全树扫描”，就无法判断请求由谁发起、工作在哪个线程执行，也无法找到对应的优化位置。

下图展示了 Android 17 中 ContentCapture 和 Autofill 的主要调用方向。

```mermaid
flowchart LR
    subgraph App["目标应用进程"]
        Draw["首个成功 draw"]
        CCUI["UI thread<br/>ContentCapture ViewStructure"]
        CCBG["BackgroundThread<br/>queue / merge / flush"]
        Focus["View focus / requestAutofill"]
        AFM["AutofillManager"]
        ATH["ActivityThread<br/>handleRequestAssistContextExtras"]
        AS["AssistStructure<br/>View traversal"]
    end

    subgraph System["system_server"]
        CCMS["ContentCaptureManagerService<br/>session broker"]
        AFMS["Autofill Session"]
        ATM["ActivityTaskManager<br/>assist request"]
    end

    subgraph Providers["服务进程"]
        CCS["ContentCaptureService<br/>main looper"]
        AFS["AutofillService / password provider"]
        IME["IME inline suggestions"]
    end

    Draw --> CCUI --> CCBG
    CCMS -->|"direct service binder"| CCBG
    CCBG -->|"oneway sendEvents"| CCS

    Focus --> AFM
    AFM -->|"oneway call + result receiver"| AFMS
    AFMS --> ATM --> ATH --> AS
    AS --> ATM --> AFMS --> AFS
    AFMS <-->|"inline request / response"| IME
```

ContentCapture 会话由 `system_server` 协调，建立连接后，应用通过服务提供的 direct Binder 直接发送事件批次，无须让每一批都再次经过 `system_server`。Autofill 的结构请求则由 `system_server` 发回应用，在应用主线程采集完成后再送给数据提供方。两条路径可能在同一时间窗口出现，但这并不能证明它们重复采集了同一份结构。

### ContentCapture：初始 UI 遍历与后台事件管线

#### `system_server` 负责会话，事件直送服务

Activity 创建时，`ContentCaptureManager` 通过 `IContentCaptureManager.startSession()` 请求 `ContentCaptureManagerService` 建立会话。这个 AIDL 接口是 `oneway`，结果另行通过 `IResultReceiver` 返回。服务端完成权限、用户、组件和 allowlist（允许列表）检查后，把 `IContentCaptureDirectManager` Binder 交给应用。

后续事件不必逐批经过 `system_server`。`MainContentCaptureSession` 调用 direct interface（直连接口）的 `sendEvents()`，把装有一批 `ContentCaptureEvent` 的 `ParceledListSlice` 直接发往 `ContentCaptureService`；这个接口同样是 `oneway`。

`oneway` 只表示发送方不等待服务方法处理结束。应用仍要创建事件、复制文本、写入 Parcel，并把 transaction（事务）放进 Binder 队列。服务处理过慢还会消耗异步 Binder 配额和系统 CPU，因此异步调用同样需要计入成本。

#### 初始结构生成仍在 UI 线程

Android 17 的 `ViewRootImpl` 会在窗口首帧成功 draw（绘制）后执行一次 `performContentCaptureInitialReport()`。它先调用根 View 的 `dispatchInitialProvideContentCaptureStructure()`，再由 `ViewGroup.dispatchProvideContentCaptureStructure()` 遍历允许采集的子节点。每个节点通过 `onProvideContentCaptureStructure()` 填充自己的结构信息。

这段工作在应用 UI 线程上执行，并且仍属于 ViewRoot 的一次 traversal（测量、布局与绘制）路径。自定义 View 如果在回调中访问磁盘、数据库或网络，或者临时解析大型对象，就会直接延长这次主线程任务。

遍历范围由 `importantForContentCapture` 和 View 的启发式判断共同决定。`no` 只排除当前节点，框架仍可能访问它的子节点；`noExcludeDescendants` 表示整棵子树都不参与采集。父节点一旦使用 exclude-descendants（排除后代）模式，子节点即使显式设置为重要，也无法重新加入这次采集。

#### 后续变化按 traversal 批量转交

View 的出现、消失和交互变化会先记录在 `AttachInfo` 中。`ViewRootImpl` 在 traversal 结束阶段调用 `notifyContentCaptureEvents()`，主会话随后在 UI Handler 上准备对应的 `ViewStructure`。读取完 View 属性后，事件进入应用进程的 `BackgroundThread`：

- `ConcurrentLinkedQueue` 接收来自不同线程的事件；
- 文本 composing 事件，也就是输入法仍在组合候选文本期间产生的变化，可以与同一节点的待发事件合并；
- 连续的 disappeared 事件可合并为一个带多个 ID 的事件；
- buffer 达到 `maxBufferSize`，或遇到会话边界、显式 flush、idle timeout、text-change timeout 时发送；这里的 flush 表示立即提交当前缓冲批次；
- 批次通过 direct `oneway` Binder 进入 ContentCaptureService。

分析 ContentCapture 性能时，应分别观察 UI 线程上的 `ViewStructure` 准备，以及后台线程上的事件合并、Parcel 写入和 Binder 发送。只看到其中一侧，无法完整判断开销发生在哪里。

#### 服务回调运行在服务主线程

`ContentCaptureService` 的 direct Binder stub（接收 Binder 调用的服务端对象）拿到批次后，会把消息投递到服务进程的 main looper，再逐个调用 `onContentCaptureEvent()`。如果服务在回调中执行大规模解析、同步 I/O 或模型推理，它自己的事件队列就会延迟。应用侧使用的是 `oneway`，所以这种积压通常表现为服务处理滞后、异步 Binder 压力或系统 CPU 上升，并不表示应用正在同步等待服务方法返回。

ContentCapture 没有一套适用于所有设备的结构大小或耗时阈值。节点字段、文本长度、虚拟层级、更新频率、服务 options 和设备 CPU 都会影响结果；“500 个 View 固定需要 30–100 ms”这类数字不能直接用于其他页面或设备。

### Autofill：会话等待、AssistStructure 与提供方响应

#### 焦点进入才是常见入口

标准 View 获得焦点时，会间接调用 `AutofillManager.notifyViewEntered()`；自定义控件也可以在用户发起自动填充操作时调用 `requestAutofill()`。Autofill 通常从这类焦点或显式请求开始，并不会在每次 View 树构建完成后自动采集完整结构。

`IAutoFillManager` 在 Android 17 中是 `oneway` 接口，但 `AutofillManager` 的 `addClient()` 和 `startSession()` 会附带 `SyncResultReceiver`，通过另一个结果通道等待会话建立完成，超时常量为 5000 ms。焦点事件通常来自 UI 线程，因此 trace 中如果出现 `SyncResultReceiver` 等待，需要沿 Binder flow（跨进程调用流）继续检查 `system_server` 创建 Autofill 会话的过程。

5000 ms 是异常情况下的保护上限，并非正常延迟目标。接口契约也无法推出“每次 Binder 约 5–10 ms”之类的固定耗时。

#### AssistStructure 在应用主线程采集

Autofill Session 需要新响应时，会通过 `ActivityTaskManager.requestAutofillData()` 请求应用提供 assist data（辅助上下文数据）。应用的 `ActivityThread.handleRequestAssistContextExtras()` 在主线程创建 `AssistStructure`，也就是描述当前窗口和可填充节点的结构快照。构造时会枚举 Activity 的 ViewRoot，并调用根 View 的 `dispatchProvideAutofillStructure()`：

1. `View.onProvideAutofillStructure()` 写入资源 ID、尺寸、可见性、autofill type、hints、value 等字段；
2. `View.onProvideAutofillVirtualStructure()` 允许 WebView、自绘控件等暴露没有对应实体 View 的虚拟节点；
3. `ViewGroup` 选择需要进入结构的子节点并递归采集；
4. `ActivityThread` 记录 acquisition start / end（采集开始 / 结束），再把结构的传输通道报告给 `system_server`。

普通节点回调与应用 UI 工作共享线程。虚拟层级也可以用 `asyncNewChild()` / `asyncCommit()` 在异步任务中补充；`AssistStructure.waitForReady()` 最多等待 5000 ms，超过时限仍未提交就会放弃该结构。

#### 大结构采用分段传输

`AssistStructure` 不要求把整个对象装进一次 Binder transaction。Android 17 的 `ParcelTransferWriter` 在 Parcel 达到 `IBinder.MAX_IPC_SIZE` 边界后写入 continuation token（续传令牌），接收方再凭这个令牌请求下一段。`Session.AssistDataReceiver` 调用 `ensureDataForAutofill()` 取回全部数据，建立代表本次填充上下文的 `FillContext`，然后创建 `FillRequest`。

分段传输可以避免单次 transaction 超过 IPC 大小上限，但遍历、字段复制、序列化、反序列化和多次 Binder 往返仍然存在。报告应记录这次结构包含的 window 数、node 数、文本规模、采集时长和分段次数，不应套用“中等页面 1–5 MB”之类的固定估计。

#### 密码管理器与 IME 不会各扫一遍树

用户选中的 `AutofillService` 通常由密码管理器提供。IME inline suggestions（输入法内联建议）只是展示 Autofill 数据集的一种界面路径：Autofill Session 先向 IME 获取 `InlineSuggestionsRequest`，将它随 `FillRequest` 交给提供方，再把 inline response 送回 IME 显示。

这组协作会增加 `system_server`、提供方、IME 和渲染服务之间的 IPC 与等待，也可能与键盘显示动画重叠。不过，IME 不需要为此独立创建第二份 `AssistStructure`。Android 17 的主、次提供方路径也可以复用已有的 `FillContext`，所以提供方数量不能直接换算成应用 View 树的遍历次数。

IME 自身的启动、`InputConnection` 和窗口动画问题见 [3.5 InputMethodManager 与软键盘性能](../../part1-fundamentals/ch03-input/05-input-method-manager-performance.md)。Binder 等待和异步事务容量可结合 [1.3 Android IPC 全景与 Binder 性能](../../part1-fundamentals/ch01-architecture/03-ipc-binder-performance.md) 继续分析。

### 把成本按线程和进程拆开

| 位置 | ContentCapture | Autofill | trace 中的表现 |
|---|---|---|---|
| 应用 UI 线程 | 初始结构遍历；动态节点的 `ViewStructure` 准备 | 等待会话结果；遍历 `AssistStructure` | frame / traversal 延长、主线程 waiting 或 Runnable |
| 应用后台线程 | 事件合并、buffer、Parcel、direct Binder | 通常不负责遍历标准 View 的 `AssistStructure` | `BackgroundThread` CPU、Binder transaction |
| `system_server` | 会话、allowlist、服务连接 | Session、assist request、`FillContext`、IME 协调 | Autofill / ATM handler、Binder、锁与调度 |
| `ContentCaptureService` | 主线程逐个处理增量事件 | 无 | 服务 main looper 积压 |
| `AutofillService` / 密码提供方 | 无 | 解析 `FillRequest`、生成 dataset、处理认证 | provider CPU / I/O、response latency |
| IME | 无 | inline request、展示与交互 | IME main/render、窗口动画 |

应用 UI 线程出现一次较长的 traversal 时，应先确认触发者是 ContentCapture 初始报告还是 Autofill assist request。后台 `sendEvents()` 变长时，则要检查事件批次、Parcel 和 Binder 异步压力。如果提供方响应较慢但 App frame 正常，用户感受到的是填充建议出现得晚，不应记作应用渲染卡顿。

### 应用侧结构设计

#### 让登录字段保留明确语义

下面的 XML 为登录字段提供稳定的 hints（字段类型提示），并将纯装饰图片从 ContentCapture 和 Autofill 两套结构中排除。

```xml
<LinearLayout
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:orientation="vertical">

    <ImageView
        android:layout_width="match_parent"
        android:layout_height="96dp"
        android:importantForAutofill="no"
        android:importantForContentCapture="no"
        android:src="@drawable/login_decoration" />

    <EditText
        android:id="@+id/username"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:autofillHints="username"
        android:importantForAutofill="yes"
        android:inputType="textEmailAddress" />

    <EditText
        android:id="@+id/password"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:autofillHints="password"
        android:importantForAutofill="yes"
        android:inputType="textPassword" />
</LinearLayout>
```

`autofillHints` 帮助提供方稳定识别字段用途，并不会让系统跳过结构采集。需要自动填充的用户名、密码、地址和银行卡字段，不应为了缩小结构而设置为 `no`。

只有整块 UI 都没有可填充字段或可采集内容时，才适合评估在容器上使用 `noExcludeDescendants`。ContentCapture 会据此排除整棵子树，之后在其中新增的有效内容也不会被服务看到。Autofill 的同名模式表达相同意图，但请求 flags 和系统 options 仍可能要求包含更多节点；复用组件和动态页面都需要覆盖回归测试。

从 Android 14 / API 34 开始，Autofill 会结合 importance、其他 View 属性、请求 flags 和系统 options（配置选项），决定是否触发以及结构中包含哪些节点。手动请求、compat mode（兼容模式）、PCC detection（Autofill 的字段分类检测流程）或设备配置，都可能纳入原本标记为不重要的节点。`importantForAutofill` 是语义提示，无法保证每种请求模式都会减少相同数量的节点。

#### 保持结构回调纯内存

`onProvideAutofillStructure()`、`onProvideAutofillVirtualStructure()` 和 `onProvideContentCaptureStructure()` 应当只读取已经准备好的 UI 状态。以下工作应移出回调：

- 数据库、文件、网络和跨进程查询；
- 为描述临时解码图片或解析整份文档；
- 对全量业务集合排序、去重或格式转换；
- 等待锁、`Future` 或主线程之外的渲染进程；
- 每次回调重新构造不变的 hints、资源映射和长文本。

对于自绘控件或虚拟层级，应保持 `AutofillId` 稳定，以便框架在多次请求间识别同一个节点，并且只报告当前可交互、语义完整的节点。ContentCapture 的多个虚拟节点可以用 `notifyViewsAppeared()` / `notifyViewsDisappeared()` 批量报告；Autofill 的异步虚拟节点必须在时限内调用 `asyncCommit()`。批量 API 可以减少调用次数，但节点是否需要报告仍由产品语义决定。

#### 避免重复触发

标准 `TextView`、`EditText` 和常见 View 已经接入 Autofill 与 ContentCapture。自定义组件只有在以下情况中才需要补充通知：

- 虚拟节点进入、离开或值改变；
- 自绘文本发生用户可感知的语义变化；
- 用户明确选择“自动填充”操作；
- 子 ContentCaptureSession 的上下文发生切换。

不要在每次 `onDraw()`、动画帧，或数据没有变化的 bind 中调用 `requestAutofill()`、`notifyValueChanged()` 或 ContentCapture 文本通知。焦点在相邻节点间反复切换，也会产生额外的会话更新、结构请求或建议 UI 显示与隐藏。

`ContentCaptureManager.getContentCaptureConditions()` 会使用带超时的结果接收器查询系统服务。浏览器可以根据 URL 条件判断是否报告虚拟页面，但不能在每帧执行路径中重复发起这项查询。

### 隐私边界也会改变性能路径

`ContentCaptureService` 需要声明 `android.permission.BIND_CONTENT_CAPTURE_SERVICE`，这项绑定权限由系统控制；Android 14 并不存在面向普通应用的 `CAPTURE_CONTENT` 运行时授权流程。Android 17 平台也没有 `RedactionRule` / `ContentCaptureContext.addRedactionRule()` API，不能依据不存在的接口设计脱敏路径。

Android 17 / API 37 已将 `ContentCaptureManager.setContentCaptureEnabled()` 标记为 deprecated。目标 SDK 为 37 及以上时，该调用可能成为 no-op（不执行任何操作）；平台文档要求敏感窗口使用 `WindowManager.LayoutParams.FLAG_SECURE` 退出 content capture。`FLAG_SECURE` 同时会限制截图和非安全显示，只适合有明确安全需求的窗口，不应用作临时性能开关。

页面内更细的控制仍可使用 `importantForContentCapture`。Autofill 有自己独立的敏感数据处理规则，也受用户所选 provider 的信任边界约束。如果密码字段需要由密码管理器填充，就应保留 Autofill 结构并依赖框架清理敏感值，不能用 ContentCapture 设置代替 Autofill 设置。

### WebView 与跨框架页面

WebView 可以通过 `onProvideAutofillVirtualStructure()` 向 Autofill 暴露 HTML 虚拟节点，也可以通过 `ContentCaptureSession` 报告虚拟页面内容。不能笼统地认为 WebView 会“绕过系统 Autofill”。

同一 WebView 同时参与两条管线时，成本可能包含：

- Autofill 会话触发的一次 AssistStructure 与虚拟节点构建；
- ContentCapture 初始结构及后续增量事件；
- WebView 渲染进程准备虚拟节点的语义数据；
- provider、IME 与 ContentCaptureService 各自的处理。

是否存在重复计算，取决于 WebView 的版本和实现。应同时记录 WebView provider 版本、页面 DOM（文档对象模型）规模、虚拟节点数、目标字段、ContentCapture conditions 和 Autofill request ID，再从 trace 判断是哪条路径占用了 UI 线程。

### 观测与复现

#### Perfetto 中使用源码存在的标记

采集 Perfetto trace 时，打开 `view`、`am`、`wm` 这些 atrace 类别，并启用 app、`system_server`、provider 和 IME 的线程调度与 Binder 数据。Android 17 源码中可以直接对应到实现位置的 slice（时间片标记）包括：

- `dispatchContentCapture() for ...`：ViewRoot 初始 ContentCapture 遍历；
- `flushContentCapture for ...`：窗口获得焦点后的 flush；
- `sendEventAsync`：ContentCapture view-tree 事件从开始到结束的异步区间；
- `notifyContentCaptureEvents`：应用 BackgroundThread 处理动态事件；
- `handleRequestAssistContextExtras`：应用主线程构建 Autofill AssistStructure 的入口。

`android.content_capture.request`、`android.content_capture.process`、`android.autofill.request` 和 `android.autofill.process` 并非 Android 17 AOSP 在这些类中定义的标准 slice。如果设备上出现同名标记，应先确认它们是否由厂商、provider 或应用自行添加。

#### dumpsys 确认服务与会话

下面的命令用于确认当前设备上两套服务的启用状态、会话和配置。输出字段可能随厂商 build（系统构建版本）变化。

```bash
adb shell dumpsys content_capture
adb shell dumpsys autofill
```

`dumpsys` 适合确认“哪个服务、哪个 session、使用了哪些 options”。它无法代替帧时间、线程 slice、Binder flow 和结构规模数据。输出中可能包含账号、字段、组件或采集条件等敏感信息，分享前需要脱敏。

#### 一轮可复核的 A/B

使用受控测试用户并固定 provider 版本，保持设备温度、刷新率、页面数据、IME、账号和输入脚本一致，至少采集以下五组条件：

1. 页面进入但不聚焦 Autofill 字段；
2. 聚焦字段并等待 provider 建议；
3. 开启与关闭 IME inline suggestions 的相同操作；
4. ContentCapture 服务允许该页面与不允许该页面的相同操作；
5. 移除回调中的耗时工作，或排除无关虚拟子树后的版本。

每组都记录 App frame、主线程 `handleRequestAssistContextExtras`、ContentCapture 初始 slice、`BackgroundThread`、`AssistStructure` acquisition 时间、provider 首次响应时间和 IME 建议出现时间。不要在用户日常使用的设备上随意关闭密码管理器、辅助服务或内容采集组件。

### 归因检查表

| 现象 | 需要补充的证据 | 可能的修复位置 |
|---|---|---|
| 首屏 draw 后主线程出现长任务 | `dispatchContentCapture()`、节点数、回调栈 | App 自定义 ContentCapture structure、无关子树 |
| 聚焦输入框时主线程处于 waiting | Autofill `startSession`、result receiver、`system_server` flow | Autofill Session、`system_server` 锁或调度 |
| 主线程执行大量结构回调 | `handleRequestAssistContextExtras`、request ID、virtual nodes | App View / WebView / custom provider |
| 应用 BackgroundThread CPU 高 | ContentCapture queue、flush reason、batch size、文本长度 | App 事件频率、虚拟节点报告 |
| 密码建议出现较晚但帧正常 | provider response、IME inline request、render service | `AutofillService`、IME 或 inline 渲染 |
| `ContentCaptureService` 事件积压 | 服务 main looper、每事件处理时间、I/O | `ContentCaptureService` 实现 |
| 大结构出现多段 Binder | window/node/文本规模、partial transfer 日志 | App 结构设计、虚拟层级、字段体积 |

性能报告至少应写明触发字段、request / session ID、目标线程、provider / IME / WebView 版本和结构规模。如果只记录“开启密码管理器后变慢”，就无法区分会话等待、结构遍历、服务响应和建议 UI 各自的耗时。

### Android 8—17 版本边界

- **Android 8.0 / API 26**：Autofill Framework 和 `importantForAutofill` 进入公开 API。
- **Android 10 / API 29**：`ContentCaptureManager`、`ContentCaptureSession` 和 `ContentCaptureService` 进入公开 API。
- **Android 11 / API 30**：`importantForContentCapture` 和 IME inline suggestions 相关公开 API 可用。
- **Android 14 / API 34**：Autofill 对 importance、其他 View 属性和优化选项的组合判断发生变化，不能沿用早期版本的固定包含规则。
- **Android 17 / API 37**：按 `android-17.0.0_r1` 核对。ContentCapture 使用 UI 结构准备、应用 `BackgroundThread` 缓冲和 direct `oneway` Binder；Autofill 仍通过 `ActivityThread` 构建 `AssistStructure`。`setContentCaptureEnabled()` 在 API 37 已 deprecated，目标 SDK 37 及以上版本应按照 `FLAG_SECURE` 契约处理敏感窗口。

这些路径属于 framework 和应用 / 服务进程，理解它们不需要依赖 `android17-6.18-2026-06_r6` kernel tag。Binder 驱动、线程调度和内存压力会影响时延，但本文讨论的调用关系没有引入 Android 17 内核专属机制。

### ContentCapture 与 Autofill 源码与资料

- [`ContentCaptureManager.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/contentcapture/ContentCaptureManager.java)、[`MainContentCaptureSession.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/contentcapture/MainContentCaptureSession.java) 与 [`IContentCaptureDirectManager.aidl`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/contentcapture/IContentCaptureDirectManager.aidl)：会话、后台队列、事件合并、flush 和 direct `oneway` Binder。
- [`View.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/View.java)、[`ViewGroup.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewGroup.java) 与 [`ViewRootImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)：两套 structure 回调、importance、初始报告、动态事件和 AOSP trace slice。
- [`ContentCaptureManagerService.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/contentcapture/java/com/android/server/contentcapture/ContentCaptureManagerService.java) 与 [`ContentCaptureService.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/service/contentcapture/ContentCaptureService.java)：会话代理、direct service Binder 与服务 main-looper 回调。
- [`AutofillManager.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/autofill/AutofillManager.java) 与 [`IAutoFillManager.aidl`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/autofill/IAutoFillManager.aidl)：焦点触发、会话状态、`oneway` 调用和结果接收器等待。
- [`ActivityThread.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityThread.java) 与 [`AssistStructure.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/assist/AssistStructure.java)：主线程采集、虚拟节点等待与分段 Binder 传输。
- [`Session.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/autofill/java/com/android/server/autofill/Session.java) 与 [`AutofillInlineSuggestionsRequestSession.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/autofill/java/com/android/server/autofill/AutofillInlineSuggestionsRequestSession.java)：assist request、FillContext、provider 与 IME inline suggestions 协作。
- [Autofill 优化指南](https://developer.android.com/identity/autofill/autofill-optimize)、[View API](https://developer.android.com/reference/android/view/View) 与 [ContentCaptureManager API](https://developer.android.com/reference/android/view/contentcapture/ContentCaptureManager)：公开属性、版本行为与 API 37 弃用边界。
