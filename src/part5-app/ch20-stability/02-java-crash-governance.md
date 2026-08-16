---
title: Java Crash 治理
chapter: '20.2'
section: '20.2'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-08-14'
last_verified_against: AOSP android-17.0.0_r1; Android Developers crash docs; kotlinx.coroutines 1.11.0 API and exception-handling docs current on 2026-08-14
confidence: medium-high
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
pipeline_stage: ready-to-publish
sources:
- type: clippings-structure-ref
  path: Clippings/Android 应用稳定性剖析与优化 - Java Crash 监控：实现自定义 Crash 处理器.md
- type: clippings-structure-ref
  path: Clippings/Android 应用稳定性剖析与优化 - Java 堆栈：深入了解 Throwable.md
- type: aosp
  path: frameworks/base/core/java/com/android/internal/os/RuntimeInit.java
- type: official
  path: developer.android.com/reference/java/lang/Thread.UncaughtExceptionHandler
  url: https://developer.android.com/reference/java/lang/Thread.UncaughtExceptionHandler
- type: official
  path: https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-coroutine-exception-handler/
tags:
- java-crash
- exception-handling
- uncaughtexceptionhandler
- stability
related_chapters:
- '20.1'
- '20.7'
- '1.7'
---

# Java Crash 治理

Java Crash 指 `Throwable` 沿当前线程的调用路径传播时一直没有被处理，最终逃出线程入口。Android 的默认致命异常处理器（fatal handler）随后终止应用进程。异常类型只能帮助选择排查方向；能否恢复还取决于失败发生在哪个边界、数据与状态是否一致，以及调用方能否返回明确的失败或降级结果。

平台与 ART 源码按 Android 17 / API 37 / `android-17.0.0_r1` 核对。

## Java 异常分类：语法类别不等于恢复策略

所有 Java 异常都继承自 `Throwable`，主要分为 `Exception` 与 `Error`。工程上要同时看语言规则和故障语义。

| 类别 | 编译器约束 | 常见例子 | 治理重点 |
|---|---|---|---|
| Checked Exception（受检异常） | Java 调用方必须捕获或声明抛出 | `IOException`、`GeneralSecurityException` | 在 I/O、加密、进程间调用等边界定义重试、降级或向上返回 |
| `RuntimeException` | 编译器不强制处理 | `NullPointerException`、`IndexOutOfBoundsException`、`IllegalStateException` | 修正契约、状态机、生命周期或并发错误 |
| `Error` | 编译器不强制处理 | `OutOfMemoryError`、`StackOverflowError`、`NoSuchMethodError` | 判断运行时资源、递归、依赖或二进制兼容问题，避免宽泛恢复 |

Checked Exception 也可能由程序错误引起，例如关闭顺序错误导致读写失败；`RuntimeException` 也可能来自系统或第三方 API 的版本差异。分类只是线索。

`Error` 抛出后不会自动由虚拟机终止进程。它和其他 `Throwable` 一样可以被异常捕获；只有未处理并逃出线程入口时，才进入未捕获异常处理链。许多 `Error` 表示进程资源或链接状态已经异常：

- `OutOfMemoryError` 发生后，再分配日志对象或创建上传线程都可能失败。不能通过应用代码突破 ART 为该设备配置的堆上限（heap limit）。
- `StackOverflowError` 常见于无界递归，也可能来自过深的合法递归或较小线程栈。
- `NoSuchMethodError`、`NoClassDefFoundError` 属于链接错误（linkage error），应检查依赖解析、R8、动态特性模块、插件化、设备厂商差异和 API 兼容；额外包一层异常捕获通常只会隐藏错误。

判断是否捕获时可以问三个问题：

1. 当前层是否拥有足够信息给出业务可解释的结果？
2. 捕获后，数据与状态机是否仍保持一致？
3. 调用方能否明确收到成功、失败或取消结果，避免在没有结果的情况下继续？

如果三个问题不能回答清楚，就应让异常沿调用链传播到拥有决策权的边界。

## Android 17 的默认致命异常处理链

### 从 ART 到 `Thread.dispatchUncaughtException()`

ART 把当前未处理异常保存在每个线程的 pending exception（待处理异常）状态中。解释器或已编译代码按照异常处理器表查找处理位置并展开栈帧；当异常逃出线程入口，线程销毁路径中的 [`Thread::HandleUncaughtExceptions()`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread.cc) 取出并清除该状态，然后调用 Java 层 [`Thread.dispatchUncaughtException(Throwable)`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/Thread.java)。

Java 层的顺序是：

1. 调用 Android 私有的 uncaught exception pre-handler（前置未捕获异常处理器）；
2. 调用该线程显式安装的处理器；如果没有，则交给它的 `ThreadGroup`；
3. 根 `ThreadGroup` 再委托给 `Thread.getDefaultUncaughtExceptionHandler()` 返回的默认处理器。

[`RuntimeInit.commonInit()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/RuntimeInit.java) 在应用代码运行前安装平台处理器：

| 处理器 | 安装位置 | Android 17 行为 |
|---|---|---|
| `LoggingHandler` | 前置处理器（pre-handler） | 写入 `FATAL EXCEPTION`、线程、进程、PID（进程编号）和异常栈。应用通过公开 `Thread` API 不能替换它。 |
| `KillApplicationHandler` | 默认处理器（default handler） | 必要时补写日志，调用 ActivityManager 上报 Crash，并在 `finally` 中执行 `Process.killProcess()` 与 `System.exit(10)`。 |

应用调用 `Thread.setDefaultUncaughtExceptionHandler()` 会替换当前默认处理器。平台前置处理器仍会先执行，但 `KillApplicationHandler` 只有在自定义处理器继续调用安装前保存的处理器时才会运行。

线程级处理器的优先级高于 `ThreadGroup` 和默认处理器。如果某个线程通过 `setUncaughtExceptionHandler()` 安装处理器后不再委托，它也会截断进程级采集链。排查 SDK（Software Development Kit，软件开发工具包）冲突时，两种注册方式都要检查。

### 自定义处理器的最小正确结构

下面的示例强调委托和故障隔离。`CrashSpool.tryAppendMinimal()` 代表正常运行时已经初始化好的有界暂存区；spool 是等待下次启动校验和上传的追加式临时存储。致命异常路径中不应临时创建复杂对象。

```kotlin
class DelegatingFatalHandler(
    private val previous: Thread.UncaughtExceptionHandler?,
    private val crashSpool: CrashSpool,
) : Thread.UncaughtExceptionHandler {
    private val entered = AtomicBoolean(false)

    override fun uncaughtException(thread: Thread, error: Throwable) {
        try {
            if (entered.compareAndSet(false, true)) {
                crashSpool.tryAppendMinimal(thread, error)
            }
        } catch (_: Throwable) {
            // Fatal 路径只能尽力保存，采集失败不能截断平台退出链。
        } finally {
            if (previous != null) {
                previous.uncaughtException(thread, error)
            } else {
                Process.killProcess(Process.myPid())
                exitProcess(10)
            }
        }
    }
}

fun installFatalHandler(crashSpool: CrashSpool) {
    val previous = Thread.getDefaultUncaughtExceptionHandler()
    Thread.setDefaultUncaughtExceptionHandler(
        DelegatingFatalHandler(previous, crashSpool)
    )
}
```

`AtomicBoolean` 保证多个线程接近同时崩溃时，只有一个线程进入最小写入路径。`finally` 保证自有采集失败后仍委托旧处理器。Android 应用进程里的 `previous` 通常是平台处理器或先注册的 SDK 处理器；示例保留空值分支，避免异常线程返回后留下状态未知的进程。

这个示例不承诺崩溃记录一定保存成功。致命路径可能同时面临 OOM、磁盘满、文件锁被占用、栈溢出或进程被外部终止，因此无法保证记录或上报必达。

### 致命路径只做最少工作

较稳妥的设计把采集拆成正常运行期和致命异常发生时两部分。

正常运行期持续维护：

- 固定容量的 breadcrumb（近期用户操作和状态变化线索）环形缓冲区；
- 版本、进程、会话、页面和关键状态的紧凑快照；
- R8 混淆映射文件、构建 ID（用于把崩溃记录匹配到准确二进制和符号文件的版本标识）、动态模块与配置版本；
- 已打开并可独占写入的应用私有暂存区，或不需要复杂初始化的追加写入策略。

致命异常处理器内只尝试写入：

- 墙上时钟时间（可对应日志中的日期）与单调时间（只向前递增，适合计算耗时）；
- 进程名、线程名和线程 ID；
- 异常类、限制长度的消息、原因链（cause）与附加异常（suppressed）摘要；
- 已准备好的 breadcrumb；
- 完整性字段，如长度、版本和校验值。

不要在这里发送同步网络请求、生成完整堆转储、等待其他线程释放普通业务锁，或初始化数据库与大型序列化框架。即使把记录传给独立进程，IPC（Inter-Process Communication，进程间通信）也只能尽力而为：对端可能尚未启动，同一 UID（应用身份）下的进程可能同时被系统处理，Binder 调用也可能阻塞。

普通第三方应用不应把系统 `DropBoxManager` 当作自有崩溃暂存区。它是系统级、容量受限的诊断设施，条目可能被丢弃，写入与读取还受平台权限和设备策略约束。自有数据应写入应用私有存储，并在下次进程启动后校验、去重、脱敏和上传。

### 安装时机与多 SDK 链

`Application.attachBaseContext()` 是应用侧常用的早期安装点。Android 17 的 [`ActivityThread.handleBindApplication()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java) 先创建 `Application` 并在此过程中调用 `attachBaseContext()`，再安装常规 ContentProvider，随后调用 `Application.onCreate()`。它仍覆盖不了自定义 `Application` 构造、类加载或处理器安装前发生的故障；这些事件要依赖平台日志、Android vitals 等进程外来源。

多个 SDK 都修改默认处理器时，后注册者只能看到注册当时的前一个处理器。每个处理器都应在 `finally` 中继续委托，并限制自己的执行时间与写入量。建议在测试构建中记录处理器类名和安装顺序，主动注入以下故障条件：

- 主线程与后台线程分别抛出未捕获异常；
- 自有持久化抛异常；
- OOM 或磁盘满时进入处理器；
- 两个线程接近同时崩溃；
- SDK 初始化顺序变化。

测试要确认平台退出链没有被截断、记录未损坏、重启后只上传一次；仅确认处理器被调用还不够。

## Throwable 堆栈的成本与信息边界

### `kMaxSavedFrames = 256` 是优化阈值

`Throwable` 默认构造会执行 `fillInStackTrace()`，ART 再通过 [`Thread::CreateInternalStackTrace()`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread.cc) 遍历当前由 ART 管理的 Java/Kotlin 调用栈。

Android 17 源码中的 `kMaxSavedFrames = 256` 用于减少重复回溯：

1. 第一次 `WalkStack()` 计算深度，并尝试在 `saved_frames` 数组中保存前 256 个栈帧（frame）；
2. 实际深度小于 256 时，直接使用已保存栈帧构造内部堆栈记录；
3. 深度达到或超过 256 时，再执行一次 `WalkStack()` 构造完整结果。

所以 256 不是最大 Java 栈深度，也不限定日志展示的栈帧数。最终结果还会受到原因链中重复尾部栈帧的折叠、日志截断、采集 SDK 限制和服务端处理影响。

### `Thread.getStackTrace()` 也有成本

`new Throwable()`、`Throwable.getStackTrace()`、`Thread.currentThread().getStackTrace()` 和跨线程取栈都会产生不同程度的栈遍历、`StackTraceElement` 对象创建或目标线程停顿。改用 `Thread.getStackTrace()` 不能据此认定成本更低。

在高频路径采集调用来源时，应先定义：

- 采样率与每个会话的上限；
- 最大栈帧数、字符串长度和去重策略；
- 是否只在异常状态或慢事件超过阈值后采集；
- 对目标线程的停顿预算；
- 数据是否包含业务参数、文件路径或其他敏感信息。

性能结论要用目标设备和目标构建实测。debug（调试）、profileable（接近发布配置但允许性能采集）与 release（发布）构建的运行方式不同；JIT（运行时即时编译）、AOT（安装或构建时预先编译）和混淆状态也会改变结果，三类构建不能互相代替。

### 一份可诊断的 Java crash 记录

只保存 `Throwable.toString()` 通常不够。建议保留：

- 异常类型、消息、原因链与附加异常；
- 原始栈帧，包括类、方法、文件和行号；
- 线程名、进程名、应用版本名、版本号与构建标识；
- R8 混淆映射标识和动态模块版本；
- 受限、脱敏的 breadcrumb 与关键状态；
- 首次出现版本、受影响用户数和重复次数。

R8 混淆映射文件必须和产生 Crash 的构建一一对应。重复使用同一版本号发布不同构建、错配渠道包或丢失动态模块的映射文件，都会让反混淆结果指向错误代码。

## 高频 Crash 模式：从栈顶继续追状态

异常分布由业务和技术栈决定，不存在可泛用的“前五类占 80%”。下面这些模式常见，但治理优先级仍要依据本应用数据。

### `NullPointerException`

NPE 的栈顶告诉你在哪里解引用了 `null`，不一定告诉你它为什么变成 `null`。排查时按来源拆分：

- **边界数据**：服务端字段、数据库迁移、Intent/Bundle 参数是否声明可空，缺失时是拒绝、默认还是降级；
- **初始化顺序**：依赖是否在多进程、延迟初始化或冷启动竞态中尚未准备；
- **生命周期**：Fragment 的 View 已销毁、Activity 已结束，或回调到达时拥有该任务的生命周期对象已经失效；
- **并发可见性**：共享字段是否由另一线程清空，是否缺少同步或不可变快照。

补 `?.` 或空字符串只能改变症状。若字段是业务必需项，应在解析边界返回明确失败，并记录协议版本；若字段允许缺失，类型本身就应声明为 nullable（可空类型）或显式可选状态。

### `IndexOutOfBoundsException`

越界常见于“检查列表长度”和“按索引访问”使用了不同版本的数据快照：

- 后台更新列表，UI 仍使用旧位置；
- 分页请求乱序返回，旧响应覆盖新数据；
- Adapter 已提交新列表，点击回调仍保存旧位置；
- 多个 `add/remove/clear` 没有在同一串行状态容器中执行。

RecyclerView 点击时应重新读取 `bindingAdapterPosition` 并处理表示位置已经失效的 `NO_POSITION`，但这只是 UI 边界保护。数据层仍应使用不可变列表、单一写入者或受控同步，确保“选择项”和“读取项”来自同一版本。

### `ClassCastException`

类型转换失败常见于 JSON 多态字段、Bundle/Intent 参数、`Serializable`/`Parcelable`、反射和插件接口。同一 APK 的多个进程通常来自同一安装版本；动态模块、插件 class loader（类加载器）以及进程重启时恢复的旧状态，仍可能造成类定义或 schema（数据结构约定）不匹配。

安全转换 `as?` 适合业务允许该类型缺失的场景。若类型是协议必需项，应让解析失败携带字段、实际类型和 schema 版本，不能默默使用默认值继续写入错误数据。

### `IllegalStateException` 与生命周期错误

`IllegalStateException` 表示调用时状态不满足 API 契约，常见证据包括：

- FragmentManager 已保存状态后提交事务；
- Fragment 的 View 已销毁，异步回调仍访问旧的 View 引用（binding）；
- 生命周期已经低于所需状态，回调或收集任务仍运行；
- 同一个一次性结果、导航动作或状态转换被重复消费。

`commitAllowingStateLoss()` 只适合允许丢失的展示事务。支付结果、用户输入、导航主状态等不能用它掩盖时序错误。更稳妥的做法是把任务绑定到 `viewLifecycleOwner` 表示的 Fragment View 生命周期，使用 `repeatOnLifecycle` 在指定生命周期内启动或停止数据收集，并让状态机拒绝重复或过期事件。

### `OutOfMemoryError`、`StackOverflowError` 与链接错误

- OOM 要区分 Java 堆、线程创建、Native（原生/C++）或图形内存的间接压力与 LMK（低内存终止），详见 [20.5 OOM 治理](05-oom-governance.md)。
- 栈溢出要从重复栈帧、递归深度、线程栈大小和生成代码入手；捕获后继续在同一深栈执行也有风险。
- `NoSuchMethodError`、`NoClassDefFoundError` 要按依赖图、R8 保留规则（keep rules）、API 级别、动态模块和类加载器排查，不能归入普通业务异常。

## Kotlin 协程异常如何到达 Java 致命异常处理器

协程异常是否触发 Java Crash，取决于它能否传播给调用者、父协程或结果对象。`Job` 是表示协程生命周期及父子关系的句柄；安装 `CoroutineExceptionHandler` 只是其中一个条件。

| 场景 | 异常去向 |
|---|---|
| `coroutineScope` 内的子协程失败 | 取消异常以外的失败通常传播给父协程并取消同级任务，`coroutineScope` 再向调用者抛出异常 |
| 没有父 `Job` 的根 `launch`，或 `SupervisorJob`（子任务失败不会自动取消监督者及其他子任务）下没有其他传播路径的 `launch` | 交给 `CoroutineExceptionHandler`；没有合适处理器时进入平台最终处理，JVM/Android 上可能调用当前线程的未捕获异常处理器 |
| `async` | 异常保存在返回的 `Deferred` 结果对象中，由 `await()` 重新抛出；作为子协程时还要考虑父 `Job` 的传播关系 |
| 在具体挂起调用外捕获异常 | 当前边界可以转换为重试、失败结果或继续向上抛 |
| `CancellationException` | 通常表示协程之间的协作取消，不应当作业务 Crash；捕获 `Throwable` 时要重新抛出或以其他方式保留取消语义 |

`CoroutineExceptionHandler` 在协程已经失败、无法继续时收到异常，只能用于报告或执行失败后的动作，不能恢复该协程。给普通子 `launch` 单独安装处理器也未必生效，因为结构化并发会把子任务的生命周期和失败绑定到父协程，异常可能先传播给父协程。

协程行为应以项目锁定的 `kotlinx.coroutines` 版本为准。本文核对的 1.11.0 官方 [`CoroutineExceptionHandler`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-coroutine-exception-handler/) 文档说明：JVM 的最终处理流程会调用通过 `ServiceLoader`（运行时发现服务实现的标准机制）找到的处理器，以及当前线程的 `Thread.uncaughtExceptionHandler`。旧版 `kotlinx-coroutines-android` 的反射实现不能视为 Android 17 平台的固定机制。

更完整的异常架构见 [20.7 异常处理架构](07-exception-architecture.md)。

## 第三方 SDK：线程隔离不等于进程隔离

把 SDK 放到独立线程池，可以限制排队长度、线程数和耗时任务之间的干扰，但不能隔离未捕获异常。后台线程的异常到达 Android 默认处理器后，`KillApplicationHandler` 仍会终止整个应用进程。

治理第三方 SDK 可以按风险从低到高处理：

- 在有明确契约的同步调用边界捕获已知异常，并转换为 SDK 不可用或业务降级；
- 对回调做生命周期、线程和重复调用保护；
- 固定、审计并回归测试 SDK 版本，保留其 R8 混淆映射文件与 Native 符号文件；符号文件用于把本地代码地址还原为函数和源码位置；
- 为非关键功能提供本地或远程关闭开关，并确保关闭路径不依赖故障 SDK 初始化成功；
- 对不可信、可独立关闭且 IPC 成本可接受的能力使用独立进程；同时处理进程死亡、重连和状态恢复。

不要用线程级 `UncaughtExceptionHandler` 吞掉未知 SDK 异常后继续运行。异常线程已经终止，共享状态是否一致无法确认；这类处理会把显式 Crash 变成更难诊断的数据错乱或无响应。

## 治理优先级与反馈流程

### 先评估用户伤害，再评估修复成本

修复成本影响排期和方案选择，不应降低故障本身的严重度。建议按以下信息排序：

| 维度 | 需要回答的问题 |
|---|---|
| 用户伤害 | 是否阻断启动、登录、支付、创作或数据保存；是否进入启动后反复崩溃的 crash loop |
| 影响范围 | 受影响用户数、用户率、会话率、机型与渠道分布 |
| 回归证据 | 是否由当前版本新增，是否随分阶段发布比例同步增长 |
| 重复伤害 | 同一用户是否反复触发，是否每次进入固定路径都崩溃 |
| 可恢复性 | 重启是否恢复，是否需要清数据、回滚配置或安全模式 |
| 修复风险 | 改动范围、兼容性、服务端配合、验证样本和撤回能力 |

事件次数与受影响用户数都要看。一个用户在 crash loop 中产生一百次事件，严重度可能高于一百个用户各触发一次可绕过的边缘功能错误；不能固定只用 UV（去重用户数）或事件次数排序。

### 从聚类到验证

1. **聚类**：按反混淆后的异常类型、根原因与稳定栈帧生成候选问题簇，保留应用版本、混淆映射 ID 和协程或反射边界。
2. **分层**：按新旧版本、设备、Android 版本、渠道、内存容量档位和关键业务路径比较。
3. **建立假设**：从栈顶继续追输入、状态、生命周期和并发关系，写出能被日志或复现推翻的根因。
4. **修复**：优先修契约与状态机；临时保护要有监控、撤除条件和失败语义。
5. **分阶段发布**：定义暂停扩大用户比例与撤回条件，确认混淆映射文件、告警和新问题簇监控已就绪。
6. **验证**：在相同分母和可比样本下确认原问题簇下降，同时检查 Crash 是否迁移为 ANR、数据错误或新堆栈。
7. **预防复发**：把能够自动识别的根因加入静态规则、契约测试、生命周期测试或故障注入。

告警阈值应来自产品自己的历史基线、版本样本和风险等级，不使用来源不明的固定崩溃率。小比例发布的样本较少时，要同时看表示统计不确定范围的置信区间、绝对用户数和故障严重度。

## 源码与官方文档

- 平台：AOSP [`android-17.0.0_r1`](https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1/)
- Java 未捕获异常接口：[`Thread.UncaughtExceptionHandler`](https://developer.android.com/reference/java/lang/Thread.UncaughtExceptionHandler)
- 应用启动顺序：[`ActivityThread.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- ART 未捕获异常与栈回溯：[`runtime/thread.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread.cc) · [`java_lang_Throwable.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/native/java_lang_Throwable.cc)
- Java 未捕获异常分发：[`Thread.java`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/Thread.java) · [`ThreadGroup.java`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/ThreadGroup.java)
- Android 致命异常处理：[`RuntimeInit.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/RuntimeInit.java)
- 官方 Crash 指南：[Crashes](https://developer.android.com/topic/performance/vitals/crash)
- 协程异常：[`CoroutineExceptionHandler`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-coroutine-exception-handler/) · [Coroutine exceptions handling](https://kotlinlang.org/docs/exception-handling.html)
