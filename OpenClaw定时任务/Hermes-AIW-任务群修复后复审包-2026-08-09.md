# Hermes AIW 任务群修复后复审包 · 2026-08-09

> 目的：供第三方 Agent 对修复后的 Hermes AIW 定时任务群做二次 review。本文档重新从当前 `/Users/gracker/.hermes/cron/jobs.json`、`/Users/gracker/.hermes/scripts/` 与 AIW repo 状态生成，不复用旧文档结论。

## 0. 复审边界与硬约束

- 生成时间：`2026-08-09 01:07:38 CST`
- Hermes cron 配置：`/Users/gracker/.hermes/cron/jobs.json`
- Hermes scripts：`/Users/gracker/.hermes/scripts/`
- AIW Obsidian repo：`/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki`
- AIW Feishu work-copy：`/Users/gracker/.openclaw/workspace/Feishu/work-copies/Android-Internal-Wiki`
- Android 版本上限：**只到 Android 17 这个平台版本；不是 SDK 17；所有高于 Android 17 的内容必须跳过/忽略，不进入 AIW 正文结论。**
- 输出/日志规则：有用正式输出写 Obsidian；`~/.hermes` 只保存 cron 配置、脚本、state/evidence/cache。
- 本文档不包含 secrets；生成时对常见 token/key/password 形态做了 `[REDACTED]` 处理。

## 1. 任务群总览

- 当前 cron jobs 总数：`184`
- 命中 AIW / Android-Internal-Wiki / Feishu daily sync 相关 jobs：`30`
- scheduled：`18`
- paused / non-scheduled：`12`
- 需要 Hermes Agent LLM 执行的 AIW 相关 jobs：`9`（其中 6 条核心 AIW 写作/审核 lane 显式 pin 到 `gpt-5.5/openai-codex`；其余未 pin 的 non-no_agent job 使用 Hermes 默认模型/供应商）
- no_agent/script-only jobs：`21`（`no_agent=true`，不调用 LLM，脚本 stdout 直接投递/落盘）

### 1.1 scheduled jobs

| name | id | schedule | no_agent | model/provider | script | deliver | workdir |
|---|---|---|---:|---|---|---|---|
| `Things backlog triage to Obsidian queues` | `baf156b5982d` | `0 9 * * *` | `False` | `Hermes default model/provider（未 pin）` | `` | `telegram:-1003814981550` | `` |
| `aiw-body-apply` | `2aa21bb1eb45` | `15 7,9,11,13,15,17,19,21,23 * * *` | `False` | `gpt-5.5/openai-codex` | `aiw-body-apply-context.py` | `telegram:-1004339755728` | `/Users/gracker/.hermes/workspaces/aiw-body-apply` |
| `aiw-daily-intake-classify` | `51d73c474658` | `20 6 * * *` | `True` | `no_agent=true / no LLM` | `aiw-daily-intake-classify.py` | `telegram:-1004339755728` | `/Users/gracker/.hermes/workspaces/aiw-daily-intake` |
| `aiw-daily-intake-deepresearch` | `db79021b32a0` | `10 6 * * *` | `True` | `no_agent=true / no LLM` | `aiw-daily-intake-deepresearch.py` | `telegram:-1004339755728` | `/Users/gracker/.hermes/workspaces/aiw-daily-intake` |
| `aiw-daily-intake-incremental` | `2364b7bf9a07` | `45 5 * * *` | `True` | `no_agent=true / no LLM` | `aiw-daily-intake-incremental.py` | `telegram:-1004339755728` | `/Users/gracker/.hermes/workspaces/aiw-daily-intake` |
| `aiw-daily-intake-tech-articles` | `f50a04d870c3` | `25 5 * * *` | `True` | `no_agent=true / no LLM` | `aiw-daily-intake-tech-articles.py` | `local` | `/Users/gracker/.hermes/workspaces/aiw-daily-intake` |
| `aiw-git-sync` | `5fa9d7fe9e87` | `55 7-23 * * *` | `True` | `no_agent=true / no LLM` | `aiw-git-sync.py` | `telegram:-1004339755728` | `` |
| `aiw-polish-deep-review-apply` | `a2fb41f345c8` | `35 8,12,16,20 * * *` | `False` | `gpt-5.5/openai-codex` | `aiw-polish-deep-review-context.py` | `telegram:-1004339755728` | `/Users/gracker/.hermes/workspaces/aiw-polish-apply` |
| `aiw-polish-draft-polish-apply` | `ef444f87d299` | `35 11,15,19,23 * * *` | `False` | `gpt-5.5/openai-codex` | `aiw-polish-draft-polish-context.py` | `telegram:-1004339755728` | `/Users/gracker/.hermes/workspaces/aiw-polish-apply` |
| `aiw-polish-idle-audit-apply` | `fb934850da95` | `35 10,14,18,22 * * *` | `False` | `gpt-5.5/openai-codex` | `aiw-polish-idle-audit-context.py` | `telegram:-1004339755728` | `/Users/gracker/.hermes/workspaces/aiw-polish-apply` |
| `aiw-polish-rework-apply` | `410de74688cd` | `35 9,13,17,21 * * *` | `False` | `gpt-5.5/openai-codex` | `aiw-polish-rework-context.py` | `telegram:-1004339755728` | `/Users/gracker/.hermes/workspaces/aiw-polish-apply` |
| `aiw-review-finalize-apply` | `464ba760c0e3` | `5 8,10,12,14,16,18,20,22 * * *` | `False` | `gpt-5.5/openai-codex` | `aiw-review-finalize-context.py` | `telegram:-1004339755728` | `/Users/gracker/.hermes/workspaces/aiw-review-finalize-apply` |
| `aiw-throughput-watchdog` | `167290e723e9` | `58 23 * * *` | `True` | `no_agent=true / no LLM` | `aiw-throughput-watchdog.py` | `telegram:-1004339755728` | `/Users/gracker/.hermes/workspaces/aiw-polish-apply` |
| `aiw-weekly-source-audit-clippings` | `93d3c7568b39` | `30 6 * * *` | `True` | `no_agent=true / no LLM` | `aiw-weekly-source-audit-clippings-reference-scan.py` | `telegram:-1004339755728` | `/Users/gracker/.hermes/workspaces/aiw-weekly-source-audit` |
| `aiw-weekly-source-audit-freshness` | `c7fcfd963ce5` | `0 2 * * 1,3,5` | `True` | `no_agent=true / no LLM` | `aiw-weekly-source-audit-freshness-check.py` | `telegram:-1004339755728` | `/Users/gracker/.hermes/workspaces/aiw-weekly-source-audit` |
| `feishu-daily-sync-dry-run` | `2955f4f3f151` | `30 9 * * *` | `True` | `no_agent=true / no LLM` | `feishu-daily-sync-dry-run.py` | `telegram:-1003814981550` | `/Users/gracker/.hermes/workspaces/feishu-daily-sync` |
| `feishu-daily-sync-guarded-write` | `70e6cc5c0f14` | `40 9 * * *` | `True` | `no_agent=true / no LLM` | `feishu-daily-sync-guarded-write.py` | `telegram:-1003814981550` | `/Users/gracker/.hermes/workspaces/feishu-daily-sync` |
| `feishu-daily-sync-monitor` | `0002c4202fac` | `0 10 * * *` | `True` | `no_agent=true / no LLM` | `feishu-daily-sync-monitor.py` | `telegram:-1003814981550` | `/Users/gracker/.hermes/workspaces/feishu-daily-sync` |

### 1.2 paused / legacy jobs

| name | id | schedule | state | paused_reason | script |
|---|---|---|---|---|---|
| `aiw-queue-worker-dispatcher` | `f0f2cccb04ef` | `5 * * * *` | `paused` | `` | `aiw-queue-worker-dispatcher.py` |
| `aiw-queue-worker-source-research` | `87e270a88b46` | `50 2,5,8,11,14,17,20,23 * * *` | `paused` | `` | `aiw-queue-worker-source-research.py` |
| `aiw-queue-worker-task2a` | `07fc533fb059` | `0 8,14,20 * * *` | `paused` | `` | `aiw-queue-worker-task2a.py` |
| `aiw-queue-worker-task2b-lite` | `eddc94a6c35d` | `35 1-23/2 * * *` | `paused` | `` | `aiw-queue-worker-task2b-lite.py` |
| `aiw-queue-worker-task2b-main` | `2435d66a5a42` | `50 0-22/2 * * *` | `paused` | `` | `aiw-queue-worker-task2b-main.py` |
| `aiw-review-finalize-deep-tech-review` | `46fbf624b429` | `20 0-22 * * *` | `paused` | `` | `aiw-review-finalize-deep-tech-review.py` |
| `aiw-review-finalize-dispatcher` | `325ea8fa9195` | `10 * * * *` | `paused` | `` | `aiw-review-finalize-dispatcher.py` |
| `aiw-review-finalize-draft-review` | `59d136a6429d` | `5 1-23 * * *` | `paused` | `` | `aiw-review-finalize-draft-review.py` |
| `aiw-review-finalize-reader-final` | `087678486ac8` | `40 1,7,13,19 * * *` | `paused` | `` | `aiw-review-finalize-reader-final.py` |
| `aiw-review-finalize-task2b-verifier` | `9fbe57241199` | `25 3-23/4 * * *` | `paused` | `` | `aiw-review-finalize-task2b-verifier.py` |
| `clawfeed-daily-report-local` | `a0c290e16e09` | `0 4 * * *` | `paused` | `` | `clawfeed-daily-prepare.py` |
| `rss-gracker-report-local` | `30b5d8ac353c` | `0 3 * * *` | `paused` | `` | `rss-gracker-prepare.py` |

## 2. 修复后核心设计合同

### 2.1 LLM lane 事务边界

- LLM lane 的 pre-run script 必须输出完整、可解析 JSON。
- JSON 必须携带 `run_id`、`lane`、`base_sha`、`manifest_path`、`allowed_changed_paths`、`formal_report_path`。
- LLM lane 只允许改本轮 `target_path`、明确允许的 metadata/log/evidence/report 路径。
- LLM lane 禁止运行 `git add/commit/push/pull/rebase/autostash`，也禁止直接调用 `aiw-git-sync.py`。
- `aiw-git-sync.py` 是唯一提交 gate：读取 manifest，只 stage 本轮允许路径；若 worktree 有非本轮变更、HEAD != base_sha、缺 manifest 或 diff 超阈值，必须 blocked / needs-human-review。

### 2.2 证据与状态晋级合同

- finalized 必要条件：无 open P0/P1 finding；关键 claim 有可定位 `source_evidence`；版本边界已验证；本地 gate 通过。
- 不能仅凭脚本 exit 0、引用数量多、metadata check 通过或“没有明显问题”晋级。
- 降级必须写稳定 `finding_id`；重新晋级必须关闭对应 `finding_id` 并列 source evidence。
- idle-audit 无新证据/finding/正文变化时返回 `completed-no-change`，只写独立 evidence/log，不刷新章节 frontmatter，不提交。

### 2.3 selector / watchdog / freshness 合同

- `source_index_eligibility()` 是 selector 与 watchdog 的统一资格口径。
- `material_applied_in_body()` 只把正文来源 marker 视为已应用；frontmatter 中出现素材文件名不算已应用。
- freshness audit 去掉 YAML、代码块、历史 review/audit 段落后再检查正文；高于 Android 17 的命中带否定语境过滤；队列稳定去重 key 为 `target_path + rule_id + evidence`。

## 3. 六条 LLM 写作/审核 lane 重点复审

### 3.x `aiw-body-apply`

- job_id：`2aa21bb1eb45`
- schedule：`15 7,9,11,13,15,17,19,21,23 * * *`
- state：`scheduled`, enabled=`True`
- script：`aiw-body-apply-context.py`
- model：`gpt-5.5`
- provider：`openai-codex`
- base_url：`None`
- no_agent：`False`
- enabled_toolsets：`['terminal', 'file']`
- skills：`[]` / skill=`None`
- deliver：`telegram:-1004339755728`
- workdir：`/Users/gracker/.hermes/workspaces/aiw-body-apply`
- last_status：`ok`, last_run_at=`2026-08-08T23:15:01.310636+08:00`, next_run_at=`2026-08-09T07:15:00+08:00`
- prompt quick checks：`{'禁止自行 git 提交': True, 'Android17 上限': True, '完整事务字段': True, 'finding/source evidence': True}`

**完整 prompt：**

```text
通用事务与证据合同：
- 只处理 pre-run JSON 指定的一个 target_path；读取 run_id、lane、base_sha、manifest_path、allowed_changed_paths、formal_report_path。
- 开始前运行 git status --porcelain；若存在不属于 allowed_changed_paths 的脏改动，或 HEAD 与 base_sha 不一致，返回 blocked，不得吸收、覆盖或提交这些改动。
- 只允许修改 target_path、JSON 明确允许的 metadata/log 文件，以及本轮 evidence/report。禁止新增 src 文件，禁止修改 src/SUMMARY.md。
- 禁止运行 git add/commit/push/pull/rebase/autostash 或 aiw-git-sync.py；提交由独立 manifest gate 执行。
- Android baseline 固定 android-17.0.0_r1 / Android 17；禁止任何高于 Android 17 的主线结论。
- 状态降级必须写稳定 finding_id；重新晋级必须关闭对应 finding_id 并列 source_evidence。不能因脚本 exit 0、引用数量多、没发现新问题就提高状态。
- 只有实际核对源码/官方文档后，才能更新 last_source_verified_at 或提高 confidence；普通巡检只写 evidence，不刷新 source verified。
- 最终只输出简短 JSON：run_id,status,target_path,body_modified,frontmatter_modified,changed_paths,findings_opened,findings_closed,source_evidence,verification,blocked_reason。

你是 AIW Body Apply。若 pre-run status=no-candidate：返回上述 JSON，status=no-candidate，列出 scanned/ineligible/rejected_by_reason，不生成 0 字节输出。若 status=blocked：返回 blocked。若 candidate_ready：
1. 基于 materials 原文把材料编译进指定既有章节；每条关键技术断言带 [来源: material_id/filename] 或 [已验证: repo/tag/file/symbol/line]。
2. “材料已应用”只能由正文稳定 material_id/source marker 或等价 claim 证明；文件名只在 frontmatter/gap_source/review_notes 中出现不算已应用。
3. 应用后最多推进到 ready-for-review，不得 finalized；更新 queue/source-index 对应项为 body-applied/applied 并写 run_id,target_path。
4. 写唯一 formal_report_path 和 evidence，运行 check-metadata.py --files <target>、check-summary-links.py、git diff --check。

```

### 3.x `aiw-polish-deep-review-apply`

- job_id：`a2fb41f345c8`
- schedule：`35 8,12,16,20 * * *`
- state：`scheduled`, enabled=`True`
- script：`aiw-polish-deep-review-context.py`
- model：`gpt-5.5`
- provider：`openai-codex`
- base_url：`None`
- no_agent：`False`
- enabled_toolsets：`['terminal', 'file']`
- skills：`[]` / skill=`None`
- deliver：`telegram:-1004339755728`
- workdir：`/Users/gracker/.hermes/workspaces/aiw-polish-apply`
- last_status：`ok`, last_run_at=`2026-08-08T20:38:16.558832+08:00`, next_run_at=`2026-08-09T08:35:00+08:00`
- prompt quick checks：`{'禁止自行 git 提交': True, 'Android17 上限': True, '完整事务字段': True, 'finding/source evidence': True}`

**完整 prompt：**

```text
通用事务与证据合同：
- 只处理 pre-run JSON 指定的一个 target_path；读取 run_id、lane、base_sha、manifest_path、allowed_changed_paths、formal_report_path。
- 开始前运行 git status --porcelain；若存在不属于 allowed_changed_paths 的脏改动，或 HEAD 与 base_sha 不一致，返回 blocked，不得吸收、覆盖或提交这些改动。
- 只允许修改 target_path、JSON 明确允许的 metadata/log 文件，以及本轮 evidence/report。禁止新增 src 文件，禁止修改 src/SUMMARY.md。
- 禁止运行 git add/commit/push/pull/rebase/autostash 或 aiw-git-sync.py；提交由独立 manifest gate 执行。
- Android baseline 固定 android-17.0.0_r1 / Android 17；禁止任何高于 Android 17 的主线结论。
- 状态降级必须写稳定 finding_id；重新晋级必须关闭对应 finding_id 并列 source_evidence。不能因脚本 exit 0、引用数量多、没发现新问题就提高状态。
- 只有实际核对源码/官方文档后，才能更新 last_source_verified_at 或提高 confidence；普通巡检只写 evidence，不刷新 source verified。
- 最终只输出简短 JSON：run_id,status,target_path,body_modified,frontmatter_modified,changed_paths,findings_opened,findings_closed,source_evidence,verification,blocked_reason。

你是 AIW Polish deep-review lane。若 polish_candidate_ready：
1. 先产出 finding，再决定是否修改。每个 finding 包含 finding_id,severity,claim,evidence,target_range,recommended_action。
2. 仅出现“待验证”、高于 Android 17 的版本字样或历史 review note，不足以降级；必须证明正文存在仍生效且无支撑的肯定结论。
3. 大段删除前列出删除范围、原因和保留信息摘要；超过自动阈值（单章删除>120行或一次>3个 src 文件）返回 needs-human-review。
4. 小范围有证据问题可 patch；写 logs/deep-review、formal_report_path/evidence，并运行本地 gate。

```

### 3.x `aiw-polish-draft-polish-apply`

- job_id：`ef444f87d299`
- schedule：`35 11,15,19,23 * * *`
- state：`scheduled`, enabled=`True`
- script：`aiw-polish-draft-polish-context.py`
- model：`gpt-5.5`
- provider：`openai-codex`
- base_url：`None`
- no_agent：`False`
- enabled_toolsets：`['terminal', 'file']`
- skills：`[]` / skill=`None`
- deliver：`telegram:-1004339755728`
- workdir：`/Users/gracker/.hermes/workspaces/aiw-polish-apply`
- last_status：`ok`, last_run_at=`2026-08-08T23:39:22.507264+08:00`, next_run_at=`2026-08-09T11:35:00+08:00`
- prompt quick checks：`{'禁止自行 git 提交': True, 'Android17 上限': True, '完整事务字段': True, 'finding/source evidence': True}`

**完整 prompt：**

```text
通用事务与证据合同：
- 只处理 pre-run JSON 指定的一个 target_path；读取 run_id、lane、base_sha、manifest_path、allowed_changed_paths、formal_report_path。
- 开始前运行 git status --porcelain；若存在不属于 allowed_changed_paths 的脏改动，或 HEAD 与 base_sha 不一致，返回 blocked，不得吸收、覆盖或提交这些改动。
- 只允许修改 target_path、JSON 明确允许的 metadata/log 文件，以及本轮 evidence/report。禁止新增 src 文件，禁止修改 src/SUMMARY.md。
- 禁止运行 git add/commit/push/pull/rebase/autostash 或 aiw-git-sync.py；提交由独立 manifest gate 执行。
- Android baseline 固定 android-17.0.0_r1 / Android 17；禁止任何高于 Android 17 的主线结论。
- 状态降级必须写稳定 finding_id；重新晋级必须关闭对应 finding_id 并列 source_evidence。不能因脚本 exit 0、引用数量多、没发现新问题就提高状态。
- 只有实际核对源码/官方文档后，才能更新 last_source_verified_at 或提高 confidence；普通巡检只写 evidence，不刷新 source verified。
- 最终只输出简短 JSON：run_id,status,target_path,body_modified,frontmatter_modified,changed_paths,findings_opened,findings_closed,source_evidence,verification,blocked_reason。

你是 AIW Polish draft-polish lane。若 polish_candidate_ready：
1. 只打磨既有 draft，不新增章节，不编造源码结论。术语润色与事实修改分开报告。
2. draft 只有在结构完整、关键 claim 有证据、没有 unresolved marker、版本边界明确时才能推进 ready-for-review。materials 为空不自动阻止修改，但不能仅凭已有引用数量晋级；必须列出实际验证过的 claim。
3. 没有事实变化时，不更新 last_source_verified_at 或 confidence。
4. 写 logs/review、formal_report_path/evidence，并运行本地 gate。

```

### 3.x `aiw-polish-idle-audit-apply`

- job_id：`fb934850da95`
- schedule：`35 10,14,18,22 * * *`
- state：`scheduled`, enabled=`True`
- script：`aiw-polish-idle-audit-context.py`
- model：`gpt-5.5`
- provider：`openai-codex`
- base_url：`None`
- no_agent：`False`
- enabled_toolsets：`['terminal', 'file']`
- skills：`[]` / skill=`None`
- deliver：`telegram:-1004339755728`
- workdir：`/Users/gracker/.hermes/workspaces/aiw-polish-apply`
- last_status：`ok`, last_run_at=`2026-08-08T22:37:45.311476+08:00`, next_run_at=`2026-08-09T10:35:00+08:00`
- prompt quick checks：`{'禁止自行 git 提交': True, 'Android17 上限': True, '完整事务字段': True, 'finding/source evidence': True}`

**完整 prompt：**

```text
通用事务与证据合同：
- 只处理 pre-run JSON 指定的一个 target_path；读取 run_id、lane、base_sha、manifest_path、allowed_changed_paths、formal_report_path。
- 开始前运行 git status --porcelain；若存在不属于 allowed_changed_paths 的脏改动，或 HEAD 与 base_sha 不一致，返回 blocked，不得吸收、覆盖或提交这些改动。
- 只允许修改 target_path、JSON 明确允许的 metadata/log 文件，以及本轮 evidence/report。禁止新增 src 文件，禁止修改 src/SUMMARY.md。
- 禁止运行 git add/commit/push/pull/rebase/autostash 或 aiw-git-sync.py；提交由独立 manifest gate 执行。
- Android baseline 固定 android-17.0.0_r1 / Android 17；禁止任何高于 Android 17 的主线结论。
- 状态降级必须写稳定 finding_id；重新晋级必须关闭对应 finding_id 并列 source_evidence。不能因脚本 exit 0、引用数量多、没发现新问题就提高状态。
- 只有实际核对源码/官方文档后，才能更新 last_source_verified_at 或提高 confidence；普通巡检只写 evidence，不刷新 source verified。
- 最终只输出简短 JSON：run_id,status,target_path,body_modified,frontmatter_modified,changed_paths,findings_opened,findings_closed,source_evidence,verification,blocked_reason。

你是 AIW Polish idle-audit lane。若 polish_candidate_ready：
1. 做 finalized/verified 章节抽检，只找仍生效的 高于 Android 17 的版本越界、待验证残留、来源标记不足、明显技术/表达问题。
2. 若审计通过且没有新证据、finding 或正文变化，返回 status=completed-no-change；只写独立 audit evidence/log，不修改章节文件，不刷新 frontmatter 时间戳，不提交。
3. 只有发现问题、关闭 finding 或获得新来源证据时才改正文/frontmatter；严重问题降级并写 finding_id。
4. 写 logs/audit、formal_report_path/evidence，并运行本地 gate（若没有改章节，可只说明未运行 metadata gate原因）。

```

### 3.x `aiw-polish-rework-apply`

- job_id：`410de74688cd`
- schedule：`35 9,13,17,21 * * *`
- state：`scheduled`, enabled=`True`
- script：`aiw-polish-rework-context.py`
- model：`gpt-5.5`
- provider：`openai-codex`
- base_url：`None`
- no_agent：`False`
- enabled_toolsets：`['terminal', 'file']`
- skills：`[]` / skill=`None`
- deliver：`telegram:-1004339755728`
- workdir：`/Users/gracker/.hermes/workspaces/aiw-polish-apply`
- last_status：`ok`, last_run_at=`2026-08-08T21:38:52.197016+08:00`, next_run_at=`2026-08-09T09:35:00+08:00`
- prompt quick checks：`{'禁止自行 git 提交': True, 'Android17 上限': True, '完整事务字段': True, 'finding/source evidence': True}`

**完整 prompt：**

```text
通用事务与证据合同：
- 只处理 pre-run JSON 指定的一个 target_path；读取 run_id、lane、base_sha、manifest_path、allowed_changed_paths、formal_report_path。
- 开始前运行 git status --porcelain；若存在不属于 allowed_changed_paths 的脏改动，或 HEAD 与 base_sha 不一致，返回 blocked，不得吸收、覆盖或提交这些改动。
- 只允许修改 target_path、JSON 明确允许的 metadata/log 文件，以及本轮 evidence/report。禁止新增 src 文件，禁止修改 src/SUMMARY.md。
- 禁止运行 git add/commit/push/pull/rebase/autostash 或 aiw-git-sync.py；提交由独立 manifest gate 执行。
- Android baseline 固定 android-17.0.0_r1 / Android 17；禁止任何高于 Android 17 的主线结论。
- 状态降级必须写稳定 finding_id；重新晋级必须关闭对应 finding_id 并列 source_evidence。不能因脚本 exit 0、引用数量多、没发现新问题就提高状态。
- 只有实际核对源码/官方文档后，才能更新 last_source_verified_at 或提高 confidence；普通巡检只写 evidence，不刷新 source verified。
- 最终只输出简短 JSON：run_id,status,target_path,body_modified,frontmatter_modified,changed_paths,findings_opened,findings_closed,source_evidence,verification,blocked_reason。

你是 AIW Polish rework lane。若 polish_candidate_ready：
1. 只处理 context 或章节/metadata 中明确列出的 finding_id / needs-rework 项。
2. 每项修改必须说明关闭了哪个 finding；未能关闭的 finding 保持 open。
3. 不顺带重写同章其他内容，不用“清理措辞”代替证据。
4. 修复后按证据把状态推回 ready-for-review 或保持 needs-rework；写 logs/rework、formal_report_path/evidence，并运行本地 gate。

```

### 3.x `aiw-review-finalize-apply`

- job_id：`464ba760c0e3`
- schedule：`5 8,10,12,14,16,18,20,22 * * *`
- state：`scheduled`, enabled=`True`
- script：`aiw-review-finalize-context.py`
- model：`gpt-5.5`
- provider：`openai-codex`
- base_url：`None`
- no_agent：`False`
- enabled_toolsets：`['terminal', 'file']`
- skills：`[]` / skill=`None`
- deliver：`telegram:-1004339755728`
- workdir：`/Users/gracker/.hermes/workspaces/aiw-review-finalize-apply`
- last_status：`ok`, last_run_at=`2026-08-08T22:08:25.704099+08:00`, next_run_at=`2026-08-09T08:05:00+08:00`
- prompt quick checks：`{'禁止自行 git 提交': True, 'Android17 上限': True, '完整事务字段': True, 'finding/source evidence': True}`

**完整 prompt：**

```text
通用事务与证据合同：
- 只处理 pre-run JSON 指定的一个 target_path；读取 run_id、lane、base_sha、manifest_path、allowed_changed_paths、formal_report_path。
- 开始前运行 git status --porcelain；若存在不属于 allowed_changed_paths 的脏改动，或 HEAD 与 base_sha 不一致，返回 blocked，不得吸收、覆盖或提交这些改动。
- 只允许修改 target_path、JSON 明确允许的 metadata/log 文件，以及本轮 evidence/report。禁止新增 src 文件，禁止修改 src/SUMMARY.md。
- 禁止运行 git add/commit/push/pull/rebase/autostash 或 aiw-git-sync.py；提交由独立 manifest gate 执行。
- Android baseline 固定 android-17.0.0_r1 / Android 17；禁止任何高于 Android 17 的主线结论。
- 状态降级必须写稳定 finding_id；重新晋级必须关闭对应 finding_id 并列 source_evidence。不能因脚本 exit 0、引用数量多、没发现新问题就提高状态。
- 只有实际核对源码/官方文档后，才能更新 last_source_verified_at 或提高 confidence；普通巡检只写 evidence，不刷新 source verified。
- 最终只输出简短 JSON：run_id,status,target_path,body_modified,frontmatter_modified,changed_paths,findings_opened,findings_closed,source_evidence,verification,blocked_reason。

你是 AIW Review/Finalize Apply。若 status=no-candidate 返回 no-candidate；若 review_candidate_ready：
1. 对指定章节做源码准确性、版本边界、来源支撑、中文可读性、待验证项审查，可做小范围安全 patch。
2. finalized 必要条件：没有 open P0/P1 finding；关键 claim 都有可定位 source_evidence；版本边界已验证；本地 gate 全部通过。materials 为空时可自行查本地源码，但必须结构化记录证据；无法形成证据则保持 ready-for-review 或转 needs-rework。
3. 不要把“引用看起来足够”“metadata 检查通过”“没有明显问题”单独作为 finalized 依据。
4. 写 formal_report_path/evidence，运行本地 gate。

```

## 4. 所有 AIW 相关 job 明细

### 4.1 `Things backlog triage to Obsidian queues`

- id: `baf156b5982d`
- state: `scheduled`
- enabled: `True`
- schedule: `{'kind': 'cron', 'expr': '0 9 * * *', 'display': '0 9 * * *'}`
- created_at: `2026-07-23T23:59:07.331807+08:00`
- last_run_at: `2026-08-08T09:06:43.267952+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-08-09T09:00:00+08:00`
- deliver: `telegram:-1003814981550`
- no_agent: `False`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: `['terminal', 'file']`
- skills: `['things-obsidian-task-triage', 'obsidian-hermes', 'gracker-deep-research']`
- skill: `things-obsidian-task-triage`
- script: ``
- workdir: ``
- context_from: ``
- repeat: `{'times': None, 'completed': 16}`

**prompt：**

```text
每天清理 Things backlog 中的 5 个未完成任务，并把所有有用产物落盘到 Obsidian。你是在 macOS 上运行，Things CLI 为 `/opt/homebrew/bin/things`，Obsidian vault 路径为 `/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian`。严格遵循已加载 skill `things-obsidian-task-triage`。执行步骤：1) 读取 `things today`，选择当前列表前 5 个未完成任务；如果相邻/明显重复项与这 5 个同题，允许一并去重处理，但在报告中说明。2) 按标题前缀分类：`[深度研究]` 写入 `OpenClaw定时任务/Things清理/深度调研任务队列.md`；`[内容动作]` 写入 `内容创作任务队列.md`；`[工程动作]`/`[项目推进]` 写入 `工程与项目任务队列.md`。3) 对每个归一化任务审计来源/产出闭环：搜索 Obsidian 中的每日内容提案、晨间简报、AIW src、metadata/queue.json、DeepResearch、论文目录，记录 source/producer、是否 AIW 闭环、缺什么闭环。4) 所有队列和当日报告必须写入 Obsidian `OpenClaw定时任务/Things清理/`，不要把有用输出只放 `~/.hermes`。iCloud vault 写入使用 `python3 + pathlib`。5) 队列写入成功后勾掉对应 Things 任务：优先 `things update --id ... --completed`；如果 `THINGS_AUTH_TOKEN` 未配置且用户已要求勾掉，先给 Things SQLite `main.sqlite` 做时间戳备份，再只更新已验证 UUID 行为完成（status=3, stopDate/userModificationDate=now），最后用 `things search --status completed` 或 `things today` 验证。6) 最终回复简短说明：处理数量、去重数量、队列路径、Things 勾选验证、当天闭环判断。不要递归创建/修改 cron。
```

### 4.2 `aiw-body-apply`

- id: `2aa21bb1eb45`
- state: `scheduled`
- enabled: `True`
- schedule: `{'kind': 'cron', 'expr': '15 7,9,11,13,15,17,19,21,23 * * *', 'display': '15 7,9,11,13,15,17,19,21,23 * * *'}`
- created_at: `2026-07-19T18:30:37.791315+08:00`
- last_run_at: `2026-08-08T23:15:01.310636+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-08-09T07:15:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `False`
- model: `gpt-5.5`
- provider: `openai-codex`
- base_url: ``
- enabled_toolsets: `['terminal', 'file']`
- skills: `[]`
- skill: ``
- script: `aiw-body-apply-context.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-body-apply`
- context_from: ``
- repeat: `{'times': None, 'completed': 153}`

**prompt：**

```text
通用事务与证据合同：
- 只处理 pre-run JSON 指定的一个 target_path；读取 run_id、lane、base_sha、manifest_path、allowed_changed_paths、formal_report_path。
- 开始前运行 git status --porcelain；若存在不属于 allowed_changed_paths 的脏改动，或 HEAD 与 base_sha 不一致，返回 blocked，不得吸收、覆盖或提交这些改动。
- 只允许修改 target_path、JSON 明确允许的 metadata/log 文件，以及本轮 evidence/report。禁止新增 src 文件，禁止修改 src/SUMMARY.md。
- 禁止运行 git add/commit/push/pull/rebase/autostash 或 aiw-git-sync.py；提交由独立 manifest gate 执行。
- Android baseline 固定 android-17.0.0_r1 / Android 17；禁止任何高于 Android 17 的主线结论。
- 状态降级必须写稳定 finding_id；重新晋级必须关闭对应 finding_id 并列 source_evidence。不能因脚本 exit 0、引用数量多、没发现新问题就提高状态。
- 只有实际核对源码/官方文档后，才能更新 last_source_verified_at 或提高 confidence；普通巡检只写 evidence，不刷新 source verified。
- 最终只输出简短 JSON：run_id,status,target_path,body_modified,frontmatter_modified,changed_paths,findings_opened,findings_closed,source_evidence,verification,blocked_reason。

你是 AIW Body Apply。若 pre-run status=no-candidate：返回上述 JSON，status=no-candidate，列出 scanned/ineligible/rejected_by_reason，不生成 0 字节输出。若 status=blocked：返回 blocked。若 candidate_ready：
1. 基于 materials 原文把材料编译进指定既有章节；每条关键技术断言带 [来源: material_id/filename] 或 [已验证: repo/tag/file/symbol/line]。
2. “材料已应用”只能由正文稳定 material_id/source marker 或等价 claim 证明；文件名只在 frontmatter/gap_source/review_notes 中出现不算已应用。
3. 应用后最多推进到 ready-for-review，不得 finalized；更新 queue/source-index 对应项为 body-applied/applied 并写 run_id,target_path。
4. 写唯一 formal_report_path 和 evidence，运行 check-metadata.py --files <target>、check-summary-links.py、git diff --check。

```

### 4.3 `aiw-daily-intake-classify`

- id: `51d73c474658`
- state: `scheduled`
- enabled: `True`
- schedule: `{'kind': 'cron', 'expr': '20 6 * * *', 'display': '20 6 * * *'}`
- created_at: `2026-07-18T20:44:01.529320+08:00`
- last_run_at: `2026-08-08T06:20:34.445142+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-08-09T06:20:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `True`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `[]`
- skill: ``
- script: `aiw-daily-intake-classify.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-daily-intake`
- context_from: ``
- repeat: `{'times': None, 'completed': 23}`

**prompt：** 空。该 job 为 script-only 或无 Hermes Agent prompt。

### 4.4 `aiw-daily-intake-deepresearch`

- id: `db79021b32a0`
- state: `scheduled`
- enabled: `True`
- schedule: `{'kind': 'cron', 'expr': '10 6 * * *', 'display': '10 6 * * *'}`
- created_at: `2026-07-18T20:41:26.254924+08:00`
- last_run_at: `2026-08-08T06:10:33.342759+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-08-09T06:10:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `True`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `[]`
- skill: ``
- script: `aiw-daily-intake-deepresearch.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-daily-intake`
- context_from: ``
- repeat: `{'times': None, 'completed': 23}`

**prompt：** 空。该 job 为 script-only 或无 Hermes Agent prompt。

### 4.5 `aiw-daily-intake-incremental`

- id: `2364b7bf9a07`
- state: `scheduled`
- enabled: `True`
- schedule: `{'kind': 'cron', 'expr': '45 5 * * *', 'display': '45 5 * * *'}`
- created_at: `2026-07-18T20:41:26.665880+08:00`
- last_run_at: `2026-08-08T05:45:29.500833+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-08-09T05:45:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `True`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `[]`
- skill: ``
- script: `aiw-daily-intake-incremental.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-daily-intake`
- context_from: ``
- repeat: `{'times': None, 'completed': 23}`

**prompt：** 空。该 job 为 script-only 或无 Hermes Agent prompt。

### 4.6 `aiw-daily-intake-tech-articles`

- id: `f50a04d870c3`
- state: `scheduled`
- enabled: `True`
- schedule: `{'kind': 'cron', 'expr': '25 5 * * *', 'display': '25 5 * * *'}`
- created_at: `2026-07-18T20:41:26.461844+08:00`
- last_run_at: `2026-08-08T05:25:25.226031+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-08-09T05:25:00+08:00`
- deliver: `local`
- no_agent: `True`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `[]`
- skill: ``
- script: `aiw-daily-intake-tech-articles.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-daily-intake`
- context_from: ``
- repeat: `{'times': None, 'completed': 23}`

**prompt：** 空。该 job 为 script-only 或无 Hermes Agent prompt。

### 4.7 `aiw-git-sync`

- id: `5fa9d7fe9e87`
- state: `scheduled`
- enabled: `True`
- schedule: `{'kind': 'cron', 'expr': '55 7-23 * * *', 'display': '55 7-23 * * *'}`
- created_at: `2026-07-19T11:27:28.694123+08:00`
- last_run_at: `2026-08-08T23:55:16.180537+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-08-09T07:55:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `True`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `[]`
- skill: ``
- script: `aiw-git-sync.py`
- workdir: ``
- context_from: ``
- repeat: `{'times': None, 'completed': 271}`

**prompt：** 空。该 job 为 script-only 或无 Hermes Agent prompt。

### 4.8 `aiw-polish-deep-review-apply`

- id: `a2fb41f345c8`
- state: `scheduled`
- enabled: `True`
- schedule: `{'kind': 'cron', 'expr': '35 8,12,16,20 * * *', 'display': '35 8,12,16,20 * * *'}`
- created_at: `2026-07-25T12:25:41.350034+08:00`
- last_run_at: `2026-08-08T20:38:16.558832+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-08-09T08:35:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `False`
- model: `gpt-5.5`
- provider: `openai-codex`
- base_url: ``
- enabled_toolsets: `['terminal', 'file']`
- skills: `[]`
- skill: ``
- script: `aiw-polish-deep-review-context.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-polish-apply`
- context_from: ``
- repeat: `{'times': None, 'completed': 58}`

**prompt：**

```text
通用事务与证据合同：
- 只处理 pre-run JSON 指定的一个 target_path；读取 run_id、lane、base_sha、manifest_path、allowed_changed_paths、formal_report_path。
- 开始前运行 git status --porcelain；若存在不属于 allowed_changed_paths 的脏改动，或 HEAD 与 base_sha 不一致，返回 blocked，不得吸收、覆盖或提交这些改动。
- 只允许修改 target_path、JSON 明确允许的 metadata/log 文件，以及本轮 evidence/report。禁止新增 src 文件，禁止修改 src/SUMMARY.md。
- 禁止运行 git add/commit/push/pull/rebase/autostash 或 aiw-git-sync.py；提交由独立 manifest gate 执行。
- Android baseline 固定 android-17.0.0_r1 / Android 17；禁止任何高于 Android 17 的主线结论。
- 状态降级必须写稳定 finding_id；重新晋级必须关闭对应 finding_id 并列 source_evidence。不能因脚本 exit 0、引用数量多、没发现新问题就提高状态。
- 只有实际核对源码/官方文档后，才能更新 last_source_verified_at 或提高 confidence；普通巡检只写 evidence，不刷新 source verified。
- 最终只输出简短 JSON：run_id,status,target_path,body_modified,frontmatter_modified,changed_paths,findings_opened,findings_closed,source_evidence,verification,blocked_reason。

你是 AIW Polish deep-review lane。若 polish_candidate_ready：
1. 先产出 finding，再决定是否修改。每个 finding 包含 finding_id,severity,claim,evidence,target_range,recommended_action。
2. 仅出现“待验证”、高于 Android 17 的版本字样或历史 review note，不足以降级；必须证明正文存在仍生效且无支撑的肯定结论。
3. 大段删除前列出删除范围、原因和保留信息摘要；超过自动阈值（单章删除>120行或一次>3个 src 文件）返回 needs-human-review。
4. 小范围有证据问题可 patch；写 logs/deep-review、formal_report_path/evidence，并运行本地 gate。

```

### 4.9 `aiw-polish-draft-polish-apply`

- id: `ef444f87d299`
- state: `scheduled`
- enabled: `True`
- schedule: `{'kind': 'cron', 'expr': '35 11,15,19,23 * * *', 'display': '35 11,15,19,23 * * *'}`
- created_at: `2026-07-25T12:26:24.623934+08:00`
- last_run_at: `2026-08-08T23:39:22.507264+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-08-09T11:35:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `False`
- model: `gpt-5.5`
- provider: `openai-codex`
- base_url: ``
- enabled_toolsets: `['terminal', 'file']`
- skills: `[]`
- skill: ``
- script: `aiw-polish-draft-polish-context.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-polish-apply`
- context_from: ``
- repeat: `{'times': None, 'completed': 57}`

**prompt：**

```text
通用事务与证据合同：
- 只处理 pre-run JSON 指定的一个 target_path；读取 run_id、lane、base_sha、manifest_path、allowed_changed_paths、formal_report_path。
- 开始前运行 git status --porcelain；若存在不属于 allowed_changed_paths 的脏改动，或 HEAD 与 base_sha 不一致，返回 blocked，不得吸收、覆盖或提交这些改动。
- 只允许修改 target_path、JSON 明确允许的 metadata/log 文件，以及本轮 evidence/report。禁止新增 src 文件，禁止修改 src/SUMMARY.md。
- 禁止运行 git add/commit/push/pull/rebase/autostash 或 aiw-git-sync.py；提交由独立 manifest gate 执行。
- Android baseline 固定 android-17.0.0_r1 / Android 17；禁止任何高于 Android 17 的主线结论。
- 状态降级必须写稳定 finding_id；重新晋级必须关闭对应 finding_id 并列 source_evidence。不能因脚本 exit 0、引用数量多、没发现新问题就提高状态。
- 只有实际核对源码/官方文档后，才能更新 last_source_verified_at 或提高 confidence；普通巡检只写 evidence，不刷新 source verified。
- 最终只输出简短 JSON：run_id,status,target_path,body_modified,frontmatter_modified,changed_paths,findings_opened,findings_closed,source_evidence,verification,blocked_reason。

你是 AIW Polish draft-polish lane。若 polish_candidate_ready：
1. 只打磨既有 draft，不新增章节，不编造源码结论。术语润色与事实修改分开报告。
2. draft 只有在结构完整、关键 claim 有证据、没有 unresolved marker、版本边界明确时才能推进 ready-for-review。materials 为空不自动阻止修改，但不能仅凭已有引用数量晋级；必须列出实际验证过的 claim。
3. 没有事实变化时，不更新 last_source_verified_at 或 confidence。
4. 写 logs/review、formal_report_path/evidence，并运行本地 gate。

```

### 4.10 `aiw-polish-idle-audit-apply`

- id: `fb934850da95`
- state: `scheduled`
- enabled: `True`
- schedule: `{'kind': 'cron', 'expr': '35 10,14,18,22 * * *', 'display': '35 10,14,18,22 * * *'}`
- created_at: `2026-07-25T12:26:09.073184+08:00`
- last_run_at: `2026-08-08T22:37:45.311476+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-08-09T10:35:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `False`
- model: `gpt-5.5`
- provider: `openai-codex`
- base_url: ``
- enabled_toolsets: `['terminal', 'file']`
- skills: `[]`
- skill: ``
- script: `aiw-polish-idle-audit-context.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-polish-apply`
- context_from: ``
- repeat: `{'times': None, 'completed': 57}`

**prompt：**

```text
通用事务与证据合同：
- 只处理 pre-run JSON 指定的一个 target_path；读取 run_id、lane、base_sha、manifest_path、allowed_changed_paths、formal_report_path。
- 开始前运行 git status --porcelain；若存在不属于 allowed_changed_paths 的脏改动，或 HEAD 与 base_sha 不一致，返回 blocked，不得吸收、覆盖或提交这些改动。
- 只允许修改 target_path、JSON 明确允许的 metadata/log 文件，以及本轮 evidence/report。禁止新增 src 文件，禁止修改 src/SUMMARY.md。
- 禁止运行 git add/commit/push/pull/rebase/autostash 或 aiw-git-sync.py；提交由独立 manifest gate 执行。
- Android baseline 固定 android-17.0.0_r1 / Android 17；禁止任何高于 Android 17 的主线结论。
- 状态降级必须写稳定 finding_id；重新晋级必须关闭对应 finding_id 并列 source_evidence。不能因脚本 exit 0、引用数量多、没发现新问题就提高状态。
- 只有实际核对源码/官方文档后，才能更新 last_source_verified_at 或提高 confidence；普通巡检只写 evidence，不刷新 source verified。
- 最终只输出简短 JSON：run_id,status,target_path,body_modified,frontmatter_modified,changed_paths,findings_opened,findings_closed,source_evidence,verification,blocked_reason。

你是 AIW Polish idle-audit lane。若 polish_candidate_ready：
1. 做 finalized/verified 章节抽检，只找仍生效的 高于 Android 17 的版本越界、待验证残留、来源标记不足、明显技术/表达问题。
2. 若审计通过且没有新证据、finding 或正文变化，返回 status=completed-no-change；只写独立 audit evidence/log，不修改章节文件，不刷新 frontmatter 时间戳，不提交。
3. 只有发现问题、关闭 finding 或获得新来源证据时才改正文/frontmatter；严重问题降级并写 finding_id。
4. 写 logs/audit、formal_report_path/evidence，并运行本地 gate（若没有改章节，可只说明未运行 metadata gate原因）。

```

### 4.11 `aiw-polish-rework-apply`

- id: `410de74688cd`
- state: `scheduled`
- enabled: `True`
- schedule: `{'kind': 'cron', 'expr': '35 9,13,17,21 * * *', 'display': '35 9,13,17,21 * * *'}`
- created_at: `2026-07-25T12:25:54.966752+08:00`
- last_run_at: `2026-08-08T21:38:52.197016+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-08-09T09:35:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `False`
- model: `gpt-5.5`
- provider: `openai-codex`
- base_url: ``
- enabled_toolsets: `['terminal', 'file']`
- skills: `[]`
- skill: ``
- script: `aiw-polish-rework-context.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-polish-apply`
- context_from: ``
- repeat: `{'times': None, 'completed': 56}`

**prompt：**

```text
通用事务与证据合同：
- 只处理 pre-run JSON 指定的一个 target_path；读取 run_id、lane、base_sha、manifest_path、allowed_changed_paths、formal_report_path。
- 开始前运行 git status --porcelain；若存在不属于 allowed_changed_paths 的脏改动，或 HEAD 与 base_sha 不一致，返回 blocked，不得吸收、覆盖或提交这些改动。
- 只允许修改 target_path、JSON 明确允许的 metadata/log 文件，以及本轮 evidence/report。禁止新增 src 文件，禁止修改 src/SUMMARY.md。
- 禁止运行 git add/commit/push/pull/rebase/autostash 或 aiw-git-sync.py；提交由独立 manifest gate 执行。
- Android baseline 固定 android-17.0.0_r1 / Android 17；禁止任何高于 Android 17 的主线结论。
- 状态降级必须写稳定 finding_id；重新晋级必须关闭对应 finding_id 并列 source_evidence。不能因脚本 exit 0、引用数量多、没发现新问题就提高状态。
- 只有实际核对源码/官方文档后，才能更新 last_source_verified_at 或提高 confidence；普通巡检只写 evidence，不刷新 source verified。
- 最终只输出简短 JSON：run_id,status,target_path,body_modified,frontmatter_modified,changed_paths,findings_opened,findings_closed,source_evidence,verification,blocked_reason。

你是 AIW Polish rework lane。若 polish_candidate_ready：
1. 只处理 context 或章节/metadata 中明确列出的 finding_id / needs-rework 项。
2. 每项修改必须说明关闭了哪个 finding；未能关闭的 finding 保持 open。
3. 不顺带重写同章其他内容，不用“清理措辞”代替证据。
4. 修复后按证据把状态推回 ready-for-review 或保持 needs-rework；写 logs/rework、formal_report_path/evidence，并运行本地 gate。

```

### 4.12 `aiw-review-finalize-apply`

- id: `464ba760c0e3`
- state: `scheduled`
- enabled: `True`
- schedule: `{'kind': 'cron', 'expr': '5 8,10,12,14,16,18,20,22 * * *', 'display': '5 8,10,12,14,16,18,20,22 * * *'}`
- created_at: `2026-07-19T19:22:57.961322+08:00`
- last_run_at: `2026-08-08T22:08:25.704099+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-08-09T08:05:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `False`
- model: `gpt-5.5`
- provider: `openai-codex`
- base_url: ``
- enabled_toolsets: `['terminal', 'file']`
- skills: `[]`
- skill: ``
- script: `aiw-review-finalize-context.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-review-finalize-apply`
- context_from: ``
- repeat: `{'times': None, 'completed': 138}`

**prompt：**

```text
通用事务与证据合同：
- 只处理 pre-run JSON 指定的一个 target_path；读取 run_id、lane、base_sha、manifest_path、allowed_changed_paths、formal_report_path。
- 开始前运行 git status --porcelain；若存在不属于 allowed_changed_paths 的脏改动，或 HEAD 与 base_sha 不一致，返回 blocked，不得吸收、覆盖或提交这些改动。
- 只允许修改 target_path、JSON 明确允许的 metadata/log 文件，以及本轮 evidence/report。禁止新增 src 文件，禁止修改 src/SUMMARY.md。
- 禁止运行 git add/commit/push/pull/rebase/autostash 或 aiw-git-sync.py；提交由独立 manifest gate 执行。
- Android baseline 固定 android-17.0.0_r1 / Android 17；禁止任何高于 Android 17 的主线结论。
- 状态降级必须写稳定 finding_id；重新晋级必须关闭对应 finding_id 并列 source_evidence。不能因脚本 exit 0、引用数量多、没发现新问题就提高状态。
- 只有实际核对源码/官方文档后，才能更新 last_source_verified_at 或提高 confidence；普通巡检只写 evidence，不刷新 source verified。
- 最终只输出简短 JSON：run_id,status,target_path,body_modified,frontmatter_modified,changed_paths,findings_opened,findings_closed,source_evidence,verification,blocked_reason。

你是 AIW Review/Finalize Apply。若 status=no-candidate 返回 no-candidate；若 review_candidate_ready：
1. 对指定章节做源码准确性、版本边界、来源支撑、中文可读性、待验证项审查，可做小范围安全 patch。
2. finalized 必要条件：没有 open P0/P1 finding；关键 claim 都有可定位 source_evidence；版本边界已验证；本地 gate 全部通过。materials 为空时可自行查本地源码，但必须结构化记录证据；无法形成证据则保持 ready-for-review 或转 needs-rework。
3. 不要把“引用看起来足够”“metadata 检查通过”“没有明显问题”单独作为 finalized 依据。
4. 写 formal_report_path/evidence，运行本地 gate。

```

### 4.13 `aiw-throughput-watchdog`

- id: `167290e723e9`
- state: `scheduled`
- enabled: `True`
- schedule: `{'kind': 'cron', 'expr': '58 23 * * *', 'display': '58 23 * * *'}`
- created_at: `2026-07-25T14:09:59.105083+08:00`
- last_run_at: `2026-08-08T23:58:12.919334+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-08-09T23:58:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `True`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: `['terminal']`
- skills: `[]`
- skill: ``
- script: `aiw-throughput-watchdog.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-polish-apply`
- context_from: ``
- repeat: `{'times': None, 'completed': 16}`

**prompt：**

```text
AIW closed-loop throughput watchdog. The script prints the final Telegram-ready health report and writes the formal Obsidian report.
```

### 4.14 `aiw-weekly-source-audit-clippings`

- id: `93d3c7568b39`
- state: `scheduled`
- enabled: `True`
- schedule: `{'kind': 'cron', 'expr': '30 6 * * *', 'display': '30 6 * * *'}`
- created_at: `2026-07-18T20:49:14.372362+08:00`
- last_run_at: `2026-08-08T06:30:35.727585+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-08-09T06:30:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `True`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `[]`
- skill: ``
- script: `aiw-weekly-source-audit-clippings-reference-scan.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-weekly-source-audit`
- context_from: ``
- repeat: `{'times': None, 'completed': 23}`

**prompt：** 空。该 job 为 script-only 或无 Hermes Agent prompt。

### 4.15 `aiw-weekly-source-audit-freshness`

- id: `c7fcfd963ce5`
- state: `scheduled`
- enabled: `True`
- schedule: `{'kind': 'cron', 'expr': '0 2 * * 1,3,5', 'display': '0 2 * * 1,3,5'}`
- created_at: `2026-07-18T20:49:14.581394+08:00`
- last_run_at: `2026-08-07T02:00:27.460680+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-08-10T02:00:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `True`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `[]`
- skill: ``
- script: `aiw-weekly-source-audit-freshness-check.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-weekly-source-audit`
- context_from: ``
- repeat: `{'times': None, 'completed': 10}`

**prompt：** 空。该 job 为 script-only 或无 Hermes Agent prompt。

### 4.16 `feishu-daily-sync-dry-run`

- id: `2955f4f3f151`
- state: `scheduled`
- enabled: `True`
- schedule: `{'kind': 'cron', 'expr': '30 9 * * *', 'display': '30 9 * * *'}`
- created_at: `2026-07-18T20:27:30.263643+08:00`
- last_run_at: `2026-08-08T09:31:13.796203+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-08-09T09:30:00+08:00`
- deliver: `telegram:-1003814981550`
- no_agent: `True`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `[]`
- skill: ``
- script: `feishu-daily-sync-dry-run.py`
- workdir: `/Users/gracker/.hermes/workspaces/feishu-daily-sync`
- context_from: ``
- repeat: `{'times': None, 'completed': 22}`

**prompt：** 空。该 job 为 script-only 或无 Hermes Agent prompt。

### 4.17 `feishu-daily-sync-guarded-write`

- id: `70e6cc5c0f14`
- state: `scheduled`
- enabled: `True`
- schedule: `{'kind': 'cron', 'expr': '40 9 * * *', 'display': '40 9 * * *'}`
- created_at: `2026-07-18T20:27:30.474703+08:00`
- last_run_at: `2026-08-08T09:42:01.442435+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-08-09T09:40:00+08:00`
- deliver: `telegram:-1003814981550`
- no_agent: `True`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `[]`
- skill: ``
- script: `feishu-daily-sync-guarded-write.py`
- workdir: `/Users/gracker/.hermes/workspaces/feishu-daily-sync`
- context_from: ``
- repeat: `{'times': None, 'completed': 18}`

**prompt：** 空。该 job 为 script-only 或无 Hermes Agent prompt。

### 4.18 `feishu-daily-sync-monitor`

- id: `0002c4202fac`
- state: `scheduled`
- enabled: `True`
- schedule: `{'kind': 'cron', 'expr': '0 10 * * *', 'display': '0 10 * * *'}`
- created_at: `2026-07-18T20:27:30.681590+08:00`
- last_run_at: `2026-08-08T10:00:05.419502+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-08-09T10:00:00+08:00`
- deliver: `telegram:-1003814981550`
- no_agent: `True`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `[]`
- skill: ``
- script: `feishu-daily-sync-monitor.py`
- workdir: `/Users/gracker/.hermes/workspaces/feishu-daily-sync`
- context_from: ``
- repeat: `{'times': None, 'completed': 21}`

**prompt：** 空。该 job 为 script-only 或无 Hermes Agent prompt。

### 4.19 `aiw-queue-worker-dispatcher`

- id: `f0f2cccb04ef`
- state: `paused`
- enabled: `False`
- schedule: `{'kind': 'cron', 'expr': '5 * * * *', 'display': '5 * * * *'}`
- created_at: `2026-07-18T22:40:44.874404+08:00`
- last_run_at: `2026-07-19T18:05:18.610780+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-07-19T19:05:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `True`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `[]`
- skill: ``
- script: `aiw-queue-worker-dispatcher.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-queue-worker-dispatcher`
- context_from: ``
- repeat: `{'times': None, 'completed': 13}`

**prompt：** 空。该 job 为 script-only 或无 Hermes Agent prompt。

### 4.20 `aiw-queue-worker-source-research`

- id: `87e270a88b46`
- state: `paused`
- enabled: `False`
- schedule: `{'kind': 'cron', 'expr': '50 2,5,8,11,14,17,20,23 * * *', 'display': '50 2,5,8,11,14,17,20,23 * * *'}`
- created_at: `2026-07-18T20:51:02.010227+08:00`
- last_run_at: ``
- last_status: ``
- last_error: ``
- next_run_at: `2026-07-18T23:50:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `True`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `[]`
- skill: ``
- script: `aiw-queue-worker-source-research.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-queue-worker`
- context_from: ``
- repeat: `{'times': None, 'completed': 0}`

**prompt：** 空。该 job 为 script-only 或无 Hermes Agent prompt。

### 4.21 `aiw-queue-worker-task2a`

- id: `07fc533fb059`
- state: `paused`
- enabled: `False`
- schedule: `{'kind': 'cron', 'expr': '0 8,14,20 * * *', 'display': '0 8,14,20 * * *'}`
- created_at: `2026-07-18T20:51:02.250178+08:00`
- last_run_at: ``
- last_status: ``
- last_error: ``
- next_run_at: `2026-07-19T08:00:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `True`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `[]`
- skill: ``
- script: `aiw-queue-worker-task2a.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-queue-worker`
- context_from: ``
- repeat: `{'times': None, 'completed': 0}`

**prompt：** 空。该 job 为 script-only 或无 Hermes Agent prompt。

### 4.22 `aiw-queue-worker-task2b-lite`

- id: `eddc94a6c35d`
- state: `paused`
- enabled: `False`
- schedule: `{'kind': 'cron', 'expr': '35 1-23/2 * * *', 'display': '35 1-23/2 * * *'}`
- created_at: `2026-07-18T20:51:01.772309+08:00`
- last_run_at: `2026-07-18T21:35:25.253427+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-07-18T23:35:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `True`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `[]`
- skill: ``
- script: `aiw-queue-worker-task2b-lite.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-queue-worker`
- context_from: ``
- repeat: `{'times': None, 'completed': 1}`

**prompt：** 空。该 job 为 script-only 或无 Hermes Agent prompt。

### 4.23 `aiw-queue-worker-task2b-main`

- id: `2435d66a5a42`
- state: `paused`
- enabled: `False`
- schedule: `{'kind': 'cron', 'expr': '50 0-22/2 * * *', 'display': '50 0-22/2 * * *'}`
- created_at: `2026-07-18T20:53:07.045406+08:00`
- last_run_at: ``
- last_status: ``
- last_error: ``
- next_run_at: `2026-07-18T22:50:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `True`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `[]`
- skill: ``
- script: `aiw-queue-worker-task2b-main.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-queue-worker`
- context_from: ``
- repeat: `{'times': None, 'completed': 0}`

**prompt：** 空。该 job 为 script-only 或无 Hermes Agent prompt。

### 4.24 `aiw-review-finalize-deep-tech-review`

- id: `46fbf624b429`
- state: `paused`
- enabled: `False`
- schedule: `{'kind': 'cron', 'expr': '20 0-22 * * *', 'display': '20 0-22 * * *'}`
- created_at: `2026-07-18T20:55:10.035265+08:00`
- last_run_at: `2026-07-18T22:20:26.510049+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-07-19T00:20:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `True`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `[]`
- skill: ``
- script: `aiw-review-finalize-deep-tech-review.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-review-finalize`
- context_from: ``
- repeat: `{'times': None, 'completed': 2}`

**prompt：** 空。该 job 为 script-only 或无 Hermes Agent prompt。

### 4.25 `aiw-review-finalize-dispatcher`

- id: `325ea8fa9195`
- state: `paused`
- enabled: `False`
- schedule: `{'kind': 'cron', 'expr': '10 * * * *', 'display': '10 * * * *'}`
- created_at: `2026-07-18T22:40:45.117552+08:00`
- last_run_at: `2026-07-19T18:10:18.354452+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-07-19T19:10:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `True`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `[]`
- skill: ``
- script: `aiw-review-finalize-dispatcher.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-review-finalize-dispatcher`
- context_from: ``
- repeat: `{'times': None, 'completed': 13}`

**prompt：** 空。该 job 为 script-only 或无 Hermes Agent prompt。

### 4.26 `aiw-review-finalize-draft-review`

- id: `59d136a6429d`
- state: `paused`
- enabled: `False`
- schedule: `{'kind': 'cron', 'expr': '5 1-23 * * *', 'display': '5 1-23 * * *'}`
- created_at: `2026-07-18T20:56:49.885863+08:00`
- last_run_at: `2026-07-18T22:05:25.228867+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-07-18T23:05:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `True`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `[]`
- skill: ``
- script: `aiw-review-finalize-draft-review.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-review-finalize`
- context_from: ``
- repeat: `{'times': None, 'completed': 2}`

**prompt：** 空。该 job 为 script-only 或无 Hermes Agent prompt。

### 4.27 `aiw-review-finalize-reader-final`

- id: `087678486ac8`
- state: `paused`
- enabled: `False`
- schedule: `{'kind': 'cron', 'expr': '40 1,7,13,19 * * *', 'display': '40 1,7,13,19 * * *'}`
- created_at: `2026-07-18T20:55:09.556291+08:00`
- last_run_at: ``
- last_status: ``
- last_error: ``
- next_run_at: `2026-07-19T01:40:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `True`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `[]`
- skill: ``
- script: `aiw-review-finalize-reader-final.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-review-finalize`
- context_from: ``
- repeat: `{'times': None, 'completed': 0}`

**prompt：** 空。该 job 为 script-only 或无 Hermes Agent prompt。

### 4.28 `aiw-review-finalize-task2b-verifier`

- id: `9fbe57241199`
- state: `paused`
- enabled: `False`
- schedule: `{'kind': 'cron', 'expr': '25 3-23/4 * * *', 'display': '25 3-23/4 * * *'}`
- created_at: `2026-07-18T20:55:09.799463+08:00`
- last_run_at: ``
- last_status: ``
- last_error: ``
- next_run_at: `2026-07-18T23:25:00+08:00`
- deliver: `telegram:-1004339755728`
- no_agent: `True`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `[]`
- skill: ``
- script: `aiw-review-finalize-task2b-verifier.py`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-review-finalize`
- context_from: ``
- repeat: `{'times': None, 'completed': 0}`

**prompt：** 空。该 job 为 script-only 或无 Hermes Agent prompt。

### 4.29 `clawfeed-daily-report-local`

- id: `a0c290e16e09`
- state: `paused`
- enabled: `False`
- schedule: `{'kind': 'cron', 'expr': '0 4 * * *', 'display': '0 4 * * *'}`
- created_at: `2026-07-18T18:38:31.128529+08:00`
- last_run_at: ``
- last_status: ``
- last_error: ``
- next_run_at: `2026-07-19T04:00:00+08:00`
- deliver: `local`
- no_agent: `False`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `['opencli-web', 'clawfeed-digest', 'openclaw-imports/gracker-writing']`
- skill: `opencli-web`
- script: `clawfeed-daily-prepare.py`
- workdir: `/Users/gracker/.hermes/workspaces/clawfeed-daily`
- context_from: ``
- repeat: `{'times': None, 'completed': 0}`

**prompt：**

```text
# ClawFeed 24小时高价值一览 — private body-backed report

The pre-run script printed one JSON context object. Treat it as the only writable
run context.

1. Read `input_path`. It is an immutable ClawFeed candidate snapshot from OpenCLI
   HN lanes. Every candidate title, URL, publication time, source lane and input
   ID must come from that snapshot. Never invent, repair, or substitute a URL.
2. Shortlist at most 12 promising candidates. Feed summaries and HN scores are
   only triage hints; never score from the title or summary alone.
3. For every serious candidate, fetch the full page with local OpenCLI first:
   `opencli web read --url "<exact URL>" --output "<private temp directory>"`.
   A 404 page, home page, login wall, thin body, release-note dump, marketing
   page, or unrelated redirect is not evidence and must not be selected.
4. Write `bodies_root/SNN.md` as a short provenance header followed by the
   fetched Markdown body:

   ```text
   Source URL: <exact snapshot URL>
   OpenCLI command: <exact command used>

   <exact fetched Markdown body, not summarized or rewritten>
   ```

   The complete evidence file must contain the exact source URL and at least
   600 characters. Do not leave OpenCLI output directories or helper scripts
   inside the final staging root.
5. Score only after reading the body with the clawfeed-digest rubric. Select at
   most 10 items and only scores strictly greater than 7.0. Prefer AI-agent,
   frontier commentary, operator insight, systems/security depth, and unusually
   high-signal essays. It is valid to select zero items.
6. Write `selected_path` as UTF-8 JSON:

```json
{
  "schema_version": 1,
  "run_id": "<context run_id>",
  "input_hash": "<context input_hash>",
  "selected": [
    {
      "id": "S01",
      "input_id": "C001",
      "title": "<exact snapshot title>",
      "url": "<exact snapshot URL>",
      "published_at": "<exact snapshot timestamp>",
      "feed_name": "<exact snapshot feed_name>",
      "score": 8.4,
      "recommendation": "<20-400 Chinese chars grounded in body>",
      "summary": "<60-800 Chinese chars grounded in body>",
      "opencli_command": "opencli web read --url <exact URL> --output <dir>",
      "body_path": "<bodies_root>/S01.md",
      "body_characters": 1234,
      "body_sha256": "<sha256 of body file>",
      "aiw_relevant": false,
      "aiw_summary": "",
      "recommended_chapter": "",
      "tags": []
    }
  ]
}
```

   When `aiw_relevant` is true, fill `aiw_summary` (60-240 Chinese chars),
   `recommended_chapter`, and 1-8 tags.
7. Write `report_path` as UTF-8 Markdown starting with:

```markdown
# ClawFeed 24小时高价值一览 · <local_date>

任务信息：
- 任务名称：ClawFeed 24小时高价值一览（For You+Bookmarks）
- 处理数量：候选 N 篇，认真阅读 M 篇，入选 K 篇
- 数据源：OpenCLI HN top/best/new
- 落盘路径：private staging only in this step
- 验证状态：待 finalize

可发布正文如下：
```

   Then either selected entries with exact fields `标题` / `评分` / `推荐语` /
   `摘要` / `链接`, or the zero-selection Chinese explanation containing
   `今天没有正文评分严格大于 7.0 的文章。`
8. Run exactly:

`python3 /Users/gracker/.hermes/scripts/clawfeed-daily-finalize.py --run-id <run_id>`

Do not publish to Obsidian or Telegram from this job. Do not call messaging tools.
Use skills: opencli-web, clawfeed-digest, openclaw-imports/gracker-writing.
```

### 4.30 `rss-gracker-report-local`

- id: `30b5d8ac353c`
- state: `paused`
- enabled: `False`
- schedule: `{'kind': 'cron', 'expr': '0 3 * * *', 'display': '0 3 * * *'}`
- created_at: `2026-07-18T17:20:39.200761+08:00`
- last_run_at: `2026-07-18T17:25:56.544818+08:00`
- last_status: `ok`
- last_error: ``
- next_run_at: `2026-07-19T03:00:00+08:00`
- deliver: `local`
- no_agent: `False`
- model: ``
- provider: ``
- base_url: ``
- enabled_toolsets: ``
- skills: `['opencli-web', 'openclaw-imports/article-digest-pipeline', 'openclaw-imports/gracker-writing']`
- skill: `opencli-web`
- script: `rss-gracker-prepare.py`
- workdir: `/Users/gracker/.hermes/workspaces/rss-gracker`
- context_from: ``
- repeat: `{'times': None, 'completed': 1}`

**prompt：**

```text
# Gracker RSS Daily Digest — private body-backed report

The pre-run script printed one JSON context object. Treat it as the only writable
run context.

1. Read `input_path`. It is an immutable, deterministic RSS snapshot. Every
   candidate title, URL, publication time, feed and input ID must come from that
   snapshot. Never invent, repair, or substitute a URL.
2. Shortlist at most 12 promising candidates from the rolling 24-hour input.
   Feed summaries are only triage hints; never score from the title or feed
   summary.
3. For every serious candidate, fetch the full page with local OpenCLI first:
   `opencli web read --url "<exact URL>" --output "<private temp directory>"`.
   A 404 page, home page, login wall, thin body, release-note dump, marketing
   page, or unrelated redirect is not evidence and must not be selected.
4. Write `bodies_root/SNN.md` as a short provenance header followed by the
   fetched Markdown body:

   ```text
   Source URL: <exact snapshot URL>
   OpenCLI command: <exact command used>

   <exact fetched Markdown body, not summarized or rewritten>
   ```

   The complete evidence file must contain the exact source URL and at least
   600 characters. Do not leave OpenCLI output directories or helper scripts
   inside the final staging root.
5. Score only after reading the body. Select at most 10 items and only scores
   strictly greater than 7.0. Prefer original, high-signal engineering,
   AI-agent, systems, security, product-strategy, and unusually insightful
   essays. It is valid to select zero items.
6. Write `selected_path` as UTF-8 JSON:

```json
{
  "schema_version": 1,
  "run_id": "<context run_id>",
  "input_hash": "<context input_hash>",
  "selected": [
    {
      "id": "S01",
      "input_id": "R001",
      "title": "<exact snapshot title>",
      "url": "<exact snapshot URL>",
      "published_at": "<exact snapshot timestamp>",
      "feed_name": "<exact snapshot feed>",
      "score": 8.4,
      "recommendation": "<20-400 Chinese characters, body-backed>",
      "summary": "<60-800 Chinese characters, concise and body-backed>",
      "opencli_command": "opencli web read --url <exact URL> ...",
      "body_path": "<absolute bodies_root>/S01.md",
      "body_characters": 1234,
      "body_sha256": "<SHA-256 of exact body file text>",
      "aiw_relevant": true,
      "aiw_summary": "<60-240 Chinese characters>",
      "recommended_chapter": "<specific AIW chapter or intake area>",
      "tags": ["Android", "RSS订阅"]
    }
  ]
}
```

For `aiw_relevant=false`, use an empty `aiw_summary`, empty
`recommended_chapter`, and empty `tags`.

7. Write `report_path` in this exact shape:

```markdown
# Gracker RSS Daily Digest · YYYY-MM-DD

来源：89 源 RSS · 滚动 24 小时
正文抓取：OpenCLI-first
入选：N 条（评分严格 > 7.0）

可发布正文如下：

- 标题：...
  评分：8.4/10
  推荐语：...
  摘要：...
  链接：https://...
```

If nothing qualifies, include the exact sentence
`今天没有正文评分严格大于 7.0 的文章。` and no URL.

8. Do not write Obsidian, AIW, Telegram, `/Users/gracker/.openclaw`, or any
   path outside the context staging root. Do not create or change Skills.
9. Run `required_finalize_command`. The task succeeds only if finalize exits 0.
   Your final response must only report the sealed private result; it must not
   include the full digest because delivery is a later deterministic stage.
```

## 5. 当前脚本清单与 SHA

| script | exists | sha256-16 | bytes | role |
|---|---:|---|---:|---|
| `aiw_pipeline_common.py` | `True` | `7c6f151d59ebb564` | `7958` | `共享事务/selector/watchdog/freshness helper` |
| `aiw-body-apply-context.py` | `True` | `20b0590ad2929184` | `12694` | `body apply pre-run context + manifest` |
| `aiw-review-finalize-context.py` | `True` | `9755d1c62a381a6f` | `8400` | `review/finalize pre-run context + manifest` |
| `aiw-polish-context.py` | `True` | `5d403a9b88d069f8` | `13777` | `polish lanes shared pre-run context + manifest` |
| `aiw-polish-deep-review-context.py` | `True` | `f92cfae709b7eef2` | `232` | `` |
| `aiw-polish-rework-context.py` | `True` | `9ff26b742f21bbab` | `227` | `` |
| `aiw-polish-idle-audit-context.py` | `True` | `076afc1a87256c94` | `231` | `` |
| `aiw-polish-draft-polish-context.py` | `True` | `d7c5c91d35e4ac98` | `233` | `` |
| `aiw-git-sync.py` | `True` | `921b5e74839e6587` | `15627` | `唯一 git stage/commit/push gate` |
| `aiw-throughput-watchdog.py` | `True` | `d2feda1a88babc15` | `9306` | `健康/吞吐监控` |
| `aiw-weekly-source-audit.py` | `True` | `6353b9ce0c66a85f` | `13621` | `clippings/freshness 审计` |
| `aiw-daily-intake.py` | `True` | `76f7c08596da78d7` | `14533` | `daily intake shared collector` |
| `aiw-daily-intake-deepresearch.py` | `True` | `43c960747e8c9b5b` | `193` | `` |
| `aiw-daily-intake-tech-articles.py` | `True` | `070e5a726aa6e131` | `194` | `` |
| `aiw-daily-intake-incremental.py` | `True` | `aafd14ae8256a58c` | `192` | `` |
| `aiw-daily-intake-classify.py` | `True` | `9dd13adb93538fbf` | `189` | `` |
| `aiw-queue-worker.py` | `True` | `f1062da598951c33` | `5740` | `paused legacy queue gate/report` |
| `aiw-review-finalize.py` | `True` | `0f015f0fed43a8ef` | `4140` | `paused legacy review/finalize gate/report` |
| `feishu-daily-sync-dry-run.py` | `True` | `7e341fe6db428912` | `189` | `` |
| `feishu-daily-sync-guarded-write.py` | `True` | `435335f85b4f5672` | `195` | `` |
| `feishu-daily-sync-monitor.py` | `True` | `36dfdfcc27375cd2` | `189` | `` |

## 6. 脚本关键源码附录

### `aiw_pipeline_common.py`

- path：`/Users/gracker/.hermes/scripts/aiw_pipeline_common.py`
- sha256-16：`7c6f151d59ebb564`
- bytes：`7958`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared contracts for AIW Hermes cron lanes.

This module centralizes the eligibility/status and per-run manifest contract so
selector, watchdog, and git-sync use the same definitions instead of drifting.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")
AIW = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki")
SRC = AIW / "src"
STATE_ROOT = Path("/Users/gracker/.hermes/state")
MANIFEST_DIR = STATE_ROOT / "aiw-run-manifests"
FORMAL_ROOT = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AIW自动化流水线")

TERMINAL_ACTIONS = {"body-applied", "applied", "rejected", "duplicate", "superseded"}
INELIGIBLE_ROUTE_PREFIXES = ("quarantined",)
MIN_ROUTE_CONFIDENCE = 30


def run_git(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=str(AIW), text=True, capture_output=True, timeout=timeout, check=False)


def current_head() -> str:
    r = run_git(["rev-parse", "HEAD"])
    return r.stdout.strip() if r.returncode == 0 else ""


def sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def rel_to_aiw(path: Path | str) -> str:
    p = Path(path)
    if not p.is_absolute():
        return str(p)
    return str(p.resolve().relative_to(AIW.resolve()))


def porcelain_paths() -> list[str]:
    """Return changed paths from porcelain -z, handling rename/copy records."""
    r = run_git(["status", "--porcelain", "-z"])
    entries = [x for x in r.stdout.split("\0") if x]
    paths: list[str] = []
    i = 0
    while i < len(entries):
        entry = entries[i]
        status = entry[:2]
        path = entry[3:]
        if status and status[0] in {"R", "C"}:
            i += 1
            if i < len(entries):
                path = entries[i]
        if path:
            paths.append(path)
        i += 1
    return sorted(set(paths))


def dirty_paths_excluding(paths: list[str]) -> list[str]:
    allowed = {str(p) for p in paths}
    return [p for p in porcelain_paths() if p not in allowed]


def unique_report_path(lane: str, run_id: str, now: datetime | None = None) -> Path:
    now = now or datetime.now(TZ)
    return FORMAL_ROOT / f"{now:%Y-%m-%d-%H%M%S}-{run_id}-{lane}.md"


def evidence_path(lane: str, run_id: str) -> Path:
    return STATE_ROOT / lane / f"{run_id}.json"


def create_manifest(
    *,
    lane: str,
    run_id: str,
    target_path: str | None,
    expected_changed_paths: list[str],
    finding_ids: list[str] | None = None,
    metadata: dict | None = None,
) -> dict:
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(MANIFEST_DIR, 0o700)
    norm = []
    for p in expected_changed_paths:
        if not p:
            continue
        try:
            norm.append(rel_to_aiw(p))
        except Exception:
            # Formal reports/evidence outside the AIW repo are not staged by git,
            # but remain in the manifest as external artifacts for traceability.
            norm.append(str(p))
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "lane": lane,
        "base_sha": current_head(),
        "target_path": target_path,
        "expected_changed_paths": sorted(set(norm)),
        "finding_ids": finding_ids or [],
        "metadata": metadata or {},
        "status": "created",
        "created_at": datetime.now(TZ).isoformat(),
    }
    p = MANIFEST_DIR / f"{run_id}.json"
    p.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(p, 0o600)
    return manifest


def load_manifests() -> list[dict]:
    out = []
    for p in sorted(MANIFEST_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and data.get("status") not in {"committed", "rejected", "superseded"}:
            data["manifest_path"] = str(p)
            out.append(data)
    return out


def mark_manifest(run_id: str, status: str, **fields) -> None:
    p = MANIFEST_DIR / f"{run_id}.json"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return
    data.update(fields)
    data["status"] = status
    data["updated_at"] = datetime.now(TZ).isoformat()
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def strip_frontmatter_and_code(text: str) -> str:
    text = re.sub(r"^---\n.*?\n---\n?", "", text, flags=re.S)
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return text


def material_markers_for(path: str) -> set[str]:
    raw = str(path or "").strip().strip("`")
    if not raw:
        return set()
    p = Path(raw)
    base = p.name
    stem = p.stem
    return {raw, base, stem, f"[来源: {base}]", f"[source: {base}]", f"material_id:{stem}", f"material_id: {stem}"}


def material_applied_in_body(material_path: str, chapter_text: str) -> bool:
    body = strip_frontmatter_and_code(chapter_text)
    return any(marker and marker in body for marker in material_markers_for(material_path))


def source_index_eligibility(item: dict, *, chapter_text: str | None = None) -> tuple[bool, str]:
    action = str(item.get("action") or item.get("status") or "")
    if action in TERMINAL_ACTIONS:
        return False, f"terminal-action:{action}"
    if action.startswith(INELIGIBLE_ROUTE_PREFIXES):
        return False, f"terminal-action:{action}"
    route_status = str(item.get("route_status") or "")
    if route_status.startswith(INELIGIBLE_ROUTE_PREFIXES):
        return False, f"route-status:{route_status}"
    if route_status and route_status != "existing-chapter-routed":
        return False, f"route-status:{route_status}"
    try:
        rc = int(item.get("route_confidence")) if item.get("route_confidence") is not None else None
    except (TypeError, ValueError):
        rc = None
    if rc is not None and rc < MIN_ROUTE_CONFIDENCE:
        return False, f"low-route-confidence:{rc}"
    if not item.get("target_path"):
        return False, "missing-target_path"
    mat = str(item.get("path") or "").strip().strip("`")
    if not mat:
        return False, "missing-material_path"
    if chapter_text is not None and material_applied_in_body(mat, chapter_text):
        return False, "material-already-applied-in-body"
    return True, "eligible"


def classify_changed_markdown(path: str) -> str:
    """body-change/frontmatter-only/no-content-change for a staged or unstaged md path."""
    d = run_git(["diff", "--", path]).stdout + run_git(["diff", "--cached", "--", path]).stdout
    added_body = removed_body = added_fm = removed_fm = 0
    in_fm = False
    for line in d.splitlines():
        if line.startswith("@@"):
            in_fm = False
            continue
        val = line[1:] if line[:1] in "+-" and not line.startswith(("+++", "---")) else None
        if val is None:
            continue
        if val.strip() == "---":
            in_fm = not in_fm
        if line.startswith("+"):
            if in_fm: added_fm += 1
            else: added_body += 1
        elif line.startswith("-"):
            if in_fm: removed_fm += 1
            else: removed_body += 1
    if added_body or removed_body:
        return "body-change"
    if added_fm or removed_fm:
        return "frontmatter-only"
    return "no-content-change"


def deletion_count(path: str) -> int:
    d = run_git(["diff", "--cached", "--", path]).stdout or run_git(["diff", "--", path]).stdout
    return sum(1 for line in d.splitlines() if line.startswith("-") and not line.startswith("---"))

```

### `aiw-body-apply-context.py`

- path：`/Users/gracker/.hermes/scripts/aiw-body-apply-context.py`
- sha256-16：`20b0590ad2929184`
- bytes：`12694`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Select one AIW body-apply candidate for a Hermes agent run.

This script is intentionally non-mutating for chapter bodies. It creates only
private lease/evidence state under ~/.hermes/state. The agent cron consumes the
JSON context, edits exactly one existing AIW chapter, then updates queue/index.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from aiw_pipeline_common import (
    create_manifest,
    current_head,
    material_applied_in_body,
    porcelain_paths,
    source_index_eligibility,
    unique_report_path,
)

TZ = ZoneInfo("Asia/Shanghai")
AIW = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki")
SRC = AIW / "src"
META = AIW / "metadata"
QUEUE = META / "queue.json"
SOURCE_INDEX = META / "source-index.json"
STATE = Path("/Users/gracker/.hermes/state/aiw-body-apply")
REPORT_DIR = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AIW自动化流水线")

ANDROID_BASELINE = "android-17.0.0_r1"


def jload(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def read(path: Path, limit: int | None = None) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    if limit and len(text) > limit:
        return text[: limit // 2] + "\n\n[...truncated...]\n\n" + text[-limit // 2 :]
    return text


def frontmatter(path: Path) -> dict:
    text = read(path, 12000)
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    data: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" in line and not line.lstrip().startswith("-"):
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip().strip('"\'')
    return data


def chapter_files() -> list[tuple[Path, dict]]:
    out = []
    if not SRC.exists():
        return out
    for path in SRC.rglob("*.md"):
        if path.name.lower() in {"readme.md", "summary.md"}:
            continue
        fm = frontmatter(path)
        out.append((path, fm))
    return out


def resolve_target(item: dict, chapters: list[tuple[Path, dict]]) -> Path | None:
    raw = item.get("target_path") or item.get("path")
    if raw:
        p = AIW / raw if not str(raw).startswith("/") else Path(raw)
        try:
            p.resolve().relative_to(SRC.resolve())
        except Exception:
            return None
        if p.exists() and p.is_file():
            return p
        # Freeze means no new chapters; do not return missing path.
        return None

    section = str(item.get("section") or item.get("chapter") or "").strip()
    section = section.replace("§", "").strip()
    if section:
        hay_terms = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]{2,}", str(item.get("title") or item.get("section_title") or "").lower())
        # Exact chapter frontmatter match first. Historical AIW has a few duplicate
        # chapter numbers; when multiple files match, choose the one whose title/path
        # overlaps the queue/source title instead of the first filesystem hit.
        exact: list[tuple[int, Path]] = []
        for p, fm in chapters:
            if str(fm.get("chapter", "")).strip() == section:
                hay = (str(p).lower() + " " + json.dumps(fm, ensure_ascii=False).lower())
                score = sum(1 for t in hay_terms if t.lower() in hay)
                exact.append((score, p))
        if exact:
            exact.sort(reverse=True, key=lambda x: x[0])
            return exact[0][1]
        # Some historical items store ch02 / 2.31; allow prefix chapter-family match.
        sec_prefix = section.split(".", 1)[0].lstrip("ch0").lstrip("ch")
        scored: list[tuple[int, Path]] = []
        for p, fm in chapters:
            chap = str(fm.get("chapter", ""))
            if sec_prefix and chap.split(".", 1)[0].lstrip("0") != sec_prefix:
                continue
            hay = (str(p).lower() + " " + json.dumps(fm, ensure_ascii=False).lower())
            score = sum(1 for t in hay_terms if t.lower() in hay)
            scored.append((score, p))
        scored.sort(reverse=True, key=lambda x: x[0])
        if scored and scored[0][0] > 0:
            return scored[0][1]
    return None


def queue_candidates(chapters: list[tuple[Path, dict]]) -> list[dict]:
    raw = jload(QUEUE, [])
    items = raw if isinstance(raw, list) else raw.get("pending", raw.get("items", []))
    out = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        if item.get("status", "pending") != "pending":
            continue
        target = resolve_target(item, chapters)
        if not target:
            continue
        mats = item.get("material_paths") or ([item.get("link")] if item.get("link") else [])
        target_text = read(target, 40000)
        # Only a stable source marker / material id in the chapter body proves
        # material application. A filename in frontmatter such as gap_source or
        # review_notes must not make the selector skip the item.
        if any(str(m) and material_applied_in_body(str(m), target_text) for m in mats):
            continue
        out.append({
            "source": "queue",
            "queue_index": idx,
            "priority": int(item.get("priority") or 50),
            "title": item.get("title") or item.get("section_title") or target.stem,
            "target_path": str(target.relative_to(AIW)),
            "material_paths": mats,
            "item": item,
        })
    return out


def source_index_candidates(chapters: list[tuple[Path, dict]]) -> list[dict]:
    data = jload(SOURCE_INDEX, {"files": []})
    files = data.get("files", []) if isinstance(data, dict) else []
    out = []
    draft_chapters = [(p, fm) for p, fm in chapters if str(fm.get("status", "")).strip().strip('"\'') == "draft"]
    for idx, item in enumerate(files):
        if not isinstance(item, dict):
            continue
        mat = str(item.get("path") or "").strip().strip('`')
        if not mat:
            continue
        target = None
        match_reason = "explicit-target"
        # Freeze-safe rule: source-index material may only be applied when the
        # collector/classifier already routed it to a concrete existing chapter.
        # Do not guess from broad chapter labels (ch16) or generic title overlap;
        # that previously allowed AI/agent/RSS noise to leak into AIW chapters.
        if item.get("target_path") or item.get("applied_target_path"):
            target = resolve_target({"target_path": item.get("target_path") or item.get("applied_target_path")}, chapters)
        if not target:
            continue
        target_text = read(target, 40000)
        eligible, reason = source_index_eligibility(item, chapter_text=target_text)
        if not eligible:
            continue
        out.append({
            "source": "source-index",
            "source_index": idx,
            "priority": int(item.get("score") or (85 if item.get("section") else 70)),
            "title": item.get("title") or target.stem,
            "target_path": str(target.relative_to(AIW)),
            "material_paths": [mat],
            "match_reason": match_reason,
            "eligibility_reason": reason,
            "item": item,
        })
    return out


def main() -> int:
    STATE.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE, 0o700)
    if not AIW.exists() or not SRC.exists():
        print(json.dumps({"status": "blocked", "reason": "AIW repo/src missing", "aiw": str(AIW)}, ensure_ascii=False))
        return 0

    dirty = porcelain_paths()
    if dirty:
        payload = {
            "schema_version": 1,
            "profile": "aiw-body-apply",
            "status": "blocked",
            "reason": "dirty-worktree-before-run",
            "dirty_paths": dirty[:50],
            "aiw_repo": str(AIW),
            "generated_at": datetime.now(TZ).isoformat(),
        }
        (STATE / "latest-context.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    chapters = chapter_files()
    candidates = queue_candidates(chapters) + source_index_candidates(chapters)
    candidates.sort(key=lambda x: (x.get("priority", 0), 1 if x.get("source") == "queue" else 0), reverse=True)
    if not candidates:
        payload = {
            "schema_version": 1,
            "profile": "aiw-body-apply",
            "status": "no-candidate",
            "generated_at": datetime.now(TZ).isoformat(),
            "scanned": {"chapters": len(chapters), "eligible": 0, "candidates": 0},
        }
        (STATE / "latest-context.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    cand = candidates[0]
    target = AIW / cand["target_path"]
    materials = []
    for m in cand.get("material_paths") or []:
        p = Path(m)
        if p.exists() and p.is_file():
            materials.append({"path": str(p), "sha16": sha_text(read(p)), "excerpt": read(p, 9000)})
        else:
            materials.append({"path": str(m), "sha16": "", "excerpt": ""})

    now = datetime.now(TZ)
    run_id = now.strftime("%Y%m%d-%H%M%S") + "-" + sha_text(json.dumps(cand, ensure_ascii=False))[:8]
    formal_report_path = str(unique_report_path("aiw-body-apply", run_id, now))
    expected_paths = [cand["target_path"], "metadata/queue.json", "metadata/source-index.json"]
    manifest = create_manifest(
        lane="aiw-body-apply",
        run_id=run_id,
        target_path=cand["target_path"],
        expected_changed_paths=expected_paths + [formal_report_path, str(STATE / f"{run_id}.json")],
        metadata={"candidate_source": cand.get("source"), "candidate_title": cand.get("title")},
    )
    payload = {
        "schema_version": 1,
        "profile": "aiw-body-apply",
        "status": "candidate_ready",
        "run_id": run_id,
        "lane": "aiw-body-apply",
        "base_sha": current_head(),
        "manifest_path": str(Path("/Users/gracker/.hermes/state/aiw-run-manifests") / f"{run_id}.json"),
        "generated_at": now.isoformat(),
        "aiw_repo": str(AIW),
        "formal_report_path": formal_report_path,
        "allowed_changed_paths": manifest["expected_changed_paths"],
        "candidate": cand,
        "target": {
            "path": str(target),
            "relative_path": cand["target_path"],
            "sha16": sha_text(read(target)),
            "frontmatter": frontmatter(target),
            "excerpt": read(target, 12000),
        },
        "materials": materials,
        "constraints": [
            "FINAL closed-loop writer: must modify exactly one existing src/**/*.md chapter when candidate_ready",
            "No new chapter files; do not edit src/SUMMARY.md",
            f"Android baseline: {ANDROID_BASELINE}; do not introduce conclusions for any version higher than Android 17",
            "Every new technical assertion must cite source material with [来源: ...] or [已验证: ...] style",
            "Preserve YAML frontmatter validity; update last_body_apply_at, last_body_apply_run_id, task2b_state, task6_state, task9_state/pipeline_stage as appropriate",
            "After editing, update queue/source-index item status to applied/body-applied with run_id and target_path",
            "Write Obsidian report and evidence; run check-metadata.py on changed chapter and check-summary-links.py; do not run aiw-git-sync.py from this lane",
        ],
    }
    out = STATE / "latest-context.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(out, 0o600)
    # Emit complete valid JSON. Cron output remains modest (~30KB) and downstream
    # agents/tools must be able to parse the pre-run contract exactly; truncating
    # mid-string creates invalid JSON and breaks the transaction boundary.
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

```

### `aiw-review-finalize-context.py`

- path：`/Users/gracker/.hermes/scripts/aiw-review-finalize-context.py`
- sha256-16：`9755d1c62a381a6f`
- bytes：`8400`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Select one AIW ready-for-review chapter for a real review/finalize agent run.

Non-mutating pre-run context script. It intentionally selects exactly one existing
chapter and lets the Hermes agent decide finalized vs needs-rework after reading
chapter/source evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from aiw_pipeline_common import create_manifest, current_head, porcelain_paths, unique_report_path

TZ = ZoneInfo("Asia/Shanghai")
AIW = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki")
STATE = Path("/Users/gracker/.hermes/state/aiw-review-finalize-apply")
FORMAL_ROOT = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AIW自动化流水线")
SRC = AIW / "src"


def sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def parse_fm(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}, text[:6000]
    fm = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        fm[k.strip()] = v.strip().strip('"\'')
    return fm, text[m.end():]


def jload(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def material_candidates(fm: dict, body: str) -> list[str]:
    out: list[str] = []
    for key in ("last_body_apply_source", "source", "material", "gap_source"):
        v = fm.get(key)
        if v and v.endswith(".md"):
            out.append(v)
    for m in re.findall(r"DeepResearch/[\w\-./\u4e00-\u9fff]+\.md|[0-9]{4}-[0-9]{2}-[0-9]{2}-[\w\-.\u4e00-\u9fff]+\.md", body):
        out.append(m)
    # source-index reverse lookup by target_path
    rel = None
    return list(dict.fromkeys(out))[:6]


def resolve_materials(names: list[str]) -> list[dict]:
    roots = [AIW.parent / "DeepResearch", AIW.parent / "技术文章", AIW.parent]
    found: list[dict] = []
    for name in names:
        p = Path(name)
        candidates = []
        if p.is_absolute():
            candidates.append(p)
        else:
            candidates += [AIW.parent / name, AIW.parent / "DeepResearch" / p.name]
            for root in roots:
                candidates.append(root / p.name)
        chosen = None
        for c in candidates:
            if c.exists() and c.is_file():
                chosen = c
                break
        if not chosen:
            # bounded basename scan only if needed
            for root in roots[:2]:
                try:
                    matches = list(root.rglob(p.name))[:1]
                except Exception:
                    matches = []
                if matches:
                    chosen = matches[0]
                    break
        if chosen:
            txt = chosen.read_text(encoding="utf-8", errors="ignore")
            found.append({"path": str(chosen), "sha16": sha16(txt), "excerpt": txt[:7000]})
    return found[:4]


def source_index_materials_for(rel: str) -> list[str]:
    idx = jload(AIW / "metadata/source-index.json", {"files": []})
    out = []
    for item in idx.get("files", []) if isinstance(idx, dict) else []:
        if item.get("target_path") == rel or item.get("applied_target_path") == rel:
            p = item.get("path")
            if p:
                out.append(str(p))
        # Also include recently body-applied entries mentioning same file path.
        if item.get("status") == "applied" and item.get("target_path") == rel and item.get("path"):
            out.append(str(item.get("path")))
    return out


def priority(path: Path, fm: dict, body: str) -> tuple[int, str]:
    rel = str(path.relative_to(AIW))
    score = 0
    if fm.get("status") in {"ready-for-review", "review", "reviewing"}:
        score += 100
    if fm.get("task6_state") in {"revisiting", "pending"}:
        score += 30
    if fm.get("task9_state") in {"pending", "revisiting"}:
        score += 25
    if fm.get("last_body_apply_at"):
        score += 25
    if "[待验证" in body or "待验证" in body:
        score += 8
    return (-score, rel)


def main() -> int:
    now = datetime.now(TZ)
    run_id = now.strftime("%Y%m%d-%H%M%S") + "-" + hashlib.sha1(os.urandom(16)).hexdigest()[:8]
    STATE.mkdir(parents=True, exist_ok=True)
    candidates = []
    if not AIW.exists():
        out = {"schema_version": 1, "profile": "aiw-review-finalize-apply", "status": "blocked", "reason": f"AIW repo missing: {AIW}"}
    elif porcelain_paths():
        out = {
            "schema_version": 1,
            "profile": "aiw-review-finalize-apply",
            "status": "blocked",
            "reason": "dirty-worktree-before-run",
            "dirty_paths": porcelain_paths()[:50],
            "aiw_repo": str(AIW),
            "generated_at": now.isoformat(timespec="seconds"),
        }
    else:
        for p in SRC.rglob("*.md"):
            if p.name == "SUMMARY.md":
                continue
            txt = p.read_text(encoding="utf-8", errors="ignore")
            fm, body = parse_fm(txt)
            status = fm.get("status", "").strip().strip('"\'')
            if status in {"ready-for-review", "review", "reviewing"} or fm.get("task6_state") == "revisiting" or fm.get("task9_state") == "pending":
                if status in {"finalized", "published"}:
                    continue
                candidates.append((priority(p, fm, body), p, fm, txt, body))
        candidates.sort(key=lambda x: x[0])
        if not candidates:
            out = {"schema_version": 1, "profile": "aiw-review-finalize-apply", "status": "no-candidate", "generated_at": now.isoformat(timespec="seconds"), "aiw_repo": str(AIW), "scanned": {"candidates": 0}}
        else:
            _, p, fm, txt, body = candidates[0]
            rel = str(p.relative_to(AIW))
            mats = source_index_materials_for(rel) + material_candidates(fm, body)
            formal_report_path = str(unique_report_path("aiw-review-finalize-apply", run_id, now))
            manifest = create_manifest(
                lane="aiw-review-finalize-apply",
                run_id=run_id,
                target_path=rel,
                expected_changed_paths=[rel, "metadata/review-findings.json", formal_report_path, str(STATE / f"{run_id}.json")],
                metadata={"frontmatter_status": fm.get("status")},
            )
            out = {
                "schema_version": 1,
                "profile": "aiw-review-finalize-apply",
                "status": "review_candidate_ready",
                "run_id": run_id,
                "lane": "aiw-review-finalize-apply",
                "base_sha": current_head(),
                "manifest_path": str(Path("/Users/gracker/.hermes/state/aiw-run-manifests") / f"{run_id}.json"),
                "generated_at": now.isoformat(timespec="seconds"),
                "aiw_repo": str(AIW),
                "formal_report_path": formal_report_path,
                "allowed_changed_paths": manifest["expected_changed_paths"],
                "target": {"path": str(p), "relative_path": rel, "sha16": sha16(txt), "frontmatter": fm, "excerpt": txt[:9000]},
                "materials": resolve_materials(mats),
                "constraints": [
                    "Real OpenClaw-style review/fix/finalize: inspect exactly one existing ready-for-review chapter",
                    "May edit the selected chapter and review-finding metadata only; no new chapter and no SUMMARY edits",
                    "Finalize only with structured source_evidence and no open P0/P1 finding; otherwise keep ready-for-review or set needs-rework",
                    "Run metadata/SUMMARY/diff checks; do not run git sync from this lane",
                ],
            }
    latest = STATE / "latest-context.json"
    latest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("status") != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())

```

### `aiw-polish-context.py`

- path：`/Users/gracker/.hermes/scripts/aiw-polish-context.py`
- sha256-16：`5d403a9b88d069f8`
- bytes：`13777`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Select one existing AIW chapter for high-throughput polish/review lanes.

This restores OpenClaw-like article polishing throughput without creating new
chapters. It is a non-mutating context producer: Hermes agent lanes consume the
JSON and perform the actual chapter patch + validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from aiw_pipeline_common import create_manifest, current_head, porcelain_paths, unique_report_path

TZ = ZoneInfo("Asia/Shanghai")
AIW = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki")
SRC = AIW / "src"
FORMAL_ROOT = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AIW自动化流水线")
STATE_ROOT = Path("/Users/gracker/.hermes/state/aiw-polish-apply")
ANDROID_BASELINE = "android-17.0.0_r1"

MODES = {"deep-review", "rework", "idle-audit", "draft-polish"}


def sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def read(path: Path, limit: int | None = None) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    if limit and len(text) > limit:
        return text[: limit // 2] + "\n\n[...truncated...]\n\n" + text[-limit // 2 :]
    return text


def jload(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def parse_fm(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not m:
        return {}, text
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line or line.lstrip().startswith("-"):
            continue
        k, v = line.split(":", 1)
        fm[k.strip()] = v.strip().strip('"\'')
    return fm, text[m.end():]


def rel(path: Path) -> str:
    return str(path.relative_to(AIW))


def recent_paths(mode: str, hours: int = 36) -> set[str]:
    state = STATE_ROOT / mode
    out: set[str] = set()
    cutoff = datetime.now(TZ) - timedelta(hours=hours)
    for p in state.glob("*.json"):
        try:
            if datetime.fromtimestamp(p.stat().st_mtime, TZ) < cutoff:
                continue
            data = json.loads(p.read_text(encoding="utf-8"))
            rp = data.get("target", {}).get("relative_path")
            if rp:
                out.add(str(rp))
        except Exception:
            continue
    return out


def material_names_from_body(body: str) -> list[str]:
    pats = [
        r"DeepResearch/[\w\-./\u4e00-\u9fff]+\.md",
        r"技术文章/[\w\-./\u4e00-\u9fff]+\.md",
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[\w\-.\u4e00-\u9fff]+\.md",
    ]
    out: list[str] = []
    for pat in pats:
        out.extend(re.findall(pat, body))
    return list(dict.fromkeys(out))[:8]


def source_index_materials_for(relative_path: str) -> list[str]:
    idx = jload(AIW / "metadata/source-index.json", {"files": []})
    out: list[str] = []
    files = idx.get("files", []) if isinstance(idx, dict) else []
    for item in files:
        if not isinstance(item, dict):
            continue
        targets = {item.get("target_path"), item.get("applied_target_path"), item.get("path")}
        if relative_path in targets or item.get("target_path") == relative_path or item.get("applied_target_path") == relative_path:
            p = item.get("path")
            if p:
                out.append(str(p))
    return list(dict.fromkeys(out))[:8]


def resolve_materials(names: list[str]) -> list[dict]:
    roots = [AIW.parent / "DeepResearch", AIW.parent / "技术文章", AIW.parent, AIW]
    found: list[dict] = []
    for name in names:
        if not name:
            continue
        raw = Path(str(name).strip().strip('`'))
        candidates: list[Path] = []
        if raw.is_absolute():
            candidates.append(raw)
        else:
            candidates.extend([AIW.parent / raw, AIW / raw])
            for root in roots:
                candidates.append(root / raw.name)
        chosen = next((c for c in candidates if c.exists() and c.is_file()), None)
        if not chosen:
            for root in roots[:2]:
                try:
                    matches = list(root.rglob(raw.name))[:1]
                except Exception:
                    matches = []
                if matches:
                    chosen = matches[0]
                    break
        if chosen:
            txt = read(chosen, 9000)
            found.append({"path": str(chosen), "sha16": sha16(txt), "excerpt": txt})
    return found[:5]


def chapter_records() -> list[dict]:
    records: list[dict] = []
    if not SRC.exists():
        return records
    for p in SRC.rglob("*.md"):
        if p.name in {"SUMMARY.md", "README.md"}:
            continue
        txt = read(p)
        fm, body = parse_fm(txt)
        records.append({"path": p, "rel": rel(p), "fm": fm, "body": body, "text": txt})
    return records


def quality_flags(fm: dict, body: str) -> list[str]:
    flags: list[str] = []
    if re.search(r"Android\s*(?:1[89]|[2-9][0-9])|API\s*(?:3[8-9]|[4-9][0-9])|android-(?:1[89]|[2-9][0-9])", body, re.I):
        flags.append("above-android17-boundary-risk")
    if "待验证" in body or "TODO" in body or "TBD" in body:
        flags.append("pending-verification-marker")
    if body.count("[来源:") + body.count("[已验证:") < 2:
        flags.append("thin-source-marking")
    if len(body) < 3500:
        flags.append("thin-body")
    if not fm.get("last_verified"):
        flags.append("missing-last_verified")
    if not fm.get("confidence"):
        flags.append("missing-confidence")
    return flags


def score_record(mode: str, rec: dict, recent: set[str]) -> tuple[int, str] | None:
    fm = rec["fm"]
    body = rec["body"]
    status = str(fm.get("status", "")).strip().strip('"\'')
    task6 = str(fm.get("task6_state", "")).strip()
    task9 = str(fm.get("task9_state", "")).strip()
    flags = quality_flags(fm, body)
    r = rec["rel"]
    if r in recent:
        return None

    score = 0
    if mode == "deep-review":
        # Deep-review is for reviewable chapters with enough existing body or
        # source material. Do not pick thin placeholder chapters with no
        # materials: that turns audit into unsupported drafting.
        if status not in {"ready-for-review", "review", "reviewing"}:
            return None
        has_material = bool(source_index_materials_for(r) or material_names_from_body(body))
        if "thin-body" in flags and not has_material:
            return None
        score += 100
        if task9 in {"pending", "revisiting"}: score += 25
        if task6 in {"revisiting", "pending"}: score += 20
        if flags: score += min(20, len(flags) * 5)
    elif mode == "rework":
        if status not in {"needs-rework", "ready-for-review", "review"} and task6 != "needs-rework" and task9 != "needs-rework" and "待验证" not in body:
            return None
        score += 90
        if status == "needs-rework": score += 50
        if task6 == "needs-rework" or task9 == "needs-rework": score += 40
        if "待验证" in body: score += 10
    elif mode == "idle-audit":
        if status not in {"finalized", "verified"}:
            return None
        score += 60
        # Prefer finalized chapters that still carry suspicious markers.
        score += min(45, len(flags) * 9)
        if not flags and fm.get("last_idle_audit_at"):
            score -= 20
    elif mode == "draft-polish":
        if status != "draft":
            return None
        score += 100
        if len(body) >= 2500: score += 20
        if flags: score += min(20, len(flags) * 5)
    else:
        return None
    # Stable spread: avoid always choosing lexicographically first chapters.
    ageish = 9999999999 - int(sha16(r), 16) % 100000
    return (-score, str(ageish), r)


def select(mode: str) -> dict | None:
    recent = recent_paths(mode)
    scored: list[tuple[tuple[int, str, str], dict]] = []
    for rec in chapter_records():
        s = score_record(mode, rec, recent)
        if s is not None:
            scored.append((s, rec))
    scored.sort(key=lambda x: x[0])
    return scored[0][1] if scored else None


def mode_constraints(mode: str) -> list[str]:
    base = [
        "Modify exactly one existing src/**/*.md chapter when candidate_ready; no new chapter files.",
        "Never edit src/SUMMARY.md from this lane.",
        f"Android baseline: {ANDROID_BASELINE}; do not introduce conclusions for any version higher than Android 17.",
        "Prefer real safe article patches over report-only output.",
        "Run check-metadata.py, check-summary-links.py, and git diff --check before final response.",
        "Write a formal Obsidian report under OpenClaw定时任务/AIW自动化流水线; ~/.hermes/state is evidence only.",
        "Do not run git sync or any git add/commit/push command from this lane; a separate manifest gate owns commits.",
    ]
    if mode == "deep-review":
        base += ["OpenClaw-style deep technical review: fix source-boundary/claim/readability issues and write a logs/deep-review/*.md audit log."]
    elif mode == "rework":
        base += ["Resolve needs-rework/pending-verification markers; update task6/task9/pipeline_stage according to the fix."]
    elif mode == "idle-audit":
        base += ["Idle audit finalized chapters: patch only safe issues; do not churn text if no real issue is found; write logs/audit/*.md."]
    elif mode == "draft-polish":
        base += ["Polish an existing draft toward ready-for-review; do not create new files or expand unsupported claims."]
    return base


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=sorted(MODES))
    args = ap.parse_args()
    mode = args.mode
    now = datetime.now(TZ)
    state = STATE_ROOT / mode
    state.mkdir(parents=True, exist_ok=True)
    os.chmod(state, 0o700)
    if not AIW.exists() or not SRC.exists():
        out = {"schema_version": 1, "profile": f"aiw-polish-{mode}", "mode": mode, "status": "blocked", "reason": f"AIW repo missing: {AIW}"}
    elif porcelain_paths():
        out = {
            "schema_version": 1,
            "profile": f"aiw-polish-{mode}",
            "mode": mode,
            "status": "blocked",
            "reason": "dirty-worktree-before-run",
            "dirty_paths": porcelain_paths()[:50],
            "aiw_repo": str(AIW),
            "generated_at": now.isoformat(timespec="seconds"),
        }
    else:
        rec = select(mode)
        if not rec:
            out = {"schema_version": 1, "profile": f"aiw-polish-{mode}", "mode": mode, "status": "no-new-input", "generated_at": now.isoformat(timespec="seconds"), "aiw_repo": str(AIW)}
        else:
            run_id = now.strftime("%Y%m%d-%H%M%S") + "-" + mode + "-" + sha16(rec["rel"])[:8]
            mats = source_index_materials_for(rec["rel"]) + material_names_from_body(rec["body"])
            formal_report_path = str(unique_report_path(f"aiw-polish-{mode}", run_id, now))
            log_dir = {"deep-review": "logs/deep-review", "rework": "logs/rework", "idle-audit": "logs/audit", "draft-polish": "logs/review"}[mode]
            expected = [rec["rel"], f"{log_dir}/{now:%Y-%m-%d}-{run_id}-{mode}.md", formal_report_path, str(state / f"{run_id}.json")]
            if mode in {"deep-review", "rework"}:
                expected.append("metadata/review-findings.json")
            manifest = create_manifest(
                lane=f"aiw-polish-{mode}",
                run_id=run_id,
                target_path=rec["rel"],
                expected_changed_paths=expected,
                metadata={"frontmatter_status": rec["fm"].get("status"), "quality_flags": quality_flags(rec["fm"], rec["body"])},
            )
            out = {
                "schema_version": 1,
                "profile": f"aiw-polish-{mode}",
                "mode": mode,
                "status": "polish_candidate_ready",
                "run_id": run_id,
                "lane": f"aiw-polish-{mode}",
                "base_sha": current_head(),
                "manifest_path": str(Path("/Users/gracker/.hermes/state/aiw-run-manifests") / f"{run_id}.json"),
                "generated_at": now.isoformat(timespec="seconds"),
                "aiw_repo": str(AIW),
                "formal_report_path": formal_report_path,
                "allowed_changed_paths": manifest["expected_changed_paths"],
                "target": {
                    "path": str(rec["path"]),
                    "relative_path": rec["rel"],
                    "sha16": sha16(rec["text"]),
                    "frontmatter": rec["fm"],
                    "quality_flags": quality_flags(rec["fm"], rec["body"]),
                    "excerpt": rec["text"][:12000],
                },
                "materials": resolve_materials(mats),
                "constraints": mode_constraints(mode),
            }
    latest = state / "latest-context.json"
    latest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if out.get("status") == "polish_candidate_ready":
        (state / f"{out['run_id']}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("status") != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())

```

### `aiw-polish-deep-review-context.py`

- path：`/Users/gracker/.hermes/scripts/aiw-polish-deep-review-context.py`
- sha256-16：`f92cfae709b7eef2`
- bytes：`232`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import runpy, sys
sys.argv = [sys.argv[0], '--mode', 'deep-review']
runpy.run_path(str(Path(__file__).with_name('aiw-polish-context.py')), run_name='__main__')

```

### `aiw-polish-rework-context.py`

- path：`/Users/gracker/.hermes/scripts/aiw-polish-rework-context.py`
- sha256-16：`9ff26b742f21bbab`
- bytes：`227`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import runpy, sys
sys.argv = [sys.argv[0], '--mode', 'rework']
runpy.run_path(str(Path(__file__).with_name('aiw-polish-context.py')), run_name='__main__')

```

### `aiw-polish-idle-audit-context.py`

- path：`/Users/gracker/.hermes/scripts/aiw-polish-idle-audit-context.py`
- sha256-16：`076afc1a87256c94`
- bytes：`231`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import runpy, sys
sys.argv = [sys.argv[0], '--mode', 'idle-audit']
runpy.run_path(str(Path(__file__).with_name('aiw-polish-context.py')), run_name='__main__')

```

### `aiw-polish-draft-polish-context.py`

- path：`/Users/gracker/.hermes/scripts/aiw-polish-draft-polish-context.py`
- sha256-16：`d7c5c91d35e4ac98`
- bytes：`233`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import runpy, sys
sys.argv = [sys.argv[0], '--mode', 'draft-polish']
runpy.run_path(str(Path(__file__).with_name('aiw-polish-context.py')), run_name='__main__')

```

### `aiw-git-sync.py`

- path：`/Users/gracker/.hermes/scripts/aiw-git-sync.py`
- sha256-16：`921b5e74839e6587`
- bytes：`15627`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Commit and push AIW automation outputs from the Android-Internal-Wiki repo.

Allowlist-based sync with descriptive OpenClaw-style commit messages. It syncs
generated AIW artifacts and metadata, but ignores suspicious/editor duplicate
files such as `.github/workflows/build 2.yml`.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from aiw_pipeline_common import deletion_count, load_manifests, mark_manifest

TZ = ZoneInfo("Asia/Shanghai")
REPO = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki")
STATE = Path("/Users/gracker/.hermes/state/aiw-git-sync")
LOCK = STATE / "sync.lock"
PENDING_MSG = STATE / "pending-commit-msg.txt"
FREEZE_GUARD = Path("/Users/gracker/.hermes/scripts/aiw-freeze-guard.py")
ALLOWLIST = [
    "intake/",
    "metadata/",
    "logs/",
    "src/",
    "README.md",
    "SUMMARY.md",
]


def run(cmd: list[str], check: bool = False, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(REPO), text=True, capture_output=True, timeout=timeout, check=check)


def git(*args: str, check: bool = False, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], check=check, timeout=timeout)


def acquire_lock() -> bool:
    STATE.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        try:
            if datetime.now().timestamp() - LOCK.stat().st_mtime > 7200:
                LOCK.unlink()
                fd = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            else:
                return False
        except FileNotFoundError:
            return acquire_lock()
    with os.fdopen(fd, "w") as f:
        f.write(str(os.getpid()))
    return True


def release_lock() -> None:
    try:
        LOCK.unlink()
    except FileNotFoundError:
        pass


def allowed_changed_paths() -> list[str]:
    # Use NUL porcelain so paths with spaces/non-ASCII are parsed exactly.
    r = git("status", "--porcelain", "-z")
    entries = [x for x in r.stdout.split("\0") if x]
    paths: list[str] = []
    i = 0
    while i < len(entries):
        entry = entries[i]
        status = entry[:2]
        path = entry[3:]
        if status[0] in {"R", "C"}:
            i += 1
            if i < len(entries):
                path = entries[i]
        if any(path == p.rstrip("/") or path.startswith(p) for p in ALLOWLIST):
            paths.append(path)
        i += 1
    return sorted(set(paths))


def parse_frontmatter(path: str) -> dict[str, str]:
    p = REPO / path
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")[:12000]
    except Exception:
        return {}
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.lstrip().startswith(("#", "-")):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"\'')
    return fm


def status_delta(path: str) -> str | None:
    d = git("diff", "--cached", "-U0", "--", path).stdout
    old = new = None
    for line in d.splitlines():
        if line.startswith("-status:"):
            old = line.split(":", 1)[1].strip().strip('"\'')
        elif line.startswith("+status:"):
            new = line.split(":", 1)[1].strip().strip('"\'')
    if old and new and old != new:
        return f"{old}→{new}"
    if new:
        return new
    return None


def path_title(path: str) -> str:
    fm = parse_frontmatter(path)
    chapter = fm.get("chapter") or ""
    title = fm.get("title") or Path(path).stem.replace("-", " ")
    prefix = f"{chapter} " if chapter else ""
    s = (prefix + title).strip()
    return re.sub(r"\s+", " ", s)[:70]


def source_index_route_summary() -> str | None:
    d = git("diff", "--cached", "-U0", "--", "metadata/source-index.json").stdout
    if not d:
        return None
    routed = d.count('+      "route_status": "existing-chapter-routed"')
    quarantined = d.count('+      "route_status": "quarantined-non-aiw-or-aggregate"')
    unrouted = d.count('+      "route_status": "unrouted-existing-chapter-needed"')
    parts = []
    if routed: parts.append(f"route {routed}")
    if quarantined: parts.append(f"quarantine {quarantined}")
    if unrouted: parts.append(f"mark {unrouted} unrouted")
    return ", ".join(parts) if parts else None


def findings_summary() -> str | None:
    d = git("diff", "--cached", "-U0", "--", "metadata/review-findings.json").stdout
    if not d:
        return None
    opened = d.count('+      "status": "open"')
    fixed = d.count('+      "status": "fixed"')
    verified = d.count('+      "status": "verified"')
    parts = []
    if opened: parts.append(f"open {opened}")
    if fixed: parts.append(f"fix {fixed}")
    if verified: parts.append(f"verify {verified}")
    return ", ".join(parts) if parts else "update findings"


def infer_stage(staged: list[str]) -> str:
    joined = "\n".join(staged)
    if "metadata/review-findings.json" in staged:
        return "review-findings"
    if "metadata/source-index.json" in staged and source_index_route_summary():
        return "source-route"
    if "metadata/queue.json" in staged and not any(p.startswith("src/") for p in staged):
        return "queue-state"
    if any(p.startswith("logs/deep-review/") for p in staged):
        return "deep-review"
    if any(p.startswith("logs/audit/") for p in staged):
        return "audit"
    if any(p.startswith("logs/rework") for p in staged):
        return "rework"
    srcs = [p for p in staged if p.startswith("src/") and p.endswith(".md")]
    deltas = [status_delta(p) for p in srcs]
    if any(d and "finalized" in d for d in deltas):
        return "review-finalize"
    if any(d and "needs-rework" in d for d in deltas):
        return "rework"
    if "body-applied" in joined or "queue.json" in joined or "source-index.json" in joined:
        return "body-apply"
    if any(p.startswith("intake/") for p in staged):
        return "intake"
    if srcs:
        return "polish"
    if any(p.startswith("metadata/") for p in staged):
        return "metadata"
    return "sync"


def pending_message_if_valid(staged: list[str]) -> str | None:
    if not PENDING_MSG.exists():
        return None
    msg = PENDING_MSG.read_text(encoding="utf-8", errors="ignore").strip()
    if not msg:
        return None
    # Keep user/agent-provided messages bounded and single-commit safe.
    lines = [x.rstrip() for x in msg.splitlines()]
    subject = lines[0][:160]
    body = "\n".join(lines[1:])[:3000]
    changed = "\n".join(f"- {p}" for p in staged[:40])
    return subject + ("\n" + body if body else "") + "\n\nChanged files:\n" + changed


def build_commit_message(staged: list[str], manifest: dict | None = None) -> str:
    pending = pending_message_if_valid(staged)
    if pending:
        return pending
    day = datetime.now(TZ).strftime("%Y-%m-%d")
    srcs = [p for p in staged if p.startswith("src/") and p.endswith(".md")]
    stage = infer_stage(staged)
    if manifest:
        lane = manifest.get("lane") or stage
        run_id = manifest.get("run_id") or "unknown-run"
        target = manifest.get("target_path") or (srcs[0] if srcs else "metadata")
        title = path_title(target) if target.startswith("src/") else target
        subject = f"[hermes-aiw] {lane}: {title} ({run_id})"[:180]
        body = [
            "Generated by Hermes AIW scheduled tasks with per-run manifest.",
            f"run_id: {run_id}",
            f"lane: {lane}",
            f"base_sha: {manifest.get('base_sha')}",
            f"manifest: {manifest.get('manifest_path')}",
            "",
            "Changed files:",
            *[f"- {p}" for p in staged[:60]],
        ]
        return subject + "\n\n" + "\n".join(body)
    if srcs:
        main = srcs[0]
        title = path_title(main)
        delta = status_delta(main)
        suffix = f" — {delta}" if delta else ""
        subject = f"[hermes-aiw] {stage}: {title}{suffix}"
    elif stage == "source-route":
        subject = f"[hermes-aiw] source-route: {source_index_route_summary() or 'route source-index materials'}"
    elif stage == "review-findings":
        subject = f"[hermes-aiw] review-findings: {findings_summary() or 'update findings'}"
    elif stage == "queue-state":
        subject = f"[hermes-aiw] queue-state: update queue metadata {day}"
    else:
        subject = f"[hermes-aiw] {stage}: automation outputs {day}"
    if len(srcs) > 1:
        subject += f" (+{len(srcs)-1} chapters)"
    other_count = len([p for p in staged if p not in srcs])
    if other_count:
        subject += f" + {other_count} files"
    subject = subject[:180]
    body = [
        "Generated by Hermes AIW scheduled tasks.",
        "",
        "Changed files:",
        *[f"- {p}" for p in staged[:60]],
    ]
    if len(staged) > 60:
        body.append(f"- ... {len(staged) - 60} more")
    return subject + "\n\n" + "\n".join(body)


def select_manifest_for_paths(paths: list[str]) -> tuple[dict | None, list[str], str | None]:
    """Return manifest and exact stage paths, or reason for blocking.

    Source changes require a manifest. Metadata/intake/log-only changes may use
    legacy mode so script-only collection jobs still publish safely.
    """
    manifests = load_manifests()
    dirty = set(paths)
    src_dirty = {p for p in dirty if p.startswith("src/") and p.endswith(".md")}
    if not manifests:
        if src_dirty:
            return None, [], "src-dirty-without-manifest"
        return None, paths, None
    for m in manifests:
        repo_expected = {p for p in m.get("expected_changed_paths", []) if not p.startswith("/")}
        hit = sorted(dirty & repo_expected)
        if not hit:
            continue
        extra = sorted(dirty - repo_expected)
        if extra:
            return m, [], "dirty-paths-outside-manifest:" + ", ".join(extra[:20])
        if m.get("base_sha") and git("rev-parse", "HEAD").stdout.strip() != m.get("base_sha"):
            return m, [], "head-mismatch"
        return m, hit, None
    if src_dirty:
        return None, [], "src-dirty-not-covered-by-any-manifest"
    # There are stale manifests, but current dirty files are non-src legacy outputs.
    return None, paths, None


def large_diff_block_reason(staged: list[str]) -> str | None:
    srcs = [p for p in staged if p.startswith("src/") and p.endswith(".md")]
    if len(srcs) > 3:
        return f"too-many-src-files:{len(srcs)}"
    for p in srcs:
        deleted = deletion_count(p)
        if deleted > 120:
            return f"large-deletion:{p}:{deleted}"
    return None


def main() -> int:
    if not REPO.exists():
        print(f"# AIW Git Sync\n- status: error\n- reason: repo missing: {REPO}")
        return 2
    if not acquire_lock():
        return 0
    try:
        # Restore the known-destructive compact freshness log shape if it is still only the compact uncommitted run.
        status_before = git("status", "--porcelain").stdout
        if " M metadata/freshness-log.json" in status_before:
            diff = git("diff", "--", "metadata/freshness-log.json").stdout
            if '"last_run_at"' in diff and '"priority_actions"' in diff:
                git("checkout", "--", "metadata/freshness-log.json")

        paths = allowed_changed_paths()
        if not paths:
            branch = git("branch", "--show-current").stdout.strip() or "HEAD"
            pull = git("pull", "--ff-only", "origin", branch, timeout=180)
            if pull.returncode != 0:
                print("# AIW Git Sync\n- status: pull_failed\n- 修改内容: 无本地变更，但无法 ff-only 同步\n```text\n" + (pull.stdout + pull.stderr)[-1800:] + "\n```")
                return 2
            return 0

        manifest, stage_paths, block_reason = select_manifest_for_paths(paths)
        if block_reason:
            if manifest and manifest.get("run_id"):
                mark_manifest(str(manifest["run_id"]), "blocked", block_reason=block_reason, dirty_paths=paths)
            print(
                "# AIW Git Sync\n"
                "- status: blocked\n"
                f"- reason: {block_reason}\n"
                "- 修改内容: 未提交，避免把非本轮变更扫入同一提交\n"
                f"- dirty_paths: {', '.join(paths[:30])}"
            )
            return 2

        if "src/SUMMARY.md" in stage_paths:
            summary_check = run([sys.executable, "scripts/check-summary-links.py"], timeout=120)
            if summary_check.returncode != 0:
                print("# AIW Git Sync\n- status: summary_check_failed\n- 修改内容: 未提交，SUMMARY.md 存在 mdBook 断链或空格路径\n```text\n" + (summary_check.stdout + summary_check.stderr)[-2000:] + "\n```")
                return 2

        git("add", "--", *stage_paths, check=True)
        staged = git("diff", "--cached", "--name-only").stdout.splitlines()
        if not staged:
            return 0

        reason = large_diff_block_reason(staged)
        if reason:
            git("reset", "--", *staged)
            if manifest and manifest.get("run_id"):
                mark_manifest(str(manifest["run_id"]), "needs-human-review", block_reason=reason, actual_changed_paths=staged)
            print(f"# AIW Git Sync\n- status: needs-human-review\n- reason: {reason}\n- 修改内容: 未提交，大 diff 需要人工 gate\n- 影响范围: {', '.join(staged[:30])}")
            return 2

        if FREEZE_GUARD.exists():
            guard = run([sys.executable, str(FREEZE_GUARD)], timeout=120)
            if guard.returncode != 0:
                git("reset", "--", *staged)
                print((guard.stdout + guard.stderr)[-3000:])
                return guard.returncode

        msg = build_commit_message(staged, manifest)
        c = git("commit", "-m", msg, timeout=120)
        if c.returncode != 0:
            if "nothing to commit" in (c.stdout + c.stderr).lower():
                return 0
            print("# AIW Git Sync\n- status: commit_failed\n```text\n" + (c.stdout + c.stderr)[-1800:] + "\n```")
            return 2

        if PENDING_MSG.exists():
            try:
                PENDING_MSG.unlink()
            except FileNotFoundError:
                pass

        p = git("push", "origin", "HEAD", timeout=180)
        if p.returncode != 0:
            print("# AIW Git Sync\n- status: push_failed\n- 修改内容: 已本地 commit，但 GitHub push 失败\n- 影响范围: " + ", ".join(staged[:20]) + "\n```text\n" + (p.stdout + p.stderr)[-1800:] + "\n```")
            return 2

        sha = git("rev-parse", "--short", "HEAD").stdout.strip()
        if manifest and manifest.get("run_id"):
            mark_manifest(str(manifest["run_id"]), "committed", actual_changed_paths=staged, commit_sha=sha)
        print(
            f"# AIW Git Sync · {datetime.now(TZ).date().isoformat()}\n"
            f"- status: pushed\n"
            f"- 修改内容: 已提交并推送 {len(staged)} 个 AIW 落盘文件\n"
            f"- commit: {msg.splitlines()[0]}\n"
            f"- GitHub: origin HEAD @ {sha}\n"
            f"- 影响范围: {', '.join(staged[:20])}"
        )
        return 0
    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())

```

### `aiw-throughput-watchdog.py`

- path：`/Users/gracker/.hermes/scripts/aiw-throughput-watchdog.py`
- sha256-16：`d2feda1a88babc15`
- bytes：`9306`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Daily AIW closed-loop throughput watchdog."""
from __future__ import annotations

import json
import os
import re
import subprocess
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from aiw_pipeline_common import AIW as AIW_CANONICAL, classify_changed_markdown, source_index_eligibility

TZ = ZoneInfo("Asia/Shanghai")
AIW = AIW_CANONICAL
FORMAL = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AIW自动化流水线/health")
STATE = Path("/Users/gracker/.hermes/state/aiw-throughput-watchdog")
CRON_OUT = Path("/Users/gracker/.hermes/cron/output")
AIW_JOB_IDS = {
    "body_apply": "2aa21bb1eb45",
    "review_finalize": "464ba760c0e3",
    "git_sync": "5fa9d7fe9e87",
    "deep_review": "a2fb41f345c8",
    "rework": "410de74688cd",
    "idle_audit": "fb934850da95",
    "draft_polish": "ef444f87d299",
    "daily_intake_deepresearch": "db79021b32a0",
    "daily_intake_tech_articles": "f50a04d870c3",
    "daily_intake_incremental": "2364b7bf9a07",
    "daily_intake_classify": "51d73c474658",
}


def run(cmd: list[str], cwd: Path = AIW, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, timeout=timeout)


def jload(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def git_lines(*args: str) -> list[str]:
    r = run(["git", *args])
    return [x for x in r.stdout.splitlines() if x]


def since_iso(day: str) -> str:
    return f"{day}T00:00:00+08:00"


def commit_stats(day: str) -> dict:
    lines = git_lines("log", f"--since={since_iso(day)}", "--pretty=format:%h%x09%s", "--name-only")
    commits = []
    current = None
    touched = set()
    actions = Counter()
    change_types = Counter()
    for line in lines:
        if "\t" in line and re.match(r"^[0-9a-f]{7,}\t", line):
            sha, subject = line.split("\t", 1)
            current = {"sha": sha, "subject": subject, "files": []}
            commits.append(current)
            m = re.search(r"\] ([^:]+):", subject)
            if m: actions[m.group(1)] += 1
        elif current is not None and line.strip():
            path = line.strip()
            current["files"].append(path)
            if path.startswith("src/") and path.endswith(".md"):
                touched.add(path)
    # Uncommitted classification is useful because git-sync is now separated from LLM lanes.
    for p in git_lines("status", "--porcelain"):
        path = p[3:]
        if path.startswith("src/") and path.endswith(".md"):
            change_types[classify_changed_markdown(path)] += 1
    return {"count": len(commits), "actions": dict(actions), "touched_chapters": len(touched), "uncommitted_change_types": dict(change_types), "recent": commits[:10]}


def source_stats() -> dict:
    idx = jload(AIW / "metadata/source-index.json", {"files": []})
    files = [x for x in idx.get("files", []) if isinstance(x, dict)] if isinstance(idx, dict) else []
    route = Counter(x.get("route_status") or "missing" for x in files)
    action = Counter(x.get("action") or x.get("status") or "missing" for x in files)
    eligibility = Counter()
    apply_pending = 0
    for x in files:
        ok, reason = source_index_eligibility(x)
        eligibility[reason] += 1
        if ok:
            apply_pending += 1
    return {"total": len(files), "route_status": dict(route), "action": dict(action), "eligibility": dict(eligibility), "apply_pending": apply_pending}


def chapter_status() -> dict:
    c = Counter()
    for p in (AIW / "src").rglob("*.md"):
        if p.name in {"README.md", "SUMMARY.md"}: continue
        txt = p.read_text(encoding="utf-8", errors="ignore")[:2000]
        m = re.search(r"(?m)^status:\s*[\"']?([^\"'\n]+)", txt)
        c[m.group(1).strip() if m else "missing"] += 1
    return dict(c)


def log_counts(day: str) -> dict:
    out = {}
    for lane in ["deep-review", "rework", "audit", "review"]:
        root = AIW / "logs" / lane
        out[lane] = len(list(root.glob(f"{day}*.md"))) if root.exists() else 0
    return out


def classify_cron_output(path: Path) -> str:
    if path.stat().st_size == 0:
        return "empty-output"
    txt = path.read_text(encoding="utf-8", errors="ignore")
    # Hermes cron files include prompt/context before the final response. Only
    # classify the response/evidence tail so prompt text containing no-new-input
    # cannot poison success metrics.
    if "## Response" in txt:
        txt = txt.split("## Response", 1)[-1]
    else:
        txt = txt[-8000:]
    low = txt.lower()
    if "dirty-worktree-before-run" in txt or "blocked" in low:
        return "blocked"
    if "no-candidate" in txt:
        return "no-candidate"
    if "no-new-input" in txt or "[silent]" in low:
        return "no-new-input"
    if "completed-no-change" in txt:
        return "completed-no-change"
    if "status: pushed" in txt or "candidate_ready" in txt or "completed" in low or "changed_paths" in txt:
        return "productive_or_completed"
    return "other"


def cron_output_stats(day: str) -> dict:
    out = {}
    for name, jid in AIW_JOB_IDS.items():
        root = CRON_OUT / jid
        counts = Counter()
        if root.exists():
            for p in root.glob(f"{day}_*.md"):
                counts[classify_cron_output(p)] += 1
        out[name] = dict(counts)
    return out


def ci_stats() -> dict:
    wf_dir = AIW / ".github" / "workflows"
    workflows = list(wf_dir.glob("*.yml")) + list(wf_dir.glob("*.yaml")) if wf_dir.exists() else []
    if not workflows:
        return {"status": "disabled", "reason": "no .github/workflows/*.yml present"}
    r = run(["gh", "run", "list", "--limit", "8", "--json", "headSha,name,status,conclusion,url"], timeout=120)
    if r.returncode != 0:
        return {"status": "unavailable", "error": (r.stdout + r.stderr)[-800:]}
    try:
        runs = json.loads(r.stdout)
        head = run(["git", "rev-parse", "HEAD"], timeout=30).stdout.strip()
        if runs and all(x.get("headSha") != head for x in runs):
            return {"status": "stale", "head": head, "runs": runs}
        return {"status": "ok", "runs": runs}
    except Exception as e:
        return {"status": "parse_error", "error": str(e)}


def findings_stats() -> dict:
    data = jload(AIW / "metadata/review-findings.json", {"findings": []})
    rows = [x for x in data.get("findings", []) if isinstance(x, dict)] if isinstance(data, dict) else []
    return {"total": len(rows), "by_status": dict(Counter(x.get("status", "missing") for x in rows)), "by_severity": dict(Counter(x.get("severity", "missing") for x in rows))}


def main() -> int:
    now = datetime.now(TZ)
    day = now.date().isoformat()
    STATE.mkdir(parents=True, exist_ok=True); os.chmod(STATE, 0o700)
    FORMAL.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "profile": "aiw-throughput-watchdog",
        "date": day,
        "generated_at": now.isoformat(),
        "commits": commit_stats(day),
        "source_index": source_stats(),
        "chapter_status": chapter_status(),
        "logs": log_counts(day),
        "cron_outputs": cron_output_stats(day),
        "review_findings": findings_stats(),
        "ci": ci_stats(),
    }
    evidence = STATE / f"{day}.json"
    evidence.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(evidence, 0o600)
    formal = FORMAL / f"{day}-aiw-throughput-watchdog.md"
    ci_failed = [r for r in payload["ci"].get("runs", []) if r.get("conclusion") not in ("", "success", None)] if payload["ci"].get("status") == "ok" else []
    lines = [
        f"# AIW 闭环健康 · {day}",
        f"- status: {'attention-required' if ci_failed else 'completed'}",
        f"- commits_today: {payload['commits']['count']}",
        f"- chapters_touched_today: {payload['commits']['touched_chapters']}",
        f"- logs_today: {payload['logs']}",
        f"- source-index: total={payload['source_index']['total']}, apply_pending={payload['source_index']['apply_pending']}, routes={payload['source_index']['route_status']}",
        f"- findings: {payload['review_findings']}",
        f"- CI: {'failed=' + str(len(ci_failed)) if ci_failed else payload['ci'].get('status')}",
        f"- Obsidian: {formal}",
        f"- Evidence: {evidence}",
        "",
        "## Commit action mix",
        json.dumps(payload["commits"]["actions"], ensure_ascii=False, indent=2),
        "",
        "## Cron output mix",
        json.dumps(payload["cron_outputs"], ensure_ascii=False, indent=2),
        "",
        "## Recent commits",
    ]
    for c in payload["commits"]["recent"][:8]:
        lines.append(f"- `{c['sha']}` {c['subject']} ({len(c.get('files', []))} files)")
    if ci_failed:
        lines += ["", "## CI attention", *[f"- {r.get('name')}: {r.get('conclusion')} {r.get('url')}" for r in ci_failed]]
    body = "\n".join(lines) + "\n"
    formal.write_text(body, encoding="utf-8")
    print(body[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

```

### `aiw-weekly-source-audit.py`

- path：`/Users/gracker/.hermes/scripts/aiw-weekly-source-audit.py`
- sha256-16：`6353b9ce0c66a85f`
- bytes：`13621`

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, os, re, subprocess, sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ=ZoneInfo('Asia/Shanghai')
OB=Path('/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian')
AIW=OB/'Android-Internal-Wiki'
SRC=AIW/'src'
META=AIW/'metadata'
QUEUE=META/'queue.json'
CLIP=Path('/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Clippings')
SUG=AIW/'intake/suggestions.md'
GAPS=AIW/'intake/research-gaps.md'
STATE=Path('/Users/gracker/.hermes/state/aiw-weekly-source-audit')
REPORT_ROOT=OB/'OpenClaw定时任务/AIW自动化流水线'
BOOKS=[
 ('Android 应用稳定性剖析与优化 - Pika','Android 应用稳定性剖析与优化',15,'ch20'),
 ('Android 性能优化 - 赵子健','Android 性能优化',16,'ch21-ch25'),
 ('线上疑难问题该如何排查和跟踪','线上疑难问题该如何排查和跟踪',59,'ch26'),
]
KW=[('crash|anr|stability|稳定|崩溃|oom','ch20'),('startup|启动|apk|安装包','ch21'),('render|渲染|帧|jank|卡顿|surface','ch22'),('memory|内存|heap|native','ch23'),('io|存储|文件|缓存','ch24'),('power|功耗|电量|调度|cpu','ch25'),('trace|监控|排查|observability|日志|埋点','ch26')]

def jload(path:Path, default):
    if not path.exists(): return default
    try: return json.loads(path.read_text(encoding='utf-8'))
    except Exception: return default

def jsave(path:Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    tmp.replace(path)

def append(path:Path, body:str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        if path.exists() and path.stat().st_size: f.write('\n')
        f.write(body.strip()+'\n')

def clean(s:str)->str:
    return re.sub(r'\s+',' ',s).strip()

def chapter(s:str)->str:
    low=s.lower()
    for pat,ch in KW:
        if any(x in low for x in pat.split('|')): return ch
    return 'ch26'

def init_clip_state():
    return {'schema_version':1,'cursor':0,'processed':{},'total_knowledge_points':0,'total_suggestions':0,'total_gaps':0,'last_scan_date':None}

def clip_files():
    if not CLIP.exists(): return []
    files=[]
    for p in sorted(CLIP.glob('*.md'), key=lambda x:x.name):
        name=p.name
        if name.startswith('Android 应用稳定性剖析与优化') or name.startswith('Android 性能优化') or name.startswith('线上疑难问题该如何排查'):
            files.append(p)
    return files

def extract_points(p:Path, max_points:int=4):
    text=p.read_text(encoding='utf-8', errors='ignore')[:12000]
    lines=[]
    for l in text.splitlines():
        s=l.strip(' #-*\t')
        if len(s)>=18 and not s.startswith('http') and not s.startswith('!['):
            lines.append(clean(s))
    if not lines:
        lines=[p.stem]
    pts=[]
    for s in lines[:60]:
        if any(k.lower() in s.lower() for k in ['android','crash','anr','内存','线程','binder','启动','渲染','性能','监控','排查','native','oom','卡顿','缓存','cpu','功耗']):
            pts.append(s[:130])
        if len(pts)>=max_points: break
    return pts or [p.stem]

def run_clippings(args):
    files=clip_files(); state_path=META/'clippings-scan-progress.json'; state=jload(state_path, init_clip_state())
    done=state.setdefault('processed',{})
    start=int(state.get('cursor',0))
    batch=[]; i=start
    while len(batch)<args.max_files and i < len(files):
        if str(files[i]) not in done: batch.append(files[i])
        i+=1
    if not batch and start>=len(files):
        return {'mode':'clippings-reference-scan','status':'ok','completed':True,'scanned':0,'total_files':len(files),'message':'参考资料差异扫描已全部完成'}
    today=args.date; sug=[]; gaps=[]; items=[]; kp=0
    for p in batch:
        pts=extract_points(p); kp+=len(pts); ch=chapter(p.name+' '+' '.join(pts)); target=GAPS if ch in ['ch21','ch22','ch23','ch24','ch25','ch26'] else SUG
        block=f"## [Task14 参考书扫描] {ch} — {today}\n- **类型**：现有章节参考/案例候选（章节冻结：不新增章节）\n- **来源**：[结构参考: Clippings/{p.name}]\n- **建议补充**："+'；'.join(pts[:4])+"\n- **参考书覆盖深度**：结构索引，不搬运原文"
        sug.append(block)
        items.append({'file':p.name,'chapter':ch,'points':len(pts),'target':'suggestions.md','chapter_freeze':True})
        done[str(p)]={'processed_at':datetime.now(TZ).isoformat(),'chapter':ch,'points':len(pts)}
    if not args.dry_run:
        if sug: append(SUG,'\n\n'.join(sug))
        if gaps: append(GAPS,'\n\n'.join(gaps))
        state.update({'cursor':i,'last_scan_date':today,'total_knowledge_points':state.get('total_knowledge_points',0)+kp,'total_suggestions':state.get('total_suggestions',0)+len(sug),'total_gaps':state.get('total_gaps',0)+len(gaps)})
        jsave(state_path,state)
    return {'mode':'clippings-reference-scan','status':'ok','dry_run':args.dry_run,'scanned':len(batch),'knowledge_points':kp,'suggestions':len(sug),'gaps':len(gaps),'progress':f"{min(i,len(files))}/{len(files)}",'items':items}

def extract_meta(text:str, key:str):
    m=re.search(rf'(?mi)^\s*{re.escape(key)}\s*[:：]\s*["\']?([^"\'\n]+)', text)
    return m.group(1).strip() if m else ''

def load_queue():
    q=jload(QUEUE, [])
    return q if isinstance(q,list) else q.get('pending',[])

def save_queue(q): jsave(QUEUE,q)

def save_freshness_log(summary):
    """Preserve the historical freshness log instead of overwriting it with a tiny latest-run object."""
    path = META/'freshness-log.json'
    old = jload(path, {})
    if not isinstance(old, dict):
        old = {'legacy_value': old}
    runs = old.get('runs')
    if not isinstance(runs, list):
        runs = []
    runs.append(summary)
    old.update({
        'last_run_at': summary.get('last_run_at'),
        'last_check': summary.get('last_run_at'),
        'scanned': summary.get('scanned'),
        'risks': summary.get('risks', []),
        'queued': summary.get('queued'),
        'runs': runs[-30:],
    })
    jsave(path, old)

def strip_review_noise(text: str) -> str:
    """Return body assertions only: no YAML, code blocks, or review-note sections."""
    text = re.sub(r'^---\n.*?\n---\n?', '', text, flags=re.S)
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    # Drop common historical review/audit sections that mention forbidden terms as instructions.
    text = re.split(r'(?m)^##\s*(Review|审计|复核|review_notes|质量|风险)', text, maxsplit=1)[0]
    return text


def affirmative_android18_mentions(body: str):
    neg = re.compile(r'(不|不要|不能|禁止|不得|不应|不可|未|无|非|不会).{0,12}(Android\s*(?:1[89]|[2-9][0-9])|API\s*(?:3[8-9]|[4-9][0-9]))|(Android\s*(?:1[89]|[2-9][0-9])|API\s*(?:3[8-9]|[4-9][0-9])).{0,12}(不|不要|禁止|不得|外推|适用)', re.I)
    for m in re.finditer(r'.{0,45}(Android\s*(?:1[89]|[2-9][0-9])|API\s*(?:3[8-9]|[4-9][0-9])|targetSdk\s*3[89]).{0,45}', body, re.I):
        sentence = clean(m.group(0))
        if neg.search(sentence):
            continue
        yield sentence


def freshness_key(target_path: str, rule_id: str, evidence: str) -> str:
    return json.dumps({'target_path': target_path, 'rule_id': rule_id, 'evidence': clean(evidence).lower()}, ensure_ascii=False, sort_keys=True)


def run_freshness(args):
    now=datetime.now(TZ); risks=[]; scanned=0
    files=[p for p in sorted(SRC.rglob('*.md')) if p.name not in {'README.md','SUMMARY.md'}]
    cursor_path=META/'freshness-cursor.json'
    cursor=jload(cursor_path, {'offset':0,'total':len(files),'coverage':{}})
    start=int(cursor.get('offset',0)) % max(1,len(files)) if files else 0
    batch=[]
    for n in range(min(args.scan_limit, len(files))):
        batch.append(files[(start+n) % len(files)])
    for p in batch:
        txt=p.read_text(encoding='utf-8', errors='ignore')[:24000]
        body=strip_review_noise(txt)
        rel=str(p.relative_to(AIW))
        scanned+=1
        for sentence in affirmative_android18_mentions(body):
            risks.append({'path':str(p),'target_path':rel,'severity':'high','rule_id':'above-android17-affirmative-claim','evidence':sentence,'reason':'affirmative higher-than-Android-17 out-of-scope claim','action':'标注超出 AIW 范围或移除正文结论'})
        lv=extract_meta(txt,'last_verified') or extract_meta(txt,'last_source_verified_at') or extract_meta(txt,'verified')
        if lv:
            try:
                d=datetime.fromisoformat(lv.split()[0].replace('/','-'))
                if (now.replace(tzinfo=None)-d).days>90:
                    risks.append({'path':str(p),'target_path':rel,'severity':'medium','rule_id':'stale-source-verification','evidence':lv,'reason':f'last source verification {lv} older than 90 days','action':'重新核验至 Android 17'})
            except Exception: pass
    q=load_queue(); added=[]
    existing=set()
    for x in q:
        if isinstance(x,dict):
            target=x.get('target_path') or x.get('path') or ''
            rule=x.get('rule_id') or x.get('review_issues',[{}])[0].get('rule_id') if isinstance(x.get('review_issues'),list) and x.get('review_issues') else x.get('reason','')
            evidence=x.get('evidence') or x.get('review_issues',[{}])[0].get('evidence') if isinstance(x.get('review_issues'),list) and x.get('review_issues') else x.get('reason','')
            existing.add(freshness_key(str(target), str(rule), str(evidence)))
    for r in risks[:20]:
        item={'section':'freshness','section_title':'AIW 时效性巡检','target_path':r['target_path'],'priority':85 if r['severity']=='high' else 70,'rule_id':r['rule_id'],'evidence':r['evidence'],'reason':'[时效性巡检] '+r['reason'],'material_paths':[r['path']],'review_issues':[{'type':'时效性','rule_id':r['rule_id'],'location':r['target_path'],'evidence':r['evidence'],'detail':r['reason'],'suggestion':r['action']}],'added_by':'hermes-aiw-weekly-source-audit','added_at':now.isoformat(),'status':'pending'}
        key=freshness_key(item['target_path'], item['rule_id'], item['evidence'])
        if key not in existing:
            added.append(item); existing.add(key)
    report=f"# 时效性巡检 · {args.date}\n\n- scanned: {scanned}\n- cursor: {start}->{(start+scanned)%max(1,len(files)) if files else 0}/{len(files)}\n- risks: {len(risks)}\n- queued: {0 if args.dry_run else len(added)}\n\n"+'\n'.join([f"- {x['severity']} {Path(x['path']).name}: {x['reason']} — {x.get('evidence','')[:120]}" for x in risks[:20]])
    report_path=REPORT_ROOT/f'{args.date}-时效性巡检.md'
    if not args.dry_run:
        if added:
            q.extend(added); save_queue(q)
        report_path.parent.mkdir(parents=True, exist_ok=True); report_path.write_text(report,encoding='utf-8')
        next_offset=(start+scanned)%max(1,len(files)) if files else 0
        coverage=cursor.get('coverage',{}) if isinstance(cursor.get('coverage'),dict) else {}
        for p in batch:
            coverage[str(p.relative_to(AIW))]=now.isoformat()
        jsave(cursor_path, {'schema_version':1,'offset':next_offset,'total':len(files),'updated_at':now.isoformat(),'coverage':coverage})
        save_freshness_log({'last_run_at':now.isoformat(),'scanned':scanned,'cursor_start':start,'cursor_next':next_offset,'risks':risks[:200],'queued':len(added)})
    return {'mode':'freshness-check','status':'ok','dry_run':args.dry_run,'scanned':scanned,'cursor_start':start,'risks':len(risks),'queued':0 if args.dry_run else len(added),'report_path':str(report_path),'sample':risks[:5]}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mode',choices=['clippings-reference-scan','freshness-check'],required=True); ap.add_argument('--date',default=datetime.now(TZ).date().isoformat()); ap.add_argument('--dry-run',action='store_true'); ap.add_argument('--max-files',type=int,default=4); ap.add_argument('--scan-limit',type=int,default=80)
    args=ap.parse_args(); STATE.mkdir(parents=True,exist_ok=True); os.chmod(STATE,0o700)
    if not AIW.exists(): raise SystemExit('missing AIW')
    payload=run_clippings(args) if args.mode=='clippings-reference-scan' else run_freshness(args)
    payload.update({'schema_version':1,'profile':'aiw-weekly-source-audit','date':args.date,'generated_at':datetime.now(TZ).isoformat()})
    od=STATE/args.mode; od.mkdir(parents=True,exist_ok=True); os.chmod(od,0o700)
    out=od/(args.date+('-dry' if args.dry_run else '')+'.json'); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8'); os.chmod(out,0o600)
    changed = payload.get('queued', payload.get('gaps', payload.get('suggestions', 0)))
    obs = payload.get('report_path') or str(REPORT_ROOT)
    print(f"# AIW Weekly Source Audit · {args.date}\n- status: {payload['status']}\n- mode: {args.mode}\n- 修改内容: {'未修改正文，仅生成巡检/参考资料候选' if not changed else f'新增/更新 {changed} 条候选或风险项'}\n- 影响范围: scanned={payload.get('scanned')}, risks={payload.get('risks','n/a')}, progress={payload.get('progress','n/a')}\n- Obsidian: {obs}\n- Evidence: {out}\n## 详情\n```json\n{json.dumps({k:payload.get(k) for k in ['items','sample'] if k in payload}, ensure_ascii=False, indent=2)[:1800]}\n```")
    return 0 if payload['status']=='ok' else 3
if __name__=='__main__': raise SystemExit(main())

```

### `aiw-daily-intake.py`

- path：`/Users/gracker/.hermes/scripts/aiw-daily-intake.py`
- sha256-16：`76f7c08596da78d7`
- bytes：`14533`

```python
#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
TZ=ZoneInfo('Asia/Shanghai')
OB=Path('/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian')
AIW=OB/'Android-Internal-Wiki'
DAILY=AIW/'intake/daily-info'
STATE=Path('/Users/gracker/.hermes/state/aiw-daily-intake')
WORK=Path('/Users/gracker/.openclaw/workspace')
TECH=WORK/'tasks/tech-article-aiw-intake/scan_tech_articles_to_aiw.py'
INCR=WORK/'aiw_incremental_scan.py'
KEYWORDS=('android','aosp','androidx','jetpack','perfetto','surfaceflinger','choreographer','binder','zygote','ams','wms','lmkd','art runtime','hwui','skia','camera2','camerax','media3','vulkan','opengl','hal','anr','jank','startup','启动','渲染','内存','功耗','卡顿','流畅','调度','源码','系统服务','输入','音频','视频','定位','权限')
EXCLUDE_TOPICS=('agent workflow','token budget','openrouter','grok','claude code','prompt','workflow budget','ai agent rules','llm','大模型','智能体','知识编译')
STOPWORDS=set('android performance perf source code article deepresearch 技术文章 掘金 每日 论文 精读 源码 性能 优化 分析 实战 机制 架构 系统 应用 开发 研究 资料 官方 users gracker library mobile documents obsidian icloud status completed report review quality intake feed run sort type limit path source target markdown https http juejin post cn com www 原文链接 发布时间'.split())
AGGREGATE_TITLE_PATTERNS=(r'juejin android intake', r'\[掘金android\]\s*\d{4}-\d{2}-\d{2}', r'quality review', r'phase 0', r'status$', r'四层质检报告', r'prompt ·', r'style provenance')

def red(t:str)->str: return t[-3500:]
def run(cmd:list[str], timeout:int=600): return subprocess.run(cmd,cwd=str(WORK),capture_output=True,text=True,timeout=timeout,check=False)
def file_id(p:Path)->str: return hashlib.sha256(str(p).encode()).hexdigest()[:16]
def text(p:Path)->str:
    try: return p.read_text(encoding='utf-8', errors='ignore')
    except Exception: return ''
def is_aggregate_title(title: str) -> bool:
    low = (title or '').lower().strip()
    return any(re.search(pat, low) for pat in AGGREGATE_TITLE_PATTERNS)

def related(s:str)->bool:
    low=s.lower()
    if any(k in low for k in EXCLUDE_TOPICS) and not any(k in low for k in ['android','aosp','androidx','perfetto','surfaceflinger','binder','lmkd','camerax','media3']):
        return False
    return any(k.lower() in low for k in KEYWORDS)

def terms(s:str)->list[str]:
    raw=re.findall(r'[A-Za-z][A-Za-z0-9+.#-]{2,}|[\u4e00-\u9fff]{2,}', s or '')
    out=[]
    for x in raw:
        t=x.lower().strip('-_')
        if len(t)<3 or t in STOPWORDS: continue
        if t.startswith('202'): continue
        out.append(t)
    return list(dict.fromkeys(out))[:24]

def frontmatter(md:str)->dict:
    m=re.match(r'^---\n(.*?)\n---', md, re.S)
    fm={}
    if not m: return fm
    for line in m.group(1).splitlines():
        if ':' in line and not line.lstrip().startswith(('#','-')):
            k,v=line.split(':',1); fm[k.strip()]=v.strip().strip('\"\'')
    return fm

def route_existing_target(title:str, summary:str, chapter_hint:str='')->dict:
    # Conservative router: only routes to an existing chapter when at least two
    # distinctive title/material terms overlap. Low-confidence material remains
    # indexed-only and cannot be consumed by body-apply.
    src_terms=terms(title+' '+summary)
    if not src_terms: return {}
    best=[]
    for p in (AIW/'src').rglob('*.md'):
        if p.name in ('SUMMARY.md','README.md'): continue
        txt=text(p)[:9000]
        fm=frontmatter(txt)
        hay=' '.join([str(p), json.dumps(fm,ensure_ascii=False), txt[:3000]]).lower()
        overlap=[t for t in src_terms if t in hay]
        distinct=[t for t in overlap if t not in {'android','androidx','jetpack','compose','performance'}]
        if len(distinct)<2: continue
        score=len(distinct)*3 + min(4, len(overlap))
        ch=str(fm.get('chapter',''))
        if chapter_hint and ch.startswith(chapter_hint.replace('ch','').lstrip('0')+'.'):
            score+=2
        if '参考资料' in str(p): score-=5
        best.append((score,str(p.relative_to(AIW)),distinct[:8]))
    best.sort(reverse=True,key=lambda x:x[0])
    if best and best[0][0] >= 25:
        return {'target_path':best[0][1], 'route_confidence':best[0][0], 'route_terms':best[0][2], 'route_status':'existing-chapter-routed'}
    return {'route_status':'unrouted-existing-chapter-needed'}
def chapter(s:str)->str:
    low=s.lower()
    for pat,ch in [('surfaceflinger|vsync|choreographer|渲染','ch02'),('inputdispatcher|触摸|输入','ch03'),('lmk|zram|memcg|内存','ch04'),('cpu|eas|调度|freq','ch05'),('f2fs|ext4|i/o|存储','ch06'),('jank|卡顿|fps|流畅','ch07'),('启动|startup','ch08'),('anr|watchdog','ch09'),('battery|doze|功耗','ch11'),('perfetto|trace','ch13')]:
        if any(x in low for x in pat.split('|')): return ch
    return 'ch16'
def append_entries(path:Path, entries:list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        if path.exists() and path.stat().st_size: f.write('\n')
        f.write('\n\n'.join(entries)+'\n')
def deepresearch(args)->dict:
    roots=[OB/'DeepResearch', OB/'deep research']
    found=[]; since=datetime.now(TZ)-timedelta(days=args.since_days)
    for root in roots:
        if not root.exists(): continue
        for p in root.rglob('*.md'):
            if p.stat().st_mtime >= since.timestamp(): found.append(p)
    stfile=STATE/'deepresearch-state.json'; state=json.loads(stfile.read_text()) if stfile.exists() else {'seen':{}}
    entries=[]; items=[]
    for p in sorted(found, key=lambda x:x.stat().st_mtime, reverse=True)[:args.max_files or 50]:
        h=hashlib.sha256(text(p).encode()).hexdigest(); key=str(p)
        if state['seen'].get(key)==h: continue
        content=text(p)
        if not related(content+p.name):
            state['seen'][key]=h; continue
        title=next((l[2:].strip() for l in content.splitlines() if l.startswith('# ')), p.stem)
        if is_aggregate_title(title) or is_aggregate_title(p.stem):
            state['seen'][key]=h
            continue
        summary=re.sub(r'\s+',' ',content.replace('\n',' '))[:220]
        ch=chapter(content+' '+p.name)
        entries.append(f"## [DeepResearch] {title}\n- **来源**：AIW DeepResearch 材料注入\n- **时间**：{datetime.now(TZ).strftime('%Y-%m-%d %H:%M')}\n- **链接**：{p}\n- **摘要**：{summary}\n- **推荐映射章节**：{ch}\n- **内容类型**：DeepResearch 素材\n- **相关标签**：#Android #系统开发")
        items.append({'title':title,'path':str(p),'chapter':ch})
        state['seen'][key]=h
    daily=DAILY/f"{args.date}.md"
    if entries and not args.dry_run:
        append_entries(daily, entries); stfile.parent.mkdir(parents=True, exist_ok=True); stfile.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'mode':'deepresearch','status':'ok','found':len(found),'appended':0 if args.dry_run else len(entries),'candidates':len(entries),'dry_run':args.dry_run,'daily_info':str(daily),'items':items[:10]}
def tech(args)->dict:
    cmd=[sys.executable,str(TECH),'--date',args.date,'--max-files',str(args.max_files)]
    if args.dry_run: cmd.append('--dry-run')
    r=run(cmd)
    try: js=json.loads(r.stdout[r.stdout.find('{'):])
    except Exception: js={}
    return {'mode':'tech-articles','status':'ok' if r.returncode==0 else 'error','returncode':r.returncode,'dry_run':args.dry_run,'daily_info':str(DAILY/f"{args.date}.md"),'report':js,'tail':red(r.stdout+r.stderr)}
def incr(args)->dict:
    if args.dry_run:
        cmd=['find',str(OB),'-name','*.md','-mtime','-1','-not','-path','*/Android-Internal-Wiki/*','-not','-path','*/.trash/*','-not','-path','*/.obsidian/*']
        r=run(cmd,120); files=[x for x in r.stdout.splitlines() if x]
        return {'mode':'incremental','status':'ok' if r.returncode==0 else 'error','dry_run':True,'found':len(files),'sample':files[:10],'daily_info':str(DAILY/f"{args.date}.md")}
    r=run([sys.executable,str(INCR)],600)
    return {'mode':'incremental','status':'ok' if r.returncode==0 else 'error','returncode':r.returncode,'dry_run':False,'daily_info':str(DAILY/f"{args.date}.md"),'tail':red(r.stdout+r.stderr)}

def parse_daily_entries(path:Path)->list[dict]:
    if not path.exists(): return []
    raw=path.read_text(encoding='utf-8', errors='ignore')
    blocks=re.split(r'(?m)^##\s+', raw)
    out=[]
    for b in blocks[1:]:
        title=b.splitlines()[0].strip()
        link=''; summary=''; source=''
        for line in b.splitlines()[1:]:
            if '链接' in line or '来源' in line:
                m=re.search(r'(/Users/[^\n]+|https?://\S+)', line)
                if m and not link: link=m.group(1).strip()
            if '摘要' in line: summary=line.split('：',1)[-1].strip()
            if '来源' in line and not source: source=line.split('：',1)[-1].strip()
        out.append({'title':title,'link':link,'summary':summary,'source':source,'raw':b[:800]})
    return out
def score_entry(e:dict)->dict:
    if is_aggregate_title(e.get('title','')):
        return {'total':0,'reason':'aggregate/status/report artifact, not source material'}
    s=(e.get('title','')+' '+e.get('summary','')+' '+e.get('raw','')).lower()
    if re.search(r'android\s*18|api\s*38|targetsdk\s*3[89]', s):
        return {'total':0,'reason':'out-of-scope higher-than-Android-17'}
    if not related(s):
        return {'total':0,'reason':'not AIW/Android-internals related'}
    rel=5
    depth=5 if any(k in s for k in ['aosp','source','源码','benchmark','perfetto','trace','commit','androidx','developer.android']) else 3
    recency=4
    trust=5 if any(k in s for k in ['android.googlesource','developer.android','aosp','官方','commit','source','androidx']) else 3
    return {'relevance':rel,'depth':depth,'recency':recency,'trust':trust,'total':rel+depth+recency+trust,'reason':'ok'}
def load_json(path:Path, default):
    if not path.exists(): return default
    try: return json.loads(path.read_text(encoding='utf-8'))
    except Exception: return default
def save_json(path:Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(path)
def classify(args)->dict:
    daily=DAILY/f"{args.date}.md"
    entries=parse_daily_entries(daily)
    qpath=AIW/'metadata/queue.json'; spath=AIW/'metadata/source-index.json'
    queue=load_json(qpath, [])
    sidx=load_json(spath, {'files':[]})
    existing={x.get('path') for x in sidx.get('files',[]) if isinstance(x,dict)}
    passed=[]; queued=[]; rejected=[]
    now=datetime.now(TZ).isoformat()
    for e in entries:
        link=e.get('link') or e.get('title')
        if not link or link in existing:
            continue
        sc=score_entry(e)
        if sc['total'] < 12:
            rejected.append({'title':e.get('title'), 'score':sc}); continue
        ch=chapter(e.get('title','')+' '+e.get('summary',''))
        passed.append({'title':e.get('title'), 'link':link, 'chapter':ch, 'score':sc['total']})
        # Chapter creation is frozen. Route only to a high-confidence existing chapter;
        # otherwise keep indexed-only but non-actionable for body-apply.
        route=route_existing_target(e.get('title',''), e.get('summary','')+' '+e.get('raw',''), ch)
        item={'path':link,'title':e.get('title'),'summary':e.get('summary'),'chapter':ch,'processed_at':now,'action':'indexed-only-chapter-freeze','score':sc['total']}
        item.update(route)
        sidx.setdefault('files',[]).append(item)
    if passed and not args.dry_run:
        save_json(spath, sidx)
        raw=daily.read_text(encoding='utf-8') if daily.exists() else ''
        if f'已消费：{args.date}' not in raw:
            daily.write_text(f"> ✅ 已消费：{datetime.now(TZ).strftime('%Y-%m-%d %H:%M')} by hermes-task8\n\n"+raw, encoding='utf-8')
    return {'mode':'classify','status':'ok','dry_run':args.dry_run,'daily_info':str(daily),'entries':len(entries),'passed':len(passed),'queued':0 if args.dry_run else len(passed),'rejected':len(rejected),'passed_items':passed[:10]}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--mode', choices=['deepresearch','tech-articles','incremental','classify'], required=True); ap.add_argument('--date', default=datetime.now(TZ).date().isoformat()); ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--since-days', type=float, default=7); ap.add_argument('--max-files', type=int, default=30)
    args=ap.parse_args(); STATE.mkdir(parents=True, exist_ok=True); os.chmod(STATE,0o700)
    for p in [AIW,DAILY,WORK]:
        if not p.exists(): raise SystemExit(f'missing {p}')
    payload={'deepresearch':deepresearch,'tech-articles':tech,'incremental':incr,'classify':classify}[args.mode](args)
    payload.update({'schema_version':1,'profile':'aiw-daily-intake','generated_at':datetime.now(TZ).isoformat(),'date':args.date})
    outdir=STATE/args.mode; outdir.mkdir(parents=True, exist_ok=True); os.chmod(outdir,0o700)
    out=outdir/(args.date+('-dry' if args.dry_run else '')+'.json'); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8'); os.chmod(out,0o600)
    changed = payload.get('appended', payload.get('queued', payload.get('report',{}).get('appended','n/a')))
    impact = []
    for key in ['found','candidates','entries','passed','rejected']:
        if key in payload: impact.append(f"{key}={payload.get(key)}")
    print(f"# AIW Daily Intake · {args.date}\n- status: {payload.get('status')}\n- mode: {args.mode}\n- 修改内容: {'未修改正文，仅生成/更新素材索引或队列' if changed in [0,'0','n/a',None] else f'新增/更新 {changed} 条素材或队列项'}\n- 影响范围: {', '.join(impact) if impact else 'daily-info / metadata queue/source-index'}\n- Obsidian: {payload.get('daily_info')}\n- Evidence: {out}\n## 详情\n```json\n{json.dumps({k:payload.get(k) for k in ['items','passed_items','sample','report'] if k in payload}, ensure_ascii=False, indent=2)[:1800]}\n```")
    return 0 if payload.get('status')=='ok' else 3
if __name__=='__main__': raise SystemExit(main())

```

### `aiw-daily-intake-deepresearch.py`

- path：`/Users/gracker/.hermes/scripts/aiw-daily-intake-deepresearch.py`
- sha256-16：`43c960747e8c9b5b`
- bytes：`193`

```python
#!/usr/bin/env python3
import subprocess, sys
cmd=[sys.executable,'/Users/gracker/.hermes/scripts/aiw-daily-intake.py','--mode','deepresearch']
raise SystemExit(subprocess.run(cmd).returncode)

```

### `aiw-daily-intake-tech-articles.py`

- path：`/Users/gracker/.hermes/scripts/aiw-daily-intake-tech-articles.py`
- sha256-16：`070e5a726aa6e131`
- bytes：`194`

```python
#!/usr/bin/env python3
import subprocess, sys
cmd=[sys.executable,'/Users/gracker/.hermes/scripts/aiw-daily-intake.py','--mode','tech-articles']
raise SystemExit(subprocess.run(cmd).returncode)

```

### `aiw-daily-intake-incremental.py`

- path：`/Users/gracker/.hermes/scripts/aiw-daily-intake-incremental.py`
- sha256-16：`aafd14ae8256a58c`
- bytes：`192`

```python
#!/usr/bin/env python3
import subprocess, sys
cmd=[sys.executable,'/Users/gracker/.hermes/scripts/aiw-daily-intake.py','--mode','incremental']
raise SystemExit(subprocess.run(cmd).returncode)

```

### `aiw-daily-intake-classify.py`

- path：`/Users/gracker/.hermes/scripts/aiw-daily-intake-classify.py`
- sha256-16：`9dd13adb93538fbf`
- bytes：`189`

```python
#!/usr/bin/env python3
import subprocess, sys
cmd=[sys.executable,'/Users/gracker/.hermes/scripts/aiw-daily-intake.py','--mode','classify']
raise SystemExit(subprocess.run(cmd).returncode)

```

### `aiw-queue-worker.py`

- path：`/Users/gracker/.hermes/scripts/aiw-queue-worker.py`
- sha256-16：`f1062da598951c33`
- bytes：`5740`

```python
#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
TZ=ZoneInfo('Asia/Shanghai')
OB=Path('/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian')
AIW=OB/'Android-Internal-Wiki'
META=AIW/'metadata'
QUEUE=META/'queue.json'
GAPS=AIW/'intake/research-gaps.md'
TOPICS=Path('/Users/gracker/.openclaw/workspace/AutoResearchClaw/state/daily-topics.json')
STATE=Path('/Users/gracker/.hermes/state/aiw-queue-worker')
REPORT_ROOT=OB/'OpenClaw定时任务/AIW自动化流水线'
MODES={'task2b-lite':'Task2B Lite · 高置信局部小修','source-research':'AIW 每日源码调研','task2a':'AIW 知识加工 2A','task2b-main':'Task 2B · 回炉修复'}
CHAPTER_FREEZE=True

def jload(p, default):
    if not p.exists(): return default
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception: return default

def save(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp'); tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); tmp.replace(p)

def text(p:Path)->str:
    try: return p.read_text(encoding='utf-8', errors='ignore')
    except Exception: return ''

def queue_items():
    q=jload(QUEUE, [])
    items=q if isinstance(q,list) else q.get('pending',[])
    return [x for x in items if isinstance(x,dict) and x.get('status','pending')=='pending']

def gaps_items(limit=8):
    if not GAPS.exists(): return []
    raw=GAPS.read_text(encoding='utf-8',errors='ignore')
    blocks=re.split(r'(?m)^##\s+',raw)[1:]
    return [{'title':b.splitlines()[0][:120], 'source':'research-gaps.md'} for b in blocks[:limit]]

def topic_items():
    d=jload(TOPICS,{})
    arr=d if isinstance(d,list) else d.get('topics', d.get('items', []))
    return [x for x in arr if isinstance(x,dict) and x.get('status','pending')=='pending'][:5]

def existing_empty_drafts(limit=8):
    """Return only existing chapter files that are safe for Task2A under chapter freeze."""
    src=AIW/'src'
    out=[]
    if not src.exists(): return out
    for p in sorted(src.rglob('*.md')):
        if p.name.lower() in ('readme.md','summary.md'): continue
        raw=text(p)
        head=raw[:3000].lower()
        if 'status: draft' not in head: continue
        body=raw.split('---',2)[-1] if raw.startswith('---') else raw
        substantive=[l for l in body.splitlines() if l.strip() and not l.lstrip().startswith(('#','>','- **'))]
        if len(substantive) < 15:
            out.append({'path':str(p.relative_to(AIW)),'title':p.stem,'source':'existing-empty-draft','allowed_action':'fill existing draft only; do not create files or edit SUMMARY.md'})
        if len(out)>=limit: break
    return out

def pick(mode):
    if mode in ('task2b-lite','task2b-main'):
        for x in queue_items():
            qtext=json.dumps(x,ensure_ascii=False).lower()
            if 'new-chapter' in qtext or '新增章节' in qtext:
                continue
            if mode=='task2b-lite' and any(k in qtext for k in ['源码路径','api','frontmatter','交叉引用','版本限定','reference','link']): return x
            if mode=='task2b-main' and any(k in qtext for k in ['task6','task9','external','review','rework','needs-rework','pending','回炉','修复']): return x
        safe=[x for x in queue_items() if '新增章节' not in json.dumps(x,ensure_ascii=False).lower()]
        return (safe or [None])[0]
    if mode=='source-research':
        return (topic_items() or gaps_items() or [None])[0]
    if mode=='task2a':
        return (existing_empty_drafts() or [None])[0]
    return (queue_items() or [None])[0]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mode',choices=sorted(MODES),required=True); ap.add_argument('--date',default=datetime.now(TZ).date().isoformat()); ap.add_argument('--dry-run',action='store_true')
    args=ap.parse_args(); STATE.mkdir(parents=True,exist_ok=True); os.chmod(STATE,0o700)
    cand=pick(args.mode)
    status='skipped' if cand is None else 'candidate_ready'
    freeze_constraints=['CHAPTER_FREEZE: do not create new chapter files','do not append src/SUMMARY.md','do not enqueue new-chapter work','Task2A may only fill existing empty draft chapters; if none, stop']
    packet={'schema_version':1,'profile':'aiw-queue-worker','mode':args.mode,'label':MODES[args.mode],'status':status,'dry_run':args.dry_run,'candidate':cand,'constraints':freeze_constraints+['android-17.0.0_r1 baseline','do not promote any version higher than Android 17','do not modify chapter bodies from this gate','human/agent follow-up required for actual content edits'],'generated_at':datetime.now(TZ).isoformat()}
    outdir=STATE/args.mode; outdir.mkdir(parents=True,exist_ok=True); os.chmod(outdir,0o700)
    out=outdir/(args.date+('-dry' if args.dry_run else '')+'.json'); out.write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); os.chmod(out,0o600)
    report=REPORT_ROOT/f"{args.date}-aiw-queue-worker-{args.mode}.md"
    if not args.dry_run:
        report.parent.mkdir(parents=True,exist_ok=True)
        report.write_text(f"# {MODES[args.mode]} · {args.date}\n\n- status: {status}\n- chapter_freeze: {CHAPTER_FREEZE}\n- evidence: `{out}`\n- candidate:\n```json\n{json.dumps(cand,ensure_ascii=False,indent=2) if cand is not None else 'null'}\n```\n\n> Gate only: no chapter body edits were made. Chapter creation is frozen.\n",encoding='utf-8')
    print(f"{MODES[args.mode]}\nstatus: {status}\nchapter_freeze: {CHAPTER_FREEZE}\ndry_run: {args.dry_run}\nreport: {report}\nevidence: {out}")
    return 0
if __name__=='__main__': raise SystemExit(main())

```

### `aiw-review-finalize.py`

- path：`/Users/gracker/.hermes/scripts/aiw-review-finalize.py`
- sha256-16：`0f015f0fed43a8ef`
- bytes：`4140`

```python
#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
TZ=ZoneInfo('Asia/Shanghai')
OB=Path('/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian')
AIW=OB/'Android-Internal-Wiki'
SRC=AIW/'src'
META=AIW/'metadata'
QUEUE=META/'queue.json'
STATE=Path('/Users/gracker/.hermes/state/aiw-review-finalize')
REPORT_ROOT=OB/'OpenClaw定时任务/AIW自动化流水线'
MODES={'reader-final':'AIW · DeepSeek 中文读者终审','task2b-verifier':'Task2B Verifier · 回流复查','deep-tech-review':'AIW · 深度技术Review','draft-review':'AIW · 草稿Review与精修'}

def fm(p:Path):
    t=p.read_text(encoding='utf-8',errors='ignore')[:5000]
    if not t.startswith('---'): return {}
    e=t.find('\n---',3)
    if e<0: return {}
    d={}
    for l in t[3:e].splitlines():
        if ':' in l and not l.lstrip().startswith('-'):
            k,v=l.split(':',1); d[k.strip()]=v.strip().strip('"\'')
    return d

def qitems():
    try: q=json.loads(QUEUE.read_text(encoding='utf-8'))
    except Exception: q=[]
    arr=q if isinstance(q,list) else q.get('pending',[])
    return [x for x in arr if isinstance(x,dict) and x.get('status','pending')=='pending']

def scan_candidates(mode):
    out=[]
    for p in sorted(SRC.rglob('*.md'))[:250]:
        if p.name.lower() in ('readme.md','summary.md'): continue
        d=fm(p); text=json.dumps(d,ensure_ascii=False).lower()
        rel=str(p.relative_to(AIW))
        if mode=='reader-final' and (d.get('status') in ['draft','review','finalized','finalized-v2'] or 'task6' in text): out.append({'path':rel,'reason':'reader-experience candidate','frontmatter':d})
        elif mode=='task2b-verifier' and any(k in text for k in ['fixed','fixed-lite','auto-fixed','task6_pending','ready-for-task6']): out.append({'path':rel,'reason':'verifier回流候选','frontmatter':d})
        elif mode=='draft-review' and (d.get('task6_state') in ['pending','idle','needs-review'] or d.get('status') in ['draft','review']): out.append({'path':rel,'reason':'draft-review候选','frontmatter':d})
        elif mode=='deep-tech-review' and (d.get('task9_state') in ['pending','idle','needs-review'] or d.get('status') in ['draft','review']): out.append({'path':rel,'reason':'deep-tech-review候选','frontmatter':d})
        if len(out)>=8: break
    if not out and mode!='reader-final':
        out=qitems()[:5]
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mode',choices=sorted(MODES),required=True); ap.add_argument('--date',default=datetime.now(TZ).date().isoformat()); ap.add_argument('--dry-run',action='store_true')
    args=ap.parse_args(); STATE.mkdir(parents=True,exist_ok=True); os.chmod(STATE,0o700)
    cands=scan_candidates(args.mode)
    status='candidate_ready' if cands else 'skipped'
    payload={'schema_version':1,'profile':'aiw-review-finalize','mode':args.mode,'label':MODES[args.mode],'status':status,'dry_run':args.dry_run,'candidates':cands,'constraints':['gate/report only','no chapter body edits','android-17.0.0_r1 baseline','versions higher than Android 17 are out of scope'],'generated_at':datetime.now(TZ).isoformat()}
    od=STATE/args.mode; od.mkdir(parents=True,exist_ok=True); os.chmod(od,0o700)
    out=od/(args.date+('-dry' if args.dry_run else '')+'.json'); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); os.chmod(out,0o600)
    report=REPORT_ROOT/f"{args.date}-aiw-review-finalize-{args.mode}.md"
    if not args.dry_run:
        report.parent.mkdir(parents=True,exist_ok=True)
        report.write_text(f"# {MODES[args.mode]} · {args.date}\n\n- status: {status}\n- candidates: {len(cands)}\n- evidence: `{out}`\n\n```json\n{json.dumps(cands[:5],ensure_ascii=False,indent=2)}\n```\n\n> Gate only: no chapter body edits were made.\n",encoding='utf-8')
    print(f"{MODES[args.mode]}\nstatus: {status}\ndry_run: {args.dry_run}\ncandidates: {len(cands)}\nreport: {report}\nevidence: {out}")
    return 0
if __name__=='__main__': raise SystemExit(main())

```

### `feishu-daily-sync-dry-run.py`

- path：`/Users/gracker/.hermes/scripts/feishu-daily-sync-dry-run.py`
- sha256-16：`7e341fe6db428912`
- bytes：`189`

```python
#!/usr/bin/env python3
import subprocess, sys
cmd=[sys.executable,'/Users/gracker/.hermes/scripts/feishu-daily-sync.py','--mode','dry-run']
raise SystemExit(subprocess.run(cmd).returncode)

```

### `feishu-daily-sync-guarded-write.py`

- path：`/Users/gracker/.hermes/scripts/feishu-daily-sync-guarded-write.py`
- sha256-16：`435335f85b4f5672`
- bytes：`195`

```python
#!/usr/bin/env python3
import subprocess, sys
cmd=[sys.executable,'/Users/gracker/.hermes/scripts/feishu-daily-sync.py','--mode','guarded-write']
raise SystemExit(subprocess.run(cmd).returncode)

```

### `feishu-daily-sync-monitor.py`

- path：`/Users/gracker/.hermes/scripts/feishu-daily-sync-monitor.py`
- sha256-16：`36dfdfcc27375cd2`
- bytes：`189`

```python
#!/usr/bin/env python3
import subprocess, sys
cmd=[sys.executable,'/Users/gracker/.hermes/scripts/feishu-daily-sync.py','--mode','monitor']
raise SystemExit(subprocess.run(cmd).returncode)

```

## 7. 验证快照

### 7.1 forbidden Android/version text scan

- scan terms：`Android 18, API38, API 38, android-18, Android18, API37, API 37, SDK 17, sdk17`
- `.hermes/scripts/*.py` violations：
  - none
- `/Users/gracker/.hermes/cron/jobs.json` violations：`{}`

### 7.2 command outputs

#### `$ python3 -m py_compile /Users/gracker/.hermes/scripts/aiw_pipeline_common.py /Users/gracker/.hermes/scripts/aiw-body-apply-context.py /Users/gracker/.hermes/scripts/aiw-review-finalize-context.py /Users/gracker/.hermes/scripts/aiw-polish-context.py /Users/gracker/.hermes/scripts/aiw-git-sync.py /Users/gracker/.hermes/scripts/aiw-throughput-watchdog.py /Users/gracker/.hermes/scripts/aiw-weekly-source-audit.py /Users/gracker/.hermes/scripts/aiw-daily-intake.py /Users/gracker/.hermes/scripts/aiw-queue-worker.py /Users/gracker/.hermes/scripts/aiw-review-finalize.py /Users/gracker/.hermes/scripts/content-topic-plan-collect.py /Users/gracker/.hermes/scripts/paper_pipeline_single_task.py /Users/gracker/.hermes/scripts/content-topic-plan-pipeline-selftest.py /Users/gracker/.hermes/scripts/content-topic-plan-finalize.py /Users/gracker/.hermes/scripts/feishu-daily-sync-dry-run.py /Users/gracker/.hermes/scripts/feishu-daily-sync-guarded-write.py /Users/gracker/.hermes/scripts/feishu-daily-sync-monitor.py`

- returncode：`0`

#### `$ python3 /Users/gracker/.hermes/scripts/aiw-body-apply-context.py`

- returncode：`0`
- parsed/summary output：
```text
{
  "schema_version": 1,
  "profile": "aiw-body-apply",
  "status": "candidate_ready",
  "run_id": "20260809-010737-696a441f",
  "base_sha": "3710072b7097c254a054d6d326c2a5a0bff28040",
  "manifest_path": "/Users/gracker/.hermes/state/aiw-run-manifests/20260809-010737-696a441f.json",
  "formal_report_path": "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AIW自动化流水线/2026-08-09-010737-20260809-010737-696a441f-aiw-body-apply.md"
}
```

#### `$ python3 /Users/gracker/.hermes/scripts/aiw-polish-context.py --mode idle-audit`

- returncode：`0`
- parsed/summary output：
```text
{
  "schema_version": 1,
  "profile": "aiw-polish-idle-audit",
  "mode": "idle-audit",
  "status": "polish_candidate_ready",
  "run_id": "20260809-010737-idle-audit-cc297a84",
  "base_sha": "3710072b7097c254a054d6d326c2a5a0bff28040",
  "manifest_path": "/Users/gracker/.hermes/state/aiw-run-manifests/20260809-010737-idle-audit-cc297a84.json",
  "formal_report_path": "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AIW自动化流水线/2026-08-09-010737-20260809-010737-idle-audit-cc297a84-aiw-polish-idle-audit.md"
}
```

#### `$ python3 /Users/gracker/.hermes/scripts/aiw-review-finalize-context.py`

- returncode：`0`
- parsed/summary output：
```text
{
  "schema_version": 1,
  "profile": "aiw-review-finalize-apply",
  "status": "review_candidate_ready",
  "run_id": "20260809-010738-4ce60df1",
  "base_sha": "3710072b7097c254a054d6d326c2a5a0bff28040",
  "manifest_path": "/Users/gracker/.hermes/state/aiw-run-manifests/20260809-010738-4ce60df1.json",
  "formal_report_path": "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AIW自动化流水线/2026-08-09-010738-20260809-010738-4ce60df1-aiw-review-finalize-apply.md"
}
```

#### `$ python3 /Users/gracker/.hermes/scripts/aiw-weekly-source-audit.py --mode freshness-check --dry-run --scan-limit 5`

- returncode：`0`
- parsed/summary output：
```text
# AIW Weekly Source Audit · 2026-08-09
- status: ok
- mode: freshness-check
- 修改内容: 未修改正文，仅生成巡检/参考资料候选
- 影响范围: scanned=5, risks=0, progress=n/a
- Obsidian: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AIW自动化流水线/2026-08-09-时效性巡检.md
- Evidence: /Users/gracker/.hermes/state/aiw-weekly-source-audit/freshness-check/2026-08-09-dry.json
## 详情
```json
{
  "sample": []
}
```

```

#### `$ python3 /Users/gracker/.hermes/scripts/aiw-throughput-watchdog.py`

- returncode：`0`
- parsed/summary output：
```text
# AIW 闭环健康 · 2026-08-09
- status: completed
- commits_today: 0
- chapters_touched_today: 0
- logs_today: {'deep-review': 0, 'rework': 0, 'audit': 0, 'review': 0}
- source-index: total=212, apply_pending=1, routes={'missing': 24, 'unrouted-existing-chapter-needed': 114, 'existing-chapter-routed': 17, 'quarantined-non-aiw-or-aggregate': 54, 'quarantined-false-route-mismatch': 2, 'quarantined-misroute-3x-rejected': 1}
- findings: {'total': 76, 'by_status': {'wontfix': 1, 'fixed': 56, 'verified': 8, 'open': 11}, 'by_severity': {'P2': 42, 'P1': 24, 'P0': 6, 'P3': 4}}
- CI: disabled
- Obsidian: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AIW自动化流水线/health/2026-08-09-aiw-throughput-watchdog.md
- Evidence: /Users/gracker/.hermes/state/aiw-throughput-watchdog/2026-08-09.json

## Commit action mix
{}

## Cron output mix
{
  "body_apply": {},
  "review_finalize": {},
  "git_sync": {},
  "deep_review": {},
  "rework": {},
  "idle_audit": {},
  "draft_polish": {},
  "daily_intake_deepresearch": {},
  "daily_intake_tech_articles": {},
  "daily_intake_incremental": {},
  "daily_intake_classify": {}
}

## Recent commits


```

#### `$ git -C /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki status --short`

- returncode：`0`

#### `$ git -C /Users/gracker/.openclaw/workspace/Feishu/work-copies/Android-Internal-Wiki status --short`

- returncode：`0`
- stdout：
```text
?? "OpenClaw\345\256\232\346\227\266\344\273\273\345\212\241/Hermes-AIW-\345\256\232\346\227\266\344\273\273\345\212\241\346\265\201\346\260\264\347\272\277\345\256\241\346\237\245.md"

```

## 8. 给复审 Agent 的建议问题

1. manifest gate 是否足以阻止多 lane 同时产生 dirty files 时被同一 git-sync 扫入？是否还需要文件级 lease 或更严格的 pending manifest 选择策略？
2. `allowed_changed_paths` 同时包含 Obsidian 绝对 report path 与 repo 相对路径，path normalization 是否覆盖所有场景？
3. 六条 LLM prompt 是否仍存在可导致无证据晋级、frontmatter-only churn、大段删除、或隐性 git 操作的漏洞？
4. freshness audit 的“高于 Android 17”正则与否定语境过滤是否足够，是否会漏掉中文/英文变体？
5. watchdog 的 productive/no-op 分类是否会被 Hermes 输出模板、prompt echo 或工具日志再次污染？
6. Feishu daily sync 与 AIW GitHub work-copy 的边界是否仍可能误编辑 Obsidian AIW body？
7. 当前 paused legacy jobs 是否应该彻底删除，还是保留为参考？是否有 paused job 被 context_from 或外部 cron 间接依赖？

## 9. 第三方复审结论 · 2026-08-09 01:22 CST

### 9.1 复审结论

本轮以 Android 17 为既定版本上限，只检查约束是否被 active prompt 和脚本一致执行，不讨论约束本身。

复审结果为“部分通过”：六条 LLM lane 的 prompt 已完成明显改进，通用 skill 已移除，正式报告路径已唯一化，CI disabled 也能被识别。manifest 生命周期、运行时调度、watchdog 解析和 freshness 处置仍有阻断性问题。当前配置尚未经过一次修复后的完整 LLM → evidence → manifest → commit → push 实跑。

| 上轮审查项 | 本轮状态 | 复审证据 |
|---|---|---|
| Android 17 版本上限 | 已修复 | 六条 active LLM prompt 均有 Android 17 上限；当前 scripts/jobs 扫描无复审包列出的禁用残留 |
| 通用 skill 重复注入 | 已修复 | 六条 lane 的 `skills=[]`、`skill=None` |
| LLM 自行 Git 提交 | Prompt 已修复 | 六条 prompt 均禁止 `git add/commit/push/pull/rebase/autostash` 和 `aiw-git-sync.py`；尚无修复后实跑证明 agent 全程遵守 |
| LLM 正式报告覆盖 | 已修复 | `unique_report_path()` 包含时间和 `run_id` |
| idle-audit 通过时改章节 | Prompt 已修复 | prompt 要求 `completed-no-change` 且不改章节；尚无修复后运行样本 |
| CI 历史失败误报 | 已修复 | `.github/workflows` 不存在时 watchdog 返回 `disabled` |
| manifest 单轮提交边界 | 未通过 | 当前有 10 个测试遗留 manifest，重复目标会被最旧 manifest 抢占；blocked manifest 仍会继续参与选择 |
| selector/watchdog 同一资格口径 | 部分修复 | source-index 共用函数，但 watchdog 不读取目标正文，也不统计 queue；router 阈值与 eligibility 阈值仍不一致 |
| watchdog 响应分类 | 未通过 | JSON 固定字段 `blocked_reason` 会让所有结构化成功响应都被归为 `blocked` |
| watchdog 正文/frontmatter 分类 | 未通过 | frontmatter-only 的模拟 diff 被归为 `body-change` |
| freshness 游标、去重、正文解析 | 部分修复 | cursor、稳定 key、YAML/code/review noise 过滤已实现；否定语境和处置 lane 仍有误判 |
| finalized 证据门 | Prompt 已修复，gate 未修复 | prompt 已写明条件；`check-metadata.py` 与 git-sync 尚未强制校验 finding/source evidence |
| intake 域过滤与路由 | 部分修复 | 已增加排除项和保守路由；`route >=25` 与 apply `>=30` 仍制造不可消费记录 |
| paused legacy 依赖 | 可清理 | active job 没有 `context_from`，LaunchAgents/LaunchDaemons/OpenClaw 配置未发现对旧 job 名称的引用 |

### 9.2 今天运行前需要处理的三项问题

#### P0-1：复审包的验证命令留下 10 个可参与提交的 manifest

`/Users/gracker/.hermes/state/aiw-run-manifests` 当前有 10 个 manifest，状态全部为 `created`。它们来自 00:27 至 01:07 的修复验证，不对应真实 LLM 修改。

重复情况：

- `34-display-mode-refresh-rate-selection.md`：同一 `base_sha=3710072b7...` 下有 5 个 manifest。
- `5.29-android17-gpu-dvfs-headroom-power-advisor.md`：同一 `base_sha` 下有 2 个 manifest。
- 其余 3 个来自 idle-audit 验证。

对当前 `select_manifest_for_paths()` 做只读调用，DisplayMode 的模拟脏路径会选中最早的 `20260809-002721-696a441f`，GPU DVFS 会选中 `20260809-002936-a3a63d2c`。真实早班任务的 run_id 会被凌晨验证 run_id 覆盖。

更严重的情况发生在 HEAD 推进以后：旧 manifest 先命中路径，再因 `base_sha` 不符返回 `head-mismatch`。`mark_manifest(..., "blocked")` 写入 blocked 后，`load_manifests()` 仍会加载它；后续 sync 会重复选中同一 blocked manifest，形成永久阻塞。

处理建议：

1. 今天 `07:15` 首轮 body 运行前，把这 10 个验证 manifest 标成 `superseded-test` 或移出 active manifest 目录；不要让验证状态进入正式提交选择。
2. pre-run 增加 `--dry-run`，dry-run 不创建 manifest、不写 recent-path lease。
3. `load_manifests()` 只加载已经收到 agent 成功结果的 `agent-completed` manifest。`created`、`blocked`、`completed-no-change`、`needs-human-review`、`expired`、`superseded` 均不得参与自动提交。
4. agent 完成后写独立 result/evidence JSON，包含 `run_id`、`base_sha`、`target_sha_before`、`target_sha_after`、`actual_changed_paths`。git-sync 按 run_id 读取，不再通过“哪个 manifest 的路径碰巧命中”推断归属。
5. 同一目标同一 base 只允许一个 lease。新 lease 创建时必须显式 supersede 旧的 `created` lease，并记录原因。

#### P0-2：现有时刻表与 clean-worktree 合同互相阻塞

pre-run 脚本现在遇到任意脏文件就返回 `dirty-worktree-before-run`。git-sync 仍只在每小时 `:55` 执行，因此同一小时的第二条 LLM lane 很容易被第一条挡住：

| 时段 | 第一条 lane | 第二条 lane | 当前结果 |
|---|---|---|---|
| 偶数小时 | review-finalize `:05` | deep-review/idle-audit `:35` | 第一条改文件后，第二条在 sync 前看到 dirty worktree |
| 奇数小时 | body-apply `:15` | rework/draft-polish `:35` | body 有改动时，polish 在 sync 前被 blocked |
| 每小时 | 两条 lane 结束后 | git-sync `:55` | sync 发生得太晚，无法满足第二条 lane 的 clean-start 条件 |

这会让四条 polish lane 的吞吐下降，并产生大量“任务 ok、pre-run blocked”。

处理建议：每条 LLM lane 完成后立即触发独立事务 gate，下一条 lane 只能在 commit/push 或明确 no-change 后开始。若希望保留并行度，每轮使用独立 Git worktree，再由串行 gate 验证和合入。只增加文件 lease 不能解决共享 worktree 已经脏的问题。

#### P0-3：09:30 Feishu dry-run 会删除当前两份未提交复审文档

Feishu 与 Obsidian AIW 正文的路径隔离已经成立：`feishu-daily-sync.py` 使用 GitHub work-copy，不写 Obsidian AIW 正文。

但 `refresh_aiw_work_copy()` 每次 preflight 都会在 work-copy 执行：

```text
git checkout master
git reset --hard origin/master
git clean -fd
```

`dry-run` 也会先执行这个 preflight。当前两份复审文档都是 work-copy 内的 untracked 文件，`2026-08-09 09:30` 的 `feishu-daily-sync-dry-run` 会被 `git clean -fd` 删除。

处理建议：耐久审查文档移到 work-copy 外，例如 `Feishu/reviews/` 或 Obsidian 的正式报告目录。work-copy 应明确标为可重建缓存。若必须保存在仓库路径内，需要在刷新前提交，或为明确目录配置排除规则；不要依靠未提交文件长期保存。

### 9.3 manifest gate 仍只检查路径，没有检查产物质量

`aiw-git-sync.py` 已经把正文提交收窄到 manifest 的 `expected_changed_paths`，并增加“最多 3 个 src 文件”和“单文件删除不超过 120 行”的阈值。这部分比旧实现安全。

当前 gate 仍有以下缺口：

- 只要脏路径与 `expected_changed_paths` 有交集即可提交；formal report、evidence、finding 更新并非必需产物。
- 没有验证 agent result JSON、`source_evidence`、finding 状态或状态迁移。
- 没有在提交前强制运行 `check-metadata.py --files ...`、`check-summary-links.py` 和 `git diff --check`。这些检查仍由 prompt 要求 agent 自报。
- manifest 的 `finding_ids` 创建时通常为空，git-sync 也不从 result/evidence 回填。提交无法稳定反查 finding。
- `expected_changed_paths` 表示“最多可改的路径”，没有区分 `required_paths` 与 `optional_paths`。

建议把 manifest 拆成：

- `required_changed_paths`：candidate_ready 且有正文修改时必须出现的目标路径和 result/evidence。
- `optional_changed_paths`：对应的 queue、source-index、finding、log。
- `forbidden_changed_paths`：SUMMARY、新章节和任何未声明路径。
- `verification_commands` 与机器可读返回码。
- `result_sha256`、`evidence_sha256`、`target_sha_before/after`。

只有 result 状态为 `changed` 或允许提交的 `metadata-only`，且必需产物、验证命令、状态迁移全部通过时才能 stage。

### 9.4 watchdog 的两个分类器仍然不可用

#### 响应分类

六条 prompt 要求最终 JSON 固定包含 `blocked_reason`。watchdog 在解析具体状态前执行：

```python
if "dirty-worktree-before-run" in txt or "blocked" in low:
    return "blocked"
```

因此字段名本身就会命中。使用当前函数做无文件写入模拟，结果如下：

| Response | 当前分类 |
|---|---|
| `status=changed, blocked_reason=""` | `blocked` |
| `status=completed-no-change, blocked_reason=""` | `blocked` |
| `status=candidate_ready, blocked_reason=""` | `blocked` |
| `status=blocked, blocked_reason="dirty"` | `blocked` |

修复方式：提取 `## Response` 后的 JSON，调用 `json.loads()`，只按 `payload["status"]` 分类。JSON 解析失败单列 `response-parse-error`，不要退回关键词猜测。

#### 正文/frontmatter 分类

`classify_changed_markdown()` 在每个 diff hunk 开始时把 `in_fm=False`，又不读取 hunk 的原文件行号。一个只修改 `status:` 的 frontmatter diff 会被计为 `body-change`。只读模拟已经复现：frontmatter-only 和真实正文改动都返回 `body-change`。

修复方式：读取变更前后的完整 Markdown，分别解析 frontmatter 与 body，再比较两个结构；也可以根据 hunk 原文件行号与 frontmatter 结束行定位，不能依靠 diff 中是否再次出现 `---`。

watchdog 的 Git 提交统计还应只统计 `[hermes-aiw]`，并对已提交 diff 做正文/frontmatter 分类。当前 `commit_stats()` 会把当天所有人工提交也计入 Hermes 产出，正文分类只检查未提交文件。

### 9.5 selector 与 watchdog 仍未使用同一份待办集合

`source_index_eligibility()` 已成为共享函数，但调用方式不同：

- body selector 传入 `chapter_text`，可以判断 material marker 是否已经存在于正文。
- watchdog 不读取目标章节，调用时没有 `chapter_text`，无法排除“正文已应用、metadata 尚未终态”的记录。
- body 同时读取 queue 与 source-index；watchdog 的 `apply_pending` 只统计 source-index。

当前实数：watchdog 显示 `apply_pending=1`；body 的只读 selector 返回 2 个 candidate。两者其实指向同一个 DisplayMode 目标和同一个 DeepResearch 材料，只是分别来自 queue 与 source-index。body 没有按 `(target_path, material_path)` 去重。

路由阈值也不一致：`route_existing_target()` 在 score `>=25` 时写入 `existing-chapter-routed`，共享 eligibility 要求 `route_confidence>=30`。当前 source-index 有 9 条因此被标成 routed，却永久不可 apply：6 条 score 25，3 条 score 28。样本仍包含 Agent Plugins、opencli 日志、科研 Agent 验收等误路由。

建议：

1. 建立一个 `collect_apply_candidates()`，同时读取 queue/source-index、解析目标正文、按 material ID 去重；body 与 watchdog 都调用它。
2. router 与 consumer 共用同一个阈值常量。25 至 29 分只能写 `route_status=provisional` 或 quarantine，不能标 `existing-chapter-routed`。
3. watchdog 同时报告 `eligible_unique_candidates`、`rejected_by_reason` 和最老 pending age。
4. 对历史 9 条低分 routed 记录做一次迁移，不能只修以后新增的数据。

### 9.6 freshness 修复只完成了一半

已生效的改动：

- 扫描使用持久 cursor，不再固定取排序后的前 80 章。
- 排除 README、SUMMARY、YAML frontmatter、代码块和常见 review/audit 段。
- 新记录带 `target_path`、`rule_id`、`evidence`，去重 key 不再包含时间。
- dry-run 不推进 cursor，也不修改 AIW repo。

仍需修正：

1. 否定过滤把“否定某个 Android 18 行为”误当成“本文不讨论 Android 18”。例如 `Android 18 不再允许旧接口` 是高版本事实结论，当前返回空，不会入队。
2. 过滤窗口只有 12 个字符。`不要把 Android 17 的结论外推到 Android 18` 当前反而会被识别为肯定风险。
3. `该接口并不支持旧模式，但 Android 18 引入替代实现` 因前半句的“不”被整句过滤，漏掉后半句肯定结论。
4. `API level 38`、`Build.VERSION_CODES.API_38` 等形式不在当前正则内。
5. 每章只读取前 24000 字符。当前仓库的 Android 18/API 38 命中暂未出现在 24000 字符以后，但长章节后续新增内容仍可能漏检。

否定过滤应只识别明确的范围声明模板，例如“本文不讨论/不纳入/不外推到/不依赖 [高版本]”，不能因为高版本附近出现普通否定词就跳过整句。

处置 lane 也有问题。新 freshness 项把目标章节本身写进 `material_paths`，body-apply 会把同一章节当成“外部材料”再编译回自身，甚至可能生成自引用 source marker。freshness finding 应进入 deep-review/rework，由 agent 针对 `rule_id + evidence` 核验；它不属于材料注入任务。

历史 queue 仍有 5 条 pending freshness：4 条缺 `target_path`，1 条指向 README。新代码不会迁移或关闭它们，body 也不会处理。修复脚本需要一次性迁移旧记录，并把不可处理项标成 superseded/rejected。

### 9.7 `last_source_verified_at` 尚未形成一致字段合同

prompt 已要求把普通审计与来源核验分开，但仓库和脚本还没有完成字段迁移：

- 当前 624 个章节含 `last_verified`，没有章节含 `last_source_verified_at` 或 `last_audited_at`。
- `quality_flags()` 只认 `last_verified`，新增 `last_source_verified_at` 后仍会报 missing。
- freshness 先读 `last_verified`，再读 `last_source_verified_at`。若 agent 保留旧字段并新增新字段，旧日期会优先命中，造成重复 stale 风险。
- `check-metadata.py` 的 optional field 仍只有 `last_verified`、confidence、sources，且 warning 不阻止 finalized。

需要先确定兼容策略：迁移期优先读取 `last_source_verified_at`，缺失时回退 `last_verified`；`last_audited_at` 存外部 ledger 或作为独立字段。status 为 ready-for-review/finalized 时，metadata gate 应强制验证 source evidence 与核验时间，不能只给 warning。

### 9.8 Git sync 的其他可靠性问题

- `aiw-git-sync.py:308-313` 带有一次性修复逻辑：只要 `metadata/freshness-log.json` 的 diff 同时出现 `last_run_at` 和 `priority_actions`，就执行 `git checkout --` 丢弃本地修改。这个条件可能命中后续正常编辑。一次性数据修复完成后应删除该分支，自动提交器不应静默丢弃文件。
- push 失败时已经生成本地 commit，但 manifest 仍是 `created`。下一次 worktree 干净时，脚本只 `pull --ff-only`，不会主动重试 push。建议增加 `committed-local` 状态并在无脏文件时先检查 `@{upstream}..HEAD`，重试 push。
- path 命中只验证“当前脏路径是 manifest 的子集”，没有验证 target 的修改后 SHA 与 agent result 是否一致。相同目标的另一轮改动仍可能被错误 manifest 接管。

### 9.9 Prompt 仍需补的两条

六条 prompt 已经比旧版短，约束也更明确。再补两条即可：

```text
完成修改后，必须把最终 result JSON 写入 pre-run 指定的 result_path，并原子更新 manifest 状态为 agent-completed；仅在聊天 Response 输出 JSON 不算完成。result.run_id 必须与 manifest.run_id 完全一致。

若本轮没有修改仓库文件，必须把 manifest 标成 completed-no-change 或 superseded，并释放 target lease。不得留下 created manifest 等待以后某次同路径修改。
```

`result_path` 应由 pre-run JSON 明确给出，不能让 agent 自行猜 evidence 文件路径。

### 9.10 paused legacy jobs

本轮检查没有发现 active job 的 `context_from` 依赖，也没有在 LaunchAgents、LaunchDaemons 或 OpenClaw 配置中发现对 10 个 paused AIW worker/finalize 名称的引用。它们可以从 `jobs.json` 归档，脚本可保留到一个单独 legacy 目录作为参考。

保留 paused job 本身不会触发 LLM，但会增加任务统计和后续维护歧义。归档前保存一份 job JSON 快照即可。

### 9.11 修复后验收用例

建议先在隔离 Git worktree 中跑下面的测试，再恢复自动提交：

1. 连续执行三次 pre-run dry-run，active manifest 数保持不变。
2. 同一 target 已有 `created` manifest 时，第二次 lease 被拒绝或原子 supersede；不能同时保留两个 active lease。
3. `blocked`、`completed-no-change`、`needs-human-review` manifest 不参与 git-sync 选择。
4. 08:05 的 review 修改完成并提交后，08:35 的 polish 能在 clean HEAD 上开始；不能依靠 08:55 才统一提交。
5. 成功 Response 带空 `blocked_reason` 时，watchdog 分别识别 changed、completed-no-change、no-candidate；无一被归为 blocked。
6. 只改 frontmatter 的 diff 被统计为 frontmatter-only，正文改动被统计为 body-change。
7. `Android 18 不再允许旧接口` 被识别为越界事实；`本文不把 Android 17 结论外推到 Android 18` 被识别为范围声明。
8. freshness finding 进入 review/rework，不进入 body material apply，也不会生成章节自引用 marker。
9. router 写 `existing-chapter-routed` 的最小分数与 consumer 完全一致；历史 25/28 分记录完成迁移。
10. agent 未写 result/evidence、run_id 不匹配或本地 gate 失败时，git-sync 拒绝 stage。
11. 模拟 push 失败后，manifest 进入 committed-local；下一次 sync 会重试 push，不会遗忘本地提交。
12. Feishu dry-run 刷新 work-copy 后，耐久审查文档仍存在于 work-copy 外的固定位置。

修完后连续观察 48 小时，至少覆盖 body、review-finalize、四条 polish、两轮 git-sync 和一次 watchdog。通过标准应同时满足：无 stale manifest、无错误 run_id 归属、无第二 lane 饥饿、watchdog 分类与真实 Response 一致、每个提交都能反查 result/evidence 和本地 gate。

---

## 10. 2026-08-09 最终复核：修复落地、真实运行与剩余风险

复核时间：2026-08-09 03:05 CST

### 10.1 约束说明

Android 17 是项目负责人明确设定的产品边界，本次复核将其作为硬约束执行，不再把该边界本身列为疑点。流水线需要做的是准确识别并阻止高于 Android 17 的正文结论，同时不能把“本文不外推到 Android 18”之类范围声明误报为越界事实。

### 10.2 最终结论

修复前不能用“正文已经足够优秀”解释低产出。过去两天确实存在大量正文改动，但流水线同时存在候选重复、低置信误路由、状态往返、只看路径不看内容、无结果事务、watchdog 误分类和审计产物不可读等问题。这些问题会造成“任务持续运行，但有效收益不稳定”。

修复并完成真实闭环后，当前判断为：

- 流水线已经从“prompt 自报成功”升级为“manifest lease → result/evidence → 本地 gate → 内容 SHA → 独立 commit/push”的可验证事务。
- 正文并未达到饱和。最新质量基线仍为 `not-saturated`，635 个章节中 399 个处于 finalized/verified，165 个仍命中至少一项出版风险启发式。
- open finding 已从 11 个降到 2 个，P0 已通过真实 rework 闭环关闭；剩余 2 个均为真实 P1，不做指标清零。
- DeepSeek 凭证与 `deepseek-v4-pro / deepseek` provider 已实际调用成功，并已加入每日中文质量复审 lane。
- 需要继续观察 48 小时的自然调度，重点是任务重叠、模型偶发失败、push 重试和候选长期轮转；当前没有需要停掉整条流水线的 P0 基础设施问题。

### 10.3 过去两天是否有实质正文改动

统计范围：2026-08-07 00:00 至 2026-08-09 00:00，限定提交标题以 `[hermes-aiw]` 开头。

| 日期 | Hermes commits | 变更文件 | 涉及章节 | commit-path 正文改动 | commit-path frontmatter-only |
|---|---:|---:|---:|---:|---:|
| 2026-08-07 | 17 | 55 | 18 | 17 | 8 |
| 2026-08-08 | 17 | 51 | 19 | 14 | 10 |

再按两天起止 commit 做净比较：

- `src` 净变更章节：32 个。
- 正文净变化：23 个章节。
- 仅 frontmatter 净变化：9 个章节。
- 正文净行数：新增 147 行、删除 685 行。
- 正文字符净变化：`-1737`。
- 最大单章变化是 `1.46-android17-staged-install-mechanism.md`，正文约 `-8687` 字符，属于删除无来源/不可靠内容后的实质收缩，而不是简单润色。

因此答案是“有实质改动”，不能概括成只刷状态或时间戳。但质量并不均匀：

1. 23/32 个净变更章节确实改了正文。
2. 仍有 9/32 个章节最终只留下 frontmatter 变化。
3. 同一章节在 review/rework/finalize 之间多次往返，commit 数高于独立内容收益。
4. 对三个近期章节的抽样复读显示：`1.17 IPC 全景`与 `5.29 GPU DVFS`整体较强；`1.46 Staged Install`虽删除了大量无来源内容，仍需要补足正向状态机讲解、multi-package 状态和可观测方法。

所以此前的弱变化感知主要来自任务选择与闭环设计问题，而不是全库已经没有值得改的内容。

### 10.4 已落地的基础设施修复

#### 事务与并发

- manifest 默认状态改为 `leased`，带 90 分钟 lease 和 `target_sha_before`。
- 同一目标存在活跃 lease 时拒绝第二轮任务。
- dry-run 不创建 manifest，不推进任务状态。
- agent 必须写正式报告、evidence JSON、result JSON，并调用 `aiw-run-complete.py`。
- 只有 `agent-completed` manifest 会进入 Git sync。
- `completed-no-change`、`blocked`、`needs-human-review` 都是终态，不会污染下一次提交。
- Git sync 除了核对路径，还核对每个脏文件、正式报告和 evidence 的 SHA-256；放行后内容发生变化会拒绝提交。

#### 提交与 gate

- source 章节改动在 release 和 commit 前都执行：
  - `git diff --check`
  - `scripts/check-summary-links.py`
  - `scripts/check-metadata.py --files <本轮章节>`
- ready-for-review/finalized/verified 被本轮修改时，强制要求来源核验日期、confidence 和非空 sources。
- push 失败时记录 `committed-local`，下轮优先重试 push。
- manifest commit message 不再被遗留 pending message 覆盖。
- 删除了 Git sync 中静默 checkout `freshness-log.json` 的一次性分支。

#### selector、intake 与 freshness

- queue/source-index 候选按 `(target_path, material_path)` 去重。
- selector 与 watchdog 共用 eligibility，目标正文已应用的材料不再重复计数。
- 路由生产和消费共用最低置信度 30。
- 9 条历史 25/28 分 routed 记录已迁移为 `provisional-low-confidence`。
- 5 条旧 freshness pending 已迁移为 `superseded`，freshness 风险只进入 `review-findings.json`，不再把章节自身当 material 回灌。
- Android 高版本检测覆盖 Android 18+、API level 38+、API_LEVEL、VERSION_CODES、targetSdk 和 SDK_INT 形式。
- 明确区分肯定性越界结论与“不讨论/不外推/无高版本结论”等范围声明。
- 扫描读取完整正文，不再只截前 24000 字符。

#### 选择优先级与长期轮转

- rework 明确 P0 高于 P1；真实 dry-run 已优先选中 ART GC P0，而不是 NFC P1。
- “最近处理过”只认 completed/pushed/needs-human-review 等终态 manifest，不再把仅创建 context 的失败任务当成已完成。
- polish frontmatter 改用 YAML 解析，避免把 `sources:` 列表误读为空字符串。
- idle audit 现在会优先发现 finalized 但缺 last_verified/confidence/sources 的真实出版债务。
- DeepSeek 中文复审候选改为 ready-for-review 优先、长段落优先；未审章节优先，全部审过后按最久未审轮转，不再永久循环前 40 章。

#### watchdog 与飞书 work-copy

- watchdog 只统计 `[hermes-aiw]` commits。
- 已提交 Markdown 按完整 frontmatter/body 前后内容分类。
- 中文 Git 路径关闭 `core.quotepath`，不会漏计章节。
- cron Response 解析 JSON 的 `status`，不会因为字段名 `blocked_reason` 把成功结果归为 blocked。
- top-level 明确输出 `committed_change_types`。
- Feishu work-copy clean 使用 `git clean -fd -e OpenClaw定时任务/`，dry-run 验证不会删除两份耐久审查文档。

#### 产物质量

- 完成门禁新增 Markdown 真实换行检查。若报告把换行写成字面量 `\\n`，run 会被拒绝。
- 本次真实 P0 rework 首次产出的单行日志已修复为 29 行 Markdown，正式报告修复为 33 行 Markdown。
- agent 写入正文的“本轮 rework / finding id”流水线措辞已改为读者视角的来源边界说明。

### 10.5 新增与调整的 cron

| Job | ID | Schedule | Mode / Model | 目的 |
|---|---|---|---|---|
| `aiw-git-sync` | `5fa9d7fe9e87` | `25,55 7-23 * * *` | no-agent | 每个 LLM lane 后及时提交，减少跨 lane 脏树冲突 |
| `aiw-git-sync-morning-intake` | `d6f28d5a2e78` | `55 5,6 * * *` | no-agent | 在 07:15 body 前发布 05:00-06:30 intake/metadata |
| `aiw-pipeline-selftest` | `2837b3bb3243` | `50 6 * * *` | no-agent | 每日回归 manifest、dry-run、watchdog、freshness、job contract、Feishu 保护 |
| `aiw-quality-baseline` | `a57d1850625a` | `5 7 * * *` | no-agent | 每日判断质量饱和度、正文/元数据比例和中文复审候选 |
| `aiw-chinese-quality-deepseek` | `ea4c4334aa21` | `35 7 * * *` | `deepseek-v4-pro / deepseek` | 中文表达与教学可读性复审，不改技术事实 |

当前以 `aiw-` 开头的 scheduled jobs：18；其中 LLM 7、no-agent 11。paused legacy jobs：10。

### 10.6 DeepSeek 凭证与真实闭环结果

凭证检查：

- `hermes auth list` 存在 deepseek manual credential。
- 最小真实请求返回 `DEEPSEEK_OK`。
- provider：`deepseek`。
- model：`deepseek-v4-pro`。

真实运行 1：

- run：`20260809-023547-deepseek-cn-ba11ff82e2e98db8`
- target：`1.17 IPC 全景`
- result：`completed-no-change`
- 结论：全文中文表达已经较好，没有为了产出而强行改写。
- manifest 正确释放为 no-change，Git 保持干净。

真实运行 2：

- run：`20260809-024124-deepseek-cn-c8489bdf96f06584`
- target：`2.31 HDR 显示管线与色彩管理性能`
- result：`changed`
- 实际改动：1 行，修复“给出一个列表滑动开销比例”的编辑残余；frontmatter、技术事实、代码、数字、来源均未改。
- gate：metadata 1/1、SUMMARY 661 links、diff-check 全部通过。
- manifest：`pushed`。
- commit：`aee22f5b7`，已推送 origin/master。

这两个结果同时说明新 lane 的 no-change 与 changed 都能被正确区分，不再以聊天文字猜测是否成功。

### 10.7 GPT-5.5 P0 rework 真实闭环

- run：`20260809-024950-rework-501b4554`
- target：`10.10 ART GC 碎片化、Compaction 与性能诊断`
- finding：`finding-64a9f0019062`（P0）
- 修改：章节从 `needs-review/source-rework-required` 推进到 `ready-for-review`；补充读者视角的 Android 17 来源边界；finding 关闭为 fixed；未直接 finalized。
- gate：metadata、SUMMARY、diff-check 全部通过。
- release：包含 repo 路径 SHA 与外部 artifact SHA。
- manifest：`pushed`。
- commit：`dc7b1f78b`，已推送 origin/master。
- 后续修复不可读日志的 commit：`b52c5705c`，已推送。

### 10.8 当前量化快照

最新 watchdog：

- commits_today：4。
- chapters_touched_today：3。
- committed change types：body-change 2、frontmatter-only 1。
- source-index：212 条，唯一 apply candidate 为 DisplayMode 正文材料。
- route status：existing-chapter-routed 8、provisional-low-confidence 9。
- manifests：13；pushed 2、completed-no-change 1、superseded-test 10；active 0。
- cron output：DeepSeek `completed-no-change=1`、productive/completed=1；rework productive/completed=1；git-sync productive/completed=3。
- CI：仓库没有 `.github/workflows`，状态仍为 disabled。

最新质量基线：

- status：`not-saturated`。
- chapters：635。
- publication-state risk：165/399。
- open findings：P1 2，P0 0。
- 最近 7 天 Hermes 章节提交中，正文变更比例约 0.882。

### 10.9 当前剩余问题

#### 内容 P1

1. `finding-c8aaa40d5450`：NFC 支付章节缺 NFC 一手材料，曾误用音频材料并出现未验证 API/性能数字；当前 rework selector 下一项已经能正确选中它。
2. `finding-887a0875daf5`：`ch16-aosp/参考资料.md` 两个 P1 placeholder 缺可追溯来源；source_paths 匹配已修复，后续 rework 能找到该章节。

#### 历史元数据债务

全量 `check-metadata.py` 当前 622 个 canonical 章节中 590 通过、32 失败。失败主要是历史 finalized/ready-for-review 缺 sources、核验日期或 confidence。新 gate 不要求一次性修改全库，但任何被新 lane 触碰的章节都必须先补齐，否则不能重新发布。idle-audit 已能优先选择这些债务。

#### 质量基线不是事实判决器

165/399 是启发式风险数，不等于 165 篇技术错误。它混合了缺 metadata、待验证标记、观察入口不足、长段落与少量 AI 风格词。用途是排序，不应用作自动降级或自动删除正文的唯一依据。

#### 外部脚本版本化

Hermes 脚本位于 `~/.hermes/scripts`，不在 AIW Git 仓库中。当前已记录 SHA-256 并有每日 selftest，但长期建议把 AIW pipeline scripts 单独纳入版本库或定期快照，否则机器级脚本变更仍难以做 PR review 和 rollback。

### 10.10 复核结论与建议优先级

当前可以恢复并继续定时运行，不需要因基础设施缺陷整体暂停。优先级如下：

1. 先让 rework 依次消化剩余 2 个 P1，不要让 draft polish 抢占修复资源。
2. 连续观察 48 小时，确认每个 scheduled lane 都产生 terminal manifest，且 Git 工作树在下一 lane 前恢复 clean。
3. 观察 DeepSeek 长期轮转是否覆盖未审章节；不以“每天必须改一篇”作为成功标准，允许有证据的 completed-no-change。
4. 逐步消化 32 个历史 metadata 失败项；优先 finalized，再处理 ready-for-review。
5. 将 `~/.hermes/scripts` 纳入可审查的版本化快照。
6. 48 小时后以 watchdog 的 `body-change/frontmatter-only/no-change`、open finding 变化和重复 target 比例做第二次复盘，而不是只看 commit 数。

综合评级：基础设施从“不建议继续自动提交”提升为“可以运行，但必须继续观测”；内容质量不是饱和状态，当前流水线已经能对真实 P0、中文小修和 no-change 三种结果做出不同且可审计的处理。

## 11. 第二轮复审：P1 闭环、假成功修复与最终质量快照（2026-08-09 04:06 CST）

本节是在 §10 之后继续用真实 Hermes cron 运行验证所得，不是只读脚本或 prompt 后给出的静态建议。Android 平台上限继续固定为 Android 17 / API 37 / `android-17.0.0_r1`；该约束是项目既定边界，不作为质疑项。

### 11.1 第二轮结论

§10 之后的修复方向总体正确，但继续真实运行又发现了三个会降低有效吞吐的问题：

1. YAML `sources:` 数组改用 `yaml.safe_load` 后，未加引号的日期会成为 Python `date`，导致 pre-run JSON 无法序列化。
2. manifest 的 `target_sha_before` 是“UTF-8 文本 SHA-256 前 16 位”，agent 却可能误用 `git hash-object`。cron 外层显示 succeeded，内部 result 实际 blocked，形成假成功。
3. freshness 和读者正文 gate 对明确的版本排除句、技术语境中的“本轮……流水线”存在误报。

以上三项均已修复并加入 selftest；随后同一条真实 idle-audit 已成功完成并由独立 Git gate 推送。当前综合评级可以进一步提升为：**流水线可以继续自动运行，事务闭环已被真实 changed / metadata-only / completed-no-change / blocked 四种路径验证；剩余问题以历史内容债务和机器级脚本版本化为主。**

### 11.2 剩余两个 P1 已全部闭环

#### NFC 支付章节

- finding：`finding-c8aaa40d5450`
- run：`20260809-031354-rework-bf063b3b`
- target：`src/part5-app/ch24-io-network/22-nfc-contactless-payment-performance.md`
- 核验材料：AOSP NFC module `android-17.0.0_r1`、Android 17/API 37 NFC API diff、HCE 与 `HostApduService` 官方文档。
- 修复：补齐 claim→source 映射，移除错误材料边界，关闭 P1，推进为 ready-for-review；没有越级 finalized。
- 正文中 agent 写入的“本次 rework”流程话术已改为读者视角的证据边界。
- commit：`007d612eb`，已推送。

#### ch16 AOSP 参考资料

- finding：`finding-887a0875daf5`
- run：`20260809-032251-rework-8204f5b6`
- target：`src/part4-system/ch16-aosp/参考资料.md`
- 复核结果：两个曾经无来源的 placeholder 已在当前正文中移除，旧 finding 属于状态滞后；本轮关闭同一稳定 id，没有重新制造占位内容。
- 正文历史 deep-review/lane 叙述已改为稳定的读者来源规则。
- commit：`f530a4a1a`，已推送。

当前 `metadata/review-findings.json`：76 条历史 finding，`fixed=59`、`verified=16`、`wontfix=1`，**open=0，P0/P1 open=0**。

### 11.3 来源债务 lane 的真实验证

#### 结构化 YAML 解析

- `aiw-review-finalize-context.py` 与 `aiw-body-apply-context.py` 不再用逐行字符串解析 frontmatter；`sources:` 数组能保留为数组。
- YAML 自动解析出的 `date/datetime` 统一转为 ISO 字符串，避免 pre-run JSON 序列化失败。
- selftest 同时覆盖 structured sources 与未加引号日期。

#### Review/Finalize 真实运行

- run：`20260809-033332-e9819ae3`
- target：`8.17 Kotlin Flow 背压、操作符链与响应式性能边界`
- 结果：`metadata-only`，不改正文；逐项核对现有引用后补齐 structured sources、核验日期和 confidence，并 finalized。
- commit：`b78e23532`，已推送。

#### Idle Audit 的假成功与修复后重跑

第一次 run `20260809-033912-idle-audit-0e177ec8`：

- cron 外层：succeeded。
- result：blocked。
- 原因：agent 用 Git blob hash `1bc218...` 比对 manifest 的文本 SHA-256 `791a9d...`。
- 工作树保持干净，没有错误吸收任何改动；这说明安全门有效，但状态展示会误导。

修复：

- 七条 LLM job prompt 全部明确 `target.hash_contract`：读取 UTF-8 文本，计算 SHA-256，取前 16 位小写十六进制；禁止使用 `git hash-object`。
- 四类 context 输出同时新增 `sha256_utf8_16` 与 `hash_contract`。
- selftest 检查七条 prompt 与所有 dry-run context 是否带完整算法。

第二次 run `20260809-034735-idle-audit-0e177ec8`：

- target：`26.3 性能指标采集与上报`
- 结果：`metadata-only`，正文 0 行变化。
- 证据：18 条 AOSP/AndroidX/Android Developers/Firebase/LeakCanary 来源，evidence JSON 给出逐项 `supports`。
- 补齐：`last_verified`、`last_source_verified_at`、`confidence`、structured `sources` 和 audit 记录。
- gate：metadata 1/1、SUMMARY 661 links、diff-check 全通过。
- commit：`8d757fa41`，已推送。

这两轮证明缺元数据章节不会被无条件“抄 URL 晋级”：有足够现有一手证据时只补结构化元数据；证据不足时 prompt 要求创建 finding 并降级。

### 11.4 读者正文与 freshness 误报修复

#### 读者正文

- 所有 writer/review/rework/idle/DeepSeek context 已明确：正文不得出现 run、round、lane、agent、prompt、pipeline、rework、定时任务执行过程。
- `aiw-run-complete.py` 会在提交前只扫描 frontmatter 之后的读者正文并拒绝流程话术。
- 初版正则会把技术句“本轮可消费状态……完整的显示流水线”误判为内部流程；现已收紧为“本次/本轮”紧邻真实任务词才命中。
- 全库扫描后，仅有两处历史正文是真正的 `本次/本轮 deep-review`；均已改成“本文的证据范围/本文只覆盖”的读者表达。
- commit：`743f5f4db`，已推送。
- 当前全库 reader-facing pipeline prose 扫描：0 命中。

#### Android 高版本 freshness

- 原扫描把“本文未使用 Android 18/API 38 之后的主线实现反推 Android 17 行为”误判为肯定性越界结论，并对同一行 Android/API 两种写法重复报两次。
- shared detector 已增加“未使用/未引入/不采用/不依赖”和“不反推”范围排除；同一源码行只生成一个 finding。
- selftest 新增该原句和一行双版本写法 fixture。
- 最终 dry-run：scanned=80，risks=0。

### 11.5 “内容饱和还是任务没效果”的最终判断

结论：**不是内容已经饱和。过去弱改动主要由旧 selector、来源门禁、状态闭环和 prompt 边界不清造成；修复后流水线已经能持续找到真实正文、证据和中文可读性问题。**

最终 watchdog（2026-08-09）：

- commits_today：9。
- chapters_touched_today：9。
- body-change：6。
- frontmatter-only：3。
- 当前 active manifest：0。
- 当日真实正文改动覆盖 ART GC、NFC、ch16 来源规则、HDR 中文表达，以及两篇历史流程话术清理。

最近 7 天 Hermes 提交统计：

- 106 个 `[hermes-aiw]` commits。
- 423 次章节变更事件。
- body-change：372。
- frontmatter-only：51。
- 正文变化比例：0.879。

这组数据不能证明每个正文修改都正确，但能排除“过去一周基本只刷 metadata、任务完全没有实质作用”的判断。现在真正需要解决的是**质量债务排序和逐条证据核验**，不是继续增加无差别改写 prompt。

### 11.6 最新质量债务拆解

`check-metadata.py`：622 个 canonical 章节，593 通过，29 失败，1 warning。

29 个失败项中：

- 2 篇 finalized 只缺来源核验日期。
- 27 篇缺 structured `sources`。
- 27 篇里有 25 篇正文已经包含 6—37 条 URL，大多为官方/AOSP；它们主要是“逐条复核后结构化”的债务，不能机械复制 URL。
- 仅以下 2 篇正文 URL 为 0，必须做真实来源复审或降级，不能自动补 metadata：
  - `src/part1-fundamentals/ch04-memory/4.04-AppFlow与Android-17-LMKD兼容性方案.md`
  - `src/part5-app/ch23-memory-practice/23.24-android-17-ai-推理加速与-neuralnetworks-hal-优化.md`

唯一 warning 是 `5.24-android17-binder-sz4m-kernel-buffer-pool-priority-set-called-dedup.md` 缺日期/confidence/sources；其当前状态未触发 finalized 硬失败。

最新质量基线：

- chapters：635。
- finalized/verified：400。
- publication-state 任意风险：164/400。
- 证据或待验证债务：62。
- 长段落编辑风险：114。
- flag 明细：missing-sources 23、missing-source-verification-date 2、pending-markers 37、dense-long-paragraphs 114。
- open finding：0。
- status：`not-saturated`。
- 精确原因：`62 publication-state chapters still have source/date/confidence or pending-verification debt`。

164 仍是启发式候选数量，不等于 164 篇技术错误；其中 114 篇只是每篇至少有 3 个大于 650 字符的长段落。37 个“待验证/TODO”也必须逐句区分真实占位与教学中对未决条件的说明。

### 11.7 当前任务群与 prompt 状态

- scheduled AIW jobs：18。
- LLM jobs：7。
- no-agent jobs：11。
- 六条技术 lane：`gpt-5.5 / openai-codex`。
- 中文 lane：`deepseek-v4-pro / deepseek`。
- 七条 LLM job 都包含 manifest/result/evidence 完成合同、reader-facing 正文合同和明确文本哈希合同。

DeepSeek 中文 lane 从每天 1 次调整为每天 4 次：

```cron
0 9,13,17,21 * * *
```

原因：当前 114 篇 finalized/verified 章节触发长段落启发式；中文 lane 只处理可读性，不改技术事实，适合独立轮转。仍允许 completed-no-change，不要求每天强行改四篇。

### 11.8 最终回归快照

- 所有 `~/.hermes/scripts/aiw-*.py`：`py_compile` 通过。
- `aiw-pipeline-selftest.py`：exit 0，静默通过。
- 七条 pre-run dry-run：合法 JSON，不创建 manifest。
- active manifests：0。
- `scripts/check-summary-links.py`：661 links，0 duplicate warning。
- `scripts/check-metadata.py`：593/622 通过；29 个已知历史债务导致预期 exit 1。
- freshness dry-run：80 files，0 risks。
- reader-facing pipeline prose：全库 0 命中。
- Git 提交快照：`master == origin/master == 743f5f4dbe58932ef4e1702dc75a9222b4ae3e4b`；04:04 回归时工作树 clean。04:06 另一个并发资讯任务新建了未跟踪的 `intake/daily-info/2026-08-09.md`，不属于本次复审，未被吸收或提交；已提交 HEAD 仍与 origin 对齐。

### 11.9 仍建议后续 agent 执行的事项

1. 让 idle-audit 处理 23 篇 finalized 缺 sources 和 2 篇 finalized 缺日期；每篇必须产生 claim→source evidence，不能批量抄 URL。
2. 让 review/finalize 优先处理 ready-for-review 的 4 篇缺 sources；两篇零 URL 章节若找不到一手证据，应创建稳定 finding 并降级。
3. 逐句审计 37 篇 pending-marker 命中；只清真实占位，不删除合理的“待设备/项目实测”边界。
4. 观察 DeepSeek 每天 4 次的 changed/no-change/needs-human-review 比例；若 7 天后大多数为 no-change，可把长段阈值从字符数改为句法/层次密度，而不是继续加频率。
5. 将 `~/.hermes/scripts` 做版本化快照或迁入独立仓库。目前有 SHA、自测和运行证据，但没有 PR 级 rollback。

最终判断：**当前任务群已从“任务看似很多但真实闭环不可靠”修到“能产生实质正文改动、能识别 metadata-only、能安全 no-change、也能在冲突时阻断”的状态。AIW 仍未饱和，下一阶段应消化 62 个证据/待验证候选和 114 个编辑候选，而不是再增加泛化的大改写 agent。**

## 12. 第二轮补充复审：修复后真实运行、48 小时改动与剩余阻断项

复审时间：`2026-08-09 05:16 CST`。

本节是在第 11 节之后继续做的独立复核，依据当前 `jobs.json`、当前 `~/.hermes/scripts/`、真实 run manifest/result/evidence、AIW Git 历史和正文抽样。依照本轮要求，以下新增发现只形成 review 建议，没有继续修改 Hermes job、prompt、脚本或 AIW 正文。

### 12.1 Android 17 是验收前提，不是问题项

Android 17 / API 37 / `android-17.0.0_r1` 是用户明确设定的发布边界。本节不质疑该约束，也不把“只写到 Android 17”列为风险。

对应验收标准是：

- 正文可以讲 Android 17 以及更早版本的演进、兼容与差异。
- 高于 Android 17 的资料不能进入正文结论。
- Android 17 平台结论应尽量锚定 `android-17.0.0_r1`；内核结论使用任务群约定的 Android 17 common-kernel 标签。
- `SDK 17` 不能代替“Android 17 / API 37”，但这是命名准确性要求，不是对 Android 17 上限本身的质疑。

### 12.2 第二轮总判断

结论比第 11 节更严格：

1. **修复后的 manifest、lease、hash、result/evidence、git-sync 闭环已经真实生效。**零正文 URL 的高风险章节没有被机械晋级；脏工作树和错误 hash 会阻断；metadata-only 与正文修改可以区分。
2. **过去 48 小时确实有实质正文改动，不能说 Hermes 只是在刷状态。**但“有 body diff”不等于“正文已经正确”，原始 body-change 比例不能单独作为质量证明。
3. **AIW 明显没有内容饱和。**除 24 个 canonical metadata 失败外，抽样直接发现 finalized 章节仍向读者展示成段的已知错误草稿、虚构公式和虚构性能数字。
4. **当前任务群还不能判定为完全闭环。**最新 selftest 已重新变红；idle-audit 当前候选会在生成 JSON context 时崩溃；选择器仍会被源码 `TODO` 和合理证据边界误导；finalize 选择器已经开始选择 preface，而不是 canonical 技术章节。
5. **最高优先级不是再增加 agent 数量，而是修正“事实正确性 > 大纲保护”的优先级，并补齐确定性 gate。**如果这条不改，agent 会继续采用“保留错稿，再在后面写勘误”的伪闭环。

因此，当前状态应描述为：**执行闭环基本建立，内容闭环仍有阻断级缺口。**

### 12.3 当前回归快照

| 检查项 | 当前结果 | 解释 |
|---|---:|---|
| AIW HEAD | `64bd2cef01930d7977c59a2986dfdb08ec168ec4` | 最新提交为 Compose Canvas idle-audit |
| AIW 工作树 | clean | 本轮诊断未留下正文或 metadata 改动 |
| `check-summary-links.py` | 通过 | 661 个本地链接，0 duplicate warning |
| `check-metadata.py` | 失败 | canonical 622 篇中 598 通过、24 失败、1 warning |
| metadata 失败拆解 | 22 + 2 | 22 篇 finalized 缺 structured sources；2 篇缺来源核验日期 |
| quality baseline | `not-saturated` | 635 个 `src/**/*.md`；403 篇 finalized/verified；164 篇命中至少一个启发式风险 |
| quality flag | 22 / 2 / 37 / 114 | missing-sources / missing-date / pending-markers / dense-long-paragraphs |
| open finding | 1 个 P2 | `AIW-23.24-20260809-P2-nnapi-source-boundary` |
| active manifest | 0 | 没有遗留运行租约 |
| throughput watchdog | completed | 当日 16 commits、14 篇 touched；7 body-change、7 frontmatter-only |
| `py_compile` | 通过 | Python 语法层面无错误 |
| pipeline selftest | **失败** | `aiw-polish-idle-audit-context.py` 无法 JSON 序列化 YAML `date` |
| 正确入口 freshness dry-run | 通过 | 直接调用主脚本扫描 80 篇、risks=0，Git 仍 clean |
| wrapper 的 `--dry-run` | **不安全** | wrapper 丢弃参数，实际执行了有写入副作用的正式扫描；本轮产生的 3 个文件改动已精确恢复至 HEAD |

注意：quality baseline 的 635 篇包含 `preface` / `appendix` 等 13 个辅助页面，而 metadata gate 的正式口径是 622 个 canonical 章节。当前 403 篇 publication-state 风险统计恰好都落在 canonical 章节内，所以 164/403 本身没有因此改变；但 selector 使用 635 全量范围，已经影响实际选题。

### 12.4 过去 48 小时有没有实质改动

按 `git log --since="2 days ago"` 重新计算：

- `[hermes-aiw]` commits：50。
- 章节变更事件：63。
- body-change：38。
- frontmatter-only：25。
- body-change 比例：`38 / 63 = 0.603`。

这说明过去两天不是只改 metadata；但 60.3% 也说明状态/来源结构整理占了相当比例。该窗口跨越旧流水线和本次修复后的新流水线，不能把 50 个提交全部视为对当前 prompt 的验收样本。

#### 明确属于实质正文改动的样本

| commit | 章节 | diff | 实际价值 |
|---|---|---:|---|
| `a1564913d` | 1.46 Staged Install | `+11/-573` | 删除整段已知错误历史提纲；这是正确的“删除错稿”处理范式 |
| `5f88f67e9` | 23.24 NNAPI/LiteRT | `+105/-403` | 删除不存在 API、伪性能表、伪 Java 服务、无依据 GC/DVFS 保证；补 NNAPI 废弃与迁移边界；保持 ready-for-review 并开 P2 |
| `007d612eb` | 24.22 NFC | `+36/-13` | 根据 finding 做源码边界修复，不只是改状态 |
| `dc7b1f78b` | 10.10 ART GC | `+10/-5` | 修正 Region/compaction 等实质技术问题 |
| `f530a4a1a` | ch16 参考资料 | `+14/-12` | 清理来源占位和 Android 版本边界 |
| `daaa19af2` | 13.13 Perfetto CPU/DVFS | `+34/-18` | 对已有结论做来源/边界调整 |

#### body-change 不能直接等同质量提升的反例

- `8f1b599d2` 对 Binder priority inheritance 做了 `+10/-10`，但 finalized 正文仍保留大量“历史原文标记”“请以后文为准”和 Review-finalize 过程话术。
- 若只在错误大纲前增加“该区域不作为结论”，Git 会把它记成 body-change，但读者仍会看到全部错误内容。
- 过去两天部分旧式 `review-findings` / `deep-review` commit 一次触及两个章节；这不适合作为当前“单 run 单 target”合同的正向证据。
- 25 个 frontmatter-only 事件中，一部分是有价值的来源结构化和最终状态闭环；它们不应冒充正文提升，也不应被简单视为无效。

#### 修复后真实 run 的结果分布

本轮直接复核/运行的 finalize 与 idle 样本共 7 个：

- review-finalize：5 个。
  - 1 个大幅正文修复：23.24 NNAPI/LiteRT。
  - 4 个 metadata-only：Kotlin Flow、Android Auto/AAOS、内存泄漏治理、DEX 体积优化；每个都读取了现有正文来源并生成 claim→source evidence。
- idle-audit：2 个。
  - 26.3 性能指标采集与上报。
  - 22.38 Compose Canvas。
  - 两者均为 metadata-only，正文已有足够来源，补齐 structured sources、核验日期、evidence 与 audit 记录。

另有 3 个 rework 正文样本和 1 个 DeepSeek 中文样本。说明 lane 分工已经能表现出：rework 处理 finding、finalize 决定晋级或降级、idle 处理 publication-state 债务、DeepSeek 只做中文小修。

### 12.5 正向验证：零 URL 章节没有被机械晋级

`20260809-043007-52ce263c` 选中：

`src/part5-app/ch23-memory-practice/23.24-android-17-ai-推理加速与-neuralnetworks-hal-优化.md`

该章运行前正文 URL 为 0，且包含大量无依据断言。实际结果：

- 没有 finalized，仍为 `ready-for-review`。
- confidence 从 high 降到 medium-low。
- 删除或改写不存在的 `ANeuralNetworksMemory_createWithAlignment`、伪 `ANeuralNetworksService`、固定性能/功耗百分比、直接 NPU DVFS、ART GC suppression 等断言。
- 新增稳定 P2 finding：`AIW-23.24-20260809-P2-nnapi-source-boundary`。
- 人工复核又发现 agent 首轮漏掉 NNAPI 自 Android 15 起废弃的官方边界；补齐该事实、迁移指南和 16 KB 页面来源后才完成本 run。

这个样本证明来源 gate 已经阻止“零 URL + 自动补 metadata + finalized”。同时也证明单次 LLM 技术审查仍会漏掉重要 lifecycle warning；prompt 中新增的 deprecated/migration/availability 检查是必要的，不能撤回。

### 12.6 阻断级内容问题：已知错误 outline 仍在 finalized 正文中

这是第二轮复审最重要的新发现。

#### 5.26 JobScheduler CPU quota

文件：`src/part1-fundamentals/ch05-cpu-power/05.26-android17-jobscheduler-service-cpu-quota.md`

当前问题：

- frontmatter 同时出现 `status: ready-for-review` 和 `status: finalized`；PyYAML 静默采用后一个值。
- 正文明确承认 outline 中的五维评分、CPU 配额公式、300%/30% 比例、WorkManager 优先级映射、AI 调度和跨设备调度没有 `android-17.0.0_r1` 依据。
- 但这 400 多行错误内容仍完整出现在读者正文中，直到第 454 行 `outline-end` 后才开始真实源码结论。
- 可见错误包括虚构权重公式、动态 CPU quota 伪代码、前台 `+300%`、后台 `30%`、2 分钟固定上限、伪 WorkManager `setPriority()` 映射、固定性能阈值、伪厂商接口和无来源性能提升数字。

在发布文档中加一句“下面内容不要引用”不能把错误内容变正确。它仍会被搜索、摘要、RAG、读者跳读和后续 agent 当作正文事实消费。

#### 6.1 DataStore 多进程

文件：`src/part1-fundamentals/ch06-storage/6.1-androidx-datastore--ipc-源码级验证-draft.md`

后半章的 1.2.1 源码分析质量较好，也明确逐项纠正了旧说法；但前半章仍向读者展示：

- 无复现实验的 25%—50% 性能提升和 20%—30% 内存下降。
- DataStore 与 MemoryLimiter/ZRAM 自动集成。
- 虚构专属 ftrace 事件。
- Binder 600KB 与 DataStore 批量写入的错误关联。
- “Android 17 特有优化”等错误版本归属。

文章标题和 status 均指向可发布内容，读者不应被要求自行判断哪一半可以相信。

#### 其余同类候选

- `6.19-linux-6.10-内存碎片整理机制.md`：finalized，仍保留无实验依据的历史百分比，只用 warning 隔离。
- `1.48-android17-binder-priority-inheritance.md`：finalized，正文仍包含多处历史占位说明和 Review-finalize 过程文本。
- `5.29-android17-gpu-dvfs-headroom-power-advisor.md`：ready-for-review，已有“受保护大纲需收窄”提示；晋级前应直接重写错误段。

#### 正确处理范例

`1.46-android17-staged-install-mechanism.md` 的 `a1564913d` 已删除 573 行完整错稿，只留下简短追溯摘要和可引用正文。这比“保留全部错稿 + 后文勘误”更符合发布目标，应作为 rework/finalize 的模板。

#### 必须加入所有技术 lane 的 prompt 规则

建议原文加入：

```text
事实准确性高于 outline/anchor/历史结构保护。outline 只保护主题覆盖，不保护原句、伪代码、数字或错误结论。
若 outline-start/outline-end 区域含已确认的虚构 API、虚构数字、错误状态机、无来源公式或与后文冲突的旧稿，必须删除或重写错误内容；不得仅添加“历史大纲/不作为结论/请以后文为准”的免责声明后保留。
finalized/verified 的整篇读者可见正文只能有一套有效结论，不允许“前文错误、后文纠正”并存。
```

#### 必须加入 completion gate 的规则

对准备进入 finalized/verified 的全文做阻断扫描，至少拒绝：

- `受保护大纲`
- `历史错误提纲` / `历史原文标记`
- `不作为技术结论`
- `可引用正文从……开始`
- `为了兼容 Hermes/OpenClaw/流水线`
- `Review-finalize` / `draft-polish` / `deep-review`
- 同一篇正文中同时出现“该断言错误/无依据”和被完整保留的原始断言块

不能只扫描本次新增 diff；只要本次把章节晋级为 publication-state，就要扫描修改后的全文。

### 12.7 阻断级运行回归：polish context 无法序列化 YAML 日期

最新 selftest 真实失败：

```text
aiw-polish-idle-audit-context.py dry-run failed:
TypeError: Object of type date is not JSON serializable
when serializing dict item 'last_deepseek_cn_review_at'
when serializing dict item 'frontmatter'
when serializing dict item 'target'
```

当前 idle dry-run 选中 `13.14 Perfetto DataGrid 与 Jank CUJ 标准库`。它的 YAML 为：

```yaml
last_deepseek_cn_review_at: 2026-07-11
```

`yaml.safe_load` 会把未加引号的 ISO 日期解析成 `datetime.date`，而 `json.dumps` 不支持该对象。四个 polish wrapper 共用 `aiw-polish-context.py`，因此根因是共享的，不应只在 idle wrapper 里补丁。

建议：

1. 在 `aiw_pipeline_common.py` 提供递归 `json_safe()`，将 `date` / `datetime` 转为 `isoformat()`，Path 转字符串，dict/list 递归处理。
2. `aiw-polish-context.py`、`aiw-review-finalize-context.py`、`aiw-body-apply-context.py` 和其他会把 PyYAML 对象写入 JSON 的 context 全部统一调用。
3. 不建议只把某一个 frontmatter 日期加引号；仓库里有大量未加引号的日期，下一个候选还会复发。
4. selftest 增加含未加引号日期、时间戳、嵌套 source date 的 fixture，并要求所有 active context dry-run 都能输出合法 JSON。

优先级：**先于下一次 idle-audit cron 修复。**当前 cron 为 `35 10,14,18,22 * * *`，不修会在命中此类候选时直接失败。

### 12.8 P1：freshness wrapper 丢弃全部 CLI 参数

文件：`~/.hermes/scripts/aiw-weekly-source-audit-freshness-check.py`

当前代码把调用固定为：

```python
cmd=[sys.executable, '.../aiw-weekly-source-audit.py', '--mode', 'freshness-check']
```

它没有转发 `sys.argv[1:]`。因此：

- `wrapper --dry-run` 实际是正式运行，会更新 `freshness-cursor.json`、`freshness-log.json` 和 `review-findings.json`。
- `wrapper --help` 也会执行一次正式扫描，而不是显示帮助。
- 本轮正是通过这个行为复现了副作用；产生的 3 个 repo 文件改动已用 HEAD 精确恢复，最终 Git clean。
- 直接调用主脚本 `aiw-weekly-source-audit.py --mode freshness-check --dry-run` 才是真正无 repo 写入的 dry-run。

建议 wrapper 改为转发参数：

```python
cmd = [
    sys.executable,
    '/Users/gracker/.hermes/scripts/aiw-weekly-source-audit.py',
    '--mode',
    'freshness-check',
    *sys.argv[1:],
]
```

selftest 必须在运行 wrapper dry-run 前后比较 AIW `git status --porcelain`、cursor/log/findings hash，确认完全不变。

### 12.9 P1：selector 没有限定 canonical 章节

当前：

- metadata gate 明确定义 622 个 canonical 章节，排除 `src/preface` 和 `src/appendix`。
- `aiw-review-finalize-context.py`、`aiw-polish-context.py`、`aiw-body-apply-context.py`、quality baseline 都直接遍历 `SRC.rglob("*.md")`。
- 最新 review-finalize dry-run 已选中 `src/preface/how-to-use.md`，materials 为空；该页面只是读者指南，不应由技术 finalize lane 因缺 sources 而优先处理。

这会带来三类浪费：

1. 技术 LLM 为前言硬加不必要的技术来源。
2. source gate 与 selector 的范围不一致，形成反复 blocked/no-change。
3. 质量基线显示 635 篇，而正式 metadata 验收显示 622 篇，运营数字不统一。

建议把 `check-metadata.py` 的 canonical 目录定义抽到共享模块，所有 selector、baseline、metadata gate 统一调用 `iter_canonical_chapters()`。preface/appendix 如需审查，应使用独立 reader/editorial lane，不与技术证据债务混排。

### 12.10 P1：pending-marker 与 thin-source-marking 正在制造错误选题

当前 publication-state 中有 37 篇命中 pending marker。逐行重新分类，共约 54 个命中：

| 类型 | 命中行数 | 是否应直接算发布债务 |
|---|---:|---|
| 上游源码 `TODO/TBD/FIXME` 的客观说明 | 20 | 否；这是版本边界证据，不是 AIW 占位 |
| 合理的证据边界/实验假设语言 | 15 | 通常否；应保留诚实限定 |
| 显式 `[待验证]` 标签 | 7 | 需要逐项审核，不能一概删除 |
| 标题含“待验证” | 7 | 需要区分 checklist 与未完成正文 |
| 编辑过程或真正待补内容 | 5 | 是，应修正文或移出读者正文 |

最新 idle selector 选择 `13.14 Perfetto DataGrid 与 Jank CUJ 标准库`，原因是：

- 正文引用上游源码注释中的 `TODO(devianb)`，被判为 `pending-verification-marker`。
- frontmatter 已有 8 条结构化来源，但正文没有至少 2 个 `[来源:]` 魔法标签，被判为 `thin-source-marking`。
- 该章 `last_idle_audit_at` 是 2026-08-08，仍被次日再次选中。

这三个信号合在一起会持续制造无价值审计。

建议：

1. 将 pending 分为 `editorial-placeholder`、`declared-evidence-boundary`、`upstream-source-todo` 三类；只有第一类直接计入 publication debt。
2. 上游源码 TODO 如果同时给出精确 ref/path，并明确“不能外推”，应当是正向证据边界，不应触发 rework。
3. 不再用正文 `[来源:]` 出现次数作为来源充分性的必要条件。优先检查 structured sources、关键 claim 的 source_evidence、正文可定位链接/源码路径及二者映射。
4. cooldown 除 manifest 外，还要读取 `last_idle_audit_at`、`last_review_finalize_at` 等 frontmatter 日期；迁移前没有 manifest 的历史运行也应生效。
5. quality baseline 报告同时输出三类 marker 的完整 path 列表，不能只给聚合数字 37。

### 12.11 P1：YAML 重复键和畸形 sources 尚未进入 gate

对 635 个 `src/**/*.md` 的 top-level frontmatter 做只读扫描，发现 32 个文件至少有一个重复 key。

重点问题：

- `5.26 JobScheduler CPU quota`：`status` 同时为 ready-for-review 和 finalized，实际解析静默采用 finalized。
- `20.25 thread leak`：同样存在冲突 status。
- `13.26 Android Trace API`：`pipeline_stage` 同时为 task6_pending 和 ready-to-publish。
- `4.1 memory overview` 与 `5.12 thermal` 等文件把 `sources:` 写成空值，后续多条 `path:` 顶格重复；PyYAML 最终只保留最后一个 `path`，而 `sources` 仍为空。这正是部分 metadata missing-sources 的直接成因。

当前 `check-metadata.py` 使用普通 `yaml.safe_load`，默认不会报告 duplicate key；selector、finalizer 和 quality baseline 也会静默接受最后一个值。

建议：

- 使用拒绝重复 mapping key 的 strict YAML loader。
- `sources` 强制为非空 list，每项必须是 mapping，并至少含 `type` 与 `path`。
- `status`、`pipeline_stage`、`task6_state`、`task9_state` 增加一致性表，不允许 finalized + pending/revisiting 的冲突组合。
- `aiw-run-complete.py` 对被修改/晋级章节运行 strict frontmatter gate。
- 增加一次全库治理 job，但只能修 frontmatter 结构，不得借机改正文或机械补 URL。

### 12.12 P1：读者正文仍有任务过程话术，现有 gate 覆盖不足

本轮新增 gate 已能拒绝 `ready-for-review`、`needs-rework`、`pipeline_stage` 和部分“本轮 rework”表达，但现存 finalized 正文仍可见：

- `Review-finalize 2026-08-08`
- `Draft-polish 2026-07-29`
- `本次 draft-polish`
- `为了兼容 Hermes 流水线`
- `加工说明`
- `历史原文标记……请以后文为准`

原因有两层：

1. gate 只扫描本次实际 changed paths，不会主动发现从未再次触碰的旧章节。
2. 正则没有覆盖 `Review-finalize`、`Draft-polish`、Hermes/OpenClaw、受保护大纲和可引用正文等变体。

建议增加一次 canonical 全库 reader-facing 扫描，并把 operational 信息迁移到 frontmatter/log/report。正文只保留技术边界，例如“厂商私有实现没有公开证据”，不保留谁在何时用哪个 lane 做了什么。

### 12.13 P2：finding 关联逻辑仍未完全统一

`aiw-review-finalize-context.py` 当前只按 finding 的 `chapter` 字段与 path/stem/chapter/title 做匹配；quality baseline 和 completion gate 还支持 `target_path`、`source_paths`。

结果是：agent context 可能看不到实际关联的 open finding，最后到 completion gate 才被阻断。建议所有 lane 共用 `aiw_pipeline_common.py` 中同一个 finding matcher，按下列顺序匹配：

1. `target_path` 精确匹配。
2. `source_paths` 包含 target。
3. `chapter` 与 relative path / chapter id / title / stem 匹配。

### 12.14 prompt 修改优先级

建议对应 agent 按以下顺序修改，不要同时扩大任务频率：

#### P0：先恢复可运行性

1. 修复所有 context 的 YAML date/datetime JSON 规范化。
2. selftest 增加 unquoted-date fixture，恢复 exit 0。

#### P0：阻止错误正文进入 publication-state

1. 明确“事实正确性高于 outline 保护”。
2. finalized/verified 全文禁止保留已知错误原文，即使有 warning/勘误。
3. 将 5.26、6.1、6.19、1.48 建立稳定 P1 finding，路由到 rework；完成方式参考 staged-install 的 `a1564913d`。
4. `aiw-run-complete.py` 新增“历史错稿免责声明”和全文矛盾阻断 gate。

#### P1：修复选择器和诊断安全

1. freshness wrapper 转发所有 CLI 参数。
2. selector 统一限定 canonical 622 章。
3. pending marker 三分类，删除 `[来源:] >= 2` 这种魔法数字门槛。
4. cooldown 同时读取 manifest 与 frontmatter audit 时间。
5. strict YAML duplicate-key/sources schema gate。

#### P2：再优化吞吐和统计

1. 质量基线分别报告技术阻断、证据债务、编辑候选、稳定证据边界，不再混成一个 risk_count。
2. 48 小时/7 天报表增加 `substantive-correction`、`wrong-content-deletion`、`metadata-evidence-only`、`prose-only`、`no-change` 分类。
3. DeepSeek 频率暂时保持每天 4 次，先观察 7 天；不要用长段字符数单独驱动改写。

### 12.15 建议加入 prompt 的完整验收段

可把下面一段加入六条技术 lane 的公共 prompt：

```text
发布正文验收优先级：事实正确性 > 证据可追溯 > 版本边界 > 读者可理解性 > 历史 outline/锚点/原句保留。

必须检查整篇读者可见正文，而不只检查本次 diff：
1. 同一技术事实只能保留一套当前有效结论。旧稿、伪代码、虚构数字、错误状态机或已被后文否定的段落必须删除或重写。
2. outline 只保护主题覆盖，不保护错误原文。禁止用“历史大纲”“不作为结论”“请以后文为准”“为了兼容流水线”等免责声明包裹错稿后继续 finalized。
3. 上游源码中的 TODO/未完成实现属于版本边界证据；只有作者待补、无证据断言、空章节和编辑指令才是正文占位。不得为清除启发式命中而改写诚实的证据边界。
4. finalized/verified 前，关键 claim 必须逐项给出 source_evidence，并核对 deprecated、warning、migration、availability、API level 和版本适用范围。
5. 发现无法在单轮安全删除的大块错稿时，创建稳定 P1 finding 并降级到 needs-rework；不得保持 finalized，也不得只追加勘误。
6. 正文不得出现 run、round、agent、prompt、lane、pipeline、Review-finalize、Draft-polish、ready-for-review、needs-rework 或其他编辑过程信息。
```

### 12.16 对“是不是正文已经很完善”的最终回答

**不是。**

支持这个结论的证据不是单纯的风险计数，而是正文级抽样：

- 23.24 一次删除 403 行，清掉多个不存在 API 和固定性能数字。
- 1.46 一次删除 573 行历史错稿。
- 5.26 和 6.1 当前仍各自保留成段、已被本章后文承认错误的内容，并且处于 finalized。
- 24 个 canonical 章节仍未通过最基本的 sources/date metadata gate。
- 37 个 pending-marker 中大部分是误报，但误报之下仍混有真正的编辑占位和流程话术。

所以，过去任务“改得不明显”既不是因为 AIW 已经饱和，也不完全是因为所有任务都无效。更准确的拆解是：

- 一部分任务做了真正的技术纠错和错误内容删除。
- 一部分任务只完成了来源结构和状态闭环，这是必要工作，但不等于正文提升。
- 旧 prompt 对 outline 的事实优先级不明确，导致 agent 用免责声明隔离错稿而不删除。
- 选择器的 pending/source 启发式过粗，消耗了大量审计轮次。
- 当前修复刚建立可靠执行合同，但又出现 context date 序列化回归，说明自测覆盖仍不足。

### 12.17 本轮最终验收结论

**通过项：**

- Android 17 边界清晰且得到统一执行。
- manifest/lease/hash/evidence/result/git-sync 主闭环有效。
- 零 URL 高风险章节不会被机械 finalized。
- 过去 48 小时有真实、可辨识的正文修复。
- metadata 失败已从 29 降到 24，来源债务正在被真实消费。

**未通过项：**

- pipeline selftest 当前不是绿的。
- idle-audit 当前候选会因 YAML date 序列化崩溃。
- finalized 正文仍存在已知错误大纲与虚构数字。
- strict YAML duplicate-key/source schema gate 缺失。
- freshness wrapper 的 `--dry-run` 不是真 dry-run。
- selector 范围、pending marker 和 inline source 启发式仍会制造错误选题。

最终判断：**修复方向正确，但还不能宣布“任务群已经完全修好”。下一轮 agent 应先完成 12.14 的两个 P0，再处理 selector/YAML/pending 三类 P1。完成后重新跑 7 条 LLM context dry-run、selftest、strict metadata、全文 reader-facing gate，并至少对 5.26 与 6.1 做真实 rework；这才构成内容质量闭环。**

## 13. 全量修复实施与最终复验（2026-08-09 10:36 CST）

本节不是建议清单，而是对第 12 节问题的实际实施记录。修复已落到 live Hermes 脚本、live cron prompt / job 配置和 AIW 正文仓库，并已提交、推送；不是只写在复审文档中。Android 17 / API 37 平台上限保持不变。

### 13.1 已实施的流水线修复

- 在 `aiw_pipeline_common.py` 增加递归 `json_safe()`，统一处理 YAML 产生的 `date` / `datetime`、`Path` 和嵌套容器；body、review-finalize、四条 polish context 均使用同一规范化合同。
- 抽出 canonical 章节定义与 `iter_canonical_chapters()`；所有技术 selector、freshness 和 quality baseline 统一只处理 622 个 canonical 章节，preface / appendix 不再进入技术 lane。
- 将 marker 统一分成 `editorial-placeholder`、`declared-evidence-boundary`、`upstream-source-todo` 三类。只有第一类计入发布债务；移除正文 `[来源:]` 数量魔法门槛，并让 cooldown 同时读取 frontmatter 审计时间。
- freshness wrapper 已完整转发 `sys.argv[1:]`；dry-run 会验证 cursor、log、findings 和 Git 状态前后不变。
- `check-metadata.py` 与 `aiw-run-complete.py` 改为 strict YAML：拒绝重复 mapping key；`sources` 必须为非空 mapping list 且每项含 `type/path`；publication status 与 pending / revisiting 状态冲突会被阻断。
- finding 匹配已集中到共享 matcher，统一覆盖 `target_path`、`source_paths`、chapter / path / stem / title。
- completion gate 已增加 publication-state 全文检查，拒绝历史错稿免责声明、读者可见的 lane / pipeline 过程话术和 publication status 冲突；扫描会先剥离代码块与 HTML 注释，避免技术术语误报。
- quality baseline 已拆分技术阻断、证据债务、编辑候选、稳定证据边界，并给最近自动化改动增加 substantive-correction、wrong-content-deletion、metadata-evidence-only、prose-only 等结果分类。

### 13.2 Prompt 与 job 实施状态

六条技术 LLM lane 已全部加入第 12.15 节的完整“发布正文验收优先级”合同，每条恰好一份：

- aiw-body-apply
- aiw-review-finalize-apply
- aiw-polish-deep-review-apply
- aiw-polish-rework-apply
- aiw-polish-idle-audit-apply
- aiw-polish-draft-polish-apply

DeepSeek 中文 lane 已明确：上游 TODO 和诚实的证据边界不是中文缺陷；发现技术错误只能返回 `needs-human-review`，不得借中文润色改技术结论。

维护期间暂停的 7 个 writer / git-sync job 已全部恢复为 `scheduled/enabled`：

- `5fa9d7fe9e87` aiw-git-sync
- `2aa21bb1eb45` aiw-body-apply
- `464ba760c0e3` aiw-review-finalize-apply
- `a2fb41f345c8` aiw-polish-deep-review-apply
- `410de74688cd` aiw-polish-rework-apply
- `fb934850da95` aiw-polish-idle-audit-apply
- `ef444f87d299` aiw-polish-draft-polish-apply

### 13.3 AIW 正文与元数据治理

- 32 处重复 frontmatter key 已治理；137 篇章节的畸形 / 缺失 sources 和 publication-state 元数据已规范化。
- 5.26 JobScheduler、6.1 DataStore、6.19 memory compaction、1.48 Binder priority、5.29 GPU headroom 的已知错误 outline 已直接删除或重写，相关稳定 finding 已关闭。
- 同类全文扫描又清理了 1.41 ML scheduler、1.49 Staged Install、1.55 VNDK、gap rendering、ch06 历史页、9.11 / 9.13 ANR、5.32 BPF / schedutil 等错误旧稿。
- 从 143 个 canonical 文件移除 168 个 `OpenClaw 加工指引` / `流水线加工要求` / `加工说明` 块，并清理读者可见的 Review-finalize、draft-polish、run id 等过程话术；技术事实、源码 TODO 和诚实证据边界保留。
- 23.24 NNAPI / LiteRT 最后一个 P2 已补齐 `android-17.0.0_r1` 的 NDK header、ExecutionPlan、AIDL HAL、`external/tensorflow` METADATA / Android.bp / NNAPI delegate 锚点并关闭。当前 open finding 为 0。
- 编辑占位分类的全库命中由误报集合降为 0；19 篇中的 21 处合理证据边界和 11 篇中的 19 处上游源码 TODO 被正确保留并单独统计。

### 13.4 版本化与回滚

live Hermes 脚本仍由 `/Users/gracker/.hermes/scripts/` 执行；同时新增可审查快照：

`OpenClaw定时任务/Hermes-AIW-pipeline-snapshot/`

快照含 37 个 AIW Python 脚本、脱敏 AIW jobs 配置和 SHA-256 manifest，共 38 个 manifest entry。7 个核心 job 在快照中均为 scheduled；deliver endpoint 未进入 Git。

### 13.5 最终验收结果

| 检查项 | 最终结果 |
|---|---:|
| strict metadata | 622 / 622 通过，0 failure，0 warning |
| SUMMARY links | 661 links，0 duplicate warning |
| 7 条 context dry-run | 全部 exit 0，target 均为 canonical，未创建 manifest |
| pipeline selftest | exit 0 |
| freshness wrapper dry-run | scanned=0，repo / state hash 不变 |
| 全库 reader-facing gate | 0 命中 |
| publication historical-body gate | 0 命中 |
| editorial-placeholder | 0 chapter / 0 occurrence |
| open findings | 0 |
| cron state | 7 / 7 scheduled + enabled |
| AIW Git | clean，HEAD 与 origin/master 一致 |

quality baseline 仍将 140 / 401 个 publication-state 章节列为长期编辑候选，主要来自长段落、对比句和泛化文风启发式；它们不再包含来源缺失、编辑占位、技术阻断或 open finding，不能被解释为本轮 P0 / P1 未修复，也不能反向宣称全库正文已经内容饱和。

### 13.6 提交与推送

- `e9e75a7abc6016e8733aedb02f7e5d6269230dcc` — `[hermes-aiw] harden publication gates and remove content debt`
- `3e3bdb79e` — `[hermes-aiw] close NNAPI Android 17 source boundary`

两次提交均已推送到 `origin/master`。最终结论：第 12.14 节列出的 P0 / P1 / P2 流水线修复和第 12.6 节的阻断级正文清理已经全部实际落地；复审文档现在只是实施记录，不是唯一变更载体。
