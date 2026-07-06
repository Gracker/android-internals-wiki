---
title: "Startup Insights API 与启动性能可观测性"
chapter: "21.17"
section: "21.17"
status: ready-for-review
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
last_verified: "2026-07-06"
last_verified_against: "AOSP android-17.0.0_r1, frameworks/base/core/java/android/app/ApplicationStartInfo.java"
confidence: medium
drafted_date: "2026-07-06"
tags: [startup, insights, observability, api, metrics, performance-monitoring]
related_chapters: ["21.1", "21.2", "21.8", "8.1", "26.13"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-05"
gap_source: "研究素材/知识盲区"
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/app/ApplicationStartInfo.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityManager.java (android-17.0.0_r1)"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动速度？.md"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationStartInfo"
  - type: official
    path: "https://developer.android.com/about/versions/15/features"
---

# 21.17 Startup Insights API 与启动性能可观测性

## 为什么需要 Startup Insights API

21.8 节讨论了启动监控的基本方法：在关键节点打点、收集分位值、设置退化告警。但这套方案有一个根本局限——**应用代码只能感知从 `Application.onCreate()` 开始的部分**，进程创建、Zygote fork、类加载、资源初始化等阶段发生在应用代码执行之前，传统打点方案完全看不到。

开发者通常靠抓 Perfetto trace 来分析这些早期阶段，但 trace 是离线工具，无法用于线上持续监控。Google Play Vitals 提供了粗粒度的启动时间统计，但数据延迟大（最多 24 小时）、维度少（只有冷/温/热 + 分位值），且无法与应用自身埋点关联。

Android 15（API 35）引入的 `ApplicationStartInfo` 填补了这个空白：**系统以 Parcel 形式向应用提供从进程 fork 到首帧绘制的完整启动时间线，应用可以在运行时或启动完成后查询**。到 Android 17（API 37），该 API 进一步扩展了启动组件分类和自定义时间戳能力。

> **本节聚焦实战集成**。ApplicationStartInfo 的 API 字段详解和归因上报机制参见 26.13 节。本节回答的问题是：**拿到 ApplicationStartInfo 后，如何用于启动优化闭环**。

[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md — 从底层原理出发建立速度优化的认知体系]

## 🔹 Startup Insights API 定位与架构

### 启动可观测性工具谱系

| 工具 | 数据来源 | 覆盖阶段 | 线上可用 | 粒度 |
|------|----------|----------|----------|------|
| 手动打点 | 应用代码内 | Application.onCreate → 首帧 | ✅ | 自定义 |
| Perfetto trace | 内核 + 系统 服务 | 全链路（fork → 首帧 +） | ❌ 仅调试 | 函数级 |
| Google Play Vitals | 匿名聚合数据 | 冷/温/热启动耗时 | ✅ | 粗（P50/P90 等） |
| **ApplicationStartInfo** | **ActivityManagerService** | **fork → 首帧 + reportFullyDrawn** | **✅** | **阶段级（8 个里程碑）** |

`ApplicationStartInfo` 的独特价值在于：**系统提供的、线上的、覆盖进程创建到首帧的全链路时间线**。

### 数据流架构

```
ActivityManagerService (AMS)
  └─ ActiveLogs 记录每次进程启动
       └─ ApplicationStartInfo 对象构建
            ├─ 进程 fork 时间（来自 Zygote）
            ├─ Application/bindApplication 时间（来自 AMS）
            ├─ 首帧时间（来自 ViewRootImpl）
            └─ reportFullyDrawn 时间（来自应用调用）
                 │
                 ▼
  ActivityManager#getHistoricalProcessStartReasons()
  ActivityManager#addApplicationStartInfoCompletionListener()
```

应用有两种获取方式：

1. **主动查询**：`getHistoricalProcessStartReasons()` — 返回最近的启动记录列表，可在启动过程中或完成后调用
2. **被动监听**：`addApplicationStartInfoCompletionListener()` — 注册回调，在启动完成（首帧绘制或出错）后异步回调

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/app/ApplicationStartInfo.java]

## 🔹 关键 API 与数据模型

### 系统时间戳（8 个里程碑）

Android 17 的 `ApplicationStartInfo` 定义了 8 个系统级启动时间戳（`START_TIMESTAMP_*` 常量）：

| 常量 | 含义 | 对应阶段 |
|------|------|----------|
| `START_TIMESTAMP_LAUNCH` (0) | Launcher 触发启动的时刻 | 冷启动起点 |
| `START_TIMESTAMP_FORK` (1) | Zygote fork 完成时间 | 进程创建完成 |
| `START_TIMESTAMP_APPLICATION_ONCREATE` (2) | `Application.onCreate()` 调用时间 | 应用代码起点 |
| `START_TIMESTAMP_BIND_APPLICATION` (3) | `bindApplication()` 完成时间 | 应用绑定完成 |
| `START_TIMESTAMP_FIRST_FRAME` (4) | 首帧绘制完成时间 | 用户可见 |
| `START_TIMESTAMP_FULLY_DRAWN` (5) | `reportFullyDrawn()` 调用时间 | 应用自定义终点 |
| `START_TIMESTAMP_INITIAL_RENDERTHREAD_FRAME` (6) | RenderThread 初始帧时间 | 渲染线程就绪 |
| `START_TIMESTAMP_SURFACEFLINGER_COMPOSITION_COMPLETE` (7) | SurfaceFlinger 合成完成 | 画面真正上屏 |

> ⚠️ `START_TIMESTAMP_FULLY_DRAWN` 不保证一定有值——只有应用主动调用 `Activity.reportFullyDrawn()` 才会记录。
> ⚠️ `START_TIMESTAMP_LAUNCH` 在 `START_COMPONENT_SERVICE` 类型的启动中可能不准确（见源码注释）。

[已验证: AOSP android-17.0.0_r1, ApplicationStartInfo.java START_TIMESTAMP_* 常量定义]

### 启动类型与原因

**启动类型**（`getStartType()`）：
- `START_TYPE_COLD`：从零开始的冷启动（进程不存在）
- `START_TYPE_WARM`：温启动（进程已存在但 Activity 需重新创建）
- `START_TYPE_HOT`：热启动（Activity 已在栈中，如返回）

**启动原因**（`getReason()`）：12 种系统定义原因，包括 `LAUNCHER`（用户点击图标）、`PUSH`（推送消息）、`ALARM`（闹钟唤醒）、`SERVICE`（服务启动）、`JOB`（JobScheduler）、`BROADCAST`（广播接收）、`CONTENT_PROVIDER`（内容提供者访问）等。

**启动组件**（`getStartComponent()`，Android 17+，受 `FLAGS_APP_START_INFO_COMPONENT` 门控）：
- `START_COMPONENT_ACTIVITY` / `START_COMPONENT_BROADCAST` / `START_COMPONENT_CONTENT_PROVIDER` / `START_COMPONENT_SERVICE` / `START_COMPONENT_OTHER`

这个分类对启动优化非常有价值：**可以区分"用户感知的 Activity 启动"和"后台 Service/Broadcast 触发的进程创建"**，避免将后台拉活的时间统计进用户体验指标。

### 开发者自定义时间戳

Android 17 在系统时间戳之外预留了 **开发者自定义时间戳区间**（key 21-30，对应 `START_TIMESTAMP_RESERVED_RANGE_DEVELOPER_START` 到 `START_TIMESTAMP_RESERVED_RANGE_DEVELOPER`）。

应用可通过 `addStartupTimestamp(key, timestampNanos)` 注入自己的业务里程碑，比如「首页数据加载完成」「首屏列表渲染完成」「广告展示完成」等，实现与系统时间戳的统一分析。

[已验证: AOSP android-17.0.0_r1, ApplicationStartInfo.java, START_TIMESTAMP_RESERVED_RANGE_* 常量及 addStartupTimestamp() 方法]

## 🔹 与 Perfetto Trace 的协同分析

### 两者的互补关系

Perfetto trace 和 ApplicationStartInfo 不是替代关系，而是**定位→验证**的协同关系：

| 场景 | ApplicationStartInfo | Perfetto Trace |
|------|---------------------|----------------|
| 线上持续监控 | ✅ 每次启动自动获取 | ❌ 需手动/条件触发 |
| 函数级瓶颈定位 | ❌ 只有阶段级粒度 | ✅ 精确到函数 |
| 启动耗时分位数统计 | ✅ 可聚合计算 P50/P90/P99 | ❌ 难以大规模采集 |
| 回归检测 | ✅ 对比版本间各阶段耗时 | ❌ 不适用 |
| 异常启动归因 | ✅ 通过 reason/component 分维度 | ✅ 可深入定位 |

### 实战协同工作流

1. **ApplicationStartInfo 发现问题**：线上监控发现某版本冷启动 P90 从 1.2s 飙升到 2.8s
2. **分析阶段分布**：拆解时间戳发现 `FORK → APPLICATION_ONCREATE` 阶段正常（200ms），但 `APPLICATION_ONCREATE → FIRST_FRAME` 从 800ms 涨到 1800ms
3. **定位为应用代码问题**：不是进程创建或类加载慢，而是 `Application.onCreate()` 到首帧之间的业务逻辑变慢
4. **Perfetto trace 深入**：在开发环境用 Perfetto 抓 trace，定位到具体函数（如某个 SDK 初始化阻塞主线程）

### 从 Perfetto trace 提取启动阶段的 SQL 参考

```sql
-- 提取 ApplicationStartInfo 相关的 trace event
SELECT
  ts,
  name,
  EXTRACT_ARG(arg_set_id, 'reason') AS start_reason,
  EXTRACT_ARG(arg_set_id, 'start_type') AS start_type,
  EXTRACT_ARG(arg_set_id, 'startup_state') AS startup_state
FROM slice
WHERE name LIKE '%ApplicationStart%' OR name LIKE '%startup%'
ORDER BY ts;

-- 结合 FrameTimeline 判定真正可交互时间
SELECT
  s.ts AS frame_ts,
  s.name AS frame_name,
  ft.do_frame_ms AS frame_duration,
  ft.jank_type AS jank_type
FROM slice s
JOIN experimental_frame_timeline ft ON s.ts = ft.ts
WHERE s.name LIKE '%firstFrame%' OR s.name LIKE '%Choreographer%'
ORDER BY s.ts
LIMIT 20;
```

> [待验证: Perfetto trace event 格式可能因 Android 版本而异，以上 SQL 适用于 Perfetto v50+，建议在目标设备上验证实际 track 名称]

[结构参考: Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动速度？.md — 通过 HeapTaskDaemon 分析定位启动 GC 卡顿]

## 🔹 Android 17 启动可观测性增强

### Android 15 → 16 → 17 演进

| 能力 | Android 15 (API 35) | Android 16 (API 36) | Android 17 (API 37) |
|------|---------------------|---------------------|---------------------|
| ApplicationStartInfo 基础字段 | ✅ pid/uid/reason/state | ✅ + 启动时间戳 | ✅ + 更多时间戳 |
| `getHistoricalProcessStartReasons()` | ✅ | ✅ | ✅ |
| `addApplicationStartInfoCompletionListener()` | ✅ | ✅ | ✅ |
| 启动时间戳（LAUNCH→FIRST_FRAME） | 部分 | ✅ 7 个时间戳 | ✅ 8 个时间戳（+SurfaceFlinger 合成） |
| 开发者自定义时间戳（key 21-30） | ❌ | ❌ | ✅ 新增 |
| `getStartComponent()` 分类 | ❌ | ❌ | ✅ 新增（门控 Flag） |
| `getLaunchMode()` | ❌ | 部分 | ✅ |
| `wasForceStopped()` | ✅ | ✅ | ✅ |
| Intent strip（防止大数据泄漏） | ❌ | ❌ | ✅ 优化 |

### Android 17 的两个关键增强

**1. 开发者自定义时间戳（key 21-30）**

之前只能依赖系统定义的 8 个里程碑。现在应用可以注入自己的业务节点：

```kotlin
// Android 17+ 开发者自定义时间戳示例
val startInfo = activityManager.getHistoricalProcessStartReasons(1).firstOrNull()
startInfo?.addStartupTimestamp(21, SystemClock.elapsedRealtimeNanos()) // 首页数据加载完成
startInfo?.addStartupTimestamp(22, SystemClock.elapsedRealtimeNanos()) // 首屏渲染完成
```

> 注意：key 必须在 `START_TIMESTAMP_RESERVED_RANGE_DEVELOPER_START`(21) 到 `START_TIMESTAMP_RESERVED_RANGE_DEVELOPER`(30) 范围内。

**2. 启动组件分类（`getStartComponent()`）**

通过 `@FlagsAppStartInfoComponent` flag 门控，可精确区分启动是由 Activity、Broadcast、ContentProvider 还是 Service 触发。对于**多进程应用**和**后台拉活场景**，这个分类能帮助过滤掉非用户感知的启动，避免污染启动性能指标。

[已验证: AOSP android-17.0.0_r1, ApplicationStartInfo.java START_TIMESTAMP_RESERVED_RANGE_* 及 START_COMPONENT_* 常量]

## 🔹 生产环境启动监控集成

### 接入 APM 平台的架构

```
┌─────────────────────────────────────────┐
│                应用进程                   │
│                                          │
│  Application.onCreate()                  │
│    └─ APM Agent 初始化                   │
│         └─ 注册 ApplicationStartInfo     │
│            CompletionListener            │
│              │                           │
│              ▼ (启动完成后异步回调)       │
│  ┌──────────────────────────────┐        │
│  │ ApplicationStartInfo 处理    │        │
│  │  ├─ 提取 8 个系统时间戳      │        │
│  │  ├─ 计算阶段耗时差值         │        │
│  │  ├─ 按启动类型/原因分维度    │        │
│  │  └─ 上报到 APM 后端          │        │
│  └──────────────────────────────┘        │
└─────────────────────────────────────────┘
                    │
                    ▼ HTTPS
┌─────────────────────────────────────────┐
│            APM 后端                      │
│  ├─ 按版本/设备/OS 分维度聚合            │
│  ├─ P50/P90/P99 分位数计算              │
│  ├─ 阶段耗时分布对比（版本间回归）       │
│  └─ 异常检测与告警                       │
└─────────────────────────────────────────┘
```

### 基线设定建议

启动基线不能只有一个数字。建议**按维度分层**设定：

| 维度 | 示例基线 | 说明 |
|------|----------|------|
| 冷启动 P50 | < 800ms | 50% 用户的启动体验 |
| 冷启动 P90 | < 1500ms | 90% 用户体验（长尾更重要） |
| 冷启动 P99 | < 3000ms | 极端情况但影响差评率 |
| 温启动 P90 | < 600ms | 进程已存在的场景 |
| FORK→ONCREATE P90 | < 300ms | 进程创建阶段（系统开销） |
| ONCREATE→FIRST_FRAME P90 | < 1000ms | 应用代码阶段（可控部分） |

> 基线值应**按设备性能分层**：旗舰机/中端机/低端机的基线应不同。可以用设备内存（如 ≤4GB / 4-8GB / >8GB）或 SoC 等级（如 Go Edition / 标准 / 旗舰）作为分层维度。

### 启动异常检测策略

1. **版本间回归**：新版本某阶段 P90 环比增长 >20% → 自动告警
2. **分位数发散**：P99/P50 比值突然增大（说明长尾恶化）→ 排查极端 case
3. **启动原因异常**：`START_REASON_PUSH` 类型的启动占比突增 → 可能是推送频率过高
4. **启动失败率**：`STARTUP_STATE_ERROR` 占比 >0.1% → 系统级问题

## 🔹 与 Jetpack Metrics 库的对比

Google 提供了 `androidx.metrics:metrics-performance` 库，面向 **Library 开发者** 度量自身组件的启动耗时。两者的定位互补：

| 维面 | ApplicationStartInfo | Jetpack Metrics |
|------|---------------------|-----------------|
| **目标用户** | 应用开发者 / APM 平台 | Library / SDK 开发者 |
| **数据来源** | ActivityManagerService（系统） | Library 内部打点 |
| **覆盖范围** | 进程级完整启动链路 | Library 自身初始化耗时 |
| **线上可用** | ✅ API 35+ | ✅ 所有版本 |
| **最低 API** | 35 (Android 15) | API 14+ |
| **粒度** | 阶段级（8 个里程碑） | 自定义（Library 控制） |

### 同时使用的策略

- **Application 开发者**：用 ApplicationStartInfo 做整体启动监控，用 Jetpack Metrics 收集第三方 SDK 的启动耗时作为归因补充
- **Library 开发者**：用 Jetpack Metrics 向宿主应用报告自身启动耗时，不依赖 ApplicationStartInfo 的系统权限

## 🔸 扩展：启动优化闭环（测量→分析→优化→验证）

启动优化不是一次性工作，而是持续迭代的闭环。21.1-21.7 节覆盖了具体的优化手段，这里从可观测性角度串联闭环：

### 测量（Measure）

- 每次 SDK 集成后，用 Macrobenchmark（参见 14.27）跑 baseline
- 线上持续收集 ApplicationStartInfo 的 8 个时间戳
- 按启动类型/原因/设备分层统计

### 分析（Analyze）

- 定位最耗时的阶段（通常是 `ONCREATE → FIRST_FRAME`）
- 细分该阶段的主线程 trace：SDK 初始化、布局 inflate、数据加载
- 检查 `START_REASON` 分布，确认是否非 Activity 启动污染了数据

### 优化（Optimize）

根据 21.1-21.7 节的具体手段：异步初始化（21.6）、Baseline Profile（21.4）、Splash Screen（21.5）、GC 抑制（21.13）等。

### 验证（Verify）

- Macrobenchmark 验证优化效果（A/B 对比）
- 灰度发布后观察 ApplicationStartInfo 各阶段耗时变化
- 确认 P90 改善的同时 P99 没有退化

> **关键指标**：不要只看均值。P90 和 P99 更能反映用户真实体验。版本发布后，P90 退化 >10% 就应该考虑回滚或修复。

## 小结

ApplicationStartInfo 是 Android 15+ 提供的系统级启动可观测性 API，到 Android 17 进一步扩展了自定义时间戳和组件分类。它填补了「传统打点看不到进程创建阶段」和「Perfetto trace 无法线上使用」之间的空白，使应用开发者能够建立完整的启动优化闭环：系统级测量 → 精确定位 → 针对性优化 → 数据验证。

对于 Part 5 的实战目的而言，关键不是记住 API 字段（详见 26.13），而是**将 ApplicationStartInfo 接入线上监控体系，用它驱动启动优化的持续迭代**。

---

*Drafted by OpenClaw Task 2A on 2026-07-06*
