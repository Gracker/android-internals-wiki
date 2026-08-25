---
title: Baseline、Startup 与 Cloud Profile 编译优化
chapter: '21.4'
section: '21.4'
status: finalized
applicable_versions: Android 7 (API 24) - Android 17 (API 37)
last_verified: '2026-08-14'
last_verified_against: Current Android Developers Baseline/Startup Profile, ProfileVerifier and Macrobenchmark docs; AOSP android-17.0.0_r1 art/profman + art/dex2oat
confidence: medium-high
sources:
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/overview
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles
- type: official
  path: https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/confirm-startup-profiles
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/configure-baselineprofiles
- type: official
  path: https://developer.android.com/reference/androidx/profileinstaller/ProfileVerifier
- type: aosp
  path: art/profman/profman.cc
- type: aosp
  path: art/dex2oat/dex2oat.cc
- type: clippings-structure
  path: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md
- type: clippings-structure
  path: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md
- type: official
  path: https://source.android.com/docs/core/runtime/configure
- type: official
  path: https://source.android.com/docs/core/runtime/configure/art-service
- type: aosp
  path: frameworks/base/core/java/android/content/pm/dex/DexMetadataHelper.java
- type: aosp
  path: frameworks/native/cmds/installd/dexopt.cpp
- type: aosp
  path: frameworks/base/core/java/android/content/pm/PackageManager.java
- type: aosp
  path: art/libartservice/service/java/com/android/server/art/PrimaryDexopter.java
- type: aosp
  path: art/libartservice/service/java/com/android/server/art/DexMetadataHelper.java
- type: clippings-structure
  path: Clippings/Android 性能优化 - 原理：重新认识 APK 安装包.md
tags:
- baseline-profile
- aot
- dex-layout
- macrobenchmark
- startup
- art
- dexopt
- cloud-profile
related_chapters:
- '21.1'
- '1.5'
- '22.10'
- '8.2'
consolidated_from:
- src/part5-app/ch21-startup/12-startup-profile-dex-layout.md
- src/part5-app/ch21-startup/09-startup-case-studies.md#案例三
- src/part5-app/ch21-startup/04-baseline-profile-practice.md
- src/part5-app/ch21-startup/10-cloud-profile-dm-install-compile.md
- src/part2-performance/ch08-responsiveness/05-baseline-profiles.md
- src/part3-tools/ch17-apm/07-jetpack-benchmark-baseline-profiles.md#profile-generation
pipeline_stage: finalized
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_consolidated_at: '2026-08-24'
---

# Baseline、Startup 与 Cloud Profile 编译优化

Baseline Profile 和 Startup Profile 由应用构建流程提供热路径，Cloud Profile 由分发侧根据真实使用生成，DM 文件把 Profile 随安装包交付给 ART。最终收益取决于安装后编译状态和代码版本匹配。

## 应用构建侧：生成、打包与基准验证

### 范围

Baseline Profile 解决的是代码在用户设备上“何时以什么编译状态运行”。ART 是 Android Runtime，负责执行 DEX 字节码；DEX 是 APK 中承载应用字节码的文件格式。没有预编译时，ART 可以先解释执行代码，再由 JIT（Just-In-Time）在运行中编译热点；AOT（Ahead-Of-Time）则在代码运行前完成编译。Baseline Profile 可以让关键路径更早获得合适的编译状态，却不能消除磁盘、网络、Binder、锁等待、业务初始化或首屏布局工作。

平台源码锚点为 Android 17 / API 37 / `android-17.0.0_r1`。截至 2026-08-14，官方列出的最低推荐稳定组合是 AGP 8.0.0、Macrobenchmark 1.4.1 和 ProfileInstaller 1.4.1；Android Studio 的 Baseline Profile Generator 模板和 Startup Profile 建议使用 AGP 8.2 以上。AGP、Macrobenchmark、ProfileInstaller 和 Google Play 各自演进，项目仍需固定一组经过验证的版本并写入实验记录。

这里还要划清两条相邻但不同的优化链路。Baseline/Startup Profile 只处理由 ART 管理的 DEX 代码；[AutoFDO](../../part4-system/ch18-aosp/04-autofdo-feedback-directed-optimization.md) 用采样或硬件分支轨迹指导 LLVM/Clang 优化 native 可执行文件和共享库。OEM dexpreopt 则发生在系统镜像构建阶段，处理 boot classpath、`system_server`、系统组件和预装 APK。预装应用可能同时受三者影响，但输入数据、消费者、产物位置和验证工具不能互换。

### 1. Baseline Profile 是编译提示

#### 1.1 Profile 规则包含什么

Human Readable Format（HRF，可读文本格式）用类名和方法签名记录需要优化的代码。方法规则前可带：

- `H`：Hot，运行中频繁使用的方法；
- `S`：Startup，启动阶段使用的方法；
- `P`：Post-startup，启动后使用的方法。

构建工具会把应用与依赖库的规则合并，按 release 产物的混淆和优化结果重写，再生成 ART 可消费的紧凑二进制 profile。二进制规则会关联具体 APK 中的 DEX 标识与校验信息，因此旧版本 profile 不能直接套到新 APK。

#### 1.2 Android 17 上的 ART 关系

Android 17 ART 的 [`profman`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/profman/profman.cc) 负责 profile 处理与合并，`dex2oat` 根据 compiler filter 和 profile 选择编译工作；源码入口见 [`dex2oat.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/dex2oat/dex2oat.cc)。compiler filter 是 ART 的编译策略名称，用来决定编译范围和优化程度。

`speed-profile` 表示由 profile 指定热点、按需进行编译，不代表：

- 整个应用都已 AOT；
- 每条规则一定仍与当前 DEX 匹配；
- 静态初始化代码不再执行；
- 类加载、验证和页面创建成本全部消失；
- 所有安装渠道在同一时点完成编译。

Profile 改变的是代码执行前的准备状态。方法内部逻辑仍会执行，I/O、锁和网络仍会等待。

#### 1.3 构建到设备的链路

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

### 2. 四种 profile 不要混用

| 类型 | 生产者 | 主要用途 | 可用边界 |
| --- | --- | --- | --- |
| Baseline Profile | 应用/库作者与 CI | 引导 ART 编译常用路径 | Android 7 / API 24+ |
| Startup Profile | 应用的启动生成场景 | 构建期优化 DEX 布局 | 依赖 AGP/R8 工具链 |
| Cloud Profile | Google Play 聚合真实使用数据 | 补充安装/更新时的 PGO | Android 9 / API 28+、Play 渠道 |
| 本地运行时 profile | 单台设备的 ART/JIT | 随用户行为更新热点 | 使用后逐步积累 |

CI 是持续集成系统，用来在每次代码变化后自动构建和测试。Baseline Profile 由团队选择 CUJ（Critical User Journey，关键用户路径），能随新版本交付；Cloud Profile 要等待真实数据聚合，官方文档给出的传播时间是数小时到数天，并要求应用有足够用户规模。PGO（Profile-Guided Optimization）表示用运行行为 profile 指导编译优化，两种 profile 会共同影响 Play 用户的编译状态。

Startup Profile 是 Baseline Profile 的启动子集，但消费方不同：Baseline Profile 给 ART，Startup Profile 给构建工具做 DEX 布局。它们可以来自同一生成脚本，验证方法不能互换。

Android 7 / API 24 是混合执行、JIT、本地 profile 与后台 profile-guided dexopt 协作的运行时边界；Android 9 / API 28 才增加 Google Play Cloud Profile。因此 Android 7～8.1 的包内 Baseline Profile 通常要由 ProfileInstaller 写入 current profile 后等待后台编译，而 Play 用户也不能仅凭安装完成就假定 Cloud/Baseline Profile 已经变成 `speed-profile` 产物。

### 3. 什么场景可能受益

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

先用 [启动完整路径分析](01-app-startup-path-monitoring.md)确认瓶颈。Baseline Profile 应与初始化、I/O 和渲染修复一同评估，不能用“后几次会变快”掩盖首次运行的问题。

### 4. 生成：场景决定 profile 质量

#### 4.1 使用 Baseline Profile Gradle Plugin

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

这条流水线有三个明确角色，模块边界比“把规则文件复制到 app”更重要：

| 角色 | 典型模块 | 负责什么 | 不负责什么 |
|---|---|---|---|
| producer | 独立 `com.android.test` 的 `:baseline-profile` | 在受控设备上驱动 CUJ，输出 HRF 规则 | 不承载生产业务代码 |
| consumer | 最终 `:app` | 合并应用与依赖库规则，由 R8 按 release 符号重写并打包 | 不用生成 variant 的未混淆 DEX 代替发布 DEX |
| library | AAR 与 sample app | 通过真实公开 API 生成并过滤本库规则 | 不知道宿主启动入口，不能贡献最终 Startup Profile |

producer 的生成 variant 应保持 `debuggable=false`、`profileable=true`、不混淆且不优化；最终 release 应启用 R8。API 33+ 可在非 root 设备生成规则，API 28～32 需要 rooted 环境；生成环境只决定能否收集，收益结论仍要回到目标物理设备和 release 类产物。

#### 4.2 启动场景要显式加入 Startup Profile

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
        strictStability = true,
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

`strictStability = true` 会在规则稳定性检查失败时让采集失败，但它不能代替页面就绪和业务数据断言。

`includeInStartupProfile = true` 只应用于初始显示必经的启动场景。滚动、详情、搜索等 CUJ 可以进入 Baseline Profile，但不能因为它们常用就全部进入 Startup Profile，否则会扩大启动 DEX 布局范围。

#### 4.3 覆盖所有主要启动入口

只有从桌面图标（launcher）启动的场景还不够时，应增加独立且确定的场景：

- 已登录与未登录；
- deep link（从网页或其他应用直达指定页面）到高频页面；
- 通知点击；
- 恢复保存状态；
- Compose 首次进入；
- 动态特性模块已安装/未安装的允许路径；
- 主要 product flavor，例如 free/paid 或不同渠道配置。

每个场景都要固定账号、隐私弹窗、远程配置、语言、数据和网络响应。`waitForIdle()` 只说明界面线程暂时空闲，不能证明目标内容正确；测试应断言业务 UI 或状态。脚本走错页面时应立即失败，避免把错误路径写入 profile。

#### 4.4 启动之外的 CUJ

高频滚动、导航和交互可用另一条 `collect` 场景生成 Baseline Profile 规则，并保持 `includeInStartupProfile = false`。这样 ART 仍可编译相关方法，R8 不会把它们当成启动布局依据。

库可以随 AAR（Android Library Archive，Android 库包）提供 Baseline Profile，应用构建时会合并这些规则。应用仍应检查最终规则和包体；库作者不知道宿主的启动入口，Startup Profile 不能由库替宿主贡献。

### 5. 生成产物要可复现

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

### 6. 检查 APK/AAB

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

### 7. 安装与编译状态

#### 7.1 渠道决定时机

Android 7～8.1 主要依靠 `ProfileInstaller` 在首次运行后写入 current profile，再等待后台 dexopt。Android 9+ 可以由 Google Play 或支持 DexMetadata 的 package installer 交付 reference profile。当前官方调试文档指出，Google Play 的 Baseline Profile 编译可能发生在后台设备更新，不能假定 APK 安装命令返回时已经完成。

侧载、第三方商店、Android Studio、Gradle 和 Play 的行为不能互相代替。其他安装工具通常由 ProfileInstaller 把规则排入下一次后台 dexopt；非 Play 渠道也可能要等设备空闲时才获得编译收益。AGP 8.4+ 会让 Android Studio 或 Gradle Wrapper 安装的本地不可调试构建（non-debuggable）自动执行设备端编译，但发布验收仍要覆盖目标渠道。

#### 7.2 `ProfileVerifier` 能说明什么

[`ProfileVerifier`](https://developer.android.com/reference/androidx/profileinstaller/ProfileVerifier)可以报告：

- APK 内没有嵌入 profile；
- 包内有 profile，但设备尚未安装可用 profile；
- profile 已入队等待编译；
- 已按 profile 编译；
- 已使用不完全匹配的 profile 编译；
- 不支持的 API 或缓存/包错误。

`RESULT_CODE_ERROR_NO_PROFILE_EMBEDDED` 表示包内没有规则，`RESULT_CODE_NO_PROFILE` 则可能表示包内有规则，但 ProfileInstaller 没有运行或设备尚无已安装 profile。`ProfileVerifier` 不能区分当前编译使用的是 Baseline Profile 还是 Cloud Profile。`RESULT_CODE_COMPILED_WITH_PROFILE` 说明应用已有可用的 profile 引导编译状态，不说明全部代码已经 AOT。

`ProfileVerifier` 支持 API 28～29 和 API 31+；API 27 以下以及 API 30 都会返回 `RESULT_CODE_ERROR_UNSUPPORTED_API_VERSION`，API 30 的原因也是 reference profile 目录权限限制。`writeProfileVerification()` 会执行 I/O，应在后台线程调用。若关闭 `ProfileInstallerInitializer`，需要在启动数秒后手动调用该方法，否则 `getCompilationStatusAsync()` 返回的 Future（异步结果对象）可能一直等待或超时。

#### 7.3 `dumpsys package dexopt`

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

### 8. 用 Macrobenchmark 测 profile 差值

#### 8.1 固定编译模式

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

#### 8.2 正确解释 `None` 与 `Partial`

`CompilationMode.None()` 构造无预编译的受控状态，适合测量 profile 能提供的本地差值。它不能代表线上所有“未配置 Baseline Profile”的用户，因为线上还可能存在 Cloud Profile、本地 JIT profile 或后台 dexopt。

`CompilationMode.Partial(...Require)` 测量 Baseline Profile 已准备并参与部分编译的状态。`CompilationMode.Full()` 可作为全部代码编译后的实验上界，不代表生产安装常态。

#### 8.3 同时观察这些指标

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

### 9. Startup Profile 与 DEX Layout

#### 9.1 构建期职责

[Startup Profile](https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations) 让 R8/D8 调整类和方法在 DEX 文件中的顺序与分布，把初始显示所需代码优先放进启动 DEX 或相邻区域。这样可以提高加载局部性，也就是一次文件映射或读取更容易覆盖接下来要执行的代码。它不会生成另一套 ART 编译状态，也不能替代 Baseline Profile。

使用要点：

- 启动 generator 设置 `includeInStartupProfile = true`；
- release 开启 R8 与优化；
- AGP 8.1～8.2 显式启用 DEX layout；
- AGP 8.3+默认启用相关优化；
- 不把非启动 CUJ 全塞进 Startup Profile；
- 所有主要启动入口都由应用 generator 覆盖。

启用 `saveInSrc` 时，生成后的规则通常位于 `src/<variant>/generated/baselineProfiles/startup-prof.txt`，由 AGP 自动消费。当前官方文档明确说明，库可以贡献 Baseline Profile，不能替宿主贡献 Startup Profile。库不知道宿主的入口、主 DEX 容量和完整调用路径。

#### 9.2 验证方式

Startup Profile 在构建时应用，APK/AAB 中没有供 ART 使用的独立 `startup.prof`。验证方式包括：

- AGP 8.8+检查 AAB 中 `r8.json` 的 startup DEX 标记；
- 用 APK Analyzer 检查 `classes.dex` 是否包含主要启动类；
- 比较 DEX 数量、布局和 page fault；page fault 表示所需内存页尚未驻留，系统需要把对应文件页载入内存；
- 用同编译模式 Macrobenchmark 比较 TTID/TTFD。

不能把收益表述成“类靠近就一定命中 CPU cache”。这里优化的是 DEX 文件布局和读取局部性，运行时结果仍受设备、文件映射、编译状态与代码路径影响。

#### 9.3 证明 release 产物保留了布局

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

#### 9.4 用单变量 A/B 隔离布局收益

DEX layout A/B 的源码、资源、R8 规则、签名配置、Baseline Profile、安装步骤和设备端 `CompilationMode` 必须一致，唯一变量是是否向 D8/R8 提供 Startup Profile。若一组同时移除 Baseline Profile，测到的差异会混合 ART 编译和 DEX 布局，无法解释各自贡献。

实验至少记录 TTID、TTFD、P50/P90/P95、数据波动范围和失败样本，并用 Perfetto 核对。P50 是中位数，P90/P95 分别表示 90%/95% 的样本不超过该值：

- DEX 映射、文件读取和缺页次数是否减少且趋于稳定；
- 类加载区间是否缩短；
- 两组 JIT/AOT 状态是否一致；
- Binder、SQLite、锁、网络、资源解码是否掩盖布局收益；
- 反射、动态 DEX 或条件分支是否让关键代码没有进入规则。

杀进程后的冷启动不代表设备 page cache 也处于冷态。page cache 是内核缓存的文件页，应用进程退出后仍可能保留；除非实验能重复控制存储冷态，否则首轮结果不能直接解释成稳定的 DEX I/O 收益。

#### 9.5 常见失效模式

- **规则过宽**：主 DEX 接近容量上限，非首屏 CUJ 挤占布局预算；缩小到初始显示路径。
- **生成环境漂移**：弹窗、实验、账号和网络分支让同一源码版本产生不同规则；固定测试环境并审查差异。
- **构建后改写 DEX**：`r8.json` checksum 与最终 DEX 不一致；修复加固、插桩或重打包链路。
- **编译状态不一致**：实验组的 compiler filter 不同；固定编译模式后再比较布局。
- **瓶颈不在 DEX**：Trace 显示主要时间落在 Binder、数据库、锁或网络；保留 Profile，同时治理当前关键路径。

### 10. 维护与回归

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

当回归来自 I/O、锁、网络或任务编排时，回到 [启动任务编排](02-startup-task-lazy-concurrency.md)和 [ContentProvider 启动治理](03-contentprovider-multiprocess-startup.md)。Profile 是编译侧工具，不能替业务关键路径做取舍。

### 检查清单

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

## 分发与设备侧：Cloud Profile、DM 与 dexopt

应用构建侧负责生成规则并证明本地收益；分发与设备侧负责回答这些输入是否到达目标 APK、是否被 ART 接受，以及何时形成可用编译产物。Cloud Profile 补充真实用户热路径，DM 只是随 APK 交付元数据的容器，compiler filter 与 reason 才描述设备最终做了什么。

### Profile 在发布后如何生效

上一部分已经完成 Baseline/Startup Profile 的生成、打包与受控基准。本部分只追踪发布后的安装来源、外部 profile、DM、ART Service 与 dexopt 状态；同一条证据不能同时证明“规则打包成功”和“设备已按规则编译”。

先划清收益边界。Profile 可以减少解释器逐条执行代码、JIT（Just-In-Time，运行时即时编译）预热和部分 DEX（Android 字节码文件）读取开销，却不会缩短数据库迁移、网络等待、锁竞争或 SDK 同步初始化。一次冷启动同时包含这些成本，只看总耗时很容易误判。

### 云端 Profile 在启动优化里的位置

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

### DM 文件与 ART 编译模式

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

#### Android 17 的执行链路

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

#### compiler filter 与 compilation reason

这两个字段回答不同问题。compiler filter 是编译器工作到什么程度，compilation reason 是这次工作为什么发生：

- compiler filter 表示“生成了何种编译产物”。
- compilation reason 表示“哪类事件触发了这次 dexopt”，例如安装、后台维护或 shell 命令。

| filter | Android 17 中的含义 | 代价与边界 |
|---|---|---|
| `verify` | 验证 DEX，不生成 AOT 机器码 | CPU、存储成本较低；启动路径更多依赖解释器与 JIT |
| `speed-profile` | 只 AOT 编译有效 profile 选中的方法 | 成本取决于 profile；没有有效 profile 时，实际 filter 会变成 `verify` |
| `speed` | 面向速度 AOT 编译全部方法 | 编译耗时和产物体积更高，不适合作为普通第三方 App 的默认对照目标 |

排查时必须同时记录 requested filter（请求的编译强度）和 actual filter（ART 最终采用的编译强度）。只看到命令参数 `-m speed-profile`，不能证明 profile 已经命中；Android 17 的 `Dexopter.java` 在找不到有效 profile 时会把它改为 `verify`。

### dex2oat、bg-dexopt-job 与空闲编译

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

#### 查看包的 dexopt 状态

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

### Profile 命中率与冷启动收益评估

#### 第一道检查：发布产物里有什么

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

#### 第二道检查：外部 profile 能否被 ART 使用

Android 17 官方 ART Service 文档推荐先清除本地采集的 profile，再强制执行带详细结果的 `speed-profile` 编译。

```bash
adb shell pm art clear-app-profiles com.example.app
adb shell pm compile -m speed-profile -f -v com.example.app
```

第一条命令清除 current profile（ART 当前采集的运行记录）和 reference profile（已合并、供后续编译参考的记录），但保留 Cloud Profile 等 external profile（由 APK 或安装器从外部提供的 profile），也不会删除已有编译产物。第二条命令的判定依据是输出：`actualCompilerFilter=speed-profile` 表示找到了有效 profile；`actualCompilerFilter=verify` 表示没有可用 profile。典型原因包括文件名错误、格式错误和 DEX checksum 不匹配。

这个测试仍不能区分 APK 内嵌 Baseline Profile、相邻 `.prof` 与 `.dm` 中的 profile，因为它们都属于 ART 可选择的外部输入。要区分来源，必须控制安装产物，而不能只看 `actualCompilerFilter`。

#### 第三道检查：构造无 AOT 编译基线

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

#### 三组实验与观测字段

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

#### `ProfileVerifier` 与 Macrobenchmark 的边界

`ProfileVerifier` 是 AndroidX 提供的 profile 状态检查器，适合在 App 或测试代码里确认“是否有 profile、是否已经用 profile 编译、是否排队等待编译、已编译 profile 是否与当前 APK 匹配”。它不能告诉你 ART 使用的是 Baseline Profile 还是 Cloud Profile，也不能替代方法覆盖率与启动耗时测量。

Macrobenchmark 的 `CompilationMode.None`（不预编译）与 `CompilationMode.Partial`（使用 Baseline Profile 做部分预编译）更适合评估 Baseline Profile 的可控收益。官方文档将本地结果视为 profile 可用时的理想场景，并明确指出它不包含生产设备上的 Cloud Profile 影响。验证 Cloud Profile 需要 Play 安装来源、同版本样本分组和足够的观察周期，不能用一次本地 `pm compile` 宣称完成了 Cloud Profile A/B 实验。

### 灰度发布中的 Profile 风险

Profile 是编译输入，覆盖不足会损失收益，覆盖过宽会增加编译时间和产物体积。分批放量（灰度）阶段需要同时看启动、安装/升级与稳定性。

Profile 与 APK 紧密绑定，同一版本里的运行时开关不能移除已经打包或编译的 profile。需要线上对照时，应使用只改变 profile 的小流量受控版本或专项小版本，并在 Cloud Profile 尚未充分传播的发布早期按安装来源、安装时间和编译状态分组。代码、资源、服务端配置与用户入口必须保持一致；否则无法把变化归因给 profile。

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

### 与 Baseline Profile 生成流程衔接

前半篇负责生成和维护 Baseline Profile，发布后则要确认 ART 是否拿到、接受并使用了 profile。两条流程按下面的证据顺序衔接：

1. 21.4 用当前 release 构建生成规则，并通过 Macrobenchmark 验证代表性场景。
2. 检查 APK/AAB 条目、安装来源和每个 APK 各自对应的 `.dm`。
3. 用 `pm art dump` 与 `pm compile -v` 读取 actual filter 和 compilation reason。
4. 用 Perfetto 区分 JIT/类加载成本与业务初始化成本。
5. 按 [21.1 App 启动路径、监控与度量](01-app-startup-path-monitoring.md)的口径，分版本、渠道和设备监控 TTID/TTFD。

ART 编译原理可回看 1.5，冷/温/热启动路径可回看 8.2。若问题已经定位到数据库、网络、锁或 SDK 同步任务，应治理对应任务，不要继续扩大 profile 规则。

### 厂商 ROM 编译策略差异

同一 APK 在不同设备上可能得到不同的编译结果。可变因素包括安装器是否交付 external metadata、系统 build、ART Mainline（可独立更新的 ART 系统模块）版本、`pm.dexopt.<reason>`、dex2oat 并发数与允许使用的 CPU 核心集合、省电状态、温控和存储压力。

一轮跨 ROM 对比应保存以下证据：

1. 设备 build fingerprint（唯一标识系统构建的字符串）、ART 模块版本、ABI 与安装来源；
2. 安装后立即读取的 per-APK filter/reason；
3. 同一自动化脚本采集的启动 trace；固定“启动三次”无法保证样本条件一致；
4. idle/charging 维护窗口前后的 filter/reason；
5. 设备温度、低电量与低存储状态；
6. ROM 的 `pm.dexopt` 与 `dex2oat` 系统属性快照。

厂商对维护窗口和资源策略的修改没有统一公开清单。缺少源码或厂商文档时，应把差异标成设备观测，不能把单台设备的行为写成 Android 17 规范。

### 动态特性模块与 Play 分发

App Bundle 的每个安装单元都要单独检查。Base APK 已按 `speed-profile` 编译，不代表 on-demand feature（按需下载的功能模块）的 split 已安装、具有匹配 metadata 或完成 dexopt。

| 场景 | 需要检查的对象 | 典型信号 |
|---|---|---|
| 安装后打开首页 | base APK、主 ABI | 主进程启动阶段的 filter、JIT 与类加载 |
| 首次进入按需模块 | 新安装的 feature split | split 的 compiler filter、模块入口附近的 JIT 编译 |
| 升级后进入模块 | 新版本 base 与 split | 旧 metadata 是否失效、升级首进是否回退 |
| 热修复后进入模块 | secondary/dynamic DEX | 自定义 ClassLoader、secondary DEX 与 profile 偏离 |

`.dm` 按 APK 文件名匹配，所以验证日志也要按 base/split 和 ABI 拆分。Play 对 Cloud Profile 及 metadata 的交付策略可能变化；若没有当前 Play 文档或实际取得的安装产物，只能确认设备侧怎样消费文件，不能推断服务端一定交付了什么。

### 排查手册

一次完整排查可以按七步进行：

1. 固定 release 产物、设备 build、ART 模块和安装来源。
2. 检查 APK/AAB 中的 Baseline Profile；有外部 `.prof`/`.dm` 时，按 base/split 核对文件名与版本。
3. 安装后立即执行 `pm art dump`，记录每个 APK/ABI 的 filter 与 reason。
4. 清本地 profile 后用 `pm compile -m speed-profile -f -v` 验证外部 profile，读取 actual filter。
5. 用 `pm compile --reset` 建立无 AOT 编译组，再与目标 profile 组、设备稳态组比较。
6. 在 Perfetto 中同时看 `art::jit::*`（ART 的 JIT 时间片段）、类加载、文件缺页和主线程任务。
7. 分批放量数据按版本、渠道、Android 版本和设备分层，联合观察启动、安装/升级、崩溃与 ANR（应用无响应）。

若 trace 的主要耗时来自业务初始化，profile 排查到这里应停止。扩大规则不会缩短任务自身耗时，还可能增加 dex2oat 与存储成本。

## 小结

Profile 优化必须沿“场景生成 → release 打包 → 渠道交付 → ART 接受 → 实际编译状态 → 启动收益”逐层验证。Baseline/Cloud Profile 负责设备端编译输入，Startup Profile 负责构建期 DEX 布局，DM 只是可能承载外部输入的容器；任何一层存在文件并不能替下一层证明已生效。最终结论仍要回到固定编译条件下的 TTID、TTFD、帧和功能验证。

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
