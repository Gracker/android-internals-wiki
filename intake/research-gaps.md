**研究方向**: 需要分析 Android 17 binder IPCThreadState.cpp 中的优先级继承实现机制


## [Task2A Round 60] 知识缺口挖掘 — 2026-07-11 03:04

### 已检查方向（本轮）
- ✅ Phase 0: 发现 6 个空 draft 全部为重复创建 → 已清理删除
- ✅ Phase 0.5: TASK2B_BACKLOG=0，允许进入 Phase 1
- ✅ DeepResearch 新增文件 1 个 (2026-07-11 02:55): android17-gpu-power-hal-dvfs-headroom
- ✅ source-index: 114 个 unmapped 条目均已对应到已有章节（前 59 轮已覆盖）
- ✅ Clippings: 无新文件
- ✅ research-feeds: 无新文件
- ✅ daily-info: 无新增

### 合格缺口（≥14 分）
1. ✅ **5.29 GPU DVFS Headroom + PowerAdvisor** — 评分 18/20
   - 素材: DeepResearch 250+ 行一手 AOSP 源码调研
   - 现有覆盖: 5.04/5.09/15.1 仅 API 层提及，缺少 HAL 实现 + SurfaceFlinger PowerAdvisor + Composition 反向通道
   - 新增内容: Power HAL V6 接口 / HintManagerService HeadroomCache / SurfaceFlinger boost/mode 推送 / sendCompositionData 反向通道 / Scheduler 65Hz 阈值

### 清理动作
- 删除 6 个重复空 draft 文件（01.56, 01.57, 01.58, 01.59, 04.45, 08.1）
- 记录到 metadata/duplicate-cleanup-log.md

### 结论
1 个新知识缺口（5.29, 18/20）已创建并录入。Coverage remains well-mapped after 60 rounds.


## [Task2A Round 61] 知识缺口挖掘 — 2026-07-11 04:04

### 已检查方向（本轮）
- ✅ Phase 0: 0 个空 draft 章节
- ✅ Phase 0.5: TASK2B_BACKLOG=1，允许进入 Phase 1
- ✅ source-index: 46 个 high-score 条目，全部已映射到已有章节
- ✅ DeepResearch 新增文件 3 个 (2026-07-10~11): thread-affinity→§20.9, satellite-ntn→§24.11, flutter-impeller→§22.30
- ✅ Clippings: 无新文件 (7+ 天无更新)
- ✅ daily-info 2026-07-11: 2 项 (调度器/内存→§1.43/§4.x, Linux BPF→§14.25)
- ✅ AOSP 系统服务扫描: 53 个候选服务，筛选后 4 个初步合格
- ✅ Android 17 新特性扫描: 13 个 NOT COVERED 特性，筛选后 2 个合格

### 合格缺口（≥14 分）
1. ✅ **5.30 OnDeviceIntelligence / FoundationModelManager** — 评分 18/20
   - 素材: AOSP packages/modules/OnDeviceIntelligence + developer.android.com API 参考
   - 现有覆盖: §5.20 (AICore) / §5.21 (AppFunctionService) / §23.24 (NN HAL) 均未覆盖框架级推理调度
   - 新增内容: Mainline 模块架构 / 模型生命周期 / 推理调度与 ADPF 协同 / 沙箱 IPC 开销 / QoS 排队 / 功耗归因 / 三层 API 分工

### 不合格候选 (<14 分)
- AlarmManager Doze 适配 (12/20) — 已在 §25.20 覆盖
- JobScheduler/WorkManager (12/20) — 已在 §25.04/§25.13 覆盖
- InputManager 输入分发 (11/20) — 已在 ch03-input (13 节) 覆盖
- AppIntents/AppFunctions (11/20) — 与 §5.21 高度重叠
- BatteryStats 归因 (12/20) — §25.01 power-diagnosis 已覆盖核心内容
- DeviceIdleController (13/20) — Doze 成熟，时效性不足
- MediaCodec 编解码 (12/20) — 非全书核心方向
- Mainline Module 性能 (13/20) — 间接影响，素材不足
- HealthConnect/Uwb/Matter (5-6/20) — 非性能相关

### 结论
1 个新知识缺口（5.30, 18/20）已创建并录入。Coverage remains well-mapped after 61 rounds.


## [Task2A Round 62] 知识缺口挖掘 — 2026-07-11 05:06

### 已检查方向（本轮）
- ✅ Phase 0: 0 个空 draft 章节
- ✅ Phase 0.5: TASK2B_BACKLOG=0，允许进入 Phase 1
- ✅ source-index: 0 个 unmapped high-quality 条目（全部已映射）
- ✅ DeepResearch: 无新文件（最近 2026-07-11 02:55 已被 Round 60 消费）
- ✅ Clippings: 无新文件（18+ 天无更新，最后 2026-06-23）
- ✅ research-feeds: 无新文件（最后 2026-04-14）
- ✅ daily-info 2026-07-11: 2 项 RSS（调度器/内存→§1.43/§4.x, Linux BPF→§14.25），均已映射
- ✅ AOSP 系统服务: 前 61 轮已全面覆盖
- ✅ Android 17 新特性: 前 61 轮已全面覆盖
- ✅ 章节扩展点: 前 61 轮已全部评估

### 合格缺口（≥14 分）
（无）

### 结论
Coverage remains saturated (62nd consecutive round). No new knowledge gaps ≥14 identified.
All input sources (DeepResearch, Clippings, research-feeds, daily-info, source-index) have been fully consumed.


---

## [2026-07-11] 第24章 包体积优化 — 参考书素材

### 来源
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 25.md（第22讲 包体积上）+ 26.md（第23讲 包体积下）]

### 知识点
1. 包体积与下载转化率关系（Google I/O 数据：APK 越小转化率越高，10MB vs 40MB 差距明显）
2. 包体积对性能三维度影响：安装时间（ODEX 编译）、运行内存（Resource/Library/Dex 类加载占内存）、ROM 空间（100MB APK 解压后 >200MB）
3. ProGuard/R8 混淆优化技巧：过度 keep 检测、四大组件和 View 混淆（XML+代码替换，ASM 实现，饿了么 Mess 组件）
4. Debug 信息/行号裁剪优化（ReDex StripDebugInfoPass：drop_local_variables/drop_line_numbers 配置，可减约 5% Dex 体积，保留行号用于崩溃栈）
5. Dex 分包优化：跨 Dex 调用冗余分析、ReDex InterDexPass 贪心算法最小化跨 Dex 引用、Dex 信息有效率指标
6. Dex 压缩：XZ/LZMA 压缩（比 Zip 高 30%）、Facebook secondary.dex.jar.xzs 方案、多线程首次启动解压
7. Native Library 优化：XZ 压缩 + SoLoader、Library 合并（Buck，Android 4.3 前进程加载限制）、Library 裁剪（relinkersymbol 分析无用导出符号）
8. AndResGuard 资源混淆原理：短路径优化 resources.arsc + 签名文件(MF/SF) + ZIP 文件索引
9. AndResGuard 极限压缩：7-Zip 大字典（提升约 3%）+ 强制压缩 PNG/JPG/GIF
10. 资源合并方案：所有资源合并为大文件 + mmap 加载 + 自定义 ResourceCache（参考 Facebook 逆向发现）
11. 无用资源优化三阶段演进：Lint 静态扫描 → shrinkResources（配合 ProGuard，但不处理 resources.arsc 且不真正删除文件）→ realShrinkResources（Public ID 非连续机制，重写 resources.arsc）
12. 包体积监控体系：大小监控（版本对比）、依赖监控（JAR/AAR 新增）、规则监控（ApkChecker：无用资源/大文件/重复文件/R 文件）
13. 无用 Assets 资源识别难点（代码中各种引用方式导致难以准确识别）

### 重要程度
中（AIW 当前缺少独立的包体积优化章节，这些知识点具有较高的实战参考价值，但需结合 Android 17 的 App Bundle/R8/AGP 最新特性进行全面更新）

### 建议加工方向
- 以参考书的优化思路框架（代码→Library→资源→监控）为骨架，结合 Android 17 AAB 分发、R8 full mode、AGP resource shrinking 最新实现进行刷新
- 重点更新：App Bundle 已成为标准分发格式（Split APKs 按需下载）、R8 完全替代 ProGuard 且与 ReDex 的关系需重新评估
- 资源混淆部分：AndResGuard 原理仍有教学价值，但 AGP 已内置资源优化能力，需对比说明
- [需确认: 参考书中提到的 shrinkResources 缺陷在 Android 17 AGP 中是否已修复]

## [2026-07-11] 第22章 渲染实战 — 参考书素材（进阶手段更新）

### 来源
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 24.md（第21讲 UI优化下）]

### 知识点
1. Litho 异步布局框架：measure/layout 移至后台线程（Yoga 布局引擎）、界面扁平化（自动减少 ViewGroup 层级）、RecyclerView 组件级缓存（按 text/image/video 独立回收）
2. Flutter 渲染架构：Skia 引擎直接集成（不依赖系统渲染）、Dart VM + isolate 并发模型、UI Runner → GPU Runner 四阶段渲染管线、Layer Tree 生成与栅格化
3. RenderThread 异步动画渲染（Android 5.0+）：ViewPropertyAnimator/CircularReveal 主线程阻塞时不受影响
4. UI 优化演进脉络：系统框架下优化 → 利用系统新特性 → 突破系统限制

### 重要程度
中（AIW 已有 §22.30 Impeller/Flutter 相关内容，需对比参考书的历史视角与当前 Flutter Impeller 的差异）

### 建议加工方向
- Litho 部分需标注 2026 现状（使用率下降，Jetpack Compose 已成为声明式 UI 主流）
- Flutter 部分需从参考书的 Skia 时代更新至 Impeller 时代（§22.30 已覆盖部分）
- RenderThread 异步动画作为系统特性的基础知识点仍有保留价值
- [需确认: Jetpack Compose 的 measure/layout 异步化能力是否已覆盖 Litho 的核心优化点]


## [Task2A Round 63] 知识缺口挖掘 — 2026-07-11 08:06

### 已检查方向（本轮）
- ✅ Phase 0: 0 个空 draft 章节（53 个 draft 全部 >15 行）
- ✅ Phase 0.5: TASK2B_BACKLOG=0，允许进入 Phase 1
- ✅ source-index: 0 个 unmapped high-quality 条目（全部已映射）
- ✅ DeepResearch: 最新 2 个文件 (2026-07-11) 已被 Round 60/61 消费（→§5.29/§20.9）
- ✅ Clippings: 无新文件（18+ 天无更新，最后 2026-06-23）
- ✅ research-feeds: 无新文件（最后 2026-04-14）
- ✅ daily-info 2026-07-11: 2 项 RSS（调度器/内存→§1.43/§4.x, Linux BPF→§14.25），均已映射
- ✅ Task 11 增量扫描: 5 项（satellite-ntn→§24.11, SoC battery→§15.1/§5.21/§17.21, startup→§21.2, Flutter Impeller→§22.30, thread affinity→§20.9），全部映射到已有章节
- ✅ suggestions.md: Task14 ch06 补充建议（Dex/ODEX/R8/资源编译/APK压缩），均为已有章节补充
- ✅ queue.json pending: §2.32/§5.30/§5.28/§ch16/§14.11 — 全部为已有章节的素材注入/补充

### 合格缺口（≥14 分）
（无）

### 结论
Coverage remains saturated (63rd consecutive round). No new knowledge gaps ≥14 identified. All new material maps to existing chapters.


---

## [Task2A Round 64] 知识缺口挖掘 — 2026-07-11 09:10

### 已检查方向（本轮）
- ✅ Phase 0: 0 个空 draft 章节（53 个 draft 全部 >15 行）
- ✅ Phase 0.5: TASK2B_BACKLOG=0，允许进入 Phase 1
- ✅ source-index: 0 个 unmapped high-quality 条目（全部已映射）
- ✅ DeepResearch: 最新文件 (2026-07-11 06:20 注入) 已被 Round 61/63 消费
  - APA/AGI System Profiler + ANGLE denylist → §14.8 supplement
  - PowerMonitor 数据精度 → §14.11/§25.18 supplement
  - SoC battery optimization → §5.22 supplement
  - eBPF observability matrix verified → §14.25 supplement (已创建)
  - Power Stats HAL OEM → §25.18 supplement
- ✅ Clippings: 无新文件（18+ 天无更新，最后 2026-06-23）
- ✅ research-feeds: 无新文件（最后 2026-04-14）
- ✅ daily-info 2026-07-11: 2 项 RSS（调度器/内存→§1.43/§4.x, Linux BPF→§14.25），均已映射
- ✅ WOOTdroid 论文 (arxiv 2604.27830, 06:45 注入): Pixel 9/Android 16 eBPF 全系统追踪 → §14.25/§1.4 已覆盖，评分 9/20（学术研究，素材 2 + 相关性 3 + 需求 2 + 时效 2）
- ✅ Task14 suggestions (06:32): 全部为已有章节补充（ch02 渲染/gfxinfo framestats/GAPID→AGI, ch06 存储 Dex/ODEX/R8/资源编译, ch22 渲染实战/Litho/Flutter）
- ✅ AOSP 系统服务: 前 63 轮已全面覆盖
- ✅ Android 17 新特性: 前 63 轮已全面覆盖
- ✅ 章节扩展点: 前 63 轮已全部评估

### 合格缺口（≥14 分）
（无）

### 结论
Coverage remains saturated (64th consecutive round). No new knowledge gaps ≥14 identified.
All input sources (DeepResearch, Clippings, research-feeds, daily-info, source-index, Task14 suggestions) have been fully consumed and map to existing chapters.
