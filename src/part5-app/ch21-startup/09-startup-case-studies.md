---
title: "启动优化复盘框架与案例模板"
chapter: "21.9"
section: "21.9"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-02"
last_verified_against: "AOSP android-17.0.0_r1 Activity.reportFullyDrawn / ActivityMetricsLogger.notifyFullyDrawn, Android Developers launch-time / App Startup / Baseline Profiles docs"
confidence: medium
drafted_date: "2026-05-13"
polish_count: 0
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/launch-time"
  - type: official
    path: "https://developer.android.com/topic/libraries/app-startup"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/overview"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile"
  - type: aosp
    path: "frameworks/base/core/java/android/app/Activity.java#reportFullyDrawn"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityMetricsLogger.java#notifyFullyDrawn"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动速度？.md"
  - type: local
    path: "src/part5-app/ch21-startup/01-startup-analysis.md"
  - type: local
    path: "src/part5-app/ch21-startup/02-startup-framework.md"
  - type: local
    path: "src/part5-app/ch21-startup/04-baseline-profile-practice.md"
tags: [case-study, startup, optimization, baseline-profile, startup-framework]
related_chapters: ["21.1", "21.2", "21.4"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: "2026-05-19"
task9_state: reviewed
task9_result: pass-tech-review
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-19"
task2b_state: "fixed"
task2b_result: "fixed"
last_task6_at: "2026-05-19T08:16:46+08:00"
last_task6_audit: "2026-06-11"
last_task6_review_log: logs/review/2026-05-19-08-review.md
last_task9_at: "2026-05-19T08:27:59+08:00"
last_task9_audit: "2026-07-02"
last_task9_review_log: logs/deep-review/2026-05-19-08-deep-review.md
task9_review_notes: "2026-05-19 Task9：pass-tech-review。P0 0 / P1 0 / P2 0；源码锚点、App Startup、Baseline Profile 与 TTFD 链路复核通过；满足 Task6+Task9+queue 条件，自动晋升 finalized。"
auto_promoted_by: task9-deep-tech-review
auto_promoted_at: "2026-05-19T08:27:59+08:00"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-17
---

# 启动优化复盘框架与案例模板

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 大型 App 启动优化实战
- 🔹 启动框架演进案例
- 🔹 Baseline Profile 实施效果

### 扩展（可选深入）

- 🔸 （待扩展）

<!-- outline-end -->

## 本节定位：案例要能被复查

启动优化复盘的价值不在“列出做过哪些动作”，而在于留下可验证的因果链：

```text
用户症状
  -> 指标确认影响范围
  -> trace / 平台时间戳定位阶段
  -> 代码与配置证明触发条件
  -> 单变量实验验证改动
  -> 线上同 cohort 回看
  -> 门禁、负责人和回滚条件
```

这条链路把现象、证据、改动和结果分开记录。缺少任一段，后续读者都很难判断收益来自代码、编译状态、缓存、设备差异还是样本结构变化。

本文提供三组复盘演练：大型 App 初始化、启动框架演进、Baseline Profile。它们是可套用的分析框架，不冒充某个产品的脱敏数据，也不提供脱离设备、构建和样本的固定收益百分比。启动链路见[启动完整路径分析](./01-startup-analysis.md)，任务调度见[启动任务编排框架](./02-startup-framework.md)，编译状态见[Baseline Profile 实战](./04-baseline-profile-practice.md)，线上验收见[启动监控与度量](./08-startup-monitoring.md)。

## 案例一：大型 App 的 `Application` 阶段持续变长

### 1. 先写问题陈述

一个合格的问题陈述应包含：

- 哪个版本开始变化；
- cold、warm、hot 中哪一类变化；
- 哪些入口、设备档位、Android 版本和安装状态受影响；
- TTID、TTFD、首屏前 ANR/Crash 和 fully drawn 完成率怎样变化；
- 变化是否超过历史噪声和产品预算；
- 监控 schema、采样率与启动类型占比是否同时变化。

“`Application.onCreate()` 有很多 SDK，所以启动慢”只是猜测。先用 Android 15+ `ApplicationStartInfo`、应用阶段事件和 Perfetto 判断时间消耗在哪个区间。Android 10–14 没有平台启动信息 API 时，使用 Macrobenchmark、Logcat `Displayed`、应用单调时钟和 Perfetto 互相校准。

### 2. 从阶段区间缩小范围

| 区间 | 证据 | 常见方向 |
| --- | --- | --- |
| launch → fork | `ApplicationStartInfo` / Perfetto | 系统负载、进程创建竞争、设备或 ROM 集中性 |
| fork → bindApplication | 平台时间戳 / Perfetto | 进程准备、运行时与应用绑定 |
| bindApplication → Application.onCreate | `ActivityThread`、Provider trace | Provider、类加载、Instrumentation |
| Application 入口 → 出口 | task 埋点、自定义 trace | SDK、同步 I/O、锁、序列化、线程创建 |
| Activity 创建 → first frame | Activity、View/Compose、RenderThread trace | 布局、首次组合、资源、主线程与渲染调度 |
| first frame → fully drawn | ready 状态、数据链路、`reportFullyDrawn()` | 数据库、缓存、网络和首屏业务条件 |

阶段表只能指向排查区域。比如 Application 区间变长，并不证明某个后台 task 消耗了同样长的 CPU 时间；它可能在 Binder、文件锁或调度队列中等待。需要展开对应线程轨道才能下结论。

### 3. 建立初始化清单

把所有自动与显式入口放进一张清单，包括 manifest 合并得到的 Provider、`Application`、AndroidX App Startup initializer、依赖注入容器、静态初始化和首屏 Activity。

| 字段 | 说明 |
| --- | --- |
| `componentId` | 稳定 ID，与 trace、线上事件、owner 映射一致 |
| 入口 | Provider、Application、Activity、手动调用或类加载 |
| 进程 | 主进程、指定远程进程或所有相关进程 |
| 首帧需求 | 必须完成、只需最小能力、可以延后 |
| TTFD 需求 | 是否影响核心内容和首个操作 |
| 依赖 | 硬依赖、可降级依赖、仅顺序约束 |
| 线程与等待 | 主线程、CPU、I/O、Binder、锁 |
| 失败语义 | fail-fast、降级、重试、跳过 |
| 幂等与重入 | 多入口并发、进程重建、配置切换时是否安全 |
| owner / 开关 | 负责人、灰度开关、回滚方式 |

“公共基础设施”不能自动获得首帧优先级。Crash SDK 可能只需要尽早安装最小异常捕获，历史报告扫描与上传可以延后；埋点 SDK 可以先缓存内存事件，再补全设备信息和发送；网络库若首屏没有请求，可以到首个调用再初始化。

### 4. 用最小能力拆分 SDK

| 模块 | 首帧前的最小能力 | 可延后部分 | 需要验证的风险 |
| --- | --- | --- | --- |
| Crash | 安装必要 handler，记录最小进程信息 | 历史文件扫描、符号/设备扩展、上传 | 延后窗口内是否丢失关键崩溃信息 |
| 埋点 | 接受事件并写入有界内存队列 | 设备画像、压缩、批量发送 | 队列溢出、进程死亡与事件顺序 |
| Push | 当前入口必需的 token/路由状态 | 非关键注册、上报和扩展能力 | 通知点击路径是否依赖同步初始化 |
| 数据库 | 首屏必需查询与 schema 可用性 | 非首屏表预热、清理、统计 | 迁移独占、跨进程访问与失败恢复 |
| 远程配置 | 已验证的本地快照与默认值 | 网络刷新 | 旧配置兼容、过期策略和回滚 |
| 图片/媒体 | 首屏解码所需最小配置 | 非首屏缓存扫描、预取和大池创建 | 首帧后 CPU/内存竞争 |

数据库迁移不能简单丢到后台。只要首屏或其他进程会打开同一数据库，schema 必须先达到可用状态。可延后的是非关键数据库、可拆分的数据搬运或首屏不访问的迁移阶段，并且要有单一迁移者、版本检查、超时和恢复策略。

### 5. 判断一次改动是否只是“挪时间”

把工作移出 `Application.onCreate()` 可能改善 TTID，也可能产生四种副作用：

- 首帧后立即争抢 CPU，让首屏滚动或动画掉帧；
- 数据未 ready，TTFD 和首个点击延迟上升；
- 初始化顺序改变，低概率路径出现空引用或旧配置；
- 延后上传、注册或恢复任务，导致数据完整性变化。

验收需要同时看 TTID、TTFD、首屏 frame timeline、首个操作延迟、ANR/Crash、关键能力成功率和资源峰值。若 TTID 下降但 TTFD、交互或稳定性变差，这次改动只能算成本转移。

### 6. GC 只能由 trace 证明

启动阶段出现 GC 时，先检查分配来源、对象存活和堆增长：

- 大 JSON/Proto 解码是否创建重复中间对象；
- 依赖注入或反射扫描是否构造大量元数据；
- 图片、字体、Bitmap 或 native buffer 是否过早创建；
- 多个初始化任务是否同时制造分配峰值；
- 堆大小和 GC pause 是否与慢样本同一时间窗口相关。

看到 `HeapTaskDaemon`、GC slice 或 allocation spike，仍不能直接断言 GC 是全部瓶颈。要比较主线程 pause、Runnable 等待、并发 GC CPU 和关键路径重叠。

Hook ART 内部符号、暂停 GC daemon 或改写运行时策略依赖私有实现，会跨 Android 版本、ABI 与厂商构建失效，还可能把回收压力推到更危险的时点。应用默认方案应是减少分配、缩短对象存活、延后非关键对象和修复堆峰值。底层 hook 只适合作为隔离实验，不进入常规生产路径。

## 案例二：启动框架从散点入口演进为可治理任务

### 1. App Startup 解决哪一层

早期项目常见多个 SDK Provider、`Application.onCreate()` 和入口 Activity 各自初始化。AndroidX App Startup 可以让多个 initializer 共用一个 `InitializationProvider`，并通过 `dependencies()` 表达顺序；不需要自动初始化的组件可以移除 manifest metadata，改为手动懒初始化。

它有清晰边界：

- `InitializationProvider` 仍是 Provider，仍早于 `Application.onCreate()`；
- 自动发现的 initializer 会在 Provider 初始化调用链中执行；
- `dependencies()` 表达初始化先后，不提供任务优先级、超时、取消或线程切换；
- `Initializer.create()` 的重工作仍会阻塞调用它的线程；
- 移除单个 initializer 的自动初始化时，它的自动依赖也会受影响，需要重新检查手动入口。

因此，App Startup 适合合并 Provider 和显式描述小型同步初始化。首帧前的大型异步任务图需要独立调度设计。

### 2. 从“代码顺序”迁移到任务契约

启动任务不能只包含 `Runnable` 和 dependency list。建议把任务契约写成：

| 字段 | 必须回答的问题 |
| --- | --- |
| phase | Provider、Application、pre-first-frame、post-first-frame、on-demand 中哪一段 |
| process | 哪个进程执行，是否可能被多个进程重复运行 |
| hard dependencies | 缺少结果就不能执行的依赖 |
| soft dependencies | 超时或失败后可降级的依赖 |
| executor | 主线程、CPU 池、I/O 池或专用串行执行器 |
| result | 输出值、版本和生命周期 |
| timeout | 等待方 deadline；超时是否会取消底层工作 |
| failure policy | 阻断、降级、重试或跳过 |
| idempotence | 多入口、重试和进程重建是否安全 |
| metrics / owner | trace 名、线上指标、负责人和开关 |

`timeoutMs` 只限制等待方，不一定能停止已经开始的磁盘、网络或 Binder 工作。框架若声称支持取消，任务实现必须接受 cancellation token，并在底层操作可取消的位置检查。

### 3. DAG 优化看关键路径

总耗时由最长依赖链和主线程/资源竞争决定，不由所有任务耗时相加得到。把互不依赖的任务并发执行，只有在设备还有 CPU 或 I/O 余量时才可能缩短关键路径；低端设备上过量并发会让主线程和 RenderThread 更晚获得调度。

框架演进应分批进行：

1. 只接入清单、trace 和 owner，不改变原执行顺序。
2. 标记硬依赖、软依赖与首帧阶段，验证循环依赖和缺失依赖。
3. 移动一个风险较低的任务，保留旧路径开关。
4. 按设备档位观察 TTID、TTFD、线程 Runnable 时间和失败率。
5. 逐步扩大覆盖，任何批次都能回退到已验证顺序。

一次迁移同时改十几个任务、线程池和初始化顺序，出现回归时很难归因。任务框架自身也有类加载、对象创建、拓扑排序和 trace 成本，应进入启动预算。

### 4. 发布门禁使用项目基线

下面这些检查比统一的“主线程任务不得超过 10 ms”更可靠：

| 检查项 | 判定方式 | 失败动作 |
| --- | --- | --- |
| 新增 pre-first-frame 任务 | 必须有首屏需求、owner、trace 和回滚开关 | 缺任一项则不进入关键路径 |
| 关键路径增长 | 同设备、同入口、同编译模式下超过噪声带和预算 | 拆依赖、延后或取消变更 |
| 主线程长区间 | Perfetto 证明确有连续占用或同步等待 | 移除重工作或同步边 |
| task 超时/失败 | 灰度同 cohort 的失败率和降级成功率 | 关闭任务、修协议或恢复旧顺序 |
| manifest Provider 增长 | 检查 merged manifest 与进程归属 | 合并、手动初始化或接受并记录成本 |
| 首帧后资源竞争 | frame timeline、TTFD 与首个操作回归 | 降低并发、延后或按设备分级 |

阈值应绑定设备、构建、入口、编译状态、分位数和样本量。人眼可读的 trace 证据与机器门禁要使用同一 task ID，避免线上告警找不到代码责任点。

## 案例三：Baseline Profile 已生成，收益却无法复现

### 1. 先判断瓶颈是否受编译状态影响

Baseline Profile 可以减少被覆盖路径的解释执行和 JIT 预热，并引导 ART 做 profile-guided 编译。它无法缩短网络、Binder、锁、主线程磁盘 I/O、数据库迁移和业务等待。

| trace 现象 | Profile 相关性 | 下一步 |
| --- | --- | --- |
| 解释/JIT、类加载和首次执行位于关键路径 | 高 | 检查规则覆盖和编译状态 |
| 新装或升级后慢，稳定使用后明显改善 | 中到高 | 控制缓存、Cloud Profile 与本地运行时 profile 后复测 |
| 主线程等待文件、数据库、Binder 或锁 | 低 | 修复同步等待 |
| TTID 快，TTFD 等网络或数据 | 低到中 | 先拆内容 ready 路径，再看其中代码执行部分 |
| Compose 首次组合有较多首次执行 | 中到高 | 覆盖正确入口，并同时检查 composition 工作量 |

“多启动几次会变快”只能提示编译或缓存可能参与，不能单独证明 Profile 命中。页缓存、数据库缓存、网络连接和业务数据也会在重复运行中变热。

### 2. 四层证据缺一不可

| 层级 | 要证明的事实 | 推荐证据 |
| --- | --- | --- |
| 生成 | 脚本走了正确入口，规则随当前代码生成 | generator 断言、规则 diff、设备与工具链记录 |
| 构建 | 目标 release variant 消费并重写规则 | APK/AAB 中 binary profile、R8/AGP 构建日志 |
| 安装与编译 | 目标设备已拥有 profile-guided 编译状态 | `ProfileVerifier`、`dumpsys package dexopt` |
| 性能 | 同场景的编译状态差值超过噪声 | Macrobenchmark `None` vs `Partial(...Require)`、trace |

源码仓库有 `baseline-prof.txt`，不能证明 release 包携带二进制 profile；包内有 `baseline.prof`，不能证明设备已经完成编译；设备显示 `speed-profile`，也不能证明当前启动入口被规则覆盖。

### 3. 设计能解释因果的实验

本地 Profile 实验应固定：

- 同一 release APK、设备、入口、账号和数据；
- 同一网络响应、弹窗状态、电量和温度范围；
- 相同迭代次数与测试顺序；
- 只改变 Macrobenchmark 的 `CompilationMode.None()` 和 `CompilationMode.Partial(BaselineProfileMode.Require)`；
- 同时采集 TTID、TTFD、关键 trace 与功能正确性。

`BaselineProfileMode.Require` 可以在产物没有 profile 时让测试失败。`None` 构造无预编译的受控状态，`Partial` 构造 Profile 参与编译的状态。这个差值用于解释当前设备和场景中的编译收益，不代表线上所有“未使用 Profile”用户，因为线上还可能有 Cloud Profile、本地 JIT profile、后台 dexopt 和不同安装渠道。

若要比较两版 profile 规则，应保持业务代码和资源相同，只替换 profile 产物，并检查两边最终 APK、混淆映射和编译状态。代码也发生变化时，结果只能解释“整个版本组合”的差异。

### 4. Baseline Profile 与 Startup Profile 分开验收

两者可以来自同一套 generator，但消费方不同：

| 类型 | 消费阶段 | 改变什么 | 验收重点 |
| --- | --- | --- | --- |
| Baseline Profile | 设备安装/编译 | ART 对覆盖代码的编译状态 | binary profile、设备编译状态、`None`/`Partial` |
| Startup Profile | release 构建 | R8/D8 的启动 DEX 布局与读取局部性 | 构建配置、DEX 内容/布局、page fault 与同编译模式 benchmark |

比较 Startup Profile 布局收益时，两组必须保持 ART 编译状态一致；比较 Baseline Profile 编译收益时，应使用相同 APK 布局。把两项一起打开后只看总差值，无法说明各自贡献，也不能把两个独立实验的收益百分比直接相加。

更完整的生成、构建、安装和 Macrobenchmark 操作见[Baseline Profile 实战](./04-baseline-profile-practice.md)，DEX 布局见[Startup Profile 与 DEX 布局](./12-startup-profile-dex-layout.md)。

### 5. `reportFullyDrawn()` 的源码边界

Android 17 的 `Activity.reportFullyDrawn()` 会把 fully drawn 事件交给 system_server，并调用 `VMRuntime.notifyStartupCompleted()`。`ActivityMetricsLogger.notifyFullyDrawn()` 若发现 Activity 窗口尚未绘制，会暂存请求，等窗口完成绘制后再记录；它还会把 fully drawn 时间写入启动统计。

这两个源码点说明 fully drawn 既是诊断信号，也参与系统对启动阶段的理解。上报过早会把未完成工作排除在 TTFD 之外，上报过晚会扩大启动窗口并可能影响优化。Profile 场景应把条件绑定到核心 UI 和数据可用，不能为了 benchmark 数字提前调用。

## 一份可直接使用的复盘模板

下面的 Markdown 模板用于 PR、故障复盘或性能专项文档。字段可以裁剪，证据、测量条件和风险不应省略：

```markdown
# <入口 / 问题> 启动优化复盘

## 1. 范围
- App commit / versionCode:
- Android: 17 / API 37 / android-17.0.0_r1
- 设备 / RAM / ABI / 温度与电量:
- release variant / R8 / 编译模式:
- 入口 / 账号 / 数据 / 网络:
- cold / warm / hot 定义:
- 统计窗口、样本量、采样率:

## 2. 用户症状
- TTID P50 / P90:
- TTFD P50 / P90 / 完成率:
- 首屏 ANR / Crash / 退出:
- 受影响 cohort:

## 3. 证据
- ApplicationStartInfo 区间:
- Macrobenchmark 报告:
- Perfetto trace:
- task / Provider / manifest:
- 首次出现的版本、配置或实验:

## 4. 根因假设
- 假设:
- 支持证据:
- 反证:
- 仍未知:

## 5. 单变量改动
- 改动:
- 为什么会影响目标区间:
- 风险:
- 回滚开关:

## 6. 验证
- 线下 before / after 分布:
- 线上同 cohort 灰度:
- TTID / TTFD / frame / ANR / Crash / 业务 guardrail:
- 结果是否超过噪声与预算:

## 7. 后续
- CI / 灰度门禁:
- task owner:
- Profile / 脚本更新:
- 未解决问题与复查日期:
```

模板要求把“观察”和“推断”分开。根因假设可以失败，但必须写出支持证据和反证；这样下一位排查者不会重复同一条无效路径。

## 复盘中常见的错误结论

| 写法 | 问题 | 改写方式 |
| --- | --- | --- |
| “延迟初始化后启动提升 30%” | 没有起止点、设备、样本和 TTFD 风险 | 写明移动了哪个 task、影响哪个区间、before/after 分布与 guardrail |
| “Provider 越少越快” | Provider 工作量与进程归属比数量更关键 | 检查 merged manifest、初始化内容、顺序和 trace |
| “并行后总耗时等于最长任务” | 忽略依赖、线程切换、CPU/I/O 竞争 | 用关键路径和 Runnable/Running 时间验证 |
| “出现 GC，所以 GC 是根因” | GC 可能是分配结果，也可能未阻断关键线程 | 对齐 pause、并发 GC CPU、分配来源和主线程 |
| “Profile 文件存在，所以已生效” | 缺构建、安装/编译和性能证据 | 完成四层验收 |
| “本地快了，线上会同比例变快” | 线上编译、设备、入口和缓存分布不同 | 用本地建立因果，线上验证范围 |
| “TTID 下降，优化完成” | 工作可能移动到首帧后 | 同时检查 TTFD、frame、首个操作和稳定性 |

## Review 清单

- [ ] 问题陈述包含版本、启动类型、入口、设备和安装状态。
- [ ] before/after 使用同一构建条件、场景和统计口径。
- [ ] 平台区间、应用 task 和 trace 能互相对齐。
- [ ] Provider 清单来自 merged manifest，包含进程归属。
- [ ] 首帧前任务区分最小能力、硬依赖和可降级依赖。
- [ ] timeout 与 cancellation 的语义分别验证。
- [ ] 延后任务同时检查 TTFD、首屏帧和首个操作。
- [ ] GC 结论有 pause、CPU、分配和关键路径证据。
- [ ] Baseline Profile 完成生成、构建、编译和性能四层验收。
- [ ] Baseline Profile 与 Startup Profile 使用独立实验口径。
- [ ] 收益数字带设备、构建、样本量、分位数和置信范围。
- [ ] 灰度包含 Crash、ANR、业务成功率和回滚条件。
- [ ] 复盘产出 owner、门禁和下一次复查条件。

## 小结

大型 App 启动优化通常会同时遇到初始化扩散、任务依赖、编译状态和首帧后资源竞争。复盘时不要按“做过的优化技巧”组织材料，应沿着用户症状、阶段区间、代码证据、单变量实验和线上 cohort 展开。

Application 精简、任务框架和 Baseline Profile 各自解决不同问题。前者减少关键路径工作，任务框架约束执行阶段与依赖，Profile 改善覆盖代码的编译与布局条件。把边界写清、把副作用放进 guardrail、把证据留在模板里，下一次回归才有可复用的起点。

## 参考资料

- [Android 17 `Activity.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/Activity.java)：`reportFullyDrawn()` 与 `VMRuntime.notifyStartupCompleted()`。
- [Android 17 `ActivityMetricsLogger.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/ActivityMetricsLogger.java)：`notifyFullyDrawn()` 的窗口等待与启动统计。
- [App startup time](https://developer.android.com/topic/performance/vitals/launch-time)：TTID、TTFD、cold/warm/hot 与 excessive startup。
- [App Startup](https://developer.android.com/topic/libraries/app-startup)：单一 Provider、initializer 依赖和手动初始化。
- [Baseline Profiles overview](https://developer.android.com/topic/performance/baselineprofiles/overview)：Baseline Profile、Cloud Profile 与 Startup Profile 边界。
- [Create Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile)：生成场景、构建配置与 Macrobenchmark。
- [Debug Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles)：产物与设备编译状态验证。
- [Startup Profiles and DEX layout](https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations)：构建期 DEX 布局优化。
