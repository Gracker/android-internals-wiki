# 第 21 章：启动优化

启动优化需要同时控制进程创建、组件初始化、主线程调度、首帧渲染和后台任务的开销。首帧是应用窗口第一次显示 UI 的画面；它出现后，页面仍可能没有数据或不能交互。指标应区分冷启动、温启动和热启动：冷启动从没有应用进程开始；温启动复用部分状态，常见情形是进程仍在而 Activity 需要重建；热启动把仍在内存中的 Activity 带回前台。页面可见与业务可用也要分开计时。

第 8 章分析系统侧的响应速度与启动路径；这里聚焦 App 侧的任务执行顺序、Profile、监控，以及不同设备档位下的启动策略。

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

## 术语提示

- **任务编排**：明确每项启动任务何时执行、依赖谁、运行在哪个线程，以及失败或超时后怎样继续。
- **Profile**：这里指交给构建工具或 ART 的热点代码信息，与用户资料无关。Baseline Profile 主要指导设备端预编译，Startup Profile 主要调整启动代码在 DEX 中的排列。
- **DM 与 DEX layout**：`.dm` 是与 APK 对应的 Dex Metadata 容器，可携带 Profile 等编译输入；DEX layout 是类和方法在 DEX 文件中的物理排列，会影响启动阶段的读取与缺页成本。
- **GC 抑制**：在条件允许时避开或推迟启动敏感阶段的垃圾回收，不等于永久关闭 GC。
- **冷热端与设备分级**：“热”指启动时高频访问的代码或数据，“冷”指低频部分，与设备温度无关；设备分级则按内存、CPU、系统能力等条件选择不同预算和策略。

## 阅读建议

- 排查单个启动阶段时，可直接进入对应条目。
- 建立启动优化流程时，先读 21.1、21.2 和 21.8。
- 先用 21.4 掌握 Baseline/Startup Profile 的生成与验证，再用 21.10 追踪 Cloud Profile、DM 交付、设备端编译和 DEX layout。
- 启动复盘模板与 Android 15+ 的 `ApplicationStartInfo` 系统启动记录都在 21.8。
- 维护广告 SDK 或旧 Privacy Sandbox 接入时，结合 21.9 核对 Android 17 的退场边界与普通 SDK 回退路径。
