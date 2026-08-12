---

title: "R8 与资源优化"
chapter: "25.7"
section: "25.7"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-05-14"
last_verified_against: "Android Developers docs 2026-03/2026-05, R8 full mode docs, AOSP ResourceTypes.h"
confidence: medium
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
related_chapters: ["25.6", "25.8"]
pipeline_stage: ready-to-publish
task6_state: "reviewed"
task9_state: reviewed
task2b_state: fixed
---

# R8 与资源优化

## 四类优化的职责

R8、资源缩减、图片编码和字体交付处理的是四类问题：

- **R8** 删除、改写和重命名代码；
- **资源缩减器** 删除不可达资源；
- **图片编码** 改变仍需交付的图片字节数与解码成本；
- **字体策略** 决定字符、字重和字体文件何时交付。

25.6 负责体积测量与归因，这里处理具体配置。Android 17（API 37）是平台行为锚点，R8/AGP 的行为仍由构建工具版本决定，不能仅凭设备系统版本推导。R8 和资源打包不涉及 kernel 实现，因此无需用 kernel 代码作为优化依据。

## R8 全模式（Full Mode）与兼容模式

R8 有三个相互独立的动作：

| 动作 | 含义 | 常见风险 |
| --- | --- | --- |
| shrinking | 删除不可达类、成员和属性 | 反射、JNI、序列化入口未表达 |
| optimization | 内联、类合并、访问级别调整等代码改写 | 依赖反射可见性或类结构 |
| obfuscation | 缩短类、字段和方法名 | 通过稳定名字查找代码或字段 |

AGP 8.0 起，full mode 默认开启。与 compatibility mode 相比，它不再为未精确描述的运行时行为保留额外余量，几个差异尤其需要检查：

- `Signature`、运行时注解、`InnerClasses`、`EnclosingMethod` 等 class-file 属性，只有在属性及其关联端点都满足保留条件时才会留下；
- 类被保留不代表其无参构造函数自动保留，反射调用构造函数要写到成员粒度；
- R8 可以修改成员可见性以获得更多内联机会，依赖 `private`/`public` 状态的反射代码要有契约；
- 只在字符串、资源、JNI 或外部注册表里出现的符号，不会自动成为静态可达入口。

相关工具版本边界如下：

| 工具版本 | 行为 |
| --- | --- |
| AGP 8.0+ | R8 full mode 默认启用 |
| AGP 8.12/8.13 | 优化版资源缩减需设置 `android.r8.optimizedResourceShrinking=true` |
| AGP 9.0+ | legacy DSL 中启用 `isShrinkResources` 后自动使用优化版资源缩减 |
| AGP 9.3+ | 推荐 `optimization { enable = true }`，同时启用代码与资源优化 |

各版本 DSL 和资源缩减开关以 [Enable app optimization](https://developer.android.com/topic/performance/app-optimization/enable-app-optimization) 为准。

下面的开关只用于确认故障是否与 full mode 语义有关。它不应留在长期发布配置中。

```properties
# gradle.properties
android.enableR8.fullMode=false
```

如果关闭 full mode 后问题消失，应回到 release 构建，找出缺失的类、成员或属性，并补最小规则。官方文档也要求删除该兼容开关以使用完整优化能力；详见 [R8 full mode](https://developer.android.com/topic/performance/app-optimization/full-mode)。

## Keep 规则编写与优化

Keep rule 的目标是把静态分析看不到的运行时契约告诉 R8。规则来源通常有四类：

- AGP/AAPT2 根据 manifest 等信息生成的平台规则；
- 应用自己的规则；
- AAR 中随库发布的 consumer rules；
- 注解处理器、代码生成器或编译插件生成的规则。

Activity、Service、Provider 等 manifest 组件已有构建工具生成的入口规则，不应因为担心误删就保留整个业务包。应用更需要审计反射构造、序列化字段、JNI 回调、`Class.forName()`、运行时注解扫描和旧式插件注册表。

### 先理解规则语义

| 写法 | 语义 |
| --- | --- |
| `-keep` | 默认禁止删除、优化和重命名匹配项 |
| `allowshrinking` | 允许匹配项在不可达时被删除 |
| `allowoptimization` | 允许对匹配项做代码优化 |
| `allowobfuscation` | 允许重命名匹配项 |
| `-keepclassmembers` | 仅在类本身存活时保留匹配成员，不负责让类存活 |
| `-keepclasseswithmembers` | 类含有指定成员时，保留类和匹配成员 |
| `includedescriptorclasses` | 同时约束字段或方法描述符中出现的类型 |

`-keep class com.example.** { *; }` 会同时限制三类优化。规则写窄不能靠机械添加 `allow*`：只有运行时契约允许删除、改名或改写时，相应修饰符才安全。例如，完整类名来自外部配置或 R8 无法识别的字符串时，`Class.forName()` 的目标不能允许改名；JNI 按方法名和描述符查找时也不能允许这些符号变化。

### 用库版本对应的规则

下面的规则用于 Gson 2.11.0 以前的 `TypeToken` full-mode 兼容。Gson 2.11.0 起已随库提供必要规则；新版项目不应无条件复制这段配置。

```proguard
-keepattributes Signature
-keep,allowobfuscation,allowshrinking,allowoptimization class com.google.gson.reflect.TypeToken { *; }
-keep,allowobfuscation,allowshrinking,allowoptimization class * extends com.google.gson.reflect.TypeToken
```

`TypeToken` 通过匿名子类的 `Signature` 属性恢复泛型实参。这里允许删除、优化和改名，是因为静态使用仍决定实例是否存活，运行时不依赖匿名类的原始名字；该规则不等于对所有反射模型都能使用 `allowshrinking`。模型字段仍应使用稳定序列化注解或库文档要求的规则。

下面是 `proguard-android-optimize.txt` 已包含的 JNI downcall 规则，用于防止 `native` 方法名及描述符相关类型被错误处理。项目若使用 native 到 Java/Kotlin 的 upcall，还要对被回调的类、构造函数和方法另写精确规则。

```proguard
-keepclasseswithmembernames,includedescriptorclasses class * {
    native <methods>;
}
```

这条规则只匹配声明为 `native` 的 Java/Kotlin 方法。它看不到 C/C++ 通过 `GetMethodID()`、`RegisterNatives()` 或反射调用的普通 Java/Kotlin 方法；这些入口需要按 native 代码中使用的类名、方法名和 JNI descriptor 逐项核对。官方示例见 [Keep rule use cases](https://developer.android.com/topic/performance/app-optimization/keep-rule-examples)。

### 从 release 产物反查

规则审计应使用与发布相同的 release 变体：

- `configuration.txt`：查看应用规则、默认规则和 consumer rules 合并后的结果；
- `seeds.txt`：查看入口与保留项；
- `usage.txt`：查看被删除的代码；
- `mapping.txt`：还原线上混淆堆栈；
- `-whyareyoukeeping`：针对某个意外存活的类查询保留路径；
- R8 Configuration Analyzer：工具链提供时，用于找宽泛规则和它限制的优化。

文件集合和目录会随 AGP/R8 版本调整，CI 应从实际构建产物中发现并归档。测试至少覆盖反射构造、泛型序列化、深链、通知、推送、JNI、WebView 接口和动态功能。Debug 包没有经历同一套优化，不能替代 release 验证。

库维护者应把库内部运行时契约写进 consumer rules；应用不应长期替三方库维护整包 keep。依赖升级时同时比较 `configuration.txt` 与 DEX 增量，规则变化和代码变化要分开判断。

## 资源缩减：从代码引用图到资源表

AGP 9.3 及以上推荐用下面的配置启用代码与资源优化。

```kotlin
android {
    buildTypes {
        release {
            optimization {
                enable = true
            }
        }
    }
}
```

新 DSL 会应用 Android 平台默认 keep rules，自定义规则放在 `src/<variant>/keepRules/*.keep`。AGP 9.3 以下使用 `isMinifyEnabled=true` 与 `isShrinkResources=true`；两者要同时开启，因为资源缩减依赖代码可达性。

动态资源名无法被静态引用图完整表示时，下面的文件演示如何保留换肤图片和动态页面布局，并丢弃已确认仅供内部调试的图片。文件可命名为 `res/raw/com.example.app.keep.xml`。

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources xmlns:tools="http://schemas.android.com/tools"
    tools:keep="@drawable/skin_*,@layout/dynamic_*"
    tools:discard="@drawable/internal_debug_*" />
```

Keep 文件作用于合并后的全局资源，应用与 AAR 应使用包含包名的唯一文件名。`tools:discard` 会覆盖缩减器的保守判断，只有构建变体与运行路径都能证明资源无用时才可添加。规则格式见 [Customize which resources to keep](https://developer.android.com/topic/performance/app-optimization/customize-which-resources-to-keep)。

`resourceConfigurations` 用于排除应用明确不支持的替代资源；AAB 则可以按语言、密度和 ABI 生成 configuration APK。支持系统“应用语言”或语言按需下载时，不能删掉受支持语言来换取上传制品变小。资源缩减、替代资源过滤与 AAB 分发是三种不同机制。

Android 17 的 [`ResourceTypes.h`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/androidfw/include/androidfw/ResourceTypes.h) 定义了字符串池、资源表头、package、type spec 和 type 等二进制结构。这能解释 `resources.arsc` 的组织方式，却不能证明第三方资源表重写工具与 AGP、动态资源名、热修或资源覆盖兼容。发布流程应先使用官方缩减，再评估额外工具。

## AOSP Soong 与应用 AGP 不能混用配置

`android-17.0.0_r1` 的平台源码使用 Soong 构建系统。下面两段是源码中的关键调用形态，用于说明 AAPT2 规则输出和 R8 诊断产物如何接入平台构建。

```text
aapt2 link ... --proguard <proguard-options> --output-text-symbols <R.txt>

r8 ... --no-data-resources \
  -printmapping <mapping> \
  -printconfiguration <configuration> \
  -printusage <usage>
```

第一条来自 Soong 的 [`java/aapt2.go`](https://android.googlesource.com/platform/build/soong/+/android-17.0.0_r1/java/aapt2.go)，AAPT2 生成规则文件；第二条来自 [`java/dex.go`](https://android.googlesource.com/platform/build/soong/+/android-17.0.0_r1/java/dex.go)，R8 输出映射、最终配置和删除报告。启用优化版资源缩减时，Soong 还会向 R8 传 `--resource-input`、`--resource-output` 和 `--optimized-resource-shrinking`；[`java/app.go`](https://android.googlesource.com/platform/build/soong/+/android-17.0.0_r1/java/app.go) 会使用非 final resource ID，并避免追加旧的 AAPT2 生成规则，让 R8 联合追踪代码与资源。

这些源码只约束 AOSP 平台模块。`Optimize.*` 属性、`RELEASE_*` 变量和 `R8_DUMP_*` 环境变量不是普通 Android 应用的 Gradle DSL。同一份 `dex.go` 中仍可看到由 API 36 与 Baklava 条件控制的 DEX v41 分支；它属于 Android 16 的版本演进，不能写成 Android 17 新特性，也不能当作应用瘦身开关。

## 资源格式优化：WebP / VectorDrawable / AVIF

资源缩减处理“是否还需要”，图片编码处理“留下的文件怎样表达”。格式选择要同时比较 APK 中的压缩后大小、解码时间、内存、画质和调用场景。

| 格式 | 适用场景 | Android 10–17 边界 |
| --- | --- | --- |
| VectorDrawable | 简单图标、少量路径、需要多密度适配的图形 | 平台早已支持；复杂路径可能增加解析与绘制成本 |
| WebP | 照片、插画、透明位图，支持有损与无损 | 本书适用版本均支持，仍需逐图做画质回归 |
| AVIF | 对传输体积敏感、允许按版本提供资源的位图 | Android 12（API 31）起平台支持；低版本需 WebP/PNG 资源变体 |
| PNG / 9-patch | 像素精确、无损、小型图标或带拉伸语义的背景 | 9-patch 的拉伸区与内容区不能用普通格式转换替代 |

VectorDrawable 通过一份路径数据覆盖多密度设备，但复杂 SVG 转换后可能比位图更大，也可能增加首帧解析和栅格化成本。WebP/AVIF 的编码质量参数对不同图片影响不同，不能全目录使用同一阈值。启动图、品牌素材、文字边缘、渐变、暗部和透明边缘要在目标设备上人工检查。

AVIF 可放在 `drawable-v31`，低版本目录保留 WebP 或 PNG；资源选择由系统版本限定符完成。若图片来自网络，服务端也要根据客户端解码能力和显示尺寸返回合适格式与分辨率，避免下载大图后再缩小。格式与画质建议见 [Reducing image download sizes](https://developer.android.com/develop/ui/views/graphics/reduce-image-sizes)。

图片转换应从原始素材生成，记录编码器版本与参数，并在 CI 比较最终 release 制品。对已经有损压缩的图片反复转码会累积失真；源文件、生成脚本和验收图应一起保存。

## 字体子集化与按需加载

字体治理从字符覆盖、字重、使用页面和许可证开始。一个字体家族可能包含多个静态字重、斜体和大字符集；删除其中任何部分前，要确认动态文案、多语言、无障碍字号和服务端下发内容仍有字形可用。

### 字体子集

子集化适合字符范围可枚举的内容，例如品牌数字、固定英文标题或稳定图标集合。构建流程应保存：

- 原始字体的版本、许可证和校验值；
- 输入字符集及其来源；
- 子集工具与参数；
- 生成字体的 glyph 覆盖检查；
- 缺字时的系统字体回退结果。

不要从当前仓库字符串机械生成全局子集：服务端文案、用户输入、人名、货币符号和辅助功能文本可能不在静态资源中。多字重场景还可评估 variable font，但应比较“一个可变字体”与“项目实际使用的几份静态字体”，不能预设哪种更小。

### Downloadable Fonts

Downloadable Fonts 由字体 provider 返回并缓存字体，AndroidX Core 可覆盖 API 14 及以上设备。下面的 XML 展示 Google Fonts provider 的声明结构；实际 query 与证书数组应由 Android Studio 或 provider 文档生成。

```xml
<font-family xmlns:android="http://schemas.android.com/apk/res/android"
    android:fontProviderAuthority="com.google.android.gms.fonts"
    android:fontProviderPackage="com.google.android.gms"
    android:fontProviderQuery="Noto Sans"
    android:fontProviderCerts="@array/com_google_android_gms_fonts_certs" />
```

Provider 的包名与证书用于验证来源。Google Fonts provider 依赖 Google Play services，不能假设所有渠道和设备都具备；首屏也不能阻塞等待字体。应用应准备系统字体回退，覆盖 provider 不可用、离线、缓存未命中、请求失败和证书更新。接口与证书要求见 [Use Downloadable Fonts](https://developer.android.com/develop/ui/views/text-and-emoji/downloadable-fonts)。

需要自建下载时，字体文件会进入系统字体解析器，应按不可信二进制输入处理，并补 HTTPS、内容校验、版本绑定、存储上限、原子替换和许可证检查。基础正文使用系统字体、低频品牌字体按需加载，通常比所有字体随包或所有字体远程化更容易维护。

## 资源优化与 AAB 分发的分工

R8 与资源缩减减少每个模块中的无用内容；AAB 决定某台设备获得哪些 base、configuration 和 Dynamic Feature APK。两者不能互相替代：

- 未开启 R8 的 AAB 仍会在模块中携带可删除代码；
- 转成 WebP 不会删除未使用语言或 ABI 副本；
- on-demand Dynamic Feature 改变首次交付量，不会自动删除该模块内部的无用代码与资源；
- 单 APK 渠道没有 Play 服务端 split，需要单独评估替代资源、ABI 和低频大文件。

AAB 和动态交付的测试见 25.8。专项资源优化完成后，仍要回到 25.6 的设备规格与 release 基线，确认收益出现在目标用户的交付集合中。

## 发布检查清单

- R8/AGP 版本、DSL 形式和 full-mode 状态已记录；
- `configuration.txt` 中没有无依据的整包 keep；
- 反射、泛型、JNI、序列化和动态功能使用 release 包通过；
- `mapping.txt`、删除报告、资源报告和规则配置已归档；
- 动态资源有最小 `tools:keep`，`tools:discard` 有变体测试；
- WebP/AVIF/VectorDrawable 经过包内大小、画质、解码和内存检查；
- 字体字符集、字重、许可证、provider 失败与系统字体回退已覆盖；
- AAB 与单 APK 渠道分别测量，使用同一业务基线比较。

## 小结

R8 full mode 要求工程把运行时契约写清：类是否必须存活、名字是否稳定、成员能否改写、哪些属性要保留。资源缩减建立在代码可达性之上，图片和字体优化则处理仍需交付的数据。Android 17 平台源码可以验证资源表与 Soong 构建分支，但应用配置仍以当前 AGP/R8 官方文档为准，不能把 Soong 环境变量搬进 Gradle 工程。
