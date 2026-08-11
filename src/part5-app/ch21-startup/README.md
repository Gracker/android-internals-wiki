# 第 21 章：启动优化

启动优化需要同时控制进程创建、组件初始化、主线程调度、首帧渲染和后台任务的开销。指标应区分冷启动、温启动、热启动，以及用户可感知的页面就绪时间。

第 8 章分析系统侧的响应速度与启动链路；这里聚焦 App 侧的任务编排、Profile、监控和不同设备等级下的启动策略。

## 内容索引

- [21.1 启动链路分析（App 视角）](01-startup-analysis.md)
- [21.2 启动框架设计与任务编排](02-startup-framework.md)
- [21.3 ContentProvider 启动治理](03-contentprovider-optimization.md)
- [21.4 Baseline Profile 与 Startup Profile 实战](04-baseline-profile-practice.md)
- [21.5 Splash Screen 与感知启动速度](05-splash-screen.md)
- [21.6 延迟初始化与按需加载](06-lazy-initialization.md)
- [21.7 多进程启动优化](07-multiprocess-startup.md)
- [21.8 启动监控与度量](08-startup-monitoring.md)
- [21.9 Privacy Sandbox 退场与广告 SDK 启动治理](09-sdk-runtime-ad-sdk-startup.md)
- [21.10 云端 Profile、DM 文件与安装后编译优化](10-cloud-profile-dm-install-compile.md)
- [21.11 ART GC 抑制与启动性能优化](11-art-gc-suppression-startup-performance.md)
- [21.12 依赖注入框架性能：Dagger、Hilt、Koin 启动开销与优化](12-di-framework-performance.md)
- [21.13 Compose 首次组合开销与启动性能](13-compose-first-composition-startup.md)
- [21.14 线程池与并发调度性能实战](14-thread-pool-concurrency-performance.md)
- [21.15 缓存优化实战：冷热端分离、重排序与 CPU 缓存命中率提升](15-cache-optimization-cpu-locality.md)
- [21.16 设备分级性能策略实战](16-device-tier-performance-strategy.md)

## 阅读建议

- 排查单个启动阶段时，可直接进入对应条目。
- 建立启动优化流程时，先读 21.1、21.2 和 21.8。
- Profile 的生成、设备端编译与构建期 DEX layout 分别由 21.4、21.10 串联说明。
- 启动复盘模板与 Android 15+ 系统启动记录统一收在 21.8。
