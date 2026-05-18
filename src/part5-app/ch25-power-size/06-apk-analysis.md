---
title: "APK 体积分析与瘦身"
chapter: "25.6"
section: "25.6"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-14"
last_verified_against: "Android Developers docs 2026-03/2026-04 + AOSP master code search"
confidence: medium
drafted_date: "2026-05-14"
polish_count: 0
sources:
  - type: official
    path: "https://developer.android.com/studio/debug/apk-analyzer"
  - type: official
    path: "https://developer.android.com/topic/performance/reduce-apk-size"
  - type: official
    path: "https://developer.android.com/studio/build/shrink-code"
  - type: official
    path: "https://developer.android.com/topic/performance/app-optimization/enable-app-optimization"
  - type: official
    path: "https://developer.android.com/topic/performance/app-optimization/customize-which-resources-to-keep"
  - type: official
    path: "https://developer.android.com/ndk/guides/abis"
  - type: official
    path: "https://developer.android.com/tools/bundletool"
  - type: aosp
    path: "https://cs.android.com/android/platform/superproject/+/master:frameworks/base/services/core/java/com/android/server/pm/PackageAbiHelperImpl.java"
  - type: aosp
    path: "https://cs.android.com/android/platform/superproject/+/master:frameworks/base/core/java/com/android/internal/content/NativeLibraryHelper.java"
  - type: aosp
    path: "https://cs.android.com/android/platform/superproject/+/master:frameworks/base/libs/androidfw/include/androidfw/ResourceTypes.h"
  - type: book-structure
    path: "Clippings/Android 性能优化 - 原理：重新认识 APK 安装包.md"
  - type: book-structure
    path: "Clippings/Android 性能优化 - dex 文件的体积优化实战.md"
  - type: book-structure
    path: "Clippings/Android 性能优化 - 资源文件的体积优化实战.md"
  - type: book-structure
    path: "Clippings/Android 性能优化 - so 文件的体积优化实战.md"
tags: [apk-size, apk-analyzer, r8, resource-shrink, abi-filter]
related_chapters: ["25.7", "25.8", "12.1"]
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: pending
task2b_state: fixed
reviewed_by: openclaw-task6
reviewed_date: "2026-05-14"
task6_result: pass-light-edit
last_task6_at: "2026-05-14T19:10:00+08:00"
last_task6_review_log: logs/review/2026-05-14-19-review.md
task6_review_notes: "2026-05-14 Task6：L1/L2 小修 3 处；写作层通过，等待 Task9 技术复核。"
task2b_result: fixed
task9_result: needs-rework
task9_reviewed_by: openclaw-task9
task9_reviewed_date: '2026-05-14'
last_task9_at: '2026-05-14T19:29:00+08:00'
last_task9_review_log: logs/deep-review/2026-05-14-19-deep-review.md
task9_review_notes: '2026-05-14 19:29 Task9 deep-review: needs-rework。P0 1 / P1 0 / P2 0；已写入 queue.json，等待 Task2B 回炉。'
---

# APK 体积分析与瘦身

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 APK Analyzer 与体积构成分析
- 🔹 代码瘦身：ProGuard / R8 规则优化
- 🔹 资源瘦身：无用资源移除、资源混淆
- 🔹 `.so` 库瘦身：ABI 过滤、动态下发

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 APK 体积分析与瘦身

包体积治理的第一步不是改 Gradle 配置，而是把体积账算清楚。一个 release 包里通常有 dex、`resources.arsc`、`res/`、`assets/`、`lib/<abi>/`、`AndroidManifest.xml` 和签名文件；它们进入安装、启动和内存映射路径的方式不同，对应的优化手段也不同。APK 结构、`resources.arsc` 作用、dex / res / lib 三类产物的基础原理，详见 12.1 节。这里处理实战流程：怎么定位体积来源，怎么评估改动收益，怎么把 R8、资源缩减和 ABI 策略纳入发版检查。

[结构参考: Clippings/Android 性能优化 - 原理：重新认识 APK 安装包.md]

## APK Analyzer 与体积构成分析

[已验证: 官方文档, developer.android.com/studio/debug/apk-analyzer]

APK Analyzer 适合做包体积排查的基线工具。Android Studio 文档确认它可以查看 APK 或 App Bundle 中各文件的绝对大小和相对大小，查看 dex 文件结构，查看最终打包后的 `AndroidManifest.xml`、资源和二进制文件，并支持两个 APK 或 App Bundle 的并排对比。

一次有效的体积分析要同时记录几组口径：

- **Raw File Size**：ZIP entry 解压后的原始大小，用来判断某类产物自身是否膨胀，例如 dex 代码、图片、`.so`、`assets` 原文件。
- **Download Size**：按 Google Play 分发时的压缩下载大小估算，用来判断用户下载包的变化。图片、文本、dex、`.so` 的压缩表现不同，只看原始大小容易误判收益。
- **按目录归因**：`classes*.dex` 对应 Kotlin / Java 代码和依赖；`res/` 与 `resources.arsc` 对应编译资源；`assets/` 多见于字体、离线包、模型、Web 资源；`lib/<abi>/` 对应 native 库副本。
- **按版本对比**：发版前把当前 release 包和上一版 release 包放进 APK Analyzer 对比，优先处理增长项，而不是重新扫全包。

命令行环境要补一层可复现检查。`apkanalyzer` 可以输出 APK 总大小和估算下载大小；App Bundle 场景下，`bundletool get-size total` 可以按 `.apks` 估算压缩后的下载体积。[已验证: 官方文档, developer.android.com/tools/apkanalyzer；developer.android.com/tools/bundletool]

下面这组命令用于把体积检查接入 CI。读数只作为门禁输入，是否阻断发布要结合业务版本和渠道包策略判断。

```bash
# APK 总大小与估算下载大小
apkanalyzer apk file-size -h app-release.apk
apkanalyzer apk download-size -h app-release.apk

# AAB 生成 APK set 后估算下载大小
bundletool build-apks --bundle=app-release.aab --output=app-release.apks
bundletool get-size total --apks=app-release.apks
```

如果本轮 APK Analyzer 显示主要增长来自 dex，就进入 R8 / 依赖治理；来自 `res/` 或 `resources.arsc`，优先检查资源缩减、图片格式和资源命名；来自 `lib/`，先看 ABI 副本和 debug symbol；来自 `assets/`，检查离线包、模型、字体和配置文件是否应改为首启后下载或按需下载。

## 代码瘦身：ProGuard / R8 规则优化

[已验证: 官方文档, developer.android.com/studio/build/shrink-code]

Android 现在的代码瘦身以 R8 为主。R8 会从 manifest 中声明的 Activity、Service、Provider 等入口出发，构建可达代码图，移除不可达的类和方法；随后执行方法内联、类合并、命名缩短等优化。ProGuard 规则仍然沿用在 R8 配置里，但工程判断要从“开没开混淆”改成“规则有没有过度保留”。

release 构建至少保留下面这组开关。资源缩减依赖代码缩减，单独打开 `isShrinkResources` 没有意义。

```kotlin
android {
    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
}
```

这段配置让 R8 参与代码缩减、混淆和优化，也让 AGP 在 R8 移除无用代码后继续移除不可达资源。构建后要检查 `build/outputs/mapping/release/` 里的 `mapping.txt`、`usage.txt` 和资源诊断文件，确认被移除的是预期代码和资源。

R8 规则排查按这个顺序处理：

- **先看依赖增长**：APK Analyzer 打开 `classes.dex`，按包名找增长最大的库或模块。只用到一个功能却带入整套 SDK，是 dex 膨胀最常见的来源。
- **再看 keep 规则**：`-keep class com.xxx.** { *; }` 会让整个包逃过大部分优化。反射、序列化、JNI 注册和框架回调需要 keep，但规则应收窄到类、成员或注解粒度。
- **检查 consumer rules**：AAR 自带的 consumer ProGuard rules 会传递到 App。某些三方库为了避免误删，会把规则写得很宽，导致 App 侧 R8 空间变小。
- **保留可回溯能力**：混淆后必须归档 `mapping.txt`。Crash 平台、ANR 堆栈和线上日志都依赖它还原符号。

AGP 8.12 / 8.13 支持手动开启优化版资源缩减；AGP 9.0 起，在 `isShrinkResources = true` 时自动使用这一流程。它会让资源缩减更贴近 R8 的引用图，但动态资源名仍然要显式声明保留，详见 25.7 节。[已验证: 官方文档, developer.android.com/topic/performance/app-optimization/enable-app-optimization]

[结构参考: Clippings/Android 性能优化 - dex 文件的体积优化实战.md]

## 资源瘦身：无用资源移除、资源混淆

[已验证: 官方文档, developer.android.com/topic/performance/reduce-apk-size]

资源瘦身分两类：减少资源数量和减少单个资源大小。前者靠 lint、资源缩减、变体过滤和资源合并；后者靠图片格式、字体子集化、资源名压缩和大型资源按需下载。12.1 节已经覆盖资源类型和 `resources.arsc` 基础，这里只写操作路径。

无用资源移除先用官方工具确认：

- **lint / Android Studio inspection**：扫描 `res/` 中没有被代码引用的资源，适合手工清理老图片、老布局和废弃主题。
- **`isShrinkResources = true`**：配合 R8 删除不可达代码引用的资源。官方文档明确说明，构建过程中先由 R8 移除无用代码，再由 AGP 移除无用资源。
- **`res/raw/*.keep.xml`**：动态资源名无法完全静态分析，使用 `tools:keep` 和 `tools:discard` 指定保留或丢弃规则。keep 文件有全局作用域，文件名要带包名前缀，避免库之间规则冲突。[已验证: 官方文档, developer.android.com/topic/performance/app-optimization/customize-which-resources-to-keep]
- **`resourceConfigurations` / `resConfigs`**：移除不需要的语言、密度等替代资源。AAB 分发默认会按设备语言、屏幕密度和 ABI 生成配置 APK；普通 APK 或国内渠道包仍要显式检查这些资源是否被全量打入。

动态资源引用要单独列风险清单。`Resources.getIdentifier()`、拼接资源名、主题皮肤包、WebView 与 native 混合页面常把资源引用藏在字符串里；R8 和资源缩减器很难从静态引用图里找到这些资源。处理方式是建立白名单：保留资源名前缀、记录调用点、在 `resources.txt` 中检查缩减结果，并给动态加载路径加回归用例。

资源混淆和 `resources.arsc` 处理属于收益明显但风险较高的优化。资源文件名变短后，`resources.arsc` 中的字符串池会变小；重复图片也可以在资源表层面复用同一份文件路径。AOSP 的 `ResourceTypes.h` 定义了资源表相关结构，能说明 `resources.arsc` 是二进制资源表，不是文本清单。[已验证: AOSP master, frameworks/base/libs/androidfw/include/androidfw/ResourceTypes.h]

这一类优化不建议在没有测试覆盖的项目里直接引入。更稳的顺序是：先开 R8 + 官方资源缩减，再处理图片格式和语言 / 密度过滤，再评估资源混淆。资源混淆上线前至少要覆盖启动页、换肤、通知图标、桌面 widget、WebView bridge、动态页面和多语言场景。

[结构参考: Clippings/Android 性能优化 - 资源文件的体积优化实战.md]

## `.so` 库瘦身：ABI 过滤、动态下发

[已验证: 官方文档, developer.android.com/ndk/guides/abis]

`.so` 体积问题通常不是单个库大，而是同一套库按多个 ABI 重复打包。NDK 文档说明 fat APK 会明显大于只包含单一 ABI 二进制的 APK，并建议使用 App Bundle 或 APK Splits，在保持设备兼容性的同时减少用户实际下载大小。

排查 `.so` 先看三件事：

- **ABI 是否全量打入**：`lib/arm64-v8a/`、`lib/armeabi-v7a/`、`lib/x86/`、`lib/x86_64/` 同时存在时，先确认线上是否还需要 x86 或 32 位 ARM。模拟器专用 ABI 不应出现在正式渠道包里。
- **debug symbol 是否被剥离**：NDK 文档建议使用 strip 工具移除 native 库中的非必要调试符号。正式包里保留完整符号会显著放大 `lib/` 目录，符号文件应单独归档给崩溃还原系统。
- **native 库是否属于低频功能**：OCR、地图、音视频编辑、游戏引擎、模型推理等库经常只服务少数路径，适合放到动态特性模块、Play Asset Delivery，或国内渠道的自研按需下载方案。

使用普通 APK 分发时，可以用 `abiFilters` 限定打包 ABI。下面的配置只表达打包策略，是否只保留 64 位要结合设备占比、性能要求和渠道政策决定。

```kotlin
android {
    defaultConfig {
        ndk {
            abiFilters += listOf("arm64-v8a")
        }
    }
}
```

这段配置会让 APK 只包含 `arm64-v8a` 对应 native 库。对于仍需覆盖 32 位设备的应用，应使用多 APK、AAB 配置 APK，或保留 `armeabi-v7a`。如果一刀切删除 32 位 ABI，旧设备会在安装或加载 native 库时失败。

Android 平台安装 native 库时，会按设备 primary ABI 查找 `lib/<primary-abi>/lib<name>.so`，找不到时再看 secondary ABI。安装期 ABI 选择链路为 `PackageAbiHelperImpl.derivePackageAbi()` → `NativeLibraryHelper.findSupportedAbi()` 确定最佳 ABI → `copyNativeBinariesForSupportedAbi()` 将对应 `.so` 复制到应用 nativeLibraryDir；运行时 linker 按 `nativeLibraryDir` 搜索 `.so`。[已验证: AOSP master, frameworks/base/services/core/java/com/android/server/pm/PackageAbiHelperImpl.java; frameworks/base/core/java/com/android/internal/content/NativeLibraryHelper.java]

`android:extractNativeLibs` 和 AGP 的 native library packaging 策略会影响 `.so` 是否从 APK 解压到文件系统。Android 6.0+ 支持未压缩且页对齐的 native 库直接从 APK 加载；这能减少磁盘副本，但 APK 内 `.so` 可能不再经过 ZIP 压缩。工程上不能只看 APK 文件大小，要同时比较下载大小、安装后占用、启动加载成本和崩溃还原能力。更细的 AAB / 动态特性分发策略详见 25.8 节。

[结构参考: Clippings/Android 性能优化 - so 文件的体积优化实战.md]

## [自动发现] 体积门禁比一次性瘦身更可靠

包体积优化不能只在版本末期突击处理。更稳的做法是在 CI 中保留基线包，按模块、目录和文件类型记录差异：dex 增长超过阈值时要求说明依赖来源；`res/` 增长超过阈值时要求列出新增图片和多语言资源；`lib/` 增长超过阈值时要求说明 ABI 与符号策略；`assets/` 增长超过阈值时要求说明是否可按需下载。

门禁记录不需要复杂系统，早期可以从 `apkanalyzer`、`bundletool get-size total`、APK Analyzer 对比截图和构建产物归档开始。要把“这次为什么大了”记录下来，避免下个版本再重复排查同一个 SDK、同一批图片或同一套 ABI 副本。

## 小结

APK 体积分析按文件类型归因：dex 看 R8 和依赖，资源看 shrink / 图片 / `resources.arsc`，native 库看 ABI、符号和按需分发，`assets` 看离线包和大文件。25.6 的产出应是一张可复现的体积账；具体 R8 规则和资源格式细节进入 25.7，AAB、动态特性和 Play Asset Delivery 进入 25.8。
