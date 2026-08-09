# Hermes AIW pipeline snapshot

这是当前机器上 Hermes AIW 自动化的可审查快照，用于 Git diff、代码复审和故障回滚。

- 实际运行入口仍是 `/Users/gracker/.hermes/scripts/` 与 `/Users/gracker/.hermes/cron/jobs.json`。
- `scripts/` 保存所有 `aiw-*.py` / `aiw_*.py` 文件的逐字节快照。
- `jobs.aiw.redacted.json` 保存 AIW 相关任务的 schedule、prompt、model、script 等配置，不保存 deliver endpoint。
- `manifest.json` 记录 SHA-256、文件大小、生成时间和 Android 17 / API 37 平台上限。
- 更新 live 脚本或 prompt 后，运行 `python3 scripts/snapshot-hermes-aiw-pipeline.py` 刷新快照，再随 AIW 变更一起提交审查。

快照不是第二套运行目录，不应直接由 cron 执行。
