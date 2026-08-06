# Metadata 维护边界

本目录同时保存活动状态、素材索引和历史审计快照。它们的更新规则不同，不能把所有文件当成“当前事实”整体重写。

## 当前权威文件

| 文件 | 用途 | 更新规则 |
|---|---|---|
| `v1.0-definition.md` | 5 部分、26 章的规范架构与发布标准 | 目录结构变化时更新 |
| `progress.json` | 规范章节正文 frontmatter 的聚合快照 | 从正文重新统计，不手工猜测总数 |
| `queue.json` | 尚待处理或已明确解决的工作项 | 顶层为对象数组；同一目标/问题去重 |
| `source-index.json` | 外部素材、历史路由标签及当前目标正文 | 活动 `target_path` 必须指向现存规范正文；`canonical_target_chapter` 从该路径派生，旧 `chapter` 仅作路由审计 |
| `review-findings.json` | Review finding 审计账本 | `open` finding 必须指向现存正文；已关闭 finding 可保留发生时旧路径 |
| `inventory.json` | 项目外 Obsidian 素材资产清单 | 必须排除整个 AIW 仓库；旧素材的 `mapped_chapters` 仅在重新分类时更新，新记录使用当前 26 章映射 |

## 历史快照

以下文件用于还原当时的扫描或任务结果，不追改其中的旧统计、旧章节号或旧路径：

- `scan-report-*`、`freshness-report-*`、`task8-report-*`、`last-scan-report.md`
- `duplicate-cleanup-log.md`、`review-log.json`、`verification-log.json`
- `queue*.bak`、`queue*backup*`、`locks/**/archive/`

历史快照不得重新作为当前章节路径、总数或队列状态的来源。

## 路径规则

- 当前正文路径以 `v1.0-definition.md` 和 `src/SUMMARY.md` 为准。
- 正文迁移后，同步更新活动 queue、`source-index.json` 的 `target_path` 和未关闭 finding。
- `source-index.json` 中没有 `target_path` 的旧索引条目保留采集时章节标签，不在缺少内容证据时机械改写。
- 已关闭 finding、历史日志和扫描报告保留原始路径，以维护可审计性。
- 不得把本仓库中的正文、README、日志或元数据再次索引为“外部素材”。
