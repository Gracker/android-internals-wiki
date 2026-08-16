---
title: "ART 编译管线与 dex2oat 优化"
chapter: "1.7"
section: "1.7"
status: finalized
pipeline_stage: finalized
applicable_versions: "Android 7.0 (API 24) - Android 17 (API 37)"
confidence: high
tags:
  - art
  - dex2oat
  - jit
  - aot
  - baseline-profile
  - startup-profile
  - cloud-profile
  - compiler-filter
  - cold-start
sources:
  - type: official
    path: "https://source.android.com/docs/core/runtime"
  - type: official
    path: "https://source.android.com/docs/core/runtime/configure"
  - type: official
    path: "https://source.android.com/docs/core/runtime/configure/art-service"
  - type: official
    path: "https://source.android.com/docs/core/runtime/jit-compiler"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/overview"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile"
  - type: official
    path: "https://developer.android.com/topic/performance/startupprofiles/overview"
  - type: official
    path: "https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations"
  - type: aosp
    path: "art/libartbase/base/compiler_filter.h @ android-17.0.0_r1"
  - type: aosp
    path: "art/dex2oat/dex2oat.cc @ android-17.0.0_r1"
  - type: aosp
    path: "art/compiler/optimizing/optimizing_compiler.cc @ android-17.0.0_r1"
  - type: aosp
    path: "art/runtime/jit/jit.cc @ android-17.0.0_r1"
  - type: aosp
    path: "art/runtime/jit/jit_options.cc @ android-17.0.0_r1"
  - type: aosp
    path: "art/runtime/jit/jit_code_cache.h @ android-17.0.0_r1"
  - type: aosp
    path: "art/runtime/jit/jit_code_cache.cc @ android-17.0.0_r1"
  - type: aosp
    path: "art/runtime/jit/profile_saver.cc @ android-17.0.0_r1"
  - type: aosp
    path: "art/libprofile/profile/profile_compilation_info.h @ android-17.0.0_r1"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/ArtShellCommand.java @ android-17.0.0_r1"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/ArtManagerLocal.java @ android-17.0.0_r1"
  - type: aosp
    path: "art/DISASSEMBLY_GUIDE.md @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/jni/AndroidRuntime.cpp @ android-17.0.0_r1"
last_verified: "2026-08-07"
last_verified_against: "AOSP android-17.0.0_r1; Android Developers; source.android.com; 2026-08-07 body-apply freshness pass"
related_chapters:
  - "1.6"
  - "1.12"
  - "4.3"
  - "8.2"
  - "8.3"
  - "16.1"
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_body_apply_at: "2026-08-07T07:15:26+08:00"
last_body_apply_run_id: "20260807-071512-04a03874"
last_deep_review_at: "2026-08-07T08:36:48+08:00"
last_deep_review_run_id: "20260807-083648-deep-review-962ac2dc"
last_review_finalize_at: "2026-08-07T10:08:18+08:00"
last_review_finalize_run_id: "20260807-100535-f89828e4"
---

# 1.7 ART 编译管线与 dex2oat 优化

一个方法在 Android 上运行时，不一定只有一种执行形态。Android 运行时（Android Runtime，ART）可以解释 Dalvik 可执行格式（DEX）字节码、在运行期用即时编译（JIT）处理热点代码，也可以加载 `dex2oat` 预先生成的提前编译（AOT）代码。

分析启动性能时，不要笼统比较“AOT 还是 JIT 更快”，应依次确认：

1. 启动路径上的方法当前有没有可用的 AOT 代码？
2. 没有 AOT 代码时，是解释执行，还是已经被 JIT 编译？
3. AOT 产物为什么不存在、失效，或者没有覆盖这条路径？
4. 为了得到更多机器码，安装时间、存储和后台编译成本增加了多少？

诊断时，先看 `pm art dump` 和决定 AOT 编译范围的编译过滤器（compiler filter），再确认记录常用方法与类的代码使用画像（Profile）是否参与 AOT，然后用系统性能跟踪工具 Perfetto 或启动性能测试工具 Macrobenchmark，量化解释执行、JIT 与 `dex2oat` 的成本。仅凭 ODEX 文件存在、单条 JIT 时间片段（slice）或 Profile 文件打包成功，都不足以证明启动性能已经优化。

## 从 DEX 到执行代码

应用构建后携带 DEX 字节码。安装、系统构建或后台维护期间，dex2oat 可以产生 ART 编译产物。文件名和位置会随版本与安装方式变化，常见职责是：

- `.odex`/`.oat`：保存 AOT 编译的机器码和相关元数据；
- `.vdex`：保存验证依赖等信息，某些情况下也包含未压缩 DEX；
- `.art`：可选的应用映像（app image），保存 ART 内部的类和对象表示。

这些产物不是 APK 的永久附属物。DEX 校验和、启动映像（boot image）、描述类加载时可见代码及依赖的类加载器上下文（class loader context）、指令集或 ART 版本不匹配时，旧产物可能被判定为不可用，随后改用解释执行或 JIT，也可能重新进行 DEX 优化（dexopt）。

```text
DEX
 ├─ verification
 ├─ interpreter ────────────────────┐
 ├─ JIT compile -> code cache  ├─> 执行
 └─ dex2oat -> OAT/ODEX/VDEX ──┘
                ^
                └─ Baseline / Cloud / local profile
```

一个 `.odex` 文件存在，也不代表每个方法都有机器码。编译范围由编译过滤器和代码使用画像决定。

## 编译策略为什么经历多次反转

| 版本 | 主要策略 | 代价落点 |
|---|---|---|
| Android 4.4 | ART 作为可选运行时，尝试安装期 AOT | 安装和存储成本增加 |
| Android 5.0-6.0 | ART 成为平台运行时，以较完整的 AOT 为主 | 更新、首次开机和安装期编译较重 |
| Android 7.0+ | 解释器 + JIT + 画像引导 AOT | 运行时热身和后台编译换取更小产物 |
| Android 9+ | Google Play 可在安装时交付基准或云端画像 | 安装时就能按真实或预设热点做部分 AOT |
| Android 12+ | ART 成为可独立更新的 Mainline 模块 | 运行时和编译器行为可随模块更新变化 |
| Android 14+ | ART Service 管理应用在设备上执行的 DEX 优化 | 编译原因、优先级和产物管理集中到 ART 模块 |
| Android 17 | 延续混合执行与 ART Service 架构 | 仍应以代码使用画像、编译过滤器和设备状态解释结果 |

Android 17 没有把应用统一切到“云端机器码”或“全量 AOT”。云端画像（Cloud Profile）分发的是代码使用画像，设备仍按本机指令集、运行时和依赖生成编译产物。

## 编译过滤器决定 AOT 范围

Android 17 的 `art/libartbase/base/compiler_filter.h` 定义了当前编译过滤器集合：

```cpp
// @ android-17.0.0_r1，节选
enum Filter {
  kAssumeVerified,
  kVerify,
  kSpaceProfile,
  kSpace,
  kSpeedProfile,
  kSpeed,
  kEverythingProfile,
  kEverything,
};
```

应用诊断最常遇到三种：

| 过滤器 | 行为 | 适合怎样理解 |
|---|---|---|
| `verify` | 验证 DEX，不为应用方法生成 AOT 机器码 | 运行主要依赖解释器与 JIT |
| `speed-profile` | AOT 编译代码使用画像中的方法，并优化画像中类的加载 | 在启动、交互性能、存储和编译时间之间取平衡 |
| `speed` | 尽可能 AOT 编译应用方法 | 运行期热身少，但编译时间和产物更大 |

`space*` 与 `everything*` 也存在于当前源码，但主要面向系统和产品配置。不能只按名称把过滤器排成简单的“越靠后越快”：代码使用画像的质量、代码布局、存储 I/O、类加载和实际执行路径都会影响结果。

Android 14 及以上版本的 ART Service 会按不同的 DEX 优化原因（dexopt reason）配置过滤器。AOSP 的标准默认值包括：

```properties
pm.dexopt.first-boot=verify
pm.dexopt.boot-after-ota=verify
pm.dexopt.boot-after-mainline-update=verify
pm.dexopt.bg-dexopt=speed-profile
pm.dexopt.inactive=verify
pm.dexopt.cmdline=verify
```

设备厂商（OEM）可以调整这些属性，ART Service 也会根据代码使用画像、共享代码、存储压力和编译原因选择或降低过滤器级别。因此，“Android 17 安装后一定是 `speed-profile`”不是可靠结论。

## dex2oat 做了什么

`dex2oat` 是 ART 在设备上运行的 AOT 编译器入口。对于过滤器选中的方法，主要流程可以概括为：

1. 打开 DEX、启动映像和类加载器上下文；
2. 验证字节码及类型约束；
3. 为需要编译的方法构建中间表示；
4. 运行内联、常量传播、死代码消除、循环和寄存器分配等优化；
5. 针对目标指令集架构（ISA）生成机器码，以及垃圾回收、异常和去优化（deopt）所需的元数据；
6. 写出 OAT/ODEX、VDEX 和可选应用映像。

源码里的 `HGraph` 是优化编译器使用的静态单赋值（Static Single Assignment，SSA）形式中间表示；每个变量只在一个位置赋值，便于追踪值的定义与使用。但“用了 SSA”不等于每项优化都必然发生。方法大小、异常控制流、类加载假设、代码使用画像和编译资源预算都会限制优化。

### AOT 产物为什么会失效

编译代码既依赖 APK 本身，也依赖：

- DEX 校验和与拆分包集合；
- 启动类路径（boot class path）与启动映像；
- 类加载器上下文和 `<uses-library>` 顺序；
- ART/APEX 与编译产物格式；
- 目标指令集架构、运行时特性和编译选项。

ART 会校验这些依赖。强行复制另一台设备或另一版本的 `.odex`，即使文件名相同，也不能保证可加载。因此，Play 无法直接下发适用于所有设备的通用 ODEX。

### ART Service 与编译并发

Android 14 起，应用在设备上的 DEX 优化由 ART Service 负责。`pm.dexopt.<reason>.concurrency` 控制可并发的 `dex2oat` 进程数，`dalvik.vm.*dex2oat-threads` 控制单个 `dex2oat` 的线程数。两者共同决定并行规模。

提高并发可能缩短批处理总时间，也可能增加峰值内存、上下文切换、温升和与前台任务争用资源的时间。产品调优必须在目标设备上测首次启动、OTA、后台维护和交互延迟，不能只看 DEX 优化完成时间。

## JIT：用运行时热度换取机器码

当方法没有可用 AOT 代码时，ART 可以先解释执行并记录执行热度。方法调用、循环跳回起点的次数和线程权重等信息会增加热度计数；达到相应阈值后，ART 把编译任务交给 JIT。

Android 17 的 JIT 源码具有快速（`fast`）、基线（`baseline`）、优化（`optimized`）与栈上替换（OSR）等编译路径。具体启用哪些层级、阈值是多少，受运行时选项和产品属性影响。`dalvik.vm.jitthreshold` 等属性由 `AndroidRuntime.cpp` 转换为 ART 参数，但第三方应用不应依赖或尝试修改这些系统属性。

JIT 的典型过程是：

```text
解释执行
  -> 累积 hotness / 类型反馈
  -> JIT 编译任务
  -> 写入进程内 JIT code cache
  -> 更新方法入口
  -> 后续调用执行机器码
```

栈上替换（On-Stack Replacement，OSR）允许长循环在方法尚未返回时切换到编译后的代码。JIT 也能利用运行时类型反馈，把虚方法调用改为更直接的调用（去虚化）并执行方法内联，但编译本身会消耗 CPU 和内存。

### JIT 代码缓存的数字要注明层级

Android 17 固定标签中的源码默认值是：

```cpp
// art/runtime/jit/jit_code_cache.h
// @ android-17.0.0_r1，节选
static constexpr size_t kMaxCapacity = 64 * MB;

static size_t GetInitialCapacity() {
  const size_t page_size = GetPageSizeSlow();
  return std::max(kIsDebugBuild ? 8 * KB : 64 * KB, 2 * page_size);
}
```

这段代码给出默认初始容量和上限，不表示每个应用一启动就占用 64 MB：

- 初始容量在 16 KB 内存页系统上至少是两个页面；
- `dalvik.vm.jitinitialsize` 和 `dalvik.vm.jitmaxsize` 可以覆盖默认值；
- 容量上限、虚拟地址空间、常驻集大小（RSS）和按共享页比例分摊的内存（PSS）不是同一个指标；
- 进程中的真实机器码、用于描述栈内容的栈映射（stack map）与性能剖析数据会随工作负载增长。

空间压力下，`JitCodeCache::DoCollection(Thread*)` 扫描活动栈和代码缓存状态，保留仍然需要的代码并回收可移除项。调试信息、Java 虚拟机工具接口（JVMTI）、首次使用即编译（JIT-at-first-use）等模式会影响是否允许回收。不能把它简化成固定的最近最少使用（LRU）策略，也没有依据说大型应用“通常稳定在 4 MB”。

### 去优化用于撤销不再成立的投机优化

JIT/AOT 可能根据当前类层次、记录调用点常见目标的内联缓存（inline cache）或只有一种实现的方法做优化。如果后来加载的新类型、类重定义、调试器或插桩工具（instrumentation）破坏这些假设，ART 必须丢弃代码、改用不依赖该假设的执行入口，或去优化栈帧。

看到去优化（deoptimization）活动时，需要确认原因和 CPU 时间。一次去优化可能只是正常的类加载边界；持续反复的失效和重编译才更值得检查动态代理、热修复、JVMTI 或插件化行为。

## 四类代码使用画像不要混在一起

### 本地 JIT 画像

ART 在应用运行时收集热点方法、类和部分调用点类型信息，由 `ProfileSaver` 持久化。常见内部路径形如：

```text
/data/misc/profiles/cur/<user>/<package>/primary.prof
/data/misc/profiles/ref/<package>/primary.prof
```

这些是系统内部目录，普通应用和普通命令行用户（shell）不一定有直接读取权限，路径和布局也不属于公开 SDK 保证稳定的内容。诊断时优先使用 ART Service 或 Package Manager 提供的 shell 命令。

本地画像只反映这台设备、这个用户实际执行过的路径。后台 DEX 优化可以把它与外部画像合并，用于下一轮 `speed-profile` 编译。

### 基准画像（Baseline Profile）

基准画像由开发者为启动和关键使用流程生成。开发者可读的规则在构建时被转换为二进制画像，常见打包位置是 `assets/dexopt/baseline.prof`。

通过 Google Play 安装时，Play 可以处理画像，并随 APK 或 DEX 元数据（DM）文件交付，让 ART 在安装期 AOT 编译标记的方法。非 Play 分发或较老平台可以依赖 `ProfileInstaller` 把内置画像放到 ART 可读取的位置，随后由 DEX 优化使用。

基准画像是“应该优先编译哪些代码”的提示，不是机器码。它也不会缩短画像之外的业务逻辑。

### 云端画像（Cloud Profile）

云端画像由 Google Play 根据历史用户实际执行过的路径汇总，并用于之后的安装或更新。它支持 Android 9/API 28 及以上，需要足够的用户样本，而且新版本发布后可能要经过数小时到数天才能覆盖。

基准画像用于改善新版本和小样本阶段的冷启动；云端画像补充真实用户覆盖。两者可以共同影响安装时编译，但都不会把某台设备生成的 `.odex` 直接复制给另一台设备。

### 启动画像（Startup Profile）

启动画像是构建期输入，由 R8 用来调整 DEX 布局，让启动关键类和方法尽量集中在首个 DEX 和更连续的位置。它不参与设备上的编译过滤器选择，也不会作为一份独立的运行时画像留在 APK 中。

```text
Baseline Profile -> ART on-device AOT 范围
Startup Profile  -> R8/D8 构建期 DEX 布局
```

启动画像只能由应用的启动场景生成，库不能单独提供最终启动画像。启动代码超出主 DEX 容量时，布局收益会受限；需要用 APK Analyzer 或构建产物中的 R8 元数据验证，不能只检查 `startup-prof.txt` 是否存在。

## 应用侧怎样生成和验证画像

基准画像生成器（Baseline Profile Generator）应覆盖真实、稳定且对用户重要的路径：

```kotlin
@RunWith(AndroidJUnit4::class)
@LargeTest
class BaselineProfileGenerator {
    @get:Rule
    val rule = BaselineProfileRule()

    @Test
    fun generate() = rule.collect(
        packageName = "com.example.app",
        includeInStartupProfile = true,
    ) {
        pressHome()
        startActivityAndWait()
        // 再执行首页首帧所需的稳定交互。
    }
}
```

生成画像后还需要验证：

1. 用发布版（release）代码、R8 和与线上一致的拆分包（split）构建；
2. 确认 APK/AAB 内有 ART 可读取的基准画像；
3. 确认启动画像已经改变 DEX 布局；
4. 用 Macrobenchmark 对比无预编译与基准画像模式；
5. 分别统计启动、关键交互、安装耗时和包/产物体积。

画像不应无限扩张。覆盖所有代码会增加安装期编译和存储成本，还会削弱“关键路径”的区分作用。每次大规模重构、混淆规则或入口变化后，应重新生成并检查覆盖范围。

## 用命令确认设备的编译状态

Android 14 及以上版本可以通过 ART Service 查看应用包的 DEX 优化状态：

```bash
adb shell pm art dump com.example.app
```

`android-17.0.0_r1` 的 `ArtShellCommand` 会把这个子命令转到 `ArtManagerLocal.dumpPackage()`。输出中关注：

- DEX 容器与拆分包；
- 编译过滤器；
- 编译原因；
- 主/次 DEX（primary/secondary dex）的产物状态；
- 代码使用画像与编译产物是否匹配。

较老版本常用 `dumpsys package dexopt`，字段与新 ART Service 不同。诊断脚本需要按平台分支解析。

### 用强制编译做对照实验

下面的命令会改变设备上的编译状态，只适合测试机：

```bash
# 不生成 AOT 应用机器码
adb shell pm compile -f -m verify com.example.app

# 使用现有 Profile 编译
adb shell pm compile -f -m speed-profile com.example.app

# 尽可能完整 AOT 编译
adb shell pm compile -f -m speed com.example.app

# 恢复为类似新安装后的编译状态
adb shell pm compile --reset com.example.app
```

`speed-profile` 没有可用画像时，结果会受 ART Service 策略影响。每次实验都要重新导出状态，不能只凭命令退出码判断最终编译过滤器。

### `oatdump`、画像导出与权限边界

`oatdump` 适合检查与构建匹配的 OAT/ODEX/VDEX，`pm dump-profiles --dump-classes-and-methods <package>` 可以让 ART Service 导出文本画像。它们属于平台或设备调试工具：

- 面向最终用户的构建（user build）可能没有所需二进制或权限；
- `/data/app` 路径含随机段，不能硬编码；
- 二进制画像只保存 DEX 索引，解析时还需要匹配 APK；
- 来自另一构建版本的 `oatdump` 可能不理解当前产物格式。

应用团队更适合先用 `pm art dump`、Macrobenchmark 和 APK/AAB 检查；只有调试平台本身时再读取内部产物。

## 在 Perfetto 中怎样识别编译成本

录制 Perfetto 数据时，可以启用系统跟踪标记机制 atrace 的 `dalvik` 类别，再配合调度、CPU 频率和必要的调用栈数据。不要依赖旧跟踪数据里的固定时间片段名称：Android 17 ART 大量使用 `ScopedTrace(__FUNCTION__)` 或 `__PRETTY_FUNCTION__`，名称会随实现和构建变化。

可靠的观察点包括：

- 应用进程中 JIT 编译器线程占用 CPU 的时间；
- `art::jit`、`JitCodeCache::DoCollection`、`ProfileSaver` 等调用栈或时间片段；
- 独立的 `dex2oat` 进程或 ART 守护进程 `artd` 的活动，以及它们造成的 CPU、I/O 和内存压力；
- 主线程同一时段是在运行（Running）、等待 CPU（Runnable），还是等待锁或 I/O；
- 安装后首次启动与画像编译后相同路径的对比。

启动期出现 JIT 只能说明有方法进入运行时编译路径，不能单独证明基准画像失效。还要确认这是否发生在非关键线程、编译占用了多少 CPU、目标方法是否属于画像，以及启动是否受它影响。

## 常见误区

### “存在 ODEX 就说明应用已经全量编译”

ODEX 可以只包含部分方法的机器码，编译过滤器甚至可能只做验证。应以 `pm art dump` 和 OAT 文件头为准。

### “基准画像会加速所有代码”

它只引导命中的方法和类。未覆盖路径仍可能解释执行或 JIT，业务自身的 I/O、锁和算法成本也不会消失。

### “JIT 代码缓存上限就是进程实际内存”

上限只是容量配置。实际映射、已经提交的内存页、RSS/PSS 和有效机器码大小需要分别测量。

### “云端画像就是云端编译”

云端画像是汇总后的编译提示，设备用它指导本地 `dex2oat`。它不是跨设备复用的机器码包。

### “把应用强制编成 `speed`，启动变快就应该上线这个设置”

`pm compile` 是设备调试命令，应用无法把它作为发布策略。线上应使用基准画像、启动画像、代码瘦身和合理的关键路径。

### “Mainline 更新后所有应用一定全部重编译”

是否失效取决于启动类路径、ART 版本、产物校验和依赖。应观察具体 DEX 优化原因和编译产物状态，不能从“发生过更新”直接推导全量重编译。

ART 性能优化需要可重复验证：确认当前编译过滤器与代码使用画像，测出解释执行、JIT 和 AOT 的实际成本，再修改画像或代码，并用相同发布构建的应用包和相同设备复测。只看版本号、文件扩展名或一条 JIT 时间片段，都不足以解释启动性能。
