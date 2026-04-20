---
title: Baseline Profiles 与编译优化实践
chapter: '8.7'
section: '8.7'
status: ready-for-review
drafted_date: '2026-04-06'
drafted_by: openclaw-task2a
applicable_versions: Android 9 (API 28) - Android 17 (API 37)
last_verified: '2026-04-14'
last_verified_against: developer.android.com Baseline Profiles docs + profileable docs + AOSP android-17-beta3 cross-check
reviewed_date: '2026-04-20'
reviewed_by: openclaw-task6
task6_result: pass-light-edit
task9_result: "needs-rework"
confidence: medium
sources:
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles
- type: blog
  path: intake/research-feeds/2026-04-06-11-baseline-profiles-compilation-optimization.md
- type: blog
  path: intake/research-feeds/2026-04-04-07-ch08-startup-profiles-dex-layout-optimization.md
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles
- type: official
  path: https://developer.android.com/guide/topics/manifest/profileable-element
tags:
- android
- research
pipeline_stage: "task2b_pending"
task6_state: reviewed
task9_state: "reviewed"
task2b_state: "pending"
task2b_result: fixed
review_round: 2
task9_reviewed_date: "2026-04-20"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-04-20T20:06:23+08:00"
---


# 8.7 Baseline Profiles 与编译优化实践

Android 的 ART 运行时经历了多次编译策略的演变——从 Android 5.0 的全量 AOT 编译，到 Android 7.0 的解释执行 + JIT，再到 Profile-Guided 编译。每次转变都在安装时间、运行性能和存储占用之间做不同的权衡。但有一个问题始终存在：**应用首次安装后的冷启动性能**。

在这个时间窗口内，ART 还没有收集到足够的运行时 profile 数据，无法知道哪些方法是热点。结果是大量关键代码只能解释执行，冷启动速度比经过优化的状态慢 30% 甚至更多。

Baseline Profiles 就是 Google 给出的解决方案：**让开发者在 APK 中预置一份"热点方法清单"，在安装时直接告诉 dex2oat 编译器哪些代码需要优先编译为机器码**。这样即使没有任何用户使用数据，首次启动也能获得接近稳态的性能。

[已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles]

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **Android 7 与 Android 9 的编译时间线要分开写**：[已验证: 1.7 节 + 官方 Baseline Profiles 文档]
  Android 7 引入 JIT、本地 Profile 和后台 `dex2oat`；Android 9 起 Google Play 才能分发 Cloud Profiles。

- 🔹 **HRF 文本、二进制产物、安装后 OAT 目录是三件事**：[已验证: create/debug docs]
  `baseline-prof.txt` 位于 `src/<variant>/generated/baselineProfiles/`，构建后得到 `baseline.prof`；APK 看 `/assets/dexopt/baseline.prof`，AAB 看 `/BUNDLE-METADATA/com.android.tools.build.profiles/baseline.prof`，安装后的 `base.odex` 在 `/data/app/.../oat/arm64/`。

- 🔹 **安装来源会改变 Profile 的消费时机**：[已验证: debug docs + ProfileInstaller/ProfileVerifier 文档]
  Google Play、Android Studio/Gradle、其他 installer + `ProfileInstaller` 的行为不同，`verify` 只表示当前还没看到已编译产物，不等于 APK 或 AAB 里没有 Baseline Profile。

- 🔹 **验证路径先看编译状态，再看启动收益**：[已验证: debug docs + Macrobenchmark docs]
  编译状态用 `ProfileVerifier` 或 `dumpsys package dexopt`，收益用 Macrobenchmark 的 TTID / TTFD 对比 `CompilationMode.None()` 与 `CompilationMode.Partial()`。

- 🔹 **`<profileable>` 与 OEM dexpreopt 要分开写**：[已验证: manifest docs + AOSP build 资料]
  `<profileable>` 元素是 API 29，`android:shell` 是 API 30；`WITH_DEXPREOPT_*` 属于系统镜像 preopt 开关，和应用侧 Baseline Profiles 不是一套机制。

### 扩展（可选深入）

- 🔸 Startup Profiles 与 DEX layout
- 🔸 [待验证] Google Play 云端预编译分发
- 🔸 1.12 节 AutoFDO 与应用侧 Profile 的分工

### OpenClaw 加工指引

> 锚点是最低覆盖要求，修稿时必须逐条落到正文。
> 涉及构建产物路径、ADB 命令、版本边界的段落，优先按官方文档和 AOSP 可核对口径写。
> 对公开证据不足的云端编译细节，保留 `[待验证]`，不要补成确定结论。
<!-- outline-end -->

## 为什么需要 Baseline Profiles

### ART 编译策略的演变

Android 5.x 的 ART 走的是全量 AOT。安装时 `dex2oat` 会把整包 DEX 尽量编成机器码，运行时体验稳定，但安装时间、OTA 后首开时间和磁盘占用都很重。

Android 7.0 把策略换成了混合编译。安装阶段以 `verify` 或 `quicken` 这一类轻量模式为主，运行期再由 JIT 收集热点方法，并把本地 Profile 持久化到 `/data/misc/profiles/cur/0/<package>/primary.prof`。设备空闲、充电时，后台 `bg-dexopt` 再按这些 Profile 做 `speed-profile` 编译。这一版才是 Android 把 profile-guided 编译正式放进 ART 主路径的起点，和 1.7 节的时间线一致。

Android 9.0 在这套本地 Profile 之上又补了一层 **Cloud Profiles**。Google Play 可以把聚合后的热点方法分发给安装端，帮助新版本更早拿到 `speed-profile` 编译收益。Cloud Profiles 只覆盖 Android 9+，也只存在于 Google Play 分发路径里。

Baseline Profiles 的价值落在这两条时间线之间。它不替代 Android 7 之后的本地 Profile，也不等 Google Play 的 Cloud Profiles 慢慢收敛，而是把开发者已经确认的启动路径和核心 CUJ 直接随包分发，让首装和首更阶段少走解释执行与 JIT 热身。

### Baseline Profiles 的定位

把三类 Profile 放在一起看，边界会更清楚：

| 类型 | 生产者 | 何时可用 | 主要用途 |
|------|--------|----------|----------|
| 本地 JIT Profile | 设备运行时 | 用户已经用过应用之后 | 指导后台 `bg-dexopt` 做 `speed-profile` 编译 |
| Baseline Profiles | 开发者 / CI | 安装包生成时 | 把启动路径和核心 CUJ 提前交给 ART |
| Cloud Profiles | Google Play | 新版本分发一段时间后 | 用真实用户数据补齐开发者没覆盖到的热点 |

因此，Baseline Profiles 解决的是 Day-0 和 Day-1 的冷启动问题，Cloud Profiles 解决的是规模化分发后的热点补全，本地 JIT Profile 解决的是单设备的持续收敛。三者能合并使用，但触发时机和来源不同。

### 实测效果

Baseline Profiles 的性能收益有大量公开数据支撑：

Google 官方给出的通用范围是 **15-30% 的启动速度提升**。实际案例中：
- **Reddit**（2024.12）：Baseline Profiles + R8 full mode → median 启动时间缩短 **51%**
- **Duolingo**：Macrobenchmark 测试显示 **25-40%** 的启动速度增益
- **Android Calendar**：启动时间 **~20%** 提升
- **Now in Android** 示例应用：有 profiles 时 229.0ms，无编译时 324.8ms（**~30%**）
- 某手机应用：median startup 提升 **23%**（328ms），Wear OS 应用 **14%**（267ms）

这些数据的差异主要来自应用本身的代码结构和 profile 覆盖的完整度。使用大量 Jetpack/Compose 库的应用收益通常更大，因为这些库的初始化路径长、方法调用密集。

[来源: intake/research-feeds/2026-04-06-11-baseline-profiles-compilation-optimization.md]

## Baseline Profiles 的工作机制

### Profile 格式与打包

开发阶段最先看到的是 Human-Readable Format（HRF）文本文件，通常名为 `baseline-prof.txt`。使用 AGP 或 Baseline Profile plugin 生成时，结果会复制到 `src/<variant>/generated/baselineProfiles/baseline-prof.txt`。这个文件适合进版本库，也适合人工审阅。

构建阶段，AGP 会把 HRF 转成 ART 能直接消费的二进制 `baseline.prof`。检查打包结果时要把 AAB 和 APK 分开看：

- APK：`/assets/dexopt/baseline.prof`
- AAB：`/BUNDLE-METADATA/com.android.tools.build.profiles/baseline.prof`

这两个路径说的是构建产物里的位置。应用真正安装到设备后，编译产物不会再留在这些目录里，而是表现为 `/data/app/.../oat/arm64/base.odex` 一类 OAT / VDEX 文件。运行期和后台任务收集到的 Profile 数据则继续放在 `/data/misc/profiles/...` 下。

### 安装时的编译流程

同一份 `baseline.prof`，到了不同安装来源，消费时机并不完全一样。按官方调试文档，实操里至少要分这几条主路径：

| 安装来源 | Profile 来源 | 常见触发时机 | 观察入口 |
|----------|--------------|--------------|----------|
| Google Play | APK 自带 Baseline Profile + Play 聚合的 Cloud Profiles | 安装期或后续后台设备更新 | `ProfileVerifier`、`dumpsys package dexopt` |
| Android Studio / Gradle 安装的 non-debuggable build | APK 自带 Baseline Profile | 设备端自动编译，必要时可手工触发 `bg-dexopt` | `ProfileVerifier`、`dumpsys package dexopt` |
| 其他 installer / 侧载 | APK 自带 Baseline Profile，常配合 `ProfileInstaller` 入队 | 常见为排队等待 `bg-dexopt`，或手工执行 `cmd package compile -r bg-dexopt` | `ProfileVerifier`、`dumpsys package dexopt` |

无论哪条路径，`/data/misc/profiles/...` 放的是 Profile 数据，`/data/app/.../oat/arm64/base.odex` 放的是编译后的应用 OAT 产物。把这两类目录分开看，`dumpsys package dexopt` 的输出才不会读反。

### ART Service 与 Profile 管理

Android 14 之后，`dexopt` 管理更多由 ART Service 承担。写验证步骤时，命令口径最好和官方调试文档保持一致：

```bash
# 触发一次后台编译
adb shell cmd package compile -r bg-dexopt com.example.app

# 查看当前编译状态
adb shell dumpsys package dexopt | grep -A 2 com.example.app
```

`dumpsys` 输出里常见的几个字段要这样读：

- `status = speed-profile`：已存在按 Profile 编译的产物
- `status = verify`：当前还没有看到编译产物，常见原因是还在排队、安装来源没有触发编译，或者包里没有 profile
- `reason = install-dm / bg-dexopt / cmdline`：分别对应安装期、后台任务和手工 ADB 触发
- `location is /data/app/.../oat/arm64/base.odex`：这是编译产物目录，不是 Profile 数据目录

如果需要在应用内自检，官方更推荐 `ProfileVerifier`。它能区分“包里没有 Baseline Profile”“已入队等待编译”“已经按 Profile 编译”等状态，适合接到 debug build 或灰度埋点里。

### Cloud Profiles 的配合

Cloud Profiles 用真实用户数据补齐 Baseline Profiles 没覆盖到的热点。它们只对 Android 9+、并且通过 Google Play 分发的安装路径有效。实际运行时，ART 会把安装包自带的 Baseline Profile 和 Play 下发的 Cloud Profile 一起作为 `speed-profile` 的输入，所以文中更适合把它写成叠加关系。

### [待验证] Android 16 的云端预编译分发

公开材料把 Android 16 描述为 Google Play 分发侧的云端预编译能力，目标是减少设备端 `dex2oat` 的工作量，让安装和更新阶段更短。到目前为止，公开的一手文档还不足以稳定确认 `SDM` 文件格式、签名绑定方式，以及“设备端是否完全不再做本地编译”的边界。

写到这一段时，先保留两个稳妥结论：

- 它属于 Google Play 分发增强能力，不是所有安装渠道都具备的通用机制。
- 它和 Baseline Profiles、Cloud Profiles 同属 ART 编译优化体系，但公开证据还不够支撑更细的实现断言。

## 生成与维护 Baseline Profiles

### 使用 Macrobenchmark 生成

官方推荐的主路径仍然是 Jetpack Macrobenchmark 配合 `BaselineProfileRule`。生成器的职责只有一件事，按真实用户路径把需要的类和方法跑一遍，让 Gradle 把这段执行轨迹转成 HRF 规则。

```kotlin
@RunWith(AndroidJUnit4::class)
class BaselineProfileGenerator {
    @get:Rule
    val rule = BaselineProfileRule()

    @Test
    fun startup() = rule.collect(
        packageName = "com.example.app",
        includeInStartupProfile = true,
    ) {
        pressHome()
        startActivityAndWait()
        // 其余核心 CUJ 用 UIAutomator 继续补
    }
}
```

`includeInStartupProfile` 用来把这段路径同时纳入 Startup Profile，文档里的正式参数名就是这个。

生成命令也要按当前文档写：

```bash
./gradlew :app:generateBaselineProfile
./gradlew :app:generateReleaseBaselineProfile
```

Gradle 任务跑完后，生成的 HRF 文件会复制到 `src/<variant>/generated/baselineProfiles/baseline-prof.txt`。如果项目有 product flavor，对应任务名会变成 `generate<Variant>BaselineProfile`。

### Profile 的关键覆盖路径

一个高质量的 Baseline Profile 需要覆盖以下路径：

- **冷启动**：从 `Application.onCreate()` 到首帧渲染完成
- **热启动**：从 Activity `onRestart()` 到界面恢复
- **核心用户旅程**：应用最常用的 3-5 个功能流程
- **Compose 渲染**：如果使用 Compose，包含组合（composition）相关方法

Profile 不需要追求 100% 覆盖——覆盖 80% 的启动路径就能获得大部分收益。过于追求覆盖率反而会导致 profile 文件过大，增加安装时的编译时间。

### AGP 自动化

AGP 8.0+ 已经把 Baseline Profiles 的生成和打包流程收进官方插件。实际项目里更稳妥的做法是直接使用 Baseline Profile Generator 模板或 `androidx.baselineprofile` 插件，让 release 或特定 variant 在 CI 里执行 `generate<Variant>BaselineProfile`。AGP 8.3 起，Startup Profile 相关的 DEX layout 优化默认开启，构建系统会把启动阶段更常用的类排到更靠前的位置。

项目治理上，关注三件事就够了：

- 生成任务是否覆盖所有核心 CUJ
- `baseline-prof.txt` 是否随变更一起进仓
- release 包里是否真的出现 `baseline.prof`

## 与 AutoFDO 的关系与区别

Baseline Profiles 和 AutoFDO 都属于 Profile-Guided Optimization，但它们处理的对象不同。

**Baseline Profiles** 针对的是 ART 管理的 Java/Kotlin 代码。输入是开发者定义的热点路径，输出是安装端 `speed-profile` AOT 编译覆盖范围。我们关心的是“哪些方法要提前编”。

**AutoFDO** 针对的是内核和系统 native binary 的机器码质量。Android ARM64 设备的主采样路径通常来自 ETM / CoreSight 一类硬件分支追踪，用户态常见入口是 `simpleperf record` 和后续的 `branch-list` 转换。LBR 是 x86 平台常见术语，不适合直接拿来描述 Android 的主实现。

| 维度 | AutoFDO | Baseline Profiles |
|------|---------|-------------------|
| 代码类型 | Native（C/C++） | Managed（Java/Kotlin） |
| 主要工具链 | LLVM / Clang + simpleperf | ART + dex2oat + AGP |
| 数据来源 | 硬件分支追踪 / 采样信息 | Macrobenchmark / 开发者定义 CUJ |
| 产物 | `*.afdo` / 更优的 native binary | `baseline.prof` / `oat` 编译产物 |
| 观测入口 | simpleperf、构建日志、内核基准 | `ProfileVerifier`、`dumpsys package dexopt`、Macrobenchmark |

对 OEM 来说，两者可以同时使用，但要分开写。AutoFDO 属于 GKI / native build 体系，Baseline Profiles 属于 APK / ART 编译体系。把 LBR、`WITH_DEXPREOPT_*`、`baseline.prof` 放进同一段，读者很容易把三套机制混成一套。

## 验证是否生效：先看编译状态，再看启动收益

### 1. 确认包里真的带了 Profile

最简单的第一步是看构建产物。AAB 检查 `/BUNDLE-METADATA/com.android.tools.build.profiles/baseline.prof`，APK 检查 `/assets/dexopt/baseline.prof`。如果这一步就缺文件，后面的 `dumpsys` 和基准测试都没有意义。

### 2. 确认设备端已经完成 `speed-profile` 编译

应用安装到设备后，用 `ProfileVerifier` 或 ADB 看状态：

```bash
adb shell cmd package compile -r bg-dexopt com.example.app
adb shell dumpsys package dexopt | grep -A 2 com.example.app
```

我们关心的是三类信息：

- `status = speed-profile`，说明设备侧已经生成按 Profile 编译的 OAT 产物
- `status = verify`，说明当前还没有看到编译产物，常见原因是 profile 还在排队、安装来源没有触发编译，或者包里根本没有 profile
- `location is /data/app/.../oat/arm64/base.odex`，说明观测点在应用 OAT 目录，而不是 `/data/misc/profiles/` 这类 Profile 数据目录

### 3. 再测启动收益

收益验证更适合交给 Macrobenchmark。常见做法是对同一条冷启动路径分别跑 `CompilationMode.None()` 和 `CompilationMode.Partial()`，再对比 TTID / TTFD。Baseline Profiles 解决的是编译覆盖率问题，Macrobenchmark 刚好能把这部分差异转成稳定的启动时间数据。

Perfetto 仍然有用，但更适合做补充观察：

- 看启动切片里是否还出现密集的 JIT 活动
- 看主线程、RenderThread 的热点是否转移
- 对照 `speed-profile` 状态确认优化前后的 trace 可比性

[图：同一条冷启动路径的两组验证视图。左侧是 `dumpsys package dexopt` 的 `speed-profile` 状态，右侧是 Macrobenchmark 的 TTID / TTFD 对比。]

## 常见问题与最佳实践

### Profile 过大导致编译时间增加

一个常见误区是“profile 越大越好”。profile 中列出的每个方法都需要 dex2oat 编译。如果 profile 列了数千个方法，安装时的编译时间反而会成为瓶颈——用户看到的"安装优化中..."提示会持续很久。

最佳实践是**只覆盖启动和核心 CUJ 的代码路径**，而不是整个应用的方法列表。Google 建议保持 profile 在合理的行数范围内（通常不超过几千条规则）。

### 多 DEX 文件的 Profile 管理

大型应用通常使用 multidex（多个 DEX 文件）。每个 DEX 文件都可以有自己的 profile 规则，它们会被合并处理。AGP 会自动处理多 DEX 的 profile 分配，开发者通常不需要手动干预。

### AAB 与 Baseline Profiles 的打包

打包路径只要记住一对目录即可：

- AAB：`/BUNDLE-METADATA/com.android.tools.build.profiles/baseline.prof`
- APK：`/assets/dexopt/baseline.prof`

AAB 里的 `BUNDLE-METADATA` 是构建产物视角，安装到设备后不会原样保留这个目录。Google Play 处理 bundle 后，真正参与编译的是 delivered APK 里的 Profile 数据和设备侧生成的 OAT 产物。

### 非 Google Play 渠道的 Profile 处理

这是国内开发者最关心的问题。Baseline Profiles 本身**不依赖 Google Play**——它打包在 APK 中，安装时直接被 dex2oat 消费。无论用户通过什么渠道安装（侧载、国内应用商店），只要设备的 ART 支持 speed-profile 编译过滤器（Android 9+），Baseline Profiles 都会生效。

但是，Cloud Profiles 和 Cloud Compilation **依赖 Google Play 服务**。非 Google Play 渠道拿不到这两类优化时，Baseline Profiles 往往就是最现实的 profile 优化手段。

[待验证: 国内主流应用商店是否有类似的云端 profile 基础设施]

### Library 的 Baseline Profiles 与 App 的合并

Jetpack 和其他 Google 库会自带 Baseline Profiles。当应用依赖这些库时，AGP 会自动将库的 profile 与应用自身的 profile 合并。开发者不需要手动管理库的 profile——这是 AGP 的默认行为。

Compose 运行时（`androidx.compose.*`）自带了大量的 Baseline Profiles 规则，覆盖了组合（composition）、布局（layout）、绘制（drawing）的完整管线。使用 Compose 的应用即使不生成自己的 profile，也能从库的 profile 中获得一部分收益。

## Jetpack Compose 与 Baseline Profiles

Compose 运行时对 Baseline Profiles 的依赖程度比传统 View 系统高得多。原因是 Compose 的组合阶段（composition）涉及大量 Kotlin 编译器生成的辅助方法——这些方法在 Compose 的 compiler plugin 生成的代码中，路径长、调用频率高，如果没有 AOT 编译，冷启动时的解释执行开销会非常明显。

Google 在 Compose 的每个 release 中都附带了预生成的 Baseline Profiles。具体来说：
- `androidx.compose.runtime` 的 profile 覆盖了 `ComposerImpl` 的核心方法
- `androidx.compose.ui` 的 profile 覆盖了布局和绘制管线的关键路径
- `androidx.compose.foundation` 的 profile 覆盖了 LazyColumn/Row 的测量和布局逻辑

使用 Compose 的应用**强烈建议**生成自己的 Baseline Profiles，而不仅仅依赖库的 profile。因为库的 profile 不知道应用的具体组合树结构——它只知道库内部的方法是热点，但不知道应用层的 `@Composable` 函数调用链。应用层的 profile 和库的 profile 合并后，才能覆盖完整的渲染路径。

实测数据也验证了这一点：Compose 应用添加 Baseline Profiles 后的收益通常比传统 View 应用更大（25-40% vs 15-20%），原因就是 Compose 运行时的编译依赖更重。

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance#baseline_profiles]

## 扩展

### Profileable 应用与性能分析

`<profileable>` 元素本身是 API 29 加入的，`android:shell` 属性是 API 30 新增的。写版本边界时，这两个点要分开。

- API 29：可以在 release-like build 上声明 `<profileable>`
- API 30：`android:shell="true"` 允许 shell 工具、Perfetto、simpleperf、`am profile` 等本地工具分析应用

实际项目里，Baseline Profile 生成和验证通常使用 non-debuggable + `profileable` 的组合。debuggable build 会改变 ART 优化行为，启动时间和 trace 都更容易失真。

```xml
<profileable
    android:shell="true"
    tools:targetApi="30" />
```

### OEM 系统镜像级别的编译优化

OEM 侧当然也会做编译优化，但主路径是 system dexpreopt 和 boot image preopt。`WITH_DEXPREOPT=true`、`WITH_DEXPREOPT_BOOT_IMG_AND_SYSTEM_SERVER_ONLY=true` 这类开关控制的是系统镜像里哪些 JAR、APK 在构建时预编译。

把这套机制直接写成“System Baseline Profiles”会把概念写乱。当前公开 AOSP build 文档并没有给出一个稳定的、与应用侧 `baseline.prof` 一一对应的系统 Profile 产物格式。更稳妥的写法是：

- 应用侧 Baseline Profiles，由开发者生成，随 APK 或 AAB 分发，由 ART 在安装端消费
- 系统镜像 preopt，由 OEM 在构建系统镜像时完成，产物属于 boot image、system_server 和预装包的 dexpreopt 结果

[待验证] 如果某些 OEM 在私有构建体系里给预装应用注入额外 Profile，那是厂商扩展实现，不能直接当成 AOSP 通用机制。

## 参考资料

### 官方文档
- https://developer.android.com/topic/performance/baselineprofiles/overview
- https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile
- https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles
- https://developer.android.com/guide/topics/manifest/profileable-element

### AOSP / 交叉章节
- `src/part1-fundamentals/ch01-architecture/07-art-compilation.md`
- `src/part1-fundamentals/ch01-architecture/12-autofdo-optimization.md`

### 研究素材
- `intake/research-feeds/2026-04-06-11-baseline-profiles-compilation-optimization.md`
- `intake/research-feeds/2026-04-04-07-ch08-startup-profiles-dex-layout-optimization.md`
