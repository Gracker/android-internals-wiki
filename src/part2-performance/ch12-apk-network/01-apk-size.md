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
last_verified: '2026-04-24'
last_verified_against: AGP 8.8 DSL deprecation docs + AGP 8.12.0 release notes + Android
  App Bundle docs
confidence: medium
sources:
- type: official
  path: https://developer.android.com/topic/performance/reduce-apk-size
- type: official
  path: https://developer.android.com/build/shrink-code
- type: official
  path: https://developer.android.com/build/app-bundle
- type: official
  path: https://developer.android.com/reference/tools/gradle-api/8.8/com/android/build/api/dsl/ApplicationBaseFlavor#resourceConfigurations
- type: official
  path: https://developer.android.com/reference/tools/gradle-api/8.8/com/android/build/api/dsl/ApplicationAndroidResources#localeFilters
- type: official
  path: https://developer.android.com/guide/playcore/feature-delivery
- type: blog
  path: 得物技术《包体积：Layout 二进制文件裁剪优化》2023-09
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
task9_review_notes: "2026-05-06 05 task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 2。Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-05-24 Task9 闲时抽检：needs-rework。P0 0 / P1 1 / P2 0；Dynamic Feature Module 仍使用旧 Play Core Library 1.6+ 口径，需更新为 Play Feature Delivery Library 2.1.0+ 并标注 Android 14+ target SDK 版本边界。 | 2026-05-28 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-06-18 Task9 闲时抽检：pass-tech-review。P0 0 / P1 0 / P2 1；官方文档核对未发现 Android 18/API 38 越界；zipalign 16KB 验证命令建议后续从对齐命令改为 -c 校验命令。"
last_task6_at: '2026-05-06T05:05:00+08:00'
last_task6_audit: '2026-07-03'
review_notes: '2026-05-05 Task6 23:26：revisiting 写作复审，清理填充词/元叙述，并让 density FAQ 与正文口径一致；写作层通过。Task9
  已有 P1/P2 queue pending，等待 Task2B。 | 2026-05-06 Task6 05:05：revisiting 写作复审；清理 L1/L2
  结构性引导语与术语一致性问题，写作层通过。Task9 仍 pending，本轮不做技术裁决。 | 2026-05-06 05 task9 deep-review:
  pass-tech-review。P0 0 / P1 0 / P2 2。Task6 已通过且 queue 无 pending，自动晋升 finalized。'
last_task9_review_log: "logs/deep-review/2026-05-28-01-deep-review.md"
last_task9_audit: '2026-06-18'
last_task9_audit_log: logs/deep-review/2026-06-18-11-audit.md
rework_type: review回炉修复（Task9 闲时抽检问题单）
last_task2b_lite_at: '2026-05-27'
pipeline_stage: ready-to-publish
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-18
---

# APK 体积优化

## 为什么要关注 APK 体积

试想一个场景：用户在地铁上用 4G 搜到一个 App，Google Play 显示「下载大小 156 MB」——这个数字很可能直接让他划走了。Google 在 2018 年的一项内部研究中发现，APK 体积每增加 6 MB，安装转化率就下降约 1%。在国内应用市场，这个数字可能更敏感——很多用户还在按流量计费，或者手机存储已经捉襟见肘。

体积问题不仅仅是下载体验。APK 安装后，dex 文件需要被解压、验证、编译（AOT/JIT）；resources.arsc 会被加载到内存；native libraries 被解压到磁盘。体积越大，安装时间越长，运行时的内存占用也越高。对于 MTK、高通这类平台上做性能优化的工程师来说，包体积和启动速度、内存占用之间存在一条不太显眼但会影响结果的因果链。

本章不罗列优化技巧清单——那种清单任何博客上都能找到。本章只回答三件事：**一个 APK 里面到底装了什么，哪些东西占了多少空间，我们用什么工具能看清楚，以及从工程实践的角度，哪些优化手段投入产出比最高。**

## APK 里面到底装了什么


一个标准的 release APK 就是一个 ZIP 压缩包。解压之后，我们通常会看到以下几类文件：

**Dex 文件（classes.dex, classes2.dex, ...）** 是编译后的 Dalvik 字节码。所有 Kotlin/Java 代码——包括业务代码、AndroidX 库、第三方 SDK——最终都会编译进 dex 文件。一个中等规模的 App，dex 通常占总大小的 30%-50%。当方法数超过 65536（即一个 dex 文件的理论上限）时，Gradle 会自动进行多 dex 分包，产生 classes2.dex、classes3.dex 等文件。

**resources.arsc** 是资源索引表。把它看成一张总目录更接近实际实现。文件里至少有三层和体积直接相关的字符串池：全局字符串池、每个 `ResTable_package` 下的 Type String Pool（`string`、`layout`、`drawable` 这类资源类型名），以及 Key String Pool（`app_name`、`main_title` 这类 entry 名称）。系统根据资源 ID 定位 package、type、entry 后，再回到这些池和对应的类型块取元数据。AndResGuard 这类工具压缩 `resources.arsc` 时，主要就是缩短 Type String Pool 和 Key String Pool 里的字符串条目，资源表本身和内存映射开销也会跟着下降。

**res/ 目录**包含编译后的二进制资源文件——布局 XML 的二进制编译版、图片资源、颜色值等。Android 构建工具会把 XML 布局文件编译成二进制格式（AXML），这不是普通的文本 XML。得物技术团队曾经通过裁剪二进制 XML 中的冗余字段（如 Namespace 声明、重复的属性名）实现了单个 Layout 文件体积缩减约 40%。

**assets/ 目录**存放原始文件——字体、WebView 加载的 HTML、配置文件等。这些文件不会被编译，原样打包进 APK。如果 App 内置了字体文件或大型 JSON 配置，assets 可能成为体积大户。

**lib/ 目录**是 native libraries（.so 文件）的存放位置。这个目录按 ABI（Application Binary Interface）分子目录——`arm64-v8a/`、`armeabi-v7a/`、`x86/`、`x86_64/`。每一个 ABI 子目录下都是一份完整的 so 库副本。所以如果 Gradle 里没有配置 `ndk.abiFilters`，APK 里可能同时包含了 4 个架构的 native 库——arm64 设备只需要其中 1 份，另外 3 份全是浪费。

**META-INF/ 目录**包含签名信息。这个目录下的文件（CERT.SF、CERT.RSA、MANIFEST.MF）在 APK 安装时用于验证完整性，体积通常不大。

`AndroidManifest.xml` 是编译后的二进制清单文件，描述了 App 的组件、权限、SDK 版本等信息。

理解这个结构是优化体积的前提。不同类型的文件需要完全不同的优化策略：dex 靠代码缩减和混淆，res 靠资源压缩和格式替换，lib 靠 ABI 过滤和动态下发。APK 本身是 ZIP 容器，`classes.dex` 和 ELF `.so` 只是被放进容器里的内容，它们是否压缩取决于 packaging 策略，不取决于文件格式本身。

对 dex 来说，APK 里常见的是 ZIP entry 的压缩结果，安装后还会继续进入 dexopt、vdex / odex 这些流程。对 native 库来说，Android 6.0+ 已支持直接从 APK 加载未压缩且 page-aligned 的 `.so`。AGP 4.2+ 更常用 `jniLibs.useLegacyPackaging` 控制这条路径，旧的 `android:extractNativeLibs` 清单属性只是同一问题的旧入口。`useLegacyPackaging=false` 时，`.so` 会保持未压缩以支持 direct loading；`true` 时才会走压缩并提取到文件系统的路径。

## APK Analyzer：先测量，再优化


盲目优化是工程上的大忌。在动手之前，我们需要知道 APK 里到底什么最占空间。Android Studio 自带的 **APK Analyzer** 是做这件事的第一选择。

打开方式很简单：在 Android Studio 中选择 **Build → Analyze APK...**，然后选中 release APK 文件。APK Analyzer 会展示一个树状结构，列出每个文件和目录的大小，包括 **Raw Size**（未压缩原始大小）和 **Download Size**（估算的下载大小，考虑了 Google Play 的进一步压缩）。

在 APK Analyzer 的顶部，有几个关键信息值得注意：

**Total Size** 给出了整个 APK 的大小概览。如果这个数字和预期差距很大，说明构建配置可能有问题（比如 debug 构建没开混淆，或者意外包含了一个大型 SDK）。

**Dex 文件分析**：点击 classes.dex，APK Analyzer 会展示一个类列表，按包名组织。这里能看到每个包（也就是每个库或模块）贡献了多少方法和多少字节。这一步通常能立即暴露问题——比如某个只用了其中一个工具方法的工具库，却带着 20000 个方法和 5 MB 的 dex 代码。

**资源对比**：APK Analyzer 的另一个实用功能是**对比两个 APK**。把优化前后的两个 APK 拖进去，它会把差异高亮出来，确认优化是否生效、有没有意外引入新的资源。

在命令行环境下，可以使用 Google 提供的 `bundletool`（App Bundle 的配套工具）或 `aapt dump badging` 来获取 APK 结构信息，适合集成到 CI/CD 流水线中做体积门禁检查。

## 代码瘦身：让 R8 帮你砍掉不需要的代码


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

keep 规则常见的工程陷阱是：**规则写得越宽，R8 能优化的空间就越小**。一条 `-keep class com.example.** { *; }` 就可能让整个包名下的所有类逃过优化。Android 官方推荐的做法是尽量使用 `@Keep` 注解，精确标注需要保留的类和成员：

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

本章前面的 `isMinifyEnabled` / `isShrinkResources` 配置以 AGP 8.7 为基线。升级到 AGP 8.12.0+ 后，还可以打开**优化的资源缩减**（Optimized Resource Shrinking），把资源缩减逻辑并入 R8 的引用图分析。启用方式：

```properties
# gradle.properties
android.r8.optimizedResourceShrinking=true
```

[适用版本: AGP 8.12/8.13 手动 opt-in；AGP 9.0.0+ 在 `isShrinkResources=true` 时默认使用 Optimized Resource Shrinking，不再需要设置该属性]

AGP 8.12/8.13 需要手动开启这个开关。AGP 9.0.0 起只要 `isShrinkResources=true` 就自动使用优化版资源缩减。低版本仍然使用传统的资源缩减流程。

> **⚠️ 动态资源引用的安全边界**：开启 `android.r8.optimizedResourceShrinking` 后，R8 的引用图分析会接管资源缩减逻辑。如果项目中有通过 `Resources.getIdentifier()` 动态获取资源的写法（常见于插件化框架、主题引擎、WebView 混合应用），R8 无法在编译期追踪这类动态引用，可能导致资源被误缩减。启用前的检查清单：
> 1. 扫描代码中所有 `Resources.getIdentifier()` 调用点
> 2. 检查反射式资源名拼接（如 `getIdentifier("icon_" + suffix, "drawable", packageName)`）
> 3. 确认 `res/raw/keep.xml` 中用 `tools:keep` 声明了所有动态引用的资源匹配模式
> 4. 构建后检查 `build/outputs/mapping/*/resources.txt`，确认没有误删
> 5. 跑一轮资源路径回归测试，覆盖动态加载场景

## 资源瘦身：图片、布局和字符串的优化

### 图片格式替换：PNG → WebP

图片通常是 `res/` 目录下体积最大的贡献者。把 PNG 替换为 WebP 是投入产出比最高的优化之一：在同等视觉质量下，WebP 比 PNG 小 25%-35%；如果允许有损压缩（对于照片类图片完全可以），压缩率可达 60%-70%。

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

### 语言过滤和密度过滤要分开写

AGP 8.8 的 DSL 文档已经把 `resourceConfigurations` / `resConfigs` 标成 deprecated。语言资源如果还需要在构建期裁剪，新项目直接用 `androidResources.localeFilters`：

```kotlin
android {
    androidResources {
        localeFilters += listOf("zh", "en")
    }
}
```

这条配置解决的是“项目实际支持哪些 locale”。它对非 Play 分发、CI 产物和本地 universal 包更直接，因为三方库经常顺手带进几十种语言资源。构建期先把不用的 locale 删掉，`resources.arsc` 和 split 之前的基线包都会更干净。

密度资源要单独看。Google Play 上架 AAB 之后，density / ABI split 由 App Bundle 分发机制处理，用户下载的并不是把所有密度和 ABI 都塞进去的 universal APK。所以在 2026 这个基线下，`resConfigs("xhdpi", "xxhdpi")` 已经不该写成默认方案。

手动过滤 density 只适合几类受控场景：

- 仍然产出单 APK 的 sideload / 企业内部分发
- 设备范围固定的 OEM 预装包或行业设备
- 明确知道目标屏幕密度集合，且没有走 Google Play 动态分发

如果项目还在维护旧 DSL，`resConfigs` 更适合当作兼容存量工程的过渡配置，不再是通用推荐路径。尤其不要把“语言过滤”和“密度过滤”写成同一条默认建议：前者在非 Play 构建里仍有现实价值，后者在 AAB 发布流程里通常已经由 split 覆盖。

```kotlin
android {
    defaultConfig {
        // 旧 DSL，只建议用于受控单 APK / 非 Play 分发场景
        resConfigs("zh", "en", "xxhdpi", "xxxhdpi")
    }
}
```

如果项目已经切到 App Bundle，体积优化的顺序更稳一些：语言裁剪看 `localeFilters`，ABI / density 交给 Play split，剩下再回到图片、资源表和 native 库本身。

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

ABI 过滤只解决“带了几份库”。`.so` 是否压缩是另一条轴：在支持 direct loading 的设备上，`useLegacyPackaging=false` 会让库保持未压缩并满足 page alignment，安装后不必再额外抽取一份；`true` 时才会更接近旧式 `extractNativeLibs=true` 的行为。分析下载体积和安装后磁盘占用时，这两条设置要分开看。

### 16KB Page Size 兼容不是体积优化项

Android 15+ 要求部分设备支持 16KB page size，这对 native library 产生了硬约束——不是“优化可选项”，而是“不满足就加载失败”。

关键要求：

- **AGP 8.5.1+**：使用未压缩 shared libraries（`useLegacyPackaging=false`），确保 `.so` 的 ZIP entry 按 16KB 边界排列
- **NDK r28+**：默认生成 16KB ELF alignment（`max-page-size=16384`）；NDK r27 及以下需在链接器 flags 中添加 `-Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384`
- **Prebuilt .so**：用 `readelf -l <lib>.so | grep LOAD` 检查所有 LOAD 段的 `Align` 是否 ≥ 2\*\*14（16384）
- **APK alignment 验证**：`zipalign -P 16 4 <input.apk> <output.apk>` 或 `bundletool` 验证 ZIP entry 是否按 16KB 边界排列

常见踩坑：为了追求更小的 APK 数值，手动压缩 `.so` 或用第三方工具重打包，会破坏 ELF LOAD 段的 `p_align` 和 ZIP entry 边界布局。16KB 设备上 `dlopen` 会因 alignment 不匹配而失败。


### Strip 符号表与符号管理

AGP 在 release 构建中默认 strip native libraries，移除调试符号表。不需要手动配置 CMake `LINK_FLAGS` 或 `ANDROID_STRIP_DEBUG_SYMBOLS`。AGP 8.x 的标准 DSL 口径分两层：

**符号上传（Play Console 线上符号化）**

在 `build.gradle.kts` 中控制保留多少符号信息用于 crash 崩溃栈还原：

```kotlin
android {
    buildTypes {
        release {
            // SYMBOL_TABLE: 仅保留函数级符号，体积最小
            // FULL: 保留完整调试符号，支持源码行号还原
            ndk.debugSymbolLevel = "SYMBOL_TABLE"
        }
    }
}
```

Play Console 的 Native Crash Reporting 需要 `SYMBOL_TABLE` 或 `FULL` 才能还原 so 崩溃栈。如果不上传符号，线上 crash 只能看到十六进制地址。

**选择性保留指定 so 的调试符号**

当只需要保留部分 so 的调试符号时：

```kotlin
android {
    packaging {
        jniLibs {
            keepDebugSymbols += listOf(
                "**/libcore-engine.so",
                "**/libFaceDetect.so"
            )
        }
    }
}
```

`keepDebugSymbols` 接受 glob 模式。只有匹配到的 so 会跳过 strip，其余 so 仍然走 release 默认 strip。

### 动态下发 so

对于某些大型 native 库（如人脸识别 SDK、地图引擎），最激进的优化方案是**不在 APK 中打包**，而是在用户首次使用相关功能时从服务器下载。这种方式需要自己管理下载、校验、加载的完整流程，实现复杂度较高，但收益明确：主包体积可以减少数十 MB，直接提升安装转化率。

一个折中方案是使用 Play Feature Delivery Library 的 **on-demand delivery**：将大型 so 库放在 Dynamic Feature Module 中（下一节讨论），用户安装基础 APK 时不包含这些库，只有当用户导航到需要该库的功能页面时才触发下载。

## App Bundle 与 Dynamic Feature Module


### App Bundle 解决了什么问题

传统 APK 分发模式的限制很直接：**一个 APK 必须适配所有设备**。结果是，同一个 APK 里同时装着 hdpi 和 xxxhdpi 的图片、arm64 和 x86 的 so 库、中文和斯瓦希里语的字符串。用户在 arm64 设备上下载了这个 APK，其中 70% 的资源对他毫无用处——但他不得不下载。

Android App Bundle（AAB）是 Google 在 2018 年推出的发布格式，它改变了这个模型。开发者上传一个 AAB 到 Google Play，Play 的服务器会根据每个用户的设备配置（屏幕密度、CPU 架构、语言）自动生成一个**最小化的 APK**（称为 Split APK）。结果是：用户只下载他设备实际需要的那部分资源。

从 APK 切换到 AAB，通常能把下载大小减小 **15%-40%**，不需要改一行业务代码。这也是 Google Play 自 2021 年 8 月起强制要求新 App 使用 AAB 发布的原因。

### Dynamic Feature Module：按需加载功能

App Bundle 的进阶用法是 **Dynamic Feature Module**（动态功能模块）。它的理念是把 App 拆分为一个 base module 和多个 feature module：

- **Install-time delivery**：模块随 base 一起安装，但可以在用户使用后卸载（适合新手引导模块）
- **On-demand delivery**：模块仅在用户访问对应功能时才下载（适合支付模块、滤镜编辑器等非核心功能）
- **Conditional delivery**：模块根据设备条件自动决定是否安装（如只在有 VR 功能的设备上安装 VR 模块）

配置一个 on-demand 的 Dynamic Feature Module，至少要同时改 base app module 和 feature module。

base app module（通常是 `:app`）负责声明它有哪些动态模块：

```kotlin
plugins {
    id("com.android.application")
    kotlin("android")
}

android {
    namespace = "com.example.app"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.example.app"
        minSdk = 21
    }
    dynamicFeatures += setOf(":feature:payment")
}
```

feature module 自己要应用 `com.android.dynamic-feature` plugin，并依赖 base module：

```kotlin
plugins {
    id("com.android.dynamic-feature")
    kotlin("android")
}

android {
    namespace = "com.example.app.feature.payment"
    compileSdk = 36
    defaultConfig {
        minSdk = 21
    }
}

dependencies {
    implementation(project(":app"))
}
```

`settings.gradle(.kts)` 里也要包含这两个模块。然后再在 feature module 的 `AndroidManifest.xml` 中声明分发策略：

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

在运行时使用 Play Feature Delivery Library 请求加载：

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

[适用版本: Play Feature Delivery Library 2.1.0+ / Android 5.0 (API 21)+；target Android 14 (API 34)+ 的工程必须使用 2.1.0 或更高版本，旧 monolithic Play Core Library 不再适合作为现代基线]

使用 Dynamic Feature Module 时，有几个工程上的注意点。第一，模块之间的代码依赖需要仔细规划——feature module 可以依赖 base module，但两个 feature module 之间不能直接依赖。第二，导航需要特殊处理——因为目标 Activity 在下载前还不存在于设备上，标准的 `startActivity()` 会崩溃。Android Navigation Component 提供了 Dynamic Feature Module 的原生支持来处理这个问题。

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

**「应该支持所有屏幕密度」**——Android 的资源缩放机制可以在缺失某一密度资源时自动从最近的高密度资源缩放。AAB / Google Play 分发时，density split 应交给 App Bundle；只有 sideload、企业包、OEM 固定设备等受控单 APK 场景，才考虑用 `resConfigs` 过滤密度资源。

**「WebP 不如 PNG 清晰」**——这是过时的观念。对于照片类图片，WebP 有损压缩在 80% 质量以上时，人眼几乎无法察觉与 PNG 的差异；对于图标类图片，WebP 无损模式的压缩率也优于 PNG。alpha 通道需要单独看——某些带半透明效果的复杂图标，WebP 有损可能产生 artifact，这种情况用 WebP 无损即可。

**「App Bundle 是强制性的，国内市场没法用」**——国内应用市场不支持 AAB 格式。但 App Bundle 的技术价值不限于 Google Play。可以在本地用 `bundletool` 生成针对特定 ABI 和密度的 APK，然后分渠道上传。这比「一个 APK 适配所有设备」高效得多。此外，Dynamic Feature Module 的按需加载思想，也可以通过自研的插件化框架在非 Google Play 渠道实现。

## 构建期体积治理：从测量到持续跟踪

知道 APK 大了，但不知道是哪个依赖膨胀了——这是工程实践中最常见的排查难点。目前经过官方验证的工具链按场景分三层：

**APK Analyzer**（手动排查）：上一节已介绍。适合定位体积大户、检查单个库的保留比例。

**bundletool + CI 门禁**（自动化基线）：在 CI 流水线中用 `bundletool get-size total` 对比每次构建的下载大小，超出阈值自动告警。这是体积治理从"发布前突击检查"变成"每次构建持续跟踪"的基础设施层。

**APK Analyzer / Ruler / Play Console App Size**（依赖审计）：如果需要分析传递依赖对 dex / res / native 体积的贡献，可以使用 Slack 开源的 [Ruler](https://github.com/slackhq/ruler) 或 Play Console 的 App Size 报告。Ruler 在编译期按模块和包名归集体积数据，适合大型多模块项目。

> **关于 AGP 8.12 体积分析**：截至 2026-05，AGP 8.12.0 的 release notes 中与体积依赖分析直接相关的入口仍是 `bundletool` 和 APK Analyzer。Build Analyzer 主要面向构建耗时。如果后续 Android Studio Feature Drop 提供了更细粒度的体积分析面板，以官方文档为准。

## 与其他章节的关系

APK 体积优化不是孤立的主题。代码瘦身（R8）不仅减小 dex 体积，还能通过方法内联和类合并提升运行时性能——这与 §8.3 中讨论的启动优化直接相关。Native 库的大小和加载方式影响着冷启动时的 `dlopen` 耗时，可以在 Perfetto 的主线程 track 中观察到。资源优化则和 §4.1 内存管理有关——加载一张 oversized 的图片不仅浪费存储，还浪费运行时内存。

工具层面，APK Analyzer 的使用技能与 §14.1 中的 Android Studio Profiler 互补。持续集成中的体积门禁，则是 §15.6 自动化监控理念的具体实践。

## 扩展：Baseline Profile 对体积的影响

Baseline Profile（基线配置文件）是 Android 从 7.0 开始引入的 AOT 编译优化机制。它在 APK 中嵌入一个列表，告诉 ART 运行时「这些代码路径很重要，请在安装时就预编译它们」，从而避免运行时 JIT 编译的卡顿。

从下载体积看，Baseline Profile 文件本身很小，通常只有几十 KB，对 APK 或 AAB 的下载大小影响很弱。安装后的磁盘占用要单独看。Profile 会让 ART 在安装或后台编译阶段生成更多 AOT 产物，这些机器码会落到 `.odex` / `.vdex`。常见业务包里，这部分新增磁盘占用往往会比对应的 DEX 字节码再大 10%-30%。Profile 范围写得过宽，冷启动也许会更快，但 `/data` 分区占用、安装后的编译时间和更新成本都会上升。如果使用 Cloud Profile，还要确保 Profile 中的类和方法在混淆后仍能正确映射。AGP 会在构建时处理这层映射；手动管理 Profile 时，需要额外检查。



## 扩展：大厂包体积优化实践参考

以下是公开可查的大厂优化实践数据，供参考：

- **微信**：通过 AndResGuard 资源混淆 + 动态插件化，将主包体积控制在 200MB 以内（含大量 native 库）
- **得物 App**：通过 Layout 二进制 XML 裁剪优化（裁剪 Namespace、属性名、修正偏移量），在资源层面实现了额外 10%-15% 的缩减
- **抖音**：通过 so 动态下发 + 按需加载，将核心 native 库从 APK 中分离，主包仅保留启动必需的 so



## 参考资料

- [Reduce your app size | Android Developers](https://developer.android.com/topic/performance/reduce-apk-size)
- [Shrink, obfuscate, and optimize your app | Android Developers](https://developer.android.com/build/shrink-code)
- [Android App Bundle | Android Developers](https://developer.android.com/build/app-bundle)
- [Play Feature Delivery | Android Developers](https://developer.android.com/guide/playcore/feature-delivery)
- [bundletool 命令行工具 | GitHub](https://github.com/google/bundletool)
- 得物技术：《包体积：Layout 二进制文件裁剪优化》
