---




title: "APK 体积分析与瘦身"
chapter: "25.6"
section: "25.6"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-11"
last_verified_against: "Android Developers APK/App Bundle/R8/16 KB docs 2026-07 + AOSP android-17.0.0_r1 + AGP 9.3.0"
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
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageAbiHelperImpl.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/com/android/internal/content/NativeLibraryHelper.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/androidfw/include/androidfw/ResourceTypes.h"
  - type: book-structure
    path: "Clippings/Android 性能优化 - 原理：重新认识 APK 安装包.md"
  - type: book-structure
    path: "Clippings/Android 性能优化 - dex 文件的体积优化实战.md"
  - type: book-structure
    path: "Clippings/Android 性能优化 - 资源文件的体积优化实战.md"
  - type: book-structure
    path: "Clippings/Android 性能优化 - so 文件的体积优化实战.md"
tags: [apk-size, apk-analyzer, r8, resource-shrink, abi-filter]
related_chapters: ["25.7", "25.8", "25.17", "25.18", "25.19"]
last_consolidated_at: "2026-08-11"
consolidated_from:
  - "src/part2-performance/ch12-apk-network/01-apk-size.md"
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
reviewed_by: openclaw-task6
reviewed_date: "2026-07-12"
task6_result: "pass-light-edit"
last_task6_at: "2026-07-12T12:15:00+08:00"
last_task6_review_log: "logs/review/2026-06-06-10-review.md"
task6_review_notes: "2026-07-12 Task6 revisiting 复审：pass-light-edit。L1 修复 2 处（链路→流程、关键是删除）；L2 结构/节奏/读者视角通过；task9 idle audit auto-fixed（P2 版本锚点）等效通过；无新增 L3/L4 回炉项。自动晋升 finalized。"
task2b_result: fixed-lite
task9_result: auto-fixed
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-06"
last_task9_at: "2026-06-06T10:21:00+08:00"
last_task9_review_log: "logs/deep-review/2026-06-06-10-deep-review.md"
task9_review_notes: "2026-06-06 09:20 Task9 deep-review: auto-fixed。修正 apkanalyzer --human-readable 全局参数位置；证据为 Android Developers apkanalyzer 语法。回 Task6 复审。 | 2026-06-06 10:21 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0；Task6 已通过且 queue 无 pending，自动晋升 finalized。"
last_task2b_lite_at: 2026-06-03
last_task9_autofix_at: "2026-07-12"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-12
last_task9_audit: "2026-07-12"
last_task9_audit_log: "logs/deep-review/2026-07-12-09-audit.md"
last_task9_audit_at: "2026-07-12T09:26:38+08:00"
last_task9_audit_result: auto-fixed-idle-audit
last_task9_audit_notes: "idle audit: P2 source-anchor auto-fix; AOSP PackageAbiHelperImpl/NativeLibraryHelper/ResourceTypes references moved from android-16.0.0_r1 to android-17.0.0_r1 after path and symbol verification; no P0/P1."
finalized_date: "2026-07-12"
finalized_by: openclaw-task6-auto-promote
---


# APK 体积分析与瘦身

## 先统一体积口径

体积优化不能从“删哪个目录”开始。先要回答三个问题：用户所在渠道拿到了哪些 APK，这些 APK 下载了多少字节，安装后又占用了多少空间。三者不是同一个数。

- **上传制品**：APK 是可安装制品；AAB 是发布制品，Google Play 会从中生成 base、ABI、语言、密度和动态功能 APK。AAB 文件本身的大小不能代表任何一台设备的下载量。
- **设备交付量**：普通单 APK 渠道交付一个完整 APK；App Bundle 渠道交付与设备配置匹配的一组 split APK。比较 AAB 时必须固定 ABI、密度、语言、SDK 和动态功能集合。
- **安装占用**：除了已安装 APK，还可能包含提取后的 native 库、编译产物、应用数据和缓存。减少下载量不保证安装占用按相同比例下降。

APK 或 APK 集合中常见的主体包括 `classes*.dex`、`resources.arsc`、`res/`、`assets/`、`lib/<abi>/`、编译后的 `AndroidManifest.xml` 和签名数据。它们的构建、交付和加载方式不同，不能用同一种办法处理。DEX、native library 与资源的专项分析分别见 25.17、25.18 和 25.19；这里建立统一测量、归因和发布门禁。

### APK 是带平台约束的 ZIP

ZIP 目录只能说明文件组织，不能替代 Android 的安装和加载语义：

- `classes*.dex` 保存字节码；单个 DEX 的 `method_ids` 上限是 65,536 个方法引用，不是整个应用只能定义 65,536 个方法。
- `resources.arsc` 与 `res/` 组成编译资源，`assets/` 保存按原始文件接口读取的内容；静态缩减器无法仅凭业务代码判断所有 asset 是否仍被使用。
- `lib/<abi>/` 保存各 ABI 的 ELF 库。条目是否压缩会同时影响下载字节、安装提取和直接映射条件。
- V1/JAR 签名会在 `META-INF/` 生成清单与签名文件；V2/V3 签名位于 APK Signing Block；V4 安装还可能使用独立 `.idsig`。看到 `META-INF/` 不能反推出制品只采用 V1。

因此，评审表要同时记录 ZIP 压缩大小、原始大小、设备实际获得的 split 集合与安装后形态。未压缩条目让 APK 文件变大，却可能减少安装期提取或支持直接映射；它不是可以单独判错的体积回归。

## APK Analyzer 与体积构成分析

[APK Analyzer](https://developer.android.com/studio/debug/apk-analyzer) 可以打开 APK 或 App Bundle，查看文件构成、DEX 包结构、资源、编译后的 manifest，并比较两版制品。界面中的两个尺寸容易混淆：

- **Raw File Size**：该实体压缩后写入 APK ZIP 的大小，也是它对 APK 文件大小的贡献。它不是解压后的大小。
- **Download Size**：工具对 Google Play 压缩传输大小的估算。它适合观察变化方向，不等同于 Play Console 针对某个设备配置给出的精确交付结果。

分析时再按目录归因：

- `classes*.dex`：业务代码、生成代码和依赖；
- `res/` 与 `resources.arsc`：编译资源、替代资源和资源表；
- `assets/`：字体、离线页面、模型、媒体和配置；
- `lib/<abi>/`：各 ABI 的 native 库；
- `META-INF/` 与签名块：签名方案和签名数据。

### 固定构建条件再比较

基线包与候选包要来自同一种 build type、同一渠道、同一签名流程和同一版本的构建工具。是否开启 R8、资源缩减、压缩、加固或渠道重签，都会改变结果。Debug 包与 release 包没有可比性。

下面的命令用于记录单 APK 的文件大小、估算下载大小，并找出两版 APK 的差异。`-h` 是 `apkanalyzer` 的全局人类可读格式参数，应放在 subject 之前。

```bash
apkanalyzer -h apk file-size app-release.apk
apkanalyzer -h apk download-size app-release.apk
apkanalyzer apk compare --different-only baseline.apk app-release.apk
```

前两行给出单 APK 的两个口径；第三行只列出变化项，适合在 CI 中保存为构建附件。命令语法以 [`apkanalyzer` 官方文档](https://developer.android.com/tools/apkanalyzer) 为准。

App Bundle 要先生成 APK Set，再针对固定设备规格计算交付量。下面的第一条命令从已连接的代表设备生成规格文件；审核其中的 SDK、ABI、密度和语言后，应将它作为体积基线的一部分固定下来。CI 还应使用稳定的 `bundletool` 版本和相同签名参数。

```bash
bundletool get-device-spec --output=device-spec.json

bundletool build-apks \
  --bundle=app-release.aab \
  --output=app-release.apks

bundletool get-size total \
  --apks=app-release.apks \
  --device-spec=device-spec.json
```

`get-device-spec` 读取当前连接设备；`build-apks` 生成完整 APK Set；`get-size total` 再按规格选择会交付的 APK。未传 `--device-spec` 时，输出可能是设备维度下的最小值和最大值，不能直接充当某台设备的回归基线。Dynamic Feature 的测量还要固定 `--modules`；详细用法见 25.8 节和 [`bundletool` 文档](https://developer.android.com/tools/bundletool)。

定位顺序由增长目录决定：DEX 增长检查依赖和 R8；`res/` 或 `resources.arsc` 增长检查资源缩减与替代资源；`lib/` 增长检查 ABI、符号和对齐；`assets/` 增长检查低频大文件的交付时机。每次只改一类变量，重新生成 release 制品并比较，才能知道收益来自哪里。

## 代码瘦身：ProGuard / R8 规则优化

Android release 构建的代码缩减器是 R8。AGP 会把 manifest 组件、应用与依赖提供的 keep rules，以及构建系统掌握的其他入口交给 R8；JNI、反射、序列化和由字符串间接引用的代码仍可能需要精确规则。把它简化成“只从 manifest 遍历”会漏掉这些入口。

AGP 9.3 及以上推荐使用 `optimization` DSL。下面的配置同时启用代码和资源优化。

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

新 DSL 会应用 Android 平台默认 keep rules；自定义规则可放在 `src/<variant>/keepRules/*.keep`。规则文件仍要进入版本控制，并与对应变体一起测试。

AGP 9.3 以下，或仍使用 legacy DSL 的工程，可用下面的配置。资源缩减依赖 R8 的可达性结果，不能脱离代码缩减单独工作。

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

`proguard-android-optimize.txt` 启用推荐的优化配置，项目规则放在 `proguard-rules.pro`。AGP 9.3 仍兼容 legacy DSL，但团队应固定一种配置方式，避免规则分散在两个位置。配置生效后，构建产物和测试结果才是判断依据，不能只看 Gradle 开关。

R8 排查可沿着下面四条线进行：

- **依赖**：在 APK Analyzer 的 DEX 视图中按包名比较。业务只调用少量 API，却引入整套 SDK 时，应优先评估依赖拆分、替代库或按功能引入。
- **应用 keep rules**：`-keep class com.example.** { *; }` 会保留整个包及成员。反射、JNI 和框架回调需要规则时，应收窄到被间接访问的类、成员或注解。
- **AAR consumer rules**：库发布者的规则会合并进应用。宽泛 consumer rules 既保留库代码，也可能保留应用侧实现。
- **保留原因**：遇到意外未缩减的类，当前工具链提供 R8 Configuration Analyzer 时可查看宽泛规则；其他版本可临时用 `-whyareyoukeeping` 查询保留路径，避免靠猜测删除规则。

发布系统应归档 `mapping.txt`，否则混淆后的 Java/Kotlin 崩溃和 ANR 堆栈无法还原。`usage.txt` 用于检查删除内容，`seeds.txt` 用于查看入口和保留项，`configuration.txt` 用于审计最终合并配置；资源缩减开启后还要保存资源诊断文件。不同 AGP/R8 版本的文件集合和路径会变化，CI 应从实际 release 构建中确认。

AGP 8.12/8.13 需要通过 `android.r8.optimizedResourceShrinking=true` 手动启用优化版资源缩减；AGP 9.0 起，legacy DSL 中只要 `isShrinkResources=true` 就会自动使用该流程；AGP 9.3 的新 DSL 默认启用优化版资源缩减。升级 AGP/R8 可能改变优化结果，升级提交应单独跑启动、反射、序列化、JNI、通知、Widget 和动态功能测试。修改 R8 输出的后处理工具还可能破坏 DEX 布局和 Baseline Profile，应在发布链中单独审计。细节见 [Enable app optimization](https://developer.android.com/topic/performance/app-optimization/enable-app-optimization) 和 25.7 节。

## 资源瘦身：无用资源移除、资源混淆

资源体积可以从数量、单项大小和交付范围三个方向处理：

- **数量**：用 lint、Android Studio 检查和 `isShrinkResources=true` 清理未使用资源。自动检查只给候选项，删除公共库资源前要确认下游调用。
- **单项大小**：按内容选择 WebP、AVIF、矢量图、字体子集或媒体压缩，并在目标 API、画质、解码耗时和内存占用下验证。格式转换不应只看文件字节数。
- **交付范围**：普通 APK 可用 `resourceConfigurations` 排除明确不支持的替代资源；AAB 默认可按语言、密度和 ABI 生成配置 APK。若应用支持系统“应用语言”或运行时下载语言资源，不能为减小上传包而删掉受支持语言。
- **低频资源**：完整低频功能可放入 Dynamic Feature；大体积非代码素材可评估 Play Asset Delivery 或受校验的 CDN 方案。交付方式不能替代未使用资源清理。

`Resources.getIdentifier()`、字符串拼接、主题皮肤、WebView 协议和 JNI 可能隐藏资源引用。缩减器无法可靠推导时，在 `res/raw/<package>.keep.xml` 中用 `tools:keep` 或 `tools:discard` 声明；这类文件作用于合并后的全局资源，文件名应包含唯一包名，避免应用与多个 AAR 之间冲突。保留规则、用例和调用点应同时维护，不能用一个宽泛通配符长期遮住问题。规则格式见 [Customize which resources to keep](https://developer.android.com/topic/performance/app-optimization/customize-which-resources-to-keep)。

“资源混淆”要区分官方构建优化与第三方重写工具。R8/AGP 的资源缩减、资源表优化属于受支持流程；自行重写资源名、路径、`resources.arsc` 或 R8 中间产物并不是通用 AGP 能力，可能破坏动态查找、资源覆盖、增量更新和诊断工具。没有明确工具版本、产物校验和完整回归时，不应把它列为默认步骤。

Android 17 的 [`ResourceTypes.h`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/androidfw/include/androidfw/ResourceTypes.h) 定义了资源表数据结构。它说明 `resources.arsc` 是编译后的二进制资源表，却不能证明任意资源表改写都兼容平台和构建工具。资源专项优化与验证流程见 25.7 和 25.19 节。

推荐的处理顺序是：移除无用资源，开启官方缩减，处理大文件和替代资源，再评估交付拆分。每一步都检查启动、换肤、通知图标、桌面 Widget、WebView/JNI 桥接和多语言路径。

## `.so` 库瘦身：ABI 过滤、动态下发

同一份 native 功能通常要为多个 ABI 各编译一份 `.so`。Universal APK 会包含这些副本；AAB 可让 Play 只交付设备 ABI 对应的配置 APK。因此，应同时查看上传制品和设备 APK Set，不能看到 AAB 中有四套 ABI 就断言用户下载了四套。

排查时检查四项：

- **支持范围**：根据真实设备与渠道数据决定 `arm64-v8a`、`armeabi-v7a`、`x86_64` 等 ABI，不能把模拟器配置直接带入正式包，也不能在没有兼容性数据时删掉 32 位 ABI。
- **ABI 完整性**：一个 APK/split 中的 JNI 依赖要有相互匹配的 ABI 版本。只删除某个间接依赖的 `armeabi-v7a` 副本，会把体积问题变成安装失败或 `UnsatisfiedLinkError`。
- **发布库与符号**：AGP 默认会剥离 release native 库中的符号表和调试信息。用于 native 崩溃还原的符号应通过 `ndk.debugSymbolLevel` 生成并独立归档或上传，不能靠把未剥离 `.so` 留在交付包中解决。
- **低频功能**：Dynamic Feature 可以包含代码、资源和 native 库；Play Asset Delivery 只能交付非可执行素材。非 Play 渠道若自行下载 native 代码，还要处理签名校验、版本绑定、加载路径、回滚、审核政策和攻击面，不能只按文件大小决定。

使用普通 APK 分发时，下面的配置将变体限制为 `arm64-v8a`。它只适用于已经决定不支持其他 ABI 的产品和渠道。

```kotlin
android {
    defaultConfig {
        ndk {
            abiFilters += listOf("arm64-v8a")
        }
    }
}
```

`abiFilters` 改变应用的设备支持范围，并不负责给不同设备分发不同 APK。需要多个 ABI 时，Play 渠道优先使用 AAB 的 ABI configuration APK；单 APK 渠道可保留多 ABI，或由发布系统管理 per-ABI APK 的签名、版本号和升级兼容。NDK 的 ABI 约束见 [Android ABIs](https://developer.android.com/ndk/guides/abis)。

### Android 17 安装期如何选择 ABI

`android-17.0.0_r1` 的 [`PackageAbiHelperImpl.derivePackageAbi()`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageAbiHelperImpl.java) 会按包是否为 multi-arch、设备支持的 ABI 顺序、覆盖参数以及是否提取 native 库走不同分支：

- 需要提取时，调用 `NativeLibraryHelper.copyNativeBinariesForSupportedAbi()`；该方法先用 `findSupportedAbi()` 选出设备 ABI 列表中排名最靠前的匹配项，再创建目标目录并执行复制与校验。
- `extractNativeLibs=false` 时，`PackageAbiHelperImpl` 直接调用 `findSupportedAbi()` 选择并校验 ABI，不会把 `.so` 复制到应用 native library 目录。
- multi-arch 包会分别检查设备支持的 32 位和 64 位 ABI；不能概括成“primary 找不到再试 secondary”这一条固定路径。

这些分支可在 Android 17 的 [`NativeLibraryHelper`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/com/android/internal/content/NativeLibraryHelper.java) 中交叉核对。未压缩且满足 ZIP/ELF 对齐要求的 `.so` 可以从 APK 直接映射，减少提取副本；对应的 APK 文件可能因不使用 ZIP 压缩而变大，所以要同时记录下载量与安装占用。

### 16 KB page size 是兼容门槛

Android 15 开始支持 16 KB 基础页设备。到 Android 17（API 37），含 native 库的应用仍要同时满足 ELF load segment 对齐和 APK 中未压缩 `.so` 的 ZIP 对齐。Google Play 自 2025 年 11 月 1 日起，要求面向 Android 15/API 35 及以上设备的新应用和更新支持 16 KB page size。当前推荐工具链是 AGP 8.5.1 及以上、NDK r28 及以上，并确认所有预编译 `.so` 也兼容；仅升级自己编译的库不够。完整迁移边界见 [Support 16 KB page sizes](https://developer.android.com/guide/practices/page-sizes) 和 25.18 节。

下面的命令用于确认测试设备的运行时页大小、AAB 请求的页对齐方式，以及最终 APK 内未压缩 shared library 的 ZIP 对齐。`zipalign -P 16` 需要 Android SDK Build-Tools 35.0.0 或更高版本。

```bash
adb shell getconf PAGE_SIZE
bundletool dump config --bundle=app-release.aab | grep alignment
zipalign -v -c -P 16 4 app-release.apk
```

第一行在 16 KB 设备上应输出 `16384`；第二行应包含 `PAGE_ALIGNMENT_16K`；第三行使用检查模式，可以对最终签名并准备交付的 APK 执行。若检查失败，需要重新排列 ZIP，则必须在签名前完成，因为签名后再改变 ZIP 会破坏签名。`zipalign` 通过也只证明 ZIP entry 对齐，不能替代对 ELF `PT_LOAD` 对齐、预编译依赖和 16 KB 真机路径的检查。对齐 padding 可能增加 APK 文件字节数，但兼容要求优先于这部分体积差异。

这里涉及的是构建产物与 Android 17 framework 安装逻辑，不把 kernel 内部实现当作 APK 体积依据。需要追踪 16 KB 运行时页行为时，kernel 统一以 `android17-6.18-2026-06_r6` 为源码锚点。


## 体积门禁比一次性瘦身更可靠

CI 应保存已发布 release 制品、候选 release 制品、构建工具版本、渠道、签名方式和设备规格。门禁阈值来自项目基线与业务预算，不应套用一个与应用类型无关的固定数字。

每次构建至少生成这些记录：

- 单 APK 的 file size、estimated download size 和文件级差异；
- 代表设备规格下 APK Set 的下载量，并区分首次安装与选定动态功能；
- DEX、资源、assets、各 ABI native 库的增量归因；
- R8 mapping、最终配置、删除报告、资源诊断和 native symbols 的归档状态；
- 普通 APK、Play AAB 和其他渠道包各自的结果；
- 含 native 库时的 ABI 完整性与 4 KB/16 KB 兼容结果。

体积增长不一定要阻断发布。新增语言、离线能力或安全库可能有明确价值，但提交记录应说明增长来自哪个制品、影响哪些设备、是否改变安装占用，以及有没有遗漏可删除内容。

## 小结

APK 体积分析先固定制品与设备口径，再按 DEX、资源、assets 和 native 库归因。DEX 关注依赖、R8 入口与宽泛 keep rules；资源关注可达性、替代资源和交付范围；native 库关注 ABI、符号、动态功能与 16 KB 对齐。AAB 是上传制品，设备 APK Set 才能回答用户下载了什么。

交付物应是一份可复现的体积账：基线制品、候选制品、工具版本、设备规格、目录增量、兼容结果和诊断文件齐全。R8 与资源格式的专项处理见 25.7，AAB 与动态交付见 25.8，native 库和 16 KB 对齐见 25.18。
