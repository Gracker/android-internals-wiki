# [研究] Android 输入管线延迟分解：从触控到帧上屏的全链路量化

- **来源**: source.android.com/docs/core/interaction/input + AOSP Choreographer.java + developer.android.com/reference/android/view/Choreographer
- **作者/机构**: AOSP / Google
- **日期**: 2026-04-05
- **四维评分**: 相关性 5/5 · 技术深度 4/5 · 时效性 3/5 · 可验证性 5/5 · **总分 17/20**
- **映射章节**: 3.4 输入延迟与预测输入技术 / 3.1 Input 事件分发全流程
- **映射锚点**: 输入管线各阶段延迟、Choreographer CALLBACK_INPUT 优先级、VSYNC 同步延迟、InputChannel socketpair 通信、触控响应时间定义
- **摘要**: Android 输入延迟由硬件延迟（触控IC到内核驱动）+ 系统延迟（EventHub到InputReader到InputDispatcher到InputChannel socketpair）+ 应用延迟（Choreographer CALLBACK_INPUT到CALLBACK_TRAVERSAL到RenderThread）+ 显示延迟（SurfaceFlinger 合成到HAL到LCD）四段组成。UX 研究表明小于100ms 感知为即时响应，典型 Android 管线至少 2 帧延迟（约33ms@60Hz / 约17ms@120Hz）。

### 关键发现

1. **输入管线六阶段**: 物理设备 -> Linux 内核驱动(evdev) -> EventHub -> InputReader(解码为 Android 事件) -> InputDispatcher(路由到目标窗口) -> InputChannel(socketpair IPC) -> App UI 线程。每阶段引入的延迟可通过 Perfetto trace 精确度量。

2. **Choreographer 回调严格顺序**: CALLBACK_INPUT -> CALLBACK_ANIMATION -> CALLBACK_INSETS_ANIMATION -> CALLBACK_TRAVERSAL -> CALLBACK_COMMIT。输入事件保证在帧回调之前处理完毕，不会与渲染并发。这意味着如果 CALLBACK_INPUT 处理耗时过长，会直接压缩后续 measure/layout/draw 时间。

3. **VSYNC 同步引入的固有延迟**: 输入事件在 VSYNC 到来前被排队，VSYNC 到来时才触发 Choreographer。这引入最多一个 VSYNC 周期的等待（16.6ms@60Hz / 8.3ms@120Hz）。VSYNC offset（VSYNC-app 和 VSYNC-sf 的时间差）是缓解此延迟的关键机制。

4. **InputChannel 使用 socketpair 而非 Binder**: InputDispatcher 与 App 之间的通信使用 socketpair 封装的 InputChannel，而非 Binder IPC。这避免了 Binder 线程池的竞争，但仍然是跨进程通信（system_server 到 app 进程）。

5. **触控响应时间定义**: 从用户手指离开屏幕到 App 渲染出反应帧的时间。小于100ms 感知为即时（UX 研究）。典型 Android 实现至少 2 帧：帧 1 处理输入+渲染，帧 2 SurfaceFlinger 合成+显示。

### 可直接引用段落

> Input events that arrive before a VSYNC signal are queued and processed when the VSYNC event occurs. This inherent synchronization can introduce a delay of up to one VSYNC interval (e.g., 16.6ms at 60Hz) before the input is visually reflected.

> The Choreographer processes input callbacks before animation and traversal. Any delay in these callbacks, or if the main thread is busy, can increase the time Choreographer spends processing a frame, leading to skipped frames and increased latency.

> Android has introduced VSYNC offsets to mitigate latency. This technique reduces input-to-display latency by making app and composition signals relative to the hardware VSYNC. With VSYNC offsets, SurfaceFlinger receives the buffer and composites the frame while the app simultaneously processes the input and renders the frame.

### 与 queue.json 联动
- 素材路径建议：补充到 §3.4（管线延迟分解）和 §3.1（Input 分发链路回顾）
- 交叉引用：§2.3 VSync 机制 / §2.4 Choreographer / §2.6 SurfaceFlinger
