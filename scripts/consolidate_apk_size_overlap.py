#!/usr/bin/env python3
"""Fuse the overlapping APK/R8 overview into the deep size article.

The resulting canonical article keeps the established 25.5 entry point and
absorbs the DEX/Native/resource depth formerly published as 25.12.  This is an
editorial transform, not a concatenation: only source material that adds a
distinct responsibility is inserted; already-covered R8/resource passages are
represented by the deeper target sections.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "src/part5-app/ch25-power-size/05-apk-r8-resource-optimization.md"
DEEP = ROOT / "src/part5-app/ch25-power-size/12-dex-native-resource-size.md"
MAP_PATH = ROOT / "metadata/2026-08-24-editorial-fusion-v7-map.json"

NEW_TITLE = "应用体积分析与优化：DEX、Native SO 与资源"

GENERAL_SECTION = r"""
## 先统一制品与体积口径

体积治理不能从“删哪个目录”开始。先要固定用户拿到哪组 APK、下载多少字节、安装后占用多少空间，以及运行时映射了哪些页；这四个结果可能沿不同方向变化。

### APK 是带平台约束的 ZIP

APK 使用 ZIP 组织文件，但目录结构不能替代 Android 的安装和加载语义：

- `classes*.dex` 保存字节码。单个 DEX 的 `method_ids`（方法引用 ID 表）上限是 65,536，不是整个应用只能定义 65,536 个方法；
- `resources.arsc` 与 `res/` 组成编译资源，`assets/` 保存按原始文件接口读取的内容。静态缩减器不能仅凭业务代码判断所有 asset 是否仍被使用；
- `lib/<abi>/` 保存各 ABI（应用二进制接口）的 ELF（Executable and Linkable Format，可执行与可链接格式）库。条目是否压缩会同时影响下载字节、安装期提取和直接映射条件；
- V1/JAR 签名会在 `META-INF/` 生成清单与签名文件，V2/V3 签名位于 APK Signing Block（APK 签名块），V4 还使用独立的 `.idsig` 文件。看到 `META-INF/` 不能反推出制品只采用 V1。

未压缩条目会让 APK 文件变大，却可能避免安装期提取或支持直接映射。因此，单看 ZIP 中某个文件的字节数，不能判定下载、安装或内存是否一起改善。

### 四种数字不能互相替代

| 口径 | 回答的问题 | 常见误读 |
|---|---|---|
| 上传制品 | APK 或 AAB（Android App Bundle）本身多大 | 把 AAB 大小当作任意设备的下载量 |
| 设备交付集合 | 固定 ABI、语言、密度、SDK 与模块后，设备会获得哪些 split APK（拆分包） | 用 universal APK 代表 Play 的设备专用交付 |
| 安装占用 | 已安装 APK、提取的原生库、ART 编译产物、应用数据与缓存共占多少 | 认为下载减少 1 MB，安装空间必然同步减少 1 MB |
| 运行时映射 | DEX、SO、资源的文件页、私有脏页和共享页如何进入进程 | 用磁盘文件大小直接推导 PSS（按共享比例分摊的物理内存） |

普通单 APK 渠道交付一个完整 APK；App Bundle 渠道会生成基础 APK、按 ABI、语言或密度拆分的配置 APK，以及 Dynamic Feature APK（动态功能模块包）。比较 AAB 必须固定设备规格和模块集合。减少上传制品、设备下载量、安装占用和运行时内存是四个不同目标，应分别记录。

### 先做整包归因，再进入专项

[APK Analyzer](https://developer.android.com/studio/debug/apk-analyzer) 可查看 APK/AAB 的文件构成、DEX 包结构、资源和编译后的 manifest（应用清单），并比较两版制品。界面中的两个尺寸要分开解释：

- **Raw File Size** 是实体压缩后写入 APK ZIP 的大小，也就是它对当前 APK 文件大小的贡献，不是解压后的大小；
- **Download Size** 是工具对 Google Play 压缩传输大小的估算，适合观察变化方向，但不等于 Play Console 针对某个设备配置给出的精确结果。

先按增长目录选择后续路径：`classes*.dex` 看依赖、生成代码和 R8；`resources.arsc`、`res/` 与 `assets/` 看引用图、替代资源和素材；`lib/<abi>/` 看 ABI、符号、链接与页对齐。签名、压缩、加固和渠道重签也会改变产物，基线与候选必须使用同一发布变体、构建工具、签名流程和设备规格。每次只改变一类变量，重新生成 release 制品，才能把收益归到具体机制。

后文依次进入 DEX、Native SO 与资源三类专项；App Bundle 与按需分发的完整机制见 [25.6 App Bundle 与按需分发](06-app-bundle-delivery.md)。
""".strip()

ABI_SECTION = r"""
#### Android 17 安装期如何选择 ABI

`android-17.0.0_r1` 的 [`PackageAbiHelperImpl.derivePackageAbi()`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageAbiHelperImpl.java) 会根据包是否为 multi-arch（同时包含 32 位和 64 位原生库）、设备支持的 ABI 顺序、覆盖参数，以及是否提取原生库选择不同分支：

- 需要提取时，它调用 `NativeLibraryHelper.copyNativeBinariesForSupportedAbi()`；该流程先用 `findSupportedAbi()` 选择设备 ABI 列表中排名最靠前的匹配项，再创建目录并复制、校验；
- `extractNativeLibs=false` 时，安装流程仍会选择并校验 ABI，但不会把 `.so` 复制到应用原生库目录；
- multi-arch 包会分别检查设备支持的 32 位和 64 位 ABI，不能简化成“primary ABI 找不到再尝试 secondary ABI”这一条固定路径。

这些分支可在 Android 17 的 [`NativeLibraryHelper`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/com/android/internal/content/NativeLibraryHelper.java) 中交叉核对。未压缩且满足 ZIP/ELF 对齐要求的 `.so` 可以从 APK 直接映射，减少安装后的提取副本；对应 APK 可能因为不使用 ZIP 压缩而变大，所以发布报告必须同时保留下载量与安装占用。
""".strip()

SOONG_SECTION = r"""
#### AOSP Soong 与应用 AGP 的配置边界

AOSP 的 `android-17.0.0_r1` 平台模块使用 Soong 构建系统。源码中的关键调用形态能说明平台构建如何串联 AAPT2、R8 和诊断产物：

```text
aapt2 link ... --proguard <proguard-options> --output-text-symbols <R.txt>

r8 ... --no-data-resources \
  -printmapping <mapping> \
  -printconfiguration <configuration> \
  -printusage <usage>
```

第一条来自 Soong 的 [`java/aapt2.go`](https://android.googlesource.com/platform/build/soong/+/android-17.0.0_r1/java/aapt2.go)，第二条来自 [`java/dex.go`](https://android.googlesource.com/platform/build/soong/+/android-17.0.0_r1/java/dex.go)。启用协同资源缩减时，Soong 还会向 R8 传递 `--resource-input`、`--resource-output` 和 `--optimized-resource-shrinking`；[`java/app.go`](https://android.googlesource.com/platform/build/soong/+/android-17.0.0_r1/java/app.go) 则配合 non-final resource ID（非编译期常量的资源 ID）调整旧的 AAPT2 规则接入方式。

这些参数只约束 AOSP 平台模块。Soong 的 `Optimize.*` 属性、`RELEASE_*` 变量和 `R8_DUMP_*` 环境变量不是普通应用的 Gradle DSL；应用工程仍应按所用 AGP/R8 版本配置 `optimization` 或 legacy build type，并以最终 release APK/APKS 验证结果。
""".strip()


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one marker, found {count}")
    return text.replace(old, new, 1)


def build_article(entry: str, deep: str) -> str:
    text = deep
    text = replace_once(
        text,
        "title: DEX、Native SO 与资源文件体积优化",
        f"title: {NEW_TITLE}",
        "frontmatter title",
    )
    text = replace_once(text, "chapter: '25.12'", "chapter: '25.5'", "chapter")
    text = replace_once(text, "section: '25.12'", "section: '25.5'", "section")
    text = replace_once(
        text,
        "applicable_versions: Android 12 (API 31) - Android 17 (API 37)",
        "applicable_versions: Android 10 (API 29) - Android 17 (API 37)",
        "applicable versions",
    )
    text = text.replace("- '25.5'\n", "", 1)

    tags_marker = "- AAPT2\n"
    text = replace_once(
        text,
        tags_marker,
        tags_marker + "- apk-analyzer\n- resource-shrink\n- abi-filter\n",
        "tags",
    )

    source_marker = (
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/tools/aapt2/ResourceTable.cpp\n"
    )
    extra_sources = (
        "- type: official\n"
        "  path: https://developer.android.com/tools/apksigner\n"
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageAbiHelperImpl.java\n"
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/com/android/internal/content/NativeLibraryHelper.java\n"
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/build/soong/+/android-17.0.0_r1/java/aapt2.go\n"
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/build/soong/+/android-17.0.0_r1/java/dex.go\n"
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/build/soong/+/android-17.0.0_r1/java/app.go\n"
    )
    text = replace_once(text, source_marker, source_marker + extra_sources, "sources")

    consolidated_marker = (
        "consolidated_from:\n"
        "- src/part5-app/ch25-power-size/17-dex-size-optimization.md\n"
        "- src/part5-app/ch25-power-size/18-native-so-size-optimization.md\n"
        "- src/part5-app/ch25-power-size/19-resource-file-size-optimization.md\n"
    )
    consolidated = (
        "consolidated_from:\n"
        "- src/part2-performance/ch12-apk-network/01-apk-size.md\n"
        "- src/part5-app/ch25-power-size/06-apk-analysis.md\n"
        "- src/part5-app/ch25-power-size/07-r8-resource-optimization.md\n"
        "- src/part5-app/ch25-power-size/17-dex-size-optimization.md\n"
        "- src/part5-app/ch25-power-size/18-native-so-size-optimization.md\n"
        "- src/part5-app/ch25-power-size/19-resource-file-size-optimization.md\n"
        "- src/part5-app/ch25-power-size/12-dex-native-resource-size.md\n"
    )
    text = replace_once(text, consolidated_marker, consolidated, "consolidated_from")

    old_opening = (
        "# DEX、Native SO 与资源文件体积优化\n\n"
        "应用体积主要由 DEX、Native SO 和资源文件组成。三类内容使用不同的分析工具和裁剪手段，最终都要同时检查下载、安装、运行时映射和功能兼容。\n\n"
        "## 字节码、依赖与 Profile 交付"
    )
    new_opening = (
        f"# {NEW_TITLE}\n\n"
        "应用体积主要由 DEX、Native SO 与资源文件组成，但治理对象不是一个孤立的 APK 数字。先固定交付制品和设备口径，再沿字节码、原生库与资源三条路径归因，最后回到下载、安装、运行时和功能兼容验证。\n\n"
        f"{GENERAL_SECTION}\n\n"
        "## 字节码、依赖与 Profile 交付"
    )
    text = replace_once(text, old_opening, new_opening, "opening")
    text = replace_once(
        text,
        "### 先确定优化对象\n\nDEX（Dalvik Executable",
        "### 先确定 DEX 的优化对象\n\nDEX（Dalvik Executable",
        "DEX scope heading",
    )

    abi_marker = (
        "普通 APK 渠道不具备 Play 的服务端 ABI 拆分能力时，可以为每个 ABI 分别构建 APK（per-ABI APK）。多个 APK 的 `versionCode`、签名、升级兼容和渠道选择必须由发布系统管理，不能把 `abiFilters` 当成分发方案。\n\n"
        "#### 不同 ABI 不能只比文件字节"
    )
    text = replace_once(
        text,
        abi_marker,
        abi_marker.replace(
            "\n\n#### 不同 ABI 不能只比文件字节",
            f"\n\n{ABI_SECTION}\n\n#### 不同 ABI 不能只比文件字节",
        ),
        "ABI insertion",
    )

    soong_marker = (
        "`compile` 的逐文件中间产物有利于增量构建，不能拿 `.flat` 目录总量当发布体积。`link` 处理资源覆盖（overlay）与 ID；资源缩减处理可达性；App Bundle 决定某个设备获取哪些配置。四个阶段的问题要用不同证据定位。\n\n"
        "#### 资源合并不是内容去重器"
    )
    text = replace_once(
        text,
        soong_marker,
        soong_marker.replace(
            "\n\n#### 资源合并不是内容去重器",
            f"\n\n{SOONG_SECTION}\n\n#### 资源合并不是内容去重器",
        ),
        "Soong insertion",
    )

    # Links back to either predecessor would now be self-links.  The material
    # remains in the surrounding section, so remove only those list entries.
    lines = []
    for line in text.splitlines():
        if line.startswith("- [25.5 APK 分析、R8 与资源优化]"):
            continue
        if line.startswith("- [25.12 DEX、Native SO 与资源文件体积优化]"):
            continue
        lines.append(line)
    text = "\n".join(lines) + "\n"
    return text


def update_src_references(path: Path, text: str) -> str:
    text = text.replace(
        "part5-app/ch25-power-size/12-dex-native-resource-size.md",
        "part5-app/ch25-power-size/05-apk-r8-resource-optimization.md",
    )
    text = text.replace("12-dex-native-resource-size.md", "05-apk-r8-resource-optimization.md")
    text = text.replace(
        "25.12 DEX、Native SO 与资源文件体积优化",
        f"25.5 {NEW_TITLE}",
    )
    text = text.replace(
        "25.5 APK 分析、R8 与资源优化",
        f"25.5 {NEW_TITLE}",
    )
    text = text.replace(
        "25.5 → 25.6 → 25.12（包体积）",
        "25.5（应用体积）→ 25.6（分发）",
    )
    text = text.replace(
        "包结构、R8 与资源收缩见 25.5，App Bundle 交付见 25.6，DEX（Android 字节码文件）、native library（原生库）和资源文件专项统一见 25.12。",
        "包结构、DEX、R8、native library（原生库）与资源文件专项统一见 25.5，App Bundle 交付见 25.6。",
    )
    if path.name == "18-media3-video-rendering.md":
        text = text.replace("- '25.12'", "- '25.5'")
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not ENTRY.exists() or not DEEP.exists():
        raise SystemExit("Both predecessor articles must exist; this transform is one-shot.")

    entry = ENTRY.read_text(encoding="utf-8")
    deep = DEEP.read_text(encoding="utf-8")
    merged = build_article(entry, deep)

    changed_files: dict[Path, str] = {ENTRY: merged}
    for path in sorted((ROOT / "src").rglob("*.md")):
        if path in (ENTRY, DEEP):
            continue
        original = path.read_text(encoding="utf-8")
        updated = update_src_references(path, original)
        if updated != original:
            changed_files[path] = updated

    for relative in (
        "metadata/queue.json",
        "metadata/queue_backup.json",
        "metadata/queue.backup.2026-07-08T10-53-47.json",
    ):
        path = ROOT / relative
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        updated = original.replace(
            "src/part5-app/ch25-power-size/12-dex-native-resource-size.md",
            "src/part5-app/ch25-power-size/05-apk-r8-resource-optimization.md",
        )
        if updated != original:
            changed_files[path] = updated

    result = {
        "version": 7,
        "operation": "editorial_fusion",
        "removed_path": str(DEEP.relative_to(ROOT)),
        "target_path": str(ENTRY.relative_to(ROOT)),
        "target_title": NEW_TITLE,
        "merged_paths": [
            {
                "source": str(DEEP.relative_to(ROOT)),
                "target": str(ENTRY.relative_to(ROOT)),
                "role": "application_size_owner",
            }
        ],
        "source_bytes": {
            str(ENTRY.relative_to(ROOT)): len(entry.encode("utf-8")),
            str(DEEP.relative_to(ROOT)): len(deep.encode("utf-8")),
        },
        "result_bytes": len(merged.encode("utf-8")),
        "source_sha256": {
            str(ENTRY.relative_to(ROOT)): sha256(entry),
            str(DEEP.relative_to(ROOT)): sha256(deep),
        },
        "result_sha256": sha256(merged),
        "content_routes": [
            {
                "source": "25.5 制品组成、下载体积与安装体积",
                "destination": "25.5 先统一制品与体积口径",
                "treatment": "rewritten_and_embedded",
                "preserved_unique_points": [
                    "APK signing and ZIP semantics",
                    "upload/download/install/runtime measurement boundary",
                    "APK Analyzer Raw File Size versus Download Size",
                    "whole-package attribution before specialist analysis",
                ],
            },
            {
                "source": "25.5 代码收缩、混淆与资源裁剪",
                "destination": "25.5 字节码、依赖与 Profile 交付 / 图片、语言、表和压缩格式",
                "treatment": "deduplicated_into_deeper_existing_sections",
                "preserved_unique_points": [
                    "AOSP Soong versus application AGP boundary",
                    "AGP 9.3 and R8 Full Mode evidence already present",
                ],
            },
            {
                "source": "25.5 Android 17 安装期如何选择 ABI",
                "destination": "25.5 ABI、符号、链接与 ELF 段 / ABI 构建集合",
                "treatment": "rewritten_and_embedded",
                "preserved_unique_points": [
                    "PackageAbiHelperImpl branches",
                    "extractNativeLibs boundary",
                    "multi-arch selection",
                ],
            },
            {
                "source": "25.12 three specialist chapters",
                "destination": "25.5 canonical article",
                "treatment": "retained_as_primary_body",
                "preserved_unique_points": [
                    "DEX and R8 internals",
                    "ELF, ABI, symbols and 16 KB alignment",
                    "AAPT2, resources, images, fonts and delivery",
                ],
            },
        ],
        "updated_reference_files": [
            str(path.relative_to(ROOT)) for path in sorted(changed_files) if path != ENTRY
        ],
        "applied": args.apply,
    }

    if args.apply:
        for path, updated in changed_files.items():
            path.write_text(updated, encoding="utf-8")
        DEEP.unlink()
        MAP_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
