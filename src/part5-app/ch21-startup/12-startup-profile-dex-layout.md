---
title: "Startup Profile 与 DEX Layout 启动优化"
chapter: "21.12"
section: "21.12"
status: ready-for-review
drafted_date: "2026-05-25"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 7 (API 24) - Android 17 (API 37)"
last_verified: "2026-05-25"
last_verified_against: "Android Developers Startup Profiles / Baseline Profiles docs 2026-05; AOSP ART profman + dex2oat; R8 StartupOptions; AIW 1.7/8.7/19.15/21.4"
confidence: medium-high
tags: [startup-profile, baseline-profile, dex-layout, startup-optimization, macrobenchmark]
related_chapters: ["21.1", "21.4", "8.7", "19.15", "1.7"]
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
  - type: source
    path: "r8/src/main/java/com/android/tools/r8/profile/startup/StartupOptions.java"
pipeline_stage: task6_pending
task2a_state: processed
task2a_result: processed-draft
last_task2a_at: "2026-05-25T23:10:00+08:00"
---

# 21.12 Startup Profile 与 DEX Layout 启动优化

<!-- outline-start -->
## 要点

### 🔹 Startup Profile 与 Baseline Profile 的边界
说明 Startup Profile 只面向启动路径的 DEX 布局优化，Baseline Profile 面向启动与高频交互的 ART 预编译；两者可能由同一套 Macrobenchmark 脚本产出，但编译阶段和收益来源不同。

### 🔹 DEX Layout 优化如何影响冷启动
梳理 R8 根据 `startup-prof.txt` 调整 classes.dex 方法和类布局的路径，解释它主要降低启动阶段的类加载、页面故障、磁盘读取局部性成本，而不是替代业务初始化治理。

### 🔹 `includeInStartupProfile` 的场景选择
给出哪些 CUJ 应进入 Startup Profile：入口 Activity、首屏骨架、首屏 Compose/View 树、首屏路由和必要 SDK 初始化；同时说明搜索、滚动、详情页等非首屏路径应留在 Baseline Profile。

### 🔹 构建条件与产物检查
覆盖 AGP、R8、Macrobenchmark、`dexLayoutOptimization` 等配置要求，说明如何检查 `startup-prof.txt`、`baseline-prof.txt`、APK/AAB 内二进制 profile 和 DEX 布局结果。

### 🔹 度量方式与回归判断
用 Macrobenchmark 对比 `CompilationMode.Partial`、无 profile、仅 Baseline Profile、Baseline + Startup Profile 的结果，区分 TTID、TTFD、首帧前 CPU 时间、主线程 I/O、类加载耗时和方差。

### 🔹 维护风险与发布策略
说明规则过宽会增加启动路径外代码的磁盘读取成本，规则过窄会漏掉首屏路径；补充 CI 生成、profile diff review、登录态/弹窗/远程配置固定、灰度验证和异常回滚策略。

### 🔹 Android 版本与安装渠道边界
建立 Android 7+、Android 9+ Cloud Profile、Play 分发、本地安装、第三方商店与 Android 16 云端编译材料之间的边界，避免把某一渠道能力写成通用系统行为。

## 扩展

### 🔸 与 21.4 Baseline Profile 实战的分工
本节从 21.4 的扩展点拆出，21.4 保留 Profile 生成和治理主线，本节聚焦启动路径 DEX layout、构建产物和验证组合。

### 🔸 AOSP `profman` / `dex2oat` 验证入口
后续加工可结合 `art/profman/`、`art/dex2oat/` 和 AGP/R8 文档验证 profile 消费路径，不照搬官方示例代码。

### 🔸 失败案例
记录 Startup Profile 误覆盖非首屏路径、启动弹窗导致 profile 不稳定、CI 设备状态污染、首屏网络请求掩盖 DEX layout 收益等案例。

<!-- outline-end -->

Startup Profile 解决的是启动代码在 DEX 文件里的排布问题。它通常和 Baseline Profile 一起生成，但消费方不同：Baseline Profile 交给 ART 做 profile-guided AOT 编译，Startup Profile 交给构建系统和 R8 调整 DEX layout。前者减少解释执行和 JIT 热身，后者减少启动阶段加载 DEX 时的随机访问、页故障和缓存失配。[已验证: 官方文档, developer.android.com/topic/performance/startupprofiles/overview][已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles/difference-baseline-startup]

21.4 已经覆盖 Baseline Profile 的生成、打包和验证主线。本节只处理启动路径 DEX layout：哪些路径应该带 `includeInStartupProfile = true`，怎样确认 `startup-prof.txt` 被构建系统消费，怎样把收益和业务初始化、I/O、网络等待区分开。ART 编译管线详见 1.7，Baseline Profile 的系统机制详见 8.7，APM 视角详见 19.15。

Clippings 的《Android 性能优化》把速度问题拆成 CPU 时间、缓存命中率和任务调度三个视角，并把 Dex 类文件重排序放在缓存局部性一类。这里借用这个组织方式：Startup Profile 不直接减少业务代码指令数，也不改变线程调度，它把“启动会读到的类和方法”放得更集中，让同一段冷启动更少等 DEX 页加载。[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md][结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]

## Startup Profile 与 Baseline Profile 的边界

Baseline Profile 的规则面向 ART。构建阶段会把 `baseline-prof.txt` 编成二进制 `baseline.prof` / `baseline.profm`，APK 中位于 `/assets/dexopt/`，AAB 中位于 `/BUNDLE-METADATA/com.android.tools.build.profiles/`。安装或后台 dexopt 阶段，`profman` 和 `dex2oat --compiler-filter=speed-profile` 消费这些规则，生成 OAT / VDEX 产物。[已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles][已验证: AOSP, art/profman/profman.cc + art/dex2oat/dex2oat.cc]

Startup Profile 的规则面向构建期 DEX layout。生成出来的文本文件通常是 `src/<variant>/generated/baselineProfiles/startup-prof.txt`，AGP 在构建 release 包时把它交给 R8 / D8，使启动路径里的类和方法更集中地落在前面的 DEX 区域。官方文档把它称为 Baseline Profile 的一个子集，但它不等同于 `speed-profile` 编译，也不需要等设备端后台 dexopt 才生效。[已验证: 官方文档, developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations][已验证: R8, StartupOptions.java]

两者的关系适合按收益来源来分：

| 项目 | Baseline Profile | Startup Profile |
|------|------------------|-----------------|
| 主要消费方 | ART / `profman` / `dex2oat` | AGP / R8 / D8 |
| 生效阶段 | 安装后或后台 dexopt | 构建 APK / AAB 时 |
| 主要收益 | 常用方法提前 AOT 编译，减少解释执行和 JIT 热身 | 启动代码排布更集中，减少 DEX 加载局部性成本 |
| 覆盖路径 | 启动、高频交互、列表滚动、搜索、详情等 | 从入口到首屏可交互前的启动路径 |
| 验证重点 | `baseline.prof`、`dumpsys package dexopt`、`ProfileVerifier`、Macrobenchmark | `startup-prof.txt`、R8 输出元数据、DEX 数量和 layout、Macrobenchmark |

Baseline Profile 可以覆盖启动之后的核心操作；Startup Profile 应该收窄到启动入口。把详情页、搜索页、大量滚动路径都塞进 Startup Profile，可能让 `classes.dex` 被非首屏代码挤占，首屏路径反而溢出到后续 DEX 文件。

## DEX Layout 优化如何影响冷启动

冷启动期间，系统要加载 APK 中的 DEX，解析类、方法、字符串、类型索引，并执行入口 Activity、依赖注入、首屏 UI 和必要 SDK 初始化。即使这些方法后续会被 AOT 编译，启动时仍然要访问 DEX 元数据和类定义；访问顺序越分散，越容易产生额外的磁盘读取和页故障。

Dex 类文件重排序的旧做法通常要收集类加载顺序，再用外部工具改 APK。Startup Profile 把这件事合入官方构建路径：Macrobenchmark 记录启动测试中触达的类和方法，生成 `S` 标记规则，R8 根据这些规则调整 DEX 中的布局。Clippings 的 Dex 重排序章节强调空间局部性，本节沿用这个判断：启动阶段连续访问的类和方法越集中，CPU 等待数据进入缓存和内存映射页的时间越少。[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]

这类优化只处理代码位置，不能替代启动治理：

- `Application.onCreate()` 里同步初始化 10 个 SDK，Startup Profile 只能让相关代码更快被读到，不能减少这些 SDK 的工作量。
- 首屏等待网络接口，DEX layout 不会改变服务端耗时和弱网抖动。
- 主线程读数据库或大文件，收益可能被 I/O 等待覆盖。
- 冷启动里频繁反射、动态代理、插件化类加载，Profile 生成脚本需要覆盖这些路径，否则 layout 只优化到静态入口。

因此，度量时要把“代码加载和类初始化收益”与“业务初始化减少”分开看。Perfetto 中如果首帧前大头是 Binder、SQLite、网络等待或锁竞争，Startup Profile 的收益会很有限。

## `includeInStartupProfile` 的场景选择

Macrobenchmark 生成 Baseline Profile 时，可以在 `rule.collect()` 里用 `includeInStartupProfile = true` 标记启动路径。官方建议把启动相关测试放进这个标记，非启动路径不要放进去。[已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles/create-baselineprofile]

下面的代码只展示参数位置，重点是把入口路径和启动路径标出来：

```kotlin
@RunWith(AndroidJUnit4::class)
@LargeTest
class StartupProfileGenerator {
    @get:Rule
    val rule = BaselineProfileRule()

    @Test
    fun startup() {
        rule.collect(
            packageName = "com.example.app",
            includeInStartupProfile = true
        ) {
            pressHome()
            startActivityAndWait()
            device.waitForIdle()
        }
    }
}
```

这段测试会把启动期间触达的类和方法纳入 Startup Profile。真实项目里，脚本要固定登录态、远程配置、弹窗和实验分组，否则每次生成出的 `startup-prof.txt` 会漂移。

适合放进 Startup Profile 的路径：

- Launcher 入口：从桌面点击图标到首屏骨架可见，是大多数用户的主入口。
- Deep link 入口：消息、外链、分享卡片会直接进入某个首屏路由，路径和 Launcher 不同。
- 通知启动：通知点击后可能走独立 Activity、任务栈恢复或中转页。
- 首屏 Compose / View 树：首屏布局、主题、字体、图片占位、导航容器、首屏列表骨架。
- 必要 SDK 初始化：只保留首屏必须同步完成的 SDK；能延后的初始化不应靠 Startup Profile 掩盖。

不适合放进 Startup Profile 的路径：

- 首页列表长距离滚动：它属于高频交互，留给 Baseline Profile。
- 搜索、详情、支付、播放等二级路径：它们适合 Profile AOT，不适合占用启动 DEX 区域。
- 低频活动入口：规则会挤占 `classes.dex` 空间。
- 依赖网络状态的分支：启动 Profile 需要稳定可复现，网络分支会放大噪声。

官方文档给的选择顺序是从最常见启动入口开始，再沿启动 funnel 添加入口；当启动代码快要占满 `classes.dex` 时停止。复杂应用不要追求“所有入口都覆盖”，应该先保证主入口和最高频深链入口稳定命中。[已验证: 官方文档, developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations]

## 构建条件与产物检查

Startup Profile 对工具链有要求。官方推荐 Jetpack Macrobenchmark 1.2.0+、AGP 8.2+ 和 Android Studio Iguana+；Release 构建需要启用 R8，也就是 `isMinifyEnabled = true`。DEX layout optimization 从 AGP 8.1 开始提供，AGP 8.3 起默认启用；AGP 8.1 到 8.2 需要在 `baselineProfile {}` 中显式开启 `dexLayoutOptimization = true`。[已验证: 官方文档, developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations]

配置检查可以按四层做：

| 检查层 | 要看什么 | 常见失败 |
|--------|----------|----------|
| 生成层 | `src/<variant>/generated/baselineProfiles/startup-prof.txt` | 测试没有 `includeInStartupProfile = true`，文件为空或缺失 |
| 打包层 | APK / AAB 中的 `baseline.prof` / `baseline.profm` | 只生成了文本规则，没有进入 release 产物 |
| 构建层 | R8 是否启用，`dexLayoutOptimization` 是否开启 | Debug / non-minified 包验证 layout，结果不代表发布包 |
| DEX 层 | 启动类是否留在 `classes.dex`，AGP 8.8+ 可看 R8 输出元数据 | 启动路径过大，溢出到后续 DEX 文件 |

AGP 8.8+ 的项目可以检查生成的 `r8.json`，确认 Startup Profile 是否应用到 DEX layout。旧项目没有这个元数据时，只能结合 DEX 文件数量、反编译顺序和 Macrobenchmark 结果判断。官方还提醒：如果启用 Startup Profile 后单 DEX 应用变成两个 DEX，末尾 desugared DEX 不参与 DEX layout 优化，排查时不要把它误读成启动代码溢出。[已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles/confirm-startup-profiles]

验证命令要把“包内 profile 存在”和“设备端已编译”分开。Startup Profile 关注前者和 DEX layout，Baseline Profile 还要看设备端编译状态：

```bash
# 检查 APK 内 Baseline Profile 二进制产物
zipinfo app-release.apk | grep 'assets/dexopt/baseline.prof'

# 检查 AAB 内 Baseline Profile 二进制产物
zipinfo app-release.aab | grep 'BUNDLE-METADATA/com.android.tools.build.profiles/baseline.prof'

# 检查设备端是否已经按 Profile 编译
adb shell dumpsys package dexopt | grep -A 3 com.example.app
```

`baseline.prof` 存在只说明 ART 有机会收到预编译材料。`status = speed-profile` 才表示设备端已有按 Profile 编译的产物；`status = verify` 可能是还没进入后台 dexopt，也可能是安装来源没有触发编译。[已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles]

## 度量方式与回归判断

Startup Profile 的收益需要用同一套 release 包、同一设备、同一启动脚本对比。Macrobenchmark 应至少分四组：

| 组别 | 目的 | 预期读法 |
|------|------|----------|
| 无 Profile | 建立解释执行 / 未优化基线 | 作为最慢参考 |
| 仅 Baseline Profile | 看 ART AOT 编译收益 | TTID / TTFD 应下降，JIT 相关成本减少 |
| Baseline + Startup Profile | 看 DEX layout 增量收益 | 在 Baseline 之上继续下降，方差也可能收窄 |
| 业务优化后 Profile | 验证延迟初始化、删同步 I/O 后的组合收益 | 判断 Profile 是否仍覆盖新启动路径 |

指标不要只看平均值。启动优化更适合看 P50 / P90 / P95、标准差和冷启动首轮数据。TTID 衡量首帧，TTFD 衡量可交互；如果 App 没正确调用 full display 上报，TTFD 会失真。官方调试文档也提醒，启动期间的网络和重 I/O 会增加 benchmark 方差，最好在测试环境用假实现固定这些依赖。[已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles]

Perfetto 侧可以看这些信号：

- `bindApplication` 到首帧前的主线程 CPU 时间是否下降。
- `ClassLinker`、类加载、反射路径是否减少长尾。
- `art::jit::*` 活动是否仍在首启期间出现，若出现要回到 Baseline Profile 覆盖率排查。
- 主线程 I/O、SQLite、网络等待是否仍占主导；如果是，Startup Profile 不是主矛盾。
- 多次迭代的页故障和磁盘读取是否更稳定；DEX layout 的收益常体现在方差收窄。

官方文档提到 Startup Profile 在部分应用中可带来相对 Baseline Profile 的额外启动提升，但影响大小取决于 App 结构。工程里不要直接把官方比例写进目标 KPI，应使用本项目 release 包实测。

## 维护风险与发布策略

Startup Profile 的维护成本来自“路径变化”。首页改成 Compose、导航框架换路由、引入启动弹窗、AB 实验调整首屏模块，都会改变启动期间触达的类和方法。CI 里只要生成脚本不更新，Profile 就会逐渐偏离真实启动路径。

建议把治理做成发布门禁：

- 生成脚本固定环境：登录态、语言、地区、实验桶、弹窗、通知权限和远程配置都要固定。
- Profile diff 必须 review：新增大量非首屏包名、测试工具类、debug 依赖时拦截。
- 启动路径大小设阈值：`startup-prof.txt` 行数、`classes.dex` 方法数、首屏包名占比都可纳入巡检。
- Macrobenchmark 跑发布包：debug、non-minified、关闭 R8 的结果不能代表 DEX layout。
- 灰度只改 Profile 时要单独看新装和首更用户：老用户可能已经有 Cloud Profile 或本地 JIT Profile，收益会被冲淡。
- 回滚策略保留业务开关：Profile 文件本身随包发布，线上回滚通常要靠版本回退；能延后的启动初始化仍应有远程开关。

失败案例通常有三类。第一类是规则过宽，把搜索、详情、支付全放进 Startup Profile，`classes.dex` 被挤满，主入口收益消失。第二类是测试环境不稳定，弹窗、登录、权限页随机出现，生成结果每次都不同。第三类是启动慢来自网络、数据库、锁等待或第三方 SDK，同步问题没有处理，Profile 只能改善很小一段代码加载成本。

## Android 版本与安装渠道边界

版本和渠道要拆开写，避免把某个分发路径能力说成系统通用行为。

| 能力 | 版本 / 渠道边界 | 写作口径 |
|------|----------------|----------|
| 开发者 Baseline Profile | Android 7+ 可随 APK / AAB 携带 | 所有渠道都能携带文件，但设备端何时编译取决于安装来源和 ProfileInstaller |
| Cloud Profiles | Android 9+，Google Play 分发 | 来自 Play 的聚合热点补充，不覆盖第三方商店和 sideload |
| Startup Profile / DEX layout | 构建期能力，AGP / R8 决定 | 只要 release 构建消费了 `startup-prof.txt`，安装渠道不会改变 DEX 文件布局 |
| Android Studio / Gradle 自动编译 | AGP 8.4+ non-debuggable build | 适合本地验证，不代表 Play 安装的即时行为 |
| Android 16 云端编译材料 | 当前公开材料仍需更多一手证据 | 可写成 Play 分发增强方向，不写成所有设备本地 dex2oat 被替代 |

第三方商店和企业内部分发要重点验证 `ProfileInstaller` 状态。官方文档写明：非 Play、非现代 Gradle 安装路径下，Jetpack ProfileInstaller 通常负责把 profile 入队，等待下一轮后台 DEX 优化。`RESULT_CODE_PROFILE_ENQUEUED_FOR_COMPILATION` 只表示已入队，`RESULT_CODE_COMPILED_WITH_PROFILE` 才表示编译完成。这个边界对启动 A/B 很重要，尤其是中国区多商店分发。[已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles]

## 与 21.4 Baseline Profile 实战的分工

21.4 继续负责 Baseline Profile 主线：生成脚本、二进制 profile 产物、ProfileInstaller、`dumpsys package dexopt`、Cloud Profiles 和线上回归。本节只追加启动路径 DEX layout 的判断：哪些规则能进 `startup-prof.txt`，R8 是否消费了它，`classes.dex` 是否放得下，Macrobenchmark 是否能测出相对 Baseline Profile 的增量。

如果读者只做一件事，优先把 21.4 的 Baseline Profile 做对。Startup Profile 是第二层优化，适合已经有稳定启动脚本、release 构建打开 R8、首屏路径可控的项目。

## AOSP `profman` / `dex2oat` 验证入口

Baseline Profile 的设备端消费可以从 AOSP `art/profman/` 和 `art/dex2oat/` 验证。`profman` 负责读取、合并和分析 Profile；`dex2oat` 在 `speed-profile` 这类依赖 Profile 的编译模式下，只编译 Profile 命中的方法和类加载相关内容。系统编译策略的总览见 1.7。[已验证: AOSP, art/profman/profman.cc + art/dex2oat/dex2oat.cc]

Startup Profile 的 DEX layout 不在 `dex2oat` 里完成。它的公开验证入口更靠近 AGP / R8：生成的 `startup-prof.txt`、R8 的 startup profile 选项、AGP 8.8+ 的 `r8.json` 和最终 DEX 排布。排查时把这两条路径分开，能避免把“ART 是否编译”误当成“DEX layout 是否生效”。

## 失败案例

**规则过宽。** 某次把首页滚动、搜索、详情和支付都标成 `includeInStartupProfile = true`。Macrobenchmark 里启动首帧没有变快，反而 P90 抖动变大。原因是启动规则占用太多 `classes.dex` 空间，主入口需要的类被挤到后续 DEX。修复方式是把非首屏路径移回 Baseline Profile，只保留 Launcher、通知、深链三类入口。

**启动弹窗污染 Profile。** 灰度弹窗、权限弹窗和登录态变化会让脚本每次跑到不同 UI 分支。生成文件 diff 里出现大量弹窗 SDK、实验 SDK 和测试账号路径。修复方式是为 Profile 生成环境固定实验桶和账号状态，必要时给启动弹窗加 benchmark-only 关闭开关。

**首屏网络掩盖收益。** 代码布局优化后，TTID 下降很小，Perfetto 显示主线程大段等待网络回调和 SQLite 初始化。这个结果不说明 Startup Profile 失效，只说明启动瓶颈不在 DEX layout。处理顺序应回到 21.1 的启动分段：先删同步网络和主线程 I/O，再重新测 Profile 增量。

**本地结果误推线上。** AGP 8.4+ 的本地 non-debuggable 安装可能自动触发 profile 编译，Play 安装则常在后台设备更新时编译。把本地 `speed-profile` 状态当作 Play 首装即时状态，会高估线上首开收益。灰度分析要把安装来源、安装后等待时间、新用户和更新用户分开。
