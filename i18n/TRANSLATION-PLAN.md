# 英文翻译计划

> 本文件记录英文版本的翻译策略，v1.0 中文版发布后启动。
> 翻译目录以 `metadata/v1.0-definition.md` 与 `src/SUMMARY.md` 的当前五部分、26 章为准。

## 翻译策略

### 整体方案
- 中文版 v1.0 完成后，整体翻译为英文
- 使用 mdbook 的多语言支持（或独立分支/目录）
- 文件路径保持英文不变（当前已是英文命名）

### 翻译原则
1. **技术术语保留英文**：Choreographer、SurfaceFlinger、Binder、VSync 等专有名词不翻译
2. **中文特有表达意译**：如"卡顿"→ "jank/stutter"、"流畅性"→ "smoothness"、"响应速度"→ "responsiveness"
3. **AOSP 源码路径和代码保持原样**
4. **案例中的中文 App 名称保留**，附英文说明

### 需要提前维护的资产
- `src/appendix/glossary.md` — 术语表（中英对照），在中文版写作过程中持续更新
- 每篇文章的 YAML frontmatter 中的 `title` 字段保留中文，翻译时新增 `title_en` 字段

## 翻译流程（v1.0 后）

1. 创建 `src-en/` 目录，镜像 `src/` 结构
2. 逐章翻译，OpenClaw 可辅助初译，人工 review
3. 术语一致性检查（基于 glossary.md）
4. 英文版独立构建和部署

## 章节标题中英对照（预留）

书名：《Android 技术内幕：系统机制、性能优化与工具实战》
英文：*Android Internals: System Architecture, Performance & Tooling in Practice*

| 中文 | English |
|------|---------|
| 第一部分：Android 系统运行机制 | Part 1: Android System Internals |
| 第 1 章：系统架构全景 | Chapter 1: System Architecture Overview |
| 第 2 章：渲染系统 | Chapter 2: Rendering System |
| 第 3 章：输入系统 | Chapter 3: Input System |
| 第 4 章：内存管理 | Chapter 4: Memory Management |
| 第 5 章：CPU 调度与能耗管理 | Chapter 5: CPU Scheduling & Power Management |
| 第 6 章：存储与 I/O | Chapter 6: Storage & I/O |
| 第二部分：性能专题 | Part 2: Performance Topics |
| 第 7 章：流畅性 | Chapter 7: Smoothness |
| 第 8 章：响应速度 | Chapter 8: Responsiveness |
| 第 9 章：ANR | Chapter 9: ANR |
| 第 10 章：内存性能 | Chapter 10: Memory Performance |
| 第 11 章：功耗 | Chapter 11: Power Consumption |
| 第 12 章：包体积与网络 | Chapter 12: APK Size & Networking |
| 第 18 章：渲染链路全景 | Chapter 18: Rendering Pipelines |
| 第三部分：工具与方法论 | Part 3: Tools & Methodology |
| 第 13 章：Perfetto | Chapter 13: Perfetto |
| 第 14 章：其他分析工具 | Chapter 14: Other Analysis Tools |
| 第 15 章：方法论 | Chapter 15: Methodology |
| 第 19 章：APM 工具与性能监控生态 | Chapter 19: APM & Performance Monitoring |
| 第四部分：系统级优化与行业实践 | Part 4: System Optimization & Industry Practices |
| 第 16 章：AOSP 性能优化 | Chapter 16: AOSP Performance Optimization |
| 第 17 章：厂商优化实践 | Chapter 17: OEM Optimization Practices |
| 第五部分：应用层优化 | Part 5: Application Performance |
| 第 20 章：应用稳定性治理 | Chapter 20: Application Stability |
| 第 21 章：启动优化 | Chapter 21: Startup Optimization |
| 第 22 章：渲染优化实战 | Chapter 22: Rendering Optimization in Practice |
| 第 23 章：内存优化实战 | Chapter 23: Memory Optimization in Practice |
| 第 24 章：I/O 与网络优化 | Chapter 24: I/O & Network Optimization |
| 第 25 章：功耗与包体积优化 | Chapter 25: Power & App Size Optimization |
| 第 26 章：应用可观测性 | Chapter 26: Application Observability |
