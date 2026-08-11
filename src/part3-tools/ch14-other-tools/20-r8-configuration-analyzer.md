---
title: "R8 Configuration Analyzer 与 keep 规则体积归因"
chapter: "14.20"
section: "14.20"
status: ready-for-review
drafted_date: "2026-05-23"
applicable_versions: "Android 17 (API 37)；AGP 9.3.0+ / R8 9.3.7-dev+；旧 AGP 需替换内置 R8 后手动生成报告"
last_verified: "2026-07-30"
last_verified_against: "R8 Configuration Analyzer 文档更新至 2026-07-14；keep rule 文档更新至 2026-06-29；android-17.0.0_r1 / android17-6.18-2026-06_r6"
confidence: high
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
    path: "https://developer.android.com/topic/performance/app-optimization/add-keep-rules"
  - type: official
    path: "https://developer.android.com/topic/performance/app-optimization/choose-libraries-wisely"
  - type: official
    path: "https://developer.android.com/studio/debug/apk-analyzer"
  - type: r8
    path: "https://r8.googlesource.com/r8/+/refs/heads/main/README.md"
  - type: aosp
    path: "https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1/default.xml"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Makefile"
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
related_chapters: ["25.6", "25.7", "14.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-23"
gap_source: "官方文档"
android17_review_notes: "2026-07-30：补齐 AGP 9.3 standalone analyzer task、新 optimization DSL 与 .keep source set；纠正旧 AGP 仍需 R8 9.3.7-dev+、consumer rule 不能靠新增窄规则抵消、报告分数不等于实际体积收益、JNI descriptor class 也需保护等边界。运行验证锚定 Android 17 / API 37 / android-17.0.0_r1；本工具运行在构建主机，不依赖 android17-6.18-2026-06_r6 内核实现。"
---

# 14.20 R8 Configuration Analyzer 与 keep 规则体积归因

## 为什么需要单独看 R8 Configuration Analyzer

APK 体积排查通常从 25.6 节的 APK Analyzer 开始：先看 `classes.dex`、`resources.arsc`、`res/`、`lib/` 哪一块在增长，再判断该动 R8、资源、图片还是 native 库。这个入口能回答“结果变大在哪里”，但回答不了“哪条 keep 规则让 R8 放弃了哪些优化”。

R8 Configuration Analyzer 补的是后一半。它把最终合并后的 R8 配置映射到类、字段和方法，给出 shrinking、optimization、obfuscation 三类分数，并列出影响最大的 keep 规则和被覆盖的规则。体积治理到 keep 规则这一层时，它比肉眼读 `proguard-rules.pro` 更可靠，因为最终生效的规则还包括默认 AGP 规则、App 自定义规则、各个 AAR 传进来的 consumer rules，以及部分工具生成的规则。

Analyzer 的 score 与 rule impact 统计的是哪些类、字段、方法仍允许被处理，不会计算每条规则对应多少 DEX 字节，也不会预测启动耗时变化。独立分析任务甚至不生成 APK 或 AAB。体积归因要把 analyzer 报告与同一次完整构建的 APK Analyzer、mapping 和 benchmark 结果配对。

## Android 17 与构建工具版本边界

R8 和 Configuration Analyzer 运行在构建主机，发布周期独立于 Android 平台。`android-17.0.0_r1` 不包含这个 AGP 分析页面，`android17-6.18-2026-06_r6` 也不参与 keep rule 合并、whole-program analysis 或 score 计算。

Android 17 / API 37 在这里有两个作用：

- R8 以 API 37 的 `android.jar` 作为 platform library 之一，结合项目的 `compileSdk`、`minSdk`、程序类和依赖建立分析图；
- 优化后的 release artifact 要在 Android 17 实机或等价构建上覆盖反射、JNI、序列化、组件启动和动态加载路径。

报告应同时记录 AGP、R8、JDK、Gradle、`compileSdk=37`、`minSdk`、variant、依赖锁和代码提交。只写“已在 Android 17 验证”无法复现 analyzer 结果；升级 R8 后，score 的统计实现也可能变化。

## 三条报告生成路径

Configuration Analyzer 的最低要求是 R8 9.3.7-dev。AGP 9.3.0-alpha05 开始预置满足要求的 R8；当前官方工作流按 AGP 9.3.0 及以上描述。AGP 版本较旧时，系统属性本身不会升级 R8，仍要按 R8 官方说明替换 AGP 内置版本。

AGP 9.3.0 及以上提供独立任务，适合本地迭代 keep rule：

```bash
./gradlew :app:analyzeReleaseR8Config
```

这个任务跳过 APK/AAB 生成，报告写入 `app/build/reports/r8/r8-config-analyzer-release.html`。它能快速比较规则影响，不能同时提供最终包体或运行时验证。

完整 release 构建会自动生成报告：

```bash
./gradlew :app:assembleRelease
```

默认路径是 `app/build/outputs/mapping/release/configanalyzer.html`；模块名和 variant 改变时，路径中的 `app`、`release` 也随之改变。若确有需要，可以用 `android.experimental.r8.enableR8ConfigurationAnalyzer=false` 关闭完整构建的自动报告。

AGP 9.2 及更早版本在替换到 R8 9.3.7-dev 或更新版后，使用下面的系统属性生成 HTML：

```bash
mkdir -p /tmp/r8analysis

./gradlew :app:assembleRelease \
  -Dcom.android.tools.r8.dumpkeepradiushtmltodirectory=/tmp/r8analysis
```

`dumpkeepradiushtmltodirectory` 是 R8 系统属性，不是 AGP 9.3 standalone task 的替代名称。CI 使用前应固定 R8 override 来源和校验值，避免把 `-dev` artifact 静默换成另一次构建。

### AGP 9.3 的 optimization DSL

AGP 9.3 及以上用 `optimization.enable` 同时开启代码和资源优化，App keep rules 放在 `src/<variant>/keepRules/` 下且文件名以 `.keep` 结尾。下面的 Kotlin DSL 用于 release variant：

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

例如公共规则可以放在 `src/main/keepRules/app.keep`。AGP 9.3 默认规则等价于 `proguard-android-optimize.txt`。旧版 AGP 继续使用 `isMinifyEnabled=true`、`isShrinkResources=true` 和 `proguardFiles(...)`；不要把两套 DSL 拼在同一个示例里。

## 报告里哪些字段该看

报告首页的三类分数衡量“仍允许 R8 处理的代码占比”，不能当作已经获得的优化收益，也不能跨 R8 版本直接设绝对排名。

| 指标 | 它衡量什么 | 分数下降时先看哪里 |
| --- | --- | --- |
| Shrinking score | 类、字段、方法中仍允许被删除的比例 | 包级 keep、`-dontshrink`、过宽的 `-keep class ** { *; }` |
| Optimization score | 仍允许被内联、类合并、访问级别调整等优化处理的比例 | `-dontoptimize`、未加 `allowoptimization` 的宽规则、full mode 兼容性兜底规则 |
| Obfuscation score | 仍允许被重命名的比例 | `-dontobfuscate`、协议字段名和反射类名被整包固定 |

这三个分数要结合规则列表读。一个项目的 shrinking score 下降，原因可能是 App 侧新增一条宽规则，也可能是三方 SDK 的 consumer rules 在新版本里扩大了范围。报告里的 source 字段用于判断规则来源：App 规则能直接改；library consumer rules 应优先通过升级 SDK 或反馈库作者处理；默认 AGP 规则只做识别，不应改动。

Keep rule 是加法配置。App 再添加一条更窄的规则，无法抵消 AAR 已经带入的宽 consumer rule。必须临时验证潜在收益时，AGP 8.4 及以上可通过 `optimization.keepRules.ignoreFrom("group:artifact")` 过滤指定依赖的规则，再把该依赖运行时所需的规则放回项目。这个动作会改变库作者声明的运行时契约，只适合隔离实验和有完整回归覆盖的受控构建。

`impactful rules` 适合排优先级。它把 keep 规则影响到的类、字段、方法数量聚合起来，能快速暴露“写一条顶十条”的规则。排查时先看影响范围最大的规则，再看它是否真的对应运行时入口。

`subsumed rules` 用于清理技术债。典型例子是同一个包里同时存在这两条规则：

```proguard
# 规则 A：保留整个包
-keep class com.example.package.** { *; }

# 规则 B：保留包内一个类
-keep class com.example.package.MyClass
```

规则 A 已经覆盖了规则 B，报告会把这种重叠关系暴露出来。处理时先确认 A 是否过宽：如果只有 `MyClass` 需要保留，应收窄 A；如果整包都要保留，再考虑 B 是否冗余。

报告还会列出两类配置噪声：

- unused rule：当前构建没有匹配任何类、字段或方法；删除前要确认它是否用于其它 flavor、动态 feature 或可选依赖；
- identical rule：同一文件或多个配置来源中存在相同声明；移除副本不会改变当前匹配集合，但仍应通过完整构建确认。

unused、identical 和 subsumed 都描述当前 variant 的配置关系。它们不是跨所有构建变体的删除清单。

## keep 规则的代价分级

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

# native 层按固定签名回调 Java/Kotlin 时，保留成员及描述符类型。
-keepclassmembers,includedescriptorclasses class com.example.bridge.NativeBridge {
    public void onNativeEvent(com.example.bridge.NativePayload);
}
```

第一条来自默认优化规则的 JNI downcall 保护；第二条面向 native 层 upcall，`includedescriptorclasses` 同时保护方法参数和返回值中的应用类型。若 native 代码还按名字访问 `NativePayload` 的构造函数或字段，这些成员需要单独规则。二者都比 `-keep class com.example.bridge.** { *; }` 窄。

## 高风险规则的排查顺序

规则排查不要从“删规则”开始。更稳的顺序是：先根据 APK Analyzer 或 dex size diff 找增长包，再用 Configuration Analyzer 找规则影响范围，随后回到代码确认运行时入口。

1. **包级兜底规则**：优先处理 `-keep class ** { *; }`、`-keep class com.company.** { *; }`、`-keep class * { *; }`。这类规则会同时压低三类分数，常见来源是迁移 R8 full mode 时的临时兜底。
2. **反射框架规则**：Gson、Moshi、Jackson、反射式路由、插件化框架要区分“依赖类名”“依赖字段名”“依赖泛型签名”三种契约。只读字段名就保字段；读泛型就保 `Signature` 和相关类型；不要把整包模型全量固定。
3. **代码生成与自带规则的库**：Room、Hilt、Moshi codegen 通过注解处理器或 KSP 让 R8 看见静态引用；Gson 2.11.0+、Retrofit 2.10.0+ 自带关键 consumer rules。App 侧新增大范围兜底前，先看库版本、AAR 内容和最终 `configuration.txt`。
4. **JNI 入口**：Java/Kotlin 调 native 的 `native <methods>` 通常由默认优化规则覆盖；native 回调 Java/Kotlin 的 upcall 才需要项目补规则。规则要精确到 bridge 类或方法签名。
5. **ServiceLoader 和可选依赖**：`META-INF/services/` 或字符串类名加载路径要保留 provider 类和无参构造函数；如果传入的是 `Class` 对象，通常不需要保留原始类名。
6. **注解和泛型签名**：R8 full mode 下，attribute 是否保留与被 keep 的类、字段、方法有关。只写 `-keepattributes` 可能不够，必须确认读取 attribute 的对象也被规则匹配。

排查时同步查看 `build/outputs/mapping/<variant>/configuration.txt`、`mapping.txt`、`seeds.txt`、`usage.txt`。`configuration.txt` 说明最终规则从哪里来；`seeds.txt` 说明哪些元素被规则保留；`usage.txt` 说明哪些元素被删除；`mapping.txt` 说明哪些名字发生了变化。四个文件和 analyzer 报告放在一起，才能判断“规则变窄后是否真的产生收益”。

## 与 R8 full mode 迁移的配合

R8 full mode 从 AGP 8.0 起默认启用。它会做更积极的类合并、方法内联、属性裁剪和访问级别调整。迁移失败时，常见补救动作是往 `proguard-rules.pro` 里加宽规则，甚至在 `gradle.properties` 里保留 `android.enableR8.fullMode=false`。这能让崩溃暂时消失，但会把优化空间长期锁死。

Configuration Analyzer 适合放在 full mode 迁移后的第二轮：第一轮先让 release 包稳定跑完 smoke test，第二轮再看哪些兜底规则影响最大。报告里影响最大的规则，往往就是迁移期间为了“先过”加进去的规则。处理方式是把运行时契约拆成可验证的单元：

- Gson `TypeToken` 依赖 `Signature`，规则要保留泛型签名和相关 `TypeToken` 类型；Gson 2.11.0+ 已带 full mode 所需 consumer rules，旧版本才考虑 App 侧补规则。
- 反射构造只需要无参构造函数时，保构造函数，不要保整个类的所有字段和方法。
- 注解扫描只需要运行时注解时，保 `RuntimeVisibleAnnotations` 和被扫描成员，不要把包内所有类都固定。
- native upcall 只需要固定被 native 查找的方法签名时，保 bridge 方法，不要禁用整包混淆和优化。

如果必须临时关闭 full mode，要把它当作定位开关，并给回滚设截止时间。长期方案是用 analyzer 找出压低分数的兜底规则，再用 release 回归覆盖序列化、登录、支付、推送、深链、插件加载和 JNI 路径。

## CI 与回归治理

R8 Configuration Analyzer 更适合做“趋势门禁”，不适合把某个绝对分数当全项目通用红线。不同 App 的反射、动态化和 SDK 结构差异很大，同样 80% 的 optimization score，在一个纯 Compose App 和一个插件化 App 里含义不同。

基线与候选构建必须使用相同的 AGP、R8、JDK、Gradle、variant、依赖图和 analyzer 生成路径。升级编译器时先建立新基线，不把 score 变化直接归因到业务 keep rule。

CI 里至少归档这些产物：

| 产物 | 建议路径 | 用途 |
| --- | --- | --- |
| analyzer HTML | `build/reports/r8/r8-config-analyzer-<variant>.html`、`build/outputs/mapping/<variant>/configanalyzer.html` 或手动输出目录 | 查看三类分数及 impactful、subsumed、unused、identical rules |
| `configuration.txt` | `build/outputs/mapping/<variant>/configuration.txt` | 追踪最终合并后的规则来源 |
| `mapping.txt` | `build/outputs/mapping/<variant>/mapping.txt` | 判断 obfuscation 是否生效，支持 crash 还原 |
| `seeds.txt` | `build/outputs/mapping/<variant>/seeds.txt` | 查看被 keep 的类、字段、方法 |
| `usage.txt` | `build/outputs/mapping/<variant>/usage.txt` | 查看被删除的类、字段、方法 |
| APK / AAB size diff | CI artifact | 对照 dex、resources、native 体积变化 |

standalone analyzer task 不生成 APK、AAB、mapping、seeds 或 usage；表中的编译产物来自完整 R8 build，并且必须和被比较的 APK/AAB 属于同一次构建。mapping 会被后续构建覆盖，发布时应按 artifact 校验值归档。

官方公开产物是 HTML，没有承诺稳定的 CI JSON schema。若团队从 HTML 或内部 analyzer 数据提取 score，应固定 R8 版本，为解析器加契约测试，并在格式变化时让门禁失败并提示人工检查。

门禁规则建议按“变宽”定义，避免把低分本身当作失败。可执行的评审条件包括：

- 新增或修改的 keep 规则进入团队基线定义的高影响集合。
- shrinking、optimization、obfuscation 任一分数相比主干基线下降超过团队约定阈值。
- `configuration.txt` 出现新的包级 `-keep class xxx.** { *; }` 或全局 `-dontshrink`、`-dontobfuscate`、`-dontoptimize`。
- dex size 增长和 analyzer 分数下降同时出现，且增长集中在同一个业务包或 SDK 包。
- 新版 SDK 带入 consumer rules 后，subsumed rules 数量明显增加。

官方 r8-analyzer skill 还提供了一条 agent 化路径：检查 Gradle 配置和 R8 版本，R8 9.3.7-dev 及以上走定量分析，旧版本走启发式规则审查。它适合做报告摘要和初筛，但不能替代人工判断。keep 规则背后是运行时契约，agent 能指出“这条规则影响大”，最终仍要由工程师确认反射、JNI、序列化和插件化路径是否被覆盖。

## 与 APK Analyzer / apkanalyzer 的边界

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

两者合用时，先用 APK Analyzer 确认 dex 体积异常，再用 analyzer 找规则原因；如果异常在图片、字体、native 库，R8 报告不会提供直接答案，应回到 25.6 和 25.7 节的资源与包结构治理。

## 框架规则评审表

通用“框架 keep 模板”很容易随库升级失效。评审时先识别运行时契约，再选择规则：

| 运行时契约 | 需要保护的内容 | 可以尝试放开的能力 | 验证重点 |
| --- | --- | --- | --- |
| `Class.forName()` 使用固定字符串 | 类名、类本身、被反射构造的构造函数 | 只在字符串随 mapping 改写时考虑 obfuscation | 动态注册、插件入口、可选实现 |
| 代码直接传递 `Class` 对象 | 被反射调用的构造函数或成员 | `allowobfuscation`；未使用实现可 `allowshrinking` | 每个实现类与低频分支 |
| 按字段名序列化 | 对应字段名和字段 | 未被协议读取的成员仍可 shrink/optimize | 旧数据、缺省值、混淆后协议兼容 |
| 读取泛型或注解 | `Signature`、运行时注解及其关联类/成员 | 不依赖名字的对象可 obfuscate | 泛型返回值、匿名 `TypeToken`、suspend 接口 |
| Room、Hilt、Moshi codegen | 生成代码和静态引用 | 通常不需要 App 侧整包 keep | 生成器版本、增量构建、consumer rules |
| JNI upcall | 被回调成员、descriptor 中的应用类型、native 按名访问的成员 | 只放开 native 不依赖的名称和成员 | ABI、注册方式、构造函数、回调签名 |

Gson 2.11.0+ 与 Retrofit 2.10.0+ 已携带关键 consumer rules。官方示例用于解释语法，不应无条件复制到项目。先检查依赖版本和 AAR 中的规则，再补 App 特有的 model 或接口契约。

## Agent 评审的安全边界

R8 Analyzer skill 可以汇总 score、影响较大的规则和重叠关系，也可以标出全局 `-dont*` 选项。它适合生成候选清单，不能自动删除 keep rule。建议把 agent 工作限制为以下步骤：

1. 读取 Gradle、AGP、R8、variant 和依赖锁；
2. 生成或读取 analyzer 报告，不修改规则；
3. 把候选规则映射到 source file、依赖坐标和受影响元素；
4. 提出更窄规则与必须覆盖的运行时路径；
5. 由工程师批准变更并运行 release 构建、功能回归、体积对比和性能测试；
6. 把失败样本、mapping 和最终规则归档。

三方登录回调、支付、push receiver、动态 feature、JNI crash 上报和旧数据反序列化通常不在日常 smoke test 中。没有这些路径的用例时，保持规则并记录证据缺口。

## 参考资料

- [R8 Configuration Analyzer](https://developer.android.com/topic/performance/app-optimization/r8-configuration-analyzer)
- [Enable app optimization with R8](https://developer.android.com/topic/performance/app-optimization/enable-app-optimization)
- [Use R8 in full mode](https://developer.android.com/topic/performance/app-optimization/full-mode)
- [Add keep rules](https://developer.android.com/topic/performance/app-optimization/add-keep-rules)
- [Keep rule use cases and examples](https://developer.android.com/topic/performance/app-optimization/keep-rule-examples)
- [Choose libraries wisely](https://developer.android.com/topic/performance/app-optimization/choose-libraries-wisely)
- [Analyze a build with APK Analyzer](https://developer.android.com/studio/debug/apk-analyzer)
- [R8 source and AGP replacement instructions](https://r8.googlesource.com/r8/+/refs/heads/main/README.md)
- [Android 17 platform manifest](https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1/default.xml)
- [Android 17 common kernel 6.18 Makefile](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Makefile)
