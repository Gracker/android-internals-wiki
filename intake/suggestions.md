## [Task9 Deep Review] 15 Android 性能优化研究方法论 — 2026-07-04
- **类型**：源码准确性
- **位置**：Section 4.4 "VSync 偏动态调整"
- **问题**：将 VSync 系统简化为单组件，忽略了 Android 17 中拆分为三个协作组件的重大架构变化
- **建议**：更新源码描述，说明 VSyncTracker、VSyncModulator、VSyncDispatch 三组件协作的工作原理，及其对动态帧率切换的优化效果

## [Task9 Deep Review] 15 Android 性能优化研究方法论 — 2026-07-04
- **类型**：原理链完整性
- **位置**：Section 2.2 "三类研究方法，各有各的着力点"
- **问题**：方法论章节只讲"要做什么"，不讲"为什么这样工具匹配问题"，导致读者无法理解工具选择的内在逻辑
- **建议**：在章节中增加"问题类型→数据需求→工具匹配"的桥接逻辑，说明为什么启动性能必须用 Perfetto sched 数据源、内存泄漏需要 heapprofd 等

## [Task9 Deep Review] 15 Android 性能优化研究方法论 — 2026-07-04
- **类型**：数据缺失
- **位置**：Section 4.4 "Perfetto trace_processor 实战"
- **问题**：章节提到要分析 Expected vs Actual，但没有提供具体的 SQL 查询语句
- **建议**：补充如下 SQL 示例：
```sql
SELECT 
  f.frame_id,
  f.expected_presentation_timestamp_ns,
  f.actual_presentation_timestamp_ns,
  (f.actual_presentation_timestamp_ns - f.expected_presentation_timestamp_ns) / 1000000.0 AS miss_ms
FROM expected_frame_timeline f
JOIN actual_frame_timeline a ON f.frame_id = a.frame_id
WHERE a.actual_presentation_timestamp_ns > f.expected_presentation_timestamp_ns
ORDER BY miss_ms DESC;
```

## [Task9 Deep Review] 15 Android 性能优化研究方法论 — 2026-07-04
- **类型**：版本差异覆盖
- **位置**：Section 3.2 "版本兼容性"
- **问题**：DeviceConfig.perfetto 的具体 key 名称在文中描述不够准确
- **建议**：补充 `device_config list perfetto` 的典型输出示例，如：
```
perfetto.buffer_size_mb: 32
perfetto.heapprofd.enabled: true
perfetto.binder_tracing.enabled: true
```

## [Task9 Deep Review] 15 Android 性能优化研究方法论 — 2026-07-04
- **类型**：版本差异覆盖
- **位置**：Section 4.4 "自适应刷新率场景的帧数据分析"
- **问题**：缺少对 Android 17 AI 驱动调度器对帧率优化影响的说明
- **建议**：增加一节说明 AI 如何基于用户使用模式动态调整帧率分配，包括训练数据、决策阈值等

## [Task9 Deep Review] 15 Android 性能优化研究方法论 — 2026-07-04
- **类型**：数据支撑不足
- **位置**：Section 7.1 "验证的铁三角"
- **问题**：灰度发布所需的最小样本量缺少具体数值指导
- **建议**：补充具体数值：如"建议实验组占比 5%-10%，至少 10 万用户次数据，覆盖 3 个完整日历日"

## [Task9 Deep Review] 15 Android 性能优化研究方法论 — 2026-07-04
- **类型**：数据支撑不足
- **位置**：Section 4.4 "自适应刷新率场景的帧数据分析"
- **问题**：FrameRateOverrides API 的性能影响缺少实测数据支撑
- **建议**：补充典型场景的性能改善数据，如"游戏场景切换到 120Hz 后，帧 deadline miss 减少 40%"

## [Task2A 知识缺口挖掘] 已检查方向记录 — 2026-07-04 20:04
- **本轮结果**：无评分 ≥ 14 的知识缺口，跳过新章节创建
- **已检查方向**（避免下轮重复）：
  1. AOSP system services 全覆盖审计：ActivityManagerService / WindowManagerService / PackageManagerService / NotificationManagerService / JobSchedulerService / PowerManagerService / ConnectivityManagerService / TelephonyManagerService / SensorService / LocationManagerService / AlarmManagerService / AudioManagerService / ContentService / StorageManagerService / MediaService — 全部已覆盖
  2. BatteryStatsService × PowerStatsService 功耗归因全链路：已由 §11.8（Tare+电池统计源码闭环）、§25.16（ADPF PowerMonitor）、§26.20（Battery Historian 集成）深度覆盖（48 文件命中）
  3. AI Agent 端侧内存管理：已由 §5.20（GenAI 集成）、§5.21（跨 App Agent 系统原语）、§5.27（端侧 LLM 能效）、§22.9（端侧 LLM 内存管理）覆盖
  4. Native Hook 技术体系：已由 §14.13（Hook 基础设施）深度覆盖（23 文件命中）
  5. Thread governance / 线程治理：已由 §20.1（线程与 FD 监控治理）、§21.16（线程池与并发调度）、§5.18（CPU Cache 友好代码）覆盖
  6. Perfetto SQL 场景化速查：已由 §13.8（输入延迟 SQL）、§13.10（SQL 实战手册）、§13.11（SPAN_JOIN）、§13.13（CPU 频率 DVFS）、§13.14（DataGrid+Jank CUJ）、§13.15（BufferQueue 阻塞）覆盖；FrameTimeline SQL 补充为 Task2B 内容改进项
  7. 低内存设备性能策略：研究素材不足（score 11/20），material richness 仅 2/5
  8. Crash 现场持久化可靠性：研究素材不足（score 10/20），且与 §20.2/§20.3 高度重叠
  9. Android 文件加密 FBE 存储性能：研究素材不足（score 10/20）
  10. SELinux audit 性能影响：过于 niche（score 7/20）
  11. OTA/UpdateEngine 性能：已由 §6.1 存储架构提及，系统级非 App 性能主线
  12. VpnService 性能：过于 niche（score < 10/20）
  13. Wear OS / Android TV 性能：非本书 App 性能主线（score < 11/20）
  14. Compose Multiplatform / KMP：非 Android 特定性能（score 10/20）
  15. Clippings 三本参考书全覆盖交叉验证：ch20（18 节）/ch21（16 节）/ch22（30 节）/ch23（16 节）/ch24（20 节）/ch25（22 节）/ch26（24 节）— 参考书知识点已充分映射
  16. research-gaps.md 盲区（FrameTimeline SQL + 低内存设备）：均为内容改进需求（Task2B），非新章节缺口
  17. suggestions.md Task9 审查建议（VSync 三组件拆分、FrameTimeline SQL、AI 调度帧率影响等）：均为现有章节内容改进（Task2B）
  18. DeepResearch 最新文章（2026-07-04）：binder death notification batch、heapprofd 部署、lmkd procs_prio batch、modular startup dependency graph — 全部映射到现有章节

- **全书规模**：589 节（finalized 233 / ready-for-review 194 / draft 12），0 个空 draft
- **结论**：本书已高度完备，下一阶段建议集中精力在 Task2B 内容回炉和质量提升
