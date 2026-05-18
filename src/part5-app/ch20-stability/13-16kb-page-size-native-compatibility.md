---
title: "16KB Page Size 兼容性与 Native 崩溃治理"
chapter: "20.13"
status: ready-for-review
drafted_date: "2026-05-18"
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
related_chapters: ["4.7", "20.3", "20.11", "23.3", "25.6"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-18"
gap_source: "素材驱动/官方文档/AOSP结构/Clippings结构参考"
source_refs:
  - "[结构参考: Clippings/Android 应用稳定性剖析与优化 - ELF 文件与 readelf & objdump ：了解 ELF 格式与解析工具.md]"
  - "[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Crash 监控：为我们应用插上监控 Native Crash 的电子眼.md]"
  - "[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Hook 全解析：Native 闯关入门秘籍.md]"
  - "OpenClaw定时任务/AutoResearchClaw调研报告/2026-04-30-android-16kb-page-size-hook-library-compatibility.md"
  - "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-02-android-16kb-page-size-ndk-compatibility.md"
  - "DeepResearch/2026-05-08-16kb-page-size-third-party-library-impact.md"
  - "https://developer.android.com/guide/practices/page-sizes"
  - "https://source.android.com/docs/core/architecture/16kb-page-size/16kb"
  - "https://source.android.com/docs/core/architecture/16kb-page-size/16kb-backcompat-option"
---

# 20.13 16KB Page Size 兼容性与 Native 崩溃治理

## 要点

### 🔹 16KB Page Size 在稳定性治理里的边界

16KB Page Size 对应用稳定性的影响集中在 native 依赖：自研 `.so`、预编译 `.so`、静态链接库、Prefab 包、游戏引擎插件、Hook / APM SDK。纯 Java / Kotlin 应用通常不需要处理 ELF 对齐；只要依赖树里混入 native SDK，仍要把它纳入排查清单。[已验证: 官方文档, developer.android.com/guide/practices/page-sizes]

治理目标不是把所有 native crash 都归因到页大小，而是把 16KB 设备上的安装失败、`dlopen` 失败、`UnsatisfiedLinkError`、`mprotect ... Invalid argument` 和 Play 预发布验证失败拆成可验证的几类证据。页大小是一个环境变量，崩溃归因还要同时看 ABI、NDK 版本、链接参数、三方 SDK 版本和设备系统镜像。

### 🔹 ELF `PT_LOAD` 对齐与 Play 合规检查

16KB 设备加载 native 库时，`PT_LOAD` segment 的对齐值要覆盖 16KB 页面。工程侧最常用的判断是两层：ELF 内部的 `p_align`，以及 APK / AAB 产物里未压缩 `.so` 的 ZIP 边界对齐。前者决定 linker 能否按 16KB 页面映射 `.so`，后者决定安装包在设备侧能否直接 mmap 未压缩库文件。

本地检查 ELF 时，重点看 `LOAD` 行的 `align` 是否至少为 `2**14` / `0x4000` / `16384`。同时检查 `p_vaddr` 与 `p_offset` 对齐关系；二者不同余时，即使 `p_align` 写得足够大，也可能在加载时失败。APK 层面用 Build Tools 35.0.0+ 的 `zipalign -c -P 16 -v 4 app.apk` 检查 16KB 边界。[已验证: 官方文档, developer.android.com/guide/practices/page-sizes]

这段脚本适合放进 CI，在打包后扫描 APK 中的 arm64 / x86_64 `.so`，发现 4KB 对齐库时直接失败：

```bash
#!/usr/bin/env bash
set -euo pipefail

APK="$1"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

unzip -q "$APK" 'lib/*/*.so' -d "$WORK_DIR"

fail=0
while IFS= read -r so; do
  if ! llvm-readelf -l "$so" | awk '
    /LOAD/ { if ($NF != "0x4000" && $NF != "0x10000" && $NF != "0x20000") bad=1 }
    END { exit bad ? 1 : 0 }
  '; then
    echo "[16KB] ELF alignment check failed: $so" >&2
    fail=1
  fi
done < <(find "$WORK_DIR/lib" -name '*.so' -print)

exit "$fail"
```

脚本只负责发现明显不合规的 ELF；ZIP 对齐、AAB 经 bundletool 生成后的 APK 对齐、Play Console 预发布验证仍要单独跑。AGP 8.3 到 8.5 的默认对齐和 Play 侧 bundletool 行为存在差异，不能只用本地 debug APK 代替上架产物。[已验证: 官方文档, developer.android.com/guide/practices/page-sizes]

### 🔹 NDK、AGP 与链接器参数的升级路径

AGP 8.5.1+ 与 NDK r28+ 是当前最稳的默认路径：AGP 负责未压缩 `.so` 的 16KB ZIP 边界，NDK r28+ 默认打开 16KB ELF 对齐能力。旧工具链仍可通过链接器参数补齐，但要确认参数传到了每一个产物，而不是只传给主工程 CMake。[已验证: 官方文档, developer.android.com/guide/practices/page-sizes]

CMake 工程通常把参数放到 `target_link_options()`，避免全局变量被子工程覆盖：

```cmake
if(ANDROID_ABI STREQUAL "arm64-v8a" OR ANDROID_ABI STREQUAL "x86_64")
  target_link_options(app_native PRIVATE
    "-Wl,-z,max-page-size=16384"
    "-Wl,-z,common-page-size=16384")
endif()
```

这段配置能覆盖当前 target；Prefab 包、React Native 模块、Unity / Unreal 插件、闭源 SDK 通常有自己的构建入口。CI 仍要扫描最终 APK，不以 Gradle 配置存在作为通过依据。

ndk-build 项目可在 `Android.mk` 中追加链接参数：

```makefile
LOCAL_LDFLAGS += -Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384
```

旧代码里还要清掉对 `PAGE_SIZE == 4096` 的假设。NDK r27+ 在 16KB 模式下已经弱化对编译期 `PAGE_SIZE` 的依赖，应用代码应改用 `sysconf(_SC_PAGESIZE)` 或 `getpagesize()` 获取运行时页大小。若某个常量只是业务缓冲区尺寸，不应继续命名为 `PAGE_SIZE`，否则排查时很难区分“页面大小”和“恰好取 4096 的块大小”。[已验证: AOSP docs, source.android.com/docs/core/architecture/16kb-page-size/getting-page-size]

### 🔹 NDK r27 `WriteProtected` 崩溃路径

NDK r27 有一类特殊风险：静态链接 `libc.a` 的 native 库可能命中 bionic `WriteProtected` 的旧实现。公开 issue 中的典型错误是 `WriteProtected mprotect 1 failed: Invalid argument`，影响范围包含 arm64-v8a、ndk-build 和 r27 版本；维护者回复该问题已修复，r28 路径可避开这类崩溃。[引用: https://github.com/android/ndk/issues/2026]

归因时按这条路径查：

```text
16KB 设备启动应用
  -> 加载静态链接旧 libc.a 的 native 产物
  -> bionic WriteProtected 保护页调用 mprotect
  -> 传入长度或边界仍按 4KB 假设处理
  -> 16KB 内核返回 EINVAL
  -> 进程在加载阶段终止
```

这类崩溃和普通 `SIGSEGV` 不同。`SIGSEGV` 多发生在非法地址访问，MTE 崩溃会带有 tag mismatch 相关信息，业务 native 崩溃通常能还原到应用符号。`WriteProtected mprotect ... Invalid argument` 的入口更靠前，常出现在库加载阶段，堆栈里会混入 linker / bionic 相关帧。处理策略也不同：优先重编所有 native 产物并升级到 NDK r28+，而不是在信号处理器里兜底。

### 🔹 Hook、监控 SDK 与 legacy native 库分层排查

Hook / APM SDK 不能按“有 mprotect 调用就高风险”处理。PLT Hook、inline Hook、native crash 监控都会操作代码页或信号处理器，但 16KB 风险来自两件事：产物是否满足 ELF / ZIP 对齐，运行时是否按实际页大小计算 `mprotect` 边界。[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Hook 全解析：Native 闯关入门秘籍.md]

依赖排查可分三层：

- legacy native 库：闭源 SDK、长期未升级的 `.a` / `.so`、静态链接 NDK r27 `libc.a` 的产物优先排查。这类库缺少源码，升级 SDK 或要求供应商重编通常比本地绕过更可靠。
- 中间构建产物：Prefab、React Native codegen、Unity / Unreal 插件、自定义 Gradle task 生成的库要看最终 APK。主工程 CMake 参数不保证传到这些产物。[来源: DeepResearch/2026-05-08-16kb-page-size-third-party-library-impact.md]
- 已适配 SDK：公开资料显示 ByteHook / ShadowHook 等库已有 16KB 对齐配置或版本说明，但仍要以接入版本和最终产物为准。Hook 框架自身可通过 `sysconf(_SC_PAGESIZE)` 对齐 `mprotect` 边界，不能只看库名做判断。[来源: OpenClaw定时任务/AutoResearchClaw调研报告/2026-04-30-android-16kb-page-size-hook-library-compatibility.md]

排查结果要写入依赖清单：库名、来源、版本、ABI、构建系统、NDK 版本、是否闭源、ELF 对齐结果、ZIP 对齐结果、供应商修复版本。只记录“已升级”不够，线上崩溃回溯时无法知道升级覆盖了哪一个 `.so`。

### 🔹 线上崩溃识别与灰度兜底

线上侧要把 16KB 当成崩溃聚合维度，而不是事后人工搜索日志。崩溃事件里至少带上这些字段：

- `page_size`: 应用进程内通过 `sysconf(_SC_PAGESIZE)` 采集，值为 `4096` 或 `16384`。
- `abi`: 设备 ABI 与崩溃 `.so` ABI，用于区分 arm64-v8a、x86_64、32 位兼容包。
- `native_lib`: 崩溃或加载失败的库名，包含版本、来源 SDK、是否闭源。
- `toolchain`: AGP、NDK、CMake / ndk-build、Prefab / RN / Unity / Unreal 版本。
- `signature`: `UnsatisfiedLinkError`、`dlopen failed`、`WriteProtected mprotect`、`Invalid argument`、tombstone signal。
- `release_gate`: Play pre-launch 结果、CI ELF 扫描结果、ZIP 对齐扫描结果、灰度批次。

聚合规则可按“设备页大小 + 错误签名 + native 库 + SDK 版本”建主键。示例规则如下：

```json
{
  "rule": "native_16kb_compat",
  "match": {
    "page_size": 16384,
    "any_signature": [
      "UnsatisfiedLinkError",
      "dlopen failed",
      "WriteProtected mprotect",
      "Invalid argument"
    ]
  },
  "group_by": ["native_lib", "abi", "ndk_version", "sdk_vendor", "sdk_version"],
  "action": "block_next_gray_batch"
}
```

这条规则不替代 native crash 符号化。它的作用是把 16KB 环境下的加载失败和早期崩溃从普通 native crash 里分出来，给灰度系统一个明确的暂停信号。若同一版本只在 16KB 设备上出现 `dlopen failed`，优先回看产物扫描；若 4KB 与 16KB 设备同时出现相同 `SIGSEGV`，归因应回到 20.3 的 tombstone 和符号化流程。

### 🔹 兼容性验证流水线

16KB 验证要按产物生成顺序布置，越早发现越便宜：

| 阶段 | 检查对象 | 能发现的问题 | 容易漏掉的问题 |
|------|----------|--------------|----------------|
| 本地开发 | 16KB emulator / Pixel 9a，`adb shell getconf PAGE_SIZE` | 基础启动、`dlopen`、明显的 `mprotect EINVAL` | AAB 经 Play 生成后的 APK 对齐 |
| CI 打包 | 最终 APK / universal APK / split APK | ELF `PT_LOAD` 对齐、ZIP 16KB 边界、闭源 `.so` 漏扫 | Play pre-launch 设备差异、灰度真实机型差异 |
| Play 预发布验证 | Play Console 生成产物 | 上架合规、安装失败、设备兼容提示 | 自建渠道包、动态下发插件 |
| 灰度发布 | 16KB 设备分桶指标 | 真实用户崩溃率、特定 SDK 版本异常 | 样本量不足、设备厂商分布偏斜 |
| 线上告警 | Native crash / Java exception / install failure | 版本级回滚判断、供应商库定位 | 未采集页大小字段导致无法分组 |

本地测试的最低门槛是确认运行环境：

```bash
adb shell getconf PAGE_SIZE
# 期望输出: 16384
```

开发者选项里的 16KB toggle 能做兼容性测试，但它不等价于所有真实 16KB 设备的性能表现。性能收益、内存占用变化、TLB 与 page fault 的机制分析放在 4.7 节；这里的验证目标是应用能安装、能加载 native 库、能在灰度中被及时拦截。[已验证: AOSP docs, source.android.com/docs/core/architecture/16kb-page-size/16kb-developer-option]

## 扩展

### 🔸 bionic 16KB app compat mode 的安全代价

AOSP 提供 16KB backcompat option，`bionic.linker.16kb.app_compat.enabled` 控制库加载兼容行为，`pm.16kb.app_compat.disabled` 控制 APK 安装侧兼容行为。它用于让部分 4KB 对齐应用在 16KB 设备上过渡运行；官方仍建议应用产物本身满足 16KB 对齐。[已验证: AOSP docs, source.android.com/docs/core/architecture/16kb-page-size/16kb-backcompat-option]

这不是长期方案。兼容模式可能改变 linker 对旧库的加载方式，并带来 RELRO 保护退化等安全代价。灰度期间可以把它当作定位开关：打开后崩溃消失，说明问题接近 ELF / 加载兼容；关闭后复现，则继续追具体 `.so`。发布版本不能依赖设备侧属性兜底，用户设备和 Play 审核环境都不受应用控制。

### 🔸 React Native、Unity、Unreal 的 native 依赖清单化

跨平台框架的风险在“生成了很多 native 产物，但参数入口不在主工程”。React Native 的 Prefab / codegen 模块、Unity IL2CPP 插件、Unreal 第三方插件、广告 SDK 和监控 SDK 都要按最终 APK 扫描。清单字段至少包括：产物路径、来源模块、构建入口、NDK 版本、ABI、是否闭源、是否可重编、扫描结果、供应商修复版本。

清单化之后，升级顺序更清楚：可重编的自研库先升级 NDK / AGP 并重建；闭源 SDK 要求供应商提供 16KB 声明和新版本；动态下发插件纳入同一套扫描；灰度中把 SDK 版本写进崩溃事件。Unity / Unreal 的具体兼容状态仍需以项目实际引擎版本和插件版本验证，不能只根据引擎名称判断。[待验证: Unity / Unreal 不同版本的 NDK r27 静态链接覆盖范围]

### 🔸 与 4.7 机制篇的交叉引用

页大小、TLB、页表、page fault、bionic linker 兼容模式内部实现详见 4.7 节。20.13 只保留应用侧治理动作：产物扫描、工具链升级、依赖清单、线上归因和灰度拦截。Native crash 信号处理、tombstone、符号化详见 20.3；MTE tag mismatch 归因详见 20.11；`.so` 装载成本与 native 内存治理详见 23.3；APK / AAB 体积和 split 产物分析详见 25.6。

## 参考资料

- [结构参考: Clippings/Android 应用稳定性剖析与优化 - ELF 文件与 readelf & objdump ：了解 ELF 格式与解析工具.md]
- [结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Crash 监控：为我们应用插上监控 Native Crash 的电子眼.md]
- [结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Hook 全解析：Native 闯关入门秘籍.md]
- [引用: https://developer.android.com/guide/practices/page-sizes]
- [引用: https://source.android.com/docs/core/architecture/16kb-page-size/16kb]
- [引用: https://source.android.com/docs/core/architecture/16kb-page-size/16kb-backcompat-option]
- [引用: https://source.android.com/docs/core/architecture/16kb-page-size/getting-page-size]
- [引用: https://github.com/android/ndk/issues/2026]
- [来源: OpenClaw定时任务/AutoResearchClaw调研报告/2026-04-30-android-16kb-page-size-hook-library-compatibility.md]
- [来源: OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-02-android-16kb-page-size-ndk-compatibility.md]
- [来源: DeepResearch/2026-05-08-16kb-page-size-third-party-library-impact.md]
