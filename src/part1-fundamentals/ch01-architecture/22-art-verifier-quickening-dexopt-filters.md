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
task6_state: reviewed
task9_state: reviewed
related_chapters: ["1.7", "1.9", "16.6", "21.10"]
task2b_state: fixed
---
# 1.22 ART Verifier、Quickening 与 dexopt 过滤器的性能边界

看到 `speed-profile`，不能直接认定应用已经充分编译；看到 `verify`，也不能认定应用完全没有优化。编译过滤器（compiler filter，下文简称 filter）描述某一次 `dexopt` 想达到的目标。最终写入磁盘的结果还会受到性能配置文件（profile）、DEX 规模、依赖关系、安装方式和设备策略影响；profile 记录需要优先优化的方法和类。

排查安装慢、首次启动慢或 OTA 后应用变慢时，先分清三件事：

1. DEX 是否已经通过验证，验证结果能否复用。
2. 哪些方法已有 AOT（预先编译）机器码，哪些方法仍要解释执行或等待 JIT（运行时即时编译）。
3. 当前看到的是请求使用的 filter，还是 ART 最终采用的 filter。

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

split APK 是按功能或设备配置拆分的 APK，次级 DEX 则是应用运行时另外加载的 DEX。单个产物文件或一种 filter，都不足以独立证明启动已经达到最佳状态。例如：

- `verify` 可以让验证结果被复用，但不会为 Java/Kotlin 方法生成 AOT 机器码。
- `speed-profile` 只编译 profile 覆盖的方法；没有可用 profile 时，实际结果可以降为 `verify`。
- ODEX 存在，不代表启动路径上的关键方法一定被编译。
- VDEX 存在，也不代表依赖完全匹配；Android 17 可以保留验证/提取收益，同时放弃不再可信的编译和类解析结果。

## 验证器检查什么

ART 字节码验证器（bytecode verifier）检查 DEX 是否满足运行时安全约束，包括类型一致性、寄存器使用、控制流、方法调用和字段访问是否合法。它判断字节码能否安全执行，不判断代码是否已经编译成机器码。

验证有两类性能价值：

- 第一次处理 DEX 时，提前发现非法字节码，避免把错误推迟到任意运行路径。
- 后续处理相同 DEX 时，复用验证器依赖信息（verifier dependencies）等元数据，减少重复验证工作。

因此，`verify` 仍会执行实际工作。在 Android 17 的 ART Service 定义中，它会完成验证与 DEX 提取，但不编译方法，也不会根据 profile 提前完成类解析（resolution）或类初始化（initialization）。

## VDEX、ODEX 和 ART image 各自负责什么

三类产物经常同时出现，但职责不同。

| 产物 | 主要内容与作用 | 不能据此推出什么 |
| --- | --- | --- |
| `.vdex` | DEX 校验信息和验证器依赖信息；某些格式也会带 DEX 数据区。Android 17 的 `dex2oat` 还能从 `.dm` 中读取 VDEX，用于快速验证 | 不能仅凭文件存在断言 AOT 代码可用，也不能断言 CLC 完全匹配 |
| `.odex` / OAT | AOT 机器码和 ART 运行所需的编译元数据；实际代码覆盖范围由最终 filter 和 profile 决定 | 不能仅凭文件大小或存在性断言关键启动路径已编译 |
| `.art` | 可选的应用镜像，保存可复用的运行时对象状态，减少部分对象创建和类准备成本 | 并非每次 `dexopt` 都会生成；没有它也不表示 DEX 无法运行 |

Android 17 对输入 VDEX 的处理很具体：

1. `dex2oat` 可以从独立 VDEX 或 DexMetadata 归档文件中打开输入。
2. 如果 VDEX 不含 DEX 数据区，源码会核对 DEX 数量和位置校验和（location checksum）。
3. 验证器依赖信息解析成功后，进入快速验证。
4. 输入 VDEX 无法打开时，`dex2oat` 会告警并按无 VDEX 的路径继续；但文件已打开后若 DEX 数量或 checksum 不匹配，本次 `dex2oat` 会失败，不会把错误元数据当成可复用结果。

不要把所有应用产物都归到 `/data/misc/apexdata/com.android.art/dalvik-cache`。Android 17 的默认位置按对象类型拆开：

| 对象 | 常见位置 |
| --- | --- |
| 安装到数据分区的主 DEX（primary dex） | `/{data,mnt/expand/*}/app/*/*/oat/<isa>/{base,split_*}.{art,odex,vdex}` |
| 只读文件系统中的包 | `/data/dalvik-cache/<isa>/<encoded-dex-path>.{art,dex,vdex}` |
| 次级 DEX | 应用数据目录下对应的 `oat/<isa>/*.{art,odex,vdex}` |
| 主 DEX 的当前 / 参考 profile | `/data/misc/profiles/{cur/<user-id>,ref}/<package-name>/*.prof` |
| 设备端启动镜像 | `/data/misc/apexdata/com.android.art/dalvik-cache/boot*.{art,oat,vdex}` |

当前 profile（current profile）记录设备上逐步收集的热点，参考 profile（reference profile）则供后续编译使用。只读包的 OAT 文件因历史原因可能使用 `.dex` 扩展名。排障时应先确认对象属于启动类路径、普通安装包、只读系统包还是次级 DEX，再到对应目录查找证据。

## Android 17 当前支持哪些应用侧 filter

AOSP `android-17.0.0_r1` 的 ART Service README 和命令帮助只对应用 `dexopt` 公开三种 filter：

| Filter | Android 17 中的含义 | 典型取舍 |
| --- | --- | --- |
| `verify` | 验证并提取 DEX；不编译方法，也不根据 profile 提前解析或初始化类 | `dexopt` 快、产物小；运行期更多依赖解释器和 JIT |
| `speed-profile` | 验证并提取 DEX；编译 profile 中的方法，并处理 profile 中类的解析与初始化 | 在安装或后台处理成本、存储占用和运行性能之间取平衡 |
| `speed` | 验证并提取 DEX；AOT 编译所有可编译方法，不根据 profile 提前解析或初始化类 | 编译时间和空间成本最高，运行期机器码覆盖最广 |

`speed` 不是任何场景下都更好。它可能增加安装或维护耗时、占用更多存储，而且不能修复主线程 I/O、Binder 等待、数据库迁移或错误的启动架构。

`speed-profile` 也不承诺一定按该级别编译。Android 17 的 `pm compile` 帮助明确说明：没有可用 profile 时，请求 `speed-profile` 可能实际得到 `verify`。因此，`pm art dump` 显示的最终状态比命令行参数更可信。

底层 `CompilerFilter::Filter` 还保留 `space*`、`everything*` 等枚举，`compiler_filter.cc` 也能解析这些名称；但 ART Service 的应用侧命令只把 `speed`、`speed-profile`、`verify` 列为可用选项。写应用性能文档时，不应把内部解析能力等同于受支持的常规运维接口。

## `quicken`：历史功能仍有兼容入口

官方文档把 `quicken` 限定在 Android 11 及以下。它在完成验证后改写部分 DEX 指令，使解释器更快地访问已解析的字段或方法。它优化的是解释执行路径，不会因此产生 ARM64 或 x86 方法机器码。

版本边界如下：

| 版本 | `quicken` 应如何理解 |
| --- | --- |
| Android 8–11 | 受官方文档支持的 filter；输出服务于解释器快速路径 |
| Android 12–13 | 不再属于当前官方 filter 范围，排障应以 `verify`、`speed-profile`、`speed` 为主 |
| Android 14–17 | ART Service 的应用侧接口只公开上述三种 filter |
| Android 17 源码兼容行为 | `kQuicken` 枚举已不存在，但解析到字符串 `quicken` 时会打印“已废弃”警告，并映射成 `kVerify` |

Android 17 为兼容旧配置保留了 `quicken` 名称入口，对应的执行含义已经变为 `verify`。厂商 ROM 还可能修改实现，所以看到日志中的旧字符串时，应同时记录 Android 版本、ART Mainline 版本和 `pm art dump` 的最终状态。

## Android 17 的 dexopt 场景

Android 14 起，应用在设备端生成的 `dexopt` 产物由 ART Service 管理。PackageManager 仍负责安装流程，并在安装时调用 `dexoptPackage`；安装期 `dexopt` 不是 ART Service 自行发起的批处理任务，因此不会触发 `BatchDexoptStartCallback`。

Android 17 默认场景如下。

| 场景 | 原因标识 | 默认行为 | 容易误判的地方 |
| --- | --- | --- | --- |
| 首次开机 | `first-boot` | 对应用主 DEX 以 `verify` 为目标 | 系统镜像里的包可能已通过 dexpreopt 生成 `speed-profile` 或 `speed` 产物，不能说所有包都是 `verify` |
| OTA 后首次开机 | `boot-after-ota` | 主 DEX 以 `verify` 为目标，尽量缩短开机阻塞 | 已完成重启前 Dexopt（Pre-reboot Dexopt）的包可能保持 `speed-profile` |
| Mainline 更新后首次开机 | `boot-after-mainline-update` | 重点处理 SystemUI 和桌面启动器；桌面启动器使用 `speed-profile`，SystemUI 由 `dalvik.vm.systemuicompilerfilter` 决定 | 不会对所有应用重新执行 AOT |
| 应用安装 | `install`、`install-fast`、`install-bulk*` | DM 含 Cloud Profile 时用 `speed-profile`，否则用 `verify` | 快速安装场景或增量安装可以跳过安装期 `dexopt` |
| 日常后台优化 | `bg-dexopt` / `inactive` | 每日空闲且充电时运行；对主 DEX 和次级 DEX 执行 profile 引导的 `dexopt` | 条件消失时任务会被取消；稍后重试不代表失败 |
| 更新应用前优化 | `ab-ota` | OTA 或 Mainline 更新时，在空闲充电窗口针对新依赖环境执行重启前 Dexopt，目标为 `speed-profile` | 用户提前重启时可能尚未完成，剩余包先以 `verify` 运行 |
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

`pm.dexopt.shared=speed` 不会让所有共享应用无条件使用 `speed`。当一个包被其他应用加载，并且本轮请求 profile 引导编译时，ART 出于隐私限制不能使用它的本地 profile；系统会先尝试 Cloud Profile，没有可用 Cloud Profile 时才把 `shared` filter 作为后备。若本轮没有请求 profile 引导编译，这个属性不生效。

厂商还可以通过属性和 ART Service API 调整包列表、filter、优先级与并发数，所以这组值只能作为 AOSP 默认值，不能代替设备实测。

## 安装时，`.dm` 到底改变了什么

Android 17 的默认安装策略可以概括为两条：

- `.dm` 中有可用 Cloud Profile：目标通常是 `speed-profile`。
- 没有可用 profile：目标通常是 `verify`。

`.dm` 是 Dex Metadata（DEX 元数据）容器，文件存在不能证明 profile 已经生效。它可以携带 profile，也可以携带 VDEX 验证元数据，还可能为空，或因校验、版本等问题未被采用。OAT 文件头中的 `install-dm` 后缀只表示安装期 `dexopt` 把 DM 传给了 `dex2oat`；Android 17 的 ART Service README 明确指出，这个后缀不保证 DM 内的任何内容实际生效。

还要注意两个跳过路径：

- 应用商店使用 `INSTALL_SCENARIO_FAST`，对应 `install-fast`，默认可跳过 dexopt。
- 增量安装（incremental install）可以跳过安装期 `dexopt`。

判断 Cloud Profile 是否生效时，应依次检查安装输入、`dexopt` 执行结果，以及最终的 profile 和 filter 状态，不能只检查 APK 旁边是否有 `.dm`。

## 依赖不匹配时仍可复用部分产物

`dexopt` 的依赖除原始 DEX 外，还包括启动类路径（boot classpath）、启动镜像（boot image）和类加载器上下文（ClassLoaderContext，CLC）。CLC 描述类加载器所看到的依赖及其顺序，由共享库、同一应用的其他 split APK 等共同决定。

Android 17 的 ART Service 把复用边界分成两层：

- 编译结果以及类解析、类初始化结果，要求 `dexopt` 时的依赖与运行时依赖完全匹配。
- 验证与提取结果在依赖不匹配时仍可能复用，产物按 `verify` 状态使用。

CLC 不匹配后，依赖敏感的 AOT 与类解析结果不再可信，但验证和提取结果仍可能保留。`pm art dump` 里可能显示特殊原因标识 `vdex`；它只用于在命令输出中表达这种状态，不会传给 `dex2oat`，也不会作为实际编译原因写进 OAT 文件头。

### `<uses-library>` 为什么经常触发 CLC 问题

dexpreopt 在构建机上计算 CLC，运行时再根据应用清单、共享库 XML、split APK 和实际类加载器关系计算一次。两边不一致时，预编译产物不能按原级别复用。

排查顺序应是：

1. 核对应用清单中的 `<uses-library>` 声明。
2. 核对 `Android.bp` 或 `Android.mk` 中的构建侧依赖。
3. 核对设备上的共享库配置与实际加载顺序。
4. 查看 `pm art dump` 的状态是否变成 `vdex` 或 `verify`，再结合日志确认依赖不匹配。
5. 修复依赖模型后重新构建或执行 `dexopt`，不要用强制 `speed` 掩盖 CLC 错误。

可先采集日志：

```bash
adb logcat -b all -d |
  grep -E 'ClassLoaderContext|class loader context|dex2oat|Running dexopt'
```

日志文本会随版本和厂商修改变化，正则只用于缩小范围，不能当成固定接口。

## 安装、首启和后台优化如何衔接

| 时点 | 常见状态 | 运行性能含义 |
| --- | --- | --- |
| 安装完成 | 有 Cloud Profile 时可能是 `speed-profile`；否则常见 `verify` | `verify` 已完成安全验证，但关键方法可能仍无 AOT 代码 |
| 第一次运行 | 已有 AOT 代码的方法直接执行；其余方法解释执行，热点方法进入 JIT | 首启可能产生类加载、缺页（page fault）、解释器执行和 JIT 预热成本 |
| 多次运行后 | 当前 profile 逐步积累真实用户热点 | profile 只是编译输入，尚不代表参考 profile 已用于 `dexopt` |
| 空闲充电 | 后台 `dexopt` 合并可用 profile，以 `speed-profile` 重新处理 | 后续启动可能改善，但任务可以被取消或因策略跳过 |
| OTA / Mainline 更新前 | 重启前 Dexopt 尝试针对新依赖生成产物 | 未完成的包重启后仍能以 `verify` 配合 JIT 正常运行 |

“安装很快但第一次打开慢”和“升级后第一次打开变慢”常由此产生。这些现象可能源于系统主动把 AOT 成本从交互路径移到后台。需要修复的对象包括不合理的关键启动路径、profile 覆盖、长期无法完成的后台任务或错误的依赖配置。

## 大体积 DEX 的特殊降级

Android 17 的 `dex2oat.cc` 会累加输入 DEX 文件头中的 `file_size_`，再与调用方传入的超大 DEX 阈值（very-large threshold）比较。对命中阈值、且本次目标不是启动镜像的任务，系统会：

- 禁用应用镜像；
- 如果当前 filter 高于 `verify`，把本轮编译降为 `verify`；
- 输出 `Very large app, downgrading to verify.` 日志。

阈值不是这段代码里固定的“某个 APK 大小”。`dex2oat` 的字段默认是最大值，实际阈值由调用方参数和产品配置决定；比较对象还是 DEX 累计大小，不是 APK 下载体积。文档或排障脚本不应硬编码一个通用 MB 数。

因此，上层即使请求了 `speed-profile` 或 `speed`，最终也可能只有 `verify`。遇到超大、多 DEX 应用时，要同时检查请求参数、`dex2oat` 日志和 `pm art dump` 显示的最终状态。

## Android 17 的推荐取证命令

### 1. 保存系统策略

下面的命令保存 `dexopt` 与 JIT 相关属性，作为设备策略背景：

```bash
adb shell getprop |
  grep -E 'pm.dexopt|dalvik.vm.*compilerfilter|dalvik.vm.*dex2oat|dalvik.vm.usejit'
```

属性反映默认策略，不代表某个包最终使用的过滤器。

### 2. 查看包级最终状态

下面的 ART Service 命令读取指定包当前的 `dexopt` 产物与编译原因：

```bash
adb shell pm art dump com.example.app
```

Android 14–17 优先使用 `pm art dump`。重点查看主 DEX 与次级 DEX、compiler filter、compilation reason（编译原因）、产物是否为最新状态，以及是否出现 `vdex` 状态。`dumpsys package dexopt` 仍可用于兼容旧版本或交叉核对，但不应作为现代 ART Service 的首选入口。

### 3. 建立无 AOT 代码的基线

下面的重置命令只适合受控实验，用来建立以 `verify` 为主、没有应用方法 AOT 代码的对照状态：

```bash
adb shell pm compile --reset com.example.app
```

Android 17 的 `--reset` 会清理本地的当前 profile 和参考 profile；对主 DEX，当前实现等同于用 `verify` 执行 `dexopt`。外部 profile（例如 Cloud Profile 或应用内置 profile）会保留，但本次重置不会使用；次级 DEX 的产物会被删除，也不会在本轮重建。该命令适合实验室建立对照基线，不适合在线上随意执行。

### 4. 验证 profile 引导编译

以下命令强制请求 `speed-profile`，随后读取最终状态，验证请求是否被满足：

```bash
adb shell pm compile -m speed-profile -f -v com.example.app
adb shell pm art dump com.example.app
```

`-f` 表示即使现有产物“不差于”目标也强制执行。命令成功不代表最终一定是 `speed-profile`；没有可用 profile 时仍可能得到 `verify`，所以必须再次运行 `pm art dump` 查看结果。

如需建立“尽可能全面 AOT”的实验对照，可执行：

```bash
adb shell pm compile -m speed -f -v com.example.app
```

这个结果只用于定位 AOT 覆盖是否影响性能，不应直接变成产品默认策略。

### 5. 手动运行系统后台 dexopt 流程

下面的命令会立即触发并等待 ART Service 的后台 `dexopt` 任务，适合在实验室复现系统行为：

```bash
adb shell pm bg-dexopt-job
```

不带参数时，Android 17 会立即启动并等待一次系统后台 `dexopt` 任务。它仍按系统任务的包选择、并发设置、低存储降级和清理逻辑执行，但不会等待设备自然进入空闲充电状态。可以在另一个终端取消：

```bash
adb shell pm bg-dexopt-job --cancel
```

前一条命令用于触发任务，后一条用于取消正在运行的任务。

如果只想对单个包模拟 `bg-dexopt` 这一编译原因，应使用：

```bash
adb shell pm compile -r bg-dexopt -f -v com.example.app
```

把包名直接传给 `pm bg-dexopt-job` 的旧用法，在 Android 17 中已标记为废弃。

## 三类慢问题如何取证

### 安装慢

先在 Perfetto 中分别观察下载或文件复制、APK 签名校验、包扫描、原生库、DM 处理和 `dexopt`。只有看到 `artd` 或 `dex2oat` 占据安装关键路径，才能把主要耗时归到 ART。

继续核对：

- 编译原因是 `install`、`install-fast` 还是 `install-bulk*` 变体；
- 请求的 filter 和最终 filter 是否一致；
- DM 是否提供了可用 profile 或 VDEX；
- 是否因超大 DEX 阈值而降为 `verify`；
- `dex2oat` 的优先级与并发是否符合交互安装场景。

若最终只是 `verify`，就不要把耗时描述成“完整 AOT 编译”；验证、提取、I/O 或其他 PackageManager 阶段更值得检查。

### 首次启动慢

把 `pm art dump` 与启动系统轨迹放在一起看：

- `verify` 且有大量解释器或 JIT 活动：可能是 profile 尚未到达设备，或后台编译尚未完成。
- `speed-profile` 但启动关键方法未命中：检查 profile 覆盖，不能只看 filter 名称。
- `speed-profile` 或 `speed`，但主线程仍被 I/O、锁、Binder 或数据库占满：瓶颈不在 compiler filter。
- 状态为 `vdex`：检查依赖变化和 CLC，AOT 代码可能没有被采用。

应至少对比重置后、profile 引导编译后和稳定运行后的冷启动数据；不要把第二次启动的文件缓存收益误算成 AOT 收益。

### OTA 或 Mainline 更新后变慢

Android 17 会先尝试重启前 Dexopt。若用户很快重启、设备没有足够的空闲充电时间，或任务执行失败，部分应用会先降为 `verify`，之后依靠 JIT 和后台 `dexopt` 恢复性能。

排查时关注：

- `ab-ota` 是否执行并完成；
- 更新是否改变启动类路径、启动镜像或 CLC；
- `pm art dump` 是否出现 `vdex` 或 `verify`；
- 后台 `dexopt` 是否长期被取消；
- SystemUI 和桌面启动器是否符合各自的单独策略。

“更新后慢”不能一概归因于旧 ODEX 被删除。Android 17 会尽量复用仍可信的验证信息，并只放弃依赖不匹配的优化层。

## 版本演进速查

| 版本段 | 主线判断 |
| --- | --- |
| Android 8–11 | `verify`、`quicken`、`speed-profile`、`speed` 都是官方文档中的 filter；`quicken` 优化解释器执行路径 |
| Android 12–13 | `quicken` 退出当前官方口径；应用侧排障以 `verify`、`speed-profile`、`speed` 为主 |
| Android 14–16 | ART Service 接管应用 dexopt 产物管理；命令和场景逐步迁移到 `pm art` / `pm compile` |
| Android 17 / API 37 | 当前源码基准；ART Service 命令行公开三种 filter；旧 `quicken` 字符串仅兼容映射到 `verify`；重启前 Dexopt 已进入 OTA 和 Mainline 更新主流程 |

相关机制可继续阅读：

- 1.7：ART 解释器、JIT、AOT 与 profile 的完整流程。
- 1.9：PackageManager 安装会话与 `dexopt` 调用位置。
- 16.6：Cloud Profile 的生成、传递与覆盖边界。
- 21.10：DexMetadata、DM / SDM 和安装后编译验证。

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
