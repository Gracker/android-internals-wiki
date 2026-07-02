# OpenClaw 错误处理指南

## 元数据备份

每个 Task 执行前，可备份关键元数据。备份只用于短期恢复，不进入长期治理口径：

```bash
BACKUP_DIR="metadata/.backups/$(date +%Y-%m-%d-%H%M)"
mkdir -p "$BACKUP_DIR"
cp metadata/inventory.json metadata/queue.json metadata/progress.json "$BACKUP_DIR/"
```

清理规则：

- `metadata/.backups/.gitkeep` 保留，具体备份目录不提交。
- 30 天以上备份应移入系统废纸篓或由 git 可恢复的删除提交清理，不用不可恢复的 `rm -rf`。
- 单文件临时备份如 `metadata/queue.json.bak`、`metadata/progress.json.backup`、`metadata/*.tmp` 不应作为恢复链长期保留。

## 错误分类与处理

### 可自动恢复的错误
| 错误 | 处理方式 |
|------|---------|
| 网络超时（查官方文档） | 标注 `[待验证]`，继续加工 |
| AOSP 源码路径失效 | 标注路径变更，尝试搜索新路径 |
| Obsidian 文件编码异常 | 跳过该文件，记录到错误日志 |
| JSON 解析失败 | 从最近备份恢复 |

### 需要人工介入的错误
| 错误 | 处理方式 |
|------|---------|
| 同一小节加工 >2 次被驳回 | 标记为「需高爷直接处理」 |
| 多个来源严重矛盾 | 标注 `[争议]`，记录到 intake/suggestions.md |
| 素材涉及版权争议 | 停止加工，等待高爷确认 |
| Git 冲突 | 停止提交，等待人工解决 |

## 错误日志

所有错误记录到 metadata/error-log.json，格式：
```json
{
  "entries": [
    {
      "timestamp": "2026-03-28T12:00:00Z",
      "task": "task2",
      "error_type": "verification_timeout",
      "chapter": "2.3",
      "message": "L2 验证超时：developer.android.com 请求 >30s",
      "action_taken": "标注 [待验证]，继续加工",
      "resolved": false
    }
  ]
}
```

## 监控告警规则

| 指标 | 阈值 | 动作 |
|------|------|------|
| 草稿驳回率 | > 30%/周 | 暂停加工，检查 prompt 质量 |
| 待审核堆积 | > 10 篇 | 提醒高爷集中审核 |
| 未验证知识点 | > 50%/篇 | 检查验证流程是否正常 |
| JSON 备份失败 | 任何一次 | 立即告警 |
