---

title: "App Bundle 与按需分发"
chapter: "25.8"
section: "25.8"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-14"
last_verified_against: "Android Developers docs 2026-02/2026-03 + AOSP master code search"
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
    path: "https://cs.android.com/android/platform/superproject/+/master:frameworks/base/core/java/android/content/pm/PackageInstaller.java"
  - type: aosp
    path: "https://cs.android.com/android/platform/superproject/+/master:frameworks/base/services/core/java/com/android/server/pm/PackageInstallerSession.java"
  - type: aosp
    path: "https://cs.android.com/android/platform/superproject/+/master:frameworks/base/services/core/java/com/android/server/pm/InstallPackageHelper.java"
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
related_chapters: ["25.6", "25.7", "12.1"]
pipeline_stage: ready-to-publish
task6_state: "reviewed"
task9_state: reviewed
last_task9_review_log: "logs/deep-review/2026-05-18-12-deep-review.md"
last_task9_at: "2026-05-18T12:44:40+08:00"
task9_result: pass-tech-review
task2b_state: fixed
reviewed_by: openclaw-task6
reviewed_date: "2026-05-14"
task6_result: pass-light-edit
task6_reviewed_at: "2026-05-14T22:10:00+08:00"
task6_reviewed_by: openclaw-task6
last_task6_at: "2026-05-14T22:10:00+08:00"
last_task6_review_log: "logs/review/2026-05-14-22-review.md"
task6_review_notes: "2026-05-14 22:10 Task6：写作层小修 3 处后通过；无新增 L3/L4 回炉项；既有 Task9 P0/P1 队列保留，等待 Task2B。"
task2b_result: fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-18"
task9_review_notes: "2026-05-18 12:44 Task9 deep-review: pass-tech-review。P0/P1/P2 0；Task6 已通过且 queue 无 pending，自动晋升 finalized。"---

# App Bundle 与按需分发

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 AAB 格式与分包机制
- 🔹 Dynamic Feature Module 实践
- 🔹 Play Asset Delivery 与大资源管理
- 🔹 国内分发场景的 AAB 替代方案

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 App Bundle 与按需分发

25.6 和 25.7 节已经处理了包体积治理的两类基础工作：把 dex、资源、`.so`、`assets` 的体积账算清楚，再用 R8、资源缩减、图片格式和 ABI 策略压小产物。25.8 节处理另一类问题：同一份产物是否应该发给所有用户。

Android App Bundle（AAB）是交给 Google Play 或 `bundletool` 的发布格式，设备最终安装的是分发侧生成的 APK 组合。分发侧会根据设备 ABI、屏幕密度、语言、功能模块和资产包生成一组 APK。对用户来说，下载目标从“拿完整安装包”变成“拿这台设备需要的 base APK、配置 APK、功能 APK 或资产包”。

[结构参考: Clippings/Android 性能优化 - 原理：重新认识 APK 安装包.md]

## AAB 格式与分包机制

[已验证: 官方文档, developer.android.com/guide/app-bundle；developer.android.com/guide/app-bundle/app-bundle-format]

AAB 的主要收益来自分包：把不同设备需要的代码、资源和资产拆成可选择的 APK 组合。一个 AAB 通常包含 base module、dynamic feature module、asset pack 和元数据。Google Play 根据这些内容生成 base APK、configuration APK、feature module APK、asset APK 或面向旧设备的 multi-APK。官方文档明确说明，用户设备只下载运行应用所需的代码和资源；语言、密度和 ABI 这三类配置资源会按设备裁剪。

工程里要区分三种体积口径：

- **AAB 文件大小**：这是上传产物大小，适合检查构建产物是否异常，但不能代表用户下载大小。
- **设备下载大小**：同一 AAB 在 arm64 + zh + xxhdpi 设备和 x86_64 + en + hdpi 设备上生成的 APK 组合不同，下载大小也不同。
- **安装后占用**：未压缩 native 库、asset pack、本地缓存和 dexopt 产物会影响安装后磁盘占用，不能只看下载大小。

本地验证要使用 `bundletool`。这段命令用于把 AAB 转成 `.apks`，再按设备配置估算下载体积。重点看同一个 AAB 在不同 `device-spec.json` 下的差异。

```bash
bundletool build-apks \
  --bundle=app-release.aab \
  --output=app-release.apks

bundletool get-size total \
  --apks=app-release.apks \
  --device-spec=pixel-arm64-zh-xxhdpi.json
```

`build-apks` 复现 Google Play 的服务端拆包过程，`get-size total` 给出某台设备需要下载的 APK 组合大小。CI 里应保存几个代表性设备配置：主流 arm64 高密度设备、低密度设备、多语言设备、平板或折叠屏设备。只用 universal APK 做体积门禁，会把 AAB 分发收益全部抹掉。[已验证: 官方文档, developer.android.com/tools/bundletool]

Android 平台侧接收 APK 组合，`.aab` 停在发布和拆包阶段。`PackageInstaller` 提供 `createSession()` / `openSession()` / `write()` / `commit()` 接口，安装会进入 `PackageInstallerSession.installNonStaged()` → Package Manager 的解析、split 校验（`ApkLiteParseUtils.composePackageLiteFromApks()`）、复制流程；缺少 required split 时返回 `INSTALL_FAILED_MISSING_SPLIT`。这些入口在 AOSP `PackageInstaller.java` 和 `PackageInstallerSession.java` 中。[已验证: AOSP master, frameworks/base/core/java/android/content/pm/PackageInstaller.java; frameworks/base/services/core/java/com/android/server/pm/PackageInstallerSession.java]

AAB 对包体积治理有两个边界。第一，AAB 不会替代 R8 和资源缩减；无用代码如果留在 base module，仍会进入所有用户的基础包。第二，AAB 不能自动判断业务功能冷热；模块边界、资源归属和下载时机仍由工程决定。详见 25.6、25.7 节。

## Dynamic Feature Module 实践

[已验证: 官方文档, developer.android.com/guide/playcore/feature-delivery；developer.android.com/guide/playcore/feature-delivery/on-demand]

Dynamic Feature Module 适合拆低频、体积大、依赖重的功能，例如视频编辑、AR、地图离线包、OCR、滤镜、客服 IM、游戏副玩法。它不适合拆启动页、登录态恢复、支付成功页这类必须立即可用的路径。用户进入功能后才开始下载模块，等待、失败、取消、弱网和版本不一致都要进入产品设计。

交付模式按业务路径选择：

| 模式 | 适合场景 | 主要成本 |
| --- | --- | --- |
| install-time | 模块随基础包安装，适合逐步模块化或安装后马上会用的功能 | 对首包下载收益有限；可移除模块数量不要过多 |
| on-demand | 用户触发功能时下载，适合低频重功能 | 首次进入要处理下载等待、失败重试和空间不足 |
| conditional | 按国家、设备特性、API level 等条件安装 | 条件设计错误会让目标用户缺功能或让非目标用户多下载 |
| deferred install / uninstall | 安装后择机下载或卸载 | 状态管理复杂，要处理多端登录、版本回退和缓存清理 |

base module 负责声明动态模块。下面的配置用于把 `:feature:camera_editor` 注册为动态特性模块。读者重点看模块名必须进入 base module 的 `dynamicFeatures` 集合。

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
        minSdk = 29
    }

    dynamicFeatures += setOf(":feature:camera_editor")
}
```

这段配置只建立构建关系。feature module 还要使用 `com.android.dynamic-feature` 插件，并依赖 base module；否则它不会作为可独立交付的功能 APK 进入 AAB。

```kotlin
plugins {
    id("com.android.dynamic-feature")
    kotlin("android")
}

android {
    namespace = "com.example.app.feature.cameraeditor"
    compileSdk = 36
}

dependencies {
    implementation(project(":app"))
}
```

运行时通过 Play Feature Delivery Library 请求模块。下面这段代码只展示状态流转骨架，生产环境还要把状态写入页面状态机。

```kotlin
val manager = SplitInstallManagerFactory.create(context)
val request = SplitInstallRequest.newBuilder()
    .addModule("camera_editor")
    .build()

manager.startInstall(request)
    .addOnSuccessListener { sessionId ->
        // 记录 sessionId，后续监听下载和安装状态。
    }
    .addOnFailureListener { error ->
        // 展示重试、稍后再试或保留基础功能入口。
    }
```

`startInstall()` 只是发起安装请求，不代表模块已经可用。页面入口要监听 `SplitInstallSessionStatus`，在 `INSTALLED` 后再导航；如果状态是 `REQUIRES_USER_CONFIRMATION`、`FAILED`、`CANCELED` 或下载空间不足，要给用户明确的返回路径。把 `startInstall()` 放在点击后同步等待，会把按需加载做成首屏卡顿。

模块边界按依赖方向设计。feature module 可以依赖 base module，base module 不能直接引用 feature module 的实现类；公共接口、路由协议、埋点模型和错误码应放在 base 或独立 API 模块。资源也要跟着功能移动：功能页面专用图片、layout、字符串和 native 库放进 feature module；启动图、通用图标、登录依赖和崩溃兜底页面留在 base module。

[结构参考: Clippings/Android 性能优化 - 通过插件化来优化包体积（上）.md；Clippings/Android 性能优化 - 通过插件化来优化包体积（下）.md]

## Play Asset Delivery 与大资源管理

[已验证: 官方文档, developer.android.com/guide/playcore/asset-delivery]

Play Asset Delivery（PAD）处理的是大资源，不处理可执行代码。游戏纹理、地图包、离线模型、音视频素材、课程包和模板库更适合进 asset pack；需要参与编译、路由和依赖注入的功能代码更适合 Dynamic Feature Module。

PAD 有三种常用交付模式：

- **install-time**：随应用安装，适合首启必须使用的基础资源，例如默认场景、基础素材、首屏离线配置。
- **fast-follow**：应用安装后自动下载，适合首启不阻塞但很快会用的资源，例如新手引导后的默认资源包。
- **on-demand**：用户进入特定功能时下载，适合低频大资源，例如高清地图区域、额外关卡、素材市场资源。

资源包接入要先决定“资源是否影响首屏”。影响首屏的资源不能简单丢到 on-demand，否则首启会变成等待下载；不影响首屏的资源如果继续放在 base module，所有用户都会多付下载成本。比较稳的拆法是：首屏最小资源留在 base，常见路径资源用 install-time 或 fast-follow，低频资源用 on-demand。

对图形资源密集的应用，PAD 还支持 Texture Compression Format Targeting。官方文档说明，开发者可以在 AAB 中放入多种纹理压缩格式，Google Play 按设备支持能力分发更合适的格式。这个能力主要面向游戏和图形重应用；普通 App 的运营图、插画和图标仍应优先走 WebP、AVIF、VectorDrawable 和 CDN 策略，详见 25.7 节。[已验证: 官方文档, developer.android.com/guide/playcore/asset-delivery/texture-compression]

PAD 的风险主要在可用性与缓存一致性：

- **弱网与中断**：下载进度要能恢复，失败后保留基础功能，不要让页面停在空白加载态。
- **版本一致性**：资源包版本要与 App 版本绑定，不能让旧代码读取新资源格式，也不能让新代码读取旧资源目录。
- **磁盘占用**：按需资源不会让磁盘成本消失，只是把下载时机后移。清理策略要纳入发版设计。
- **观测指标**：记录资源包下载耗时、失败码、取消率、重试次数和首用等待时间。没有这些指标，PAD 上线后很难判断收益是否覆盖等待成本。

[结构参考: Clippings/Android 性能优化 - 资源文件的体积优化实战.md；Clippings/Android 性能优化 - so 文件的体积优化实战.md]

## 国内分发场景的 AAB 替代方案

[已验证: 官方文档, developer.android.com/tools/bundletool；待验证: 各国内应用市场 AAB 支持策略需按渠道复核]

国内多数应用市场仍以 APK 分发为主，不能假设它们会像 Google Play 一样处理 AAB、Dynamic Feature Module 和 PAD。工程上要把“构建 AAB”与“渠道能分发 AAB”分开：前者可以本地完成，后者取决于市场能力、签名流程、加固流程和审核规则。

可选方案按风险从低到高排列：

1. **用 `bundletool` 生成渠道 APK**：从同一 AAB 按渠道能力生成不同产物，三类路径要分开：

   - **渠道只收单 APK**：使用 `bundletool build-apks --mode=universal` 或传统 `productFlavor` / ABI split 产出独立 APK。不要把 device-specific split 拆成独立渠道包。
   - **渠道 / 企业安装器支持 split APK session**：一次提交 base + required config splits。Android 10（API 29）+ 和所有 Google-certified 设备上，缺少 required split APK 会导致安装失败（sideload protection）。
   - **universal APK 兜底**：国内渠道和 sideload 场景保留 universal APK 作为 fallback，但要单独记录大小，避免 Play 渠道的分发包收益掩盖其他渠道的实际下载成本。

   收益来自配置裁剪，风险低；缺点是渠道包数量、签名和回归范围会变大。
2. **自研大资源按需下载**：把模型、离线包、皮肤、模板和大媒体资源放到 CDN，由 App 做下载、校验、解压和缓存。收益清晰；成本集中在版本一致性、弱网恢复、磁盘清理和安全校验。
3. **插件化或动态代码下载**：把低频代码拆成插件包或动态 dex / native 组件。收益可能高，但兼容性、稳定性、启动成本、安全审核和线上回滚都更难。Google Play 对动态可执行代码有明确政策要求，国内渠道也可能在加固或审核阶段拦截这类方案。[待验证: 具体渠道政策]

如果选择第一种方案，CI 中可以按设备配置生成多个产物。下面这组命令展示从 AAB 生成指定设备 APK，并把 APK 安装到连接设备上验证。

```bash
bundletool build-apks \
  --bundle=app-release.aab \
  --output=app-release.apks \
  --device-spec=domestic-arm64-zh-xxhdpi.json

bundletool install-apks --apks=app-release.apks
```

这套流程能验证拆包后的 APK 组合是否可安装、启动和进入关键页面。它不能替代渠道验证：加固、重签、V1/V2/V3/V4 签名、增量更新、厂商安装器和应用市场审核仍要单独跑。

自研按需下载要补一层安全协议。每个资源包至少包含资源 ID、版本号、目标 ABI / 屏幕密度、压缩格式、SHA-256、签名、最小 App 版本和回滚策略。下载完成后先校验，再解压到私有目录；读取时按版本目录寻址，不覆盖正在使用的旧资源。资源清理必须可延迟执行，避免用户正在使用功能时删掉文件。

## [自动发现] 按需分发要进入体积门禁

[已验证: 官方文档, developer.android.com/guide/app-bundle/test；developer.android.com/tools/bundletool]

AAB、Dynamic Feature Module 和 PAD 上线后，CI 体积门禁要从“单包大小”改成“多设备、多路径、多时机”。至少保留四类检查：

- **base download size**：代表用户首次安装成本，按主流设备配置记录 P50 / P90 下载大小。
- **feature download size**：每个 on-demand module 的下载大小、首次使用等待时间和失败率。`bundletool get-size total` 默认只测量 base first-download；要测量某个动态特性模块，需传 `--modules=<module>`，bundletool 会自动包含依赖模块：

```bash
# 测量 on-demand module 的下载大小
bundletool get-size total \
  --apks=app-release.apks \
  --device-spec=pixel-arm64-zh-xxhdpi.json \
  --modules=camera_editor
```

CI 中按代表设备 × on-demand module 迭代统计，单独保留 base first-download、feature download、asset pack 和 universal fallback 四类口径。
- **asset pack size**：install-time、fast-follow、on-demand 三类资源包分别记录下载大小、磁盘占用和清理状态。
- **universal fallback size**：国内渠道或 sideload 需要 universal APK 时，记录完整包大小，避免 Play 渠道收益掩盖其他渠道成本。

这类门禁不需要一开始做成复杂平台。先用 `bundletool get-size total`、构建产物归档、代表设备配置和下载状态埋点，就能发现常见问题：某个 feature module 误依赖整套 SDK、资源仍留在 base module、asset pack 版本清理失败、渠道 universal APK 比 Play 下载包大很多。

## 小结

AAB 解决“哪些设备该拿哪些 APK”，Dynamic Feature Module 解决“哪些功能该等用户需要时再拿”，Play Asset Delivery 解决“大资源什么时候下载”。它们和 R8、资源缩减、图片格式、ABI 过滤是两层工作：前者改分发，后者改产物。Google Play 渠道优先使用 AAB + Play Feature Delivery + PAD；国内渠道要把 `bundletool` 生成 APK、自研资源下载和插件化方案分开评估，并把下载失败、版本一致性、安全校验和渠道审核纳入门禁。
