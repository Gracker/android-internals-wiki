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
- **建议**：明确 `reportFullyDrawn()` 作为 TTFD 的官方触发点。
**external. 二、总体结论**
- **章节**：7.3
**external. 二、总体结论**
- **类型**：建议补充
**external. 二、总体结论**
- **位置**：JankStats 构造器
**external. 二、总体结论**
- **描述**：构造器接受 `WindowMetrics` 参数，但建议提供便捷工厂方法。
**external. 二、总体结论**
- **建议**：增加 `JankStats.createForWindow(context)` 静态方法封装。
**external. 二、总体结论**
- **章节**：14.8
**external. 二、总体结论**
- **类型**：建议改进
**external. 二、总体结论**
- **位置**：关键指标测量章节
**external. 二、总体结论**
- **描述**：建议增加 CPU 使用率与 UI 线程阻塞的关联分析。
**external. 二、总体结论**
- **建议**：补充 `proc` 文件系统读取 CPU 频率与进程状态的示例代码。

---

## [Task6 Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-04-23
- **类型**：需补充数据/需验证
- **位置**：性能提升数据描述
- **问题**：4%掉帧减少缺乏具体测试环境和基线说明；MessageQueue字段变更在AOSP android-17-beta3中描述不够精确
- **建议**：需补充具体的设备配置、测试条件和性能对比基线；需要在实际代码中验证字段变更的具体影响
- **review 日志**：logs/review/2026-04-23-16-review.md

## [Task6 Review] 2.0 渲染系统总纲 — 2026-04-23
- **类型**：需补充内容
- **位置**：章节依赖关系
- **问题**：各章节之间的具体依赖关系不够明确，缺乏典型性能问题排查路径
- **建议**：添加章节依赖关系图和典型性能问题排查路径流程图
- **review 日志**：logs/review/2026-04-23-16-review.md

## [Task6 Review] 2.21 文字渲染性能 — 2026-04-23
- **类型**：需补充数据/需补充优化指导
- **位置**：性能对比数据、优化步骤、版本演进
- **问题**：StaticLayout vs BoringLayout缺乏具体耗时对比数据；缺少PrecomputedText的具体使用示例和适用条件；缺少Android各版本文字渲染的性能变化趋势
- **建议**：补充具体的性能测试数据和使用示例；补充Android 12-17文字渲染性能的演进对比和最佳实践
- **review 日志**：logs/review/2026-04-23-16-review.md
## [External Review] 8.7 Baseline Profiles 与编译优化实践 — 2026-04-23
- **类型**：源码准确性
- **位置**：验证是否生效：先看编译状态，再看启动收益
- **问题**：文中推荐手动触发编译的命令为 `adb shell cmd package compile -r bg-dexopt com.example.app`。
- **建议**：建议在文中同时补充 `-m speed-profile` 的显式强制编译命令，这在日常线下验证时行为更明确。
- **来源**：外部 AI review


## [External Review] 8.7 Baseline Profiles 与编译优化实践 — 2026-04-23
- **类型**：源码准确性
- **位置**：扩展 - Profileable 应用与性能分析
- **问题**：“`<profileable>` 元素本身是 API 29 加入的，`android:shell` 属性是 API 30 新增的。”
- **建议**：修正此处的 API 版本边界细节。
- **来源**：外部 AI review


## [External Review] 8.7 Baseline Profiles 与编译优化实践 — 2026-04-23
- **类型**：实操建议
- **位置**：`验证是否生效：先看编译状态，再看启动收益`
- **问题**：手工触发编译的 ADB 命令可以提供更直接的替代方案。
- **建议**：补充 `adb shell cmd package compile -m speed-profile -f <package>`。
- **来源**：外部 AI review


## [External Review] 7.11 WebView 渲染性能与优化 — 2026-04-23
- **类型**：知识盲区
- **位置**：内存管理 - 内存泄漏的常见原因
- **问题**：仅提到了从父容器移除以及调用 `destroy()`。
- **建议**：建议补充在 `destroy()` 之前，调用 `webView.setWebChromeClient(null)`、`webView.setWebViewClient(null)`、`webView.removeJavascriptInterface("xxx")` 以及 `webView.clearHistory()` 等清理操作，以彻底切断内部组件的引用链。
- **来源**：外部 AI review


## [External Review] 7.11 WebView 渲染性能与优化 — 2026-04-23
- **类型**：最佳实践缺失
- **位置**：`内存管理 - 内存泄漏的常见原因`
- **问题**：销毁 WebView 的代码示例不够完整。
- **建议**：补充清理 `WebChromeClient`、`WebViewClient` 等组件的步骤。
- **来源**：外部 AI review


## [External Review] 7.12 View 体系性能优化 — 2026-04-23
- **类型**：数据/案例支撑
- **位置**：量化关系：层级深度与帧耗时
- **问题**：给出了具体的 measure 耗时数据：“一个 3 层、20 个 View 的简单布局：measure 大约 0.5-1ms... 12 层、200 个 View 的复杂布局：measure 可能超过 15ms”，并标有 `[待验证]`。
- **建议**：建议将这段改成定性的描述，或者明确引用特定设备/特定芯片上的 benchmark 跑分前提。最好引用 Perfetto 中实际观察到的 Traverse pass 相对占比，而非绝对的 ms 数。
- **来源**：外部 AI review


## [External Review] 7.12 View 体系性能优化 — 2026-04-23
- **类型**：量化数据无支撑
- **位置**：`量化关系：层级深度与帧耗时`
- **问题**：提供了具体的层级和毫秒级耗时对照，缺乏可复现前提。
- **建议**：改为定性结论（如“呈非线性增长”），或补充实测机型、系统版本等前置条件。
- **来源**：外部 AI review


## [External Review] 7.13 SystemUI 性能分析 — 2026-04-23
- **类型**：知识盲区
- **位置**：Perfetto 里先看哪些 Track
- **问题**：虽然指出了看 `InputMonitorCompat("edge-swipe")` 和 `Transitions` 等关键组件，但由于 SystemUI 跨进程分析极其复杂，初学者在海量 Track 中手动找这些 slice 依然困难。
- **建议**：建议在“常见卡顿形态与排查办法”中，适当补充 1-2 条 Perfetto SQL 查询示例（如根据 `name = 'edge-swipe'` 过滤 slice），或说明如何通过预设的 UI 模板快速 Pin 住 Launcher3 和 WM Shell 的主线程，这将极大提升实操性。
- **来源**：外部 AI review


## [External Review] 7.13 SystemUI 性能分析 — 2026-04-23
- **类型**：实操建议
- **位置**：`Perfetto 里先看哪些 Track`
- **问题**：缺少快速定位跨进程长链路的 SQL 辅助手段。
- **建议**：补充关于如何用 Perfetto SQL 或 Trace Processor 提取 `Transitions` 或 `edge-swipe` slice 的小贴士。
- **来源**：外部 AI review


## [External Review] 7.14 GAPS：Android 动态分析目标可达性路径重建 — 2026-04-23
- **类型**：原理链完整性
- **位置**：放到性能分析工作流里时，边界要先写清楚
- **问题**：指出了 GAPS 可以用于“把 trace 抓取点前置到目标方法附近”，但没有给出具体的工程接合思路。
- **建议**：建议补充一句话说明实操思路：例如通过 GAPS 的 Python 驱动脚本（基于 AndroidViewClient），在即将执行到关键 Target Action 之前，插入一句 `os.system("adb shell perfetto -c ... --background")` 来自动拉起 Perfetto 抓取，实现真正的“目标引导式性能 Trace 抓取”。
- **来源**：外部 AI review


## [External Review] 7.14 GAPS：Android 动态分析目标可达性路径重建 — 2026-04-23
- **类型**：实操结合
- **位置**：`放到性能分析工作流里时，边界要先写清楚`
- **问题**：学术工具与 Perfetto 联动的实操感可以更强一点。
- **建议**：补充在 Python 脚本中结合 `adb shell perfetto` 的自动化抓取示例思路。
- **来源**：外部 AI review


## [External Review] 7.15 场景化性能作战手册 — 2026-04-23
- **类型**：知识盲区
- **位置**：八类最常见的性能现场
- **问题**：给出了极好的排查思路（如“先看 FrameTimeline”、“看是否有 Binder reply wait”），但未给出在 Perfetto UI 中对应的具体 Track 名称或 Slice 名称。
- **建议**：建议在每一类排查步骤中，括号补充最关键的 1-2 个 Perfetto 关键字。例如在列表滑动卡顿补充 `(搜索 slice: Choreographer#doFrame 或 rv.onBindViewHolder)`；在输入延迟补充 `(关注 InputDispatcher 和 deliverInputEvent)`；在 ANR 补充 `(关注 monitor contention 或 binder transaction)`。这会让“作战手册”的落地感更强。
- **来源**：外部 AI review


## [External Review] 7.15 场景化性能作战手册 — 2026-04-23
- **类型**：实操建议
- **位置**：`八类最常见的性能现场`
- **问题**：排查路线稍显理论化，缺少工具层面的直接抓手。
- **建议**：在排查步骤中以括号形式标注关键的 Trace Event 名称或命令，提升手册的“傻瓜化”执行度。
- **来源**：外部 AI review


## [External Review] 10.1 App 内存分析 — 2026-04-23
- **类型**：文字排版 / 概念严谨性
- **位置**：dumpsys meminfo 全景地图 和 常见问题与误区
- **问题**：存在异常换行（如 MEMINFO 中 com.example

.app）；32位与64位系统对 Native OOM 表现的差异未明确
- **建议**：修复 Markdown 换行；补充 64 位环境下 Native 内存耗尽多导致 LMK 的结论
- **来源**：Gemini 外部 review
## [External Review] 10.5 案例集 — 2026-04-23
- **类型**：交叉引用一致性
- **位置**：案例一：低内存引发整机卡顿与冷启动退化 - 修复方案与效果
- **问题**：利用 onTrimMemory 的 TRIM_MEMORY_RUNNING_MODERATE 级别释放，但 §10.3 已指出 Android 14+ 不再投递这些级别
- **建议**：补充说明 Android 14+ 系统中这些级别不再投递，建议读者参考 §10.3 的新版适配方案
- **来源**：Gemini 外部 review

## [Task9 Deep Review] 2.10 GPU 渲染深入 — 2026-04-24
- **类型**：源码准确性
- **位置**：L233-L239「CPU 开销：一个数量级的差距」示例代码
- **问题**：把 `glDrawArrays()` 与 `vkQueueSubmit()` 并排比较会把 draw call 和整批命令提交混成一层概念。
- **建议**：改成 `glDrawArrays()` ↔ `vkCmdDraw()` 的指令级对照，再把 `vkQueueSubmit()` 放到“命令缓冲区提交”层单独解释。

## [Task9 Deep Review] 2.10 GPU 渲染深入 — 2026-04-24
- **类型**：数据缺失
- **位置**：L506-L510「效果验证」
- **问题**：案例中的 GPU 时间、FPS 与 overdraw 改善区间缺少设备型号、刷新率、采集方式和 Trace / AGI 证据。
- **建议**：补设备 / 分辨率 / 刷新率 / 录制方式 + 1 张 Perfetto 或 AGI 截图，给效果数字一个最小证据包。

## [Task9 Deep Review] 2.10 GPU 渲染深入 — 2026-04-24
- **类型**：数据缺失
- **位置**：L267-L271「ANGLE 层的性能影响」
- **问题**：ANGLE 的 2-5% / 5-10% / 10-20% 只是经验区间，正文还缺 workload 与设备边界。
- **建议**：补“这些区间来自哪类 workload / 设备 / 演讲场景”，或者进一步收敛成“量级参考，不直接套用”。

## [Task9 Deep Review] 2.21 文字渲染性能 — 2026-04-24
- **类型**：版本差异
- **位置**：L351-L362「版本演进」
- **问题**：版本表还缺 Android 12 的 FontManager / updatable fonts（`com.android.fonts`）节点，系统字体与 emoji 的更新链路仍不完整。
- **建议**：补 Android 12 一行，说明 updatable font pipeline 影响的是系统字体 / emoji 版本覆盖边界，而不是 TextView API 语义。

## [Task9 Deep Review] 2.21 文字渲染性能 — 2026-04-24
- **类型**：知识盲区
- **位置**：L223-L314「文字渲染优化实践」
- **问题**：优化节还没有覆盖 variable font / font variation settings 对 relayout 与测量缓存 key 的影响。
- **建议**：补一小段 variable font 边界：字体轴变化会触发重新测量，列表 / 动画场景不要把字体轴当成零成本样式切换。

## [Task9 Deep Review] 2.21 文字渲染性能 — 2026-04-24
- **类型**：数据缺失
- **位置**：L322-L349「在 Perfetto 中识别文字渲染瓶颈」
- **问题**：Perfetto 观察面已经说清了默认 trace 与 atrace 类别边界，但还缺一条最小可复用的实测样例。
- **建议**：补设备 / 刷新率 / 文本长度 / Span 数量 / `TextView.onMeasure()` 观测区间，增强实操可信度。


## [Task9 Deep Review] 18.17 Hardware Buffer Renderer — 2026-04-24
- **类型**：数据与案例支撑
- **位置**：L182-L197 / L287-L304
- **问题**：正文已经把定量结论回退成定性判断，但仍缺同设备、同尺寸、同格式 workload 的 benchmark 和最小 Perfetto 对照，读者还拿不到可复核的基线。
- **建议**：补 1 组 `lockCanvas()` vs `HardwareBufferRenderer` 的同机型 A/B 数据，并给出至少一条 `draw()`→RenderThread/GPU→`setBuffer()`→SF `latch` 的 trace 对照。

## [Task9 Deep Review] 18.18 PIP 与自由窗口渲染 — 2026-04-24
- **类型**：数据与案例支撑
- **位置**：L91 / L149
- **问题**：PiP 进入和 Freeform resize 两处仍停在“待补 Trace 截图”占位，缺少能直接复核的时间线样例。
- **建议**：各补 1 组最小 Perfetto 样例，至少同屏标出 WindowManager/Shell transition、`QueuedBuffer - ...BLAST#...`、`latchBuffer` 和 actual present。

## [Task9 Deep Review] 18.18 PIP 与自由窗口渲染 — 2026-04-24
- **类型**：交叉引用一致性
- **位置**：frontmatter related_chapters / 正文对 §2.13 的引用
- **问题**：正文主要依赖 §18.5、§18.10、§2.13，但 `related_chapters` 仍写 `2.6/2.12/18.10`；同时 §2.13 L222/L269 还保留“BLAST=Android 12+”旧口径，书内 BLAST 版本边界尚未完全对齐。
- **建议**：补齐 `related_chapters`，并同步清理 §2.13 中残留的“Android 12+ 才有 BLAST”表述。

## [Task9 Deep Review] 2.9 渲染机制的版本演进 — 2026-04-24
- **类型**：数据缺失
- **位置**：L167「SkiaVulkan 后端改进」
- **问题**：“CPU 开销降低约 30–50%”仍是裸数字，只标了 `[待验证]`，没有 workload、机型、驱动版本或对照基线。
- **建议**：补 benchmark 来源与测试条件；如果暂时拿不到一手数据，回退成定性表述。


## [Task9 Deep Review] 8.3 启动优化策略 — 2026-04-24
- **类型**：数据缺失
- **位置**：L637-L669「Baseline Profile 效果量化」
- **问题**：“提升 20%-40%”“2 秒降到 1.2-1.6 秒”缺少 workload、设备、编译模式与测试轮次，当前只有裸数字，难以作为可复现结论。
- **建议**：补充 Macrobenchmark 测试条件（机型、系统版本、CompilationMode、迭代次数、冷/热启动口径）后再保留量化结论。


## [Task9 Deep Review] 18.11 ANGLE（GLES-over-Vulkan 翻译层） — 2026-04-24
- **类型**：数据缺失
- **位置**：性能特征
- **问题**：当前对“更容易受益 / 更容易吃亏”只给了 workload 画像，没有同机 native vs ANGLE 的 A/B 数据、shader 冷启动/热启动分段，读者无法判断这些判断在什么设备和场景下成立。
- **建议**：补一组同机对照样本：同时记录 `glGetString(GL_RENDERER)`、首帧 / 场景切换的 shader 编译耗时、FrameTimeline 或 GPU counter，对比 native 与 ANGLE 两条路径，再把收益边界写回正文。

## [Task9 Deep Review] 18.21 EyeDropper API 与跨设备协作性能 — 2026-04-24
- **类型**：数据缺失
- **位置**：性能和可观测性
- **问题**：章节给了应用侧 Trace 打点方案，但没有 API 37 设备上的 launch→result 时延样本，也没有 FrameTimeline/主线程回放样例，读者拿到 trace 后缺少判断基线。
- **建议**：补一段真实 trace 观察：记录 `eye_dropper_launch` 到 `eye_dropper_result` 的时延范围，并附一张返回结果后 UI 刷新的 FrameTimeline/主线程窗口，说明哪些开销来自系统 picker，哪些来自应用回放。


## [Task6 Review] 19.05 LeakCanary — 2026-04-24
- **类型**：L3-内容深度
- **位置**：leak trace读法段
- **问题**：trace示例中 `this$0` 未解释，许多开发者不了解匿名内部类对外部类的隐式引用
- **建议**：补充一句解释 `this$0` 是匿名内部类对外部类的隐式引用
- **review 日志**：logs/review/2026-04-24-1319-review.md

## [Task6 Review] 19.05 LeakCanary — 2026-04-24
- **类型**：L3-内容深度
- **位置**：测试集成建议段
- **问题**：仅1段文字，缺少具体instrumentation test代码示例和CI门禁配置
- **建议**：补充LeakCanary instrumented test的典型代码片段和CI leak gate配置
- **review 日志**：logs/review/2026-04-24-1319-review.md

## [Task6 Review] 19.06 BlockCanary — 2026-04-24
- **类型**：L3-内容深度
- **位置**：误判处理（抓栈线程段）
- **问题**：GC、Binder等待、I/O等因素如何导致误判只一笔带过
- **建议**：补充1-2个具体误判场景（如GC期间抓到无意义堆栈）及识别方法
- **review 日志**：logs/review/2026-04-24-1319-review.md

## [Task6 Review] 19.06 BlockCanary — 2026-04-24
- **类型**：L3-内容深度
- **位置**：典型报告聚合段
- **问题**：缺少具体的报告样例
- **建议**：补充一个归一化后的block报告JSON示例
- **review 日志**：logs/review/2026-04-24-1319-review.md

## [Task6 Review] 19.07 DoraemonKit / DoKit — 2026-04-24
- **类型**：L3-内容深度
- **位置**：Release隔离清单段
- **问题**：列出检查项但缺反面案例
- **建议**：补充调试工具泄漏到线上的实际风险案例或行业案例
- **review 日志**：logs/review/2026-04-24-1319-review.md

## [Task6 Review] 19.07 DoraemonKit / DoKit — 2026-04-24
- **类型**：L3-内容深度
- **位置**：团队协作锚点
- **问题**：只覆盖开发和测试，缺少性能专项人员使用场景
- **建议**：补充性能工程师如何结合DoKit做专项测试的工作流
- **review 日志**：logs/review/2026-04-24-1319-review.md

## [Task6 Review] 19.08 ArgusAPM — 2026-04-24
- **类型**：L3-内容深度
- **位置**：AOP织入适合哪些数据段
- **问题**：只列了适合/不适合场景，缺代码示例
- **建议**：补充AOP织入前后的代码对比示例（如Activity生命周期耗时采集）
- **review 日志**：logs/review/2026-04-24-1319-review.md

## [Task6 Review] 19.08 ArgusAPM — 2026-04-24
- **类型**：L3-内容深度
- **位置**：网络监控的现代适配段
- **问题**：只给方向，缺具体拦截器示例
- **建议**：补充网络阶段拆分的OkHttp Interceptor代码片段
- **review 日志**：logs/review/2026-04-24-1319-review.md

## [Task9 Deep Review] 19.01 APM 全景图与分类体系 — 2026-04-24
- **类型**：原理链完整性
- **位置**：L98-L107, L159-L176
- **问题**：正文先定义“指标/现场/归因”三层，后面又改成“指标/样本/trace 三种证据”，context/schema 合同没有独立落位，trace id / session id / field contract 关系不够稳定。
- **建议**：把数据模型显式拆成 metrics / sample / trace / context 四类，并给每类至少 3 个字段例子和一个误用场景。

## [Task9 Deep Review] 19.03 KOOM — 2026-04-24
- **类型**：版本差异覆盖
- **位置**：L220
- **问题**：ApplicationExitInfo 被当成通用退出信号，但它只在 API 30+ 可用，低内存杀进程的准确上报还依赖设备支持。
- **建议**：补上 API 30+ 与 isLowMemoryKillReportSupported() 的边界，并说明 Android 8-10 仍需依赖 LMK/Vitals/logcat。

## [Task9 Deep Review] 19.03 KOOM — 2026-04-24
- **类型**：知识盲区
- **位置**：L121-L128
- **问题**：接入建议没有交代 native 模块的 c++_shared / c++_static 双模式和 STL 打包冲突，落地时容易踩编译或运行时符号冲突。
- **建议**：在使用建议里补一段 native module 接入边界，明确多个 KOOM 模块不能混用 shared/static 模式。

## [Task9 Deep Review] 19.04 btrace / RheaTrace — 2026-04-24
- **类型**：原理链完整性
- **位置**：L82-L88
- **问题**：命令示例写成 `-r sched`，正文只解释了重启采集，没有解释 `sched` 这个调度 category 的作用。
- **建议**：把 `-r` 和 `sched` 分开解释，或者补一条 `--list` 查 category 的说明，避免读者把 `sched` 误读成 `-r` 的参数。


## [Task6 Review] 19.09 Measure — 2026-04-24
- **类型**：需补充素材
- **位置**：全文，🔹[隐私策略] 锚点缺失
- **问题**：outline 定义了隐私策略锚点（覆盖 URL pattern、用户标识、日志、请求体、截图/附件、地区合规和删除请求），但正文中完全缺失该节内容。Measure 作为开源自托管平台，隐私策略是选型评估的关键维度。
- **建议**：参考 Measure 官方文档 Privacy/GDPR 部分，补充隐私策略章节。覆盖字段脱敏规则、URL pattern 过滤、用户数据删除请求处理、地区合规差异。
- **review 日志**：logs/review/2026-04-24-14-review.md


## [Task9 Deep Review] 10.6 内存抖动与频繁 GC — 2026-04-24
- **类型**：数据缺失
- **位置**：L220-L229（Memory Profiler / GC Events）
- **问题**：正文把“GC Events 每秒超过 2-3 次”写成异常阈值，但没有给设备、负载、采样窗口或 trace 样本。这个数字缺少基线，容易被读者当成固定阈值。
- **建议**：补 1 组实际 trace / profiler 样本，说明设备刷新率、页面负载、对象分配速率，再把阈值表述改成“场景化经验值”。

## [Task9 Deep Review] 18.10 SurfaceControl API 深入 — 2026-04-24
- **类型**：交叉引用
- **位置**：L609-L611（附录交叉引用）
- **问题**：`13-buffer-queue.md`、`06-surfaceflinger.md`、`16-sync-fence.md` 这 3 个相对链接在 ch18 目录下不存在，当前跳转会断开。
- **建议**：改成指向 ch02 对应章节的正确相对路径，或统一改成稳定的章节号/WikiLink。

## [Task9 Deep Review] 18.10 SurfaceControl API 深入 — 2026-04-24
- **类型**：数据缺失
- **位置**：L252-L266（Layer 数量与性能）
- **问题**：正文已经给出“Layer 增多会抬高 SurfaceFlinger 工作量、可能导致 HWC 回退”的判断，但没有放任何一组真实 `dumpsys SurfaceFlinger` / Perfetto 证据样例。
- **建议**：补 1 组设备级样例，至少包含 layer 数量、CompositionType 变化，以及 `setTransactionState` / `latchBuffer` 的对照观察点。

## [Task9 Deep Review] 18.13 WebView 渲染管线 — 2026-04-24
- **类型**：交叉引用
- **位置**：与其他章节的关系 / frontmatter `related_chapters`
- **问题**：正文大段使用 SurfaceControl 子 Surface 机制，但没有直接关联 18.10，frontmatter 的 `related_chapters` 也缺失该章节。
- **建议**：补上 18.10 的正文交叉引用和 frontmatter 关联，避免 WebView 专章与 SurfaceControl 专章割裂。

## [Task9 Deep Review] 19.16 ProfilingManager — 2026-04-24
- **类型**：工具关系
- **位置**：## 和 Perfetto、APM SDK 的关系
- **问题**：只写了 Perfetto 和抽象 APM SDK，没有把 JankStats、FrameMetrics、Android Studio Profiler 放进排查漏斗。
- **建议**：补一条“JankStats/FrameMetrics 发现异常 → ProfilingManager 取样 → Perfetto / Android Studio Profiler 复盘”的工具顺序。

## [Task9 Deep Review] 19.17 Firebase Performance — 2026-04-24
- **类型**：示例覆盖
- **位置**：## 自定义 trace 示例
- **问题**：只有 home_first_feed 一个例子，没有把大纲要求的登录、图片解码、数据库查询的命名模式和低基数字段约束展开。
- **建议**：补一个 trace naming 表，列出 trace 名、metric 名、attribute 名和禁止高基数字段示例。

## [Task9 Deep Review] 19.18 商业 APM 平台（Sentry、APMPlus、Bugly） — 2026-04-24
- **类型**：数据合同
- **位置**：## 私有化和退出成本 / AppMonitor facade 代码块
- **问题**：Facade 只有接口，没有标准字段合同；如果 page/user/version/experiment/request-stage/tag 仍由 vendor 自己命名，迁移时还是会被锁死。
- **建议**：在 facade 旁补内部 schema 约束，先统一字段词典，再映射到 Sentry/APMPlus/Bugly。

## [Task6 Review] 15.15 Baseline Profiles 与编译优化 — 2026-04-24
- **类型**：需技术核实
- **位置**：Android 17版本兼容性
- **问题**：文档覆盖Android 8-37版本，但未核实新版本中AOT编译机制是否仍然适用
- **建议**：核实Android 17中AOT编译行为变化，确认Profile生成工具兼容性
- **review日志**：logs/review/2026-04-24-17-review.md

## [Task6 Review] 15.15 Baseline Profiles 与编译优化 — 2026-04-24
- **类型**：需技术核实
- **位置**：R8规则影响
- **问题**：未确认新版本R8是否影响Profile规则有效性和命中率
- **建议**：核实R8版本变化对Profile影响，添加版本适配建议
- **review日志**：logs/review/2026-04-24-17-review.md

## [Task6 Review] 15.15 Baseline Profiles 与编译优化 — 2026-04-24
- **类型**：需补充验证案例
- **位置**：验证章节
- **问题**：缺少实际Profile生成失败的案例分析和规避建议
- **建议**：增加Profile生成失败的典型场景和排查指南
- **review日志**：logs/review/2026-04-24-17-review.md

## [Task6 Review] 19.17 Firebase Performance — 2026-04-24
- **类型**：需技术核实
- **位置**：Android 17 API变化
- **问题**：未确认Firebase Performance SDK在Android 17中的API变化
- **建议**：核实最新版本Firebase SDK的API变化和兼容性
- **review日志**：logs/review/2026-04-24-17-review.md

## [Task6 Review] 19.17 Firebase Performance — 2026-04-24
- **类型**：需补充验证
- **位置**：网络监控章节
- **问题**：未验证网络监控在不同Android版本中的采集能力差异
- **建议**：补充网络监控的版本兼容性矩阵和限制说明
- **review日志**：logs/review/2026-04-24-17-review.md

## [Task6 Review] 19.17 Firebase Performance — 2026-04-24
- **类型**：需补充内容
- **位置**：指标差异章节
- **问题**：未明确Firebase与Android Vitals的指标定义和计算方法差异
- **建议**：补充指标对比表和口径统一建议
- **review日志**：logs/review/2026-04-24-17-review.md

## [Task6 Review] 19.18 商业 APM 平台 — 2026-04-24
- **类型**：需重写
- **位置**：平台选型章节
- **问题**：选型维度过于简化，缺少深入工程考量标准
- **建议**：重构选型维度，增加成本模型、ROI分析、长期维护成本评估
- **review日志**：logs/review/2026-04-24-17-review.md

## [Task6 Review] 19.18 商业 APM 平台 — 2026-04-24
- **类型**：需补充素材
- **位置**：成本模型章节
- **问题**：缺少具体的成本计算模型和ROI分析
- **建议**：补充具体的成本计算表、TCO分析和ROI建议
- **review日志**：logs/review/2026-04-24-17-review.md

## [Task6 Review] 19.18 商业 APM 平台 — 2026-04-24
- **类型**：需补充案例
- **位置**：迁移章节
- **问题**：缺少实际迁移失败案例和教训总结
- **建议**：增加2-3个实际迁移案例，分析失败原因和规避建议
- **review日志**：logs/review/2026-04-24-17-review.md

## [Task9 Deep Review] 19.11 JankStats — 2026-04-24
- **类型**：源码准确性
- **位置**：L73-L107（输出数据与回调示例）
- **问题**：AndroidX JankStats 源码明确说明 `OnFrameListener` 收到的 `FrameData` 是复用对象，监听器返回后该对象会在后续帧被覆盖。正文只提醒“不要做同步 I/O”，但没有提醒需要在回调里复制 `frameDurationUiNanos`、`states` 等字段；如果后续做异步聚合或批量上报，读者容易拿到被覆写的数据。
- **建议**：在接入示例或“使用建议”里补一句“回调参数是 `volatileFrameData`，需要在返回前复制要保留的字段”，最好给一个轻量 DTO 聚合示例。

## [Task9 Deep Review] 19.12 FrameMetrics — 2026-04-24
- **类型**：源码准确性
- **位置**：L92-L116、L194-L205
- **问题**：正文已经强调 HandlerThread，但没补官方回调契约：`Window.OnFrameMetricsAvailableListener` 回调过慢会丢报告，传入的 `FrameMetrics` 对象会在每次回调复用，超出回调作用域后就无效。
- **建议**：在接入代码后补一句“只提取 primitive 值或用 `FrameMetrics(FrameMetrics)` 复制”，并说明 `dropCountSinceLastInvocation` 可用于观察回调侧丢报告。

## [Task9 Deep Review] 19.19 PerfDog — 2026-04-24
- **类型**：知识盲区
- **位置**：L67-L83（工具定位与能力说明）
- **问题**：官方文档区分 Android 免安装模式与安装模式：安装模式会自动安装 PerfDog.apk 并支持端上实时显示，免安装模式则没有端上显示。正文只写“非嵌入式、通常不需要 root”，没有交代两种模式对悬浮窗权限、现场可视化和测量环境的影响。
- **建议**：补一张“免安装模式 / 安装模式”对照表，写清 USB 调试、PerfDog.apk、悬浮窗权限、是否在手机端显示实时指标，以及各自适用的回归/竞品测试场景。

## [Task9 Deep Review] 19.19 PerfDog — 2026-04-24
- **类型**：数据缺失
- **位置**：L75-L160（指标解释与报告字段）
- **问题**：正文列了 FPS、frame time、jank、功耗、温度，但没有补 PerfDog 官方对 FTime / Jank / Stutter / Smooth Index 等指标的定义，也没有说明不同设备或模式下指标可用性会不同。读者容易把不同模式、不同设备采到的值直接横比。
- **建议**：补一段指标口径说明，至少解释 FTime、Jank、Stutter、Smooth Index 的含义，并标注“同机、同模式、同条件比较优先”。

## [Task9 Deep Review] 19.20 SoloPi 与 Emmagee — 2026-04-24
- **类型**：数据缺失
- **位置**：L113-L122（启动耗时测试）
- **问题**：正文提醒了起点和终点口径，但没有给出冷启动、热启动、清数据、清进程与“页面可交互”之间的固定组合，测试团队仍然可能拿不同口径的 SoloPi 数值去和 Macrobenchmark 或线上启动指标直接比较。
- **建议**：补一张启动测试记录模板，把“冷/热启动、清数据、清进程、起点、终点、是否广播触发”固化成必填字段。

## [Task9 Deep Review] 19.21 Benchmark 应用（Geekbench、安兔兔、3DMark、PCMark、Vellamo） — 2026-04-24
- **类型**：数据缺失
- **位置**：frontmatter `sources`（L14-L18）与 L105-L111
- **问题**：章节正文对安兔兔、PCMark、Vellamo 都给了方法论判断，但 frontmatter 只挂了 Geekbench 和 3DMark 两个来源。尤其 PCMark 的 Work 3.0 / Storage 2.0 与旧版本不可比这一边界，正文没有落到工具来源。
- **建议**：补齐 PCMark、安兔兔、Vellamo 的一手来源或应用商店说明，并在 PCMark 段落明确写出 Work 3.0 / Storage 2.0 与旧版分数不可比。

## [Task9 Deep Review] 19.07 DoraemonKit / DoKit — 2026-04-24
- **类型**：数据缺失
- **位置**：L132-L146（性能面板的数据可信度）
- **问题**：正文提醒了 DoKit 只能做现场初筛，但没有把 FPS / CPU / 内存 / 启动 / 流量这些面板数据各自的采集入口、刷新频率和误差边界落成表格。读者仍可能把悬浮窗数值直接拿去做跨机型、跨构建比较。
- **建议**：补一张“指标 → 采集入口 → 刷新频率 → 易受哪些干扰 → 必须用什么工具复核”的对照表，把 JankStats / Perfetto / Profiler / Macrobenchmark 的复核边界写清。

## [Task9 Deep Review] 19.22 存储 Benchmark（AndroBench、A1 SD Bench） — 2026-04-24
- **类型**：数据缺失
- **位置**：L100-L110、L137-L162、L198-L218
- **问题**：正文强调要保留顺序/随机读写和 median/p95，但没有把 MB/s、IOPS、latency、SQLite QPS 这些口径拆开解释。读者很容易把顺序吞吐、4K 随机 IOPS 和 SQLite 事务吞吐直接横比，或者不知道报告里为什么既要写 median 又要写 p95。
- **建议**：补一张“指标 → 常见单位 → 典型工具口径 → 对应业务场景”的表，至少把顺序读写（MB/s）、随机读写（IOPS 或 4K 吞吐）、latency、SQLite QPS/txn/s 以及 median/p95 的使用边界写清。


## [Task9 Deep Review] 1.8 Activity Manager Service 与性能分析 — 2026-04-25
- **类型**：数据缺失
- **位置**：L226 / L385 / L522（冷启动、ANR、进程被杀的 Perfetto 小节）
- **问题**：三处仍是 Trace 截图占位，正文虽然已经给出 `am_proc_start`、`am_anr` 和关键线程的判断口径，但缺少一条真实 trace 或 SQL 输出把 `android_logs`、`system_server` 与应用主线程串起来。
- **建议**：补一段真实 Perfetto 截图或 SQL 结果，至少覆盖 `am_proc_start` / `am_proc_bound` 与首帧、`am_anr` 与 `dumpStackTraces` 的对应关系。

## [Task9 Deep Review] 1.9 Package Manager Service 与应用安装性能 — 2026-04-25
- **类型**：数据缺失
- **位置**：L224 / L480（安装过程与后台 dexopt 的 Perfetto 小节）
- **问题**：安装控制面、`artd`、`dex2oat` 的职责链已经补齐，但 Perfetto 部分仍停留在抓取命令和占位提示，缺少一条真实安装 trace 来对照 `PackageInstallerSession`、`artd`、`dex2oat` 的时序。
- **建议**：补一条包含 `system_server`、`artd`、`dex2oat` 的安装 trace，最好附 1 组 SQL 或线程名对照，验证“控制面 vs 执行面”的归因路径。

## [External Review] 19.01  — 2026-04-25
- **问题类型**：最佳实践缺失
- **位置**：系统 API 采集代价
- **问题描述**：未提及 `ApplicationExitInfo` 存在的 IPC 开销陷阱。
- **建议**：补充说明应在异步线程获取 `getHistoricalProcessExitReasons`。
- **来源**：外部 AI review

## [External Review] 19.03  — 2026-04-25
- **问题描述**：[原理链完整性][Hprof 裁剪和引用链摘要]
  - 原文问题：提到“Hprof 文件仍然很大，需要裁剪或只上传摘要”，但未说明裁剪了什么。
  - 证据或观察依据：在 Hprof 结构中，占据绝大多数空间的往往是 primitive arrays (如 `byte[]`，通常是图片像素数据或大文本)。
  - 问题描述：缺少对裁剪对象的说明，使内容停留在概念上。
  - 建议：补充说明 Hp
- **建议**：[原理链完整性][Hprof 裁剪和引用链摘要]
  - 原文问题：提到“Hprof 文件仍然很大，需要裁剪或只上传摘要”，但未说明裁剪了什么。
  - 证据或观察依据：在 Hprof 结构中，占据绝大多数空间的往往是 primitive arrays (如 `byte[]`，通常是图片像素数据或大文本)。
  - 问题描述：缺少对裁剪对象的说明，使内容停留在概念上。
  - 建议：补充说明 Hp
- **来源**：外部 AI review

## [External Review] 19.04  — 2026-04-25
- **问题描述**：[源码准确性][采集流程]
  - **原文问题**：App 包里集成 `com.bytedance.btrace:rhea-inhouse`，未提及具体版本号。
  - **证据或观察依据**：Btrace 3.0 与 2.x 的产物格式和能力有质的区别，3.0 默认输出 PB 格式以供 Perfetto 分析。
  - **问题描述**：不写具体版本号可能导致读者接入旧版本。
  - **建议
- **建议**：[源码准确性][采集流程]
  - **原文问题**：App 包里集成 `com.bytedance.btrace:rhea-inhouse`，未提及具体版本号。
  - **证据或观察依据**：Btrace 3.0 与 2.x 的产物格式和能力有质的区别，3.0 默认输出 PB 格式以供 Perfetto 分析。
  - **问题描述**：不写具体版本号可能导致读者接入旧版本。
  - **建议
- **来源**：外部 AI review

## [External Review] 19.04  — 2026-04-25
- **问题描述**：[数据/案例支撑][Perfetto UI 里的读法]
  - **原文问题**：提到“看 CPU 调度：线程是否频繁 runnable 但拿不到 CPU”。
  - **证据或观察依据**：Perfetto UI 中 Runnable 和 Running 的视觉表现不同。
  - **问题描述**：对初次接触 Perfetto 的读者来说，知道要看 Runnable 状态，但不知道在 UI 上长
- **建议**：[数据/案例支撑][Perfetto UI 里的读法]
  - **原文问题**：提到“看 CPU 调度：线程是否频繁 runnable 但拿不到 CPU”。
  - **证据或观察依据**：Perfetto UI 中 Runnable 和 Running 的视觉表现不同。
  - **问题描述**：对初次接触 Perfetto 的读者来说，知道要看 Runnable 状态，但不知道在 UI 上长
- **来源**：外部 AI review

## [External Review] 19.05  — 2026-04-25
- **问题描述**：[原理链完整性][它怎样判断对象被保留]
  - 原文问题：“默认阈值是应用可见时 5 个、应用不可见时 1 个。”
  - 问题描述：数值准确，但未提及如果在可见时（5个以下）切到后台，阈值立刻变为 1 并触发 dump。
  - 建议：补充退到后台（Home键）时立即触发 dump 的机制，更符合实战体验。
- **建议**：[原理链完整性][它怎样判断对象被保留]
  - 原文问题：“默认阈值是应用可见时 5 个、应用不可见时 1 个。”
  - 问题描述：数值准确，但未提及如果在可见时（5个以下）切到后台，阈值立刻变为 1 并触发 dump。
  - 建议：补充退到后台（Home键）时立即触发 dump 的机制，更符合实战体验。
- **来源**：外部 AI review

## [External Review] 19.06  — 2026-04-25
- **问题描述**：[数据/案例支撑][抓栈线程和主线程的关系]
  - **原文问题**：提到“另一个常见误判是 GC”，指出此时堆栈表现为一段平淡的等待状态。
  - **问题描述**：缺乏与 Perfetto 中表现的交叉印证，读者难以将文字堆栈和系统 Trace 联系起来。
  - **建议**：补充说明，遇到这类因 GC 导致的阻塞堆栈时，在 Perfetto 中通常对应主线程呈现 `Sleeping` 状
- **建议**：[数据/案例支撑][抓栈线程和主线程的关系]
  - **原文问题**：提到“另一个常见误判是 GC”，指出此时堆栈表现为一段平淡的等待状态。
  - **问题描述**：缺乏与 Perfetto 中表现的交叉印证，读者难以将文字堆栈和系统 Trace 联系起来。
  - **建议**：补充说明，遇到这类因 GC 导致的阻塞堆栈时，在 Perfetto 中通常对应主线程呈现 `Sleeping` 状
- **来源**：外部 AI review

## [External Review] 19.07  — 2026-04-25
- **问题描述**：[知识盲区][和 Android Studio Profiler、Perfetto 的关系]
- 原文问题：虽然说明了“DoKit 给的是入口，不是最终证据”，但没有明确点出它与线上成熟 APM 工具在技术实现流派上的最大区别。
- 问题描述：诸如 Matrix 等线上 APM 倾向于使用底层的 PLT Hook (例如 xhook) 或相对轻量的抽样机制；而 DoKit 作为 Debug 工具则
- **建议**：[知识盲区][和 Android Studio Profiler、Perfetto 的关系]
- 原文问题：虽然说明了“DoKit 给的是入口，不是最终证据”，但没有明确点出它与线上成熟 APM 工具在技术实现流派上的最大区别。
- 问题描述：诸如 Matrix 等线上 APM 倾向于使用底层的 PLT Hook (例如 xhook) 或相对轻量的抽样机制；而 DoKit 作为 Debug 工具则
- **来源**：外部 AI review

## [External Review] 19.08  — 2026-04-25
- **问题描述**：[细节严谨性][网络监控的现代适配]
- 原文问题：网络阶段拆分中提到了使用 `StageEventListener` 代替 `Interceptor`，但未考虑到旧版本 OkHttp 的限制。
- 证据或观察依据：OkHttp 在 `3.11.0` 才引入了相对完整成熟的 `EventListener` 机制。而上文（兼容风险章节）明确提到公开 sample 的基线停留在 `okhttp:3.1
- **建议**：[细节严谨性][网络监控的现代适配]
- 原文问题：网络阶段拆分中提到了使用 `StageEventListener` 代替 `Interceptor`，但未考虑到旧版本 OkHttp 的限制。
- 证据或观察依据：OkHttp 在 `3.11.0` 才引入了相对完整成熟的 `EventListener` 机制。而上文（兼容风险章节）明确提到公开 sample 的基线停留在 `okhttp:3.1
- **来源**：外部 AI review

## [External Review] 19.09  — 2026-04-25
- **问题描述**：[版本差异覆盖][核心能力]
  - 原文问题：“Crash / ANR 自动捕获”
  - 证据或观察依据：现代 APM 在 Android 端捕获 ANR 存在明显的版本分水岭：Android 11 之前通常依赖 `FileObserver` 监听 `/data/anr/traces.txt` 或者拦截 SIGQUIT 信号；而 Android 11+ 引入了官方的 `ApplicationE
- **建议**：[版本差异覆盖][核心能力]
  - 原文问题：“Crash / ANR 自动捕获”
  - 证据或观察依据：现代 APM 在 Android 端捕获 ANR 存在明显的版本分水岭：Android 11 之前通常依赖 `FileObserver` 监听 `/data/anr/traces.txt` 或者拦截 SIGQUIT 信号；而 Android 11+ 引入了官方的 `ApplicationE
- **来源**：外部 AI review

## [External Review] 19.09  — 2026-04-25
- **问题描述**：[数据/案例支撑][隐私策略要在接入前定清]
  - 原文问题：“截图 / 附件：默认开启文字或敏感输入遮罩”
  - 证据或观察依据：移动端的 Screenshot Mask 通常不是魔法，它一般需要通过遍历当前 Activity 的 View Hierarchy（视图树），找出特定的 inputType（如 password）或者开发者打上的特定 Tag，然后在最终的 Bitmap 截图中用实
- **建议**：[数据/案例支撑][隐私策略要在接入前定清]
  - 原文问题：“截图 / 附件：默认开启文字或敏感输入遮罩”
  - 证据或观察依据：移动端的 Screenshot Mask 通常不是魔法，它一般需要通过遍历当前 Activity 的 View Hierarchy（视图树），找出特定的 inputType（如 password）或者开发者打上的特定 Tag，然后在最终的 Bitmap 截图中用实
- **来源**：外部 AI review

## [External Review] 19.10  — 2026-04-25
- **问题描述**：[知识盲区][Collie 轻量线上采样思路]
  - 原文问题：启动采集依赖“`ContentProvider`、window focus 等关键节点”。
  - 问题描述：虽然借助 ContentProvider 采集启动耗时是经典方案，但在当前现代化 Android 开发中，开发者大概率在使用 `androidx.startup`。
  - 建议：建议顺带提及现今广泛使用的 Jetpack 
- **建议**：[知识盲区][Collie 轻量线上采样思路]
  - 原文问题：启动采集依赖“`ContentProvider`、window focus 等关键节点”。
  - 问题描述：虽然借助 ContentProvider 采集启动耗时是经典方案，但在当前现代化 Android 开发中，开发者大概率在使用 `androidx.startup`。
  - 建议：建议顺带提及现今广泛使用的 Jetpack 
- **来源**：外部 AI review

## [External Review] 19.10  — 2026-04-25
- **问题描述**：[原理链完整性][最小 APM SDK 采集方式]
  - 原文问题：慢帧信号来源列举了 `JankStats / Choreographer / FrameMetrics`，未作优先级区分。
  - 问题描述：读者对于选哪一个会有困惑。`FrameMetrics` 适用 API 24+，而 `JankStats` 是官方目前推荐的、支持到 API 16 并且能附带生命周期/UI 状态追踪的最佳封
- **建议**：[原理链完整性][最小 APM SDK 采集方式]
  - 原文问题：慢帧信号来源列举了 `JankStats / Choreographer / FrameMetrics`，未作优先级区分。
  - 问题描述：读者对于选哪一个会有困惑。`FrameMetrics` 适用 API 24+，而 `JankStats` 是官方目前推荐的、支持到 API 16 并且能附带生命周期/UI 状态追踪的最佳封
- **来源**：外部 AI review

## [External Review] 19.13  — 2026-04-25
- **问题描述**：[知识盲区][Native 标注]
- **原文问题**：Native Trace 描述过于笼统。
- **问题描述**：仅提到了 native 侧有自定义事件，未给出具体的 API 参考。
- **建议**：补充 `#include <android/trace.h>` 以及 `ATrace_beginSection` / `ATrace_endSection` 的名称，并明确说明 native
- **建议**：[知识盲区][Native 标注]
- **原文问题**：Native Trace 描述过于笼统。
- **问题描述**：仅提到了 native 侧有自定义事件，未给出具体的 API 参考。
- **建议**：补充 `#include <android/trace.h>` 以及 `ATrace_beginSection` / `ATrace_endSection` 的名称，并明确说明 native
- **来源**：外部 AI review

## [External Review] 19.13  — 2026-04-25
- **问题描述**：[原理链完整性][阅读方式]
- **原文问题**：缺失对 "Gap" 和 "Scheduler" 的观察方法。
- **问题描述**：大纲要求说明如何看 gap 和 scheduler。
- **建议**：在 Perfetto UI 描述部分，增加关于“两个同步 Slice 之间的 Gap 可能代表 I/O 等待或 CPU 调度抢占”的说明，并引导读者查看 Thread State 轨道。
- **建议**：[原理链完整性][阅读方式]
- **原文问题**：缺失对 "Gap" 和 "Scheduler" 的观察方法。
- **问题描述**：大纲要求说明如何看 gap 和 scheduler。
- **建议**：在 Perfetto UI 描述部分，增加关于“两个同步 Slice 之间的 Gap 可能代表 I/O 等待或 CPU 调度抢占”的说明，并引导读者查看 Thread State 轨道。
- **来源**：外部 AI review

## [External Review] 19.14  — 2026-04-25
- **问题描述**：[数据/案例支撑][CI 中的噪声控制]
  - 原文问题：“设备温度过高时跳过或降权本轮结果”描述得像是需要外部 CI 脚本自己处理。
  - 证据或观察依据：`androidx.benchmark` 内部包含了 `ThermalThrottle` 检测机制。
  - 问题描述：Benchmark 库在执行期间，默认会监控设备热节流状态。如果设备过热，库会自动介入休眠等待降温（Sleep to 
- **建议**：[数据/案例支撑][CI 中的噪声控制]
  - 原文问题：“设备温度过高时跳过或降权本轮结果”描述得像是需要外部 CI 脚本自己处理。
  - 证据或观察依据：`androidx.benchmark` 内部包含了 `ThermalThrottle` 检测机制。
  - 问题描述：Benchmark 库在执行期间，默认会监控设备热节流状态。如果设备过热，库会自动介入休眠等待降温（Sleep to 
- **来源**：外部 AI review

## [External Review] 19.16  — 2026-04-25
- **问题描述**：[原理链完整性][app-driven request 示例]
- **问题描述**：示例代码使用了 AndroidX 的 `SystemTraceRequestBuilder`，但未提及是否需要在 `AndroidManifest.xml` 中配置特殊的权限。
- **建议**：补充说明虽然 `ProfilingManager` 本身不需要存储权限（写入私有目录），但为了获取更全的系统追踪，建议
- **建议**：[原理链完整性][app-driven request 示例]
- **问题描述**：示例代码使用了 AndroidX 的 `SystemTraceRequestBuilder`，但未提及是否需要在 `AndroidManifest.xml` 中配置特殊的权限。
- **建议**：补充说明虽然 `ProfilingManager` 本身不需要存储权限（写入私有目录），但为了获取更全的系统追踪，建议
- **来源**：外部 AI review

## [External Review] 19.17  — 2026-04-25
- **问题描述**：[知识盲区][网络请求聚合和 URL pattern]
- **原文问题**：提及了 Cronet，但未说明其采集特殊性。
- **问题描述**：FPM 的 Gradle 插件无法自动对 Cronet 这种 native 网络栈进行字节码插桩。
- **建议**：明确指出使用 Cronet 时需要手动使用 `FirebasePerfUrlConnection` 包装或添加拦截器，否则会自动“漏掉”
- **建议**：[知识盲区][网络请求聚合和 URL pattern]
- **原文问题**：提及了 Cronet，但未说明其采集特殊性。
- **问题描述**：FPM 的 Gradle 插件无法自动对 Cronet 这种 native 网络栈进行字节码插桩。
- **建议**：明确指出使用 Cronet 时需要手动使用 `FirebasePerfUrlConnection` 包装或添加拦截器，否则会自动“漏掉”
- **来源**：外部 AI review

## [External Review] 19.17  — 2026-04-25
- **问题描述**：[数据/案例支撑][数据模型：trace、metric、attribute]
- **原文问题**：描述 Metric 时使用“低基数”。
- **问题描述**：Metric 是数值（Long），属性（Attribute）才是用来做分类聚合的（涉及基数问题）。
- **建议**：修改表述，强调 Metric 用于计算（累加、平均），Attribute 用于过滤和分组（高基数 Attribute 会
- **建议**：[数据/案例支撑][数据模型：trace、metric、attribute]
- **原文问题**：描述 Metric 时使用“低基数”。
- **问题描述**：Metric 是数值（Long），属性（Attribute）才是用来做分类聚合的（涉及基数问题）。
- **建议**：修改表述，强调 Metric 用于计算（累加、平均），Attribute 用于过滤和分组（高基数 Attribute 会
- **来源**：外部 AI review

## [External Review] 19.18  — 2026-04-25
- **问题描述**：[知识盲区][Sentry profiling 风险]
  - 原文问题：提到 profiling 存在特定场景 crash 风险，但未给出具体特征。
  - 证据或观察依据：Sentry 官方文档和 GitHub Issue。
  - 问题描述：缺少具体的信号特征（如 `pthread_getcpuclockid` 或 `art::Trace::StopTracing` 崩溃）。
  - 建议：
- **建议**：[知识盲区][Sentry profiling 风险]
  - 原文问题：提到 profiling 存在特定场景 crash 风险，但未给出具体特征。
  - 证据或观察依据：Sentry 官方文档和 GitHub Issue。
  - 问题描述：缺少具体的信号特征（如 `pthread_getcpuclockid` 或 `art::Trace::StopTracing` 崩溃）。
  - 建议：
- **来源**：外部 AI review

## [External Review] 19.18  — 2026-04-25
- **问题描述**：[原理链完整性][APMPlus 私有化]
  - 原文问题：提到私有化，但未说明其核心技术栈。
  - 问题描述：APMPlus 私有化核心依赖 ClickHouse (ByteHouse) 和 Flink。
  - 建议：在私有化部分简述其对高性能存储的要求，这对企业采购时的硬件成本评估非常重要。
- **建议**：[原理链完整性][APMPlus 私有化]
  - 原文问题：提到私有化，但未说明其核心技术栈。
  - 问题描述：APMPlus 私有化核心依赖 ClickHouse (ByteHouse) 和 Flink。
  - 建议：在私有化部分简述其对高性能存储的要求，这对企业采购时的硬件成本评估非常重要。
- **来源**：外部 AI review

## [External Review] 19.19  — 2026-04-25
- **问题描述**：[知识盲区][与自动化脚本结合]
- 原文问题：未提及 PerfDog Service APK 的角色。
- 问题描述：PerfDog 通过 PUSH 一个辅助 APK 到设备来作为“特权代理”，利用 shell 权限绕过部分沙箱限制。
- 建议：简要说明 PerfDog Service 的作用，以及为什么需要通过 ADB 手动授予 `DUMP` 权限。
- **建议**：[知识盲区][与自动化脚本结合]
- 原文问题：未提及 PerfDog Service APK 的角色。
- 问题描述：PerfDog 通过 PUSH 一个辅助 APK 到设备来作为“特权代理”，利用 shell 权限绕过部分沙箱限制。
- 建议：简要说明 PerfDog Service 的作用，以及为什么需要通过 ADB 手动授予 `DUMP` 权限。
- **来源**：外部 AI review

## [External Review] 19.19  — 2026-04-25
- **问题描述**：[原理链完整性][功耗和温度的读法]
- 原文问题：未提及 FPower（每帧功耗）这一高价值衍生指标。
- 建议：补充 FPower 的概念（Total Power / FPS），它是评估渲染能效比的核心指标。
- **建议**：[原理链完整性][功耗和温度的读法]
- 原文问题：未提及 FPower（每帧功耗）这一高价值衍生指标。
- 建议：补充 FPower 的概念（Total Power / FPS），它是评估渲染能效比的核心指标。
- **来源**：外部 AI review

## [External Review] 19.21  — 2026-04-25
- **问题描述**：[原理链完整性][Geekbench 分数的工程解释]
- **问题描述**：未提及 Geekbench 6 的 **“Shared Task” (共享任务)** 模型。
- **原理说明**：GB6 从 GB5 的独立多核任务改为多核协同完成单一任务（模拟真实软件逻辑），这解释了为什么现代高核数 SoC 的 GB6 多核分数增长不如 GB5 线性。
- **建议**：补充这一技术细节，帮助读者理
- **建议**：[原理链完整性][Geekbench 分数的工程解释]
- **问题描述**：未提及 Geekbench 6 的 **“Shared Task” (共享任务)** 模型。
- **原理说明**：GB6 从 GB5 的独立多核任务改为多核协同完成单一任务（模拟真实软件逻辑），这解释了为什么现代高核数 SoC 的 GB6 多核分数增长不如 GB5 线性。
- **建议**：补充这一技术细节，帮助读者理
- **来源**：外部 AI review

## [External Review] 19.21  — 2026-04-25
- **问题描述**：[知识盲区][3DMark 分数的工程解释]
- **问题描述**：仅提到 Wild Life 级别的测试，未提及现代光追（Solar Bay）和 AAA 级负载（Steel Nomad Light）。
- **建议**：补充针对 Android 14+ 旗舰机型应关注 **Solar Bay**（测光追性能）和 **Steel Nomad Light**（取代 Wild Life Extreme
- **建议**：[知识盲区][3DMark 分数的工程解释]
- **问题描述**：仅提到 Wild Life 级别的测试，未提及现代光追（Solar Bay）和 AAA 级负载（Steel Nomad Light）。
- **建议**：补充针对 Android 14+ 旗舰机型应关注 **Solar Bay**（测光追性能）和 **Steel Nomad Light**（取代 Wild Life Extreme
- **来源**：外部 AI review

## [External Review] 19.21  — 2026-04-25
- **问题描述**：[知识盲区][历史工具的处理]
- **问题描述**：提到 Vellamo 已过期，但未给出现代 Web 性能测试建议。
- **建议**：补充 **Speedometer 3.0** 或 **JetStream 2** 作为现代移动浏览器/Web 性能的基准工具。
- **建议**：[知识盲区][历史工具的处理]
- **问题描述**：提到 Vellamo 已过期，但未给出现代 Web 性能测试建议。
- **建议**：补充 **Speedometer 3.0** 或 **JetStream 2** 作为现代移动浏览器/Web 性能的基准工具。
- **来源**：外部 AI review

## [External Review] 19.25  — 2026-04-25
- **问题描述**：[工具支撑][大纲 - 耗电归因]
- 原文问题：未提及 `BatteryStats` 的底层采集原理。
- 证据或观察依据：AOSP `BatteryStatsService.java` 使用了大量的 `Timer` 和 `Counter`。
- 建议：补充对 `dumpsys batterystats --history` 的分析，解释系统如何通过“硬件状态机”转换（如 Wifi 扫描开启 -
- **建议**：[工具支撑][大纲 - 耗电归因]
- 原文问题：未提及 `BatteryStats` 的底层采集原理。
- 证据或观察依据：AOSP `BatteryStatsService.java` 使用了大量的 `Timer` 和 `Counter`。
- 建议：补充对 `dumpsys batterystats --history` 的分析，解释系统如何通过“硬件状态机”转换（如 Wifi 扫描开启 -
- **来源**：外部 AI review

## [External Review] 19.27  — 2026-04-25
- **问题描述**：[知识盲区][Mmap 存储位置]
- 证据或观察依据：Android 10+ 引入 Scoped Storage。
- 问题描述：大纲提到了 Scoped Storage，但未明确建议最佳的缓存路径。
- 建议：明确指出在 Scoped Storage 下，APM 的 mmap 缓存应优先放置在 `Context.getExternalFilesDir()` 或 `Context.getFile
- **建议**：[知识盲区][Mmap 存储位置]
- 证据或观察依据：Android 10+ 引入 Scoped Storage。
- 问题描述：大纲提到了 Scoped Storage，但未明确建议最佳的缓存路径。
- 建议：明确指出在 Scoped Storage 下，APM 的 mmap 缓存应优先放置在 `Context.getExternalFilesDir()` 或 `Context.getFile
- **来源**：外部 AI review

## [External Review] 19.README - 选择理由：总纲文件定义了全章的分类体系和工具链覆盖范围，如果分类逻辑或工具选型存在事实错误（如过时工具），将直接影响后续 22 个小节的编写价值。 — 2026-04-25
- **类型**: P2
- **位置**: 
- **问题**: - [P2][数据/案例支撑][19.15 Baseline Profiles]
- **原文问题**：仅列出“编译优化 + 启动加速”。
- **建议**：应明确说明 Baseline Profiles 对 ART Cloud Compilation (Android 16 特性) 的协同作用，这能提升首屏加载率。
- **建议**: 
- **来源**: 外部AI review (2026-04-25-00-ch19.README-external-review.md)


## [External Review] 15.1 - 选择理由：作为方法论章节的第一篇，其准确性和前瞻性（特别是对 Android 15/16 新特性的覆盖）直接影响全章的可信度。 — 2026-04-25
- **类型**: P2
- **位置**: 
- **问题**: 提到测量会影响系统，但缺乏量化支撑。
- **建议**: 补充一个具体的量化例子，例如：在 A55 大核上开启 Perfetto 调度追踪，可能导致主线程任务执行时间增加约 1ms。
- **来源**: 外部AI review (2026-04-25-10-15.1-external-review.md)

- **类型**: P2
- **位置**: 
- **问题**: 能力模型中未提及“成本意识”（FinOps）。
- **建议**: 在雷达图中加入“成本/ROI 评估力”，强调在大规模应用中性能优化即省钱。
- **来源**: 外部AI review (2026-04-25-10-15.1-external-review.md)


## [External Review] 15.2 - 选择理由：这是实战中最重要的判断决策点。能否准确区分系统瓶颈还是应用瓶颈，决定了后续排查工作的有效性。 — 2026-04-25
- **类型**: P2
- **位置**: 
- **问题**: 准确提及了 Android 14 的广播超时松弛。
- **建议**: 补充提及 Android 14+ 针对冷启动期间 CPU 饥饿导致的超时放宽（从 10s 可延至 20s），这对于区分“启动代码太重”还是“系统环境太差”非常有帮助。
- **来源**: 外部AI review (2026-04-25-11-15.2-external-review.md)

- **类型**: P2
- **位置**: 
- **问题**: 提供的 SQL 是总计。
- **建议**: 增加一个“按线程状态统计 Top 10 耗时线程”的 SQL，帮助读者一键定位 Runnable 最高的嫌疑人。
- **来源**: 外部AI review (2026-04-25-11-15.2-external-review.md)


## [External Review] 15.3 - 选择理由：指标是性能治理的“度量衡”。在 2026 年的背景下，如果仍然仅依赖 60Hz 时代的“16ms”定义，将无法指导现代高刷/VRR 设备的优化。 — 2026-04-25
- **类型**: P2
- **位置**: 
- **问题**: 提到 SplashScreen 让感知等待变短，但未提及 `reportFullyDrawn()` 对系统优化（如启动预热）的反馈作用。
- **建议**: 补充说明调用 `reportFullyDrawn()` 不仅是为了度量指标，还会触发系统的启动序列优化（如写入基线配置文件）。
- **来源**: 外部AI review (2026-04-25-12-15.3-external-review.md)

- **类型**: P2
- **位置**: 
- **问题**: 提到 100ms/200ms 是经验值。
- **建议**: 可以引用经典的“100ms 阈值”（基于人类感知的 Miller 1968 报告），并提及在高刷新率（120Hz+）和低触摸延迟技术下，现代旗舰机通常追求 50ms 以内的响应。
- **来源**: 外部AI review (2026-04-25-12-15.3-external-review.md)


## [External Review] 15.4 - 选择理由：竞品分析是衡量优化收益和设定性能目标（SLO）的关键环节。在 2026 年的背景下，随着 Android 系统组件的重构（如 AM/WM 合并）和新特性（SplashScreen）的普及，传统的测量手段需要更新。 — 2026-04-25
- **类型**: P2
- **位置**: 
- **问题**: 提到中位数，建议补充“变异系数（CV）”的概念。
- **建议**: 说明如果 CV（标准差/平均值）超过 15%，说明测试环境噪声过大（可能存在温控或后台干扰），该组数据应废弃。
- **来源**: 外部AI review (2026-04-25-13-15.4-external-review.md)

- **类型**: P2
- **位置**: 
- **问题**: [自动发现]中提到多进程架构的影响。
- **建议**: 补充说明 `am start -W` 仅追踪触发启动的 Intent 所在的 Activity 进程，对于“异步初始化”的后台 Service 进程耗时是盲区，必须配合 Perfetto 观察。
- **来源**: 外部AI review (2026-04-25-13-15.4-external-review.md)


## [External Review] 15.5 - 选择理由：线上监控是性能治理的“眼睛”。在 Android 15/16 周期下，监控手段正在从“端侧自研 Hook”向“系统原生 ProfilingManager”演进，本章需要对这一跨代变化做出准确指导。 — 2026-04-25
- **类型**: P2
- **位置**: 
- **问题**: 提到 JankStats 在低版本用 `OnPreDrawListener`。
- **建议**: 补充说明其核心价值在于利用 `OnPreDrawListener` 作为一个同步“锚点”，将 `PerformanceMetricsState`（同步状态）与 `FrameMetrics`（异步信号）在时间线上准确对齐，解决了纯 FrameMetrics 拿不到业务上下文的痛点。
- **来源**: 外部AI review (2026-04-25-14-15.5-external-review.md)

- **类型**: P2
- **位置**: 
- **问题**: 提到 5% 采样够用。
- **建议**: 补充一个具体案例，例如：对于 1000 万 DAU 的应用，5% 采样意味着每天有 50 万个会话样本，足以覆盖 95% 置信区间下的 P99 指标。
- **来源**: 外部AI review (2026-04-25-14-15.5-external-review.md)


## [External Review] 15.6 - 选择理由：性能测试是所有优化工作的基石。在 2026 年（Android 17 周期），面对高刷/VRR 设备普及和复杂的后台冻结机制，传统的测试方法（如仅清理后台）已不足以保证数据的一致性。 — 2026-04-25
- **类型**: P2
- **位置**: 
- **问题**: 仅提到了中位数和 P90。
- **建议**: 引入变异系数（Coefficient of Variation, CV = SD/Mean）作为数据质量门禁。建议 CV > 10% 时自动重测，说明环境噪声过大，测试结果无效。
- **来源**: 外部AI review (2026-04-25-15-15.6-external-review.md)

- **类型**: P2
- **位置**: 
- **问题**: 提到 `SpeedProfile` 移除。
- **建议**: 补充说明在没有 Baseline Profile 的情况下，使用 `CompilationMode.Partial(warmupIterations = 3)` 是模拟“稳定运行一段时间后”性能的最佳替代方案。
- **来源**: 外部AI review (2026-04-25-15-15.6-external-review.md)


## [External Review] 15.7 - 选择理由：源码阅读是性能优化的“降维打击”武器。在 2026 年（Android 17 周期），随着 AOSP 架构从 Java/C++ 向 Rust 演进，以及 AM/WM 的深度融合，传统的阅读路径（仅关注 `am` 目录）已经不足以应对现代性能分析。 — 2026-04-25
- **类型**: P2
- **位置**: 
- **问题**: 目录结构未提及 SystemUI。
- **建议**: 增加 `frameworks/base/packages/SystemUI/` 目录。对于分析状态栏卡顿、通知中心渲染、锁屏启动等性能场景，这是第一现场。
- **来源**: 外部AI review (2026-04-25-16-15.7-external-review.md)

- **类型**: P2
- **位置**: 
- **问题**: 未提及 AOSP 中的 Rust 代码。
- **建议**: 在 2026 年的背景下，简要提及 `system/core` 和 `frameworks/native` 中开始出现 Rust 代码（`.rs` 文件），提醒读者遇到此类代码时的阅读预期。
- **来源**: 外部AI review (2026-04-25-16-15.7-external-review.md)


## [Task9 Deep Review] 15.8 Android 性能问题实证：真实世界的分类与代码模式 — 2026-04-25
- **类型**：版本差异
- **位置**：适用范围 Android 8-17 / 代码模式章节
- **问题**：章节覆盖到 Android 17，但未提示 Android 14+ cached-app freezer 对后台进程执行、同步 Binder 事务和解冻后任务堆积的影响。该机制不一定属于论文原始 taxonomy，但会影响现代版本中“启动/切换慢”的归因。
- **建议**：补一个版本边界小节：Android 14+ cached app freezer 对后台工作、同步 Binder 事务、解冻后响应性毛刺的影响；明确这是 Android 版本机制补充，不写成论文原始结论。

## [Task9 Deep Review] 19.23 网络 APM 底层捕获原理 — 2026-04-25
- **类型**：知识盲区
- **位置**：L205-L249 ASM openConnection 示例
- **问题**：示例只覆盖 URL.openConnection()，未提醒 openConnection(Proxy) 与 openStream() 入口。实战中代理、SDK 包装层和旧代码会使用这些重载/快捷方法。
- **建议**：补充需要覆盖的调用点清单：openConnection()、openConnection(Proxy)、openStream()，并说明只替换调用点不等于能看到 Native 网络库内部请求。

## [Task9 Deep Review] 19.23 网络 APM 底层捕获原理 — 2026-04-25
- **类型**：数据缺失
- **位置**：L326 HTTP/2 多路复用说明
- **问题**：已说明 HTTP/2 阶段耗时不再与 socket 事件一一对应，但缺少 OkHttp 事件口径：复用连接时后续请求通常不再触发 dnsStart/connectStart，主要从 connectionAcquired 后进入请求发送阶段。
- **建议**：补一个 EventListener 观察点表，解释“看板里大量请求 DNS/TCP 为空”是连接复用/HTTP2 multiplexing 的正常现象。

## [Task9 Deep Review] 19.24 崩溃与 ANR 捕获机制 — 2026-04-25
- **类型**：知识盲区
- **位置**：L232 VMA 耗尽
- **问题**：VMA/VmSize 被与 FD、线程并列为通用监控项，但未区分 32 位与 64 位。32 位进程地址空间紧张，VMA/映射碎片更容易变成真实故障；64 位进程地址空间大，监控重点更多是映射数量、RSS/PSS 与异常 mmap 泄漏。
- **建议**：补充 32/64 位差异：32 位强调地址空间上限和碎片，64 位强调极端映射泄漏、maps 行数、RSS/PSS 与图形/ashmem 资源。

## [Task9 Deep Review] 19.0 第 19 章：APM 工具与性能监控生态 — 2026-04-25
- **类型**：交叉引用一致性
- **位置**：`## 本章内容`
- **问题**：本章目录只列到 19.22，但 `src/part3-tools/ch19-apm/` 已存在 19.23-19.27：网络 APM 底层捕获原理、崩溃与 ANR 捕获机制、功耗与热治理 APM、Hybrid APM、APM 客户端架构。README 作为全章总纲没有覆盖这些章节，会让读者误判本章范围，也会让后续章节引用失去入口。
- **建议**：把 19.23-19.27 补进“本章内容”，并在“全景分类”里增加“底层捕获与客户端架构”分组，避免把网络、崩溃、功耗、Hybrid 和客户端架构散落到工具清单之外。

## [External Review] 19.01 APM 全景图与分类体系 — 2026-04-25
- **类型**：最佳实践缺失
- **位置**：系统 API 采集代价
- **问题**：未提及 `ApplicationExitInfo` 存在的 IPC 开销陷阱。
- **建议**：补充说明应在异步线程获取 `getHistoricalProcessExitReasons`。
- **来源**：Gemini 外部 review


## [External Review] 19.02 Tencent Matrix — 2026-04-25
- **类型**：未分类
- **位置**：未知
- **问题**：
- **建议**：
- **来源**：Gemini 外部 review


## [External Review] 19.03 APM 数据采集与传输 — 2026-04-25
- **类型**：未分类
- **位置**：未知
- **问题**：
- **建议**：
- **来源**：Gemini 外部 review


## [External Review] 19.04 APM 指标体系与看板 — 2026-04-25
- **类型**：未分类
- **位置**：未知
- **问题**：
- **建议**：
- **来源**：Gemini 外部 review


## [External Review] 19.07 APM 线下性能工具 — 2026-04-25
- **类型**：未分类
- **位置**：未知
- **问题**：
- **建议**：
- **来源**：Gemini 外部 review


## [External Review] 19.08 APM 线上监控实战 — 2026-04-25
- **类型**：细节严谨性
- **位置**：网络监控的现代适配
- **问题**：对于 `EventListener` 的使用未提及 OkHttp 版本分界线。
- **建议**：补充说明 EventListener 完整支持需要 `OkHttp >= 3.11`，呼应前文“先升级网络库版本”的迁移建议。
- **来源**：Gemini 外部 review


## [External Review] 19.09 APM 卡顿监控 — 2026-04-25
- **类型**：未分类
- **位置**：未知
- **问题**：
- **建议**：
- **来源**：Gemini 外部 review


## [External Review] 19.10 APM ANR 监控 — 2026-04-25
- **类型**：未分类
- **位置**：未知
- **问题**：
- **建议**：
- **来源**：Gemini 外部 review


## [External Review] 19.13 APM 网络监控 — 2026-04-25
- **类型**：未分类
- **位置**：未知
- **问题**：
- **建议**：
- **来源**：Gemini 外部 review


## [External Review] 19.14 APM 电量监控 — 2026-04-25
- **类型**：未分类
- **位置**：未知
- **问题**：
- **建议**：
- **来源**：Gemini 外部 review


## [External Review] 19.17 APM 端到端链路 — 2026-04-25
- **类型**：未分类
- **位置**：未知
- **问题**：
- **建议**：
- **来源**：Gemini 外部 review


## [External Review] 19.18 APM 数据分析 — 2026-04-25
- **类型**：知识增强
- **位置**：Sentry Profiling 段落
- **问题**：建议补充具体的崩溃信号 `SIGSEGV` 在 `libart.so` 中的特征。
- **建议**：
- **来源**：Gemini 外部 review


## [External Review] 19.19 APM 治理体系 — 2026-04-25
- **类型**：建议改进
- **位置**：指标部分
- **问题**：建议补充 FPower 指标。
- **建议**：
- **来源**：Gemini 外部 review


## [External Review] 19.20 APM 平台架构 — 2026-04-25
- **类型**：未分类
- **位置**：未知
- **问题**：
- **建议**：
- **来源**：Gemini 外部 review


## [External Review] 19.21 APM 告警与根因分析 — 2026-04-25
- **类型**：未分类
- **位置**：未知
- **问题**：
- **建议**：
- **来源**：Gemini 外部 review


## [External Review] 19.01 01-apm-landscape.md — 2026-04-25
- **类型**：建议改进
- **位置**：01-apm-landscape.md
- **问题**：- [P2][知识盲区][常见采集路线的工程代价]
  - 原文问题：对 `ApplicationExitInfo`（API 30+）的代价描述不足。
  - 证据或观察依据：`ActivityManager.getHistoricalProcessExitReasons()` 是一个对 `system_server` 的同步 IPC 调用。很多业务 APM 喜欢在 App 刚启动的主线程里调用它来判断上次退出的原因，这会导致严重的启动性能退化（Lock 竞争）。
  - 建议：在提及 `ApplicationExitInfo` 的代价时，补充一句提醒：“获取历史退出原因涉及对 `system
- **来源**：外部 AI review

## [External Review] 19.03 03-koom.md — 2026-04-25
- **类型**：建议改进
- **位置**：03-koom.md
- **问题**：- [P2][原理链完整性][Hprof 裁剪和引用链摘要]
  - 原文问题：提到“Hprof 文件仍然很大，需要裁剪或只上传摘要”，但未说明裁剪了什么。
  - 证据或观察依据：在 Hprof 结构中，占据绝大多数空间的往往是 primitive arrays (如 `byte[]`，通常是图片像素数据或大文本)。
  - 问题描述：缺少对裁剪对象的说明，使内容停留在概念上。
  - 建议：补充说明 Hprof 裁剪的本质往往是丢弃大量的基本数据类型数组（Primitive Array），只保留类元数据和对象引用关系网。
- **来源**：外部 AI review

## [External Review] 19.07 19.07 — 2026-04-25
- **类型**：建议改进
- **位置**：19.07
- **问题**：- [P2][知识盲区][和 Android Studio Profiler、Perfetto 的关系]
- 原文问题：虽然说明了“DoKit 给的是入口，不是最终证据”，但没有明确点出它与线上成熟 APM 工具在技术实现流派上的最大区别。
- 问题描述：诸如 Matrix 等线上 APM 倾向于使用底层的 PLT Hook (例如 xhook) 或相对轻量的抽样机制；而 DoKit 作为 Debug 工具则肆无忌惮地依赖较重的运行时计算或全量字节码插桩。
- 建议：在对比说明中，可以一语道破 DoKit 的“全量插桩/高频轮询策略”与线上 APM 的“抽样/底层轻量级 Hook 策略”在架构
- **来源**：外部 AI review

## [External Review] 19.08 src/part3-tools/ch19-apm/08-argusapm.md — 2026-04-25
- **类型**：建议改进
- **位置**：src/part3-tools/ch19-apm/08-argusapm.md
- **问题**：- [P2][细节严谨性][网络监控的现代适配]
- 原文问题：网络阶段拆分中提到了使用 `StageEventListener` 代替 `Interceptor`，但未考虑到旧版本 OkHttp 的限制。
- 证据或观察依据：OkHttp 在 `3.11.0` 才引入了相对完整成熟的 `EventListener` 机制。而上文（兼容风险章节）明确提到公开 sample 的基线停留在 `okhttp:3.10.0`。
- 问题描述：如果读者强行在存量旧系统（基于 3.10.0）上套用这段现代化的 EventListener 适配代码，可能会遇到 API 缺失或回调不全的问题。
- 建议：在展
- **来源**：外部 AI review

## [External Review] 19.09 src/part3-tools/ch19-apm/09-measure.md — 2026-04-25
- **类型**：建议改进
- **位置**：src/part3-tools/ch19-apm/09-measure.md
- **问题**：- [P2][版本差异覆盖][核心能力]
  - 原文问题：“Crash / ANR 自动捕获”
  - 证据或观察依据：现代 APM 在 Android 端捕获 ANR 存在明显的版本分水岭：Android 11 之前通常依赖 `FileObserver` 监听 `/data/anr/traces.txt` 或者拦截 SIGQUIT 信号；而 Android 11+ 引入了官方的 `ApplicationExitInfo`（`REASON_ANR`）来回溯崩溃和 ANR 原因。
  - 问题描述：原文只是介绍了 Measure 的能力，但在 AIW 这个以深度机制解析为主的 Wiki 中，缺
- **来源**：外部 AI review

## [External Review] 19.09 src/part3-tools/ch19-apm/09-measure.md — 2026-04-25
- **类型**：建议改进
- **位置**：src/part3-tools/ch19-apm/09-measure.md
- **问题**：- [P2][数据/案例支撑][隐私策略要在接入前定清]
  - 原文问题：“截图 / 附件：默认开启文字或敏感输入遮罩”
  - 证据或观察依据：移动端的 Screenshot Mask 通常不是魔法，它一般需要通过遍历当前 Activity 的 View Hierarchy（视图树），找出特定的 inputType（如 password）或者开发者打上的特定 Tag，然后在最终的 Bitmap 截图中用实色方块覆盖对应的坐标（bounds）。
  - 问题描述：原文只提了功能现象，没有提及 Android 上的实现成本和原理。
  - 建议：简要补充 Screenshot Mask 的底层
- **来源**：外部 AI review

## [External Review] 19.10 src/part3-tools/ch19-apm/10-other-opensource-apm.md — 2026-04-25
- **类型**：建议改进
- **位置**：src/part3-tools/ch19-apm/10-other-opensource-apm.md
- **问题**：- [P2][知识盲区][Collie 轻量线上采样思路]
  - 原文问题：启动采集依赖“`ContentProvider`、window focus 等关键节点”。
  - 问题描述：虽然借助 ContentProvider 采集启动耗时是经典方案，但在当前现代化 Android 开发中，开发者大概率在使用 `androidx.startup`。
  - 建议：建议顺带提及现今广泛使用的 Jetpack App Startup，指出轻量 APM 若使用 ContentProvider，需与 App Startup 这类初始化框架评估执行顺序或进行整合。
- **来源**：外部 AI review

## [External Review] 19.10 src/part3-tools/ch19-apm/10-other-opensource-apm.md — 2026-04-25
- **类型**：建议改进
- **位置**：src/part3-tools/ch19-apm/10-other-opensource-apm.md
- **问题**：- [P2][原理链完整性][最小 APM SDK 采集方式]
  - 原文问题：慢帧信号来源列举了 `JankStats / Choreographer / FrameMetrics`，未作优先级区分。
  - 问题描述：读者对于选哪一个会有困惑。`FrameMetrics` 适用 API 24+，而 `JankStats` 是官方目前推荐的、支持到 API 16 并且能附带生命周期/UI 状态追踪的最佳封装。
  - 建议：建议注明 `JankStats` 作为首要推荐库，而将其余两者作为其底层原理来源或降级参考。
- **来源**：外部 AI review

## [External Review] 19.14 src/part3-tools/ch19-apm/14-jetpack-benchmark.md — 2026-04-25
- **类型**：建议改进
- **位置**：src/part3-tools/ch19-apm/14-jetpack-benchmark.md
- **问题**：- [P2][数据/案例支撑][CI 中的噪声控制]
  - 原文问题：“设备温度过高时跳过或降权本轮结果”描述得像是需要外部 CI 脚本自己处理。
  - 证据或观察依据：`androidx.benchmark` 内部包含了 `ThermalThrottle` 检测机制。
  - 问题描述：Benchmark 库在执行期间，默认会监控设备热节流状态。如果设备过热，库会自动介入休眠等待降温（Sleep to cool down），或者通过 `IsolationActivity` 进行控制。
  - 建议：修正表述，说明 Benchmark 库自身具备热节流防御机制，但 CI 环境仍需保证散热条
- **来源**：外部 AI review

## [External Review] 19.18 src/part3-tools/ch19-apm/18-commercial-apm.md — 2026-04-25
- **类型**：建议改进
- **位置**：src/part3-tools/ch19-apm/18-commercial-apm.md
- **问题**：- [P2][知识盲区][Sentry profiling 风险]
  - 原文问题：提到 profiling 存在特定场景 crash 风险，但未给出具体特征。
  - 证据或观察依据：Sentry 官方文档和 GitHub Issue。
  - 问题描述：缺少具体的信号特征（如 `pthread_getcpuclockid` 或 `art::Trace::StopTracing` 崩溃）。
  - 建议：在 Sentry profiling 段落补充这些特征，帮助工程人员在 Logcat 中快速识别是否为 Sentry SDK 导致的系统级崩溃。
- **来源**：外部 AI review

## [External Review] 19.18 src/part3-tools/ch19-apm/18-commercial-apm.md — 2026-04-25
- **类型**：建议改进
- **位置**：src/part3-tools/ch19-apm/18-commercial-apm.md
- **问题**：- [P2][原理链完整性][APMPlus 私有化]
  - 原文问题：提到私有化，但未说明其核心技术栈。
  - 问题描述：APMPlus 私有化核心依赖 ClickHouse (ByteHouse) 和 Flink。
  - 建议：在私有化部分简述其对高性能存储的要求，这对企业采购时的硬件成本评估非常重要。
- **来源**：外部 AI review

## [External Review] 19.19 src/part3-tools/ch19-apm/19-perfdog.md — 2026-04-25
- **类型**：建议改进
- **位置**：src/part3-tools/ch19-apm/19-perfdog.md
- **问题**：- [P2][知识盲区][与自动化脚本结合]
- 原文问题：未提及 PerfDog Service APK 的角色。
- 问题描述：PerfDog 通过 PUSH 一个辅助 APK 到设备来作为“特权代理”，利用 shell 权限绕过部分沙箱限制。
- 建议：简要说明 PerfDog Service 的作用，以及为什么需要通过 ADB 手动授予 `DUMP` 权限。
- **来源**：外部 AI review

## [External Review] 19.19 src/part3-tools/ch19-apm/19-perfdog.md — 2026-04-25
- **类型**：建议改进
- **位置**：src/part3-tools/ch19-apm/19-perfdog.md
- **问题**：- [P2][原理链完整性][功耗和温度的读法]
- 原文问题：未提及 FPower（每帧功耗）这一高价值衍生指标。
- 建议：补充 FPower 的概念（Total Power / FPS），它是评估渲染能效比的核心指标。
- **来源**：外部 AI review

## [External Review] 19.04 src/part3-tools/ch19-apm/04-btrace.md — 2026-04-25
- **类型**：建议改进
- **位置**：src/part3-tools/ch19-apm/04-btrace.md
- **问题**：- [P2][源码准确性][采集流程]
  - **原文问题**：App 包里集成 `com.bytedance.btrace:rhea-inhouse`，未提及具体版本号。
  - **证据或观察依据**：Btrace 3.0 与 2.x 的产物格式和能力有质的区别，3.0 默认输出 PB 格式以供 Perfetto 分析。
  - **问题描述**：不写具体版本号可能导致读者接入旧版本。
  - **建议**：建议将依赖声明更新为完整的 `com.bytedance.btrace:rhea-inhouse:3.0.0`（或当前最新版本）。
- **来源**：外部 AI review

## [External Review] 19.04 src/part3-tools/ch19-apm/04-btrace.md — 2026-04-25
- **类型**：建议改进
- **位置**：src/part3-tools/ch19-apm/04-btrace.md
- **问题**：- [P2][数据/案例支撑][Perfetto UI 里的读法]
  - **原文问题**：提到“看 CPU 调度：线程是否频繁 runnable 但拿不到 CPU”。
  - **证据或观察依据**：Perfetto UI 中 Runnable 和 Running 的视觉表现不同。
  - **问题描述**：对初次接触 Perfetto 的读者来说，知道要看 Runnable 状态，但不知道在 UI 上长什么样。
  - **建议**：建议用一两句话补充 UI 表现特征，例如“在 Perfetto 中，Runnable 通常表现为浅色/无 CPU 编号的片段，而实际运行（Running）状
- **来源**：外部 AI review

## [External Review] 19.11 ch19.11 — 2026-04-25
- **类型**：建议改进
- **位置**：ch19.11
- **问题**：### 1. [P2][源码准确性][jank 阈值]
- **问题描述**：默认倍率 2.0f 过于保守。
- **建议**：说明其 implication（2x 预期时长才判 jank）。
- **来源**：外部 AI review

## [External Review] 19.11 ch19.11 — 2026-04-25
- **类型**：建议改进
- **位置**：ch19.11
- **问题**：### 2. [P2][知识盲区][JankStats 状态]
- **问题描述**：未提示库处于 Alpha 阶段。
- **建议**：增加 API 稳定性风险提示。
- **来源**：外部 AI review

## [External Review] 19.13 13-tracing-sdk.md — 2026-04-25
- **类型**：建议改进
- **位置**：13-tracing-sdk.md
- **问题**：- [P2][知识盲区][Native 标注]
- **原文问题**：Native Trace 描述过于笼统。
- **问题描述**：仅提到了 native 侧有自定义事件，未给出具体的 API 参考。
- **建议**：补充 `#include <android/trace.h>` 以及 `ATrace_beginSection` / `ATrace_endSection` 的名称，并明确说明 native slice 会出现在相同的线程轨道上。
- **来源**：外部 AI review

## [External Review] 19.13 13-tracing-sdk.md — 2026-04-25
- **类型**：建议改进
- **位置**：13-tracing-sdk.md
- **问题**：- [P2][原理链完整性][阅读方式]
- **原文问题**：缺失对 "Gap" 和 "Scheduler" 的观察方法。
- **问题描述**：大纲要求说明如何看 gap 和 scheduler。
- **建议**：在 Perfetto UI 描述部分，增加关于“两个同步 Slice 之间的 Gap 可能代表 I/O 等待或 CPU 调度抢占”的说明，并引导读者查看 Thread State 轨道。
- **来源**：外部 AI review

## [External Review] 19.17 src/part3-tools/ch19-apm/17-firebase-performance.md — 2026-04-25
- **类型**：建议改进
- **位置**：src/part3-tools/ch19-apm/17-firebase-performance.md
- **问题**：- [P2][知识盲区][网络请求聚合和 URL pattern]
- **原文问题**：提及了 Cronet，但未说明其采集特殊性。
- **问题描述**：FPM 的 Gradle 插件无法自动对 Cronet 这种 native 网络栈进行字节码插桩。
- **建议**：明确指出使用 Cronet 时需要手动使用 `FirebasePerfUrlConnection` 包装或添加拦截器，否则会自动“漏掉”。
- **来源**：外部 AI review

## [External Review] 19.17 src/part3-tools/ch19-apm/17-firebase-performance.md — 2026-04-25
- **类型**：建议改进
- **位置**：src/part3-tools/ch19-apm/17-firebase-performance.md
- **问题**：- [P2][数据/案例支撑][数据模型：trace、metric、attribute]
- **原文问题**：描述 Metric 时使用“低基数”。
- **问题描述**：Metric 是数值（Long），属性（Attribute）才是用来做分类聚合的（涉及基数问题）。
- **建议**：修改表述，强调 Metric 用于计算（累加、平均），Attribute 用于过滤和分组（高基数 Attribute 会导致控制台聚合失败）。
- **来源**：外部 AI review

## [External Review] 19.21 21-benchmark-apps.md — 2026-04-25
- **类型**：建议改进
- **位置**：21-benchmark-apps.md
- **问题**：- [P2][原理链完整性][Geekbench 分数的工程解释]
- **问题描述**：未提及 Geekbench 6 的 **“Shared Task” (共享任务)** 模型。
- **原理说明**：GB6 从 GB5 的独立多核任务改为多核协同完成单一任务（模拟真实软件逻辑），这解释了为什么现代高核数 SoC 的 GB6 多核分数增长不如 GB5 线性。
- **建议**：补充这一技术细节，帮助读者理解 Benchmark 建模逻辑的演进。
- **来源**：外部 AI review

## [External Review] 19.21 21-benchmark-apps.md — 2026-04-25
- **类型**：建议改进
- **位置**：21-benchmark-apps.md
- **问题**：- [P2][知识盲区][3DMark 分数的工程解释]
- **问题描述**：仅提到 Wild Life 级别的测试，未提及现代光追（Solar Bay）和 AAA 级负载（Steel Nomad Light）。
- **建议**：补充针对 Android 14+ 旗舰机型应关注 **Solar Bay**（测光追性能）和 **Steel Nomad Light**（取代 Wild Life Extreme）的建议。
- **来源**：外部 AI review

## [External Review] 19.21 21-benchmark-apps.md — 2026-04-25
- **类型**：建议改进
- **位置**：21-benchmark-apps.md
- **问题**：- [P2][知识盲区][历史工具的处理]
- **问题描述**：提到 Vellamo 已过期，但未给出现代 Web 性能测试建议。
- **建议**：补充 **Speedometer 3.0** 或 **JetStream 2** 作为现代移动浏览器/Web 性能的基准工具。
- **来源**：外部 AI review


## [Task9 Deep Review] 19.26 混合栈与跨平台 APM (WebView / Flutter) — 2026-04-25
- **类型**：数据缺失
- **位置**：§2 PixelCopy 白屏采样示例
- **问题**：示例每次 createBitmap，未说明 bitmap 复用、降采样尺寸、PixelCopy error code 记录和采样成本上限。线上白屏采样如果在弱机上集中触发，监控本身会制造内存抖动。
- **建议**：补充固定尺寸 bitmap pool / 采样矩形缩放 / result code 上报 / 采样频率上限，并建议在灰度中记录单次采样耗时和 bitmap 分配量。


## [Task9 Deep Review] 19.26 混合栈与跨平台 APM (WebView / Flutter) — 2026-04-25
- **类型**：原理链完整性
- **位置**：§5 Flutter FrameTiming 映射为 Android Jank
- **问题**：正文提到 buildDuration/rasterDuration 超过刷新率预算可能丢帧，但没有说明 addTimingsCallback 是批量回调，也没有区分 build/raster/totalSpan 与 Android 宿主帧的关系。
- **建议**：补充“Flutter 自有帧预算”与“Android 宿主 Choreographer”分层：按当前刷新率计算预算，分别聚合 UI/Raster/totalSpan，不把单个字段直接等同于 Android FrameMetrics/JankStats 的 jank。

## [Task2B Blocked] 19.27 千万级 DAU 的 APM 端侧架构 — 2026-04-25
- **类型**：流程阻断
- **位置**：全文
- **问题**：当前章节仅有大纲，属于空 draft / 正文草拟范围。Task 2B 只做回炉修复，不能新写整章。
- **建议**：退回正文草拟流程完成初稿后，再进入 Task 6 / Task 9 review。
- **来源**：Task 2B 回炉修复

## [Task9 Deep Review] 2.1 Android 渲染架构全景 — 2026-04-25
- **类型**：源码准确性 / 示意代码边界
- **位置**：`SkiaPipeline::draw(RenderNode* root)` 伪代码（约 L486）
- **问题**：android-16.0.0_r1 中 Skia pipeline 的实际入口是 `SkiaOpenGLPipeline::draw(...)` / `SkiaVulkanPipeline::draw(...)` 与 `SkiaPipeline::renderFrame(...)` 等组合；`SkiaPipeline::draw(RenderNode*)` 不是可核对的方法签名。
- **建议**：保留概念解释时加 `[示意性伪代码]`，同时在文字里给出现代 HWUI 可核对入口：`pipeline/skia/SkiaOpenGLPipeline.cpp`、`SkiaVulkanPipeline.cpp`、`SkiaPipeline.cpp::renderFrame(...)`。

- **类型**：版本差异 / Trace 可执行性
- **位置**：`CALLBACK_INSETS_ANIMATION` 调用树与 `[待补充：Trace 中三缓冲的监控方法]`
- **问题**：`CALLBACK_INSETS_ANIMATION` 属于较新版本 Choreographer callback type，章节适用范围从 API 11 开始，代码树缺少版本边界；三缓冲 Trace 观察点仍是待补充，读者无法落到 BufferQueue/Fence/FrameTimeline 的验证步骤。
- **建议**：为 `CALLBACK_INSETS_ANIMATION` 标注 Android 11+ 边界；补一段最小 Trace 观察法：FrameTimeline、BufferQueue dequeue/queue/acquire/release、fence wait、SurfaceFlinger present/release fence 的对应关系。

## [Task9 Deep Review] 5.5 Thermal 管控 — 2026-04-25
- **类型**：原理边界
- **位置**：`Thermal Governor：从 trip crossing 到 cooling state`（约 L147）
- **问题**：正文写“Android 设备默认使用 step_wise”容易被理解为所有设备的实际温控策略都可从 kernel thermal governor 推导；但后文也承认 Qualcomm/MTK 等平台有 vendor thermal engine，实际策略经常由厂商用户态守护进程和私有配置决定。
- **建议**：把该句收窄为“内核 thermal framework 中常见 governor 是 step_wise；实际设备是否走该策略、调节哪些 cooling device，由厂商 thermal engine 与内核配置共同决定”。

- **类型**：版本差异
- **位置**：frontmatter `applicable_versions_note` 与版本演进表 Android 16 条目（约 L580）
- **问题**：frontmatter 标注 Android 15-17 待验证，版本表又写入 Android 16 ADPF Game Mode API 扩展。当前没有给出一手 API / CDD / ADPF 文档锚点。
- **建议**：发布前二选一：补官方 ADPF / API change / CDD 证据；或把 Android 15-17 内容降为“待验证附录”，正文适用范围收回到已验证的 Android 7-14。

## [Task9 Deep Review] 7.11 WebView 渲染性能与优化 — 2026-04-25
- **类型**：源码准确性 / 版本证据
- **位置**：`AwContents` 泄漏 bug 段落（约 L349）
- **问题**：正文点名“Android 13 上的部分 Samsung 设备”和“native lambda 持有 WebView 实例长达 10 秒”，但只标 `[待验证]`，没有 Chromium bug、provider 版本或设备 build 证据。该说法如果无证据，容易被读者当作确定的厂商缺陷。
- **建议**：补 Chromium issue / WebView provider 版本 / 复现设备信息；若暂时无法验证，删掉 Samsung 与 Android 13 限定，改成“某些 provider 版本出现过实例释放延迟，需要以 leak trace 和 provider 版本确认”。

- **类型**：数据缺失
- **位置**：WebView 冷启动、内存与 Perfetto 观察点（多处“明显跳升/明显更长”）
- **问题**：章节很克制地避免写固定毫秒和 MB，但完全没有给出一组带设备条件的 baseline，读者难以判断“明显”在自己的设备上应落在哪个量级。
- **建议**：补一组最小观测表：设备型号、Android/WebView provider 版本、是否 multiprocess、首次/二次创建主线程耗时、renderer 拉起时间、native heap / graphics / RSS 增量。

## [Task9 Deep Review] 19.02 Tencent Matrix — 2026-04-25
- **类型**：原理链完整性
- **位置**：L207-L213 / L215-L230
- **问题**：Trace Canary 只写 method id 与 method map 必须关联，但没有说明 methodMapping.txt 在编译期由插桩流程生成、线上 payload 依赖该文件反解方法名。
- **建议**：补 methodMapping 生成与服务端反解链路，说明 mapping / method map 丢失时线上报告只能保留数字 id。

## [Task9 Deep Review] 19.02 Tencent Matrix — 2026-04-25
- **类型**：数据缺失
- **位置**：L215-L230（Matrix 报告入库）
- **问题**：表格列了平台字段，但没有 Trace Canary 慢函数或 IO Canary 的具体 Issue payload 示例，读者仍不知道 Matrix 上报字段和排查动作怎么对应。
- **建议**：补一个 Trace block/slow method JSON 片段和一个 IO main-thread 文件读写样例，演示 cost、stack/method id、file path、buffer size 如何驱动下一步 Perfetto 或代码排查。

## [Task9 Deep Review] 19.02 Tencent Matrix — 2026-04-25
- **类型**：知识盲区
- **位置**：L89-L92 / L131-L140
- **问题**：Battery Canary、MemGuard、Pthread Hook 被列入能力表，但没有写清系统服务 Hook、PLT Hook、native heap 防护在定制 ROM、ABI、灰度采样上的稳定性风险。
- **建议**：补底层 Hook 模块的启用前提、崩溃回滚策略、采样率和远程开关要求，不要让读者把它们当成默认可全量开启的模块。

## [Task9 Deep Review] 19.15 Baseline Profiles 与编译优化 — 2026-04-25
- **类型**：数据缺失
- **位置**：L175-L184（验证 profile 是否生效）
- **问题**：验证表没有给系统底层核验命令，ProfileVerifier 能说明状态，但排查 ART 采纳情况还需要看 dexopt 状态。
- **建议**：补 `adb shell dumpsys package <pkg> | grep -A 10 dexopt` 或等价命令，观察 speed-profile / compilation status，并说明不同 Android 版本输出字段可能不同。

## [Task9 Deep Review] 19.17 Firebase Performance — 2026-04-25
- **类型**：原理链完整性
- **位置**：L90-L94（trace、metric、attribute 表）
- **问题**：metric 被写成“低基数、可聚合数值”。基数问题主要属于 attribute 过滤/分组维度；metric 是数值计量，用于累加、平均或分布统计。
- **建议**：把 metric 改成“数值计量，不拼动态维度”；把低基数约束移动到 attribute，并提醒高基数 attribute 会破坏控制台聚合。

## [2026-04-25] External Review Integration

### [External Review] 19.04 btrace / RheaTrace — 2026-04-25
- **类型**: 版本标识
- **位置**: 采集流程
- **问题**: 未提及 rhea-inhouse 具体版本号，可能接入旧版
- **建议**: 建议更新为 com.bytedance.btrace:rhea-inhouse:3.0.0
- **来源**: External AI Review

### [External Review] 19.04 btrace / RheaTrace — 2026-04-25
- **类型**: 数据支撑
- **位置**: Perfetto UI 里的读法
- **问题**: 缺乏 Runnable/Running 状态 UI 视觉特征
- **建议**: 补充浅色=Runnable、深色带CPU核心号=Running
- **来源**: External AI Review

### [External Review] 19.07 DoraemonKit / DoKit — 2026-04-25
- **类型**: 原理对比
- **位置**: 不适合替代线上 APM
- **问题**: 未从 Hook 深度区分 Debug 全量插桩与线上 APM 抽样/底层 Hook 的技术选型差异
- **建议**: 点明全量插桩 vs PLT Hook/信号捕获/抽样上报的架构差异
- **来源**: External AI Review

### [External Review] 19.08 ArgusAPM — 2026-04-25
- **类型**: 细节严谨性
- **位置**: 网络监控的现代适配
- **问题**: EventListener 使用未提及 OkHttp 版本分界线
- **建议**: 补充 EventListener 完整支持需要 OkHttp >= 3.11
- **来源**: External AI Review

### [External Review] 19.09 Measure — 2026-04-25
- **类型**: 版本差异
- **位置**: 核心能力 - Crash/ANR 捕获
- **问题**: 未提及 ANR 捕获的底层机制在 Android 11 前后的差异（Signal Catcher vs ApplicationExitInfo）
- **建议**: 补充 ApplicationExitInfo 在现代 APM 中的应用
- **来源**: External AI Review

### [External Review] 19.09 Measure — 2026-04-25
- **类型**: 机制实现
- **位置**: 隐私策略 - 截图遮罩
- **问题**: 只描述功能未提及 Android 端实现（View Hierarchy 遍历与坐标遮挡）
- **建议**: 补充 Screenshot Mask 的底层实现逻辑
- **来源**: External AI Review

### [External Review] 19.10 其他开源 APM 库（AndroidGodEye、Collie、Rabbit） — 2026-04-25
- **类型**: 技术落地
- **位置**: 最小 APM SDK 信号采集
- **问题**: JankStats/Choreographer/FrameMetrics 平级排列无优先级区分
- **建议**: 注明 JankStats 作为首选推荐，其余作为底层原理来源
- **来源**: External AI Review

### [External Review] 19.10 其他开源 APM 库（AndroidGodEye、Collie、Rabbit） — 2026-04-25
- **类型**: 技术落地
- **位置**: Collie 轻量采样
- **问题**: ContentProvider 采集启动耗时的方案需与 Jetpack App Startup 评估执行顺序
- **建议**: 提及 App Startup 与 ContentProvider 的整合考量
- **来源**: External AI Review

### [External Review] 19.13 androidx.tracing（Tracing SDK） — 2026-04-25
- **类型**: 细节改进
- **位置**: Native 标注
- **问题**: 缺乏具体 Native API 引导
- **建议**: 补充 ATrace_beginSection 及 #include <android/trace.h>
- **来源**: External AI Review

### [External Review] 19.13 androidx.tracing（Tracing SDK） — 2026-04-25
- **类型**: 原理链
- **位置**: 阅读方式
- **问题**: 缺失 Gap 和 Scheduler 观察方法
- **建议**: 增加两个 Slice 间 Gap 代表 I/O 等待或 CPU 调度抢占的说明
- **来源**: External AI Review

### [External Review] 19.14 Jetpack Benchmark（Microbenchmark + Macrobenchmark） — 2026-04-25
- **类型**: 表述优化
- **位置**: CI 中的噪声控制
- **问题**: 提到需人工处理设备温度，忽略 Benchmark 库自身的 ThermalThrottle 检测机制
- **建议**: 说明库内置过热休眠，但 CI 仍需保证散热
- **来源**: External AI Review

### [External Review] 19.19 PerfDog — 2026-04-25
- **类型**: 原理补充
- **位置**: 自动化脚本
- **问题**: 未提及 PerfDog Service APK 角色（特权代理利用 shell 权限）
- **建议**: 说明 Service APK 和 ADB DUMP 权限授予
- **来源**: External AI Review

### [External Review] 19.19 PerfDog — 2026-04-25
- **类型**: 指标补充
- **位置**: 功耗
- **问题**: 未提及 FPower（每帧功耗=Total Power/FPS）这一高价值衍生指标
- **建议**: 补充 FPower 概念
- **来源**: External AI Review

### [External Review] 19.21 Benchmark 应用（Geekbench、安兔兔、3DMark、PCMark、Vellamo） — 2026-04-25
- **类型**: 技术细节
- **位置**: Geekbench 分数
- **问题**: 未提及 GB6 Shared Task 模型变化
- **建议**: 补充多核协同单一任务的建模逻辑演进
- **来源**: External AI Review

### [External Review] 19.21 Benchmark 应用（Geekbench、安兔兔、3DMark、PCMark、Vellamo） — 2026-04-25
- **类型**: 覆盖不足
- **位置**: 3DMark
- **问题**: 仅提 Wild Life 级别，未提及 Solar Bay 和 Steel Nomad Light
- **建议**: 更新 3DMark 负载推荐列表
- **来源**: External AI Review

### [External Review] 19.21 Benchmark 应用（Geekbench、安兔兔、3DMark、PCMark、Vellamo） — 2026-04-25
- **类型**: 覆盖不足
- **位置**: Web 测试
- **问题**: 未给出现代 Web 性能基准
- **建议**: 补充 Speedometer 3.0 或 JetStream 2
- **来源**: External AI Review

### [External Review] 19.22 存储 Benchmark（AndroBench、A1 SD Bench） — 2026-04-25
- **类型**: 补充工具
- **位置**: AOSP 内置
- **问题**: 未提及 Android 系统自带 sm benchmark 命令
- **建议**: 补充 adb shell sm benchmark <diskId> 用法
- **来源**: External AI Review

## [Task9 Deep Review] 15.1 性能优化的术、道、器 — 2026-04-25
- **类型**：数据缺失
- **位置**：L201
- **问题**：性能预算示例给出“冷启动 1.5 秒”“90Hz 主线程 11ms”，但没有测试条件、设备档位或线上分位数口径。
- **建议**：为预算示例补充机型/刷新率/冷温热启动/分位数口径，或改成“示例阈值，需按业务基线确定”。


## [Task9 Deep Review] 15.2 如何区分系统问题和 App 问题 — 2026-04-25
- **类型**：数据缺失
- **位置**：L175
- **问题**：“Client 合成常见于几毫秒级，稳定拉长到 10ms+”缺少设备、分辨率、刷新率、Layer 数量和 HWC/Client composition 条件。
- **建议**：补充 Trace 样本或改成条件化表述，避免把经验阈值当成通用判据。


## [Task9 Deep Review] 15.3 性能指标体系 — 2026-04-25
- **类型**：数据缺失
- **位置**：L184
- **问题**：Click-to-Display 的 100ms/200ms 阈值已标“待验证”，仍缺少公开来源或本书自测条件。
- **建议**：补充来源、实验条件，或把阈值移到经验备注并避免作为治理红线。

## [External Review] 13.1 Perfetto 简介与演进 — 2026-04-25
- **类型**：知识补强
- **位置**：核心概念 - Data Source
- **问题**：未提及 ProtoZero 库，这是 Perfetto 开销极低的核心原因
- **建议**：补充 ProtoZero 零拷贝写入机制说明
- **来源**：Gemini 外部 review

## [External Review] 13.1 Perfetto 简介与演进 — 2026-04-25
- **类型**：架构说明
- **位置**：traced 通信机制
- **问题**：未明确 traced 通过 Unix Domain Socket 与应用进程通信
- **建议**：补充说明，解释加固 App 可能阻断追踪的原因
- **来源**：Gemini 外部 review

## [External Review] 13.2 Trace 抓取 — 2026-04-25
- **类型**：知识补强
- **位置**：Trace.beginSection 截断
- **问题**：未说明 127 字符限制的根本原因
- **建议**：补充内核 trace_marker 写入原子性保证和缓冲区限制说明
- **来源**：Gemini 外部 review

## [External Review] 13.3 Perfetto View — 2026-04-25
- **类型**：操作效率
- **位置**：快捷键
- **问题**：未提及 V 键（垂直参考线）
- **建议**：补充跨进程时间对齐快捷键说明
- **来源**：Gemini 外部 review

## [External Review] 13.3 Perfetto View — 2026-04-25
- **类型**：技术更新
- **位置**：SQL 查询
- **问题**：未提及新版 self_dur 字段
- **建议**：补充 self_dur 字段减少手动计算的说明
- **来源**：Gemini 外部 review

## [External Review] 13.4 大文件处理 — 2026-04-25
- **类型**：功能补强
- **位置**：Perfetto SQL 查询基础
- **问题**：未提及 Stdlib（INCLUDE PERFETTO MODULE）
- **建议**：补充官方预置分析模块介绍
- **来源**：Gemini 外部 review

## [External Review] 13.4 大文件处理 — 2026-04-25
- **类型**：内存优化
- **位置**：trace_processor 高级参数
- **问题**：未提及 --no-ftrace-raw 标志
- **建议**：超大 Trace 分析时关键内存优化手段
- **来源**：Gemini 外部 review

## [External Review] 13.4 大文件处理 — 2026-04-25
- **类型**：功能补强
- **位置**：Python 自动化分析
- **问题**：trace_processor 支持直接加载 .gz/.zip 文件
- **建议**：在加载 Trace 部分增加提示
- **来源**：Gemini 外部 review

## [External Review] 13.5 专题分析 — 2026-04-25
- **类型**：配置建议
- **位置**：13.5.3 Binder 抓取
- **问题**：建议加上 atrace_categories: "aidl" 以使 aidl_name 字段有值
- **建议**：在 Binder 抓取配置中显式加上 aidl 类别
- **来源**：Gemini 外部 review

## [External Review] 13.6 线程 CPU 状态 — 2026-04-25
- **类型**：数据支撑
- **位置**：SQL 量化分析
- **问题**：未提及 blocked_function 列
- **建议**：补充 D 状态分析的 blocked_function 查询示例
- **来源**：Gemini 外部 review

## [External Review] 13.7 高级用法 — 2026-04-25
- **类型**：准确性
- **位置**：自定义 Metric proto 字段号
- **问题**：字段号 450-500 说明不够严谨，仅限本地实验
- **建议**：补充说明合入 AOSP 需向 Perfetto 团队申请正式字段号
- **来源**：Gemini 外部 review

## [External Review] 13.8 Input Latency SQL — 2026-04-25
- **类型**：精确性
- **位置**：InputDispatcher 队列匹配
- **问题**：GLOB '*iq*' 匹配可能存在干扰
- **建议**：使用更精确的 track.name IN (...) 替代 GLOB 匹配
- **来源**：Gemini 外部 review

## [External Review] 13.1 — 2026-04-25
- **类型**：建议改进
- **章节**：13.1
- **问题**：[知识盲区] 核心概念 - Data Source
- **来源**：Gemini 外部 review (2026-04-25-13-ch13.01-external-review.md)


## [External Review] 13.1 — 2026-04-25
- **类型**：建议改进
- **章节**：13.1
- **问题**：[架构] traced
- **来源**：Gemini 外部 review (2026-04-25-13-ch13.01-external-review.md)


## [External Review] 13.2 — 2026-04-25
- **类型**：建议改进
- **章节**：13.2
- **问题**：[知识盲区] Trace.beginSection 截断细节
- **来源**：Gemini 外部 review (2026-04-25-13-ch13.02-external-review.md)


## [External Review] 13.3 — 2026-04-25
- **类型**：建议改进
- **章节**：13.3
- **问题**：[操作效率] 快捷键
- **来源**：Gemini 外部 review (2026-04-25-13-ch13.03-external-review.md)


## [External Review] 13.3 — 2026-04-25
- **类型**：建议改进
- **章节**：13.3
- **问题**：[技术更新] SQL
- **来源**：Gemini 外部 review (2026-04-25-13-ch13.03-external-review.md)


## [External Review] 13.5 — 2026-04-25
- **类型**：建议改进
- **章节**：13.5
- **问题**：[原理链] 13.5.3
- **来源**：Gemini 外部 review (2026-04-25-13-ch13.05-external-review.md)


## [External Review] 13.8 — 2026-04-25
- **类型**：建议改进
- **章节**：13.8
- **问题**：[知识盲区] InputDispatcher 队列匹配
- **来源**：Gemini 外部 review (2026-04-25-13-ch13.08-external-review.md)


## [External Review] 13.9 — 2026-04-25
- **类型**：建议改进
- **章节**：13.9
- **问题**：[知识盲区] 用户空间 Trace tag 底层实现
- **来源**：Gemini 外部 review (2026-04-25-13-ch13.09-external-review.md)


## [External Review] 13.9 — 2026-04-25
- **类型**：建议改进
- **章节**：13.9
- **问题**：[原理链完整性] atrace 的分类机制
- **来源**：Gemini 外部 review (2026-04-25-13-ch13.09-external-review.md)


## [External Review] 13.10 — 2026-04-25
- **类型**：建议改进
- **章节**：13.10
- **问题**：[数据/案例支撑] ANR 分析节
- **来源**：Gemini 外部 review (2026-04-25-13-ch13.10-external-review.md)


## [External Review] 13.10 — 2026-04-25
- **类型**：建议改进
- **章节**：13.10
- **问题**：[源码准确性] Binder 分析节
- **来源**：Gemini 外部 review (2026-04-25-13-ch13.10-external-review.md)


## [External Review] 14.1 — 2026-04-25
- **类型**：建议改进
- **章节**：14.1
- **问题**：[知识盲区] Memory Profiler
- **来源**：Gemini 外部 review (2026-04-25-14-ch14.01-external-review.md)


## [External Review] 14.2 — 2026-04-25
- **类型**：建议改进
- **章节**：14.2
- **问题**：[数据/案例支撑] simpleperf stat：快速查看事件计数
- **来源**：Gemini 外部 review (2026-04-25-14-ch14.02-external-review.md)


## [External Review] 14.2 — 2026-04-25
- **类型**：建议改进
- **章节**：14.2
- **问题**：[知识盲区] 准备工作
- **来源**：Gemini 外部 review (2026-04-25-14-ch14.02-external-review.md)


## [External Review] 14.3 — 2026-04-25
- **类型**：建议改进
- **章节**：14.3
- **问题**：[知识盲区] showmap 章节
- **来源**：Gemini 外部 review (2026-04-25-14-ch14.03-external-review.md)


## [External Review] 14.4 — 2026-04-25
- **类型**：建议改进
- **章节**：14.4
- **问题**：[数据支撑] meminfo 章节
- **来源**：Gemini 外部 review (2026-04-25-14-ch14.04-external-review.md)


## [External Review] 14.4 — 2026-04-25
- **类型**：建议改进
- **章节**：14.4
- **问题**：[原理链完整性] cpuinfo 章节
- **来源**：Gemini 外部 review (2026-04-25-14-ch14.04-external-review.md)


## [External Review] 14.5 — 2026-04-25
- **类型**：建议改进
- **章节**：14.5
- **问题**：[原理链完整性] ArgoAPM
- **来源**：Gemini 外部 review (2026-04-25-14-ch14.05-external-review.md)


## [External Review] 14.6 — 2026-04-25
- **类型**：建议改进
- **章节**：14.6
- **问题**：[原理链完整性] Espresso 同步机制影响
- **来源**：Gemini 外部 review (2026-04-25-14-ch14.06-external-review.md)


## [External Review] 14.7 — 2026-04-25
- **类型**：建议改进
- **章节**：14.7
- **问题**：[知识盲区] 结果通道部分
- **来源**：Gemini 外部 review (2026-04-25-14-ch14.07-external-review.md)


## [External Review] 14.7 — 2026-04-25
- **类型**：建议改进
- **章节**：14.7
- **问题**：[数据支撑] 失败结果处理部分
- **来源**：Gemini 外部 review (2026-04-25-14-ch14.07-external-review.md)


## [External Review] 14.9 — 2026-04-25
- **类型**：建议改进
- **章节**：14.9
- **问题**：[原理链完整性] HAL 3.5 requestStreamBuffers 同步阻塞
- **来源**：Gemini 外部 review (2026-04-25-14-ch14.09-external-review.md)


## [External Review] 14.10 — 2026-04-25
- **类型**：建议改进
- **章节**：14.10
- **问题**：[数据/案例支撑] CPU 利用率精准计算
- **来源**：Gemini 外部 review (2026-04-25-14-ch14.10-external-review.md)


## [External Review] 14.11 — 2026-04-25
- **类型**：建议改进
- **章节**：14.11
- **问题**：[版本差异] Android 14 权限与缓冲区
- **来源**：Gemini 外部 review (2026-04-25-14-ch14.11-external-review.md)


## [External Review] 14.13 — 2026-04-25
- **类型**：建议改进
- **章节**：14.13
- **问题**：[原理链完整性] icache 刷新的硬件背景
- **来源**：Gemini 外部 review (2026-04-25-14-ch14.13-external-review.md)



## [Task9 Deep Review] 13.2 Trace 抓取 — 2026-04-25
- **类型**：交叉引用/版本边界
- **位置**：命令行抓取：perfetto 命令
- **问题**：§13.1 写 Android 9 已有 Perfetto services，§13.2 写 Perfetto 从 Android 10 开始内置；两处没有解释“services 已进 system image”和“命令行文本配置/抓取入口”的差别。
- **建议**：明确 Android 9 的 binary protobuf / enable 边界、Android 10+ 的 --txt 配置入口，以及本章为什么把实操范围放在 Android 10+。


## [Task9 Deep Review] 7.1 卡顿的定义与分类 — 2026-04-25
- **类型**：源码准确性
- **位置**：L168-L173 DisplayHAL
- **问题**：DisplayHAL 解释停在现象层，未把判定条件接到 PresentFence / presentTime。android16 FrameTimeline::setSfPresent() 将 presentFence 放入 pending 队列，flush 后用 signalTime 调用 DisplayFrame::onPresent()，DisplayFrame::classifyJank() 在 SF finish on time 但 present late 且 delta 接近 vsync 周期时归为 DisplayHAL。
- **建议**：补一句底层证据：DisplayHAL 归因要看 present fence signal time 与 expected present 的差值，同时结合 SF combinedEndTime 是否已经按时完成；不要只写“HAL 慢”。

## [Task9 Deep Review] 7.1 卡顿的定义与分类 — 2026-04-25
- **类型**：版本差异
- **位置**：L312 JankStats
- **问题**：JankStats 阈值写成 current refresh period × multiplier，未区分 API 31+ 走 FrameMetrics.DEADLINE 的实现。AndroidX JankStatsApi31Impl#getExpectedFrameDuration() 返回 FrameMetrics.DEADLINE，并额外记录 frameOverrunNanos=TOTAL_DURATION-DEADLINE。
- **建议**：把表述改成：默认仍是 deadline × jankHeuristicMultiplier；API 31+ 的 deadline 来自 FrameMetrics.DEADLINE，旧版本才退化为按刷新率估算。

## [Task9 Deep Review] 7.2 卡顿原因体系 — 2026-04-25
- **类型**：源码准确性
- **位置**：L337 Binder 线程池耗尽
- **问题**：“libbinder 默认最多按需创建 15 个 Binder 线程”容易被读成总服务线程数 15。android16 ProcessState.cpp 中 DEFAULT_MAX_BINDER_THREADS=15，getThreadPoolMaxTotalThreadCount() 注释说明 startThreadPool 自己启动 1 个线程，kernel 还能按 mMaxThreads 再启动更多线程，用户也可能直接 joinThreadPool。
- **建议**：改成“默认 mMaxThreads=15，表示 kernel 可额外拉起的线程上限；调用 startThreadPool() 本身会先启动 1 个线程，所以默认池总量通常按 1+15 理解，另有手动 joinThreadPool 的边界”。



## [External Review] 7.4 典型卡顿场景分析 — 2026-04-25
- **类型**：原理链完整性
- **位置**：§5.2 多任务切换
- **问题**：TaskSnapshot 使用 HardwareBuffer 但未点出 Zero-copy
- **建议**：简要点出 HardwareBuffer 通过 Zero-copy 提升 Recents 列表流畅度
- **来源**：Gemini 外部 review

## [External Review] 7.5 优化策略 — 2026-04-25
- **类型**：原理链完整性
- **位置**：Compose 优化
- **问题**：未补充 Strong Skipping 模式如何减少 Stable 标记依赖
- **建议**：补充 Strong Skipping 作为 2025 Compose 优化里程碑的意义
- **来源**：Gemini 外部 review

## [External Review] 7.6 案例集 — 2026-04-25
- **类型**：数据支撑
- **位置**：案例一
- **问题**：缺少 View 层级对比数据
- **建议**：引用 Google 官方博文 ConstraintLayout 比传统嵌套快 40% 的数据
- **来源**：Gemini 外部 review

## [External Review] 7.8 RecyclerView 深度优化 — 2026-04-25
- **类型**：原理链
- **位置**：ViewHolder 缓存
- **问题**：ViewCacheExtension 默认值为 null 未标注
- **建议**：补充"默认不启用，需手动管理存取"的说明
- **来源**：Gemini 外部 review

## [External Review] 7.8 RecyclerView 深度优化 — 2026-04-25
- **类型**：数据支撑
- **位置**：DiffUtil
- **问题**：O(N+D²) 复杂度未解释 D 含义
- **建议**：补充 D 代表编辑距离的说明
- **来源**：Gemini 外部 review

## [External Review] 7.9 感官流畅性 — 2026-04-25
- **类型**：配图建议
- **位置**：Perfetto FrameTimeline 部分
- **问题**：缺少 8ms/9ms 交替导致位移波动的示意图
- **建议**：补充步幅波动示意图
- **来源**：Gemini 外部 review

## [External Review] 7.10 图片与 Bitmap 性能 — 2026-04-25
- **类型**：原理链完整性
- **位置**：Hardware Bitmap fd 监控
- **问题**：Glide fd 检查机制描述不够具体
- **建议**：补充每50次解码检查一次 /proc/self/fd，阈值700-800
- **来源**：Gemini 外部 review

## [External Review] 7.11 WebView 性能 — 2026-04-25
- **类型**：版本差异
- **位置**：Android 11 内存优化
- **问题**：未解释 Android 11 为何能在低端设备跑多进程
- **建议**：补充 Memory-aware sandboxing 动态调整子进程优先级
- **来源**：Gemini 外部 review

## [External Review] 7.12 View 布局优化 — 2026-04-25
- **类型**：原理链
- **位置**：requestLayout 触发流程
- **问题**：同步屏障机制说明不够深入
- **建议**：补充 postSyncBarrier 拦截同步消息、仅允许异步消息通过的机制
- **来源**：Gemini 外部 review

## [External Review] 7.13 SystemUI 性能 — 2026-04-25
- **类型**：知识盲区
- **位置**：Flexiglass 与窗口系统
- **问题**：未说明 Flexiglass 在 WindowManager 层面的窗口数量变化
- **建议**：补充说明仍为单一 Surface 以保证手势连续性
- **来源**：Gemini 外部 review

## [External Review] 7.15 作战手册 — 2026-04-25
- **类型**：工具应用
- **位置**：ANR 部分
- **问题**：仅列出 ApplicationExitInfo 和 traces.txt
- **建议**：补充 Perfetto Thread State 和 Blocked on Binder SQL 查询技巧
- **来源**：Gemini 外部 review

## [External Review] 8.2 App 启动全流程 — 2026-04-25
- **类型**：原理链
- **位置**：ApplicationStartInfo
- **问题**：ContentProvider 触发启动时计时起点追溯未说明
- **建议**：补充 REASON_CONTENT_PROVIDER 场景下 ActivityMetricsLogger 的计时起点
- **来源**：Gemini 外部 review

## [External Review] 8.5-8.6 案例集与协程 — 2026-04-25
- **类型**：知识盲区
- **位置**：调试工具
- **问题**：未提及 Android Studio Coroutine Debugger 通过 JDWP 不需要 DebugProbes
- **建议**：补充系统级协程观测方案
- **来源**：Gemini 外部 review
**external. 13.03**
- - [P2][操作效率][快捷键]：建议补充 **`V` 键（垂直参考线）**。在对齐跨进程（App -> SF -> HWC）的时间点时，该快捷键是绝对的效率神器。

**external. 13.03**
- - [P2][技术更新][SQL]：提及新版 Perfetto SQL 已支持 `self_dur` 字段，减少手动计算负担。

**external. 13.05**
- - [P2][原理链][13.5.3] 建议在 Binder 抓取配置中显式加上 `atrace_categories: "aidl"`。虽然 `ftrace` 能拿到事务，但只有开启了 `aidl` 类别，`android_binder_txns` 视图中的 `aidl_name` 字段才会有值。

**external. 13.09**
- - **[P2][知识盲区][用户空间 Trace tag 底层实现]**

**external. 13.09**
- - **原文问题**：只提到了 `B` (Begin) 和 `E` (End) 格式。

**external. 13.09**
- - **证据或观察依据**：`atrace.cpp` 和 `libcutils/Trace.cpp` 广泛使用 `C` (Counter) 格式。

**external. 13.09**
- - **问题描述**：基础设施章节应覆盖 `trace_marker` 的完整常用协议。

**external. 13.09**
- - **建议**：补充 `C|<pid>|<name>|<value>` 格式说明，因为 Counter 也是 Perfetto 中非常重要的数据维度。

**external. 13.09**
- - **[P2][原理链完整性][atrace 的分类机制]**

**external. 13.09**
- - **原文问题**：`atrace gfx` → 主线实现里至少启用 `ATRACE_TAG_GRAPHICS`。

**external. 13.09**
- - **证据或观察依据**：`atrace.cpp` 中的 `k_categories` 和 `k_ftraceEventMap`。

**external. 13.09**
- - **问题描述**：`atrace` 的 category 不仅仅对应用户态 tag，通常还联动特定的 ftrace events。

**external. 13.09**
- - **建议**：明确指出 `gfx` 除了 tag，还会联动如 `events/gpu_mem/gpu_mem_total/enable`（如果存在）或特定的 vendor ftrace points。

**external. 13.09**
- - **问题类型**：原理缺失

**external. 13.09**
- - **位置**：用户空间 Trace tag 的底层实现

**external. 13.09**
- - **问题描述**：缺失 `trace_marker` 的 Counter (C) 格式。

**external. 13.09**
- - **建议**：增加对 Counter 格式的简要说明。

**external. 14.01**
- - [P2][知识盲区][Memory Profiler]

**external. 14.01**
- - **原文问题**：未明确指出 `profileable` 模式在内存分析中的局限性。

**external. 14.01**
- - **证据依据**：官方文档显示，`profileable` 模式不支持 Java 堆转储（Heap Dump）和对象分配跟踪（Allocation Tracking）。

**external. 14.01**
- - **建议**：在“各 Profiler 模式的性能开销与适用场景”或 Memory Profiler 章节中增加说明：如果需要 Heap Dump 来排查 Java 泄露，目前仍需 `debuggable` 模式或通过特定手段（如使用 `am dumpheap`）绕过。

**external. 14.01**
- - **问题类型**：补充说明

**external. 14.01**
- - **位置**：`profileable` 与 `debuggable` 对比

**external. 14.01**
- - **问题描述**：提到“28% 性能提升”时，可以简单备注出处为社区性能评测数据，增加可信度。

**external. 14.03**
- - [P2][知识盲区][showmap 章节]

**external. 14.03**
- - **问题描述**：未提及 `showmap` 对 `profileable` 应用的限制。

**external. 14.03**
- - **建议**：补充说明在非 root 设备上，即便应用是 `profileable`，`adb shell showmap <pid>` 依然可能因为权限无法读取 `/proc/<pid>/smaps`，此时 heapprofd 是更好的选择。

**external. 14.05**
- - [P2][原理链完整性][ArgoAPM]

**external. 14.05**
- - **问题描述**：指令提到的 ArgoAPM (饿了么) 已多年不维护。

**external. 14.05**
- - **建议**：如果要在文中提及此类库，建议改提 **ArgusAPM** (360) 或明确标注 ArgoAPM 为历史参考。

**external. 14.05**
- - **问题描述**：缺失 BlockCanary 等历史纵深。

**external. 14.05**
- - **建议**：在“演进”小节增加 BlockCanary 作为 Looper 监控的起源说明。

**external. 14.06**
- - [P2][原理链完整性][Espresso 同步机制影响]

**external. 14.06**
- - **原文问题**：提到 Espresso 不适合性能测量。

**external. 14.06**
- - **建议**：进一步明确指出 Espresso 的 `IdlingResource` 机制会导致 UI 线程“被动等待”，从而掩盖了真实的竞争和耗时情况。

**external. 14.09**
- - **[P2][原理链完整性][HAL 3.5 requestStreamBuffers 同步阻塞]**

**external. 14.09**
- - **建议**：强调此 API 的同步阻塞特性，建议在专用高优先级线程预取，避免 Request 下发抖动。

**external. 14.11**
- - **[P2][版本差异][Android 14 权限与缓冲区]**

**external. 14.11**
- - **原文问题**：提到了断开 USB，但未细化 Android 14 的权限收紧。

**external. 14.11**
- - **建议描述**：Android 14+ 访问详细电池统计需手动执行 `adb shell pm grant <pkg> android.permission.BATTERY_STATS`。同时，History Buffer 默认仅 256KB，开启全量记录后溢出极快。

**external. 14.12**
- - **[P2][原理链完整性] Measure 工具说明**

**external. 14.12**
- - **问题**：`Measure` 作为一个新兴开源项目（measure-sh），其知名度远低于 Sentry/Bugly，建议补充其适用场景（如：寻求 Firebase 替代方案的开源可观测性方案）。

**external. 14.13**
- - **[P2][原理链完整性][icache 刷新的硬件背景]**

**external. 14.13**
- - **建议描述**：补充说明 ARM64 架构下 icache 和 dcache 的**非一致性**原因，即 CPU 预取指令的流水线不会自动感应数据总线的写入，从而必须显式 flush。

**external. 07.04**
- - [P2][原理链完整性][§5.2 多任务切换]

**external. 07.04**
- - **原文问题**：提到 TaskSnapshot 使用 HardwareBuffer 传递。

**external. 07.04**
- - **证据或观察依据**：Android 8+ 引入 `HardwareBuffer` (native `AHardwareBuffer`) 替代共享内存处理跨进程图像传输，减少了拷贝开销。

**external. 07.04**
- - **建议**：在提到缩略图加载时，简要点出 `HardwareBuffer` 如何通过 Zero-copy 提升 Recents 列表滑动的流畅度。

**external. 07.05**
- - [P2][原理链完整性][§Compose 优化]

**external. 07.05**
- - **原文问题**：提到了 BOM 2025.12.00。

**external. 07.05**
- - **证据或观察依据**：该版本确实是目前的最前沿版本，包含了强跳过模式（Strong Skipping）的正式优化。

**external. 07.05**
- - **建议**：补充 `Strong Skipping` 模式如何减少对 `Stable` 标记的依赖，这是 2025 年 Compose 优化的重要里程碑。

**external. 07.07**
- - [P2][原理链][SnapshotStateObserver]

**external. 07.07**
- - **建议**：补充 `SnapshotStateObserver` 如何通过 `registerApplyObserver` 实现“状态变化 -> Scope 失效”的映射逻辑。

**external. 07.08**
- - [P2][原理链][ViewHolder 缓存] 原文提到 `ViewCacheExtension` 在 Pool 之前查询，建议明确标注该扩展层默认值为 `null`，且开发者需手动管理存取，以防读者误以为设置后系统会自动处理。

**external. 07.08**
- - [P2][数据支撑][DiffUtil] 原文标注复杂度为 $O(N + D^2)$，虽然这是 Android 官方文档的精准表述，但建议补充说明 $D$ 代表编辑距离，以便算法背景较弱的读者理解。

**external. 07.08**
- - [7.8][ViewCacheExtension] 在描述查找顺序时，补充“默认不启用”的说明。

**external. 07.09**
- - [P2][数据支撑][Perfetto] 建议在“路径二：用 FrameTimeline 判断”部分，补充一个关于 `Expected Timeline` 为绿色而 `Actual Timeline` 也是绿色但画面依然“抖动”的逻辑链闭环描述。

**external. 07.09**
- - [7.9][配图建议] 建议补充一张 8ms/9ms 交替导致位移波动的示意图。

**external. 07.12**
- - [P2][知识盲区][requestLayout() 触发的完整流程]

**external. 07.12**
- - **问题描述**：虽然提到了同步屏障（Sync Barrier），但未深入解释它是如何通过 `MessageQueue` 确保 UI 消息优先于普通 Handler 消息的。

**external. 07.12**
- - **建议**：补充 1-2 句关于 `postSyncBarrier` 拦截同步消息、仅允许异步消息（如 TraversalRunnable）通过的机制说明，帮助读者建立“UI 优先级”的深度模型。

**external. 07.13**
- - [P2][知识盲区][Flexiglass 与窗口系统]

**external. 07.13**
- - **问题描述**：原文详尽描述了 Flexiglass 的 Compose 化，但未说明它在 `WindowManager` 层面的窗口数量变化。

**external. 07.13**
- - **证据依据**：Flexiglass 旨在将 UI 逻辑场景化，但在 SurfaceFlinger 层面，它通常仍运行在 `NotificationShade` 对应的单一超大窗口中。

**external. 07.13**
- - **建议**：补充说明 Flexiglass 虽然在 UI 逻辑上实现了“解耦”，但在窗口管理层面仍遵循单一层级以确保手势连续性。

**external. 08**
- - **[P2][知识盲区][06-coroutine-performance.md][调试工具段落]**

**external. 08**
- - **问题描述**：对 `kotlinx-coroutines-debug` 的限制描述准确，但建议补充 Android 16+ 引入的系统级协程观测方案。

**external. 08**
- - **建议**：补充提及 Android Studio 的 "Coroutine Debugger" 是通过 JDWP 协议直接扫描堆栈的，不需要手机端安装 `DebugProbes`。

**external. 08**
- - **章节**：`06-coroutine-performance.md`

**external. 08**
- - **关键源码路径**：`kotlinx-coroutines-core/jvm/src/scheduling/CoroutineScheduler.kt`

**external. 08**
- - **关键结论**：Kotlin 2.2 优化的核心在于 `CoroutineScheduler` 中的 `local queue` 窃取算法从单向环形队列优化为双端优先级队列。

**external. 08**
- ## 十、下一候选章节

**external. 08**
- - `src/part2-performance/ch09-ui-smoothness/01-rendering-pipeline.md`

**external. 08**
- ## 十一、落盘信息

**external. 08**
- - 已写入文件：`/Users/chris/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki/logs/external-review/2026-04-25-15-ch08.[05-06]-external-review.md`

**external. 08**
- - [P2][数据/案例支撑][Thermal 关联策略]

**external. 08**
- - **建议内容**：建议明确给出 `getThermalHeadroom`（预测性）与 `getCpuHeadroom`（即时性）的组合策略建议。

**external. 08**
- - **理由**：帮助读者理解何时该看热，何时该看调度压力。

**external. 08**
- - **章节**：`README.md`

**external. 08**
- - **问题类型**：结构建议

**external. 08**
- - **位置**：阅读建议部分

**external. 08**
- - **问题描述**：可以更明确地引导游戏开发者关注“输入响应（Input Latency）”与“Game Activity”的关联。

**external. 08**
- - **建议**：在阅读建议中增加一行：“如果是游戏开发者关注输入延迟，请参考 8.9”。

**external. 09**
- - [P2][知识盲区][src/part2-performance/ch09-anr/05-case-studies.md]

**external. 09**
- - **原文内容**：提到的反射修复 `QueuedWork` 方案。

**external. 09**
- - **建议**：应补充说明 Android 12+ 后由于 Hidden API 限制，此类反射需配合内卷（元反射）或特定策略，且 Google 已在 `Modern Broadcast Queue` 中优化了此类排队逻辑。

**external. 09**
- - **关键源码路径**：`frameworks/native/libs/binder/ProcessState.cpp` (Binder 线程池上限)。

**external. 09**
- - **核心机制**：Input ANR 的 5s 检测是在 `inputflinger` 的 `InputDispatcher.cpp` 中通过 `processAnrsLocked` 驱动的。

**external. 09**
- - **版本锚点**：`POST_NOTIFICATIONS` 权限分界线是 Android 13。

**external. 09**
- - `src/part2-performance/ch10-memory/`

**external. 09**
- - 已写入文件：`logs/external-review/2026-04-25-15-ch09.[05-README]-external-review.md`

**external. 10**
- - **[P2][交叉引用][README.md] 目录索引不匹配**

**external. 10**
- - **原文问题**：README 列出的子章节为“App 内存分析、内存泄漏、内存持续增长...”，但对应的文件名为 `05-case-studies.md` 等。

**external. 10**
- - **建议**：确保 README 的列表与 `01-04` 缺失章节的占位或实际文件名保持一致。

**external. 10**
- - **[P2][知识盲区][07-sqlite-room-performance.md] WAL 模式下的 F2FS 写入放大**

**external. 10**
- - **建议**：补充提及在现代 Android 手机普遍使用的 F2FS 文件系统下，WAL 模式可能带来的微小写入放大效应，以及对闪存寿命/性能的极小影响，提升深度。

## [Task9 Deep Review] 18.7 TextureView 合成链路 — 2026-04-25
- **类型**：数据缺失/边界说明
- **位置**：L170-L174 / L190
- **问题**：内存对比把 SurfaceView 写成“只需要 Producer Buffer（1x）”，但 App 主窗口 Buffer 在 SurfaceView 场景仍然存在；准确差异是 TextureView 还要把 Producer 内容采样进 App Window 合成结果，独立内容也失去直接 Overlay 机会。“SurfaceView 不受主线程影响”也应限定为内容生产/提交相对独立，View 树位置、生命周期和宿主 UI 仍受主线程约束。
- **建议**：把“2 倍”改成带条件的估算，补分辨率、像素格式、buffer count 与是否已有 App Window Buffer 的基线；表格中把 SurfaceView 主线程影响改为“内容帧相对独立，宿主 View 变更仍受影响”。

## [External Review] 07.06 — 2026-04-25
- **类型**：外部建议
- **位置**：07.06
- **问题**：[P2][数据支撑][案例一]
- **来源**：外部 AI review (2026-04-25-15-ch07.06-external-review.md)

## [External Review] 07.10 — 2026-04-25
- **类型**：外部建议
- **位置**：07.10
- **问题**：[P2][原理链完整性][Hardware Bitmap fd 监控]
- **来源**：外部 AI review (2026-04-25-15-ch07.10-external-review.md)

## [External Review] 07.11 — 2026-04-25
- **类型**：外部建议
- **位置**：07.11
- **问题**：[P2][版本差异][Android 11 内存优化]
- **来源**：外部 AI review (2026-04-25-15-ch07.11-external-review.md)

## [External Review] 07.15 — 2026-04-25
- **类型**：外部建议
- **位置**：07.15
- **问题**：[P2][工具应用][ANR]
- **来源**：外部 AI review (2026-04-25-15-ch07.15-external-review.md)

## [External Review] 08.02 — 2026-04-25
- **类型**：外部建议
- **位置**：08.02
- **问题**：**[P2][原理链/源码锚点][ActivityMetricsLogger]**
- **来源**：外部 AI review (2026-04-25-15-ch08.02-external-review.md)

## [External Review] 10.02 — 2026-04-25
- **类型**：外部建议
- **位置**：10.02
- **问题**：**[P2][知识盲区][原因分析] ApplicationExitInfo 深度分析**
- **来源**：外部 AI review (2026-04-25-15-ch10.02-external-review.md)

## [External Review] 10.04 — 2026-04-25
- **类型**：外部建议
- **位置**：10.04
- **问题**：**[P2][版本差异][ZRAM 调优]**
- **来源**：外部 AI review (2026-04-25-15-ch10.04-external-review.md)

## [External Review] 18.06 — 2026-04-25
- **类型**：外部建议
- **位置**：18.06
- **问题**：**[P2][原理改进]** 建议补充 `BufferStateLayer` 的角色，解释 BLAST 事务如何让宿主 Window 的透明矩形与独立 Surface 同步。
- **来源**：外部 AI review (2026-04-25-15-ch18.[06-10]-external-review.md)

## [Task9 Deep Review] 10.4 低内存对系统性能的影响 — 2026-04-25
- **类型**：数据缺失
- **位置**：L211
- **问题**：低内存 Perfetto 图仍是占位，缺少实际 trace 片段或可复现 TraceConfig。
- **建议**：补一段可复现 trace：mem.mm_events、linux.ftrace mm_vmscan_*、sched、process_stats/psi、lmkd 事件，并标出 kswapd、direct reclaim、GC、lmk 的时间关系。

## [Task9 Deep Review] 10.5 案例集 — 2026-04-25
- **类型**：数据缺失
- **位置**：L96-L100 / L209 / L231 / L285
- **问题**：三处图示与两个效果百分比仍为占位，案例集要求“修复方案与量化效果”，当前证据链没有闭合。
- **建议**：补原始 trace/堆栈截图或删除图占位；renderD128 与 MemoryThrashing 的效果若无公开数值，应改成“回落至基线/明显下降（来源未给百分比）”，不要保留待补充百分比。

## [Task9 Deep Review] 10.6 内存抖动与频繁 GC — 2026-04-25
- **类型**：数据缺失
- **位置**：L127 / L272
- **问题**：Memory Churn 与 GC Event/Heap Track 图仍是占位。章节技术结论已可成立，但观测路径缺少实际截图或 trace 配置。
- **建议**：补 Perfetto trace 配置与截图：android.java_hprof 或 android.heapprofd、art/gc slices、Java Heap track、sched；标出分配峰值、GC 事件和帧耗时尖峰的同一时间窗。

## [External Review] 11 19.11 — 2026-04-25
- **type**: 原理链完整性
- **location**: 
- **description**: [原理链完整性][JankStatsApi16Impl 降级方案]
- **suggestion**: 
- **来源**: external-review

## [External Review] 11 19.11 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: 提到 API 16-23 使用“较粗的帧时间估算”。
- **suggestion**: 
- **来源**: external-review

## [External Review] 11 19.11 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议：补充说明其底层是基于 `Choreographer.FrameCallback` 和 `ViewTreeObserver.OnPreDrawListener` 来模拟计算的，相比 `FrameMetrics` 缺少了渲染线程和 GPU 的真实反馈，因此在低版本上该数据不包含 GPU 耗时。
- **suggestion**: 补充说明其底层是基于 `Choreographer.FrameCallback` 和 `ViewTreeObserver.OnPreDrawListener` 来模拟计算的，相比 `FrameMetrics` 缺少了渲染线程和 GPU 的真实反馈，因此在低版本上该数据不包含 GPU 耗时。
- **来源**: external-review

## [External Review] 12 19.12 — 2026-04-25
- **type**: 原理链完整性
- **location**: 
- **description**: [原理链完整性][SYNC_DURATION 的深层含义]
- **suggestion**: 
- **来源**: external-review

## [External Review] 12 19.12 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议：补充说明 `SYNC_DURATION` 不仅包含 DisplayList 同步，还包含“等待前一帧 GPU 完成以腾出 Buffer”的时间。如果 GPU 负载极高导致 Buffer 阻塞，该值会显著升高。
- **suggestion**: 补充说明 `SYNC_DURATION` 不仅包含 DisplayList 同步，还包含“等待前一帧 GPU 完成以腾出 Buffer”的时间。如果 GPU 负载极高导致 Buffer 阻塞，该值会显著升高。
- **来源**: external-review

## [External Review] 13 19.13 — 2026-04-25
- **type**: 数据支撑
- **location**: 
- **description**: [数据支撑][Trace 缓冲区溢出]
- **suggestion**: 
- **来源**: external-review

## [External Review] 13 19.13 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: 未提及 App Trace 写入太快会导致系统缓冲区溢出。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13 19.13 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议：提醒开发者如果开启了 `forceEnableAppTracing` 并大量打标，需要增大 Perfetto 的缓冲区大小，否则会导致 trace 断片。
- **suggestion**: 提醒开发者如果开启了 `forceEnableAppTracing` 并大量打标，需要增大 Perfetto 的缓冲区大小，否则会导致 trace 断片。
- **来源**: external-review

## [External Review] 13.1 13.1 — 2026-04-25
- **type**: 知识盲区
- **location**: 
- **description**: [知识盲区][核心概念 - Shared Memory]
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.1 13.1 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: 提到了 Shared Memory，但没讲清它的底层实现（匿名共享内存 vs memfd）。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.1 13.1 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 证据或观察依据：Perfetto 源码 `src/base/unix_shared_memory.cc`。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.1 13.1 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: Android 9+ 优先使用 `memfd_create`，这在安全和开销上与传统的 `ashmem` 不同。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.1 13.1 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议：在解释“低开销写入”时，顺带提一句“基于 memfd 的匿名共享内存”，增加技术深度。
- **suggestion**: 在解释“低开销写入”时，顺带提一句“基于 memfd 的匿名共享内存”，增加技术深度。
- **来源**: external-review

## [External Review] 13.10 13.10 — 2026-04-25
- **type**: 版本差异覆盖
- **location**: 
- **description**: [版本差异覆盖][Java Heap 相关 Counter 名称]
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.10 13.10 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: 查询 Java Heap 时提到了几种名称匹配方式。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.10 13.10 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 证据或观察依据：在 Android 13+ 的某些版本中，`process_stats` 数据源上报的 heap 字段名可能变为 `mem.java_heap.size_kb`。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.10 13.10 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: 如果读者直接使用固定字符串查询，可能会返回空结果。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.10 13.10 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议：在 SQL 示例中优先展示“查看可用 counter”的查询，教读者“授人以渔”。
- **suggestion**: 在 SQL 示例中优先展示“查看可用 counter”的查询，教读者“授人以渔”。
- **来源**: external-review

## [External Review] 13.2 13.2 — 2026-04-25
- **type**: 知识盲区
- **location**: 
- **description**: [知识盲区][atrace Categories - binder_driver]
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.2 13.2 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: 提到了 `binder_driver`，但没说明它对内核版本或 `CONFIG_BINDERFS` 的依赖。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.2 13.2 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 证据或观察依据：Android 10+ 引入 binderfs，其 ftrace 挂载点发生了变化。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.2 13.2 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: 部分旧内核设备可能不支持某些 binder 事件。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.2 13.2 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议：在分类表里注上一句“取决于内核是否开启相应 ftrace event”。
- **suggestion**: 在分类表里注上一句“取决于内核是否开启相应 ftrace event”。
- **来源**: external-review

## [External Review] 13.3 13.3 — 2026-04-25
- **type**: 知识盲区
- **location**: 
- **description**: [知识盲区][颜色编码 - 锁竞争红色标记]
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.3 13.3 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: 提到了红色代表锁竞争，但没说明 Perfetto 如何区分“正常的互斥等待”和“严重的优先级翻转”。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.3 13.3 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 证据或观察依据：Perfetto 详情面板中的 `waking_thread` 和 `owner` 信息。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.3 13.3 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: 读者可能只看到红色就紧张，但需要教他们通过 `owner` 轨迹判断这是否属于关键路径阻塞。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.3 13.3 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议：在“实战示例”部分增加一句话，引导读者点击红色 slice 查看 `owner`。
- **suggestion**: 在“实战示例”部分增加一句话，引导读者点击红色 slice 查看 `owner`。
- **来源**: external-review

## [External Review] 13.4 13.4 — 2026-04-25
- **type**: 知识盲区
- **location**: 
- **description**: [知识盲区][Python API - as_pandas_dataframe]
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.4 13.4 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: 推荐使用 `as_pandas_dataframe()`。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.4 13.4 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 证据或观察依据：在处理 GB 级 Trace 且查询结果集巨大时，一次性转为 DataFrame 会导致 Python 进程 OOM。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.4 13.4 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: 未提及大数据量下的分批处理或迭代器模式的优势。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.4 13.4 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议：增加一句话提醒：如果查询结果达到百万行级，应优先使用迭代器模式处理。
- **suggestion**: 增加一句话提醒：如果查询结果达到百万行级，应优先使用迭代器模式处理。
- **来源**: external-review

## [External Review] 13.5 13.5 — 2026-04-25
- **type**: 知识盲区
- **location**: 
- **description**: [知识盲区][Binder 专题 - aidl_name 为空]
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.5 13.5 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: 提到了 `aidl_name`。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.5 13.5 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 证据或观察依据：`android_binder_txns` 模块依赖 trace 中存在 `AIDL::DoSomething` 形式的 slice。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.5 13.5 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: 如果用户采集时没有在 `atrace_apps` 中指定包名，或 App 没有打对应的 trace 点，`aidl_name` 会为空。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.5 13.5 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议：在 SQL 示例后增加说明，告知读者 `aidl_name` 缺失时的 fallback 方案（依靠 tid 和 timestamp）。
- **suggestion**: 在 SQL 示例后增加说明，告知读者 `aidl_name` 缺失时的 fallback 方案（依靠 tid 和 timestamp）。
- **来源**: external-review

## [External Review] 13.6 13.6 — 2026-04-25
- **type**: 源码准确性
- **location**: 
- **description**: [源码准确性][Block Reason - 内核支持检查]
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.6 13.6 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: 提到了 `sched_blocked_reason` 需要内核补丁。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.6 13.6 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 证据或观察依据：并非所有 Android 10+ 设备的内核都回填了此 tracepoint。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.6 13.6 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: 读者可能因为找不到 Block Reason 而困惑。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.6 13.6 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议：补充 adb 命令 `adb shell "ls /sys/kernel/debug/tracing/events/sched/sched_blocked_reason"` 作为验证手段。
- **suggestion**: 补充 adb 命令 `adb shell "ls /sys/kernel/debug/tracing/events/sched/sched_blocked_reason"` 作为验证手段。
- **来源**: external-review

## [External Review] 13.7 13.7 — 2026-04-25
- **type**: 源码准确性
- **location**: 
- **description**: [源码准确性][Trace Summarization - 字段别名]
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.7 13.7 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: `spec.textproto` 示例中的字段名。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.7 13.7 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 证据或观察依据：新版总结 API 对聚合算子（如 `DURATION_WEIGHTED_MEAN`）的输出字段名有特定的默认映射规则。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.7 13.7 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: 如果读者自定义了 `result_column_name` 但 SQL 模块内部没对应上，会导致抽取失败。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.7 13.7 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议：增加一句话提醒读者检查 stdlib 模块的导出列名。
- **suggestion**: 增加一句话提醒读者检查 stdlib 模块的导出列名。
- **来源**: external-review

## [External Review] 13.8 13.8 — 2026-04-25
- **type**: 知识盲区
- **location**: 
- **description**: [知识盲区][ Choroegrapher 与 Input 的时序关联 - 预测输入]
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.8 13.8 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: 提到了 `frame_id` 关联。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.8 13.8 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 证据或观察依据：Android 输入系统支持 `Predictive Back` 和 `Resampled Motion Events`。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.8 13.8 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: 如果开启了输入采样（Resampling），一个渲染帧可能对应多个原始输入采样点，`android_input_events` 的一行可能不代表一个完整的物理采样。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.8 13.8 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议：在解释 `frame_id` 时，注上一句“如果开启了事件重采样，关联关系会变得复杂”。
- **suggestion**: 在解释 `frame_id` 时，注上一句“如果开启了事件重采样，关联关系会变得复杂”。
- **来源**: external-review

## [External Review] 13.9 13.9 — 2026-04-25
- **type**: 版本差异覆盖
- **location**: 
- **description**: [版本差异覆盖][tracefs 路径演进]
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.9 13.9 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: 提到了 `/sys/kernel/tracing`。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.9 13.9 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 证据或观察依据：在某些 Android 11 以下或旧内核（< 4.14）的设备上，该路径可能不存在，只能访问 `/sys/kernel/debug/tracing`。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.9 13.9 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: 如果读者在旧设备上排查问题，可能会找不到目录。
- **suggestion**: 
- **来源**: external-review

## [External Review] 13.9 13.9 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议：在路径列表后注上一句“旧内核（如 Linux 3.18/4.4）可能仅挂载在 debugfs 下”。
- **suggestion**: 在路径列表后注上一句“旧内核（如 Linux 3.18/4.4）可能仅挂载在 debugfs 下”。
- **来源**: external-review

## [External Review] 15.1  — 2026-04-25
- **description**: 问题类型：建议改进
- **来源**: external-review

## [External Review] 15.1  — 2026-04-25
- **description**: 位置：正文
- **来源**: external-review

## [External Review] 15.1  — 2026-04-25
- **description**: 问题描述：建议增加更多实战中的 Trace 观察点描述。
- **来源**: external-review

## [External Review] 15.1  — 2026-04-25
- **type**: 原理链完整性
- **location**: 
- **description**: [原理链完整性][正文]
- **suggestion**: 
- **来源**: external-review

## [External Review] 15.1  — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议补充更具体的 Perfetto Trace 截图占位符，引导读者对应源码行为。
- **suggestion**: 
- **来源**: external-review

## [External Review] 15.10  — 2026-04-25
- **description**: 章节：15.10
- **来源**: external-review

## [External Review] 15.10  — 2026-04-25
- **description**: 问题类型：建议改进
- **来源**: external-review

## [External Review] 15.10  — 2026-04-25
- **description**: 位置：正文
- **来源**: external-review

## [External Review] 15.10  — 2026-04-25
- **description**: 问题描述：建议增加更多实战中的 Trace 观察点描述。
- **来源**: external-review

## [External Review] 15.10  — 2026-04-25
- **type**: 原理链完整性
- **location**: 
- **description**: [原理链完整性][正文]
- **suggestion**: 
- **来源**: external-review

## [External Review] 15.10  — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议补充更具体的 Perfetto Trace 截图占位符，引导读者对应源码行为。
- **suggestion**: 
- **来源**: external-review

## [External Review] 15.2  — 2026-04-25
- **description**: 章节：15.2
- **来源**: external-review

## [External Review] 15.2  — 2026-04-25
- **description**: 问题类型：建议改进
- **来源**: external-review

## [External Review] 15.2  — 2026-04-25
- **description**: 位置：正文
- **来源**: external-review

## [External Review] 15.2  — 2026-04-25
- **description**: 问题描述：建议增加更多实战中的 Trace 观察点描述。
- **来源**: external-review

## [External Review] 15.2  — 2026-04-25
- **type**: 原理链完整性
- **location**: 
- **description**: [原理链完整性][正文]
- **suggestion**: 
- **来源**: external-review

## [External Review] 15.2  — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议补充更具体的 Perfetto Trace 截图占位符，引导读者对应源码行为。
- **suggestion**: 
- **来源**: external-review

## [External Review] 15.3  — 2026-04-25
- **description**: 章节：15.3
- **来源**: external-review

## [External Review] 15.3  — 2026-04-25
- **description**: 问题类型：建议改进
- **来源**: external-review

## [External Review] 15.3  — 2026-04-25
- **description**: 位置：正文
- **来源**: external-review

## [External Review] 15.3  — 2026-04-25
- **description**: 问题描述：建议增加更多实战中的 Trace 观察点描述。
- **来源**: external-review

## [External Review] 15.3  — 2026-04-25
- **type**: 原理链完整性
- **location**: 
- **description**: [原理链完整性][正文]
- **suggestion**: 
- **来源**: external-review

## [External Review] 15.3  — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议补充更具体的 Perfetto Trace 截图占位符，引导读者对应源码行为。
- **suggestion**: 
- **来源**: external-review

## [External Review] 15.4  — 2026-04-25
- **description**: 章节：15.4
- **来源**: external-review

## [External Review] 15.4  — 2026-04-25
- **description**: 问题类型：建议改进
- **来源**: external-review

## [External Review] 15.4  — 2026-04-25
- **description**: 位置：正文
- **来源**: external-review

## [External Review] 15.4  — 2026-04-25
- **description**: 问题描述：建议增加更多实战中的 Trace 观察点描述。
- **来源**: external-review

## [External Review] 15.4  — 2026-04-25
- **type**: 原理链完整性
- **location**: 
- **description**: [原理链完整性][正文]
- **suggestion**: 
- **来源**: external-review

## [External Review] 15.4  — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议补充更具体的 Perfetto Trace 截图占位符，引导读者对应源码行为。
- **suggestion**: 
- **来源**: external-review

## [External Review] 15.5  — 2026-04-25
- **description**: 章节：15.5
- **来源**: external-review

## [External Review] 15.5  — 2026-04-25
- **description**: 问题类型：建议改进
- **来源**: external-review

## [External Review] 15.5  — 2026-04-25
- **description**: 位置：正文
- **来源**: external-review

## [External Review] 15.5  — 2026-04-25
- **description**: 问题描述：建议增加更多实战中的 Trace 观察点描述。
- **来源**: external-review

## [External Review] 15.5  — 2026-04-25
- **type**: 原理链完整性
- **location**: 
- **description**: [原理链完整性][正文]
- **suggestion**: 
- **来源**: external-review

## [External Review] 15.5  — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议补充更具体的 Perfetto Trace 截图占位符，引导读者对应源码行为。
- **suggestion**: 
- **来源**: external-review

## [External Review] 15.6  — 2026-04-25
- **description**: 章节：15.6
- **来源**: external-review

## [External Review] 15.6  — 2026-04-25
- **description**: 问题类型：建议改进
- **来源**: external-review

## [External Review] 15.6  — 2026-04-25
- **description**: 位置：正文
- **来源**: external-review

## [External Review] 15.6  — 2026-04-25
- **description**: 问题描述：建议增加更多实战中的 Trace 观察点描述。
- **来源**: external-review

## [External Review] 15.6  — 2026-04-25
- **type**: 原理链完整性
- **location**: 
- **description**: [原理链完整性][正文]
- **suggestion**: 
- **来源**: external-review

## [External Review] 15.6  — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议补充更具体的 Perfetto Trace 截图占位符，引导读者对应源码行为。
- **suggestion**: 
- **来源**: external-review

## [External Review] 15.7  — 2026-04-25
- **description**: 章节：15.7
- **来源**: external-review

## [External Review] 15.7  — 2026-04-25
- **description**: 问题类型：建议改进
- **来源**: external-review

## [External Review] 15.7  — 2026-04-25
- **description**: 位置：正文
- **来源**: external-review

## [External Review] 15.7  — 2026-04-25
- **description**: 问题描述：建议增加更多实战中的 Trace 观察点描述。
- **来源**: external-review

## [External Review] 15.7  — 2026-04-25
- **type**: 原理链完整性
- **location**: 
- **description**: [原理链完整性][正文]
- **suggestion**: 
- **来源**: external-review

## [External Review] 15.7  — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议补充更具体的 Perfetto Trace 截图占位符，引导读者对应源码行为。
- **suggestion**: 
- **来源**: external-review

## [External Review] 15.8  — 2026-04-25
- **description**: 章节：15.8
- **来源**: external-review

## [External Review] 15.8  — 2026-04-25
- **description**: 问题类型：建议改进
- **来源**: external-review

## [External Review] 15.8  — 2026-04-25
- **description**: 位置：正文
- **来源**: external-review

## [External Review] 15.8  — 2026-04-25
- **description**: 问题描述：建议增加更多实战中的 Trace 观察点描述。
- **来源**: external-review

## [External Review] 15.8  — 2026-04-25
- **type**: 原理链完整性
- **location**: 
- **description**: [原理链完整性][正文]
- **suggestion**: 
- **来源**: external-review

## [External Review] 15.8  — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议补充更具体的 Perfetto Trace 截图占位符，引导读者对应源码行为。
- **suggestion**: 
- **来源**: external-review

## [External Review] 15.9  — 2026-04-25
- **description**: 章节：15.9
- **来源**: external-review

## [External Review] 15.9  — 2026-04-25
- **description**: 问题类型：建议改进
- **来源**: external-review

## [External Review] 15.9  — 2026-04-25
- **description**: 位置：正文
- **来源**: external-review

## [External Review] 15.9  — 2026-04-25
- **description**: 问题描述：建议增加更多实战中的 Trace 观察点描述。
- **来源**: external-review

## [External Review] 15.9  — 2026-04-25
- **type**: 原理链完整性
- **location**: 
- **description**: [原理链完整性][正文]
- **suggestion**: 
- **来源**: external-review

## [External Review] 15.9  — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议补充更具体的 Perfetto Trace 截图占位符，引导读者对应源码行为。
- **suggestion**: 
- **来源**: external-review

## [External Review] None  — 2026-04-25
- **description**: 章节：15.README
- **来源**: external-review

## [External Review] None  — 2026-04-25
- **description**: 问题类型：建议改进
- **来源**: external-review

## [External Review] None  — 2026-04-25
- **description**: 位置：正文
- **来源**: external-review

## [External Review] None  — 2026-04-25
- **description**: 问题描述：建议增加更多实战中的 Trace 观察点描述。
- **来源**: external-review

## [External Review] None  — 2026-04-25
- **type**: 原理链完整性
- **location**: 
- **description**: [原理链完整性][正文]
- **suggestion**: 
- **来源**: external-review

## [External Review] None  — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议补充更具体的 Perfetto Trace 截图占位符，引导读者对应源码行为。
- **suggestion**: 
- **来源**: external-review

## [External Review] 19 19.19 — 2026-04-25
- **type**: 原理链完整性
- **location**: 
- **description**: [原理链完整性][热降频识别]
- **suggestion**: 
- **来源**: external-review

## [External Review] 19 19.19 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: PerfDog 是观察热降频的最佳工具。
- **suggestion**: 
- **来源**: external-review

## [External Review] 19 19.19 — 2026-04-25
- **type**: 建议改进
- **location**: 
- **description**: - 建议：补充一个判定模型：如果 `Temperature` 达到临界值且 `CPU/GPU Frequency` 出现断崖式下跌，此时的 FPS 下降应归因为系统调度而非业务逻辑。
- **suggestion**: 补充一个判定模型：如果 `Temperature` 达到临界值且 `CPU/GPU Frequency` 出现断崖式下跌，此时的 FPS 下降应归因为系统调度而非业务逻辑。
- **来源**: external-review

## [Task9 Deep Review] 11.1 Android 功耗模型 — 2026-04-25
- **类型**：数据缺失
- **位置**：L282 / L405
- **问题**：归属流程图和 Battery Historian 截图仍是占位，章节的功耗归属路径已经讲清，但缺少可复核的图或 bugreport 示例。
- **建议**：补一张 BatteryStatsImpl → BatteryUsageStatsProvider → *PowerCalculator → Settings/bugreport 的流程图；再补一个 Battery Historian 或 bugreport 电池摘要样例，标出 CPU、Screen、WakeLock 的归属入口。

## [Task9 Deep Review] 11.2 App 耗电优化 — 2026-04-25
- **类型**：数据缺失
- **位置**：L210 / L271 / L357
- **问题**：后台任务、位置、Alarm 三处观测图仍是占位，读者无法按章节复现 Battery Historian / dumpsys / Perfetto 的取证路径。
- **建议**：补 3 个最小样例：JobScheduler 频繁触发、定位请求过密、精确闹钟穿透 Doze；每个样例给出 bugreport/Battery Historian 行名、辅助 dumpsys 命令和判断条件。

## [Task9 Deep Review] 11.3 系统级功耗优化 — 2026-04-25
- **类型**：数据缺失
- **位置**：L147 / L315
- **问题**：Doze 维护窗口和 Battery Saver 对 CPU/Job 的影响仍是图占位，机制描述缺少一段可复核时间线。
- **建议**：补一段可复现实验：`dumpsys deviceidle step/force-idle`、`settings get global low_power`、`dumpsys jobscheduler` 与 Perfetto `power/cpu_idle`、`power/cpu_frequency`、`sched/*` 对时。

## [Task9 Deep Review] 11.3 系统级功耗优化 — 2026-04-25（Adaptive Battery）
- **类型**：知识盲区/数据支撑
- **位置**：L187
- **问题**：Adaptive Battery 段落保留了“TensorFlow Lite 的 CNN + 前馈网络架构”待验证说法，但 AOSP / 官方文档不公开具体模型结构。继续保留具体网络结构会让读者把未证实实现当成系统事实。
- **建议**：删除具体网络结构猜测，改写为“系统根据 Usage Events、通知交互、前台时长等本地信号预测使用频率，并输出 Standby Bucket 调整”；如果要写 TFLite/CNN，必须补一手来源和版本边界。

## [External Review] ? ch10-memory-perf [05-07, README] — 2026-04-25
- **类型**：交叉引用
- **位置**：ch10-memory-perf [05-07, README]
- **问题**：- **[P2][交叉引用][README.md] 目录索引不匹配**
  - **原文问题**：README 列出的子章节为“App 内存分析、内存泄漏、内存持续增长...”，但对应的文件名为 `05-case-studies.md` 等。
  - **建议**：确保 README 的列表与 `01-04` 缺失章节的占位或实际文件名保持一致。
- **[P2][知识盲区][07-sqlite-
- **建议**：
- **来源**：Gemini 外部 review (2026-04-25-15-10.README-external-review.md)

## [External Review] ? 13.README — 2026-04-25
- **类型**：建议改进
- **位置**：本章内容列表
- **问题**：建议将 13.8 和 13.10 这两个“SQL 重灾区”标记为“进阶分析必读”。
- **建议**：在目录项后增加简单的难度或场景标签。
- **来源**：Gemini 外部 review (2026-04-25-15-13.README-external-review.md)

## [External Review] 14.1 14.1 — 2026-04-25
- **类型**：知识盲区
- **位置**：14.1
- **问题**：建议补充如何通过 `AS_PROFILER_AGENT_MEMORY_LIMIT`（或类似环境变量，需核实）来控制 Agent 开销的说明。
- **建议**：说明在做极致内存测试时，应尽量减少 Profiler 的记录项。
- **来源**：Gemini 外部 review (2026-04-25-15-14.1-external-review.md)

## [External Review] 14.1 14.1 — 2026-04-25
- **类型**：建议改进
- **位置**：Power Profiler
- **问题**：ODPM 的支持机型目前仍集中在 Pixel 系列。
- **建议**：补充说明对于不支持 ODPM 的机型，Power Profiler 会降级到传统的估算模型。
- **来源**：Gemini 外部 review (2026-04-25-15-14.1-external-review.md)

## [External Review] 14.2 14.2 — 2026-04-25
- **类型**：数据/案例支撑
- **位置**：14.2
- **问题**：建议补充如何通过 `simpleperf list` 结果来校准具体事件名称的说明。
- **建议**：在 14.2.4 节增加一段提示，引导读者根据设备实际输出调整命令。
- **来源**：Gemini 外部 review (2026-04-25-15-14.2-external-review.md)

## [External Review] 14.2 14.2 — 2026-04-25
- **类型**：建议改进
- **位置**：off-CPU Profiling
- **问题**：建议补充 `sched_switch` 事件在 simpleperf 内部是如何与采样周期对齐的说明。
- **建议**：简要解释 off-CPU 样本的权重计算逻辑（Time Difference）。
- **来源**：Gemini 外部 review (2026-04-25-15-14.2-external-review.md)

## [External Review] 14.3 14.3 — 2026-04-25
- **类型**：数据/案例支撑
- **位置**：14.3
- **问题**：建议补充一个从 GC Root 到 Activity 实例的节点层级展示图。
- **建议**：提供一个 OQL 查询“查询所有未释放 Activity”的语句示例。
- **来源**：Gemini 外部 review (2026-04-25-15-14.3-external-review.md)

## [External Review] 14.3 14.3 — 2026-04-25
- **类型**：建议改进
- **位置**：MTE 部分
- **问题**：MTE 的 Async 模式在 Android 14+ 已经可以被 App 自定义。
- **建议**：补充说明如何在 `AndroidManifest.xml` 中配置 `android:memtagMode`。
- **来源**：Gemini 外部 review (2026-04-25-15-14.3-external-review.md)

## [External Review] 14.4 14.4 — 2026-04-25
- **类型**：数据/案例支撑
- **位置**：14.4
- **问题**：建议补充一段关于“如何从 Frontend dump 中识别 Layer 遮挡关系”的文字提示。
- **建议**：说明 `Composition list` 的排列顺序通常对应合成层级顺序。
- **来源**：Gemini 外部 review (2026-04-25-15-14.4-external-review.md)

## [External Review] 14.4 14.4 — 2026-04-25
- **类型**：建议改进
- **位置**：gfxinfo 专题
- **问题**：建议增加一个“VRR 场景下 deadline 判定”的数值计算公式。
- **建议**：对比 120Hz 下 `FrameInterval` 的纳秒值与 `FrameDeadline` 的关系。
- **来源**：Gemini 外部 review (2026-04-25-15-14.4-external-review.md)

## [External Review] 14.5 14.5 — 2026-04-25
- **类型**：知识盲区
- **位置**：14.5
- **问题**：建议补充如何通过 `__builtin_clear_cache` 或厂商专有指令来刷新指令缓存的简要说明。
- **建议**：在 14.5.8 节增加一段关于“Inline Hook 稳定性边界”的提示。
- **来源**：Gemini 外部 review (2026-04-25-15-14.5-external-review.md)

## [External Review] 14.5 14.5 — 2026-04-25
- **类型**：建议改进
- **位置**：KOOM 部分
- **问题**：建议补充“Fork 子进程 Dump”在 Android 11+ 之后可能遇到的写写时拷贝（Copy-on-Write）放大问题。
- **建议**：简要说明在大堆（> 4GB）场景下，Fork 可能导致的短暂系统卡顿。
- **来源**：Gemini 外部 review (2026-04-25-15-14.5-external-review.md)

## [External Review] ? ? — 2026-04-25
- **类型**：原理链完整性
- **位置**：?
- **问题**：- [P2][原理链完整性][正文]
- 建议补充更具体的 Perfetto Trace 截图占位符，引导读者对应源码行为。
- **建议**：
- **来源**：Gemini 外部 review (2026-04-25-15-15.README-external-review.md)

## [External Review] ? ? — 2026-04-25
- **类型**：建议改进
- **位置**：正文
- **问题**：建议增加更多实战中的 Trace 观察点描述。
- **建议**：
- **来源**：Gemini 外部 review (2026-04-25-15-15.README-external-review.md)

## [External Review] ? ? — 2026-04-25
- **类型**：数据/案例支撑
- **位置**：?
- **问题**：- [P2][数据/案例支撑][Thermal 关联策略]
- **建议内容**：建议明确给出 `getThermalHeadroom`（预测性）与 `getCpuHeadroom`（即时性）的组合策略建议。
- **理由**：帮助读者理解何时该看热，何时该看调度压力。
- **建议**：
- **来源**：Gemini 外部 review (2026-04-25-15-8.README-external-review.md)

## [External Review] ? ? — 2026-04-25
- **类型**：建议改进
- **位置**：?
- **问题**：- **章节**：`README.md`
- **问题类型**：结构建议
- **位置**：阅读建议部分
- **问题描述**：可以更明确地引导游戏开发者关注“输入响应（Input Latency）”与“Game Activity”的关联。
- **建议**：在阅读建议中增加一行：“如果是游戏开发者关注输入延迟，请参考 8.9”。
- **建议**：
- **来源**：Gemini 外部 review (2026-04-25-15-8.README-external-review.md)

## [External Review] ? ch09 案例集与专项 — 2026-04-25
- **类型**：知识盲区
- **位置**：ch09 案例集与专项
- **问题**：- [P2][知识盲区][src/part2-performance/ch09-anr/05-case-studies.md]
- **原文内容**：提到的反射修复 `QueuedWork` 方案。
- **建议**：应补充说明 Android 12+ 后由于 Hidden API 限制，此类反射需配合内卷（元反射）或特定策略，且 Google 已在 `Modern Broadcast Queue
- **建议**：
- **来源**：Gemini 外部 review (2026-04-25-15-9.README-external-review.md)

## [External Review] ? ch09 案例集与专项 — 2026-04-25
- **类型**：建议改进
- **位置**：ch09 案例集与专项
- **问题**：- **关键源码路径**：`frameworks/native/libs/binder/ProcessState.cpp` (Binder 线程池上限)。
- **核心机制**：Input ANR 的 5s 检测是在 `inputflinger` 的 `InputDispatcher.cpp` 中通过 `processAnrsLocked` 驱动的。
- **版本锚点**：`POST_NOTIFI
- **建议**：
- **来源**：Gemini 外部 review (2026-04-25-15-9.README-external-review.md)

## [External Review] 19.19 19.19 — 2026-04-25
- **类型**：原理链完整性
- **位置**：19.19
- **问题**：- [P2][原理链完整性][热降频识别]
- 描述：PerfDog 是观察热降频的最佳工具。
- 建议：补充一个判定模型：如果 `Temperature` 达到临界值且 `CPU/GPU Frequency` 出现断崖式下跌，此时的 FPS 下降应归因为系统调度而非业务逻辑。

- **建议**：补充一个判定模型：如果 `Temperature` 达到临界值且 `CPU/GPU Frequency` 出现断崖式下跌，此时的 FPS 下降应归因为系统调度而非业务逻辑。
- **来源**：Gemini 外部 review (2026-04-25-15-19-external-review.md)

## [Task9 Deep Review] 7.7 Jetpack Compose 性能优化 — 2026-04-25
- **类型**：数据缺失
- **位置**：L151 / L556
- **问题**：Compose vs View 帧耗时对比、重组驱动动画 vs Draw 阶段动画对比仍是 `[待补充]`，当前结论虽有边界说明，但缺少可复现 trace 或 Macrobenchmark 数据支撑。
- **建议**：补 1 组 `FrameTimingMetric` / Perfetto Trace 样例，至少标明设备、刷新率、Compose 版本、测试场景，并给出 Composition/Layout/Draw 或 FrameTimeline 的观察点。

## [Task9 Deep Review] 7.7 Jetpack Compose 性能优化 — 2026-04-25
- **类型**：待验证
- **位置**：L510
- **问题**：`Compose 1.10 中 ReuseComposeView API 的稳定性` 仍标为待验证。
- **建议**：下一轮补官方 release note / AndroidX 源码锚点；如果 API 仍处实验或不存在稳定入口，改成条件化说明，避免读者按稳定 API 使用。

## [Task9 Deep Review] 7.12 View 体系性能优化 — 2026-04-25
- **类型**：数据缺失
- **位置**：L603
- **问题**：`Layout Inspector V2 使用 View.encode() 而非反射获取属性，dump 速度提升 3-5 倍` 缺少来源或 benchmark 条件，且与前文源码错误位于同一补充段。
- **建议**：补 Android Studio / AOSP 工具侧资料或删除具体倍数，只保留可由 AOSP 验证的 `ViewDebug.dumpv2()` / `View.encode(ViewHierarchyEncoder)` 关系。


## [External Review] 19.14 Macrobenchmark — 2026-04-25
- **类型**：知识盲区
- **位置**：温控降频
- **建议**：补充对 androidx.benchmark.suppressErrors 配置的警示，说明强行跳过温控检查会导致实验结果不可信
- **来源**：Gemini 外部 review

## [External Review] 19.15 Baseline Profile — 2026-04-25
- **类型**：源码准确性
- **位置**：ProfileInstaller 激活
- **建议**：增加混淆与初始化检查锚点，确保 ProfileInstallReceiver 未被混淆
- **来源**：Gemini 外部 review

## [External Review] 19.20 其他工具 — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：Emmagee 定位修正
- **建议**：将 Emmagee 移至附录：历史工具回顾，或在正文中以醒目 Deprecated 标识
- **来源**：Gemini 外部 review

## [Task9 Deep Review] 19.18 商业 APM 平台（Sentry、APMPlus、Bugly） — 2026-04-25
- **类型**：数据缺失
- **位置**：L100 Sentry profiling 排查建议
- **问题**：文中列出 `libart.so`、`art::Trace::StopTracing`、`pthread_getcpuclockid` 等崩溃栈排查路径，但未绑定 Sentry Android SDK 版本、issue 链接或真实事故样本。
- **建议**：补充 Sentry SDK 版本/issue/官方文档锚点；如果来自实践经验，应标成经验性排查清单，并写明适用 Android 版本和采样率范围。

## [Task9 Deep Review] 19.18 商业 APM 平台（Sentry、APMPlus、Bugly） — 2026-04-25
- **类型**：数据缺失
- **位置**：L132/L207 SDK 自身开销验收
- **问题**：已经要求看 SDK crash、ANR、启动开销、线程数、包体积，但没有给出 APM SDK 初始化自监控的具体观测口径。
- **建议**：增加 `apm.sdk.init` / `apm.sdk.first_upload` 等 Trace 名称，要求用 Macrobenchmark 或 Perfetto 对比接入前后启动 P50/P95、主线程耗时、线程数、流量和包体积增量。

## [Task9 Deep Review] 19.20 SoloPi 与 Emmagee — 2026-04-25
- **类型**：源码准确性
- **位置**：L158 SoloPi 启动耗时算法
- **问题**：正文写成 MediaProjection 录屏 + OpenCV 图像相似度/变化率的“典型路径”，但 SoloPi README 只确认双点按钮与广播调用，未给出算法级实现细节。
- **建议**：补 SoloPi 源码锚点或官方 wiki 证明；若无法闭环，把该段改为“视觉首屏/页面稳定口径”，避免把未核验实现写成确定事实。

## [Task9 Deep Review] 19.22 存储 Benchmark（AndroBench、A1 SD Bench） — 2026-04-25
- **类型**：数据缺失
- **位置**：L230-L233 存储报告模板
- **问题**：模板对吞吐量和 IOPS 使用 `median / p95`。这类指标数值越高越好，p95 表示偏高表现，不代表尾部退化；读者可能把它误读成延迟指标的 p95。
- **建议**：吞吐量/IOPS 建议记录 median + p10/min 或稳定轮均值；延迟指标另列 p50/p95/p99。报告中明确“高好/低好”的指标方向。

## [Task9 Deep Review] 19.22 存储 Benchmark（AndroBench、A1 SD Bench） — 2026-04-25
- **类型**：数据支撑
- **位置**：frontmatter sources L18-L20
- **问题**：AndroBench / A1 SD Bench 的来源包含 APKPure 这类第三方镜像，作为版本能力和维护状态依据不够稳。
- **建议**：补充论文、开发者主页、Google Play/官方发布页或项目维护信息；若只能用镜像来源，需标注“第三方镜像，仅用于包名和历史版本线索”。

## [external-review] 14.11 Battery Historian — 2026-04-25
- **类型**：工具建议
- **建议**：社区镜像 Apple Silicon 兼容性说明可更突出 --platform linux/amd64 参数

## [Task9 Deep Review] 12.1 APK 体积优化 — 2026-04-25
- **类型**：数据缺失
- **位置**：L442
- **问题**：Baseline Profile “`.odex` / `.vdex` 新增磁盘占用通常比 DEX 字节码再大 10%-30%”缺少实验环境、设备、ART 编译模式和样本来源。
- **建议**：补一个可复现实验口径：同一 release 包、有/无 baseline profile、固定 Android 版本和 ABI，比较 `/data/app/.../oat`、安装耗时和首启 trace；如果没有数据，先删除百分比。

## [Task9 Deep Review] 12.4 Android 网络安全与 TLS 性能优化 — 2026-04-25
- **类型**：数据缺失
- **位置**：L119 / L230
- **问题**：ECH/HPKE “计算开销很小”“硬件加速处理”“缺少 HPKE 基准”三处没有给出设备、算法 suite、消息大小或来源，容易把协议级判断写成通用性能结论。
- **建议**：补 Android 设备侧 microbenchmark 或官方/Chromium 实测来源；至少区分 X25519/P-256、AES-GCM/ChaCha20-Poly1305、payload 大小和是否命中硬件加速。

## [External Review] 15.10 Performance Governance — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：全文
- **问题**：Android 12+ 演进细节不足 / 缺少具体性能案例数据
- **建议**：适当补充新版本的差异和 benchmark 数据
- **来源**：Gemini 外部 review

## [External Review] 15.10 Performance Governance — 2026-04-25
- **类型**：版本演进
- **位置**：全文
- **问题**：Android 12+ 演进细节不足
- **建议**：适当补充新版本的差异。
- **来源**：Gemini 外部 review

## [External Review] 15.6 Testing Best Practices — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：全文
- **问题**：Android 12+ 演进细节不足 / 缺少具体性能案例数据
- **建议**：适当补充新版本的差异和 benchmark 数据
- **来源**：Gemini 外部 review

## [External Review] 15.6 Testing Best Practices — 2026-04-25
- **类型**：版本演进
- **位置**：全文
- **问题**：Android 12+ 演进细节不足
- **建议**：适当补充新版本的差异。
- **来源**：Gemini 外部 review

## [External Review] 15.7 AOSP Reading — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：全文
- **问题**：Android 12+ 演进细节不足 / 缺少具体性能案例数据
- **建议**：适当补充新版本的差异和 benchmark 数据
- **来源**：Gemini 外部 review

## [External Review] 15.7 AOSP Reading — 2026-04-25
- **类型**：版本演进
- **位置**：全文
- **问题**：Android 12+ 演进细节不足
- **建议**：适当补充新版本的差异。
- **来源**：Gemini 外部 review

## [External Review] 15.8 Empirical Performance Issues — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：全文
- **问题**：Android 12+ 演进细节不足 / 缺少具体性能案例数据
- **建议**：适当补充新版本的差异和 benchmark 数据
- **来源**：Gemini 外部 review

## [External Review] 15.8 Empirical Performance Issues — 2026-04-25
- **类型**：版本演进
- **位置**：全文
- **问题**：Android 12+ 演进细节不足
- **建议**：适当补充新版本的差异。
- **来源**：Gemini 外部 review

## [External Review] 15.9 Observability Closed Loop — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：全文
- **问题**：Android 12+ 演进细节不足 / 缺少具体性能案例数据
- **建议**：适当补充新版本的差异和 benchmark 数据
- **来源**：Gemini 外部 review

## [External Review] 15.9 Observability Closed Loop — 2026-04-25
- **类型**：版本演进
- **位置**：全文
- **问题**：Android 12+ 演进细节不足
- **建议**：适当补充新版本的差异。
- **来源**：Gemini 外部 review

## [External Review] 19.19 PerfDog — 2026-04-25
- **类型**：建议改进
- **位置**：
- **问题**：- [P2]- [P2][原理链完整性][热降频识别]
- 描述：PerfDog 是观察热降频的最佳工具。
- 建议：补充一个判定模型：如果 `Temperature` 达到临界值且 `CPU/GPU Frequency` 出现断崖式下跌，此时的 FPS 下降应归因为系统调度而非业务逻辑。
- **建议**：见 external-review 文件
- **来源**：Gemini 外部 review

## [External Review] 19.1 APM Landscape — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：全文
- **问题**：Android 12+ 演进细节不足 / 缺少具体性能案例数据
- **建议**：适当补充新版本的差异和 benchmark 数据
- **来源**：Gemini 外部 review

## [External Review] 19.1 APM Landscape — 2026-04-25
- **类型**：版本演进
- **位置**：全文
- **问题**：Android 12+ 演进细节不足
- **建议**：适当补充新版本的差异。
- **来源**：Gemini 外部 review

## [External Review] 19.10 Other Open-source APM — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：全文
- **问题**：Android 12+ 演进细节不足 / 缺少具体性能案例数据
- **建议**：适当补充新版本的差异和 benchmark 数据
- **来源**：Gemini 外部 review

## [External Review] 19.10 Other Open-source APM — 2026-04-25
- **类型**：数据/案例支撑
- **位置**：全文
- **问题**：缺乏具体的性能案例数据。
- **建议**：补充真实测试数据或 Trace 截图。
- **来源**：Gemini 外部 review

## [External Review] 19.11 JankStats — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：全文
- **问题**：Android 12+ 演进细节不足 / 缺少具体性能案例数据
- **建议**：适当补充新版本的差异和 benchmark 数据
- **来源**：Gemini 外部 review

## [External Review] 19.11 JankStats — 2026-04-25
- **类型**：数据/案例支撑
- **位置**：全文
- **问题**：缺乏具体的性能案例数据。
- **建议**：补充真实测试数据或 Trace 截图。
- **来源**：Gemini 外部 review

## [External Review] 19.12 FrameMetrics — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：全文
- **问题**：Android 12+ 演进细节不足 / 缺少具体性能案例数据
- **建议**：适当补充新版本的差异和 benchmark 数据
- **来源**：Gemini 外部 review

## [External Review] 19.12 FrameMetrics — 2026-04-25
- **类型**：数据/案例支撑
- **位置**：全文
- **问题**：缺乏具体的性能案例数据。
- **建议**：补充真实测试数据或 Trace 截图。
- **来源**：Gemini 外部 review

## [External Review] 19.13 Tracing SDK — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：全文
- **问题**：Android 12+ 演进细节不足 / 缺少具体性能案例数据
- **建议**：适当补充新版本的差异和 benchmark 数据
- **来源**：Gemini 外部 review

## [External Review] 19.13 Tracing SDK — 2026-04-25
- **类型**：数据/案例支撑
- **位置**：全文
- **问题**：缺乏具体的性能案例数据。
- **建议**：补充真实测试数据或 Trace 截图。
- **来源**：Gemini 外部 review

## [External Review] 19.14 Jetpack Benchmark — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：全文
- **问题**：Android 12+ 演进细节不足 / 缺少具体性能案例数据
- **建议**：适当补充新版本的差异和 benchmark 数据
- **来源**：Gemini 外部 review

## [External Review] 19.14 Jetpack Benchmark — 2026-04-25
- **类型**：数据/案例支撑
- **位置**：全文
- **问题**：缺乏具体的性能案例数据。
- **建议**：补充真实测试数据或 Trace 截图。
- **来源**：Gemini 外部 review

## [External Review] 19.15 Baseline Profiles — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：全文
- **问题**：Android 12+ 演进细节不足 / 缺少具体性能案例数据
- **建议**：适当补充新版本的差异和 benchmark 数据
- **来源**：Gemini 外部 review

## [External Review] 19.15 Baseline Profiles — 2026-04-25
- **类型**：数据/案例支撑
- **位置**：全文
- **问题**：缺乏具体的性能案例数据。
- **建议**：补充真实测试数据或 Trace 截图。
- **来源**：Gemini 外部 review

## [External Review] 19.16 ProfilingManager — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：全文
- **问题**：Android 12+ 演进细节不足 / 缺少具体性能案例数据
- **建议**：适当补充新版本的差异和 benchmark 数据
- **来源**：Gemini 外部 review

## [External Review] 19.16 ProfilingManager — 2026-04-25
- **类型**：数据/案例支撑
- **位置**：全文
- **问题**：缺乏具体的性能案例数据。
- **建议**：补充真实测试数据或 Trace 截图。
- **来源**：Gemini 外部 review

## [External Review] 19.2 Tencent Matrix — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：全文
- **问题**：Android 12+ 演进细节不足 / 缺少具体性能案例数据
- **建议**：适当补充新版本的差异和 benchmark 数据
- **来源**：Gemini 外部 review

## [External Review] 19.2 Tencent Matrix — 2026-04-25
- **类型**：版本演进
- **位置**：全文
- **问题**：Android 12+ 演进细节不足
- **建议**：适当补充新版本的差异。
- **来源**：Gemini 外部 review

## [External Review] 19.3 KOOM — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：全文
- **问题**：Android 12+ 演进细节不足 / 缺少具体性能案例数据
- **建议**：适当补充新版本的差异和 benchmark 数据
- **来源**：Gemini 外部 review

## [External Review] 19.3 KOOM — 2026-04-25
- **类型**：版本演进
- **位置**：全文
- **问题**：Android 12+ 演进细节不足
- **建议**：适当补充新版本的差异。
- **来源**：Gemini 外部 review

## [External Review] 19.4 BTrace — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：全文
- **问题**：Android 12+ 演进细节不足 / 缺少具体性能案例数据
- **建议**：适当补充新版本的差异和 benchmark 数据
- **来源**：Gemini 外部 review

## [External Review] 19.4 BTrace — 2026-04-25
- **类型**：版本演进
- **位置**：全文
- **问题**：Android 12+ 演进细节不足
- **建议**：适当补充新版本的差异。
- **来源**：Gemini 外部 review

## [External Review] 19.5 LeakCanary — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：全文
- **问题**：Android 12+ 演进细节不足 / 缺少具体性能案例数据
- **建议**：适当补充新版本的差异和 benchmark 数据
- **来源**：Gemini 外部 review

## [External Review] 19.5 LeakCanary — 2026-04-25
- **类型**：版本演进
- **位置**：全文
- **问题**：Android 12+ 演进细节不足
- **建议**：适当补充新版本的差异。
- **来源**：Gemini 外部 review

## [External Review] 19.6 BlockCanary — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：全文
- **问题**：Android 12+ 演进细节不足 / 缺少具体性能案例数据
- **建议**：适当补充新版本的差异和 benchmark 数据
- **来源**：Gemini 外部 review

## [External Review] 19.6 BlockCanary — 2026-04-25
- **类型**：数据/案例支撑
- **位置**：全文
- **问题**：缺乏具体的性能案例数据。
- **建议**：补充真实测试数据或 Trace 截图。
- **来源**：Gemini 外部 review

## [External Review] 19.7 DoKit — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：全文
- **问题**：Android 12+ 演进细节不足 / 缺少具体性能案例数据
- **建议**：适当补充新版本的差异和 benchmark 数据
- **来源**：Gemini 外部 review

## [External Review] 19.7 DoKit — 2026-04-25
- **类型**：数据/案例支撑
- **位置**：全文
- **问题**：缺乏具体的性能案例数据。
- **建议**：补充真实测试数据或 Trace 截图。
- **来源**：Gemini 外部 review

## [External Review] 19.8 ArgusAPM — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：全文
- **问题**：Android 12+ 演进细节不足 / 缺少具体性能案例数据
- **建议**：适当补充新版本的差异和 benchmark 数据
- **来源**：Gemini 外部 review

## [External Review] 19.8 ArgusAPM — 2026-04-25
- **类型**：数据/案例支撑
- **位置**：全文
- **问题**：缺乏具体的性能案例数据。
- **建议**：补充真实测试数据或 Trace 截图。
- **来源**：Gemini 外部 review

## [External Review] 19.9 Measure — 2026-04-25
- **类型**：版本差异覆盖
- **位置**：全文
- **问题**：Android 12+ 演进细节不足 / 缺少具体性能案例数据
- **建议**：适当补充新版本的差异和 benchmark 数据
- **来源**：Gemini 外部 review

## [External Review] 19.9 Measure — 2026-04-25
- **类型**：数据/案例支撑
- **位置**：全文
- **问题**：缺乏具体的性能案例数据。
- **建议**：补充真实测试数据或 Trace 截图。
- **来源**：Gemini 外部 review

## [External Review] 8.09 Game Performance — 2026-04-25
- **类型**：改进建议
- **来源**：Gemini 外部 review (2026-04-25-15-8.README-external-review.md)
- **建议**：建议明确 getThermalHeadroom(预测性)与 getCpuHeadroom(即时性)的组合策略

## [External Review] 8.09 Game Performance — 2026-04-25
- **类型**：改进建议
- **来源**：Gemini 外部 review (2026-04-25-15-8.README-external-review.md)
- **建议**：README 阅读建议中增加游戏开发者关注输入延迟与 Game Activity 关联的引导

## [External Review] 9.05 ch09 案例集与专项 — 2026-04-25
- **类型**：改进建议
- **来源**：Gemini 外部 review (2026-04-25-15-9.README-external-review.md)
- **建议**：反射修复 QueuedWork 方案应补充说明 Android 12+ Hidden API 限制及 Modern Broadcast Queue 优化

## [External Review] 10.5 ch10 Memory Perf [05-07, README] — 2026-04-25
- **类型**：改进建议
- **来源**：Gemini 外部 review (2026-04-25-15-10.README-external-review.md)
- **建议**：README 目录索引需与实际文件名(01-04)缺失章节占位保持一致

## [External Review] 10.5 ch10 Memory Perf [05-07, README] — 2026-04-25
- **类型**：改进建议
- **来源**：Gemini 外部 review (2026-04-25-15-10.README-external-review.md)
- **建议**：07-sqlite-room-performance.md 补充 F2FS 下 WAL 模式写入放大说明

## [External Review] 12 APK 与网络性能 — 2026-04-25
- **类型**：改进建议
- **来源**：Gemini 外部 review (2026-04-25-15-12.README-external-review.md)
- **建议**：ANDROID_STRIP_DEBUG_SYMBOLS 在 AGP 8.x 中优先推荐 packaging.jniLibs.keepDebugSymbols DSL 写法

## [External Review] 12 APK 与网络性能 — 2026-04-25
- **类型**：改进建议
- **来源**：Gemini 外部 review (2026-04-25-15-12.README-external-review.md)
- **建议**：网络传输优化补充 Brotli(br)相比 Gzip 额外减少 15-25% 体积的推荐

## [External Review] 13.README Perfetto 章节导航 — 2026-04-25
- **类型**：改进建议
- **来源**：Gemini 外部 review (2026-04-25-15-13.README-external-review.md)
- **建议**：建议在 13.8 和 13.10(SQL 重灾区)目录项后增加难度或场景标签(进阶分析必读)

## [External Review] 15.README 方法论章节 README — 2026-04-25
- **类型**：改进建议
- **来源**：Gemini 外部 review (2026-04-25-15-15.README-external-review.md)
- **建议**：Android 12+ 演进细节不足，适当补充新版本差异

## [External Review] 18.16 渲染管线(Game Engine/VRR/PIP 等) — 2026-04-25
- **类型**：改进建议
- **来源**：Gemini 外部 review (2026-04-25-15-18.README-external-review.md)
- **建议**：Freeform Resize 分析补充 Android 12+ Shell Transition 将窗口管理从 System Server 剥离到 SysUI 的说明

## [External Review] 18.16 渲染管线(Game Engine/VRR/PIP 等) — 2026-04-25
- **类型**：改进建议
- **来源**：Gemini 外部 review (2026-04-25-15-18.README-external-review.md)
- **建议**：dumpsys SurfaceFlinger --latency 在 BLAST 架构下参考价值下降，建议优先推荐 Winscope

## [External Review] 18.16 渲染管线(Game Engine/VRR/PIP 等) — 2026-04-25
- **类型**：改进建议
- **来源**：Gemini 外部 review (2026-04-25-15-18.README-external-review.md)
- **建议**：EyeDropper API 37 需明确指出 secure window 和 protected buffer 像素拦截机制


## [Task9 Deep Review] 1.7 ART 编译管线与 dex2oat 优化 — 2026-04-25
- **类型**：数据缺失
- **位置**：L89 / L173 / L310 / L336 / L452
- **问题**：冷启动差距 30%+、JIT code cache 常见 4MB、Baseline / Startup Profiles 15-30% 或 30%+ 这几组数字仍缺设备、版本、样本与官方出处。正文已标待验证，但发布前仍会削弱技术可信度。
- **建议**：把收益数字集中成一张数据表，至少补官方文档原文、测试设备/Android 版本、样本应用、对照组；不能补齐的数字保留为定性判断。

## [Task9 Deep Review] 1.12 AutoFDO 反馈导向编译优化 — 2026-04-25
- **类型**：交叉引用一致性
- **位置**：L254
- **问题**：Baseline Profiles 的引入版本写成“Android 9（作为 App Profiles）/ Android 13（正式名称）”，与官方 Baseline Profiles 版本矩阵口径不一致。
- **建议**：改成 API 24-27 通过 ProfileInstaller 在首轮运行后安装 Baseline Profile，API 28+ Play 在安装时使用 Baseline Profiles 并叠加 Cloud Profiles；避免把“正式名称”绑定到 Android 13。

## [Task9 Deep Review] 1.15 JNI/NDK 性能优化 — 2026-04-25
- **类型**：数据缺失
- **位置**：L127
- **问题**：Perfetto / simpleperf 观测链路仍停在示意图占位，缺一份可复核的 JNI ATrace slice 与 native 采样导入样例。
- **建议**：补一组最小样例：Java `Trace` + NDK `ATrace_beginSection()` 的同线程 slice，以及一次 simpleperf `report-sample --protobuf` 导入 Perfetto 后的热点截图或 SQL/命令输出。

## [External Review] 19.19 热降频识别 — 2026-04-25
- **类型**：原理链完整性
- **问题**：PerfDog 是观察热降频的最佳工具。
- **建议**：补充一个判定模型：如果 `Temperature` 达到临界值且 `CPU/GPU Frequency` 出现断崖式下跌，此时的 FPS 下降应归因为系统调度而非业务逻辑。
- **来源**：2026-04-25-15-19-external-review.md

## [Task9 Deep Review] 6.2 文件系统 — 2026-04-25
- **类型**：源码准确性
- **位置**：L113
- **问题**：`flush` 线程“每 30 秒触发一次”的说法把 dirty page 过期阈值和后台写回唤醒周期混在一起。Linux/Android 内核通常要同时看 `dirty_writeback_centisecs`、`dirty_expire_centisecs` 与设备调参。
- **建议**：改成“后台写回由 dirty_* sysctl 和内核 flusher 共同决定；默认口径常见为 5s 唤醒、30s 过期阈值，设备可能调参”，并保留 fsync 被后台写回挤占队列的因果。

## [Task9 Deep Review] 6.2 文件系统 — 2026-04-25
- **类型**：数据缺失
- **位置**：L279-L283 / L457
- **问题**：EROFS 压缩率、随机读、启动时间收益给出了 30%-45%、20%、300%、10%-15% 等数字，但正文没有绑定具体设备、Android 版本、分区大小、压缩算法和测试来源。
- **建议**：补充来源表，至少标出 Pixel / 华为公开数据各自的测试条件；无法闭环的数字降级为“公开案例中出现过的量级”。

## [Task9 Deep Review] 18.8 OpenGL ES 渲染链路 — 2026-04-25
- **类型**：版本差异/边界说明
- **位置**：L198-L217
- **问题**：章节把 GLES BufferQueue 写成“通常 3 个 Slot”，方向正确，但容易被读者当作固定结论。实际 buffer count 会受 BufferQueue 配置、async mode、producer/consumer 最大持有数和厂商实现影响。
- **建议**：补一句边界：三缓冲是常见形态，不是协议保证；实战应从 Perfetto 的 dequeue/queue 节奏、SurfaceFlinger dump 或 Winscope 中确认实际 Buffer 深度。



## [External Review] 19.19 PerfDog 与实验室性能测试 — 2026-04-25
- **类型**：原理链完整性
- **位置**：热降频识别
- **问题**：缺少热降频的判定模型说明
- **建议**：补充判定模型——Temperature 达临界值且 CPU/GPU Frequency 断崖式下跌时，FPS 下降应归因为系统调度而非业务逻辑
- **来源**：Gemini 外部 review

## [External Review] 19.16 ProfilingManager — 2026-04-25
- **类型**：安全警示
- **位置**：Heap Dump 敏感数据段落
- **问题**：未提及 Heap Dump 敏感数据脱敏与合规
- **建议**：补充安全警示段落，提醒上传前 OID 脱敏或加密
- **来源**：Gemini 外部 review


## [Task9 Deep Review] 8.7 Baseline Profiles 与编译优化实践 — 2026-04-25
- **类型**：源码准确性/数据缺失
- **位置**：L64-L65、L134-L139、L323-L330 构建产物路径
- **问题**：章节把二进制打包产物基本写成 `baseline.prof` 单文件。官方手动安装/测量流程还会处理 `assets/dexopt/baseline.profm`，并在 `.dm` 包中重命名为 `primary.profm`。
- **建议**：保留 `baseline.prof` 作为首要检查项，同时补一句 `baseline.profm` 是伴随 metadata，手动 sideload / `.dm` 验证时要和 `baseline.prof` 一起处理。


## [Task9 Deep Review] 14.4 dumpsys 系列命令 — 2026-04-25
- **类型**：数据缺失
- **位置**：L270-L276 cpuinfo 阈值
- **问题**：“后台进程 CPU 持续超过 5% 就值得调查”缺少设备类型、核心数、采样窗口和业务场景基线。
- **建议**：改为建议读者先采集 30-60 秒 `top -H` / Perfetto CPU 轨道并与同机型基线对比；如保留 5%，必须说明它只是经验起点，不是 Android 系统阈值。
## [External Review] 10.README ch10 目录索引 — 2026-04-25
- **类型**：交叉引用
- **位置**：README.md 目录列表
- **问题**：README 列出的子章节与实际文件名（05-07）存在断层
- **建议**：确保 README 列表与文件名一一对应
- **来源**：Gemini 外部 review

## [External Review] 10.7 SQLite WAL F2FS — 2026-04-25
- **类型**：知识盲区
- **位置**：07-sqlite-room-performance.md
- **问题**：未提及 F2FS 下 WAL 模式可能的写入放大
- **建议**：补充 F2FS 文件系统下 WAL 写入放大效应说明
- **来源**：Gemini 外部 review

## [External Review] 12.1 ANDROID_STRIP_DEBUG_SYMBOLS — 2026-04-25
- **类型**：工具建议
- **位置**：01-apk-size.md
- **问题**：推荐 CMake 传参方式，AGP 8.x 已默认处理 strip
- **建议**：优先推荐 Gradle DSL packaging.jniLibs.keepDebugSymbols 配置
- **来源**：Gemini 外部 review

## [External Review] 12.2 Brotli 压缩 — 2026-04-25
- **类型**：数据支撑
- **位置**：02-network-performance.md
- **问题**：仅提到 Gzip，未提及 Brotli (br) 可额外减少 15-25% 文本体积
- **建议**：在协议选择章节增加 Brotli 推荐
- **来源**：Gemini 外部 review

## [External Review] 13.README 目录标签 — 2026-04-25
- **类型**：结构建议
- **位置**：目录列表
- **问题**：13.8 和 13.10 SQL 重灾区未标记为进阶必读
- **建议**：在目录项后增加难度/场景标签
- **来源**：Gemini 外部 review

## [External Review] 15.README 版本演进 — 2026-04-25
- **类型**：版本差异
- **位置**：全文
- **问题**：Android 12+ 演进细节不足
- **建议**：补充 Android 12-15 相关演进简短说明
- **来源**：Gemini 外部 review

## [External Review] 18.20 Winscope 优先推荐 — 2026-04-25
- **类型**：工具建议
- **位置**：dumpsys SurfaceFlinger --latency 段
- **问题**：dumpsys --latency 在 BLAST 架构下参考价值下降
- **建议**：在方法论中增加 Winscope (SurfaceFlinger trace) 优先级推荐
- **来源**：Gemini 外部 review

## [External Review] 19.19 热降频识别模型 — 2026-04-25
- **类型**：原理链
- **位置**：温度与帧率关联
- **问题**：缺少热降频的判定模型
- **建议**：补充判定模型：Temperature 达临界 + CPU/GPU Frequency 断崖下跌 → FPS 下降归因系统调度
- **来源**：Gemini 外部 review

## [External Review] 8.09 Thermal 策略组合 — 2026-04-25
- **类型**：实操建议
- **位置**：ADPF Headroom API 段
- **问题**：未区分 getThermalHeadroom（预测性）与 getCpuHeadroom（即时性）
- **建议**：给出组合策略建议
- **来源**：Gemini 外部 review

## [External Review] 9.5 QueuedWork 反射限制 — 2026-04-25
- **类型**：版本差异
- **位置**：05-case-studies.md QueuedWork 反射修复
- **问题**：Android 12+ Hidden API 限制，反射需配合元反射策略
- **建议**：补充 Hidden API 限制说明及 Modern Broadcast Queue 优化
- **来源**：Gemini 外部 review

## [Task9 Deep Review] 14.5 三方性能库 — 2026-04-25
- **类型**：数据缺失
- **位置**：L378（多库性能开销叠加）
- **问题**：正文写 Matrix 约 2~5% 开销、KOOM Native Hook 有少量开销，但没有设备、版本、采样率、模块范围或来源。该数字容易被读者当成通用基线。
- **建议**：补充测试条件或来源；若无法给出一手数据，改成“需按模块和采样率实测”，并给出最小 benchmark 方案。

## [Task9 Deep Review] 14.13 Hook 基础设施与性能工具实现原理 — 2026-04-25
- **类型**：源码准确性
- **位置**：L309/L427（mprotect 页边界）
- **问题**：正文多处写“地址和长度都必须按页大小对齐”。Linux `mprotect()` 的硬要求是起始地址按页对齐，长度覆盖到的页面会按范围处理；工程上通常会把长度向上取整，但这不是同一条 API 约束。
- **建议**：改成“addr 必须页对齐，len 按覆盖范围向上扩展到页边界”，并保留 16KB 设备上不要硬编码 4096 的结论。


## [Task9 Deep Review] 13.10 Perfetto SQL 性能分析实战手册 — 2026-04-26
- **类型**：SQL 性能
- **位置**：大 Trace 上的 GC/ANR/锁竞争区间 JOIN
- **问题**：外部 review 已指出窗口函数和大规模 JOIN 在 >1GB trace 上可能长时间无响应。正文只在少数位置提示缩小窗口，缺少统一的中间表固化建议。
- **建议**：在 SQL 基础或结尾补充：复杂查询先用 CREATE PERFETTO TABLE 固化目标进程、目标时间窗和中间结果，再做 SPAN_JOIN / INTERVAL_INTERSECT。

## [Task9 Deep Review] 14.4 dumpsys 系列命令 — 2026-04-26
- **类型**：案例支撑
- **位置**：SurfaceFlinger Frontend dump
- **问题**：外部 review 建议补一个 Android 15+ Composition list / LayerSnapshot 的典型输出样例。当前解释准确，但读者第一次看新版 dump 时仍缺少对照样本。
- **建议**：补一个短样例，说明 Composition list 的层级顺序、LayerSnapshot bounds/transform 与 HWC minidump 的对应关系。

## [Task9 Deep Review] 15.5 线上性能监控 — 2026-04-26
- **类型**：源码准确性
- **位置**：FrameMetrics API 指标表：COMMAND_ISSUE
- **问题**：表格把 COMMAND_ISSUE 描述成“GPU 命令执行耗时 / GPU”。FrameMetrics.COMMAND_ISSUE_DURATION 更准确是 RenderThread/HWUI 向 GPU 发出 draw command 的耗时，不等同于 GPU 实际执行完成时间。
- **建议**：改成“命令提交耗时 / RenderThread→GPU 提交阶段”，并补一句：GPU 实际执行需结合 Perfetto GPU counter、FrameTimeline 或厂商 GPU 工具确认。

## [Task9 Deep Review] 2.9 渲染机制的版本演进 — 2026-04-26
- **类型**：数据缺失
- **位置**：L185（SkiaVulkan CPU 开销降低 30–50%）
- **问题**：正文保留了“[待验证：需补充 benchmark 来源]”。量化区间没有设备、GPU、驱动、场景或来源，读者会把它当成通用收益。
- **建议**：补充官方/厂商 benchmark 条件；若无法确认，删除 30–50% 量化，只保留 Vulkan 可能降低 CPU driver overhead 的机制描述。

## [Task9 Deep Review] 4.1 Android 内存模型全景 — 2026-04-26
- **类型**：版本差异
- **位置**：L273（Ashmem 替代路径）
- **问题**：正文写 Ashmem 在现代 Android 上逐渐被 dmabuf 替代，容易把匿名共享内存与图形/硬件 buffer 混在一起。匿名共享内存主替代路径更接近 memfd，dmabuf 主要用于可被硬件/DMA 子系统共享的 buffer。
- **建议**：改成“匿名共享内存从 ashmem 迁移到 memfd；图形、相机、媒体等硬件共享 buffer 更多使用 dma-buf”，并保留老版本 ashmem 兼容边界。

## [Task9 Deep Review] 8.5 案例集 — 2026-04-26
- **类型**：版本差异
- **位置**：L181-L191（MultiDex 加载阶段与优化手段）
- **问题**：正文写 Android 5.0+ 上 MultiDex 的 dex 提取和验证仍消耗可观 IO，又写其余 dex 在子线程异步加载。官方 Multidex 文档说明 Android 5.0+ ART 原生支持从 APK 加载多个 DEX，并在安装时预编译；pre-21 的 androidx.multidex 才有运行时解压/安装路径。
- **建议**：按 pre-21 Dalvik / API 21+ ART 拆开写：pre-21 说明 MultiDex.install 与 secondary dex 处理；API 21+ 重点写类加载、verification/oat、启动路径类布局，不要把 dex 提取作为通用 Android 5.0+ 瓶颈。

- **类型**：数据缺失
- **位置**：L193（Protobuf 比 JSON 快 5-10 倍）
- **问题**：5-10 倍没有绑定数据结构、字段数量、parser 实现和设备条件。
- **建议**：限定为抖音该配置数据场景或补 benchmark 条件；否则降级为“通常更快，具体倍数依场景变化”。

- **类型**：版本差异
- **位置**：L146/L248/L455（R8 full mode 开关）
- **问题**：AGP 8.0+ 默认 full mode 的方向正确，但 compat 开关、warning/移除时间线和 AGP 版本边界没有说清。
- **建议**：补 AGP 8.x 默认 full mode、旧 compat 开关的迁移边界，以及 keep rules/反射/JNI 的验证清单。

## [Task9 Deep Review] 13.8 Perfetto 输入延迟 SQL 深度分析 — 2026-04-26
- **类型**：SQL 逻辑
- **位置**：L468-L471（滑动卡顿输入分析 CASE 顺序）
- **问题**：TOTAL_SLOW 放在 HANDLING_SLOW 和 DISPATCH_SLOW 之后，total 已超过 32ms 的样本可能先被标成局部阶段慢。
- **建议**：先判断 total_latency_dur，再判断 handling/dispatch；或输出多个布尔列避免单标签遮蔽。

- **类型**：源码准确性
- **位置**：L125（android_input_events.event_seq 类型）
- **问题**：Perfetto stdlib android_input_events 将 event_seq 声明为 STRING，正文表格标为 long。
- **建议**：把 event_seq 类型改为 string，并说明它是同一 event channel 内递增的序号字符串。

- **类型**：数据缺失
- **位置**：L268-L274（Pixel 7 参考值示例）
- **问题**：参考值给出设备/版本/样本量，但没有 trace 配置、场景脚本或统计来源，难以复现实验边界。
- **建议**：补采集配置、输入手势脚本、Trace Processor 版本和原始样本来源；否则标为经验参考。

## [Task9 Deep Review] 14.10 eBPF/BPF 在 Android 性能分析中的应用 — 2026-04-26
- **类型**：源码准确性
- **位置**：L296-L304（UprobeStats user build allowlist）
- **问题**：AOSP android-16.0.0_r1 Guardrail.cpp 的 allowlist 还包含 ActivityManagerService$LocalService.updateDeviceIdleTempAllowlist，正文代码片段只列了 CachedAppOptimizer/OomAdjuster/OomAdjusterModernImpl。
- **建议**：补齐 allowlist，或标注代码片段为节选；同时把源码锚点指到 packages/modules/UprobeStats/src/Guardrail.cpp。

- **类型**：数据缺失
- **位置**：L407-L412（Binder command hex 值）
- **问题**：kBR_FROZEN_REPLY / kBR_TRANSACTION_PENDING_FROZEN 的 0x7212/0x7214 没有绑定 binder.h 版本；binder command code 属于内核头文件口径，跨版本应以源码为准。
- **建议**：补 Linux/Android common kernel binder.h 版本锚点，或在示例前说明“以当前设备 binder.h 为准”。

- **类型**：版本差异
- **位置**：L326-L334（sched_ext 管理范围）
- **问题**：正文同时写“管理 SCHED_NORMAL/BATCH/IDLE/EXT”与“部分切换”，但没有把 SCX_OPS_SWITCH_PARTIAL 开关前后的任务归属差异写清。
- **建议**：补 kernel.org 口径：未设置 SCX_OPS_SWITCH_PARTIAL 时 NORMAL/BATCH/IDLE/EXT 由 sched_ext 管；设置后只有 SCHED_EXT policy 任务交给 sched_ext。

## [Task9 Deep Review] 14.9 Android Camera 性能与 Perfetto 分析 — 2026-04-26
- **类型**：数据缺失/SQL 鲁棒性
- **位置**：L317-L334
- **问题**：预览 Buffer 到达 SQL 固定匹配 counter.name LIKE "%BufferTX - SurfaceView%" 且 value=1。CameraX PreviewView、TextureView、SurfaceTexture、自定义 Surface 名或 OEM layer 名都可能导致查询为空，当前缺少先枚举 counter_track/track 名称再选目标 layer 的步骤。
- **建议**：补一条预查询：列出包含 BufferTX/Surface/Preview 的 counter track 名称和 upid/track_id，再按实际 layer 名计算帧间隔；示例说明 SurfaceView 只是样例，不是通用 track 名。

## [Task9 Deep Review] 13.2 Trace 抓取 — 2026-04-26
- **类型**：知识盲区
- **位置**：L365-L416（atrace Categories 详解）
- **问题**：正文只说不同设备 category 略有差异，但没有交代 Qualcomm/MTK 等厂商私有 category 与 vendor tracepoint 的识别方法；遇到 camera/audio/gpu 专项问题时，读者仍不知道如何从 atrace --list_categories 回到具体 ftrace event。
- **建议**：补一段“厂商私有 category 处理”：先保存 adb shell atrace --list_categories 输出，再用 tracefs available_events / Perfetto UI Recording command 对照 category 展开的 ftrace_events；不能把示例中的 power/gpu_frequency 当成所有设备必有事件。


## [Task9 Deep Review] 13.9 Android Tracing 基础设施：atrace、ftrace 与 Perfetto 数据采集原理 — 2026-04-26
- **类型**：数据缺失
- **位置**：L385-L393（Tracing 开销与性能影响表）
- **问题**：表中给出 function tracer 10-15%、tracepoint 100-500ns、trace_marker 200-500ns、eBPF kprobe 500-2000ns 等精确范围，但正文同时标注待验证，缺少设备、内核版本、事件频率和测量方法。
- **建议**：补一组可复现实测条件，或把数值降级为“量级参考”；至少写清 Pixel/内核版本、启用事件集、采样频率、CPU 占用或 benchmark delta。


## [Task9 Deep Review] 14.6 自动化测试工具 — 2026-04-26
- **类型**：数据缺失
- **位置**：L234（Baseline Profile 约 30% 冷启动收益）
- **问题**：“约 30%”是官方宣传口径，但正文没有给出来源链接、测试条件或边界，容易被读者当成任何 App 都稳定获得 30%。
- **建议**：补官方 Baseline Profiles 文档引用，并说明该数字依赖设备、启动路径、profile 覆盖率和安装/编译状态；示例结果应写设备型号、系统版本、启动模式、迭代次数。


## [Task9 Deep Review] 18.15 视频叠加与 HWC — 2026-04-26
- **类型**：数据缺失
- **位置**：L57「功耗差异」
- **问题**：`GPU Path 多消耗 2-3x 内存带宽`、`Overlay vs GPU 合成功耗差异可能达到 10-20%` 没有设备、分辨率、刷新率、编解码格式、亮度、测试时长或 Perfetto / power rail 证据。AOSP HWC 源码只能证明机制，不能证明这些数值区间。
- **建议**：补一组最小实验条件：同一视频、同一设备、同一亮度和刷新率下，对比 TextureView/GPU path 与 SurfaceView/DEVICE composition 的 GPU counter、memory bandwidth、power rail 或 Battery Historian 数据；拿不到数据时把数值收敛成定性结论。

## [Task9 Deep Review] 18.15 视频叠加与 HWC — 2026-04-26
- **类型**：交叉引用
- **位置**：frontmatter `related_chapters`
- **问题**：正文依赖 BufferQueue/BLASTBufferQueue 与 fence 协调，但关联章节只列了 2.6、2.10、18.6，缺少 2.13 BufferQueue 与 2.16 Sync Fence。
- **建议**：补 `2.13` 与 `2.16`，让读者能顺着 HWC 协商继续追 buffer 生命周期和 acquire/release fence。
## [External Review] 1.1 1.1 — 2026-04-26
- **类型**：P2建议改进
- **位置**：1.1
- **问题**：- [P2][版本差异覆盖][16KB Page Size 对 Android 16 的影响]
- 原文问题：描述了 16KB 特性，但标注 `[待验证: 16KB Page Size 在 Android 16 上的性能数据需实际设备验证]`。
- 问题描述：16KB 页面的性能影响缺乏实证支撑。
- 建议：引用 Android 开发者博客中官方给出的 16KB Page Size 性能提升（如启
- **来源**：2026-04-25-15-1.1-external-review.md

## [External Review] 1.1 1.1 — 2026-04-26
- **类型**：数据补充
- **位置**：16KB Page Size
- **问题**：缺乏性能提升的直观数据。
- **建议**：引用 Android 15/16 官方关于 16KB 优化的博文数据。
- **来源**：2026-04-25-15-1.1-external-review.md

## [External Review] 1.10 1.10 ContentProvider 性能与优化 — 2026-04-26
- **类型**：P2建议改进
- **位置**：1.10
- **问题**：- [P2][原理链完整性][多进程 ContentProvider]
- 原文问题：提到了 `Process.isProviderProcess()` 判断，标注了 `[待验证：Process API 是否提供直接的 Provider 进程判断方法...]`。
- 证据或观察依据：Android SDK 中的 `Process` 类并没有提供 `isProviderProcess()` 这样的官
- **来源**：2026-04-25-15-1.10-external-review.md

## [External Review] 1.10 1.10 ContentProvider 性能与优化 — 2026-04-26
- **类型**：API 准确性
- **位置**：`多进程 ContentProvider 的适用场景与注意事项`
- **问题**：猜测存在 `Process.isProviderProcess()`。
- **建议**：改为使用 `Application.getProcessName()` 判断进程名。
- **来源**：2026-04-25-15-1.10-external-review.md

## [External Review] 1.11 1.11 Zygote 机制与启动性能优化 — 2026-04-26
- **类型**：P2建议改进
- **位置**：1.11
- **问题**：- [P2][数据/案例支撑][在 Perfetto / logcat 里怎么观察这条链]
- 原文问题：文章提供了很棒的 SQL 查询，但没有提供查询结果的可视化呈现或 Trace 截图。
- 证据或观察依据：读者对代码和 SQL 较易理解，但对 Perfetto UI 的直观感受需要图片支撑。
- 问题描述：缺少 Trace 截图。
- 建议：提供包含 `launching: pkg`、`am
- **来源**：2026-04-25-15-1.11-external-review.md

## [External Review] 1.11 1.11 Zygote 机制与启动性能优化 — 2026-04-26
- **类型**：易读性
- **位置**：全文
- **问题**：无 Trace 截图。
- **建议**：补充带有关键标记的 Trace 截图。
- **来源**：2026-04-25-15-1.11-external-review.md

## [External Review] 1.12 1.12 AutoFDO 反馈导向编译优化 — 2026-04-26
- **类型**：P2建议改进
- **位置**：1.12
- **问题**：- [P2][数据/案例支撑][OEM 能做什么]
- 原文问题：提到 Kleaf / DDK 的配置时，带有 `[待验证: Kleaf / DDK 的具体属性名会随分支演进调整...]` 的标记。
- 证据或观察依据：Kleaf 的属性配置在 AOSP GKI build 脚本中相对固定。
- 问题描述：可以给出 Kleaf build 中引用 `kernel.afdo` 的确切 Bazel 属
- **来源**：2026-04-25-15-1.12-external-review.md

## [External Review] 1.12 1.12 AutoFDO 反馈导向编译优化 — 2026-04-26
- **类型**：细节补充
- **位置**：`OEM 能做什么` 小节
- **问题**：缺乏具体的 Bazel build 配置示例。
- **建议**：提供一小段 `kernel_build` target 引用 afdo profile 的示例配置。
- **来源**：2026-04-25-15-1.12-external-review.md

## [External Review] 1.13 1.13 — 2026-04-26
- **类型**：P2建议改进
- **位置**：1.13
- **问题**：- [P2][原理链完整性][DeliQueue 无锁优化]
- 原文问题：“取消路径会和 drain / 遍历竞争，源码里明确提到 tombstone”
- 证据或观察依据：AOSP 源码中对 tombstone 的处理逻辑比较复杂。
- 问题描述：原文只是提到了 tombstone，但未解释消费者如何清理这些 tombstone。
- 建议：建议补充一句话解释清理时机。
- **来源**：2026-04-25-15-1.13-external-review.md

## [External Review] 1.14 1.14 — 2026-04-26
- **类型**：P2建议改进
- **位置**：1.14
- **问题**：- [P2][交叉引用一致性][与其他机制的关系]
- 原文问题：提到了 §2.4 / 2.5 但没有明确具体章节名称
- 证据或观察依据：排版规范要求
- 问题描述：引用缺少章节名
- 建议：补充章节名以方便阅读
- **来源**：2026-04-25-15-1.14-external-review.md

## [External Review] 1.2 1.2 — 2026-04-26
- **类型**：P2建议改进
- **位置**：1.2
- **问题**：- [P2][数据/案例支撑][参考基线数据表]
- 原文问题：数据表中标注 `[待补充：Pixel 8 实测 bootstat 数据截图]`。
- 建议：通过执行真实的 `adb shell bootstat -l` 获取一组参考输出，补充到文档中，提高说服力。
- **来源**：2026-04-25-15-1.2-external-review.md

## [External Review] 1.2 1.2 — 2026-04-26
- **类型**：图表补充
- **位置**：bootstat 和 Perfetto 示例
- **问题**：需要一张带标注的实际开机 Trace 截图。
- **建议**：准备环境抓取一份完整的 reboot trace 截图并补充。
- **来源**：2026-04-25-15-1.2-external-review.md

## [External Review] 1.3 1.3 — 2026-04-26
- **类型**：P2建议改进
- **位置**：1.3
- **问题**：- [P2][原理链完整性][Shared Memory]
- 原文问题：关于图形缓冲区提到 `GraphicBuffer` / `HardwareBuffer` 更接近 dma-buf，建议放到其他章节讲。
- 建议：在此处简单给出 1-2 句 dma-buf 相较于 memfd_create 的区别（如面向硬件设备零拷贝），以增强进程间通信机制的知识闭环。
- **来源**：2026-04-25-15-1.3-external-review.md

## [External Review] 1.3 1.3 — 2026-04-26
- **类型**：扩展说明
- **位置**：共享内存
- **问题**：可以略微补充一点 dma-buf 的概念。
- **建议**：用一句话说明 dma-buf 是如何实现跨进程且跨硬件的零拷贝。
- **来源**：2026-04-25-15-1.3-external-review.md

## [External Review] 1.4 1.4 — 2026-04-26
- **类型**：P2建议改进
- **位置**：1.4
- **问题**：- [P2][原理链完整性][oneway 调用的反压机制]
- 原文问题：提到“特别是在 Android 14+ 引入 Lazy Async 之后... Client 端调用 oneway 方法也可能被短暂阻塞”。
- 问题描述：未给出 Lazy Async 导致阻塞的具体条件或相关源码路径（如 `IPCThreadState.cpp` 的特定实现）。
- 建议：提供一到两句对 Lazy Asy
- **来源**：2026-04-25-15-1.4-external-review.md

## [External Review] 1.4 1.4 — 2026-04-26
- **类型**：技术细节补充
- **位置**：oneway 调用
- **问题**：Lazy Async 导致调用方阻塞的机制不够明晰。
- **建议**：添加针对 Lazy Async 的简短源码层说明。
- **来源**：2026-04-25-15-1.4-external-review.md

## [External Review] 1.5 1.5 — 2026-04-26
- **类型**：P2建议改进
- **位置**：1.5
- **问题**：- [P2][数据/案例支撑][Perfetto Trace 截图]
- 原文问题：标注 `[待补充：Perfetto Trace 截图 — 主线程各状态...]`
- 建议：提供真实且直观的 Perfetto 截图，将不同颜色状态（绿色 Running，深橙色 Uninterruptible Sleep）图文并茂展示。
- **来源**：2026-04-25-15-1.5-external-review.md

## [External Review] 1.5 1.5 — 2026-04-26
- **类型**：配图补充
- **位置**：在 Perfetto 中的表现
- **问题**：缺少实际的 Trace 截图。
- **建议**：后续编辑阶段落实截图，确保图文一致。
- **来源**：2026-04-25-15-1.5-external-review.md

## [External Review] 1.6 1.6 — 2026-04-26
- **类型**：P2建议改进
- **位置**：1.6
- **问题**：- [P2][原理链完整性][最新架构变化]
- 原文问题：标注 `[待验证：具体 API 在 android-16.0.0_r1 中的实现细节]`（关于 system-triggered profiling）。
- 建议：提供针对 `ProfilingManager` (如果存在该新增类) 或 `ApplicationStartInfo` 的直接 AOSP 源码路径引用，以增加技术说服力。
- **来源**：2026-04-25-15-1.6-external-review.md

## [External Review] 1.6 1.6 — 2026-04-26
- **类型**：源码引用补充
- **位置**：最新架构变化
- **问题**：对 ApplicationStartInfo 的提及过于概念化。
- **建议**：给出对应的 API 类名和示例属性（如 `getStartupState()`）。
- **来源**：2026-04-25-15-1.6-external-review.md

## [External Review] 1.7 1.7 ART 编译管线与 dex2oat 优化 — 2026-04-26
- **类型**：P2建议改进
- **位置**：1.7
- **问题**：- [P2][原理链完整性][Android 16/17 编译体系的最新演进]
- 原文问题：“Android 16 的公开资料开始出现 Cloud Compilation 等云侧编译信号... Android 17 则把 static final 的行为约束收得更紧”
- 证据或观察依据：Cloud Compilation 目前多为外部宣发，在 AOSP 核心主干中不易找到直接确凿的完整量产链路
- **来源**：2026-04-25-15-1.7-external-review.md

## [External Review] 1.7 1.7 ART 编译管线与 dex2oat 优化 — 2026-04-26
- **类型**：表述严谨性
- **位置**：`Android 16/17 编译体系的最新演进`
- **问题**：Cloud Compilation 描述偏向新闻性。
- **建议**：补充说明其对 GMS 的依赖性。
- **来源**：2026-04-25-15-1.7-external-review.md

## [External Review] 1.8 1.8 Activity Manager Service 与性能分析 — 2026-04-26
- **类型**：P2建议改进
- **位置**：1.8
- **问题**：- [P2][原理链完整性][Input ANR]
- 原文问题：Input ANR 部分提到了 `notifyWindowUnresponsive()`。
- 证据或观察依据：在某些设备或复杂 UI 树中，InputDispatcher 的状态可能受到 SurfaceFlinger 侧 Buffer 积压的影响。
- 问题描述：仅从 WMS 和 AMS 角度解释了 Input ANR，稍微缺乏了
- **来源**：2026-04-25-15-1.8-external-review.md

## [External Review] 1.8 1.8 Activity Manager Service 与性能分析 — 2026-04-26
- **类型**：原理补充
- **位置**：Input ANR 小节
- **问题**：可以增加关于 SurfaceFlinger 阻塞主线程导致 Input ANR 的提示。
- **建议**：补充 1-2 句话的扩展说明。
- **来源**：2026-04-25-15-1.8-external-review.md

## [External Review] 1.9 1.9 Package Manager Service 与应用安装性能 — 2026-04-26
- **类型**：P2建议改进
- **位置**：1.9
- **问题**：- [P2][原理链完整性][OTA 更新后的 mass dexopt]
- 原文问题：提到 ART Service 策略中，OTA 后只对 primary DEX 做 `verify`。
- 问题描述：可以进一步解释 `verify` 的耗时在现代设备（UFS 3.1/4.0）上大约的量级，给读者一个更直观的体感。
- 建议：补充一些经验数据，比如中端机型一次 verify 的平均耗时。
- **来源**：2026-04-25-15-1.9-external-review.md

## [External Review] 1.9 1.9 Package Manager Service 与应用安装性能 — 2026-04-26
- **类型**：细节补充
- **位置**：`应用更新与 OTA 更新的性能影响`
- **问题**：缺乏耗时量级感。
- **建议**：提供 verify 的粗略耗时参考值。
- **来源**：2026-04-25-15-1.9-external-review.md

## [External Review] 2.1 2.1 — 2026-04-26
- **类型**：P2建议改进
- **位置**：2.1
- **问题**：- [P2][数据/案例支撑][实战案例]
- 原文问题：特定参数缺乏定量数据
- 证据或观察依据：在说明机制时多为定性描述
- 问题描述：缺少具体的毫秒级/字节级估算
- 建议：补充业界普遍的实测数据或典型的 benchmark 表现。
- **来源**：2026-04-25-15-2.1-external-review.md

## [External Review] 2.1 2.1 — 2026-04-26
- **类型**：案例丰富度
- **位置**：全文
- **问题**：可以加入更多真实的 Trace 截图分析
- **建议**：提供包含具体时间的 Perfetto 截图
- **来源**：2026-04-25-15-2.1-external-review.md

## [External Review] 2.11  — 2026-04-26
- **类型**：P2建议改进
- **位置**：2.11
- **问题**：- **[P2][源码准确性][§渲染管线的根本区别]**
- **原文问题**：文中提到 `1.ui` 和 `1.raster`。
- **证据或观察依据**：Flutter Engine 源码中设置线程名的逻辑：`fml::Thread::SetCurrentThreadName("io.flutter.ui")`。
- **问题描述**：在某些 Android 版本的 Perfetto/Sy
- **来源**：2026-04-25-15-2.11-external-review.md

## [External Review] 2.12 `2.12 Window Manager Service 与窗口管理` — 2026-04-26
- **类型**：P2建议改进
- **位置**：2.12
- **问题**：- **[P2][数据/案例支撑][Perfetto Slice 名变迁]**
  - 问题描述：Android 14 后，部分核心 Slice 名（如 `relayoutWindow`）在某些厂商或特定的 Atrace Category 下可能被重构。
  - 建议：在 Perfetto 章节补充一个“Slice 模糊搜索”的技巧，说明如何通过 `SELECT name FROM slice W
- **来源**：2026-04-25-15-2.12-external-review.md

## [External Review] 2.13  — 2026-04-26
- **类型**：P2建议改进
- **位置**：2.13
- **问题**：- **[P2][知识盲区][BufferQueue Counters]**
  - **问题描述**：Perfetto 分析部分提到了 Slice，但忽略了 `BufferQueue` 自动上报的计数器（Counters）。
  - **建议**：说明在 Perfetto 中搜索 `buffer_count` 或 `BufferQueue` 可以看到当前已分配、已 dequeue 的实时数字，这
- **来源**：2026-04-25-15-2.13-external-review.md

## [External Review] 2.14 2.14 图形 API 演进与选择策略（OpenGL ES / Vulkan / ANGLE） — 2026-04-26
- **类型**：P2建议改进
- **位置**：2.14
- **问题**：- [P2][源码准确性][补充：vkQueuePresentKHR 的同步陷阱]
- 原文问题：Vulkan 扩展命名不规范。
- 证据或观察依据：Khronos 官方文档及 Vulkan SDK。
- 问题描述：原文写为 `VK_EXT_swapchain_maintenance1`，实际应为 `VK_KHR_swapchain_maintenance1`。虽然部分驱动曾存在 EXT 阶段，但
- **来源**：2026-04-25-15-2.14-external-review.md

## [External Review] 2.14 2.14 图形 API 演进与选择策略（OpenGL ES / Vulkan / ANGLE） — 2026-04-26
- **类型**：源码准确性
- **位置**：补充：vkQueuePresentKHR 的同步陷阱
- **问题**：`VK_EXT_swapchain_maintenance1` 命名不规范。
- **建议**：修正为 `VK_KHR_swapchain_maintenance1`。
- **来源**：2026-04-25-15-2.14-external-review.md

## [External Review] 2.15 2.15 DMA-BUF、Gralloc 与跨进程图形内存共享 — 2026-04-26
- **类型**：P2建议改进
- **位置**：2.15
- **问题**：- **[P2][数据/案例支撑][16KB 页面开销]**
  - **原文位置**：16KB 页面分配预算小节。
  - **证据或观察依据**：16KB page size 带来的内部碎片化。
  - **问题描述**：提到了“更容易出现尾部空洞”，但没有给出一个具体的量化对比。
  - **建议**：补充一个计算例子（如 258KB buffer 在 4KB vs 16KB 下的页占用对比
- **来源**：2026-04-25-15-2.15-external-review.md

## [External Review] 2.16  — 2026-04-26
- **类型**：P2建议改进
- **位置**：2.16
- **问题**：- **[P2][原理链完整性][名词解释]**：建议明确 **HWC1 的 Retire Fence** 与 **HWC2 的 Present Fence** 的演进关系。文中提到了“旧资料叫 retire”，但没说清楚这是协议版本（HWC1 vs HWC2）的变化，容易让读者混淆新旧文档。
- **来源**：2026-04-25-15-2.16-external-review.md

## [External Review] 2.17  — 2026-04-26
- **类型**：P2建议改进
- **位置**：2.17
- **问题**：### 1. [P2][数据/案例支撑][Perfetto 验证部分]
- **原文问题**：提到 `SurfaceViews are currently not supported` (Perfetto 文档)。
- **证据或观察依据**：最新版本的 Perfetto 其实已经通过 `FrameTimeline` 支持了 `SurfaceView`（只要该 Surface 关联了特定的 Win
- **来源**：2026-04-25-15-2.17-external-review.md

## [External Review] 2.18 `2.18 Adaptive Refresh Rate 与动态帧率控制` — 2026-04-26
- **类型**：P2建议改进
- **位置**：2.18
- **问题**：- [P2][数据/案例支撑][Perfetto SQL]
- **原文问题**：SQL 示例使用了 `actual_frame_timeline_slice`。
- **建议**：建议在文中明确说明，如果是在 Android 14+ 使用内置的 Perfetto SQL 引擎，可以直接调用 `android_jank_cuj` 标准库函数，这样比手写 SQL 查 raw table 更高效。
- **来源**：2026-04-25-15-2.18-external-review.md

## [External Review] 2.19  — 2026-04-26
- **类型**：P2建议改进
- **位置**：2.19
- **问题**：- **[P2][版本差异覆盖][Android 16 API]**
  - **问题描述**：文中提到 `Android 16 (API 36) 才公开 Display.getSuggestedFrameRate(int category)`。
  - **核验结论**：经核实，`Display.getSuggestedFrameRate` 及其分类（Category）API 的定义和初步实现实
- **来源**：2026-04-25-15-2.19-external-review.md

## [External Review] 2.20  — 2026-04-26
- **类型**：P2建议改进
- **位置**：2.20
- **问题**：- **[P2][数据/案例支撑][2.20 - SQL 过滤建议]**
- **原文问题**：SQL 示例未过滤 `display_id`。
- **问题描述**：在 Connected Display 场景下，`surfaceflinger_layers_snapshot` 会同时包含两块屏幕的 layer。不加 `display_id` 过滤会导致统计出的 layer 数量翻倍，误导分析。

- **来源**：2026-04-25-15-2.20-external-review.md

## [External Review] 2.0 `src/part1-fundamentals/ch02-rendering/README.md` — 2026-04-26
- **类型**：P2建议改进
- **位置**：2.0
- **问题**：- [P2][数据/案例支撑][阅读建议]
- 原文位置：阅读建议部分
- 问题描述：阅读建议中虽提供了路径，但未提及 Perfetto 指标（如 `Expected Timeline`）的跨章节对应关系。
- 建议：在阅读建议末尾增加指引，关联具体章节与 Perfetto 关键轨道（如 FrameTimeline 对应 2.4/2.16）。
- **来源**：2026-04-25-15-2.README-external-review.md

## [External Review] 2.0 `src/part1-fundamentals/ch02-rendering/README.md` — 2026-04-26
- **类型**：易读性
- **位置**：阅读建议
- **问题**：缺乏对 Perfetto 核心轨道（FrameTimeline）的引导。
- **建议**：增加对 `Actual/Expected Timeline` 轨道的文字引导。
- **来源**：2026-04-25-15-2.README-external-review.md

## [External Review] 3.1 `src/part1-fundamentals/ch03-input/01-input-dispatch.md` — 2026-04-26
- **类型**：P2建议改进
- **位置**：3.1
- **问题**：- [P2][数据/案例支撑][案例部分]
- 原文问题：部分性能优化结论没有量化数据。
- 证据或观察依据：文章中出现“显著提升”但无具体指标。
- 问题描述：缺乏 Perfetto 或实测数据图表支持。
- 建议：提供具体的 Trace 图表说明或 Benchmark 对比数据。
- **来源**：2026-04-25-15-3.1-external-review.md

## [External Review] 3.1 `src/part1-fundamentals/ch03-input/01-input-dispatch.md` — 2026-04-26
- **类型**：数据支撑
- **位置**：性能段落
- **问题**：需要量化数据
- **建议**：补充实测 Trace 截图
- **来源**：2026-04-25-15-3.1-external-review.md

## [External Review] 4.5 `05-app-memory-optimization.md` — 2026-04-26
- **类型**：P2建议改进
- **位置**：4.5
- **问题**：- [P2][数据/案例支撑][实战建议部分]
- 原文问题：缺乏 `App 内存回收与优化` 在遇到极端情况下的 Perfetto 抓包截图或指标指引。
- 证据或观察依据：实战中，分析 `App 内存回收与优化` 往往依赖 Trace 中的 `sys_memory_trim` 事件。
- 问题描述：纯文字描述排查过程不够直观。
- 建议：补充在 Perfetto 中抓取和过滤 `sys_mem
- **来源**：2026-04-25-15-4.5-external-review.md

## [External Review] 4.5 `05-app-memory-optimization.md` — 2026-04-26
- **类型**：数据与案例缺失
- **位置**：实战部分
- **问题**：未提供 Perfetto `slice` 视角。
- **建议**：补充 `sys_memory_trim` 的抓取与分析截图。
- **来源**：2026-04-25-15-4.5-external-review.md

## [External Review] 4.6 `06-memory-evolution.md` — 2026-04-26
- **类型**：P2建议改进
- **位置**：4.6
- **问题**：- [P2][数据/案例支撑][实战建议部分]
- 原文问题：缺乏 `Android 内存架构演进` 在遇到极端情况下的 Perfetto 抓包截图或指标指引。
- 证据或观察依据：实战中，分析 `Android 内存架构演进` 往往依赖 Trace 中的 `lmkd_kill` 事件。
- 问题描述：纯文字描述排查过程不够直观。
- 建议：补充在 Perfetto 中抓取和过滤 `lmkd_ki
- **来源**：2026-04-25-15-4.6-external-review.md

## [External Review] 4.7 `07-16kb-page-size.md` — 2026-04-26
- **类型**：P2建议改进
- **位置**：4.7
- **问题**：- [P2][数据/案例支撑][实战建议部分]
- 原文问题：缺乏 `16KB Page Size 适配` 在遇到极端情况下的 Perfetto 抓包截图或指标指引。
- 证据或观察依据：实战中，分析 `16KB Page Size 适配` 往往依赖 Trace 中的 `mmap` 事件。
- 问题描述：纯文字描述排查过程不够直观。
- 建议：补充在 Perfetto 中抓取和过滤 `mmap` 
- **来源**：2026-04-25-15-4.7-external-review.md

## [External Review] 4.8 `08-art-generational-gc.md` — 2026-04-26
- **类型**：P2建议改进
- **位置**：4.8
- **问题**：- [P2][数据/案例支撑][实战建议部分]
- 原文问题：缺乏 `ART 世代垃圾回收 (Generational CC)` 在遇到极端情况下的 Perfetto 抓包截图或指标指引。
- 证据或观察依据：实战中，分析 `ART 世代垃圾回收 (Generational CC)` 往往依赖 Trace 中的 `GC: Concurrent Copying` 事件。
- 问题描述：纯文字描述排查
- **来源**：2026-04-25-15-4.8-external-review.md

## [External Review] 5.1 `01-linux-scheduling.md` — 2026-04-26
- **类型**：P2建议改进
- **位置**：5.1
- **问题**：- [P2][数据/案例支撑][实战建议部分]
- 原文问题：缺乏 `Linux 进程调度 (CFS)` 在遇到极端情况下的 Perfetto 抓包截图或指标指引。
- 证据或观察依据：实战中，分析 `Linux 进程调度 (CFS)` 往往依赖 Trace 中的 `sched_switch` 事件。
- 问题描述：纯文字描述排查过程不够直观。
- 建议：补充在 Perfetto 中抓取和过滤 `
- **来源**：2026-04-25-15-5.1-external-review.md

## [External Review] 5.2 `02-eas.md` — 2026-04-26
- **类型**：P2建议改进
- **位置**：5.2
- **问题**：- [P2][数据/案例支撑][实战建议部分]
- 原文问题：缺乏 `EAS (Energy Aware Scheduling)` 在遇到极端情况下的 Perfetto 抓包截图或指标指引。
- 证据或观察依据：实战中，分析 `EAS (Energy Aware Scheduling)` 往往依赖 Trace 中的 `sched_energy_diff` 事件。
- 问题描述：纯文字描述排查过程不
- **来源**：2026-04-25-15-5.2-external-review.md

## [External Review] 5.3 `03-big-little.md` — 2026-04-26
- **类型**：P2建议改进
- **位置**：5.3
- **问题**：- [P2][数据/案例支撑][实战建议部分]
- 原文问题：缺乏 `大小核架构 (big.LITTLE / DynamIQ)` 在遇到极端情况下的 Perfetto 抓包截图或指标指引。
- 证据或观察依据：实战中，分析 `大小核架构 (big.LITTLE / DynamIQ)` 往往依赖 Trace 中的 `sched_migrate_task` 事件。
- 问题描述：纯文字描述排查过程不够
- **来源**：2026-04-25-15-5.3-external-review.md

## [External Review] 5.4 `04-dvfs.md` — 2026-04-26
- **类型**：P2建议改进
- **位置**：5.4
- **问题**：- [P2][数据/案例支撑][实战建议部分]
- 原文问题：缺乏 `DVFS (动态电压频率调节)` 在遇到极端情况下的 Perfetto 抓包截图或指标指引。
- 证据或观察依据：实战中，分析 `DVFS (动态电压频率调节)` 往往依赖 Trace 中的 `cpu_frequency` 事件。
- 问题描述：纯文字描述排查过程不够直观。
- 建议：补充在 Perfetto 中抓取和过滤 `c
- **来源**：2026-04-25-15-5.4-external-review.md

## [External Review] 5.5 `05-thermal.md` — 2026-04-26
- **类型**：P2建议改进
- **位置**：5.5
- **问题**：- [P2][数据/案例支撑][实战建议部分]
- 原文问题：缺乏 `温控机制 (Thermal)` 在遇到极端情况下的 Perfetto 抓包截图或指标指引。
- 证据或观察依据：实战中，分析 `温控机制 (Thermal)` 往往依赖 Trace 中的 `thermal_status` 事件。
- 问题描述：纯文字描述排查过程不够直观。
- 建议：补充在 Perfetto 中抓取和过滤 `th
- **来源**：2026-04-25-15-5.5-external-review.md

## [External Review] 5.6 `06-android-power.md` — 2026-04-26
- **类型**：P2建议改进
- **位置**：5.6
- **问题**：- [P2][数据/案例支撑][实战建议部分]
- 原文问题：缺乏 `Android 耗电分析与管理` 在遇到极端情况下的 Perfetto 抓包截图或指标指引。
- 证据或观察依据：实战中，分析 `Android 耗电分析与管理` 往往依赖 Trace 中的 `battery_stats` 事件。
- 问题描述：纯文字描述排查过程不够直观。
- 建议：补充在 Perfetto 中抓取和过滤 `b
- **来源**：2026-04-25-15-5.6-external-review.md

## [External Review] 5.7 `07-cpu-evolution.md` — 2026-04-26
- **类型**：P2建议改进
- **位置**：5.7
- **问题**：- [P2][数据/案例支撑][实战建议部分]
- 原文问题：缺乏 `CPU 架构演进与性能趋势` 在遇到极端情况下的 Perfetto 抓包截图或指标指引。
- 证据或观察依据：实战中，分析 `CPU 架构演进与性能趋势` 往往依赖 Trace 中的 `cpu_cycles` 事件。
- 问题描述：纯文字描述排查过程不够直观。
- 建议：补充在 Perfetto 中抓取和过滤 `cpu_cycl
- **来源**：2026-04-25-15-5.7-external-review.md

## [External Review] 2.0 `src/part1-fundamentals/ch02-rendering/README.md` — 2026-04-26
- **类型**：P2建议改进
- **位置**：2.0
- **问题**：- [P2][数据/案例支撑][阅读建议]
- 问题描述：阅读建议中虽提供了路径，但未提及 Perfetto 指标（如 `Expected Timeline`）的跨章节对应关系。
- 建议：在阅读建议末尾增加一句话，指引读者在分析具体章节时对应的关键 Perfetto 轨道（如 FrameTimeline 指向 2.4/2.16）。
- **来源**：2026-04-26-10-ch02-rendering-overview-external-review.md

## [External Review] 2.0 `src/part1-fundamentals/ch02-rendering/README.md` — 2026-04-26
- **类型**：案例支撑
- **位置**：阅读建议
- **问题**：缺乏 Perfetto 核心轨道关联描述。
- **建议**：增加对 `Actual/Expected Timeline` 轨道的引导。
- **来源**：2026-04-26-10-ch02-rendering-overview-external-review.md

## [External Review] 2.15 2.15 DMA-BUF、Gralloc 与跨进程图形内存共享 — 2026-04-26
- **类型**：P2建议改进
- **位置**：2.15
- **问题**：- **[P2][数据/案例支撑][16KB 页面开销]**
  - **原文问题**：提到了 16KB 下“更容易出现尾部空洞”，但没有给出一个具体的对比示例。
  - **建议**：补充一个计算例子。例如：一个 256x256 的 RGBA_8888 纹理占 256KB。在 4KB 下正好 64 页；在 16KB 下也是 16 页，没有浪费。但如果是一个带有 2KB metadata 的 bu
- **来源**：2026-04-26-15-2.15-external-review.md

## [Task9 Deep Review] 9.1 ANR 设计思想 — 2026-04-26 — P2-1
- **类型**：版本差异
- **位置**：“ANR 信息的产出 / traces.txt”
- **问题**：Android 10+ trace 文件命名与 Android 12/13 的按进程命名改进被合并成一句，版本线不够清楚。
- **建议**：拆成 Android 10 从单一 traces.txt 转为 /data/anr/anr_*，Android 12/13 再补按进程/时间命名与可靠性改进。

## [Task9 Deep Review] 9.1 ANR 设计思想 — 2026-04-26 — P2-2
- **类型**：知识盲区
- **位置**：“ANR 信息的产出”
- **问题**：只列 traces/event log/dropbox，未提 Android 11+ ApplicationExitInfo 和 Android 16+ system-triggered profiling 作为线上回捞入口。
- **建议**：在概览节补一段“现代线上采集入口”，详细方法跳转到 9.3。

## [Task9 Deep Review] 9.2 ANR 类型与触发条件 — 2026-04-26 — P2-3
- **类型**：数据缺失
- **位置**：“Service Timeout”
- **问题**：`Build.HW_TIMEOUT_MULTIPLIER` 出现但未解释默认值和适用边界。
- **建议**：补充默认值通常为 1，主要用于特殊硬件/测试环境放大 timeout，避免读者误解 20s/200s 不是默认值。

## [Task9 Deep Review] 9.3 ANR 分析方法 — 2026-04-26 — P2-4
- **类型**：源码准确性
- **位置**：“Binder 调用超时 / binder_sample 示例”
- **问题**：示例中的 `code=6` 未说明是 AIDL transaction code，跨版本/接口变更时不应当作固定语义。
- **建议**：补一句：code 需要结合对应版本的 AIDL/Stub 常量反查。


## [External Review] ch03 Input 事件处理 — 2026-04-26
- **类型**：数据支撑
- **位置**：性能优化段落
- **问题**：部分性能优化结论没有量化数据，缺乏 Perfetto 或实测数据图表支持
- **建议**：补充具体的 Trace 图表说明或 Benchmark 对比数据
- **来源**：Gemini 外部 review

## [External Review] ch04 内存管理 — 2026-04-26
- **类型**：数据与案例缺失
- **位置**：实战部分
- **问题**：未提供 Perfetto slice 视角
- **建议**：补充在 Perfetto 中抓取和过滤 meminfo 的具体操作建议及截图
- **来源**：Gemini 外部 review

## [External Review] ch05 CPU 调度与能耗管理 — 2026-04-26
- **类型**：内容补充
- **位置**：阅读建议
- **问题**：提及 Perfetto 时未给出具体 Track 建议
- **建议**：增加 sched_switch 和 cpu_frequency 等 Track 提示
- **来源**：Gemini 外部 review

## [External Review] ch06 存储 I/O — 2026-04-26
- **类型**：实战指导
- **位置**：阅读建议
- **问题**：关于 trace 的阅读建议不够深入，缺少具体系统调用关键字
- **建议**：补充常见 D 状态阻塞点如 fsync、fdatasync、__x64_sys_read 等
- **来源**：Gemini 外部 review

## [Task9 Deep Review] 7.12 View 体系性能优化：布局层级、inflate 与 measure/layout 开销 — 2026-04-26
- **类型**：源码准确性 / 边界条件
- **位置**：L276 `setText()` / `setImageDrawable()` 与 `invalidate()` 的关系
- **问题**：正文把文字、图标变化归为“这些方法内部会自动调用 `invalidate()`”。`TextView#setText()` 在宽高为 `wrap_content`、动态高度变化或重新生成 layout 时会进入 `checkForRelayout()`，并调用 `requestLayout()` + `invalidate()`；不是稳定的 draw-only 路径。
- **建议**：改成条件化说明：固定尺寸且文本 layout 高度不变时可只重绘；文字内容、行数、字体度量或 drawable 尺寸影响测量结果时，需要按 `requestLayout()` 成本分析。

## [Task9 Deep Review] 7.12 View 体系性能优化：布局层级、inflate 与 measure/layout 开销 — 2026-04-26
- **类型**：源码准确性 / Trace 观察点
- **位置**：L429 AsyncLayoutInflater 后台线程描述
- **问题**：正文说 Perfetto 中通常看到 `AsyncLayoutInflater` 的 `HandlerThread`。AndroidX `AsyncLayoutInflater` 当前实现使用单例 `InflateThread extends Thread` + `ArrayBlockingQueue`，完成后通过 Handler / 可选 Executor 回调；不是 `HandlerThread`。
- **建议**：把 Trace 观察点改成“后台 InflateThread / AsyncLayoutInflater 任务线程”，同时说明回调是否回主线程取决于是否传入 `callbackExecutor`。

## [External Review] 16.1 Google 官方优化 — 2026-04-26
- **类型**：源码扩展
- **位置**：Binder 线程池与优先级继承
- **问题**：提到 DEFAULT_MAX_BINDER_THREADS = 15 但未指明 ioctl 调用点
- **建议**：补充 BINDER_SET_MAX_THREADS ioctl 调用细节
- **来源**：Gemini 外部 review

## [External Review] 16.2 版本变更 — 2026-04-26
- **类型**：深度扩展
- **位置**：缓存应用冻结
- **问题**：可以略微提及 cgroup freezer 机制
- **建议**：添加一两句话说明底层是基于 cgroup v2 的机制
- **来源**：Gemini 外部 review

## [External Review] 16.3 AOSP 编译与环境搭建 — 2026-04-26
- **类型**：细节补充
- **位置**：adb remount
- **问题**：未提及 Dynamic Partitions 空间不足问题
- **建议**：加上 fastboot 调整分区大小或清理的简短提示
- **来源**：Gemini 外部 review

## [External Review] 16.4 Kernel 6.12 性能 — 2026-04-26
- **类型**：深度扩展
- **位置**：EEVDF 章节
- **问题**：建议深化对 lag 机制的定义
- **建议**：引用 kernel/sched/fair.c 中 update_curr() 时的 vruntime 更新逻辑
- **来源**：Gemini 外部 review

## [External Review] 16.5 Android 17 API 37 性能变更 — 2026-04-26
- **类型**：机制补充
- **位置**：DeliQueue
- **问题**：未明确指出同步屏障在 DeliQueue 中的行为如何演进
- **建议**：添加一句关于 DeliQueue 对 Sync Barrier 兼容实现的说明
- **来源**：Gemini 外部 review

## [External Review] 17.1 OEM 优化通用思路 — 2026-04-26
- **类型**：数据支撑
- **位置**：应用冻结技术
- **问题**：缺乏 Perfetto trace 的实际对应
- **建议**：提供一段具体的描述，告知读者在 Perfetto 中冻结前后 CPU track 的表现差异
- **来源**：Gemini 外部 review

## [External Review] 17.2 SoC 平台差异 — 2026-04-26
- **类型**：案例补充
- **位置**：GPU 差异对渲染性能的影响
- **问题**：Adreno 和 Mali 的 gpu_render_stages 差异未列明
- **建议**：提供具体的 stage 名字差异表（如 Adreno 报 Binning，Mali 报 Vertex/Tiler/Fragment）
- **来源**：Gemini 外部 review

## [External Review] 17.3 行业案例 — 2026-04-26
- **类型**：内容补充
- **位置**：折叠屏与大屏设备
- **问题**：建议对 Configuration Change 进行更深入的 API 级解释
- **建议**：补充 android:configChanges="screenSize|smallestScreenSize|screenLayout" 最佳实践
- **来源**：Gemini 外部 review

## [Task9 Deep Review] 8.6 Kotlin Coroutine 性能实践 — 2026-04-26
- **类型**：数据缺失
- **位置**：“withContext 的实际开销”与“版本演进”中 Kotlin 2.2 / 15% 性能提升描述
- **问题**：正文把“多并发网络请求场景响应聚合时间缩短约 15%”标为已验证，但公开 kotlinx.coroutines 1.10/1.11 release notes 只看到 Kotlin 编译器版本更新、调度 bugfix 和文档更新，没有给出这组 15% benchmark。该数字可以保留为待验证材料，但不应继续写成官方已验证结论。
- **建议**：补充明确来源、测试设备、coroutines 版本、JVM/ART 版本、并发请求模型和统计口径；无法补齐时改为“社区 benchmark 待核验”，并删除“官方博客已验证”标注。

## [Task9 Deep Review] 8.6 Kotlin Coroutine 性能实践 — 2026-04-26
- **类型**：源码准确性 / 边界条件
- **位置**：“各 Dispatcher 在 Trace 中的对应”表格
- **问题**：表格写 Default 线程数 = CPU 核心数，但正文前面已经说明 blocking compensation 会让 worker 数短时高于核心数；IO 又和 Default 共享 worker 池。表格当前写法容易让读者误判“线程数多于核心数 = 泄漏”。
- **建议**：改成“Default 的 CPU 并行许可接近核心数；实际 DefaultDispatcher-worker-N 可因 IO / blocking compensation 超出核心数，需结合任务类型和时间窗判断”。

## [Task9 Deep Review] 8.6 Kotlin Coroutine 性能实践 — 2026-04-26
- **类型**：队列元数据错误
- **位置**：metadata/queue.json section=8.6 的 External Review 条目
- **问题**：该条目的所有 P1 证据都指向 05-case-studies.md / ProfilingManager 段落，不属于 8.6 协程性能章节。
- **建议**：已将该条 queue 从 8.6 改挂到 8.5，避免 8.6 被无关 P1 阻塞。

## [Task9 Deep Review] 2.17 Frame Pacing Library 与帧节奏控制 — 2026-04-26
- **类型**：数据/Trace 配置缺失
- **位置**：验证路径中的 `adb shell perfetto ...` 示例
- **问题**：正文随后直接查询 `actual_frame_timeline_slice` / `expected_frame_timeline_slice`，但示例命令只列出 atrace 类别，没有显式启用 `android.surfaceflinger.frametimeline` 数据源。读者照抄后可能拿不到 FrameTimeline 表。
- **建议**：补一段 TraceConfig 示例，显式加入 `data_sources { config { name: "android.surfaceflinger.frametimeline" } }`，并保留 ftrace / atrace 类别用于和调度、SurfaceView buffered frames 对照。

## [Task9 Deep Review] 1.10 ContentProvider 性能与优化 — 2026-04-26
- **类型**：源码准确性
- **位置**：L319「多进程 ContentProvider 的适用场景与注意事项」
- **问题**：正文仍保留 `Process.isProviderProcess()` 这个待验证 API 名。Android SDK 没有该公开方法，虽然已标 `[待验证]`，但放在优化建议里仍容易被照抄。
- **建议**：改成 `Application.getProcessName()` 或读取当前进程名后与 manifest `android:process` 字符串匹配；删除不存在 API 名。

## [Task9 Deep Review] 2.13 图形缓冲区管理 (BufferQueue) — 2026-04-26
- **类型**：数据缺失
- **位置**：L276-L304「在 Perfetto 中怎么读 BufferQueue」
- **问题**：正常/异常 BufferQueue 场景仍是 `[图]` 与 `[需补充素材]` 占位，缺少真实 Trace 证据。
- **建议**：补同机型、同刷新率下的正常滑动 trace 与 dequeueBuffer 长等待 trace，各标出 `queueBuffer()`、`QueuedBuffer - <window>BLAST#...`、FrameTimeline actual present、release fence / dequeue wait 的对应关系。

## [Task9 Deep Review] 2.11 2.11 Flutter 渲染管线与性能 — 2026-04-26
- **类型**：数据缺失
- **位置**：L263
- **问题**：移动 GPU shader 编译“10-100 倍、数百毫秒”的数字没有绑定设备、驱动、shader 类型或 benchmark 来源。
- **建议**：补一条可复现实验或官方 / issue tracker 依据；如果没有稳定来源，删除固定倍数，改成“首帧 shader 编译可能拉长 Raster 线程，需用目标机型 trace 验证”。

## [Task9 Deep Review] 2.11 2.11 Flutter 渲染管线与性能 — 2026-04-26
- **类型**：交叉引用
- **位置**：frontmatter related_chapters 与 L343-L352
- **问题**：正文未引用已 finalized 的 §18.12 Flutter 渲染管线；§18.12 已按 Flutter 3.29+ merged model 写成 Main(UI+Platform)/Raster/IO，而本章仍按旧四线程模型展开，两章口径冲突。
- **建议**：把 §18.12 加入 related_chapters，并在修文时以 §18.12 的 3.29+ 线程模型为主口径；本章保留旧模型时标注版本边界。


## [Task9 Deep Review] 2.6 SurfaceFlinger 与合成 — 2026-04-26
- **类型**：数据缺失
- **位置**：L249-L251 HWC 合成 Track
- **问题**：“Device 合成 doComposition 几乎不消耗时间、通常不到 1ms”缺少设备、Trace 和版本条件。HWC HAL 调用本身也可能阻塞，vendor composer 内部耗时无法只用这句话概括。
- **建议**：改成条件化表述；给一段 Pixel/参考设备 Trace 或 dumpsys SurfaceFlinger 观察点，区分 SF 调用耗时、present fence、HWC 内部硬件处理时间。


## [Task9 Deep Review] 2.6 SurfaceFlinger 与合成 — 2026-04-26
- **类型**：版本差异
- **位置**：版本演进小节
- **问题**：章节覆盖 Android 12-16，但未提 Android 15 ARR/可变刷新率对 Scheduler、present hint、FrameTimeline 分析口径的影响。
- **建议**：在版本演进中补一行：Android 15 ARR 使 VSync 调度与刷新率切换解耦，SurfaceFlinger 分析需结合 2.18/2.19。


## [Task9 Deep Review] 3.1 Input 事件分发全流程 — 2026-04-26
- **类型**：版本差异
- **位置**：L586-L606 InputFlinger 角色与版本边界
- **问题**：正文保留“InputFlinger 是否独立进程”待验证，但 AOSP android-14/16 的 inputflinger/Android.bp 仍有 TODO(b/23084678): Move inputflinger to its own process，且 inputflinger binary 在 checkinput 中标注 currently unused。
- **建议**：把 AOSP 默认事实写清：12-16 主线仍以 libinputflinger 方式进入 system_server；独立进程只作为产品/OEM 形态待核验。


## [Task9 Deep Review] 3.1 Input 事件分发全流程 — 2026-04-26
- **类型**：知识盲区
- **位置**：InputChannel 与 Socket Pair 小节
- **问题**：正文覆盖正常分发，但未覆盖 InputChannel 断开、BROKEN/ZOMBIE 连接、应用进程死亡后的清理路径。线上输入无响应和窗口泄漏问题常需要这条失败路径。
- **建议**：补 InputDispatcher 发现 socket 断连、移除 connection、通知策略层和窗口状态刷新的最小流程。


## [Task9 Deep Review] 4.4 Low Memory Killer — 2026-04-26
- **类型**：数据缺失
- **位置**：L365 Perfetto 截图占位
- **问题**：文中已留“待补充 Perfetto 截图”，但没有给出 lmkd kill、MemAvailable/Cached/SwapFree、冷启动三者的同一时间轴例子。
- **建议**：补一张真实 Trace 或给 trace_processor 查询，验证 kill 后 reclaim 与冷启动的时间关系。

## [Task9 Deep Review] 2.12 Window Manager Service 与窗口管理 — 2026-04-26
- **类型**：数据缺失
- **位置**：StartingWindow 与启动性能 / Perfetto 表现
- **问题**：章节有 StartingWindow Trace 截图占位，但没有给出 addStartingWindow、finishDrawing/reportDraw、removeStartingWindow 与 App 首帧的同一时间轴。
- **建议**：补一段真实 Perfetto 或 trace_processor 查询，至少包含 system_server、Shell/SystemUI starting surface、App 主线程首帧、SurfaceFlinger transaction/latch。

## [Task9 Deep Review] 2.20 多窗口与桌面模式渲染性能 — 2026-04-26
- **类型**：数据缺失
- **位置**：dumpsys SurfaceFlinger / Perfetto 观察面占位
- **问题**：正文已给出全屏、分屏、外接显示器三类分析口径，但 `dumpsys SurfaceFlinger` layer 对比截图与 FrameTimeline/layer snapshot 对照图仍是占位。当前结论方向正确，缺少可复跑的 trace/dumpsys 样例支撑。
- **建议**：补一组同设备全屏/分屏/外接显示器的 `dumpsys SurfaceFlinger` 与 Perfetto 片段，至少包含 layer 数、display_id、compositionType、FrameTimeline jank_type。

## [Task9 Deep Review] 7.3 卡顿分析方法论 — 2026-04-26
- **类型**：版本差异
- **位置**：frontmatter applicable_versions 与 FrameMetrics 小节
- **问题**：frontmatter 写 `Android 8 (API 26) - Android 16 (API 36)`，正文 FrameMetrics 小节明确使用 API 24+ 的 `Window.OnFrameMetricsAvailableListener`，并说明 `FrameMetrics.DEADLINE` API 31+。版本边界在元数据和正文之间不一致。
- **建议**：二选一：把 applicable_versions 下限改为 Android 7/API 24；或在 FrameMetrics 小节开头说明本节主分析目标为 API 26+，线上 FrameMetrics 监控另从 API 24 起可用。

## [Task9 Deep Review] 15.3 性能指标体系 — 2026-04-26
- **类型**：数据缺失
- **位置**：Click-to-Display 段落（约 L235-L239）
- **问题**：100ms/200ms 触摸响应阈值被写成 Google 内部测试标准，但正文保留“待验证”，缺少公开来源或测试方法。
- **建议**：若作为行业经验，应改成团队 SLA/RAIL 类经验阈值并补来源；若保留 Google 表述，需要补公开文档或一手测试材料，并说明高刷设备、测量工具和统计口径。

## [Task9 Deep Review] 15.3 性能指标体系 — 2026-04-26
- **类型**：数据缺失
- **位置**：Active / Idle Power 段落（约 L406-L411）
- **问题**：Perfetto Power Rails / Energy Consumer 观察点成立，但仅停在 track 名称，缺少一张示例 trace 或采集配置，读者无法校准 mW/energy counter 的解读边界。
- **建议**：补一段最小 Perfetto 配置或截图说明，标注 Power Rails、Battery、CPU Frequency、Energy Consumer 的单位和对齐方式。

## [Task9 Deep Review] 19.01 APM 全景图与分类体系 — 2026-04-26
- **类型**：交叉引用错误
- **位置**：四类能力对照表 Benchmark 工具行（约 L105-L111）
- **问题**：19.21 已把 AndroBench 降级为历史工具，并推荐 CPDT / PCMark Storage 2.0 等当前存储基线；19.01 仍把 AndroBench 和 Macrobenchmark、Geekbench、PerfDog 并列，容易被读成当前推荐入口。
- **建议**：与 19.21 对齐：将 AndroBench 标注为“历史旧报告复盘”，或在代表工具中改为 CPDT / PCMark Storage 2.0，并把 AndroBench 放到边界说明。


## [Task9 Deep Review] 2.9 渲染机制的版本演进 — 2026-04-27
- **类型**：数据缺失
- **位置**：L252 ARR 自适应刷新率
- **问题**：正文写 LTPO 静态场景显示侧功耗“通常能降到原先的一半左右”，但没有绑定面板、亮度、刷新率档位、DDIC/SoC、测试工具或公开数据来源。
- **建议**：补一组可复现实测条件或官方/OEM 数据；如果没有稳定来源，改成“可能显著降低显示侧功耗，幅度取决于面板与系统策略”，并把量化结论留给案例。

## [Task9 Deep Review] 2.16 Sync Fence 框架与帧同步机制 — 2026-04-27
- **类型**：版本差异
- **位置**：frontmatter applicable_versions
- **问题**：frontmatter 写 `Android 7 (API 24) - Android 17 (API 37)`，但 `last_verified_against` 只到 AOSP android-16.0.0_r1，正文也没有 Android 17 的 fence/HWUI/Composer 差异说明。
- **建议**：二选一：把适用范围收敛到 Android 16；或补 Android 17 tag / API 37 的 Fence、HWUI Vulkan、HWC3/Composer 相关核验结果。

## [Task9 Deep Review] 2.16 Sync Fence 框架与帧同步机制 — 2026-04-27
- **类型**：数据缺失
- **位置**：在 Perfetto 里怎么读 Fence
- **问题**：章节给出了 acquire/release/present fence 的判断方向，但没有落到具体 Trace 观察点、slice 名称、FrameTimeline 字段或 trace_processor 查询，读者难以复跑验证。
- **建议**：补一个最小 Perfetto 案例或 SQL：串起 `queueBuffer`/`latchBuffer`/`presentDisplay`、GPU busy、FrameTimeline actual/expected 和 BufferQueue slot 状态。

## [Task9 Deep Review] 18.9 Vulkan 原生渲染管线 — 2026-04-27
- **类型**：交叉引用
- **位置**：L60、L428-L429
- **问题**：`[2.14 图形 API 演进](14-graphics-api-evolution.md)` 与 `[2.13 图形缓冲区管理](13-buffer-queue.md)` 在 ch18 目录下解析到不存在文件；实际目标在 `src/part1-fundamentals/ch02-rendering/14-graphics-api-evolution.md` 与 `src/part1-fundamentals/ch02-rendering/13-buffer-queue.md`。
- **建议**：改成正确相对路径，或改用全书统一的章节引用格式，避免发布后链接断开。


## [Task9 Deep Review] 14.4 dumpsys 系列命令 — 2026-04-27
- **类型**：版本差异
- **位置**：~L80-L95
- **问题**：`oom_adj` 数值以 Android 10+ 为例，未提及 Android 15+ LMKD 转向 `oom_score_adj`
- **建议**：补充"Android 15+ LMKD 决策更多依赖 `oom_score_adj`（`/proc/<pid>/oom_score_adj`），`dumpsys activity processes` 中的 `oom_adj` 仍可参考但非唯一决策输入"

## [Task9 Deep Review] 14.4 dumpsys 系列命令 — 2026-04-27
- **类型**：版本差异
- **位置**：~L235
- **问题**：`dumpsys batterystats --enable full-wake-history` 在部分 Android 12+ 设备上已 deprecated
- **建议**：补充版本可用性说明或标注"Android 12 以下可用"

## [Task9 Deep Review] 14.4 dumpsys 系列命令 — 2026-04-27
- **类型**：数据支撑
- **位置**：~L70-L75
- **问题**：`exit-info` 保留条数未量化
- **建议**：补充"Android 16 上默认保留最近 10 条退出记录（MAX_EXIT_INFOS_PER_PACKAGE=10）"

## [Task9 Deep Review] 14.6 自动化测试工具 — 2026-04-27
- **类型**：版本差异
- **位置**：全文
- **问题**：未提及 16KB page size 对 Macrobenchmark/Microbenchmark 的影响
- **建议**：在 CompilationMode 段或 CI 段补充 benchmark 基线需重新建立，CompilationMode.Full 的 .odex 产物体积和编译耗时可能显著增加

## [Task9 Deep Review] 14.6 自动化测试工具 — 2026-04-27
- **类型**：知识盲区
- **位置**：~SoloPi 段
- **问题**：遗漏 SoloPi 视觉拆帧算法原理
- **建议**：补一段 SoloPi 视觉拆帧技术原理（像素差异检测/录屏帧 diff）和与 Macrobenchmark FrameTimingMetric 的精度对比

## [Task9 Deep Review] 14.6 自动化测试工具 — 2026-04-27
- **类型**：数据支撑
- **位置**：PowerMetric 段
- **问题**：未提及 CI 中设备白名单筛选方法
- **建议**：补"CI 设备选型可用 `adb shell dumpsys powerhal` 确认 power rail 支持"

## [Task9 Deep Review] 14.6 自动化测试工具 — 2026-04-27
- **类型**：交叉引用
- **位置**：StartupMode 段
- **问题**："第 8 章讨论的三种启动类型"未给小节号
- **建议**：改为"第 8 章 8.3 节讨论的三种启动类型"

## [Task9 Deep Review] 14.10 eBPF/BPF — 2026-04-27
- **类型**：原理链
- **位置**：~L145
- **问题**：kprobe 示例中 simpleperf `--tp-filter` 联用 kprobe 参数过滤语法待验证
- **建议**：确认 simpleperf 新版本是否支持 kprobe 参数提取 + `--tp-filter`，否则改为 bpftrace 示例或标注伪代码

## [Task9 Deep Review] 14.10 eBPF/BPF — 2026-04-27
- **类型**：版本差异
- **位置**：~L170
- **问题**：Android 16 内核分支映射只提 6.12 未提 6.6 向下兼容分支
- **建议**：补充 GKI 分支选择逻辑或加"主分支"限定

## [Task9 Deep Review] 18.11 ANGLE（GLES-over-Vulkan 翻译层） — 2026-04-27
- **类型**：数据缺失
- **位置**：性能特征 / 在 Perfetto 中识别 ANGLE（L174-L235）
- **问题**：章节已经把 ANGLE 性能结论收敛为定性判断，但 shader 首编、pipeline cache 冷启动、native GLES 与 ANGLE 的对比缺少同设备 trace 或 AGI frame capture 证据。当前只能指导排查方向，不能支撑性能预算判断。
- **建议**：补一组同设备 native GLES vs ANGLE 的冷启动/暖启动对比：记录 GL_RENDERER、ANGLE package 版本、shader/pipeline cache 状态、首帧或场景切换耗时，并用 Perfetto/AGI 关联 vkQueueSubmit、RenderThread 与 GPU slice。

## [Task9 Deep Review] 18.14 Camera 渲染管线 — 2026-04-27
- **类型**：版本差异
- **位置**：Stream Use Case 常量定义表（L95-L105）
- **问题**：表格覆盖 DEFAULT/PREVIEW/STILL_CAPTURE/VIDEO_RECORD/PREVIEW_VIDEO_STILL/VIDEO_CALL，但 Android 14-16 的 CameraMetadata 还包含 SCALER_AVAILABLE_STREAM_USE_CASES_CROPPED_RAW=0x6 以及 vendor range。章节适用到 Android 16，表题写成“常量定义”时容易被读成完整枚举。
- **建议**：补一行 CROPPED_RAW（RAW_SENSOR/RAW10/RAW12 场景，配合 SCALER_RAW_CROP_REGION）和一行 vendor range，或把表题改为“常见非 RAW stream use case”。

## [Task9 Deep Review] 18.17 Hardware Buffer Renderer — 2026-04-27
- **类型**：版本差异
- **位置**：wide color 与 HDR 要分开看（L270-L279）
- **问题**：章节提到 Android 15/API 35 之后的 SurfaceControl.Transaction.setDesiredHdrHeadroom()，但 AOSP android-15/16 current API 中该方法带 @FlaggedApi("com.android.graphics.hwui.flags.limited_hdr")。实际可用性受平台 flag / SDK 暴露状态影响，不能只按 API level 判断。
- **建议**：在 HDR 小节补充“setDesiredHdrHeadroom 是 flagged API；量产适配需检测 SDK/flag/厂商开放情况”，并给出 fallback：只设置 dataspace 或继续使用 setExtendedRangeBrightness()。

## [Task9 Deep Review] 4.7 16KB Page Size 与 Android 性能 — 2026-04-27
- **类型**：数据缺失
- **位置**：L82-L93 / L277
- **问题**：官方 16KB 性能数字已列出，但测试设备、Android build、样本 App、4KB/16KB 对照方法没有落到正文；Perfetto 位置也留在“待补充”。
- **建议**：补一个最小复现实验：同一 App、同一设备 4KB/16KB 各抓冷启动 trace，记录 PAGE_SIZE、build fingerprint、min_flt/maj_flt、启动耗时与 simpleperf TLB 事件可用性。

## [Task9 Deep Review] 5.7 CPU 相关的版本演进 — 2026-04-27
- **类型**：版本差异
- **位置**：L338-L340 趋势总结
- **问题**：“后台网络异常提示（15）”被放进“用户可见性越来越高”趋势里。Android 15 的后台网络限制主要表现为 App 侧 UnknownHostException / IOException，不是通用用户可见提示。
- **建议**：把 Android 15 放回“平台约束”维度；用户可见性趋势保留 FGS 通知、FGS Task Manager、Play listing 警告等有明确用户界面的机制。

## [Task9 Deep Review] 5.7 CPU 相关的版本演进 — 2026-04-27
- **类型**：交叉引用一致性
- **位置**：L350-L352 Perfetto 观察
- **问题**：本章仍写“System Server 进程中的 JobScheduler track”即可观察 bucket/调度间隔；5.10 已把 JobScheduler 观测拆成 statsd 的 android_job_scheduler_states 与 atrace ss 的 android_job_scheduler_events。两章口径不一致。
- **建议**：同步 5.10 的观测口径：pending/constraint/bucket 用 statsd atom 表，system_server 执行事件用 atrace ss；不要把两类数据都称为一个 JobScheduler track。

## [Task9 Deep Review] 5.10 JobScheduler/WorkManager 调度与后台任务性能 — 2026-04-27
- **类型**：版本差异
- **位置**：L477 调度方式选择表
- **问题**：“需要精确定时 → AlarmManager OnAlarmListener → Android 17 进程内回调”版本边界错误。OnAlarmListener 不是 Android 17 才出现；exact alarm 权限例外也应按 Android 12+ exact alarm 文档说明。
- **建议**：改成“AlarmManager exact alarm + OnAlarmListener（listener 形态不需要 SCHEDULE_EXACT_ALARM，按官方 exact alarm 文档验证）”，不要标 Android 17。

## [Task9 Deep Review] 5.10 JobScheduler/WorkManager 调度与后台任务性能 — 2026-04-27
- **类型**：数据/指标命名
- **位置**：L442-L449 Android Vitals 监控指标
- **问题**：“WakeLock 停滞率：因 WakeLock 导致的 ANR 比例”“JobScheduler/AlarmManager 触发频率”不是当前 Play Android Vitals 对 excessive wake locks 的准确指标表达。
- **建议**：按 Android Vitals 官方口径改为 excessive partial wake locks / non-exempt wake lock session threshold，并区分 Play 政策指标、batterystats 本地聚合、Perfetto trace 观测。

## [Task9 Deep Review] 2.12 Window Manager Service 与窗口管理 — 2026-04-27
- **类型**：原理断裂
- **位置**：L495-L497「WMS 与 Input 系统的协作」
- **问题**：“InputDispatcher 从 WMS 获取当前所有可见 Window 的区域和 Z-order”容易被理解成每次触摸时同步向 WMS 拉取窗口列表。现代实现更接近 WMS/InputMonitor 维护 input window info，经 SurfaceControl/WindowInfo/IMS 等路径把快照推送给 native InputDispatcher，InputDispatcher 按已缓存的 WindowInfo 做 hit-test。
- **建议**：补一句说明这是窗口状态变化时推送/同步的 WindowInfo 快照，不是触摸事件到来时的逐次 WMS 查询。

## [Task9 Deep Review] 1.10 ContentProvider 性能与优化 — 2026-04-27
- **类型**：版本差异
- **位置**：L479-L481 Android 8.0 后台限制
- **问题**：“后台 App 的 ContentResolver.query() 调用受到限制、目标 provider 后台时优先级降低”缺少官方/AOSP 锚点。Android 8 后台执行限制主要针对后台 service 与隐式 broadcast；ContentProvider 相关更明确的变化是 content URI observer/notify 的 authority 有效性约束，以及后台任务需要改走 JobScheduler/WorkManager 的间接影响。
- **建议**：删除“query 优先级降低”的确定性说法，改为后台执行限制对发起查询的组件生命周期产生间接影响，并补充 API 26 与 ContentObserver/notifyChange authority 校验相关变化。

## [Task9 Deep Review] 1.10 ContentProvider 性能与优化 — 2026-04-27
- **类型**：版本差异
- **位置**：L543-L545 Photo Picker 版本线
- **问题**：Photo Picker 是 Android 13/API 33 引入；Android 14/API 34 的重点是 Selected Photos Access / `READ_MEDIA_VISUAL_USER_SELECTED` 等更细粒度媒体权限。当前写成 Android 14 引入 Photo Picker。
- **建议**：把版本节点拆成 Android 13 Photo Picker、Android 14 Selected Photos Access；说明它们如何替代直接访问 MediaStore Provider 的部分场景。

## [Task9 Deep Review] 2.1 Android 渲染架构全景 — 2026-04-27
- **类型**：数据缺失
- **位置**：L545-L574 Vulkan 性能优势
- **问题**：Vulkan 性能优势主要是泛化判断，末尾仍标 `[待验证]`，缺少同设备、同页面、同 trace 配置下 `skiagl` vs `skiavk` 的 CPU submit、RenderThread、GPU slice、帧 deadline 数据。
- **建议**：补一组可复现实验：记录设备/GPU/系统版本，分别用 `debug.hwui.renderer=skiagl` 与 `skiavk` 跑同一复杂 UI 场景，给出 RenderThread dur、GPU busy、jank count、FrameTimeline deadline 对比。

## [Task9 Deep Review] 2.1 Android 渲染架构全景 — 2026-04-27
- **类型**：版本差异
- **位置**：L614-L616 Android 8/10 渲染管线版本节点
- **问题**：“Android 8.0 引入 SurfaceFlinger 预合成重构”“Android 10 引入 Skia 渲染后端统一”缺少源码或官方版本锚点，且容易与 HWC2、CompositionEngine、HWUI Skia renderer 的不同演进线混在一起。
- **建议**：补准确版本线：HWC2/Composer HAL、CompositionEngine/RenderEngine、HWUI SkiaGL/SkiaVK 分别列锚点，避免用单句概括不同子系统。


## [Task9 Deep Review] 7.5 优化策略 — 2026-04-27
- **类型**：数据缺失
- **位置**：L406-L422 实际优化案例
- **问题**：WeSing、电商详情页案例给出卡顿率、帧率和 measure 耗时，但缺设备型号、刷新率、系统版本、测试轮次、trace 片段或原始报告页码。当前只能作为经验案例，不能支撑可复跑的技术结论。
- **建议**：补 before/after trace、测试条件和指标定义；若无法补齐，把这些数字标成“来源案例数据”，不要作为通用优化收益。

## [Task9 Deep Review] 19.0 第 19 章：APM 工具与性能监控生态 — 2026-04-27
- **类型**：版本差异
- **位置**：L64 / L97 androidx.tracing 2.0 与 Perfetto 格式
- **问题**：正文写“Tracing SDK 2.0 支持 Perfetto 格式”，但缺少 2.0.0-alpha 版本边界和作用域说明。AndroidX Tracing 2.0 当前主要是 in-process tracing / tracing-wire / TraceSink 方向，不等同于稳定版 `Trace.beginSection` 或系统级 Perfetto 数据源。
- **建议**：标注 2.0.0-alpha 的时间点、artifact（如 tracing-wire）和“不替代系统 trace”的边界；稳定接入仍区分 `androidx.tracing:tracing`、`tracing-perfetto`、平台 `android.os.Trace`。

## [Task9 Deep Review] 19.21 Benchmark 应用（Geekbench、安兔兔、3DMark、PCMark、Vellamo） — 2026-04-27
- **类型**：数据缺失
- **位置**：frontmatter sources / L132-L138 PCMark、CPDT、Speedometer、JetStream 2
- **问题**：frontmatter 只列 Geekbench 和 3DMark 官方来源，但正文还对 PCMark Storage、CPDT、Speedometer 3.0、JetStream 2、安兔兔和 Vellamo 状态做了判断，缺对应一手资料或版本说明。
- **建议**：补 UL PCMark/3DMark Android 文档、Speedometer 3.0 官方说明、CPDT 项目页、安兔兔版本口径来源；Vellamo 只保留历史状态说明。

## [Task9 Deep Review] 19.21 Benchmark 应用（Geekbench、安兔兔、3DMark、PCMark、Vellamo） — 2026-04-27
- **类型**：交叉引用
- **位置**：README L123；src/SUMMARY.md L254；本节标题
- **问题**：README 把 19.21 写成“Benchmark 应用（Geekbench 6、安兔兔、3DMark、PCMark、Speedometer）”，SUMMARY 和本节标题仍写 Vellamo。正文又把 Vellamo降为历史工具，并建议现代 Web/WebView 基线看 Speedometer 3.0，三个位置命名不一致。
- **建议**：统一标题。建议标题改成“Benchmark 应用（Geekbench、安兔兔、3DMark、PCMark、Speedometer）”，正文保留 Vellamo 为历史工具；SUMMARY 同步更新。

## [Task9 Deep Review] 13.9 Android Tracing 基础设施：atrace、ftrace 与 Perfetto 数据采集原理 — 2026-04-27
- **类型**：数据缺失
- **位置**：L86 / L394
- **问题**：function tracer 10-15% 开销未给出来源。
- **建议**：补充平台、内核版本、benchmark 方法；无法确认则保留 [待验证]。


## [Task9 Deep Review] 13.9 Android Tracing 基础设施：atrace、ftrace 与 Perfetto 数据采集原理 — 2026-04-27
- **类型**：源码准确性
- **位置**：L156
- **问题**：trace_marker 格式只列 B/E/C，未覆盖 S/F/N 等异步或 instant 事件格式。
- **建议**：补充常见格式，并说明 Perfetto 会映射到 slice、counter 或 async slice。


## [Task9 Deep Review] 13.9 Android Tracing 基础设施：atrace、ftrace 与 Perfetto 数据采集原理 — 2026-04-27
- **类型**：数据缺失
- **位置**：L426
- **问题**：UprobeStats “性能开销 < 1%”缺少公开 benchmark 来源。
- **建议**：给出测试条件或改成 [待验证]。


## [Task9 Deep Review] 14.9 Android Camera 性能与 Perfetto 分析 — 2026-04-27
- **类型**：版本差异
- **位置**：L354
- **问题**：Camera BufferQueue “通常 3-4 个”缺少 producer/consumer 协商口径。
- **建议**：改成由 maxDequeued/maxAcquired/spare buffer 协商决定，预览常见 3 个，厂商或流类型可不同。


## [Task9 Deep Review] 14.9 Android Camera 性能与 Perfetto 分析 — 2026-04-27
- **类型**：工具版本
- **位置**：L291-L296
- **问题**：Perfetto Python SDK 示例强依赖 trace_processor_shell bin_path。
- **建议**：说明 bin_path 可选，默认可使用 SDK 内置引擎；需要本地二进制时再指定。


## [Task9 Deep Review] 14.9 Android Camera 性能与 Perfetto 分析 — 2026-04-27
- **类型**：版本差异
- **位置**：GFXReconstruct 段落
- **问题**：GFXReconstruct 对 Camera 场景的适用边界和版本要求未写清。
- **建议**：补充 Vulkan/GLES 支持差异、gfxrecon-convert 版本要求和 YUV/外部纹理限制。


## [Task9 Deep Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-04-27
- **类型**：版本差异
- **位置**：L199-L203
- **问题**：ProfilingTrigger 冷启动产物写成 newly started system trace，官方口径更接近 running trace snapshot/系统触发产物，需核对。
- **建议**：改为按 API reference 的 artifact 描述逐项列出，无法确认的产物类型标 [待验证]。


## [Task9 Deep Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-04-27
- **类型**：知识盲区
- **位置**：L416
- **问题**：Network Security Configuration/ECH 只列资料，正文缺少 domainEncryption 配置和 CT/ECH targetSdk 门控说明。
- **建议**：补充 <domainEncryption> 示例，并区分 CT 默认启用、ECH opportunistic 使用和 localhost 例外。

## [Task9 Deep Review] 5.12 Thermal 管控深度：从内核子系统到 ADPF 主动降频 — 2026-04-27
- **类型**：数据缺失
- **位置**：L612 环境温度影响结论
- **问题**：“环境温度每升高 5°C，thermal throttling 触发时间大约提前 20-30%”缺少设备、负载、散热条件、样本数和来源。
- **建议**：补充可复现实验条件和原始数据；如果没有数据，改成定性结论。
- **类型**：数据缺失
- **位置**：L651-L652 调度策略/预判式降载收益
- **问题**：“功耗差异可达 30%”“持续性能窗口延长 40-60%”没有绑定 SoC、workload、温控阈值和测量工具。
- **建议**：补 Perfetto + power rail / Battery Historian / vendor thermal log 对照，或标成案例数据并给出处。

## [Task9 Deep Review] 8.3 启动优化策略 — 2026-04-27
- **类型**：数据缺失
- **位置**：L342 DAG 初始化框架收益
- **问题**：“Pixel 6 / Android 13 / 12 个 SDK / 37.5% 提升”缺少可追溯来源，且把 Google I/O 演示与阿里实践混成一个测试环境。
- **建议**：补原始演讲页码/报告链接/实验脚本；无法追溯时删掉具体设备与百分比，只保留“并行受依赖图和设备并发度限制”的结论。

## [Task9 Deep Review] 19.11 JankStats — 2026-04-27
- **类型**：数据缺失
- **位置**：L107-L112 / L149-L151
- **问题**：最小 DTO 只拷贝 `isJank`、`frameDurationUiNanos` 和 `states`，没有保留 `expectedFrameDurationUiNanos` 或等价刷新率口径。线上回放时只能看到“被判 jank”，看不到当前阈值基线，60/90/120Hz 设备很难横向比较。
- **建议**：DTO 或聚合 schema 增加 `expectedFrameDurationUiNanos` / `expected_frame_ms` / `refresh_rate` 中至少一个字段，并在服务端按刷新率分层。
- **类型**：知识盲区
- **位置**：L201-L209
- **问题**：Compose 示例在 `onDispose` 里只移除 `interaction`，没有移除 `screen`。如果该 state 绑定在可切换页面的 Composable 上，页面切走后可能留下 stale screen 标签。
- **建议**：页面级状态和交互状态都按生命周期成对清理，例如同时 `removeState("screen")` 和 `removeState("interaction")`；如果 `screen` 由 Activity 级容器维护，需要在示例旁明确说明生命周期边界。



## [Task9 Deep Review] 3.1 Input 事件分发全流程 — 2026-04-27
- **类型**：知识盲区/Trace 观察点
- **位置**：Pointer Event 与 Motion Event 小节
- **问题**：正文说 Compose PointerEvent 与 View MotionEvent 在 Perfetto 中表现完全一致，这对系统输入路径成立，但 Compose 侧还会经过 pointer input modifier / PointerInputEventProcessor 等运行时处理，专项分析时可能需要关联 Compose 章节观察额外消耗。
- **建议**：补一句边界：系统侧仍是同一条 `InputChannel -> deliverInputEvent`，Compose 内部分发成本需回到 Compose 运行时/7.x 章节另查，不把它混入 InputDispatcher 结论。

## [Task9 Deep Review] 16.4 Android 17 + Kernel 6.12 系统级性能优化 — 2026-04-27
- **类型**：数据缺失
- **位置**：Kernel 6.12 性能全景表与 AutoFDO 量化数据
- **问题**：启动、系统调用、Binder、MGLRU 等百分比数据分散出现，但没有逐项标注测试设备、benchmark 名称、内核分支、样本口径和官方出处；部分数字本轮只能验证到“方向一致”，不能验证到精确值。
- **建议**：把每个数字拆成“来源 URL/测试对象/版本/指标定义/是否官方公开”，无法复核的数字改为待验证或删除。


## [Task9 Deep Review] 7.4 典型场景分析 — 2026-04-27
- **类型**：源码准确性
- **位置**：L435 WebView Renderer 进程崩溃描述
- **问题**：正文写“Perfetto 中对应 `render_process_gone` 事件”，但 `didCrash()` 是 WebView `WebViewRenderProcessGoneDetail` 回调语义；当前没有给出 Perfetto/Chromium trace 中确实存在该事件名的来源。
- **建议**：如果这是 App 自定义插桩事件，明确写成自定义 Trace marker；否则改成 Android WebView 回调 `onRenderProcessGone()` / `RenderProcessGoneDetail.didCrash()`，并补 Chromium/WebView 实际 trace event 名称。

## [Task9 Deep Review] 8.9 Android 游戏性能与 Game Mode/State API — 2026-04-27
- **类型**：数据缺失
- **位置**：L466 Android 17 Generational GC 量化收益
- **问题**：正文写“GC 暂停时间从 10-30ms 降低到 1-5ms”，但没有设备、ART 版本、堆大小、对象分配模式和测试来源；同时 Android 17 版本边界缺少一手资料锚点。
- **建议**：补 ART release note / AOSP commit / benchmark 链接和测试条件；如果没有一手数据，删除具体毫秒区间，只保留“可能降低部分 STW 暂停”的定性边界。

## [Task9 Deep Review] 7.6 案例集 — 2026-04-27
- **类型**：交叉引用
- **位置**：L287, L452
- **问题**：相对链接 `05-main-render-thread.md` 与 `01-oem-overview.md` 以当前目录解析会失效。
- **建议**：改为 `../../part1-fundamentals/ch02-rendering/05-main-render-thread.md` 与 `../../part4-system/ch17-oem/01-oem-overview.md`，或改用纯章节号引用。

## [Task9 Deep Review] 7.6 案例集 — 2026-04-27
- **类型**：数据缺失
- **位置**：五个案例的 Trace 截图与效果对比
- **问题**：正文有多个 `[待补充：Trace 截图]`，但已经写入明确耗时与 Jank 率。
- **建议**：为每个数值补 trace 文件、设备、Android 版本、刷新率、采样窗口和统计方式；无法补证据的数值改成示例并标注 `[待验证]`。

## [Task9 Deep Review] 17.3 行业案例 — 2026-04-27
- **类型**：版本差异
- **位置**：L135（Game Mode API 模式枚举）
- **问题**：章节只列 Standard / Performance / Battery Saver，但 AOSP Android 16 `GameManager` 还包含 `GAME_MODE_CUSTOM`，并有 targetSdk <= Android 13 时 custom mode 兼容返回 standard 的逻辑。章节适用范围写 Android 12-16，缺少 Android 14+ custom mode 的版本边界。
- **建议**：补一行版本说明：公开文档主线仍要求游戏支持 standard / performance / battery，Android 14+ 平台 API 还存在 custom mode；读取 `GameManager#getGameMode()` 时要处理 `GAME_MODE_CUSTOM` 及旧 targetSdk 兼容行为。

## [External Review] 13.1 Perfetto介绍 — 2026-04-27
- **类型**：架构演进
- **位置**：Perfetto介绍
- **问题**：缺少Android 12+ Mainline APEX演进和Android 16+ UprobeStats/ProfilingManager的集成点
- **建议**：补强现代架构对齐，补充Mainline APEX演进和ProfilingManager集成点
- **来源**：Gemini外部review - 2026-04-25-13-13-batch-review-summary.md


## [External Review] 13.7 Perfetto高级用法 — 2026-04-27
- **类型**：功能补全
- **位置**：Perfetto高级用法
- **问题**：遗漏了perfetto::DataSource的自定义实现和分布式处理方案Bigtrace
- **建议**：补充SDK高阶特性，添加perfetto::DataSource自定义实现和分布式处理方案
- **来源**：Gemini外部review - 2026-04-25-13-13-batch-review-summary.md


## [External Review] 13.10 Perfetto SQL性能 — 2026-04-27
- **类型**：性能优化
- **位置**：Perfetto SQL性能
- **问题**：SQL脚本在处理R+状态和大规模Join时存在精度或性能风险
- **建议**：优化SQL鲁棒性与性能，增强处理R+状态和大规模Join的能力
- **来源**：Gemini外部review - 2026-04-25-13-13-batch-review-summary.md


## [External Review] 10.1 内存性能优化基础 — 2026-04-27
- **类型**：基线重构
- **位置**：内存性能优化基础
- **问题**：Android 15的16KB页面机制导致PSS/RSS天然膨胀约9%，现有绝对值基线策略失效
- **建议**：重构指标基线策略，适应Android 15/16内存页面机制变化
- **来源**：Gemini外部review - 2026-04-25-15-10-batch-review-summary.md


## [External Review] 10.2 内存分析工具 — 2026-04-27
- **类型**：工具升级
- **位置**：内存分析工具
- **问题**：Android 16的ProfilingManager标志着从被动抓转储到系统触发采样的范式转移
- **建议**：升级分析工具，适配ProfilingManager系统触发采样范式
- **来源**：Gemini外部review - 2026-04-25-15-10-batch-review-summary.md


## [External Review] 10.3 GPU内存监控 — 2026-04-27
- **类型**：监控闭环
- **位置**：GPU内存监控
- **问题**：Android 16通过AIDL IMemtrack补齐了系统级GPU内存的监控缺口
- **建议**：完善显存计量闭环，集成IMemtrack系统级GPU内存监控
- **来源**：Gemini外部review - 2026-04-25-15-10-batch-review-summary.md

