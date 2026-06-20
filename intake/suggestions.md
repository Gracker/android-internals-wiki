## [Task9 Deep Review] 11.4 案例集 — 2026-06-20

### P2 建议改进：

- **类型**：版本差异覆盖
- **位置**：JobScheduler throttling 机制
- **问题**：11.4.7 提到的三层节流防线在 Android 14-17 有重要变化未区分：Android 14 引入 CountQuotaTracker、Android 15 强化 mEJLimitsMs[] 配置、Android 16+ 完全迁移到 APEX。影响开发者准确理解和适配不同版本的限流策略。
- **建议**：按 Android 14/15/16/17 分节说明各版本的关键变化，特别是 QuotaController 配置差异和 APEX 路径稳定化时间点。

- **类型**：版本差异覆盖  
- **位置**：Location Mode 权限机制
- **问题**：文中提到 Android 12+ 开启后台节流（30min），但 Android 13 新增 READ_LOCATION_BYPASS_ALLOWLIST、Android 14 收紧 LOCATION_BYPASS，这些关键权限和策略演进未覆盖。
- **建议**：补充 Android 13-14 的 Location 权限沙盒演进，说明 OEM 定制点和应用适配策略差异。

- **类型**：原理链完整性
- **位置**：FGS 超时机制引入背景
- **问题**：11.4.1 描述了 Android 14-17 的 FGS 超时机制，但未解释为什么需要引入时间限制机制的根本原因。
- **建议**：补充 FGS 超时机制的引入背景：如无限运行导致的内存泄漏、系统资源竞争、用户投诉等业务场景，帮助读者理解设计动机。

### P3 锦上添花建议：

- **类型**：知识盲区
- **位置**：Radio 状态机与 Thermal 协同
- **问题**：未讨论 Radio 状态与 Thermal Status 协同的具体场景（如高温状态下 Radio 是否自动降频）。
- **建议**：增加 "Radio 状态机与热节流协同" 小节，分析不同 Thermal 等级对 Radio 状态的限制规则。
## [2026-06-20 21:00] Task2A 缺口挖掘 — 第 84 轮

### 本轮检查方向（6 个）
1. 今日 daily-info：ML 内存泄漏检测论文 — 评分 9/20（学术前沿，工程实战素材不足，全书定位不匹配）
2. Android 17 PowerStats 重构（PowerAttributor/PowerStatsProcessor）— 评分 17/20 但已在 11.1 章节由 Task2B 修复覆盖，非新缺口
3. Perfetto Remote Trace Processor 架构 — 评分 12/20，已在 queue 中 pending 供 13.7 章节补充，非新缺口
4. source-index.json 未映射素材 — 9 篇 DeepResearch 均已注入对应章节
5. 近期 research-feeds — 最新为 2026-04 月，全部已映射
6. AOSP frameworks/base 未覆盖服务 — 已在历轮 83+ 次扫描中穷尽

### 结论
- 最高新缺口评分：9/20（远低于 14 分门槛）
- 连续无合格缺口轮次：84 轮
- 全书 443 节（307 finalized, 94 ready-for-review, 3 draft 有实质内容）
- **知识库高度饱和，本轮跳过**
