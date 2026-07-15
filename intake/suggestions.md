## [Task9 Deep Review] 13.25 源码调研：PerfDog 的 Android 平台 GPU/性能采集底层数据源 — 2026-07-15
- **类型**：源码准确性
- **位置**：SurfaceFlinger 帧统计实现路径
- **问题**：文中提到 "frameworks/native/services/surfaceflinger/" 作为 SurfaceFlinger 帧统计源码路径，但 android-17.0.0_r1 中 SurfaceFlinger 的实际主要实现路径是 "SurfaceFlinger::dumpFrameEventsLocked()"
- **建议**：建议明确标注具体的类文件路径，如 "frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp" 及相关类文件

## [Task9 Deep Review] 13.25 源码调研：PerfDog 的 Android 平台 GPU/性能采集底层数据源 — 2026-07-15
- **类型**：版本差异
- **位置**：Vulkan 版本支持状态
- **问题**：文中提到 "ANGLE 在 Android 17 的 AOSP build 中的 Vulkan 后端基于 Vulkan 1.3 API 功能集，Vulkan 1.4 规范发布于 2024 年底，截止 android-17.0.0_r1 尚未被 AOSP ANGLE 作为默认目标"，但未明确说明 android-17.0.0_r1 的 AOSP 是否支持 Vulkan 1.4
- **建议**：明确标注 Vulkan 版本边界和具体支持状态
## [Task6 抽检] 5.7 CPU 相关的版本演进 — 2026-07-15
- **类型**：需确认（版本基线）
- **位置**：frontmatter sources 7 条 AOSP 路径 + 正文 [已验证] 标注 3 处 + 参考资料段
- **问题**：全章节 AOSP 源码引用锚定 android-16.0.0_r1（共 11 处），0 处 android-17.0.0_r1。违反版本基线规则「源码链接必须锚定 android-17.0.0_r1」。last_verified_against 字段也写的是 "AOSP android-16.0.0_r1"。
- **建议**：逐条确认文件在 android-17.0.0_r1 中存在性和内容差异，更新 tag。涉及文件：UsageStatsManager.java、DeviceIdleController.java、AppStandbyController.java、JobSchedulerService.java、task_profiles.json、PerformanceHintManager.java、sched.h
- **review 日志**：logs/review/2026-07-15-20-audit.md
