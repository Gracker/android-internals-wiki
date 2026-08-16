---

title: 内存持续增长
chapter: '10.3'
section: '10.3'
status: finalized
applicable_versions: Android 8.0 (API 26) - Android 17 (API 37)
last_verified: '2026-07-31'
last_verified_against: AOSP android-17.0.0_r1; Android common kernel android17-6.18-2026-06_r6
confidence: high
sources:
- type: blog
  path: OPPO内存反碎片优化原理
- type: blog
  path: RTC 性能自动化工具在内存优化场景下的实践
- type: blog
  path: Hummer引擎优化系列 - 内存稳定性研究与优化
- type: aosp
  path: platform/frameworks/base/core/java/android/util/LruCache.java@android-17.0.0_r1
- type: aosp
  path: platform/frameworks/base/core/java/android/os/Debug.java@android-17.0.0_r1
- type: aosp
  path: platform/frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java@android-17.0.0_r1
- type: kernel
  path: kernel/common/mm/page_alloc.c@android17-6.18-2026-06_r6
- type: kernel
  path: kernel/common/mm/compaction.c@android17-6.18-2026-06_r6
- type: official
  path: https://developer.android.com/reference/android/util/LruCache
- type: official
  path: https://developer.android.com/about/versions/17/behavior-changes-all#app-memory-limits
- type: official
  path: https://developer.android.com/topic/performance/memory-management
- type: official
  path: https://developer.android.com/topic/performance/graphics/manage-memory
- type: official
  path: https://perfetto.dev/docs/data-sources/native-heap-profiler
tags:
- memory
- pss
- memory-growth
- fragmentation
- lru-cache
- bitmap
- native-heap
related_chapters:
- '10.1'
- '10.2'
- '4.1'
- '4.3'
- '4.5'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---

# 10.3 内存持续增长

> 适用范围：Android 8.0（API 26）至 Android 17（API 37）。平台源码按 `android-17.0.0_r1` 核对；涉及物理页分配与规整时，内核源码按 `android17-6.18-2026-06_r6` 核对。

内存持续增长是一种观测现象，不对应单一故障。无上限缓存、对象泄漏、allocator（C/C++ 内存分配器）保留、直接 `mmap`（内存映射）、图形缓冲区、线程栈、WebView 预热和文件页进入驻留状态，都可能让 RSS（驻留页面总量）或 PSS（按比例分摊共享页后的内存量）上升。处理前需要回答两个问题：增长来自哪一类内存，业务生命周期结束后能回收多少。

## 1. 增长曲线能说明什么

常见来源可以按“谁持有、怎样释放”划分：

| 来源 | 典型表现 | 需要补充的证据 |
| --- | --- | --- |
| 业务 live set（仍在使用的数据集合）增长 | Java used、对象数或 Native live allocations（尚未释放的原生分配）随数据量增加 | 容量上限、对象类型、持有者、清理后的差分 |
| 泄漏 | 已结束生命周期的对象或分配持续保留 | GC Root 路径、JNI 持有者、未释放调用栈 |
| allocator retention（分配器保留）/ 页内空洞 | Native allocated 下降，Native RSS/PSS 回落较少 | 分配器统计、smaps、heapprofd 前后快照 |
| 直接 `mmap` / 文件页 | RSS 的 anon（匿名页）、file（文件页）或 shmem（共享内存页）分类增长 | `/proc/<pid>/smaps`、映射路径和创建栈 |
| Graphics / DMA-BUF（设备间共享缓冲区） | Graphics、memtrack 或相关进程增长 | Buffer、Surface、ImageReader、Codec 生命周期 |
| 线程与栈 | Threads、Stack、RssAnon 同步上升 | 线程创建栈、线程池上限、退出条件 |
| 运行时与组件预热 | 类、JIT code（即时编译代码）、WebView renderer（渲染进程）或共享库在首次使用后增加 | 稳态基线、进程列表、Code/File 页分类 |

锯齿曲线的波谷逐步升高也不能直接判定泄漏。ART 可能扩大 heap，malloc allocator 可能保留已经释放的页面，文件页和图形资源也有独立回收时机。曲线用于发现异常时段，heap dump（堆转储）、allocation profile（分配记录）和映射明细用于定位来源。

## 2. 建立可复现的增长实验

实验应固定 App 版本、设备、系统版本、ABI（应用二进制接口）、page size（内存页大小）、账号数据、网络响应和进程状态。采样点可以设置为：

1. 进程启动并完成必要预热后的基线。
2. 执行一组固定业务操作后的峰值。
3. 页面退出、任务取消、资源关闭后的状态。
4. 缓存主动收缩后的状态。
5. 再次执行同一操作后的状态。

下面的命令用于保存进程摘要、页大小、RSS 分类和线程数：

```bash
adb shell dumpsys meminfo -d com.example.app
adb shell getconf PAGE_SIZE
adb shell 'pid=$(pidof com.example.app); grep -E "VmRSS|RssAnon|RssFile|RssShmem|VmSwap|Threads" /proc/$pid/status'
```

三个采样动作应尽量靠近，但它们仍无法形成同一时刻的原子快照。报告中要保留时间、前后台状态和原始输出，避免把采样时差解释成业务增长。

### 2.1 不用一次 GC 给问题分类

点击 Memory Profiler 的 GC 按钮，只能请求一次垃圾回收。对象仍被缓存或泄漏路径持有时都会保持可达；Native、Graphics 和 `mmap` 也不受 Java GC 直接控制。因此：

- GC 后不回落，无法区分缓存与泄漏。
- GC 后回落，只能说明部分 Java 对象已经不可达。
- 清空缓存后回落，说明该缓存贡献了占用；缓存外仍可能同时存在泄漏。
- 稳定状态下的 heap dump 和 GC Root 路径，才能确认 Java 生命周期错误。

10.2 节给出了 retained object（超出预期生命周期后仍被保留的对象）的证据链。这里关注有意保留的数据如何设预算，以及对象释放后 resident memory（驻留内存）为何可能延迟回落。

## 3. 缓存必须有可执行的预算

缓存容量应由数据能否重新生成、命中收益、前后台状态和设备档位共同决定。`ActivityManager.getMemoryClass()` 描述 ART heap 的近似上限，不能当作整个进程的 PSS 预算。Graphics、Native、Code、Stack 和多进程占用都在这个数值之外。

一个可执行的缓存预算至少包含：

- hard limit：任何输入规模下都不能超过的硬上限。
- shrink target：页面隐藏或进程进入后台状态时要缩减到的目标值。
- 计量单位：字节、像素、条目或成本权重。
- owner：负责创建、收缩和销毁缓存的持有者。
- 观测值：size（当前大小）、hit（命中）、miss（未命中）、eviction（淘汰）和重建耗时。

### 3.1 Android 17 的 `LruCache`

`android.util.LruCache` 在 `android-17.0.0_r1` 中仍使用 `LinkedHashMap(..., accessOrder=true)` 维护访问顺序。`put()`、`resize()` 和 `trimToSize()` 会按 LRU（Least Recently Used，最近最少使用）顺序淘汰；`sizeOf()` 决定预算单位。

下面的缓存按 Bitmap 已分配字节计量，预算由调用方根据产品基线传入：

```kotlin
class BitmapMemoryCache(
    maxBytes: Int,
) : LruCache<String, Bitmap>(maxBytes) {

    override fun sizeOf(key: String, value: Bitmap): Int {
        return value.allocationByteCount.coerceAtLeast(1)
    }
}
```

`maxBytes` 与 `sizeOf()` 使用相同单位。缓存中的 value 若会改变计量大小，应移除后重新放入，避免 `LruCache` 内部 size 与对象状态不一致。Bitmap 的单项字节数仍受 config（像素格式）、复用分配和硬件位图路径影响；图片框架已有内存缓存时，不要再增加一层没有统一预算的进程级缓存。

`LruCache` 的 `size()` 只统计仍在 map 中的条目。条目被淘汰后，如果 Adapter、View、任务或其他集合仍保存引用，对象不会回收。排查缓存失控时，要同时查看缓存计数与 heap 中的持有者。

### 3.2 `entryRemoved()` 不是 Bitmap 回收开关

`entryRemoved()` 适合关闭条目独占的 `Closeable`、句柄或自定义资源。对 Android 8.0 及以上的普通 Bitmap，缓存淘汰时直接调用 `recycle()` 可能破坏仍在显示或被其他持有者使用的图片。引用关系结束后由运行时释放关联像素数据更安全；只有在专门的所有权协议能证明没有其他使用者时，才主动调用 `recycle()`。

### 3.3 响应 `onTrimMemory()`

Android 17 的 `ComponentCallbacks2` 仍提供 `TRIM_MEMORY_UI_HIDDEN` 和 `TRIM_MEMORY_BACKGROUND`。`TRIM_MEMORY_RUNNING_*`、`MODERATE`、`COMPLETE` 自 API 34 起不再投递给 App，并在 API 35 标为 deprecated，不能继续设计细粒度压力阶梯。

下面的回调为 UI 隐藏和进程进入后台 LRU 区域分别设置缓存目标。后台 LRU 区域是系统按最近使用顺序管理后台进程的状态：

```kotlin
override fun onTrimMemory(level: Int) {
    when {
        level >= ComponentCallbacks2.TRIM_MEMORY_BACKGROUND -> {
            imageCache.evictAll()
        }
        level >= ComponentCallbacks2.TRIM_MEMORY_UI_HIDDEN -> {
            imageCache.trimToSize(backgroundImageBudgetBytes)
        }
    }
}
```

比较使用 `>=`，以兼容可能增加的中间等级。回调只提供状态提示，不能代替应用自己的 hard limit；App 也不需要在这里主动调用 `System.gc()`。

## 4. Bitmap 与图片管线

ARGB_8888 的逻辑像素成本通常按 `width × height × 4` 估算。例如 1080 × 1920 的未压缩像素约为 7.9 MiB。压缩文件大小不能代表解码后成本，row stride（每行实际占用的字节数）、config、复用分配、硬件位图和 GPU 上传还会改变运行时占用。

Android 8.0（API 26）及以上，Bitmap 像素数据位于 Native heap。Java heap 中的 `Bitmap` 对象仍是生命周期入口，所以一张图片可能同时影响：

- Java heap：Bitmap wrapper（包装对象）、Drawable、缓存索引和业务对象。
- Native heap：像素 backing storage（底层存储）。
- Graphics：纹理、硬件缓冲区或 renderer 侧副本。

图片增长的治理顺序：

1. 按显示尺寸解码，避免让缩略图 View 持有原图像素。
2. 让一个图片库统一管理内存缓存、Bitmap 复用和请求生命周期。
3. 为预取设置窗口，列表向前滚动时淘汰窗口外请求和数据。
4. 区分 encoded bytes（压缩编码数据）、decoded pixels（解码后的像素）与 GPU 资源，三者不能只记一次 Java 对象大小。
5. 对相同 URL 的不同尺寸和变换建立可解释的 cache key（缓存键），避免重复驻留。

heapprofd 采到 Bitmap 相关 Native 分配栈时，只能确认分配来源。是否超预算还要结合缓存条目、图片规格和释放后的 live allocation 差分。

## 5. Native allocator 保留与碎片

Native 内存分析要分开三组数：

```text
live allocations
  业务仍持有、allocator 仍视为已分配的内存

allocator footprint
  live allocations + arena/cache/metadata/空闲块

resident footprint
  当前驻留的匿名页、共享页与相关映射
```

这里的 footprint 指对应统计口径下的内存占用：allocator footprint 包含分配器仍持有的空闲块，resident footprint 只计算当前驻留的页面。`Debug.getNativeHeapAllocatedSize()` 返回 allocator 计为已分配的字节；`getNativeHeapSize()` 与 `getNativeHeapFreeSize()` 反映 allocator heap 的规模与空闲量。Native PSS/RSS 还受页面是否驻留、共享映射、swap（换出内存）、直接 `mmap` 和统计时刻影响。`Native PSS - allocated bytes` 的差值包含多种来源，不能直接命名为碎片。

### 5.1 用 heapprofd 看操作差分

heapprofd 对 `malloc/free` 和 `new/delete` 采样。下面的命令定期保存 continuous dump（连续快照），便于比较业务操作前后的 live allocation：

```bash
tools/heap_profile android -n com.example.app -c 5000
```

`-c 5000` 表示 5000 ms 的快照间隔。默认 sampling interval（采样间隔）是 4096 bytes，含义是平均每分配相应字节量产生一次样本，并非按单次分配大小过滤。结果还受采集开始时刻、buffer overrun（采集缓冲区溢出）、符号化和直接 `mmap` 影响。

若 live allocations 在清理后下降而 Native RSS/PSS 保持较高，可以继续检查 allocator 保留、页内仍有其他活对象、直接映射和图形资源。若 live allocations 也沿同一调用栈增长，应回到分配持有者和释放路径。

### 5.2 降低 allocator 压力

- 固定尺寸、高频复用的音视频或网络 buffer 可以使用有上限的对象池。
- 同一阶段创建并一起销毁的对象可使用 arena/region（区域分配器），但 arena 自身也要设 hard limit。
- 每帧或每个音频包创建不同尺寸临时块，会增加 allocator 工作量；稳定的环形缓冲区通常更容易控制。
- 池化只适合复用收益高、释放点清楚的对象。池没有容量限制时，它会成为另一种缓存增长。

## 6. 进程碎片与物理页碎片是两层问题

应用常见的 malloc 碎片发生在虚拟地址空间和 allocator 管理的页面内。普通匿名内存可以由不连续的物理页映射成连续虚拟地址，因此物理页不连续通常不会直接让普通小块 `malloc` 失败。

物理页碎片影响的是高阶连续物理页需求、部分 DMA/CMA（连续内存分配器）分配、大页等路径。内核用 order 表示连续页块的阶数：order 每增加 1，页块数量翻倍。`android17-6.18-2026-06_r6` 中：

- `mm/page_alloc.c` 的 buddy allocator（伙伴分配器）按 order 管理空闲页块，并在一对相邻伙伴页块都空闲时合并。
- `mm/compaction.c` 执行 compaction（内存规整）：隔离可迁移页和空闲页，通过页面迁移形成更高 order 的空闲块。

因此，App 侧看到一次 Native 分配失败时，要区分：

| 场景 | 可能约束 |
| --- | --- |
| 64 位普通 `malloc` | allocator live set、地址空间、内存提交失败、进程或系统限制 |
| 32 位大块映射 | 连续虚拟地址范围 |
| Camera / Codec / GPU buffer | DMA-BUF、CMA、驱动与物理页条件 |
| 大页或高阶内核分配 | 伙伴分配器的空闲 order、迁移类型、compaction 成本 |

应用无法通过清缓存直接要求内核完成物理页规整。应用侧可以缩小并稳定 buffer 规格、及时关闭 Surface/Image/Codec、限制并发数量；系统或 OEM 侧则可用 page allocation 与 compaction tracepoint（跟踪点）检查高阶页分配路径。

源码核对：

- [`mm/page_alloc.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/page_alloc.c)
- [`mm/compaction.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/compaction.c)

## 7. `mmap`、Graphics 与线程栈

### 7.1 匿名映射和文件映射

`RssAnon` 增长可能来自 malloc arena、直接匿名 `mmap`、线程栈或运行时 heap；`RssFile` 增长可能来自代码、共享库和已经访问的文件页；`RssShmem` 涉及共享内存。查看 `/proc/<pid>/smaps` 的 mapping name（映射名称）、Pss、Private Dirty（进程独占且已修改的页面）和 VmFlags（映射标志），才能把页面归到创建者。

文件页在需要时可由内核回收，当前驻留不等于业务持有同等数量的脏内存。比较两次 RSS 时，要记录系统压力和进程状态。

### 7.2 Graphics 与 DMA-BUF

`Debug.MemoryInfo` 的 Graphics 摘要依赖 memtrack HAL（厂商提供的设备内存记账接口）和设备实现。Android 17 的 AIDL `IMemtrack` 负责报告 smaps 难以覆盖的 DMA-BUF PSS 与 GPU private allocation（GPU 私有分配），但设备支持度和驱动归属精度仍有差异。

排查 Graphics 增长时，优先核对 SurfaceView、TextureView、ImageReader、MediaCodec、Camera、Vulkan image 和 WebView renderer 的生命周期。平台调试环境可结合 bugreport、memtrack、SurfaceFlinger 和可用的 DMA-BUF 统计；普通 App 不应假设 `dmabuf_dump` 或特定 sysfs（内核设备与驱动信息接口）节点在所有 user build 都开放。

### 7.3 线程栈

线程创建会预留虚拟地址空间，被触碰的栈页会进入 RSS。线程池没有上限、每个会话创建专用线程、Native 库线程未退出，都可能造成阶梯增长。把 `Threads`、Stack summary 和线程名称与业务操作次数放在同一时间轴上，能很快识别这类问题。

## 8. 监控指标怎样组合

Android 17 的 `Debug.java` 提供 `getRss()`、`getPss()`、`getNativeHeapAllocatedSize()` 等接口。`getRss()` 自 API 35 公开，读取成本低于需要计算共享页分摊的 PSS；PSS 适合低频校准，不适合放进高频定时器。

推荐组合如下：

| 指标 | 用途 | 不能独自回答的问题 |
| --- | --- | --- |
| Java used / max | ART heap 使用量与预算 | 对象由谁持有 |
| Native allocated | allocator live allocation（分配器仍记为已分配的内存）规模 | Native RSS 与碎片量 |
| RSS、RssAnon、RssFile、RssShmem | 驻留趋势和大类变化 | 共享页应分给谁 |
| PSS / SwapPss | 包含共享映射分摊的内存占用校准 | LMKD 或 Memory Limiter 的唯一决策 |
| Graphics / memtrack | smaps 外的图形与设备内存 | 每台设备都完整记账 |
| Threads / Stack | 线程与已触碰栈页趋势 | 线程为何创建 |
| cache size / eviction / hit rate | 预算是否执行、收益是否存在 | 缓存外的持有者是否仍持有对象 |

线上采样应绑定业务状态变更，例如页面退出、前后台切换、长任务完成和异常阈值越过。固定秒级 PSS 轮询会增加成本，也容易得到系统缓存值。

### 8.1 4 KB 与 16 KB page size

Android 15 起，AOSP 支持 16 KB page size 设备。更大的页会改变映射对齐、尾页浪费、页表行为和 RSS/PSS 的最小变化粒度。跨设备基线应按 page size 分组，并用下面的命令记录：

```bash
adb shell getconf PAGE_SIZE
```

不能只根据页大小推导同一业务在 16 KB 设备上的内存占用变化方向；二进制对齐、mapping（映射）数量、分配形态和设备实现都会影响结果。

## 9. Android 17 App Memory Limiter

Android 17（API 37）在部分设备上启用基于设备总 RAM 档位的 App memory limits（应用内存限制）。这项行为变更对运行在 Android 17 上的 App 生效，不以 `targetSdkVersion` 为前提。平台没有向应用提供可作为通用预算的固定 MB 数。

`android-17.0.0_r1` 的 `services/core/java/com/android/server/am/MemoryLimiter.java` 显示：

- visible 与 not-visible proc state（进程状态）可以配置不同限制。
- Native 层通过 cgroup（控制组）的 `memory.high` 和 `memory.swap.high` 对进程内存及交换空间施加限制。
- 越限后系统可采集诊断数据，并根据配置终止进程。
- 功能是否启用、是否执行终止以及具体限制由设备配置和 feature flag（功能开关）决定。

若进程受此机制影响，`ApplicationExitInfo` 的 reason 为 `REASON_OTHER`，description 包含 `MemoryLimiter:AnonSwap`。分析时要区分以下三种机制：

- ART heap limit：Java/Kotlin 分配可能抛出 `OutOfMemoryError`。
- LMKD：系统内存压力下，按进程重要性与预计回收量选择要终止的进程。
- Memory Limiter：针对单个 App 进程设置 cgroup 内存与 swap 阈值。

下面的 Android 17 shell 命令用于查看支持状态，并在测试设备上施加受控限制：

```bash
adb shell am memory-limiter status
adb shell am memory-limiter manual <pid> <limit-in-mb>
adb shell am memory-limiter manual <pid> none
```

这些命令在未启用该机制的设备上没有效果。`manual` 适合验证功能降级、状态保存和重启恢复，不能用极低限制产生的数据代替正常设备基线。

Android 17 的 `ProfilingTrigger.TRIGGER_TYPE_OOM` 可请求 OOM 时的 Java heap dump；自定义 `UncaughtExceptionHandler` 必须继续调用默认 handler，否则该 trigger（触发器）无法生效。`TRIGGER_TYPE_ANOMALY` 可在系统识别异常行为时返回与异常类型对应的 artifact（诊断文件）。触发式采集有系统限流，也可能没有生成文件，结果文件还需要应用自行管理。它们用于补充线上证据，不负责判断缓存上限和引用所有权。

## 10. WebView 的进程级增长

WebView 初始化会带来 Chromium、V8、Blink、代码页、缓存和 renderer 进程成本。Android O 及以上 WebView 可使用独立的 sandboxed renderer（沙箱渲染进程）；同一应用进程中的多个 WebView 可能共享 renderer，所以单个 WebView 销毁后，renderer 的内存占用未必同步消失。

治理时注意：

- WebView 从 View hierarchy 移除且不再使用后，在创建它的线程调用 `destroy()`；调用后不能再使用该实例。
- 用 `WebViewClient.onRenderProcessGone()` 处理 renderer 退出，不能假设 renderer 永远存在。
- 多个应用进程都使用 WebView 时，要在初始化前配置各自的数据目录 suffix（后缀）；多数应用更适合只允许一个进程使用 WebView，并在其他长寿命进程调用 `WebView.disableWebView()`。
- `WebSettings` 的 cache mode、DOM storage 等开关影响页面行为和存储语义，无法提供精确的进程内存上限。
- 把 WebView 放进独立应用进程可以隔离故障，也便于按进程回收，但会增加 IPC（进程间通信）、冷启动、登录态同步和状态恢复成本，应作为架构决策评估。

WebView 基线要同时记录 App 进程、renderer 进程和 GPU/Graphics 分类。只看主进程 PSS 会漏掉一部分成本。

## 11. 长时间运行 App 的预算策略

音乐、导航、运动追踪、IM 和 RTC 场景需要把“运行时间”作为基线维度：

- 数据流使用有上限的 ring buffer（环形缓冲区）或分页窗口，历史数据及时持久化。
- 图片、地图瓦片、波形、字幕和模型缓存分别设 hard limit。
- 前台、不可见、后台服务三个状态使用不同预算。
- 音视频 codec、Surface、Image 和 Native session 由会话持有者成对关闭。
- 周期任务复用线程与 buffer，监控每轮结束后的 live set。
- 发生 Memory Limiter、LMK、OOM 或 renderer exit 后验证状态恢复，而不只验证进程存活。

预算值应来自目标设备分层和固定场景的分位数数据，并保留足够系统余量。不能复制其他产品的固定 MB 数，也不能把单台旗舰机的峰值当成全量设备安全线。

## 12. 排查路径

| 观察 | 下一份证据 | 常见治理方向 |
| --- | --- | --- |
| Java used 与对象数同增 | heap dump、dominator、GC Root | 生命周期、缓存硬上限、分页 |
| Native allocated 同调用栈增长 | heapprofd continuous dump | 释放路径、buffer 复用、池上限 |
| Native allocated 回落，RssAnon 不回落 | smaps、allocator 规模、直接 mmap | arena、页内仍存活的对象、映射释放 |
| Graphics 增长 | memtrack、Surface/Buffer 生命周期 | Image/Surface/Codec 关闭、并发限制 |
| Threads 与 Stack 增长 | 线程列表、创建栈 | 线程池上限、退出条件 |
| 主进程稳定，总 PSS 增长 | 子进程与 renderer 列表 | 多进程预算、进程生命周期 |
| Android 17 被系统终止 | `ApplicationExitInfo` description | Memory Limiter 诊断、状态恢复、降低内存预算 |

## 版本边界

- Android 8.0（API 26）起，Bitmap pixel data 位于 Native heap。
- Android 10 起，heapprofd 提供 Native allocation sampling（原生分配采样）。
- Android 14（API 34）起，App 不再收到 `TRIM_MEMORY_RUNNING_*`、`MODERATE`、`COMPLETE`；`UI_HIDDEN` 与 `BACKGROUND` 仍可使用。
- Android 15（API 35）起，AOSP 支持 16 KB page size 设备，`Debug.getRss()` 成为公开 API，`ProfilingManager` 提供 App 请求式采集。
- Android 17（API 37）在部分设备启用 App Memory Limiter，并增加 OOM 与 anomaly profiling trigger（异常分析触发器）。

## 检查清单

- 增长来自 Java、Native allocator、mmap、Graphics、线程还是其他进程？
- 基线是否排除了初始化和预热阶段？
- 业务操作、清理和采样点是否固定？
- 缓存是否有 hard limit（硬上限）、收缩目标和统一计量单位？
- `LruCache` 淘汰后是否还有其他持有者保存对象？
- Native live allocation 与 resident footprint 是否分开解释？
- 普通 malloc 碎片与内核高阶物理页碎片是否分开？
- page size、ABI、进程名和设备档位是否进入基线维度？
- Android 17 退出记录是否检查 `MemoryLimiter:AnonSwap`？
- Profiling artifact（分析产物）是否有访问控制、保留期限和失败处理？

## 与其他章节的关系

- [§10.1 App 内存分析](01-app-memory-analysis.md)：指标口径、采集工具和基线方法。
- [§10.2 内存泄漏](02-memory-leak.md)：retained object、GC Root 与 Native 未释放路径。
- [§10.6 内存抖动与频繁 GC](06-memory-churn.md)：高分配率与 GC/帧时间关联。
- [§10.7 GPU 与图形内存统计](07-gpu-graphics-memory-tracking.md)：Graphics、DMA-BUF、Surface 与 GPU 资源归因。
- [§4.5 App 内存优化](../../part1-fundamentals/ch04-memory/05-app-memory-optimization.md)：进程级内存预算与系统压力。

## 参考资料

- [AOSP `LruCache.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/util/LruCache.java)
- [AOSP `Debug.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Debug.java)
- [AOSP `ComponentCallbacks2.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/ComponentCallbacks2.java)
- [AOSP `MemoryLimiter.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryLimiter.java)
- [AOSP `ProfilingTrigger.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java)
- [Android 17：App memory limits](https://developer.android.com/about/versions/17/behavior-changes-all#app-memory-limits)
- [Android Developers：Memory allocation among processes](https://developer.android.com/topic/performance/memory-management)
- [Android Developers：Managing Bitmap Memory](https://developer.android.com/topic/performance/graphics/manage-memory)
- [Android Developers：`LruCache`](https://developer.android.com/reference/android/util/LruCache)
- [Android Developers：`ComponentCallbacks2`](https://developer.android.com/reference/android/content/ComponentCallbacks2)
- [Android Developers：WebView](https://developer.android.com/reference/android/webkit/WebView)
- [Android Developers：Support 16 KB page sizes](https://developer.android.com/guide/practices/page-sizes)
- [Perfetto：Native heap profiler](https://perfetto.dev/docs/data-sources/native-heap-profiler)
