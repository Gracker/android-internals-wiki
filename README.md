# Android 技术内幕：系统机制、性能优化与工具实战

> *Android Internals: System Architecture, Performance & Tooling in Practice*
> English version planned after v1.0 release.

一本由 AI 辅助持续进化的 Android 技术百科，面向有经验的 Android 开发者和系统工程师。

## 项目特点

- **跨层覆盖**：App → Framework → Native → Kernel，完整链路
- **持续更新**：按 Android 版本持续追踪变化（稳定基准：Android 16，并持续跟踪 Android 17 变化）
- **源码级引用**：每个知识点标注 AOSP 源码路径，可追溯验证
- **实战驱动**：大量来自一线性能优化的真实案例

## 内容结构

- **第一部分：Android 系统运行机制** — 架构、渲染、输入、内存、CPU/功耗、存储
- **第二部分：性能专题** — 流畅性、响应速度、ANR、内存性能、功耗、包体积
- **第三部分：工具与方法论** — Perfetto、Simpleperf、MAT、dumpsys、APM、方法论
- **第四部分：系统级优化与行业实践** — AOSP 优化、厂商实践
- **第五部分：应用层优化** — 稳定性、启动、渲染、内存、I/O、功耗、可观测性

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
├── src/              # 书的内容源文件（中文）
├── intake/           # 外部输入（建议、资料）
├── metadata/         # 项目元数据
├── evidence/         # 验证证据（Trace、截图、源码引用）
├── logs/             # review / research / integration 日志
├── openclaw-tasks/   # 内容流水线任务定义
├── scripts/          # 辅助脚本
└── i18n/             # 国际化相关（术语映射等，v1.0 后启用）
```

## 内容验证标准

章节 frontmatter 目前主要跟踪工作流状态，如 `ready-for-review`、`finalized`。
正文中的知识点级标注仍使用以下验证状态：

- `verified` — 已通过 AOSP 源码或实机验证
- `draft` — 初稿完成，等待验证
- `needs-review` — 需要人工审核
- `outdated` — 存在已知过时部分

## 项目进度

当前阶段：**alpha**（目录已扩展到 ch01-ch26，正文持续批量 review / finalize）

| 部分 | 章节数 | 内容文件数 | 状态 |
|------|--------|------------|------|
| Part 1: 系统运行机制 | 6 | 97 文件 | 🔄 主体已成型，持续精修 |
| Part 2: 性能专题 | 7 | 89 文件 | 🔄 主体已成型，持续精修 |
| Part 3: 工具与方法论 | 4 | 79 文件 | 🔄 持续精修 |
| Part 4: 系统级优化 | 2 | 17 文件 | 🔄 持续补齐 |
| Part 5: 应用层优化 | 7 | 123 文件 | 🔄 批量加工与 review 中 |
| 前言 + 附录 | - | 12 文件 | ⏳ 前言待补齐，附录已部分完成 |

目前 `src/` 中已有 400+ 篇 Markdown 内容文件。正文主体以 `ready-for-review`
和 `finalized` 为主，但全书尚未公开发布。

详细路线图见 [metadata/roadmap.md](metadata/roadmap.md)

## 贡献

欢迎贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解贡献方式和规范。

## 关于 AI 辅助

本项目使用 AI Agent（OpenClaw）辅助内容加工：
- AI 负责：素材整理、结构化、初稿生成、格式校验
- 人工负责：技术判断、内容审核、最终定稿
- 所有 AI 生成的内容都经过人工审核和修改

## License

本作品采用 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) 许可协议。

> 注：本书引用的 AOSP 源码遵循 Apache License 2.0。引用他人内容均已标注原始出处，仅用于技术说明目的。
