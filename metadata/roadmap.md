# 项目路线图

## 当前状态（2026-08-11）

- 框架搭建：完成
- 内容范围：正文已经覆盖 ch01-ch26、前言、附录和若干 Android 17 / 工具链扩展条目
- 当前阶段：alpha 内容收敛期，按章逐篇审阅、合并重复正文并统一编号
- 发布形态：mdBook 中文版优先，英文版在 v1.0 中文内容冻结后启动
- 当前风险：目录架构已经恢复，但正文仍有 293 篇尚未进入 `ready-to-publish`；活动 queue 还有 9 条 `body-applied` 待后续复核，遗留状态名仍需收敛

当前统计口径：

| 口径 | 数量 | 说明 |
|------|------|------|
| 规范章节正文 | 609 篇 | 396 finalized、211 ready-for-review、1 verified、1 outdated |
| `src/SUMMARY.md` | 648 个本地链接 | 覆盖前言、26 章、附录和全部保留正文，0 失效、0 重复 |
| `metadata/queue.json` | 23 条 | 9 body-applied、7 rejected、5 superseded、1 review-finalized、1 completed |
| `pipeline_stage=ready-to-publish` | 316 篇 | 来自规范章节正文 frontmatter 聚合 |

当前工作重点：

| 优先级 | 工作 | 说明 |
|--------|------|------|
| P0 | 复核 `metadata/queue.json` 的 body-applied 项 | 当前剩余时效性与 DeepResearch 条目 |
| P0 | 逐章收敛重复与过拆正文 | 每章完整阅读、同步活动引用和统计后独立提交；进度见 `content-consolidation-audit.md` |
| P0 | 统一遗留状态名 | 收敛 status / pipeline_stage 的旧枚举，避免发布判断分叉 |
| P1 | 完整构建验证 | 在具备 mdBook + Mermaid 的环境持续执行 HTML 构建 |
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
- [x] 元数据检查恢复稳定通过
- [x] `metadata/progress.json` 与规范章节 frontmatter 原始扫描完成口径对齐

### M4: Alpha 精修收敛（目标：2026-Q3）

- [x] `src/SUMMARY.md` 重建并覆盖发布范围
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
