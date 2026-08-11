---

title: "App Bundle 与按需分发"
chapter: "25.8"
section: "25.8"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-05-14"
last_verified_against: "Android Developers docs 2026-02/2026-03 + AOSP android-16.0.0_r1 source anchors"
confidence: medium
drafted_date: "2026-05-14"
polish_count: 0
sources:
  - type: official
    path: "https://developer.android.com/guide/app-bundle"
  - type: official
    path: "https://developer.android.com/guide/app-bundle/app-bundle-format"
  - type: official
    path: "https://developer.android.com/guide/app-bundle/dynamic-delivery"
  - type: official
    path: "https://developer.android.com/guide/playcore/feature-delivery"
  - type: official
    path: "https://developer.android.com/guide/playcore/feature-delivery/on-demand"
  - type: official
    path: "https://developer.android.com/guide/playcore/asset-delivery"
  - type: official
    path: "https://developer.android.com/tools/bundletool"
  - type: aosp
    path: "https://cs.android.com/android/platform/superproject/+/android-16.0.0_r1:frameworks/base/core/java/android/content/pm/PackageInstaller.java"
  - type: aosp
    path: "https://cs.android.com/android/platform/superproject/+/android-16.0.0_r1:frameworks/base/services/core/java/com/android/server/pm/PackageInstallerSession.java"
  - type: aosp
    path: "https://cs.android.com/android/platform/superproject/+/android-16.0.0_r1:frameworks/base/services/core/java/com/android/server/pm/InstallPackageHelper.java"
  - type: aosp
    path: "https://cs.android.com/android/platform/superproject/+/android-16.0.0_r1:frameworks/base/core/java/android/content/pm/parsing/ApkLiteParseUtils.java"
  - type: book-structure
    path: "Clippings/Android 性能优化 - 原理：重新认识 APK 安装包.md"
  - type: book-structure
    path: "Clippings/Android 性能优化 - so 文件的体积优化实战.md"
  - type: book-structure
    path: "Clippings/Android 性能优化 - 资源文件的体积优化实战.md"
  - type: book-structure
    path: "Clippings/Android 性能优化 - 通过插件化来优化包体积（上）.md"
  - type: book-structure
    path: "Clippings/Android 性能优化 - 通过插件化来优化包体积（下）.md"
tags: [app-bundle, aab, dynamic-feature, play-asset-delivery]
related_chapters: ["25.6", "25.7"]
pipeline_stage: "ready-to-publish"
task6_state: reviewed
task9_state: reviewed
last_task9_review_log: "logs/deep-review/2026-06-15-22-audit.md"
last_task9_at: "2026-06-15T22:23:00+08:00"
task9_result: auto-fixed
task2b_state: fixed
reviewed_by: "openclaw-task6"
reviewed_date: "2026-06-16"
task6_result: "pass-light-edit"
task6_reviewed_at: "2026-05-14T22:10:00+08:00"
task6_reviewed_by: openclaw-task6
last_task6_at: "2026-06-16T01:13:48+08:00"
last_task6_review_log: "logs/review/2026-06-16-01-review.md"
task6_review_notes: "2026-06-16 01:xx Task6 revisiting review: pass-light-edit。四层质检全部通过，无小修、无回炉项。task9_result=auto-fixed（P0/P1/P2=0），queue 无 pending，自动晋升 finalized。"
task2b_result: fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-15"
task9_review_notes: "2026-05-18 12:44 Task9 deep-review: pass-tech-review。P0/P1/P2 0；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-06-15 22:23 Task9 idle audit auto-fix：AOSP 源码锚点从未固定 tag 改为 android-16.0.0_r1，补 `ApkLiteParseUtils.java` 锚点并修复 frontmatter 结束标记；无 P0/P1。"
last_task9_audit: "2026-06-15"
last_task9_autofix_at: "2026-06-15"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-16
---

# App Bundle 与按需分发

## 分发要解决的问题

25.6 和 25.7 处理“产物中还有什么可以删除或缩小”，这里关注“哪些产物应该在什么时间交给哪台设备”。这两个问题相互独立：AAB 不会删除 base module 中的无用代码，R8 也不会决定低频功能是否延后下载。

Android App Bundle（AAB）是发布格式，不是 Android 平台可直接安装的包。Google Play 根据 AAB 生成并签名 APK；设备收到的是 base APK、configuration APK、feature APK 和可能的 install-time asset split。`bundletool` 可以在本地生成同类 APK Set，用于测量和测试。构建与分发关系可参照 [About Android App Bundles](https://developer.android.com/guide/app-bundle)。

平台安装行为以 Android 17（API 37）为锚点。AAB 拆分与 Play Feature/Asset Delivery 由构建工具和 Google Play 服务实现，不涉及 kernel 分包逻辑，因此无需用 kernel 代码作为分发依据。

## AAB 格式与分包机制

AAB 按 module 组织代码和资源。base module 是所有安装必需的主体；feature module 可以在安装时、满足条件时或用户请求时交付；asset pack 用于 Play Asset Delivery。Google Play 还可以按 ABI、语言和屏幕密度生成 configuration APK，让设备只下载匹配配置。

工程中要分开记录三种尺寸：

- **AAB 上传大小**：用于检查发布制品，不代表任一设备的下载量；
- **设备交付大小**：由 SDK、ABI、语言、密度、module 集合和交付时机决定；
- **安装后占用**：还会受 native 库提取、dexopt、asset pack 展开和应用数据影响。

下面的命令从已连接设备生成规格文件，构建完整 APK Set，再估算该设备首次下载的压缩大小。规格文件审核后应固定到体积基线中。

```bash
bundletool get-device-spec --output=device-spec.json

bundletool build-apks \
  --bundle=app-release.aab \
  --output=app-release.apks

bundletool get-size total \
  --apks=app-release.apks \
  --device-spec=device-spec.json
```

`get-size total` 默认统计首次下载时安装的所有 module，其中不止 base。指定 `--modules` 时，工具会把所选 module 的依赖一并计入。未提供设备规格时，结果可能以设备维度的最小值和最大值表示，不能作为某台设备的基线。命令语义见 [`bundletool` 文档](https://developer.android.com/tools/bundletool)。

本地 `build-apks` 使用与 Play 相关的拆包工具，但签名、Play 服务端处理和线上设备选择仍要通过测试轨道验证。未显式传 keystore 时，`bundletool` 会尝试使用 debug key；这样的 APK Set 适合本地测试，不能作为渠道发布制品。

### Android 17 如何接收 split APK

`.aab` 不会进入 Package Manager。安装器通过 [`PackageInstaller`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/PackageInstaller.java) 建立安装会话，写入 base 与 split APK 后提交。`android-17.0.0_r1` 的 [`PackageInstallerSession`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerSession.java) 在 `streamValidateAndCommit()` 中调用 `validateApkInstallLocked()`，主要校验：

- 每个 split name 唯一；
- package name、version code 和签名一致；
- base 声明需要 split 时，要求的 split type 已提供；
- 完整安装缺少必需 split 时返回 `INSTALL_FAILED_MISSING_SPLIT`；
- 通过 [`ApkLiteParseUtils.composePackageLiteFromApks()`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/parsing/ApkLiteParseUtils.java) 形成 base、feature、`uses-split` 和 `configForSplit` 的统一视图。

验证完成后，非分阶段安装进入 `installNonStaged()` 等后续流程。这些校验表明，split APK 不是任意文件集合：base、配置 split 和功能 split 必须作为同一个包的一致集合安装。Android 官方还明确说明，缺少必需 split 的侧载安装会在 Android 10 及以上设备或 Google-certified 设备失败。

## Dynamic Feature Module 实践

Dynamic Feature Module 适合低频、体积较大、允许等待的完整功能，例如视频编辑、OCR、AR 或额外关卡。登录恢复、崩溃提示、支付结果、通知入口等必须立即可用的路径应留在 base。拆分前要检查使用率、首次进入可接受等待、离线需求和模块依赖。

### 交付方式

| 方式 | 行为 | 工程边界 |
| --- | --- | --- |
| install-time | 随应用安装，未声明其他方式时为默认 | 模块化清晰，但不减少首次下载 |
| conditional | 在安装时按设备特性、用户国家或最低 API 等条件交付 | 条件必须与业务可用性一致 |
| on-demand | 应用运行后由用户路径触发下载 | 要处理进度、确认、失败、取消和空间不足 |
| deferred install | 后台尽力预取 on-demand module | 无法跟踪进度，不保证立刻可用 |
| deferred uninstall | 请求稍后移除已安装 module | 不能假设调用返回后文件已经消失 |

Base module 用下面的配置注册动态功能，并把编译平台统一到 Android 17/API 37。

```kotlin
android {
    compileSdk = 37
    dynamicFeatures += setOf(":feature:camera_editor")
}
```

这只建立 base 到 feature 的构建关系。Feature module 还要应用动态功能插件并依赖 base：

```kotlin
plugins {
    id("com.android.dynamic-feature")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.example.app.feature.cameraeditor"
    compileSdk = 37
}

dependencies {
    implementation(project(":app"))
}
```

Feature 可以访问 base 的公共 API；base 不能编译期引用 feature 实现。公共路由、错误类型和埋点协议应放在 base 或独立 API module，功能专用页面、资源和 native 库放在 feature。

Feature 会继承 base 的部分配置，不应重复声明签名、`versionCode`、`versionName` 或 `minifyEnabled`。各 feature 的附加 keep rules 会在构建时与全应用规则合并。

下面的 feature manifest 把模块配置为 on-demand。`dist:title` 引用的字符串应放在 base，保证模块下载前系统也能读取；`dist:fusing` 决定模块能否进入需要融合的 APK，包括 `bundletool --mode=universal` 生成的 universal APK。

```xml
<manifest xmlns:dist="http://schemas.android.com/apk/distribution">
    <dist:module
        dist:instant="false"
        dist:title="@string/title_camera_editor">
        <dist:delivery>
            <dist:on-demand />
        </dist:delivery>
        <dist:fusing dist:include="true" />
    </dist:module>
</manifest>
```

`dist:on-demand` 只声明交付方式。应用仍需通过 Play Feature Delivery Library 请求模块并监听状态。

下面的 Kotlin 骨架展示安装会话过滤和关键状态处理。页面只有收到 `INSTALLED` 后才能进入功能。

```kotlin
val manager = SplitInstallManagerFactory.create(context)
val request = SplitInstallRequest.newBuilder()
    .addModule("camera_editor")
    .build()

var activeSessionId = 0
val listener = SplitInstallStateUpdatedListener { state ->
    if (state.sessionId() != activeSessionId) return@SplitInstallStateUpdatedListener

    when (state.status()) {
        SplitInstallSessionStatus.DOWNLOADING -> {
            // 用 bytesDownloaded/totalBytesToDownload 更新进度。
        }
        SplitInstallSessionStatus.REQUIRES_USER_CONFIRMATION -> {
            // 通过 startConfirmationDialogForResult 请求用户确认。
        }
        SplitInstallSessionStatus.INSTALLED -> {
            // 此时再导航到 feature 页面。
        }
        SplitInstallSessionStatus.FAILED,
        SplitInstallSessionStatus.CANCELED -> {
            // 保留基础功能，并提供重试或退出。
        }
    }
}

manager.registerListener(listener)
manager.startInstall(request)
    .addOnSuccessListener { activeSessionId = it }
    .addOnFailureListener { /* 请求尚未建立，展示可恢复错误。 */ }
```

`startInstall()` 成功回调只返回安装会话 ID，不代表安装完成。监听器要按页面或进程生命周期注销；进程重建后，通过 `installedModules` 和安装会话状态恢复，不能只依赖内存变量。`deferredInstall()` 是无法追踪进度的尽力而为请求，需要立即使用模块时仍应调用 `startInstall()`。完整状态和用户确认流程见 [Configure on-demand delivery](https://developer.android.com/guide/playcore/feature-delivery/on-demand)。

应用和 feature Activity 还要按官方要求启用 SplitCompat。可选 feature 不应声明 exported 组件；需要对外入口时，在 base 放代理组件，确认模块已安装后再转发。刚下载完成的一段时间内，平台可能无法把 feature 新增的 manifest 组件用于所有系统入口，也可能无法让通知等系统界面访问 feature 资源。通知图标、系统会拉起的组件和故障页面应放在 base。

Play 会让已安装 feature 随应用更新；不要给 Play feature 自建独立版本协议。版本一致性问题主要出现在自建资源下载、非 Play 插件或绕过 Play 的分发方案中。

## Play Asset Delivery 与大资源管理

Play Asset Delivery（PAD）面向 asset，不允许 asset pack 包含可执行代码。纹理、音频、关卡、离线模型和媒体素材可以进入 asset pack；DEX、JAR、`.so` 和需要参与编译的功能应使用应用或 Dynamic Feature。

三种模式在磁盘形态上也有差异：

| 模式 | 下载时机 | 访问与更新边界 |
| --- | --- | --- |
| install-time | 随应用安装 | 以 split APK 交付，启动时可用 |
| fast-follow | 安装完成后自动下载，不要求先启动应用 | 以归档文件交付并展开到应用内部存储 |
| on-demand | 应用运行时请求 | 以归档文件交付并展开到应用内部存储 |

Fast-follow 和 on-demand pack 的路径可能跨会话移动，文件也可能被用户或 Play Asset Delivery Library 删除。应用每次使用前都要查询 pack 状态和位置，并把展开后的内容视为只读，因为补丁依赖文件完整性。应用更新期间还可能出现新二进制已安装、资源补丁尚未应用完的短暂状态，页面要能显示“资源更新中”。

首屏必需的最小资源留在 base 或 install-time pack；可在安装后准备的内容用 fast-follow；低频内容用 on-demand。推迟下载不会减少最终磁盘占用，仍要设计空间检查、失败恢复和资源回收。

Texture Compression Format Targeting 允许 AAB 携带多种 GPU 纹理格式，由 Play 为设备选择受支持的格式，适合游戏或图形密集应用。普通 UI 图片仍应按 25.7 的 WebP、AVIF、VectorDrawable 与网络图片策略处理。PAD 的模式、路径和更新语义以 [Play Asset Delivery](https://developer.android.com/guide/playcore/asset-delivery) 为准。


## 国内分发场景的 AAB 替代方案

应用市场和企业分发服务的能力会变化，不能用“国内渠道”概括成一种安装器。每个版本都要维护渠道能力表，至少确认：接收 AAB 还是 APK、是否生成 split、由谁签名、是否加固/重签、增量更新方式、是否支持动态功能和大资源服务。

常见方案如下：

- **渠道原生支持 AAB**：按渠道文档上传和验证，不能假设其分包、签名或动态交付与 Google Play 完全相同。
- **渠道只接收单 APK**：构建专用 universal APK 或常规 APK 变体。`bundletool --mode=universal` 只融合 manifest 中 `dist:fusing=true` 的 feature module；Play Feature Delivery 和 PAD 依赖 Play 服务，非 Play 渠道要另做功能/资源方案。
- **受控安装器支持 split 安装会话**：安装器必须一次提交匹配设备的 base 与全部 required splits，处理签名、版本、失败回滚和升级。
- **自建非代码资源下载**：适用于模型、地图、皮肤、模板和媒体。资源清单要包含版本、长度、哈希、签名、最低应用版本和可选设备选择条件；先验证签名与哈希，再原子发布到版本目录。

下面的命令生成面向连接设备的 APK Set 并安装，用于检查 base/config/feature 组合。若测试 on-demand feature，应在 `build-apks` 中增加 `--local-testing`。

```bash
bundletool get-device-spec --output=device-spec.json

bundletool build-apks \
  --bundle=app-release.aab \
  --output=app-release.apks \
  --device-spec=device-spec.json

bundletool install-apks --apks=app-release.apks
```

这只能验证本地 APK Set。渠道的加固、重签、签名方案、升级、安装器和审核仍要用渠道最终制品测试。Universal APK 还要单独记录体积，避免 Play 的设备裁剪结果掩盖单 APK 渠道成本。

动态 DEX、JAR 或 `.so` 下载不应被当作普通体积方案。Google Play 的 [Device and Network Abuse policy](https://support.google.com/googleplay/android-developer/answer/16559646) 禁止应用从 Google Play 之外下载可执行代码；其他渠道也要逐项核对政策、安全、兼容和更新责任。自建分发只应交付非代码资源。

## 按需分发要进入体积门禁

AAB、Dynamic Feature 和 PAD 上线后，CI 要按设备、module 和下载时机保存结果：

- 首次下载：默认 install-time modules 与 configuration APK；
- on-demand feature：所选 module 及其依赖；
- asset pack：按 install-time、fast-follow、on-demand 分开记录下载与磁盘；
- universal APK：单 APK 渠道的完整下载量；
- 运行指标：feature/asset 下载耗时、失败码、取消、确认和首次使用等待。

下面的命令分别测量同一设备的首次下载和 `camera_editor` module 集合。

```bash
bundletool get-size total \
  --apks=app-release.apks \
  --device-spec=device-spec.json

bundletool get-size total \
  --apks=app-release.apks \
  --device-spec=device-spec.json \
  --modules=camera_editor
```

第一条默认包含首次下载时安装的所有 module；第二条按显式 module 集合测量，并自动加入依赖。两条结果的含义不同，不能简单相减推导 feature 自身大小。最终发布还应使用 Play 测试轨道或渠道测试环境校验。

门禁阈值来自项目基线和实际设备分布，不填写通用百分位或固定数字。制品、`bundletool` 版本、device spec、签名方式和 module 集合必须随结果归档。

## 小结

AAB 决定设备获得哪些 APK，Dynamic Feature 决定功能 module 的交付条件和时机，PAD 决定非代码 asset pack 的交付方式。设备始终安装 APK/split，而不是 AAB；Android 17 Package Manager 会校验 split 的包名、版本、签名和必需关系。

Play 与非 Play 渠道要分开设计。Play Feature Delivery/PAD 不能直接搬到不具备 Play 服务的渠道，universal APK 也不会保留设备裁剪收益。无论使用哪种分发方式，都要把 release 制品、设备规格、module 集合、下载状态、失败恢复和安全校验纳入发布检查。
