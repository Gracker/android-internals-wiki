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
