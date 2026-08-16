---
title: "AOSP 性能优化的分层方法"
section: "16.1"
chapter: "16.1"
status: finalized
applicable_versions: "Android 4.1 (API 16) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "AOSP android-17.0.0_r1 + android17-6.18-2026-06_r6 + current Android 17 behavior-change, Mainline, GKI and ART documentation"
confidence: high
tags: [android, performance, aosp, methodology]
related_chapters: ["15.2", "15.3", "15.6", "15.7", "16.2", "16.3", "16.4", "16.5"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
consolidated_from:
  - "16.1 Google 官方的性能优化思路中的平台方法、工具选择与设备验证边界"
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/overview"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17"
  - type: official
    path: "https://source.android.com/docs/core/ota/modular-system"
  - type: official
    path: "https://source.android.com/docs/core/architecture/kernel/android-common"
  - type: official
    path: "https://source.android.com/docs/core/runtime/configure"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/java/com/android/server/SystemServer.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/ProcessState.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/"
---

# AOSP 性能优化的分层方法

AOSP（Android Open Source Project，Android 开源平台）的性能改动会改变多个 App 共用的执行路径，收益可能覆盖整台设备，回归也可能让原本正常的兼容性、稳定性、功耗或安全行为退步。本节只讨论怎样界定、验证和交付一项 AOSP 性能改动。Android 版本变化见 16.2，Android 17 的应用适配见 16.5；ART（Android Runtime，Android 运行时）、Binder（Android 的进程间通信机制）、图形和内核的具体机制由各专项正文承载。

## 先判断问题是否属于平台

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

## 用五层模型定位改动面

平台性能路径可以按五层阅读。这五层用于确认成本和对外行为边界落在哪里，不对应团队组织架构。

1. **应用与公开 API**：调用频率、参数规模、target SDK（App 声明适配到的 API 级别）和公开行为约定。
2. **Framework 与 system service**：Java/Kotlin 状态机、Binder 服务、锁和生命周期。
3. **Native service 与运行时**：ART、SurfaceFlinger（显示合成服务）、media、netd（网络管理服务）、libbinder 等原生进程或库。
4. **Kernel 与驱动**：调度、内存、Binder driver（Binder 的内核驱动）、文件系统、block I/O（面向存储块设备的读写）和设备驱动。
5. **硬件与产品策略**：SoC（System on Chip，片上系统）、固件、Power/Thermal HAL（电源与温控的硬件抽象层）、显示和厂商配置。

一次等待可能跨越多层。例如同步 Binder 的调用方处于 `Sleeping`，只说明它正在等回复；真正的耗时可能来自目标线程的 runnable delay（线程已可运行、却仍在调度队列等待的时间）、服务端锁、TEE（Trusted Execution Environment，可信执行环境）、块设备或驱动。分析时应同时保留调用方、目标进程、内核等待和硬件状态，再判断哪一层造成了等待，不能根据最先看到的层直接下结论。

## 三类证据共同约束结论

### 公开接口与行为约定

release notes（版本说明）、behavior changes（行为变更文档）、SDK 文档和 source.android.com 说明外部可以依赖什么。这些公开约定决定兼容性和迁移边界，却通常不会给出目标设备的实际启用状态。

### 固定版本源码

源码用于回答实现、gate（决定代码路径是否启用的条件或开关）、默认值和失败路径。平台结论固定到 `android-17.0.0_r1`，内核结论固定到 `android17-6.18-2026-06_r6`。tag 是可复查的固定源码版本；main 是持续变化的开发分支。GKI（Generic Kernel Image，通用内核镜像）还有多条受支持分支，读取其他分支只能说明机制如何演进，不能反推这里固定的 tag。

### 设备运行证据

最终产品还会受到 aconfig、DeviceConfig、Mainline 模块、vendor（设备或芯片厂商）配置、kernel config、boot 参数和硬件能力影响。aconfig 与 DeviceConfig 都可承载平台功能开关，但生效阶段和更新方式不同；Mainline 则把部分系统组件做成可独立更新的模块。设备结论至少需要 build fingerprint（唯一标识系统构建的一组属性）、target SDK、ART/APEX（系统模块容器）版本、kernel release 和相关功能状态；trace、dump（状态或内存转储）与实验结果再说明本次 workload（受测操作）实际走到哪条路径。

源码中存在某个函数、内核配置项默认 `y`，或系统版本号满足要求，都不能单独证明目标设备已经启用该功能。产品配置、模块版本或运行时开关还可能改变最终状态。

## 把版本与交付路径拆开

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

## 一轮平台优化怎样完成验证与交付

### 1. 定义用户动作和完成边界

用可重复动作描述问题，例如“点击图标到首个可交互页面”“触摸事件到对应帧 present（提交到屏幕显示）”“提交安装会话到包可启动”。起点和终点应写进指标定义，不能用 CPU 利用率、函数耗时或某条 trace slice（轨迹中的一个时间区间）代替用户体验指标。

### 2. 保存可复现实验环境

至少记录源码 revision（commit 或 tag）、local diff（尚未进入该版本的本地改动）、产品 target（AOSP 编译所选的设备产品目标）、build variant（`user`、`userdebug` 或 `eng` 构建类型）、设备与内核、页大小、刷新率、编译状态、温度、电源条件、测试脚本和数据集。`userdebug` 会保留更多调试能力，root 会取得超级用户权限，关闭 verity 会停用系统分区完整性校验；这些操作以及额外日志、trace 配置都可能改变结果，必须显式标注。

### 3. 用统计确认问题，用 trace 解释问题

多轮样本先确认 P50、P90/P95 和离散程度；P50、P90、P95 分别表示 50%、90%、95% 的样本不高于该数值。再用 Perfetto（系统级 trace 工具）、simpleperf（CPU 性能分析工具）、`dumpsys`（导出系统服务状态的命令）或模块专用统计解释慢样本。单次 trace 可以帮助判断慢样本由哪条路径造成，不能单独证明总体收益。

### 4. 一次只改变一个主要变量

平台、kernel、vendor、配置和 App 同时变化时，无法判断结果由哪项变化造成。能用 compat change、feature flag（运行时功能开关）、build flag（构建时开关）或小补丁在同一设备做 A/B 对照时，优先使用改动前后成对比较的实验；无法隔离变量时，报告应降低结论强度。

### 5. 同时检查副作用

平台改动除目标指标外，还要检查：

- 稳定性：crash、ANR（Application Not Responding，应用无响应）、watchdog（系统看门狗判定关键线程或服务长时间无响应）、kernel panic（内核遇到无法继续运行的致命错误）；
- 资源：CPU、内存、I/O、功耗和热状态；
- 正确性：时序、状态机、数据一致性和错误回退；
- 兼容性：旧 target、旧模块、vendor 实现和测试工具；
- 安全：权限、SELinux（Android 的强制访问控制机制）、签名、隔离和缓解机制没有被削弱。

### 6. 把回滚路径作为实现的一部分

可配置优化要定义默认值、分批发布的设备分组、状态观测方式和回滚后的清理动作。涉及持久产物、profile、缓存或文件格式时，还要验证新旧版本交替后不会误用旧状态。

## 常见的平台优化模式

### 删除不必要的工作

优先消除重复扫描、重复序列化、无用唤醒、过早初始化和失效产物。删除工作通常比把同一工作换线程更容易得到稳定收益，但仍要证明被删除的步骤不承担正确性或安全职责。

### 把工作移出关键路径

预加载、异步初始化、后台 dexopt（对 DEX 字节码做验证或编译优化）和延迟服务启动，都会把 CPU、I/O 或内存成本移到另一个时间点。验收必须同时观察原关键路径和成本转移后的阶段，避免启动时间变短，首个交互或后台功耗却变差。

### 增加并发但保留依赖

并行 driver probe（驱动探测并初始化硬件）、SystemServer 系统服务初始化或批量处理可以缩短串行阶段。依赖表达错误时，成本会变成锁等待、I/O 竞争、defer storm（依赖未就绪导致大量驱动反复推迟探测）或偶发状态错误。并发方案应有明确的 ready 条件（依赖何时算就绪）、超时、降级和取消语义。

### 用反馈信号代替固定策略

ADPF（Android Dynamic Performance Framework，应用与系统协同提示性能需求）、thermal（温度与热节流状态）、PSI（Pressure Stall Information，CPU、内存或 I/O 压力造成停顿的统计）、headroom（距离温度或资源上限的余量）和 profile-guided optimization（根据真实执行热点指导编译优化）都利用运行信号调整决策。信号可能延迟、缺失，也会受产品实现影响；控制逻辑必须有静态回退、滞回和频率限制。滞回表示进入和退出某状态使用不同阈值，可避免读数在边界附近反复切换。

## 设备样本按瓶颈维度选择

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

## 审查清单

- [ ] 问题能跨应用或随平台变量稳定复现。
- [ ] 公开接口与行为约定、固定 tag 源码和设备运行证据没有互相替代。
- [ ] 平台、target、Mainline、kernel 和 vendor 版本分别记录。
- [ ] 指标包含用户动作、起止边界、样本数和分位数。
- [ ] trace 解释等待对象，统计证明总体变化。
- [ ] 实验只改变一个主要变量，或明确说明无法隔离的混杂项。
- [ ] 稳定性、资源、正确性、兼容性与安全回归已覆盖。
- [ ] feature 状态可观察，分批发布和回滚不会遗留不兼容产物。

## 延伸阅读

- 16.2：Android 12～17 的版本与 target SDK 变化。
- 16.3：固定源码、编译模块、Cuttlefish（AOSP 虚拟设备）/真机验证和实验记录。
- 16.4：Android 17 GKI 6.18 的调度、存储、AutoFDO（利用采样 profile 指导编译优化）与 MGLRU（Multi-Gen LRU，多代内存页回收算法）。
- 16.5：Android 17 / API 37 行为与应用适配。
- 15.2、15.3、15.6、15.7：因果分析、指标、测试和源码阅读的通用方法。

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
