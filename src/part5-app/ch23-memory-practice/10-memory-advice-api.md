---
title: "Memory Advice API 与游戏内存压力治理"
chapter: "23.10"
status: ready-for-review
drafted_date: "2026-05-21"
applicable_versions: "AGDK Memory Advice Library 2022.0.0-2022.3.0 / Jetpack games-memory-advice 1.x；官方文档 2026-02 起标记 beta deprecated"
last_verified: "2026-05-21"
last_verified_against: "Android Developers Memory Advice docs 2026-02-26; AOSP frameworks/opt/gamesdk master f455ab1"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/games/sdk/memory-advice/overview"
  - type: official
    path: "https://developer.android.com/games/sdk/memory-advice/start"
  - type: official
    path: "https://developer.android.com/games/optimize/memory-allocation"
  - type: official
    path: "https://developer.android.com/reference/games/memory-advice/namespacememory/advice"
  - type: official
    path: "https://developer.android.com/games/optimize/vitals/lmk"
  - type: aosp
    path: "frameworks/opt/gamesdk/include/memory_advice/memory_advice.h"
  - type: aosp
    path: "frameworks/opt/gamesdk/games-memory-advice/core/memory_advice_impl.cpp"
  - type: aosp
    path: "frameworks/opt/gamesdk/games-memory-advice/core/metrics_provider.cpp"
  - type: aosp
    path: "frameworks/opt/gamesdk/games-memory-advice/core/state_watcher.cpp"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 虚拟内存优化（上）：线程+多进程优化.md"
tags: [memory-advice, agdk, game-memory, low-memory, native-memory]
related_chapters: ["8.9", "10.1", "10.4", "23.3", "23.7", "23.9", "26.9"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-21"
gap_source: "官方文档/AOSP结构/每日信息"
---

# 23.10 Memory Advice API 与游戏内存压力治理

## 先确定结论：新项目不要新增 Memory Advice 依赖

Android Developers 已在 2026 年 2 月把 Memory Advice API 标记为 deprecated，并明确表示 beta 已结束。新项目应采用引擎内存预算、仍有效的生命周期回调、系统诊断工具、`ApplicationExitInfo`与 Android Vitals 等能力，不应再把 Memory Advice 加入核心依赖。

这套 API 仍值得研究，原因有两个：

- 历史游戏可能已经接入，需要知道状态值、线程和预测模型的边界，避免误用；
- 它展示了一种可复用的工程结构：压力信号只负责提出降级请求，资源策略负责选择动作，系统指标负责验证效果。

平台行为以 Android 17（API 37）和 AOSP `android-17.0.0_r1` 为锚点，内核压力语义以 `android17-6.18-2026-06_r6` 为锚点。Memory Advice 属于独立的 Games SDK 源码仓库，该仓库没有 `android-17.0.0_r1` 标签，因此源码机制引用固定 commit `044fd03c4a7d3b75aeb6ca2bd7fb6155d2cdb787`，不把可变的 `master` 当成 Android 17 平台源码。

## Memory Advice 解决的历史问题

游戏的主要内存消费者通常跨越多个分配体系：Java/Kotlin 对象、native arena、纹理、mesh、音频解码缓冲、Vulkan/OpenGL 资源、DMA-BUF、线程栈和引擎缓存。Java Heap 水位无法代表整个进程。

Memory Advice 是一个 native 库，不是 framework 服务。官方把它定义为实验性 API：库采集设备与进程指标，再结合设备测试和机器学习数据估算内存安全余量。官方说明估算范围考虑 `malloc` 分配和 OpenGL ES/Vulkan 图形分配，目标是让游戏在进入危险区时减少资源。

三种状态表达的是建议，不是系统承诺：

| 状态 | 可采用的工程解释 | 不可推导的结论 |
| --- | --- | --- |
| `MEMORYADVICE_STATE_OK` | 当前模型没有产生告警 | 下一次大分配一定成功；LMKD 或 Android 17 MemoryLimiter 不会终止进程 |
| `MEMORYADVICE_STATE_APPROACHING_LIMIT` | 应停止非必要增长并准备释放可重建资源 | 已经发生 OOM；某个具体模块存在泄漏 |
| `MEMORYADVICE_STATE_CRITICAL` | 应请求资源系统降低峰值和常驻量 | 系统一定会在固定时间内终止进程 |
| `MEMORYADVICE_STATE_UNKNOWN` 或负错误码 | 本次状态不可用，应记录错误并切换到其他信号 | 内存安全 |

业务模块不应直接读取这些值。更稳妥的接口是 `Normal`、`Conservative`、`Emergency` 之类的引擎资源档位，由一个进程级策略组件把信号映射到档位。

## 发行形态与适用边界

Memory Advice 曾通过三种渠道分发：

- Android Games Jetpack 的 `androidx.games:games-memory-advice`；
- AGDK 二进制发行包；
- AOSP 的 `frameworks/opt/gamesdk` 独立仓库源码。

官方 Android Studio 指南使用 `games-memory-advice:1.0.0-beta01`、Prefab 和 `games-memory-advice::memory_advice` CMake target。这些内容是历史维护参考，不是推荐新接入的版本清单。

运行环境也有限制：

- 面向以 C/C++ 为主的 native 应用；
- 只支持物理设备，不支持模拟器；
- 官方总览记录的最低系统要求为 Android 4.4（API 19），具体二进制还要遵守其 release notes、NDK 与 STL 组合；
- Unity 官方插件页面只列出 Unity 2019—2022 与 NDK r19/r21/r23 的已测组合。

这些旧组合不能证明现代 Unity、NDK 或 Android 17 工程仍受支持。历史项目应锁定现有插件、NDK、STL 和构建工具版本，先建立可复现构建，再评估迁移；源码仍留在 AOSP 仓库也不表示产品支持仍在继续。

## 从源码理解状态与“可用内存”

固定 commit 的 `memory_advice.h` 定义了四个状态，以及下列主要 C API：

- `MemoryAdvice_init()`：在其他调用之前初始化；
- `MemoryAdvice_getMemoryState()`：同步计算状态；
- `MemoryAdvice_getAvailableMemory()`：返回模型估算的安全可分配字节数；
- `MemoryAdvice_getPercentageAvailableMemory()`：返回估算百分比；
- `MemoryAdvice_getTotalMemory()`：返回设备总内存；
- `MemoryAdvice_registerWatcher()` / `MemoryAdvice_unregisterWatcher()`：注册或移除 watcher。

`GetAvailableMemory()`不是 `/proc/meminfo` 的 `MemAvailable`。源码计算方式是：

> `predictedAvailable × GetTotalMemory()`

`predictedAvailable`来自模型预测，`GetTotalMemory()`来自初始化 baseline 中的 `ActivityManager.MemoryInfo.totalMem`。`metrics_provider.cpp`还读取 `/proc/meminfo`、当前进程 `/proc/<pid>/status`、`oom_score`、`ActivityManager.getMemoryClass()`、`getLargeMemoryClass()`和 `isLowRamDevice()` 等指标。

`GetMemoryState()`会读取 advice JSON：存在 red warning 时返回 `CRITICAL`，存在其他 warning 时返回 `APPROACHING_LIMIT`，没有 warning 时返回 `OK`。这说明状态是模型与规则的结果，并非内核或图形驱动直接报告的剩余容量。官方所说的图形内存“纳入估算”，也不能理解为库逐项枚举了每个 Vulkan allocation。

## watcher 的线程与生命周期

官方文档给出三个必须保留的行为：

- watcher 在库创建的独立线程中执行回调；
- 每次计算状态通常消耗 1—3 ms，频率要根据设备与游戏负载决定；
- 状态为 `OK` 时不调用 watcher，只有非 `OK` 状态才回调。

AOSP `state_watcher.cpp`进一步说明，内部线程按 `intervalMillis`休眠，然后调用 `GetMemoryState()`。这带来几个工程后果：

- 回调不能直接销毁纹理、mesh、scene graph 或其他要求引擎线程亲和性的对象；
- watcher 不会通知状态恢复为 `OK`，恢复策略必须在引擎线程主动复查；
- 过短间隔会增加计算开销，过长间隔会延迟建议，没有一个适用于所有设备的固定值；
- `MemoryAdvice_unregisterWatcher(callback)`按函数指针移除所有同 callback 的 watcher，不是按注册句柄精确移除；
- 注销与回调可能存在并发窗口，`user_data` 的生命周期必须长于可能执行中的回调。

下面的适配层只把最高压力等级写入原子变量。资源线程随后读取并执行策略，watcher 线程不触碰引擎对象。

```cpp
#include <atomic>
#include <cstdint>
#include <memory_advice/memory_advice.h>

namespace {
std::atomic<int32_t> g_pending_state{MEMORYADVICE_STATE_OK};
std::atomic<bool> g_watcher_registered{false};

void OnMemoryAdvice(MemoryAdvice_MemoryState state, void*) {
  int32_t expected = g_pending_state.load(std::memory_order_relaxed);
  const int32_t incoming = static_cast<int32_t>(state);
  while (expected < incoming &&
         !g_pending_state.compare_exchange_weak(
             expected,
             incoming,
             std::memory_order_release,
             std::memory_order_relaxed)) {
  }
}
}  // namespace

bool StartMemoryAdviceWatcher(uint64_t interval_millis) {
  if (interval_millis == 0 || g_watcher_registered.exchange(true)) {
    return false;
  }

  const auto error = MemoryAdvice_registerWatcher(
      interval_millis,
      OnMemoryAdvice,
      nullptr);
  if (error != MEMORYADVICE_ERROR_OK) {
    g_watcher_registered.store(false);
    return false;
  }
  return true;
}

MemoryAdvice_MemoryState ConsumeMemoryAdviceState() {
  return static_cast<MemoryAdvice_MemoryState>(
      g_pending_state.exchange(
          MEMORYADVICE_STATE_OK,
          std::memory_order_acq_rel));
}

void StopMemoryAdviceWatcher() {
  if (!g_watcher_registered.exchange(false)) {
    return;
  }
  MemoryAdvice_unregisterWatcher(OnMemoryAdvice);
}
```

调用这段代码前仍须检查 `MemoryAdvice_init()`返回值。引擎资源线程定期调用 `ConsumeMemoryAdviceState()`，再把压力请求交给策略组件。示例使用进程期全局状态，避免短生命周期对象成为 `user_data`；发布代码还要记录注册、注销与初始化错误码。

`CRITICAL`被消费后不能立即恢复高资源档位。watcher 不报告 `OK`，策略组件应通过低频 polling 确认恢复，并使用由实测确定的滞回条件，防止纹理反复卸载和重载。

## 从压力状态到资源动作

降级动作必须满足三个条件：资源可重建、释放线程正确、释放成本可控。

| 资源类别 | `APPROACHING_LIMIT` 请求 | `CRITICAL` 请求 | 验证重点 |
| --- | --- | --- | --- |
| 纹理 | 停止更高 mip 或更高分辨率的预取；限制新缓存增长 | 卸载不在当前视野且可重建的高分辨率资源；后续加载降低质量 | Graphics、DMA-BUF、帧时间、重载次数 |
| mesh/动画 | 缩短预加载距离；阻止池继续扩容 | 卸载远距离高 LOD、非当前角色动画数据 | native/graphics 内存、切场景卡顿 |
| 音频 | 减少非即时音效预解码；限制缓存增长 | 释放可从包体重建的解码缓存 | native 内存、音频缺失与解码尖峰 |
| 场景流式加载 | 暂停推测性加载 | 取消非当前路径的加载任务并回收 staging buffer | 峰值、I/O、任务取消正确性 |
| 对象池与 arena | 冻结容量增长 | 按空闲块和重建成本缩减；保留活跃对象 | allocator 保留量、碎片、下一次扩容 |
| shader/pipeline 数据 | 限制新建与预热范围 | 只清理引擎已证明可重建、低命中的缓存 | 编译卡顿、驱动内存、缓存命中 |

“清理 pipeline cache”不能作为通用动作。磁盘序列化缓存、CPU 侧缓存和驱动对象的生命周期不同；盲目清理可能没有可测内存收益，却增加 shader 编译卡顿。每一种动作都要对应引擎的所有权模型和前后指标。

GPU 对象还受命令队列与 fence 生命周期约束。资源已经从业务容器移除，不代表驱动可以立即释放底层内存。应使用引擎现有的延迟销毁队列，并把“发出释放请求”和“系统指标下降”记录为两个检查点。

## Android 17 上应采用的替代结构

Memory Advice deprecated 后，没有一个新 API 可以原样替代其连续预测状态。Android 官方当前建议组合使用：

- 引擎自有的内存预算与资产计数；
- `TRIM_MEMORY_UI_HIDDEN`、`TRIM_MEMORY_BACKGROUND`等仍有效的生命周期机会，释放进入后台后可重建的资源；
- `dumpsys meminfo`、Perfetto、Android Studio、Unity Memory Profiler 或 Unreal Memory Insights 做定位；
- `ApplicationExitInfo`识别上一次运行的低内存或 Android 17 MemoryLimiter 退出；
- Android Vitals 的 user-perceived LMK rate 观察用户影响。

这里不能把 `onTrimMemory()`当成 native 内存压力传感器。Android 官方说明，大多数旧 trim level 已废弃，仍保留的 level 主要表达 UI 隐藏或后台状态。它们适合触发后台资源清理，无法提供 Memory Advice 那样的预测状态。

一个可替换的策略组件可以保留相同结构：

| 层 | 输入/输出 | 约束 |
| --- | --- | --- |
| 信号层 | 引擎占用、PSS/RSS 采样、生命周期、历史退出、可选旧 Memory Advice | 每个信号标明来源、单位、延迟和失败状态 |
| 策略层 | 根据设备、场景与预算输出资源档位 | 不直接操作纹理或对象池 |
| 执行层 | 在正确线程分批释放、降规格或暂停加载 | 动作可取消、可恢复、可记录 |
| 验证层 | 峰值、回落、帧时间、LMK/MemoryLimiter 退出 | 同设备与同场景比较 |

这样可以移除旧库，而不修改每个资源模块。

## 与 LMKD、ApplicationExitInfo、Vitals 的分工

| 阶段 | 信号或工具 | 能回答的问题 | 不能回答的问题 |
| --- | --- | --- | --- |
| 运行时 | Memory Advice（历史项目）、引擎预算、有效 trim 回调 | 是否请求资源降级 | 系统会在何时、以何种原因终止进程 |
| 系统压力 | LMKD、PSI 与回收机制 | 系统是否处于资源竞争 | 哪个业务资产应释放 |
| 下次启动 | `ApplicationExitInfo` | 最近进程退出原因与系统最近内存采样 | 每个资源模块的完整时间序列 |
| 线上聚合 | Android Vitals user-perceived LMK rate | 版本、设备和用户群的 LMK 影响 | 单次会话的分配栈 |
| 根因定位 | meminfo、Perfetto、heapprofd、引擎 profiler | 内存类别、趋势与调用栈 | 自动选择无副作用的业务降级 |

LMKD 基于系统压力和进程优先级选择目标。内核 PSI 量化 CPU、memory、I/O 争用导致的 stall；它是系统守护进程的重要输入，不是 Memory Advice watcher 的回调来源。应用不能依靠 Memory Advice 阻止 LMKD。

读取低内存退出时，还要先检查 `ActivityManager.isLowMemoryKillReportSupported()`；设备不支持报告时，缺少 `REASON_LOW_MEMORY`记录不等于没有 LMK。Android 17 MemoryLimiter 则使用 23.9 所述的 `REASON_OTHER + MemoryLimiter:AnonSwap`。

## 与 Android 17 App Memory Limits 的关系

Android 17 App Memory Limits 根据设备总 RAM 和 vendor 配置限制部分设备上的应用进程。Memory Advice 的预测模型并不知道某台 Android 17 设备当前的 MemoryLimiter 配置，也没有 API 保证 `APPROACHING_LIMIT`或 `CRITICAL`一定先于系统限制命中。

两者的关系只能表述为：

- Memory Advice 可作为历史项目中的一项提前降级输入；
- Android 17 MemoryLimiter 是系统保护机制，命中后可通过 `ApplicationExitInfo`归因，并可触发 anomaly heap dump；
- 资源预算与系统验证决定降级是否有效，不能用 Memory Advice 状态代替 MemoryLimiter 证据。

对于新项目，连续运行时决策应来自引擎预算和经过校准的进程指标。`TRIGGER_TYPE_ANOMALY`产生的是命中异常时的诊断 artifact，不是连续压力回调，不能用来重建 Memory Advice 状态机。

## Perfetto 与 meminfo 的验证方法

压力状态只能触发实验，系统指标才用于确认资源动作是否有效。

| 证据 | 适合回答的问题 | 边界 |
| --- | --- | --- |
| `dumpsys meminfo <package>` | Java、Native、Graphics、Private Dirty、总体 PSS 的检查点差异 | 分类受版本和实现影响，单次快照不能说明趋势 |
| Perfetto memory counters / 长 trace | RSS 峰值、回收与场景时间关系 | 需要固定设备、trace 配置和动作脚本 |
| heapprofd | `malloc/free` 等 native 分配的存活字节与调用栈 | 不覆盖所有图形、映射和自定义 allocator |
| `/proc/<pid>/smaps_rollup` / `smaps` | 匿名页、文件映射和 VMA 证据 | 量产 user 设备上的 adb shell 通常无权限 |
| GPU、DMA-BUF 与引擎工具 | 纹理、缓冲与渲染资源趋势 | 可见性取决于设备、驱动、权限与工具 |
| Unity/Unreal profiler | 引擎资源分类、快照和标签 | 与系统 PSS/RSS 口径不同，需要对齐时间点 |

RSS 采集成本通常低于 PSS，更适合观察细粒度峰值；PSS 适合比较共享页按比例分摊后的进程规模。二者都不能直接替代资产计数。

一次回归至少包含：

- 相同设备、构建、关卡、输入与动作序列；
- 动作前、资源峰值、降级请求、降级完成、场景退出和冷却后的检查点；
- 状态或策略输入、每批资源动作、Java/Native/Graphics/PSS/RSS 与帧时间；
- 下一次启动读取到的退出原因，以及线上 LMK/MemoryLimiter 聚合。

若收到 `CRITICAL`后内存没有下降，应检查动作是否只修改了逻辑档位、资源是否仍被引用、GPU 是否仍等待 fence、allocator 是否保留空闲页。若内存下降而帧时间恶化，应检查销毁批次、重新加载和 shader 编译。若状态长期为 `OK`而 LMK 上升，应停止依赖该预测，回到设备分组和系统证据。

## Unity、Unreal 与自研引擎

历史 Unity 项目若已使用官方插件，应保留它列出的 Unity/NDK 组合，并用 Unity Memory Profiler 与系统指标验证。迁移到现代 Unity 或 NDK 时，deprecated 插件应视为待移除依赖，不能只通过编译成功判断兼容。

官方没有提供与 Unity 插件同级的通用 Unreal Memory Advice 接入说明。Unreal 项目更适合用 Memory Insights、Low Level Memory tags 和平台层信号建立自己的策略组件。自研引擎也应在 native 平台层封装信号，不把 C API 传播到纹理、音频和场景模块。

无论引擎类型，资源动作都要用引擎的线程、引用和延迟销毁机制。直接从 watcher 线程调用资源释放 API，是最需要避免的接入错误。

## 线上灰度

迁移或调整降级策略时，按三个阶段验证：

1. **只记录**：保存信号来源、场景、设备、资源档位和系统内存，不改变资源。
2. **低风险动作**：停止推测性预加载、限制缓存增长、清理明确可重建的空闲资源。
3. **高影响动作**：降低后续纹理质量、缩短流式加载距离、卸载非当前场景资源。

每个动作都要记录请求时间、执行线程、资源数量或字节、完成时间、系统指标变化和用户体验指标。灰度比例、观察时长与预算线来自项目基线，不在通用章节中给固定数字。

回滚应能单独禁用某个信号源或某类动作，并让其余诊断组件继续工作。若旧 Memory Advice 与自研预算给出不同结果，日志必须保留两者原始值，策略层只输出一份最终决定。

## 小结

Memory Advice API 已经 deprecated。历史项目可以继续把它当成一个带预测成分的运行时信号，但要记住：

- `GetAvailableMemory()`是模型估算，不是系统剩余内存；
- watcher 在库线程执行，且不会回调恢复到 `OK`；
- 资源释放必须切换到引擎规定的线程，并通过系统指标验证；
- LMKD、Android 17 MemoryLimiter、`ApplicationExitInfo`和 Android Vitals 分别处理系统处置、退出归因与线上聚合；
- 新项目应使用可替换信号层、引擎预算、资源策略和验证工具，不再新增该库依赖。

这套分层比任何单一压力 API 更重要：信号可以变化，资源所有权、预算和复测证据必须长期稳定。

## 参考资料

- [Android Developers：Memory Advice API overview](https://developer.android.com/games/sdk/memory-advice/overview)
- [Android Developers：Get started with the Memory Advice API](https://developer.android.com/games/sdk/memory-advice/start)
- [Android Developers：Manage memory effectively in games](https://developer.android.com/games/optimize/memory-allocation)
- [Android Developers：Memory Advice C++ reference](https://developer.android.com/reference/games/memory-advice/namespacememory/advice)
- [Android Developers：Low memory killers and Android Vitals](https://developer.android.com/games/optimize/vitals/lmk)
- [Android Developers：Memory Advice for Unity](https://developer.android.com/games/engines/unity/memory-advice)
- [Android Developers：Android 17 App memory limits](https://developer.android.com/about/versions/17/behavior-changes-all#app-memory-limits)
- [Perfetto：Native heap profiler](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [Games SDK commit `044fd03c...`：`memory_advice.h`](https://android.googlesource.com/platform/frameworks/opt/gamesdk/+/044fd03c4a7d3b75aeb6ca2bd7fb6155d2cdb787/include/memory_advice/memory_advice.h)
- [Games SDK commit `044fd03c...`：`memory_advice_impl.cpp`](https://android.googlesource.com/platform/frameworks/opt/gamesdk/+/044fd03c4a7d3b75aeb6ca2bd7fb6155d2cdb787/games-memory-advice/core/memory_advice_impl.cpp)
- [Games SDK commit `044fd03c...`：`metrics_provider.cpp`](https://android.googlesource.com/platform/frameworks/opt/gamesdk/+/044fd03c4a7d3b75aeb6ca2bd7fb6155d2cdb787/games-memory-advice/core/metrics_provider.cpp)
- [Games SDK commit `044fd03c...`：`state_watcher.cpp`](https://android.googlesource.com/platform/frameworks/opt/gamesdk/+/044fd03c4a7d3b75aeb6ca2bd7fb6155d2cdb787/games-memory-advice/core/state_watcher.cpp)
- [AOSP `android-17.0.0_r1`：`MemoryLimiter.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryLimiter.java)
- [Android Common Kernel `android17-6.18-2026-06_r6`：PSI](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/accounting/psi.rst)
