# 第 21 章：启动优化

启动优化需要同时控制进程创建、组件初始化、主线程调度、首帧渲染和后台任务的开销。首帧是应用窗口第一次显示 UI 的画面；它出现后，页面仍可能没有数据或不能交互。指标应区分冷启动、温启动和热启动：冷启动从没有应用进程开始；温启动复用部分状态，常见情形是进程仍在而 Activity 需要重建；热启动把仍在内存中的 Activity 带回前台。页面可见与业务可用也要分开计时。

第 8 章分析系统侧的响应速度与启动路径；这里聚焦 App 侧的任务执行顺序、Profile、运行时分配、首帧呈现与专项 SDK 治理。跨场景设备分级策略移入 15.8，通用缓存与数据局部性统一由 5.8 承载。

## 内容索引

- [21.1 App 启动路径、监控与度量](01-app-startup-path-monitoring.md)
- [21.2 启动任务编排、延迟初始化与并发调度](02-startup-task-lazy-concurrency.md)
- [21.3 ContentProvider 与多进程启动治理](03-contentprovider-multiprocess-startup.md)
- [21.4 Baseline、Startup 与 Cloud Profile 编译优化](04-baseline-startup-cloud-profile.md)
- [21.5 Splash Screen 与感知启动速度](05-splash-screen.md)
- [21.6 Privacy Sandbox 退场与广告 SDK 启动治理](06-sdk-runtime-ad-sdk-startup.md)
- [21.7 ART GC 启动期开销与分配治理](07-art-gc-startup-allocation-governance.md)
- [21.8 依赖注入框架性能：Dagger/Hilt/Koin 启动开销与优化](08-di-framework-performance.md)
- [21.9 Compose 首次组合开销与启动性能](09-compose-first-composition-startup.md)

## 术语提示

- **任务编排**：明确每项启动任务何时执行、依赖谁、运行在哪个线程，以及失败或超时后怎样继续。
- **Profile**：这里指交给构建工具或 ART 的热点代码信息，与用户资料无关。Baseline Profile 主要指导设备端预编译，Startup Profile 主要调整启动代码在 DEX 中的排列。
- **DM 与 DEX layout**：`.dm` 是与 APK 对应的 Dex Metadata 容器，可携带 Profile 等编译输入；DEX layout 是类和方法在 DEX 文件中的物理排列，会影响启动阶段的读取与缺页成本。
- **GC 分配治理**：减少首帧前对象图、分配速率和 live set，让 ART 更少在启动关键路径达到回收条件；不等于关闭 GC。

## 阅读建议

- 建立启动优化流程时，先读 21.1，再按 21.2 → 21.3 → 21.4 收敛任务、自动组件和编译状态。
- 处理用户看到的启动交接或第三方广告入口时，分别阅读 21.5、21.6。
- Baseline、Startup 与 Cloud Profile 的生成、DM 交付、设备端编译和 DEX layout 统一见 21.4。
- 启动复盘模板与 Android 15+ 的 `ApplicationStartInfo` 系统启动记录都在 21.1。
- 维护广告 SDK 或旧 Privacy Sandbox 接入时，结合 21.6 核对 Android 17 的退场边界与普通 SDK 回退路径。
- 排查启动期分配、DI 容器或 Compose 首次组合时，依次阅读 21.7、21.8、21.9；业务缓存和设备策略分别见 5.8、15.8。
