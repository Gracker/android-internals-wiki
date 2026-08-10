---
title: AutoFDO 反馈导向编译优化
chapter: '1.12'
section: '1.12'
status: finalized
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
last_verified: '2026-07-25'
last_verified_against: AOSP android-17.0.0_r1 + ACK android17-6.18-2026-06_r6 + Android/LLVM official documentation
confidence: high
sources:
  - type: aosp
    path: "system/extras/simpleperf/doc/collect_etm_data_for_autofdo.md @ android-17.0.0_r1"
  - type: aosp
    path: "build/soong/cc/afdo.go @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/libs/hwui/Android.bp @ android-17.0.0_r1"
  - type: aosp
    path: "art/libartbase/Android.bp @ android-17.0.0_r1"
  - type: aosp
    path: "art/runtime/Android.bp @ android-17.0.0_r1"
  - type: kernel
    path: "kernel/common/BUILD.bazel @ android17-6.18-2026-06_r6"
  - type: kernel
    path: "kernel/common/gki/aarch64/afdo/README.md @ android17-6.18-2026-06_r6"
  - type: kernel
    path: "kernel/common/gki/aarch64/afdo/kernel.afdo @ android17-6.18-2026-06_r6"
  - type: kernel
    path: "kernel/common/drivers/hwtracing/coresight/coresight-etm4x-core.c @ android17-6.18-2026-06_r6"
  - type: kernel
    path: "kernel/common/drivers/hwtracing/coresight/coresight-trbe.c @ android17-6.18-2026-06_r6"
  - type: official
    path: "https://android-developers.googleblog.com/2026/03/BoostingAndroid%20PerformanceIntroducingAutoFDO.html"
  - type: official
    path: "https://source.android.com/docs/core/architecture/kernel/generic-kernel-image"
  - type: official
    path: "https://clang.llvm.org/docs/UsersManual.html#using-sampling-profilers"
  - type: research
    path: "https://research.google/pubs/autofdo-automatic-feedback-directed-optimization-for-warehouse-scale-applications/"
  - type: source
    path: "https://github.com/google/autofdo"
tags:
  - autofdo
  - sample-pgo
  - llvm
  - gki
  - kernel
  - simpleperf
  - coresight
related_chapters:
  - '1.7'
  - '5.2'
  - '8.3'
  - '8.7'
drafted_date: '2026-04-06'
drafted_by: openclaw-task2a
reviewed_by: openclaw-task6
reviewed_date: '2026-05-19'
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed
pipeline_stage: ready-to-publish
deepseek_cn_review_state: done
task9_reviewed_date: "2026-06-12"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-07-14T17:26:54+08:00"
finalized_date: "2026-05-19"
finalized_by: openclaw-task9-auto-promote
last_task2b_at: "2026-05-19T15:20:11+08:00"
task6_review_notes_round5: "2026-07-14 Task6 revisiting-review round5 (post-Task9 autofix): pass-light-edit. L1 小修 2 处（形容词+冒号「思路很简单」→「思路」；冗余副词「真正」×1 删除）。L2: 结构完整，outline 5/5 锚点 + 2/2 扩展覆盖。无新增 L3/L4 回炉项。task9_result=auto-fixed（非 pass-tech-review），送 Task9 正式复审。"
last_task6_audit: "2026-06-08"
last_task9_audit: "2026-06-12"
last_task9_autofix_at: "2026-06-12"
last_task6_at: "2026-07-14T13:14:05+08:00"
last_task6_review_log: "logs/review/2026-05-19-16-review.md"
last_task9_review_log: logs/deep-review/2026-07-14-17-deep-review.md
task9_review_notes: "2026-06-12 Task9 idle audit: auto-fixed android15-6.6 branch HEAD benchmark drift and Android17/module roadmap boundary; no queue entry; return to Task6. | 2026-05-19 Task9 deep review: pass-tech-review。P0 0 / P1 0 / P2 0；AutoFDO kernel profile 命令链、GKI 分支路径、android15/android16 数据口径复核通过；模块化 AutoFDO Android17 段落仅作为 P3 roadmap 口径收紧建议记录。"
last_deepseek_cn_review_at: 2026-07-15
---

# 1.12 AutoFDO 反馈导向编译优化

编译器不知道线上设备最常执行哪条路径，只能先用静态启发式规则决定函数内联、基本块顺序和热点/冷点布局。AutoFDO 把真实工作负载中的执行采样转换成 LLVM sample profile，再用这份 profile 重新构建二进制，让编译器根据运行时证据做这些决策。

它不会在手机运行时“自动优化”某个应用，也不是 ART 的 Baseline Profile。AutoFDO 的反馈流程发生在构建系统中：

```text
运行代表性工作负载
  → 采集指令/分支历史
  → 地址与符号还原
  → 生成 LLVM sample profile
  → 用同源代码和相近工具链重新编译
  → A/B 性能与稳定性验证
  → 发布 profile 或二进制
```

Android 17 同时能看到两类接入：

- 平台 userspace 的 native library / executable 由 Soong `afdo` 能力接入；
- ACK `android17-6.18-2026-06_r6` 携带 GKI `kernel.afdo`，Kleaf 在构建 `vmlinux` 时引用。

当前基线为 AOSP `android-17.0.0_r1` 和 ACK `android17-6.18-2026-06_r6`。Android 15/16 的分支只用于说明 kernel AutoFDO 的 rollout。

---

## Sample PGO 与 AutoFDO

PGO（基于配置文件的优化，Profile-Guided Optimization）按 profile 的产生方式大致分两类：

| 类型 | 数据来源 | 优点 | 主要代价 |
|---|---|---|---|
| Instrumentation PGO | 编译器插入计数器，运行后产生精确计数 | 基本块和边信息完整 | 需要插桩构建，运行开销与代码布局都会变化 |
| Sample PGO / AutoFDO | PMU、分支 trace 或采样 profiler 记录运行位置 | 不必改源代码或插入计数器，适合生产型工作负载 | 采样会丢失、偏斜，地址还原和 workload 代表性更难保证 |

“Automatic”指 profile 从采样数据自动转换并进入反馈构建，不表示系统能省略工作负载、符号、工具链和验证。

采样也有开销。Coresight trace 会产生 AUX 数据，需要缓冲、压缩和后处理；数据量过大时还可能 overflow 或被 simpleperf 限流。它没有 instrumentation counter 的代码侵入，但采集仍会影响设备。

### 编译器如何使用配置文件

LLVM sample profile 可以影响：

- 热点调用的内联决策；
- 基本块与函数的布局；
- 分支权重；
- 热/冷代码拆分；
- 优化预算在不同函数上的分配。

最终变化的是机器码，不是 C/C++ 源码语义。配置偏差可能造成代码膨胀或性能回退，编译器和链接器也可能有缺陷。Android 的发布流程仍要比较 profile、二进制 text section、基准性能和稳定性。

---

## Android 17 的 userspace 接入

Soong 的 `build/soong/cc/afdo.go` 负责 C/C++ 目标的 AFDO 属性、profile 查找和编译参数。模块用：

```bp
afdo: true,
```

声明希望使用由构建环境提供的 sample profile。Android 17 固定 tag 中，可以直接看到：

- `frameworks/base/libs/hwui/Android.bp` 的 `libhwui`；
- `art/libartbase/Android.bp` 的 `libartbase`；
- `art/runtime/Android.bp` 的 `libart`；

开启了 `afdo: true`。

这只能证明目标具备 AFDO 构建接入，不能证明任意本地构建都一定拿到了有效 profile。是否使用，还取决于配置、目标 arch、构建变体和产物日志。验证时应在 verbose build log 中查找 `-fprofile-sample-use=`，再核对该路径对应的 profile。

### 与 ART Baseline Profile 的区别

| 维度 | AutoFDO | Baseline / Runtime Profile |
|---|---|---|
| 主要代码 | C/C++ native binary、library、kernel | 应用 DEX 中的 Java/Kotlin 方法 |
| 编译器 | Clang/LLVM | ART / dex2oat |
| profile 单位 | 地址、源码位置、调用与分支样本 | DEX 类和方法热点 |
| 生效时机 | 系统或内核构建 | 安装、更新或后台 dexopt |
| 谁负责 | Android 平台、内核、OEM 构建团队 | 应用开发者、分发渠道和 ART |

Baseline Profile 决定应用中哪些 DEX 路径值得提前编译。AutoFDO 让 `libhwui`、`libart`、Bionic 或内核等 native 目标按照真实系统热点重新生成机器码。两者可以同时改善启动，但不能互换。

---

## Android 17 GKI 已接入 `kernel.afdo`

ACK `android17-6.18-2026-06_r6` 中有三条直接证据：

1. `gki/aarch64/afdo/kernel.afdo` 存在；
2. 同目录 README 记录 profile 来源、工作负载、转换命令和基准；
3. 根 `BUILD.bazel` 的 GKI 目标设置：

```python
clang_autofdo_profile = ":gki/aarch64/afdo/kernel.afdo"
```

当前标签已经把内核 AutoFDO 接入 GKI 构建。说明文档指出，当前 profile 针对 AArch64 kernel 6.18.21 采集，并会在对应滚动分支持续更新。tag 固定了某次 profile 内容，分支最新提交仍会继续变化；复现实验必须记录使用的是 tag、profile blob 还是分支提交。

### Android 17 README 的性能数据

固定 tag 的 README 给出 Pixel 8 结果：

| Benchmark | Improvement |
|---|---:|
| Boot time | 1.1% |
| Cold App launch time | 6.6% |
| Binder-rpc | 15% |
| Binder-addints | 23% |
| Hwbinder | 23% |

这些数字不能直接当成所有 Android 17 设备的收益。README 同时注明：

- 结果仍是 preliminary；
- 当时 Pixel 对 6.18 的功耗、CPU frequency scaling 和调度尚未完全调优；
- Binder 三项是多轮测试中的最佳结果，用于处理方差。

这些结果只说明该 profile 在特定 Pixel 8 实验中观察到正向变化。OEM 仍要在自己的 SoC、调度配置、vendor modules 和 CUJ 上重新进行 A/B 测试。

---

## 分支 trace 从哪里来

### PMU、ETM/ETE 与 TRBE 的分工

PMU 是 ARM CPU 性能事件的基础设施，simpleperf 通过 Linux perf 接口访问。要生成高质量 AutoFDO profile，仅有周期采样未必足够；Android kernel 流程使用 Coresight 分支 trace 还原已执行的 instruction stream。

硬件实现随 SoC 变化：

- ETM（嵌入式跟踪宏单元，Embedded Trace Macrocell）是常见的 Coresight 指令 trace 源；
- ARMv9 平台可以使用 ETE（Embedded Trace Extension）；
- TRBE（跟踪缓冲扩展，Trace Buffer Extension）把 trace 写入内存缓冲区。

simpleperf 对用户暴露的事件名仍是 `cs-etm`。命令中的 `cs-etm:k` 是软件接口名，不代表每台设备底层一定只有传统 ETM。ACK 当前 tag 中既有 `coresight-etm4x-core.c`，也有 `coresight-trbe.c`，但具体设备是否提供、是否可访问，要看 SoC、内核配置和权限。

### 为什么工作负载比采样时长更重要

Profile 只描述采集期间实际执行的代码。只跑一次开机，会过度偏向 boot；只启动一个应用，会遗漏 Binder、文件系统、网络、内存回收和后台工作。

Android kernel README 使用的代表性流程包括：

- 对前 100 个应用执行 App Crawler；
- 单应用 crawler 运行 3 分钟、执行两次；
- 单应用启动 3 秒、执行 15 次；
- 每次启动后终止进程并清 cache，覆盖 cold startup。

Android 官方 blog 还报告实验室工作负载与内部 fleet 执行模式约有 85% 相似。这个数字只说明该套 Google 工作负载的验证结果，不是 OEM 自建 workload 的天然质量分。

---

## 从 `perf.data` 生成 `kernel.afdo`

Android 17 simpleperf 文档和当前 ACK README 给出的 kernel 流程可整理成四步。

### 1. 准备可还原的构建

至少保留：

- 与测试镜像匹配的未剥离 `vmlinux`；
- kernel modules 的未剥离 ELF；
- build ID；
- 当前源码、toolchain 和构建配置；
- 可选但推荐的 `-fdebug-info-for-profiling`。

用另一次构建的 `vmlinux` 强行还原地址，会让 profile 映射到错误源码位置。`--allow-mismatched-build-id` 只是工具提供的容错开关，不能用来忽略来源信息。

### 2. 设备侧录制并转为 branch list

测试设备通常需要 userdebug/eng 构建、root 权限、Coresight 能力和匹配的内核配置：

```bash
adb root
adb shell
cd /data/local/tmp

simpleperf record \
  -e cs-etm:k \
  -a \
  --duration 60 \
  -z \
  -o perf.data

mkdir branch_data
simpleperf inject \
  -i perf.data \
  -o branch_data/branch01.data \
  --output branch-list \
  --binary kernel.kallsyms
```

`perf.data` 是原始采集容器；`branch01.data` 是压缩后的中间 branch-list。文档建议多次录制，因为 ETM instruction stream 在高负载下可能因 overflow 和 rate limiting 丢失。多份 profile 能增加覆盖，但也要防止放大异常工作负载的噪声。

### 3. Host 侧生成 AutoFDO text profile

把所有 branch list 与对应未剥离二进制放到 host：

```bash
adb pull /data/local/tmp/branch_data
cd branch_data

simpleperf inject \
  -i branch01.data,branch02.data \
  --binary kernel.kallsyms \
  --symdir . \
  --allow-mismatched-build-id \
  -o kernel.autofdo \
  -j 20
```

`kernel.autofdo` 是按 kernel binary 聚合并符号化后的 text profile。若采集覆盖多个 binary，必须按 binary 分开处理；不能把同一份未区分目标的地址样本同时用于 `vmlinux`、`.ko` 和 userspace library。

### 4. 转为 LLVM sample profile

当前 Android 17 ACK README 使用：

```bash
create_llvm_prof \
  --profiler=text \
  --binary=/path/to/vmlinux \
  --profile=kernel.autofdo \
  --format=extbinary \
  --use_fs_discriminator \
  --out=kernel.afdo \
  --prof_sym_list=false
```

几个参数不能随意省略：

- `--binary` 必须指向匹配的未剥离 `vmlinux`；
- `--use_fs_discriminator` 是当前 GKI README 的转换要求；
- `--prof_sym_list=false` 避免 Clang 把未列入 profile 的 kernel 函数都视为 cold。

Kernel profile 不可能覆盖所有错误处理、中断和低频管理路径。保留未采样函数的标准优化策略，可以降低 coverage 不足造成的去优化风险，也能避免某些 hot/cold section 与初始化代码段不匹配。

---

## Profile 的质量控制

AutoFDO 更隐蔽的失败方式是配置文件成功接入，但性能在真实场景回退。

### Profile 与 binary 必须接近

源码、内联结构和地址布局变化后，旧样本的可用程度会下降。应记录：

- 内核/平台提交；
- Clang 版本；
- build ID；
- profile 生成时间和输入工作负载；
- profile 覆盖的二进制；
- 转换工具版本与完整命令。

固定 tag 能保证复现边界。分支 HEAD 的 `kernel.afdo` 会持续刷新，不记录 profile blob 就无法解释两次构建差异。

### 覆盖率不等于代表性

Profile 覆盖更多函数，不一定更好。后台压力测试、开机和交互启动的权重若与真实产品不一致，编译器可能把有限的 I-cache 和内联预算分给错误路径。

可以按 CUJ 分桶收集，再决定权重：

- boot；
- cold/warm app launch；
- Binder/HWBinder；
- 相机、音频、显示；
- 文件系统与存储；
- 网络；
- 内存压力和进程回收；
- OEM 自有硬件路径。

### 不要只看几何平均

一个聚合分数可能掩盖关键回退。至少分别检查：

- P50/P90/P95/P99 启动延迟；
- boot 分段；
- Binder transaction latency；
- cycles、instructions、branch misses、I-cache misses；
- 功耗和温升；
- 二进制 text size；
- crash、hung task 和 watchdog。

---

## 正确的 A/B 验证

AutoFDO 不会在 Perfetto 里生成名为 `AutoFDO` 的 slice。它改变的是同一源码路径的执行成本。

### 构建变量只保留 profile

两组镜像应保持：

- 同一源码 tag/commit；
- 同一 Clang、Kleaf/Soong 版本；
- 同一 `defconfig`、LTO 和链接参数；
- 同一设备和固件；
- 同一温度、电量与调频条件；
- 唯一变量为是否应用目标 profile。

先从 verbose build log 和反汇编确认 A 组没有使用 profile、B 组已经使用。否则“无差异”可能只是两组都没接入，所谓“提升”也可能来自工具链或配置漂移。

### Perfetto 看系统结果

Perfetto 适合比较：

- cold startup 的 `system_server`、Zygote、app 和首帧分段；
- Binder 请求的调用方等待与服务端执行；
- runnable、CPU frequency、idle 和调度迁移；
- 文件系统 I/O 和 page fault；
- boot timeline。

同一 CUJ 至少运行足够轮次，并采用相同的 cache/进程状态。只比较单次截图没有统计意义。

### simpleperf 看函数和硬件事件

对 A/B 两组执行相同 workload：

```bash
adb shell simpleperf stat \
  -e cycles,instructions,branch-misses,cache-misses \
  --app com.example.app \
  --duration 10
```

硬件事件是否可用、怎样归因取决于 PMU 和权限。函数级变化可用 `simpleperf record/report` 验证热点是否移动；内核目标还要区分 GKI `vmlinux`、GKI module 和 vendor module。

如果 cold launch 变快但 cycles 上升，可能是调频、并行度或 I/O 改变；如果微基准变快而整机 CUJ 不变，说明该路径不是当前瓶颈。两类结果都需要解释，不能只挑正向指标。

---

## OEM 与应用开发者分别做什么

### OEM / 平台团队

直接使用 Android 17 GKI profile 只是起点。OEM 还应：

1. 确认实际 GKI build 引用了固定 tag 的 `kernel.afdo`；
2. 为自研内核差异和产品 CUJ 采集代表性 profile；
3. 为 GKI modules/ vendor modules 分别保留未剥离 ELF 和 profile；
4. 用同版本工具链生成每个 target 的 sample profile；
5. 建立性能、体积、功耗和稳定性门禁；
6. 随代码漂移定期刷新，避免长期复用旧 profile。

当前 ACK README 聚焦 `vmlinux`。模块需要单独采集、符号化和构建接入；不能因为内核主体有 `kernel.afdo` 就认定 vendor driver 已经得到相同优化。

### 应用开发者

应用开发者通常不控制系统 `libart`、`libhwui` 或 GKI 的构建。日常工作应放在：

- Baseline Profile 和 Startup Profile；
- native library 自身的 PGO/LTO（如果掌握构建与代表性 workload）；
- 用 Perfetto 和 simpleperf 确认瓶颈层次；
- 不把 OEM 或 Pixel kernel AutoFDO 数据承诺为应用自身收益。

应用包含大型 C/C++ library 时，也可以建立自己的 sample PGO 流程，但那是该 native target 的构建优化，不等于 Android GKI AutoFDO。

---

## 版本演进

| 时间点 | 已确认变化 | 当前阅读方式 |
|---|---|---|
| Android 13 固定 tag | `libhwui` 已可见 `afdo: true` | userspace native AFDO 已进入代表性平台模块 |
| Android 15 / 16 GKI | 2026 官方 blog 说明先向 6.6、6.12 分支持续发布 kernel profile | 作为 kernel rollout 历史，不把 branch HEAD 数据当作 Android 17 固定结果 |
| Android 17 / `android17-6.18-2026-06_r6` | 固定 tag 含 profile、README，并在 `BUILD.bazel` 接入 | 当前 kernel 基线；性能数字按 README 的 preliminary 条件解释 |

官方 blog 发布时把 Android 17 对应的 6.18 GKI 写作后续扩展方向；当前固定 tag 已经包含对应 profile。版本判断应以所选 tag 的文件与构建规则为准，不能停留在更早的 roadmap。

---

## 常见误区

### “AutoFDO 会在用户手机上边运行边改内核”

不会。采集、转换、重新编译和验证发生在研发/构建流程，用户设备运行的是已经用 profile 编译好的产物。

### “`afdo: true` 证明本地 binary 已优化”

它只打开模块的构建接入。还要从 build log、profile 路径和编译参数确认实际使用。

### “ETM 采集没有性能开销”

它不需要插桩计数器，但 trace 数据仍消耗硬件缓冲、带宽、存储和后处理时间，也可能丢失。

### “Pixel 8 的 6.6% cold launch 会复制到所有设备”

该数字来自 Android 17 README 的特定初步实验，且平台当时尚未完全调优。不同 SoC、kernel config、vendor modules 和 workload 都会改变收益。

### “同一个 `kernel.afdo` 能优化所有模块”

Sample profile 必须对应具体 binary 和源码位置。`vmlinux`、GKI module、vendor module 与 userspace library 要分别处理。

### “AutoFDO 替代 Baseline Profile”

前者优化 native/kernel 构建，后者指导 ART 编译应用 DEX。它们作用层不同。

---

## 源码阅读顺序

1. `system/extras/simpleperf/doc/collect_etm_data_for_autofdo.md`：采集、branch-list、符号化和转换；
2. ACK `gki/aarch64/afdo/README.md`：Android 17 profile 来源、命令与 benchmark 限定；
3. ACK `BUILD.bazel`：`clang_autofdo_profile` 怎样进入 GKI 构建；
4. `build/soong/cc/afdo.go`：userspace C/C++ 模块怎样查找和应用 profile；
5. `libhwui`、`libartbase`、`libart` 的 `Android.bp`：真实模块怎样声明 `afdo: true`；
6. Coresight ETM/TRBE 驱动：设备侧 trace 能力从哪里来。

完整证据需要回答四个问题：profile 采了什么 workload、对应哪个 binary、由哪个构建规则消费、收益用什么 A/B 结果确认。缺少任何一项，AutoFDO 都只是一个已开启但缺乏验证证据的编译选项。
