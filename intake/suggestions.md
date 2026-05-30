## [Task6 Review] 2.10 GPU 渲染深入 — 2026-05-30

- **类型**：需补充素材
- **位置**：实战案例章节
- **问题**：缺乏真实的 Perfetto Trace 截图、AGI 分析截图或可复现的测试条件
- **建议**：补齐一手 Trace/AGI 证据，或明确标注为示例场景
- **review 日志**：logs/review/2026-05-30-22-review.md

- **类型**：需补充素材
- **位置**：ASTC vs ETC2 带宽对比章节
- **问题**：依赖厂商优化指南，缺少实际测试数据验证
- **建议**：在目标设备上用 `adb shell cmd gpu vkjson` 确认支持并测试对比
- **review 日志**：logs/review/2026-05-30-22-review.md

- **类型**：需重写
- **位置**：多个技术分析章节
- **问题**：论述偏理论化，缺乏个人调试经验分享
- **建议**：增加实际排查案例中的观察细节和个人判断过程
- **review 日志**：logs/review/2026-05-30-22-review.md

- **类型**：需重写
- **位置**：GPU Headroom API 使用说明、Vulkan 优势解释等
- **问题**：表述过于模板化，缺乏个人视角
- **建议**：重写为更具个人经验的表述方式
- **review 日志**：logs/review/2026-05-30-22-review.md

## [Task9 Deep Review] 18.13 WebView 渲染管线 — 2026-05-31

- **类型**：数据缺失
- **位置**：SurfaceControl 子 Surface 性能特征部分
- **问题**："网页重绘压力会更容易和App UI预算分开观察" 缺少性能对比数据
- **建议**：补充独立 SurfaceControl vs Functor 路径的内存占用、帧率稳定性、GPU 负载对比数据

- **类型**：数据缺失
- **位置**：第三方 Texture-like 实现部分
- **问题**："宿主侧会多一次纹理采样，开销是否可接受取决于实现" 缺少量化分析
- **建议**：在典型设备上测试 TextureView 路径 vs Functor 路径的帧率影响

- **类型**：数据缺失
- **位置**：独立 SurfaceControl vs Functor 路径性能比较
- **问题**：缺少独立 SurfaceControl vs Functor 路径的性能基准数据
- **建议**：在主流设备上补充两种路径的典型性能数据对比

- **类型**：交叉引用不完整
- **位置**：引用 SurfaceControl API 深入章节
- **问题**：引用"§18.10 SurfaceControl API 深入"但未说明具体要查看哪些 Transaction 和 fence 细节
- **建议**：明确说明在 §18.10 中需要查看的关键技术点

## [Task6 Review] 18.15 视频叠加与 HWC — 2026-05-31

- **类型**：需重写
- **位置**：SKIP_VALIDATE 相关技术说明
- **问题**：Task9 已多次指出 SKIP_VALIDATE 版本边界与 canSkipValidate 条件未修正，存在技术事实风险
- **建议**：需 Task9 审核 AOSP 源码中的 SKIP_VALIDATE 实际逻辑和版本边界，Task2B 修正技术准确性
- **review 日志**：logs/review/2026-05-31-04-review.md

- **类型**：需重写
- **位置**：术语使用不一致
- **问题**：SurfaceFlinger 在全文中时而使用全称，时而简写为 SF，术语不一致影响可读性
- **建议**：统一使用全称 'SurfaceFlinger' 保持术语一致性
- **review 日志**：logs/review/2026-05-31-04-review.md

- **类型**：需补充素材
- **位置**：Tunnel Mode 启用条件
- **问题**：关键的技术断言缺少具体的验证来源和 AOSP 源码引用
- **建议**：补充 MediaCodec TunneledPlayback 的具体 AOSP 实现路径和版本差异
- **review 日志**：logs/review/2026-05-31-04-review.md

## [Task9 Deep Review] 18.15 视频叠加与 HWC — 2026-05-31

- **类型**：知识盲区
- **位置**：HWC 合成决策机制
- **问题**：缺少 HWC 合成类型决策机制的说明 - 决定 DEVICE vs CLIENT 的具体启发式算法是什么
- **建议**：补充 HWC 作出 composition type 决策的具体条件和优先级规则

- **类型**：版本差异
- **位置**：HWC3 vs HWC2 实现差异
- **问题**：缺少 HWC3 与 HWC2 在合成决策实践中的具体差异说明
- **建议**：对比 HWC2 和 HWC3 在 composition 类型决策、性能优化方面的关键差异

- **类型**：版本差异
- **位置**：Tunnel Mode 演进
- **问题**：缺少 tunnel mode 能力在 Android 10-17 间的演进信息
- **建议**：补充各版本中 tunnel mode 支持的关键变化和限制条件

- **类型**：数据缺失
- **位置**：性能影响量化
- **问题**：'GPU Path 多消耗 2-3x 的内存带宽,Overlay Path 几乎不消耗 GPU 资源' 缺少基准数据
- **建议**：提供具体的测试方法和测量数据来支撑带宽和资源消耗的量化描述

- **类型**：交叉引用不完整
- **位置**：内存管理章节关联
- **问题**：未说明与内存管理章节（buffer 处理、同步）的关联
- **建议**：补充与 buffer 管理、内存同步相关的技术细节和注意事项
