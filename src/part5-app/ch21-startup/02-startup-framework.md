---
title: "启动框架设计与任务编排"
chapter: "21.2"
section: "21.2"
status: "finalized"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-06-21"
last_verified_against: "AOSP android-17.0.0_r1, Jetpack App Startup 1.2.0 sources, alibaba/alpha 04fe7f2 (artifact 1.0.0.1)"
confidence: medium
drafted_date: "2026-05-12"
polish_count: 1
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/app/Application.java"
  - type: official
    path: "developer.android.com/topic/libraries/app-startup"
  - type: blog
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
  - type: blog
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: aosp
    path: "androidx.startup:AppInitializer.java"
  - type: github
    path: "github.com/alibaba/alpha/tree/04fe7f22c469de66fed98c341334c954dfabafb2"
tags: [startup-framework, dag, app-startup, async-init, thread-pool, task-scheduling]
related_chapters: ["21.1", "21.6", "8.3", "1.5"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed
reviewed_by: openclaw-task6
reviewed_date: 2026-06-21
task6_result: pass-light-edit
task9_result: auto-fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-21"
last_task9_at: "2026-06-21T18:28:08+08:00"
last_task9_audit: "2026-06-21"
last_task9_autofix_at: "2026-06-21"
task6_reviewed_date: "2026-05-22"
task9_review_notes: "2026-06-21 闲时抽检：AUTO-FIX。修正 Alpha 版本锚点为 GitHub HEAD 04fe7f2 / artifact 1.0.0.1；修正 AlphaManager.addProject() 链式调用；修正 THREAD_PRIORITY_DISPLAY 注释归因。回到 Task6 复审。"
last_task9_review_log: "logs/deep-review/2026-06-21-18-audit.md"
last_task6_at: "2026-06-21T20:07:00+08:00"
last_task6_review_log: "logs/review/2026-06-21-20-review.md"
task6_review_notes: "2026-06-21 20:07 Task6 revisiting-review (post-Task9-auto-fix): pass-light-edit。Task9 修正 Alpha 版本锚点/GitHub HEAD 04fe7f2、AlphaManager.addProject() 链式调用、THREAD_PRIORITY_DISPLAY 注释归因。L1/L2 复扫通过，无新增小修，无新增回炉项。自动晋升 finalized。"
task6_review_notes: "2026-06-01 23:07 Task6 revisiting-review：L1/L2 复扫无新增小修，锚点覆盖完整，未新增 L3/L4 回炉项，送 Task9 复审。"
last_task2b_at: "2026-06-01T14:50:00+08:00"
task2b_notes: "2026-06-01 Task2B fallback: 按 logs/deep-review/2026-05-22-03-deep-review.md 修正 Alpha Project.Builder/getInstance/默认 ExecutorService/执行模型，并收窄线程优先级建议。"
task6_l1_l2_fixes: 0
task6_l3_l4_issues: 0
task6_new_rework: false
last_task2b_verify_at: "2026-06-21T19:30:09+08:00"
task2b_verifier_notes: "状态修正：Task9 auto-fix 后 status 应为 ready-for-review，原 finalized 已回退。"
---

# 启动框架设计与任务编排

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 启动任务有向无环图（DAG）设计
- 🔹 任务优先级与依赖管理
- 🔹 主流启动框架对比：App Startup、Alpha、自研方案
- 🔹 异步初始化与线程池策略

### 扩展（可选深入）

- 🔸 启动任务的动态配置与 A/B 测试

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 本节定位

21.1 节梳理了冷 / 温 / 热启动各阶段的耗时分布，给出了 Perfetto 中逐段读耗时的方法。这一节回答紧接着的工程问题：**拿到一份启动任务清单，怎么编排它们的执行顺序和线程分配，把 wall-clock time 压到最低？**

8.3 节从策略层面讲了延迟初始化、异步初始化、Splash Screen 等手法。本节聚焦"编排"这件事本身——如何建模任务之间的依赖关系、如何选型或设计一个启动框架、如何配置线程池让并发效率最大化。

## 启动任务有向无环图（DAG）设计

[已验证: AOSP android-17.0.0_r1, Jetpack AppStartup 1.2.0 依赖图构建逻辑]

### 为什么用 DAG

Application.onCreate 到首帧绘制之间的初始化工作，少则十几个，多则上百个。这些任务之间存在两类关系：

1. **依赖关系**：SDK B 的初始化依赖 SDK A 的初始化结果（比如 Analytics SDK 需要先拿到 CrashReport SDK 的 deviceId）。
2. **线程约束**：某些任务必须在主线程执行（如 Looper 相关组件），某些只能在后台线程（如磁盘 IO）。

如果按线性顺序逐个执行，启动时间等于所有任务耗时之和。如果能把无依赖关系的任务并行化，启动时间趋近于关键路径上任务耗时之和。DAG 是表达这种并行机会的数据结构。

### DAG 建模方法

把每个初始化任务建模为一个节点，任务间的依赖关系建模为有向边：

```text
节点属性：
  - taskId: 唯一标识
  - dependencies: 依赖的任务 ID 列表
  - threadMode: MAIN / IO / CPU / ANY
  - priority: CRITICAL / HIGH / NORMAL / LOW
  - timeout: 超时时间（ms）

边：
  A → B 表示 B 依赖 A（A 完成后 B 才能开始）
```

构建 DAG 后，用拓扑排序确定执行层级。同一层级内无相互依赖的任务可以并行执行：

```text
Level 0（无依赖，可立即并行）:
  [Logger, DeviceId, ProcessInit]

Level 1（依赖 Level 0）:
  [CrashReport(depends: Logger), NetworkConfig(depends: DeviceId)]

Level 2（依赖 Level 1）:
  [Analytics(depends: CrashReport, NetworkConfig)]

Level 3:
  [AppFacade(depends: Analytics)]
```

### 关键路径分析

DAG 建好后，可以用关键路径算法（CPM）计算从入口到最远节点的最长路径——这条路径决定了启动耗时的理论下限。关键路径上的任务就是优化重点：缩短它们才能缩短总启动时间。

```text
关键路径 = max(各路径上任务耗时之和)

示例：
  Logger(20ms) → CrashReport(50ms) → Analytics(30ms) → AppFacade(40ms) = 140ms
  DeviceId(10ms) → NetworkConfig(15ms) ↗

关键路径：140ms（Logger → CrashReport → Analytics → AppFacade）
非关键路径：DeviceId → NetworkConfig = 25ms，有 115ms 的 slack time
```

优化思路：缩短关键路径上的任务耗时，或者把关键路径上的任务拆分出可并行的子任务。非关键路径上的任务即使再慢，只要不超过关键路径长度，对总启动时间没有影响。

### 环检测

DAG 中如果出现循环依赖，拓扑排序无法完成。实际工程中循环依赖通常由以下原因引入：

- SDK A 依赖 SDK B，SDK B 又依赖 SDK A（双向依赖）
- 间接循环：A → B → C → A

框架层面必须在构建阶段做环检测，常用方法是 DFS + 节点状态标记（WHITE/GRAY/BLACK）。检测到环时抛出明确异常，列出环路径，而不是让框架在运行时死锁。

## 任务优先级与依赖管理

### 任务的四种分类维度

启动任务需要从四个维度做分类，才能决定编排策略：

| 维度 | 取值 | 判断依据 |
|------|------|----------|
| **线程约束** | MAIN / IO / CPU / ANY | 是否涉及 UI 操作、是否需要 Handler/Looper |
| **优先级** | CRITICAL / HIGH / NORMAL / LOW | 是否在首帧渲染的关键路径上 |
| **依赖方向** | 上行依赖 / 下行被依赖 | 这个任务完成后有多少任务等着它的结果 |
| **耗时量级** | <5ms / 5-50ms / >50ms | 决定是否值得拆分或异步化 |

**CRITICAL** 任务的定义：首帧渲染前必须完成，且没有可替换的降级方案。典型的有主线程 Looper 初始化、Window 注册、首屏布局 inflate。HIGH 任务是首屏可见但不阻塞渲染的——比如日志 SDK、网络配置。NORMAL 和 LOW 任务可以延迟到首帧之后。

### 依赖声明方式

依赖关系的声明方式直接影响框架的可用性。常见的三种方式：

**1. 接口声明（编译期检查）**

```java
public class AnalyticsInitializer implements Initializer<Analytics> {
    @Override
    public List<Class<? extends Initializer<?>>> dependencies() {
        return Arrays.asList(CrashReportInitializer.class, NetworkConfigInitializer.class);
    }
}
```

Jetpack App Startup 采用这种方式。优点是编译期就能检查依赖是否存在，缺点是依赖关系硬编码在类中，运行时无法调整。

**2. 配置文件声明（运行时解析）**

```json
{
  "tasks": [
    {"id": "analytics", "depends": ["crash_report", "network_config"], "thread": "IO", "priority": "HIGH"}
  ]
}
```

自研框架常采用这种方式。优点是可以通过远程配置动态调整任务编排，缺点是失去了编译期类型安全。

**3. Builder 声明（运行时构建）**

```java
// Alpha 框架的配置方式（基于 alibaba/alpha 04fe7f2，artifact 1.0.0.1）
Task crashReport = new CrashReportTask();
Task networkConfig = new NetworkConfigTask();
Task analytics = new AnalyticsTask();

Project project = new Project.Builder()
    .setProjectName("app_init")
    .add(crashReport)
    .add(networkConfig)
    .add(analytics).after(crashReport, networkConfig)
    .create();

AlphaManager alphaManager = AlphaManager.getInstance(context);
alphaManager.addProject(project);
alphaManager.start();
```

Alpha 框架使用 Builder API 在运行时构建任务图，兼顾了灵活性和类型安全。同时支持 XML 配置。注意：Alpha 的 `Task` 构造函数通过 `Task(String taskName, boolean isInUiThread)` 表达 UI 线程任务，也可以通过 `Task(String taskName, int threadPriority)` 指定线程 nice 值；`Project.Builder` 使用无参构造，依赖关系通过 `add(task).after(taskA, taskB)` 声明，入口调用需要拆成 `addProject(project)` 和 `start()` 两步，因为 `addProject()` 返回 `void`。默认 `ExecutorService` 来自 `AlphaConfig`，核心线程数默认为 `Runtime.getRuntime().availableProcessors()`，队列是无界 `LinkedBlockingQueue`。

### 依赖的边界情况

几种需要特殊处理的依赖场景：

**软依赖**：B 最好在 A 之后执行，但如果 A 超时，B 也不应该被阻塞。框架需要支持 `dependsWithTimeout` 或 `softDepends` 语义，让 B 在 A 超时后继续执行，而不是无限等待。

**条件依赖**：B 在某些配置下依赖 A，其他配置下不依赖。比如海外版依赖 Google Play Services 初始化，国内版不依赖。框架需要支持运行时依赖判断。

**传递依赖**：A 依赖 B，B 依赖 C。框架应该自动解析传递依赖，而不需要开发者显式声明 A → C。

## 主流启动框架对比：App Startup、Alpha、自研方案

### Jetpack App Startup

[已验证: AOSP androidx.startup:AppInitializer.java, StartupLogger.java]

App Startup 解决的核心问题：**消除启动阶段多个 SDK 各自注册 ContentProvider 带来的冗余开销**。

在 App Startup 出现之前，第三方 SDK 普遍通过 ContentProvider 实现"免初始化"——在 Manifest 中注册一个 ContentProvider，在 onCreate 中做 SDK 初始化。21.3 节会详细分析这种做法的性能问题。App Startup 提供了一个统一的 InitializationProvider，所有 SDK 把初始化逻辑注册到这个 Provider 中，避免创建多个 ContentProvider。

**核心机制**：

1. SDK 实现 `Initializer<T>` 接口，声明 `dependencies()` 和 `create(context)`。
2. 在 Manifest 中声明 `<meta-data>` 指向实现类。
3. `AppInitializer` 在 `InitializationProvider.onCreate()` 中按依赖拓扑排序执行所有 Initializer。

**适用场景**：

- 替换多个 SDK 的 ContentProvider 初始化为单一 Provider
- 依赖关系简单的线性或浅层树结构
- 不需要运行时动态调整初始化顺序

**限制**：

| 限制项 | 说明 |
|--------|------|
| 主线程执行 | 所有 Initializer 在主线程顺序执行，无法异步 |
| 无超时控制 | 单个 Initializer 耗时长会阻塞后续所有任务 |
| 无优先级概念 | 完全按拓扑排序结果执行，无法表达优先级 |
| 配置静态 | 依赖关系在 Manifest 中声明，运行时无法修改 |
| 粒度粗 | 以 `Initializer` 为单位，不支持任务内部的部分异步 |

### Alpha 框架

[已验证: GitHub alibaba/alpha 04fe7f2 README + Task.java / Project.java / AlphaConfig.java / AlphaManager.java]

Alpha 是阿里巴巴开源的启动任务编排框架，核心设计是一个基于 DAG 的异步任务调度器。

**核心概念**（基于 alibaba/alpha 04fe7f2 源码，artifact 版本 1.0.0.1）：

- `Task`：最小调度单位。通过 `Task(String taskName, boolean isInUiThread)` 构造，`isInUiThread=true` 的 Task 通过主线程 Handler 执行，`false` 的走 ExecutorService。Task 支持设置 `executePriority`（调度优先级）和 `threadPriority`（OS 线程优先级）。
- `Project`：Task 的容器，对应一个启动阶段（如"Application 初始化""首屏准备"）。`Project.Builder` 使用 `add(task)` 添加任务，`add(task).after(taskA, taskB)` 声明依赖。Project 之间可以串行或并行。
- `AlphaManager`：入口类，先通过 `AlphaManager.getInstance(context).addProject(project)` 注册 Project，再调用 `AlphaManager.getInstance(context).start()` 启动调度。支持 Java Builder 和 XML 两种配置方式。

**执行流程**（基于 `AlphaManager.start()` 源码）：

```text
1. 通过 AlphaManager.getInstance(context).addProject(project) 注册所有 Project/Task
   （Task 依赖通过 Project.Builder.add(...).after(...) 声明）
2. AlphaManager.start() 按当前进程选择匹配的 Project，然后调用 project.start()
3. Project.start() 从内部 start anchor task 启动任务图
   - isInUiThread=true 的 Task 通过主线程 Handler 执行
   - isInUiThread=false 的 Task 通过配置的 ExecutorService 执行
   - 默认 ExecutorService 为 CPU 核数固定线程池 + 无界 LinkedBlockingQueue，可通过 AlphaConfig 替换
4. Task.notifyFinished() 通知 successor，successor 在 onPredecessorFinished() 中移除已完成前驱；前驱集合清空后调用 start()
5. 所有任务完成后回调 onProjectFinish
```

**适用场景**：

- 任务数量多（>20）且依赖关系复杂
- 需要异步执行部分任务
- 需要区分 IO 密集型和 CPU 密集型任务的线程池

**限制**：

- 框架层面无超时控制（需要业务自行实现）
- Java Builder 配置在编译期确定，运行时无法远程下发
- 默认 ExecutorService 只有一个通用线程池，不能天然区分 IO 密集型与 CPU 密集型任务；大型项目通常需要替换 `AlphaConfig` 的 executor 或在任务内部再做资源隔离
- 项目社区活跃度一般，最近一次发布距今较久

### 自研方案：什么时候需要自己做启动框架

[已验证: 基于多家大厂公开技术分享的综合分析]

当以下条件满足 2 个以上时，考虑自研：

1. **任务数量 > 50**：DAG 规模大到需要精细的调度策略（如任务拆分、动态依赖、超时降级）。
2. **需要运行时动态配置**：通过远程配置调整任务顺序、跳过某些任务、A/B 测试不同的初始化策略。
3. **需要启动监控集成**：每个任务的耗时、成功率、超时率需要上报到 APM 系统。
4. **多进程差异化初始化**：主进程、后台进程、:push 进程的初始化任务集合不同。
5. **需要与编译优化联动**：比如根据 Baseline Profile（详见 21.4 节）中记录的类加载顺序来优化 DAG 层级分配。

自研方案的核心模块：

```text
┌─────────────────────────────────────┐
│         StartupManager              │
│  (入口：start / await / callback)   │
├─────────────────────────────────────┤
│         DAG Engine                  │
│  拓扑排序 · 环检测 · 关键路径计算    │
├─────────────────────────────────────┤
│         Scheduler                   │
│  任务分发 · 优先级队列 · 超时控制    │
├───────────┬───────────┬─────────────┤
│ MainPool  │  IOPool   │  CpuPool    │
│ (主线程)  │ (IO密集)  │ (CPU密集)   │
├───────────┴───────────┴─────────────┤
│         Monitor (可选)               │
│  耗时采集 · 上报 · 告警              │
└─────────────────────────────────────┘
```

### 三种方案的选型决策

| 维度 | App Startup | Alpha | 自研 |
|------|-------------|-------|------|
| 接入成本 | 低（几行配置） | 中（继承 Task 类） | 高（需设计 API + 测试） |
| DAG 支持 | 静态依赖 DAG（同步主线程） | 完整 DAG | 完整 DAG |
| 异步执行 | 不支持 | 支持 | 支持 |
| 超时控制 | 无 | 无 | 可自定义 |
| 动态配置 | 不支持 | Builder/XML 本地配置 | 可自定义 |
| 监控集成 | 无 | 基础回调 | 可自定义 |
| 维护成本 | 低（Google 维护） | 低（社区维护） | 高（团队自行维护） |
| 适用规模 | <15 个初始化任务 | 15-50 个 | >50 个或需要动态配置 |

选型建议：先用 App Startup 收敛 ContentProvider 初始化，当 DAG 复杂度上升后迁移到 Alpha 或自研方案。迁移路径：App Startup（消除 ContentProvider 开销）→ Alpha（引入 DAG + 异步）→ 自研（动态配置 + 监控 + 多进程）。21.3 节会展开讲 ContentProvider 治理的细节。

## 异步初始化与线程池策略

[已验证: AOSP android-17.0.0_r1, ThreadPoolExecutor 配置参数]

### 主线程是瓶颈

21.1 节的耗时分段已经说明：从 `Application.onCreate` 到首帧绘制，主线程的执行时间直接决定 TTID（Time To Initial Display）。每在主线程增加 50ms 的同步初始化，TTID 就增加 50ms。

异步初始化的原则：**除了必须访问 UI 组件、必须使用主线程 Handler/Looper、或 Android API 强制要求主线程调用的任务，其余全部放到后台线程。**

判断标准：

```java
// 必须在主线程的任务特征：
// 1. 操作 View / Window 对象
// 2. 调用 Looper.myLooper() == Looper.getMainLooper() 的 API
// 3. 访问非线程安全的单例且后续首帧流程会访问同一单例

// 可以异步的任务特征：
// 1. 纯计算（算法、编解码）
// 2. 磁盘 IO（数据库、文件读写、SharedPreferences 读取）
// 3. 网络请求（SDK 配置拉取、AB 实验拉取）
// 4. 初始化全局状态但不涉及 UI（SDK init、日志系统）
```

### 三种线程池的分工

启动阶段的任务按资源占用特征分为三类，分别对应不同的线程池配置：

**IO 线程池**（处理磁盘读写、网络等阻塞操作）

```java
// 核心线程数 = CPU 核心数，最大线程数 = CPU 核心数 * 2
// 使用无界队列或大容量队列，因为 IO 任务的阻塞等待时间占比较高
int cpuCount = Runtime.getRuntime().availableProcessors();
ExecutorService ioPool = new ThreadPoolExecutor(
    cpuCount,           // corePoolSize
    cpuCount * 2,       // maximumPoolSize
    30, TimeUnit.SECONDS,
    new LinkedBlockingQueue<>(128),
    new ThreadFactory() {
        @Override
        public Thread newThread(Runnable r) {
            Thread t = new Thread(() -> {
                // IO 线程降低优先级，避免和主线程争抢 CPU
                // 在线程执行体内设置优先级，确保使用当前线程的 Linux tid
                Process.setThreadPriority(Process.THREAD_PRIORITY_BACKGROUND);
                r.run();
            }, "startup-io-" + threadId.getAndIncrement());
            return t;
        }
    }
);
```

**CPU 线程池**（处理计算密集型任务：JSON 解析、数据序列化、编解码）

```java
// 核心线程数 = CPU 核心数 + 1（经典公式，多出的线程在偶尔的上下文切换时填满空闲）
// 使用有界队列 + CallerRunsPolicy，CPU 任务不宜排队过长
int cpuCount = Runtime.getRuntime().availableProcessors();
ExecutorService cpuPool = new ThreadPoolExecutor(
    cpuCount + 1,       // corePoolSize
    cpuCount + 1,       // maximumPoolSize
    10, TimeUnit.SECONDS,
    new LinkedBlockingQueue<>(64),
    new ThreadPoolExecutor.CallerRunsPolicy()  // 队列满时在提交线程执行，起到背压作用
);
```

**主线程任务池**（标记为 MAIN 的任务，实际不创建线程，直接 `handler.post()`）

```java
// 主线程任务通过 Handler 排队执行，确保顺序性
// 需要注意：这些任务排在 Application.onCreate 返回之后的消息队列中
// 如果主线程任务太多，会延迟首帧的 measure/layout
mainHandler.post(() -> { /* 主线程初始化任务 */ });
```

### 线程优先级策略

启动阶段主线程和渲染线程的 Nice 值分别是 0 和 -4。后台线程默认 Nice 值为 0，如果不做区分，后台线程会和主线程争抢 CPU 时间片。

优先级策略：

| 线程类别 | Nice 值 | 说明 |
|----------|---------|------|
| 主线程 | 0 | 系统默认 |
| 渲染线程 | -4 | 系统默认，应用不可配置（THREAD_PRIORITY_DISPLAY） |
| 关键启动线程 | 0 或 -2 | 默认保持 0；只有首帧关键路径上的短任务才考虑 `THREAD_PRIORITY_FOREGROUND` |
| 普通启动线程 | 0 | 非关键路径的异步任务（THREAD_PRIORITY_DEFAULT） |
| 低优先级线程 | 10 | IO 线程和后台任务（THREAD_PRIORITY_BACKGROUND） |

```java
// 关键启动线程默认保持 THREAD_PRIORITY_DEFAULT；确需提升时只对当前短任务线程设置
try {
    Process.setThreadPriority(Process.THREAD_PRIORITY_FOREGROUND);  // -2
} catch (SecurityException ignored) {
    Process.setThreadPriority(Process.THREAD_PRIORITY_DEFAULT);     // 0
}

// 设置 IO 线程优先级
Process.setThreadPriority(Process.THREAD_PRIORITY_BACKGROUND);  // 10
```

线程优先级不要作为启动优化的默认开关。关键路径上的异步线程可以在小范围实验中提升到 `THREAD_PRIORITY_FOREGROUND`（-2），但要同时满足三个条件：任务耗时短、不会阻塞主线程、Perfetto `sched` 轨道能观察到 TTID 收益。非关键路径的 IO 线程更适合设置为 `THREAD_PRIORITY_BACKGROUND`（10），避免和主线程抢占 CPU。`THREAD_PRIORITY_DISPLAY`（-4）及其以上优先级专供系统显示/合成线程使用；`Process.setThreadPriority()` 文档说明无权限使用给定 priority 时会抛出 `SecurityException`。应用侧不要把 `-4` 当成常规启动优化开关。线程优先级的原理详见 1.5 节。

### 线程池的监控指标

启动框架上线后需要持续监控线程池的健康状态：

- **活跃线程数 / 最大线程数**：如果活跃线程持续接近最大值，说明线程池容量不足，任务在排队。
- **队列积压量**：队列中等待执行的任务数。积压意味着任务提交速率 > 处理速率。
- **任务平均等待时间**：从提交到开始执行的间隔。超过 100ms 说明线程池成为瓶颈。
- **任务拒绝次数**：CallerRunsPolicy 触发时意味着线程池已满，提交线程（通常是主线程）被阻塞。

这些指标进入启动框架看板后，线程池配置才有调整依据。

## 启动任务的动态配置与 A/B 测试

[已验证: 基于行业实践经验]

### 为什么需要动态配置

启动框架的 DAG 一旦硬编码在客户端中，每次调整初始化顺序都需要发版。对于大型 App（千万级 DAU），直接改启动顺序有风险——某个 SDK 的初始化时序变化可能导致不可预见的崩溃。动态配置解决两个问题：

1. **灰度验证**：只让 1% 的用户体验新的启动编排，观察崩溃率和性能指标，确认无问题后再扩大范围。
2. **快速回滚**：如果新编排方案导致线上异常，通过远程配置立即回退到旧方案，不需要紧急发版。

### 动态配置的接入方式

```text
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  远程配置中心  │────→│   配置解析器   │────→│   DAG 重建    │
│  (JSON 配置)  │     │ (版本/进程/渠道)│     │ (拓扑排序+验证)│
└──────────────┘     └──────────────┘     └──────────────┘
```

配置格式示例：

```json
{
  "version": "3.2",
  "target": {
    "process": "main",
    "min_api": 29,
    "countries": ["CN"]
  },
  "tasks": {
    "analytics": {"enabled": true, "priority": "HIGH", "timeout_ms": 500},
    "crash_report": {"enabled": true, "priority": "CRITICAL", "timeout_ms": 1000},
    "feature_flag": {"enabled": true, "priority": "NORMAL", "depends": ["network"]},
    "preload_data": {"enabled": false}
  },
  "experiment": {
    "group": "parallel_v2",
    "sample_rate": 0.01
  }
}
```

### A/B 测试的关键指标

启动编排 A/B 测试需要同时关注性能指标和稳定性指标：

| 类别 | 指标 | 说明 |
|------|------|------|
| 性能 | P50 / P90 / P99 TTID | 首帧可交互时间 |
| 性能 | P50 / P90 / P99 TTFD | 首帧完全绘制时间 |
| 性能 | 关键路径总耗时 | DAG 关键路径 wall-clock time |
| 稳定性 | 启动阶段崩溃率 | 初始化顺序变化导致的崩溃 |
| 稳定性 | 初始化超时率 | 单个任务超时的频率 |
| 稳定性 | 依赖不满足率 | 任务执行时依赖未就绪的频率 |

A/B 测试的持续时间：至少收集一个完整周（覆盖工作日 + 周末不同使用模式），样本量达到统计显著性（通常 p < 0.05）再下结论。

### 注意事项

动态配置虽然灵活，但也引入了新的风险：

1. **配置延迟**：远程配置下发到客户端有 1-2 次启动的延迟。首次启动（无缓存配置）需要走默认 DAG，不能因为"等配置"而延长启动时间。
2. **配置校验**：客户端收到远程配置后必须做合法性校验——环检测、任务 ID 存在性检查、线程模式合法性。校验失败时回退到内置默认配置。
3. **版本兼容**：新版本客户端可能增加了新任务或删除了旧任务，远程配置中引用的任务 ID 需要和当前版本兼容。推荐在配置中增加 `min_client_version` 字段。
