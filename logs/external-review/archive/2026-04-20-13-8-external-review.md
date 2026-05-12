# AIW 自动 Review 任务报告 (13.8 Perfetto 输入延迟 SQL 深度分析)

## 一、目标发现结果
- 扫描范围：`src/part3-tools/ch13-perfetto/`
- 最终选择：`src/part3-tools/ch13-perfetto/08-input-latency-sql.md`

## 二、总体结论
- 总体技术评分：3.8/5
- 是否建议回炉：是
- 主要风险：核心 SQL 字段名与 v53 标准库不符，会导致查询失败；关联逻辑未体现 2026 年主流的桥接表模式。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 3.0/5 | 2 |
| 原理链完整性 | 4.5/5 | 1 |
| 版本差异覆盖 | 4.0/5 | 1 |
| 知识盲区 | 4.0/5 | 1 |
| 数据/案例支撑 | 4.5/5 | 0 |
| 交叉引用一致性 | 5.0/5 | 0 |

## 四、P0 问题（事实错误）
- **[P0][源码准确性][SQL 列名错误]**
  - **位置**：android_input_events
  - **问题**：文中列名为 `dispatch_ts`、`receive_ts` 等。
  - **纠正**：标准库字段名为 `dispatch_latency_dur`、`handling_latency_dur`、`ack_latency_dur` 等。
  - **建议**：统一修正为官方标准名。

- **[P0][源码准确性][视图名称错误]**
  - **位置**：Choreographer 耗时分析
  - **纠正**：标准库视图名为 `android_choreographer_callbacks`。

## 五、P1 问题（重要缺失）
- **[P1][原理/关联][桥接表关联逻辑]**
  - **内容**：应使用 `android_input_event_to_frame` 桥接表进行“输入-帧”关联。
  - **建议**：重构 SQL 示例，展示 `event_id` -> `frame_id` 的跳转。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：13.8 Perfetto 输入延迟 SQL 深度分析
- **严重级别**：P0
- **问题描述**：SQL 列名与 stdlib v53 不符；缺少核心桥接表 `android_input_event_to_frame` 的使用说明。
- **建议修正方向**：修正全篇 SQL 列名；重构关联逻辑小节。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-20-13-8-external-review.md`
