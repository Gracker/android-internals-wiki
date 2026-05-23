---
title: "R8 Configuration Analyzer 与 keep 规则体积归因"
chapter: "14.20"
section: "14.20"
status: ready-for-review
drafted_date: "2026-05-23"
applicable_versions: "AGP 9.3.0-alpha05+ / R8 9.3.7-dev+；AGP 9.2 及更早版本可手动生成报告"
last_verified: "2026-05-23"
last_verified_against: "Android Developers R8 Configuration Analyzer / R8 full mode / keep rule docs, Android Developers Blog 2025-11/2026-05"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/app-optimization/r8-configuration-analyzer"
  - type: official
    path: "https://developer.android.com/topic/performance/app-optimization/enable-app-optimization"
  - type: official
    path: "https://developer.android.com/topic/performance/app-optimization/full-mode"
  - type: official
    path: "https://developer.android.com/topic/performance/app-optimization/keep-rule-examples"
  - type: official
    path: "https://developer.android.com/agents/skills/performance/r8-analyzer/references/CONFIGURATION-ANALYZER"
  - type: official
    path: "https://developer.android.com/agents/skills/performance/r8-analyzer/references/CONFIGURATION"
  - type: blog
    path: "https://developer.android.com/blog/posts/configure-and-troubleshoot-r8-keep-rules"
  - type: blog
    path: "https://android-developers.googleblog.com/2026/05/whats-new-android-developer-tools.html"
  - type: github
    path: "https://github.com/android/skills/blob/main/performance/r8-analyzer/SKILL.md"
tags: [r8, app-size, build-tools, keep-rules, apk-optimization]
related_chapters: ["12.1", "25.7", "14.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-23"
gap_source: "官方文档"
---

# 14.20 R8 Configuration Analyzer 与 keep 规则体积归因

<!-- outline-start -->
## 要点

### 🔹 R8 Configuration Analyzer 解决的问题
说明它面向的是 keep 规则过宽、默认 AGP 规则、consumer rules 与 App 自定义规则叠加后造成的优化空间损失；区别于 APK Analyzer 的“结果体积查看”。

### 🔹 输入材料与报告产物
梳理生成分析数据所需的构建产物、规则来源、impactful rules、subsumed rules、历史对比文件，以及报告中哪些字段适合进入 CI。

### 🔹 keep 规则影响分级
按“阻止 shrinking / obfuscation / optimization / attribute pruning”的影响拆分规则代价，说明 `allowshrinking`、`allowobfuscation`、`allowoptimization` 的使用边界。

### 🔹 典型高风险规则模式
覆盖包级 `-keep class ** { *; }`、反射框架兜底规则、序列化字段保留、JNI 入口、ServiceLoader、注解与泛型签名等场景，给出排查顺序。

### 🔹 与 R8 full mode 迁移的配合
说明 AGP 8.0+ full mode 下 analyzer 如何帮助定位兼容问题，同时避免把 full mode 关闭当作长期方案。

### 🔹 CI 与回归治理
给出基线包、候选包、规则差异、dex size、mapping / seeds / usage 文件的归档方式，定义“规则变宽”的评审门槛。

### 🔹 与 APK Analyzer / apkanalyzer 的边界
APK Analyzer 看最终 APK 组成，R8 Configuration Analyzer 看规则为什么阻止优化；两者在体积排查中应按先结果、后原因的顺序配合。

## 扩展

### 🔸 反射与代码生成框架的 keep 规则模板
后续可整理 Gson、Moshi、Jackson、Room、Hilt、Retrofit、JNI 注册和插件化框架的最小规则模板。

### 🔸 R8 Analyzer 与 AI agent 辅助评审
官方 android/skills 中已有 r8-analyzer skill，可作为规则审查和报告摘要的工具链参考，但需要保留人工复核环节。

<!-- outline-end -->

## 为什么需要单独看 R8 Configuration Analyzer

APK 体积排查通常从 12.1 节的 APK Analyzer 开始：先看 `classes.dex`、`resources.arsc`、`res/`、`lib/` 哪一块在增长，再判断该动 R8、资源、图片还是 native 库。这个入口能回答“结果变大在哪里”，但回答不了“哪条 keep 规则让 R8 放弃了哪些优化”。

R8 Configuration Analyzer 补的是后一半。它把最终合并后的 R8 配置映射到类、字段和方法，给出 shrinking、optimization、obfuscation 三类分数，并列出影响最大的 keep 规则和被覆盖的规则。体积治理到 keep 规则这一层时，它比肉眼读 `proguard-rules.pro` 更可靠，因为最终生效的规则还包括默认 AGP 规则、App 自定义规则、各个 AAR 传进来的 consumer rules，以及部分工具生成的规则。

[已验证: 官方文档, developer.android.com/topic/performance/app-optimization/r8-configuration-analyzer]

工具的适用前提要按版本拆开。R8 Configuration Analyzer 需要 R8 9.3.7-dev 或更新版本；这个版本随 AGP 9.3.0-alpha05 及之后版本预置。AGP 9.3.0-alpha05 起，运行带 R8 的构建会自动生成 `build/outputs/mapping/release/configanalyzer.html`。AGP 9.2 及更早版本要在 Gradle 命令里显式传入系统属性，把 HTML 报告输出到指定目录。[已验证: 官方文档, developer.android.com/topic/performance/app-optimization/r8-configuration-analyzer]

这段命令用于旧版本工具链手动生成 HTML 报告，读者重点看系统属性名和输出目录。

```bash
mkdir -p /tmp/r8analysis

./gradlew assembleRelease \
    -Dcom.android.tools.r8.dumpkeepradiushtmltodirectory=/tmp/r8analysis
```

生成报告前要确保构建走的是 release 或等价的性能测试变体，并且 `isMinifyEnabled=true`。如果工程没有启用 R8，报告没有分析对象；如果用 debug 包生成，规则、依赖和构建开关都可能和线上包不一致。

## 报告里哪些字段该看

[已验证: 官方文档, developer.android.com/topic/performance/app-optimization/r8-configuration-analyzer]

报告首页的三类分数衡量“仍允许 R8 处理的代码占比”，不能当作已经获得的优化收益。

| 指标 | 它衡量什么 | 分数下降时先看哪里 |
| --- | --- | --- |
| Shrinking score | 类、字段、方法中仍允许被删除的比例 | 包级 keep、`-dontshrink`、过宽的 `-keep class ** { *; }` |
| Optimization score | 仍允许被内联、类合并、访问级别调整等优化处理的比例 | `-dontoptimize`、未加 `allowoptimization` 的宽规则、full mode 兼容性兜底规则 |
| Obfuscation score | 仍允许被重命名的比例 | `-dontobfuscate`、协议字段名和反射类名被整包固定 |

这三个分数要结合规则列表读。一个项目的 shrinking score 下降，原因可能是 App 侧新增一条宽规则，也可能是三方 SDK 的 consumer rules 在新版本里扩大了范围。报告里的 source 字段用于判断规则来源：App 规则能直接改；library consumer rules 更适合通过升级 SDK、反馈库作者或在 App 侧增加更窄的替代规则处理；默认 AGP 规则只做识别，不应改动。

`impactful rules` 适合排优先级。它把 keep 规则影响到的类、字段、方法数量聚合起来，能快速暴露“写一条顶十条”的规则。排查时先看影响范围最大的规则，再看它是否真的对应运行时入口。

`subsumed rules` 用于清理技术债。典型例子是同一个包里同时存在这两条规则：

```proguard
# 规则 A：保留整个包
-keep class com.example.package.** { *; }

# 规则 B：保留包内一个类
-keep class com.example.package.MyClass
```

规则 A 已经覆盖了规则 B，报告会把这种重叠关系暴露出来。处理时先确认 A 是否过宽：如果只有 `MyClass` 需要保留，应收窄 A；如果整包都要保留，再考虑 B 是否冗余。

## keep 规则的代价分级

[已验证: 官方文档, developer.android.com/blog/posts/configure-and-troubleshoot-r8-keep-rules；developer.android.com/topic/performance/app-optimization/keep-rule-examples]

keep 规则的风险不只体现在“删不删”。同一条规则可能同时影响四件事：是否允许删除、是否允许重命名、是否允许优化、是否保留 class file attribute。规则越宽，R8 能处理的空间越小。

| 规则影响 | 常见触发方式 | 典型后果 | 修正方向 |
| --- | --- | --- | --- |
| 阻止 shrinking | `-keep class com.foo.** { *; }`、`-dontshrink` | 未使用类和成员留在 dex 中 | 改成精确类、接口实现、注解匹配或成员级规则 |
| 阻止 obfuscation | 直接 `-keep` 类名或字段名 | dex 字符串池变大，mapping 收益下降 | 确认运行时是否依赖名字；不依赖就加 `allowobfuscation` |
| 阻止 optimization | 宽规则未放开 optimization、`-dontoptimize` | 方法内联、类合并、访问级别调整受限 | 不用全局禁用；对安全范围加 `allowoptimization` |
| attribute 保留不足 | full mode 下只写 `-keepattributes Signature` | 反射框架读不到泛型、内部类或注解信息 | 同时 keep 关联类、字段或方法，并尽量放开混淆和优化 |

`allowshrinking`、`allowobfuscation`、`allowoptimization` 的作用是把一部分处理权还给 R8。是否能加这些修饰符，取决于运行时契约依赖什么：

- 如果框架拿到的是 `Class` 对象，不依赖字符串类名，类名通常允许混淆。
- 如果对象只在某个功能路径使用，功能不用时允许删除，规则可以加 `allowshrinking`。
- 如果反射只要求成员存在，不要求调用点形状和访问级别不变，可以考虑 `allowoptimization`，但要用 release 包跑覆盖测试。
- 如果 JSON 协议、JNI 查找或服务端下发类名依赖原始名字，不能放开对应的 obfuscation。

这组规则展示同一个运行时入口怎样收窄。重点是只保留 JNI 需要的 native 方法名，避免固定整个包。

```proguard
# 默认优化规则已覆盖 Java/Kotlin 调 native 的 downcall 场景。
-keepclasseswithmembernames,includedescriptorclasses class * {
    native <methods>;
}

# native 层按固定签名回调 Java/Kotlin 时，只保留被回调成员。
-keepclassmembers class com.example.bridge.NativeBridge {
    public void onNativeEvent(com.example.bridge.NativePayload);
}
```

第一条是默认规则里常见的 JNI downcall 保护思路；第二条面向 native 层 upcall 的项目规则。二者都比 `-keep class com.example.bridge.** { *; }` 窄，回归验证也更容易定位问题。

## 高风险规则的排查顺序

[已验证: 官方文档, developer.android.com/topic/performance/app-optimization/keep-rule-examples]

规则排查不要从“删规则”开始。更稳的顺序是：先根据 APK Analyzer 或 dex size diff 找增长包，再用 Configuration Analyzer 找规则影响范围，随后回到代码确认运行时入口。

1. **包级兜底规则**：优先处理 `-keep class ** { *; }`、`-keep class com.company.** { *; }`、`-keep class * { *; }`。这类规则会同时压低三类分数，常见来源是迁移 R8 full mode 时的临时兜底。
2. **反射框架规则**：Gson、Moshi、Jackson、反射式路由、插件化框架要区分“依赖类名”“依赖字段名”“依赖泛型签名”三种契约。只读字段名就保字段；读泛型就保 `Signature` 和相关类型；不要把整包模型全量固定。
3. **代码生成框架规则**：Room、Hilt、Retrofit 这类框架多数版本已通过注解处理器、KSP 或 consumer rules 生成必要规则。App 侧新增大范围兜底前，先看库版本和最终 `configuration.txt`。
4. **JNI 入口**：Java/Kotlin 调 native 的 `native <methods>` 通常由默认优化规则覆盖；native 回调 Java/Kotlin 的 upcall 才需要项目补规则。规则要精确到 bridge 类或方法签名。
5. **ServiceLoader 和可选依赖**：`META-INF/services/` 或字符串类名加载路径要保留 provider 类和无参构造函数；如果传入的是 `Class` 对象，通常不需要保留原始类名。
6. **注解和泛型签名**：R8 full mode 下，attribute 是否保留与被 keep 的类、字段、方法有关。只写 `-keepattributes` 可能不够，必须确认读取 attribute 的对象也被规则匹配。

排查时同步查看 `build/outputs/mapping/<variant>/configuration.txt`、`mapping.txt`、`seeds.txt`、`usage.txt`。`configuration.txt` 说明最终规则从哪里来；`seeds.txt` 说明哪些元素被规则保留；`usage.txt` 说明哪些元素被删除；`mapping.txt` 说明哪些名字发生了变化。四个文件和 analyzer 报告放在一起，才能判断“规则变窄后是否真的产生收益”。

## 与 R8 full mode 迁移的配合

[已验证: 官方文档, developer.android.com/topic/performance/app-optimization/full-mode；developer.android.com/agents/skills/performance/r8-analyzer/references/CONFIGURATION]

R8 full mode 从 AGP 8.0 起默认启用。它会做更积极的类合并、方法内联、属性裁剪和访问级别调整。迁移失败时，常见补救动作是往 `proguard-rules.pro` 里加宽规则，甚至在 `gradle.properties` 里保留 `android.enableR8.fullMode=false`。这能让崩溃暂时消失，但会把优化空间长期锁死。

Configuration Analyzer 适合放在 full mode 迁移后的第二轮：第一轮先让 release 包稳定跑完 smoke test，第二轮再看哪些兜底规则影响最大。报告里影响最大的规则，往往就是迁移期间为了“先过”加进去的规则。处理方式是把运行时契约拆成可验证的单元：

- Gson `TypeToken` 依赖 `Signature`，规则要保留泛型签名和相关 `TypeToken` 类型；Gson 2.11.0+ 已带 full mode 所需 consumer rules，旧版本才考虑 App 侧补规则。
- 反射构造只需要无参构造函数时，保构造函数，不要保整个类的所有字段和方法。
- 注解扫描只需要运行时注解时，保 `RuntimeVisibleAnnotations` 和被扫描成员，不要把包内所有类都固定。
- native upcall 只需要固定被 native 查找的方法签名时，保 bridge 方法，不要禁用整包混淆和优化。

如果必须临时关闭 full mode，要把它当作定位开关，并给回滚设截止时间。长期方案是用 analyzer 找出压低分数的兜底规则，再用 release 回归覆盖序列化、登录、支付、推送、深链、插件加载和 JNI 路径。

## CI 与回归治理

[已验证: 官方文档, developer.android.com/topic/performance/app-optimization/r8-configuration-analyzer；developer.android.com/agents/skills/performance/r8-analyzer/references/CONFIGURATION-ANALYZER]

R8 Configuration Analyzer 更适合做“趋势门禁”，不适合把某个绝对分数当全项目通用红线。不同 App 的反射、动态化和 SDK 结构差异很大，同样 80% 的 optimization score，在一个纯 Compose App 和一个插件化 App 里含义不同。

CI 里至少归档这些产物：

| 产物 | 建议路径 | 用途 |
| --- | --- | --- |
| `configanalyzer.html` | `build/outputs/mapping/<variant>/configanalyzer.html` 或手动输出目录 | 查看三类分数、impactful rules、subsumed rules |
| `configuration.txt` | `build/outputs/mapping/<variant>/configuration.txt` | 追踪最终合并后的规则来源 |
| `mapping.txt` | `build/outputs/mapping/<variant>/mapping.txt` | 判断 obfuscation 是否生效，支持 crash 还原 |
| `seeds.txt` | `build/outputs/mapping/<variant>/seeds.txt` | 查看被 keep 的类、字段、方法 |
| `usage.txt` | `build/outputs/mapping/<variant>/usage.txt` | 查看被删除的类、字段、方法 |
| APK / AAB size diff | CI artifact | 对照 dex、resources、native 体积变化 |

门禁规则建议按“变宽”定义，避免把低分本身当作失败。可执行的评审条件包括：

- 新增或修改的 keep 规则影响范围进入 impactful rules 前 10。
- shrinking、optimization、obfuscation 任一分数相比主干基线下降超过团队约定阈值。
- `configuration.txt` 出现新的包级 `-keep class xxx.** { *; }` 或全局 `-dontshrink`、`-dontobfuscate`、`-dontoptimize`。
- dex size 增长和 analyzer 分数下降同时出现，且增长集中在同一个业务包或 SDK 包。
- 新版 SDK 带入 consumer rules 后，subsumed rules 数量明显增加。

官方 r8-analyzer skill 还提供了一条 agent 化路径：检查 Gradle 配置和 R8 版本，R8 9.3.7-dev 及以上走定量分析，旧版本走启发式规则审查。它适合做报告摘要和初筛，但不能替代人工判断。keep 规则背后是运行时契约，agent 能指出“这条规则影响大”，最终仍要由工程师确认反射、JNI、序列化和插件化路径是否被覆盖。[已验证: GitHub android/skills r8-analyzer, 2026-05-19]

## 与 APK Analyzer / apkanalyzer 的边界

[已验证: 官方文档, developer.android.com/topic/performance/app-optimization/r8-configuration-analyzer；详见 12.1 节]

体积排查的顺序建议固定下来：APK Analyzer 或 `apkanalyzer` 看结果，R8 Configuration Analyzer 看原因。

APK Analyzer 适合回答：

- `classes.dex`、`resources.arsc`、`res/`、`lib/` 哪一类变大。
- 哪个包、哪个资源目录、哪个 ABI 贡献了主要体积。
- 两个 APK / AAB 构建之间有哪些文件级差异。

R8 Configuration Analyzer 适合回答：

- 哪条 keep 规则阻止了最多类、字段、方法被 shrink、optimize 或 obfuscate。
- App 规则、consumer rules、默认 AGP 规则各自贡献了哪些影响。
- 哪些规则互相覆盖，哪些宽规则可以收窄。
- full mode 迁移后，哪些兜底规则正在吞掉收益。

两者合用时，先用 APK Analyzer 确认 dex 体积异常，再用 analyzer 找规则原因；如果异常在图片、字体、native 库，R8 报告不会提供直接答案，应回到 12.1 和 25.7 节的资源与包结构治理。

## 后续扩展：框架规则模板与 agent 评审

[待补充] 反射与代码生成框架的 keep 规则模板可以单独整理成附录：Gson / Moshi / Jackson 处理字段和泛型签名，Room / Hilt / Retrofit 处理 generated code 和 consumer rules，JNI 处理 downcall 与 upcall，插件化框架处理类名、资源名和动态加载入口。模板必须绑定具体库版本；同一库在新旧版本的 consumer rules 差异很大。

[自动发现] R8 Analyzer 与 AI agent 辅助评审的最佳位置是 CI 报告摘要：自动抓取 top impactful rules、subsumed rules、三类分数变化和新增全局规则，再把候选问题交给人工复核。不要让 agent 自动删除 keep 规则。规则删除后的失败常发生在低频路径，例如三方登录回调、支付 SDK、push receiver、灰度插件、native crash 上报和旧数据反序列化，只有项目回归用例能兜住这些路径。
