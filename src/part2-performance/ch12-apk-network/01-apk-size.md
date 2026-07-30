---

title: APK 体积优化
section: '12.1'
chapter: '12.1'
status: "finalized"
drafted_date: '2026-04-03'
drafted_by: openclaw-task2a
task6_reviewed_date: '2026-05-06'
polish_count: 1
polish_date: '2026-04-10'
polish_by: task2b-polish
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: '2026-07-31'
last_verified_against: 'AOSP android-17.0.0_r1；Android 17 / API 37 SDK；AGP 9.3.0、R8、bundletool、Play Feature Delivery 与 16KB page-size 官方文档（2026-07）'
confidence: high
sources:
- type: official
  path: https://developer.android.com/topic/performance/reduce-apk-size
- type: official
  path: https://developer.android.com/guide/app-bundle/test
- type: official
  path: https://developer.android.com/tools/bundletool
- type: official
  path: https://developer.android.com/topic/performance/app-optimization/enable-app-optimization
- type: official
  path: https://developer.android.com/build/releases/agp-9-3-0-release-notes
- type: official
  path: https://developer.android.com/reference/tools/gradle-api/9.3/com/android/build/api/dsl/ApplicationAndroidResources
- type: official
  path: https://developer.android.com/guide/playcore
- type: official
  path: https://developer.android.com/guide/playcore/feature-delivery
- type: official
  path: https://developer.android.com/guide/playcore/feature-delivery/on-demand
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/overview
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/configure-baselineprofiles
- type: official
  path: https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations
- type: official
  path: https://developer.android.com/guide/practices/page-sizes
- type: official
  path: https://developer.android.com/tools/zipalign
- type: official
  path: https://developer.android.com/build/include-native-symbols
- type: aosp
  path: frameworks/base/libs/androidfw/ResourceTypes.cpp
- type: aosp
  path: art/libdexfile/dex/dex_file_loader.cc
- type: aosp
  path: bionic/linker/linker.cpp
tags:
- apk
- r8
- proguard
- app-bundle
- resource-optimization
- native-libs
- dex
- code-shrinking
- webp
- abi-filter
- dynamic-feature
- apk-analyzer
related_chapters:
- '8.3'
- '14.1'
- '15.6'
task2b_state: fixed
task9_result: "pass-tech-review"
task2b_result: fixed-lite
task9_reviewed_date: "2026-05-28"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-05-28T01:28:49+08:00"
reviewed_by: openclaw-task6
reviewed_date: '2026-05-06'
task6_result: pass-light-edit
task6_state: "reviewed"
task9_state: "reviewed"
repaired_by: openclaw-task2b
last_task2b_at: '2026-05-06T04:41:00+08:00'
task9_review_notes: "2026-05-06 05 task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 2。Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-05-24 Task9 闲时抽检：needs-rework。P0 0 / P1 1 / P2 0；Dynamic Feature Module 仍使用旧 Play Core Library 1.6+ 口径，需更新为 Play Feature Delivery Library 2.1.0+ 并标注 Android 14+ target SDK 版本边界。 | 2026-05-28 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-06-18 Task9 闲时抽检：pass-tech-review。P0 0 / P1 0 / P2 1；官方文档核对未发现 Android 18/API 38 越界；zipalign 16KB 验证命令建议后续从对齐命令改为 -c 校验命令。 | 2026-07-09 Task9 闲时抽检：pass-tech-review。P0 0 / P1 0 / P2 1；复核官方文档未发现 Android 18/API 38 越界；16KB zipalign 仍为既有 P2 建议，未新增队列。"
last_task6_at: '2026-05-06T05:05:00+08:00'
last_task6_audit: 2026-07-16T14:18:09+08:00
review_notes: '2026-05-05 Task6 23:26：revisiting 写作复审，清理填充词/元叙述，并让 density FAQ 与正文口径一致；写作层通过。Task9
  已有 P1/P2 queue pending，等待 Task2B。 | 2026-05-06 Task6 05:05：revisiting 写作复审；清理 L1/L2
  结构性引导语与术语一致性问题，写作层通过。Task9 仍 pending，本轮不做技术裁决。 | 2026-05-06 05 task9 deep-review:
  pass-tech-review。P0 0 / P1 0 / P2 2。Task6 已通过且 queue 无 pending，自动晋升 finalized。'
last_task9_review_log: "logs/deep-review/2026-05-28-01-deep-review.md"
last_task9_audit: '2026-07-09'
last_task9_audit_log: logs/deep-review/2026-07-09-14-audit.md
rework_type: review回炉修复（Task9 闲时抽检问题单）
last_task2b_lite_at: '2026-05-27'
pipeline_stage: ready-to-publish
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-18
---

# APK 体积优化

“安装包有多大”没有单一答案。团队若只盯着 `app-release.aab` 的文件大小，很容易优化错对象。一次 Android 发布至少会出现四组体积：

- **上传体积**：发布系统接收的 AAB，或某个渠道接收的 APK。
- **下载体积**：商店为特定设备生成制品后，经传输压缩得到的字节数。
- **安装制品体积**：设备保存的 base APK、configuration APK 与 feature APK 总量。
- **安装后占用**：安装制品、提取文件、ART 编译产物、应用数据和缓存共同占用的存储空间。

这些数字服务于不同问题。下载体积影响网络等待，安装制品影响设备存储，ART 产物属于运行时编译结果。包体变小可能缩短下载或安装时间，却不能据此推导堆内存、启动耗时或常驻内存必然同比下降。性能结论仍需用对应指标测量。

本章以 Android 17 / API 37、AOSP `android-17.0.0_r1` 和 AGP 9.3.0 为基准，讨论 release 制品的分析、缩减、分发与验证。

## 建立可比较的体积口径

### AAB、APK 与设备交付集

AAB 是发布用的容器，不能直接安装。Google Play 会依据设备的 ABI、屏幕密度、语言和 feature 状态生成一组 APK。相同 AAB 在两台设备上的下载量与安装制品总量可能不同。

直接分发 APK 的渠道没有这层按设备生成能力，单 APK 往往需要覆盖更多 ABI 和资源配置。`bundletool` 可以从 AAB 生成 APK set，也可以生成 universal APK；universal APK 合并了广泛的设备配置，因此会失去大部分按设备裁剪收益。非 Play 渠道是否接收 AAB、是否支持拆分安装，由该渠道的发布规范决定。

### 固定测量输入

可复现的比较需要固定这些条件：

- 同一 build variant、签名方式与构建工具版本；
- 同一 `bundletool` 版本和同一 device spec；
- 相同的压缩口径，例如 min、max 或某个固定设备的下载估算；
- 相同的符号、mapping、Baseline Profile 与动态模块配置；
- release 制品对 release 制品，避免拿 debug APK 做基线。

下面的命令用于生成设备交付集，并查询指定设备的压缩下载范围：

```bash
bundletool build-apks \
  --bundle=app-release.aab \
  --output=app-release.apks \
  --overwrite

bundletool get-size total \
  --apks=app-release.apks \
  --device-spec=ci/device-spec.json

apkanalyzer apk file-size app-release.apk
```

`bundletool get-size total` 分析 APK set，`apkanalyzer` 返回 APK 文件自身的字节数。发布门禁应使用流水线生成的签名制品；本地临时签名只适合方向性分析。Google Play Console 的下载数据更接近线上交付结果，不能用 AAB 的 ZIP 大小替代。

Android Studio 的 APK Analyzer 适合查看目录贡献、DEX 包级贡献、资源和两个制品之间的差异。它显示的 Raw Size 与 Download Size 是不同口径，后者属于工具估算。报告中应注明工具和版本，避免把估算值写成商店观测值。

## APK 内部有哪些内容

APK 是带有 Android 约束的 ZIP 文件。常见条目可分为以下几类：

- `classes.dex`、`classes2.dex` 等保存 DEX 字节码。单个 DEX 的 `method_ids` 表最多容纳 65,536 个**方法引用**，它不是“应用最多只能有 65,536 个方法”。D8 会结合 `minSdk`、主 DEX 规则与依赖生成一个或多个 DEX；API 21 起平台原生支持从 APK 加载多个 DEX。
- `resources.arsc` 保存编译后的资源表，`res/` 保存编译资源及图片等文件。AOSP `androidfw` 依照 package、type、entry 与 configuration 解析资源表；可从 [`ResourceTypes.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/androidfw/ResourceTypes.cpp) 核对数据结构和边界检查。
- `assets/` 保存应用按原始文件接口读取的内容，例如字体、模型、网页资源或配置。构建系统不会分析业务语义，未使用的 asset 需要工程侧识别。
- `lib/<abi>/` 保存 ELF 共享库。同一个库为多个 ABI 编译后会形成多份机器码。
- `AndroidManifest.xml` 是编译后的清单。
- Java resource、服务声明和许可证文件通常位于各自 ZIP 路径或 `META-INF/`。

签名信息需要按 APK Signature Scheme 区分。V1/JAR 签名会在 `META-INF/` 生成 `MANIFEST.MF`、`.SF` 与签名块文件；V2/V3 签名位于 APK Signing Block；V4 安装流程还可能使用独立的 `.idsig`。看到 `META-INF/` 不能推断制品只采用哪一种签名方案。

ZIP 条目是否压缩也会改变观察结果。DEX、资源和 native library 可能因打包策略采用压缩或未压缩存储。未压缩条目的 APK 文件会更大，却可支持直接映射或减少安装时提取。体积评审应同时记录 ZIP 压缩大小、原始大小和设备侧形态。

## 用贡献者排序代替猜测

一轮体积分析可以按四个贡献域展开：

1. **代码**：应用模块、传递依赖、生成代码、反射保留规则。
2. **资源**：图片、翻译、资源表、重复资源和无法被静态分析的动态引用。
3. **native**：ABI、副本、符号、第三方预编译库和页对齐。
4. **asset 与交付模块**：字体、媒体、模型、Web 内容、install-time feature。

报告至少保留“优化前、优化后、差值、归属文件、目标设备口径”五列。总量变化只能说明结果，文件或包级 diff 才能解释来源。百分比应由项目制品计算，不能套用行业案例的固定收益。

## 代码与资源：以 R8 输出为准

### AGP 9.3.0 的优化入口

AGP 9.3.0 支持的最高 API 级别是 37，并引入了新的 `optimization` DSL。release 构建可这样开启代码优化和优化后的资源缩减：

```kotlin
android {
    compileSdk = 37

    buildTypes {
        release {
            optimization {
                enable = true
            }
        }
    }
}
```

在 AGP 9.3 中，这个开关同时启用代码与资源优化，并带有等价于 `proguard-android-optimize.txt` 的平台默认规则。旧的 `isMinifyEnabled`、`isShrinkResources` 和 `proguardFiles` DSL 仍受支持，已有项目无需为了改写语法进行一次无收益迁移。

新 DSL 的自定义 keep 文件放在 `src/<variant>/keepRules/`，扩展名为 `.keep`，例如 `src/main/keepRules/reflection.keep`。库作者应提供精确的 consumer keep rules，让应用在完整程序图上做优化。`@Keep` 会保留被标注元素，适用于少量稳定入口；它无法替代对反射、JNI、序列化与动态代理边界的分析。

AGP 8.12 引入优化后的资源缩减，AGP 9.0 起在启用资源缩减时自动使用。第三方工具若在 R8 之后重写 DEX、资源表或资源名，可能破坏 DEX 布局、Baseline Profile、mapping 和资源引用一致性。此类工具需要独立兼容清单、崩溃验证与制品 diff。

AGP 9.3.0 还提供独立的 R8 配置分析任务，下面的命令可以在完整打包前生成报告：

```bash
./gradlew :app:analyzeReleaseR8Config
```

报告可定位覆盖范围过宽的 keep 规则。处理方式是缩小类、成员、注解或调用边界，再运行 release 测试与 retrace 验证；不能以删除全部 keep 规则换取体积数字。

### 依赖治理

依赖体积需要查看 release 结果，因为源码行数、AAR 大小和进入 DEX 的大小没有固定换算关系。R8 可移除不可达代码，但以下内容常会留下：

- 由 Manifest 合并引入的 component、provider 或 metadata；
- 反射与序列化规则保留的类和成员；
- AAR 中的资源、asset、JNI 库与 consumer rules；
- 多个 SDK 自带的重复 native 库或模型；
- `ServiceLoader` 配置、JNI 注册入口和运行时按名称查找的实现。

替换依赖前要对比 API 覆盖、行为、稳定性、许可、初始化成本和发布制品贡献。只使用库中一个很小的功能时，局部实现可能更轻；密码学、媒体编解码、数据库等领域不适合为了数百 KB复制高风险实现。

## 资源：裁剪配置，保留语义

### 语言资源

AGP 9.3 的应用资源 DSL 使用 `localeFilters`。若产品只声明有限语言，可用下面的配置过滤依赖带入的其他翻译：

```kotlin
android {
    androidResources {
        localeFilters += listOf("en", "zh-rCN")
    }
}
```

过滤后，未列出的 locale 资源不会进入该构建。配置值必须覆盖产品支持的语言、脚本和地区变体；应用内语言选择器、服务端下发语言或渠道差异也要纳入测试。AAB 的 language split 可以减少每台设备的初始下载，但应用若需要在运行时切换到未安装语言，还要采用 Play 的附加语言资源交付接口。

### 图片、XML 与资源表

位图优化应依据视觉质量、解码支持、透明度、动画和目标设备选择格式。WebP、PNG、JPEG、AVIF 的收益由素材内容与编码参数决定，没有通用缩减百分比。图标和简单几何图形可评估 VectorDrawable；VectorDrawable 是 Android XML 矢量资源，不能把任意 SVG 文件原样放入 `res/drawable/` 期待平台解析。

资源命名缩短、二进制 XML 重写和资源表改写属于构建工具变换。AAPT2、R8、资源访问方式、split、签名与增量发布都会影响安全边界。若项目采用这类方案，至少要验证：

- `Resources#getIdentifier()`、反射式资源访问和 WebView 路径；
- 动态 feature 与 asset pack 的资源引用；
- 所有密度、locale、夜间模式和产品 flavor；
- 资源 ID 稳定性要求以及增量补丁系统；
- 签名校验、Baseline Profile 和崩溃符号化。

### asset

Asset 不会因为业务代码不可达而自动消失。可以从 APK Analyzer 的 `assets/` 排序开始，逐项确认所有者、加载入口和更新策略。大模型、视频、离线地图或大字体集合需要评估 Play Asset Delivery、按需下载或服务端内容；自行下载可执行代码和 `.so` 还涉及完整性、加载安全与渠道政策，不能只按体积决策。

## native library：ABI、符号与 16KB 页

### ABI 裁剪要服从分发模型

Google Play 从 AAB 为设备生成 ABI configuration APK，arm64 设备不会收到 x86 库。直接发布单 APK 时，`abiFilters` 才会直接决定 APK 包含哪些 ABI。下面的配置只适用于产品已经明确停止支持其他 ABI 的场景：

```kotlin
android {
    defaultConfig {
        ndk {
            abiFilters += setOf("arm64-v8a")
        }
    }
}
```

这一设置会让其他 ABI 设备无法安装或无法加载 native 功能。变更前应从渠道设备分布、最低系统版本、模拟器与合作方设备确认支持范围。一个项目也可能只产出某些 ABI，因为源码构建和第三方 AAR 本来就没有提供其余库；“未配置过滤便一定打入四种 ABI”不成立。

### 发布符号和 APK 内符号是两件事

`ndk.debugSymbolLevel` 生成供 Play Console 做 native 崩溃符号化的独立符号归档，发布 APK 内的 `.so` 仍会按 release 规则 strip。`packaging.jniLibs.keepDebugSymbols` 会让匹配的 `.so` 跳过 strip，通常会显著增加交付体积。需要线上符号化时，应上传独立符号文件和 mapping，避免把调试符号留在用户制品中。

### 16KB 是兼容要求

Android 15 开始支持采用 16KB page size 的设备。它会影响 ELF `LOAD` segment 对齐、APK 内未压缩 `.so` 的 ZIP 对齐，以及 native 代码对页大小的假设。AGP 8.5.1 及以上配合 NDK r28 及以上时，工具链会按 16KB 要求打包并链接自研库；预编译 SDK 仍需逐个核对。AGP 9.3.0 的默认 NDK 是 28.2。

下面的命令分别验证运行环境、APK ZIP 对齐和 ELF segment 对齐：

```bash
adb shell getconf PAGE_SIZE
zipalign -c -P 16 -v 4 app-release.apk
bundletool dump config --bundle=app-release.aab | grep alignment
llvm-objdump -p lib/arm64-v8a/libexample.so | grep LOAD
```

16KB 设备的 `getconf` 应返回 `16384`，`zipalign -c` 只做校验，不会修改已签名 APK。AAB 配置应报告 `PAGE_ALIGNMENT_16K`。ELF 检查中每个 `LOAD` segment 的 alignment 要达到 `2**14`。应用需要覆盖所有自研和第三方 `.so`，不能只检查主库。

Native 代码不应把 `4096` 或 `PAGE_SIZE` 当作设备页大小。需要页大小时，可用下面的系统接口：

```cpp
#include <unistd.h>

long pageSize = sysconf(_SC_PAGESIZE);
```

返回值用于运行时的映射、对齐和缓冲区计算。还应审计 `mmap`、`mprotect`、共享内存、文件偏移与自定义分配器中的常量假设。

Android 17 可以关闭 16KB backcompat，并让不兼容二进制立即中止。测试设备可设置以下属性：

```bash
adb shell setprop bionic.linker.16kb.app_compat.enabled fatal
adb shell setprop pm.16kb.app_compat.disabled true
```

这些属性用于测试，不应写入应用发布流程。设置后要重新启动目标进程，并覆盖冷启动、JNI 注册、延迟加载、动态 feature 和每条 native 功能路径。Google Play 自 2025 年 11 月 1 日起要求面向 Android 15 及以上设备的新应用和更新支持 16KB page size。

## AAB 与 Play Feature Delivery

### Base module 仍是重点

App Bundle 会按 ABI、密度和语言生成 configuration APK，但 base module 中的通用代码和资源仍会交付给每位用户。动态 feature 适合边界清楚、使用率有限、可容忍下载等待的功能。把高频首屏代码拆成 on-demand module 会增加状态管理、失败处理和用户等待。

Play Core 已按功能拆成独立库。Play Feature Delivery 的当前官方依赖为 `2.1.0`，配置如下：

```kotlin
dependencies {
    implementation("com.google.android.play:feature-delivery:2.1.0")
    implementation("com.google.android.play:feature-delivery-ktx:2.1.0")
}
```

旧的单体 Play Core 依赖应迁移到按功能划分的库。依赖版本还需进入常规升级与安全审计，不能把本章版本视作永久锁定值。

On-demand feature 的清单需要声明交付模式，下面是模块清单的最小结构：

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:dist="http://schemas.android.com/apk/distribution">
    <dist:module
        dist:instant="false"
        dist:title="@string/feature_title">
        <dist:delivery>
            <dist:on-demand />
        </dist:delivery>
        <dist:fusing dist:include="true" />
    </dist:module>
</manifest>
```

`dist:on-demand` 让模块在安装时保持可选；`dist:fusing` 影响面向旧设备或 universal APK 的融合行为。模块的活动入口在调用前要确认模块已安装，外部应用也不应依赖一个尚未下载的 exported component。

按需安装是异步状态机。下面的示例区分“请求被接收”和“模块已经安装”：

```kotlin
val manager = SplitInstallManagerFactory.create(context)
var trackedSessionId = 0

lateinit var listener: SplitInstallStateUpdatedListener
listener = SplitInstallStateUpdatedListener { state ->
    if (state.sessionId() != trackedSessionId) return@SplitInstallStateUpdatedListener

    when (state.status()) {
        SplitInstallSessionStatus.REQUIRES_USER_CONFIRMATION -> {
            manager.startConfirmationDialogForResult(state, activity, 1001)
        }
        SplitInstallSessionStatus.INSTALLED -> {
            openInstalledFeature()
            manager.unregisterListener(listener)
        }
        SplitInstallSessionStatus.FAILED,
        SplitInstallSessionStatus.CANCELED -> {
            showFeatureInstallError(state.errorCode())
            manager.unregisterListener(listener)
        }
    }
}

manager.registerListener(listener)
val request = SplitInstallRequest.newBuilder()
    .addModule("advanced_editor")
    .build()

manager.startInstall(request)
    .addOnSuccessListener { sessionId -> trackedSessionId = sessionId }
    .addOnFailureListener { error ->
        manager.unregisterListener(listener)
        showRequestError(error)
    }
```

`addOnSuccessListener` 返回 session ID，只说明 Play 接收了请求。业务入口要等到 `SplitInstallSessionStatus.INSTALLED`。生产代码还要处理进程重启、已有 session、存储不足、网络失败、用户确认、模块已安装和 Play Store 不可用。

## Baseline Profile 与 Startup Profile

体积评审容易把两类 profile 混为一谈：

- **Baseline Profile** 向 ART 提供常用代码路径，安装期间或后续由 ART 对这些方法做 AOT 编译。
- **Startup Profile** 供 D8/R8 调整 DEX 布局，并帮助启动路径进入 primary DEX。

它们可能增加制品中的 profile 数据，也可能增加设备侧编译产物；对应收益是运行时性能，不应仅以 APK 字节数否决。R8 会根据重命名后的程序重写 profile，因此在 R8 之后修改 DEX 的工具可能使 profile 失配。

下面的路径用于检查 release 制品是否包含编译后的 Baseline Profile：

```text
APK: assets/dexopt/baseline.prof
AAB: BUNDLE-METADATA/com.android.tools.build.profiles/baseline.prof
```

官方要求编译后的 Baseline Profile 小于 1.5MB。源码中的文本 profile 与制品内二进制大小不同。安装后空间增长由 ART 编译策略、设备版本、ABI 和 profile 覆盖共同决定，应以目标设备的 Macrobenchmark 与磁盘观测评估，不能套用固定比例。

## 把体积检查放进发布流水线

一次稳定的门禁可以包含这些步骤：

1. 构建签名 release AAB，以及需要直接分发的 release APK。
2. 固定 `bundletool`，为主力设备、低存储设备和各 ABI 保存 versioned device spec。
3. 记录 AAB 上传体积、设备下载估算、安装 APK 集大小和主要目录贡献。
4. 对 DEX 包、resource、asset 和 `.so` 做版本差异分析。
5. 校验 R8 mapping、Baseline Profile、native symbol archive 与 16KB 对齐。
6. 当预算超限时，输出新增文件与依赖归属，由模块所有者确认。

预算应按产品与渠道建立。通用的“DEX 占比”“图片可压缩比例”或“每次发布最多增长多少 MB”不能替代项目基线。可操作的规则通常包含绝对上限、相对增量和少量高风险文件：

- 某固定 device spec 的压缩下载估算不得超过产品上限；
- 单次提交增长超过阈值时必须提供贡献者 diff；
- 新增 `.so`、字体、模型、视频和 install-time feature 必须列出所有者；
- ABI、locale、density 与 16KB 校验失败直接阻断对应渠道制品；
- mapping、native symbols 或 profile 缺失时阻断 release。

## Android 8 到 Android 17 的边界

| 版本或工具 | 与体积相关的边界 |
|---|---|
| Android 8 / API 26 | 本章支持范围下界；ART、split 与 profile 行为仍需按设备版本验证 |
| Android 9 / API 28 | Google Play 交付 Baseline Profile 的设备侧支持范围从 Android 9 起较完整；ProfileInstaller 可覆盖更低版本 |
| Android 15 / API 35 | 平台开始支持 16KB page-size 设备，native 制品要同时满足 ELF 与 ZIP 对齐 |
| AGP 8.12 | 引入优化后的资源缩减，需要在 8.12/8.13 显式启用 |
| AGP 9.0 | 启用资源缩减时自动采用优化后的资源缩减 |
| Android 17 / API 37 | 本章平台锚点；提供 16KB backcompat fatal 测试模式 |
| AGP 9.3.0 | 本章构建锚点；最高支持 API 37，提供 `optimization {}` DSL 和独立 R8 配置分析任务 |

历史项目采用旧 DSL、单 APK 或旧 NDK 时，可以保留现有发布方式，但要分别验证其交付体积、设备覆盖和 16KB 兼容性。升级构建工具后应重新生成基线，旧版本测得的百分比不能直接沿用。

## 排查清单

### 测量

- [ ] 比较的是签名 release 制品
- [ ] AAB、下载估算、安装 APK 集和安装后占用已分开记录
- [ ] `bundletool` 版本与 device spec 已固定
- [ ] 增量已定位到 DEX 包、资源、asset 或 `.so`

### 代码与资源

- [ ] AGP 9.3 release 已启用 `optimization { enable = true }`
- [ ] keep rules 有明确的反射、JNI 或序列化依据
- [ ] `analyzeReleaseR8Config` 未发现无意的宽范围保留
- [ ] locale、图片格式与动态资源访问经过全配置测试
- [ ] R8 输出之后没有未经验证的 DEX 或资源重写

### Native

- [ ] ABI 集合与每个发布渠道的设备范围一致
- [ ] APK 中的 `.so` 已 strip，独立 native symbols 可用于线上回溯
- [ ] 所有 ELF `LOAD` segment 满足 16KB 对齐
- [ ] `zipalign -c -P 16 -v 4` 校验通过
- [ ] 16KB 设备与 Android 17 fatal 模式覆盖了 JNI 和延迟加载路径
- [ ] native 代码没有固定 4KB 页大小的假设

### 交付与 profile

- [ ] Base module 只保留所有用户安装时需要的代码和资源
- [ ] On-demand 模块处理了完整安装状态与错误
- [ ] 非 Play 渠道的 AAB、split 或 universal APK 能力已单独确认
- [ ] Baseline Profile 与 Startup Profile 的用途和体积分别记录
- [ ] mapping、native symbols、profile 与发布制品来自同一次构建

## 参考资料

- [Reduce your app size](https://developer.android.com/topic/performance/reduce-apk-size)
- [About Android App Bundles](https://developer.android.com/guide/app-bundle)
- [Build an Android App Bundle](https://developer.android.com/build/app-bundle)
- [Enable app optimization with R8](https://developer.android.com/topic/performance/app-optimization/enable-app-optimization)
- [Android Gradle plugin 9.3.0 release notes](https://developer.android.com/build/releases/agp-9-3-0-release-notes)
- [AGP 9.3 `localeFilters` API](https://developer.android.com/reference/tools/gradle-api/9.3/com/android/build/api/dsl/ApplicationAndroidResources)
- [Overview of Play Core libraries](https://developer.android.com/guide/playcore)
- [Play Feature Delivery](https://developer.android.com/guide/playcore/feature-delivery)
- [Configure on-demand delivery](https://developer.android.com/guide/playcore/feature-delivery/on-demand)
- [Baseline Profiles overview](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [Configure Baseline Profile generation](https://developer.android.com/topic/performance/baselineprofiles/configure-baselineprofiles)
- [DEX layout optimizations and Startup Profiles](https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations)
- [Support 16KB page sizes](https://developer.android.com/guide/practices/page-sizes)
- [`zipalign`](https://developer.android.com/tools/zipalign)
- [Include native symbols in a release build](https://developer.android.com/build/include-native-symbols)
- [AOSP `android-17.0.0_r1`: `ResourceTypes.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/androidfw/ResourceTypes.cpp)
- [AOSP `android-17.0.0_r1`: DEX loader](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/libdexfile/dex/dex_file_loader.cc)
- [AOSP `android-17.0.0_r1`: bionic linker](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/linker/linker.cpp)
