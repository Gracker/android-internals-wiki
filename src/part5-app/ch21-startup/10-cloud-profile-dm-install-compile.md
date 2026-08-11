---


title: "云端 Profile、DM 文件与安装后编译优化"
chapter: "21.10"
section: "21.10"
status: finalized
drafted_date: "2026-05-21"
applicable_versions: "Android 7 (API 24) - Android 17 (API 37)"
last_verified: "2026-05-21"
last_verified_against: "source.android.com ART configure / ART Service configuration, Android Developers Baseline Profiles docs, AOSP DexMetadataHelper + installd dexopt.cpp + ART Service"
confidence: medium
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
  - type: clippings-structure
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings-structure
    path: "Clippings/Android 性能优化 - 原理：重新认识 APK 安装包.md"
  - type: clippings-structure
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
tags: [startup, art, baseline-profile, dexopt, cloud-profile]
related_chapters: ["1.7", "8.2", "21.4", "21.8"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-20"
gap_source: "素材驱动/AOSP结构/官方文档"
pipeline_stage: ready-to-publish
task6_state: reviewed
reviewed_date: "2026-06-23"
reviewed_by: openclaw-task6
review_type: draft-review
review_round: 1
task6_result: pass-light-edit
task9_state: reviewed
task9_result: auto-fixed
last_task6_at: "2026-06-23T01:10:00+08:00"
last_task6_audit: 2026-06-15
last_task6_review_log: logs/review/2026-05-21-01-review.md
task6_review_notes: "2026-05-21 Task6 01: L1/L2 无需正文修改；结构、锚点、验证标注通过，转 Task9 pending。"
task2b_state: fixed
task2b_result: fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-06-06
last_task9_at: "2026-06-22T19:25:53+08:00"
last_task9_review_log: logs/deep-review/2026-06-22-19-audit.md
last_task2b_lite_at: "2026-06-06"
task9_review_notes: '2026-05-21 Task9 01: needs-rework。P0 1：ART Service dump 命令；P1 1：无 profile 基线命令/API34+ 口径。已写入 logs/deep-review/2026-05-21-01-deep-review.md。; 2026-06-22 Task9 idle-audit AUTO-FIX: 按 Android 17 ArtShellCommand 修正 API34+ pm compile --reset 与 external profile 口径。'
task2b_fixed_date: "2026-06-06"
finalized_date: "2026-06-23"
finalized_by: "openclaw-task6-auto-promote"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-23
last_task9_audit: 2026-06-22
last_task9_autofix_at: 2026-06-22
---

# 云端 Profile、DM 文件与安装后编译优化

## Profile 在发布后如何生效

Baseline Profile 的生成、Gradle 接入和 Macrobenchmark 验证见 21.4。发布后还要继续追踪：安装来源交付了哪些 profile，Android 17 的 ART Service 怎样选择 profile 和 compiler filter，以及 App 团队怎样判断一次启动变化是否来自编译状态。

先划清收益边界。Profile 可以减少解释执行、JIT 预热和部分 DEX 读取开销，却不会缩短数据库迁移、网络等待、锁竞争或 SDK 同步初始化。一次冷启动同时包含这些成本，只看总耗时很容易误判。

## 云端 Profile 在启动优化里的位置

从 Android 7 起，ART 会在解释执行、JIT 和 AOT 产物之间选择。设备运行应用时，本地 profile 逐渐记录常用代码；后台 dexopt 再按 profile 编译热点路径。Baseline Profile 和 Cloud Profile 都是在本地使用数据充分之前提供编译依据，但生产者、可用时机和可控程度不同。

| Profile 类型 | 生产者 | 何时生效 | 主要作用 | App 团队能否直接控制 |
|---|---|---|---|---|
| Baseline Profile | App 或库的开发团队 | 随发布产物交付，安装期或后续 dexopt 使用 | 覆盖新安装、新升级后的核心路径 | 可以；规则、版本和回归测试都由发布方维护 |
| Cloud Profile | Google Play 根据已发布版本的用户样本聚合 | 样本达到条件并由 Play 交付之后 | 补充 Baseline Profile 未覆盖的高频路径 | 不能直接编辑；依赖 Play、版本规模和聚合周期 |
| 本地运行时 profile | 单台设备上的 ART/JIT | 用户运行应用后逐步积累 | 指导该设备后续的 `speed-profile` 编译 | 只能通过稳定的代码路径间接影响 |
| Startup Profile | App 团队与构建工具 | 构建期由 D8/R8 消费 | 调整启动相关类和方法在 DEX 中的布局 | 可以；它不作为设备端 AOT profile 使用 |

Google 的 Baseline Profiles 文档给出两个重要边界：

- Cloud Profile 需要 Android 9（API 28）或更高版本、足够的用户样本以及聚合时间；新版本发布后的数小时到数天内，不应假设它已经可用。
- Baseline Profile 随当前版本发布，可以覆盖 Day-0。它不能由 Cloud Profile 替代。

因此，Baseline/Cloud Profile 与 Startup Profile 要分开评估。前两者主要影响哪些方法被 AOT 编译；Startup Profile 主要改变 DEX 布局，目标是降低启动阶段的读取与缺页成本。一次构建可以同时使用二者，但 A/B 实验需要明确改变的是编译状态、DEX 布局，还是两者一起改变。

## DM 文件与 ART 编译模式

`.dm` 是与某个 APK 一一对应的 Dex Metadata 容器。Android 17 的 `frameworks/base/.../DexMetadataHelper` 把 `base.apk` 映射为同目录下的 `base.dm`；split APK 也按各自文件名匹配，不能拿 base 的 `.dm` 替代 split 的 metadata。

需要避开三个常见误解：

1. `.dm` 不等同于 Cloud Profile。它是 zip 容器，可以带 profile，也可以带 VDEX 和配置；是否来自 Play、包含什么内容，要结合安装来源和文件内容判断。
2. `.dm` 不保证每次安装都存在。APK 内嵌 Baseline Profile、相邻的 `base.apk.prof` 和相邻的 `base.dm` 都可能成为 ART Service 的外部输入。
3. 文件存在不代表 profile 可用。文件名、二进制格式或 DEX checksum 不匹配时，ART Service 会拒绝该 profile。

Android 17 源码为这些判断提供了直接证据：

- `PrimaryDexUtils.getExternalProfiles()` 同时返回 prebuilt profile 路径和 `.dm` profile 路径。
- `DexMetadataHelper.getDexMetadataInfo()` 打开 `.dm`，读取可选的 `config.pb`，并按 profile、VDEX 或两者都有进行分类。
- `PrimaryDexopter.buildDmPath()` 按当前 base/split APK 构造 `.dm` 路径。
- `Dexopter` 只有在存在有效 profile 时才保留 profile-guided filter；profile 为空时，会把请求的 `speed-profile` 调整为 `verify`。

Android 17 的 framework 安装校验只确认 `.dm` 能作为 zip archive 打开。旧资料经常根据方法注释写成“安装阶段一定校验 `manifest.json` 的包名和版本号”，但 `android-17.0.0_r1` 的该方法实现并没有执行这项语义校验，不宜继续沿用这条结论。ART 在消费 profile 时仍会检查格式和 DEX 匹配关系。

`PackageManager.INSTALL_IGNORE_DEXOPT_PROFILE` 也能说明安装期与后续 dexopt 是两个时机：该安装标志会忽略 `.dm` 和 APK 内嵌 profile，并抑制无效安装 profile 的警告，但不会阻止以后由后台 dexopt 或 `pm compile` 使用 profile。

### Android 17 的执行链路

下面的路径图用于区分输入、调度者和编译执行者。

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

从 Android 14（API 34）起，应用的设备端 AOT 编译由 ART Service 管理。`installd/dexopt.cpp` 对理解 Android 13 及更早版本有历史价值，但不能再作为 Android 17 的主调度链路；Android 17 应以 `ArtManagerLocal`、`Dexopter`、`PrimaryDexopter`、`artd` 和 `dex2oat` 为源码锚点。

### compiler filter 与 compilation reason

这两个字段回答不同问题：

- compiler filter 表示“生成了何种编译产物”。
- compilation reason 表示“哪类事件触发了这次 dexopt”，例如安装、后台维护或 shell 命令。

| filter | Android 17 中的含义 | 代价与边界 |
|---|---|---|
| `verify` | 执行验证，不生成 AOT 编译代码 | CPU、存储成本较低；启动路径更多依赖解释器与 JIT |
| `speed-profile` | 按有效 profile 编译选中的方法 | 成本取决于 profile；没有有效 profile 时，实际 filter 会变成 `verify` |
| `speed` | 面向速度编译全部方法 | 编译耗时和产物体积更高，不应作为普通三方应用的默认对照目标 |

排查时必须记录 **requested filter** 和 **actual filter**。只看到命令参数 `-m speed-profile`，不能证明 profile 已经命中。`Dexopter.java` 在“there is no valid profile”分支明确执行 `speed-profile → verify` 调整。

## dex2oat、bg-dexopt-job 与空闲编译

安装返回成功不代表以后不再编译。若安装期没有使用有效 profile，应用运行后仍可由 JIT 采集本地 profile；后台任务再把这些信息用于 `speed-profile` 编译。因此，同一 APK 的“安装后第一次打开”和“使用数日后的打开”可能处于不同编译状态。

ART Service 的标准默认值包括：

- `pm.dexopt.first-boot=verify`
- `pm.dexopt.boot-after-ota=verify`
- `pm.dexopt.boot-after-mainline-update=verify`
- `pm.dexopt.bg-dexopt=speed-profile`
- `pm.dexopt.inactive=verify`
- `pm.dexopt.cmdline=verify`
- `pm.dexopt.shared=speed`，作为共享代码无法使用本地 profile 时的兜底

共享代码的规则需要额外说明。某个包的代码被其他 App 通过共享库或动态加载方式使用时，ART Service 不能把该包的本地 profile 用于公共编译产物，以免泄露用户行为。系统会尝试 Cloud Profile；缺失时才使用 `pm.dexopt.shared` 指定的 filter。

Android 14 及更高版本中，后台 dexopt 默认每天在设备空闲且充电时运行。设备退出 idle 或达到温控阈值时，任务会被取消。ART Service 没有旧 Package Manager 的 post-boot dexopt job，因此不能把开机后前台资源竞争直接套用到 Android 17。

App 进程无权要求用户设备立即完成后台 dexopt。`pm.dexopt.disable_bg_dexopt` 和 `pm bg-dexopt-job --disable` 是平台测试入口，不应写入三方 App 的优化方案。

### 查看包的 dexopt 状态

下面的命令用于 Android 14—17 测试设备，读取目标包当前的主 dex 与 split dex 编译状态。

```bash
adb shell pm art dump com.example.app
```

输出中要逐个 APK/ABI 查看 compiler filter、compilation reason 和 artifact 状态。Android 13 及更早版本可用 `dumpsys package dexopt` 辅助排查；Android 17 的首选入口是 `pm art dump`。

下面的属性采集用于记录 ROM 对标准策略的修改，仅适合测试环境。

```bash
adb shell getprop | grep -E 'pm\.dexopt|dex2oat'
```

这些值由系统镜像和 ART 模块决定。不同设备出现差异时，应把它们作为实验条件保存，不能据此要求线上 App 修改系统属性。

## Profile 命中率与冷启动收益评估

### 第一道检查：发布产物里有什么

下面的命令用于确认 APK 和 AAB 是否包含 Baseline Profile；它不判断规则覆盖率。

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

第一条命令清除 current/reference 等本地 profile，但保留 Cloud Profile 等 external profile，也不会删除已有编译产物。第二条命令的判定依据是输出：`actualCompilerFilter=speed-profile` 表示找到了有效 profile；`actualCompilerFilter=verify` 表示没有可用 profile。典型原因包括文件名错误、格式错误和 DEX checksum 不匹配。

这个测试仍不能区分 APK 内嵌 Baseline Profile、相邻 `.prof` 与 `.dm` 中的 profile，因为它们都属于 ART 可选择的外部输入。要区分来源，必须控制安装产物，而不能只看 `actualCompilerFilter`。

### 第三道检查：构造无 AOT 编译基线

下面的命令用于把包恢复到近似“新安装但未编译”的状态，适合在 Android 14—17 上建立 shell 实验基线。

```bash
adb shell pm compile --reset com.example.app
```

Android 17 的 `ArtShellCommand` 对该命令有精确定义：它清除 current/reference profile；保留 external profile 供以后 dexopt 使用，但本次 reset 不读取它们；主 dex 当前等价于 `verify`，secondary dex 的 dexopt 产物会被删除。该命令与“卸载并从某个商店重新安装”并不等价，因为安装来源、数据状态和交付文件没有重建。

若只想生成不含 AOT 代码的产物而不清 profile，可以使用下面的命令。

```bash
adb shell pm compile -m verify -f -v com.example.app
```

它与 `--reset` 的差别在于不负责清除 profile。实验记录里要写清使用了哪条命令，否则后续 `speed-profile` 可能读取到上一轮留下的本地 profile。

### 三组实验与观测字段

| 组别 | 建议状态 | 回答的问题 |
|---|---|---|
| 无 AOT 编译组 | `pm compile --reset` 后立即测量 | 解释器/JIT 较多时的上界成本 |
| 目标 profile 组 | 控制交付文件，确认 actual filter 为 `speed-profile` | 当前外部 profile 能带来多少收益 |
| 设备稳态组 | 固定版本运行代表性路径，等待后台 dexopt 后测量 | 本地 profile 收敛后的性能 |

每组至少固定 APK/AAB、设备与系统 build、ART 模块版本、安装来源、账号与数据、网络条件、温度、启动脚本和启动类型。测量指标至少包含 TTID、TTFD、慢帧以及 P50/P90/P99，并为每条样本附上：

- 首次安装还是版本升级；
- base 与各 split 的 compiler filter/reason；
- 是否执行过 clear/reset/force compile；
- 是否处于后台 dexopt 之后；
- 是否清进程、清数据，以及是否清过文件页缓存。

“冷进程”与“冷文件页缓存”不是同一条件。杀进程只能重建进程状态，系统仍可能保留 APK、DEX 和资源页；常规 App 启动基准也不应依赖需要 root 的全局 cache drop。

### `ProfileVerifier` 与 Macrobenchmark 的边界

`ProfileVerifier` 适合在 App 或测试代码里确认“是否有 profile、是否已经用 profile 编译、是否排队等待编译、已编译 profile 是否与当前 APK 匹配”。它不能告诉你 ART 使用的是 Baseline Profile 还是 Cloud Profile，也不能替代方法覆盖率与启动耗时测量。

Macrobenchmark 的 `CompilationMode.None` 与 `CompilationMode.Partial` 更适合评估 Baseline Profile 的可控收益。官方文档把这种本地结果定义为较理想的性能场景，并明确指出它不包含 Cloud Profile 的作用。Cloud Profile 的验证需要 Play 安装来源、同版本分群和足够的观察周期，不能用一次本地 `pm compile` 宣称已完成 Cloud A/B。

## 灰度发布中的 Profile 风险

Profile 是编译输入，覆盖不足会损失收益，覆盖过宽会增加编译时间和产物体积。灰度阶段需要同时看启动、安装/升级与稳定性。

| 风险 | 触发条件 | 可能表现 | 核查方法 |
|---|---|---|---|
| profile 与当前 DEX 不匹配 | 复用旧版本产物、错误的 split、交付过程混包 | actual filter 退为 `verify`，Day-0 收益消失 | 检查版本、DEX checksum、文件名与 `-v` 结果 |
| 规则覆盖过窄 | 只录首页，遗漏登录态、深链、实验分支 | P50 改善，P90/P99 变化很小 | 按入口、账号状态和配置分桶 |
| 规则覆盖过宽 | 把低频代码也纳入热路径 | dex2oat 时间与产物体积增加 | 监控安装耗时、dex2oat CPU 时间和 artifact size |
| R8/代码变化 | 生成 profile 的产物与发布产物不一致 | profile 不匹配或有效规则减少 | 用当前 release 产物生成并检查规则 |
| 热修复或自定义 ClassLoader | 启动代码转移到动态 DEX | secondary dex 上出现类加载、解释执行和 JIT | 在 Perfetto 中定位 DEX 来源与 JIT slice |
| 动态特性模块 | on-demand split 尚未下载或没有对应 profile | 模块首次进入慢，base 启动正常 | 单独检查每个 split 的安装与 dexopt 状态 |

profile 不匹配通常表现为编译优化缺失，而不是直接导致 App 代码语义改变。不过，若同一次发布还修改了 split、热修复、混淆或安装器流程，类加载失败和初始化异常也可能一起出现，所以灰度看板至少要并排展示：

- TTID、TTFD 与启动慢帧；
- 安装/升级完成到首次可交互的耗时；
- 崩溃率与 ANR 率；
- 各版本、渠道、Android 版本的 compiler filter 分布；
- 安装失败与 profile mismatch 相关日志。

## 与 Baseline Profile 生成流程衔接

21.4 负责生成和维护 Baseline Profile，发布后则要确认 ART 是否拿到、接受并使用了 profile。两条流程按下面的证据链衔接：

1. 21.4 用当前 release 构建生成规则，并通过 Macrobenchmark 验证代表性场景。
2. 检查 APK/AAB 条目、安装来源和 per-APK `.dm`。
3. 用 `pm art dump` 与 `pm compile -v` 读取 actual filter 和 reason。
4. 用 Perfetto 区分 JIT/类加载成本与业务初始化成本。
5. 21.8 按版本、渠道和设备分层监控 TTID/TTFD。

ART 编译原理可回看 1.7，冷/温/热启动路径可回看 8.2。若问题已经定位到数据库、网络、锁或 SDK 同步任务，应回到启动任务治理，不要继续扩大 profile。

## 厂商 ROM 编译策略差异

同一 APK 在不同设备上可能得到不同的编译结果。可变因素包括安装器是否交付外部 metadata、系统 build、ART Mainline 版本、`pm.dexopt.<reason>`、dex2oat 并发与 CPU 集、省电状态、温控和存储压力。

一轮跨 ROM 对比应保存以下证据：

1. 设备 build fingerprint、ART 模块版本、ABI 与安装来源；
2. 安装后立即读取的 per-APK filter/reason；
3. 同一脚本的启动 trace，而不是固定“启动三次”；
4. idle/charging 维护窗口前后的 filter/reason；
5. 设备温度、低电量与低存储状态；
6. ROM 的 `pm.dexopt` 与 `dex2oat` 属性快照。

厂商对维护窗口和资源策略的修改没有统一公开清单。缺少源码或厂商文档时，应把差异标成设备观测，不能把单台设备的行为写成 Android 17 规范。

## 动态特性模块与 Play 分发

App Bundle 的每个安装单元都要单独看。Base APK 已按 `speed-profile` 编译，不代表 on-demand feature 的 split 已下载、具有匹配 metadata 或完成 dexopt。

| 场景 | 需要检查的对象 | 典型信号 |
|---|---|---|
| 安装后打开首页 | base APK、主 ABI | 主进程启动阶段的 filter、JIT 与类加载 |
| 首次进入按需模块 | 新安装的 feature split | split 的 compiler filter、模块入口附近的 JIT |
| 升级后进入模块 | 新版本 base 与 split | 旧 metadata 是否失效、升级首进是否回退 |
| 热修复后进入模块 | secondary/dynamic DEX | 自定义 ClassLoader、secondary dex 与 profile 偏离 |

`.dm` 按 APK 文件名匹配，所以验证日志也要按 base/split 和 ABI 拆分。Play 对 Cloud Profile 及 metadata 的交付策略可能变化；没有当前 Play 文档或抓取到的安装产物时，只能确认设备侧消费路径，不能推断服务端一定交付了哪些文件。

## 排查手册

一次完整排查可以收敛为七步：

1. 固定 release 产物、设备 build、ART 模块和安装来源。
2. 检查 APK/AAB 中的 Baseline Profile；有外部 `.prof`/`.dm` 时按 base/split 核对文件名与版本。
3. 安装后立即执行 `pm art dump`，记录每个 APK/ABI 的 filter 与 reason。
4. 清本地 profile 后用 `pm compile -m speed-profile -f -v` 验证外部 profile，读取 actual filter。
5. 用 `pm compile --reset` 建立无 AOT 编译组，再与目标 profile 组、设备稳态组比较。
6. 在 Perfetto 中同时看 `art::jit::*`、类加载、文件缺页和主线程任务。
7. 灰度数据按版本、渠道、Android 版本和设备分层，联合观察启动、安装/升级、崩溃与 ANR。

若 trace 的主要耗时来自业务初始化，profile 证据链到这里应停止。扩大规则不会缩短任务自身耗时，还可能增加 dex2oat 与存储成本。

## 参考资料

- [Baseline Profiles overview](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [Debug Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles)
- [Manually create and measure Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/manually-create-measure)
- [Configure ART](https://source.android.com/docs/core/runtime/configure)
- [ART Service configuration](https://source.android.com/docs/core/runtime/configure/art-service)
- [`DexMetadataHelper.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/pm/dex/DexMetadataHelper.java)
- [`PackageManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/pm/PackageManager.java)
- [`Dexopter.java`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/Dexopter.java)
- [`PrimaryDexopter.java`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/PrimaryDexopter.java)
- [`PrimaryDexUtils.java`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/PrimaryDexUtils.java)
- [`ArtShellCommand.java`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ArtShellCommand.java)
- [历史参考: Android 13 及更早链路] `frameworks/native/cmds/installd/dexopt.cpp`
