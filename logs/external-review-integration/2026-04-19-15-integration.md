# External Review Integration Log — 2026-04-19 15:34

## 扫描结果
- 活跃文件：10 个
- 已消费（重复）：4 个（7.0, 7.13, 9.0, 11.0 — 内容已在 queue 中从不同源文件写入）
- 本轮新增整合：6 个

## 新增整合详情

### 12.0 APK 体积优化与网络性能 (README)
- **来源文件**：2026-04-19-14-12.0-external-review.md
- **评分**：0/5（空壳章节）
- **queue.json**：新增 1 条 (P95)
- **research-gaps.md**：新增 1 条（aapt2/HTTPDNS/Perfetto/PMS 交互）
- **suggestions.md**：新增 1 条（资料未消化）

### 18.9 Vulkan 原生渲染链路
- **来源文件**：2026-04-19-14-18.9-external-review.md
- **评分**：2.0/5
- **queue.json**：新增 1 条 (P95)，含 P0 (vkQueuePresentKHR 边界误解) + 3xP1
- **research-gaps.md**：新增 1 条（IPC 阻塞风险 + Frame Pacing 映射）
- **suggestions.md**：新增 2 条（IMMEDIATE 降级 + 数据支撑不足）

### 18.10 SurfaceControl API
- **来源文件**：2026-04-19-14-18.10-external-review.md
- **评分**：3.0/5
- **queue.json**：新增 1 条 (P95)，含 P0 (Buffer 回收机制错误) + 2xP1
- **research-gaps.md**：新增 1 条（跨进程 ASurfaceControl + VsyncId 溯源）
- **suggestions.md**：新增 1 条（deprecated API + BufferDataSpace）

### 18.11 ANGLE (GLES->Vulkan 翻译层)
- **来源文件**：2026-04-19-14-18.11-external-review.md
- **评分**：3.0/5
- **queue.json**：新增 1 条 (P95)，含 P0 (queryAngleChoice 不存在) + 3xP1
- **research-gaps.md**：新增 1 条（Shader Cache + 分层决策树）
- **suggestions.md**：新增 2 条（trace marker 区分 + a4a_rules 严谨性）

### 18.12 Flutter 渲染链路
- **来源文件**：2026-04-19-14-18.12-external-review.md
- **评分**：3.5/5
- **queue.json**：新增 1 条 (P85)，含 3xP1
- **research-gaps.md**：新增 1 条（VSync 拍频错位 + Layer 分配）
- **suggestions.md**：新增 1 条（Perfetto SQL 查询补充）

### 18.13 WebView 渲染链路
- **来源文件**：2026-04-19-14-18.13-external-review.md
- **评分**：3.5/5
- **queue.json**：新增 1 条 (P95)，含 P0 (SurfaceControl 误判) + 2xP1
- **research-gaps.md**：新增 1 条（Viz 线程追踪 + DrawFn）
- **suggestions.md**：新增 1 条（线程命名对应）

## 跳过的重复文件（已在 queue 中）
- 2026-04-19-10-7.0-external-review.md → queue 已有 section 7.0
- 2026-04-19-10-7.13-external-review.md → queue 已有 section 7.12
- 2026-04-19-11-9.0-external-review.md → queue 已有 section 9.0/9.1
- 2026-04-19-12-11.0-external-review.md → queue 已有 section 11.1

## 非标准文件（跳过）
- TODO-part2-performance.md（规划文件，非 review 结果）
- ch01-review-todo.md（规划文件）
- part1-fundamentals-todo.md（规划文件）
- part2-performance-todo.md（规划文件）
- batch_review_log.txt（非 .md 格式）

## 写入统计
- queue.json：新增 6 条
- research-gaps.md：新增 6 条
- suggestions.md：新增 8 条

## 去重说明
- Section 7.0/7.12/9.0/9.1/11.1 已有 external-ai-review 条目，本轮跳过不重复写入
- 12.0 章节整体空壳问题与 12.1/12.3/12.4 子章节问题互补不冲突
- 18.9-18.13 为全新章节，无去重冲突

## 可复用知识资产（保留在 external-review 文件本体）
- 18.9：vkQueuePresentKHR 的 CPU 侧 queueBuffer 调用链 + Semaphore→Fence FD 转换
- 18.10：API 29-35 getPreviousReleaseFenceFd 回收标准路径 + API 36 setBufferWithRelease 升级
- 18.11：ANGLE 分层决策树（全局 > 包级别 > Game Mode > 平台 rules）
- 18.12：FlutterSurfaceView/FlutterTextureView/VsyncWaiter 关键类锚点
- 18.13：WebViewSurfaceControl Child Surface 独立提交机制 + Viz Display Compositor 角色
