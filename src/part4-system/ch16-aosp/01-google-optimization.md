---
title: "AOSP 性能优化的分层方法"
section: "16.1"
chapter: "16.1"
status: finalized
drafted_date: "2026-04-10"
drafted_by: "openclaw-task2a"
reviewed_date: "2026-07-13"
reviewed_by: "openclaw-task6"
applicable_versions: "Android 4.1 (API 16) - Android 17 (API 37)"
last_verified: "2026-08-11"
last_verified_against: "AOSP android-17.0.0_r1 + android17-6.18-2026-06_r6 + Android performance and platform documentation"
confidence: high
tags: [android, performance, aosp, methodology]
related_chapters: ["15.2", "15.3", "15.6", "15.7", "16.2", "16.3", "16.4", "16.5"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task9_result: pass-tech-review
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

平台侧性能工作会改变公共执行路径，收益可能覆盖大量应用，回归也可能同时影响兼容性、稳定性、功耗和安全。本节只讨论怎样界定、验证和交付一项 AOSP 性能改动。Android 版本变化见 16.2，Android 17 的应用适配见 16.5，具体的 ART、Binder、图形和内核机制由各专项正文承载。

## 先判断问题是否属于平台

同一个用户现象可能来自不同责任层。只有证据指向公共路径，或应用无法通过公开契约避开问题时，才应优先修改平台。

| 现象 | 更像应用问题的证据 | 更像平台问题的证据 |
| --- | --- | --- |
| 冷启动慢 | 主线程业务初始化、同步 I/O、依赖注入占主导 | 多个应用共同等待 system service、ART 或存储公共路径 |
| 掉帧 | View 遍历、图片解码、每帧分配集中在单个应用 | 同机多应用出现相同合成、调度或驱动等待 |
| Binder 延迟 | 调用次数过多、事务过大、服务端业务锁 | 多个调用方同时遇到线程池、driver 或公共服务拥塞 |
| 内存压力 | 单个进程缓存、泄漏或对象峰值异常 | reclaim、LMKD、freezer 或产品参数使整机工作集反复失效 |
| 后台任务延迟 | 约束、配额或生命周期使用错误 | 平台 controller、时钟或状态传播出现回归 |

判断不能只靠一次 trace。先找同版本、同设备上的对照应用，再比较跨版本、跨设备和兼容性开关；只有问题能随着平台变量稳定移动，才有足够依据进入 framework、ART、native service 或 kernel。

## 用五层模型定位改动面

平台性能路径可以按五层阅读。层级不是组织架构，而是帮助确认成本和契约落在哪里。

1. **应用与公开 API**：调用频率、参数规模、target SDK 和公开行为合同。
2. **Framework 与 system service**：Java/Kotlin 状态机、Binder 服务、锁和生命周期。
3. **Native service 与运行时**：ART、SurfaceFlinger、media、netd、libbinder 等进程或库。
4. **Kernel 与驱动**：调度、内存、Binder driver、文件系统、block I/O 和设备驱动。
5. **硬件与产品策略**：SoC、固件、Power/Thermal HAL、显示和厂商配置。

一次等待可能跨越多层。例如同步 Binder 的调用方处于 Sleeping，只说明它在等回复；真正成本可能是目标线程 runnable delay、服务端锁、TEE、块设备或驱动。分析时应保留调用方、目标进程、内核等待和硬件状态，而不是把最先看到的层当作根因。

## 三类证据共同约束结论

### 公开合同

release notes、behavior changes、SDK 文档和 source.android.com 说明外部可以依赖什么。公开合同决定兼容性和迁移边界，却通常不会给出目标设备的实际启用状态。

### 固定版本源码

源码用于回答实现、gate、默认值和失败路径。平台结论固定到 `android-17.0.0_r1`，内核结论固定到 `android17-6.18-2026-06_r6`。读取 main 分支或另一条 GKI 分支时，只能作为演进线索，不能反推固定 tag。

### 设备运行证据

最终产品还会受到 aconfig、DeviceConfig、Mainline 模块、vendor 配置、kernel config、boot 参数和硬件能力影响。设备结论至少需要 build fingerprint、target SDK、ART/APEX 版本、kernel release 和相关功能状态；trace、dump 或实验结果再说明该次 workload 实际走到哪条路径。

源码中“存在”某个函数、配置项默认 `y`、或系统版本号满足要求，都不能单独证明设备已经启用功能。

## 把版本与交付路径拆开

Android 大版本不是唯一版本轴。同一项优化通过哪条路径交付，决定它能覆盖哪些设备以及如何回滚。

| 交付对象 | 常见载体 | 需要额外记录 |
| --- | --- | --- |
| Framework / system image | 整机 OTA | build ID、产品 overlay、target SDK 行为 |
| Mainline 模块 | APEX/APK 系统更新 | 模块版本、激活状态、回滚记录 |
| GKI / vendor kernel | boot/vendor_boot 或 OTA | 精确 tag、最终 `.config`、vendor module 与启动参数 |
| Vendor service / HAL | vendor 分区或厂商 OTA | 接口版本、SoC/固件、产品配置 |
| 应用编译输入 | APK/AAB、DM、Profile | 安装来源、compiler filter、产物位置 |

因此，Android 17 设备不必然运行唯一的 kernel 或 ART build；target SDK 37 也只会开启文档明确绑定 target 的行为。跨版本实验要把 OS、target、Mainline、kernel 和产品配置分成独立变量。

## 一轮平台优化怎样闭环

### 1. 定义用户动作和完成边界

用可重复动作描述问题，例如“点击图标到首个可交互页面”“触摸事件到对应帧 present”“提交安装会话到包可启动”。起点和终点进入指标名，避免用 CPU 利用率、函数耗时或某条 slice 代替体验指标。

### 2. 保存可复现实验环境

至少记录源码 revision、local diff、产品 target、build variant、设备与内核、页大小、刷新率、编译状态、温度、电源条件、测试脚本和数据集。`userdebug`、root、关闭 verity、额外日志和 trace 配置都可能改变结果，必须显式标注。

### 3. 用统计确认问题，用 trace 解释问题

多轮样本先确认 P50、P90/P95 和离散程度，再用 Perfetto、simpleperf、dumpsys 或模块专用统计解释慢样本。单次 trace 可以支持机制归因，不能单独证明总体收益。

### 4. 一次只改变一个主要变量

平台、kernel、vendor、配置和应用同时变化时，结果无法归因。能用 compat change、feature flag、build flag 或小补丁做同设备 A/B 时，优先使用配对实验；不能隔离时，报告应降低结论强度。

### 5. 同时检查副作用

平台改动除目标指标外，还要检查：

- 稳定性：crash、ANR、watchdog、kernel panic；
- 资源：CPU、内存、I/O、功耗和热状态；
- 正确性：时序、状态机、数据一致性和错误回退；
- 兼容性：旧 target、旧模块、vendor 实现和测试工具；
- 安全：权限、SELinux、签名、隔离和缓解机制没有被削弱。

### 6. 把回滚路径作为实现的一部分

可配置优化要定义默认值、灰度单位、状态可观测性和回滚后的清理动作。涉及持久产物、profile、缓存或文件格式时，还要验证新旧版本交替后不会误用旧状态。

## 常见的平台优化模式

### 删除不必要的工作

优先消除重复扫描、重复序列化、无用唤醒、过早初始化和失效产物。删除工作通常比把同一工作换线程更容易得到稳定收益，但仍要证明被删除的步骤不承担正确性或安全职责。

### 把工作移出关键路径

预加载、异步初始化、后台 dexopt 和延迟服务启动都在改变成本的支付时间。验收必须同时观察原关键路径和新的支付点，避免启动时间变短、首个交互或后台功耗变差。

### 增加并发但保留依赖

并行 driver probe、SystemServer 初始化或批量处理可以缩短串行阶段；依赖表达错误时，成本会变成锁等待、I/O 竞争、defer storm 或偶发状态错误。并发方案应有明确的 ready 条件、超时、降级和取消语义。

### 用反馈信号代替固定策略

ADPF、thermal、PSI、headroom 和 profile-guided optimization 都使用运行信号调整决策。信号会延迟、缺失或受产品实现影响，控制器必须有静态回退、滞回和频率限制，不能按一次读数剧烈切换。

## 设备样本按瓶颈维度选择

“高端、中端、低端”不能稳定描述性能。样本应覆盖具体瓶颈：

| 维度 | 记录项 | 容易暴露的问题 |
| --- | --- | --- |
| CPU | 拓扑、频率、调度、thermal | runnable delay、锁竞争、编译 |
| 内存 | RAM、zRAM/swap、压力策略 | reclaim、GC、LMK、后台重启 |
| 存储 | 文件系统、介质、cache 状态 | major fault、数据库和资源加载 |
| 图形 | GPU、驱动、分辨率、刷新率 | RenderThread、fence、合成 deadline |
| 系统 | build、模块、kernel、target | feature gate、兼容行为和厂商差异 |

Android Go 可以代表一类低资源配置，不能代表全部长尾；高刷新率或高分辨率设备也可能更容易暴露图形预算问题。

## 审查清单

- [ ] 问题能跨应用或随平台变量稳定复现。
- [ ] 公开合同、固定 tag 源码和设备运行证据没有互相替代。
- [ ] 平台、target、Mainline、kernel 和 vendor 版本分别记录。
- [ ] 指标包含用户动作、起止边界、样本数和分位数。
- [ ] trace 解释等待对象，统计证明总体变化。
- [ ] 实验只改变一个主要变量，或明确说明无法隔离的混杂项。
- [ ] 稳定性、资源、正确性、兼容性与安全回归已覆盖。
- [ ] feature 状态可观察，灰度和回滚不会遗留不兼容产物。

## 延伸阅读

- 16.2：Android 12～17 的版本与 target SDK 变化。
- 16.3：固定源码、编译模块、Cuttlefish/真机验证和实验记录。
- 16.4：Android 17 GKI 6.18 的调度、存储、AutoFDO 与 MGLRU。
- 16.5：Android 17 / API 37 行为与应用适配。
- 15.2、15.3、15.6、15.7：归因、指标、测试和源码阅读的通用方法。

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
