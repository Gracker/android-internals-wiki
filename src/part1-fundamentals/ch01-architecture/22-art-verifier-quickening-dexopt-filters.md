---
title: 1.22 ART Verifier Quickening 与 dexopt 过滤器性能边界
chapter: 1.22
section: 1.22
status: ready-for-review
pipeline_stage: task6_pending
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
tags: [art, dex2oat, dexopt, verifier, vdex, startup]
confidence: high
last_verified: 2026-07-03
last_verified_against: source.android.com ART configure / ART Service configuration 2026-05; AOSP android-17.0.0_r1 platform/art compiler_filter.h / dex2oat.cc / libartservice/service/README.md; Android Developers ART compatibility docs
task6_review_notes: 2026-06-17 Task6 revisiting复审:pass-light-edit。L1/L2 扫描通过(1.22 复审无禁用词、高频词、元叙述命中);task9 auto-fix 已验证写作质量无回归;queue 无 pending;自动晋升 finalized。 | 2026-07-03 09 Task6 revisiting-review: pass-light-edit;L1/L2 小修 0 处(\"对齐\"为 zipalign 术语,非大厂黑话,保留);outline 7/7 覆盖;无 L3/L4 回炉项。Task9 result 为 auto-fixed(AOSP 锚点 android-17.0.0_r1 重锚),未满足 pass-tech-review 自动晋升条件,送 Task9 复核。
last_task6_review_log: logs/review/2026-07-03-11-review.md
task6_state: revisiting
task9_state: pending
drafted_date: 2026-05-24
related_chapters: [\"1.7\", \"1.9\", \"16.6\", \"21.11\"]
created_by: task2a-knowledge-gap
created_date: 2026-05-24
gap_source: 研究素材/官方文档/AOSP结构
path: intake/daily-info/2026-05-24.md#增量扫描-源码调研art-verifier-quickening-与-dex2oat-过滤器体系
task9_result: auto-fixed
task2b_state: fixed
task2b_result: fixed
last_task9_at: 2026-07-03T09:32:24+08:00
task9_reviewed_date: 2026-07-03
task9_reviewed_by: openclaw-task9
task9_review_notes: 2026-06-17 Task9 deep-review: AUTO-FIX P1 1; replaced AOSP main anchors with android-16.0.0_r1 after android-17 platform tag was not present. 2026-07-03 Task2B main: re-anchored all AOSP references from android-16.0.0_r1 to android-17.0.0_r1 (tag verified available on googlesource); no Android 18/API 38 material used. | 2026-07-03 09 Task9 deep-review AUTO-FIX:旧设备 quicken 表格把 ART Service 版本段写到 Android 14-16;android-17.0.0_r1 仍包含 platform/art libartservice,已改为 Android 14-17。P0 0 / P1 1 / P2 0;回到 Task6 复审。
last_task9_review_log: logs/deep-review/2026-07-03-09-deep-review.md
last_task9_autofix_at: 2026-07-03
task6_result: pass-light-edit
last_task2b_lite_at: 2026-06-30
task2b_lite_note: 2026-06-30 Task2B Lite: 修复 last_task6_review_log 字段被 title 污染的机械错误。
reviewed_by: openclaw-task6
reviewed_date: 2026-07-03
last_task6_at: 2026-07-03T11:12:00+08:00
last_task6_audit: 2026-07-03
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-17
p0: 0
p1: 1
p2: 0
task9_p0_issues: 0
task9_p1_issues: 1
task9_p2_issues: 0
---
-

# 1.22 ART Verifier Quickening 与 dexopt 过滤器性能边界

<!-- outline-start -->
## 要点

### 🔹 Verifier 在安装、首次启动和后台编译中的位置
梳理 ART bytecode verifier、`dex2oat`、VDEX/OAT 产物和 PackageManager 安装流程的关系,明确哪些耗时属于安装期,哪些会转移到首次运行或后台 dexopt。

### 🔹 compiler filter 的执行成本和效果边界
按 `verify`、`quicken`、`speed-profile`、`speed` 拆分工作内容、产物形态、启动效果、存储成本和适用版本，避免把过滤器当成单纯的优化等级。

### 🔹 quickening 的版本边界
说明 `quicken` 在 Android 11 及以下的解释器优化语义,以及 Android 12 之后官方过滤器口径变化对旧文档、旧设备和厂商定制 ROM 的影响。

### 🔹 ART Service 接管 dexopt 后的场景拆分
覆盖 Android 14+ ART Service 在 first boot、OTA、mainline update、install、bg-dexopt、cmdline 下的默认策略,以及 `pm.dexopt.*` 系统属性的排障价值。

### 🔹 VDEX、verifier deps 与 class loader context
解释 VDEX 中验证结果和 quickening 信息的复用条件,关联 class loader context mismatch、`<uses-library>` 检查和 dexpreopt 产物失效后的降级路径。

### 🔹 性能排障中的证据采集
整理 `pm compile`、`pm bg-dexopt-job`、`dumpsys package dexopt`、logcat ART/dex2oat 日志和安装耗时拆分方法,用于区分 verifier、AOT 编译、profile 缺失和 CLC mismatch。

### 🔹 与启动优化和云端 Profile 的关系
把本节与 1.7 ART 编译管线、16.6 Android 16 云端 Profile、21.11 DM 文件安装后编译优化建立交叉引用,只补执行策略和排障动作,不重复讲 ART 总体架构。

## 扩展

### 🔸 旧设备 quicken 产物与现代 ART Service 的兼容排查
围绕 Android 8-11 旧设备和 Android 14+ 主线化 ART 做版本对照,记录验证、quickening、AOT 产物复用的差异。

### 🔸 dexopt 策略对大体积应用安装耗时的影响
结合 very-large dex 降级、profile 缺失和后台 dexopt 取消条件,形成大包安装后首启慢的排障清单。

<!-- outline-end -->

## 本节解决什么问题

`verify`、`quicken`、`speed-profile`、`speed` 经常一起出现在安装、启动和 OTA 排障里。它们都通过 `dex2oat` 进入 ART 产物管理体系，但成本和效果完全不同：有的只做 DEX 验证，有的生成 profile-guided AOT 代码，有的属于 Android 11 及以下的解释器优化历史。

排查安装慢、升级后首启慢、后台 dexopt 没执行时,可以把问题归到三个具体位置:验证是否已经复用、AOT 是否按 profile 编译、当前 ROM 的 dexopt 场景是否选了符合预期的 compiler filter。

## Verifier、dex2oat 和 VDEX 的分工

ART 在运行 DEX 之前必须确认字节码的类型安全、访问权限、方法签名和控制流全部合规,这由 bytecode verifier 完成。Verifier 的输出不是"让代码更快"的机器码,而是一组能证明 DEX 可安全执行的验证结果。

`dex2oat` 的职责是把 APK 或 DEX 转成 ART 运行时可直接使用的产物。从 Android 8 开始,典型产物有三种:`.vdex`、`.odex` 和可选的 `.art`:

- `.vdex`: 存验证加速用的元数据,部分版本和场景也会存未压缩 DEX。
- `.odex`: 存 AOT 编译后的方法机器码。
- `.art`: 存 ART 内部字符串、类等启动加速数据。

这三个文件回答的问题不同。VDEX 让下一次验证少做重复解析;ODEX 让命中方法跳过解释执行和 JIT 热身;ART 文件减少部分运行时对象准备成本。排查时不能只看到 `/data/misc/apexdata/com.android.art/dalvik-cache` 里有文件就判断"已经优化完"。

### 安装期和运行期的边界

安装期可能触发 dexopt,但不会保证所有代码都已变成机器码。现代 Android 常见策略是:有 profile 时编译 profile 中的方法,没有 profile 时更偏向验证和延后优化。首次运行时,未 AOT 覆盖的方法仍会解释执行;热点方法随后由 JIT 编译,并写入本地 profile,等空闲充电窗口再进入后台 dexopt。

这也是"安装很快但首次启动慢"的常见来源。安装阶段选择 `verify` 时,系统已经完成安全验证和必要产物准备,但启动路径仍可能有解释执行、JIT 编译、类加载和 page fault。详见 1.7 节的 ART 编译管线,本文只讨论 filter 和验证产物的排障边界。

## compiler filter 不是优化等级

compiler filter 是传给 `dex2oat` 的策略参数。它决定本轮做多少验证、是否编译方法、是否依赖 profile。把它理解成"越高越好"的等级，会导致两个误判：为了启动效果强行用 `speed`，把安装和存储成本拉高；或者看到 `speed-profile` 就以为启动路径都已编译，忽略 profile 覆盖率。

| Filter | 做什么 | 产物重点 | 常见性能含义 | 版本边界 |
| --- | --- | --- | --- | --- |
| `verify` | 只运行 DEX 验证,不做 AOT 编译 | VDEX / 验证信息 | 安装、首启、OTA 更快;运行时仍可能解释执行和 JIT | Android 8+ 官方支持 |
| `quicken` | 验证 DEX,并优化部分 DEX 指令,减少解释器符号解析成本 | quickened DEX / VDEX | 改善解释执行成本,不生成机器码 | 官方文档限定 Android 11 及以下 |
| `speed-profile` | 验证 DEX,按 profile 编译方法,并优化 profile 中类加载 | ODEX + VDEX | 命中 profile 的启动路径更早执行机器码 | Android 8+ 官方支持 |
| `speed` | 验证 DEX,并 AOT 编译全部方法 | ODEX 体积更大 | 运行时覆盖广,安装时间和存储成本高 | Android 8+ 官方支持 |

AOSP `android-17.0.0_r1` 的 `art/libartbase/base/compiler_filter.h` 已经没有 `kQuicken` 枚举,保留的是 `kVerify`、`kSpaceProfile`、`kSpace`、`kSpeedProfile`、`kSpeed`、`kEverythingProfile`、`kEverything` 等当前过滤器。旧文章或旧 ROM 日志里出现 `quicken` 时,要先确认设备版本,再决定能否把它套到 Android 12+ 的行为上。

## quickening 的版本边界

`quicken` 解决的是解释器执行成本,不是 AOT 编译成本。它把部分 DEX 指令里的符号引用转换成运行时更容易使用的偏移或快速形式,减少解释器反复查方法表、字段表的成本。输出仍然是 DEX 层面的产物;方法没有因此变成 ARM64 / x86 机器码。

这条边界对性能判断很有用:

- Android 8-11 设备上,如果 filter 是 `quicken`,首启可能比纯 `verify` 少一些解释器解析开销,但热点方法仍要等 JIT 或后续 AOT。
- Android 12+ 文档口径里,`quicken` 已不再作为当前主线 filter 描述;排查重点应转到 `verify`、`speed-profile`、`speed` 以及 ART Service 的场景策略。
- 厂商 ROM 可能保留旧属性或日志字符串。只凭日志里出现 `quicken` 不能推断 Android 12+ / ART Service 口径的行为。

## ART Service 接管后的 dexopt 场景

Android 14 起,应用的 on-device AOT 编译由 ART Service 处理。ART Service 是 ART Mainline 模块的一部分,负责管理 dexopt 产物、查询编译状态、删除产物,并通过 `artd` 对接 `dex2oat`。Android 13 及以下仍以 Package Manager 侧 legacy 实现为主,版本跨度分析时要把这条线拆开。

Android 14+ 的标准默认值更偏保守:

```text
pm.dexopt.first-boot=verify
pm.dexopt.boot-after-ota=verify
pm.dexopt.boot-after-mainline-update=verify
pm.dexopt.bg-dexopt=speed-profile
pm.dexopt.inactive=verify
pm.dexopt.cmdline=verify
pm.dexopt.shared=speed
```

这组值反映了系统取舍:开机、OTA 和 mainline update 优先缩短阻塞时间;后台空闲充电阶段再用 profile 补编译;被其他应用加载的 shared app 不能直接使用本地 profile 时,可能走 `pm.dexopt.shared` 兜底策略。

### 场景对照表

| 场景 | 触发原因 | Android 14+ 默认行为 | 排障观察点 |
| --- | --- | --- | --- |
| very first boot / boot-after-OTA | `first-boot` / `boot-after-ota` | 主 dex 使用 `verify`,避免开机被大量 AOT 编译阻塞 | boot trace 里看 `artd` / `dex2oat` 是否集中,logcat 看 CLC mismatch |
| first boot after mainline update | `boot-after-mainline-update` | ART Service README 描述会优先处理 System UI 和 Launcher | SystemUI / Launcher filter、ART Mainline 版本 |
| app install | `install` / `install-fast` | 有 DM cloud profile 时可用 `speed-profile`;没有 profile 时常退到 `verify` | 安装来源、`.dm` 是否随包到达、`cmd package art dump` |
| idle + charging | `bg-dexopt` / `inactive` | JobScheduler 触发后台 dexopt,常用 `speed-profile`;任务可取消 | idle、charging、battery-not-low、后台任务日志 |
| command line | `cmdline` | 由 `pm compile`、`pm bg-dexopt-job`、`pm art dexopt-packages` 显式触发 | 命令参数和 verbose result |

这一节只给机制判断。Cloud Profile、Baseline Profile、`.dm` 文件和 SDM 产物的应用侧验证详见 16.6 节和 21.11 节;PMS、`InstallPackageHelper`、`DexOptHelper` 与安装 session 的关系详见 1.9 节。

## VDEX 复用和 class loader context

VDEX 的价值是减少重复验证。`dex2oat.cc` 在处理输入 VDEX 时,会打开 `input_vdex_file_`,解析 verifier deps,并在有可用 VDEX 时走快速验证路径。源码中还包含从 dex metadata archive 读取 VDEX 的路径,日志文案会提到 fast verification with vdex from DexMetadata archive。

VDEX 能否复用不只看文件是否存在,还要看 DEX checksum、bootclasspath、class loader context 和相关依赖是否匹配。`<uses-library>` 是常见触发点。dexpreopt 发生在构建机上,运行期加载发生在设备上;两边计算出的 class loader context 必须一致,否则构建期生成的 AOT 产物会被拒绝,设备端改跑 dexopt 或退回未优化执行。

排查 CLC mismatch 时,可以直接抓 logcat:

```bash
adb wait-for-device
adb logcat | grep -E 'ClassLoaderContext [a-z ]+ mismatch|Running dexopt' -A1
```

这条命令用于确认"预编译产物被拒绝后重新 dexopt"。看到 mismatch 后,要回到模块的 `Android.bp` / `Android.mk`、Manifest `<uses-library>`、设备端 shared library XML 配置,而不是只调 `pm.dexopt.*`。

## 性能排障证据采集

排查这类问题时,证据要分成三组:当前系统策略、当前包产物状态、本轮 trace 或日志里有没有发生编译。

这组命令用于记录 ROM 的 dexopt 默认策略和线程资源设置:

```bash
adb shell getprop | grep -E 'pm.dexopt|dalvik.vm.*dex2oat|dalvik.vm.usejit'
```

输出里的 `pm.dexopt.*` 只说明默认策略。厂商可以通过系统属性、ART Service API、安装来源和设备状态改变实际行为,包级结果还要继续看 dump。

这组命令用于确认指定包的当前编译状态:

```bash
adb shell cmd package art dump com.example.app
adb shell dumpsys package dexopt | grep -A 12 com.example.app
```

Android 14+ 优先看 `cmd package art dump`。旧设备或 ROM 裁剪后没有该命令时,再用 `dumpsys package dexopt`。重点字段是 compiler filter、compilation reason、primary / secondary dex 状态和 profile 是否被使用。

这组命令用于实验室复现 profile-guided 编译,不适合直接当线上结论:

```bash
adb shell cmd package compile -m speed-profile -f com.example.app
adb shell cmd package bg-dexopt-job
```

`pm compile` 能强制触发当前可用 profile 的编译,适合验证"有 profile 时系统能不能编译"。`bg-dexopt-job` 仍受设备状态和 ROM 策略影响,执行失败不能直接归因到 ART 问题。

## 三类常见问题的判断路径

### 安装慢

安装慢先拆文件 I/O、签名校验、包扫描、`.dm` 校验和 dexopt。Trace 里如果 `dex2oat` 进程占用 CPU 明显,`system_server` 里又能看到安装 session 提交后进入 dexopt,问题才落到 ART 编译成本。若当前 filter 是 `verify`,安装慢通常不该归因到完整 AOT 编译。

### 首次启动慢

首次启动慢要同时看编译状态和启动 trace。如果包状态停在 `verify`,trace 里有大量 `art::jit::*`、class loading、page fault,说明启动路径还在解释执行 / JIT 热身。若包状态已经是 `speed-profile`,但业务初始化、数据库迁移或网络同步占据主线程,继续扩大 profile 不会解决瓶颈。

### OTA 后首启慢

OTA 或 mainline update 后,bootclasspath、boot image、ART Mainline 版本都可能变化,旧 dexpreopt 产物会失效。Android 14+ 默认用 `verify` 降低开机阻塞,很多应用不会在首启阶段重新 AOT。用户感知到"升级后第一次打开慢",可能来自后台 dexopt 尚未完成,也可能来自 CLC mismatch 后产物被拒绝。

## 旧设备 quicken 产物排查

Android 8-11 设备仍可能出现 `quicken`。这类设备上，不要把 `quicken` 当作 `speed-profile` 的低配版本。它的好处来自解释器快速路径，不能提供 AOT 机器码覆盖。

| 版本段 | 重点 filter | 排查重点 |
| --- | --- | --- |
| Android 8-11 | `verify` / `quicken` / `speed-profile` / `speed` | 区分 quickened DEX、VDEX 和 ODEX;观察首次运行后 JIT 是否继续活跃 |
| Android 12-13 | `verify` / `speed-profile` / `speed` 为主 | ART Mainline 化后,旧 `quicken` 口径不再直接套用 |
| Android 14-17 | ART Service 管理 dexopt | 以 `cmd package art dump`、`pm.dexopt.*`、JobScheduler 状态和 `.dm` / profile 为主 |

## 大体积应用安装后首启慢清单

大包最容易把安装、编译、首次启动混在一起。排查时按下面顺序做,不要先改 compiler filter:

1. 确认安装来源是否传递 `.dm` / Baseline Profile / Cloud Profile。
2. 确认 `cmd package art dump` 里的 filter 和 reason,是 `verify`、`speed-profile` 还是 `speed`。
3. 检查 APK / split 的 DEX 数量、未压缩和对齐状态,以及启动路径是否跨多个 DEX。
4. 用 Perfetto 同时看 `system_server`、`artd`、`dex2oat`、目标应用主线程和 `art::jit::*`。
5. 等待空闲充电窗口或手动实验 `pm compile -m speed-profile -f`,对比首启、第二次启动和后台 dexopt 后启动。
6. 若出现 CLC mismatch,优先修 `<uses-library>` 和 shared library 配置,不要用强制 `speed` 掩盖产物拒绝。

这套清单的目标是把"安装后慢"拆成四类:profile 没到设备、profile 到了但未编译、编译完成但启动瓶颈不在代码执行、构建期和运行期依赖不一致导致产物被拒绝。

## References

- [已验证: 官方文档] Configure ART - `https://source.android.com/docs/core/runtime/configure`
- [已验证: 官方文档] ART Service configuration - `https://source.android.com/docs/core/runtime/configure/art-service`
- [已验证: 官方文档] Dexpreopt and `<uses-library>` checks - `https://source.android.com/docs/core/runtime/art-class-loader-context`
- [已验证: 官方文档] Verifying app behavior on ART - `https://developer.android.com/guide/practices/verifying-apps-art`
- [已验证: AOSP android-17.0.0_r1] `art/libartbase/base/compiler_filter.h`
- [已验证: AOSP android-17.0.0_r1] `art/dex2oat/dex2oat.cc`
- [已验证: AOSP android-17.0.0_r1] `art/libartservice/service/README.md`
- [来源: Obsidian] `intake/daily-info/2026-05-24.md`
