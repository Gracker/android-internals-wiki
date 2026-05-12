# AIW 自动 Review 任务报告

## 一、目标发现结果
- **扫描范围**：`src/part1-fundamentals/ch01-architecture/`
- **候选章节**：
  1. 08-activity-manager.md | AMS 是系统核心，Android 17 (Baklava) 有重大 ADJ 调整。
- **最终选择**：08-activity-manager.md
- **选择理由**：AMS 是调度的“心脏”。Android 17 对进程优先级进行了精细重构，引入了 225 等新档位；Android 16 则实装了 ModernBroadcastQueue。这些变化对 ANR 归因至关重要。

## 二、总体结论
- **总体技术评分**：4.5/5
- **是否建议回炉**：是
- **主要风险**：缺失对 **Android 17 (Baklava)** 新增 ADJ 档位描述；对 **ModernBroadcastQueue** 按进程排队机制描述不足；未提及 **getStartComponent()** 启动归因。
- **评分理由**：原理解析极佳，但版本前瞻性需同步 API 36/37 的最新变更。

## 三、六维评分
| 维度 |评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 5.0/5 | 0 |
| 原理链完整性 | 4.5/5 | 1 |
| 版本差异覆盖 | 3.5/5 | 2 |
| 知识盲区 | 4.5/5 | 1 |
| 数据/案例支撑 | 4.5/5 | 1 |
| 交叉引用一致性 | 5.0/5 | 0 |

## 四、P1 问题（重要缺失）
- **[P1][版本差异][oom_adj 章节]**
  - **缺失内容**：Android 17 (Baklava) 新增 ADJ 档位。
  - **技术事实**：引入 PERCEPTIBLE_MEDIUM_APP_ADJ (225) 和 CACHED_APP_LMK_FIRST_ADJ (950)。
  - **建议补充方向**：更新对照表。

- **[P1][原理链完整性][广播管理章节]**
  - **缺失内容**：ModernBroadcastQueue 架构。
  - **技术事实**：广播进化为按进程组织的队列，解决了“队头阻塞”问题。
  - **建议补充方向**：修正分发机制描述。

- **[P1][知识盲区][启动耗时分析章节]**
  - **缺失内容**：getStartComponent() 归因。
  - **技术事实**：Android 16 可精确区分冷启动是由哪种组件（Activity/Service/Receiver/Provider）触发。
  - **建议补充方向**：加入该 API 作为归因手段。

## 五、P2 问题（建议改进）
- **[P2][源码准确性][AMS 锁拆分]**
  - **建议**：提及 OomAdjusterLock 等细粒度锁对 Binder 线程池饱和的缓解。

## 六、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|------|-------|
| 广播异步处理超时 | 中 | 进程队列下的弹性时长计算 |
| ADJ 225 触发点 | 高 | 系统绑定的优先级分级 |

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：1.8 Activity Manager Service 与性能分析
- **严重级别**：P1
- **位置**：ADJ 表格与广播管理小节
- **问题描述**：未反映 Android 16/17 最新架构演进。
- **建议修正方向**：同步 Baklava ADJ 列表与 ModernBroadcastQueue 机制。

### 9.4 可复用知识资产
- **性能锚点**：`ApplicationStartInfo.getStartComponent()`。
- **核心逻辑**：ModernBroadcastQueue 实现了广播分发的“进程级隔离”。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch01-08-activity-manager-external-review.md`
