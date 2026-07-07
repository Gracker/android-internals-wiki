---
title: "AOSP 源码编译与调试环境"
chapter: "16.3"
status: finalized
drafted_date: "2026-04-04"
drafted_by: "openclaw-task2a"
reviewed_date: '2026-07-07'
reviewed_by: "openclaw-task6"
task6_result: pass-light-edit
task6_review_notes: "2026-07-07 Task6 revisiting review: pass-light-edit；Task9 auto-fix 已验证；L1 修 1 处物理动作动词(收紧→受限)；章节无 outline 块(历史遗留)；无 L3/L4 回炉项。task9_result=auto-fixed 非 pass-tech-review，未自动晋升。"
last_task6_at: "2026-07-07T20:11:24+08:00"
task6_state: reviewed
last_task6_audit: "2026-06-22"
task9_state: reviewed
task9_result: pass-tech-review
last_task9_autofix_at: "2026-07-07"
last_task9_at: "2026-07-08T00:31:29+08:00"
task9_reviewed_date: "2026-07-08"
task9_reviewed_by: openclaw-task9
task2b_state: fixed
task2b_result: fixed
pipeline_stage: ready-to-publish
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
last_verified: "2026-07-07"
last_verified_against: "AOSP android-17.0.0_r1 + source.android.com"
confidence: medium
last_task9_audit: "2026-07-07"
last_task9_audit_at: "2026-07-07T11:27:49+08:00"
last_task9_audit_log: "logs/deep-review/2026-07-07-11-audit.md"
sources:
  - type: official
    path: "source.android.com/docs/setup/start/requirements"
  - type: official
    path: "source.android.com/docs/setup/build"
  - type: official
    path: "source.android.com/docs/devices/cuttlefish/get-started"
  - type: official
    path: "source.android.com/docs/devices/cuttlefish/webrtc"
  - type: official
    path: "source.android.com/docs/setup/download"
  - type: official
    path: "https://android.googlesource.com/platform/packages/modules/adb/+/android-17.0.0_r1/docs/user/adb.1.md"
  - type: official
    path: "source.android.com/docs/core/architecture/configuration/add-system-properties"
  - type: official
    path: "source.android.com/docs/core/architecture/configuration/sysprops-apis"
  - type: official
    path: "https://developers.google.com/android/drivers"
section: "16.3"
tags: ['aosp', 'build', 'soong', 'ninja', 'emulator', 'cuttlefish', 'debug']
related_chapters: ["16.1", "16.2", "15.7", "14.7"]
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-08
last_task2b_verifier_at: "2026-07-07T23:28:23+08:00"
last_task9_review_log: "logs/deep-review/2026-07-08-00-deep-review.md"
finalized_date: "2026-07-08"
finalized_by: openclaw-task9-auto-promote
auto_promoted_date: "2026-07-08"
auto_promoted_by: openclaw-task9
---

# AOSP 源码编译与调试环境

要理解 Android 系统的深层行为——比如 Zygote fork 后主线程的 200ms 卡顿、SurfaceFlinger 选择 GPU 合成的条件——仅阅读源码不够，需要实际修改代码、编译模块、验证效果。本节构建完整的「修改 Framework 代码并验证假设」工作流：从环境搭建、源码下载到编译、模拟器运行、修改验证。

## 环境准备与源码下载

编译 AOSP 需要一台性能足够的工作站。Google 内部使用 72 核、64 GB RAM 的机器，全量编译大约 40 分钟。对个人开发者来说，16 核 CPU、64 GB RAM、500 GB 以上 SSD 是比较现实的起步配置。磁盘空间至少预留 400 GB——源码 checkout 约 250 GB，编译产物另需 150 GB。

[已验证: 官方文档, source.android.com/docs/setup/start/requirements]

**操作系统方面，Linux 是唯一官方支持的编译平台。**Ubuntu 20.04 LTS 和 22.04 LTS 都可以正常编译 Android 11+（包括 Android 17）。macOS 自 2021 年起（Android 11+）已不再官方支持作为 AOSP 编译平台。即使通过 case-sensitive APFS 卷做 workaround，也经常会遇到路径大小写敏感性问题。如果主力机是 Mac，推荐用 Ubuntu 虚拟机或远程 Linux 服务器来编译。

Ubuntu 上需要安装一系列编译依赖包。Android 17 基线下的 Ubuntu 编译依赖可以通过以下命令一次性安装：

```bash
sudo apt-get install git-core gnupg flex bison build-essential \
  zip curl zlib1g-dev libc6-dev-i386 x11proto-core-dev \
  libx11-dev lib32z1-dev libgl1-mesa-dev libxml2-utils \
  xsltproc unzip fontconfig
```

源码下载使用 Google 的 `repo` 工具。`repo` 是一个 Python 脚本，封装了数百个 Git 仓库的批量管理。初始化和同步的标准流程是：

```bash
# 初始化 manifest
repo init -u https://android.googlesource.com/platform/manifest \
  -b android-17.0.0_r1

# 并行同步（-j 后跟 CPU 核心数的 2-4 倍通常效果最好）
repo sync -j32
```

本书主线结论固定在 `android-17.0.0_r1`，因此示例直接 pin 到 Android 17 release tag。从 2026 年开始，Google 调整了 AOSP 发布节奏，改为每年两次（Q2 和 Q4）公开发布源码；官方面向普通构建/贡献者仍推荐 `android-latest-release`，它会跟随最近一次推送到 AOSP 的 release。本书复现时不要用它替代固定 tag，避免后续移动到更高版本口径。首次同步大约需要 50-100 GB 的网络流量，耗时取决于网速。

[已验证: 官方文档, source.android.com/docs/setup/download]

AOSP 的构建系统由三层组成：Soong、Kati 和 Ninja。Soong 解析 `Android.bp` 文件（声明式模块描述），生成 Ninja 构建清单；Kati 将遗留的 `Android.mk` 文件翻译为 Ninja 清单；Ninja 作为执行引擎负责实际的编译调度。Google 曾计划将构建系统迁移到 Bazel，但该迁移已于 2024 年中止。了解这三层的关系，有助于理解为什么修改一个 `.bp` 文件后需要先跑 `m nothing` 来验证构建描述是否正确。

## Lunch Target 与 Build Variant

源码同步完成之后，需要选择编译目标。这个选择通过 `lunch` 命令完成：

```bash
source build/envsetup.sh    # 加载构建环境
lunch                       # 交互式选择 target
# 或直接指定
lunch aosp_cf_x86_64_only_phone-trunk_staging-userdebug
```

`lunch` 做的事情是设置一系列环境变量（`TARGET_PRODUCT`、`TARGET_BUILD_VARIANT`、`OUT` 等），后续的编译命令 `m` 会读取这些变量来决定编译什么。

Build variant 是一个容易混淆的概念，三种变体各有用途：

**`user`** 是生产环境版本。关闭了 root 权限、adb root、调试日志的默认输出，开启了完整的安全检查（SELinux enforcing、Verified Boot）。这是厂商出厂镜像使用的变体，不适合开发调试。

**`userdebug`** 是最常用的开发变体。在 `user` 的基础上开放了 root 和 adb 访问，保留了大部分安全检查。性能优化分析、Perfetto 抓 Trace、框架层调试都用这个变体。它在性能表现上与 `user` 足够接近，调试数据有参考价值。

**`eng`** 是工程开发变体。开启了所有调试选项，包括更详细的日志输出、禁用部分安全检查、预装开发工具。eng 构建的自测更方便，但性能数据不可用于 benchmark——因为额外的调试开销会显著影响调度、GC、渲染等行为。

对于性能分析场景，建议用 `userdebug` 做主要验证，`eng` 做快速自测。做 benchmark 之前一定要确认当前是 `userdebug` 而非 `eng`，否则数据基本不可信。

选定 target 后，开始编译：

```bash
m -j$(nproc)    # 全量编译
# 或只编译特定模块
m framework     # 编译 framework.jar
m services      # 编译 services.jar
```

全量编译首次耗时取决于硬件配置。增量编译（修改少量文件后重新 `m`）利用 Ninja 的增量构建能力，通常只需要几十秒到几分钟。

## 模拟器运行 AOSP

编译完成后，需要一种方式运行和验证。Android 提供两种模拟器方案。

### Android Emulator（QEMU）

这是大家最熟悉的方案，Android Studio 自带的那个模拟器。编译 AOSP 后可以直接启动：

```bash
# 编译 emulator 和 system image
m emulator -j$(nproc)

# 启动
emulator -avd <avd_name> -system <path/to/system.img>
```

传统 Android Emulator 基于 QEMU，适合开发和调试应用。但对于 Framework 层的修改验证，它有一个局限性：系统镜像的更新需要重新编译和重启模拟器，调试循环相对较慢。

### Cuttlefish

Cuttlefish 是 Google 推荐的 AOSP 测试方案。它是一个运行在 Linux 主机上的虚拟 Android 设备，使用 KVM 硬件加速，对 AOSP 源码改动有更好的支持。

Cuttlefish 基于 Google 自研的 **crosvm** 虚拟机和 **virtio** 设备模型。crosvm 是 Chrome OS / Android 场景专用的轻量级 VMM；virtio 提供了低开销的半虚拟化 I/O 接口（网络、块设备、输入设备等）。相比 QEMU，这套架构启动更快、开销更小，被 AOSP CI 和 Android 仪表盘选作标准测试平台。Host 侧通过 WebRTC 暴露交互界面（浏览器 `https://localhost:8443`），同时通过 ADB 提供命令行访问。


Cuttlefish 的设置流程（以 AOSP 编译产物路径为例）：

```bash
# 1. 编译 Cuttlefish 镜像
lunch aosp_cf_x86_64_only_phone-trunk_staging-userdebug
m -j$(nproc)

# 2. 编译并安装 Cuttlefish host 包
# 从 AOSP 源码编译 host 依赖（cuttlefish-base, cuttlefish-user）
m -j$(nproc) cvd-host-package
# 解压并安装 deb 包（或按官方 get-started 配置 artifact registry）
sudo dpkg -i cuttlefish-base_*.deb cuttlefish-user_*.deb
sudo apt-get install -f  # 修复依赖

# 3. 添加用户组并重新登录
sudo usermod -aG kvm,cvdnetwork,render $USER
# 重新登录使组变更生效

# 4. 解压 host package 并启动
tar -xvf cvd-host_package.tar.gz
HOME=$PWD ./bin/launch_cvd --daemon
```

对于不编译 AOSP 的场景（CI 预编译镜像路径），从 Android CI 下载 `cvd-host_package.tar.gz` 和目标设备 image，解压后用 `./bin/launch_cvd` 启动。`sudo apt install -y cuttlefish-common` 在干净 Ubuntu 上不保证具备可复现性，因为 `cuttlefish-common` 包的版本可能与当前 AOSP 分支不匹配。

[已验证: source.android.com/docs/devices/cuttlefish/get-started, source.android.com/docs/devices/cuttlefish/webrtc, AOSP android-17.0.0_r1 device/google/cuttlefish README]

启动后，Cuttlefish 默认提供一个 Web 界面（`https://localhost:8443`），可以直接在浏览器里看到虚拟设备的画面。同时可以通过 ADB 连接：

```bash
adb connect 0.0.0.0:6520
adb devices  # 应该能看到一个 Cuttlefish 设备
```

Cuttlefish 的核心优势在于它与 AOSP 构建系统的深度集成。修改 Framework 代码后，只需要增量编译，再用 `adb sync system` 或单文件 `adb push` 同步改动，不需要每次都重新刷机。对于经常需要改一点、跑一下、看日志的 Framework 调试循环，效率提升非常明显。

ARM64 主机（如 Apple Silicon Mac 上的 Linux 虚拟机）也可以运行 Cuttlefish，但需要使用 `aosp_cf_arm64_only_phone` target，且性能会略低于 x86_64 方案。

## 修改 Framework 代码并验证

Framework 调试的核心是修改代码，然后验证效果。调试循环如下：

**第一步：定位要修改的文件。** AOSP 的 Framework 层源码主要分布在 `frameworks/base/` 下。System Server 的代码在 `frameworks/base/services/`，核心类如 ActivityManagerService、WindowManagerService 都在这里。对于性能分析相关的调试，我们经常需要修改的地方包括：

- `frameworks/base/core/java/android/view/` — Choreographer、ViewRootImpl
- `frameworks/base/core/jni/` — 渲染相关的 JNI 层
- `frameworks/base/services/core/java/com/android/server/am/` — AMS 进程管理
- `frameworks/native/services/surfaceflinger/` — SurfaceFlinger

[已验证: AOSP android-17.0.0_r1, frameworks/base/ 结构]

**第二步：增量编译并推送。** 修改完 Java 文件后，增量编译只需要针对修改的模块：

```bash
# 编译 framework（包含修改）
m framework -j$(nproc)

# 推送到设备（Cuttlefish 或 userdebug 设备）
adb root
adb remount
adb shell stop
adb sync system

# 重启 framework
adb shell start
```

ADB man page 里的 `sync` 只接受 `all`、`data`、`odm`、`oem`、`product`、`system`、`system_ext`、`vendor` 这些分区参数，不接受 `framework` 这种模块名。`framework.jar` 属于 `system` 分区，所以这里应该用 `adb sync system`。如果只想替换单个文件，也可以直接：

```bash
adb push out/target/product/<device>/system/framework/framework.jar /system/framework/
```

[已验证: 官方文档, https://android.googlesource.com/platform/packages/modules/adb/+/android-17.0.0_r1/docs/user/adb.1.md]

`stop` / `start` 会重启 Java 层的 System Server 进程（zygote 会重新 fork），所有 App 进程也会随之重启。这比完整的 `adb reboot` 快得多，通常几秒钟就能回到桌面。

对于 Native 层的修改（如 SurfaceFlinger），流程类似但需要重启对应的服务：

```bash
m surfaceflinger -j$(nproc)
adb root
adb remount
adb sync system
adb shell killall surfaceflinger   # surfaceflinger 会自动重启
```

如果只替换单个二进制，也可以直接 push `out/target/product/<device>/system/bin/surfaceflinger` 到 `/system/bin/`。

**第三步：观察效果。** 这一步的具体手段取决于我们在验证什么。下一节会详细展开。

## 常用 Debug 手段

Framework 调试有三种重要手段：加 Log、改 SystemProperties、用 dumpsys。

### 增加 Log

在 Framework 代码中插入 `android.util.Log` 调用是最直接的观察手段：

```java
// 在 Choreographer.doFrame() 中增加耗时日志
import android.util.Log;

private static final String TAG = "Choreographer";
// ...
long startTime = System.nanoTime();
// ... doFrame 逻辑 ...
long duration = System.nanoTime() - startTime;
if (duration > 16_000_000L) {  // 超过 16ms
    Log.w(TAG, "doFrame took " + (duration / 1_000_000f) + "ms");
}
```

[已验证: 官方文档, developer.android.com/reference/android/util/Log]

在 userdebug 版本上，可以通过 `adb logcat -s TAG:LEVEL` 过滤特定 tag 的日志。对于临时调试，可以用 `setprop` 动态调整日志级别而不需要重新编译：

```bash
# 开启特定 tag 的 VERBOSE 日志
adb shell setprop log.tag.Choreographer VERBOSE
```

这个设置在重启后会失效。如果需要持久化，使用 `persist.log.tag.XXX` 前缀。

一个实用技巧：在 Perfetto Trace 中看到某个系统服务的 binder 调用耗时异常，但不确定瓶颈在哪。在对应服务的方法入口和出口各加一行 `Log.d()` 打印时间戳，然后对比 logcat 时间线和 Perfetto Trace 的时间线，就能精确到是哪个内部步骤在耗时。

### SystemProperties

SystemProperties 是 Android 系统的全局键值对配置。在 Framework 调试中，它常用于动态开关调试功能而不需要重新编译：

```java
// 在代码中读取一个调试开关
if (SystemProperties.getBoolean("debug.hwui.profile", false)) {
    // 开启 HWUI 性能 profiling
}
```

对应的 shell 操作：

```bash
# 读取
adb shell getprop debug.hwui.profile

# 设置（立即生效，重启后失效）
adb shell setprop debug.hwui.profile true

# 持久化设置
adb shell setprop persist.debug.hwui.profile true
```

[已验证: 官方文档, source.android.com/docs/core/architecture/configuration/add-system-properties]

Android 17 基线推荐用 Sysprop API（`.sysprop` 文件）定义新的 Framework 调试开关，而不是直接调 `SystemProperties.get()`。Sysprop API 会生成类型安全的 Java/C++/Rust 接口，避免运行时的类型转换错误。

### dumpsys

`dumpsys` 是查看系统服务内部状态的窗口。它通过 binder 调用各系统服务的 `dump()` 方法，获取服务的运行时快照：

```bash
# 列出所有可 dump 的服务
adb shell dumpsys -l

# 查看 SurfaceFlinger 的 Layer 信息
adb shell dumpsys SurfaceFlinger

# 查看某个 App 的帧渲染数据
adb shell dumpsys gfxinfo com.example.app

# 查看 Activity 栈
adb shell dumpsys activity activities

# 查看内存信息
adb shell dumpsys meminfo com.example.app
```

[已验证: 官方文档, developer.android.com/studio/command-line/dumpsys]

对于性能分析，几个高频使用的 dumpsys 子命令值得记住：

- `dumpsys gfxinfo <package> framestats` — 输出最近 120 帧的渲染时间线，可以用来计算 jank 率
- `dumpsys cpuinfo` — 当前各进程的 CPU 使用率快照
- `dumpsys meminfo --checkin <package>` — 以 checkin 格式输出内存数据，方便脚本化分析
- `dumpsys activity processes` — 所有进程的 oom_adj 和 LRU 状态

当我们在 Perfetto 中观察到某个现象（比如某个 App 的主线程被大量 GC 暂停打断），可以用 `dumpsys meminfo` 来看该 App 当时的内存分布是否异常，两者对照分析。

## ADB Root 与 System 分区快速调试

在 userdebug 版本上，`adb root` 可以获取 root shell 权限，这为快速调试打开了更多可能：

```bash
adb root
adb remount    # 首次可能提示先 adb disable-verity 并重启
```

`adb remount` 在动态分区设备上通常借助 OverlayFS 提供可写层，在只读的 system 分区上叠加一个可写层。这样可以直接 push 修改后的文件到 `/system/` 下，而不需要重新刷入完整镜像。首次在某台 userdebug 设备上操作时，往往还需要先 `adb disable-verity` 并重启，然后再执行 `adb remount`。

[已验证: 官方文档, source.android.com/docs/setup/build/adb]

快速调试流程：

```bash
# 1. 增量编译单个模块
m framework -j$(nproc)

# 2. 获取 root 权限并重新挂载
adb root
adb remount

# 3. 直接 push 修改的文件
adb push out/target/product/<device>/system/framework/framework.jar /system/framework/

# 4. 重启 framework
adb shell stop && adb shell start
```

这一步有两个边界。`adb remount` 可能要求先关闭 dm-verity，这会降低设备安全性，不应在生产设备上使用。部分系统分区在 Android 12+ 使用了 EROFS 等只读文件系统，`adb remount` 能否工作取决于设备的分区方案和 OverlayFS 支持。

## Pixel 设备刷入自编译 ROM

对于需要在真实硬件上验证的场景（比如 GPU 合成路径、调度器行为），Cuttlefish 和 Emulator 无法完全替代真机。Pixel 设备因为 bootloader 可解锁，factory image 和 driver binaries 资料也相对完整，仍然是最常见的 AOSP 真机验证平台之一。

刷机的基本流程：

```bash
# 1. 解锁 bootloader（会清除所有数据）
adb reboot bootloader
fastboot flashing unlock

# 2. 下载对应 Pixel 型号的驱动二进制
# 从 developers.google.com/android/drivers 下载并解压到 AOSP 根目录
# 执行 extract.sh 脚本安装驱动

# 3. 选择 Pixel 对应的 lunch target
lunch aosp_oriole-userdebug    # 以当前 branch 中实际存在的 Pixel target 为准

# 4. 编译
m -j$(nproc)

# 5. 刷入
adb reboot bootloader
fastboot flashall -w
```

[已验证: 官方文档, source.android.com/docs/setup/download]

真机验证至少要分三条资源线看：

| 资源 | 当前公开情况 | 用途 |
|:--|:--|:--|
| Factory Images / Full OTA | 公开，Google 仍持续提供 | 回退基线、恢复官方系统 |
| Driver binaries / vendor image | 公开，`developers.google.com/android/drivers` 仍可看到 Pixel 8、8a、9、9a、9 Pro Fold 等条目 | 让 AOSP 构建补齐闭源硬件支持 |
| 设备树 / 硬件仓库 / kernel history | `[待验证]`，不同机型和分支公开程度不一致 | 决定是否能直接按某个 Pixel target 完整编译 |

[已验证: 官方文档, https://developers.google.com/android/drivers]

设备树公开策略、kernel history、driver binaries 是三条不同的线，不应混淆。当前至少可以确认 driver binaries 页面还在更新新款 Pixel 条目，但这不等于每个机型都保留了同等完整的公开设备树。做真机计划前，先核对目标机型在当前 AOSP branch 里是否还有可用 target，再核对 factory image 和 driver binaries 页面是否具备对应资源。

## 常见问题与误区

**「macOS 可以编译 AOSP」**。从 Android 11 开始，macOS 不再是官方支持的编译平台。虽然有 workaround（创建 case-sensitive APFS 卷、使用 Docker），但构建过程中会频繁遇到路径大小写问题，尤其是涉及到 C/C++ 头文件 `#include` 的大小写不一致时。节省折腾的时间，直接用 Ubuntu 虚拟机或远程 Linux 服务器。

**「eng 版本更适合性能分析」**。正好相反。eng 版本默认开启了大量调试功能（assert、详细日志、调试工具），这些开销会影响调度延迟、GC 行为、渲染管线等几乎所有性能相关的指标。做性能分析时，应该使用 `userdebug` 版本，它最接近用户实际使用的 `user` 版本，同时保留了足够的调试能力。

**「全量编译每次都要等几小时」**。Ninja 的增量编译在 AOSP 上非常高效。修改一个 Java 文件后，`m framework` 通常只需 30 秒到 2 分钟。只有修改了 `Android.bp` 构建描述文件或触发了全量依赖重建时，才需要较长的编译时间。善用模块级编译（`m <module>`）而非全量编译（`m`），可以大幅缩短调试循环。

**「刷 Pixel 就能跑自编译 AOSP」**。这条经验在新旧机型上的成立条件不同。Pixel 的 factory image 和 driver binaries 页面仍在更新，真机验证通道没有消失；受限的是部分设备树、硬件仓库和公开提交历史。对刷机和回归验证，先核对三样东西：当前 branch 有没有可用的 lunch target、drivers page 有没有对应 vendor image、factory images page 有没有同版本基线。缺一项时，Cuttlefish 往往更稳。

## 与其他章节的关系

本节是 AOSP 编译和调试的基础设施。§15.7 AOSP 代码阅读介绍了如何在源码中定位感兴趣的系统服务，本节则解决定位之后「怎么改、怎么验证」的问题。§16.1 和 §16.2 讨论了 Google 官方的性能优化思路和各版本变化，理解这些内容需要在 AOSP 源码中找到对应的改动点，同样依赖本节搭建的编译调试环境。§14.7 中 Perfetto 的高级用法（如自定义 Track、atrace 分类）可以直接在 userdebug 设备上验证，不需要编译 AOSP；但如果需要验证框架层的 trace 点是否准确，就需要回到本节的流程。

## 参考资料

- AOSP 构建要求：source.android.com/docs/setup/start/requirements
- 下载 AOSP 源码：source.android.com/docs/setup/download
- 构建系统概览：source.android.com/docs/setup/build
- Cuttlefish 设置：source.android.com/docs/devices/cuttlefish/get-started
- adb 与 fastboot：source.android.com/docs/setup/build/adb
- SystemProperties：source.android.com/docs/core/architecture/configuration/add-system-properties
- dumpsys 参考：developer.android.com/studio/command-line/dumpsys
- Android Log API：developer.android.com/reference/android/util/Log
- Pixel 驱动二进制：developers.google.com/android/drivers
- Sysprop API：source.android.com/docs/core/architecture/configuration/sysprops-apis
