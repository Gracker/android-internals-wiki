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
- [7.10 图片加载与 Bitmap 性能优化](10-image-bitmap-performance.md)
- [7.11 WebView 渲染性能与优化](11-webview-performance.md)
- [7.12 View 体系性能优化：布局层级、inflate 与 measure/layout 开销](12-view-layout-performance.md)
- [7.13 SystemUI 性能分析](13-systemui-performance.md)
- [7.14 GAPS：Android 动态分析目标可达性路径重建](14-gaps-dynamic-analysis.md)
- [7.15 场景化性能作战手册](15-scenario-playbooks.md)
- [7.16 功耗、温控与卡顿联合排查](16-power-thermal-jank-playbook.md)
- [7.17 FragmentTransaction 提交引发的卡顿](17-fragmenttransaction-commit-jank.md)
- [7.18 HWC Overlay 合成降级分析](18-hwc-overlay-composition-downgrade.md)
- [7.19 Accessibility 链路性能](19-accessibility-manager-performance.md)
- [7.20 ContentCapture 与 Autofill 性能](20-contentcapture-autofill-performance.md)

## 阅读建议

- 系统学习流畅性时，按 `7.1 → 7.2 → 7.3` 阅读，建立帧时间、根因和证据之间的关系。
- 排查线上卡顿时，可从 `7.3`、`7.4`、`7.6` 和 `7.15` 选择与现场最接近的入口。
- 分析具体 UI 技术栈时，按问题进入 `7.7` 到 `7.13`，分别检查 Compose、RecyclerView、图片、WebView、View 布局和 SystemUI。
- 卡顿与系统状态同时变化时，结合 `7.16` 的功耗、温控和调度证据判断。
- 卡顿集中在事务提交、合成策略或系统辅助服务时，分别查阅 `7.17` 到 `7.20`。
- 需要将动态分析结果映射到 Perfetto 证据时，阅读 `7.14`，再结合第 13 章的工具说明执行采集。
