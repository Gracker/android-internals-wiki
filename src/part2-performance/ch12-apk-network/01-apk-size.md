---
title: "APK 体积优化"
section: "12.1"
chapter: "12.1"
status: ready-for-review
drafted_date: "2026-04-03"
drafted_by: "openclaw-task2a"
reviewed_date: "2026-04-10"
reviewed_by: "openclaw-task6"
task6_result: pass-light-edit
task6_reviewed_date: "2026-04-16"
polish_count: 1
polish_date: "2026-04-10"
polish_by: "task2b-polish"
applicable_versions: "Android 8 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-03"
last_verified_against: "AGP 8.7 / R8 default"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/reduce-apk-size"
  - type: official
    path: "https://developer.android.com/build/shrink-code"
  - type: official
    path: "https://developer.android.com/build/app-bundle"
  - type: official
    path: "https://developer.android.com/guide/playcore/feature-delivery"
  - type: blog
    path: "得物技术《包体积：Layout 二进制文件裁剪优化》2023-09"
tags: [apk, r8, proguard, app-bundle, resource-optimization, native-libs, dex, code-shrinking, webp, abi-filter, dynamic-feature, apk-analyzer]
related_chapters: ["8.3", "14.1", "15.6"]
pipeline_stage: task9_pending
task6_state: reviewed
task9_state: pending
task2b_state: idle
---

# APK 体积优化

## 为什么要关注 APK 体积

当一个用户在地铁里用 4G 网络搜索一个 App，Google Play 页面显示「下载大小 156 MB」——这个数字很可能直接劝退了他。Google 在 2018 年的一项内部研究中发现，APK 体积每增加 6 MB，安装转化率就下降约 1%[待验证: Google 内部数据，引用自 Android Developers Blog]。在国内应用市场，这个数字只会更残酷——很多用户还在按流量计费，或者手机存储已经捉襟见肘。

体积问题不仅仅是下载体验。APK 安装后，dex 文件需要被解压、验证、编译（AOT/JIT）；resources.arsc 会被加载到内存；native libraries 被解压到磁盘。体积越大，安装时间越长，运行时的内存占用也越高。对于 MTK、高通这类平台上做性能优化的工程师来说，包体积和启动速度、内存占用之间存在一条不那么显眼但确实存在的因果链。

本章的目标不是罗列一堆优化技巧——那种清单任何博客上都能找到。我们想回答的核心问题是：**一个 APK 里面到底装了什么，哪些东西占了多少空间，我们用什么工具能看清楚，以及从工程实践的角度，哪些优化手段投入产出比最高。**

## APK 里面到底装了什么

[已验证: 官方文档, developer.android.com/topic/performance/reduce-apk-size]

一个标准的 release APK 就是一个 ZIP 压缩包。解压之后，我们通常会看到以下几类文件：

**Dex 文件（classes.dex, classes2.dex, ...）** 是编译后的 Dalvik 字节码。所有 Kotlin/Java 代码——包括业务代码、AndroidX 库、第三方 SDK——最终都会编译进 dex 文件。一个中等规模的 App，dex 通常占总大小的 30%-50%。当方法数超过 65536（即一个 dex 文件的理论上限）时，Gradle 会自动进行多 dex 分包，产生 classes2.dex、classes3.dex 等文件。

**resources.arsc** 是资源索引表。它记录了所有资源 ID 到具体资源的映射关系——比如 `R.string.app_name` 对应哪个字符串值，`R.drawable.icon` 对应哪个 drawable 资源。这个文件不大（通常几百 KB 到几 MB），但它是资源加载的入口点。资源混淆工具（如 AndResGuard）的核心优化目标之一就是缩短这个表中的字符串条目。

**res/ 目录**包含编译后的二进制资源文件——布局 XML 的二进制编译版、图片资源、颜色值等。Android 构建工具会把 XML 布局文件编译成二进制格式（AXML），这不是普通的文本 XML。得物技术团队曾经通过裁剪二进制 XML 中的冗余字段（如 Namespace 声明、重复的属性名）实现了单个 Layout 文件体积缩减约 40%[已验证: 来源见 Cubox/包体积：Layout 二进制文件裁剪优化｜得物技术-2023-09-18.md]。

**assets/ 目录**存放原始文件——字体、WebView 加载的 HTML、配置文件等。这些文件不会被编译，原样打包进 APK。如果 App 内置了字体文件或大型 JSON 配置，assets 可能成为体积大户。

**lib/ 目录**是 native libraries（.so 文件）的存放位置。这个目录按 ABI（Application Binary Interface）分子目录——`arm64-v8a/`、`armeabi-v7a/`、`x86/`、`x86_64/`。每一个 ABI 子目录下都是一份完整的 so 库副本。所以如果 Gradle 里没有配置 `ndk.abiFilters`，APK 里可能同时包含了 4 个架构的 native 库——arm64 设备只需要其中 1 份，另外 3 份全是浪费。

**META-INF/ 目录**包含签名信息。这个目录下的文件（CERT.SF、CERT.RSA、MANIFEST.MF）在 APK 安装时用于验证完整性，体积通常不大。

`AndroidManifest.xml` 是编译后的二进制清单文件，描述了 App 的组件、权限、SDK 版本等信息。

理解这个结构是优化体积的前提。不同类型的文件需要完全不同的优化策略：dex 靠代码缩减和混淆，res 靠资源压缩和格式替换，lib 靠 ABI 过滤和动态下发。**不加区分地对整个 APK 做「压缩」是无效的**——dex 和 so 已经是压缩格式，再压缩不会减小体积，反而增加安装时的解压开销。

## APK Analyzer：先测量，再优化

[已验证: 官方文档, developer.android.com/studio/debug/apk-analyzer]

盲目优化是工程上的大忌。在动手之前，我们需要知道 APK 里到底什么最占空间。Android Studio 自带的 **APK Analyzer** 是做这件事的第一选择。

打开方式很简单：在 Android Studio 中选择 **Build → Analyze APK...**，然后选中 release APK 文件。APK Analyzer 会展示一个树状结构，列出每个文件和目录的大小，包括 **Raw Size**（未压缩原始大小）和 **Download Size**（估算的下载大小，考虑了 Google Play 的进一步压缩）。

在 APK Analyzer 的顶部，有几个关键信息值得注意：

**Total Size** 给出了整个 APK 的大小概览。如果这个数字和预期差距很大，说明构建配置可能有问题（比如 debug 构建没开混淆，或者意外包含了一个大型 SDK）。

**Dex 文件分析**：点击 classes.dex，APK Analyzer 会展示一个类列表，按包名组织。我们可以看到每个包（也就是每个库或模块）贡献了多少方法和多少字节。这一步通常能立即暴露问题——比如某个只用了其中一个工具方法的工具库，却带着 20000 个方法和 5 MB 的 dex 代码。

**资源对比**：APK Analyzer 的另一个实用功能是**对比两个 APK**。把优化前后的两个 APK 拖进去，它会把差异高亮出来，确认优化是否生效、有没有意外引入新的资源。

在命令行环境下，可以使用 Google 提供的 `bundletool`（App Bundle 的配套工具）或 `aapt dump badging` 来获取 APK 结构信息，适合集成到 CI/CD 流水线中做体积门禁检查。

## 代码瘦身：让 R8 帮你砍掉不需要的代码

[已验证: 官方文档, developer.android.com/build/shrink-code]

### R8 是什么，为什么它比 ProGuard 更好

R8 是 Android 构建工具链中的代码优化器，从 Android Gradle Plugin（AGP）3.4.0 开始取代 ProGuard 成为默认工具。它做四件事：

**代码缩减（Code Shrinking / Tree Shaking）**——通过分析代码的入口点（Activity、Service、ContentProvider 等在 AndroidManifest 中声明的组件），R8 追踪所有可达的代码路径，不可达的类和方法会被直接移除。这对第三方库尤其有效——我们可能只用了 Guava 的 `Strings.isNullOrEmpty()`，但 Guava 的完整 jar 包含几千个方法，R8 会把没用到的那部分全部删掉。

**资源缩减（Resource Shrinking）**——与代码缩减联动，一旦某个代码被移除，该代码中引用的资源文件（如仅在已删除 Activity 中使用的布局文件）也会被移除。

**代码混淆（Obfuscation）**——把 `com.example.androidperformance.MainActivity` 重命名为 `a.b.c`。这不仅能保护代码，更直接的效果是大幅缩减 dex 文件中的字符串常量池。一个有上千个类名的项目，混淆后 dex 可以减小 10%-20%。

**代码优化（Optimization）**——R8 Full Mode（AGP 8.0+ 默认开启）会执行方法内联、类合并、无用接口移除等更激进的优化。比如如果一个方法只被调用一次，R8 可能会直接把方法体内联到调用点，消除方法调用的开销。

### 怎么开启 R8

在模块级 `build.gradle`（或 `build.gradle.kts`）中：

```kotlin
android {
    buildTypes {
        release {
            isMinifyEnabled = true      // 开启代码缩减 + 混淆 + 优化
            isShrinkResources = true    // 开启资源缩减（依赖 isMinifyEnabled）
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
}
```

两个开关都要打开。`isMinifyEnabled` 控制 R8 的代码缩减和混淆，`isShrinkResources` 控制资源缩减。资源缩减必须依赖代码缩减先运行，因为它需要知道哪些代码还在使用——只有代码层面确认无用的资源，才会被移除。

注意 `proguard-android-optimize.txt` 这个文件名。Android 提供两个默认规则文件：`proguard-android.txt` 是保守配置，`proguard-android-optimize.txt` 包含更多优化选项。对于新项目，直接用 optimize 版本即可。

### Keep 规则：告诉 R8 别删错了

R8 的静态分析有一个盲区：**通过反射调用的代码，R8 看不到调用链**。如果用 `Class.forName("com.example.MyClass")` 或者 Gson 反序列化 JSON 到某个类，R8 可能会把那个类当作无用代码删掉。

解决方法是在 `proguard-rules.pro` 中添加 keep 规则：

```proguard
-keep class com.example.MyModelClass { *; }
```

但这里有一个常见的工程陷阱：**keep 规则写得越宽，R8 能优化的空间就越小**。一条 `-keep class com.example.** { *; }` 就可能让整个包名下的所有类逃过优化。Android 官方推荐的做法是尽量使用 `@Keep` 注解，精确标注需要保留的类和成员：

```kotlin
@Keep
data class ApiResponse(
    val status: String,
    val data: List<Item>
)
```

这样 R8 知道只保留 `ApiResponse` 及其字段，而不会波及包内其他类。

在 APK Analyzer 中，如果发现某个库的代码几乎完整保留（混淆后的包名还在），很可能就是这个库缺少精确的 keep 规则，或者它的构建产物自带了过宽的 consumer ProGuard rules。检查 `.aar` 文件中的 `proguard.txt`，看看是不是它把整个库都 keep 住了。

### R8 Full Mode 和新版资源缩减

AGP 8.0 开始，R8 Full Mode 成为默认行为。Full Mode 比 compatibility mode 更激进——它会改变类的可见性（把 public 改为 package-private）、内联短方法、合并只有单一实现的接口。如果项目是从很早的 AGP 版本迁移过来的，检查 `gradle.properties` 里有没有 `android.enableR8.fullMode=false`，如果有就删掉这一行。

AGP 8.12.0 引入了**优化的资源缩减**（Optimized Resource Shrinking），把资源缩减逻辑也整合进了 R8 的优化管线。启用方式：

```properties
# gradle.properties
android.r8.optimizedResourceShrinking=true
```

[适用版本: AGP 8.12.0+]

这个选项能让 R8 在代码优化阶段就识别出无用资源，比传统的资源缩减更精准，减少误删有用的资源。

## 资源瘦身：图片、布局和字符串的优化

### 图片格式替换：PNG → WebP

图片通常是 `res/` 目录下体积最大的贡献者。把 PNG 替换为 WebP 是投入产出比最高的优化之一：在同等视觉质量下，WebP 比 PNG 小 25%-35%；如果允许有损压缩（对于照片类图片完全可以），压缩率可达 60%-70%[已验证: 官方文档, developer.android.com/topic/performance/reduce-apk-size#image-compression]。

Android Studio 提供了批量转换功能：右键点击 `res/drawable` 目录，选择 **Convert to WebP...**，可以选择无损或有损模式，还能设置质量参数。对于 4.x 及以上设备（如今基本上是所有设备），WebP 的兼容性已经不是问题。

对于简单的矢量图形（图标、简单形状），直接使用 **VectorDrawable**（SVG 格式）更好。矢量图不依赖屏幕密度，一个文件适配所有分辨率，而且体积通常比同等效果的 PNG 小得多。不过矢量图也有边界——复杂的矢量图在运行时渲染的开销可能比加载一张位图更大，所以不适合用于照片或复杂插图。

### 资源混淆：AndResGuard

资源混淆工具（如腾讯的 AndResGuard、字节跳动的 ResShrinker）通过缩短资源路径和文件名来减小 APK 体积。把 `res/drawable-hdpi/icon_background_launch_screen.png` 重命名为 `r/d/a.png`，看似只省了几个字符，但当 App 有上千个资源文件时，这种优化累积起来可以节省数百 KB 到数 MB。

资源混淆的核心操作包括：将资源文件路径缩短为 `r/a/a.png` 这样的短路径，将 `resources.arsc` 中的字符串条目缩短为无意义的短字符串，合并重复的资源文件（同名同内容的资源只保留一份）。

配置方法（以 AndResGuard 为例）：

```groovy
andResGuard {
    mappingFile = null
    use7zip = true
    useSign = true
    keepRoot = false
    whiteList = [
        "R.drawable.app_icon",  // 不能混淆启动图标
        "R.string.app_name",
    ]
    compressedFileFilter = [
        "*.png", "*.jpg", "*.jpeg", "*.webp"
    ]
}
```

`whiteList` 是关键——有些资源不能混淆，比如桌面启动图标（launcher 会通过固定资源名查找）、Notification 的小图标等。

### 按密度过滤和按语言过滤

如果 App 不需要支持所有屏幕密度，可以在 Gradle 中指定：

```kotlin
android {
    defaultConfig {
        resConfigs("zh", "en")           // 只保留中文和英文资源
        resConfigs("hdpi", "xhdpi", "xxhdpi", "xxxhdpi")  // 只保留这几种密度
    }
}
```

一个真实案例：某 App 的 `res/` 目录下有 6 种密度的图片资源（mdpi、hdpi、xhdpi、xxhdpi、xxxhdpi、tvdpi），通过过滤掉几乎无人使用的 mdpi 和 tvdpi，资源体积直接减半。对于语言资源也一样——很多第三方库（如 Google Play Services）自带了几十种语言的字符串，通过 `resConfigs` 过滤后可以大幅减小 `resources.arsc` 的大小。

## Native 库瘦身：ABI 过滤与动态下发

### ABI 过滤

Native libraries（.so 文件）经常是 APK 体积的最大贡献者，尤其是包含音视频处理、机器学习等 native 代码的 App。问题在于默认构建会把所有 ABI 架构的 so 都打包进去。

现实情况是：2024 年以后，Google Play 已经强制要求提交的 App 支持 64 位架构（arm64-v8a）。绝大多数现代 Android 手机都是 arm64。`x86` 和 `x86_64` 架构主要用于模拟器（和极少数 Chrome OS 设备），`armeabi-v7a`（32 位 ARM）覆盖率也在快速萎缩。

最直接的优化：只保留目标设备实际需要的架构。

```kotlin
android {
    defaultConfig {
        ndk {
            abiFilters += listOf("arm64-v8a", "armeabi-v7a")
        }
    }
}
```

对于 Google Play 分发的 App，更好的方案是使用 App Bundle（下一节讨论）——Play 会根据用户设备的 ABI 自动生成只包含对应架构的 APK，不需要手动过滤。

### Strip 符号表

编译 so 库时，默认会包含调试符号表（symbol table）和部分调试信息。这些信息对 release 构建毫无用处，但可能让 so 体积膨胀数倍。

在 `CMakeLists.txt` 中确保设置了 strip 选项：

```cmake
set_target_properties(your-lib PROPERTIES
    LINK_FLAGS "-Wl,--strip-all"
)
```

或者在 Gradle 的 `externalNativeBuild` 配置中：

```kotlin
android {
    buildTypes {
        release {
            externalNativeBuild {
                cmake {
                    arguments("-DANDROID_STRIP_DEBUG_SYMBOLS=ON")
                }
            }
        }
    }
}
```

[待验证: ANDROID_STRIP_DEBUG_SYMBOLS 在 AGP 8.x 中是否仍然有效]

### 动态下发 so

对于某些大型 native 库（如人脸识别 SDK、地图引擎），最激进的优化方案是**不在 APK 中打包**，而是在用户首次使用相关功能时从服务器下载。这种方式需要自己管理下载、校验、加载的完整流程，实现复杂度较高，但收益明确：主包体积可以减少数十 MB，直接提升安装转化率。

一个折中方案是使用 Play Core Library 的 **on-demand delivery**：将大型 so 库放在 Dynamic Feature Module 中（下一节讨论），用户安装基础 APK 时不包含这些库，只有当用户导航到需要该库的功能页面时才触发下载。

## App Bundle 与 Dynamic Feature Module

[已验证: 官方文档, developer.android.com/build/app-bundle]

### App Bundle 解决了什么问题

传统 APK 分发模式有一个根本性的问题：**一个 APK 必须适配所有设备**。结果是，同一个 APK 里同时装着 hdpi 和 xxxhdpi 的图片、arm64 和 x86 的 so 库、中文和斯瓦希里语的字符串。用户在 arm64 设备上下载了这个 APK，其中 70% 的资源对他毫无用处——但他不得不下载。

Android App Bundle（AAB）是 Google 在 2018 年推出的发布格式，它改变了这个模型。开发者上传一个 AAB 到 Google Play，Play 的服务器会根据每个用户的设备配置（屏幕密度、CPU 架构、语言）自动生成一个**最小化的 APK**（称为 Split APK）。结果是：用户只下载他设备真正需要的那部分资源。

从 APK 切换到 AAB，通常可以看到下载大小减小 **15%-40%**，不需要改一行业务代码。这也是 Google Play 自 2021 年 8 月起强制要求新 App 使用 AAB 发布的原因。

### Dynamic Feature Module：按需加载功能

App Bundle 的进阶用法是 **Dynamic Feature Module**（动态功能模块）。它的理念是把 App 拆分为一个 base module 和多个 feature module：

- **Install-time delivery**：模块随 base 一起安装，但可以在用户使用后卸载（适合新手引导模块）
- **On-demand delivery**：模块仅在用户访问对应功能时才下载（适合支付模块、滤镜编辑器等非核心功能）
- **Conditional delivery**：模块根据设备条件自动决定是否安装（如只在有 VR 功能的设备上安装 VR 模块）

配置一个 on-demand 的 Dynamic Feature Module：

首先在模块的 `build.gradle.kts` 中声明：

```kotlin
android {
    // 动态功能模块的配置
}
dynamicFeatures.add(":feature:payment")
```

然后在 feature module 的 `AndroidManifest.xml` 中：

```xml
<dist:module
    dist:instant="false"
    dist:title="@string/title_payment">
    <dist:delivery>
        <dist:on-demand />
    </dist:delivery>
    <dist:fusing dist:include="true" />
</dist:module>
```

在运行时使用 Play Core Library 请求加载：

```kotlin
val splitInstallManager = SplitInstallManagerFactory.create(context)
val request = SplitInstallRequest.newBuilder()
    .addModule("payment")
    .build()

splitInstallManager.startInstall(request)
    .addOnSuccessListener {
        // 模块已下载，可以导航到支付页面
    }
    .addOnFailureListener { e ->
        // 下载失败处理
    }
```

[适用版本: Play Core Library 1.6+ / Android 5.0 (API 21)+]

使用 Dynamic Feature Module 时，有几个工程上的注意点。第一，模块之间的代码依赖需要仔细规划——feature module 可以依赖 base module，但两个 feature module 之间不能直接依赖。第二，导航需要特殊处理——因为目标 Activity 在下载前根本不存在于设备上，标准的 `startActivity()` 会崩溃。Android Navigation Component 提供了 Dynamic Feature Module 的原生支持来处理这个问题。

### bundletool：在本地验证 AAB 的效果

上传到 Google Play 之前，可以用 `bundletool` 命令行工具在本地模拟生成 Split APK，验证不同设备配置下的实际下载大小：

```bash
# 从 AAB 生成 Split APK
bundletool build-apks --bundle=app-release.aab --output=app.apks

# 查看特定设备配置的 APK 大小
bundletool get-size total --apks=app.apks \
    --device-spec=device-spec.json
```

这个工具可以验证：切换到 AAB 之后，用户在 arm64 + xxxhdpi 设备上的实际下载大小是多少。

## 常见问题与误区

**「开启 minifyEnabled 就够了」**——这是最常见的误区。R8 的代码缩减只能删掉静态不可达的代码。如果项目里有大量通过反射调用的代码、插件化框架、或者 Gson/Jackson 反序列化的 Model 类，没有配置正确的 keep 规则，R8 要么删错（运行时 ClassNotFoundException），要么不敢删（keep 范围过大）。正确的做法是：开启 R8 后跑一遍完整的回归测试，结合 APK Analyzer 检查每个库的保留比例，逐步收窄 keep 规则。

**「应该支持所有屏幕密度」**——Android 的资源缩放机制可以在缺失某一密度资源时自动从最近的高密度资源缩放。对于大多数 App，提供 xxhdpi 资源即可覆盖主流设备，系统会自动处理其他密度的缩放。在 Gradle 中配置 `resConfigs` 过滤掉不需要的密度，可以减小资源体积。

**「WebP 不如 PNG 清晰」**——这是过时的观念。对于照片类图片，WebP 有损压缩在 80% 质量以上时，人眼几乎无法察觉与 PNG 的差异；对于图标类图片，WebP 无损模式的压缩率也优于 PNG。唯一需要注意的是 alpha 通道——某些带半透明效果的复杂图标，WebP 有损可能产生 artifact，这种情况用 WebP 无损即可。

**「App Bundle 是强制性的，国内市场没法用」**——国内应用市场确实不支持 AAB 格式。但 App Bundle 的技术价值不限于 Google Play。可以在本地用 `bundletool` 生成针对特定 ABI 和密度的 APK，然后分渠道上传。这比「一个 APK 适配所有设备」高效得多。此外，Dynamic Feature Module 的按需加载思想，也可以通过自研的插件化框架在非 Google Play 渠道实现。

## 与其他章节的关系

APK 体积优化不是孤立的主题。代码瘦身（R8）不仅减小 dex 体积，还能通过方法内联和类合并提升运行时性能——这与 §8.3 中讨论的启动优化直接相关。Native 库的大小和加载方式影响着冷启动时的 `dlopen` 耗时，可以在 Perfetto 的主线程 track 中观察到。资源优化则和 §4.1 内存管理有关——加载一张 oversized 的图片不仅浪费存储，还浪费运行时内存。

工具层面，APK Analyzer 的使用技能与 §14.1 中的 Android Studio Profiler 互补。持续集成中的体积门禁，则是 §15.6 自动化监控理念的具体实践。

## 扩展：Baseline Profile 对体积的影响

Baseline Profile（基线配置文件）是 Android 从 7.0 开始引入的 AOT 编译优化机制。它在 APK 中嵌入一个列表，告诉 ART 运行时「这些代码路径很重要，请在安装时就预编译它们」，从而避免运行时 JIT 编译的卡顿。

从体积角度，Baseline Profile 文件本身很小（通常几十 KB），对 APK 体积几乎无影响。但有一个间接影响值得注意：如果使用 Cloud Profile（从真实用户收集的编译配置），需要确保 Profile 中的类没有被 R8 混淆——否则 Profile 指向的类名在混淆后的 dex 中不存在，等于白配。AGP 在构建时会自动处理 Profile 和混淆的映射关系，但如果手动管理 Profile，需要注意这一点。

[待补充: Baseline Profile 生成和配置的详细流程]

## 扩展：大厂包体积优化实践参考

以下是公开可查的大厂优化实践数据，供参考：

- **微信**：通过 AndResGuard 资源混淆 + 动态插件化，将主包体积控制在 200MB 以内（含大量 native 库）
- **得物 App**：通过 Layout 二进制 XML 裁剪优化（裁剪 Namespace、属性名、修正偏移量），在资源层面实现了额外 10%-15% 的缩减[已验证: 来源见 Cubox/包体积：Layout 二进制文件裁剪优化｜得物技术-2023-09-18.md]
- **抖音**：通过 so 动态下发 + 按需加载，将核心 native 库从 APK 中分离，主包仅保留启动必需的 so

[待补充: 更多可验证的大厂数据点]

## 参考资料

- [Reduce your app size | Android Developers](https://developer.android.com/topic/performance/reduce-apk-size)
- [Shrink, obfuscate, and optimize your app | Android Developers](https://developer.android.com/build/shrink-code)
- [Android App Bundle | Android Developers](https://developer.android.com/build/app-bundle)
- [Play Feature Delivery | Android Developers](https://developer.android.com/guide/playcore/feature-delivery)
- [bundletool 命令行工具 | GitHub](https://github.com/google/bundletool)
- 得物技术：《包体积：Layout 二进制文件裁剪优化》
