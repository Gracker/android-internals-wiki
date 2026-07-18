# AIW Knowledge Pack 维护说明

Knowledge Pack 是从私有 Android Internals Wiki 仓库生成的公开、只读、版本化
知识快照。`src/` 下的正文 Markdown 全部进入候选语料，草稿、待审、定稿、
deprecated、queue 中的正文一视同仁。工作流状态只进入聚合审计，不发送给模型，
也不作为收录门槛。

各级 `README.md`、`SUMMARY.md` 和 `src/graphify-out/**` 是导航或生成产物，不属于
正文。公开仓库只接收经过安全投影的正文片段、聚合审计、许可证和 TUF 元数据：
本机绝对路径所在行会被确定性脱敏，高置信密钥命中会阻断构建；私有源仓库、queue、
review notes、日志、原始绝对路径和 Git remote 都不会进入 Pack。

合法 frontmatter 只投影白名单内的公开字段。缺少 frontmatter 时从一级标题和路径生成
稳定元数据；YAML 损坏但分隔符闭合时丢弃损坏元数据后保留正文；分隔符未闭合时只有
找到明确的一级正文标题才从该标题起收录，否则失败关闭。SQLite 中的文章哈希和公开
内容 fingerprint 只基于这份公开投影，不基于脱敏前原文或工作流状态。
`distribution.smartperfetto.projection_revision` 是构建格式的显式重发开关：仅修复
SQLite、FTS、压缩或公开投影算法且正文投影未变化时，必须递增它，避免稳定发布被
相同内容 fingerprint 判定为 no-op。

## 自动流程

候选 CI 在影响 Pack 的 push 和 pull request 上运行：

1. 安装 `requirements.txt` 中锁定的依赖；
2. 运行构建器和 TUF 单元测试；
3. 按 `policy.yaml` 收录全部正文并生成公开安全投影；
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
