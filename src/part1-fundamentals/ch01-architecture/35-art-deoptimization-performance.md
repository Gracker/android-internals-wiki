---
title: "ART 去优化（Deoptimization）触发机制与性能影响"
chapter: "1.35"
status: ready-for-review
drafted_date: "2026-06-28"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-06-28"
last_verified_against: "AOSP android-17.0.0_r1, art/runtime/ branch refs/tags/android-17.0.0_r1"
confidence: high
sources:
  - type: paper
    path: "AOSP art/runtime/deopt_checkpoint.cc, quick_exception_handler.cc, instrumentation.cc, cha.cc"
  - type: blog
    path: "DeepResearch: ART 编译管线中的 Deoptimization 机制深度解析"
  - type: official
    path: "https://source.android.com/docs/core/runtime/configure"
  - type: blog
    path: "LSPlant 文档 — Deoptimize 方法说明"
tags: [art, deoptimization, deopt, jit, aot, safepoint, cha, instrumentation, perfetto]
related_chapters: ["1.7", "1.13", "1.22", "8.7", "21.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-28"
gap_source: "AOSP结构/章节深挖"
---

# 1.35 ART 去优化（Deoptimization）触发机制与性能影响

## 本节解决什么问题

当应用在运行中突然变卡、Perfetto trace 里出现不明原因的 `Deoptimization` slice、或者接入 Xposed/Hook 框架后性能暴跌时，问题往往落在 ART 的去优化（deoptimization）机制上。deopt 是 ART 在"编译假设失效"时维持语义正确性的逃生通道——它把已经编译为机器码的方法回退到解释执行。

读完本节，你能在 Perfetto 中识别 deopt 事件、定位触发源、评估性能影响，并知道哪些操作（debugger attach、Apply Changes、Hook 注入、运行时类加载）会触发它。

---

## 要点

### 🔹 去优化的本质：从编译代码回退到解释执行

ART 在 AOT（dex2oat）或 JIT 编译阶段会做推测式优化：基于编译时已知的类型信息，把虚方法调用去虚化为直接调用（devirtualization）、把短方法内联（inlining）、消除边界检查（bounds check elimination）。这些优化有一个前提——**运行时的实际行为不会违反编译时的假设**。

当假设被打破时（例如运行时加载了一个新子类，使原本"只有一个实现"的虚方法有了两个实现），ART 必须放弃已编译的机器码，回到解释执行。这个过程就是 deoptimization。

deopt 的本质是一次**特化的异常抛出**。运行时构造一个 sentinel 对象（`Thread::GetDeoptimizationException()`），把它送进正常的异常处理器栈遍历器 `QuickExceptionHandler`。处理器不找 Java `catch` 块，而是在展开每个编译帧时，通过 `DeoptimizeStackVisitor` 把它转换成 `ShadowFrame`——一种解释器能直接消费的帧结构，记录 dex 寄存器、monitor 状态和 dex PC。帧重建完成后，控制流通过 `interpreter::EnterInterpreterFromDeoptimize` 进入解释器。

[已验证: AOSP android-17.0.0_r1, art/runtime/quick_exception_handler.cc — DeoptimizeStack 路径]

> 详见 1.7 节了解 ART 编译管线（AOT/JIT/解释器三层）的整体架构，本节只展开 deopt 机制本身。

### 🔹 Deopt 触发条件分类

ART 的 deopt 不是单一操作，而是一组从"便宜且局部"到"昂贵且全进程"的机制谱系。按触发粒度可以分为三类：

**1. 同步局部 deopt（HDeoptimize）**

由优化编译器在代码中插入的 guard 检查触发。编译器在以下位置插入 `HDeoptimize` IR 节点：

- **边界检查消除**（bounds-check elimination）：循环 pre-header 里插入 guard，运行时验证索引范围
- **类型检查 guard**：`HCheckCast` / `HLoadClass` 上的类型断言
- **单态内联缓存**（monomorphic inline cache）：`TryInlineMonomorphicCall` 在 receiver class 上做类型比对，不匹配就 deopt
- **CHA 内联 guard**：基于类层次分析的虚方法内联检查

codegen 阶段，`HDeoptimize` 被降低为条件分支，跳转到 `DeoptimizationSlowPath`，后者 tail-call 到 `art_quick_deoptimize_from_compiled_code` 汇编 trampoline。

这类 deopt 代价最小——每次命中只是一条分支跳转加几个 cache line 的元数据访问。被 deopt 的方法随后会被 JIT 重新编译。

**2. 异步方法级 deopt（CHA / Instrumentation）**

当运行时发现某个编译假设已失效（如 CHA 发现新子类、Instrumentation 层要求 hook），系统需要让所有正在执行该编译代码的线程在下一个安全点回退。这通过 **ShouldDeoptimizeFlag** 机制实现：

每个符合条件的编译帧预留一个栈槽，`OatQuickMethodHeader` 的 `has_should_deoptimize_flag` 位记录其存在。Runtime 在 `ScopedSuspendAll` 暂停所有 mutator 线程后，遍历每个线程的栈，对需要 deopt 的帧写入这个槽。当线程恢复执行、方法返回或触发编译器插入的检查点时，prologue 读取该标志并跳转到 deopt 慢路径。

**3. 全进程 deopt（DeoptimizeEverything）**

`Instrumentation::DeoptimizeEverything(key)` 把所有非 native、非 proxy 的方法强制切换到解释器。这是最昂贵的操作，触发场景包括：

- Debugger attach 时切换到 Java-debuggable 状态
- JVMTI agent 请求 method-entry / method-exit / single-step 事件
- 结构性类重定义（RedefineClasses 的部分场景）
- Hook 框架的 `forced_interpret_only_` 路径

全进程 deopt 的代价分两层：`ConfigureStubs` 本身的 suspend-all 延迟（小 app 几十毫秒，加载了几千个类的大 app 数百毫秒），以及之后**所有先前被编译的方法回到解释器执行**直到 JIT 重新热起来的稳态性能恶化（可能持续数秒到数十秒）。

[已验证: AOSP android-17.0.0_r1, art/runtime/instrumentation.cc — ConfigureStubs / DeoptimizeAllThreadFrames]

### 🔹 类加载导致的去优化（CHA 失效）

CHA（Class Hierarchy Analysis）失效是异步 deopt 最典型的生产场景。

**触发链路**：`ClassLoader.loadClass` 解析一个新类 → `ClassHierarchyAnalysis::UpdateAfterLoadingOf` 遍历新类的 vtable / iftable → `CheckVirtualMethodSingleImplementationInfo` 发现某个原本"只有一个实现"的虚方法现在有了第二个 override → 清除其 single-implementation 位 → `AddDependency` 找到所有依赖这个假设的编译体 → `InvalidateSingleImplementationMethods` 将它们重置回解释器 bridge → 下发 checkpoint 在活跃帧上置 ShouldDeoptimizeFlag。

**典型触发场景**：

- **插件化框架**：运行时动态加载包含子类的 DEX，使编译阶段的去虚化决策失效
- **动态代理**：`java.lang.reflect.Proxy` 创建的类可能引入新的接口实现
- **MultiDex**：第二个 DEX 中的类加载延迟到运行时，可能触发 CHA 失效
- **ServiceLoader / DI 框架**：运行时发现新的实现类

**在 Perfetto 中的表现**：`CHA::UpdateAfterLoadingOf` slice 出现，紧跟着被影响方法的 `Single method deoptimization` 或更广泛的 deopt 事件。

[已验证: AOSP android-17.0.0_r1, art/runtime/cha.cc/.h]

> **与 1.7 节的交叉引用**：1.7 节提到了"AOT 编译的前提是编译时能确定类型和调用关系"，本节展开的是这个前提被打破时发生了什么。

### 🔹 Debuggable 应用的全面去优化

`android:debuggable="true"` 或通过 `adb shell setprop debug.app.xxx 1` 激活 debuggable 状态时，ART 的行为发生根本变化：

**Instrumentation 级别切换**：`Instrumentation::ConfigureStubs` 将全局 InstrumentationLevel 从 `kInstrumentNothing` 升级到 `kInstrumentWithInterpreter`。这意味着所有方法走解释器，JIT 可能被禁用或限制，方法 entry/exit 钩子被安装。

**JIT code cache 降级**：`JitCodeCache::TransitionToDebuggable` 使 boot image 预编译的 entrypoint 失效。Commit `a0619e2` 简化了这条逻辑：`IsJavaDebuggable()` 成为唯一判据，老的 `-Xfully-deoptable` flag 已删除。

**性能影响**：debuggable app 的性能**不能代表 release 体验**。调试器 attach 瞬间的全进程 deopt 会让先前所有 AOT 编译的方法回到解释器。对加载了几千个类的大型 app，`InstallStubsClassVisitor` 遍历每个类的 entrypoint 改写可能耗时数百毫秒。

**Android Studio Apply Changes 的陷阱**：`RedefineClasses` 走的路径包括 `JitCodeCache::NotifyMethodRedefined`、`MoveObsoleteMethod`、`InvalidateAllCompiledCode`、以及 `DeoptimizeAllThreadFrames`。开发者频繁使用 Apply Changes 会导致 JIT code cache 压力飙升和持续的编译重建。

[已验证: AOSP android-17.0.0_r1, art/runtime/instrumentation.cc — ConfigureStubs 状态机]

### 🔹 Deopt 执行链路：DeoptCheckpoint 与栈遍历

异步 deopt 的执行链路涉及 ART 的安全点（safepoint）机制和 checkpoint 协议：

**Step 1：发起 checkpoint**。Runtime 调用 `ThreadList::ModifySuspendedThreadCountOnAnyThreadUnsafe` 或类似入口，下发一个 `DeoptCheckpoint`。checkpoint 是 ART 实现的协作式暂停协议——每个 mutator 线程在 safepoint（方法返回、JNI 边界、GC 检查点）检查是否有待处理的 checkpoint。

**Step 2：线程到达 safepoint 后的栈帧重建**。线程在下一个 safepoint 检查到 checkpoint，进入 `DeoptimizeStack` 流程。`DeoptimizeStackVisitor::VisitFrame` 逐帧遍历编译代码栈，为每个帧构造 `ShadowFrame`：

- 从编译代码的 stack map（编译时记录的元数据）中提取 dex 寄存器值
- 恢复 monitor 持有状态
- 记录正确的 dex PC（使用 `DeoptimizationMethodType::kKeepDexPc` 或 `kDefault` 决定是重新执行当前指令还是跳到下一条）

**Step 3：shadow frame 链交接**。所有重建的 shadow frame 串成链表，通过 `DoLongJump()` 跳转到解释器入口 `EnterInterpreterFromDeoptimize`。解释器逐帧消费 shadow frame，运行到帧返回后将返回值传入 caller 的 shadow frame，一层层解开直到 deopt context 被 pop。

**Step 4：DeoptimizationContextRecord 清理**。`Thread::PopDeoptimizationContext` 恢复返回值和 deopt 时挂起的异常。deopt context 可组合——一个线程可以在 native-to-Java 返回途中 deopt，context 按栈序堆叠，多层 deopt 按顺序逐层解开。

[已验证: AOSP android-17.0.0_r1, art/runtime/deopt_checkpoint.cc, art/runtime/quick_exception_handler.cc]

> **与 1.13 节的交叉引用**：MessageQueue 的 dequeue 任务处理如果发生在 deopt 期间，会被延迟到 shadow frame 重建完成后才执行。详见 1.13 节关于 MessageQueue 调度时序的描述。

### 🔹 Perfetto 中的 Deoptimization 事件识别与量化

ART 在 `ATRACE_TAG_DALVIK`（短名 `dalvik`）下产出 atrace slice，可以直接在 Perfetto trace 中识别 deopt 事件。

**关键 slice 名称对照表**：

| Slice 名 | 来源文件 | 含义 |
|---|---|---|
| `Deoptimization` | `instrumentation.cc` | 通用 deopt 事件 |
| `FullDeoptimization` / `DeoptimizeEverything` | `instrumentation.cc` | 进程级全量 deopt（debugger attach、`-Xint`） |
| `Single method deoptimization` | `instrumentation.cc` | 单方法 deopt（breakpoint、LSPlant、JVMTI redefine） |
| `InstallStubsForClass` | `instrumentation.cc` | ConfigureStubs 过程中某个类的 entrypoint 改写 |
| `ConfigureStubs` | `instrumentation.cc` | Instrumentation level 变化（JVMTI / debugger / tracer 到来或离开） |
| `CHA::UpdateAfterLoadingOf` | `cha.cc` | CHA 失效——新类打破 devirt 假设 |
| `JIT compiling %s` | `jit.cc` | 单方法 JIT 编译（deopt 之后会密集出现） |
| `JitCodeCache::GarbageCollectCache` | `jit_code_cache.cc` | Zombie code 回收（大规模 deopt 后爆发） |
| `MoveObsoleteMethod` | `ti_redefine.cc` | JVMTI RedefineClasses / Apply Changes |

**Perfetto 配置**：要抓 deopt 事件，至少开启 `dalvik`、`am`、`sched` atrace category，并指定目标 app：

```text
atrace_categories: "dalvik"
atrace_categories: "am"
atrace_categories: "sched"
atrace_apps: "com.example.myapp"
```

**SQL 查询：按耗时排序的 deopt 事件**：

```sql
SELECT ts, dur, name, thread_name, process_name
FROM thread_slice
WHERE name GLOB '*Deoptimi*' OR name GLOB '*ConfigureStubs*'
ORDER BY dur DESC;
```

**SQL 查询：按进程聚合 deopt 总耗时**：

```sql
SELECT process_name, COUNT(*) AS deopt_count, SUM(dur)/1e6 AS total_ms
FROM thread_slice
WHERE name GLOB '*Deoptimi*'
GROUP BY process_name
ORDER BY total_ms DESC;
```

**SQL 查询：关联 deopt 与后续 JIT 重建活动**：

```sql
WITH deopts AS (
  SELECT ts, dur, ts + dur AS te, name
  FROM thread_slice
  WHERE name GLOB '*Deoptimi*'
),
jits AS (
  SELECT ts, name
  FROM thread_slice
  WHERE name GLOB 'JIT compiling*'
)
SELECT d.name AS deopt_event, d.dur/1e6 AS deopt_ms,
       COUNT(j.ts) AS jit_count_after
FROM deopts d
LEFT JOIN jits j ON j.ts BETWEEN d.ts AND d.te + 500e6
GROUP BY d.ts
ORDER BY d.dur DESC;
```

健康的 app 应该是零 deopt 事件。被 hook 或被调试的 app 会出现一波 deopt slice，紧跟着一波 `JIT compiling` 的爆发，表示 runtime 在重建编译池。

### 🔹 去优化与 JIT 重编译的循环：抖动场景

**deopt 抖动**（deopt thrashing）是指方法反复 deopt → 重新 JIT → 再次 deopt 的恶性循环，导致持续的性能退化。

**典型抖动场景**：

1. **AOT inline-cache miss 循环**：Commit `af44e6c` 显式关掉了 AOT inline-cache miss 的 `HDeoptimize`，原因就是 AOT profile 无法原地刷新——一个运气不好的 receiver 类型会让方法每次调用都 deopt 一次，形成永久 deopt 循环。AOT 编译的方法在遇到 inline-cache miss 时不再触发 deopt，而是静默回退。

2. **Hook 框架与 JIT 的对抗**：标准 Xposed 配方会禁用 `ProfileSaver`——既防止 JIT 偷偷重新 inline 破坏 hook，也意味着这些路径永远无法回到优化性能。Hook 引擎在 caller 上 deopt 以打破 inlining，但隐式地把 caller inline 进来的一切都 deopt 掉了，可能级联到一大片热代码。

3. **JIT code cache 压力**：突发性 deopt 让 code cache 中出现大量 **zombie code**——已被取代但可能在某些线程栈上执行的编译体。`JitCodeCache::DoCollection` 只在遍历完所有活跃线程、确认仍然可达的代码之后才清空 zombie 集合。在 zombie code 积累快于回收速度时，code cache 压力飙升，进一步限制 JIT 的重新编译能力。

**诊断方法**：

```bash
# 开启 deopt verbose 日志
adb shell setprop dalvik.vm.extra-opts -verbose:jit,deopt,class,startup
adb logcat -s art dex2oat
```

logcat 中的关键关键字：

| 关键字 | 触发源 |
|---|---|
| `Deoptimizing:` | 通用 deopt |
| `Deoptimize due to CHA invalidation for` | CHA 失效 |
| `Installing stubs for class` | Instrumentation 改写 |
| `Enabling deoptimization` | 选择性 deopt 启动 |
| `Async deopt` | 异步 deopt checkpoint |
| `DeoptManager` | JVMTI 管理的 deopt 请求 |

如果 logcat 中反复出现同一方法的 `Deoptimizing:` 和 `JIT compiling` 交替记录，说明存在 deopt 抖动。

---

## 扩展

### 🔸 Quickening 失效与 deopt 的关系

> 详见 1.22 节关于 Verifier Quickening 与 dexopt 过滤器的完整描述。

Quickening 是 Android 11 及以下解释器层的 DEX 指令优化，把部分符号引用转换成偏移量或快速形式。Quickening 本身**不直接触发 deopt**——它是解释器内部的优化，发生在 DEX 层面，不涉及编译代码的推测式假设。

两者的关联在于：如果一个方法先被 quicken 优化执行，然后被 JIT 编译（此时 JIT 的优化可能依赖 quickening 产生的快速路径信息），当 JIT 代码被 deopt 后，方法会回到解释器——这时如果 VDEX 中有 quickening 信息，解释执行可以利用快速路径；如果没有（例如 CLC mismatch 导致 VDEX 不可用），则退回纯符号解析的解释执行，更慢一层。

[已验证: 官方文档, source.android.com/docs/core/runtime/configure — quickening 仅限 Android 11 及以下]

### 🔸 Android 17 中 deopt 行为的变化

Android 17（API 37）在 deopt 机制上的主要改进方向：

1. **JIT code cache 策略调整**：更大的默认 code cache 容量减少了 deopt 后 zombie code 积压导致的编译空间不足问题。`JitCodeCache::DoCollection` 的回收策略经过优化，能更快释放 zombie code。

2. **nterp 性能提升**：Android 12+ 引入的汇编解释器 nterp（new interpreter）在 Android 17 上进一步优化，缩小了 deopt 后回退到解释执行的性能差距。这意味着同等 deopt 事件的稳态性能影响比 Android 14 之前更小。

3. **选择性 deopt 覆盖面扩大**：更多场景从全进程 deopt 迁移到方法级或帧级 deopt，减少不必要的全局解释器回退。JVMTI redefinition 的部分路径不再使用 full-deopt 大锤。

4. **Debuggable 切换优化**：`Runtime::IsDeoptimizeable` 与 `Runtime::IsAsyncDeoptimizeable` 的检查更加精细，Commit `8135664` 统一了多个调用点的 deopt 可行性检查，静默跳过不可 deopt 的帧而非崩溃。

[已更新至 Android 17]

### 🔸 Baseline Profile 如何减少 deopt 概率

Baseline Profile 本身**不能阻止运行时的 deopt 触发**——如果运行时加载了新子类导致 CHA 失效，或者 debugger attach 了，deopt 照样发生。但 Baseline Profile 从两个维度降低了 deopt 的影响：

**1. 缩短 deopt 后的重建窗口**：安装期通过 `speed-profile` 编译的热方法，在 deopt 后 runtime 有一份现成的 profile，可以按优先级重排 JIT 任务。Google 公开数据显示 Baseline Profile 带来约 30% 冷启动提升——在 deopt 高发 workload 上，这个收益会被放大，因为它同时缩短了重建编译池的时间。

**2. 更保守的去虚化决策**：Profile-guided 编译比无 profile 的 JIT 更了解实际的类型分布。编译器可以根据 profile 中观察到的 receiver 类型分布做更精准的 inline-cache 决策，减少因意外类型导致的 IC miss deopt。

> 详见 8.7 节关于 Baseline Profiles 实践和 21.4 节关于 Baseline Profile 在启动优化中的应用。

### 🔸 Gradle 采样与 deopt：为什么 release build 不要 debuggable

在 CI/CD 流水线中用 debuggable build 做性能测试，结果可能与 release 体验严重偏离：

- **debuggable=true**：ART 全程使用解释器或受限 JIT，所有方法可能被 deopt，性能指标偏高（更慢）
- **debuggable=false**：AOT/JIT 编译正常工作，deopt 只在真正的运行时事件（CHA 失效、Hook）触发

**正确做法**：

1. 性能基准测试必须用 `minifiedEnabled=true` + `debuggable=false` 的 release build
2. 如果必须用 debuggable build（如需要 logcat 详细日志），在报告中标注"debuggable 性能数据"，不要直接与 release 数据比较
3. 使用 `@Benchmark` 注解的 Macrobenchmark 测试会自动用 release 配置，避免这个问题
4. 如果发现 release build 在某些场景突然变卡，用 Perfetto 抓 trace 检查是否有 deopt 事件——可能是某个运行时类加载行为触发了 CHA 失效

```bash
# 确认当前包的编译状态和 debuggable 标志
adb shell dumpsys package dexopt | grep -A2 com.example.app
adb shell run-as com.example.app getprop debug.app.com.example.app
```

---

## 诊断命令速查

| 命令 | 用途 |
|---|---|
| `adb shell dumpsys package dexopt \| grep -A1 <pkg>` | 确认 compiler filter 和编译原因 |
| `adb shell cmd package art dump <pkg>` | Android 14+ 详细编译状态 |
| `adb shell cmd package compile -m speed-profile -f <pkg>` | 强制重编译（验证用） |
| `adb shell cmd package compile --reset <pkg>` | 重置编译状态（Android 13+） |
| `adb shell setprop dalvik.vm.extra-opts -verbose:deopt` | 开启 deopt verbose 日志 |
| `adb logcat -s art \| grep -E 'Deoptimiz\|CHA\|stubs'` | 抓 deopt 相关日志 |

---

## References

- [已验证: AOSP android-17.0.0_r1] `art/runtime/quick_exception_handler.cc` — QuickExceptionHandler::DeoptimizeStack
- [已验证: AOSP android-17.0.0_r1] `art/runtime/instrumentation.cc` — ConfigureStubs / DeoptimizeAllThreadFrames
- [已验证: AOSP android-17.0.0_r1] `art/runtime/cha.cc/.h` — ClassHierarchyAnalysis::UpdateAfterLoadingOf
- [已验证: AOSP android-17.0.0_r1] `art/runtime/deopt_checkpoint.cc` — DeoptCheckpoint 机制
- [已验证: AOSP android-17.0.0_r1] `art/runtime/jit/jit_code_cache.cc` — Zombie code 管理 / InvalidateAllCompiledCode
- [已验证: AOSP android-17.0.0_r1] `art/runtime/entrypoints/quick/quick_deoptimization_entrypoints.cc` — art_quick_deoptimize trampoline
- [已验证: AOSP android-17.0.0_r1] `art/openjdkjvmti/ti_redefine.cc` — RedefineClasses deopt 路径
- [已验证: AOSP android-17.0.0_r1] `art/openjdkjvmti/deopt_manager.cc` — DeoptManager 引用计数
- [来源: DeepResearch] "ART 编译管线中的 Deoptimization 机制深度解析:触发路径、内部机制与可观测性"
- [引用: https://source.android.com/docs/core/runtime/configure] ART 配置
- [适用版本: Android 12 - Android 17]
