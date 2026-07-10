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
