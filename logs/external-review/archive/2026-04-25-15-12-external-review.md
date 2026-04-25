# AIW 自动 Review 任务报告 (19.12)

## 一、目标发现结果
- 扫描范围：`src/part3-tools/ch19-apm/`
- 最终选择：19.12 FrameMetrics
- 选择理由：FrameMetrics 是 Android 渲染性能分析的基石 API，涉及 UI 线程、RenderThread 和 GPU 的分工协作。

## 二、总体结论
- 总体技术评分：4.5/5
- 是否建议回炉：否
- 主要风险：缺少对 `HandlerThread` 优先级设置的强调，可能导致在高负载下的数据丢失。
- 评分理由：指标解释详尽且准确，涵盖了 Android 12 (API 31) 的关键更新（DEADLINE, GPU_DURATION），具备极强的实战价值。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 5.0/5 | 0 |
| 原理链完整性 | 4.5/5 | 1 |
| 版本差异覆盖 | 5.0/5 | 0 |
| 知识盲区 | 4.0/5 | 1 |
| 数据/案例支撑 | 4.5/5 | 0 |
| 交叉引用一致性 | 5.0/5 | 0 |

## 四、P0 问题
无

## 五、P1 问题
- [P1][原理链完整性][HandlerThread 调度优先级]
- 原文问题：示例代码创建了 `HandlerThread` 但未指定优先级。
- 源码锚点：`android.os.HandlerThread` 构造函数及 `android.os.Process.setThreadPriority`。
- 关键代码逻辑：`FrameMetrics` 是在每帧结束时回调。如果系统 CPU 负载极高，监控线程可能抢不到 CPU 时间片，导致 `dropCount` 增加。
- 建议补充方向：建议在 `HandlerThread` 启动后调用 `Process.setThreadPriority(Process.THREAD_PRIORITY_URGENT_DISPLAY)` 或 `THREAD_PRIORITY_DISPLAY`，确保监控数据的准时性。

- [P1][知识盲区][GPU_DURATION 的局限性]
- 原文问题：未提及 `GPU_DURATION` 在某些驱动实现下可能不准。
- 缺失内容：`GPU_DURATION` 依赖于驱动程序支持。在某些旧设备或非标驱动上，该值可能返回 0 或是一个基于 CPU 端计时的近似值，而非真实的 GPU hardware timer。
- 建议补充方向：增加一条“驱动依赖说明”，提醒开发者在分析该指标时需核对 `GPU_DURATION > 0`。

## 六、P2 问题
- [P2][原理链完整性][SYNC_DURATION 的深层含义]
- 建议：补充说明 `SYNC_DURATION` 不仅包含 DisplayList 同步，还包含“等待前一帧 GPU 完成以腾出 Buffer”的时间。如果 GPU 负载极高导致 Buffer 阻塞，该值会显著升高。

## 九、可闭环输出

### 9.1 回炉问题单
- 章节：19.12
- 严重级别：P1
- 问题类型：原理断裂
- 描述：监控线程优先级未强调。
- 建议：代码示例中加入线程优先级设置逻辑。

### 9.4 可复用知识资产
- 关键源码路径：`android.view.FrameMetrics`
- 版本差异：API 31 引入 `GPU_DURATION` 和 `DEADLINE`。
- 技术结论：`DEADLINE` 是处理 Variable Refresh Rate (VRR) 的核心，不应再使用 16.6ms 固定阈值。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-25-15-12-external-review.md`
