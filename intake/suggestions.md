# General Suggestions and Improvements
**external. 二、总体结论**
- 章节：14.8
**external. 二、总体结论**
- 问题类型：数据支撑
**external. 二、总体结论**
- 位置：实战案例 1-3
**external. 二、总体结论**
- 问题描述：缺乏真实实测数据支撑，目前多为经验数值估计。
**external. 二、总体结论**
- 建议：收集设备上真实的 trace 记录，并替换为真实业务数据。
**external. 二、总体结论**
- **章节**：14.5 / 15.5
**external. 二、总体结论**
- **类型**：建议补充
**external. 二、总体结论**
- **位置**：Booster 章节
**external. 二、总体结论**
- **描述**：AGP 8.0 Transform 替代方案可以提供更清晰的 API 指引。
**external. 二、总体结论**
- **建议**：明确提及 `AsmClassVisitorFactory`。
**external. 二、总体结论**
- 章节：14.10
**external. 二、总体结论**
- 问题类型：原理链完整性
**external. 二、总体结论**
- 位置：UprobeStats 与动态埋点
**external. 二、总体结论**
- 问题描述：缺少 Mainline 升级特性的明确说明。
**external. 二、总体结论**
- 建议：补充说明 UprobeStats APEX 模块具备 Mainline 独立升级特性。
**external. 二、总体结论**
- 章节：15.13 Hook 基础设施与性能工具实现原理
**external. 二、总体结论**
- 问题类型：内容缺失
**external. 二、总体结论**
- 位置：第一条路线：系统回调 / 官方接口
**external. 二、总体结论**
- 问题描述：未提及 JVMTI。
**external. 二、总体结论**
- 建议：补充 JVMTI (Android 8.0+) 作为线下最强大的官方监控基础设施。
**external. 二、总体结论**
- **章节**：14.6 / 15.6
**external. 二、总体结论**
- **类型**：建议改进
**external. 二、总体结论**
- **位置**：指标测量章节
**external. 二、总体结论**
- **描述**：强化 TTFD 和 `reportFullyDrawn()` 的绑定关系。
**external. 二、总体结论**
- 章节：14.3 / 15.3 内存分析工具
**external. 二、总体结论**
- 问题类型：知识更新
**external. 二、总体结论**
- 位置：HWASAN 与 MTE
**external. 二、总体结论**
- 问题描述：MTE 的 Async 模式描述过时。
**external. 二、总体结论**
- 建议：补充说明在支持 Armv9.2 的设备上，Async 模式会透明转换为 ASYMM 模式。
**external. 二、总体结论**
- 章节：14.2 / 15.2 Simpleperf
**external. 二、总体结论**
- 问题类型：知识盲区
**external. 二、总体结论**
- 位置：符号解析
**external. 二、总体结论**
- 问题描述：仅提到了 C/C++ 符号解析，遗漏了新兴的 Rust 支持。
**external. 二、总体结论**
- 建议：在 Native 符号解析中提及对 Rust Demangling 的支持。
**external. 二、总体结论**
- 章节：15.1 Android Studio Profiler
**external. 二、总体结论**
- 问题类型：版本差异
**external. 二、总体结论**
- 位置：Power Profiler
**external. 二、总体结论**
- 问题描述：ODPM 设备支持范围表述过窄。
**external. 二、总体结论**
- 建议：调整为“Pixel 6+ 及部分支持 ODPM 硬件的旗舰设备”。
**external. 二、总体结论**
- 章节：15.12 APM / 可观测性平台与 SDK 选型
**external. 二、总体结论**
- 问题类型：案例支撑
**external. 二、总体结论**
- 位置：第二层：客户端增强层
**external. 二、总体结论**
- 问题描述：介绍开源库时太过高层，缺少技术内核描述。
**external. 二、总体结论**
- 建议：补充 KOOM 的 fork-dump 机制和 btrace 的 ASM 机制一句话简介。
**external. 二、总体结论**
- **章节**：14.7 / 15.7
**external. 二、总体结论**
- **类型**：建议改进
**external. 二、总体结论**
- **位置**：第五节
**external. 二、总体结论**
- **描述**：提及 Extension 版本时可增加具体调用的示例。
**external. 二、总体结论**
- **建议**：补充一句“例如通过 `SdkExtensions.getExtensionVersion` 校验 extension 级别”。
**external. 二、总体结论**
- 章节：14.9
**external. 二、总体结论**
- 问题类型：数据支撑
**external. 二、总体结论**
- 位置：Camera 功耗优化
**external. 二、总体结论**
- 问题描述：补充部分功耗基线数据。
**external. 二、总体结论**
- 建议：加入具体的毫安 (mA) 测试数据对比或功耗百分比对比示例。
**external. 二、总体结论**
- 章节：14.4 / 15.4 dumpsys 系列命令
**external. 二、总体结论**
- 问题类型：表述更新
**external. 二、总体结论**
- 位置：dumpsys SurfaceFlinger
**external. 二、总体结论**
- 问题描述：提到 GLES 合成退回时，未体现最新的 Vulkan 趋势。
**external. 二、总体结论**
- 建议：可简要提及 RenderEngine 默认驱动正在转向 ANGLE/Vulkan，Dump 中会反映这一变化。
**external. 二、总体结论**
- 章节：15.11 Battery Historian 与功耗分析工具
**external. 二、总体结论**
- 问题类型：数据/案例支撑
**external. 二、总体结论**
- 位置：模式分析部分
**external. 二、总体结论**
- 问题描述：缺乏具体代码片段。
**external. 二、总体结论**
- 建议：补充 Wakelock 未释放等典型反例的小段代码。
## [Task9 Deep Review] 8.3 启动优化机制 — 2026-04-22
- **类型**：版本差异
- **位置**：SplashScreen 持续时间
- **问题**：需要标注适用版本和配置要求
- **建议**：需要SplashScreen 持续时间相关技术验证和修正
- **类型**：知识盲区
- **位置**：Baseline Profiles
- **问题**：缺少 ART Mainline 相关说明
- **建议**：需要Baseline Profiles相关技术验证和修正

## [Task9 Deep Review] 13.2 Trace 捕捉配置 — 2026-04-22
- **类型**：知识盲区
- **位置**：record_android_trace
- **问题**：缺少脚本位置和分支说明
- **建议**：需要record_android_trace相关技术验证和修正
- **类型**：版本差异
- **位置**：Java Heap Sampling
- **问题**：使用 android.surfaceflinger.frametimeline 仅支持 Android 12+
- **建议**：需要Java Heap Sampling相关技术验证和修正

## [Task9 Deep Review] 13.8 输入延迟 SQL 查询 — 2026-04-22
- **类型**：版本差异
- **位置**：android.input.inputevent
- **问题**：仅支持 debug 构建
- **建议**：需要android.input.inputevent相关技术验证和修正
- **类型**：数据支撑
- **位置**：参考值
- **问题**：缺少 trace ID 或捕获配置，数据可复现性存疑
- **建议**：需要参考值相关技术验证和修正

## [External Review] 7.1 卡顿的定义与分类 — 2026-04-22
- **类型**：源码准确性
- **位置**：Google 的 Jank 分类体系 - AppDeadlineMissed
- **问题**：提到 `终点取 max(gpu time, post time)`。
- **建议**：建议将 `post time` 进一步澄清为 App 调用 `queueBuffer` 将 Buffer 提交给 BufferQueue 的时间，以便读者和 Systrace/Perfetto 中的 `queueBuffer` 动作对应起来。
- **来源**：Gemini 外部 review


## [External Review] 7.1 卡顿的定义与分类 — 2026-04-22
- **类型**：知识盲区
- **位置**：不同刷新率下的帧预算
- **问题**：提到了 VSync-app 和 VSync-sf 错峰推进。
- **建议**：可以简单补充一句：这种错峰是通过 `appPhase` 和 `sfPhase`（VSync Offset）来实现的，允许 App 提前被唤醒进行渲染。
- **来源**：Gemini 外部 review


## [External Review] 7.10 图片与 Bitmap 性能优化 — 2026-04-22
- **类型**：版本差异覆盖
- **位置**：AVIF 格式解码
- **问题**：提及 Android 12 支持 AVIF 基础支持，Android 14 强制要求 AV1 硬件解码。
- **建议**：补充在低版本系统上通过集成 C++ 库实现 AVIF 软解的常见工程实践方案，以增强实战指导意义。
- **来源**：Gemini 外部 review


## [External Review] 7.11 WebView 渲染性能 — 2026-04-22
- **类型**：原理链完整性
- **位置**：JS Bridge 与主线程阻塞
- **问题**：解释了 evaluateJavascript 同步阻塞引发 ANR。
- **建议**：补充一条建议：JS Bridge 不适合高频度（如 `onScroll` 中的每一帧）传递大量数据，大量数据应采用序列化或 ArrayBuffer，避免高频 IPC 卡顿。
- **来源**：Gemini 外部 review


## [External Review] 7.12 View 体系性能优化 — 2026-04-22
- **类型**：知识盲区
- **位置**：Perfetto 观测点
- **问题**：定位具体 View 的耗时仅提到了手动 trace、Layout Inspector 和业务埋点。
- **建议**：建议补充通过系统属性或 `ViewDebug` 开启更详细 View 树 trace 的方法，这对于没有 App 源码的系统级性能分析非常有用。
- **来源**：Gemini 外部 review


## [External Review] 7.12 View 体系性能优化 — 2026-04-22
- **类型**：原理链完整性
- **位置**：MeasureSpec 传递
- **问题**：对 `MeasureSpec` 的描述停留在 32 位整数的高 2 位和低 30 位，未深入解释 `ViewGroup.getChildMeasureSpec()` 的计算矩阵。
- **建议**：建议用简表或核心伪代码展示 `getChildMeasureSpec` 的逻辑，特别是 `AT_MOST` 遇到 `WRAP_CONTENT` 的处理。
- **来源**：Gemini 外部 review


## [External Review] 7.13 SystemUI 性能分析 — 2026-04-22
- **类型**：版本差异覆盖
- **位置**：通知内容绑定 / Android 15+ 演进
- **问题**：详细介绍了 Android 15+ 的 `NotificationIconContainerStatusBarViewModel`，但未提及 SystemUI 正在进行的重大架构演进 SceneContainer (内部代号 Flexiglass)。
- **建议**：建议在版本边界或扩展部分简单提及 Flexiglass / SceneContainer 重构对 `NotificationShadeWindowView` 的潜在影响。
- **来源**：Gemini 外部 review


## [External Review] 7.13 SystemUI 性能分析 — 2026-04-22
- **类型**：知识盲区
- **位置**：多显示器与双屏设备
- **问题**：通篇基于单屏手机的形态展开。
- **建议**：简要提及大屏形态下多窗口或展开态对 SystemUI 带来的渲染负担倍增效应。
- **来源**：Gemini 外部 review


## [External Review] 7.14 GAPS 动态分析 — 2026-04-22
- **类型**：原理链完整性
- **位置**：动态驱动原理
- **问题**：在“把结果落成 JSON 指令”和“运行期按指令驱动应用”环节，缺乏对具体 UI 驱动方式（如点击的具体坐标、资源解析后的匹配）在不同 Android 版本兼容性的深入说明。
- **建议**：建议简要补充一句，指出纯资源 ID 驱动在复杂动态界面（如列表或动态下发 UI）中的脆弱性，说明工程化时通常需要结合 AccessibilityService。
- **来源**：Gemini 外部 review


## [External Review] 7.15 场景化性能作战手册 — 2026-04-22
- **类型**：实战指导
- **位置**：抓 trace 的方式
- **问题**：在“抓 trace 时，先求回答问题，不求一次最全”小节中，给出了抓取策略，但没给出最快的工具手段。
- **建议**：增加一行提示，建议使用 `Traceur` 的快捷磁贴（Quick Settings Tile）用于抓取突发的偶现滑动/输入卡顿，或者使用 `adb shell perfetto -c` 获取包含内存或特殊 atrace 标签的长时日志。
- **来源**：Gemini 外部 review


## [External Review] 7.2 卡顿原因体系 — 2026-04-22
- **类型**：源码准确性
- **位置**：Binder 调用导致的主线程阻塞
- **问题**：提到了 SurfaceFlinger 的 Binder 瓶颈（dequeueBuffer, queueBuffer）。
- **建议**：明确提及 `BufferQueueCore` 的内部 `mMutex` 锁竞争。
- **来源**：Gemini 外部 review


## [External Review] 7.2 卡顿原因体系 — 2026-04-22
- **类型**：原理链完整性
- **位置**：误区四：「RenderThread 在独立线程，所以不会影响主线程」
- **问题**：提到了 `syncAndDrawFrame` 阶段主线程需要将 DisplayList 同步给 RenderThread。
- **建议**：补充提到在 Perfetto trace 中，主线程会因为等待 RenderThread 表现为一个长 `syncFrameState` 的 block/sleeping 状态。
- **来源**：Gemini 外部 review


## [External Review] 7.3 卡顿分析方法论 — 2026-04-22
- **类型**：原理链完整性
- **位置**：分析 CPU 调度问题的工具技巧
- **问题**：列举了分析 CPU 调度的工具技巧，如 CPU Info 区域。
- **建议**：在分析工具技巧中，补充：点击主线程异常长的 `binder transaction` slice，在 flow events 中跳转到接收端进程的线程，查看接收端是 Blocked 还是 Running 状态，这是定位跨进程锁竞争的核心。
- **来源**：Gemini 外部 review


## [External Review] 7.4 典型场景的卡顿根因分析 — 2026-04-22
- **类型**：内容缺失
- **位置**：第七章 扩展
- **问题**：存在多处 `[待补充]` 内容。
- **建议**：移除待补充标记，补充实质性摘要或单独立项。
- **来源**：Gemini 外部 review


## [External Review] 7.5 流畅性优化策略 — 2026-04-22
- **类型**：内容改进
- **位置**：线程优化：耗时操作异步化
- **问题**：可以进一步强化 UI 线程和 RenderThread 交互时的资源竞争概念。
- **建议**：无特殊，可酌情补充。
- **来源**：Gemini 外部 review


## [External Review] 7.6 案例实战分析 — 2026-04-22
- **类型**：代码严谨性
- **位置**：案例三：修复方案
- **问题**：LruCache 容量计算直接使用 `Runtime.maxMemory()` 存在 largeHeap 隐患。
- **建议**：建议改为 `ActivityManager.getMemoryClass()`，并加入注释说明。
- **来源**：Gemini 外部 review


## [External Review] 7.7 Compose 性能优化 — 2026-04-22
- **类型**：内容完善
- **位置**：混合布局
- **问题**：可以补充说明 `AndroidView` 中过度调用 `update` 方法带来的开销。
- **建议**：无特殊。
- **来源**：Gemini 外部 review


## [External Review] 7.8 RecyclerView 深度优化 — 2026-04-22
- **类型**：数据/案例支撑
- **位置**：嵌套滑动的性能影响
- **问题**：提到了 ViewPager2 + 外层 RecyclerView。
- **建议**：在提及 ViewPager2 嵌套时，顺带提一句 ViewPager2 内置 RecyclerView 的获取方式及共享 Pool 的注意事项。
- **来源**：Gemini 外部 review


## [External Review] 7.9 感知流畅性 — 2026-04-22
- **类型**：数据/案例支撑
- **位置**：在应用侧同步采样位移
- **问题**：给出的 `StepJitterProbe` 示例代码虽然说明了概念，但缺少了平滑处理的手段示范。
- **建议**：提供一段如何使用 `doFrame` 传入的 `frameTimeNanos` 进行浮点级位移计算的伪代码，作为“解决毫秒量化问题”的正面示例。
- **来源**：Gemini 外部 review

## [External Review] 15.10 eBPF 性能分析 — 2026-04-22
- **类型**：原理链完整性
- **位置**：4 UprobeStats 与动态埋点
- **问题**：描述了 UprobeStats 作为 APEX 模块依赖 config push 来工作。
- **建议**：加入一句话简要提及该模块属于 Project Mainline，可通过 Google Play 系统更新独立升级。
- **来源**：Gemini 外部 review


## [External Review] 15.11 Battery Historian — 2026-04-22
- **类型**：数据/案例支撑
- **位置**：从 Battery Historian 到根因定位
- **问题**：提供了模式 1、2、3、4 的文字描述，但未给出一段典型的高耗电代码及 Trace 对应截图说明。
- **建议**：提供一到两个微型的代码反例（例如一个持有不放的 WakeLock 代码），以及它在 dumpsys checkin 文本里的样子，加深实战体感。
- **来源**：Gemini 外部 review


## [External Review] 15.12 APM 可观测性平台 — 2026-04-22
- **类型**：数据/案例支撑
- **位置**：第二层：客户端增强层
- **问题**：泛泛谈到了 btrace / KOOM / Matrix 的优势，但缺少技术上的“它是怎么做到的”的说明。
- **建议**：在介绍这些工具时，用一两句话点出它们的**核心黑科技**（如 fork dump、ASM 插桩），这才是硬核技术文档的特色。
- **来源**：Gemini 外部 review


## [External Review] 15.3 内存分析工具 — 2026-04-22
- **类型**：知识盲区
- **位置**：HWASAN 与 MTE
- **问题**：关于 MTE 的描述“开发者选项启用异步 MTE 模式（async mode）”不够准确和与时俱进。
- **建议**：在 MTE 段落更新 Android 15 下的默认状态及 ASYMM 模式。
- **来源**：Gemini 外部 review


## [External Review] 15.4 dumpsys 系列命令 — 2026-04-22
- **类型**：知识更新
- **位置**：dumpsys SurfaceFlinger
- **问题**：仍然以“GLES”作为非硬件合成的主要代名词。
- **建议**：在解释 GLES 合成退回时，顺带提及 RenderEngine 的 Vulkan 化趋势。
- **来源**：Gemini 外部 review


## [External Review] 15.5 三方性能库 — 2026-04-22
- **类型**：原理链完整性
- **位置**：第四节 Booster
- **问题**：提到 AGP 8.0 彻底移除了 Transform API。
- **建议**：建议补充 AGP 8.0+ 之后具体的替代方案 API（`AsmClassVisitorFactory` / Artifacts API），让读者能知道如果要在 Android 15/AGP 8.x 的环境里写一个类似 Booster 的插件应该用什么 API。
- **来源**：Gemini 外部 review


## [External Review] 15.9 Camera 性能分析 — 2026-04-22
- **类型**：数据/案例支撑
- **位置**：Camera 功耗优化
- **问题**：标注有 `[待量化: 具体增幅因 SoC 和 Sensor 而异，暂缺通用基线]`。
- **建议**：提供一组典型中端/高端 SoC 在 1080p 30fps vs 60fps 下的电流消耗差异基线参考值，提升文章实战感。
- **来源**：Gemini 外部 review

## [External Review] 7.10 图片与 Bitmap 性能优化 — 2026-04-22
- **类型**：实战扩展
- **位置**：AVIF：压缩率的新天花板
- **问题**：未提及低版本通过自带 libavif 软解的工程实践。
- **建议**：提供一句话指引，说明可以通过 JNI 打包 libavif 解决 minSdk < 31 的软解问题。
- **来源**：Gemini 外部 review


## [External Review] 7.11 WebView 渲染性能 — 2026-04-22
- **类型**：优化实践
- **位置**：JS Bridge 与主线程阻塞
- **问题**：未提及高频跨语言 IPC 的性能影响。
- **建议**：指出 JS 与 Native 之间的高频调用（如滑动监听中逐帧调用桥接方法）会引发性能灾难。
- **来源**：Gemini 外部 review


## [External Review] 7.12 View 体系性能优化 — 2026-04-22
- **类型**：原理补充
- **位置**：`measure/layout` 的开销与 `requestLayout` -> `MeasureSpec` 的传递规则
- **问题**：缺少 `getChildMeasureSpec` 具体规则矩阵的说明。
- **建议**：补充一个小表格展示父 View 模式与子 View LayoutParams 是如何结合计算出子 View 的 MeasureSpec 的。
- **来源**：Gemini 外部 review


## [External Review] 7.13 SystemUI 性能分析 — 2026-04-22
- **类型**：版本差异补充
- **位置**：第一节“先分清谁负责什么”或最后总结处
- **问题**：缺少对 Android 15/16 正在进行的 SceneContainer (Flexiglass) 重构的提及。
- **建议**：加入一句话提醒读者：在 Android 15+ 主线中，SystemUI 正逐步向基于 Jetpack Compose 的 SceneContainer 架构迁移，未来 `NotificationShadeWindowView` 等传统容器将被 Compose 节点替代，Trace 分析重心将转向 Compose 渲染管线。
- **来源**：Gemini 外部 review


## [External Review] 7.14 GAPS 动态分析 — 2026-04-22
- **类型**：内容延伸
- **位置**：局限性：哪些场景会掉精度
- **问题**：未提及代码混淆与加壳对静态分析重建路径的毁灭性打击。
- **建议**：在局限性中补充：“严重的代码混淆 (R8/ProGuard) 以及商业加固方案会破坏类名和方法名映射，导致静态反向查找直接失败”。
- **来源**：Gemini 外部 review


## [External Review] 7.15 场景化性能作战手册 — 2026-04-22
- **类型**：内容补充
- **位置**：“抓 trace 时，先求回答问题，不求一次最全”
- **问题**：缺少落地抓取工具的指引。
- **建议**：补充一句话说明“建议配置 Quick Settings 中的 System Tracing 磁贴，以便在遇到偶发卡顿时能实现 3 秒内起手抓取，或者储备一份标准的 adb shell perfetto 配置文件以备长时抓取。”
- **来源**：Gemini 外部 review


## [External Review] 7.3 卡顿分析方法论 — 2026-04-22
- **类型**：实战技巧补充
- **位置**：分析 CPU 调度问题的工具技巧
- **问题**：缺少关于 Binder 跳转的具体操作步骤。
- **建议**：补充点击 `binder_transaction` slice 并通过 flow events 查看接收端线程状态的技巧。
- **来源**：Gemini 外部 review


## [External Review] 7.4 典型场景卡顿根因 — 2026-04-22
- **类型**：知识盲区
- **位置**：七、扩展：其他重渲染场景
- **问题**：
- **建议**：**：如果在当前版本不打算写，建议直接移除或保留一句话摘要。如果打算写，需要明确 MediaCodec 输出到 Surface 不走主线程，而是通过 SurfaceFlinger 直接合成；WebView 的卡顿应当看 Renderer 进程而非 App 主进程。
- **来源**：Gemini 外部 review


## [External Review] 7.5 流畅性优化策略 — 2026-04-22
- **类型**：知识盲区
- **位置**：RecyclerView 优化：SnapHelper
- **问题**：
- **建议**：**：补充对快速 Fling 时预取（Prefetch）可能存在的副作用说明（GapWorker 可能挤占过多时间片）。
- **来源**：Gemini 外部 review


## [External Review] 7.6 案例实战分析 — 2026-04-22
- **类型**：源码准确性
- **位置**：案例三：内存压力下 GC 频繁暂停主线程
- **问题**：
- **建议**：**：建议补充说明优先使用 `ActivityManager.getMemoryClass()` 来获取标准内存指标，或者在代码示例中加入对 `largeHeap` 风险的提示。
- **来源**：Gemini 外部 review


## [External Review] 7.7 Compose 性能优化 — 2026-04-22
- **类型**：版本差异覆盖
- **位置**：ComposeView：在传统布局中嵌入 Compose
- **问题**：
- **建议**：**：补充对 `ViewCompositionStrategy` 策略的说明。
- **来源**：Gemini 外部 review


## [External Review] 7.8 RecyclerView 深度优化 — 2026-04-22
- **类型**：原理断裂
- **位置**：GapWorker 预取机制
- **问题**：缺少对首次滑动的均值初始化策略说明。
- **建议**：在讲解 `willCreateInTime` 时补充：若均值为 0，则默认允许一次执行，这是导致列表“第一下发卡”的常见隐蔽原因。
- **来源**：Gemini 外部 review


## [External Review] 7.9 感知流畅性 — 2026-04-22
- **类型**：原理补充
- **位置**：成因三：Choreographer 把时间同步到 VSync
- **问题**：缺少对整数除法截断行为的强调。
- **建议**：明确指出 `frameTimeNanos / NANOS_PER_MS` 为截断行为，解释 2ns 的 VSync 微小抖动为何能引发 1ms 的大跳变。
- **来源**：Gemini 外部 review



## [Task9 Deep Review] 18.8 OpenGL ES 渲染链路 — 2026-04-22
- **类型**：交叉引用错误
- **位置**：L323-L327 / 交叉引用
- **问题**：末尾 [2.14 图形 API 演进] 与 [2.1 BufferQueue] 都链接到了目录 ../../part1-fundamentals/ch02-rendering/，不是实际章节文件。
- **建议**：分别改到 14-graphics-api-evolution.md 与 13-buffer-queue.md 的具体文件路径。


## [Task9 Deep Review] 18.12 Flutter 渲染链路 — 2026-04-22
- **类型**：数据缺失
- **位置**：L200-L213 / Perfetto 观察
- **问题**：Perfetto 章节仍保留两处 [待补充] 截图占位，缺少实际 Trace 轨道样例，导致 “Main/Dart Runner / Raster / SurfaceFlinger” 的识别方法没有实证落点。
- **建议**：补一组 SurfaceView mode 与 TextureView mode 的真实 Perfetto 截图或轨道观察清单，并写明采样条件。


## [Task9 Deep Review] 18.12 Flutter 渲染链路 — 2026-04-22
- **类型**：交叉引用错误
- **位置**：L220-L224 / 与其他章节的关系
- **问题**：“13.8 WebView 渲染性能” 在当前仓库里不存在；现有可对应章节是 7.11 WebView 性能优化或 18.13 WebView 渲染链路。
- **建议**：把交叉引用改到实际存在的章节，并明确是“性能优化”还是“渲染链路”视角。


## [Task9 Deep Review] 18.15 视频叠加与 HWC — 2026-04-22
- **类型**：数据缺失
- **位置**：L39-L41 / 开头功耗结论
- **问题**：“2-3x 内存带宽”“10-20% 功耗差异”没有给出设备、分辨率、codec、刷新率或测量工具，AOSP 源码本身也不能支撑这两个百分比。
- **建议**：补充实测条件与数据来源；如果没有稳定复现数据，应去掉定量数字，只保留方向性结论。

## [Task9 Deep Review] 12.1 APK 体积优化 — 2026-04-22
- **类型**：原理边界
- **位置**：L46
- **问题**：开头把 native libraries 一律写成“被解压到磁盘”，与后文 direct loading / `useLegacyPackaging=false` 的说明不一致，会把现代 Android 6.0+ 的 direct load 路径抹平。
- **建议**：在开头补出 direct loading 的例外条件，明确“解压到磁盘”只适用于 legacy packaging 或旧系统路径。

## [Task9 Deep Review] 12.1 APK 体积优化 — 2026-04-22
- **类型**：数据缺失
- **位置**：L291
- **问题**：`15%-40%` 的 AAB 下载体积收益区间没有给出官方来源、样本结构或设备分布边界。
- **建议**：补充官方出处 / 实测样本前提，或改成不带百分比的定性表述。

## [Task9 Deep Review] 18.16 游戏引擎渲染链路 — 2026-04-22
- **类型**：数据支撑
- **位置**：L177-L194 / 最小 trace case
- **问题**：三组 Swappy 场景只有“期望表现”，没有真实 Trace 截图、轨道名组合或 SQL/指标锚点，读者难以用同一方法验证接入前后差异。
- **建议**：补一组 60Hz 或 120Hz 的实 trace 样例，至少给出 FrameTimeline、游戏 render 线程、SurfaceFlinger 的对应观察点。

## [Task9 Deep Review] 18.16 游戏引擎渲染链路 — 2026-04-22
- **类型**：知识盲区
- **位置**：L198-L204 / DrawCall 合批
- **问题**：章节直接写“在 Perfetto 中，如果 RenderThread 的 DrawCall 数量过多…”，但没有说明 per-drawcall slice 通常需要 AGI、额外 graphics tracing 或引擎自定义埋点，默认 system trace 不一定直接可见。
- **建议**：补出默认 Perfetto、AGI/graphics tracing、自定义埋点三种可见性边界，避免把观测前提写成默认能力。

## [External Review] 1.0 架构全景导读 — 2026-04-22
- **类型**：数据/案例支撑
- **位置**：阅读建议
- **问题**：建议过于笼统，缺乏量化或具体实战目标
- **建议**：补充具体的"性能勋章"目标，例如"读完 1.4 后应能通过 Perfetto 识别 Binder 优先级继承导致的启动卡顿"
- **来源**：Gemini 外部 review


## [External Review] 1.2 系统启动全流程 — 2026-04-22
- **类型**：知识盲区
- **位置**：内存管理
- **问题**：预加载类增至 18k+，未解释 16KB Page Size 如何支撑而不会导致 RSS 崩溃
- **建议**：补充 16KB Page Size 提升内存共享效率和对齐性能的逻辑
- **来源**：Gemini 外部 review


## [External Review] 1.3 进程模型 — 2026-04-22
- **类型**：原理完善
- **位置**：输入系统 SocketPair
- **问题**：量化逻辑忽略了 epoll 唤醒路径对上下文切换的节省
- **建议**：补充 SocketPair 配合 Looper/epoll 实现事件直达 UI 线程的特性
- **来源**：Gemini 外部 review

## [External Review] 1.3 进程模型 — 2026-04-22
- **类型**：实战建议
- **位置**：DeathRecipient Perfetto 观测
- **问题**：binderDied() 不会在 ftrace 中自动产生 slice
- **建议**：建议开发者在 DeathRecipient 回调中手动添加 Trace.beginSection
- **来源**：Gemini 外部 review


## [External Review] 1.4 Binder IPC — 2026-04-22
- **类型**：源码严谨性
- **位置**：mmap 描述
- **问题**：提到"默认约 1MB"但未说明 BINDER_VM_SIZE 实际减去了 2 个 Page Size 的 Guard Page
- **建议**：补充 ProcessState.cpp 中的具体公式定义
- **来源**：Gemini 外部 review


## [External Review] 1.5 线程模型 — 2026-04-22
- **类型**：知识盲区
- **位置**：ThreadLocal 章节
- **问题**：只讲 ThreadLocal 好处，未讲协程 Dispatcher 切换时数据丢失陷阱
- **建议**：补充 ThreadContextElement 知识点
- **来源**：Gemini 外部 review

## [External Review] 1.5 线程模型 — 2026-04-22
- **类型**：数据支撑
- **位置**：Perfetto 状态标识符
- **问题**：futex_wait_queue_me 是内核函数名，Perfetto 界面显示不同
- **建议**：优先使用 Perfetto 界面显示的文字状态
- **来源**：Gemini 外部 review


## [External Review] 1.6 版本演进 — 2026-04-22
- **类型**：知识盲区
- **位置**：Android 15 配额限制
- **问题**：提到 6 小时配额限制，未明确开发者如何感知
- **建议**：补充 Service.onTimeout(int, int) 回调机制
- **来源**：Gemini 外部 review

## [External Review] 1.6 版本演进 — 2026-04-22
- **类型**：源码准确性
- **位置**：ART 编译策略
- **问题**：提到 Profile-Guided 编译但缺乏源码级入口
- **建议**：补充 art/compiler/driver/compiler_driver.cc 或 art/dex2oat/dex2oat.cc 锚点
- **来源**：Gemini 外部 review


## [External Review] 1.7 ART 编译管线 — 2026-04-22
- **类型**：知识盲区
- **位置**：JIT Code Cache
- **问题**：未提及 Data 与 Code 1:1 分配比例
- **建议**：补充说明 64MB Max Size 中各占一半
- **来源**：Gemini 外部 review

## [External Review] 1.7 ART 编译管线 — 2026-04-22
- **类型**：实战建议
- **位置**：profman 验证
- **问题**：profman 实战说明较少
- **建议**：增加 profman --dump-only 快速核验 Profile 覆盖率的示例
- **来源**：Gemini 外部 review


## [External Review] 1.8 AMS — 2026-04-22
- **类型**：数据/案例支撑
- **位置**：Input ANR
- **问题**：notifyNoFocusedWindowAnr 出现时通常意味着 WMS 正在进行窗口焦点切换
- **建议**：补充实战细节：冷启动期间点击无响应的排查思路
- **来源**：Gemini 外部 review


## [External Review] 1.9 PMS — 2026-04-22
- **类型**：原理链完整性
- **位置**：PMS 启动优化
- **问题**：未提及 SystemServerInitThreadPool 和 ParallelPackageParser
- **建议**：补充 PMS 如何利用多核并行解析 Manifest 以优化开机时间
- **来源**：Gemini 外部 review


## [External Review] 1.10 ContentProvider — 2026-04-22
- **类型**：版本差异
- **位置**：ContentProvider 版本演进
- **问题**：遗漏 Android 15 的 16KB 页面支持和 SQLite 只读事务
- **建议**：补充 16KB 页面如何减少分页开销提升大数据量查询效率
- **来源**：Gemini 外部 review

## [External Review] 1.10 ContentProvider — 2026-04-22
- **类型**：知识盲区
- **位置**：Perfetto 表现
- **问题**：未提及 Android 16 AnrHelper + ProfilingManager 联动
- **建议**：补充 Android 16 下系统自动生成 ContentProvider 超时采样报告
- **来源**：Gemini 外部 review


## [External Review] 1.11 Zygote — 2026-04-22
- **类型**：原理完善
- **位置**：PostFork Trace
- **问题**：建议补充 USAP 路径下 specializeAppProcess 触发 PostFork 的完整特化逻辑
- **建议**：补充 UID/GID 切换和 SELinux 上下文设置在 PostFork Slice 中的占比
- **来源**：Gemini 外部 review


## [External Review] 1.12 AutoFDO — 2026-04-22
- **类型**：交叉引用
- **位置**：与 Baseline Profiles 的关系
- **问题**：提到了与 1.7 章节关联但未给出具体 Perfetto 观测点
- **建议**：补充 AutoFDO 收益体现在 syscall 耗时缩减和 Binder Transaction 处理周期下降
- **来源**：Gemini 外部 review


## [External Review] 1.13 MessageQueue/DeliQueue — 2026-04-22
- **类型**：知识盲区
- **位置**：Perfetto 具体 Trace 事件
- **问题**：提到 monitor contention 但未具体说明对应的 Java 对象
- **建议**：明确指出 Android 17 前主线程常出现的 monitor_contention 对应 android.os.MessageQueue
- **来源**：Gemini 外部 review


## [External Review] 1.14 锁竞争 — 2026-04-22
- **类型**：原理链完整性
- **位置**：优先级反转
- **问题**：对 Binder 优先级继承的实现描述较笼统
- **建议**：补充 binder_select_thread_ilocked 与 binder_transaction_priority 的协作逻辑
- **来源**：Gemini 外部 review

## [External Review] 1.14 锁竞争 — 2026-04-22
- **类型**：数据/案例支撑
- **位置**：版本演进
- **问题**：DeliQueue 性能提升数据仅给出总体结论
- **建议**：引用 Google 官方测试中高并发插入下 5000 倍提升的量化数据
- **来源**：Gemini 外部 review


## [External Review] 1.15 JNI/NDK — 2026-04-22
- **类型**：原理链完整性
- **位置**：@CriticalNative 为什么快
- **问题**：缺少底层解释
- **建议**：补充不检查 GC 挂起请求、直接生成汇编级 BL/CALL 指令、无 Trampoline 的说明
- **来源**：Gemini 外部 review


## [External Review] 1.16 Audio Pipeline — 2026-04-22
- **类型**：实战建议
- **位置**：后台音频强化
- **问题**：未提及 adb 强报错模式
- **建议**：补充 adb shell cmd audio set-enable-hardening throw 用于调试
- **来源**：Gemini 外部 review


## [External Review] 1.17 IPC 全景 — 2026-04-22
- **类型**：数据/案例支撑
- **位置**：§6.1 Binder 追踪
- **问题**：Perfetto SQL 依赖 android.binder 数据源，非 userdebug/eng 或未配置 ftrace 环境下可能无法跑通
- **建议**：补充 trace 捕获时必须开启 android.binder ftrace 分类的说明
- **来源**：Gemini 外部 review

## [External Review] 1.17 IPC 全景 — 2026-04-22
- **类型**：知识盲区
- **位置**：§3.6 Signal
- **问题**：提到 BIONIC_SIGNAL_DEBUGGER 但未明确信号编号
- **建议**：补充 DEBUGGER_SIGNAL 通常是 35 (__SIGRTMIN + 3)，便于 shell 下 kill -35 <pid> 手动触发堆栈导出
- **来源**：Gemini 外部 review


## [External Review] 2.1 渲染架构全景 — 2026-04-22
- **类型**：知识盲区
- **位置**：BufferQueue
- **问题**：对 BlastBufferQueue 描述略显陈旧
- **建议**：补充 Android 16 中 BlastBufferQueue 与 ASurfaceControl 的深层整合
- **来源**：Gemini 外部 review

## [External Review] 2.1 渲染架构全景 — 2026-04-22
- **类型**：性能断言
- **位置**：硬件加速性能提升
- **问题**：5-10 倍描述缺乏基准测试环境说明
- **建议**：补充'在复杂 Path 和多层 Overdraw 场景下'的限定语
- **来源**：Gemini 外部 review


## [External Review] 2.2 帧率与刷新率 — 2026-04-22
- **类型**：知识盲区
- **位置**：Game Mode / Frame Rate 策略
- **问题**：未提及 Android 15 开发者选项的 Disable default frame rate for games 开关
- **建议**：补充 persist.graphics.game_default_frame_rate.enabled 属性控制的说明
- **来源**：Gemini 外部 review

## [Task9 Deep Review] 2.4 Choreographer 与渲染流水线 — 2026-04-22
- **类型**：数据缺失
- **位置**：高级分析方法 / 长帧 SQL 示例
- **问题**：示例查询把长帧阈值写死为 `dur > 16666700`，只适用于 60Hz。正文前面已经讨论 90Hz / 120Hz 帧预算，读者如果直接复用 SQL，容易漏掉高刷新率设备上的长帧。
- **建议**：把这段 SQL 明确标成“60Hz 示例”，或补成可参数化的 frame budget 查询。

## [Task9 Deep Review] 2.10 GPU 渲染深入 — 2026-04-22
- **类型**：数据缺失
- **位置**：ANGLE 层的性能影响
- **问题**：`2-5% / 5-10% / 10-20%` 的开销区间没有给出设备、GPU、驱动版本、工作负载和测试方法，正文只写“Google I/O + 社区数据”，读者无法复核。
- **建议**：补至少一组可复现实验条件，或改成 `[待验证]` / 经验值描述并说明适用边界。

## [Task6 Review] 15.5 线上性能监控 — 2026-04-22
- **类型**：需合并（非阻塞）
- **位置**：「监控数据的采样、聚合与报警策略」和「采样、聚合与报警策略」两个 ## 小节
- **问题**：两个小节覆盖相同的采样/聚合/报警三个维度，前者是详细版（~600字，含代码示例和分层策略），后者是精简版（~300字，bullet points），约 60% 内容重叠。违反 writing-guide.md "同一内容不在两处各写一遍"原则。
- **建议**：合并为一个小节，保留详细版的分析深度，在末尾加一个精简 checklist；或者拆成"策略原理"和"实战 checklist"两个互补但不重叠的部分。
- **review 日志**：logs/review/2026-04-22-23-review.md


## [2026-04-23] External Review 建议批量整合

### [External Review] 2.5 — 版本差异覆盖

- 问题**：[版本差异覆盖][ANGLE Mandatory Status]
- **来源**：External AI Review

### [External Review] 2.5 — 原理链完整性

- 问题**：[原理链完整性][Triple Buffering 复用]
- **来源**：External AI Review

### [External Review] 2.0 — 交叉引用一致性

- **问题**：- [P2][交叉引用一致性][## 阅读建议]
- **来源**：External AI Review

### [External Review] 2.11 — 版本差异

- **问题**：### 1. [P2][版本差异][Android 14 兼容性]
- **来源**：External AI Review

### [External Review] 2.12 — 知识盲区

- **问题**：### 1. [P2][知识盲区][2.12 扩展] 缺少 Android 17 反射禁令警告
- **来源**：External AI Review

### [External Review] 2.13 — 知识盲区

- **问题**：### [P2][知识盲区][配置细节] `setMaxDequeuedBufferCount(2)` 的灵活度
- **来源**：External AI Review

### [External Review] 2.14 — 工具

- **问题**：- [P2][工具][§ 7.2 AGI 与不同 API 的兼容性]
- **来源**：External AI Review

### [External Review] 2.15 — 知识盲区

- 问题**：[知识盲区][16KB 页面模式章节]
- **来源**：External AI Review

### [External Review] 2.16 — 维度

- **问题**：- [P2][维度][在 Perfetto 里怎么读 Fence]
- **来源**：External AI Review

### [External Review] 2.17 — 原理链

- **问题**：### 1. [P2][原理链][calculateSwapInterval 的 Hysteresis]
- **来源**：External AI Review

### [External Review] 2.18 — 知识盲区

- **问题**：- [P2][知识盲区][版本演进]
- **来源**：External AI Review

### [External Review] 2.18 — 源码准确性

- **问题**：- [P2][源码准确性][Surface.setFrameRate()]
- **来源**：External AI Review

### [External Review] 2.19 — P2

- **来源**：External AI Review

### [External Review] 2.20 — 数据/案例支撑

- **问题**：- [P2][数据/案例支撑][SurfaceFlinger 压力部分]
- **来源**：External AI Review

### [External Review] 2.20 — 知识盲区

- **问题**：- [P2][知识盲区][Perfetto 观察面]
- **来源**：External AI Review

### [External Review] 2.21 — 数据支撑

- **问题**：- [P2][数据支撑][Minikin 与文字测量性能]
- **来源**：External AI Review

### [External Review] 2.7 — 知识盲区

- **问题**：- [P2][知识盲区][Compose graphicsLayer]
- **来源**：External AI Review

### [External Review] 2.9 — 原理链完整性

- **问题**：- [P2][原理链完整性][Project Butter]
- **来源**：External AI Review

### [External Review] 3.2 — 数据/案例支撑

- 问题**：[数据/案例支撑][延迟全景图]
- **来源**：External AI Review

### [External Review] 3.3 — 知识盲区

- **问题**：- [P2][知识盲区][Exclusion Limit]
- **来源**：External AI Review

### [External Review] 3.3 — 源码准确性

- **问题**：- [P2][源码准确性][Gesture Blocking Activity]
- **来源**：External AI Review

### [External Review] 3.4 — 知识盲区

- 问题**：[知识盲区][Predictive Back]
- **来源**：External AI Review

### [External Review] 3.5 — 源码准确性

- **问题**：- [P2][源码准确性][KeyEventDispatcher 超时]
- **来源**：External AI Review

### [External Review] 3.6 — 原理链完整性

- **问题**：- [P2][原理链完整性][onSingleTapConfirmed 的触发时机]
- **来源**：External AI Review

### [External Review] 3.6 — 源码准确性

- **问题**：- [P2][源码准确性][TouchSlop 单位歧义]
- **来源**：External AI Review

### [External Review] 3.0 — P2

- **来源**：External AI Review



## [2026-04-23] External Review 建议批量整合

### [External Review] 4.1 — 原理链完整性

- 问题**：[原理链完整性][LMKD]
- **来源**：External AI Review

### [External Review] 4.2 — 数据支撑

- 问题**：[数据支撑][16K Page Size]
- **来源**：External AI Review

### [External Review] 4.2 — 源码准确性

- 问题**：[源码准确性][DMA-BUF Heaps]
- **来源**：External AI Review

### [External Review] 4.3 — 版本差异

- 问题**：[版本差异][§8.2]
- **来源**：External AI Review


## [Task9 Deep Review] 8.8 Android 多媒体管线性能 — 2026-04-23
- **类型**：数据缺失
- **位置**：L213-L215 / ABR 小节
- **问题**：`更主动的预测模型`、`亚 100ms adaptation decision` 没有给出可回查的官方 release note、实验条件或 trace 基线，当前 `[已验证]` 标注不足以支撑这个量化结论。
- **建议**：如果没有一手 benchmark 或官方变更说明，改成不带定量承诺的表述；若保留，补具体版本、测试网络条件和直接来源链接。

## [Task9 Deep Review] 12.2 网络性能优化 — 2026-04-23
- **类型**：交叉引用
- **位置**：L101 / 已验证标注
- **问题**：`developer.android.com/reference/okhttp3/EventListener` 不是有效的官方文档路径；OkHttp EventListener 的官方文档在 Square 站点。
- **建议**：把验证来源改为 `square.github.io/okhttp/features/events/` 或对应 API reference，避免把不存在的 Android Developers 路径写成已验证来源。

## [Task9 Deep Review] 12.2 网络性能优化 — 2026-04-23
- **类型**：数据缺失
- **位置**：L133 / HTTP/3 实际性能数据
- **问题**：YouTube `15%`、Uber `10-30%`、Meta `6% / 20%` 这些数字没有测试场景、终端范围、网络条件和直接链接，读者无法判断它们能否迁移到 Android 客户端业务。
- **建议**：补直接出处与实验边界；至少说明是移动端还是服务端、尾延迟口径、弱网条件和样本规模，否则改成不带百分比的趋势性描述。

## [Task9 Deep Review] 18.14 Camera 渲染管线 — 2026-04-23
- **类型**：原理链完整性
- **位置**：L137-L140 / sequenceDiagram Recording 分支
- **问题**：图里写成 `FW ->> MC: queueBuffer(Video)`，会把录像路径误读成直接调用 `MediaCodec.queueInputBuffer()`；实际 input surface 方案隔着 `Surface` / ANativeWindow / BufferQueue 边界，编码器只是 consumer。
- **建议**：把录像分支改成 `Camera3OutputStream -> encoder input Surface/ANativeWindow -> MediaCodec`，并显式标出这是 surface-input 零拷贝路径，不是 ByteBuffer 输入模式。


## [Task9 Deep Review] 15.3 性能指标体系 — 2026-04-23
- **类型**：数据支撑
- **位置**：TTFD / system-triggered profiling（约 186-190 行）
- **问题**：当前把 Android 16 的 system-triggered profiling 结论标成“已验证”，但挂靠的 `developer.android.com/topic/performance/launch-time` 只覆盖 TTID/TTFD 与 `reportFullyDrawn()`，并不支撑 ProfilingManager 触发机制本身。
- **建议**：补一条 Android 16 ProfilingManager / system-triggered profiling 的官方来源，再把启动指标与 profiling 触发机制分开标注，避免证据链错位。

## [Task9 Deep Review] 18.2 Android View 标准链路（BLAST 深入） — 2026-04-23
- **类型**：原理准确性
- **位置**：一帧的完整旅程 / Draw（记录）（约 51 行）
- **问题**：把 `DisplayList` 直接写成“也称为 `RenderNode`”，会把命令列表和承载它的节点对象混成一个概念。
- **建议**：改成“RenderNode 持有/封装 DisplayList”，后文 `syncFrameState` 同步 RenderNode 树时也更容易和对象边界对齐。

## [Task9 Deep Review] 18.2 Android View 标准链路（BLAST 深入） — 2026-04-23
- **类型**：交叉引用
- **位置**：文末交叉引用（约 248-250 行）
- **问题**：`[2.1 BufferQueue 机制](13-buffer-queue.md)`、`[2.5 SurfaceFlinger](06-surfaceflinger.md)`、`[2.6 同步机制](16-sync-fence.md)` 在当前目录下都是失效链接。
- **建议**：改成指向 `../../part1-fundamentals/ch02-rendering/` 下的真实文件，保证章节内跳转和出版链路一致。

---

## [External Review] 4.0 4.0 内存章节导读 — 2026-04-23
- **类型**：阅读建议
- **位置**：阅读建议段落
- **问题**：未提及 Native 内存安全
- **建议**：增加对 MTE 和 16KB 适配的推荐链接
- **来源**：Gemini 外部 review (4.0)

---

## [External Review] 4.5 4.5 App 内存优化 — 2026-04-23
- **类型**：数据支撑
- **位置**：120Hz 掉帧计算
- **问题**：描述精彩但可更量化
- **建议**：给出公式示例: Vsync(8.33ms) < UI Work(4ms) + GC Pause(5ms) = Frame Drop
- **来源**：Gemini 外部 review (4.5)

---

## [External Review] 4.5 4.5 App 内存优化 — 2026-04-23
- **类型**：源码准确性
- **位置**：Bitmap.java 路径
- **问题**：路径对应旧分支
- **建议**：标注此路径对应 AOSP 现代版本 android-15.0.0_r1+
- **来源**：Gemini 外部 review (4.5)

---

## [External Review] 4.7 4.7 16KB Page Size — 2026-04-23
- **类型**：内容优化
- **位置**：构建工具链要求
- **问题**：AGP 8.5 描述冗长
- **建议**：直接强调 AGP 8.5.1+ 是修复 bundletool 16KB 对齐 Bug 的关键版本
- **来源**：Gemini 外部 review (4.7)

---

## [External Review] 4.8 4.8 ART 分代 GC — 2026-04-23
- **类型**：Perfetto 优化
- **位置**：SQL 示例
- **问题**：使用 process_name 较慢
- **建议**：推荐使用 upid 替代 process_name 以利用索引
- **来源**：Gemini 外部 review (4.8)

---

## [External Review] 5.0 5.0 CPU 与功耗章节导读 — 2026-04-23
- **类型**：阅读建议
- **位置**：阅读建议
- **问题**：未区分内核开发与应用优化
- **建议**：App 开发者关注 5.8/5.9/5.10，系统工程师关注 5.1-5.5
- **来源**：Gemini 外部 review (5.0)

---

## [External Review] 5.1 5.1 Linux 进程调度基础 — 2026-04-23
- **类型**：Perfetto SQL
- **位置**：EEVDF 排队
- **问题**：缺少前瞻性 SQL
- **建议**：增加识别 EEVDF Lag 限制导致排队的示例 SQL
- **来源**：Gemini 外部 review (5.1)

---

## [External Review] 5.2 5.2 EAS 能量感知调度 — 2026-04-23
- **类型**：源码更新
- **位置**：能量模型函数名
- **问题**：em_pd_energy 为旧名
- **建议**：补充 v5.10+ 更名为 em_cpu_energy
- **来源**：Gemini 外部 review (5.2)

---

## [External Review] 5.2 5.2 EAS 能量感知调度 — 2026-04-23
- **类型**：版本差异
- **位置**：Cgroup V2 状态
- **问题**：CPU 控制器状态未说明
- **建议**：补充 Android 12 CPU 控制器仍保留在 Cgroup V1
- **来源**：Gemini 外部 review (5.2)

---

## [External Review] 5.3 5.3 大小核架构 — 2026-04-23
- **类型**：数学描述
- **位置**：PELT 32ms
- **问题**：32ms = 1024us × 32 不严谨
- **建议**：修正为半衰期约 32ms，负载每 1024us 更新一次
- **来源**：Gemini 外部 review (5.3)

---

## [External Review] 5.3 5.3 大小核架构 — 2026-04-23
- **类型**：公式优化
- **位置**：schedutil 公式
- **问题**：过于理想化
- **建议**：体现 1.25 SCHED_CAPACITY_SCALE 裕量概念
- **来源**：Gemini 外部 review (5.3)

---

## [External Review] 5.4 5.4 DVFS 动态调频 — 2026-04-23
- **类型**：延迟构成
- **位置**：升频延迟
- **问题**：200ms 延迟未拆解
- **建议**：区分硬件物理切换(us 级)与 PELT 衰减惯性(32-64ms)
- **来源**：Gemini 外部 review (5.4)

---

## [External Review] 5.8 5.8 后台执行限制 — 2026-04-23
- **类型**：数据支撑
- **位置**：App Standby
- **问题**：Active 桶限额背景缺失
- **建议**：补充 Android 16 Active 桶引入限额背景
- **来源**：Gemini 外部 review (5.8)

---

## [External Review] 5.8 5.8 后台执行限制 — 2026-04-23
- **类型**：交叉引用
- **位置**：后台执行对前台性能
- **问题**：未引用 LMK
- **建议**：显式引用 4.4 节关于 LMK 的描述
- **来源**：Gemini 外部 review (5.8)

---

## [External Review] 5.9 5.9 ADPF 自适应性能框架 — 2026-04-23
- **类型**：版本差异
- **位置**：Thermal API
- **问题**：仅描述 NDK 监听器
- **建议**：补充 Android 16 Java 层预测回调 forecastHeadroom
- **来源**：Gemini 外部 review (5.9)

---

## [External Review] 5.9 5.9 ADPF 自适应性能框架 — 2026-04-23
- **类型**：版本差异
- **位置**：版本演进表
- **问题**：Android 17 为[待验证]
- **建议**：填充 ADPF 扩展至非游戏场景内容
- **来源**：Gemini 外部 review (5.9)

---

## [External Review] 5.10 5.10 JobScheduler/WorkManager 性能 — 2026-04-23
- **类型**：源码准确性
- **位置**：JobScheduler 内部架构
- **问题**：assignJobToContext 应为 assignJobsToContextsLocked
- **建议**：修正方法名
- **来源**：Gemini 外部 review (5.10)

---

## [External Review] 5.10 5.10 JobScheduler/WorkManager 性能 — 2026-04-23
- **类型**：边界说明
- **位置**：WorkManager 持久化
- **问题**：未提强制停止后的行为
- **建议**：补充 Force Stop 后 WorkManager 也不执行
- **来源**：Gemini 外部 review (5.10)

---

## [External Review] 5.11 5.11 端侧 AI 推理性能 — 2026-04-23
- **类型**：版本差异
- **位置**：GPU Delegate
- **问题**：未提 Android 15 优化
- **建议**：标注 LiteRT GPU Delegate 在 Android 15 通过 OpenCL 优化实现 1.4x 提速
- **来源**：Gemini 外部 review (5.11)

---

## [External Review] 5.12 5.12 热管理深度分析 — 2026-04-23
- **类型**：最佳实践
- **位置**：getThermalHeadroom
- **问题**：调用频率无建议
- **建议**：建议每秒调用不超过 1 次，避免 Binder 开销
- **来源**：Gemini 外部 review (5.12)

---

## [External Review] 6.0 6.0 存储章节导读 — 2026-04-23
- **类型**：引导优化
- **位置**：阅读建议
- **问题**：弱化了 6.1 硬件基线重要性
- **建议**：平衡 6.1 与 6.2/6.3 阅读推荐权重
- **来源**：Gemini 外部 review (6.0)

---

## [External Review] 6.1 6.1 存储架构 — 2026-04-23
- **类型**：边界说明
- **位置**：FUSE Passthrough
- **问题**：未强调元数据操作无效
- **建议**：补充 open/create/readdir 仍由 MediaProvider 处理
- **来源**：Gemini 外部 review (6.1)

---

## [External Review] 6.2 6.2 文件系统 — 2026-04-23
- **类型**：源码补强
- **位置**：SQLite 原子写
- **问题**：只提 START ioctl
- **建议**：补充 COMMIT 和 ABORT ioctl 完整闭环
- **来源**：Gemini 外部 review (6.2)

---

## [External Review] 6.4 6.4 存储版本演进 — 2026-04-23
- **类型**：版本门槛
- **位置**：FUSE Passthrough
- **问题**：未标注内核门槛
- **建议**：补充需要 Kernel 5.4+ 且 CONFIG_FUSE_PASSTHROUGH=y
- **来源**：Gemini 外部 review (6.4)

---

## [External Review] 6.5 6.5 SP/DataStore 优化 — 2026-04-23
- **类型**：实战建议
- **位置**：sLoadExecutor
- **问题**：级联效应警示不足
- **建议**：明确多 SP 文件全局串行化风险
- **来源**：Gemini 外部 review (6.5)

---

## [External Review] 6.5 6.5 SP/DataStore 优化 — 2026-04-23
- **类型**：版本差异
- **位置**：MMKV vs DataStore
- **问题**：未提 16KB 适配差异
- **建议**：MMKV mmap 在 16KB 页设备需 native 适配
- **来源**：Gemini 外部 review (6.5)

---

## [External Review] 7.2 7.2 卡顿原因体系 — 2026-04-23
- **类型**：背景说明
- **位置**：华为 VSync 异常
- **问题**：描述为错误注入
- **建议**：补充 OEM 功耗平衡 Smart Refresh Rate 策略背景
- **来源**：Gemini 外部 review (7.2)

---

## [External Review] 7.3 7.3 卡顿分析方法论 — 2026-04-23
- **类型**：实战价值
- **位置**：doFrame 回调
- **问题**：未说明 CALLBACK_INSETS_ANIMATION
- **建议**：补充 IME 弹出分析价值
- **来源**：Gemini 外部 review (7.3)

---

## [External Review] 7.3 7.3 卡顿分析方法论 — 2026-04-23
- **类型**：SQL 精度
- **位置**：抢占分析
- **问题**：未区分 R+ 和 R
- **建议**：区分 Preempted (R+) 和 Runnable (R)
- **来源**：Gemini 外部 review (7.3)

---

## [External Review] 7.4 7.4 典型场景卡顿根因 — 2026-04-23
- **类型**：源码准确性
- **位置**：TaskSnapshot
- **问题**：未提及 HardwareBuffer
- **建议**：明确 Android 8.0+ 使用 GraphicBuffer FD 零拷贝传递
- **来源**：Gemini 外部 review (7.4)

---

## [External Review] 7.6 7.6 案例实战分析 — 2026-04-23
- **类型**：数学解释
- **位置**：嵌套布局
- **问题**：层级嵌套导致多次 measure 未量化
- **建议**：补充指数级增长（乘法关系）说明
- **来源**：Gemini 外部 review (7.6)

---

## [External Review] 7.6 7.6 案例实战分析 — 2026-04-23
- **类型**：Binder 差异
- **位置**：onBindViewHolder
- **问题**：未区分冷/热调用
- **建议**：补充首次系统服务调用的权限校验开销
- **来源**：Gemini 外部 review (7.6)

---

## [External Review] 7.7 7.7 Compose 性能优化 — 2026-04-23
- **类型**：版本更新
- **位置**：ReuseComposeView
- **问题**：标注为待验证
- **建议**：Compose 1.8.0 稳定版已正式发布，直接更新
- **来源**：Gemini 外部 review (7.7)

---

## [External Review] 7.7 7.7 Compose 性能优化 — 2026-04-23
- **类型**：实现细节
- **位置**：ScopeUpdateScope
- **问题**：未说明实际实现类
- **建议**：明确实际实现类是 RecomposeScopeImpl
- **来源**：Gemini 外部 review (7.7)

---

## [External Review] 7.8 7.8 RecyclerView 深度优化 — 2026-04-23
- **类型**：实战建议
- **位置**：hasTransientState
- **问题**：未提及对回收影响
- **建议**：补充非框架属性动画导致 hasTransientState=true 阻断回收
- **来源**：Gemini 外部 review (7.8)

---

## [External Review] 7.8 7.8 RecyclerView 深度优化 — 2026-04-23
- **类型**：可视化
- **位置**：VSync 精度
- **问题**：缺少像素偏移示例
- **建议**：补充 120Hz 1ms 误差在 2000px/s 下对应 2 像素偏移
- **来源**：Gemini 外部 review (7.8)

---

## [Task9 Deep Review] 14.4 dumpsys 系列命令 — 2026-04-23
- **类型**：版本差异 / 观察路径
- **位置**：`dumpsys SurfaceFlinger：Layer 信息与合成状态`
- **问题**：正文提醒了 Android 15 FrontEnd 变化，但没有给出 `dumpsys SurfaceFlinger --frontend` 这个新的文本入口，也没有把它和 Winscope 的使用边界分开。
- **建议**：补一段最小排查路径：Android 15+ 先看 `--frontend` 或 Winscope，再决定是否继续用 `--latency` 做逐层采样。

---

## [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-04-23
- **类型**：知识盲区 / 交叉引用
- **位置**：`PowerMonitor API` 与最佳实践
- **问题**：本章已经讲到“怎么测”，但没有把 Android 15 的 ADPF power-efficiency mode 与 §5.9 串起来，读者拿到功耗数据后看不到官方的“怎么控”入口。
- **建议**：补一个交叉引用到 §5.9，说明 `PowerMonitor` 负责观测，ADPF / `PerformanceHintManager.Session` 负责在支持设备上做能效取舍。

---

## [Task9 Deep Review] 14.12 APM / 可观测性平台与 SDK 选型 — 2026-04-23
- **类型**：实现原理 / 案例支撑
- **位置**：第二层：客户端增强层
- **问题**：Matrix、KOOM、btrace 只写到了产品定位，没有交代最能体现技术差异的实现切口，例如 KOOM 的 fork-dump、btrace 的插桩式采样。
- **建议**：每个工具补 1 句实现抓手，至少让读者知道它们为什么能拿到那类现场。


## [Task9 Deep Review] 1.15 JNI/NDK 性能优化 — 2026-04-23
- **类型**：数据支撑
- **位置**：L133-L135
- **问题**：正文写“近两年的旗舰机实测通常已经明显低于这组数值”，但没有给出设备、SoC、ART 版本、编译状态或测试来源。
- **建议**：补充可复核 benchmark 条件；如果拿不到一手数据，就保留官方 angler-userdebug 数字并删除现代设备量级判断。

## [Task9 Deep Review] 1.16 Audio Pipeline 延迟与性能 — 2026-04-23
- **类型**：版本差异
- **位置**：L362 / L368-L370
- **问题**：正文把已在 android-16.0.0_r1 AAudio.h 中公开的 offloaded playback 能力，与仍未核实的 offloaded PCM / 设备支持范围混写在一起。
- **建议**：拆成“已验证的 Android 16 API 边界”和“仍需设备/格式验证的实现边界”两层，避免把官方 API 与未证实实现状态混成一条。


---

## [Task9 Deep Review] 6.2 文件系统 — 2026-04-23
- **类型**：数据支撑
- **位置**：L186 / L267-L276 / L471
- **问题**：正文给出了“batch atomic write 约 3 倍提速”“UFS 4.0 4KB 随机写应低于 0.1ms”“使用一年后会到 1-5ms”等量化结论，但没有设备型号、存储介质、文件系统挂载参数、测试工具或样本范围，读者无法判断这些数字是 Pixel / UFS / 特定 workload 结果，还是通用基线。
- **建议**：给每组数字补最小实验条件；如果拿不到稳定样本，就把这些数字降级为定性表述，只保留可复核的 trace 观察方法。

---

## [Task9 Deep Review] 6.2 文件系统 — 2026-04-23
- **类型**：工具观察路径
- **位置**：L382
- **问题**：dm-verity 可观测性段落写成“通过 `disk Greenland` 或 `mmc` trace”观察，但 `disk Greenland` 不是当前 Perfetto / ftrace 的有效观察名称，会把读者带到不存在的轨道或脚本关键字上。
- **建议**：改成具体可操作的观察路径：例如 block layer / mmc / dm tracepoint 与对应 Perfetto 数据源配置，并明确 dm-verity 没有独立 slice，只能从底层 I/O 延迟侧面观察。
