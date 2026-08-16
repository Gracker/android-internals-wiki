---
title: "云端 Profile、DM 文件与安装后编译优化"
chapter: "21.10"
section: "21.10"
status: finalized
applicable_versions: "Android 7 (API 24) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "current Android Developers Baseline/Startup/Cloud Profile and ProfileVerifier docs; current AOSP ART Service configuration; AOSP android-17.0.0_r1 framework DexMetadataHelper, ART Service DexMetadataHelper, Dexopter, PrimaryDexopter, PrimaryDexUtils and ArtShellCommand"
confidence: high
sources:
  - type: official
    path: "https://source.android.com/docs/core/runtime/configure"
  - type: official
    path: "https://source.android.com/docs/core/runtime/configure/art-service"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/overview"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile"
  - type: aosp
    path: "frameworks/base/core/java/android/content/pm/dex/DexMetadataHelper.java"
  - type: aosp
    path: "frameworks/native/cmds/installd/dexopt.cpp"
  - type: aosp
    path: "frameworks/base/core/java/android/content/pm/PackageManager.java"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/PrimaryDexopter.java"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/DexMetadataHelper.java"
  - type: clippings-structure
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings-structure
    path: "Clippings/Android 性能优化 - 原理：重新认识 APK 安装包.md"
  - type: clippings-structure
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
tags: [startup, art, baseline-profile, dexopt, cloud-profile]
related_chapters: ["1.7", "8.2", "21.4", "21.8"]
pipeline_stage: finalized
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---

# 云端 Profile、DM 文件与安装后编译优化

## Profile 在发布后如何生效

Baseline Profile 是由 App 或库维护的“常用类和方法”规则，Android Runtime（ART）可据此提前编译关键代码。它的生成、Gradle 构建接入和 Macrobenchmark（AndroidX 宏基准测试）验证见 [Baseline Profile 与 Startup Profile 实战](./04-baseline-profile-practice.md)。发布后还要继续追踪：安装来源交付了哪些 profile，Android 17 的 ART Service 怎样选择 profile 和 compiler filter（编译强度），以及 App 团队怎样判断一次启动变化是否来自编译状态。

先划清收益边界。Profile 可以减少解释器逐条执行代码、JIT（Just-In-Time，运行时即时编译）预热和部分 DEX（Android 字节码文件）读取开销，却不会缩短数据库迁移、网络等待、锁竞争或 SDK 同步初始化。一次冷启动同时包含这些成本，只看总耗时很容易误判。

## 云端 Profile 在启动优化里的位置

从 Android 7 起，ART 会在解释执行、JIT 和 AOT（Ahead-Of-Time，运行前预编译）产物之间选择。设备运行 App 时，本地 profile 逐渐记录常用代码；后台 dexopt（DEX 优化/编译流程）再按 profile 编译高频路径。Baseline Profile 和 Cloud Profile 都能在本机运行数据尚未积累充分时提供编译依据，但两者的生产者、可用时机和可控程度不同。

| Profile 类型 | 生产者 | 何时生效 | 主要作用 | App 团队能否直接控制 |
|---|---|---|---|---|
| Baseline Profile | App 或库的开发团队 | 随发布产物交付，安装期或后续 dexopt 使用 | 覆盖新安装、新升级后的核心路径 | 可以；规则、版本和回归测试都由发布方维护 |
| Cloud Profile | Google Play 根据已发布版本的真实用户样本聚合 | 样本达到条件并由 Play 交付之后 | 补充 Baseline Profile 未覆盖的高频路径 | 不能直接编辑；依赖 Play、版本规模和聚合周期 |
| 本地运行时 profile | 单台设备上的 ART/JIT | 用户运行 App 后逐步积累 | 指导该设备后续的 `speed-profile` 编译 | 只能通过稳定的代码路径间接影响 |
| Startup Profile | App 团队与构建工具 | 构建期由 D8/R8 消费 | 调整启动相关类和方法在 DEX 中的排列 | 可以；它不作为设备端 AOT profile 使用 |

Google 的 Baseline Profiles 文档给出两个重要边界：

- Cloud Profile 属于 PGO（Profile-Guided Optimization，按真实运行特征优化），需要 Android 9（API 28）或更高版本、足够的用户样本以及聚合时间；新版本发布后的数小时到数天内，不能假设它已经可用。
- Baseline Profile 随当前版本发布，可以覆盖 Day-0，也就是用户安装或升级这个版本后的首次使用阶段。Cloud Profile 无法及时替代它。

因此，Baseline/Cloud Profile 与 Startup Profile 要分开评估。前两者主要影响哪些方法被 AOT 编译；Startup Profile 由 D8/R8 在构建期使用，主要改变 DEX 布局，目标是减少启动阶段分散读取文件和触发内存缺页的成本。一次构建可以同时使用两类规则，但 A/B 实验（把条件相同的用户随机分组对比）需要明确改变的是编译状态、DEX 布局，还是两者一起改变。

## DM 文件与 ART 编译模式

`.dm` 是 Dex Metadata 容器，与某个 APK 一一对应。Android 17 framework 中的 `android.content.pm.dex.DexMetadataHelper` 把 `base.apk` 映射为同目录下的 `base.dm`；split APK（App Bundle 拆出的功能或配置 APK）也按各自文件名匹配，不能拿 base 的 `.dm` 替代 split 的 metadata。

需要避开三个常见误解：

1. `.dm` 不等同于 Cloud Profile。它是 ZIP 容器，可以带 profile，也可以带 VDEX（ART 使用的 DEX 校验相关数据）和配置；是否来自 Play、包含什么内容，要结合安装来源和文件内容判断。
2. `.dm` 不保证每次安装都存在。APK 内嵌 Baseline Profile、相邻的 `base.apk.prof` 和相邻的 `base.dm` 都可能成为 ART Service 的外部输入。
3. 文件存在不代表 profile 可用。文件名、二进制格式或 DEX checksum（用于确认 profile 对应同一份 DEX 的校验值）不匹配时，ART Service 会拒绝该 profile。

Android 17 源码为这些判断提供了直接证据：

- `PrimaryDexUtils.getExternalProfiles()` 同时返回 prebuilt profile（与 APK 相邻的 `<apk-name>.prof`）路径和 `.dm` profile 路径。
- ART Service 的 `com.android.server.art.DexMetadataHelper.getDexMetadataInfo()` 打开 `.dm`，读取可选的 `config.pb`，并按只含 profile、只含 VDEX、两者都有或都没有进行分类。
- `PrimaryDexopter.buildDmPath()` 按当前 base/split APK 构造 `.dm` 路径。
- `Dexopter` 只有在存在有效 profile 时才保留 profile-guided filter；profile 为空时，会把请求的 `speed-profile` 调整为 `verify`。

Android 17 framework 的安装流程会先检查每个 `.dm` 是否有同名 APK 与之配对。完成路径匹配后，`android.content.pm.dex.DexMetadataHelper.validateDexMetadataFile()` 只确认 `.dm` 能作为 ZIP 归档打开；它的注释仍提到校验 `manifest.json` 中的包名和版本号，但 `android-17.0.0_r1` 的方法体没有执行这项语义校验。ART 在消费 profile 时还会检查 profile 格式和 DEX 匹配关系，这几个阶段不能混为一谈。

`PackageManager.INSTALL_IGNORE_DEXOPT_PROFILE` 也能说明安装期与后续 dexopt 是两个时机：该安装标志会在安装时忽略 `.dm` 和 APK 内嵌 profile，并不报告无效安装 profile 的警告；以后由后台 dexopt 或 `pm compile` 发起的编译仍可使用 profile。

### Android 17 的执行链路

下面的路径图用于区分输入、调度者和编译执行者。Package Manager 负责安装流程，ART Service 负责制定本次 dexopt 参数，`artd` 是执行 ART 文件与编译操作的系统守护进程，`dex2oat` 则把 DEX 编译为设备可执行的 ART 产物。

```text
APK / split APK
  ├─ APK 内嵌 Baseline Profile
  ├─ 相邻的 <apk-name>.prof
  └─ 相邻的 <apk-stem>.dm
             │
Package Manager ──发起安装期 dexopt──► ART Service
                                           │ 选择 profile、reason、filter
                                           ▼
                                         artd
                                           │
                                           ▼
                                        dex2oat

运行时 JIT profile ──后台维护窗口──────────► ART Service
```

从 Android 14（API 34）起，App 的设备端 AOT 编译由 ART Service 管理。`installd/dexopt.cpp` 对理解 Android 13 及更早版本有历史价值，但已不是 Android 17 的主调度链路；核对 Android 17 行为时，应查看 `ArtManagerLocal`、`Dexopter`、`PrimaryDexopter`、`artd` 和 `dex2oat`。

### compiler filter 与 compilation reason

这两个字段回答不同问题。compiler filter 是编译器工作到什么程度，compilation reason 是这次工作为什么发生：

- compiler filter 表示“生成了何种编译产物”。
- compilation reason 表示“哪类事件触发了这次 dexopt”，例如安装、后台维护或 shell 命令。

| filter | Android 17 中的含义 | 代价与边界 |
|---|---|---|
| `verify` | 验证 DEX，不生成 AOT 机器码 | CPU、存储成本较低；启动路径更多依赖解释器与 JIT |
| `speed-profile` | 只 AOT 编译有效 profile 选中的方法 | 成本取决于 profile；没有有效 profile 时，实际 filter 会变成 `verify` |
| `speed` | 面向速度 AOT 编译全部方法 | 编译耗时和产物体积更高，不适合作为普通第三方 App 的默认对照目标 |

排查时必须同时记录 requested filter（请求的编译强度）和 actual filter（ART 最终采用的编译强度）。只看到命令参数 `-m speed-profile`，不能证明 profile 已经命中；Android 17 的 `Dexopter.java` 在找不到有效 profile 时会把它改为 `verify`。

## dex2oat、bg-dexopt-job 与空闲编译

`dex2oat` 是 ART 的 DEX 编译器，`bg-dexopt-job` 是系统安排的后台 DEX 优化任务。安装返回成功不代表以后不再编译：若安装期没有使用有效 profile，App 运行后仍可由 JIT 采集本地 profile；后台任务再把这些信息用于 `speed-profile` 编译。因此，同一 APK 的“安装后第一次打开”和“使用数日后的打开”可能处于不同编译状态。

ART Service 的标准默认值包括：

- `pm.dexopt.first-boot=verify`
- `pm.dexopt.boot-after-ota=verify`
- `pm.dexopt.boot-after-mainline-update=verify`
- `pm.dexopt.bg-dexopt=speed-profile`
- `pm.dexopt.inactive=verify`
- `pm.dexopt.cmdline=verify`
- `pm.dexopt.shared=speed`，作为共享代码无法使用本地 profile 时的备用 filter

共享代码的规则需要额外说明。某个包的代码被其他 App 通过 `<uses-library>` 共享库声明或动态加载方式使用时，ART Service 不能把该包基于单个用户行为生成的本地 profile 用于公共编译产物，以免泄露使用特征。系统会先尝试 Cloud Profile；缺失时才使用 `pm.dexopt.shared` 指定的 filter。

Android 14 及更高版本中，后台 dexopt 默认每天在设备空闲且充电时运行。设备退出 idle（无人操作的空闲状态），或温度达到 `THERMAL_STATUS_MODERATE` 阈值时，任务会立即取消。ART Service 没有旧 Package Manager 的 post-boot（开机后）dexopt job，因此不能把旧版本的开机后前台资源竞争直接套用到 Android 17。

普通 App 进程无权要求用户设备立即完成后台 dexopt。`pm.dexopt.disable_bg_dexopt` 和 `pm bg-dexopt-job --disable` 是系统开发者用于测试的入口，不能写进第三方 App 的线上优化方案。

### 查看包的 dexopt 状态

下面的命令用于 Android 14—17 测试设备，读取目标包当前的主 DEX 与 split DEX 编译状态。

```bash
adb shell pm art dump com.example.app
```

输出中要逐个 APK/ABI 查看 compiler filter、compilation reason 和 artifact（编译产物）状态。ABI 表示 CPU 指令集与二进制接口，例如 `arm64-v8a`。Android 13 及更早版本可用 `dumpsys package dexopt` 辅助排查；Android 17 的首选入口是 `pm art dump`。

下面的属性采集用于记录 ROM（设备厂商定制的系统软件）对标准策略的修改，仅适合测试环境。

```bash
adb shell getprop | grep -E 'pm\.dexopt|dex2oat'
```

这些值由系统镜像和 ART 模块决定。不同设备出现差异时，应把它们作为实验条件保存，不能据此要求线上 App 修改系统属性。

## Profile 命中率与冷启动收益评估

### 第一道检查：发布产物里有什么

下面的命令用于确认 APK 和 AAB 是否包含 Baseline Profile；它不判断规则覆盖率。APK 是安装包，AAB（Android App Bundle）是交给应用商店生成设备专用 APK 的发布包。

```bash
unzip -l app-release.apk | grep 'assets/dexopt/baseline.prof'
unzip -l app-release.aab | grep 'BUNDLE-METADATA/com.android.tools.build.profiles/baseline.prof'
```

APK 和 AAB 的存放位置不同。看到条目只能说明打包成功，不能证明目标设备已按它完成编译。

若测试材料已经包含匹配的 APK 与 `.dm`，下面的安装方式可以复现二者一起交付的路径。

```bash
adb install-multiple base.apk base.dm
```

`.dm` 必须与该 APK 版本匹配。该实验能验证 Android 设备怎样消费外部 metadata，却不能自动证明这个 `.dm` 来自 Play 的 Cloud Profile。

### 第二道检查：外部 profile 能否被 ART 使用

Android 17 官方 ART Service 文档推荐先清除本地采集的 profile，再强制执行带详细结果的 `speed-profile` 编译。

```bash
adb shell pm art clear-app-profiles com.example.app
adb shell pm compile -m speed-profile -f -v com.example.app
```

第一条命令清除 current profile（ART 当前采集的运行记录）和 reference profile（已合并、供后续编译参考的记录），但保留 Cloud Profile 等 external profile（由 APK 或安装器从外部提供的 profile），也不会删除已有编译产物。第二条命令的判定依据是输出：`actualCompilerFilter=speed-profile` 表示找到了有效 profile；`actualCompilerFilter=verify` 表示没有可用 profile。典型原因包括文件名错误、格式错误和 DEX checksum 不匹配。

这个测试仍不能区分 APK 内嵌 Baseline Profile、相邻 `.prof` 与 `.dm` 中的 profile，因为它们都属于 ART 可选择的外部输入。要区分来源，必须控制安装产物，而不能只看 `actualCompilerFilter`。

### 第三道检查：构造无 AOT 编译基线

下面的命令用于把包恢复到近似“新安装但未编译”的状态，适合在 Android 14—17 的命令行测试中建立基准组。

```bash
adb shell pm compile --reset com.example.app
```

Android 17 的 `ArtShellCommand` 对该命令有精确定义：它清除 current/reference profile；保留 external profile 供以后 dexopt 使用，但本次 reset（重置）不读取它们；主 DEX 当前等价于 `verify`，secondary DEX（运行期发现的附加 DEX）的 dexopt 产物会被删除。该命令与“卸载并从某个商店重新安装”并不等价，因为安装来源、数据状态和交付文件没有重建。

若只想生成不含 AOT 代码的产物而不清 profile，可以使用下面的命令。

```bash
adb shell pm compile -m verify -f -v com.example.app
```

它与 `--reset` 的差别在于不负责清除 profile。实验记录里要写清使用了哪条命令，否则后续 `speed-profile` 可能读取到上一轮留下的本地 profile。

### 三组实验与观测字段

| 组别 | 建议状态 | 回答的问题 |
|---|---|---|
| 无 AOT 编译组 | `pm compile --reset` 后立即测量 | 解释器/JIT 工作较多时的近似最慢基线 |
| 目标 profile 组 | 控制交付文件，确认 actual filter 为 `speed-profile` | 当前外部 profile 能带来多少收益 |
| 设备稳态组 | 固定版本运行代表性路径，等待后台 dexopt 后测量 | 本地 profile 积累并完成编译后的性能 |

每组至少固定 APK/AAB、设备与系统 build（构建版本）、ART 模块版本、安装来源、账号与数据、网络条件、温度、启动脚本和启动类型。测量指标至少包含 TTID（首次显示时间）、TTFD（主要内容完整可用时间）、慢帧以及 P50/P90/P99（分别有 50%、90%、99% 样本不超过的耗时），并为每条样本附上：

- 首次安装还是版本升级；
- base 与各 split 的 compiler filter/reason；
- 是否执行过 clear/reset/force compile；
- 是否处于后台 dexopt 之后；
- 是否清进程、清数据，以及是否清过文件页缓存。

“冷进程”与“冷文件页缓存”不是同一条件。杀进程只能重建进程状态，系统仍可能把 APK、DEX 和资源文件内容保留在内核页缓存中；常规 App 启动基准也不应依赖需要 root 权限的全局 cache drop（清空页缓存）。

### `ProfileVerifier` 与 Macrobenchmark 的边界

`ProfileVerifier` 是 AndroidX 提供的 profile 状态检查器，适合在 App 或测试代码里确认“是否有 profile、是否已经用 profile 编译、是否排队等待编译、已编译 profile 是否与当前 APK 匹配”。它不能告诉你 ART 使用的是 Baseline Profile 还是 Cloud Profile，也不能替代方法覆盖率与启动耗时测量。

Macrobenchmark 的 `CompilationMode.None`（不预编译）与 `CompilationMode.Partial`（使用 Baseline Profile 做部分预编译）更适合评估 Baseline Profile 的可控收益。官方文档将本地结果视为 profile 可用时的理想场景，并明确指出它不包含生产设备上的 Cloud Profile 影响。验证 Cloud Profile 需要 Play 安装来源、同版本样本分组和足够的观察周期，不能用一次本地 `pm compile` 宣称完成了 Cloud Profile A/B 实验。

## 灰度发布中的 Profile 风险

Profile 是编译输入，覆盖不足会损失收益，覆盖过宽会增加编译时间和产物体积。分批放量（灰度）阶段需要同时看启动、安装/升级与稳定性。

| 风险 | 触发条件 | 可能表现 | 核查方法 |
|---|---|---|---|
| profile 与当前 DEX 不匹配 | 复用旧版本产物、错误的 split、交付过程混入其他版本文件 | actual filter 退为 `verify`，Day-0 收益消失 | 检查版本、DEX checksum、文件名与 `-v` 结果 |
| 规则覆盖过窄 | 只录首页，遗漏登录态、deep link（直达特定页面的链接）、实验分支 | P50 改善，P90/P99 变化很小 | 按入口、账号状态和配置分组 |
| 规则覆盖过宽 | 把低频代码也纳入高频启动路径 | dex2oat 时间与产物体积增加 | 监控安装耗时、dex2oat CPU 时间和 artifact size（编译产物大小） |
| R8/代码变化 | 生成 profile 的产物与发布产物不一致 | profile 不匹配或有效规则减少 | 用当前 release（发布）产物生成并检查规则 |
| 热修复或自定义 ClassLoader | 启动代码转移到动态 DEX | secondary DEX 上出现类加载、解释执行和 JIT | 在 Perfetto 系统时间线中定位 DEX 来源与 JIT slice（时间片段） |
| 动态特性模块 | on-demand（按需下载）split 尚未安装或没有对应 profile | 模块首次进入慢，base 启动正常 | 单独检查每个 split 的安装与 dexopt 状态 |

profile 不匹配通常表现为编译优化缺失，本身不会直接改变 App 代码语义。不过，若同一次发布还修改了 split、热修复、R8 混淆或安装器流程，类加载失败和初始化异常也可能一起出现，所以分批放量看板至少要并排展示：

- TTID、TTFD 与启动慢帧；
- 安装/升级完成到首次可交互的耗时；
- 崩溃率与 ANR 率；
- 各 App 版本、渠道、Android 版本的 compiler filter 分布；
- 安装失败与 profile mismatch 相关日志。

## 与 Baseline Profile 生成流程衔接

[21.4 Baseline Profile 与 Startup Profile 实战](./04-baseline-profile-practice.md) 负责生成和维护 Baseline Profile，发布后则要确认 ART 是否拿到、接受并使用了 profile。两条流程按下面的证据顺序衔接：

1. 21.4 用当前 release 构建生成规则，并通过 Macrobenchmark 验证代表性场景。
2. 检查 APK/AAB 条目、安装来源和每个 APK 各自对应的 `.dm`。
3. 用 `pm art dump` 与 `pm compile -v` 读取 actual filter 和 compilation reason。
4. 用 Perfetto 区分 JIT/类加载成本与业务初始化成本。
5. 按 [21.8 启动监控](./08-startup-monitoring.md)的口径，分版本、渠道和设备监控 TTID/TTFD。

ART 编译原理可回看 1.7，冷/温/热启动路径可回看 8.2。若问题已经定位到数据库、网络、锁或 SDK 同步任务，应治理对应任务，不要继续扩大 profile 规则。

## 厂商 ROM 编译策略差异

同一 APK 在不同设备上可能得到不同的编译结果。可变因素包括安装器是否交付 external metadata、系统 build、ART Mainline（可独立更新的 ART 系统模块）版本、`pm.dexopt.<reason>`、dex2oat 并发数与允许使用的 CPU 核心集合、省电状态、温控和存储压力。

一轮跨 ROM 对比应保存以下证据：

1. 设备 build fingerprint（唯一标识系统构建的字符串）、ART 模块版本、ABI 与安装来源；
2. 安装后立即读取的 per-APK filter/reason；
3. 同一自动化脚本采集的启动 trace；固定“启动三次”无法保证样本条件一致；
4. idle/charging 维护窗口前后的 filter/reason；
5. 设备温度、低电量与低存储状态；
6. ROM 的 `pm.dexopt` 与 `dex2oat` 系统属性快照。

厂商对维护窗口和资源策略的修改没有统一公开清单。缺少源码或厂商文档时，应把差异标成设备观测，不能把单台设备的行为写成 Android 17 规范。

## 动态特性模块与 Play 分发

App Bundle 的每个安装单元都要单独检查。Base APK 已按 `speed-profile` 编译，不代表 on-demand feature（按需下载的功能模块）的 split 已安装、具有匹配 metadata 或完成 dexopt。

| 场景 | 需要检查的对象 | 典型信号 |
|---|---|---|
| 安装后打开首页 | base APK、主 ABI | 主进程启动阶段的 filter、JIT 与类加载 |
| 首次进入按需模块 | 新安装的 feature split | split 的 compiler filter、模块入口附近的 JIT 编译 |
| 升级后进入模块 | 新版本 base 与 split | 旧 metadata 是否失效、升级首进是否回退 |
| 热修复后进入模块 | secondary/dynamic DEX | 自定义 ClassLoader、secondary DEX 与 profile 偏离 |

`.dm` 按 APK 文件名匹配，所以验证日志也要按 base/split 和 ABI 拆分。Play 对 Cloud Profile 及 metadata 的交付策略可能变化；若没有当前 Play 文档或实际取得的安装产物，只能确认设备侧怎样消费文件，不能推断服务端一定交付了什么。

## 排查手册

一次完整排查可以按七步进行：

1. 固定 release 产物、设备 build、ART 模块和安装来源。
2. 检查 APK/AAB 中的 Baseline Profile；有外部 `.prof`/`.dm` 时，按 base/split 核对文件名与版本。
3. 安装后立即执行 `pm art dump`，记录每个 APK/ABI 的 filter 与 reason。
4. 清本地 profile 后用 `pm compile -m speed-profile -f -v` 验证外部 profile，读取 actual filter。
5. 用 `pm compile --reset` 建立无 AOT 编译组，再与目标 profile 组、设备稳态组比较。
6. 在 Perfetto 中同时看 `art::jit::*`（ART 的 JIT 时间片段）、类加载、文件缺页和主线程任务。
7. 分批放量数据按版本、渠道、Android 版本和设备分层，联合观察启动、安装/升级、崩溃与 ANR（应用无响应）。

若 trace 的主要耗时来自业务初始化，profile 排查到这里应停止。扩大规则不会缩短任务自身耗时，还可能增加 dex2oat 与存储成本。

## 参考资料

- [Baseline Profiles overview](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [Debug Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles)
- [Manually create and measure Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/manually-create-measure)
- [Configure ART](https://source.android.com/docs/core/runtime/configure)
- [ART Service configuration](https://source.android.com/docs/core/runtime/configure/art-service)
- [`DexMetadataHelper.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/pm/dex/DexMetadataHelper.java)
- [ART Service `DexMetadataHelper.java`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/DexMetadataHelper.java)
- [`PackageManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/pm/PackageManager.java)
- [`Dexopter.java`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/Dexopter.java)
- [`PrimaryDexopter.java`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/PrimaryDexopter.java)
- [`PrimaryDexUtils.java`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/PrimaryDexUtils.java)
- [`ArtShellCommand.java`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ArtShellCommand.java)
- [历史参考: Android 13 及更早链路] `frameworks/native/cmds/installd/dexopt.cpp`
