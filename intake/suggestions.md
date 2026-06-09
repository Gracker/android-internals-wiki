## [Task9 Idle Audit] 5.12 Thermal 管控深度：从内核子系统到 ADPF 主动降频 — 2026-06-10
- **类型**：源码准确性
- **位置**：step_wise governor - throttle 参数描述
- **问题**：章节提到 android16-6.12 中的 throttle 参数控制 cooling state 增加，但未明确标注该参数的 Android 分支特异性。mainline kernel 6.12+ 可能不包含相同参数实现。
- **建议**：在 step_wise 代码示例旁添加版本注释，说明该参数为 Android 分支特有，mainline kernel 可能有不同实现。

## [Task9 Idle Audit] 5.12 Thermal 管控深度：从内核子系统到 ADPF 主动降频 — 2026-06-10
- **类型**：版本差异
- **位置**：power_allocator governor pid_controller 签名描述
- **问题**：章节将 android-mainline/common 的 pid_controller() 签名误描述为通用实现，但实际上 android16-6.12 分支仍使用旧风格参数 (trip_switch_on, trip_temp, MAX_K*)，存在显著差异。
- **建议**：分开描述 mainline 和 Android 分支的 pid_controller() 签名差异，明确标注不同版本的参数结构。

## [Task9 Idle Audit] 5.12 Thermal 管控深度：从内核子系统到 ADPF 主动降频 — 2026-06-10
- **类型**：数据缺失
- **位置**：Framework TemperatureWatcher 实现
- **问题**：getHeadroomCallbackDataLocked() 内部使用 getForecast(0) + getForecast(10) 但未说明 forecastSeconds 参数可能动态变化。
- **建议**：补充说明 TemperatureWatcher 中 mForecastSeconds 参数的动态性，以及其对 listener 回调频率的影响。

## [Task9 Idle Audit] 5.12 Thermal 管控深度：从内核子系统到 ADPF 主动降频 — 2026-06-10
- **类型**：知识盲区
- **位置**：Governor 参数差异
- **问题**：章节仅泛泛提及 power_allocator PID 参数调优原则，但未包含 Qualcomm/SoC vendor 对默认参数的具体差异。
- **建议**：增加表格对比主流 SoC 厂商 (Qualcomm, MediaTek, Samsung) 的 power_allocator 默认 PID 参数差异，并提供调优建议。

## [Task6 Review] 14.2 Simpleperf — 2026-06-10

- **类型**：需重写（文体）+ 需验证（技术准确性）
- **位置**：全章，重点 14.7、14.9、14.10、14.2
- **问题**：
  1. **文体违反 writing-guide（全章）**：37个代码块全部是命令/代码堆砌，无连贯叙述。属于 writing-guide 反面教材1（百科词条式）+ 反面教材3（概述式）。writing-guide 要求 Type C 工具篇以"没有这个工具你会多痛苦"开篇，实际是"Simpleperf是Android系统自带的高性能性能分析工具"这种百科开头。
  2. **14.7 性能优化实践与 Simpleperf 无关**：展示 TexturePool 对象池、WeakReference 防泄漏、线程池配置——全是通用 Java 知识，不是"从 simpleperf report 定位到优化点"的分析闭环。
  3. **14.9 案例缺乏 Simpleperf 特有输出**：案例里没有 simpleperf report 的调用栈、--show-call-graph 结果、热点函数排名。LazyInitializer 和 SafeHandler 是 Android 通用知识，不是 Simpleperf 分析流程。
  4. **14.10 Gradle 插件存疑**：`id 'simpleperf-plugin'` 未在官方文档中找到对应记录。
  5. **14.2 设备端路径错误**：`adb pull /system/bin/simpleperf` 在多数设备上不存在，simpleperf 通过 NDK 分发。
- **建议**：按 writing-guide Type C 结构重写全章；14.7/14.9 重写为 simpleperf 分析闭环；验证 14.10 和 14.2 的技术准确性。
- **review 日志**：logs/review/2026-06-10-05-review.md
