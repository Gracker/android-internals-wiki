# 研究日志 2026-03-30 15:00 — VSync 机制

## 研究方向
2.3 VSync 机制（queue.json priority 75，最高优先级 pending 章节，此前 0 篇素材）

## 搜索层级
- L1 ✓: AOSP cs.android.com / googlesource.com — DispSync.cpp, EventThread.cpp, SurfaceFlinger.cpp, Choreographer.java
- L2 ✓: source.android.com 架构文档, developer.android.com API 文档
- L3 ✓: Medium 技术文章, GitHub 博客
- L4 ✓: StackOverflow 高票回答

## 候选素材: 8 条 | 通过评分: 4 条 | 投递: 4 条

### 投递列表

| # | 标题 | 评分 | 映射 |
|---|------|------|------|
| 1 | Android VSync/DispSync 管线架构 | 20/20 | 2.3 全锚点 |
| 2 | Vsync-AppSF & EventThread 重构 | 17/20 | 2.3, 2.9 |
| 3 | Android 15/16 ARR + VSync 演进 | 18/20 | 2.3, 2.9 |
| 4 | DispSync VsyncModel + WorkDuration | 19/20 | 2.3 |

## 关键发现摘要
1. DispSync 是软件锁相环，通过 HW_VSYNC_0 时间戳构建内部模型生成周期性回调
2. Android 13 引入 vsync-appSf 解决 sf EventThread 双重职责问题
3. Android 15/16 ARR 使用离散 VSync 步进动态匹配内容帧率
4. AOSP main 分支用 WorkDuration/VsyncConfiguration 替代 legacy PhaseOffsets

## 联动更新
- queue.json: 2.3 material_paths 已更新（4 篇素材）
- suggestions: 建议将 2.9 priority 从 70 → 75（ARR 素材同时映射）
