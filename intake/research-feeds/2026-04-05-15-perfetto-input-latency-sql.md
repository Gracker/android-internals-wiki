# [研究] Perfetto android.input 模块：输入延迟的 SQL 化精确分析

- **来源**: perfetto.dev/docs/analysis/sql-tables/android-input
- **作者/机构**: Perfetto Team / Google
- **日期**: 2026-04-05
- **四维评分**: 相关性 5/5 · 技术深度 5/5 · 时效性 4/5 · 可验证性 5/5 · **总分 19/20**
- **映射章节**: 3.4 输入延迟与预测输入技术 / 13.3 Perfetto View 解读 / 13.5 专题解读
- **映射锚点**: android_input_events 表、dispatch_latency_dur、handling_latency_dur、ack_latency_dur、total_latency_dur、end_to_end_latency_dur、Perfetto SQL 查询
- **摘要**: Perfetto 的 android.input 标准库模块提供了 android_input_events 表，包含从 InputDispatcher 到 App 的完整延迟分解：dispatch_latency、handling_latency、ack_latency、total_latency、end_to_end_latency 五个维度，可通过 SQL 精确定位输入延迟瓶颈发生在哪个阶段。

### 关键发现

1. **android_input_events 表的五个延迟维度**:
   - dispatch_latency_dur: InputDispatcher 发送事件到 App 接收事件的耗时
   - handling_latency_dur: App 接收到 App 处理完毕（发送 ACK）的耗时
   - ack_latency_dur: App 发送 ACK 到 InputDispatcher 收到 ACK 的耗时
   - total_latency_dur: dispatch 到 ACK 完整往返时间
   - end_to_end_latency_dur: InputReader 读取事件到帧上屏时间的端到端延迟（如果有关联帧事件）

2. **android_input_id 追踪**: 每个输入事件分配唯一 ID，可跨 InputReader/InputDispatcher/App 追踪同一事件在不同阶段的行为。

3. **Perfetto SQL 实战查询**: 通过 INCLUDE PERFETTO MODULE android.input 引入模块，JOIN thread/process 表定位到具体线程和进程，按 total_latency_dur DESC 排序快速定位最慢事件。

4. **在 Perfetto UI 中的可视化**: 启用 Input trace category 后，可在 UI 中看到 InputReader track、InputDispatcher track、App 线程的 DeliverInputEvent 切片。FrameTimeline 关联可判断是否因输入导致的掉帧。

### 实战 SQL 查询

```sql
INCLUDE PERFETTO MODULE android.input;

SELECT
  CAST(input.ts / 1000000.0) AS timestamp_ms,
  input.thread_name AS receiving_thread,
  process.name AS receiving_process,
  CAST(input.dispatch_latency_dur / 1000000.0) AS dispatch_latency_ms,
  CAST(input.handling_latency_dur / 1000000.0) AS handling_latency_ms,
  CAST(input.ack_latency_dur / 1000000.0) AS ack_latency_ms,
  CAST(input.total_latency_dur / 1000000.0) AS total_latency_ms,
  CAST(input.end_to_end_latency_dur / 1000000.0) AS end_to_end_latency_ms,
  input.android_input_id
FROM android_input_events AS input
JOIN thread USING (utid)
JOIN process USING (upid)
WHERE input.total_latency_dur IS NOT NULL
ORDER BY input.total_latency_dur DESC
LIMIT 100;
```

### 与 queue.json 联动
- 素材路径建议：补充到 §3.4（输入延迟分析方法）和 §13.3/§13.5（Perfetto 工具链）
