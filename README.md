# Android 技术内幕：系统机制、性能优化与工具实战

[English navigation summary](README.en.md)

> *Android Internals: System Architecture, Performance & Tooling in Practice*
> 完整英文版计划在 v1.0 之后提供；当前已有英文项目与生态导航摘要。

一本由 AI 辅助持续进化的 Android 技术百科，面向有经验的 Android 开发者和系统工程师。

当前项目处于 **alpha 精修期**。正文已恢复为 5 个部分、26 章、前言和附录的规范架构；当前重点从“目录收敛”转向技术审校、状态统一和发布验证。阅读和维护时请优先参考本文件下面的“当前事实口径”。

<!-- android-performance-ecosystem:start -->
## Android 性能分析生态

[Android Performance Ecosystem](https://github.com/Gracker/android-performance-ecosystem) 通过导航 Hub 与七个核心项目，把可选插桩、采集、分析、系统知识与可复现案例连接成一套完整路径。

| 阶段 | 项目 | 作用 | 地址 |
| --- | --- | --- | --- |
| 导航 | [Android Performance Ecosystem](https://github.com/Gracker/android-performance-ecosystem) | 维护统一项目地图、交接元数据、README 导航区块与漂移检查。 | [GitHub](https://github.com/Gracker/android-performance-ecosystem) |
| 插桩 | [TraceFix](https://github.com/Gracker/TraceFix) | 在编译期注入 App 侧 android.os.Trace section，让方法执行在运行时 Trace 中可见。 | [GitHub](https://github.com/Gracker/TraceFix) |
| 采集与测量 | [Perfetto Tools](https://github.com/Gracker/perfetto-tools) | 抓取可复现的 Perfetto Trace，并采集 FPS 或 Simpleperf 测量结果。 | [GitHub](https://github.com/Gracker/perfetto-tools) |
| 分析 | [SmartPerfetto](https://github.com/Gracker/SmartPerfetto) | 通过 AI 辅助 Web UI、CLI、报告、会话、对比和证据工作流分析 Trace。 | [GitHub](https://github.com/Gracker/SmartPerfetto) |
| Agent 分析 | [Perfetto Skills](https://github.com/Gracker/Perfetto-Skills) | 为 Agent 提供可移植的 Android、Linux、Chromium Perfetto 分析 Skill，并通过固定版本流程同步选定资产。 | [GitHub](https://github.com/Gracker/Perfetto-Skills) |
| 学习 | [Android Performance Blog](https://github.com/Gracker/Gracker.github.io) | 通过文章、系统原理和案例复盘讲解 Perfetto 与 Systrace 分析。 | [AndroidPerformance.com](https://www.androidperformance.com/) · [GitHub](https://github.com/Gracker/Gracker.github.io) |
| 系统知识 | Android Internal Wiki | 处于 alpha 阶段的 Android 系统知识库，覆盖 App、Framework、Native 与 Kernel 机制。 | **Coming soon** |
| 复现 | [Trace for Blog (SystraceForBlog)](https://github.com/Gracker/SystraceForBlog) | 提供文章使用的 Perfetto、Systrace 及相关案例文件，支持动手复现。 | [GitHub](https://github.com/Gracker/SystraceForBlog) |
<!-- android-performance-ecosystem:end -->

## 项目特点

- **跨层覆盖**：App → Framework → Native → Kernel，完整链路
- **持续更新**：按 Android 版本持续追踪变化（当前基准：Android 17 / API 37）
- **源码级引用**：每个知识点标注 AOSP 源码路径，可追溯验证
- **实战驱动**：大量来自一线性能优化的真实案例

## 内容结构

- **第一部分：Android 系统运行机制** — 架构、渲染、输入、内存、CPU/功耗、存储
- **第二部分：性能专题** — 流畅性、响应速度、ANR、内存性能、功耗、网络性能
- **第三部分：工具与方法论** — Perfetto、Simpleperf、MAT、dumpsys、APM、方法论
- **第四部分：系统级优化与行业实践** — AOSP 优化、厂商实践
- **第五部分：应用层优化** — 稳定性、启动、渲染、内存、I/O、功耗、可观测性

`src/SUMMARY.md` 是 mdBook 的权威发布入口，当前已经覆盖 5 个部分、26 章、前言、附录和全部保留正文。工作流成熟度和未闭环问题仍需结合 `metadata/progress.json`、`metadata/queue.json` 与 `logs/` 判断。

## 语言

当前版本为中文。v1.0 发布后将全文翻译为英文并发布英文版本。项目中已保留英文翻译所需的基础设施（术语表中英对照、文件路径英文命名、i18n 计划文档）。

## 本地构建

```bash
# 安装 mdbook
cargo install mdbook

# 安装 Mermaid 预处理器
cargo install mdbook-mermaid

# 构建
mdbook build

# 本地预览
mdbook serve
```

## 目录结构

```
├── src/              # 书的正文源文件与 mdBook 目录
├── intake/           # 外部输入、人工请求、素材索引入口
├── metadata/         # 队列、进度、质量索引、扫描状态
├── logs/             # review / research / integration / rework 日志
├── openclaw-tasks/   # OpenClaw 流水线任务说明
├── scripts/          # 元数据、索引、changelog、校验脚本
├── changelog/        # 每日变更记录
└── i18n/             # 国际化相关（v1.0 中文内容冻结后启用）
```

## 当前事实口径

截至 2026-08-11，当前活动口径已经统一：

- 规范章节正文共 454 篇：`finalized` 312、`ready-for-review` 142。
- `pipeline_stage=ready-to-publish` 的正文为 263 篇；其余遗留流水线状态按 `metadata/progress.json` 聚合展示。
- `src/SUMMARY.md` 包含 493 个本地链接，链接目标和重复项检查均通过。
- `metadata/queue.json` 共有 23 条活动/审计记录：9 条 `body-applied`、7 条 `rejected`、5 条 `superseded`、1 条 `review-finalized`、1 条 `completed`。
- `metadata/inventory.json` 只索引项目外的素材文档，不再把本仓库 `src/` 当作外部输入。

若状态发生短时冲突，优先级是：章节 frontmatter 与正在处理的 queue > 最近 logs > `metadata/progress.json` 聚合 > README 快照。已关闭的 review finding 和历史日志允许保留变更发生时的旧路径。

## 内容验证标准

章节 frontmatter 目前主要跟踪工作流状态，如 `ready-for-review`、`finalized`。
正文中的知识点级标注仍使用以下验证状态：

默认源码验证锚点为 AOSP `android-17.0.0_r1`。旧版本 tag 只用于版本演进、历史行为对比或章节内明确说明的低版本边界。

- `verified` — 已通过 AOSP 源码或实机验证
- `draft` — 初稿完成，等待验证
- `needs-review` — 需要人工审核
- `outdated` — 存在已知过时部分

## 项目进度

当前阶段：**alpha**（正文持续批量 review / finalize，目录架构和基础治理口径已经收敛）

当前优先事项：

1. 消费 `metadata/queue.json` 中仍为 `pending` 的时效性与 DeepResearch 条目。
2. 把正文中的遗留状态名逐步统一到 `draft`、`ready-for-review`、`finalized` 和 `ready-to-publish`。
3. 推进 Part 1-3 发布前审校，并补齐 Part 4-5 的版本边界与证据链。
4. 在安装 mdBook 与 Mermaid 预处理器的环境中持续验证完整 HTML 构建。

详细路线图见 [metadata/roadmap.md](metadata/roadmap.md)

## 贡献

欢迎贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解贡献方式和规范。

## 关于 AI 辅助

本项目使用 AI Agent（OpenClaw）辅助内容加工：
- AI 负责：素材整理、结构化、初稿生成、格式校验
- 人工负责：技术判断、内容审核、最终定稿
- 所有 AI 生成的内容都经过人工审核和修改

## License

本作品采用双许可：

- 社区使用：[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)；
- 商业使用：由权利持有人另行书面授予的
  [AIW Commercial License](COMMERCIAL-LICENSE.md)。

仅下载仓库或 Knowledge Pack 不代表获得商业授权。SmartPerfetto 使用的公开
Knowledge Pack 收录规范章节目录中的所有正文，不以 `status`、`pipeline_stage`、
Task6/Task9 或 queue 状态作为门槛。各级 `README.md`、`SUMMARY.md` 和自动生成的
导航/分析产物不属于正文；私有路径行会在公开投影中脱敏，密钥命中会阻断发布。构建和分发规则见
[`knowledge-pack/policy.yaml`](knowledge-pack/policy.yaml)，Pack 再分发边界见
[`KNOWLEDGE-PACK-LICENSE.md`](KNOWLEDGE-PACK-LICENSE.md)。

> 注：本书引用的 AOSP 源码遵循 Apache License 2.0。引用他人内容均已标注原始出处，仅用于技术说明目的。
