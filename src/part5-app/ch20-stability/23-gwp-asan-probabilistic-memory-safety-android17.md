---
title: "GWP-ASan 灰度检测演进与 Android 17 内存安全防线"
chapter: "20.23"
status: ready-for-review
drafted_date: "2026-07-16"
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
last_verified: "2026-07-16"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
tags: ['gwp-asan', 'memory-safety', 'use-after-free', 'heap-overflow', 'scudo', 'android17']
related_chapters: ['20.11', '4.9', '20.15', '23.25']
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "research-gaps + AOSP结构"
gap_score: "15/20"
sources:
  - type: aosp
    path: "bionic/libc/bionic/gwp_asan.cpp (android-17.0.0_r1)"
  - type: aosp
    path: "system/memory/libmemunreachable/MemUnreachable.cpp"
  - type: aosp
    path: "external/scudo/standalone/gwp_asan.cpp"
  - type: official
    path: "https://source.android.com/docs/security/test/memory-safety"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - Native Crash 监控原理.md"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - Native 内存泄漏监控.md"
---

# 20.23 GWP-ASan 灰度检测演进与 Android 17 内存安全防线

GWP-ASan 用两层抽样把少量 Native heap allocation 放进 guard-page 区域。命中的 use-after-free、越界或错误释放会变成带 allocation/deallocation 证据的 Native 报告。它适合从大量真实设备中发现低概率内存破坏，但不能证明未命中的代码安全，也不会修复内存破坏。

本文的平台和用户空间源码锚点为 Android 17 / API 37 / `android-17.0.0_r1`。GWP-ASan 主体位于 Bionic、Zygote、debuggerd 和 `external/gwp_asan`；它没有面向应用的 Android 17 kernel 专用接口。guard page 最终依赖 `mmap()`、页权限和 `SIGSEGV`，涉及内核语义时以 `android17-6.18-2026-06_r6` 为边界。

## 1. 它解决什么问题

普通 Native crash 往往只能看到错误访问发生时的线程栈。对于 use-after-free，释放动作可能早已发生在另一条线程，访问栈只能指出受害者，无法直接指出所有权在哪一步被破坏。

GWP-ASan 在被抽样的 allocation 上保存：

- allocation 地址、请求大小、线程和调用栈；
- deallocation 线程和调用栈；
- fault 时的访问栈与错误类型；
- debuggerd 生成报告所需的 allocator state。

它主要回答“这块 heap 内存在哪里申请、在哪里释放、在哪里被错误访问”。以下问题不属于它的职责：

- 谁长期占用最多 Native heap：使用 heapprofd、`smaps` 或 allocator profile；
- 哪个对象没有释放：使用 heap profile、ownership 审计或泄漏检测；
- Java/Kotlin 对象为什么泄漏：使用 HPROF 与引用链分析；
- 任意一次内存错误都要稳定复现：使用 HWASan、ASan、MTE SYNC 或 fuzzing；
- 修复后的代码是否没有同类缺陷：靠测试、所有权设计和长期观测共同判断。

GWP-ASan 是诊断能力，不是完整的安全缓解。未被抽样的 allocation 没有 guard-page 保护；Recoverable 模式命中后还会让已经发生内存破坏的进程继续运行。

## 2. 两层抽样：先选进程，再选 allocation

Android 的默认路径包含两次选择：

1. 进程启动时，决定本次进程生命周期是否初始化 GWP-ASan。
2. 已初始化的进程中，再从 allocator 调用里选择少量 allocation 进入 guarded pool。

Android 17 的 `bionic/libc/bionic/gwp_asan_wrappers.cpp` 给出的内部默认值如下：

| 内部选项 | `android-17.0.0_r1` 默认值 | 含义 |
|---|---:|---|
| `ProcessSampling` | `128` | `default`/系统模式约每 128 次进程启动选中一次 |
| `SampleRate` | `2500` | 已选中进程中，平均约每 2500 次 allocation 尝试一次抽样 |
| `MaxSimultaneousAllocations` | `32` | guarded pool 最多同时容纳 32 个活跃 allocation |
| `Recoverable` | `true` | 默认内部选项支持恢复路径 |
| `InstallSignalHandlers` | `false` | Android 使用既有 debuggerd/Bionic 协作路径，不安装独立通用 handler |

这些数值是当前源码实现，不属于 SDK 契约。设备配置、系统属性和平台构建可以覆盖它们；普通应用不应把 `libc.debug.gwp_asan.*` 属性或 `GWP_ASAN_*` 环境变量包装成线上配置接口。

抽样也不是“每次 allocation 独立抛一次 1/2500 的硬币”。`GuardedPoolAllocator::shouldSample()` 使用线程局部倒计数，并在归零后随机生成下一段间隔，以较低分支成本逼近目标频率。

对某一次具体错误，发现概率可近似拆成：

`P(report) ≈ P(进程被选中) × P(目标 allocation 被选中) × P(错误访问碰到保护边界或释放保护窗口)`

三个因子都会受运行时长、allocation 频率、对象大小、错误方向和 slot 复用影响。零报告只能表示“尚未观测到”，不能作为缺陷已消失的证明。

## 3. Android 17 的初始化路径

应用进程的路径可以概括为：

`manifest/process policy → Zygote runtime flag → native SpecializeCommon() → android_mallopt(M_INITIALIZE_GWP_ASAN) → Bionic malloc dispatch → GuardedPoolAllocator`

### 3.1 Zygote 选择模式

`Zygote.getGwpAsanLevel()` 按以下优先级决定 runtime flag：

1. `<process android:gwpAsanMode>` 的显式值；
2. `<application android:gwpAsanMode>` 的显式值；
3. platform compat change；
4. 系统 app lottery；
5. manifest 未指定时的 default。

native `SpecializeCommon()` 再把 `NEVER`、`ALWAYS`、`LOTTERY` 或 `DEFAULT` 转成 `android_mallopt_gwp_asan_options_t::Mode`，并调用 `M_INITIALIZE_GWP_ASAN`。Android 17 对 default 应用模式还受 `persist.device_config.memory_safety_native.gwp_asan_recoverable_apps` 控制，AOSP 默认值为 `true`。这属于平台策略，应用没有修改权限。

### 3.2 Bionic 通过 malloc dispatch 接入

Android 17 的 Bionic 安装 `gwp_asan_dispatch`。`malloc()`、`calloc()` 等入口到达该 dispatch 后：

- 抽样命中且 guarded pool 能处理时，返回 guard slot；
- 未命中、pool 无空位、大小或 alignment 不支持时，转给 `prev_dispatch`；
- `free()`、`realloc()` 遇到 guarded pointer 时，交回 `GuardedPoolAllocator`；
- 其他 pointer 继续交给 backing allocator。

现代 Android 的 backing allocator 通常是 Scudo，但本条 Android 应用路径在源码上表现为 Bionic malloc dispatch 包装。把它描述成“Scudo 每次 allocation 都直接运行 GWP-ASan”会混淆层次。上游 Scudo 也有嵌入式 GWP-ASan hooks，那是另一种集成形态。

Bionic 要在 malloc_debug、heapprofd 或 malloc hooks 之前安装 GWP-ASan 才能安全组合。Android 正常初始化顺序会优先处理 GWP-ASan；若进程较晚尝试初始化且其他 dispatch 已安装，`MaybeInitGwpAsan()` 会拒绝启用。专项测试同时开启多种 allocator 工具时，应验证最终生效状态，不能只看启动参数。

## 4. Guarded pool 怎样捕获错误

### 4.1 slot 与 guard page

`external/gwp_asan` 的 Android 17 实现把整段虚拟地址先以 `PROT_NONE` 保留。每个 slot 的最大 allocation size 等于系统 page size，slot 之间夹着 guard page，池尾还保留额外页面。

allocation 命中时，分配器随机选择靠左或靠右放置，再按 alignment 调整：

- 靠左时，越过左边界的 underflow 更容易立即进入 guard page；
- 靠右时，越过右边界的 overflow 更容易立即进入 guard page；
- 未使用页面继续保持不可访问；
- allocation 与 deallocation 元数据记录在独立映射中。

这里是“随机选择左对齐或右对齐”，并非在 slot 内任意随机偏移。一次 sampled allocation 也不能保证所有越界都被发现：错误若朝未贴 guard 的方向发生、仍落在可访问页内，或属于对象内部越界，就可能没有 fault。

### 4.2 use-after-free 与 slot 复用

释放 guarded allocation 时，`deallocateInGuardedPool()` 用 `MAP_FIXED | PROT_NONE` 的匿名映射覆盖整个 slot。后续访问会触发 `SIGSEGV`，debuggerd 可结合 `IsDeallocated` 元数据诊断 use-after-free。

slot 不会“全部用完后批量重置”。源码策略是：

- 在每个 slot 至少使用一次之前，不复用旧 slot；
- slot 释放后进入 free list；
- 所有 slot 都至少使用过一次后，从 free list 随机选择可复用项；
- 32 个 slot 全部仍处于活跃状态时，新抽样 allocation 回退到 backing allocator。

因此，UAF 的保护窗口从 `free()` 延续到该 slot 被复用。对象释放后很快被访问更容易命中；跨越很久且 allocation 压力很高的悬空指针，原 slot 可能已经承载新对象。

### 4.3 double-free 与 invalid free

`deallocate()` 会比较 pointer 与元数据中的 allocation 起始地址：

- pointer 不是 allocation 起点，诊断为 invalid/wild free；
- metadata 已标记释放，诊断为 double free。

这两类错误由 allocator 内部发现。实现会写入 `FailureType`/`FailureAddress`，再访问池内专用的不可访问地址，让既有 crash 报告路径生成统一的 GWP-ASan 诊断。它并非简单调用 `abort()` 后丢失 allocation 元数据。

### 4.4 page size 对 pool 的影响

Android 17 的 allocator state 令 `maximumAllocationSize() == PageSize`，池的主虚拟区大小为：

`PageSize × (2 + 2 × MaxSimultaneousAllocations)`

按默认 32 个 slot 计算：

| 系统 page size | 主虚拟区保留量 | sampled allocation 理论请求上限 |
|---:|---:|---:|
| 4KiB | 264KiB | 4KiB |
| 16KiB | 1056KiB | 16KiB |

这些数字描述地址空间保留，不等于 RSS。`PROT_NONE` guard page 不会因为保留就全部成为驻留物理页，metadata、free-slot 数组和活跃 slot 另行占用内存。官方文档以约 70KiB 描述当前受影响进程的 RAM 开销；项目仍应在自己的 4KiB/16KiB 设备、ABI 和 workload 上测量 RSS/PSS，而不是把 VSS 与 RAM 混为一谈。

## 5. 能检测什么，不能检测什么

| 缺陷 | 覆盖条件 | 主要盲区 |
|---|---|---|
| heap use-after-free | 目标 allocation 被抽样，访问发生在 slot 复用前 | 未抽样、复用后、未经过 Bionic allocator |
| heap overflow/underflow | 错误访问越过 allocation 相邻的受保护边界 | 朝另一侧的小越界、页内 padding、intra-object overflow |
| double-free | 被抽样 pointer 再次释放 | 未抽样 allocation |
| invalid/wild free | 错误 pointer 指向 guarded allocation 范围并可关联元数据 | 普通 heap 上的错误 free |
| leak | 不负责 | allocation 从未释放不会触发 guard fault |
| stack/global 越界 | 不负责 | GWP-ASan 只处理其抽样的 heap allocation |
| 自定义 allocator / 直接 `mmap()` | 通常不负责 | 没有经过 Bionic malloc dispatch |

GWP-ASan 能覆盖没有重新编译的预编译 `.so`，前提是该库的分配最终经过进程的 Bionic allocator。库自行维护 arena、GPU memory、共享内存或私有 allocator 时，manifest 开关不会自动获得覆盖。

“对被抽样 allocation 具有 ASan 字节级检测精度”也过于宽泛。guard page 能对触及不可访问页的访问给出高质量报告，但 ASan shadow memory 可检测的许多页内越界并不在同一覆盖范围。

## 6. `android:gwpAsanMode` 的三个值

| manifest 值 | Android 17 行为 | 命中后的进程行为 | 推荐用途 |
|---|---|---|---|
| 未设置 / `default` | Recoverable GWP-ASan，官方称约 1% app launch；AOSP 内部分母为 128 | 生成首份报告后继续运行，后续行为未定义 | 常规生产默认 |
| `always` | 每次进程启动都初始化，allocation 仍按比例抽样 | 命中后生成报告并终止进程 | 内测、定向 canary、隔离的高风险子进程 |
| `never` | 禁用 | 不产生 GWP-ASan 报告 | 明确兼容问题下的临时止损 |

Android 13 / API 33 及更早版本中，未设置/default 对普通应用关闭；Android 14 / API 34 起才改为 Recoverable 默认。`always` 会把“抽样命中后继续”改成“抽样命中后退出”，不能只把它理解为提高采样率。

应用整体启用 `always` 时，可以在 manifest 中显式声明：

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application
        android:gwpAsanMode="always"
        android:label="@string/app_name">
        ...
    </application>
</manifest>
```

这段配置会作用于没有被进程级值覆盖的应用进程。发布前应检查 merged manifest；依赖库、build type 和产品 flavor 都可能改变最终属性。

多进程应用可以在 `<processes>` 中为高风险 Native 子进程设 `always`，其他进程保持 default。组件还要通过 `android:process` 明确运行到对应进程。这样能把 fatal canary 的用户影响限制在可重启的子进程，但业务仍需处理 Binder 断连、状态恢复和任务幂等。

普通应用没有公开 API 在进程启动后切换 GWP-ASan，也没有可靠公开 API 查询本次 default launch 是否被 lottery 选中。发布平台可以按 APK 版本、人群和子进程做灰度；业务远程配置只能关闭高风险功能，不能把已经启动的 allocator 从 default 改成 always。

## 7. Recoverable 模式不是“无崩溃模式”

Android 14～Android 17 的 Recoverable 路径会：

1. 判断 fault address 是否属于当前 GWP-ASan pool；
2. 首次命中时由 debuggerd 生成 Native report，并通知 ActivityManager；
3. allocator 的 pre/post crash hook 临时恢复相关页面，使 faulting thread 能返回；
4. ART app 进程的 signal chain 把这次 fault 标记为已处理；
5. 同一进程生命周期的后续 GWP-ASan fault 仍做修复处理，但不再生成新的 debuggerd 报告。

ActivityManager 不展示普通“应用已崩溃”流程，也不因这次报告主动终止进程。`AppExitInfoTracker` 会写入 `REASON_CRASH_NATIVE`、`description=recoverable_crash` 的记录，供应用通过历史退出信息读取报告。

“Recoverable”只表示系统尝试在生成一次报告后继续。错误访问已经发生，业务状态可能被破坏，进程可能稍后以普通 SIGSEGV、业务断言或数据错误结束。稳定性平台应把它当作高优先级内存安全缺陷，并把同一进程后续异常与该报告按时间关联。

官方文档还明确规定：代表 Recoverable GWP-ASan fault 的 `SIGSEGV` 不会交给应用自定义 signal handler。Native Crash SDK 不能依赖自己的 handler 抓取或放行这类事件，也不能在 handler 里读取私有 allocator metadata。保留系统 debuggerd、sigchain 和 tombstone 路径，详见 [20.19 Android 17 信号处理架构迁移](19-android17-signal-handler-debuggerd-migration.md)。

`always` 使用基础 GWP-ASan，命中后进程终止。自定义 Native reporter 仍要遵守 signal chaining 与 async-signal-safe 约束；不要为了多收一份附件破坏 debuggerd 的 GWP-ASan cause。

## 8. 报告采集与符号化

GWP-ASan 报告应至少保留：

- `Cause: [GWP-ASan]` 的错误类型与 allocation 大小；
- fault signal、`si_code`、fault address；
- 错误访问线程栈；
- allocation thread 与栈；
- deallocation thread 与栈，若该错误存在释放动作；
- 每个 native frame 的 module、relative PC 和 ELF Build ID；
- package version、process name、ABI、Android build fingerprint；
- manifest mode、报告是否 Recoverable；
- 同一进程生命周期随后发生的 fatal crash 或异常退出。

API 31 起，应用可通过 `ActivityManager.getHistoricalProcessExitReasons()` 获取自身 `ApplicationExitInfo`，并用 `getTraceInputStream()` 读取系统保存的 tombstone 数据。Recoverable 记录虽然不代表进程已经退出，Android 仍通过同一 API 暴露。读取端要容忍 stream 为空、历史条目被回收、设备实现差异和重复扫描。

### 8.1 为什么 allocation/deallocation 栈可能缺失

Android 的 Bionic 默认把 `android_unsafe_frame_pointer_chase` 传给 GWP-ASan，以低开销记录 allocation/deallocation 栈。应用 native frame 缺少 frame pointer 时，采样当下无法可靠回溯。

官方建议 64 位库不要使用 `-fomit-frame-pointer`。arm64 通常默认保留 frame pointer；arm32 通常不保留，而且应用无法替换 libc 的构建方式，32 位报告更容易缺少 allocation/deallocation frame。是否成功不能只看 ABI，还要用最终 `.so` 和符号化结果验收。

### 8.2 聚合键怎样设计

fault address、PID、TID 和 ASLR 后绝对 PC 都不稳定，不适合作为 issue key。推荐按以下证据组合：

- GWP-ASan error type；
- access 栈中前若干个业务 frame 的 Build ID + relative PC；
- allocation 栈业务 frame；
- deallocation 栈业务 frame，若存在；
- allocation size bucket；
- ABI 与关键 native 模块版本。

不要固定认为“释放栈比访问栈更重要”。UAF 要同时看 allocation、free 与 access 的 ownership 关系；overflow 可能没有 deallocation 栈；invalid free 的错误调用点也很关键。

## 9. 从报告到修复

一份报告的处理顺序建议如下：

1. 确认 `Cause: [GWP-ASan]`、Recoverable/fatal 模式和符号文件匹配。
2. 以 Build ID 校验每个业务 `.so`，完成 access/allocation/deallocation 三组栈符号化。
3. 还原对象所有权、线程转移、异步 callback、取消和销毁顺序。
4. 检查是否存在自定义 allocator、对象池、JNI 生命周期或跨语言引用。
5. 用 HWASan 构建重放相同 workload；无法稳定触发时，围绕解析器或状态机设计 fuzz target。
6. 修复 ownership 或边界计算，并加入可重复失败的测试。
7. 在 HWASan/ASan/MTE SYNC 环境验证，再观察后续发布中相同 fingerprint 的报告趋势。

对 UAF 增加一次 `ptr = nullptr` 只会影响某个变量副本，不能修复其他悬空引用。可靠修复通常涉及所有权唯一化、生命周期同步、callback 注销、线程 join、引用计数规则或跨语言 handle 失效协议。

GWP-ASan 的概率性使本地反复运行仍可能长期不命中。官方优先建议 64 位问题使用 HWASan 重现；生产报告负责提供方向，确定性 sanitizer 和 fuzzing 负责扩大覆盖。

## 10. 灰度策略

### 10.1 保留 default 作为生产基线

Android 14～Android 17 的 default 已提供 Recoverable 抽样。没有兼容证据时，不要把全应用统一设成 `never`。生产系统应先确认：

- `ApplicationExitInfo` 报告能否进入自有采集端；
- symbols 与 Build ID 是否能对应线上版本；
- Recoverable 记录是否与普通 fatal native crash 分开；
- 自定义 signal handler 是否破坏系统链；
- 多进程 package 是否记录了正确 process name。

### 10.2 `always` 只用于能承受 fatal hit 的范围

`always` 适合：

- 内部测试版本；
- 小比例 canary APK；
- 可独立重启、状态可恢复的 Native 子进程；
- 某个高风险 `.so` 升级后的定向验证。

不要直接在主进程大范围切换 `always`，再用 Crash 率上升判断工具“有副作用”。命中后退出就是该模式的设计语义。灰度评估要把“发现了真实缺陷导致的预期终止”和“初始化开销或兼容回归”分开。

### 10.3 监控分母

原始 GWP-ASan 报告数不能跨版本直接比较。至少按以下维度记录曝光：

- package version 与 native module Build ID；
- Android 版本、ABI、4KiB/16KiB page size；
- process name 与 manifest mode；
- 活跃设备、进程启动数、Native 功能使用量；
- canary 发布比例与持续时间；
- 报告 fingerprint 首见、末见和受影响版本。

普通应用无法知道某次 default launch 是否被内部抽样选中，因此不能计算精确的“命中进程 crash rate”。更稳妥的指标是每百万活跃设备/进程启动的 GWP-ASan report、独立 fingerprint 数、已修复 fingerprint 的后续趋势，以及报告采集成功率。

“两周没有报告”也没有通用统计意义。低频路径、短会话或小人群可能没有足够 exposure；高频错误则可能很快被发现。结束灰度前应基于功能调用量和期望发现概率评估，而不是固定等待天数。

## 11. 与其他工具的分工

| 工具 | 覆盖方式 | 适合环境 | 与 GWP-ASan 的关系 |
|---|---|---|---|
| HWASan | 编译器插桩与地址 tag，覆盖 heap/stack/global | 64 位测试、预发、复现 | 用于扩大 GWP 报告对应路径的确定性覆盖 |
| ASan | shadow memory 编译器插桩 | 支持的测试构建 | 适合单测和定向复现，开销高于 GWP |
| MTE | 硬件 allocation tag 检查 | 支持硬件上的测试或生产 | 覆盖更广，但有 tag 与 granule 概率边界 |
| Scudo | hardened backing allocator | Android 常规运行 | 提供 heap hardening；GWP 抽样走独立 guarded pool |
| heapprofd | allocation sampling 与调用栈 | 内存容量分析 | 说明谁分配得多，不检测 UAF/越界 |
| malloc_debug | allocator 调试选项 | 实验室、受控设备 | 诊断范围不同；共存时检查初始化顺序 |

GWP-ASan 与 MTE 可以同时作为证据源，但 Android 17 的 `gwp_asan_wrappers.cpp` 没有“检测到 MTE 后自动降低 GWP 采样率”的逻辑，Zygote 也分别决定 GWP-ASan 与 memtag flags。不能把设备支持 MTE 等同于 GWP-ASan 已自动调参。

MTE 使用 tag mismatch，GWP-ASan 使用页权限；两者的漏检原因不同。MTE 详细边界见 [20.11 MTE memtagMode 与 Native 崩溃治理](11-mte-memtag-native-crash.md)，heap 容量工具见 [23.3 Native 内存管理](../ch23-memory-practice/03-native-memory-management.md)。

## 12. Android 17 的可验证变化

对 `android-16.0.0_r1` 与 `android-17.0.0_r1` 做文件级源码差分后，可以确认：

- `external/gwp_asan` 的 guarded allocator、metadata 和 crash diagnosis 主实现没有非测试代码变化；
- Zygote 的 GWP-ASan mode 选择与 native mallopt 初始化没有相关行为变化；
- Bionic `gwp_asan_dispatch` 增加 `reallocarray()` 包装，使 guarded pointer 能沿 GWP 的 `realloc()` 语义处理，并保留乘法溢出检查；
- 进程抽样随机数从旧 helper 改用 `__libc_arc4random_buf_or_die()`，并改用公共 `powerof2()` 检查。

所以，Recoverable 默认、约 1% launch、`2500/32`、按进程属性和定向系统属性都不能标成 Android 17 新增。Android 17 在这一区域延续了 Android 14 起的应用行为，并做 Bionic 包装与随机数路径维护。

版本演进只保留有官方或 tag diff 支撑的节点：

| Android 版本 | 已确认行为 |
|---|---|
| Android 11 / API 30 | 面向 target API 30+ 应用提供 GWP-ASan；可用 manifest opt-in |
| Android 13 / API 33 及更早 | 普通应用未设置/default 时关闭 |
| Android 14 / API 34 | 普通应用未设置/default 改为 Recoverable GWP-ASan |
| Android 15～16 | 延续 Recoverable 应用模型 |
| Android 17 / API 37 | 公共 mode 与 Recoverable 语义延续；Bionic wrapper 有上述局部维护 |

没有 commit 或源码差分支撑时，不应加入“自适应采样”“与 MTE 自动协调”“Android 17 全量升级”等叙述。

## 13. 常见误判

### “开了 GWP-ASan，所有 Native 内存都受保护”

只有被选中的进程、经 Bionic allocator 分配、又被 allocation sampler 命中的小部分 heap 对象进入 guarded pool。自定义 allocator、stack、global 和普通 heap allocation 都可能不受它检查。

### “sampled allocation 一定能抓到任意越界”

guard slot 随机靠左或靠右。触及 guard page 的方向能被捕获，仍停留在可访问页内的越界可能漏掉。

### “Recoverable 报告不算稳定性事件”

它证明线上发生了真实内存破坏。进程继续运行只减少当下退出，不能恢复已经被破坏的数据结构。

### “`always` 只是把 default 的 1% 调到 100%”

它还把命中行为从 Recoverable 改为 fatal。allocation 层仍保留抽样，32 个活跃 slot 上限也没有消失。

### “看到 1/2500 就能计算准确发现率”

进程选择、线程局部间隔、slot 可用性、错误方向、UAF 时间窗口和业务触发次数都会改变发现概率。`1/2500` 只描述当前内部 allocation sampler 目标。

### “Crash SDK 应从自定义 SIGSEGV handler 解析 GWP metadata”

Recoverable fault 不会进入应用 handler；allocator state 也是平台私有结构。正确入口是系统报告、`ApplicationExitInfo`、Build ID 符号化和后续离线聚合。

## 14. 发布检查清单

- merged manifest 中每个进程的 `gwpAsanMode` 与发布意图一致；
- `always` 只进入能承受 fatal hit 的构建或子进程；
- arm64 业务库保留 frame pointer，并用线上同构产物验证 allocation/free 栈；
- 所有 `.so` 的未剥离符号和 Build ID 可按版本长期检索；
- `ApplicationExitInfo` 的 `REASON_CRASH_NATIVE` 与 trace stream 已接入；
- Recoverable GWP-ASan 与 fatal Native crash 分开计数，但能按进程生命周期关联；
- issue key 不使用 fault address、PID 或绝对 PC；
- 自定义 signal handler 不吞信号，不破坏 debuggerd/sigchain；
- 4KiB 与 16KiB 设备分别测量启动、RSS/PSS 和 Native workload；
- 第三方库若有自定义 allocator，单独评估 GWP-ASan 覆盖；
- 报告进入 HWASan/fuzz/test 流程，并以 ownership 修复作为完成条件；
- 没有证据时不通过 `never` 隐藏报告。

## 参考资料

- [Android NDK：GWP-ASan](https://developer.android.com/ndk/guides/gwp-asan)
- [Android Developers：`ApplicationExitInfo`](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [AOSP Bionic `gwp_asan_wrappers.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/libc/bionic/gwp_asan_wrappers.cpp)
- [AOSP `GuardedPoolAllocator`（android-17.0.0_r1）](https://android.googlesource.com/platform/external/gwp_asan/+/android-17.0.0_r1/gwp_asan/guarded_pool_allocator.cpp)
- [AOSP GWP-ASan crash diagnosis（android-17.0.0_r1）](https://android.googlesource.com/platform/external/gwp_asan/+/android-17.0.0_r1/gwp_asan/crash_handler.cpp)
- [AOSP Zygote Java policy（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/com/android/internal/os/Zygote.java)
- [AOSP Zygote native initialization（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/jni/com_android_internal_os_Zygote.cpp)
- [AOSP debuggerd signal handling（android-17.0.0_r1）](https://android.googlesource.com/platform/system/core/+/android-17.0.0_r1/debuggerd/handler/debuggerd_handler.cpp)
- [AOSP ActivityManager recoverable Native crash handling（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java)
- [Android Open Source Project：Memory safety](https://source.android.com/docs/security/test/memory-safety)
- [Android NDK：HWASan](https://developer.android.com/ndk/guides/hwasan)
- [Android NDK：Arm MTE](https://developer.android.com/ndk/guides/arm-mte)
- [Android Open Source Project：Diagnose native crashes](https://source.android.com/docs/core/tests/debug/native-crash)
- [LLVM：GWP-ASan design and implementation](https://llvm.org/docs/GwpAsan.html)
