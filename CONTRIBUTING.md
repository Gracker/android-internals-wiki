# 贡献指南

欢迎提 Issue 和 Pull Request。

这本书的机制来自 AOSP、官方文档和公开资料，作者做的是按 Android 17 核对、整理和写清适用范围。写错了请直接指出。合并由维护者人工完成。

## 参与方式

两条路就够：

1. **Issue**：报错、提问、建议补哪一章。
2. **Pull Request**：直接改正文。适合错别字、失效链接、事实勘误、补例子或观测方法。

新章节、整节重写、大段案例，先开 Issue 说清楚要补什么、依据是什么，讨论后再写 PR。

### 提交之后会发生什么

仓库每天 **11:40** 和 **19:40**（Asia/Shanghai）会跑一次社区处理任务，读取还没分流的 Issue 和 PR，一次处理一条：

- 致谢，并打上 `typo` / `fact-error` / `new-content` / `question` / `needs-evidence` / `needs-human` / `android-17` 这类标签。
- 缺 Android 版本、AOSP 路径或官方文档、期望与实际现象时，会在评论里请你补。
- 对 PR 做第一轮核对。新增章节、缺来源、结论超过 Android 17、整篇搬运原文，会 `request-changes`。
- **不会改书，不会 `git push`，不会合 PR。**

所以你可能会先收到一条分流评论，再等维护者合入。没有时限承诺。明显 spam 或完全重复的 Issue 才可能被关掉。

## 开 Issue 时请写清

用仓库里的 Issue 模板最省事。无论用不用模板，尽量带上：

- 章节号或文件路径，例如 `2.3` 或 `src/part1-fundamentals/ch02-rendering/03-vsync-choreographer-sf-scheduling.md`
- 现在怎么写、你认为应该怎么写
- **Android 版本**。正文确定性结论最高到 Android 17 / API 37，源码标签是 `android-17.0.0_r1`（内核是 `android17-6.18-2026-06_r6`）。Android 18 及之后的材料不要当成当前结论
- AOSP 路径、官方文档 URL，或可复现的观察方法
- 期望现象和实际现象（如果是排障类问题）

没有这些信息时，定时任务会打 `needs-evidence`，等你补完再往下走。

## 开 Pull Request 时

- 从 `master` 拉分支，改动尽量小，一个 PR 只做一件事。
- 正文在 `src/` 下，目录以 [`src/SUMMARY.md`](src/SUMMARY.md) 为准。不要新建历史目录名（`src/chXX-*`、`partX-*` 这类）。
- 不要改 `metadata/queue.json`、`metadata/progress.json` 等流水线文件，除非维护者明确要你改。
- 提交说明写人话即可，例如 `fix: 2.3 更正 Choreographer 回调顺序的源码路径`。
- 许可按 [CC BY-NC-SA 4.0](LICENSE)。提交 PR 即表示你的贡献按同一许可授权。

小的事实修正可以直接 PR。拿不准就先 Issue。

## 正文要求

- 技术结论能回到源码、官方文档或可复现观察。不要补不存在的 API、类、路径、时延或厂商保证。
- 不要整篇搬运别人的文章。可以提取事实，用自己的话重写，并标明出处。
- 章节开头的 YAML 至少包含 `title`、`chapter`、`status`、`applicable_versions`、`tags`。`status` 用 `draft` / `ready-for-review` / `finalized`。不要在新稿里再引入 `verified`、`needs-review`、`outdated` 这些旧名。
- 源码路径、类名、线程名、trace 轨道名保持原样。中英文术语与邻近章节一致。
- 生成图、扫描报告、分析草稿放在 `src/` 之外。

## 翻译

完整英文版计划在 v1.0 之后进行，见 [`i18n/TRANSLATION-PLAN.md`](i18n/TRANSLATION-PLAN.md)。现在先把中文正文改对。

## 致谢

合入的贡献者会记在 README 的贡献者列表里。v1.0 出书时也会写进致谢。

## 维护者内部约定

队列、frontmatter 工作流字段、目录冻结规则见 [`docs/pipeline.md`](docs/pipeline.md)。外部贡献者不需要读那份文件。
