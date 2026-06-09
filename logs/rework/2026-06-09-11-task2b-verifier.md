# Task2B Verifier · 回流复查 · 2026-06-09 11:28

## 复查范围

### Phase 1: task6_state=revisiting 残留修正（12 章）

以下章节已 finalized/ready-to-publish，但 task6_state 仍为 revisiting（前轮 verifier 修正了 pipeline_stage 但遗漏了 task6_state）：

1. 14.4 dumpsys 系列命令
2. 19 / 16 APM profiling-manager
3. 8.5 响应速度案例研究
4. 9.4 特殊 ANR
5. 2.4 Choreographer
6. 2.11 Flutter 渲染管线
7. 2.18 自适应刷新率
8. 6.2 文件系统
9. 4.3 ART 内存模型
10. 3.9 输入延迟预算与感知
11. 22.6 图片加载
12. 22.8 帧监控

修正：task6_state → "reviewed"。

### Phase 2: frontmatter 值污染清理（23 章）

前轮 verifier 在修改 YAML 值时追加了行内注释（如 `# updated by task2b-verifier`），
导致 YAML 值被污染（如 `reviewed  # updated by task2b-verifier 2026-06-08`）。
部分更严重：pipeline_stage 值后跟了 task6_state/task9_state 等新键值（如
`ready-to-publish  # promoted by task2b-verifier 2026-06-08task6_state: reviewed`）。

涉及字段：pipeline_stage, task6_state, task9_state。
修正：清理为纯 YAML 值（如 `"reviewed"`, `"ready-to-publish"`）。

## 统计
- 状态修正：35（12 revisiting + 23 污染清理）
- 阻塞：0
- 结果：no-change（无章节需要回流 Task6；所有 fixed 章节均已正确 finalized 或在 task9_pending 流程中）
