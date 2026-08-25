#!/usr/bin/env python3
"""Consolidate Baseline Profile coverage by editorial responsibility.

Routes the former responsiveness overview into three existing owners:

* 21.4 owns application generation, packaging, delivery and verification.
* 19.7 owns Benchmark measurement protocol and only the minimal generator hook.
* 16.5 owns platform install compilation and OEM image-build boundaries.

The script also removes the duplicated long Profile tutorial from 19.7 and
reindexes the remaining chapter 8 articles after removing 8.5.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REMOVED = ROOT / "src/part2-performance/ch08-responsiveness/05-baseline-profiles.md"
APP = ROOT / "src/part5-app/ch21-startup/04-baseline-startup-cloud-profile.md"
BENCH = ROOT / "src/part3-tools/ch19-apm/07-jetpack-benchmark-baseline-profiles.md"
PLATFORM = ROOT / "src/part4-system/ch16-aosp/05-profile-dm-sdm-install-compilation.md"
MAP_PATH = ROOT / "metadata/2026-08-24-editorial-fusion-v8-map.json"

REINDEX = [
    (
        ROOT / "src/part2-performance/ch08-responsiveness/06-keystore-biometric-credential-login.md",
        ROOT / "src/part2-performance/ch08-responsiveness/05-keystore-biometric-credential-login.md",
        "8.6",
        "8.5",
    ),
    (
        ROOT / "src/part2-performance/ch08-responsiveness/07-push-notification-pipeline-performance.md",
        ROOT / "src/part2-performance/ch08-responsiveness/06-push-notification-pipeline-performance.md",
        "8.7",
        "8.6",
    ),
    (
        ROOT / "src/part2-performance/ch08-responsiveness/08-play-integrity-api-performance.md",
        ROOT / "src/part2-performance/ch08-responsiveness/07-play-integrity-api-performance.md",
        "8.8",
        "8.7",
    ),
]

BENCH_TITLE = "Jetpack Benchmark：Microbenchmark、Macrobenchmark 与测量协议"

APP_SCOPE_BOUNDARY = """
这里还要划清两条相邻但不同的优化链路。Baseline/Startup Profile 只处理由 ART 管理的 DEX 代码；[AutoFDO](../../part4-system/ch16-aosp/04-autofdo-feedback-directed-optimization.md) 用采样或硬件分支轨迹指导 LLVM/Clang 优化 native 可执行文件和共享库。OEM dexpreopt 则发生在系统镜像构建阶段，处理 boot classpath、`system_server`、系统组件和预装 APK。预装应用可能同时受三者影响，但输入数据、消费者、产物位置和验证工具不能互换。
""".strip()

APP_ROLES = """
这条流水线有三个明确角色，模块边界比“把规则文件复制到 app”更重要：

| 角色 | 典型模块 | 负责什么 | 不负责什么 |
|---|---|---|---|
| producer | 独立 `com.android.test` 的 `:baseline-profile` | 在受控设备上驱动 CUJ，输出 HRF 规则 | 不承载生产业务代码 |
| consumer | 最终 `:app` | 合并应用与依赖库规则，由 R8 按 release 符号重写并打包 | 不用生成 variant 的未混淆 DEX 代替发布 DEX |
| library | AAR 与 sample app | 通过真实公开 API 生成并过滤本库规则 | 不知道宿主启动入口，不能贡献最终 Startup Profile |

producer 的生成 variant 应保持 `debuggable=false`、`profileable=true`、不混淆且不优化；最终 release 应启用 R8。API 33+ 可在非 root 设备生成规则，API 28～32 需要 rooted 环境；生成环境只决定能否收集，收益结论仍要回到目标物理设备和 release 类产物。
""".strip()

ONLINE_AB = """
Profile 与 APK 紧密绑定，同一版本里的运行时开关不能移除已经打包或编译的 profile。需要线上对照时，应使用只改变 profile 的小流量受控版本或专项小版本，并在 Cloud Profile 尚未充分传播的发布早期按安装来源、安装时间和编译状态分组。代码、资源、服务端配置与用户入口必须保持一致；否则无法把变化归因给 profile。
""".strip()

OEM_SECTION = """
### 7.3 OEM dexpreopt 与应用 Profile

OEM dexpreopt 在系统镜像构建期处理 boot classpath、`system_server`、系统组件和预装 APK。`WITH_DEXPREOPT`、`WITH_DEXPREOPT_BOOT_IMG_AND_SYSTEM_SERVER_ONLY` 等构建开关决定镜像预编译范围，产物进入 system 分区或 boot image 相关目录；应用 Baseline Profile 则随 APK/AAB 交付，由安装端 ART、渠道或 ProfileInstaller 消费。

预装应用可能同时获得镜像 dexpreopt 与后续 profile-guided dexopt，但两者发生的阶段、权限、输入和产物归属不同。不能把 `WITH_DEXPREOPT_*` 当成第三方应用的 Profile 开关，也不能把某家 OEM 的私有预装策略写成 AOSP 应用分发规则。实验应分别记录镜像构建配置、安装输入、ART Service 的 compiler filter/reason 和应用侧 Macrobenchmark 结果。
""".strip()


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one marker, found {count}")
    return text.replace(old, new, 1)


def remove_block(text: str, start: str, end: str, label: str) -> tuple[str, str]:
    start_at = text.find(start)
    end_at = text.find(end, start_at + len(start)) if start_at >= 0 else -1
    if start_at < 0 or end_at < 0:
        raise RuntimeError(f"{label}: block markers not found")
    removed = text[start_at:end_at]
    return text[:start_at] + text[end_at:], removed


def build_app(text: str) -> str:
    text = text.replace(
        "last_verified_against: Current Android Developers Baseline/Startup Profile, ProfileVerifier and Macrobenchmark docs; AOSP android-17.0.0_r1 art/profman + art/dex2oat; AIW 8.7 / 19.12",
        "last_verified_against: Current Android Developers Baseline/Startup Profile, ProfileVerifier and Macrobenchmark docs; AOSP android-17.0.0_r1 art/profman + art/dex2oat",
    )
    for block in (
        "- type: local\n  path: src/part2-performance/ch08-responsiveness/07-baseline-profiles.md\n",
        "- type: local\n  path: src/part3-tools/ch19-apm/12-baseline-profiles.md\n",
    ):
        text = replace_once(text, block, "", "stale local source")
    text = replace_once(text, "- '8.5'\n", "", "obsolete related chapter")

    consolidated = (
        "- src/part5-app/ch21-startup/10-cloud-profile-dm-install-compile.md\n"
    )
    text = replace_once(
        text,
        consolidated,
        consolidated
        + "- src/part2-performance/ch08-responsiveness/05-baseline-profiles.md\n"
        + "- src/part3-tools/ch19-apm/07-jetpack-benchmark-baseline-profiles.md#profile-generation\n",
        "app provenance",
    )
    text = replace_once(
        text,
        "## 本地 Profile 生成、打包与基准验证",
        "## 应用构建侧：生成、打包与基准验证",
        "app H2 role",
    )
    scope_marker = (
        "AGP、Macrobenchmark、ProfileInstaller 和 Google Play 各自演进，项目仍需固定一组经过验证的版本并写入实验记录。"
    )
    text = replace_once(
        text,
        scope_marker,
        scope_marker + "\n\n" + APP_SCOPE_BOUNDARY,
        "scope boundary",
    )

    timeline_marker = (
        "Startup Profile 是 Baseline Profile 的启动子集，但消费方不同：Baseline Profile 给 ART，Startup Profile 给构建工具做 DEX 布局。它们可以来自同一生成脚本，验证方法不能互换。"
    )
    timeline = (
        "Android 7 / API 24 是混合执行、JIT、本地 profile 与后台 profile-guided dexopt 协作的运行时边界；Android 9 / API 28 才增加 Google Play Cloud Profile。"
        "因此 Android 7～8.1 的包内 Baseline Profile 通常要由 ProfileInstaller 写入 current profile 后等待后台编译，而 Play 用户也不能仅凭安装完成就假定 Cloud/Baseline Profile 已经变成 `speed-profile` 产物。"
    )
    text = replace_once(
        text,
        timeline_marker,
        timeline_marker + "\n\n" + timeline,
        "historical timeline",
    )

    roles_marker = (
        "具体插件版本应与项目 AGP、Macrobenchmark 和 ProfileInstaller 组成经过验证的工具链；升级其中一项后需要重新生成和测量。"
    )
    text = replace_once(
        text,
        roles_marker,
        roles_marker + "\n\n" + APP_ROLES,
        "toolchain roles",
    )
    text = replace_once(
        text,
        "        includeInStartupProfile = true,\n    ) {",
        "        includeInStartupProfile = true,\n        strictStability = true,\n    ) {",
        "strict stability option",
    )
    generator_note = (
        "`includeInStartupProfile = true` 只应用于初始显示必经的启动场景。"
    )
    text = replace_once(
        text,
        generator_note,
        "`strictStability = true` 会在规则稳定性检查失败时让采集失败，但它不能代替页面就绪和业务数据断言。\n\n"
        + generator_note,
        "generator stability explanation",
    )

    text, _ = remove_block(
        text,
        "### 9. Cloud Profile 与线上验证\n",
        "### 10. Startup Profile 与 DEX Layout\n",
        "duplicated cloud section",
    )
    text = text.replace("### 10. Startup Profile 与 DEX Layout", "### 9. Startup Profile 与 DEX Layout")
    text = text.replace("#### 10.", "#### 9.")
    text = text.replace("### 11. 维护与回归", "### 10. 维护与回归")

    device_opening = (
        "## Cloud Profile、DM 交付与 dexopt\n\n"
        "应用自带 Profile 建立可控基线，云端 Profile 补充真实用户热路径。两者都要通过 DM、安装场景和 compiler filter 进入 ART。\n\n"
        "### Profile 在发布后如何生效\n\n"
        "Baseline Profile 是由 App 或库维护的“常用类和方法”规则，Android Runtime（ART）可据此提前编译关键代码。它的生成、Gradle 构建接入和 Macrobenchmark（AndroidX 宏基准测试）验证见 [Baseline Profile 与 Startup Profile 实战](04-baseline-startup-cloud-profile.md)。发布后还要继续追踪：安装来源交付了哪些 profile，Android 17 的 ART Service 怎样选择 profile 和 compiler filter（编译强度），以及 App 团队怎样判断一次启动变化是否来自编译状态。"
    )
    device_rewrite = (
        "## 分发与设备侧：Cloud Profile、DM 与 dexopt\n\n"
        "应用构建侧负责生成规则并证明本地收益；分发与设备侧负责回答这些输入是否到达目标 APK、是否被 ART 接受，以及何时形成可用编译产物。Cloud Profile 补充真实用户热路径，DM 只是随 APK 交付元数据的容器，compiler filter 与 reason 才描述设备最终做了什么。\n\n"
        "### Profile 在发布后如何生效\n\n"
        "上一部分已经完成 Baseline/Startup Profile 的生成、打包与受控基准。本部分只追踪发布后的安装来源、外部 profile、DM、ART Service 与 dexopt 状态；同一条证据不能同时证明“规则打包成功”和“设备已按规则编译”。"
    )
    text = replace_once(text, device_opening, device_rewrite, "device-side opening")

    grey_marker = (
        "Profile 是编译输入，覆盖不足会损失收益，覆盖过宽会增加编译时间和产物体积。分批放量（灰度）阶段需要同时看启动、安装/升级与稳定性。"
    )
    text = replace_once(
        text,
        grey_marker,
        grey_marker + "\n\n" + ONLINE_AB,
        "online experiment guidance",
    )
    return text


def build_benchmark(text: str) -> str:
    text = replace_once(
        text,
        "title: Jetpack Benchmark 与 Baseline Profiles",
        f"title: {BENCH_TITLE}",
        "benchmark title",
    )
    text = replace_once(
        text,
        "related_chapters:\n- '19.0'",
        "related_chapters:\n- '19.0'\n- '21.4'",
        "benchmark related chapter",
    )
    text = replace_once(
        text,
        "# Jetpack Benchmark 与 Baseline Profiles\n\nMicrobenchmark 测量局部代码，Macrobenchmark 测量应用启动和交互；Baseline Profile 记录应优先编译的热路径。基准测试负责证明收益，Profile 负责把收益带到用户安装环境。",
        f"# {BENCH_TITLE}\n\nMicrobenchmark 测量可重复的局部工作，Macrobenchmark 从外部进程测量启动与完整交互。本文只负责实验结构、编译状态、指标定义、噪声和 CI 门禁；BaselineProfileRule 作为一种实验输入保留最小接入示例，完整的生成、打包、渠道交付和 ART 状态统一由 21.4 维护。",
        "benchmark opening",
    )
    bridge_marker = (
        "生成后的 profile 需要随关键用户旅程、R8 映射（压缩后名称与原始名称的对应关系）、启动依赖和大版本调整重新生成。文件存在只说明产物被创建，`Partial(Require)`、`ArtMetric` 与启动/滚动指标才能证明它在当前 APK 和设备上发挥作用。"
    )
    text = replace_once(
        text,
        bridge_marker,
        bridge_marker
        + "\n\n应用侧 producer/consumer 配置、`baseline.prof`/`baseline.profm` 位置、ProfileInstaller/Verifier 状态、Cloud Profile 与 DM 边界见 [21.4 Baseline、Startup 与 Cloud Profile 编译优化](../../part5-app/ch21-startup/04-baseline-startup-cloud-profile.md)。这里不再复制第二套生成教程。",
        "benchmark bridge",
    )
    text, _ = remove_block(
        text,
        "\n## Profile 生成、打包与设备验证\n",
        "\n## 参考资料\n",
        "duplicated benchmark profile tutorial",
    )
    return text


def build_platform(text: str) -> str:
    text = replace_once(
        text,
        "- 16.9 Android 17 SDM 安装编译流程性能\n",
        "- 16.9 Android 17 SDM 安装编译流程性能\n"
        "- src/part2-performance/ch08-responsiveness/05-baseline-profiles.md#oem-dexpreopt\n",
        "platform provenance",
    )
    text = replace_once(
        text,
        "### 7.3 应用团队可复核的产物与状态",
        OEM_SECTION + "\n\n### 7.4 应用团队可复核的产物与状态",
        "OEM dexpreopt insertion",
    )
    duplicate = (
        "- [21.4 Baseline、Startup 与 Cloud Profile 编译优化](../../part5-app/ch21-startup/04-baseline-startup-cloud-profile.md)：从应用启动角度补充 DM 与 Profile。\n"
    )
    text = replace_once(text, duplicate, "", "duplicate 21.4 related link")
    related_marker = (
        "- [21.4 Baseline、Startup 与 Cloud Profile 编译优化](../../part5-app/ch21-startup/04-baseline-startup-cloud-profile.md)：从应用侧生成、打包和回归 Baseline Profile。\n"
    )
    text = replace_once(
        text,
        related_marker,
        related_marker
        + "- [16.4 AutoFDO 反馈导向编译优化](04-autofdo-feedback-directed-optimization.md)：native 采样反馈与 LLVM/Clang 构建期优化，不属于 ART Profile。\n",
        "AutoFDO related link",
    )
    return text


def relpath(target: Path, source_file: Path) -> str:
    return Path(os.path.relpath(target, source_file.parent)).as_posix()


def update_references(path: Path, text: str) -> str:
    # Remove navigation entries for the retired overview before rewriting its
    # destination, otherwise SUMMARY/README would gain a duplicate 21.4 link.
    navigation_files = {
        ROOT / "src/SUMMARY.md",
        ROOT / "src/part2-performance/ch08-responsiveness/README.md",
    }
    if path in navigation_files:
        lines = [
            line
            for line in text.splitlines()
            if "05-baseline-profiles.md" not in line
        ]
        if len(lines) != len(text.splitlines()):
            text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")

    old_rel = relpath(REMOVED, path)
    app_rel = relpath(APP, path)
    # `consolidated_from` records historical paths by design; keep the source
    # identity while rewriting live links that point at the retired article.
    provenance = "src/part2-performance/ch08-responsiveness/05-baseline-profiles.md"
    placeholder = "__HISTORICAL_BASELINE_PROFILE_SOURCE__"
    text = text.replace(provenance, placeholder)
    text = text.replace(old_rel, app_rel)
    text = text.replace(
        provenance,
        "src/part5-app/ch21-startup/04-baseline-startup-cloud-profile.md",
    )
    text = text.replace(
        "[[05-baseline-profiles|8.5 Baseline Profiles 与编译优化实践]]",
        f"[21.4 Baseline、Startup 与 Cloud Profile 编译优化]({app_rel})",
    )
    text = text.replace(
        "8.5 Baseline Profiles 与编译优化实践",
        "21.4 Baseline、Startup 与 Cloud Profile 编译优化",
    )
    text = text.replace("Baseline Profile 见 8.5", "Baseline Profile 见 21.4")
    text = text.replace("- '8.5'", "- '21.4'")
    text = text.replace(placeholder, provenance)

    for old, new, _, _ in REINDEX:
        old_link = relpath(old, path)
        new_link = relpath(new, path)
        text = text.replace(old_link, new_link)
        text = text.replace(
            str(old.relative_to(ROOT)),
            str(new.relative_to(ROOT)),
        )

    text = text.replace("- '8.6'", "- '8.5'")
    text = text.replace("- '8.7'", "- '8.6'")
    text = text.replace("- '8.8'", "- '8.7'")

    # Unlinked prose references whose meaning is the chapter article rather
    # than a library/CPU version number.
    prose_replacements = {
        "8.6 讨论应用进程、keystore2": "8.5 讨论应用进程、keystore2",
        "§8.6 Keystore/KeyMint": "§8.5 Keystore/KeyMint",
        "§8.6 BiometricPrompt": "§8.5 BiometricPrompt",
        "§8.7 推送通知管线性能": "§8.6 推送通知管线性能",
        "8.6 Keystore / KeyMint": "8.5 Keystore / KeyMint",
        "8.6 BiometricPrompt": "8.5 BiometricPrompt",
        "8.7 推送通知管线性能": "8.6 推送通知管线性能",
        "8.8 Play Integrity": "8.7 Play Integrity",
        "相关内容见 `8.6` 和 `8.8`": "相关内容见 `8.5` 和 `8.7`",
        "8.1-8.6（响应速度）": "8.1-8.7（响应速度）",
    }
    for old, new in prose_replacements.items():
        text = text.replace(old, new)
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    required = [REMOVED, APP, BENCH, PLATFORM] + [row[0] for row in REINDEX]
    if not all(path.exists() for path in required):
        raise SystemExit("Expected predecessor files are missing; this transform is one-shot.")

    originals = {path: path.read_text(encoding="utf-8") for path in required}
    app_new = build_app(originals[APP])
    bench_new = build_benchmark(originals[BENCH])
    platform_new = build_platform(originals[PLATFORM])

    reindexed: dict[Path, str] = {}
    for old, new, old_number, new_number in REINDEX:
        body = originals[old]
        body = replace_once(
            body,
            f"chapter: '{old_number}'",
            f"chapter: '{new_number}'",
            f"{old.name} chapter",
        )
        body = replace_once(
            body,
            f"section: '{old_number}'",
            f"section: '{new_number}'",
            f"{old.name} section",
        )
        reindexed[new] = body

    changed: dict[Path, str] = {
        APP: app_new,
        BENCH: bench_new,
        PLATFORM: platform_new,
        **reindexed,
    }

    skip = {REMOVED, APP, BENCH, PLATFORM, *[row[0] for row in REINDEX]}
    for path in sorted((ROOT / "src").rglob("*.md")):
        if path in skip:
            continue
        original = path.read_text(encoding="utf-8")
        updated = update_references(path, original)
        if updated != original:
            changed[path] = updated

    # Apply reference changes inside the rewritten owners and reindexed bodies.
    for path in list(changed):
        changed[path] = update_references(path, changed[path])

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
            str(REMOVED.relative_to(ROOT)),
            str(APP.relative_to(ROOT)),
        )
        for old, new, _, _ in REINDEX:
            updated = updated.replace(str(old.relative_to(ROOT)), str(new.relative_to(ROOT)))
        if updated != original:
            changed[path] = updated

    result = {
        "version": 8,
        "operation": "distributed_editorial_fusion",
        "removed_path": str(REMOVED.relative_to(ROOT)),
        "target_path": str(APP.relative_to(ROOT)),
        "merged_paths": [
            {
                "source": str(REMOVED.relative_to(ROOT)),
                "target": str(APP.relative_to(ROOT)),
                "role": "application_profile_owner",
            },
            {
                "source": f"{REMOVED.relative_to(ROOT)}#release-like-profiling",
                "target": str(BENCH.relative_to(ROOT)),
                "role": "benchmark_measurement_owner",
            },
            {
                "source": f"{REMOVED.relative_to(ROOT)}#oem-dexpreopt",
                "target": str(PLATFORM.relative_to(ROOT)),
                "role": "platform_install_compilation_owner",
            },
        ],
        "rewritten_paths": [
            str(APP.relative_to(ROOT)),
            str(BENCH.relative_to(ROOT)),
            str(PLATFORM.relative_to(ROOT)),
        ],
        "reindexed_paths": [
            {"from": str(old.relative_to(ROOT)), "to": str(new.relative_to(ROOT))}
            for old, new, _, _ in REINDEX
        ],
        "source_bytes": {
            str(path.relative_to(ROOT)): len(text.encode("utf-8"))
            for path, text in originals.items()
        },
        "result_bytes": {
            str(APP.relative_to(ROOT)): len(changed[APP].encode("utf-8")),
            str(BENCH.relative_to(ROOT)): len(changed[BENCH].encode("utf-8")),
            str(PLATFORM.relative_to(ROOT)): len(changed[PLATFORM].encode("utf-8")),
        },
        "source_sha256": {
            str(path.relative_to(ROOT)): digest(text) for path, text in originals.items()
        },
        "result_sha256": {
            str(path.relative_to(ROOT)): digest(changed[path])
            for path in (APP, BENCH, PLATFORM)
        },
        "content_routes": [
            {
                "source": "8.5 Profile mechanism, generation, Startup Profile and validation",
                "destination": "21.4 application build and device delivery sections",
                "treatment": "deduplicated_into_deeper_owner",
            },
            {
                "source": "8.5 Android 7/9 history and AutoFDO boundary",
                "destination": "21.4 scope and profile taxonomy",
                "treatment": "rewritten_and_embedded",
            },
            {
                "source": "8.5 release-like profileable measurement",
                "destination": "19.7 existing benchmark build structure",
                "treatment": "already_subsumed_and_verified",
            },
            {
                "source": "8.5 OEM dexpreopt",
                "destination": "16.5 distribution and application responsibilities",
                "treatment": "rewritten_and_embedded",
            },
            {
                "source": "19.7 duplicated Profile generation tutorial",
                "destination": "21.4 producer/consumer/library, generator stability and validation sections",
                "treatment": "unique_points_embedded_then_duplicate_removed",
            },
            {
                "source": "21.4 duplicated Cloud Profile overview",
                "destination": "21.4 distribution/device-side H2 and gray-release section",
                "treatment": "fused_within_article",
            },
        ],
        "updated_reference_files": [
            str(path.relative_to(ROOT)) for path in sorted(changed) if path not in required
        ],
        "applied": args.apply,
    }

    if args.apply:
        for path, body in changed.items():
            path.write_text(body, encoding="utf-8")
        REMOVED.unlink()
        for old, _, _, _ in REINDEX:
            old.unlink()
        MAP_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
