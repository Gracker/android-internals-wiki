# 贡献规范

本文面向当前 AIW alpha 精修期。仓库里还保留了一些早期状态名和历史脚本，新改动请遵循下面的当前规则。

## OpenClaw 操作规范

### Commit Message 格式

```
[openclaw] <type>: <章节号> <描述>
```

Type 类型：
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

### Review Commit Message 格式

```
[review] <action>: <章节号> <描述>
```

Action 类型：
- `approve` — 审核通过，从 staging 合入 src
- `reject` — 驳回，移入 staging/rejected 并记录理由

示例：
```
[review] approve: ch02.3 VSync 机制 — 已审核通过
[review] reject: ch05.2 EAS 部分不准确 — 需要重新验证
```

## 内容元数据标准

每篇正文内容的头部必须包含 YAML 元数据。新写或大修章节优先使用以下字段：

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

说明：

- `status` 表示正文成熟度。当前主状态为 `draft`、`ready-for-review`、`finalized`。
- `pipeline_stage` 表示流水线位置。发布就绪使用 `ready-to-publish`。
- 早期遗留的 `verified`、`needs-review`、`outdated`、`fixed-lite` 可被脚本兼容，但不要在新章节里继续引入。
- `src/preface/`、`src/appendix/`、`src/graphify-out/` 可按内容需要简化字段，但不得缺少标题和来源边界。

## 内容融入策略

### 高质量原创文章
保留核心表达和观点，重新组织结构以符合章节逻辑，补充引用和交叉链接。

### 笔记片段
提取知识点融入章节，不保留原始结构，标注来源路径。

### 收藏的他人文章
绝不直接搬运，只提取事实性知识点用自己的语言重述，标注原始出处。

## 验证标注规范

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
- `metadata/progress.json`：精修跟踪子集，不等同于 `src/` 全量文件数量。
- `metadata/source-index.json`：素材索引。大文件操作应优先使用 `scripts/source_index_helper.py`。
- `intake/suggestions.md`、`intake/research-gaps.md`、`intake/manual-requests/`：人工建议、知识缺口、手动请求的落点。
- `logs/`：review、research、rework、integration 的证据链。

非权威或临时文件不要作为流水线输入：

- 根目录的 `queue.json`、`source-index.json`
- `temp_entries.json`、`telegram-output.md`、`rework-result-*.txt`
- `metadata/*.backup`、`metadata/*.bak`、`metadata/*.tmp`
- `src/**/*.bak`、根目录源码摘录 `*_java.txt` / `*_cpp.txt`

## 社区贡献指南

### 贡献类型

**类型 1：修正与完善（欢迎直接提 PR）**
- 修正事实性错误、过时内容、语法错误
- 添加或改进验证标注
- 改进代码示例
- 修复交叉引用链接

**类型 2：新增内容（请先开 Issue 讨论）**
- 新增章节或小节
- 大幅重写现有内容
- 添加新的案例研究

**类型 3：翻译贡献（v1.0 后启动）**
- 参与英文版翻译，详见 i18n/TRANSLATION-PLAN.md

### 贡献者致谢
所有被合并的 PR 贡献者将被列入：
- 项目 README 的「贡献者」部分
- 书的「致谢」章节（v1.0 发布时）

### Review 时效
- P1（核心章节 ch01-ch12）：7 天内 review
- P2（工具与方法论 ch13-ch15）：14 天内 review
- P3（系统级优化 ch16-ch17、附录）：30 天内 review
