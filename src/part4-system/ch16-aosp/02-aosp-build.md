---
title: AOSP 源码编译与调试环境
chapter: '16.2'
status: finalized
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
pipeline_stage: ready-to-publish
applicable_versions: Android 11 (API 30) - Android 17 (API 37)
last_verified: '2026-08-14'
last_verified_against: AOSP android-17.0.0_r1 + android-latest-release pointing to android17-release + current Android 17 build/Cuttlefish docs + android17-6.18-2026-06_r6
confidence: high
sources:
- type: official
  path: https://source.android.com/docs/setup/start/requirements
- type: official
  path: https://source.android.com/docs/setup/download
- type: official
  path: https://source.android.com/docs/setup/about/faqs
- type: official
  path: https://source.android.com/docs/setup/build
- type: official
  path: https://source.android.com/docs/setup/build/building
- type: official
  path: https://source.android.com/docs/setup/test/running
- type: official
  path: https://source.android.com/docs/devices/cuttlefish/get-started
- type: official
  path: https://source.android.com/docs/devices/cuttlefish/webrtc
- type: official
  path: https://android.googlesource.com/platform/packages/modules/adb/+/android-17.0.0_r1/docs/user/adb.1.md
- type: official
  path: https://source.android.com/docs/core/architecture/configuration/add-system-properties
- type: official
  path: https://source.android.com/docs/core/architecture/configuration/sysprops-apis
- type: official
  path: https://source.android.com/docs/setup/build/building-kernels
- type: official
  path: https://source.android.com/docs/core/architecture/kernel/gki-android17-6_18-release-builds
- type: official
  path: https://developers.google.com/android/drivers
section: '16.2'
tags:
- aosp
- build
- soong
- ninja
- emulator
- cuttlefish
- debug
related_chapters:
- '16.1'
- '15.6'
- '14.8'
---

# AOSP 源码编译与调试环境

阅读源码可以说明一条路径“可能怎样运行”，构建、启动和测量才能说明目标版本“当前怎样运行”。Framework（Android 系统框架层）调试依赖一套完整过程：固定源码版本，修改最小代码面，编译所属模块，把产物同步到匹配的设备镜像，再用测试、日志和 trace（性能轨迹）验证。

平台源码固定为 Android 17 / API 37 / `android-17.0.0_r1`。Android 内核使用独立源码树和构建系统，内核核验锚点固定为 `android17-6.18-2026-06_r6`。两个 tag（固定源码快照的标签）不能互换，也不能用平台仓库中的预编译 kernel 反推它对应哪个 Android Common Kernel 提交。

## 构建主机：先满足官方基线

Android 17 的官方构建文档要求 64 位 x86 Linux 主机、glibc 2.17 或以上、至少 400 GB 可用磁盘和至少 64 GB 内存。glibc 是 GNU C Library，也是 Linux 基础运行库。

400 GB 由约 250 GB checkout 与约 150 GB 构建产物组成；checkout 指检出的完整源码工作区。做多 target、多工作树或内核构建时还要预留更多空间；这里的 target 是产品、发布配置与构建变体的组合。

官方给出的构建时间样例是：72 核、64 GB 内存的 Google 主机完成全量构建约 40 分钟，6 核、64 GB 主机约 6 小时。这组数字只用于说明硬件差距，不能当作任意 Android 17 target 的耗时承诺。磁盘 I/O（输入输出）、内存带宽、远程文件系统、目标产品和当次依赖图都会改变耗时。

主机软件边界如下：

- 官方的 Android 11 及以上依赖安装命令以 Ubuntu 18.04 或更新版本为基线；主机总要求允许其他满足 glibc 条件的 64 位 Linux 发行版，但要自行映射软件包。
- AOSP 从 2021 年 6 月 22 日起不再支持 macOS 平台构建。
- 最新 release checkout 已携带 OpenJDK、Make 和 Python 3 预编译版本，不要额外改动 JDK 版本覆盖它们。
- Cuttlefish 还要求 KVM（Kernel-based Virtual Machine，Linux 内核虚拟机）。云主机和虚拟机需要额外确认嵌套虚拟化，也就是能否在虚拟机内再次运行虚拟机，并检查 `/dev/kvm` 权限。

下面的命令用于在 Ubuntu 18.04 及以上安装官方列出的基础依赖：

```bash
sudo apt-get update
sudo apt-get install git-core gnupg flex bison build-essential \
  zip curl zlib1g-dev libc6-dev-i386 x11proto-core-dev \
  libx11-dev lib32z1-dev libgl1-mesa-dev libxml2-utils \
  xsltproc unzip fontconfig repo
```

安装完成后运行 `repo version`，确认 Repo launcher（负责初始化源码工作区并下载完整 Repo 工具的启动脚本）可以工作。官方当前要求 Repo 2.4 或以上；团队环境还应记录实际版本，避免不同主机使用差异过大的 launcher。

## 固定 Android 17 源码

官方面向日常构建和贡献工作推荐 `android-latest-release`。它是供 Repo 使用的 manifest branch（清单分支），会指向最新公开 release branch；截至 2026-08-14，它指向 `android17-release`。这个指向会移动，适合跟进最新代码，不适合复现固定版本结论。

下面的命令创建固定在 `android-17.0.0_r1` 的平台 checkout：

```bash
repo init --partial-clone --no-use-superproject \
  -u https://android.googlesource.com/platform/manifest \
  -b android-17.0.0_r1
repo sync -c -j8
```

manifest 是描述各 Git 项目、存放位置和 revision（项目版本）的 XML 清单。`--partial-clone` 减少初始对象下载，`-c` 只同步当前 manifest 分支。`-j8` 来自官方示例，主机可以按网络、文件系统和服务器响应调整并发；“CPU 核数的数倍”没有通用保证。

团队需要保存可复现 manifest。下面的命令把每个项目解析到具体 revision：

```bash
repo manifest -r -o pinned-manifest.xml
git -C build describe --tags --always
```

`pinned-manifest.xml` 应与实验记录一起归档，其中每个 revision 已解析为具体提交标识。只记录 `android-17.0.0_r1` 仍可能漏掉本地 cherry-pick（把选定提交应用到当前分支）、未提交修改或后来单独切换的项目，所以还要保存 `repo status` 和补丁集标识。

## Soong、Kati 与 Ninja 的职责

AOSP 平台使用 Soong 构建系统。Soong 读取 `Android.bp`，Kati 处理仍存在的 `Android.mk`，二者生成构建图，再由 Ninja 执行图中的具体命令。日常命令 `m` 是构建环境提供的入口，开发者通常不直接调用 Ninja。

三层的故障表现不同：

- `Android.bp` 属性、模块名或可见性错误发生在 Soong 解析阶段。
- 遗留 `Android.mk` 的转换问题会出现在 Kati 阶段。
- 编译器、链接器和命令执行失败由 Ninja 报出具体 action，也就是失败的那一步构建命令。

改动构建描述后，可先运行下面的结构校验：

```bash
m nothing
```

这个构建目标会解析并验证构建结构，不生成模块产物。它通过后仍要编译受影响模块，因为类型检查、链接和生成代码错误只会在对应 action 执行时出现。

平台构建文档把 `Android.bp` 描述为语法接近 Bazel BUILD 文件。Android 17 平台的常规入口仍是 Soong；Android Common Kernel 则由 Kleaf（基于 Bazel 的 Android 内核构建规则）构建。看到 Bazel 文件不能据此把平台和内核构建命令混用。

## lunch 的三段式 target

Android 17 的 lunch target 由三段组成：

```text
product_name-release_config-build_variant
```

- `product_name` 选择产品，例如 `aosp_cf_x86_64_only_phone`。
- `release_config` 选择 feature launch flag（构建时功能开关）的发布配置，例如 `aosp_current`。
- `build_variant` 选择 `user`、`userdebug` 或 `eng`。

下面的命令使用官方文档给出的 Cuttlefish target：

```bash
source build/envsetup.sh
lunch aosp_cf_x86_64_only_phone-aosp_current-userdebug
m
```

`envsetup.sh` 会把 `lunch`、`m` 等命令加载到当前 shell，因此每个新 shell 都要执行一次。`m` 未指定 `-j` 时会自行选择并发度，先采用默认值；只有经过主机测量后才调整 `-jN`。

固定 tag 中可用的产品与 release config 以 checkout 内的定义为准。直接复制其他分支的 `trunk_staging` target 可能得到不存在的组合。拿不准时运行无参数 `lunch` 查看常用 target，并检查命令输出中的 `TARGET_PRODUCT`、`TARGET_BUILD_VARIANT`、`BUILD_ID` 和 `OUT_DIR`。

### 三种 build variant 怎么选

| Variant | 主要用途 | 性能数据边界 |
| --- | --- | --- |
| `user` | 生产配置、发布基线 | 最接近量产安全和调试配置，但缺少 root 调试能力 |
| `userdebug` | 平台开发、功耗与性能调试 | 可使用 adb root 等能力，仍与 `user` 存在配置差异 |
| `eng` | 日常功能开发、快速实验 | 调试检查和工具更多，不适合作为发布性能基线 |

Framework 修改通常用 `userdebug` 完成定位和功能验证。需要报告绝对性能数字时，再用匹配的 `user` 或量产构建复测。`userdebug` 和 `user` 之间的差异必须写入报告，不能用“足够接近”省略。

## 模块编译与产物归属

`m` 会构建当前 lunch target。小改动可以编译模块名：

```bash
m services
m surfaceflinger
```

模块名来自 `Android.bp` 的 `name`，文件路径不等于模块名。一个 Java 文件也可能进入 boot jar（开机时加载的 Framework Java 包）、APEX（可独立更新的系统组件包）或多个变体。修改前应查看同目录 `Android.bp` 及依赖，确认所属模块和安装分区。

常见源码位置包括：

- `frameworks/base/core/java/android/view/`：Choreographer、ViewRootImpl 等 Framework 类。
- `frameworks/base/services/core/java/com/android/server/`：承载主要 Framework 服务的 `system_server` 实现。
- `frameworks/native/services/surfaceflinger/`：系统显示合成服务 SurfaceFlinger。
- `frameworks/native/libs/renderengine/`：SurfaceFlinger 使用的渲染后端 RenderEngine。
- `packages/modules/`：Mainline（可独立更新的系统模块）源码；产物可能位于 APEX 或 APK。

增量构建耗时与改动触发的依赖图有关。Java API 变化、`Android.bp` 变化、生成代码、APEX 和 bootclasspath（运行时启动类路径）都可能扩大构建范围，不应承诺固定秒数。

## 用 Cuttlefish 验证 Framework

Cuttlefish 是 AOSP 的标准虚拟设备，适合验证纯 AOSP Framework 行为、CTS、系统服务和自定义测试。CTS 是 Compatibility Test Suite，即兼容性测试套件。它与真机的主要差异集中在 HAL 以及依赖具体硬件的部分；HAL 是 Hardware Abstraction Layer，即硬件抽象层。GPU 合成、热控制、SoC 调度、相机和功耗结论仍需真机；SoC 指 System on a Chip，即片上系统。

### 主机与产物必须匹配

Cuttlefish 运行前应确认 KVM：

```bash
test -e /dev/kvm
ls -l /dev/kvm
```

两个命令分别检查设备节点是否存在以及当前用户是否有权限。x86_64 主机也可以检查 CPU 的 `vmx` 或 `svm` 硬件虚拟化标志；ARM64 主机以 `/dev/kvm` 为直接依据。

ARM64 Linux 主机可以运行匹配架构的 Cuttlefish 预编译镜像。这项能力没有改变平台源码构建文档的 x86_64 主机要求；在 ARM64 主机上应把“运行预编译虚拟设备”和“本地编译完整 AOSP”分开记录。

使用 Android CI（持续集成系统）产物时，`cvd-host_package.tar.gz` 和设备 image 必须来自同一个 build，也就是同一次 CI 构建记录。主机包、镜像和分支混搭会引入协议或配置不兼容，不能靠“能启动”证明组合受支持。

解压 host package 后，在该目录启动 Cuttlefish，再用包内 ADB（Android Debug Bridge，主机与设备通信工具）检查设备。下面展示两个命令的主体，`HOME` 的处理见代码块后说明：

```bash
./bin/launch_cvd --daemon
./bin/adb devices
```

当前官方示例使用 `HOME=$PWD ./bin/launch_cvd --daemon`，只为这一条命令临时指定运行目录；不要在用户 shell 中永久改写 `HOME`。具体版本仍以同 build 的启动说明为准。Cuttlefish 会向 ADB 注册设备，通常不需要手工连接 `0.0.0.0:6520`。`0.0.0.0` 是监听地址语义，也不适合作为客户端目标。多实例环境的 TCP 端口会随实例号变化。

默认启动会开启 WebRTC（浏览器实时音视频与控制协议）界面，浏览器访问 `https://localhost:8443`。跨主机访问还要配置防火墙、TLS 加密连接，以及 WebRTC 使用的 TCP/UDP 端口，不能把本地开发端口直接暴露到不可信网络。

### 编译、同步、重启

下面的命令展示 system 分区内模块的常见同步流程：

```bash
m services
adb root
adb remount
adb sync system
adb shell stop
adb shell start
```

`adb sync` 接受 `system`、`system_ext`、`product`、`vendor` 等分区名，不接受 `framework` 这类模块名。改动位于 APEX、vendor 或其他分区时，要同步对应分区。涉及 boot image、内核、APEX 激活或早期启动代码时，完整 `adb reboot` 更稳妥。

`stop` / `start` 会重启 Zygote 和依赖它的 Java 进程，设备界面会暂时消失；Zygote 负责孵化 App 的 Java 进程。这个操作不会模拟完整开机，也不会重新执行 bootloader、`init` 和 early-boot 路径。bootloader 是启动 Android 前的引导程序，`init` 是用户空间首个进程。研究系统启动时延必须执行完整重启。

Native（C/C++）服务可以单独重启，但要先确认 `init` 配置和依赖。SurfaceFlinger 崩溃或退出后通常由 `init` 拉起；这类操作会中断显示，并可能使当前测试状态失效。自动化脚本应等待服务重新注册，再开始采样。

### 把测试纳入调试循环

源码改动至少要通过三层验证：

1. 编译所属模块和相关测试。
2. 运行定向 `atest` 或模块测试。
3. 在干净 Cuttlefish 实例复现目标路径，并留存 trace、日志和 build 信息。

下面的命令用测试模块名执行定向验证：

```bash
atest FrameworksServicesTests
```

`atest` 是 AOSP 的定向测试入口，会按测试配置构建、安装并执行。模块名需要从目标目录的 `Android.bp` 或 `TEST_MAPPING`（声明目录相关测试的文件）确认；一个大型聚合测试并不能替代改动附近的单元测试。

## 调试信息：优先低扰动证据

### 日志与 Trace

在高频路径增加 Log 会改变锁竞争、调度和 I/O。Choreographer、Binder（Android 进程间调用机制）、SurfaceFlinger 等路径尤其敏感。临时日志适合确认控制流，测量时应移除或改成受控 trace 点。

如果使用动态日志级别，属性必须已经由目标代码读取并受属性策略允许。`setprop log.tag.Choreographer VERBOSE` 只会影响遵循 log tag 属性的调用，不能自动开启所有 Choreographer 诊断。日志时间戳还需要与 Perfetto（Android 系统性能追踪工具）使用的时钟域对齐后再做关联。

### System properties

系统属性是供系统范围共享配置的键值项，受命名、类型、稳定性、分区边界、`property_contexts` 和 SELinux 规则控制。`property_contexts` 把属性名映射到安全上下文与数据类型；SELinux 是 Android 的强制访问控制机制。shell 不能任意创建可写的 `persist.debug.*` 属性。`persist` 只应在确有跨重启需求且系统属性是合适载体时使用。

Android 17 平台新增属性时，流程包括：

1. 明确 owner（属性所属分区）、读写进程与跨分区稳定性。
2. 在 sepolicy（SELinux 策略源码）定义属性类型和访问规则。
3. 在 `property_contexts` 绑定名称、上下文与数据类型。
4. 优先用 `.sysprop` 描述文件和 `sysprop_library` 构建模块生成 Java、C++、Rust 类型安全 API。
5. 补充 API 文件、单元测试和拒绝访问测试。

低层 `android.os.SystemProperties` 仍存在，但官方建议在可行时使用 Sysprop API。读取某个现有属性前要找到它的定义和消费者；看到 `getprop` 有值不能说明目标代码一定会在运行时重新读取。

### dumpsys

下面这些命令取得系统服务的当前快照：

```bash
adb shell dumpsys -l
adb shell dumpsys activity processes
adb shell dumpsys meminfo com.android.systemui
adb shell dumpsys gfxinfo com.android.systemui framestats
adb shell dumpsys SurfaceFlinger
```

`dumpsys` 通过 Binder 调用服务的 dump 接口，执行本身也有开销。输出通常是某一时刻的状态或有限历史，不能替代连续 trace。分析卡顿时可用 Perfetto 定位时间段，再用 `dumpsys` 补充进程、内存、显示 Layer 或服务配置。

## adb root、remount 与 OverlayFS

`adb root` 和 `adb remount` 面向 `userdebug`、`eng` 或明确支持调试的构建。量产 `user` 构建通常不提供同等能力。首次 remount 可能需要关闭 verity 并重启：

```bash
adb root
adb disable-verity
adb reboot
adb wait-for-device
adb root
adb remount
```

关闭 dm-verity（块级文件系统完整性校验）会降低设备保护，只能用于隔离的开发设备。动态分区和只读文件系统通常通过 OverlayFS 覆盖：只读下层保持不变，修改写入可写上层。重刷、清理 overlay 或切换镜像会使这些修改消失。

单文件 push 的风险高于分区同步：类路径中可能还有 dexpreopt（构建期 DEX 预编译）产物、架构变体、映射表或关联 APEX。稳妥做法是确认 Soong 安装路径，使用对应分区的 `adb sync`，再执行满足该组件激活条件的重启。

## Pixel 真机：先核对四个条件

Cuttlefish 无法给出 SoC 调度、热、GPU、相机和功耗的量产结论，真机仍然必要。把自编译 AOSP 刷入 Pixel 前，需要同时确认：

1. 当前平台 tag 中存在目标产品和 lunch 配置。
2. driver binaries（设备专用闭源支持文件）与设备、平台 build 匹配。
3. bootloader 和 radio 固件满足该系统镜像要求。
4. 设备允许 OEM unlocking（解锁引导加载程序），且已备份全部数据。

官方说明：AOSP 可以直接运行在 Cuttlefish 上，物理硬件则需要设备专用闭源库。driver binaries 以自解压脚本提供，接受许可证后把文件和 Make 配置安装到 `vendor/`。页面出现某个 Pixel 型号，只能证明 Google 提供过相应二进制；仍要检查当前 tag 的产品配置。

解锁和全量刷写的官方命令如下：

```bash
adb reboot bootloader
fastboot flashing unlock
fastboot flashall -w
```

`fastboot flashing unlock` 和 `fastboot flashall -w` 都会涉及数据清除；前者由设备端再次确认，后者的 `-w` 会清除 `/data` 分区。刷写前应记录 factory image（官方出厂镜像），并准备官方恢复路径。平台调试设备不应保存个人数据或生产凭据。

## Android 17 内核必须单独构建

AOSP 平台树主要包含预编译 kernel binary，完整 kernel 源码、工具链和构建规则位于独立 kernel checkout。Android 17 的新 GKI（Generic Kernel Image，通用内核镜像）分支是 `android17-6.18`，内核核验 release tag 为 `android17-6.18-2026-06_r6`。

Android 13 起的现代 Android Common Kernel 使用 Bazel/Kleaf。`build.sh` 在 Android 14 及以上不受支持。典型 GKI arm64 distribution target 是：

```bash
tools/bazel run //common:kernel_aarch64_dist
```

该命令运行 Kleaf 的标准 distribution target，生成一组可分发内核产物。复现 r6 时还要确认 common 仓库精确 tag、manifest revision、Kleaf 配置和输出摘要。单个 GKI Image 不包含设备 vendor modules、DTBO、`vendor_boot` 分区、签名和 KMI 兼容性处理；vendor modules 是厂商内核模块，DTBO 是设备树覆盖镜像，KMI 是 Kernel Module Interface，即内核模块接口。

Cuttlefish 可以通过 `cvd create` 指定 kernel 与 initramfs（启动早期使用的内存文件系统）产物，适合验证 Android Common Kernel 与平台的组合。物理设备还需要厂商模块和设备启动链；把 GKI Image 单独刷入任意 Pixel 并不构成完整方案。

## 性能实验的构建记录

每次实验至少保存这些字段：

| 类别 | 字段 |
| --- | --- |
| 平台源码 | manifest、tag、local diff、build ID |
| 构建配置 | product、release config、variant、关键 aconfig（平台功能开关配置）与 build flags |
| 运行设备 | serial、build fingerprint、页大小、SELinux/verity 状态 |
| 运行时 | ART/Mainline 模块版本、是否 remount、是否有额外日志 |
| 内核 | `uname -a`、GKI tag、vendor modules、启动参数 |
| 测试 | 用例 revision、数据集、轮次、温度与电源条件 |

`userdebug`、Cuttlefish、remount、附加 Log、关闭 verity 都会改变环境。报告中保留这些信息，其他人才能判断结果适合功能验证、方向判断，还是量产性能结论。

## 常见故障判断

### `lunch` 找不到 target

先检查命令是否来自当前 shell 的 `envsetup.sh`，再核对三段式 product、release config 和 variant。旧文章里的两段式 target 或其他分支的 `trunk_staging` 不能直接套到 Android 17 tag。

### `m` 没有重编修改文件

检查文件是否属于预期 Soong module，生成源码是否来自另一输入，当前 `OUT_DIR` 是否对应同一 target，以及设备上是否仍运行旧分区或旧 APEX。修改路径与安装模块没有一一对应关系。

### 同步后行为没有变化

用 `adb shell` 检查设备端文件哈希和 build fingerprint，确认同步分区正确。APEX、boot jar、native service 和 early-boot 代码需要不同的激活方式，`stop` / `start` 只覆盖其中一部分。

### Cuttlefish 结果和真机不同

先确认差异是否位于 HAL、kernel、GPU、thermal（热管理）、Power HAL 或 vendor service。纯 Framework 状态机更适合在 Cuttlefish 复现；硬件相关性能必须回到目标设备。

## 参考资料

- [AOSP 构建主机要求](https://source.android.com/docs/setup/start/requirements)
- [下载 Android 源码](https://source.android.com/docs/setup/download)
- [AOSP FAQ：android-latest-release](https://source.android.com/docs/setup/about/faqs)
- [AOSP 构建系统概览](https://source.android.com/docs/setup/build)
- [构建 Android](https://source.android.com/docs/setup/build/building)
- [Fastboot 与刷写](https://source.android.com/docs/setup/test/running)
- [Cuttlefish 入门](https://source.android.com/docs/devices/cuttlefish/get-started)
- [Cuttlefish WebRTC](https://source.android.com/docs/devices/cuttlefish/webrtc)
- [`android-17.0.0_r1` adb man page](https://android.googlesource.com/platform/packages/modules/adb/+/android-17.0.0_r1/docs/user/adb.1.md)
- [添加系统属性](https://source.android.com/docs/core/architecture/configuration/add-system-properties)
- [Sysprop API](https://source.android.com/docs/core/architecture/configuration/sysprops-apis)
- [构建 Android kernel](https://source.android.com/docs/setup/build/building-kernels)
- [android17-6.18 GKI release builds](https://source.android.com/docs/core/architecture/kernel/gki-android17-6_18-release-builds)
- [Pixel driver binaries](https://developers.google.com/android/drivers)
