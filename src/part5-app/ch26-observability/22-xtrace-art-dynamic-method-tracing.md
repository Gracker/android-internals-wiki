---
title: "生产级 ART 动态方法追踪：XTrace 论文机制与 Android 17 边界"
chapter: "26.22"
section: "26.22"
status: finalized
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
tags: [ART, tracing, instrumentation, XTrace, dynamic-tracing, production, Ghost-Bug, bytedance]
related_chapters: ["1.7", "13.1", "14.11", "26.18", "26.25"]
last_verified: "2026-08-15"
last_source_verified_at: "2026-08-15"
last_verified_against: "arXiv:2512.21555v1, still the only public version and without venue metadata as of 2026-08-15; AOSP android-17.0.0_r1 ART sources; current Android Developers, AOSP ART TI, Android 17 features, and Perfetto documentation retrieved 2026-08-15"
confidence: high
sources:
  - type: paper
    path: "https://arxiv.org/abs/2512.21555"
    note: "XTrace: A Non-Invasive Dynamic Tracing Framework for Android Applications in Production; arXiv v1 submitted 2025-12-25; no public venue metadata as of 2026-08-15"
  - type: legacy-reference-preserved
    path: "DeepResearch/XTrace：字节跳动生产级 Android 动态追踪系统深度解析.md"
  - type: legacy-reference-preserved
    path: "art/runtime/instrumentation.h, art/runtime/instrumentation.cc (android-17.0.0_r1)"
  - type: legacy-reference-preserved
    path: "art/runtime/art_method.h (android-17.0.0_r1)"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/instrumentation.h"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/instrumentation.cc"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/trace.cc"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/art_method.h"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/arch/arm64/quick_entrypoints_arm64.S"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Debug.java"
  - type: official
    path: "https://developer.android.com/reference/android/os/Debug"
  - type: official
    path: "https://developer.android.com/studio/profile/record-java-kotlin-methods"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingManager"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/profile-types-overview"
  - type: official
    path: "https://developer.android.com/about/versions/17/features"
  - type: official
    path: "https://developer.android.com/studio/profile/sample-callstack"
  - type: official
    path: "https://source.android.com/docs/core/runtime/art-ti"
  - type: official
    path: "https://perfetto.dev/docs/"
---

# 26.22 生产级 ART 动态方法追踪：XTrace 论文机制与 Android 17 边界

动态方法追踪会在程序运行时记录指定方法的进入、退出或异常事件。XTrace 论文针对一个生产诊断难题：事故发生后才知道要观察哪个方法，希望无需重新发版就能下发目标，同时避免全量方法追踪拖慢用户设备。

公开材料目前只有论文，没有可下载的 XTrace SDK 或源码。判断这项方案时需要分开回答三个问题：

- 论文公开了哪些机制和实验结果；
- 这些机制与 `android-17.0.0_r1` 的 ART 源码是否一致；
- 普通应用可以采用哪些受支持的方案，哪些能力只能由自研基础设施或系统镜像提供。

## 证据范围

截至 2026-08-15，arXiv 提交历史仍只有 2025-12-25 上传的 [arXiv v1 手稿](https://arxiv.org/abs/2512.21555)。arXiv 页面没有会议或期刊元数据；PDF 上的 `Conference’17, July 2017, Washington, DC, USA`、假 ISBN 和占位 DOI 来自 ACM 模板，不能作为正式发表证据。

论文也未附带 XTrace 源码、SDK、符号表或可复现实验脚本。文中的结论按三类证据区分：

| 标记 | 含义 |
|---|---|
| 论文报告 | 数字、案例或内部流程来自 arXiv v1，公开资料不足以独立复现 |
| Android 17 源码确认 | 能在 `android-17.0.0_r1` 的 AOSP 文件中找到对应实现 |
| 工程建议 | 根据公开机制和风险边界提出的做法，不归入论文结论或平台保证 |

论文报告的兼容范围是 **Android 5.0–15+**。Android 17 部分来自源码对照，只能说明 ART 实现已经变化，无法证明 XTrace 在 Android 17 设备或厂商 ROM 上通过验证。

## 为什么会需要“事后指定目标”的方法追踪

论文把一类只有 Framework、WebView 或库代码栈、缺少业务入口的线上问题称为 Ghost Bug。Ghost Bug 是论文自定义名称，指“故障现场可见，但更早的触发者已经离开当前调用栈”的诊断困境。Framework 在这里指 Android 系统向应用提供组件、窗口等能力的框架层。

例如，某个监听器较早注册了不合适的 `Context`，稍后由异步消息触发 `Context.getDisplay()` 异常。`Context` 是 Android 组件访问资源和系统服务的环境对象，部分窗口 API 要求它关联正确的 display。崩溃栈只能看到使用这个对象的阶段；要追查对象来自哪里，需要在监听器注册方法被调用时记录调用者。事故前若没有日志或插桩，常规崩溃上报无法补回这段历史。

几类工具回答的问题并不相同：

| 手段 | 擅长的问题 | 主要边界 |
|---|---|---|
| Perfetto system trace | 把调度、频率、Binder IPC、帧和预埋 trace section 放到同一时间线 | 默认不会记录任意 Java 方法的每次进入 |
| 调用栈采样 | 周期性截取线程栈，找 CPU 热点和概率意义上的调用路径 | 短方法可能落在两次采样之间 |
| `Debug.startMethodTracing()` | 一段时间内的 Java/Kotlin 方法进入与退出 | 追踪开销高，Android 文档建议缩短录制时长 |
| 编译期 ASM 插桩 | 用 ASM 字节码库在构建时改写自有代码与 APK 内字节码 | 无法修改设备 boot class path 中的系统框架类；事故前必须已有插桩 |
| JVMTI / ART TI | 通过原生 agent 接收虚拟机事件并执行调试、分析操作 | Android 仅允许向 `debuggable` 应用附加 agent |
| XTrace 论文方案 | 线上按配置选择目标方法，并记录精确调用事件 | 私有实现、未开源，依赖 ART 内部 C++ 设施 |

Binder IPC 是 Android 的跨进程调用机制，boot class path 是系统启动时提供给应用的核心 Java 类路径。JVMTI（Java Virtual Machine Tool Interface）是虚拟机工具接口，ART TI 是 Android 对这套能力的实现；agent 则是加载进目标进程、通过接口接收回调的原生库。`debuggable` 表示应用在清单中明确允许调试和插桩，量产发布包通常关闭该标记。

Perfetto 支持动态 trace config（追踪配置），也支持 Java/Kotlin 调用栈采样。XTrace 的差异在于按方法签名拦截一次具体调用，并在事件发生时执行自定义动作。这里的 hook 指改变或截获原有执行入口。采样、系统 trace 与精确方法事件应按诊断问题组合使用。

## Android 17 的 ART Instrumentation 是什么

### 事件监听器位于 ART 内部

[`runtime/instrumentation.h`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/instrumentation.h) 定义了 `InstrumentationListener`。ART（Android 运行时）负责执行应用代码，DEX 是 Android 保存应用字节码的文件格式；Instrumentation 是 ART 内部向调试器和分析工具分发事件的设施。监听器可以接收方法进入、正常退出、异常展开、字段访问和异常等事件。`ArtMethod` 是 ART 在原生层描述一个已加载方法的对象，`MethodEntered` 会收到当前线程和该对象；正常退出回调还可以接收返回值。

下面的源码摘录用于确认 Android 17 仍有三种插桩级别，以及方法进入事件前存在快速检查：

```cpp
enum class InstrumentationLevel {
  kInstrumentNothing,
  kInstrumentWithEntryExitHooks,
  kInstrumentWithInterpreter
};

void MethodEnterEvent(Thread* thread, ArtMethod* method) const {
  if (UNLIKELY(HasMethodEntryListeners())) {
    MethodEnterEventImpl(thread, method);
  }
}
```

这个快速分支会在没有方法进入监听器时跳过事件分发。启用追踪后还要安装入口/出口 hook、切换 ART 调试状态、遍历已加载类、写入事件并执行监听器，因此“非目标方法零开销”仍需用完整路径实验验证。

### `EXPORT` 不等于 Android 公共 API

`Instrumentation::AddListener()`、`EnableMethodTracing()`、`UpdateMethodsCode()` 和 `ArtMethod` 都是 ART 原生代码中的 C++ 接口。源码里的 `EXPORT` 控制符号在原生二进制中的可见性；Android SDK/NDK 是否承诺兼容，要以公开 API 文档和对应头文件为准。

普通应用可直接调用 [`android.os.Debug.startMethodTracing()`](https://developer.android.com/reference/android/os/Debug) 等 Java API。`Debug.startMethodTracingDdms()` 带有 `@hide`；`Instrumentation` 与 `ArtMethod` 也属于平台内部实现。ART APEX 是可独立更新 ART 的模块化系统包，ABI 是二进制层的调用约定。动态链接器命名空间限制应用能加载哪些共享库和符号；私有依赖还会受到 APEX 更新、厂商修改、ABI 变化与符号裁剪影响。

### Android 17 的方法追踪不再必然全量解释执行

旧版本分析常引用下面这个默认值：

`kDeoptimizeForAccurateMethodEntryExitListeners = true`

这个默认参数在 Android 17 源码中仍然存在，但实际行为由调用方传值决定。Android 17 的 [`Trace::Start()`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/trace.cc) 显式传入 `false`，覆盖了默认值：

```cpp
runtime->GetInstrumentation()->AddListener(
    the_trace_,
    Instrumentation::kMethodEntered |
        Instrumentation::kMethodExited |
        Instrumentation::kMethodUnwind,
    listener_type);

runtime->GetInstrumentation()->EnableMethodTracing(
    kTracerInstrumentationKey,
    the_trace_,
    /*needs_interpreter=*/false);
```

`EnableMethodTracing()` 因而选择 `kInstrumentWithEntryExitHooks`，没有选择 `kInstrumentWithInterpreter`。Android 17 的普通 method tracing 会优先使用方法进入/退出 hook，统一强制解释执行已经不符合这条调用路径。

method tracing 仍不适合长期运行在生产环境。Android 17 的普通 tracing 路径会执行这些工作：

- 切换到 Java-debuggable 状态，失效 JIT 编译代码缓存（`code cache`），并对 boot image 做反优化；boot image 是预加载核心类及其编译结果的运行时镜像；
- `ConfigureStubs()` 进入 `UpdateStubs()` 后，通过 `ClassLinker::VisitClasses()` 检查已加载方法；
- 现有代码不支持 entry/exit hook 时，把非 native 方法入口改到解释器桥；解释器桥会从已编译入口转入字节码解释执行；
- 为每次方法进入、退出或异常展开记录事件。

JIT（Just-In-Time）会在应用运行时编译热点方法，AOT（Ahead-Of-Time）则提前生成机器码。上述状态切换和事件写入都会改变执行条件。Android Studio 官方文档仍建议把 Java/Kotlin 精确方法追踪控制在五秒以内，并提醒插桩会改变被测程序的时间表现。

### Android 17 的入口也发生了变化

论文展示的 ARM64 快速入口名为 `art_quick_instrumentation_entry`。`android-17.0.0_r1` 的 [`quick_entrypoints_arm64.S`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/arch/arm64/quick_entrypoints_arm64.S) 已找不到这个旧名称，源码包含 `art_quick_method_entry_hook`，并通过 `artMethodEntryHook` 进入 C++。`Trace::Start()` 还会根据时钟源选择 fast 或 slow listener：fast 路径要求 JIT 代码无需为读取线程 CPU 时钟进入内核，32 位 Arm 因时间戳条件固定使用 slow 路径。这是 ART 内部分类，不表示 fast 路径没有追踪成本。

这些变化说明 Android 15 的私有符号映射无法直接充当 Android 17 适配结果。每个目标版本都要重新核对入口协议、寄存器保存、JIT/AOT code header（编译代码头）、线程挂起条件、失败恢复路径和厂商 ART 版本。

## XTrace 论文提出了什么

### 目标注入

论文认为传统 method tracing 的主要静态成本来自处理大量已加载方法。XTrace 把配置指定的方法组成 target set（目标集合），只更新这些方法的入口，其余方法继续沿原入口执行。这个设计减少全局遍历和改写，但监听器状态与运行时切换仍可能产生进程级成本。

### 自适应入口

stub 是负责保存现场、调用追踪逻辑并恢复执行的一小段入口代码。目标方法已有 JIT/AOT 编译代码时，论文选择 ART 的 instrumentation 快速 stub，在回调后继续执行原机器码；方法处于解释状态时，则选择解释器入口。两类入口分开选择，避免把已有编译代码的目标方法统一改走解释器。

### 事件代理

论文将事件代理注册到方法进入事件，再通过 JNI 调用 Java 层 interceptor。JNI（Java Native Interface）连接 C/C++ 与 Java；interceptor 是收到命中事件后执行采集动作的拦截器。配置包含类名、方法名、参数/返回类型签名和动作，例如只在 `addWindowLayoutInfoListener()` 被调用时采集调用栈。

这段伪代码只复述论文 Algorithm 1 的职责顺序，无法直接编译，也没有表达线程挂起、JIT 并发和失败恢复：

```text
将 EnableMethodTracing 的全局处理替换为空处理
对目标方法集合逐个选择入口，并更新方法入口
注册 MethodEntryProxy
借助 Debug.startMethodTracingDdms 启动事件处理
MethodEntryProxy 只处理配置命中的方法
```

公开论文没有给出 hook 引擎、符号解析、方法重载消歧、入口写入同步或卸载代码。直接把伪代码翻成 native hook，会遗漏暂停线程、原子更新入口、处理 JIT 重编译和恢复原入口等进程安全条件。

### “不侵入”应理解为论文中的相对概念

XTrace 不改写 DEX 方法体，也不覆盖目标机器码开头；后一种做法通常称为 inline hook。它仍会 hook ART 私有函数、定位 `ArtMethod` 并改变方法执行入口。因此，“Non-Invasive”只表示相对其他 hook 路径减少改写范围，公开 Android API、Play Integrity 结果、SELinux 策略和厂商 ROM 兼容性都没有随之获得保证。Play Integrity 用于评估应用和设备环境完整性，SELinux 则执行系统强制访问控制。

论文称其 SDK 无需 root 或系统权限，并把 `UpdateMethodsCode`、`EnableMethodTracing`、`MethodEntered` 称为 “public subset”。这里的 public 表示作者选用的 ART 符号子集；按 Android API 定义，这些 C++ 接口仍是平台内部实现。作者的部署经验与 Android SDK 兼容性合同应分开记录。

## 论文实验应该怎样读

### 在线稳定性

DAU（Daily Active Users）是每日活跃用户数。论文报告了一次持续一个月、约 1.08 亿 DAU 的 A/B 实验：用户被分到不启用 XTrace 的对照组和启用 XTrace 的实验组，两组各约 5400 万人。Crash User Rate 和 ANR Rate 是论文沿用的指标名；ANR 表示 Application Not Responding（应用无响应），公开文本没有给出两项指标的去重周期和精确分母。

| 指标 | 对照组 | XTrace 组 | 相对变化 | p 值 | 论文结论 |
|---|---:|---:|---:|---:|---|
| Crash User Rate | 0.018490% | 0.018501% | +0.0595% | 0.615817 | 通过论文设定的 +0.5% 非劣界值 |
| ANR Rate | 0.025480% | 0.025510% | +0.1177% | 0.551651 | 通过论文设定的 +0.8% 非劣界值 |

非劣界值是实验预先允许的最大相对恶化幅度，95% 置信区间表示样本估计的不确定范围。论文表中的区间上界低于 Crash 的 +0.5% 和 ANR 的 +0.8% 界值，因此按其规则判为通过。p 值高于 0.05 只表示本次检验没有观察到统计显著差异，单靠 p 值无法证明两组完全等价。

这些结果支持的范围是该应用、该配置和该统计口径。目标方法数量、命中频率、机型分布或采集动作变化后，风险需要重新实验。

### 启动与单次调用

性能实验只使用一台 Android 15 小米设备，以 `Log.e` 为追踪目标，每个数值来自十次测量。表中的“均值 ± 标准差”同时表示平均值和样本波动。论文 Table 2 报告：

| 启动类型 | 无 XTrace | XTrace | Frida |
|---|---:|---:|---:|
| 冷启动 | 450.2 ± 25.1 ms | 456.7 ± 25.9 ms，增加 6.5 ms | 580.5 ± 45.2 ms，增加 130.3 ms |
| 热启动 | 180.5 ± 10.3 ms | 183.9 ± 10.8 ms，增加 3.4 ms | 215.8 ± 18.5 ms，增加 35.3 ms |

Frida 是支持动态插桩和函数拦截的通用工具。论文还报告 XTrace CPU 增量低于 1%，单方法事件低于 0.01 ms；Frida 对照约为 5%–8% 和 0.1–0.2 ms。这些数字来自单设备、单目标，不能按比例换算“追踪 100 个方法必然增加多少毫秒”。

### 消融实验

消融实验会逐项移除设计机制，观察性能变化，以判断每个机制的贡献。论文 Table 3 比较了完整方案、关闭目标注入的全局版本和关闭自适应入口的解释器版本：

| 指标 | 完整 XTrace | XTrace-Global | XTrace-Interpreter |
|---|---:|---:|---:|
| 冷启动增量 | 约 6.5 ms | 约 418.0 ms | 约 8.0 ms |
| CPU 增量 | < 1.0% | 约 37.1% | 约 1.5% |
| 单次调用延迟 | < 0.01 ms | 约 0.03 ms | 约 0.13 ms |

这组数据支持两个局部结论：缩小目标集合主要改善启动与全局 CPU 成本，保留编译代码主要改善高频调用的事件成本。实验设备运行 Android 15，数据不能用于推断 Android 17 原生 tracing 仍沿用论文描述的旧路径。

### 兼容性

ROM 在这里指设备厂商交付的 Android 系统构建。论文报告的范围与结果是：

- Android 5.0–15+；
- 1200 个自动化场景；
- 测试 ROM 覆盖该应用 98% 的 DAU；
- 功能通过率 99.9%；
- 新 Android 版本通常需要 1–2 人日适配。

论文未公开 ROM 清单、失败场景、测试代码和 Android 17 数据。Android 17 ART 已出现入口与 tracing 路径变化，“更新符号表即可适配”的说法缺少公开证据。

## 两个案例能说明什么

### Ghost Bug：找到错误 `Context` 的生产者

论文案例中，异常发生在 `WindowLayoutComponentImpl.onDisplayFeaturesChanged()` 读取监听器关联的 `Context` 时，影响每天超过 4 万名用户。异常栈只有系统与库代码，业务侧需要知道谁更早调用了 `addWindowLayoutInfoListener()`。

XTrace 配置命中该注册方法并记录调用栈。论文展示的调用路径从 `SparkFragment.onCreateView()` 经混合容器和 `WebView.evaluateJavascript()`，到 Chromium 的 device-posture 逻辑，再进入 `addWindowLayoutInfoListener()`。团队据此修正传入的 `Context`，报告称三小时内完成定位和修复，发布后小时崩溃数降为零。

这个案例通过记录监听器注册时的调用者，补回了异步消费栈中缺失的来源。遇到异步消费、监听器注册、缓存写入和任务投递时，可以优先观察“谁写入或投递”，再观察稍后“谁读取或执行”。

### UI 卡顿：从 measure 阶段定位到实例

论文先用 Perfetto 看到 `Choreographer.doFrame` 多次超过 16.6 ms，并把热点缩小到 measure 阶段。随后 XTrace 同时观察 `FrameDisplayEventListener.run` 与 `View.measure`，报告同一个 `RelativeLayout` 每帧出现三次 measure 调用，并保留了各次调用的 Java 栈。

团队据此找到 layout constraint（布局约束）冲突，论文称半天内修复；后续 A/B 实验中，处理组 UI 掉帧率下降 25.95%。论文没有说明两套数据是否共享时钟、trace ID 或自动关联逻辑；trace ID 是跨数据源标识同一次诊断事件的关联编号。公开证据能支持的过程是：先用 Perfetto 缩小阶段，再用方法事件定位具体实例；可复用的数据自动关联能力尚无实现细节。

## 生产系统比 hook 本身更难

论文把 XTrace 包装成 native library（原生库）和 Java wrapper（对外封装层），并通过内部 A/B 平台下发配置。它报告的运行流程包括：

- 授权工程师提交带版本的配置；
- 数据保护人员审核目标与动作；
- 通常从 0.1% 用户开始金丝雀发布，也就是先让极少量用户接收配置；
- 观察 Crash 与 ANR 等健康指标；
- 异常时停止下发，并让已接收配置失效；
- 稳定后逐步扩大范围。

数据处理也不止“上传方法名”。论文明确提到运行时数据可能包含方法参数：原始数据只在设备内存中处理，先经 DLP（Data Loss Prevention，数据防泄漏）规则去除或遮盖可识别个人的信息，再使用应用层加密和 TLS 1.3 传输；后端使用聚合数据，并设定 14 天保留期。TLS 1.3 保护传输过程，DLP、访问控制和删除期限仍要由配套系统实现，XTrace 方法拦截本身不会自动提供这些控制。

团队设计相似设施时，至少要评审四组问题。

### 配置是否能安全命中方法

- 类加载器决定类来自哪个命名空间；方法重载需要用参数和返回类型消歧；桥接方法是编译器为泛型等语义生成的适配方法。配置必须明确这三类匹配规则；
- Kotlin `suspend` 函数会被编译成带 `Continuation` 的状态机方法，混淆映射则负责把线上短名称还原为源码名称；两者都要纳入签名解析；
- 目标方法尚未加载、被 JIT 重编译或入口被其他工具修改时怎样处理；
- ART APEX 版本、ABI、厂商指纹和符号校验失败时是否拒绝启用；
- 每项配置是否有有效期、设备范围、版本范围和远程停用能力。

### 回调能否在任意线程运行

- interceptor 必须防止递归，也就是采集过程中触发同一目标时直接旁路；记录日志、序列化或上报路径都可能造成再次命中；
- 主线程、Binder 线程、GC 临界区和持锁路径中不能执行阻塞 I/O；GC（Garbage Collection，垃圾回收）负责回收不可达对象，临界区则是运行时要求保持特定锁或线程状态的一段代码；
- 事件缓存必须有容量上限和丢弃策略；
- 正常退出、异常展开、进程终止与配置撤销都要恢复入口和监听器状态；恢复失败时应关闭该设备上的后续动态配置。

### 数据是否超出诊断目的

- 默认只采集方法标识、线程、时间与必要的调用栈；
- 参数、返回值、对象字段和 WebView 内容要单独授权；技术上可读取不构成采集许可；
- 设备端脱敏前的原始数据同样属于敏感数据；
- 服务端需要审计查询、访问控制、删除期限和按实验隔离。

### 实验结论是否可解释

- 记录目标数量、命中频率、设备分布、ART 版本和配置动作；
- 分别观察启用、运行、撤销三个阶段，避免只测稳定运行阶段；
- 使用同版本对照组，并预先定义 Crash、ANR、启动和 CPU 的判断标准；
- 对出现过符号解析或恢复失败的设备保留失败分类，并把失败样本纳入风险统计。

## Android 17 上怎样选方案

| 需求 | 建议工具 | 原因 |
|---|---|---|
| 线上 CPU 热点或长调用路径 | `ProfilingManager` stack sampling、Perfetto 或受支持的采样工具 | 采样开销可控，不要求私有 ART hook |
| 线上系统调度、Binder、帧和内存事件 | `ProfilingManager` system trace / Perfetto | Android 15 起可由应用请求；Android 16 起可注册系统触发器，Android 17 又扩展触发类型 |
| 精确观察自有方法 | 编译期 ASM 插桩，并让采集开关可远程控制 | 行为可测试，版本和代码范围由应用掌握 |
| 本地或实验室中的精确方法事件 | Android Studio method tracing、`Debug.startMethodTracing()` | 平台支持，但录制要短 |
| 对调试包做运行时 agent 分析 | JVMTI / ART TI | agent ABI 受 CTS（Compatibility Test Suite，兼容性测试套件）验证，但只允许 `debuggable` 应用 |
| 普通线上应用动态拦截任意 Framework 方法 | 没有等价的公共 Android API | XTrace 属于未开源的私有基础设施 |
| 自有系统镜像或设备产品 | 基于对应 ART tag 开发并纳入系统验证 | 可以使用内部接口，但要由平台团队维护 ABI 与升级 |

[`ProfilingManager`](https://developer.android.com/reference/android/os/ProfilingManager) 从 API 35 提供 system trace、stack sampling、heap profile 和 Java heap dump 请求。heap profile 会在分配发生时采样并保留代码位置，Java heap dump 则保存某一时刻的 Java 对象及引用关系。API 36 加入系统触发 profiling；Android 17 又增加冷启动、OOM、过度 CPU 使用和系统异常等触发类型，不同触发器会返回系统 trace、调用栈样本或堆转储。请求受限流约束，也不保证每次执行；返回结果经过脱敏，只包含请求应用相关信息。

采样适合回答“哪条路径最热”，自有代码插桩适合记录业务状态的写入者，两者都比修改 ART 私有入口更容易验证和维护。只有目标位于设备 Framework、事件短到采样难以命中、并且必须记录每次调用时，XTrace 这类方案才有独特价值。此时工作范围已经属于运行时平台工程，超出常规应用监控 SDK。

## 结论

XTrace 的主要贡献是把“只选择少量目标方法”和“尽量保留原编译执行路径”结合到 ART 方法事件机制上。论文的生产案例与大规模 A/B 数据表明，这条技术路线在作者的基础设施中获得了可用结果。

Android 17 源码给出了五条使用边界：

- XTrace 依赖 ART 私有 C++ 实现，Android 公共 API 中没有等价入口；
- 论文只报告 Android 5.0–15+，Android 17 兼容性仍待设备验证；
- Android 17 的普通 method tracing 已显式选择 entry/exit hooks，统一强制解释执行不再符合源码；
- 论文展示的 ARM64 instrumentation 入口已经变化，适配工作远多于替换符号名；
- Perfetto、调用栈采样、`ProfilingManager` 和编译期插桩各有可覆盖的生产场景。

XTrace 目前是一份尚无法独立复现的系统设计研究。目标注入、自适应入口和生产控制流程可为诊断设施设计提供参考；源码、设备覆盖和失败恢复验证齐备后，才具备进入线上进程的工程前提。

## 参考资料

1. [XTrace: A Non-Invasive Dynamic Tracing Framework for Android Applications in Production](https://arxiv.org/abs/2512.21555)，arXiv:2512.21555v1，2025-12-25。
2. AOSP `android-17.0.0_r1`：[instrumentation.h](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/instrumentation.h)、[instrumentation.cc](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/instrumentation.cc)。
3. AOSP `android-17.0.0_r1`：[trace.cc](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/trace.cc)、[art_method.h](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/art_method.h)。
4. AOSP `android-17.0.0_r1`：[ARM64 quick entrypoints](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/arch/arm64/quick_entrypoints_arm64.S)。
5. Android Developers：[Debug API](https://developer.android.com/reference/android/os/Debug)、[录制 Java/Kotlin 方法](https://developer.android.com/studio/profile/record-java-kotlin-methods)。
6. Android Developers：[ProfilingManager](https://developer.android.com/reference/android/os/ProfilingManager)、[调用栈采样](https://developer.android.com/studio/profile/sample-callstack)。
7. Android Developers：[Android 17 新增 ProfilingManager 触发器](https://developer.android.com/about/versions/17/features#profiling-manager)。
8. AOSP 文档：[ART TI](https://source.android.com/docs/core/runtime/art-ti)。
9. Perfetto：[Tracing documentation](https://perfetto.dev/docs/)。
10. [26.18 编译期字节码插桩与监控自动化](18-bytecode-instrumentation-monitoring-automation.md)。
