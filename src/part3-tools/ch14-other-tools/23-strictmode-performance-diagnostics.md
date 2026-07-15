---
title: "StrictMode 性能检查与开发期诊断"
chapter: "14.23"
status: finalized
task2b_result: fixed-lite
task2b_state: fixed
task6_state: "reviewed"
task6_result: pass-light-edit
task6_reviewed_date: "2026-06-17"
last_task6_at: "2026-06-17T19:12:00+08:00"
task9_state: reviewed
pipeline_stage: ready-to-publish
last_task2b_lite_at: 2026-06-17
applicable_versions: "Android 9 (API 28) - Android 17 (API 37)"
tags: [strictmode, disk-read, disk-write, network, custom-penalty, performance-diagnostics]
related_chapters: ["15.6", "14.4", "21.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-07"
drafted_date: "2026-06-08"
last_verified: "2026-06-08"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
task9_result: auto-fixed
last_task9_at: "2026-06-17T14:32:54+08:00"
task9_reviewed_date: "2026-06-17"
task9_reviewed_by: openclaw-task9
last_task9_autofix_at: "2026-06-17"
last_task9_review_log: "logs/deep-review/2026-06-17-14-deep-review.md"
task9_review_notes: "2026-06-17 Task9 auto-fix: StrictMode API 归属、VmPolicy bit 口径、Compose/ActivityScenario 边界、DropBox/netd 说明与 AOSP android-17.0.0_r1 源码锚点修正；回到 Task6 复审。"
last_task6_audit: "2026-07-16"
last_task6_audit_notes: "L1抽检：链路→路径(大厂黑话)，关键 7→2(高频降频)，frontmatter完整"
p0: 0
p1: 0
p2: 0
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/os/StrictMode.java"
  - type: aosp
    path: "libcore/dalvik/src/main/java/dalvik/system/BlockGuard.java"
gap_source: "AOSP结构/官方文档/章节深挖"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-19
---

# 14.23 StrictMode 性能检查与开发期诊断

StrictMode 是 Android 提供的开发期性能守卫工具，能在主线程执行磁盘 I/O、网络请求、Closeable 泄漏等操作时主动拦截并报告。它不用于线上监控——线上场景靠 APM SDK（详见 19.27），StrictMode 负责在开发和测试阶段提前暴露问题。

源码位置：`frameworks/base/core/java/android/os/StrictMode.java`。底层拦截机制依赖 `dalvik.system.BlockGuard`（`libcore/dalvik/src/main/java/dalvik/system/BlockGuard.java`），在 JNI 调用、文件操作、网络 socket 操作的关键路径上插入检查点。

## StrictMode 的两类策略

StrictMode 分两条独立的策略线：

- **ThreadPolicy**：拦截当前线程上的阻塞操作（磁盘读、磁盘写、网络、自定义慢调用）
- **VmPolicy**：拦截虚拟机级别的违规（Activity 泄漏、Closeable 未关闭、SQLite 对象泄漏、非 SDK API 调用）

两条策略各自有独立的 detect 方法和 penalty 配置，互不干扰。

## ThreadPolicy 配置

### 检测项

```java
StrictMode.ThreadPolicy policy = new StrictMode.ThreadPolicy.Builder()
    .detectDiskReads()
    .detectDiskWrites()
    .detectNetwork()
    .detectCustomSlowCalls()
    .detectResourceMismatches()      // API 23+
    .detectExplicitGc()              // API 34+
    .penaltyLog()
    .build();
StrictMode.setThreadPolicy(policy);
```

各检测项的行为：

- `detectDiskReads()`：拦截主线程的文件读取操作。底层通过 BlockGuard 包装 `FileInputStream`、`FileOutputStream`、`RandomAccessFile` 的 read/write 调用。`SharedPreferences.getString()` 走 `XmlUtils.readFileMap()` 会触发此检测。
- `detectDiskWrites()`：拦截主线程的文件写入。`SharedPreferences.edit().commit()` 必然触发（`apply()` 不会，因为写入发生在后台线程）。参见 21.3 对 ContentProvider 启动阶段 SharedPreferences 使用方式的分析。
- `detectNetwork()`：拦截主线程的网络操作。BlockGuard 对 `Socket`、`HttpURLConnection` 的 connect/write/read 插入拦截。OkHttp 底层也走 Socket，同样会触发。
- `detectCustomSlowCalls()`：配合 `StrictMode.noteSlowCall("tag")` 使用，开发者自行标记耗时操作。适合标记那些不涉及磁盘/网络但耗时可能超标的逻辑（如 JSON 解析、Bitmap 解码）。
- `detectResourceMismatches()`（API 23+）：检测资源定义类型与读取方法不匹配，比如 `TypedArray.getInt()` 读取到 String 类型资源时触发 `ResourceMismatchViolation`。
- `detectExplicitGc()`（API 34+）：检测当前线程显式调用 `System.gc()` / `Runtime.gc()`。它是 ThreadPolicy 检测项，不属于 VmPolicy。

### Penalty 策略

```java
// 选项一：仅打 Log（推荐开发期默认配置）
.penaltyLog()

// 选项二：抛异常让 App 崩溃（推荐 CI 环境和强制执行场景）
.penaltyDeath()

// 选项三：弹 Dialog 提示（开发期调试用，生产构建别开）
.penaltyDialog()

// 选项四：写入 DropBox（适合后台收集）
.penaltyDropBox()

// 选项五：自定义回调（接入自建日志或 APM）
.penaltyListener(new StrictMode.OnThreadViolationListener() {
    @Override
    public void onThreadViolation(StrictMode.Violation v) {
        // 自定义处理，如上报到内部日志系统
    }
})
```

`penaltyLog()` 在 Logcat 输出 tag 为 `StrictMode` 的日志。`penaltyDeath()` 抛出 `StrictModeViolation`（继承自 `RuntimeException`），适合 CI 环境把违规变成测试失败。`penaltyDeathWithNetwork()` 在网络违规时直接崩溃、其他违规仅打 Log——适合磁盘违规还想继续调试的场景。

`penaltyListener()`（API 28+）适合接入内部日志系统或 APM SDK，不中断运行的同时把违规记录到线上。

### Debug 构建启用模板

```java
public class MyApp extends Application {
    @Override
    public void onCreate() {
        if (BuildConfig.DEBUG) {
            StrictMode.setThreadPolicy(
                new StrictMode.ThreadPolicy.Builder()
                    .detectDiskReads()
                    .detectDiskWrites()
                    .detectNetwork()
                    .detectCustomSlowCalls()
                    .penaltyLog()
                    .build());

            StrictMode.setVmPolicy(
                new StrictMode.VmPolicy.Builder()
                    .detectLeakedClosableObjects()
                    .detectLeakedSqlLiteObjects()
                    .detectActivityLeaks()
                    .penaltyLog()
                    .build());
        }
    }
}
```

生产构建不启用。StrictMode 的检查本身有性能开销——BlockGuard 对每次 I/O 操作都做一次策略检查，在性能敏感路径上会影响测量结果。

## VmPolicy 配置

```java
StrictMode.VmPolicy vmPolicy = new StrictMode.VmPolicy.Builder()
    .detectActivityLeaks()
    .detectLeakedClosableObjects()
    .detectLeakedSqlLiteObjects()
    .detectNonSdkApiUsage()           // API 28+
    .detectUnsafeIntentLaunch()        // API 31+
    .penaltyLog()
    .build();
StrictMode.setVmPolicy(vmPolicy);
```

各检测项说明：

- `detectActivityLeaks()`：通过 `ActivityThread` 的创建/销毁路径维护 Activity 实例的期望计数；销毁后如果 `InstanceTracker` / `VMDebug.countInstancesOfClass()` 统计仍超过阈值，就报告 `InstanceCountViolation`。
- `detectLeakedClosableObjects()`：检查 `Closeable` 对象（`InputStream`、`OutputStream`、`Cursor` 等）是否在 finalize 时仍未关闭。底层通过 `CloseGuard`（`libcore/dalvik/src/main/java/dalvik/system/CloseGuard.java`）实现，每个 `Closeable` 在构造时注册一个 guard，`finalize()` 时检查 guard 是否已关闭。
- `detectLeakedSqlLiteObjects()`：SQLite 特化的泄漏检测。SQLiteCursor 和 SQLiteDatabase 在 finalize 时检查是否已关闭。和 `detectLeakedClosableObjects()` 有重叠，但 SQLite 检测会额外报告 SQL 语句和数据库路径。
- `detectNonSdkApiUsage()`（API 28+）：拦截通过反射或 JNI 访问非 SDK 接口的行为。Android 9 起对 `@hide` API 实施限制，这个检测帮助发现代码中的灰色地带。`setVmPolicy()` 会注册 `VMRuntime.setNonSdkApiUsageConsumer()` 并关闭 ART 内部去重，非 SDK 访问检查命中后回调到 StrictMode。
- `detectUnsafeIntentLaunch()`：检测应用把外部来源的 `Intent` 继续用于 `startActivity()`、`startService()`、`bindService()`、`sendBroadcast()` 或 `setResult()` 时可能触发的未保护组件/URI 授权风险。它主要是安全检测，不应写成 `setPackage()` / `setComponent()` 本身的性能问题。

## 违规日志分析

StrictMode 违规在 Logcat 中的典型输出格式：

```
D/StrictMode: StrictMode policy violation: android.os.strictmode.DiskReadViolation
    at android.os.StrictMode$AndroidBlockGuardPolicy.onThreadPolicyViolation(StrictMode.java:xxxx)
    at dalvik.system.BlockGuard.wrapAround(BlockGuard.java:xxx)
    at java.io.FileInputStream.read(FileInputStream.java:xxx)
    at android.app.SharedPreferencesImpl.getString(SharedPreferencesImpl.java:xxx)
    at com.example.MyActivity.onResume(MyActivity.java:42)
```

信息提取方法：

1. **违规类型**：第一行的 `DiskReadViolation` / `DiskWriteViolation` / `NetworkViolation` / `CustomSlowCallViolation` 标明问题类别。
2. **触发位置**：堆栈最下面的应用代码行（`MyActivity.java:42`）是问题发生的具体位置。
3. **中间路径**：`SharedPreferencesImpl.getString` → `FileInputStream.read` 说明是 SharedPreferences 的同步读触发了磁盘 I/O。

DropBox 标签：StrictMode 违规同时写入 DropBox（`android.os.DropBoxManager`），标签为 `system_app_strictmode`（系统应用）或 `data_app_strictmode`（第三方应用）。通过 `adb shell dumpsys dropbox --print` 可以查看历史违规记录，适合批量分析测试结果。

## 临时豁免机制

对已知的安全操作（如初始化时必要的文件读取），可以使用临时豁免：

```java
// 豁免磁盘读（包裹需要执行的操作）
StrictMode.ThreadPolicy old = StrictMode.allowThreadDiskReads();
try {
    // 这里执行必要的磁盘读取
    readConfigFromDisk();
} finally {
    StrictMode.setThreadPolicy(old);
}
```

`allowThreadDiskReads()` 和 `allowThreadDiskWrites()` 的返回值是当前的 ThreadPolicy，在 finally 块中恢复。注意这两个方法是 ThreadPolicy 级别的豁免，不影响 VmPolicy。

常见豁免场景：
- SharedPreferences 首次初始化（`Context.getSharedPreferences()` 在 API 31 之前会在主线程读取 XML 文件）
- 数据库首次打开（`SQLiteOpenHelper.getReadableDatabase()`）
- 日志库初始化时的文件创建

豁免不应该被滥用——每处豁免都应该有明确的注释说明为什么这条磁盘 I/O 不可避免。如果发现豁免超过 5 处，说明代码架构本身需要调整。

## CI/CD 集成

### Espresso 测试中启用

```java
@Before
public void enableStrictMode() {
    StrictMode.setThreadPolicy(
        new StrictMode.ThreadPolicy.Builder()
            .detectDiskReads()
            .detectDiskWrites()
            .detectNetwork()
            .penaltyDeath()    // CI 环境：违规即失败
            .build());
    StrictMode.setVmPolicy(
        new StrictMode.VmPolicy.Builder()
            .detectLeakedClosableObjects()
            .detectActivityLeaks()
            .penaltyDeath()
            .build());
}
```

`penaltyDeath()` 在测试环境中让违规变成测试失败，防止问题被忽略。结合 Firebase Test Lab 或 Android Test Orchestrator 时，StrictMode 违规会出现在测试报告的 crash 堆栈中。

`ActivityScenario` 不会替测试自动打开 StrictMode；需要在测试基类、JUnit Rule 或 `Application.onCreate()` 中显式设置策略，才能把违规转成 CI 失败。

### 将违规纳入 CI 失败条件

Gradle 配置示例（在 `build.gradle` 中通过 testOptions 传入）：

```groovy
android {
    testOptions {
        // 在 CI 环境通过系统属性控制
        // System.setProperty("strictmode.test", "death")
    }
}
```

在 CI 脚本中通过 `-Dstrictmode.test=death` 传入系统属性，Application 的 `onCreate()` 中读取并决定使用 `penaltyLog()` 还是 `penaltyDeath()`。

## 局限性与替代方案

### StrictMode 检测不到的场景

StrictMode 的拦截点有限，以下场景不会触发检测：

- **后台线程的磁盘 I/O 延迟**：StrictMode 只看主线程。如果后台线程的磁盘操作阻塞了主线程（如通过 `Future.get()` 等待），StrictMode 只能看到 `Future.get()` 的阻塞，看不到根因是磁盘 I/O。这类问题需要 Perfetto 的 `ftrace` + `io_uring` 分析（参见 13.10）。
- **Binder 调用耗时**：StrictMode 不检测 Binder IPC 耗时。跨进程调用 AMS/PMS/WMS 时的阻塞只能通过 Perfetto 的 Binder 轨道分析（参见 13.15）。
- **GPU 操作**：GPU 渲染管线的耗时（`RenderThread` 的 `drawFrames`）不在 StrictMode 覆盖范围。用 `adb shell dumpsys gfxinfo` 或 Perfetto 的 `gpu_mem` counter 分析。
- **内存分配抖动**：频繁的短生命周期对象分配导致的 GC 暂停，StrictMode 不检测。用 Android Studio Profiler 的 Memory面板或 Perfetto 的 `java_hprof` 数据源（参见 14.22）。

### 何时从 StrictMode 迁移到 Perfetto

StrictMode 解决的是"有没有"的问题——有没有主线程磁盘读、有没有网络调用。Perfetto 解决的是"有多慢"的问题——这个磁盘操作耗时多少、Binder 调用路径哪一步最慢。

当 StrictMode 的豁免列表越来越长、或者性能问题的瓶颈从"是否在主线程"转向"耗时多少毫秒"时，需要结合 Perfetto 自定义 trace 点做精确度量：

```java
// 从 StrictMode 的 noteSlowCall 过渡到 Perfetto trace
Trace.beginSection("MySlowOperation");
doWork();
Trace.endSection();
```

StrictMode + Perfetto 的组合使用：StrictMode 负责开发期门控（`penaltyDeath()` 阻止违规合入），Perfetto 负责性能度量（量化优化前后的耗时差异）。两者不是替代关系。

### 性能开销

BlockGuard 对每次 I/O 操作执行策略检查。在高频操作路径上（如每帧读取文件），StrictMode 会引入可测量的延迟。因此 StrictMode 仅在 Debug 构建启用，生产环境不开启。

量化 StrictMode 开销时，需在目标设备上分别测量 `penaltyLog()`、`penaltyDeath()` 和 `penaltyListener()`。结论不可直接套用固定毫秒数：违规处理会构造堆栈，`penaltyDeath()` 还会抛异常，DropBox / listener 路径的耗时也取决于系统负载。

## 扩展

### StrictMode 与 Jetpack Compose 的兼容性

Compose 的渲染管线在 `Composer` 层面不做文件 I/O，不会直接触发 StrictMode。但以下场景可能产生误报：

- Compose 的 `LaunchedEffect` 默认继承当前 composition 的协程上下文；Android UI 组合通常在主线程上运行，effect 体里直接做文件 I/O 仍会触发 ThreadPolicy。需要显式切到 `Dispatchers.IO`，例如 `rememberCoroutineScope().launch(Dispatchers.IO) { ... }`。
- `AndroidView` 包装的传统 View 如果在 `onMeasure`/`onLayout` 中做磁盘操作，会触发 StrictMode。这与 View 体系的行为一致，不是 Compose 特有问题。

### 常见违规模式的修复

| 违规模式 | 修复方向 | 注意事项 |
|----------|----------|----------|
| `SharedPreferences.commit()` | 改用 `apply()` | `commit()` 允许在调用线程同步写盘；`apply()` 走异步写盘，但仍要避免随后在主线程等待加载或 flush |
| `FileInputStream.read()` 在 `onCreate()` | 移到 `Dispatchers.IO` 协程 | 注意协程切换后变量作用域的变化 |
| `Cursor` 未关闭 | 使用 `use {}` 扩展函数 | Kotlin 的 `use` 会自动调用 `close()` |
| `OkHttp.execute()` 在主线程 | 移到 `viewModelScope` + `Dispatchers.IO` | OkHttp 的 `enqueue()` 是另一种方式 |
| `BitmapFactory.decodeFile()` | 移到后台线程 | `coil`/`Glide` 等图片库默认在后台解码 |

### 多进程环境中的行为

StrictMode 的策略是进程内的、线程级别的。每个进程需要独立配置。

- **ContentProvider 进程**：在 `Application.onCreate()` 中配置即可，和主进程一样。
- **Service 进程**：如果 Service 进程有自己的 `Application` 子类（通过 `android:process` 指定），在该子类的 `onCreate()` 中配置。如果共用 Application 类，通过进程名判断是否启用。
- **多进程 StrictMode 检测结果互不干扰**：每个进程有自己的 StrictMode 策略实例，不会跨进程报告。




## Android 14–17 VmPolicy 演进与跨 Binder 违规传播（源码级补充）

> 以下从 AOSP android-17.0.0_r1 源码出发，补充主章节 VmPolicy 层面的细节：比特位全景、跨 Binder 违规传播机制、以及 Android 14–17 窗口内的演进。

### VmPolicy 比特位全景（API 37 范围）

`StrictMode.java`（android-17.0.0_r1）里，本文只讨论 API 37 范围内可用、且与性能诊断直接相关的 `DETECT_VM_*` 位；下表聚焦 Android 14–17 窗口内的 bit 9–14：

| 比特 | 常量 | API | 主要特性 |
|------|------|-----|---------|
| bit 9  | `DETECT_VM_NON_SDK_API_USAGE` | API 28 | 与 `VMRuntime.setNonSdkApiUsageConsumer` 集成 |
| bit 10 | `DETECT_VM_IMPLICIT_DIRECT_BOOT` | API 29 | 在 CE/DE 加密盘加载前检测 direct-boot 误用 |
| bit 11 | `DETECT_VM_CREDENTIAL_PROTECTED_WHILE_LOCKED` | API 34 | 检测锁屏后访问 CE 加密路径 |
| bit 12 | `DETECT_VM_INCORRECT_CONTEXT_USE` | API 34 | `@TestApi`，配合 `permitIncorrectContextUse()` 豁免 |
| bit 13 | `DETECT_VM_UNSAFE_INTENT_LAUNCH` | API 33 | 通过 `IUnsafeIntentStrictModeCallback` 接收 AMS 端通知 |
| bit 14 | `DETECT_VM_BACKGROUND_ACTIVITY_LAUNCH_ABORTED` | API 36 | `@FlaggedApi(Flags.FLAG_BAL_STRICT_MODE_RO)` 双门控 |

### 跨 Binder 违规传播机制（gatheredViolations ThreadLocal）

主章节已提及"StrictMode 策略是进程内的、线程级别的"。但这里需要细化：被调用方进程内的违规如何回写到调用方进程。答案是 `gatheredViolations` ThreadLocal + Parcel 反向序列化。

**调用链**：

1. `StrictMode.setThreadPolicyMask(int mask)` 同步写两个 thread-local：libcore `BlockGuard`（Java 层）+ `Binder.setThreadStrictModePolicy`（native 层）。native 层跨 Binder transaction 把 mask 带到被调用方线程。
2. `libcore/.../BlockGuard.java::Policy.getPolicyMask()` 把 mask 暴露给 native binder —— `BlockGuard.Policy` 接口显式注释 `Returns the policy bitmask, for shipping over Binder calls to remote threads/processes`。
3. 被调用方进程触发违规时（如 system_server 在 onTransaction 路径做磁盘读），走 `onThreadPolicyViolation` → 判 `PENALTY_GATHER` 启用 → 把 `ViolationInfo` 累积到 `gatheredViolations.get().add(info)`。
4. `Parcel.writeNoException()` 返回前调 `StrictMode.hasGatheredViolations()` 检查 → 若有违规，把 `ViolationInfo` 列表序列化进 reply Parcel → `Parcel.writeException()` 反序列化在调用方进程重新 throw RuntimeException。

**代码片段**：

```java
// StrictMode.java - gatheredViolations ThreadLocal
private static final ThreadLocal<ArrayList<ViolationInfo>> gatheredViolations =
        new ThreadLocal<ArrayList<ViolationInfo>>() {
            @Override
            protected ArrayList<ViolationInfo> initialValue() {
                return null; // 起始 null，避免 hasGatheredViolations() 不必要分配
            }
        };

/* package */ static boolean hasGatheredViolations() {
    return gatheredViolations.get() != null;
}

/* package */ static void clearGatheredViolations() {
    gatheredViolations.set(null);
}

// setThreadPolicyMask 同步写双 thread-local
public static void setThreadPolicyMask(@ThreadPolicyMask int threadPolicyMask) {
    setBlockGuardPolicy(threadPolicyMask);    // Java 层 (Dalvik BlockGuard)
    Binder.setThreadStrictModePolicy(threadPolicyMask);  // Native 层 (Binder)
}
```

**性能影响**：跨 Binder 违规采集是无锁 ThreadLocal 累积（O(1)），但 Parcel 反向序列化包含完整 stacktrace，`new Throwable().fillInStackTrace()` 通常 50–200μs。`gatheredViolations` 在同条 Binder 事务内会去重（`info.getStackTrace().equals(previous.getStackTrace())`），但跨事务不复用。

### DETECT_VM_BACKGROUND_ACTIVITY_LAUNCH_ABORTED 的双门控

bit 14 在 Builder API 上是 `@FlaggedApi(Flags.FLAG_BAL_STRICT_MODE_RO)` 标注：

```java
@SuppressWarnings("BuilderSetStyle")
@FlaggedApi(Flags.FLAG_BAL_STRICT_MODE_RO)
public @NonNull Builder detectBlockedBackgroundActivityLaunch() {
    return enable(DETECT_VM_BACKGROUND_ACTIVITY_LAUNCH_ABORTED);
}

@SuppressWarnings("BuilderSetStyle")
@FlaggedApi(Flags.FLAG_BAL_STRICT_MODE_RO)
public @NonNull Builder ignoreBlockedBackgroundActivityLaunch() {
    return disable(DETECT_VM_BACKGROUND_ACTIVITY_LAUNCH_ABORTED);
}
```

**双门控机制**：

1. **客户端门控**：应用调用 `detectBlockedBackgroundActivityLaunch()` 才能在 VmPolicy mask 中打开 bit 14。
2. **服务端门控**：`Flags.FLAG_BAL_STRICT_MODE_RO` 必须通过 `DeviceConfig` 推送到设备且打开。`setVmPolicy` 内部判 `if ((sVmPolicy.mask & DETECT_VM_BACKGROUND_ACTIVITY_LAUNCH_ABORTED) != 0) registerBackgroundActivityLaunchCallback()`，服务端 flag 未开启时 `registerBackgroundActivityLaunchCallback` 走 no-op，AMS 端不会回调。

应用 + 服务端同时开启时，注册路径是 `ActivityTaskManager.getService().registerBackgroundActivityStartCallback(...)` → system_server 端 `ActivityTaskManagerService.mBgActivityStartCallbacks` 列表。BAL 被 abort 后通过 `IBackgroundActivityLaunchCallback.Stub` 回调到 app 进程，走 `penaltyLog()` 输出到 Logcat。

### DETECT_VM_NON_SDK_API_USAGE 的 ART 端联动

`StrictMode.setVmPolicy()` 内部根据 bit 9 是否开启，注册 / 取消 `VMRuntime.setNonSdkApiUsageConsumer`：

```java
private static final Consumer<String> sNonSdkApiUsageConsumer =
        message -> onVmPolicyViolation(new NonSdkApiUsedViolation(message));

// setVmPolicy 内部
if ((sVmPolicy.mask & DETECT_VM_NON_SDK_API_USAGE) != 0) {
    VMRuntime.setNonSdkApiUsageConsumer(sNonSdkApiUsageConsumer);
    VMRuntime.setDedupeHiddenApiWarnings(false);  // 关闭 ART 内部去重
} else {
    VMRuntime.setNonSdkApiUsageConsumer(null);
    VMRuntime.setDedupeHiddenApiWarnings(true);   // 恢复 ART 默认去重
}
```

`setDedupeHiddenApiWarnings(false)` 关闭 ART 内部去重确保每次访问 @hide / @UnsupportedAppUsage 都触发 consumer 回调。生产应用误开此检测在高频反射路径（如 Gson、Retrofit）上可能造成每秒数万次回调。`setViolationLogger(ViolationLogger listener)` 是 TestApi，测试期把违规收集到自定义 logger。

### DETECT_VM_CLEARTEXT_NETWORK 的 netd 集成

```java
int networkPolicy = NETWORK_POLICY_ACCEPT;
if ((sVmPolicy.mask & DETECT_VM_CLEARTEXT_NETWORK) != 0) {
    if ((sVmPolicy.mask & PENALTY_DEATH) != 0
            || (sVmPolicy.mask & PENALTY_DEATH_ON_CLEARTEXT_NETWORK) != 0) {
        networkPolicy = NETWORK_POLICY_REJECT;
    } else {
        networkPolicy = NETWORK_POLICY_LOG;
    }
}
INetworkManagementService netd = INetworkManagementService.Stub.asInterface(
        ServiceManager.getService(Context.NETWORKMANAGEMENT_SERVICE));
if (netd != null) {
    try {
        netd.setUidCleartextNetworkPolicy(android.os.Process.myUid(), networkPolicy);
    } catch (RemoteException ignored) { }
}
```

`NETWORK_POLICY_LOG` 路径只记录明文网络事件，不阻断连接；`NETWORK_POLICY_REJECT` 路径才会由 netd 拒绝流量。应用层看到的异常类型取决于 socket / TLS / Network Security Config 触发点，不能固定写成某一种 `SocketException`。

### DropBox 限流与 BackgroundThread 异步

`dropboxViolationAsync` 通过 `sDropboxCallsInFlight: AtomicInteger` 跟踪在飞 DropBox 写入：

```java
private static void dropboxViolationAsync(final int penaltyMask, final ViolationInfo info) {
    int outstanding = sDropboxCallsInFlight.incrementAndGet();
    if (outstanding > 20) {
        sDropboxCallsInFlight.decrementAndGet();
        return; // 超过 20 直接丢弃，避免 DropBoxManager 雪崩
    }
    BackgroundThread.getHandler().post(() -> {
        handleApplicationStrictModeViolation(penaltyMask, info);
        sDropboxCallsInFlight.decrementAndGet();
    });
}
```

**实战含义**：线上应用如果同时开 `PENALTY_DROPBOX` + 在高频路径违规（每分钟数百条），`sDropboxCallsInFlight` 会经常到 20 上限，后续违规直接丢弃。DropBox 条目写入 `/data/system/dropbox`，tag 常见为 `system_app_strictmode`（系统应用）或 `data_app_strictmode`（第三方应用）。配额和保留时间由 `DropBoxManagerService` 的全局配置控制，android-17.0.0_r1 默认保留 3 天、全局配额约 10MB（user）/20MB（userdebug），不要把它理解成单个 StrictMode tag 固定 24h/8KB。CI 测试更适合用 `penaltyListener` 把违规统一收集到自定义 logger。

### 推荐补充到章节 §14.23 的源码级引用清单

完整调研覆盖 14 个函数与 6 个集成锚点，需要更深细节时参考对应 DeepResearch 报告。

> [适用版本: Android 9 (API 28) - Android 17 (API 37)]
> [已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/os/StrictMode.java, libcore/dalvik/src/main/java/dalvik/system/BlockGuard.java]
> [版本边界: 仅使用 Android 17/API 37 及以下源码锚点]

> [适用版本: Android 9 (API 28) - Android 17 (API 37)]
> [已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/os/StrictMode.java]
> [已验证: AOSP android-17.0.0_r1, libcore/dalvik/src/main/java/dalvik/system/BlockGuard.java]


## 参考资料

### Android 14–17 StrictMode VmPolicy 演进与跨 Binder 违规传播机制
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-14-android17-strictmode-vmpolicy-evolution-cross-binder-propagation.md
- 类型：DeepResearch 调研结果
- 摘要：StrictMode VmPolicy 从 Android 14 的 10 个 DETECT_VM_* 比特扩展到 Android 17 的 15 个，新增 credential-protected-while-locked、incorrect-context-use、BAL-aborted 等。跨 Binder 违规传播靠 gatheredViolations ThreadLocal + Parcel.writeNoException() 反向序列化；BlockGuard.Policy 通过 getPolicyMask() 把策略位图打包进 Binder native thread-local。定位 14 个函数与 6 个集成锚点。

### Android 17 StrictMode 新增 FlaggedApi 集成与 ImplicitUriPermissionGrantViolation
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-19-strictmode-android17-new-features.md
- 类型：DeepResearch 调研结果
- 摘要：Android 17 引入 @FlaggedApi 标注的 detectBlockedBackgroundActivityLaunch 和 detectImplicitUriPermissionGrant，新增 BackgroundActivityLaunchViolation 和 ImplicitUriPermissionGrantViolation 两个 violation 类。bal_strict_mode_ro flag 通过 AConfig 实现 is_fixed_read_only 控制，支持双门控——应用端 enable + 服务端 DeviceConfig 推送同时开启才生效。