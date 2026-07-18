# AIW Knowledge Pack 维护说明

Knowledge Pack 是从私有 Android Internals Wiki 仓库生成的公开、只读、版本化
知识快照。公开仓库只接收严格入选的正文片段、聚合审计、许可证和 TUF
元数据，不接收草稿、queue、review notes、日志、绝对路径或 Git remote。

## 自动流程

候选 CI 在影响 Pack 的 push 和 pull request 上运行：

1. 安装 `requirements.txt` 中锁定的依赖；
2. 运行构建器和 TUF 单元测试；
3. 按 `policy.yaml` 失败关闭地筛选文章；
4. 构建 SQLite FTS5 数据库并运行完整校验和黄金查询；
5. 上传保留 7 天的候选 artifact；push 构建附加 provenance attestation。

稳定发布任务每天北京时间 00:30（UTC 16:30）运行。它重新 checkout 当前
master 的确定 SHA 并从头构建，不复用候选 artifact。发布器先比较公开内容
fingerprint：

- 内容未变化：成功 no-op，不创建空版本；
- 内容变化：使用 UTC 日期生成 `YYYY.MM.DD.N`，同日从 `0` 递增；
- 已存在的版本和目标文件永不覆盖；
- 更新 delegated targets、snapshot、timestamp 后一次 Git commit 推送；
- 推送后从不可变 commit URL 启动空缓存 TUF 客户端做下载和检索 canary。

## 本地统一入口

先创建 Python 虚拟环境并安装锁定依赖：

```bash
python3 -m venv .venv-knowledge-pack
.venv-knowledge-pack/bin/pip install -r knowledge-pack/requirements.txt
```

只构建、验证和计算版本，不修改公开仓库：

```bash
AIW_PACK_PYTHON=.venv-knowledge-pack/bin/python \
  scripts/update_knowledge_pack.sh \
  --dry-run \
  --public-repo /path/to/android-internals-knowledge-pack
```

向已 checkout 的公开仓库写入 TUF 目标和元数据：

```bash
AIW_PACK_PYTHON=.venv-knowledge-pack/bin/python \
  scripts/update_knowledge_pack.sh \
  --publish \
  --public-repo /path/to/android-internals-knowledge-pack \
  --keys-dir /secure/path/to/online-role-keys
```

紧急撤回只更新签名 channel，不删除历史目标：

```bash
AIW_PACK_PYTHON=.venv-knowledge-pack/bin/python \
  scripts/update_knowledge_pack.sh \
  --publish \
  --public-repo /path/to/android-internals-knowledge-pack \
  --keys-dir /secure/path/to/online-role-keys \
  --revoke 2026.07.18.0 \
  --minimum-safe-version 2026.07.19.0 \
  --reason-code content-safety
```

`--version YYYY.MM.DD.N` 只用于受控重发；正常发布由脚本自动计算版本。
`--allow-dirty` 只允许本地 dry-run，发布模式会拒绝。

## 密钥与 GitHub Secrets

`bootstrap_knowledge_pack_repository.py` 一次性生成五个 Ed25519 role key：

- `root.pem`、`targets.pem` 必须离线保存，不进入 GitHub；
- `nightly.pem`、`snapshot.pem`、`timestamp.pem` 分别写入
  `AIW_TUF_NIGHTLY_KEY`、`AIW_TUF_SNAPSHOT_KEY`、
  `AIW_TUF_TIMESTAMP_KEY`；
- `AIW_PACK_DEPLOY_KEY` 是只对公开分发仓库具有写权限的 deploy key。

私钥目录必须位于 Git 仓库外，权限为 `0700`；私钥文件权限为 `0600`。
root 和 top-level targets 轮换是离线维护操作，不由每日 workflow 执行。
