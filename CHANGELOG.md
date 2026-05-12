# Changelog

所有重要变更记录在此文件中。

## [0.2.0] - 2026-03-28

### 新增
- 新增 4 个小节：7.7 Compose 性能、8.6 Coroutine 性能、2.10 GPU 渲染深入、10.6 内存抖动
- 新增「阅读路径推荐」前言章节
- 新增 CI/CD：GitHub Actions 自动构建与部署
- 新增 v1.0 发布标准定义（metadata/v1.0-definition.md）
- 新增项目路线图（metadata/roadmap.md）
- 新增 OpenClaw 错误处理指南
- 新增 PR 模板和 Markdown lint 配置

### 改进
- 优化 OpenClaw task1：增加到每日 3 次扫描，新增素材分类与质量评估
- 优化 OpenClaw task2：调整验证优先级（L2 优先），新增异常处理和恢复机制
- 优化 OpenClaw task3：增加到每周 3 次巡检，新增分级巡检策略
- 修复 7 处大纲锚点准确性问题（HIDL/AIDL 演进、Binder 线程池、AsyncTask deprecated 等）
- 升级 2 个扩展为锚点：Phantom Process Killer、BlastBufferQueue
- 完善 CONTRIBUTING.md：新增社区贡献指南和 Review 时效
- 完善 .gitignore：补充 Python/IDE/日志等忽略规则
- 完善 book.toml：添加 mermaid 插件和搜索优化配置

### 修复
- 修正 ch01/01 中 HIDL/AIDL 的演进方向描述
- 修正 ch01/04 Binder 线程池默认数量的过度简化描述
- 修正 ch01/05 AsyncTask 缺少 deprecated 标注
- 修正 ch07/01 Jank 定义未覆盖高刷新率场景

## [Unreleased]
