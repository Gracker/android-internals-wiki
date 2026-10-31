# 中文改写抽检 · 2026-10-31

- 提交数: 15
- 生成于: 2026-10-31T23:15:19.881080+08:00

## 1. 7.5 HWC Overlay Plane 与合成降级排查

- commit: `63238516dcba`
- 文件: `src/part2-performance/ch07-smoothness/05-hwc-overlay-composition-downgrade.md`
- run_id: `20261031-223019-cn-rewrite-7041be2c6d67c275`
- compare: gloss_per_1k 11.09→10.8, neg_per_1k 2.86→0.0, regloss 0→0, women 15→19, pass=True

## 2. 8.1 响应速度原理、场景与案例

- commit: `9d5fbe243b86`
- 文件: `src/part2-performance/ch08-responsiveness/01-responsiveness-principles-scenarios-cases.md`
- run_id: `20261031-220019-cn-rewrite-6eb000fd3b542737`
- compare: gloss_per_1k 3.96→3.93, neg_per_1k 2.37→0.06, regloss 0→0, women 15→23, pass=True

## 3. 6.4 vold、MediaProvider 与 FUSE：共享存储 I/O 路径

- commit: `7c247ca29834`
- 文件: `src/part1-fundamentals/ch06-storage/04-vold-mediaprovider-fuse.md`
- run_id: `20261031-213020-cn-rewrite-3327e53be28ccc88`
- compare: gloss_per_1k 9.95→9.74, neg_per_1k 2.16→0.16, regloss 1→1, women 16→16, pass=True

## 4. 6.1 Android 存储架构

- commit: `e3b00a45a426`
- 文件: `src/part1-fundamentals/ch06-storage/01-storage-architecture.md`
- run_id: `20261031-210019-cn-rewrite-1f93810e4fe0d809`
- compare: gloss_per_1k 12.19→12.08, neg_per_1k 2.85→0.23, regloss 2→2, women 24→26, pass=True

## 5. 7.2 卡顿分析方法、典型场景与案例

- commit: `76571bbbfcfb`
- 文件: `src/part2-performance/ch07-smoothness/02-jank-methodology-scenarios-cases.md`
- run_id: `20261031-203019-cn-rewrite-1099e59d922bd79a`
- compare: gloss_per_1k 17.46→17.39, neg_per_1k 1.34→0.56, regloss 10→10, women 30→29, pass=True

## 6. 24.11 BluetoothSocket read

- commit: `771cfc97cbbc`
- 文件: `src/part5-app/ch24-io-network/11-bluetoothsocket-read-disconnect.md`
- run_id: `20261031-183020-cn-rewrite-fd460c7bc206b6ee`
- compare: gloss_per_1k 2.28→2.25, neg_per_1k 2.47→0.0, regloss 0→0, women 16→19, pass=True

## 7. 2.6 文字渲染性能

- commit: `92537c10e75e`
- 文件: `src/part1-fundamentals/ch02-rendering/06-text-rendering-performance.md`
- run_id: `20261031-170020-cn-rewrite-fd3b018ba84f7ec3`
- compare: （缺）

## 8. 23.7 内存监控与线上治理

- commit: `6941c2d7ff79`
- 文件: `src/part5-app/ch23-memory-practice/07-memory-monitoring.md`
- run_id: `20261031-163020-cn-rewrite-5f76066e7fbdbeeb`
- compare: gloss_per_1k 8.33→8.1, neg_per_1k 1.14→0.18, regloss 0→0, women 9→11, pass=True

## 9. 2.7 GPU 渲染与图形 API 选型

- commit: `56d84d7b4bbe`
- 文件: `src/part1-fundamentals/ch02-rendering/07-gpu-rendering-graphics-api.md`
- run_id: `20261031-130020-cn-rewrite-3d5d14f889e56553`
- compare: gloss_per_1k 16.31→16.19, neg_per_1k 1.39→0.07, regloss 8→7, women 19→26, pass=True

## 10. 1.19 Android 显示架构与 WindowManager

- commit: `2070bfd61806`
- 文件: `src/part1-fundamentals/ch01-architecture/19-display-windowmanager-architecture.md`
- run_id: `20261030-060020-cn-rewrite-f805dc056a83060c`
- compare: gloss_per_1k 6.09→6.03, neg_per_1k 1.98→0.16, regloss 0→0, women 36→43, pass=True

## 11. 2.14 多窗口、PiP 与桌面模式渲染管线

- commit: `49c388060039`
- 文件: `src/part1-fundamentals/ch02-rendering/14-multiwindow-desktop-rendering.md`
- run_id: `20261030-020020-cn-rewrite-dfbeafab6f7b3140`
- compare: gloss_per_1k 12.41→12.0, neg_per_1k 0.82→0.13, regloss 2→0, women 12→24, pass=True

## 12. 22.20 Android 17 EyeDropper：系统取色、截图边界与跨设备同步

- commit: `34d0fdcf06ea`
- 文件: `src/part5-app/ch22-rendering-practice/20-android17-eyedropper.md`
- run_id: `20261029-193020-cn-rewrite-9fb0a4aee4279eec`
- compare: gloss_per_1k 1.14→1.06, neg_per_1k 5.99→0.79, regloss 0→0, women 0→10, pass=True

## 13. 第10章 内存性能·章首

- commit: `4596e7bb2949`
- 文件: `src/part2-performance/ch10-memory-perf/README.md`
- run_id: `20261029-013020-cn-rewrite-57196442cb5d86ef`
- compare: gloss_per_1k 17.6→15.52, neg_per_1k 3.91→2.39, regloss 1→0, women 0→6, pass=True

## 14. 26.8 Android Vitals 与 Play Console 质量指标归因

- commit: `ba776fed612f`
- 文件: `src/part5-app/ch26-observability/08-android-vitals-play-console-quality.md`
- run_id: `20261028-210019-cn-rewrite-127f8f36f4b825e6`
- compare: gloss_per_1k 6.56→6.07, neg_per_1k 7.81→1.31, regloss 1→1, women 0→23, pass=True

## 15. 25.6 Hybrid/WebView 功耗与原生化取舍

- commit: `9b2c4dc64ec4`
- 文件: `src/part5-app/ch25-power-size/06-hybrid-webview-power.md`
- run_id: `20261028-203019-cn-rewrite-ffa53e578db11b3b`
- compare: gloss_per_1k 8.35→7.66, neg_per_1k 8.12→0.43, regloss 0→0, women 0→14, pass=True
