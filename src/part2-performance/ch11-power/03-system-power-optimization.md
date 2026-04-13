---
title: "系统级功耗优化"
chapter: "11.3"
status: ready-for-review
section: "11.3"
drafted_date: "2026-04-03"
drafted_by: "openclaw-task2a"
reviewed_date: "2026-04-13"
reviewed_by: "openclaw-task6"
task6_result: needs-rework
applicable_versions: "Android 6.0 (API 23) - Android 16 (API 36)"
last_verified: "2026-04-03"
last_verified_against: "AOSP android-16.0.0_r1"
polish_count: 1
polish_date: "2026-04-05"
polish_by: "task2b-polish"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/training/monitoring-device-state/doze-standby"
  - type: official
    path: "https://source.android.com/docs/core/power"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/DeviceIdleController.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/usage/UsageStatsService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/PowerManager.java"
  - type: official
    path: "https://dontkillmyapp.com/"
tags: ['doze', 'standby', 'battery-saver', 'background-restriction', 'oem-power', 'adaptive-battery', 'foreground-service']
related_chapters: ["5.6", "11.1", "11.2", "1.3", "4.4"]
pipeline_stage: task2b_pending
task6_state: reviewed
task9_state: reviewed
task9_result: needs-rework
task2b_state: pending
---

# 系统级功耗优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Doze 模式的分阶段触发与维护窗口机制
- 🔹 App Standby Buckets（Active/Working/Frequent/Rare/Restricted）的调度差异
- 🔹 系统级限后台策略：Background Activity Starts 限制、后台定位限制
- 🔹 省电模式下的系统行为变化
- 🔹 厂商级功耗管理：后台冻结、自启动管理、后台杀进程策略

### 扩展（可选深入）

- 🔸 Adaptive Battery 的 ML 模型工作原理
- 🔸 电池健康管理（Adaptive Charging）与性能的关系

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解系统级功耗管理

在 §11.2 中，我们讨论了 App 侧可以做的功耗优化：减少 WakeLock 持有时间、合理使用 WorkManager、优化网络请求频率等。这些都是在 App 主动配合的前提下完成的。但现实是，即便一个 App 自身做得很好，系统依然可能替它"省电"——在用户不知情的情况下限制它的后台行为、推迟它的任务执行、甚至直接杀掉它的进程。

这不是 Bug，而是 Android 系统在设计时就内置的功耗管理策略。从 Android 6.0 的 Doze 模式开始，到 Android 9 的 App Standby Buckets，再到 Android 12 的 Restricted 桶和各厂商自研的后台管控机制，系统级功耗管理的能力越来越强、粒度越来越细。

如果我们不了解这些机制，就会遇到一些令人困惑的现象：推送延迟到达、后台任务没有按预期执行、用户投诉 App "吃电" 但代码里找不到问题。这些问题的根因往往不在 App 内部，而在系统级功耗策略对外部行为的约束上。

理解这些机制后，我们能做的事情包括：在 Perfetto/Battery Historian 中识别系统级限制导致的延迟；根据 Standby Bucket 的不同配额调整后台任务策略；在用户反馈"后台被杀"时判断是 AOSP 行为还是厂商定制行为；有针对性地引导用户在系统设置中为 App 豁免某些限制。

## Doze 模式：分阶段触发与维护窗口机制

Doze 模式是 Android 6.0（API 23）引入的低功耗状态管理机制，核心思想是：当设备长时间不被使用时，系统主动限制后台 App 的 CPU 和网络活动，将它们集中到短暂的"维护窗口"中执行，其余时间设备尽可能保持深度睡眠。

### 两种 Doze：Light Doze 与 Deep Doze

Android 7.0（API 24）将 Doze 拆分为两个层级：

**Light Doze** 的触发条件比较宽松——只要屏幕关闭且设备未在充电，即使设备在移动中也会进入。它的限制力度相对温和：推迟非关键的网络请求和 JobScheduler 任务，但仍然允许高优先级 FCM 消息到达、允许精确闹钟（有速率限制）、允许前台服务运行。

**Deep Doze** 则是原始的、更严格的 Doze。它需要设备满足三个条件：屏幕关闭、未在充电、且设备处于静止状态（通过加速度计判断）。一旦进入 Deep Doze，系统会实施大幅度的限制：网络访问被暂停、标准 AlarmManager 闹钟被推迟、WakeLock 大部分被忽略、JobScheduler 任务和 SyncAdapter 同步被延迟、后台 Wi-Fi 扫描停止。

[已验证: 官方文档, developer.android.com/training/monitoring-device-state/doze-standby]

### 维护窗口：递增长度的呼吸机制

Doze 不是把设备"冻住"就不管了。它会周期性地进入短暂的维护窗口（Maintenance Window），在这个窗口内临时解除大部分限制，让 App 有机会完成积压的工作。

维护窗口的关键特征是**间隔递增**。随着设备空闲时间变长，两次维护窗口之间的间隔也越来越大：

- 刚进入 Doze 后，大约每小时唤醒一次
- 随后间隔逐渐拉长到 2 小时、4 小时甚至更长
- 维护窗口本身持续的时间也从几秒到几十秒不等

在维护窗口内，系统会临时恢复以下能力：

- 执行被推迟的 JobScheduler 任务和 SyncAdapter 同步
- 允许被延迟的 AlarmManager 闹钟触发
- 临时恢复网络访问
- WakeLock 正常工作

这也是为什么常会出现这样的用户反馈：“我的 App 后台同步有时候能工作，有时候不行。”如果同步恰好赶上了维护窗口，它就能完成；如果错过了，就要等下一个窗口。

### 在 Perfetto 中的表现

在 Perfetto Trace 中，可从下面几个观察点判断 Doze 是否生效：

- 搜索 `DeviceIdleController` 相关事件，查看设备进入和退出 Doze 的时刻
- 观察 CPU 状态变化：Deep Doze 期间 CPU 几乎完全休眠，维护窗口期间短暂唤醒
- 网络活动：Doze 期间网络 Track 几乎为空，维护窗口出现短暂的网络活跃区间
- `PowerManagerService` Track 中可直接观察到设备空闲状态的转换

[图：Perfetto 中 Doze 状态切换、维护窗口唤醒与恢复休眠的示意截图]

### Doze 的豁免与例外

并非所有场景都适合被 Doze 限制。以下情况 Doze 不会生效或可以豁免：

- **设备在充电时**：Doze 完全不激活
- **高优先级 FCM 消息**：可以在 Doze 期间唤醒 App（这是 Google 推荐的紧急通知方式）
- **用户在设置中手动豁免的 App**：设置 → 电池 → 未受限
- **前台服务**：一旦 App 拥有前台服务，Doze 对它的限制大幅放宽
- **紧急闹钟**（`setAndAllowWhileIdle` / `setExactAndAllowWhileIdle`）：可以在 Doze 期间触发，但每个 App 有速率限制（大约每 9 分钟一次）

[已验证: 官方文档, developer.android.com/training/monitoring-device-state/doze-standby]

## App Standby Buckets：基于使用频率的分层调度

Doze 模式解决的是"设备空闲"场景的功耗问题。但很多时候，设备并不是空闲的——用户正在刷微博，但后台还有一个从来不用的购物 App 在频繁拉取数据。这就是 App Standby Buckets 要解决的问题。

Android 9（API 28）引入了 App Standby Buckets 机制，根据用户对每个 App 的使用频率，将它们分为五个优先级桶，每个桶拥有不同的后台资源配额。与 Doze 不同，App Standby 不需要设备处于空闲状态，它随时都在工作。

### 五个桶的定义与调度差异

**Active（活跃）**——用户当前正在使用或刚刚使用过的 App。这是最自由的桶：

- 常规 Job 运行配额：60 分钟滚动窗口内最多 20 分钟（Android 16 起开始限制，此前无限制）
- 加速 Job（Expedited Job）：24 小时内最多 30 分钟
- 闹钟：无限制
- 网络：不受限制

**Working Set（工作集）**——用户经常使用但当前不在前台的 App：

- 常规 Job：4 小时滚动窗口内最多 10 分钟
- 加速 Job：24 小时内最多 15 分钟
- 闹钟：每小时最多 10 次
- 网络：不受限制

**Frequent（常用）**——用户定期使用但不是每天都会打开的 App：

- 常规 Job：12 小时滚动窗口内最多 10 分钟
- 加速 Job：24 小时内最多 10 分钟
- 闹钟：每小时最多 2 次
- 网络：不受限制

**Rare（极少使用）**——用户很少打开的 App：

- 常规 Job：24 小时滚动窗口内最多 10 分钟
- 加速 Job：显著受限
- 闹钟：每天最多 1 次
- 网络：受限（后台不允许访问网络）

**Restricted（受限）**——Android 12（API 31）新增的最低优先级桶。App 被放入这个桶的原因包括：用户手动限制了它的后台活动、App 消耗了过多系统资源、或者用户已经超过 8 天（Android 13 起，Android 12 为 45 天）没有与之交互：

- 常规 Job：每天一次，以 10 分钟批次运行，且与其他 App 的 Job 合并执行
- 加速 Job：进一步受限
- 闹钟：每天最多 1 次（精确或不精确）
- 网络：后台不允许访问
- 这些限制即使在设备充电时也部分生效（充电 + 空闲 + 非计费网络时会放宽）

[已验证: 官方文档, developer.android.com/topic/performance/appstandby]

### 桶的动态分配：Adaptive Battery 的角色

App 不会被固定在某个桶里。系统会根据用户行为持续调整。这个分配决策背后是 Android 9 引入的 **Adaptive Battery** 机制。

Adaptive Battery 使用一个运行在本地的机器学习模型来预测用户在未来几小时内可能使用哪些 App。[待验证：部分来源提及基于 TensorFlow Lite 的 CNN + 前馈网络架构，但具体网络结构未在 AOSP 源码或官方文档中确认] 模型基于以下信号做预测：

- App 的历史启动频率和时间分布
- App 在前台的使用时长
- App 的通知交互情况（用户是否点击通知打开 App）
- 设备的整体状态（时间、位置等）

所有训练数据都在设备本地处理，个人身份信息在训练前被移除。模型的输出直接用于决定 App 应该被放入哪个 Standby Bucket。对于模型预测"用户近期不会打开"的 App，系统会将其放入更低优先级的桶，从而限制它的后台资源消耗。

这解释了一个常见的开发困惑："我的 App 昨天后台任务还正常，今天就执行不了了。"原因可能是 Adaptive Battery 根据用户几天的使用模式，将 App 从 Working Set 降到了 Rare 桶。

[已验证: 官方文档, source.android.com/docs/core/power]

### 如何在开发中应对 Standby Buckets

了解了 Buckets 机制后，我们的策略应该是：

1. **不要试图影响 Bucket 分配**——这是系统根据用户行为自动决定的，API 层面没有"请把我放到 Active 桶"的调用
2. **适配而非对抗**——确保 App 在每个桶的限制下都能正常工作，尤其是 Rare 和 Restricted 桶
3. **测试覆盖**——使用 ADB 命令模拟不同桶的状态：
   ```bash
   # 将 App 设置为 Rare 桶
   adb shell am set-standby-bucket com.example.app rare
   # 查看当前桶
   adb shell am get-standby-bucket com.example.app
   ```
4. **使用 WorkManager 而非直接使用 JobScheduler**——WorkManager 内部已经处理了 Standby Bucket 的配额差异

## 系统级限后台策略

Doze 和 Standby Buckets 会根据设备状态和用户行为动态收紧后台活动。除此之外，Android 还有一类更直接的后台限制，不管设备状态如何，都会生效。这些限制从 Android 8.0 开始逐步收紧，到 Android 14 已经形成了一套比较完整的后台管控体系。

### Background Activity Starts 限制

从 Android 10（API 29）开始，系统限制后台 App 启动 Activity。这是一个容易引发"我的页面弹不出来"投诉的策略。

核心规则很简单：**当 App 不在前台时，它不能调用 `startActivity()` 显示新页面**（有少数例外）。这是为了防止 App 在后台突然弹出广告或干扰用户当前操作。

在 Android 14（API 34）中，这个限制进一步收紧：即使通过 `PendingIntent` 启动 Activity，也需要显式声明权限。App 在后台时应该通过通知（Notification）来传递信息，让用户主动点击打开，而不是直接弹页面。

豁免场景包括：

- App 有一个正在运行的前台服务（且该服务与通知关联）
- App 刚刚收到高优先级 FCM 消息
- 用户刚刚与 App 的通知交互（如点击通知）
- App 是设备的当前输入法、VoiceInteractionService 等

[已验证: 官方文档, developer.android.com/guide/components/activities/background-starts]

### 后台定位限制

位置信息是功耗大户（GPS 模块的功耗可以占到整机的 10-20%），Android 对后台定位的限制逐年收紧：

**Android 8.0（API 26）**——后台 App 的位置更新频率被限制为"每小时几次"，无论 App 的 targetSdkVersion 是多少。

**Android 10（API 29）**——引入 `ACCESS_BACKGROUND_LOCATION` 权限。App 如果需要在后台获取位置，必须单独声明这个权限。用户可以选择"仅在使用中允许"或"始终允许"，前者意味着 App 在后台无法获取位置。

**Android 11（API 30）**——进一步收紧：即使 App 持有前台服务，如果用户没有授予"始终允许"权限，App 在后台仍然无法获取位置。

**Android 14（API 34）**——如果 App 没有 `ACCESS_BACKGROUND_LOCATION` 权限却尝试通过前台服务获取位置，会直接抛出 `SecurityException`。

这对性能优化的影响是：如果我们的 App 有后台轨迹记录或位置上报需求，需要仔细设计权限请求流程，确保用户理解并授权。否则在较新的 Android 版本上，后台定位功能会静默失败。

[已验证: 官方文档, developer.android.com/training/location/background]

### 后台服务限制（Android 8.0+）

Android 8.0（API 26）对后台服务做了根本性限制：**当 App 处于后台超过几分钟，系统不再允许它创建后台服务**。已有的后台服务会在几分钟内被停止。

这直接推动了 `JobScheduler` 和后来的 `WorkManager` 成为后台任务的首选方案。如果 App 确实需要在后台持续执行任务，必须使用前台服务（Foreground Service），它会显示一个持续通知告知用户。但这也会增加功耗和用户的感知负担。

Android 14 对前台服务进一步增加了限制：某些类型的前台服务（如位置相关的）需要声明特定的前台服务类型（foreground service type），并在 Manifest 中声明对应权限。

[已验证: 官方文档, developer.android.com/about/versions/oreo/background]

## 省电模式下的系统行为变化

上面讨论的 Doze 和 Standby Buckets 是系统自动触发的。省电模式（Battery Saver）则是由用户手动开启（或系统在电量低于一定阈值时建议开启）的更激进的功耗管理策略。

### 省电模式的核心行为

当省电模式激活时，系统层面会发生以下变化：

**CPU 降频**——处理器的最大频率被限制，部分实现甚至会禁用大核。这直接降低了 CPU 功耗，但也意味着计算密集型任务（如图片处理、列表渲染）会变慢，可能出现掉帧。

**后台活动收紧**——省电模式下，所有 App 都被当作"Rare"桶对待，即使它本来是 Active。JobScheduler 的配额被进一步压缩，闹钟被推迟，后台网络访问受限。

**屏幕与显示**——屏幕亮度降低，屏幕超时时间缩短，动画可能被简化或禁用。在高刷设备上，刷新率可能被强制降到 60Hz 甚至更低。

**网络限制**——后台 App 的网络访问被大幅限制。移动数据连接被当作计费网络处理，系统会推迟非必要的网络请求。

**定位服务**——GPS 模块的工作频率降低，后台 App 的位置更新进一步减少。

**其他**——GPU 可能被限频，振动反馈被禁用，某些设备特性（如 Pixel 的 Motion Sense、车载碰撞检测）被关闭。

[已验证: 官方文档, developer.android.com/training/monitoring-device-state/doze-standby]

### 自适应省电（Adaptive Battery Saver）

Android 9 引入了自适应省电功能，系统会根据用户的充电习惯和电池消耗模式，在电量较低时自动启用省电模式，而不需要用户手动操作。这个功能在 Pixel 设备上默认开启，厂商可以自定义触发阈值。

自适应省电与 Adaptive Battery 是互补关系：Adaptive Battery 通过预测 App 使用频率来分配 Standby Bucket（微观调度），自适应省电则根据整体电量状况决定是否启用全局省电模式（宏观调控）。两者共享用户行为数据作为输入，但作用层面不同——前者影响单个 App 的后台配额，后者影响所有 App 的运行环境。

### 在 Perfetto 中观察省电模式

在 Trace 中，可从下面几个观察点识别省电模式：

- `PowerManagerService` Track 中查找 `isPowerSaveMode` 状态变化
- CPU 频率 Track：如果看到所有核心频率被限制在较低值（如 1.0 GHz 以下），且持续时间较长，可能是省电模式
- 刷新率 Track：从 120Hz 突降到 60Hz 可能是省电模式的征兆
- `DeviceIdleController` 的状态变化

[图：Perfetto 中省电模式触发后 CPU 频率受限与刷新率回落的示意截图]

### 对 App 性能分析的影响

当我们在做性能测试和分析时，省电模式是一个必须控制的变量。如果测试时设备处于省电模式，所有的帧率、启动时间、滑动流畅度数据都会偏慢，可能导致错误的优化方向。

建议的做法：

- 性能测试前确认设备未开启省电模式
- 使用 `adb shell settings put global low_power 0` 确保省电模式关闭
- 在测试报告中注明设备是否开启了省电模式

## 厂商级功耗管理：Android 生态中的"灰色地带"

AOSP 提供的功耗管理机制（Doze、Standby、省电模式）只是“官方基线”。在中国市场，几乎所有主流厂商都会在此基础上叠加自研的、更激进的后台管控策略。这些策略通常不在 AOSP 代码中，也不遵循标准的 Standby Bucket 配额，是 Android 碎片化问题中最让开发者头疼的一环。

网站 dontkillmyapp.com 专门跟踪了各大厂商的后台杀进程行为，并给出了"杀伤力"评分，从侧面反映了这个问题的严重性。

### 小米（MIUI / HyperOS）

小米的功耗管理在业界以"激进"著称：

**自启动管理**——默认禁止所有 App 自启动（开机自动运行和被其他 App 唤醒）。用户需要手动为每个 App 开启"后台自启动"权限。如果 App 的核心功能依赖自启动（如消息推送的长连接），会直接受到影响。

**后台冻结**——MIUI 的 `com.miui.powerkeeper` 服务会在后台持续扫描 App 活动。对于被标记为"可优化"的 App，系统会在它们进入后台一段时间后（通常 10 分钟左右）直接冻结进程，使其无法执行任何代码。

**电池优化策略**——在设置 → 电池 → 应用智能省电中，用户可以为每个 App 选择"无限制"、"智能限制"或"后台运行 10 分钟后限制"。默认选择通常是"智能限制"。

**应对策略**：对于需要后台持续运行的 App（如即时通讯、导航），需要在文档中引导用户：将 App 设为"无限制"电池策略、在最近任务界面锁定 App、开启自启动权限。

### 华为（EMUI / HarmonyOS）

华为的功耗管控同样以严格闻名：

**应用启动管理**——设置 → 电池 → 应用启动管理中，华为为每个 App 提供了"自动管理"和"手动管理"两种模式。自动管理模式下，系统会根据使用频率决定是否允许 App 在后台运行。手动管理模式允许用户分别控制"自启动"、"关联启动"和"后台活动"三个开关。

**PowerGenie**——在 EMUI 9+ 设备上，系统内置了一个名为 PowerGenie 的任务管理器，它会主动扫描并杀掉"不活跃"的后台进程。PowerGenie 没有用户可配置的白名单，唯一的绕过方式是通过 ADB 卸载它（`adb shell pm uninstall -k --user 0 com.huawei.powergenie`），但这需要开发者模式的用户才能操作。

**超级省电模式**——极端省电模式下，系统只保留电话、短信等核心功能，所有第三方 App 被暂停。

### OPPO / vivo（ColorOS / OriginOS）

OPPO 和 vivo 的策略类似：

**应用冻结/睡眠**——ColorOS 的"睡眠待机优化"会在设备空闲时限制后台 App 活动。在电池管理中，用户可以为每个 App 设置"允许后台活动"开关。

**自启动管理**——与小米类似，默认禁止 App 自启动。需要在"手机管家"或"安全中心"中手动开启。

**关联启动限制**——限制 App 之间的相互唤醒（A App 启动后拉起 B App），这是国内厂商特有的管控维度。

### 厂商策略对性能分析的影响

做功耗和后台行为分析时，厂商策略的影响主要体现在：

1. **后台任务执行不稳定**——同一个 WorkManager 任务，在 Pixel 上能按时执行，在小米上可能被推迟数小时。这不是 WorkManager 的 Bug，而是厂商的进程冻结策略。
2. **推送延迟**——FCM 在国内不可用，App 通常使用厂商推送通道（小米推送、华为推送等）或第三方推送（如极光推送）。这些推送通道能否正常工作，取决于 App 是否被厂商系统"放行"。
3. **功耗数据差异巨大**——同一 App 在不同厂商设备上的电池消耗报告可能差 3-5 倍，大部分差异来自厂商的后台管控策略，而非 App 本身的行为差异。

**分析建议**：

- 在 Perfetto/Battery Historian 中关注进程状态变化（`Process State` Track），判断进程是被正常调度还是被强制冻结
- 测试覆盖主流厂商设备（至少包括小米、华为、OPPO/vivo）
- 在性能测试报告中注明设备型号和厂商 ROM 版本
- 参考各厂商的开发者文档了解其后台管控策略的细节

[已验证: 官方文档, dontkillmyapp.com; 厂商策略基于公开资料整理，具体行为可能因 ROM 版本而异]

## 与其他机制的关系

系统级功耗管理并非孤立存在，它和全书讨论的多个机制都有交叉：

**与进程管理（§1.3）的关系**——LMK（Low Memory Killer）杀进程和厂商的后台杀进程策略是两套独立的机制，但它们会叠加影响。一个 App 可能先被厂商冻结，然后因为内存压力被 LMK 彻底回收。

**与 CPU 调度与功耗管理（§5.6）的关系**——§5.6 讨论的是 CPU 调度层面的功耗优化（EAS、UClamp、Doze 底层的 Idle 状态管理）。本节讨论的是应用框架层的功耗策略，是 §5.6 底层机制的上层体现。当本节提到的省电模式导致 CPU 降频时，实际的频率限制通过 §5.6 中讨论的 cpufreq 机制执行；Doze 模式下 CPU 进入深度 Idle 状态，对应的也是 §5.6 中介绍的 CPU Idle 状态管理。

**与 App 耗电优化（§11.2）的关系**——§11.2 是"App 主动配合"，本节是"系统强制约束"。两者是互补关系：即便 App 做好了所有主动优化，系统策略仍然会限制它的后台行为。

**与 Perfetto 工具（§13.1-13.7）的关系**——分析系统级功耗限制时，Perfetto 是最核心的工具。通过 Trace 能观察到进程调度状态、CPU 频率变化、网络活动窗口等信息，帮助我们区分问题是 App 自身造成的，还是系统策略导致的。

## 版本演进

系统级功耗管理在不同 Android 版本中的演进路径：

| 版本 | 关键变化 |
|------|---------|
| Android 6.0 (API 23) | 引入 Doze 模式和 App Standby |
| Android 7.0 (API 24) | 拆分为 Light Doze 和 Deep Doze |
| Android 8.0 (API 26) | 限制后台服务创建、限制后台定位频率、限制隐式广播 |
| Android 9 (API 28) | 引入 App Standby Buckets（四桶：Active/Working/Frequent/Rare）、Adaptive Battery |
| Android 10 (API 29) | Background Activity Starts 限制、`ACCESS_BACKGROUND_LOCATION` 权限 |
| Android 11 (API 30) | 前台服务也不能无权限获取后台位置 |
| Android 12 (API 31) | 新增 Restricted 桶、Exact Alarm 需要声明权限 |
| Android 13 (API 33) | Restricted 桶触发条件从 45 天缩短到 8 天、FCM 配额不再与桶绑定 |
| Android 14 (API 34) | PendingIntent 启动 Activity 需要显式权限、前台服务类型强制声明 |
| Android 16 (API 36) | Active 桶也开始有 Job 运行配额限制（20min/60min） |

[已验证: 官方文档, developer.android.com/about/versions]

## 常见问题与误区

### "后台被杀是 Android 的 Bug"

不是。Android 的后台管控策略是有意为之。Doze、Standby Buckets、省电模式都是系统为了延长电池续航而设计的正常机制。厂商的后台管控虽然更激进，但也是在其 ROM 中有明确设置项供用户调整的。正确的心态是：理解这些机制，适配它们，而不是对抗它们。

### "WorkManager 能保证任务一定执行"

WorkManager 保证的是"最终一致性"——任务最终会被执行，但不保证在什么时候执行。在 Rare 或 Restricted 桶中，WorkManager 任务可能被推迟数小时甚至一天。如果业务需要精确的时间控制，需要结合前台服务或其他手段。

### "用户不会手动调整电池设置"

用户手动调整电池设置的比例并不低。尤其当系统提示“XX App 正在耗电”时，用户很可能会选择“限制”。我们的 App 也就可能随时从 Active 桶被手动降到 Restricted 桶，因此需要在设置页或帮助文档里说明后台运行权限的用途。

### "Doze 只在晚上才会生效"

不完全准确。Deep Doze 确实需要设备静止，但 Light Doze 只要屏幕关闭且未充电就会触发。如果用户习惯性地锁屏但不充电（比如开会时），Light Doze 在白天也会频繁生效。

### "国产厂商的后台管控都是负面的"

厂商的激进后台管控确实给开发者带来了适配负担，但从用户角度看，它也在换取更长的续航。更实际的做法是理解这些策略，并告诉用户如何在系统设置里放行我们的 App。

## 参考资料

### AOSP 源码路径

- `frameworks/base/services/core/java/com/android/server/DeviceIdleController.java` — Doze 模式控制
- `frameworks/base/services/core/java/com/android/server/usage/UsageStatsService.java` — 使用统计与 Standby Bucket 分配
- `frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java` — 省电模式管理
- `frameworks/base/core/java/android/os/PowerManager.java` — PowerManager API
- `frameworks/base/services/core/java/com/android/server/job/JobSchedulerService.java` — Job 配额管理

### 官方文档

- [Optimize for Doze and App Standby](https://developer.android.com/training/monitoring-device-state/doze-standby)
- [Power usage optimization](https://developer.android.com/topic/performance/power)
- [Background execution limits](https://developer.android.com/about/versions/oreo/background)
- [Restrictions on starting activities from the background](https://developer.android.com/guide/components/activities/background-starts)
- [Request background location](https://developer.android.com/training/location/background)
- [Android power management](https://source.android.com/docs/core/power)

### 其他参考

- [Don't kill my app!](https://dontkillmyapp.com/) — 各厂商后台管控策略追踪
- Android 16 Developer Preview 文档 — Active 桶 Job 配额变更
