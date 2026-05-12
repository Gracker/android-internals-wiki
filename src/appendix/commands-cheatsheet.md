# 附录 B：常用 adb / dumpsys 命令速查

在 Android 性能分析和日常排障中，终端命令是最快速、最底层的诊断工具。本速查表整理了最常用的 `adb`、`dumpsys`、`am` 和 `pm` 等命令，方便在实际开发中直接复制使用。

---

## 1. 基础设备与状态查询

| 命令 | 用途与说明 |
|:---|:---|
| `adb devices` | 列出当前连接的所有设备及状态 |
| `adb shell getprop ro.build.version.release` | 获取 Android 系统版本号（如 14, 15） |
| `adb shell getprop ro.build.version.sdk` | 获取 API 级别（如 34, 35） |
| `adb shell getprop ro.product.cpu.abi` | 获取设备 CPU 架构（如 arm64-v8a） |
| `adb shell wm size` | 获取屏幕分辨率（物理分辨率与覆盖分辨率） |
| `adb shell wm density` | 获取屏幕像素密度（DPI） |

## 2. Dumpsys 核心命令

`dumpsys` 可以打印所有系统服务（System Service）的当前状态。通过 `adb shell dumpsys -l` 可以列出所有支持的服务。

### 2.1 界面与 Activity 栈 (activity / window)
| 命令 | 用途与说明 |
|:---|:---|
| `adb shell dumpsys activity top` | 获取当前处于最前台（Top）的 Activity 及进程信息 |
| `adb shell dumpsys activity activities` | 打印整个 Activity Task 栈的层级状态 |
| `adb shell dumpsys window windows` | 打印当前所有的 Window 列表及其 Z-Order、Bounds 等几何信息 |
| `adb shell dumpsys activity processes` | 打印所有进程的运行状态、`oom_adj`（优先级）、内存分组 |

### 2.2 内存分析 (meminfo)
| 命令 | 用途与说明 |
|:---|:---|
| `adb shell dumpsys meminfo` | 打印整个系统的内存概况（按 PSS 排序的进程列表） |
| `adb shell dumpsys meminfo <package_name>` | 打印指定 App 的详细内存占用（Java Heap, Native, Graphics 等） |
| `adb shell procrank` | 打印系统中所有进程的 VSS, RSS, PSS, USS (通常需 Root) |

### 2.3 渲染与 SurfaceFlinger (gfxinfo / SurfaceFlinger)
| 命令 | 用途与说明 |
|:---|:---|
| `adb shell dumpsys gfxinfo <package_name> framestats` | 输出最近 120 帧的详细渲染耗时数据（按阶段划分） |
| `adb shell dumpsys SurfaceFlinger` | 打印所有 Layer、Display 配置、VSync 偏移以及 HWC 状态 |
| `adb shell dumpsys SurfaceFlinger --list` | 仅列出当前由 SurfaceFlinger 管理的所有 Layer 名称 |

### 2.4 功耗与唤醒锁 (batterystats / power)
| 命令 | 用途与说明 |
|:---|:---|
| `adb shell dumpsys batterystats --reset` | 清空历史电量统计数据（测试功耗前必须执行） |
| `adb shell dumpsys batterystats <package_name>` | 打印指定 App 的耗电统计（唤醒次数、网络请求、GPS 使用等） |
| `adb shell dumpsys power` | 打印当前的电源管理状态、休眠状态以及所有持有的 Wakelock |
| `adb shell dumpsys alarm` | 打印当前的 Alarm 队列，用于排查不合理的定时唤醒 |

---

## 3. AM (Activity Manager) 操作

`am` 命令用于与 ActivityManager 交互，可用于启动应用、发送广播、模拟低内存等。

| 命令 | 用途与说明 |
|:---|:---|
| `adb shell am start -W -n <pkg>/<activity>` | 冷启动应用并打印耗时（ThisTime, TotalTime, WaitTime） |
| `adb shell am force-stop <package_name>` | 强制停止指定应用的所有进程 |
| `adb shell am kill <package_name>` | 仅杀死处于后台的进程（模拟系统内存回收回收缓存进程） |
| `adb shell am send-trim-memory <pkg> <level>` | 向应用发送特定的内存裁剪级别（如 `RUNNING_CRITICAL`） |
| `adb shell am profile start <pkg> <file.trace>` | 启动方法级 Method Profiling（生成 .trace 文件） |
| `adb shell am profile stop <pkg>` | 停止 Method Profiling |
| `adb shell am dumpheap <pkg> <file.hprof>` | 触发指定 App 生成 Java Heap Dump |

---

## 4. PM (Package Manager) 操作

`pm` 命令用于与 PackageManager 交互，主要处理包管理、安装、权限相关。

| 命令 | 用途与说明 |
|:---|:---|
| `adb shell pm list packages -3` | 列出所有已安装的第三方 App 包名 |
| `adb shell pm path <package_name>` | 查找指定 App 的 APK 物理安装路径（含 split APKs） |
| `adb shell pm clear <package_name>` | 清除指定 App 的所有数据和缓存（等同于“清除数据”） |
| `adb shell pm grant <pkg> <permission>` | 授予应用特定运行时权限 |
| `adb shell pm revoke <pkg> <permission>` | 撤销应用的特定运行时权限 |
| `adb shell cmd package compile -m speed-profile -f <pkg>` | 手工触发 Baseline Profile / AOT 的完整编译 |

---

## 5. Logcat 与性能日志

| 命令 | 用途与说明 |
|:---|:---|
| `adb logcat -v time` | 输出带有时间戳的完整日志 |
| `adb logcat -s TAG` | 仅输出特定 TAG 的日志（如 `adb logcat -s Choreographer`） |
| `adb logcat \| grep -E 'am_anr\|am_crash'` | 过滤系统的 ANR 和 Crash 事件（需配合 grep，部分 Windows 端用 findstr） |
| `adb shell cat /data/anr/traces.txt` | 查看最新生成的 ANR traces 堆栈文件（Android 8 以前） |
| `adb bugreport > bugreport.zip` | 导出全系统的 bugreport（包含 traces、logs 和 dumpsys 快照，耗时较长） |

---

## 6. Perfetto 与 Atrace

通过命令行直接触发系统 Trace 抓取（适用于无法使用 UI 抓取的场景）。

| 命令 | 用途与说明 |
|:---|:---|
| `adb shell atrace --list_categories` | 列出当前设备支持的所有 Atrace 抓取类别（Tags） |
| `adb shell atrace gfx view wm am res sched freq -t 5 > trace.txt` | 抓取 5 秒的基础性能 Trace（传统 Systrace 格式） |
| `adb shell perfetto -c /data/misc/perfetto-traces/config.pbtx -o /data/misc/perfetto-traces/trace.perfetto-trace` | 以后台模式使用自定义 config 执行 Perfetto 追踪 |

> **提示**：目前抓取 Perfetto 最简便的方式是通过 [UI 工具](https://ui.perfetto.dev/record)，或通过 `tools/record_android_trace` Python 脚本一键执行。命令行方式通常用于自动化压测脚本中。
