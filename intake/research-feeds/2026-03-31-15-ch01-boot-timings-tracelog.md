# [研究] BootTimingsTraceLog 与 SystemServer 启动时间度量体系

- **来源**: AOSP 源码 (frameworks/base/core/java/com/android/internal/os/ZygoteInit.java + frameworks/base/services/core/java/com/android/server/BootTimingsTraceLog.java)
- **作者/机构**: Google / AOSP
- **日期**: 2026-03-31
- **四维评分**: 相关性 5/5 · 技术深度 4/5 · 时效性 4/5 · 可验证性 5/5 · **总分 18/20**
- **映射章节**: 1.2 系统启动全流程
- **映射锚点**: 启动时间的度量、BootTimingsTraceLog、boot_progress 里程碑
- **摘要**: Android 系统启动时间度量由两套互补的追踪机制组成：BootTimingsTraceLog 用于 Zygote 预加载阶段的耗时标记，TimingsTraceAndSlog 用于 SystemServer 各服务启动阶段的耗时记录。两者均通过 traceBegin/traceEnd 输出到 Perfetto/Systrace。

## 关键发现

### 1. BootTimingsTraceLog 的工作机制

BootTimingsTraceLog 是一个轻量级的启动耗时记录工具类，主要在 ZygoteInit 中使用。它对 Zygote 预加载过程的关键阶段进行 traceBegin/traceEnd 标记：

- **BeginIcuCachePinning**: ICU 数据内存锁定耗时
- **PreloadClasses**: 预加载常用 Java 类到 ART 运行时的耗时（通常是 Zygote 预加载中最耗时的阶段）
- **PreloadResources**: 预加载常用资源的耗时
- **PreloadOpenGL**: OpenGL 相关预加载
- **PreloadSharedLibraries**: 共享库预加载
- **PreloadTextResources**: 文本资源预加载

源码位置：`frameworks/base/core/java/com/android/internal/os/ZygoteInit.java`

每个 traceBegin/traceEnd 对会在 Perfetto 中生成为 system_server 进程下的 slice 事件，可以通过 Perfetto UI 直接查看。

### 2. TimingsTraceAndSlog：SystemServer 启动追踪

SystemServer 使用 TimingsTraceAndSlog（而非 BootTimingsTraceLog）来追踪四个核心启动阶段：

1. **startBootstrapServices()**: 启动相互依赖的关键服务（ATMS、PMS 等）
2. **startCoreServices()**: 启动无直接依赖的核心服务（BatteryService、UsageStatsService 等）
3. **startOtherServices()**: 启动其余系统服务（AMS、WMS 等），这是最耗时的阶段
4. **startApexServices()**: [Android 16+] 启动 APEX 模块中的服务

TimingsTraceAndSlog 同时做了两件事：
- 通过 `Trace.traceBegin()/traceEnd()` 写入 Perfetto 追踪
- 通过 `Slog` 输出日志（因此名字中有 "AndSlog"）

源码位置：`frameworks/base/core/java/android/os/TimingsTraceAndSlog.java`

### 3. boot_progress 里程碑事件

除了上述 trace 标记，Android 还通过 logcat 输出一系列 boot_progress 里程碑：

- `boot_progress_preload_start` / `boot_progress_preload_end`: Zygote 预加载起止
- `boot_progress_system_run`: SystemServer 准备就绪
- `boot_progress_pms_start` / `boot_progress_pms_ready`: PMS 启动与就绪
- `boot_progress_ams_ready`: AMS 就绪
- `boot_progress_enable_screen`: 屏幕点亮

这些事件可通过 `logcat | grep boot_progress` 快速查看各阶段耗时，也可在 Perfetto 的 logcat track 中检索。

### 4. 在 Perfetto 中的可视化

在 Perfetto 中分析启动性能的推荐方法：

1. 使用 `adb shell perfetto -c - --txt` 配置开机 trace 抓取
2. 在 Perfetto UI 中查看 `system_server` 进程的 track
3. 每个 startBootstrapServices/startCoreServices/startOtherServices 会显示为嵌套的 slice
4. 结合 CPU scheduling track 判断是否因 CPU 调度或 I/O 等待导致延迟

分析工具辅助：
- `system/extras/boottime_tools/bootanalyze/bootanalyze.py`: 自动分析 boot trace
- Perfetto SQL: `SELECT name, dur FROM slice WHERE name LIKE "Start%sServices"` 可量化各阶段耗时

## 可直接引用段落

> BootTimingsTraceLog 和 TimingsTraceAndSlog 是 Android 框架内置的两套启动耗时追踪工具。前者专注于 Zygote 预加载阶段（PreloadClasses、PreloadResources 等），后者覆盖 SystemServer 的全部服务启动阶段（startBootstrapServices、startCoreServices、startOtherServices、startApexServices）。两者都通过 Trace.traceBegin/traceEnd 将计时数据写入 atrace/ftrace，最终可在 Perfetto 中可视化。在 Perfetto UI 中，这些事件显示在 system_server 进程的 track 上，每个服务启动阶段呈现为独立的 slice，可以精确到毫秒级别分析耗时。

> 对于快速定位启动瓶颈，最直接的方法是通过 logcat 过滤 boot_progress 关键字，查看从 boot_progress_system_run 到 boot_progress_enable_screen 之间各里程碑的耗时。如果某个阶段耗时异常（比如 PMS 启动超过 2 秒），再配合 Perfetto trace 深入分析该阶段内的具体原因——是 CPU 调度延迟、I/O 等待、还是锁竞争。

## 与 queue.json 联动

- **优先级调整建议**: 1.2 的 priority 90 应保持（review 回炉补充 BootTimingsTraceLog 后可推进到加工状态）
- **素材路径建议**: 补充到 1.2 的 material_paths
