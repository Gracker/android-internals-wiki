---
title: "Baseline Profile 与 Startup Profile 实战"
chapter: "21.4"
section: "21.4"
status: finalized
applicable_versions: "Android 7 (API 24) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "Current Android Developers Baseline/Startup Profile, ProfileVerifier and Macrobenchmark docs; AOSP android-17.0.0_r1 art/profman + art/dex2oat; AIW 8.7 / 19.12"
confidence: medium-high
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/overview"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles"
  - type: official
    path: "https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/confirm-startup-profiles"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/configure-baselineprofiles"
  - type: official
    path: "https://developer.android.com/reference/androidx/profileinstaller/ProfileVerifier"
  - type: aosp
    path: "art/profman/profman.cc"
  - type: aosp
    path: "art/dex2oat/dex2oat.cc"
  - type: clippings-structure
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings-structure
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
  - type: local
    path: "src/part2-performance/ch08-responsiveness/07-baseline-profiles.md"
  - type: local
    path: "src/part3-tools/ch19-apm/12-baseline-profiles.md"
tags: [baseline-profile, aot, dex-layout, macrobenchmark]
related_chapters: ["21.1", "8.7", "1.7", "19.12"]
consolidated_from:
  - "src/part5-app/ch21-startup/12-startup-profile-dex-layout.md"
  - "src/part5-app/ch21-startup/09-startup-case-studies.md#案例三"
pipeline_stage: finalized
task6_state: reviewed
task9_state: "reviewed"
task2b_state: "fixed"
---

# Baseline Profile 与 Startup Profile 实战

## 范围

Baseline Profile 解决的是代码在用户设备上“何时以什么编译状态运行”。ART 是 Android Runtime，负责执行 DEX 字节码；DEX 是 APK 中承载应用字节码的文件格式。没有预编译时，ART 可以先解释执行代码，再由 JIT（Just-In-Time）在运行中编译热点；AOT（Ahead-Of-Time）则在代码运行前完成编译。Baseline Profile 可以让关键路径更早获得合适的编译状态，却不能消除磁盘、网络、Binder、锁等待、业务初始化或首屏布局工作。

平台源码锚点为 Android 17 / API 37 / `android-17.0.0_r1`。截至 2026-08-14，官方列出的最低推荐稳定组合是 AGP 8.0.0、Macrobenchmark 1.4.1 和 ProfileInstaller 1.4.1；Android Studio 的 Baseline Profile Generator 模板和 Startup Profile 建议使用 AGP 8.2 以上。AGP、Macrobenchmark、ProfileInstaller 和 Google Play 各自演进，项目仍需固定一组经过验证的版本并写入实验记录。

## 1. Baseline Profile 是编译提示

### 1.1 Profile 规则包含什么

Human Readable Format（HRF，可读文本格式）用类名和方法签名记录需要优化的代码。方法规则前可带：

- `H`：Hot，运行中频繁使用的方法；
- `S`：Startup，启动阶段使用的方法；
- `P`：Post-startup，启动后使用的方法。

构建工具会把应用与依赖库的规则合并，按 release 产物的混淆和优化结果重写，再生成 ART 可消费的紧凑二进制 profile。二进制规则会关联具体 APK 中的 DEX 标识与校验信息，因此旧版本 profile 不能直接套到新 APK。

### 1.2 Android 17 上的 ART 关系

Android 17 ART 的 [`profman`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/profman/profman.cc) 负责 profile 处理与合并，`dex2oat` 根据 compiler filter 和 profile 选择编译工作；源码入口见 [`dex2oat.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/dex2oat/dex2oat.cc)。compiler filter 是 ART 的编译策略名称，用来决定编译范围和优化程度。

`speed-profile` 表示由 profile 指定热点、按需进行编译，不代表：

- 整个应用都已 AOT；
- 每条规则一定仍与当前 DEX 匹配；
- 静态初始化代码不再执行；
- 类加载、验证和页面创建成本全部消失；
- 所有安装渠道在同一时点完成编译。

Profile 改变的是代码执行前的准备状态。方法内部逻辑仍会执行，I/O、锁和网络仍会等待。

### 1.3 构建到设备的链路

下面按产物形态列出从生成规则到设备编译的各层。AGP 是 Android 构建插件，D8 把 Java/Kotlin 编译结果转换成 DEX，R8 负责代码缩减、混淆和优化：

```text
BaselineProfileRule / 库规则
        ↓
HRF baseline-prof.txt（H/S/P + 类/方法）
        ↓  AGP + D8/R8 重写、合并、编码
APK/AAB 中的 binary baseline.prof
        ↓  Play / package installer / ProfileInstaller
设备 profile
        ↓  install-dm 或后台 dexopt
ART profile-guided 编译产物
```

这张图用于表达分层关系，不是一条适用于所有渠道的严格时间线。Google Play 或支持 DexMetadata（DM，随 APK 交付的 DEX 元数据）的安装器可以提供 reference profile（作为编译基准安装的 profile），并以 `install-dm` 等原因触发编译；ProfileInstaller 则把包内规则写入设备可持续更新的 current profile，等待后台 `dexopt`。`dexopt` 是系统对 DEX 做验证、编译和优化的过程。

图中的每一层都需要单独验证。源码里有 `baseline-prof.txt`，不代表 release 包一定携带；包内有 `baseline.prof`，也不代表设备已经完成由 profile 指导的编译。

## 2. 四种 profile 不要混用

| 类型 | 生产者 | 主要用途 | 可用边界 |
| --- | --- | --- | --- |
| Baseline Profile | 应用/库作者与 CI | 引导 ART 编译常用路径 | Android 7 / API 24+ |
| Startup Profile | 应用的启动生成场景 | 构建期优化 DEX 布局 | 依赖 AGP/R8 工具链 |
| Cloud Profile | Google Play 聚合真实使用数据 | 补充安装/更新时的 PGO | Android 9 / API 28+、Play 渠道 |
| 本地运行时 profile | 单台设备的 ART/JIT | 随用户行为更新热点 | 使用后逐步积累 |

CI 是持续集成系统，用来在每次代码变化后自动构建和测试。Baseline Profile 由团队选择 CUJ（Critical User Journey，关键用户路径），能随新版本交付；Cloud Profile 要等待真实数据聚合，官方文档给出的传播时间是数小时到数天，并要求应用有足够用户规模。PGO（Profile-Guided Optimization）表示用运行行为 profile 指导编译优化，两种 profile 会共同影响 Play 用户的编译状态。

Startup Profile 是 Baseline Profile 的启动子集，但消费方不同：Baseline Profile 给 ART，Startup Profile 给构建工具做 DEX 布局。它们可以来自同一生成脚本，验证方法不能互换。

## 3. 什么场景可能受益

TTID 表示首帧首次显示所需时间，TTFD 表示应用达到完整可用状态所需时间。优先检查这些现象：

- 新装/升级后的启动明显慢于稳定使用后的启动；
- Trace 中启动阶段有解释执行、JIT 编译、类加载和大量首次执行；
- Compose、反射路由或大依赖链带来较多关键方法首次执行；
- 首次进入高频页面时出现代码执行相关抖动；
- 库升级后 profile 覆盖率明显变化。

这些现象通常不由 profile 解决：

- 主线程同步文件或数据库升级；
- Binder 跨进程调用或锁等待；
- 网络结果成为 TTID/TTFD 硬依赖；
- 图片解码、复杂布局或过多 Compose 组合（根据状态构建界面树的过程）；
- SDK 在 Provider/Application 中执行重活；
- Main（UI 主线程）/RenderThread（负责部分渲染工作的线程）被大量后台任务抢占。

先用 [启动完整路径分析](./01-startup-analysis.md)确认瓶颈。Baseline Profile 应与初始化、I/O 和渲染修复一同评估，不能用“后几次会变快”掩盖首次运行的问题。

## 4. 生成：场景决定 profile 质量

### 4.1 使用 Baseline Profile Gradle Plugin

推荐用 Android Studio 的 Baseline Profile Generator 模板或 Baseline Profile Gradle Plugin。generator module 是一个独立的设备测试模块，负责启动目标应用并采集规则；应用模块通过下面的依赖消费它：

```kotlin
plugins {
    id("com.android.application")
    id("androidx.baselineprofile")
}

dependencies {
    baselineProfile(project(":baseline-profile"))
}
```

插件负责把构建变体（variant）与生成任务关联起来，合并规则，并按 release 产物的混淆结果重写类名和方法名。具体插件版本应与项目 AGP、Macrobenchmark 和 ProfileInstaller 组成经过验证的工具链；升级其中一项后需要重新生成和测量。

### 4.2 启动场景要显式加入 Startup Profile

下面的 generator 覆盖从桌面图标进入首页的路径，并明确把该场景加入 Startup Profile：

```kotlin
@LargeTest
@RunWith(AndroidJUnit4::class)
class BaselineProfileGenerator {
    @get:Rule
    val rule = BaselineProfileRule()

    @Test
    fun launcherToHome() = rule.collect(
        packageName = TARGET_PACKAGE,
        includeInStartupProfile = true,
    ) {
        pressHome()
        startActivityAndWait()

        check(
            device.wait(
                Until.hasObject(By.res(TARGET_PACKAGE, "home_list")),
                5_000,
            )
        )
    }
}
```

`includeInStartupProfile = true` 只应用于初始显示必经的启动场景。滚动、详情、搜索等 CUJ 可以进入 Baseline Profile，但不能因为它们常用就全部进入 Startup Profile，否则会扩大启动 DEX 布局范围。

### 4.3 覆盖所有主要启动入口

只有从桌面图标（launcher）启动的场景还不够时，应增加独立且确定的场景：

- 已登录与未登录；
- deep link（从网页或其他应用直达指定页面）到高频页面；
- 通知点击；
- 恢复保存状态；
- Compose 首次进入；
- 动态特性模块已安装/未安装的允许路径；
- 主要 product flavor，例如 free/paid 或不同渠道配置。

每个场景都要固定账号、隐私弹窗、远程配置、语言、数据和网络响应。`waitForIdle()` 只说明界面线程暂时空闲，不能证明目标内容正确；测试应断言业务 UI 或状态。脚本走错页面时应立即失败，避免把错误路径写入 profile。

### 4.4 启动之外的 CUJ

高频滚动、导航和交互可用另一条 `collect` 场景生成 Baseline Profile 规则，并保持 `includeInStartupProfile = false`。这样 ART 仍可编译相关方法，R8 不会把它们当成启动布局依据。

库可以随 AAR（Android Library Archive，Android 库包）提供 Baseline Profile，应用构建时会合并这些规则。应用仍应检查最终规则和包体；库作者不知道宿主的启动入口，Startup Profile 不能由库替宿主贡献。

## 5. 生成产物要可复现

Baseline Profile Gradle task 的保存位置由 `saveInSrc` 决定。设为 `true` 时，生成结果会复制到 `src/<variant>/generated/baselineProfiles` source set；source set 是只属于某个构建变体的一组源码和资源。设为 `false` 时，结果只保留在 `build` 目录的中间产物中。团队可以选择：

- 将生成规则纳入版本控制并审查每次差异；
- 或由固定设备镜像与工具链在 CI 重建，保存产物和差异报告。

两种方式都要记录：

- generator 代码与测试数据版本；
- 设备/API 和 Macrobenchmark 版本；
- AGP/R8/ProfileInstaller 版本；
- 目标构建变体与应用源码版本；
- 生成规则增删数量和异常大范围变化。

模板中的 profile 生成变体通常不做混淆和优化，release 则开启 R8。Baseline Profile Plugin 与 AGP 负责把可读规则重写为优化后 release DEX 中的类名和方法名。绕开插件手工复制时，签名可能不匹配。

不要把一次 generator 成功等同于 profile 正确。规则异常变大、入口漏掉、测试误入错误页，都需要在构建阶段阻止发布。

## 6. 检查 APK/AAB

[官方调试指南](https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles) 给出的关键位置是：

- APK：`/assets/dexopt/baseline.prof`
- AAB：`/BUNDLE-METADATA/com.android.tools.build.profiles/baseline.prof`

APK 是可安装包，AAB 是交给应用商店生成设备专用 APK 的发布包。下面的命令用于确认二者是否包含二进制 profile：

```bash
unzip -l app-release.apk \
  | rg 'assets/dexopt/baseline\\.prof$'

unzip -l app-release.aab \
  | rg 'BUNDLE-METADATA/com\\.android\\.tools\\.build\\.profiles/baseline\\.prof$'
```

没有输出时，检查构建变体、source set、generator 依赖和 AGP 任务。编译后的 `baseline.prof` 必须小于 1.5 MB；这个限制不适用于通常更大的 HRF 文本规则。工具链还可能打包 `baseline.profm`，它保存 profile 格式转换所需的元数据，以便 ProfileInstaller 适配不同 ART 版本。验收仍要按当前 AGP 与目标设备格式进行，不能只凭扩展名推断可用性。

库 profile 也要在最终应用产物中验证。AAR 自身有规则，不能证明宿主所用 AGP 已正确消费。

## 7. 安装与编译状态

### 7.1 渠道决定时机

Android 7～8.1 主要依靠 `ProfileInstaller` 在首次运行后写入 current profile，再等待后台 dexopt。Android 9+ 可以由 Google Play 或支持 DexMetadata 的 package installer 交付 reference profile。当前官方调试文档指出，Google Play 的 Baseline Profile 编译可能发生在后台设备更新，不能假定 APK 安装命令返回时已经完成。

侧载、第三方商店、Android Studio、Gradle 和 Play 的行为不能互相代替。其他安装工具通常由 ProfileInstaller 把规则排入下一次后台 dexopt；非 Play 渠道也可能要等设备空闲时才获得编译收益。AGP 8.4+ 会让 Android Studio 或 Gradle Wrapper 安装的本地不可调试构建（non-debuggable）自动执行设备端编译，但发布验收仍要覆盖目标渠道。

### 7.2 `ProfileVerifier` 能说明什么

[`ProfileVerifier`](https://developer.android.com/reference/androidx/profileinstaller/ProfileVerifier)可以报告：

- APK 内没有嵌入 profile；
- 包内有 profile，但设备尚未安装可用 profile；
- profile 已入队等待编译；
- 已按 profile 编译；
- 已使用不完全匹配的 profile 编译；
- 不支持的 API 或缓存/包错误。

`RESULT_CODE_ERROR_NO_PROFILE_EMBEDDED` 表示包内没有规则，`RESULT_CODE_NO_PROFILE` 则可能表示包内有规则，但 ProfileInstaller 没有运行或设备尚无已安装 profile。`ProfileVerifier` 不能区分当前编译使用的是 Baseline Profile 还是 Cloud Profile。`RESULT_CODE_COMPILED_WITH_PROFILE` 说明应用已有可用的 profile 引导编译状态，不说明全部代码已经 AOT。

`ProfileVerifier` 支持 API 28～29 和 API 31+；API 27 以下以及 API 30 都会返回 `RESULT_CODE_ERROR_UNSUPPORTED_API_VERSION`，API 30 的原因也是 reference profile 目录权限限制。`writeProfileVerification()` 会执行 I/O，应在后台线程调用。若关闭 `ProfileInstallerInitializer`，需要在启动数秒后手动调用该方法，否则 `getCompilationStatusAsync()` 返回的 Future（异步结果对象）可能一直等待或超时。

### 7.3 `dumpsys package dexopt`

下面的命令用于线下查看目标包的 compiler filter（当前编译策略）与 reason（触发原因）：

```bash
adb shell dumpsys package dexopt \
  | rg -A 4 'com\\.example\\.app'
```

`status=speed-profile` 表示存在由 profile 指导的编译产物；`reason=install-dm`、`bg-dexopt` 或 `cmdline` 分别表示安装期 DexMetadata、后台优化或命令行触发。它仍不能逐方法证明哪条规则命中。

需要手工验证编译器能否消费已经安装的 profile 时，可使用：

```bash
adb shell cmd package compile \
  -f -m speed-profile com.example.app
```

该命令不会从 APK 中主动取出一份尚未写入设备 profile 目录的规则。Macrobenchmark 会按 `CompilationMode` 准备 profile 和编译状态，自动化性能实验优先使用它。

## 8. 用 Macrobenchmark 测 profile 差值

### 8.1 固定编译模式

下面的两个测试使用同一应用、入口和场景，只改变编译模式：

```kotlin
@LargeTest
@RunWith(AndroidJUnit4::class)
class BaselineProfileStartupBenchmark {
    @get:Rule
    val rule = MacrobenchmarkRule()

    @Test
    fun noPreCompilation() = measure(
        CompilationMode.None(),
    )

    @Test
    fun baselineProfile() = measure(
        CompilationMode.Partial(
            baselineProfileMode = BaselineProfileMode.Require,
        ),
    )

    private fun measure(mode: CompilationMode) = rule.measureRepeated(
        packageName = TARGET_PACKAGE,
        metrics = listOf(StartupTimingMetric()),
        compilationMode = mode,
        startupMode = StartupMode.COLD,
        iterations = 10,
        setupBlock = {
            pressHome()
        },
    ) {
        startActivityAndWait()
    }
}
```

`BaselineProfileMode.Require` 在产物缺少 profile 时让测试失败，避免 `Partial()` 静默换成没有 Baseline Profile 的条件。官方 API 还要求测试 APK 包含 ProfileInstaller，并由 AGP 7.0+ 打包 Baseline Profile。十次迭代只是起点，应按设备噪声和希望识别的最小回归幅度决定样本量。

### 8.2 正确解释 `None` 与 `Partial`

`CompilationMode.None()` 构造无预编译的受控状态，适合测量 profile 能提供的本地差值。它不能代表线上所有“未配置 Baseline Profile”的用户，因为线上还可能存在 Cloud Profile、本地 JIT profile 或后台 dexopt。

`CompilationMode.Partial(...Require)` 测量 Baseline Profile 已准备并参与部分编译的状态。`CompilationMode.Full()` 可作为全部代码编译后的实验上界，不代表生产安装常态。

### 8.3 同时观察这些指标

- TTID 与 TTFD；
- 首屏和高频 CUJ 的 FrameTiming 与 Jank；Jank 指一帧错过显示期限造成的卡顿；
- 主线程 Running（正在 CPU 上执行）/Runnable（可以执行但在等 CPU）、类加载、JIT 和垃圾回收；
- 安装/编译状态与产物；
- APK/AAB 大小和编译产物带来的设备磁盘成本；
- 崩溃、ANR（应用无响应）与功能正确性。

如果 `None` 与 `Partial` 几乎相同，打开 Trace 判断：

- 测试产物是否带 profile；
- Profile 是否覆盖当前入口；
- R8 重写后规则是否匹配；
- 关键路径是否已经转移到 I/O、锁、Binder 或渲染；
- 测试是否被缓存、弹窗或错误页面污染。

## 9. Cloud Profile 与线上验证

Cloud Profile 由 Google Play 聚合用户设备上的 ART profile，并在后续安装或更新流程中提供给 Android 9+ 用户。它有三个限制：

1. 只适用于 Google Play 交付链路；
2. 新版本发布后需要数小时到数天积累；
3. 用户规模不足时覆盖有限。

Baseline Profile 负责团队可控的首批新装/升级性能，Cloud Profile 随真实使用补充未覆盖热点。非 Play 渠道需要验证 package installer 与 ProfileInstaller 的具体路径。

Profile 与 APK 紧密绑定，同一版本里的运行时 A/B 开关无法移除已经打包或编译的 profile。线上评估通常使用：

- 只改变 profile 的小流量受控版本；
- 相邻版本的专项小版本发布，只改变 profile；
- 发布早期、Cloud Profile 尚未充分传播时，按安装来源和安装时间分组的数据；
- 本地 `None`/`Partial` Macrobenchmark 作为受控对照证据。

对照组必须控制代码、资源、服务端配置和用户入口。随着 Cloud Profile 传播，两组编译状态可能继续变化，因此报告要记录版本发布时间与安装来源。

## 10. Startup Profile 与 DEX Layout

### 10.1 构建期职责

[Startup Profile](https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations) 让 R8/D8 调整类和方法在 DEX 文件中的顺序与分布，把初始显示所需代码优先放进启动 DEX 或相邻区域。这样可以提高加载局部性，也就是一次文件映射或读取更容易覆盖接下来要执行的代码。它不会生成另一套 ART 编译状态，也不能替代 Baseline Profile。

使用要点：

- 启动 generator 设置 `includeInStartupProfile = true`；
- release 开启 R8 与优化；
- AGP 8.1～8.2 显式启用 DEX layout；
- AGP 8.3+默认启用相关优化；
- 不把非启动 CUJ 全塞进 Startup Profile；
- 所有主要启动入口都由应用 generator 覆盖。

启用 `saveInSrc` 时，生成后的规则通常位于 `src/<variant>/generated/baselineProfiles/startup-prof.txt`，由 AGP 自动消费。当前官方文档明确说明，库可以贡献 Baseline Profile，不能替宿主贡献 Startup Profile。库不知道宿主的入口、主 DEX 容量和完整调用路径。

### 10.2 验证方式

Startup Profile 在构建时应用，APK/AAB 中没有供 ART 使用的独立 `startup.prof`。验证方式包括：

- AGP 8.8+检查 AAB 中 `r8.json` 的 startup DEX 标记；
- 用 APK Analyzer 检查 `classes.dex` 是否包含主要启动类；
- 比较 DEX 数量、布局和 page fault；page fault 表示所需内存页尚未驻留，系统需要把对应文件页载入内存；
- 用同编译模式 Macrobenchmark 比较 TTID/TTFD。

不能把收益表述成“类靠近就一定命中 CPU cache”。这里优化的是 DEX 文件布局和读取局部性，运行时结果仍受设备、文件映射、编译状态与代码路径影响。

### 10.3 证明 release 产物保留了布局

验证不能停在仓库中存在 `startup-prof.txt`。应逐层回答生成、消费和发布产物是否一致：

| 证据 | 能证明什么 | 不能证明什么 |
| --- | --- | --- |
| `startup-prof.txt` 及其差异 | generator 采到了哪些启动规则 | R8 已消费规则 |
| release 的 R8 配置与构建日志 | 构建具备 DEX layout 条件 | 最终 DEX 未被后处理改写 |
| APK Analyzer 中的 `classes.dex` | 关键启动类实际位于哪个 DEX | 设备端已经按 profile 编译 |
| AAB 的 `BUNDLE-METADATA/com.android.tools/r8.json` | 哪些 DEX 被标记为 startup DEX | metadata 一定对应最终文件 |
| metadata checksum 与 DEX SHA-256 | R8 后的 DEX 没有被加固、插桩或重打包悄悄替换 | 布局一定带来可测收益 |

checksum 是用于判断文件内容是否变化的摘要。AGP 8.8+ 可以从 AAB 的 `r8.json` 构建元数据中检查至少一个 DEX 是否带有 `"startup": true`，并将其中 checksum 与包内对应 DEX 的 SHA-256 摘要对齐。两者不一致时，应先定位 R8 之后的处理步骤，不能依据旧元数据宣称发布包保留了布局。表中的“加固”指 R8 后对应用包追加保护处理，“插桩”指向 DEX 插入监控或统计代码。

主 DEX 容量也是约束。规则过宽时，初始显示以外的 CUJ 会挤占 `classes.dex`，必要的启动代码反而溢出。单 DEX 应用因布局优化变为两个 DEX 不一定是回归：构建工具可能把启动代码集中在主 DEX，并把非启动代码移到后续 DEX。判断依据应是启动类分布、R8 诊断和测量结果，不能只看 DEX 个数。

### 10.4 用单变量 A/B 隔离布局收益

DEX layout A/B 的源码、资源、R8 规则、签名配置、Baseline Profile、安装步骤和设备端 `CompilationMode` 必须一致，唯一变量是是否向 D8/R8 提供 Startup Profile。若一组同时移除 Baseline Profile，测到的差异会混合 ART 编译和 DEX 布局，无法解释各自贡献。

实验至少记录 TTID、TTFD、P50/P90/P95、数据波动范围和失败样本，并用 Perfetto 核对。P50 是中位数，P90/P95 分别表示 90%/95% 的样本不超过该值：

- DEX 映射、文件读取和缺页次数是否减少且趋于稳定；
- 类加载区间是否缩短；
- 两组 JIT/AOT 状态是否一致；
- Binder、SQLite、锁、网络、资源解码是否掩盖布局收益；
- 反射、动态 DEX 或条件分支是否让关键代码没有进入规则。

杀进程后的冷启动不代表设备 page cache 也处于冷态。page cache 是内核缓存的文件页，应用进程退出后仍可能保留；除非实验能重复控制存储冷态，否则首轮结果不能直接解释成稳定的 DEX I/O 收益。

### 10.5 常见失效模式

- **规则过宽**：主 DEX 接近容量上限，非首屏 CUJ 挤占布局预算；缩小到初始显示路径。
- **生成环境漂移**：弹窗、实验、账号和网络分支让同一源码版本产生不同规则；固定测试环境并审查差异。
- **构建后改写 DEX**：`r8.json` checksum 与最终 DEX 不一致；修复加固、插桩或重打包链路。
- **编译状态不一致**：实验组的 compiler filter 不同；固定编译模式后再比较布局。
- **瓶颈不在 DEX**：Trace 显示主要时间落在 Binder、数据库、锁或网络；保留 Profile，同时治理当前关键路径。

## 11. 维护与回归

这些变化应触发 profile 复核：

- 启动 Activity、deep link、导航或登录流程改变；
- Compose、路由、DI（依赖注入）、数据库或大 SDK 升级；
- 包名、模块、动态特性、product flavor 或 ABI（应用二进制接口）改变；
- R8/AGP/Kotlin/Compose 编译器升级；
- `reportFullyDrawn()` 完成条件改变；
- 新增高频 CUJ 或删除旧功能；
- profile 规则数量、大小或覆盖率异常变化。

CI 至少执行：

1. generator 场景断言；
2. profile 规则差异与大小检查；
3. release APK/AAB profile 路径检查；
4. `CompilationMode.Partial(BaselineProfileMode.Require)` 基准；
5. `None` 对照与回归阈值；
6. 选定设备档位的 TTID/TTFD 和帧结果归档。

当回归来自 I/O、锁、网络或任务编排时，回到 [启动任务编排](./02-startup-framework.md)和 [ContentProvider 启动治理](./03-contentprovider-optimization.md)。Profile 是编译侧工具，不能替业务关键路径做取舍。

## 检查清单

- [ ] 生成工具链、设备/API、构建变体和源码版本可追溯。
- [ ] launcher、deep link、登录态等主要入口有确定脚本。
- [ ] 只有初始显示场景进入 Startup Profile。
- [ ] 应用和库 Baseline Profile 已在最终 release 合并。
- [ ] APK/AAB 中存在目标构建变体的 `baseline.prof`。
- [ ] 安装渠道、ProfileInstaller 和编译状态已分别验证。
- [ ] Macrobenchmark 显式使用 `BaselineProfileMode.Require`。
- [ ] `None`/`Partial` 结果在相同设备与数据条件下比较。
- [ ] TTID、TTFD、帧、稳定性与功能同时通过。
- [ ] Startup Profile 的 DEX 布局用构建产物和 Trace 验证。

## 参考资料

- [Baseline Profiles 概览](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [创建 Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile)
- [配置 Baseline Profile 生成](https://developer.android.com/topic/performance/baselineprofiles/configure-baselineprofiles)
- [调试 Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles)
- [`ProfileVerifier` API](https://developer.android.com/reference/androidx/profileinstaller/ProfileVerifier)
- [`CompilationMode.Partial` API](https://developer.android.com/reference/kotlin/androidx/benchmark/macro/CompilationMode.Partial)
- [Startup Profile 与 DEX layout](https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations)
- [确认 Startup Profile 优化](https://developer.android.com/topic/performance/baselineprofiles/confirm-startup-profiles)
- [AOSP Android 17 `profman`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/profman/profman.cc)
- [AOSP Android 17 `dex2oat`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/dex2oat/dex2oat.cc)
