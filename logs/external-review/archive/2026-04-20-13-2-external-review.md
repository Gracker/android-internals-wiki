# AIW 自动 Review 任务报告 (13.2 Trace 抓取)

## 一、目标发现结果
- 扫描范围：`src/part3-tools/ch13-perfetto/`
- 最终选择：`src/part3-tools/ch13-perfetto/02-trace-capture.md`

## 二、总体结论
- 总体技术评分：4.0/5
- 是否建议回炉：是
- 主要风险：缺少 Android 15/16 引入的 `ProfilingManager` 体系说明，以及对 User Build 上堆栈采样（linux.perf）权限门槛的深度解析。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 4.5/5 | 0 |
| 原理链完整性 | 4.0/5 | 1 |
| 版本差异覆盖 | 3.5/5 | 2 |
| 知识盲区 | 3.5/5 | 2 |
| 数据/案例支撑 | 4.0/5 | 1 |
| 交叉引用一致性 | 5.0/5 | 0 |

## 四、P0 问题（事实错误）
*本章未发现 P0 级事实错误。*

## 五、P1 问题（重要缺失）
- **[P1][原理/版本][Android 15 ProfilingManager]**
  - **位置**：在 App 中添加自定义 Trace 标记 / 后续
  - **内容**：应新增 `ProfilingManager` (API 35+) 小节。它是 Android 15 推荐的应用自抓取方式，支持异步请求 System Trace、Heap Profile 和 Stack Sampling。
  - **建议**：补充 `ProfilingManager` 的基本用法及其脱敏（Redaction）特性。

- **[P1][知识盲区][User Build 权限门槛]**
  - **位置**：Heap Profiling 与 Callstack Sampling
  - **问题**：未提及 `<profileable android:shell="true" />`。
  - **建议**：在分析非 Debug 包时，必须强调此 Manifest 标签的作用。

## 六、P2 问题（建议改进）
- **[P2][功能/实战][新增 Category: memreclaim]**
  - **建议**：在常用 Categories 中补充 `memreclaim`（内存回收），用于 Android 15+ 分析内存压力导致的卡顿。
- **[P2][功能/实战][DWARF Unwind]**
  - **建议**：提及 `linux.perf` 在新版本中对 DWARF 异步回溯的支持。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：13.2 Trace 抓取
- **严重级别**：P1
- **问题描述**：遗漏了 Android 15 核心 API `ProfilingManager`；未强调 `profileable` 标签在 User Build 采样的必要性。
- **建议修正方向**：新增 `ProfilingManager` 小节；在高级采集部分增加 Manifest 配置说明。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-20-13-2-external-review.md`
