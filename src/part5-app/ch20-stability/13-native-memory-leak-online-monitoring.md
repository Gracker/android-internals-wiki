---
title: Native 内存泄漏线上监控实战：malloc 钩子、Scudo 追踪与 mallinfo 治理
chapter: '20.13'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
tags:
- native
- memory-leak
- malloc
- Scudo
- mallinfo
- monitoring
- online
related_chapters:
- '20.3'
- '20.6'
- '20.11'
- '23.3'
- '26.14'
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
last_draft_polish_at: '2026-08-03T15:35:11+08:00'
last_draft_polish_run_id: 20260803-153511-draft-polish-5d4831f5
last_verified: '2026-08-14'
last_verified_against: Android 17 public docs (updated 2026-08-13) / android-17.0.0_r1 / android17-6.18-2026-06_r6
last_review_finalize_at: '2026-08-03T16:06:58+08:00'
last_review_finalize_run_id: 20260803-160658-53d1b7cb
confidence: high
sources:
- type: aosp
  path: bionic/libc/include/malloc.h @ android-17.0.0_r1
- type: aosp
  path: external/scudo/standalone/wrappers_c.inc @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/jni/android_os_Debug.cpp @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/jni/com_android_server_am_MemoryLimiter.cpp @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerShellCommand.java @ android-17.0.0_r1
- type: official
  path: https://developer.android.com/about/versions/17/behavior-changes-all#app-memory-limits
- type: official
  path: https://developer.android.com/ndk/guides/memory-debug
---

# Native 内存泄漏线上监控实战：malloc 钩子、Scudo 追踪与 mallinfo 治理

Native（由 C/C++ 等本地代码管理的）内存问题很少能靠一条曲线定性。`malloc` 尚未释放的字节、allocator（内存分配器）向内核映射的页、进程的 RSS（Resident Set Size，当前驻留在物理内存中的页）、按共享比例分摊后的 PSS（Proportional Set Size），以及 GPU 或 dma-buf（让进程与硬件驱动共享缓冲区的内核机制）占用，回答的是不同问题。若把它们都叫作“Native Heap”，也就是由 `malloc`、`new` 等接口管理的本地堆，告警会互相矛盾，定位也容易走偏。

平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`，讨论普通三方应用可以部署的监控方法。内核行为以 `android17-6.18-2026-06_r6` 为锚点。涉及 Android 10—16 的内容仅用于说明接口演进和兼容边界。

## 1. Android 17 让异常增长更早变成进程退出

Android 17 引入了 App Memory Limits（应用内存限制）。该变化对运行在 Android 17 上的所有应用生效，不取决于 `targetSdkVersion`，但只在实施该机制的设备上启用。限制值由设备内存和厂商配置决定，平台没有向应用承诺统一的字节阈值。

在 `android-17.0.0_r1` 中，`MemoryLimiter` 读取 `/vendor/etc/memory-limiter-config.xml`，按可见与不可见进程状态选择限制。JNI（Java Native Interface，Java 与 C/C++ 的调用桥）会操作进程所属的 cgroup v2；cgroup v2 是 Linux 按进程组统计和约束 CPU、内存等资源的接口：

- `memory.high`：设置内存高水位；越过后会触发直接回收并减慢新的内存分配，但允许用量短时超过该值；
- `memory.swap.max`：设置 swap 用量上限；swap 是被换出的匿名页，Android 设备通常由压缩内存设备 zram 承载；
- `memory.swap.current`：读取当前 swap 用量；
- `memory.stat`：读取 `anon`（匿名内存）与 `shmem`（共享内存）；
- `memory.events`：观察 `memory.high` 事件。

源码里部分 Java 注释和日志仍称 `memory.swap.high`，但 JNI 写入的文件是 `memory.swap.max`。这是系统实现细节，应用侧不应依赖具体 cgroup 文件名。

`memory.stat` 中的 `anon + shmem` 再加 `memory.swap.current` 超过组合阈值后，系统会上报 `TRIGGER_TYPE_ANOMALY`。应用若已通过 `ProfilingManager`（系统剖析服务的应用接口）注册该触发器，系统可在后台 trace（带时间轴的性能记录）正在运行且配额允许时保存诊断资料。`r1` 的 `MemoryLimiter` 随后延迟 30 秒结束进程。历史退出记录可通过 `ApplicationExitInfo`（系统保存的进程退出元数据）识别：

- `ApplicationExitInfo.reason == REASON_OTHER`；
- `ApplicationExitInfo.description` 包含 `MemoryLimiter:AnonSwap`。

下面的代码用于应用下次启动时识别最近一次是否受到 Android 17 MemoryLimiter 影响：

```kotlin
fun findRecentMemoryLimiterExit(context: Context): ApplicationExitInfo? {
    val am = context.getSystemService(ActivityManager::class.java)
    return am.getHistoricalProcessExitReasons(
        context.packageName,
        0,
        16
    ).firstOrNull { exit ->
        exit.reason == ApplicationExitInfo.REASON_OTHER &&
            exit.description?.contains("MemoryLimiter:AnonSwap") == true
    }
}
```

命中该条件只能说明系统因匿名内存和 swap 约束结束了进程，不能直接证明 `malloc` 泄漏。匿名 `mmap`、线程栈、共享内存及分配器页也可能参与增长。上报时至少应携带应用版本、ABI（Application Binary Interface，用于区分 arm64-v8a 等二进制架构）、设备型号、进程名、前后台状态、运行时长及此前采集的内存时间序列。

在支持该功能的 Android 17 设备上，可以用以下命令验证应用在约束下的行为：

```shell
adb shell am memory-limiter status
adb shell am memory-limiter manual <pid> 512
adb shell am memory-limiter ignore <uid>
adb shell am memory-limiter ignore none
```

截至 2026-08-13 的 Android 17 官方文档规定，`manual` 的数字是整数 MB，所以上例表示 512 MB。`manual <pid> max` 会移除该 PID（进程 ID）的全部内存限制，`manual <pid> none` 会清除手动覆盖并恢复系统默认限制；`ignore none` 只清除 UID（Android 用户标识符）维度的忽略设置。

首个 AOSP 标签 `android-17.0.0_r1` 与这份公开契约存在实现差异：shell help 把数字写成总 RAM 百分比，执行路径却按 MiB（1,048,576 字节）放大；parser（命令参数解析器）不接受 `max`，还会先把 `none` 对应的 `-1` 乘以 `1 MiB`，导致 native 层忽略这次更新。这是 `r1` 的源码审计结论，不能据此推断后续 Android 17 构建也有相同行为。测试前应记录设备 build fingerprint（系统构建指纹），并用设备上的 help 与 `status` 核对实际实现；若使用基于 `r1` 的调试镜像，重启目标进程可让新 PID 重新取得默认限制。

这些命令在未启用 MemoryLimiter 的设备上没有效果。测试目标应是确认监控数据能在退出前解释增长，以及重启后能关联退出原因，不要把压低阈值后的退出直接归类为泄漏。

## 2. 先给各类“内存”划清边界

一次采样建议至少保留下列维度。表中的 live 指分配器仍记为“在用”，mapped/retained 指已经向内核映射或释放后仍由分配器保留，owner counter 指业务组件自行维护的资源计数。Perfetto 是 Android 的系统追踪与性能分析框架：

| 维度 | 典型来源 | 能回答的问题 | 不能回答的问题 |
| --- | --- | --- | --- |
| allocator live bytes（在用字节） | `mallinfo().uordblks`、`Debug.getNativeHeapAllocatedSize()` | 当前分配器认为仍在用的总字节数 | 哪个对象应当释放；匿名 `mmap` 或 GPU 占用 |
| allocator mapped/retained（映射/保留字节） | `mallinfo()`、`malloc_info()` | 分配器映射、空闲和保留页的大致状态 | 页是否全部驻留；业务所有者 |
| RSS | `/proc/self/status`、Perfetto RSS 计数器 | 进程当前驻留在物理内存的页 | 共享页归属；分配调用栈 |
| PSS | `smaps_rollup`、`dumpsys meminfo` | 把共享页按映射数分摊后的进程占用 | 一次分配的调用栈；业务生命周期 |
| VMA（Virtual Memory Area，虚拟内存区域）分类 | `/proc/self/smaps`、`dumpsys meminfo` | `[anon:scudo:*]`、文件映射、栈等增长在哪类映射 | allocator 内每个存活对象的所有者 |
| sampled allocations（采样分配） | heapprofd | 采样窗口内分配与释放的调用栈 | 未采到的小对象；绕过 `malloc` 的分配 |
| owner counters（所有者计数器） | 图片池、解码器、媒体组件、自研 arena（从大块内存中二次分配的内存池） | 资源数量、字节数和业务场景 | 未接入组件的系统级总量 |

这里有三个很常见的误判：

1. **RSS 上升不等于泄漏。** 新触达的代码页、文件页、线程栈和 allocator 保留页都会抬高 RSS。
2. **`uordblks` 回落而 RSS 不回落，不等于 `free()` 失效。** Scudo 可以保留已释放页供后续复用，是否归还内核还受尺寸、碎片和 release（把空闲页归还内核）策略影响。
3. **Native Heap 平稳不等于 Native 资源平稳。** `mmap(MAP_ANONYMOUS)` 的自研内存池、GraphicBuffer、AHardwareBuffer、dma-buf 与驱动内存可能绕过 `malloc`。

因此，线上监控要同时回答两个问题：“哪类内存在增长”和“增长是否脱离业务生命周期”。单个数值无法完成这两个判断。

## 3. `mallinfo`：便宜的趋势计数器，不是泄漏证明

### 3.1 Android 17 中 `mallinfo2()` 没有独立实现

Android 17 bionic（Android 的 C 标准库）的 `<malloc.h>` 中，`struct mallinfo` 的字段已经是 `size_t`。`struct mallinfo2` 具有相同字段布局，`mallinfo2()` 通过 `__RENAME(mallinfo)` 指向同一个 `mallinfo` 符号。它并没有一条“Android 12 以后才提供、专门解决 64 位溢出”的独立运行时路径。

这与 glibc（GNU C 标准库）历史上 `mallinfo` 使用窄整数的背景不同。移植跨平台代码时不要把 glibc 的版本规则直接套到 bionic。

Android 17 的 Scudo C 包装层按以下方式填充主要字段：

- `uordblks`：allocated bytes；
- `fordblks`：free bytes；
- `hblkhd`：mapped bytes；
- `usmblks`：同样取 mapped bytes；
- `fsmblks`：free bytes。

这些是 allocator 统计，不是进程的 RSS/PSS。bionic 头文件也明确把 `mallinfo()` 和 `mallinfo2()` 标为“inherently unreliable”，建议需要更多信息时考虑 `malloc_info()`；这句话提醒调用方不要依赖跨 allocator 的精确语义。在 allocator 和配置保持一致时，这些计数器仍可用于观察趋势。

下面的 C++ 代码用于低频采集当前 allocator 的三个基础指标：

```cpp
#include <malloc.h>
#include <cstdint>

struct NativeAllocatorSnapshot {
    uint64_t allocated_bytes;
    uint64_t free_bytes;
    uint64_t mapped_bytes;
};

NativeAllocatorSnapshot ReadNativeAllocatorSnapshot() {
    const struct mallinfo info = mallinfo();
    return {
        .allocated_bytes = static_cast<uint64_t>(info.uordblks),
        .free_bytes = static_cast<uint64_t>(info.fordblks),
        .mapped_bytes = static_cast<uint64_t>(info.hblkhd),
    };
}
```

采样函数没有执行栈回溯、磁盘 I/O 或网络上传，适合放在独立监控线程中按秒级或分钟级间隔调用。业务代码应把结果与单调时钟（只向前推进、不受系统时间调整影响的时钟）、进程状态和业务场景一起记录，单独保存某个时刻的绝对值无法呈现趋势。

Java 层的 `Debug.getNativeHeapAllocatedSize()` 也没有提供更宽的覆盖面。`android-17.0.0_r1` 的 `android_os_Debug.cpp` 直接调用 `mallinfo()` 并返回 `uordblks`；`getNativeHeapSize()` 返回 `usmblks`，`getNativeHeapFreeSize()` 返回 `fordblks`。它们仍是当前 malloc dispatch（当前生效的分配函数转发表）的视角。

### 3.2 sanitizer（内存错误检测工具）与 hook 会改变可观测结果

bionic 通过 `MallocDispatch` 转发 `mallinfo`、`malloc_info` 和 `mallopt`。当 heapprofd、GWP-ASan（对少量堆分配启用保护检查的低开销工具）或其他受支持的 malloc dispatch 处于工作状态时，统计由当前 dispatch 路径提供。HWASan（Hardware-assisted AddressSanitizer，硬件辅助内存错误检测工具）路径中的 `__sanitizer_malloc_info()` 会返回 `-1` 并把 `errno`（C 接口保存最近一次错误原因的线程局部变量）设置为 `ENOTSUP`，相关统计也可能不可用。

采集端必须允许“无数据”：

- 不要把 0 自动解释成没有分配；
- 记录 sanitizer、GWP-ASan 和 profiler 是否开启；
- 灰度组之间比较时保持构建类型、ABI 与 allocator 配置一致；
- 对 `malloc_info()` 检查返回值和 `errno`。

### 3.3 `malloc_info()` 的 XML 不是稳定业务协议

`malloc_info(int options, FILE* fp)` 在 bionic 中从 API 23 可用。Android 17 Scudo 输出的结构以 `<malloc version="scudo-1">` 开头，并按 size/count 列出当前分配；它与旧版 jemalloc 示例中的 arena、bin（按尺寸组织分配块的内部类别）XML 结构不同。

Scudo 实现还会分配临时尺寸数组、暂停 allocator 并遍历 chunks（分配器管理的内存块）。因此，`malloc_info()` 不适合信号处理器，也不应作为高频心跳。更合适的用途是：低内存告警后在安全线程执行一次，保存原始 XML 文本，并让解析器按 allocator/version 分派。

若监控平台只需要稳定趋势，优先保存 `uordblks`、RSS/PSS 和 owner counters。XML 是诊断附件，不要把某个 XML 节点写成长期兼容的告警字段。

## 4. RSS、PSS 与 `smaps`：判断增长落在哪类映射

### 4.1 `smaps_rollup` 只有总览

`/proc/self/smaps_rollup` 汇总进程所有 VMA 的 RSS、PSS、共享/私有页、匿名页和 swap 等数据。它输出的文本比完整 `smaps` 少，但内核仍需遍历页表完成统计，因此不应放在每帧或其他高频热路径。

`smaps_rollup` 的 PSS 也不能命名为 `PSS-Native`。它包含 Java 堆、Native allocator、线程栈、代码、文件映射和其他进程映射。要做类别拆分，需要读取完整 `smaps`，或使用系统已做分类的 `dumpsys meminfo`/Perfetto 数据。

### 4.2 `[heap]` 不是全部 Native Heap

现代 Android 上，Scudo 会创建带名称的匿名映射，例如 `[anon:scudo:*]`。GWP-ASan 也有自己的匿名映射。只累计传统 `[heap]` VMA 会漏掉大部分 allocator 区域。

完整 `smaps` 的分类建议按“映射语义”而非固定单一名称进行：

- `[anon:libc_malloc]`、`[anon:scudo:*]`、GWP-ASan 区域：allocator 相关；
- `[stack]` 与线程栈：线程数量和栈提交；
- `dalvik-*`、ART space：托管堆和 ART（Android Runtime）自身的内存区域；
- `.so`、`.dex`、`.oat`、`.art`：代码和文件映射；
- 业务命名的匿名 VMA：自研 arena、缓存或引擎内存；
- dmabuf、GraphicBuffer、GPU：结合系统服务和组件计数器分析。

VMA 名称会随版本和 allocator 变化。解析器应保留原始名称，并把无法识别的项归入 `other_anon` 或 `other_file`，不要静默丢弃。

### 4.3 用时间窗口看“能否回到基线”，不要用一个固定阈值

建议为每个进程构建场景化时间线：

1. 冷启动完成；
2. 核心场景预热完成；
3. 前后台切换并等待缓存清理；
4. 重复同一场景若干轮；
5. 回到相同稳态后再次采样。

比较点必须具有相近的页面、网络、播放和前后台状态。启动后 1 分钟、10 分钟、1 小时的固定时刻只适合连续使用场景；若用户行为不同，时间点本身没有可比性。

线上告警可以同时观察：

- `allocated_bytes` 的稳态斜率；
- `RSS - Java committed` 的增长斜率；这里的 Java committed 是虚拟机已经为 Java 堆承诺、可以直接使用的容量，不等于当前存活对象大小；
- 多轮场景后的回落幅度；
- owner counter 与 allocator 增量是否一致；
- 相同版本、设备档位、ABI 和场景下的分位数变化。

单设备连续增长适合触发诊断，版本级回归则要看同版本、同设备档位等可比样本组（cohort）的分布。千万级 DAU（日活跃用户数）会让很小的差异也具有统计显著性，因此还应设置工程意义阈值，例如 P95（95% 样本不超过的分位值）增量、退出率和持续增长时长。p-value 只表示在“没有差异”的假设下出现当前或更极端结果的概率，数值小不代表差异一定值得工程介入。

## 5. malloc/free hook：覆盖范围比“能否 hook”更重要

### 5.1 PLT hook 只能改写选定 ELF 的导入跳转

xhook、bhook 一类方案通常修改 ELF 模块的 PLT/GOT relocation（动态链接器用于解析外部函数地址的跳转表重定位项），使该模块对 `malloc`、`free` 等导入符号的调用进入代理函数。ELF 是 Android Native 可执行文件与 `.so` 使用的二进制格式。这类 hook 只改写命中的导入调用，覆盖范围达不到进程级 allocator 替换，Android 平台也没有承诺其为稳定 API。

Android 8 以后，linker namespace（动态链接器的库隔离空间）会影响库的可见性、加载和符号解析，但不存在一个简单的“namespace 开关把 PLT hook 全部禁用”。是否能覆盖取决于：

- 目标函数是否经由可改写的 PLT relocation 调用；
- 模块是否已加载，后续加载模块是否会被注册；
- 调用是否被静态链接、内联、本地绑定或隐藏；
- 库是否使用自研 allocator；
- Android 版本、RELRO（把重定位完成后的相关内存改成只读的加固机制）与 hook 库自身的兼容性。

不要把访问 linker 私有结构或绕过 namespace 限制作为线上监控的主要实现。私有实现不受 NDK ABI 兼容性承诺保护，系统升级后可能直接崩溃。

### 5.2 只 hook `malloc/free` 会形成错误账本

若目标是维护“仍存活的分配”，至少要处理：

- `malloc`、`calloc`、`realloc`、`free`；
- `posix_memalign`、`aligned_alloc`、`memalign` 等对齐分配；
- C++ `new/delete`、数组和 sized/aligned delete 变体；
- 模块动态加载与卸载；
- 地址复用和重复事件。

`realloc` 尤其容易写错：

- 输入指针为 `nullptr` 时等价于分配；
- 失败返回 `nullptr` 时，旧分配仍然有效；
- 成功时地址可能不变，也可能搬迁；
- size 为 0 的行为不宜脱离当前 libc 契约自行假定。

账本不能只用裸指针地址作为 key（索引键）。地址释放后会被复用，事件还可能因异步消费而乱序。记录中应包含单调时间、分配序号、线程 ID、尺寸、模块 Build ID（标识某次二进制构建的 ID）和原始 PC（Program Counter，指令地址），使消费端能区分同一地址在不同分配周期中的事件。

### 5.3 hook 热路径必须比被观测代码更克制

代理函数内不能再走可能分配内存的路径。`std::string`、普通容器、日志格式化、在线符号化、文件 I/O 和完整 unwind（从当前栈帧逐层还原调用链）都可能递归进入 allocator。

稳妥的事件路径通常包含：

- TLS（Thread-Local Storage，线程局部存储）重入标记；
- 预分配的有界 ring buffer（容量固定、首尾相接的环形缓冲区）；
- 原子写入的固定长度事件；
- 少量原始 PC，或仅记录返回地址；
- 单独消费者线程；
- 离线按 Build ID 符号化，也就是把指令地址还原成对应版本的函数和源码位置；
- 缓冲区满时丢弃并计数，不阻塞分配线程。

完整调用栈若必须在线采集，需要结合 [20.3 Native Crash、堆栈回溯与符号化](03-native-crash-unwinding-symbolication.md) 评估 unwind 的安全性与成本。hook 自身还应具备远程关闭、时限、进程白名单和崩溃熔断；这里的熔断指诊断功能引发异常达到阈值后自动关闭，避免扩大故障面。

### 5.4 “每 1000 次取 1 次”不是通用采样答案

固定按事件计数采样会偏向高频小对象：一次 64 MiB 分配与一次 32 B 分配拥有相同入样概率。若要估算字节归因，可按尺寸分层，或使用以分配字节为权重的随机采样，并在服务端用每条记录的采样概率反推总体规模。

低采样率还会遇到配对问题。若分配事件未采到而释放事件采到，不能从账本删除未知对象；若只对分配采样，则应给入样对象建立专用追踪状态，释放时查询这一状态。任何估算都要附带样本数和采样概率。

自建 PLT hook 适用于已知模块、受控灰度（仅向小比例设备启用）和特定问题复现。需要通用的 sampled allocation stack（采样分配调用栈）时，平台的 heapprofd 通常更可靠。

## 6. heapprofd：按触发采样调用栈

heapprofd 是 Perfetto 的 Native 堆采样器，从 Android 10 起提供。Android 17 继续完善平台剖析 API、触发机制和生产部署路径。

在 bionic 中，heapprofd 接入 `MallocDispatch`。Android 17 的 `malloc_heapprofd.cpp` 会检查其他 hook，并可在保留 GWP-ASan backing allocator（GWP-ASan 下层继续负责实际分配的 allocator）的情况下接入。这与修改各 ELF PLT 的第三方 hook 路径不同。

heapprofd 能提供：

- 采样分配与释放的 Native 调用栈；
- 分配大小、进程、线程和时间信息；
- 按栈聚合的 allocated（已分配）、freed（已释放）与 unreleased（采样窗口内尚未匹配到释放）视图；
- Perfetto trace 中与进程时间线的关联。

它仍有清晰边界：

- profile 开始前已经存在的分配无法补回原始分配栈；
- 采样可能漏掉小对象，结果需要按采样权重解释；
- 直接 `mmap`、自研 arena 内部切分、GPU 与 AHardwareBuffer 不经过 malloc 时不可见；
- `unreleased` 表示采样窗口内尚未匹配到 free 的分配，不等同于从所有业务根不可达；
- 它没有 Java 对象到 Native 资源的所有权引用图。

生产环境更适合在异常趋势、MemoryLimiter anomaly（内存限制异常触发）或灰度命中后开启短窗口采样。持续高频 profiling（性能剖析）会增加 CPU、内存、trace 存储和隐私成本。

Android 15 / API 35 起，普通应用可通过 `ProfilingManager` 请求受系统管理的 heap profile（堆剖析）。Android 10—14 中，能否采集取决于应用是否声明 `profileable`、是否为 `debuggable` 调试构建，以及请求是否由 shell 发起；完整配置见 [26.14 heapprofd、procfs CPU 与 Page Fault 分析](../ch26-observability/14-heapprofd-procfs-page-fault.md)。实施时应复用该章已经验证的权限模型、guardrail（平台为控制开销设置的采样护栏）和符号化流程，不要再维护一套私有规则。

## 7. Scudo、GWP-ASan、HWASan、MTE 各自查什么

Android 11 起，Scudo 用于大多数 Android Native 分配；低内存设备仍可能使用 jemalloc。Scudo 是 hardened allocator（通过完整性检查、隔离和随机化降低堆破坏风险的分配器），不会自动给出泄漏对象及其业务所有者。

| 工具 | 适用环境 | 主要能力 | 对普通泄漏的能力 |
| --- | --- | --- | --- |
| Scudo | 日常系统与应用进程 | allocator 安全加固、部分错误检测、统计与释放策略 | 只给 allocator 视角，不给业务所有权 |
| GWP-ASan | 生产小概率采样 | 捕获被采中对象的 heap UAF（Use After Free，释放后使用）和越界 | 不负责检测普通泄漏 |
| HWASan | 自动化测试、fuzz（模糊测试）、dogfood（团队内部试用） | 高覆盖 UAF、越界和栈错误 | 不是低开销线上泄漏监控 |
| MTE（Memory Tagging Extension，内存标签扩展） | 支持硬件与系统配置的 64 位设备 | 用硬件内存标签辅助发现或缓解内存破坏 | 不提供泄漏引用图 |
| ASan（AddressSanitizer，内存错误检测工具） | HWASan 不可用的测试场景 | 传统地址检查 | 已被替代，不适合线上 |
| heapprofd | 灰度或异常触发的采样窗口 | malloc 分配/释放调用栈 | 可定位未释放增长，但结论需结合生命周期 |

有三处版本边界值得单独说明：

- HWASan 的 NDK 支持可追溯到 NDK r21 / API 29；到 API 34 与 NDK r26 之前，部署通常需要兼容的系统镜像。它不是“Android 14 才出现的 ARM MTE”。
- MTE 依赖 Arm 硬件标签能力、64 位进程与设备系统配置。它和编译器插桩的 HWASan 是两条路径。
- ASan 官方已标为被其他工具取代。官方给出的量级约为 CPU +100%、代码 +50%、内存 +100%，不能写成所有应用固定“2—3 倍”。

HWASan 官方给出的典型成本约为 CPU +100%、代码 +50%、内存 +10%—35%，仍应以应用实测为准。GWP-ASan 的生产灰度、MTE 配置与两类报告的差异统一见 [20.6 MTE 与 GWP-ASan Native 内存安全检测](06-mte-gwp-asan-native-memory-safety.md)。

## 8. Scudo 选项与 `mallopt`：调 allocator，不是修泄漏

Scudo 支持通过 `__scudo_default_options()` 或 `SCUDO_OPTIONS` 配置部分行为。这适用于可控的 Native 进程、测试构建或系统组件；由 Zygote（预加载公共资源并派生应用进程的父进程）启动的普通三方应用不应把环境变量当作可远程切换的线上开关。

Android 17 没有公布名为 `options=scudo_options` 的 Scudo 配置语法。选项名称和默认值也可能随平台构建变化，使用前要以目标版本的 Scudo 文档和源码为准。

bionic 对外提供的 `mallopt` 命令更适合应用代码调用。这里的 decay 指空闲页等待自动归还内核的时间策略，purge 指主动请求归还当前可释放的空闲页：

- `M_DECAY_TIME`：API 27 起调整 decay 时间；
- `M_PURGE`：API 28 起请求释放空闲内存；
- `M_PURGE_ALL`：API 34 起请求更广的 purge；
- `M_PURGE_FAST`：API 37 新增，以较低成本快速释放部分空闲页，可能少于普通 purge。

下面的代码用于 Android 17 设备在明确的低频生命周期节点请求快速 purge：

```cpp
#include <android/api-level.h>
#include <malloc.h>

bool RequestFastNativeHeapPurge() {
    if (android_get_device_api_level() < 37) {
        return false;
    }
    return mallopt(M_PURGE_FAST, 0) == 1;
}
```

这段代码要求以 API 37 头文件编译，并在调用前检查设备 API。`mallopt` 符号早于 API 37 已存在，Android 17 新增的是 `M_PURGE_FAST` 命令值；只有 API 37 及以上设备可以执行该调用。

purge 只能尝试把 allocator 中已经空闲且可归还的页交回内核。仍被引用的泄漏块不会因此消失，碎片也可能让一部分页无法释放。若每次 purge 后 RSS 暂时下降又持续上升，应继续查对象生命周期；不要把周期性 purge 当作修复。

## 9. `mmap`、自研内存池和图形内存必须另建账

游戏引擎、数据库、媒体栈和模型推理库常用 `mmap(MAP_ANONYMOUS)` 直接创建匿名虚拟内存映射，再由内部 arena 切分。heapprofd 和 malloc hook 最多看到 arena 的外层申请；如果外层直接走 `mmap`，两者都看不到。

自研组件应在资源所有者一侧记录：

- `mmap/munmap` 的地址、长度、保护位和用途；
- arena committed（已向系统取得）、used（业务正在使用）、free（池内空闲）和 high-water mark（历史峰值）；
- 缓存条目数量、预算、逐出原因；
- 关联场景、实例 ID 和生命周期；
- VMA 命名，便于 `smaps` 与 Perfetto 分类。

不要在进程中无差别 hook 所有 `mmap` 后就把结果称为业务泄漏。运行时、linker、线程栈、JIT（运行时即时编译器）、文件映射和系统库都会使用 mmap；必须结合 flags（映射标志）、fd（文件描述符）、VMA 名称与 owner events（业务所有者记录的申请/释放事件）分类。

截至 2026-08-14，在 Android 公开 NDK、Perfetto 文档和 AOSP Android 17 源码中，没有找到可供应用使用、名为“Kohanakai / Android 14+ mmap tracking”的工具或 API。缺少明确源码路径、接口契约和发布说明时，不应把这个名称写入生产设计。可验证的路径包括 owner 侧 mmap 记账、`smaps`/VMA 分类、Perfetto RSS 数据和组件自身统计。

## 10. 三类常见案例怎样建立证据

### 10.1 图片与 Bitmap

Android 8 以后，Bitmap pixel data（像素数据）通常由 Native 内存承载，但 Java `Bitmap`、Drawable、图片缓存和解码任务仍可能掌握所有权。排查时需要同时观察：

- Java `Bitmap` 数量及 retaining path（从 GC Root 到该对象的强引用链）；
- 图片缓存 current/max bytes、命中和逐出；
- Native allocator 或图形内存增长；
- 页面退出、请求取消、进程后台后的回落；
- 硬件 Bitmap、GraphicBuffer 与普通软件 Bitmap 的差异。

“Native Bitmap 增长”不能直接写成“Skia 对象未释放”。先查 Java owner、缓存预算与解码生命周期；若 Java owner 已消失而 Native 内存仍增长，再用 heapprofd、图形内存统计和平台 trace 缩小范围。更多版本差异见 [23.2 Bitmap 与图片内存优化](../ch23-memory-practice/02-bitmap-optimization.md)。

### 10.2 第三方 SDK

第三方 `.so` 持续增长时，诊断包至少保留 SDK 版本、ABI、模块 Build ID、进程、初始化次数和采样栈。若 heapprofd 栈停在 SDK 导出函数，应让供应方用相同 Build ID 的未裁剪符号文件还原；仅靠函数地址无法跨版本比较。

也要验证 SDK 是否使用自研 allocator 或直接 mmap。malloc hook 没有记录不代表它没有分配，只有“目标调用不在当前 hook 覆盖范围内”这一层含义。

### 10.3 音视频与相机

媒体内存可能分布在 malloc buffer、codec buffer（编解码器缓冲区）、Image、GraphicBuffer、AHardwareBuffer、共享内存和驱动侧。排查步骤应从 owner（负责创建、持有和释放资源的组件）开始：

- `MediaCodec`、`Image`、`ImageReader` 是否按生命周期 `close()`/`release()`；
- 队列中 outstanding buffer（已经交出、尚未归还的缓冲区）数量是否持续增加；
- 解码分辨率、并发路数和缓冲深度是否变化；
- allocator live bytes、graphics/dmabuf 与 mmap 哪一类在增长；
- stop/release 后资源是否回到可复用基线。

若 heapprofd 平稳但 graphics/dmabuf 上升，应转向 buffer queue（生产者与消费者之间传递图形缓冲区的队列）、fence（表示 GPU/显示操作何时完成的同步对象）和组件释放路径；继续加大 malloc 采样率不会增加有效证据。

## 11. 一套可运行的线上监控分层

L0—L3 表示采集成本和证据深度逐层增加，不表示事故严重等级。L0 常驻，L1 确认增长类别，L2 定位调用栈，L3 回到测试环境复现。

### 11.1 L0：常驻低成本指标

按进程和场景采集：

- `mallinfo().uordblks`；
- RSS，必要时低频 PSS；
- Java heap committed/used；
- 线程数；
- 图片、媒体、自研 arena 等 owner counters；
- 前后台状态、页面、运行时长和版本维度。

采样周期由性能测试决定。前台活跃时可相对密集，后台稳态降低频率；任何采集都不能阻塞主线程。

### 11.2 L1：异常确认

当连续窗口斜率异常、回落不足，或同类样本的分位数比上一版本变差时：

- 追加一次 `smaps_rollup`；
- 在允许的诊断环境保存完整 `smaps`；
- 采集 `malloc_info()` 附件；
- 提高 owner counter 频率；
- 记录 MemoryLimiter 状态和历史退出原因。

这一层的目标是把问题归为 allocator、mmap、graphics、线程栈或文件映射等类别。

### 11.3 L2：调用栈定位

按设备、版本、渠道和进程灰度：

- heapprofd 短窗口；
- 受控模块的 malloc hook；
- 针对自研 arena 的 owner allocation events；
- 保留 Build ID 的 Native 符号化。

诊断开始和结束都要记录边界，避免把窗口外存量解释成窗口内泄漏。

### 11.4 L3：测试环境复现

把线上场景带回自动化测试、fuzz 或 dogfood：

- HWASan 查 UAF、越界和栈错误；
- MTE 在支持设备上查标签错误；
- GWP-ASan 验证线上低概率出现的堆内存安全崩溃；
- ASan 只用于其他方案不可用的兼容场景；
- 循环场景并验证回到同一稳态后的内存差值。

工具命中的是内存安全错误时，应按崩溃证据修复；只有稳定增长、未释放栈与业务生命周期互相吻合时，才可以把结论写成泄漏。

## 12. 评审清单

上线一套 Native 内存监控前，逐项回答：

- 指标测的是 allocator、RSS、PSS、VMA、graphics 还是业务 owner？
- `Debug.getNativeHeapAllocatedSize()` 是否被错误命名成“全部 Native 内存”？
- `mallinfo` 在当前 allocator/sanitizer 组合下是否可用？
- `malloc_info` 解析器是否按 allocator/version 区分，并保留原始输出？
- PLT hook 覆盖了哪些模块和分配 API，明确漏掉哪些路径？
- hook 是否有重入保护、有界缓冲、丢弃计数、远程关闭和崩溃熔断？
- 采样概率是否与尺寸分布匹配，服务端是否正确加权？
- heapprofd 窗口、Build ID、符号文件和 profileable 权限是否匹配？
- `mmap`、图形、媒体和自研池是否有 owner counters？
- 告警比较的场景与进程状态是否一致？
- Android 17 MemoryLimiter 退出是否通过 `ApplicationExitInfo` 单独归因？
- purge 是否只作为释放空闲页的动作，而没有被包装成泄漏修复？

## 13. 源码锚点与参考资料

### 13.1 Android 17 / `android-17.0.0_r1`

- [bionic `malloc.h`](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/include/malloc.h)：`mallinfo`/`mallinfo2`、`malloc_info`、`mallopt` 与 API 级别。
- [bionic `malloc_common.cpp`](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/malloc_common.cpp)：malloc dispatch 和统计接口转发。
- [bionic `malloc_heapprofd.cpp`](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/malloc_heapprofd.cpp)：heapprofd hook、兼容性检查及 GWP-ASan backing allocator。
- [Scudo `wrappers_c.inc`](https://android.googlesource.com/platform/external/scudo/+/refs/tags/android-17.0.0_r1/standalone/wrappers_c.inc)：Scudo 的 `mallinfo`、`malloc_info` 和 purge 实现。
- [frameworks/base `android_os_Debug.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/jni/android_os_Debug.cpp)：`Debug.getNativeHeap*()` 到 `mallinfo` 字段的映射。
- [frameworks/base `MemoryLimiter.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryLimiter.java)：配置、进程状态、异常剖析、延迟结束与退出描述。
- [frameworks/base `ActivityManagerShellCommand.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerShellCommand.java)：`memory-limiter` 测试命令的参数解析与 help 文案差异。
- [frameworks/base `MemoryLimiter.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/jni/com_android_server_am_MemoryLimiter.cpp)：cgroup v2 文件、事件与限制写入。
- [common kernel `cgroup-v2.rst`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/admin-guide/cgroup-v2.rst)：`memory.high`、`memory.swap.max` 与内存控制器语义。

### 13.2 官方指南

- [Android 17：App memory limits](https://developer.android.com/about/versions/17/behavior-changes-all#app-memory-limits)
- [Android：Trigger-based profiling](https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture)
- [Android NDK：Memory error debugging and mitigation](https://developer.android.com/ndk/guides/memory-debug)
- [AOSP：Scudo](https://source.android.com/docs/security/test/scudo)
- [Android 游戏内存管理](https://developer.android.com/games/optimize/memory-allocation)
- [Android 游戏：Low memory killers 与诊断工具](https://developer.android.com/games/optimize/vitals/lmk)
- [Android 应用内存管理](https://developer.android.com/topic/performance/memory-management)

这些资料给出的边界是一致的：低成本计数器负责发现异常，带调用栈的采样负责定位增长来源，owner 生命周期用于证明资源是否错过释放时机，内存安全工具负责发现越界和释放后使用。分别保存这四类证据，才能在 Scudo、mmap、图形内存和 Android 17 MemoryLimiter 同时存在时得到可复核的结论。
