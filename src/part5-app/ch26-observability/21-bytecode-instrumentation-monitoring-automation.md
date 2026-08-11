---
title: 编译期字节码插桩与监控自动化
chapter: '26.21'
status: ready-for-review
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: '2026-06-26'
last_verified_against: AGP 8.x docs + AOSP android-17.0.0_r1 + ASM 9.x docs
confidence: high
sources:
- type: clipping
  path: Clippings/Android 应用稳定性剖析与优化 - ASM 与字节码插桩：改写字节码的"神器".md
- type: official
  path: https://developer.android.com/reference/tools/gradle-api/8.6/com/android/build/api/instrumentation/AsmClassVisitorFactory
- type: official
  path: https://developer.android.com/build/asm-instrumentation
- type: aosp
  path: frameworks/base/core/java/android/os/Trace.java
- type: aosp
  path: tools/base/build-system/gradle-api/src/main/java/com/android/build/api/instrumentation/
tags:
- asm
- bytecode
- instrumentation
- agp
- apm
- monitoring
- compile-time
related_chapters:
- '20.2'
- '20.7'
- '20.14'
- '26.3'
- '14.26'
- '19.2'
- '19.18'
- '19.22'
drafted_date: '2026-06-26'
created_by: task2a-knowledge-gap
created_date: '2026-06-26'
gap_source: 素材驱动/参考书
---

# 26.21 编译期字节码插桩与监控自动化

字节码插桩适合解决“规则明确、调用点很多、人工埋点容易遗漏”的问题，例如给一组业务入口加 trace、把已有 API 调用改写到监控桥接层，或检查某类调用是否符合约束。它不能自动获得所有性能问题的因果关系，也不适合修改 Android framework、ART 或任意第三方库的内部实现。

平台语义以 Android 17 / API 37 / `android-17.0.0_r1` 为准，构建入口以 AGP 8.x Instrumentation API 为准。Android 17 没有改变 App 构建期 `.class` 插桩的基本边界；运行时证据仍来自公开 Trace API、Perfetto、JankStats、网络库接口和业务指标。

## 先确定插桩边界

一条可维护的监控链路包含四层：

| 层级 | 责任 | 常见错误 |
|---|---|---|
| 选择规则 | 决定哪些 variant、class、method 需要处理 | Release 无条件全量插桩，或误改生成代码与依赖 |
| 字节码变换 | 保证控制流、操作数栈、局部变量和 frame 合法 | 只处理正常 `return`，异常路径没有清理 |
| 运行时桥接 | 采样、限流、隐私处理并写入 Trace/APM | 在热路径分配对象、同步 I/O 或递归调用 |
| 验证与发布 | 校验 class、D8/R8 产物、运行时 trace 和成本 | 只看编译成功，没有检查优化后产物 |

“无业务手写埋点”不等于“零侵入”。每条注入指令都会改变 class、构建时间和运行路径。是否启用、覆盖哪些方法以及容许多少成本，都应由当前工程的测量结果决定。

## ASM Core API 与 Tree API

ASM Core API 以 visitor 回调读取 class。`ClassVisitor` 处理类级结构，`MethodVisitor` 逐条接收方法指令。它适合局部、流式的变换，通常不需要把整个类表示保存在内存中。

Tree API 把类读入 `ClassNode`，方法指令保存在 `InsnList`。需要多次遍历同一方法、重排较长指令序列或进行控制流分析时，Tree API 更容易编写；代价是额外内存和对象分配。

选择依据来自变换本身：

- 入口、出口、调用点替换等局部操作优先使用 Core API。
- 需要查看一个方法的完整指令、异常表和跳转关系时考虑 Tree API。
- 需要全程序调用图、跨类数据流或统一改写 jar 时，单 class Instrumentation API 不够，应使用 AGP Scoped Artifacts 注册独立 task。

ASM 操作的是 JVM class，不是 DEX。Kotlin 编译器、KSP、Compose Compiler 等前置步骤先生成 class，AGP 插桩随后处理；D8/R8 再对结果做 desugar、压缩、优化、混淆和 dex 转换。

## AGP 8.x 的插桩入口

### Transform API 已被移除

旧的 `com.android.build.api.transform.Transform` 在 AGP 7.2 被废弃，并从 AGP 8.0 移除。官方的 [AGP API 更新说明](https://developer.android.com/build/releases/gradle-plugin-api-updates)没有提供一个覆盖所有旧用法的单一替代物：

- 独立处理每个 class：使用 `variant.instrumentation.transformClassesWith()`。
- 读取或变换整个 class 集合：使用 `variant.artifacts.forScope()` 和 `ScopedArtifact.CLASSES`。
- 增加生成 class：向 `MultipleArtifact.ALL_CLASSES_DIRS` 追加产物。

Instrumentation API 能按 class 增量处理，并允许 AGP 并行准备不同依赖。代价是 visitor 只拥有有限的 classpath 视图，不能假设所有 class 已经完成其他 visitor 的变换。

### 注册 AsmClassVisitorFactory

下面的 Kotlin 代码用于把 factory 注册到 release variant，并让 AGP 为被修改的方法重新计算 stack frame。示例使用 `PROJECT`，只处理当前 Android 模块的 class。

```kotlin
import com.android.build.api.instrumentation.FramesComputationMode
import com.android.build.api.instrumentation.InstrumentationScope
import com.android.build.api.variant.ApplicationAndroidComponentsExtension
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.kotlin.dsl.getByType

class TraceInstrumentationPlugin : Plugin<Project> {
    override fun apply(project: Project) {
        project.pluginManager.withPlugin("com.android.application") {
            val androidComponents =
                project.extensions.getByType<ApplicationAndroidComponentsExtension>()

            androidComponents.onVariants(
                androidComponents.selector().withBuildType("release")
            ) { variant ->
                variant.instrumentation.transformClassesWith(
                    TraceClassVisitorFactory::class.java,
                    InstrumentationScope.PROJECT
                ) { params ->
                    params.packagePrefixes.set(listOf("com.example.app"))
                }

                variant.instrumentation.setAsmFramesComputationMode(
                    FramesComputationMode.COMPUTE_FRAMES_FOR_INSTRUMENTED_METHODS
                )
            }
        }
    }
}
```

这段代码只展示注册关系。工程应把包前缀和启用 variant 暴露为插件扩展，而不是把示例值复制到多个模块。`COMPUTE_FRAMES_FOR_INSTRUMENTED_METHODS` 适合给既有方法增加控制流；如果 visitor 只加注解或能够自行维护 frame，`COPY_FRAMES` 的构建成本更低。`COMPUTE_FRAMES_FOR_ALL_CLASSES` 会产生非增量的全类计算，只有改变继承关系等特殊变换才应考虑。

`InstrumentationScope` 还受模块类型约束。应用和测试模块可选择 `PROJECT` 或 `ALL`；Android library 只能对本项目 class 注册 Instrumentation。`ALL` 会处理传递依赖，可能重复修改已插桩库，也会把第三方版本差异纳入兼容范围，因此不应当成默认值。

### Factory 必须支持异步调用

AGP 的 [`AsmClassVisitorFactory`](https://developer.android.com/reference/tools/gradle-api/8.6/com/android/build/api/instrumentation/AsmClassVisitorFactory)明确要求 `isInstrumentable()` 和 `createClassVisitor()` 能被异步调用。factory 不应使用可变全局集合统计访问结果，也不应在回调中读写共享文件。

下面的代码用于声明可缓存的输入参数、过滤生成类，并把 AGP 提供的 ASM API 版本交给 visitor。

```kotlin
import com.android.build.api.instrumentation.AsmClassVisitorFactory
import com.android.build.api.instrumentation.ClassContext
import com.android.build.api.instrumentation.ClassData
import com.android.build.api.instrumentation.InstrumentationParameters
import org.gradle.api.provider.ListProperty
import org.gradle.api.tasks.Input
import org.objectweb.asm.ClassVisitor

interface TraceParameters : InstrumentationParameters {
    @get:Input
    val packagePrefixes: ListProperty<String>
}

abstract class TraceClassVisitorFactory :
    AsmClassVisitorFactory<TraceParameters> {

    override fun isInstrumentable(classData: ClassData): Boolean {
        val className = classData.className
        val simpleName = className.substringAfterLast('.')
        val inConfiguredPackage = parameters.get().packagePrefixes.get()
            .any { prefix ->
                className == prefix || className.startsWith("$prefix.")
            }

        return inConfiguredPackage &&
            simpleName != "R" &&
            !simpleName.startsWith("R\$") &&
            simpleName != "BuildConfig"
    }

    override fun createClassVisitor(
        classContext: ClassContext,
        nextClassVisitor: ClassVisitor
    ): ClassVisitor {
        return TraceClassVisitor(
            api = instrumentationContext.apiVersion.get(),
            next = nextClassVisitor
        )
    }
}
```

`ClassData.className` 使用点分隔的全限定类名。过滤逻辑需要覆盖 `R` 的内部类，并根据工程情况排除 generated、data binding、Hilt、Compose synthetic、监控 SDK 自身等代码。参数必须通过 Gradle `Property`、`ListProperty`、`RegularFileProperty` 等声明输入；回调中临时读取未声明的 YAML 或 JSON 会破坏 up-to-date 与 build cache 判断。

## 方法 trace 的控制流必须完整

### 为什么只检查 RETURN 和 ATHROW 不够

在每个 `RETURN` 和 `ATHROW` 前插入 `Trace.endSection()`，只能覆盖显式出现在当前方法字节码中的退出指令。下面这种 Java 代码没有本地 `ATHROW` 也可能异常退出：

`repository.load()` 抛出的异常可以直接沿调用栈传播，当前方法会在 `INVOKEVIRTUAL` 处离开。visitor 若只观察退出 opcode，`Trace.beginSection()` 就不会配对，后续同线程的嵌套 section 也会错位。

稳妥做法是给原方法体增加一个 catch-all handler，语义等价于 `try/finally`：正常返回前调用 `endSection()`；任何传播到方法边界的 `Throwable` 由 handler 调用 `endSection()` 后原样抛出。构造方法要等到父类构造调用完成后才能执行通用入口 advice，ASM `AdviceAdapter` 已处理这一限制。

下面的 visitor 用于演示这一控制流。它跳过抽象、native、synthetic 方法以及构造器，避免示例同时引入构造器语义和编译器生成方法。

```kotlin
import org.objectweb.asm.ClassVisitor
import org.objectweb.asm.Label
import org.objectweb.asm.MethodVisitor
import org.objectweb.asm.Opcodes
import org.objectweb.asm.Type
import org.objectweb.asm.commons.AdviceAdapter
import org.objectweb.asm.commons.Method
import java.nio.charset.StandardCharsets
import java.security.MessageDigest

class TraceClassVisitor(
    api: Int,
    next: ClassVisitor
) : ClassVisitor(api, next) {
    private var ownerInternalName: String = ""

    override fun visit(
        version: Int,
        access: Int,
        name: String,
        signature: String?,
        superName: String?,
        interfaces: Array<out String>?
    ) {
        ownerInternalName = name
        super.visit(version, access, name, signature, superName, interfaces)
    }

    override fun visitMethod(
        access: Int,
        name: String,
        descriptor: String,
        signature: String?,
        exceptions: Array<out String>?
    ): MethodVisitor {
        val next = super.visitMethod(
            access, name, descriptor, signature, exceptions
        )
        val unsupported = access and (
            Opcodes.ACC_ABSTRACT or
                Opcodes.ACC_NATIVE or
                Opcodes.ACC_SYNTHETIC
            ) != 0

        if (unsupported || name == "<init>" || name == "<clinit>") {
            return next
        }

        return TraceMethodVisitor(
            api = api,
            next = next,
            access = access,
            name = name,
            descriptor = descriptor,
            traceTag = buildTraceTag(ownerInternalName, name, descriptor)
        )
    }
}

private class TraceMethodVisitor(
    api: Int,
    next: MethodVisitor,
    access: Int,
    name: String,
    descriptor: String,
    private val traceTag: String
) : AdviceAdapter(api, next, access, name, descriptor) {
    private val bodyStart = Label()
    private val bodyEnd = Label()

    override fun onMethodEnter() {
        visitLdcInsn(traceTag)
        invokeStatic(TRACE_TYPE, BEGIN_SECTION)
        visitLabel(bodyStart)
    }

    override fun onMethodExit(opcode: Int) {
        if (opcode != ATHROW) {
            invokeStatic(TRACE_TYPE, END_SECTION)
        }
    }

    override fun visitMaxs(maxStack: Int, maxLocals: Int) {
        val handler = Label()
        visitTryCatchBlock(bodyStart, bodyEnd, handler, null)
        visitLabel(bodyEnd)
        visitLabel(handler)
        invokeStatic(TRACE_TYPE, END_SECTION)
        throwException()
        super.visitMaxs(maxStack, maxLocals)
    }

    companion object {
        private val TRACE_TYPE = Type.getObjectType("android/os/Trace")
        private val BEGIN_SECTION =
            Method("beginSection", "(Ljava/lang/String;)V")
        private val END_SECTION = Method("endSection", "()V")
    }
}

private fun buildTraceTag(
    ownerInternalName: String,
    methodName: String,
    descriptor: String
): String {
    val key = "$ownerInternalName#$methodName$descriptor"
    val digest = MessageDigest.getInstance("SHA-256")
        .digest(key.toByteArray(StandardCharsets.UTF_8))
        .take(6)
        .joinToString("") { "%02x".format(it) }
    val readable = "${ownerInternalName.substringAfterLast('/')}#$methodName"
        .replace('|', ' ')
        .replace('\n', ' ')
        .replace('\u0000', ' ')
    return "${readable.takeUtf16Safely(110)}@$digest"
}

private fun String.takeUtf16Safely(maxCodeUnits: Int): String {
    if (length <= maxCodeUnits) return this
    val end = if (
        Character.isHighSurrogate(this[maxCodeUnits - 1]) &&
        Character.isLowSurrogate(this[maxCodeUnits])
    ) {
        maxCodeUnits - 1
    } else {
        maxCodeUnits
    }
    return substring(0, end)
}
```

正常返回路径由 `onMethodExit()` 写入 `endSection()`；显式与隐式异常由新增 handler 处理，所以同一个异常不会结束两次。`visitMaxs()` 增加了异常边，注册阶段必须选择能重新计算 frame 的模式。生产 visitor 还要根据注解、方法大小、访问标志和业务规则缩小范围，并为 tag 截断、多字节标识符和哈希冲突编写测试。

Android 17 的 [`android.os.Trace`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Trace.java)与公开 [Trace API](https://developer.android.com/reference/android/os/Trace)规定：同步 section 必须在同一线程成对并正确嵌套，名称上限为 127 个 UTF-16 code unit。竖线、换行和空字符会被替换。示例在构建期生成固定 tag，避免每次调用时拼接字符串。若 tag 包含业务参数、URL、账号或内容摘要，trace 文件也会携带这些信息，因此只应使用低敏感度的稳定标识。

`Trace.isEnabled()` 从 API 29 提供。固定字符串的 `beginSection()` 可以直接调用，因为平台内部会检查 tracing 状态；只有运行时需要构造临时对象或格式化字符串时，才值得先调用 `isEnabled()` 避免无效分配。

## 选择性插桩比全量插桩更可靠

方法数量不能直接决定开销。成本还与调用频率、tag 构造、采样逻辑、R8 优化结果、CPU 和是否正在采集 trace 有关。文章不应给出通用的“每方法增加多少字节”或“每次调用多少微秒”。

可用的筛选维度包括：

- variant：开发、性能测试、灰度和生产可采用不同规则；
- 模块与包：默认只处理自有代码，依赖库必须逐版本验证；
- 类与方法：注解、接口、访问标志和稳定签名共同决定；
- 热度：循环体、高频 getter、Compose 编译器生成方法和协程状态机应谨慎；
- 采样：运行时桥接可按会话、场景或设备分群启用，但不能改变 begin/end 配对；
- 预算：用本项目的 clean build、增量 build、APK/Dex 和基准测试建立门禁。

注解只用于构建期选择时，`Retention.BINARY`/Java `RetentionPolicy.CLASS` 足够。ASM 在 R8 前读取注解，运行时无需保留。只有运行时代码仍通过反射读取注解时，才需要对应的 `-keepattributes` 与成员规则。

## 与 R8 的关系

AGP Instrumentation 产生的 class 会继续进入 D8/R8。需要区分三类情况：

- 注入的是直接方法调用：R8 能看到引用链，通常不需要为桥接类添加全包 `-keep`。
- 桥接类通过反射或 JNI 名称查找：R8 无法从普通调用图推导目标，需要精确的 keep 规则。
- 监控要求与源码方法一一对应：R8 的内联、合并、删除和 outlining 会改变最终执行形态，必须在 minified release 产物上验证 trace，而不能只检查未优化 class。

若 trace tag 保存插桩前的类名，它可以帮助阅读源码，但也可能暴露内部命名。另一种方案是使用稳定 method ID，并随构建产出一份受控的 ID 到源码符号映射。崩溃栈仍使用 R8 `mapping.txt` 还原，两种映射不要混为一种文件。

不要为了保留 trace 结构而对整包禁用优化。更合适的顺序是缩小插桩范围、确认关键方法在 release 中的形态，再为确有需要的少量边界设置规则。

## 网络监控：优先使用稳定扩展点

OkHttp 已提供 application interceptor、network interceptor 和 `EventListener`。能在依赖注入或 client factory 中统一配置时，应使用这些公开扩展点。字节码插桩适合补齐无法统一管理的自有调用点，例如把特定构造或 factory 调用改写到一个版本化桥接方法。

直接修改 `OkHttpClient.Builder` 的私有字段或重写依赖 jar 内部 `build()` 有几项风险：

- 字段名、可见性、Kotlin 实现和构造流程不是稳定兼容协议；
- `InstrumentationScope.ALL` 可能对同一依赖重复处理；
- 多个插件可能改变 visitor 顺序，导致重复 interceptor；
- shaded、不同主版本和厂商分支的 owner/descriptor 不一致；
- 监控 interceptor 自己发请求时可能形成递归。

调用点变换必须同时匹配 owner、方法名和 descriptor，并在不支持的库版本上停止变换或给出构建错误。桥接层要保留请求成功、失败、取消和重试的语义，不采集授权头、Cookie、请求体、完整 URL 查询参数等敏感数据。

`HttpURLConnection` 也不应依赖“某 Android 版本默认切换到 Cronet”之类假设。App 构建期 visitor 无法修改 boot classpath 中的 `URL` 或 framework 实现；包装返回对象还可能破坏调用方的具体类型转换。若工程仍使用 `HttpURLConnection`，优先在自有网络抽象层计时，或只改写已经验证的自有调用点。

## 帧与主线程监控：不要修改 framework class

`Choreographer`、`ActivityThread` 和 `Looper` 属于 Android framework。普通 App 的 AGP 插桩只处理 App 与所选依赖的 class，不能改写设备上的 boot classpath。运行时反射或 ART hook 也会受隐藏 API、版本差异和完整性策略影响，不应作为常规线上方案。

帧问题优先使用：

- [JankStats](https://developer.android.com/topic/performance/jankstats)：按 `Window` 提供帧时长、jank 判断和 App UI state；
- `FrameMetrics` / `FrameMetricsAggregator`：面向 View 窗口的帧阶段数据；
- Macrobenchmark 与 Perfetto：在可重复场景中分析 UI thread、RenderThread、SurfaceFlinger 和调度；
- Android vitals：观察用户侧 slow session 与 jank 分布。

刷新率可能动态变化，不能固定以 16.6 ms 判断所有设备和场景。字节码插桩在这里更适合给自有的列表绑定、图片解码、状态更新或业务事务加稳定 trace，用时间关系帮助定位慢帧附近执行了什么。

`Looper.setMessageLogging()` 是公开 API，但一个 Looper 只有一个当前 `Printer`；后设置者会替换先设置者。它还处于消息分发热路径。若需要使用，应由统一初始化组件协调，并把回调工作限制为轻量记录。为初始化一项监控而修改 `Application.onCreate()` 字节码通常不如显式 App Startup initializer 清晰。

## Kotlin、协程与 Compose 的特殊形态

Kotlin 默认参数、inline、suspend、lambda 和 synthetic accessor 会产生与源码不同的方法。协程函数的主要执行逻辑可能位于生成的 `ContinuationImpl.invokeSuspend()`，一次源码调用也可能跨线程恢复多次。仅按源码函数名插入同步 `Trace.beginSection()` 不能表达跨线程生命周期。

协程需要异步 trace 或支持 context propagation 的 tracing API，并为并发实例分配不会冲突的 cookie/flow 标识。同步 section 只描述当前线程上的一段执行。

Compose Compiler 会改变 `@Composable` 函数签名并生成重组相关代码。基于生成参数或内部方法名的 ASM 规则会随 Compose/Kotlin 版本变化。Composition tracing 已有官方 [`androidx.compose.runtime:runtime-tracing`](https://developer.android.com/develop/ui/compose/tooling/tracing)支持；UI 卡顿仍结合 JankStats、Macrobenchmark 与 Perfetto。只有公开工具无法覆盖且受支持版本集合可控时，才考虑对 Compose 产物做专项 visitor。

## 多模块与依赖范围

Instrumentation 注册在每个 Android 模块的 variant 上。根工程插件可以统一应用配置，但仍需对 application、library、dynamic feature 和 test 模块分别注册适配的 Android Components 扩展。

推荐的范围策略是：

- 自有 library 使用 `PROJECT`，在 AAR 生成前处理该模块 class；
- application 默认使用 `PROJECT`，避免再次处理已插桩 library；
- dynamic feature 单独应用同一插件，确保规则版本一致；
- 只有明确要修改未插桩依赖时，application 才使用 `ALL`，并设置依赖坐标、class 和方法签名白名单；
- 跨类全局分析使用 Scoped Artifacts 独立 task，接受它比逐 class visitor 更高的构建成本。

插件版本、规则版本、AGP 版本和 ASM API 版本都应写入构建产物或诊断信息。多插件共同处理 class 时，还要用集成测试固定注册顺序和最终结果。

## 验证一套插桩规则

### class 级测试

给 visitor 准备包含正常返回、多个 return、显式 throw、被调用方法抛异常、try/catch/finally、synchronized、宽类型返回值和大方法的 fixture。验证项包括：

- `CheckClassAdapter` 不报告 verifier 问题；
- class 可由隔离 ClassLoader 加载和执行；
- 正常与异常路径的 begin/end 数量相等；
- 原返回值、异常类型、异常 cause 和 suppressed 信息不变；
- 已插桩输入再次经过插件时不会重复注入。

`ClassWriter.COMPUTE_FRAMES` 能修正 frame，不能证明业务语义没有改变。测试仍需执行变换后的 class。

### Android 构建集成测试

用 Gradle TestKit 或样例工程覆盖 clean、incremental、configuration cache、build cache、不同 variant、多模块和 dependency scope。随后构建 minified release，让 D8/R8、desugar 与 dex verifier 参与验证。

产物检查至少包含：

- APK/AAB 与各 dex 的大小变化；
- mapping、seeds/usage 和插桩 ID 映射是否随构建归档；
- 目标调用是否存在，排除类是否未被修改；
- Debug 与 Release 的启用规则是否符合配置；
- 依赖升级或 AGP 升级后 owner/descriptor 是否仍匹配。

### 设备与性能验证

在 Android 8 到 Android 17 的代表设备或模拟器上运行关键场景，采集 Perfetto 并检查 section 嵌套、线程、异常退出和 R8 后名称。构建时间、启动、帧、CPU、分配、包体积和上报量使用同一工程的启用/禁用 A/B 结果评估。

门禁阈值来自该工程的基线分布，不使用文章中的固定百分比。样本还要记录设备、系统、编译模式、温度、场景和 trace 是否启用，否则不同实验不能直接比较。

## 运行时桥接的安全要求

插桩代码只负责调用一个窄接口，复杂策略留在版本化桥接层。桥接层应满足：

- 可快速关闭，失败时不阻塞业务；
- 不在主线程执行文件或网络 I/O；
- 不记录密钥、token、正文、完整 URL 或用户输入；
- 有递归保护，监控 SDK 自身不再触发同类监控；
- 处理采样、缓冲上限、背压和进程退出；
- 事件包含 schema、插件、规则、App 和 Android 版本；
- 监控异常独立计数，不用吞掉业务异常来维持上报。

Android trace 通常用于短时诊断，不应把每个方法的原始事件长期上传。线上需要聚合时，优先保存场景级耗时、计数、分位数和低基数状态；罕见问题再通过 Android 17 的受控 profiling 能力获取更完整证据。

## Android 17 验收清单

- 构建插件使用 `variant.instrumentation`，没有引用已移除的 Transform API。
- factory 无共享可变状态，所有配置都声明为 Gradle 输入。
- 默认 scope 为自有 class；处理第三方依赖时有坐标和签名白名单。
- visitor 覆盖隐式异常退出，且 begin/end 在同一线程正确嵌套。
- 新增控制流后选择合适的 frame computation mode。
- trace tag 不超过公开 API 限制，不包含用户或业务敏感数据。
- 过滤抽象、native、生成类、监控 SDK 自身和不适合处理的热方法。
- 网络监控优先使用客户端公开扩展点，不修改 framework 或依赖私有字段。
- 帧监控使用 JankStats、FrameMetrics、Macrobenchmark 与 Perfetto，不注入 `Choreographer` 或 `ActivityThread`。
- Kotlin 协程与 Compose 使用符合其执行模型的 tracing 方案。
- class fixture、Gradle 集成、minified release 和 Android 设备测试均通过。
- 成本门禁基于当前工程实测，保留可关闭开关和规则版本。

编译期字节码插桩的优势是可重复、可审计和可在发布前验证。把变换范围、控制流正确性、R8 后产物、运行时成本与数据隐私同时纳入设计，监控自动化才不会成为新的稳定性来源。
