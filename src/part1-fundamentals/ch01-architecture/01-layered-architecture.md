---
title: "Android 分层架构"
chapter: "1.1"
section: "1.1"
status: "finalized"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-25"
last_verified_against: "AOSP android-17.0.0_r1: system/core/init/main.cpp, frameworks/base ZygoteInit.java and SystemServer.java, frameworks/native SurfaceFlinger.cpp and libbinder, bionic linker namespaces; Android Common Kernel android17-6.18-2026-06_r6: drivers/android/binder.c and security/selinux/hooks.c"
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/guide/platform"
  - type: official
    path: "https://source.android.com/docs/core/architecture/hal"
  - type: official
    path: "https://source.android.com/docs/core/architecture/aidl/aidl-hals"
  - type: official
    path: "https://source.android.com/docs/core/architecture/vintf"
  - type: official
    path: "https://source.android.com/docs/core/ota/modular-system"
  - type: official
    path: "https://source.android.com/docs/core/architecture/vndk"
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/"
  - type: source
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/"
tags: [architecture, 分层架构, HAL, HIDL, AIDL, Binder, SystemServer, Zygote, SurfaceFlinger, Perfetto]
related_chapters: ["1.2", "1.3", "1.4", "1.11", "2.1", "3.1", "4.1", "5.1", "7.1"]
pipeline_stage: "ready-to-publish"
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed
review_notes: "2026-07-25 Android 17/API 37 全文复审：以 android-17.0.0_r1 与 android17-6.18-2026-06_r6 重建源码锚点；删除未实测的 Binder/JNI/SELinux/Zygote/VNDK 数值、固定线程池经验、设备形态推断、内部调研记录和私有路径；修正 JNI 不是进程切换、Perfetto 数据源不与架构层一一对应、SystemServer Android 17 还调用 startApexServices 等表述。"
reviewed_date: "2026-07-14"
reviewed_by: "openclaw-task6"
polish_count: 1
polish_date: "2026-04-05"
polish_by: "task2b-polish"
task9_reviewed_date: 2026-07-14
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-07-14T17:26:54+08:00"
task9_review_notes: "2026-07-14 Task9 round-3 复审（post-Task2B fix）: pass-tech-review。P0=0 / P1=0。复核 SurfaceFlinger 切片表 android-17 行已添加、16KB Page Size 三层边界（AOSP 构建 / 设备配置 / Google Play）声明清晰、last_verified_against 锚定 android-17.0.0_r1 等修复全部到位。P2 3 处已写入 suggestions.md（USAP 量化、ProcessState.cpp 行号、binder.c spawn 守门行号待验证），P3 3 处仅日志记录。满足自动晋升条件 → ✅ finalized。"
last_task6_at: "2026-07-14T21:09:00+08:00"
last_task6_audit: "2026-07-06"
last_task6_review_log: "logs/review/2026-07-14-21-review.md"
last_task6_audit_log: "logs/review/2026-06-25-10-audit.md"
task6_review_notes: "07-14 21 Task6 re-review (post-Task2B fix): pass-light-edit。L2 小修 1 处（outline 锚点 Android 16→15-17 与正文标题对齐）；frontmatter 去重 last_task6_review_log；outline 5/5 覆盖、2/3 扩展；L1 禁用词扫描全清。Task9 needs-rework P1:2 已由 Task2B 修复（SF切片表缺android-17行+版本锚点），待 Task9 复审。"
last_task9_audit: "2026-07-08"
task9_review_log: logs/deep-review/2026-07-14-21-deep-review.md
reviewed_at: "2026-05-18T08:31:45+08:00"
task6_reviewed_date: "2026-07-14"
finalized_date: "2026-07-14"
finalized_by: "openclaw-task9-auto-promote"
last_task9_review_log: logs/deep-review/2026-07-14-17-deep-review.md
last_task2b_at: 2026-07-14T20:51:00+08:00
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-15
last_task9_autofix_at: "2026-07-08"
last_task9_audit_log: "logs/deep-review/2026-07-08-18-audit.md"
---

# 1.1 Android 分层架构

Android 的“五层架构”是一张职责地图，不是五个严格套叠的进程。一个应用进程同时包含应用代码、Framework 客户端代码、ART 和原生库；`system_server` 既运行 Java 系统服务，也加载 JNI 库；SurfaceFlinger 是独立的原生服务进程；HAL 既可能通过 Binder 跨进程提供服务，也可能以同进程共享库存在于旧实现中。

这张地图仍然很有用。面对一段卡顿、启动慢或硬件访问延迟，先确定工作发生在哪个进程，再确认它通过 Binder、JNI、系统调用还是 HAL 接口进入下一段代码。进程、接口和调度状态共同构成证据，单看“属于哪一层”不足以定位问题。

## 五层分别解决什么问题

Android 通常从上到下分为应用、应用框架、原生库与 ART、HAL、Linux 内核五层：

```mermaid
flowchart TB
    Apps["应用：业务代码与系统应用"]
    Framework["应用框架：SDK 客户端与 system_server 服务"]
    Native["原生库与 ART：运行时、Bionic、Skia、媒体与原生服务"]
    HAL["HAL：Stable AIDL、存量 HIDL 与厂商实现"]
    Kernel["Linux 内核：调度、内存、Binder、网络与驱动"]

    Apps -->|"SDK 调用 / Binder"| Framework
    Framework -->|"JNI / Native Binder"| Native
    Framework -->|"Stable AIDL / HIDL"| HAL
    Native -->|"系统调用 / ioctl / mmap"| Kernel
    HAL -->|"系统调用 / 驱动接口"| Kernel
```

图中的箭头表示常见接口，不表示所有请求都必须逐层经过。例如，应用可以直接通过 Bionic 发起文件系统调用，SurfaceFlinger 可以直接与 Composer HAL 和内核 DRM/显示驱动交互，媒体数据也常通过共享缓冲区传递。

| 层次 | Android 17 中的典型对象 | 主要边界 | 性能分析入口 |
| --- | --- | --- | --- |
| 应用 | `Activity`、Compose/View、业务线程、RenderThread | SDK、Binder、JNI、文件与网络 API | 应用主线程、RenderThread、自定义 trace、FrameTimeline |
| 应用框架 | `ActivityTaskManagerService`、`WindowManagerService`、`PackageManagerService` 等 `system_server` 服务 | Java Binder、Native Binder、系统服务内部锁 | `system_server` Binder 线程、服务 trace slice、锁与调度状态 |
| 原生库与 ART | ART、Bionic、Skia、SQLite、SurfaceFlinger、AudioFlinger、media 服务 | JNI、Native Binder、共享内存、系统调用 | ART GC/JIT、native slice、调用栈、原生堆与系统调用 |
| HAL | Stable AIDL HAL、存量 HIDL HAL、厂商服务或同进程实现 | Binder、hwbinder、FMQ、共享缓冲区、设备节点 | HAL 服务进程、Binder transaction、锁、I/O 与硬件 fence |
| Linux 内核 | 调度器、内存管理、Binder 驱动、网络栈、文件系统、DMA-BUF 与设备驱动 | 系统调用、`ioctl`、`mmap`、中断 | ftrace、线程状态、CPU 频率、I/O、Binder 与驱动事件 |

本书的 Android 17 平台代码统一锚定 AOSP `android-17.0.0_r1`。内核部分统一锚定 Android Common Kernel `android17-6.18-2026-06_r6`。量产设备会在 ACK 之上增加 SoC 驱动、GKI vendor module、产品配置和厂商调度策略，因此公共内核 tag 不能替代设备自己的 kernel commit 与配置。

## 启动过程把这些层连在一起

Android 17 的 `system/core/init/main.cpp` 仍然按 first stage、SELinux setup 和 second stage 进入 init。second-stage init 解析 rc 配置并启动 Zygote、SurfaceFlinger 等服务。Zygote 随后预加载常用类和资源，fork `system_server`，再进入命令 socket 循环等待创建应用进程。

`frameworks/base/core/java/com/android/internal/os/ZygoteInit.java` 的 `main()` 给出了这条顺序：

1. 未启用 lazy preload 时调用 `preload()`。
2. 创建 `ZygoteServer`。
3. 主 Zygote 调用 `forkSystemServer()`。
4. 父进程进入 `zygoteServer.runSelectLoop()` 接收后续 fork 请求。

`system_server` 子进程最终进入 `SystemServer.main()`。Android 17 的服务启动骨架如下，重点是第四个 `startApexServices()`；旧资料只列前三组会漏掉 APEX 服务阶段。

```java
// AOSP android-17.0.0_r1
// frameworks/base/services/java/com/android/server/SystemServer.java
startBootstrapServices(t);
startCoreServices(t);
startOtherServices(t);
startApexServices(t);
```

这段代码证明的是启动分组和调用顺序。它不能证明所有服务都在主线程串行完成初始化：各组内部可以使用专门线程或 `SystemServerInitThreadPool` 执行允许并行的工作。排查开机耗时时，应从 `SystemServerTiming`、init service 事件和具体线程 slice 还原实际执行。

应用冷启动还会经过另一个方向：应用或 Launcher 通过 Binder 请求 `system_server` 中的 Activity/Task 管理服务，系统服务通过 Zygote socket 请求 fork，子进程进入 `ActivityThread.main()`，再通过 Binder 向 `system_server` 完成 attach。这里同时存在 Binder 和本地 socket，不能把整条启动路径统称为 Binder 调用。

## 三类跨边界接口

### Binder：跨进程控制面

Binder 由用户态 `libbinder` 与内核 Binder 驱动共同完成。Android 17 的 `frameworks/native/libs/binder/ProcessState.cpp` 定义了接收 transaction 的映射区，以及默认写入 `BINDER_SET_MAX_THREADS` 的动态线程上限：

```cpp
// AOSP android-17.0.0_r1
#define BINDER_VM_SIZE ((1 * 1024 * 1024) - sysconf(_SC_PAGE_SIZE) * 2)
#define DEFAULT_MAX_BINDER_THREADS 15
```

`DEFAULT_MAX_BINDER_THREADS = 15` 不是进程内 Binder 线程总数。`ProcessState::startThreadPool()` 另行启动池中的首个线程；内核在没有等待线程、尚无未完成的增线程请求、驱动请求启动的线程数低于 `max_threads`，且当前线程已经进入 Binder looper 等条件成立时，通过 `BR_SPAWN_LOOPER` 请求用户态增加线程。手工调用 `IPCThreadState::joinThreadPool()` 的线程也不包含在这 15 个驱动请求名额中。`setThreadPoolMaxThreadCount()` 会使用 `BINDER_SET_MAX_THREADS` 配置驱动，而且线程池启动后不能缩小已有上限。

这些常量不能直接变成“应用用 4 到 8 个、系统服务用 30 到 50 个”之类的通用建议。线程数太少会让长事务阻塞后续请求，线程数太多会增加并发、锁竞争和内存成本。调整前要用 Perfetto 和服务日志确认：

- 调用方是否在同步等待 Binder reply；
- 目标进程是否没有空闲 Binder 线程；
- 处理线程是在运行、等待 CPU、等锁还是等 I/O；
- 长事务来自少数异常请求，还是稳定的并发容量不足。

Binder 的 transaction 数据由驱动从发送方用户空间复制到接收方可映射的 Binder buffer，常被概括为“一次拷贝”。文件描述符转换、对象解析、权限检查、线程调度和目标服务执行仍会产生开销。同步 Binder 的端到端延迟由整条请求决定，不能用“一次拷贝”推导调用一定很快。

SELinux 也在 transaction 路径上参与授权。ACK `android17-6.18-2026-06_r6` 的 `security/selinux/hooks.c` 中，`selinux_binder_transaction()` 会检查 `BINDER__CALL`；当前凭据与 transaction 发起方凭据不同时，还会检查 `BINDER__IMPERSONATE`。源码只能证明检查与条件存在；没有同设备、同策略与同负载的测量，不能给它写固定纳秒开销。

### JNI：同一进程里的托管代码与原生代码边界

JNI 不是进程切换，也不会因为进入 C/C++ 就自动发生 Binder 或内核态切换。它是同一进程内从 ART 托管执行环境进入原生函数的 ABI 边界。成本来自调用约定、线程状态转换、引用管理、参数转换、数组或字符串的复制/固定，以及原生函数自身的工作。

优化 JNI 时优先减少跨边界次数和数据转换：

- 循环中的细粒度调用可以改成一次批量调用，但要同时评估额外内存与延迟。
- 大块二进制数据可以评估 direct buffer 或其他共享表示，避免反复构造 Java 对象。
- `@FastNative` 与 `@CriticalNative` 只适用于满足签名和运行时约束的系统级场景，不能按一组固定倍数估算收益。

是否值得调整要用目标设备上的基准和调用栈判断。空 JNI benchmark 的纳秒结果不能代表包含字符串、数组、锁和 I/O 的业务调用。

### 系统调用与共享缓冲区：数据面常走另一条路

高吞吐数据不适合反复塞进 Binder parcel。图形、相机和音频通常把 Binder 用作控制面，再用 BufferQueue、DMA-BUF、共享内存、FMQ 或硬件 buffer 传递数据和同步信息。

这类问题要把控制命令、buffer 生命周期和 fence 分开观察。一次相机请求可以很快完成 Binder 往返，却仍然长时间等待传感器、ISP 或 buffer fence；一次显示提交也可能在 SurfaceFlinger 侧很短，而 GPU 或 HWC 的完成时间更晚。

## Treble、HIDL 与 Stable AIDL

Project Treble 从 Android 8.0 开始约束 framework/vendor 边界。VINTF manifest、framework compatibility matrix、device compatibility matrix 和稳定 HAL 接口共同决定 system 与 vendor 是否兼容。Treble 提供 framework-only 更新成立所需的接口边界，但并不保证任意 framework 与任意 vendor 组合都兼容，组合仍要通过 VINTF 与兼容性测试。

HIDL 时代需要区分两种传输：

- binderized HIDL HAL 以服务进程运行，常使用 `/dev/hwbinder`。
- passthrough HIDL HAL 以共享库加载到调用方进程，调用路径中没有独立 HAL 服务进程。

新 HAL 接口已经转向 Stable AIDL。用于 system/vendor 边界的 AIDL HAL 需要 VINTF stability，并以 Binder 服务运行。旧 HIDL HAL 仍可能为了兼容已有 vendor image 保留，Android 17 设备上不能仅凭系统版本假定全部 HAL 都已经迁移。

排查 HAL 延迟时按实际传输模式处理：

1. 从 Framework 或原生客户端找到接口调用与目标服务。
2. binderized 服务沿 Binder flow 进入 HAL 进程，检查服务线程、锁、系统调用与 fence。
3. passthrough 实现留在调用方进程，检查原生调用栈和共享库内部等待。
4. 涉及数据面的请求继续追 buffer、FMQ、DMA-BUF 与驱动事件，不能停在控制面 reply。

## Android 15 到 Android 17 的三个架构边界

### 16 KB page size

从 Android 15 开始，AOSP 支持配置为 16 KB page size 的设备。应用只包含 Java/Kotlin 代码时通常不需要为 ELF 对齐做改造；包含 NDK 库或通过 SDK 间接引入 `.so` 时，需要检查 ELF LOAD segment 和 APK 内未压缩 native library 的 zip 对齐。

设备运行时页大小可直接读取：

```bash
adb shell getconf PAGE_SIZE
```

`4096` 表示 4 KB，`16384` 表示 16 KB。Android Developers 文档公布的启动、功耗和系统启动收益来自 Google 的初始测试，并明确说明实际设备结果会不同。它们适合作为测试方向，不能作为任意应用或设备的预期收益。

Google Play 自 2025 年 11 月 1 日起要求面向 Android 15 及以上设备的新应用和更新支持 16 KB page size。这是应用分发兼容要求，不等于所有 Android 15、16 或 17 设备都运行在 16 KB 模式。

### Mainline 模块

Mainline 把一部分系统组件封装为 APEX 或 APK，使它们可以通过 Google Play system update 或合作伙伴 OTA 独立更新。Android 17 的 `SystemServer.run()` 也明确执行每进程 Mainline module 初始化，并在常规服务组之后调用 `startApexServices()`。

分析问题时，Android 版本号不足以唯一确定 ART、Media、Wi-Fi、Bluetooth 等模块的实现。报告应同时记录 build fingerprint、相关 APEX/APK 版本和复现时间。模块更新可能改变实现，但仍受稳定 SDK/System API、稳定 C API 或 Stable AIDL 边界约束。

### VNDK deprecation 与 linker namespace

VNDK 从 Android 15 开始废弃。新 vendor 或 product 分区不再声明 `ro.vndk.version`，原 VNDK libraries 按 vendor-available library 的方式安装到 vendor 或 product image；为旧 vendor image 提供兼容的 VNDK APEX 仍可能存在。

VNDK 废弃没有删除动态链接器命名空间。Android 17 的 `bionic/linker/linker_namespaces.cpp` 中，隔离命名空间仍通过 `android_namespace_t::is_accessible()` 检查 `allowed_libs_`、library search paths 和 `permitted_paths_`。这段源码支持“加载前存在可访问性校验”，不能推出固定的启动耗时比例。`dlopen()` 成本要结合加载库数量、搜索路径、文件系统缓存、重定位、RELRO 和构造函数一起测量。

## SurfaceFlinger 说明了“层”和“进程”为什么不能混为一谈

WindowManagerService 运行在 `system_server`，负责窗口容器、层级、焦点、配置和策略。SurfaceFlinger 是 init 启动的独立原生服务，负责接收 layer 状态与 buffer，借助 CompositionEngine、RenderEngine 和 Composer HAL 生成显示输出。二者协作，但不在同一进程，也不能简单归入同一个“Framework 进程”。

Android 17 的 `frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp` 中，主刷新路径包含：

- `SurfaceFlinger::commit(...)`：提交本轮状态并决定是否需要合成。
- `SurfaceFlinger::composite(...)`：进入各显示设备的合成与 present 路径。
- `postComposition` trace：记录合成后的处理阶段。

历史 trace 的搜索词会变化：

| 版本范围 | 建议先查的 SurfaceFlinger 入口 | 边界 |
| --- | --- | --- |
| Android 17 | `commit <vsyncId>`、`composite <vsyncId>`、`postComposition` | 以 `android-17.0.0_r1` 为当前基线 |
| Android 15-16 | `commit <vsyncId>`、`composite <vsyncId>`；再按 tag 确认 post-composition 标记 | 不把 Android 17 的 trace 宏与名称直接套到旧 tag |
| Android 13-14 | `commit`、`composite` 与对应 post-composition 路径 | 名称是否带 VSync ID 要以设备 trace 为准 |
| Android 11-12 | `onMessageInvalidate`、`onMessageRefresh`、CompositionEngine present 路径 | 仍是消息驱动入口 |
| Android 10 及以前 | `onMessageReceived`、`handleMessageRefresh`、`doComposition` | 只用于历史设备与版本演进 |

`composite` 变长也不能直接判定 GPU 过载。还要检查 HWC composition decision、present fence、RenderEngine、display mode、layer 数量和驱动等待。

## 在 Perfetto 中按因果关系定位

Perfetto 数据源与五层架构没有一一对应关系：

- `linux.ftrace` 可以提供调度、频率、I/O、Binder 驱动和部分驱动事件。它来自内核，但描述的线程可能属于应用、系统服务或 HAL。
- ATrace/TrackEvent 是用户态埋点机制。应用、Framework、原生服务和 HAL 都可以产生 slice，category 是采集开关，不是架构层名称。
- process stats、heap profiling、FrameTimeline、power counters 等数据源各自回答特定问题，不能合并成一个“上层数据源”。

一次跨进程等待可以按下面的顺序读：

1. 在调用方找到同步 Binder slice，确认发起线程和 transaction。
2. 沿 flow 找到目标进程的处理线程。
3. 检查目标线程处于 Running、Runnable、Sleeping 还是 Uninterruptible Sleep。
4. Running 表示线程正在 CPU 上执行，仍需用 slice 或调用栈判断执行内容。
5. Runnable 表示已经可运行但尚未获得 CPU，结合优先级、CPU 利用率、频率和 thermal 信息判断调度延迟。
6. Sleeping 可能是 Binder reply、futex、epoll 或定时等待；Uninterruptible Sleep 常见于不可中断的内核等待，但仍要用 wchan、I/O 与驱动事件确认对象。

Binder flow 只说明 transaction 关系。调用方 slice 的持续时间、目标线程的排队时间和服务执行时间需要分别计算，不能根据箭头视觉长度直接下结论。

## 三个常见排障场景

| 现象 | 第一组证据 | 向下追踪 | 不应直接得出的结论 |
| --- | --- | --- | --- |
| 应用主线程同步 Binder 很长 | 调用方 Binder slice、目标进程与目标线程 | 目标线程调度、锁、I/O、服务代码与下游 Binder | “Binder 驱动慢” |
| `surfaceflinger` 的 `composite` 变长 | SF 主线程、CompositionEngine、HWC/RenderEngine 事件 | composition type、fence、GPU/HWC、显示模式与 layer 变化 | “一定是应用绘制慢” |
| Camera 请求返回慢 | Framework/CameraService/HAL transaction 与 request ID | HAL 线程、FMQ/buffer、fence、驱动与传感器时间 | “HAL 只是接口，不会产生延迟” |

定位不能停在调用 API 的进程，还要继续寻找接收进程、执行线程和内核等待对象。每多跨一个边界，都要保存 transaction ID、线程 ID、时间范围或源码符号，避免只凭相邻事件建立因果关系。

## 容易混淆的六个判断

- **SurfaceFlinger 不在 `system_server`。** 它是独立原生服务；WMS 与 SurfaceFlinger 通过明确接口协作。
- **Zygote fork 不会立即复制全部物理内存。** Copy-on-Write 让父子进程共享未修改页面；后续写入、ART 运行和应用初始化会逐步产生私有页。
- **HAL 不等于独立进程。** Stable AIDL HAL 是 Binder 服务，存量 HIDL 还要区分 binderized 与 passthrough。
- **JNI 不等于 IPC。** JNI 在同一进程内跨托管/原生边界；原生函数随后是否发起系统调用或 Binder 是另一件事。
- **Binder 一次拷贝不等于端到端低延迟。** 排队、调度、权限检查、对象解析、目标服务和下游依赖都会进入总耗时。
- **应用现象不保证根因位于应用层。** `system_server`、SurfaceFlinger、HAL、驱动与硬件等待都可能把延迟传回应用。

## Android 17 源码入口

以下路径用于复核上述结论：

1. init 三阶段入口：`system/core/init/main.cpp`，AOSP `android-17.0.0_r1`。
2. Zygote preload、fork SystemServer 与 socket loop：`frameworks/base/core/java/com/android/internal/os/ZygoteInit.java`，AOSP `android-17.0.0_r1`。
3. SystemServer 服务分组：`frameworks/base/services/java/com/android/server/SystemServer.java`，AOSP `android-17.0.0_r1`。
4. SurfaceFlinger commit/composite：`frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp`，AOSP `android-17.0.0_r1`。
5. Binder 用户态线程池：`frameworks/native/libs/binder/ProcessState.cpp` 与 `IPCThreadState.cpp`，AOSP `android-17.0.0_r1`。
6. 动态链接器命名空间：`bionic/linker/linker_namespaces.cpp`，AOSP `android-17.0.0_r1`。
7. Binder 驱动：`drivers/android/binder.c`，ACK `android17-6.18-2026-06_r6`。
8. Binder SELinux hook：`security/selinux/hooks.c`，ACK `android17-6.18-2026-06_r6`。

固定 tag、项目路径和符号一起使用，才能把架构图中的箭头还原成可验证的运行路径。
