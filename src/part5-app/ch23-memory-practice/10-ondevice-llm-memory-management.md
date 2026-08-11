---
title: "端侧大模型推理的内存管理"
chapter: "23.10"
status: ready-for-review
drafted_date: "2026-06-25"
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
last_verified: "2026-06-25"
last_verified_against: "AIW 5.11 / 23.6 / 23.7 / 4.15 已验证数据；Memory Advice API deprecated beta (developer.android.com 2026-02)"
confidence: medium
sources:
  - type: official
    path: "developer.android.com/ndk/guides/neuralnetworks"
  - type: official
    path: "developer.android.com/games/sdk/memory-advice/overview"
  - type: official
    path: "ai.google.dev/edge/litert/android"
  - type: aosp
    path: "frameworks/ml/nn/"
  - type: aosp
    path: "frameworks/opt/gamesdk/games-memory-advice/"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md"
tags: [端侧AI, 大模型, 内存管理, 推理优化, MemoryAdvice, KVCache, 量化]
related_chapters: ["5.11", "5.12", "23.6", "23.7", "23.9", "4.3", "4.15", "10.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-24"
gap_source: "章节深挖"
drafted_by: "openclaw-task2a"
consolidated_from:
  - "src/part5-app/ch23-memory-practice/22.09-ondevice-llm-memory-management.md"
  - "src/part5-app/ch23-memory-practice/23.24-android-17-ai-推理加速与-neuralnetworks-hal-优化.md"
---

# 端侧大模型推理的内存管理

端侧大模型的内存风险很少只来自模型文件。权重、KV Cache、prefill 临时张量、运行时编译产物、GPU/NPU 缓冲区、应用自身的 Java 与 native 内存，会在不同阶段形成不同峰值。模型能够加载，也不等于长上下文生成、并发会话和后台切换能够稳定运行。

平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`；涉及 `/proc` 与页回收语义时，以 `android17-6.18-2026-06_r6` 为内核锚点。LiteRT、MediaPipe LLM Inference 等属于独立发布的库，能力要按项目锁定的库版本和目标设备验证，不能从 Android API level 推导。

## 1. 先把内存分项记清楚

### 1.1 六类常驻或阶段性内存

| 类别 | 典型内容 | 容易出现峰值的阶段 | 主要控制量 |
|---|---|---|---|
| 模型权重 | embedding、attention、FFN、量化元数据 | 文件映射、运行时初始化、delegate（硬件执行插件）准备 | 参数量、位宽、混合精度、是否重排或复制 |
| KV Cache | 每层历史 token 的 Key/Value | prefill（提示词预填充）结束、持续 decode（逐 token 解码） | 上下文长度、批大小、KV 头数、元素类型 |
| 临时张量 | attention 分数、FFN 中间值、prefill 工作区 | 首次运行、长 prompt prefill | 分块大小、算子实现、缓冲区复用 |
| 编译与后端资源 | 计算图、着色器、NPU 编译产物、命令缓冲区 | delegate 初始化、首次运行 | 后端、AOT/JIT、驱动实现 |
| 输入与输出 | tokenizer 缓冲区、Bitmap、音频、输出 token | 多模态预处理、流式输出 | 输入尺寸、并发请求、对象生命周期 |
| 应用基线 | ART heap、native heap、线程栈、代码与 UI | 进程整个生命周期 | 依赖、缓存、线程和页面状态 |

排查时应记录每个阶段。一次 `dumpsys meminfo` 只能说明采样时刻的状态。至少区分：未加载模型、模型文件打开、运行时/delegate 初始化完成、首次运行、prefill 峰值、稳定 decode、取消生成、关闭会话、关闭模型。

### 1.2 权重大小只能先算理论下限

如果参数量为 \(P\)，平均权重位宽为 \(b\)，仅权重数据的理论下限是：

`weight_min_bytes = P × b ÷ 8`

下表按十进制参数量计算，再换算成 GiB。它不包含 scale、zero-point、分组索引、padding、词表、运行时副本和编译产物：

| 参数量 | FP16 下限 | 8-bit 下限 | 4-bit 下限 |
|---:|---:|---:|---:|
| 2B | 3.73 GiB | 1.86 GiB | 0.93 GiB |
| 7B | 13.04 GiB | 6.52 GiB | 3.26 GiB |
| 13B | 24.21 GiB | 12.11 GiB | 6.05 GiB |

“4-bit 模型”也可能保留 FP16/FP32 的归一化层、embedding 或输出层。分组量化还要为每组保存 scale，非对称方案通常还需要 zero-point。模型文件大小比表中下限高并不说明打包异常。

量化选择不能只看压缩率。算子是否被目标后端支持、是否触发 CPU 回退、加载时是否反量化或重排，都会改变运行时内存。精度变化也依赖模型、校准集、量化算法和任务，不能用一个通用的 MMLU 降幅代替应用验收。

### 1.3 KV Cache 要按模型配置计算

对每层都保留完整 K/V、没有滑动窗口的常见 decoder，KV Cache 可按下式估算：

`kv_bytes = 2 × batch × layers × kv_heads × head_dim × cached_tokens × element_bytes`

系数 2 分别对应 Key 和 Value。这里使用 `kv_heads`，不能直接拿 attention query head 数代替；GQA 和 MQA 的 KV 头数可能更少。

例如 batch 为 1、32 层、8 个 KV 头、head dimension 为 128、缓存 4096 个 token、每个元素 2 bytes，结果是 512 MiB。只把 KV 头数改成 32，结果变为 2 GiB。这两个数是公式演示，不对应某个产品模型。

还要处理这些修正项：

- 部分层采用 sliding-window attention 时，只能对这些层把保留 token 数限制到窗口大小；global attention 层仍可能保留完整上下文。
- KV 量化只有在引擎明确支持时才会减少缓存；权重量化不会自动改变 KV 的元素类型。
- 并发会话通常各自拥有 KV Cache，共享同一份权重不代表共享会话状态。
- 推测解码（speculative decoding）会增加草稿模型的权重和会话状态，内存收益不能由速度收益代替评估。
- 前缀缓存、分页 KV 或会话状态导出/导入都属于引擎能力，不能把服务端框架的实现推定为 Android 端已有能力。

[MediaPipe LLM Inference 的 Android 配置](https://developers.google.com/edge/mediapipe/solutions/genai/llm_inference/android) 把 `maxTokens` 定义为输入与输出 token 的总上限。对使用该 API 的应用，这个参数会直接限制会话上下文上界，但具体内存仍要由模型结构和后端实测。

### 1.4 文件映射不等于零成本加载

权重以只读文件映射加载时，VSS 会先增加，RSS/PSS 随缺页和回收变化。文件页可以被内核回收，也可能与其他进程共享页缓存；这不保证 delegate 会直接使用原始映射。后端可能为了对齐、布局转换、量化解码或设备私有格式再分配一份缓冲区。

因此需要分别观察：

- 模型文件映射的 VSS、RSS/PSS；
- native heap 与匿名映射；
- 图形、DMA-BUF 或 memtrack 能看到的设备缓冲区；
- delegate 初始化前后的增量；
- 第一次 inference 前后的增量。

把模型文件大小、native heap 和 GPU 缓冲区直接相加也可能重复计算同一物理页。跨域比较应优先使用进程 PSS，并保留各分类作为归因线索。

### 1.5 16 KiB 页与数据搬运也会形成峰值

16 KiB 页设备会改变模型文件映射、native allocator region 和小映射的页面粒度。自研 loader 不能写死 4096 字节对齐；文件 `mmap()` 的 offset 必须遵守运行时页大小，APK/ELF 也要按官方 16 KiB 兼容要求构建。页变大不会自动让每个 tensor 占用独立 16 KiB，但会改变内部碎片和驻留页的观察结果。

跨进程或跨硬件后端传递大 tensor 时，Binder 只传控制信息、句柄和小型元数据。数据本体优先使用运行时 tensor buffer、`SharedMemory`、文件描述符或满足 consumer 约束的 `AHardwareBuffer`。Java direct `ByteBuffer` 通常没有可访问的 array，不能用 `arrayOffset()` 推断 native 地址。即便共享缓冲区能够 import，也要用 trace 验证是否发生 CPU staging copy、后端重排或额外设备副本。

模型加载、delegate 初始化和首次 compilation 不放在主线程。Perfetto 中除了计算 slice，还要查看 Binder wait、Runnable 排队、page fault、大块 memcpy 和后端返回码，避免把数据搬运与初始化等待误判为“算子计算慢”。

## 2. 设备 RAM 不是应用预算

### 2.1 三种上限回答不同问题

`ActivityManager.getMemoryClass()` 与 `getLargeMemoryClass()` 描述的是应用的近似 Java heap class，不覆盖 native heap、线程栈、文件映射和图形缓冲区。系统在内存压力下还会根据进程重要性和整体压力回收或终止进程。

[`ActivityManager.MemoryInfo`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java) 中：

- `availMem` 是系统层面的可用内存估算，源码注释明确说明它不能当作绝对值；
- `threshold` 是系统开始清理后台服务和其他进程时参考的阈值；
- `lowMemory` 表示系统当前是否处于低内存状态。

这些字段都不是为当前应用预留的可分配额度。`availMem >= model_file_size × 1.5` 之类的固定公式会忽略应用基线、KV Cache、后端副本、进程优先级和并发工作集，因此不能作为上线准入条件。

Android 17 的 [`MemoryLimiter.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryLimiter.java) 和 LMKD/OOM-adj 控制位于 `system_server` 与系统守护进程内。普通应用没有公共 API 为自己设置 `memory.high`、`memory.swap.high` 或 OOM-adj，也不应通过反射或 shell 权限绕过系统策略。

### 2.2 为每个模型变体建立设备档案

可执行的预算来自目标设备测试。每条档案至少包含：

- 模型与量化格式的不可变版本；
- 运行时、delegate 与驱动版本；
- ABI、Android 版本、页大小、SoC 和物理 RAM 档位；
- 后端与回退结果；
- 上下文上限、并发会话数、输入模态与尺寸；
- 各阶段 PSS、RSS、`VmHWM`、native heap 和可见的图形/DMA 数据；
- 冷加载、热加载、取消、释放和重新加载结果；
- 发生 delegate 编译失败、`mmap`/allocator 失败、Java OOM 或 LMK 的现场。

同一个模型在两台 RAM 相同的设备上也可能得到不同结果。驱动是否复制权重、NPU 编译策略、GPU 共享内存核算和厂商后台进程都会影响可用余量。

### 2.3 降级项必须能够独立选择

建议把降级项分开配置，不要只准备“完整模型”和“拒绝运行”两个状态：

| 维度 | 可选动作 | 需要重新验证的内容 |
|---|---|---|
| 模型 | 参数更少或量化更强的变体 | 精度、算子覆盖、加载峰值 |
| 上下文 | 降低 input + output token 上限 | 业务可用性、KV 峰值 |
| 会话 | 限制并发、关闭闲置会话 | 排队时延、取消语义 |
| 模态 | 降低图像尺寸、限制图像/音频数量 | 任务质量、预处理峰值 |
| 后端 | NPU/GPU 失败后选择 GPU/CPU | 回退路径的内存与延迟 |
| 预热 | 关闭后台预加载或 JIT 预热 | 首次请求时延 |

每个组合都要有实测档案。量化更强的模型如果触发 CPU 回退，内存和时延都可能比原方案更差。

## 3. 运行时生命周期决定峰值

### 3.1 一个资源管理器负责模型、会话和缓冲区

模型、delegate、会话、KV Cache、输入/输出缓冲区应由同一个生命周期组件管理。释放顺序建议遵守运行时的所有权关系：

1. 停止接收新请求；
2. 请求取消正在生成的任务；
3. 等待回调和后端工作结束；
4. 关闭会话，释放 KV Cache；
5. 关闭 I/O、图像、音频和共享缓冲区；
6. 关闭模型、delegate 与运行时；
7. 清除只为该模型服务的 tokenizer 和业务缓存。

不能在异步回调仍可能访问对象时直接关闭 native handle。框架实现 `AutoCloseable` 时，应使用 `try-with-resources`、Kotlin `use` 或显式 `finally`。MediaPipe 官方多模态示例也把 `LlmInference` 与 `LlmInferenceSession` 放进受控的关闭范围。

### 3.2 切换模型时避免双份驻留

“先加载新模型，成功后再释放旧模型”能降低切换失败风险，却会制造双模型峰值。内存紧张的设备应采用以下过程：

- 保存可重建的会话文本和业务状态；
- 停止旧会话；
- 关闭旧模型并保存释放后的资源所有者、PSS/RSS 与 native 分配快照；
- 加载目标变体；
- 加载失败时进入更小变体或云端路径。

allocator、驱动缓存或文件页可能让数值延迟回落，所以“旧资源已关闭”不能只由单个 RSS 数字判断。若产品要求无缝切换，双模型窗口就必须作为独立场景进入预算，不能把它归入正常单模型峰值。

### 3.3 多会话与多模型要经过统一调度

同一进程中的推理入口应统一限制模型数、会话数、上下文 token 总量和多模态输入总量。并发是否可行要由后端文档和测试决定；“NPU 同一时刻只能运行一个任务”不是 Android 平台契约，不同 SoC、驱动和 delegate 可能采用排队、并发或回退。

闲置会话的处理也要明确：

- 能快速从文本重建时，关闭会话通常比长期保存 KV 更稳妥；
- 只有引擎提供稳定的状态导出/导入时，才考虑把 KV 或会话状态写入存储；
- 会话状态可能含用户敏感内容，持久化需要加密、失效和删除规则；
- 预热模型与预热会话分开配置，保留权重不要求保留全部 KV。

## 4. Android 17 可用的压力信号

### 4.1 不为新项目接入 Memory Advice

[Memory Advice API](https://developer.android.com/games/sdk/memory-advice/overview) 的 beta 已结束，库已被官方标记为 deprecated。它属于 AGDK 的实验性 native 库，不是 Android 17 新增的平台内存接口。现有项目可以在迁移期保留观测，但不应把它作为新推理管线唯一的准入或降级信号；接口状态与迁移边界详见 [内存监控与线上治理](07-memory-monitoring.md)。

### 4.2 `onTrimMemory()` 只负责机会性释放

Android 14 起，系统不再发送大部分旧的 running trim level；Android 15 将这些常量正式标记为 deprecated。当前官方建议集中处理 `TRIM_MEMORY_UI_HIDDEN` 和 `TRIM_MEMORY_BACKGROUND`。

下面的片段用于展示回调内只派发释放任务，不在回调线程执行模型关闭或等待后端：

```kotlin
override fun onTrimMemory(level: Int) {
    when {
        level >= ComponentCallbacks2.TRIM_MEMORY_BACKGROUND -> {
            inferenceExecutor.execute {
                inferenceController.cancelAndReleaseRebuildableState()
            }
        }
        level >= ComponentCallbacks2.TRIM_MEMORY_UI_HIDDEN -> {
            inferenceExecutor.execute {
                inferenceController.releaseUiInputs()
            }
        }
    }
}
```

`inferenceController` 是应用自己的生命周期组件，不是平台类。任务还要去重，避免连续回调排队执行多次关闭。`TRIM_MEMORY_UI_HIDDEN` 表示 UI 已不可见，不证明系统已经出现内存压力；它提供的是释放 UI 输入与预览缓存的时机。该回调也不是“杀进程前一定通知”的协议；会话文本和用户操作进度应在正常业务流程中持续保存。

### 4.3 `MemoryInfo` 适合做信号，不适合做容量承诺

加载前可以读取 `lowMemory`、`availMem` 和当前进程状态，结合已经测得的设备档案决定是否禁用预热、选择较小模型或延后任务。不要高频轮询；[`ActivityManager.getMemoryInfo()`](https://developer.android.com/reference/android/app/ActivityManager#getMemoryInfo(android.app.ActivityManager.MemoryInfo)) 的文档也建议优先使用 trim callback。

Android 17 的 `ProfilingManager` 增加了 `TRIGGER_TYPE_OOM` 与 `TRIGGER_TYPE_ANOMALY` 等触发器。它们适合生产问题取证，不是同步的“剩余多少字节”查询：OOM 触发结果在后续启动注册时提供，anomaly 也只能说明系统检测到异常资源行为。配置细节参阅 [Android 17 ProfilingManager 文档](https://developer.android.com/reference/android/os/ProfilingManager)。

## 5. CPU、GPU 与 NPU 的边界

### 5.1 Android 17 不再把 NNAPI 作为新方案

[NNAPI 在 Android 15 / API 35 已 deprecated](https://developer.android.com/ndk/guides/neuralnetworks/migration-guide)。Android 17 仍保留接口用于兼容，但官方说明未来设备可能更多回到 CPU 后端，并建议迁移到可独立更新的高层运行时。新项目不应通过 NNAPI 枚举设备来设计长期 NPU 调度。

当前 [LiteRT `CompiledModel` API](https://developers.google.com/edge/litert/next/android_kotlin) 提供 CPU、GPU 和 NPU 路径，但具体 NPU 支持仍依赖 SoC、运行时包、delegate、模型算子和分发方式。选择 `Accelerator.NPU` 不能证明整图都在 NPU 上运行；需要记录分区、回退、初始化峰值和首轮峰值。

对较大的、目标 SoC 已知的模型，[部分 LiteRT NPU 路径](https://developers.google.com/edge/litert/android/npu/qualcomm) 支持 AOT 产物，用于减少设备侧编译工作。AOT 是否降低内存、产物是否会与原模型同时驻留，仍应按对应 vendor delegate 的版本验证。

### 5.2 共享缓冲区不代表所有硬件都能直接访问

[`AHardwareBuffer`](https://developer.android.com/ndk/reference/group/a-hardware-buffer) 从 API 26 起提供跨进程和图形 API 可共享的缓冲区。格式、usage flags、尺寸和实现共同决定它能否分配或被某个消费者导入；API 29 起可先用 `AHardwareBuffer_isSupported()` 检查给定描述。

`AHardwareBuffer` 没有“所有 NPU 都可访问”的平台保证。即使 GPU 或 delegate 接受它，也要核对：

- CPU 锁定访问是否允许、是否会等待 fence；
- GPU/NPU import 是否产生额外副本；
- 缓存同步与所有权转换；
- 缓冲区的引用计数和关闭时机；
- memtrack、DMA-BUF 与进程 PSS 中怎样核算。

OpenCL 也不是 Android NDK 面向所有设备提供的稳定公共计算 API。某个推理库要求声明 vendor OpenCL native library，只能说明该库在指定设备路径上的依赖，不能上升为 Android 17 通用接口。

### 5.3 CPU 路径仍有映射和工作区

CPU 后端可以直接访问进程地址空间中的权重和 tensor，通常不需要设备私有显存，但仍会使用文件映射、native arena、线程栈、权重打包缓冲区和算子工作区。增加线程数可能同时增加栈 reservation 和每线程临时缓冲区。并行度应根据吞吐、峰值 PSS、温度和尾延迟共同确定。

## 6. 怎样测到可解释的峰值

### 6.1 `VmRSS` 与 `VmHWM` 不要混用

Android 17 的 [`Debug.getRss()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Debug.java) 是带 flag 的当前 RSS 查询；它不返回历史峰值。`/proc/self/status` 中 `VmRSS` 是当前 RSS，`VmHWM` 是进程生命周期内的 RSS high-water mark。推理前后各调用一次当前 RSS，再取差值，无法证明区间峰值。

下面的 Kotlin 函数用于低频读取关键 `/proc/self/status` 字段。内存字段的单位是 KiB，`Threads` 表示线程数量：

```kotlin
import java.io.File

private val memoryStatusKeys = setOf(
    "VmSize", "VmRSS", "VmHWM", "RssAnon",
    "RssFile", "RssShmem", "VmSwap", "Threads"
)

fun readProcessStatus(): Map<String, Long> =
    File("/proc/self/status").useLines { lines ->
        lines.mapNotNull { line ->
            val separator = line.indexOf(':')
            if (separator <= 0) return@mapNotNull null

            val key = line.substring(0, separator)
            if (key !in memoryStatusKeys) return@mapNotNull null

            val value = line.substring(separator + 1)
                .trim()
                .substringBefore(' ')
                .toLongOrNull()
                ?: return@mapNotNull null
            key to value
        }.toMap()
    }
```

该函数适合在阶段边界或异常触发时采样，不应放进逐 token 热路径。`VmHWM` 不能重置；需要比较单阶段峰值时，可在独立测试进程中运行场景，或用足够频率的 RSS/PSS 采样配合 Perfetto 时间线。

### 6.2 每个采样点保存同一组字段

建议统一保存：

- 时间、场景、模型/会话 ID、上下文 token 数和输入尺寸；
- 后端、delegate、回退结果与线程数；
- `VmSize`、`VmRSS`、`VmHWM`、`RssAnon`、`RssFile`、`RssShmem`、`VmSwap`；
- PSS 分类、native heap、Java heap、图形与代码；
- 当前模型、会话、KV Cache 和 I/O 缓冲区数量；
- 最近一次加载、编译、取消、关闭、allocator 或 delegate 错误。

`/proc` 字段语义以 [`android17-6.18-2026-06_r6` 的 `proc.rst`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/proc.rst) 为准。PSS 会按共享比例分摊，比 RSS 更适合比较多进程总成本；诊断单个分配所有者时仍要看 maps、native 分配分析和运行时日志。

### 6.3 GPU 与 native 内存需要外部工具

Android 17 `Debug.java` 中的 `getGpuTotalUsageKb()` 和 `getGpuPrivateMemoryKb()` 是 `@hide` 系统接口，普通应用不能把它们当作 SDK API。`dumpsys gfxinfo` 也不是通用的 LLM GPU 内存计数器。

测试环境可以组合：

- `adb shell dumpsys meminfo <package>` 的 Graphics、GL、DMA/memtrack 分类；
- Perfetto 的进程、内存和可用 GPU 计数器；
- [heapprofd](https://perfetto.dev/docs/data-sources/native-heap-profiler) 定位 native 分配调用栈；
- delegate/运行时自带 profiler；
- SoC 厂商工具，用于只在对应设备上解释驱动内存。

Native heap 统计与 Scudo 边界详见 [Native 内存管理与优化](03-native-memory-management.md)。同一场景应保留完整工具版本和设备 build fingerprint，避免直接横向比较厂商字段。

## 7. 内存压力下的动作顺序

### 7.1 根据原因处理，不按单一颜色处理

| 现场 | 可能原因 | 优先动作 |
|---|---|---|
| 加载阶段 PSS 翻倍 | 权重重排、delegate 编译、旧模型未关闭 | 对比分阶段快照，检查双模型窗口与后端副本 |
| prefill 峰值过高 | 长 prompt、临时 attention/FFN 工作区 | 限制上下文、评估 chunked prefill 或更小模型 |
| decode 随 token 线性增长 | KV Cache 持续扩张 | 限制总 token、关闭闲置会话、验证 KV 量化支持 |
| 取消后内存不回落 | 回调仍在运行、会话/模型未关闭、分配器保留 | 核对资源所有者、等待后端、区分泄漏与可复用 arena |
| GPU delegate 失败后峰值更高 | 回退时旧资源未释放或产生双后端资源 | 记录回退顺序，关闭失败后端后再创建替代路径 |
| 无 Java OOM 但进程消失 | LMK、native abort、driver crash 或系统限制 | 查 `ApplicationExitInfo`、logcat、Vitals 与系统事件 |

压力信号到达后，控制器应先阻止新任务，再取消或完成当前临界操作，然后释放可重建资源。不要在 native 后端执行中途随意 `munmap()` 权重或缓冲区；这会把可恢复的压力问题变成 use-after-free 或驱动错误。

### 7.2 保存可恢复状态

端侧对话的可恢复状态通常是结构化消息、采样参数、模型版本和已提交的业务结果。KV Cache 只是运行时加速状态。进程可能在没有回调的情况下被 LMKD 终止，因此重要状态应随交互增量保存；进程重建后再根据策略恢复模型和上下文。

## 8. 多进程能隔离生命周期，不能减少总账

把推理引擎放入私有子进程有两个常见收益：native/driver 崩溃不会直接破坏 UI 进程，结束子进程可以一次释放它拥有的运行时与映射。代价包括第二套 ART/native 基线、Binder/序列化成本、模型可能重复映射，以及更复杂的恢复协议。

评估多进程时需要：

- 汇总所有应用进程的 PSS；主进程下降只能说明内存转移，不能说明总成本下降；
- 确认模型只在需要的进程初始化；
- 大输入优先传 FD、`SharedMemory` 或受控的 `HardwareBuffer`，避免 Binder 内复制大数组；
- 定义子进程死亡、任务幂等、结果去重和版本不匹配的处理；
- 不用前台服务或频繁绑定服务提高进程存活率来掩盖过高内存。

应用不能调用 `ProcessList.batchSetOomAdj()` 或向 LMKD 发送私有控制包。进程重要性由可见组件、服务状态和系统策略决定，伪造高优先级会挤压整机内存。

## 9. 测试覆盖与通过条件

### 9.1 设备与软件维度

设备与软件范围至少覆盖：

- Android 14、15、16、17 中产品支持的版本；
- 32/64 位 ABI，以及产品实际支持的 4 KiB/16 KiB 页设备；
- 不同 RAM 档位、SoC 和 GPU/NPU 驱动；
- 运行时/delegate 的发布版本；
- CPU、GPU、NPU 与每条允许的回退路径；
- 冷启动、热启动和进程被系统重建。

### 9.2 场景维度

每个模型变体都要覆盖：

- 最短、常用和允许的最大上下文；
- 最大输出 token；
- 单会话与允许的最大并发；
- 多模态最大输入尺寸和数量；
- 首次编译、AOT 产物、缓存命中与缓存失效；
- 生成中取消、前后台切换、旋转/配置变化；
- 模型切换、后端失败与降级；
- 多轮加载/关闭，直到 PSS/RSS 与 native 分配进入稳定区间；
- 受控系统内存压力和 LMK 恢复。

循环次数应由“是否进入稳定区间”和泄漏检测灵敏度决定，不使用统一的 10 次或 1000 次。模拟 trim callback 只能测试处理代码，不能替代真实内存压力、页回收、swap 和 LMKD 场景。

### 9.3 通过条件

通过条件来自每个设备档案，至少包含：

- 所有阶段峰值未触发 Java/native OOM、系统内存限制或前台 LMK；
- 最大上下文下没有未声明的后端回退；
- 取消与关闭后，资源所有者数量归零，内存回到可解释的稳定区间；
- 后台释放后能够恢复，用户输入和已确认结果不丢失；
- 模型切换的双份窗口已被消除或明确计入预算；
- 线上能够通过 Android Vitals、`ApplicationExitInfo` 和 Android 17 分析触发器追踪失败。

全设备通用的安全系数无法覆盖运行时、驱动和模型结构差异。应把权重、KV、工作区、后端资源和应用基线分别量化，再用阶段化数据限定模型、上下文、会话和后端组合。Android 17 提供了更好的系统约束与取证能力，但应用仍要自己管理推理资源的所有权和恢复协议。

## 参考资料

- [Android 17 `ActivityManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java)
- [Android 17 `Debug.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Debug.java)
- [Android 17 `MemoryLimiter.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryLimiter.java)
- [Android 17 LMKD](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/)
- [Android 17 common kernel `/proc` documentation](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/proc.rst)
- [Manage your app's memory](https://developer.android.com/topic/performance/memory)
- [Memory Advice API overview](https://developer.android.com/games/sdk/memory-advice/overview)
- [NNAPI migration guide](https://developer.android.com/ndk/guides/neuralnetworks/migration-guide)
- [LiteRT `CompiledModel` Kotlin API](https://developers.google.com/edge/litert/next/android_kotlin)
- [MediaPipe LLM Inference for Android](https://developers.google.com/edge/mediapipe/solutions/genai/llm_inference/android)
- [Android NDK `AHardwareBuffer`](https://developer.android.com/ndk/reference/group/a-hardware-buffer)
- [Perfetto native heap profiler](https://perfetto.dev/docs/data-sources/native-heap-profiler)
