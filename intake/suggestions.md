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
