---

title: Baseline Profiles 与编译优化实践
chapter: '8.7'
section: '8.7'
status: "finalized"
drafted_date: '2026-04-06'
drafted_by: openclaw-task2a
applicable_versions: Android 7 (API 24) - Android 17 (API 37)
last_verified: "2026-06-20"
last_verified_against: "Android Developers Baseline/Startup/ProfileVerifier/Profileable docs (2026-06) + AOSP platform/art android-17.0.0_r1 ART Service"
reviewed_date: "2026-05-27"
reviewed_by: "openclaw-task6"
task6_result: "pass-light-edit"
task9_result: "pass-tech-review"
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
- baseline-profiles
- art
- dexopt
- startup
- performance
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: "reviewed"
task2b_state: "fixed"
task2b_result: fixed
review_round: 6
task9_reviewed_date: "2026-06-20"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-20T04:27:08+08:00"
last_task6_audit: '2026-06-11'
last_task2b_at: '2026-04-24T19:36:54+08:00'
review_notes: "2026-04-24 task6 re-review (revisiting): pass-light-edit. Task2b 修复后内容无新L1/L2问题。版本边界清晰，编译流程拆分完整，验证路径实用。Task9仍有needs-rework待重审。评分: 结构5/5·措辞5/5·一致性5/5·验证4/5·元数据5/5。"
task9_review_notes: "2026-06-20 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 3；Android Developers Baseline/Startup/ProfileVerifier/Profileable 文档与 AOSP android-17.0.0_r1 ART Service 源码锚点复核通过；Task6 已通过且 queue 无 pending，自动晋升 finalized。"
last_task9_audit: "2026-06-19"
last_task2b_verifier_at: "2026-06-20T03:32:38+08:00"
task2b_verifier_result: "ready-for-task6"
last_task6_at: "2026-06-20T01:07:00+08:00"
last_task6_review_log: "logs/review/2026-06-20-01-review.md"
task6_review_notes: "2026-05-27 Task6 04:06：pass-light-edit。L1/L2 小修 5 处；无新增 L3/L4 回炉。Task9 仍为 needs-rework/pending，未自动晋升 finalized。 | 2026-06-20 01:07 Task6 revisiting re-review：pass-light-edit。Task2B 修复 + Task9 auto-fix 后内容无新增 L1/L2 问题；无 L3/L4 回炉项。Task9 为 auto-fixed（非 pass-tech-review），未满足自动晋升条件。"
last_task9_review_log: "logs/deep-review/2026-06-20-04-deep-review.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-20
last_task9_autofix_at: "2026-06-19"
auto_promoted: true
finalized_date: "2026-06-20"
finalized_by: "openclaw-task9-auto-promote"
---
# 8.7 Baseline Profiles 与编译优化实践

ART 的编译策略经历过几次大的调整：Android 5.0 走全量 AOT，Android 7.0 换成解释执行 + JIT，再到后来的 Profile-Guided 编译。每次调整都在安装时间、运行性能和磁盘占用之间做新的取舍。但有一个问题始终没变：**应用首次安装后的冷启动性能**。

在这个时间窗口内，ART 还没有收集到足够的运行时 profile 数据，无法知道哪些方法是热点。结果是大量关键代码只能解释执行，冷启动速度比经过优化的状态慢 30% 甚至更多。

Baseline Profiles 的作用是让开发者在 APK 中预置一份"热点方法清单"，并在设备端的安装期或后续 Profile 编译阶段优先告诉 dex2oat 哪些代码需要先编译为机器码。这样即使没有任何用户使用数据，首次启动也更容易接近稳态性能。
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
  编译状态用 `ProfileVerifier`（Android 9+）或 `dumpsys package dexopt`，收益用 Macrobenchmark 的 TTID / TTFD 对比 `CompilationMode.None()` 与 `CompilationMode.Partial()`。

- 🔹 **`<profileable>` 与 OEM dexpreopt 要分开写**：[已验证: manifest docs + AOSP build 资料]
  `<profileable>` 元素和 `android:shell` 都从 API 29 开始可用；API 30 新增的是 `android:enabled`。`WITH_DEXPREOPT_*` 属于系统镜像 preopt 开关，和应用侧 Baseline Profiles 不是一套机制。

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

**版本覆盖表：**

| 能力 | 起始版本 | 渠道限制 | 说明 |
|------|----------|----------|------|
| 开发者 Baseline Profile | Android 7 (API 24) | 无 | 随 APK/AAB 分发，所有安装渠道均可携带 |
| Cloud Profiles | Android 9 (API 28)+ | 仅 Google Play | 聚合真实用户热点数据，分发周期取决于 Play |
| AGP 8.4+ 设备端自动编译 | Android 7+ | Android Studio / Gradle 安装 non-debuggable build | 旧版 AGP 或其他 installer 需 ProfileInstaller |
| AGP 8.1+ Startup Profile / DEX layout | Android 7+ (DEX layout), Android 15+ (16KB 红利) | 无 | AGP 8.1 引入 Startup Profile 布局优化，8.3 默认启用；16KB 页环境下单页覆盖更多热方法，放大缓存友好效应 |
| Android 15+ 16KB page-size 兼容 | Android 15+ | 无 | NDK r28+ 默认 16KB ELF 对齐、AGP 8.5.1+ 未压缩 .so、zipalign `-P 16`；属于构建对齐与 native 兼容，与 DEX layout 是两套机制 |

Android 7/8 是"有开发者 Baseline Profile 但无 Cloud Profile"的关键边界——这两个版本的冷启动优化完全依赖开发者预置的规则，无法从 Google Play 获得聚合补充。

### 实测效果

Baseline Profiles 的性能收益有大量公开数据支撑：

Google 的通用结论是 **15-30% 的启动速度提升**，实际公开案例包括：
- **Reddit**（2024.12）：Baseline Profiles + R8 full mode → median 启动时间缩短 **51%**
- **Duolingo**：Macrobenchmark 测试显示 **25-40%** 的启动速度增益
- **Android Calendar**：启动时间 **~20%** 提升
- **Now in Android** 示例应用：有 profiles 时 229.0ms，无编译时 324.8ms（**~30%**）
- 某手机应用：median startup 提升 **23%**（328ms），Wear OS 应用 **14%**（267ms）

收益差异主要来自应用的代码结构和 profile 覆盖完整度。大量使用 Jetpack 和 Compose 库的应用收益通常更高，因为这些库的初始化路径长、方法调用密集。
## Baseline Profiles 的工作机制

### Profile 格式与打包

开发阶段最先看到的是 Human-Readable Format（HRF）文本文件，通常名为 `baseline-prof.txt`。使用 AGP 或 Baseline Profile plugin 生成时，结果会复制到 `src/<variant>/generated/baselineProfiles/baseline-prof.txt`。这个文件适合进版本库，也适合人工审阅。

构建阶段，AGP 会把 HRF 转成 ART 能直接消费的二进制 `baseline.prof`，同时生成伴随的元数据文件 `baseline.profm`（Profile Metadata）。检查打包结果时要把 AAB 和 APK 分开看：

- APK：`/assets/dexopt/baseline.prof`（规则文件）、`/assets/dexopt/baseline.profm`（元数据）
- AAB：`/BUNDLE-METADATA/com.android.tools.build.profiles/baseline.prof`、`/BUNDLE-METADATA/com.android.tools.build.profiles/baseline.profm`

`.profm` 文件存储的是 profile 规则与 DEX 编译单元的映射关系。手动 sideload 验证或生成 `.dm`（Dex Metadata）包时，`baseline.profm` 会被重命名为 `primary.profm`，需要和 `baseline.prof` 一起处理。

这两个路径说的是构建产物里的位置。应用安装到设备后，编译产物不会再留在这些目录里，而是表现为 `/data/app/.../oat/arm64/base.odex` 一类 OAT / VDEX 文件。运行期和后台任务收集到的 Profile 数据则继续放在 `/data/misc/profiles/...` 下。

### 安装时的编译流程

同一份 `baseline.prof`，到了不同安装来源，消费时机并不完全一样。按官方调试文档，实操里至少要分这几条主路径：

| 安装来源 | Profile 来源 | 常见触发时机 | 观察入口 |
|----------|--------------|--------------|----------|
| Google Play | APK 自带 Baseline Profile + Play 聚合的 Cloud Profiles | 后台设备更新/后续 dexopt（不是安装时立即编译） | `ProfileVerifier`、`dumpsys package dexopt` |
| Android Studio / Gradle 安装的 non-debuggable build（AGP 8.4+） | APK 自带 Baseline Profile | 设备端自动编译，必要时可手工触发 `bg-dexopt` | `ProfileVerifier`、`dumpsys package dexopt` |
| Android Studio / Gradle 安装的 non-debuggable build（AGP < 8.4） | APK 自带 Baseline Profile | 不会自动编译；需要 `ProfileInstaller` 入队或手工 `cmd package compile` | `ProfileVerifier`、`dumpsys package dexopt` |
| 其他 installer / 侧载 | APK 自带 Baseline Profile，`ProfileInstaller` 负责把 profile 入队 | 常见为等待下一次 `bg-dexopt`；线下要立刻确认时，可手工执行 `cmd package compile -r bg-dexopt` 或 `cmd package compile -m speed-profile -f` | `ProfileVerifier`、`dumpsys package dexopt` |

`ProfileVerifier` 的查询能力从 Android 9（API 28）开始可用。Android 7/8 仍在 Baseline Profile 的适用范围内，但验证状态时应优先看 ADB 编译状态和启动基准，不要把 `RESULT_CODE_ERROR_UNSUPPORTED_API_VERSION` 误判成 profile 没有生效。

AGP 8.4 是自动编译的分界线。AGP 8.4+ 通过 Android Studio 或 Gradle 安装 non-debuggable build 时，设备端会自动触发 `speed-profile` 编译。AGP 8.4 之前的版本或其他 installer（如 `adb install`、第三方工具）不会自动编译，需要依赖 `ProfileInstaller` 库把 profile 入队，或手工执行 `cmd package compile`。

无论哪条路径，`/data/misc/profiles/...` 放的是 Profile 数据，`/data/app/.../oat/arm64/base.odex` 放的是编译后的应用 OAT 产物。把这两类目录分开看，`dumpsys package dexopt` 的输出才不会读反。

### ART Service 与 Profile 管理

Android 14 之后，`dexopt` 管理由 ART Mainline 模块内的 ART Service 承担。Android 17 源码锚点在 AOSP `platform/art/artd/` 和 `platform/art/libartservice/`：前者承接 artd 侧服务，后者包含 ART Service 控制面与 dexopt 调度相关逻辑。应用侧常用的入口有两个：`cmd package compile -r bg-dexopt` 触发后台编译语义，`cmd package compile -m speed-profile -f` 直接强制 speed-profile 编译。写验证步骤时，命令口径最好和官方调试文档保持一致：

```bash
# 触发一次后台 dexopt 语义的编译
adb shell cmd package compile -r bg-dexopt com.example.app

# 直接强制做 speed-profile 编译，线下验证更直观
adb shell cmd package compile -m speed-profile -f com.example.app

# 查看当前编译状态
adb shell dumpsys package dexopt | grep -A 2 com.example.app
```

如果要模拟系统稍后会不会吃到 profile，`-r bg-dexopt` 更贴近后台任务语义；如果只是线下确认当前包能不能按 Profile 编译，`-m speed-profile -f` 更直接。

`dumpsys` 输出里常见的几个字段要这样读：

- `status = speed-profile`：已存在按 Profile 编译的产物
- `status = verify`：当前还没有看到编译产物，常见原因是还在排队、安装来源没有触发编译，或者包里没有 profile
- `reason = install-dm / bg-dexopt / cmdline`：分别对应安装期、后台任务和手工 ADB 触发
- `location is /data/app/.../oat/arm64/base.odex`：这是编译产物目录，不是 Profile 数据目录

如果需要在应用内自检，官方更推荐 `ProfileVerifier`。它能区分“包里没有 Baseline Profile”“已入队等待编译”“已经按 Profile 编译”等状态，适合接到 debug build 或灰度埋点里。这个入口只支持 Android 9（API 28）及更高版本；Android 7/8 仍可携带 Baseline Profile，但状态验证要依赖 ADB、`dumpsys package dexopt` 或 Macrobenchmark 对比。

### Cloud Profiles 的配合

Cloud Profiles 用真实用户数据补齐 Baseline Profiles 没覆盖到的热点。它们只对 Android 9+、并且通过 Google Play 分发的安装路径有效。实际运行时，ART 会把安装包自带的 Baseline Profile 和 Play 下发的 Cloud Profile 一起作为 `speed-profile` 的输入，所以文中更适合把它写成叠加关系。

### [待验证] Android 16 的云端预编译分发

公开材料把 Android 16 描述为 Google Play 分发侧的云端预编译能力，目标是减少设备端 `dex2oat` 的工作量，让安装和更新阶段更短。到目前为止，公开的一手文档还不足以稳定确认 `SDM` 文件格式、签名绑定方式，以及“设备端是否完全不再做本地编译”的边界。

目前能确定两点：

- 它属于 Google Play 分发增强能力，不是所有安装渠道都具备的通用机制。
- 它和 Baseline Profiles、Cloud Profiles 同属 ART 编译优化体系，但公开证据还不够支撑更细的实现断言（包括 SDM 的具体格式和签名绑定方式，目前仍缺少可复核的 AOSP 或官方文档锚点）。

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

### Startup Profile 与指令缓存局部性

Startup Profile（`includeInStartupProfile = true` 标记的规则）不仅告诉 `dex2oat` 优先编译哪些方法，还通过 DEX layout 优化改变了方法的物理排列顺序。启动阶段的热点方法被集中排列在连续的 DEX 页中，这带来了硬件层面的收益：

- **L1 I-Cache 命中率提升**：连续的热方法减少了 Cache Line 的冲突失效，冷启动时指令缓存的有效覆盖率更高。
- **L2 Cache 与 TLB 协同**：方法集中排列还减少了跨页访问，降低了 TLB Miss 的概率。在 16KB 页环境下，单页覆盖的方法数更多，这个效应被进一步放大。

实测中，Startup Profile 对冷启动的贡献通常占 Baseline Profile 总收益的 40-60%，其中一部分就来自这种硬件级的缓存友好性，而不仅仅是编译覆盖本身。

### Profile 的关键覆盖路径

一个高质量的 Baseline Profile 需要覆盖以下路径：

- **冷启动**：从 `Application.onCreate()` 到首帧渲染完成
- **热启动**：从 Activity `onRestart()` 到界面恢复
- **核心用户旅程**：应用最常用的 3-5 个功能流程
- **Compose 渲染**：如果使用 Compose，包含组合（composition）相关方法

Profile 不需要追求 100% 覆盖——覆盖 80% 的启动路径就能获得大部分收益。过于追求覆盖率反而会导致 profile 文件过大，增加安装时的编译时间。

### AGP 自动化

AGP 8.0+ 已经把 Baseline Profiles 的生成和打包流程收进官方插件。实际项目里更稳妥的做法是直接使用 Baseline Profile Generator 模板或 `androidx.baselineprofile` 插件，让 release 或特定 variant 在 CI 里执行 `generate<Variant>BaselineProfile`。

Startup Profile 的 DEX layout 优化从 AGP 8.1 可用、8.3 默认启用。它把启动阶段的热点方法集中排列在连续的 DEX 页中，减少 Page Fault 并提高指令缓存命中率。16KB 页环境下单页覆盖更多热方法，这个缓存友好效应被进一步放大——但这是 16KB 内核页的被动红利，不是 AGP 版本决定的开关。

16KB page-size 兼容是另一套机制：NDK r28+ 默认生成 16KB ELF 对齐的 .so、AGP 8.5.1+ 使用未压缩 shared libraries、zipalign `-P 16` / bundletool 验证 ZIP entry 对齐。它与 Startup Profile / DEX layout 优化是两个独立的构建能力，不要混在一起判断。

项目治理上，关注三件事就够了：

- 生成任务是否覆盖所有核心 CUJ
- `baseline-prof.txt` 是否随变更一起进仓
- release 包里是否包含 `baseline.prof`

### Android 17 与 R8 的适配边界

到 Android 17，应用侧 Baseline Profiles 的消费路径没有换轨。公开文档和 android-17-beta3 交叉核对后，release 包里仍然是 `baseline.prof`，设备端仍然生成 `speed-profile` 对应的 OAT 产物。Android 14 之后更多 dexopt 调度转到 ART Service，但验证入口还是 `ProfileVerifier` 和 `dumpsys package dexopt`。

R8 会影响收益，但影响点在 release 产物的代码形态和启动路径命中率，不是把 Baseline Profiles 机制改掉。官方生成文档明确要求按 release build 或基于 release 的 variant 生成 profile，product flavor 也要分别产出。实操里把下面四件事固定下来，命中率会稳定很多：

- Profile 生成、打包和 Macrobenchmark 都对准 release 或 release-like variant，不拿 debug 产物代替
- 打开 R8 full mode、调整 keep 规则、做大规模包结构改动后，重新生成 `baseline-prof.txt`
- 先检查最终 APK / AAB 里是否还带着 `baseline.prof`，再谈命中率
- 收益回落时，用同一 release 包对比 `CompilationMode.None()` 和 `CompilationMode.Partial()`，不要把版本差异和编译差异混在一起

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

### 1. 确认包里带有 Profile

最简单的第一步是看构建产物。AAB 检查 `/BUNDLE-METADATA/com.android.tools.build.profiles/baseline.prof`，APK 检查 `/assets/dexopt/baseline.prof`。如果这一步就缺文件，后面的 `dumpsys` 和基准测试都没有意义。

### 2. 确认设备端已经完成 `speed-profile` 编译

应用安装到设备后，Android 9+ 可以用 `ProfileVerifier` 或 ADB 看状态；Android 7/8 走 ADB 路径：

```bash
adb shell cmd package compile -r bg-dexopt com.example.app
adb shell cmd package compile -m speed-profile -f com.example.app
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

AAB 里的 `BUNDLE-METADATA` 是构建产物视角，安装到设备后不会原样保留这个目录。Google Play 处理 bundle 后，参与编译的是 delivered APK 里的 Profile 数据和设备侧生成的 OAT 产物。

### 非 Google Play 渠道的 Profile 处理

这是国内开发者最关心的问题。Baseline Profiles 本身不依赖 Google Play，但离线安装也不能写成“APK 一装上，dex2oat 就一定已经按 profile 编完”。更稳妥的边界是：

- APK 可以携带 `baseline.prof`，这表示安装包里带了规则，不等于设备侧已经生成 `speed-profile` 产物
- 通过其他 installer 或侧载安装时，Jetpack `ProfileInstaller` 负责把 profile 入队，等待下一次后台 DEX 优化流程处理
- 想确认当前设备是否已经吃到编译收益，Android 9+ 可以看 `ProfileVerifier`，所有版本都应看 `dumpsys package dexopt`；需要立即验证时，用 `cmd package compile -m speed-profile -f`，要模拟后台任务语义时再用 `cmd package compile -r bg-dexopt`

所以，非 Google Play 渠道并不是拿不到 Baseline Profile 收益，而是“何时完成编译”取决于安装器、`ProfileInstaller` 和后台 dexopt 是否已经跑完。Cloud Profiles 和 Cloud Compilation 仍然依赖 Google Play 服务，离线渠道拿不到这两类分发增强能力。

[待验证: 国内主流应用商店是否有类似的云端 profile 基础设施]

### Profile 生成失败或收益回落时怎么查

常见的失败形态有四种：

- 构建产物里没有 `baseline.prof`：生成任务没跑到目标 variant，或者 CI 只产出了 debug 包
- 设备一直停在 `status = verify`：侧载路径只完成了 profile 入队，`bg-dexopt` 还没跑
- 切到新的 R8 / Startup Profile 配置后收益消失：旧的 HRF 文件还在，但启动路径已经变了
- Macrobenchmark 几乎没差异：测试拿的不是同一 release 包，或者对比模式不是 `None()` / `Partial()`

排查顺序也固定下来：

1. 检查 APK / AAB 里有没有 `baseline.prof`
2. Android 9+ 用 `ProfileVerifier`，所有版本用 `dumpsys package dexopt` 看设备是否进入 `speed-profile`
3. 仍停在 `verify` 时，先跑 `adb shell cmd package compile -m speed-profile -f com.example.app`
4. 再用 Macrobenchmark 对同一包做 `None()` / `Partial()` 对比

这组顺序能把“没打进去”“没编出来”“编出来但收益不明显”三类问题拆开。

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

这也解释了为什么 Compose 应用添加 Baseline Profiles 后的收益通常比传统 View 应用更明显。
## 扩展

### Profileable 应用与性能分析

`<profileable>` 元素和 `android:shell` 都从 API 29 开始可用；API 30 新增的是 `android:enabled`。写版本边界时，把这三个点拆开更稳妥。

- API 29：可以在 release-like build 上声明 `<profileable android:shell="true" />`
- API 30：`android:enabled` 允许进一步控制系统服务或 shell 工具是否可见
- 本地线下分析场景里，`android:shell="true"` 允许 shell 工具、Perfetto、simpleperf、`am profile` 等直接分析应用

实际项目里，Baseline Profile 生成和验证通常使用 non-debuggable + `profileable` 的组合。debuggable build 会改变 ART 优化行为，启动时间和 trace 都更容易失真。

```xml
<profileable
    android:shell="true"
    tools:targetApi="29" />
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
