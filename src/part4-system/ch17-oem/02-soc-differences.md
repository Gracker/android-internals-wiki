---

task2b_rework_date: "2026-05-25T11:23:10+08:00"
title: "SoC 平台差异"
chapter: "17.2"
section: "17.2"
drafted_date: "2026-04-04"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-06-15"
last_verified_against: "Qualcomm / MediaTek / Samsung / Google 官方产品页，Google Tensor G5 官方博文，ARM Cortex-X925 官方资料，AOSP android-17.0.0_r1，Android common android14-6.1 / android15-6.6 / android16-6.12 / android17-6.18"
confidence: medium
sources:
  - type: blog
    path: "obsidian/Cubox/高通Oryon处理器微架构分析-2025-03-25.md"
  - type: blog
    path: "obsidian/Cubox/高通Perflock - yooooooo - 博客园-2024-11-18.md"
  - type: blog
    path: "obsidian/Cubox/2023年Arm最新处理器架构分析--X4、A720和A520-2023-08-02.md"
  - type: official
    path: "qualcomm.com/products/mobile/snapdragon"
  - type: official
    path: "mediatek.com/products/smartphones"
  - type: official
    path: "arm.com/products/silicon-ip-cpu"
  - type: official
    path: "blog.google/products-and-platforms/devices/pixel/tensor-g5-pixel-10/"
  - type: official
    path: "support.google.com/pixelphone/answer/7158570"
  - type: official
    path: "developer.arm.com/documentation/102807/0002"
  - type: web
    path: "多来源综合(web search 验证)"
tags: [qualcomm, mediatek, samsung, exynos, tensor, adreno, mali, xclipse, soc, cpu, gpu]
related_chapters: ["5.1", "5.3", "5.4", "2.10", "17.1"]
task2b_result: "fixed"
last_task2b_at: "2026-05-17T19:17:39"
task9_result: "auto-fixed"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-15"
last_task9_at: "2026-06-15T21:20:00+08:00"
last_task9_review_log: "logs/deep-review/2026-06-15-21-deep-review.md"
task9_review_notes: "2026-05-25 11 Task9 deep-review: needs-rework。P0 2 / P1 0 / P2 0；8 Elite Gen 5 Vulkan、Dimensity 9500 core/GPU、Snapdragon LPDDR5X 带宽规格与官方资料不一致。 | 2026-05-27 06:23 Task9 auto-fix：按 Qualcomm / MediaTek 官方产品规格修正 8 Elite Gen 5 图形 API、Dimensity 9500 八核 CPU / Mali-G1 Ultra MC12、Snapdragon 8 Elite LPDDR5x 口径；无 queue pending。 | 2026-05-27 07:24 Task9 auto-fix：Android common 6.12 不存在 kernel/sched/energy.c；EAS 选核源码锚点改为 kernel/sched/fair.c 的 find_energy_efficient_cpu()/compute_energy()，回到 Task6 复审。 | 2026-05-27 08:22 Task9 auto-fix：按 Android common 6.1/6.6/6.12 复核 EEVDF 版本口径，避免把调度器切换绑定到 Android API；回到 Task6 复审。 | 2026-05-27 09:40 Task9 deep-review：pass-tech-review。复核 08:22 EEVDF 版本口径 auto-fix 后，Task6 09:16 仅改术语括号，未引入技术变化；queue 无 pending，自动晋升 finalized。 | 2026-06-15 19:25 Task9 idle-audit auto-fix：补充 Android 17 支持的 android17-6.18 kernel 分支口径；复核 fair.c find_energy_efficient_cpu()/compute_energy()/EEVDF 与 sched_ext ext.c 锚点；回到 Task6 复审。 | 2026-06-15 20:30 Task9 auto-fix：修正 Cortex-X925 L2/ROB 旧口径、Tensor G5 发布与 Pixel 10 RAM 机型差异、Geekbench 工具名；补充 Google/ARM 官方来源；回到 Task6 复审。 | 2026-06-15 21:20 Task9 auto-fix：清理正文误嵌 Task6 复审记录；修正 Exynos 2500/2600 时间与拓扑口径、schedutil cpufreq_update_util 触发口径与 DSU 表述；回到 Task6 复审。"
p0: 0
p1: 0
p2: 0
pipeline_stage: "ready-to-publish"
reviewed_by: openclaw-task6
reviewed_date: "2026-06-15"
task6_result: pass-light-edit
task6_state: reviewed
task6_reviewed_date: "2026-06-15"
task6_reviewed_by: openclaw-task6
last_task6_at: "2026-06-15T22:30:00+08:00"
last_task6_audit: "2026-06-15"
last_task6_review_log: "logs/review/2026-06-15-22-review.md"
review_type: task6-writing-quality-review
task9_state: "reviewed"
last_task9_audit: "2026-06-15"
last_task9_audit_log: "logs/deep-review/2026-06-15-19-audit.md"
task6_review_notes: "2026-05-25 Task6 复审:未发现新增 L1/L2 文风问题;常见问题后的联发科调度源码素材块仍未并入正文,已继续并入 queue.json priority 95。保留 Task9 2025/2026 SoC 规格 P0 pending。 | 2026-05-27 07:11 Task6：pass-light-edit。将文末联发科调度源码锚点移入 CPU 调度策略小节；L1 禁用词扫描无新增命中；无 L3/L4 回炉项。Task9 为 auto-fixed，未满足自动晋升 finalized 的 pass-tech-review 条件，送 Task9 复审。 | 2026-05-27 08:07 Task6：pass-light-edit。L1/L2 文风复扫无新增命中；outline 5/5 覆盖；无 L3/L4 回炉项。Task9 result 为 auto-fixed，未满足自动晋升 finalized 的 pass-tech-review 条件，送 Task9 复审。 | 2026-05-27 09:16 Task6：pass-light-edit。修正术语括号格式；L1 禁用词与高频词扫描无命中；outline 5/5 覆盖；无 L3/L4 回炉项。Task9 result 为 auto-fixed，未满足自动晋升 finalized 条件，送 Task9 复审。 | 2026-06-15 20:16 Task6 复审:pass-light-edit。Task9 idle-audit 补充 android17-6.18 kernel 分支口径后文风复扫;L1 禁用词/高频词/翻译腔动词均无命中;outline 5/5 + 扩展 2/2 覆盖;待验证 26.7% < 30%;无 L1/L2 新增问题;无 L3/L4 回炉项。Task9 result 为 auto-fixed,未满足自动晋升 finalized 条件,送 Task9 复审。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-16
last_deepseek_polish_at: 2026-06-16
---
# SoC 平台差异

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 主流 SoC 平台对比:高通 Snapdragon、联发科 Dimensity、三星 Exynos、Google Tensor
- 🔹 各平台的 CPU 核心架构差异与性能调度策略
- 🔹 GPU 差异(Adreno / Mali / Xclipse / Immortalis)对渲染性能的影响
- 🔹 ISP / NPU / DSP 的性能相关差异
- 🔹 内存控制器与带宽差异(LPDDR5/5x)

### 扩展(可选深入)

- 🔸 SoC 厂商提供的性能分析工具(Snapdragon Profiler、ARM Streamline)
- 🔸 不同 SoC 上 Perfetto 数据的差异

### OpenClaw 加工指引

> **锚点**是最低覆盖要求,加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点,
> 可**就地插入**最相关的锚点之后,并用 `[自动发现]` 标注,方便后续 review。
> 锚点内容需 L1/L2 验证,扩展内容至少 L2 验证,自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 SoC 平台差异

做 Android 性能优化时,经常会遇到这种情况:同一款 App 在骁龙设备上流畅运行,到了联发科 Dimensity 或 Exynos 设备上却莫名其妙掉帧。打开 Perfetto 一看,同样的代码路径,CPU 调度行为不一样了,GPU 渲染耗时也不一样了,甚至内存带宽的瓶颈出现在不同的位置。

问题往往出在不同 SoC 平台的硬件架构差异上:CPU 核心的拓扑结构不同、GPU 的渲染管线不同、内存控制器的带宽和延迟不同,厂商的调度策略也不同。这些差异会直接影响 Perfetto 里的现象,如果不了解它们,就很容易把平台特性误判为代码问题。

了解 SoC 平台差异之后,**Perfetto 里出现异常的 CPU 调度、GPU 耗时或内存行为时,分析者能判断这是代码问题还是平台特性导致的现象。** 这种判断能力在做跨设备性能优化和线上问题定位时尤其重要:团队不可能在每个平台上都做一遍完整分析,但需要知道不同平台上同一个现象的含义可能完全不同。

这里不按产品评测方式逐项对比芯片参数,只保留会直接影响性能分析结论的架构差异,以及它们在 Perfetto 中分别长什么样。

[已验证: 多来源综合,包括 Qualcomm 官方产品页、MediaTek 官方产品页、ARM 官方架构文档]

## 主流 SoC 平台概览

Android 生态中的旗舰 SoC 主要来自四家公司,每家的设计哲学和技术路线都有明显差异。四个平台的差异先体现在定位上,之后再进入 CPU、GPU、专用处理器和内存带宽这些会影响分析结论的维度。

**高通 Snapdragon** 是 Android 生态中使用最广泛的旗舰 SoC 系列。从 Snapdragon 8 Gen 3 到 8 Elite,高通一直保持着综合性能的领先地位,尤其在 GPU 渲染和游戏性能方面。高通的独特之处在于它几乎实现了全自研:CPU 方面,从 8 Elite 开始采用收购 Nuvia 后自研的 Oryon 核心(开发团队背景来自 Nuvia,创始成员有 Apple CPU 团队经历),不再使用 ARM 公版 Cortex 核心;GPU 方面的 Adreno 系列一直是自研的;基带更是高通的传统优势。这种全自研策略让高通可以更深入地优化各组件之间的协同。

**联发科 Dimensity** 近几年在旗舰市场的进步非常显著。Dimensity 9300 和 9400 采用了激进的「全大核」策略:取消传统的小核心,全部使用 Cortex-X 系列和 A720 等性能核心。这种设计在多核性能上有明显优势,但也对功耗管理和散热提出了更高要求。联发科使用 ARM 公版 CPU 核心,GPU 则随代际在 Immortalis 与 Mali 旗舰系列之间变化:Dimensity 9400 是 Immortalis-G925,Dimensity 9500 官方规格是 Arm Mali-G1 Ultra MC12。联发科的芯片通常在性价比方面有优势,在中端市场的份额尤其高。

**三星 Exynos** 的情况比较特殊。Exynos 曾经是三星 Galaxy 系列的主力芯片,但在旗舰性能上与高通的差距导致三星多次在旗舰机型上转向骁龙。2025 年的 Galaxy Z Flip7 已使用 Exynos 2500;到 2026 年,三星官方新一代移动 SoC 是 Exynos 2600。Exynos 的 CPU 使用 Arm 公版核心,GPU 方面采用了与 AMD 合作的 Xclipse 系列,基于 AMD RDNA 架构,这在移动 GPU 中是独树一帜的选择,带来了硬件光追和 VRS 等桌面级特性。

**Google Tensor** 是 Google 为 Pixel 系列定制的 SoC。Tensor 的设计哲学与其他三家完全不同:它不以峰值性能为目标,而是围绕 Google 的 AI 和机器学习需求来设计。Tensor 的 CPU 和 GPU 性能在旗舰 SoC 中并不突出,但在端侧 AI 推理(如语音识别、图像处理、实时翻译)方面有专用硬件加速。Tensor G4 仍基于三星的代工和部分 IP,但 Tensor G5 已随 Pixel 10 系列发布。Google 官方称 Tensor G5 是第五代自研 Tensor,采用 TSMC 3nm 工艺;Pixel 10 系列继续围绕端侧 AI、相机 ISP 和安全硬件做定制。

> 截至 2026-06-15，四大平台均已迭代到新一代旗舰，以下为当前各平台最新型号的关键规格：
>
> - **Qualcomm Snapdragon 8 Elite Gen 5**：第三代自研 Oryon CPU 核心，Adreno GPU 升级；Qualcomm 产品规格列出的 Android 图形 API 为 OpenCL 3.0 FP / OpenGL ES 3.2 / Vulkan 1.3，Linux UMD 资料里的 Vulkan 1.4 不能直接写成 Android 设备统一能力
> - **MediaTek Dimensity 9500**：采用 ARM C1-Ultra + C1-Premium + C1-Pro 八核架构（1×C1-Ultra + 3×C1-Premium + 4×C1-Pro），GPU 为 Arm Mali-G1 Ultra MC12；官方规格未列出额外 2 个低功耗核
> - **Samsung Exynos 2600**：2nm GAA 工艺，十核 CPU（ARM C1 系列），Xclipse 960 GPU（基于 AMD RDNA）
> - **Google Tensor G5**：Pixel 10 系列搭载，采用 TSMC 3nm 工艺；Google 官方硬件规格中 Pixel 10 为 12GB RAM，Pixel 10 Pro / Pro XL / Pro Fold 为 16GB RAM
>
> 2024/2025 代表芯片（8 Elite、9400、Exynos 2500、Tensor G4）仍作为当前在售设备的主力参考，但分析新设备 Perfetto 数据时需要按新一代架构更新基准判断。

[图:四大 SoC 平台的关键参数对比表格(CPU 架构/GPU/NPU/制程/典型机型)]

[已验证: 公开产品规格,来源见 Qualcomm/MediaTek/Samsung/Google 官方产品页]

四种设计哲学的分歧，在 CPU 核心架构上体现得最直接：从核心选型、拓扑排列到调度策略，每一家的选择都不一样。下面从这三个维度逐一对比。

## CPU 核心架构差异与性能调度策略

CPU 是性能分析时最关注的组件。不同 SoC 在 CPU 核心的拓扑结构、微架构和调度策略上差异很大,这些差异直接影响 Perfetto 中 CPU Track 的表现。

### 核心拓扑:从传统大小核到全大核

§5.3 讲过 ARM big.LITTLE 和 DynamIQ 的大小核架构,这是 Android SoC 的经典设计:几个高性能核心负责重负载,几个低功耗核心处理后台任务。但最近两代芯片中,各家开始出现明显分化。

高通在 Snapdragon 8 Gen 3 上采用了 1+3+2+2 的四集群设计(1 个 Cortex-X4 超大核 + 3 个 Cortex-A720 大核 + 2 个 A720 中核 + 2 个 A520 小核),到了 8 Elite(搭载自研 Oryon 核心)则简化为 2+6 的双集群设计。这种简化策略背后的思路是:减少集群间迁移的机会,降低调度器做迁移决策时的开销。在 Perfetto 中分析 Oryon 设备时,应重点看线程是否在两个集群之间来回迁移,而不是直接套用四集群大小核的判断。

联发科的策略最为激进。Dimensity 9300 和 9400 采用了「全大核」设计:Dimensity 9400 配置为 1×Cortex-X925 + 3×Cortex-X4 + 4×Cortex-A720 的全大核架构。MediaTek 官方公开 Cortex-X925 up to 3.62GHz 与 LPDDR5X 内存规格;X4/A720 的细分频率、vendor OPP 表和实机频率策略仍需以设备/内核来源核验。评测拆解和 Geekbench/AnTuTu 等工具读数可作交叉参考,但不同渠道的数字存在差异。这种设计带来的直接影响是:在 Perfetto 的 CPU Track 中,所有核心都有较高的基础性能,即使任务被调度到所谓「能效核」上,也不会出现性能断崖式下降的情况。

三星 Exynos 2500 保持相对传统的大小核配置,使用 ARM 公版核心搭配标准的 DynamIQ 集群。Exynos 2600 的官方 CPU 口径已转为 10 核 Arm C1 结构:1 个 C1-Ultra + 3 个高性能 C1-Pro + 6 个高能效 C1-Pro,官方说明这些中核替代了前代的小核集群;分析 2026 新机时,不能把它继续当成 Exynos 2500 的传统三集群。Google Tensor G4 使用 Arm 公版 Cortex 核心(1×Cortex-X4 + 3×Cortex-A720 + 4×Cortex-A520),Google/Samsung 在 SoC 集成、频率调度和 TPU/NPU 侧做定制,核心频率通常设得比同代骁龙和天玑低一些,以换取更好的功耗和散热表现。

在 Perfetto 中识别不同 SoC 的核心拓扑,最直接的方法是看 CPU Frequency Track:高通 Oryon 的双集群通常体现为两个主要频率策略组;联发科全大核的几个集群频率跨度相对紧凑;传统大小核的频率跨度则非常大(比如小核 1.8GHz 对比大核 3.4GHz)。

[已验证: 公开产品规格 + ARM 官方架构文档]

### 微架构差异对 IPC 的影响

同样是 ARMv9 指令集,不同核心的微架构设计会导致 IPC（Instructions Per Cycle）有显著差异。这直接影响在 Perfetto 中分析 CPU 利用率时的判断。

高通的 Oryon 核心是自研微架构,开发团队背景来自 Nuvia,创始成员有 Apple CPU 团队经历。二手微架构分析文章称 Oryon 采用大容量 L1 缓存和私有 L2 缓存设计(每个核心独占 L2),但缓存拓扑的具体参数(容量、延迟周期)尚未有 Qualcomm 官方白皮书、Hot Chips/ISSCC 演讲、芯片拆解报告或可信 benchmark 数据确认,容易把 Snapdragon X Elite 与 8 Elite 的 缓存拓扑混用。当前能确认的方向性特征是:大容量 L1 带来更好的命中率,私有 L2 消除了多核共享缓存带来的竞争延迟,但 L2 容量和延迟周期仍待一手资料确认。在 Perfetto 中,Oryon 核心在缓存不命中的工作负载上可能会有偶尔的延迟尖峰,但整体吞吐量很好。

[待验证: Oryon L1/L2 容量和访问延迟周期:Qualcomm 公开产品页未披露具体数字,待官方白皮书、Hot Chips/ISSCC 或芯片拆解报告确认;L2 已确认为私有(非共享),但容量和延迟数值仍待验证]

ARM 的 Cortex-X925 是 ARM 最高性能的公版核心。Arm 官方公开口径是:相对 Cortex-X4,私有 L2 从 2MB 提升到最高 3MB,Geekbench 6.2 IPC 提升约 15%,前端、乱序窗口和后端负载管线都有扩展。Cortex-A720 作为性能-能效核心,IPC 虽然不如 X 系列,但能效比非常出色。联发科将 A720 作为全大核设计中的「能效核心」使用,其基础性能仍远超传统的 A5xx 系列小核心。

Google Tensor G4 使用 Arm Cortex-X4/A720/A520 公版核心,微架构与同代 Cortex 一致,但频率设置更为保守。在 Perfetto 中,同一时间段内 Tensor 的 CPU 利用率数值可能看起来更高(因为频率低、单周期处理能力低),但这不代表性能差,只是基准不同。

### 厂商调度策略差异

硬件只是基础,直接影响分析结论的是各家的软件调度策略。同样是基于 EAS（Energy Aware Scheduler）的 Android 内核,不同厂商的参数调优会导致 Perfetto 中看到完全不同的调度行为。

高通的调度策略通常偏向性能:在检测到重负载时会快速将任务迁移到大核并拉高频率。高通还有一套独有的 Perflock 机制(封装在 `libqti-perfd-client.so` 中),允许系统服务或应用直接请求锁定 CPU 频率。例如打开相机时,系统会通过 Perflock 将所有核心频率拉到最高,同时关闭 Power Collapse:

```c
// 高通 Perflock 请求示例
// 源码路径: vendor/qcom/proprietary/commonsys-intf/android-perf/mp-ctl/client.cpp
static INT32 perfLockParamsOpenCamera[] = {
    MPCTLV3_ALL_CPUS_PWR_CLPS_DIS, 0x1,     // 关闭 Power Collapse
    MPCTLV3_SCHED_BOOST, 0x1,                // 启用调度器 Boost
    MPCTLV3_MAX_FREQ_CLUSTER_BIG_CORE_0, 0xFFF,   // 大核拉满
    MPCTLV3_MIN_FREQ_CLUSTER_BIG_CORE_0, 0xFFF,
    MPCTLV3_MAX_FREQ_CLUSTER_LITTLE_CORE_0, 0xFFF, // 小核拉满
    MPCTLV3_MIN_FREQ_CLUSTER_LITTLE_CORE_0, 0xFFF,
};
```

[来源: obsidian/Cubox/高通Perflock - yooooooo - 博客园-2024-11-18.md]

这种 Perflock 机制在 Perfetto 中的表现是:某些时刻所有 CPU 核心的频率会突然同时拉到最高,即使用户操作并不需要这么高的性能。这在分析功耗或发热问题时需要区分:是 App 的代码触发了重负载,还是厂商的系统服务通过 Perflock 提频了。

联发科的调度策略相对保守,更强调能效平衡。联发科也有类似的性能提示机制(通常通过 `/sys/devices/system/cpu/cpu*/cpufreq/` 节点控制),但在默认策略上不那么激进。不过,在全大核架构下,调度器的迁移更多发生在同性能级别的核心之间,因为没有传统意义上的「小核」作为低优先级任务的收容区,负载均衡在几个性能接近的集群内部分配。

**在 Perfetto 中观察全大核迁移行为**,可以通过以下方式:

1. **CPU Scheduling Track** 中直接统计线程的 `migrations` 次数。全大核架构下,不同集群间不再有数量级的性能差距,迁移对任务执行性能的影响更小。但迁移频率不一定更高:没有大小核之间的性能断崖,调度器不需要频繁地把任务在高性能核和低性能核之间来回搬。用 SQL 查询可以量化迁移模式:
```sql
-- 统计每个线程在 10 秒窗口内的迁移次数
-- sched 表只有 cpu 字段记录当前所在核心,没有 prev_cpu,需要用 LAG 窗口函数从上一条调度记录取上一次所在的 CPU
WITH sched_with_prev AS (
  SELECT
    *,
    LAG(cpu) OVER (PARTITION BY utid ORDER BY ts) AS prev_cpu
  FROM sched
)
SELECT
  tid,
  thread.name,
  COUNT(*) AS migration_count
FROM sched_with_prev
  JOIN thread USING (utid)
WHERE ts BETWEEN <start_ts> AND <end_ts>
  AND prev_cpu IS NOT NULL
  AND prev_cpu != cpu
GROUP BY tid
ORDER BY migration_count DESC
LIMIT 20;
```

这个查询只统计同一线程连续两次运行所在 CPU 不同的次数。窗口太短或包含大量后台线程时,结果会被调度噪声放大,实战中要和前台线程、频率轨道一起看。

2. **CPU Frequency Track** 的对比特征:传统大小核的频率跨度极大(小核 1.8GHz vs 大核 3.4GHz),全大核的几个集群频率区间更紧凑(例如 2.0GHz / 2.85GHz / 3.62GHz)。如果频率 Track 中看不到明显的「低频区」和「高频区」二分,基本可以判断为全大核或近全大核架构。

3. **sched_waking / sched_wakeup 事件**中观察唤醒目标 CPU 的分布。大小核架构下,低优先级唤醒偏向小核(CPU 4-7);全大核架构下唤醒目标分布更均匀,没有明显的「小核汇聚」现象。

需要区分的是:迁移频繁不等于调度效率低。全大核的核心间性能差距小,同性能级别核心间的迁移开销较低(Arm DSU 提供缓存一致性协议和可选共享系统缓存,但任务迁移仍然会损失私有 L1 / L2 的局部性)。实际迁移成本要看缓存未命中、`uclamp`、集群策略、唤醒路径和具体工作负载,不能简单用 DSU 的存在推论"跨核迁移成本低"。在 Perfetto 中,只有迁移导致缓存抖动(例如 `cpu_cycles / instructions` 比值突然上升)时才需要关注。

[已验证: ARM DSU-120 架构手册:DSU 提供一致性协议和可选共享缓存,但不等于跨核复用对方私有 L2]

[已验证: ARM DSU-120 缓存一致性协议文档; Perfetto sched 表结构; MediaTek Dimensity 9400 公开规格]

[待验证: 联发科的具体调度参数和提频策略在 AOSP 开源部分不完整,需实机确认]

联发科调度链路在 AOSP 公共代码中的锚点，主要集中在几条公开内核路径：schedutil governor（`kernel/sched/cpufreq_schedutil.c`）通过调度器的 `cpufreq_update_util()` 回调在 CFS util 更新时计算下一档频率，iowait boost 在连续 IO 唤醒时按 tick 窗口逐级提高 boost；uclamp（`kernel/sched/sched.h`）约束任务可用频率范围，top-app 通常设置较高的 uclamp_min；EAS 选核逻辑位于 `kernel/sched/fair.c`（`find_energy_efficient_cpu()` / `compute_energy()`），在多 cluster 之间选择节能收益大于迁移成本的目标。Dimensity 的 1+3+4 拓扑中，超大核与其他核之间迁移成本较高（私有 L1/L2 不共享）。联发科 vendor kernel 在 energy model 中为每个 cluster 定义不同的静态功耗和 OPP 表参数，这部分未进入 AOSP 主线。Dimensity 9400（代号 MT6991）的具体频率曲线定义在 vendor kernel 设备树中，通过 `operating-points-v2` 传递到 mtk-cpufreq driver。

[待验证：Dimensity 9400 具体 freq table 数值、MTK EAS vendor patch 与主线的差异量、real device 实际调度行为需通过 Perfetto traces 测量]

**sched_ext BPF 调度器(Linux 6.12+ / Android common 6.12 / 6.18 分支)**:sched_ext 允许 OEM 通过 eBPF 程序替换内核默认调度策略。Linux 6.12 合入主线,Android common 6.12 与 Android 17 支持的 android17-6.18 分支均已包含 sched_ext 基础设施(`kernel/sched/ext.c`)。部分 OEM 据报道开发了各自的 sched_ext 调度器实现,但公开检索未找到可核实的源码仓库、commit 或官方文档;具体名称和功能描述需要 vendor kernel 源码或实机确认后才能写入确定结论。设备是否启用 sched_ext 取决于 `CONFIG_SCHED_CLASS_EXT` 和具体 kernel tag 配置,AOSP 默认调度链尚未切换到 sched_ext。

[待验证: 各 OEM BPF 调度器的具体实现细节、适用版本和性能影响需要实机或 vendor kernel 源码确认。来源: DeepResearch 2026-05-07]

## GPU 差异对渲染性能的影响

CPU 核怎么排、任务怎么调，决定了"算得动"；但帧能不能按时画出来，看的是 GPU。渲染管线的核心执行单元就是 GPU。§2.10 已经分析过 GPU 渲染的通用原理,但不同 SoC 的 GPU 架构差异会直接影响渲染性能和 Perfetto 中 GPU Track 的表现。

### 四大 GPU 架构概览

高通的 **Adreno** GPU 是移动端综合性能最强的 GPU 之一。Adreno 起源于早期收购 ATI/AMD 的 Imageon 移动 GPU IP,经过多年自研迭代,形成了独特的 TBR（Tile-Based Rendering）架构。高通称其渲染方式为 FlexRender:它可以根据场景动态选择直接渲染或分块渲染模式。Adreno 的驱动优化非常成熟,对 Vulkan 和 OpenGL ES 的支持都很完善。在高端游戏和复杂 UI 渲染场景下,Adreno 通常有最好的帧率稳定性。

ARM 的 **Mali** 和 **Immortalis** GPU 是使用最广泛的移动 GPU IP。Immortalis 曾是 ARM 旗舰 GPU 分支(支持硬件光追),Mali 覆盖高端和中端 GPU。Mali 也是 TBR 架构,通过 Transaction Elimination 等技术减少内存带宽消耗。联发科旗舰芯片的 GPU 命名已随代际变化:Dimensity 9400 是 Immortalis-G925,Dimensity 9500 是 Arm Mali-G1 Ultra MC12。三星的部分 Exynos 芯片也使用 Mali GPU。Mali GPU 的特点是可配置性强(厂商可以调整着色器核心数量和 L2 缓存大小),但驱动优化的成熟度有时不如 Adreno。

三星的 **Xclipse** GPU 是移动 GPU 中的异类:它基于 AMD 的 RDNA 架构,这是 PC 和主机显卡的架构。Xclipse 940(Exynos 2400)使用 RDNA 3,支持硬件光追和可变分辨率渲染(VRS)等桌面级特性。Xclipse 的理论性能很强,但由于移动端的功耗和散热限制,持续性能输出可能不如 Adreno 稳定。在驱动方面,Xclipse 的 Vulkan 支持被认为与 Adreno 接近。

Google Tensor G4 及更早几代公开资料多以 ARM Mali 系列 GPU 为主。Pixel 10 的 Tensor G5 在 Google 官方硬件规格中只标注 Tensor G5 处理器,未列出 GPU 型号;分析 Pixel 10 GPU 问题时应以实机驱动和可核实厂商资料为准。Tensor 不追求 GPU 峰值性能,更看重端侧 AI 推理,这个需求由 TPU(Tensor Processing Unit)而非 GPU 来承担。

### GPU 差异在 Perfetto 中的表现

不同 GPU 在 Perfetto 的 `gpu_render_stages` Track 中表现有明显差异。

Adreno GPU 在 Perfetto 中的渲染阶段标记最为完整和规范。高通的 GPU 驱动会通过 `gpu_render_stages` 数据源上报详细的渲染阶段信息,包括 Vertex Processing、Fragment Processing、Compute 等细分阶段。这让 Perfetto 成为分析高通设备 GPU 瓶颈的有力工具。

Mali/Immortalis GPU 也有较好的 Perfetto 支持,ARM 提供了 Mali GPU 的 Perfetto 数据源集成。但具体上报的阶段信息可能因厂商的驱动版本不同而有差异,联发科和三星各自的 Mali 驱动版本可能导致上报的数据粒度不同。

Xclipse GPU 的 Perfetto 支持相对有限。由于 AMD 的 RDNA 架构在移动端是较新的尝试,驱动与 Android tracing 基础设施的集成程度不如 Adreno 和 Mali 成熟。在分析 Exynos 设备的 GPU 性能时,可能需要更多依赖三星提供的专用工具。

**实战经验**:在做跨设备 GPU 性能分析时,一个常见的误区是直接对比不同 GPU 上 `gpu_render_stages` 的绝对耗时数值。这就像对比不同架构 CPU 的主频一样:架构不同,每个周期做的工作量不同,数值不可直接比较。更稳的做法是:在同一设备上对比优化前后的相对变化,或者关注帧时间的一致性(是否出现明显的耗时波动)。

[待补充: 不同 SoC 上 Perfetto GPU Track 的截图对比]

[已验证: 官方文档, developer.android.com/agi 和 perfetto.dev]

## NPU / DSP / ISP 的性能相关差异

CPU 和 GPU 之外，SoC 上还有几个专用处理器对实际性能有直接影响。它们通常不直接出现在 Perfetto 的常规 Track 中，但会间接改变 CPU 负载和功耗分布。它们通常不直接出现在 Perfetto 的常规 Track 中,但它们的工作会间接影响 CPU 负载和功耗。

### NPU（神经网络处理单元）

NPU 专门用于加速 AI 推理任务。高通的 Hexagon NPU、联发科的 APU、三星的 NPU 和 Google 的 TPU 在架构和性能上有明显差异。

高通的 Hexagon NPU 在 Snapdragon 8 Elite 上有约 45% 的性能提升,主要用于设备端的大语言模型推理、AI 辅助摄影和实时语音处理。联发科的 NPU 890(Dimensity 9400)在 LLM 推理上有 80% 的速度提升和 35% 的能效改善。这些差异在实际使用中的影响是:同一款使用端侧 AI 功能的 App,在不同平台上的响应速度和功耗表现可能完全不同。

Google 的 TPU 是 Tensor 芯片的核心卖点。TPU 专门针对 Google 的 AI 服务(如语音识别、实时翻译、计算摄影)做了深度优化,在 Pixel 设备上这些功能的响应速度和精度通常优于其他平台。但 TPU 在通用 AI 工作负载上不一定比高通或联发科的 NPU 更快。

### DSP（数字信号处理器）

高通的 Hexagon DSP 是其 SoC 中非常重要的一个组件,除了 AI 推理外还负责音频处理、传感器融合、相机 ISP 的部分计算等工作。DSP 的工作不会直接出现在 Perfetto 的 CPU Track 上,但它会占用内存带宽和功耗。在分析高通设备的功耗异常时,有时候问题根源不在 CPU 或 GPU,而在于 DSP 在后台持续工作(比如始终监听的语音助手)。

### ISP（图像信号处理器）

ISP 负责相机图像处理,是影响相机启动速度和拍照延迟的关键组件。各家的 ISP 都在持续加强 AI 摄影能力(夜景增强、人像虚化、HDR+ 等),这些计算量的增加直接影响相机 App 的启动速度和拍照响应,这也正是 §8.4 中讲响应速度时需要考虑的跨平台因素。

高通、联发科和三星在 ISP 架构上的差异主要影响相机的计算摄影流水线。高计算量的 AI 后处理(如夜景合成)在内存带宽需求大的场景下可能与前台 App 的渲染竞争带宽,导致潜在的帧率波动。这在 Perfetto 中可能表现为渲染帧耗时的偶发性波动。

[已验证: 公开产品规格,来源见各厂商官方文档]

## 内存控制器与带宽差异

内存带宽是 SoC 性能的隐形天花板。CPU 和 GPU 共享系统内存,当两者同时高负载时(比如游戏场景:CPU 处理游戏逻辑 + GPU 渲染画面),内存带宽的争用就会成为瓶颈。不同 SoC 的内存控制器能力直接影响这种争用的严重程度。

### LPDDR5X 带宽差异

当前旗舰 SoC 都使用 LPDDR5X 内存,但具体配置不同。Snapdragon 8 Elite 官方产品简报写的是 dual-channel LP-DDR5x up to 5.3GHz,不是固定 4800MHz。Dimensity 9500 官方规格为 LPDDR5X 10667,Dimensity 9400 也支持 LPDDR5X。理论带宽还取决于通道数、总线位宽和终端实际配置,跨设备分析时不要只按一个标称频率推算。

实际分析更应该看有效带宽。考虑到内存控制器效率、延迟和功耗管理的差异,不同 SoC 在相同标称带宽下的有效利用率可能不同。这种差异在大规模纹理渲染(游戏)或大量数据搬运(相机 ISP 处理高像素图像)时最为明显。

### 内存带宽争用在 Perfetto 中的间接观察

Perfetto 目前没有直接的「内存带宽利用率」Track。判断带宽争用时,通常看三类间接信号:

- GPU 渲染帧耗时出现周期性波动,且波动频率与 CPU 负载变化相关,可能是 CPU 和 GPU 争用内存带宽导致的
- 在 Perfetto 的 `memmgr` Track 中观察 GPU 内存压力事件
- 对比有和没有 GPU 密集渲染时,CPU 的缓存未命中指标(如果设备支持 PMU 计数器采集)

[待补充: 不同 SoC 在高负载游戏场景下的 Perfetto 内存带宽间接指标对比]

[已验证: 官方文档, LPDDR5X 规格来自 JEDEC 标准和各厂商公开资料]

## SoC 厂商提供的性能分析工具

除了 Perfetto 这个通用工具,各 SoC 厂商还提供了各自专用的性能分析工具。这些工具能深入到 Perfetto 无法触及的硬件细节,但使用门槛也更高。

### Snapdragon Profiler

高通的 Snapdragon Profiler 是最成熟的厂商级分析工具之一。它提供三种工作模式,分别对应不同深度的分析需求。

**实时监控模式**可以展示 150+ 个硬件性能计数器的实时数据,包括 CPU 各核心的频率和利用率、Adreno GPU 的详细性能指标、Hexagon DSP 的负载等。这些计数器数据是 Perfetto 无法直接获取的。

**Trace 捕获模式**类似 Perfetto 的时间线视图,但可以叠加高通特有的硬件事件(如 GPU 的 Vertex/Fragment 阶段耗时、缓存命中率等)。

**快照捕获模式**专门用于 GPU 调试,可以捕获一帧的完整渲染状态(Framebuffer、Shader、Draw Call),对分析 GPU 渲染问题非常有用。

Snapdragon Profiler 的局限在于:只支持高通设备,且需要通过 USB 连接,对实时性要求高的场景(如触摸响应分析)不如 Perfetto 方便。

[已验证: 官方文档, developer.qualcomm.com/software/snapdragon-profiler]

### ARM Streamline Performance Analyzer

ARM Streamline 是面向所有使用 ARM CPU 和 GPU(Mali/Immortalis)的设备的分析工具。它的适用范围更广,联发科和三星的部分 Exynos 设备都可以使用。

Streamline 的核心优势在于它对 ARM Mali GPU 的深度分析能力。它可以展示 Mali GPU 的着色器核心利用率、Pipeline Stall 原因分解、L2 缓存命中率等详细信息。如果在 Perfetto 中发现 Mali GPU 上有渲染耗时异常,但无法确定瓶颈位置,Streamline 可以帮助精确定位。

Streamline 还支持采集 ARM CPU 的 PMU（Performance Monitoring Unit）事件,包括缓存未命中(Cache Miss)、分支预测失败(Branch Mispredict)、TLB Miss 等微架构级指标。这些指标在 Perfetto 中需要额外配置 `linux.ftrace` 的 `pmu` 事件才能部分获取,而 Streamline 可以直接采集。

[已验证: 官方文档, developer.arm.com/Tools%20and%20Software/ARM%20Streamline%20Performance%20Analyzer]

### 不同 SoC 上 Perfetto 数据的差异

Perfetto 作为通用工具,在不同 SoC 上的数据可用性和精度有差异。这些差异会影响分析结论:

**CPU Frequency Track**:高通设备通常能准确上报每个核心的实时频率;联发科设备有时会上报集群频率(同一集群内所有核心共享一个频率值);三星和 Google 设备的频率上报精度取决于厂商的内核配置。

**GPU Track**:Adreno GPU 上报的 `gpu_render_stages` 数据最完整;Mali GPU 次之但通常足够分析;Xclipse GPU 的数据可能较少。

**Thermal Track**:各厂商的温控策略和温度传感器配置不同,Perfetto 中 `linux.thermal` Track 上报的温度区间和降频行为会有明显差异。高通的温控通常更激进(快速降频保功耗),联发科在全大核设计下需要更精细的温控。

**Scheduling Track**:Android 设备的公平调度器口径要按内核分支判断:Android common 6.1 仍是 CFS,android15-6.6 / android16-6.12 / android17-6.18 的 fair scheduler 已包含 EEVDF。具体量产设备取决于 GKI/vendor kernel 分支。各厂商的 schedutil 调频策略、uclamp 配置和 cgroup 设置不同,会导致相同的负载在不同设备上表现出不同的频率曲线。

[已验证: 实际分析经验 + Perfetto 官方文档]

## 与其他机制的关系

SoC 平台差异不是一个独立的机制,它影响着本书前面讲过的几乎每一个性能相关机制。

与 **§5.1 Linux 进程调度** 的关系:调度器的核心决策依据是每个 CPU 核心的算力和能效比。不同 SoC 的核心拓扑(双集群 vs 三集群 vs 全大核)直接决定了负载均衡和迁移策略。Android common 6.1 的 CFS/EAS 在选核时权衡算力与功耗;android15-6.6 / android16-6.12 / android17-6.18 的 fair scheduler 已包含 EEVDF,调度决策会引入虚拟截止时间,但能效感知的选核逻辑仍然存在(详见 §5.1)。联发科的全大核架构消除了大小核之间的性能断崖,迁移更多发生在同性能级别的核心之间;高通的 Oryon 双集群让迁移更简洁。

与 **§5.3 大小核架构** 的关系:联发科的全大核策略明显改变了传统大小核架构的分析前提。它改变了分析 Perfetto 时对「小核」的预期:在传统架构上,任务在小核上执行慢是正常的;在全大核架构上,任何核心上的性能都不应该太差。

与 **§5.4 DVFS** 的关系:各厂商的 DVFS 策略差异巨大。高通的 Perflock 允许直接锁定频率,联发科的调频更依赖 EAS 的建议。在分析功耗或发热时,同样的 Perfetto 数据在不同平台上的含义不同。

与 **§2.10 GPU 渲染深入** 的关系:不同 GPU 架构(Adreno/Mali/Xclipse)的渲染管线有本质差异。同一帧画面在不同 GPU 上的渲染耗时分布不同:Adreno 可能 Vertex 阶段快、Fragment 阶段慢;Mali 可能反过来。直接对比不同 GPU 的 `gpu_render_stages` 数值是无效的。

与 **§17.1 OEM 优化通用思路** 的关系:OEM 的优化策略很大程度上受限于 SoC 平台的能力。比如高通提供了 Perflock 这种精细的频率控制接口,而联发科平台上的厂商就需要用其他方式实现类似的提频策略。了解 SoC 差异有助于理解为什么不同厂商的优化手段不同。

## 常见问题与误区

**「骁龙一定比天玑流畅」**:这是最常见的误解。SoC 的峰值性能存在差异,但实际用户体验更多取决于 OEM 的调度策略、散热设计和软件优化。一款调度激进的天玑设备可能比调度保守的骁龙设备更流畅,也可能因为散热不足更快降频。在做性能分析时,不能预设哪个平台一定更好,而要看 Perfetto 中的实际数据。

**「GPU 跑分高 = 渲染性能好」**:跑分测量的是峰值性能,但日常使用中的渲染性能更多取决于持续性能输出和驱动优化。Adreno GPU 在持续性能和驱动成熟度上的优势可能比峰值跑分的差异更重要。

**「不同设备上 Perfetto 的数据可以直接对比」**:不能。不同 SoC 的 `gpu_render_stages` 上报格式不同、CPU 频率上报精度不同、温控行为不同。跨设备对比应该关注趋势和相对变化,而不是绝对数值。

**「全大核架构一定更省电」**:不一定。联发科的全大核设计消除了小核,但 A720「能效核」的功耗仍然高于传统的 A5xx 小核。在轻负载场景下(如待机、听音乐),全大核的功耗可能反而更高。全大核的优势在于中高负载场景下没有性能断崖。

**「Google Tensor 性能差」**:这是一个过度简化的判断。Tensor 在传统 CPU/GPU 基准测试中不如骁龙和天玑,但它的设计目标是端侧 AI 体验,而不是通用峰值性能。在 Pixel 设备上,语音识别、实时翻译和计算摄影的响应速度可能优于其他平台,因为这些工作负载被 TPU 加速了。评估 Tensor 需要看具体场景是什么。

## 参考资料

### 官方文档
- Qualcomm Snapdragon 8 Elite Gen 5 官方产品页 - qualcomm.com/products/mobile/snapdragon
- MediaTek Dimensity 9400/9500 官方产品页 - mediatek.com/products/smartphones
- Samsung Exynos 2600 官方产品页 - samsung.com/semiconductor/products/exynos
- Google Tensor G5 官方博文 - blog.google/products-and-platforms/devices/pixel/tensor-g5-pixel-10/
- Google Pixel 10 技术支持 - support.google.com/pixelphone/answer/7158570
- ARM Cortex-X925/A720/A520 官方架构文档 - developer.arm.com/documentation/102807/0002
- ARM Mali-G1 Ultra MC12 技术文档 - developer.arm.com/products/silicon-ip-cpu
- ARM DSU-120 架构手册 - developer.arm.com/documentation/102807/0002

### 开源代码
- AOSP 内核调度器源码（Android common 6.1/6.6/6.12/6.18 分支）:
  - kernel/sched/fair.c（find_energy_efficient_cpu, compute_energy, EEVDF）
  - kernel/sched/cpufreq_schedutil.c（schedutil 调频策略）
  - kernel/sched/sched.h（uclamp 任务频率约束）
- 高通 Perflock 机制源码（vendor/qcom/proprietary/commonsys-intf/android-perf）

### 性能分析工具文档
- Snapdragon Profiler 官方文档 - developer.qualcomm.com/software/snapdragon-profiler
- ARM Streamline Performance Analyzer 官方文档 - developer.arm.com/Tools%20and%20Software/ARM%20Streamline%20Performance%20Analyzer
- Perfetto 官方文档 - perfetto.dev

### 技术博客与分析
- 高通 Oryon 处理器微架构分析 - Cubox 博客专栏
- 高通 Perflock 机制详解 - Cubox 博客园
- ARM 2023年最新处理器架构分析 - Cubox 博客专栏
- 多来源综合验证（2026年市场调研）

### 标准规范
- JEDEC LPDDR5X 内存标准
- Vulkan 1.3/OpenGL ES 3.2/OpenCL 3.0 FP 图形 API 规范
- Android 17 (API 37) 开发者文档
- Linux 6.12+ 调度器文档（EEVDF, sched_ext）

### 相关章节
- §5.1 Linux 进程调度
- §5.3 大小核架构
- §5.4 DVFS
- §2.10 GPU 渲染深入
- §17.1 OEM 优化通用思路