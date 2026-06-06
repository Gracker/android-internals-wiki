---

title: "R8 与资源优化"
chapter: "25.7"
section: "25.7"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-14"
last_verified_against: "Android Developers docs 2026-03/2026-05, R8 full mode docs, AOSP ResourceTypes.h"
confidence: medium
drafted_date: "2026-05-14"
polish_count: 0
sources:
  - type: official
    path: "https://developer.android.com/build/shrink-code"
  - type: official
    path: "https://developer.android.com/topic/performance/app-optimization/full-mode"
  - type: official
    path: "https://developer.android.com/topic/performance/app-optimization/adopt-optimizations-incrementally"
  - type: official
    path: "https://developer.android.com/topic/performance/app-optimization/keep-rule-examples"
  - type: official
    path: "https://developer.android.com/topic/performance/app-optimization/customize-which-resources-to-keep"
  - type: official
    path: "https://developer.android.com/topic/performance/reduce-apk-size"
  - type: official
    path: "https://developer.android.com/develop/ui/views/graphics/reduce-image-sizes"
  - type: official
    path: "https://developer.android.com/develop/ui/views/text-and-emoji/downloadable-fonts"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/libs/androidfw/include/androidfw/ResourceTypes.h"
  - type: book-structure
    path: "Clippings/Android 性能优化 - 原理：重新认识 APK 安装包.md"
  - type: book-structure
    path: "Clippings/Android 性能优化 - 资源文件的体积优化实战.md"
  - type: book-structure
    path: "Clippings/Android 性能优化 - dex 文件的体积优化实战.md"
tags: [r8, proguard, webp, vector-drawable, font-subsetting]
related_chapters: ["25.6", "12.1", "25.8"]
pipeline_stage: ready-to-publish
task6_state: "reviewed"
task9_state: reviewed
last_task9_autofix_at: "2026-06-06"
task2b_state: fixed
reviewed_by: "openclaw-task6"
reviewed_date: "2026-06-06"
task6_result: "pass-light-edit"
task6_reviewed_at: "2026-05-14T20:10:00+08:00"
task6_reviewed_by: openclaw-task6
last_task6_at: "2026-06-06T10:12:00+08:00"
last_task6_review_log: "logs/review/2026-06-06-10-review.md"
task6_review_notes: "2026-06-06 Task6 revisit-review #5: L1/L2 无新增写作问题。Task 9 auto-fix 已验证（allowobfuscation 误用已修正，keep 规则语义正确）。task9_result=auto-fixed 仍不满足自动晋升条件 ②（需 pass-tech-review），回 Task 9 复确认。"

task2b_result: fixed
last_task2b_at: "2026-06-03T14:54:49+08:00"
task2b_fixed_by: "openclaw-task2b"
task2b_fixed_date: "2026-06-03"
task9_result: pass-tech-review
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-06"
last_task9_at: "2026-06-06T10:21:00+08:00"
last_task9_review_log: "logs/deep-review/2026-06-06-10-deep-review.md"
task9_review_notes: "2026-06-06 09:20 Task9 deep-review: auto-fixed。修正 JSON 字段 keep-rule 示例中的 allowobfuscation 误用；证据为 Android Developers R8 full-mode / keep rules 文档。回 Task6 复审。 | 2026-06-06 10:21 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0；Task6 已通过且 queue 无 pending，自动晋升 finalized。"
---

# R8 与资源优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 R8 全模式（Full Mode）与兼容模式
- 🔹 Keep 规则编写与优化
- 🔹 资源格式优化：WebP / VectorDrawable / AVIF
- 🔹 字体子集化与按需加载

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 R8 与资源优化

25.6 节已经把包体积分析、R8 开关、资源缩减和 ABI 策略放进同一套体积排查流程。这里聚焦两个更容易出线上事故的细节：R8 规则怎样既保留运行时入口又不放弃优化空间，资源怎样在格式、命名、字体和动态加载之间做取舍。包结构、APK Analyzer 和 `.so` 策略详见 12.1 与 25.6 节。

[结构参考: Clippings/Android 性能优化 - 原理：重新认识 APK 安装包.md]

## R8 全模式（Full Mode）与兼容模式

[已验证: 官方文档, developer.android.com/topic/performance/app-optimization/full-mode]

R8 全模式从 AGP 8.0 起成为默认模式。它比旧兼容模式更积极：会更大胆地做类合并、方法内联、泛型签名属性裁剪、注解属性裁剪和无用成员删除。体积收益来自这些优化，但风险也集中在同一批地方：反射、序列化、依赖注入、JNI、枚举名、`ServiceLoader`、框架通过注解或泛型读取类型信息的路径。

R8 全模式、资源缩减和库 keep rules 的版本边界要按工具链拆开：

| 能力 | 版本要求 | 说明 |
|------|----------|------|
| R8 full mode 默认 | AGP 8.0+ | 取代旧兼容模式，开启类合并、内联、无用成员删除 |
| optimized resource shrinking | AGP 8.12/8.13 | 需显式设置 `android.r8.optimizedResourceShrinking=true` |
| optimized resource shrinking 自动 | AGP 9.0+ | `isShrinkResources=true` 时自动启用 |
| Gson consumer rules | Gson 2.11.0+ | 库自带 full mode 所需 keep rules，旧版需 App 侧补 TypeToken/Signature 规则 |
| resource shrinking 依赖代码缩减 | 全版本 | 必须先开 `isMinifyEnabled=true`，否则 `isShrinkResources` 缺少代码引用图 |

迁移时不要把“全模式出问题”归因成 R8 不稳定。更常见的原因是工程里有运行时入口没有被静态引用图表达出来。R8 只能保证静态可达代码不被删；反射和外部框架契约要靠 keep 规则、`@Keep`、库的 consumer rules 或 generated keep rules 补齐。

这段配置用于临时退回兼容模式，只应作为定位手段，不应作为长期方案。

```properties
# gradle.properties
android.enableR8.fullMode=false
```

如果关闭全模式后崩溃消失，下一步不是保留这个开关，而是收窄到具体规则：找出被裁剪的类、成员或属性，再用最小 keep 规则保留它。长期停留在兼容模式会让后续 AGP 升级更难，也会让 R8 的体积和运行时优化空间变小。[已验证: 官方文档, developer.android.com/topic/performance/app-optimization/adopt-optimizations-incrementally]

Gson、Moshi、Jackson、Room、Hilt、Retrofit、JNI 注册和自研插件框架是全模式迁移的高风险区。以 Gson `TypeToken` 为例，官方 full mode 文档给出的失败原因是 `Signature` 属性被裁剪后，运行时拿不到泛型类型信息；对应规则要保留 `Signature`，同时允许类继续被混淆和优化。这个例子说明 keep 规则不是越宽越安全，规则写宽会把整片代码从优化器手里拿走。

## Keep 规则编写与优化

[已验证: 官方文档, developer.android.com/build/shrink-code；developer.android.com/topic/performance/app-optimization/keep-rule-examples]

R8 规则要围绕“谁在运行时访问它”来写。Activity、Service、Provider 这类 manifest 入口由构建工具识别；反射、JSON 字段、JNI 方法、注解处理器生成的注册表、跨进程协议类，才需要额外规则。工程里最伤体积的写法通常是 `-keep class com.company.** { *; }`，它让包名下的类、字段和方法一起逃过裁剪、混淆和内联。

排查 keep 规则按三步走：

- **先看增长来源**：用 APK Analyzer 或 `apkanalyzer` 找出 dex 增长来自哪个包。没有归因的规则调整只是在碰运气。
- **再看保留原因**：用 R8 输出的 `usage.txt`、`mapping.txt`、`seeds.txt` 和 `-whyareyoukeeping` 查被保留的类从哪条规则进入。
- **规则再改形状**：能保留成员就不要保留整类；能允许混淆就不要禁止混淆；能允许裁剪就不要禁止裁剪。

下面这组规则展示“保留运行时契约，但把优化权还给 R8”的写法。重点看 `allowshrinking`、`allowobfuscation`、`allowoptimization` 这几个修饰符。

**`allowshrinking` 的安全前提**：`allowshrinking` 允许 R8 删除“静态不可达”的成员或类。它只能在以下条件之一成立时使用：

1. 目标仍有**静态可达路径**——被其它 `-keep` 规则、`@Keep`、manifest 入口或 library consumer rules 保护。
2. 目标确实**允许被删除**——删除后不会产生运行时错误（例如已废弃的 debug 工具类）。

对反射入口（JSON 字段、JNI 方法、`ServiceLoader`、注解处理器注册表），`allowshrinking` 是危险的——R8 看不到反射路径，会把它们判定为“不可达”并删除。这类入口不应加 `allowshrinking`。

下面的规则按这个前提分化：JSON 字段不加 `allowshrinking`（反射入口）；JNI 方法不加 `allowshrinking`（native 入口）；Gson TypeToken 可以加 `allowshrinking`（有其它 keep 规则保护且静态可达）。

```proguard
# Gson TypeToken 场景：保留泛型签名，但允许类名继续缩短和优化。
-keepattributes Signature
-keep,allowobfuscation,allowshrinking,allowoptimization class com.google.gson.reflect.TypeToken
-keep,allowobfuscation,allowshrinking,allowoptimization class * extends com.google.gson.reflect.TypeToken

# JNI 场景：native 方法签名由 native 层查找，类本身仍可按调用关系裁剪。
# includedescriptorclasses 防止 native 方法参数/返回值类型的 descriptor class 被改名
# ——当 native 签名包含应用自定义类型或回调接口时，descriptor class 改名会破坏 JNI 查找。
-keepclasseswithmembernames,includedescriptorclasses,allowoptimization class * {
    native <methods>;
}

# 反射/序列化模型类：字段名参与 JSON/Gson/Jackson/Moshi 协议时不能混淆。
# ⚠️ 绝不能加 allowshrinking，也不要加 allowobfuscation；否则 release 包可能反序列化缺字段或字段名不匹配。
-keepclassmembers class com.example.api.** {
    <fields>;
}
```

第一组规则解决泛型签名读取问题；第二组规则用 `includedescriptorclasses` 保留 JNI 方法名和 descriptor class，避免 native 注册失败；第三组规则保留字段名，不把整个模型类固定；如果所有序列化字段都有稳定注解（如 `@SerializedName`），才可以再评估 `allowobfuscation`。上线前要用混淆后的 release 包跑序列化、登录、支付、推送、深链、插件加载和 JNI smoke test。debug 包不经过同一套 R8 路径，不能替代 release 验证。

consumer rules 也要纳入体积排查。AAR 里的 `consumer-proguard-rules.pro` 会传递到 App，三方 SDK 为了降低接入失败率，常把规则写得很保守。遇到 dex 增长异常时，先从 `build/outputs/mapping/release/configuration.txt` 查看最终合并后的规则，再决定是升级 SDK、覆盖规则，还是向 SDK 方反馈更细的 consumer rules。

[结构参考: Clippings/Android 性能优化 - dex 文件的体积优化实战.md]

## 资源格式优化：WebP / VectorDrawable / AVIF

[已验证: 官方文档, developer.android.com/topic/performance/reduce-apk-size；developer.android.com/develop/ui/views/graphics/reduce-image-sizes]

资源优化要先区分“引用关系”和“文件格式”。`isShrinkResources = true` 处理的是不可达资源，WebP、VectorDrawable、AVIF 处理的是已使用资源的单文件大小。两者互补，不能互相替代。资源缩减还依赖 R8 的代码缩减结果；只打开资源缩减，构建工具没有足够的代码引用图可用。[已验证: 官方文档, developer.android.com/build/shrink-code]

这段 Gradle 配置是 release 包的基线。读者重点看两个开关必须同时启用。

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

构建后要检查资源缩减报告，确认被移除的是废弃布局、图片、字符串和 style，而不是动态加载路径里的资源。动态资源名要通过 `res/raw/*.keep.xml` 保留，特别是换肤、服务端下发页面、WebView bridge、通知图标和桌面 widget。

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources xmlns:tools="http://schemas.android.com/tools"
    tools:keep="@drawable/skin_*,@layout/dynamic_*"
    tools:discard="@drawable/debug_*" />
```

`tools:keep` 和 `tools:discard` 是给资源缩减器的显式规则。它们有全局作用域，库模块里的 keep 文件要带上包名或模块名前缀，避免规则互相覆盖。[已验证: 官方文档, developer.android.com/topic/performance/app-optimization/customize-which-resources-to-keep]

格式选择可以按下表处理：

| 资源类型 | 推荐格式 | 适用场景 | 风险边界 |
| --- | --- | --- | --- |
| 简单图标、线性图形 | VectorDrawable | 单色或少量路径、需要多密度适配的图标 | 复杂路径会增加解析和绘制成本，照片类资源不适合 |
| 普通位图、透明图片 | WebP | PNG / JPG / 静态 GIF 的替代，适合大部分插画和运营图 | 转换后必须做视觉回归，渐变、阴影、文字边缘容易出现压缩痕迹 |
| 高压缩比位图 | AVIF | Android 12（API 31）及以上设备，适合对下载体积敏感的图片 | 低版本不能直接使用；多渠道包要按 minSdk 或资源变体拆分 |
| 需要拉伸边界的图片 | 9-patch PNG | 气泡、背景框、可拉伸控件背景 | 不要直接转 WebP / AVIF；拉伸区域和内容区域会丢语义 |

VectorDrawable 的收益来自去掉多套密度位图，而不是来自压缩算法。它适合图标和简单插画；如果把复杂 SVG 全量转成 VectorDrawable，XML 路径数据可能比原 WebP 更大，还会把解析成本挪到运行时。WebP 适合替换多数 PNG / JPG，但转换要按资源类型分批做：启动页、登录页、品牌图和支付图标先人工验收，再进入批处理。AVIF 在 Android 12 及以上有系统支持，适合新系统占比高、图片体积压力大的渠道；低版本要保留 WebP 或 PNG 兜底。[已更新至 Android 16]

resources.arsc 相关优化要谨慎。参考书把资源去重、资源名压缩和字符串池处理放在同一类问题里，这个结构是合理的：AOSP `ResourceTypes.h` 也能印证资源表由字符串池、package、type spec、type item 等二进制块组成，不是普通文本文件。工程上更稳的顺序是：先开官方资源缩减，再做图片格式转换，再评估资源名压缩或重复图片去重。直接改 `resources.arsc` 的工具必须覆盖换肤、多语言、动态资源名和热修资源路径。[已验证: AOSP android-16.0.0_r1, frameworks/base/libs/androidfw/include/androidfw/ResourceTypes.h]

[结构参考: Clippings/Android 性能优化 - 资源文件的体积优化实战.md]

## 字体子集化与按需加载

[已验证: 官方文档, developer.android.com/develop/ui/views/text-and-emoji/downloadable-fonts]

字体文件经常被低估。一个完整 CJK 字体可能比多张运营图还大；如果 App 只在少数页面使用品牌字体，直接把全量 `.ttf` 放进 `assets/` 或 `res/font/`，会让所有用户为少数场景付下载成本。字体治理先做两件事：确认每个字体文件的使用页面和字重，再确认它是否需要随安装包交付。

字体子集化适合范围稳定的文本，例如品牌数字、英文标题、固定营销文案和图标字体。处理时要按字符集、字重、斜体、语言拆分，保留 fallback 字体，避免缺字变成方框。子集文件生成后要记录输入字符集和工具版本，否则下一次文案变更很难复现同一份产物。[待验证: 字体子集化工具链需结合项目 CI 确认]

按需加载适合范围不稳定或使用频率低的字体。Android 官方 Downloadable Fonts 支持通过 provider 请求字体，AndroidX Core 可覆盖 API 14 及以上设备；它的收益是减少 APK 内置字体文件，让多个 App 复用 provider 缓存。限制也很明确：首次展示依赖 provider 可用性和网络 / 缓存状态，页面要准备系统字体 fallback，不能把首屏文本强依赖在远程字体返回上。

这段 XML 展示 Downloadable Fonts 的资源声明方式。重点是字体文件不再打进 APK，而是由字体 provider 按需返回。

```xml
<font-family xmlns:android="http://schemas.android.com/apk/res/android"
    android:fontProviderAuthority="com.google.android.gms.fonts"
    android:fontProviderPackage="com.google.android.gms"
    android:fontProviderQuery="Noto Sans"
    android:fontProviderCerts="@array/com_google_android_gms_fonts_certs" />
```

接入后要补两类验证：冷启动首屏是否因为字体等待而抖动，弱网或 provider 不可用时 fallback 是否稳定。对于国内分发渠道，Google Play services 不一定可用，Downloadable Fonts 不能作为唯一方案；更稳的做法是“基础字体随包、低频字体按需下载、品牌字体按页面缓存”。

## 扩展：资源优化与 AAB 分发的分工

[已验证: 官方文档, developer.android.com/guide/app-bundle；developer.android.com/guide/playcore/feature-delivery]

AAB 和 Play Feature Delivery 解决的是“按设备、语言、密度、ABI 或功能模块分发”的问题；R8 和资源优化解决的是“产物本身是否还有无用代码和资源”的问题。二者不能互相替代。一个没有开 R8 的 AAB 仍会把无用代码带进 base module；一个只做 WebP 转换的 APK 也不会自动减少未使用语言包或 ABI 副本。

对 Google Play 渠道，优先让 AAB 拆出语言、密度、ABI 和 dynamic feature；对国内渠道，很多市场仍以 APK 为主，仍要显式处理 `resourceConfigurations`、ABI 过滤、字体和大资源按需下载。AAB 与按需分发的细节放到 25.8 节。资源优化先让每个产物变小，分发策略再决定哪些用户需要拿到哪些产物。