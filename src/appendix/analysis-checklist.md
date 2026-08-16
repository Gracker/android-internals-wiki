# 附录 D：性能分析核对清单

这份清单用于在采集和归因前核对现象、测试条件与证据，减少无效测试，也避免看到单个信号便直接判断原因。

系统跟踪（trace）是按时间排列的调度、CPU、I/O、内存和图形事件记录。Perfetto 是 Android 常用的系统跟踪采集与分析工具；文中保留其中的事件名、API 名与字段名，便于回到工具中搜索。

---

## 0. 先固定测试条件

- [ ] 记录应用版本、构建类型、设备型号、Android 版本、API 级别、CPU ABI 和厂商系统版本。CPU ABI 是原生二进制接口，决定 native 库需要匹配的指令集与调用约定。
- [ ] 记录刷新率、电源模式、电量、充电状态与温控状态；性能模式和温度不同，结果不可直接比较。
- [ ] 写清复现步骤、复现概率、开始时间、结束时间和用户可见现象，并为日志与 trace 保留同一时间基准。
- [ ] 至少保留一组正常样本和一组异常样本；机型、账号数据、网络与操作步骤尽量一致。
- [ ] 把“观测到的信号”和“据此提出的原因”分开记录。例如，“主线程等待 Binder 回复 800 ms”是信号，“远端服务持锁”仍需远端线程或调度证据确认。

---

## 1. 卡顿（Jank）排查清单

Jank 指某一帧没有赶上对应的显示刷新期限，用户会看到掉帧、动画停顿或触控反馈延迟。帧预算取决于刷新率，60 Hz、90 Hz、120 Hz 每帧约有 16.7 ms、11.1 ms、8.3 ms，不能把 16 ms 当成所有设备的固定阈值。

### 1.1 现象与范围

- [ ] 是否可稳定复现：必现、偶发、只在特定机型出现，还是只在低内存或高温状态出现？
- [ ] 用户看到的是列表掉帧、动画停顿、点击无响应、页面切换慢，还是画面撕裂？这些现象对应的采集范围并不相同。
- [ ] 同一场景是否有帧耗时分布、慢帧比例、冻结帧比例和 GPU 耗时，而非只有平均值？
- [ ] 指标是否来自同一种渲染方式？Android vitals 是 Google Play Console 汇总的线上质量指标，其中的 View 渲染指标不能完整覆盖 OpenGL、Vulkan、Unity 或 Unreal 直接渲染的帧，详见[慢帧说明](https://developer.android.com/topic/performance/vitals/render)。

### 1.2 确认渲染路径

- [ ] 页面使用标准 View、Compose、SurfaceView、TextureView，还是 OpenGL/Vulkan 直接上屏？Flutter 或 WebView 是否参与合成？
- [ ] 是否存在悬浮窗、Dialog、半透明 Activity、多窗口或画中画，改变了缓冲区数量与合成成本？
- [ ] 卡顿只发生在应用生成画面时，还是已经生成的画面迟迟没有显示？前者优先查应用线程，后者还需检查 SurfaceFlinger、GPU 与显示合成。

### 1.3 检查 Perfetto 时间线

FrameTimeline 是 Perfetto 中把应用帧与显示帧对应起来的时间线，可用来区分应用未按时产出、SurfaceFlinger 合成延迟和显示阶段延迟。其中，Expected Timeline 表示帧原本应覆盖的时间，Actual Timeline 表示帧的实际执行与显示时间。

- [ ] 在 FrameTimeline 中定位用户看到的慢帧，并确认对应的 Actual Timeline 与 Expected Timeline；不要只搜索一个耗时较长的函数。
- [ ] 主线程的 `Choreographer#doFrame` 是否超过当前刷新率对应的期限？
  - [ ] `measure`、`layout` 是否因布局层级过深或频繁 `requestLayout()` 变慢？
  - [ ] `draw` 或 `Record View#draw` 是否因 View 数量、阴影、裁剪或 Canvas 绘制变慢？
  - [ ] 主线程是否等待监视器锁、同步 Binder 调用或磁盘 I/O？Binder 是 Android 的跨进程调用机制，调用方可能一直等待远端进程回复。
  - [ ] 线程处于 D 状态时，表示它在内核中进行不可中断等待，常见于块设备 I/O；仅凭 D 状态还不能确定是哪次读写造成等待。
- [ ] RenderThread 是否延迟？RenderThread 是替应用准备和提交硬件加速绘制命令的线程。
  - [ ] `DrawFrame`、`syncFrameState`、`flush commands` 或 `eglSwapBuffers` 是否跨过帧期限？
  - [ ] 是否在 `dequeueBuffer` 等待可用缓冲区？BufferQueue 是连接画面生产方与消费方的缓冲区队列；继续检查它、SurfaceFlinger 和 GPU 的时间线，不能直接认定 GPU 过慢。
- [ ] SurfaceFlinger 是否及时接收并合成缓冲区？SurfaceFlinger 是系统显示合成服务。
  - [ ] `latchBuffer` 与事务提交是否延迟？
  - [ ] HWC（Hardware Composer，硬件合成器）是否从 DEVICE 合成改为 CLIENT 合成，从而增加 GPU 的合成工作？
- [ ] CPU 是否因温控降频，线程是否长时间处于 Runnable 却得不到调度，或被其他进程持续抢占？
- [ ] `kswapd` 是否频繁回收内存，LMKD 是否在内存压力下终止进程？`kswapd` 是内核内存回收线程，LMKD 是 Android 的低内存终止守护进程，两者含义不同。
- [ ] 若启用 method tracing，是否先做一次无插桩对照？method tracing 会记录方法进入与退出，能提供调用级耗时，但会增加开销，也可能制造原本不存在的卡顿。

---

## 2. 启动（App Launch）排查清单

### 2.1 对齐启动类型与指标

- [ ] 启动类型是否明确？冷启动表示应用进程尚不存在；温启动通常复用进程但需重建 Activity；热启动通常把仍在内存中的 Activity 带回前台。
- [ ] TTID（Time to Initial Display）是否按首帧显示计时？TTFD（Time to Full Display）是否在关键内容可交互后调用 `reportFullyDrawn()`？两者回答的问题不同，定义见[应用启动时间](https://developer.android.com/topic/performance/vitals/launch-time)。
- [ ] `am start -W` 的 `TotalTime`、Logcat 的 `Displayed`、Macrobenchmark 结果和业务埋点是否使用相同的起点与终点？Macrobenchmark 是 AndroidX 用来从应用进程外测量启动、滚动等完整场景的基准测试工具。
- [ ] 是否分别统计中位数、高分位和极端样本，而非用少量手工启动的平均值代替分布？

### 2.2 检查启动时间线

- [ ] 进程创建和 Zygote fork 是否变慢？Zygote 是预加载常用类与资源、再派生应用进程的系统进程；这一段异常还需结合系统内存压力和调度情况判断。
- [ ] `Application#onCreate` 是否包含主线程同步初始化、磁盘读取、数据库打开或网络等待？
- [ ] 第三方 SDK 是否都必须在首帧前初始化？延迟初始化后是否会把等待转移到用户首次操作？
- [ ] ContentProvider 是否在应用入口之前隐式初始化大量组件？检查 `attachBaseContext`、`installProvider` 与各 Provider 的 `onCreate()`。
- [ ] `Activity#onCreate` 到 `onResume` 之间，XML inflate、依赖注入、SharedPreferences、文件或数据库 I/O 是否占用主线程？
- [ ] 图片解码、字体加载和网络回调是否挡住首帧，或让首帧很快出现但关键内容很晚才可用？分别记录 TTID 与 TTFD 才能分辨。
- [ ] method tracing 是否改变了启动结果？优先用系统跟踪定位区段，再对较小范围做方法级分析。

### 2.3 检查编译与兼容条件

- [ ] 应用是否随包提供 Baseline Profile？Baseline Profile 是构建时提供的热点代码规则，设备安装后可据此提前编译常走代码。
- [ ] 是否通过 `ProfileVerifier` 或 `adb shell dumpsys package dexopt` 检查编译状态？
  - [ ] `speed-profile` 表示正在使用按配置文件编译的代码；只看到 `/data/app/.../oat/.../base.odex` 文件，不能证明目标规则已安装或被采用，参见[调试 Baseline Profile](https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles)。
- [ ] 在使用 16 KB 内存页的设备上，包含原生代码的 APK 是否按 16 KB 对齐并重新构建？纯 Java/Kotlin 应用通常无需修改；这属于兼容性检查，不应预设原生库加载一定变慢，参见[支持 16 KB 页大小](https://developer.android.com/guide/practices/page-sizes)。
- [ ] 启动期间创建的线程是否与主线程竞争 CPU？减少线程数之后，应比较首帧和完整可用时间，避免只把任务移到稍晚阶段。

---

## 3. ANR 排查清单

ANR（Application Not Responding）表示应用在系统规定的时间内没有响应某类请求。阈值取决于请求类型、Android 版本和设备实现；官方列出的默认值面向 AOSP（Android 开源项目）与 Pixel，厂商可以调整，详见[ANR 诊断说明](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs)。

### 3.1 确认触发类型与时间窗口

- [ ] 从 ANR subject、Android vitals、bugreport 或系统事件中确认触发类型，不要只按主线程栈猜测。subject 是触发原因摘要，bugreport 是设备导出的系统诊断包。
- [ ] Input dispatch 默认阈值通常为 5 秒；检查输入事件等待的是主线程、焦点窗口，还是 GPU/显示系统。
- [ ] Broadcast 在 Android 13 及更早版本的默认阈值通常为前台优先级 10 秒、后台优先级 60 秒；Android 14 及更高版本会因进程是否缺少 CPU 时间扩展到约 10–20 秒或 60–120 秒。
- [ ] Service 执行超时的 AOSP 默认值通常为前台服务 20 秒、后台服务 200 秒，计时可包含冷启动以及 `onCreate()`、`onStartCommand()` 或 `onBind()`。
- [ ] ContentProvider 没有统一的 10 秒默认值；远端查询的检测阈值由调用方通过 `ContentProviderClient.setDetectNotResponding()` 指定。
- [ ] 记录触发时间、线程转储时间和 trace 覆盖范围。若转储晚于触发点，恢复空闲后的栈不能解释先前的超时。

### 3.2 阅读线程转储与日志

`traces.txt` 或 ANR report（无响应报告）只保存某个采样时刻的线程转储，无法呈现完整执行历史。

- [ ] 主线程为 `Blocked` 时，是否能找到锁对象、持有者线程和持锁区间？只看到等锁线程仍不足以定位慢代码。
- [ ] 主线程为 `Runnable` 时，Perfetto 是否显示它在 CPU 上运行？Runnable 只表示具备运行条件，不等于正在运行，也不自动说明存在死循环。
- [ ] 主线程为 `Native` 时，是在原生库执行、等待 Binder/I/O，还是停在正常的 `epoll_wait`/`nativePollOnce`？后两者也可能表示转储采集得太晚。
- [ ] 主线程为 `Sleeping` 时，是否存在显式 `Thread.sleep()`、退避重试或定时等待？
- [ ] Logcat 中的 `am_anr`、`dvm_lock_sample`、`binder_sample` 和 `Slow operation` 是否与同一进程、同一时间窗口对应？
- [ ] CPU 高负载来自本应用、`system_server` 还是其他进程？高 iowait 表示 CPU 时间花在等待 I/O 完成，仍需继续定位设备和请求。
- [ ] 物理内存、交换空间和内存压力是否在 ANR 前已经恶化？内存回收可能让应用线程长期得不到调度。

### 3.3 用 Perfetto 补齐因果证据

- [ ] 主线程在触发前是否被一次长任务阻塞，或被多次短 I/O、锁等待、Binder 调用累计拖慢？采集窗口应覆盖 subject 对应的完整超时区间。
- [ ] 同步 Binder 调用的回复线程在做什么？若远端是 `system_server`，同时检查其调度、锁竞争和 I/O。
- [ ] Binder 线程是否全部忙于处理请求？记录设备上当时的线程数量、运行状态与调用栈，不要把“15 个线程”当成所有进程和版本的固定配置。
- [ ] 无焦点窗口 ANR 是否来自首帧太慢或窗口设置了 `FLAG_NOT_FOCUSABLE`？也要核对焦点转移时序，不能只检查当前窗口。
- [ ] 出现 `am_freeze` 时，冻结和解冻事件是否覆盖 ANR 窗口，系统记录的冻结原因是什么？该事件是线索，本身不能证明进程被系统错误冻结。

---

## 4. 内存（Memory）排查清单

### 4.1 先区分故障类型

- [ ] Java 堆是否抛出 `OutOfMemoryError`？记录异常消息、堆上限、失败分配大小和分配调用栈。
- [ ] 原生分配是否失败？检查 tombstone、malloc 日志、Native Heap 和映射区，不能用 Java 堆余量排除原生内存问题。tombstone 是系统保存的原生崩溃转储，包含线程、寄存器和原生调用栈等现场信息。
- [ ] 进程是否被 LMKD 因系统内存压力终止？这种终止通常不会在应用内抛出 Java OOM。
- [ ] 是否耗尽文件描述符（FD）？`EMFILE` 或 “Too many open files” 表示进程打开的文件、socket、管道等句柄达到限制，与堆 OOM 是两类问题。
- [ ] Android 11 及更高版本是否用 `ActivityManager.getHistoricalProcessExitReasons()` 读取 `ApplicationExitInfo`？
  - [ ] 核对 `getReason()`、`getStatus()`、`getImportance()` 与说明字段；各退出原因见 [`ApplicationExitInfo`](https://developer.android.com/reference/android/app/ApplicationExitInfo)。

### 4.2 查看整体内存

PSS（Proportional Set Size，按共享比例分摊后的内存）便于估算进程对系统内存的贡献，但不能视为某个堆的硬上限。GC（Garbage Collection）是虚拟机查找并回收不可达对象的过程。

- [ ] `dumpsys meminfo` 中的 Java Heap 是否接近当前虚拟机堆上限？`getMemoryClass()` 与 `getLargeMemoryClass()` 只说明配置上限，不能代替分配失败现场。
- [ ] `Native Heap`（原生堆）、`Graphics`（图形内存）、`code`（代码映射）、`stack`（线程栈）、`Ashmem`（旧式 Android 共享内存）和其他 `mmap` 映射中，哪一项随复现步骤增长？
- [ ] 不可见窗口、Bitmap、纹理、硬件缓冲区和解码器资源是否在生命周期结束后仍保留？Graphics 数值异常只是入口，还需对象或缓冲区证据。
- [ ] 系统是否频繁交换、回收页或触发 PSI 内存压力？PSI（Pressure Stall Information）统计任务因 CPU、内存或 I/O 资源不足而停顿的时间；LMKD 会在系统内存不足时按进程重要性选择目标，说明见 [lmkd 文档](https://source.android.com/docs/core/perf/lmkd)。
- [ ] 曲线是多轮操作后基线持续升高，还是分配与 GC 形成高频锯齿？前者再查泄漏，后者再查分配速率和暂停时间。

### 4.3 定位泄漏与分配热点

- [ ] 已关闭的 Activity、Fragment、View 或 Compose 相关对象是否仍可从 GC Root 到达？GC Root 是垃圾回收器判断对象可达性的起点；Heap Dump 中仍存活的对象不一定都是泄漏，要结合预期生命周期判断。
- [ ] 单例、静态字段、全局 Handler、回调、监听器或缓存是否持有短生命周期的 `Context` 或 View？
- [ ] 匿名内部类、非静态内部类、协程、`LaunchedEffect` 或高阶函数闭包是否捕获了生命周期更长的对象？
- [ ] 主线程是否被频繁 GC 暂停？结合 Perfetto 的 GC 区段、分配速率和帧时间判断影响，不能只用 GC 次数归因卡顿。
- [ ] `String`、`char[]`、`byte[]` 或业务对象是否高频创建？回到分配调用栈确认来源。
- [ ] `onDraw()`、RecyclerView 的 `onBindViewHolder()` 或 Compose 重组热点中是否每次都创建临时对象？

---

## 5. 功耗（Power / Battery）排查清单

### 5.1 对齐测量条件

- [ ] 用户反馈的是发热、前台续航缩短、后台静默掉电，还是待机无法休眠？这些现象需要不同的复现场景。
- [ ] 是否固定亮度、刷新率、网络、信号强度、位置、媒体音量、电池电量区间和温度，并在相同条件下保留正常对照？
- [ ] 发热是否与持续 CPU/GPU 负载、蜂窝弱信号或充电同时出现？温度只能说明热量累积，不能单独指出耗电模块。
- [ ] 使用 Power Profiler、Perfetto 或 Macrobenchmark 的 `PowerMetric` 时，是否记录工具给出的是事件、估算功耗还是硬件计量值？
- [ ] 若使用 Battery Historian，是否明确它已不再积极维护？Historian 仍可回看系统事件，但不能把活跃时长直接当成精确能耗；官方建议优先使用前述工具，参见[功耗分析说明](https://developer.android.com/topic/performance/power/battery-historian)。

### 5.2 检查后台与休眠

Doze 是设备长时间闲置时限制后台活动的系统省电模式；Deep Sleep 表示主 CPU 进入挂起状态。Wakelock（唤醒锁）是应用或系统组件为了继续执行而阻止部分休眠的机制。

- [ ] 设备是否能进入 Deep Sleep？若不能，哪一个唤醒源、定时器、中断或唤醒锁覆盖了待机区间？
- [ ] `PARTIAL_WAKE_LOCK` 是否成对获取和释放？异常、取消和超时路径是否都能释放？
- [ ] `AlarmManager` 是否频繁唤醒设备，任务是否要求精确到点？可延迟且退出应用后仍需执行的持久任务适合 WorkManager；日历提醒等精确、面向用户的时间事件仍可能需要 AlarmManager，参见[后台任务选择](https://developer.android.com/develop/background-work/background-tasks/persistent)。
- [ ] 周期网络同步是否能合并请求、增加退避并使用充电或网络约束？更换调度 API 之前先确认时效要求。

### 5.3 检查前台与硬件活动

- [ ] 帧率是否高于场景需要，应用是否在不可见或静止画面仍持续提交帧？帧率无上限和过度绘制是两个问题，应分别检查提交频率与每帧绘制量。
- [ ] 视频播放时 HWC Overlay（硬件叠加层）是否可用？若改为 GPU 合成，原因是格式、缩放、旋转、透明度还是图层数量？
- [ ] 高精度位置是否在后台持续更新，停止场景是否调用 `removeLocationUpdates()`？
- [ ] 传感器、相机、麦克风、蓝牙扫描和 Wi-Fi 扫描是否按界面可见性与任务生命周期注册、注销？
- [ ] 蜂窝网络是否因小包高频上传反复进入高功耗状态？尝试批量发送后，用相同网络条件复测。

### 5.4 核对系统限制

- [ ] 厂商定制系统（常被简称为 ROM）是否对后台启动、自启动、待机或省电白名单另有规则？记录具体系统版本和策略开关，不要只写“某厂商限制”。
- [ ] 前台服务（FGS）类型、启动来源、通知和权限是否符合当前系统及目标 API 要求？FGS 是持续执行用户可感知任务、并显示通知的服务形态，不适合所有后台任务。
- [ ] 对运行在 Android 15 及更高版本、且目标 API 为 35 及更高的应用，`dataSync` 与 `mediaProcessing` 类型是否各自在任意 24 小时内累计超过 6 小时？
  - [ ] 同类型的多个服务共享时限；应用回到前台会重置计时。超时后系统调用 `Service.onTimeout(int, int)`，详见[前台服务时限](https://developer.android.com/develop/background-work/services/fgs/timeout)。
- [ ] 系统终止或限制任务时，是否保存了异常类型、系统日志、`ApplicationExitInfo` 和前台服务事件？只有业务回调停止，无法区分主动结束、系统限制和进程退出。
