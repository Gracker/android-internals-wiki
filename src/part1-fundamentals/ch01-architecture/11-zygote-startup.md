---
title: Zygote 机制与启动性能优化
chapter: '1.11'
section: '1.11'
status: finalized
applicable_versions: Android 5.0 (API 21) - Android 17 (API 37)
last_verified: '2026-07-25'
last_verified_against: AOSP android-17.0.0_r1 + ACK android17-6.18-2026-06_r6 + Android Developers
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/ZygoteInit.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/Zygote.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/ZygoteServer.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/ZygoteConnection.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/ZygoteArguments.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/ZygoteConfig.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/RuntimeInit.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/ZygoteProcess.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/AppZygote.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/webkit/WebViewZygote.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ZygotePreload.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessList.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/EventLogTags.logtags @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityMetricsLogger.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/java/com/android/server/SystemServer.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/jni/com_android_internal_os_Zygote.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/jni/com_android_internal_os_ZygoteInit.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/cmds/app_process/app_main.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/config/preloaded-classes @ android-17.0.0_r1"
  - type: aosp
    path: "system/core/rootdir/init.zygote64.rc @ android-17.0.0_r1"
  - type: aosp
    path: "system/core/rootdir/init.zygote64_32.rc @ android-17.0.0_r1"
  - type: kernel
    path: "kernel/common/kernel/fork.c @ android17-6.18-2026-06_r6"
  - type: kernel
    path: "kernel/common/mm/memory.c @ android17-6.18-2026-06_r6"
  - type: official
    path: "https://source.android.com/docs/core/runtime/zygote"
  - type: official
    path: "https://developer.android.com/reference/android/app/ZygotePreload"
  - type: official
    path: "https://developer.android.com/guide/topics/manifest/application-element#zygotePreloadName"
  - type: official
    path: "https://developer.android.com/guide/topics/manifest/service-element#useAppZygote"
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
tags:
  - zygote
  - fork
  - preload
  - copy-on-write
  - usap
  - app-zygote
  - webview-zygote
related_chapters:
  - '1.2'
  - '1.3'
  - '1.5'
  - '1.10'
  - '8.2'
  - '8.3'
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
pipeline_stage: ready-to-publish
---

# 1.11 Zygote 机制与启动性能优化

Zygote 是长期存活的应用进程父进程，它提前完成每个 Android 应用都会用到的一部分运行时初始化。启动应用时，系统不必从空进程重新装载 ART 和常用框架状态，而是从 Zygote 派生（fork）子进程，或把未特化应用进程池（USAP 池）中的预备进程转换成目标应用进程。

这套机制同时解决启动和内存问题：

- 预加载结果可被子进程继承；
- fork 后的私有可写内存页暂时共享，父进程或子进程首次写入时再触发写时复制（Copy-on-Write，COW）；
- `system_server` 可以通过受控协议为子进程设置 UID、GID、SELinux 安全域、挂载命名空间、资源上限和系统调用过滤规则。

分析冷启动时，Zygote 只负责“请求进程、创建或特化进程、进入应用入口”这一段。后面的 `bindApplication`（系统向新进程发送应用绑定信息）、Provider 初始化、`Application.onCreate()` 和首帧都属于应用初始化。若把整段冷启动都归因于 Zygote，就会找错优化位置。

平台基线为 AOSP `android-17.0.0_r1`；涉及 `fork` 与 COW 时，内核基线为 Android 通用内核（ACK）`android17-6.18-2026-06_r6`。Android 5～16 仅用于解释版本演进。

---

## 从启动请求到 Zygote

桌面启动器（Launcher）发起 Activity 启动时，请求先通过 Binder 进入 `system_server`。Activity Task Manager Service（ATMS）和 Activity Manager Service（AMS）解析 Activity、Task 与进程状态；只有目标进程不存在时，`ProcessList` 才请求创建进程。

普通应用进程的控制流可以简化为：

```text
Launcher / App
  → Binder
system_server: ATMS / AMS / ProcessList
  → Process.start()
  → ZygoteProcess.startViaZygote()
  → LocalSocket
primary 或 secondary Zygote
  → forkAndSpecialize() 或 USAP specialize
  → 返回 PID
```

`system_server` 与 Zygote 之间不使用 Binder 服务调用。`ZygoteProcess.openZygoteSocketIfNeeded(abi)` 先根据目标应用二进制接口（ABI，用于匹配处理器架构）选择主（primary）或次（secondary）Zygote 的套接字，再把参数写入 `LocalSocket`。请求中包含 UID、GID、附加用户组（supplementary groups）、目标 SDK 版本、ABI、SELinux `seInfo`、进程名和挂载选项等。

`ProcessList.startProcess()` 还会先看进程类型：

- WebView 相关进程可以走 `WebViewZygote`；
- 声明使用 App Zygote 的隔离服务（isolated service，以独立 UID 运行的服务）可以走 `AppZygote`；
- 其余应用走普通的主/次 Zygote。

因此，调用 `Process.start()` 不代表所有进程都会连接同一个 Zygote 套接字。

---

## Zygote 在开机时预加载什么

Android 17 的 `ZygoteInit.main()` 先解析启动参数，并根据 `--enable-lazy-preload` 决定立即预加载还是延后执行 `preload()`；随后创建 `ZygoteServer`，再按参数 fork `system_server`。常见的 64 位主 Zygote 由 `init.zygote64.rc` 启动，它带有 `--start-system-server`，但没有延迟预加载参数，因此会先预加载，再 fork `system_server`。

`ZygoteInit.preload()` 的当前顺序是：

```text
beginPreload
  → preloadClasses
  → cacheNonBootClasspathClassLoaders
  → Resources.preloadResources
  → nativePreloadAppProcessHALs
  → maybePreloadGraphicsDriver
  → preloadSharedLibraries
  → preloadTextResources
  → preloadCompatConfig
  → HttpEngine.preload              [feature flag]
  → WebViewFactory.prepareWebViewInZygote
  → endPreload
  → warmUpJcaProviders
```

`HttpEngine.preload()` 受功能开关（flag）控制，并用 `NoSuchMethodError` 兼容 Zygote 与模块版本不一致的情况。它并非所有 Android 17 产品都会执行的固定阶段。

### `preloaded-classes` 的边界

`preloadClasses()` 读取 `/system/etc/preloaded-classes`。AOSP 对应的源文件是 `frameworks/base/config/preloaded-classes`，主要包含启动类路径（boot class path）和 Android 框架中适合跨进程共享的类。AndroidX、业务代码和普通第三方 SDK 不会因为“常用”就自动进入主 Zygote。

预加载并非越多越好：

- 类加载会增加开机时间；
- 预加载对象若在子进程中很快被写，会触发 COW，降低共享收益；
- 很少使用的类会增加 Zygote 常驻内存；
- 预加载后若遗留不适合由子进程继承的文件描述符或线程，会给 fork 后的进程带来错误状态。

应根据启动样本和内存样本选择条目，不能只按类加载次数扩充列表。

### HAL 与图形驱动预加载

`nativePreloadAppProcessHALs()` 在 Android 17 的 JNI 实现中只调用：

```cpp
android::GraphicBufferMapper::preloadHal();
```

源码注释给出的约束是：适合放在这里的硬件抽象层（HAL）实现，应当始终采用直通模式，也就是在应用进程内直接调用，并且会被大多数应用进程使用。因此，不能把这个入口理解成“Zygote 预加载所有 HAL”。

`nativePreloadGraphicsDriver()` 调用 `zygote_preload_graphics()`。`ZygoteInit` 的注释说明，它通过一次 OpenGL 或 Vulkan 调用加载并初始化图形驱动；属性 `ro.zygote.disable_gl_preload=true` 可以关闭该动作。

这里预热的是可继承的驱动装载状态，不包含每个应用自己的图形运行环境。应用的 RenderThread、EGL/Vulkan 图形上下文（context）、Surface 和首帧命令仍在子进程中创建。应用选择的可更新 GPU 驱动（updatable GPU driver）也不一定与 Zygote 预加载的系统驱动相同。

### 32 位次 Zygote 的延迟预加载

在 64/32 双 ABI 的 AOSP 配置中：

- `init.zygote64.rc` 启动 64 位主 Zygote，并立即预加载（eager preload）；
- `init.zygote64_32.rc` 启动 32 位次 Zygote，并带有 `--enable-lazy-preload`，采用延迟预加载（lazy preload）。

Android 17 的 `SystemServer` 提交 `SecondaryZygotePreload` 任务，调用：

```java
Process.ZYGOTE_PROCESS.preloadDefault(Build.SUPPORTED_32_BIT_ABIS[0]);
```

该任务约在 WebView 准备任务开始前一秒启动，后者会等待它完成。`preloadDefault()` 通过 Zygote 套接字发送 `--preload-default`。返回 `true` 表示本次触发了延迟预加载；返回 `false` 表示此前已经完成，或该 Zygote 没有采用延迟预加载模式。

这是特定 `init` 配置下的行为。只支持 64 位、只支持 32 位以及使用厂商自定义 Zygote 配置的设备可能不同。分析设备时，要同时检查 `ro.zygote`、实际的 `init` 服务配置和对应进程。

---

## 普通 fork 路径

普通路径进入 `Zygote.forkAndSpecialize()`：

```java
ZygoteHooks.preFork();
int pid = nativeForkAndSpecialize(...);
if (pid == 0) {
    Trace.traceBegin(TRACE_TAG_ACTIVITY_MANAGER, "PostFork");
    // child-only Java setup
}
ZygoteHooks.postForkCommon();
```

`preFork()` 会让 ART 和运行时完成 fork 前的必要准备，避免子进程继承不合适的运行时状态。JNI（Java 与原生代码的调用桥梁）层的 `nativeForkAndSpecialize()` 调用 `ForkCommon()`；子进程随后进入 `SpecializeCommon()`。

“特化”是把通用子进程转换成具有目标应用身份和安全限制的进程，远不止修改 UID。Android 17 的原生实现包含：

- 关闭或替换不应继承的文件描述符；
- 建立应用的挂载命名空间（mount namespace），形成该应用可见的文件系统视图；
- 设置附加用户组与资源上限（rlimit）；
- 切换 GID、UID；
- 安装 seccomp 系统调用过滤器；
- 设置调度策略；
- 收缩 Linux capabilities（按权限拆分的内核特权）；
- 执行 SELinux 安全域切换（domain transition）；
- 设置进程名、调试与内存安全选项；
- 运行 ART 在 fork 后为子进程准备的回调（post-fork child hooks）。

这些步骤负责建立应用的安全隔离，也会计入进程创建时间。某次启动在 `PostFork` 区段内显著变慢时，应检查挂载操作、文件描述符、SELinux、调度和运行时回调，不能只看 `fork()` 系统调用本身。

### 内核中的 fork 与 COW

在 ACK `android17-6.18-2026-06_r6` 中，`copy_process()` 通过 `copy_mm()` 复制地址空间描述，`dup_mmap()` 复制虚拟内存区域（VMA）和必要的页表。私有可写页起初可以继续引用同一物理页；子进程或父进程首次写入时，会触发写保护缺页异常（write-protect fault）并进入 `do_wp_page()`，需要时再由 `wp_page_copy()` 创建独占副本。

写时复制的边界如下：

- fork 时不会把 Zygote 全部内存复制一遍；
- 共享文件映射和只读页可以继续共享；
- 私有可写页在被修改后逐步私有化；
- 预加载后对象越容易被子进程修改，共享收益越低。

已退出的普通应用进程不会成为后续应用的父进程。`lmkd` 终止缓存应用，不会让下一次 fork 脱离 Zygote，也不会因为“缓存子进程少了”直接降低 Zygote 的 COW 复用率。内存压力可以通过回收文件页、交换空间（swap）、调度与 I/O 间接影响启动，但这属于另一条因果路径。

### 16KB 内存页不会只带来收益

对于相同的虚拟内存范围，16KB 页通常需要更少的页表项；但 VMA 数量由内存映射布局决定，不会因为页大小从 4KB 变为 16KB 就自动减少 75%。

更大的页可能减少部分页表和缺页管理开销，也会改变 COW 的复制单位：即使只修改页内少量数据，也要私有化整个更大的页面。对 Zygote 子进程而言，启动时间、按共享比例分摊的内存（PSS）和驻留物理内存（RSS）的净变化，取决于内存访问是否集中、脏页比例、文件映射和设备内存配置，不能只根据页大小推导固定收益。

---

## USAP：先 fork，后特化

USAP 是未特化应用进程（Unspecialized App Process）。启用后，主/次 Zygote 可以预先维护一小组尚未绑定具体应用身份的进程。满足条件的启动请求直接发送到 USAP 套接字，由池中的进程调用 `specializeAppProcess()` 完成 UID、GID、SELinux 等特化，无需再为这次请求 fork 新进程。

普通路径和 USAP 路径的区别是：

| 路径 | 本次请求是否执行新的 fork | Java 入口 | 共同结果 |
|---|---|---|---|
| 普通 Zygote | 是 | `forkAndSpecialize()` | 子进程完成特化并进入应用入口 |
| USAP 命中 | 否，使用池中现有进程 | `specializeAppProcess()` | 现有进程完成特化并进入应用入口 |

两条路径都会在目标进程中开始名为 `PostFork` 的 Trace 区段。看到该区段只能证明 fork 后或特化后的准备阶段已经开始，不能证明这次启动刚执行了 `fork()`。

### USAP 默认关闭

Android 17 的 `ZygoteConfig.USAP_POOL_ENABLED_DEFAULT` 是 `false`。配置读取顺序是：

1. `persist.device_config.runtime_native.usap_pool_enabled`；
2. `dalvik.vm.usap_pool_enabled`；
3. 源码默认值。

即使池已经启用，也只有标记为延迟敏感（latency-sensitive）且不属于系统进程的请求符合基础策略。`--start-child-zygote`、`--invoke-with` 和各种预加载命令等参数会让请求改走传统 Zygote；USAP 套接字通信失败时，`ZygoteProcess` 也会改走传统路径。

设备上可先读取这两个属性：

```bash
adb shell getprop persist.device_config.runtime_native.usap_pool_enabled
adb shell getprop dalvik.vm.usap_pool_enabled
```

属性为空不代表 USAP 最终一定启用，应按上述优先级和默认值解释，并结合启动轨迹判断请求是否使用了池中进程。

### 子 Zygote 为什么没有 USAP

`ZygoteServer(boolean isPrimaryZygote)` 用于系统的主/次 Zygote，并设置 `mUsapPoolSupported = true`。无参 `ZygoteServer()` 用于子 Zygote（child zygote，即专门派生某类进程的次级父进程），明确设置 `mUsapPoolSupported = false`。

App Zygote 和 WebView Zygote 不从主 Zygote 的 USAP 池获取进程，也不维护自己的 USAP 池。两者通过各自的子 Zygote 套接字接收后续 fork 请求。

---

## 从特化完成到 `Application.onCreate()`

普通应用的入口类参数 `processClass` 是 `android.app.ActivityThread`。子进程完成特化后，调用顺序如下：

```text
ZygoteConnection.handleChildProc()
  → 结束 PostFork trace
  → ZygoteInit.zygoteInit()
      → RuntimeInit.commonInit()
      → nativeZygoteInit()
      → RuntimeInit.applicationInit()
      → findStaticMain("android.app.ActivityThread")
  → ActivityThread.main()
      → Looper.prepareMainLooper()
      → ActivityThread.attach()
      → IActivityManager.attachApplication()
```

`nativeZygoteInit()` 最终进入 `AppRuntime.onZygoteInit()`，为普通应用启动 Binder 线程池。子 Zygote 使用 `childZygoteInit()`，跳过这套普通应用初始化，再进入自己的 Zygote 服务端循环，等待派生后续进程。

新进程通过 `attachApplication()` 回到 `system_server` 后，AMS 才发送 `bindApplication`。接下来才会执行：

- 创建 Application 并调用其 `attach()`；
- 安装当前进程的 ContentProvider；
- 调用 `Application.onCreate()`；
- 启动目标 Activity；
- 创建窗口并绘制首帧。

这给出了清晰的责任边界：

| 区间 | 优先怀疑 |
|---|---|
| `system_server` 发出请求到 PID 返回 | Zygote 套接字、USAP/fork、父进程调度 |
| `PostFork` | 原生特化、挂载操作、SELinux、运行时 fork 后回调 |
| `ActivityThreadMain` 到 `attachApplication` | 子进程调度、运行时入口、Binder 初始化 |
| `bindApplication` | APK/类加载、Application、Provider、配置 |
| 应用绑定完成到首帧 | Activity、View、资源、RenderThread、Surface |

---

## 四类 Zygote 不要混在一起

| 类型 | 谁启动 | 服务对象 | 预加载特点 | USAP |
|---|---|---|---|---|
| 主 Zygote（Primary Zygote） | `init` | 主 ABI、`system_server`、普通应用 | 通常立即预加载 | 产品配置可启用 |
| 次 Zygote（Secondary Zygote） | `init` | 次 ABI 的普通应用 | 64/32 位配置中通常延迟预加载 | 产品配置可启用 |
| WebView Zygote | `WebViewZygote` 经主 Zygote 创建 | WebView 及其渲染器进程 | 预加载当前 WebView 实现 | 不支持 |
| App Zygote | `AppZygote` 经主 Zygote 创建 | 声明 `useAppZygote` 的隔离服务 | 调用应用的 `ZygotePreload` 实现 | 不支持 |

### App Zygote 与 `ZygotePreload`

`android.app.ZygotePreload` 从 API 29 开始提供。应用在 `<application>` 上用 `android:zygotePreloadName` 指定实现类，并在隔离服务上设置 `android:useAppZygote="true"`。

预加载的数据会被该 App Zygote 后续 fork 的隔离服务进程继承。实现时必须遵守与主 Zygote 类似的约束：

- 不创建 fork 后状态会失效的线程；
- 不保留不该继承的连接和文件描述符；
- 优先加载只读、可共享且会被多个隔离服务使用的数据；
- 不把用户或单次请求状态放入父进程。

它不是普通 Activity 进程的通用预加载 API。

### WebView Zygote

`WebViewZygote` 通过 `startChildZygote()` 创建 `webview_zygote`，等待套接字可用，再用 `preloadApp()` 预加载当前 WebView 实现的应用信息。切换 WebView 实现后，旧 Zygote 需要停止或重建，不能把一次预热当作永久状态。

---

## Perfetto 中怎样拆分启动时间

建议同时采集：

- atrace 的 `am` 与 `dalvik`；
- `sched` 的线程切换与唤醒事件；
- Binder 事务；
- 进程创建和退出等生命周期事件；
- Android EventLog 的 `events` 缓冲区；
- 需要分析内核 fork 时，再加入系统调用（syscall）和内存事件。

Android 17 可使用的源码锚点包括：

- Zygote 进程：`ZygotePreload`、`PreloadClasses`、`CacheNonBootClasspathClassLoaders`、`PreloadResources`、`PreloadAppProcessHALs`、`PreloadGraphicsDriver`；
- 目标应用：`PostFork`、`ZygoteInit`、`ActivityThreadMain`、`bindApplication`；
- `system_server`：异步 Trace 区段 `launching: <package>`；
- EventLog：`am_proc_start`、`am_proc_bound`。

只有在性能轨迹启用了 Android 日志并包含 `events` 缓冲区时，才能查询 EventLog。没有查到这些记录，不能证明进程没有启动。

### 诊断顺序

1. 用 `launching: <package>` 定位一次 Activity 启动；
2. 确认目标 PID 是否为新进程；
3. 查设备是否启用 USAP，不要仅凭 `PostFork` 判断；
4. 比较 `system_server` 发出进程请求、目标进程首次获得调度、`PostFork`、`ActivityThreadMain`、`am_proc_bound` 和 `bindApplication` 的时间；
5. 对最长区间展开线程状态、Binder、I/O 和锁等待；
6. 把 `bindApplication` 之后的问题交给应用初始化和首帧分析。

几个常见结论：

- Zygote 侧等待很久、目标进程尚未运行：检查套接字排队、USAP 池补充进程（pool refill）、父 Zygote 调度和系统负载；
- `PostFork` 长：检查原生特化步骤；
- `PostFork` 已结束，但 `ActivityThreadMain` 或 `attach()` 很晚：检查新进程是否长时间处于可运行（runnable）状态却没有获得 CPU，或运行时入口是否阻塞；
- `bindApplication` 长：优先检查内容提供者、Application、类加载和资源；
- 目标进程早已存在：本次属于温启动或热启动（warm/hot start），Zygote 不在关键路径上。

不能用固定的“fork 应小于 N 毫秒”作为跨设备阈值。ABI、内存页大小、SELinux、挂载操作、调度、内存压力和厂商实现都会改变耗时分布，应与同一设备、同一构建、同一启动类型的基线比较。

---

## 版本演进

| 版本 | 已确认变化 | 分析意义 |
|---|---|---|
| Android 8 | AOSP 出现 `WebViewZygote` | WebView 相关进程有独立预加载父进程 |
| Android 9 | `PreloadAppProcessHALs` 出现在 Zygote 预加载流程 | 图形缓冲区映射器（gralloc mapper）HAL 开始在主 Zygote 阶段预热 |
| Android 10 | `PreloadGraphicsDriver` 替代旧 `preloadOpenGL`；AOSP 出现 USAP、App Zygote 与 `ZygotePreload` | 普通 fork、USAP、WebView/App 子 Zygote 需要分开判断 |
| Android 17 | 当前固定基线；保留可选的 `HttpEngine.preload()`、次 Zygote 延迟预加载和当前 USAP 策略 | 以产品功能开关、ABI、`init` 配置和实际轨迹判断生效路径 |

历史版本只用于说明机制何时出现。判断当前平台行为时，以 `android-17.0.0_r1` 为准；判断内核 COW 行为时，以 `android17-6.18-2026-06_r6` 为准。

---

## 常见误区

### “`system_server` 通过 Binder 调用 Zygote”

创建进程的命令通过 Zygote `LocalSocket` 传递。Binder 用在启动请求进入 `system_server`，以及子进程通过 `attachApplication()` 连接回 `system_server` 等位置。

### “看到 `PostFork` 就证明刚执行了 fork”

普通 fork 和 USAP 特化都会开始 `PostFork` Trace 区段，还要结合 USAP 配置、PID 和父进程事件判断实际路径。

### “预加载越多，应用一定越快”

预加载会增加开机时间和常驻内存；容易被子进程写入并形成脏页的对象还会削弱 COW 收益。只读、普遍使用且可安全继承的数据才适合预加载。

### “图形驱动预加载已经创建应用的 GPU 图形上下文”

它只预热驱动装载状态。应用自己的 RenderThread、图形上下文、Surface 与首帧仍在子进程中创建。

### “lmkd 杀缓存应用会破坏 Zygote 的父子复用”

普通应用始终从 Zygote 或 USAP 派生，不会从其他缓存应用 fork。`lmkd` 清理子进程不会改变这个父进程关系。

### “16KB 页让 fork 固定快 75%”

页表项、COW 粒度、缺页和内存浪费会同时变化；VMA 数量也不会按页大小等比缩减。必须实测。

---

## 源码阅读顺序

普通冷启动涉及以下源码路径：

1. `ProcessList.startProcess()`：选择普通、WebView 还是 App Zygote；
2. `ZygoteProcess.startViaZygote()`：组装参数、选择对应 ABI 的套接字、判断是否使用 USAP；
3. `ZygoteServer.runSelectLoop()` / `ZygoteConnection.processCommand()`：Zygote 端接收命令；
4. `Zygote.forkAndSpecialize()` 与 `com_android_internal_os_Zygote.cpp`：fork 并为进程设置安全身份；
5. `ZygoteConnection.handleChildProc()`：结束 `PostFork` 并选择普通应用或子 Zygote 入口；
6. `ZygoteInit.zygoteInit()` / `RuntimeInit.applicationInit()`：进入 `ActivityThread.main()`；
7. `ActivityThread.attach()` 与 AMS 的绑定处理：从新进程回到 `bindApplication`。

冷启动轨迹中的每段时间都能对应到具体进程和职责：创建慢就检查 Zygote，特化慢就检查原生安全准备，绑定慢就检查应用初始化，首帧慢就检查组件与渲染。Zygote 优化应限定在它负责的范围内。
