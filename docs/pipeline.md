# 仓库内部约定

给维护者和自动化车道看。外部贡献者走 [CONTRIBUTING.md](../CONTRIBUTING.md)。

本文面向当前 AIW 精修期。仓库里还保留了一些早期状态名和历史脚本，新改动请遵循下面的当前规则。

## Commit Message 格式

自动化车道常用：

```
[openclaw] <type>: <章节号> <描述>
```

Type：

- `draft` — 新建或更新草稿
- `verify` — 验证内容并标注
- `fix` — 修正内容错误
- `intake` — 处理外部输入资料
- `meta` — 更新元数据（inventory、progress 等）

示例：

```
[openclaw] draft: ch02.3 VSync 机制初稿
[openclaw] verify: ch01.5 确认 DeliQueue 源码路径
[openclaw] fix: ch09.2 更新 ANR 超时数值（Android 16 变更）
[openclaw] intake: 处理 external-resources/xxx.pdf
```

社区贡献的 PR 不强制这套前缀，人话说明即可。

### Review Commit Message 格式

```
[review] <action>: <章节号> <描述>
```

Action：

- `approve` — 审核通过
- `reject` — 驳回并记录理由

## 内容元数据

每篇正文头部需要 YAML。新写或大修章节优先使用：

```yaml
---
title: "章节标题"
chapter: "X.Y"
status: draft | ready-for-review | finalized
pipeline_stage: task6_pending | task9_pending | task2b_pending | ready-to-publish
applicable_versions: "Android X (API N) - Android Y (API M)"
last_verified: "YYYY-MM-DD"
last_verified_against: "AOSP branch"
confidence: high | medium | low
sources:
  - type: aosp | blog | official | paper
    path: "源码路径或 URL"
tags: [tag1, tag2]
related_chapters: ["X.Y", "X.Z"]
---
```

- `status` 表示正文成熟度。当前主状态为 `draft`、`ready-for-review`、`finalized`。
- `pipeline_stage` 表示流水线位置。发布就绪使用 `ready-to-publish`。
- 早期遗留的 `verified`、`needs-review`、`outdated`、`fixed-lite` 可被脚本兼容，不要在新章节里继续引入。
- `src/preface/`、`src/appendix/` 可按内容需要简化字段，但不得缺少标题和来源边界。生成图、扫描报告和其他分析产物必须放在 `src/` 之外。

字段白名单以 `scripts/frontmatter_schema.py` 为准。

## 内容融入策略

### 高质量原创文章

保留核心表达和观点，重新组织结构以符合章节逻辑，补充引用和交叉链接。

### 笔记片段

提取知识点融入章节，不保留原始结构，标注来源路径。

### 收藏的他人文章

绝不直接搬运，只提取事实性知识点用自己的语言重述，标注原始出处。

## 验证标注

- `[已验证: AOSP android-17.0.0_r1, frameworks/base/...]` — 源码验证
- `[已验证: 官方文档, developer.android.com/...]` — 官方文档验证
- `[待验证]` — 未能验证
- `[待补充]` — 内容缺失
- `[来源: obsidian/path/to/note.md]` — 素材来源
- `[引用: url]` — 外部引用
- `[适用版本: Android X - Android Y]` — 版本范围
- `[争议]` — 不同来源说法不一致

## 流水线文件边界

当前权威文件：

- `metadata/queue.json`：回炉、素材注入、人工请求队列。当前结构为列表；追加时保留既有条目，不要整体重写。
- `metadata/progress.json`：规范章节正文的聚合快照；由 frontmatter 原始扫描生成，不作为单篇正文的写入源。
- `metadata/source-index.json`：素材索引。大文件操作应优先使用 `scripts/source_index_helper.py`。
- `intake/suggestions.md`、`intake/research-gaps.md`、`intake/manual-requests/`：人工建议、知识缺口、手动请求的落点。
- `logs/`：review、research、rework、integration 的证据链。

目录与路径规则：

- 当前正文只能位于 `src/preface/`、`src/appendix/` 和 `metadata/v1.0-definition.md` 定义的 26 个规范章节目录。
- 不得重新创建 `src/chXX-*`、`partX-*`、`chchXX-*`、`part2-rendering` 等历史错位目录。
- 章节移动或合并后必须同步更新 `src/SUMMARY.md`、活动 queue、source-index 的 `target_path` 和未关闭 finding；历史日志与已关闭 finding 保留原路径。
- 新增章节文件或改 `src/SUMMARY.md` 时，提交说明需带 `[allow-new-aiw-chapter]`，否则 `scripts/check-no-new-chapters.py` 会拦截。

非权威或临时文件不要作为流水线输入：

- 根目录的 `queue.json`、`source-index.json`
- `temp_entries.json`、`telegram-output.md`、`rework-result-*.txt`
- `metadata/*.backup`、`metadata/*.bak`、`metadata/*.tmp`
- `src/**/*.bak`、根目录源码摘录 `*_java.txt` / `*_cpp.txt`

## GitHub 社区车道

Hermes 任务 `aiw-github-community` 每天 11:40 / 19:40 处理 1 条未分流的 Issue 或 PR。

- 允许：评论、打标签、`gh pr review --comment` / `--request-changes`
- 禁止：合 PR、push、改 `src/`、无故关 Issue
- 公开评论带 `<!-- aiw-community-bot -->`
- 标签：`needs-evidence`、`typo`、`fact-error`、`new-content`、`question`、`android-17`、`needs-human`

## 每周电子书

Hermes 任务 `aiw-weekly-ebook-release` 周日 10:00 从 `origin/master` 打包 EPUB，发到 GitHub Releases。正文归属信息（版权页、章末来源、页脚）由 `~/.hermes/scripts/aiw_weekly_ebook.py` 在打包时插入，不要把同样的页脚写进 280 篇正文。
