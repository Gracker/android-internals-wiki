#!/usr/bin/env python3
"""Separate the 16 KB page-size owner from the Native DCL owner.

The predecessor 20.7 contains two independently useful articles. The 16 KB
half overlaps the deeper 4.5 owner, while the Android 17 Native DCL half owns a
distinct release, loading and rollback protocol. This transform embeds every
source-only 16 KB increment in 4.5, retains and restructures the DCL material as
20.7, and rewires references without changing the canonical article count.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/part5-app/ch20-stability/07-16kb-native-library-compatibility.md"
DCL_TARGET = ROOT / "src/part5-app/ch20-stability/07-native-dcl-secure-loading.md"
PAGE_TARGET = ROOT / "src/part1-fundamentals/ch04-memory/05-16kb-page-size.md"
MAP_PATH = ROOT / "metadata/2026-08-24-editorial-fusion-v12-map.json"


DCL_FRONTMATTER = """---
title: Native 动态库安全发布、装载与回滚
chapter: '20.7'
section: '20.7'
status: finalized
applicable_versions: Android 14 (API 34) - Android 17 (API 37); System.load writable-file enforcement requires Android 17 with targetSdkVersion 37
last_verified: '2026-08-24'
last_verified_against: Android 17 behavior changes and AOSP android-17.0.0_r1 Runtime, VMRuntime and bionic linker; Android 14 safer DCL and current Android DCL security guidance
confidence: high
sources:
- type: official
  path: https://developer.android.com/about/versions/17/behavior-changes-17#safer-native-dcl-c
- type: official
  path: https://developer.android.com/about/versions/14/behavior-changes-14#safer-dynamic-code-loading
- type: official
  path: https://developer.android.com/privacy-and-security/risks/dynamic-code-loading
- type: official
  path: https://developer.android.com/ndk/guides/jni-tips#native-libraries
- type: official
  path: https://developer.android.com/guide/practices/page-sizes
- type: aosp
  path: https://source.android.com/docs/core/permissions/namespaces_libraries
- type: aosp
  path: https://android.googlesource.com/platform/libcore/+/android-17.0.0_r1/ojluni/src/main/java/java/lang/Runtime.java
- type: aosp
  path: https://android.googlesource.com/platform/libcore/+/android-17.0.0_r1/libart/src/main/java/dalvik/system/VMRuntime.java
- type: aosp
  path: https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/linker/linker.cpp
tags:
- stability
- native
- dynamic-code-loading
- secure-loading
- elf
- system-load
- rollback
- android17
related_chapters:
- '1.10'
- '1.22'
- '4.5'
- '20.3'
- '20.11'
pipeline_stage: finalized
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part5-app/ch20-stability/07-16kb-native-library-compatibility.md
- src/part5-app/ch20-stability/13-android17-native-dcl-stability.md
---
"""


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one marker, found {count}")
    return text.replace(old, new, 1)


def build_dcl_target(source: str) -> str:
    marker = "## Native 库装载、只读约束与安全发布"
    if source.count(marker) != 1:
        raise RuntimeError("DCL source section marker is missing or duplicated")
    body = source.split(marker, 1)[1].lstrip()

    opening_old = (
        "页大小兼容保证 ELF 能被正确映射，发布安全继续约束库文件来源、权限和装载方式。"
        "两组检查都应在安装产物上执行。\n\n"
    )
    opening_new = (
        "Native 动态库能够被 linker 装入，不等于它适合直接发布。应用还要证明文件来自可信来源、"
        "发布过程没有暴露半成品、加载时已不可写，并且新版本失败后能够回到最近一次确认可用的版本。\n\n"
    )
    body = replace_once(body, opening_old, opening_new, "DCL opening")
    body = replace_once(
        body,
        "本章的源码依据为 AOSP（Android Open Source Project，Android 开源项目）`android-17.0.0_r1`。16 KB 页面大小的结论沿用本节前文的 Android 17 基线；这里不重复讨论 Linux 内核实现。",
        "平台实现以 AOSP（Android Open Source Project，Android 开源项目）`android-17.0.0_r1` 为锚点。16 KB 页的 ELF、APK 与运行时兼容检查由 [4.5 16 KB Page Size 与 Android 性能](../../part1-fundamentals/ch04-memory/05-16kb-page-size.md) 统一维护，本文只在独立 `.so` 发布时引用该检查结果。",
        "DCL owner boundary",
    )

    headings = {
        "### 1. 四条加载路径的检查范围": "## Android 17 的 Native DCL 装载边界\n\n### 四条加载路径的检查范围",
        "### 2. `Runtime.load0()` 的检查顺序": "### `Runtime.load0()` 的检查顺序",
        "### 3. 只读检查不等于来源可信": "## 可信发布与回滚协议\n\n### 只读检查不等于来源可信",
        "### 4. 用发布状态机隔离未完成文件": "### 用发布状态机隔离未完成文件",
        "#### 4.1 发布顺序": "#### 发布顺序",
        "#### 4.2 `File.renameTo()` 不是完整的发布事务": "#### `File.renameTo()` 不是完整的发布事务",
        "### 5. ABI、ELF 与动态链接条件": "### ABI、ELF 与动态链接条件",
        "#### 5.1 不要直接取 `Build.SUPPORTED_ABIS[0]`": "#### 不要直接取 `Build.SUPPORTED_ABIS[0]`",
        "#### 5.2 检查 `DT_NEEDED` 与链接器命名空间": "#### 检查 `DT_NEEDED` 与链接器命名空间",
        "#### 5.3 16 KB 页面大小要检查 ELF 程序头": "#### 16 KB 页面大小要检查 ELF 程序头",
        "### 6. 多进程与回滚": "### 多进程与回滚",
        "### 7. 失败分类与处理": "## 故障分类、诊断与发布验证\n\n### 失败分类与处理",
        "### 8. 诊断记录": "### 诊断记录",
        "### 9. Android 17 分阶段测试表": "### Android 17 分阶段测试表",
        "### 10. 与相邻章节的边界": "### 与相邻章节的边界",
    }
    for old, new in headings.items():
        body = replace_once(body, old, new, f"DCL heading {old}")

    body = replace_once(
        body,
        "运行时释放出的独立 `.so` 应按本节前文的 Android 17 规则检查这些字段。",
        "运行时释放出的独立 `.so` 应按 4.5 节的规则检查这些字段。",
        "DCL 16 KB cross-reference",
    )
    body = replace_once(
        body,
        "| 16 KB 不兼容 | ELF `PT_LOAD` 段对齐检查失败或链接器报告对齐错误 | 使用符合本节基线的构建 |",
        "| 16 KB 不兼容 | ELF `PT_LOAD` 段对齐检查失败或链接器报告对齐错误 | 按 4.5 节的工具链与产物基线重新构建 |",
        "DCL failure routing",
    )
    body = replace_once(
        body,
        "- 本章前文讨论 16 KB 页面大小下的 ELF 与 APK 兼容，后续章节只使用对应检查结果。",
        "- 4.5 讨论 16 KB 页下的 ELF、APK 和运行时代码兼容，本文只使用独立 `.so` 的 ELF 检查结果。",
        "DCL neighboring owner boundary",
    )
    body = body.rstrip() + "\n"
    return DCL_FRONTMATTER + "\n# Native 动态库安全发布、装载与回滚\n\n" + body


def build_page_target(text: str) -> str:
    text = replace_once(text, "last_verified: '2026-06-28'", "last_verified: '2026-08-24'", "4.5 verification date")
    text = replace_once(
        text,
        "last_verified_against: developer.android.com page size docs, source.android.com 16KB architecture docs, AOSP android-17.0.0_r1 bionic/linker + libc/private/WriteProtected.h, ARM Architecture Reference Manual",
        "last_verified_against: Android Developers page-size guide updated 2026-08-23 and retrieved 2026-08-24; source.android.com 16 KB architecture docs; AOSP android-17.0.0_r1 bionic/linker and manifest attrs; ARM Architecture Reference Manual",
        "4.5 verification provenance",
    )
    source_marker = (
        "- type: official\n"
        "  path: source.android.com/docs/core/architecture/16kb-page-size/16kb\n"
    )
    source_additions = (
        "- type: official\n"
        "  path: developer.android.com/guide/topics/manifest/application-element#pageSizeCompat\n"
        "- type: official\n"
        "  path: source.android.com/docs/core/architecture/16kb-page-size/16kb-backcompat-option\n"
        "- type: official\n"
        "  path: source.android.com/docs/core/architecture/16kb-page-size/getting-page-size\n"
        "- type: aosp\n"
        "  path: platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/res/values/attrs_manifest.xml\n"
    )
    text = replace_once(text, source_marker, source_marker + source_additions, "4.5 sources")
    text = replace_once(
        text,
        "- research\n"
        "pipeline_stage: ready-to-publish\n",
        "- research\n"
        "- ndk\n"
        "- elf\n"
        "related_chapters:\n"
        "- '1.10'\n"
        "- '20.7'\n"
        "- '25.5'\n"
        "pipeline_stage: finalized\n",
        "4.5 tags and related owners",
    )
    text = replace_once(
        text,
        "task2b_state: fixed\n---",
        "task2b_state: fixed\n"
        "last_consolidated_at: '2026-08-24'\n"
        "consolidated_from:\n"
        "- src/part5-app/ch20-stability/07-16kb-native-library-compatibility.md\n"
        "- src/part5-app/ch20-stability/11-16kb-page-size-native-compatibility.md\n"
        "---",
        "4.5 provenance",
    )

    opening_marker = (
        "2. 更大的基础页能否改善目标应用的性能。\n\n"
        "第一个问题有明确的工程检查项；第二个问题必须测量。"
    )
    opening_replacement = (
        "2. 更大的基础页能否改善目标应用的性能。\n\n"
        "Google Play 当前要求目标版本为 Android 15（API 35）或更高的应用支持 64 位设备上的 16 KB 页；"
        "从 2027 年 2 月 1 日起，不支持 16 KB 页的应用更新将无法发布。这里判断的是 `targetSdkVersion` 与最终分发产物，不能用测试设备的系统版本代替。\n\n"
        "第一个问题有明确的工程检查项；第二个问题必须测量。"
    )
    text = replace_once(text, opening_marker, opening_replacement, "4.5 current Play requirement")

    text = replace_once(
        text,
        "unzip -l app-release.apk | grep '\\.so$'",
        "unzip -Z1 app-release.apk | grep -E '^lib/[^/]+/[^/]+[.]so$'",
        "4.5 APK native inventory",
    )
    agp_marker = (
        "AGP 8.3 到 8.5 可能已经生成满足要求的 ELF，但 bundletool 默认生成的 Play APK 仍可能缺少正确的 ZIP 对齐。"
        "不要根据本地 `.so` 检查结果推断 Play 分发产物一定可安装。"
    )
    agp_addition = (
        agp_marker
        + "\n\n暂时无法升级到 AGP 8.5.1+ 时，可按官方迁移方案启用 `useLegacyPackaging`，把共享库压缩进 APK 并在安装时解压。"
        "这种过渡方式会增加安装后占用，也可能在存储紧张时提高安装失败风险，不能代替工具链升级。"
        "若 NDK r27 项目出现与 `WriteProtected` 相关的报告，应保存完整错误、构建参数和库 Build ID，再与 NDK r28+ 全量重编结果对照；单个 issue 样本不能证明所有 r27 静态库都不兼容。"
    )
    text = replace_once(text, agp_marker, agp_addition, "4.5 legacy toolchain route")

    elf_marker = "### 3.3 检查 ELF 程序头\n\n以下命令用于查看每个可加载段的对齐值："
    elf_replacement = (
        "### 3.3 检查 ELF 程序头\n\n"
        "Android 官方提供 `check_elf_alignment.sh` 扫描 APK 内的共享库，并用 `ALIGNED` / `UNALIGNED` 标出结果。"
        "发布检查至少覆盖 `arm64-v8a` 与 `x86_64`，两种 ABI 都不能留下 `UNALIGNED`；CI 应固定一份已经审核的官方脚本版本。\n\n"
        "需要手工复核时，以下命令用于查看每个可加载段的对齐值："
    )
    text = replace_once(text, elf_marker, elf_replacement, "4.5 official ELF checker")

    manifest_marker = (
        "应用也可以在清单文件中通过 `android:pageSizeCompat` 为单个应用启用或禁用向后兼容。"
        "兼容模式适合迁移和诊断；发布前仍应让所有原生产物直接满足 16 KiB 要求。"
    )
    manifest_replacement = (
        "应用也可以在使用 Android 16 SDK 或更高版本编译时，通过 `<application>` 上的 `android:pageSizeCompat` 控制单个应用：\n\n"
        "```xml\n"
        "<application\n"
        "    android:pageSizeCompat=\"disabled\"\n"
        "    ... />\n"
        "```\n\n"
        "AOSP `attrs_manifest.xml` 将该属性定义为 `enabled` / `disabled` 枚举。`enabled` 可强制启用兼容路径并隐藏首次提示，适合迁移诊断；"
        "`disabled` 适合让未适配 ELF 在测试阶段直接失败。这个属性只控制兼容模式，不是合格证明；发布前仍应让所有原生产物直接满足 16 KiB 要求。"
    )
    text = replace_once(text, manifest_marker, manifest_replacement, "4.5 manifest control")

    verification_marker = (
        "期望看到 `PAGE_ALIGNMENT_16K`。最终仍应在 Play Console 的 App Bundle Explorer 中检查平台生成的 APK，"
        "因为用户安装的是 Play 拆分后的产物。"
    )
    verification_replacement = (
        verification_marker
        + "\n\n发布记录应保存主 APK、各设备 split、其他渠道包、加固或重签名后产物的哈希，以及逐 ABI 的 ELF、ZIP 和 AAB 检查结果。"
        "构建目录中的 `.so` 通过，不能替代对最终交付物的验收。"
    )
    text = replace_once(text, verification_marker, verification_replacement, "4.5 release evidence")

    text = replace_once(
        text,
        "- **2025 年 11 月 1 日**：Google Play 要求面向 Android 15 / API 35 及以上的 64 位新应用和更新支持 16 KiB 页。",
        "- **2027 年 2 月 1 日**：Google Play 将阻止不支持 64 位设备 16 KB 页、且目标版本为 Android 15 / API 35 或更高的应用更新继续发布。",
        "4.5 Play milestone",
    )

    reference_marker = "- [AOSP：16 KB page size](https://source.android.com/docs/core/architecture/16kb-page-size/16kb)\n"
    reference_additions = (
        "- [Android Developers：`android:pageSizeCompat`](https://developer.android.com/guide/topics/manifest/application-element#pageSizeCompat)\n"
        "- [AOSP：Enable 16 KB backcompat option](https://source.android.com/docs/core/architecture/16kb-page-size/16kb-backcompat-option)\n"
    )
    text = replace_once(text, reference_marker, reference_marker + reference_additions, "4.5 reference additions")
    return text


def remap_related(text: str, replacements: dict[str, list[str]]) -> str:
    match = re.search(r"(?m)^related_chapters:\n((?:- .*\n)+)", text)
    if not match:
        raise RuntimeError("related_chapters block missing")
    values = []
    for line in match.group(1).splitlines():
        value_match = re.fullmatch(r"- ['\"](\d+\.\d+)['\"]", line.strip())
        if not value_match:
            raise RuntimeError(f"unexpected related_chapters line: {line}")
        value = value_match.group(1)
        values.extend(replacements.get(value, [value]))
    deduped = list(dict.fromkeys(values))
    block = "".join(f"- '{value}'\n" for value in deduped)
    return text[: match.start(1)] + block + text[match.end(1) :]


def update_reference(path: Path, text: str) -> str:
    if path == ROOT / "src/SUMMARY.md":
        return replace_once(
            text,
            "  - [20.7 16 KB Page Size 与 Native 动态库兼容](part5-app/ch20-stability/07-16kb-native-library-compatibility.md)",
            "  - [20.7 Native 动态库安全发布、装载与回滚](part5-app/ch20-stability/07-native-dcl-secure-loading.md)",
            "SUMMARY 20.7",
        )

    if path == ROOT / "src/part5-app/ch20-stability/README.md":
        text = replace_once(
            text,
            "- [20.7 16 KB Page Size 与 Native 动态库兼容](07-16kb-native-library-compatibility.md)",
            "- [20.7 Native 动态库安全发布、装载与回滚](07-native-dcl-secure-loading.md)",
            "chapter 20 index",
        )
        text = replace_once(
            text,
            "| 16 KB Page Size | 系统以 16 KB 作为基础内存页大小。Native 库的 ELF（可执行文件和动态库采用的文件格式）对齐、打包和运行时假设都要兼容这一配置。 |",
            "| 16 KB Page Size | 系统以 16 KB 作为基础内存页大小。ELF 对齐、打包和运行时假设的统一检查见 [4.5](../../part1-fundamentals/ch04-memory/05-16kb-page-size.md)。 |",
            "chapter 20 16 KB glossary",
        )
        text = replace_once(
            text,
            "| DCL | Dynamic Code Loading，动态代码加载。本章 20.7 关注运行时写入或下载 Native 动态库后再调用 `System.load()` 的场景。 |",
            "| DCL | Dynamic Code Loading，动态代码加载。20.7 关注 Native 动态库的可信发布、Android 17 `System.load()` 只读约束与回滚。 |",
            "chapter 20 DCL glossary",
        )
        return text

    if path == ROOT / "src/part5-app/ch25-power-size/05-apk-r8-resource-optimization.md":
        text = remap_related(text, {"20.7": ["4.5"]})
        return replace_once(
            text,
            "- [20.7 16 KB Page Size 与 Native 动态库兼容](../ch20-stability/07-16kb-native-library-compatibility.md)：ELF/ZIP 检查、兼容模式和故障归因。",
            "- [4.5 16 KB Page Size 与 Android 性能](../../part1-fundamentals/ch04-memory/05-16kb-page-size.md)：ELF/ZIP 检查、兼容模式和故障归因。",
            "25.5 16 KB owner link",
        )

    if path == ROOT / "src/part5-app/ch21-startup/07-art-gc-suppression-startup-performance.md":
        return remap_related(text, {"20.7": ["4.5"]})

    if path == ROOT / "src/part5-app/ch26-observability/14-heapprofd-procfs-page-fault.md":
        return remap_related(text, {"20.7": ["4.5"]})

    if path == ROOT / "src/part1-fundamentals/ch01-architecture/10-jni-ndk-bionic-performance.md":
        text = remap_related(text, {"20.7": ["4.5", "20.7"]})
        text = replace_once(
            text,
            "从 2025-11-01 起，提交到 Google Play、且面向 Android 15 / API 35 及以上设备的新应用和更新必须支持 16KB 内存页。",
            "Google Play 当前要求目标版本为 Android 15 / API 35 或更高的应用支持 64 位设备上的 16 KB 页；从 2027-02-01 起，不支持的应用更新将无法发布。",
            "1.10 Play policy",
        )
        return replace_once(
            text,
            "Native Heap 与 Scudo 的进一步分析见 **23.3 Native 内存管理与优化**；16 KB 页的系统影响见 **4.5 16 KB Page Size 与 Android 性能**；MTE 与 16 KB Native 兼容性处理分别见 **20.6 MTE 与 GWP-ASan Native 内存安全检测** 与 **20.7 16 KB Native 兼容性**。",
            "Native Heap 与 Scudo 的进一步分析见 **23.3 Native 内存管理与优化**；16 KB 页的系统影响与兼容验收见 **4.5 16 KB Page Size 与 Android 性能**；MTE 检测见 **20.6 MTE 与 GWP-ASan Native 内存安全检测**；运行时下载或释放 `.so` 的发布协议见 **20.7 Native 动态库安全发布、装载与回滚**。",
            "1.10 neighboring owners",
        )

    if path == ROOT / "src/part5-app/ch20-stability/03-native-crash-unwinding-symbolication.md":
        text = remap_related(text, {"20.7": ["20.7", "4.5"]})
        text = replace_once(
            text,
            "Native 库兼容性检查见 20.7。",
            "16 KB 页兼容检查见 4.5；运行时发布库的只读装载与回滚见 20.7。",
            "20.3 Native compatibility routing",
        )
        return replace_once(
            text,
            "- 20.7：16 KB 页下的 ELF、打包和第三方库兼容。",
            "- 4.5：16 KB 页下的 ELF、打包和运行时代码兼容。\n- 20.7：运行时发布 Native 库的只读装载、可信来源和回滚。",
            "20.3 neighboring owner list",
        )

    if path == ROOT / "src/part1-fundamentals/ch01-architecture/01-android-architecture-process-threading.md":
        return replace_once(
            text,
            "Google Play 自 2025 年 11 月 1 日起要求面向 Android 15 及以上设备的新应用和更新支持 16 KB 页大小。",
            "Google Play 当前要求目标版本为 Android 15 / API 35 或更高的应用支持 64 位设备上的 16 KB 页；从 2027 年 2 月 1 日起，不支持的应用更新将无法发布。",
            "1.1 Play policy",
        )

    if path == ROOT / "src/part1-fundamentals/ch01-architecture/04-version-evolution.md":
        return replace_once(
            text,
            "Google Play 从 2025 年 11 月 1 日起，要求面向 Android 15 及以上设备的新应用和更新支持 16 KB 内存页。",
            "Google Play 当前要求目标版本为 Android 15 / API 35 或更高的应用支持 64 位设备上的 16 KB 页；从 2027 年 2 月 1 日起，不支持的应用更新将无法发布。",
            "1.4 Play policy",
        )

    return text


def h2_inventory(text: str) -> list[str]:
    return [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]


def heading_inventory(text: str, start: str) -> list[str]:
    section = text.split(start, 1)[1]
    return [line.lstrip("# ") for line in section.splitlines() if re.match(r"^#{2,4} ", line)]


def validate(changed: dict[Path, str]) -> None:
    page_needles = [
        "`check_elf_alignment.sh`",
        "`arm64-v8a` 与 `x86_64`",
        "`useLegacyPackaging`",
        "android:pageSizeCompat=\"disabled\"",
        "2027 年 2 月 1 日",
        "构建目录中的 `.so` 通过，不能替代对最终交付物的验收",
        "NDK r27 项目出现与 `WriteProtected` 相关的报告",
    ]
    dcl_needles = [
        "## Android 17 的 Native DCL 装载边界",
        "## 可信发布与回滚协议",
        "`STAGED -> VERIFIED -> PUBLISHED -> SELECTED -> LOADED`",
        "Attempt to load writable file",
        "#### `File.renameTo()` 不是完整的发布事务",
        "## 故障分类、诊断与发布验证",
        "last-known-good",
    ]
    missing = [needle for needle in page_needles if needle not in changed[PAGE_TARGET]]
    missing += [needle for needle in dcl_needles if needle not in changed[DCL_TARGET]]
    if missing:
        raise RuntimeError(f"missing routed 16 KB/DCL concepts: {missing}")

    forbidden_dcl = [
        "## ELF 对齐、打包与 16 KB 设备验证",
        "`check_elf_alignment.sh`",
        "`useLegacyPackaging`",
        "Google Play 当前要求：目标版本为 Android 15",
    ]
    leaked = [needle for needle in forbidden_dcl if needle in changed[DCL_TARGET]]
    if leaked:
        raise RuntimeError(f"16 KB owner material still duplicated in DCL target: {leaked}")

    for path, body in changed.items():
        if path.suffix != ".md":
            continue
        if "](07-16kb-native-library-compatibility.md)" in body or "/07-16kb-native-library-compatibility.md)" in body:
            raise RuntimeError(f"live Markdown link still points to predecessor: {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not SOURCE.exists() or not PAGE_TARGET.exists():
        raise SystemExit("Expected predecessor and 4.5 owner must both exist")
    if DCL_TARGET.exists():
        raise SystemExit(f"DCL target already exists: {DCL_TARGET}")

    originals = {
        SOURCE: SOURCE.read_text(encoding="utf-8"),
        PAGE_TARGET: PAGE_TARGET.read_text(encoding="utf-8"),
    }
    changed: dict[Path, str] = {
        DCL_TARGET: build_dcl_target(originals[SOURCE]),
        PAGE_TARGET: build_page_target(originals[PAGE_TARGET]),
    }

    for path in sorted((ROOT / "src").rglob("*.md")):
        if path in {SOURCE, PAGE_TARGET}:
            continue
        original = path.read_text(encoding="utf-8")
        updated = update_reference(path, original)
        if updated != original:
            changed[path] = updated

    validate(changed)

    result = {
        "version": 12,
        "operation": "16kb_page_size_and_native_dcl_owner_split",
        "count_change": {"before": 278, "after": 278},
        "merged_paths": [
            {
                "source": str(SOURCE.relative_to(ROOT)),
                "target": str(PAGE_TARGET.relative_to(ROOT)),
                "role": "canonical_16kb_page_size_build_runtime_and_performance_owner",
            },
            {
                "source": str(SOURCE.relative_to(ROOT)),
                "target": str(DCL_TARGET.relative_to(ROOT)),
                "role": "native_dcl_secure_publish_load_and_rollback_owner",
            },
        ],
        "rewritten_paths": [
            str(PAGE_TARGET.relative_to(ROOT)),
            str(DCL_TARGET.relative_to(ROOT)),
        ],
        "renamed_paths": [
            {"from": str(SOURCE.relative_to(ROOT)), "to": str(DCL_TARGET.relative_to(ROOT))}
        ],
        "reindexed_paths": [
            {"from": str(SOURCE.relative_to(ROOT)), "to": str(DCL_TARGET.relative_to(ROOT))}
        ],
        "source_bytes": {
            str(path.relative_to(ROOT)): len(body.encode("utf-8"))
            for path, body in originals.items()
        },
        "result_bytes": {
            str(path.relative_to(ROOT)): len(changed[path].encode("utf-8"))
            for path in (PAGE_TARGET, DCL_TARGET)
        },
        "source_sha256": {
            str(path.relative_to(ROOT)): digest(body) for path, body in originals.items()
        },
        "result_sha256": {
            str(path.relative_to(ROOT)): digest(changed[path])
            for path in (PAGE_TARGET, DCL_TARGET)
        },
        "source_h2_inventory": h2_inventory(originals[SOURCE]),
        "dcl_source_heading_inventory": heading_inventory(
            originals[SOURCE], "## Native 库装载、只读约束与安全发布"
        ),
        "content_routes": [
            {
                "source": "20.7 ELF alignment, APK/AAB packaging, runtime page math and compatibility mode",
                "destination": "4.5 application compatibility and migration sections",
                "treatment": "duplicate_exposition_deduplicated_against_deeper_owner",
            },
            {
                "source": "official ELF checker, ABI scope, legacy AGP packaging fallback and NDK r27 issue boundary",
                "destination": "4.5 toolchain and ELF verification sections",
                "treatment": "source_only_release_details_embedded",
            },
            {
                "source": "pageSizeCompat enum behavior, release artifact evidence and current Play milestone",
                "destination": "4.5 compatibility mode, release evidence and milestone sections",
                "treatment": "source_only_manifest_and_policy_details_embedded_and_updated",
            },
            {
                "source": "Android 17 System.load writable-file enforcement and four loading paths",
                "destination": "20.7 Android 17 Native DCL loading boundary",
                "treatment": "retained_and_promoted_to_real_owner_section",
            },
            {
                "source": "signed manifest, immutable version path, staged publish protocol and Kotlin example",
                "destination": "20.7 trusted publish and rollback protocol",
                "treatment": "retained_without_summary_loss",
            },
            {
                "source": "ABI, DT_NEEDED, multiprocess recovery, failure taxonomy, diagnostics and test matrix",
                "destination": "20.7 publish protocol and verification sections",
                "treatment": "retained_and_restructured",
            },
            {
                "source": "cross-chapter references and stale Play policy statements",
                "destination": "SUMMARY, chapter index, 4.5/20.7 related owners and affected articles",
                "treatment": "semantic_owner_links_reconciled_and_policy_updated",
            },
        ],
        "updated_reference_files": [
            str(path.relative_to(ROOT))
            for path in sorted(changed)
            if path not in {PAGE_TARGET, DCL_TARGET}
        ],
        "applied": args.apply,
    }

    if args.apply:
        for path, body in changed.items():
            path.write_text(body, encoding="utf-8")
        SOURCE.unlink()
        MAP_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
