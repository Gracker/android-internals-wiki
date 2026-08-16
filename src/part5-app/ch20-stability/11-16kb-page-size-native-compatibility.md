---
title: "16 KB Page Size 兼容检查与 Native 崩溃排查"
chapter: "20.11"
status: finalized
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "Android Developers 16 KB page-size guide updated 2026-08-05; AOSP android-17.0.0_r1 and android17-6.18-2026-06_r6 sources; Android NDK issue #2026"
confidence: medium-high
sources:
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
  - type: official
    path: "https://developer.android.com/guide/topics/manifest/application-element#pageSizeCompat"
  - type: official
    path: "https://developer.android.com/about/versions/16/behavior-changes-all"
  - type: aosp
    path: "https://source.android.com/docs/core/architecture/16kb-page-size/16kb"
  - type: aosp
    path: "https://source.android.com/docs/core/architecture/16kb-page-size/16kb-backcompat-option"
  - type: aosp
    path: "https://source.android.com/docs/core/architecture/16kb-page-size/getting-page-size"
  - type: blog
    path: "OpenClaw定时任务/AutoResearchClaw调研报告/2026-04-30-android-16kb-page-size-hook-library-compatibility.md"
    availability: "not present in the current vault as of 2026-08-14; retained as legacy provenance and not used as current evidence"
  - type: blog
    path: "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-02-android-16kb-page-size-ndk-compatibility.md"
    availability: "not present in the current vault as of 2026-08-14; retained as legacy provenance and not used as current evidence"
  - type: blog
    path: "DeepResearch/2026-05-08-16kb-page-size-third-party-library-impact.md"
    availability: "not present in the current vault as of 2026-08-14; retained as legacy provenance and not used as current evidence"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/res/values/attrs_manifest.xml"
  - type: aosp
    path: "https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker_phdr.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker_phdr_16kib_compat.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/private/WriteProtected.h"
  - type: aosp-kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/Kconfig"
  - type: issue
    path: "https://github.com/android/ndk/issues/2026"
tags: [stability, native-crash, 16kb-page-size, ndk, elf]
related_chapters: ["4.7", "20.3", "20.13", "23.3", "25.6"]
---

# 16 KB Page Size 兼容检查与 Native 崩溃排查

Android 15 / API 35 起，AOSP（Android Open Source Project，Android 开源项目）支持配置为 16 KB 基础页的设备。页大小是内核管理虚拟内存映射与访问权限的基本粒度；应用从 4 KB 环境迁移到 16 KB 环境时，Native 二进制的对齐方式和运行时地址计算都会受影响。

Google Play 当前要求：目标版本为 Android 15（API 35）或更高的应用，必须在 Google Play 的 64 位设备上支持 16 KB 页；从 2027 年 2 月 1 日起，不支持 16 KB 页的应用更新将无法发布。这里的“目标版本”指 `targetSdkVersion`，不能用应用当前运行在哪个 Android 版本来代替这项判断。

本文聚焦应用稳定性。Native 指应用或 SDK 中编译为机器码的 C/C++ 等代码；Android linker 是进程启动或调用 `dlopen()` 时装入共享库的动态链接器。

下文解释安装失败、共享库拒绝加载，以及固定 4 KB 假设导致 `mmap()` 或 `mprotect()` 参数错误的原因。TLB（CPU 缓存的地址转换结果）、page fault（缺页异常）、THP（透明大页）与内存收益见 4.7 节。

为便于复查实现，平台源码固定到 `android-17.0.0_r1`，内核源码固定到 `android17-6.18-2026-06_r6`；版本不同的设备可能采用不同实现。

## 1. 判断应用是否受影响

如果 APK（Android 安装包）、动态功能模块（安装时或按需交付的应用模块）以及全部 SDK 都只有 Java/Kotlin 字节码，Android 官方将其视为已支持 16 KB 页。

仍应在 16 KB 环境完成一次回归测试，因为 AAR（Android 库归档）、媒体库、数据库、监控或广告 SDK 可能附带 `.so`；加固工具也可能在重写或保护安装包时加入 Native 库。

下面的命令列出一个 APK 中随包交付的 `.so` 共享库。

```bash
unzip -Z1 app-release.apk | grep -E '^lib/[^/]+/[^/]+[.]so$'
```

没有输出只说明当前 APK 的 `lib/` 目录没有 `.so`。检查范围尚未包含动态功能模块、运行时下载插件、从 AAR 取出后另行处理的库，以及构建插件在后续任务中加入的 Native 产物。

只要存在 Native 代码，就要分别检查三个层面。`.so` 通常采用 ELF（Executable and Linkable Format，可执行与可链接格式）保存机器码和加载信息。

| 检查面 | 检查对象 | 失败表现 |
| --- | --- | --- |
| ELF 映射 | 每个 `.so` 的可加载段对齐值和段布局 | `dlopen()` / `System.loadLibrary()` 失败，或只能依赖兼容模式 |
| APK 打包 | 未压缩 `.so` 在 ZIP 容器内的起始位置 | 安装失败，或系统改用兼容安装方式 |
| 运行时代码 | 页大小查询、地址与文件偏移计算 | 系统调用返回 `EINVAL`、访问越界、内存权限范围错误或稍后崩溃 |

`EINVAL` 是系统调用的“参数无效”错误码，单凭这个错误码无法确定是页大小问题。

静态库 `.a` 是多个目标文件的归档，不会被 Android linker 直接装入，也无须作为 APK 条目做 ZIP 对齐；其中的代码会参与生成最终 `.so`，写死的 4 KB 计算仍会一并进入。因此，发布检查以最终 `.so` 为准，依赖清单还要记录 `.a` 的来源和构建工具版本。

## 2. ELF 对齐和 ZIP 对齐是两件事

ELF 的 program header（程序头）描述系统怎样把 `.so` 映射到进程的虚拟地址空间。`PT_LOAD` 表示需要装入内存的段；segment（段）是具有相同加载属性的一段文件内容，`p_align` 字段记录它的对齐要求。

16 KB 设备要求每个 `PT_LOAD` 的 `p_align` 不小于 `2**14`，也就是 16384 字节。文件偏移和虚拟地址还要对 `p_align` 取相同余数，这就是段的同余关系。直接改程序头里的数值不会重新排列文件内容，因而无法修复完整布局。

构建期 linker 根据目标文件生成 ELF；Android linker 在应用运行时装入 ELF，二者不要混为一谈。

APK 本身是 ZIP 容器。共享库以未压缩形式交付时，Package Manager（软件包管理器）和 Android linker 可以直接从 APK 映射内容，因此 `.so` 在 ZIP 内的起始偏移也要落在 16 KB 边界。ELF 对齐正确的 `.so` 仍可能位于错误的 ZIP 偏移；ZIP 对齐通过时，ELF 的 `PT_LOAD` 也可能仍按 4 KB 对齐。

下面两种判断都缺少一层证据：

- “CMake 已传链接参数，所以安装包一定兼容”；
- “`zipalign` 通过，所以库一定能在 16 KB 内核加载”。

ELF 布局和 ZIP 偏移都要针对最终交付物验证。

## 3. 工具链基线与旧版本补救

截至 2026 年 8 月 14 日，Android 官方建议使用以下工具链基线：

- Android Gradle Plugin（AGP，Android 构建插件）8.5.1 或更高；
- Android SDK Build Tools（打包与校验工具集）35.0.0 或更高；
- Android NDK（Native Development Kit，Native 开发工具包）r28 或更高；
- 每个预编译 `.so` 都使用明确支持 16 KB 的版本。

NDK r28+ 默认生成 16 KB 对齐的 ELF。使用 NDK r27 或更低版本时，当前官方指南要求同时传入 `max-page-size` 和 `common-page-size` 两个构建期 linker 参数。下面的 CMake 配置只作用于名为 `app_native` 的构建目标。

```cmake
target_link_options(
    app_native
    PRIVATE
    "-Wl,-z,max-page-size=16384"
    "-Wl,-z,common-page-size=16384"
)
```

这两个参数不会自动传入独立构建的 Prefab 包（携带预编译 C/C++ 库的 Android 依赖）、Rust crate（Rust 包）、React Native 模块、Unity/Unreal 插件或闭源 SDK，也不会重写已有 `.so`。

`ndk-build` 项目可通过 `LOCAL_LDFLAGS` 传参。配置文件出现过参数只说明构建意图，验收仍要扫描最终产物。

AGP 8.3～8.5 生成的本地 APK 可能已对齐，`bundletool` 却不会默认对 Play 从 AAB 生成的 APK 做相同的 ZIP 对齐，最终安装包仍可能失败。

暂时无法升级到 AGP 8.5.1+ 时，官方迁移方案是启用 `useLegacyPackaging`：先把共享库压进安装包，安装时再解压到磁盘。这样会增加安装占用，并可能在存储空间不足时提高安装失败率，只适合作为过渡。

## 4. 发布产物怎样检查

### 4.1 ELF：优先使用官方脚本

Android 官方提供 `check_elf_alignment.sh`，以 `ALIGNED` / `UNALIGNED` 报告 APK 中共享库的检查结果；官方步骤要求 `arm64-v8a` 和 `x86_64` 两种 ABI 都没有 `UNALIGNED`。ABI 是二进制代码与处理器、调用约定之间的接口约束。

CI（持续集成）应固定一份已审核的脚本版本，避免自写解析器因 `llvm-readelf` 输出格式变化而误判。

手工复核时，可用 NDK 自带的 `llvm-objdump` 查看各个 `LOAD` 段。

```bash
"$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/darwin-x86_64/bin/llvm-objdump" \
  -p libexample.so | grep -A 1 LOAD
```

每个 `LOAD` 的 `align` 都不能低于 `2**14`。旧脚本若只接受 `0x4000`、`0x10000`、`0x20000` 三个值，会错误拒绝其他更大的合法对齐值；正确条件是“不小于 16 KB”。

还要检查所有 `.so` 是否存在 `GNU_RELRO`。RELRO 是 Relocation Read-Only 的缩写：动态重定位完成后，相关区域会改为只读，以降低被篡改的风险。

RELRO 是独立的安全与布局检查，不能替代 16 KB 对齐；重新链接或混合不同目标文件也可能改变 RELRO 所在的页面边界。若该段缺失，应检查链接选项和依赖版本。

不要用 `llvm-objcopy` 单独修改 `p_align`，文件偏移、虚拟地址、重定位和权限边界需要由构建期 linker 重新生成。

### 4.2 APK：检查未压缩库的 ZIP 边界

Build Tools 35.0.0+ 提供的 `zipalign` 可以校验最终 APK。

```bash
"$ANDROID_SDK_ROOT/build-tools/35.0.0/zipalign" \
  -v -c -P 16 4 app-release.apk
```

`-P 16` 检查未压缩共享库是否位于 16 KB 边界，末尾的 `4` 检查其他未压缩条目的常规 4 字节对齐。命令通过只证明当前 APK 合格；按设备拆分的 split APK、其他渠道包，以及加固或重签名后的安装包都要单独检查。

### 4.3 AAB：检查 bundle 配置和生成后的 APK

AAB（Android App Bundle）是交给应用商店生成设备专用 APK 的发布包。下面用 `bundletool`（构建和检查 AAB 的官方命令行工具）确认 bundle 请求哪一种 ZIP 页对齐。

```bash
bundletool dump config --bundle=app-release.aab | grep alignment
```

期望结果是 `PAGE_ALIGNMENT_16K`。`PAGE_ALIGNMENT_4K` 表示由该 bundle 生成的 APK 会把未压缩 `.so` 放在 4 KB 边界。

AAB 配置通过后，还要按目标设备规格生成 APK set（同一 AAB 产生的一组 APK），检查其中每个相关 split。Play 发布前再核对 App Bundle Explorer 或预发布报告；用户通常安装按设备选择的 split APK，不会直接安装本地生成、包含全部资源的 universal APK。

## 5. 运行时代码不能假设 4096

采用 16 KB ELF 对齐的 `.so` 可以同时运行在 4 KB 和 16 KB 设备上，因为 16 KB 也满足 4 KB 的对齐要求。ELF 对齐描述二进制布局，不会改变设备内核的基础页大小；把源码里的 `4096` 统一替换成 `16384` 仍会让代码在 4 KB 设备上算错。

Native 代码应在运行时查询当前设备的页大小，再用于地址和长度计算。

```c
#include <unistd.h>

long value = sysconf(_SC_PAGESIZE);
if (value <= 0) {
    // 初始化失败：不要继续做地址对齐或内存保护。
}
size_t page_size = (size_t) value;
```

`getpagesize()` 也可用于同一目的。NDK r27+ 的 16 KB 模式不再定义供这类计算使用的编译期 `PAGE_SIZE`。如果 `4096` 仅表示网络缓冲区或文件块大小，应改成能说明用途的常量名，例如 `network_buffer_size`，以免后续维护者把它当作系统页大小。

源码检查至少覆盖以下模式：

- `& ~4095`、`+ 4095`、`>> 12` 和 `<< 12` 等把 4 KB 编进位运算的写法；
- `mmap()` 的文件偏移，以及要求映射到指定地址的 `MAP_FIXED`；
- 改变内存权限的 `mprotect()` 和解除映射的 `munmap()`，包括起始地址与覆盖范围；
- Hook 框架修改代码页时采用的向上、向下取整；Hook 指在运行时改写函数调用路径的技术；
- 自建 allocator（内存分配器）、guard page（用不可访问页面捕获越界）、共享内存和 JIT code cache（即时编译生成代码的缓存）；
- `/proc`、ELF、minidump（进程崩溃摘要）或 tombstone（Android 系统生成的 Native 崩溃记录）解析器中的“页数 × 4096”。

调用 `mprotect()` 时，要把目标区间 `[address, address + length)` 扩展到运行时页边界：起点向下取整，终点向上取整。仅把 `length` 取整到 16 KB，起始地址仍可能未对齐并返回 `EINVAL`。

文件 `mmap()` 的文件偏移也要按运行时页大小对齐。地址加法和向上取整还要检查整数溢出，防止终点回绕到较小地址。

16 KB 页不会放宽 W^X、SELinux 或代码签名约束。W^X 要求内存页在可写与可执行权限之间择一，以减少注入代码的机会；SELinux（Security-Enhanced Linux）是 Android 使用的强制访问控制机制，还会按系统安全策略限制操作。Hook 或 APM（应用性能监控）SDK 即使算对了地址，也不能假定任意页面都能同时写入和执行。

## 6. 怎样判断故障是否由 16 KB 页引起

16 KB 是设备环境条件，看到 `EINVAL` 还不足以完成归因。可以按故障发生阶段整理证据：

| 阶段 | 典型证据 | 处理方向 |
| --- | --- | --- |
| 安装 | Package Manager、Play 或 `adb install` 报错 | 检查未压缩 `.so` 的 ZIP 对齐与打包方式 |
| 进程早期加载 | `program alignment ... smaller than system page size` | 定位 `LOAD` 对齐不足的具体 `.so` |
| `System.loadLibrary()` / `dlopen()` | `UnsatisfiedLinkError`、`dlerror()` | 保存完整加载错误、ABI、库路径和 build ID |
| 内存映射 | `mmap()` / `mprotect()` / `munmap()` 返回 `EINVAL` | 核对页大小、地址、文件偏移、范围与溢出 |
| 延迟业务路径 | 进入媒体、游戏、支付或监控页面后崩溃 | 查按需加载库与该路径的页计算 |
| Native 致命信号 | tombstone 中出现业务或 Hook 调用帧 | 按 20.3 节符号化，结合调用栈定位 |

build ID 是链接器写入二进制的构建标识，可用来确认符号文件与崩溃中的 `.so` 是否对应。

`Invalid argument` 的含义过宽；只有同时具备 `page_size=16384`、相关系统调用、参数值和调用栈时，才适合归入页大小兼容问题。4 KB 与 16 KB 设备都出现同一 `SIGSEGV`（非法内存访问信号）时，应先按一般 Native Crash 分析。

### NDK r27 的 WriteProtected 报告怎样使用

NDK issue #2026 记录了一组具体样本：`arm64-v8a`、`ndk-build`、NDK r27 和静态归档，报错为 `WriteProtected mprotect 1 failed: Invalid argument`；报告者称 r28 canary（公开测试版）可以运行。

该 issue 后来以 “not planned” 关闭，页面没有给出适用于所有 r27 产物的维护者结论。

这份报告可用于匹配错误文本和构建条件，无法据此认定“NDK r27 的 `libc.a` 全部不支持 16 KB”。遇到相同消息时，应保留完整调用栈和库 build ID，用当前 NDK r28+ 全量重编作对照，并确认每个静态归档的来源。

Android 17 的 `WriteProtected<T>` 是 bionic（Android 的 C 标准库及相关底层运行时）内部用于保护小块全局数据的模板；当前实现按 `max_android_page_size()` 对齐存储区，并用同一长度调用 `mprotect()`。这段新实现不能证明旧预编译库都采用同一份代码。

## 7. Android 17 linker 的兼容模式

Android 16 起，16 KB 设备可以为部分仅按 4 KB 对齐的应用启用 backcompat，也就是 16 KB 页大小兼容模式。Package Manager 发现 ELF 的 `LOAD` 段按 4 KB 对齐，或 APK 内未压缩 ELF 的 ZIP 起点只按 4 KB 对齐时，可以让应用进入该模式，并在首次启动时显示警告。

在 `android-17.0.0_r1` 中，`ElfReader::LoadSegments()` 加载各段时会核对页大小、最小段对齐和兼容模式。运行时页大小至少为 16 KB、最小段对齐低于系统页大小并且兼容模式关闭时，普通加载路径会拒绝这种 ELF，并给出以下错误：

```text
program alignment (4096) cannot be smaller than system page size (16384)
```

这条消息说明 ELF 布局不满足当前页大小。应用自行调用 `mprotect()` 时传入未对齐地址属于另一类故障，错误文本和调用栈也不同。

兼容路径无法把 4 KB 段直接映射到 16 KB 权限边界。Android 17 的 `CompatMapSegment()` 先建立不直接对应文件的匿名内存映射，将段内容放入其中，再按各段需求恢复访问权限；`linker_phdr_16kib_compat.cpp` 也会为 RELRO 设置只读保护。

兼容模式没有关闭 RELRO，其启动耗时、内存共享方式和 PSS 也未必与原生 16 KB ELF 相同。PSS（Proportional Set Size）会按共享比例分摊进程使用的共享内存。

兼容模式只帮助部分旧 ELF 完成加载，以下问题仍需应用修复：

- 内核基础页仍是 16 KB；
- 业务代码里的 `4096`、`>> 12` 或错误 `mprotect()` 不会变化；
- 动态下载的未知库不会被重新构建；
- 未验证的 Hook、加固壳或插件不会自动获得正确的页计算；
- Google Play 的 16 KB 发布要求仍然适用。

### 用应用清单控制单个应用

使用 Android 16 SDK 或更高版本编译时，可以在 `<application>` 上设置 `android:pageSizeCompat`，覆盖平台或用户选择的兼容模式。下面的写法适合已完成适配后的测试：若仍有旧 ELF，系统不会再自动为该应用启用兼容模式。

```xml
<application
    android:pageSizeCompat="disabled"
    ... >
</application>
```

这个属性只控制兼容模式，不代表应用已经通过 16 KB 检查。`enabled` 强制启用兼容模式并隐藏首次警告，可用于迁移诊断；`disabled` 便于让遗漏的旧 ELF 直接失败。发布前仍要检查最终产物，并在 16 KB 真机或等效测试环境中运行。

### Android 17 的 `fatal`（立即中止）测试

Android 17 允许测试设备在发现不兼容 ELF 时立即触发 `SIGABRT`，即由进程主动中止并留下崩溃记录。下面两项系统属性要配套设置，并且只适用于专用测试设备或 emulator（Android 模拟器）。

```bash
adb shell setprop bionic.linker.16kb.app_compat.enabled fatal
adb shell setprop pm.16kb.app_compat.disabled true
```

重新安装并启动待测应用后，要沿完整功能路径触发所有延迟加载库。`fatal` 模式会把系统自动采用的兼容加载转成明确崩溃，便于发现遗漏；测试完成后应恢复设备属性。同一发布包还要支持 4 KB 设备，因此这项测试不能替代 4 KB 环境回归。

## 8. 第三方 SDK、Hook 和动态模块

依赖清单至少记录以下信息：

| 字段 | 目的 |
| --- | --- |
| 库名、ABI、build ID | 确认崩溃记录对应哪一个最终二进制 |
| 来源模块或 SDK、版本 | 确认由哪个依赖引入，以及由谁负责升级 |
| `.so` / `.a` / Prefab / AAR | 区分最终共享库与构建输入 |
| NDK、构建期 linker 和构建系统 | 解释 ELF 如何生成和对齐 |
| 是否有源码、是否可重编 | 决定修复路径 |
| ELF、RELRO、ZIP 检查结果 | 保留可重复执行的检查证据 |
| 4 KB / 16 KB 运行结果 | 确认两种基础页环境都能运行 |

供应商声明“支持 16 KB”只能作为版本选择信息，最终 APK 仍要接受检查。同一个 SDK 的不同 ABI 可能来自不同构建流程；`arm64-v8a` 通过，无法证明 `x86_64` 模拟器产物也通过。

加固、重签名和渠道重打包发生在编译之后，要对处理后的安装包重新检查。

Hook 和 Native 监控 SDK 还要检查运行时页计算。PLT Hook 通过过程链接表（Procedure Linkage Table，ELF 用来间接调用外部函数的表）改写函数目标，未必修改代码页；inline Hook 会改写函数入口处的机器指令，通常需要改变页面权限。

出现 `mprotect()` 只能说明代码尝试调整权限，不能直接判定为 16 KB 不兼容。结论应对应具体 SDK 版本、地址计算方式和最终 `.so`。

动态下载的 `.so` 不在初始 APK 扫描范围内，Android linker 仍会按当前页大小检查它。下载服务应按 ABI、版本、文件哈希和 16 KB 兼容状态选择产物，并保留数字签名校验和回退到上一可用版本的能力。加载失败后不要直接修改 ELF header（文件头）；完整布局需要重新链接生成。

## 9. 线上监控与发布前检查

进程启动后，可以通过 `sysconf(_SC_PAGESIZE)` 记录运行时页大小。异常事件建议包含：

- Android API、build fingerprint（标识系统构建版本的字符串）、ABI 和 `page_size`；
- 应用版本、Native 库名、build ID 和供应商版本；
- 加载阶段，以及 `dlerror()` / `UnsatisfiedLinkError` 的完整原文；
- signal（致命信号）、fault address（触发访问错误的地址）、符号化调用栈（把机器地址还原为函数名和源码位置），以及故障是否发生在 Hook 或加载路径；
- AGP、NDK、Build Tools 与打包任务版本；
- ELF、ZIP、AAB 检查所对应的构建产物 ID。

`page_size=16384` 本身是正常设备属性，只适合用于事件分组。必需库加载失败时，不应捕获 `UnsatisfiedLinkError` 后让应用在初始化不完整的状态下继续运行；可以展示说明原因的错误页。可选库失败时，则禁用依赖它的功能。

崩溃若发生在监控 SDK 初始化之前，进程内 crash handler（崩溃处理器）来不及记录，需要依赖系统 tombstone、Play 报告，并在下一次启动时补交上次留下的记录。

发布流程可按产物生成顺序执行以下检查：

1. 枚举主 APK、各动态功能模块、AAR、Prefab、游戏插件和动态下载库；
2. 升级工具链并清理缓存，全量重建所有 ABI；
3. 对每个最终 `.so` 检查 `LOAD` 对齐和 RELRO；
4. 对每个最终 APK 检查 ZIP 对齐，对 AAB 检查 bundle 配置；
5. 对 Play 或 `bundletool` 生成的目标设备 split 再检查一次；
6. 在 4 KB 和 16 KB 环境跑启动与关键功能；
7. 在 Android 17 `fatal` 模式触发所有按需加载路径；
8. 分批发布期间，按 `page_size + Native build ID + crash signature` 对告警分组；crash signature 是根据异常类型和关键调用帧归并同类崩溃的标识。

发布通过条件应覆盖全部产物和关键功能路径，并保留相应检查记录。应用首页能在一台 16 KB 模拟器上打开，只验证了一个启动路径。

## 10. 测试组合

设备启动后先确认运行时基础页。

```bash
adb shell getconf PAGE_SIZE
adb shell getprop ro.build.fingerprint
```

16 KB 环境的 `PAGE_SIZE` 应输出 `16384`。开发者选项、16 KB 模拟器、Cuttlefish 和真实设备都可用于兼容性测试。Cuttlefish 是 AOSP 提供的可配置虚拟 Android 设备。

Cuttlefish 和 Android 模拟器都无法覆盖 OEM（设备制造商）的打包差异、硬件驱动、应用加固和全部真实 ABI 组合。

JNI 是 Java/Kotlin 与 Native 代码之间的调用接口，`RegisterNatives` 用于注册 Native 方法实现。至少执行以下场景：

- 全新安装、覆盖安装、AAB 生成的 split APK 安装与渠道包安装；
- 冷启动、二次启动、后台进程和 isolated process（权限与组件范围受限的隔离进程）；
- 所有 `System.loadLibrary()`、JNI `RegisterNatives` 与手工 `dlopen()`；
- 媒体、相机、WebView、数据库、地图、游戏和支付页面；
- Hook、Native Crash 采集、热修复、加固壳和性能 SDK；
- 动态功能模块安装后的加载，以及离线动态插件；
- 低存储空间下使用压缩共享库的安装路径；
- 4 KB 与 16 KB 设备的相同功能回归。

出现差异时，应保存原始安装日志、logcat 系统日志、tombstone、目标 `.so` 和 build ID。失败产物如果没有保留，只剩错误文本截图，后续就无法确认修复前后测试的是不是同一个二进制。

## 11. 复核清单

- [ ] 是否列出了间接依赖、动态功能模块、加固产物和动态下载库？
- [ ] 是否把最终 `.so` 与输入 `.a`、Prefab、AAR 区分开？
- [ ] 是否使用 AGP 8.5.1+、Build Tools 35+、NDK r28+ 或有证据的旧版补救？
- [ ] 每个 `LOAD` 段的 `align` 是否不小于 `2**14`？
- [ ] 每个 `.so` 是否保留 `GNU_RELRO`？
- [ ] 每个最终 APK 是否通过 `zipalign -P 16`？
- [ ] AAB 是否显示 `PAGE_ALIGNMENT_16K`，生成后的 split 是否复检？
- [ ] 是否移除了 `4096`、`>> 12` 与编译期 `PAGE_SIZE` 假设？
- [ ] `mmap()` 文件偏移、`mprotect()` 起点和保护范围是否按运行时页计算？
- [ ] 是否把一般的 `EINVAL` 与 16 KB 归因所需的额外证据区分开？
- [ ] 是否在 Android 17 `fatal` 模式触发了全部延迟加载路径？
- [ ] 是否同时在 4 KB 和 16 KB 环境回归？
- [ ] 是否避免把兼容模式当作发布方案？
- [ ] 分批发布时，是否按页大小、ABI、库 build ID 和崩溃特征监控？

## 源码与官方资料

- [Android Developers：Support 16 KB page sizes](https://developer.android.com/guide/practices/page-sizes)：Play 要求、工具链、ELF/ZIP 检查、16 KB 兼容模式与 Android 17 `fatal` 测试模式。
- [Android Developers：`<application>` / `android:pageSizeCompat`](https://developer.android.com/guide/topics/manifest/application-element#pageSizeCompat)：应用清单覆盖项的公开契约。
- [Android Developers：Android 16 behavior changes](https://developer.android.com/about/versions/16/behavior-changes-all)：16 KB 兼容模式及 `pageSizeCompat` 的 SDK 编译要求。
- [AOSP：16 KB page size](https://source.android.com/docs/core/architecture/16kb-page-size/16kb)：平台与内核配置、运行时页编程和系统产物检查。
- [AOSP：Enable 16 KB backcompat option](https://source.android.com/docs/core/architecture/16kb-page-size/16kb-backcompat-option)：兼容模式的触发条件、设备属性与单应用控制方式。
- [AOSP：Get the page size](https://source.android.com/docs/core/architecture/16kb-page-size/getting-page-size)：通过代码、命令、`/proc` 和辅助向量读取运行时页大小。
- [AOSP `attrs_manifest.xml`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/res/values/attrs_manifest.xml)：`pageSizeCompat` 的 `enabled` / `disabled` 枚举定义。
- [AOSP `linker_phdr.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker_phdr.cpp)：LOAD 对齐校验、compat 选择与 fatal 失败路径。
- [AOSP `linker_phdr_16kib_compat.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker_phdr_16kib_compat.cpp)：4 KB ELF 在 16 KB 页上的兼容映射与权限恢复。
- [AOSP `WriteProtected.h`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/private/WriteProtected.h)：bionic 当前的最大页对齐实现。
- [Android Common Kernel `arch/arm64/Kconfig`（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/Kconfig)：`CONFIG_ARM64_16K_PAGES` 的内核配置边界。
- [Android NDK issue #2026](https://github.com/android/ndk/issues/2026)：NDK r27 `WriteProtected` 报错的具体样本及其证据限制。

16 KB 兼容检查要回答三个独立问题：交付物能否安装，所有 ELF 能否原生加载，代码能否按运行时页大小正确计算。三项都通过，才说明最终发布包覆盖了安装、加载和运行阶段；首页测试成功只验证其中一小部分。
