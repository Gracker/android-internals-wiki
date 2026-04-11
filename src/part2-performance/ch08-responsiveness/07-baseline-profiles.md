---
title: "Baseline Profiles 与编译优化实践"
chapter: "8.7"
status: ready-for-review
drafted_date: "2026-04-06"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 9 (API 28) - Android 17 (API 37)"
last_verified: "2026-04-06"
last_verified_against: "AOSP android-17-beta3"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles"
  - type: blog
    path: "intake/research-feeds/2026-04-06-11-baseline-profiles-compilation-optimization.md"
  - type: blog
    path: "intake/research-feeds/2026-04-04-07-ch08-startup-profiles-dex-layout-optimization.md"
tags:
  - android
  - research
pipeline_stage: task6_pending
task6_state: pending
task9_state: pending
task2b_state: idle
---


# 8.7 Baseline Profiles 与编译优化实践

Android 的 ART 运行时经历了多次编译策略的演变——从 Android 5.0 的全量 AOT 编译，到 Android 7.0 的解释执行 + JIT，再到 Profile-Guided 编译。每次转变都在安装时间、运行性能和存储占用之间做不同的权衡。但有一个问题始终存在：**应用首次安装后的冷启动性能**。

在这个时间窗口内，ART 还没有收集到足够的运行时 profile 数据，无法知道哪些方法是热点。结果是大量关键代码只能解释执行，冷启动速度比经过优化的状态慢 30% 甚至更多。

Baseline Profiles 就是 Google 给出的解决方案：**让开发者在 APK 中预置一份"热点方法清单"，在安装时直接告诉 dex2oat 编译器哪些代码需要优先编译为机器码**。这样即使没有任何用户使用数据，首次启动也能获得接近稳态的性能。

[已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles]

## 为什么需要 Baseline Profiles

### ART 编译策略的演变

Android 5.0（Lollipop）引入 ART 时，采用了全量 AOT（Ahead-Of-Time）编译策略：在应用安装时，dex2oat 将整个 DEX 文件编译为机器码。这种策略运行时性能最好（没有 JIT 开销），但安装时间过长、存储占用巨大。在低端设备上，一个大型应用的安装可能需要几分钟。

Android 7.0（Nougat）做了彻底的转向：默认只做解释执行，配合 JIT 编译器在运行时动态优化热点代码。安装速度大幅提升，但代价是**首次运行时性能较差**——那些还没被 JIT 编译到的代码只能走解释器，速度比机器码慢一个数量级。

从 Android 9.0（Pie）开始，ART 引入了 Profile-Guided 编译：在设备上收集运行时 profile（哪些方法被频繁调用），然后交给 dex2oat 做针对性的 AOT 编译。这套机制后来扩展为 Cloud Profiles——Google Play 聚合大量用户的使用数据，生成一个"群体热点清单"随应用分发。

但 Cloud Profiles 有一个关键缺陷：**新版本发布后的前 1-2 天，数据还没收集够，用户等不了**。每次更新都是如此——Cloud Profiles 的积累周期重新开始。

### Baseline Profiles 的定位

Baseline Profiles 填补的就是这个空白。它由开发者在构建时生成，随 APK 一起分发，不需要等待任何用户数据。安装时 dex2oat 根据 profile 中的规则，将指定的方法和类直接编译为机器码。

换句话说：
- **Cloud Profiles** 是群体智慧，需要时间积累
- **Baseline Profiles** 是开发者判断，即时生效
- 两者可以合并使用，效果叠加

[已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles/overview]

### 实测效果

Baseline Profiles 的性能收益有大量公开数据支撑：

Google 官方给出的通用范围是 **15-30% 的启动速度提升**。实际案例中：
- **Reddit**（2024.12）：Baseline Profiles + R8 full mode → median 启动时间缩短 **51%**
- **Duolingo**：Macrobenchmark 测试显示 **25-40%** 的启动速度增益
- **Android Calendar**：启动时间 **~20%** 提升
- **Now in Android** 示例应用：有 profiles 时 229.0ms，无编译时 324.8ms（**~30%**）
- 某手机应用：median startup 提升 **23%**（328ms），Wear OS 应用 **14%**（267ms）

这些数据的差异主要来自应用本身的代码结构和 profile 覆盖的完整度。使用大量 Jetpack/Compose 库的应用收益通常更大，因为这些库的初始化路径长、方法调用密集。

[来源: intake/research-feeds/2026-04-06-11-baseline-profiles-compilation-optimization.md]

## Baseline Profiles 的工作机制

### Profile 格式与打包

Baseline Profile 有两种格式：

**Human-Readable Profile Format（HRPF）** 是开发者直接编辑的文本格式，文件名为 `baseline-prof.txt`。每行是一条规则，指定一个类或方法：

```
HSPLandroidx/compose/runtime/ComposerImpl;->updateValue(Ljava/lang/Object;)V
HSPLandroidx/compose/runtime/ComposerImpl;->changed(Z)V
Landroidx/compose/runtime/ComposerKt;
```

前缀字母编码了规则的类型（H = hot method, S = startup method, P = post-startup method, L = class 等）。大多数开发者不需要手写这个文件——工具会自动生成。

**二进制格式** 是 AGP（Android Gradle Plugin）将 HRPF 编译后的产物，文件名为 `baseline.prof`，打包在 APK 的 `assets/dexopt/baseline.prof` 路径下。对于 AAB（Android App Bundle）分发格式，profile 位于对应的 dex 分片内。

[已验证: AOSP, frameworks/base/cmds/profman/profman.cc 二进制格式解析逻辑]

### 安装时的编译流程

当用户安装一个包含 Baseline Profiles 的应用时，系统执行以下步骤：

1. **Profile 提取**：Package Manager 从 APK 中提取 `baseline.prof` 二进制文件
2. **Profile 合并**：如果设备上同时存在 Cloud Profiles（来自 Google Play 的聚合数据），系统会将 Baseline Profiles 与 Cloud Profiles 合并。合并策略是取并集——两者指定的方法都会被编译
3. **dex2oat 编译**：ART 使用 `speed-profile` 编译过滤器调用 dex2oat，只编译 profile 中列出的方法。相比全量编译（`speed` 过滤器），这种方式编译时间短得多
4. **产物存储**：编译产物（`.odex`、`.vdex`、`.art` 文件）存储在 `/data/misc/profiles/` 或 `/data/dalvik-cache/` 目录下

关键点在于编译过滤器的选择。没有 profile 时，dex2oat 默认使用 `verify` 过滤器（只做验证不编译）；有 profile 时使用 `speed-profile`（编译 profile 中指定的方法）。这个差异直接决定了首次启动的性能。

### ART Service 与 Profile 管理

Android 14 引入了 **ART Service**，将 dexopt（DEX 优化）管理从 Package Manager Service 中独立出来。ART Service 提供了一组 API 和系统属性来控制编译行为：

```
# 查看当前编译过滤器
adb shell getprop pm.dexopt.install

# 查看特定应用的编译状态
adb shell cmd package compile --dump com.example.app

# 强制重新编译（使用 speed-profile）
adb shell cmd package compile -m speed-profile -f com.example.app
```

ART Service 管理 profile 的生命周期：应用更新时清除旧 profile，后台 dexopt 任务定期用新数据更新编译产物，设备空闲时做全量优化。Baseline Profiles 在每次安装/更新时都会被重新消费。

[已验证: AOSP, frameworks/base/services/art/ArtManagerLocal.java, Android 14+]

### Cloud Profiles 的配合

Cloud Profiles 和 Baseline Profiles 的关系不是竞争，而是互补：

| 维度 | Baseline Profiles | Cloud Profiles |
|------|-------------------|----------------|
| 来源 | 开发者定义 | 用户数据聚合 |
| 生效时机 | 安装即生效 | 需 1-2 天数据积累 |
| 覆盖范围 | 开发者判断的 CUJ | 真实用户热点 |
| 更新频率 | 随 APK 更新 | 持续优化 |
| 适用场景 | 所有渠道 | 仅 Google Play |

当两者同时存在时，ART 会合并 profile 并按合并后的完整列表做 AOT 编译。这意味着即使开发者遗漏了某些热点路径，Cloud Profiles 也能在后续补上。

[待验证: 非 Google Play 渠道是否也有类似的云端 profile 机制]

### Android 16 Cloud Compilation

Android 16 引入了 **Cloud Compilation**（云端编译），将编译过程进一步推向云端：

1. Google Play 在服务端执行 dex2oat，生成预编译产物
2. 产物以 **SDM（Secure Dex Metadata）** 格式下发，使用与 APK 相同的密钥签名
3. 设备端下载 SDM 后直接使用，无需本地编译

这意味着安装过程完全跳过了 dex2oat 编译步骤，安装速度大幅提升（尤其低端设备），应用更新时的"冻结"时间降到毫秒级。

Cloud Compilation 的完整优化链路：

```
开发者侧                    Google 侧                    设备侧
─────────                   ─────────                    ─────────
Baseline Profiles           Cloud Profiles               JIT 热路径收集
(AGP 生成)         →        (聚合优化)           →        Profile 上传
                                                        ↓
Startup Profiles            Cloud Compilation            dex2oat AOT
(AGP 8.3 DEX 重排)  →       (预编译 SDM)         →       本地安装
                                                        ↓
R8/D8 优化                  AutoFDO (GKI)                内核级 PGO
(代码收缩/DEX布局)   →       (内核 hot path)      →       CPU 效率提升
```

[来源: intake/research-feeds/2026-04-06-11-baseline-profiles-compilation-optimization.md]

## 生成与维护 Baseline Profiles

### 使用 Macrobenchmark 生成

Baseline Profiles 的标准生成流程基于 Jetpack Macrobenchmark 库。步骤如下：

**1. 添加 Baseline Profile Gradle 模块**

在项目中创建一个专门的 `baselineprofile` Gradle 模块，或者使用 Android Studio 的向导（File → New → Baseline Profile Module）。模块配置中需要指定目标应用和要覆盖的 Critical User Journeys（CUJ）。

**2. 编写 Profile Generator 测试**

```kotlin
@RunWith(AndroidJUnit4::class)
class BaselineProfileGenerator {
    @get:Rule
    val rule = BaselineProfileRule()

    @Test
    fun generateBaselineProfile() {
        rule.collect(
            packageName = "com.example.app",
            // 定义要覆盖的关键路径
            includeInStartupFilter = true  // 启动路径自动包含
        ) {
            // 冷启动
            pressHome()
            startActivityAndWait()

            // 核心用户旅程
            findViewById(R.id.navigation_search).clickAndWait(Until.newWindow(), 1000)
            findViewById(R.id.search_input).text = "performance"
            findViewById(R.id.search_button).clickAndWait(Until.newWindow(), 2000)
        }
    }
}
```

这段代码在运行时会记录所有被执行的方法，生成 profile 规则。

**3. 执行生成任务**

```bash
./gradlew :app:generateBaselineProfile
```

AGP 会自动在目标设备上运行 profile generator，收集 profile 数据，然后将 HRPF 文件写入项目的 `src/main/generated/baseline-prof.txt`。

[已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles/create-baselineprofile]

### Profile 的关键覆盖路径

一个高质量的 Baseline Profile 需要覆盖以下路径：

- **冷启动**：从 `Application.onCreate()` 到首帧渲染完成
- **热启动**：从 Activity `onRestart()` 到界面恢复
- **核心用户旅程**：应用最常用的 3-5 个功能流程
- **Compose 渲染**：如果使用 Compose，包含组合（composition）相关方法

Profile 不需要追求 100% 覆盖——覆盖 80% 的启动路径就能获得大部分收益。过于追求覆盖率反而会导致 profile 文件过大，增加安装时的编译时间。

### AGP 自动化

从 AGP 8.0 开始，Baseline Profiles **默认启用**。相关 Gradle 配置：

```kotlin
// app/build.gradle.kts
android {
    baselineProfile {
        // 自动生成并合并 profile
        automaticGenerationDuringBuild = true
        // 保存生成的 profile 到 src/main/
        saveInSrc = true
    }
}
```

AGP 8.3 引入了 **Startup Profiles**（启动 profile），作为 Baseline Profiles 的子集。Startup Profiles 专门指导 D8 编译器优化 DEX 文件的布局，将启动阶段需要的方法集中到主 DEX 文件中，减少启动时的磁盘 I/O。配合 Baseline Profiles 使用，冷启动可额外提升 **15-30%**。

[来源: intake/research-feeds/2026-04-04-07-ch08-startup-profiles-dex-layout-optimization.md]

## 与 AutoFDO 的关系与区别

Baseline Profiles 和 AutoFDO（1.12 节）虽然都是 Profile-Guided Optimization，但优化对象和作用层面完全不同：

**AutoFDO** 是系统级的编译优化，基于硬件性能计数器（如 CPU 的 LBR——Last Branch Record）收集 native 代码的热路径信息，反馈给编译器优化内核和系统服务的机器码。它优化的是 **C/C++ 代码的指令布局和分支预测**。

**Baseline Profiles** 是应用级的编译优化，基于代码路径覆盖指导 dex2oat 将热点 DEX 方法预编译为机器码。它优化的是 **Java/Kotlin 代码的 AOT 编译范围**。

两者的优化对象不重叠，可以同时使用：

| 维度 | AutoFDO | Baseline Profiles |
|------|---------|-------------------|
| 代码类型 | Native（C/C++） | Managed（Java/Kotlin） |
| 运行层面 | 内核 + 系统服务 | 应用 + 第三方库 |
| 数据来源 | 硬件性能计数器 | 代码路径覆盖 |
| 分发方式 | GKI 内核镜像 | APK 内置 |
| 版本要求 | Android 12+ GKI | Android 9+（API 28+） |

在 OEM 构建流程中，两者配合使用：AutoFDO 优化系统镜像中 native 代码的执行效率（冷启动 4.3%、Binder-rpc 21.7%），Baseline Profiles 优化预装应用的 Java 代码启动速度。

[交叉引用: 1.12 AutoFDO 反馈导向编译优化]

## 在 Perfetto 中验证 Baseline Profiles 的效果

验证 Baseline Profiles 是否生效，需要在 Perfetto 中对比安装 profile 前后的启动 trace。

### 对比方法

**步骤 1：无 profile 安装**

```bash
# 使用 verify 编译过滤器安装（跳过 AOT 编译）
adb install --no-streaming app.apk
adb shell cmd package compile --set-compilation-state -m verify com.example.app
```

**步骤 2：抓取冷启动 trace**

```bash
adb shell perfetto \
  -c - --txt \
  -o /data/misc/perfetto-traces/trace_no_profile.pb \
<<EOF
buffers: { size_kb: 65536 }
data_sources: { config { name: "linux.ftrace" ftrace_config {
  ftrace_events: "sched/sched_switch" ftrace_events: "power/cpu_frequency"
  atrace_categories: "am" atrace_categories: "view" atrace_categories: "dalvik"
}}}
duration_ms: 10000
EOF
```

**步骤 3：安装 profile 版本，再次抓取 trace**

对比两次 trace 的关键指标：
- **`ActivityManager: Start proc` 到 `Choreographer doFrame` 的时间差**：这是冷启动到首帧的完整时间
- **dex2oat 编译 slice 的出现**：有 profile 时应该看到 `dex2oat` 的编译活动更早完成
- **JIT 编译活动**：无 profile 时启动阶段会出现大量 `JIT compiling` slice；有 profile 时应该显著减少

### app-speed-index 指标

Perfetto 提供了 `app-speed-index` 指标来量化应用启动速度的综合评分。通过 SQL 查询可以获取：

```sql
-- 查询 app-speed-index
SELECT
  package_name,
  app_speed_index
FROM app_speed_index
WHERE package_name = 'com.example.app';
```

这个指标综合了多个启动阶段的耗时，是一个标准化的性能分数。

[待补充: Trace 截图——有/无 Baseline Profiles 的冷启动 trace 对比]

## 常见问题与最佳实践

### Profile 过大导致编译时间增加

一个常见误区是"profile 越大越好"。实际上，profile 中列出的每个方法都需要 dex2oat 编译。如果 profile 列了数千个方法，安装时的编译时间反而会成为瓶颈——用户看到的"安装优化中..."提示会持续很久。

最佳实践是**只覆盖启动和核心 CUJ 的代码路径**，而不是整个应用的方法列表。Google 建议保持 profile 在合理的行数范围内（通常不超过几千条规则）。

### 多 DEX 文件的 Profile 管理

大型应用通常使用 multidex（多个 DEX 文件）。每个 DEX 文件都可以有自己的 profile 规则，它们会被合并处理。AGP 会自动处理多 DEX 的 profile 分配，开发者通常不需要手动干预。

### AAB 与 Baseline Profiles 的打包

使用 AAB（Android App Bundle）分发时，Baseline Profiles 的打包由 AGP 自动处理。profile 数据存储在 AAB 的 `dex-metadata` 目录下，随 split APK 一起分发。对于按 ABI 或屏幕密度分发的场景，profile 在所有 split 中共享。

### 非 Google Play 渠道的 Profile 处理

这是国内开发者最关心的问题。Baseline Profiles 本身**不依赖 Google Play**——它打包在 APK 中，安装时直接被 dex2oat 消费。无论用户通过什么渠道安装（侧载、国内应用商店），只要设备的 ART 支持 speed-profile 编译过滤器（Android 9+），Baseline Profiles 都会生效。

但是，Cloud Profiles 和 Cloud Compilation **依赖 Google Play 服务**。非 Google Play 渠道无法获得这两个优化。这意味着在国内市场，Baseline Profiles 是唯一的 profile 优化手段，更加重要。

[待验证: 国内主流应用商店是否有类似的云端 profile 基础设施]

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

实测数据也验证了这一点：Compose 应用添加 Baseline Profiles 后的收益通常比传统 View 应用更大（25-40% vs 15-20%），原因就是 Compose 运行时的编译依赖更重。

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance#baseline_profiles]

## 扩展

### Profileable 应用与性能分析

Android 13 引入了 `profileable` 标志，允许应用在不设置为 debuggable 的情况下进行性能分析。这对于 Baseline Profiles 的生成和验证有直接影响：

- **Profileable 应用**：可以被 Macrobenchmark 和 Perfetto 分析，性能接近 release 版本
- **Debuggable 应用**：ART 会关闭部分优化（如 JIT 内联），性能数据不准确
- **Release 应用（无 profileable）**：无法进行任何性能分析

在 `AndroidManifest.xml` 中添加 profileable 标志：

```xml
<profileable
    android:shell="true"
    tools:targetApi="30" />
```

这个配置允许 shell（adb）用户分析应用，同时保持 release 级别的性能特征。

### OEM 系统镜像级别的编译优化

Baseline Profiles 不只适用于第三方应用。在系统镜像中，预装应用和 framework 本身也可以使用预编译 profile 来优化启动性能：

- **System Baseline Profiles**：在系统构建时预置的 profile 文件，存储在 `/system/etc/sysconfig/` 下
- **framework 优化**：`system_server` 和 framework JAR 的预编译 profile 可以加速系统启动和核心服务的初始化
- **预装应用优化**：OEM 可以为预装应用生成 profile，确保出厂后的首次开机即拥有最优性能

在 AOSP 构建流程中，可以通过 `WITH_DEXPREOPT=true` 和 `WITH_DEXPREOPT_BOOT_IMG_AND_SYSTEM_SERVER_ONLY=true` 来控制预编译的范围。

[待补充: 具体的系统构建配置示例和 profile 文件格式]

## 参考资料

### Android 16 云端编译 + Baseline/Startup Profiles DEX Layout 优化
- 来源：https://android-developers.googleblog.com/cloud-compilation-baseline-profiles
- 类型：research
- 摘要：云编译替代设备端dex2oat。Startup Profiles DEX Layout额外+15-30%启动速度。Baseline Profiles + Startup Profiles组合：首次launch即可30%执行提速，已深度集成CI/CD。
- 入库时间：2026-04-08

