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

<!-- outline-start -->
## 要点

### 🔹 Memory Advice API 解决的问题
说明 Memory Advice API 面向游戏和图形重负载应用的定位：估算内存压力、给出状态通知、帮助应用在被系统杀进程前主动降级内存占用。

### 🔹 接入形态与版本边界
梳理 Jetpack 发行包、Android Game Development Kit、Unity 接入路径、原生 API 与 C/C++ 引擎的关系，明确它是库能力，不等同于新的 framework 系统服务。

### 🔹 MemoryState、可用内存与 watcher 回调
整理 `GetMemoryState()`、`GetAvailableMemory()`、`GetPercentageAvailableMemory()`、`RegisterWatcher()` 等接口的使用边界，以及回调线程、采样间隔和生命周期管理风险。

### 🔹 与 LMKD / ApplicationExitInfo / Android Vitals 的关系
解释 Memory Advice API 适合做运行时降级信号，LMKD 和 `ApplicationExitInfo` 负责事后归因，Android Vitals 负责线上质量聚合；三者不能互相替代。

### 🔹 游戏资产与图形内存降级策略
围绕纹理、mesh、音频缓存、关卡流式加载、对象池和 shader / pipeline cache（着色器与管线缓存），整理不同压力等级下可执行的释放和降级动作。

### 🔹 Perfetto 与 meminfo 验证方法
给出 `dumpsys meminfo`、Perfetto memory counter、heap profile、DMA-BUF / GPU memory 轨道和线上指标的复核路径，避免只看 API 状态就下结论。

## 扩展

### 🔸 Unity / Unreal 接入差异
记录 Unity 示例、Unreal 原生插件和自研引擎接入方式的差异，后续加工时补充官方示例和工程边界。

### 🔸 与 Android 17 App Memory Limits 的关系
对照 23.9 节的 Android 17 App Memory Limits，说明 Memory Advice API 在新系统内存限制下能提前暴露哪些信号。

### 🔸 线上灰度策略
补充把内存压力信号接入 A/B Test、功能开关和资源质量档位的策略，避免一次性对所有用户启用激进降级。

<!-- outline-end -->

## 先确认版本口径：Memory Advice API beta 已废弃

Memory Advice API 的官方文档在 2026-02 之后已经标注：beta 阶段结束，库已废弃，不再推荐使用。新项目不应把它当作 2026 年的首选内存治理入口。[已验证: 官方文档, developer.android.com/games/sdk/memory-advice/overview]

这不代表这个 API 没有阅读价值。它仍然适合两类场景：历史游戏项目已经接入，需要判断它给出的状态是否可信；自研引擎需要参考一套“运行时内存压力信号 → 资产降级 → 事后归因”的工程组织方式。本文按这个口径展开。

[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md] 只用于组织内存指标口径，[结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]、[结构参考: Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md] 和 [结构参考: Clippings/Android 性能优化 - 虚拟内存优化（上）：线程+多进程优化.md] 只用于整理“指标 → 归因 → 释放动作”的顺序。正文不复用参考书原文与代码。

## Memory Advice API 解决的问题

游戏内存压力和普通页面应用不同。普通 App 主要盯 Java Heap、Bitmap、Native Heap、PSS 增长；游戏还要把纹理、mesh、音频包、关卡流式加载、OpenGL ES / Vulkan 图形分配、DMA-BUF 和引擎对象池放在一起看。系统最终只关心进程在内存压力下是否该被回收，游戏关心的是在被杀之前能否主动降一档画质或释放一批资源。

Memory Advice API 的设计目标就是给游戏一个运行时信号：当前还能不能继续安全分配内存，是否已经接近限制，是否应尽快释放资源。官方文档把它描述为 experimental native API，估算范围包含 `malloc` 申请的 Native Heap，以及 OpenGL ES / Vulkan 图形 API 分配的图形内存，定位明显偏游戏和图形重负载应用。[已验证: 官方文档, developer.android.com/games/sdk/memory-advice/overview]

它给出的不是系统承诺，也不是进程保活能力。更准确的读法是：

| API 输出 | 工程含义 | 适合触发的动作 | 不适合承担的职责 |
| --- | --- | --- | --- |
| `MEMORYADVICE_STATE_OK` | 当前估算值仍在安全范围内 | 维持现有资源档位，继续记录基线 | 不能承诺下一次大分配一定成功 |
| `MEMORYADVICE_STATE_APPROACHING_LIMIT` | 继续增长可能逼近安全边界 | 暂停预加载，减少新资源分配，清理可重建缓存 | 不能当作 OOM 已发生 |
| `MEMORYADVICE_STATE_CRITICAL` | 需要尽快降低进程内存占用 | 释放高成本纹理、缩小池化对象、降低资源质量档位 | 不能替代 LMKD、`ApplicationExitInfo` 和线上 LMK 指标 |

这种接口适合挂在引擎资源管理器上，而不是散落在业务层。业务层只应看到“资源质量档位”“预加载开关”“关卡缓存预算”这类稳定抽象，避免每个模块都直接读取 API 状态。

## 接入形态与版本边界

Memory Advice API 是 AGDK / Jetpack games-memory-advice 库能力，不是 Android framework 新增系统服务。AOSP `frameworks/opt/gamesdk` 里有独立的 `games-memory-advice` 模块，`build.gradle` 使用 `com.android.library`，`minSdkVersion 21`、`targetSdkVersion 35`，通过 Prefab 发布 `memory_advice` / `memory_advice_static` 头文件与库。[已验证: AOSP master, frameworks/opt/gamesdk/games-memory-advice/build.gradle]

官方接入路径分三类：

| 接入对象 | 入口 | 工程边界 |
| --- | --- | --- |
| Android Studio + C/C++ 游戏 | Jetpack Android Games libraries，CMake 链接 `games-memory-advice::memory_advice` | 适合 NDK 引擎；文档示例要求在 Java/Kotlin 侧加载 `libmemory_advice.so`，native 侧包含 `memory_advice/memory_advice.h` |
| Unity 游戏 | Unity package 插件 | 官方文档列出 Unity 2019/2020 + NDK r19、Unity 2021 + NDK r21、Unity 2022 + NDK r23 的已测组合；其他组合要按工程实际验证 |
| 自研或 Unreal 引擎 | 原生 C API / C++ namespace API | 需要自己把状态映射到资源系统；Unreal 没有官方同等层级的通用插件说明，通常走 native module 封装 |

[已验证: 官方文档, developer.android.com/games/sdk/memory-advice/start] [已验证: 官方文档, developer.android.com/games/engines/unity/memory-advice]

接入前要先做一次取舍：历史项目可继续维护；新项目优先使用 `onTrimMemory()`、引擎内存预算、Android Vitals LMK、`ApplicationExitInfo`、Perfetto / Android Studio Profiler 组成的组合方案。官方已经把 Memory Advice API 标为 deprecated 后，把它作为新增依赖会引入维护风险。


<!-- AIW-源码调研-2026-06-05 -->
### 源码层验证：Memory Advice 库在 AOSP 公开分支的实际状态

| 维度 | Android Developers 文档 | AOSP main / android-16.0.0_r3 源码 |
|---|---|---|
| 库可用性 | 顶部 banner "The Memory Advice API beta is now deprecated, and no longer recommended for use" | 完整保留 v2.2.0，未删除 .cpp/.h，未在源码内加 `@Deprecated` 标注 |
| `versionName` / `versionCode` | – | `1.1` / `1`（build.gradle） |
| `targetSdkVersion` / `compileSdk` | – | `35` / `31`（build.gradle） |
| `namespace` | – | `com.google.androidgamesdk.memory_advice`（build.gradle） |
| 状态机实现 | – | `MemoryAdviceImpl::GetMemoryState()` 走 `available.tflite` + `available_features.json` 预测 `predictedAvailable`；按 `heuristics.formulas` 输出 `MEMORYADVICE_STATE_OK/APPROACHING_LIMIT/CRITICAL` |

AOSP 关键源码（main，2026-06-05 抓取）：

```cpp
// platform/frameworks/opt/gamesdk/include/memory_advice/memory_advice.h
typedef enum MemoryAdvice_MemoryState : int32_t {
  MEMORYADVICE_STATE_UNKNOWN = 0,
  MEMORYADVICE_STATE_OK = 1,
  MEMORYADVICE_STATE_APPROACHING_LIMIT = 2,
  MEMORYADVICE_STATE_CRITICAL = 3,
} MemoryAdvice_MemoryState;
```

```cpp
// platform/frameworks/opt/gamesdk/games-memory-advice/core/memory_advice_impl.cpp
MemoryAdvice_MemoryState MemoryAdviceImpl::GetMemoryState() {
    Json::object advice = GetAdvice();
    if (advice.find("warnings") != advice.end()) {
        Json::array warnings = advice["warnings"].array_items();
        for (auto& it : warnings) {
            if (it.object_items().at("level").string_value() == "red") {
                return MEMORYADVICE_STATE_CRITICAL;
            }
        }
        return MEMORYADVICE_STATE_APPROACHING_LIMIT;
    }
    return MEMORYADVICE_STATE_OK;
}
```

工程含义：源码 v2.2.0 与 `targetSdkVersion 35` 表明 AOSP 内部仍在维护，但文档已挂 deprecation banner。新项目接入建议遵循 23.10 节"接入前要先做一次取舍"——把 Memory Advice 包成可替换的"信号源"层，未来切到 `TRIGGER_TYPE_OOM` / `TRIGGER_TYPE_ANOMALY` 时业务侧不用改。`TRIGGER_TYPE_OOM` 与 Memory Advice 的关键差异：前者是 Java OOM 异常的当场 heap dump（一次性事件），后者是 TFLite 预测的连续状态信号。两者在产物类型（heap dump vs JSON 状态）上完全不同，**不能视为等价替代**。
<!-- /AIW-源码调研-2026-06-05 -->

## MemoryState、可用内存与 watcher 回调

AOSP 头文件 `include/memory_advice/memory_advice.h` 定义了 C API 的状态和接口。状态枚举包括 `UNKNOWN`、`OK`、`APPROACHING_LIMIT`、`CRITICAL`；查询接口包括 `MemoryAdvice_getMemoryState()`、`MemoryAdvice_getAvailableMemory()`、`MemoryAdvice_getPercentageAvailableMemory()`、`MemoryAdvice_getTotalMemory()`；watcher 通过 `MemoryAdvice_registerWatcher(intervalMillis, callback, user_data)` 注册。[已验证: AOSP master, frameworks/opt/gamesdk/include/memory_advice/memory_advice.h]

这段示例只展示 watcher 应该触发什么等级的动作，主要看状态到资源动作的映射，不要照搬为发布代码。

```cpp
#include <memory_advice/memory_advice.h>

static void OnMemoryAdvice(MemoryAdvice_MemoryState state, void* user_data) {
  auto* budget = static_cast<GameMemoryBudget*>(user_data);

  switch (state) {
    case MEMORYADVICE_STATE_APPROACHING_LIMIT:
      budget->StopLevelPreload();
      budget->ShrinkRebuildableCaches();
      break;
    case MEMORYADVICE_STATE_CRITICAL:
      budget->DropTextureQualityOneStep();
      budget->ReleaseUnusedSceneAssets();
      budget->FlushPipelineCacheIfSafe();
      break;
    default:
      break;
  }
}

void RegisterMemoryAdvice(GameMemoryBudget* budget) {
  constexpr uint64_t kIntervalMs = 2000;
  MemoryAdvice_registerWatcher(kIntervalMs, OnMemoryAdvice, budget);
}
```

发布代码还要补三件事：初始化失败时降级为自研采样；引擎销毁或场景切换时调用 `MemoryAdvice_unregisterWatcher()`；所有释放动作都要保证在引擎线程模型下安全执行。AOSP `state_watcher.cpp` 显示 watcher 内部会创建线程，按 `intervalMillis` sleep 后调用 `GetMemoryState()`，只有状态不为 `OK` 时才回调业务函数。[已验证: AOSP master, frameworks/opt/gamesdk/games-memory-advice/core/state_watcher.cpp]

`GetAvailableMemory()` 也不能按“系统剩余内存”理解。AOSP `memory_advice_impl.cpp` 的实现是读取预测出的 `predictedAvailable`，再乘以 `GetTotalMemory()` 得到估算字节数；`GetTotalMemory()` 来自 baseline 中的 `totalMem`。`metrics_provider.cpp` 会从 `/proc/meminfo`、`/proc/<pid>/status`、`oom_score`、`ActivityManager.MemoryClass`、`LargeMemoryClass`、`isLowRamDevice()` 等来源取指标，再交给预测模型。[已验证: AOSP master, frameworks/opt/gamesdk/games-memory-advice/core/memory_advice_impl.cpp] [已验证: AOSP master, frameworks/opt/gamesdk/games-memory-advice/core/metrics_provider.cpp]

这带来三个边界：

- 采样有成本。官方文档写明每次生成内存状态通常需要 1-3ms，频率由设备和游戏负载决定。2s 轮询只是示例，不应在每帧或高频资源分配点调用。
- 状态有预测成分。它适合控制资源预算，不适合写成精确容量保证。大块 Vulkan allocation、驱动内部图形内存、厂商 allocator 行为都可能让实际结果偏离估算。
- 回调线程不能直接改渲染对象。纹理、pipeline cache、scene graph 的释放应投递到引擎资源线程或渲染线程，不能在 watcher 回调里直接销毁 GPU 对象。

## 与 LMKD、ApplicationExitInfo、Android Vitals 的分工

Memory Advice API、LMKD、`ApplicationExitInfo` 和 Android Vitals 解决的是同一类问题的不同阶段。

| 阶段 | 工具 / 信号 | 能回答的问题 | 不能回答的问题 |
| --- | --- | --- | --- |
| 运行中 | Memory Advice API / `onTrimMemory()` / 引擎预算 | 当前是否应主动降低资源占用 | 进程被杀的最终原因 |
| 系统回收 | LMKD / PSI / 内核回收信号 | 系统是否因内存压力回收进程 | 应用内部哪类资产增长失控 |
| 下次启动 | `ApplicationExitInfo` | 上一次退出是否可能是低内存、ANR、native crash 等 | 退出前每个资源模块的占用曲线 |
| 线上聚合 | Android Vitals LMK rate / Play Developer Reporting API | 用户感知 LMK 是否在版本、机型、地区上升 | 单个会话里哪一次 allocation 触发临界点 |
| 根因分析 | `dumpsys meminfo`、Perfetto、heapprofd、Android Studio Profiler | Java / Native / Graphics / DMA-BUF / 线程栈等占用来源 | 自动给出业务释放方案 |

LMKD 依据系统压力和进程优先级做回收，应用侧无法通过 Memory Advice API 阻止 LMKD。`ApplicationExitInfo` 是事后归因入口，详见 26.9 节；低内存对系统性能的影响和 LMKD 触发路径详见 10.4 节。

Android Vitals 的 LMK 指标适合看版本质量和机型分布。若某版本的 user-perceived LMK rate 上升，端侧可以回放该版本的 Memory Advice 状态、资源档位、PSS / RSS / Graphics 曲线，确认是否存在资源预算失控。Android Vitals 不会告诉你“哪张纹理应该释放”。

## 游戏资产与图形内存降级策略

Memory Advice API 的价值取决于资源系统是否有可执行动作。只监听状态、不改变资源预算，线上结果不会变。

一套可执行的分级表通常长这样：

| 压力等级 | 纹理 / 图片 | mesh / 动画 | 音频 | 关卡与场景 | 引擎缓存 |
| --- | --- | --- | --- | --- | --- |
| `OK` | 按设备档位加载 | 保持当前 LOD | 保持当前采样率和缓存 | 保持预加载窗口 | 维持命中率优先 |
| `APPROACHING_LIMIT` | 停止加载更高 mip / 高分辨率贴图 | 新对象使用较低 LOD | 限制长音频预解码 | 缩短下一场景预加载窗口 | 清理可重建缓存，冻结对象池扩容 |
| `CRITICAL` | 降低一档纹理质量，释放屏外大贴图 | 释放不可见角色高模资源 | 清理非即时音效缓存 | 取消后台关卡流式加载 | 释放 shader / pipeline cache 中低命中项，回收临时 arena |

这些动作要满足两个约束。第一，释放后必须可恢复；用户切回高画质或进入新场景时能重新加载。第二，释放路径本身不能制造卡顿；大批量 GPU 资源销毁应分帧执行，并记录每批资源数量、耗时和释放前后内存指标。

游戏项目容易把 Java Heap 优化当成全部内存优化。Memory Advice API 的估算会把 Native Heap 和图形 API 分配纳入视野，实际治理也要把 Java 对象、Native arena、纹理、DMA-BUF、线程栈一起纳入预算。Java Heap 收缩了，但 Vulkan 纹理池继续涨，LMK 风险不会自然消失。Native 内存排查详见 23.3 节，线上水位线详见 23.7 节。

## Perfetto 与 meminfo 验证方法

Memory Advice 状态只能作为输入信号，发布前要用系统指标复核。最小验证路径分四层：

| 验证层 | 命令 / 工具 | 读数 | 用法 |
| --- | --- | --- | --- |
| 进程全景 | `adb shell dumpsys meminfo <package>` | PSS、Private Dirty、Java Heap、Native Heap、Graphics | 确认状态变化前后进程总占用是否下降 |
| VMA 明细 | `/proc/<pid>/maps`、`/proc/<pid>/smaps_rollup` | `[anon:*]`、`.so`、ashmem、dmabuf 映射 | 区分 Native arena、线程栈、图形 buffer 和文件映射 |
| 分配调用栈 | Perfetto heapprofd / Android Studio Native Memory Profiler | Native allocation callstack、malloc RSS 差异 | 找到哪个模块持续分配，避免只按资源类型猜 |
| 图形内存 | Perfetto memory counters、GPU / DMA-BUF 相关轨道、厂商工具 | graphics PSS、DMA-BUF、Vulkan / GL 分配趋势 | 验证纹理和图形 buffer 降级是否反映到系统口径 |

Perfetto heapprofd 适合解释 Native Heap 由谁分配，但它和 `malloc_info()`、RSS、PSS 的口径不同。Perfetto 文档也提示：heapprofd 看到的是分配调用栈，RSS 还受 allocator 缓存、ZRAM、页面驻留影响；`dumpsys meminfo` 的 Private Dirty 更接近系统侧回收成本。[已验证: Perfetto docs, perfetto.dev/docs/data-sources/native-heap-profiler]

一次合格的验证至少包含三组数据：

- 状态序列：每次 `MemoryState` 变化、`GetAvailableMemory()`、资源档位、场景名、帧率档位。
- 内存序列：PSS / RSS / Java Heap / Native Heap / Graphics / DMA-BUF，按场景和设备 RAM 档位分组。
- 结果序列：LMK、`ApplicationExitInfo` reason、冷启动回访、卡顿率、资源降级用户感知投诉。

如果 `CRITICAL` 出现后内存没有下降，要查释放动作是否只清了 Java 缓存；如果内存下降但卡顿上升，要查释放动作是否集中在渲染线程；如果状态长期 `OK` 但 Vitals LMK 上升，要回到 LMKD、机型 RAM 档位和图形内存口径重新核对。

## Unity / Unreal 接入差异

Unity 官方插件把 C API 包装成 C# 可调用接口，示例同样围绕 `GetMemoryState()` 和 watcher 展开。它适合历史 Unity 项目做最小接入，但版本组合要按官方列出的 Unity / NDK 对照关系验证，不能只看 Android API level。[已验证: 官方文档, developer.android.com/games/engines/unity/memory-advice]

Unreal 或自研引擎更适合在 native 层封装一层 `MemoryPressureService`，对外只暴露资源预算变化。例如：

- `MemoryPressure::Normal`: 维持当前资源档位。
- `MemoryPressure::Conservative`: 停止预加载，缩小缓存。
- `MemoryPressure::Emergency`: 分帧释放非当前视野资源，降低纹理质量。

这样做的好处是后续替换信号源不会影响资源系统。Memory Advice API 废弃后，可以把信号源切到 `onTrimMemory()`、自研 PSS/RSS 采样、Android Vitals 线上阈值、`ApplicationExitInfo` 回访结果，而业务层不用改。

## 与 Android 17 App Memory Limits 的关系

23.9 节讨论的是 Android 17 App Memory Limits 和内存泄漏治理，它关注系统侧限制、退出归因和触发式诊断。Memory Advice API 关注的是运行中提前降级。两个方向的关系可以按时间顺序理解：

1. 运行中：Memory Advice API 或替代信号提示引擎收缩资源预算。
2. 接近系统限制：`onTrimMemory()`、系统内存压力、LMKD 风险升高。
3. 退出后：`ApplicationExitInfo`、Android Vitals、端侧日志回放确认是否低内存退出。
4. 下一版本：把退出归因回灌到资源预算表，调整纹理、关卡预加载、对象池上限。

如果 Android 17 App Memory Limits 在目标设备上提供更明确的退出归因，Memory Advice API 仍然不能替代它；它只能作为“退出前尝试自救”的一类输入。新项目应优先围绕系统公开诊断能力和自研预算体系搭建，不要因为历史 API 名字里带 advice 就把它放到架构中心。

## 线上灰度策略

内存降级策略不能一次性对所有用户打开。推荐按“只采集 → 温和动作 → 激进动作”三阶段灰度：

| 阶段 | 开关 | 动作 | 退出条件 |
| --- | --- | --- | --- |
| 只采集 | 记录状态、场景、内存曲线，不改变资源 | 建立状态与 LMK / 卡顿的相关性 | 数据覆盖主力机型和低 RAM 档位 |
| 温和动作 | `APPROACHING_LIMIT` 触发停止预加载、清理可重建缓存 | 观察卡顿率、资源重载耗时、用户画质感知 | LMK 下降且卡顿无明显上升 |
| 激进动作 | `CRITICAL` 触发画质降档、释放图形资源 | 小流量灰度，强制记录释放批次和耗时 | 有明确收益，且投诉和卡顿指标可控 |

端侧日志要能回答四个问题：什么场景触发、哪个状态触发、释放了多少资源、释放后系统口径是否下降。缺少这四个字段，线上只会留下“某次回调触发过”的弱证据。

## 小结

Memory Advice API 的发布口径已经变了：它是一个已废弃的 beta 库，不适合作为新项目首选方案。历史项目维护时，可以把它当作运行时内存压力信号，驱动游戏资源系统做分级降级；所有结论都要用 `dumpsys meminfo`、Perfetto、heapprofd、`ApplicationExitInfo` 和 Android Vitals 复核。

对游戏内存治理来说，最稳的结构是信号源可替换、资源预算可配置、释放动作可回放。Memory Advice API 只是其中一个信号源。

## 参考资料

- [Memory Advice API overview](https://developer.android.com/games/sdk/memory-advice/overview)
- [Get started with the Memory Advice API](https://developer.android.com/games/sdk/memory-advice/start)
- [Manage memory effectively in games](https://developer.android.com/games/optimize/memory-allocation)
- [memory_advice namespace reference](https://developer.android.com/reference/games/memory-advice/namespacememory/advice)
- [Low memory killers | Android Developers](https://developer.android.com/games/optimize/vitals/lmk)
- [AOSP gamesdk memory_advice.h](https://android.googlesource.com/platform/frameworks/opt/gamesdk/+/master/include/memory_advice/memory_advice.h)
- [AOSP gamesdk MemoryAdviceImpl](https://android.googlesource.com/platform/frameworks/opt/gamesdk/+/master/games-memory-advice/core/memory_advice_impl.cpp)
- [AOSP gamesdk MetricsProvider](https://android.googlesource.com/platform/frameworks/opt/gamesdk/+/master/games-memory-advice/core/metrics_provider.cpp)
- [AOSP gamesdk StateWatcher](https://android.googlesource.com/platform/frameworks/opt/gamesdk/+/master/games-memory-advice/core/state_watcher.cpp)
- [结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]
- [结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]
- [结构参考: Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md]
- [结构参考: Clippings/Android 性能优化 - 虚拟内存优化（上）：线程+多进程优化.md]
