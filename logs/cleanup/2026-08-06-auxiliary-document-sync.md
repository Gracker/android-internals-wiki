# 辅助文档与元数据架构同步

- 日期：2026-08-06
- 前置正文清理：`logs/cleanup/2026-08-06-body-architecture-restoration.md`
- 架构依据：`metadata/v1.0-definition.md`、`src/SUMMARY.md`
- 范围：README、发布标准、元数据、素材索引、OpenClaw 任务说明、翻译计划、Knowledge Pack 与校验脚本；历史扫描/Review 日志不追改。

## 结果

- README、roadmap、v1.0 标准和翻译计划统一为五部分、26 章、622 篇规范正文、661 个 SUMMARY 本地链接。
- `metadata/queue.json` 收敛为 17 个对象：9 pending、7 rejected、1 completed；每条均带现存 `target_path`，7 个旧 Gap Mining 新章候选映射回已有正文。
- `metadata/inventory.json` 移除 438 条 AIW 项目自索引正文记录，并清空 95 条同类 `last_scan_new_docs`；当前只保留 7,369 条项目外 Obsidian 素材。
- `metadata/source-index.json` 修正 5 个尾随反引号路径；保留采集时路由标签，并为 20 条已有 `target_path` 的记录派生 `canonical_target_chapter`。
- 高质量素材索引的旧 17 章标签已重新映射到当前章节；缺少足够内容证据的旧库存标签保留为历史值，后续重新分类时更新。
- Task 1/7/11 明确排除整个 `Android-Internal-Wiki/**`；Task 7/8/10/11 使用当前章节映射，无法匹配时进入人工分配，不再强制归入 ch16/ch17。
- 旧 Task 2 单通道任务标记停用；未处理人工请求和历史 Gap Mining 候选改为并入现有正文，禁止创建新章节。
- Knowledge Pack 改为 26 个规范章节目录白名单，投影版本递增到 3；前言、附录、重复、空白、废弃路径和生成物不进入正文包。
- 元数据检查与进度统计脚本改为扫描规范章节白名单，异常 Part/Chapter 目录会直接报错。

## 历史边界

- `logs/**`、`changelog/**`、已关闭 review finding、旧 scan/freshness/task8 report 和 queue backup 保留事件发生时的旧路径、旧编号与旧统计。
- `metadata/source-index.json` 中没有 `target_path` 的旧素材条目不做无证据机械重分类。
- 本轮不修改或提交任何章节正文；并发任务产生的正文改动保持独立。

## 校验

- JSON 解析、queue/source-index/inventory 路径与数量断言：通过。
- 622 篇规范正文全部出现在 `src/SUMMARY.md`：通过。
- `python3 scripts/check-summary-links.py`：661 个本地链接，0 失效，0 重复。
- `python3 scripts/check-metadata.py`：622 个正文通过，0 个结构/元数据失败；38 个既有可选字段警告。
- `python3 -m unittest discover -s tests -p 'test_knowledge_pack.py'`：15 项通过。
- `git diff --check`：通过。
- TUF 测试未执行：当前系统 Python 缺少 `tuf` 依赖；本机也未安装 `mdbook`，未执行 HTML 构建。
