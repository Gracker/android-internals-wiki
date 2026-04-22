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
