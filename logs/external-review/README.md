# external-review 归档说明

该目录用于归档外部 AI（如 Gemini）对 AIW 章节产生的 review 结果中的**高价值知识资产**，以及对应的结构化 review 摘要。

## 用途

这里不只是存“问题清单”，更重要的是保留：
- 一手资料索引
- 源码锚点
- 版本差异摘要
- Trace / Perfetto 观察点
- 可直接复用的技术结论

这些内容可被后续 AI 或人工直接参考，用于：
- 回炉修稿
- 补研究
- 补案例
- 补交叉引用
- 沉淀到章节参考资料或 wiki

## 文件命名

建议命名：

`YYYY-MM-DD-HH-{章节号}-external-review.md`

注意：**后续 task 主要按“章节号”匹配单章节 external-review 文件**，所以文件名里必须包含章节号，不能只写 slug 或文件序号。

示例：
- `2026-04-18-21-5.3-external-review.md`
- `2026-04-18-22-2.4-external-review.md`

## 最低内容要求

每份 external review 归档至少应包含：
1. Review 目标章节
2. 外部 review 核心结论
3. 回炉问题摘要（如有）
4. 知识盲区摘要（如有）
5. 可复用知识资产
6. 明确的章节号与源文件名

单章节文件是后续 task 的主要消费对象；batch summary 只作为辅助摘要，不替代单章节文件。

## 关系说明

- 必须修的问题 → `metadata/queue.json`
- 研究缺口 → `intake/research-gaps.md`
- 一般建议 → `intake/suggestions.md`
- 高价值知识资产 → 本目录归档

本目录是外部 review 的活跃输入区，不替代 queue / suggestions / research-gaps。

## 生命周期

### 活跃区
- `logs/external-review/` 根目录
- 只放**待消费 / 最近新增 / 尚未归档**的 external-review 文件
- 后续 task 默认只应优先读取这里的文件

### 归档区
- `logs/external-review/archive/`
- 放**已经被后续流程消费过**、主要用于留档复查的 external-review 文件
- 归档文件默认不应再被当成新的活跃输入重复消费

## 归档时机

当 external-review 的核心结果已经被整合进以下任一位置后，即可考虑归档：
- `metadata/queue.json`
- `intake/research-gaps.md`
- `intake/suggestions.md`
- 或对应章节已完成一次基于 external-review 的修稿 / 复审

如果不确定是否已被完整消费，宁可暂留在活跃区，不要过早归档。

## 归档辅助脚本

- 状态检查：
  `python3 scripts/external_review_archive_helper.py status`
- 归档已消费文件：
  `python3 scripts/external_review_archive_helper.py archive`
