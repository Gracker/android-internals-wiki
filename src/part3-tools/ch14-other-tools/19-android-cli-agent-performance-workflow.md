---
title: "Android CLI 与 Agent 化性能调试工作流"
chapter: "14.19"
status: draft
applicable_versions: "Android CLI 1.0+；Android Studio Quail 2 Canary 1+（studio 命令预览能力）"
tags: [android-cli, agent, performance-tooling, android-studio, perfetto]
related_chapters: ["13.10", "13.12", "14.1", "14.18", "19.14"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-22"
gap_source: "官方文档/每日信息/研究素材"
---

# 14.19 Android CLI 与 Agent 化性能调试工作流

<!-- outline-start -->
## 要点

### 🔹 Android CLI 在性能工具链里的位置
说明 Android CLI 不是替代 Android Studio Profiler、Perfetto 或 APA 的分析引擎，而是把项目描述、设备管理、运行、UI 结构读取、Journey 测试和 Android Studio 语义能力接到 agent 工作流里的命令入口。

### 🔹 项目描述、SDK 与设备基线
覆盖 `android describe`、`android info`、`android sdk list/install/update`、`android emulator create/start/list` 的适用场景，建立性能复现实验前的 SDK、设备 profile、构建产物和运行环境基线。

### 🔹 run / layout / screen 在复现流程中的边界
梳理 `android run` 部署 APK、`android layout` 导出布局树、`android screen capture/resolve` 采集屏幕和坐标的证据价值，强调这些命令适合复现、UI 状态确认和自动化点击，不替代帧级 trace。

### 🔹 Journeys 与关键用户路径回归
说明 Journey 用自然语言描述核心用户路径，适合驱动 agent 按真实交互路径运行应用；需要补齐冷启动、页面切换、滚动、弱网和登录态等性能场景的基线设计。

### 🔹 Android Studio 语义命令与性能排查协作
覆盖 `android studio check/analyze-file/find-declaration/find-usages/open-file/render-compose-preview/version-lookup` 的能力边界，说明它们如何服务于源码定位、Compose Preview、依赖版本核对和人工复核。

### 🔹 Android skills 与性能专项能力
梳理 `android skills list/find/add/remove` 和 Android skills 的更新/覆盖边界，重点记录 Perfetto SQL、Testing setup、R8 auditing 等与性能工程相关的技能如何作为 agent 的可复用知识包。

### 🔹 与 APA / Perfetto / Macrobenchmark 的分工
建立 Android CLI、Android Performance Analyzer、Perfetto UI、Macrobenchmark、Android Studio Profiler 的分工矩阵：CLI 负责串起环境与动作，Trace/Profiler 负责证据采集，SQL/APA 负责分析，Macrobenchmark 负责可重复指标。

## 扩展

### 🔸 CI 与本地 agent 工作流模板
可补充从构建产物定位、安装运行、Journey 执行、trace 采集到报告生成的一条最小可复现链路。

### 🔸 隐私与遥测边界
可补充 Android CLI 官方收集/不收集的数据范围，以及企业内网使用时的配置、日志和凭证处理边界。

<!-- outline-end -->

> 本节内容待加工。
