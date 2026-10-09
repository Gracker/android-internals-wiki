# 中文改写抽检 · 2026-10-09

- 提交数: 30
- 生成于: 2026-10-09T23:15:33.960258+08:00

## 1. 13.2 Android 软件、离屏与混合渲染路径

- commit: `31f3807a71be`
- 文件: `src/part2-performance/ch13-rendering-pipelines/02-android-software-offscreen-mixed-rendering.md`
- run_id: `20261009-220034-cn-rewrite-fc6999b9e232fb87`
- compare: （缺）

## 2. 16.5 性能测试最佳实践

- commit: `15d22fae9157`
- 文件: `src/part3-tools/ch16-methodology/05-testing-best-practices.md`
- run_id: `20261009-183034-cn-rewrite-05983a9cfb0b6059`
- compare: gloss_per_1k 16.25→4.13, neg_per_1k 5.42→0.34, regloss 1→0, women 0→13, pass=True

## 3. 5.4 ADPF 自适应性能框架

- commit: `07dd3ab72463`
- 文件: `src/part1-fundamentals/ch05-cpu-power/04-adpf.md`
- run_id: `20261009-180034-cn-rewrite-919d67aa730c04ff`
- compare: gloss_per_1k 15.3→7.93, neg_per_1k 4.68→0.64, regloss 0→0, women 0→8, pass=True

## 4. 22.16 WebView 性能优化实战

- commit: `ebba430b82a9`
- 文件: `src/part5-app/ch22-rendering-practice/16-webview-optimization.md`
- run_id: `20261009-173034-cn-rewrite-a96724d8e1c9f625`
- compare: gloss_per_1k 12.71→3.27, neg_per_1k 4.29→2.08, regloss 2→0, women 0→9, pass=True

## 5. 9.2 ANR 与 Kernel Trace 联合诊断

- commit: `004e3ce36a03`
- 文件: `src/part2-performance/ch09-anr/02-anr-kernel-trace-diagnosis.md`
- run_id: `20261009-163034-cn-rewrite-44ab9e51e72bc150`
- compare: gloss_per_1k 12.64→5.16, neg_per_1k 4.05→0.33, regloss 13→0, women 0→17, pass=True

## 6. 25.9 热节流适配与性能退化治理

- commit: `95b8d96666e2`
- 文件: `src/part5-app/ch25-power-size/09-thermal-throttling-performance.md`
- run_id: `20261009-160034-cn-rewrite-0e16ba0f67fea7ef`
- compare: gloss_per_1k 11.37→6.14, neg_per_1k 3.95→1.0, regloss 0→0, women 0→8, pass=True

## 7. 2.7 GPU 渲染与图形 API 选型

- commit: `81b2f3d576f9`
- 文件: `src/part1-fundamentals/ch02-rendering/07-gpu-rendering-graphics-api.md`
- run_id: `20261009-143034-cn-rewrite-3d5d14f889e56553`
- compare: gloss_per_1k 19.16→3.56, neg_per_1k 4.55→2.1, regloss 12→0, women 0→11, pass=True

## 8. 2.8 BufferQueue、Gralloc 与 Sync Fence

- commit: `90273733f80e`
- 文件: `src/part1-fundamentals/ch02-rendering/08-bufferqueue-gralloc-sync-fence.md`
- run_id: `20261009-103034-cn-rewrite-2a07f2fc9b354218`
- compare: gloss_per_1k 16.24→7.15, neg_per_1k 5.92→0.26, regloss 14→0, women 0→10, pass=True

## 9. 5.1 Linux 调度、EAS 与大小核架构

- commit: `0d35e5ae21dc`
- 文件: `src/part1-fundamentals/ch05-cpu-power/01-linux-eas-big-little-scheduling.md`
- run_id: `20261009-083034-cn-rewrite-ccf90362a9ee6732`
- compare: gloss_per_1k 13.84→5.96, neg_per_1k 4.63→1.35, regloss 8→2, women 0→13, pass=True

## 10. 6.2 文件系统与 I/O 调度

- commit: `80cd1acb14d0`
- 文件: `src/part1-fundamentals/ch06-storage/02-filesystem-io-scheduling.md`
- run_id: `20261009-080034-cn-rewrite-fcb49f1fb7e38448`
- compare: gloss_per_1k 18.38→4.83, neg_per_1k 4.65→0.35, regloss 6→0, women 0→16, pass=True

## 11. 18.1 AOSP 性能优化与 Android 版本变更

- commit: `1e7fda472c22`
- 文件: `src/part4-system/ch18-aosp/01-aosp-performance-version-changes.md`
- run_id: `20261009-150033-cn-rewrite-9a0d1d884a624159`
- compare: gloss_per_1k 11.68→5.79, neg_per_1k 5.47→0.15, regloss 14→0, women 0→21, pass=True

## 12. 15.13 Android Performance Analyzer 与 GAPS：性能追踪与目标可达性

- commit: `58f93090564a`
- 文件: `src/part3-tools/ch15-other-tools/13-performance-analyzer-gaps.md`
- run_id: `20261009-133034-cn-rewrite-6317ef1a25588724`
- compare: gloss_per_1k 18.65→10.14, neg_per_1k 5.37→2.27, regloss 1→0, women 0→6, pass=True

## 13. 26.4 A/B Test 与性能回归防护

- commit: `81d8c9492132`
- 文件: `src/part5-app/ch26-observability/04-ab-testing-regression.md`
- run_id: `20261009-130034-cn-rewrite-18098fe3b1ec8929`
- compare: gloss_per_1k 7.59→0.91, neg_per_1k 7.59→1.09, regloss 0→0, women 0→7, pass=True

## 14. 7.5 HWC Overlay Plane 与合成降级排查

- commit: `f172ecf6d6ca`
- 文件: `src/part2-performance/ch07-smoothness/05-hwc-overlay-composition-downgrade.md`
- run_id: `20261009-123034-cn-rewrite-7041be2c6d67c275`
- compare: gloss_per_1k 15.93→1.31, neg_per_1k 6.32→2.62, regloss 0→0, women 0→9, pass=True

## 15. 2.11 Frame Pacing Library 与帧节奏控制

- commit: `38d14d420e0e`
- 文件: `src/part1-fundamentals/ch02-rendering/11-frame-pacing.md`
- run_id: `20261009-120034-cn-rewrite-7aa3daab9d7cab79`
- compare: gloss_per_1k 19.94→2.53, neg_per_1k 4.71→1.12, regloss 0→0, women 0→12, pass=True

## 16. 1.2 Android 版本演进中的架构变化

- commit: `372e8ce50806`
- 文件: `src/part1-fundamentals/ch01-architecture/02-version-evolution.md`
- run_id: `20261009-113034-cn-rewrite-23ce00b21bf0c11f`
- compare: gloss_per_1k 16.11→7.82, neg_per_1k 5.22→1.79, regloss 0→0, women 0→17, pass=True

## 17. 17.11 混合栈与跨平台 APM

- commit: `0f295abd0fb5`
- 文件: `src/part3-tools/ch17-apm/11-hybrid-apm.md`
- run_id: `20261009-100034-cn-rewrite-f5f38ea519caff12`
- compare: gloss_per_1k 10.66→6.2, neg_per_1k 6.43→0.56, regloss 0→0, women 0→6, pass=True

## 18. 2.3 VSync、Choreographer 与 SurfaceFlinger 调度

- commit: `c40cefded482`
- 文件: `src/part1-fundamentals/ch02-rendering/03-vsync-choreographer-sf-scheduling.md`
- run_id: `20261009-093034-cn-rewrite-bf3a94cc77218ef2`
- compare: gloss_per_1k 12.44→11.85, neg_per_1k 2.93→1.65, regloss 12→11, women 0→31, pass=True

## 19. 15.14 Camera 性能分析工具：Perfetto、SQL 与 GFXReconstruct

- commit: `051df8729021`
- 文件: `src/part3-tools/ch15-other-tools/14-camera-performance-analysis.md`
- run_id: `20261009-073034-cn-rewrite-a2837856abfe3289`
- compare: gloss_per_1k 26.88→5.76, neg_per_1k 4.79→0.44, regloss 1→0, women 0→14, pass=True

## 20. 6.4 vold、MediaProvider 与 FUSE：共享存储 I/O 路径

- commit: `61f63177d217`
- 文件: `src/part1-fundamentals/ch06-storage/04-vold-mediaprovider-fuse.md`
- run_id: `20261009-033033-cn-rewrite-3327e53be28ccc88`
- compare: gloss_per_1k 15.15→7.19, neg_per_1k 4.73→0.23, regloss 0→0, women 0→15, pass=True

## 21. 5.8 CPU Cache 友好代码与数据布局优化

- commit: `99224210b7b2`
- 文件: `src/part1-fundamentals/ch05-cpu-power/08-cpu-cache-friendly-code-data-layout.md`
- run_id: `20261009-030033-cn-rewrite-b7df5fa77229369c`
- compare: gloss_per_1k 13.35→5.22, neg_per_1k 6.26→0.16, regloss 0→0, women 0→11, pass=True

## 22. 7.2 卡顿分析方法、典型场景与案例

- commit: `6e707d7f2dd7`
- 文件: `src/part2-performance/ch07-smoothness/02-jank-methodology-scenarios-cases.md`
- run_id: `20261009-053033-cn-rewrite-1099e59d922bd79a`
- compare: gloss_per_1k 24.47→3.11, neg_per_1k 4.77→0.85, regloss 27→0, women 0→24, pass=True

## 23. 2.9 SurfaceFlinger 合成、FrontEnd 与事务队列

- commit: `42e58086d341`
- 文件: `src/part1-fundamentals/ch02-rendering/09-surfaceflinger-frontend-transaction.md`
- run_id: `20261009-063034-cn-rewrite-fc9fdc918383fbe6`
- compare: gloss_per_1k 20.88→2.37, neg_per_1k 4.26→1.0, regloss 24→0, women 0→10, pass=True

## 24. 2.6 文字渲染性能

- commit: `54ad32780e7c`
- 文件: `src/part1-fundamentals/ch02-rendering/06-text-rendering-performance.md`
- run_id: `20261009-040034-cn-rewrite-fd3b018ba84f7ec3`
- compare: gloss_per_1k 27.03→7.33, neg_per_1k 5.22→0.28, regloss 5→0, women 0→13, pass=True

## 25. 13.1 Android View 渲染管线与分析方法

- commit: `6f4333ec1c27`
- 文件: `src/part2-performance/ch13-rendering-pipelines/01-android-view-pipeline-analysis.md`
- run_id: `20261009-023033-cn-rewrite-f5a1be37257a69c2`
- compare: gloss_per_1k 19.77→1.73, neg_per_1k 5.77→0.0, regloss 7→0, women 0→7, pass=True

## 26. 2.9 SurfaceFlinger 合成、FrontEnd 与事务队列

- commit: `82bf37b54c51`
- 文件: `（无 src）`
- run_id: `20261009-063034-cn-rewrite-fc9fdc918383fbe6`
- compare: gloss_per_1k 20.88→2.37, neg_per_1k 4.26→1.0, regloss 24→0, women 0→10, pass=True

## 27. 17.8 网络 APM 底层捕获原理

- commit: `2e53cd984880`
- 文件: `src/part3-tools/ch17-apm/08-network-apm-internals.md`
- run_id: `20261009-020033-cn-rewrite-288906d745d4b091`
- compare: gloss_per_1k 14.98→4.42, neg_per_1k 5.74→0.85, regloss 1→0, women 0→16, pass=True

## 28. 7.2 卡顿分析方法、典型场景与案例

- commit: `fcd888679753`
- 文件: `（无 src）`
- run_id: `20261009-053033-cn-rewrite-1099e59d922bd79a`
- compare: gloss_per_1k 24.47→3.11, neg_per_1k 4.77→0.85, regloss 27→0, women 0→24, pass=True

## 29. 7.1 卡顿定义、分类与原因体系

- commit: `5dec984f35c8`
- 文件: `src/part2-performance/ch07-smoothness/01-jank-definition-causes.md`
- run_id: `20261009-000034-cn-rewrite-1eb45e55e33ef560`
- compare: gloss_per_1k 28.94→9.64, neg_per_1k 4.45→0.52, regloss 20→1, women 0→20, pass=True

## 30. 2.6 文字渲染性能

- commit: `850a20081718`
- 文件: `（无 src）`
- run_id: `20261009-040034-cn-rewrite-fd3b018ba84f7ec3`
- compare: gloss_per_1k 27.03→7.33, neg_per_1k 5.22→0.28, regloss 5→0, women 0→13, pass=True
