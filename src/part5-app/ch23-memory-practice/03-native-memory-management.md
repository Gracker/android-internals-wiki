---

title: "Native 内存管理与优化"
chapter: "23.3"
section: "23.3"
status: finalized
drafted_date: "2026-05-14"
reviewed_date: 2026-06-08
reviewed_by: openclaw-task6
task6_result: pass-light-edit
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-06-08"
last_verified_against: "AOSP android-16.0.0_r1 / Android Developers docs / Perfetto docs"
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
    path: "android.googlesource.com/platform/bionic/+/android-16.0.0_r1/libc/malloc_debug/README.md"
  - type: aosp
    path: "android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/core/jni/android_os_Debug.cpp"
  - type: aosp
    path: "android.googlesource.com/platform/system/memory/libmeminfo/+/android-16.0.0_r1/androidprocheaps.cpp"
  - type: blog
    path: "Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md"
tags: [native-memory, malloc, asan, hwasan, so-memory]
related_chapters: ["23.2", "4.1", "4.2", "10.1", "14.3"]
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
---

# Native 内存管理与优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Native 内存构成：SO 库、malloc、mmap
- 🔹 Native 内存泄漏检测：malloc_debug、ASan、HWASan
- 🔹 Native 内存监控方案
- 🔹 SO 库内存优化

### 扩展（可选深入）

- 🔸 jemalloc / scudo allocator 差异

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要处理 Native 内存

Java Heap 没有持续增长，不代表进程内存安全。使用 JNI、音视频 SDK、地图 SDK、游戏引擎、图片库、加密库的应用，Native Heap、匿名 `mmap`、共享库映射和图形缓冲都可能把 PSS 推高，进而触发后台保活变差、前台卡顿、低内存杀进程，甚至 native crash。

本节面向应用侧排查：先把 Native 内存拆成能观察的几类，再选择 heapprofd、malloc_debug、ASan、HWASan、GWP-ASan、MTE 等工具定位问题。底层内存模型详见 4.1、4.2 节；工具细节详见 14.3 节。[结构参考: Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md]

## Native 内存由哪些部分组成

应用侧讨论 Native 内存时，容易把所有非 Java Heap 的增长都归到 `malloc`。排查时要拆开看，至少分四类：

- **Native Heap**：C/C++ 代码通过 `malloc`、`calloc`、`realloc`、`new` 申请的堆内存，常见来源是 JNI 层业务代码、第三方 so、音视频编解码、图片库和加密库。
- **匿名 `mmap` 区域**：代码直接用 `mmap` 申请的私有匿名映射，或者 allocator 内部向内核申请的大块 arena。`/proc/<pid>/smaps` 中可能显示为 `[anon:libc_malloc]`、`[anon:scudo:*]` 或业务自定义名称。
- **SO / ELF 映射**：`.so` 文件被动态链接器映射到进程地址空间后，会产生代码段、只读数据、可写数据、重定位相关页面。共享只读页面通常按 PSS 分摊，可写脏页由当前进程承担。
- **图形与硬件缓冲**：Bitmap 像素、OpenGL/Vulkan 纹理、Surface buffer、`dma-buf` 等可能计入 Native Heap、Graphics、GL 或 memtrack 相关分类。图片内存详见 23.2 节。

AOSP 的 `android_os_Debug.cpp` 在汇总 `dumpsys meminfo` 时会通过 libmeminfo 读取 `/proc/<pid>/smaps`；VMA 名称分类规则在 `androidprocheaps.cpp`，例如 `[heap]`、`[anon:libc_malloc]`、`[anon:scudo:*]`、`[anon:GWP-ASan*]` 会进入 Native Heap 相关统计，`.so`、`.jar`、`.apk` 等文件映射进入 code 相关统计。[已验证: AOSP android-16.0.0_r1, frameworks/base/core/jni/android_os_Debug.cpp; system/memory/libmeminfo/androidprocheaps.cpp]

这四类的处理动作不同：Native Heap 用分配栈定位；SO 映射看装载数量、重定位和脏页；图形缓冲看图像解码和渲染资源释放；匿名 `mmap` 要追调用方或自定义 VMA 名称。把它们混在一起，只会得到“Native 内存很大”这种不可执行的结论。

## 排查入口：先看趋势，再抓调用栈

Native 内存问题分两种：一次性峰值过高，或者存活内存随操作次数持续增长。前者多见于大图、模型、音视频缓冲和一次性解压；后者更像泄漏、缓存失控或对象池没有回收。

线下排查建议从三组数据开始：

```bash
# 1. 看系统口径的进程内存分类
adb shell dumpsys meminfo <package_or_pid>

# 2. 看 VMA 级别明细，适合确认 [anon:*]、.so、ashmem、dmabuf 等来源
adb shell cat /proc/<pid>/smaps > smaps.txt

# 3. 看 Native Heap 运行时统计，适合快速判断 malloc 分配量是否异常
adb shell dumpsys meminfo <pid> | grep -A 20 "Native Heap"
```

这三条命令只回答“哪一类在涨”。如果 Native Heap 增长明显，下一步采 heapprofd；如果 Graphics / GL / dma-buf 增长，回到图片和渲染资源排查路径；如果 `.so` 私有脏页异常，检查动态库装载、初始化写入和符号/重定位成本。

[已验证: 官方文档, https://source.android.com/docs/core/tests/debug/native-memory]

## heapprofd：默认首选的 Native Heap 分配画像

heapprofd 适合回答两个问题：哪条调用栈累计分配最多，哪条调用栈在快照时仍有大量存活分配。它是 Perfetto 的 native heap profiler，从 Android 10 开始可用，常用在开发包、profileable release 包、userdebug/eng 设备上。

这段配置用于采集指定进程的 Native Heap 分配，重点看 `process_cmdline` 和 `sampling_interval_bytes`：

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

采集后在 Perfetto UI 打开 trace，查看 Heap profile 火焰图。排查泄漏时看快照中的存活分配；排查抖动时看累计分配和分配频率。采样间隔越小，越容易捕获小对象，开销也更高。线上实验包不建议无差别开启，要按用户白名单、场景开关和采样窗口控制成本。

[已验证: 官方文档, https://perfetto.dev/docs/data-sources/native-heap-profiler]

## malloc_debug：本地复现时拿更完整的分配证据

`malloc_debug` 是 Bionic 提供的调试能力，能在分配前后加保护、记录 backtrace、导出 heap dump。它比 heapprofd 更偏调试，不适合普通线上包；在能复现的线下场景里，它能给出更细的分配记录。

这组命令展示的是调试思路：用 wrap 属性让目标应用冷启动时加载 malloc 调试配置，再复现操作并抓日志。具体选项要按 Android 版本核对 Bionic README。

```bash
adb shell setprop wrap.com.example.app '"LIBC_DEBUG_MALLOC_OPTIONS=backtrace logwrapper"'
adb shell am force-stop com.example.app
adb shell monkey -p com.example.app 1
adb logcat | grep -i malloc
```

`malloc_debug` 的限制来自系统属性、进程重启和运行开销，部分能力还需要 root、userdebug 或可调试设备。工程上常把它放在“本地复现后进一步确认”的位置，而不是第一入口。

[已验证: AOSP android-16.0.0_r1, bionic/libc/malloc_debug/README.md]

## ASan、HWASan、GWP-ASan、MTE 怎么选

Native 内存问题不只有泄漏。越界写、use-after-free、double free 会先表现为偶现 crash、数据损坏或 UI 异常，再在内存统计里留下噪声。检测工具按使用场景选择：

| 工具 | 适合场景 | 代价与边界 |
| --- | --- | --- |
| ASan | 开发阶段发现越界访问、use-after-free | 需要重新编译插桩，内存和运行时开销高，不适合常规 release 包 |
| HWASan | 64 位 Arm 开发包上的内存错误检测，速度和定位能力优于传统 ASan 场景 | 需要支持的系统镜像和编译配置，主要用于测试和预发 |
| GWP-ASan | 在较低开销下抽样捕获 native heap use-after-free、heap-buffer-overflow | 抽样检测，不保证每次问题都命中 |
| MTE | Arm Memory Tagging Extension，硬件标签检测越界和释放后访问 | 依赖硬件、系统版本和 manifest / 系统配置，模式不同会影响性能与报错时机 |

ASan / HWASan 偏测试构建，GWP-ASan 和 MTE 更适合在较低开销下扩大检测面。它们解决的是内存安全错误，不替代 heapprofd 的容量分析；heapprofd 能说明谁分配得多，sanitizer 能说明哪次访问越界或访问了已释放内存。

[已验证: 官方文档, https://developer.android.com/ndk/guides/memory-debug]
[已验证: 官方文档, https://developer.android.com/ndk/guides/gwp-asan]
[已验证: 官方文档, https://developer.android.com/ndk/guides/arm-mte]

## SO 库内存优化从三个口径入手

SO 库相关内存要拆成装载成本、运行时分配和可写脏页。三者对应不同动作。

### 装载成本：少装、晚装、按需装

一个 `.so` 被加载后，代码段、只读数据、重定位表和符号相关页面会进入进程地址空间。只看 APK 体积无法判断运行时内存，排查时要看进程 maps/smaps 中对应 so 的 RSS/PSS/Private Dirty。

可执行动作：

- 合并小型 native 模块，减少启动阶段 `dlopen` 数量；
- 把低频功能的 so 延后到功能入口加载；
- 清理未使用 ABI、未使用架构和重复打包的 so；
- release 包保留必要符号文件到构建产物，App 内不携带调试符号。

### 运行时分配：把大块分配变成可解释事件

第三方 so 分配异常时，单靠 `dumpsys meminfo` 只能看到 Native Heap 变大。heapprofd 或 malloc hook 能把分配归到调用栈；如果符号文件保留完整，还能还原到函数名和源码行。

工程上建议给 native 大对象建立统一分配入口，例如模型缓冲、音视频 frame buffer、解码输出池、压缩临时缓冲都经过封装层。封装层记录大小、用途、生命周期和调用栈摘要，线上只上报聚合数据；线下再打开 heapprofd 或 malloc_debug 做细查。

### 可写脏页：少改共享映射，少做启动期全量初始化

`.so` 的只读页面可以在多个进程间共享；页面一旦被当前进程写脏，就会变成私有成本。常见来源包括全局可变数据、启动期大表初始化、懒加载缓存写入和重定位后的可写段。

排查时对比同一 so 的 `Shared Clean`、`Private Dirty`、`Private Clean`。如果某个库的 `Private Dirty` 远高于同类模块，要检查它是否在启动期写入大块全局状态，或者把可延迟的数据提前初始化了。

## Native 内存监控方案

线上监控不应该复刻线下 profiler。用户设备上的目标是发现趋势、定位版本和场景，不能长期记录完整调用栈。

一套可控方案可以分三层：

- **基础指标层**：定时采集 PSS、RSS、Native Heap Alloc、Graphics、GL、线程数、fd 数，并带上页面、业务场景、前后台状态、设备内存档位。采集频率按场景设定，避免常驻高频轮询。
- **异常判定层**：同一用户同一会话内看增长斜率，例如进入页面前后、重复打开页面 N 次后、播放/拍摄/上传结束后。只用单点阈值容易误伤高内存设备或资源密集场景。
- **诊断触发层**：命中灰度规则后，对少量 debug/profileable 包触发 heapprofd、系统 meminfo 快照或业务侧 native 分配摘要。普通 release 包只上报聚合指标和场景标签。

指标上报要区分“占用高”和“泄漏”。缓存命中带来的短时 Native Heap 增长不一定是问题；退出场景、收到 `onTrimMemory()`、完成任务后仍不回落，才进入泄漏或缓存失控路径。

## 🔸 jemalloc / scudo allocator 差异

Android 应用通常不直接选择系统 allocator，但 allocator 会影响碎片率、释放回收、错误检测和 `smaps` 命名。排查时关注现象，不要把问题写成“换 allocator 就能解决”。

Scudo 的设计目标是提高 native heap 对越界、use-after-free、double free 等问题的抵抗能力，并在内存映射名称中留下 `[anon:scudo:*]` 一类线索。jemalloc 更强调通用分配性能和碎片控制。不同 Android 版本、设备配置和进程状态下，系统默认 allocator 与安全开关可能不同，应用侧结论要以设备上的 `smaps`、系统属性和 crash tombstone 为准。

[已验证: 官方文档, https://source.android.com/devices/tech/debug/scudo]
[待验证: 不同厂商 Android 14-16 user 版本默认 allocator 与安全开关清单]

## 排查清单

- `dumpsys meminfo` 中增长的是 Native Heap、Graphics/GL、Code，还是 Unknown？
- 同一操作重复 5-10 次后，退出场景是否回落？
- heapprofd 的存活分配火焰图中，最大路径是否来自业务 JNI、第三方 SDK、图片库或音视频库？
- Native crash 是否带有 ASan、HWASan、GWP-ASan、MTE 相关标记？
- 相关 so 是否有符号文件可用于地址还原？
- `smaps` 里同一 so 的 `Private Dirty` 是否异常偏高？
- 线上是否只采聚合指标，避免在用户设备上长期开启高开销调试能力？

## 参考资料

- [结构参考: Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md]
- [结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]
- [已验证: 官方文档, Debug native memory use, https://source.android.com/docs/core/tests/debug/native-memory]
- [已验证: 官方文档, Perfetto Native Heap Profiler, https://perfetto.dev/docs/data-sources/native-heap-profiler]
- [已验证: 官方文档, Memory error debugging and mitigation, https://developer.android.com/ndk/guides/memory-debug]
- [已验证: 官方文档, GWP-ASan, https://developer.android.com/ndk/guides/gwp-asan]
- [已验证: 官方文档, Arm MTE, https://developer.android.com/ndk/guides/arm-mte]
- [已验证: AOSP android-16.0.0_r1, bionic/libc/malloc_debug/README.md]
- [已验证: AOSP android-16.0.0_r1, frameworks/base/core/jni/android_os_Debug.cpp]
- [已验证: AOSP android-16.0.0_r1, system/memory/libmeminfo/androidprocheaps.cpp]
