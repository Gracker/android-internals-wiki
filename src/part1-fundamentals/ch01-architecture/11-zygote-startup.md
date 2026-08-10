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
drafted_date: '2026-04-05'
drafted_by: openclaw-task2a
reviewed_by: openclaw-task6
reviewed_date: '2026-07-14'
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed
pipeline_stage: ready-to-publish
deepseek_cn_review_state: needs-structure-rework
last_task9_review_log: logs/deep-review/2026-07-14-17-deep-review.md
last_task9_at: "2026-07-14T17:26:54+08:00"
last_task9_review_notes: "2026-07-14 Task9 deep-review: needs-rework。P0 0 / P1 2。需要修复 USAP 与 Child Zygote 关系描述、16KB 页边界影响数据等问题后重新复审。Round 2: P0=0 / P1=2 (applicable_versions vs last_verified_against 不一致 + frontmatter task9_state 重复字段冲突). P2 1 (USAP 边界前提). queue.json 新增 P95 条目."
finalized_by: "openclaw-task9-auto-promote"
task6_reviewed_date: "2026-07-14"
last_task6_review_log: "logs/review/2026-07-14-21-review.md"
task6_review_notes: "07-14 21 Task6 re-review (post-Task2B fix): pass-light-edit。L2 小修 3 处（移除「你」→无主语改写，符合 writing-guide）；outline 6/6 覆盖；L1 禁用词扫描全清。Task9 needs-rework P1:2 已由 Task2B 修复（源码行号+版本声明），待 Task9 复审。"
last_task9_audit: "2026-05-26"
last_task9_audit_at: "2026-05-26T14:20:00+08:00"
last_task9_audit_log: "logs/deep-review/2026-05-26-14-audit.md"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-07-14
repaired_date: "2026-04-24"
repaired_by: "openclaw-task2b"
last_task2b_at: 2026-07-14T20:51:00+08:00
last_last_task6_audit: "2026-07-17"
last_task6_at: "2026-07-14T21:09:00+08:00"
reviewed_at: "2026-05-18T03:31:27+08:00"
task9_review_log: logs/deep-review/2026-07-14-21-deep-review.md
task9_review_notes: "2026-07-14 Task9 round-3 复审（post-Task2B fix）: pass-tech-review。P0=0 / P1=0。复核 16KB 页边界声明、USAP 与 Child Zygote 源码级隔离证据、last_verified_against 锚定 android-17.0.0_r1 等修复全部到位。P2 3 处已写入 suggestions.md（USAP 量化数据、内核 tag 标注、cppath 微调），P3 3 处仅日志记录。满足自动晋升条件 → ✅ finalized。"
finalized_date: "2026-07-14"
last_deepseek_cn_review_at: 2026-07-15
---

# 1.11 Zygote 机制与启动性能优化

Zygote 把每个 Android 应用都需要的一部分运行时初始化前移到一个长期存活的父进程中。启动应用时，系统不必从空进程重新装载 ART 和常用 framework 状态，而是从 Zygote fork，或把 USAP 池中的未特化进程变成目标应用进程。

这套机制同时解决启动和内存问题：

- 预加载结果可被子进程继承；
- fork 后的私有可写页面先共享，首次写入时再触发 Copy-on-Write；
- `system_server` 可以通过受控协议为子进程设置 UID、GID、SELinux domain、mount namespace、rlimit 和 seccomp。

分析冷启动时，Zygote 只覆盖“进程请求、创建或特化、进入应用入口”这一段。`bindApplication`、Provider 初始化、`Application.onCreate()` 和首帧仍属于后续应用初始化。把整段冷启动都归因于 Zygote，会看错优化位置。

平台基线为 AOSP `android-17.0.0_r1`；涉及 `fork` 与 COW 时，内核基线为 ACK `android17-6.18-2026-06_r6`。Android 5～16 仅用于版本演进。

---

## 从启动请求到 Zygote

Launcher 发起活动启动时，前半段通过 Binder 进入 `system_server`。ATMS/AMS 解析活动、Task 和进程状态；只有目标进程不存在时，`ProcessList` 才请求创建进程。

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

`system_server` 与 Zygote 之间不使用 Binder 服务调用。`ZygoteProcess.openZygoteSocketIfNeeded(abi)` 先按目标 ABI 选择主或 secondary socket，再把参数写入 `LocalSocket`。请求中包含 UID、GID、supplementary groups、target SDK、ABI、SELinux `seInfo`、进程名和挂载选项等。

`ProcessList.startProcess()` 还会先看进程类型：

- WebView 相关进程可以走 `WebViewZygote`；
- 声明使用 App Zygote 的 isolated service 可以走 `AppZygote`；
- 其余应用走普通的主/次 Zygote。

调用 `Process.start()` 不代表所有进程都进入同一个 Zygote socket。

---

## Zygote 在开机时预加载什么

Android 17 的 `ZygoteInit.main()` 先解析启动参数，并根据 `--enable-lazy-preload` 决定是否立即执行 `preload()`；随后创建 `ZygoteServer`，再按参数派生 `system_server`。常见的 64 位主 Zygote 由 `init.zygote64.rc` 启动，带 `--start-system-server`，没有 lazy 参数，所以先预加载，再派生 `system_server`。

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

`HttpEngine.preload()` 受 flag 控制，并用 `NoSuchMethodError` 兼容 Zygote 与模块版本不一致的情况。它不是所有 Android 17 产品都会执行的固定阶段。

### `preloaded-classes` 的边界

`preloadClasses()` 读取 `/system/etc/preloaded-classes`。AOSP 对应源文件是 `frameworks/base/config/preloaded-classes`，主要覆盖 boot class path / framework 中适合跨进程共享的类。AndroidX、业务代码和普通第三方 SDK 不会因为“常用”就自动进入主 Zygote。

预加载并非越多越好：

- 类加载会增加开机时间；
- 预加载对象若在子进程中很快被写，会触发 COW，降低共享收益；
- 很少使用的类会增加 Zygote 常驻内存；
- preload 后遗留不安全文件描述符或线程，会破坏 fork 边界。

应根据启动样本和内存样本选择条目，不能只按类加载次数扩充列表。

### HAL 与图形驱动预加载

`nativePreloadAppProcessHALs()` 在 Android 17 的 JNI 实现中只调用：

```cpp
android::GraphicBufferMapper::preloadHal();
```

源码注释给出的约束是：适合放在这里的 HAL 应当始终采用直通模式，并被大多数应用进程使用。因此，不能把这个入口理解成“Zygote 预加载所有 HAL”。

`nativePreloadGraphicsDriver()` 调用 `zygote_preload_graphics()`。`ZygoteInit` 的注释说明，它通过一次 OpenGL 或 Vulkan 调用加载并初始化图形驱动；属性 `ro.zygote.disable_gl_preload=true` 可以关闭该动作。

这里预热的是可继承的驱动装载状态，不是每个应用自己的图形运行环境。应用的 RenderThread、EGL/Vulkan context、Surface 和首帧命令仍在子进程中创建。也不能假定每个应用选择的可更新 GPU 驱动都等于 Zygote 预加载的系统驱动。

### 32 位次 Zygote 的 lazy preload

在 64/32 双 ABI 的 AOSP 配置中：

- `init.zygote64.rc` 启动 64 位主 Zygote，eager preload；
- `init.zygote64_32.rc` 启动 32 位次 Zygote，并带 `--enable-lazy-preload`。

Android 17 的 `SystemServer` 提交 `SecondaryZygotePreload` 任务，调用：

```java
Process.ZYGOTE_PROCESS.preloadDefault(Build.SUPPORTED_32_BIT_ABIS[0]);
```

任务约在 WebView 准备前一秒启动；WebView 准备会等待这个 future。`preloadDefault()` 通过 Zygote 套接字发送 `--preload-default`。返回 `true` 表示本次触发了 lazy preload，`false` 表示此前已经完成或 Zygote 并非延迟模式。

这是特定 init 配置下的行为。纯 64-only、纯 32 位和厂商自定义 Zygote 配置可能不同，分析设备时要同时看 `ro.zygote`、实际 init 服务和对应进程。

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

`preFork()` 要让 ART 和运行时进入适合 fork 的状态。JNI 的 `nativeForkAndSpecialize()` 调用 `ForkCommon()`；子进程再进入 `SpecializeCommon()`。

特化包含的步骤远多于修改 UID。Android 17 的原生实现包含：

- 关闭或替换不应继承的文件描述符；
- 建立应用 mount namespace 和存储视图；
- 设置附加组与资源限制；
- 切换 GID、UID；
- 安装 seccomp filter；
- 设置调度策略；
- 收缩进程能力；
- 执行 SELinux domain transition；
- 设置进程名、调试与内存安全选项；
- 运行 ART 的 post-fork child hooks。

这些步骤既是安全边界，也是进程创建时间的一部分。某次启动在 `PostFork` 内显著变慢时，应检查挂载、文件描述符、SELinux、调度和运行时钩子，不能只看 `fork()` 系统调用本身。

### 内核中的 fork 与 COW

ACK `android17-6.18-2026-06_r6` 中，`copy_process()` 通过 `copy_mm()` 复制地址空间描述，`dup_mmap()` 复制 VMA 和必要页表。私有可写页起初可以继续引用相同物理页；子进程或父进程首次写入时，write-protect fault 进入 `do_wp_page()`，需要时由 `wp_page_copy()` 创建独占副本。

写时复制的边界如下：

- fork 时不会把 Zygote 全部内存复制一遍；
- 共享文件映射和只读页可以继续共享；
- 私有可写页在被修改后逐步私有化；
- 预加载后对象越容易被子进程修改，共享收益越低。

已退出的普通应用进程不是后续应用的父进程。`lmkd` 杀掉缓存应用，不会让下一次 fork 脱离 Zygote，也不会因为“缓存子进程少了”直接降低 Zygote 写时复制复用率。内存压力可以通过回收文件页、swap、调度与 I/O 间接影响启动，但那是另一条因果路径。

### 16KB 页大小不是单向收益

相同虚拟内存范围在 16KB 页上通常需要更少的页表项，但 VMA 数量由映射布局决定，不会因为页从 4KB 变为 16KB 就自动减少 75%。

更大的页可能减少部分页表和缺页管理开销，也会改变 COW 粒度：只修改页内少量数据时，私有化的单位更大。对 Zygote 子进程而言，启动时间和 PSS/RSS 的净变化取决于访问局部性、脏页比例、文件映射和设备内存配置，不能只用页大小推导固定收益。

---

## USAP：预先派生，按需特化

USAP 是未特化应用进程（Unspecialized App Process）。启用后，primary/secondary Zygote 可以预先维护一小组尚未绑定具体应用身份的进程。满足条件的启动请求直接发到 USAP socket，现有进程调用 `specializeAppProcess()` 完成 UID、GID、SELinux 等特化，不再为这次请求派生新进程。

普通路径和 USAP 路径的区别是：

| 路径 | 本次请求是否派生新进程 | Java 入口 | 共同结果 |
|---|---|---|---|
| 普通 Zygote | 是 | `forkAndSpecialize()` | 子进程完成特化并进入应用入口 |
| USAP 命中 | 否，使用池中现有进程 | `specializeAppProcess()` | 现有进程完成特化并进入应用入口 |

两条路径都会在目标进程中开始 `PostFork` trace。看到 `PostFork` 只能证明 post-fork/post-specialize 阶段已经开始，不能证明这次启动刚执行了 `fork()`。

### USAP 默认关闭

Android 17 的 `ZygoteConfig.USAP_POOL_ENABLED_DEFAULT` 是 `false`。配置读取顺序是：

1. `persist.device_config.runtime_native.usap_pool_enabled`；
2. `dalvik.vm.usap_pool_enabled`；
3. 源码默认值。

即使池已启用，也只有 latency-sensitive 且非 system process 的请求符合基础策略。`--start-child-zygote`、`--invoke-with`、各种 preload 命令等参数会让请求回退到传统 Zygote；USAP 套接字通信失败时，`ZygoteProcess` 也会回退。

设备上可先读取这两个属性：

```bash
adb shell getprop persist.device_config.runtime_native.usap_pool_enabled
adb shell getprop dalvik.vm.usap_pool_enabled
```

空值不表示最终一定启用，应按上述优先级和默认值解释，并结合启动跟踪判断是否命中。

### 子 Zygote 为什么没有 USAP

`ZygoteServer(boolean isPrimaryZygote)` 用于系统主/次 Zygote，设置 `mUsapPoolSupported = true`。无参 `ZygoteServer()` 用于子 Zygote，明确设置 `mUsapPoolSupported = false`。

App Zygote 和 WebView Zygote 不从主 Zygote 的 USAP 池取进程，也不维护自己的 USAP 池。两者通过各自的子 Zygote 套接字接收后续 fork 请求。

---

## 从特化完成到 `Application.onCreate()`

普通应用的 `processClass` 是 `android.app.ActivityThread`。子进程完成特化后，调用顺序是：

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

`nativeZygoteInit()` 最终进入 `AppRuntime.onZygoteInit()`，为普通应用启动 Binder thread pool。child zygote 使用 `childZygoteInit()`，跳过这套普通应用初始化，再进入自己的 Zygote 服务端循环。

应用调用 `attachApplication()` 回到 `system_server` 后，AMS 才发送 `bindApplication`。接着才有：

- 创建并附加应用；
- 安装当前进程的 ContentProvider；
- 调用 `Application.onCreate()`；
- 启动目标活动；
- 创建窗口并绘制首帧。

这给出了清晰的责任边界：

| 区间 | 优先怀疑 |
|---|---|
| `system_server` 请求到 PID 返回 | Zygote socket、USAP/fork、父进程调度 |
| `PostFork` | native specialize、mount、SELinux、运行时 post-fork hook |
| `ActivityThreadMain` 到 `attachApplication` | 子进程调度、运行时入口、Binder 初始化 |
| `bindApplication` | APK/类加载、Application、Provider、配置 |
| bind 完成到首帧 | Activity、View、资源、RenderThread、Surface |

---

## 四类 Zygote 不要混在一起

| 类型 | 谁启动 | 服务对象 | 预加载特点 | USAP |
|---|---|---|---|---|
| Primary Zygote | `init` | primary ABI、`system_server`、普通应用 | 通常 eager preload | 产品配置可启用 |
| Secondary Zygote | `init` | secondary ABI 普通应用 | 64/32 位配置中常为 lazy preload | 产品配置可启用 |
| WebView Zygote | `WebViewZygote` 经主 Zygote 创建 | WebView/renderer 相关进程 | 预加载当前 WebView provider | 不支持 |
| App Zygote | `AppZygote` 经主 Zygote 创建 | 声明 `useAppZygote` 的 isolated service | 调用应用的 `ZygotePreload` 实现 | 不支持 |

### App Zygote 与 `ZygotePreload`

`android.app.ZygotePreload` 从 API 29 提供。应用在 `<application>` 上用 `android:zygotePreloadName` 指定实现类，并在 isolated service 上设置 `android:useAppZygote="true"`。

预加载的数据会被该 App Zygote 后续派生的 isolated services 继承。实现时必须遵守与主 Zygote 类似的约束：

- 不创建会跨 fork 失效的线程；
- 不保留不该继承的连接和文件描述符；
- 优先加载只读、可共享、被多个 isolated service 使用的数据；
- 不把用户或单次请求状态放入父进程。

它不是普通活动进程的通用预加载 API。

### WebView Zygote

`WebViewZygote` 通过 `startChildZygote()` 创建 `webview_zygote`，等待 socket 可用，再用 `preloadApp()` 预加载当前 WebView 提供者的应用信息。切换 WebView 提供者后，旧 Zygote 需要停止或重建，不能把一次预热当作永久状态。

---

## Perfetto 中怎样拆分启动时间

建议同时采集：

- atrace 的 `am` 与 `dalvik`；
- sched switch / waking；
- Binder transaction；
- process lifecycle；
- Android EventLog events buffer；
- 需要分析内核 fork 时再加入 syscall 和内存事件。

Android 17 可使用的源码锚点包括：

- Zygote 进程：`ZygotePreload`、`PreloadClasses`、`CacheNonBootClasspathClassLoaders`、`PreloadResources`、`PreloadAppProcessHALs`、`PreloadGraphicsDriver`；
- 目标应用：`PostFork`、`ZygoteInit`、`ActivityThreadMain`、`bindApplication`；
- `system_server`：`launching: <package>` async trace；
- EventLog：`am_proc_start`、`am_proc_bound`。

EventLog 只有在跟踪启用 Android 日志并包含 events buffer 时才可查询。没有这些行不代表进程没有启动。

### 诊断顺序

1. 用 `launching: <package>` 圈出一次 Activity launch；
2. 确认目标 PID 是否为新进程；
3. 查设备是否启用 USAP，不要仅凭 `PostFork` 判断；
4. 比较 system_server 进程请求、目标进程首次调度、`PostFork`、`ActivityThreadMain`、`am_proc_bound` 和 `bindApplication`；
5. 对最长区间展开线程状态、Binder、I/O 和锁等待；
6. 把 `bindApplication` 之后的问题交给应用初始化和首帧分析。

几个常见结论：

- Zygote 侧等待长、目标进程尚未运行：检查套接字排队、USAP pool refill、父 Zygote 调度和系统负载；
- `PostFork` 长：检查原生特化步骤；
- `PostFork` 已结束，但 `ActivityThreadMain` 或附加很晚：检查新进程是否长期 runnable 未获 CPU，或运行时入口是否阻塞；
- `bindApplication` 长：优先检查内容提供者、Application、类加载和资源；
- 目标进程早已存在：本次是 warm/hot start，Zygote 不在关键路径。

不能用固定的“fork 应小于 N 毫秒”作为跨设备阈值。ABI、page size、SELinux、mount、调度、内存压力和厂商实现都会改变分布，应与同设备、同构建、同启动类型的基线比较。

---

## 版本演进

| 版本 | 已确认变化 | 分析意义 |
|---|---|---|
| Android 8 | AOSP 出现 `WebViewZygote` | WebView 相关进程有独立预加载父进程 |
| Android 9 | `PreloadAppProcessHALs` 出现在 Zygote preload | gralloc mapper HAL 开始在主 Zygote 阶段预热 |
| Android 10 | `PreloadGraphicsDriver` 替代旧 `preloadOpenGL`；AOSP 出现 USAP、App Zygote 与 `ZygotePreload` | 普通 fork、USAP、WebView/App child zygote 需要分开判断 |
| Android 17 | 当前固定基线；保留可选 `HttpEngine.preload()`、secondary lazy preload Zygote 延迟预加载和当前 USAP 策略 | 以产品开关、ABI/init 配置和实际跟踪判断生效路径 |

历史版本只用于说明机制何时出现。当前行为与路径一律回到 `android-17.0.0_r1`，内核 COW 一律回到 `android17-6.18-2026-06_r6`。

---

## 常见误区

### “`system_server` 通过 Binder 调用 Zygote”

创建进程命令走 Zygote `LocalSocket`。Binder 用在启动请求进入 `system_server`，以及子进程附加回 `system_server` 等位置。

### “看到 `PostFork` 就证明刚执行了 fork”

普通 fork 和 USAP 特化都会开始 `PostFork` trace。还要查看 USAP 配置、PID 和父进程事件。

### “预加载越多，应用一定越快”

预加载会增加开机和常驻内存成本；容易被写脏的对象还会削弱 COW。只读、普遍使用、可安全继承的数据才适合。

### “图形驱动预加载已经创建应用 GPU context”

它只预热驱动装载状态。应用自己的 RenderThread、context、Surface 与首帧仍在子进程中创建。

### “lmkd 杀缓存应用会破坏 Zygote 的父子复用”

普通应用一直从 Zygote 或 USAP 派生，不从其他缓存应用派生。`lmkd` 清理子进程不会改变这个父进程关系。

### “16KB 页让 fork 固定快 75%”

页表项、COW 粒度、缺页和内存浪费会同时变化；VMA 数量也不会按页大小等比缩减。必须实测。

---

## 源码阅读顺序

普通冷启动涉及以下源码路径：

1. `ProcessList.startProcess()`：选择普通、WebView 还是 App Zygote；
2. `ZygoteProcess.startViaZygote()`：组装参数、选择 ABI socket、判断 USAP；
3. `ZygoteServer.runSelectLoop()` / `ZygoteConnection.processCommand()`：Zygote 端接收命令；
4. `Zygote.forkAndSpecialize()` 与 `com_android_internal_os_Zygote.cpp`：fork 和安全特化；
5. `ZygoteConnection.handleChildProc()`：结束 `PostFork` 并选择普通应用或子 Zygote 入口；
6. `ZygoteInit.zygoteInit()` / `RuntimeInit.applicationInit()`：进入 `ActivityThread.main()`；
7. `ActivityThread.attach()` 与 AMS attach：从新进程回到 `bindApplication`。

冷启动跟踪中的每段时间都可对应到具体进程和职责：创建慢检查 Zygote，特化慢检查原生安全准备，绑定慢检查应用初始化，首帧慢检查组件与渲染。Zygote 优化应限定在它负责的范围内。
