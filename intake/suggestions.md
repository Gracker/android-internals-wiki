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