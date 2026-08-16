# 附录 B：常用 adb / dumpsys 命令速查

`adb`（Android Debug Bridge）是开发机与 Android 设备通信的命令行工具。`dumpsys` 在设备端读取系统服务诊断信息，`am` 和 `pm` 分别调用 Activity Manager 与 Package Manager 的命令接口。

命令输出会随 Android 版本、厂商实现、构建类型和 shell 权限变化。遇到参数差异时，先运行 `adb --help`、`adb shell am help`、`adb shell pm help` 或 `adb shell dumpsys <service> -h`，不要把某台设备的输出格式当成稳定 API。

## 使用前确认

- 多台设备同时连接时，先用 `adb devices -l` 找到序列号，再在命令中加入 `adb -s <serial>`；否则 adb 会拒绝执行，或脚本可能选错目标。
- `<package_name>` 与 `<pkg>` 都表示应用包名，`<activity>` 表示组件类名，`<file>` 表示设备端路径。主机路径和设备路径属于两个文件系统，复制文件要使用 `adb push` 或 `adb pull`。
- `dumpsys`、`getprop` 和多数查询命令通常只读；`batterystats --reset`、`force-stop`、`kill`、`send-trim-memory`、`pm clear`、权限变更和强制编译会修改设备或应用状态。
- `pm clear` 会删除应用用户数据，`batterystats --reset` 会清除设备级电池统计。只在目标明确的测试设备上执行，并先保存需要的现场。

零售设备通常运行 user 构建，shell 权限受限；userdebug 和 eng 是面向调试或开发的系统构建。root 表示取得系统最高权限，量产设备通常不允许 `adb root`。

---

## 1. 基础设备与状态查询

| 命令 | 用途与说明 |
|:---|:---|
| `adb devices` | 列出已连接设备及连接状态；`device` 只表示 adb 已连接，不保证系统已经完成启动 |
| `adb shell getprop ro.build.version.release` | 获取 Android 版本号，例如 15 或 17 |
| `adb shell getprop ro.build.version.sdk` | 获取 API 级别，例如 35 或 37 |
| `adb shell getprop ro.product.cpu.abi` | 获取设备首选 ABI；ABI 是原生二进制接口，比“CPU 型号”更准确 |
| `adb shell wm size` | 获取物理分辨率和可能存在的覆盖分辨率 |
| `adb shell wm density` | 获取物理密度和可能存在的覆盖密度，单位为 dpi |

## 2. dumpsys 系统服务查询

`dumpsys` 可输出设备上的系统服务状态。`adb shell dumpsys -l` 列出当前设备支持的服务；`adb shell dumpsys -t <seconds> <service>` 可设置等待服务返回的超时时间，默认通常为 10 秒。

### 2.1 界面与 Activity 栈（activity / window）

| 命令 | 用途与说明 |
|:---|:---|
| `adb shell dumpsys activity top` | 查看顶部 Activity、所属任务和进程信息；字段随平台版本变化 |
| `adb shell dumpsys activity activities` | 打印 Activity 与 Task 的组织关系，用于核对前后台和任务栈 |
| `adb shell dumpsys window windows` | 打印窗口列表、Z order、bounds、焦点等信息；Z order 表示窗口叠放顺序，bounds 表示几何边界 |
| `adb shell dumpsys activity processes` | 打印进程重要性、调度组和内存调整值；`oom_adj` 或相关字段用于系统回收决策，不能当作应用内存大小 |

### 2.2 内存分析（meminfo）

VSS 是虚拟地址空间大小，RSS 是驻留物理内存的页总量，PSS 会按共享比例分摊内存，USS 只计算进程独占的页。四者口径不同，不能互相替代，也不能直接等同于 Java 堆。

| 命令 | 用途与说明 |
|:---|:---|
| `adb shell dumpsys meminfo` | 打印系统内存概况与进程 PSS 汇总；完整输出可能较慢 |
| `adb shell dumpsys meminfo <package_name>` | 打印指定应用的 Java Heap、Native Heap、Graphics、代码映射等分类 |
| `adb shell procrank` | 打印进程 VSS、RSS、PSS、USS；零售版设备可能没有该命令或拒绝 shell 读取，常需 root、userdebug 或 eng 构建 |

### 2.3 渲染与 SurfaceFlinger（gfxinfo / SurfaceFlinger）

SurfaceFlinger 是 Android 的系统显示合成服务，HWC（Hardware Composer）是硬件合成器，Layer 是参与合成的图层。

| 命令 | 用途与说明 |
|:---|:---|
| `adb shell dumpsys gfxinfo <package_name> framestats` | 输出 View 渲染的近期帧统计，常见实现最多保留约 120 帧；不能完整覆盖 OpenGL、Vulkan、Unity 或其他直接渲染路径 |
| `adb shell dumpsys SurfaceFlinger` | 打印 Layer、Display、VSync、HWC 等合成状态；输出结构会随平台和厂商实现变化 |
| `adb shell dumpsys SurfaceFlinger --list` | 只列出当前由 SurfaceFlinger 管理的 Layer 名称，适合先缩小目标范围 |

### 2.4 功耗与唤醒锁（batterystats / power）

Wakelock（唤醒锁）用于阻止设备进入部分休眠状态。BatteryStats 记录系统归因事件和估算值，无法替代外部功率计的精确能量测量。

| 命令 | 用途与说明 |
|:---|:---|
| `adb shell dumpsys batterystats --reset` | 清除整台设备的历史电池统计并开始新的观察窗口；该操作会破坏原有现场 |
| `adb shell dumpsys batterystats <package_name>` | 查看指定应用相关的唤醒、网络、位置等归因统计；不同版本可用字段不同 |
| `adb shell dumpsys power` | 查看电源管理、交互、休眠与唤醒锁状态 |
| `adb shell dumpsys alarm` | 查看 Alarm 队列、触发时间和来源，用于排查频繁定时唤醒 |

---

## 3. am（Activity Manager）操作

`am` 可启动组件、停止进程、发送广播或请求诊断操作。该组命令多会改变应用状态，执行后要重新建立测试基线。LMKD 是 Android 在系统内存紧张时选择并终止进程的守护进程。

| 命令 | 用途与说明 |
|:---|:---|
| `adb shell am start -W -n <pkg>/<activity>` | 启动指定 Activity，并返回 `ThisTime`、`TotalTime`、`WaitTime` 等字段；测试前要明确采用哪个字段和启动类型 |
| `adb shell am force-stop <package_name>` | 强制停止包关联的进程，并把包置为 stopped 状态；与自然进程死亡不同 |
| `adb shell am kill <package_name>` | 只终止系统认为可安全停止的后台进程；可测试进程重建，但不能复现真实 LMKD 内存压力现场 |
| `adb shell am send-trim-memory <pkg> <level>` | 请求进程处理指定内存裁剪级别；回调是否送达及可用级别受版本、进程状态和构建限制，需在应用日志中验证 |
| `adb shell am profile start <pkg> <file.trace>` | 对允许分析的进程启动方法跟踪，输出到设备端路径；采集本身有开销，零售版设备可能拒绝目标应用 |
| `adb shell am profile stop <pkg>` | 停止由 `am profile start` 启动的方法跟踪 |
| `adb shell am dumpheap <pkg> <file.hprof>` | 请求生成 Java 堆转储到设备端路径；通常要求目标构建允许调试或性能分析，转储会暂停进程并占用存储空间 |

---

## 4. pm（Package Manager）操作

`pm` 管理已安装包、用户数据、权限和编译状态。dexopt 是 ART（Android 运行时）在设备上编译或优化 DEX 代码的过程；profile 是记录常走代码路径的数据，Baseline Profile 是随应用发布的预置热点规则。涉及数据删除、权限或 dexopt 的命令都应视为有状态操作。

| 命令 | 用途与说明 |
|:---|:---|
| `adb shell pm list packages -3` | 列出系统可见的第三方应用包名；多用户设备可加 `--user <user_id>` 限定用户 |
| `adb shell pm path <package_name>` | 输出应用已安装 APK 的设备端路径；拆分安装会返回 base 与多个 split APK |
| `adb shell pm clear <package_name>` | 删除指定用户下的应用数据并停止应用；该数据无法通过撤销命令恢复 |
| `adb shell pm grant <pkg> <permission>` | 授予应用已经声明、且允许 shell 授予的运行时权限；不适用于所有权限类型 |
| `adb shell pm revoke <pkg> <permission>` | 撤销应用的运行时权限，可能触发进程重启或行为变化 |
| `adb shell cmd package compile -m speed-profile -f <pkg>` | 强制按设备上现有 profile 编译目标包；没有可用 profile 时，执行成功也不能证明 Baseline Profile 已生效 |
| `adb shell dumpsys package dexopt \| grep -A 2 <package_name>` | 在 macOS/Linux 主机筛选 dexopt 状态；Windows 可用 PowerShell。`status=speed-profile` 表示有已编译 profile 正在使用，还要结合 `reason` 判断来源 |

---

## 5. Logcat、ANR 与 bugreport

Logcat 是 Android 的日志读取工具。ANR（Application Not Responding）表示应用未在系统规定时间内响应；Android vitals 是 Google Play Console 汇总的线上质量指标。

| 命令 | 用途与说明 |
|:---|:---|
| `adb logcat -v time` | 持续输出当前 shell 有权限读取的日志缓冲区，并显示时间；不代表设备上的全部日志 |
| `adb logcat -s TAG` | 只输出指定 TAG，例如 `adb logcat -s Choreographer` |
| `adb logcat \| grep -E 'am_anr\|am_crash'` | 在 macOS/Linux 主机过滤 ANR 与崩溃事件；Windows 可改用 `findstr` 或 PowerShell |
| `adb shell ls /data/anr` | 列出 ANR 线程转储：旧系统常见单个 `traces.txt`，新系统常见多个 `anr_*`；直接访问通常需要 root |
| `adb pull /data/anr/<filename>` | 把指定 ANR 转储复制到主机；零售版设备无法 `adb root` 时，改用 bugreport 或 Android vitals |
| `adb bugreport <output_directory>` | 在已有主机目录生成包含系统服务、日志和线程现场的 bugreport zip；多设备连接时使用 `adb -s <serial> bugreport <output_directory>` |

---

## 6. Perfetto 与 atrace

system trace（系统跟踪）是按时间排列的调度、频率、Binder、图形与应用事件记录。atrace 输出传统 Systrace 文本，Perfetto 可采集更丰富的数据源并生成 `.perfetto-trace` 文件。

| 命令 | 用途与说明 |
|:---|:---|
| `adb shell atrace --list_categories` | 列出当前设备支持的 atrace 类别；类别集合随设备变化 |
| `adb shell atrace gfx view wm am res sched freq -t 5 > trace.txt` | 采集 5 秒 atrace，并通过主机 shell 重定向到本地 `trace.txt`；先确认所列类别存在 |
| `adb push config.pbtxt /data/local/tmp/config.pbtxt` | 把文本格式的 Perfetto 配置复制到设备临时目录 |
| `adb shell perfetto --txt -c /data/local/tmp/config.pbtxt -o /data/misc/perfetto-traces/trace.perfetto-trace` | 按文本配置采集，并把结果写入设备端 trace 目录；`.pbtxt` 配置需要 `--txt` |
| `adb pull /data/misc/perfetto-traces/trace.perfetto-trace` | 把采集结果复制到当前主机目录，再用 Perfetto UI 打开 |

> 旧录制入口 [UI 工具](https://ui.perfetto.dev/record) 已返回 404，作为 `legacy-reference-preserved` 保留。
>
> 当前从 [Perfetto UI](https://ui.perfetto.dev/) 选择 “Record New Trace”；也可使用 `tools/record_android_trace` Python 脚本或设备端命令。
>
> 自动化测试通常使用脚本或设备端命令，并把配置文件与结果一起归档。

## 一手资料

- [Android Debug Bridge](https://developer.android.com/tools/adb)
- [dumpsys](https://developer.android.com/tools/dumpsys)
- [采集和阅读 bugreport](https://developer.android.com/studio/debug/bug-report)
- [ANR 线程转储](https://developer.android.com/topic/performance/vitals/anr)
- [调试 Baseline Profile](https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles)
- [Perfetto system tracing](https://perfetto.dev/docs/getting-started/system-tracing)
