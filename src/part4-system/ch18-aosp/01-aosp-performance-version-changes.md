---
title: AOSP 性能优化与 Android 版本变更
section: '18.1'
chapter: '18.1'
status: finalized
applicable_versions: Android 4.1 (API 16) - Android 17 (API 37)
last_verified: '2026-08-14'
last_verified_against: AOSP android-17.0.0_r1 + android17-6.18-2026-06_r6 + current Android 17 behavior-change, Mainline, GKI and ART documentation
confidence: high
tags:
- android
- performance
- aosp
- methodology
- version-changes
- behavior-changes
- api-evolution
- migration
- performance-api
- android17
- api37
- deliqueue
- generational-gc
- profiling-manager
- cloud-compilation
related_chapters:
- '16.2'
- '16.3'
- '16.5'
- '16.7'
- '18.2'
- '18.3'
- '1.2'
- '2.1'
- '4.5'
- '5.3'
- '6.3'
- '9.1'
- '14.1'
- '15.7'
- '1.8'
- '4.6'
- '8.2'
- '17.1'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
consolidated_from:
- 16.1 Google 官方的性能优化思路中的平台方法、工具选择与设备验证边界
- src/part4-system/ch18-aosp/01-google-optimization.md
- src/part4-system/ch18-aosp/02-version-changes.md
- src/part4-system/ch18-aosp/05-android17-api37-performance-changes.md
sources:
- type: official
  path: https://developer.android.com/topic/performance/overview
- type: official
  path: https://developer.android.com/about/versions/17/behavior-changes-17
- type: official
  path: https://source.android.com/docs/core/ota/modular-system
- type: official
  path: https://source.android.com/docs/core/architecture/kernel/android-common
- type: official
  path: https://source.android.com/docs/core/runtime/configure
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/java/com/android/server/SystemServer.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/ProcessState.cpp
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/
- type: official
  path: https://developer.android.com/about/versions/12/behavior-changes-12
- type: official
  path: https://developer.android.com/about/versions/12/behavior-changes-all
- type: official
  path: https://developer.android.com/about/versions/13/features
- type: official
  path: https://developer.android.com/about/versions/14/behavior-changes-all
- type: official
  path: https://developer.android.com/about/versions/14/behavior-changes-14
- type: official
  path: https://developer.android.com/about/versions/15/behavior-changes-15
- type: official
  path: https://developer.android.com/about/versions/16/features
- type: official
  path: https://developer.android.com/about/versions/16/behavior-changes-16
- type: official
  path: https://developer.android.com/about/versions/17/release-notes
- type: official
  path: https://developer.android.com/about/versions/17/behavior-changes-all
- type: official
  path: https://developer.android.com/about/versions/17/changes/messagequeue
- type: official
  path: https://developer.android.com/reference/android/os/ProfilingManager
- type: official
  path: https://developer.android.com/reference/android/os/ProfilingTrigger
- type: official
  path: https://developer.android.com/reference/android/os/PerformanceHintManager.Session
- type: official
  path: https://source.android.com/docs/core/architecture/16kb-page-size/16kb
- type: official
  path: https://source.android.com/docs/core/interaction/neural-networks
- type: source
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc
- type: source
  path: https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingManager.java
- type: official
  path: https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html
- type: official
  path: https://developer.android.com/about/versions/17/features
- type: official
  path: https://developer.android.com/reference/android/app/job/JobScheduler
- type: official
  path: https://developer.android.com/guide/topics/resources/runtime-changes
- type: official
  path: https://developer.android.com/about/versions/17/changes/ff-restrictions-ignored
- type: official
  path: https://developer.android.com/privacy-and-security/security-config
- type: official
  path: https://developer.android.com/privacy-and-security/local-network-permission
- type: official
  path: https://developer.android.com/guide/practices/page-sizes
- type: official
  path: https://developer.android.com/about/versions/17/changes/bg-audio
- type: source
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/CombinedMessageQueue/MessageQueue.java
- type: source
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/res/values/attrs_manifest.xml
- type: source
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/runtime.cc
- type: source
  path: https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java
- type: source
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java
- type: source
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java
last_consolidated_at: '2026-08-24'
---

# AOSP 性能优化与 Android 版本变更

AOSP（Android Open Source Project，Android 开源平台）的性能改动会改变多个 App 共用的执行路径，收益可能覆盖整台设备，回归也可能让原本正常的兼容性、稳定性、功耗或安全行为退步。本文先讨论怎样界定、验证和交付一项 AOSP 性能改动，再梳理 Android 12—17 的版本变化与 Android 17 应用适配；ART（Android Runtime，Android 运行时）、Binder（Android 的进程间通信机制）、图形和内核的具体机制由各专项正文承载。

AOSP 性能优化要先确定问题属于应用、framework、runtime、native 服务还是内核，再固定源码标签和设备实现。版本追踪用于识别责任边界变化，Android 17 适配则落到具体 API、flag 和行为验证。

## 从现象到源码层级和责任模块

### 先判断问题是否属于平台

同一个用户现象可能来自不同责任层。只有证据指向公共路径，或 App 无法在公开接口与文档约定内避开问题时，才应优先修改平台。

| 现象 | 更像应用问题的证据 | 更像平台问题的证据 |
| --- | --- | --- |
| 冷启动慢 | 主线程业务初始化、同步 I/O、依赖注入占主导 | 多个应用共同等待 system service、ART 或存储公共路径 |
| 掉帧 | View 遍历、图片解码、每帧分配集中在单个应用 | 同机多应用出现相同合成、调度或驱动等待 |
| Binder 延迟 | 调用次数过多、事务过大、服务端业务锁 | 多个调用方同时遇到线程池、driver 或公共服务拥塞 |
| 内存压力 | 单个进程缓存、泄漏或对象峰值异常 | reclaim、LMKD、freezer 或产品参数使整机工作集反复失效 |
| 后台任务延迟 | 约束、配额或生命周期使用错误 | 平台 controller、时钟或状态传播出现回归 |

system service 是运行在系统进程、向 App 或其他系统组件提供能力的服务。表中的 reclaim 是内核回收内存页，LMKD（Low Memory Killer Daemon）会在内存压力下选择进程终止，freezer 会暂时冻结合适的后台进程；platform controller 则是判断后台任务何时满足运行条件的控制模块。

判断不能只靠一次 trace（按时间记录线程、进程和系统事件的运行轨迹）。先找同版本、同设备上的对照 App，再比较不同版本、设备和 compatibility change（用于单独启停行为变化的兼容性开关）。问题只有在这些平台变量变化时稳定跟着移动，才有足够依据继续检查 framework（Java/Kotlin 平台层）、ART、native service（原生系统服务）或 kernel（内核）。

### 用五层模型定位改动面

平台性能路径可以按五层阅读。这五层用于确认成本和对外行为边界落在哪里，不对应团队组织架构。

1. **应用与公开 API**：调用频率、参数规模、target SDK（App 声明适配到的 API 级别）和公开行为约定。
2. **Framework 与 system service**：Java/Kotlin 状态机、Binder 服务、锁和生命周期。
3. **Native service 与运行时**：ART、SurfaceFlinger（显示合成服务）、media、netd（网络管理服务）、libbinder 等原生进程或库。
4. **Kernel 与驱动**：调度、内存、Binder driver（Binder 的内核驱动）、文件系统、block I/O（面向存储块设备的读写）和设备驱动。
5. **硬件与产品策略**：SoC（System on Chip，片上系统）、固件、Power/Thermal HAL（电源与温控的硬件抽象层）、显示和厂商配置。

一次等待可能跨越多层。例如同步 Binder 的调用方处于 `Sleeping`，只说明它正在等回复；真正的耗时可能来自目标线程的 runnable delay（线程已可运行、却仍在调度队列等待的时间）、服务端锁、TEE（Trusted Execution Environment，可信执行环境）、块设备或驱动。分析时应同时保留调用方、目标进程、内核等待和硬件状态，再判断哪一层造成了等待，不能根据最先看到的层直接下结论。

### 三类证据共同约束结论

#### 公开接口与行为约定

release notes（版本说明）、behavior changes（行为变更文档）、SDK 文档和 source.android.com 说明外部可以依赖什么。这些公开约定决定兼容性和迁移边界，却通常不会给出目标设备的实际启用状态。

#### 固定版本源码

源码用于回答实现、gate（决定代码路径是否启用的条件或开关）、默认值和失败路径。平台结论固定到 `android-17.0.0_r1`，内核结论固定到 `android17-6.18-2026-06_r6`。tag 是可复查的固定源码版本；main 是持续变化的开发分支。GKI（Generic Kernel Image，通用内核镜像）还有多条受支持分支，读取其他分支只能说明机制如何演进，不能反推这里固定的 tag。

#### 设备运行证据

最终产品还会受到 aconfig、DeviceConfig、Mainline 模块、vendor（设备或芯片厂商）配置、kernel config、boot 参数和硬件能力影响。aconfig 与 DeviceConfig 都可承载平台功能开关，但生效阶段和更新方式不同；Mainline 则把部分系统组件做成可独立更新的模块。设备结论至少需要 build fingerprint（唯一标识系统构建的一组属性）、target SDK、ART/APEX（系统模块容器）版本、kernel release 和相关功能状态；trace、dump（状态或内存转储）与实验结果再说明本次 workload（受测操作）实际走到哪条路径。

源码中存在某个函数、内核配置项默认 `y`，或系统版本号满足要求，都不能单独证明目标设备已经启用该功能。产品配置、模块版本或运行时开关还可能改变最终状态。

### 把版本与交付路径拆开

Android 大版本不是唯一版本轴。同一项优化通过哪条路径交付，决定它能覆盖哪些设备以及如何回滚。

| 交付对象 | 常见载体 | 需要额外记录 |
| --- | --- | --- |
| Framework / system image | 整机 OTA | build ID、产品 overlay、target SDK 行为 |
| Mainline 模块 | APEX/APK 系统更新 | 模块版本、激活状态、回滚记录 |
| GKI / vendor kernel | boot/vendor_boot 或 OTA | 精确 tag、最终 `.config`、vendor module 与启动参数 |
| Vendor service / HAL | vendor 分区或厂商 OTA | 接口版本、SoC/固件、产品配置 |
| 应用编译输入 | APK/AAB、DM、Profile | 安装来源、compiler filter、产物位置 |

OTA（Over-the-Air）是设备通过网络接收的系统更新；product overlay 是产品对平台资源或配置的覆盖。`boot`/`vendor_boot` 是启动相关分区，最终 `.config` 记录实际构建进内核的选项。APK 是 App 安装包，AAB 是供应用商店生成设备适配 APK 的 Android App Bundle。DM（Dex Metadata）和 Profile 为 ART 提供安装或编译输入，compiler filter 决定只做验证，还是采用不同强度的 AOT（Ahead-of-Time，运行前编译）。

Android 17 的官方兼容矩阵包含多条受支持 GKI 分支，因此不能只根据 Android 大版本推断设备内核；ART 又能作为 Mainline 模块独立更新，版本也要单独读取。target SDK 37 只会开启文档明确绑定 target 的行为；影响所有 Android 17 App 的变化还要查另一份行为变更清单。跨版本实验应把 OS、target、Mainline、kernel 和产品配置作为独立变量记录。

### 一轮平台优化怎样完成验证与交付

#### 1. 定义用户动作和完成边界

用可重复动作描述问题，例如“点击图标到首个可交互页面”“触摸事件到对应帧 present（提交到屏幕显示）”“提交安装会话到包可启动”。起点和终点应写进指标定义，不能用 CPU 利用率、函数耗时或某条 trace slice（轨迹中的一个时间区间）代替用户体验指标。

#### 2. 保存可复现实验环境

至少记录源码 revision（commit 或 tag）、local diff（尚未进入该版本的本地改动）、产品 target（AOSP 编译所选的设备产品目标）、build variant（`user`、`userdebug` 或 `eng` 构建类型）、设备与内核、页大小、刷新率、编译状态、温度、电源条件、测试脚本和数据集。`userdebug` 会保留更多调试能力，root 会取得超级用户权限，关闭 verity 会停用系统分区完整性校验；这些操作以及额外日志、trace 配置都可能改变结果，必须显式标注。

#### 3. 用统计确认问题，用 trace 解释问题

多轮样本先确认 P50、P90/P95 和离散程度；P50、P90、P95 分别表示 50%、90%、95% 的样本不高于该数值。再用 Perfetto（系统级 trace 工具）、simpleperf（CPU 性能分析工具）、`dumpsys`（导出系统服务状态的命令）或模块专用统计解释慢样本。单次 trace 可以帮助判断慢样本由哪条路径造成，不能单独证明总体收益。

#### 4. 一次只改变一个主要变量

平台、kernel、vendor、配置和 App 同时变化时，无法判断结果由哪项变化造成。能用 compat change、feature flag（运行时功能开关）、build flag（构建时开关）或小补丁在同一设备做 A/B 对照时，优先使用改动前后成对比较的实验；无法隔离变量时，报告应降低结论强度。

#### 5. 同时检查副作用

平台改动除目标指标外，还要检查：

- 稳定性：crash、ANR（Application Not Responding，应用无响应）、watchdog（系统看门狗判定关键线程或服务长时间无响应）、kernel panic（内核遇到无法继续运行的致命错误）；
- 资源：CPU、内存、I/O、功耗和热状态；
- 正确性：时序、状态机、数据一致性和错误回退；
- 兼容性：旧 target、旧模块、vendor 实现和测试工具；
- 安全：权限、SELinux（Android 的强制访问控制机制）、签名、隔离和缓解机制没有被削弱。

#### 6. 把回滚路径作为实现的一部分

可配置优化要定义默认值、分批发布的设备分组、状态观测方式和回滚后的清理动作。涉及持久产物、profile、缓存或文件格式时，还要验证新旧版本交替后不会误用旧状态。

### 常见的平台优化模式

#### 删除不必要的工作

优先消除重复扫描、重复序列化、无用唤醒、过早初始化和失效产物。删除工作通常比把同一工作换线程更容易得到稳定收益，但仍要证明被删除的步骤不承担正确性或安全职责。

#### 把工作移出关键路径

预加载、异步初始化、后台 dexopt（对 DEX 字节码做验证或编译优化）和延迟服务启动，都会把 CPU、I/O 或内存成本移到另一个时间点。验收必须同时观察原关键路径和成本转移后的阶段，避免启动时间变短，首个交互或后台功耗却变差。

#### 增加并发但保留依赖

并行 driver probe（驱动探测并初始化硬件）、SystemServer 系统服务初始化或批量处理可以缩短串行阶段。依赖表达错误时，成本会变成锁等待、I/O 竞争、defer storm（依赖未就绪导致大量驱动反复推迟探测）或偶发状态错误。并发方案应有明确的 ready 条件（依赖何时算就绪）、超时、降级和取消语义。

#### 用反馈信号代替固定策略

ADPF（Android Dynamic Performance Framework，应用与系统协同提示性能需求）、thermal（温度与热节流状态）、PSI（Pressure Stall Information，CPU、内存或 I/O 压力造成停顿的统计）、headroom（距离温度或资源上限的余量）和 profile-guided optimization（根据真实执行热点指导编译优化）都利用运行信号调整决策。信号可能延迟、缺失，也会受产品实现影响；控制逻辑必须有静态回退、滞回和频率限制。滞回表示进入和退出某状态使用不同阈值，可避免读数在边界附近反复切换。

### 设备样本按瓶颈维度选择

“高端、中端、低端”不能稳定描述性能。样本应覆盖具体瓶颈：

| 维度 | 记录项 | 容易暴露的问题 |
| --- | --- | --- |
| CPU | 拓扑、频率、调度、thermal | runnable delay、锁竞争、编译 |
| 内存 | RAM、zRAM/swap、压力策略 | reclaim、GC、LMK、后台重启 |
| 存储 | 文件系统、介质、cache 状态 | major fault、数据库和资源加载 |
| 图形 | GPU、驱动、分辨率、刷新率 | RenderThread、fence、合成 deadline |
| 系统 | build、模块、kernel、target | feature gate、兼容行为和厂商差异 |

zRAM 是用内存中的压缩块充当交换空间，swap 是把暂时不用的内存页换出；reclaim 是回收可释放内存页，GC 是运行时回收不再使用的对象，LMK 是内存不足时终止进程。major fault 表示缺页时还需要从存储读取数据。RenderThread 是 App 侧执行部分硬件加速渲染工作的线程，fence 用于表示图形任务何时完成，合成 deadline 是一帧必须赶上的显示提交时限。feature gate 则是决定某条系统路径是否启用的条件。

Android Go 可以代表一类低资源配置，不能代表所有低性能或特殊瓶颈设备；高刷新率或高分辨率设备也可能更容易暴露图形预算问题。

### 审查清单

- [ ] 问题能跨应用或随平台变量稳定复现。
- [ ] 公开接口与行为约定、固定 tag 源码和设备运行证据没有互相替代。
- [ ] 平台、target、Mainline、kernel 和 vendor 版本分别记录。
- [ ] 指标包含用户动作、起止边界、样本数和分位数。
- [ ] trace 解释等待对象，统计证明总体变化。
- [ ] 实验只改变一个主要变量，或明确说明无法隔离的混杂项。
- [ ] 稳定性、资源、正确性、兼容性与安全回归已覆盖。
- [ ] feature 状态可观察，分批发布和回滚不会遗留不兼容产物。

### 与后续专题的边界

- 后文继续展开 Android 12～17 的版本、target SDK 变化与 Android 17 / API 37 应用适配。
- 18.2：固定源码、编译模块、Cuttlefish（AOSP 虚拟设备）/真机验证和实验记录。
- 18.3：Android 17 GKI 6.18 的调度、存储、AutoFDO（利用采样 profile 指导编译优化）与 MGLRU（Multi-Gen LRU，多代内存页回收算法）。
- 16.2、16.3、16.5：因果分析、指标、测试和源码阅读的通用方法。


## 版本演进与行为迁移

层级定位明确后，版本差异应按模块和用户可见行为记录，避免把发布说明直接当成设备结论。

### 为什么版本号必须进入性能结论

同一个 APK 在两个系统版本上可能走入不同的调度、进程管理和运行时路径。`targetSdkVersion` 表示 App 声明适配到的 API 级别，又会单独开启一部分兼容性变更。因此，“Android 17 上发生”还不足以描述问题；性能记录至少要包含设备系统版本、`targetSdkVersion`、Mainline（可独立更新的系统模块）版本和内核版本。

平台上限为 Android 17 / API 37 / `android-17.0.0_r1`。Android 17 对应的新 GKI（Generic Kernel Image，通用内核镜像）分支是 6.18，内核核验锚点为 `android17-6.18-2026-06_r6`。官方兼容矩阵还列出多条较早内核分支；其中 `android13-5.10` 与 `android12-5.10` 从 Android 17 QPR1（Quarterly Platform Release 1，该 Android 版本的第 1 次季度平台更新）起不再受支持。看到 Android 17 不能反推设备必然运行 6.18，仍要读取实际内核版本。

下面的“适用范围”分为两类：

- **所有 App**：只要运行在该系统版本上就受影响，通常与 `targetSdkVersion` 无关。
- **目标版本变更**：只有 App 将 `targetSdkVersion` 提升到对应 API 后才启用。

| 版本 | 性能排查时优先关注 | 适用范围 |
| --- | --- | --- |
| Android 12 / API 31 | 后台前台服务、精确闹钟、通知跳板 | 多数为 target 31 |
| Android 13 / API 33 | 通知权限、文本断字、FrameTimeline | 权限受 target 影响，渲染 API 为能力项 |
| Android 14 / API 34 | 缓存进程资源、前台服务类型、JobScheduler ANR | 同时包含所有 App 与 target 34 |
| Android 15 / API 35 | ProfilingManager、启动信息、ADPF 会话扩展、16 KB 页 | API 能力与 target 35 行为并存 |
| Android 16 / API 36 | 触发式 Profiling、作业诊断、CPU/GPU headroom、大屏适配 | API 能力与 target 36 行为并存 |
| Android 17 / API 37 | 无锁 MessageQueue、分代 CMC、新 ProfilingTrigger、App 内存限制 | 同时包含所有 App 与 target 37 |

### Android 12（API 31）：后台执行边界收窄

#### 后台启动前台服务

运行在 Android 12 及以上且 target 31 的 App，从后台启动前台服务时会受到限制。未命中官方豁免条件时，`startForegroundService()` 会抛出 `ForegroundServiceStartNotAllowedException`。这会改变后台采集、上传和周期维护任务的可达性，不能简单解释成任务“变慢”。

迁移方案要按任务语义选择：

- 可延迟、受约束的持久工作交给 WorkManager。
- 必须尽快执行且符合配额条件的短任务可以评估 expedited work。
- 用户明确发起的大文件传输应评估相应系统版本提供的用户发起数据传输机制。
- 需要持续感知的设备类场景还要评估 Companion Device Manager 等专用 API。

expedited work 是 WorkManager 中希望尽快执行、但会消耗系统配额的加急任务。WorkManager 不能替代所有 foreground service（前台服务，运行时以持续通知表明正在执行用户可感知工作）；持续导航、媒体播放、通话等场景仍有各自的前台服务类型和运行条件。

#### 精确闹钟

target 31 的 App 使用精确闹钟时，需要声明 `SCHEDULE_EXACT_ALARM` 并检查特殊应用访问状态。周期遥测通常允许时间窗口，优先采用非精确闹钟或 WorkManager。只有业务语义要求精确触发时，才接受权限、配额和省电策略带来的成本。

Android 14 又调整了新安装 App 的默认授权状态。排查闹钟延迟时，要同时记录安装来源、授权状态和目标版本。

#### 通知跳板

target 31 的 App 不能通过通知启动 BroadcastReceiver（广播接收器）或 Service（无界面组件），再由中间组件启动 Activity（界面组件）。通知点击应直接使用指向 Activity 的 `PendingIntent`，也就是交给系统稍后代表 App 执行的封装操作。迁移后，冷启动链路会少一个中间组件；收益大小取决于原有实现，不能预设固定时延。

#### Stretch Overscroll 与性能提示

Android 12 为所有 App 引入 stretch overscroll（滚动到边界后拉伸内容的过度滚动效果）。自定义滚动容器若自行处理边缘效果，需要检查重复拉伸、额外绘制和触摸反馈一致性。

`PerformanceHintManager` 也在 API 31 提供公开入口，App 可用线程组、目标工作时长和实际工作时长向系统表达持续负载。它属于 ADPF（Android Dynamic Performance Framework，应用与系统协同调整性能）的 CPU 性能提示路径，与 Game Mode 是两套 API。Game Mode 描述游戏偏好的性能或省电模式，不能代替每帧工作时长反馈。

### Android 13（API 33）：权限与帧标识能力扩展

#### 运行时通知权限

Android 13 引入 `POST_NOTIFICATIONS` 运行时权限。通知是前台服务可见性和后台任务反馈的一部分，拒绝权限不等于前台服务可以省略通知义务。性能测试需要覆盖首次授权、拒绝、升级安装和重新授权，避免把通知流程差异计入启动或任务耗时。

#### ART Mainline 更新

ART（Android Runtime，Android 运行时）可作为 Mainline 模块通过 Google Play 系统更新变化；设备的 Android 大版本相同，也不保证 ART 构建完全相同。比较启动、编译或 GC（Garbage Collection，对象垃圾回收）时，应记录 ART 模块版本，不能把一次设备观测写成全平台结论。

#### 文本断字与 FrameTimeline

Android 13 优化了断字实现，官方文档给出的上限描述是“最多约 200%”。开发者可按排版质量与成本选择 `fullFast` 或 `normalFast` 两种快速断字频率。该百分比来自平台说明，不代表任意文本、字体和语言都能复现；正文排版性能仍要用目标语料测量。

Choreographer（协调 UI 帧回调的系统类）和 NDK（Native Development Kit，原生开发工具包）`ASurfaceControl` 在 Android 13 获得 FrameTimeline（描述一帧预期与实际显示时序）相关能力。一个应用帧可能对应多个 timeline；Vsync ID 是垂直同步周期的标识，可把 App 侧帧工作与 SurfaceFlinger（系统显示合成服务）、显示流水线中的同一帧关联起来。排查卡顿时，应以帧标识对齐各阶段，少用时间戳邻近关系猜测对应关系。

### Android 14（API 34）：缓存进程和前台服务约束

#### 缓存进程的资源限制

Android 14 对所有 App 加强缓存进程管理。进程进入 cached 状态后，系统会在较短时间内限制其后台工作；动态注册的广播也可能在进程离开 cached 状态后再投递。缓存进程中的线程、网络循环或定时器不应被设计成可靠执行机制。

cached 表示进程当前没有活跃组件、可在内存压力下被终止；frozen 表示系统暂停其线程执行；killed 则表示进程已经结束。线程暂时没有获得 CPU 时间，不能单独证明进程已经 frozen；要结合 ActivityManager 状态、freezer（系统冻结进程的机制）信息和进程存活证据判断。

#### 前台服务类型

target 34 的 App 必须为前台服务声明符合用途的类型及对应权限。漏掉类型会在 `startForeground()` 时触发 `MissingForegroundServiceTypeException`，不满足运行时前置条件则可能触发 `SecurityException`。

Android 14 新增 `shortService` 等类型。`shortService` 的运行窗口约为 3 分钟，超时后系统调用 `Service.onTimeout()`，服务未及时停止会触发 ANR。它适合短而不可延后的用户可感知工作，不适合无限续期的后台循环。

#### JobScheduler 回调超时

target 34 的 App 若在 `JobService.onStartJob()` 或 `onStopJob()` 中阻塞主线程，系统会以 ANR（Application Not Responding，应用无响应）处理。Android 14 对所有 App 还会把多次 JobScheduler ANR 计入 restricted standby bucket（严格限制后台作业、闹钟和网络的待机分组）的判断。回调应快速返回，耗时工作转移到合适的执行器，并正确处理停止信号。

#### 非线性字体缩放

Android 14 将字体最大缩放提高到 200%，并采用非线性缩放。大字号文本增长更明显，已经较大的文本增长较缓。性能测试应同时检查布局重排、文本测量次数、截断和滚动范围，不能看到缩放后的布局抖动就直接判定绘制器有问题。

### Android 15（API 35）：进程内 Profiling 与 16 KB 页支持

#### ProfilingManager

`ProfilingManager` 在 API 35 加入公开 SDK。App 可以通过 `requestProfiling()` 请求 Java heap dump（Java 堆中对象与引用的快照）、heap profile（按时间或调用栈统计分配）、stack sampling（定期抽样线程调用栈）或 system trace（系统运行轨迹），并通过监听器接收结果。仅注册监听器不会开始采集；调用方还必须显式调用 `requestProfiling()`，否则会一直等待一个从未发起的结果。

它适合在用户同意和产品采样策略允许的场景中取得现场数据。系统仍会执行速率限制，并可能拒绝请求。调用方应把“请求成功提交”“收到结果”“超时或失败”记录为不同状态。

#### ApplicationStartInfo

`ApplicationStartInfo` 在 API 35 提供进程启动原因、启动类型、时间点和启动状态等结构化信息。它能减少只靠日志拼接启动阶段的歧义。时间点是否存在与启动路径有关，读取方必须检查返回数据，不能假设每个阶段都有值。

#### ADPF 会话扩展

API 35 为 `PerformanceHintManager.Session` 增加 `setPreferPowerEfficiency()` 和基于 `WorkDuration`（一轮工作的起止时间及 CPU/GPU 耗时）的 `reportActualWorkDuration()`。前者表达功耗优先偏好，后者可以报告更丰富的工作时长信息。二者都是提示，设备是否支持、系统如何响应、频点如何变化由实现和当前热状态决定。

#### 前台服务时间配额

target 35 的 App 在后台运行 `dataSync` 和 `mediaProcessing` 前台服务时，每种类型共享 24 小时内 6 小时的总配额。用户把 App 带到前台会重置计时器。配额耗尽后，系统调用 `Service.onTimeout(int, int)`；服务只有很短的停止窗口。

这里的 6 小时按同一类型的全部服务累计，不能按每个 Service 实例分别计算。迁移时需要盘点并发服务、重启路径和用户回到前台的状态转换。

#### 16 KB 页面大小

Android 15 开始支持 16 KB 页大小的 arm64（64 位 ARM 架构）设备。它在 Android 15 并未成为所有设备默认配置。含原生代码的 APK 需要检查 ELF（Executable and Linkable Format，原生可执行文件和共享库格式）段对齐、打包对齐、预编译依赖和运行期页大小假设。

页大小变化会影响页表、缺页、映射粒度和小对象驻留开销，方向取决于工作负载。只看到系统版本无法判断设备页大小，应用应通过运行期 API 或系统信息识别，并在 4 KB 与 16 KB 环境分别测量。

### Android 16（API 36）：触发式 Profiling 与诊断 API

#### 触发式 Profiling

`ProfilingManager.addProfilingTriggers()` 在 API 36 加入。App 可以登记由系统事件触发的采集规则，API 36 的公开触发类型包括 ANR 和 `APP_FULLY_DRAWN`（冷启动后调用 `reportFullyDrawn()`）。36.1 是 Android 16 的 minor SDK（小版本 API），又增加请求运行中 trace、用户强制停止、从最近任务划掉和任务管理器停止等触发类型。

触发式采集仍受系统速率限制和设备条件约束。它适合补充低复现率现场问题，不能保证每次事件都生成产物。

#### 启动、帧与作业诊断

`ApplicationStartInfo.getStartComponent()` 在 API 36 加入，用于标识触发进程启动的组件类型。启动性能数据可以按 Activity（界面）、Service（无界面组件）、BroadcastReceiver（广播接收器）、ContentProvider（数据提供组件）等入口分组，避免把不同启动原因混在同一分位数中。

`FrameMetrics.FRAME_TIMELINE_VSYNC_ID` 也在 API 36 提供。它返回当前帧 timeline 的 Vsync ID，可用于关联 HWUI（Android 的硬件加速 UI 渲染管线）、SurfaceFlinger 和 Perfetto（Android 系统性能追踪工具）中的帧记录。设备或窗口条件不支持时，分析工具应保留缺失值。

`JobScheduler.getPendingJobReasons()` 返回一个作业当前可能存在的多个等待原因，`getPendingJobReasonsHistory()` 返回近期约束变化。这里的约束包括 App 显式要求的网络、电量条件，以及系统隐式施加的配额或待机限制。后台任务“没运行”时，先读取约束历史，再检查配额、网络、电量和待机状态，比仅看一次当前状态更可靠。

#### SystemHealthManager headroom

Android 16 在 `SystemHealthManager` 提供 CPU 和 GPU headroom API。headroom 是指定时间窗口内还能使用多少处理能力的估计值。返回值适合让画质、工作量或并发度逐步调整，不能视作固定频率预算，也不能替代 Thermal API（系统温度与热节流接口）。

调用方需要遵守系统给出的最小查询间隔，处理设备不支持和无可用样本，并对连续读数做平滑。按单次读数立刻切换重负载档位，容易让工作量在两个档位间反复变化。

#### 大屏自适应

target 36 的 App 在 smallest width（最小宽度）达到 600dp 的显示上，系统会忽略一部分方向、宽高比和可调整性限制；dp 是按屏幕密度换算的布局单位。迁移重点包括窗口 resize（尺寸变化）、配置变化、状态恢复和多窗口布局。尺寸变化是否重建 Activity 取决于清单和配置处理，不能写成每次 resize 都必然重建。

target 36 还可以用 `PROPERTY_COMPAT_ALLOW_RESTRICTED_RESIZABILITY` 暂时退出该行为。target 37 会忽略这项临时退出配置，所以 Android 16 的迁移不能停留在兼容模式。

#### 预测性返回、定期任务与 edge-to-edge

target 36 的 App 运行在 Android 16 及以上时，系统默认启用 back-to-home（返回桌面）、cross-task（跨任务）和 cross-activity（跨 Activity）的预测性返回动画。旧的 `onBackPressed()` 不再收到调用，`KEYCODE_BACK` 也不再分发。AndroidX 返回分发器、平台返回回调和页面状态恢复都要一并测试；清单里的 `android:enableOnBackInvokedCallback="false"` 只适合作为临时退出手段。

`ScheduledThreadPoolExecutor.scheduleAtFixedRate()` 也有 target 36 行为变化。进程离开有效生命周期而错过多个周期后，恢复时最多立即执行一个遗漏任务。依赖“恢复后补跑全部周期”的统计或维护逻辑需要改成显式计算缺口。

对运行在 Android 16 且 target 36 的 App，系统不再接受 `windowOptOutEdgeToEdgeEnforcement` 退出配置。edge-to-edge 表示内容可以绘制到状态栏和导航栏所在区域；页面应正确处理 system bar（系统栏）、display cutout（刘海或挖孔区域）和 IME（输入法）提供的 insets（需要避让的边缘距离）。布局区域变化会影响测量、绘制和滚动范围，基准测试必须使用迁移后的最终布局。

### Android 17（API 37）：消息队列、GC 与现场诊断

#### target 37 的无锁 MessageQueue

运行在 Android 17 且 target 37 的 App 使用新的 lock-free（无锁）`MessageQueue` 实现。lock-free 表示并发竞争时系统整体仍有线程能够前进，不代表每次操作都有固定耗时；官方目标是减少锁竞争和漏帧。公开 API 语义保持兼容，依赖反射读取私有字段或方法的代码会暴露问题。

兼容层仍保留 `mMessages` 字段，但新实现下该字段始终为 `null`，它不能反映队列是否为空。测试依赖需要升级：

- Espresso 使用 3.7.0 或以上版本。
- Robolectric 使用 4.17 或以上版本，并从 `@LooperMode(LEGACY)` 迁移到 `@LooperMode(PAUSED)`。
- 自研空闲判断改用公开同步机制或 Android 16 引入的 `TestLooperManager` 能力。

可在 debuggable（允许调试器附加的）构建上用兼容性开关提前测试 `USE_NEW_MESSAGEQUEUE`。测试范围要覆盖 Handler 密集场景、IdleHandler（消息队列空闲时的回调）、同步屏障（暂时只放行异步消息的队列标记）、测试框架空闲判断和依赖反射的 SDK。

Android 17 对 target 37 App 还禁止通过反射或 JNI（Java Native Interface，Java/Kotlin 与原生代码的调用接口）修改 `static final` 字段。性能测试框架若依赖这种方式替换时钟、常量或单例，需要同步清理。

#### ART 分代 Concurrent Mark-Compact

Android 17 发布的 ART Concurrent Mark-Compact（并发标记压缩，简称 CMC）支持分代 GC。年轻代对象通常存活时间短，平台可以用更频繁、成本较低的 young collection（只覆盖年轻代的回收）处理这部分对象，再按条件执行 full collection（覆盖更大范围堆的回收）。

这项变化不能和 `userfaultfd` 混为同一开关。`userfaultfd` 是让用户空间参与处理缺页事件的 Linux 接口，CMC 使用它的演进早于 Android 17；Android 17 新增的是按对象代际选择回收范围的策略。分析时应区分 young/full collection、暂停阶段、并发标记时间、年轻对象进入老年代的晋升量，以及回收后仍驻留内存的集合。

这项 ART 改进还可以通过 Google Play system update 下发到 Android 12 及以上设备，因此“系统不是 Android 17”也不能证明它不存在。实验要同时记录 OS 版本、ART Mainline 模块版本和实际功能状态。

分代回收也不保证每个 App 都降低暂停时间。对象存活率高、跨代引用多或堆压力大时，收益会变化。结论需要来自目标设备、目标 ART 构建和稳定负载。

#### API 37 的 ProfilingTrigger

Android 17 扩充系统触发式 Profiling：

| 触发类型 | 系统事件 | 产物或行为 |
| --- | --- | --- |
| `TRIGGER_TYPE_OOM` | App 抛出 OOM（Out of Memory，内存耗尽） | Java heap dump |
| `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` | 因 CPU 过度使用被终止 | 运行中 system trace 的快照 |
| `TRIGGER_TYPE_COLD_START` | `START_TYPE_COLD` 冷启动 | 新 system trace 与 stack sampling |
| `TRIGGER_TYPE_ANOMALY` | 平台识别到 App 的异常行为 | 产物和结果 tag 由异常类型决定 |
| `TRIGGER_TYPE_APP_COMPAT` | 平台识别到未来版本将不再支持的 App 异常行为 | 产物随异常变化，结果 tag 提供兼容性信息 |

冷启动采集持续到 App 调用 `Activity.reportFullyDrawn()`，默认上限为 5 秒，并使用 discard buffer：缓冲区写满后丢弃新事件，从而保留较早的启动轨迹。未调用 `reportFullyDrawn()` 会失去业务就绪边界，只能依赖超时停止。

OOM 触发要求自定义 `Thread.UncaughtExceptionHandler` 调用默认异常处理器。若异常链被截断，系统触发无法完成，App 只能另行调用 `requestProfiling()` 请求 heap dump。

#### App 内存限制

Android 17 对所有 App 引入按设备总 RAM 设定的保守内存限制，但并非每台设备都会实施。命中限制后，`ApplicationExitInfo` 的 reason 为 `REASON_OTHER`，description 包含 `MemoryLimiter:AnonSwap`；AnonSwap 指匿名内存及其交换空间口径。只按 reason 聚合会把它和其他 `REASON_OTHER` 混在一起。

平台提供 `am memory-limiter status`、`manual` 和 `ignore` 子命令，用于查看状态、给指定 PID（进程号）施加测试限制或按 UID（App 的系统用户标识）忽略限制；不实施内存限制的设备上，这些命令不会产生对应效果。线上诊断可以结合 `TRIGGER_TYPE_ANOMALY` 获取命中内存限制时的 heap dump，但仍要考虑采样和速率限制。

#### Android 17 的 NPU 与 NNAPI 边界

Android 17 要求 target 37 的 App 在直接访问 NPU（Neural Processing Unit，神经网络处理器）时声明 `FEATURE_NEURAL_PROCESSING_UNIT`。这属于设备能力声明与访问边界，不能据此推导某个模型会自动提速。

NNAPI（Neural Networks API）的 NDK App 接口从 Android 15 起已废弃，NN HAL（神经网络硬件抽象层）仍供系统和设备实现使用。NN HAL 1.3 也早于 Android 17。`android-17.0.0_r1` 中继续存在相关代码，只能证明兼容实现仍在源码树内，不能把旧接口写成 Android 17 新增能力。

对端侧推理做版本比较时，至少固定模型、delegate（把算子交给特定加速后端的适配层）、runtime（执行模型的软件运行时）、驱动、量化方案、热状态和功耗窗口。编译缓存是否命中、burst execution（复用执行上下文以减少重复准备开销）是否可用，都要从目标实现和 trace 证据判断，不应填写通用微秒级收益。

### 新增性能 API 的演进脉络

| API | 加入版本 | 用途 | 使用边界 |
| --- | --- | --- | --- |
| `PerformanceHintManager` | API 31 | 线程组工作时长提示 | 提示不等于频点命令 |
| FrameTimeline / Vsync ID 能力 | API 33 起扩展 | 跨渲染阶段关联帧 | 以设备和具体 API 可用性为准 |
| `ProfilingManager.requestProfiling()` | API 35 | App 主动请求 profile | 有速率限制，注册监听器不会发起采集 |
| `ApplicationStartInfo` | API 35 | 结构化启动信息 | 时间点和字段可能缺失 |
| `Session.setPreferPowerEfficiency()` | API 35 | 表达功耗优先偏好 | 由系统决定响应 |
| `ProfilingManager.addProfilingTriggers()` | API 36 | 注册系统事件采集 | 触发类型跨 36、36.1、37 扩展 |
| `FRAME_TIMELINE_VSYNC_ID` | API 36 | 关联窗口帧与系统帧 | 缺失时保留 unknown（未知）值 |
| CPU/GPU headroom | API 36 | 估计资源余量 | 设备可选，限制查询频率 |
| Android 17 新 ProfilingTrigger | API 37 | 冷启动、OOM、异常 CPU 等现场数据 | 受事件条件和速率限制 |

API 级别检查只解决符号可用性。设备能力、服务是否存在、权限、配额和厂商实现仍要单独探测。

### Deprecated API 与替代路径

#### 返回手势

`Activity.onBackPressed()` 从 API 33 起废弃，时间点早于 Android 16。应用层优先使用 AndroidX `OnBackPressedDispatcher` 管理回调和生命周期；平台侧可按需求接入 `OnBackInvokedDispatcher`。预测性返回还要求界面状态在手势进行过程中可预览，单纯替换方法名不能完成迁移。

#### WebView 强制深色

Android 13 起，`WebSettings.setForceDark()` 对 target 33 App 的行为变化，并进入废弃路径。网页内容应通过 CSS 的 `prefers-color-scheme`（页面声明偏好的明暗主题）和 WebView 的算法深色策略配合。切换主题时要测量页面重排与重绘，避免在滚动中反复改动设置。

#### NNAPI NDK

NNAPI NDK 从 Android 15 起废弃。新推理方案应评估目标运行时及其 delegate，并把模型兼容性、驱动覆盖和回退路径纳入测试。HAL 继续存在不代表 App 应继续新增对废弃 NDK API 的依赖。

#### edge-to-edge 与 elegant text

`windowOptOutEdgeToEdgeEnforcement` 在 target 36 且运行 Android 16 时已经失效，替代路径是完整处理窗口 insets。`elegantTextHeight` 也在 target 36 时被忽略；受影响文字系统需要重新验证字形高度、基线、行距和裁切。

废弃标记不等于 API 会立刻消失。迁移顺序应由目标版本行为、调用频率、故障风险和替代方案成熟度共同决定。

### targetSdkVersion 升级检查表

#### target 31

- 枚举所有后台启动前台服务的入口及豁免条件。
- 检查精确闹钟授权和非精确调度的容忍窗口。
- 删除通知跳板。

#### target 33

- 覆盖通知授权的完整状态转换。
- 清理对 `onBackPressed()` 和旧深色策略的新增依赖。
- 记录 ART 主线模块版本，避免只按 OS 大版本聚合。

#### target 34

- 为每个前台服务声明精确类型、权限和运行时前置条件。
- 保证 JobService 回调快速返回。
- 在 cached 状态验证后台工作不会依赖进程持续获得 CPU。

#### target 35

- 统计 `dataSync`、`mediaProcessing` 的 24 小时累计用量。
- 实现并测试超时停止路径。
- 在 4 KB 与 16 KB 页设备验证所有原生依赖。

#### target 36

- 在 600dp 及以上窗口测试 resize、旋转、多窗口和状态恢复。
- 迁移预测性返回，覆盖 back-to-home、跨任务和跨 Activity。
- 删除对 edge-to-edge 退出属性和 `elegantTextHeight` 的依赖。
- 检查 fixed-rate 定期任务是否依赖恢复后连续补跑。
- 使用新的作业等待原因历史定位后台任务。
- 把 headroom 作为可选信号，保留 Thermal API 和静态档位回退。

#### target 37

- 提前启用 `USE_NEW_MESSAGEQUEUE` 兼容性变更，升级测试依赖。
- 搜索对 `MessageQueue` 私有成员和 `static final` 修改的反射/JNI 代码。
- 测试冷启动、OOM、异常 CPU 与内存限制的采集和退出信息解析。
- 直接访问 NPU 的 App 声明对应硬件 feature（能力声明），并处理设备不支持。

每次升级都应分开比较“系统版本变化”和“target 变化”。可在同一 Android 17 设备上用兼容性框架逐项开关行为，再用两个 target 构建复测，减少变量混杂。

### Perfetto 与平台数据如何配合

版本变化在 Perfetto 中的可见程度不同：

- 无锁 MessageQueue 的效果要从主线程调度、Handler 消息处理和帧 deadline（必须完成本帧工作的时限）观察；trace 中没有一个字段能代替兼容性检查，直接证明“无锁已启用”。
- FrameTimeline Vsync ID 可以关联应用帧、HWUI 和 SurfaceFlinger。
- GC 需要区分 young/full collection 及暂停、并发阶段；只有总 GC 次数很难解释分代策略。
- CPU/GPU headroom 是 App 可查询信号，频率、调度和热事件仍需系统 trace 辅助。
- ProfilingManager 生成独立的 profile 产物，不能假设它自动出现在当前 Perfetto 会话中。
- 前台服务配额、权限拒绝和 JobScheduler 等待原因需要结合 `dumpsys`（导出系统服务状态的命令）、API 返回和系统日志，trace 只覆盖其中一部分。

一次可复核的跨版本实验，应固定 APK、数据集、操作序列、设备温度和电源条件，并记录 OS build fingerprint（标识具体系统构建的一组属性）、target、ART/Mainline 模块、页大小和内核版本。Android 17 的内核字段若为 6.18，还要记录精确 tag；这里的核验锚点是 `android17-6.18-2026-06_r6`。


## Android 17 行为、开关与适配验证

Android 17 的变化需要在 API 级别、AOSP tag、feature flag 和 OEM 实现四个层面核对。

### 阅读边界：四组变化不能混在一起

`target SDK` 是应用通过 `targetSdkVersion` 声明的目标行为级别，它会决定一部分兼容开关。设备所运行的系统版本则决定平台实现与可用 API，二者是独立维度。

本文以 Android 17 / API 37 / `android-17.0.0_r1` 为平台锚点。性能文章很容易把 target SDK 行为、所有应用行为、公开 API 和系统实现改动写成同一种“Android 17 强制变化”，迁移时必须按触发条件分开判断。

| 类别 | 触发条件 | 涉及项目 |
|:---|:---|:---|
| target SDK 行为 | Android 17 上运行且 `targetSdkVersion >= 37` | 新 `MessageQueue`、`static final` 写保护、ECH、CT、原生动态加载、局域网权限、大屏约束 |
| Android 17 平台行为 | 运行在 Android 17；文档未声明 target SDK 门槛 | 部分设备的 app memory limits、后台音频基础限制、特定配置变化不再重建 Activity |
| API 与运行时能力 | API 37 或 Android 17 的系统组件提供能力 | `ProfilingTrigger`、`JobScheduler.getPendingJobReasonStats()`、ART 分代 CMC |
| 延续性兼容要求 | 早于 Android 17 已出现，升级时仍需满足 | 16KB 页面大小 |

这四类变化的验证方法也不同。行为开关要做兼容性 A/B，也就是在同一应用上分别启用和关闭开关；公开 API 要检查返回边界；ART 与图形实现要读 trace；16KB 要检查每个 ELF（Executable and Linkable Format，`.so` 使用的二进制格式）及其打包对齐。

### DeliQueue：重写的是消息入队争用

#### 旧队列为何会阻塞主线程

旧 `MessageQueue` 用同一个对象 monitor（Java 对象监视器锁）保护按 `when` 排序的单链表。后台线程通过 `Handler.post()` 或 `sendMessage()` 入队，Looper 线程通过 `next()` 取消息，两边会竞争同一把锁。业务回调执行期间不会持有这个 monitor；把整段 `doFrame()` 或布局时间算成队列持锁时间，会误判卡顿来源。

旧实现遇到高并发投递时可能出现优先级反转：较低优先级线程在队列维护代码中持锁，主线程等待 monitor。Perfetto 中应沿 `android.monitor_contention` 事件回到 waiter 与 owner 的调用栈，确认 owner 是否位于 `MessageQueue.enqueueMessage()` 附近。仅凭主线程处于 Sleeping 状态无法证明是消息队列锁。

#### Android 17 的启用边界

Android 17 对 target SDK 37 及以上应用启用新的 lock-free `MessageQueue`，这里的 lock-free 指消息入队不再依赖一把全局锁。`android-17.0.0_r1` 把兼容实现和并发实现放在同一个文件：

`frameworks/base/core/java/android/os/CombinedMessageQueue/MessageQueue.java`

该文件中的 compat change ID（兼容性变更编号）为 `USE_NEW_MESSAGEQUEUE = 421623328L`。应用侧选择条件来自 `CompatChanges.isChangeEnabled(USE_NEW_MESSAGEQUEUE)`；平台还保留 feature flag（平台功能开关）和系统进程选择逻辑，因此不能用应用 target SDK 推断所有系统进程的队列模式。

官方把这套设计称为 DeliQueue。下图只表达职责分离：producer 指投递消息的线程，consumer 指取出消息的 Looper 线程；图中的名称不代表 r1 中存在同名 Java 类。

```text
background producer threads
      │  VarHandle CAS
      ▼
Treiber-style StackNode 链
      │  Looper 调用 nextMessage() 时 drain
      ▼
普通消息有序集合 + 异步消息有序集合
      │  when / insertSeq
      ▼
Looper 选择可交付消息
```

后台 producer 通过 CAS（compare-and-set，比较并交换）把消息压入 Treiber stack；它是一种用 CAS 更新栈顶的无锁链栈。Looper 端批量取走节点，再按投递时间和序号选择消息。Looper 线程给自己的队列投递时有直接写入有序集合的快速路径。同步屏障是队列中的特殊标记，可让异步消息越过暂时被拦住的普通消息，因此仍会影响两类消息的选择。

#### 博客模型怎样对应到固定 r1 标签源码

Android Developers Blog 用 “Treiber stack + single-threaded min-heap” 解释算法，并讨论 tombstone（逻辑删除标记）、把退出状态编码进原生层引用计数的方案，以及无分支比较器。这个概念模型有助于理解并发写入和有序读取的分工。

`android-17.0.0_r1` 的 Java 源码组织与早期说明不同：

- `StackNode`、`MessageNode`、`StateNode`、`QuittingNode` 是 `MessageQueue.java` 的嵌套类。
- `VarHandle` 是 Java 提供的底层变量访问句柄，源码用 `sState` 对 `mStateValue` 做原子读写。成功的 CAS 决定本次入队何时生效，这个瞬间就是并发语义中的线性化点；CAS 失败的线程重读状态后重试。
- Looper 线程自身入队时直接调用 `insertIntoPriorityQueue()`；其他线程走并发栈。
- drain 后的普通消息与异步消息分别存入两个 `ConcurrentSkipListSet<Message>`：`mPriorityQueue` 和 `mAsyncPriorityQueue`。该类型是基于 skip list（跳表）的并发有序集合。
- 同一 `when` 下用 `insertSeq` 保持顺序；`sendMessageAtFrontOfQueue()` 使用递减序号维持队首投递语义。
- 移除路径会以原子标记完成逻辑删除，Looper 随后跳过或清理已移除节点。

所以，这里的“MessageStack / MessageHeap”只表示写入栈和有序读取端的职责。r1 没有 `MessageStack.java`、`MessageHeap.java`、`CombinedDeliMessageQueue/` 或 `LegacyMessageQueue/` 这些路径。源码定位应以 `CombinedMessageQueue/MessageQueue.java` 为准。

“lock-free MessageQueue”也不表示整个文件没有任何锁。消息入队的共享关键路径不再依赖 legacy 全局 monitor；IdleHandler、文件描述符监听、drain 完成通知等辅助状态仍可使用 `synchronized` 或 `ReentrantLock`。它保证系统在竞争下能持续推进，不保证每个线程都在固定次数内完成操作。

#### drain 发生在什么位置

Looper 进入并发实现的 `nextMessage()` 后，会把栈状态切到 active，取得旧栈顶并调用 `drainStack(oldTop)`。这里的 drain 指把并发栈中的一批节点转移到有序集合。随后 Looper 从普通、异步两个集合取最早项，结合同步屏障和当前时间决定交付、等待或再次循环。

drain 是批量转移点，也是理解 trace 的边界。producer 的 CAS 完成只代表消息已发布到并发栈；消息按 `when` 进入可交付顺序，需要 Looper 完成 drain。高频 producer 仍可能增加 Looper 的整理工作，所以 lock contention 下降不等于队列积压消失。

#### 兼容性风险与测试方式

公共 `Handler`、`Looper`、`Message` 用法无需迁移。风险集中在私有实现依赖：

- 反射读取 `MessageQueue.mMessages` 或遍历旧链表。
- 自制 idle 检测、测试框架或监控 SDK 假定队头保存在 `mMessages`。
- 通过 JNI 或 hidden API（未公开的平台接口）操作队列内部状态。

为维持二进制兼容，Android 17 仍保留 `mMessages` 字段；并发实现启用时该字段恒为 `null`。字段存在不能说明旧链表仍在工作。

官方给出的测试库基线是 Espresso 3.7.0 及以上、Robolectric 4.17 及以上。Robolectric 测试还要从 `@LooperMode(LEGACY)` 迁到 `@LooperMode(PAUSED)`。

以下命令用于在可调试应用上做同包 A/B。

```bash
adb shell am compat enable USE_NEW_MESSAGEQUEUE com.example.app
adb shell am force-stop com.example.app

adb shell am compat disable USE_NEW_MESSAGEQUEUE com.example.app
adb shell am force-stop com.example.app
```

每次切换后都重新启动进程，并保持机型、构建、场景、trace 配置和热状态一致。compat disable 适合定位，不应作为 target SDK 37 发布方案。

#### 公开性能数据该怎样使用

官方博客公开了三组数据：

| 证据 | 官方结果 | 解释边界 |
|:---|:---|:---|
| `busy queue synthetic benchmark`（繁忙队列合成压测） | 多线程插入最高快 5,000 倍 | 压力测试上限，不代表端到端页面性能 |
| internal beta Perfetto traces | App 主线程 lock contention 时间下降 15% | 只衡量锁等待 |
| 同批测试设备体验指标 | App missed frames 下降 4%；System UI / Launcher 下降 7.7%；启动到首帧 P95 下降 9.1% | 官方未公开完整设备、脚本和原始 trace |

业务验收应同时看三类指标：`android.monitor_contention` 中队列 monitor 等待、消息排队时间、帧或启动端到端指标。若锁等待下降而消息排队时间上升，瓶颈已经转移到 producer 数量、Looper 回调成本或 drain 压力。

分析 `system_server` 的消息流时，官方博客给出了 `mq` track-event category，也就是名为 `mq` 的 trace 采集类别。下面是可嵌入 Perfetto 配置的最小片段。

```textproto
data_sources {
  config {
    name: "track_event"
    track_event_config {
      enabled_categories: "mq"
    }
  }
}
```

该 category 用于观察消息投递与交付流。普通应用是否出现同等细节取决于进程、构建类型和 trace 权限，不能把没有 `mq` slice 当成 DeliQueue 未启用。

### ART 分代 CMC：Android 17 新增的是 CMC 分代路径

ART（Android Runtime）在 Android 10 已有分代 Concurrent Copying（CC，并发复制）回收器。Android 17 的变化是 Concurrent Mark-Compact（CMC，并发标记-压缩）加入分代能力。两件事不能写成“Android 17 才有分代 GC”。

官方对收益的表述是：更频繁、成本更低的年轻代回收可减轻 GC 对应用的干扰，并改善最大 RSS（resident set size，进程驻留内存）。官方没有给出适用于所有应用的暂停时间或内存百分比。列表、图片和解析场景都应在自己的分配速率与对象存活分布下测量。

#### r1 的 young、mid、old 模型

`art/runtime/gc/collector/mark_compact.cc` 把上次 GC 后的新分配视为 young：

1. 对象存活一次 GC 后进入 mid。
2. 下一次 young GC 同时标记 young 与 mid，并通过 card table 处理 old 到年轻区域的引用。card table 是按固定内存片记录跨代引用的表，可避免每次都扫描整个 old 区域。
3. 存活的 mid 对象压缩后晋升 old，存活的 young 对象压缩后进入 mid。
4. full GC 处理全堆，并重置或更新分代边界。

这里不能写成“young GC 完全忽略 old”。old 区域通常不做整区追踪和压缩，但 old-to-young 引用仍要靠 aged/dirty cards 与根处理保证可达性。

`YoungMarkCompact` 也没有单独的 `young_mark_compact.cc`。它的构造与 `RunPhases()` 实现在 `mark_compact.cc`，内部复用主 `MarkCompact` collector，并在本轮设置 `young_gen_`。

#### Generational CMC 的启用门槛

下面的等价表达式用于说明 `android-17.0.0_r1` 的启用关系，变量名与源码一致。

```cpp
use_generational_gc =
    (kUseBakerReadBarrier || gUseUserfaultfd)
    && xgc_option.generational_gc
    && ShouldUseGenerationalGC();

if (gUseUserfaultfd && !flags::use_generational_cmc()) {
    return false;
}
return GetBoolProperty(
    "persist.device_config.runtime_native_boot.use_generational_gc", true);
```

顶层是三项 AND：可兼容的 read barrier（对象引用读取屏障）或 userfaultfd（Linux 用户态缺页处理机制）路径、运行时 GC 选项、`ShouldUseGenerationalGC()`。`use_generational_cmc` 只在 `gUseUserfaultfd` 为真时形成额外门槛。device-config 系统属性的默认值是 `true`，所以 `device_config get` 返回空值不能直接判定功能关闭。

应用不应修改 ART 的 device-config 或假定所有 Android 17 设备使用同一 collector。OEM 配置、ART Mainline（可独立更新的 ART 系统模块）和运行时选项都可能改变选择；Android 17 的 ART 改进还可通过 Google Play 系统更新覆盖 Android 12 及以上版本。

验证时以目标进程的 GC 事件、暂停分布、分配速率和 RSS 为证据。对同一测试负载，对比 young/full collection 次数、GC CPU 时间、mutator stall（应用线程因 GC 停顿的时间）与峰值 RSS，比只查一个属性更可靠。需要展开回收器与暂停分析时，参阅 [4.2 ART Heap、GC 与后台维护调度](../../part1-fundamentals/ch04-memory/02-art-heap-gc-maintenance.md)。

### ProfilingManager：系统事件提供采集时机

Android 17 为 `ProfilingManager` 增加多种系统 trigger，也就是由特定系统事件启动的采集条件。应用仍需注册全局结果监听器并添加 trigger；系统不保证每次事件都有产物，采集还受系统与应用设置的限频约束。

#### API 37 主要 trigger 与产物

| trigger | 触发条件 | API 37 定义的产物或边界 |
|:---|:---|:---|
| `TRIGGER_TYPE_COLD_START` | `ApplicationStartInfo.START_TYPE_COLD` | 新启动的 system trace（系统级 Perfetto 轨迹）+ stack sampling（调用栈采样）；持续到 `reportFullyDrawn()`，未调用时默认 5 秒停止 |
| `TRIGGER_TYPE_OOM` | 未捕获 `OutOfMemoryError` | Java heap dump（堆转储）；自定义 uncaught handler（未捕获异常处理器）必须继续调用默认 handler |
| `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` | 进程因过量 CPU 被杀，exit reason 为 `REASON_EXCESSIVE_RESOURCE_USAGE` | 正在运行的 system trace 快照 |
| `TRIGGER_TYPE_ANOMALY` | 系统识别到资源或性能异常 | 产物随 anomaly 类型变化，`ProfilingResult.getTag()` 提供类型信息 |
| `TRIGGER_TYPE_APP_COMPAT` | 系统识别到未来版本将不支持的行为 | 产物随问题变化，tag 提供兼容问题信息 |

`TRIGGER_TYPE_ANOMALY` 注册在 shared UID 场景时，部分异常可能不给产物；shared UID 指多个 package 共用同一个 Linux 用户 ID。OOM trigger 若被自定义 uncaught handler 截断，也不会完成预期 heap dump。接入阶段必须测试这些失败分支。

下面的示例展示最小注册顺序，重点是先注册全局 listener（监听器），再添加 trigger。

```java
if (Build.VERSION.SDK_INT >= 37) {
    ProfilingManager profiling =
            getSystemService(ProfilingManager.class);

    profiling.registerForAllProfilingResults(
            getMainExecutor(),
            result -> handleProfilingResult(result));

    ProfilingTrigger coldStart =
            new ProfilingTrigger.Builder(
                    ProfilingTrigger.TRIGGER_TYPE_COLD_START)
                    .setRateLimitingPeriodHours(24)
                    .build();

    profiling.addProfilingTriggers(List.of(coldStart));
}
```

`setRateLimitingPeriodHours(24)` 是应用提出的最短间隔，系统仍可延后或不交付。回调中要先检查 `getErrorCode()`，成功后再读取 `getResultFilePath()`、`getTriggerType()` 与 `getTag()`；系统 trigger 的结果只交给全局 listener。

把 trigger 当作线上证据入口，不要把它写成常驻采样器。产物可能包含堆对象、调用栈和业务标识，上传与保留策略要遵守隐私、权限和数据最小化要求。完整使用方式参阅 [15.7 ProfilingManager](../../part3-tools/ch15-other-tools/07-profiling-manager.md)。

### JobScheduler pending reason 统计

API 36 已提供当前 pending reasons（任务暂时无法执行的原因）与有限历史。API 37 新增：

`Map<Integer, Duration> JobScheduler.getPendingJobReasonStats(int jobId)`

返回值把 `PENDING_JOB_REASON_*` 映射到该 job 从调度到结束的生命周期内，因该原因 pending 的累计时长。多个原因可能同时成立，各项 `Duration` 之和常会超过总等待时间。

这些统计不跨重启持久化；job 成功完成或取消时也会清空。传入的 ID 若不是当前 pending job，API 会抛出 `IllegalArgumentException`。诊断顺序可按“当前 reasons → history → stats”推进：

- current reasons 回答此刻卡在哪里。
- history 回答约束在何时变化。
- stats 回答长期占比最高的约束，但不能由各项相加计算 wall time，也就是实际流逝的等待时间。

WorkManager 场景还要建立 `WorkSpec` 与系统 job ID 的映射；`WorkSpec` 是 WorkManager 保存的一条内部任务记录。否则，拿错 job ID 会把调度问题变成数据对齐问题。后台调度机制参阅 [5.3 后台执行、任务调度与 App Hibernation](../../part1-fundamentals/ch05-cpu-power/03-background-jobs-hibernation.md)。

### target SDK 37 适配项

#### `static final` 字段不可修改

Android 17 上运行且 target SDK 37 及以上的应用，不能再修改 `static final` 字段：

- Java reflection 写入会抛出 `IllegalAccessException`。
- JNI `SetStatic<Type>Field()` 写入会导致应用崩溃。

影响面常在测试注入、旧序列化框架、热修复和 native 测试工具。`setAccessible(true)` 不能绕过该限制。将可变测试值放进构造参数、接口、配置对象或专用的测试替换点；常量继续保持常量。发布前同时扫描 Java/Kotlin 反射与 JNI，因为两条失败路径不同。

这项约束允许 ART 更积极地依赖常量语义做优化，但不能据此推导某段业务代码一定获得可测加速。迁移目标是移除未受规范保证的写入行为。

#### 大屏方向、尺寸与 Activity 配置变化

target SDK 37 应用运行在 smallest width（配置中的最小可用宽度）至少 600dp 的大屏上时，平台会忽略固定方向、不可调整大小和宽高比限制，包括相关 manifest 属性与 `setRequestedOrientation()` 值。

以 `android:appCategory` 识别的游戏、较小屏幕以及用户在设备设置中的显式选择属于文档列出的例外。

适配重点是窗口尺寸变化后的正确性与帧稳定性：

- 用 `WindowMetrics`（当前窗口可用范围）和自适应布局决定内容结构，避免用物理屏幕尺寸或启动方向固化布局。
- 保存编辑、滚动、播放等 UI 状态，覆盖旋转、折叠、多窗口和桌面自由窗口。
- 检查相机预览、Surface、地图和 `AndroidView` 等嵌入组件在尺寸连续变化时的重建成本。
- 用 Perfetto 观察配置变化附近的 lifecycle、`performTraversals`（View 系统的一轮测量、布局与绘制遍历）、buffer queue（图形生产者与消费者之间的缓冲队列）和 missed frame。

大屏约束由 target SDK 37 触发，下面的 Activity 重建优化则是另一类 Android 17 平台默认规则。官方运行时配置指南没有为它声明 target SDK 门槛：keyboard、keyboardHidden、navigation、touchscreen、colorMode，以及进出 desk UI mode 时，系统默认不再销毁重建 Activity，而是保留实例并调用 `onConfigurationChanged()`。

`android-17.0.0_r1` 的 `attrs_manifest.xml` 允许 `android:recreateOnConfigChanges` 使用 touchscreen、keyboard、keyboardHidden、navigation、colorMode，以及 Android 8 已有的 mcc、mnc（移动国家码与移动网络码）；同一个标志不能再放入 `android:configChanges`。

该属性没有 `uiMode` 取值，因此进出 desk UI mode（桌面停靠模式）时要由应用更新资源和组件。下面的示例只为确有重建依赖的五类 Android 17 事件恢复旧行为。

```xml
<activity
    android:name=".ReaderActivity"
    android:recreateOnConfigChanges="keyboard|keyboardHidden|navigation|colorMode|touchscreen" />
```

这五类事件发生时，该属性会让 Activity 执行完整的 stop、destroy、recreate 周期。没有重建依赖时，应在 `onConfigurationChanged()` 中更新非 Compose 状态与嵌入组件；Compose 中读取 `LocalConfiguration.current` 的部分会重组，`AndroidView`、`AndroidFragment` 等嵌入对象仍需应用自行刷新。

#### Network Security Configuration、ECH 与 CT

Android 17 计划在未来版本弃用 manifest 级 `usesCleartextTraffic`，当前版本尚未删除该属性。Network Security Configuration 是声明式 XML 配置，可把仍需保留的 HTTP 例外限制到具体域名。若 `minSdkVersion >= 24`，可只使用这份配置；若最低支持版本低于 24，官方建议同时保留 `usesCleartextTraffic="true"` 和网络安全配置文件。

对 target SDK 37 应用，Android 17 为 TLS 连接启用 Encrypted Client Hello（ECH），用于加密 ClientHello 中的 SNI（Server Name Indication，服务器名称指示）。生效还要求应用所用网络库已经接入 ECH，服务端也支持协商；无法协商时客户端发送 ECH GREASE，即带随机内容的占位扩展，以减少中间网络设备对固定握手格式的依赖。

Network Security Configuration 新增 `<domainEncryption>`，可在 `<base-config>` 或 `<domain-config>` 中按全局或域名设置 `enabled`、`disabled` 等模式。

下面的配置为 `example.com` 显式选择 `enabled` 模式。

```xml
<network-security-config>
    <domain-config>
        <domain includeSubdomains="true">example.com</domain>
        <domainEncryption mode="enabled" />
    </domain-config>
</network-security-config>
```

`enabled` 表示客户端拿到 ECH 配置时启用 ECH，拿不到时发送 ECH GREASE；它没有提供 fail-closed 语义，也就是不会因服务端缺少 ECH 支持而直接拒绝连接。平台支持、客户端库接入、携带 ECH 配置的 DNS HTTPS 记录和服务端部署都会影响协商。排障要记录网络库版本、DNS 结果和 TLS handshake，不要给 ECH 写固定时延收益。

target SDK 37 应用还会默认启用 Certificate Transparency（CT，证书透明度）。网络栈按 Network Security Configuration 执行 CT 时，证书链或 SCT（Signed Certificate Timestamp，证书已记入日志的签名凭据）不满足策略会使 TLS 连接失败。

若某个 `domain-config` 使用用户证书库或内嵌证书作为 trust anchor（验证证书链的信任根），CT 默认会关闭；需要时可用 `<certificateTransparency enabled="true"/>` 再显式开启。

CT 校验通常使用证书或握手携带的 SCT，不能概括成“每次连接都会访问 CT log”。升级前应覆盖生产域名、备用域名、CDN 切换、证书轮换以及自定义 trust anchor。

#### 局域网访问权限

target SDK 37 应用在 Android 17 上访问局域网时，需要声明并在运行时申请 `ACCESS_LOCAL_NETWORK`。该权限属于 `NEARBY_DEVICES` 权限组；用户已授予组内其他权限时，系统不会再次弹出授权框。设备发现、投屏、智能家居、调试桥接和本地 HTTP 服务都要覆盖“未授权、拒绝、之后授权”三条路径。

Google Cast Output Switcher 和带 `DiscoveryRequest.FLAG_SHOW_PICKER` 的 `NsdManager` 可由系统完成发现与选择；这里的 picker 是只把用户选中的设备交给应用的系统选择器，对应场景无需直接获得整个局域网访问权。迁移时应按产品能力选择 picker 或运行时权限，不能用连接超时替代权限状态判断。

缺少权限时，TCP 常表现为超时，UDP 通常返回 `EPERM`（operation not permitted）；native 网络栈可用 `android_getnetworkblockedreason()` 区分 Local Network Protection 拦截。性能测试若包含局域网服务，必须记录授权状态，避免把权限拒绝误判为 DNS、TCP 或服务端性能问题。

#### 16KB 页面是延续性发布要求

Android 15 起 AOSP 支持 16KB page-size 设备。这项能力早于 target SDK 37，但 Android 17 迁移仍要检查。Google Play 的现行要求覆盖面向 Android 15（API 35）及以上版本的 64 位设备；自 2027 年 2 月 1 日起，不支持 16KB 页面大小的应用更新将无法发布。

纯 Java/Kotlin 应用通常已兼容。只要 APK/AAB 直接或经 SDK 带有 `.so`，就要同时检查：

- APK/AAB 内未压缩 `.so` 的 ZIP 对齐。
- 每个 ELF `LOAD` segment（装载段）的对齐。
- 所有预编译 SDK 的 native 库版本。
- `mmap()`（内存映射）、共享内存与自制 allocator（内存分配器）是否假定页大小固定为 4096 字节。
- 运行时页大小是否用 `getpagesize()` 或 `sysconf(_SC_PAGESIZE)` 获取。

AGP 8.5.1 及以上配合 NDK r28 及以上，并使用兼容 16KB 的预编译依赖时，官方工具默认处理 16KB ZIP 和 ELF 对齐。NDK r27 及以下可按官方指南为自有库显式加入 `-Wl,-z,max-page-size=16384` 与 `-Wl,-z,common-page-size=16384`；旧版 `libc++_shared.so` 和第三方预编译库仍需逐个核验。

以下命令用于检查 bundle 配置、APK 对齐和 ELF program headers。

```bash
bundletool dump config --bundle app-release.aab
zipalign -c -P 16 -v 4 app-release.apk
llvm-readelf -lW lib/arm64-v8a/libexample.so
adb shell getconf PAGE_SIZE
```

bundle 配置应显示 `PAGE_ALIGNMENT_16K`，`zipalign` 应通过，`readelf` 中每个 `LOAD` segment 的 Align 不得低于 `2**14`，设备命令应返回 `16384`。工具通过后还要在 16KB emulator 或设备上覆盖启动、动态加载、数据库、媒体与 mmap 场景。

Android 17 还能把 16KB backcompat（兼容模式）设为 `fatal`，让不兼容二进制立即终止；这个模式只适合测试，不能代替发布兼容。原理和排查步骤参阅 [4.5 16 KB Page Size 与 Android 性能](../../part1-fundamentals/ch04-memory/05-16kb-page-size.md)。

### 运行在 Android 17 时还要检查的项目

#### App memory limits

Android 17 在部分设备上按总 RAM 对应用施加保守的内存上限，面向所有应用。受影响进程的 `ApplicationExitInfo.getReason()` 为 `REASON_OTHER`，description 包含 `MemoryLimiter:AnonSwap` 及附加信息。`TRIGGER_TYPE_ANOMALY` 可在触发限制时请求 heap dump，但交付仍受 trigger 规则约束。

`adb shell am memory-limiter status` 用于查看当前设备是否启用及可见/不可见进程上限。`ignore` 与 `manual` 子命令适合复现测试，不能写成生产规避方式。该退出原因和 LMKD（low-memory killer daemon，系统低内存杀进程服务）的低内存 kill 应分开统计。

#### 后台音频

所有运行在 Android 17 的应用，后台播放、audio focus 和音量修改需要可见 Activity，或运行非 `SHORT_SERVICE` 类型的 foreground service（FGS，前台服务）。无效状态下，播放与音量 API 会静默失效，audio focus 返回 `AUDIOFOCUS_REQUEST_FAILED`。

target SDK 37 应用在后台还有一层要求：foreground service 需具备 while-in-use（WIU）能力。这里指系统根据应用可见状态、明确用户交互或受信任的系统委托，判定该 FGS 可以继续使用“仅在使用期间”开放的能力。持有 exact alarm 权限且操作 `USAGE_ALARM` stream 时，文档提供了对应豁免。媒体应用应覆盖通知、蓝牙控制、车机、定时闹钟、进程冻结恢复和用户主动续播。

#### 原生动态代码加载

target SDK 37 后，Android 14 对 DEX/JAR 的 Safer Dynamic Code Loading 保护扩展到 native library。经 `System.load()` 加载的 native 文件必须为只读，否则抛出 `UnsatisfiedLinkError`。

优先移除网络下载并执行 native code 的设计。确有动态加载需求时，文件应位于应用私有目录，完成来源与签名或散列校验，并在 `System.load()` 前设置只读。更新时写入独立临时文件，关闭写句柄并校验，设置只读后再原子替换；不要在已加载路径上边写边执行。只读标志满足平台加载检查，签名或散列才用于确认文件来源和内容。

### Choreographer Buffer Stuffing Recovery

这项机制早于 API 37 的迁移边界，但它仍存在于 `android-17.0.0_r1`，分析 Android 17 图形 trace 时容易和 DeliQueue 的效果混淆。buffer stuffing 指图形 buffer 的生产速度持续高于消费速度，导致 buffer queue 被塞满。

`frameworks/base/core/java/android/view/Choreographer.java` 中：

- `onWaitForBufferRelease(durationNanos)` 在等待超过上一帧间隔一半时设置 stuffed 状态。
- `updateBufferStuffingState()` 可能选择 `DELAY_FRAME`，主动等下一次 vsync（垂直同步信号）给 buffer queue 回落机会。
- recovery 进行中可选择 `OFFSET`，把动画时间线向前偏移一个 frame interval，也就是一次垂直同步周期。
- 多次 recovery 与最长累计延迟受 feature flag 控制；r1 常量 `MAX_BUFFER_STUFFING_DELAY_NS` 为 100ms。
- trace 中可出现 `Buffer stuffing recovery`、`buffer stuffed` 和记录负偏移量的事件。

`onWaitForBufferRelease()` 是隐藏接口，应用不能把它当作自定义调度 API。看到 recovery slice（trace 中带持续时间的事件片段）时，应继续查看 `dequeueBuffer` 等待、SurfaceFlinger（系统图形合成服务）、GPU completion、buffer 数量与主线程产出速率。recovery 是缓解 buffer stuffing 的时序策略，也可能主动延迟一帧；它不能证明根因已经消失。

DeliQueue 处理 Java 消息投递争用，Buffer Stuffing Recovery 处理图形 buffer queue 堵塞后的帧时序。两者都可能改善 missed frames，但证据轨道和修复对象不同。

### 迁移检查清单

#### 提升 target SDK 前

- [ ] 搜索 `MessageQueue` 私有字段、hidden API、JNI 与自制 idle 检测。
- [ ] 升级到 Espresso 3.7.0+、Robolectric 4.17+，移除 `@LooperMode(LEGACY)`。
- [ ] 搜索反射和 JNI 对 `static final` 的写入。
- [ ] 盘点 HTTP 域名、ECH/CT 兼容、证书、CDN 切换与自定义 trust anchor。
- [ ] 盘点局域网发现和连接入口，覆盖 `ACCESS_LOCAL_NETWORK` 的授权状态。
- [ ] 检查动态 native library 的来源、写权限与加载流程。
- [ ] 在 sw600dp、折叠、多窗口、桌面窗口和方向变化中验证 UI 状态。
- [ ] 审核所有直接和间接 native 依赖的 16KB 对齐。

#### Android 17 运行验证

- [ ] 用 compat change 对新旧 MessageQueue 做同包 A/B，记录 monitor contention、排队时间和端到端指标。
- [ ] 以进程 GC 事件确认 collector 和 young/full 分布，不用单一 device-config 值替代 trace。
- [ ] 验证 Profiling trigger 的成功、限频、无产物、shared UID 和自定义 OOM handler 分支。
- [ ] 用 JobScheduler current reasons、history、stats 定位长期 pending 约束。
- [ ] 检查 `ApplicationExitInfo` 中的 `MemoryLimiter:AnonSwap`。
- [ ] 覆盖后台音频在可见、FGS、闹钟、冻结恢复和用户续播状态下的结果。
- [ ] 在 16KB 系统上运行包含 mmap、数据库、媒体和动态加载的回归。

#### 性能验收

- [ ] 固定设备、系统 build、应用 build、场景、热状态与 Perfetto 配置。
- [ ] 报告 P50/P95/P99、样本数和波动，不把官方内部百分比当成业务目标。
- [ ] 将 Java 消息争用、GC、Activity 重建、buffer stuffing 和网络握手放到各自证据轨道。
- [ ] 回归正确性、功耗、峰值 RSS 与崩溃，避免只看平均帧时间。

系统与内核边界参阅 [18.3 Android 17 Kernel 6.18 与 ARM64 安全开销](03-android17-kernel-arm64-security.md)，其中内核锚点为 `android17-6.18-2026-06_r6`。这是 18.3 为复现实验固定的快照标签，后续发布序列已有更新；API 行为也不能由 kernel tag 单独推导。


## 常见误区

### “只升级 compileSdk，不改 target，不会影响性能”

compileSdk 只决定编译时可见 API。运行在新系统上的所有 App 变更仍会生效，例如 Android 14 的 cached 进程资源管理和 Android 17 部分设备的内存限制。

### “升 target 后的回归都是平台优化失败”

target 会启用一组兼容性行为。任务不再执行、服务启动异常或测试框架无法判断主线程空闲，可能来自行为边界变化。应按兼容性开关逐项定位。

### “新性能 API 在低版本不能调用，所以没有集成价值”

可以用 API 级别、能力探测和回退实现渐进接入。价值取决于新数据是否改善诊断或控制决策，不取决于覆盖全部历史设备。

### “NN HAL 代码仍在 AOSP，说明 NNAPI 是 Android 17 新加速点”

源码存在表示平台仍维护兼容路径。NNAPI NDK 已在 Android 15 废弃，NN HAL 版本也有独立历史。性能收益必须回到当前 runtime、delegate、驱动和模型测量。

### “Android 17 的分代 GC 等于打开 userfaultfd”

userfaultfd 是 Concurrent Mark-Compact 的一条实现路径，分代是对象代际和回收范围策略。两者处在不同维度。

## 小结

AOSP 性能改动必须从公共路径证据出发，把平台、Mainline、kernel、vendor 与 target SDK 分成独立变量，并用统计确认收益、用 trace 和源码解释原因。Android 12—17 的行为变化既包含面向所有应用的系统规则，也包含 target 触发的兼容变化和设备可选能力；迁移与性能回归只有在这些触发条件被分别记录和验证后，才能归因到正确责任层。


## 参考资料

- [Android app performance overview](https://developer.android.com/topic/performance/overview)
- [Android 17 behavior changes](https://developer.android.com/about/versions/17/behavior-changes-17)
- [Mainline modules](https://source.android.com/docs/core/ota/modular-system)
- [Configure ART](https://source.android.com/docs/core/runtime/configure)
- [Android common kernels](https://source.android.com/docs/core/architecture/kernel/android-common)
- [`android-17.0.0_r1` SystemServer](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/java/com/android/server/SystemServer.java)
- [`android-17.0.0_r1` ProcessState](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/ProcessState.cpp)
- [`android-17.0.0_r1` ART Mark-Compact](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc)
- [`android17-6.18-2026-06_r6` kernel](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)

### Android Developers

- [Android 12：目标版本行为变化](https://developer.android.com/about/versions/12/behavior-changes-12)
- [Android 12：所有 App 行为变化](https://developer.android.com/about/versions/12/behavior-changes-all)
- [Android 13：功能与 API](https://developer.android.com/about/versions/13/features)
- [Android 14：所有 App 行为变化](https://developer.android.com/about/versions/14/behavior-changes-all)
- [Android 14：目标版本行为变化](https://developer.android.com/about/versions/14/behavior-changes-14)
- [Android 14：前台服务类型](https://developer.android.com/about/versions/14/changes/fgs-types-required)
- [Android 15：目标版本行为变化](https://developer.android.com/about/versions/15/behavior-changes-15)
- [Android 16：功能与 API](https://developer.android.com/about/versions/16/features)
- [Android 16：目标版本行为变化](https://developer.android.com/about/versions/16/behavior-changes-16)
- [Android 17 Release Notes](https://developer.android.com/about/versions/17/release-notes)
- [Android 17：目标版本行为变化](https://developer.android.com/about/versions/17/behavior-changes-17)
- [Android 17：所有 App 行为变化](https://developer.android.com/about/versions/17/behavior-changes-all)
- [Android 17 MessageQueue 迁移指南](https://developer.android.com/about/versions/17/changes/messagequeue)
- [ProfilingManager API](https://developer.android.com/reference/android/os/ProfilingManager)
- [ProfilingTrigger API](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [ApplicationStartInfo API](https://developer.android.com/reference/android/app/ApplicationStartInfo)
- [FrameMetrics API](https://developer.android.com/reference/android/view/FrameMetrics)
- [PerformanceHintManager.Session API](https://developer.android.com/reference/android/os/PerformanceHintManager.Session)

#### AOSP 与平台文档

- [`android-17.0.0_r1` ProfilingManager.java](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingManager.java)
- [16 KB page size](https://source.android.com/docs/core/architecture/16kb-page-size/16kb)
- [NNAPI 驱动与废弃状态](https://source.android.com/docs/core/interaction/neural-networks)
- [android17-6.18 release builds](https://source.android.com/docs/core/architecture/kernel/gki-android17-6_18-release-builds)

- [Android 17：target SDK 37 行为变更](https://developer.android.com/about/versions/17/behavior-changes-17)
- [Android 17：影响所有应用的行为变更](https://developer.android.com/about/versions/17/behavior-changes-all)
- [MessageQueue behavior change guidance](https://developer.android.com/about/versions/17/changes/messagequeue)
- [Under the hood: Android 17's lock-free MessageQueue](https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html)
- [Android 17 Features and APIs](https://developer.android.com/about/versions/17/features)
- [ProfilingTrigger API reference](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [JobScheduler API reference](https://developer.android.com/reference/android/app/job/JobScheduler)
- [Handle configuration changes](https://developer.android.com/guide/topics/resources/runtime-changes)
- [Restrictions on orientation and resizability are ignored](https://developer.android.com/about/versions/17/changes/ff-restrictions-ignored)
- [Network Security Configuration](https://developer.android.com/privacy-and-security/security-config)
- [Local network permission](https://developer.android.com/privacy-and-security/local-network-permission)
- [Background audio hardening](https://developer.android.com/about/versions/17/changes/bg-audio)
- [Support 16KB page sizes](https://developer.android.com/guide/practices/page-sizes)
- [AOSP r1：CombinedMessageQueue/MessageQueue.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/CombinedMessageQueue/MessageQueue.java)
- [AOSP r1：attrs_manifest.xml](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/res/values/attrs_manifest.xml)
- [AOSP r1：ART runtime.cc](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/runtime.cc)
- [AOSP r1：ART mark_compact.cc](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc)
- [AOSP r1：ProfilingTrigger.java](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java)
- [AOSP r1：JobScheduler.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java)
- [AOSP r1：Choreographer.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java)
