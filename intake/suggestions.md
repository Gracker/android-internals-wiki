## [Task9 Deep Review] 13.25 源码调研：PerfDog 的 Android 平台 GPU/性能采集底层数据源 — 2026-07-13

### 源码准确性问题
- **类型**：源码准确性
- **位置**：GameDevicePerformanceManager API 路径引用
- **问题**：`frameworks/base/core/java/android/gamedeviceperformance/` 路径在 Android 17 中不存在，实际 API 位于 `frameworks/base/core/java/android/hardware/display/` 下
- **建议**：修正 API 路径引用，补充 GameDevicePerformanceManager 在 Android 17 中的实际包路径和类名

### 交叉引用一致性问题
- **类型**：交叉引用一致性
- **位置**：相关章节引用
- **问题**：章节中引用的 13.17、13.14、14.19 在项目中不存在，造成读者困惑
- **建议**：移除不存在的章节引用，或创建实际的引用章节，改为引用现有相关章节如 ch13-perfetto 目录下的其他章节

### 版本差异覆盖问题
- **类型**：版本差异
- **位置**：Android 17 新特性说明
- **问题**：未充分说明 Android 17 相比 Android 16 在 GPU 性能数据采集方面的新变化
- **建议**：增加 Android 17 特有的 GPU 性能数据采集特性说明，如 FrameTimeline 机制的新功能

### 知识盲区问题
- **类型**：知识盲区
- **位置**：GPU 计算着色器性能采集
- **问题**：缺少 GPU 计算着色器（Compute Shader）性能数据采集方法的说明
- **建议**：补充 Vulkan Compute Shader 的性能观测路径，包括 vkCmdDispatch 的 GPU 执行时间测量方法

### 知识盲区问题
- **类型**：知识盲区
- **位置**：GPU 重叠分析
- **问题**：未提及 GPU 重叠（Overdraw）的定量分析方法
- **建议**：补充 overdraw 数据采集方法，包括通过 `dumpsys gfxinfo` 的 overdraw 统计和 Perfetto 的 overdraw track 分析

### 数据支撑问题
- **类型**：数据缺失
- **位置**：GPU 频率调节阈值
- **问题**：缺少具体的 GPU 频率调节阈值数据，不同厂商 thermal throttle 数值不明确
- **建议**：提供主要 GPU 厂商（高通、ARM Mali）的具体 thermal trigger 数值，如高通 85°C 降频 30% 等

### 数据支撑问题
- **类型**：数据缺失
- **位置**：Perfetto SQL 查询案例
- **问题**：缺少实际的 GPU 性能问题定位的 SQL 查询案例
- **建议**：提供具体的 Perfetto SQL 查询示例，如分析 GPU 渲染瓶颈的查询语句

### 数据支撑问题
- **类型**：数据缺失
- **位置**：性能基准数据
- **问题**：缺少典型应用的 GPU 性能正常范围参考值
- **建议**：提供不同类型应用（游戏、UI、视频）的 GPU 性能基准数据，包括正常 GPU 利用率、频率范围等

### 内容衔接问题
- **类型**：交叉引用一致性
- **位置**：与前序章节衔接
- **问题**：未充分引用 13.14（Perfetto 基础）中的相关概念，缺少概念衔接
- **建议**：增加对 Perfetto 基础章节的引用，说明本章内容如何建立在 Perfetto 基础之上

## [Task9 Deep Review] 1.6 Android 版本演进中的架构变化 — 2026-07-13

### 源码锚点缺失问题
- **类型**：源码准确性
- **位置**：Android 17 MessageQueue 实现描述
- **问题**：章节中提到 Android 17 引入 lock-free MessageQueue，但未提供具体的 AOSP 源码路径支持该技术结论
- **建议**：补充 `frameworks/native/services/binder/MessageQueue.cpp` 或相关源码文件的引用，增强技术结论的可验证性

### 版本差异表述优化
- **类型**：版本差异
- **位置**：ART 编译行为描述
- **问题**：版本差异表格中未说明 Android 12+ ART 行为可能通过 Play Store 独立更新，不仅受大版本升级影响
- **建议**：在 Android 12+ 相关描述中明确标注 "Android 12+ ART 行为可能通过 Play Store 独立更新，分析时需注意区分大版本升级和 Play Store 更新的影响"

## [Task9 Deep Review] 14.9 Android Camera 性能与 Perfetto 分析 — 2026-07-13
- **类型**：数据缺失
- **位置**：Camera 功耗优化章节
- **问题**：缺少 Camera 不同操作模式（预览、拍照、录像）下的具体功耗数值和基线数据
- **建议**：补充典型场景下的功耗基准数值，如预览 1080p@30fps 耗电 X mA、拍照 Y mA、4K 录制 Z mA，为优化提供量化基准

- **类型**：知识盲区
- **位置**：厂商 HAL 实现差异
- **问题**：高通/MTK 等厂商 HAL 实现差异仅作为排查线索提及，缺少典型厂商的性能特征和调优方向
- **建议**：增加主要厂商 HAL 实现的性能特征分析，如高通 CamX/CHI 架构的关键优化点、联发科 MTKCam 的性能瓶颈等