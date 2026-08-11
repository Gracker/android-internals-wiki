---
title: "Scudo 分配器与 Native Heap 性能边界"
chapter: "23.11"
status: ready-for-review
drafted_date: "2026-05-24"
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
last_verified: "2026-05-24"
last_verified_against: "AOSP main / Android Developers 2026-03~04 文档"
confidence: medium
sources:
  - type: aosp
    path: "source.android.com/docs/security/test/scudo"
  - type: aosp
    path: "source.android.com/docs/core/tests/debug/native-memory"
  - type: aosp
    path: "frameworks/base/core/jni/android_os_Debug.cpp"
  - type: aosp
    path: "bionic/libc/bionic/malloc_common.cpp"
  - type: aosp
    path: "system/memory/libmemunreachable/MemUnreachable.cpp"
  - type: official
    path: "developer.android.com/studio/profile/record-native-allocations"
  - type: official
    path: "developer.android.com/ndk/guides/gwp-asan"
  - type: official
    path: "developer.android.com/guide/practices/page-sizes"
  - type: official
    path: "source.android.com/docs/security/test/memory-safety/arm-mte"
  - type: book
    path: "Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md"
  - type: book
    path: "Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md"
  - type: book
    path: "Clippings/Android 应用稳定性剖析与优化 - Native 内存泄漏监控：寻找 Native 中不可达内存.md"
tags: [native-memory, scudo, allocator, heapprofd, gwp-asan]
related_chapters: ["4.5", "14.5", "20.11", "23.3", "26.16"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-24"
gap_source: "素材驱动/官方文档/Clippings结构参考"
---

# 23.11 Scudo 分配器与 Native Heap 性能边界

Native 内存曲线变大时，先确认正在看哪一种“大小”。`Debug.getNativeHeapAllocatedSize()`、`dumpsys meminfo` 的 Native Heap、`smaps` 的匿名映射、heapprofd 的未释放样本和 Graphics PSS 来自不同统计路径。它们可以同时变化，也可能朝相反方向变化。

平台源码锚点为 Android 17 / API 37 / `android-17.0.0_r1`。涉及页大小、`/proc` 和 MTE 的内核边界时，以 `android17-6.18-2026-06_r6` 为基线。Scudo 属于用户态分配器，内核版本不会把某次 `malloc()` 自动归为业务泄漏。Native 内存分层见 4.5 节，常规排查见 23.3 节，MTE 崩溃分析见 20.11 节。

## 先把五种口径分开

| 口径 | 数据来源 | 适合回答的问题 | 不能直接回答的问题 |
| --- | --- | --- | --- |
| `Debug.getNativeHeapAllocatedSize()` | allocator 的 `mallinfo().uordblks` | 当前由分配器记为已分配的字节数 | 进程全部 Native RSS、Graphics、任意 `mmap()` |
| `dumpsys meminfo` 的 Native Heap | Scudo、jemalloc、GWP-ASan 等堆 VMA 的 PSS/RSS 分类，加上相关统计 | Native Heap 对进程物理内存的贡献 | 哪条调用栈仍持有对象 |
| `/proc/$pid/smaps`、`showmap` | 内核记录的 VMA 与页统计 | 匿名映射、文件映射、线程栈、共享库分别占多少 | 每次 `malloc()` 的调用者 |
| heapprofd、Native Allocations | 对分配与释放事件采样并记录调用栈 | 哪些调用栈产生分配、哪些样本仍未释放 | 录制开始前的分配、非 allocator 映射 |
| Graphics | `smaps` 可见部分与 libmemtrack 补充数据 | 图形缓冲区对进程和系统内存的影响 | C/C++ 普通堆对象的持有关系 |

### `getNativeHeapAllocatedSize()` 的源码口径

Android 17 在同一文件中用三个接口分别读取 `mallinfo` 字段。下面只摘录 `getNativeHeapAllocatedSize()`，用于确认它对应 `uordblks`。

```cpp
static jlong android_os_Debug_getNativeHeapAllocatedSize(CRITICAL_JNI_PARAMS)
{
    struct mallinfo info = mallinfo();
    return (jlong) info.uordblks;
}
```

这段实现位于 [`frameworks/base/core/jni/android_os_Debug.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/jni/android_os_Debug.cpp)。它说明该 API 是 allocator 统计，不是对 `/proc/$pid/smaps` 求和。它适合低频记录趋势，不能代替 PSS/RSS，也不能覆盖所有匿名 `mmap()`、线程栈、共享库和图形缓冲区。

### `dumpsys meminfo` 为什么会更大

Android 17 的 `libmeminfo` 会把以下 VMA 名归到 `HEAP_NATIVE`：

- `[heap]`
- `[anon:libc_malloc]`
- `[anon:scudo:*]`
- `[anon:GWP-ASan*]`

分类逻辑见 [`system/memory/libmeminfo/androidprocheaps.cpp`](https://android.googlesource.com/platform/system/memory/libmeminfo/+/android-17.0.0_r1/androidprocheaps.cpp)。Native Heap 行反映这些映射中当前驻留页面的 PSS/RSS 等数据，粒度是 VMA 和页面。Scudo 可以保留已经没有活跃对象的页，也可以把空闲页归还操作系统；因此 allocator 已分配字节下降后，Native Heap PSS 不要求同步下降。

这是诊断上的推断，不是泄漏判据。要证明泄漏，需要同时看到可重复的增长场景和对象归因，例如：

- 同一操作重复执行后，allocator 已分配字节持续上升；
- heapprofd 的未释放样本集中在稳定调用栈；
- 离开页面并等待业务缓存过期后，样本仍保持增长；
- Graphics、线程栈、文件映射等旁路没有解释这部分增量。

Android 17 的 `android_os_Debug.cpp` 还通过 libmemtrack 读取未出现在 `smaps` 中的 graphics memory。看到 Graphics 增长时，应转向 BufferQueue、Bitmap、硬件缓冲区和驱动侧归因，修改 Scudo 参数无法处理这类内存。

## Scudo 在 Android 17 中负责什么

[AOSP Scudo 文档](https://source.android.com/docs/security/test/scudo)把 Scudo 定义为用户态 heap allocator。它提供标准的 `malloc/free`、`new/delete` 等接口，并对 heap buffer overflow、use-after-free、double free 等风险增加防护。Android 11 起，Scudo 服务常规 Native Heap；低内存设备仍可能使用 jemalloc。

Android 17 的 bionic 仍保留 malloc dispatch。`malloc()`、`free()`、`mallinfo()` 等入口先检查动态 dispatch，再调用构建时选定的 allocator 实现，代码见 [`bionic/libc/bionic/malloc_common.cpp`](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/libc/bionic/malloc_common.cpp)。malloc debug、heapprofd 和 GWP-ASan 能接入这条路径，但职责不同：

| 组件 | 职责 | 看到异常时能得到什么 |
| --- | --- | --- |
| Scudo | 分配、释放、缓存、quarantine 和一致性检查 | `Scudo ERROR`、触发检查时的线程栈 |
| heapprofd | 采样分配/释放事件 | 分配调用栈、未释放样本和时间分布 |
| malloc debug | 以更高成本记录 allocator 调试信息 | 本地或系统调试环境中的详细分配证据 |
| GWP-ASan | 抽样保护少量 heap allocation | 命中样本的访问、分配和释放信息 |
| MTE | 用硬件内存标签检查访问 | 标签不匹配故障与相应诊断信息 |
| HWASan | 编译插桩检测更广的内存错误 | 测试构建中的高密度错误报告 |

Scudo 是防护能力，也是一套分配实现。它不记录所有对象的业务语义，不负责分析引用关系，也不是完整的内存错误检测器。

## 分配器保留不等于业务泄漏

`free()` 完成后，内存至少经历两个层面的状态变化：

1. 对业务而言，这个 chunk 已经不可再访问；
2. 对 allocator 而言，这块空间可以进入 quarantine、线程缓存或空闲结构，等待复用或归还操作系统。

Scudo 文档公开了 `QuarantineSizeKb`、`ThreadLocalQuarantineSizeKb`、`QuarantineChunksUpToSize` 与 `allocator_release_to_os_interval_ms` 等选项。它们说明安全检查、线程竞争、复用速度与 RSS 回落之间存在取舍。文档中的默认值属于特定位数和版本的实现配置，不应转写成所有设备、所有进程都固定不变的应用预算。

普通应用排查内存增长时，不建议把 `SCUDO_OPTIONS` 或 `__scudo_default_options` 当作常规优化入口，理由有三点：

- 低内存设备可能仍使用 jemalloc，同一选项没有统一适用面；
- 降低 quarantine 会削弱 use-after-free 防护；
- 调整释放节奏可能改变 RSS、CPU 和锁竞争，单看内存峰值无法评价结果。

需要评估 allocator 配置的系统组件，应使用可回滚的受控实验：固定系统镜像、ABI、页大小、负载脚本和进程生命周期，同时比较分配延迟、CPU、RSS/PSS、故障检测能力与重复运行的方差。应用工程师更应处理可归因的业务分配、缓存上限和资源生命周期。

## 一套可复现的快照采集

下面的脚本接收包名和输出目录，采集一次 `meminfo`，并在权限允许时补充 `showmap` 与 `smaps`。它避免把示例占位符直接复制进终端。

```bash
#!/usr/bin/env bash
set -euo pipefail

if (( $# != 2 )); then
  echo "usage: $0 PACKAGE OUTPUT_DIR" >&2
  exit 2
fi

package_name="$1"
output_dir="$2"
mkdir -p "$output_dir"

pid="$(adb shell pidof -s "$package_name" | tr -d '\r')"
if [[ -z "$pid" ]]; then
  echo "process not found: $package_name" >&2
  exit 1
fi

adb shell dumpsys meminfo "$pid" > "$output_dir/meminfo.txt"

if ! adb shell showmap "$pid" > "$output_dir/showmap.txt"; then
  rm -f "$output_dir/showmap.txt"
  echo "showmap unavailable for pid $pid" >&2
fi

if ! adb shell cat "/proc/$pid/smaps" > "$output_dir/smaps.txt"; then
  rm -f "$output_dir/smaps.txt"
  echo "smaps unavailable for pid $pid" >&2
fi
```

`meminfo.txt` 用于比较 Native Heap、Graphics、Code、Stack 与 Unknown；`showmap.txt` 用于快速查看 VMA 汇总；`smaps.txt` 用于核对每段映射的 RSS、PSS、Private Dirty 和名称。user build 对 `/proc` 和其他调试接口有限制，失败结果应记录为“无权限或工具不可用”，不能补写成零。

采集时还要控制场景。冷启动、页面首次进入、重复操作、退出页面和等待缓存过期各取一组快照；每组测试保持设备、ABI、页大小和进程状态一致。单张快照只能描述当时状态，增长是否异常要靠同场景的时间序列判断。

## 工具如何选择

### heapprofd：回答“谁分配了这些对象”

[Perfetto heapprofd 文档](https://perfetto.dev/docs/data-sources/native-heap-profiler)明确说明：Android 10 起可记录 `malloc/free`、`new/delete` 的分配与释放，并把内存归因到调用栈。user build 上，目标应用需要是 debuggable 或 profileable。Native profiling 只观察录制开始后的事件，不会还原此前已经存在的分配。

推荐使用 Perfetto 的 `tools/heap_profile android -n PROCESS_NAME`，或在 Perfetto UI 中启用 Native heap profiling。采样间隔应按目标进程的分配速率和设备成本选择：

- 样本太稀，短生命周期对象和小额热点可能缺失；
- 样本太密，profiling 开销与缓冲区压力会上升；
- 出现 buffer overrun 时，先检查突发分配速率，再调整共享内存或采样间隔。

heapprofd 的未释放样本可以提示增长调用栈，但仍是采样结果。修复前要用固定操作复测，并检查样本的 so build ID 与本地符号是否一致。

### Android Studio Native Allocations：本地交互验证

[Android Studio 文档](https://developer.android.com/studio/profile/record-native-allocations)中的 Native Allocations 任务会展示 allocation、deallocation、两者的字节数、净数量和 Remaining Size。它适合开发阶段观察某个页面或某段操作。

文档当前默认 sample size 为 2048 bytes；更小的值会提高采样频率和精度，也会增加资源消耗。这个数值是工具默认配置，不是业务阈值，更不是 Scudo 的分配粒度。团队记录报告时，应同时写下 Android Studio 版本、sample size、设备和操作步骤。

### malloc debug 与 libmemunreachable：受控诊断

[AOSP Native memory 文档](https://source.android.com/docs/core/tests/debug/native-memory)把 malloc debug、libmemunreachable、malloc hooks 和 heapprofd 分成不同工具。malloc debug 适合 root、userdebug 或可控调试条件，不应常驻普通应用生产进程。

libmemunreachable 用保守的可达性扫描报告疑似不可达 Native Heap。Android 17 的 [`MemUnreachable.cpp`](https://android.googlesource.com/platform/system/memory/libmemunreachable/+/android-17.0.0_r1/MemUnreachable.cpp)会把 `[anon:libc_malloc]`、`[anon:scudo:*]` 和 `[anon:GWP-ASan*]` 识别为 heap mappings，并通过 `DetectLeaks()`、结果归并与回溯生成报告。保守扫描可能因为类似指针的数值而保留对象，也可能受权限和线程状态影响；报告适合作为线索，需要用分配栈和复现场景确认。

### `smaps`：回答“增长属于哪种映射”

以下情况应回到 VMA，而不是继续放大 heap profiler：

- `dumpsys meminfo` 的 Unknown、Code 或 Stack 比 Native Heap 涨得快；
- 线程数量与 Stack RSS 同时增加；
- 大块匿名 `mmap()` 没有经过 `malloc()`；
- 共享库或模型文件映射增加；
- Graphics 增长明显，heapprofd 没有对应样本。

`smaps` 中出现 `[anon:scudo:primary]` 或 `[anon:scudo:secondary]` 只能证明这段 VMA 由 Scudo 管理。它不能指出哪个对象泄漏，也不能说明 VMA 内每一页都被业务对象占用。

## Scudo 崩溃如何归因

Scudo 发现不可恢复的堆状态异常时会输出 `Scudo ERROR` 并终止进程。常见类型包括 corrupted chunk header、invalid chunk state、misaligned pointer、allocation type mismatch 和 invalid sized delete。错误名称是 allocator 在检查点看到的症状。

例如，线程 B 在 `free()` 时发现 chunk header 损坏，越界写入可能早已发生在线程 A。此时 B 的栈可以确认检查点，不能单独证明 B 是写坏内存的位置。排查应保留：

- 完整 tombstone、signal、fault address 和 Scudo 错误文本；
- so 路径、Build ID、ABI、Android 版本和设备；
- 崩溃线程与相关工作线程；
- 可匹配 Build ID 的未剥离符号；
- GWP-ASan、MTE 或 HWASan 提供的 allocation、deallocation、access 信息。

### GWP-ASan 的生产边界

[GWP-ASan 官方文档](https://developer.android.com/ndk/guides/gwp-asan)给出的当前规则如下：

- GWP-ASan 适用于 target Android 11 / API 30 及以上的应用；
- `android:gwpAsanMode="always"` 会在命中保护样本时终止进程；
- Android 14 / API 34 及以上，manifest 未指定该属性时默认使用 Recoverable GWP-ASan；
- Recoverable GWP-ASan 约在 1% 的应用启动中启用，每次启动最多生成一份报告；
- Recoverable 模式写出 tombstone 后允许进程继续运行，但此后的程序行为未定义；
- 报告可通过 `ActivityManager.getHistoricalProcessExitReasons()` 获取。

官方文档还给出启用 GWP-ASan 时每个受影响进程当前约 70 KiB 的固定 RAM 开销。这里的“约”与“当前”必须保留，它是平台实现说明，不能当成所有未来版本的保证。

Recoverable 模式没有立即结束进程，不表示内存破坏已恢复。应用侧应优先修复该报告，不要依赖损坏后的进程继续提供正确结果。

### MTE 的测试与生产边界

[AOSP MTE 文档](https://source.android.com/docs/security/test/memory-safety/arm-mte)说明，MTE 用硬件标签检查指针与内存标签，可发现 use-after-free 和 buffer overflow。模式选择影响错误定位与成本：

- SYNC 在标签不匹配时立即触发 `SIGSEGV`，诊断更精确，适合测试和专项复现；
- ASYNC 会延后到内核入口处报告，性能成本较低，故障地址与访问位置不如 SYNC 精确；
- ASYMM 对读写采用不同检查方式，最终行为还受设备硬件和平台配置影响。

应用 manifest 的 `android:memtagMode` 只表达进程请求，设备是否支持、平台如何配置以及 CPU 核心的有效模式都要一并确认。20.11 节详细说明 MTE 报告和灰度策略。

## 16 KB Page Size 与 Native Heap

Android 15 起，AOSP 支持使用 16 KB page size 的设备。[Android 16 KB page size 指南](https://developer.android.com/guide/practices/page-sizes)还记录了 Android 17 的兼容行为和当前工具要求。页大小影响 ELF LOAD segment 对齐、APK 中未压缩 so 的 zip alignment、`mmap()` 参数与物理页统计。

它与 Scudo 的关系需要分层理解：

- Scudo 管理对象分配和自己的内存区域；
- 内核按页面维护映射与驻留状态；
- 16 KB 页会改变小映射、线程栈、文件映射和 allocator region 的页面粒度；
- PSS/RSS 变化不能直接推导为 `malloc()` 对象增加。

含 Native 代码或三方 so 的应用，应检查所有 ABI 的 ELF segment 和 APK 对齐。运行时用 `adb shell getconf PAGE_SIZE` 读取设备实际页大小，不要在代码中假设 `4096`。官方指南要求 Google Play 上面向 Android 15 及以上设备的新应用和更新自 2025 年 11 月 1 日起支持 16 KB page size；该要求是发布兼容性规则，不是内存性能结论。

Android 17 还允许将 16 KB backcompat 设为 `fatal`，用于让不兼容二进制立即中止。该模式适合兼容性测试；内存治理仍要分别观察 allocator 统计、VMA 和调用栈。

## 三方 so 的排查重点

三方 so 没有源码时，分配栈仍能支持工程决策，但前提是保留可比对的信息：

- SDK 名称、版本、so Build ID 和 ABI；
- 触发功能、输入尺寸、并发数与进程；
- Android 版本、设备页大小和是否启用 GWP-ASan/MTE；
- heapprofd 样本、tombstone 与相同场景的 `meminfo`；
- 供应商提供的符号或符号化结果。

可执行动作包括升级或回退 SDK、限制输入和并发、关闭问题功能、把高风险任务放到独立进程。进程隔离可以减少主进程受影响的范围，不会修复泄漏或内存破坏。缺少 Build ID 与版本信息时，同名 so 的报告可能来自不同二进制，聚合结果会失真。

## 建立可回归的判断标准

Native Heap 预算应按设备内存档位、ABI、页大小、进程类型和业务场景分别建立。固定一个全量阈值会把正常差异与异常增长混在一起。

每个回归用例至少记录：

1. 操作前、峰值、退出页面后和稳定等待后的 allocator allocated、PSS/RSS 与内存分类；
2. 重复操作次数、输入规模、并发数和缓存状态；
3. heapprofd 或 Native Allocations 的未释放调用栈；
4. 线程数、Graphics、匿名映射和文件映射的增量；
5. native crash、LMKD 退出与用户可见性能变化。

修复是否有效，要看同设备分组、同场景和同工具配置下的差值。若 allocator allocated 回落而 PSS 暂未回落，应继续观察复用与页面归还；若未释放样本和 allocated 持续上升，则回到持有路径；若 PSS 增长集中在 Graphics 或非 heap VMA，则转到对应子系统。

## 小结

Scudo 是 Android 17 的常规 Native Heap 分配器和安全防护组件，低内存设备仍可能使用 jemalloc。`Debug.getNativeHeapAllocatedSize()` 读取 allocator 的已分配字节；`dumpsys meminfo` 按 VMA 和页面统计 Native Heap；heapprofd 对录制期间的分配事件采样。三种数据不能互相替代。

排查顺序应保持稳定：确认内存分类，比较时间序列，再用分配栈或 VMA 证明归因。Scudo ERROR 表示 allocator 发现了异常，触发检查的栈未必是最早的破坏位置。GWP-ASan、MTE、HWASan、符号与可重复场景共同决定能否定位代码。

## 参考资料

- [AOSP：Scudo](https://source.android.com/docs/security/test/scudo)
- [AOSP：Debug native memory use](https://source.android.com/docs/core/tests/debug/native-memory)
- [AOSP Android 17：`android_os_Debug.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/jni/android_os_Debug.cpp)
- [AOSP Android 17：bionic `malloc_common.cpp`](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/libc/bionic/malloc_common.cpp)
- [AOSP Android 17：libmeminfo `androidprocheaps.cpp`](https://android.googlesource.com/platform/system/memory/libmeminfo/+/android-17.0.0_r1/androidprocheaps.cpp)
- [AOSP Android 17：libmemunreachable `MemUnreachable.cpp`](https://android.googlesource.com/platform/system/memory/libmemunreachable/+/android-17.0.0_r1/MemUnreachable.cpp)
- [Android 17 Kernel：`android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)
- [Perfetto：Callstack-based Allocation Profiling](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [Android Studio：Record native allocations](https://developer.android.com/studio/profile/record-native-allocations)
- [Android NDK：GWP-ASan](https://developer.android.com/ndk/guides/gwp-asan)
- [Android Developers：Support 16 KB page sizes](https://developer.android.com/guide/practices/page-sizes)
- [AOSP：Arm Memory Tagging Extension](https://source.android.com/docs/security/test/memory-safety/arm-mte)
