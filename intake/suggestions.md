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
