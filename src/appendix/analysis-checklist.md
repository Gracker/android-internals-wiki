# 附录 D：性能分析 Checklist

这份 Checklist 用于在采集和归因前核对现象、范围、设备状态与证据，减少无效测试和证据缺口。

清单覆盖卡顿、启动、ANR、内存和功耗五类常见场景。每次排障前先确认对应条目，再决定需要采集的 trace、日志或系统状态。

---

## 1. 卡顿（Jank）排查清单

### 1.1 现象与范围
- [ ] **是否可稳定复现**？（必现 / 偶发 / 仅特定机型 / 仅低端机）
- [ ] **现象是什么**？（列表滑动掉帧 / 动画卡顿 / 点击无响应 / 页面切换慢）
- [ ] **宏观指标**：当前场景的 Jank 率、Jank 持续时间（Jank duration）、GPU 渲染耗时等是否有大盘统计数据？

### 1.2 Rendering pipeline
- [ ] **当前渲染链路**：是标准 View（BLAST）、SurfaceView、TextureView，还是 GL/Vulkan 直接上屏、Flutter/WebView 混合渲染？
- [ ] **多窗口/覆盖层**：是否有悬浮窗、Dialog 或半透明 Activity 存在？

### 1.3 Perfetto / trace 观测
- [ ] **主线程（UI Thread）**：`Choreographer#doFrame` 是否超过了 VSync 预算？
  - [ ] `measure` / `layout` 耗时是否异常？（布局太深 / 频繁 requestLayout）
  - [ ] `draw` / `Record View#draw` 是否过长？（View 过多 / 复杂的 Canvas 绘制）
  - [ ] 主线程是否在等锁（`monitor contention`）或等 I/O（`D 状态` / `binder_sample`）？
- [ ] **RenderThread**：`DrawFrame` 是否超时？
  - [ ] `syncFrameState` 是否阻塞了主线程？
  - [ ] `flush commands` / `eglSwapBuffers` 是否耗时过长？
  - [ ] 是否在 `dequeueBuffer` 处阻塞等待？（通常意味着 BufferQueue 已满，SurfaceFlinger 消费慢或 GPU 阻塞）
- [ ] **SurfaceFlinger**：
  - [ ] `latchBuffer` 与 `setTransactionState` 是否及时？
  - [ ] HWC 合成策略是否从 DEVICE 退化成了 CLIENT（GPU 合成）？
- [ ] **系统环境**：
  - [ ] CPU 频率是否降频？（Thermal Throttling）
  - [ ] 是否存在后台 CPU 抢占或内存回收（kswapd / LMK）？

---

## 2. 启动（App Launch）排查清单

### 2.1 启动类型与度量对齐
- [ ] **启动类型**：是完全的冷启动（Cold Start）、温启动（Warm Start）还是热启动（Hot Start）？
- [ ] **数据口径**：是以 `am start -W` 的 `TotalTime` 为准，还是以 logcat `Displayed` 为准，还是以业务自定义的 TTFD（Fully Drawn）为准？

### 2.2 启动时间线分析（Perfetto / method tracing）
- [ ] **进程创建与 Zygote fork**：系统侧耗时是否异常长？（可能是系统内存压力导致）
- [ ] **Application#onCreate**：
  - [ ] 是否有第三方 SDK 在主线程同步初始化？
  - [ ] ContentProvider 是否隐式触发了大量不必要的加载？（留意 `attachBaseContext` 和 `installProvider`）
- [ ] **Activity#onCreate 到 onResume**：
  - [ ] XML Inflate（`LayoutInflater.inflate`）是否耗时过大？
  - [ ] 是否有读写 SharedPreferences/文件、数据库查询等 I/O 操作？
- [ ] **首帧渲染（First Frame）**：
  - [ ] 首页层级是否过深？
  - [ ] 图片解码、网络请求回调是否在首帧期间阻塞了主线程？

### 2.3 进阶检查项
- [ ] **Baseline Profiles**：应用是否集成了 Baseline Profiles？是否确认在本地生效（`/data/app/.../oat/arm64/base.odex` 已生成）？
- [ ] **16KB 页面大小**：如果运行在 Android 15+ 设备上，是否有因为 16KB 页引起的 native 库加载耗时增加？
- [ ] **线程调度**：启动期间的子线程初始化任务，是否和主线程发生了激烈的 CPU 竞争？

---

## 3. ANR 排查清单

### 3.1 现场确认与超时类型
- [ ] **ANR 触发源**：
  - [ ] Input Dispatching Timeout (一般 5 秒)
  - [ ] Broadcast Timeout (前台 10-20s，后台 60s)
  - [ ] Service Timeout (前台 20s，后台 200s)
  - [ ] ContentProvider Timeout (10s)
- [ ] **系统快照**：
  - [ ] CPU 整体负载：是单 App 高负载，还是系统级资源耗尽（如 100% iowait）？
  - [ ] 物理内存剩余量（Free RAM）和 Swap 压力。

### 3.2 痕迹分析（`traces.txt` 与 Logcat）
- [ ] **主线程状态**：
  - [ ] `Blocked` (等锁)：看当前被谁持有锁，寻找死锁链。
  - [ ] `Runnable`：说明在抢 CPU，或陷入死循环。
  - [ ] `Native`：是正常的 `epoll_wait`，还是卡在某个 Native 库的执行中（如 WebRTC / DB 读写）？若 dump 时主线程已经恢复空闲，不能直接用该栈解释触发点。
  - [ ] `Sleeping`：是否有显式的 `Thread.sleep()`。
- [ ] **Logcat 信号搜索**：
  - 搜索 `am_anr`、`dvm_lock_sample`、`binder_sample`、`Slow operation`。
  - 确认 `am_anr` 发生的时间戳与 `traces.txt` 生成的时间差，判断主线程栈是否已发生偏移。

### 3.3 深度排查（Perfetto）
- [ ] 主线程在 ANR 发生前 5~10 秒内，是否有密集的短暂阻塞（如数百次几毫秒的 I/O），导致累积超时？
- [ ] Binder 线程池是否耗尽（15 个线程全忙）？
- [ ] 系统焦点是否异常？（如 `Application does not have a focused window`，排查前一应用是否卡死）。
- [ ] 是否遭遇了 `am_freeze`（进程被错误冻结导致消息无法派发）？

---

## 4. 内存（Memory）排查清单

### 4.1 现象分类
- [ ] **是崩溃（OOM）还是变慢（GC 抖动 / kswapd 抢占）？**
- [ ] OOM 类型：Java OOM（`OutOfMemoryError`）、lmkd 终止进程，还是 FD 耗尽？

### 4.2 宏观数据（dumpsys meminfo）
- [ ] Java Heap 占用是否接近虚拟机上限（`getMemoryClass()` / `getLargeMemoryClass()`）？
- [ ] Native Heap 占用是否过大？
- [ ] Graphics（Gfx dev）内存是否异常？（留意不可见窗口的资源未释放）
- [ ] 内存曲线是**平稳增加不下降**（内存泄漏），还是**高频大锯齿**（内存抖动 / 对象风暴）？

### 4.3 内存泄漏定位
- [ ] 是否有关闭的 Activity/Fragment 仍在 Heap Dump 中存活？
- [ ] 是否有单例、静态变量、全局 Handler 错误持有了 `Context`？
- [ ] 匿名内部类/非静态内部类是否隐式持有了外部类？
- [ ] Compose 中的 `LaunchedEffect` 或高阶函数闭包是否捕获了长生命周期对象？

### 4.4 内存抖动与 GC
- [ ] Perfetto 中，主线程是否被大量 `GC` 阻塞（如 `Alloc`、`MarkCompact` 阶段暂停）？
- [ ] Memory Profiler 中，`String`、`char[]`、`byte[]` 的分配和回收频率是否极高？
- [ ] 是否在 `onDraw` 或 RecyclerView `onBindViewHolder` 中做了对象分配？

---

## 5. 功耗（Power / Battery）排查清单

### 5.1 耗电特征归因
- [ ] **发热还是掉电**？（发热通常伴随持续的高 CPU/GPU 负载；单纯后台掉电可能是唤醒锁导致）。
- [ ] **耗电场景**：是前台重载（游戏/视频），还是后台静默掉电？

### 5.2 后台与休眠机制（Doze / Wakelock）
- [ ] 电池统计（Battery Historian）：设备是否能进入 Deep Sleep？
- [ ] **Wakelock 泄漏**：是否有未释放的 `PARTIAL_WAKE_LOCK`？（重点查 `try-finally` 块是否安全释放）。
- [ ] **Alarm 与网络唤醒**：后台是否存在频繁的 `AlarmManager` 唤醒或周期性网络同步任务？（是否可以通过 WorkManager 替代？）

### 5.3 前台与硬件调优
- [ ] GPU 渲染是否没有开启上限，导致过度绘制或帧率过高跑满负载？
- [ ] 视频播放场景，HWC Overlay 是否失效退化到了 GPU 合成，导致额外耗电？
- [ ] 位置服务（GPS）：是否在后台持续请求高精度位置更新，未及时调用 `removeLocationUpdates()`？
- [ ] 传感器与蓝牙：是否在不需要时仍保持注册状态？

### 5.4 验证系统策略
- [ ] App 是否在特定 ROM 上被列入后台强杀名单？
- [ ] 在 Android 14+ 上，前台服务（FGS）是否因为超时（如 `dataSync` 6 小时限制）或类型声明不当被系统截断？
