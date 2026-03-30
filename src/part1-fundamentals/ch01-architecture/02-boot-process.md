---
title: "系统启动全流程"
chapter: "1.2"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 16 (API 35)"
last_verified: "2026-07-17"
last_verified_against: "AOSP android-16.0.0_r1, 官方文档"
confidence: high
sources:
  - type: aosp
    path: "system/core/init/init.cpp @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/ZygoteInit.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/java/com/android/server/SystemServer.java @ android-16.0.0_r1"
  - type: official
    path: "https://source.android.com/docs/core/architecture"
  - type: official
    path: "https://source.android.com/docs/core/boot"
  - type: blog
    path: "https://source.android.com/docs/core/perf/boot-times"
  - type: blog
    path: "obsidian/Cubox/Android 启动系列之我是 init 进程 - 掘金-2024-01-27.md"
tags: ['boot', 'init', 'zygote', 'SystemServer', '启动优化', 'bootchart']
related_chapters: ["1.1", "1.3", "1.4", "8.2"]
---

# 系统启动全流程

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 完整启动链：Bootloader → Linux Kernel → init → Zygote → SystemServer → Launcher
- 🔹 init 进程的职责：解析 init.rc、启动关键 native 服务（servicemanager、surfaceflinger 等）
- 🔹 Zygote 预加载机制：preloadClasses / preloadResources，对首次 App 启动的影响
- 🔹 SystemServer 启动的核心服务顺序及依赖关系（AMS、WMS、PMS 等）
- 🔹 启动时间的度量：boot_completed 广播、BootTimingsTraceLog
- 🔹 开机性能优化的常见手段（并行启动、延迟加载、cgroup 优先级）

### 扩展（可选深入）

- 🔸 AB 分区与 Virtual A/B 对 OTA 和启动时间的影响
- 🔸 dm-verity / AVB 对启动链的安全与性能权衡
- 🔸 各厂商 boot 优化黑科技概述

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 Android 启动流程

当我们按下手机电源键，到看到桌面图标可点击，中间经历了一条长长的时间线。这条时间线涉及硬件初始化、内核启动、用户空间构建、Java 运行时准备、系统服务启动，最终才把一个可用的 Android 桌面呈现在我们面前。

了解这条链路的意义远不止"知道就行"。在实际的性能优化工作中，启动流程中的每一个环节都可能成为瓶颈：

- 开机时间太长——用户抱怨"等半天才能用"。这可能是 init 阶段挂载分区慢了，也可能是 SystemServer 启动了太多不必要的服务。
- 冷启动 App 慢——这和 Zygote 的预加载机制直接相关。了解预加载了什么、没预加载什么，才能判断 App 启动时哪些类需要重新加载。
- OTA 升级后首次开机特别慢——这与 dm-verity 校验和 AB 分区切换有关。

在 Perfetto 中，我们可以抓取开机阶段的 Trace，看到 init、Zygote、SystemServer 各自消耗了多少时间。但如果你不了解这条链路的来龙去脉，面对 Trace 中的那些色块，只会一头雾水。读完本节后，你应该能打开一份开机 Trace，准确地找到每个阶段对应的区间，并定位到耗时异常的环节。

## 完整启动链：从按下电源到桌面可见

Android 的启动是一个严格的有序过程，前一阶段为后一阶段准备运行环境。我们用一个完整的时序图来梳理这条链路：

```
[图：Android 启动全流程时序图]
Boot ROM → Bootloader → Linux Kernel → init → Zygote → SystemServer → Launcher
   │            │             │          │        │          │            │
   │            │             │          │        │          │            └─ 显示桌面
   │            │             │          │        │          └─ 启动核心系统服务
   │            │             │          │        └─ 预加载类/资源 → fork App 进程
   │            │             │          └─ 解析 init.rc，启动 native 服务
   │            │             └─ 硬件驱动、内存管理、进程调度
   │            └─ 加载 Kernel、 recovery/OTA 相关
   └─ 芯片内置 ROM 代码
```

下面我们逐阶段深入。

### Boot ROM 与 Bootloader：硬件的"第一口气"

当我们按下电源键的那一刻，CPU 从芯片内置的 Boot ROM 中开始执行代码。这段代码是出厂时固化在芯片中的，它的任务非常简单：初始化最基本的硬件（时钟、RAM 控制器），然后找到并加载 Bootloader。

Bootloader（Android 设备上通常是 U-Boot 或厂商自研的引导程序）接管后，负责更完整的硬件初始化：配置显示器、设置 USB、加载设备树（Device Tree）。Bootloader 最重要的工作是**加载 Linux Kernel**。

在 Bootloader 阶段，如果设备处于 OTA 升级状态，Bootloader 还需要决定从哪个分区启动（A 分区还是 B 分区）。这就是 Android 的无缝更新机制的基础。[待补充：Bootloader 阶段的 Perfetto Trace 截图]

### Linux Kernel：搭建操作系统的地基

Bootloader 将 Linux Kernel 加载到内存后，内核开始执行。这个阶段的工作包括：

1. **硬件驱动初始化**：GPU、Display、Audio、Modem 等底层驱动逐一加载
2. **内存管理初始化**：建立页表、启动内存分配器
3. **文件系统挂载**：挂载 rootfs 和关键分区（system、vendor 等）
4. **内核线程启动**：创建 kthreadd（内核线程的鼻祖）、kworker 等内核线程

内核启动的最后一步是启动 **swapper/idle 进程**（PID 0）——这是 Linux 系统中所有进程的真正起点。swapper 进程通过 `kernel_thread()` 创建两个子进程 [已验证: AOSP goldfish/init/main.c, `rest_init()`]：

```c
// init/main.c
noinline void __ref rest_init(void)
{
    int pid;
    // 创建 init 进程 (PID 1) - 用户空间所有进程的鼻祖
    pid = kernel_thread(kernel_init, NULL, CLONE_FS);
    // 创建 kthreadd 进程 (PID 2) - 内核空间所有线程的鼻祖
    pid = kernel_thread(kthreadd, NULL, CLONE_FS | CLONE_FILES);
    ...
}
```

这里有一个关键的转换：init 进程最初是内核线程，通过调用 `do_execve()` 执行 `/sbin/init`（或 `/init`），从内核态切换到用户态，正式成为**用户空间第一个进程**。

### init 进程：用户空间的"总指挥"

init 进程是 Android 用户空间所有进程的鼻祖，PID 永远是 1。如果说 swapper（PID 0）是内核空间的起点，那 init 就是用户空间的起点。它的核心职责可以归纳为四件事：

1. **解析和执行 init.rc 脚本**，建立整个用户空间的运行环境
2. **启动关键的 native 服务**（servicemanager、surfaceflinger、lmkd 等）
3. **管理属性系统**（property service），为系统范围内的配置提供读写机制
4. **监听和服务生命周期管理**——如果关键进程崩溃，init 负责重启它们

#### init.rc：Android Init Language

init 进程不会硬编码"我要启动哪些服务"。它采用了一套声明式的脚本语言——**Android Init Language**（文件后缀为 `.rc`），把"启动什么、什么时候启动、怎么启动"全部外置到配置文件中。[来源: obsidian/Cubox/Android 启动系列之我是 init 进程 - 掘金-2024-01-27.md]

init.rc 的核心语法只有几个关键字：

```rc
# 定义一个服务
service servicemanager /system/bin/servicemanager
    class core animation
    user system
    critical
    onrestart restart apexd

# 在特定阶段触发动作
on init
    # 执行命令
    mkdir /cache/recovery 0770 system cache
    # 启动服务
    start servicemanager
```

`on` 关键字定义了触发条件（也叫 action），常见的触发阶段有严格的先后顺序 [已验证: AOSP system/core/init/init.cpp]：

```
early-init → init → late-init → early-fs → fs → post-fs → late-fs → early-boot → boot → late-boot
```

这个顺序至关重要。比如，servicemanager 必须在 `init` 阶段启动，因为后续几乎所有进程都依赖 binder 通信；而 surfaceflinger 的启动可以稍晚一些。

#### 关键 native 服务的启动顺序

init 启动的 native 服务中，最重要的几个及其作用：

| 服务 | 启动阶段 | 核心作用 |
|------|----------|----------|
| **servicemanager** | `on init` | Binder 通信的"名字服务"，管理所有 Binder 服务的注册与查找 |
| **surfaceflinger** | `on core`（稍后于 init） | 图形合成引擎，负责将多个图层的渲染结果合成为最终显示画面 |
| **lmkd** | `on init` | Low Memory Killer Daemon，在内存不足时杀掉低优先级进程 |
| **logd** | `on init` | 系统日志守护进程 |
| **hwservicemanager** | `on init` | HIDL 服务的注册管理（用于 HAL 层通信） |

其中，**servicemanager 必须最先启动**。因为它为整个 Binder 通信体系提供名字服务——所有后续进程（包括 Zygote 和 SystemServer）要进行 IPC 通信，都需要先到 servicemanager 注册或查找服务。

[自动发现: 来源 obsidian/Cubox/Android 启动系列之我是 init 进程 - 掘金-2024-01-27.md] init 进程采用"被动创建"模式——它不关心要创建哪些子进程，而是让各模块自己通过 .rc 文件声明。这种设计使得 Android 的启动配置高度模块化，每个模块（比如 Wi-Fi、蓝牙）可以有自己的 .rc 文件，通过 `import` 指令引入主配置。

[待补充：init 阶段在 Perfetto 中的表现截图]

### Zygote：Java 世界的"孵化器"

init 进程通过 init.rc 中的配置启动 Zygote。Zygote 是 Android 中最巧妙的进程设计之一，它解决了一个核心问题：**如何让 App 启动既快又省内存？**

如果没有 Zygote，每次启动一个 App 都需要：
1. fork 一个新进程
2. 启动 ART 虚拟机
3. 加载几千个基础类（Activity、View、Context 等）
4. 加载资源（图片、字符串、布局等）

这个过程可能需要数秒。Zygote 的方案是：**提前把这些工作做一次，之后所有 App 进程通过 fork 复用这些成果。**

#### Zygote 的预加载机制

Zygote 进程启动后，会执行一系列预加载操作 [已验证: AOSP frameworks/base/core/java/com/android/internal/os/ZygoteInit.java]：

1. **preloadClasses()**：加载预定义的 Java 类列表。这些类定义在 `/apex/com.android.art/etc/preloaded-classes` 文件中（Android 10+ 使用 APEX 模块管理），通常包含 3000-4000 个常用类——Activity、Fragment、View、TextView 等全部在其中。
   
2. **preloadResources()**：预加载常用资源，包括系统主题、默认字体、常用图片等。
   
3. **preloadDexCaches()**：预热 DEX 文件的方法调用缓存，让后续 App 不需要重新解析这些方法。
   
4. **preloadSharedLibraries()**：加载常用的 native 库（如 androidhwui、skia 等）。

Zygote 完成预加载后，就进入"等待"状态，监听 Unix 域套接字上的请求。当 SystemServer 或 AMS 需要创建新的 App 进程时，会通过这个套接字通知 Zygote，Zygote 调用 `fork()` 创建子进程。

#### fork() 与 Copy-on-Write

fork 的妙处在于 **Copy-on-Write（CoW）** 机制。新 fork 出来的子进程和父进程（Zygote）共享同一块物理内存，只有在子进程试图修改某个内存页时，内核才会为子进程创建该页的独立副本。

这意味着：
- 所有 App 进程共享 Zygote 预加载的那几千个类和资源，内存开销极小
- App 进程启动时不需要重新加载这些类，启动速度大幅提升
- 在 Perfetto 中，你可以看到 App 进程启动后很快就开始执行 Application.onCreate()，不需要再花时间加载基础类

但这也带来了一个限制：**Zygote 预加载之后，不能再加载新的 class 或资源到共享区域**。这就是为什么 Zygote 启动后的类加载都只影响当前进程。

[待补充：Zygote 预加载阶段在 Perfetto 中的 Trace 表现]

### SystemServer：系统服务的"大管家"

Zygote 预加载完成后，第一件事就是 **fork 出 SystemServer**。这是一个硬编码的行为，定义在 `ZygoteInit.java` 中 [已验证: AOSP frameworks/base/core/java/com/android/internal/os/ZygoteInit.java, `startSystemServer()` 方法]：

```java
// ZygoteInit.java
private static boolean startSystemServer(...)
        throws MethodAndArgsCaller, RuntimeException {
    // 硬编码参数，启动 SystemServer
    String args[] = {
        "--setuid=1000",
        "--setgid=1000",
        "--setgroups=...",
        "--capabilities=...",
        "--runtime-args",
        "com.android.server.SystemServer",
    };
    // fork SystemServer 进程
    pid = Zygote.forkSystemServer(...);
    ...
}
```

SystemServer 启动后，会在自己的进程中按顺序启动 Android Framework 的核心服务。这些服务分为三个阶段 [已验证: AOSP frameworks/base/services/java/com/android/server/SystemServer.java]：

#### 第一阶段：Bootstrap Services

最基础的服务，后续所有服务都依赖它们：

- **ActivityManagerService (AMS)**：管理所有 Activity 的生命周期、进程调度
- **PackageManagerService (PMS)**：管理已安装应用的信息
- **PowerManagerService**：电源管理
- **DisplayManagerService**：显示管理
- **SensorService**：传感器服务

其中 AMS 尤为关键——它不仅管 Activity，还负责整个进程级别的调度。在 Perfetto 中，如果你看到某个 App 进程被创建或被杀，那背后都是 AMS 在操作。

#### 第二阶段：Core Services

基础服务就位后，启动核心服务：

- **WindowManagerService (WMS)**：窗口管理，决定哪个窗口显示在最前面
- **InputManagerService**：输入事件管理（触摸、按键）
- **BatteryService**：电池状态管理
- **StorageManagerService**：存储管理
- **NetworkManagementService**：网络管理

WMS 是性能分析中的"老朋友"。在 Perfetto 中，当你分析 ANR 或者界面切换卡顿时，经常需要看 WMS 的状态——它决定了 Input 事件的分发和窗口的可见性。

#### 第三阶段：Other Services

最后启动的是其他服务，数量最多，重要性相对较低：

- **NotificationManagerService**
- **LocationManagerService**
- **AudioService**
- **VibratorService**
- 等等...

这三个阶段有严格的依赖关系。比如 WMS 依赖 AMS 来知道哪个 Activity 处于前台，InputManagerService 依赖 WMS 来决定把触摸事件分发给哪个窗口。

[待补充：SystemServer 各阶段启动时间在 Perfetto 中的表现]

### Launcher：最后的临门一脚

SystemServer 启动完成后，AMS 会发送 `ACTION_BOOT_COMPLETED` 广播（实际流程更复杂，先发送 `ACTION_LOCKED_BOOT_COMPLETED`，用户解锁后再发送 `ACTION_BOOT_COMPLETED`）。同时，SystemServer 启动 Launcher App，桌面显示出来，整个开机过程完成。

在 Perfetto 中，你可以追踪到这条完整的时间线：从 Kernel 启动，到 init 执行各阶段脚本，到 Zygote 预加载，到 SystemServer 启动各类服务，最后 Launcher 渲染出第一帧——这就是从按下电源键到看到桌面的完整旅程。

## 启动时间的度量

"你不能优化你无法度量的东西。"Android 提供了多种工具来度量启动时间。

### boot_completed 广播

`ACTION_BOOT_COMPLETED` 是最常用的开机完成标志。它表示系统已完成启动，用户已解锁设备。在代码中，AMS 负责在合适时机发送这个广播 [已验证: 官方文档 developer.android.com]。

但要注意两个细节：

1. 在 Android 24+（Nougat），先发送 `ACTION_LOCKED_BOOT_COMPLETED`（设备启动完成但处于锁屏状态），用户解锁后再发送 `ACTION_BOOT_COMPLETED`。
2. 现代 Android 版本对 `BOOT_COMPLETED` 广播做了限流——如果 App 从未被用户打开过，可能收不到这个广播。

### bootstat 工具

`bootstat` 是 AOSP 内置的启动时间记录工具，定义在 `system/core/bootstat/` 目录下 [已验证: AOSP system/core/bootstat/bootstat.cpp]。它记录了启动过程中各个关键节点的时间戳：

```bash
# 查看启动记录
adb shell bootstat -l
# 输出示例：
# firmware_loaded: 2.3s
# bootloader_complete: 3.1s
# kernel_loaded: 5.8s
# boot_complete: 18.2s
```

这些时间戳是相对于系统启动的 uptime（秒），可以直接看出哪个阶段最耗时。

### dmesg 与 logcat

在 Kernel 阶段，`dmesg` 可以看到内核启动的时间线：

```bash
adb shell dmesg | head -50
# 可以看到各驱动的加载时间
```

在用户空间阶段，`logcat` 过滤 `boot` 相关 tag：

```bash
adb logcat -b events | grep boot
```

### Perfetto / Systrace

最直观的方式是用 Perfetto 抓取开机 Trace：

```bash
# 抓取开机 Trace
adb shell perfetto \
  -c - --txt \
  -o /data/misc/perfetto-traces/trace.pb <<EOF
buffers: {
    size_kb: 63488
}
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_config {
            ftrace_events: "sched/sched_switch"
            ftrace_events: "power/cpu_frequency"
            ftrace_events: "sched/sched_wakeup"
            ftrace_events: "sched/sched_wakeup_new"
            atrace_categories: "am"
            atrace_categories: "sm"
            atrace_categories: "wm"
            atrace_categories: "view"
            atrace_categories: "dalvik"
            atrace_categories: "gfx"
        }
    }
}
duration_ms: 30000
EOF
```

在 Perfetto UI 中，你可以清晰地看到：
- **init 进程**的各阶段（early-init → init → boot）
- **Zygote 进程**的预加载区间
- **SystemServer 进程**的服务启动时间线
- **Launcher 进程**的首帧渲染时间

[待补充：一份真实的开机 Perfetto Trace 截图，标注各阶段]

## 开机性能优化的常见手段

理解了启动链路，我们来看看如何优化开机时间。优化的核心思路是：**减少串行等待，增加并行执行，推迟非必要工作。**

### 并行启动

init.rc 中，同一个 `on` 触发条件下的命令是串行执行的。但不同触发条件之间，init 可以通过 `trigger` 命令来控制并行度。现代 Android 设备上，init 已经做了大量并行化：

- 多个相同 `class` 的服务可以同时启动（通过 `class_start` 命令批量启动）
- 不相互依赖的服务放在不同的触发阶段，并行执行

### 延迟加载（Lazy Loading）

不是所有服务都需要在开机时立即可用。比如：
- NFC 服务：用户不用 NFC 的时候不需要启动
- 打印服务：很少用到的功能
- 一些 OEM 特定的服务

Android 提供了 `bind` 类型的服务——只有当 App 绑定时才启动。这是一种"按需启动"的策略，可以显著减少开机时间。

### cgroup 优先级调整

init.rc 中可以为服务设置 cgroup（Control Group），控制其 CPU 和 I/O 优先级。关键服务（如 SystemServer）应该获得更高的 CPU 份额和 I/O 优先级：

```rc
on boot
    # 为系统服务设置更高的 CPU 优先级
    write /dev/cpuset/system-background/cpus 0-3
    write /dev/cpuset/foreground/cpus 4-7
```

### Zygote 优化

Zygote 的预加载时间直接影响开机时间。优化手段包括：

1. **精简预加载类列表**：移除不常用的类。但这需要权衡——减少预加载意味着 App 启动时可能需要重新加载这些类。
2. **并行预加载**：Android 已经将一些预加载工作并行化。
3. **预加载缓存**：通过 `--enable-preload-dex2oat` 等选项，在系统更新后后台预先编译预加载类的 OAT 文件。

### 厂商优化黑科技

各手机厂商在开机优化上有自己的手段：

- **小米**：MIUI 的"光速启动"——通过在关机前保存系统状态，开机时快速恢复
- **华为**：EROFS 文件系统优化——通过改进文件系统布局，减少启动时的 I/O 时间
- **三星**：Galaxy App Booster——在首次开机后后台优化 App 的 dex2oat 编译

[待验证：各厂商具体优化方案的细节]

## 扩展：AB 分区与 dm-verity 的影响

### AB 分区与 Virtual A/B

现代 Android 设备使用 AB 分区方案来实现无缝 OTA 更新。设备上有两套系统分区（A 和 B），更新在后台分区进行，重启时切换到新分区。

这对启动的影响：
- **正面**：OTA 后不需要在 recovery 模式下花时间安装，重启即可
- **负面**：需要额外的存储空间（Virtual A/B 通过快照技术缓解了这个问题），启动时 Bootloader 需要确认从哪个分区启动

[待补充：AB 分区切换流程图]

### dm-verity 与 AVB

dm-verity（Device Mapper Verity）是 Android 用于验证系统分区完整性的机制。AVB（Android Verified Boot）是更高层的验证框架。

在启动链中：
1. Bootloader 验证 Kernel 和 initramfs 的完整性（AVB）
2. Kernel 启动后，通过 dm-verity 验证 system 分区的每个块

这对启动时间的直接影响：**每次读取系统分区的数据块时，都需要验证其 hash 值**。在开机阶段，大量文件被读取（dex2oat 编译、类加载等），dm-verity 会引入额外的 CPU 开销。

权衡点在于：
- **安全性更高** → 启动稍慢
- **可以关闭 dm-verity**（需要解锁 bootloader）→ 启动更快但失去安全保护

[适用版本: Android 7.0 (Nougat) 起 dm-verity 默认启用]

## 在 Perfetto 中识别启动各阶段

当你拿到一份开机阶段的 Perfetto Trace 时，以下是快速定位各阶段的指南：

| 阶段 | 在 Perfetto 中的表现 | 关键 Track |
|------|---------------------|-----------|
| Kernel 启动 | Trace 的最前面，通常有几个空白区域（Kernel 启动前无法 trace） | cpu track |
| init 进程 | init 进程的 CPU 活动，可以看到多个阶段性的执行区间 | init 进程 track |
| Zygote 预加载 | zygote64/zygote 进程的 CPU 使用高峰期，持续数秒 | zygote 进程 track |
| SystemServer 启动 | system_server 进程中出现密集的 CPU 活动 | system_server track |
| Launcher 首帧 | launcher 进程开始渲染，到第一帧提交完成 | launcher / SurfaceFlinger track |

[待补充：完整的开机 Trace 标注截图]

## 常见问题与误区

### 误区："init 进程是 Android 所有进程的鼻祖"

准确地说，init 是**用户空间所有进程**的鼻祖。真正的起点是 swapper（PID 0），它还创建了 kthreadd（PID 2）——内核线程的鼻祖。

### 误区："开机时间就是到桌面显示的时间"

Android 定义了多个"开机完成"节点：
- `boot_completed`：系统启动完成（可能还处于锁屏状态）
- `locked_boot_completed`：启动完成，但设备仍处于 Direct Boot 模式
- `user_setup_complete`：用户完成首次设置向导

不同场景关注不同的节点。对于性能优化，通常关注从开机到 `boot_completed` 的总时间。

### 误区："App 冷启动慢是因为 Zygote 预加载不够"

Zygote 预加载了 3000+ 个常用类，但**App 自己的类**不在预加载列表中。冷启动慢更可能的原因是：
- App 自身的 Application.onCreate() 做了太多初始化
- App 的 Dex 文件需要 dex2oat 编译（特别是首次启动）
- 主线程做了 I/O 或网络操作

## 参考资料

- AOSP 源码路径（精确到文件和关键函数）：
  - `system/core/init/init.cpp` — init 进程主流程
  - `system/core/init/init.rc` — 主 init.rc 配置文件
  - `frameworks/base/core/java/com/android/internal/os/ZygoteInit.java` — Zygote 启动和预加载
  - `frameworks/base/services/java/com/android/server/SystemServer.java` — SystemServer 服务启动
  - `system/core/bootstat/bootstat.cpp` — 启动时间记录
- 官方文档：
  - [Android Boot Time](https://source.android.com/docs/core/perf/boot-times)
  - [Android Architecture](https://source.android.com/docs/core/architecture)
  - [Verified Boot](https://source.android.com/docs/security/features/verifiedboot)
- 其他高质量参考：
  - [Android 启动系列之我是 init 进程 - 掘金](https://juejin.cn/post/7287913415804370955)
