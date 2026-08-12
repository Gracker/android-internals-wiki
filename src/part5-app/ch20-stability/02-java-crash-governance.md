---

title: Java Crash 治理
chapter: '20.2'
section: '20.2'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-07-01'
last_verified_against: AOSP android-17.0.0_r1, developer.android.com
confidence: medium
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

Java Crash 的定义很窄：`Throwable` 没有在当前线程的传播路径中被处理，逃出线程入口，Android 默认 fatal handler 随后终止应用进程。异常类型能帮助选择排查方向，却不能单独判断是否可恢复；恢复能力取决于失败发生在哪个边界、状态是否仍一致，以及调用方能否给出明确的降级结果。

平台与 ART 源码锚点为 Android 17 / API 37 / `android-17.0.0_r1`。

## Java 异常分类：语法类别不等于恢复策略

所有 Java 异常都继承自 `Throwable`，主要分为 `Exception` 与 `Error`。工程上要同时看语言规则和故障语义。

| 类别 | 编译器约束 | 常见例子 | 治理重点 |
|---|---|---|---|
| Checked Exception | Java 调用方必须捕获或声明抛出 | `IOException`、`GeneralSecurityException` | 在 I/O、加密、进程间调用等边界定义重试、降级或向上返回 |
| `RuntimeException` | 编译器不强制处理 | `NullPointerException`、`IndexOutOfBoundsException`、`IllegalStateException` | 修正契约、状态机、生命周期或并发错误 |
| `Error` | 编译器不强制处理 | `OutOfMemoryError`、`StackOverflowError`、`NoSuchMethodError` | 判断运行时资源、递归、依赖或二进制兼容问题，避免宽泛恢复 |

Checked Exception 也可能由程序错误引起，例如关闭顺序错误导致读写失败；`RuntimeException` 也可能来自系统或第三方 API 的版本差异。分类只是线索。

`Error` 也不是“一抛出就由虚拟机杀进程”。它和其他 `Throwable` 一样可以被 `catch`；只有未处理并逃出线程入口时，才进入 uncaught exception 链。区别在于许多 `Error` 表示进程资源或链接状态已经异常：

- `OutOfMemoryError` 发生后，再分配日志对象或创建上传线程都可能失败。不能通过应用代码突破 ART 为该设备配置的 heap limit。
- `StackOverflowError` 常见于无界递归，也可能来自过深的合法递归或较小线程栈。
- `NoSuchMethodError`、`NoClassDefFoundError` 属于 linkage 问题，应检查依赖解析、R8、动态特性模块、插件化和 OEM/API 兼容，补一层 `catch` 往往只会隐藏错误。

判断是否捕获时可以问三个问题：

1. 当前层是否拥有足够信息给出业务可解释的结果？
2. 捕获后，数据与状态机是否仍保持一致？
3. 调用方是否会收到成功、失败、取消中的明确一种，而不是静默继续？

如果三个问题不能回答清楚，就应让异常沿调用链传播到拥有决策权的边界。

## Android 17 的默认 fatal handler 链

### 从 ART 到 `Thread.dispatchUncaughtException()`

异常在 ART 中以线程的 pending exception 状态传播。解释器或编译代码按照 catch table 查找处理器并展开栈帧；当异常逃出线程入口，线程销毁路径中的 [`Thread::HandleUncaughtExceptions()`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread.cc) 取出并清除 pending exception，然后调用 Java 层 [`Thread.dispatchUncaughtException(Throwable)`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/Thread.java)。

Java 层的顺序是：

1. 调用 Android 私有的 uncaught exception pre-handler；
2. 调用该线程的显式 handler；如果没有，则交给它的 `ThreadGroup`；
3. 根 `ThreadGroup` 再委托给 `Thread.getDefaultUncaughtExceptionHandler()`。

[`RuntimeInit.commonInit()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/RuntimeInit.java) 在应用代码运行前安装平台处理器：

| 处理器 | 安装位置 | Android 17 行为 |
|---|---|---|
| `LoggingHandler` | pre-handler | 写入 `FATAL EXCEPTION`、线程、进程、PID 和异常栈。应用通过公开 `Thread` API 不能替换它。 |
| `KillApplicationHandler` | default handler | 必要时补写日志，调用 ActivityManager 上报 crash，并在 `finally` 中执行 `Process.killProcess()` 与 `System.exit(10)`。 |

应用调用 `Thread.setDefaultUncaughtExceptionHandler()` 会替换 default handler 的当前位置。平台 pre-handler 仍会先执行，但 `KillApplicationHandler` 只有在自定义 handler 委托给安装前保存的 handler 时才会继续运行。

线程级 handler 的优先级高于 `ThreadGroup` 和 default handler。如果某个线程通过 `setUncaughtExceptionHandler()` 安装处理器后不再委托，它也能截断进程级采集链。排查 SDK 冲突时，两种注册方式都要检查。

### 自定义 handler 的最小正确结构

下面的示例强调委托和故障隔离；`CrashSpool.tryAppendMinimal()` 代表已经在正常运行期初始化好的有界存储，不是在 fatal 路径临时创建复杂对象。

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

`AtomicBoolean` 用于阻止多个线程同时崩溃时重复进入脆弱的写入路径。`finally` 保证自有采集失败后仍委托旧 handler。Android 应用进程里 `previous` 通常是平台或先注册 SDK 的 handler；示例保留空值兜底，避免异常线程返回后留下状态未知的进程。

这个示例不承诺 crash record 一定保存成功。fatal 路径可能同时面临 OOM、磁盘满、文件锁持有、栈溢出或进程被外部终止，任何“必达上报”说法都不严谨。

### Fatal 路径只做最少工作

较稳妥的设计把采集拆成正常运行期和 fatal 时刻两部分。

正常运行期持续维护：

- 固定容量的 breadcrumb 环形缓冲；
- 版本、进程、会话、页面和关键状态的紧凑快照；
- mapping、构建 ID、动态模块与配置版本；
- 已打开并可独占写入的 app-private spool，或无需复杂初始化的追加策略。

fatal handler 内只尝试写入：

- wall clock 与 monotonic time；
- 进程名、线程名和线程 ID；
- 异常类、受限长度的 message、cause 与 suppressed 摘要；
- 已准备好的 breadcrumb；
- 完整性字段，如长度、版本和校验值。

不要在这里发同步网络请求、执行完整 heap dump、等待其他线程释放普通业务锁，或初始化数据库与大型序列化框架。独立进程 IPC 也只是尽力传递：对端可能尚未启动、同 UID 进程可能同时被系统处理，Binder 调用也可能阻塞。

普通三方应用不应把系统 `DropBoxManager` 当作自有 crash spool。它是系统级、容量受限的诊断设施，条目可被丢弃，写入与读取还受平台权限和设备策略约束。自有数据应写入 app-private 存储，并在下次进程启动后校验、去重、脱敏和上传。

### 安装时机与多 SDK 链

`Application.attachBaseContext()` 是应用侧常用的早期安装点，比 `Application.onCreate()` 更早，也早于常规 ContentProvider 初始化。但它仍覆盖不了自定义 Application 构造、类加载或应用 handler 安装前发生的故障；这些事件要依赖平台日志、Play Vitals 等进程外来源。

多个 SDK 都修改 default handler 时，后注册者只能看到注册当时的前驱。每个 handler 都应在 `finally` 中委托前驱，并限制自己的执行时间与写入量。建议在测试构建记录 handler 类名和安装顺序，覆盖以下故障注入：

- 主线程与后台线程分别抛出未捕获异常；
- 自有持久化抛异常；
- OOM 或磁盘满时进入 handler；
- 两个线程接近同时崩溃；
- SDK 初始化顺序变化。

测试重点是“平台退出链没有被截断、记录不损坏、重启后只上传一次”，而不是只看 handler 是否被调用。

## Throwable 堆栈的成本与信息边界

### `kMaxSavedFrames = 256` 是优化阈值

`Throwable` 默认构造会执行 `fillInStackTrace()`，ART 再通过 [`Thread::CreateInternalStackTrace()`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread.cc) 遍历当前 managed stack。

Android 17 源码中的 `kMaxSavedFrames = 256` 用于减少重复回溯：

1. 第一次 `WalkStack()` 计算深度，并尝试在 `saved_frames` 数组保存前 256 个 frame；
2. 当实际深度小于 256 时，直接使用已保存 frame 构造 internal stack trace；
3. 当深度达到或超过 256 时，再执行一次 `WalkStack()` 构造完整结果。

所以 256 不是最大 Java 栈深度，也不是日志一定展示的 frame 数。展示还会受到异常 cause 的共同尾帧折叠、日志截断、采集 SDK 限制和服务端处理影响。

### `Thread.getStackTrace()` 不是免费替代品

`new Throwable()`、`Throwable.getStackTrace()`、`Thread.currentThread().getStackTrace()` 和跨线程 stack trace 都会引入不同程度的栈遍历、对象物化或暂停成本。把 API 换成 `Thread.getStackTrace()` 不能推导出成本更低。

在高频路径采集调用来源时，应先定义：

- 采样率与每个会话的上限；
- 最大 frame 数、字符串长度和去重策略；
- 是否只在异常状态或慢事件超过阈值后采集；
- 对目标线程的停顿预算；
- 数据是否包含业务参数、文件路径或其他敏感信息。

性能结论要用目标设备和目标构建实测。debug、profileable 与 release 构建的解释、JIT/AOT 和混淆状态不同，不能互相代替。

### 一份可诊断的 Java crash 记录

只保存 `Throwable.toString()` 通常不够。建议保留：

- exception type、message、cause chain 与 suppressed exceptions；
- 原始 frame，包括类、方法、文件和行号；
- 线程名、进程名、app version、version code 与构建标识；
- R8 mapping 标识和动态模块版本；
- 受限、脱敏的 breadcrumb 与关键状态；
- 首次出现版本、受影响用户数和重复次数。

R8 mapping 必须和产生 crash 的构建一一对应。重发同一 version code、错配渠道包或丢失动态模块 mapping，都会让反混淆结果指向错误代码。

## 高频 Crash 模式：从栈顶继续追状态

异常分布由业务和技术栈决定，不存在可泛用的“前五类占 80%”。下面这些模式常见，但治理优先级仍要依据本应用数据。

### `NullPointerException`

NPE 的栈顶告诉你在哪里解引用了 `null`，不一定告诉你它为什么变成 `null`。排查时按来源拆分：

- **边界数据**：服务端字段、数据库迁移、Intent/Bundle 参数是否声明可空，缺失时是拒绝、默认还是降级；
- **初始化顺序**：依赖是否在多进程、延迟初始化或冷启动竞态中尚未准备；
- **生命周期**：Fragment view 已销毁、Activity 已结束、回调晚于 owner；
- **并发可见性**：共享字段是否由另一线程清空，是否缺少同步或不可变快照。

补 `?.` 或空字符串只能改变症状。若字段是业务必需项，应在解析边界返回明确失败，并记录协议版本；若字段允许缺失，类型本身就应表达 nullable 或可选状态。

### `IndexOutOfBoundsException`

越界常见于“检查 size”和“按 index 访问”基于不同快照：

- 后台更新列表，UI 仍使用旧 position；
- 分页请求乱序返回，旧响应覆盖新数据；
- Adapter 数据已提交新列表，点击回调仍保存旧 position；
- 多个 `add/remove/clear` 没有在同一串行状态容器中执行。

RecyclerView 点击时应重新读取 `bindingAdapterPosition` 并处理 `NO_POSITION`，但这只是 UI 边界保护。数据层仍应使用不可变列表、单一写入者或受控同步，确保“选择项”和“读取项”来自同一版本。

### `ClassCastException`

类型转换失败常见于 JSON 多态字段、Bundle/Intent 参数、`Serializable`/`Parcelable`、反射和插件接口。多进程并不会让同一 APK 的两端自然运行不同版本，但动态模块、插件类加载器、进程重启时保存的旧状态，都可能造成类或 schema 不匹配。

安全转换 `as?` 适合业务允许该类型缺失的场景。若类型是协议必需项，应让解析失败携带字段、实际类型和 schema 版本，不能默默使用默认值继续写入错误数据。

### `IllegalStateException` 与生命周期错误

`IllegalStateException` 表示调用时状态不满足 API 契约，常见证据包括：

- FragmentManager 已保存状态后提交事务；
- Fragment 的 view 已销毁，异步回调仍访问旧 binding；
- 生命周期已经低于所需状态，回调或收集任务仍运行；
- 同一个一次性结果、导航动作或状态转换被重复消费。

`commitAllowingStateLoss()` 只适合允许丢失的展示事务。支付结果、用户输入、导航主状态等不能用它掩盖时序错误。更稳妥的做法是把任务绑定到 `viewLifecycleOwner`，使用 `repeatOnLifecycle` 管理收集，并让状态机拒绝重复或过期事件。

### `OutOfMemoryError`、`StackOverflowError` 与 linkage error

- OOM 要区分 Java heap、线程创建、Native/graphics 间接压力与 LMK，详见 [20.5 OOM 治理](05-oom-governance.md)。
- Stack overflow 要从重复 frame、递归深度、线程栈大小和生成代码入手；捕获后继续在同一深栈执行也有风险。
- `NoSuchMethodError`、`NoClassDefFoundError` 要按依赖图、R8 keep 规则、API level、动态模块和类加载器排查，不能归入普通业务异常。

## Kotlin 协程异常如何到达 Java fatal handler

协程异常是否触发 Java Crash，取决于它有没有传播路径，而不是只看有没有安装 `CoroutineExceptionHandler`。

| 场景 | 异常去向 |
|---|---|
| `coroutineScope` 内 child 失败 | 非取消异常通常向父协程传播并取消同级任务，作用域向调用者重新抛出 |
| 根 `launch` 或 `SupervisorJob` 下无传播路径的 `launch` | 交给 `CoroutineExceptionHandler`；没有合适 handler 时进入平台兜底，JVM/Android 上可到当前线程的 uncaught handler |
| `async` | 异常保存在 `Deferred`，由 `await()` 重新抛出；仍要考虑其 parent Job 的传播关系 |
| `try/catch` 包围具体 suspend 调用 | 当前边界可以转换为重试、失败结果或继续向上抛 |
| `CancellationException` | 通常表示协作取消，不应当作业务 crash；捕获 `Throwable` 时要保留取消语义 |

`CoroutineExceptionHandler` 在协程已经失败、无法继续时收到异常，它是报告点，不是恢复点。给普通 child `launch` 单独安装 handler 也未必生效，因为异常可能先按结构化并发传播给父协程。

当前行为应以项目锁定的 `kotlinx-coroutines` 版本为准。官方 [`CoroutineExceptionHandler`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-coroutine-exception-handler/) 文档说明：JVM 的兜底流程会调用通过 `ServiceLoader` 发现的 handler 和当前线程的 `Thread.uncaughtExceptionHandler`。不要把某个旧版 `kotlinx-coroutines-android` 的反射实现当成 Android 17 平台固定机制。

更完整的异常架构见 [20.7 异常处理架构](07-exception-architecture.md)。

## 第三方 SDK：线程隔离不等于进程隔离

把 SDK 放到独立线程池，能限制排队、线程数和耗时任务之间的干扰，但不能隔离未捕获异常。后台线程的异常到达 Android default handler 后，`KillApplicationHandler` 仍会终止整个应用进程。

治理第三方 SDK 可以按风险从低到高处理：

- 在有明确契约的同步调用边界捕获已知异常，并转换为 SDK 不可用或业务降级；
- 对回调做生命周期、线程和重复调用保护；
- 固定、审计并回归测试 SDK 版本，保留其 mapping 与 Native symbols；
- 为非关键功能提供本地或远程关闭开关，并确保关闭路径不依赖故障 SDK 初始化成功；
- 对不可信、可独立关闭且 IPC 成本可接受的能力使用独立进程；同时处理进程死亡、重连和状态恢复。

不要用线程级 `UncaughtExceptionHandler` 吞掉未知 SDK 异常后继续运行。异常线程已经终止，共享状态是否一致无法证明；这类处理会把显式 crash 变成更难诊断的数据错乱或无响应。

## 治理优先级与反馈流程

### 先评估用户伤害，再评估修复成本

修复成本影响排期和方案选择，不应降低故障本身的严重度。建议按以下信息排序：

| 维度 | 需要回答的问题 |
|---|---|
| 用户伤害 | 是否阻断启动、登录、支付、创作或数据保存；是否进入 crash loop |
| 影响范围 | 受影响用户数、用户率、会话率、机型与渠道分布 |
| 回归证据 | 是否由当前版本新增，是否随灰度比例同步增长 |
| 重复伤害 | 同一用户是否反复触发，是否每次进入固定路径都崩溃 |
| 可恢复性 | 重启是否恢复，是否需要清数据、回滚配置或安全模式 |
| 修复风险 | 改动范围、兼容性、服务端配合、验证样本和撤回能力 |

事件次数与受影响用户数都要看。一个用户在 crash loop 中产生一百次事件，严重度可能高于一百个用户各触发一次可绕过的边缘功能错误；不能固定只用 UV 或次数排序。

### 从聚类到验证

1. **聚类**：按反混淆后的 exception type、根 cause 与稳定 frame 生成候选簇，保留 app version、mapping ID 和协程/反射边界。
2. **分层**：按新旧版本、设备、Android 版本、渠道、RAM 档和关键业务路径比较。
3. **建立假设**：从栈顶继续追输入、状态、生命周期和并发关系，写出能被日志或复现推翻的根因。
4. **修复**：优先修契约与状态机；临时保护要有监控、撤除条件和失败语义。
5. **分阶段发布**：定义暂停扩量与撤回条件，确认 mapping、告警和新簇监控已就绪。
6. **验证**：在相同分母和可比样本下确认原簇下降，同时检查 crash 是否迁移为 ANR、数据错误或新堆栈。
7. **预防复发**：把可机械识别的根因加入静态规则、契约测试、生命周期测试或故障注入。

告警阈值应来自产品自己的历史基线、版本样本和风险等级，不使用来源不明的固定 crash rate。低样本灰度要同时看置信区间、绝对用户数和故障严重度。

## 源码与文档锚点

- 平台：AOSP [`android-17.0.0_r1`](https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1/)
- ART 未捕获异常与栈回溯：[`runtime/thread.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread.cc) · [`java_lang_Throwable.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/native/java_lang_Throwable.cc)
- Java handler 分发：[`Thread.java`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/Thread.java) · [`ThreadGroup.java`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/ThreadGroup.java)
- Android fatal handler：[`RuntimeInit.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/RuntimeInit.java)
- 官方 Crash 指南：[Crashes](https://developer.android.com/topic/performance/vitals/crash)
- 协程异常：[`CoroutineExceptionHandler`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-coroutine-exception-handler/) · [Coroutine exceptions handling](https://kotlinlang.org/docs/exception-handling.html)
