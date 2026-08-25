# 第 7 章：流畅性

用户口中的“卡”可能对应掉帧、输入延迟、跨进程阻塞、渲染链路退化、功耗或温控限制，也可能已经接近 ANR（Application Not Responding，应用无响应）。相似的主观感受背后，系统行为和需要调整的位置可能完全不同。

平台基线为 Android 17 / API 37 / `android-17.0.0_r1`，内容依次说明帧时间的含义、诊断证据和常见优化边界。涉及调度、功耗和温控时，内核基线为 `android17-6.18-2026-06_r6`。分析目标是把“界面感觉很卡”转化为能够复现、定位原因并验证的结论。

## 内容索引

- [7.1 卡顿定义、分类与原因体系](01-jank-definition-causes.md)
- [7.2 卡顿分析方法、典型场景与案例](02-jank-methodology-scenarios-cases.md)
- [7.3 感知流畅性：步幅波动与无掉帧卡顿](03-perceived-smoothness.md)
- [7.4 SystemUI 性能分析](04-systemui-performance.md)
- [7.5 HWC Overlay Plane 与合成降级排查](05-hwc-overlay-composition-downgrade.md)
- [7.6 Accessibility、ContentCapture 与 Autofill 性能](06-accessibility-contentcapture-autofill.md)

## 阅读建议

- 系统学习流畅性时，按 `7.1 → 7.2` 阅读，建立帧时间、根因和证据之间的关系。
- 排查线上卡顿时，从 `7.2` 的证据流程与 `7.3` 的感知节奏选择入口；若已定位到具体 UI 组件，再进入 22.1～22.3。
- 分析具体 UI 技术体系时，View、Compose 与 RecyclerView 分别进入 22.1、22.3、22.2；第 7 章保留 `7.3` 的感知节奏和 `7.4` 的 SystemUI 系统链路。
- 卡顿与功耗、温控同时变化时，结合 25.1 与 25.11 的功耗归因记录、thermal（温控）和调度证据判断。
- 卡顿集中在页面与窗口变化、图片、WebView 或显示合成时，分别查阅 22.10、22.5、22.6/18.9 与 `7.5`。
- 无障碍、ContentCapture（内容捕获）或 Autofill（自动填充）改变页面开销时，查阅 `7.6`；用于自动寻找目标方法调用路径的 GAPS 工具见 14.13。
