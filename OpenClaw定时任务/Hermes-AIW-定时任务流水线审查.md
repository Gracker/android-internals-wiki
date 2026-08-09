# Hermes AIW 定时任务流水线审查包

- 生成时间：2026-08-08T22:29:51
- 来源：`/Users/gracker/.hermes/cron/jobs.json` + `/Users/gracker/.hermes/scripts/*.py` + 当前 `cronjob list` 输出。
- AIW 主项目：`/Users/gracker/.openclaw/workspace/Feishu/work-copies/Android-Internal-Wiki`
- Hermes profile：`default`
- 目的：给第三方 Agent review 当前 AIW 自动化流水线的任务设计、prompt、模型、写入边界、并发/调度风险。

## 0. 关键结论（给 reviewer 先读）

1. 当前活跃 AIW 写正文/改正文的 Hermes Agent LLM lane 共有 **6 个**：`aiw-body-apply`、`aiw-review-finalize-apply`、4 个 `aiw-polish-*-apply`。它们都显式固定为 `model=gpt-5.5`、`provider=openai-codex`，并限制 toolsets 为 `terminal,file`。
2. 采集、索引、Feishu 发布、git sync、watchdog 多数为 `no_agent=true` 的 script-only job：没有 Hermes prompt，也没有执行大模型。
3. 旧 OpenClaw 迁移遗留的 queue-worker/review-finalize script-only lane 仍在 cron 表里，但全部 paused；它们只产生候选/门禁报告，不由 LLM 改正文。
4. AIW 正文写入边界在 prompts 中反复声明：只改 JSON 指定的一个既有章节；禁止新增 `src/**/*.md`；禁止修改 `src/SUMMARY.md`；Android baseline 固定 `android-17.0.0_r1` / Android 17；禁止 Android 18/API38+ 主线结论。
5. Feishu sync 属于 AIW 发布链路，不改 AIW 正文；成功判据不能只看 dry-run ok，必须看 remote_writes、publish-state advance、AIW Unmapped=0。

## 1. 任务总览

| 状态 | 数量 | 任务 |
|---|---:|---|
| active/scheduled | 17 | `feishu-daily-sync-dry-run`, `feishu-daily-sync-guarded-write`, `feishu-daily-sync-monitor`, `aiw-daily-intake-tech-articles`, `aiw-daily-intake-incremental`, `aiw-daily-intake-deepresearch`, `aiw-daily-intake-classify`, `aiw-weekly-source-audit-clippings`, `aiw-weekly-source-audit-freshness`, `aiw-body-apply`, `aiw-review-finalize-apply`, `aiw-polish-deep-review-apply`, `aiw-polish-rework-apply`, `aiw-polish-idle-audit-apply`, `aiw-polish-draft-polish-apply`, `aiw-git-sync`, `aiw-throughput-watchdog` |
| paused legacy | 10 | `aiw-queue-worker-task2b-lite`, `aiw-queue-worker-source-research`, `aiw-queue-worker-task2a`, `aiw-queue-worker-task2b-main`, `aiw-review-finalize-reader-final`, `aiw-review-finalize-task2b-verifier`, `aiw-review-finalize-deep-tech-review`, `aiw-review-finalize-draft-review`, `aiw-queue-worker-dispatcher`, `aiw-review-finalize-dispatcher` |

## 2. 活跃流水线结构

```text
素材/资料采集（script-only, no LLM）
  aiw-daily-intake-tech-articles / incremental / deepresearch
        ↓
分类入队（script-only, no LLM）
  aiw-daily-intake-classify  -> metadata/source-index.json, metadata/queue.json
        ↓
正文应用与 review/finalize（Hermes Agent LLM: gpt-5.5 via openai-codex）
  aiw-body-apply
  aiw-review-finalize-apply
  aiw-polish-{deep-review,rework,idle-audit,draft-polish}-apply
        ↓
Git 发布（script-only, no LLM）
  aiw-git-sync -> commit/push origin master
        ↓
Feishu 发布（script-only, no LLM）
  feishu-daily-sync-dry-run -> guarded-write -> monitor
        ↓
吞吐/健康观测（script-only, no LLM）
  aiw-throughput-watchdog
```

## 3. 每个任务详情（prompt 与模型）

### feishu-daily-sync-dry-run

- job_id: `2955f4f3f151`
- state/enabled: `scheduled` / `True`
- schedule: `30 9 * * *`
- repeat: `{'times': None, 'completed': 22}`
- deliver: `telegram:-1003814981550`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-08-08T09:31:13.796203+08:00` / `ok`
- next_run: `2026-08-09T09:30:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/feishu-daily-sync`
- script: `feishu-daily-sync-dry-run.py`
- no_agent: `True`
- skills: `[]`
- enabled_toolsets: `None`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- 无 Hermes Agent 大模型：`no_agent=true`，仅运行脚本 stdout；job.model/provider/model_snapshot 均不参与推理。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

脚本只执行 Feishu sync dry-run 包装器；核心职责是刷新 AIW GitHub work-copy、重建 AIW map、生成 publish plan/sanity gate，不写 Feishu。成功不能代表远端发布成功。

**Hermes prompt**

> 空：该 job 没有 Hermes prompt。若 `no_agent=true`，调度器只运行脚本并把 stdout 原样投递；第三方 review 需要看 script 的行为而不是 prompt。

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/feishu-daily-sync-dry-run.py`

### feishu-daily-sync-guarded-write

- job_id: `70e6cc5c0f14`
- state/enabled: `scheduled` / `True`
- schedule: `40 9 * * *`
- repeat: `{'times': None, 'completed': 18}`
- deliver: `telegram:-1003814981550`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-08-08T09:42:01.442435+08:00` / `ok`
- next_run: `2026-08-09T09:40:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/feishu-daily-sync`
- script: `feishu-daily-sync-guarded-write.py`
- no_agent: `True`
- skills: `[]`
- enabled_toolsets: `None`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- 无 Hermes Agent 大模型：`no_agent=true`，仅运行脚本 stdout；job.model/provider/model_snapshot 均不参与推理。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

脚本执行 guarded write；先跑 dry-run/catch-up gate，再在安全条件下写入 Feishu。AIW 成功判据是 remote_writes>0、publish-state advance、AIW Unmapped 为 0。

**Hermes prompt**

> 空：该 job 没有 Hermes prompt。若 `no_agent=true`，调度器只运行脚本并把 stdout 原样投递；第三方 review 需要看 script 的行为而不是 prompt。

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/feishu-daily-sync-guarded-write.py`

### feishu-daily-sync-monitor

- job_id: `0002c4202fac`
- state/enabled: `scheduled` / `True`
- schedule: `0 10 * * *`
- repeat: `{'times': None, 'completed': 21}`
- deliver: `telegram:-1003814981550`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-08-08T10:00:05.419502+08:00` / `ok`
- next_run: `2026-08-09T10:00:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/feishu-daily-sync`
- script: `feishu-daily-sync-monitor.py`
- no_agent: `True`
- skills: `[]`
- enabled_toolsets: `None`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- 无 Hermes Agent 大模型：`no_agent=true`，仅运行脚本 stdout；job.model/provider/model_snapshot 均不参与推理。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

脚本读取最近 daily artifacts / publish-state / gate 输出，做发布健康检查与 Action 群简报；不调用 LLM，不写正文。

**Hermes prompt**

> 空：该 job 没有 Hermes prompt。若 `no_agent=true`，调度器只运行脚本并把 stdout 原样投递；第三方 review 需要看 script 的行为而不是 prompt。

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/feishu-daily-sync-monitor.py`

### aiw-daily-intake-tech-articles

- job_id: `f50a04d870c3`
- state/enabled: `scheduled` / `True`
- schedule: `25 5 * * *`
- repeat: `{'times': None, 'completed': 23}`
- deliver: `local`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-08-08T05:25:25.226031+08:00` / `ok`
- next_run: `2026-08-09T05:25:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-daily-intake`
- script: `aiw-daily-intake-tech-articles.py`
- no_agent: `True`
- skills: `[]`
- enabled_toolsets: `None`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- 无 Hermes Agent 大模型：`no_agent=true`，仅运行脚本 stdout；job.model/provider/model_snapshot 均不参与推理。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

wrapper -> aiw-daily-intake.py --mode tech-articles；调用 metadata/tech-article intake 脚本，读取外部技术文章素材，写 intake/daily-info 与报告/状态，不改正文。

**Hermes prompt**

> 空：该 job 没有 Hermes prompt。若 `no_agent=true`，调度器只运行脚本并把 stdout 原样投递；第三方 review 需要看 script 的行为而不是 prompt。

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-daily-intake-tech-articles.py`
- common implementation: `/Users/gracker/.hermes/scripts/aiw-daily-intake.py`

### aiw-daily-intake-incremental

- job_id: `2364b7bf9a07`
- state/enabled: `scheduled` / `True`
- schedule: `45 5 * * *`
- repeat: `{'times': None, 'completed': 23}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-08-08T05:45:29.500833+08:00` / `ok`
- next_run: `2026-08-09T05:45:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-daily-intake`
- script: `aiw-daily-intake-incremental.py`
- no_agent: `True`
- skills: `[]`
- enabled_toolsets: `None`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- 无 Hermes Agent 大模型：`no_agent=true`，仅运行脚本 stdout；job.model/provider/model_snapshot 均不参与推理。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

wrapper -> aiw-daily-intake.py --mode incremental；扫描最近 Obsidian/资料变更，汇入 intake/daily-info 或索引，不改正文。

**Hermes prompt**

> 空：该 job 没有 Hermes prompt。若 `no_agent=true`，调度器只运行脚本并把 stdout 原样投递；第三方 review 需要看 script 的行为而不是 prompt。

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-daily-intake-incremental.py`
- common implementation: `/Users/gracker/.hermes/scripts/aiw-daily-intake.py`

### aiw-daily-intake-deepresearch

- job_id: `db79021b32a0`
- state/enabled: `scheduled` / `True`
- schedule: `10 6 * * *`
- repeat: `{'times': None, 'completed': 23}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-08-08T06:10:33.342759+08:00` / `ok`
- next_run: `2026-08-09T06:10:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-daily-intake`
- script: `aiw-daily-intake-deepresearch.py`
- no_agent: `True`
- skills: `[]`
- enabled_toolsets: `None`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- 无 Hermes Agent 大模型：`no_agent=true`，仅运行脚本 stdout；job.model/provider/model_snapshot 均不参与推理。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

wrapper -> aiw-daily-intake.py --mode deepresearch；扫描 DeepResearch 新材料，生成 daily-info 条目和推荐映射章节，不改正文。

**Hermes prompt**

> 空：该 job 没有 Hermes prompt。若 `no_agent=true`，调度器只运行脚本并把 stdout 原样投递；第三方 review 需要看 script 的行为而不是 prompt。

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-daily-intake-deepresearch.py`
- common implementation: `/Users/gracker/.hermes/scripts/aiw-daily-intake.py`

### aiw-daily-intake-classify

- job_id: `51d73c474658`
- state/enabled: `scheduled` / `True`
- schedule: `20 6 * * *`
- repeat: `{'times': None, 'completed': 23}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-08-08T06:20:34.445142+08:00` / `ok`
- next_run: `2026-08-09T06:20:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-daily-intake`
- script: `aiw-daily-intake-classify.py`
- no_agent: `True`
- skills: `[]`
- enabled_toolsets: `None`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- 无 Hermes Agent 大模型：`no_agent=true`，仅运行脚本 stdout；job.model/provider/model_snapshot 均不参与推理。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

wrapper -> aiw-daily-intake.py --mode classify；解析 daily-info，评分、过滤聚合/状态报告，把高分材料写入 metadata/source-index.json / queue.json。带 chapter freeze：route 到既有章节，避免新增章节。

**Hermes prompt**

> 空：该 job 没有 Hermes prompt。若 `no_agent=true`，调度器只运行脚本并把 stdout 原样投递；第三方 review 需要看 script 的行为而不是 prompt。

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-daily-intake-classify.py`
- common implementation: `/Users/gracker/.hermes/scripts/aiw-daily-intake.py`

### aiw-weekly-source-audit-clippings

- job_id: `93d3c7568b39`
- state/enabled: `scheduled` / `True`
- schedule: `30 6 * * *`
- repeat: `{'times': None, 'completed': 23}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-08-08T06:30:35.727585+08:00` / `ok`
- next_run: `2026-08-09T06:30:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-weekly-source-audit`
- script: `aiw-weekly-source-audit-clippings-reference-scan.py`
- no_agent: `True`
- skills: `[]`
- enabled_toolsets: `None`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- 无 Hermes Agent 大模型：`no_agent=true`，仅运行脚本 stdout；job.model/provider/model_snapshot 均不参与推理。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

wrapper -> aiw-weekly-source-audit.py --mode clippings-reference-scan；批量扫描参考资料/剪藏差异，生成 suggestions/gaps 证据，通常不改正文。

**Hermes prompt**

> 空：该 job 没有 Hermes prompt。若 `no_agent=true`，调度器只运行脚本并把 stdout 原样投递；第三方 review 需要看 script 的行为而不是 prompt。

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-weekly-source-audit-clippings-reference-scan.py`
- common implementation: `/Users/gracker/.hermes/scripts/aiw-weekly-source-audit.py`

### aiw-weekly-source-audit-freshness

- job_id: `c7fcfd963ce5`
- state/enabled: `scheduled` / `True`
- schedule: `0 2 * * 1,3,5`
- repeat: `{'times': None, 'completed': 10}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-08-07T02:00:27.460680+08:00` / `ok`
- next_run: `2026-08-10T02:00:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-weekly-source-audit`
- script: `aiw-weekly-source-audit-freshness-check.py`
- no_agent: `True`
- skills: `[]`
- enabled_toolsets: `None`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- 无 Hermes Agent 大模型：`no_agent=true`，仅运行脚本 stdout；job.model/provider/model_snapshot 均不参与推理。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

wrapper -> aiw-weekly-source-audit.py --mode freshness-check；扫描章节时效性风险，向 queue.json 追加风险修复项，写 Obsidian formal report，不改正文。

**Hermes prompt**

> 空：该 job 没有 Hermes prompt。若 `no_agent=true`，调度器只运行脚本并把 stdout 原样投递；第三方 review 需要看 script 的行为而不是 prompt。

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-weekly-source-audit-freshness-check.py`
- common implementation: `/Users/gracker/.hermes/scripts/aiw-weekly-source-audit.py`

### aiw-body-apply

- job_id: `2aa21bb1eb45`
- state/enabled: `scheduled` / `True`
- schedule: `15 7,9,11,13,15,17,19,21,23 * * *`
- repeat: `{'times': None, 'completed': 152}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '-1004339755728', 'chat_name': 'OpenClaw - EBook', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-08-08T21:15:44.038401+08:00` / `ok`
- next_run: `2026-08-08T23:15:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-body-apply`
- script: `aiw-body-apply-context.py`
- no_agent: `False`
- skills: `['scheduled-obsidian-output-task']`
- enabled_toolsets: `['terminal', 'file']`
- model/provider/base_url: `gpt-5.5` / `openai-codex` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- Hermes Agent LLM：model=`gpt-5.5`；provider=`openai-codex`；base_url=`None`。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

LLM apply lane。pre-run script aiw-body-apply-context.py 从 queue/source-index 选一个 candidate_ready，输出目标章节、材料、run_id、formal_report_path；Hermes Agent 修改一个既有章节并更新队列/索引。

**Hermes prompt**

```text
你是 AIW Body Apply 最终闭环任务，替代旧 OpenClaw AIW writer loop。上游脚本 aiw-body-apply-context.py 会输出 JSON。若 status=no-new-input：最终回复保持简短 no-new-input，不改文件。若 status=blocked：写清 blocker。若 status=candidate_ready，必须完成整个闭环，不要停在计划或候选：

1. 读取 JSON 中 aiw_repo、target.path、materials、candidate、formal_report_path、run_id。
2. 只修改 JSON 指定的一个既有 target.path 章节正文；禁止新增 src 文件，禁止修改 src/SUMMARY.md。Android baseline 为 android-17.0.0_r1 / android17-6.18；不得引入 Android 18/API38+ 结论。
3. 基于 materials 的原文和 target 现状，把材料编译进章节正文；每条关键技术断言都必须带来源标记，如 [来源: <material filename>] 或 [已验证: ...]。不是写候选报告，必须实际改正文。
4. 更新 target YAML frontmatter：status 至少推进到 ready-for-review；写 last_body_apply_at、last_body_apply_run_id、last_body_apply_source；设置 task2b_state=fixed、task6_state=revisiting、task9_state=pending、pipeline_stage=task6_pending；补齐 last_verified/confidence/sources 以通过 metadata 检查。
5. 更新 metadata/queue.json 或 metadata/source-index.json 中对应 candidate：status/action=body-applied 或 applied，写 applied_at、applied_run_id、target_path。保持 JSON 有效。
6. 写 formal_report_path 到 Obsidian，说明修改了哪些正文、来源、影响范围、evidence。~/.hermes/state 只作 evidence。
7. 在 AIW repo 运行：python3 scripts/check-metadata.py --files <changed chapter>；python3 scripts/check-summary-links.py；git diff --check。失败则修复后重跑。
8. 运行 /Users/gracker/.hermes/scripts/aiw-git-sync.py 提交推送 allowlist 文件。推送后用 gh run list / gh run watch 检查新 HEAD 的 Build & Check 和 Knowledge Pack Candidate；必须等到 success 或明确报告失败日志。
9. 最终 Telegram 输出按 AIW 格式：status、修改内容、影响范围、Obsidian report、Evidence、GitHub SHA、CI 结论。
```

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-body-apply-context.py`

### aiw-review-finalize-apply

- job_id: `464ba760c0e3`
- state/enabled: `scheduled` / `True`
- schedule: `5 8,10,12,14,16,18,20,22 * * *`
- repeat: `{'times': None, 'completed': 138}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '-1004339755728', 'chat_name': 'OpenClaw - EBook', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-08-08T22:08:25.704099+08:00` / `ok`
- next_run: `2026-08-09T08:05:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-review-finalize-apply`
- script: `aiw-review-finalize-context.py`
- no_agent: `False`
- skills: `['scheduled-obsidian-output-task']`
- enabled_toolsets: `['terminal', 'file']`
- model/provider/base_url: `gpt-5.5` / `openai-codex` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- Hermes Agent LLM：model=`gpt-5.5`；provider=`openai-codex`；base_url=`None`。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

LLM review/finalize lane。pre-run script aiw-review-finalize-context.py 选择 ready-for-review/review/revisiting/task9 pending 章节；Hermes Agent 做深度 review、必要修复、状态推进或 needs-rework。

**Hermes prompt**

```text
你是 AIW Review/Finalize Apply，恢复 OpenClaw 旧高强度 review/fix/finalize 的核心，但必须串行、受控、避免同时写文件。上游脚本 aiw-review-finalize-context.py 会输出 JSON。

若 status=no-new-input：最终回复 `[SILENT]`。
若 status=blocked：输出 blocker。
若 status=review_candidate_ready，必须处理 JSON 指定的一个 target：

1. 读取 aiw_repo、target.path、target.frontmatter、materials、formal_report_path、run_id。
2. 只处理这一个既有章节。禁止新增 `src/**/*.md`；禁止修改 `src/SUMMARY.md`；主线 Android baseline 为 `android-17.0.0_r1` / Android 17，禁止 Android 18/API38+ 主线结论。
3. 做 OpenClaw 风格深度 review：源码准确性、版本边界、来源支撑、中文可读性、章节结构、待验证项是否诚实。
4. 不要只写候选报告：
   - 如果发现小范围问题且有材料支撑，直接 patch 章节正文/frontmatter。
   - 如果已足够可靠，推进 `status: finalized`，写 `reviewed_date`、`reviewed_by: hermes-aiw-review-finalize-apply`、`task6_state: reviewed`、`task9_state: reviewed`、`pipeline_stage: finalized`、`last_review_finalize_at`、`last_review_finalize_run_id`。
   - 如果不能 finalized，保持或设置 `status: ready-for-review` / `needs-rework`，写明 rework reason，并更新 `task9_state: needs-rework` 或 `task6_state: needs-rework`。
5. 写 Obsidian formal_report_path，说明审阅结论、实际改动、是否 finalized、风险/待验证、evidence。
6. 写 evidence 到 `/Users/gracker/.hermes/state/aiw-review-finalize-apply/<run_id>.json`。
7. 在 AIW repo 运行：`python3 scripts/check-metadata.py --files <target-relative-path>`、`python3 scripts/check-summary-links.py`、`git diff --check`。失败必须修复后重跑。
8. 不要主动运行 aiw-git-sync.py；git sync 已降频到每轮 :50 批量执行，避免过度频繁提交。
9. 最终输出 AIW 格式：status、审阅章节、实际改动、finalize/rework 结论、Obsidian report、Evidence、本地校验结论。
```

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-review-finalize-context.py`

### aiw-polish-deep-review-apply

- job_id: `a2fb41f345c8`
- state/enabled: `scheduled` / `True`
- schedule: `35 8,12,16,20 * * *`
- repeat: `{'times': None, 'completed': 58}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-08-08T20:38:16.558832+08:00` / `ok`
- next_run: `2026-08-09T08:35:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-polish-apply`
- script: `aiw-polish-deep-review-context.py`
- no_agent: `False`
- skills: `['scheduled-obsidian-output-task']`
- enabled_toolsets: `['terminal', 'file']`
- model/provider/base_url: `gpt-5.5` / `openai-codex` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- Hermes Agent LLM：model=`gpt-5.5`；provider=`openai-codex`；base_url=`None`。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

LLM polish lane。pre-run script aiw-polish-deep-review-context.py -> aiw-polish-context.py --mode deep-review；选择 ready-for-review/reviewing 章节做技术审计。

**Hermes prompt**

```text
你是 AIW Polish Apply 的 deep-review lane，用来恢复 OpenClaw 的高强度技术审计，但保留“不新增章节”的约束。上游脚本输出 JSON。

若 status=no-new-input：最终回复 `[SILENT]`，不改文件。
若 status=blocked：输出 blocker。
若 status=polish_candidate_ready：必须处理 JSON 指定的一个既有 target。

执行要求：
1. 读取 aiw_repo、mode、target.path、target.frontmatter、target.quality_flags、materials、formal_report_path、run_id。
2. 只处理这个既有章节；禁止新增 `src/**/*.md`；禁止修改 `src/SUMMARY.md`；Android baseline 固定 `android-17.0.0_r1` / Android 17，禁止 Android 18/API38+ 主线结论。
3. 职责是 deep-review / 技术审计，不是无来源写新章节：
   - 有 materials 或章节已有充分正文时，做源码/版本边界/来源支撑/中文可读性/章节结构/待验证项审计，并修复小范围且有依据的问题。
   - 若 materials 为空且章节正文很薄/像占位稿，禁止凭通用知识大段扩写；只能做 frontmatter/状态修复、标注 `needs-rework` 或 `ready-for-review` 回流原因，并写明需要 body-apply/source material。
4. 根据结果更新正文与 frontmatter：可保留 `ready-for-review`，或推进/修正 `task6_state`、`task9_state`、`pipeline_stage`、`last_deep_review_at`、`last_deep_review_run_id`、`last_verified`、`confidence`。如果无来源支撑，不能提升 confidence。
5. 在 repo 写 `logs/deep-review/YYYY-MM-DD-<run_id>-deep-review.md`，记录审计结论、P0/P1/P2、实际补丁或回流原因。
6. 写 formal_report_path 到 Obsidian，说明修改内容、影响范围、风险、evidence。
7. 在 AIW repo 运行：`python3 scripts/check-metadata.py --files <target-relative-path>`、`python3 scripts/check-summary-links.py`、`git diff --check`。失败必须修复后重跑。
8. 不要运行 `aiw-git-sync.py`；后续 sync cron 会用描述性 commit message 批量提交。
9. 最终输出 AIW 格式：status、审计章节、实际改动、P0/P1/P2、Obsidian report、Evidence、本地校验结论。
```

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-polish-deep-review-context.py`
- common implementation: `/Users/gracker/.hermes/scripts/aiw-polish-context.py`

### aiw-polish-rework-apply

- job_id: `410de74688cd`
- state/enabled: `scheduled` / `True`
- schedule: `35 9,13,17,21 * * *`
- repeat: `{'times': None, 'completed': 56}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-08-08T21:38:52.197016+08:00` / `ok`
- next_run: `2026-08-09T09:35:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-polish-apply`
- script: `aiw-polish-rework-context.py`
- no_agent: `False`
- skills: `['scheduled-obsidian-output-task']`
- enabled_toolsets: `['terminal', 'file']`
- model/provider/base_url: `gpt-5.5` / `openai-codex` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- Hermes Agent LLM：model=`gpt-5.5`；provider=`openai-codex`；base_url=`None`。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

LLM polish lane。pre-run script aiw-polish-rework-context.py -> aiw-polish-context.py --mode rework；优先 needs-rework/task6/task9/待验证，做安全修复和状态回流。

**Hermes prompt**

```text
你是 AIW Polish Apply 的 rework lane，用来恢复 OpenClaw 的 rework / rework-verify 状态流转，但保留“不新增章节”的约束。上游脚本输出 JSON。

若 status=no-new-input：最终回复 `[SILENT]`，不改文件。
若 status=blocked：输出 blocker。
若 status=polish_candidate_ready：必须处理 JSON 指定的一个既有 target。

执行要求：
1. 读取 aiw_repo、mode、target.path、quality_flags、materials、formal_report_path、run_id。
2. 只处理这个既有章节；禁止新增 `src/**/*.md`；禁止修改 `src/SUMMARY.md`；Android baseline 固定 `android-17.0.0_r1` / Android 17。
3. 聚焦 needs-rework、待验证、版本边界、引用不足、frontmatter 状态错误。优先做安全正文/元数据修复，不要停在报告。
4. 修复后根据实际情况把 `status` 推回 `ready-for-review` 或保持 `needs-rework`；更新 `task6_state`、`task9_state`、`pipeline_stage`、`last_rework_at`、`last_rework_run_id`、`last_verified`、`confidence`。
5. 在 repo 写 `logs/rework/YYYY-MM-DD-<run_id>-rework.md`，记录原问题、修复点、剩余风险。
6. 写 formal_report_path 到 Obsidian。
7. 在 AIW repo 运行：`python3 scripts/check-metadata.py --files <target-relative-path>`、`python3 scripts/check-summary-links.py`、`git diff --check`。失败必须修复后重跑。
8. 不要运行 `aiw-git-sync.py`；后续 sync cron 批量提交。
9. 最终输出 AIW 格式：status、rework 章节、实际改动、状态流转、Obsidian report、Evidence、本地校验结论。
```

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-polish-rework-context.py`
- common implementation: `/Users/gracker/.hermes/scripts/aiw-polish-context.py`

### aiw-polish-idle-audit-apply

- job_id: `fb934850da95`
- state/enabled: `scheduled` / `True`
- schedule: `35 10,14,18,22 * * *`
- repeat: `{'times': None, 'completed': 56}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-08-08T18:38:00.954359+08:00` / `ok`
- next_run: `2026-08-08T22:35:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-polish-apply`
- script: `aiw-polish-idle-audit-context.py`
- no_agent: `False`
- skills: `['scheduled-obsidian-output-task']`
- enabled_toolsets: `['terminal', 'file']`
- model/provider/base_url: `gpt-5.5` / `openai-codex` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- Hermes Agent LLM：model=`gpt-5.5`；provider=`openai-codex`；base_url=`None`。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

LLM polish lane。pre-run script aiw-polish-idle-audit-context.py -> aiw-polish-context.py --mode idle-audit；闲时抽检 finalized/verified 章节的越界、待验证、引用缺口。

**Hermes prompt**

```text
你是 AIW Polish Apply 的 idle-audit lane，用来恢复 OpenClaw 的 idle audit / sampling audit，但保留“不新增章节”的约束。上游脚本输出 JSON。

若 status=no-new-input：最终回复 `[SILENT]`，不改文件。
若 status=blocked：输出 blocker。
若 status=polish_candidate_ready：必须处理 JSON 指定的一个既有 finalized/verified target。

执行要求：
1. 读取 aiw_repo、mode、target.path、quality_flags、materials、formal_report_path、run_id。
2. 只处理这个既有章节；禁止新增 `src/**/*.md`；禁止修改 `src/SUMMARY.md`；Android baseline 固定 `android-17.0.0_r1` / Android 17。
3. 做闲时抽检：找 Android 18/API38 越界、待验证残留、来源标记不足、frontmatter 缺项、明显技术/表达问题。
4. 只修复安全且明确的问题。若无安全补丁，也要写 audit log 说明“抽检通过/未修改”，但不要为了提交而 churn 正文。
5. 更新 `last_idle_audit_at`、`last_idle_audit_run_id`、`task9_state` / `pipeline_stage` 等必要 frontmatter。若发现严重问题，降级为 `ready-for-review` 或 `needs-rework` 并写原因。
6. 在 repo 写 `logs/audit/YYYY-MM-DD-<run_id>-idle-audit.md`。
7. 写 formal_report_path 到 Obsidian。
8. 在 AIW repo 运行：`python3 scripts/check-metadata.py --files <target-relative-path>`、`python3 scripts/check-summary-links.py`、`git diff --check`。失败必须修复后重跑。
9. 不要运行 `aiw-git-sync.py`；后续 sync cron 批量提交。
10. 最终输出 AIW 格式：status、audit 章节、实际改动/抽检通过、Obsidian report、Evidence、本地校验结论。
```

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-polish-idle-audit-context.py`
- common implementation: `/Users/gracker/.hermes/scripts/aiw-polish-context.py`

### aiw-polish-draft-polish-apply

- job_id: `ef444f87d299`
- state/enabled: `scheduled` / `True`
- schedule: `35 11,15,19,23 * * *`
- repeat: `{'times': None, 'completed': 56}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-08-08T19:37:39.946760+08:00` / `ok`
- next_run: `2026-08-08T23:35:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-polish-apply`
- script: `aiw-polish-draft-polish-context.py`
- no_agent: `False`
- skills: `['scheduled-obsidian-output-task']`
- enabled_toolsets: `['terminal', 'file']`
- model/provider/base_url: `gpt-5.5` / `openai-codex` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- Hermes Agent LLM：model=`gpt-5.5`；provider=`openai-codex`；base_url=`None`。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

LLM polish lane。pre-run script aiw-polish-draft-polish-context.py -> aiw-polish-context.py --mode draft-polish；只打磨既有 draft，不新增章节。

**Hermes prompt**

```text
你是 AIW Polish Apply 的 draft-polish lane，用来恢复 OpenClaw 的 draft polishing / review preparation，但保留“不新增章节”的约束。上游脚本输出 JSON。

若 status=no-new-input：最终回复 `[SILENT]`，不改文件。
若 status=blocked：输出 blocker。
若 status=polish_candidate_ready：必须处理 JSON 指定的一个既有 draft target。

执行要求：
1. 读取 aiw_repo、mode、target.path、quality_flags、materials、formal_report_path、run_id。
2. 只处理这个既有 draft 章节；禁止新增 `src/**/*.md`；禁止修改 `src/SUMMARY.md`；Android baseline 固定 `android-17.0.0_r1` / Android 17。
3. 职责是“打磨既有 draft”，不是无来源写新章节。只能补强已有材料或章节现有内容支撑的内容；不得编造源码结论。
4. 如果 materials 为空且章节正文很薄/像占位稿：不要大段扩写；只做结构/frontmatter/状态修复，保留 draft 或设置 needs-rework，并写清需要 body-apply/source material。
5. 有足够支撑时，目标是把现有 draft 打磨到 `ready-for-review`：结构、术语、来源标记、版本边界、待验证项、frontmatter 完整性。更新 `status: ready-for-review`、`task6_state: pending` 或 `revisiting`、`task9_state: pending`、`pipeline_stage: task6_pending`、`last_draft_polish_at`、`last_draft_polish_run_id`、`last_verified`、`confidence`。不足时保持 draft 并写清阻塞原因。
6. 在 repo 写 `logs/review/YYYY-MM-DD-<run_id>-draft-polish.md`。
7. 写 formal_report_path 到 Obsidian。
8. 在 AIW repo 运行：`python3 scripts/check-metadata.py --files <target-relative-path>`、`python3 scripts/check-summary-links.py`、`git diff --check`。失败必须修复后重跑。
9. 不要运行 `aiw-git-sync.py`；后续 sync cron 批量提交。
10. 最终输出 AIW 格式：status、draft 章节、实际改动、状态推进、Obsidian report、Evidence、本地校验结论。
```

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-polish-draft-polish-context.py`
- common implementation: `/Users/gracker/.hermes/scripts/aiw-polish-context.py`

### aiw-git-sync

- job_id: `5fa9d7fe9e87`
- state/enabled: `scheduled` / `True`
- schedule: `55 7-23 * * *`
- repeat: `{'times': None, 'completed': 269}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-08-08T21:56:00.916359+08:00` / `ok`
- next_run: `2026-08-08T22:55:00+08:00`
- workdir: `None`
- script: `aiw-git-sync.py`
- no_agent: `True`
- skills: `[]`
- enabled_toolsets: `None`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- 无 Hermes Agent 大模型：`no_agent=true`，仅运行脚本 stdout；job.model/provider/model_snapshot 均不参与推理。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

script-only Git 同步。扫描 AIW repo 变更，按变更类型生成 commit subject，运行 summary 检查，commit/push 到 origin master；不调用 LLM。注意它指向 Obsidian local AIW repo，而 Feishu sync 使用 GitHub work-copy。

**Hermes prompt**

> 空：该 job 没有 Hermes prompt。若 `no_agent=true`，调度器只运行脚本并把 stdout 原样投递；第三方 review 需要看 script 的行为而不是 prompt。

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-git-sync.py`

### aiw-throughput-watchdog

- job_id: `167290e723e9`
- state/enabled: `scheduled` / `True`
- schedule: `58 23 * * *`
- repeat: `{'times': None, 'completed': 15}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-08-07T23:58:43.292546+08:00` / `ok`
- next_run: `2026-08-08T23:58:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-polish-apply`
- script: `aiw-throughput-watchdog.py`
- no_agent: `True`
- skills: `[]`
- enabled_toolsets: `['terminal']`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- 无 Hermes Agent 大模型：`no_agent=true`，仅运行脚本 stdout；job.model/provider/model_snapshot 均不参与推理。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

script-only 吞吐 watchdog。统计最近报告、source-index pending、chapter frontmatter status、GitHub Actions 状态，写 formal Obsidian report 并发 Telegram 健康报告；不调用 LLM。

**Hermes prompt**

```text
AIW closed-loop throughput watchdog. The script prints the final Telegram-ready health report and writes the formal Obsidian report.
```

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-throughput-watchdog.py`

### aiw-queue-worker-task2b-lite

- job_id: `eddc94a6c35d`
- state/enabled: `paused` / `False`
- schedule: `35 1-23/2 * * *`
- repeat: `{'times': None, 'completed': 1}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-07-18T21:35:25.253427+08:00` / `ok`
- next_run: `2026-07-18T23:35:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-queue-worker`
- script: `aiw-queue-worker-task2b-lite.py`
- no_agent: `True`
- skills: `[]`
- enabled_toolsets: `None`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- 无 Hermes Agent 大模型：`no_agent=true`，仅运行脚本 stdout；job.model/provider/model_snapshot 均不参与推理。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

暂停 legacy script-only lane。wrapper -> aiw-queue-worker.py --mode task2b-lite；只产出候选/门禁报告，不写正文。

**Hermes prompt**

> 空：该 job 没有 Hermes prompt。若 `no_agent=true`，调度器只运行脚本并把 stdout 原样投递；第三方 review 需要看 script 的行为而不是 prompt。

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-queue-worker-task2b-lite.py`
- common implementation: `/Users/gracker/.hermes/scripts/aiw-queue-worker.py`

### aiw-queue-worker-source-research

- job_id: `87e270a88b46`
- state/enabled: `paused` / `False`
- schedule: `50 2,5,8,11,14,17,20,23 * * *`
- repeat: `{'times': None, 'completed': 0}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `None` / `None`
- next_run: `2026-07-18T23:50:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-queue-worker`
- script: `aiw-queue-worker-source-research.py`
- no_agent: `True`
- skills: `[]`
- enabled_toolsets: `None`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- 无 Hermes Agent 大模型：`no_agent=true`，仅运行脚本 stdout；job.model/provider/model_snapshot 均不参与推理。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

暂停 legacy script-only lane。wrapper -> aiw-queue-worker.py --mode source-research；选择 source-index pending 候选，只产出报告。

**Hermes prompt**

> 空：该 job 没有 Hermes prompt。若 `no_agent=true`，调度器只运行脚本并把 stdout 原样投递；第三方 review 需要看 script 的行为而不是 prompt。

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-queue-worker-source-research.py`
- common implementation: `/Users/gracker/.hermes/scripts/aiw-queue-worker.py`

### aiw-queue-worker-task2a

- job_id: `07fc533fb059`
- state/enabled: `paused` / `False`
- schedule: `0 8,14,20 * * *`
- repeat: `{'times': None, 'completed': 0}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `None` / `None`
- next_run: `2026-07-19T08:00:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-queue-worker`
- script: `aiw-queue-worker-task2a.py`
- no_agent: `True`
- skills: `[]`
- enabled_toolsets: `None`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- 无 Hermes Agent 大模型：`no_agent=true`，仅运行脚本 stdout；job.model/provider/model_snapshot 均不参与推理。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

暂停 legacy script-only lane。wrapper -> aiw-queue-worker.py --mode task2a；只允许填充 existing empty draft，当前暂停。

**Hermes prompt**

> 空：该 job 没有 Hermes prompt。若 `no_agent=true`，调度器只运行脚本并把 stdout 原样投递；第三方 review 需要看 script 的行为而不是 prompt。

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-queue-worker-task2a.py`
- common implementation: `/Users/gracker/.hermes/scripts/aiw-queue-worker.py`

### aiw-queue-worker-task2b-main

- job_id: `2435d66a5a42`
- state/enabled: `paused` / `False`
- schedule: `50 0-22/2 * * *`
- repeat: `{'times': None, 'completed': 0}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `None` / `None`
- next_run: `2026-07-18T22:50:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-queue-worker`
- script: `aiw-queue-worker-task2b-main.py`
- no_agent: `True`
- skills: `[]`
- enabled_toolsets: `None`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- 无 Hermes Agent 大模型：`no_agent=true`，仅运行脚本 stdout；job.model/provider/model_snapshot 均不参与推理。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

暂停 legacy script-only lane。wrapper -> aiw-queue-worker.py --mode task2b-main；回炉修复候选筛选，当前暂停。

**Hermes prompt**

> 空：该 job 没有 Hermes prompt。若 `no_agent=true`，调度器只运行脚本并把 stdout 原样投递；第三方 review 需要看 script 的行为而不是 prompt。

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-queue-worker-task2b-main.py`
- common implementation: `/Users/gracker/.hermes/scripts/aiw-queue-worker.py`

### aiw-review-finalize-reader-final

- job_id: `087678486ac8`
- state/enabled: `paused` / `False`
- schedule: `40 1,7,13,19 * * *`
- repeat: `{'times': None, 'completed': 0}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `None` / `None`
- next_run: `2026-07-19T01:40:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-review-finalize`
- script: `aiw-review-finalize-reader-final.py`
- no_agent: `True`
- skills: `[]`
- enabled_toolsets: `None`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- 无 Hermes Agent 大模型：`no_agent=true`，仅运行脚本 stdout；job.model/provider/model_snapshot 均不参与推理。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

暂停 legacy script-only lane。wrapper -> aiw-review-finalize.py --mode reader-final；只扫描候选/报告，不写正文。

**Hermes prompt**

> 空：该 job 没有 Hermes prompt。若 `no_agent=true`，调度器只运行脚本并把 stdout 原样投递；第三方 review 需要看 script 的行为而不是 prompt。

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-review-finalize-reader-final.py`
- common implementation: `/Users/gracker/.hermes/scripts/aiw-review-finalize.py`

### aiw-review-finalize-task2b-verifier

- job_id: `9fbe57241199`
- state/enabled: `paused` / `False`
- schedule: `25 3-23/4 * * *`
- repeat: `{'times': None, 'completed': 0}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `None` / `None`
- next_run: `2026-07-18T23:25:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-review-finalize`
- script: `aiw-review-finalize-task2b-verifier.py`
- no_agent: `True`
- skills: `[]`
- enabled_toolsets: `None`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- 无 Hermes Agent 大模型：`no_agent=true`，仅运行脚本 stdout；job.model/provider/model_snapshot 均不参与推理。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

暂停 legacy script-only lane。wrapper -> aiw-review-finalize.py --mode task2b-verifier；只扫描回流候选/报告。

**Hermes prompt**

> 空：该 job 没有 Hermes prompt。若 `no_agent=true`，调度器只运行脚本并把 stdout 原样投递；第三方 review 需要看 script 的行为而不是 prompt。

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-review-finalize-task2b-verifier.py`
- common implementation: `/Users/gracker/.hermes/scripts/aiw-review-finalize.py`

### aiw-review-finalize-deep-tech-review

- job_id: `46fbf624b429`
- state/enabled: `paused` / `False`
- schedule: `20 0-22 * * *`
- repeat: `{'times': None, 'completed': 2}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-07-18T22:20:26.510049+08:00` / `ok`
- next_run: `2026-07-19T00:20:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-review-finalize`
- script: `aiw-review-finalize-deep-tech-review.py`
- no_agent: `True`
- skills: `[]`
- enabled_toolsets: `None`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- 无 Hermes Agent 大模型：`no_agent=true`，仅运行脚本 stdout；job.model/provider/model_snapshot 均不参与推理。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

暂停 legacy script-only lane。wrapper -> aiw-review-finalize.py --mode deep-tech-review；只扫描深度技术 review 候选/报告。

**Hermes prompt**

> 空：该 job 没有 Hermes prompt。若 `no_agent=true`，调度器只运行脚本并把 stdout 原样投递；第三方 review 需要看 script 的行为而不是 prompt。

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-review-finalize-deep-tech-review.py`
- common implementation: `/Users/gracker/.hermes/scripts/aiw-review-finalize.py`

### aiw-review-finalize-draft-review

- job_id: `59d136a6429d`
- state/enabled: `paused` / `False`
- schedule: `5 1-23 * * *`
- repeat: `{'times': None, 'completed': 2}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-07-18T22:05:25.228867+08:00` / `ok`
- next_run: `2026-07-18T23:05:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-review-finalize`
- script: `aiw-review-finalize-draft-review.py`
- no_agent: `True`
- skills: `[]`
- enabled_toolsets: `None`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- 无 Hermes Agent 大模型：`no_agent=true`，仅运行脚本 stdout；job.model/provider/model_snapshot 均不参与推理。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

暂停 legacy script-only lane。wrapper -> aiw-review-finalize.py --mode draft-review；只扫描 draft review 候选/报告。

**Hermes prompt**

> 空：该 job 没有 Hermes prompt。若 `no_agent=true`，调度器只运行脚本并把 stdout 原样投递；第三方 review 需要看 script 的行为而不是 prompt。

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-review-finalize-draft-review.py`
- common implementation: `/Users/gracker/.hermes/scripts/aiw-review-finalize.py`

### aiw-queue-worker-dispatcher

- job_id: `f0f2cccb04ef`
- state/enabled: `paused` / `False`
- schedule: `5 * * * *`
- repeat: `{'times': None, 'completed': 13}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-07-19T18:05:18.610780+08:00` / `ok`
- next_run: `2026-07-19T19:05:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-queue-worker-dispatcher`
- script: `aiw-queue-worker-dispatcher.py`
- no_agent: `True`
- skills: `[]`
- enabled_toolsets: `None`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- 无 Hermes Agent 大模型：`no_agent=true`，仅运行脚本 stdout；job.model/provider/model_snapshot 均不参与推理。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

暂停 legacy dispatcher。每小时按时间选择 queue-worker due_lanes，依次运行对应 script-only modes，写 evidence/report。

**Hermes prompt**

> 空：该 job 没有 Hermes prompt。若 `no_agent=true`，调度器只运行脚本并把 stdout 原样投递；第三方 review 需要看 script 的行为而不是 prompt。

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-queue-worker-dispatcher.py`
- common implementation: `/Users/gracker/.hermes/scripts/aiw-queue-worker.py`

### aiw-review-finalize-dispatcher

- job_id: `325ea8fa9195`
- state/enabled: `paused` / `False`
- schedule: `10 * * * *`
- repeat: `{'times': None, 'completed': 13}`
- deliver: `telegram:-1004339755728`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-07-19T18:10:18.354452+08:00` / `ok`
- next_run: `2026-07-19T19:10:00+08:00`
- workdir: `/Users/gracker/.hermes/workspaces/aiw-review-finalize-dispatcher`
- script: `aiw-review-finalize-dispatcher.py`
- no_agent: `True`
- skills: `[]`
- enabled_toolsets: `None`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `None` / `None`

**执行大模型**

- 无 Hermes Agent 大模型：`no_agent=true`，仅运行脚本 stdout；job.model/provider/model_snapshot 均不参与推理。
- 未发现脚本自身调用 LLM/API model；执行模型由 Hermes job 层决定，或为纯脚本。

**任务角色 / 设计意图**

暂停 legacy dispatcher。每小时按时间选择 review-finalize due_lanes，依次运行对应 script-only modes，写 evidence/report。

**Hermes prompt**

> 空：该 job 没有 Hermes prompt。若 `no_agent=true`，调度器只运行脚本并把 stdout 原样投递；第三方 review 需要看 script 的行为而不是 prompt。

**脚本复查入口**

- `/Users/gracker/.hermes/scripts/aiw-review-finalize-dispatcher.py`
- common implementation: `/Users/gracker/.hermes/scripts/aiw-review-finalize.py`

## 4. 边界相关但非 AIW 专属任务

### Things backlog triage to Obsidian queues
- job_id: `baf156b5982d`
- state/enabled: `scheduled` / `True`
- schedule: `0 9 * * *`
- repeat: `{'times': None, 'completed': 16}`
- deliver: `telegram:-1003814981550`
- origin: `{'platform': 'telegram', 'chat_id': '1584227965', 'chat_name': 'Xxxxxxx', 'thread_id': None, 'user_id': '1584227965'}`
- last_run/status: `2026-08-08T09:06:43.267952+08:00` / `ok`
- next_run: `2026-08-09T09:00:00+08:00`
- workdir: `None`
- script: `None`
- no_agent: `False`
- skills: `['things-obsidian-task-triage', 'obsidian-hermes', 'gracker-deep-research']`
- enabled_toolsets: `['terminal', 'file']`
- model/provider/base_url: `None` / `None` / `None`
- model_snapshot/provider_snapshot: `grok-4.5` / `xai-oauth`

- 关联点：prompt 要求 triage Things backlog，并搜索/写入 Obsidian 队列，其中会审计 AIW 相关来源/产出闭环。
- 执行大模型：Hermes Agent LLM：model=`default snapshot grok-4.5`；provider=`default snapshot xai-oauth`；base_url=`None`。
- prompt：
```text
每天清理 Things backlog 中的 5 个未完成任务，并把所有有用产物落盘到 Obsidian。你是在 macOS 上运行，Things CLI 为 `/opt/homebrew/bin/things`，Obsidian vault 路径为 `/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian`。严格遵循已加载 skill `things-obsidian-task-triage`。执行步骤：1) 读取 `things today`，选择当前列表前 5 个未完成任务；如果相邻/明显重复项与这 5 个同题，允许一并去重处理，但在报告中说明。2) 按标题前缀分类：`[深度研究]` 写入 `OpenClaw定时任务/Things清理/深度调研任务队列.md`；`[内容动作]` 写入 `内容创作任务队列.md`；`[工程动作]`/`[项目推进]` 写入 `工程与项目任务队列.md`。3) 对每个归一化任务审计来源/产出闭环：搜索 Obsidian 中的每日内容提案、晨间简报、AIW src、metadata/queue.json、DeepResearch、论文目录，记录 source/producer、是否 AIW 闭环、缺什么闭环。4) 所有队列和当日报告必须写入 Obsidian `OpenClaw定时任务/Things清理/`，不要把有用输出只放 `~/.hermes`。iCloud vault 写入使用 `python3 + pathlib`。5) 队列写入成功后勾掉对应 Things 任务：优先 `things update --id ... --completed`；如果 `THINGS_AUTH_TOKEN` 未配置且用户已要求勾掉，先给 Things SQLite `main.sqlite` 做时间戳备份，再只更新已验证 UUID 行为完成（status=3, stopDate/userModificationDate=now），最后用 `things search --status completed` 或 `things today` 验证。6) 最终回复简短说明：处理数量、去重数量、队列路径、Things 勾选验证、当天闭环判断。不要递归创建/修改 cron。
```

## 5. Reviewer 建议重点

1. **并发写文件风险**：6 个 LLM apply/polish lane 的时间错开，但共享同一个 AIW repo。请检查是否存在跨 lane 同时修改同一章节、metadata/queue/source-index 的锁。
2. **script-only 到 LLM 的上下文完整性**：pre-run JSON 是否包含足够材料原文、target excerpt、frontmatter、run_id、formal_report_path；LLM 是否可能凭 excerpt 不足而过度补写。
3. **Git sync 与正文写入分离**：`aiw-git-sync` 每小时 commit/push；LLM lane 不直接 push。请检查失败恢复：LLM 写完但 git sync 失败时的积压与冲突处理。
4. **Feishu sync 的 AIW map 约束**：确认 dry-run/guarded-write 每次从 SUMMARY 重建 list-shape map，防止 AIW / Unmapped。
5. **Android baseline 约束是否可测试**：prompts 明确禁止 Android 18/API38+ 主线结论，但 reviewer 应检查是否有自动 grep/test gate。
6. **Formal output 位置**：规则要求 useful outputs 落 Obsidian formal report；`~/.hermes/state` 只作为 evidence/cache。请检查每条 lane 是否都写正式报告。

## 6. 原始数据定位

- Cron store：`/Users/gracker/.hermes/cron/jobs.json`
- Scripts：`/Users/gracker/.hermes/scripts/`
- AIW repo：`/Users/gracker/.openclaw/workspace/Feishu/work-copies/Android-Internal-Wiki`
- Feishu workspace：`/Users/gracker/.openclaw/workspace/Feishu`
- Formal reports：`/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AIW自动化流水线`

## 7. 独立 Review：最近一周与最近两天的实跑结果

### 7.1 审查口径与路径纠正

本节以实际运行证据为准，交叉检查了 cron 运行记录、Hermes 输出、AIW Git 历史、正文 diff、metadata 队列、流水线脚本、正式报告和 Feishu 同步结果。

- 审查时间：`2026-08-08 23:40 +08:00` 左右。
- 已提交数据截止：AIW `main` 的 `8f1b599d2`，提交时间 `2026-08-08 22:56 +08:00`。
- 另有一轮 `23:36` 的 draft-polish 尚未提交：修改 `5.29-android17-gpu-dvfs-headroom-power-advisor.md`，不计入下面的 33 个提交和 48 次正文文件触达。
- 实际被 Hermes 脚本持续读写的 AIW 主仓库是：`/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki`。
- 本文所在的 `/Users/gracker/.openclaw/workspace/Feishu/work-copies/Android-Internal-Wiki` 是 Feishu 发布工作副本。它在本次检查时停留于 `2026-08-08 08:55` 的 `6e5902b41`，不能作为当天后续流水线的 Git 事实源。
- 因此，第 6 节中的“AIW repo”应理解为 Feishu 发布快照，而不是 Hermes 正文流水线的实际主仓库。

### 7.2 总结判断

这套流水线确实在工作，也确实改出了有价值的内容，不是只改时间戳或空跑。最近两天最有价值的结果包括：删除大段无来源的历史补写、纠正 API/AIDL 版本混淆、收紧结论边界、补充源码定位，以及把一批草稿推进到可复核状态。

但当前“任务成功”不能等同于“正文获得有效改进”。主要原因有四个：

1. 监控把不少真实运行误判成 `no-new-input`，同时把 0 字节 body 输出归为 `other`，成功率数据不可直接使用。
2. 多个 lane 的选择条件和 backlog 统计条件不一致，出现 watchdog 显示有待办、body lane 却连续空跑的情况。
3. Git sync 会收集仓库内所有允许路径的脏改动，无法证明一次提交只包含本轮 agent 的产物；8 月 5 日已经出现一次 280 个正文文件被同一提交扫入的事件。
4. prompt 把“跑过 metadata 检查”当成主要质量门，但当前检查器只验证字段与枚举，不能证明正文结论有足够来源，也不能证明状态晋级合理。

结论：可以继续运行，但应先修正提交边界、选择谓词、监控统计和状态晋级门槛，再考虑增加频率或 lane。只优化措辞，解决不了上述结构性问题。

### 7.3 最近一周：Git 实际改动量

统计窗口为 `2026-08-02 00:00` 至 `2026-08-08 22:56 +08:00`，仅统计提交标题以 `[hermes-aiw]` 开头的提交。

| 日期 | Hermes 提交 | `src/` 文件触达次数 | 去重后的 `src/` 文件 |
|---|---:|---:|---:|
| 08-02 | 0 | 0 | 0 |
| 08-03 | 4 | 6 | 6 |
| 08-04 | 17 | 24 | 17 |
| 08-05 | 17 | 301 | 288 |
| 08-06 | 25 | 33 | 20 |
| 08-07 | 17 | 25 | 18 |
| 08-08（截至 22:56） | 16 | 23 | 18 |
| 合计 | 96 | 412 | — |

按提交标题归类：`review-findings 26`、`polish 20`、`audit 16`、`rework 12`、`deep-review 9`、`review-finalize 5`、`source-route 4`、`body-apply 3`、`intake 1`。

08-05 的数值异常主要来自提交 `9bff1bc77d`：一个名为 polish 的自动化提交实际触达了 280 个 `src/` 文件。这个提交更像“把当时工作区里的大量脏改动统一收走”，不能据此认定 Hermes 在单轮中独立审查并改好了 280 章。

### 7.4 最近两天：是否有实质性正文改动

从 08-07 00:00 到 08-08 22:56：

- 共有 33 个提交，全部为 `[hermes-aiw]`；最后一个非 Hermes 提交在 08-06 22:03。
- 触达 `src/` 文件 48 次，涉及 31 个不同章节。
- 30 次包含正文变化，18 次仅改 frontmatter。
- 22 个不同章节有正文变化，9 个章节只有 metadata/frontmatter 变化。
- 多数正文改动较小，常见为来源标记、边界收紧、术语修正和状态说明，净变化通常在 0 至 4 行。

最明确的一次实质改进是 `a1564913d` 对 `1.46-android17-staged-install-mechanism.md` 的处理：从正文删除约 562 行历史无依据扩写，包括虚构的性能百分比、状态机、配置项和 ML 推断；同时把 Android 16/API 35 的错误对应纠正为 Android 15/API 35。这个结果说明 deep-review/rework 链路有能力发现并清理严重内容问题。

截止审查时尚未提交的 `23:36 draft-polish` 也属于有效修改：它区分了 API 版本与 AIDL 接口版本，修正 `HeadroomCache` 容量语义和 RPC 边界，删除无来源的“90%”数字，收紧 `sendCompositionData`、65Hz 与 OEM 阈值的表述。该轮约为 24 行新增、19 行删除。

其余有效变化大致分为：

- 源码与边界修正：Perfetto data source、CPU DVFS、ADPF、Staged Install、Binder priority、测试实践。
- 草稿推进：Compose Pausable、Infinite Animation、Subcompose、SDK 治理、NetworkQuota、Compose Text 等章节从 draft 进入待复核或 finalized。
- 状态和审计记录：最近两天 18/48 的文件触达仅修改 frontmatter。这些改动有管理价值，但不应计入“正文质量提升”。
- 来源接入与发布：source intake/routing 持续写入索引；Feishu dry-run、guarded write 和 monitor 两天均成功。

### 7.5 六条 LLM lane 的实际产出

下表统计 08-07 至 08-08 23:40 左右的触发记录；draft-polish 包含尚未 Git 提交的 23:36 一轮。

| lane | 触发 | 非空输出 | `materials` 为空 | 实跑判断 |
|---|---:|---:|---:|---|
| body-apply | 18 | 1 | 0/1 | 17 次生成 0 字节输出，只有 1 次实际应用材料 |
| review-finalize | 16 | 16 | 15/16 | 持续工作，但上游材料解析几乎没有供给证据 |
| polish-deep-review | 8 | 8 | 8/8 | 有实质发现，也有状态降级；依赖 agent 自行查本地源码 |
| polish-rework | 8 | 8 | 6/8 | 能修复 finding，但 finding 与修改缺少稳定 ID 关联 |
| polish-idle-audit | 8 | 8 | 6/8 | 很多通过轮只更新时间戳/frontmatter |
| polish-draft | 8 | 8 | 8/8 | 有小幅有效修订，也有仅凭章节现有引用晋级的情况 |

合计 66 次触发，49 次有非空 LLM 输出；49 次中有 43 次的 `materials` 字段为空。空 `materials` 不代表 agent 完全没有查证：抽样中能看到 agent 直接读取本地 AOSP 并记录文件与行号。问题是这类查证没有统一、可机读的证据合同，finalizer 只能从自然语言输出猜测质量是否达标。

六条 lane 两天产生的 cron 输出约 1.77 MB，其中包含重复注入的长 skill、prompt、context 和 response。它不能直接换算 token 成本，但足以说明当前输出协议过重。

### 7.6 Feishu 发布链路

Feishu 链路两天均成功：

| 日期 | 同步 head | map | unmapped | upsert | guarded write | monitor |
|---|---|---:|---:|---:|---:|---|
| 08-07 | `1c7bb9400` | 661 | 0 | 20 | 53 | ok |
| 08-08 | `6e5902b41` | 661 | 0 | 18 | 25 | ok |

这部分没有发现 `AIW / Unmapped` 回归。需要注意的是，Feishu 工作副本是发布时点快照；用它审查当日晚间新改动会漏数据。

## 8. 问题清单与优先级

### P0：Git 提交没有单轮事务边界

证据：`aiw-git-sync.py` 会 stage 当前工作区中所有命中允许目录的脏文件，而不是只 stage 某次 run 声明的文件。它的 freeze guard 主要阻止新增/重命名正文和 SUMMARY 变化，不能阻止大量已跟踪文件被修改或删除。`9bff1bc77d` 一次纳入 280 个正文文件，已经证明风险存在。

影响：提交标题、lane、run_id 与真实 diff 不能一一对应；人工改动或另一条 lane 的改动可能被一起提交。发生大规模误删时，当前 gate 也可能放行。

建议：

1. 每轮生成 manifest，至少包含 `run_id`、`lane`、`base_sha`、`target_path`、`expected_changed_paths`、`actual_changed_paths`、`finding_ids`。
2. 开始前确认当前 HEAD 等于 context 中的 `base_sha`；工作区存在不属于本轮的脏文件时，暂停该轮，不要顺手收走。
3. Git sync 只 stage manifest 中的精确路径，并验证 diff；禁止使用宽目录 allowlist 代替单轮清单。
4. 正文大规模删除、跨多个章节修改、SUMMARY 变化必须进入人工 gate。建议默认阈值：单章删除超过 120 行，或一次修改超过 3 个正文文件，即停止自动提交。
5. commit message 写入 lane 和 run_id。不能证明归属的脏改动不要由自动任务提交。
6. body prompt 当前会在写完后直接调用 git sync，而其他 lane 等到 :55 批量同步。应统一为“LLM 不直接提交”，由带 manifest 的独立 gate 提交；否则至少要做到一次 run 一次原子提交。

### P1：监控口径与真实结果不一致

证据：watchdog 只读取 output 前约 6000 字节，再搜索 `no-new-input`。重复注入的 skill/prompt 本身就包含这个词，所以真实完成的 review/polish 也会被报为 no-new-input；body 的 0 字节输出反而被归为 `other`。当前提交统计也只数 commit 和触达章节，没有区分正文、frontmatter、状态变化或净 diff。

此外，仓库的 GitHub Actions workflow 已在 `07f22668b`（08-06 22:03）被人工删除。此后没有新 CI run；watchdog 仍反复报告历史上的 8 次失败。旧失败发生在 artifact upload 配额，不是正文构建或 metadata 校验失败。body prompt 仍要求等待 `Build & Check` 和 `Knowledge Pack Candidate`，在当前配置下不会得到新的运行结果。

建议：

- watchdog 只解析 `## Response` 后的结构化 JSON，或直接读每轮 evidence 文件；不要扫描完整 prompt 文本。
- 0 字节输出单列为 `empty-output`，与 `no-candidate`、`completed-no-change`、`changed`、`failed` 分开。
- 指标至少增加：正文变化次数、frontmatter-only 次数、状态迁移、净增删行、finding 新建/关闭、材料应用成功率、stuck age。
- CI 状态改成 `enabled / disabled / stale / failing` 四态。workflow 不存在时显示 disabled，不要把历史配额失败当成本轮失败。
- 如果决定长期停用 GitHub Actions，应同步删除 prompt 中等待 CI 的步骤，并用本地可重复 gate 替代。

### P1：backlog、selector 与 watchdog 使用了不同的“可处理”定义

证据：body selector 只要发现 material 的完整路径或 basename 出现在目标章节任意位置，就认为已经应用。`DisplayMode` 相关材料只出现在 frontmatter 的 `gap_source`，也会被跳过。另一方面，watchdog 会把约 9 至 10 条 source-index 记录算作 `apply_pending`，其中不少 `route_confidence` 只有 25/28，是 Agent/社交内容误路由；body 又因低于 30 而跳过。freshness queue 项通常没有 `target_path`，其 material_path 还是章节自身，body 无法建立映射。

结果是：body 连续 17/18 次空输出，但 watchdog 同时报告仍有待应用项。

建议：分类器、body context、watchdog 共用一个 eligibility 函数和同一组状态枚举。每个未处理项都必须带规范化 `target_path`、`material_path`、`route_confidence`、`status`、`rejection_reason`。材料是否已应用只能检查正文中的稳定 source marker 或 material ID，不能因为文件名出现在 frontmatter 就判定完成。

### P1：freshness audit 会制造重复和自我强化的假阳性

证据：`aiw-weekly-source-audit.py` 每次只扫描按路径排序后的前 80 个 Markdown 文件，没有游标，661 章中的后续章节会长期得不到检查。它在包含 frontmatter 和历史 review_notes 的前 20000 字符里搜索 `Android 18|API 38`，无法识别否定句或“不要外推”的边界说明。因此“本文不外推到 Android 18/API 38”也会被当作 freshness 风险。body 再补一句同类免责声明，下轮仍会命中。dedupe key 又包含 `added_at`，同一发现换一天就可能重新入队。README 也可能入队，但 body 明确不处理 README。

建议：

- 只解析正文的有效结论段，排除 frontmatter、review_notes、代码块和显式否定/禁止外推语句。
- 使用持久 cursor 或 coverage map，确保 661 章在一个明确周期内都被覆盖。
- 去重键固定为 `(target_path, rule_id, normalized_evidence)`，不要包含时间。
- freshness 项必须给出原句、规则 ID、是否为肯定结论、目标路径和处置状态。
- 不可被 body 处理的 README/索引项应路由到专用 lane，不能留在正文 apply backlog。

### P1：finalized 与“有证据”之间缺少机器可判定的合同

`check-metadata.py` 当前主要检查必填键和枚举。`last_verified`、confidence、sources 等很多问题只是 warning 且退出码仍为 0；它也不验证引用能否支持具体 claim。最近两天多个 lane 在 `materials: []` 时仍然推进状态，说明“脚本通过”不足以证明可 finalized。

建议：ready-for-review/finalized 使用更严格的状态门：

- 每个关键结论绑定 `claim_id` 与 `source_evidence`，证据至少包含仓库/tag、文件、symbol 或行区间、支持的 claim。
- 不允许存在未关闭的 P0/P1 finding。
- 状态迁移必须符合显式状态机，降级要带 finding ID，重新晋级必须关闭同一 finding ID。
- `last_verified` 拆成 `last_audited_at` 与 `last_source_verified_at`。只做文本扫描或 frontmatter 审计时，不得刷新 source verified 时间，也不得提高 confidence。
- 大幅删除、关键版本变化和无法本地验证的事实应要求人工确认或明确风险豁免。

### P1：通过型 idle audit 强制制造无信息提交

idle-audit prompt 一方面要求不要为改而改，另一方面又要求每次更新 frontmatter。于是“没有发现问题”也会制造一次文件修改和后续提交，最近两天的 18 次 frontmatter-only 触达中有相当一部分来自这类审计。

建议：通过时只写独立 audit evidence，不改章节；只有发现问题、关闭 finding 或获得新的来源证据时才改正文/frontmatter。把审计时间放在外部 ledger，而不是用触碰章节文件表示“巡检过”。

### P2：正式报告会被同日后续运行覆盖

formal report 路径只包含日期和 lane，例如 `2026-08-08-aiw-polish-deep-review.md`。同一 lane 每天运行多次，后一次会覆盖前一次，无法形成可追溯的运行历史。

建议：文件名加入 `HHMMSS-run_id`，或采用按日 append 的不可变条目，并维护一份 latest 索引。prompt 不应把一个会被覆盖的文件称为永久证据。

### P2：所有 LLM lane 重复注入了不相干的通用 skill

六条 lane 都注入 `scheduled-obsidian-output-task`。其中包含“一项业务只保留一个 enabled cron”、社交发布、任务合并等与 AIW 章节审查无关的规则，甚至与当前多 lane 设计冲突。两天 cron output 约 1.77 MB，大量内容是重复的 skill 和 prompt。

建议：移除这六条任务的通用 skill，或换成一份短小的 `aiw-review-lane-contract`，只保留路径、状态机、证据、diff 范围、响应 schema 和禁止提交规则。通用工作流治理不应在每次章节 review 时重复注入。

### P2：intake/classifier 的噪声被推迟到下游处理

08-07/08 的候选中出现 Agent 插件、社交内容等与 AIW 正文关系很弱的材料，并被低分路由到 ch05/ch08/ch16。后续 confidence 阈值和 quarantine 暂时保护了正文，但 source-index 和 watchdog backlog 被污染。daily intake 两天都输出 `{}`，任务仍标记 ok，无法区分“确实无新增”和“脚本没有产出有效统计”。

建议：分类器先做域过滤，再做章节路由；低于阈值的项进入明确的 rejected/quarantine 状态，不进入 apply_pending。intake 即使无新增，也应返回扫描数、新增数、去重数、拒绝数和原因分布。

## 9. Prompt 修改建议

以下建议可以直接交给负责修改任务的 agent。先统一六条 lane 的合同，再处理各 lane 的个别差异。

### 9.1 六条 lane 共用合同

建议在 prompt 开头加入：

```text
你只处理 pre-run JSON 指定的一个 target_path。开始前记录 run_id、lane、base_sha、target_path 和允许修改的路径；HEAD 与 base_sha 不一致，或工作区存在不属于本轮的脏改动时，返回 blocked，不得吸收、覆盖或提交这些改动。

只允许修改 target_path，以及本轮唯一的 evidence/report 文件。不要执行 git add、commit、push、pull、rebase、autostash 或 aiw-git-sync.py。提交由独立的事务 gate 完成。

任何状态降级必须创建稳定 finding_id；任何重新晋级必须关闭对应 finding_id，并列出验证证据。不能因为脚本 exit 0、已有引用数量较多、或没有发现新问题，就自动提高状态。

只有实际核对过源码/官方文档后，才能更新 last_source_verified_at 或提高 confidence。普通巡检只写 last_audited_at 到外部 evidence，不触碰章节。

结束时返回一个简短 JSON：run_id、status、target_path、body_modified、frontmatter_modified、changed_paths、findings_opened、findings_closed、source_evidence、verification、blocked_reason。不要在 Response 中重复 prompt、skill 或大段正文。
```

### 9.2 body-apply

补充约束：

```text
“材料已应用”必须由正文中的稳定 material_id/source marker 或等价 claim 证明。材料文件名只出现在 gap_source、review_notes 或其他 frontmatter 字段时，不算已应用。

若没有可处理 candidate，返回 status=no-candidate，并列出 scanned、ineligible、rejected_by_reason；不要生成 0 字节输出。

应用后只把章节推进到 ready-for-review，不得自行 finalized，不得直接调用 git sync。列出新增/修改的 claim 与对应 source_evidence。
```

### 9.3 review-finalize

补充约束：

```text
finalized 的必要条件：没有 open P0/P1 finding；关键 claim 都有可定位 source_evidence；版本边界已验证；本地 gate 全部通过。materials 为空时，可以自行查本地源码，但必须把查证结果结构化记录；无法形成证据时保持 ready-for-review 或转 needs-rework。

不要把“引用看起来足够”“metadata 检查通过”或“正文没有明显问题”单独作为 finalized 依据。
```

### 9.4 deep-review

补充约束：

```text
先产出 finding，再决定是否修改。每个 finding 包含 finding_id、severity、claim、evidence、target_range、recommended_action。仅出现“待验证”、Android 18/API 38 字样或历史 review note，不足以降级；必须证明正文存在一个仍生效且不受支持的肯定结论。

大段删除前先给出删除范围、原因和保留信息摘要；超过自动阈值时返回 needs-human-review。
```

### 9.5 rework

补充约束：

```text
只处理 context 中明确列出的 finding_id。每项修改必须说明关闭了哪个 finding，未能关闭的 finding 保持 open。不要顺带重写同章其他内容，不要用“清理了措辞”代替证据。
```

### 9.6 idle-audit

建议把当前强制更新 frontmatter 的条款删除，替换为：

```text
若审计通过且没有新证据、finding 或正文变化，返回 completed-no-change，只写独立 audit evidence，不修改章节文件。不得仅为刷新时间戳而提交。
```

同时降低频率或改为分片抽样，避免与 deep-review/finalize 在数小时内重复检查同一章。

### 9.7 draft-polish

补充约束：

```text
draft 只有在结构完整、关键 claim 有证据、没有 unresolved marker、版本边界明确时才能推进到 ready-for-review。materials 为空并不自动阻止修改，但不能仅凭章节已有引用数量晋级；必须列出实际验证过的 claim。

术语润色与事实修改分开报告。没有事实变化时，不更新 source verified 时间或 confidence。
```

## 10. 需要脚本配合的改造

以下事项不能只靠 prompt 保证：

1. 实现 per-run manifest、base SHA 校验、精确 stage 和大 diff 人工 gate。
2. 让 classifier、body selector、watchdog 共用 eligibility 与状态枚举。
3. 修复 freshness audit 的正文解析、否定识别、稳定去重键和覆盖游标。
4. watchdog 解析结构化 Response/evidence，不再搜索输出前 6000 字节。
5. metadata gate 增加 status-dependent 校验、finding 状态和 source evidence 完整性检查。
6. formal report 文件名加入时间与 run_id，避免覆盖。
7. 明确 CI 当前是 disabled，或者恢复一套不会因 artifact quota 阻塞的本地/远端 gate。
8. 把 `last_audited_at` 与 `last_source_verified_at` 分开存储。

## 11. 修改后的验收标准

建议负责修改的 agent 至少用以下场景回归：

- 同一个材料名只存在于 frontmatter 时，body 仍能识别为未应用。
- watchdog 有待办时，body selector 对同一条目也判定可处理；不可处理时双方显示同一个 rejection reason。
- 一轮无候选返回结构化 `no-candidate`，不再生成 0 字节“成功”记录。
- 否定句“不要外推到 Android 18/API 38”不会进入 freshness backlog。
- 661 章能在明确周期内全部被 freshness audit 覆盖。
- idle audit 通过时不修改章节。
- `materials: []` 且没有独立 source evidence 时不能 finalized。
- 工作区预先放置一处人工改动后，自动 sync 会阻止本轮提交，而不是把它一起收走。
- 单章删除超过阈值或一次触达多个正文文件时进入人工 gate。
- workflow 不存在时 watchdog 显示 CI disabled，不再报告历史失败为当前失败。
- 同一天多次运行会生成不同的 report/evidence 文件。
- 每个 Git 提交可以从 run_id 反查到唯一 manifest、target、finding 和验证结果。

完成这些修正后，再观察至少 48 小时。评估时不要只看 cron 的 `ok` 数量，建议看四个结果指标：有效正文改动率、finding 关闭率、frontmatter-only 比例、从入队到完成的 p50/p95 时长。


---

## 修复执行记录 · 2026-08-09 00:35

### 处理结论

已确认第三方 Review 中列出的核心问题成立，并按 P0/P1 优先级完成修复。修复范围覆盖 Hermes AIW 任务脚本、六条 LLM lane prompt、git-sync 事务边界、selector/watchdog 口径、freshness audit、以及 Android 版本上限约束。

### 已修复问题

1. **P0：Git sync 缺少单轮事务边界**
   - 新增 `/Users/gracker/.hermes/scripts/aiw_pipeline_common.py`，统一 per-run manifest、`base_sha`、`expected_changed_paths`、状态落盘和路径归一化。
   - `aiw-body-apply-context.py`、`aiw-review-finalize-context.py`、`aiw-polish-context.py` 现在都会生成 `run_id/base_sha/manifest_path/allowed_changed_paths/formal_report_path`。
   - `aiw-git-sync.py` 改为 manifest gate：只 stage 本轮 manifest 允许的路径；发现非本轮 dirty path、HEAD 不一致、缺 manifest 或大 diff 时 blocked / needs-human-review。
   - 禁止 LLM lane 自己运行 `git add/commit/push/pull/rebase/autostash` 或调用 `aiw-git-sync.py`；提交由独立 sync lane 执行。

2. **P1：selector 与 watchdog 口径不一致 / frontmatter 文件名误判**
   - `source_index_eligibility()` 统一 source-index eligibility：排除 quarantined、低置信 route、已 rejected/duplicate/superseded/applied 的素材。
   - `material_applied_in_body()` 只把正文稳定 `[来源: ...]` / `[已验证: ...]` / material marker 视为已应用；frontmatter 中 `gap_source` / `review_notes` 出现文件名不再算已应用。
   - `aiw-throughput-watchdog.py` 改用同一 eligibility 口径，并把 frontmatter-only 与 body material changes 分开统计。

3. **P1：监控误判**
   - cron output 分类改为读取 response/evidence tail，避免 prompt 中的 `no-new-input` 文本污染统计。
   - CI 状态现在先检查 `.github/workflows`；无 workflow 时明确 `disabled`，不再误判远端历史 run。

4. **P1：finalized / ready-for-review 证据门槛不足**
   - 六条 LLM lane prompt 已全部改为明确证据合同：不能因为脚本 exit 0、引用数量多、metadata 检查通过或“未发现明显问题”而晋级。
   - finalized 必须满足：无 open P0/P1 finding、关键 claim 有可定位 source evidence、版本边界已验证、本地 gate 通过。
   - 状态降级/重新晋级必须绑定稳定 `finding_id` 与 `source_evidence`。

5. **P1：idle-audit churn**
   - idle-audit prompt 改为：审计通过且无新证据/finding/正文变化时返回 `completed-no-change`，只写独立 audit evidence/log，不修改章节、不刷新 frontmatter、不提交。

6. **P1：freshness audit 误报与重复队列**
   - freshness audit 现在剥离 YAML/frontmatter、代码块和历史 review/audit 段落后再检查正文。
   - 高于 Android 17 的版本命中采用否定语境识别，避免“不得/禁止/未纳入”等边界说明被当成正文越界 claim。
   - 新增 cursor 覆盖状态 `metadata/freshness-cursor.json`，不再每次只扫固定前 N 个文件。
   - 队列去重改为稳定 key：`target_path + rule_id + evidence`。

7. **全局 Android 版本上限**
   - 所有 AIW/Android 相关 Hermes scripts 与 cron prompt 已锁定为：最高只到 **Android 17 这个平台版本**，不是 SDK 17。
   - 已清理 active `.hermes/scripts/*.py` 与 `/Users/gracker/.hermes/cron/jobs.json` 中的 `Android 18`、`API38/API 38`、`API37/API 37`、`SDK 17/sdk17` 触发文本；prompt 统一表达为“Android 17 / 高于 Android 17 的内容跳过”。

### 已验证

- `python3 -m py_compile` 通过：
  - `aiw_pipeline_common.py`
  - `aiw-body-apply-context.py`
  - `aiw-review-finalize-context.py`
  - `aiw-polish-context.py`
  - `aiw-git-sync.py`
  - `aiw-throughput-watchdog.py`
  - `aiw-weekly-source-audit.py`
  - `aiw-daily-intake.py`
  - `aiw-queue-worker.py`
  - `aiw-review-finalize.py`
  - `content-topic-plan-collect.py`
  - `paper_pipeline_single_task.py`
  - `content-topic-plan-pipeline-selftest.py`
  - `content-topic-plan-finalize.py`
- `aiw-body-apply-context.py` 输出为完整可解析 JSON：`status=candidate_ready`，含 `run_id/base_sha/manifest_path`。
- `aiw-polish-context.py --mode idle-audit` 输出为完整可解析 JSON：`status=polish_candidate_ready`，含 `run_id/base_sha/manifest_path`。
- `aiw-review-finalize-context.py` 输出为完整可解析 JSON：`status=review_candidate_ready`，含 `run_id/base_sha/manifest_path`。
- `aiw-weekly-source-audit.py --mode freshness-check --dry-run --scan-limit 5` 通过：`scanned=5, risks=0`。
- selector 回归：frontmatter-only material path 不算 applied；正文 `[来源: foo.md]` 才算 applied；低置信 route 被拒绝；有效 route 通过。
- `aiw-throughput-watchdog.py` 通过并写入 health report，CI 正确显示 `disabled`。
- `aiw-git-sync.py` 在无 AIW repo dirty paths 时正常 no-op / ff-only 同步。
- 扫描 active scripts 与 cron prompts，未发现 `Android 18`、`API38`、`API 38`、`android-18`、`Android18`、`API37`、`API 37`、`SDK 17`、`sdk17` 残留。

### 未执行

- 未自动运行六条 LLM lane 的真实写正文任务，避免在修复任务设计时产生新的 AIW 正文变更。
- 未 commit / push 本审查文档；当前仍为未提交文件。
