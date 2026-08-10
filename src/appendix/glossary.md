# 附录 E：术语表（中英对照）

> 表格只对照通用概念。Choreographer、SurfaceFlinger、Binder、VSync、Perfetto、Systrace 等 Android 专有名词在中英文内容中均保留原文。

| 中文 | English | 说明 |
|------|---------|------|
| 卡顿 | Jank / Stutter | 帧未在预期时间内完成渲染 |
| 流畅性 | Smoothness | 用户感知的界面流畅程度 |
| 响应速度 | Responsiveness | 用户操作到界面响应的延迟 |
| 冷启动 | Cold Start / Cold Launch | 进程不存在时的启动 |
| 温启动 | Warm Start | 进程存在但 Activity 需重建 |
| 热启动 | Hot Start | Activity 在栈中直接恢复 |
| 掉帧 | Dropped Frame / Frame Drop | 帧未能在 VSync 截止时间前完成 |
| 过度绘制 | Overdraw | 同一像素在一帧内被多次绘制 |
| 大小核 | big.LITTLE / DynamIQ | ARM 异构多核架构 |
| 功耗 | Power Consumption | 设备电量消耗 |
| 帧率 | Frame Rate (FPS) | 每秒渲染帧数 |
| 刷新率 | Refresh Rate (Hz) | 屏幕每秒刷新次数 |
| 渲染流水线 | Rendering Pipeline | 从 View 绘制到屏幕显示的完整流程 |
| 合成 | Composition | SurfaceFlinger 将多个 Layer 合成为最终画面 |
| 进程优先级 | Process Priority / oom_adj | 决定进程被回收顺序的优先级值 |
| 杀进程 | Process Kill / LMK | 低内存时系统回收进程 |
| 链式唤醒 | Chained Wakeup | 一个进程唤醒触发多个后续唤醒 |
