---
title: "Perfetto SQL 性能分析实战手册"
chapter: "13.10"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [Perfetto, SQL, Trace Processor, 性能分析, 帧时间, ANR, 启动时间, Binder]
related_chapters: ["13.3", "13.5", "13.7", "13.8", "7.1", "8.2", "9.3"]
section: "13.10"
created_by: "task2a-knowledge-gap"
created_date: "2026-04-09"
gap_source: "官方文档+读者需求+AOSP结构"
gap_score: "19/20"
---

# 13.10 Perfetto SQL 性能分析实战手册

<!-- outline-start -->
## 要点

### 🔹 锚点 1：Trace Processor SQL 基础
- Perfetto Trace Processor 的 SQL 引擎：基于 SQLite 的扩展语法
- INCLUDE PERFETTO MODULE 语句：加载预置分析模块
- 核心表结构：slice / thread_track / process_track / counter / sched
- JOIN 关系：slice → thread_track → thread → process
- 时间单位：纳秒 (ns)，常用 1e6 转毫秒、1e9 转秒
- trace_start() 函数：对齐时间零点

### 🔹 锚点 2：帧时间与卡顿分析 SQL
- 实际帧时间查询：从 Choreographer doFrame slice 计算帧间隔
- 掉帧统计：期望帧时间 vs 实际帧时间的差值
- 大帧 (Big Frame) 分析：超过 2 倍期望帧时间的帧
- 帧时间分布直方图：LEAD/LAG 窗口函数统计帧间隔分布
- 按场景分段的帧时间分析（冷启动/滑动/动画）
- 7.9 感知流畅性相关的步幅波动 (cadence discrepancy) SQL 查询

```sql
-- 统计帧时间分布
INCLUDE PERFETTO MODULE android.frames;

SELECT
  bucket_name,
  count(*) as frame_count
FROM (
  SELECT
    CASE
      WHEN dur < 8e6 THEN '< 8ms (120fps)'
      WHEN dur < 11e6 THEN '8-11ms (90fps)'
      WHEN dur < 16e6 THEN '11-16ms (60fps)'
      WHEN dur < 33e6 THEN '16-33ms (jank)'
      WHEN dur < 50e6 THEN '33-50ms (big jank)'
      ELSE '> 50ms (huge jank)'
    END as bucket_name,
    dur
  FROM slice
  WHERE name = 'Choreographer#doFrame'
)
GROUP BY bucket_name
ORDER BY MIN(dur);
```

### 🔹 锚点 3：线程调度与 CPU 使用分析 SQL
- 线程 CPU 时间统计：从 sched 表计算每线程的 running 时间
- Runnable → Running 延迟：调度延迟分析
- CPU 频率与负载关联：counter 表 + sched 表 JOIN
- 线程状态分布：Running / Runnable / Sleeping / Uninterruptible 的占比
- 按时间窗口分析 CPU 使用率

```sql
-- 主线程 CPU 使用率（每 100ms 窗口）
SELECT
  CAST((ts - trace_start()) / 1e8 AS INTEGER) AS time_bucket_100ms,
  SUM(dur) / 1e8 AS cpu_usage_pct
FROM sched
JOIN thread USING (utid)
WHERE thread.name = 'main'
GROUP BY time_bucket_100ms
ORDER BY time_bucket_100ms;
```

### 🔹 键点 4：Binder 事务分析 SQL
- Binder 事务耗时统计：按服务/方法分组
- Binder 线程池利用率：活跃线程数 vs 总线程数
- 跨进程调用链追踪：从客户端 slice 到服务端 slice 的关联
- Binder 事务超时预警：接近 5s 超时的长时间事务

### 🔹 锚点 5：内存与 GC 分析 SQL
- GC 事件统计：次数、总暂停时间、最大暂停时间
- Java Heap 变化趋势：从 counter 表提取 Java Heap 尺寸
- GC 暂停与帧时间的关联分析
- 内存分配速率与 GC 频率的关系

### 🔹 锚点 6：启动时间分析 SQL
- 冷启动全链路时间分解：Zygote fork → Application.onCreate → Activity.onCreate → firstFrame
- 各阶段耗时占比
- 启动过程中的 Binder 调用统计
- 启动过程中的锁竞争统计
- 冷启动 vs 温启动 vs 热启动的 SQL 对比模板

### 🔹 锚点 7：ANR 分析 SQL
- ANR 发生时刻前 5 秒的主线程活动分析
- 主线程阻塞原因分类：锁等待 / Binder 等待 / IO 等待 / CPU 抢占
- system_server 视角：Binder 线程池状态
- Input 事件超时分析：从 InputDispatcher 到 App 处理的延迟分解

### 🔹 锚点 8：锁竞争与同步分析 SQL
- monitor contention 事件统计
- 持锁时间 Top N 分析
- Owner-Waiter 关系链分析
- 锁竞争与帧时间的关联

```sql
-- 监控主线程锁竞争 Top 10
INCLUDE PERFETTO MODULE android.monitor;

SELECT
  slice.name AS lock_name,
  CAST(slice.dur / 1e6 AS FLOAT) AS wait_ms,
  thread.name AS waiter_thread
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread USING (utid)
WHERE thread.name = 'main'
  AND slice.name GLOB '*monitor*'
ORDER BY slice.dur DESC
LIMIT 10;
```

## 🔸 扩展 1：自定义 SQL 函数与模块
- Perfetto 支持的自定义 SQL 函数
- 创建可复用的 SQL 模板
- 如何贡献分析模块到 Perfetto 社区

## 🔸 扩展 2：常见分析模板
- 每次分析都可以直接套用的通用 SQL 模板集合
- 按性能问题类型（卡顿/ANR/启动慢/功耗高）的 SQL 诊断路径
- 从 trace 到结论的标准化分析流程

## 🔸 扩展 3：与其他章节的交叉引用
- **13.3 Perfetto View**：UI 中的可视化查询对应 SQL 中的哪些表
- **13.5 专题解读**：专题分析背后的 SQL 查询逻辑
- **13.8 输入延迟 SQL**：输入延迟的专用 SQL，本章的补充
- **7.1 卡顿定义**：帧时间分析 SQL 对应 7.1 的卡顿分类
- **8.2 启动全流程**：启动时间 SQL 对应 8.2 的阶段划分
<!-- outline-end -->

> 本节内容待加工。
