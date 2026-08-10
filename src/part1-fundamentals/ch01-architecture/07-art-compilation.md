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
drafted_date: "2026-04-05"
drafted_by: "openclaw-task2a"
polish_count: 2
polish_date: "2026-04-17"
polish_by: "task2b-polish"
reviewed_date: "2026-08-07"
reviewed_by: "hermes-aiw-review-finalize-apply"
task6_result: pass-light-edit
task2b_result: fixed
task6_state: reviewed
review_round: 6
repaired_date: "2026-04-25"
repaired_by: "openclaw-task2b"
review_notes: "2026-05-03 task9 deep-review: needs-rework。P0 1 / P1 1 / P2 1；P0/P1 写入 queue.json，P2 写入 suggestions.md。"
last_task6_at: "2026-06-20T08:08:00+08:00"
last_task6_review_log: "logs/review/2026-06-20-08-review.md"
task6_review_notes: "2026-06-20 08:08 Task6 revisiting review: pass-light-edit。L1 禁用词 0 命中，L2 可读性通过；Task9 idle-audit auto-fixed（JitCodeCache DoCollection + 404 链接修正）后正文未回退；task6+task9 双通过且 queue 无 pending，自动晋升 finalized。"
task9_result: pass-tech-review
task9_state: reviewed
last_task2b_at: "2026-05-26T03:19:12+08:00"
task2b_state: fixed
task9_reviewed_date: "2026-06-20"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-20T05:27:05+08:00"
task9_review_notes: "2026-05-26 Task9 deep-review 04:30: pass-tech-review。P0 0 / P1 0 / P2 1；JIT code cache 4MB 工程值仍需补实测出处；Task6 已通过且 queue 无 pending，自动晋升 finalized。 2026-06-20 Task9 idle-audit auto-fixed: JitCodeCache 回收入口按 android-15/16/17 修正为 DoCollection(Thread*)，保留 android-14 旧名边界；修正两个 404 source.android 官方链接；回到 Task6 复审。"
last_task6_audit: "2026-07-13"
last_task6_audit_log: "logs/review/2026-07-13-11-audit.md"
last_task6_audit_notes: "L1/L2 格式规范修复完成，保持 finalized 状态"
last_task9_review_log: "logs/deep-review/2026-06-20-05-audit.md"
last_task9_audit: "2026-06-20"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: "2026-06-20"
last_task9_autofix_at: "2026-06-20"
last_body_apply_at: "2026-08-07T07:15:26+08:00"
last_body_apply_run_id: "20260807-071512-04a03874"
last_body_apply_source: "queue:freshness:src/part1-fundamentals/ch01-architecture/07-art-compilation.md"
last_deep_review_at: "2026-08-07T08:36:48+08:00"
last_deep_review_run_id: "20260807-083648-deep-review-962ac2dc"
last_deep_review_log: "logs/deep-review/2026-08-07-20260807-083648-deep-review-962ac2dc-deep-review.md"
deep_review_notes: "2026-08-07 deep-review: 复核 android-17.0.0_r1 ART/JIT/Profile 边界；未发现 Android 18/API38+ 主线结论，修正正文自引用来源标注并关闭 task9 pending 状态。P0 0 / P1 0 / P2 1（已修复）。"
last_review_finalize_at: "2026-08-07T10:08:18+08:00"
last_review_finalize_run_id: "20260807-100535-f89828e4"
review_finalize_notes: "2026-08-07 Hermes finalize-apply: 复核 deep-review 结论、frontmatter/source 边界与正文可读性；未发现开放 P0/P1/P2，推进 finalized。"
---

# ART 编译管线与 dex2oat 优化

一个方法在 Android 上运行时，不一定只有一种执行形态。ART 可以解释 DEX 字节码、在运行期用 JIT 编译热点，也可以加载 dex2oat 预先生成的 AOT 代码。

分析启动性能时，不要笼统比较“AOT 还是 JIT 更快”，应依次确认：

1. 启动路径上的方法当前有没有可用的 AOT 代码？
2. 没有 AOT 代码时，是解释执行，还是已经被 JIT 编译？
3. AOT 产物为什么不存在、失效，或者没有覆盖这条路径？
4. 为了得到更多机器码，安装时间、存储和后台编译成本增加了多少？

诊断时，先看 `pm art dump` 和编译过滤器，再确认 Profile 是否参与 AOT，然后用 Perfetto 或 Macrobenchmark 量化解释执行、JIT 与 dex2oat 成本。仅凭 ODEX 文件存在、单条 JIT 切片或 Profile 文件打包成功，都不足以证明启动性能已经优化。

## 从 DEX 到执行代码

应用构建后携带 DEX 字节码。安装、系统构建或后台维护期间，dex2oat 可以产生 ART 编译产物。文件名和位置会随版本与安装方式变化，常见职责是：

- `.odex`/`.oat`：保存 AOT 编译的机器码和相关元数据；
- `.vdex`：保存验证依赖等信息，某些情况下也包含未压缩 DEX；
- `.art`：可选的 app image，保存 ART 内部的类和对象表示。

这些产物不是 APK 的永久附属物。DEX 校验和、boot image、class loader context、指令集或 ART 版本不匹配时，旧产物可能被判定为不可用，随后回退到解释/JIT，或者重新 dexopt。

```text
DEX
 ├─ verification
 ├─ interpreter ────────────────────┐
 ├─ JIT compile -> code cache  ├─> 执行
 └─ dex2oat -> OAT/ODEX/VDEX ──┘
                ^
                └─ Baseline / Cloud / local profile
```

一个 `.odex` 文件存在，也不代表每个方法都有机器码。编译范围由 compiler filter 和 Profile 决定。

## 编译策略为什么经历多次反转

| 版本 | 主要策略 | 代价落点 |
|---|---|---|
| Android 4.4 | ART 作为可选运行时，尝试安装期 AOT | 安装和存储成本增加 |
| Android 5.0-6.0 | ART 成为平台运行时，以较完整的 AOT 为主 | 更新、首次开机和安装期编译较重 |
| Android 7.0+ | 解释器 + JIT + profile-guided AOT | 运行时热身和后台编译换取更小产物 |
| Android 9+ | Google Play 可在安装时交付 Baseline/Cloud Profile | 安装时就能按真实或预设热点做部分 AOT |
| Android 12+ | ART 成为 Mainline 模块 | 运行时和编译器行为可随模块更新变化 |
| Android 14+ | ART Service 管理应用的设备端 dexopt | 编译原因、优先级和产物管理集中到 ART 模块 |
| Android 17 | 延续混合执行与 ART Service 架构 | 仍应以 Profile、filter 和设备状态解释结果 |

Android 17 没有把应用统一切到“云端机器码”或“全量 AOT”。Cloud Profile 分发的是 Profile，设备仍按本机指令集、运行时和依赖生成编译产物。

## Compiler filter 决定 AOT 范围

Android 17 的 `art/libartbase/base/compiler_filter.h` 定义了当前 filter 集合：

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

| filter | 行为 | 适合怎样理解 |
|---|---|---|
| `verify` | 验证 DEX，不为应用方法生成 AOT 机器码 | 运行主要依赖解释器与 JIT |
| `speed-profile` | AOT 编译 Profile 中的方法，并优化 Profile 中类的加载 | 在启动/交互性能、存储和编译时间之间取平衡 |
| `speed` | 尽可能 AOT 编译应用方法 | 运行期热身少，但编译时间和产物更大 |

`space*` 与 `everything*` 也存在于当前源码，但主要面向系统和产品配置。不能只按名称把 filter 排成简单的“越靠后越快”：Profile 质量、代码布局、存储 I/O、类加载和实际路径都会影响结果。

Android 14+ ART Service 为不同 dexopt 原因配置 filter。AOSP 的标准默认值包括：

```properties
pm.dexopt.first-boot=verify
pm.dexopt.boot-after-ota=verify
pm.dexopt.boot-after-mainline-update=verify
pm.dexopt.bg-dexopt=speed-profile
pm.dexopt.inactive=verify
pm.dexopt.cmdline=verify
```

OEM 可以调整这些属性，ART Service 也会根据 Profile、共享代码、存储压力和编译原因选择或降级 filter。因此，“Android 17 安装后一定是 speed-profile”不是可靠结论。

## dex2oat 做了什么

dex2oat 是 ART 的设备端 AOT 编译器入口。对被 filter 选中的方法，主要流程可以概括为：

1. 打开 DEX、引导映像和类加载器上下文；
2. 验证字节码及类型约束；
3. 为需要编译的方法构建中间表示；
4. 运行内联、常量传播、死代码消除、循环和寄存器分配等优化；
5. 针对目标 ISA 生成机器码及 GC、异常、deopt 所需元数据；
6. 写出 OAT/ODEX、VDEX 和可选 app image。

源码里的 `HGraph` 是 optimizing compiler 使用的 SSA 风格中间表示。SSA 便于追踪值的定义与使用，但“用了 SSA”不等于每个优化都必然发生。方法大小、异常边、类加载假设、Profile 信息和编译预算都会限制优化。

### AOT 产物为什么会失效

编译代码既依赖 APK 本身，也依赖：

- DEX 校验和与拆分包集合；
- 引导类路径与引导映像；
- class loader context 和 `<uses-library>` 顺序；
- ART/APEX 与编译产物格式；
- 目标 ISA、运行时特性和编译选项。

ART 会校验这些依赖。强行复制另一台设备或另一版本的 `.odex`，即使文件名相同，也不能保证可加载。这正是“从 Play 直接下发通用 odex”这一说法不成立的原因。

### ART Service 与编译并发

Android 14 起，应用的设备端 dexopt 由 ART Service 负责。`pm.dexopt.<reason>.concurrency` 控制可并发的 dex2oat 进程数，`dalvik.vm.*dex2oat-threads` 控制单个 dex2oat 的线程数。两者共同决定并行规模。

提高并发可能缩短批处理总时间，也可能增加峰值内存、上下文切换、温升和前台竞争。产品调优必须在目标设备上测首启、OTA、后台维护和交互延迟，不能只看 dexopt 完成时间。

## JIT：用运行时热度换取机器码

当方法没有可用 AOT 代码时，ART 可以先解释执行并记录热度。方法调用、循环回边和线程权重等信息推动计数；达到相应阈值后，ART 把编译任务送入 JIT。

Android 17 的 JIT 源码具有 `fast`、`baseline`、`optimized` 与 OSR 等编译路径。具体启用哪些层级、阈值是多少，受运行时选项和产品属性影响。`dalvik.vm.jitthreshold` 等属性由 `AndroidRuntime.cpp` 转换为 ART 参数，但三方应用不应依赖或尝试修改这些系统属性。

JIT 的典型过程是：

```text
解释执行
  -> 累积 hotness / 类型反馈
  -> JIT 编译任务
  -> 写入进程内 JIT code cache
  -> 更新方法入口
  -> 后续调用执行机器码
```

OSR（On-Stack Replacement）允许长循环在方法尚未返回时切入编译代码。JIT 也能利用运行时类型反馈做去虚化和内联，但编译本身会消耗 CPU 和内存。

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

这表示源码默认的初始容量和上限，不表示每个应用启动就占用 64 MB：

- 初始容量在 16 KB 页大小下至少是两个页面；
- `dalvik.vm.jitinitialsize` 和 `dalvik.vm.jitmaxsize` 可以覆盖默认值；
- capacity、虚拟地址空间和实际 RSS/PSS 不是同一个指标；
- 进程中的机器码、栈映射与性能剖析数据随工作负载增长。

空间压力下，`JitCodeCache::DoCollection(Thread*)` 扫描活动栈和 code cache 状态，保留仍然需要的代码并回收可移除项。调试信息、JVMTI、JIT-at-first-use 等模式会影响是否允许回收。不能把它简化成固定 LRU，也没有依据说大型应用“通常稳定在 4 MB”。

### 去优化是投机优化的安全出口

JIT/AOT 可能基于当前类层次、inline cache 或单实现方法做优化。如果后来加载的新类型、类重定义、调试器或 instrumentation 破坏假设，ART 必须丢弃代码、切回安全入口或去优化栈帧。

看到 deoptimization 相关活动时，需要确认原因和 CPU 时间。一次去优化可能只是正常的类加载边界；持续反复的失效和重编译才更值得检查动态代理、热修复、JVMTI 或插件化行为。

## Profile 体系：四种数据不要混在一起

### 本地 JIT Profile

ART 在应用运行时收集热点方法、类和部分调用点类型信息，由 `ProfileSaver` 持久化。常见内部路径形如：

```text
/data/misc/profiles/cur/<user>/<package>/primary.prof
/data/misc/profiles/ref/<package>/primary.prof
```

这些是系统内部目录，普通应用和普通 shell 不一定有直接读取权限，路径和布局也不是 SDK 契约。诊断时优先用 ART Service/Package Manager 提供的 shell 命令。

本地 Profile 只反映这台设备、这个用户实际执行过的路径。后台 dexopt 可以把它与外部 Profile 合并，用于下一轮 `speed-profile`。

### Baseline Profile

Baseline Profile 由开发者为启动和关键用户旅程生成。人类可读规则在构建时被转换为二进制 Profile，常见打包位置是 `assets/dexopt/baseline.prof`。

通过 Google Play 安装时，Play 可以处理并随 APK/DM 交付 Profile，让 ART 在安装期 AOT 编译标记的方法。非 Play 分发或较老平台可以依赖 ProfileInstaller 把内置 Profile 放到 ART 可消费的位置，随后由 dexopt 使用。

Baseline Profile 是“应该优先编译哪些代码”的提示，不是机器码。它也不会缩短 Profile 外的业务逻辑。

### Cloud Profile

Cloud Profile 由 Google Play 根据历史用户的真实路径聚合，并用于之后的安装或更新。它支持 Android 9/API 28 及以上，需要足够用户样本，而且新版本发布后要经过数小时到数天才可能覆盖。

Baseline Profile 解决新版本和小样本阶段的冷启动问题；Cloud Profile 补充真实用户覆盖。两者可以共同影响安装时编译，但都不会把某台设备生成的 `.odex` 直接复制给另一台设备。

### Startup Profile

Startup Profile 是构建期输入，由 R8 用来调整 DEX 布局，让启动关键类和方法尽量集中在首个 DEX 和更连续的位置。它不参与设备上的 compiler filter 选择，也不会作为一份独立运行时 Profile 留在 APK 中。

```text
Baseline Profile -> ART on-device AOT 范围
Startup Profile  -> R8/D8 构建期 DEX 布局
```

Startup Profile 只能由应用的启动场景生成，库不能单独贡献最终 Startup Profile。启动代码超出主 DEX 容量时，布局收益会受限；需要用 APK Analyzer 或构建产物中的 R8 元数据验证，不能只检查 `startup-prof.txt` 是否存在。

## 应用侧怎样生成和验证 Profile

Baseline Profile Generator 应覆盖真实、稳定且对用户重要的路径：

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

生成 Profile 后还需要验证：

1. 用 release 代码、R8 和与线上一致的 split 构建；
2. 确认 APK/AAB 内有可消费的 Baseline Profile；
3. 确认 Startup Profile 已改变 DEX 布局；
4. 用 Macrobenchmark 对比无预编译与 Baseline Profile 模式；
5. 分别统计启动、关键交互、安装耗时和包/产物体积。

Profile 不应无边界扩张。覆盖所有代码会增加安装期编译和存储成本，还会稀释“关键路径”的意义。每次大规模重构、混淆规则或入口变化后，应重新生成并检查覆盖。

## 用命令确认设备的编译状态

Android 14+ 可以通过 ART Service 查看包的 dexopt 状态：

```bash
adb shell pm art dump com.example.app
```

`android-17.0.0_r1` 的 `ArtShellCommand` 会把这个子命令转到 `ArtManagerLocal.dumpPackage()`。输出中关注：

- DEX 容器与拆分包；
- compiler filter；
- compilation reason；
- primary/secondary dex 的产物状态；
- Profile 与 artifact 是否匹配。

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

`speed-profile` 没有可用 Profile 时，结果会受 ART Service 策略影响。每次实验都要重新 dump 状态，不能只凭命令退出码判断最终 filter。

### `oatdump`、Profile 导出与权限边界

`oatdump` 适合检查与构建匹配的 OAT/ODEX/VDEX，`pm dump-profiles --dump-classes-and-methods <package>` 可以让 ART Service 导出文本 Profile。它们属于平台/设备调试工具：

- user build 可能没有所需二进制或权限；
- `/data/app` 路径含随机段，不能硬编码；
- 二进制 Profile 只保存 DEX 索引，解析时还需要匹配 APK；
- 从另一 build 拿来的 oatdump 可能不理解当前产物格式。

应用团队更适合先用 `pm art dump`、Macrobenchmark 和 APK/AAB 检查；只有平台调试时再读取内部产物。

## 在 Perfetto 中怎样识别编译成本

录制时可以启用 `dalvik` atrace category，再配合调度、CPU 频率和必要的 callstack 数据。不要依赖一份旧 trace 里的固定 slice 名称：Android 17 ART 大量使用 `ScopedTrace(__FUNCTION__)` 或 `__PRETTY_FUNCTION__`，名称会随实现和构建变化。

可靠的观察点包括：

- 应用进程中 JIT 编译线程在 CPU 上运行的时间；
- `art::jit`、`JitCodeCache::DoCollection`、`ProfileSaver` 等调用栈或 slice；
- 独立 `dex2oat`/`artd` 活动及其 CPU、I/O、内存压力；
- 主线程同一时段是在 Running、Runnable，还是等待锁/I/O；
- 安装后首次启动与 Profile 编译后的相同路径对比。

启动期出现 JIT 只能说明有方法进入运行时编译路径，不能单独证明 Baseline Profile 失效。还要确认这是不是非关键线程、编译占用多少 CPU、目标方法是否属于 Profile，以及启动是否受它影响。

## 常见误区

### “存在 ODEX 就说明应用已经全量编译”

ODEX 可以只包含部分方法的机器码，甚至 filter 只做验证。以 `pm art dump` 和 OAT 文件头为准。

### “Baseline Profile 会加速所有代码”

它只引导命中的方法和类。未覆盖路径仍可能解释执行或 JIT，业务自身的 I/O、锁和算法成本也不会消失。

### “JIT 代码缓存上限就是进程实际内存”

上限只是 capacity 配置。实际映射、提交页面、RSS/PSS 和有效机器码大小需要分别测量。

### “Cloud Profile 就是 Cloud Compilation”

Cloud Profile 是聚合后的编译提示，设备用它指导本地 dex2oat。它不是跨设备复用的机器码包。

### “把应用强制编成 speed，启动变快就应该上线这个设置”

`pm compile` 是设备调试命令，应用无法把它作为发布策略。线上应使用 Baseline Profile、Startup Profile、代码瘦身和合理的关键路径。

### “Mainline 更新后所有应用一定全部重编译”

是否失效取决于 boot class path、ART 版本、产物校验和依赖。应观察具体 dexopt 原因和 artifact 状态，不从“发生过更新”直接推导全量重编译。

ART 性能优化需要可重复验证：确认当前编译过滤器与 Profile，测出解释/JIT/AOT 的实际成本，再改 Profile 或代码，并用相同发布构建的包和相同设备复测。只看版本号、文件扩展名或一条 JIT 切片，都不足以解释启动性能。
