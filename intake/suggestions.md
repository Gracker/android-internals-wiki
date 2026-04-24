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
