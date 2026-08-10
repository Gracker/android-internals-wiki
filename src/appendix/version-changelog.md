# 附录 A：Android 版本性能变更速查表

> 按 Android 版本与技术领域组织，以 Android 16/17 为基准。

| 版本 | 渲染 | 内存 | CPU/调度 | 功耗 | 存储 | 工具 |
|------|------|------|----------|------|------|------|
| Android 17 (Beta 3 · 平台稳定 · 3/26) | 应用名称隐藏<br>屏幕记录重设计<br>桌面 PiP<br>浮窗工具栏 | 每应用深色主题<br>BLE 助听器支持<br>静态 final 字段不可修改<br>**ART 分代 GC 稳定** | **lock-free MessageQueue (API 37)**<br>冒泡功能全启用<br>大屏强制可调整大小<br>**ProfilingManager 新触发器** | AlarmManager OnAlarmListener 减少唤醒锁<br>本地网络默认阻断<br>后量子密码学<br>CT 默认启用 | 14-bit RAW 相机<br>厂商自定义相机扩展<br>相机设备类型 API | DCL 保护扩展至 native 库<br>Photo Picker 可定制<br>NFC 弃用 ACTION_TAG_DISCOVERED |
| Android 16 (Baklava · 2025.06) | 自适应布局强制<br>OpenCL 驱动优化<br>自适应刷新率 | 16KB 内存页支持<br>4KB 兼容模式 | ART Java 特性支持<br>**AutoFDO 内核集成 (4.3% 冷启动↑)** | AutoFDO 集成 (4.3% 冷启动↑)<br>JobScheduler 配额优化<br>网络稳定性改进 | - | 性能一致性 API |
| Android 15 | - | 16KB 内存页引入 | - | - | - | - |
| Android 14 | - | - | - | - | - | - |
| Android 13 | - | - | - | - | - | - |
| Android 12 | FrameTimeline, BlastBQ | - | - | - | - | - |
| Android 11 | - | 冻结进程优化 | - | - | - | - |
| Android 10 | - | - | - | - | Scoped Storage | - |

> **更新说明 (2026-04-17)**:
> - **AutoFDO 新进展**: 已扩展至 android17-6.18 内核分支，带来显著性能提升
>   - 特定 benchmark 最高 **26.4%** 改善
>   - Binder 测试提升 **21%**
>   - 冷启动提升 **15-30%**（部分应用）
>   - 启动时间改善 2%，应用启动改善 4%+
> - **ART 分代 GC**: Android 17 中 Concurrent Mark-Compact collector 支持分代 GC 已稳定
> - **ProfilingManager 新触发器**: COLD_START、OOM、KILL_EXCESSIVE_CPU_USAGE
> - Jetpack Compose 1.9+ 滚动卡顿降至 0.2%
> - AGP 8.12.0 引入优化的资源压缩

> **更新说明 (2026-04-01)**:
> - Android 17 Beta 3 已达平台稳定性 (2026-03-26)，API 锁定
> - 新增 lock-free MessageQueue (API 37)，影响线程模型
> - AutoFDO 确认扩展至 android17-6.18 内核
> - AlarmManager 新增 OnAlarmListener 重载，减少唤醒锁
> - 大屏强制可调整大小 (sw≥600dp)，Game 豁免
> - 静态 final 字段通过反射/JNI 修改将抛异常
> - 本地网络默认阻断，需运行时权限

> **更新说明 (2026-03-30)**:
> - Android 16: ART 更新、AutoFDO 集成、16KB 内存页优化
> - 注：AutoFDO 带来 4.3% 冷启动改善，2.1% 更快启动时间
