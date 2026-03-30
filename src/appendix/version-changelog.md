# 附录 A：Android 版本性能变更速查表

> 按版本 × 领域矩阵组织，待填充。当前以 Android 16/17 为基准版本。

| 版本 | 渲染 | 内存 | CPU/调度 | 功耗 | 存储 | 工具 |
|------|------|------|----------|------|------|------|
| Android 17 (当前 Beta 3) | 应用名称隐藏<br>屏幕记录重设计<br>浮窗工具栏 | 每应用深色主题<br>蓝牙 LE 音助听器支持 | 冒泡功能全启用<br>桌面 PiP<br>减少空闲唤醒警报 | 后量子密码学<br>VPN 应用排除 | 14-bit RAW 相机 | - |
| Android 16 (Baklava) | 自适应布局强制<br>OpenCL 驱动优化 | 16KB 内存页支持<br>4KB 兼容模式 | ART Java 特性支持 | AutoFDO 集成<br>网络稳定性改进 | - | - |
| Android 15 | - | 16KB 内存页 | - | - | - | - |
| Android 14 | - | - | - | - | - | - |
| Android 13 | - | - | - | - | - | - |
| Android 12 | FrameTimeline, BlastBQ | - | - | - | - | - |
| Android 11 | - | 冻结进程优化 | - | - | - | - |
| Android 10 | - | - | - | - | Scoped Storage | - |

> **更新说明 (2026-03-30)**:
> - Android 17: 平台稳定性已达成，新增多项特性
> - Android 16: ART 更新、AutoFDO 集成、16KB 内存页优化
> - 注：AutoFDO 带来 4.3% 冷启动改善，2.1% 更快启动时间
