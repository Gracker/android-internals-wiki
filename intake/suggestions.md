# Task 9 Suggestions - 2026-06-03 07:20

## Blocked by Task2B Verifier (2026-06-03)

### Task2B 阻塞章节

**09-finalizer-referencequeue.md**
- **Issue**: Task9 标记 needs-rework 但 queue 中无对应条目
- **Current**: pipeline_stage=task6_pending, task9_result=needs-rework
- **Status**: blocked-need-rework-evidence
- **Action**: 待 Task2B 处理返工需求

**27-apm-client-architecture.md**
- **Issue**: Task9 标记 needs-rework 但 queue 中无对应条目
- **Current**: pipeline_stage=task6_pending, task9_result=needs-rework
- **Status**: blocked-need-rework-evidence
- **Action**: 待 Task2B 处理返工需求

## P0 Priority Suggestions

### Measure (19.09)
**SUGG-MEASURE-P0-001**
- **Issue**: Native crash capability incorrectly described as supported
- **Current**: "包含 native crash reporting" 
- **Fix**: "当前 Android native crash reporting 尚未完全支持，仅支持 Java/Kotlin crash"
- **Impact**: Critical - prevents misinformation about capability boundaries

### Measure (19.09)
**SUGG-MEASURE-P0-002** 
- **Issue**: ANR boundary description incomplete
- **Current**: Only mentions "API 10 以下没有 ApplicationExitInfo"
- **Fix**: Supplement with "Android 10-11 仅有 ApplicationExitInfo 但无完整 ANR 支持直到 API 31+"
- **Impact**: Critical - clarifies version support timeline

### Measure (19.09)
**SUGG-MEASURE-P0-003**
- **Issue**: HTTP body configuration not properly explained
- **Current**: Claims "默认不采集 body" but doesn't explain configuration
- **Fix**: Add explicit configuration parameters and enablement conditions
- **Impact**: Medium - affects data collection accuracy

### Measure (19.09)
**SUGG-MEASURE-P0-004**
- **Issue**: Retention endpoint path clarification needed
- **Current**: "GET/PATCH /apps/:id/retention is针对的是 apps，不是全局配置"
- **Fix**: Clarify API scope and parameter structure
- **Impact**: Medium - affects API usage understanding

## P1 Priority Suggestions

### 崩溃与 ANR 捕获机制 (19.24)
**SUGG-ANR-P1-001**
- **Issue**: ProfilingTrigger API 37 capabilities incomplete
- **Current**: Missing TRIGGER_TYPE_OOM, TRIGGER_TYPE_ANOMALY, TRIGGER_TYPE_APP_COMPAT
- **Fix**: Add complete trigger type list and usage scenarios for API 37
- **Impact**: High - covers latest Android capabilities

### Measure (19.09)
**SUGG-MEASURE-P1-001**
- **Issue**: Android 12-14 ANR capture evolution not documented
- **Current**: No version-specific ANR handling differences
- **Fix**: Document ANR capture capabilities across Android 12-14
- **Impact**: High - affects version-specific implementation

### Measure (19.09)
**SUGG-MEASURE-P1-002**
- **Issue**: Android 15+ native crash support not addressed
- **Current**: No mention of newer native crash capabilities
- **Fix**: Document Android 15+ native crash reporting evolution
- **Impact**: Medium - future-proofing the content

### 崩溃与 ANR 捕获机制 (19.24)
**SUGG-ANR-P1-002**
- **Issue**: KOOM fork-dump boundaries not clarified for Android 17
- **Current**: No mention of Android 17 compatibility
- **Fix**: Document Android 17 applicability and limitations
- **Impact**: Medium - affects low-tier device strategy

### TextureView 合成链路 (18.7)
**SUGG-TV-P1-001**
- **Issue**: BLAST submit chain not detailed enough
- **Current**: BLAST adapter to SurfaceFlinger interaction unclear
- **Fix**: Add detailed BLAST Transaction and Buffer flow description
- **Impact**: High - understanding performance bottlenecks

### TextureView 合成链路 (18.7)
**SUGG-TV-P1-002**
- **Issue**: Double fence mechanism synchronization unclear
- **Current**: Two-layer fence synchronization timing not explained
- **Fix**: Clarify acquire fence and composition fence dependency relationships
- **Impact**: Medium - important for debugging

## P2 Priority Suggestions

### All Chapters
**SUGG-ALL-P2-001**
- **Issue**: Missing performance benchmark data
- **Current**: No concrete performance metrics or benchmarks
- **Fix**: Add specific GPU sampling time, memory usage, and processing time data
- **Impact**: Medium - enables quantitative optimization decisions

### Measure (19.09)
**SUGG-MEASURE-P2-001**
- **Issue**: Data model chain flow unclear
- **Current**: Event production to backend aggregation process not described
- **Fix**: Add complete data flow diagram and pipeline description
- **Impact**: Medium - improves implementation understanding

### Measure (19.09)
**SUGG-MEASURE-P2-002**
- **Issue**: Session timeline construction principles missing
- **Current**: No technical details on how events relate to session_id
- **Fix**: Add session association mechanism explanation
- **Impact**: Low - completeness improvement

### TextureView 合成链路 (18.7)
**SUGG-TV-P2-001**
- **Issue**: Metal/Vulkan backend differences missing
- **Current**: Only covers OpenGL ES performance characteristics
- **Fix**: Add Metal/Vulkan vs OpenGL ES performance comparison
- **Impact**: Medium - future-proofing for modern devices

### TextureView 合成链路 (18.7)
**SUGG-TV-P2-002**
- **Issue**: BufferQueue reference path incorrect
- **Current**: Cross-reference path doesn't match actual file structure
- **Fix**: Correct the chapter reference to [2.13 图形缓冲区管理]
- **Impact**: Low - reference accuracy
## [Task6 Review] 25.6 APK 体积分析与瘦身 — 2026-06-03
- **类型**：需确认
- **位置**：`.so` 库瘦身节 — AOSP master 源码锚点（PackageAbiHelperImpl.java、NativeLibraryHelper.java、ResourceTypes.h）
- **问题**：三处源码引用标注为 "AOSP master"，按 AIW Android 版本边界规则（AIW_ANDROID_VERSION_CAP_2026_05_29），应替换为 android-17.0.0_r1 或更低版本标签，或标注"未进入 Android 17"并跳过正文结论。
- **建议**：Task9 验证三处源码锚点的版本归属，替换为已验证版本标签或改为"未进入 Android 17"背景说明。
- **review 日志**：logs/review/2026-06-03-14-review.md

## [Task9 Deep Review] 25.5 定位与传感器功耗优化 — 2026-06-03
- **类型**：版本差异/数据支撑
- **位置**：L197 传感器后台速率表格；L263 高频词说明段
- **问题**：`200 Hz` 在官方文档中是系统级软上限，设备 sensor hub 硬件可能支持更高采样率，但系统不会给 App 返回超过此值的事件。原文未标注"软上限"属性，读者可能误以为 200 Hz 是硬件能力而非系统上限。
- **建议**：在表格说明列和 L263 末尾各补充一句：`"200 Hz 是系统允许的软上限，设备传感器硬件本身可能支持更高采样率，但系统不会给 App 返回超过此值的事件"`。

## [Task9 Deep Review] 25.7 R8 与资源优化 — 2026-06-03
- **类型**：源码准确性/版本差异
- **位置**：L150 AVIF 格式适用版本
- **问题**：正文语境为 APK 体积优化（BitmapFactory/ImageDecoder 平台级 API），声称"Android 12（API 31）及以上设备"；若指平台级 AVIF decode，Android 10（API 29）起 `ImageDecoder` 即支持 AVIF（需设备内置 AVIF 解码器）；若指 WebView Chromium AVIF，则与 WebView 版本绑定，Pixel 6+ Android 12 起 Chromium 99+ 支持。原文按平台级 claim 更准确，Android 12+ 是保守下限。建议核实后确认。
- **建议**：结合实际目标读者场景，明确是"平台级 ImageDecoder AVIF decode（API 29+，但取决于设备厂商是否内置解码器）"还是"WebView Chromium AVIF 支持（Android 12+ Pixel 6 起）"，二者的版本边界和使用条件不同。


## Task2B 回炉修复 (frontmatter fallback) — 2026-06-03 21:40

### 3.6 手势识别算法与性能优化
- 来源：2026-05-18 deep-review audit (last_task9_audit)
- P1: VelocityTracker DEFAULT_STRATEGY_BY_AXIS 版本限定 — 补充 Android 10-13 全局 LSQ2 路径说明，明确轴级策略矩阵为 Android 14+ 特性
- P2: VelocityThreshold 资源层次 — 补充 config_viewMinFlingVelocity/config_viewMaxFlingVelocity overlay 机制和 Android 14+ axis/source 级重载
- 状态：fixed → task6_pending

### 5.3 大小核架构
- 来源：2026-05-18 task9 deep-review
- P0: sugov_get_util() 代码块修正 — 重写为与实际 android16-6.12 源码一致的实现（scx_cpuperf_target 初值 → CFS util 条件叠加 → effective_cpu_util → boost 后置 → sugov_effective_cpu_perf 映射）
- P2: 骁龙 8 Elite capacity 数据锚点 — 添加容量数值外推估算标注和设备级验证路径说明
- 状态：fixed → task6_pending


---

## DeepSeek 中文读者终审建议 — 2026-06-04

### 1. ch05.7 (07-cpu-evolution.md) — Android 14 精确闹钟段落错位

**问题**：Android 12 小节名为 "Android 12：精确闹钟进入特殊访问控制"，但其中包含一整段 Android 14 的精确闹钟默认拒绝描述（"Android 14 起，精确闹钟权限默认更严格：SCHEDULE_EXACT_ALARM 权限对大多数新安装且 targetSdkVersion >= 33 的 App 默认拒绝..."）。读者在 Android 12 小节内突然读到 Android 14 的行为，会困惑。

**建议**：将 Android 14 精确闹钟段落移到 Android 14 小节（"Android 14：前台服务类型化 + 后台 Activity 启动需显式 opt-in"），或在 Android 12 小节末尾加一句"Android 14 进一步将默认授予改为默认拒绝，详见下文 Android 14 小节"作为指引。当前写法会让读者在同一节内先看到"需要声明 SCHEDULE_EXACT_ALARM"再看到"默认拒绝"，但中间隔了 Android 13 的内容。

**严重度**：中。不影响技术准确性，但打乱了读者的时间线理解。

### 2. ch05.7 (07-cpu-evolution.md) — 已移除的 Energy Limiter 未核实线索

**原内容**：Android 17 小节末尾有一块 "> ⚠️ 未核实研究线索" 引用，提到 "ODPM/μJ 计量的 Energy Limiter 机制"。本轮终审已从正文移除，因为它是编辑过程笔记，不应出现在读者面前。

**建议**：如果后续官方确认该机制存在，可以作为正式特性补充到 Android 17 小节。目前这条线索可以保留在 DeepResearch 或素材库中跟踪。

### 3. ch05.8 (08-background-execution.md) — 已移除的 AVF pVM 待验证豁免

**原内容**：例外与豁免小节有一条 "AVF pVM 任务配额豁免：[待验证]" 条目。本轮终审已从正文移除——[待验证] 标记和"未在官方文档中核验到"的自述说明这条内容尚未达到发布标准。

**建议**：AVF pVM 任务配额豁免如果后续被 AOSP 或 Android Developers 文档确认成立，可以作为正式豁免条目补回。目前只适合留在素材跟踪清单中。

### 4. ch05.8 (08-background-execution.md) — Freezer/Binder 源码注入的阅读体验

**问题**：Freezer/Binder 协同冻结的两个小节（CachedAppOptimizer 流程 + Binder Freezer Driver 补充）来自 DeepResearch 源码级调研，包含大量 C 结构体定义、ioctl 返回码表和内核 commit hash。这部分内容的深度和密度明显高于本章其他段落，读者从"选 WorkManager 还是 JobScheduler"突然跳到"binder_freeze_info 结构体定义"，认知跳跃大。

**本轮处理**：已添加过渡句连接这两段，但本质问题是 Freezer 源码分析是否应该独立成节或收入附录。本轮不做跨节重构，留给后续编辑决策。

**严重度**：低-中。过渡句缓解了跳跃感，但长线看结构可能需要调整。


## [Task6 Review] 2.19 刷新率切换与帧率适配性能 — 2026-06-04

- **类型**：需重写 / 需补充素材
- **位置**：机制解释节伪代码块 + 案例代码 + 误区条目
- **问题**：
  1. VsyncConfiguration/Scheduler/Display.h/VsyncController/DisplayManagerInternal 等 5 个代码块含疑似编造的 AOSP 类名和方法签名，未标注为伪代码
  2. 案例 1-3 代码块使用编造 API（notifyPendingRefreshRateChange / smoothRefreshRateTransition 等）
  3. FrameTimeline 监控代码含 wasRefreshRateSwitch() 编造方法
  4. 误区 1-4 各仅 1 句，信息密度极低
- **建议**：
  1-3. Task 9 核实后改为概念性叙述 + 真实 API 引用，或明确标注为伪代码
  4. 展开为 2-3 段叙述，说明误区来源和正确理解
- **review 日志**：logs/review/2026-06-04-11-review.md


## Task 2A 缺口挖掘记录 — 2026-06-04 12:10

### 已检查方向（本轮无 ≥ 14 分候选）

1. **source-index.json 高质量未映射素材**：仅有 1 条记录，无未映射高质量素材。
2. **research-feeds 最近 5 条**（2026-03-29 ~ 2026-04-14）：
   - ch04-memory 素材索引 → 已映射到 ch04/ch01/ch05
   - Perfetto v53 Rust SDK / pprof / Simpleperf → 已映射到 ch13/ch14
   - Perfetto v54 Data Explorer / Jank CUJ → 已有 13.14 覆盖
   - Frame Timeline API 33 → 已映射到 ch02.04
   - Compose Pausable Composition → 已映射到 ch02.04 / ch22.03
3. **daily-info 最近 3 天**（2026-06-02 ~ 2026-06-04）：
   - 掘金文章多为应用锁/Gemini API/NIA 架构/AI 工具等，与性能优化核心相关性低
   - DeepResearch 增量扫描涵盖 ProfilingManager/ANR Ftrace/TextureView Metal-Vulkan/CachedAppFreezer-GC/Compose 1.10 Strong Skipping/ViewTreeObserver，均为现有章节补充素材
   - Energy Limiter / Power Check → 标记为未核实研究线索，不可作为新章节依据
4. **Clippings 三本参考书对比**：
   - 《Android 应用稳定性剖析与优化》15 篇 → 全部主题已映射到 ch20/ch26/ch14
   - 《Android 性能优化》16 篇 → 全部主题已映射到 ch05/ch23/ch24/ch25
   - 《线上疑难问题》59 篇 → 全部主题已映射到 ch26/ch13/ch14/ch19
5. **AOSP 结构对照**：
   - frameworks/base/ 核心服务（AMS/PMS/WMS/SF/InputManager/PowerManager）均已覆盖
   - system/ 核心组件（vold/netd/lmkd/installd）已在 ch04/ch06 覆盖
   - packages/modules/ 性能相关模块（ADPF/Thermal/Battery）已在 ch05/ch11 覆盖
6. **官方文档对照**：
   - Android 17 API 37 性能行为变更 → 已有 16.5 专项章节
   - Android 16/17 后台执行限制 → 已有 ch05.08 / ch25.12 / ch25.13 覆盖
   - Android 17 图形/渲染变更 → 已有 ch02.24 / ch18.x 多章节覆盖

### 管线现状

- 已有 **15 个 draft 章节**（内容 85-157 行），卡在 draft 状态
- TASK2B_BACKLOG = 20（等于阈值，未超出）
- 全书 130+ 节，覆盖率已极高
- 建议优先消化现有 draft 管线，而非继续新增章节

### 结论

本轮未发现评分 ≥ 14 的知识缺口，跳过。

---

## Task2B 回炉修复报告 · 2026-06-04 14:50 (main lane, frontmatter backlog fallback)

### 本轮处理章节

- `src/part2-performance/ch07-smoothness/13-systemui-performance.md` (7.13 SystemUI 性能分析)
- `src/part1-fundamentals/ch05-cpu-power/12-thermal-management-deep-dive.md` (5.12 Thermal 管控深度)

### 来源：frontmatter backlog fallback

Queue 中无 task6/task9/external-review pending 条目。通过 frontmatter fallback 扫描命中 16 个候选。按 severity 95 选取 7.13 和 5.12，反查问题来源：
- 7.13 → `logs/deep-review/2026-05-21-17-audit.md`（4 P0 + 2 P1）
- 5.12 → `logs/deep-review/2026-05-22-05-audit.md`（2 P1）

### 7.13 SystemUI 修复摘要

- **P0 源码锚点**：`NavigationBarController.java` / `NavigationBarControllerImpl.java` 路径从 `statusbar/phone` 修正为 `navigationbar`；数据结构从 `HashMap<Int, NavigationBarView>` 修正为 `SparseArray<NavigationBar>`
- **P0 源码锚点**：`DisplayContent.supportsSystemDecorations()` → `isSystemDecorationsSupported()`；`setShouldShowSystemDecorsLocked()` → `shouldShowSystemDecorsLocked(DisplayContent)`
- **P0 源码锚点**：`CentralSurfacesImpl.onWallpaperVisibilityChanged(displayId, visible)` 未命中，修正为 `TaskbarDelegate.updateWallpaperVisibility(boolean visible, int displayId)`
- **P0 源码锚点**：WM Shell `DesktopModeController` 未命中，修正为 `DesktopTasksController.kt`、`DesktopDisplayEventHandler.kt`、`DesktopRepository.kt`、`DesktopMode.java`
- **P1 版本覆盖**：二级显示器限制从"Android 10+ 仅 NavigationBar/Wallpaper"修正为 Android 10-11 / 12-14 / 15-16 三级口径
- **P1 证据缺口**：桌面模式下 CPU/显存增长从"阶跃增长"降级为缺少 Perfetto trace/设备基线的待验证范围
- **自发现**：移除 Foldable 节 `HashMap<Int, NavigationBarView>` 残留描述

### 5.12 Thermal 修复摘要

- **P1 内核分支混用**：`last_verified_against` 从 `Linux kernel 6.1` 修正为 `android16-6.12`；critical trip 路径移除 `thermal_zone_device_halt()` / `__hw_protection_trigger()`，改为分支明确的 `do_orderly_poweroff()` / `do_orderly_reboot()`
- **P1 step_wise 参数遗漏**：`get_target_state()` 添加 `bool throttle` 参数及其控制逻辑
- **P1 HAL 版本链**：版本演进表从"API 34 = AIDL、35 = headroom thresholds、36 = SystemHealthManager"扩充为 Android 14 AIDL 基础接口 / Android 15 cooling callback / Android 16 forecastSkinTemperature + Framework 回退三档

### 状态更新

两个章节已更新 frontmatter：`task2b_result=fixed`、`task2b_state=fixed`、`task6_state=revisiting`、`task9_state=pending`、`pipeline_stage=task6_pending`。重新进入 Task6 → Task9 流水线。
