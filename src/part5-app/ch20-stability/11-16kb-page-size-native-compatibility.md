---
title: "16KB Page Size 兼容性与 Native 崩溃治理"
chapter: "20.11"
status: finalized
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
last_verified: "2026-05-18"
last_verified_against: "Android Developers page-size guide; AOSP 16KB page-size docs; NDK issue #2026"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
  - type: aosp
    path: "https://source.android.com/docs/core/architecture/16kb-page-size/16kb"
  - type: aosp
    path: "https://source.android.com/docs/core/architecture/16kb-page-size/16kb-backcompat-option"
  - type: aosp
    path: "https://source.android.com/docs/core/architecture/16kb-page-size/getting-page-size"
  - type: blog
    path: "OpenClaw定时任务/AutoResearchClaw调研报告/2026-04-30-android-16kb-page-size-hook-library-compatibility.md"
  - type: blog
    path: "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-02-android-16kb-page-size-ndk-compatibility.md"
  - type: blog
    path: "DeepResearch/2026-05-08-16kb-page-size-third-party-library-impact.md"
  - type: blog
    path: "https://github.com/android/ndk/issues/2026"
tags: [stability, native-crash, 16kb-page-size, ndk, elf]
related_chapters: ["4.7", "20.3", "20.13", "23.3", "25.6"]
---

# 16KB Page Size 兼容性与 Native 崩溃治理

Android 15 / API 35 起，AOSP 支持使用 16 KB 基础页的设备。自 2025 年 11 月 1 日起，Google Play 要求面向 Android 15 及以上设备的新应用和更新在 64 位设备上支持 16 KB 页。到 Android 17 / API 37，这已经是发布兼容性要求，不只是性能实验。

这里聚焦应用稳定性：产物为什么会安装失败、Linker 为什么拒绝加载、页大小假设为什么会让 `mmap()` 或 `mprotect()` 出错，以及发布前怎样发现漏网的 native 依赖。TLB、page fault、THP 与内存收益见 4.7 节。

平台源码锚点是 `android-17.0.0_r1`，内核锚点是 `android17-6.18-2026-06_r6`。

## 1. 先判断应用是否受影响

如果 APK、动态功能模块和所有 SDK 都只有 Java/Kotlin 字节码，Android 官方将其视为已支持 16 KB 页。仍建议在 16 KB 环境跑一次回归，因为 AAR、加固工具、媒体库、数据库、监控 SDK 或广告 SDK 可能悄悄带入 `.so`。

下面的命令用于枚举一个 APK 中随包交付的共享库。

```bash
unzip -Z1 app-release.apk | grep -E '^lib/[^/]+/[^/]+[.]so$'
```

没有输出只能说明这个 APK 的 `lib/` 目录里没有 `.so`。它不能覆盖 dynamic feature、运行时下载插件、从 AAR 解包后再处理的库，也不能证明构建插件没有在后续阶段注入 native 产物。

只要存在 native 代码，就要同时通过三道检查：

| 检查面 | 检查对象 | 失败表现 |
| --- | --- | --- |
| ELF 映射 | 每个 `.so` 的 `PT_LOAD.p_align` 和段布局 | `dlopen` / `System.loadLibrary` 失败，或依赖兼容模式 |
| APK 打包 | 未压缩 `.so` 在 ZIP 中的起始偏移 | 安装失败、系统启用打包兼容路径 |
| 运行时代码 | 页大小查询、地址与文件偏移计算 | `EINVAL`、越界、保护范围错误或延迟崩溃 |

静态库 `.a` 不会被 Android Linker 直接加载，也不需要作为 APK 条目做 ZIP 对齐；但它的目标文件会进入最终 `.so`，其中写死的 4 KB 计算也会被带进去。因此，发布检查以最终 `.so` 为准，依赖盘点仍要追溯 `.a` 的来源和工具链。

## 2. ELF 对齐和 ZIP 对齐是两件事

ELF program header 描述进程怎样把一个 `.so` 映射到虚拟地址空间。16 KB 设备要求每个 `PT_LOAD` segment 的 `p_align` 不小于 `2**14`。ELF 还要求文件偏移与虚拟地址满足 segment 的同余关系；只修改 program header 中的数字不能修复整个链接布局。

APK 是 ZIP 容器。若共享库以未压缩形式交付，Package Manager 和 Linker 可以直接从 APK 映射它；这要求库内容在 ZIP 中从 16 KB 边界开始。一个 `.so` 可以有正确的 ELF 对齐，却被放在错误的 ZIP 偏移；也可以 ZIP 对齐正确，但 ELF 的 LOAD segment 仍只有 4 KB 对齐。

因此，下面两种判断都不成立：

- “CMake 已传链接参数，所以安装包一定兼容”；
- “`zipalign` 通过，所以库一定能在 16 KB 内核加载”。

两层必须针对最终交付物分别验证。

## 3. 工具链基线与旧版本补救

Android 官方截至 2026 年 7 月给出的稳妥基线是：

- Android Gradle Plugin 8.5.1 或更高；
- Android SDK Build Tools 35.0.0 或更高；
- Android NDK r28 或更高；
- 每个预编译 `.so` 都来自支持 16 KB 的版本。

NDK r28+ 默认生成 16 KB 对齐的 ELF。使用 NDK r27 或更低版本时，官方迁移指南要求同时设置最大页和 common page。下面的 CMake 配置只影响指定 target。

```cmake
target_link_options(
    app_native
    PRIVATE
    "-Wl,-z,max-page-size=16384"
    "-Wl,-z,common-page-size=16384"
)
```

参数不会传进另一个独立构建的 Prefab、Rust crate、React Native 模块、Unity/Unreal 插件或闭源 SDK，也不会重写已经编译好的 `.so`。`ndk-build` 项目对应使用 `LOCAL_LDFLAGS`；无论使用哪种构建系统，验收依据都应是最终产物扫描，而不是配置文件里出现过某个参数。

AGP 8.3～8.5 的本地 APK 可能看起来已经对齐，但旧组合生成的 Play APK 仍可能缺少正确的 ZIP 对齐。无法升级到 AGP 8.5.1+ 时，官方给出的过渡方案是启用 `useLegacyPackaging`，让共享库压缩后在安装时解压；代价是安装占用增加，也可能因空间不足提高安装失败概率。这是迁移手段，不是长期基线。

## 4. 发布产物怎样检查

### 4.1 ELF：优先使用官方脚本

Android 官方维护了 `check_elf_alignment.sh`，会列出 APK 中 arm64-v8a 共享库的 `ALIGNED` / `UNALIGNED` 结果。CI 可以直接固定该脚本的已审版本，避免自写 parser 因 `llvm-readelf` 输出格式变化而误判。

手工复核时，可用 NDK 自带的 `llvm-objdump` 查看 LOAD segment。

```bash
"$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/darwin-x86_64/bin/llvm-objdump" \
  -p libexample.so | grep -A 1 LOAD
```

每个 LOAD 的 `align` 都不能低于 `2**14`。不要像旧脚本那样只允许 `0x4000`、`0x10000`、`0x20000` 三个固定值；判断条件是“不小于 16 KB”，不是命中一个枚举表。

还要检查所有 `.so` 是否存在 `GNU_RELRO`。RELRO 不是 16 KB 对齐的替代条件，但重新链接和混合目标文件可能改变段布局；缺失时应回到链接选项和依赖版本排查。不要使用 `llvm-objcopy` 只改 `p_align` 字段，文件偏移、虚拟地址、重定位与权限边界必须由 Linker 完整生成。

### 4.2 APK：检查未压缩库的 ZIP 边界

Build Tools 35.0.0+ 提供的 `zipalign` 可以校验最终 APK。

```bash
"$ANDROID_SDK_ROOT/build-tools/35.0.0/zipalign" \
  -v -c -P 16 4 app-release.apk
```

`-P 16` 检查未压缩共享库的 16 KB 页对齐，尾部的 `4` 保留其他未压缩条目的常规对齐。命令通过只覆盖当前 APK；按设备生成的 split APK、其他渠道包和加固后的重打包产物都要单独检查。

### 4.3 AAB：检查 bundle 配置和生成后的 APK

下面的命令用于确认 AAB 请求哪一种页对齐。

```bash
bundletool dump config --bundle=app-release.aab | grep alignment
```

期望结果是 `PAGE_ALIGNMENT_16K`。`PAGE_ALIGNMENT_4K` 表示从该 bundle 生成的 APK 会按 4 KB 对齐未压缩 `.so`。AAB 配置通过后，还应使用目标设备规格生成 APK set 并检查其中每个相关 split；Play 发布前再核对 App Bundle Explorer 或预发布报告，因为用户安装的不是本地 universal APK。

## 5. 运行时代码不能假设 4096

一个采用 16 KB ELF 对齐的 `.so` 可以同时运行在 4 KB 和 16 KB 设备上。链接对齐为兼容上限，运行时基础页仍由当前内核决定，所以不能把源码中的 `4096` 统一替换成 `16384`。

Native 代码应从运行时查询页大小。

```c
#include <unistd.h>

long value = sysconf(_SC_PAGESIZE);
if (value <= 0) {
    // 初始化失败：不要继续做地址对齐或内存保护。
}
size_t page_size = (size_t) value;
```

`getpagesize()` 也可用于同一目的。NDK r27+ 在 16 KB 模式下不再鼓励依赖编译期 `PAGE_SIZE`；若 `4096` 只是网络缓冲区或文件块大小，应改用能表达业务含义的名称，避免以后被误当作系统页大小。

源码扫描至少覆盖以下模式：

- `& ~4095`、`+ 4095`、`>> 12` 和 `<< 12`；
- `mmap()` 的文件 offset 与 `MAP_FIXED` 地址；
- `mprotect()`、`munmap()` 的起始地址和覆盖范围；
- Hook 框架修改代码页时的向上、向下取整；
- 自建 allocator、guard page、共享内存和 JIT/code cache；
- `/proc`、ELF、minidump 或 tombstone 解析器中的“页数 × 4096”。

对 `mprotect()`，要把目标区间 `[address, address + length)` 扩展到运行时页边界：起点向下取整，终点向上取整。只对 length 做 16 KB 取整仍可能因为起始地址未对齐而返回 `EINVAL`。对文件 `mmap()`，offset 也必须满足运行时页大小要求。所有加法和向上取整还要检查整数溢出。

16 KB 页没有放宽 W^X、SELinux 或代码签名约束。Hook/APM SDK 即使把地址算对，也不能假设任意页面都允许同时写和执行。

## 6. 故障签名怎样归因

16 KB 是环境条件，不是看到 `EINVAL` 就能套用的统一原因。建议按故障阶段拆分：

| 阶段 | 典型证据 | 处理方向 |
| --- | --- | --- |
| 安装 | Package Manager、Play 或 `adb install` 报错 | 检查未压缩 `.so` 的 ZIP 对齐与打包方式 |
| 进程早期加载 | `program alignment ... smaller than system page size` | 定位 LOAD 对齐不足的具体 `.so` |
| `System.loadLibrary` / `dlopen` | `UnsatisfiedLinkError`、`dlerror()` | 保存完整 loader 文本、ABI、库路径和 build ID |
| 内存映射 | `mmap` / `mprotect` / `munmap` 返回 `EINVAL` | 核对页大小、地址、offset、范围与溢出 |
| 延迟业务路径 | 进入媒体、游戏、支付或监控页面后崩溃 | 查按需加载库与该路径的页计算 |
| native signal | tombstone 中出现业务或 Hook 帧 | 按 20.3 节符号化，不能只凭设备是 16 KB 下结论 |

`Invalid argument` 太宽泛。只有同时具备 `page_size=16384`、相关系统调用、参数证据和调用栈时，才应归入页大小兼容问题。4 KB 与 16 KB 设备都出现的同一 `SIGSEGV`，应先按普通 native crash 分析。

### NDK r27 的 WriteProtected 报告怎样使用

NDK issue #2026 记录了一组具体样本：arm64-v8a、`ndk-build`、NDK r27、静态 archive，报错为 `WriteProtected mprotect 1 failed: Invalid argument`；报告者称 r28 canary 可用。该 issue 被关闭为 “not planned”，页面没有给出能覆盖所有 r27 产物的维护者结论。

因此，它适合作为精确签名线索，不适合推导“NDK r27 的 `libc.a` 全部不支持 16 KB”。遇到相同消息时，应保留完整堆栈和库 build ID，用当前 NDK r28+ 全量重编做对照，并追查每个静态 archive 的来源。Android 17 的 `WriteProtected<T>` 已按 `max_android_page_size()` 对齐 storage 和保护长度，这也不能反向证明旧预编译库都来自同一实现。

## 7. Android 17 Linker 的兼容模式

Android 16 起，16 KB 设备可以为部分 4 KB 对齐应用启用 backcompat。Package Manager 在发现 4 KB LOAD 对齐的 ELF，或 APK 中存在按 4 KB ZIP 对齐的未压缩 ELF 时，可以让应用进入兼容模式并显示提示。

在 `android-17.0.0_r1` 中，`ElfReader::Read()` 只有在运行时页大小为 16 KB 且某个 LOAD segment 的最小对齐不足 16 KB 时，才判断 Linker 兼容开关。普通加载路径拒绝这种 ELF，并给出以下错误：

```text
program alignment (4096) cannot be smaller than system page size (16384)
```

这条消息说明 ELF 链接布局不满足当前页大小；它与应用自己调用 `mprotect()` 时传入错误地址属于不同故障。

兼容路径不能简单地把 4 KB segment 直接映射到 16 KB 权限边界。Android 17 的 `CompatMapSegment()` 使用匿名映射承载内容，再按 segment 需求恢复权限；`linker_phdr_16kib_compat.cpp` 也为 RELRO 处理只读保护。因此，不能把兼容模式描述成“关闭 RELRO”，也不能承诺它与原生 16 KB ELF 的启动耗时、共享页和 PSS 相同。

兼容模式还有一项限制：它只帮助旧 ELF 被加载，不会：

- 把内核基础页改成 4 KB；
- 修复业务代码中的 `4096`、`>> 12` 或错误 `mprotect()`；
- 改造动态下载的未知库；
- 让未验证的 Hook、加固壳或插件自动安全；
- 替代 Google Play 的 16 KB 发布要求。

### 用 manifest 控制单个应用

使用 Android 16 SDK 或更高版本编译时，可以在 `<application>` 上设置 `android:pageSizeCompat`。下面的写法用于已完成适配后的测试：一旦仍有旧 ELF，就不让系统为应用兜底。

```xml
<application
    android:pageSizeCompat="disabled"
    ... >
</application>
```

这个属性是兼容模式覆盖项，不是“已通过 16 KB 检查”的声明。`enabled` 会强制启用兼容模式并隐藏首次提示，适合迁移诊断；`disabled` 适合暴露遗漏，但发布前仍要以产物扫描和 16 KB 真机运行结果为准。

### Android 17 的 fatal 测试

Android 17 还允许在测试设备上让不兼容 ELF 立即 `SIGABRT`。下面两条属性必须配套使用，并且只应在专用测试设备或 emulator 上设置。

```bash
adb shell setprop bionic.linker.16kb.app_compat.enabled fatal
adb shell setprop pm.16kb.app_compat.disabled true
```

重新安装并启动待测应用后，按完整业务路径触发所有延迟加载库。`fatal` 模式的价值是把隐式 backcompat 变成可见失败；测试完成后应恢复设备属性。它不替代 4 KB 设备回归，因为同一发布包仍要同时支持两种基础页。

## 8. 三方 SDK、Hook 和动态模块

依赖清单至少记录：

| 字段 | 目的 |
| --- | --- |
| 库名、ABI、build ID | 唯一定位最终二进制 |
| 来源模块或 SDK、版本 | 找到升级责任方 |
| `.so` / `.a` / Prefab / AAR | 区分最终产物与输入 |
| NDK、Linker 和构建系统 | 解释对齐方式 |
| 是否有源码、是否可重编 | 决定修复路径 |
| ELF、RELRO、ZIP 检查结果 | 留下可复核证据 |
| 4 KB / 16 KB 运行结果 | 防止只在一种设备验证 |

供应商写一句“支持 16 KB”只能作为输入，不能替代最终 APK 检查。同一个 SDK 的不同 ABI 可能来自不同流水线；arm64-v8a 通过不代表 x86_64 emulator 产物也通过。加固、重签名和渠道重打包位于编译之后，更要对处理后的包再跑一遍检查。

Hook 和 native 监控 SDK 还要关注运行时页计算。PLT Hook 不一定修改代码页，inline Hook 往往需要改变页面权限；不能用“调用了 `mprotect()`”直接判为不兼容，也不能只看 SDK 名称判定安全。证据应落到具体版本、地址计算和最终 `.so`。

动态下载的 `.so` 不在初始 APK 扫描范围内，但 Linker 仍按 16 KB 规则加载。下载端应按 ABI、版本、哈希和 16 KB 能力选择产物，并保留签名校验与回滚；不要在加载失败后尝试修改二进制 header。

## 9. 线上监控与发布门禁

进程启动后可以通过 `sysconf(_SC_PAGESIZE)` 记录运行时页大小。异常事件建议包含：

- Android API、build fingerprint、ABI 和 `page_size`；
- 应用版本、native 库名、build ID 和供应商版本；
- 加载阶段、`dlerror()` / `UnsatisfiedLinkError` 原文；
- signal、fault address、符号化栈和是否发生在 Hook/加载路径；
- AGP、NDK、Build Tools 与打包任务版本；
- ELF、ZIP、AAB 检查对应的构建产物 ID。

不要把 `page_size=16384` 本身标成异常。它只用于分组。必需库加载失败时，不应捕获 `UnsatisfiedLinkError` 后让应用带着半初始化状态继续运行；可以展示受控错误页或禁用对应的可选功能。若崩溃发生在监控 SDK 初始化之前，进程内 handler 也无能为力，需要依赖系统 tombstone、Play 报告和下一次启动补偿。

发布流程建议按产物生成顺序设置检查：

1. 枚举主 APK、各 dynamic feature、AAR、Prefab、游戏插件和动态下发库；
2. 升级工具链并清理缓存，全量重建所有 ABI；
3. 对每个最终 `.so` 检查 LOAD 对齐和 RELRO；
4. 对每个最终 APK 检查 ZIP 对齐，对 AAB 检查 bundle 配置；
5. 对 Play 或 `bundletool` 生成的目标设备 split 再检查一次；
6. 在 4 KB 和 16 KB 环境跑启动与关键功能；
7. 在 Android 17 fatal 模式覆盖所有按需加载路径；
8. 灰度阶段按 `page_size + native build ID + signature` 分组告警。

发布门禁的通过条件应是“所有产物和关键路径都有证据”，不能只看应用首页在一台 16 KB emulator 上打开成功。

## 10. 测试组合

设备启动后先确认运行时基础页。

```bash
adb shell getconf PAGE_SIZE
adb shell getprop ro.build.fingerprint
```

16 KB 环境的 `PAGE_SIZE` 应输出 `16384`。开发者选项、16 KB emulator、Cuttlefish 和真实设备都可用于兼容性测试，但 emulator 不能覆盖 OEM 打包、驱动、加固和真实 ABI 组合。

至少执行以下场景：

- 全新安装、覆盖安装、AAB split 安装与渠道包安装；
- 冷启动、二次启动、后台进程和 isolated process；
- 所有 `System.loadLibrary()`、JNI `RegisterNatives` 与手工 `dlopen()`；
- 媒体、相机、WebView、数据库、地图、游戏和支付页面；
- Hook、native crash 采集、热修复、加固壳和性能 SDK；
- dynamic feature 安装后加载，以及离线动态插件；
- 低存储空间下使用压缩共享库的安装路径；
- 4 KB 与 16 KB 设备的相同功能回归。

出现差异时保存原始安装日志、logcat、tombstone、目标 `.so` 和 build ID。没有保留失败产物，只留下字符串截图，后续很难证明修复是否覆盖同一个二进制。

## 11. 复核清单

- [ ] 是否盘点了间接依赖、dynamic feature、加固产物和动态下载库？
- [ ] 是否把最终 `.so` 与输入 `.a`、Prefab、AAR 区分开？
- [ ] 是否使用 AGP 8.5.1+、Build Tools 35+、NDK r28+ 或有证据的旧版补救？
- [ ] 每个 LOAD segment 的 `align` 是否不小于 `2**14`？
- [ ] 每个 `.so` 是否保留 `GNU_RELRO`？
- [ ] 每个最终 APK 是否通过 `zipalign -P 16`？
- [ ] AAB 是否显示 `PAGE_ALIGNMENT_16K`，生成后的 split 是否复检？
- [ ] 是否移除了 `4096`、`>> 12` 与编译期 `PAGE_SIZE` 假设？
- [ ] `mmap()` offset、`mprotect()` 起点和保护范围是否按运行时页计算？
- [ ] 是否把 generic `EINVAL` 与 16 KB 归因需要的额外证据区分开？
- [ ] 是否在 Android 17 fatal 模式覆盖了延迟加载路径？
- [ ] 是否同时在 4 KB 和 16 KB 环境回归？
- [ ] 是否避免依赖 backcompat 作为发布方案？
- [ ] 是否按页大小、ABI、库 build ID 和签名监控灰度？

## 源码与官方资料

- [Android Developers：Support 16 KB page sizes](https://developer.android.com/guide/practices/page-sizes)：Play 要求、工具链、ELF/ZIP 检查、backcompat 与 Android 17 fatal 模式。
- [Android Developers：`<application>` / `android:pageSizeCompat`](https://developer.android.com/guide/topics/manifest/application-element#pageSizeCompat)：manifest 覆盖项的公开契约。
- [AOSP：16 KB page size](https://source.android.com/docs/core/architecture/16kb-page-size/16kb)：平台与内核配置、运行时页编程和系统产物检查。
- [AOSP `attrs_manifest.xml`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/res/values/attrs_manifest.xml)：`pageSizeCompat` 的 `enabled` / `disabled` 枚举定义。
- [AOSP `linker_phdr.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker_phdr.cpp)：LOAD 对齐校验、compat 选择与 fatal 失败路径。
- [AOSP `linker_phdr_16kib_compat.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker_phdr_16kib_compat.cpp)：4 KB ELF 在 16 KB 页上的兼容映射与权限恢复。
- [AOSP `WriteProtected.h`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/private/WriteProtected.h)：bionic 当前的最大页对齐实现。
- [Android Common Kernel `arch/arm64/Kconfig`（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/Kconfig)：`CONFIG_ARM64_16K_PAGES` 的内核配置边界。
- [Android NDK issue #2026](https://github.com/android/ndk/issues/2026)：NDK r27 `WriteProtected` 报错的具体样本及其证据限制。

16 KB 兼容治理要同时回答三个问题：交付物能否安装，所有 ELF 能否原生加载，代码能否在运行时页大小下正确计算。任何一项缺失，都可能让“首页测试通过”变成延迟加载时的线上故障。
