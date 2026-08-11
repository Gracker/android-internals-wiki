---

title: "Startup Profile 与 DEX Layout 启动优化"
chapter: "21.12"
section: "21.12"
status: finalized
drafted_date: "2026-05-25"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 7 (API 24) - Android 17 (API 37)"
last_verified: "2026-05-25"
last_verified_against: "Android Developers Startup Profiles / Baseline Profiles docs 2026-05; AOSP android-17.0.0_r1 ART profman + dex2oat; AIW 1.7/8.7/19.12/21.4"
confidence: medium-high
tags: [startup-profile, baseline-profile, dex-layout, startup-optimization, macrobenchmark]
related_chapters: ["21.1", "21.4", "8.7", "19.12", "1.7"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-25"
gap_source: "章节深挖/官方文档"
material_paths:
  - "src/part5-app/ch21-startup/04-baseline-profile-practice.md#扩展-Startup-Profile-与-Dex-Layout-优化"
  - "https://developer.android.com/topic/performance/startupprofiles/overview"
  - "https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations"
  - "https://developer.android.com/topic/performance/baselineprofiles/difference-baseline-startup"
  - "https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles"
  - "https://developer.android.com/topic/performance/baselineprofiles/confirm-startup-profiles"
  - "https://developer.android.com/topic/performance/baselineprofiles/configure-baselineprofiles"
sources:
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md]"
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]"
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - 原理：重新认识 APK 安装包.md]"
  - type: official
    path: "https://developer.android.com/topic/performance/startupprofiles/overview"
  - type: official
    path: "https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/difference-baseline-startup"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/confirm-startup-profiles"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/configure-baselineprofiles"
  - type: aosp
    path: "art/profman/profman.cc"
  - type: aosp
    path: "art/dex2oat/dex2oat.cc"
pipeline_stage: ready-to-publish
task2a_state: processed
task2a_result: processed-draft
last_task2a_at: "2026-05-25T23:10:00+08:00"
task6_state: reviewed
task9_state: reviewed
task6_result: pass-light-edit
task9_result: auto-fixed
reviewed_by: openclaw-task6
reviewed_date: "2026-06-23"
last_task6_at: "2026-06-23T01:10:00+08:00"
last_task9_at: "2026-06-05T05:28:04+08:00"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-14
task2b_state: "fixed"
last_task9_autofix_at: "2026-06-22"
last_task9_audit: "2026-06-22"
finalized_date: "2026-06-23"
finalized_by: "openclaw-task6-auto-promote"
last_task6_audit: "2026-06-22"
---

# 21.12 Startup Profile 与 DEX Layout 启动优化

Startup Profile 是构建期的 DEX 布局输入。它告诉 D8/R8 哪些类和方法属于启动路径，构建工具据此把相关代码尽量集中到主 `classes.dex`。Android 17 安装和运行的是已经排布好的 DEX；设备端 ART 不会在安装时重新执行这次布局。

这与 Baseline Profile 的设备端编译是两条链路。Baseline Profile 交给 ART，帮助 `speed-profile` 选择 AOT 编译范围；Startup Profile 交给构建工具，帮助生成 DEX。前者主要减少解释器/JIT 成本，后者改善启动代码的局部性。两者通常由同一套 `BaselineProfileRule` 测试生成，也应一起使用，但验证证据不能混用。

Baseline Profile 的生成与治理见 21.4，设备端 profile 和 compiler filter 见 21.11。这里重点回答三个问题：

1. 哪些启动入口应标为 `includeInStartupProfile = true`；
2. 怎样证明 release 构建消费了 `startup-prof.txt`；
3. 怎样单独测出 DEX layout 的增量收益。

## Startup Profile 与 Baseline Profile 的边界

`BaselineProfileRule.collect()` 会把采集到的规则写入 Baseline Profile。将某段 CUJ 标为 `includeInStartupProfile = true` 后，这段路径的规则还会进入 Startup Profile。因此，Startup Profile 通常是 Baseline Profile 的子集。

| 项目 | Baseline Profile | Startup Profile |
|---|---|---|
| 文本规则 | `baseline-prof.txt` | `startup-prof.txt` |
| 消费方 | AGP 转成二进制 profile，设备端 ART 使用 | D8/R8 在构建期使用 |
| 生效时机 | 安装期或后续 dexopt | APK/AAB 构建期 |
| 主要结果 | profile-guided AOT 编译 | 主 DEX 与后续 DEX 的代码排布 |
| 覆盖范围 | 启动与高频交互 CUJ | 初始显示所必需的启动 CUJ |
| 直接证据 | 二进制 profile、`ProfileVerifier`、actual compiler filter | `startup-prof.txt`、APK Analyzer、AAB 中的 R8 metadata |

构建后的 APK 通常在 `assets/dexopt/` 中包含 `baseline.prof` 和配套 metadata；AAB 在 `BUNDLE-METADATA/com.android.tools.build.profiles/` 下包含二进制 Baseline Profile。它们能证明 Baseline Profile 已打包，不能证明 DEX layout 已应用。

反过来也一样：`classes.dex` 的布局已经优化，不代表设备端完成了 `speed-profile` 编译。`pm art dump`、`ProfileVerifier` 和 compiler filter 属于 Baseline Profile 证据，不属于 Startup Profile 证据。

还有一个容易遗漏的限制：库可以贡献 Baseline Profile 规则，但不能贡献独立的 Startup Profile。应用需要用自己的启动测试覆盖主要入口，不能等待依赖库替应用决定主 DEX 布局。

## DEX Layout 优化如何影响冷启动

冷启动时，ART 既可能执行 AOT/JIT 代码，也需要读取 DEX 中的类定义、方法、字符串和类型信息。启动代码散落在多个 DEX 或相距很远的区域时，映射和读取会接触更多页，局部性较差。D8/R8 根据 Startup Profile 把启动类和方法尽量放入主 `classes.dex`，并改善其中的顺序。

收益来自“更少、更集中的启动代码页”，并不要求 Android 17 提供新的运行时 API。只要构建产物的 DEX 布局已经改变，Android 7—17 都可能受益；收益大小取决于应用结构、DEX 数量、存储与内存状态。

主 `classes.dex` 的容量是约束条件。Startup Profile 过宽时，启动代码会溢出到后续 DEX；官方建议沿用户启动漏斗逐个加入入口，在主 DEX 接近容量上限之前停止。若已有大量非启动代码占用主 DEX，应先用 R8 缩减无用代码、移出启动路径中的非必要工作，再扩展入口。

布局优化不会改变任务的业务成本：

- 同步 SDK 初始化仍会执行同样的初始化逻辑；
- 数据库升级、大文件读取、Binder 等待和网络请求仍需单独治理；
- 反射与自定义 ClassLoader 触达的动态路径只有被测试覆盖后才可能进入规则；
- native 库加载、资源解码和首屏渲染不由 DEX layout 直接优化。

因此，TTID/TTFD 改善很小并不等于构建未消费 Startup Profile。要先证明布局已应用，再用 trace 判断 DEX/类加载是否占据了足够大的启动成本。

## `includeInStartupProfile` 的场景选择

`includeInStartupProfile = true` 作用于一个 `collect` 块：该块采集的规则既进入 Baseline Profile，也进入 Startup Profile。它应覆盖“启动到初始显示”所需的代码，不宜顺手执行搜索、滚动或二级页面。

下面的测试展示 Launcher 入口的最小写法；项目可以为高频 deep link 或通知入口增加独立测试。

```kotlin
@RunWith(AndroidJUnit4::class)
@LargeTest
class BaselineProfileGenerator {
    @get:Rule
    val rule = BaselineProfileRule()

    @Test
    fun launcherStartup() {
        rule.collect(
            packageName = "com.example.app",
            includeInStartupProfile = true
        ) {
            startActivityAndWait()
        }
    }
}
```

这个块结束在 Activity 启动完成处，没有继续滚动或打开详情页。若首屏在初始显示后仍要完成必要的 Compose/View 组合，应以应用定义的可用边界为准，但不能用漫长的 `waitForIdle()` 把后台任务一并采入。

建议纳入的入口包括：

- 主 Launcher Activity；
- 会创建新进程并进入不同路由的高频 deep link；
- 高频通知点击入口；
- 其他使用量足够高、且启动代码与主入口明显不同的 launcher Activity。

这些动作通常只留在 Baseline Profile：

- 首页长距离滚动；
- 搜索、详情、支付、播放等启动后的 CUJ；
- 低频入口与运营临时页面；
- 依赖随机弹窗、实时网络内容或未固定实验桶的分支。

生成环境要固定账号、语言、地区、权限、通知、远程配置和实验分组。若入口依赖服务端数据，应使用稳定的测试后端或预置数据；否则规则 diff 会反映环境漂移，而非代码变化。

## 构建条件与产物检查

官方当前推荐的组合是 Macrobenchmark 1.2.0 或更高、AGP 8.2 或更高、Android Studio Iguana 或更高。Release 构建需要启用 R8，即 `isMinifyEnabled = true`。

DEX layout optimization 从 AGP 8.1 提供，AGP 8.3 起默认开启。仍使用 AGP 8.1—8.2 的项目，需要在应用模块的 `baselineProfile {}` 中设置 `dexLayoutOptimization = true`。AGP 8.2 不能为每个 variant 保留独立 Startup Profile；若项目必须停留在 8.2，应使用 Baseline Profile Gradle Plugin 1.2.3 或更高版本合并规则，或升级 AGP。

验证要按五层推进：

| 层次 | 证据 | 能回答的问题 |
|---|---|---|
| 规则生成 | `startup-prof.txt` 非空且 diff 合理 | 测试是否采到了启动规则 |
| 构建配置 | Release 开启 R8，layout optimization 生效 | 构建工具是否具备消费条件 |
| DEX 布局 | APK Analyzer、R8 诊断、AAB `r8.json` | 启动代码是否进入 startup DEX |
| ART 编译 | `ProfileVerifier`、`pm art dump` | Baseline Profile 是否用于设备端编译 |
| 性能结果 | Macrobenchmark 与 Perfetto | 布局改变是否缩短了目标启动路径 |

### 检查生成规则和 Baseline Profile 打包

下面的命令用于查看源目录中的两份文本规则，以及发布产物中的二进制 Baseline Profile。

```bash
find app/src -path '*/generated/baselineProfiles/*-prof.txt' -print
unzip -l app-release.apk | grep 'assets/dexopt/baseline.prof'
unzip -l app-release.aab | grep 'BUNDLE-METADATA/com.android.tools.build.profiles/baseline.prof'
```

`startup-prof.txt` 证明规则已生成；`baseline.prof` 证明 Baseline Profile 已打包。两者都不能单独证明 Startup Profile 已改变 DEX 布局。

二进制 Baseline Profile 必须小于 1.5 MB。这个限制针对编译后的 `baseline.prof`，不针对体积通常更大的文本规则。

### 用 APK Analyzer 检查主 DEX

在 Android Studio 中打开 release APK，检查启动类是否集中在主 `classes.dex`。若主 DEX 已被完全填满，或大量启动类落入后续 DEX，说明 Startup Profile 过宽或启动代码体积过大。R8 8.3.21 及更高版本还能输出“启动类中包含多少非启动方法”的诊断。

单 DEX 应用启用 Startup Profile 后出现两个 DEX 并不必然是回归：构建工具可能把启动代码集中到主 DEX，把其余代码移入第二个 DEX。另一个特例是 core library desugaring 的兼容实现固定放在末尾 DEX，该 DEX 不参与布局优化，不能据此判定启动代码溢出。

### 用 AGP 8.8+ 的 R8 metadata 检查

下面的命令直接读取 AAB 中的 R8 metadata，适合 CI 检查是否至少存在一个 startup DEX。

```bash
unzip -p app-release.aab BUNDLE-METADATA/com.android.tools/r8.json \
  | jq '.dexFiles'
```

至少一个条目应为 `"startup": true`。若全部为 `false`，要检查 Startup Profile 是否启用、规则是否为空，以及规则是否在构建流程中被错误混淆。metadata 中的 checksum 还应与 AAB 内对应 DEX 的 SHA-256 一致；不一致说明 R8 之后还有步骤改写了 DEX，metadata 已不能描述发布文件。

## 度量方式与回归判断

官方文档给出的典型提升是相对“只有 Baseline Profile”快 15%—30%，同时强调收益可能很大，也可能很小。这个区间只适合作为决定是否实验的参考，不能作为项目验收阈值。

要测 DEX layout 增量，A/B 两个 release 产物必须满足：

- 源码、R8 规则、资源、签名配置和 Baseline Profile 相同；
- A 组不向 D8/R8 提供 Startup Profile；
- B 组提供目标 `startup-prof.txt`；
- 两组使用相同的 `CompilationMode`，让设备端 AOT 状态一致；
- 每次安装、数据准备、启动入口和迭代次数一致。

若 A 组同时移除了 Baseline Profile，而 B 组同时增加 Baseline 与 Startup Profile，结果会混合 AOT 编译和 DEX layout 两种收益，无法单独度量 DEX layout。

指标至少包含 TTID、TTFD、P50/P90/P95 和离散程度。TTFD 依赖应用在内容可用时调用 `reportFullyDrawn()`；上报点错误时，不能用该指标判断布局效果。

Perfetto 用于解释差异：

- 入口到首帧之间的进程 CPU 时间与类加载区间；
- DEX 映射、缺页和文件读取是否收敛；
- `art::jit::*` 是否在两组间一致，防止 Baseline Profile 编译状态污染实验；
- Binder、SQLite、锁、网络和资源解码是否掩盖布局收益；
- 启动类是否因反射、动态 DEX 或条件分支而未被采集。

“杀进程后的冷启动”仍可能命中文件页缓存。除非测试目标明确包含存储冷态，并且有可重复的设备控制方案，否则不要把一次首轮结果解释成稳定的 DEX I/O 收益。

## 维护风险与发布策略

Startup Profile 会随首页、导航、Compose/View 架构、依赖注入、启动弹窗和实验分支变化。生成测试不更新时，规则文件仍可能存在并通过构建，但内容会逐步偏离当前入口。

发布门禁至少包含：

- 只用 non-debuggable、minified release 等价构建验证；
- 固定账号、地区、语言、权限、弹窗、通知和实验桶；
- review `startup-prof.txt` diff，拦截测试框架、debug 代码和大量非首屏包；
- 检查 `classes.dex` 容量与 startup DEX 标记；
- 保持 Baseline Profile 二进制小于 1.5 MB；
- 对 Launcher、通知和高频 deep link 分别跑回归；
- 在线上区分新装、升级、渠道和编译状态，避免 Cloud/本地 profile 混淆。

不要只用 `startup-prof.txt` 的行数设硬阈值。R8 会内联、移除和重命名代码，同样的文本行数未必对应同样的 DEX 体积。更可靠的门禁是规则 diff、R8 诊断、主 DEX 分布和性能回归一起判断。

## Android 版本与安装渠道边界

Startup Profile 的核心效果在构建期完成，安装渠道不会重新安排 DEX。版本和渠道影响的是 Baseline/Cloud Profile 的设备端编译，不改变已经写入 APK 的布局。

| 能力 | 版本 / 渠道边界 | 写作口径 |
|---|---|---|
| Startup Profile / DEX layout | AGP/D8/R8 构建能力；产物可运行于 Android 7—17 | 验证 release DEX，不把效果绑定到 Play |
| 开发者 Baseline Profile | Android 7+；APK/AAB 可携带 | 设备何时编译取决于系统版本、安装来源和 ProfileInstaller |
| Cloud Profile | Android 9+，由 Google Play 聚合与分发 | 第三方商店和 sideload 不能假设存在 |
| Android 17 ART 编译 | `android-17.0.0_r1` 由 ART Service 管理 dexopt | 用 21.11 的 actual filter 证据验证 |

第三方商店和企业分发需要单独检查 `ProfileVerifier`。`RESULT_CODE_PROFILE_ENQUEUED_FOR_COMPILATION` 只表示 profile 已等待后台编译；`RESULT_CODE_COMPILED_WITH_PROFILE` 才表示存在按 profile 编译的产物。这个差异影响 Baseline Profile A/B，却不改变 Startup Profile 已生成的 DEX 排布。

## 三类 Profile 的职责

Baseline Profile 的生成脚本、Gradle 接入、二进制产物和 Macrobenchmark 基础配置见 21.4；`.dm`、ART Service 与 compiler filter 见 21.11；Startup Profile 关注构建期证据和 DEX layout A/B。

建议的实施顺序是：

1. 先建立稳定的启动 CUJ 和 Baseline Profile；
2. 把初始显示所需的 CUJ 标为 Startup Profile；
3. 确认 release 构建产生 startup DEX；
4. 保持设备端编译状态一致，测量 layout 增量；
5. 若启动代码放不进主 DEX，先减少启动路径，再增加入口。

## AOSP `profman` / `dex2oat` 验证入口

Android 17 的 `art/profman/profman.cc` 和 `art/dex2oat/dex2oat.cc` 可以验证 Baseline/runtime profile 的设备端消费；`Dexopter.java` 可以验证没有有效 profile 时 `speed-profile` 会调整为 `verify`。这些 AOSP 源码不负责 Startup Profile 的 DEX layout。

Startup Profile 的证据应停在 AGP/D8/R8 和构建产物：`startup-prof.txt`、R8 诊断、AAB 的 `r8.json`、APK Analyzer 中的 DEX 分布。把边界划在这里，可以避免用 `pm art dump` 证明一项它无法证明的构建期优化。

## 失败案例

### 规则过宽

症状是主 `classes.dex` 接近满载，大量启动类进入后续 DEX，B 组 P90 没有改善。处理方式是移除搜索、详情、滚动等非初始显示 CUJ，并检查是否能把同步初始化移出启动路径。

### 生成环境漂移

症状是同一 commit 多次生成的 diff 出现弹窗、实验、登录和测试工具类。处理方式是固定环境，并将不稳定入口拆成受控测试。CI 应对同一输入的规则稳定性做抽样检查。

### 构建后改写 DEX

症状是 `r8.json` 标记了 startup DEX，但 checksum 与 AAB 中的 DEX 不一致。处理方式是定位 R8 之后的加固、插桩或重打包步骤；在 checksum 对齐之前，不能依据 metadata 宣称发布包已保留布局。

### AOT 状态污染 A/B

症状是 B 组同时显示 `speed-profile`，A 组仍为 `verify`，启动差异远大于布局可解释范围。处理方式是固定 `CompilationMode`，确认两组 actual filter 一致，再比较 DEX layout。

### 瓶颈不在 DEX

症状是 layout 证据完整，但 Perfetto 显示 Binder、SQLite、锁或网络占据首帧前的大部分时间。处理方式是回到 21.1 的启动分段治理；保留 Startup Profile，同时把优化预算放到占比更高的路径。

## 参考资料

- [Overview of Startup Profiles](https://developer.android.com/topic/performance/startupprofiles/overview)
- [Create Startup Profiles](https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations)
- [Difference between Baseline Profiles and Startup Profiles](https://developer.android.com/topic/performance/baselineprofiles/difference-baseline-startup)
- [Confirm Startup Profiles optimization](https://developer.android.com/topic/performance/baselineprofiles/confirm-startup-profiles)
- [Configure Baseline Profile generation](https://developer.android.com/topic/performance/baselineprofiles/configure-baselineprofiles)
- [`profman.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/profman/profman.cc)
- [`dex2oat.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/dex2oat/dex2oat.cc)
- [`Dexopter.java`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/Dexopter.java)
