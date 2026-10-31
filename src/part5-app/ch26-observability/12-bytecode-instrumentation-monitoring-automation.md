---
title: 编译期字节码插桩与监控自动化
chapter: '26.12'
section: '26.12'
status: finalized
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: '2026-10-25'
last_source_verified_at: '2026-10-25'
last_verified_against: fixed AGP 9.3.3 API baseline including POST_COMPILATION_CLASSES; current metadata (latest stable 9.4.1), ASM 9.11.1 and visitor contracts; android-17.0.0_r1 Trace and current official UI/profiling docs; reviewed 2026-10-25 with host JVM visitor fixture verification only
confidence: high
sources:
- type: legacy-reference-preserved
  path: Clippings/Android 应用稳定性剖析与优化 - ASM 与字节码插桩：改写字节码的"神器".md
- type: official
  path: https://developer.android.com/build/releases/agp-9-3-0-release-notes
- type: official
  path: https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/maven-metadata.xml
- type: official
  path: https://developer.android.com/build/releases/gradle-plugin-api-updates
- type: official
  path: https://developer.android.com/reference/tools/gradle-api/8.6/com/android/build/api/instrumentation/AsmClassVisitorFactory
- type: official
  path: https://developer.android.com/reference/tools/gradle-api/9.3/com/android/build/api/instrumentation/AsmClassVisitorFactory
- type: official
  path: https://developer.android.com/reference/tools/gradle-api/9.3/com/android/build/api/instrumentation/InstrumentationScope
- type: official
  path: https://developer.android.com/reference/tools/gradle-api/9.3/com/android/build/api/artifact/ScopedArtifact.CLASSES
- type: official
  path: https://developer.android.com/reference/tools/gradle-api/9.3/com/android/build/api/artifact/ScopedArtifact.POST_COMPILATION_CLASSES
- type: upstream
  path: https://asm.ow2.io/versions.html
- type: legacy-reference-preserved
  path: https://developer.android.com/build/asm-instrumentation
- type: legacy-reference-preserved
  path: frameworks/base/core/java/android/os/Trace.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Trace.java
- type: official
  path: https://developer.android.com/reference/android/os/Trace
- type: official
  path: https://developer.android.com/topic/performance/jankstats
- type: official
  path: https://developer.android.com/develop/ui/compose/tooling/tracing
- type: official
  path: https://developer.android.com/reference/android/os/ProfilingManager
- type: legacy-reference-preserved
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
- '15.10'
- '17.2'
- '22.10'
- '15.7'
- '17.7'
- '17.11'
- '20.2'
- '26.1'
last_draft_polish_at: '2026-08-15T22:34:03+08:00'
last_review_finalize_at: '2026-08-15T22:34:03+08:00'
last_rework_at: '2026-08-15T22:34:03+08:00'
---

# 编译期字节码插桩与监控自动化

字节码插桩（bytecode instrumentation）是在源码编译成 JVM `.class` 之后、生成 DEX 之前自动检查或改写指令。它适合处理“规则明确、调用点很多、人工埋点容易遗漏”的任务，例如给一组业务入口加 trace（按时间记录代码区间的跟踪片段）、把已有 API 调用改写到监控桥接层，或检查某类调用是否符合约束。

它的适用范围很清楚：能改写的只有进入当前 App 构建流程的 class；Android framework（随系统镜像发布的 Java/Kotlin 框架代码）、ART（`Android Runtime`，负责执行 DEX 并管理应用运行）和任意第三方库的内部实现，都不适合作为插桩对象；性能问题的因果关系要靠运行时数据推导。

> 源码基线：AOSP `android-17.0.0_r1`；平台语义以 Android 17 / API 37 为准。

AGP（Android Gradle Plugin）是把 Android 模块接入 Gradle 构建流程的插件。本文固定AGP9.3.3的Instrumentation API基线，以覆盖本页使用的POST_COMPILATION_CLASSES。2026年10月25日metadata中最新无预览后缀的稳定版是9.4.1，release标签则可能指向9.6.0-alpha01，生产稳定版的选择应以metadata为准。本文9.3系列支持最高API37，要求Gradle9.5.0和JDK17；升级版本应另核兼容表。

Android 17 没有改变 App 构建期 `.class` 插桩的基本边界。运行时证据仍来自公开 Trace API、Perfetto（系统级跟踪的采集与分析工具）、JankStats、网络库接口和业务指标。

## 先确定插桩边界

一套可维护的插桩监控方案分为四层：选择规则、字节码变换、运行时桥接、验证与发布。四层各自负责一段职责，也各有典型的出错方式；这张表也是后面各节的路线图。

| 层级 | 责任 | 常见错误 |
|---|---|---|
| 选择规则 | 决定哪些 variant、class、method 需要处理 | Release 无条件全量插桩，或误改生成代码与依赖 |
| 字节码变换 | 保证控制流、操作数栈、局部变量和 frame 合法 | 只处理正常 `return`，异常路径没有清理 |
| 运行时桥接 | 采样、限流、隐私处理并写入 Trace/APM | 在热路径分配对象、同步 I/O 或递归调用 |
| 验证与发布 | 校验 class、D8/R8 产物、运行时 trace 和成本 | 只看编译成功，没有检查优化后产物 |

表里的术语先约定：variant 指由构建类型、产品风味等配置组合出的构建变体；stack frame 是 JVM verifier（字节码验证器）用来核对操作数栈和局部变量类型的校验信息。

表里还有两个监控侧的词：APM（Application Performance Monitoring）指应用性能监控；热路径指调用频繁的代码路径，少量额外工作也可能累积成明显开销。

“无业务手写埋点”仍会带来侵入：每条注入指令都会改变 class、构建时间和运行路径。所以是否启用、覆盖哪些方法、容许多少成本，都交给当前工程的测量结果来决定。


## ASM Core API 与 Tree API

ASM 是一个直接读写 JVM class 的字节码库。Core API 采用 visitor（访问器）回调：`ClassVisitor` 接收类级结构，`MethodVisitor` 依次接收方法指令；它适合局部、流式的变换，通常无需把整个类的表示保存在内存中。

Tree API 走另一条路：把类读入 `ClassNode`，方法指令保存在 `InsnList`。需要多次遍历同一方法、重排较长指令序列或分析控制流时，它更容易编写，代价是更多内存和对象分配。

两套 API 怎么选？依据来自变换本身：

- 入口、出口、调用点替换等局部操作优先使用 Core API。
- 需要查看一个方法的完整指令、异常表和跳转关系时考虑 Tree API。
- 需要全程序调用图、跨类数据流或统一改写 jar 时，逐 class 的 Instrumentation API 看不到这么宽的视野，应通过 AGP Scoped Artifacts（按当前模块或连同依赖取得整组构建产物的 API）注册独立 task。

### ASM 在构建流程中的位置

放到构建流程里看，ASM 的输入是 JVM class，DEX 在后续阶段产生：Kotlin 编译器、KSP（Kotlin Symbol Processing，在编译期间读取程序符号并生成代码）、Compose Compiler 等前置步骤先生成 class，AGP 插桩随后处理。

再往后是 D8/R8：执行 desugar（把较新的 Java 字节码特性转换成旧 Android 版本可执行的形式）、压缩、优化、混淆和 DEX 转换。R8 是 Android 的代码压缩与优化器，D8 则负责把 JVM 字节码转换为 DEX。


## AGP 9.3.3 的插桩入口

Instrumentation API 是 AGP 为逐 class 注册 ASM visitor 的公开接口。它支持增量处理，也允许 AGP 并行准备不同依赖。visitor 只能看到有限的 classpath（编译当前 class 时可查询的类集合）；至于某个 class 是否已被其他 visitor 变换过，这里没有任何保证，两种情况都要当作输入。

### Transform API 已被移除

旧的 `com.android.build.api.transform.Transform` 在 AGP 7.2 被废弃，并从 AGP 8.0 移除。官方的 [AGP API 更新说明](https://developer.android.com/build/releases/gradle-plugin-api-updates)没有给出一个覆盖所有旧用法的单一替代物，迁移入口取决于任务目标，我们分三条看：

- 独立处理每个 class：使用 `variant.instrumentation.transformClassesWith()`。
- 读取或变换整组 class：使用 `variant.artifacts.forScope()` 和 [`ScopedArtifact.CLASSES`](https://developer.android.com/reference/tools/gradle-api/9.3/com/android/build/api/artifact/ScopedArtifact.CLASSES)。
- 在编译后生成新 class 且还要读取已编译 class：读取 `ScopedArtifact.POST_COMPILATION_CLASSES`，再把生成目录追加到 `ScopedArtifact.CLASSES`，避免任务同时消费和生成同一个产物形成循环依赖。`POST_COMPILATION_CLASSES`在9.3.3才加入且标有 `@Incubating`，使用它的插件应固定 AGP 版本并保留升级集成测试。

### 注册 AsmClassVisitorFactory

下面的 Kotlin 代码把 factory（为每个 class 创建 visitor 的工厂）注册到 release variant，并让 AGP 为被修改的方法重新计算 stack frame。示例使用 `PROJECT`，只处理当前 Android 模块的 class。

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

这段代码只展示注册关系；工程上应把包前缀和启用 variant 暴露为插件扩展，避免把示例值复制到多个模块。scope 与 frame 计算模式怎么选，我们分开说。

`InstrumentationScope` 决定 visitor 处理哪些 class。应用和测试模块可选择 `PROJECT` 或 `ALL`；Android library 的注册范围仅限本项目 class。`ALL` 会处理传递依赖，可能重复修改已插桩库，也会把第三方版本差异纳入兼容范围，所以默认从 `PROJECT` 起步，确有处理传递依赖的需求时再评估 `ALL`。

frame 计算模式跟着变换类型选：`COMPUTE_FRAMES_FOR_INSTRUMENTED_METHODS` 适合给既有方法增加控制流；visitor 只加注解或能自行维护 frame 时，`COPY_FRAMES` 的构建成本更低。`COMPUTE_FRAMES_FOR_ALL_CLASSES` 会触发非增量的全类计算，留给改变继承关系这类特殊变换。


### Factory 回调的异步约束

写 factory 前先记住一条约束：[`AsmClassVisitorFactory`](https://developer.android.com/reference/tools/gradle-api/8.6/com/android/build/api/instrumentation/AsmClassVisitorFactory) 8.6 版本页保留了异步调用要求，当前 AGP 9.3 API 也相同——`isInstrumentable()` 和 `createClassVisitor()` 可能异步调用。

不同 class 的回调还可能并发发生。所以 factory 要保持无共享状态：可变全局集合、回调里读写共享文件都避开，需要全局统计时放到独立的可缓存任务里做。

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

截至2026年10月25日，上游ASM最新版本为9.11.1（10月17日发布）。这个版本号只说明上游进展；写 visitor 时应改用 `instrumentationContext.apiVersion`，服从 AGP 实际内置的 ASM API 版本，避免插件声明的版本高于构建环境。

`ClassData.className` 使用点分隔的全限定类名，过滤逻辑据此匹配。除了包前缀，还要覆盖 `R` 的内部类，并按工程情况排除生成代码、Data Binding、Hilt、Compose synthetic（编译器合成的方法或类）以及监控 SDK 自身。

参数一律通过 Gradle `Property`、`ListProperty`、`RegularFileProperty` 等声明为输入。这样约定的原因在于：回调中临时读取未声明的 YAML 或 JSON，会让 Gradle 判断任务最新状态时出错，也会破坏 `build cache`（跨构建复用任务输出的缓存）命中。


## 方法 trace 的控制流

### 显式退出与隐式退出

给方法加 trace 时，我们最先要处理的是控制流。`RETURN` 和 `ATHROW` 是 JVM 表示“返回”和“抛出异常”的 opcode（操作码），常见的实现是在这些操作码前插入 `Trace.endSection()`——这样覆盖到的，只是显式写在当前方法字节码里的退出指令。

麻烦在于异常会沿调用栈传播。例如 `repository.load()` 抛出的异常，当前方法可能完全没有自己的 `ATHROW`，却仍会在调用指令 `INVOKEVIRTUAL` 处退出。只观察退出 opcode 的 visitor 在这里会漏掉配对：`Trace.beginSection()` 找不到对应的 `endSection()`，后续同线程的嵌套 section 也会跟着错位。

稳妥做法是给原方法体增加 catch-all handler（捕获所有传播到方法边界的 `Throwable` 的异常处理块），语义等价于 `try/finally`：正常返回前调用 `endSection()`；异常路径由 handler 调用 `endSection()` 后原样抛出。

构造器要单独对待：它涉及未初始化this及this()/super()构造链，入口写法照搬普通方法会出错。AdviceAdapter能协助处理入口位置，但捕获所有异常时还必须保留原异常表优先级并遵守visitTryCatchBlock先于相关label的访问契约。

下面的实现采用逐方法MethodNode缓冲：先读取完整指令与原异常表，把catch-all追加为最后一项，再由MethodNode按合法顺序输出。这样同时保留原catch/finally优先级和label访问约束，代价是该方法树的内存。示例跳过abstract、native、synthetic和构造器，并加入不可见版本标记，让同规则的二次处理直接跳过已注入的方法。

<!-- gracker-diagram: a297-05-normal-return-and-propagating-exception -->
![先保留原 catch/finally，最后的 catch-all 才清理逃逸异常](../../assets/diagrams/ch26/a297-05-normal-return-and-propagating-exception.png)

图：方法树输出会先发异常表再发相关label；只处理RETURN/ATHROW不能覆盖调用点隐式异常退出。

```kotlin
import org.objectweb.asm.ClassVisitor
import org.objectweb.asm.MethodVisitor
import org.objectweb.asm.Opcodes
import org.objectweb.asm.tree.AnnotationNode
import org.objectweb.asm.tree.InsnList
import org.objectweb.asm.tree.InsnNode
import org.objectweb.asm.tree.LabelNode
import org.objectweb.asm.tree.LdcInsnNode
import org.objectweb.asm.tree.MethodInsnNode
import org.objectweb.asm.tree.MethodNode
import org.objectweb.asm.tree.TryCatchBlockNode
import java.nio.charset.StandardCharsets
import java.security.MessageDigest

class TraceClassVisitor(api: Int, next: ClassVisitor) : ClassVisitor(api, next) {
    private var ownerInternalName = ""

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
    ): MethodVisitor? {
        val next = super.visitMethod(access, name, descriptor, signature, exceptions)
            ?: return null
        val excluded = access and (
            Opcodes.ACC_ABSTRACT or Opcodes.ACC_NATIVE or Opcodes.ACC_SYNTHETIC
        ) != 0
        if (excluded || name == "<init>" || name == "<clinit>") return next

        val traceTag = buildTraceTag(ownerInternalName, name, descriptor)
        // Buffer one method so existing exception handlers keep their priority.
        return object : MethodNode(api, access, name, descriptor, signature, exceptions) {
            override fun visitEnd() {
                super.visitEnd()
                val marked = invisibleAnnotations.orEmpty().any {
                    it.desc == MARKER_DESCRIPTOR
                }
                if (!marked) instrumentMethod(this, traceTag)
                // MethodNode emits the full exception table before its labels.
                accept(next)
            }
        }
    }

    companion object {
        private const val MARKER_DESCRIPTOR =
            "Lcom/example/monitor/TraceInstrumentedV1;"
        private const val TRACE_OWNER = "android/os/Trace"

        private fun endSection() = MethodInsnNode(
            Opcodes.INVOKESTATIC, TRACE_OWNER, "endSection", "()V", false
        )

        private fun instrumentMethod(method: MethodNode, tag: String) {
            val bodyStart = LabelNode()
            val bodyEnd = LabelNode()
            val handler = LabelNode()
            // Insert cleanup only before normal returns. ATHROW is handled once
            // by the catch-all, including exceptions thrown by callees.
            for (instruction in method.instructions.toArray()) {
                if (instruction.opcode in Opcodes.IRETURN..Opcodes.RETURN) {
                    method.instructions.insertBefore(instruction, endSection())
                }
            }
            method.instructions.insert(InsnList().apply {
                add(LdcInsnNode(tag))
                add(MethodInsnNode(
                    Opcodes.INVOKESTATIC, TRACE_OWNER, "beginSection",
                    "(Ljava/lang/String;)V", false
                ))
                add(bodyStart)
            })
            method.instructions.add(bodyEnd)
            method.instructions.add(handler)
            method.instructions.add(endSection())
            method.instructions.add(InsnNode(Opcodes.ATHROW))
            // Existing handlers stay first; only otherwise-escaping Throwable
            // reaches this last handler.
            method.tryCatchBlocks.add(TryCatchBlockNode(bodyStart, bodyEnd, handler, null))
            val annotations = method.invisibleAnnotations ?: mutableListOf()
            annotations.add(AnnotationNode(MARKER_DESCRIPTOR))
            method.invisibleAnnotations = annotations
        }
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

回看这段代码：正常return前插入endSection；显式与隐式传播异常由排在原异常表之后的catch-all处理；MethodNode先输出异常表再输出label，新增控制流后仍需注册重新计算frame；此例假定Trace调用正常。生产桥接则必须独立隔离自身故障，诊断出错时也要让业务原本的返回或异常原样通过。同步方法的自动monitor获取发生在方法体之前，本例section也不包含那段锁等待。


生产visitor还需按注解、大小、访问标志和业务规则缩小范围。示例V1标记只保证同规则重复处理；规则升级应从未插桩输入重建，或明确拒绝旧标记，避免在新旧标记上累叠。tag截断与UTF-16代理对需要专门测试，短哈希仍可能与别的方法冲突；构建产出的完整ID映射须检查重复ID，不同方法冲突时构建失败或扩展ID。UTF-16 代理对是 Java `String` 用两个 16 位单元表示部分 Unicode 字符的编码方式，截断要在完整字符的边界上切。

配对与嵌套的规则写在平台里：[`android.os.Trace`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Trace.java)与公开 [Trace API](https://developer.android.com/reference/android/os/Trace)规定，同步 section 必须在同一线程成对并正确嵌套，名称上限为 127 个 UTF-16 code unit。code unit 是 Java `String` 的一个 16 位编码单元，它与用户看到的字符数并不总是一一对应。

示例在构建期生成固定 tag，把竖线、换行和空字符提前替换掉，省去每次调用时的字符串拼接。tag 内容要克制：一旦带上业务参数、URL、账号或内容摘要，trace 文件也会原样携带这些信息，所以只用低敏感度的稳定标识。

`Trace.isEnabled()` 从 API 29 提供。固定字符串的 `beginSection()` 可以直接调用，因为平台内部会检查 tracing 状态；只有运行时需要构造临时对象或格式化字符串的场景，才值得先调用 `isEnabled()` 避免无效分配。


## 插桩范围的选择

开销按什么估？方法数量只是一个输入，成本还与调用频率、tag 构造、采样逻辑、R8 优化结果、CPU 和是否正在采集 trace 有关。所以本文不给“每方法增加多少字节”“每次调用多少微秒”这类通用数字，开销由具体工程的测量回答。

可用的筛选维度覆盖构建结构和运行特征：

- variant：开发、性能测试、灰度和生产可采用不同规则；
- 模块与包：默认只处理自有代码，依赖库必须逐版本验证；
- 类与方法：注解、接口、访问标志和稳定签名共同决定；
- 热度：循环体、高频 getter、Compose 编译器生成方法和协程状态机应谨慎；协程状态机是 Kotlin 编译器为保存挂起点和局部变量而生成的 class。
- 采样：运行时桥接可按会话、场景或设备分群启用，begin/end 配对在任何分群下都保持成立；
- 预算：用本项目的 clean build、增量 build、APK/Dex 和基准测试建立门禁。

注解若只用于构建期选择，`Retention.BINARY`/Java `RetentionPolicy.CLASS` 就足够：ASM 在 R8 前读取注解，运行时无需保留。只有运行时代码仍通过反射读取注解时，才需要对应的 `-keepattributes` 与成员规则。

## 与 R8 的关系

AGP Instrumentation 产生的 class 会继续进入 D8/R8。我们按 R8 看见桥接代码的方式分三类：

- 注入的是直接方法调用：R8 能从调用关系找到桥接类，通常无需为整包添加 `-keep`。
- 桥接类通过反射或 JNI（Java/Kotlin 与原生 C/C++ 代码互调的接口）按名称查找：R8 无法从普通调用图推导目标，需要精确的 keep 规则。
- 监控要求与源码方法一一对应：R8 的内联、合并、删除和 outlining 会改变发布产物中的执行形态。outlining 是把多个位置的重复指令抽成共享方法的优化；这类需求要在 minified release（经过压缩和优化的发布构建）上验证 trace，只看未优化 class 会漏掉真实执行形态。

trace tag 的内容在这里也有代价：若保存插桩前的类名，它可以帮助阅读源码，也可能暴露内部命名。另一种方案是使用稳定 method ID，并随构建产出一份受控的“ID 到源码符号”映射。崩溃栈仍使用 R8 `mapping.txt` 还原，两种映射要分开保存和授权。

遇到冲突时的顺序是：先缩小插桩范围，确认关键方法在 release 中的形态，再为确有需要的少量边界设置规则；为保留 trace 结构而对整包禁用优化，等于把顺序走反了。


## 网络监控的扩展点选择

网络监控我们优先看现有的公开扩展点。OkHttp 已提供 application interceptor、network interceptor 和 `EventListener`：interceptor（拦截器）可以在请求执行前后读取或调整请求与响应，`EventListener` 则按 DNS、连接、TLS、请求和响应等阶段报告事件。

能在依赖注入容器或 client factory（统一创建网络客户端的工厂）中集中配置时，用这些扩展点就够了；字节码插桩留给无法统一管理的自有调用点，例如把特定构造或 factory 调用改写到一个版本化桥接方法。

绕开扩展点、直接修改 `OkHttpClient.Builder` 的私有字段或重写依赖 jar 内部 `build()`，风险集中在几处：

- 字段名、可见性、Kotlin 实现和构造流程属于库的内部细节，升级时可能改变；
- `InstrumentationScope.ALL` 可能对同一依赖重复处理；
- 多个插件可能改变 visitor 顺序，导致重复 interceptor；
- shaded 依赖、不同主版本和厂商分支的 owner/descriptor 可能不同；shaded 指库在打包时改写了依赖的包名，owner 是声明方法的类，descriptor 是 JVM 编码的方法参数与返回类型；
- 监控 interceptor 自己发请求时可能形成递归。

这些风险决定了变换的纪律：同时匹配 owner、方法名和 descriptor，只在验证过的库版本上生效，遇到不支持的版本就停止变换或给出构建错误。桥接层要保留请求成功、失败、取消和重试的语义；授权头、Cookie、请求体、完整 URL 查询参数等敏感数据一律排除在采集范围之外。

`HttpURLConnection` 这边同理，“某 Android 版本默认切换到 Cronet”之类的假设靠不住。boot classpath 是系统启动时提供给 App 的核心 framework class 集合，App 构建期 visitor 的处理范围到不了其中的 `URL` 或其他系统实现。

包装返回对象还可能破坏调用方的具体类型转换。若工程仍使用 `HttpURLConnection`，优先在自有网络抽象层计时，或只改写已经验证过的自有调用点。

## 帧与主线程监控的边界

这一节先把对象划分清楚：`Choreographer`、`ActivityThread` 和 `Looper` 属于 Android framework；普通 App 的 AGP 插桩只处理 App 与所选依赖的 class，设备上的 boot classpath 在它的改写范围之外。

运行时反射或 ART hook（在应用运行时替换方法入口）会受隐藏 API、版本差异和完整性策略影响，我们在生产方案里只把它们当非常规手段。

隐藏 API 是系统保留、未向普通 App 承诺兼容性的接口。

那帧问题该怎么监控？优先用现成工具链：

- [JankStats](https://developer.android.com/topic/performance/jankstats)：按Window提供帧时长、库自身的jank启发式判断和App UI状态；该标记不直接等于SurfaceFlinger实际呈现deadline miss；
- `FrameMetrics` / `FrameMetricsAggregator`：面向 View 窗口的帧阶段数据；
- Macrobenchmark 与 Perfetto：Macrobenchmark 会在设备上重复运行用户场景，再分析 UI thread（执行界面逻辑的主线程）、RenderThread、SurfaceFlinger 和系统调度；
- Android vitals：观察用户侧慢会话与 jank 分布。

字节码插桩在这一层的合适位置是业务侧：给自有的列表绑定、图片解码、状态更新或业务事务加稳定 trace，用时间关系帮助定位慢帧附近执行了什么。判断卡顿时还要记得刷新率可能动态变化，16.6 ms 这类固定数字结合设备和场景再用。

`Looper.setMessageLogging()` 是公开 API，用它之前先接受两个限制：一个 Looper 只有一个当前 `Printer`，后设置者会替换先设置者；而且它处于消息分发热路径，也就是每条主线程消息都会经过的高频路径。

真要用的话，由统一初始化组件协调，并把回调工作限制为轻量记录。初始化通常有更清晰的做法：显式声明 App Startup initializer（由 AndroidX Startup 负责调用的初始化器），省得为一项监控去修改 `Application.onCreate()` 字节码。


## Kotlin、协程与 Compose 的特殊形态

插桩规则按源码写，字节码却由编译器生成，这道缝隙在 Kotlin 上最明显：默认参数、`inline`、`suspend`、lambda 和 synthetic accessor 都会产生与源码不同的方法。synthetic accessor 是编译器为访问受可见性限制的成员而生成的辅助方法。

协程把这道缝隙拉得更大：协程函数的主要执行逻辑可能位于生成的 `ContinuationImpl.invokeSuspend()`，一次源码调用也可能跨线程恢复多次。仅按源码函数名插入同步 `Trace.beginSection()`，表达跨线程生命周期是做不到的。

所以要描述跨挂起/跨线程的逻辑协程生命周期，我们改用异步trace或能传播关联信息的tracing API；同步section仍可记录每次物理线程执行片段，只是每个片段各自独立，硬拼成一个连续生命周期会出错。关联信息传播是让同一个标识跟随协程切换线程；并发实例还要分配不会冲突的 cookie 或 flow 标识，用来把不同线程上的开始与结束事件配成一组。

同步 section 只描述当前线程上的一段执行。

<!-- gracker-diagram: a297-10-coroutine-logical-and-thread-segments -->
![协程逻辑生命周期与每次线程执行片段分开记录](../../assets/diagrams/ch26/a297-10-coroutine-logical-and-thread-segments.png)

图：物理方法片段可以同步成对结束；把挂起等待和另一线程恢复包进一个同步section会破坏线程语义。

Compose 面对同样的问题。Compose Compiler 会改变 `@Composable` 函数签名并生成重组相关代码；重组是 Compose 在状态变化后重新执行受影响 UI 代码的过程。基于生成参数或内部方法名的 ASM 规则会随 Compose/Kotlin 版本变化。

Composition tracing 已有官方 [`androidx.compose.runtime:runtime-tracing`](https://developer.android.com/develop/ui/compose/tooling/tracing)支持，UI 卡顿仍结合 JankStats、Macrobenchmark 与 Perfetto 分析。对 Compose 产物做专项 visitor，留给公开工具覆盖不了、且受支持版本集合可控的场景。

## 多模块与依赖范围

Instrumentation 注册在每个 Android 模块的 variant 上。根工程插件可以统一应用配置，但 application、library、dynamic feature 和 test 模块仍要分别注册适配的 Android Components 扩展。

其中 dynamic feature 容易漏：它是按需交付、独立编译的动态功能模块，不会自动继承 application 模块上的 visitor。

范围策略上，建议从最小范围开始：

- 自有 library 使用 `PROJECT`，在 AAR（Android 库归档）生成前处理该模块 class；
- application 默认使用 `PROJECT`，避免再次处理已插桩 library；
- dynamic feature 单独应用同一插件，确保规则版本一致；
- 只有明确要修改未插桩依赖时，application 才使用 `ALL`，并设置依赖坐标、class 和方法签名白名单；
- 跨类全局分析使用 Scoped Artifacts 独立 task，并为它比逐 class visitor 更高的构建成本预留预算。

插件版本、规则版本、AGP 版本和 ASM API 版本都应写入构建产物或诊断信息。多插件共同处理 class 时，注册顺序和最终结果也要用集成测试固定下来。


## 验证一套插桩规则

规则写完只是一半；验证从 class 字节码一路做到设备性能数据，我们按三层展开。

### class 级测试

class 级测试先给 visitor 准备足够的 fixture。fixture 是内容固定、用于重复测试某条变换规则的样例 class，形态上要覆盖正常返回、多个 return、显式 throw、被调用方法抛异常、try/catch/finally、synchronized、宽类型返回值和大方法。验证项包括：

- `CheckClassAdapter` 不报告 verifier 问题；verifier 是 JVM/Android 运行时在执行前检查字节码类型与控制流是否合法的验证器；
- class 可由隔离 ClassLoader 加载和执行；ClassLoader 是把 class 字节定义成运行时类的加载器，隔离加载可避免测试进程中已有同名类干扰；
- 正常与异常路径的 begin/end 数量相等；
- 原返回值、异常类型、异常 cause（原因异常）和 suppressed（随主异常保留的附加异常）信息不变；
- 已插桩输入再次经过插件时不会重复注入。

`ClassWriter.COMPUTE_FRAMES` 能修正 frame，也仅止于 frame；业务语义要靠执行变换后的 class 来回答。

### Android 构建集成测试

构建这一层用 Gradle TestKit 或样例工程，覆盖 clean build（不复用旧产物的完整构建）、incremental build（只重做受改动影响部分的增量构建）、`configuration cache`（复用 Gradle 配置阶段结果）、`build cache`、不同 variant、多模块和依赖范围。

随后构建 minified release，让 D8/R8、desugar 与 DEX verifier 参与验证。

产物检查至少包含：

- APK/AAB（安装包与 Android App Bundle）和各 DEX 的大小变化；
- R8 `mapping.txt`（混淆名称映射）、seeds/usage（保留项与删除项报告）和插桩 ID 映射是否随构建归档；
- 目标调用是否存在，排除类是否未被修改；
- Debug 与 Release 的启用规则是否符合配置；
- 依赖升级或 AGP 升级后，owner/descriptor 是否仍匹配。

### 设备与性能验证

在 Android 8 到 Android 17 的代表设备或模拟器上运行关键场景，采集 Perfetto 并检查 section 嵌套、线程、异常退出和 R8 后名称。

构建时间、启动、帧、CPU、分配、包体积和上报量使用同一工程的启用/禁用 A/B 结果评估。这里的 A/B 指只改变“是否启用插桩”这一项条件，然后比较两组结果。

门禁阈值来自该工程的基线分布，文章中的固定百分比不进入门禁。样本还要记录设备、系统、编译模式、温度、场景和 trace 是否启用；这些条件对齐之后，两组实验的结果才能直接比较。

<!-- gracker-diagram: a297-12-semantic-build-and-device-validation -->
![插桩验收从业务语义到 Android 发布产物逐层推进](../../assets/diagrams/ch26/a297-12-semantic-build-and-device-validation.png)

图：COMPUTE_FRAMES不是业务语义证明；主机class测试、AGP集成与设备性能测试有独立范围。

## 运行时桥接的安全要求

插桩代码只调用参数少、职责单一的接口，采样与存储等复杂策略留在版本化桥接层。这一层要满足：

- 可快速关闭，失败时不阻塞业务；
- 不在主线程执行文件或网络 I/O；
- 不记录密钥、访问令牌、正文、完整 URL 或用户输入；
- 有递归保护，监控 SDK 自身不再触发同类监控；
- 处理采样、缓冲上限、背压和进程退出；背压是下游写入或上传变慢时，限制上游继续产生日志，避免内存无界增长；
- 事件包含 schema、插件、规则、App 和 Android 版本；schema 是事件字段、类型与兼容规则的版本化定义；
- 监控异常独立计数，不用吞掉业务异常来维持上报。

Android trace 通常用于短时诊断；生产环境需要长期数据时，保存的是聚合结果——场景级耗时、计数、分位数和低基数状态；每个方法的原始事件留给诊断现场。

低基数表示字段只有少量可枚举取值，例如页面类型；它比完整 URL 或用户 ID 更适合聚合。

罕见问题需要更完整的证据时，路径是先获得授权并限制采集范围，再通过公开的 `ProfilingManager`、Perfetto 或可重复实验取证。`ProfilingManager` 是允许 App 请求系统采集限定类型性能资料的公开 API，结果仍需按隐私与存储策略处理。


## 验收清单

全文的要求收在下面这张清单里：

- 构建插件使用 `variant.instrumentation`，已移除的 Transform API 清理干净。
- factory 无共享可变状态，所有配置都声明为 Gradle 输入。
- 默认 scope 为自有 class；处理第三方依赖时有坐标和签名白名单。
- visitor 覆盖隐式异常退出，且 begin/end 在同一线程正确嵌套。
- 新增控制流后选择合适的 frame computation mode。
- trace tag 不超过公开 API 限制，不包含用户或业务敏感数据。
- 过滤抽象、native、生成类、监控 SDK 自身和不适合处理的热方法。
- 网络监控优先使用客户端公开扩展点，framework 与依赖私有字段保持原样。
- 帧监控使用 JankStats、FrameMetrics、Macrobenchmark 与 Perfetto，`Choreographer`、`ActivityThread` 一类 framework 类保持原样。
- Kotlin 协程与 Compose 使用符合其执行模型的 tracing 方案。
- class fixture、Gradle 集成、minified release 和 Android 设备测试均通过。
- 成本门禁基于当前工程实测，保留可关闭开关和规则版本。

## 全文小结

编译期字节码插桩可以重复执行、检查变更，并在发布前验证。设计时把变换范围、控制流正确性、R8 后产物、运行时成本与数据隐私同时约束住，监控代码才不会成为新的稳定性问题。
