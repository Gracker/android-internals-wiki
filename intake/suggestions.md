## [Task9 Deep Review] 4.7 16KB Page Size 与 Android 性能 — 2026-06-24
- **类型**：数据支撑
- **位置**：量化性能数据部分
- **问题**：缺少具体设备型号和测试条件，引用的 Google 官方数据缺乏完整样本说明
- **建议**：补充具体测试环境（如 Pixel 8 Pro build fingerprint）、测试次数统计区间、冷启动复现方法

## [Task9 Deep Review] 7.7 Jetpack Compose 性能优化 — 2026-06-24
- **类型**：知识盲区
- **位置**：跨平台适配部分
- **问题**：缺少对不同 Compose 编译后 bytecode 大小的具体影响分析
- **建议**：补充 Compose 编译产物大小对比、实际设备上的包体积膨胀率数据
## [Task6 Review] 8.10 ProfilingManager 系统触发式性能追踪 — 2026-06-24
- **类型**：技术一致性错误（B-class）
- **位置**：trigger table（正文表格）+ version table（版本演进表）+ outline（要点大纲）
- **问题**：TRIGGER_TYPE_COLD_START 和 TRIGGER_TYPE_APP_COMPAT 的常量值在全文三处给出三组不同的值：
  - outline: `COLD_START=11`、`APP_COMPAT=10`
  - trigger table: `COLD_START = 11`、`APP_COMPAT = 11`（两个不同 trigger 同值，不可能）
  - version table: `COLD_START=10`、`APP_COMPAT=11`
- **建议**：查阅 AOSP `packages/modules/Profiling/framework/java/android/os/ProfilingTrigger.java` 中的常量定义，统一全文三处引用。这是技术事实错误，不能靠写作层面解决。
- **review 日志**：logs/review/2026-06-24-04-review.md

## [Task9 闲时抽检] 25.4 WorkManager 实战与后台任务调度 — 2026-06-24
- **类型**：版本/术语准确性
- **位置**：§停止原因与回归守门 末段
- **问题**：章节称"如果任务频繁超时，系统可能把 App 放入 restricted standby bucket"。但 Android App Standby Buckets 中，"Restricted"桶需要用户主动操作，系统不会自动将 App 放入 Restricted 桶。系统可根据使用模式自动降级到"Rare"或"Limited"桶。
- **建议**：将"restricted standby bucket"改为"更低的 standby bucket（如 Rare 或 Limited）"，或删除"restricted"这一特指，仅保留"系统可能限制 App 的后台执行能力"。

## [Task2B 修复完成] 8.10 ProfilingManager 系统触发式性能追踪 — 2026-06-24
- **状态**：已修复
- **修复内容**：
  - COLD_START 常量值修正：outline 中 `COLD_START=11` → `10`，trigger table 中 `TRIGGER_TYPE_COLD_START = 11` → `10`，与 AOSP `android-17.0.0_r1` 源码一致
  - APP_COMPAT 常量值修正：outline 中 `APP_COMPAT=10` → `11`，与源码一致
  - 版本演进表中 COLD_START=10 / APP_COMPAT=11 已确认正确，无需修改
  - Frontmatter 去重：删除重复的 `task6_review_notes`
- **章节状态**：task2b_result/task2b_state → fixed，pipeline_stage → task6_pending（等待下一轮 Task6/Task9 review）
- **修复日志**：logs/review/2026-06-24-04-review.md
