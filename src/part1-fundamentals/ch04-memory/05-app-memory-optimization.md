---



status: ready-for-review
title: App 内存优化与诊断
section: '4.5'
chapter: '4.5'
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: '2026-06-24'
last_verified_against: AOSP android-16.0.0_r1
confidence: medium
sources:
- type: official
  path: https://developer.android.com/topic/performance/memory
- type: official
  path: https://developer.android.com/topic/performance/graphics/manage-memory
- type: official
  path: https://developer.android.com/build/apps/16kb-page-size
- type: aosp
  path: frameworks/base/core/java/android/app/ActivityManager.java
- type: aosp
  path: frameworks/base/core/java/android/content/ComponentCallbacks2.java
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/Bitmap.java
- type: blog
  path: https://android-developers.googleblog.com/2024/10/16kb-page-size-android-15.html
- type: official
  path: https://perfetto.dev/docs/data-sources/native-heap-profiler
- type: official
  path: https://developer.android.com/ndk/guides/debug-gdb
tags:
- memory-optimization
- bitmap
- memory-leak
- onTrimMemory
- native-memory
- memory-churn
- object-pool
- heapprofd
- 16kb-page-size
related_chapters:
- '4.1'
- '4.2'
- '4.3'
- '4.4'
- '7.2'
- '7.3'
drafted_date: '2026-03-31'
drafted_by: openclaw-task2
reviewed_date: 2026-06-04
reviewed_by: openclaw-task6
review_type: draft-review
review_round: 5
polish_count: 1
polish_date: '2026-04-08'
polish_by: task2b-polish
pipeline_stage: ready-for-review
task6_state: pending-verification
task2b_state: fixed
task2b_result: fixed
last_task2b_at: "2026-06-04T04:55:01"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-04"
task9_review_notes: "2026-06-04 Task9 deep review: auto-fixed。修正 onTrimMemory 在 Android 16 的 ApplicationThread→主线程分发链、Debug.getPss API level、heapprofd 开销边界和 System.gc 使用边界;已回到 Task6 复审。"
task6_result: pass-light-edit
last_task6_at: "2026-06-23T20:08:00+08:00"
last_task6_review_log: "logs/review/2026-06-23-20-review.md"
task6_review_notes: '2026-06-23 task6 revisiting-review: pass-light-edit。L1 修复 1 处（恰恰相反→删除）。L2 全部通过。无B类大问题。task2b 已 fixed，task9 auto-fixed，queue.json 无 pending，自动晋升 finalized。'
review_notes: 2026-05-12 Task6 16：15：L1/L2 小修 29 处（禁用词、第一人称导航、中英文间距、待验证标注）；L3 数据/Perfetto 证据缺口已写入 queue.json（priority 90）。
last_task9_at: "2026-06-24T09:27:00+08:00"
last_task9_audit: '2026-06-24'
task9_result: pass-tech-review
task9_state: reviewed
last_task9_review_log: "logs/deep-review/2026-06-04-08-deep-review.md"
last_task9_autofix_at: "2026-06-04"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-24
last_consolidated_at: "2026-08-11"
consolidated_from:
  - "src/part1-fundamentals/ch04-memory/4.35-android17-cpu-cache-locality-pss-accounting.md"
  - "src/part1-fundamentals/ch04-memory/4.36-android17-advanced-memory-optimization.md"
---


# 4.5 App 内存优化与诊断

## 先确定优化对象

平台以 Android 17 / API 37 / `android-17.0.0_r1` 为锚点，并兼顾 Android 8～16 的行为差异。App 的内存并非一个数字：Java/Kotlin 对象主要在 ART 管理的堆中，`malloc`、Bitmap 像素和部分运行时数据位于 Native 侧，GraphicBuffer、硬件 Bitmap、Surface 等还可能出现在 Graphics、memtrack 或 dmabuf 口径中。文件描述符不属于堆，却同样可能耗尽进程资源。

因此，“Java 堆没有到上限”无法证明进程没有内存问题。一次完整排查至少要回答四个问题：

1. 哪个内存口径在增长：Java、Native、Graphics、共享页、swap，还是 FD？
2. 增长发生在哪个业务场景，退出场景后能否回落？
3. 增长来自仍在使用的对象、缓存、延迟释放，还是不可达却仍被引用的对象？
4. 问题表现为 OOM、系统低内存终止、GC 干扰帧执行，还是后台驻留能力下降？

这四个问题决定工具选择。只看一张总 PSS 曲线，通常无法定位到具体引用或调用栈。

## 四步优化顺序

App 侧可以按“减少分配 → 缩短持有时间 → 消除泄漏 → 监控和回归”推进。这是一个排查顺序，并非四套彼此独立的技巧。

### 第一层：减少无效分配

高频路径中的临时对象会增加分配速率，也可能增加 GC、线程停顿和内存带宽开销。优先检查：

- `onDraw()`、动画回调和触摸处理中的 `Paint`、`Path`、数组与临时集合；
- `onBindViewHolder()` 和 Compose 重组中的排序、映射、字符串格式化；
- 循环内不必要的装箱、复制和中间集合；
- 先解码原图、再缩放成缩略图的图片链路；
- 每次请求都新建的大缓冲区、编解码器或解析器。

优化前先用分配记录或 Trace 证明热点。把偶发的小对象改成成员变量，可能延长对象存活时间；为了“零分配”长期保留大缓冲区，也会抬高常驻内存。

### 第二层：缩短持有时间

对象离开业务场景后，应尽快断开强引用并释放其拥有的外部资源。典型动作包括：

- 页面销毁时取消任务、移除回调和监听器；
- 对有容量的缓存设置上限，并根据场景主动缩容；
- `Closeable`、游标、文件、ParcelFileDescriptor 和 Native handle 使用确定的关闭路径；
- Fragment 在 `onDestroyView()` 清除 View Binding，而非等到 Fragment 销毁；
- 图片请求离开目标 View 后交还给图片库，不继续由业务对象持有。

“及时”应按所有权定义判断。仍在被 View、Canvas、解码任务或跨线程工作使用的资源，提前释放会把内存问题变成崩溃或数据竞争。

### 第三层：消除泄漏

泄漏意味着业务已经不再需要某个对象，但 GC Root 到它仍存在强引用路径。页面反复进入和退出后，Activity、Fragment View、Bitmap 或监听器实例数量持续增加，是常见信号。

弱引用只能改变引用强度，无法自动取消工作、注销观察者或关闭资源。首选方案是让任务和注册行为服从生命周期，再根据 API 合约决定是否需要弱引用。

### 第四层：监控和回归

开发期可用 LeakCanary 和 Heap Dump 查引用链，用 Android Studio Memory Profiler 看分配热点；性能测试可用 Perfetto、heapprofd、`dumpsys meminfo` 和 `/proc` 指标；线上则关注退出原因、用户可感知的低内存终止率以及分设备档位的内存水位。

每次优化都应保留可复现的场景、设备、构建类型和前后数据。内存值会受 GC 时机、共享页归属、系统服务和设备实现影响，单次快照不适合作为结论。

## 内存抖动与帧预算

内存抖动指短时间内大量分配并很快失效。Profiler 中常见锯齿曲线：分配使曲线上升，回收使曲线下降；问题在于分配速率、回收频率和停顿是否干扰用户路径。

ART 的收集器和代际策略会随版本、设备配置与运行状态变化，不能假设所有进程都固定使用某一种 Collector，也不能把某个停顿时长当成通用门槛。诊断时应在同一设备上同时观察：

- 主线程与 RenderThread 的 FrameTimeline；
- GC slice、线程调度和 safepoint；
- 分配速率、存活对象数量与回收后基线；
- 60 Hz、90 Hz、120 Hz 等目标刷新率下的业务负载。

120 Hz 的帧间隔约为 8.33 ms，60 Hz 约为 16.67 ms。更高刷新率缩短了每帧可用时间，同样的暂停会占据更大比例；是否掉帧还取决于该帧其余工作、调度和设备性能。固定的“3 ms GC 黄金线”缺少跨设备依据，应用应以 FrameTimeline 与 GC 事件的时间重叠为证据。

### 谨慎使用对象池

Android 提供了 `Message.obtain()`、`MotionEvent.obtain()` 等具有明确获取/归还合约的复用 API。业务自建对象池需要额外评估：

- 加锁或并发容器可能比重新分配更贵；
- 归还前必须清理所有状态，遗漏会造成脏数据或引用泄漏；
- 池中的对象保持可达，会抬高存活集和常驻内存；
- 池大小和对象尺寸如果随输入增长，池会成为无界缓存。

Android 官方内存指南也提醒，对象池可能因同步、状态清理和存活集扩大而降低性能。只有 Trace 证明某类对象的分配是热点，并且所有权清晰、容量有界时，才值得引入自定义池。

## Bitmap：先控制解码尺寸，再讨论复用

例如，一张 1080 × 1920 的 `ARGB_8888` 图片仅像素数据就约为：

`1080 × 1920 × 4 = 8,294,400` 字节，约 7.91 MiB。

压缩文件大小不能代表解码后的内存大小。JPEG 或 WebP 在磁盘上可能只有几百 KiB，解码后仍按宽、高、像素格式和行跨度占用内存。

### 像素数据的版本变化

Bitmap 像素数据所在位置经历过三段变化：

| Android 版本 | 像素数据主要位置 | 管理要点 |
| --- | --- | --- |
| Android 2.2 / API 8 及更早 | Native 内存 | Java 对象与 Native 像素的释放时机需要特别谨慎 |
| Android 3.0～7.1 / API 11～25 | Dalvik/ART 堆 | 像素数据计入受管理堆 |
| Android 8.0 / API 26 及以后 | Native 内存 | 平台通过 `NativeAllocationRegistry` 把 Native 分配压力反馈给运行时 |

API 26+ 的像素数据离开 Java 堆，不代表它脱离了进程内存限制。Bitmap 仍会增加物理内存压力，Native 分配注册也会影响 ART 的回收决策；分配失败仍可能表现为 `OutOfMemoryError`。排查时要同时查看 Java、Native、Graphics/memtrack 和 dmabuf 口径。

### `inSampleSize`：在解码阶段减小像素数

只显示 200 × 200 缩略图时，不应先完整解码 4000 × 3000 原图。`BitmapFactory.Options.inSampleSize` 的平台规则是：

- 小于或等于 1 的值按 1 处理；
- 最终使用 2 的幂；非 2 的幂会向下取最近的 2 的幂；
- 值为 `n` 时，解码宽高约为原图的 `1/n`，像素数约为 `1/n²`。

下面的函数先读取图片边界，再计算不会小于目标尺寸的采样值：

```kotlin
fun calculateInSampleSize(
    outWidth: Int,
    outHeight: Int,
    requiredWidth: Int,
    requiredHeight: Int
): Int {
    var sample = 1
    while (
        outWidth / (sample * 2) >= requiredWidth &&
        outHeight / (sample * 2) >= requiredHeight
    ) {
        sample *= 2
    }
    return sample
}
```

这个结果只负责粗粒度下采样。还要结合 EXIF 方向、目标密度、裁剪方式和图片库的尺寸解析，避免把尺寸刚好的图片再次放大。

### `inBitmap`：复用有严格前提

`inBitmap` 允许 `BitmapFactory` 尝试复用已有 Bitmap 的像素分配。Android 17 的约束可归纳为：

- 候选 Bitmap 必须可变，且不能是 `Bitmap.Config.HARDWARE`；
- API 19+ 要求解码所需字节数不超过候选对象的 `getAllocationByteCount()`；
- API 11～18 只支持 JPEG/PNG、尺寸相同且 `inSampleSize == 1` 的严格复用；
- 候选对象无法使用时，解码会抛出 `IllegalArgumentException`；
- 调用方必须使用 `decode*()` 的返回值，不能假设返回对象一定就是传入的候选对象。

下面的示例展示最小的防御式写法，候选池本身仍需负责容量和并发：

```kotlin
val options = BitmapFactory.Options().apply {
    inMutable = true
    inBitmap = candidate
    inSampleSize = sampleSize
}

val decoded = try {
    BitmapFactory.decodeFile(path, options)
} catch (_: IllegalArgumentException) {
    options.inBitmap = null
    BitmapFactory.decodeFile(path, options)
} ?: error("Bitmap decode failed: $path")
```

失败后移除候选再解码，可以避免把尺寸不匹配当成图片损坏。成熟图片库通常已经实现了更完整的候选筛选、引用计数和并发保护，业务代码无需重复造池。

### 像素格式要按内容选择

| `Bitmap.Config` | 常见字节数/像素 | 适用边界 |
| --- | ---: | --- |
| `ARGB_8888` | 4 | 常用格式，支持透明度和较完整的颜色精度 |
| `RGB_565` | 2 | 无 Alpha，颜色精度下降，渐变可能出现色带 |
| `ALPHA_8` | 1 | 只保存 Alpha，适合遮罩 |
| `RGBA_F16` | 8 | 宽色域或高精度处理，内存成本高 |
| `RGBA_1010102` | 4 | 更高 RGB 精度，Alpha 只有 2 bit |
| `HARDWARE` | 后端决定 | 只读、面向硬件渲染，不能按固定字节数估算 |

`RGB_565` 是否可接受应由视觉验收决定，不能仅凭“照片没有透明度”直接切换。文字截图、渐变和需要后处理的图片尤其容易暴露精度损失。

### 硬件 Bitmap 仍占用物理内存

Android 8.0 引入 `Bitmap.Config.HARDWARE`。其像素由图形缓冲区管理，可减少绘制时向 GPU 上传纹理的成本，但 Android 设备通常使用 CPU/GPU 共享的统一物理内存。把它称为“不占系统 RAM”会误导内存分析。

硬件 Bitmap 的主要边界是：

- 对象不可变，`getPixel()`、`copyPixelsToBuffer()` 等 CPU 像素访问会失败；
- 不能作为软件 Canvas 的绘制目标，也不能绘制到软件 Canvas；
- 适合解码后直接在硬件加速 UI 中展示；
- 需要像素编辑、软件渲染或某些截图链路时，应请求软件 Bitmap；
- 内存可能显示在 Graphics、memtrack、dmabuf 或设备特定分类中。

Android 17 的 `Bitmap` 仍实现 `Parcelable`，源码包含硬件 Bitmap 的 Parcel 处理，反序列化时像素格式还可能变化。因此“硬件 Bitmap 不能经 Binder 传递”不成立。跨进程传大图仍有同步、缓冲区所有权和接收端格式变化等成本，很多场景更适合传 URI、文件描述符或共享缓冲区协议。

### `recycle()` 是所有权操作

Android 17 的 `Bitmap.recycle()` 会立即释放像素资源。调用它的前提是调用方能证明 Bitmap 此后不会被 View、Drawable、Canvas、图片库、后台任务或其他线程使用，否则后续访问会失败。

官方 Bitmap 内存指南把手动 `recycle()` 的重点放在 Android 2.3.3 / API 10 及更早版本。现代应用通常应让清晰的所有权、GC 和图片库管理生命周期。图片变换产生的中间 Bitmap若由当前函数独占，并且下游已经取得新结果，可以考虑及时回收；由 Glide 等库管理的 Bitmap 不应由业务代码手动回收。

### Glide、Coil 与 Fresco 的差异

三类图片库都提供内存缓存，但实现和所有权合约不同：

- **Glide**：使用内存缓存和 `LruBitmapPool`，并通过 `ComponentCallbacks2` 调整缓存。默认容量由屏幕尺寸、密度、memory class 和低内存设备状态共同计算，不是固定的 `maxMemory / 8`。资源仍受 Glide 管理时，业务代码不要调用 `recycle()`。
- **Coil 3**：推荐进程内共享一个 `ImageLoader`，统一管理内存缓存、磁盘缓存和请求生命周期。硬件 Bitmap、解码器和缓存策略取决于版本、平台与单次请求配置。
- **Fresco**：区分已解码、已编码和磁盘缓存，并以 `CloseableReference` 管理引用。早期 Android 版本曾使用 ashmem 等方案，这段历史不能外推为现代版本的固定存储方式。

库升级可能修改默认缓存和硬件 Bitmap 策略。应用应查阅所用版本的官方文档，并用相同图片集和滚动场景测量峰值、回落值与命中率。

## 常见泄漏：从生命周期和所有权修起

### Activity 与异步工作

匿名内部类、回调、线程或协程一旦比 Activity 活得更久，就可能保留整个 View 树。修复重点是取消或脱离生命周期：

- UI 相关协程放进 `lifecycleScope`；
- 需要按可见状态收集 Flow 时使用 `repeatOnLifecycle`；
- 网络、定位、传感器和播放器任务在对应生命周期取消；
- ViewModel 不保存 Activity、Fragment、View 或其 Drawable；
- 进程级工作只保存完成工作所需的数据，不保存页面对象。

`WeakReference<Activity>` 可以避免一条强引用，但工作仍会继续，竞态也仍存在。线程在读取弱引用后，Activity 可能已经进入销毁流程。生命周期取消和主线程状态检查更可靠。

### Handler 与延迟回调

消息队列会持有尚未执行的 `Message` 和 `Runnable`。页面退出时应移除由该页面发布的任务。下面的写法保留显式 Runnable，便于精确移除：

```kotlin
class DetailActivity : AppCompatActivity() {
    private val handler = Handler(Looper.getMainLooper())
    private val refreshTask = Runnable { renderLatestState() }

    override fun onStart() {
        super.onStart()
        handler.postDelayed(refreshTask, 5_000)
    }

    override fun onStop() {
        handler.removeCallbacks(refreshTask)
        super.onStop()
    }
}
```

清理点要与任务含义匹配：只应在页面可见时运行的任务放在 `onStop()` 清理；可以覆盖整个 Activity 生命周期的任务可在 `onDestroy()` 清理。Java 匿名 Handler 还会隐式持有外部类，静态内部类能去掉这条引用，但仍需取消消息。

### 单例持有 Context

进程级组件可以保存 `context.applicationContext`，前提是它执行的工作适合 Application Context。主题、窗口、对话框、页面导航和部分资源解析依赖 Activity 或带主题的 Context，盲目替换会产生功能错误。

判断时比较两端生命周期：

- 进程级缓存、数据库、网络客户端可使用 Application Context；
- UI 控制器只在页面作用域内持有 Activity Context；
- 静态字段和单例不保存 View、Activity、Fragment 或以它们创建的短生命周期对象。

### Fragment View、监听器与观察者

Fragment 的生命周期可能长于它创建的 View。View Binding 应在 `onDestroyView()` 清空：

```kotlin
private var _binding: DetailBinding? = null
private val binding get() = requireNotNull(_binding)

override fun onCreateView(
    inflater: LayoutInflater,
    container: ViewGroup?,
    savedInstanceState: Bundle?
): View {
    _binding = DetailBinding.inflate(inflater, container, false)
    return binding.root
}

override fun onDestroyView() {
    adapter.onItemClick = null
    recyclerView.adapter = null
    _binding = null
    super.onDestroyView()
}
```

这里同时断开 Adapter 回调和 RecyclerView 对 Adapter 的引用。广播接收器、ContentObserver、传感器监听器、WebView 回调及第三方 SDK listener 也要在与注册点对应的时机注销。

### LeakCanary 与 Heap Dump

LeakCanary 适合在 debug 构建中自动观察已销毁组件和保留对象。依赖版本应从其官方安装页获取，避免把文档中的固定版本长期复制到项目。

发现泄漏后需要阅读引用链：

1. 确认对象已经离开业务生命周期；
2. 找到最靠近 GC Root 的业务强引用；
3. 判断它属于未取消任务、未注销注册、无界缓存，还是错误所有权；
4. 修复后重复同一路径，比较实例数和 retained size。

强制 GC 可用于测试工具确认“对象是否仍可达”，但不能进入业务修复方案。

## Native 内存：用所有权和调用栈定位

Native 侧没有 Java GC 代为调用 `free()` 或 `close()`。常见问题包括：

- `malloc/new` 与 `free/delete` 不配对，错误分支提前返回；
- `NewGlobalRef()` 缺少 `DeleteGlobalRef()`，导致 Java 对象也无法回收；
- `GetStringUTFChars()`、数组 pin/copy API 缺少相应 `Release*()`；
- `open()`、socket、`AHardwareBuffer`、codec 或图形 handle 缺少关闭；
- `DirectByteBuffer` 的 Java 包装对象与底层内存所有权不明确；
- 跨线程回调在 owner 销毁后仍使用 Native 指针。

C++ 代码优先用 RAII：`std::unique_ptr`、容器、带自定义 deleter 的智能指针和作用域封装能覆盖异常与提前返回。JNI 封装还要把线程附着、局部引用容量和全局引用的所有者写清楚。

### malloc debug

bionic 的 malloc debug 可以记录 Native 分配回溯，适合 root/userdebug 设备或平台开发环境。以下命令为目标进程设置包装属性，然后重启进程：

```bash
adb shell setprop wrap.com.example.app \
  '"LIBC_DEBUG_MALLOC_OPTIONS=backtrace logwrapper"'
adb shell am force-stop com.example.app
adb shell monkey -p com.example.app 1
```

复现问题后，可以让 `dumpsys meminfo` 搜索无法从已知根到达的 Native 块：

```bash
adb shell dumpsys meminfo --unreachable "$(adb shell pidof com.example.app)"
```

启用 backtrace 后，报告能提供更多分配来源。malloc debug 有显著开销，不适合作为长期线上开关；普通第三方应用在非 root 设备上应使用 debuggable `wrap.sh`、Sanitizer 或 heapprofd。完成测试后应清除 `wrap.<APP>` 属性并重启进程。

### HWASan、ASan 与 GWP-ASan

Android 17 的 64 位 Native 测试优先考虑 HWAddressSanitizer（HWASan），它擅长发现越界和 use-after-free。AddressSanitizer（ASan）仍可作为设备、ABI 或构建链限制下的替代方案。两者都更适合测试构建，不能只凭一次通过证明没有内存错误。

CMake 目标需要同时添加编译和链接选项。下面以 HWASan 为例：

```cmake
target_compile_options(native-lib PRIVATE
    -fsanitize=hwaddress
    -fno-omit-frame-pointer)
target_link_options(native-lib PRIVATE
    -fsanitize=hwaddress)
```

运行时库、系统镜像、ABI 和最低 API 要求应按所用 NDK 的官方指南配置。`doNotStrip` 只能影响符号保留，不能启用 Sanitizer。

GWP-ASan 使用抽样方式检测部分堆内存错误，开销更适合生产环境。Android 14 / API 34 起，可恢复的 GWP-ASan 默认覆盖所有应用；抽样意味着一次未命中不能排除问题。它用于发现越界和释放后使用，不负责统计长期 Native 泄漏。

### heapprofd

Perfetto 的 heapprofd 按采样记录 Native 分配和释放，并聚合调用栈，适合回答“哪条 Native 路径仍保留最多字节”。Android 10+ 支持该能力；user 版本通常要求目标应用可调试或允许 profiling。

主机侧快速采集可使用当前 `heap_profile` 子命令：

```bash
tools/heap_profile android \
  -n com.example.app \
  --interval=16000
```

默认采样间隔为 4096 字节。增大间隔会降低开销，也会降低小分配的可见性。采集结果要同时看 outstanding size、allocation count 和调用栈，不能只按累计分配量排序。

需要放进系统 Trace 时，可配置 `linux.heapprofd` 数据源：

```textproto
data_sources {
  config {
    name: "linux.heapprofd"
    heapprofd_config {
      process_cmdline: "com.example.app"
      sampling_interval_bytes: 16384
    }
  }
}
```

Android 12+ 还可用 `heaps: "com.android.art"` 采样 Java 堆分配。它与完整 Heap Dump 的目标不同：采样更适合观察分配来源和趋势，Heap Dump 更适合追踪具体对象引用。

## `onTrimMemory`：把它当作释放机会

### Android 14 之后的回调范围

`ComponentCallbacks2` 的 trim level 是历史演进接口。Android 14 / API 34 起，平台不再向应用发送以下已废弃 level：

- `TRIM_MEMORY_RUNNING_MODERATE`（5）
- `TRIM_MEMORY_RUNNING_LOW`（10）
- `TRIM_MEMORY_RUNNING_CRITICAL`（15）
- `TRIM_MEMORY_MODERATE`（60）
- `TRIM_MEMORY_COMPLETE`（80）

仍会发送的公开 level 是：

- `TRIM_MEMORY_UI_HIDDEN`（20）：进程的 UI 已不可见，适合释放只服务于可见界面的资源；
- `TRIM_MEMORY_BACKGROUND`（40）：进程处于后台 LRU，适合缩减可重建缓存。

所以 `TRIM_MEMORY_COMPLETE` 已不能作为现代 Android 的“即将被杀”通知。系统可以在没有先发高等级 trim 回调的情况下终止缓存进程，关键状态应按正常生命周期及时持久化。

### Android 17 的 App 侧分发

在 `android-17.0.0_r1` 中，`ActivityThread.ApplicationThread.scheduleTrimMemory()` 接到 Binder 调用后，会优先把处理安排到主线程 `Choreographer.CALLBACK_COMMIT`，让回调位于绘制帧之后，以降低卡顿风险；没有可用 Choreographer 时退回 Handler。

随后私有方法 `ActivityThread.handleTrimMemory()` 收集进程内的 `ComponentCallbacks2` 并分发，最终通知 WindowManager。通过 `Application.registerComponentCallbacks()` 注册的对象由 Application 的 callback controller 继续分发。业务不能依赖各回调的相对顺序。

Android 17 还有两条需要知道的系统边界：

- 配置标志 `skipBgMemTrimOnFgApp` 可以让重要前台进程跳过 background-or-higher 的 trim；
- `CachedAppOptimizer` 在部分缓存进程进入冻结调度前发送 `TRIM_MEMORY_BACKGROUND`，该回调是异步的，系统不会等待应用完成清理。

回调在主线程执行，应只做快速、可预测的操作。耗时压缩、磁盘写入或遍历超大缓存会把内存响应变成卡顿。

### 推荐响应策略

以下实现只依赖 Android 14+ 仍投递的 level：

```kotlin
override fun onTrimMemory(level: Int) {
    when {
        level >= ComponentCallbacks2.TRIM_MEMORY_BACKGROUND -> {
            imageCache.trimTo(backgroundLimitBytes)
            decodedDocumentCache.clear()
        }
        level >= ComponentCallbacks2.TRIM_MEMORY_UI_HIDDEN -> {
            prefetchQueue.cancelAll()
            visibleOnlyCache.clear()
        }
    }
}
```

`UI_HIDDEN` 不等于内存压力，只说明 UI 不可见；响应动作应当便宜且可重建。支持 Android 8～13 的应用仍可能收到旧 level，可在兼容分支中渐进缩容，但不能让核心状态依赖这些回调。

进程级缓存可以在 `Application` 实现 `ComponentCallbacks2`，短生命周期组件也可以注册独立回调。后者离开作用域时必须调用 `unregisterComponentCallbacks()`，避免注册表继续持有它。

## 16 KB Page Size

Android 15 起 AOSP 支持 16 KB page size。自 2025 年 11 月 1 日起，Google Play 要求面向 Android 15 / API 35+ 设备的新应用和更新在 64 位设备上支持 16 KB page size。

纯 Java/Kotlin 应用只有在所有依赖也不包含 Native 代码时，通常无需源码修改，仍应在 16 KiB 环境测试。包含 `.so` 的应用需要同时检查：

- 自有 Native 库；
- AAR、SDK、游戏引擎和预编译库中的 `.so`；
- APK/AAB 打包时的未压缩库对齐；
- 代码中硬编码的 `4096`、页对齐和 `mmap` 假设。

AGP 8.5.1+、NDK r28+ 和兼容的预编译依赖可提供默认支持。NDK r27 及更早版本需要按构建链配置兼容选项；直接控制链接器时，至少同时设置以下参数：

```cmake
target_link_options(native-lib PRIVATE
    "-Wl,-z,max-page-size=16384"
    "-Wl,-z,common-page-size=16384")
```

代码应在运行时获取页大小：

```c
long page_size = sysconf(_SC_PAGESIZE);
if (page_size <= 0) {
    /* 处理查询失败，不能回退到未经验证的 4096 假设 */
}
```

在目标设备和构建产物上分别验证：

```bash
adb shell getconf PAGE_SIZE
zipalign -c -P 16 -v 4 app-release.apk
```

16 KiB 页可能减少 TLB miss 和部分启动开销，也可能增加小映射或页内碎片带来的内存消耗。收益取决于工作负载，不能写成所有应用都会更快。Bitmap、GraphicBuffer 和 allocator 的变化应通过同机 4 KiB/16 KiB 对照测量。

## Jetpack Compose 的内存边界

Compose 改变了 UI 对象的组织方式，但生命周期和所有权原则没有改变：

- `remember` 的值在对应 composable 留在 Composition 且 key 不变时保留；节点被移除或 key 变化后会被遗忘；
- `rememberSaveable` 的状态要写入 Bundle，不应保存 Bitmap、大数组或复杂对象图；
- `DisposableEffect` 适合成对注册/注销 listener、observer 和其他外部资源；
- Flow 和生命周期数据应使用生命周期感知的收集方式；
- Lazy 列表提供稳定 key，避免因位置变化丢失或重建错误状态；
- 排序、解析和大集合转换移出高频重组路径，必要时使用 `derivedStateOf` 等工具，但先测量重组与分配。

`remember` 不是通用缓存。把 Activity Context、大 Bitmap 或播放器长期记在高层 Composition，会使它们跟随该节点存活。资源已有 ViewModel、图片库或进程级 owner 时，Composable 只保存轻量句柄和展示状态。

## 大型应用的内存预算

固定的“核心 30%、业务 40%、缓存 20%、预留 10%”缺少设备和场景依据。更可用的预算来自重复测试。

### 建立设备与场景分组

先按总 RAM、low-RAM 标志、API、ABI、屏幕尺寸和 page size 选择代表设备，再固定场景：

- 冷启动、首页稳定、前后台切换；
- 长列表快速滚动并返回；
- 大图、视频、地图、相机或文档等峰值业务；
- 页面反复进入退出、旋转和多窗口；
- 低内存回调、后台冻结与恢复。

每个场景记录稳定值、峰值、退出后的回落值以及多轮后的基线漂移。至少区分 Java、Native、Graphics、总 PSS/RSS、swap、FD 和关键对象数量，并观察 p50、p95、p99，而非只保留平均值。

### 正确理解 heap class

`ActivityManager.getMemoryClass()` 返回普通应用近似的受管理堆等级，`getLargeMemoryClass()` 对应声明 `largeHeap` 后的等级。它们不是进程总 PSS 上限，也不包含所有 Native、Graphics 和共享内存。

下面的计算只能估算 Java 堆当前已用量与可增长余量：

```kotlin
val runtime = Runtime.getRuntime()
val javaUsed = runtime.totalMemory() - runtime.freeMemory()
val javaHeadroom = runtime.maxMemory() - javaUsed
```

它不能回答 Bitmap、dmabuf 或 Native 堆还有多少空间。缓存上限应同时参考设备档位、业务峰值和系统回收信号，并为突发分配保留经过压测的余量。

### 采样成本与指标解释

`Debug.getPss()` 从 API 14 可用，`Debug.getRss()` 从 API 35 可用。PSS 统计需要读取和归并内存映射，不能每帧轮询。生产采样应低频、限量，并在设备上评估成本。

`Debug.MemoryInfo.nativePss` 不能换算 Bitmap 数量。Bitmap 对象统计可看 `dumpsys meminfo <package>` 的对象区、Heap Dump 或图片库自身的请求/缓存指标；Graphics 和 dmabuf 还需要对应的系统计数器。

## 线上诊断

### `ApplicationExitInfo`

Android 11 / API 30 起，`ActivityManager.getHistoricalProcessExitReasons()` 可以回查进程退出记录。`ApplicationExitInfo` 提供 reason、importance、description、trace，以及最终采样到的 PSS/RSS。

这些 PSS/RSS 值可能为 0，也不保证等于死亡瞬间峰值。`REASON_LOW_MEMORY` 能说明系统按低内存原因记录了退出，仍需结合设备内存档位、业务场景和版本分布分析。

Android vitals 的用户可感知低内存终止率适合观察整体影响。它能指出问题规模，定位仍要依靠可复现路径、退出信息和内存采样。

### `ProfilingManager`

Android 15 / API 35 引入 `ProfilingManager`，应用可以请求由系统管理的 profiling 采集。Android 17 / API 37 的 `ProfilingTrigger` 增加：

- `TRIGGER_TYPE_OOM`：应用发生未捕获的 `OutOfMemoryError` 时触发 Java Heap Dump；自定义 `UncaughtExceptionHandler` 必须继续调用默认 handler；
- `TRIGGER_TYPE_ANOMALY`：由系统检测异常并触发相应 artifact。

该能力受系统策略、速率限制和用户构建条件约束，不能保证每次异常都有产物。接入时要记录请求结果、回调状态、文件上传策略和隐私边界。

### 从现象选择工具

| 现象 | 首选证据 |
| --- | --- |
| 页面退出后 Java 对象不回落 | LeakCanary、Heap Dump 引用链 |
| 滚动时分配率高并伴随卡顿 | Allocation recording、Perfetto FrameTimeline 与 GC |
| Native PSS 持续上涨 | heapprofd、malloc debug、HWASan/ASan |
| Graphics/dmabuf 上涨 | `dumpsys meminfo`、memtrack、dmabuf/Surface 相关 Trace |
| 后台进程频繁消失 | `ApplicationExitInfo`、Android vitals、lmkd/系统内存压力 |
| FD 持续增长 | `/proc/self/fd`、StrictMode、资源所有权审查 |

## PSS 与 CPU cache locality 分属不同层级

内存占用和访问效率可能同时改善或恶化，但测量对象不同：

| 粒度 | 典型大小与职责 | 主要证据 |
|---|---|---|
| CPU cache line | 由目标 CPU 决定；承载 cache 传输与一致性 | PMU、simpleperf、调度与 CPU 拓扑 |
| 基础 page | 4 KiB 或 16 KiB；承载映射、fault、RSS/PSS | `smaps`、page fault、Perfetto process stats |
| ART card | Android 17 为 1024 B 地址范围；记录引用写入候选 | ART GC trace 与源码 |

PSS 由内核按驻留页的 mapcount 分摊。`Debug.MemoryInfo` 的详细路径读取 `smaps` 并加入 memtrack，快速 `Debug.getPss()` 则由 libmeminfo 在 rollup 与完整 smaps 之间选择。CPU 换核、cache miss 或 false sharing 不会直接改变 PSS 算法；它们只有在改变实际触页、对象布局或工作集后，才可能间接影响驻留页。

优化局部性时，应保持工作量、线程亲和与设备状态一致，分别采集结构体/数组布局和访问顺序、CPU/cluster 调度、目标设备支持的 PMU cache 事件，以及相同时间窗内的 RSS/PSS。不要用 “PSS 下降” 代替 cache miss 证据，也不要用单个 cache-miss 计数证明内存占用已经优化。

## 从轻量计数逐级进入 profiler

Perfetto 中常用的四个内存数据源回答不同问题：

| 数据源 | 回答的问题 | 主要限制 |
|---|---|---|
| `linux.process_stats` | 进程 RSS、状态和 adj 如何变化 | 完整 PSS 需要显式 `scan_smaps_rollup`，且受 procfs/ptrace 权限限制 |
| `linux.sys_stats` | meminfo、vmstat、PSI、buddyinfo 的系统背景 | 每类字段需要在配置中显式开启 |
| `android.heapprofd` | 哪些 native 分配调用栈仍有存活采样 | 采样间隔、unwind 和传输会增加开销，且不覆盖所有 mapping/驱动内存 |
| `android.java_hprof` | 哪些 managed object 被谁保留 | 重量级对象图快照，会暂停并增加目标进程内存 |

`linux.process_stats` 的周期下限是 100 ms，但下限不是推荐频率。heapprofd 的 `sampling_interval_bytes` 越小，调用栈与传输成本通常越高；`all=true` 会尝试覆盖大量合格进程，不适合作为普通诊断默认值。使用 `block_client` 还可能直接拖慢目标进程。

一轮可复现的调查按以下顺序加深：

1. 固定用户可见问题、设备、build 和时间区间。
2. 用 process/sys stats、调度、fault/reclaim 与少量 `dumpsys meminfo` 判断 Java、native、graphics、mapping、swap 或系统 pressure 中哪一层异常。
3. 只对命中的方向启用 Java HPROF、heapprofd、memtrack/DMA-BUF、MTE 或内核 compaction 证据。
4. 保存完整 Perfetto config、采样间隔、目标 PID、profileable 状态和 profiler 自身 CPU/内存开销。
5. 用同一工作量比较优化前后，不把 profiler on/off 两组数据直接混为产品收益。

最后把“释放”拆成四个时刻：业务断开引用、GC/allocator 标为空闲、runtime/allocator 归还页面、内核回收后 RSS/PSS 下降。对象不可达后 PSS 没有立刻下降，不足以证明泄漏；PSS 暂时下降也不能证明所有权问题已经修复。

## 常见误区

### `System.gc()` 能修复内存问题

`System.gc()` 只是向运行时提出显式 GC 请求。它可能增加回收工作和暂停，无法回收仍可从 GC Root 到达的泄漏对象，也不能关闭 FD 或释放所有 Native owner。受控测试可以在断开引用后借它辅助验证，生产路径应修复引用、所有权和分配行为。

### Android 8+ 的 Bitmap 不会 OOM

API 26+ 像素位于 Native 侧，平台仍登记这部分分配，进程也仍受物理内存和系统策略约束。只盯 `Runtime.maxMemory()` 会漏掉 Bitmap、Graphics 和 dmabuf 压力。

### 每次用完 Bitmap 都调用 `recycle()`

`recycle()` 会立即让像素不可用。共享给 View、Drawable、异步任务或图片库的 Bitmap 不能由局部代码擅自回收。现代应用优先使用清晰所有权和库提供的释放 API。

### `onTrimMemory` 会提前通知进程死亡

Android 14+ 只保留 `UI_HIDDEN` 和 `BACKGROUND` 两个公开投递 level，系统可以直接终止缓存进程。内存缩减回调只负责快速释放可重建资源，状态保存仍要遵守正常生命周期。

### `largeHeap` 可以解决所有 OOM

`largeHeap` 只改变设备为应用提供的受管理堆等级，具体大小由设备决定。它不修复泄漏，不扩大 FD 上限，也不消除 Native、Graphics 或 Android 17 MemoryLimiter 带来的进程压力。只有业务确有大 Java 堆需求并经过多档设备验证时才应使用。

### 高端设备可以忽略内存抖动

高端设备 CPU 更快，但高刷新率也缩短了帧间隔。结论必须来自目标设备的 FrameTimeline、GC 与分配数据。低端设备关注总量和回收压力，高刷设备还要关注暂停与帧工作的重叠。

## 复核清单

- [ ] 是否分别观察 Java、Native、Graphics/dmabuf、PSS/RSS、swap 和 FD？
- [ ] 是否用可复现 Trace 证明高频分配或 GC 与帧问题有关？
- [ ] Bitmap 是否按目标尺寸解码，并遵守 `inBitmap`、硬件 Bitmap 和 `recycle()` 的所有权？
- [ ] Activity、Fragment View、Handler、listener、observer 和协程是否在正确生命周期解绑？
- [ ] JNI 的内存、全局引用、字符/数组访问和 FD 是否成对释放？
- [ ] `onTrimMemory` 是否只做快速、可重建的资源缩减，并兼容 API 34+ 行为？
- [ ] 所有 Native 依赖是否通过 16 KB page size 构建与设备验证？
- [ ] Compose 是否避免在 Composition 或 Bundle 中保存大对象？
- [ ] 内存预算是否来自设备×场景的 p50/p95/p99 与回落数据？
- [ ] 线上退出指标是否能关联版本、设备档位和业务场景？

---

## 参考资料

### AOSP Android 17 源码

- `frameworks/base/graphics/java/android/graphics/Bitmap.java`：Native 分配注册、硬件 Bitmap、Parcel 与 `recycle()`
- `frameworks/base/graphics/java/android/graphics/BitmapFactory.java`：解码与 `inBitmap`
- `frameworks/base/core/java/android/app/ActivityThread.java`：`scheduleTrimMemory()` 与主线程分发
- `frameworks/base/core/java/android/app/Application.java`：注册回调的分发
- `frameworks/base/core/java/android/content/ComponentCallbacks2.java`：trim level 公共契约
- `frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java`：冻结前的后台 trim
- `packages/modules/Profiling/framework/java/android/os/ProfilingManager.java`、`ProfilingTrigger.java`：系统 profiling 与 API 37 trigger

以上源码均以 `android-17.0.0_r1` 为核查锚点。

### 官方文档

- [Memory overview](https://developer.android.com/topic/performance/memory)
- [Manage Bitmap memory](https://developer.android.com/topic/performance/graphics/manage-memory)
- [BitmapFactory.Options.inBitmap](https://developer.android.com/reference/android/graphics/BitmapFactory.Options#inBitmap)
- [Bitmap.Config.HARDWARE](https://developer.android.com/reference/android/graphics/Bitmap.Config#HARDWARE)
- [Support 16 KB page sizes](https://developer.android.com/guide/practices/page-sizes)
- [Debug native Android platform code](https://developer.android.com/ndk/guides/debug)
- [HWAddressSanitizer](https://developer.android.com/ndk/guides/hwasan)
- [GWP-ASan](https://developer.android.com/ndk/guides/gwp-asan)
- [heapprofd](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [ApplicationExitInfo](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [ProfilingManager](https://developer.android.com/reference/android/os/ProfilingManager)
- [Glide configuration](https://bumptech.github.io/glide/doc/configuration.html)
- [Coil ImageLoaders](https://coil-kt.github.io/coil/image_loaders/)
- [Fresco caches](https://frescolib.org/docs/caching.html)
- [LeakCanary](https://square.github.io/leakcanary/)

### 交叉阅读

- 4.1「Android 内存模型全景」：进程内存口径
- 4.2「Linux 内存管理」：页、回收与内核压力
- 4.3「ART 虚拟机内存管理」：分配与 GC
- 4.4「系统内存压力与 lmkd」：压力检测、优先级与进程终止
- 4.6「16 KB Page Size」：构建、加载与兼容性细节
- 7.2、7.3：卡顿分类与 Perfetto 分析
