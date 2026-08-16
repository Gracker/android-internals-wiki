---
title: "App 内存分析"
chapter: "10.1"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-31"
last_verified_against: "AOSP android-17.0.0_r1 / kernel android17-6.18-2026-06_r6"
confidence: high
sources:
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Debug.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/hardware/interfaces/+/refs/tags/android-17.0.0_r1/memtrack/aidl/android/hardware/memtrack/IMemtrack.aidl"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/lmkd.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/memory/libmeminfo/+/refs/tags/android-17.0.0_r1/include/meminfo/procmeminfo.h"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/psi.c"
  - type: official
    path: "https://developer.android.com/topic/performance/memory-management"
  - type: official
    path: "https://developer.android.com/studio/profile/capture-heap-dump"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/native-heap-profiler"
  - type: official
    path: "https://developer.android.com/ndk/guides/memory-debug"
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
tags: [memory, pss, rss, mat, heapprofd, memtrack, memory-analysis]
related_chapters: ["4.1", "4.3", "4.5", "13.1", "14.5"]
task6_state: "reviewed"
section: "10.1"
status: finalized
pipeline_stage: "ready-to-publish"
task2b_state: fixed
task9_state: "reviewed"
---

# 10.1 App 内存分析

[适用版本：Android 8.0（API 26）至 Android 17（API 37）]

一条内存曲线只能说明某个统计口径发生了变化。Java heap（ART 管理的 Java/Kotlin 对象堆）、native allocator（C/C++ 默认内存分配器）、RSS、PSS、SwapPss、DMA-BUF（设备间共享缓冲区）和 GPU private memory（GPU 私有分配）分别观察不同对象；数值来自不同采样时刻时，连加都可能失真。

本文按 Android 17 / API 37 的 `android-17.0.0_r1` 核对平台行为，涉及 PSI 的内核实现以 `android17-6.18-2026-06_r6` 为准。分析顺序是先确定指标，再定位内存域，随后用对应工具寻找 owner（内存持有者或归属方）和生命周期。

---

## 1. 先确定问题属于哪种内存

### 1.1 常用指标的含义

| 指标 | 主要来源 | 回答的问题 | 容易误用的地方 |
|---|---|---|---|
| Java heap used | ART / `Runtime` / heap dump | 当前 Java/Kotlin 对象占用与引用关系 | 当成整个进程内存 |
| Java heap max | `Runtime.maxMemory()`、`getMemoryClass()` | Java heap 的增长预算 | 与 PSS 或 Graphics 直接相除 |
| Native allocated | bionic allocator / `Debug.getNativeHeapAllocatedSize()` | 分配器仍记为已分配的字节 | 当成 native RSS |
| RSS（Resident Set Size，驻留集大小） | `/proc/<pid>/status`、smaps | 当前驻留在物理内存中的共享页与私有页总和 | 汇总多个进程时重复计算共享页 |
| PSS（Proportional Set Size，按比例分摊集） | smaps / smaps_rollup | 私有页加按映射进程数分摊的共享页 | 当成硬上限或 LMKD 唯一依据 |
| USS（Unique Set Size，独占集大小） | Private Clean + Private Dirty | 当前进程独占的页面 | 忽略 swap、GPU private 与未映射 DMA-BUF |
| SwapPss | smaps | 按映射进程数分摊的换出页面 | 与 resident PSS（仍驻留部分）使用不同采样时刻相加 |
| Graphics / memtrack | `IMemtrack` 与厂商 HAL（硬件抽象层） | smaps 难以覆盖的图形、GL 和 GPU 私有内存 | 假定所有设备记账完整一致 |

PSS 适合比较包含共享映射的进程内存占用，RSS 适合低成本观察驻留变化。两者都受共享库、文件页、ZRAM（内存压缩交换设备）、进程状态和采样时刻影响。

`ActivityManager.getMemoryClass()` 与 `getLargeMemoryClass()` 返回 MB，描述 Dalvik/ART heap 的近似预算。PSS 以 kB 报告，并包含 Java heap 之外的原生分配、代码页、线程栈、图形内存和系统共享页分摊。二者没有可直接计算的“PSS 使用率”。

### 1.2 Android 17 的 `Debug.MemoryInfo`

`Debug.MemoryInfo` 将统计分成 dalvik（ART 托管堆）、native（原生分配）和 other（其他映射），并提供 Java Heap、Native Heap、Code、Stack、Graphics、Private Other、System、Total PSS 与 Total Swap 摘要。公开字段和摘要值以 kB 为单位。

几个边界需要保留：

- `getTotalPss()` 包含 swapped-out PSS，即按比例分摊的已换出页面；
- `getTotalUss()` 由各域 Private Clean 与 Private Dirty 相加；
- `getMemoryStats()` 的分类沿用 `dumpsys meminfo` 的 App Summary（应用摘要）口径；
- `Debug.getMemoryInfo()` 直接读取本进程底层统计，源码注明可能看不到部分受保护的 graphics 分配；
- `ActivityManager.getProcessMemoryInfo()` 可以补充系统侧统计，但 Android 10 / API 29 起只返回调用 UID 的进程，而且高频调用会得到缓存结果。

源码核对：

- [`Debug.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Debug.java)
- [`ActivityManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java#5115)

## 2. 建立第一份内存快照

下面的命令用于记录同一实验阶段的进程摘要、内存页大小和进程状态：

```bash
adb shell dumpsys meminfo -d com.example.app
adb shell getconf PAGE_SIZE
adb shell 'pid=$(pidof com.example.app); grep -E "VmRSS|RssAnon|RssFile|RssShmem|VmSwap|Threads" /proc/$pid/status'
adb shell dumpsys SurfaceFlinger --list
```

`dumpsys meminfo` 的详细列会随平台和厂商实现变化，报告中应保存原始输出。`/proc/<pid>/status` 的 `VmRSS` 是低成本估计；Android 17 `libmeminfo` 的源码也注明它不如 smaps（逐映射内存统计）精确。SurfaceFlinger layer（图层）列表只用于核对可见图形对象，不能单独给出每个图层的 GPU 内存。

应用内若要取得一次自进程快照，可以使用公开 `ActivityManager` API：

```kotlin
data class AppMemorySnapshot(
    val totalPssKb: Int,
    val javaHeapKb: Int,
    val nativeHeapKb: Int,
    val graphicsKb: Int?,
    val javaUsedBytes: Long,
    val javaMaxBytes: Long,
    val nativeAllocatedBytes: Long,
)

fun captureAppMemory(
    activityManager: ActivityManager,
): AppMemorySnapshot {
    val info = activityManager
        .getProcessMemoryInfo(intArrayOf(Process.myPid()))
        .single()
    val stats = info.memoryStats
    val runtime = Runtime.getRuntime()

    return AppMemorySnapshot(
        totalPssKb = info.totalPss,
        javaHeapKb = stats.getValue("summary.java-heap").toInt(),
        nativeHeapKb = stats.getValue("summary.native-heap").toInt(),
        graphicsKb = stats["summary.graphics"]?.toIntOrNull(),
        javaUsedBytes = runtime.totalMemory() - runtime.freeMemory(),
        javaMaxBytes = runtime.maxMemory(),
        nativeAllocatedBytes = Debug.getNativeHeapAllocatedSize(),
    )
}
```

这个函数保留了 kB 与 byte 的单位后缀，避免混算。系统会限制 `getProcessMemoryInfo()` 的采样频率，不能把它放进每帧回调、紧循环或高频定时器；它适合在实验步骤边界调用，或由低频诊断任务触发。

## 3. Java/Kotlin heap：用引用关系证明泄漏

Heap dump 是某一时刻 Java/Kotlin 堆中可达对象图的快照。它能回答对象由谁引用、哪个对象支配一片子图，却不能解释 native `mmap`（原生内存映射）、GPU allocation（GPU 分配）或系统为何杀进程。

### 3.1 三个必须分清的概念

- **Shallow Size**：对象自身在 managed heap（由 ART 管理的堆）中占用的字节，不含被引用对象；
- **Retained Size**：对象不可达后，预计可随它一起回收的受支配对象总量；
- **GC Root path**：对象通向 GC Root 的引用路径；GC Root 是垃圾回收器判定对象仍可达的起点，例如活跃线程、JNI global reference（JNI 全局引用）、类对象、系统类或活跃栈。

对象头、对齐、压缩引用和 ART 实现会改变 shallow size。不要用“两个 `int` 字段固定占多少字节”推导跨设备结论。

### 3.2 可复现的泄漏检查

1. 固定初始页面和进程状态；
2. 执行同一生命周期动作多轮，例如进入页面、返回、旋转或替换 Fragment View；
3. 等待异步任务和已知动画结束；
4. 采集 heap dump；
5. 查找应已销毁的 Activity、Fragment View、Compose state（Compose 状态对象）、listener、callback 或 cache entry（缓存条目）；
6. 沿 GC Root path 找到生命周期更长的持有者；
7. 修复后重复同一脚本，并比较实例数和 retained graph（保留关系图）。

单个 Activity 仍存活不一定是泄漏，系统、输入法、动画和异步消息可能短期持有引用。证据应包含“对象已经越过预期生命周期”和“引用链在稳定状态仍存在”。

Android 8.0 / API 26 及以上，Bitmap pixel data（像素数据）位于 native heap。Java heap 中的 `Bitmap` 对象仍是追踪归属关系的入口，Android Studio heap dump 也可能在 Native Size 列显示关联的原生内存。只看 Java shallow size 会低估图片成本。

来源：[Android Studio Heap Dump 指南](https://developer.android.com/studio/profile/capture-heap-dump)

### 3.3 分配 churn 与 retained leak 分开

对象创建速度很高、GC 后能回落，属于 allocation churn（大量短命对象造成的频繁分配）；对象沿异常引用链长期存活，属于 retained leak（对象保留型泄漏）。两者都可能让曲线升高，但定位工具不同：

- churn：记录 Java/Kotlin allocation callstack（分配调用栈）、GC 和帧时间；
- leak：使用 heap dump、dominator tree（支配树）与 GC root；
- 大数组或 Bitmap：同时核对 native size 和图片缓存策略；
- JNI global reference：结合 ART heap 与 native 调用栈检查持有者。

## 4. Native heap：分配归因与非法访问是两类问题

### 4.1 heapprofd 用于分配调用栈

heapprofd 在 Android 10 及以上跟踪 `malloc/free`、`new/delete` 分配，并用抽样记录降低目标进程开销。user build（日常发布版本的系统镜像）只能分析声明为 `profileable` 或 `debuggable` 的 App。

下面的命令使用 Perfetto 仓库中的推荐脚本，按进程名启动 native heap profiling：

```bash
tools/heap_profile android -n com.example.app
```

以进程名启动时，已经运行的匹配进程和后续启动的匹配进程都可进入采样；需要启动期证据时，应先启动 profiler（分析器），再启动 App。多进程应用还要分别确认 `com.example.app:worker` 等进程名。结束采集后，在 Perfetto UI 中打开生成目录里的 `raw-trace` 原始轨迹文件。

四个常用视图回答不同问题：

| 视图 | 含义 |
|---|---|
| Unreleased malloc size | 采集窗口内已分配但尚未 `free` 的估算字节数 |
| Unreleased malloc count | 采集窗口内尚未 `free` 的估算分配次数 |
| Total malloc size | 窗口内全部分配的估算字节数，包含已经 `free` 的分配 |
| Total malloc count | 窗口内全部估算分配次数，包含已经 `free` 的分配 |

heapprofd 不能回溯采集开始前的历史分配，也默认看不到绕过默认分配器的直接 `mmap`、graphics buffer（图形缓冲区）和 GPU private allocation。采样间隔、buffer overrun（采集缓冲区溢出）、符号文件与进程启动方式都会影响结果。

来源：[Perfetto Native Heap Profiler](https://perfetto.dev/docs/data-sources/native-heap-profiler)

### 4.2 heapprofd、allocator 与 resident memory 不能做简单减法

三类数字的范围逐步扩大：

```text
heapprofd
  采样到的 malloc/new 请求与 free

malloc_info / allocator statistics
  allocator 管理的 arena、cache 与仍持有的页面

Native Heap RSS / PSS
  已驻留页面，并受 page size、碎片、共享、swap 与采样时刻影响
```

`Native Heap RSS - heapprofd unreleased bytes` 不能直接命名为“碎片”。差值还可能来自未采样分配、启动前分配、allocator cache（分配器缓存）、对齐、页内空洞、直接 `mmap`、统计分类差异、ZRAM 和两个工具没有同时采样。

### 4.3 malloc debug 只用于受控调试构建

普通 App 开发者应通过 debuggable APK 的 `wrap.sh` 启用 malloc debug。下面的脚本记录 native allocation backtrace（原生分配调用栈）：

```sh
#!/system/bin/sh
LIBC_DEBUG_MALLOC_OPTIONS=backtrace logwrapper "$@"
```

`wrap.sh` 仅适用于 API 27 及以上的 debuggable App，会改变进程启动与分配开销。它不能放进生产包。`libc.debug.malloc.program` 接受可执行文件名，不能填写 Java package（包名）；平台 root/userdebug 场景若要针对 App，使用官方文档给出的 `wrap.<package>` 属性或随 APK 打包的 `wrap.sh`。

来源：[NDK wrap.sh 指南](https://developer.android.com/ndk/guides/wrap-script)

### 4.4 HWASan、GWP-ASan 与 heapprofd 的职责

| 工具 | 主要目标 | 适用方式 |
|---|---|---|
| heapprofd | 找分配调用栈、增长和 churn | profileable/debuggable App 或平台调试 |
| HWASan | 捕获 C/C++ 越界、use-after-free（释放后使用）和 double free（重复释放） | ARM64 测试构建；Android 14+ 可用 App `wrap.sh` |
| GWP-ASan | 抽样发现 heap use-after-free / overflow（堆越界） | Android 11+ 支持；Android 14+ 默认采用 Recoverable（可恢复）模式策略 |
| Malloc debug | guard（保护区）、backtrace、fill（填充值）等分配器调试 | debuggable App 或 root/userdebug |

ASan 仍可用于旧设备，但当前 NDK 指南已将它列为停止主动支持的方案；能使用 HWASan 时优先 HWASan。Sanitizer（内存错误检测器）会显著改变运行时间和内存开销，其测试数据不能作为普通 release 构建的基线。

来源：[NDK 内存错误调试与缓解](https://developer.android.com/ndk/guides/memory-debug)

## 5. Graphics、DMA-BUF 与 Bitmap

Android 17 的 AIDL `IMemtrack` 用来报告 smaps 无法完整追踪的设备相关内存。这里的 memtrack 是厂商 HAL 提供的设备内存记账接口，接口契约明确区分：

- `GRAPHICS + FLAG_SMAPS_UNACCOUNTED`：CPU/GPU 映射的 DMA-BUF PSS，并去除两组映射的重叠；
- `GL + FLAG_SMAPS_UNACCOUNTED`：指定 PID 的 GPU 私有分配；
- `pid = 0, type = GL`：系统级 GPU private memory；
- `OTHER + FLAG_SMAPS_UNACCOUNTED`：其他未进入 smaps 的设备内存。

HAL 必须避免不同 memtrack type（记账类别）重复记账，但设备是否支持某项查询、驱动能否准确归属到 PID，仍由产品实现决定。因此：

- `dumpsys meminfo` 的 Graphics 为 0 不证明没有 GPU 内存；
- Graphics 上升不能只从 Java heap dump 找 owner；
- SurfaceView、TextureView、ImageReader、MediaCodec、Camera 和 Vulkan 可能拥有不同的 buffer/layer 生命周期；
- Java `Bitmap` 引用释放后，还要等待图片库、GPU cache（GPU 缓存）和 renderer（渲染器）分别完成各自的释放流程。

源码核对：[`IMemtrack.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/refs/tags/android-17.0.0_r1/memtrack/aidl/android/hardware/memtrack/IMemtrack.aidl)

GPU 专项工具与 layer/buffer 追踪见 10.7 节；这里仅将 Graphics 从 Java/Native heap 口径中分离。

## 6. 建立可比较的基线

内存基线至少绑定以下维度：

| 维度 | 需要记录的值 |
|---|---|
| App | versionCode、build type（构建类型）、ABI、进程名 |
| 系统 | 设备型号、build fingerprint（系统构建指纹）、Android/API、page size |
| 场景 | 入口、操作脚本、循环次数、前后台状态 |
| 时间 | 进程启动后时长、采样点、采样工具 |
| 负载 | 账号数据量、图片规格、列表长度、网络响应 |
| 指标 | Java used/max、Native allocated、PSS、RSS、SwapPss、Graphics |

一条实用脚本可以设置这些采样点：

1. 冷启动首屏稳定；
2. 目标页面第一次进入；
3. 相同操作完成固定轮数；
4. 返回初始页面并等待异步释放；
5. 进入后台；
6. 进程重新回到前台。

判断时看分布和形态：

- 每轮结束后的 retained set（回收后仍保留的对象集合）持续增长：分析持有者与引用链；
- Java used 上下波动但稳定回落：更接近正常 GC 或 churn；
- Native allocated 上升：用 heapprofd 找调用栈；
- PSS/RSS 上升而 Java/Native allocated 稳定：检查 `mmap`、代码页、线程栈、图形内存、DMA-BUF 和 allocator residency（分配器持有的驻留页面）；
- 前台高、后台回落：可能来自可回收缓存或图形资源生命周期；
- 进程退出：读取 `ApplicationExitInfo`，不要只用末条内存曲线推断原因。

阈值应来自同设备族、同场景的历史分布和产品风险预算。固定写成“PSS 增长 5% 即回归”或“Java heap 超过 85% 就 dump”会在不同设备、页面和数据量上制造误报。

### 6.1 4 KB 与 16 KB page size 分组

Android 15 起支持使用 16 KB page size（内存页大小）的设备。页大小会影响 ELF（二进制文件格式）对齐、`mmap`、allocator page span（分配器跨越的页面范围）和驻留内存的计量单位。同一 APK 在 4 KB 与 16 KB 设备上的 PSS/RSS 基线可能不同。

基线处理规则：

- 记录 `getconf PAGE_SIZE`；
- 4 KB 与 16 KB 设备分组统计；
- 不用一个固定百分比从 16 KB 数据“还原”4 KB；
- native library 兼容性与内存回归分别判断；
- 同组内仍需固定系统构建版本、ABI 与输入数据。

官方文档中给出的总体内存变化来自特定测量集合，不能作为每个 App 的校正系数。

来源：[16 KB page size 支持指南](https://developer.android.com/guide/practices/page-sizes)

## 7. 系统内存压力与 LMKD

Android 17 `lmkd` 可通过 PSI（Pressure Stall Information，压力停顿信息）事件感知 memory stall（内存压力造成的任务停顿），并结合 watermark（可用内存水位）、swap、workingset refault/thrashing（工作集页面频繁换入引起的抖动）、reclaim（页面回收）状态和产品属性决定是否回收进程。候选进程按 `oom_score_adj` 的保护级别扫描；配置或压力级别要求比较进程大小时，再从同一 adj 档选择内存占用较高的进程。

所以：

- App PSS 高不等于下一次一定被杀；
- 前台/可感知进程与 cached 进程的保护级别不同；
- victim（被选中回收的进程）不只由 PSS 决定；
- LMKD kill、kernel OOM、crash、ANR 和用户 force-stop 是不同退出原因；
- 设备厂商可调整 lmkd 属性与内存策略。

源码核对：

- [`lmkd.cpp`](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/lmkd.cpp)
- [`psi.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/psi.c)

### 7.1 用 `ApplicationExitInfo` 补齐进程退出上下文

下面的代码读取当前包最近的退出记录：

```kotlin
val exitRecords = activityManager.getHistoricalProcessExitReasons(
    context.packageName,
    0,
    16,
)

for (record in exitRecords) {
    Log.i(
        "ExitMemory",
        "reason=${record.reason}, importance=${record.importance}, " +
            "pssKb=${record.pss}, rssKb=${record.rss}, " +
            "timestamp=${record.timestamp}",
    )
}
```

`getPss()` 与 `getRss()` 是系统上一次采样值，单位 kB；进程在采样前退出时可能为 0，该值也不代表退出瞬间的内存。应结合 `reason`（退出原因）、`subreason`（细分原因）、importance（进程重要性）、描述、trace 和自定义 state summary（状态摘要）判断。

应用还可以在低频业务状态切换时写入最多 128 bytes（字节）的非敏感摘要：

```kotlin
val state = "screen=checkout;phase=confirm"
    .toByteArray(StandardCharsets.UTF_8)
activityManager.setProcessStateSummary(state)
```

系统可能限制该 API 的调用频率，过度调用会抛出 `RuntimeException`。摘要用于退出分析，不用于恢复 UI，也不能包含账号、订单、位置等敏感信息。

源码核对：[`ApplicationExitInfo.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java#912)

## 8. 线上监控只采集低风险证据

线上内存监控不应远程触发 heap dump、malloc debug 或 sanitizer。适合收集的内容包括：

- 进程、页面/场景枚举和前后台状态；
- Java used/max；
- 低频采集本进程的 PSS/RSS 与摘要分类；
- native allocated；
- page size、ABI、device/build、App 版本；
- trim callback（内存回收提示回调）、退出原因和最近的非敏感状态摘要；
- OOM、native crash 与 LMKD 相关的聚合事件。

采样时机根据业务选择：

- 场景进入和退出；
- 固定生命周期节点；
- 内存增长速度异常时增加一份低成本快照；
- 进程下次启动时读取历史退出记录；
- 实验组与基线组使用相同采样策略。

采样本身会排队、读取 procfs（`/proc` 进程信息文件系统）或调用 Binder。周期由设备开销实验确定，不使用通用的“30—60 秒”。`getProcessMemoryInfo()` 的系统缓存也使更短周期未必产生新数据。

隐私与稳定性要求：

- 不上传 heap 内容、对象字符串、文件路径、图片或业务 payload（载荷数据）；
- state summary 使用枚举或短 ID，不写用户标识；
- 采样失败返回 unknown，不循环重试；
- 单位写进字段名；
- 多进程分别记录 PID、进程名和角色；
- OOM 前末次样本只当上下文，不当死亡瞬间证据。

## 9. 按现象选工具

| 现象 | 下一步工具 | 需要证明的事 |
|---|---|---|
| Java used 与实例数持续增长 | Heap dump / dominator / GC root | 哪个长生命周期持有者保留对象 |
| Java used 回落但 GC 很密 | ART allocation profiling / Perfetto | 哪些调用栈制造 churn |
| Native allocated 持续增长 | heapprofd | 哪些 malloc/new 调用栈未释放 |
| Native RSS 高于 allocator 统计 | smaps、malloc_info、mmap trace | 缓存、碎片、直接映射或 swap 哪项成立 |
| Graphics 增长 | memtrack、SurfaceFlinger layer、GPU 专项工具 | 哪个 Surface、buffer 或 GPU 资源持有者未释放 |
| PSS/RSS 增长但 heap 稳定 | meminfo 分类、threads、maps、graphics | 增量属于 code、stack、mmap、共享页还是设备内存 |
| 进程消失 | `ApplicationExitInfo`、系统日志、LMKD 事件 | 退出原因、保护级别与上次采样上下文 |
| Native 非法访问 | HWASan / GWP-ASan / Malloc debug | 越界、use-after-free 或 double free 的访问栈 |

## 10. 交付前检查表

- [ ] 每个指标都标明单位、来源、进程和采样时刻。
- [ ] PSS 没有与 `memoryClass` 或 `largeMemoryClass` 计算比例。
- [ ] Java heap、native allocator、resident pages 和 Graphics 分开。
- [ ] Heap dump 结论包含预期生命周期与 GC root。
- [ ] heapprofd 结论注明采样窗口、interval（采样间隔）、符号和未覆盖的 `mmap`/graphics。
- [ ] Native RSS 与 heapprofd 的差值没有直接写成碎片。
- [ ] malloc debug 只用于 debuggable/root 受控环境。
- [ ] Bitmap 在 API 26+ 的 pixel data 按 native 归属关系分析。
- [ ] memtrack 缺失或为 0 时，没有断言 GPU 内存为 0。
- [ ] 4 KB 与 16 KB page size 使用不同基线分组。
- [ ] LMKD 判断包含 PSI、reclaim、swap/thrashing、adj 与设备配置。
- [ ] `ApplicationExitInfo` 的 PSS/RSS 被标为上次采样。
- [ ] 线上数据不含 heap 内容和敏感业务信息。

---

## 延伸阅读

- **4.1 Android 内存管理机制**
- **4.3 Java / Native 内存泄漏**
- **4.5 Low Memory Killer 与进程优先级**
- **10.2 内存泄漏分析**
- **10.6 内存抖动**
- **10.7 GPU 与图形内存统计**
- **13.1 Perfetto 内存数据源**
