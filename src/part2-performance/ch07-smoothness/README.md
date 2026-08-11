# 第 7 章：流畅性

用户口中的“卡”可能对应掉帧、输入延迟、跨进程阻塞、渲染链路退化、功耗与温控限制，也可能已经接近 ANR。相似的主观感受背后，系统行为和修复位置可能完全不同。

平台基线为 Android 17 / API 37 / `android-17.0.0_r1`，内容依次说明帧时间语义、诊断证据和常见优化边界。涉及调度、功耗和温控时，内核基线为 `android17-6.18-2026-06_r6`。分析目标是把“界面感觉很卡”转化为可复现、可归因、可验证的结论。

## 内容索引

- [7.1 卡顿的定义与分类](01-jank-definition.md)
- [7.2 卡顿原因体系](02-jank-causes.md)
- [7.3 卡顿分析方法](03-jank-methodology.md)
- [7.4 典型场景分析](04-typical-scenarios.md)
- [7.5 优化策略](05-optimization.md)
- [7.6 案例集](06-case-studies.md)
- [7.7 Jetpack Compose 性能优化](07-compose-performance.md)
- [7.8 RecyclerView 列表滑动性能深度优化](08-recyclerview-performance.md)
- [7.9 感知流畅性：步幅波动与无掉帧卡顿](09-perceived-smoothness.md)
- [7.10 View 体系性能优化：布局层级、inflate 与 measure/layout 开销](10-view-layout-performance.md)
- [7.11 SystemUI 性能分析](11-systemui-performance.md)
- [7.12 HWC Overlay Plane 与合成降级排查](12-hwc-overlay-composition-downgrade.md)
- [7.13 AccessibilityManagerService 与无障碍服务性能影响](13-accessibility-manager-performance.md)
- [7.14 ContentCaptureService 与 Autofill 性能影响](14-contentcapture-autofill-performance.md)

## 阅读建议

- 系统学习流畅性时，按 `7.1 → 7.2 → 7.3` 阅读，建立帧时间、根因和证据之间的关系。
- 排查线上卡顿时，从 `7.3`、`7.4` 和 `7.6` 选择与现场最接近的入口。
- 分析具体 UI 技术栈时，进入 `7.7`～`7.11`，分别检查 Compose、RecyclerView、感知节奏、View 布局和 SystemUI。
- 卡顿与功耗、温控同时变化时，结合 25.1 与 25.28 的功耗账本、thermal 和调度证据判断。
- 卡顿集中在页面事务、图片、WebView 或显示合成时，分别查阅 22.12、22.35、22.7/18.13 与 `7.12`。
- 无障碍、ContentCapture 或 Autofill 改变页面成本时，分别查阅 `7.13`、`7.14`；目标方法自动触达工具 GAPS 已归入 14.28。
