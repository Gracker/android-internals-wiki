---
title: "Android 17 ART 去优化：触发、栈重建与性能诊断"
chapter: "1.35"
section: "1.35"
status: finalized
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-08-19"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: official
    path: "source.android.com/docs/core/runtime/jit-compiler"
  - type: official
    path: "source.android.com/docs/core/runtime/configure"
  - type: aosp
    path: "art/runtime/deoptimization_kind.h (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/entrypoints/quick/quick_deoptimization_entrypoints.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/quick_exception_handler.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/interpreter/interpreter.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/thread.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/runtime.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/instrumentation.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/cha.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/compiler/optimizing/inliner.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/compiler/optimizing/bounds_check_elimination.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/compiler/optimizing/instruction_builder.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/compiler/jit/jit_compiler.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/jit/jit.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/openjdkjvmti/events.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/openjdkjvmti/deopt_manager.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/openjdkjvmti/ti_redefine.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/jit/jit_code_cache.cc (android-17.0.0_r1)"
tags: [art, deoptimization, deopt, jit, aot, cha, instrumentation, jvmti, perfetto]
related_chapters: ["1.7", "1.13", "1.22", "8.7", "21.4"]
---

# 1.35 Android 17 ART 去优化：触发、栈重建与性能诊断

ART 的优化代码依赖运行时假设：某个调用点只见过一种接收者类型、某个虚方法只有一个实现、循环索引满足已证明的范围。假设失效时，继续运行旧机器码可能产生错误结果。去优化（deoptimization，简称 deopt）负责恢复对应 DEX 程序计数器（DEX PC）处的解释器状态，让当前调用继续按 Java 语义执行。

“去优化”不是单一开关。Android 17 至少有三种不同作用域：

- 显式单帧 deopt：优化代码中的守卫条件（guard）失败，只转换当前正在执行的编译帧（compiled activation）；
- 失效代码与在栈帧处理：类层次分析（CHA）等机制先撤销编译代码，再标记仍在运行旧代码的帧；
- Instrumentation / JVMTI deopt：可以限制到一个方法、一个线程，也可以安装让所有方法进入解释器的全局 interpreter stubs（解释器入口桩）。

三者的暂停方式、后续执行方式和性能代价都不同。诊断时先确认作用域，再讨论“是否回到解释器”。

## 一、单帧 deopt：编译器守卫条件失败

### 1.1 Android 17 的触发原因以枚举为准

`runtime/deoptimization_kind.h` 给出了 API 37 的完整原因集合：

| `DeoptimizationKind` | 典型生成位置 | 含义 |
|---|---|---|
| `kAotInlineCache` | `inliner.cc` | AOT 单态 inline cache（只记录一种接收者类型的内联缓存）不再匹配 |
| `kJitInlineCache` | `inliner.cc` | JIT 单态 inline cache 未命中 |
| `kJitSameTarget` | `inliner.cc` | 多种接收者原本落到同一目标，运行时目标发生变化 |
| `kLoopBoundsBCE` | `bounds_check_elimination.cc` | 循环边界检查消除（BCE）的范围守卫失败 |
| `kLoopNullBCE` | `bounds_check_elimination.cc` | 循环 BCE 使用的非空假设失败 |
| `kBlockBCE` | `bounds_check_elimination.cc` | 基本块级边界守卫失败 |
| `kCHA` | `inliner.cc` / `cha.cc` | 单实现 CHA 假设失效 |
| `kDebugging` | quick trampoline（quick 入口跳板）/ Instrumentation | 调试支持要求当前帧转入解释器 |
| `kFullFrame` | Instrumentation / 异常投递 | 需要转换一段已编译调用栈 |
| `kMethodHandleTypeMismatch` | `instruction_builder.cc` | `MethodHandle.invokeExact` 的类型与调用点（call site）不匹配 |

`HCheckCast` 或 `HLoadClass` 出现在守卫条件的构造过程中，不代表它们自身必然触发 deopt。判断某条优化是否可能去优化，应查找它是否生成 `HDeoptimize`，以及使用了哪个 `DeoptimizationKind`。

### 1.2 从 `HDeoptimize` 到解释器

下面的流程对应优化代码主动触发的单帧 deopt：

```text
guard 条件失败
  → HDeoptimize
  → 架构相关 DeoptimizationSlowPath
  → art_quick_deoptimize_from_compiled_code
  → artDeoptimizeFromCompiledCode(kind, thread)
  → Thread::Deoptimize(single_frame = true)
  → QuickExceptionHandler::DeoptimizeSingleFrame
  → DeoptimizeStackVisitor 重建 ShadowFrame
  → long jump 到 quick-to-interpreter 边界
  → EnterInterpreterFromDeoptimize
```

`artDeoptimizeFromCompiledCode()` 会压入 `DeoptimizationContextRecord`，保存返回值、原有异常以及 DEX PC 推进策略。随后只转换触发 deopt 的最外层编译帧；若该机器码内联了多个 Java 方法，栈访问器会为每个内联帧建立一个 `ShadowFrame`。`ShadowFrame` 是 ART 用于保存解释器方法、DEX PC 和虚拟寄存器状态的数据结构。

这条路径直接调用 `Thread::Deoptimize()`。它没有先抛出一个普通 Java 异常，因此把所有 deopt 概括为“特殊异常”会掩盖入口差异。

### 1.3 守卫条件的代价分为未命中和命中两部分

守卫条件未触发时，热路径通常只多一次比较和条件跳转，仍有指令与分支预测成本。触发时才进入 ART runtime，主要工作包括：

- 遍历编译帧及其内联帧；
- 根据 `CodeInfo`、stack map（机器码位置到 DEX 状态的映射）和 `DexRegisterMap` 恢复 DEX 虚拟寄存器；
- 使用寄存器掩码（register mask）与栈掩码（stack mask）区分引用和普通值；
- 构造并链接 `ShadowFrame`；
- 失效或重新初始化对应编译代码；
- 必要时更新 JIT inline cache；
- 通过 long jump 跳到解释器入口。

代价随内联深度、dex register 数量和栈映射复杂度变化，不能用固定毫秒数代表所有设备和方法。

## 二、ShadowFrame 怎样恢复 Java 执行状态

### 2.1 恢复的是 DEX 状态，不是原机器栈的复制品

`DeoptimizeStackVisitor` 以 `kIncludeInlinedFrames` 模式遍历栈。对优化编译帧，它从原生程序计数器（native PC）找到 stack map，再恢复每个虚拟寄存器（vreg）位于栈、通用寄存器、浮点寄存器还是常量。对于 nterp 解释器帧，栈访问器从 nterp 的 vreg 数组和引用数组恢复值。

新建的 `ShadowFrame` 保存：

- `ArtMethod` 与 dex PC；
- DEX 虚拟寄存器及其引用类型；
- 是否跳过方法退出、低开销跟踪等事件的标记；
- 指向上层 ShadowFrame 的链接。

API 37 的 `EnterInterpreterFromDeoptimize()` 明确说明，它不会为了锁计数恢复一套 monitor（Java 对象监视器锁）状态；编译器只应编译通过结构化锁（structured-locking）检查的方法。“逐个恢复 monitor 持有列表”不符合该标签实现。

### 2.2 DEX PC 是否重试取决于入口

从 `HDeoptimize` 进入时，`from_code=true`，解释器从守卫对应的 DEX PC 继续。由 runtime 方法返回、挂起检查（suspend check）或异常投递触发时，ART 还要避免重复执行非幂等指令：

- `kKeepDexPc` 要求重试当前 DEX 指令；
- `monitor-enter`、`monitor-exit` 和 invoke 需要专门推进规则；
- 待处理异常会先恢复，再查找解释器异常处理器（catch handler）；
- 后续 ShadowFrame 通常位于 invoke 点，返回值要传给调用者。

这些分支解释了 `DeoptimizationContextRecord` 为什么保存返回值、待处理异常、`from_code` 和 `DeoptimizationMethodType`。该记录按栈链接，允许验证器（verifier）或类加载引发嵌套 deopt。

### 2.3 sentinel exception（哨兵异常）只服务于特定跨边界路径

sentinel exception（哨兵异常）是用于传递内部控制信号的保留假对象指针。`Thread::GetDeoptimizationException()` 返回该指针；Instrumentation 可以把它写入线程的异常槽，使 quick 异常投递或 `ArtMethod::Invoke()` 在返回边界识别 deopt 请求。原有 Java 异常保存在去优化上下文中，稍后恢复。

它不会进入 Java `catch`，GC 根访问器也会排除该值。显式 `HDeoptimize` 路径直接获得 long-jump 上下文；只有需要跨既有 quick / invoke 边界传递请求时，哨兵值才用于传递信号。

## 三、CHA 失效：类加载怎样影响在栈代码

### 3.1 新类必须打破已有单实现假设才会触发

`ClassHierarchyAnalysis::UpdateAfterLoadingOf()` 在类进入已解析状态前检查虚方法表（vtable）和接口方法表（iftable）。只有新类让某个虚方法或接口方法的“单一实现”（single-implementation）信息失效，并且 JIT code cache（JIT 编译代码缓存）中存在依赖该假设的编译体时，才需要处理编译代码。

因此，下列说法都过宽：

- 动态加载一个 DEX 一定发生 deopt；
- 创建一个 `Proxy` 一定使相关调用点 deopt；
- 使用 MultiDex、ServiceLoader 或依赖注入框架必然触发 CHA。

它们增加“晚到实现类”的可能性；是否发生 deopt 取决于实际继承关系、此前是否形成单实现假设，以及是否已有依赖代码。

### 3.2 API 37 的实际链路

CHA 失效按以下顺序处理：

1. 清除受影响方法的 single-implementation 信息；
2. 从 CHA 依赖映射表收集 `ArtMethod` 与 `OatQuickMethodHeader`；
3. 调用 `JitCodeCache::InvalidateCompiledCodeFor()` 撤销对应 JIT 代码；
4. 创建 `CHACheckpoint`，让各线程扫描自己的已编译调用栈；
5. 命中失效方法头的帧，在预留栈槽写入 `DeoptimizeFlagValue::kCHA`；
6. 编译代码执行 `HShouldDeoptimizeFlag` 守卫时进入 `HDeoptimize(kCHA)`。

checkpoint 是让目标线程在安全点执行指定检查的协作机制。这里它只负责在目标线程上标记栈帧，不在 checkpoint 回调内构造 `ShadowFrame`。类链接线程会等待相关线程通过 checkpoint，因此大量线程或很深的栈可能把这部分成本反映到类加载延迟上。

Android 17 ART 源码中没有 `runtime/deopt_checkpoint.cc`。CHA checkpoint 定义在 `runtime/cha.cc`；JVMTI 的线程级同步 checkpoint 位于 `openjdkjvmti/deopt_manager.cc`。定位 API 37 源码时不要沿用不存在的文件名。

## 四、Instrumentation 与 JVMTI 的三个作用域

### 4.1 方法级 deopt

这里的 Instrumentation 指 ART runtime 中控制入口桩、事件钩子和去优化状态的子系统。`Instrumentation::Deoptimize(method)` 执行三件事：

1. 把方法加入 `deoptimized_methods_`；
2. 把该方法的执行入口（entrypoint）改为 quick-to-interpreter bridge（转入解释器的桥接入口）；
3. 遍历线程栈，在支持标志位的 JIT 帧上设置 `kCheckCallerForDeopt`。

它是可撤销的弱 deopt。正在执行的调用者在 runtime 返回 / 退出检查中，重新判断该方法是否仍在去优化集合；若请求已移除，可以继续使用原代码。撤销该方法的去优化状态前，后续新调用走解释器桥接入口。

普通非原生、非代理方法上的断点（breakpoint）采用这条受限路径。默认接口方法的断点例外：API 37 的 `DeoptManager` 会为它请求全局 deopt。

### 4.2 线程级 deopt

部分 JVMTI 事件允许指定线程，例如单步执行（single-step）、字段访问 / 修改、frame-pop（弹出栈帧）和 force-early-return（强制提前返回）。此时 `DeoptManager` 增加目标线程的强制解释执行计数，并通过 `RequestSynchronousCheckpoint()` 准备该线程的栈。

checkpoint 内部随后执行一次 suspend-all（暂停所有受管线程），再调用 `InstrumentThreadStack(target, false)`。源码注释强调：这一步只准备按需 deopt，并不立即把所有帧转成 `ShadowFrame`。

### 4.3 全局 interpreter stubs

`Instrumentation::DeoptimizeEverything(key)` 把该客户端的 instrumentation level（插桩级别）请求提升为 `kInstrumentWithInterpreter`。`ConfigureStubs()` 会综合所有客户端的需求，取最高级别：

| Level | 行为 |
|---|---|
| `kInstrumentNothing` | 没有 Instrumentation 方法进入 / 退出要求 |
| `kInstrumentWithEntryExitHooks` | 运行方法进入 / 退出钩子，仍可执行支持钩子的编译代码 |
| `kInstrumentWithInterpreter` | 安装 interpreter stubs，使方法进入解释器 |

Instrumentation 按客户端 key 保存请求，`DeoptManager` 另外用引用计数管理重复的全局需求。只有对应客户端解除请求，且没有其他客户端需要同等级别，Instrumentation 才能降低级别。全局 deopt 生效期间，JIT 的编译入口会因 `AreAllMethodsDeoptimized()` 返回 `true` 而跳过方法编译。

API 37 的 JVMTI event 映射也有明确边界：

- 断点、异常、方法进入 / 退出属于受限作用域要求；
- 全局监听异常捕获需要完整 deopt；
- 字段访问 / 修改、单步执行、弹出栈帧、强制提前返回，在没有目标线程时需要完整 deopt，有目标线程时限制到该线程；
- 类加载、已编译方法加载、GC 等事件不要求 deopt。

“启用任意 JVMTI 代理都会让全进程永久解释执行”不成立。应根据代理启用的事件和线程过滤器判断。

## 五、Debugger、方法追踪与类重定义

### 5.1 连接调试器不等于 `DeoptimizeEverything`

Android 17 可以把正在运行、原本不支持 Java 调试的 runtime 切换到 Java-debuggable 状态。转换过程会暂停 JIT，等待后台验证任务完成，使已有 JIT 代码失效，调用 `TransitionToDebuggable()`，让 JIT 使用支持调试的编译选项，并更新入口点，避免继续使用不带调试支持的 AOT 代码。

这次转换本身不等价于全局 `kInstrumentWithInterpreter`。是否继续到方法级、线程级或全局 deopt，取决于 debugger/JVMTI 随后请求的能力：

- 在普通方法设置断点，通常只 deopt 该方法；
- 对单个线程执行单步调试，使用线程级路径；
- 全局单步调试、异常捕获等事件才请求全局解释器；
- 方法跟踪可以选择进入 / 退出钩子，也可以要求使用解释器。

因此，性能报告应记录是否 debuggable、是否 attach、启用了哪些事件，不能只写“开了调试器”。

### 5.2 普通与结构性类重定义的代价不同

非结构性类重定义会为旧方法建立 obsolete method（保留给活动栈使用的旧方法版本），修正活动栈中的方法指针，并通过 `MoveObsoleteMethod()`、`NotifyMethodRedefined()` 更新 JIT 数据。

结构性类重定义可能改变字段或方法布局，风险更大。API 37 会：

- 强制为每个线程的每个可去优化帧设置重定义标志；
- 替换类 / 实例引用并清理解释器缓存；
- 调用 `InvalidateAllCompiledCode()` 清空 JIT 编译代码；
- 让后续边界检查把活动编译帧转入解释器。

Android Studio Apply Changes 最终走哪种路径取决于修改内容和部署机制。不能把每次 Apply Changes 都描述为结构性全量 deopt。

### 5.3 第三方 hook 要按实现判断

Hook 工具可能使用 JVMTI 断点 / 类重定义、修改方法入口点，或调用非 SDK 的 ART 内部接口。不同方案影响的调用者、被调用者和全局插桩级别并不相同。

诊断时需要确认三点：它是否只改目标方法，是否处理已经内联该方法的调用者，以及是否长期保持 interpreter stubs。缺少这三项证据时，不应把一次卡顿直接归因于“Xposed 导致全进程 deopt”。

## 六、deopt 后会执行什么代码

单帧 deopt 只保证当前正在执行的编译帧在解释器里继续。之后的调用由代码来源和失效范围决定：

- 非 debugging 的显式单帧 deopt 会调用 `InvalidateCompiledCodeFor()`；
- JIT inline-cache / same-target deopt 会把造成未命中的接收者类型补入性能画像信息（profiling info），降低同一类型反复未命中的概率；
- 调试 deopt 保留可复用的优化代码，调试要求解除后可以恢复；
- 方法级 deopt 在请求解除前禁止该方法重新 JIT；
- 全局解释器级别生效时，JIT 会跳过所有方法编译；
- 结构性类重定义会使全部 JIT 编译代码失效，恢复速度取决于后续热度与 JIT 调度。

“每次 deopt 后一定立即重编译”并不准确。JIT 是否再次编译取决于方法热度（hotness）、code cache、当前插桩级别、方法是否可编译，以及进程随后是否继续执行该路径。

Baseline Profile（基准配置文件）也不能阻止守卫条件、CHA 或调试器触发 deopt。它可以改变安装期编译范围和正常启动成本，但全局 interpreter stubs 生效时，已有 AOT / JIT 代码仍不能按原方式执行。评估 Baseline Profile 时要把 deopt 前的编译收益和 deopt 后的运行状态分开。

## 七、性能影响怎样分层

### 7.1 一次性停顿

显式单帧 deopt 的同步成本主要来自 stack map 解码、ShadowFrame 分配、代码失效和 long jump。内联越深、虚拟寄存器越多，恢复工作越多。

CHA 失效还包含 JIT code cache 更新和跨线程 checkpoint。类加载线程会等待 checkpoint 完成，这部分可能落在启动、插件加载或首次使用功能的关键路径上。

JVMTI 方法级 / 全局操作通常在 suspend-all 区间内更新执行入口和线程栈。已加载类数量、线程数和栈深都会影响暂停时间。

### 7.2 持续吞吐损失

方法级或全局请求如果长期存在，主要成本来自解释执行与 Instrumentation 回调，而非首次切换本身。热循环、布局、动画和启动路径上的少量方法就可能放大影响。

发布版本基准测试应使用 `debuggable=false`，并按需启用 `profileable`，允许 shell 进程采集轨迹。Macrobenchmark 或测试注解不能证明被测 APK 与线上编译条件一致；仍要核对构建变体、清单标志和 ART 编译状态。

### 7.3 code cache 与重新升温

失效的 JIT 代码不能在仍有线程执行时直接释放。`JitCodeCache::DoCollection()` 会通过 checkpoint 标记线程栈上仍在执行的编译代码，再由 `RemoveUnmarkedCode()` 清理已不可达、等待回收的 zombie code。

deopt 后看到 `DoCollection` 或密集的 `JIT compiling`，说明 runtime 正在处理 code cache 或重新编译；它们是相关证据，不代表每次回收都由 deopt 触发。持续出现同一方法、同一原因的 deopt 与重编译交替，更接近 deopt thrashing（去优化与重编译反复发生的抖动）。

## 八、Android 17 的可观测性

### 8.1 Perfetto 能直接看到哪些时间片

API 37 的单帧路径在 `QuickExceptionHandler::DeoptimizeSingleFrame()` 中输出：

```text
Deoptimizing <PrettyMethod>: <DeoptimizationKind name>
```

这条 `SCOPED_TRACE` 位于 `DeoptimizeStackVisitor::WalkStack()` 之后。因此时间片能确认方法和原因，但其 `dur` 不包含此前完整的 ShadowFrame 重建时间，不能直接当作 deopt 总耗时。

JIT compiler 另有：

```text
JIT compiling <PrettyMethod> (kind=<CompilationKind>) from <dex location>
```

code cache 回收的稳定函数名包括 `DoCollection` 和 `RemoveUnmarkedCode`。API 37 的 `instrumentation.cc`、`cha.cc` 和 `deopt_manager.cc` 没有输出名为 `ConfigureStubs`、`FullDeoptimization`、`Single method deoptimization` 或 `CHA::UpdateAfterLoadingOf` 的 atrace 时间片；其中一些名称只出现在测试或函数名中。

下面的 Perfetto ftrace 配置用于抓目标应用的 ART 与调度事件：

```textproto
data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      atrace_categories: "dalvik"
      atrace_categories: "sched"
      atrace_apps: "com.example.app"
    }
  }
}
```

`dalvik` 提供 ART 的作用域轨迹（scoped trace），`sched` 用于判断 deopt 前后线程是否被抢占，或长时间处于 runnable（已就绪但没有获得 CPU）状态。生产型 APK 还需要满足设备与 `profileable` / `debuggable` 的跟踪权限条件。

下面的查询按时间排列 deopt、JIT 编译和 code cache 回收：

```sql
SELECT
  ts,
  dur / 1e6 AS dur_ms,
  process_name,
  thread_name,
  name
FROM thread_slice
WHERE name GLOB 'Deoptimizing *'
   OR name GLOB 'JIT compiling *'
   OR name IN ('DoCollection', 'RemoveUnmarkedCode')
ORDER BY ts;
```

若轨迹中只有 `Deoptimizing` 而没有后续 JIT，可能是方法没有再次变热、当前 Instrumentation 状态禁止编译，或恢复到了其他可用代码。反过来，JIT 编译本身也不是 deopt 证据。

### 8.2 SIGQUIT 提供累计原因计数

`Runtime::DumpForSigQuit()` 会调用 `DumpDeoptimizations()`，按 `DeoptimizationKind` 输出本进程累计次数。下面的命令先向目标进程发送 SIGQUIT，再从日志中筛选计数：

```bash
adb shell kill -3 "$(adb shell pidof com.example.app | tr -d '\r')"
adb logcat -d | grep -E 'Number of .* deoptimizations'
```

SIGQUIT 同时会输出线程栈和 ART 状态，日志量较大。计数从进程启动累计，缺少方法名和时间戳；它适合比较同一实验前后的增量，不能替代 Perfetto 时间线。

### 8.3 编译状态和调试条件要一并保存

下面的命令分别检查 ART Service 的包状态、清单 / 调试标志和当前进程：

```bash
adb shell pm art dump com.example.app
adb shell dumpsys package com.example.app | grep -E 'DEBUGGABLE|PROFILEABLE|flags='
adb shell pidof com.example.app
```

`pm art dump` 反映 dexopt 产物与编译过滤器（compiler filter），不会显示某个活动帧是否刚刚发生 deopt。三组信息要与系统构建指纹（build fingerprint）、应用版本、是否连接调试器、JVMTI 代理配置一起记录。

`-verbose:deopt,jit` 是 API 37 支持的 ART runtime 日志选项，但必须在目标 runtime 启动参数中生效。临时修改属性后不重启对应 runtime / 进程，不能保证已有应用获得该选项；量产设备也可能限制这类日志。未确认启动参数时，不能把“logcat 没有 Deoptimizing”当作零 deopt。

## 九、一次可复现的实验

1. 使用 `debuggable=false` 的基准 APK，记录 `pm art dump` 和包标志；
2. 预热固定次数，保存 SIGQUIT deopt 原因计数基线；
3. 在不连接调试器的条件下采集一次业务轨迹；
4. 分别增加动态类加载、单方法断点、线程级单步执行和全局 JVMTI 事件；
5. 每次只改变一个变量，比较 deopt 原因增量、目标方法、suspend-all 邻近调度和 JIT 活动；
6. 对重复 deopt 的方法检查守卫失败原因、接收者类型、CHA 依赖，或仍在生效的 Instrumentation 客户端；
7. 去掉调试或代理后重新运行同一工作负载，确认 interpreter stubs 和方法 deopt 是否已经撤销。

“健康应用必须零 deopt”不是有效标准。JIT 推测优化允许少量守卫未命中，动态类加载也可能产生一次合法的 CHA 修正。需要处理的是落在关键路径、反复命中同一原因、触发长期解释执行，或与大范围 JIT 失效共同出现的事件。

## 十、版本边界与源码入口

以下源码入口以 `android-17.0.0_r1` 为锚点。Android 12～17 都具备 optimizing compiler（优化编译器）、ShadowFrame 与 Instrumentation deopt 的主体设计，但枚举、调试 runtime 转换、JVMTI 事件映射和轨迹名称应按目标版本核对。

API 37 的主要入口如下：

- deopt 原因：`runtime/deoptimization_kind.h`
- 编译代码入口：`runtime/entrypoints/quick/quick_deoptimization_entrypoints.cc`
- 栈帧重建：`runtime/quick_exception_handler.cc`
- 解释器恢复执行：`runtime/interpreter/interpreter.cc`
- 方法级 / 全局 deopt：`runtime/instrumentation.cc`
- CHA 失效 / checkpoint：`runtime/cha.cc`
- inline-cache / CHA 守卫：`compiler/optimizing/inliner.cc`
- BCE 守卫：`compiler/optimizing/bounds_check_elimination.cc`
- JVMTI 事件作用域：`openjdkjvmti/events.cc`
- 调试器 / JVMTI 协调：`openjdkjvmti/deopt_manager.cc`
- 类重定义：`openjdkjvmti/ti_redefine.cc`
- JIT 编译调度 / 去优化时跳过编译：`runtime/jit/jit.cc`
- JIT 失效 / 回收：`runtime/jit/jit_code_cache.cc`

排查时可以沿一条固定链路收集证据：哪个假设或 Instrumentation 请求触发了 deopt，作用域覆盖哪些方法 / 线程，活动帧在哪个边界恢复成 ShadowFrame，后续调用使用解释器还是重新获得编译代码。四个问题都有证据后，才能把一次卡顿归因到 ART 去优化。
