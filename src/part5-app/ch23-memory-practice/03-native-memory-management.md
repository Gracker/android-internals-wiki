---

title: "Native 内存管理与优化"
chapter: "23.3"
section: "23.3"
status: finalized
drafted_date: "2026-05-14"
reviewed_date: 2026-06-08
reviewed_by: openclaw-task6
task6_result: pass-light-edit
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-11"
last_verified_against: "AOSP android-17.0.0_r1 / Android Developers docs / Perfetto docs"
confidence: medium
polish_count: 1
sources:
  - type: official
    path: "https://source.android.com/docs/core/tests/debug/native-memory"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/native-heap-profiler"
  - type: official
    path: "https://developer.android.com/ndk/guides/memory-debug"
  - type: official
    path: "https://developer.android.com/ndk/guides/arm-mte"
  - type: official
    path: "https://developer.android.com/ndk/guides/gwp-asan"
  - type: aosp
    path: "android.googlesource.com/platform/bionic/+/android-17.0.0_r1/libc/malloc_debug/README.md"
  - type: aosp
    path: "android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/jni/android_os_Debug.cpp"
  - type: aosp
    path: "android.googlesource.com/platform/system/memory/libmeminfo/+/android-17.0.0_r1/androidprocheaps.cpp"
  - type: official
    path: "https://source.android.com/docs/security/test/scudo"
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
  - type: blog
    path: "Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md"
tags: [native-memory, malloc, asan, hwasan, so-memory]
related_chapters: ["23.2", "4.1", "4.2", "10.1", "14.5"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
task6_review_notes: "2026-05-14 task6 review: 修正 malloc_debug 限制表述，替换禁用语境下的抽象词；四层质检通过，无新增 L3/L4 回炉项，等待 Task9 review。 | 2026-06-08 Task6 (revisiting→finalized): pass-light-edit. Task9 auto-fixed malloc_debug nested quotes + AOSP anchor downgrade. L1/L2 clean. No B-class issues. Auto-promoted: task6=pass-light-edit, task9=auto-fixed, queue clear."
last_task6_review_log: logs/review/2026-06-08-04-review.md
last_task6_at: "2026-06-08T04:12:56+08:00"
last_task6_audit: "2026-06-06"
task9_result: auto-fixed
task9_reviewed_date: 2026-05-14
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-08T03:20:00+08:00"
last_task9_autofix_at: "2026-06-08"
last_task9_audit: "2026-06-08"
last_task9_review_log: logs/deep-review/2026-06-08-03-audit.md
task9_review_notes: "2026-05-14 Task9 01:41：pass-tech-review。无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。本轮 P2 源码锚点补充已写入 suggestions.md。 | 2026-06-08 Task9 idle audit 03:20:auto-fixed。P0 1 / P1 0 / P2 1; 修正 malloc_debug wrap.<APP> 示例缺少嵌套引号的问题，并将旧 AOSP 锚点降到 android-16.0.0_r1；回到 Task6 复审。"
task2b_result: fixed
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-11
consolidated_from:
  - "src/part5-app/ch23-memory-practice/08-memory-case-studies.md"
  - "src/part5-app/ch23-memory-practice/11-scudo-native-heap-allocator.md"
---

# Native 内存管理与优化

> **版本基线**
>
> 平台源码统一以 Android 17 / API 37 / `android-17.0.0_r1` 为锚点。涉及 `/proc`、VMA 与内核统计接口时，以 `android17-6.18-2026-06_r6` 为内核侧基线。旧版本只用于说明能力的引入时间，不作为当前实现依据。

## 为什么要处理 Native 内存

Java Heap 没有持续增长，不代表进程的内存占用稳定。使用 JNI、音视频 SDK、地图 SDK、游戏引擎、图片库或加密库的应用，Native Heap、匿名 `mmap`、共享库映射和图形缓冲都可能让 PSS 上升。后果可能是后台进程更早被回收、前台发生内存压力或 native crash。

应用侧排查先确认增长属于哪一种系统统计，再按问题类型选择 heapprofd、`libmemunreachable`、malloc_debug、ASan、HWASan、GWP-ASan 或 MTE。容量问题与非法访问需要不同证据：前者关注分配栈和存活量，后者关注越界、释放后访问等错误现场。底层内存模型详见 4.1、4.2 节，工具细节详见 14.5 节。

## Native 内存由哪些部分组成

应用侧讨论 Native 内存时，容易把所有非 Java Heap 的增长都归到 `malloc`。排查时要拆开看，至少分四类：

- **Native Heap**：C/C++ 代码通过 `malloc`、`calloc`、`realloc`、`new` 申请的堆内存，常见来源是 JNI 层业务代码、第三方 so、音视频编解码、图片库和加密库。
- **匿名 `mmap` 区域**：代码直接用 `mmap` 申请的私有匿名映射，或者 allocator 内部向内核申请的大块 arena。`/proc/<pid>/smaps` 中可能显示为 `[anon:libc_malloc]`、`[anon:scudo:*]` 或业务自定义名称。
- **SO / ELF 映射**：`.so` 文件被动态链接器映射到进程地址空间后，会产生代码段、只读数据、可写数据、重定位相关页面。共享只读页面通常按 PSS 分摊，可写脏页计入当前进程。
- **图形与硬件缓冲**：Bitmap 像素、OpenGL/Vulkan 纹理、Surface buffer、`dma-buf` 等资源可能出现在 Native Heap、Graphics、GL 或 memtrack 相关统计中。统计位置受分配方式、驱动和厂商实现影响，不能只根据一个 VMA 名称判断资源类型。图片内存详见 23.2 节。

Android 17 中，`android_os_Debug.cpp` 的 `android_os_Debug_getDirtyPagesPid()` 调用 libmeminfo 的 `ExtractAndroidHeapStats()` 取得按 VMA 分类的统计，再把 memtrack 返回的图形数据计入相应字段。VMA 分类规则位于 `androidprocheaps.cpp`：`[heap]`、`[anon:libc_malloc]`、`[anon:scudo:]` 和 `[anon:GWP-ASan]` 等名称归入 Native Heap，`.so` 归入 SO，`.jar`、`.apk` 等归入对应的代码分类。Graphics 数值还可能来自 memtrack，不能推断所有 `dma-buf` 都由 `androidprocheaps.cpp` 按名称归类。

这里还有一个容易混淆的读取路径。`androidprocheaps.cpp` 必须扫描详细的 `/proc/<pid>/smaps`，因为分类依赖每个 VMA 的名字。`ProcMemInfo::SmapsOrRollup()` 则服务于 PSS、RSS 等聚合值；内核提供 `smaps_rollup` 时可以读取汇总文件，否则回到 `smaps`。`smaps_rollup` 没有逐 VMA 名称，不能替代前一条分类路径。

[源码锚点: AOSP `android-17.0.0_r1`, `frameworks/base/core/jni/android_os_Debug.cpp`, `system/memory/libmeminfo/androidprocheaps.cpp`, `system/memory/libmeminfo/procmeminfo.cpp`]

四类内存对应不同的诊断动作：Native Heap 看分配栈；SO 映射看装载范围、重定位和脏页；图形缓冲看图像、渲染资源与 memtrack；匿名 `mmap` 需要追踪调用方或业务设置的 VMA 名称。把它们合成一个“Native 内存”数字，会丢失定位所需的信息。

## 排查入口：先看趋势，再抓调用栈

Native 内存问题分两种：一次性峰值过高，或者存活内存随操作次数持续增长。前者多见于大图、模型、音视频缓冲和一次性解压；后者更像泄漏、缓存失控或对象池没有回收。

下面三组命令用于建立第一次快照。`dumpsys meminfo` 适合先看系统分类；读取 `smaps` 适合检查 VMA，但在量产设备上可能受到 UID、SELinux 和 `/proc` 访问限制，需要 root、userdebug 或目标进程具备相应调试条件。

```bash
# 1. 看系统口径的进程内存分类
adb shell dumpsys meminfo <package_or_pid>

# 2. 在权限允许时保存 VMA 级明细
adb shell cat /proc/<pid>/smaps > smaps.txt

# 3. 从系统分类中单独观察 Native Heap
adb shell dumpsys meminfo <pid> | grep -A 20 "Native Heap"
```

这些快照只能说明“哪一类发生变化”，不能直接证明泄漏。应在相同设备、相同构建和相同操作序列下，对比进入场景前、场景稳定后、退出并等待回收后的数据。如果 Native Heap 持续增长，再采 heapprofd；如果 Graphics、GL 或 memtrack 相关值增长，转到图片和渲染资源路径；如果 `.so` 的私有脏页异常，再检查动态库装载、初始化写入和重定位。

## heapprofd：默认首选的 Native Heap 分配画像

heapprofd 适合回答两个问题：哪条调用栈的累计分配量高，哪条调用栈在快照时仍有较多存活分配。它是 Perfetto 的 native heap profiler，从 Android 10 开始可用。user build 上只能分析满足系统权限规则的 debuggable 或 profileable 应用；系统进程和更深的诊断通常需要 userdebug/eng 环境。

### 中央服务默认禁用，由采集请求按需启动

Android 17 的 `heapprofd.rc` 把 `heapprofd` 服务声明为 `disabled`。`persist.heapprofd.enable=1` 或 `traced.lazy.heapprofd=1` 时 init 才启动服务；两个属性都清空后停止。因此，heapprofd 不是从开机起持续运行的常驻采集器。

服务启动后，`heapprofd.cc::StartCentralHeapprofd()` 从 init 传入的 socket 取得监听端，建立 `HeapprofdProducer`，接收目标进程中 profiler client 的连接。应用进程侧不是依赖 `LD_PRELOAD`：`malloc_interceptor_bionic_hooks.cc` 通过 Bionic 的 `MallocDispatch` 接管 `malloc`、`free`、`calloc`、`realloc` 等入口，并通过 `AHeapProfile_registerHeap` 注册要分析的 heap。

这套接口属于 heapprofd 与系统 allocator 的内部协作面，不应当作为应用 SDK 的公共 malloc-hook API。Android 17 源码里的 `heapprofd_get_malloc_leak_info` 和 `heapprofd_write_malloc_leak_info` 是显式的空实现，不能把它们解释为 LeakCanary 或其他 native 泄漏 SDK 的基础接口。

[源码锚点: Perfetto `android-17.0.0_r1`, `heapprofd.rc`, `src/profiling/memory/heapprofd.cc`, `src/profiling/memory/malloc_interceptor_bionic_hooks.cc`]

### 采集配置与采样语义

这段配置演示如何采集一个指定进程。`size_kb` 和 `dump_interval_ms` 是诊断示例值，需要根据复现时长和设备负载调整；决定采样密度的是 `sampling_interval_bytes`。

```protobuf
buffers: {
  size_kb: 65536
}
data_sources: {
  config {
    name: "android.heapprofd"
    heapprofd_config {
      process_cmdline: "com.example.app"
      sampling_interval_bytes: 4096
      continuous_dump_config {
        dump_interval_ms: 10000
      }
    }
  }
}
```

Perfetto 官方文档把 `4096` 字节作为默认采样间隔。`Sampler::SampleSize()` 对小于间隔的分配使用按字节推进的概率采样，含义是长期期望每 N 字节产生一个样本；单次分配大于或等于间隔时绕过该概率路径，记录这次分配的原始大小。因而，不能用“采样覆盖率”直接换算某个对象被记录的固定次数，也不能脱离设备、调用栈展开成本和负载给出固定 CPU 百分比。

采集后在 Perfetto UI 查看 Heap Profile。分析泄漏时，比较多个时间点仍然存活的分配及其调用栈；分析分配抖动时，观察累计分配量与分配频率。间隔越小，小分配的细节越多，事件量与运行开销也越高。应先在目标设备上测量开销，再决定复现窗口和采样间隔。

[源码锚点: Perfetto `android-17.0.0_r1`, `src/profiling/memory/sampler.h`, `src/profiling/memory/sampler.cc`]

### Native Heap 与 Java HPROF 是两条独立路径

Android 17 的 Perfetto 源码为 native heapprofd 使用 `__SIGRTMIN + 4`，为 Java HPROF 使用 `__SIGRTMIN + 6`。Java HPROF producer 在发送信号前还会通过 `CanProfile()` 检查目标进程是否允许分析。两者是不同的数据源、信号与权限路径；某一种 dump 命令能运行，不能推出另一种 Perfetto 数据源也一定可用。

[源码锚点: Perfetto `android-17.0.0_r1`, `src/profiling/memory/heapprofd_producer.cc`, `src/profiling/memory/java_hprof_producer.cc`]

## libmemunreachable 与 malloc_debug：本地复现时补充泄漏证据

`libmemunreachable` 在请求发生时扫描 native allocator 中无法从可达根访问的分配块。默认模式不会为每次分配记录回溯，因此运行期开销低，但报告只能提供地址、大小上界和部分内容。启用 malloc_debug backtrace 后，报告可以带分配栈，代价是明显的运行时开销。

Android 17 固定标签下，面向应用的可验证流程位于独立仓库 `platform/system/memory/libmemunreachable`。下面的命令用于 userdebug 设备上的单个应用；`<process>` 要替换为进程名，设置属性后必须终止并重新启动进程。

```bash
adb root
adb shell setprop libc.debug.malloc.program app_process
adb shell setprop wrap.<process> "\$\@"
adb shell setprop libc.debug.malloc.options backtrace=4

# 重启目标进程并复现问题后执行
adb shell dumpsys -t 600 meminfo --unreachable <process>
```

`--unreachable` 报告的是扫描时无法到达的分配块，不等于语言层意义上的确定泄漏。保守扫描可能把某些整数误认成指针，第三方 allocator 或自管理内存也可能不在它的观察范围内。应结合可重复的增长趋势、分配栈和资源生命周期判断。

完成诊断后要清除三个属性并重启进程，避免后续测试继续承受 backtrace 开销：

```bash
adb shell setprop libc.debug.malloc.options "''"
adb shell setprop libc.debug.malloc.program "''"
adb shell setprop wrap.<process> "''"
```

这些清理命令只撤销本次 malloc_debug 配置，不会修改应用数据。量产 user 设备通常不具备执行该流程所需的 root、属性和 SELinux 权限，因此它应位于可控环境的复现阶段。

## ASan、HWASan、GWP-ASan、MTE 怎么选

Native 内存问题不只有泄漏。越界写、use-after-free、double free 会先表现为偶现 crash、数据损坏或 UI 异常，再在内存统计里留下噪声。检测工具按使用场景选择：

| 工具 | 适合场景 | 代价与边界 |
| --- | --- | --- |
| ASan | 开发阶段发现越界访问、use-after-free | 需要重新编译插桩，内存和运行时开销高，不适合常规 release 包 |
| HWASan | 64 位 Arm 测试环境中的内存错误检测 | 需要支持的系统镜像和编译配置，主要用于测试和预发 |
| GWP-ASan | 在较低开销下抽样捕获 native heap use-after-free、heap-buffer-overflow | 抽样检测，不保证每次问题都命中 |
| MTE | Arm Memory Tagging Extension，硬件标签检测越界和释放后访问 | 依赖硬件、系统版本和 manifest / 系统配置，模式不同会影响性能与报错时机 |

ASan / HWASan 偏测试构建，GWP-ASan 和 MTE 更适合在较低开销下扩大检测面。它们解决的是内存安全错误，不替代 heapprofd 的容量分析；heapprofd 能说明谁分配得多，sanitizer 能说明哪次访问越界或访问了已释放内存。

## SO 库内存优化从三个维度入手

SO 库相关内存要拆成装载成本、运行时分配和可写脏页。三者对应不同动作。

### 装载成本：少装、晚装、按需装

一个 `.so` 被加载后，代码段、只读数据、重定位表和符号相关页面会进入进程地址空间。只看 APK 体积无法判断运行时内存，排查时要看进程 maps/smaps 中对应 so 的 RSS/PSS/Private Dirty。

可执行动作：

- 只在测量表明 `dlopen` 数量或重复元数据造成显著成本时，评估合并小型 native 模块；合并后若低频代码被一并加载，也可能增加常驻映射；
- 把低频功能的 so 延后到功能入口加载；
- 清理未使用 ABI、未使用架构和重复打包的 so，这主要减少安装包与安装占用；只有相关文件原本会被映射时，才会影响运行时 RSS/PSS；
- 把 release 符号文件作为独立构建产物保存，供 tombstone、Perfetto 和地址回溯使用；从 App 内移除调试段主要减少文件体积，不能直接视为等量的运行时内存收益。

### 运行时分配：把大块分配变成可解释事件

第三方 so 分配异常时，单靠 `dumpsys meminfo` 只能看到 Native Heap 变大。heapprofd 或 malloc hook 能把分配归到调用栈；如果符号文件保留完整，还能还原到函数名和源码行。

工程上可以为可控的 native 大对象建立统一分配入口，例如模型缓冲、音视频 frame buffer、解码输出池和压缩临时缓冲。封装层记录大小、用途、生命周期与调用位置，线上只上报有界的聚合数据；线下再使用 heapprofd 或 malloc_debug 取得完整分配栈。对于不可改动的第三方库，以 profiler 证据为准，避免仅凭库名归因。

### 可写脏页：少改共享映射，少做启动期全量初始化

`.so` 的只读页面可以在多个进程间共享；页面一旦被当前进程写脏，就会变成私有成本。常见来源包括全局可变数据、启动期大表初始化、懒加载缓存写入和重定位后的可写段。

排查时对比同一 so 的 `Shared Clean`、`Private Dirty`、`Private Clean`。如果某个库的 `Private Dirty` 远高于同类模块，要检查它是否在启动期写入大块全局状态，或者把可延迟的数据提前初始化了。

## Native 内存监控方案

线上监控不应该复刻线下 profiler。用户设备上的目标是发现趋势、定位版本和场景，不能长期记录完整调用栈。

一套可控方案可以分三层：

- **基础指标层**：定时采集 PSS、RSS、Native Heap Alloc、Graphics、GL、线程数、fd 数，并带上页面、业务场景、前后台状态、设备内存档位。采集频率按场景设定，避免常驻高频轮询。
- **异常判定层**：在同一会话内观察增长斜率，例如进入页面前后、按确定脚本重复操作后、播放或上传结束后。单点阈值容易把合理的高占用当成异常。
- **诊断触发层**：命中灰度规则后，对少量 debug/profileable 包触发 heapprofd、系统 meminfo 快照或业务侧 native 分配摘要。普通 release 包只上报聚合指标和场景标签。

指标上报要区分“占用高”和“泄漏”。缓存命中带来的短时 Native Heap 增长不一定是问题；退出场景、收到 `onTrimMemory()` 或完成任务后仍不回落，只能构成进一步分析的信号，还需要分配栈与对象生命周期证明原因。allocator 可能保留空闲页，PSS 没有立刻下降也不能单独证明对象仍然存活。

## Scudo 与 Native Heap 的统计边界

Android 应用通常不直接选择系统 allocator，但 allocator 会影响碎片、页归还、错误检测和 `smaps` 命名。Android 11 起常规设备使用 Scudo，低内存设备仍可能使用 jemalloc；最终实现应根据设备构建、VMA 名称和 tombstone 确认。

### 四种数值不要互相替代

| 口径 | 数据来源 | 适合回答的问题 | 覆盖不到的部分 |
| --- | --- | --- | --- |
| `Debug.getNativeHeapAllocatedSize()` | `mallinfo().uordblks` | allocator 当前记为已分配的字节 | 任意 `mmap()`、线程栈、共享库、Graphics |
| `dumpsys meminfo` 的 Native Heap | heap VMA 的 PSS/RSS 分类 | Native Heap 对物理内存的贡献 | 具体分配调用栈 |
| `/proc/$pid/smaps` / `showmap` | 内核 VMA 与页统计 | 匿名映射、文件映射、栈和 so 分别占多少 | 每次 `malloc()` 的调用者 |
| heapprofd / Native Allocations | 录制窗口内的分配、释放与栈 | 哪些路径分配、哪些样本仍存活 | 录制前分配和绕过 allocator 的映射 |

Android 17 的 `android_os_Debug.cpp` 直接把 `mallinfo().uordblks` 返回为 `getNativeHeapAllocatedSize()`。`libmeminfo` 则把 `[heap]`、`[anon:libc_malloc]`、`[anon:scudo:*]` 和 `[anon:GWP-ASan*]` 等 VMA 归到 Native Heap，并按页面计算 PSS/RSS。两条统计路径不同，所以 allocator allocated 下降后，Native Heap PSS 不要求同步下降。

### `free()` 后 RSS 没回落不等于泄漏

业务调用 `free()` 后，chunk 已不能再访问，但 allocator 可以把它放进 quarantine、线程缓存或空闲结构，等待复用或批量归还操作系统。Scudo 的 quarantine 和 release interval 在安全检查、锁竞争、复用速度与 RSS 回落之间做取舍。普通应用不应通过 `SCUDO_OPTIONS` 或 `__scudo_default_options` 把这类系统配置当作常规省内存开关。

泄漏判断仍需同时满足可重复增长和对象归因：固定场景中 allocated 持续上升，heapprofd 的未释放样本集中在稳定调用栈，业务缓存过期后仍不回落，并且 Graphics、线程栈、文件映射等旁路不能解释增量。

### Scudo ERROR 是发现点，不一定是破坏点

Scudo 会在发现 corrupted chunk header、invalid chunk state、misaligned pointer、allocation type mismatch 或 invalid sized delete 等异常时终止进程。若线程 B 在 `free()` 时发现 header 已损坏，真正的越界写可能早已发生在线程 A。排查必须保留完整 tombstone、错误文本、fault address、Build ID、ABI、相关线程和匹配的未剥离符号；再用 GWP-ASan、MTE 或 HWASan 补充 allocation、deallocation 与 access 证据。

GWP-ASan 是抽样检测，Recoverable 模式写出 tombstone 后继续运行也不代表进程已经恢复正确状态。MTE 的 SYNC、ASYNC 和 ASYMM 模式在定位精度与成本上不同，manifest 请求还受设备硬件和系统配置约束。这些工具定位内存安全错误，不能替代 heapprofd 的容量归因。

### 16 KiB 页与三方 so

16 KiB 页会改变 ELF segment 对齐、APK 中未压缩 so 的 zip alignment、`mmap()` 约束以及 allocator region 的页面粒度。它不会让每个小对象都占用独立 16 KiB，也不能从 PSS 增量直接反推出 `malloc()` 对象数。含 native 代码的应用应检查所有 ABI，运行时通过 `getconf PAGE_SIZE` 获取实际页大小，清理 loader 和三方库中写死的 4096 字节假设。

三方 so 的报告至少保存 SDK 版本、so Build ID、ABI、输入与并发、设备页大小、heapprofd 样本和相同场景的 `meminfo`。缺少 Build ID 时，同名 so 可能来自不同二进制，聚合后的调用栈没有可比性。

[源码锚点: AOSP `android-17.0.0_r1`, `frameworks/base/core/jni/android_os_Debug.cpp`, `system/memory/libmeminfo/androidprocheaps.cpp`, `platform/bionic/libc/bionic/malloc_common.cpp`, `platform/external/scudo`]

## 排查清单

- `dumpsys meminfo` 中增长的是 Native Heap、Graphics/GL、Code，还是 Unknown？
- 使用确定的操作脚本重复场景后，内存曲线是趋于平台、随次数增长，还是只出现一次峰值？
- heapprofd 的存活分配火焰图中，最大路径是否来自业务 JNI、第三方 SDK、图片库或音视频库？
- Native crash 是否带有 ASan、HWASan、GWP-ASan、MTE 相关标记？
- 相关 so 是否有符号文件可用于地址还原？
- `smaps` 里同一 so 的 `Private Dirty` 是否异常偏高？
- 线上是否只采聚合指标，避免在用户设备上长期开启高开销调试能力？

## 参考资料

- [Debug native memory use](https://source.android.com/docs/core/tests/debug/native-memory)
- [Perfetto Native Heap Profiler](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [Memory error debugging and mitigation](https://developer.android.com/ndk/guides/memory-debug)
- [GWP-ASan](https://developer.android.com/ndk/guides/gwp-asan)
- [Arm MTE](https://developer.android.com/ndk/guides/arm-mte)
- [Scudo](https://source.android.com/docs/security/test/scudo)
- [AOSP `android-17.0.0_r1`, libmemunreachable README](https://android.googlesource.com/platform/system/memory/libmemunreachable/+/refs/tags/android-17.0.0_r1/README.md)
- [AOSP `android-17.0.0_r1`, android_os_Debug.cpp](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/jni/android_os_Debug.cpp)
- [AOSP `android-17.0.0_r1`, androidprocheaps.cpp](https://android.googlesource.com/platform/system/memory/libmeminfo/+/android-17.0.0_r1/androidprocheaps.cpp)
- [AOSP `android-17.0.0_r1`, procmeminfo.cpp](https://android.googlesource.com/platform/system/memory/libmeminfo/+/android-17.0.0_r1/procmeminfo.cpp)
- [AOSP `android-17.0.0_r1`, Bionic README](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/README.md)
- [Perfetto `android-17.0.0_r1`, heapprofd.rc](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/heapprofd.rc)
- [Perfetto `android-17.0.0_r1`, heapprofd.cc](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/profiling/memory/heapprofd.cc)
- [Perfetto `android-17.0.0_r1`, malloc_interceptor_bionic_hooks.cc](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/profiling/memory/malloc_interceptor_bionic_hooks.cc)
- [Perfetto `android-17.0.0_r1`, heapprofd_producer.cc](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/profiling/memory/heapprofd_producer.cc)
- [Perfetto `android-17.0.0_r1`, java_hprof_producer.cc](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/profiling/memory/java_hprof_producer.cc)
- [Perfetto `android-17.0.0_r1`, sampler.h](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/profiling/memory/sampler.h)
- [Perfetto `android-17.0.0_r1`, sampler.cc](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/profiling/memory/sampler.cc)
