# AIW 自动 Review 任务报告 (Gemini 专用)

## 一、目标发现结果
- 扫描范围：`src/part3-tools/ch14-other-tools/08-gpu-debug-tools.md`
- 候选章节：
  1. `src/part3-tools/ch14-other-tools/08-gpu-debug-tools.md` | 本次指定的目标章节。
- 最终选择：`src/part3-tools/ch14-other-tools/08-gpu-debug-tools.md`
- 选择理由：用户指定，且状态为 `ready-for-review`。
- 排除的高频原因：无（单一目标）。

## 二、总体结论
- 总体技术评分：3.5/5
- 是否建议回炉：是
- 主要风险：存在多处关键概念混淆（如 `<profileable>` 标签语法误描述为属性）、部分工具版本与 AOSP 演进逻辑描述不够严谨（如 ANGLE 的 AOSP 提交路径与开关机制）。
- 评分理由：文章覆盖面广，包含了 2026 年的前瞻性工具（Sokatoa），但在基础 Manifest 配置、Perfetto 数据源路径等源码/配置级细节上存在错误（P0/P1），且对厂商工具（Snapdragon Profiler）的维护状态描述与最新官方趋势（Qualcomm Profiler 整合）存在细微偏差。
- 本轮 review 覆盖范围：全章，包括工具分层、AGI、Perfetto GPU、RenderDoc、Sokatoa、指标分析、厂商工具。
- 本轮未完成部分：无。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 3/5 | 2 (P0/P1) |
| 原理链完整性 | 4/5 | 1 (P1) |
| 版本差异覆盖 | 4/5 | 1 (P1) |
| 知识盲区 | 3/5 | 1 (P1) |
| 数据/案例支撑 | 4/5 | 0 |
| 交叉引用一致性 | 4/5 | 0 |

## 四、P0 问题（事实错误）
- [P0][源码准确性][误用 Manifest 标签]
- 原文问题：文中描述为 "Android 11 (API 30) 增加了 android:profileable enabled="true" 写法"。
- 源码 / 一手资料锚点：`https://developer.android.com/guide/topics/manifest/profileable-element`
- 关键代码逻辑：`profileable` 是 `<application>` 的子标签 `<profileable />`，而非属性。正确语法为 `<profileable android:shell="true" android:enabled="true" />`。
- 运行原理说明：PackageManager 在解析 Manifest 时会寻找对应的子标签。
- 版本差异：Android 10 (API 29) 引入该标签。
- 核验结论：原文将其描述为属性写法，会导致开发者配置失败，Perfetto 无法采集数据。
- 为什么错：混淆了标签与属性的概念。
- 建议修正方向：明确指出是子标签写法，并给出正确的 XML 示例。

## 五、P1 问题（重要缺失）
- [P1][原理链完整性][ANGLE 切换机制缺失]
- 原文问题：文中提到 Android 17 的 denylist 策略，但未说明如何通过 `adb` 或系统属性在开发阶段强制切换。
- 源码 / 一手资料锚点：AOSP 中 `cmd gpu` 命令或 `persist.graphics.egl` 系统属性。
- 关键代码逻辑：`adb shell cmd gpu set-graphics-driver --package <pkg> --driver angle`。
- 缺失内容：开发阶段强制验证 ANGLE 路径的方法。
- 运行原理说明：Loader 根据 `GraphicsEnvironment` 中的设置选择驱动。
- 版本差异：Android 15+ 提供了更成熟的切换入口。
- 为什么这是重要缺失：如果开发者不知道如何切换，就无法在 Android 17 之前验证自己的 App 在 ANGLE 下的 GPU 表现。
- 建议补充方向：补充 `adb shell cmd gpu` 的使用方法。

- [P1][知识盲区][Perfetto 数据源路径不具体]
- 原文问题：文中提到 `gpu.counters` 数据源，但未给出其在 AOSP 中的定义路径。
- 源码 / 一手资料锚点：`protos/perfetto/config/gpu/gpu_counter_config.proto`
- 缺失内容：具体的数据源定义和常用的 Counter ID 获取方式（`perfetto --query`）。
- 为什么这是重要缺失：开发者在编写自定义 Trace Config 时需要这些信息。
- 建议补充方向：引用具体的 proto 路径，并提示使用 `perfetto --query`。

## 六、P2 问题（建议改进）
- [P2][版本差异覆盖][Snapdragon Profiler 状态]
- 原文问题：文中称 Snapdragon Profiler "仍在活跃维护"，但实际上高通正逐渐向 **Qualcomm Profiler**（一个更通用的分析器）整合。
- 证据或观察依据：Qualcomm 官方文档中已开始推广 Qualcomm Profiler，Snapdragon Profiler 虽然有 2025/2026 版本，但功能增长已放缓。
- 问题描述：描述不够“与时俱进”。
- 建议：提及 Qualcomm Profiler 的出现及其作为系统级工具的地位。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|------|-------|
| Tile-Based Rendering 对计数器的影响 | 高 | 研究 Mali/Adreno 在 Tilers 阶段的专用计数器含义差异。 |
| RenderDoc 与 AGI 的数据导出兼容性 | 中 | 验证 AGI 2026 H2 版本的具体导出限制。 |
| ANGLE 对 Shader 编译时间的影响 | 高 | 比较原生驱动 vs ANGLE 在初次运行时的编译尖刺差异。 |

## 八、外部核验建议
- 搜索关键词：`android:profileable manifest shell true`
- 建议查 AOSP / 官方文档 / Perfetto / blog / issue tracker 哪类来源：官方文档 `developer.android.com`。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- 章节：14.8
- 严重级别：P0
- 问题类型：源码错误
- 位置：常见问题与误区 / 误区 4
- 问题描述：`<profileable>` 误写为属性。
- 建议修正方向：更正为子标签 `<profileable android:shell="true" />`。

- 章节：14.8
- 严重级别：P1
- 问题类型：原理断裂
- 位置：AGI 对 GLES 应用的分析路径
- 问题描述：缺失开发阶段强制切换 ANGLE 的命令。
- 建议修正方向：增加 `adb shell cmd gpu` 命令说明。

### 9.2 知识盲区清单（供后续研究）
- 章节：14.8
- 盲区描述：不同厂商 GPU Counter ID 的动态发现机制。
- 重要程度：中
- 建议研究方向：`perfetto --query` 命令在不同 Android 版本上的返回差异。

### 9.4 可复用知识资产（高价值新增知识）
- 章节：14.8
- 一手资料链接或来源类型：`https://developer.android.com/agi`
- 关键源码路径：`frameworks/native/services/gpuservice` (AOSP)
- 关键类 / 方法 / 字段：`GpuService` 处理 GPU 计数器采集。
- 版本差异摘要：Android 14 增强了 profileable 应用的 GPU 计数器访问权限，无需 Root。
- 为什么条知识值得保留：这是近年最重要的 GPU 分析权限变更。

## 十、下一候选章节
- `src/part2-performance/ch02-rendering/09-gpu-rendering-pipeline.md` (作为本章的理论支撑，需确认为 Ready-for-review)

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-21-14-08-gpu-debug-tools-external-review.md`
