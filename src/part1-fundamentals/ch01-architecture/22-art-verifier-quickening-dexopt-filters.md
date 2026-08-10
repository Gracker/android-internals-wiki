---
title: 1.22 ART Verifier Quickening 与 dexopt 过滤器性能边界
chapter: 1.22
section: 1.22
status: finalized
pipeline_stage: ready-to-publish
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
tags: [art, dex2oat, dexopt, verifier, vdex, startup]
confidence: high
last_verified: 2026-07-25
last_verified_against: source.android.com Configure ART / ART Service configuration / ClassLoaderContext / JIT 2026-07; AOSP android-17.0.0_r1 platform/art compiler_filter.h / compiler_filter.cc / dex2oat.cc / ART Service README / ArtShellCommand.java / ReasonMapping.java
sources:
  - type: official
    path: "https://source.android.com/docs/core/runtime/configure"
  - type: official
    path: "https://source.android.com/docs/core/runtime/configure/art-service"
  - type: official
    path: "https://source.android.com/docs/core/runtime/art-class-loader-context"
  - type: official
    path: "https://source.android.com/docs/core/runtime/jit-compiler"
  - type: aosp
    path: "platform/art/libartbase/base/compiler_filter.h @ android-17.0.0_r1"
  - type: aosp
    path: "platform/art/libartbase/base/compiler_filter.cc @ android-17.0.0_r1"
  - type: aosp
    path: "platform/art/dex2oat/dex2oat.cc @ android-17.0.0_r1"
  - type: aosp
    path: "platform/art/libartservice/service/README.md @ android-17.0.0_r1"
  - type: aosp
    path: "platform/art/libartservice/service/java/com/android/server/art/ArtShellCommand.java @ android-17.0.0_r1"
  - type: aosp
    path: "platform/art/libartservice/service/java/com/android/server/art/ReasonMapping.java @ android-17.0.0_r1"
task6_review_notes: "2026-06-17 Task6 revisiting复审:pass-light-edit。L1/L2 扫描通过(1.22 复审无禁用词、高频词、元叙述命中);task9 auto-fix 已验证写作质量无回归;queue 无 pending;自动晋升 finalized。 | 2026-07-03 09 Task6 revisiting-review: pass-light-edit;L1/L2 小修 0 处(\"对齐\"为 zipalign 术语,非大厂黑话,保留);outline 7/7 覆盖;无 L3/L4 回炉项。Task9 result 为 auto-fixed(AOSP 锚点 android-17.0.0_r1 重锚),未满足 pass-tech-review 自动晋升条件,送 Task9 复核。 | 2026-07-03 13 Task6 revisiting-review: pass-light-edit;L1/L2 小修 1 处(frontmatter related_chapters 转义引号修正);outline 7/7 覆盖;无 L3/L4 回炉项。Task9 result 为 auto-fixed，未满足 pass-tech-review 自动晋升条件,送 Task9 复核。"
last_task6_review_log: logs/review/2026-07-03-13-review.md
task6_state: reviewed
task9_state: reviewed
drafted_date: 2026-05-24
related_chapters: ["1.7", "1.9", "16.6", "21.11"]
created_by: task2a-knowledge-gap
created_date: 2026-05-24
gap_source: 研究素材/官方文档/AOSP结构
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed
last_task9_at: 2026-07-03T13:28:31+08:00
last_task9_audit: 2026-07-07
task9_reviewed_date: 2026-07-03
task9_reviewed_by: openclaw-task9
task9_review_notes: "2026-06-17 Task9 deep-review: AUTO-FIX P1 1; replaced AOSP main anchors with android-16.0.0_r1 after android-17 platform tag was not present. 2026-07-03 Task2B main: re-anchored all AOSP references from android-16.0.0_r1 to android-17.0.0_r1 (tag verified available on googlesource); no Android 18/API 38 material used. | 2026-07-03 09 Task9 deep-review AUTO-FIX:旧设备 quicken 表格把 ART Service 版本段写到 Android 14-16;android-17.0.0_r1 仍包含 platform/art libartservice,已改为 Android 14-17。P0 0 / P1 1 / P2 0;回到 Task6 复审。 | 2026-07-03 13 Task9 deep-review pass-tech-review；无 P0/P1/P2；Task6 已通过且 queue 无 pending，自动晋升 finalized。"
last_task9_review_log: logs/deep-review/2026-07-03-13-deep-review.md
last_task9_autofix_at: 2026-07-03
task6_result: pass-light-edit
last_task2b_lite_at: 2026-06-30
task2b_lite_note: "2026-06-30 Task2B Lite: 修复 last_task6_review_log 字段被 title 污染的机械错误。"
reviewed_by: openclaw-task6
reviewed_date: 2026-07-03
last_task6_at: 2026-07-03T13:14:00+08:00
last_task6_audit: 2026-07-03
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-04
p0: 0
p1: 0
p2: 0
task9_p0_issues: 0
task9_p1_issues: 0
task9_p2_issues: 0
---
# 1.22 ART Verifier、Quickening 与 dexopt 过滤器的性能边界

看到 `speed-profile`，不能直接认定应用已经充分编译；看到 `verify`，也不能认定应用没有优化。compiler filter 描述某一次 dexopt 想达到的目标，落盘结果还会受 profile、DEX 规模、依赖关系、安装方式和设备策略影响。

排查安装慢、首次启动慢或 OTA 后应用变慢时，先分清三件事：

1. DEX 是否已经通过验证，验证结果能否复用。
2. 哪些方法已有 AOT 机器码，哪些方法仍要解释执行或等待 JIT。
3. 当前看到的是请求的 filter”，还是 ART 最终采用的 filter。

当前锚点为 Android 17 / API 37 / AOSP `android-17.0.0_r1`，同时保留 Android 8–16 的演进边界。

## 先建立一张执行地图

应用代码从安装到稳定运行，大致经过下面几层：

```text
APK / split APK / secondary DEX
        │
        ├── 可选 .dm：cloud profile、VDEX 验证元数据等
        │
        ├── bootclasspath、boot image、ClassLoaderContext
        │
        ▼
PackageManager 发起 dexopt
        │
        ▼
ART Service / artd 调用 dex2oat
        │
        ├── 验证与 DEX 提取
        ├── 按 filter 生成 AOT 代码
        └── 可选生成 app image
        ▼
VDEX / ODEX(OAT) / ART image
        │
        ▼
运行时：AOT + 解释器 + JIT
```

单个文件或过滤器无法独立证明启动已经达到最佳状态。例如：

- `verify` 可以让验证结果被复用，但不会为 Java/Kotlin 方法生成 AOT 机器码。
- `speed-profile` 只编译 profile 覆盖的方法；profile 缺失时，实际结果可以降为 `verify`。
- ODEX 存在，不代表启动路径上的关键方法一定被编译。
- VDEX 存在，也不代表依赖完全匹配；Android 17 可以保留验证/提取收益，同时放弃不再可信的编译和类解析结果。

## 验证器检查什么

ART 字节码验证器检查 DEX 是否满足运行时安全约束，包括类型一致性、寄存器使用、控制流、方法调用和字段访问是否合法。它判断字节码能否安全执行，不负责判断代码是否已经编译成机器码。

验证有两类性能价值：

- 第一次处理 DEX 时，提前发现非法字节码，避免把错误推迟到任意运行路径。
- 后续处理相同 DEX 时，复用 verifier dependencies 等元数据，减少重复验证工作。

因此，`verify` 仍会执行工作。在 Android 17 的 ART Service 定义中，它会完成验证与提取，但不编译方法，也不对配置文件中的 resolution / initialization 优化。

## VDEX、ODEX 和 ART 镜像各自负责什么

三类产物经常同时出现，但职责不同。

| 产物 | 主要内容与作用 | 不能据此推出什么 |
| --- | --- | --- |
| `.vdex` | DEX 校验信息、verifier dependencies；具体格式下也可能带 DEX section。Android 17 的 `dex2oat` 还能从 `.dm` 中读取 VDEX，用于 fast verification | 不能仅凭文件存在断言 AOT 代码可用，也不能断言 CLC 完全匹配 |
| `.odex` / OAT | AOT 机器码和 ART 运行所需的编译元数据；实际代码覆盖由最终 filter 和 profile 决定 | 不能仅凭文件大小或存在性断言关键启动路径已编译 |
| `.art` | 可选 app image，保存可复用的运行时对象状态，减少部分对象创建和类准备成本 | 并非每次 dexopt 都会生成；没有它也不表示 DEX 无法运行 |

Android 17 对输入 VDEX 的处理很具体：

1. `dex2oat` 可以从独立 VDEX 或 DexMetadata 归档文件打开输入。
2. 如果 VDEX 不含 DEX section，源码会核对 DEX 数量和 location checksum。
3. 验证器依赖解析成功后，进入快速验证。
4. 输入 VDEX 无法打开时，`dex2oat` 会告警并按无 VDEX 的路径继续；但文件已打开后若 DEX 数量或 checksum 不匹配，本次 `dex2oat` 会失败，不会把错误元数据当成可复用结果。

不要把所有应用产物都归到 `/data/misc/apexdata/com.android.art/dalvik-cache`。Android 17 的默认位置按对象类型拆开：

| 对象 | 常见位置 |
| --- | --- |
| 安装到 data 分区的主 DEX | `/{data,mnt/expand/*}/app/*/*/oat/<isa>/{base,split_*}.{art,odex,vdex}` |
| 只读文件系统中的包 | `/data/dalvik-cache/<isa>/<encoded-dex-path>.{art,dex,vdex}` |
| secondary dex | 应用数据目录下对应 `oat/<isa>/*.{art,odex,vdex}` |
| primary dex 的当前/ reference profile | `/data/misc/profiles/{cur/<user-id>,ref}/<package-name>/*.prof` |
| on-device boot image | `/data/misc/apexdata/com.android.art/dalvik-cache/boot*.{art,oat,vdex}` |

其中只读包的 OAT 文件因历史原因可能使用 `.dex` 扩展名。排障时应先确认对象是 boot classpath、安装包、只读系统包还是次级 DEX，再去对应目录找证据。

## Android 17 当前支持的应用侧 filter

AOSP `android-17.0.0_r1` 的 ART Service 说明和 shell help 对应用 dexopt 公开三种 filter：

| Filter | Android 17 的语义 | 典型取舍 |
| --- | --- | --- |
| `verify` | verification + extraction；不编译方法，不对配置文件中的 resolution / initialization | dexopt 快、产物小；运行期更多依赖解释器和 JIT |
| `speed-profile` | 验证并提取；编译 profile 中的方法；处理 profile 中类的解析/ initialization | 在安装/后台成本、存储和运行性能之间取平衡 |
| `speed` | 验证并提取；AOT 编译所有可编译方法；不按 profile 做 class resolution / initialization | 编译时间和空间成本最高，运行期机器码覆盖最广 |

`speed` 不是任何场景下都更好。它可能增加安装或维护耗时、占用更多存储，而且不能修复主线程 I/O、Binder 等待、数据库迁移或错误的启动架构。

`speed-profile` 也不承诺一定按该级别编译。Android 17 的 `pm compile` 帮助明确说明：没有可用 profile 时，请求 `speed-profile` 可能实际得到 `verify`。因此 dump 中的最终状态比命令行参数更可信。

底层 `CompilerFilter::Filter` 还保留 `space*`、`everything*` 等枚举，`compiler_filter.cc` 也能解析这些名称；但 ART Service 的应用侧命令只把 `speed`、`speed-profile`、`verify` 列为可用选项。写应用性能文档时，不应把内部解析能力等同于受支持的常规运维接口。

## `quicken`：历史功能仍有兼容入口

官方文档把 `quicken` 限定在 Android 11 及以下。它在完成验证后改写部分 DEX 指令，使解释器更快地访问已解析的字段或方法。它优化的是解释执行路径，不会因此产生 ARM64 或 x86 方法机器码。

版本边界如下：

| 版本 | `quicken` 应如何理解 |
| --- | --- |
| Android 8–11 | 受官方文档支持的 filter；输出服务于解释器快速路径 |
| Android 12–13 | 不再属于当前官方 filter 口径，排障应以 `verify`、`speed-profile`、`speed` 为主 |
| Android 14–17 | ART Service 的应用侧接口只公开三种当前 filter |
| Android 17 源码兼容行为 | `kQuicken` 枚举已不存在，但解析到字符串 `quicken` 时会打印废弃警告，并映射成 `kVerify` |

Android 17 为兼容旧配置保留了 `quicken` 名称入口，对应的执行语义已经变为 `verify`。厂商 ROM 还可能自行修改实现，所以看到日志中的旧字符串时，应同时记录 Android 版本、ART Mainline 版本和最终转储状态。

## Android 17 的 dexopt 场景

Android 14 起，应用的设备端 dexopt 产物由 ART Service 管理。PackageManager 仍负责安装流程，并在安装时调用 `dexoptPackage`；安装 dexopt 不是 ART Service 自行发起的 batch operation，因此不会触发 `BatchDexoptStartCallback`。

Android 17 默认场景如下。

| 场景 | reason | 默认行为 | 容易误判的地方 |
| --- | --- | --- | --- |
| 首次开机 | `first-boot` | 对应用主 DEX 以 `verify` 为目标 | 系统镜像里的包可能已被 dexpreopt 成 `speed-profile` 或 `speed`，不能说所有包都是 `verify` |
| OTA 后首次开机 | `boot-after-ota` | primary dex 以 `verify` 为目标，尽量缩短开机阻塞 | Pre-reboot Dexopt 已完成的包可能保持 `speed-profile` |
| Mainline 更新后首次开机 | `boot-after-mainline-update` | 重点处理 SystemUI 和 Launcher；Launcher 使用 `speed-profile`，SystemUI 由 `dalvik.vm.systemuicompilerfilter` 决定 | 不会对所有应用重新执行 AOT |
| 应用安装 | `install`、`install-fast`、`install-bulk*` | DM 含 cloud profile 时用 `speed-profile`，否则用 `verify` | fast scenario 或 incremental install 可以跳过安装期 dexopt |
| 日常后台优化 | `bg-dexopt` / `inactive` | 每日空闲且充电时运行；对主 DEX 和次级 DEX 做配置文件引导的 dexopt | 条件消失时任务会被取消；稍后重试不代表失败 |
| 更新应用前优化 | `ab-ota` | OTA/Mainline / Mainline 时，在空闲充电窗口对新依赖环境做重启前 Dexopt，目标为 `speed-profile` | 用户提前重启时可能未完成，剩余包先以 `verify` 运行 |
| 命令行 | `cmdline` | 默认 `verify`，可显式指定支持的 filter | 指定 `speed-profile` 不保证 profile 可用 |

标准属性默认值是：

```text
pm.dexopt.first-boot=verify
pm.dexopt.boot-after-ota=verify
pm.dexopt.boot-after-mainline-update=verify
pm.dexopt.bg-dexopt=speed-profile
pm.dexopt.inactive=verify
pm.dexopt.cmdline=verify
pm.dexopt.shared=speed
```

`pm.dexopt.shared=speed` 不会让所有共享应用无条件使用 `speed`。当一个包被其他应用加载且本轮请求 profile-guided 编译时，ART 出于隐私边界不能使用它的本地 profile；系统会先尝试 cloud profile，没有 cloud profile 才使用 `shared` filter 兜底。若本轮没有请求配置文件引导编译，这个属性不生效。

厂商还可以通过属性和 ART Service API 改写包列表、filter、优先级与并发数，所以这组值只能作为 AOSP 默认值，不能代替设备实测。

## 安装时，.dm 到底改变了什么

Android 17 的默认安装策略可以压缩成两条：

- `.dm` 中有可用 cloud profile：目标通常是 `speed-profile`。
- 没有可用 profile：目标通常是 `verify`。

`.dm` 是容器，文件存在不能证明配置文件已经生效。它可以携带 profile，也可以携带 VDEX 验证元数据，还可能为空或因校验、版本等问题未被采用。OAT 头中的 `install-dm` 后缀仅表示安装 dexopt 时把 DM 传给了 `dex2oat`；Android 17 的 ART Service 说明明确指出，这个后缀不保证 DM 内任何内容实际生效。

还要注意两个跳过路径：

- 应用商店使用 `INSTALL_SCENARIO_FAST`，对应 `install-fast`，默认可跳过 dexopt。
- incremental install 可以跳过安装期 dexopt。

判断 cloud profile 是否生效时，应依次检查安装输入、dexopt 结果 → profile / filter 状态，不能只检查 APK 旁边是否有 `.dm`。

## 依赖不匹配时仍可复用部分产物

dexopt 的依赖除原始 DEX 外，还包括 bootclasspath、boot image 和 ClassLoaderContext（CLC）。CLC 由 shared libraries、同一应用的其他分包等共同决定。

Android 17 的 ART Service 把复用边界分成两层：

- 编译结果以及 class resolution / initialization 结果要求 dexopt 时依赖与运行时依赖完全匹配。
- 验证与提取结果在依赖不匹配时仍可能复用，产物按 `verify` 状态使用。

CLC 不匹配后，依赖敏感的 AOT 与类解析结果不再可信，但验证/提取收益仍可保留。`pm art dump` 里可能显示特殊原因 `vdex`；这是转储层表达该状态的标记，不会传给 `dex2oat`，也不会作为真实编译原因写进 OAT 头。

### `<uses-library>` 为什么经常触发 CLC 问题

dexpreopt 在构建机上计算 CLC，运行时再根据清单、共享库 XML、shared library XML、split 和实际 class loader 关系计算一次。两边不一致时，预编译产物不能按原级别复用。

排查顺序应是：

1. 核对 Manifest 的 `<uses-library>` 声明。
2. 核对 `Android.bp` 或 `Android.mk` 中的构建侧依赖。
3. 核对设备上的 shared library 配置与实际加载顺序。
4. 查看 `pm art dump` 是否退到 `vdex`/`verify`，再结合日志确认 mismatch。
5. 修复依赖模型后重新构建或 dexopt，不要用强制 `speed` 掩盖 CLC 错误。

可先采集日志：

```bash
adb logcat -b all -d |
  grep -E 'ClassLoaderContext|class loader context|dex2oat|Running dexopt'
```

日志文本会随版本和厂商修改变化，正则只用于缩小范围，不能当成固定接口。

## 安装、首启和后台优化如何接力

| 时点 | 常见状态 | 运行性能含义 |
| --- | --- | --- |
| 安装完成 | 有 cloud profile 时可能是 `speed-profile`；否则常见 `verify` | `verify` 已完成安全验证，但关键方法可能仍无 AOT 代码 |
| 第一次运行 | AOT 命中方法直接执行；其余方法解释执行，热点进入 JIT | 首启可能产生类加载、page fault、解释器和 JIT 热身成本 |
| 多次运行后 | current profile 逐步积累真实用户热点 | profile 只是输入，尚不代表参考配置文件已用于 dexopt |
| 空闲充电 | background dexopt 合并可用 profile，以 `speed-profile` 重新处理 | 后续启动可能改善，但任务可以被取消或因策略跳过 |
| OTA / Mainline 前 | Pre-reboot Dexopt 尝试针对新依赖生成产物 | 未完成的包重启后仍能以 `verify` + JIT 正常运行 |

“安装很快但第一次打开慢”和“升级后第一次打开变慢”常由此产生。这些现象可能源于系统主动把 AOT 成本从交互路径移到后台。需要修复的对象包括不合理的关键启动路径、profile 覆盖、长期无法完成的后台任务或错误的依赖配置。

## 大体积 DEX 的特殊降级

Android 17 的 `dex2oat.cc` 会累加输入 DEX 头中的 `file_size_`，与传入的 very-large threshold 比较。命中阈值的非 boot image：

- 禁用应用镜像；
- 如果当前 filter 高于 `verify`，把本轮编译降为 `verify`；
- 输出 `Very large app, downgrading to verify.` 日志。

阈值不是这段代码里固定的“某个 APK 大小”。`dex2oat` 的字段默认是最大值，实际阈值由调用方参数和产品配置决定；比较对象还是 DEX 累计大小，不是 APK 下载体积。文档或排障脚本不应硬编码一个通用 MB 数。

因此，上层即使请求了 `speed-profile` 或 `speed`，最终也可能只有 `verify`。遇到超大、多 DEX 应用时，要同时检查请求参数、`dex2oat` 日志和最终转储。

## Android 17 的推荐取证命令

### 1. 保存系统策略

下面的命令保存 dexopt 与 JIT 相关属性，作为设备策略背景：

```bash
adb shell getprop |
  grep -E 'pm.dexopt|dalvik.vm.*compilerfilter|dalvik.vm.*dex2oat|dalvik.vm.usejit'
```

属性反映默认策略，不代表某个包最终使用的过滤器。

### 2. 查看包级最终状态

下面的 ART Service 命令读取指定包当前的 dexopt 产物与原因：

```bash
adb shell pm art dump com.example.app
```

Android 14–17 优先使用 `pm art dump`。重点查看主/次级 DEX、compiler filter、compilation reason、产物是否 up-to-date，以及是否出现 `vdex` 状态。`dumpsys package dexopt` 仍可用于兼容旧版本或对照，但不应作为现代 ART Service 的首选入口。

### 3. 建立未编译基线

下面的重置命令只适合受控实验，用来建立以 `verify` 为主的对照状态：

```bash
adb shell pm compile --reset com.example.app
```

Android 17 的 `--reset` 会清理本地当前/ reference profiles；对主 DEX，当前实现等同于以 `verify` 做 dexopt。外部 profile（如 cloud / embedded profile）会保留，但本次重置不使用；secondary dex 的产物会被删除且不在本轮重建。它适合实验室建立对照基线，不适合在线上随意执行。

### 4. 验证 profile-guided 编译

下面先强制请求 `speed-profile`，再读取最终状态验证请求是否被满足：

```bash
adb shell pm compile -m speed-profile -f -v com.example.app
adb shell pm art dump com.example.app
```

`-f` 表示即使现有产物“不差于”目标也强制执行。命令成功不代表最终一定是 `speed-profile`；没有可用 profile 时仍可能得到 `verify`，所以必须再次 dump。

如需建立“尽可能全面 AOT”的实验对照，可执行：

```bash
adb shell pm compile -m speed -f -v com.example.app
```

这个结果只用于定位 AOT 覆盖是否影响性能，不应直接变成产品默认策略。

### 5. 手动运行真实后台 dexopt 流程

下面的命令立即触发并等待 ART Service 的后台 dexopt job，适合实验室复现系统任务：

```bash
adb shell pm bg-dexopt-job
```

不带参数时，Android 17 会立即启动并等待一个真实的后台 background dexopt job。它仍按真实任务的包选择、并发设置、低存储降级和清理逻辑执行，但不会等待设备自然进入空闲充电状态。可在另一个终端取消：

```bash
adb shell pm bg-dexopt-job --cancel
```

如果只想对单个包模拟 `bg-dexopt` reason，应使用：

```bash
adb shell pm compile -r bg-dexopt -f -v com.example.app
```

把包名直接传给 `pm bg-dexopt-job` 的旧用法在 Android 17 已被标记为弃用。

## 三类慢问题怎么落证据

### 安装慢

先在 Perfetto 中拆开下载/文件复制、APK 签名校验、包扫描、native library、DM 处理和 dexopt。只有看到 `artd`/`dex2oat` 占据安装关键路径，才能把主要责任放到 ART。

继续核对：

- reason 是 `install`、`install-fast` 还是 bulk 变体；
- 目标过滤器和最终 filter 是否一致；
- DM 是否提供了可用 profile 或 VDEX；
- 是否命中 very-large 降级；
- dex2oat 的优先级与并发是否符合交互安装场景。

若最终只是 `verify`，就不要把耗时描述成“完整 AOT 编译”；验证、提取、I/O 或其他 PackageManager 阶段更值得检查。

### 首次启动慢

把 `pm art dump` 与启动跟踪放在一起看：

- `verify` + 大量解释器/JIT 活动：可能是 profile 未到达或尚未后台编译。
- `speed-profile` + 启动关键方法未命中：检查 profile 覆盖，不能只看 filter 名称。
- `speed-profile` / `speed` + 主线程仍被 I/O、锁、Binder 或数据库占满：瓶颈不在 compiler filter。
- 状态为 `vdex`：检查依赖变化和 CLC，AOT 代码可能没有被采用。

应至少对比重置后、profile-guided 编译后和稳定运行后的冷启动数据；不要把第二次启动的文件缓存收益误算成 AOT 收益。

### OTA 或 Mainline 更新后变慢

Android 17 先尝试重启前 Dexopt。若用户很快重启、设备没有足够空闲充电时间或任务失败，部分应用会先退到 `verify`，之后依靠 JIT 和后台 dexopt 恢复。

排查时关注：

- `ab-ota` 是否执行并完成；
- 更新是否改变 bootclasspath、boot image 或 CLC；
- dump 是否出现 `vdex`/`verify`；
- background dexopt 是否长期被取消；
- SystemUI / Launcher 是否符合其单独策略。

“更新后慢”不能一概归因于旧 ODEX 被删除。Android 17 会尽量复用仍可信的验证信息，并只放弃依赖不匹配的优化层。

## 版本演进速查

| 版本段 | 主线判断 |
| --- | --- |
| Android 8–11 | `verify`、`quicken`、`speed-profile`、`speed` 都是官方文档中的 filter；`quicken` 服务解释器 |
| Android 12–13 | `quicken` 退出当前官方口径；应用侧排障以 `verify`、`speed-profile`、`speed` 为主 |
| Android 14–16 | ART Service 接管应用 dexopt 产物管理；命令和场景逐步迁移到 `pm art` / `pm compile` |
| Android 17 / API 37 | 当前锚点；ART Service 命令行公开三种 filter；旧 `quicken` 字符串仅兼容映射到 `verify`；Pre-reboot Dexopt 已进入 OTA/Mainline 主流程 |

相关机制可继续阅读：

- 1.7：ART 解释器、JIT、AOT 与 profile 的完整管线。
- 1.9：PackageManager 安装 session 与 dexopt 调用位置。
- 16.6：Cloud Profile 的生成、传递与覆盖边界。
- 21.11：DexMetadata、DM / SDM 和安装后编译验证。

## 参考资料

- [Android 官方文档：Configure ART](https://source.android.com/docs/core/runtime/configure)
- [Android 官方文档：ART Service configuration](https://source.android.com/docs/core/runtime/configure/art-service)
- [Android 官方文档：Dexpreopt 与 ClassLoaderContext](https://source.android.com/docs/core/runtime/art-class-loader-context)
- [Android 官方文档：JIT compiler](https://source.android.com/docs/core/runtime/jit-compiler)
- [AOSP android-17.0.0_r1：`compiler_filter.h`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/libartbase/base/compiler_filter.h)
- [AOSP android-17.0.0_r1：`compiler_filter.cc`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/libartbase/base/compiler_filter.cc)
- [AOSP android-17.0.0_r1：ART Service README](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/libartservice/service/README.md)
- [AOSP android-17.0.0_r1：`ArtShellCommand.java`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ArtShellCommand.java)
- [AOSP android-17.0.0_r1：`ReasonMapping.java`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ReasonMapping.java)
- [AOSP android-17.0.0_r1：`dex2oat.cc`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/dex2oat/dex2oat.cc)
