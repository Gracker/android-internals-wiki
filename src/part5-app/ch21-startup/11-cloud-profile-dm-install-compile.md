---

title: "云端 Profile、DM 文件与安装后编译优化"
chapter: "21.11"
section: "21.11"
status: finalized
drafted_date: "2026-05-21"
applicable_versions: "Android 7 (API 24) - Android 16 (API 36)"
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
task6_state: revisiting
reviewed_date: "2026-05-21"
reviewed_by: openclaw-task6
review_type: draft-review
review_round: 1
task6_result: pass-light-edit
task9_state: reviewed
task9_result: pass-tech-review
last_task6_at: "2026-05-21T01:15:21+08:00"
last_task6_review_log: logs/review/2026-05-21-01-review.md
task6_review_notes: "2026-05-21 Task6 01: L1/L2 无需正文修改；结构、锚点、验证标注通过，转 Task9 pending。"
task2b_state: fixed
task2b_result: fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-06-06
last_task9_at: 2026-06-06T13:25:00+08:00
last_task9_review_log: logs/deep-review/2026-06-06-13-deep-review.md
last_task2b_lite_at: "2026-06-06"
task9_review_notes: '2026-05-21 Task9 01: needs-rework。P0 1：ART Service dump 命令；P1 1：无 profile 基线命令/API34+ 口径。已写入 logs/deep-review/2026-05-21-01-deep-review.md。'
task2b_fixed_date: "2026-06-06"
finalized_date: 2026-06-06
finalized_by: openclaw-task9-auto-promote

---

# 21.11 云端 Profile、DM 文件与安装后编译优化

<!-- outline-start -->
## 要点

### 🔹 云端 Profile 在启动优化里的位置
说明 Play 分发的 cloud profile、应用随包提供的 baseline profile、设备本地 JIT profile 分别影响哪一段启动成本，避免把编译收益和业务初始化收益混在一起评估。

### 🔹 DM 文件与 ART 编译模式
梳理 `.dm` 文件进入安装过程后的使用方式，覆盖 verify、speed-profile、speed 等常见编译模式，并标出不同模式对安装耗时和首次启动耗时的影响。

### 🔹 dex2oat、bg-dexopt-job 与空闲编译
解释安装时编译、后台空闲编译、系统维护窗口之间的关系，给出排查启动慢时需要同时观察的系统事件和命令入口。

### 🔹 Profile 命中率与冷启动收益评估
建立验证口径：同一版本、同一设备、清除本地 profile、区分首次启动与稳定启动，用 P50/P90/P99 分位值判断编译优化是否改变启动曲线。

### 🔹 灰度发布中的 Profile 风险
覆盖错误 profile、过窄场景、动态特性模块、热修复和 R8 混淆变更带来的失效场景，说明线上回归需要看启动耗时、安装耗时和崩溃率三类指标。

### 🔹 与 Baseline Profile 实战的分工
本节聚焦系统如何消费 profile 与如何验证效果；生成规则、Macrobenchmark 录制和 Gradle 集成详见 21.4 节。

## 扩展

### 🔸 厂商 ROM 编译策略差异
对比不同设备的 `pm compile` 默认策略、维护窗口频率和省电模式影响，形成启动回归排查清单。

### 🔸 动态特性模块与 Play 分发
补充 App Bundle、按需模块和 cloud profile 覆盖范围之间的关系，说明多模块应用的 profile 验证边界。

<!-- outline-end -->

## 为什么单独拆出这一节

21.4 节已经写了 Baseline Profile 怎么生成、怎么接入、怎么用 Macrobenchmark 验证。本节换一个角度：应用发布后，系统和安装来源怎样消费 profile，以及 App 团队怎样判断某次启动收益是不是来自编译状态变化。

启动优化里最容易混在一起的有三类成本：代码解释执行 / JIT 预热、启动任务本身耗时、类加载和 DEX 布局 I/O。Profile 只影响其中一部分。若主线程卡在数据库升级、网络同步、锁等待或 SDK 初始化，Cloud Profile 和 Baseline Profile 都不会把这些任务变短。

[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md]
[已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles/overview]

## 云端 Profile 在启动优化里的位置

ART 从 Android 7 起采用解释执行、JIT 和 Profile-Guided AOT 混合模式。首次安装后，如果没有可用 profile，代码路径可能先走解释执行和 JIT；设备运行一段时间后，本地 profile 会记录热点方法，再由后台 dexopt 在空闲窗口按 profile 编译。Cloud Profile 和 Baseline Profile 都是在这个机制里提前提供热点信息。

| Profile 类型 | 生产者 | 到达设备的时机 | 主要影响 | 验证入口 |
|---|---|---|---|---|
| Baseline Profile | App 团队、库作者、CI | 随 APK / AAB 打包，安装或后续编译时被 ART 消费 | 新安装、新升级后的 Day-0 代码执行成本 | APK 内 `assets/dexopt/baseline.prof`、`ProfileVerifier`、`pm art dump` |
| Cloud Profile | Google Play 基于用户群体聚合 | Play 分发时随 dex metadata 一起到达设备 | 补充真实用户高频路径，覆盖开发脚本没跑到的路径 | 安装来源、`.dm` 文件、编译状态 |
| 本地 JIT Profile | 单台设备运行时 | 用户实际使用后写入 `/data/misc/profiles/cur/.../primary.prof` | 后续启动和后台编译逐步收敛 | `profman --dump-profile-file`、后台 dexopt 日志 |
| Startup Profile | App 团队、构建系统 | 构建期交给 D8 / R8 做 DEX layout | 启动路径类和方法的物理布局 | APK DEX 布局、Macrobenchmark 对比 |

Cloud Profile 的价值不是替代应用侧 Baseline Profile。Google 官方文档明确建议随包提供 Baseline Profile，因为它比单靠 Cloud Profile 更早可用；Cloud Profile 更适合作为发布后的补充资料，帮助真实用户路径继续收敛。[已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles/overview]

这里要把收益拆清。Baseline / Cloud Profile 主要减少解释执行和 JIT 预热，把命中的方法提前编译。Startup Profile 主要调整 DEX 布局，减少启动时类加载的 I/O 和 page fault。两者可以同时使用，但验证时要分开看，避免把 DEX 布局收益和 AOT 编译收益合成一个数字。

## DM 文件与 ART 编译模式

`.dm` 是 dex metadata 文件。AOSP `DexMetadataHelper` 中固定使用 `.dm` 后缀，并把 `base.apk` 对应到 `base.dm`；校验时会把 `.dm` 当作 zip archive 打开，按包名和版本号校验 metadata manifest。`PackageManager.INSTALL_IGNORE_DEXOPT_PROFILE` 的注释也说明，安装时可以忽略 DM 文件里的 profile 和 APK 内嵌 profile，这个标志不影响之后的后台 dexopt 和手动 `pm compile`。

[已验证: AOSP `frameworks/base/core/java/android/content/pm/dex/DexMetadataHelper.java`]
[已验证: AOSP `frameworks/base/core/java/android/content/pm/PackageManager.java`]

设备端消费 `.dm` 的关键点在 `installd`。`dexopt.cpp` 会检查 dex metadata 里是否存在 `primary.prof`；存在时，`prepare_app_profile()` 打开 APK、`.dm` 和 reference profile，再通过 `profman` 的 copy-and-update 流程把 profile 合并到 reference profile。后续 `dex2oat` 才能按 `speed-profile` 这类 profile-guided filter 编译命中的方法。

[已验证: AOSP `frameworks/native/cmds/installd/dexopt.cpp`, `check_profile_exists_in_dexmetadata()` / `prepare_app_profile()`]

ART 常见 compiler filter 可以按成本理解：

| filter | 编译行为 | 安装 / 后台成本 | 首次启动影响 |
|---|---|---|---|
| `verify` | 只做 DEX 验证，不做 AOT 编译 | 成本低，安装更快 | 未命中 AOT 的路径会依赖解释执行和 JIT |
| `speed-profile` | 验证 DEX，并编译 profile 中的方法和类加载信息 | 成本中等，取决于 profile 规模 | 命中 profile 的启动路径更早进入机器码执行 |
| `speed` | 验证并 AOT 编译所有方法 | 成本高，占用更多存储和 CPU | 覆盖更广，但多数三方 App 不该把它当默认目标 |

[已验证: 官方文档, source.android.com/docs/core/runtime/configure]

`speed-profile` 的收益取决于 profile 质量。profile 过窄，启动路径仍会出现解释执行和 JIT；profile 过宽，安装后编译和后台编译的成本会上升。App 团队能控制的是 Baseline Profile 质量、发版验证口径和灰度监控，不能假设所有设备和安装来源都会在同一时刻完成同样的编译。

## dex2oat、bg-dexopt-job 与空闲编译

安装完成不等于编译完成。source.android.com 的 ART 文档描述了一条常见路径：Play 分发 `.dm` 时，`.dm` 可携带 Cloud Profile；ART 会 AOT 编译 Cloud Profile 中的方法。没有 `.dm` 时，应用前几次运行会解释执行未编译方法，热点方法再由 JIT 编译并写入本地 profile；设备空闲且充电时，后台编译任务读取合并后的 profile 重新编译，之后启动可以使用更多 AOT 产物。[已验证: 官方文档, source.android.com/docs/core/runtime/configure]

Android 14 起，App 的 on-device AOT 编译由 ART Service 处理。ART Service 文档列出了标准默认值：`pm.dexopt.bg-dexopt=speed-profile`，`pm.dexopt.first-boot=verify`，`pm.dexopt.inactive=verify`，`pm.dexopt.shared` 默认走 `speed` 兜底；被其他 App 使用的 shared code 因隐私原因不能使用本地 profile 时，ART Service 会先尝试 Cloud Profile，缺失时再按 `pm.dexopt.shared` 处理。[已验证: 官方文档, source.android.com/docs/core/runtime/configure/art-service]

AOSP ART Service 里，主 dex 的 `.dm` 路径由 `PrimaryDexopter.buildDmPath()` 构造；开启 `cloudCompilationPm()` flag 时，`PrimaryDexopter.onDexoptStart()` 会尝试创建 SDC companion 文件。这里能确认的是 ART Service 已经把 dex metadata、profile 和云侧编译资料纳入同一套 dexopt 管理面；具体设备是否命中云侧资料，仍要看安装来源、flag、设备 build 和编译状态输出。

[已验证: AOSP `art/libartservice/service/java/com/android/server/art/PrimaryDexopter.java`]

排查启动慢时，不要只看应用进程。编译相关证据分布在三个位置：

| 位置 | 看什么 | 用途 |
|---|---|---|
| 安装阶段 | `system_server`、ART Service、`artd`、`dex2oat` 是否出现 | 判断是否发生安装期或后台编译 |
| 应用启动阶段 | `art::jit::*`、类加载、page fault | 判断启动时是否还在解释执行 / JIT 预热 |
| 包状态 | compiler filter、compilation reason、profile 状态 | 判断当前 APK 已经落到什么编译结果 |

下面的命令用于本地复现时确认包的编译状态，重点看 compiler filter 和 compilation reason。

```bash
adb shell pm art dump com.example.app
adb shell dumpsys package dexopt | grep -A 12 com.example.app
```

Android 14+ 优先看 `pm art dump`；旧设备可退回 `dumpsys package dexopt`。如果状态仍是 `verify`，而启动 trace 又有大量 `art::jit::*`，编译覆盖不足就是可疑方向。

## Profile 命中率与冷启动收益评估

验证 profile 收益时，测试对象要固定。至少固定五个条件：同一个 APK / AAB、同一个设备型号和系统版本、同一安装来源、同一账号和数据状态、同一启动脚本。只要其中一个条件变化，启动耗时就可能被缓存、网络、弹窗、配置、数据库迁移或 ROM 策略污染。

推荐把测试拆成三组：

| 组别 | 状态 | 回答的问题 |
|---|---|---|
| 无 profile 基线 | 清掉编译产物和本地 profile 后启动 | App 在没有预编译帮助时有多慢 |
| Baseline / Cloud Profile 命中 | 使用目标安装来源安装，等待或强制触发 `speed-profile` | profile 是否改善首次或前几次启动 |
| 稳态组 | 应用运行多次，后台 dexopt 完成后启动 | 本地 JIT profile 和后台编译收敛后能到什么水平 |

下面的命令适合线下实验，用于构造“无 profile”和“强制 speed-profile”两个状态。执行前先确认测试设备允许这些 shell 操作。

```bash
# === API 34+ (Android 14+)：两步清理 ===
# 第一步：将编译 filter 降为 verify（不做 AOT 编译）
adb shell cmd package compile -f -m verify com.example.app

# 第二步：清掉本地 profile（包括 reference profile 和当前 profile）
adb shell pm art clear-app-profiles com.example.app

# === API 33 及以下：单条命令 ===
# 重置编译状态（通常需要 root 或 AOSP build）
adb shell cmd package compile --reset com.example.app

# 使用当前可用 profile 强制触发 speed-profile 编译
adb shell cmd package compile -m speed-profile -f com.example.app
```

API 34+ 需要两步才能保证"无 profile"基线干净：先降 filter 到 `verify`，再清 profile 文件。只做 `compile --reset` 在 API 34+ 上可能仍保留 Play / DM 下发的 profile，导致基线被旧 profile 污染。命令只适合实验室复现。线上发布验证仍要按真实安装来源测试，因为 Play、第三方商店、adb 侧载和厂商应用商店对 `.dm`、profile 安装和后台 dexopt 的触发时机可能不同。

指标上，至少看 TTID、TTFD、启动阶段慢帧和 P50 / P90 / P99。P50 变好只能说明主路径改善；P90 / P99 没变，常见原因是 profile 没覆盖长尾路径，或者长尾主要来自 I/O、网络、迁移任务和低端机 CPU。21.8 节已经给出启动监控的分位值口径，本节只补一个编译维度字段：每条启动样本最好带上安装来源、是否升级后首启、当前 compiler filter、是否清数据或首次安装。

## 灰度发布中的 Profile 风险

Profile 也会带来发布风险。它不是“加上就只会变快”的静态资源，而是一份会驱动编译决策的热点路径描述。

| 风险 | 常见触发 | 线上症状 | 验证动作 |
|---|---|---|---|
| profile 与代码不匹配 | R8 混淆、方法签名变化、热修复改写路径 | 编译状态退回、收益消失 | 每次 release 用当前产物重新生成并检查 profile diff |
| 场景过窄 | 只录制首页，漏掉登录、配置、动态首页 | P50 变好，P90 / P99 不变 | 按入口和用户状态拆分 TTID / TTFD |
| 场景过宽 | 把低频路径也写入 profile | 安装后编译时间变长，低端机后台负载上升 | 观察安装耗时、后台 dexopt 耗时和电量状态 |
| 动态特性模块缺口 | on-demand feature 首次安装后才出现代码 | 首次进入模块仍有 JIT / 类加载抖动 | 对每个 split 模块单独跑进入场景和编译状态检查 |
| 热修复 / 插件化 | 运行时加载新 dex 或替换方法 | profile 命中下降，类加载和解释执行增多 | trace 中看 secondary dex、class loading 和 JIT 活动 |

灰度看板不要只放启动耗时。至少并排看三类指标：启动 TTID / TTFD，安装或升级后首次打开耗时，崩溃率 / ANR 率。profile 文件损坏或不匹配时，最常见的结果是编译收益消失；但如果同时有安装器、split、热修复和混淆变更，启动回归可能伴随类加载异常或初始化失败。

## 与 Baseline Profile 实战的分工

21.4 节负责“怎么生成”：Macrobenchmark 场景、`BaselineProfileRule`、Gradle 集成、构建产物检查和 A/B 验证。本节负责“系统怎么消费”：`.dm` 文件、Cloud Profile、compiler filter、ART Service、`dex2oat` 和后台维护窗口。

交叉引用可以按下面的边界使用：

- 生成规则、脚本设计、`baseline-prof.txt` 维护：详见 21.4 节。
- 冷启动、温启动、热启动系统路径：详见 8.2 节。
- `dex2oat`、JIT、AOT、Profile-Guided Optimization 原理：详见 1.7 节。
- 启动线上分位值、慢启动归因、Android 15+ `ApplicationStartInfo`：详见 21.8 节。

本节不重复 ART 编译器内部优化，也不展开 Macrobenchmark 录制细节。读者排查“为什么这次启动 profile 没起效”时，只需要把文件是否存在、profile 是否被合并、compiler filter 是否变化、启动 trace 是否仍有 JIT 这四件事查清。

## 厂商 ROM 编译策略差异

[自动发现] 同一 APK 在不同 ROM 上，profile 收益可能不同。差异来自安装器是否传递 `.dm`、ART Mainline 版本、后台维护窗口、低电量策略、省电模式、存储空间压力和厂商自定义 dexopt 策略。官方 ART Service 文档也把 `pm.dexopt.<reason>`、并发数、`dalvik.vm.*dex2oat-*` 等属性列为可配置项。[已验证: 官方文档, source.android.com/docs/core/runtime/configure/art-service]

线下排查清单可以固定成几步：

1. 记录设备 build、ART module 版本、安装来源和是否开启省电模式。
2. 用 `getprop | grep -E 'pm.dexopt|dex2oat'` 记录 ROM 的默认编译策略。
3. 安装后立刻抓 `pm art dump`，记录 filter 和 reason。
4. 启动三次，观察 `art::jit::*` 是否逐步减少。
5. 充电、灭屏、空闲一段时间后再次查看编译状态，确认后台 dexopt 是否执行。

这些步骤不要求 App 团队修改代码。它们的目标是把“这台设备 profile 没收益”拆成安装来源问题、后台编译未触发、ROM filter 不同、或启动瓶颈不在编译四类。

[待验证: 主流厂商 ROM 在 `pm.dexopt.bg-dexopt`、维护窗口频率和低电量策略上的差异，缺少统一公开文档，需用实机记录补证据]

## 动态特性模块与 Play 分发

App Bundle 和动态特性模块会改变 profile 验证边界。Base APK 的 profile 命中，不等于按需模块的代码也已经完成编译。首次进入某个 dynamic feature 时，设备可能才拿到对应 split；如果该模块没有被 profile 覆盖，或者安装来源没有随模块交付对应 metadata，进入模块时仍可能出现类加载、解释执行和 JIT 活动。

多模块应用建议把验证口径拆开：

| 场景 | 验证对象 | 失败表现 |
|---|---|---|
| 首次安装打开首页 | Base module 的启动路径 | 首页 TTID 慢，`art::jit::*` 集中在主进程启动阶段 |
| 首次进入按需模块 | 动态 feature split 的入口路径 | 模块首进慢，类加载和 JIT 出现在模块入口附近 |
| 升级后进入模块 | 新旧 split + profile 是否匹配 | 升级后首进退化，稳态恢复 |
| 热修复后进入模块 | 运行时 dex 与 profile 是否偏离 | profile 命中下降，secondary dex 加载增加 |

[待验证: Play 对动态 feature 的 Cloud Profile / dex metadata 覆盖细节需要按当前 Play 分发文档和实测安装包确认]

## 排查手册

把本节内容压成一次可执行排查：

1. 确认安装来源和包内 profile：APK 内有 `assets/dexopt/baseline.prof`，Play 分发场景再确认是否存在 `.dm`。
2. 确认当前编译状态：看 `pm art dump` 或 `dumpsys package dexopt`，记录 compiler filter 和 reason。
3. 对照启动 trace：搜索 `art::jit::*`、class loading、page fault 和主线程长任务。
4. 分开测试无 profile、profile 命中、稳态三组，不用单次启动数字下结论。
5. 灰度监控同时看启动耗时、安装 / 升级后首启耗时、崩溃率和 ANR 率。

如果 trace 显示主线程时间主要花在业务初始化，profile 排查到这里就该停止。继续扩大 profile 只会增加编译范围，不能把业务任务变短。

## 参考资料

- [已验证: 官方文档] Baseline Profiles overview — `developer.android.com/topic/performance/baselineprofiles/overview`
- [已验证: 官方文档] Create Baseline Profiles — `developer.android.com/topic/performance/baselineprofiles/create-baselineprofile`
- [已验证: 官方文档] Configure ART — `source.android.com/docs/core/runtime/configure`
- [已验证: 官方文档] ART Service configuration — `source.android.com/docs/core/runtime/configure/art-service`
- [已验证: AOSP] `frameworks/base/core/java/android/content/pm/dex/DexMetadataHelper.java`
- [已验证: AOSP] `frameworks/native/cmds/installd/dexopt.cpp`
- [已验证: AOSP] `frameworks/base/core/java/android/content/pm/PackageManager.java`
- [已验证: AOSP] `art/libartservice/service/java/com/android/server/art/PrimaryDexopter.java`
- [结构参考] `Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md`
- [结构参考] `Clippings/Android 性能优化 - 原理：重新认识 APK 安装包.md`
- [结构参考] `Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md`
