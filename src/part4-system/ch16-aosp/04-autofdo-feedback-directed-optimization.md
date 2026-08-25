---
title: AutoFDO 反馈导向优化与 Android 验证
chapter: '16.4'
section: '16.4'
status: finalized
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
last_verified: '2026-07-25'
last_verified_against: AOSP android-17.0.0_r1 + ACK android17-6.18-2026-06_r6 + Android/LLVM official documentation
confidence: high
sources:
- type: aosp
  path: system/extras/simpleperf/doc/collect_etm_data_for_autofdo.md @ android-17.0.0_r1
- type: aosp
  path: build/soong/cc/afdo.go @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/libs/hwui/Android.bp @ android-17.0.0_r1
- type: aosp
  path: art/libartbase/Android.bp @ android-17.0.0_r1
- type: aosp
  path: art/runtime/Android.bp @ android-17.0.0_r1
- type: kernel
  path: kernel/common/BUILD.bazel @ android17-6.18-2026-06_r6
- type: kernel
  path: kernel/common/gki/aarch64/afdo/README.md @ android17-6.18-2026-06_r6
- type: kernel
  path: kernel/common/gki/aarch64/afdo/kernel.afdo @ android17-6.18-2026-06_r6
- type: kernel
  path: kernel/common/drivers/hwtracing/coresight/coresight-etm4x-core.c @ android17-6.18-2026-06_r6
- type: kernel
  path: kernel/common/drivers/hwtracing/coresight/coresight-trbe.c @ android17-6.18-2026-06_r6
- type: official
  path: https://android-developers.googleblog.com/2026/03/BoostingAndroid%20PerformanceIntroducingAutoFDO.html
- type: official
  path: https://source.android.com/docs/core/architecture/kernel/generic-kernel-image
- type: official
  path: https://clang.llvm.org/docs/UsersManual.html#using-sampling-profilers
- type: research
  path: https://research.google/pubs/autofdo-automatic-feedback-directed-optimization-for-warehouse-scale-applications/
- type: source
  path: https://github.com/google/autofdo
tags:
- autofdo
- sample-pgo
- llvm
- gki
- kernel
- simpleperf
- coresight
related_chapters:
- '1.5'
- '5.1'
- '8.3'
- '21.4'
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
pipeline_stage: ready-to-publish
consolidated_from:
- src/part1-fundamentals/ch01-architecture/12-autofdo-optimization.md
---

# AutoFDO 反馈导向优化与 Android 验证

编译器无法预先知道线上设备最常执行哪些代码，只能先用静态启发式规则决定函数内联、基本块顺序和热点/冷点布局。函数内联是把被调用函数展开到调用位置，基本块则是一段没有中途分支的连续指令。AutoFDO（Automatic Feedback-Directed Optimization，自动反馈导向优化）把真实工作负载中的执行样本转换成 LLVM 采样 Profile，再用这份记录热点与分支分布的 Profile 重新构建二进制，让编译器根据运行数据调整这些决策。

它不会在手机运行时“自动优化”某个应用，也不同于 ART 的 Baseline Profile。AutoFDO 的反馈流程发生在构建系统中：

```text
运行代表性工作负载
  → 采集指令/分支历史
  → 地址与符号还原
  → 生成 LLVM sample profile
  → 用同源代码和相近工具链重新编译
  → A/B 性能与稳定性验证
  → 发布 profile 或二进制
```

Android 17 提供两类接入方式：

- 平台用户空间（userspace）的原生库和可执行文件由 Android 平台构建系统 Soong 的 `afdo` 能力接入；
- Android 通用内核（ACK）`android17-6.18-2026-06_r6` 携带通用内核镜像（GKI）的 `kernel.afdo`，Android 内核的 Bazel 构建系统 Kleaf 在构建内核二进制 `vmlinux` 时引用它。

当前基线为 AOSP `android-17.0.0_r1` 和 ACK `android17-6.18-2026-06_r6`。Android 15/16 分支只用于说明内核 AutoFDO 的推广过程。

---

## Sample PGO 与 AutoFDO

PGO（Profile-Guided Optimization，Profile 引导优化）按 Profile 的产生方式大致分为两类：

| 类型 | 数据来源 | 优点 | 主要代价 |
|---|---|---|---|
| 插桩 PGO（Instrumentation PGO） | 编译器插入计数器，运行后产生精确计数 | 基本块和分支边信息完整 | 需要插桩构建，运行开销与代码布局都会变化 |
| 采样 PGO（Sample PGO）/ AutoFDO | 硬件性能监控单元（PMU）、分支轨迹或采样分析器记录运行位置 | 不必改源代码或插入计数器，适合接近生产环境的工作负载 | 样本可能丢失或偏斜，地址还原和工作负载代表性更难保证 |

名称中的 “Automatic” 指 Profile 可以从采样数据自动转换并进入反馈构建，不表示系统可以省略代表性工作负载、符号、工具链和验证。

采样同样有开销。CoreSight 轨迹会产生存放硬件跟踪数据的 AUX 数据流，需要缓冲、压缩和后处理；数据量过大时还可能溢出（overflow），或被 simpleperf 限制采样速率。它不需要在程序中插入计数器，但采集过程仍会影响设备运行。

### 编译器如何使用 Profile

LLVM 采样 Profile 可以影响：

- 热点调用的内联决策；
- 基本块与函数的布局；
- 分支权重；
- 热/冷代码拆分；
- 优化预算在不同函数上的分配。

最终改变的是机器码，不会改变 C/C++ 源码定义的程序语义。Profile 偏差可能造成代码体积膨胀或性能回退，编译器和链接器本身也可能存在缺陷。Android 的发布流程仍要比较 Profile、二进制的代码段（text section）、基准性能和稳定性。

---

## Android 17 的用户空间接入

Soong 的 `build/soong/cc/afdo.go` 负责处理 C/C++ 目标的 AFDO 属性、Profile 查找和编译参数。模块使用下面的属性声明希望接入采样 Profile：

```bp
afdo: true,
```

Android 17 的固定源码标签（tag）中，可以直接看到以下模块开启了 `afdo: true`：

- `frameworks/base/libs/hwui/Android.bp` 的 `libhwui`；
- `art/libartbase/Android.bp` 的 `libartbase`；
- `art/runtime/Android.bp` 的 `libart`；

开启了 `afdo: true`。

这只能证明目标具备 AFDO 构建接入，不能证明任意本地构建都拿到了有效 Profile。是否实际使用，还取决于 Profile 配置、目标处理器架构（arch）、构建变体和产物日志。验证时，应在详细构建日志（verbose build log）中查找 `-fprofile-sample-use=`，再核对该参数指向的 Profile。

### 与 ART Baseline Profile 的区别

| 维度 | AutoFDO | Baseline / Runtime Profile |
|---|---|---|
| 主要代码 | C/C++ 原生二进制、库和内核 | 应用 DEX 中的 Java/Kotlin 方法 |
| 编译器 | Clang/LLVM | ART / dex2oat |
| Profile 记录单位 | 地址、源码位置、调用与分支样本 | DEX 类和方法热点 |
| 生效时机 | 系统或内核构建 | 安装、更新或后台 dexopt |
| 谁负责 | Android 平台、内核、OEM 构建团队 | 应用开发者、分发渠道和 ART |

Baseline Profile 标记应用中哪些 DEX 路径值得提前编译。AutoFDO 让 `libhwui`、`libart`、Bionic 或内核等原生目标按照真实系统热点重新生成机器码。两者可以同时改善启动，但不能互换。

---

## Android 17 GKI 已接入 `kernel.afdo`

ACK `android17-6.18-2026-06_r6` 中有三条直接证据：

1. `gki/aarch64/afdo/kernel.afdo` 存在；
2. 同目录 README 记录 Profile 来源、工作负载、转换命令和基准；
3. 根 `BUILD.bazel` 的 GKI 目标设置：

```python
clang_autofdo_profile = ":gki/aarch64/afdo/kernel.afdo"
```

当前源码标签已经把内核 AutoFDO 接入 GKI 构建。说明文档指出，当前 Profile 针对 AArch64 内核 6.18.21 采集，并会在对应滚动分支持续更新。固定标签只冻结某一版 Profile，分支上的最新提交仍会变化；复现实验必须记录使用的源码标签、Profile 文件内容或具体分支提交。

### Android 17 README 中的性能数据

固定标签的 README 给出以下 Pixel 8 测试结果。表中保留原始基准名称，便于与 README 对照：

| 基准项目 | 改善幅度 |
|---|---:|
| Boot time | 1.1% |
| Cold App launch time | 6.6% |
| Binder-rpc | 15% |
| Binder-addints | 23% |
| Hwbinder | 23% |

这些数字不能直接当成所有 Android 17 设备的收益。README 同时注明：

- 结果仍处于初步阶段（preliminary）；
- 当时 Pixel 针对 6.18 内核的功耗、CPU 动态调频和调度尚未完全调优；
- Binder 三项采用多轮测试中的最佳结果，以应对各轮测试之间的波动。

这些结果只说明该 Profile 在特定 Pixel 8 实验中观察到正向变化。OEM 仍要在自己的 SoC、调度配置、厂商模块（vendor modules）和关键用户流程（Critical User Journey，CUJ）上重新进行受控 A/B 测试，也就是只改变是否使用 Profile，其余条件保持一致。

---

## 分支 trace 从哪里来

### PMU、ETM/ETE 与 TRBE 的分工

PMU 是 ARM CPU 提供硬件性能事件的基础设施，simpleperf 通过 Linux perf 接口访问它。要生成高质量 AutoFDO Profile，仅有周期采样未必足够；Android 内核流程还会使用 CoreSight 分支轨迹，还原实际执行过的指令流（instruction stream）。

硬件实现随 SoC 变化：

- ETM（嵌入式跟踪宏单元，Embedded Trace Macrocell）是常见的 CoreSight 指令轨迹源；
- ARMv9 平台可以使用 ETE（Embedded Trace Extension）；
- TRBE（跟踪缓冲扩展，Trace Buffer Extension）把轨迹数据写入内存缓冲区。

simpleperf 对用户暴露的事件名仍是 `cs-etm`。命令中的 `cs-etm:k` 是软件接口名，不代表每台设备底层都只使用传统 ETM。ACK 当前标签中既有 `coresight-etm4x-core.c`，也有 `coresight-trbe.c`；具体设备是否提供这些能力、调用方是否有权访问，取决于 SoC、内核配置和权限。

### 为什么工作负载比采样时长更重要

Profile 只描述采集期间实际执行的代码。如果只跑一次开机流程，样本会过度偏向启动；如果只启动一个应用，又会遗漏 Binder、文件系统、网络、内存回收和后台任务。

Android 内核 README 使用的代表性流程包括：

- 对前 100 个应用执行自动遍历界面的 App Crawler；
- 对单个应用运行 crawler 3 分钟，共执行两次；
- 单应用启动 3 秒、执行 15 次；
- 每次启动后终止进程并清理缓存，以覆盖冷启动。

Android 官方博客还报告，实验室工作负载与内部设备群（fleet）的执行模式约有 85% 相似。这个数字只说明 Google 对该套工作负载的验证结果，不能直接代表 OEM 自建工作负载的质量。

---

## 从 `perf.data` 生成 `kernel.afdo`

Android 17 的 simpleperf 文档和当前 ACK README 给出的内核流程可以整理成四步。

### 1. 准备可还原的构建

至少保留：

- 与测试镜像匹配的未剥离 `vmlinux`；
- 内核模块的未剥离 ELF（Linux 原生二进制格式）文件，即仍保留调试符号的二进制；
- 用于确认二进制版本的 build ID；
- 当前源码、工具链和构建配置；
- 可选但推荐的 `-fdebug-info-for-profiling`，用于生成采样归因所需的调试信息。

如果用另一次构建的 `vmlinux` 强行还原地址，Profile 会映射到错误的源码位置。`--allow-mismatched-build-id` 只是工具提供的容错开关，不能用它忽略二进制来源。

### 2. 在设备上录制并转换为分支列表

测试设备通常需要可调试的 `userdebug` 或 `eng` 构建、root 权限、CoreSight 能力和匹配的内核配置。下面的命令先录制 `cs-etm:k`，再把原始数据转换成分支列表：

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

`perf.data` 是原始采集容器，`branch01.data` 是压缩后的中间分支列表（branch-list），`kernel.kallsyms` 则提供内核地址到符号名称的映射。文档建议多次录制，因为 ETM 指令流在高负载下可能因缓冲区溢出或采样限速而丢失。多份 Profile 能增加覆盖范围，但也可能放大异常工作负载产生的噪声。

### 3. 在主机上生成 AutoFDO 文本 Profile

把所有分支列表与对应的未剥离二进制放到开发主机，然后执行：

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

`kernel.autofdo` 是按内核二进制聚合并完成符号解析的文本 Profile。若采集覆盖多个二进制，必须按目标分别处理；不能把一份未区分目标的地址样本同时用于 `vmlinux`、`.ko` 和用户空间库。

### 4. 转换为 LLVM 采样 Profile

当前 Android 17 ACK README 使用下面的命令，把文本 Profile 转换成 `kernel.afdo`：

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
- `--use_fs_discriminator` 是当前 GKI README 的转换要求，用于保留编译器生成的路径区分信息；
- `--prof_sym_list=false` 避免 Clang 把未列入 Profile 的内核函数都视为冷代码。

内核 Profile 不可能覆盖所有错误处理、中断和低频管理路径。让未采样函数继续使用标准优化策略，可以降低覆盖不足导致这些函数被错误降级优化的风险，也能避免某些热/冷代码段与初始化代码段不匹配。

---

## Profile 的质量控制

AutoFDO 还有一种不容易发现的失败：Profile 已成功接入构建，但真实场景的性能反而回退。

### Profile 必须与二进制版本接近

源码、内联结构和地址布局变化后，旧样本的可用程度会下降。应记录：

- 内核和平台的代码提交；
- Clang 版本；
- build ID；
- Profile 生成时间和输入工作负载；
- Profile 覆盖的二进制；
- 转换工具版本与完整命令。

固定源码标签能划定复现范围。分支最新提交（HEAD）中的 `kernel.afdo` 会持续更新；如果不保存所用 Profile 文件的确切内容，就无法解释两次构建之间的差异。

### 覆盖率不等于代表性

Profile 覆盖更多函数并不一定更好。如果后台压力测试、开机和交互启动的权重与真实产品不一致，编译器可能把有限的指令缓存（I-cache）空间和内联优化预算用在次要路径上。

可以按 CUJ 分类收集样本，再决定各类样本的权重：

- 系统启动；
- 应用冷启动与温启动；
- Binder/HWBinder；
- 相机、音频、显示；
- 文件系统与存储；
- 网络；
- 内存压力和进程回收；
- OEM 自有硬件路径。

### 不能只看几何平均值

一个聚合分数可能掩盖关键回退。至少分别检查：

- P50/P90/P95/P99 启动延迟，即不同百分位上的耗时分布；
- 系统启动各阶段耗时；
- Binder 事务延迟；
- CPU 周期数、指令数、分支预测未命中和指令缓存未命中；
- 功耗和温升；
- 二进制代码段大小；
- 崩溃、任务长时间无响应（hung task）和看门狗超时。

---

## 正确的 A/B 验证

AutoFDO 不会在 Perfetto 中生成名为 `AutoFDO` 的轨迹区段（slice）。它改变的是同一源码路径的执行成本。

### 构建变量只保留 Profile

两组镜像应保持：

- 同一源码标签或提交；
- 同一 Clang、Kleaf/Soong 版本；
- 同一内核默认配置（`defconfig`）、链接时优化（LTO）和链接参数；
- 同一设备和固件；
- 同一温度、电量与调频条件；
- 唯一变量为是否应用目标 Profile。

先通过详细构建日志和反汇编确认 A 组没有使用 Profile、B 组已经使用。否则，“无差异”可能只是两组都没有接入 Profile，所谓“提升”也可能来自工具链或配置变化。

### Perfetto 看系统结果

Perfetto 适合比较：

- 冷启动中 `system_server`、Zygote、应用进程和首帧的分段耗时；
- Binder 请求的调用方等待与服务端执行；
- 可运行（runnable）状态、CPU 频率、空闲状态和线程在 CPU 之间的调度迁移；
- 文件系统 I/O 和缺页异常（page fault）；
- 系统启动时间线。

同一 CUJ 要运行足够多的轮次，并保持相同的缓存和进程状态。只比较一次运行的截图没有统计意义。

### simpleperf 看函数和硬件事件

下面的命令用于在 A/B 两组上执行相同工作负载，并统计硬件性能事件：

```bash
adb shell simpleperf stat \
  -e cycles,instructions,branch-misses,cache-misses \
  --app com.example.app \
  --duration 10
```

命令返回的是 10 秒采样窗口内的周期、指令和缓存等计数。硬件事件是否可用、如何归因取决于 PMU 和权限。函数级变化可用 `simpleperf record/report` 检查热点是否移动；内核目标还要区分 GKI `vmlinux`、GKI 模块和厂商模块。

如果冷启动变快但 CPU 周期数上升，可能是调频、并行度或 I/O 发生了变化；如果微基准变快而整机 CUJ 不变，说明该路径不是当前瓶颈。两类结果都需要解释，不能只挑正向指标。

---

## OEM 与应用开发者分别做什么

### OEM / 平台团队

直接使用 Android 17 GKI Profile 只是起点。OEM 还应：

1. 确认实际 GKI 构建引用了固定标签中的 `kernel.afdo`；
2. 针对自研内核差异和产品 CUJ 采集有代表性的 Profile；
3. 分别为 GKI 模块和厂商模块保留未剥离 ELF 与 Profile；
4. 使用同版本工具链为每个构建目标生成采样 Profile；
5. 在发布前设置性能、体积、功耗和稳定性检查标准；
6. 随代码变化定期刷新，避免长期复用旧 Profile。

当前 ACK README 聚焦 `vmlinux`。模块需要单独采集、完成符号解析并接入构建；不能因为内核主体使用了 `kernel.afdo`，就认定厂商驱动已经得到相同优化。

### 应用开发者

应用开发者通常不控制系统 `libart`、`libhwui` 或 GKI 的构建。日常工作应放在：

- Baseline Profile 和 Startup Profile；
- 原生库自身的 PGO/LTO（前提是能控制构建并取得有代表性的工作负载）；
- 用 Perfetto 和 simpleperf 确认瓶颈位于应用、系统还是内核；
- 不把 OEM 或 Pixel 的内核 AutoFDO 数据当作应用自身的收益承诺。

应用包含大型 C/C++ 库时，也可以建立自己的采样 PGO 流程，但那是针对该原生构建目标的优化，不等同于 Android GKI AutoFDO。

---

## 版本演进

| 时间点 | 已确认变化 | 当前阅读方式 |
|---|---|---|
| Android 13 固定标签 | `libhwui` 已可见 `afdo: true` | 用户空间原生 AFDO 已进入代表性平台模块 |
| Android 15 / 16 GKI | 2026 年官方博客说明先向 6.6、6.12 分支持续发布内核 Profile | 只作为内核推广历史，不能把分支最新提交的数据当作 Android 17 的固定结果 |
| Android 17 / `android17-6.18-2026-06_r6` | 固定标签包含 Profile、README，并在 `BUILD.bazel` 中接入 | 当前内核基线；性能数字按 README 标明的初步实验条件解释 |

官方博客发布时，把 Android 17 对应的 6.18 GKI 写作后续扩展方向；当前固定标签已经包含对应 Profile。版本判断应以所选标签中的文件和构建规则为准，不能只依据更早的路线图（roadmap）。

---

## 常见误区

### “AutoFDO 会在用户手机上边运行边改内核”

不会。采集、转换、重新编译和验证发生在研发与构建流程中，用户设备运行的是已经使用 Profile 编译好的产物。

### “`afdo: true` 证明本地二进制已经优化”

它只打开模块的构建接入。还要通过构建日志、Profile 路径和编译参数确认是否真正使用。

### “ETM 采集没有性能开销”

它不需要插桩计数器，但轨迹数据仍会占用硬件缓冲区、带宽、存储和后处理时间，也可能发生丢失。

### “Pixel 8 的 6.6% 冷启动收益会复制到所有设备”

该数字来自 Android 17 README 中的特定初步实验，且平台当时尚未完全调优。不同 SoC、内核配置、厂商模块和工作负载都会改变收益。

### “同一个 `kernel.afdo` 能优化所有模块”

采样 Profile 必须对应具体二进制和源码位置。`vmlinux`、GKI 模块、厂商模块与用户空间库要分别处理。

### “AutoFDO 替代 Baseline Profile”

前者优化原生代码和内核构建，后者指导 ART 编译应用 DEX；两者作用层不同。

---

## 源码阅读顺序

1. `system/extras/simpleperf/doc/collect_etm_data_for_autofdo.md`：采集、分支列表、符号解析和转换；
2. ACK `gki/aarch64/afdo/README.md`：Android 17 Profile 来源、命令与基准条件；
3. ACK `BUILD.bazel`：`clang_autofdo_profile` 怎样进入 GKI 构建；
4. `build/soong/cc/afdo.go`：用户空间 C/C++ 模块怎样查找和应用 Profile；
5. `libhwui`、`libartbase`、`libart` 的 `Android.bp`：真实模块怎样声明 `afdo: true`；
6. CoreSight ETM/TRBE 驱动：设备侧指令轨迹能力从哪里来。

完整证据需要回答四个问题：Profile 采集了什么工作负载、对应哪个二进制、由哪条构建规则读取、收益通过哪些 A/B 结果确认。缺少任何一项，都只能说明 AutoFDO 选项已经开启，不能证明目标产物获得了收益。
