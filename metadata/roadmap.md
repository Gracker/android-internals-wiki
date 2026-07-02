# 项目路线图

## 当前状态（2026-07-02）

- 框架搭建：完成
- 内容范围：正文已经覆盖 ch01-ch26、前言、附录和若干 Android 17 / 工具链扩展条目
- 当前阶段：alpha 精修期，正文批量 review / finalize 持续进行
- 发布形态：mdBook 中文版优先，英文版在 v1.0 中文内容冻结后启动
- 当前风险：`src/SUMMARY.md` 是短目录，发布入口没有覆盖 `src/` 全量内容；`metadata/progress.json` 只统计精修子集，不等同于全量正文

当前统计口径：

| 口径 | 数量 | 说明 |
|------|------|------|
| `src/` frontmatter 原始扫描 | 545 文件 | `scripts/progress-report.py` 看到的正文元数据文件 |
| `metadata/progress.json` 精修子集 | 141 节 | 119 finalized、22 ready_for_review |
| `metadata/queue.json` | 18 条 | 13 pending、5 completed |
| `pipeline_stage=ready-to-publish` | 322 文件 | 来自 frontmatter 原始扫描 |

当前工作重点：

| 优先级 | 工作 | 说明 |
|--------|------|------|
| P0 | 重建 `src/SUMMARY.md` | 让 mdBook 发布目录重新覆盖 ch01-ch26 与附录 |
| P0 | 统一治理口径 | 明确 progress 精修子集、frontmatter 全量扫描、queue 待处理之间的关系 |
| P1 | 消费 `metadata/queue.json` pending 项 | 优先 Task6 / Task9 / DeepResearch 已入队问题 |
| P1 | 清理临时产物 | 根目录报告、旧 backup、临时 JSON 不再进入提交 |
| P2 | 前言与附录补齐 | 统一读者路径、版本约定、验证标准、术语表 |

## 里程碑

### M1: 初始框架就绪（已完成，2026-03-28）

- [x] mdBook 项目初始化
- [x] 初版 93 个小节创建
- [x] OpenClaw 定时任务配置
- [x] CI/CD 基础配置
- [x] 项目治理文档初版

### M2: 目录扩展与流水线成型（已完成，2026-05）

- [x] 目录扩展到 ch01-ch26
- [x] 新增 Part 5 应用层优化
- [x] 引入 Task2A / Task2B / Task6 / Task9 / Task11 的加工与 review 流水线
- [x] 建立 `metadata/progress.json`、`metadata/queue.json`、`logs/` 等状态记录

### M3: 工具与治理口径同步（目标：2026-06）

- [x] 进度统计脚本覆盖 ch01-ch26
- [x] README、roadmap、v1.0 发布标准与当前目录保持一致
- [x] 明确动态队列文件与人工治理文档的边界
- [ ] 元数据检查恢复稳定通过
- [ ] `metadata/progress.json` 与 frontmatter 原始扫描完成口径对齐

### M4: Alpha 精修收敛（目标：2026-Q3）

- [ ] `src/SUMMARY.md` 重建并覆盖发布范围
- [ ] Part 1-3 主体章节进入 `ready-to-publish`
- [ ] Part 4 关键章节完成版本边界与证据补齐
- [ ] Part 5 应用层章节完成首轮 Task6 / Task9 review
- [ ] 高优先级 `[待验证]` / `[待补充]` 标注完成归档或修复

### M5: v0.9-beta 发布准备（目标：2026-Q4）

- [ ] Part 1-3 完成发布前审校
- [ ] Part 4-5 标清发布范围与暂缓范围
- [ ] 前言和附录完成
- [ ] GitHub Pages 部署验证
- [ ] 社区公测，收集反馈

### M6: v1.0 正式发布

- [ ] 所有发布范围内章节完成技术审计
- [ ] 全书 L1/L2 验证覆盖达到发布标准
- [ ] 术语一致性检查通过
- [ ] 发布说明与版本边界说明完成

### M7: 英文版启动

- [ ] v1.0 中文内容冻结
- [ ] 翻译工作流搭建
- [ ] 社区翻译志愿者招募
