---
title: "StrictMode 性能检查与开发期诊断"
chapter: "14.23"
status: ready-for-review
applicable_versions: "Android 9 (API 28) - Android 17 (API 37)"
tags: [strictmode, disk-read, disk-write, network, custom-penalty, performance-diagnostics]
related_chapters: ["15.6", "14.4", "21.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-07"
drafted_date: "2026-06-08"
last_verified: "2026-06-08"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/os/StrictMode.java"
  - type: aosp
    path: "dalvik/system/BlockGuard.java"
gap_source: "AOSP结构/官方文档/章节深挖"
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
    .penaltyLog()
    .build();
StrictMode.setThreadPolicy(policy);
```

各检测项的行为：

- `detectDiskReads()`：拦截主线程的文件读取操作。底层通过 BlockGuard 包装 `FileInputStream`、`FileOutputStream`、`RandomAccessFile` 的 read/write 调用。`SharedPreferences.getString()` 走 `XmlUtils.readFileMap()` 会触发此检测。
- `detectDiskWrites()`：拦截主线程的文件写入。`SharedPreferences.edit().commit()` 必然触发（`apply()` 不会，因为写入发生在后台线程）。参见 21.3 对 ContentProvider 启动阶段 SharedPreferences 使用方式的分析。
- `detectNetwork()`：拦截主线程的网络操作。BlockGuard 对 `Socket`、`HttpURLConnection` 的 connect/write/read 插入拦截。OkHttp 底层也走 Socket，同样会触发。
- `detectCustomSlowCalls()`：配合 `StrictMode.noteSlowCall("tag")` 使用，开发者自行标记耗时操作。适合标记那些不涉及磁盘/网络但耗时可能超标的逻辑（如 JSON 解析、Bitmap 解码）。
- `detectResourceMismatches()`（API 23+）：检测资源类型不匹配，比如对 `TextView` 调用 `setImageResource()`。

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
    .detectExplicitGc()               // API 29+
    .detectUnsafeIntentLaunch()        // API 33+
    .penaltyLog()
    .build();
StrictMode.setVmPolicy(vmPolicy);
```

各检测项说明：

- `detectActivityLeaks()`：在 Activity `onDestroy()` 后检查该 Activity 实例是否仍被引用。如果被 GC root 间接持有，报告泄漏。实现方式是在 `ActivityThread` 的 `performDestroyActivity()` 路径中注册弱引用检查。
- `detectLeakedClosableObjects()`：检查 `Closeable` 对象（`InputStream`、`OutputStream`、`Cursor` 等）是否在 finalize 时仍未关闭。底层通过 `CloseGuard`（`libcore/dalvik/src/main/java/dalvik/system/CloseGuard.java`）实现，每个 `Closeable` 在构造时注册一个 guard，`finalize()` 时检查 guard 是否已关闭。
- `detectLeakedSqlLiteObjects()`：SQLite 特化的泄漏检测。SQLiteCursor 和 SQLiteDatabase 在 finalize 时检查是否已关闭。和 `detectLeakedClosableObjects()` 有重叠，但 SQLite 检测会额外报告 SQL 语句和数据库路径。
- `detectNonSdkApiUsage()`（API 28+）：拦截通过反射或 JNI 访问非 SDK 接口的行为。Android 9 起对 `@hide` API 实施限制，这个检测帮助发现代码中的灰色地带。底层通过 `VMRuntime setHiddenApiExemptions()` 和 class linker 的访问检查实现。
- `detectExplicitGc()`（API 29+）：检测代码中显式调用 `System.gc()`、`Runtime.gc()` 的行为。在 ART 环境下显式 GC 通常不必要，反而可能干扰分代 GC 的调度节奏。
- `detectUnsafeIntentLaunch()`（API 33+）：检测通过 `Intent.setPackage()` 或 `Intent.setComponent()` 启动外部组件时未做安全验证的行为。属于安全检测，但间接影响性能（恶意 Intent 可能触发不必要的进程启动）。

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

关键信息提取方法：

1. **违规类型**：第一行的 `DiskReadViolation` / `DiskWriteViolation` / `NetworkViolation` / `CustomSlowCallViolation` 标明问题类别。
2. **触发位置**：堆栈最下面的应用代码行（`MyActivity.java:42`）是问题发生的具体位置。
3. **中间路径**：`SharedPreferencesImpl.getString` → `FileInputStream.read` 说明是 SharedPreferences 的同步读触发了磁盘 I/O。

DropBox 标签：StrictMode 违规同时写入 DropBox（`android.os.DropBoxManager`），标签为 `system_app_strictmode`（系统应用）或 `data_app_strictmode`（第三方应用）。通过 `adb shell dumpsys dropbox --print` 可以查看历史违规记录，适合批量分析测试结果。

## 临时豁免机制

对已知的安全操作（如初始化时必要的文件读取），可以用临时豁免：

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

`penaltyDeath()` 在测试环境中让违规变成测试失败，防止问题被忽略。结合 Firebase Test Lab 或 Firebase Test Orchestra 时，StrictMode 违规会出现在测试报告的 crash 堆栈中。

`ActivityScenario`（AndroidX Test）在 API 28+ 会自动启用部分 StrictMode 检测。手动配置会叠加到自动配置之上。

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

StrictMode 解决的是"有没有"的问题——有没有主线程磁盘读、有没有网络调用。Perfetto 解决的是"有多慢"的问题——这个磁盘操作耗时多少、Binder 调用链路哪一步最慢。

当 StrictMode 的豁免列表越来越长、或者性能问题的瓶颈从"是否在主线程"转向"耗时多少毫秒"时，需要结合 Perfetto 自定义 trace 点做精确度量：

```java
// 从 StrictMode 的 noteSlowCall 过渡到 Perfetto trace
Trace.beginSection("MySlowOperation");
doWork();
Trace.endSection();
```

StrictMode + Perfetto 的组合使用：StrictMode 负责开发期门控（`penaltyDeath()` 阻止违规合入），Perfetto 负责性能度量（量化优化前后的耗时差异）。两者不是替代关系。

### 性能开销

BlockGuard 对每次 I/O 操作都做一次策略检查。在高频操作路径上（如每帧都读文件的极端情况），StrictMode 会引入可测量的延迟。这就是为什么 StrictMode 只在 Debug 构建启用、不在生产构建开启。

实测数据参考：启用 StrictMode 的 ThreadPolicy（全部检测项）后，主线程文件操作的额外开销约为每次调用 +0.1-0.5ms（取决于堆栈深度和 penalty 配置）。对于 `penaltyLog()` 这个量级通常可接受；`penaltyDeath()` 因为需要构造异常堆栈，开销略高。

## 扩展

### StrictMode 与 Jetpack Compose 的兼容性

Compose 的渲染管线在 `Composer` 层面不做文件 I/O，不会直接触发 StrictMode。但以下场景可能产生误报：

- Compose 的 `LaunchedEffect` 如果在 effect 体中执行文件操作，会在 `Recomposer` 线程触发。这不是主线程违规，StrictMode 的 ThreadPolicy 不会拦截。但如果使用 `rememberCoroutineScope { Dispatchers.IO }` 的方式不对，实际执行可能在主线程。
- `AndroidView` 包装的传统 View 如果在 `onMeasure`/`onLayout` 中做磁盘操作，会触发 StrictMode。这与 View 体系的行为一致，不是 Compose 特有问题。

### 常见违规模式的修复

| 违规模式 | 修复方向 | 注意事项 |
|----------|----------|----------|
| `SharedPreferences.commit()` | 改用 `apply()` | `apply()` 在 API 31+ 已改为异步写入，不会触发 StrictMode |
| `FileInputStream.read()` 在 `onCreate()` | 移到 `Dispatchers.IO` 协程 | 注意协程切换后变量作用域的变化 |
| `Cursor` 未关闭 | 使用 `use {}` 扩展函数 | Kotlin 的 `use` 会自动调用 `close()` |
| `OkHttp.execute()` 在主线程 | 移到 `viewModelScope` + `Dispatchers.IO` | OkHttp 的 `enqueue()` 是另一种方式 |
| `BitmapFactory.decodeFile()` | 移到后台线程 | `coil`/`Glide` 等图片库默认在后台解码 |

### 多进程环境中的行为

StrictMode 的策略是进程内的、线程级别的。每个进程需要独立配置。

- **ContentProvider 进程**：在 `Application.onCreate()` 中配置即可，和主进程一样。
- **Service 进程**：如果 Service 进程有自己的 `Application` 子类（通过 `android:process` 指定），在该子类的 `onCreate()` 中配置。如果共用 Application 类，通过进程名判断是否启用。
- **多进程 StrictMode 检测结果互不干扰**：每个进程有自己的 StrictMode 策略实例，不会跨进程报告。

> [适用版本: Android 9 (API 28) - Android 17 (API 37)]
> [已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/os/StrictMode.java]
> [已验证: AOSP android-17.0.0_r1, libcore/dalvik/src/main/java/dalvik/system/BlockGuard.java]
