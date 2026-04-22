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
